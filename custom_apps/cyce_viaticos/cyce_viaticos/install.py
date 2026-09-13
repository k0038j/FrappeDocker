import frappe
from frappe import _

APPROVER_ROLE = "Aprobador de Viaticos"
APPROVER_USER = "nelly@cise.com"


def after_install():
	ensure_exclusive_approver()
	from cyce_viaticos.accounting import ensure_accounting_setup

	ensure_accounting_setup()


def after_migrate():
	ensure_exclusive_approver()
	from cyce_viaticos.accounting import ensure_accounting_setup

	ensure_accounting_setup()


def ensure_exclusive_approver():
	"""Keep the operational viatic approval role assigned only to Nelly."""
	user_data = frappe.db.get_value("User", APPROVER_USER, ["name", "enabled", "user_type"], as_dict=True)
	if not user_data or not user_data.enabled or user_data.user_type != "System User":
		frappe.throw(_("The required approver {0} is not an enabled System User.").format(APPROVER_USER))

	if not frappe.db.exists("Role", APPROVER_ROLE):
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": APPROVER_ROLE,
				"desk_access": 1,
				"is_custom": 0,
			}
		).insert(ignore_permissions=True)

	assignments = frappe.get_all(
		"Has Role",
		filters={"role": APPROVER_ROLE, "parenttype": "User"},
		fields=["name", "parent"],
	)
	for assignment in assignments:
		if assignment.parent != APPROVER_USER:
			frappe.db.delete("Has Role", {"name": assignment.name})

	approver = frappe.get_doc("User", APPROVER_USER)
	if APPROVER_ROLE not in {row.role for row in approver.roles}:
		approver.add_roles(APPROVER_ROLE)
