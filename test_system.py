"""
Comprehensive Automated Test Suite for EquipGuard Device Warranty Management System.
Validates database integrity, CRUD operations, warranty math, de-duplication,
PDF generation, Excel exports, and authentication.
"""

import sys
from pathlib import Path
from datetime import date, timedelta

# Ensure warranty_system is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config
from excel_database import excel_db
from warranty_checker import warranty_checker, parse_date
from notification_manager import notification_manager
from device_manager import device_manager
from reports import report_service
from firebase_auth import auth_service
from google_drive import drive_service


def test_database_initialization():
    print("Testing Excel Database initialization...")
    excel_db.init_database(force_refresh=True)
    assert config.LOCAL_DB_PATH.exists(), "Local database file does not exist!"

    devices = excel_db.get_devices()
    print(f"✓ Initialized with {len(devices)} devices in {config.SHEET_DEVICES}.")
    assert len(devices) >= 8, f"Expected at least 8 seed devices, got {len(devices)}"

    logs = excel_db.get_activity_logs()
    print(f"✓ Initialized with {len(logs)} activity log entries.")
    assert len(logs) >= 1, "Expected activity logs."

    setting = excel_db.get_setting("system_name")
    print(f"✓ Settings check: system_name = '{setting}'")
    assert setting == config.APP_NAME


def test_warranty_calculation_and_deduplication():
    print("\nTesting Warranty Calculation & De-duplication Engine...")
    today = date.today()

    # Active device (> 30 days)
    res_active = warranty_checker.calculate_status(today + timedelta(days=45))
    assert res_active["status"] == "Active"
    assert res_active["days_remaining"] == 45
    print("✓ Active calculation (> 30d) passed.")

    # Expiring soon (10 days)
    res_soon = warranty_checker.calculate_status(today + timedelta(days=10))
    assert res_soon["status"] == "Expiring Soon"
    assert res_soon["days_remaining"] == 10
    print("✓ Expiring soon calculation (10d) passed.")

    # Expired device (-5 days)
    res_exp = warranty_checker.calculate_status(today - timedelta(days=5))
    assert res_exp["status"] == "Expired"
    assert res_exp["days_remaining"] == -5
    print("✓ Expired calculation (-5d) passed.")

    # Milestone de-duplication test
    mock_devices = [
        {
            "Device_ID": "TEST-001",
            "Device_Name": "Test Laptop",
            "Serial_Number": "SN-TEST-12345",
            "Warranty_End_Date": (today + timedelta(days=5)).isoformat()
        }
    ]
    # First evaluation: should trigger milestone 30, 14, 7
    first_pass = warranty_checker.evaluate_devices_for_notifications(mock_devices, [])
    assert len(first_pass) == 3, f"Expected 3 milestones (30, 14, 7), got {len(first_pass)}"
    print(f"✓ First evaluation generated {len(first_pass)} milestones.")

    # Second evaluation passing the existing notifications: must return 0 new notifications!
    second_pass = warranty_checker.evaluate_devices_for_notifications(mock_devices, first_pass)
    assert len(second_pass) == 0, f"De-duplication failed! Expected 0 duplicates, got {len(second_pass)}"
    print("✓ De-duplication verified: 0 duplicates generated on subsequent evaluation.")


def test_device_crud_and_validation():
    print("\nTesting Device Manager CRUD & Validation...")
    today = date.today()

    # Test duplicate serial rejection
    invalid_data = {
        "Device_Name": "Duplicate Tester",
        "Category": "Laptop",
        "Serial_Number": "C02G87Y9MD6R",  # Already in seed devices (DEV-1001)
        "Warranty_Start_Date": today.isoformat(),
        "Warranty_End_Date": (today + timedelta(days=365)).isoformat()
    }
    valid, msg = device_manager.validate_device_input(invalid_data)
    assert not valid, "Failed to reject duplicate serial number!"
    print(f"✓ Duplicate serial prevention passed: '{msg}'")

    # Add a valid new device
    new_data = {
        "Device_Name": "Surface Laptop Studio 2",
        "Category": "Laptop",
        "Brand": "Microsoft",
        "Model_Number": "SLS-2024",
        "Serial_Number": "SN-SURFACE-9988",
        "Assigned_User": "Rachel Green",
        "Department": "Operations",
        "Purchase_Date": (today - timedelta(days=10)).isoformat(),
        "Purchase_Price": 2399.00,
        "Supplier": "Microsoft Direct",
        "Warranty_Start_Date": today.isoformat(),
        "Warranty_End_Date": (today + timedelta(days=365)).isoformat(),
        "Notes": "Unit for operations coordinator."
    }
    success, msg, added = device_manager.add_device(new_data, "admin@equipguard.io")
    assert success, f"Failed to add device: {msg}"
    device_id = added["Device_ID"]
    print(f"✓ Successfully added device: {device_id} ({added['Device_Name']})")

    # Verify device exists in database
    retrieved = excel_db.get_device_by_id(device_id)
    assert retrieved is not None
    assert retrieved["Serial_Number"] == "SN-SURFACE-9988"
    print(f"✓ Verified device {device_id} retrieved correctly from Excel.")

    # Update device
    update_data = dict(retrieved)
    update_data["Department"] = "Finance"
    success_up, msg_up, updated = device_manager.update_device(device_id, update_data, "admin@equipguard.io")
    assert success_up, f"Failed to update device: {msg_up}"
    assert excel_db.get_device_by_id(device_id)["Department"] == "Finance"
    print(f"✓ Successfully updated device {device_id} department to Finance.")

    # Delete device
    success_del, msg_del = device_manager.delete_device(device_id, "admin@equipguard.io")
    assert success_del, f"Failed to delete device: {msg_del}"
    assert excel_db.get_device_by_id(device_id) is None
    print(f"✓ Successfully deleted device {device_id} and verified removal.")


