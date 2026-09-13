import frappe


PERIOD_NAME = "Periodo de Nomina 2026 - CYCE"

if frappe.db.exists("Payroll Period", PERIOD_NAME):
    result = {"created": [], "existing": [PERIOD_NAME]}
else:
    frappe.get_doc(
        {
            "doctype": "Payroll Period",
            "name": PERIOD_NAME,
            "company": "CYCE, S.A.",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
        }
    ).insert(ignore_permissions=True)
    frappe.db.commit()
    result = {"created": [PERIOD_NAME], "existing": []}

print(result)
