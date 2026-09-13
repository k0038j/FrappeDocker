import json

import frappe

from hrms.payroll.doctype.salary_structure.salary_structure import make_salary_slip


MONTHLY = "Nomina Mensual INSS"
BIMONTHLY = "Nomina Quincenal INSS"


def close_enough(actual, expected):
    return abs(float(actual or 0) - float(expected)) <= 0.01


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
issues = []

for assignment in assignments:
    posting_date = "2026-09-30" if assignment.salary_structure == MONTHLY else "2026-09-15"
    expected_start = "2026-09-01"
    expected_end = "2026-09-30" if assignment.salary_structure == MONTHLY else "2026-09-15"
    slip = make_salary_slip(
        assignment.salary_structure,
        employee=assignment.employee,
        posting_date=posting_date,
        for_preview=1,
    )
    inss = component_amount(slip.deductions, "INSS Laboral")
    ir = component_amount(slip.deductions, "IR Laboral")

    if not close_enough(slip.gross_pay, assignment.base):
        issues.append({"employee": assignment.employee, "issue": "gross/base mismatch"})
    if not close_enough(inss, float(assignment.base) * 0.07):
        issues.append({"employee": assignment.employee, "issue": "INSS is not 7%"})
    if ir < 0:
        issues.append({"employee": assignment.employee, "issue": "negative IR"})
    if str(slip.start_date) != expected_start or str(slip.end_date) != expected_end:
        issues.append({"employee": assignment.employee, "issue": "unexpected payroll period"})

    bucket = summary[assignment.salary_structure]
    bucket["employees"] += 1
    bucket["gross"] += float(slip.gross_pay or 0)
    bucket["inss"] += inss
    bucket["ir"] += ir
    bucket["net"] += float(slip.net_pay or 0)

if issues:
    raise RuntimeError(f"Preview validation failed: {issues}")
if frappe.db.count("Salary Slip") != 0:
    raise RuntimeError("Preview unexpectedly persisted Salary Slips")

for bucket in summary.values():
    for field in ("gross", "inss", "ir", "net"):
        bucket[field] = round(bucket[field], 2)

print(
    json.dumps(
        {
            "preview_only": True,
            "validated_employees": len(assignments),
            "issues": 0,
            "summary": summary,
            "salary_slips_persisted": 0,
        },
        ensure_ascii=False,
    )
)
