import frappe
from frappe import _

from cyce_viaticos.cyce_viaticos.report.report_utils import get_allowed_viatic


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("viatico"):
		frappe.throw(_("Seleccione un viático."))
	parent = get_allowed_viatic(
		filters.viatico,
		[
			"name", "empleado", "nombre_empleado", "tipo_viatico", "fecha_desde", "fecha_hasta",
			"moneda", "estado", "estado_integracion_contable", "planilla_origen",
		],
	)
	if not parent:
		return get_columns(), []
	details = frappe.get_all(
		"Viatico Dia",
		filters={"parent": parent.name, "parenttype": "Viatico", "parentfield": "dias"},
		fields=[
			"fecha", "cargo", "destino", "proyecto", "monto", "estado_asistencia", "elegible",
			"ajuste_anterior_aplicado", "monto_neto",
		],
		order_by="fecha asc, idx asc",
		limit_page_length=0,
	)
	data = []
	for row in details:
		row.update(parent)
		data.append(row)
	return get_columns(), data


def get_columns():
	return [
		{"fieldname":"name","fieldtype":"Link","label":_("Viático"),"options":"Viatico","width":145},
		{"fieldname":"empleado","fieldtype":"Link","label":_("Empleado"),"options":"Employee","width":130},
		{"fieldname":"nombre_empleado","fieldtype":"Data","label":_("Nombre"),"width":180},
		{"fieldname":"tipo_viatico","fieldtype":"Data","label":_("Tipo"),"width":100},
		{"fieldname":"fecha","fieldtype":"Date","label":_("Fecha"),"width":100},
		{"fieldname":"cargo","fieldtype":"Link","label":_("Cargo"),"options":"Designation","width":130},
		{"fieldname":"destino","fieldtype":"Data","label":_("Destino"),"width":140},
		{"fieldname":"proyecto","fieldtype":"Link","label":_("Proyecto"),"options":"Project","width":150},
		{"fieldname":"monto","fieldtype":"Currency","label":_("Monto"),"options":"moneda","width":110},
		{"fieldname":"estado_asistencia","fieldtype":"Data","label":_("Asistencia"),"width":150},
		{"fieldname":"ajuste_anterior_aplicado","fieldtype":"Currency","label":_("Ajuste"),"options":"moneda","width":100},
		{"fieldname":"monto_neto","fieldtype":"Currency","label":_("Neto"),"options":"moneda","width":110},
		{"fieldname":"estado","fieldtype":"Data","label":_("Estado"),"width":105},
		{"fieldname":"estado_integracion_contable","fieldtype":"Data","label":_("Integración"),"width":110},
	]
