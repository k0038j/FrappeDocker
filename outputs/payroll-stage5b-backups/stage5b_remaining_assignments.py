import json

import frappe


COMPANY = "CYCE, S.A."
CURRENCY = "NIO"
FROM_DATE = "2026-09-01"
TAX_SLAB = "IR Laboral Nicaragua 2026 - INSS Deducible"
PAYROLL_PAYABLE = "2121 - Sueldos y Salarios por Pagar - CYCE"
MONTHLY = "Nomina Mensual INSS"
BIMONTHLY = "Nomina Quincenal INSS"
EXCLUDED_EMPLOYEE = "HR-EMP-00002"

# employee, structure, base per payroll cycle, taxable earnings Jan-Aug, IR withheld Jan-Aug
REMAINING = (
    ("HR-EMP-00001", MONTHLY, 12000.0, 89280.0, 3392.0),
    ("HR-EMP-00004", MONTHLY, 15000.0, 111600.0, 6740.0),
    ("HR-EMP-00005", MONTHLY, 16000.0, 119040.0, 7856.0),
    ("HR-EMP-00006", MONTHLY, 35000.0, 260400.0, 36766.67),
    ("HR-EMP-00007", MONTHLY, 26000.0, 193440.0, 22021.33),
    ("HR-EMP-00008", MONTHLY, 26000.0, 193440.0, 22021.33),
    ("HR-EMP-00009", MONTHLY, 26000.0, 193440.0, 22021.33),
    ("HR-EMP-00010", MONTHLY, 26000.0, 193440.0, 22021.33),
    ("HR-EMP-00011", MONTHLY, 26000.0, 193440.0, 22021.33),
    ("HR-EMP-00012", MONTHLY, 23000.0, 171120.0, 17557.33),
    ("HR-EMP-00013", MONTHLY, 22000.0, 163680.0, 16069.33),
    ("HR-EMP-00014", MONTHLY, 18000.0, 133920.0, 10117.33),
    ("HR-EMP-00015", MONTHLY, 20000.0, 148800.0, 13093.33),
    ("HR-EMP-00016", MONTHLY, 20000.0, 148800.0, 13093.33),
    ("HR-EMP-00018", BIMONTHLY, 10500.0, 156240.0, 14581.33),
    ("HR-EMP-00019", BIMONTHLY, 10500.0, 156240.0, 14581.33),
    ("HR-EMP-00020", BIMONTHLY, 11000.0, 163680.0, 16069.33),
    ("HR-EMP-00021", BIMONTHLY, 9000.0, 133920.0, 10117.33),
    ("HR-EMP-00022", BIMONTHLY, 9000.0, 133920.0, 10117.33),
    ("HR-EMP-00023", BIMONTHLY, 8000.0, 119040.0, 7856.0),
    ("HR-EMP-00024", BIMONTHLY, 8000.0, 119040.0, 7856.0),
    ("HR-EMP-00025", BIMONTHLY, 8000.0, 119040.0, 7856.0),
    ("HR-EMP-00026", BIMONTHLY, 8000.0, 119040.0, 7856.0),
    ("HR-EMP-00027", BIMONTHLY, 9500.0, 141360.0, 11605.33),
    ("HR-EMP-00028", BIMONTHLY, 9500.0, 141360.0, 11605.33),
    ("HR-EMP-00029", BIMONTHLY, 9500.0, 141360.0, 11605.33),
    ("HR-EMP-00030", BIMONTHLY, 7500.0, 111600.0, 6740.0),
    ("HR-EMP-00031", BIMONTHLY, 7000.0, 104160.0, 5624.0),
    ("HR-EMP-00032", BIMONTHLY, 7000.0, 104160.0, 5624.0),
    ("HR-EMP-00033", BIMONTHLY, 7000.0, 104160.0, 5624.0),
    ("HR-EMP-00036", BIMONTHLY, 7000.0, 104160.0, 5624.0),
    ("HR-EMP-00037", BIMONTHLY, 7000.0, 104160.0, 5624.0),
    ("HR-EMP-00038", BIMONTHLY, 7000.0, 104160.0, 5624.0),
    ("HR-EMP-00040", BIMONTHLY, 7000.0, 104160.0, 5624.0),
    ("HR-EMP-00041", BIMONTHLY, 7000.0, 104160.0, 5624.0),
    ("HR-EMP-00042", BIMONTHLY, 7000.0, 104160.0, 5624.0),
)

PILOT_EMPLOYEES = {"HR-EMP-00003", "HR-EMP-00017"}


def close_enough(actual, expected):
    return abs(float(actual or 0) - float(expected)) <= 0.01


