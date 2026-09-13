import json

import frappe


POSTING_DATE = "2026-09-12"
TARGETS = (
    {
        "employee": "HR-EMP-00006",
        "employee_name": "Julio Benavides",
        "attendance": "HR-ATT-2026-00002",
        "date": "2026-09-10",
    },
    {
        "employee": "HR-EMP-00031",
        "employee_name": "Amanda Alarcon",
        "attendance": "HR-ATT-2026-00004",
        "date": "2026-09-08",
    },
)


def run():
    if frappe.db.count("Salary Slip") != 0:
        raise RuntimeError("Salary Slips already exist; adjustment aborted")

    payroll_entries = frappe.get_all(
        "Payroll Entry",
        filters={"name": ["in", ["HR-PRUN-2026-00001", "HR-PRUN-2026-00002"]]},
        fields=["name", "docstatus"],
        order_by="name",
    )
    if len(payroll_entries) != 2 or any(row.docstatus != 0 for row in payroll_entries):
        raise RuntimeError(f"Expected both Payroll Entries in draft: {payroll_entries}")

    for target in TARGETS:
        attendance = frappe.get_doc("Attendance", target["attendance"])
        if (
            attendance.employee != target["employee"]
            or str(attendance.attendance_date) != target["date"]
            or attendance.docstatus != 1
            or attendance.status != "Half Day"
            or attendance.leave_type != "Leave Without Pay"
            or attendance.half_day_status != "Absent"
            or attendance.leave_application
        ):
            raise RuntimeError(f"Unexpected Attendance state: {attendance.as_dict()}")

        existing = frappe.get_all(
            "Leave Application",
            filters={
                "employee": target["employee"],
                "from_date": ["<=", target["date"]],
                "to_date": [">=", target["date"]],
                "docstatus": ["!=", 2],
            },
            pluck="name",
        )
        if existing:
            raise RuntimeError(f"Existing Leave Application for {target['employee']}: {existing}")

    created = []
    try:
        for target in TARGETS:
            application = frappe.get_doc(
                {
                    "doctype": "Leave Application",
                    "naming_series": "HR-LAP-.YYYY.-",
                    "employee": target["employee"],
                    "leave_type": "Leave Without Pay",
                    "from_date": target["date"],
                    "to_date": target["date"],
                    "half_day": 1,
                    "half_day_date": target["date"],
                    "posting_date": POSTING_DATE,
                    "status": "Approved",
                    "leave_approver": "Administrator",
                    "description": "Inasistencia ficticia de medio dia - prueba de nomina Etapa 6A.2",
                    "follow_via_email": 0,
                }
            )
            application.insert(ignore_permissions=True)
            application.submit()
            created.append(application.name)

        results = []
        for target, application_name in zip(TARGETS, created):
            application = frappe.get_doc("Leave Application", application_name)
            attendance = frappe.get_doc("Attendance", target["attendance"])
            if (
                application.docstatus != 1
                or application.status != "Approved"
                or float(application.total_leave_days or 0) != 0.5
                or attendance.docstatus != 1
                or attendance.status != "Half Day"
                or attendance.leave_type != "Leave Without Pay"
                or attendance.half_day_status != "Present"
                or attendance.leave_application != application.name
            ):
                raise RuntimeError(
                    f"Post-submit verification failed for {target['employee']}: "
                    f"application={application.as_dict()}, attendance={attendance.as_dict()}"
                )
            results.append(
                {
                    "employee": target["employee"],
                    "employee_name": attendance.employee_name,
                    "date": target["date"],
                    "leave_application": application.name,
                    "leave_days": float(application.total_leave_days),
                    "attendance": attendance.name,
                    "attendance_status": attendance.status,
                    "half_day_status": attendance.half_day_status,
                }
            )

        if frappe.db.count("Salary Slip") != 0:
            raise RuntimeError("Adjustment unexpectedly created Salary Slips")

        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        raise

    print(
        json.dumps(
            {
                "adjustment": "6A.2",
                "created_leave_applications": created,
                "results": results,
                "salary_slips": 0,
                "payroll_entries_remain_draft": 2,
            },
            ensure_ascii=False,
        )
    )


run()
