frappe.ui.form.on("Viatico", {
	setup(frm) {
		frm.set_query("proyecto_predeterminado", () => {
			const filters = {};
			if (frm.doc.empresa) {
				filters.company = frm.doc.empresa;
			}
			return { filters };
		});
	},

	generar_dias(frm) {
		const generate = () => generate_daily_rows(frm);
		if (frm.doc.dias?.length) {
			frappe.confirm(
				__(
					"Ya existen días cargados. Si continúa, se reemplazarán, incluyendo cualquier monto modificado manualmente.",
				),
				generate,
			);
			return;
		}
		generate();
	},
});

frappe.ui.form.on("Viatico Dia", {
	monto(frm) {
		schedule_total_refresh(frm);
	},

	dias_remove(frm) {
		schedule_total_refresh(frm);
	},
});

function generate_daily_rows(frm) {
	return frm
		.call({
			doc: frm.doc,
			method: "obtener_dias_precargados",
			freeze: true,
			freeze_message: __("Generando días del viático..."),
		})
		.then(async (response) => {
			const rows = response.message || [];
			frm.clear_table("dias");
			for (const values of rows) {
				frm.add_child("dias", values);
			}
			frm.refresh_field("dias");
			frm.dirty();
			await refresh_draft_totals(frm);
			frappe.show_alert({
				message: __("Se generaron {0} días. Puede modificar cualquier monto manualmente.", [
					rows.length,
				]),
				indicator: "green",
			});
		});
}

function schedule_total_refresh(frm) {
	window.clearTimeout(frm.__viatico_total_refresh_timeout);
	frm.__viatico_total_refresh_timeout = window.setTimeout(() => {
		refresh_draft_totals(frm);
	}, 300);
}

function refresh_draft_totals(frm) {
	if (frm.doc.docstatus !== 0) return Promise.resolve();

	const rows = frm.doc.dias || [];
	const requested_total = rows.reduce((total, row) => total + flt(row.monto), 0);
	frm.set_value("monto_total", requested_total);

	if (!rows.length) {
		return frm.set_value({
			ajuste_anterior_total: 0,
			monto_neto: 0,
		});
	}
	if (
		!frm.doc.empleado ||
		!frm.doc.tipo_viatico ||
		rows.some(
			(row) =>
				!row.fecha ||
				flt(row.monto) <= 0 ||
				!row.cargo ||
				!row.destino ||
				!row.proyecto,
		)
	) {
		return Promise.resolve();
	}

	return frm.call({
		doc: frm.doc,
		method: "recalcular_totales_borrador",
		freeze: false,
	});
}
