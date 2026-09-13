import json

import frappe


COMPANY = "CYCE, S.A."
HALF_DAYS = (
    ("HR-EMP-00006", "2026-09-10"),
    ("HR-EMP-00031", "2026-09-08"),
)


def run():
    if frappe.db.count("Salary Slip") != 0:
        raise RuntimeError("Salary Slips already exist; half-day correction aborted")

    originals = []
    for employee, attendance_date in HALF_DAYS:
        names = frappe.get_all(
            "Attendance",
            filters={
                "employee": employee,
                "attendance_date": attendance_date,
                "docstatus": 1,
            },
            pluck="name",
        )
        if len(names) != 1:
            raise RuntimeError(f"Expected one submitted Attendance for {employee}: {names}")
        attendance = frappe.get_doc("Attendance", names[0])
        if (
            attendance.status != "Half Day"
            or attendance.leave_type != "Leave Without Pay"
            or attendance.half_day_status != "Absent"
        ):
            raise RuntimeError(f"Unexpected half-day state: {attendance.name}")
        originals.append(attendance)

    cancelled = []
    replacements = []
    try:
        for attendance in originals:
            employee = attendance.employee
            attendance_date = attendance.attendance_date
            attendance.cancel()
            cancelled.append(attendance.name)

            replacement = frappe.get_doc(
                {
                    "doctype": "Attendance",
                    "employee": employee,
                    "attendance_date": attendance_date,
                    "company": COMPANY,
                    "status": "Half Day",
                    "leave_type": "Leave Without Pay",
                    "half_day_status": "Present",
                }
            )
            replacement.insert(ignore_permissions=True)
            replacement.submit()
            replacements.append(replacement.name)

        for employee, attendance_date in HALF_DAYS:
            state = frappe.get_all(
                "Attendance",
                filters={
                    "employee": employee,
                    "attendance_date": attendance_date,
                    "docstatus": 1,
                },
                fields=["name", "status", "leave_type", "half_day_status"],
            )
            if (
                len(state) != 1
                or state[0].status != "Half Day"
                or state[0].leave_type != "Leave Without Pay"
                or state[0].half_day_status != "Present"
            ):
                raise RuntimeError(f"Half-day replacement verification failed: {state}")
        if frappe.db.count("Salary Slip") != 0:
            raise RuntimeError("Correction unexpectedly created Salary Slips")

        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        raise

    print(
        json.dumps(
            {
                "cancelled": cancelled,
                "replacements": replacements,
                "half_day_status": "Present",
                "salary_slips": 0,
            },
            ensure_ascii=False,
        )
    )


run()
