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
};
