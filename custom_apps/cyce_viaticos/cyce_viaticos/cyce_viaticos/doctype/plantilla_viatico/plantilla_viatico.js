frappe.ui.form.on("Plantilla Viatico", {
	setup(frm) {
		frm.set_query("proyecto", () => ({ filters: { company: frm.doc.empresa } }));
	},

	refresh(frm) {
		if (!frm.is_new() && frm.doc.activa) {
			frm.add_custom_button(__("Crear planilla"), () => {
				frappe.new_doc("Planilla Viatico", { plantilla: frm.doc.name });
			});
		}
	},
});
