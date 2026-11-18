"""
Excel Database Engine for Device Warranty Management System.
Cloud-First Architecture: Loads directly from Google Drive into memory and writes back
to Google Drive via Google Drive API v3. Strictly NO local data files and NO dummy seed data.
"""

import os
import io
import logging
import threading
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

import config
from google_drive import drive_service

logger = logging.getLogger(__name__)

# Thread lock for concurrency protection
db_lock = threading.Lock()

# Header styling for professional Excel appearance
HEADER_FILL = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
THIN_BORDER = Border(
    left=Side(style='thin', color='E2E8F0'),
    right=Side(style='thin', color='E2E8F0'),
    top=Side(style='thin', color='E2E8F0'),
    bottom=Side(style='thin', color='E2E8F0')
)


class ExcelDatabase:
    def __init__(self):
        self.excel_filename = config.EXCEL_FILENAME
        self._in_memory_bytes: Optional[bytes] = None
        self._drive_file_id: Optional[str] = None
        self._is_connected: bool = False
        self._init_done: bool = False

    def is_connected(self) -> bool:
        """Returns True if the database is actively connected to Google Drive."""
        return self._is_connected and self._in_memory_bytes is not None

    def init_database(self, force_refresh: bool = False):
        """
        Initializes the cloud-only database from Google Drive.
        Strictly NO local files and NO dummy seed devices are created.
        If Google Drive is connected:
            Loads workbook from Drive into memory, or creates a clean empty workbook in Drive if not found.
        If Google Drive is disconnected:
            Database remains disconnected and empty until credentials are provided.
        """
        with db_lock:
            if self._init_done and not force_refresh:
                return

            if not drive_service.is_configured():
                logger.warning("Google Drive is not configured. Cloud database is offline (no local data fallback).")
                self._is_connected = False
                self._in_memory_bytes = None
                self._init_done = True
                return

            # Test connection
            conn_ok, msg, _ = drive_service.test_connection()
            if not conn_ok:
                logger.warning(f"Google Drive connection test failed: {msg}")
                self._is_connected = False
                self._in_memory_bytes = None
                self._init_done = True
                return

            # Search for existing file in Google Drive
            file_id = drive_service.find_file(self.excel_filename)
            if file_id:
                logger.info(f"Loading database from Google Drive (ID: {file_id})...")
                bytes_data = drive_service.download_file_bytes(file_id)
                if bytes_data:
                    self._in_memory_bytes = bytes_data
                    self._drive_file_id = file_id
                    self._verify_and_repair_sheets_memory()
                    self._is_connected = True
                    self._init_done = True
                    return

            # If not found in Google Drive, create clean empty workbook (NO seed devices) and upload to Drive
            logger.info("Database file not found in Google Drive. Creating empty schema in Google Drive...")
            wb = self._create_empty_workbook_memory()
            buf = io.BytesIO()
            wb.save(buf)
            self._in_memory_bytes = buf.getvalue()

            new_file_id = drive_service.upload_file_bytes(self._in_memory_bytes, self.excel_filename)
            if new_file_id:
                self._drive_file_id = new_file_id
                self._is_connected = True
                logger.info(f"Initialized new cloud database in Google Drive with ID: {new_file_id}")
            else:
                self._is_connected = False
                logger.error("Failed to upload initial empty database to Google Drive.")

            self._init_done = True

    def _create_empty_workbook_memory(self) -> openpyxl.Workbook:
        """Creates an empty workbook with styled sheets and default system settings, but ZERO seed devices."""
        wb = openpyxl.Workbook()
        wb.remove(wb.active)

        # 1. Devices Sheet (Empty - no fake devices!)
        ws_devices = wb.create_sheet(title=config.SHEET_DEVICES)
        self._setup_sheet_headers(ws_devices, config.DEVICE_COLUMNS)

        # 2. Notifications Sheet
        ws_notifs = wb.create_sheet(title=config.SHEET_NOTIFICATIONS)
        self._setup_sheet_headers(ws_notifs, config.NOTIFICATION_COLUMNS)

        # 3. Activity_Log Sheet
        ws_activity = wb.create_sheet(title=config.SHEET_ACTIVITY_LOG)
        self._setup_sheet_headers(ws_activity, config.ACTIVITY_LOG_COLUMNS)

        # 4. Settings Sheet
        ws_settings = wb.create_sheet(title=config.SHEET_SETTINGS)
        self._setup_sheet_headers(ws_settings, config.SETTINGS_COLUMNS)

        # Populate Default System Configuration Settings
        default_settings = [
            ("system_name", config.APP_NAME, "Display title for the warranty system", datetime.now().isoformat()),
            ("notification_lead_days", "30,14,7,3,0", "Milestone alert days before expiration", datetime.now().isoformat()),
            ("currency_symbol", "$", "Currency symbol for purchase prices", datetime.now().isoformat()),
            ("company_name", "Acme Global Technologies", "Company name for PDF reports", datetime.now().isoformat()),
            ("admin_email", "admin@equipguard.io", "Primary administrator contact email", datetime.now().isoformat()),
            ("browser_notifications_enabled", "true", "Enable HTML5 desktop browser notifications", datetime.now().isoformat()),
        ]
        for row in default_settings:
            ws_settings.append(row)

        # Log system initialization in Activity Log
        ws_activity.append([
            f"ACT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            datetime.now().isoformat(),
            "system",
            "Cloud Database Initialized",
            "SYSTEM",
            "Google Drive cloud database schema created successfully."
        ])

        self._auto_fit_columns(ws_devices)
        self._auto_fit_columns(ws_notifs)
        self._auto_fit_columns(ws_activity)
        self._auto_fit_columns(ws_settings)

        return wb

    def _setup_sheet_headers(self, ws, headers: List[str]):
        """Applies headers and professional styling to a worksheet."""
        ws.append(headers)
        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = THIN_BORDER
        ws.row_dimensions[1].height = 28

    def _auto_fit_columns(self, ws):
        """Adjusts column widths based on maximum contents."""
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                if len(val_str) > max_len:
                    max_len = len(val_str)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    def _verify_and_repair_sheets_memory(self):
        """Ensures all 4 required sheets exist in the in-memory workbook."""
        if not self._in_memory_bytes:
            return
        try:
            wb = openpyxl.load_workbook(io.BytesIO(self._in_memory_bytes))
            changed = False
            sheets_map = {
                config.SHEET_DEVICES: config.DEVICE_COLUMNS,
                config.SHEET_NOTIFICATIONS: config.NOTIFICATION_COLUMNS,
                config.SHEET_ACTIVITY_LOG: config.ACTIVITY_LOG_COLUMNS,
                config.SHEET_SETTINGS: config.SETTINGS_COLUMNS
            }
            for title, cols in sheets_map.items():
                if title not in wb.sheetnames:
                    ws = wb.create_sheet(title=title)
                    self._setup_sheet_headers(ws, cols)
                    changed = True
            if changed:
                self._save_workbook(wb)
        except Exception as e:
            logger.error(f"Error checking sheets in memory: {e}")

    def _load_workbook(self, data_only: bool = False) -> Optional[openpyxl.Workbook]:
        """Loads the active workbook from in-memory byte buffer."""
        if not self._in_memory_bytes:
            self.init_database()
        if not self._in_memory_bytes:
            return None
        try:
            return openpyxl.load_workbook(io.BytesIO(self._in_memory_bytes), data_only=data_only)
        except Exception as e:
            logger.error(f"Failed to load workbook from memory: {e}")
            return None

    def _save_workbook(self, wb: openpyxl.Workbook) -> bool:
        """Serializes workbook to memory and syncs directly to Google Drive."""
        try:
            buf = io.BytesIO()
            wb.save(buf)
            self._in_memory_bytes = buf.getvalue()

            if self._drive_file_id:
                return drive_service.update_file_bytes(self._drive_file_id, self._in_memory_bytes)
            elif drive_service.is_configured():
                file_id = drive_service.find_file(self.excel_filename)
                if file_id:
                    self._drive_file_id = file_id
                    return drive_service.update_file_bytes(file_id, self._in_memory_bytes)
                else:
                    new_id = drive_service.upload_file_bytes(self._in_memory_bytes, self.excel_filename)
                    self._drive_file_id = new_id
                    return bool(new_id)
            return True
        except Exception as e:
            logger.error(f"Failed to save workbook to Google Drive: {e}")
            return False

    # =========================================================================
    # Device CRUD Operations
    # =========================================================================

    def get_devices(self) -> List[Dict[str, Any]]:
        """Reads all device records from the Devices sheet in Google Drive."""
        self.init_database()
        if not self.is_connected():
            return []

        with db_lock:
            devices = []
            try:
                wb = self._load_workbook(data_only=True)
                if not wb or config.SHEET_DEVICES not in wb.sheetnames:
                    return []
                ws = wb[config.SHEET_DEVICES]
                rows = list(ws.iter_rows(values_only=True))
                if len(rows) <= 1:
                    return []

                headers = [str(h).strip() for h in rows[0]]
                for r in rows[1:]:
                    if not r or not r[0]:
                        continue
                    item = {}
                    for i, h in enumerate(headers):
                        val = r[i] if i < len(r) else None
                        if isinstance(val, (datetime, date)):
                            val = val.isoformat()
                        item[h] = val
                    devices.append(item)
            except Exception as e:
                logger.error(f"Error reading devices from cloud: {e}")
            return devices

    def get_device_by_id(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Finds a device by its unique Device_ID."""
        devices = self.get_devices()
        for d in devices:
            if str(d.get("Device_ID", "")).strip().upper() == str(device_id).strip().upper():
                return d
        return None

    def get_device_by_serial(self, serial_number: str) -> Optional[Dict[str, Any]]:
        """Finds a device by its Serial_Number."""
        devices = self.get_devices()
        target = str(serial_number).strip().upper()
        for d in devices:
            if str(d.get("Serial_Number", "")).strip().upper() == target:
                return d
        return None

    def save_device(self, device_data: Dict[str, Any], is_edit: bool = False) -> Tuple[bool, str]:
        """
        Inserts or updates a device record in the Devices sheet.
        Persists directly to Google Drive.
        """
        self.init_database()
        if not self.is_connected():
            return False, "Google Drive is disconnected. Connect Google Drive service account to save devices."

        with db_lock:
            try:
                wb = self._load_workbook(data_only=False)
                if not wb:
                    return False, "Could not open Google Drive database workbook."

                ws = wb[config.SHEET_DEVICES]
                headers = [cell.value for cell in ws[1]]
                device_id = device_data.get("Device_ID")

                row_idx_to_update = None
                if is_edit or device_id:
                    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                        if row and row[0] and str(row[0]).strip().upper() == str(device_id).strip().upper():
                            row_idx_to_update = row_idx
                            break

                row_values = []
                for h in headers:
                    val = device_data.get(h)
                    if isinstance(val, (datetime, date)):
                        val = val.isoformat()
                    row_values.append(val)

                if row_idx_to_update:
                    for col_idx, val in enumerate(row_values, start=1):
                        ws.cell(row=row_idx_to_update, column=col_idx, value=val)
                    msg = f"Device {device_id} updated successfully in Google Drive."
                else:
                    ws.append(row_values)
                    msg = f"Device {device_id} added successfully to Google Drive."

                self._auto_fit_columns(ws)
                saved = self._save_workbook(wb)
                if not saved:
                    return False, "Failed to upload updated database to Google Drive."
                return True, msg

            except Exception as e:
                logger.error(f"Error saving device: {e}")
                return False, f"Failed to save device: {str(e)}"

    def delete_device(self, device_id: str) -> Tuple[bool, str]:
        """Deletes a device record by Device_ID directly from Google Drive."""
        self.init_database()
        if not self.is_connected():
            return False, "Google Drive is disconnected."

        with db_lock:
            try:
                wb = self._load_workbook(data_only=False)
                if not wb:
                    return False, "Could not open Google Drive database."

                ws = wb[config.SHEET_DEVICES]
                target_row = None
                for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                    if row and row[0] and str(row[0]).strip().upper() == str(device_id).strip().upper():
                        target_row = row_idx
                        break

                if not target_row:
                    return False, f"Device with ID {device_id} not found."

                ws.delete_rows(target_row, 1)
                saved = self._save_workbook(wb)
                if not saved:
                    return False, "Failed to sync deletion to Google Drive."
                return True, f"Device {device_id} deleted successfully from Google Drive."
            except Exception as e:
                logger.error(f"Error deleting device: {e}")
                return False, f"Failed to delete device: {str(e)}"

    # =========================================================================
    # Notifications Operations
    # =========================================================================

    def get_notifications(self) -> List[Dict[str, Any]]:
        """Reads all notification records from the Notifications sheet."""
        self.init_database()
        if not self.is_connected():
            return []

        with db_lock:
            notifs = []
            try:
                wb = self._load_workbook(data_only=True)
                if not wb or config.SHEET_NOTIFICATIONS not in wb.sheetnames:
                    return []
                ws = wb[config.SHEET_NOTIFICATIONS]
                rows = list(ws.iter_rows(values_only=True))
                if len(rows) <= 1:
                    return []

                headers = [str(h).strip() for h in rows[0]]
                for r in rows[1:]:
                    if not r or not r[0]:
                        continue
                    item = {}
                    for i, h in enumerate(headers):
                        val = r[i] if i < len(r) else None
                        if isinstance(val, (datetime, date)):
                            val = val.isoformat()
                        item[h] = val
                    notifs.append(item)
            except Exception as e:
                logger.error(f"Error reading notifications: {e}")
            return notifs

    def save_notifications_batch(self, new_notifications: List[Dict[str, Any]]) -> int:
        """Appends a batch of new notifications to Google Drive."""
        if not new_notifications:
            return 0

        self.init_database()
        if not self.is_connected():
            return 0

        with db_lock:
            count = 0
            try:
                wb = self._load_workbook(data_only=False)
                if not wb:
                    return 0
                ws = wb[config.SHEET_NOTIFICATIONS]
                headers = [cell.value for cell in ws[1]]

                for notif in new_notifications:
                    row_vals = []
                    for h in headers:
                        val = notif.get(h)
                        if isinstance(val, (datetime, date)):
                            val = val.isoformat()
                        row_vals.append(val)
                    ws.append(row_vals)
                    count += 1

                self._save_workbook(wb)
            except Exception as e:
                logger.error(f"Error saving batch notifications: {e}")
            return count

    def mark_notification_read(self, notification_id: str) -> bool:
        """Marks a notification as 'read' in Google Drive."""
        self.init_database()
        if not self.is_connected():
            return False

        with db_lock:
            try:
                wb = self._load_workbook(data_only=False)
                if not wb:
                    return False
                ws = wb[config.SHEET_NOTIFICATIONS]
                headers = [cell.value for cell in ws[1]]
                status_col_idx = headers.index("Status") + 1 if "Status" in headers else None

                if not status_col_idx:
                    return False

                for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                    if row and row[0] and str(row[0]).strip() == str(notification_id).strip():
                        ws.cell(row=row_idx, column=status_col_idx, value="read")
                        self._save_workbook(wb)
                        return True
                return False
            except Exception as e:
                logger.error(f"Error marking notification read: {e}")
                return False

    def mark_all_notifications_read(self) -> int:
        """Marks all unread notifications as 'read'."""
        self.init_database()
        if not self.is_connected():
            return 0

        with db_lock:
            updated_count = 0
            try:
                wb = self._load_workbook(data_only=False)
                if not wb:
                    return 0
                ws = wb[config.SHEET_NOTIFICATIONS]
                headers = [cell.value for cell in ws[1]]
                status_col_idx = headers.index("Status") + 1 if "Status" in headers else None

                if not status_col_idx:
                    return 0

                for row_idx in range(2, ws.max_row + 1):
                    val = ws.cell(row=row_idx, column=status_col_idx).value
                    if val != "read":
                        ws.cell(row=row_idx, column=status_col_idx, value="read")
                        updated_count += 1

                if updated_count > 0:
                    self._save_workbook(wb)
            except Exception as e:
                logger.error(f"Error marking all notifications read: {e}")
            return updated_count

    # =========================================================================
    # Activity Log Operations
    # =========================================================================

    def log_activity(self, user_email: str, action: str, device_id: str, details: str):
        """Appends a new audit record to the Activity_Log sheet."""
        self.init_database()
        if not self.is_connected():
            return

        with db_lock:
            try:
                wb = self._load_workbook(data_only=False)
                if not wb:
                    return
                ws = wb[config.SHEET_ACTIVITY_LOG]
                log_id = f"ACT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                ws.append([
                    log_id,
                    datetime.now().isoformat(),
                    user_email or "system",
                    action,
                    device_id or "N/A",
                    details
                ])
                self._save_workbook(wb)
            except Exception as e:
                logger.error(f"Error logging activity: {e}")

    def get_activity_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Reads recent activity log entries sorted newest first."""
        self.init_database()
        if not self.is_connected():
            return []

        with db_lock:
            logs = []
            try:
                wb = self._load_workbook(data_only=True)
                if not wb or config.SHEET_ACTIVITY_LOG not in wb.sheetnames:
                    return []
                ws = wb[config.SHEET_ACTIVITY_LOG]
                rows = list(ws.iter_rows(values_only=True))
                if len(rows) <= 1:
                    return []

                headers = [str(h).strip() for h in rows[0]]
                for r in reversed(rows[1:]):
                    if not r or not r[0]:
                        continue
                    item = {}
                    for i, h in enumerate(headers):
                        val = r[i] if i < len(r) else None
                        if isinstance(val, (datetime, date)):
                            val = val.isoformat()
                        item[h] = val
                    logs.append(item)
                    if len(logs) >= limit:
                        break
            except Exception as e:
                logger.error(f"Error reading activity logs: {e}")
            return logs

    # =========================================================================
    # Settings Operations
    # =========================================================================

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Retrieves a system configuration setting from the Settings sheet."""
        self.init_database()
        if not self.is_connected():
            return default

        with db_lock:
            try:
                wb = self._load_workbook(data_only=True)
                if not wb or config.SHEET_SETTINGS not in wb.sheetnames:
                    return default
                ws = wb[config.SHEET_SETTINGS]
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if row and row[0] and str(row[0]).strip() == key:
                        return row[1]
            except Exception as e:
                logger.error(f"Error getting setting {key}: {e}")
            return default

    def set_setting(self, key: str, value: Any, description: str = "") -> bool:
        """Sets or updates a configuration key in the Settings sheet."""
        self.init_database()
        if not self.is_connected():
            return False

        with db_lock:
            try:
                wb = self._load_workbook(data_only=False)
                if not wb:
                    return False
                ws = wb[config.SHEET_SETTINGS]
                found = False
                for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                    if row and row[0] and str(row[0]).strip() == key:
                        ws.cell(row=row_idx, column=2, value=str(value))
                        ws.cell(row=row_idx, column=4, value=datetime.now().isoformat())
                        if description:
                            ws.cell(row=row_idx, column=3, value=description)
                        found = True
                        break
                if not found:
                    ws.append([key, str(value), description, datetime.now().isoformat()])
                return self._save_workbook(wb)
            except Exception as e:
                logger.error(f"Error setting setting {key}: {e}")
                return False

    def sync_to_drive(self) -> Tuple[bool, str]:
        """Synchronously pushes in-memory database to Google Drive."""
        if not drive_service.is_configured() or not self._in_memory_bytes:
            return False, "Google Drive is not configured."
        return drive_service.sync_file_bytes(self._in_memory_bytes, self.excel_filename)

    def sync_from_drive(self) -> Tuple[bool, str]:
        """Synchronously pulls latest database from Google Drive."""
        if not drive_service.is_configured():
            return False, "Google Drive is not configured."
        file_id = drive_service.find_file(self.excel_filename)
        if not file_id:
            return False, "File not found in Google Drive."
        data = drive_service.download_file_bytes(file_id)
        if data:
            self._in_memory_bytes = data
            self._drive_file_id = file_id
            self._is_connected = True
            return True, f"Downloaded latest cloud database from Google Drive (File ID: {file_id[:8]}...)."
        return False, "Failed to download cloud database."


# Singleton instance
excel_db = ExcelDatabase()
