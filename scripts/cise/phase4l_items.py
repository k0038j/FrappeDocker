"""Create and validate the approved CISE construction-item catalogue."""

from __future__ import annotations

import json

import frappe


COMPANY = "CYCE, S.A."
OLD_CEMENT_CODE = "987654321"
NEW_CEMENT_CODE = "MAT-CEM-001"
MATERIAL_WAREHOUSE = "Bodega de Obra Estación Nueva Distrito 3 - CISE"
TOOLS_WAREHOUSE = "Almacén de Herramientas - CISE"
SERVICE_EXPENSE_ACCOUNT = "Costo de Servicios - CISE"


def _item(code, name, group, uom, warehouse=None, service=False):
    return {
        "item_code": code,
        "item_name": name,
        "item_group": group,
        "stock_uom": uom,
        "purchase_uom": uom,
        "warehouse": warehouse,
        "expense_account": SERVICE_EXPENSE_ACCOUNT if service else None,
        "is_stock_item": 0 if service else 1,
    }


ITEMS = (
    _item(NEW_CEMENT_CODE, "Cemento Portland 42.5 kg", "Cementos y Aglomerantes", "Unit", MATERIAL_WAREHOUSE),
    _item("MAT-AGR-001", "Arena lavada", "Agregados", "Cubic Meter", MATERIAL_WAREHOUSE),
    _item("MAT-AGR-002", 'Grava triturada 3/4"', "Agregados", "Cubic Meter", MATERIAL_WAREHOUSE),
    _item("MAT-AGR-003", "Material selecto", "Agregados", "Cubic Meter", MATERIAL_WAREHOUSE),
    _item("MAT-MAM-001", 'Bloque de concreto 6"', "Mampostería", "Nos", MATERIAL_WAREHOUSE),
    _item("MAT-MAM-002", 'Bloque de concreto 8"', "Mampostería", "Nos", MATERIAL_WAREHOUSE),
    _item("MAT-ACE-001", "Varilla corrugada #3, 6 m", "Acero y Refuerzo", "Unit", MATERIAL_WAREHOUSE),
    _item("MAT-ACE-002", "Varilla corrugada #4, 6 m", "Acero y Refuerzo", "Unit", MATERIAL_WAREHOUSE),
    _item("MAT-ACE-003", "Varilla corrugada #5, 6 m", "Acero y Refuerzo", "Unit", MATERIAL_WAREHOUSE),
    _item("MAT-ACE-004", "Alambre de amarre", "Acero y Refuerzo", "Kg", MATERIAL_WAREHOUSE),
    _item("MAT-ACE-005", "Malla electrosoldada", "Acero y Refuerzo", "Lámina", MATERIAL_WAREHOUSE),
    _item("MAT-ENC-001", "Plywood 4×8 pies, 18 mm", "Madera y Encofrado", "Lámina", MATERIAL_WAREHOUSE),
    _item("MAT-ENC-002", "Madera de pino 2×4 pulgadas", "Madera y Encofrado", "Unit", MATERIAL_WAREHOUSE),
    _item("MAT-FER-001", "Clavo corriente 2½ pulgadas", "Ferretería y Fijaciones", "Kg", MATERIAL_WAREHOUSE),
    _item("MAT-FER-002", "Tornillo y anclaje para concreto", "Ferretería y Fijaciones", "Box", MATERIAL_WAREHOUSE),
    _item("MAT-TUB-001", 'Tubería PVC 2", 6 m', "Tuberías y Accesorios", "Unit", MATERIAL_WAREHOUSE),
    _item("MAT-TUB-002", 'Tubería PVC 4", 6 m', "Tuberías y Accesorios", "Unit", MATERIAL_WAREHOUSE),
    _item("MAT-TUB-003", 'Codo PVC 2"', "Tuberías y Accesorios", "Unit", MATERIAL_WAREHOUSE),
    _item("MAT-ELE-001", "Cable THHN #12", "Material Eléctrico", "Rollo", MATERIAL_WAREHOUSE),
    _item("MAT-ELE-002", 'Conduit PVC ½", 3 m', "Material Eléctrico", "Unit", MATERIAL_WAREHOUSE),
    _item("MAT-PIN-001", "Pintura acrílica para exterior", "Pinturas y Acabados", "Cubeta", MATERIAL_WAREHOUSE),
    _item("MAT-PIN-002", "Sellador y primer", "Pinturas y Acabados", "Cubeta", MATERIAL_WAREHOUSE),
    _item("MAT-PIN-003", "Diluyente para pintura", "Pinturas y Acabados", "Litre", MATERIAL_WAREHOUSE),
    _item("MAT-CON-001", "Disco de corte para metal", "Repuestos y Consumibles de Maquinaria", "Unit", MATERIAL_WAREHOUSE),
    _item("MAT-CON-002", "Electrodo para soldadura", "Repuestos y Consumibles de Maquinaria", "Kg", MATERIAL_WAREHOUSE),
    _item("EPP-001", "Casco de seguridad", "Seguridad y EPP", "Unit", MATERIAL_WAREHOUSE),
    _item("EPP-002", "Chaleco reflectivo", "Seguridad y EPP", "Unit", MATERIAL_WAREHOUSE),
    _item("EPP-003", "Guantes de cuero", "Seguridad y EPP", "Pair", MATERIAL_WAREHOUSE),
    _item("EPP-004", "Botas de seguridad", "Seguridad y EPP", "Pair", MATERIAL_WAREHOUSE),
    _item("EPP-005", "Gafas de protección", "Seguridad y EPP", "Unit", MATERIAL_WAREHOUSE),
    _item("EPP-006", "Arnés para trabajo en altura", "Seguridad y EPP", "Unit", MATERIAL_WAREHOUSE),
    _item("HER-MAN-001", "Pala cuadrada", "Herramientas Manuales", "Unit", TOOLS_WAREHOUSE),
    _item("HER-MAN-002", "Pico para excavación", "Herramientas Manuales", "Unit", TOOLS_WAREHOUSE),
    _item("HER-MAN-003", "Carretilla de construcción", "Herramientas Manuales", "Unit", TOOLS_WAREHOUSE),
    _item("HER-MAN-004", "Martillo de uña", "Herramientas Manuales", "Unit", TOOLS_WAREHOUSE),
    _item("HER-MAN-005", "Nivel de aluminio", "Herramientas Manuales", "Unit", TOOLS_WAREHOUSE),
    _item("HER-MAN-006", "Cinta métrica 8 m", "Herramientas Manuales", "Unit", TOOLS_WAREHOUSE),
    _item("HER-MAN-007", "Cuchara de albañil", "Herramientas Manuales", "Unit", TOOLS_WAREHOUSE),
    _item("HER-ELE-001", "Rotomartillo eléctrico", "Herramientas Eléctricas", "Unit", TOOLS_WAREHOUSE),
    _item("HER-ELE-002", "Esmeril angular", "Herramientas Eléctricas", "Unit", TOOLS_WAREHOUSE),
    _item("HER-ELE-003", "Taladro eléctrico", "Herramientas Eléctricas", "Unit", TOOLS_WAREHOUSE),
    _item("HER-ELE-004", "Sierra circular", "Herramientas Eléctricas", "Unit", TOOLS_WAREHOUSE),
    _item("HER-EQM-001", "Vibrador de concreto", "Equipos Menores", "Unit", TOOLS_WAREHOUSE),
    _item("HER-EQM-002", "Extensión eléctrica industrial", "Equipos Menores", "Rollo", TOOLS_WAREHOUSE),
    _item("SRV-ALQ-001", "Alquiler de retroexcavadora", "Alquiler de Maquinaria", "Hour", service=True),
    _item("SRV-ALQ-002", "Alquiler de excavadora", "Alquiler de Maquinaria", "Hour", service=True),
    _item("SRV-ALQ-003", "Alquiler de camión volquete", "Alquiler de Maquinaria", "Day", service=True),
    _item("SRV-TRA-001", "Transporte de agregados", "Transporte", "Viaje", service=True),
    _item("SRV-TEC-001", "Ensayos de laboratorio de suelos", "Servicios Técnicos", "Unit", service=True),
)

