app_name = "cyce_viaticos"
app_title = "CYCE Viaticos"
app_publisher = "CYCE"
app_description = "Control de viaticos diarios vinculados con asistencia"
app_email = ""
app_license = "MIT"

required_apps = ["erpnext", "hrms"]

after_install = "cyce_viaticos.install.after_install"
after_migrate = "cyce_viaticos.install.after_migrate"

doc_events = {
	"Attendance": {
		"on_submit": "cyce_viaticos.viatico_service.sync_from_attendance",
		"on_cancel": "cyce_viaticos.viatico_service.sync_from_attendance",
		"on_update_after_submit": "cyce_viaticos.viatico_service.sync_from_attendance",
	},
	"Employee Advance": {
		"before_cancel": "cyce_viaticos.accounting.validate_linked_document_cancel",
		"on_cancel": "cyce_viaticos.accounting.ignore_viatico_backlink_after_cancel",
	},
	"Expense Claim": {
		"before_cancel": "cyce_viaticos.accounting.validate_linked_document_cancel",
		"on_cancel": "cyce_viaticos.accounting.ignore_viatico_backlink_after_cancel",
	},
}

scheduler_events = {
	"daily": ["cyce_viaticos.viatico_service.reconcile_due_viaticos"],
}
