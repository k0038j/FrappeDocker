import json

import frappe

from hrms.payroll.doctype.salary_structure.salary_structure import make_salary_slip


CASES = (
    ("HR-EMP-00003", "Nomina Mensual INSS", "2026-09-30"),
    ("HR-EMP-00017", "Nomina Quincenal INSS", "2026-09-15"),
)


def components(rows):
    return {row.salary_component: float(row.amount or 0) for row in rows}


results = []
for employee, structure, posting_date in CASES:
    slip = make_salary_slip(
        structure,
        employee=employee,
        posting_date=posting_date,
        for_preview=1,
    )
    results.append(
        {
            "employee": employee,
            "salary_structure": structure,
            "start_date": str(slip.start_date),
            "end_date": str(slip.end_date),
            "gross_pay": float(slip.gross_pay or 0),
            "total_deduction": float(slip.total_deduction or 0),
            "net_pay": float(slip.net_pay or 0),
            "earnings": components(slip.earnings),
            "deductions": components(slip.deductions),
            "annual_taxable_amount": float(slip.annual_taxable_amount or 0),
            "income_tax_deducted_till_date": float(slip.income_tax_deducted_till_date or 0),
        }
    )

if frappe.db.count("Salary Slip") != 0:
    raise RuntimeError("Preview unexpectedly persisted Salary Slips")

print(json.dumps({"preview_only": True, "results": results}, ensure_ascii=False))
