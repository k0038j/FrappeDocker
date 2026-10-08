"""Targeted deployment repair for existing, personalized Desk layouts."""

import json

import frappe
from frappe import _


def add_viaticos_to_saved_desktops():
	"""Add the standard root icon without replacing users' other shortcuts."""
	frappe.only_for("System Manager")
	desktop_icon = frappe.get_doc("Desktop Icon", "Viáticos")
	icon = {
		key: desktop_icon.get(key)
		for key in (
			"name", "label", "icon", "icon_type", "link_type", "link_to", "app",
			"parent_icon", "hidden", "standard", "logo_url", "bg_color", "restrict_removal",
		)
	}
	icon.update(parent_icon="", hidden=0)
	changed = []
	for saved in frappe.get_all("Desktop Layout", fields=["name", "user", "layout"]):
		if not frappe.has_permission("Viatico", "read", user=saved.user):
			continue
		layout = json.loads(saved.layout or "[]")
		if not isinstance(layout, list):
			frappe.throw(_("El diseño de escritorio {0} no es válido.").format(saved.name))
		before = json.dumps(layout)
		existing = next(
			(item for item in layout if item.get("name") == "Viáticos" or item.get("label") == "Viáticos"),
			None,
		)
		if existing is None:
			layout.append(dict(icon, idx=max((item.get("idx") or 0 for item in layout), default=0) + 1))
		else:
			for key in ("parent_icon", "hidden", "link_to", "link_type", "icon", "app"):
				existing[key] = icon[key]
		if json.dumps(layout) != before:
			doc = frappe.get_doc("Desktop Layout", saved.name)
			doc.layout = json.dumps(layout)
			doc.save()
			changed.append(saved.name)
		frappe.cache.hdel("desktop_icons", saved.user)
		frappe.cache.hdel("bootinfo", saved.user)
	return changed
