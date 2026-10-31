import frappe


def execute():
	"""Copy the accounting dimension already selected on linked Payroll Entries."""
	if not frappe.db.table_exists("Payroll Import"):
		return

	imports = frappe.get_all(
		"Payroll Import",
		filters={"cost_center": ("is", "not set"), "payroll_entry": ("is", "set")},
		fields=["name", "payroll_entry"],
	)
	for payroll_import in imports:
		cost_center = frappe.db.get_value("Payroll Entry", payroll_import.payroll_entry, "cost_center")
		if cost_center:
			frappe.db.set_value(
				"Payroll Import",
				payroll_import.name,
				"cost_center",
				cost_center,
				update_modified=False,
			)
