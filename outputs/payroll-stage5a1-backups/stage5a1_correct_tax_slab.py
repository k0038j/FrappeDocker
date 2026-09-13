import json

import frappe


COMPANY = "CYCE, S.A."
CURRENCY = "NIO"
FROM_DATE = "2026-09-01"
OLD_SLAB = "IR Laboral Nicaragua 2026"
NEW_SLAB = "IR Laboral Nicaragua 2026 - INSS Deducible"
PAYROLL_PAYABLE = "2121 - Sueldos y Salarios por Pagar - CYCE"

PILOT = (
    {
        "employee": "HR-EMP-00003",
        "salary_structure": "Nomina Mensual INSS",
        "base": 22000.0,
        "taxable_earnings_till_date": 163680.0,
        "tax_deducted_till_date": 16069.33,
    },
    {
        "employee": "HR-EMP-00017",
        "salary_structure": "Nomina Quincenal INSS",
        "base": 7250.0,
        "taxable_earnings_till_date": 107880.0,
        "tax_deducted_till_date": 6182.0,
    },
)

EXPECTED_SLABS = [
    (0.0, 100000.0, 0.0),
    (100001.0, 200000.0, 15.0),
    (200001.0, 350000.0, 20.0),
    (350001.0, 500000.0, 25.0),
    (500001.0, 0.0, 30.0),
]


def close_enough(actual, expected):
    return abs(float(actual or 0) - float(expected)) <= 0.01


def validate_old_assignment(assignment, expected):
    return (
        assignment.docstatus == 1
        and assignment.salary_structure == expected["salary_structure"]
        and str(assignment.from_date) == FROM_DATE
        and close_enough(assignment.base, expected["base"])
        and assignment.income_tax_slab == OLD_SLAB
        and close_enough(
            assignment.taxable_earnings_till_date,
            expected["taxable_earnings_till_date"],
        )
        and close_enough(
            assignment.tax_deducted_till_date,
            expected["tax_deducted_till_date"],
        )
    )


def create_assignment(row):
    assignment = frappe.get_doc(
        {
            "doctype": "Salary Structure Assignment",
            "employee": row["employee"],
            "salary_structure": row["salary_structure"],
            "from_date": FROM_DATE,
            "company": COMPANY,
            "currency": CURRENCY,
            "payroll_payable_account": PAYROLL_PAYABLE,
            "base": row["base"],
            "variable": 0,
            "income_tax_slab": NEW_SLAB,
            "taxable_earnings_till_date": row["taxable_earnings_till_date"],
            "tax_deducted_till_date": row["tax_deducted_till_date"],
        }
    )
    assignment.insert(ignore_permissions=True)
    assignment.submit()
    return assignment.name


def run():
    if frappe.db.count("Salary Slip") != 0:
        raise RuntimeError("Salary Slips already exist; correction aborted")
    if frappe.db.get_value("Employee", "HR-EMP-00002", "grade"):
        raise RuntimeError("Augusto Garcia unexpectedly has an Employee Grade")
    if frappe.db.exists("Income Tax Slab", NEW_SLAB):
        raise RuntimeError(f"Corrected tax slab already exists: {NEW_SLAB}")

    old_slab = frappe.get_doc("Income Tax Slab", OLD_SLAB)
    actual_slabs = [
        (float(row.from_amount), float(row.to_amount), float(row.percent_deduction))
        for row in old_slab.slabs
    ]
    if (
        old_slab.docstatus != 1
        or int(old_slab.disabled or 0) != 0
        or int(old_slab.allow_tax_exemption or 0) != 0
        or old_slab.company != COMPANY
        or old_slab.currency != CURRENCY
        or str(old_slab.effective_from) != "2026-01-01"
        or actual_slabs != EXPECTED_SLABS
    ):
        raise RuntimeError("Original tax slab state changed; correction aborted")

    submitted = frappe.get_all(
        "Salary Structure Assignment",
        filters={"docstatus": 1},
        fields=["name", "employee"],
        order_by="employee",
    )
    if [row.employee for row in submitted] != [row["employee"] for row in PILOT]:
        raise RuntimeError(f"Unexpected submitted assignment set: {submitted}")

    old_assignments = []
    expected_by_employee = {row["employee"]: row for row in PILOT}
    for row in submitted:
        assignment = frappe.get_doc("Salary Structure Assignment", row.name)
        if not validate_old_assignment(assignment, expected_by_employee[row.employee]):
            raise RuntimeError(f"Pilot assignment changed unexpectedly: {row.name}")
        old_assignments.append(assignment)

    cancelled = []
    created = []
    try:
        for assignment in old_assignments:
            assignment.cancel()
            cancelled.append(assignment.name)

        old_slab.disabled = 1
        old_slab.save(ignore_permissions=True)

        new_slab = frappe.get_doc(
            {
                "doctype": "Income Tax Slab",
                "name": NEW_SLAB,
                "effective_from": "2026-01-01",
                "company": COMPANY,
                "currency": CURRENCY,
                "disabled": 0,
                "allow_tax_exemption": 1,
                "standard_tax_exemption_amount": 0,
                "tax_relief_limit": 0,
                "slabs": [
                    {
                        "from_amount": from_amount,
                        "to_amount": to_amount,
                        "percent_deduction": percent,
                    }
                    for from_amount, to_amount, percent in EXPECTED_SLABS
                ],
            }
        )
        new_slab.insert(ignore_permissions=True)
        new_slab.submit()

        for row in PILOT:
            created.append(create_assignment(row))

        if frappe.db.get_value("Income Tax Slab", OLD_SLAB, "disabled") != 1:
            raise RuntimeError("Original tax slab was not disabled")
        corrected_state = frappe.db.get_value(
            "Income Tax Slab",
            NEW_SLAB,
            ["docstatus", "disabled", "allow_tax_exemption"],
            as_dict=True,
        )
        if (
            corrected_state.docstatus != 1
            or int(corrected_state.disabled or 0) != 0
            or int(corrected_state.allow_tax_exemption or 0) != 1
        ):
            raise RuntimeError(f"Corrected tax slab verification failed: {corrected_state}")

        active_assignments = frappe.get_all(
            "Salary Structure Assignment",
            filters={"docstatus": 1},
            fields=["name", "employee", "income_tax_slab"],
            order_by="employee",
        )
        if len(active_assignments) != 2 or any(
            row.income_tax_slab != NEW_SLAB for row in active_assignments
        ):
            raise RuntimeError(f"Replacement assignment verification failed: {active_assignments}")
        if frappe.db.count("Salary Slip") != 0:
            raise RuntimeError("Correction unexpectedly created Salary Slips")
        if frappe.db.get_value("Employee", "HR-EMP-00002", "grade"):
            raise RuntimeError("Augusto Garcia was unexpectedly assigned a grade")

        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        raise

    print(
        json.dumps(
            {
                "disabled_tax_slab": OLD_SLAB,
                "corrected_tax_slab": NEW_SLAB,
                "cancelled_assignments": cancelled,
                "replacement_assignments": created,
                "salary_slips": 0,
                "augusto_assignment": False,
            },
            ensure_ascii=False,
        )
    )


run()
