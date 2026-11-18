"""
Device Management Module for Device Warranty Management System.
Handles device CRUD operations, automatic ID generation, strict field validation,
serial number uniqueness enforcement, activity auditing, and enriched warranty statuses.
"""

import re
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Tuple, Optional

import config
from excel_database import excel_db
from warranty_checker import warranty_checker, parse_date
from notification_manager import notification_manager

logger = logging.getLogger(__name__)


class DeviceManager:
    def generate_next_device_id(self) -> str:
        """Generates a sequential unique Device ID (e.g. DEV-1009)."""
        devices = excel_db.get_devices()
        max_num = 1000
        for d in devices:
            d_id = str(d.get("Device_ID", "")).strip()
            match = re.search(r"DEV-(\d+)", d_id, re.IGNORECASE)
            if match:
                try:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass
        return f"DEV-{max_num + 1}"

    def validate_device_input(self, data: Dict[str, Any], is_edit: bool = False, current_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        Validates required fields, date order, and enforces serial number uniqueness.
        """
        name = str(data.get("Device_Name", "")).strip()
        category = str(data.get("Category", "")).strip()
        serial = str(data.get("Serial_Number", "")).strip()
        start_date_val = data.get("Warranty_Start_Date")
        end_date_val = data.get("Warranty_End_Date")

        if not name:
            return False, "Device Name is required."

        if not category:
            return False, "Device Category is required."

        if category not in config.DEVICE_CATEGORIES:
            return False, f"Invalid category. Must be one of: {', '.join(config.DEVICE_CATEGORIES)}"

        if not serial:
            return False, "Serial Number is required."

        start_date = parse_date(start_date_val)
        if not start_date:
            return False, "Valid Warranty Start Date is required (YYYY-MM-DD)."

        end_date = parse_date(end_date_val)
        if not end_date:
            return False, "Valid Warranty End Date is required (YYYY-MM-DD)."

        if end_date < start_date:
            return False, "Warranty End Date cannot be earlier than Warranty Start Date."

        # Check Serial Number uniqueness across other devices
        existing_device = excel_db.get_device_by_serial(serial)
        if existing_device:
            existing_id = str(existing_device.get("Device_ID", "")).strip()
            if not is_edit or (current_id and existing_id.upper() != current_id.strip().upper()):
                return False, f"A device with Serial Number '{serial}' already exists (Device ID: {existing_id}). Duplicate records are prevented."

        # Validate Purchase Price if provided
        price_val = data.get("Purchase_Price")
        if price_val not in (None, ""):
            try:
                price = float(price_val)
                if price < 0:
                    return False, "Purchase Price cannot be negative."
            except (ValueError, TypeError):
                return False, "Purchase Price must be a valid number."

        return True, "Validation successful."

    def calculate_duration_months(self, start_date_val: Any, end_date_val: Any) -> int:
        """Calculates warranty duration in months between start and end dates."""
        start = parse_date(start_date_val)
        end = parse_date(end_date_val)
        if not start or not end:
            return 12
        months = (end.year - start.year) * 12 + (end.month - start.month)
        if end.day >= start.day:
            months += 0
        return max(1, months)

    def add_device(self, data: Dict[str, Any], user_email: str = "admin@equipguard.io") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Adds a new device to the inventory.
        Validates input, generates unique Device_ID, calculates duration,
        saves to Excel, logs activity, and triggers notification evaluation.
        """
        valid, msg = self.validate_device_input(data, is_edit=False)
        if not valid:
            return False, msg, None

        device_id = self.generate_next_device_id()
        start_date = parse_date(data.get("Warranty_Start_Date"))
        end_date = parse_date(data.get("Warranty_End_Date"))
        duration_months = self.calculate_duration_months(start_date, end_date)

        purchase_date = parse_date(data.get("Purchase_Date"))
        purchase_price = None
        if data.get("Purchase_Price") not in (None, ""):
            try:
                purchase_price = round(float(data.get("Purchase_Price")), 2)
            except (ValueError, TypeError):
                purchase_price = None

        now_str = datetime.now().isoformat()
        new_device = {
            "Device_ID": device_id,
            "Device_Name": str(data.get("Device_Name", "")).strip(),
            "Category": str(data.get("Category", "Other")).strip(),
            "Brand": str(data.get("Brand", "")).strip(),
            "Model_Number": str(data.get("Model_Number", "")).strip(),
            "Serial_Number": str(data.get("Serial_Number", "")).strip(),
            "Assigned_User": str(data.get("Assigned_User", "")).strip() or "Unassigned",
            "Department": str(data.get("Department", "IT")).strip(),
            "Purchase_Date": purchase_date.isoformat() if purchase_date else "",
            "Purchase_Price": purchase_price,
            "Supplier": str(data.get("Supplier", "")).strip(),
            "Warranty_Start_Date": start_date.isoformat() if start_date else "",
            "Warranty_End_Date": end_date.isoformat() if end_date else "",
            "Warranty_Duration_Months": duration_months,
            "Invoice_Number": str(data.get("Invoice_Number", "")).strip(),
            "Notes": str(data.get("Notes", "")).strip(),
            "Image_URL": str(data.get("Image_URL", "")).strip() or self._get_default_category_image(data.get("Category")),
            "Created_At": now_str,
            "Updated_At": now_str
        }

        success, save_msg = excel_db.save_device(new_device, is_edit=False)
        if not success:
            return False, save_msg, None

        # Log to Activity Log
        excel_db.log_activity(
            user_email=user_email,
            action="Device Added",
            device_id=device_id,
            details=f"Added {new_device['Device_Name']} (S/N: {new_device['Serial_Number']}) in {new_device['Department']}."
        )

        # Run automated warranty check to register any immediate milestone alerts
        notification_manager.run_check()

        return True, f"Device {device_id} ({new_device['Device_Name']}) added successfully.", new_device

    def update_device(self, device_id: str, data: Dict[str, Any], user_email: str = "admin@equipguard.io") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Updates an existing device."""
        existing = excel_db.get_device_by_id(device_id)
        if not existing:
            return False, f"Device with ID {device_id} not found.", None

        valid, msg = self.validate_device_input(data, is_edit=True, current_id=device_id)
        if not valid:
            return False, msg, None

        start_date = parse_date(data.get("Warranty_Start_Date"))
        end_date = parse_date(data.get("Warranty_End_Date"))
        duration_months = self.calculate_duration_months(start_date, end_date)

        purchase_date = parse_date(data.get("Purchase_Date"))
        purchase_price = None
        if data.get("Purchase_Price") not in (None, ""):
            try:
                purchase_price = round(float(data.get("Purchase_Price")), 2)
            except (ValueError, TypeError):
                purchase_price = None

        updated_device = {
            "Device_ID": device_id,
            "Device_Name": str(data.get("Device_Name", "")).strip(),
            "Category": str(data.get("Category", existing.get("Category", "Other"))).strip(),
            "Brand": str(data.get("Brand", "")).strip(),
            "Model_Number": str(data.get("Model_Number", "")).strip(),
            "Serial_Number": str(data.get("Serial_Number", "")).strip(),
            "Assigned_User": str(data.get("Assigned_User", "")).strip() or "Unassigned",
            "Department": str(data.get("Department", existing.get("Department", "IT"))).strip(),
            "Purchase_Date": purchase_date.isoformat() if purchase_date else existing.get("Purchase_Date"),
            "Purchase_Price": purchase_price if purchase_price is not None else existing.get("Purchase_Price"),
            "Supplier": str(data.get("Supplier", "")).strip(),
            "Warranty_Start_Date": start_date.isoformat() if start_date else existing.get("Warranty_Start_Date"),
            "Warranty_End_Date": end_date.isoformat() if end_date else existing.get("Warranty_End_Date"),
            "Warranty_Duration_Months": duration_months,
            "Invoice_Number": str(data.get("Invoice_Number", "")).strip(),
            "Notes": str(data.get("Notes", "")).strip(),
            "Image_URL": str(data.get("Image_URL", "")).strip() or existing.get("Image_URL"),
            "Created_At": existing.get("Created_At", datetime.now().isoformat()),
            "Updated_At": datetime.now().isoformat()
        }

        success, save_msg = excel_db.save_device(updated_device, is_edit=True)
        if not success:
            return False, save_msg, None

        excel_db.log_activity(
            user_email=user_email,
            action="Device Updated",
            device_id=device_id,
            details=f"Updated details for {updated_device['Device_Name']} (S/N: {updated_device['Serial_Number']})."
        )

        notification_manager.run_check()
        return True, f"Device {device_id} updated successfully.", updated_device

    def delete_device(self, device_id: str, user_email: str = "admin@equipguard.io") -> Tuple[bool, str]:
        """Deletes a device and logs the action."""
        existing = excel_db.get_device_by_id(device_id)
        if not existing:
            return False, f"Device with ID {device_id} not found."

        success, msg = excel_db.delete_device(device_id)
        if success:
            excel_db.log_activity(
                user_email=user_email,
                action="Device Deleted",
                device_id=device_id,
                details=f"Deleted device {existing.get('Device_Name')} (S/N: {existing.get('Serial_Number')})."
            )
        return success, msg

    def get_all_devices_enriched(self) -> List[Dict[str, Any]]:
        """Returns all devices with calculated warranty status, remaining days, and display properties."""
        devices = excel_db.get_devices()
        enriched = []
        for d in devices:
            item = dict(d)
            status_info = warranty_checker.calculate_status(d.get("Warranty_End_Date"))
            item.update(status_info)
            enriched.append(item)
        return enriched

    def search_and_filter(
        self,
        query: str = "",
        category: str = "",
        department: str = "",
        status: str = "",
        sort_by: str = "Warranty_End_Date",
        sort_order: str = "asc"
    ) -> List[Dict[str, Any]]:
        """
        Searches devices by name, serial number, brand, model, assigned user, or department.
        Filters by category, department, and warranty status.
        Sorts by specified column.
        """
        devices = self.get_all_devices_enriched()

        # Text search
        if query:
            q = query.strip().lower()
            filtered = []
            for d in devices:
                match = (
                    q in str(d.get("Device_Name", "")).lower() or
                    q in str(d.get("Serial_Number", "")).lower() or
                    q in str(d.get("Device_ID", "")).lower() or
                    q in str(d.get("Brand", "")).lower() or
                    q in str(d.get("Model_Number", "")).lower() or
                    q in str(d.get("Assigned_User", "")).lower() or
                    q in str(d.get("Department", "")).lower()
                )
                if match:
                    filtered.append(d)
            devices = filtered

        # Filter by Category
        if category and category.lower() != "all":
            devices = [d for d in devices if str(d.get("Category", "")).lower() == category.lower()]

        # Filter by Department
        if department and department.lower() != "all":
            devices = [d for d in devices if str(d.get("Department", "")).lower() == department.lower()]

        # Filter by Status
        if status and status.lower() != "all":
            devices = [d for d in devices if str(d.get("status", "")).lower() == status.lower()]

        # Sorting
        reverse = (sort_order.lower() == "desc")
        if sort_by == "Warranty_End_Date":
            devices.sort(
                key=lambda x: str(x.get("Warranty_End_Date", "")),
                reverse=reverse
            )
        elif sort_by == "days_remaining":
            devices.sort(
                key=lambda x: x.get("days_remaining") if x.get("days_remaining") is not None else 999999,
                reverse=reverse
            )
        elif sort_by == "Device_Name":
            devices.sort(
                key=lambda x: str(x.get("Device_Name", "")).lower(),
                reverse=reverse
            )
        elif sort_by == "Created_At":
            devices.sort(
                key=lambda x: str(x.get("Created_At", "")),
                reverse=reverse
            )

        return devices

    def _get_default_category_image(self, category: Optional[str]) -> str:
        """Returns clean stock product images based on device category."""
        category_images = {
            "Laptop": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=300",
            "Desktop": "https://images.unsplash.com/photo-1587831990711-23ca6441447b?w=300",
            "Printer": "https://images.unsplash.com/photo-1612815154858-60aa4c59eaa6?w=300",
            "Monitor": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=300",
            "Router": "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=300",
            "CCTV": "https://images.unsplash.com/photo-1557597774-9d273605dfa9?w=300",
            "UPS": "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=300",
            "Mobile Phone": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=300",
            "Other": "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=300"
        }
        return category_images.get(category, "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=300")


# Singleton instance
device_manager = DeviceManager()
