from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

ADVANCE_TYPE = "Adelantado"
REIMBURSEMENT_TYPE = "Reposición"
ELIGIBLE_ATTENDANCE_STATUS = "Present"


@dataclass(frozen=True)
class AttendanceDecision:
	eligible: bool
	label: str
	reason: str
	provisional: bool = False


@dataclass(frozen=True)
class AdjustmentAllocation:
	applications: tuple[Decimal, ...]
	day_deductions: tuple[Decimal, ...]
	net_day_amounts: tuple[Decimal, ...]


def evaluate_attendance(
	viatic_type: str,
	attendance_status: str | None,
	viatic_date: date,
	today: date,
) -> AttendanceDecision:
	if attendance_status == ELIGIBLE_ATTENDANCE_STATUS:
		return AttendanceDecision(True, "Presente", "")

	if not attendance_status and viatic_type == ADVANCE_TYPE and viatic_date >= today:
		return AttendanceDecision(
			True,
			"Pendiente de conciliación",
			"Adelanto pendiente de validar contra la asistencia del día.",
			provisional=True,
		)

	reasons = {
		"Absent": ("Ausente", "La ausencia no genera viático."),
		"Half Day": ("Medio día", "Medio día no genera viático."),
		"On Leave": ("Permiso", "El permiso no genera viático."),
		"Work From Home": ("Trabajo desde casa", "El trabajo desde casa no genera viático."),
	}
	label, reason = reasons.get(
		attendance_status,
		("Sin asistencia", "No existe una asistencia enviada para el empleado y la fecha."),
	)
	return AttendanceDecision(False, label, reason)


def allocate_adjustments(
	day_amounts: Iterable[Decimal],
	adjustment_balances: Iterable[Decimal],
) -> AdjustmentAllocation:
	net_amounts = [max(Decimal(amount), Decimal(0)) for amount in day_amounts]
	deductions = [Decimal(0) for _ in net_amounts]
	applications: list[Decimal] = []
	day_index = 0

	for balance in adjustment_balances:
		available = sum(net_amounts, start=Decimal(0))
		application = min(max(Decimal(balance), Decimal(0)), available)
		applications.append(application)
		remaining = application

		while remaining > 0 and day_index < len(net_amounts):
			amount = min(net_amounts[day_index], remaining)
			net_amounts[day_index] -= amount
			deductions[day_index] += amount
			remaining -= amount
			if net_amounts[day_index] == 0:
				day_index += 1

	return AdjustmentAllocation(tuple(applications), tuple(deductions), tuple(net_amounts))
