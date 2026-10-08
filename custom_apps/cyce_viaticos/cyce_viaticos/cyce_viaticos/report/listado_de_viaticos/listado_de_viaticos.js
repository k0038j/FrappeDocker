frappe.query_reports["Listado de Viaticos"] = {
	filters: viatico_report_filters(),
	formatter(value, row, column, data, default_formatter) {
		if (
			value &&
			["tipo_viatico", "estado", "estado_integracion_contable"].includes(column.fieldname)
		) {
			return default_formatter(__(value), row, column, data);
		}
		return default_formatter(value, row, column, data);
	},
};

function viatico_report_filters() {
	return [
		{ fieldname: "from_date", label: __("Fecha desde"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("Fecha hasta"), fieldtype: "Date" },
		{ fieldname: "employee", label: __("Empleado"), fieldtype: "Link", options: "Employee" },
		{
			fieldname: "viatic_type",
			label: __("Tipo"),
			fieldtype: "Select",
			options: translated_select_options(["Adelantado", "Reposición"]),
		},
		{
			fieldname: "state",
			label: __("Estado"),
			fieldtype: "Select",
			options: translated_select_options([
				"Borrador",
				"Pendiente de aprobación",
				"Aprobado",
				"Rechazado",
				"Conciliado",
				"Cancelado",
			]),
		},
		{ fieldname: "project", label: __("Proyecto"), fieldtype: "Link", options: "Project" },
		{
			fieldname: "integration_state",
			label: __("Integración"),
			fieldtype: "Select",
			options: translated_select_options(["Pendiente", "Generado", "No requerido", "Cancelado"]),
		},
		{ fieldname: "planilla", label: __("Planilla"), fieldtype: "Link", options: "Planilla Viatico" },
	];
}

function translated_select_options(values) {
	return ["", ...values.map((value) => ({ value, label: __(value) }))];
}
