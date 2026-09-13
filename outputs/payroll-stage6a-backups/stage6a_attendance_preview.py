import json

import frappe

from hrms.payroll.doctype.salary_structure.salary_structure import make_salary_slip


MONTHLY = "Nomina Mensual INSS"
BIMONTHLY = "Nomina Quincenal INSS"
EXPECTED_REDUCTIONS = {
    "HR-EMP-00003": {"absent": 1.0, "lwp": 0.0},
    "HR-EMP-00006": {"absent": 0.0, "lwp": 0.5},
    "HR-EMP-00017": {"absent": 1.0, "lwp": 0.0},
    "HR-EMP-00031": {"absent": 0.0, "lwp": 0.5},
}


def close_enough(actual, expected):
    return abs(float(actual or 0) - float(expected)) <= 0.02


def component_amount(rows, component):
    return sum(float(row.amount or 0) for row in rows if row.salary_component == component)


assignments = frappe.get_all(
    "Salary Structure Assignment",
    filters={"docstatus": 1},
    fields=["employee", "salary_structure", "base"],
    order_by="employee",
)
if len(assignments) != 38:
    raise RuntimeError(f"Expected 38 active assignments, found {len(assignments)}")

summary = {
    MONTHLY: {"employees": 0, "gross": 0.0, "inss": 0.0, "ir": 0.0, "net": 0.0},
    BIMONTHLY: {"employees": 0, "gross": 0.0, "inss": 0.0, "ir": 0.0, "net": 0.0},
}
affected = []
issues = []

for assignment in assignments:
    posting_date = "2026-09-30" if assignment.salary_structure == MONTHLY else "2026-09-15"
    expected_total_days = 26.0 if assignment.salary_structure == MONTHLY else 13.0
    reduction = EXPECTED_REDUCTIONS.get(assignment.employee, {"absent": 0.0, "lwp": 0.0})
    expected_payment_days = expected_total_days - reduction["absent"] - reduction["lwp"]

    slip = make_salary_slip(
        assignment.salary_structure,
        employee=assignment.employee,
        posting_date=posting_date,
        for_preview=0,
    )
    inss = component_amount(slip.deductions, "INSS Laboral")
    ir = component_amount(slip.deductions, "IR Laboral")
    expected_gross = float(assignment.base) * expected_payment_days / expected_total_days
    expected_inss = float(assignment.base) * 0.07 * expected_payment_days / expected_total_days

    if not close_enough(slip.total_working_days, expected_total_days):
        issues.append({"employee": assignment.employee, "issue": "unexpected total working days"})
    if not close_enough(slip.payment_days, expected_payment_days):
        issues.append({"employee": assignment.employee, "issue": "unexpected payment days"})
    if not close_enough(slip.absent_days, reduction["absent"]):
        issues.append({"employee": assignment.employee, "issue": "unexpected absent days"})
    if not close_enough(slip.leave_without_pay, reduction["lwp"]):
        issues.append({"employee": assignment.employee, "issue": "unexpected LWP days"})
    if not close_enough(slip.gross_pay, expected_gross):
        issues.append({"employee": assignment.employee, "issue": "gross proration mismatch"})
    if not close_enough(inss, expected_inss):
        issues.append({"employee": assignment.employee, "issue": "INSS proration mismatch"})
    if ir < 0:
        issues.append({"employee": assignment.employee, "issue": "negative IR"})

    bucket = summary[assignment.salary_structure]
    bucket["employees"] += 1
    bucket["gross"] += float(slip.gross_pay or 0)
    bucket["inss"] += inss
    bucket["ir"] += ir
    bucket["net"] += float(slip.net_pay or 0)

    if assignment.employee in EXPECTED_REDUCTIONS:
        affected.append(
            {
                "employee": assignment.employee,
                "salary_structure": assignment.salary_structure,
                "total_working_days": float(slip.total_working_days or 0),
                "payment_days": float(slip.payment_days or 0),
                "absent_days": float(slip.absent_days or 0),
                "leave_without_pay": float(slip.leave_without_pay or 0),
                "gross_pay": float(slip.gross_pay or 0),
                "inss": inss,
                "ir": ir,
                "net_pay": float(slip.net_pay or 0),
            }
        )

if issues:
    raise RuntimeError(f"Attendance preview validation failed: {issues}")
if frappe.db.count("Salary Slip") != 0:
    raise RuntimeError("Preview unexpectedly persisted Salary Slips")

for bucket in summary.values():
    for field in ("gross", "inss", "ir", "net"):
        bucket[field] = round(bucket[field], 2)
for row in affected:
    for field in ("gross_pay", "inss", "ir", "net_pay"):
        row[field] = round(row[field], 2)

print(
    json.dumps(
        {
            "preview_only": True,
            "validated_employees": len(assignments),
            "affected": affected,
            "summary": summary,
            "issues": 0,
            "salary_slips_persisted": 0,
        },
        ensure_ascii=False,
    )
)
