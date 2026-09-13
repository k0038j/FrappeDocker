import frappe


COMPANY = "CYCE, S.A."
CURRENCY = "NIO"
STRUCTURES = (
    ("Nomina Mensual INSS", "Monthly"),
    ("Nomina Quincenal INSS", "Bimonthly"),
)


required_components = ("Basic", "INSS Laboral", "IR Laboral")
missing_components = [
    component
    for component in required_components
    if not frappe.db.exists("Salary Component", component)
]
if missing_components:
    raise RuntimeError(f"Missing salary components: {missing_components}")

created = []
existing = []

for structure_name, frequency in STRUCTURES:
    if frappe.db.exists("Salary Structure", structure_name):
        existing.append(structure_name)
        continue

    frappe.get_doc(
        {
            "doctype": "Salary Structure",
            "name": structure_name,
            "company": COMPANY,
            "currency": CURRENCY,
            "payroll_frequency": frequency,
            "salary_slip_based_on_timesheet": 0,
            "is_active": "No",
            "is_default": "No",
            "earnings": [
                {
                    "salary_component": "Basic",
                    "abbr": "B",
                    "depends_on_payment_days": 1,
                    "is_tax_applicable": 1,
                    "amount_based_on_formula": 1,
                    "formula": "base",
                }
            ],
            "deductions": [
                {
                    "salary_component": "INSS Laboral",
                    "abbr": "INSSL",
                    "depends_on_payment_days": 1,
                    "exempted_from_income_tax": 1,
                    "amount_based_on_formula": 1,
                    "formula": "base * 0.07",
                },
                {
                    "salary_component": "IR Laboral",
                    "abbr": "IRL",
                    "depends_on_payment_days": 0,
                    "variable_based_on_taxable_salary": 1,
                    "amount_based_on_formula": 0,
                },
            ],
        }
    ).insert(ignore_permissions=True)
    created.append(structure_name)

frappe.db.commit()
print({"created": created, "existing": existing})
