# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

import frappe
from openpyxl import Workbook
from openpyxl.styles import PatternFill

from hrms.payroll.doctype.payroll_import.payroll_import import (
	PayrollImport,
	MAX_PASTED_COLUMNS,
	normalize_text,
	parse_number,
	parse_pasted_data,
)
from hrms.tests.utils import HRMSTestSuite


class TestPayrollImport(HRMSTestSuite):
	@staticmethod
	def make_import(values=None):
		return PayrollImport({"doctype": "Payroll Import", **(values or {})})

	def test_payroll_sidebar_exposes_import(self):
		sidebar_path = Path(__file__).resolve().parents[3] / "workspace_sidebar" / "payroll.json"
		sidebar = json.loads(sidebar_path.read_text(encoding="utf-8"))
		self.assertTrue(any(item.get("link_to") == "Payroll Import" for item in sidebar["items"]))

	def test_import_form_keeps_internal_and_advanced_configuration_hidden_by_default(self):
		metadata_path = Path(__file__).with_name("payroll_import.json")
		metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
		fields = {field["fieldname"]: field for field in metadata["fields"]}
		hidden_by_default = {
			"workbook_filename",
			"workbook_hash",
			"workbook_sheet",
			"workbook_header_row",
			"workbook_data_start_row",
			"workbook_data_end_row",
			"workbook_candidates",
			"raw_data_section",
			"raw_data",
			"mapping_section",
			"column_mappings",
			"close_advanced_configuration",
		}
		for fieldname in hidden_by_default:
			self.assertEqual(fields[fieldname].get("hidden"), 1, fieldname)

		self.assertEqual(fields["workbook_header_row"].get("default"), "1")
		self.assertEqual(fields["workbook_data_start_row"].get("default"), "2")
		field_order = metadata["field_order"]
		self.assertLess(field_order.index("workbook_file"), field_order.index("preview_section"))
		self.assertLess(field_order.index("preview_rows"), field_order.index("validation_section"))
		self.assertLess(field_order.index("validation_messages"), field_order.index("advanced_import_section"))
		self.assertEqual(fields["close_advanced_configuration"].get("fieldtype"), "Button")
		self.assertLess(field_order.index("advanced_import_section"), field_order.index("close_advanced_configuration"))

	def test_import_form_groups_payroll_configuration_into_balanced_sections(self):
		metadata = json.loads(Path(__file__).with_name("payroll_import.json").read_text(encoding="utf-8"))
		fields = {field["fieldname"]: field for field in metadata["fields"]}
		field_order = metadata["field_order"]

		self.assertEqual(fields["general_payroll_section"]["fieldtype"], "Section Break")
		self.assertEqual(fields["period_section"]["fieldtype"], "Section Break")
		self.assertEqual(fields["status_references_section"]["fieldtype"], "Section Break")
		self.assertEqual(fields["cost_center"].get("reqd"), 1)
		self.assertEqual(
			field_order[
				field_order.index("general_payroll_section") + 1 : field_order.index("column_break_general")
			],
			["company", "payroll_mode", "default_salary_structure", "project"],
		)
		self.assertEqual(
			field_order[
				field_order.index("column_break_general") + 1 : field_order.index("period_section")
			],
			["cost_center", "basic_salary_component", "overtime_salary_component", "other_income_salary_component"],
		)
		self.assertEqual(
			field_order[
				field_order.index("period_section") + 1 : field_order.index("status_references_section")
			],
			["period_start", "column_break_period", "period_end"],
		)
		self.assertEqual(
			field_order[
				field_order.index("status_references_section") + 1 : field_order.index("workbook_section")
			],
			["status", "payroll_entry", "column_break_references", "additional_salary_documents"],
		)

	def test_import_preview_grid_shows_context_and_confirmed_worked_days(self):
		row_metadata_path = Path(__file__).resolve().parents[1] / "payroll_import_row" / "payroll_import_row.json"
		row_metadata = json.loads(row_metadata_path.read_text(encoding="utf-8"))
		fields = {field["fieldname"]: field for field in row_metadata["fields"]}
		visible_fields = {
			"employee_code",
			"employee_name",
			"matched_employee",
			"match_status",
			"basic_salary",
			"daily_rate",
			"days_worked",
			"estimated_basic_amount",
			"overtime_hours",
			"overtime_rate",
			"other_income",
			"notes",
			"payroll_category",
			"project",
			"cost_center",
		}
		for fieldname in visible_fields:
			self.assertEqual(fields[fieldname].get("in_list_view"), 1, fieldname)
		for fieldname in {
			"source_row",
			"source_data",
			"parse_error",
			"viatico_data_ignored",
			"attendance_days",
		}:
			self.assertNotEqual(fields[fieldname].get("in_list_view"), 1, fieldname)
		self.assertEqual(fields["days_worked"]["label"], "Días trabajados")
		self.assertEqual(fields["estimated_basic_amount"]["label"], "Monto básico calculado")
		self.assertEqual(fields["attendance_days"].get("hidden"), 1)

	def test_import_list_shows_project_and_payroll_period(self):
		metadata = json.loads(Path(__file__).with_name("payroll_import.json").read_text(encoding="utf-8"))
		fields = {field["fieldname"]: field for field in metadata["fields"]}
		self.assertEqual(fields["project"].get("in_list_view"), 1)
		self.assertEqual(fields["period_start"].get("in_list_view"), 1)

		list_script = Path(__file__).with_name("payroll_import_list.js").read_text(encoding="utf-8")
		self.assertIn('add_fields: ["period_end"]', list_script)
		self.assertIn('label: __("Payroll Period")', list_script)
		self.assertIn("doc.period_end", list_script)

	def test_import_client_uses_single_xlsx_preview_action_and_explicit_advanced_toggle(self):
		contents = Path(__file__).with_name("payroll_import.js").read_text(encoding="utf-8")
		self.assertIn('__("Cargar y previsualizar XLSX")', contents)
		self.assertNotIn('__("Inspeccionar XLSX")', contents)
		self.assertNotIn('__("Generar vista previa XLSX")', contents)
		inspect_call = contents.index('await save_before_call(frm, "inspect_workbook");')
		reload_after_inspection = contents.index("await frm.reload_doc();", inspect_call)
		preview_call = contents.index('await frm.call("parse_workbook_preview");', inspect_call)
		self.assertLess(inspect_call, reload_after_inspection)
		self.assertLess(reload_after_inspection, preview_call)
		self.assertIn('await frm.call("download_xlsx_template")', contents)
		self.assertIn('await frm.call("download_template")', contents)
		self.assertNotIn('save_before_call(frm, "download_xlsx_template")', contents)
		self.assertNotIn('save_before_call(frm, "download_template")', contents)
		self.assertIn('__("Editar configuración de importación")', contents)
		self.assertIn('__("Ocultar configuración de importación")', contents)
		self.assertIn("toggle_advanced_import_configuration(frm, false);", contents)
		self.assertIn("frm.clear_custom_buttons()", contents)
		self.assertIn("close_advanced_configuration(frm)", contents)
		self.assertIn('"close_advanced_configuration"', contents)

		advanced_actions = contents.index("if (frm.__advanced_import_configuration_visible)")
		tsv_action = contents.index('__("Descargar plantilla TSV")')
		pasted_preview_action = contents.index('__("Generar vista previa pegada")')
		self.assertLess(advanced_actions, tsv_action)
		self.assertLess(advanced_actions, pasted_preview_action)

		for group, variable in {"Archivo": "file", "Revisión": "review", "Nómina": "payroll"}.items():
			self.assertIn(f'const {variable}_group = __("{group}");', contents)
		self.assertIn('if (has_preview && ["Draft", "Error"].includes(frm.doc.status))', contents)
		self.assertIn('__("Preparar importes para nómina")', contents)
		self.assertIn('__("Confirmar y actualizar asistencia")', contents)
		workbook_file_handler = contents.index("workbook_file(frm)")
		self.assertGreater(contents.index("rebuild_import_actions(frm);", workbook_file_handler), workbook_file_handler)

		advanced_fields_start = contents.index("const advanced_import_fields")
		advanced_fields_end = contents.index("];", advanced_fields_start)
		advanced_fields = contents[advanced_fields_start:advanced_fields_end]
		for fieldname in {
			"workbook_sheet",
			"workbook_header_row",
			"workbook_data_start_row",
			"workbook_data_end_row",
			"raw_data",
			"column_mappings",
			"close_advanced_configuration",
		}:
			self.assertIn(f'"{fieldname}"', advanced_fields)
		for fieldname in {"workbook_filename", "workbook_hash", "workbook_candidates"}:
			self.assertNotIn(f'"{fieldname}"', advanced_fields)

	def test_import_client_matches_source_editability_to_backend_protection(self):
		contents = Path(__file__).with_name("payroll_import.js").read_text(encoding="utf-8")
		self.assertIn(
			'return Boolean(frm.doc.status === "Applied" || frm.doc.payroll_entry || frm.doc.additional_salary_documents);',
			contents,
		)
		self.assertIn("frm.toggle_enable(payroll_import_source_fields, !source_is_locked);", contents)
		self.assertIn('frappe.utils.get_form_link("Payroll Entry", frm.doc.payroll_entry, true)', contents)
		self.assertIn('__("Editable hasta crear la Entrada de nómina.")', contents)
		self.assertIn('__("Bloqueado: ya existe la Entrada de nómina {0}.", [payroll_entry_link])', contents)

		source_fields_start = contents.index("const payroll_import_source_fields")
		source_fields_end = contents.index("];", source_fields_start)
		source_fields = contents[source_fields_start:source_fields_end]
		for fieldname in {
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
			"workbook_sheet",
			"workbook_header_row",
			"workbook_data_start_row",
			"workbook_data_end_row",
			"column_mappings",
		}:
			self.assertIn(f'"{fieldname}"', source_fields)

	def test_existing_payroll_entry_locks_source_fields_even_when_status_is_not_applied(self):
		import_doc = self.make_import({"status": "Draft", "cost_center": "New Cost Center"})
		before = frappe._dict(
			status="Draft",
			payroll_entry="HR-PRUN-2026-00001",
			additional_salary_documents=None,
			column_mappings=[],
			preview_rows=[],
		)
		import_doc.get_doc_before_save = Mock(return_value=before)
		import_doc.has_value_changed = Mock(side_effect=lambda fieldname: fieldname == "cost_center")

		with self.assertRaises(frappe.ValidationError):
			import_doc._validate_immutable_applied_fields()

		self.assertIn("cost_center", [call.args[0] for call in import_doc.has_value_changed.call_args_list])

	def test_parser_accepts_tsv_and_csv(self):
		headers, rows = parse_pasted_data("employee_code\tdays_worked\nEMP-001\t10\n")
		self.assertEqual(headers, ["employee_code", "days_worked"])
		self.assertEqual(rows, [["EMP-001", "10"]])

		headers, rows = parse_pasted_data("employee_code,days_worked\nEMP-002,5\n")
		self.assertEqual(headers, ["employee_code", "days_worked"])
		self.assertEqual(rows, [["EMP-002", "5"]])

	def test_number_parser_supports_common_regional_formats(self):
		self.assertEqual(parse_number("C$ 1.234,56"), 1234.56)
		self.assertEqual(parse_number("C$ 1,234.56"), 1234.56)
		self.assertEqual(parse_number("1,234"), 1234)
		self.assertEqual(parse_number("(C$ 10.00)"), -10)
		self.assertEqual(parse_number("-10.00"), -10)

	def test_number_parser_rejects_formula_like_and_contaminated_text(self):
		for value in ("=1+1", "+10", "@SUM(A1)", "-1+1", "12abc", "C$ 10 texto"):
			with self.assertRaises(ValueError):
				parse_number(value)

	def test_csv_and_tsv_formula_like_values_are_rejected(self):
		for raw_data in (
			"employee_code,basic_salary\nEMP-001,=1+1\n",
			"employee_code\tbasic_salary\nEMP-001\t@SUM(A1)\n",
		):
			_headers, rows = parse_pasted_data(raw_data)
			with self.assertRaises(ValueError):
				parse_number(rows[0][1])

	def test_pasted_data_enforces_column_limit(self):
		header = ",".join(f"column_{index}" for index in range(MAX_PASTED_COLUMNS + 1))
		with self.assertRaises(frappe.ValidationError):
			parse_pasted_data(f"{header}\n")

	def test_tsv_template_does_not_emit_formula_like_source_headers(self):
		import_doc = self.make_import(
			{
				"column_mappings": [
					{"source_column": "=SUM(A1)", "canonical_field": "employee_name", "position": 1},
					{"source_column": "+tarifa", "canonical_field": "daily_rate", "position": 2},
					{"source_column": "-monto", "canonical_field": "basic_salary", "position": 3},
					{"source_column": "@dato", "canonical_field": "notes", "position": 4},
				]
			}
		)
		import_doc.check_permission = Mock()
		template = import_doc.download_template()
		headers = template["content"].strip().split("\t")
		self.assertEqual(headers, ["Nombre de empleado", "Tarifa diaria", "Salario básico", "Notas"])
		self.assertFalse(any(header.startswith(("=", "+", "-", "@")) for header in headers))

	def test_xlsx_header_candidates_cover_six_workbook_structures(self):
		"""Structural discovery handles common sheet/header arrangements without side effects."""
		variants = [
			("Nómina", 1, ["Código de empleado", "Nombre de empleado"]),
			("Detalle", 2, ["employee_code", "daily_rate"]),
			("Proyecto A", 3, ["Empleado", "Días trabajados"]),
			("Quincena 1", 4, ["Employee Code", "Overtime Hours"]),
			("Servicios", 5, ["Nombre", "Otros ingresos"]),
			("Resumen", 6, ["employee", "project"]),
		]
		import_doc = self.make_import()
		for title, header_row, headers in variants:
			workbook = Workbook()
			worksheet = workbook.active
			worksheet.title = title
			for _index in range(header_row - 1):
				worksheet.append(["Título"])
			worksheet.append(headers)
			candidates = import_doc._workbook_header_candidates(workbook)
			self.assertTrue(
				any(candidate["sheet"] == title and candidate["header_row"] == header_row for candidate in candidates)
			)

	def test_xlsx_real_workbook_headers_map_without_confusing_overtime_totals(self):
		"""The six supplied workbook header variants map only per-employee values."""
		variants = [
			(["NOMBRE Y APELLIDO(S)", "SALARIO MENSUAL"], "basic_salary"),
			(["NOMBRE Y APELLIDO(S)", "SALARIO POR DIA"], "daily_rate"),
			(["NOMBRE Y APELLIDO(S)", "VALOR DE H/E"], "overtime_rate"),
			(["NOMBRE Y APELLIDO(S)", "VALOR H/E"], "overtime_rate"),
			(["NOMBRE Y APELLIDO(S)", "VALOR DE HORAS EXTRAS"], "overtime_rate"),
			(["NOMBRE Y APELLIDO(S)", "VALOR DE HE"], "overtime_rate"),
		]
		for headers, expected_field in variants:
			import_doc = self.make_import({"column_mappings": []})
			mapping, _ignored = import_doc._mapped_headers(headers)
			self.assertEqual(mapping, {0: "employee_name", 1: expected_field})

		mapping, _ignored = self.make_import({"column_mappings": []})._mapped_headers(
			["NOMBRE Y APELLIDO", "SALARIO MENSUAL"]
		)
		self.assertEqual(mapping, {0: "employee_name", 1: "basic_salary"})

		import_doc = self.make_import({"column_mappings": []})
		mapping, _ignored = import_doc._mapped_headers(
			["NOMBRE Y APELLIDO(S)", "TOTAL DE H/E", "TOTAL HORAS EXTRAS"]
		)
		self.assertEqual(mapping, {0: "employee_name"})

	def test_xlsx_candidate_suggests_data_end_before_total_or_next_section(self):
		workbook = Workbook()
		worksheet = workbook.active
		worksheet.title = "Nómina"
		worksheet.append(["NOMBRE Y APELLIDO(S)", "SALARIO POR DIA"])
		worksheet.append(["Ana Pérez", 100])
		worksheet.append(["TOTALES", 100])
		worksheet.append([])
		worksheet.append(["NOMBRE Y APELLIDO(S)", "VALOR H/E"])
		worksheet.append(["Ana Pérez", 25])
		candidates = self.make_import()._workbook_header_candidates(workbook)
		self.assertEqual(candidates[0]["data_end_row"], 2)
		self.assertEqual(candidates[1]["data_end_row"], 6)
		self.assertFalse(PayrollImport._is_total_row(["NOMBRE Y APELLIDO(S)", "TOTAL DE H/E"]))

	def test_xlsx_limits_ignore_far_formatted_blank_columns(self):
		workbook = Workbook()
		worksheet = workbook.active
		worksheet.append(["Código de empleado", "Salario mensual"])
		worksheet.cell(row=1, column=101).fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
		self.assertGreater(worksheet.max_column, 100)
		PayrollImport._validate_workbook_limits(workbook)

	def test_xlsx_limits_block_real_content_outside_column_limit(self):
		workbook = Workbook()
		worksheet = workbook.active
		worksheet.cell(row=1, column=101, value="Dato real")
		with self.assertRaises(frappe.ValidationError):
			PayrollImport._validate_workbook_limits(workbook)

	def test_xlsx_reader_uses_cached_values_and_rejects_stale_formulas(self):
		workbook = Workbook()
		worksheet = workbook.active
		worksheet.title = "Nómina"
		worksheet.append(["Código de empleado", "Tarifa diaria"])
		worksheet.append(["EMP-001", "=100+25"])
		stream = BytesIO()
		workbook.save(stream)
		import_doc = self.make_import(
			{"workbook_sheet": "Nómina", "workbook_header_row": 1, "workbook_data_start_row": 2}
		)
		with self.assertRaises(frappe.ValidationError):
			import_doc._workbook_rows(stream.getvalue())

	def test_xlsx_formula_like_numeric_cell_is_never_parsed_as_a_number(self):
		workbook = Workbook()
		worksheet = workbook.active
		worksheet.title = "Nómina"
		worksheet.append(["Código de empleado", "Salario mensual"])
		worksheet.append(["EMP-001", "=1+1"])
		stream = BytesIO()
		workbook.save(stream)
		import_doc = self.make_import(
			{"workbook_sheet": "Nómina", "workbook_header_row": 1, "workbook_data_start_row": 2}
		)
		with self.assertRaises(frappe.ValidationError):
			import_doc._workbook_rows(stream.getvalue())

	def test_xlsx_spanish_visible_headers_map_to_canonical_fields(self):
		import_doc = self.make_import({"column_mappings": []})
		mapping, ignored = import_doc._mapped_headers(
			["Código de empleado", "Nombre de empleado", "Tarifa diaria", "Tarifa por hora extra"]
		)
		self.assertEqual(
			mapping,
			{0: "employee_code", 1: "employee_name", 2: "daily_rate", 3: "overtime_rate"},
		)
		self.assertEqual(ignored, [])

	def test_xlsx_overlapping_scope_is_locked_and_blocked(self):
		import_doc = self.make_import(
			{
				"name": "HR-PIMP-2026-00001",
				"workbook_sheet": "Nómina",
				"workbook_header_row": 2,
				"workbook_data_start_row": 3,
				"workbook_data_end_row": 20,
			}
		)
		with (
			patch("frappe.db.sql", side_effect=[[], [frappe._dict(name="HR-PIMP-2026-00002")]]) as sql,
			self.assertRaises(frappe.ValidationError),
		):
			import_doc._lock_and_assert_workbook_section_available("hash")
		self.assertIn("tabDocType", sql.call_args_list[0].args[0])
		self.assertIn("FOR UPDATE", sql.call_args_list[0].args[0])
		self.assertIn("tabPayroll Import", sql.call_args_list[1].args[0])
		self.assertIn("FOR UPDATE", sql.call_args_list[1].args[0])
		self.assertEqual(sql.call_args_list[1].args[1], ("HR-PIMP-2026-00001", "hash", "Nómina", 20, 3))

	def test_xlsx_section_lock_allows_a_non_overlapping_claim(self):
		import_doc = self.make_import(
			{
				"name": "HR-PIMP-2026-00003",
				"workbook_sheet": "Nómina",
				"workbook_data_start_row": 30,
				"workbook_data_end_row": 40,
			}
		)
		with patch("frappe.db.sql", side_effect=[[], []]) as sql:
			import_doc._lock_and_assert_workbook_section_available("hash")
		self.assertEqual(sql.call_count, 2)

	def test_column_mapping_ignores_viaticos(self):
		import_doc = self.make_import({"company": "_Test Company", "column_mappings": []})
		mapping, ignored = import_doc._mapped_headers(["employee_code", "viaticos", "dias trabajados"])
		self.assertEqual(mapping, {0: "employee_code", 2: "days_worked"})
		self.assertEqual(ignored, ["viaticos"])

	def test_duplicate_rows_are_ignored_or_blocked(self):
		seen = {}
		self.assertEqual(PayrollImport._classify_duplicate(seen, "emp-1", "same", 2), (None, ""))
		self.assertEqual(PayrollImport._classify_duplicate(seen, "emp-1", "same", 3)[0], "Ignored")
		self.assertEqual(PayrollImport._classify_duplicate(seen, "emp-1", "different", 4)[0], "Blocked")

	def test_employee_name_normalization_and_ambiguous_code_are_safe(self):
		self.assertEqual(normalize_text("  José  Pérez "), "jose perez")
		import_doc = self.make_import({"company": "_Test Company"})
		with patch("frappe.get_all", return_value=[frappe._dict(name="EMP-1"), frappe._dict(name="EMP-2")]):
			employee, status, _message = import_doc._resolve_employee("DUPLICATE", "")
		self.assertIsNone(employee)
		self.assertEqual(status, "Ambiguous")

	def test_employee_long_imported_name_matches_one_contained_active_name(self):
		import_doc = self.make_import({"company": "_Test Company"})
		candidates = [frappe._dict(name="EMP-001", employee_name="Halmar Cárcamo")]
		with patch("frappe.get_all", return_value=candidates):
			employee, status, _message = import_doc._resolve_employee("", "HALMAR DAVID CARCAMO")
		self.assertEqual(employee, "EMP-001")
		self.assertEqual(status, "Matched")

	def test_employee_single_token_is_not_auto_matched_from_long_imported_name(self):
		import_doc = self.make_import({"company": "_Test Company"})
		candidates = [frappe._dict(name="EMP-001", employee_name="Halmar")]
		with patch("frappe.get_all", return_value=candidates):
			employee, status, _message = import_doc._resolve_employee("", "HALMAR DAVID CARCAMO")
		self.assertIsNone(employee)
		self.assertEqual(status, "Not Found")

	def test_employee_multiple_contained_active_names_are_ambiguous(self):
		import_doc = self.make_import({"company": "_Test Company"})
		candidates = [
			frappe._dict(name="EMP-001", employee_name="Donald Fonseca"),
			frappe._dict(name="EMP-002", employee_name="Donald Arrechavala"),
		]
		with patch("frappe.get_all", return_value=candidates):
			employee, status, _message = import_doc._resolve_employee(
				"", "DONALD MARTIN FONSECA ARRECHAVALA"
			)
		self.assertIsNone(employee)
		self.assertEqual(status, "Ambiguous")

	def test_manual_employee_override_is_normalized_when_active_in_company(self):
		import_doc = self.make_import({"company": "_Test Company"})
		row = frappe._dict(
			matched_employee="EMP-001",
			source_row=2,
			match_status="Not Found",
			validation_message="No encontrado",
			parse_error=0,
		)
		with patch(
			"frappe.db.get_value", return_value=frappe._dict(company="_Test Company", status="Active")
		):
			self.assertIsNone(import_doc._validate_matched_employee(row))
		self.assertEqual(row.match_status, "Matched")
		self.assertEqual(row.validation_message, "")

	def test_manual_employee_override_rejects_other_company_or_inactive_employee(self):
		import_doc = self.make_import({"company": "_Test Company"})
		for employee in (
			frappe._dict(company="Other Company", status="Active"),
			frappe._dict(company="_Test Company", status="Inactive"),
		):
			row = frappe._dict(matched_employee="EMP-001", source_row=2)
			with patch("frappe.db.get_value", return_value=employee):
				error = import_doc._validate_matched_employee(row)
			self.assertIn("active", error)

	def test_manual_employee_override_cannot_clear_a_blocked_numeric_row(self):
		import_doc = self.make_import({"company": "_Test Company"})
		row = frappe._dict(
			matched_employee="EMP-001",
			source_row=2,
			match_status="Blocked",
			validation_message="Invalid numeric value(s): basic_salary.",
			parse_error=1,
		)
		with patch(
			"frappe.db.get_value", return_value=frappe._dict(company="_Test Company", status="Active")
		) as get_value:
			error = import_doc._validate_matched_employee(row)
		self.assertIn("parser error", error)
		self.assertEqual(row.match_status, "Blocked")
		self.assertEqual(row.validation_message, "Invalid numeric value(s): basic_salary.")
		get_value.assert_not_called()

	def test_manual_resolution_client_contract_preserves_blocked_rows(self):
		js_path = Path(__file__).with_name("payroll_import.js")
		contents = js_path.read_text(encoding="utf-8")
		blocked_guard = contents.index('if (row.parse_error || row.match_status === "Blocked")')
		matched_assignment = contents.index('row.match_status = "Matched"')
		self.assertLess(blocked_guard, matched_assignment)

	def test_invalid_parse_persists_server_side_error_marker(self):
		import_doc = self.make_import({"column_mappings": []})
		import_doc.save = Mock()
		with patch.object(import_doc, "_resolve_employee", return_value=("EMP-001", "Matched", "")):
			import_doc._parse_preview_rows(
				["employee_code", "basic_salary"],
				[["EMP-001", "=1+1"]],
				source="paste",
				source_row_start=2,
			)
		row = import_doc.preview_rows[0]
		self.assertEqual(row.parse_error, 1)
		self.assertEqual(row.match_status, "Blocked")

	def test_server_side_parse_marker_blocks_manipulated_manual_match(self):
		import_doc = self.make_import(
			{
				"cost_center": "Principal - CYCE",
				"preview_rows": [
					{
						"source_row": 2,
						"matched_employee": "EMP-001",
						"match_status": "Matched",
						"validation_message": "",
						"parse_error": 1,
					}
				]
			}
		)
		errors = import_doc._validate_preview_rows()
		self.assertEqual(len(errors), 1)
		self.assertIn("parser error", errors[0])

	def test_client_cannot_clear_persisted_parse_error_marker(self):
		import_doc = self.make_import(
			{"preview_rows": [{"name": "row-1", "source_row": 2, "parse_error": 0}]}
		)
		before = frappe._dict(preview_rows=[frappe._dict(name="row-1", parse_error=1)])
		import_doc.get_doc_before_save = Mock(return_value=before)
		with self.assertRaises(frappe.ValidationError):
			import_doc._validate_parse_error_immutability()

	def test_invalid_period_is_blocked(self):
		import_doc = self.make_import({"period_start": "2026-10-16", "period_end": "2026-10-15"})
		with self.assertRaises(frappe.ValidationError):
			import_doc._validate_period()

	def test_fortnightly_period_requires_calendar_half_month(self):
		valid_first_half = self.make_import(
			{
				"payroll_mode": "Fortnightly INSS/IR",
				"period_start": "2026-10-01",
				"period_end": "2026-10-15",
			}
		)
		valid_first_half._validate_period()

		valid_second_half = self.make_import(
			{
				"payroll_mode": "Fortnightly INSS/IR",
				"period_start": "2026-10-16",
				"period_end": "2026-10-31",
			}
		)
		valid_second_half._validate_period()

		invalid = self.make_import(
			{
				"payroll_mode": "Fortnightly INSS/IR",
				"period_start": "2026-10-02",
				"period_end": "2026-10-15",
			}
		)
		with self.assertRaises(frappe.ValidationError):
			invalid._validate_period()

	def test_fortnightly_business_cycle_uses_bimonthly_frequency(self):
		import_doc = self.make_import({"default_salary_structure": "Test Quincenal"})
		with patch("frappe.db.get_value", return_value="Bimonthly"):
			self.assertEqual(import_doc._selected_payroll_frequency(), "Bimonthly")

	def test_fortnightly_structure_requires_inss_and_ir(self):
		import_doc = self.make_import({"default_salary_structure": "Test Quincenal"})
		structure = frappe._dict(
			deductions=[
				frappe._dict(salary_component="INSS Laboral"),
				frappe._dict(salary_component="IR Laboral"),
			]
		)
		with patch("frappe.get_cached_doc", return_value=structure):
			self.assertTrue(import_doc._structure_has_statutory_deductions())

	def test_project_basic_uses_confirmed_attendance_days(self):
		import_doc = self.make_import(
			{
				"payroll_mode": "Project",
				"basic_salary_component": "Basic",
				"overtime_salary_component": "Overtime",
				"other_income_salary_component": "Other Income",
				"preview_rows": [
					{
						"matched_employee": "EMP-001",
						"match_status": "Matched",
						"daily_rate": 100,
						"days_worked": 15,
						"overtime_hours": 2,
						"overtime_rate": 25,
						"other_income": 30,
					}
				],
			}
		)
		with patch.object(import_doc, "_attendance_paid_days", return_value={"EMP-001": 10.5}):
			specs = import_doc._additional_salary_specs()
		self.assertEqual([spec["amount"] for spec in specs], [1050, 50, 30])

	def test_variable_earnings_block_existing_employee_component_and_payroll_date(self):
		import_doc = self.make_import(
			{
				"name": "HR-PIMP-2026-00001",
				"company": "_Test Company",
				"period_end": "2026-10-15",
				"status": "Validated",
			}
		)
		import_doc.check_permission = Mock()
		with (
			patch("frappe.has_permission"),
			patch("frappe.db.savepoint"),
			patch("frappe.db.rollback"),
			patch("frappe.db.sql"),
			patch("frappe.db.get_value", side_effect=[None, "HR-ADS-26-10-00001"]),
			patch.object(import_doc, "_validate_preview_rows", return_value=[]),
			patch.object(import_doc, "_assert_attendance_complete"),
			patch.object(
				import_doc,
				"_additional_salary_specs",
				return_value=[
					{"employee": "EMP-001", "component": "Overtime", "amount": 50, "overwrite": 0}
				],
			),
			self.assertRaises(frappe.ValidationError),
		):
			import_doc.prepare_variable_earnings()

	def test_reversal_blocks_additional_salary_used_by_any_salary_slip(self):
		import_doc = self.make_import({"name": "HR-PIMP-2026-00001"})
		import_doc.check_permission = Mock()
		with (
			patch(
				"frappe.get_all",
				side_effect=[
					["HR-ADS-26-10-00001"],
					["Sal Slip/00001"],
					["Sal Slip/00001"],
				],
			),
			self.assertRaises(frappe.ValidationError),
		):
			import_doc.reverse_variable_earnings()

	def test_apply_is_idempotent_when_entry_is_linked(self):
		import_doc = self.make_import(
			{"payroll_entry": "HR-PRUN-2026-00001", "cost_center": "Principal - CYCE"}
		)
		import_doc.check_permission = Mock()
		with patch("frappe.has_permission"), patch("frappe.db.sql", return_value=[]):
			self.assertEqual(import_doc.apply_import(), {"payroll_entry": "HR-PRUN-2026-00001"})

	def test_apply_requires_cost_center_even_when_company_has_a_default(self):
		import_doc = self.make_import({"payroll_entry": "HR-PRUN-2026-00001"})
		import_doc.check_permission = Mock()
		with patch("frappe.has_permission"), self.assertRaises(frappe.ValidationError):
			import_doc.apply_import()

	def test_confirmed_attendance_creates_and_submits_only_new_rows(self):
		attendance = Mock(name="attendance")
		import_doc = self.make_import(
			{
				"period_start": "2026-10-01",
				"period_end": "2026-10-01",
				"preview_rows": [{"matched_employee": "EMP-001", "match_status": "Matched"}],
			}
		)
		import_doc.check_permission = Mock()
		with (
			patch("frappe.has_permission"),
			patch("frappe.db.savepoint"),
			patch("frappe.db.sql"),
			patch("frappe.db.exists", return_value=None),
			patch("frappe.get_doc", return_value=attendance),
			patch.object(import_doc, "_allowed_attendance_dates", return_value={frappe.utils.getdate("2026-10-01")}),
			patch.object(import_doc, "sync_attendance_preview", return_value={"summaries": [], "updated": True}),
		):
			result = import_doc.apply_attendance_matrix(
				[{"employee": "EMP-001", "attendance_date": "2026-10-01", "status": "Present"}]
			)
		attendance.insert.assert_called_once()
		attendance.submit.assert_called_once()
		self.assertEqual(result["count"], 1)

	def test_existing_attendance_is_not_overwritten(self):
		import_doc = self.make_import(
			{
				"period_start": "2026-10-01",
				"period_end": "2026-10-01",
				"preview_rows": [{"matched_employee": "EMP-001", "match_status": "Matched"}],
			}
		)
		import_doc.check_permission = Mock()
		with (
			patch("frappe.has_permission"),
			patch("frappe.db.savepoint"),
			patch("frappe.db.sql"),
			patch("frappe.db.rollback"),
			patch("frappe.db.exists", return_value="HR-ATT-00001"),
			patch.object(import_doc, "_allowed_attendance_dates", return_value={frappe.utils.getdate("2026-10-01")}),
			self.assertRaises(frappe.ValidationError),
		):
			import_doc.apply_attendance_matrix(
				[{"employee": "EMP-001", "attendance_date": "2026-10-01", "status": "Present"}]
			)

	def test_attendance_confirmation_locks_employees_in_order_before_checking_attendance(self):
		attendance = Mock(name="attendance")
		import_doc = self.make_import(
			{
				"period_start": "2026-10-01",
				"period_end": "2026-10-01",
				"preview_rows": [
					{"matched_employee": "EMP-001", "match_status": "Matched"},
					{"matched_employee": "EMP-002", "match_status": "Matched"},
				],
			}
		)
		import_doc.check_permission = Mock()
		call_order = []

		def lock_employee(_query, employee):
			call_order.append(("lock", employee))

		def attendance_exists(_doctype, filters):
			call_order.append(("exists", filters["employee"]))
			return None

		with (
			patch("frappe.has_permission"),
			patch("frappe.db.savepoint"),
			patch("frappe.db.sql", side_effect=lock_employee) as row_locks,
			patch("frappe.db.exists", side_effect=attendance_exists),
			patch("frappe.get_doc", return_value=attendance),
			patch.object(import_doc, "_allowed_attendance_dates", return_value={frappe.utils.getdate("2026-10-01")}),
			patch.object(import_doc, "sync_attendance_preview", return_value={"summaries": [], "updated": True}),
		):
			import_doc.apply_attendance_matrix(
				[
					{"employee": "EMP-002", "attendance_date": "2026-10-01", "status": "Present"},
					{"employee": "EMP-001", "attendance_date": "2026-10-01", "status": "Present"},
				]
			)

		self.assertEqual([call.args[1] for call in row_locks.call_args_list], ["EMP-001", "EMP-002"])
		self.assertEqual(call_order[:2], [("lock", "EMP-001"), ("lock", "EMP-002")])
		self.assertEqual(call_order[2:], [("exists", "EMP-002"), ("exists", "EMP-001")])

	def test_sync_attendance_preview_persists_confirmed_attendance_values(self):
		import_doc = self.make_import(
			{
				"preview_rows": [
					{
						"matched_employee": "EMP-001",
						"daily_rate": 100,
						"days_worked": 15,
						"attendance_days": 0,
						"estimated_basic_amount": 0,
					}
				],
			}
		)
		import_doc.check_permission = Mock()
		import_doc.save = Mock()
		with patch.object(
			import_doc,
			"get_attendance_matrix",
			return_value={
				"rows": [],
				"summaries": [
					{"employee": "EMP-001", "attendance_days": 10.5, "estimated_basic_amount": 1050}
				],
			},
		):
			result = import_doc.sync_attendance_preview()

		self.assertTrue(result["updated"])
		self.assertEqual(import_doc.preview_rows[0].attendance_days, 10.5)
		self.assertEqual(import_doc.preview_rows[0].estimated_basic_amount, 1050)
		self.assertEqual(import_doc.preview_rows[0].days_worked, 10.5)
		import_doc.save.assert_called_once()

	def test_attendance_confirmation_refreshes_existing_attendance_without_creating_rows(self):
		import_doc = self.make_import({"preview_rows": [{"matched_employee": "EMP-001"}]})
		import_doc.check_permission = Mock()
		with (
			patch("frappe.db.savepoint"),
			patch("frappe.db.sql") as row_locks,
			patch("frappe.has_permission") as attendance_permissions,
			patch.object(
				import_doc,
				"sync_attendance_preview",
				return_value={"summaries": [{"employee": "EMP-001"}], "updated": True},
			) as sync_preview,
		):
			result = import_doc.apply_attendance_matrix([])

		sync_preview.assert_called_once()
		row_locks.assert_not_called()
		attendance_permissions.assert_not_called()
		self.assertEqual(result["count"], 0)
		self.assertTrue(result["updated"])
