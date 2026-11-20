"""
Configuration module for Device Warranty Management & Notification System.
Centralizes environment variables, default settings, file paths, and system constants.
"""

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
CREDENTIALS_DIR = BASE_DIR / "credentials"
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
ASSETS_DIR = BASE_DIR / "assets"

# Ensure runtime directories exist
for directory in [CREDENTIALS_DIR, DATA_DIR, REPORTS_DIR, ASSETS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Application Metadata
APP_NAME = "EquipGuard Warranty Manager"
APP_SUBTITLE = "Enterprise Device Warranty Management & Notification System"
APP_VERSION = "1.0.0"

# Database Configuration
EXCEL_FILENAME = "Device_Warranty_Database.xlsx"
LOCAL_DB_PATH = DATA_DIR / EXCEL_FILENAME
GOOGLE_DRIVE_FOLDER_NAME = "Device_Warranty_System"

# Google Drive Service Account Credentials Path
SERVICE_ACCOUNT_FILE = CREDENTIALS_DIR / "service_account.json"
GOOGLE_DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file"
]

def _load_secret(key: str, default: str = "") -> str:
    """Safely retrieves secrets from Streamlit secrets, environment variables, or secret.toml files."""
    def _is_valid(val) -> bool:
        if val is None:
            return False
        s = str(val).strip()
        return len(s) > 0 and not s.startswith("YOUR_")

    mapping = {
        "FIREBASE_WEB_API_KEY": ["apiKey", "api_key", "FIREBASE_API_KEY"],
        "FIREBASE_PROJECT_ID": ["projectId", "project_id"],
        "FIREBASE_AUTH_DOMAIN": ["authDomain", "auth_domain"],
        "FIREBASE_STORAGE_BUCKET": ["storageBucket", "storage_bucket"],
        "FIREBASE_MESSAGING_SENDER_ID": ["messagingSenderId", "messaging_sender_id"],
        "FIREBASE_APP_ID": ["appId", "app_id"],
        "FIREBASE_MEASUREMENT_ID": ["measurementId", "measurement_id"],
    }

    try:
        import streamlit as st
        if hasattr(st, "secrets") and st.secrets:
            if key in st.secrets and _is_valid(st.secrets[key]):
                return str(st.secrets[key]).strip()
            if "firebase" in st.secrets:
                fb = st.secrets["firebase"]
                if hasattr(fb, "get"):
                    if key in fb and _is_valid(fb[key]):
                        return str(fb[key]).strip()
                    for alias in mapping.get(key, []):
                        if alias in fb and _is_valid(fb[alias]):
                            return str(fb[alias]).strip()
            for alias in mapping.get(key, []):
                if alias in st.secrets and _is_valid(st.secrets[alias]):
                    return str(st.secrets[alias]).strip()
    except Exception:
        pass

    # Environment variables
    if os.environ.get(key) and _is_valid(os.environ.get(key)):
        return str(os.environ.get(key)).strip()
    for alias in mapping.get(key, []):
        if os.environ.get(alias) and _is_valid(os.environ.get(alias)):
            return str(os.environ.get(alias)).strip()

    # Check local TOML files
    candidates = [
        BASE_DIR / ".streamlit" / "secrets.toml",
        BASE_DIR.parent / ".streamlit" / "secrets.toml",
        BASE_DIR / "secret.toml",
        BASE_DIR.parent / "secret.toml",
        BASE_DIR / "secrets.toml",
        BASE_DIR.parent / "secrets.toml"
    ]
    for p in candidates:
        if p.exists():
            try:
                import tomllib
                with open(p, "rb") as f:
                    data = tomllib.load(f)
                    if key in data and _is_valid(data[key]):
                        return str(data[key]).strip()
                    if "firebase" in data and isinstance(data["firebase"], dict):
                        fb = data["firebase"]
                        if key in fb and _is_valid(fb[key]):
                            return str(fb[key]).strip()
                        for alias in mapping.get(key, []):
                            if alias in fb and _is_valid(fb[alias]):
                                return str(fb[alias]).strip()
                    for alias in mapping.get(key, []):
                        if alias in data and _is_valid(data[alias]):
                            return str(data[alias]).strip()
            except Exception:
                pass

    return default


