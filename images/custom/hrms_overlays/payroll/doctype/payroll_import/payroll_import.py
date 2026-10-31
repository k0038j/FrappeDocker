# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Auditable payroll import preparation.

The import creates only a draft Payroll Entry. Attendance and optional
Additional Salary preparation are separate, explicitly confirmed operations;
neither creates Salary Slips, accounting entries, or employee master data.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import math
import re
import unicodedata
import zipfile
from xml.etree import ElementTree
from collections.abc import Iterable
from datetime import date
from difflib import get_close_matches

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, date_diff, flt, get_last_day, getdate, nowdate

from hrms.hr.utils import get_holiday_dates_for_employee
from hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
	get_assigned_salary_structure,
)


CANONICAL_FIELDS = (
	"employee_code",
	"employee_name",
	"payroll_category",
	"basic_salary",
	"daily_rate",
	"days_worked",
	"overtime_hours",
	"overtime_rate",
	"other_income",
	"notes",
	"project",
	"cost_center",
)

NUMERIC_FIELDS = {
	"basic_salary",
	"daily_rate",
	"days_worked",
	"overtime_hours",
	"overtime_rate",
	"other_income",
}
PAYROLL_MODE_FREQUENCY = {
	"Fortnightly INSS/IR": "Bimonthly",
}
ATTENDANCE_STATUSES = {"Present", "Absent", "Half Day", "Work From Home"}
MAX_XLSX_BYTES = 10 * 1024 * 1024
MAX_XLSX_SHEETS = 20
MAX_XLSX_ROWS_PER_SHEET = 10_000
MAX_XLSX_COLUMNS_PER_SHEET = 100
MAX_XLSX_DATA_ROWS = 5_000
MAX_XLSX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_PASTED_BYTES = 1 * 1024 * 1024
MAX_PASTED_ROWS = 5_000
MAX_PASTED_COLUMNS = 100
MAX_PASTED_CELL_CHARS = 5_000
XLSX_VISIBLE_HEADERS = {
	"employee_code": "Código de empleado",
	"employee_name": "Nombre de empleado",
	"payroll_category": "Categoría de nómina",
	"basic_salary": "Salario básico",
	"daily_rate": "Tarifa diaria",
	"days_worked": "Días trabajados",
	"overtime_hours": "Horas extra",
	"overtime_rate": "Tarifa por hora extra",
	"other_income": "Otros ingresos",
	"notes": "Notas",
	"project": "Proyecto",
	"cost_center": "Centro de costo",
}

# The values are normalized by ``normalize_text`` before matching.
HEADER_ALIASES = {
	"employee_code": {
		"employee_code",
		"employee code",
		"codigo empleado",
		"codigo de empleado",
		"empleado",
		"employee",
	},
	"employee_name": {
		"employee_name",
		"employee name",
		"nombre empleado",
		"nombre de empleado",
		"nombre y apellido",
		"nombre y apellido(s)",
		"nombre y apellidos",
		"nombre",
	},
	"payroll_category": {"payroll_category", "payroll category", "categoria nomina", "categoria de nomina"},
	"basic_salary": {"basic_salary", "basic salary", "salario basico", "salario base", "salario mensual"},
	"daily_rate": {"daily_rate", "daily rate", "tarifa diaria", "monto diario", "salario por dia"},
	"days_worked": {"days_worked", "days worked", "dias trabajados", "dias trabajados referencia", "dias laborados"},
	"overtime_hours": {"overtime_hours", "overtime hours", "horas extra", "horas extras"},
	"overtime_rate": {
		"overtime_rate",
		"overtime rate",
		"tarifa hora extra",
		"tarifa por hora extra",
		"tarifa horas extras",
		"valor de h/e",
		"valor h/e",
		"valor de horas extras",
		"valor de he",
	},
	"other_income": {"other_income", "other income", "otros ingresos", "otro ingreso"},
	"notes": {"notes", "note", "notas", "nota", "observaciones"},
	"project": {"project", "proyecto"},
	"cost_center": {"cost_center", "cost center", "centro de costo", "centro costo"},
}
VIATICO_HEADERS = {"viatico", "viaticos", "travel allowance", "per diem", "perdiem"}
TOTAL_HEADERS = {"total de h/e", "total h/e", "total horas extras", "total de horas extras", "total he"}


def normalize_text(value: object) -> str:
	"""Return a stable comparison form for pasted headers and employee names."""
	text = unicodedata.normalize("NFKD", str(value or ""))
	text = "".join(char for char in text if not unicodedata.combining(char))
	return re.sub(r"\s+", " ", text.strip().casefold())


