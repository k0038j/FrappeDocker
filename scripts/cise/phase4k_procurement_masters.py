"""Create the approved CISE procurement master-data foundation."""

from __future__ import annotations

import json

import frappe


COMPANY = "CYCE, S.A."
ABBR = "CISE"

SUPPLIER_GROUPS = (
    ("Materiales de Construcción", "All Supplier Groups", 0),
    ("Ferretería y Herramientas", "All Supplier Groups", 0),
    ("Maquinaria y Equipos", "All Supplier Groups", 1),
    ("Venta de Maquinaria", "Maquinaria y Equipos", 0),
    ("Alquiler de Maquinaria", "Maquinaria y Equipos", 0),
    ("Servicios Técnicos y Profesionales", "All Supplier Groups", 0),
    ("Transporte y Logística", "All Supplier Groups", 0),
    ("Combustibles y Lubricantes", "All Supplier Groups", 0),
)

ITEM_GROUP_RENAME = ("Maquinaria", "Activos de Maquinaria y Transporte")
ITEM_GROUPS = (
    ("Materiales de Construcción", "All Item Groups", 1),
    ("Cementos y Aglomerantes", "Materiales de Construcción", 0),
    ("Acero y Refuerzo", "Materiales de Construcción", 0),
    ("Agregados", "Materiales de Construcción", 0),
    ("Mampostería", "Materiales de Construcción", 0),
    ("Madera y Encofrado", "Materiales de Construcción", 0),
    ("Tuberías y Accesorios", "Materiales de Construcción", 0),
    ("Material Eléctrico", "Materiales de Construcción", 0),
    ("Pinturas y Acabados", "Materiales de Construcción", 0),
    ("Ferretería y Fijaciones", "Materiales de Construcción", 0),
    ("Seguridad y EPP", "Materiales de Construcción", 0),
    ("Herramientas y Equipos Menores", "All Item Groups", 1),
    ("Herramientas Manuales", "Herramientas y Equipos Menores", 0),
    ("Herramientas Eléctricas", "Herramientas y Equipos Menores", 0),
    ("Equipos Menores", "Herramientas y Equipos Menores", 0),
    ("Repuestos y Consumibles de Maquinaria", "All Item Groups", 0),
    ("Servicios de Obra", "All Item Groups", 1),
    ("Alquiler de Maquinaria", "Servicios de Obra", 0),
    ("Transporte", "Servicios de Obra", 0),
    ("Servicios Técnicos", "Servicios de Obra", 0),
    ("Activos de Maquinaria y Transporte", "All Item Groups", 1),
    ("Vehículos", "Activos de Maquinaria y Transporte", 0),
    ("Maquinaria Pesada", "Activos de Maquinaria y Transporte", 0),
    ("Equipos Menores Capitalizables", "Activos de Maquinaria y Transporte", 0),
)

UOMS = ("Saco", "Rollo", "Lámina", "Viaje", "Cubeta")

WAREHOUSES = (
    "Bodega Central de Materiales",
    "Bodega de Obra Estación Nueva Distrito 3",
    "Almacén de Herramientas",
    "Patio de Maquinaria y Equipos",
)

COST_CENTERS = (
    ("Operaciones", "CISE - CISE", 1),
    ("Construcción Estación Nueva Distrito 3", "Operaciones - CISE", 0),
    ("Consultoría Estudio de Suelos", "Operaciones - CISE", 0),
)

PROJECT_COST_CENTERS = {
    "Estación Nueva Distrito 3": "Construcción Estación Nueva Distrito 3 - CISE",
    "Estudio de Suelos - Estación Nueva Distrito 3": (
        "Consultoría Estudio de Suelos - CISE"
    ),
}


def _ensure_supplier_group(name: str, parent: str, is_group: int) -> str:
    if frappe.db.exists("Supplier Group", name):
        doc = frappe.get_doc("Supplier Group", name)
        if doc.parent_supplier_group != parent or int(doc.is_group) != is_group:
            frappe.throw(f"El grupo de proveedores {name} tiene otra estructura.")
        return "existing"

    frappe.get_doc(
        {
            "doctype": "Supplier Group",
            "supplier_group_name": name,
            "parent_supplier_group": parent,
            "is_group": is_group,
        }
    ).insert(ignore_permissions=True)
    return "created"


def _normalize_asset_item_group() -> str:
    old_name, new_name = ITEM_GROUP_RENAME
    old_exists = frappe.db.exists("Item Group", old_name)
    new_exists = frappe.db.exists("Item Group", new_name)

    if old_exists and new_exists:
        frappe.throw(
            f"Existen simultáneamente los grupos {old_name} y {new_name}; "
            "no se modificó ninguno."
        )

    status = "existing"
    if old_exists:
        item_references = frappe.get_all("Item", filters={"item_group": old_name})
        child_groups = frappe.get_all(
            "Item Group", filters={"parent_item_group": old_name}
        )
        if item_references or child_groups:
            frappe.throw(
                f"El grupo {old_name} ya tiene referencias y no puede reutilizarse."
            )
        frappe.rename_doc("Item Group", old_name, new_name)
        status = "renamed"
    elif not new_exists:
        frappe.get_doc(
            {
                "doctype": "Item Group",
                "item_group_name": new_name,
                "parent_item_group": "All Item Groups",
                "is_group": 1,
            }
        ).insert(ignore_permissions=True)
        return "created"

    doc = frappe.get_doc("Item Group", new_name)
    changed = False
    if doc.item_group_name != new_name:
        doc.item_group_name = new_name
        changed = True
    if doc.parent_item_group != "All Item Groups":
        doc.parent_item_group = "All Item Groups"
        changed = True
    if not doc.is_group:
        doc.is_group = 1
        changed = True
    if changed:
        doc.save(ignore_permissions=True)
        if status == "existing":
            status = "updated"
    return status


