import frappe
from frappe import _
from frappe.model.document import Document

from cyce_viaticos.accounting import cancel_accounting_document, create_accounting_document
from cyce_viaticos.install import APPROVER_USER
from cyce_viaticos.viatico_service import (
	apply_adjustments,
	money,
	prepare_viatico,
	reverse_adjustments,
	validate_source_adjustments_before_cancel,
)


class Viatico(Document):
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
