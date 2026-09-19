from frappe import _

from cyce_viaticos.cyce_viaticos.report.report_utils import get_allowed_viatics


def execute(filters=None):
	data = get_allowed_viatics(
		filters,
		[
			"name", "empleado", "nombre_empleado", "empresa", "tipo_viatico", "fecha_desde", "fecha_hasta",
			"moneda", "monto_total", "ajuste_anterior_total", "monto_neto", "estado",
			"estado_integracion_contable", "planilla_origen", "anticipo_empleado", "solicitud_gasto",
		],
	)
	return get_columns(), data


def get_columns():
	return [
		{"fieldname":"name","fieldtype":"Link","label":_("Viático"),"options":"Viatico","width":145},
		{"fieldname":"empleado","fieldtype":"Link","label":_("Empleado"),"options":"Employee","width":130},
		{"fieldname":"nombre_empleado","fieldtype":"Data","label":_("Nombre"),"width":180},
		{"fieldname":"empresa","fieldtype":"Link","label":_("Empresa"),"options":"Company","width":130},
		{"fieldname":"tipo_viatico","fieldtype":"Data","label":_("Tipo"),"width":100},
		{"fieldname":"fecha_desde","fieldtype":"Date","label":_("Desde"),"width":95},
		{"fieldname":"fecha_hasta","fieldtype":"Date","label":_("Hasta"),"width":95},
		{"fieldname":"monto_total","fieldtype":"Currency","label":_("Monto total"),"options":"moneda","width":115},
		{"fieldname":"ajuste_anterior_total","fieldtype":"Currency","label":_("Ajuste"),"options":"moneda","width":105},
		{"fieldname":"monto_neto","fieldtype":"Currency","label":_("Monto neto"),"options":"moneda","width":115},
		{"fieldname":"estado","fieldtype":"Data","label":_("Estado"),"width":110},
		{"fieldname":"estado_integracion_contable","fieldtype":"Data","label":_("Integración"),"width":110},
		{"fieldname":"planilla_origen","fieldtype":"Link","label":_("Planilla"),"options":"Planilla Viatico","width":140},
		{"fieldname":"anticipo_empleado","fieldtype":"Link","label":_("Anticipo"),"options":"Employee Advance","width":140},
		{"fieldname":"solicitud_gasto","fieldtype":"Link","label":_("Gasto"),"options":"Expense Claim","width":140},
	]
