"""
Firebase Authentication module for Device Warranty Management System.
Supports Firebase Identity Toolkit REST API (Email & Password), token validation,
and seamless fallback demo authentication when API credentials are not yet configured.
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

import config

logger = logging.getLogger(__name__)

# Firebase Identity Toolkit REST endpoints
FIREBASE_AUTH_SIGNIN_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
FIREBASE_AUTH_SIGNUP_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signUp"
FIREBASE_AUTH_LOOKUP_URL = "https://identitytoolkit.googleapis.com/v1/accounts:lookup"
FIREBASE_AUTH_RESET_URL = "https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode"


class FirebaseAuthService:
    def __init__(self, api_key: Optional[str] = None, project_id: Optional[str] = None):
        self.api_key = api_key or os.environ.get("FIREBASE_WEB_API_KEY") or config.FIREBASE_WEB_API_KEY
        self.project_id = project_id or os.environ.get("FIREBASE_PROJECT_ID") or config.FIREBASE_PROJECT_ID
        self.local_users_store = dict(config.DEMO_USERS)

    def is_configured(self) -> bool:
        """Returns True if a real Firebase Web API key is configured."""
        return bool(self.api_key and len(self.api_key) > 10 and not self.api_key.startswith("YOUR_"))

    def set_api_key(self, api_key: str):
        """Allows dynamic configuration of Firebase API key from settings."""
        self.api_key = api_key

    def sign_in(self, email: str, password: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Authenticate user with email and password via Firebase Authentication.
        Strict verification: wrong passwords are NEVER accepted.
        Returns: (success: bool, message: str, user_dict: Optional[dict])
        """
        email = (email or "").strip().lower()
        password = password or ""

        if not email or not password:
            return False, "Email and password are required.", None

        if not self.is_configured():
            return False, "Firebase Authentication is not configured. Please provide a valid FIREBASE_WEB_API_KEY in your Streamlit Secrets.", None

        try:
            payload = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }
            params = {"key": self.api_key}
            response = requests.post(FIREBASE_AUTH_SIGNIN_URL, params=params, json=payload, timeout=10)
            data = response.json()

            if response.status_code == 200:
                display_name = data.get("displayName") or email.split("@")[0].title()
                user_data = {
                    "uid": data.get("localId"),
                    "email": data.get("email", email),
                    "display_name": display_name,
                    "role": "Administrator" if "admin" in email else "Asset Manager",
                    "department": "IT Operations",
                    "avatar": f"https://api.dicebear.com/7.x/initials/svg?seed={display_name}",
                    "id_token": data.get("idToken"),
                    "refresh_token": data.get("refreshToken"),
                    "expires_in": data.get("expiresIn"),
                    "is_authenticated": True,
                    "auth_mode": "firebase",
                    "last_login": datetime.now().isoformat()
                }
                return True, "Login successful via Firebase Authentication.", user_data
            else:
                error_info = data.get("error", {})
                error_msg = error_info.get("message", "Authentication failed.")
                friendly_msg = self._translate_error(error_msg)
                return False, friendly_msg, None

        except requests.RequestException as e:
            logger.error(f"Network error during Firebase auth: {e}")
            return False, f"Network error connecting to Firebase: {str(e)}", None

    def sign_up(self, email: str, password: str, display_name: Optional[str] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Register a new user with email and password via Firebase Authentication.
        Returns: (success: bool, message: str, user_dict: Optional[dict])
        """
        email = (email or "").strip().lower()
        password = password or ""
        display_name = (display_name or "").strip() or email.split("@")[0].title()

        if not email or not password:
            return False, "Email and password are required.", None

        if len(password) < 6:
            return False, "Password must be at least 6 characters long.", None

        if not self.is_configured():
            return False, "Firebase Authentication is not configured. Please provide a valid FIREBASE_WEB_API_KEY in your Streamlit Secrets.", None

        try:
            payload = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }
            params = {"key": self.api_key}
            response = requests.post(FIREBASE_AUTH_SIGNUP_URL, params=params, json=payload, timeout=10)
            data = response.json()

            if response.status_code == 200:
                user_data = {
                    "uid": data.get("localId"),
                    "email": data.get("email", email),
                    "display_name": display_name,
                    "role": "Asset Manager",
                    "department": "IT Operations",
                    "avatar": f"https://api.dicebear.com/7.x/initials/svg?seed={display_name}",
                    "id_token": data.get("idToken"),
                    "refresh_token": data.get("refreshToken"),
                    "is_authenticated": True,
                    "auth_mode": "firebase",
                    "last_login": datetime.now().isoformat()
                }
                return True, "Registration successful via Firebase Authentication.", user_data
            else:
                error_info = data.get("error", {})
                error_msg = error_info.get("message", "Registration failed.")
                return False, self._translate_error(error_msg), None
        except requests.RequestException as e:
            return False, f"Network error during registration: {str(e)}", None

    def reset_password(self, email: str) -> Tuple[bool, str]:
        """Send password reset email via Firebase Authentication."""
        email = (email or "").strip().lower()
        if not email:
            return False, "Please enter your email address."

        if not self.is_configured():
            return False, "Firebase Authentication is not configured. Please set FIREBASE_WEB_API_KEY in Streamlit Secrets."

        try:
            payload = {
                "requestType": "PASSWORD_RESET",
                "email": email
            }
            params = {"key": self.api_key}
            response = requests.post(FIREBASE_AUTH_RESET_URL, params=params, json=payload, timeout=10)
            if response.status_code == 200:
                return True, f"Password reset instructions have been sent to {email}."
            else:
                data = response.json()
                error_msg = data.get("error", {}).get("message", "Could not send reset email.")
                return False, self._translate_error(error_msg)
        except Exception as e:
            return False, f"Error requesting password reset: {e}"

    def _translate_error(self, error_code: str) -> str:
        """Translates Firebase error codes into human-readable messages."""
        translations = {
            "EMAIL_NOT_FOUND": "No registered account found with this email. Please click 'Create Account' to sign up.",
            "INVALID_PASSWORD": "Incorrect password. Please verify your credentials or click 'Forgot password?'.",
            "INVALID_LOGIN_CREDENTIALS": "Invalid email or password. If you don't have an account yet, click 'Create Account' above.",
            "USER_DISABLED": "This user account has been disabled by an administrator.",
            "EMAIL_EXISTS": "An account with this email address already exists. Please Sign In instead.",
            "OPERATION_NOT_ALLOWED": "Password sign-in is disabled in your Firebase console.",
            "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many failed login attempts. Please try again later.",
            "WEAK_PASSWORD : Password should be at least 6 characters": "Password must be at least 6 characters long.",
            "API_KEY_INVALID": "Firebase Web API Key is invalid or expired. Please update FIREBASE_WEB_API_KEY in your Streamlit Secrets.",
            "API key not valid. Please pass a valid API key.": "Firebase Web API Key is invalid or expired. Please update FIREBASE_WEB_API_KEY in your Streamlit Secrets."
        }
        return translations.get(error_code, f"Authentication error: {error_code}")


# Singleton instance
auth_service = FirebaseAuthService()
