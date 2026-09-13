import json

import frappe
from frappe.utils import get_fullname


APPROVER = "nelly@cise.com"
APPLICATIONS = ("HR-LAP-2026-00001", "HR-LAP-2026-00002")


def run():
    user = frappe.get_doc("User", APPROVER)
    if not user.enabled or user.user_type != "System User":
        raise RuntimeError(f"Nelly is not an enabled System User: {APPROVER}")

    employee = frappe.db.get_value(
        "Employee",
        {"user_id": APPROVER, "status": "Active"},
        ["name", "employee_name", "company"],
        as_dict=True,
    )
    if not employee or employee.name != "HR-EMP-00001":
        raise RuntimeError(f"Unexpected employee linked to Nelly: {employee}")

    docs = []
    for name in APPLICATIONS:
        doc = frappe.get_doc("Leave Application", name)
        if (
            doc.docstatus != 1
            or doc.status != "Approved"
            or doc.leave_approver != "Administrator"
            or doc.leave_type != "Leave Without Pay"
            or not doc.half_day
            or float(doc.total_leave_days or 0) != 0.5
        ):
            raise RuntimeError(f"Unexpected Leave Application state: {doc.as_dict()}")
        docs.append(doc)

    try:
        approver_name = get_fullname(APPROVER)
        for doc in docs:
            doc.db_set(
                {
                    "leave_approver": APPROVER,
                    "leave_approver_name": approver_name,
                },
                update_modified=True,
            )

        results = []
        for name in APPLICATIONS:
            doc = frappe.get_doc("Leave Application", name)
            if (
                doc.docstatus != 1
                or doc.status != "Approved"
                or doc.leave_approver != APPROVER
                or doc.leave_approver_name != approver_name
            ):
                raise RuntimeError(f"Approver verification failed: {doc.as_dict()}")
            results.append(
                {
                    "leave_application": name,
                    "employee": doc.employee,
                    "approver": doc.leave_approver,
                    "approver_name": doc.leave_approver_name,
                }
            )

        if frappe.db.count("Salary Slip") != 0:
            raise RuntimeError("Approver change unexpectedly created Salary Slips")
        if frappe.db.count("Payroll Entry", {"docstatus": 0}) < 2:
            raise RuntimeError("Expected Payroll Entries to remain in draft")

        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        raise

    print(
        json.dumps(
            {
                "updated": results,
                "salary_slips": 0,
                "payroll_entries_unchanged": True,
            },
            ensure_ascii=False,
        )
    )


run()
