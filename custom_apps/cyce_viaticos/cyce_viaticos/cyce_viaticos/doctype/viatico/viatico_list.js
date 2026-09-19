frappe.listview_settings["Viatico"] = {
	add_fields: ["estado", "estado_integracion_contable", "monto_total", "moneda"],

	get_indicator(doc) {
		const colors = {
			Borrador: "gray",
			"Pendiente de aprobación": "orange",
			Aprobado: "blue",
			Conciliado: "green",
			Rechazado: "red",
			Cancelado: "red",
		};
		return [__(doc.estado), colors[doc.estado] || "gray", `estado,=,${doc.estado}`];
	},
};