def parse_pasted_data(raw_data: str) -> tuple[list[str], list[list[str]]]:
	"""Parse copied CSV/TSV safely; files are intentionally not accepted here."""
	if not raw_data or not raw_data.strip():
		frappe.throw(_("Paste CSV or TSV data before generating the preview."))
	if len(raw_data.encode("utf-8")) > MAX_PASTED_BYTES:
		frappe.throw(_("Los datos pegados superan el límite de {0} MB.").format(MAX_PASTED_BYTES // (1024 * 1024)))

	lines = [line for line in raw_data.replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip()]
	if not lines:
		frappe.throw(_("Paste CSV or TSV data before generating the preview."))

	delimiter = "\t" if lines[0].count("\t") >= lines[0].count(",") else ","
	rows = list(csv.reader(io.StringIO("\n".join(lines)), delimiter=delimiter))
	if not rows or not rows[0]:
		frappe.throw(_("The pasted data does not include a header row."))
	if len(rows) - 1 > MAX_PASTED_ROWS:
		frappe.throw(_("Los datos pegados superan el límite de {0} filas.").format(MAX_PASTED_ROWS))
	if any(len(row) > MAX_PASTED_COLUMNS for row in rows):
		frappe.throw(_("Los datos pegados superan el límite de {0} columnas.").format(MAX_PASTED_COLUMNS))
	if any(len(cell) > MAX_PASTED_CELL_CHARS for row in rows for cell in row):
		frappe.throw(_("Una celda pegada supera el límite de {0} caracteres.").format(MAX_PASTED_CELL_CHARS))

	headers = [header.strip() for header in rows[0]]
	if any(not header for header in headers):
		frappe.throw(_("The header row cannot contain empty columns."))
	return headers, rows[1:]


def parse_number(value: object) -> float:
	"""Strictly parse a plain numeric or currency value; never evaluate formula-like text."""
	if isinstance(value, bool):
		raise ValueError(_("Boolean values are not valid numeric payroll values."))
	if isinstance(value, (int, float)):
		if not math.isfinite(value):
			raise ValueError(_("Numeric payroll values must be finite."))
		return float(value)
	text = str(value or "").strip()
	if not text:
		return 0.0
	if text[0] in "=@+" or (text[0] == "-" and not re.match(r"^-\s*(?:C\$|US\$|NIO|USD|\$|€|£)?\s*\d", text, re.I)):
		raise ValueError(_("Formula-like or invalid numeric text is not allowed."))

	negative = text.startswith("(") and text.endswith(")")
	if negative:
		text = text[1:-1].strip()
	if text.startswith("-"):
		negative = True
		text = text[1:].strip()

	currency_pattern = r"(?:C\$|US\$|NIO|USD|\$|€|£)"
	prefix = re.match(rf"^{currency_pattern}\s*", text, re.I)
	if prefix:
		text = text[prefix.end() :]
	suffix = re.search(rf"\s*{currency_pattern}$", text, re.I)
	if prefix and suffix:
		raise ValueError(_("Numeric payroll values cannot contain more than one currency token."))
	if suffix:
		text = text[: suffix.start()]
	text = text.strip()
	if not re.fullmatch(r"(?:\d{1,3}(?:[.,]\d{3})+|\d+)(?:[.,]\d+)?", text):
		raise ValueError(_("Numeric payroll values may only contain digits, valid separators, and an optional currency."))

	if "," in text and "." in text:
		if text.rfind(",") > text.rfind("."):
			text = text.replace(".", "").replace(",", ".")
		else:
			text = text.replace(",", "")
	elif "," in text:
		parts = text.split(",")
		text = "".join(parts) if len(parts) == 2 and len(parts[1]) == 3 else "".join(parts[:-1]) + "." + parts[-1]
	elif "." in text:
		parts = text.split(".")
		if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3):
			text = "".join(parts)
	result = float(text)
	return -abs(result) if negative else result


class PayrollImport(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		column_mappings: DF.Table
		basic_salary_component: DF.Link | None
		company: DF.Link
		cost_center: DF.Link | None
		default_salary_structure: DF.Link | None
		additional_salary_documents: DF.SmallText | None
		workbook_file: DF.Attach | None
		workbook_hash: DF.Data | None
		workbook_filename: DF.Data | None
		workbook_sheet: DF.Data | None
		workbook_header_row: DF.Int | None
		workbook_data_start_row: DF.Int | None
		workbook_data_end_row: DF.Int | None
		workbook_candidates: DF.SmallText | None
		overtime_salary_component: DF.Link | None
		other_income_salary_component: DF.Link | None
		payroll_entry: DF.Link | None
		payroll_mode: DF.Literal["Project", "Fortnightly INSS/IR", "Professional Services"]
		period_end: DF.Date
		period_start: DF.Date
		preview_rows: DF.Table
		project: DF.Link | None
		raw_data: DF.LongText | None
		status: DF.Literal["Draft", "Validated", "Applied", "Error"]
		validation_messages: DF.SmallText | None
	# end: auto-generated types

	def validate(self) -> None:
		self._validate_period()
		self._validate_parse_error_immutability()
		self._validate_immutable_applied_fields()
		self._ensure_default_column_mappings()

	def _validate_parse_error_immutability(self) -> None:
		"""Do not let a client clear persisted parser blocks through a document save."""
		if getattr(self.flags, "in_payroll_import_preview_regeneration", False):
			return
		before = self.get_doc_before_save()
		if not before:
			return
		current_rows = {row.name: row for row in self.preview_rows if row.name}
		for previous_row in before.preview_rows:
			if not previous_row.parse_error:
				continue
			current_row = current_rows.get(previous_row.name)
			if not current_row or not current_row.parse_error:
				frappe.throw(_("Rows blocked by parser errors cannot be changed or removed; regenerate the preview instead."))

	def _validate_immutable_applied_fields(self) -> None:
		before = self.get_doc_before_save()
		if not before or not (
			before.status == "Applied" or before.payroll_entry or before.additional_salary_documents
		):
			return
		protected_fields = (
			"company",
			"project",
			"cost_center",
			"payroll_mode",
			"default_salary_structure",
			"basic_salary_component",
			"overtime_salary_component",
			"other_income_salary_component",
			"period_start",
			"period_end",
			"raw_data",
			"workbook_file",
			"workbook_hash",
			"workbook_filename",
			"workbook_sheet",
			"workbook_header_row",
			"workbook_data_start_row",
			"workbook_data_end_row",
		)
		if any(self.has_value_changed(fieldname) for fieldname in protected_fields):
			frappe.throw(_("Applied payroll import source fields cannot be changed."))
		before_mappings = [
			(mapping.source_column, mapping.canonical_field, mapping.position, mapping.ignore)
			for mapping in before.column_mappings
		]
		current_mappings = [
			(mapping.source_column, mapping.canonical_field, mapping.position, mapping.ignore)
			for mapping in self.column_mappings
		]
		if before_mappings != current_mappings:
			frappe.throw(_("Applied payroll import column mappings cannot be changed."))
		preview_fields = (
			"source_row",
			"employee_code",
			"employee_name",
			"matched_employee",
			"match_status",
			"payroll_category",
			"basic_salary",
			"daily_rate",
			"days_worked",
			"overtime_hours",
			"overtime_rate",
			"other_income",
			"notes",
			"project",
			"cost_center",
			"source_data",
			"parse_error",
		)
		if getattr(self.flags, "in_payroll_import_attendance_sync", False):
			preview_fields = tuple(fieldname for fieldname in preview_fields if fieldname != "days_worked")
		before_preview = [tuple(row.get(fieldname) for fieldname in preview_fields) for row in before.preview_rows]
		current_preview = [tuple(row.get(fieldname) for fieldname in preview_fields) for row in self.preview_rows]
		if before_preview != current_preview:
			frappe.throw(_("Applied payroll import preview rows cannot be changed."))

	def _validate_period(self) -> None:
		if self.period_start and self.period_end and getdate(self.period_start) > getdate(self.period_end):
			frappe.throw(_("Period start cannot be after period end."))
		if self.payroll_mode == "Fortnightly INSS/IR" and self.period_start and self.period_end:
			start = getdate(self.period_start)
			end = getdate(self.period_end)
			valid_first_half = start.day == 1 and end.day == 15 and start.month == end.month and start.year == end.year
			month_end = getdate(get_last_day(start))
			valid_second_half = start.day == 16 and end == month_end
			if not (valid_first_half or valid_second_half):
				frappe.throw(
					_("Fortnightly INSS/IR must cover exactly day 1-15 or day 16 through month end.")
				)

	def _ensure_default_column_mappings(self) -> None:
		if self.column_mappings:
			return
		for position, fieldname in enumerate(CANONICAL_FIELDS, start=1):
			self.append(
				"column_mappings",
				{"source_column": fieldname, "canonical_field": fieldname, "position": position},
			)

	def _assert_draft(self) -> None:
		if self.status == "Applied" or self.payroll_entry or self.additional_salary_documents:
			frappe.throw(_("Applied payroll imports cannot be changed."))

	def _mapped_headers(self, headers: Iterable[str]) -> tuple[dict[int, str], list[str]]:
		configured = {
			normalize_text(mapping.source_column): mapping.canonical_field
			for mapping in self.column_mappings
			if mapping.source_column and mapping.canonical_field and not mapping.ignore
		}
		aliases = {
			normalize_text(alias): canonical
			for canonical, values in HEADER_ALIASES.items()
			for alias in values
		}
		mapping: dict[int, str] = {}
		ignored_viaticos: list[str] = []
		seen_fields: set[str] = set()
		for index, header in enumerate(headers):
			normalized = normalize_text(header)
			if normalized in VIATICO_HEADERS:
				ignored_viaticos.append(header)
				continue
			# Aggregates are not a per-employee value. In particular, never treat
			# TOTAL H/E as either worked hours or the hourly rate.
			if normalized in TOTAL_HEADERS:
				continue
			canonical = configured.get(normalized) or aliases.get(normalized)
			if not canonical:
				continue
			if canonical in seen_fields:
				frappe.throw(_("More than one pasted column maps to {0}.").format(canonical))
			seen_fields.add(canonical)
			mapping[index] = canonical

		if "employee_code" not in mapping.values() and "employee_name" not in mapping.values():
			frappe.throw(_("Map either employee_code or employee_name before generating the preview."))
		return mapping, ignored_viaticos

	def _resolve_employee(self, employee_code: str, employee_name: str) -> tuple[str | None, str, str]:
		"""Resolve only unambiguous employees within the selected company."""
		filters = {"company": self.company, "status": "Active"}
		if employee_code:
			matches = frappe.get_all(
				"Employee",
				fields=["name", "employee_name"],
				filters=filters,
				or_filters=[["name", "=", employee_code], ["employee", "=", employee_code]],
				limit_page_length=3,
			)
			if len(matches) == 1:
				if employee_name and normalize_text(matches[0].employee_name) != normalize_text(employee_name):
					return None, "Blocked", _("Employee code and employee name refer to different employees.")
				return matches[0].name, "Matched", ""
			if len(matches) > 1:
				return None, "Ambiguous", _("More than one active employee matches the employee code.")

		if not employee_name:
			return None, "Not Found", _("Employee code or employee name is required.")

		candidates = frappe.get_all(
			"Employee",
			fields=["name", "employee_name"],
			filters=filters,
			limit_page_length=0,
		)
		normalized_name = normalize_text(employee_name)
		exact = [
			candidate for candidate in candidates if normalize_text(candidate.employee_name) == normalized_name
		]
		if len(exact) == 1:
			return exact[0].name, "Matched", ""
		if len(exact) > 1:
			return None, "Ambiguous", _("More than one active employee has that normalized name.")

		excel_tokens = set(normalized_name.split())
		contained = []
		for candidate in candidates:
			candidate_tokens = set(normalize_text(candidate.employee_name).split())
			if len(candidate_tokens) >= 2 and candidate_tokens.issubset(excel_tokens):
				contained.append(candidate)
		if len(contained) == 1:
			return contained[0].name, "Matched", ""
		if len(contained) > 1:
			return None, "Ambiguous", _("More than one active employee is contained in the imported full name.")

		suggestions = get_close_matches(
			normalized_name,
			[normalize_text(d.employee_name) for d in candidates],
			n=3,
			cutoff=0.75,
		)
		if suggestions:
			suggested_names = [d.employee_name for d in candidates if normalize_text(d.employee_name) in suggestions]
			return None, "Not Found", _("Employee not found. Suggestions: {0}").format(", ".join(suggested_names))
		return None, "Not Found", _("No active employee matches this row in the selected company.")

	def _has_salary_slip_conflict(self, employee: str) -> str | None:
		return frappe.db.exists(
			"Salary Slip",
			{
				"employee": employee,
				"docstatus": ("!=", 2),
				"start_date": ("<=", self.period_end),
				"end_date": (">=", self.period_start),
			},
		)

	def _row_identity(self, values: dict[str, object]) -> str:
		return normalize_text(values.get("employee_code") or values.get("employee_name"))

	def _row_signature(self, values: dict[str, object]) -> str:
		return json.dumps(values, ensure_ascii=False, sort_keys=True, default=str)

	@staticmethod
	def _classify_duplicate(
		seen: dict[str, tuple[str, int]], identity: str, signature: str, row_index: int
	) -> tuple[str | None, str]:
		"""Return a non-empty status only when a repeated imported identity is unsafe."""
		if not identity:
			return None, ""
		if identity not in seen:
			seen[identity] = (signature, row_index)
			return None, ""
		previous_signature, previous_row = seen[identity]
		if previous_signature == signature:
			return "Ignored", _("Identical duplicate of row {0}; ignored.").format(previous_row)
		return "Blocked", _("Conflicting duplicate of row {0}; resolve it before applying.").format(previous_row)

	@frappe.whitelist()
	def parse_preview(self) -> dict[str, object]:
		"""Persist a reviewable preview only; this never creates payroll or attendance data."""
		self.check_permission("write")
		self._assert_draft()
		headers, pasted_rows = parse_pasted_data(self.raw_data or "")
		return self._parse_preview_rows(headers, pasted_rows, source="paste", source_row_start=2)

	def _parse_preview_rows(
		self, headers: list[str], pasted_rows: list[list[object]], *, source: str, source_row_start: int
	) -> dict[str, object]:
		"""Build a preview from inert cell values, without writing payroll or attendance."""
		header_mapping, ignored_viaticos = self._mapped_headers(headers)
		self.set("preview_rows", [])
		messages: list[str] = []
		if ignored_viaticos:
			messages.append(
				_("Viático columns were ignored and will never be applied: {0}").format(
					", ".join(ignored_viaticos)
				)
			)

		seen: dict[str, tuple[str, int]] = {}
		for row_index, pasted_row in enumerate(pasted_rows, start=source_row_start):
			values: dict[str, object] = {field: "" for field in CANONICAL_FIELDS}
			values["notes"] = ""
			numeric_errors: list[str] = []
			for column_index, canonical in header_mapping.items():
				value = pasted_row[column_index] if column_index < len(pasted_row) else ""
				values[canonical] = str(value).strip() if value is not None else ""
			for field in NUMERIC_FIELDS:
				try:
					values[field] = parse_number(values[field])
				except (TypeError, ValueError):
					values[field] = 0.0
					numeric_errors.append(field)
					messages.append(_("Row {0}: {1} is not a valid number.").format(row_index, field))

			match_employee, match_status, message = self._resolve_employee(
				str(values["employee_code"]), str(values["employee_name"])
			)
			identity = normalize_text(match_employee) if match_employee else self._row_identity(values)
			row_status = match_status
			if numeric_errors:
				row_status = "Blocked"
				message = _("Invalid numeric value(s): {0}.").format(", ".join(numeric_errors))
			signature = self._row_signature(values)
			duplicate_status, duplicate_message = self._classify_duplicate(seen, identity, signature, row_index)
			if duplicate_status and not numeric_errors:
				row_status = duplicate_status
				message = duplicate_message

			self.append(
				"preview_rows",
				{
					"source_row": row_index,
					"employee_code": values["employee_code"],
					"employee_name": values["employee_name"],
					"matched_employee": match_employee,
					"match_status": row_status,
					"payroll_category": values["payroll_category"],
					"basic_salary": values["basic_salary"],
					"daily_rate": values["daily_rate"],
					"days_worked": values["days_worked"],
					"estimated_basic_amount": flt(values["daily_rate"]) * flt(values["days_worked"]),
					"overtime_hours": values["overtime_hours"],
					"overtime_rate": values["overtime_rate"],
					"other_income": values["other_income"],
					"notes": values["notes"],
					"project": values["project"],
					"cost_center": values["cost_center"],
					"viatico_data_ignored": 1 if ignored_viaticos else 0,
					"validation_message": message,
					"parse_error": 1 if numeric_errors else 0,
					"source_data": json.dumps(values, ensure_ascii=False),
				},
			)

		self.status = "Draft"
		self.validation_messages = "\n".join(messages)
		self.flags.in_payroll_import_preview_regeneration = True
		try:
			self.save()
		finally:
			self.flags.in_payroll_import_preview_regeneration = False
		return {
			"rows": len(self.preview_rows),
			"ignored_viatico_columns": ignored_viaticos,
			"messages": messages,
			"source": source,
		}

	def _get_workbook_content(self) -> tuple[bytes, str]:
		if not self.workbook_file:
			frappe.throw(_("Adjunte un archivo XLSX antes de inspeccionarlo o importarlo."))
		file_doc = frappe.get_doc("File", {"file_url": self.workbook_file})
		file_doc.check_permission("read")
		filename = file_doc.file_name or self.workbook_file.rsplit("/", 1)[-1]
		if not filename.lower().endswith(".xlsx"):
			frappe.throw(_("El archivo adjunto debe ser un libro XLSX."))
		content = file_doc.get_content()
		if len(content) > MAX_XLSX_BYTES:
			frappe.throw(_("El archivo XLSX supera el límite de {0} MB.").format(MAX_XLSX_BYTES // (1024 * 1024)))
		return content, filename

	@staticmethod
	def _load_workbook(content: bytes, *, data_only: bool):
		try:
			from openpyxl import load_workbook
		except ImportError:
			frappe.throw(_("La biblioteca XLSX requerida no está disponible en este entorno."))
		try:
			with zipfile.ZipFile(io.BytesIO(content)) as archive:
				if sum(member.file_size for member in archive.infolist()) > MAX_XLSX_UNCOMPRESSED_BYTES:
					frappe.throw(_("El contenido descomprimido del XLSX supera el límite permitido."))
			return load_workbook(io.BytesIO(content), read_only=True, data_only=data_only, keep_links=False)
		except frappe.ValidationError:
			raise
		except zipfile.BadZipFile:
			frappe.throw(_("El archivo adjunto no es un libro XLSX válido."))
		except Exception as error:
			frappe.throw(_("No se pudo leer el libro XLSX: {0}").format(str(error)))

	@staticmethod
	def _nonempty_values(row: Iterable[object]) -> list[str]:
		return [str(value).strip() for value in row if value is not None and str(value).strip()]

	@staticmethod
	def _header_match_count(row: Iterable[object]) -> int:
		aliases = {normalize_text(alias) for values in HEADER_ALIASES.values() for alias in values}
		return sum(normalize_text(value) in aliases for value in PayrollImport._nonempty_values(row))

	@staticmethod
	def _is_header_row(row: Iterable[object]) -> bool:
		values = PayrollImport._nonempty_values(row)
		return PayrollImport._header_match_count(values) >= 2 or (
			PayrollImport._header_match_count(values) >= 1
			and any(normalize_text(value) in {"employee_code", "employee", "empleado"} for value in values)
		)

	@staticmethod
	def _is_total_row(row: Iterable[object]) -> bool:
		values = [normalize_text(value) for value in PayrollImport._nonempty_values(row)]
		for value in values:
			# These are legitimate per-column headings, not an aggregate data row.
			if value in TOTAL_HEADERS:
				continue
			if re.match(r"^totales?(?:\s|$)", value):
				return True
		return False

	def _suggest_data_end_row(self, worksheet, header_row: int) -> int:
		"""Stop a payroll section before totals, another table, or a long blank gap."""
		last_data_row = header_row
		blank_rows = 0
		for row_number, row in enumerate(
			worksheet.iter_rows(min_row=header_row + 1, values_only=True), start=header_row + 1
		):
			if row_number - header_row > MAX_XLSX_DATA_ROWS:
				frappe.throw(_("La sección XLSX supera el límite de {0} filas de datos.").format(MAX_XLSX_DATA_ROWS))
			values = self._nonempty_values(row)
			if not values:
				blank_rows += 1
				if last_data_row > header_row and blank_rows >= 2:
					break
				continue
			blank_rows = 0
			if self._is_total_row(values) or (last_data_row > header_row and self._is_header_row(values)):
				break
			last_data_row = row_number
		return last_data_row

	@staticmethod
	def _worksheet_content_bounds(workbook, worksheet) -> tuple[int, int]:
		"""Return the last row/column with a value or formula, ignoring formatted blanks."""
		archive = getattr(workbook, "_archive", None)
		worksheet_path = getattr(worksheet, "_worksheet_path", None)
		if archive and worksheet_path:
			from openpyxl.utils.cell import coordinate_to_tuple

			max_row = max_column = 0
			with archive.open(worksheet_path) as source:
				for _event, element in ElementTree.iterparse(source, events=("end",)):
					if not element.tag.endswith("}c"):
						continue
					if any(child.tag.endswith(("}v", "}f", "}is")) for child in element):
						row, column = coordinate_to_tuple(element.attrib["r"])
						max_row = max(max_row, row)
						max_column = max(max_column, column)
					element.clear()
			return max_row, max_column

		max_row = max_column = 0
		for row in worksheet.iter_rows():
			for cell in row:
				if cell.value is not None and str(cell.value).strip():
					max_row = max(max_row, cell.row)
					max_column = max(max_column, cell.column)
		return max_row, max_column

	@classmethod
	def _validate_workbook_limits(cls, workbook) -> None:
		if len(workbook.sheetnames) > MAX_XLSX_SHEETS:
			frappe.throw(_("El XLSX supera el límite de {0} hojas.").format(MAX_XLSX_SHEETS))
		for worksheet in workbook.worksheets:
			content_rows, content_columns = cls._worksheet_content_bounds(workbook, worksheet)
			if content_rows > MAX_XLSX_ROWS_PER_SHEET or content_columns > MAX_XLSX_COLUMNS_PER_SHEET:
				frappe.throw(
					_("La hoja {0} supera el límite de {1} filas o {2} columnas.").format(
						worksheet.title, MAX_XLSX_ROWS_PER_SHEET, MAX_XLSX_COLUMNS_PER_SHEET
					)
				)

	def _workbook_header_candidates(self, workbook) -> list[dict[str, object]]:
		candidates: list[dict[str, object]] = []
		for worksheet in workbook.worksheets:
			for row_number, row in enumerate(worksheet.iter_rows(values_only=True), start=1):
				if row_number > 100:
					break
				values = self._nonempty_values(row)
				matches = self._header_match_count(values)
				if self._is_header_row(values):
					candidates.append(
						{
							"sheet": worksheet.title,
							"header_row": row_number,
							"data_start_row": row_number + 1,
							"data_end_row": self._suggest_data_end_row(worksheet, row_number),
							"matches": matches,
							"headers": values,
						}
					)
		return candidates

	@frappe.whitelist()
	def inspect_workbook(self) -> dict[str, object]:
		"""Inspect workbook structure only; this operation never imports or evaluates formulas."""
		self.check_permission("write")
		self._assert_draft()
		content, filename = self._get_workbook_content()
		workbook = self._load_workbook(content, data_only=True)
		self._validate_workbook_limits(workbook)
		candidates = self._workbook_header_candidates(workbook)
		file_hash = hashlib.sha256(content).hexdigest()
		is_new_file = self.workbook_hash != file_hash
		self.workbook_hash = file_hash
		self.workbook_filename = filename
		self.workbook_candidates = json.dumps(candidates, ensure_ascii=False)
		if candidates and is_new_file:
			self.workbook_sheet = candidates[0]["sheet"]
			self.workbook_header_row = candidates[0]["header_row"]
			self.workbook_data_start_row = candidates[0]["data_start_row"]
			self.workbook_data_end_row = candidates[0]["data_end_row"]
		elif not self.workbook_sheet and workbook.sheetnames:
			self.workbook_sheet = candidates[0]["sheet"] if candidates else workbook.sheetnames[0]
		if not self.workbook_header_row and candidates:
			self.workbook_header_row = candidates[0]["header_row"]
		if not self.workbook_data_start_row and self.workbook_header_row:
			self.workbook_data_start_row = self.workbook_header_row + 1
		self.save()
		return {"filename": filename, "hash": file_hash, "sheets": workbook.sheetnames, "candidates": candidates}

	def _workbook_rows(self, content: bytes) -> tuple[list[str], list[list[object]]]:
		if not self.workbook_sheet or not self.workbook_header_row:
			frappe.throw(_("Seleccione una hoja y la fila de encabezados del libro XLSX."))
		formula_book = self._load_workbook(content, data_only=False)
		value_book = self._load_workbook(content, data_only=True)
		self._validate_workbook_limits(formula_book)
		if self.workbook_sheet not in formula_book.sheetnames:
			frappe.throw(_("La hoja XLSX seleccionada no existe."))
		formula_sheet = formula_book[self.workbook_sheet]
		value_sheet = value_book[self.workbook_sheet]
		from openpyxl.utils import get_column_letter

		header_row = int(self.workbook_header_row)
		start_row = int(self.workbook_data_start_row or header_row + 1)
		suggested_end_row = self._suggest_data_end_row(value_sheet, header_row)
		end_row = int(self.workbook_data_end_row or suggested_end_row)
		if header_row < 1 or start_row <= header_row or end_row < start_row:
			frappe.throw(_("El rango de encabezado y datos XLSX no es válido."))
		if end_row > suggested_end_row:
			frappe.throw(
				_("La fila final seleccionada alcanza un total o una nueva sección XLSX; seleccione el límite sugerido.")
			)
		if end_row - start_row + 1 > MAX_XLSX_DATA_ROWS:
			frappe.throw(_("La sección XLSX supera el límite de {0} filas de datos.").format(MAX_XLSX_DATA_ROWS))
		self.workbook_data_start_row = start_row
		self.workbook_data_end_row = end_row
		headers = [
			str(value or "").strip()
			for value in next(value_sheet.iter_rows(min_row=header_row, max_row=header_row, values_only=True))
		]
		if not any(headers):
			frappe.throw(_("La fila de encabezados XLSX está vacía."))
		rows: list[list[object]] = []
		for row_number, (formula_row, value_row) in enumerate(zip(
			formula_sheet.iter_rows(min_row=start_row, max_row=end_row, values_only=True),
			value_sheet.iter_rows(min_row=start_row, max_row=end_row, values_only=True),
		), start=start_row):
			if not any(value is not None and str(value).strip() for value in value_row) and not any(
				value is not None and str(value).strip() for value in formula_row
			):
				continue
			for column, (formula_value, cached_value) in enumerate(zip(formula_row, value_row), start=1):
				if isinstance(formula_value, str) and formula_value.startswith("=") and cached_value is None:
					frappe.throw(
						_("La fórmula sin resultado almacenado en {0}!{1}{2} debe recalcularse y guardarse antes de importar.").format(
							self.workbook_sheet, get_column_letter(column), row_number
						)
					)
			rows.append(list(value_row))
		return headers, rows

	def _lock_and_assert_workbook_section_available(self, file_hash: str) -> None:
		"""Serialize XLSX section claims and reject any overlapping persisted section.

		The shared DocType row is locked first, so simultaneous imports cannot both
		observe an empty hash/sheet range before either preview is saved. The
		transaction remains open through ``self.save`` in the request handler.
		"""
		frappe.db.sql("SELECT name FROM `tabDocType` WHERE name = %s FOR UPDATE", ("Payroll Import",))
		overlaps = frappe.db.sql(
			"""
			SELECT name
			FROM `tabPayroll Import`
			WHERE name != %s
				AND workbook_hash = %s
				AND workbook_sheet = %s
				AND COALESCE(workbook_data_start_row, 0) <= %s
				AND COALESCE(workbook_data_end_row, 2147483647) >= %s
			FOR UPDATE
			""",
			(
				self.name or "",
				file_hash,
				self.workbook_sheet,
				self.workbook_data_end_row,
				self.workbook_data_start_row,
			),
			as_dict=True,
		)
		if overlaps:
			frappe.throw(
				_("Este archivo, hoja y sección se solapa con la importación existente: {0}.").format(
					", ".join(row.name for row in overlaps)
				)
			)

	@frappe.whitelist()
	def parse_workbook_preview(self) -> dict[str, object]:
		"""Parse only cached XLSX values; formulas are never executed as import logic."""
		self.check_permission("write")
		self._assert_draft()
		content, filename = self._get_workbook_content()
		file_hash = hashlib.sha256(content).hexdigest()
		if self.workbook_hash and self.workbook_hash != file_hash:
			frappe.throw(_("El archivo XLSX cambió. Inspecciónelo de nuevo antes de importar."))
		headers, rows = self._workbook_rows(content)
		self.workbook_hash = file_hash
		self.workbook_filename = filename
		self._lock_and_assert_workbook_section_available(file_hash)
		return self._parse_preview_rows(
			headers,
			rows,
			source="xlsx",
			source_row_start=int(self.workbook_data_start_row or int(self.workbook_header_row) + 1),
		)

	def _validate_default_salary_structure(self) -> list[str]:
		errors: list[str] = []
		if not self.default_salary_structure:
			return [_('A default Salary Structure is required before applying the import.')]

		company_currency = frappe.db.get_value("Company", self.company, "default_currency")
		structure = frappe.db.get_value(
			"Salary Structure",
			self.default_salary_structure,
			["company", "currency", "docstatus", "is_active", "payroll_frequency"],
			as_dict=True,
		)
		if not structure or structure.docstatus != 1 or structure.is_active != "Yes":
			errors.append(_("The selected Salary Structure must be submitted and active."))
			return errors
		if structure.company != self.company or structure.currency != company_currency:
			errors.append(_("The selected Salary Structure does not match the company currency and company."))
		required_frequency = PAYROLL_MODE_FREQUENCY.get(self.payroll_mode)
		if required_frequency and structure.payroll_frequency != required_frequency:
			errors.append(
				_("Fortnightly INSS/IR requires a Bimonthly Salary Structure (1-15 and 16-end of month).")
			)
		return errors

	def _selected_payroll_frequency(self) -> str:
		frequency = frappe.db.get_value("Salary Structure", self.default_salary_structure, "payroll_frequency")
		if not frequency:
			frappe.throw(_("The selected Salary Structure does not define a payroll frequency."))
		return frequency

	def _structure_earning_component_names(self) -> set[str]:
		structure = frappe.get_cached_doc("Salary Structure", self.default_salary_structure)
		return {normalize_text(row.salary_component) for row in structure.earnings}

	def _structure_has_statutory_deductions(self) -> bool:
		structure = frappe.get_cached_doc("Salary Structure", self.default_salary_structure)
		deductions = {normalize_text(row.salary_component) for row in structure.deductions}
		has_inss = any("inss" in component for component in deductions)
		has_ir = any(
			component == "ir" or "ir laboral" in component or "income tax" in component
			for component in deductions
		)
		return has_inss and has_ir

	def _professional_services_has_withholding(self) -> bool:
		structure = frappe.get_cached_doc("Salary Structure", self.default_salary_structure)
		for deduction in structure.deductions:
			component = normalize_text(deduction.salary_component)
			formula = normalize_text(deduction.formula)
			if "retencion" in component and re.search(
				r"(?<!\d)(?:0[.,]1|10\s*%|10\s*[\)\]]?\s*/\s*100)(?!\d)", formula
			):
				return True
		return False

	def _validate_matched_employee(self, row) -> str | None:
		"""Validate a parsed or manually selected employee against the import company."""
		if row.parse_error:
			return _("Row {0} is blocked by a parser error; regenerate the preview after correcting the source data.").format(
				row.source_row
			)
		if row.match_status == "Blocked":
			return row.validation_message or _("Row {0} is blocked by invalid imported data.").format(row.source_row)
		if not row.matched_employee:
			return _("Row {0} is not matched to exactly one active employee.").format(row.source_row)
		employee = frappe.db.get_value(
			"Employee", row.matched_employee, ["company", "status"], as_dict=True
		)
		if not employee:
			return _("Row {0}: the selected employee no longer exists.").format(row.source_row)
		if employee.status != "Active" or employee.company != self.company:
			return _("Row {0}: the selected employee must be active and belong to this company.").format(
				row.source_row
			)
		row.match_status = "Matched"
		row.validation_message = ""
		return None

	def _validate_preview_rows(self) -> list[str]:
		errors: list[str] = []
		if not self.cost_center:
			errors.append(_("A Cost Center is required to create a draft Payroll Entry."))
		if self.payroll_mode == "Project" and not self.project:
			errors.append(_("Project payroll requires a Project."))
		component_names = self._structure_earning_component_names() if self.default_salary_structure else set()
		for row in self.preview_rows:
			match_error = self._validate_matched_employee(row)
			if match_error:
				errors.append(match_error)
				continue
			if self._has_salary_slip_conflict(row.matched_employee):
				errors.append(
					_("Row {0}: a non-cancelled Salary Slip overlaps the selected period.").format(
						row.source_row
					)
				)
			if get_assigned_salary_structure(row.matched_employee, self.period_start) != self.default_salary_structure:
				errors.append(
					_("Row {0}: the employee lacks the selected active Salary Structure Assignment.").format(
						row.source_row
					)
				)
			if row.project and row.project != self.project:
				errors.append(_("Row {0}: row project differs from the import project.").format(row.source_row))
			if row.cost_center and row.cost_center != self.cost_center:
				errors.append(_("Row {0}: row cost center differs from the import cost center.").format(row.source_row))
			if flt(row.overtime_hours) and not self.overtime_salary_component:
				errors.append(_("Row {0}: select an overtime Salary Component.").format(row.source_row))
			if flt(row.other_income) and not self.other_income_salary_component:
				errors.append(_("Row {0}: select an other-income Salary Component.").format(row.source_row))
			if (
				self.payroll_mode in ("Project", "Professional Services")
				and flt(row.daily_rate)
				and not self.basic_salary_component
			):
				errors.append(
					_("Row {0}: select a basic Salary Component for the attendance-based amount.").format(
						row.source_row
					)
				)
		if self.basic_salary_component and normalize_text(self.basic_salary_component) not in component_names:
			errors.append(_("The selected basic salary component is not an earning in the Salary Structure."))
		variable_components = {
			_("overtime"): self.overtime_salary_component,
			_("other income"): self.other_income_salary_component,
		}
		for label, component in variable_components.items():
			if component and frappe.db.get_value("Salary Component", component, "type") != "Earning":
				errors.append(_("The selected {0} Salary Component must be an Earning.").format(label))
		selected_components = [
			component
			for component in (
				self.basic_salary_component,
				self.overtime_salary_component,
				self.other_income_salary_component,
			)
			if component
		]
		if len(selected_components) != len(set(selected_components)):
			errors.append(_("Basic salary, overtime and other income must use different Salary Components."))
		if self.payroll_mode == "Professional Services" and not self._professional_services_has_withholding():
			errors.append(
				_(
					"Professional Services requires an existing 10% withholding deduction "
					"in the selected Salary Structure."
				)
			)
		if self.payroll_mode == "Fortnightly INSS/IR" and not self._structure_has_statutory_deductions():
			errors.append(_("Fortnightly INSS/IR requires existing INSS and IR deductions in the Salary Structure."))
		return errors

	@frappe.whitelist()
	def validate_import(self) -> dict[str, object]:
		"""Validate immutable master-data prerequisites without applying payroll data."""
		self.check_permission("write")
		self._assert_draft()
		if not self.preview_rows:
			frappe.throw(_("Generate a preview before validating the import."))
		errors = self._validate_default_salary_structure()
		if not errors:
			errors.extend(self._validate_preview_rows())
		self.status = "Error" if errors else "Validated"
		self.validation_messages = "\n".join(errors)
		self.save()
		return {"valid": not errors, "errors": errors}

	def _import_employee_names(self) -> set[str]:
		return {
			row.matched_employee
			for row in self.preview_rows
			if row.match_status == "Matched" and row.matched_employee
		}

	def _attendance_paid_days(self) -> dict[str, float]:
		employees = self._import_employee_names()
		paid_days = {employee: 0.0 for employee in employees}
		if not employees:
			return paid_days
		records = frappe.get_all(
			"Attendance",
			fields=["employee", "attendance_date", "status", "leave_type"],
			filters={
				"employee": ("in", list(employees)),
				"attendance_date": ("between", [self.period_start, self.period_end]),
				"docstatus": 1,
			},
			limit_page_length=0,
		)
		allowed_dates = {employee: self._allowed_attendance_dates(employee) for employee in employees}
		for record in records:
			if getdate(record.attendance_date) not in allowed_dates[record.employee]:
				continue
			if record.status in ("Present", "Work From Home"):
				paid_days[record.employee] += 1
			elif record.status == "Half Day":
				paid_days[record.employee] += 0.5
			elif record.status == "On Leave" and record.leave_type:
				is_lwp = frappe.db.get_value("Leave Type", record.leave_type, "is_lwp", cache=True)
				if not is_lwp:
					paid_days[record.employee] += 1
		return paid_days

	def _allowed_attendance_dates(self, employee: str) -> set[date]:
		employment = frappe.db.get_value(
			"Employee", employee, ["date_of_joining", "relieving_date"], as_dict=True
		)
		holiday_dates = {
			getdate(value)
			for value in get_holiday_dates_for_employee(employee, self.period_start, self.period_end)
		}
		allowed: set[date] = set()
		for offset in range(date_diff(self.period_end, self.period_start) + 1):
			attendance_date = getdate(add_days(self.period_start, offset))
			if attendance_date in holiday_dates:
				continue
			if employment and employment.date_of_joining and attendance_date < getdate(employment.date_of_joining):
				continue
			if employment and employment.relieving_date and attendance_date > getdate(employment.relieving_date):
				continue
			allowed.add(attendance_date)
		return allowed

	def _assert_attendance_complete(self) -> None:
		matrix = self.get_attendance_matrix()["rows"]
		pending = [row for row in matrix if row["state"] in ("Unmarked", "Conflict")]
		if pending:
			frappe.throw(_("Complete or resolve attendance for every work date before preparing variable earnings."))

	def _additional_salary_specs(self) -> list[dict[str, object]]:
		paid_days = self._attendance_paid_days()
		specs: list[dict[str, object]] = []
		for row in self.preview_rows:
			if row.match_status != "Matched" or not row.matched_employee:
				continue
			if self.basic_salary_component:
				if self.payroll_mode in ("Project", "Professional Services"):
					amount = flt(row.daily_rate) * paid_days.get(row.matched_employee, 0)
					should_create_basic = bool(flt(row.daily_rate))
				else:
					amount = flt(row.basic_salary)
					should_create_basic = bool(amount)
				if should_create_basic:
					specs.append(
						{
							"employee": row.matched_employee,
							"component": self.basic_salary_component,
							"amount": amount,
							"overwrite": 1,
						}
					)
			overtime_amount = flt(row.overtime_hours) * flt(row.overtime_rate)
			if overtime_amount:
				specs.append(
					{
						"employee": row.matched_employee,
						"component": self.overtime_salary_component,
						"amount": overtime_amount,
						"overwrite": 0,
					}
				)
			if flt(row.other_income):
				specs.append(
					{
						"employee": row.matched_employee,
						"component": self.other_income_salary_component,
						"amount": flt(row.other_income),
						"overwrite": 0,
					}
				)
		return specs

	@frappe.whitelist()
	def prepare_variable_earnings(self) -> dict[str, object]:
		"""Create and submit only explicitly confirmed, reversible Additional Salary documents."""
		self.check_permission("write")
		frappe.has_permission("Additional Salary", "create", throw=True)
		frappe.has_permission("Additional Salary", "submit", throw=True)
		if self.status not in ("Validated", "Applied"):
			frappe.throw(_("Validate the import before preparing variable earnings."))
		errors = self._validate_preview_rows()
		if errors:
			frappe.throw("<br>".join(errors), title=_("Import validation failed"))
		self._assert_attendance_complete()
		specs = self._additional_salary_specs()
		created: list[str] = []
		frappe.db.savepoint("payroll_import_variable_earnings")
		try:
			frappe.db.sql("SELECT name FROM `tabPayroll Import` WHERE name = %s FOR UPDATE", self.name)
			for employee in sorted({str(spec["employee"]) for spec in specs}):
				frappe.db.sql("SELECT name FROM `tabEmployee` WHERE name = %s FOR UPDATE", employee)
			for spec in specs:
				existing = frappe.db.get_value(
					"Additional Salary",
					{
						"ref_doctype": self.doctype,
						"ref_docname": self.name,
						"employee": spec["employee"],
						"salary_component": spec["component"],
						"docstatus": ("!=", 2),
					},
					"name",
				)
				if existing:
					created.append(existing)
					continue
				conflicting = frappe.db.get_value(
					"Additional Salary",
					{
						"employee": spec["employee"],
						"salary_component": spec["component"],
						"payroll_date": self.period_end,
						"docstatus": ("!=", 2),
					},
					"name",
				)
				if conflicting:
					frappe.throw(
						_(
							"Additional Salary {0} already exists for employee {1}, component {2}, "
							"and this payroll date."
						).format(conflicting, spec["employee"], spec["component"])
					)
				doc = frappe.get_doc({
					"doctype": "Additional Salary",
					"employee": spec["employee"],
					"company": self.company,
					"salary_component": spec["component"],
					"amount": spec["amount"],
					"payroll_date": self.period_end,
					"overwrite_salary_structure_amount": spec["overwrite"],
					"ref_doctype": self.doctype,
					"ref_docname": self.name,
				})
				doc.insert()
				doc.submit()
				created.append(doc.name)
			self.additional_salary_documents = json.dumps(created)
			self.save()
		except Exception:
			frappe.db.rollback(save_point="payroll_import_variable_earnings")
			raise
		return {"documents": created, "count": len(created)}

	@frappe.whitelist()
	def reverse_variable_earnings(self) -> dict[str, object]:
		"""Cancel only Additional Salary created by this import, before submitted Salary Slips exist."""
		self.check_permission("write")
		if self.payroll_entry and frappe.db.exists(
			"Salary Slip", {"payroll_entry": self.payroll_entry, "docstatus": 1}
		):
			frappe.throw(_("Submitted Salary Slips exist. Cancel them through the standard payroll flow first."))
		names = frappe.get_all(
			"Additional Salary",
			filters={"ref_doctype": self.doctype, "ref_docname": self.name, "docstatus": ("!=", 2)},
			pluck="name",
		)
		if names:
			salary_slips = frappe.get_all(
				"Salary Detail",
				filters={
					"parenttype": "Salary Slip",
					"additional_salary": ("in", names),
				},
				pluck="parent",
			)
			used_salary_slips = (
				frappe.get_all(
					"Salary Slip",
					filters={"name": ("in", salary_slips), "docstatus": ("!=", 2)},
					pluck="name",
				)
				if salary_slips
				else []
			)
			if used_salary_slips:
				frappe.throw(
					_("Variable earnings are already used by Salary Slips: {0}.").format(
						", ".join(used_salary_slips)
					)
				)
		frappe.db.savepoint("payroll_import_reverse_earnings")
		try:
			for name in names:
				doc = frappe.get_doc("Additional Salary", name)
				if doc.docstatus == 1:
					doc.cancel()
				elif doc.docstatus == 0:
					doc.delete()
			self.additional_salary_documents = None
			self.save()
		except Exception:
			frappe.db.rollback(save_point="payroll_import_reverse_earnings")
			raise
		return {"reversed": names, "count": len(names)}

	@frappe.whitelist()
	def get_attendance_matrix(self) -> dict[str, list[dict[str, object]]]:
		"""Return current attendance only; user confirmation is required before writing new rows."""
		self.check_permission("read")
		self._validate_period()
		employees = sorted(self._import_employee_names())
		if not employees:
			frappe.throw(_("No matched employees are available for attendance validation."))

		records = frappe.get_all(
			"Attendance",
			fields=[
				"name",
				"employee",
				"attendance_date",
				"status",
				"half_day_status",
				"leave_type",
				"docstatus",
			],
			filters={
				"employee": ("in", employees),
				"attendance_date": ("between", [self.period_start, self.period_end]),
				"docstatus": ("!=", 2),
			},
			order_by="employee, attendance_date, creation",
			limit_page_length=0,
		)
		by_employee_date: dict[tuple[str, date], list[dict]] = {}
		for record in records:
			by_employee_date.setdefault((record.employee, getdate(record.attendance_date)), []).append(record)

		matrix: list[dict[str, object]] = []
		attendance_days: dict[str, float] = {employee: 0.0 for employee in employees}
		for employee in employees:
			for attendance_date in sorted(self._allowed_attendance_dates(employee)):
				existing = by_employee_date.get((employee, getdate(attendance_date)), [])
				if len(existing) > 1:
					matrix.append(
						{
							"employee": employee,
							"attendance_date": attendance_date,
							"state": "Conflict",
							"message": _("Multiple active Attendance records exist for this employee and date."),
						}
					)
				elif existing and existing[0].docstatus != 1:
					record = existing[0]
					matrix.append(
						{
							"employee": employee,
							"attendance_date": attendance_date,
							"state": "Conflict",
							"attendance": record.name,
							"message": _("Attendance exists in draft and must be submitted or cancelled."),
						}
					)
				elif existing:
					record = existing[0]
					if record.status in ("Present", "Work From Home"):
						attendance_days[employee] += 1
					elif record.status == "Half Day":
						attendance_days[employee] += 0.5
					elif record.status == "On Leave" and record.leave_type:
						is_lwp = frappe.db.get_value("Leave Type", record.leave_type, "is_lwp", cache=True)
						if not is_lwp:
							attendance_days[employee] += 1
					matrix.append(
						{
							"employee": employee,
							"attendance_date": attendance_date,
							"state": "Existing",
							"attendance": record.name,
							"status": record.status,
							"half_day_status": record.half_day_status,
							"docstatus": record.docstatus,
						}
					)
				else:
					matrix.append({"employee": employee, "attendance_date": attendance_date, "state": "Unmarked"})
		preview_amounts = {
			row.matched_employee: flt(row.daily_rate) * attendance_days.get(row.matched_employee, 0)
			for row in self.preview_rows
			if row.matched_employee
		}
		return {
			"rows": matrix,
			"summaries": [
				{
					"employee": employee,
					"attendance_days": attendance_days[employee],
					"estimated_basic_amount": preview_amounts.get(employee, 0),
				}
				for employee in employees
			],
		}

	@frappe.whitelist()
	def sync_attendance_preview(self) -> dict[str, object]:
		"""Store the attendance-confirmed days and calculated amount shown in the preview grid.

		The original imported row remains available in ``source_data`` for traceability.
		This method is safe to call repeatedly after existing Attendance records have
		been reviewed.
		"""
		self.check_permission("write")
		matrix = self.get_attendance_matrix()
		summaries = {
			str(summary["employee"]): summary for summary in matrix["summaries"]
		}
		changed = False
		for row in self.preview_rows:
			if not row.matched_employee:
				continue
			summary = summaries.get(row.matched_employee)
			if not summary:
				continue
			attendance_days = flt(summary["attendance_days"])
			estimated_basic_amount = flt(summary["estimated_basic_amount"])
			if flt(row.days_worked) != attendance_days:
				row.days_worked = attendance_days
				changed = True
			if flt(row.attendance_days) != attendance_days:
				row.attendance_days = attendance_days
				changed = True
			if flt(row.estimated_basic_amount) != estimated_basic_amount:
				row.estimated_basic_amount = estimated_basic_amount
				changed = True
		if changed:
			self.flags.in_payroll_import_attendance_sync = True
			try:
				self.save()
			finally:
				self.flags.in_payroll_import_attendance_sync = False
		return {"summaries": matrix["summaries"], "updated": changed}

	@frappe.whitelist()
	def apply_attendance_matrix(self, confirmations: list[dict[str, object]] | str) -> dict[str, object]:
		"""Create confirmed Attendance rows and refresh the persisted preview summary."""
		self.check_permission("write")
		if self.additional_salary_documents:
			frappe.throw(_("Reverse the prepared variable earnings before changing attendance."))
		if self.payroll_entry and frappe.db.exists(
			"Salary Slip", {"payroll_entry": self.payroll_entry, "docstatus": 1}
		):
			frappe.throw(_("Submitted Salary Slips exist. Attendance can no longer be changed from this import."))
		if isinstance(confirmations, str):
			confirmations = json.loads(confirmations)
		if not isinstance(confirmations, list):
			frappe.throw(_("Attendance confirmations must be a list."))
		if confirmations:
			frappe.has_permission("Attendance", "create", throw=True)
			frappe.has_permission("Attendance", "submit", throw=True)

		allowed_employees = self._import_employee_names()
		created: list[str] = []
		frappe.db.savepoint("payroll_import_attendance")
		try:
			prepared_confirmations: list[dict[str, object]] = []
			for confirmation in confirmations:
				employee = str(confirmation.get("employee") or "")
				if not confirmation.get("attendance_date"):
					frappe.throw(_("Attendance confirmation requires a date."))
				attendance_date = getdate(confirmation.get("attendance_date"))
				status = str(confirmation.get("status") or "")
				if employee not in allowed_employees or not (
					getdate(self.period_start) <= attendance_date <= getdate(self.period_end)
				):
					frappe.throw(_("Attendance confirmation is outside this import's employees or period."))
				if attendance_date not in self._allowed_attendance_dates(employee):
					frappe.throw(_("Attendance cannot be created on a holiday or outside the employment dates."))
				if status not in ATTENDANCE_STATUSES:
					frappe.throw(_("Invalid Attendance status: {0}").format(status))
				prepared_confirmations.append(
					{"employee": employee, "attendance_date": attendance_date, "status": status}
				)

			# Serialize imports for each employee before checking Attendance. The
			# deterministic order prevents two imports from both seeing a missing
			# record and attempting the same insert at once.
			for employee in sorted({str(item["employee"]) for item in prepared_confirmations}):
				frappe.db.sql("SELECT name FROM `tabEmployee` WHERE name = %s FOR UPDATE", employee)

			for confirmation in prepared_confirmations:
				employee = str(confirmation["employee"])
				attendance_date = getdate(confirmation["attendance_date"])
				status = str(confirmation["status"])
				if frappe.db.exists(
					"Attendance", {"employee": employee, "attendance_date": attendance_date, "docstatus": ("!=", 2)}
				):
					frappe.throw(
						_("Attendance already exists for {0} on {1}; it was not overwritten.").format(
							employee, attendance_date
						)
					)
				attendance = frappe.get_doc(
					{
						"doctype": "Attendance",
						"employee": employee,
						"attendance_date": attendance_date,
						"status": status,
						"half_day_status": "Absent" if status == "Half Day" else None,
					}
				)
				attendance.insert()
				attendance.submit()
				created.append(attendance.name)
			summary = self.sync_attendance_preview()
		except Exception:
			frappe.db.rollback(save_point="payroll_import_attendance")
			raise
		return {"created": created, "count": len(created), **summary}

	@frappe.whitelist()
	def apply_import(self) -> dict[str, str]:
		"""Create one draft Payroll Entry; never submit payroll, slips, or accounting entries."""
		self.check_permission("write")
		frappe.has_permission("Payroll Entry", "create", throw=True)
		if not self.cost_center:
			frappe.throw(_("A Cost Center is required to create a draft Payroll Entry."))
		locked_import = frappe.db.sql(
			"SELECT payroll_entry FROM `tabPayroll Import` WHERE name = %s FOR UPDATE", self.name, as_dict=True
		)
		if locked_import and locked_import[0].payroll_entry:
			return {"payroll_entry": locked_import[0].payroll_entry}
		if self.payroll_entry:
			return {"payroll_entry": self.payroll_entry}
		if self.status != "Validated":
			frappe.throw(_("Validate the import successfully before creating a Payroll Entry."))
		validation_errors = self._validate_default_salary_structure()
		if not validation_errors:
			validation_errors.extend(self._validate_preview_rows())
		if validation_errors:
			frappe.throw("<br>".join(validation_errors), title=_("Import validation failed"))

		company = frappe.db.get_value(
			"Company",
			self.company,
			["default_currency", "default_payroll_payable_account"],
			as_dict=True,
		)
		if not company or not company.default_payroll_payable_account:
			frappe.throw(_("Company default payroll payable account is required."))

		employees = sorted(self._import_employee_names())
		if not employees:
			frappe.throw(_("No matched employees are available to apply."))
		frappe.db.savepoint("payroll_import_apply")
		try:
			payroll_entry = frappe.get_doc(
				{
					"doctype": "Payroll Entry",
					"company": self.company,
					"posting_date": nowdate(),
					"currency": company.default_currency,
					"exchange_rate": 1,
					"payroll_payable_account": company.default_payroll_payable_account,
					"payroll_frequency": self._selected_payroll_frequency(),
					"start_date": self.period_start,
					"end_date": self.period_end,
					"cost_center": self.cost_center,
					"project": self.project,
					"employees": [{"employee": employee} for employee in employees],
				}
			)
			payroll_entry.insert()
			self.payroll_entry = payroll_entry.name
			self.status = "Applied"
			self.save()
		except Exception:
			frappe.db.rollback(save_point="payroll_import_apply")
			raise
		return {"payroll_entry": payroll_entry.name}

	@frappe.whitelist()
	def download_template(self) -> dict[str, str]:
		"""Return a paste-ready TSV template in the configured mapping order."""
		self.check_permission("read")
		self._ensure_default_column_mappings()
		mappings = sorted(
			(mapping for mapping in self.column_mappings if mapping.canonical_field and not mapping.ignore),
			key=lambda mapping: (mapping.position or 9999, mapping.idx),
		)
		# Never echo an arbitrary source header into a downloadable spreadsheet;
		# spreadsheet applications may interpret =, +, - or @ headers as formulas.
		headers = [XLSX_VISIBLE_HEADERS.get(mapping.canonical_field, _("Campo")) for mapping in mappings]
		return {"filename": "plantilla_importacion_nomina.tsv", "content": "\t".join(headers) + "\n"}

	@frappe.whitelist()
	def download_xlsx_template(self) -> dict[str, str]:
		"""Return an inert, values-only XLSX template with Spanish visible headers."""
		self.check_permission("read")
		self._ensure_default_column_mappings()
		try:
			from openpyxl import Workbook
		except ImportError:
			frappe.throw(_("La biblioteca XLSX requerida no está disponible en este entorno."))
		mappings = sorted(
			(mapping for mapping in self.column_mappings if mapping.canonical_field and not mapping.ignore),
			key=lambda mapping: (mapping.position or 9999, mapping.idx),
		)
		workbook = Workbook()
		worksheet = workbook.active
		worksheet.title = "Nómina"
		worksheet.append([XLSX_VISIBLE_HEADERS.get(mapping.canonical_field, _("Campo")) for mapping in mappings])
		stream = io.BytesIO()
		workbook.save(stream)
		return {
			"filename": "plantilla_importacion_nomina.xlsx",
			"content_base64": base64.b64encode(stream.getvalue()).decode(),
			"mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
		}
