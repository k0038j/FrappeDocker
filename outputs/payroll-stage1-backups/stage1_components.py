import frappe


COMPANY = "CYCE, S.A."
COMPONENTS = (
    {
        "salary_component": "INSS Laboral",
        "salary_component_abbr": "INSSL",
        "type": "Deduction",
        "description": "Cotizacion laboral INSS del 7%. Creado deshabilitado en la etapa 1.",
        "depends_on_payment_days": 1,
        "amount_based_on_formula": 1,
        "formula": "base * 0.07",
        "exempted_from_income_tax": 1,
        "is_income_tax_component": 0,
        "variable_based_on_taxable_salary": 0,
        "disabled": 1,
        "account": "2138 - Retencion Inss Laboral - CYCE",
    },
    {
        "salary_component": "IR Laboral",
        "salary_component_abbr": "IRL",
        "type": "Deduction",
        "description": "IR de rentas del trabajo calculado por tabla progresiva. Creado deshabilitado en la etapa 1.",
        "depends_on_payment_days": 0,
        "amount_based_on_formula": 0,
        "exempted_from_income_tax": 0,
        "is_income_tax_component": 1,
        "variable_based_on_taxable_salary": 1,
        "disabled": 1,
        "account": "2131 - IR Salarios - CYCE",
    },
)


created = []
existing = []

for spec in COMPONENTS:
    component_name = spec["salary_component"]
    if frappe.db.exists("Salary Component", component_name):
        existing.append(component_name)
        continue

    account_name = spec["account"]
    account = frappe.db.get_value(
        "Account",
        account_name,
        ["company", "is_group", "disabled"],
        as_dict=True,
    )
    if not account:
        raise RuntimeError(f"Missing account: {account_name}")
    if account.company != COMPANY or account.is_group or account.disabled:
        raise RuntimeError(f"Invalid account for payroll component: {account_name}")

    doc_data = {key: value for key, value in spec.items() if key != "account"}
    doc_data.update(
        {
            "doctype": "Salary Component",
            "accounts": [{"company": COMPANY, "account": account_name}],
        }
    )
    frappe.get_doc(doc_data).insert(ignore_permissions=True)
    created.append(component_name)

frappe.db.commit()
print({"created": created, "existing": existing})
