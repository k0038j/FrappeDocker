import frappe
from frappe import _
from frappe.utils import flt, today

from cyce_viaticos.install import APPROVER_USER
from cyce_viaticos.viatico_service import money

COMPANY = "CYCE, S.A."
ADVANCE_ACCOUNT = "1143 - Anticipos a empleados - CYCE"
EXPENSE_ACCOUNT = "511015 - Viáticos - CYCE"
PAYABLE_ACCOUNT = "2116 - Gastos por pagar a empleados - CYCE"
EXPENSE_TYPE = "Viáticos"


def ensure_accounting_setup() -> None:
	_validate_account(ADVANCE_ACCOUNT, "Asset", "Receivable")
	_validate_account(EXPENSE_ACCOUNT, "Expense", "Expense Account")
	_validate_account(PAYABLE_ACCOUNT, "Liability", "Payable")

	company = frappe.db.get_value(
		"Company",
		COMPANY,
		["default_employee_advance_account", "default_expense_claim_payable_account"],
		as_dict=True,
	)
	if not company:
		frappe.throw(_("No existe la empresa {0}.").format(COMPANY))
	if company.default_employee_advance_account != ADVANCE_ACCOUNT:
		frappe.throw(_("La cuenta predeterminada de anticipos de empleados no coincide con {0}.").format(ADVANCE_ACCOUNT))
	if company.default_expense_claim_payable_account != PAYABLE_ACCOUNT:
		frappe.throw(_("La cuenta predeterminada de gastos por pagar no coincide con {0}.").format(PAYABLE_ACCOUNT))

	if frappe.db.exists("Expense Claim Type", EXPENSE_TYPE):
		expense_type = frappe.get_doc("Expense Claim Type", EXPENSE_TYPE)
		company_rows = [row for row in expense_type.accounts if row.company == COMPANY]
		if company_rows and company_rows[0].default_account != EXPENSE_ACCOUNT:
			frappe.throw(
				_("El tipo de gasto {0} ya usa otra cuenta para {1}.").format(EXPENSE_TYPE, COMPANY)
			)
		if not company_rows:
			expense_type.append("accounts", {"company": COMPANY, "default_account": EXPENSE_ACCOUNT})
			expense_type.save(ignore_permissions=True)
		return

	frappe.get_doc(
		{
			"doctype": "Expense Claim Type",
			"expense_type": EXPENSE_TYPE,
			"description": "Viáticos diarios controlados por asistencia.",
			"accounts": [{"company": COMPANY, "default_account": EXPENSE_ACCOUNT}],
		}
	).insert(ignore_permissions=True)


def create_accounting_document(doc) -> None:
	if doc.anticipo_empleado or doc.solicitud_gasto:
		frappe.throw(_("El viático ya tiene un documento contable relacionado."))

	if money(doc.monto_neto) <= 0:
		_set_integration_result(doc, "No requerido")
		return

	ensure_accounting_setup()
	if doc.tipo_viatico == "Adelantado":
		advance = _create_employee_advance(doc)
		_set_integration_result(doc, "Generado", employee_advance=advance.name)
		return
	if doc.tipo_viatico == "Reposición":
		expense_claim = _create_expense_claim(doc)
		_set_integration_result(doc, "Generado", expense_claim=expense_claim.name)
		return

	frappe.throw(_("El tipo de viático {0} no admite integración contable.").format(doc.tipo_viatico))


def cancel_accounting_document(doc) -> None:
	if doc.anticipo_empleado and doc.solicitud_gasto:
		frappe.throw(_("El viático tiene más de un documento contable relacionado."))

	if doc.anticipo_empleado:
		advance = frappe.get_doc("Employee Advance", doc.anticipo_empleado)
		if flt(advance.paid_amount) or flt(advance.claimed_amount) or flt(advance.return_amount):
			frappe.throw(
				_("No se puede cancelar: el anticipo {0} ya tiene movimientos.").format(advance.name)
			)
		_cancel_linked_document(advance)
	elif doc.solicitud_gasto:
		expense_claim = frappe.get_doc("Expense Claim", doc.solicitud_gasto)
		if expense_claim.is_paid or flt(expense_claim.total_amount_reimbursed):
			frappe.throw(
				_("No se puede cancelar: la solicitud de gasto {0} ya fue pagada.").format(
					expense_claim.name
				)
			)
		_cancel_linked_document(expense_claim)

	doc.estado_integracion_contable = "Cancelado"


def validate_linked_document_cancel(doc, method=None) -> None:
	if getattr(frappe.flags, "viatico_accounting_cancel", False):
		return
	fieldname = "anticipo_empleado" if doc.doctype == "Employee Advance" else "solicitud_gasto"
	viatic = frappe.db.get_value("Viatico", {fieldname: doc.name, "docstatus": 1}, "name")
	if viatic:
		frappe.throw(
			_("Cancele primero el viático {0}; este documento fue generado automáticamente.").format(
				viatic
			)
		)


