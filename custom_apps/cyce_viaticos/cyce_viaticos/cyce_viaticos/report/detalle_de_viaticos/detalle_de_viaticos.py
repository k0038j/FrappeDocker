import frappe
from frappe import _

from cyce_viaticos.cyce_viaticos.report.report_utils import get_allowed_viatics


def execute(filters=None):
	filters = frappe._dict(filters or {})
	parents = get_allowed_viatics(
		filters,
		["name", "empleado", "nombre_empleado", "empresa", "tipo_viatico", "moneda", "estado", "estado_integracion_contable", "planilla_origen"],
	)
	if not parents:
		return get_columns(), []
	parent_by_name = {row.name: row for row in parents}
	detail_filters = {
		"parent": ["in", list(parent_by_name)],
		"parenttype": "Viatico",
		"parentfield": "dias",
	}
	if filters.get("from_date"):
		detail_filters["fecha"] = [">=", filters.from_date]
	if filters.get("to_date"):
		if "fecha" in detail_filters:
			detail_filters["fecha"] = ["between", [filters.from_date, filters.to_date]]
		else:
			detail_filters["fecha"] = ["<=", filters.to_date]
	if filters.get("project"):
		detail_filters["proyecto"] = filters.project
	details = frappe.get_all(
		"Viatico Dia",
		filters=detail_filters,
		fields=[
			"parent", "fecha", "cargo", "destino", "proyecto", "monto", "asistencia", "estado_asistencia",
			"elegible", "motivo_no_elegible", "ajuste_generado", "ajuste_anterior_aplicado", "monto_neto",
		],
		order_by="fecha desc, parent desc, idx asc",
		limit_page_length=0,
	)
	data = []
	for row in details:
		parent = parent_by_name[row.parent]
		row.update(parent)
		row["viatico"] = row.pop("parent")
		data.append(row)
	return get_columns(), data


def get_columns():
	return [
		{"fieldname":"viatico","fieldtype":"Link","label":_("Viático"),"options":"Viatico","width":145},
		{"fieldname":"empleado","fieldtype":"Link","label":_("Empleado"),"options":"Employee","width":130},
		{"fieldname":"nombre_empleado","fieldtype":"Data","label":_("Nombre"),"width":180},
		{"fieldname":"tipo_viatico","fieldtype":"Data","label":_("Tipo"),"width":100},
		{"fieldname":"fecha","fieldtype":"Date","label":_("Fecha"),"width":100},
		{"fieldname":"cargo","fieldtype":"Link","label":_("Cargo"),"options":"Designation","width":130},
		{"fieldname":"destino","fieldtype":"Data","label":_("Destino"),"width":140},
		{"fieldname":"proyecto","fieldtype":"Link","label":_("Proyecto"),"options":"Project","width":150},
		{"fieldname":"monto","fieldtype":"Currency","label":_("Monto"),"options":"moneda","width":105},
		{"fieldname":"asistencia","fieldtype":"Link","label":_("Asistencia"),"options":"Attendance","width":135},
		{"fieldname":"estado_asistencia","fieldtype":"Data","label":_("Estado asistencia"),"width":150},
		{"fieldname":"elegible","fieldtype":"Check","label":_("Elegible"),"width":75},
		{"fieldname":"ajuste_anterior_aplicado","fieldtype":"Currency","label":_("Ajuste"),"options":"moneda","width":100},
		{"fieldname":"monto_neto","fieldtype":"Currency","label":_("Neto"),"options":"moneda","width":105},
		{"fieldname":"estado","fieldtype":"Data","label":_("Estado viático"),"width":110},
		{"fieldname":"estado_integracion_contable","fieldtype":"Data","label":_("Integración"),"width":110},
	]
