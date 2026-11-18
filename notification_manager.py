"""
Notification Manager for Device Warranty Management System.
Orchestrates warranty checks, unread badge counters, urgent notifications,
browser notifications, and notification status updates.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple

from excel_database import excel_db
from warranty_checker import warranty_checker, parse_date

logger = logging.getLogger(__name__)


class NotificationManager:
    def __init__(self):
        self._last_check_timestamp = None

    def run_check(self) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Executes warranty check across all devices in the database.
        Detects milestones (30, 14, 7, 3, 0 days), de-duplicates, and persists new alerts.
        Returns: (count_of_new_notifications, list_of_new_notifications)
        """
        devices = excel_db.get_devices()
        existing_notifications = excel_db.get_notifications()

        new_notifs = warranty_checker.evaluate_devices_for_notifications(devices, existing_notifications)
        if new_notifs:
            saved_count = excel_db.save_notifications_batch(new_notifs)
            logger.info(f"Generated and saved {saved_count} new milestone notifications.")
            self._last_check_timestamp = datetime.now()
            return saved_count, new_notifs

        self._last_check_timestamp = datetime.now()
        return 0, []

    def get_notifications(self, unread_only: bool = False, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Returns notifications enriched with display metadata (formatted dates, icons, CSS classes).
        Sorted newest first.
        """
        raw_notifs = excel_db.get_notifications()
        # Sort newest first
        sorted_notifs = sorted(
            raw_notifs,
            key=lambda x: str(x.get("Notification_Date", "")),
            reverse=True
        )

        formatted = []
        for n in sorted_notifs:
            status = str(n.get("Status", "unread")).strip().lower()
            if unread_only and status != "unread":
                continue

            urgency = str(n.get("Urgency", "medium")).strip().lower()
            if urgency == "critical":
                badge_class = "badge-danger"
                icon = "alert-circle"
            elif urgency == "high":
                badge_class = "badge-warning"
                icon = "alert-triangle"
            elif urgency == "medium":
                badge_class = "badge-info"
                icon = "bell"
            else:
                badge_class = "badge-secondary"
                icon = "info"

            # Parse notification date for relative display
            notif_date_str = str(n.get("Notification_Date", ""))
            formatted_date = notif_date_str[:10]
            try:
                dt = datetime.fromisoformat(notif_date_str)
                formatted_date = dt.strftime("%b %d, %Y %I:%M %p")
            except Exception:
                pass

            item = dict(n)
            item["badge_class"] = badge_class
            item["icon"] = icon
            item["formatted_date"] = formatted_date
            item["is_unread"] = (status == "unread")
            formatted.append(item)

            if len(formatted) >= limit:
                break

        return formatted

    def get_unread_count(self) -> int:
        """Returns the number of unread notifications for badge display."""
        raw_notifs = excel_db.get_notifications()
        return sum(1 for n in raw_notifs if str(n.get("Status", "unread")).strip().lower() == "unread")

    def get_urgent_notifications(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Returns top urgent unread notifications (critical/high)."""
        notifs = self.get_notifications(unread_only=True)
        urgent = [n for n in notifs if n.get("Urgency") in ("critical", "high")]
        return urgent[:limit]

    def mark_as_read(self, notification_id: str) -> bool:
        """Marks a specific notification as read."""
        return excel_db.mark_notification_read(notification_id)

    def mark_all_as_read(self) -> int:
        """Marks all unread notifications as read."""
        return excel_db.mark_all_notifications_read()


# Singleton instance
notification_manager = NotificationManager()
