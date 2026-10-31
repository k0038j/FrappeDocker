frappe.listview_settings["Payroll Import"] = {
	add_fields: ["period_end"],

	formatters: {
		period_start(value, df, doc) {
			if (!value) return "";

			const start = frappe.datetime.str_to_user(value);
			const end = doc.period_end ? frappe.datetime.str_to_user(doc.period_end) : "";
			return end ? `${start} – ${end}` : start;
		},
	},

	onload(listview) {
		if (listview.view !== "List") return;

		listview.columns = listview.columns.map((column) => {
			if (column.df?.fieldname !== "period_start") return column;
			return {
				...column,
				df: { ...column.df, label: __("Payroll Period") },
			};
		});
		listview.render_header(true);
	},
};