def run():
    if len(REMAINING) != 36 or len({row[0] for row in REMAINING}) != 36:
        raise RuntimeError("Expected 36 unique remaining employees")
    if sum(row[1] == MONTHLY for row in REMAINING) != 14:
        raise RuntimeError("Expected 14 remaining monthly employees")
    if sum(row[1] == BIMONTHLY for row in REMAINING) != 22:
        raise RuntimeError("Expected 22 remaining bimonthly employees")
    if not close_enough(sum(row[2] for row in REMAINING), 492000.0):
        raise RuntimeError("Unexpected remaining cycle-base total")
    if EXCLUDED_EMPLOYEE in {row[0] for row in REMAINING}:
        raise RuntimeError("Augusto Garcia must not be assigned")

    slab = frappe.db.get_value(
        "Income Tax Slab",
        TAX_SLAB,
        ["docstatus", "disabled", "allow_tax_exemption", "currency"],
        as_dict=True,
    )
    if (
        not slab
        or slab.docstatus != 1
        or int(slab.disabled or 0) != 0
        or int(slab.allow_tax_exemption or 0) != 1
        or slab.currency != CURRENCY
    ):
        raise RuntimeError(f"Corrected tax slab is not ready: {slab}")

    for structure_name in (MONTHLY, BIMONTHLY):
        structure = frappe.db.get_value(
            "Salary Structure",
            structure_name,
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
            raise RuntimeError(f"Salary Structure is not ready: {structure_name} {structure}")

    submitted_before = frappe.get_all(
        "Salary Structure Assignment",
        filters={"docstatus": 1},
        fields=["employee", "income_tax_slab"],
        order_by="employee",
    )
    if {row.employee for row in submitted_before} != PILOT_EMPLOYEES:
        raise RuntimeError(f"Unexpected submitted assignments before Stage 5B: {submitted_before}")
    if any(row.income_tax_slab != TAX_SLAB for row in submitted_before):
        raise RuntimeError("Pilot assignments do not use the corrected tax slab")
    if frappe.db.count("Salary Slip") != 0:
        raise RuntimeError("Salary Slips already exist; Stage 5B aborted")
    if frappe.db.get_value("Employee", EXCLUDED_EMPLOYEE, "grade"):
        raise RuntimeError("Augusto Garcia unexpectedly has an Employee Grade")

    for employee, structure_name, *_ in REMAINING:
        employee_state = frappe.db.get_value(
            "Employee", employee, ["status", "grade", "company"], as_dict=True
        )
        if (
            not employee_state
            or employee_state.status != "Active"
            or employee_state.grade != structure_name
            or employee_state.company != COMPANY
        ):
            raise RuntimeError(f"Employee state changed: {employee} {employee_state}")
        if frappe.db.exists(
            "Salary Structure Assignment",
            {"employee": employee, "from_date": FROM_DATE, "docstatus": 1},
        ):
            raise RuntimeError(f"Submitted assignment already exists: {employee}")

    journal_count_before = frappe.db.count("Journal Entry")
    payroll_entry_state_before = frappe.db.get_value(
        "Payroll Entry", "HR-PRUN-2026-00001", ["docstatus", "modified"], as_dict=True
    )

    created = []
    try:
        for employee, structure_name, base, taxable_ytd, tax_ytd in REMAINING:
            assignment = frappe.get_doc(
                {
                    "doctype": "Salary Structure Assignment",
                    "employee": employee,
                    "salary_structure": structure_name,
                    "from_date": FROM_DATE,
                    "company": COMPANY,
                    "currency": CURRENCY,
                    "payroll_payable_account": PAYROLL_PAYABLE,
                    "base": base,
                    "variable": 0,
                    "income_tax_slab": TAX_SLAB,
                    "taxable_earnings_till_date": taxable_ytd,
                    "tax_deducted_till_date": tax_ytd,
                }
            )
            assignment.insert(ignore_permissions=True)
            assignment.submit()
            created.append(assignment.name)

        active = frappe.get_all(
            "Salary Structure Assignment",
            filters={"docstatus": 1},
            fields=[
                "name",
                "employee",
                "salary_structure",
                "from_date",
                "base",
                "income_tax_slab",
                "taxable_earnings_till_date",
                "tax_deducted_till_date",
            ],
            order_by="employee",
        )
        if len(active) != 38 or len({row.employee for row in active}) != 38:
            raise RuntimeError(f"Expected 38 unique active assignments, found {len(active)}")
        if sum(row.salary_structure == MONTHLY for row in active) != 15:
            raise RuntimeError("Expected 15 monthly active assignments")
        if sum(row.salary_structure == BIMONTHLY for row in active) != 23:
            raise RuntimeError("Expected 23 bimonthly active assignments")
        if any(str(row.from_date) != FROM_DATE or row.income_tax_slab != TAX_SLAB for row in active):
            raise RuntimeError("Active assignment date or tax slab mismatch")
        if not close_enough(sum(row.base for row in active), 521250.0):
            raise RuntimeError("Unexpected total base per payroll cycle")

        expected = {
            employee: (structure_name, base, taxable_ytd, tax_ytd)
            for employee, structure_name, base, taxable_ytd, tax_ytd in REMAINING
        }
        for assignment in active:
            if assignment.employee not in expected:
                continue
            structure_name, base, taxable_ytd, tax_ytd = expected[assignment.employee]
            if (
                assignment.salary_structure != structure_name
                or not close_enough(assignment.base, base)
                or not close_enough(assignment.taxable_earnings_till_date, taxable_ytd)
                or not close_enough(assignment.tax_deducted_till_date, tax_ytd)
            ):
                raise RuntimeError(f"Assignment values mismatch: {assignment.employee}")

        if frappe.db.exists(
            "Salary Structure Assignment", {"employee": EXCLUDED_EMPLOYEE, "docstatus": 1}
        ):
            raise RuntimeError("Augusto Garcia was unexpectedly assigned a Salary Structure")
        if frappe.db.count("Salary Slip") != 0:
            raise RuntimeError("Stage 5B unexpectedly created Salary Slips")
        if frappe.db.count("Journal Entry") != journal_count_before:
            raise RuntimeError("Stage 5B unexpectedly changed Journal Entry count")
        payroll_entry_state_after = frappe.db.get_value(
            "Payroll Entry", "HR-PRUN-2026-00001", ["docstatus", "modified"], as_dict=True
        )
        if payroll_entry_state_after != payroll_entry_state_before:
            raise RuntimeError("Existing Payroll Entry was unexpectedly modified")

        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        raise

    print(
        json.dumps(
            {
                "created": len(created),
                "active_assignments": 38,
                "monthly": 15,
                "bimonthly": 23,
                "cycle_base_total": 521250.0,
                "salary_slips": 0,
                "journal_entries_created": 0,
                "augusto_assignment": False,
            },
            ensure_ascii=False,
        )
    )


run()
