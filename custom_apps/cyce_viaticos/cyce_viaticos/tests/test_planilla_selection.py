import json
import unittest
from pathlib import Path

from frappe import _dict

from cyce_viaticos.cyce_viaticos.doctype.planilla_viatico.planilla_viatico import (
	_as_employee_list,
	_is_blank_employee_row,
)


class PlanillaEmployeeSelectionTest(unittest.TestCase):
	def test_planilla_uses_standard_name_as_title(self):
		meta_path = (
			Path(__file__).resolve().parents[1]
			/ "cyce_viaticos"
			/ "doctype"
			/ "planilla_viatico"
			/ "planilla_viatico.json"
		)
		meta = json.loads(meta_path.read_text(encoding="utf-8"))
		self.assertNotIn("title_field", meta)

	def test_employee_selection_removes_duplicates_without_losing_order(self):
		self.assertEqual(
			_as_employee_list(["HR-EMP-00033", "HR-EMP-00015", "HR-EMP-00033"]),
			["HR-EMP-00033", "HR-EMP-00015"],
		)

	def test_empty_grid_row_is_detected(self):
		self.assertTrue(
			_is_blank_employee_row(
				_dict(empleado=None, monto_diario=0, destino=" ", proyecto=None, total_estimado=0)
			)
		)

	def test_incomplete_grid_row_is_not_silently_removed(self):
		self.assertFalse(_is_blank_employee_row(_dict(empleado=None, destino="Comida")))


if __name__ == "__main__":
	unittest.main()
