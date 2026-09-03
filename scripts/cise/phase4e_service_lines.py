"""Create CISE consulting service lines and link them to Project.

Copy temporarily into an installed app and run through ``bench execute`` so
Frappe initializes the site context. The operation is idempotent and refuses
to overwrite an incompatible existing customization.
"""

from __future__ import annotations

import json

import frappe


SERVICE_LINE_DOCTYPE = "CISE Service Line"
SERVICE_LINE_LABEL = "Línea de Servicio"
PROJECT_CUSTOM_FIELD = "Project-custom_linea_de_servicio"
SERVICE_LINES = (
    "Diseños",
    "Topografía",
    "Asistencia Técnica",
    "Estudios de Suelos",
    "Supervisión de Obra",
)

PERMISSION_FIELDS = (
    "permlevel",
    "read",
    "write",
    "create",
    "delete",
    "submit",
    "cancel",
    "amend",
    "report",
    "export",
    "import",
    "share",
    "print",
    "email",
    "select",
    "if_owner",
)


def _permission(role: str, *, maintain: bool) -> dict:
    permission = {
        "role": role,
        "permlevel": 0,
        "read": 1,
        "write": 0,
        "create": 0,
        "delete": 0,
        "submit": 0,
        "cancel": 0,
        "amend": 0,
        "report": 0,
        "export": 0,
        "import": 0,
        "share": 0,
        "print": 0,
        "email": 0,
        "select": 1,
        "if_owner": 0,
    }
    if maintain:
        permission.update(
            {
                "write": 1,
                "create": 1,
                "delete": 1,
                "report": 1,
                "export": 1,
                "share": 1,
                "print": 1,
                "email": 1,
            }
        )
    return permission


def _permissions_definition() -> list[dict]:
    return [
        _permission("System Manager", maintain=True),
        _permission("Projects Manager", maintain=True),
        _permission("Projects User", maintain=False),
    ]


def _doctype_definition() -> dict:
    return {
        "doctype": "DocType",
        "name": SERVICE_LINE_DOCTYPE,
        "module": "Projects",
        "custom": 1,
        "autoname": "field:service_line_name",
        "title_field": "service_line_name",
        "search_fields": "service_line_name",
        "allow_rename": 1,
        "track_changes": 1,
        "sort_field": "service_line_name",
        "sort_order": "ASC",
        "fields": [
            {
                "fieldname": "service_line_name",
                "label": SERVICE_LINE_LABEL,
                "fieldtype": "Data",
                "reqd": 1,
                "unique": 1,
                "in_list_view": 1,
                "in_standard_filter": 1,
            },
            {
                "fieldname": "disabled",
                "label": "Deshabilitada",
                "fieldtype": "Check",
                "default": "0",
                "in_list_view": 1,
                "in_standard_filter": 1,
            },
            {
                "fieldname": "description",
                "label": "Descripción",
                "fieldtype": "Small Text",
            },
        ],
        "permissions": _permissions_definition(),
    }


def _custom_field_definition() -> dict:
    return {
        "doctype": "Custom Field",
        "dt": "Project",
        "fieldname": "custom_linea_de_servicio",
        "label": SERVICE_LINE_LABEL,
        "fieldtype": "Link",
        "options": SERVICE_LINE_DOCTYPE,
        "insert_after": "project_type",
        "description": (
            "Servicio de consultoría asociado al proyecto; es independiente "
            "del Tipo de proyecto."
        ),
        "in_standard_filter": 1,
    }


