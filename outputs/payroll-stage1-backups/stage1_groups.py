import frappe


GROUPS = (
    "Nomina Mensual INSS",
    "Nomina Quincenal INSS",
)


created = []
existing = []

for group_name in GROUPS:
    if frappe.db.exists("Employee Grade", group_name):
        existing.append(group_name)
        continue

    frappe.get_doc(
        {
            "doctype": "Employee Grade",
            "name": group_name,
        }
    ).insert(ignore_permissions=True)
    created.append(group_name)

frappe.db.commit()
print({"created": created, "existing": existing})
