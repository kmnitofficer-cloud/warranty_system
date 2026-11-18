"""
Excel Database Engine for Device Warranty Management System.
Manages the 4 workbook sheets (Devices, Notifications, Activity_Log, Settings)
using openpyxl, with thread-safe operations, styled headers, and automated
Google Drive synchronization.
"""

import os
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
    def __init__(self, local_path: Optional[Path] = None):
        self.local_path = local_path or config.LOCAL_DB_PATH
        self.excel_filename = config.EXCEL_FILENAME
        self._init_done = False

    def init_database(self, force_refresh: bool = False):
        """
        Initializes the Excel database.
        1. Attempts to download from Google Drive if configured.
        2. If not found or drive offline, checks local cache.
        3. If local file missing, creates new workbook with all 4 sheets and seed data.
        """
        with db_lock:
            if self._init_done and not force_refresh:
                return

            drive_synced = False
            if drive_service.is_configured():
                file_id = drive_service.find_file(self.excel_filename)
                if file_id:
                    logger.info(f"Found existing database in Google Drive (ID: {file_id}). Downloading...")
                    drive_synced = drive_service.download_file(file_id, self.local_path)

            if not self.local_path.exists() or self.local_path.stat().st_size == 0:
                logger.info("Local database file not found. Creating fresh workbook with schema and starter data...")
                self._create_empty_workbook_with_seeds()
                if drive_service.is_configured():
                    drive_service.sync_file(self.local_path, self.excel_filename)
            else:
                # Ensure all 4 sheets exist in existing workbook
                self._verify_and_repair_sheets()

            self._init_done = True

    def _create_empty_workbook_with_seeds(self):
        """Creates the initial workbook with styled sheets and sample seed records."""
        wb = openpyxl.Workbook()
        # Remove default sheet
        wb.remove(wb.active)

        # 1. Devices Sheet
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

        # Populate Default Settings
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

        # Populate Seed Devices for instant evaluation
        today = date.today()
        seed_devices = [
            (
                "DEV-1001", "MacBook Pro 16 M3 Max", "Laptop", "Apple", "A2991", "C02G87Y9MD6R",
                "Alex Mercer", "Executive", (today - timedelta(days=330)).isoformat(), 3499.00, "Apple Business Direct",
                (today - timedelta(days=330)).isoformat(), (today + timedelta(days=35)).isoformat(), 12,
                "INV-2025-0891", "Executive workstation. High priority.", "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=300",
                datetime.now().isoformat(), datetime.now().isoformat()
            ),
            (
                "DEV-1002", "Dell Precision 5820 Tower", "Desktop", "Dell", "T5820", "8X9Q2Z3",
                "David Kim", "Operations", (today - timedelta(days=720)).isoformat(), 2850.00, "Dell Direct",
                (today - timedelta(days=720)).isoformat(), (today + timedelta(days=10)).isoformat(), 24,
                "INV-2024-0412", "CAD Engineering station. Warranty renewal pending quote.", "https://images.unsplash.com/photo-1587831990711-23ca6441447b?w=300",
                datetime.now().isoformat(), datetime.now().isoformat()
            ),
            (
                "DEV-1003", "HP Color LaserJet Pro MFP", "Printer", "HP", "M479fdw", "VNC3K98201",
                "Floor 3 Shared", "Finance", (today - timedelta(days=360)).isoformat(), 699.00, "CDW Corporation",
                (today - timedelta(days=360)).isoformat(), (today + timedelta(days=2)).isoformat(), 12,
                "INV-2025-0104", "Main finance floor printer. High utilization.", "https://images.unsplash.com/photo-1612815154858-60aa4c59eaa6?w=300",
                datetime.now().isoformat(), datetime.now().isoformat()
            ),
            (
                "DEV-1004", "Dell UltraSharp 34 Curved", "Monitor", "Dell", "U3423WE", "CN0M39YF7444",
                "Sarah Connor", "IT", (today - timedelta(days=400)).isoformat(), 899.00, "Amazon Business",
                (today - timedelta(days=400)).isoformat(), (today - timedelta(days=15)).isoformat(), 12,
                "INV-2025-0012", "Dual USB-C monitor. Warranty expired.", "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=300",
                datetime.now().isoformat(), datetime.now().isoformat()
            ),
            (
                "DEV-1005", "Cisco Catalyst 9200L Switch", "Router", "Cisco", "C9200L-48P-4G", "FOC2438S0R2",
                "MDF Server Room", "IT", (today - timedelta(days=200)).isoformat(), 3200.00, "Cisco Partner Direct",
                (today - timedelta(days=200)).isoformat(), (today + timedelta(days=165)).isoformat(), 12,
                "INV-2025-1198", "Core access layer switch in main server room.", "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=300",
                datetime.now().isoformat(), datetime.now().isoformat()
            ),
            (
                "DEV-1006", "Hikvision 4K Dome Camera", "CCTV", "Hikvision", "DS-2CD2185G0", "HK202309117",
                "Main Entrance Gate", "Operations", (today - timedelta(days=180)).isoformat(), 280.00, "SecureTech Systems",
                (today - timedelta(days=180)).isoformat(), (today + timedelta(days=185)).isoformat(), 12,
                "INV-2025-0551", "Exterior perimeter surveillance camera.", "https://images.unsplash.com/photo-1557597774-9d273605dfa9?w=300",
                datetime.now().isoformat(), datetime.now().isoformat()
            ),
            (
                "DEV-1007", "APC Smart-UPS RT 3000VA", "UPS", "APC by Schneider", "SURTD3000XLI", "AS214532098",
                "Server Room Rack A", "IT", (today - timedelta(days=364)).isoformat(), 1950.00, "PowerSolutions Inc",
                (today - timedelta(days=364)).isoformat(), (today + timedelta(days=1)).isoformat(), 12,
                "INV-2025-0099", "Critical battery backup for main host servers. Urgent renewal required.", "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=300",
                datetime.now().isoformat(), datetime.now().isoformat()
            ),
            (
                "DEV-1008", "Lenovo ThinkPad X1 Carbon Gen 11", "Laptop", "Lenovo", "21HM000KUS", "PF4H9K12",
                "Michael Scott", "Sales & Marketing", (today - timedelta(days=90)).isoformat(), 1899.00, "Lenovo Pro Store",
                (today - timedelta(days=90)).isoformat(), (today + timedelta(days=275)).isoformat(), 12,
                "INV-2025-1540", "Sales executive ultralight laptop.", "https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=300",
                datetime.now().isoformat(), datetime.now().isoformat()
            )
        ]

        for device in seed_devices:
            ws_devices.append(device)

        # Initial Activity Log
        initial_activity = [
            ("ACT-1001", (today - timedelta(days=2)).isoformat(), "admin@equipguard.io", "System Initialized", "SYSTEM", "Initial database seeded with 8 devices across 7 categories."),
            ("ACT-1002", (today - timedelta(days=1)).isoformat(), "manager@equipguard.io", "Device Added", "DEV-1008", "Added Lenovo ThinkPad X1 Carbon for Sales team."),
            ("ACT-1003", today.isoformat(), "system", "Warranty Check", "SYSTEM", "Automated warranty schedule evaluation initiated.")
        ]
        for act in initial_activity:
            ws_activity.append(act)

        self._auto_fit_columns(ws_devices)
        self._auto_fit_columns(ws_notifs)
        self._auto_fit_columns(ws_activity)
        self._auto_fit_columns(ws_settings)

        self.local_path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(str(self.local_path))
        logger.info(f"Database created successfully at {self.local_path}")

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

    def _verify_and_repair_sheets(self):
        """Ensures all 4 required sheets exist in the workbook."""
        try:
            wb = openpyxl.load_workbook(str(self.local_path))
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
                wb.save(str(self.local_path))
        except Exception as e:
            logger.error(f"Error checking sheets: {e}")

    # =========================================================================
    # Device CRUD Operations
    # =========================================================================

    def get_devices(self) -> List[Dict[str, Any]]:
        """Reads all device records from the Devices sheet."""
        self.init_database()
        with db_lock:
            devices = []
            try:
                wb = openpyxl.load_workbook(str(self.local_path), data_only=True)
                if config.SHEET_DEVICES not in wb.sheetnames:
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
                logger.error(f"Error reading devices: {e}")
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
        Persists locally and triggers Google Drive sync.
        """
        self.init_database()
        with db_lock:
            try:
                wb = openpyxl.load_workbook(str(self.local_path))
                ws = wb[config.SHEET_DEVICES]

                headers = [cell.value for cell in ws[1]]
                device_id = device_data.get("Device_ID")

                row_idx_to_update = None
                if is_edit or device_id:
                    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                        if row and row[0] and str(row[0]).strip().upper() == str(device_id).strip().upper():
                            row_idx_to_update = row_idx
                            break

                # Prepare row values according to header ordering
                row_values = []
                for h in headers:
                    val = device_data.get(h)
                    if isinstance(val, (datetime, date)):
                        val = val.isoformat()
                    row_values.append(val)

                if row_idx_to_update:
                    for col_idx, val in enumerate(row_values, start=1):
                        ws.cell(row=row_idx_to_update, column=col_idx, value=val)
                    msg = f"Device {device_id} updated successfully."
                else:
                    ws.append(row_values)
                    msg = f"Device {device_id} added successfully."

                self._auto_fit_columns(ws)
                wb.save(str(self.local_path))

                # Background sync to Google Drive
                self._trigger_drive_sync()
                return True, msg

            except Exception as e:
                logger.error(f"Error saving device: {e}")
                return False, f"Failed to save device: {str(e)}"

    def delete_device(self, device_id: str) -> Tuple[bool, str]:
        """Deletes a device record by Device_ID."""
        self.init_database()
        with db_lock:
            try:
                wb = openpyxl.load_workbook(str(self.local_path))
                ws = wb[config.SHEET_DEVICES]

                target_row = None
                for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                    if row and row[0] and str(row[0]).strip().upper() == str(device_id).strip().upper():
                        target_row = row_idx
                        break

                if not target_row:
                    return False, f"Device with ID {device_id} not found."

                ws.delete_rows(target_row, 1)
                wb.save(str(self.local_path))

                self._trigger_drive_sync()
                return True, f"Device {device_id} deleted successfully."
            except Exception as e:
                logger.error(f"Error deleting device: {e}")
                return False, f"Failed to delete device: {str(e)}"

    # =========================================================================
    # Notifications Operations
    # =========================================================================

    def get_notifications(self) -> List[Dict[str, Any]]:
        """Reads all notification records from the Notifications sheet."""
        self.init_database()
        with db_lock:
            notifs = []
            try:
                wb = openpyxl.load_workbook(str(self.local_path), data_only=True)
                if config.SHEET_NOTIFICATIONS not in wb.sheetnames:
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
        """Appends a batch of new notifications to the Notifications sheet."""
        if not new_notifications:
            return 0

        self.init_database()
        with db_lock:
            count = 0
            try:
                wb = openpyxl.load_workbook(str(self.local_path))
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

                wb.save(str(self.local_path))
                self._trigger_drive_sync()
            except Exception as e:
                logger.error(f"Error saving batch notifications: {e}")
            return count

    def mark_notification_read(self, notification_id: str) -> bool:
        """Marks a notification as 'read'."""
        self.init_database()
        with db_lock:
            try:
                wb = openpyxl.load_workbook(str(self.local_path))
                ws = wb[config.SHEET_NOTIFICATIONS]
                headers = [cell.value for cell in ws[1]]
                status_col_idx = headers.index("Status") + 1 if "Status" in headers else None

                if not status_col_idx:
                    return False

                for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                    if row and row[0] and str(row[0]).strip() == str(notification_id).strip():
                        ws.cell(row=row_idx, column=status_col_idx, value="read")
                        wb.save(str(self.local_path))
                        self._trigger_drive_sync()
                        return True
                return False
            except Exception as e:
                logger.error(f"Error marking notification read: {e}")
                return False

    def mark_all_notifications_read(self) -> int:
        """Marks all unread notifications as 'read'."""
        self.init_database()
        with db_lock:
            updated_count = 0
            try:
                wb = openpyxl.load_workbook(str(self.local_path))
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
                    wb.save(str(self.local_path))
                    self._trigger_drive_sync()
            except Exception as e:
                logger.error(f"Error marking all notifications read: {e}")
            return updated_count

    # =========================================================================
    # Activity Log Operations
    # =========================================================================

    def log_activity(self, user_email: str, action: str, device_id: str, details: str):
        """Appends a new audit record to the Activity_Log sheet."""
        self.init_database()
        with db_lock:
            try:
                wb = openpyxl.load_workbook(str(self.local_path))
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
                wb.save(str(self.local_path))
                self._trigger_drive_sync()
            except Exception as e:
                logger.error(f"Error logging activity: {e}")

    def get_activity_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Reads recent activity log entries sorted newest first."""
        self.init_database()
        with db_lock:
            logs = []
            try:
                wb = openpyxl.load_workbook(str(self.local_path), data_only=True)
                if config.SHEET_ACTIVITY_LOG not in wb.sheetnames:
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
        with db_lock:
            try:
                wb = openpyxl.load_workbook(str(self.local_path), data_only=True)
                if config.SHEET_SETTINGS not in wb.sheetnames:
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
        with db_lock:
            try:
                wb = openpyxl.load_workbook(str(self.local_path))
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
                wb.save(str(self.local_path))
                self._trigger_drive_sync()
                return True
            except Exception as e:
                logger.error(f"Error setting setting {key}: {e}")
                return False

    def sync_to_drive(self) -> Tuple[bool, str]:
        """Synchronously pushes local database to Google Drive."""
        if not drive_service.is_configured():
            return False, "Google Drive not configured."
        return drive_service.sync_file(self.local_path, self.excel_filename)

    def sync_from_drive(self) -> Tuple[bool, str]:
        """Synchronously pulls latest database from Google Drive."""
        if not drive_service.is_configured():
            return False, "Google Drive not configured."
        file_id = drive_service.find_file(self.excel_filename)
        if not file_id:
            return False, "File not found in Google Drive."
        success = drive_service.download_file(file_id, self.local_path)
        if success:
            return True, f"Downloaded latest cloud database (File ID: {file_id})."
        return False, "Failed to download cloud database."

    def _trigger_drive_sync(self):
        """Helper to sync current workbook to Google Drive in the background."""
        if drive_service.is_configured():
            try:
                threading.Thread(
                    target=drive_service.sync_file,
                    args=(self.local_path, self.excel_filename),
                    daemon=True
                ).start()
            except Exception as e:
                logger.error(f"Failed to start drive sync thread: {e}")


# Singleton instance
excel_db = ExcelDatabase()
