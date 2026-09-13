import json

import frappe


COMPANY = "CYCE, S.A."
CURRENCY = "NIO"
FROM_DATE = "2026-09-01"
TAX_SLAB = "IR Laboral Nicaragua 2026"
PAYROLL_PAYABLE = "2121 - Sueldos y Salarios por Pagar - CYCE"

PILOT = (
    {
        "employee": "HR-EMP-00003",
        "employee_name": "Marbel Canales",
        "grade": "Nomina Mensual INSS",
        "salary_structure": "Nomina Mensual INSS",
        "base": 22000.0,
        "taxable_earnings_till_date": 163680.0,
        "tax_deducted_till_date": 16069.33,
    },
    {
        "employee": "HR-EMP-00017",
        "employee_name": "Brayan López",
        "grade": "Nomina Quincenal INSS",
        "salary_structure": "Nomina Quincenal INSS",
        "base": 7250.0,
        "taxable_earnings_till_date": 107880.0,
        "tax_deducted_till_date": 6182.0,
    },
)


def close_enough(actual, expected):
    return abs(float(actual or 0) - float(expected)) <= 0.01


def run():
    if frappe.db.count("Salary Structure Assignment") != 0:
        raise RuntimeError("Salary Structure Assignments already exist; pilot aborted")
    if frappe.db.count("Salary Slip") != 0:
        raise RuntimeError("Salary Slips already exist; pilot aborted")
    if frappe.db.get_value("Employee", "HR-EMP-00002", "grade"):
        raise RuntimeError("Augusto Garcia unexpectedly has an Employee Grade")

    slab_state = frappe.db.get_value(
        "Income Tax Slab", TAX_SLAB, ["docstatus", "disabled", "currency"], as_dict=True
    )
    if not slab_state or slab_state.docstatus != 1 or slab_state.disabled or slab_state.currency != CURRENCY:
        raise RuntimeError(f"Tax slab is not ready: {slab_state}")

    for component in ("INSS Laboral", "IR Laboral"):
        if frappe.db.get_value("Salary Component", component, "disabled"):
            raise RuntimeError(f"Salary Component is disabled: {component}")

    for row in PILOT:
        employee = frappe.db.get_value(
            "Employee",
            row["employee"],
            ["employee_name", "status", "grade", "company"],
            as_dict=True,
        )
        if not employee:
            raise RuntimeError(f"Missing employee: {row['employee']}")
        if (
            employee.employee_name != row["employee_name"]
            or employee.status != "Active"
            or employee.grade != row["grade"]
            or employee.company != COMPANY
        ):
            raise RuntimeError(f"Employee data changed for {row['employee']}: {employee}")

        structure = frappe.db.get_value(
            "Salary Structure",
            row["salary_structure"],
            ["docstatus", "is_active", "company", "currency"],
            as_dict=True,
        )
        if (
            not structure
            or structure.docstatus != 1
            or structure.is_active != "Yes"
            or structure.company != COMPANY
            or structure.currency != CURRENCY
        ):
            raise RuntimeError(f"Salary Structure is not ready: {row['salary_structure']} {structure}")

    created = []
    try:
        for row in PILOT:
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
                    "income_tax_slab": TAX_SLAB,
                    "taxable_earnings_till_date": row["taxable_earnings_till_date"],
                    "tax_deducted_till_date": row["tax_deducted_till_date"],
                }
            )
            assignment.insert(ignore_permissions=True)
            assignment.submit()
            created.append(assignment.name)

        assignments = frappe.get_all(
            "Salary Structure Assignment",
            filters={"name": ["in", created]},
            fields=[
                "name",
                "employee",
                "salary_structure",
                "from_date",
                "base",
                "income_tax_slab",
                "taxable_earnings_till_date",
                "tax_deducted_till_date",
                "docstatus",
            ],
            order_by="employee",
        )
        if len(assignments) != 2:
            raise RuntimeError(f"Expected 2 pilot assignments, found {len(assignments)}")

        expected_by_employee = {row["employee"]: row for row in PILOT}
        for assignment in assignments:
            expected = expected_by_employee[assignment.employee]
            if (
                assignment.docstatus != 1
                or assignment.salary_structure != expected["salary_structure"]
                or str(assignment.from_date) != FROM_DATE
                or not close_enough(assignment.base, expected["base"])
                or assignment.income_tax_slab != TAX_SLAB
                or not close_enough(
                    assignment.taxable_earnings_till_date,
                    expected["taxable_earnings_till_date"],
                )
                or not close_enough(
                    assignment.tax_deducted_till_date,
                    expected["tax_deducted_till_date"],
                )
            ):
                raise RuntimeError(f"Pilot assignment verification failed: {assignment}")

        if frappe.db.count("Salary Slip") != 0:
            raise RuntimeError("Pilot unexpectedly created Salary Slips")
        if frappe.db.get_value("Employee", "HR-EMP-00002", "grade"):
            raise RuntimeError("Augusto Garcia was unexpectedly assigned a grade")

        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        raise

    print(
        json.dumps(
            {
                "created_assignments": created,
                "employees": [row["employee"] for row in PILOT],
                "from_date": FROM_DATE,
                "salary_slips": 0,
                "augusto_assignment": False,
            },
            ensure_ascii=False,
        )
    )


run()
