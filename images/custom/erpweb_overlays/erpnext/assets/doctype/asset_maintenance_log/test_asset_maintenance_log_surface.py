# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# See license.txt

import json
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from erpnext.assets.doctype.asset_maintenance_log import asset_maintenance_log as log_module


class TestAssetMaintenanceLogSurface(TestCase):
	def test_maintenance_task_links_show_the_friendly_title_but_keep_row_ids(self):
		task_definition = json.loads(
			(Path(__file__).parent.parent / "asset_maintenance_task" / "asset_maintenance_task.json").read_text(
				encoding="utf-8"
			)
		)
		log_definition = json.loads(
			(Path(__file__).parent / "asset_maintenance_log.json").read_text(encoding="utf-8")
		)
		log_fields = {field["fieldname"]: field for field in log_definition["fields"]}

		self.assertEqual(task_definition["title_field"], "maintenance_task")
		self.assertEqual(task_definition["show_title_field_in_link"], 1)
		self.assertEqual(log_fields["task"]["options"], "Asset Maintenance Task")

	def test_manual_log_requires_parent_and_task(self):
		definition = json.loads(
			(Path(__file__).parent / "asset_maintenance_log.json").read_text(encoding="utf-8")
		)
		fields = {field["fieldname"]: field for field in definition["fields"]}
		self.assertEqual(fields["asset_maintenance"].get("reqd"), 1)
		self.assertEqual(fields["task"].get("reqd"), 1)

	def test_task_query_returns_child_name_and_visible_description(self):
		source = (Path(__file__).parent / "asset_maintenance_log.py").read_text(encoding="utf-8")
		self.assertIn('["name", "maintenance_task"]', source)
		self.assertIn('"parenttype": "Asset Maintenance"', source)

	def test_log_form_groups_fields_into_balanced_labeled_sections(self):
		definition = json.loads(
			(Path(__file__).parent / "asset_maintenance_log.json").read_text(encoding="utf-8")
		)
		fields = {field["fieldname"]: field for field in definition["fields"]}
		field_order = definition["field_order"]

		for fieldname, label in {
			"asset_details_section": "Asset Details",
			"section_break_5": "Maintenance Details",
			"status_and_assignment_section": "Maintenance Status",
			"usage_hours_monitoring_section": "Usage Hours Monitoring",
			"results_and_actions_section": "Actions performed",
		}.items():
			self.assertEqual(fields[fieldname]["label"], label)
			self.assertEqual(fields[fieldname]["fieldtype"], "Section Break")

		for before, after in (
			("section_break_5", "status_and_assignment_section"),
			("status_and_assignment_section", "usage_hours_monitoring_section"),
			("usage_hours_monitoring_section", "results_and_actions_section"),
		):
			self.assertLess(field_order.index(before), field_order.index(after))

		self.assertEqual(fields["status_and_assignment_column_break"]["fieldtype"], "Column Break")
		self.assertEqual(fields["usage_hours_monitoring_column_break"]["fieldtype"], "Column Break")

	def test_form_fetches_task_snapshot_instead_of_leaving_zero_values(self):
		source = (Path(__file__).parent / "asset_maintenance_log.js").read_text(encoding="utf-8")
		for expected in (
			"get_maintenance_task_details",
			'"due_usage_hours"',
			'"current_usage_hours"',
			'"remaining_usage_hours"',
			'"excess_usage_hours"',
		):
			self.assertIn(expected, source)

	def test_server_snapshot_copies_usage_values_from_selected_task(self):
		doc = SimpleNamespace(task="TASK-ROW-1", asset_maintenance="ACC-ASS-0001")
		task = SimpleNamespace(
			parent="ACC-ASS-0001",
			maintenance_task="Cambio de aceite",
			maintenance_type="Preventive Maintenance",
			periodicity="",
			certificate_required=0,
			assign_to_name="Augusto García",
			assign_to="augusto.garcia@cise.com",
			description="Proceso de mantenimiento",
			maintenance_basis="Usage Hours",
			next_due_date=None,
			next_due_usage_hours=256,
			current_usage_hours=206,
			remaining_usage_hours=50,
			excess_usage_hours=0,
			alert_usage_date="2026-10-07",
			alert_usage_time="2026-10-07 13:44:31",
			alert_usage_log="ACC-AUL-2026-00003",
		)
		frappe_mock = MagicMock()
		frappe_mock.get_doc.return_value = task

		with patch.object(log_module, "frappe", frappe_mock):
			log_module.AssetMaintenanceLog.set_maintenance_task_snapshot(doc)

		self.assertEqual(doc.task_name, "Cambio de aceite")
		self.assertEqual(doc.due_usage_hours, 256)
		self.assertEqual(doc.current_usage_hours, 206)
		self.assertEqual(doc.remaining_usage_hours, 50)
		self.assertEqual(doc.excess_usage_hours, 0)