LINKED_CHILD_DOCTYPES = (
    "Purchase Order Item",
    "Purchase Invoice Item",
    "Material Request Item",
)


def _validate_prerequisites():
    required = {
        "Company": {COMPANY},
        "Warehouse": {MATERIAL_WAREHOUSE, TOOLS_WAREHOUSE},
        "Account": {SERVICE_EXPENSE_ACCOUNT},
        "Item Group": {row["item_group"] for row in ITEMS},
        "UOM": {row["stock_uom"] for row in ITEMS} | {"Saco"},
    }
    for doctype, names in required.items():
        missing = sorted(name for name in names if not frappe.db.exists(doctype, name))
        if missing:
            frappe.throw(f"Faltan maestros {doctype}: {', '.join(missing)}")

    account = frappe.get_doc("Account", SERVICE_EXPENSE_ACCOUNT)
    if account.company != COMPANY or account.is_group or account.account_type != "Cost of Goods Sold":
        frappe.throw(f"La cuenta {SERVICE_EXPENSE_ACCOUNT} no es un costo utilizable de {COMPANY}.")


def _historical_snapshot():
    snapshot = {}
    for doctype, name in (
        ("Purchase Order", "PUR-ORD-2026-00001"),
        ("Purchase Invoice", "ACC-PINV-2026-00001"),
        ("Material Request", "MAT-PRE-2026-00001"),
    ):
        if not frappe.db.exists(doctype, name):
            continue
        doc = frappe.get_doc(doctype, name)
        snapshot[f"{doctype}:{name}"] = {
            "docstatus": doc.docstatus,
            "status": doc.get("status"),
            "total": doc.get("total"),
            "grand_total": doc.get("grand_total"),
        }
    return snapshot


