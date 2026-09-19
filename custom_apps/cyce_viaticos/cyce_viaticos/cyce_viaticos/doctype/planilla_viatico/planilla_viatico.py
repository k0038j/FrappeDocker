import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, getdate

from cyce_viaticos.install import APPROVER_USER
from cyce_viaticos.rules import MAX_VIATIC_PERIOD_DAYS, build_inclusive_date_range
from cyce_viaticos.viatico_service import money

EXCLUDED_EMPLOYEE = "HR-EMP-00002"
GENERATED_STATE = "Borradores generados"
LOCKED_FIELDS = (
	"plantilla",
	"empresa",
	"fecha_desde",
	"fecha_hasta",
	"tipo_viatico",
	"moneda",
	"monto_diario",
	"destino",
	"proyecto",
)
LOCKED_CHILD_FIELDS = ("empleado", "monto_diario", "destino", "proyecto", "viatico")
EMPLOYEE_ROW_FIELDS = (
	"empleado",
	"nombre_empleado",
	"cargo",
	"monto_diario",
	"destino",
	"proyecto",
	"viatico",
	"estado_viatico",
	"total_estimado",
)


class PlanillaViatico(Document):
	def validate(self):
		self._validate_generated_fields_unchanged()
		dates = _period_dates(self.fecha_desde, self.fecha_hasta)
		self.aprobador = APPROVER_USER
		if self.docstatus == 0 and self.estado not in ("Borrador", GENERATED_STATE):
			self.estado = "Borrador"
		self._validate_template()
		self._validate_employees(dates)

	@frappe.whitelist()
	def agregar_empleados(self, empleados):
		self._validate_draft_action()
		if not self.estado:
			self.estado = "Borrador"
		if self.estado != "Borrador":
			frappe.throw(_("No se pueden agregar empleados después de generar los borradores."))
		selected = _as_employee_list(empleados)
		if not selected:
			return
		for row in list(self.empleados):
			if _is_blank_employee_row(row):
				self.remove(row)

		dates = _period_dates(self.fecha_desde, self.fecha_hasta)
		rows = frappe.get_all(
			"Employee",
			filters={
				"name": ["in", selected],
				"status": "Active",
				"company": self.empresa,
			},
			fields=["name", "employee_name", "designation"],
			limit_page_length=0,
		)
		by_name = {row.name: row for row in rows if row.name != EXCLUDED_EMPLOYEE}
		existing = {row.empleado for row in self.empleados}
		for employee_name in selected:
			employee = by_name.get(employee_name)
			if not employee or employee.name in existing:
				continue
			if not employee.designation:
				frappe.throw(_("El empleado {0} no tiene cargo asignado.").format(employee.name))
			self.append(
				"empleados",
				{
					"empleado": employee.name,
					"nombre_empleado": employee.employee_name,
					"cargo": employee.designation,
					"monto_diario": float(money(self.monto_diario)),
					"destino": (self.destino or "").strip(),
					"proyecto": self.proyecto,
					"total_estimado": float(money(self.monto_diario) * len(dates)),
				},
			)
			existing.add(employee.name)
		self._validate_employees(dates)

	@frappe.whitelist()
	def generar_borradores(self):
		self._validate_draft_action(require_saved=True)
		frappe.db.sql("select name from `tabPlanilla Viatico` where name = %s for update", (self.name,))
		if frappe.db.get_value("Planilla Viatico", self.name, "estado") != "Borrador":
			frappe.throw(_("Los borradores de esta planilla ya fueron generados."))
		if frappe.db.exists("Viatico", {"planilla_origen": self.name}):
			frappe.throw(_("La planilla ya tiene viáticos vinculados."))

		dates = _period_dates(self.fecha_desde, self.fecha_hasta)
		self._validate_template()
		self._validate_employees(dates)
		for row in self.empleados:
			viatico = frappe.get_doc(
				{
					"doctype": "Viatico",
					"naming_series": "VIA-.YYYY.-.#####",
					"empleado": row.empleado,
					"tipo_viatico": self.tipo_viatico,
					"fecha_desde": self.fecha_desde,
					"fecha_hasta": self.fecha_hasta,
					"monto_diario": row.monto_diario,
					"moneda": self.moneda,
					"destino_predeterminado": row.destino,
					"proyecto_predeterminado": row.proyecto,
					"planilla_origen": self.name,
				}
			)
			for day in dates:
				viatico.append(
					"dias",
					{
						"fecha": day,
						"monto": row.monto_diario,
						"cargo": row.cargo,
						"destino": row.destino,
						"proyecto": row.proyecto,
					},
				)
			viatico.insert(ignore_permissions=True)
			frappe.db.set_value(
				"Planilla Viatico Empleado",
				row.name,
				{
					"viatico": viatico.name,
					"estado_viatico": viatico.estado,
					"total_estimado": viatico.monto_total,
				},
				update_modified=False,
			)
		self.estado = GENERATED_STATE
		frappe.db.set_value("Planilla Viatico", self.name, "estado", self.estado)
		return {"generados": len(self.empleados)}

	def before_submit(self):
		self._validate_approver("aprobar")
		if self.estado != GENERATED_STATE:
			frappe.throw(_("Genere los borradores individuales antes de aprobar la planilla."))
		self._validate_linked_viatics(required_status=0)

	def on_submit(self):
		for row in self.empleados:
			viatico = frappe.get_doc("Viatico", row.viatico)
			viatico.submit()
			frappe.db.set_value(
				"Planilla Viatico Empleado",
				row.name,
				{"estado_viatico": viatico.estado, "total_estimado": viatico.monto_total},
				update_modified=False,
			)
		self.db_set("estado", "Aprobada", update_modified=False)

	def before_cancel(self):
		self._validate_approver("cancelar")
		self._validate_linked_viatics(required_status=1)
		previous_flag = getattr(frappe.flags, "planilla_viatico_cancel", None)
		frappe.flags.planilla_viatico_cancel = self.name
		try:
			for row in self.empleados:
				viatico = frappe.get_doc("Viatico", row.viatico)
				viatico.cancel()
				frappe.db.set_value(
					"Planilla Viatico Empleado",
					row.name,
					"estado_viatico",
					"Cancelado",
					update_modified=False,
				)
		finally:
			frappe.flags.planilla_viatico_cancel = previous_flag

	def on_cancel(self):
		self.db_set("estado", "Cancelada", update_modified=False)

	def _validate_template(self):
		if not self.plantilla:
			return
		template = frappe.db.get_value(
			"Plantilla Viatico", self.plantilla, ["activa", "empresa"], as_dict=True
		)
		if not template or not template.activa:
			frappe.throw(_("La plantilla seleccionada no existe o está inactiva."))
		if template.empresa != self.empresa:
			frappe.throw(_("La plantilla pertenece a otra empresa."))

	def _validate_employees(self, dates):
		if not self.empleados:
			frappe.throw(_("Seleccione al menos un empleado para la planilla."))
		seen = set()
		total = money(0)
		for row in self.empleados:
			if not row.empleado:
				frappe.throw(
					_("La fila {0} no tiene un empleado seleccionado. Elimínela o complete el empleado.").format(
						row.idx
					)
				)
			if row.empleado == EXCLUDED_EMPLOYEE:
				frappe.throw(_("Augusto no puede incluirse en ninguna planilla."))
			if row.empleado in seen:
				frappe.throw(_("El empleado {0} está repetido.").format(row.empleado))
			seen.add(row.empleado)
			employee = frappe.db.get_value(
				"Employee", row.empleado, ["employee_name", "designation", "company", "status"], as_dict=True
			)
			if not employee or employee.status != "Active" or employee.company != self.empresa:
				frappe.throw(_("El empleado {0} no está activo en la empresa seleccionada.").format(row.empleado))
			if not employee.designation:
				frappe.throw(_("El empleado {0} no tiene cargo asignado.").format(row.empleado))
			if money(row.monto_diario) <= 0 or not (row.destino or "").strip():
				frappe.throw(_("Monto y destino son obligatorios para {0}.").format(row.empleado))
			_validate_project(row.proyecto, self.empresa)
			row.nombre_empleado = employee.employee_name
			row.cargo = employee.designation
			row.destino = row.destino.strip()
			row.total_estimado = float(money(row.monto_diario) * len(dates))
			total += money(row.total_estimado)
		self.cantidad_empleados = len(self.empleados)
		self.total_estimado = float(total)

	def _validate_generated_fields_unchanged(self):
		if self.is_new():
			return
		stored = frappe.db.get_value("Planilla Viatico", self.name, ["estado", *LOCKED_FIELDS], as_dict=True)
		if not stored or stored.estado != GENERATED_STATE:
			return
		for fieldname in LOCKED_FIELDS:
			if str(self.get(fieldname) or "") != str(stored.get(fieldname) or ""):
				frappe.throw(_("No puede modificar {0} después de generar los borradores.").format(fieldname))
		stored_rows = frappe.get_all(
			"Planilla Viatico Empleado",
			filters={"parent": self.name, "parenttype": "Planilla Viatico"},
			fields=["idx", *LOCKED_CHILD_FIELDS],
			order_by="idx asc",
			limit_page_length=0,
		)
		current_rows = [tuple(str(row.get(field) or "") for field in LOCKED_CHILD_FIELDS) for row in self.empleados]
		database_rows = [tuple(str(row.get(field) or "") for field in LOCKED_CHILD_FIELDS) for row in stored_rows]
		if current_rows != database_rows:
			frappe.throw(_("No puede modificar los empleados después de generar los borradores."))

	def _validate_linked_viatics(self, required_status: int):
		for row in self.empleados:
			if not row.viatico:
				frappe.throw(_("Falta el viático del empleado {0}.").format(row.empleado))
			linked = frappe.db.get_value(
				"Viatico", row.viatico, ["planilla_origen", "docstatus"], as_dict=True
			)
			if not linked or linked.planilla_origen != self.name or linked.docstatus != required_status:
				frappe.throw(_("El viático {0} no está en el estado esperado.").format(row.viatico))

	def _validate_draft_action(self, require_saved=False):
		if self.docstatus != 0:
			frappe.throw(_("Esta acción solo está disponible en borrador."))
		if require_saved and self.is_new():
			frappe.throw(_("Guarde la planilla antes de generar viáticos."))
		permission_type = "create" if self.is_new() else "write"
		if not frappe.has_permission("Planilla Viatico", permission_type, doc=self):
			frappe.throw(_("No tiene permiso para modificar esta planilla."), frappe.PermissionError)

	def _validate_approver(self, action):
		if frappe.session.user != APPROVER_USER:
			frappe.throw(
				_("Solo {0} puede {1} una planilla de viáticos.").format(APPROVER_USER, action),
				frappe.PermissionError,
			)


