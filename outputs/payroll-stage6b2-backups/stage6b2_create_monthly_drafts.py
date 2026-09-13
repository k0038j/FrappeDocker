import json

import frappe


PAYROLL_ENTRY = "HR-PRUN-2026-00001"
QUINCENAL_ENTRY = "HR-PRUN-2026-00002"
AUGUSTO = "HR-EMP-00002"
EXPECTED = {
    "employees": 15,
    "gross": 331480.77,
    "inss": 23203.65,
    "ir": 31296.95,
    "net": 276980.17,
}
ATTENDANCE_CASES = {
    "HR-EMP-00003": {"working": 26.0, "payment": 25.0, "absent": 1.0, "lwp": 0.0},
    "HR-EMP-00006": {"working": 26.0, "payment": 25.5, "absent": 0.0, "lwp": 0.5},
}


def close_enough(actual, expected, tolerance=0.05):
    return abs(float(actual or 0) - float(expected)) <= tolerance


def component_amount(rows, component):
    return sum(float(row.amount or 0) for row in rows if row.salary_component == component)


def run():
    entry = frappe.get_doc("Payroll Entry", PAYROLL_ENTRY)
    if (
        entry.docstatus != 0
        or entry.status != "Draft"
        or entry.salary_slips_created
        or str(entry.start_date) != "2026-09-01"
        or str(entry.end_date) != "2026-09-30"
        or str(entry.posting_date) != "2026-09-30"
        or entry.payroll_frequency != "Monthly"
        or entry.company != "CYCE, S.A."
    ):
        raise RuntimeError(f"Unexpected Payroll Entry state: {entry.as_dict()}")

    if frappe.db.count(
        "Salary Slip", {"payroll_entry": QUINCENAL_ENTRY, "docstatus": 0}
    ) != 23:
        raise RuntimeError("Expected the 23 quincenal Salary Slips to remain in draft")
    if frappe.db.count("Salary Slip", {"payroll_entry": PAYROLL_ENTRY, "docstatus": ["!=", 2]}):
        raise RuntimeError("Monthly Salary Slips already exist; stage aborted")

    employees = sorted({row.employee for row in entry.employees})
    if len(employees) != EXPECTED["employees"]:
        raise RuntimeError(f"Expected 15 employees, found {len(employees)}")
    if AUGUSTO in employees:
        raise RuntimeError("Augusto must not be included in payroll")

    journal_entries_before = frappe.db.count("Journal Entry")
    email_queue_before = frappe.db.count("Email Queue")
    created = []
    totals = {"gross": 0.0, "inss": 0.0, "ir": 0.0, "net": 0.0}
    attendance_results = []

    try:
        for employee in employees:
            slip = frappe.get_doc(
                {
                    "doctype": "Salary Slip",
                    "employee": employee,
                    "salary_slip_based_on_timesheet": entry.salary_slip_based_on_timesheet,
                    "payroll_frequency": entry.payroll_frequency,
                    "start_date": entry.start_date,
                    "end_date": entry.end_date,
                    "company": entry.company,
                    "posting_date": entry.posting_date,
                    "deduct_tax_for_unsubmitted_tax_exemption_proof": (
                        entry.deduct_tax_for_unsubmitted_tax_exemption_proof
                    ),
                    "payroll_entry": entry.name,
                    "exchange_rate": entry.exchange_rate,
                    "currency": entry.currency,
                }
            )
            slip.insert(ignore_permissions=True)
            created.append(slip.name)

            if slip.docstatus != 0 or slip.payroll_entry != PAYROLL_ENTRY:
                raise RuntimeError(f"Salary Slip was not created as draft: {slip.name}")

            inss = component_amount(slip.deductions, "INSS Laboral")
            ir = component_amount(slip.deductions, "IR Laboral")
            totals["gross"] += float(slip.gross_pay or 0)
            totals["inss"] += inss
            totals["ir"] += ir
            totals["net"] += float(slip.net_pay or 0)

            expected_days = ATTENDANCE_CASES.get(
                employee,
                {"working": 26.0, "payment": 26.0, "absent": 0.0, "lwp": 0.0},
            )
            for field, actual in (
                ("working", slip.total_working_days),
                ("payment", slip.payment_days),
                ("absent", slip.absent_days),
                ("lwp", slip.leave_without_pay),
            ):
                if not close_enough(actual, expected_days[field], tolerance=0.02):
                    raise RuntimeError(
                        f"Attendance mismatch on {slip.name}: {field}={actual}, "
                        f"expected={expected_days[field]}"
                    )

            if employee in ATTENDANCE_CASES:
                attendance_results.append(
                    {
                        "employee": employee,
                        "salary_slip": slip.name,
                        "working_days": float(slip.total_working_days),
                        "payment_days": float(slip.payment_days),
                        "absent_days": float(slip.absent_days),
                        "lwp_days": float(slip.leave_without_pay),
                        "gross": round(float(slip.gross_pay or 0), 2),
                        "inss": round(inss, 2),
                        "ir": round(ir, 2),
                        "net": round(float(slip.net_pay or 0), 2),
                    }
                )

        for key in totals:
            totals[key] = round(totals[key], 2)
            if not close_enough(totals[key], EXPECTED[key]):
                raise RuntimeError(
                    f"Aggregate mismatch: {key}={totals[key]}, expected={EXPECTED[key]}"
                )

        if frappe.db.count("Salary Slip", {"payroll_entry": PAYROLL_ENTRY, "docstatus": 0}) != 15:
            raise RuntimeError("Expected exactly 15 monthly draft Salary Slips")
        if frappe.db.count("Salary Slip", {"docstatus": 0}) != 38:
            raise RuntimeError("Expected exactly 38 total draft Salary Slips")
        if frappe.db.count(
            "Salary Slip", {"employee": AUGUSTO, "docstatus": ["!=", 2]}
        ):
            raise RuntimeError("Augusto was unexpectedly included")
        if frappe.db.count("Journal Entry") != journal_entries_before:
            raise RuntimeError("Journal Entries were unexpectedly created")
        if frappe.db.count("Email Queue") != email_queue_before:
            raise RuntimeError("Emails were unexpectedly queued")

        entry.db_set(
            {"status": "Submitted", "salary_slips_created": 1, "error_message": ""},
            update_modified=True,
        )
        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        raise

    print(
        json.dumps(
            {
                "stage": "6B.2",
                "payroll_entry": PAYROLL_ENTRY,
                "salary_slips_created": len(created),
                "total_draft_salary_slips": 38,
                "docstatus": 0,
                "totals": totals,
                "attendance_cases": attendance_results,
                "augusto_included": False,
                "journal_entries_created": 0,
                "emails_sent": 0,
            },
            ensure_ascii=False,
        )
    )


run()
