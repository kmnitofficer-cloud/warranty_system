"""
EquipGuard - Device Warranty Management & Notification System.
Main Streamlit Application coordinating backend operations, Google Drive Excel persistence,
Firebase authentication, automated warranty calculation, PDF/Excel reports, and the modern HTML frontend.
"""

import os
import json
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
    "equipguard_component",
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
        st.session_state["user"] = None
        st.session_state["last_nonce"] = None
        st.session_state["download_payload"] = None
        st.session_state["toast_message"] = None


def handle_component_actions(component_event: dict):
    """Dispatches frontend events to backend business logic and services."""
    if not component_event or not isinstance(component_event, dict):
        return

    nonce = component_event.get("timestamp")
    if nonce and nonce == st.session_state.get("last_nonce"):
        return

    st.session_state["last_nonce"] = nonce
    action = component_event.get("action")
    payload = component_event.get("payload", {})
    user_email = (st.session_state.get("user") or {}).get("email", "admin@equipguard.io")

    logger.info(f"Handling frontend action: {action} by {user_email}")

    # 1. Login Action
    if action == "login":
        email = payload.get("email")
        password = payload.get("password")
        success, msg, user_dict = auth_service.sign_in(email, password)
        if success and user_dict:
            st.session_state["user"] = user_dict
            st.session_state["auth_error"] = None
            excel_db.log_activity(email, "User Login", "AUTH", f"User logged in via {user_dict.get('auth_mode')}.")
            st.session_state["toast_message"] = ("success", f"Welcome back, {user_dict.get('display_name')}!")
        else:
            st.session_state["auth_error"] = msg
            st.session_state["toast_message"] = ("error", msg)
        st.rerun()

    # 1b. Sign Up / Register Action
    elif action == "sign_up":
        email = payload.get("email")
        password = payload.get("password")
        display_name = payload.get("display_name", "")
        success, msg, user_dict = auth_service.sign_up(email, password, display_name)
        if success and user_dict:
            st.session_state["user"] = user_dict
            st.session_state["auth_error"] = None
            excel_db.log_activity(email, "User Registration", "AUTH", f"User registered via {user_dict.get('auth_mode')}.")
            st.session_state["toast_message"] = ("success", f"Account created! Welcome, {user_dict.get('display_name')}!")
        else:
            st.session_state["auth_error"] = msg
            st.session_state["toast_message"] = ("error", msg)
        st.rerun()

    # 1c. Client-side Auth Success Notification
    elif action == "login_success":
        user_dict = payload.get("user")
        if user_dict:
            st.session_state["user"] = user_dict
            st.session_state["auth_error"] = None
            excel_db.log_activity(user_dict.get("email", ""), "User Login", "AUTH", "Client Firebase authenticated.")
        st.rerun()

    # 2. Logout Action
    elif action == "logout":
        if st.session_state.get("user"):
            excel_db.log_activity(user_email, "User Logout", "AUTH", "User signed out.")
        st.session_state["user"] = None
        st.session_state["toast_message"] = ("info", "Signed out successfully.")
        st.rerun()

    # 3. Add Device Action
    elif action == "add_device":
        success, msg, new_dev = device_manager.add_device(payload, user_email)
        if success:
            st.session_state["toast_message"] = ("success", msg)
        else:
            st.session_state["toast_message"] = ("error", msg)
        st.rerun()

    # 4. Update Device Action
    elif action == "update_device":
        device_id = payload.get("Device_ID")
        success, msg, updated_dev = device_manager.update_device(device_id, payload, user_email)
        if success:
            st.session_state["toast_message"] = ("success", msg)
        else:
            st.session_state["toast_message"] = ("error", msg)
        st.rerun()

    # 5. Delete Device Action
    elif action == "delete_device":
        device_id = payload.get("Device_ID")
        success, msg = device_manager.delete_device(device_id, user_email)
        if success:
            st.session_state["toast_message"] = ("warning", msg)
        else:
            st.session_state["toast_message"] = ("error", msg)
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

    # 8. Test Google Drive Connection Action
    elif action == "test_drive_connection":
        drive_service._service = None
        success, msg, details = drive_service.test_connection()
        if success:
            excel_db.init_database(force_refresh=True)
            st.session_state["toast_message"] = ("success", f"Google Drive Connected! ({details.get('email')})")
        else:
            st.session_state["toast_message"] = ("warning", f"Drive Connection Failed: {msg}")
        st.rerun()

    # 8b. Save Google Drive Service Account Credentials Action
    elif action == "save_drive_credentials":
        creds_json = payload.get("json_content")
        try:
            parsed = json.loads(creds_json) if isinstance(creds_json, str) else creds_json
            if parsed.get("type") == "service_account" and parsed.get("client_email"):
                target_file = config.CREDENTIALS_DIR / "service_account.json"
                with open(target_file, "w", encoding="utf-8") as f:
                    json.dump(parsed, f, indent=2)
                drive_service.credentials_path = target_file
                drive_service._service = None
                drive_service._service_account_email = parsed.get("client_email")
                success, msg, details = drive_service.test_connection()
                if success:
                    excel_db.init_database(force_refresh=True)
                    st.session_state["toast_message"] = ("success", f"Connected to Google Drive! ({details.get('email')})")
                else:
                    st.session_state["toast_message"] = ("error", f"Key saved, but Drive API error: {msg}")
            else:
                st.session_state["toast_message"] = ("error", "Invalid Service Account JSON. Must contain 'client_email'.")
        except Exception as e:
            st.session_state["toast_message"] = ("error", f"Failed to parse JSON: {e}")
        st.rerun()

    # 9. Sync Google Drive Action
    elif action == "sync_drive":
        if drive_service.is_configured():
            success, msg = excel_db.sync_to_drive()
            if success:
                st.session_state["toast_message"] = ("success", msg)
            else:
                st.session_state["toast_message"] = ("error", msg)
        else:
            st.session_state["toast_message"] = ("warning", "Google Drive credentials not configured. Cloud database offline.")
        st.rerun()

    # 9b. Share Google Drive File Action
    elif action == "share_drive_file":
        share_email = payload.get("email") if isinstance(payload, dict) else None
        if not share_email:
            st.session_state["toast_message"] = ("error", "Please provide a valid email address.")
        elif not drive_service.is_configured():
            st.session_state["toast_message"] = ("error", "Google Drive is not configured.")
        else:
            file_id = drive_service._cached_file_id or drive_service.find_file(config.EXCEL_FILENAME)
            if not file_id:
                st.session_state["toast_message"] = ("error", "Could not locate Excel file in Google Drive.")
            else:
                success, msg = drive_service.share_file_with_email(file_id, share_email)
                if success:
                    st.session_state["toast_message"] = ("success", msg)
                else:
                    st.session_state["toast_message"] = ("error", msg)
        st.rerun()

    # 10. Export to Excel (.xlsx) Action
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

    # 11. Export to PDF Action
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

    # 12. Clear Download Payload
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

    component_state = {
        "user": st.session_state.get("user"),
        "auth_error": st.session_state.get("auth_error"),
        "firebase_config": config.get_firebase_config(),
        "devices": devices,
        "notifications": notifications,
        "analytics": analytics,
        "cloud_sync": cloud_sync_info,
        "download_payload": st.session_state.get("download_payload")
    }

    # Full-screen iframe CSS injection ensuring 100vw, 100vh true SaaS layout
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

    # Mount and execute the custom HTML5 component
    component_event = equipguard_component(
        args=component_state,
        key="equipguard_main_component",
        default=None
    )

    # Process user actions coming from the frontend
    if component_event:
        handle_component_actions(component_event)


if __name__ == "__main__":
    main()
