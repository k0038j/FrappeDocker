import frappe
from frappe import _
from frappe.utils import getdate


def translate_presentation_values(rows, fieldnames):
	"""Translate report-only values without changing canonical database values.

	Query report exports use the values returned by ``execute`` and do not run
	the client-side formatter. Translating these fields on the server therefore
	keeps Desk, PDF/print, CSV, and Excel output aligned with the session
	language while filters and stored values remain canonical.
	"""
	for row in rows:
		for fieldname in fieldnames:
			value = row.get(fieldname)
			if value:
				row[fieldname] = _(value)
	return rows


def get_allowed_viatics(filters, fields):
	filters = frappe._dict(filters or {})
	_validate_period(filters)
	parent_filters = []
	if filters.get("from_date"):
		parent_filters.append(["Viatico", "fecha_hasta", ">=", filters.from_date])
	if filters.get("to_date"):
		parent_filters.append(["Viatico", "fecha_desde", "<=", filters.to_date])
	for filter_name, field_name in (
		("employee", "empleado"),
		("viatic_type", "tipo_viatico"),
		("state", "estado"),
		("integration_state", "estado_integracion_contable"),
		("planilla", "planilla_origen"),
	):
		if filters.get(filter_name):
			parent_filters.append(["Viatico", field_name, "=", filters.get(filter_name)])

	if filters.get("project"):
		project_parents = frappe.get_all(
			"Viatico Dia",
			filters={"proyecto": filters.project, "parenttype": "Viatico"},
			pluck="parent",
			limit_page_length=0,
		)
		if not project_parents:
			return []
		parent_filters.append(["Viatico", "name", "in", list(set(project_parents))])

	return frappe.get_list(
		"Viatico",
		filters=parent_filters,
		fields=fields,
		order_by="fecha_desde desc, name desc",
		limit_page_length=0,
	)


def get_allowed_viatic(name, fields):
	rows = frappe.get_list("Viatico", filters={"name": name}, fields=fields, limit_page_length=1)
	return rows[0] if rows else None


def _validate_period(filters):
	if filters.get("from_date") and filters.get("to_date"):
		if getdate(filters.from_date) > getdate(filters.to_date):
			frappe.throw(_("La fecha desde no puede ser posterior a la fecha hasta."))