def _validate_preconditions() -> None:
    required_roles = ("System Manager", "Projects Manager", "Projects User")
    missing_roles = [
        role for role in required_roles if not frappe.db.exists("Role", role)
    ]
    if missing_roles:
        frappe.throw(f"No existen los roles requeridos: {', '.join(missing_roles)}")

    if frappe.db.exists("DocType", SERVICE_LINE_DOCTYPE):
        current = frappe.get_doc("DocType", SERVICE_LINE_DOCTYPE)
        if not current.custom:
            frappe.throw(
                f"{SERVICE_LINE_DOCTYPE} ya existe y no es un DocType personalizado."
            )
        expected_fields = {
            "service_line_name": "Data",
            "disabled": "Check",
            "description": "Small Text",
        }
        current_fields = {field.fieldname: field.fieldtype for field in current.fields}
        if any(
            current_fields.get(fieldname) != fieldtype
            for fieldname, fieldtype in expected_fields.items()
        ):
            frappe.throw(
                f"{SERVICE_LINE_DOCTYPE} existe con una estructura incompatible."
            )

    if frappe.db.exists("Custom Field", PROJECT_CUSTOM_FIELD):
        current = frappe.get_doc("Custom Field", PROJECT_CUSTOM_FIELD)
        expected = _custom_field_definition()
        protected_properties = ("dt", "fieldname", "fieldtype", "options")
        if any(current.get(key) != expected[key] for key in protected_properties):
            frappe.throw(
                f"{PROJECT_CUSTOM_FIELD} existe con una definición incompatible."
            )

    translations = frappe.get_all(
        "Translation",
        filters={"language": "es", "source_text": SERVICE_LINE_DOCTYPE},
        fields=["name", "translated_text"],
    )
    if any(row.translated_text != SERVICE_LINE_LABEL for row in translations):
        frappe.throw(
            f"Ya existe una traducción incompatible para {SERVICE_LINE_DOCTYPE}."
        )


def _synchronize_permissions(doctype_doc) -> bool:
    changed = False
    current_by_role = {row.role: row for row in doctype_doc.permissions}
    for expected in _permissions_definition():
        current = current_by_role.get(expected["role"])
        if current is None:
            doctype_doc.append("permissions", expected)
            changed = True
            continue
        for fieldname in PERMISSION_FIELDS:
            expected_value = expected[fieldname]
            if current.get(fieldname) != expected_value:
                current.set(fieldname, expected_value)
                changed = True
    return changed


def apply() -> dict:
    _validate_preconditions()
    result = {
        "doctype": "existing",
        "custom_field": "existing",
        "permissions": "existing",
        "translation": "existing",
        "lines": {},
    }

    if not frappe.db.exists("DocType", SERVICE_LINE_DOCTYPE):
        doctype_doc = frappe.get_doc(_doctype_definition())
        doctype_doc.insert(ignore_permissions=True)
        result["doctype"] = "created"
        result["permissions"] = "created"
    else:
        doctype_doc = frappe.get_doc("DocType", SERVICE_LINE_DOCTYPE)
        if _synchronize_permissions(doctype_doc):
            doctype_doc.save(ignore_permissions=True)
            result["permissions"] = "updated"

    if not frappe.db.exists("Custom Field", PROJECT_CUSTOM_FIELD):
        frappe.get_doc(_custom_field_definition()).insert(ignore_permissions=True)
        result["custom_field"] = "created"

    if not frappe.db.exists(
        "Translation", {"language": "es", "source_text": SERVICE_LINE_DOCTYPE}
    ):
        frappe.get_doc(
            {
                "doctype": "Translation",
                "language": "es",
                "source_text": SERVICE_LINE_DOCTYPE,
                "translated_text": SERVICE_LINE_LABEL,
            }
        ).insert(ignore_permissions=True)
        result["translation"] = "created"

    for service_line in SERVICE_LINES:
        if frappe.db.exists(SERVICE_LINE_DOCTYPE, service_line):
            result["lines"][service_line] = "existing"
            continue
        frappe.get_doc(
            {
                "doctype": SERVICE_LINE_DOCTYPE,
                "service_line_name": service_line,
                "disabled": 0,
            }
        ).insert(ignore_permissions=True)
        result["lines"][service_line] = "created"

    frappe.db.commit()
    frappe.clear_cache()
    frappe.clear_cache(doctype="Project")
    frappe.clear_cache(doctype=SERVICE_LINE_DOCTYPE)
    return result


def execute() -> dict:
    """Entry point for ``bench --site <site> execute``."""
    try:
        result = apply()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result
    except Exception:
        frappe.db.rollback()
        raise