def _ensure_item_group(name: str, parent: str, is_group: int) -> str:
    if frappe.db.exists("Item Group", name):
        doc = frappe.get_doc("Item Group", name)
        if doc.parent_item_group != parent or int(doc.is_group) != is_group:
            frappe.throw(f"El grupo de artículos {name} tiene otra estructura.")
        return "existing"

    frappe.get_doc(
        {
            "doctype": "Item Group",
            "item_group_name": name,
            "parent_item_group": parent,
            "is_group": is_group,
        }
    ).insert(ignore_permissions=True)
    return "created"


def _ensure_uom(name: str) -> str:
    if frappe.db.exists("UOM", name):
        doc = frappe.get_doc("UOM", name)
        if not doc.enabled or not doc.must_be_whole_number:
            frappe.throw(f"La unidad {name} existe con una configuración distinta.")
        return "existing"

    frappe.get_doc(
        {
            "doctype": "UOM",
            "uom_name": name,
            "enabled": 1,
            "must_be_whole_number": 1,
        }
    ).insert(ignore_permissions=True)
    return "created"


def _ensure_warehouse(warehouse_name: str) -> str:
    full_name = f"{warehouse_name} - {ABBR}"
    if frappe.db.exists("Warehouse", full_name):
        doc = frappe.get_doc("Warehouse", full_name)
        expected = {
            "warehouse_name": warehouse_name,
            "parent_warehouse": "Todos los almacenes - CISE",
            "company": COMPANY,
            "is_group": 0,
            "disabled": 0,
        }
        if any(doc.get(key) != value for key, value in expected.items()):
            frappe.throw(f"El almacén {full_name} tiene otra configuración.")
        return "existing"

    frappe.get_doc(
        {
            "doctype": "Warehouse",
            "warehouse_name": warehouse_name,
            "parent_warehouse": "Todos los almacenes - CISE",
            "company": COMPANY,
            "is_group": 0,
            "disabled": 0,
        }
    ).insert(ignore_permissions=True)
    return "created"


def _ensure_cost_center(name: str, parent: str, is_group: int) -> str:
    full_name = f"{name} - {ABBR}"
    if frappe.db.exists("Cost Center", full_name):
        doc = frappe.get_doc("Cost Center", full_name)
        expected = {
            "cost_center_name": name,
            "parent_cost_center": parent,
            "company": COMPANY,
            "is_group": is_group,
            "disabled": 0,
        }
        if any(doc.get(key) != value for key, value in expected.items()):
            frappe.throw(f"El centro de costo {full_name} tiene otra configuración.")
        return "existing"

    frappe.get_doc(
        {
            "doctype": "Cost Center",
            "cost_center_name": name,
            "parent_cost_center": parent,
            "company": COMPANY,
            "is_group": is_group,
            "disabled": 0,
        }
    ).insert(ignore_permissions=True)
    return "created"


def _link_project_cost_center(project_name: str, cost_center: str) -> dict:
    project_ids = frappe.get_all(
        "Project", filters={"project_name": project_name}, pluck="name"
    )
    if len(project_ids) != 1:
        frappe.throw(
            f"Se esperaba un proyecto llamado {project_name!r}; "
            f"se encontraron {len(project_ids)}."
        )

    project = frappe.get_doc("Project", project_ids[0])
    if project.company != COMPANY:
        frappe.throw(f"El proyecto {project.name} pertenece a otra empresa.")
    if project.cost_center == cost_center:
        return {"project": project.name, "cost_center": cost_center, "status": "existing"}
    if project.cost_center:
        frappe.throw(
            f"El proyecto {project.name} ya usa el centro {project.cost_center}."
        )

    project.cost_center = cost_center
    project.save(ignore_permissions=True)
    return {"project": project.name, "cost_center": cost_center, "status": "updated"}


def configure() -> dict:
    if not frappe.db.exists("Company", COMPANY):
        frappe.throw(f"No existe la empresa {COMPANY}.")

    result = {
        "supplier_groups": {},
        "item_groups": {},
        "uoms": {},
        "warehouses": {},
        "cost_centers": {},
        "projects": [],
    }

    for name, parent, is_group in SUPPLIER_GROUPS:
        result["supplier_groups"][name] = _ensure_supplier_group(
            name, parent, is_group
        )

    result["item_groups"][ITEM_GROUP_RENAME[1]] = _normalize_asset_item_group()
    for name, parent, is_group in ITEM_GROUPS:
        if name == ITEM_GROUP_RENAME[1]:
            continue
        result["item_groups"][name] = _ensure_item_group(name, parent, is_group)

    for name in UOMS:
        result["uoms"][name] = _ensure_uom(name)

    for name in WAREHOUSES:
        result["warehouses"][name] = _ensure_warehouse(name)

    for name, parent, is_group in COST_CENTERS:
        result["cost_centers"][name] = _ensure_cost_center(name, parent, is_group)

    for project_name, cost_center in PROJECT_COST_CENTERS.items():
        result["projects"].append(
            _link_project_cost_center(project_name, cost_center)
        )

    frappe.db.commit()
    return result


def execute() -> dict:
    """Entry point for ``bench --site <site> execute``."""
    try:
        result = configure()
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return result
    except Exception:
        frappe.db.rollback()
        raise
