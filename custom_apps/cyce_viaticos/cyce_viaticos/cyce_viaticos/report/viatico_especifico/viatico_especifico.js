frappe.query_reports["Viatico Especifico"] = {
	filters: [
		{
			fieldname: "viatico",
			label: __("Viático"),
			fieldtype: "Link",
			options: "Viatico",
			reqd: 1,
		},
	],
	formatter(value, row, column, data, default_formatter) {
		if (
			value &&
			["tipo_viatico", "estado_asistencia", "estado", "estado_integracion_contable"].includes(
				column.fieldname,
			)
		) {
			return default_formatter(__(value), row, column, data);
		}
		return default_formatter(value, row, column, data);
	},
};
