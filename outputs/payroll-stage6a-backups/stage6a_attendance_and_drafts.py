import json

import frappe


COMPANY = "CYCE, S.A."
CURRENCY = "NIO"
PAYROLL_PAYABLE = "2121 - Sueldos y Salarios por Pagar - CYCE"
COST_CENTER = "Principal - CYCE"
MONTHLY_GRADE = "Nomina Mensual INSS"
BIMONTHLY_GRADE = "Nomina Quincenal INSS"
MONTHLY_ENTRY = "HR-PRUN-2026-00001"
EXCLUDED_EMPLOYEE = "HR-EMP-00002"

ATTENDANCE = (
    ("HR-EMP-00003", "2026-09-03", "Absent", None, None),
    ("HR-EMP-00006", "2026-09-10", "Half Day", "Leave Without Pay", "Absent"),
    ("HR-EMP-00017", "2026-09-04", "Absent", None, None),
    ("HR-EMP-00031", "2026-09-08", "Half Day", "Leave Without Pay", "Absent"),
)


def active_employees_for_grade(grade):
    return set(
        frappe.get_all(
            "Employee",
            filters={"status": "Active", "grade": grade},
            pluck="name",
        )
    )


def payroll_employee_set(payroll_entry):
    return {row.employee for row in payroll_entry.employees}


