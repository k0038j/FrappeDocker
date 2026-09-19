import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from cyce_viaticos.accounting import cancel_accounting_document, create_accounting_document
from cyce_viaticos.install import APPROVER_USER
from cyce_viaticos.rules import MAX_VIATIC_PERIOD_DAYS, build_inclusive_date_range
from cyce_viaticos.viatico_service import (
	apply_adjustments,
	money,
	prepare_viatico,
	reverse_adjustments,
	validate_source_adjustments_before_cancel,
)


class Viatico(Document):
	@frappe.whitelist()
	def recalcular_totales_borrador(self):
		self._validate_draft_action()
		prepare_viatico(self)

	@frappe.whitelist()
	def obtener_dias_precargados(self):
		self._validate_draft_action()

		if not self.fecha_desde or not self.fecha_hasta:
			frappe.throw(_("Seleccione la fecha inicial y la fecha final."))
		if money(self.monto_diario) <= 0:
			frappe.throw(_("El monto diario debe ser mayor que cero."))
		if not self.destino_predeterminado or not self.destino_predeterminado.strip():
			frappe.throw(_("Ingrese el destino predeterminado."))
		if not self.proyecto_predeterminado:
			frappe.throw(_("Seleccione el proyecto predeterminado."))

		employee = frappe.db.get_value(
			"Employee",
			self.empleado,
			["status", "company", "designation"],
			as_dict=True,
		)
		if not employee or employee.status != "Active":
			frappe.throw(_("Seleccione un empleado activo."))
		if not employee.designation:
			frappe.throw(_("El empleado debe tener un cargo asignado."))

		if not frappe.db.exists("Project", self.proyecto_predeterminado):
			frappe.throw(_("El proyecto {0} no existe.").format(self.proyecto_predeterminado))
		project_company = frappe.db.get_value("Project", self.proyecto_predeterminado, "company")
		if project_company and project_company != employee.company:
			frappe.throw(
				_("El proyecto {0} pertenece a otra empresa.").format(self.proyecto_predeterminado)
			)

		try:
			dates = build_inclusive_date_range(getdate(self.fecha_desde), getdate(self.fecha_hasta))
		except ValueError as error:
			if str(error) == "end_before_start":
				frappe.throw(_("La fecha final no puede ser anterior a la fecha inicial."))
			frappe.throw(
				_("El período no puede superar {0} días.").format(MAX_VIATIC_PERIOD_DAYS)
			)

		return [
			{
				"fecha": str(day),
				"monto": float(money(self.monto_diario)),
				"cargo": employee.designation,
				"destino": self.destino_predeterminado.strip(),
				"proyecto": self.proyecto_predeterminado,
			}
			for day in dates
		]

	def _validate_draft_action(self):
		if self.docstatus != 0:
			frappe.throw(_("Esta acción solo está disponible en un viático en borrador."))

		permission_type = "create" if self.is_new() else "write"
		if not frappe.has_permission("Viatico", permission_type, doc=self):
			frappe.throw(_("No tiene permiso para modificar este viático."), frappe.PermissionError)

	def validate(self):
		prepare_viatico(self)

	def before_submit(self):
		self._validate_approver("aprobar")
		prepare_viatico(self)
		if money(self.monto_neto) <= 0 and money(self.ajuste_anterior_total) <= 0:
			frappe.throw(_("El viático no tiene días elegibles ni ajustes para aplicar."))
		self.estado = (
			"Aprobado"
			if any(row.estado_asistencia == "Pendiente de conciliación" for row in self.dias)
			else "Conciliado"
		)

	def on_submit(self):
		apply_adjustments(self)
		create_accounting_document(self)

	def before_cancel(self):
		self._validate_approver("cancelar")
		self._validate_planilla_cancel()
		cancel_accounting_document(self)
		validate_source_adjustments_before_cancel(self)
		reverse_adjustments(self)
		self.estado = "Cancelado"

	def _validate_approver(self, action):
		if frappe.session.user != APPROVER_USER:
			frappe.throw(
				_("Solo {0} puede {1} un viático.").format(APPROVER_USER, action),
				frappe.PermissionError,
			)

	def _validate_planilla_cancel(self):
		if not self.planilla_origen:
			return
		if getattr(frappe.flags, "planilla_viatico_cancel", None) == self.planilla_origen:
			return
		if frappe.db.get_value("Planilla Viatico", self.planilla_origen, "docstatus") == 1:
			frappe.throw(
				_("Cancele la planilla {0}; este viático pertenece a una aprobación masiva.").format(
					self.planilla_origen
				)
			)