def _linked_rows(item_codes):
    rows = []
    for doctype in LINKED_CHILD_DOCTYPES:
        rows.extend(
            {
                "doctype": doctype,
                **row,
            }
            for row in frappe.get_all(
                doctype,
                filters={"item_code": ["in", list(item_codes)]},
                fields=["name", "parent", "item_code", "qty", "rate", "amount"],
                order_by="parent asc, idx asc",
            )
        )
    return rows


def _assert_no_stock_ledger(item_codes):
    count = frappe.db.count("Stock Ledger Entry", {"item_code": ["in", list(item_codes)]})
    if count:
        frappe.throw("El cemento histórico ya tiene movimientos de inventario; no se renombró.")


def _normalize_cement():
    old_exists = frappe.db.exists("Item", OLD_CEMENT_CODE)
    new_exists = frappe.db.exists("Item", NEW_CEMENT_CODE)
    if old_exists and new_exists:
        frappe.throw(f"Existen simultáneamente {OLD_CEMENT_CODE} y {NEW_CEMENT_CODE}.")

    status = "existing"
    if old_exists:
        doc = frappe.get_doc("Item", OLD_CEMENT_CODE)
        expected = {
            "item_name": "Bolsa de Cemento",
            "item_group": "Products",
            "stock_uom": "Unit",
            "is_stock_item": 1,
            "is_fixed_asset": 0,
        }
        if any(doc.get(field) != value for field, value in expected.items()):
            frappe.throw(f"El artículo {OLD_CEMENT_CODE} no coincide con el registro histórico auditado.")
        _assert_no_stock_ledger({OLD_CEMENT_CODE, NEW_CEMENT_CODE})
        frappe.rename_doc("Item", OLD_CEMENT_CODE, NEW_CEMENT_CODE)
        status = "renamed"
    elif not new_exists:
        frappe.throw(f"No existe el cemento histórico {OLD_CEMENT_CODE} ni su código nuevo.")

    doc = frappe.get_doc("Item", NEW_CEMENT_CODE)
    doc.item_name = "Cemento Portland 42.5 kg"
    doc.item_group = "Cementos y Aglomerantes"
    doc.stock_uom = "Unit"
    doc.purchase_uom = "Saco"
    doc.description = "Cemento Portland de uso general, presentación de 42.5 kg."
    doc.disabled = 0
    doc.is_stock_item = 1
    doc.is_fixed_asset = 0
    doc.is_purchase_item = 1
    doc.is_sales_item = 0
    doc.include_item_in_manufacturing = 0
    doc.has_batch_no = 0
    doc.has_serial_no = 0
    _ensure_uom_conversion(doc, "Unit", 1)
    _ensure_uom_conversion(doc, "Saco", 1)
    _ensure_item_default(doc, MATERIAL_WAREHOUSE, None)
    doc.save(ignore_permissions=True)
    return status


def _ensure_uom_conversion(doc, uom, factor):
    matches = [row for row in doc.uoms if row.uom == uom]
    if len(matches) > 1:
        frappe.throw(f"{doc.name} tiene duplicada la conversión {uom}.")
    if matches:
        if float(matches[0].conversion_factor) != float(factor):
            frappe.throw(f"{doc.name} tiene una conversión inesperada para {uom}.")
        return
    doc.append("uoms", {"uom": uom, "conversion_factor": factor})


def _ensure_item_default(doc, warehouse, expense_account):
    matches = [row for row in doc.item_defaults if row.company == COMPANY]
    if len(matches) > 1:
        frappe.throw(f"{doc.name} tiene múltiples valores predeterminados para {COMPANY}.")
    row = matches[0] if matches else doc.append("item_defaults", {"company": COMPANY})
    row.default_warehouse = warehouse
    row.expense_account = expense_account


def _new_item(spec):
    doc = frappe.get_doc(
        {
            "doctype": "Item",
            "item_code": spec["item_code"],
            "item_name": spec["item_name"],
            "description": spec["item_name"],
            "item_group": spec["item_group"],
            "stock_uom": spec["stock_uom"],
            "purchase_uom": spec["purchase_uom"],
            "disabled": 0,
            "is_stock_item": spec["is_stock_item"],
            "is_fixed_asset": 0,
            "is_purchase_item": 1,
            "is_sales_item": 0,
            "include_item_in_manufacturing": 0,
            "has_batch_no": 0,
            "has_serial_no": 0,
        }
    )
    _ensure_uom_conversion(doc, spec["stock_uom"], 1)
    _ensure_item_default(doc, spec["warehouse"], spec["expense_account"])
    doc.insert(ignore_permissions=True)


