import json

import frappe


COMPANY = "CYCE, S.A."
HOLIDAY_LIST = "Calendario Laboral CYCE 2026 - Prueba"
FROM_DATE = "2026-01-01"
TO_DATE = "2026-12-31"


def run():
    if frappe.db.exists("Holiday List", HOLIDAY_LIST):
        raise RuntimeError(f"Holiday List already exists: {HOLIDAY_LIST}")
    if frappe.db.exists(
        "Holiday List Assignment", {"assigned_to": COMPANY, "docstatus": 1}
    ):
        raise RuntimeError("A submitted Holiday List Assignment already exists for CYCE")
    if frappe.db.count("Salary Slip") != 0:
        raise RuntimeError("Salary Slips already exist; adjustment aborted")

    settings = frappe.get_single("Payroll Settings")
    if (
        settings.payroll_based_on != "Attendance"
        or settings.consider_unmarked_attendance_as != "Present"
    ):
        raise RuntimeError("Payroll Settings are not in the approved Attendance configuration")
    if frappe.db.count(
        "Attendance",
        {"attendance_date": ["between", ["2026-09-01", "2026-09-30"]], "docstatus": 1},
    ) != 4:
        raise RuntimeError("Expected exactly four submitted September Attendance records")

    payroll_entries = frappe.get_all(
        "Payroll Entry", fields=["name", "docstatus", "number_of_employees"], order_by="name"
    )
    if (
        len(payroll_entries) != 2
        or any(row.docstatus != 0 for row in payroll_entries)
        or [row.number_of_employees for row in payroll_entries] != [15, 23]
    ):
        raise RuntimeError(f"Payroll Entry state changed: {payroll_entries}")

    journal_count_before = frappe.db.count("Journal Entry")
    assignment_name = None

    try:
        holiday_list = frappe.get_doc(
            {
                "doctype": "Holiday List",
                "holiday_list_name": HOLIDAY_LIST,
                "from_date": FROM_DATE,
                "to_date": TO_DATE,
                "weekly_off": "Sunday",
                "is_half_day": 0,
            }
        )
        holiday_list.get_weekly_off_dates()
        if len(holiday_list.holidays) != 52:
            raise RuntimeError(f"Expected 52 Sundays, found {len(holiday_list.holidays)}")
        if any(
            not row.weekly_off or row.holiday_date.weekday() != 6
            for row in holiday_list.holidays
        ):
            raise RuntimeError("Holiday List contains a non-Sunday or non-weekly-off row")
        holiday_list.insert(ignore_permissions=True)

        assignment = frappe.get_doc(
            {
                "doctype": "Holiday List Assignment",
                "naming_series": "HR-HLA-.YYYY.-",
                "applicable_for": "Company",
                "assigned_to": COMPANY,
                "holiday_list": HOLIDAY_LIST,
                "from_date": FROM_DATE,
            }
        )
        assignment.insert(ignore_permissions=True)
        assignment.submit()
        assignment_name = assignment.name

        holiday_state = frappe.db.get_value(
            "Holiday List", HOLIDAY_LIST, ["from_date", "to_date", "total_holidays"], as_dict=True
        )
        if (
            not holiday_state
            or str(holiday_state.from_date) != FROM_DATE
            or str(holiday_state.to_date) != TO_DATE
            or holiday_state.total_holidays != 52
        ):
            raise RuntimeError(f"Holiday List verification failed: {holiday_state}")
        assignment_state = frappe.db.get_value(
            "Holiday List Assignment",
            assignment_name,
            ["docstatus", "applicable_for", "assigned_to", "holiday_list", "from_date"],
            as_dict=True,
        )
        if (
            assignment_state.docstatus != 1
            or assignment_state.applicable_for != "Company"
            or assignment_state.assigned_to != COMPANY
            or assignment_state.holiday_list != HOLIDAY_LIST
            or str(assignment_state.from_date) != FROM_DATE
        ):
            raise RuntimeError(f"Holiday List Assignment verification failed: {assignment_state}")
        if frappe.db.count("Salary Slip") != 0:
            raise RuntimeError("Adjustment unexpectedly created Salary Slips")
        if frappe.db.count("Journal Entry") != journal_count_before:
            raise RuntimeError("Adjustment unexpectedly changed Journal Entry count")

        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        raise

    print(
        json.dumps(
            {
                "holiday_list": HOLIDAY_LIST,
                "weekly_off": "Sunday",
                "sundays": 52,
                "assignment": assignment_name,
                "assigned_to": COMPANY,
                "salary_slips": 0,
                "journal_entries_created": 0,
            },
            ensure_ascii=False,
        )
    )


run()
