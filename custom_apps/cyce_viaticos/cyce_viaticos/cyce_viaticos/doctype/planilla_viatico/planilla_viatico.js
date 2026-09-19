const PLANILLA_LOCKED_FIELDS = [
	"plantilla",
	"empresa",
	"fecha_desde",
	"fecha_hasta",
	"tipo_viatico",
	"moneda",
	"monto_diario",
	"destino",
	"proyecto",
	"empleados",
];

frappe.ui.form.on("Planilla Viatico", {
	setup(frm) {
		frm.set_query("plantilla", () => ({ filters: { activa: 1 } }));
		frm.set_query("proyecto", () => ({ filters: { company: frm.doc.empresa } }));
	},

	async plantilla(frm) {
		if (!frm.doc.plantilla) return;
		const template = await frappe.db.get_doc("Plantilla Viatico", frm.doc.plantilla);
		await frm.set_value({
			empresa: template.empresa,
			tipo_viatico: template.tipo_viatico,
			moneda: template.moneda,
			monto_diario: template.monto_diario,
			destino: template.destino,
			proyecto: template.proyecto,
		});
	},

	refresh(frm) {
		const locked = frm.doc.estado !== "Borrador";
		PLANILLA_LOCKED_FIELDS.forEach((fieldname) => frm.set_df_property(fieldname, "read_only", locked));
		if (!frm.is_new() && frm.doc.estado === "Borrador" && frm.doc.empleados?.length) {
			frm.add_custom_button(__("Generar borradores"), async () => {
				if (frm.dirty()) await frm.save();
				await frm.call({ doc: frm.doc, method: "generar_borradores", freeze: true, freeze_message: __("Generando viáticos...") });
				await frm.reload_doc();
			});
		}
		if (!frm.is_new() && frm.doc.empleados?.some((row) => row.viatico)) {
			frm.add_custom_button(__("Ver viáticos"), () => {
				frappe.set_route("List", "Viatico", { planilla_origen: frm.doc.name });
			});
		}
	},

	seleccionar_empleados(frm) {
		if (!frm.doc.empresa) {
			frappe.msgprint(__("Seleccione una empresa."));
			return;
		}
		const employee_selector = new frappe.ui.form.MultiSelectDialog({
			doctype: "Employee",
			target: frm,
			primary_action_label: __("Guardar"),
			setters: { company: frm.doc.empresa },
			read_only_setters: ["company"],
			columns: ["name", "employee_name", "cargo"],
			get_query() {
				return {
					query: "cyce_viaticos.cyce_viaticos.doctype.planilla_viatico.planilla_viatico.empleados_activos",
					filters: { company: frm.doc.empresa },
				};
			},
			action: async (selections) => {
				await frm.call({ doc: frm.doc, method: "agregar_empleados", args: { empleados: selections } });
				cur_dialog.hide();
				frm.refresh_field("empleados");
			},
		});
		frappe.model.with_doctype("Employee", () => {
			if (!frappe.model.can_create("Employee")) {
				employee_selector.dialog.get_secondary_btn().addClass("hide");
				return;
			}
			employee_selector.dialog.set_secondary_action_label(__("Crear empleado"));
			employee_selector.dialog.set_secondary_action(() => {
				crear_empleado_para_planilla(frm, employee_selector);
			});
		});
	},
});

frappe.ui.form.on("Planilla Viatico Empleado", {
	monto_diario: actualizar_estimado,
});

function actualizar_estimado(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!frm.doc.fecha_desde || !frm.doc.fecha_hasta) return;
	const days = frappe.datetime.get_day_diff(frm.doc.fecha_hasta, frm.doc.fecha_desde) + 1;
	frappe.model.set_value(cdt, cdn, "total_estimado", flt(row.monto_diario) * Math.max(days, 0));
}

function crear_empleado_para_planilla(frm, employee_selector) {
	const employee = frappe.model.get_new_doc("Employee");
	employee.company = frm.doc.empresa;
	employee.status = "Active";

	class ViaticoEmployeeQuickEntryForm extends frappe.ui.form.QuickEntryForm {
		set_meta_and_mandatory_fields() {
			super.set_meta_and_mandatory_fields();
			if (!this.docfields.some((field) => field.fieldname === "designation")) {
				const designation = frappe.meta.get_docfield("Employee", "designation");
				this.docfields.push({ ...designation, reqd: 1 });
			}
		}
	}

	new ViaticoEmployeeQuickEntryForm(
		"Employee",
		() => employee_selector.get_results(),
		(quick_entry) => quick_entry.toggle_enable(["company", "status"], false),
		employee,
		true
	).setup();
}