def _validate_item(spec):
    doc = frappe.get_doc("Item", spec["item_code"])
    expected = {
        "item_name": spec["item_name"],
        "item_group": spec["item_group"],
        "stock_uom": spec["stock_uom"],
        "purchase_uom": "Saco" if spec["item_code"] == NEW_CEMENT_CODE else spec["purchase_uom"],
        "disabled": 0,
        "is_stock_item": spec["is_stock_item"],
        "is_fixed_asset": 0,
        "is_purchase_item": 1,
        "is_sales_item": 0,
        "include_item_in_manufacturing": 0,
        "has_batch_no": 0,
        "has_serial_no": 0,
    }
    differences = {
        field: {"expected": value, "actual": doc.get(field)}
        for field, value in expected.items()
        if doc.get(field) != value
    }
    if differences:
        frappe.throw(f"Configuración inesperada en {doc.name}: {json.dumps(differences, ensure_ascii=False)}")

    defaults = [row for row in doc.item_defaults if row.company == COMPANY]
    if len(defaults) != 1:
        frappe.throw(f"{doc.name} no tiene un único valor predeterminado para {COMPANY}.")
    default = defaults[0]
    if default.default_warehouse != spec["warehouse"] or default.expense_account != spec["expense_account"]:
        frappe.throw(f"Valores predeterminados incorrectos en {doc.name}.")

    required_uoms = {spec["stock_uom"]}
    if spec["item_code"] == NEW_CEMENT_CODE:
        required_uoms.add("Saco")
    conversions = {row.uom: float(row.conversion_factor) for row in doc.uoms}
    if any(conversions.get(uom) != 1.0 for uom in required_uoms):
        frappe.throw(f"Conversiones de UOM incorrectas en {doc.name}.")


def configure():
    if len(ITEMS) != 49 or sum(row["is_stock_item"] for row in ITEMS) != 44:
        frappe.throw("El catálogo interno no contiene 49 artículos (44 físicos y 5 servicios).")
    if len({row["item_code"] for row in ITEMS}) != len(ITEMS):
        frappe.throw("El catálogo interno contiene códigos duplicados.")

    _validate_prerequisites()
    history_before = _historical_snapshot()
    links_before = _linked_rows({OLD_CEMENT_CODE, NEW_CEMENT_CODE})
    cement_status = _normalize_cement()

    result = {"renamed": {}, "created": [], "existing": []}
    result["renamed"][OLD_CEMENT_CODE] = {
        "new_code": NEW_CEMENT_CODE,
        "status": cement_status,
    }

    for spec in ITEMS:
        if spec["item_code"] == NEW_CEMENT_CODE:
            continue
        if frappe.db.exists("Item", spec["item_code"]):
            _validate_item(spec)
            result["existing"].append(spec["item_code"])
        else:
            _new_item(spec)
            result["created"].append(spec["item_code"])

    for spec in ITEMS:
        _validate_item(spec)

    _assert_no_stock_ledger({OLD_CEMENT_CODE, NEW_CEMENT_CODE})
    if frappe.db.exists("Item", OLD_CEMENT_CODE):
        frappe.throw(f"El código anterior {OLD_CEMENT_CODE} todavía existe.")
    if _historical_snapshot() != history_before:
        frappe.throw("Cambió el estado o importe de un documento histórico.")

    links_after = _linked_rows({OLD_CEMENT_CODE, NEW_CEMENT_CODE})
    if len(links_after) != len(links_before):
        frappe.throw("Cambió la cantidad de filas históricas vinculadas al cemento.")
    if any(row["item_code"] != NEW_CEMENT_CODE for row in links_after):
        frappe.throw("Quedaron vínculos históricos con el código anterior del cemento.")

    frappe.db.commit()
    frappe.clear_cache()
    result["counts"] = {
        "catalogue": len(ITEMS),
        "stock_items": sum(row["is_stock_item"] for row in ITEMS),
        "services": sum(not row["is_stock_item"] for row in ITEMS),
        "historical_links": len(links_after),
        "stock_ledger_entries_for_cement": 0,
    }
    result["historical_documents"] = history_before
    result["historical_links"] = links_after
    return result


def execute():
    """Entry point for ``bench --site <site> execute``."""
    try:
        result = configure()
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return result
    except Exception:
        frappe.db.rollback()
        raise
