import json

import frappe


COMPANY = "CYCE, S.A."
SLAB = "IR Laboral Nicaragua 2026"
STRUCTURES = {
    "Nomina Mensual INSS": "Monthly",
    "Nomina Quincenal INSS": "Bimonthly",
}
COMPONENTS = {
    "INSS Laboral": {
        "account": "2138 - Retencion Inss Laboral - CYCE",
        "variable_tax": 0,
        "formula": "base * 0.07",
    },
    "IR Laboral": {
        "account": "2131 - IR Salarios - CYCE",
        "variable_tax": 1,
        "formula": "",
    },
}
EXPECTED_SLABS = [
    (0.0, 100000.0, 0.0),
    (100001.0, 200000.0, 15.0),
    (200001.0, 350000.0, 20.0),
    (350001.0, 500000.0, 25.0),
    (500001.0, 0.0, 30.0),
]


def validate_component(name, expected):
    component = frappe.get_doc("Salary Component", name)
    if component.type != "Deduction":
        raise RuntimeError(f"{name} is not a Deduction")
    if int(component.variable_based_on_taxable_salary or 0) != expected["variable_tax"]:
        raise RuntimeError(f"Unexpected tax mode for {name}")
    if (component.formula or "").strip() != expected["formula"]:
        raise RuntimeError(f"Unexpected formula for {name}: {component.formula!r}")
    accounts = {row.company: row.account for row in component.accounts}
    if accounts.get(COMPANY) != expected["account"]:
        raise RuntimeError(f"Unexpected account for {name}: {accounts.get(COMPANY)!r}")
    return component


def validate_structure(name, frequency):
    structure = frappe.get_doc("Salary Structure", name)
    if structure.docstatus != 0 or structure.is_active != "No":
        raise RuntimeError(
            f"Unexpected initial state for {name}: docstatus={structure.docstatus}, active={structure.is_active}"
        )
    if structure.company != COMPANY or structure.currency != "NIO":
        raise RuntimeError(f"Unexpected company/currency for {name}")
    if structure.payroll_frequency != frequency:
        raise RuntimeError(f"Unexpected payroll frequency for {name}")

    earnings = [(row.salary_component, (row.formula or "").strip()) for row in structure.earnings]
    deductions = [
        (
            row.salary_component,
            (row.formula or "").strip(),
            int(row.variable_based_on_taxable_salary or 0),
            int(row.exempted_from_income_tax or 0),
        )
        for row in structure.deductions
    ]
    if earnings != [("Basic", "base")]:
        raise RuntimeError(f"Unexpected earnings in {name}: {earnings}")
    if deductions != [
        ("INSS Laboral", "base * 0.07", 0, 1),
        ("IR Laboral", "", 1, 0),
    ]:
        raise RuntimeError(f"Unexpected deductions in {name}: {deductions}")
    return structure


def run():
    if frappe.db.count("Salary Structure Assignment") != 0:
        raise RuntimeError("Salary Structure Assignments already exist; Stage 4 must not continue")
    if frappe.db.count("Salary Slip") != 0:
        raise RuntimeError("Salary Slips already exist; Stage 4 must not continue")
    if frappe.db.get_value("Employee", "HR-EMP-00002", "grade"):
        raise RuntimeError("Augusto Garcia unexpectedly has an Employee Grade")

    component_docs = {
        name: validate_component(name, expected) for name, expected in COMPONENTS.items()
    }

    slab = frappe.get_doc("Income Tax Slab", SLAB)
    if slab.docstatus != 0 or int(slab.disabled or 0) != 1:
        raise RuntimeError(
            f"Unexpected initial state for tax slab: docstatus={slab.docstatus}, disabled={slab.disabled}"
        )
    if slab.company != COMPANY or slab.currency != "NIO" or str(slab.effective_from) != "2026-01-01":
        raise RuntimeError("Unexpected company, currency, or effective date for tax slab")
    actual_slabs = [
        (float(row.from_amount), float(row.to_amount), float(row.percent_deduction))
        for row in slab.slabs
    ]
    if actual_slabs != EXPECTED_SLABS:
        raise RuntimeError(f"Unexpected income tax brackets: {actual_slabs}")

    structure_docs = {
        name: validate_structure(name, frequency) for name, frequency in STRUCTURES.items()
    }

    try:
        for component in component_docs.values():
            component.disabled = 0
            component.save(ignore_permissions=True)

        slab.disabled = 0
        slab.save(ignore_permissions=True)
        slab.submit()

        for structure in structure_docs.values():
            structure.is_active = "Yes"
            structure.save(ignore_permissions=True)
            structure.submit()

        for component_name in COMPONENTS:
            if int(frappe.db.get_value("Salary Component", component_name, "disabled") or 0) != 0:
                raise RuntimeError(f"Component was not enabled: {component_name}")
        slab_state = frappe.db.get_value(
            "Income Tax Slab", SLAB, ["docstatus", "disabled"], as_dict=True
        )
        if slab_state.docstatus != 1 or int(slab_state.disabled or 0) != 0:
            raise RuntimeError(f"Tax slab verification failed: {slab_state}")
        for structure_name in STRUCTURES:
            state = frappe.db.get_value(
                "Salary Structure", structure_name, ["docstatus", "is_active"], as_dict=True
            )
            if state.docstatus != 1 or state.is_active != "Yes":
                raise RuntimeError(f"Salary structure verification failed: {structure_name} {state}")
        if frappe.db.count("Salary Structure Assignment") != 0 or frappe.db.count("Salary Slip") != 0:
            raise RuntimeError("Stage 4 unexpectedly created payroll transactions")
        if frappe.db.get_value("Employee", "HR-EMP-00002", "grade"):
            raise RuntimeError("Augusto Garcia was unexpectedly assigned a grade")

        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        raise

    print(
        json.dumps(
            {
                "enabled_components": sorted(COMPONENTS),
                "submitted_tax_slab": SLAB,
                "activated_structures": sorted(STRUCTURES),
                "salary_structure_assignments": 0,
                "salary_slips": 0,
                "augusto_grade": None,
            },
            ensure_ascii=False,
        )
    )


run()
