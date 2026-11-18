"""
Warranty Calculation & Milestone Alert Engine.
Dynamically computes remaining days, status, and milestone notifications (30, 14, 7, 3, 0 days).
Enforces strict de-duplication so no duplicate alert is generated for the same device & milestone.
"""

import uuid
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Tuple, Optional

import config

logger = logging.getLogger(__name__)


def parse_date(date_val: Any) -> Optional[date]:
    """Parses various date formats safely into a datetime.date object."""
    if not date_val:
        return None
    if isinstance(date_val, date) and not isinstance(date_val, datetime):
        return date_val
    if isinstance(date_val, datetime):
        return date_val.date()

    date_str = str(date_val).strip()
    if not date_str:
        return None

    # Handle ISO formats and common date formats
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str[:19], fmt).date()
        except ValueError:
            continue
    return None


class WarrantyChecker:
    @staticmethod
    def calculate_status(warranty_end_date_val: Any, as_of_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Calculates dynamic warranty status, remaining days, and UI presentation tags.
        - Active: > 30 days
        - Expiring Soon: 0 <= days <= 30
        - Expired: days < 0
        """
        target_today = as_of_date or date.today()
        end_date = parse_date(warranty_end_date_val)

        if not end_date:
            return {
                "status": "Unknown",
                "days_remaining": None,
                "urgency": "low",
                "badge_class": "badge-secondary",
                "countdown_text": "No warranty date",
                "is_expired": False,
                "is_urgent": False
            }

        days_remaining = (end_date - target_today).days

        if days_remaining < 0:
            status = "Expired"
            urgency = "critical"
            badge_class = "badge-danger"
            days_ago = abs(days_remaining)
            countdown_text = f"Expired {days_ago} day{'s' if days_ago != 1 else ''} ago"
            is_expired = True
            is_urgent = True
        elif days_remaining <= 3:
            status = "Expiring Soon"
            urgency = "critical"
            badge_class = "badge-danger"
            countdown_text = "Expires today!" if days_remaining == 0 else f"Expires in {days_remaining} day{'s' if days_remaining != 1 else ''}"
            is_expired = False
            is_urgent = True
        elif days_remaining <= 7:
            status = "Expiring Soon"
            urgency = "high"
            badge_class = "badge-warning"
            countdown_text = f"Expires in {days_remaining} days"
            is_expired = False
            is_urgent = True
        elif days_remaining <= config.WARRANTY_EXPIRING_SOON_DAYS:  # 30 days
            status = "Expiring Soon"
            urgency = "medium" if days_remaining <= 14 else "low"
            badge_class = "badge-warning"
            countdown_text = f"Expires in {days_remaining} days"
            is_expired = False
            is_urgent = False
        else:
            status = "Active"
            urgency = "low"
            badge_class = "badge-success"
            countdown_text = f"{days_remaining} days remaining"
            is_expired = False
            is_urgent = False

        return {
            "status": status,
            "days_remaining": days_remaining,
            "urgency": urgency,
            "badge_class": badge_class,
            "countdown_text": countdown_text,
            "is_expired": is_expired,
            "is_urgent": is_urgent,
            "formatted_end_date": end_date.strftime("%b %d, %Y")
        }

    @staticmethod
    def evaluate_devices_for_notifications(
        devices: List[Dict[str, Any]],
        existing_notifications: List[Dict[str, Any]],
        as_of_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Scans all devices against milestone thresholds (30, 14, 7, 3, 0 days).
        Ensures strict de-duplication: checks existing notifications so no duplicate
        alert is generated for the exact same device and milestone!
        """
        target_today = as_of_date or date.today()
        new_notifications = []

        # Build de-duplication lookup set: (device_id, milestone)
        existing_keys = set()
        for notif in existing_notifications:
            d_id = str(notif.get("Device_ID", "")).strip().upper()
            m_stone = str(notif.get("Milestone", "")).strip().lower()
            if d_id and m_stone:
                existing_keys.add((d_id, m_stone))

        milestones = [30, 14, 7, 3, 0]

        for device in devices:
            device_id = str(device.get("Device_ID", "")).strip().upper()
            device_name = device.get("Device_Name", "Unknown Device")
            serial_number = device.get("Serial_Number", "N/A")
            end_date_val = device.get("Warranty_End_Date")

            end_date = parse_date(end_date_val)
            if not end_date or not device_id:
                continue

            days_remaining = (end_date - target_today).days

            # Determine applicable milestones
            for milestone_days in milestones:
                milestone_key = f"{milestone_days}_days" if milestone_days > 0 else "expired"

                # Check if this milestone has already been sent for this device
                if (device_id, milestone_key) in existing_keys:
                    continue

                # Condition to trigger notification:
                # - For 30 days: triggered when days_remaining <= 30
                # - For 14 days: triggered when days_remaining <= 14
                # - For 7 days: triggered when days_remaining <= 7
                # - For 3 days: triggered when days_remaining <= 3
                # - For expired: triggered when days_remaining <= 0
                should_trigger = False
                if milestone_days == 0 and days_remaining <= 0:
                    should_trigger = True
                elif milestone_days > 0 and days_remaining <= milestone_days:
                    should_trigger = True

                if should_trigger:
                    urgency = config.MILESTONE_URGENCY.get(milestone_days, "medium")
                    if milestone_days == 0:
                        msg = f"Warranty for {device_name} (S/N: {serial_number}) expired on {end_date.strftime('%b %d, %Y')}."
                    else:
                        msg = f"Warranty for {device_name} (S/N: {serial_number}) expires in {days_remaining} day{'s' if days_remaining != 1 else ''} ({end_date.strftime('%b %d, %Y')})."

                    notification_record = {
                        "Notification_ID": f"NOTIF-{uuid.uuid4().hex[:8].upper()}",
                        "Device_ID": device_id,
                        "Device_Name": device_name,
                        "Serial_Number": serial_number,
                        "Milestone": milestone_key,
                        "Notification_Date": datetime.now().isoformat(),
                        "Warranty_End_Date": end_date.isoformat(),
                        "Days_Remaining": days_remaining,
                        "Message": msg,
                        "Urgency": urgency,
                        "Status": "unread"
                    }

                    new_notifications.append(notification_record)
                    # Mark in existing keys so we don't repeat in this same batch
                    existing_keys.add((device_id, milestone_key))

        return new_notifications


warranty_checker = WarrantyChecker()
