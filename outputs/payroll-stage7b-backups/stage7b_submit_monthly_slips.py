import json

import frappe


PAYROLL_ENTRY = "HR-PRUN-2026-00001"
QUINCENAL_ENTRY = "HR-PRUN-2026-00002"
AUGUSTO = "HR-EMP-00002"
EXPECTED = {"count": 15, "gross": 331480.77, "deductions": 54500.60, "net": 276980.17}


def close_enough(actual, expected, tolerance=0.05):
    return abs(float(actual or 0) - float(expected)) <= tolerance


def totals(rows):
    return {
        "gross": round(sum(float(row.gross_pay or 0) for row in rows), 2),
        "deductions": round(sum(float(row.total_deduction or 0) for row in rows), 2),
        "net": round(sum(float(row.net_pay or 0) for row in rows), 2),
    }


def run():
    entry = frappe.get_doc("Payroll Entry", PAYROLL_ENTRY)
    if (
        entry.docstatus != 0
        or entry.status != "Submitted"
        or not entry.salary_slips_created
        or entry.salary_slips_submitted
    ):
        raise RuntimeError(f"Unexpected monthly Payroll Entry state: {entry.as_dict()}")

    if frappe.db.count(
        "Salary Slip", {"payroll_entry": QUINCENAL_ENTRY, "docstatus": 1}
    ) != 23:
        raise RuntimeError("Expected all 23 quincenal Salary Slips to be submitted")

    slips = frappe.get_all(
        "Salary Slip",
        filters={"payroll_entry": PAYROLL_ENTRY, "docstatus": 0},
        fields=["name", "employee", "gross_pay", "total_deduction", "net_pay"],
        order_by="employee",
    )
    if len(slips) != EXPECTED["count"]:
        raise RuntimeError(f"Expected 15 monthly drafts, found {len(slips)}")
    if any(row.employee == AUGUSTO for row in slips):
        raise RuntimeError("Augusto must not be included")
    if any(float(row.net_pay or 0) < 0 for row in slips):
        raise RuntimeError("A Salary Slip has negative net pay")

    before_totals = totals(slips)
    for key in ("gross", "deductions", "net"):
        if not close_enough(before_totals[key], EXPECTED[key]):
            raise RuntimeError(
                f"Unexpected pre-submit total {key}: {before_totals[key]}, expected {EXPECTED[key]}"
            )

    journal_entries_before = frappe.db.count("Journal Entry")
    gl_entries_before = frappe.db.count("GL Entry")
    emails_before = frappe.db.count("Email Queue")
    submitted = []

    try:
        frappe.flags.via_payroll_entry = True
        for row in slips:
            slip = frappe.get_doc("Salary Slip", row.name)
            slip.submit()
            submitted.append(slip.name)

        if frappe.db.count("Salary Slip", {"payroll_entry": PAYROLL_ENTRY, "docstatus": 1}) != 15:
            raise RuntimeError("Expected exactly 15 submitted monthly Salary Slips")
        if frappe.db.count("Salary Slip", {"docstatus": 0}) != 0:
            raise RuntimeError("Draft Salary Slips remain after Stage 7B")
        if frappe.db.count("Salary Slip", {"docstatus": 1}) != 38:
            raise RuntimeError("Expected exactly 38 submitted Salary Slips")
        if frappe.db.count("Salary Slip", {"employee": AUGUSTO, "docstatus": ["!=", 2]}):
            raise RuntimeError("Augusto was unexpectedly included")
        if frappe.db.count("Journal Entry") != journal_entries_before:
            raise RuntimeError("Journal Entries were unexpectedly created")
        if frappe.db.count("GL Entry") != gl_entries_before:
            raise RuntimeError("GL Entries were unexpectedly created")
        if frappe.db.count("Email Queue") != emails_before:
            raise RuntimeError("Emails were unexpectedly queued")

        entry.db_set(
            {"salary_slips_submitted": 1, "status": "Submitted", "error_message": ""},
            update_modified=True,
        )
        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        raise
    finally:
        frappe.flags.via_payroll_entry = False

    final_slips = frappe.get_all(
        "Salary Slip",
        filters={"payroll_entry": PAYROLL_ENTRY, "docstatus": 1},
        fields=["gross_pay", "total_deduction", "net_pay"],
    )
    print(
        json.dumps(
            {
                "stage": "7B",
                "payroll_entry": PAYROLL_ENTRY,
                "submitted_salary_slips": len(submitted),
                "total_submitted_salary_slips": 38,
                "totals": totals(final_slips),
                "quincenal_submitted_preserved": 23,
                "augusto_included": False,
                "journal_entries_created": 0,
                "gl_entries_created": 0,
                "emails_queued": 0,
            },
            ensure_ascii=False,
        )
    )


run()
