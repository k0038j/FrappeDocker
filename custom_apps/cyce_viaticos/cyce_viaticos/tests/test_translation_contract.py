import csv
import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from cyce_viaticos.cyce_viaticos.report import report_utils


APP_PACKAGE = Path(__file__).resolve().parents[1]
MODULE_PACKAGE = APP_PACKAGE / "cyce_viaticos"
TRANSLATIONS = APP_PACKAGE / "translations"


def load_catalog(language):
	with (TRANSLATIONS / f"{language}.csv").open(encoding="utf-8", newline="") as source:
		rows = list(csv.reader(source))
	assert all(len(row) in (2, 3) for row in rows)
	keys = [row[0] for row in rows]
	assert len(keys) == len(set(keys))
	return {row[0]: row[1] for row in rows}


def iter_json_strings(value):
	if isinstance(value, dict):
		for key, child in value.items():
			if key in {"label", "title", "description"} and isinstance(child, str) and child:
				yield child
			if key == "options" and isinstance(child, str) and "\n" in child:
				yield from filter(None, child.splitlines())
			yield from iter_json_strings(child)
	elif isinstance(value, list):
		for child in value:
			yield from iter_json_strings(child)


class TranslationCatalogTest(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.es = load_catalog("es")
		cls.en = load_catalog("en")

	def test_approved_glossary_is_used(self):
		expected = {
			"Viático": "Per Diem",
			"Planilla de viáticos": "Per Diem Batch",
			"Adelantado": "Advance",
			"Reposición": "Reimbursement",
		}
		for source, translation in expected.items():
			self.assertEqual(self.en[source], translation)
			self.assertEqual(self.es[source], source)

	def test_metadata_and_wrapped_messages_are_in_both_catalogs(self):
		required = set()
		for path in APP_PACKAGE.rglob("*.json"):
			required.update(iter_json_strings(json.loads(path.read_text(encoding="utf-8"))))
		wrapper_pattern = re.compile(r"\b_\(\s*([\"'])(.*?)\1|\b__\(\s*([\"'])(.*?)\3", re.DOTALL)
		for pattern in ("*.py", "*.js", "*.html"):
			for path in APP_PACKAGE.rglob(pattern):
				for match in wrapper_pattern.finditer(path.read_text(encoding="utf-8")):
					required.add(match.group(2) or match.group(4))
		missing_es = sorted(required - self.es.keys())
		missing_en = sorted(required - self.en.keys())
		self.assertEqual(missing_es, [])
		self.assertEqual(missing_en, [])

	def test_stored_values_have_presentation_translations(self):
		stored_values = {
			"Adelantado",
			"Reposición",
			"Borrador",
			"Borradores generados",
			"Pendiente de aprobación",
			"Aprobado",
			"Conciliado",
			"Rechazado",
			"Cancelado",
			"Pendiente",
			"Generado",
			"No requerido",
			"Abierto",
			"Parcialmente aplicado",
			"Aplicado",
			"Presente",
			"Ausente",
			"Medio día",
			"Permiso",
			"Trabajo desde casa",
			"Sin asistencia",
			"Pendiente de conciliación",
		}
		self.assertFalse(stored_values - self.es.keys())
		self.assertFalse(stored_values - self.en.keys())

	def test_protected_select_values_are_unchanged(self):
		viatico = json.loads(
			(MODULE_PACKAGE / "doctype" / "viatico" / "viatico.json").read_text(encoding="utf-8")
		)
		fields = {field["fieldname"]: field for field in viatico["fields"] if "fieldname" in field}
		self.assertEqual(fields["tipo_viatico"]["options"], "Adelantado\nReposición")
		self.assertEqual(
			fields["estado"]["options"],
			"Borrador\nPendiente de aprobación\nAprobado\nRechazado\nConciliado\nCancelado",
		)
		self.assertEqual(
			fields["estado_integracion_contable"]["options"],
			"Pendiente\nGenerado\nNo requerido\nCancelado",
		)

	def test_navigation_targets_and_report_identifiers_are_unchanged(self):
		workspace = json.loads(
			(MODULE_PACKAGE / "workspace" / "viaticos" / "viaticos.json").read_text(
				encoding="utf-8"
			)
		)
		targets = {row.get("link_to") for row in workspace["links"] if row.get("link_to")}
		self.assertTrue(
			{
				"Viatico",
				"Planilla Viatico",
				"Plantilla Viatico",
				"Viatico Ajuste",
				"Viatico Especifico",
				"Listado de Viaticos",
				"Detalle de Viaticos",
			}.issubset(targets)
		)

	def test_technical_identifiers_have_presentation_translations(self):
		expected = {
			"Viatico": "Per Diem",
			"Planilla Viatico": "Per Diem Batch",
			"Plantilla Viatico": "Per Diem Template",
			"Viatico Ajuste": "Per Diem Adjustment",
			"Viatico Especifico": "Specific Per Diem",
			"Listado de Viaticos": "Per Diem List",
			"Detalle de Viaticos": "Per Diem Details",
			"Comprobante de Viatico": "Per Diem Voucher",
		}
		for source, translation in expected.items():
			self.assertEqual(self.en[source], translation)

	def test_spanish_framework_and_getting_started_labels_are_complete(self):
		expected = {
			"Last Edited By You": "Última edición por ti",
			"Last Edited By": "Última edición por",
			"Last Edited By {0}": "Última edición por {0}",
			"Getting Started": "Primeros pasos",
			"Setup Organization": "Configurar organización",
			"Setup Company": "Configurar compañía",
			"Invite Users": "Invitar usuarios",
			"Setup Email Account": "Configurar cuenta de correo electrónico",
			"Setup Role Permissions": "Configurar permisos de roles",
			"Review System Settings": "Revisar configuración del sistema",
		}
		for source, translation in expected.items():
			self.assertEqual(self.es[source], translation)

	def test_print_uses_runtime_language_and_translates_stored_values(self):
		print_dir = MODULE_PACKAGE / "print_format" / "comprobante_de_viatico"
		metadata = json.loads((print_dir / "comprobante_de_viatico.json").read_text(encoding="utf-8"))
		template = (print_dir / "comprobante_de_viatico.html").read_text(encoding="utf-8")
		self.assertNotIn("default_print_language", metadata)
		self.assertIn('{{ _(doc.estado) }}', template)
		self.assertIn('{{ _(doc.tipo_viatico) }}', template)
		self.assertIn('{{ _(row.estado_asistencia or "Pendiente") }}', template)

	def test_reports_translate_only_presentation_values(self):
		for report in ("viatico_especifico", "listado_de_viaticos", "detalle_de_viaticos"):
			script = (
				MODULE_PACKAGE / "report" / report / f"{report}.js"
			).read_text(encoding="utf-8")
			server = (
				MODULE_PACKAGE / "report" / report / f"{report}.py"
			).read_text(encoding="utf-8")
			self.assertIn("formatter(value, row, column, data, default_formatter)", script)
			self.assertIn("default_formatter(__(value), row, column, data)", script)
			self.assertIn("translate_presentation_values(", server)

	def test_report_filters_keep_canonical_values_with_translated_labels(self):
		for report in ("listado_de_viaticos", "detalle_de_viaticos"):
			script = (MODULE_PACKAGE / "report" / report / f"{report}.js").read_text(
				encoding="utf-8"
			)
			self.assertIn('map((value) => ({ value, label: __(value) }))', script)
			self.assertNotIn('options: "\\nAdelantado\\nReposición"', script)

	def test_server_translates_export_values_without_changing_filter_contract(self):
		rows = [
			{
				"tipo_viatico": "Adelantado",
				"estado": "Aprobado",
				"estado_integracion_contable": "Generado",
				"empleado": "HR-EMP-00033",
			}
		]
		translations = {
			"Adelantado": "Advance",
			"Aprobado": "Approved",
			"Generado": "Generated",
		}
		with patch.object(report_utils, "_", side_effect=lambda value: translations.get(value, value)):
			report_utils.translate_presentation_values(
				rows,
				("tipo_viatico", "estado", "estado_integracion_contable"),
			)
		self.assertEqual(rows[0]["tipo_viatico"], "Advance")
		self.assertEqual(rows[0]["estado"], "Approved")
		self.assertEqual(rows[0]["estado_integracion_contable"], "Generated")
		self.assertEqual(rows[0]["empleado"], "HR-EMP-00033")


if __name__ == "__main__":
	unittest.main()