# Firebase Configuration
FIREBASE_WEB_API_KEY = _load_secret("FIREBASE_WEB_API_KEY", "AIzaSyDJxnSGZd0_9JrGCm6TtECPvZSCJqwqpB4")
FIREBASE_AUTH_DOMAIN = _load_secret("FIREBASE_AUTH_DOMAIN", "kmn-it-warranty-2d94c.firebaseapp.com")
FIREBASE_PROJECT_ID = _load_secret("FIREBASE_PROJECT_ID", "kmn-it-warranty-2d94c")
FIREBASE_STORAGE_BUCKET = _load_secret("FIREBASE_STORAGE_BUCKET", "kmn-it-warranty-2d94c.firebasestorage.app")
FIREBASE_MESSAGING_SENDER_ID = _load_secret("FIREBASE_MESSAGING_SENDER_ID", "131012675015")
FIREBASE_APP_ID = _load_secret("FIREBASE_APP_ID", "1:131012675015:web:57a73f89a58e3330b305e2")
FIREBASE_MEASUREMENT_ID = _load_secret("FIREBASE_MEASUREMENT_ID", "G-V7WQEFKEHN")
FIREBASE_SERVICE_ACCOUNT_FILE = CREDENTIALS_DIR / "firebase_admin.json"

def get_firebase_config() -> dict:
    return {
        "apiKey": FIREBASE_WEB_API_KEY,
        "authDomain": FIREBASE_AUTH_DOMAIN,
        "projectId": FIREBASE_PROJECT_ID,
        "storageBucket": FIREBASE_STORAGE_BUCKET,
        "messagingSenderId": FIREBASE_MESSAGING_SENDER_ID,
        "appId": FIREBASE_APP_ID,
        "measurementId": FIREBASE_MEASUREMENT_ID
    }

# Demo Credentials (Removed - Real Firebase Authentication required)
DEMO_USERS = {}

# Device Categories
DEVICE_CATEGORIES = [
    "Laptop",
    "Desktop",
    "Printer",
    "Monitor",
    "Router",
    "CCTV",
    "UPS",
    "Mobile Phone",
    "Other"
]

# Standard Departments
DEPARTMENTS = [
    "IT",
    "Finance",
    "Human Resources",
    "Operations",
    "Sales & Marketing",
    "Customer Support",
    "Executive",
    "Warehouse",
    "Legal"
]

# Warranty Status Thresholds
WARRANTY_ACTIVE_DAYS = 30       # More than 30 days remaining
WARRANTY_EXPIRING_SOON_DAYS = 30 # 30 days or fewer remaining
# Notification Milestones (days before expiration)
NOTIFICATION_MILESTONES = [30, 14, 7, 3, 0]

# Notification Urgency Mapping
MILESTONE_URGENCY = {
    30: "low",
    14: "medium",
    7: "high",
    3: "critical",
    0: "critical"
}

# Excel Database Sheets
SHEET_DEVICES = "Devices"
SHEET_NOTIFICATIONS = "Notifications"
SHEET_ACTIVITY_LOG = "Activity_Log"
SHEET_SETTINGS = "Settings"

DEVICE_COLUMNS = [
    "Device_ID",
    "Device_Name",
    "Category",
    "Brand",
    "Model_Number",
    "Serial_Number",
    "Assigned_User",
    "Department",
    "Purchase_Date",
    "Purchase_Price",
    "Supplier",
    "Warranty_Start_Date",
    "Warranty_End_Date",
    "Warranty_Duration_Months",
    "Invoice_Number",
    "Notes",
    "Image_URL",
    "Created_At",
    "Updated_At"
]

NOTIFICATION_COLUMNS = [
    "Notification_ID",
    "Device_ID",
    "Device_Name",
    "Serial_Number",
    "Milestone",
    "Notification_Date",
    "Warranty_End_Date",
    "Days_Remaining",
    "Message",
    "Urgency",
    "Status"
]

ACTIVITY_LOG_COLUMNS = [
    "Log_ID",
    "Timestamp",
    "User_Email",
    "Action",
    "Device_ID",
    "Details"
]

SETTINGS_COLUMNS = [
    "Setting_Key",
    "Setting_Value",
    "Description",
    "Updated_At"
]
