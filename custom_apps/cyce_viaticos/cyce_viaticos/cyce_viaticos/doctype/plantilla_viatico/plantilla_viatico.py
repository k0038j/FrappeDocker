import frappe
from frappe import _
from frappe.model.document import Document

from cyce_viaticos.viatico_service import money


class PlantillaViatico(Document):
	def validate(self):
		if money(self.monto_diario) <= 0:
			frappe.throw(_("El monto diario debe ser mayor que cero."))
		if not (self.destino or "").strip():
			frappe.throw(_("Ingrese el destino de la plantilla."))
		self.destino = self.destino.strip()
		_validate_project(self.proyecto, self.empresa)


def _validate_project(project: str, company: str) -> None:
	if not project or not frappe.db.exists("Project", project):
		frappe.throw(_("Seleccione un proyecto válido."))
	project_company = frappe.db.get_value("Project", project, "company")
	if project_company and project_company != company:
		frappe.throw(_("El proyecto {0} pertenece a otra empresa.").format(project))
