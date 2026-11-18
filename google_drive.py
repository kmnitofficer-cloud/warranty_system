"""
Google Drive API Integration Module for Device Warranty Management System.
Handles Service Account authentication, file search, upload, update, and download
for the primary Excel database stored in Google Drive.
"""

import os
import io
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError

import config

logger = logging.getLogger(__name__)


class GoogleDriveService:
    def __init__(self, credentials_path: Optional[Path] = None):
        self.credentials_path = credentials_path or config.SERVICE_ACCOUNT_FILE
        self.scopes = config.GOOGLE_DRIVE_SCOPES
        self._service = None
        self._cached_file_id = None
        self._last_sync_status = "Not Initialized"
        self._service_account_email = None

    def _get_credentials_dict(self) -> Optional[dict]:
        """Loads service account credentials dictionary from file, st.secrets, env, or TOML."""
        # 1. Check file path
        if self.credentials_path and os.path.isfile(self.credentials_path):
            try:
                with open(self.credentials_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("type") == "service_account" and data.get("client_email"):
                        return data
            except Exception as e:
                logger.warning(f"Failed to read credentials file: {e}")

        # 2. Check Streamlit secrets
        try:
            import streamlit as st
            if hasattr(st, "secrets") and st.secrets and "google_drive" in st.secrets:
                drive_sec = dict(st.secrets["google_drive"])
                if drive_sec.get("client_email"):
                    return drive_sec
        except Exception:
            pass

        # 3. Check environment variable
        env_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        if env_json:
            try:
                data = json.loads(env_json)
                if data.get("client_email"):
                    return data
            except Exception:
                pass

        # 4. Check local TOML files
        candidates = [
            config.BASE_DIR / ".streamlit" / "secrets.toml",
            config.BASE_DIR.parent / ".streamlit" / "secrets.toml",
            config.BASE_DIR / "secret.toml",
            config.BASE_DIR.parent / "secret.toml",
            config.BASE_DIR / "secrets.toml",
            config.BASE_DIR.parent / "secrets.toml"
        ]
        for p in candidates:
            if p.exists():
                try:
                    import tomllib
                    with open(p, "rb") as f:
                        toml_data = tomllib.load(f)
                        if "google_drive" in toml_data and toml_data["google_drive"].get("client_email"):
                            return dict(toml_data["google_drive"])
                except Exception:
                    pass

        return None

    def is_configured(self) -> bool:
        """Checks if valid Google Drive service account credentials are available."""
        creds_dict = self._get_credentials_dict()
        if creds_dict and creds_dict.get("client_email"):
            self._service_account_email = creds_dict.get("client_email")
            return True
        return False

    def get_service_account_email(self) -> Optional[str]:
        """Returns the client email of the active service account if known."""
        if not self._service_account_email and self.is_configured():
            pass
        return self._service_account_email

    def get_service(self):
        """Constructs and returns an authorized Google Drive API v3 client."""
        if self._service is not None:
            return self._service

        creds_dict = self._get_credentials_dict()
        if creds_dict:
            try:
                creds = service_account.Credentials.from_service_account_info(
                    creds_dict,
                    scopes=self.scopes
                )
                self._service_account_email = creds.service_account_email
                self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
                return self._service
            except Exception as e:
                logger.error(f"Error initializing Google Drive credentials: {e}")

        return None

    def test_connection(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Tests Google Drive API authentication and returns status details."""
        if not self.is_configured():
            return False, "Google Drive Service Account is not configured yet.", {
                "configured": False,
                "email": None
            }

        try:
            service = self.get_service()
            if not service:
                return False, "Could not initialize Google Drive API service.", {"configured": False}

            about = service.about().get(fields="user, storageQuota").execute()
            user_info = about.get("user", {})
            return True, "Successfully connected to Google Drive API.", {
                "configured": True,
                "email": user_info.get("emailAddress", self._service_account_email),
                "name": user_info.get("displayName", "Service Account"),
                "storage_quota": about.get("storageQuota", {})
            }
        except Exception as e:
            logger.error(f"Google Drive connection test failed: {e}")
            return False, f"Google Drive connection failed: {str(e)}", {"configured": False, "error": str(e)}

    def find_file(self, filename: str) -> Optional[str]:
        """Searches for a non-trashed file by name in Google Drive."""
        service = self.get_service()
        if not service:
            return None

        try:
            query = f"name = '{filename}' and trashed = false"
            response = service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name, modifiedTime, size)",
                pageSize=10
            ).execute()

            files = response.get("files", [])
            if files:
                self._cached_file_id = files[0]["id"]
                return files[0]["id"]
            return None
        except Exception as e:
            logger.error(f"Error searching for file {filename} in Google Drive: {e}")
            return None

    def download_file(self, file_id: str, destination_path: Path) -> bool:
        """Downloads a file from Google Drive to the specified local path."""
        service = self.get_service()
        if not service:
            return False

        try:
            request = service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

            destination_path.parent.mkdir(parents=True, exist_ok=True)
            with open(destination_path, "wb") as f:
                f.write(fh.getvalue())

            self._last_sync_status = "Synced from Google Drive"
            logger.info(f"Downloaded file {file_id} to {destination_path}")
            return True
        except Exception as e:
            logger.error(f"Error downloading file {file_id} from Google Drive: {e}")
            self._last_sync_status = f"Download Failed: {str(e)}"
            return False

    def upload_file(self, local_path: Path, filename: Optional[str] = None) -> Optional[str]:
        """Uploads a new file to Google Drive."""
        service = self.get_service()
        if not service:
            return None

        filename = filename or local_path.name
        try:
            file_metadata = {
                "name": filename,
                "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            }
            media = MediaFileUpload(
                str(local_path),
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                resumable=True
            )
            created_file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, name"
            ).execute()

            self._cached_file_id = created_file.get("id")
            self._last_sync_status = "Uploaded to Google Drive"
            logger.info(f"Created file {filename} in Google Drive with ID: {self._cached_file_id}")
            return self._cached_file_id
        except Exception as e:
            logger.error(f"Error uploading file {filename} to Google Drive: {e}")
            self._last_sync_status = f"Upload Failed: {str(e)}"
            return None

    def update_file(self, file_id: str, local_path: Path) -> bool:
        """Updates the content of an existing file in Google Drive without changing its ID, with automatic retry."""
        service = self.get_service()
        if not service:
            return False

        import time
        for attempt in range(1, 4):
            try:
                media = MediaFileUpload(
                    str(local_path),
                    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    resumable=True
                )
                service.files().update(
                    fileId=file_id,
                    media_body=media
                ).execute()

                self._last_sync_status = "Updated in Google Drive"
                logger.info(f"Updated file {file_id} in Google Drive")
                return True
            except Exception as e:
                logger.warning(f"Attempt {attempt}/3 failed updating Google Drive file: {e}")
                if attempt < 3:
                    time.sleep(1.0)
                else:
                    logger.error(f"Error updating file {file_id} in Google Drive after 3 attempts: {e}")
                    self._last_sync_status = f"Update Failed: {str(e)}"
                    return False
        return False

    def sync_file(self, local_path: Path, filename: Optional[str] = None) -> Tuple[bool, str]:
        """
        Synchronizes the local file with Google Drive:
        - If file exists in Drive, updates it.
        - If file does not exist, creates it.
        """
        filename = filename or local_path.name
        if not self.is_configured():
            return False, "Google Drive not configured. Saved to local storage."

        file_id = self._cached_file_id or self.find_file(filename)
        if file_id:
            success = self.update_file(file_id, local_path)
            if success:
                return True, f"Successfully synchronized with Google Drive (File ID: {file_id[:8]}...)."
            return False, f"Failed to update file in Google Drive."
        else:
            new_id = self.upload_file(local_path, filename)
            if new_id:
                return True, f"Successfully created database in Google Drive (File ID: {new_id[:8]}...)."
            return False, "Failed to upload new database to Google Drive."

    def share_file_with_email(self, file_id: str, email: str, role: str = "writer") -> Tuple[bool, str]:
        """Shares a file in Google Drive with an external user email (e.g. your personal Gmail)."""
        service = self.get_service()
        if not service:
            return False, "Google Drive API not connected."
        try:
            user_permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email.strip()
            }
            service.permissions().create(
                fileId=file_id,
                body=user_permission,
                fields='id',
                sendNotificationEmail=False
            ).execute()
            logger.info(f"Shared file {file_id} with {email} as {role}")
            return True, f"Successfully granted access to {email} ({role}). You can now open it in Google Drive!"
        except Exception as e:
            logger.error(f"Error sharing file {file_id} with {email}: {e}")
            return False, f"Failed to share file: {str(e)}"


# Singleton instance
drive_service = GoogleDriveService()
