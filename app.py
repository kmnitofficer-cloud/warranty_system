"""
EquipGuard - Device Warranty Management & Notification System.
Main Streamlit Application coordinating backend operations, Google Drive Excel persistence,
Firebase authentication, automated warranty calculation, PDF/Excel reports, and modern HTML frontend.
"""

import os
import json
import time
import base64
import logging
from pathlib import Path
from datetime import datetime, date

import streamlit as st
import streamlit.components.v1 as components

# Configure application logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("EquipGuard")

# Import application core modules
import config
from firebase_auth import auth_service
from google_drive import drive_service
from excel_database import excel_db
from warranty_checker import warranty_checker
from notification_manager import notification_manager
from device_manager import device_manager
from reports import report_service

# Set Streamlit Page Configuration
st.set_page_config(
    page_title=f"{config.APP_NAME} - Enterprise Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Declare Custom Streamlit Component serving HTML5 / CSS / JS Frontend
equipguard_component = components.declare_component(
    "equipguard_main_component",
    path=str(config.FRONTEND_DIR)
)


def initialize_app_state():
    """Initializes Streamlit session state and automated background checks."""
    if "initialized" not in st.session_state:
        # Initialize Excel database & Google Drive synchronization
        excel_db.init_database()
        
        # Execute automated warranty checks on application start
        count, new_notifs = notification_manager.run_check()
        if count > 0:
            logger.info(f"System startup check generated {count} new milestone warranty notifications.")

        st.session_state["initialized"] = True
        st.session_state["authenticated"] = False
        st.session_state["user"] = None
        st.session_state["toast"] = None
        st.session_state["error"] = None
        st.session_state["download_payload"] = None
        st.session_state["last_processed_req_id"] = None


def handle_component_actions(event: dict):
    """Dispatches frontend events to backend business logic and services securely."""
    if not event or not isinstance(event, dict):
        return

    req_id = event.get("requestId")
    if not req_id or req_id == st.session_state.get("last_processed_req_id"):
        return

    st.session_state["last_processed_req_id"] = req_id
    action = event.get("action")
    payload = event.get("payload", {})
    user_email = (st.session_state.get("user") or {}).get("email", "admin@equipguard.io")

    logger.info(f"Processing backend action: {action} by {user_email}")

    # 1. Login Action (Username/Password or Token Session Restoration)
    if action == "login":
        id_token = payload.get("idToken")
        email = payload.get("email") or payload.get("username")
        password = payload.get("password")

        if id_token:
            valid, restored_user = auth_service.verify_id_token(id_token)
            if valid and restored_user:
                st.session_state["authenticated"] = True
                st.session_state["user"] = restored_user
                st.session_state["toast"] = f"Welcome back, {restored_user.get('display_name')}!"
                st.session_state["error"] = None
                logger.info(f"Session restored for {restored_user.get('email')} via session token.")
            else:
                st.session_state["authenticated"] = False
                st.session_state["user"] = None
                st.session_state["error"] = None
        else:
            success, msg, user_dict = auth_service.sign_in(email, password)
            if success and user_dict:
                st.session_state["authenticated"] = True
                st.session_state["user"] = user_dict
                st.session_state["toast"] = f"Welcome back, {user_dict.get('display_name')}!"
                st.session_state["error"] = None
                
                # Asynchronously log user activity in Google Drive Excel
                import threading
                threading.Thread(
                    target=lambda: excel_db.log_activity(
                        email, "User Login", "AUTH", f"User authenticated via {user_dict.get('auth_mode', 'Firebase')}."
                    ),
                    daemon=True
                ).start()
                logger.info(f"User {email} successfully authenticated! Displaying dashboard.")
            else:
                st.session_state["authenticated"] = False
                st.session_state["user"] = None
                st.session_state["error"] = msg or "Authentication failed."
                logger.warning(f"Login failed for {email}: {msg}")

        st.rerun()

    # 2. Logout Action
    elif action == "logout":
        st.session_state["authenticated"] = False
        st.session_state["user"] = None
        st.session_state["toast"] = "Signed out successfully."
        st.session_state["error"] = None

        if user_email:
            import threading
            threading.Thread(
                target=lambda: excel_db.log_activity(user_email, "User Logout", "AUTH", "User signed out."),
                daemon=True
            ).start()

        st.rerun()

    # 3. Add Device Action
    elif action == "add_device":
        success, msg, new_dev = device_manager.add_device(payload, user_email)
        if success:
            st.session_state["toast"] = msg
            st.session_state["error"] = None
        else:
            st.session_state["error"] = msg
        st.rerun()

    # 4. Update Device Action
    elif action == "update_device":
        device_id = payload.get("Device_ID")
        success, msg, updated_dev = device_manager.update_device(device_id, payload, user_email)
        if success:
            st.session_state["toast"] = msg
            st.session_state["error"] = None
        else:
            st.session_state["error"] = msg
        st.rerun()

    # 5. Delete Device Action
    elif action == "delete_device":
        device_id = payload.get("Device_ID")
        success, msg = device_manager.delete_device(device_id, user_email)
        if success:
            st.session_state["toast"] = msg
            st.session_state["error"] = None
        else:
            st.session_state["error"] = msg
        st.rerun()

    # 6. Mark Notification Read Action
    elif action == "mark_notification_read":
        notif_id = payload.get("Notification_ID")
        notification_manager.mark_as_read(notif_id)
        st.rerun()

    # 7. Mark All Notifications Read Action
    elif action == "mark_all_notifications_read":
        notification_manager.mark_all_as_read()
        st.rerun()

    # 8. Export to Excel (.xlsx) Action
    elif action == "export_excel":
        devices = device_manager.get_all_devices_enriched()
        excel_bytes = report_service.generate_excel_report(devices)
        b64_data = base64.b64encode(excel_bytes).decode("utf-8")
        st.session_state["download_payload"] = {
            "data": b64_data,
            "filename": f"EquipGuard_Warranty_Report_{datetime.now().strftime('%Y%m%d')}.xlsx",
            "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }
        st.rerun()

    # 9. Export to PDF Action
    elif action == "export_pdf":
        devices = device_manager.get_all_devices_enriched()
        summary = report_service.get_analytics_summary()
        pdf_bytes = report_service.generate_pdf_report(devices, summary)
        b64_data = base64.b64encode(pdf_bytes).decode("utf-8")
        st.session_state["download_payload"] = {
            "data": b64_data,
            "filename": f"EquipGuard_Executive_Audit_{datetime.now().strftime('%Y%m%d')}.pdf",
            "mime": "application/pdf"
        }
        st.rerun()

    # 10. Clear Download Payload
    elif action == "clear_download_payload":
        st.session_state["download_payload"] = None


def main():
    initialize_app_state()

    # Prepare complete enriched state package for HTML frontend
    devices = device_manager.get_all_devices_enriched()
    notifications = notification_manager.get_notifications()
    analytics = report_service.get_analytics_summary()
    drive_configured = drive_service.is_configured()
    cloud_file_id = excel_db._drive_file_id or drive_service._cached_file_id
    cloud_sync_info = {
        "configured": excel_db.is_connected(),
        "email": drive_service.get_service_account_email() if drive_configured else None,
        "status": "Google Drive Active" if excel_db.is_connected() else "Google Drive Disconnected",
        "file_id": cloud_file_id
    }

    # Consume one-shot messages
    toast_to_send = st.session_state.get("toast")
    error_to_send = st.session_state.get("error")
    toast_id = f"toast_{time.time()}_{abs(hash(toast_to_send))}" if toast_to_send else None

    st.session_state["toast"] = None
    st.session_state["error"] = None

    component_state = {
        "authenticated": st.session_state.get("authenticated", False),
        "user": st.session_state.get("user"),
        "devices": devices,
        "notifications": notifications,
        "analytics": analytics,
        "cloud_sync": cloud_sync_info,
        "toast": toast_to_send,
        "toast_id": toast_id,
        "error": error_to_send,
        "download_payload": st.session_state.get("download_payload"),
        "timestamp": time.time()
    }

    # Full-screen iframe CSS injection ensuring 100vw, 100vh layout
    st.markdown("""
        <style>
            /* Completely hide Streamlit header, toolbar, hamburger menu, and footer */
            #MainMenu, header, footer, [data-testid="stHeader"], [data-testid="stToolbar"], .stAppToolbar, [data-testid="stDecoration"], [data-testid="stStatusWidget"] {
                display: none !important;
                visibility: hidden !important;
                height: 0 !important;
                width: 0 !important;
                opacity: 0 !important;
            }

            /* Fullscreen reset for parent containers */
            html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], .main, .block-container, [data-testid="stMainBlockContainer"] {
                padding: 0 !important;
                margin: 0 !important;
                max-width: 100vw !important;
                width: 100vw !important;
                height: 100vh !important;
                overflow: hidden !important;
                background-color: #0F172A !important;
            }

            /* Seamless Full-Screen Fixed Iframe */
            iframe {
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                right: 0 !important;
                bottom: 0 !important;
                width: 100vw !important;
                height: 100vh !important;
                min-height: 100vh !important;
                border: none !important;
                margin: 0 !important;
                padding: 0 !important;
                z-index: 999999 !important;
                background-color: #0F172A !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # Mount and execute custom HTML5 component
    event_data = equipguard_component(
        state=component_state,
        key="equipguard_main_component",
        default=None
    )

    # Process user actions coming from the frontend
    if event_data:
        handle_component_actions(event_data)


if __name__ == "__main__":
    main()