def run():
    if frappe.db.count("Salary Slip") != 0:
        raise RuntimeError("Salary Slips already exist; Stage 6A aborted")
    if frappe.db.count("Salary Structure Assignment", {"docstatus": 1}) != 38:
        raise RuntimeError("Expected 38 submitted Salary Structure Assignments")
    if frappe.db.get_value("Employee", EXCLUDED_EMPLOYEE, "grade"):
        raise RuntimeError("Augusto Garcia unexpectedly has an Employee Grade")
    if frappe.db.exists(
        "Salary Structure Assignment", {"employee": EXCLUDED_EMPLOYEE, "docstatus": 1}
    ):
        raise RuntimeError("Augusto Garcia unexpectedly has a Salary Structure Assignment")

    monthly_employees = active_employees_for_grade(MONTHLY_GRADE)
    bimonthly_employees = active_employees_for_grade(BIMONTHLY_GRADE)
    if len(monthly_employees) != 15 or len(bimonthly_employees) != 23:
        raise RuntimeError(
            f"Unexpected employee distribution: monthly={len(monthly_employees)}, "
            f"bimonthly={len(bimonthly_employees)}"
        )
    if monthly_employees & bimonthly_employees:
        raise RuntimeError("Employee appears in both payroll grades")

    existing_entries = frappe.get_all("Payroll Entry", fields=["name", "docstatus"])
    if len(existing_entries) != 1 or existing_entries[0].name != MONTHLY_ENTRY:
        raise RuntimeError(f"Unexpected Payroll Entry set: {existing_entries}")

    monthly_entry = frappe.get_doc("Payroll Entry", MONTHLY_ENTRY)
    if monthly_entry.docstatus != 0 or monthly_entry.salary_slips_created or monthly_entry.employees:
        raise RuntimeError("Existing monthly Payroll Entry is no longer an empty draft")
    if (
        monthly_entry.company != COMPANY
        or monthly_entry.payroll_frequency != "Monthly"
        or str(monthly_entry.start_date) != "2026-09-01"
        or str(monthly_entry.end_date) != "2026-09-30"
    ):
        raise RuntimeError("Existing monthly Payroll Entry dates or company changed")

    if frappe.db.count(
        "Attendance",
        {"attendance_date": ["between", ["2026-09-01", "2026-09-30"]], "docstatus": ["<", 2]},
    ):
        raise RuntimeError("September Attendance records already exist; Stage 6A aborted")

    payroll_settings = frappe.get_single("Payroll Settings")
    current_payroll_basis = payroll_settings.payroll_based_on or "Leave"
    current_unmarked_rule = payroll_settings.consider_unmarked_attendance_as or "Present"
    if current_payroll_basis not in ("Leave", "Attendance"):
        raise RuntimeError(f"Unexpected payroll basis: {current_payroll_basis}")
    if current_unmarked_rule not in ("Present", "Absent"):
        raise RuntimeError(f"Unexpected unmarked attendance rule: {current_unmarked_rule}")

    journal_count_before = frappe.db.count("Journal Entry")
    created_attendance = []
    quincenal_entry_name = None

    try:
        payroll_settings.payroll_based_on = "Attendance"
        payroll_settings.consider_unmarked_attendance_as = "Present"
        payroll_settings.save(ignore_permissions=True)

        for employee, attendance_date, status, leave_type, half_day_status in ATTENDANCE:
            attendance = frappe.get_doc(
                {
                    "doctype": "Attendance",
                    "employee": employee,
                    "attendance_date": attendance_date,
                    "company": COMPANY,
                    "status": status,
                    "leave_type": leave_type,
                    "half_day_status": half_day_status,
                }
            )
            attendance.insert(ignore_permissions=True)
            attendance.submit()
            created_attendance.append(attendance.name)

        monthly_entry.posting_date = "2026-09-30"
        monthly_entry.grade = MONTHLY_GRADE
        monthly_entry.cost_center = COST_CENTER
        monthly_entry.payroll_payable_account = PAYROLL_PAYABLE
        monthly_entry.currency = CURRENCY
        monthly_entry.exchange_rate = 1
        monthly_entry.validate_attendance = 0
        monthly_entry.fill_employee_details()
        monthly_entry.save(ignore_permissions=True)

        quincenal_entry = frappe.get_doc(
            {
                "doctype": "Payroll Entry",
                "company": COMPANY,
                "posting_date": "2026-09-15",
                "payroll_frequency": "Bimonthly",
                "start_date": "2026-09-01",
                "end_date": "2026-09-15",
                "grade": BIMONTHLY_GRADE,
                "cost_center": COST_CENTER,
                "payroll_payable_account": PAYROLL_PAYABLE,
                "currency": CURRENCY,
                "exchange_rate": 1,
                "salary_slip_based_on_timesheet": 0,
                "validate_attendance": 0,
            }
        )
        quincenal_entry.insert(ignore_permissions=True)
        quincenal_entry.fill_employee_details()
        quincenal_entry.save(ignore_permissions=True)
        quincenal_entry_name = quincenal_entry.name

        settings_check = frappe.get_single("Payroll Settings")
        if (
            settings_check.payroll_based_on != "Attendance"
            or settings_check.consider_unmarked_attendance_as != "Present"
        ):
            raise RuntimeError("Payroll Settings verification failed")

        attendance_rows = frappe.get_all(
            "Attendance",
            filters={"name": ["in", created_attendance]},
            fields=["name", "employee", "attendance_date", "status", "leave_type", "docstatus"],
        )
        if len(attendance_rows) != 4 or any(row.docstatus != 1 for row in attendance_rows):
            raise RuntimeError(f"Attendance verification failed: {attendance_rows}")

        monthly_check = frappe.get_doc("Payroll Entry", MONTHLY_ENTRY)
        quincenal_check = frappe.get_doc("Payroll Entry", quincenal_entry_name)
        if (
            monthly_check.docstatus != 0
            or monthly_check.grade != MONTHLY_GRADE
            or monthly_check.payroll_payable_account != PAYROLL_PAYABLE
            or str(monthly_check.posting_date) != "2026-09-30"
            or payroll_employee_set(monthly_check) != monthly_employees
        ):
            raise RuntimeError("Monthly Payroll Entry verification failed")
        if (
            quincenal_check.docstatus != 0
            or quincenal_check.grade != BIMONTHLY_GRADE
            or quincenal_check.payroll_frequency != "Bimonthly"
            or str(quincenal_check.start_date) != "2026-09-01"
            or str(quincenal_check.end_date) != "2026-09-15"
            or quincenal_check.payroll_payable_account != PAYROLL_PAYABLE
            or payroll_employee_set(quincenal_check) != bimonthly_employees
        ):
            raise RuntimeError("Bimonthly Payroll Entry verification failed")
        if EXCLUDED_EMPLOYEE in payroll_employee_set(monthly_check) | payroll_employee_set(quincenal_check):
            raise RuntimeError("Augusto Garcia was unexpectedly added to a Payroll Entry")
        if frappe.db.count("Salary Slip") != 0:
            raise RuntimeError("Stage 6A unexpectedly created Salary Slips")
        if frappe.db.count("Journal Entry") != journal_count_before:
            raise RuntimeError("Stage 6A unexpectedly changed Journal Entry count")

        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        raise

    print(
        json.dumps(
            {
                "payroll_based_on": "Attendance",
                "unmarked_attendance": "Present",
                "attendance_created": created_attendance,
                "monthly_entry": MONTHLY_ENTRY,
                "monthly_employees": 15,
                "bimonthly_entry": quincenal_entry_name,
                "bimonthly_employees": 23,
                "salary_slips": 0,
                "journal_entries_created": 0,
                "augusto_in_payroll_entries": False,
            },
            ensure_ascii=False,
        )
    )


run()