def ignore_viatico_backlink_after_cancel(doc, method=None) -> None:
	if not getattr(frappe.flags, "viatico_accounting_cancel", False):
		return
	ignored_doctypes = tuple(getattr(doc, "ignore_linked_doctypes", ()) or ())
	if "Viatico" not in ignored_doctypes:
		doc.ignore_linked_doctypes = (*ignored_doctypes, "Viatico")


def _create_employee_advance(doc):
	advance = frappe.get_doc(
		{
			"doctype": "Employee Advance",
			"employee": doc.empleado,
			"posting_date": today(),
			"company": doc.empresa,
			"currency": doc.moneda,
			"purpose": _purpose(doc),
			"advance_amount": float(money(doc.monto_neto)),
			"advance_account": ADVANCE_ACCOUNT,
		}
	)
	return _insert_and_submit(advance)


def _create_expense_claim(doc):
	cost_center = frappe.db.get_value("Company", doc.empresa, "cost_center")
	if not cost_center:
		frappe.throw(_("La empresa {0} no tiene centro de costo predeterminado.").format(doc.empresa))

	expenses = []
	for row in doc.dias:
		if not row.elegible or money(row.monto_neto) <= 0:
			continue
		expenses.append(
			{
				"expense_date": row.fecha,
				"expense_type": EXPENSE_TYPE,
				"default_account": EXPENSE_ACCOUNT,
				"description": _expense_description(doc.name, row),
				"amount": float(money(row.monto_neto)),
				"sanctioned_amount": float(money(row.monto_neto)),
				"cost_center": cost_center,
				"project": row.proyecto,
			}
		)

	if not expenses:
		frappe.throw(_("El viático no tiene valores netos para generar la solicitud de gasto."))

	projects = {row["project"] for row in expenses}
	expense_claim = frappe.get_doc(
		{
			"doctype": "Expense Claim",
			"employee": doc.empleado,
			"company": doc.empresa,
			"expense_approver": APPROVER_USER,
			"approval_status": "Approved",
			"currency": doc.moneda,
			"exchange_rate": 1,
			"posting_date": today(),
			"is_paid": 0,
			"payable_account": PAYABLE_ACCOUNT,
			"cost_center": cost_center,
			"project": next(iter(projects)) if len(projects) == 1 else None,
			"remark": _purpose(doc),
			"expenses": expenses,
		}
	)
	return _insert_and_submit(expense_claim)


def _insert_and_submit(doc):
	doc.flags.ignore_permissions = True
	doc.insert()
	doc.flags.ignore_permissions = True
	doc.submit()
	frappe.share.add(
		doc.doctype,
		doc.name,
		user=APPROVER_USER,
		read=1,
		flags={"ignore_share_permission": True},
	)
	return doc


def _cancel_linked_document(doc) -> None:
	if doc.docstatus == 2:
		return
	if doc.docstatus != 1:
		frappe.throw(_("El documento relacionado {0} no está enviado.").format(doc.name))

	previous_flag = getattr(frappe.flags, "viatico_accounting_cancel", False)
	previous_ignored_doctypes = tuple(getattr(doc, "ignore_linked_doctypes", ()) or ())
	frappe.flags.viatico_accounting_cancel = True
	doc.ignore_linked_doctypes = (*previous_ignored_doctypes, "Viatico")
	try:
		doc.flags.ignore_permissions = True
		doc.cancel()
	finally:
		frappe.flags.viatico_accounting_cancel = previous_flag
		doc.ignore_linked_doctypes = previous_ignored_doctypes


def _set_integration_result(doc, state, employee_advance=None, expense_claim=None) -> None:
	values = {
		"estado_integracion_contable": state,
		"anticipo_empleado": employee_advance,
		"solicitud_gasto": expense_claim,
	}
	for fieldname, value in values.items():
		doc.set(fieldname, value)
	frappe.db.set_value("Viatico", doc.name, values, update_modified=False)


def _purpose(doc) -> str:
	return _("Viático {0}, período {1} a {2}.").format(doc.name, doc.fecha_desde, doc.fecha_hasta)


def _expense_description(viatic_name, row) -> str:
	return _("Viático {0}. Destino: {1}. Cargo: {2}.").format(
		viatic_name, row.destino, row.cargo
	)


def _validate_account(account_name, root_type, account_type) -> None:
	account = frappe.db.get_value(
		"Account",
		account_name,
		["company", "root_type", "account_type", "is_group", "disabled"],
		as_dict=True,
	)
	if (
		not account
		or account.company != COMPANY
		or account.root_type != root_type
		or account.account_type != account_type
		or account.is_group
		or account.disabled
	):
		frappe.throw(_("La cuenta autorizada {0} no tiene una configuración válida.").format(account_name))