def _period_dates(start_date, end_date):
	if not start_date or not end_date:
		frappe.throw(_("Seleccione la fecha inicial y la fecha final."))
	try:
		return build_inclusive_date_range(getdate(start_date), getdate(end_date))
	except ValueError as error:
		if str(error) == "end_before_start":
			frappe.throw(_("La fecha final no puede ser anterior a la fecha inicial."))
		frappe.throw(_("El período no puede superar {0} días.").format(MAX_VIATIC_PERIOD_DAYS))


def _validate_project(project: str, company: str) -> None:
	if not project or not frappe.db.exists("Project", project):
		frappe.throw(_("Seleccione un proyecto válido."))
	project_company = frappe.db.get_value("Project", project, "company")
	if project_company and project_company != company:
		frappe.throw(_("El proyecto {0} pertenece a otra empresa.").format(project))


def _as_employee_list(value) -> list[str]:
	if isinstance(value, str):
		value = json.loads(value)
	if not isinstance(value, list):
		frappe.throw(_("La selección de empleados no es válida."))
	return list(dict.fromkeys(str(item) for item in value if item))


def _is_blank_employee_row(row) -> bool:
	return not any(_has_row_value(row.get(fieldname)) for fieldname in EMPLOYEE_ROW_FIELDS)


def _has_row_value(value) -> bool:
	if isinstance(value, str):
		return bool(value.strip())
	return bool(value)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def empleados_activos(doctype, txt, searchfield, start, page_len, filters):
	if not (
		frappe.has_permission("Planilla Viatico", "create")
		or frappe.has_permission("Planilla Viatico", "write")
	):
		frappe.throw(_("No tiene permiso para seleccionar empleados."), frappe.PermissionError)
	if isinstance(filters, str):
		filters = json.loads(filters)
	company = (filters or {}).get("company")
	if not company:
		return []
	searchfield = searchfield if searchfield in {"name", "employee_name"} else "name"
	return frappe.db.sql(
		f"""
		select name, employee_name, designation as cargo
		from `tabEmployee`
		where status = 'Active'
		  and company = %(company)s
		  and name != %(excluded)s
		  and ({searchfield} like %(txt)s or employee_name like %(txt)s or designation like %(txt)s)
		order by employee_name, name
		limit %(start)s, %(page_len)s
		""",
		{
			"company": company,
			"excluded": EXCLUDED_EMPLOYEE,
			"txt": f"%{txt}%",
			"start": cint(start),
			"page_len": cint(page_len),
		},
		as_dict=True,
	)
