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
    try:
        import streamlit as st
        if hasattr(st, "secrets") and st.secrets:
            if key in st.secrets:
                return str(st.secrets[key])
            if "firebase" in st.secrets and isinstance(st.secrets["firebase"], dict) and key in st.secrets["firebase"]:
                return str(st.secrets["firebase"][key])
    except Exception:
        pass

    # Environment variables
    if os.environ.get(key):
        return os.environ.get(key)

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
                    if key in data:
                        return str(data[key])
                    if "firebase" in data and isinstance(data["firebase"], dict) and key in data["firebase"]:
                        return str(data["firebase"][key])
            except Exception:
                pass

    return default


# Firebase Configuration
FIREBASE_WEB_API_KEY = _load_secret("FIREBASE_WEB_API_KEY", "AIzaSyC8s9oRsWxzExlhjvIZqVoYZBsjJyG47ts")
FIREBASE_AUTH_DOMAIN = _load_secret("FIREBASE_AUTH_DOMAIN", "kmn-it-warranty.firebaseapp.com")
FIREBASE_PROJECT_ID = _load_secret("FIREBASE_PROJECT_ID", "kmn-it-warranty")
FIREBASE_STORAGE_BUCKET = _load_secret("FIREBASE_STORAGE_BUCKET", "kmn-it-warranty.firebasestorage.app")
FIREBASE_MESSAGING_SENDER_ID = _load_secret("FIREBASE_MESSAGING_SENDER_ID", "270307773370")
FIREBASE_APP_ID = _load_secret("FIREBASE_APP_ID", "1:270307773370:web:dd7d54f4187e3b2b8cab83")
FIREBASE_MEASUREMENT_ID = _load_secret("FIREBASE_MEASUREMENT_ID", "G-RNJ3CP4ECJ")
FIREBASE_SERVICE_ACCOUNT_FILE = CREDENTIALS_DIR / "firebase_admin.json"

# Demo Credentials (used for instant evaluation and testing when Firebase API Key is not yet set)
DEMO_USERS = {
    "admin@equipguard.io": {
        "password": "Password123!",
        "name": "Alex Mercer",
        "role": "System Administrator",
        "department": "IT Operations",
        "avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&h=100&fit=crop&crop=faces"
    },
    "manager@equipguard.io": {
        "password": "Password123!",
        "name": "Sarah Connor",
        "role": "IT Asset Manager",
        "department": "IT Operations",
        "avatar": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop&crop=faces"
    }
}

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
