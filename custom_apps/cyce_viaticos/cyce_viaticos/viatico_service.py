from decimal import Decimal, ROUND_HALF_UP

import frappe
from frappe import _
from frappe.utils import getdate, today

from cyce_viaticos.install import APPROVER_USER
from cyce_viaticos.rules import allocate_adjustments, evaluate_attendance

MONEY_QUANTUM = Decimal("0.01")
OPEN_ADJUSTMENT_STATES = ("Abierto", "Parcialmente aplicado")
PENDING_ATTENDANCE_LABEL = "Pendiente de conciliación"


def money(value) -> Decimal:
	return Decimal(str(value or 0)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def prepare_viatico(doc) -> None:
	employee = frappe.db.get_value(
		"Employee",
		doc.empleado,
		["name", "employee_name", "company", "designation", "status"],
		as_dict=True,
	)
	if not employee or employee.status != "Active":
		frappe.throw(_("El empleado debe existir y estar activo."))

	if not doc.dias:
		frappe.throw(_("Debe registrar al menos un día de viático."))

	doc.nombre_empleado = employee.employee_name
	doc.empresa = employee.company
	doc.cargo = employee.designation
	doc.aprobador = APPROVER_USER
	if doc.docstatus == 0:
		doc.estado = "Borrador"

	_validate_projects(doc)
	dates = _validate_day_rows(doc)
	attendance_by_date = _get_attendance_by_date(doc.empleado, dates)
	today_date = getdate(today())
	requested_total = Decimal(0)
	payable_day_amounts: list[Decimal] = []

	for row in doc.dias:
		amount = money(row.monto)
		requested_total += amount
		attendance = attendance_by_date.get(getdate(row.fecha))
		decision = evaluate_attendance(
			doc.tipo_viatico,
			attendance.status if attendance else None,
			getdate(row.fecha),
			today_date,
		)
		row.asistencia = attendance.name if attendance else None
		row.estado_asistencia = decision.label
		row.elegible = int(decision.eligible)
		row.motivo_no_elegible = decision.reason
		row.ajuste_generado = None
		row.ajuste_anterior_aplicado = 0
		row.monto_neto = float(amount if decision.eligible else Decimal(0))
		payable_day_amounts.append(amount if decision.eligible else Decimal(0))

	adjustments = _get_open_adjustments(doc.empleado)
	allocation = allocate_adjustments(
		payable_day_amounts,
		[money(adjustment.saldo_pendiente) for adjustment in adjustments],
	)

	doc.set("aplicaciones_ajuste", [])
	for adjustment, applied in zip(adjustments, allocation.applications, strict=True):
		if applied <= 0:
			continue
		balance_before = money(adjustment.saldo_pendiente)
		doc.append(
			"aplicaciones_ajuste",
			{
				"ajuste": adjustment.name,
				"viatico_origen": adjustment.viatico_origen,
				"fecha_origen": adjustment.fecha_origen,
				"saldo_antes": float(balance_before),
				"monto_aplicado": float(applied),
				"saldo_despues": float(balance_before - applied),
			},
		)

	for row, deduction, net_amount in zip(
		doc.dias,
		allocation.day_deductions,
		allocation.net_day_amounts,
		strict=True,
	):
		row.ajuste_anterior_aplicado = float(deduction)
		row.monto_neto = float(net_amount)

	doc.fecha_desde = min(dates)
	doc.fecha_hasta = max(dates)
	doc.monto_total = float(requested_total)
	doc.ajuste_anterior_total = float(sum(allocation.applications, start=Decimal(0)))
	doc.monto_neto = float(sum(allocation.net_day_amounts, start=Decimal(0)))


def _validate_day_rows(doc) -> list:
	dates = []
	seen_dates = set()
	for row in doc.dias:
		row_date = getdate(row.fecha)
		if row_date in seen_dates:
			frappe.throw(_("La fecha {0} está repetida en el detalle diario.").format(row_date))
		seen_dates.add(row_date)
		dates.append(row_date)

		if money(row.monto) <= 0:
			frappe.throw(_("El monto del día {0} debe ser mayor que cero.").format(row_date))
		if not row.cargo or not row.destino or not row.proyecto:
			frappe.throw(_("Cargo, destino y proyecto son obligatorios para el día {0}.").format(row_date))

	return dates


def _validate_projects(doc) -> None:
	project_names = sorted({row.proyecto for row in doc.dias if row.proyecto})
	projects = frappe.get_all(
		"Project",
		filters={"name": ["in", project_names]},
		fields=["name", "company"],
		limit_page_length=0,
	)
	project_by_name = {project.name: project for project in projects}

	for project_name in project_names:
		project = project_by_name.get(project_name)
		if not project:
			frappe.throw(_("El proyecto {0} no existe.").format(project_name))
		if project.company and project.company != doc.empresa:
			frappe.throw(_("El proyecto {0} pertenece a otra empresa.").format(project_name))


def _get_attendance_by_date(employee: str, dates: list) -> dict:
	rows = frappe.get_all(
		"Attendance",
		filters={"employee": employee, "attendance_date": ["in", dates], "docstatus": 1},
		fields=["name", "attendance_date", "status"],
		limit_page_length=0,
	)
	return {getdate(row.attendance_date): row for row in rows}


def _get_open_adjustments(employee: str) -> list:
	return frappe.get_all(
		"Viatico Ajuste",
		filters={
			"empleado": employee,
			"docstatus": 1,
			"estado": ["in", OPEN_ADJUSTMENT_STATES],
			"saldo_pendiente": [">", 0],
		},
		fields=["name", "viatico_origen", "fecha_origen", "saldo_pendiente"],
		order_by="fecha_origen asc, creation asc",
		limit_page_length=0,
	)


def apply_adjustments(doc) -> None:
	for application in doc.aplicaciones_ajuste:
		locked = frappe.db.sql(
			"""
			select monto_original, monto_aplicado, saldo_pendiente, estado
			from `tabViatico Ajuste`
			where name = %s
			for update
			""",
			(application.ajuste,),
			as_dict=True,
		)
		if not locked:
			frappe.throw(_("El ajuste {0} ya no existe.").format(application.ajuste))

		adjustment = locked[0]
		balance_before = money(adjustment.saldo_pendiente)
		if adjustment.estado not in OPEN_ADJUSTMENT_STATES or balance_before != money(application.saldo_antes):
			frappe.throw(
				_("El saldo del ajuste {0} cambió. Recargue el viático antes de aprobar.").format(
					application.ajuste
				)
			)

		applied_now = money(application.monto_aplicado)
		if applied_now <= 0 or applied_now > balance_before:
			frappe.throw(_("La aplicación del ajuste {0} no es válida.").format(application.ajuste))

		new_applied = money(adjustment.monto_aplicado) + applied_now
		new_balance = balance_before - applied_now
		new_state = "Aplicado" if new_balance == 0 else "Parcialmente aplicado"
		frappe.db.set_value(
			"Viatico Ajuste",
			application.ajuste,
			{
				"monto_aplicado": float(new_applied),
				"saldo_pendiente": float(new_balance),
				"estado": new_state,
				"viatico_aplicado": doc.name,
			},
		)


def reverse_adjustments(doc) -> None:
	for application in doc.aplicaciones_ajuste:
		locked = frappe.db.sql(
			"""
			select monto_original, monto_aplicado
			from `tabViatico Ajuste`
			where name = %s
			for update
			""",
			(application.ajuste,),
			as_dict=True,
		)
		if not locked:
			frappe.throw(_("No se encontró el ajuste {0} para revertirlo.").format(application.ajuste))

		adjustment = locked[0]
		new_applied = money(adjustment.monto_aplicado) - money(application.monto_aplicado)
		if new_applied < 0:
			frappe.throw(_("El ajuste {0} tiene un saldo aplicado inconsistente.").format(application.ajuste))

		new_balance = money(adjustment.monto_original) - new_applied
		new_state = "Abierto" if new_applied == 0 else "Parcialmente aplicado"
		frappe.db.set_value(
			"Viatico Ajuste",
			application.ajuste,
			{
				"monto_aplicado": float(new_applied),
				"saldo_pendiente": float(new_balance),
				"estado": new_state,
				"viatico_aplicado": _latest_application(application.ajuste, doc.name),
			},
		)


def _latest_application(adjustment: str, excluded_viatic: str) -> str | None:
	rows = frappe.db.sql(
		"""
		select application.parent
		from `tabViatico Aplicacion Ajuste` application
		inner join `tabViatico` viatic on viatic.name = application.parent
		where application.ajuste = %s
		  and application.parent != %s
		  and viatic.docstatus = 1
		order by viatic.creation desc
		limit 1
		""",
		(adjustment, excluded_viatic),
	)
	return rows[0][0] if rows else None


def validate_source_adjustments_before_cancel(doc) -> None:
	adjustments = frappe.get_all(
		"Viatico Ajuste",
		filters={"viatico_origen": doc.name, "estado": ["!=", "Cancelado"]},
		fields=["name", "monto_aplicado"],
		limit_page_length=0,
	)
	for adjustment in adjustments:
		if money(adjustment.monto_aplicado) > 0:
			frappe.throw(
				_("No se puede cancelar porque el ajuste {0} ya fue aplicado.").format(adjustment.name)
			)
		frappe.db.set_value(
			"Viatico Ajuste",
			adjustment.name,
			{"estado": "Cancelado", "saldo_pendiente": 0, "viatico_aplicado": None},
		)


def sync_from_attendance(doc, method=None) -> None:
	reconcile_employee_date(doc.employee, doc.attendance_date)


def reconcile_employee_date(employee: str, attendance_date) -> None:
	row_names = frappe.db.sql(
		"""
		select detail.name
		from `tabViatico Dia` detail
		inner join `tabViatico` viatic on viatic.name = detail.parent
		where detail.fecha = %s
		  and viatic.empleado = %s
		  and viatic.docstatus = 1
		""",
		(getdate(attendance_date), employee),
		pluck=True,
	)
	for row_name in row_names:
		_reconcile_day(row_name)


def _reconcile_day(row_name: str) -> None:
	frappe.db.sql("select name from `tabViatico Dia` where name = %s for update", (row_name,))
	rows = frappe.db.sql(
		"""
		select
			detail.name, detail.parent, detail.fecha, detail.monto_neto,
			viatic.empleado, viatic.empresa, viatic.moneda, viatic.tipo_viatico,
			viatic.docstatus
		from `tabViatico Dia` detail
		inner join `tabViatico` viatic on viatic.name = detail.parent
		where detail.name = %s
		""",
		(row_name,),
		as_dict=True,
	)
	if not rows or rows[0].docstatus != 1:
		return

	row = rows[0]
	attendance = frappe.db.get_value(
		"Attendance",
		{"employee": row.empleado, "attendance_date": row.fecha, "docstatus": 1},
		["name", "status"],
		as_dict=True,
	)
	decision = evaluate_attendance(
		row.tipo_viatico,
		attendance.status if attendance else None,
		getdate(row.fecha),
		getdate(today()),
	)
	existing_adjustment = frappe.db.get_value(
		"Viatico Ajuste",
		{"detalle_origen": row.name},
		["name", "monto_aplicado", "estado"],
		as_dict=True,
	)

	adjustment_name = None
	if decision.eligible:
		if existing_adjustment and existing_adjustment.estado != "Cancelado":
			if money(existing_adjustment.monto_aplicado) > 0:
				frappe.throw(
					_("La asistencia no puede cambiar a elegible porque el ajuste {0} ya fue aplicado.").format(
						existing_adjustment.name
					)
				)
			frappe.db.set_value(
				"Viatico Ajuste",
				existing_adjustment.name,
				{"estado": "Cancelado", "saldo_pendiente": 0, "viatico_aplicado": None},
			)
	else:
		adjustment_name = _upsert_adjustment(row, attendance, decision.reason, existing_adjustment)

	frappe.db.set_value(
		"Viatico Dia",
		row.name,
		{
			"asistencia": attendance.name if attendance else None,
			"estado_asistencia": decision.label,
			"elegible": int(decision.eligible),
			"motivo_no_elegible": decision.reason,
			"ajuste_generado": adjustment_name,
		},
		update_modified=False,
	)
	_refresh_parent_state(row.parent)


def _upsert_adjustment(row, attendance, reason: str, existing_adjustment) -> str | None:
	adjustment_amount = money(row.monto_neto)
	if adjustment_amount <= 0:
		return None

	if existing_adjustment:
		applied = money(existing_adjustment.monto_aplicado)
		if applied > adjustment_amount:
			frappe.throw(_("El ajuste {0} supera el monto entregado del día.").format(existing_adjustment.name))
		balance = adjustment_amount - applied
		state = "Aplicado" if balance == 0 else ("Abierto" if applied == 0 else "Parcialmente aplicado")
		frappe.db.set_value(
			"Viatico Ajuste",
			existing_adjustment.name,
			{
				"asistencia": attendance.name if attendance else None,
				"motivo": reason,
				"monto_original": float(adjustment_amount),
				"saldo_pendiente": float(balance),
				"estado": state,
			},
		)
		return existing_adjustment.name

	adjustment = frappe.get_doc(
		{
			"doctype": "Viatico Ajuste",
			"naming_series": "VIA-AJ-.YYYY.-.#####",
			"empleado": row.empleado,
			"empresa": row.empresa,
			"viatico_origen": row.parent,
			"detalle_origen": row.name,
			"fecha_origen": row.fecha,
			"asistencia": attendance.name if attendance else None,
			"motivo": reason,
			"moneda": row.moneda,
			"monto_original": float(adjustment_amount),
			"monto_aplicado": 0,
			"saldo_pendiente": float(adjustment_amount),
			"estado": "Abierto",
		}
	)
	adjustment.insert(ignore_permissions=True)
	adjustment.flags.ignore_permissions = True
	adjustment.submit()
	return adjustment.name


def _refresh_parent_state(viatic_name: str) -> None:
	statuses = frappe.get_all(
		"Viatico Dia",
		filters={"parent": viatic_name, "parenttype": "Viatico", "parentfield": "dias"},
		pluck="estado_asistencia",
		limit_page_length=0,
	)
	state = "Aprobado" if PENDING_ATTENDANCE_LABEL in statuses else "Conciliado"
	frappe.db.set_value("Viatico", viatic_name, "estado", state, update_modified=False)
	frappe.clear_document_cache("Viatico", viatic_name)


def reconcile_due_viaticos() -> None:
	batch_size = 200
	for _batch in range(50):
		rows = frappe.db.sql(
			"""
			select detail.name
			from `tabViatico Dia` detail
			inner join `tabViatico` viatic on viatic.name = detail.parent
			where viatic.docstatus = 1
			  and detail.fecha < %s
			  and detail.estado_asistencia = %s
			order by detail.fecha, detail.name
			limit %s
			""",
			(getdate(today()), PENDING_ATTENDANCE_LABEL, batch_size),
			pluck=True,
		)
		if not rows:
			break
		for row_name in rows:
			_reconcile_day(row_name)
		if len(rows) < batch_size:
			break
