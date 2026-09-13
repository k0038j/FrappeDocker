import frappe


SLAB_NAME = "IR Laboral Nicaragua 2026"


if frappe.db.exists("Income Tax Slab", SLAB_NAME):
    result = {"created": [], "existing": [SLAB_NAME]}
else:
    frappe.get_doc(
        {
            "doctype": "Income Tax Slab",
            "name": SLAB_NAME,
            "effective_from": "2026-01-01",
            "company": "CYCE, S.A.",
            "currency": "NIO",
            "disabled": 1,
            "allow_tax_exemption": 0,
            "standard_tax_exemption_amount": 0,
            "tax_relief_limit": 0,
            "slabs": [
                {"from_amount": 0, "to_amount": 100000, "percent_deduction": 0},
                {"from_amount": 100001, "to_amount": 200000, "percent_deduction": 15},
                {"from_amount": 200001, "to_amount": 350000, "percent_deduction": 20},
                {"from_amount": 350001, "to_amount": 500000, "percent_deduction": 25},
                {"from_amount": 500001, "to_amount": 0, "percent_deduction": 30},
            ],
        }
    ).insert(ignore_permissions=True)
    frappe.db.commit()
    result = {"created": [SLAB_NAME], "existing": []}

print(result)
