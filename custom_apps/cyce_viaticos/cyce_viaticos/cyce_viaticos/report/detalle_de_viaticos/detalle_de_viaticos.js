frappe.query_reports["Detalle de Viaticos"] = {
	filters: [
		{ fieldname: "from_date", label: __("Fecha desde"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("Fecha hasta"), fieldtype: "Date" },
		{ fieldname: "employee", label: __("Empleado"), fieldtype: "Link", options: "Employee" },
		{ fieldname: "viatic_type", label: __("Tipo"), fieldtype: "Select", options: "\nAdelantado\nReposición" },
		{ fieldname: "state", label: __("Estado"), fieldtype: "Select", options: "\nBorrador\nPendiente de aprobación\nAprobado\nRechazado\nConciliado\nCancelado" },
		{ fieldname: "project", label: __("Proyecto"), fieldtype: "Link", options: "Project" },
		{ fieldname: "integration_state", label: __("Integración"), fieldtype: "Select", options: "\nPendiente\nGenerado\nNo requerido\nCancelado" },
		{ fieldname: "planilla", label: __("Planilla"), fieldtype: "Link", options: "Planilla Viatico" },
	],
};
