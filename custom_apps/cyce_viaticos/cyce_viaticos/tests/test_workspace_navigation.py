import json
import unittest
from pathlib import Path


APP_PACKAGE = Path(__file__).resolve().parents[1]


class ViaticosWorkspaceNavigationTest(unittest.TestCase):
	def load_json(self, *parts):
		return json.loads(APP_PACKAGE.joinpath(*parts).read_text(encoding="utf-8"))

	def test_desktop_icon_is_nested_in_human_resources(self):
		icon = self.load_json("desktop_icon", "viaticos.json")

		self.assertEqual(icon["label"], "Viáticos")
		self.assertEqual(icon["parent_icon"], "Frappe HR")
		self.assertEqual(icon["link_type"], "Workspace Sidebar")
		self.assertEqual(icon["link_to"], "Viáticos")

	def test_workspace_exposes_all_operational_and_report_links(self):
		workspace = self.load_json(
			"cyce_viaticos", "workspace", "viaticos", "viaticos.json"
		)
		links = {
			(row.get("link_type"), row.get("link_to"))
			for row in workspace["links"]
			if row.get("type") == "Link"
		}

		self.assertEqual(
			links,
			{
				("DocType", "Viatico"),
				("DocType", "Planilla Viatico"),
				("DocType", "Plantilla Viatico"),
				("DocType", "Viatico Ajuste"),
				("Report", "Viatico Especifico"),
				("Report", "Listado de Viaticos"),
				("Report", "Detalle de Viaticos"),
			},
		)

	def test_workspace_sidebar_targets_the_same_workspace(self):
		sidebar = self.load_json("workspace_sidebar", "viaticos.json")

		self.assertEqual(sidebar["name"], "Viáticos")
		self.assertEqual(sidebar["items"][0]["link_to"], "Viáticos")


if __name__ == "__main__":
	unittest.main()