def test_notifications_lifecycle():
    print("\nTesting Notification Manager Lifecycle...")
    count, notifs = notification_manager.run_check()
    print(f"✓ Warranty check completed. New notifications saved: {count}")

    unread = notification_manager.get_unread_count()
    print(f"✓ Total unread notifications: {unread}")

    if unread > 0:
        notif_list = notification_manager.get_notifications(unread_only=True)
        first_id = notif_list[0]["Notification_ID"]
        marked = notification_manager.mark_as_read(first_id)
        assert marked, f"Failed to mark notification {first_id} as read."
        print(f"✓ Marked individual notification {first_id} as read.")

    all_marked = notification_manager.mark_all_as_read()
    print(f"✓ Marked all remaining notifications as read (count: {all_marked}).")
    assert notification_manager.get_unread_count() == 0, "Expected 0 unread notifications after mark all."


def test_reports_excel_and_pdf():
    print("\nTesting Reports, Excel Export & PDF Generation...")
    devices = device_manager.get_all_devices_enriched()
    summary = report_service.get_analytics_summary()

    print(f"✓ Analytics summary: Total Devices={summary['total_devices']}, Active={summary['active_warranties']} ({summary['active_percentage']}%), Expiring Soon={summary['expiring_soon']}, Expired={summary['expired_warranties']}.")
    print(f"✓ Expiration Horizons: ≤30d={summary['expiring_30_days']}, ≤60d={summary['expiring_60_days']}, ≤90d={summary['expiring_90_days']}.")

    # Generate Excel Report
    excel_path = config.REPORTS_DIR / "test_report.xlsx"
    excel_bytes = report_service.generate_excel_report(devices, str(excel_path))
    assert len(excel_bytes) > 1000, "Generated Excel report is empty or invalid!"
    assert excel_path.exists(), "Excel report file not created!"
    print(f"✓ Excel report generated successfully ({len(excel_bytes)} bytes) at {excel_path}.")

    # Generate PDF Audit Report
    pdf_path = config.REPORTS_DIR / "test_report.pdf"
    pdf_bytes = report_service.generate_pdf_report(devices, summary, str(pdf_path))
    assert len(pdf_bytes) > 2000, "Generated PDF report is empty or invalid!"
    assert pdf_path.exists(), "PDF report file not created!"
    print(f"✓ PDF report generated successfully ({len(pdf_bytes)} bytes) at {pdf_path}.")


def test_authentication_service():
    print("\nTesting Firebase Authentication Service (Demo Fallback & REST)...")
    # Valid Demo Admin
    ok, msg, user = auth_service.sign_in("admin@equipguard.io", "Password123!")
    assert ok, f"Admin login failed: {msg}"
    assert user["email"] == "admin@equipguard.io"
    print(f"✓ Admin sign-in successful: {user['display_name']} ({user['role']}).")

    # Invalid Password
    bad_ok, bad_msg, _ = auth_service.sign_in("admin@equipguard.io", "WrongPassword!")
    assert not bad_ok, "Failed to reject invalid password!"
    print(f"✓ Invalid password properly rejected: '{bad_msg}'.")

    # Non-existent user
    none_ok, none_msg, _ = auth_service.sign_in("ghost@company.com", "Password123!")
    assert not none_ok, "Failed to reject unknown user!"
    print(f"✓ Unknown user properly rejected: '{none_msg}'.")


if __name__ == "__main__":
    print("=" * 70)
    print("EQUIPGUARD AUTOMATED SYSTEM AUDIT & INTEGRITY SUITE")
    print("=" * 70)

    try:
        test_database_initialization()
        test_warranty_calculation_and_deduplication()
        test_device_crud_and_validation()
        test_notifications_lifecycle()
        test_reports_excel_and_pdf()
        test_authentication_service()
        print("\n" + "=" * 70)
        print("ALL TESTS PASSED! APPLICATION IS 100% OPERATIONAL AND COMPLIANT.")
        print("=" * 70)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
