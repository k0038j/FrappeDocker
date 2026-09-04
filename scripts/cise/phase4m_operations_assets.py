"""Create the approved CISE suppliers, stock, purchase orders and assets."""

from __future__ import annotations

import json
from collections import Counter

import frappe
from frappe.utils import flt


COMPANY = "CYCE, S.A."
PROJECT = "PROJ-0001"
COST_CENTER = "Construcción Estación Nueva Distrito 3 - CYCE"
DEPARTMENT = "Maquinaria y Equipos - CYCE"
MATERIAL_WAREHOUSE = "Bodega de Obra Estación Nueva Distrito 3 - CYCE"
TOOLS_WAREHOUSE = "Almacén de Herramientas - CYCE"
STOCK_ACCOUNT = "1134 - Otros inventarios - CYCE"
STOCK_ADJUSTMENT_ACCOUNT = "511098 - Ajuste de Inventarios - CYCE"
GOODS_EXPENSE_ACCOUNT = "4410 - Costo de Ventas por Prestacion de servicios - CYCE"
SERVICE_EXPENSE_ACCOUNT = "4410 - Costo de Ventas por Prestacion de servicios - CYCE"
ACCUMULATED_DEPRECIATION_OTHER = "1390 - Otros Activos fijos - CYCE"
DEPRECIATION_EXPENSE_OTHER = "511086 - Otros activos fijos - CYCE"
TAX_TEMPLATE = "Nicaragua Tax - CYCE"
OPENING_STOCK_REMARK = "CISE-DEMO-STOCK-OPENING-2026"


SUPPLIERS = (
    ("Cemento Canal", "Materiales de Construcción"),
    ("Aceros y Mallas de Nicaragua", "Materiales de Construcción"),
    ("Agregados San Cristóbal", "Materiales de Construcción"),
    ("Ferretería El Constructor", "Ferretería y Herramientas"),
    ("Distribuidora Eléctrica y Acabados", "Materiales de Construcción"),
    ("Renta y Maquinaria del Pacífico", "Alquiler de Maquinaria"),
    ("GeoLab Nicaragua", "Servicios Técnicos y Profesionales"),
    ("Transportes y Volquetes del Sur", "Transporte y Logística"),
)


# item_code, quantity, valuation rate, target warehouse
OPENING_STOCK = (
    ("MAT-CEM-001", 120, 500, MATERIAL_WAREHOUSE),
    ("MAT-AGR-001", 80, 700, MATERIAL_WAREHOUSE),
    ("MAT-AGR-002", 60, 1000, MATERIAL_WAREHOUSE),
    ("MAT-AGR-003", 100, 550, MATERIAL_WAREHOUSE),
    ("MAT-MAM-001", 2000, 32, MATERIAL_WAREHOUSE),
    ("MAT-MAM-002", 1200, 45, MATERIAL_WAREHOUSE),
    ("MAT-ACE-001", 600, 250, MATERIAL_WAREHOUSE),
    ("MAT-ACE-002", 400, 400, MATERIAL_WAREHOUSE),
    ("MAT-ACE-003", 150, 650, MATERIAL_WAREHOUSE),
    ("MAT-ACE-004", 100, 70, MATERIAL_WAREHOUSE),
    ("MAT-ACE-005", 80, 1100, MATERIAL_WAREHOUSE),
    ("MAT-ENC-001", 100, 1400, MATERIAL_WAREHOUSE),
    ("MAT-ENC-002", 300, 350, MATERIAL_WAREHOUSE),
    ("MAT-FER-001", 100, 60, MATERIAL_WAREHOUSE),
    ("MAT-FER-002", 50, 500, MATERIAL_WAREHOUSE),
    ("MAT-TUB-001", 150, 400, MATERIAL_WAREHOUSE),
    ("MAT-TUB-002", 100, 1000, MATERIAL_WAREHOUSE),
    ("MAT-TUB-003", 100, 150, MATERIAL_WAREHOUSE),
    ("MAT-ELE-001", 30, 5000, MATERIAL_WAREHOUSE),
    ("MAT-ELE-002", 200, 80, MATERIAL_WAREHOUSE),
    ("MAT-PIN-001", 40, 3500, MATERIAL_WAREHOUSE),
    ("MAT-PIN-002", 20, 3000, MATERIAL_WAREHOUSE),
    ("MAT-PIN-003", 80, 160, MATERIAL_WAREHOUSE),
    ("MAT-CON-001", 150, 150, MATERIAL_WAREHOUSE),
    ("MAT-CON-002", 100, 100, MATERIAL_WAREHOUSE),
    ("EPP-001", 50, 400, MATERIAL_WAREHOUSE),
    ("EPP-002", 50, 250, MATERIAL_WAREHOUSE),
    ("EPP-003", 60, 150, MATERIAL_WAREHOUSE),
    ("EPP-004", 40, 1800, MATERIAL_WAREHOUSE),
    ("EPP-005", 50, 180, MATERIAL_WAREHOUSE),
    ("EPP-006", 10, 2500, MATERIAL_WAREHOUSE),
    ("HER-MAN-001", 20, 1000, TOOLS_WAREHOUSE),
    ("HER-MAN-002", 15, 900, TOOLS_WAREHOUSE),
    ("HER-MAN-003", 15, 3000, TOOLS_WAREHOUSE),
    ("HER-MAN-004", 30, 500, TOOLS_WAREHOUSE),
    ("HER-MAN-005", 20, 700, TOOLS_WAREHOUSE),
    ("HER-MAN-006", 25, 350, TOOLS_WAREHOUSE),
    ("HER-MAN-007", 25, 200, TOOLS_WAREHOUSE),
    ("HER-ELE-001", 5, 8000, TOOLS_WAREHOUSE),
    ("HER-ELE-002", 8, 4500, TOOLS_WAREHOUSE),
    ("HER-ELE-003", 8, 5000, TOOLS_WAREHOUSE),
    ("HER-ELE-004", 5, 7500, TOOLS_WAREHOUSE),
    ("HER-EQM-001", 4, 28000, TOOLS_WAREHOUSE),
    ("HER-EQM-002", 12, 5000, TOOLS_WAREHOUSE),
)


# reference, supplier, transaction date, delivery date, submit, items
PURCHASE_ORDERS = (
    (
        "CISE-DEMO-OC-002",
        "Aceros y Mallas de Nicaragua",
        "2026-07-05",
        "2026-07-20",
        True,
        (
            ("MAT-ACE-001", 600, 300),
            ("MAT-ACE-002", 450, 500),
            ("MAT-ACE-003", 200, 750),
            ("MAT-ACE-004", 100, 80),
            ("MAT-ACE-005", 80, 1300),
        ),
    ),
    (
        "CISE-DEMO-OC-003",
        "Agregados San Cristóbal",
        "2026-07-12",
        "2026-07-25",
        True,
        (
            ("MAT-AGR-001", 100, 800),
            ("MAT-AGR-002", 100, 1150),
            ("MAT-AGR-003", 200, 650),
        ),
    ),
    (
        "CISE-DEMO-OC-004",
        "Ferretería El Constructor",
        "2026-07-20",
        "2026-08-05",
        True,
        (
            ("MAT-ENC-001", 100, 1600),
            ("MAT-ENC-002", 300, 400),
            ("MAT-FER-002", 30, 900),
            ("EPP-001", 50, 450),
            ("EPP-004", 40, 1950),
            ("HER-ELE-001", 4, 8500),
            ("HER-EQM-001", 2, 30000),
        ),
    ),
    (
        "CISE-DEMO-OC-005",
        "Distribuidora Eléctrica y Acabados",
        "2026-08-05",
        "2026-08-20",
        True,
        (
            ("MAT-ELE-001", 40, 6500),
            ("MAT-ELE-002", 300, 120),
            ("MAT-PIN-001", 60, 4500),
            ("MAT-PIN-002", 30, 4000),
            ("MAT-PIN-003", 100, 200),
        ),
    ),
    (
        "CISE-DEMO-OC-006",
        "Renta y Maquinaria del Pacífico",
        "2026-08-15",
        "2026-09-15",
        False,
        (
            ("SRV-ALQ-001", 160, 2800),
            ("SRV-ALQ-002", 120, 4500),
            ("SRV-ALQ-003", 30, 10000),
            ("SRV-TRA-001", 50, 4500),
        ),
    ),
)


ASSET_ACCOUNT_TYPES = {
    "1260 - Maquinaria - CYCE": "Fixed Asset",
    "1240 - Equipo Transporte - CYCE": "Fixed Asset",
    ACCUMULATED_DEPRECIATION_OTHER: "Accumulated Depreciation",
}
ASSET_CATEGORIES = (
    ("Vehículos y Transporte", "1240 - Equipo Transporte - CYCE", "1340 - Equipo Transporte - CYCE", "511083 - Equipo Rodante - CYCE", 60),
    ("Maquinaria Pesada", "1260 - Maquinaria - CYCE", "1360 - Maquinaria - CYCE", "511085 - Maquinaria - CYCE", 96),
    ("Equipos de Compactación", "1290 - Otros Activos fijos - CYCE", ACCUMULATED_DEPRECIATION_OTHER, DEPRECIATION_EXPENSE_OTHER, 48),
)
ASSET_ITEMS = (
    ("ACT-VEH-001", "Camioneta pickup 4x4", "Vehículos", "Vehículos y Transporte"),
    ("ACT-MAQ-001", "Retroexcavadora", "Maquinaria Pesada", "Maquinaria Pesada"),
    ("ACT-MAQ-002", "Camión volquete", "Maquinaria Pesada", "Maquinaria Pesada"),
    ("ACT-MAQ-003", "Excavadora hidráulica", "Maquinaria Pesada", "Maquinaria Pesada"),
    ("ACT-EQM-001", "Compactadora tipo brincolina", "Equipos Menores Capitalizables", "Equipos de Compactación"),
)


# asset name, item, purchase date, available date, cost, opening depreciation,
# booked periods, location
ASSETS = (
    ("Camioneta Toyota Hilux 4x4", "ACT-VEH-001", "2025-01-15", "2025-01-20", 1250000, 375000, 20, "Obra Estación Nueva Distrito 3"),
    ("Camioneta Nissan Frontier 4x4", "ACT-VEH-001", "2024-06-10", "2024-06-15", 1100000, 429000, 26, "Patio de Maquinaria y Equipos"),
    ("Retroexcavadora JCB 3CX", "ACT-MAQ-001", "2023-03-20", "2023-03-25", 3950000, 1518281.25, 41, "Obra Estación Nueva Distrito 3"),
    ("Camión volquete 12 m³", "ACT-MAQ-002", "2022-11-05", "2022-11-12", 3300000, 1423125, 46, "Obra Estación Nueva Distrito 3"),
    ("Excavadora hidráulica CAT 320", "ACT-MAQ-003", "2021-08-12", "2021-08-20", 5800000, 3316875, 61, "Obra Estación Nueva Distrito 3"),
    ("Compactadora brincolina #1", "ACT-EQM-001", "2025-05-15", "2025-05-20", 165000, 49500, 16, "Obra Estación Nueva Distrito 3"),
    ("Compactadora brincolina #2", "ACT-EQM-001", "2025-05-15", "2025-05-20", 165000, 49500, 16, "Patio de Maquinaria y Equipos"),
)


def _validate_prerequisites():
    required = {
        "Company": {COMPANY},
        "Project": {PROJECT},
        "Cost Center": {COST_CENTER},
        "Department": {DEPARTMENT},
        "Warehouse": {MATERIAL_WAREHOUSE, TOOLS_WAREHOUSE},
        "Account": {
            STOCK_ACCOUNT,
            STOCK_ADJUSTMENT_ACCOUNT,
            GOODS_EXPENSE_ACCOUNT,
            SERVICE_EXPENSE_ACCOUNT,
            "1240 - Equipo Transporte - CYCE",
            "1260 - Maquinaria - CYCE",
            "1290 - Otros Activos fijos - CYCE",
            "1340 - Equipo Transporte - CYCE",
            "1360 - Maquinaria - CYCE",
            ACCUMULATED_DEPRECIATION_OTHER,
            "511083 - Equipo Rodante - CYCE",
            "511085 - Maquinaria - CYCE",
            DEPRECIATION_EXPENSE_OTHER,
        },
        "Purchase Taxes and Charges Template": {TAX_TEMPLATE},
        "Tax Category": {"IVA"},
    }
    for doctype, names in required.items():
        missing = sorted(name for name in names if not frappe.db.exists(doctype, name))
        if missing:
            frappe.throw(f"Faltan maestros {doctype}: {', '.join(missing)}")

    if len(OPENING_STOCK) != 44 or len({row[0] for row in OPENING_STOCK}) != 44:
        frappe.throw("El inventario inicial debe contener los 44 artículos físicos sin duplicados.")
    for code, *_rest in OPENING_STOCK:
        if not frappe.db.exists("Item", code) or not frappe.db.get_value("Item", code, "is_stock_item"):
            frappe.throw(f"{code} no es un artículo de inventario válido.")


def _ensure_supplier(name, group):
    if frappe.db.exists("Supplier", name):
        doc = frappe.get_doc("Supplier", name)
        if doc.supplier_name != name or doc.supplier_type != "Company":
            frappe.throw(f"El proveedor {name} tiene otra identidad o tipo.")
        if doc.supplier_group not in (None, "", group):
            frappe.throw(f"El proveedor {name} ya pertenece a {doc.supplier_group}.")
        if doc.supplier_group != group:
            doc.supplier_group = group
            doc.save(ignore_permissions=True)
            return "updated"
        return "existing"

    frappe.get_doc(
        {
            "doctype": "Supplier",
            "supplier_name": name,
            "supplier_group": group,
            "supplier_type": "Company",
            "country": "Nicaragua",
            "disabled": 0,
        }
    ).insert(ignore_permissions=True)
    return "created"


def _ensure_account(account_name, parent, account_type):
    full_name = f"{account_name} - CYCE"
    if frappe.db.exists("Account", full_name):
        doc = frappe.get_doc("Account", full_name)
        expected = {
            "company": COMPANY,
            "parent_account": parent,
            "is_group": 0,
            "root_type": "Asset",
            "account_type": account_type,
        }
        if any(doc.get(field) != value for field, value in expected.items()):
            frappe.throw(f"La cuenta {full_name} existe con otra configuración.")
        return "existing"

    doc = frappe.get_doc(
        {
            "doctype": "Account",
            "account_name": account_name,
            "company": COMPANY,
            "parent_account": parent,
            "is_group": 0,
            "root_type": "Asset",
            "report_type": "Balance Sheet",
            "account_currency": "NIO",
            "account_type": account_type,
        }
    ).insert(ignore_permissions=True)
    if doc.name != full_name:
        frappe.throw(f"La cuenta se creó como {doc.name}, no como {full_name}.")
    return "created"


def _normalize_asset_account(name, expected_type):
    doc = frappe.get_doc("Account", name)
    if doc.company != COMPANY or doc.is_group or doc.root_type != "Asset":
        frappe.throw(f"La cuenta {name} no es una cuenta de activo utilizable.")
    if doc.account_type == expected_type:
        return "existing"
    if doc.account_type not in (None, "", "Depreciation"):
        frappe.throw(f"La cuenta {name} tiene el tipo inesperado {doc.account_type}.")
    if frappe.db.count("GL Entry", {"account": name, "is_cancelled": 0}):
        frappe.throw(f"La cuenta {name} tiene movimientos; no se cambió su tipo.")
    doc.account_type = expected_type
    doc.save(ignore_permissions=True)
    return "updated"


def _configure_inventory_account():
    account = frappe.get_doc("Account", STOCK_ACCOUNT)
    if account.company != COMPANY or account.is_group or account.account_type != "Stock":
        frappe.throw(f"La cuenta {STOCK_ACCOUNT} no es una cuenta de inventario utilizable.")
    status = "existing"
    company = frappe.get_doc("Company", COMPANY)
    if company.default_inventory_account not in (None, "", STOCK_ACCOUNT):
        frappe.throw(f"La empresa ya usa otra cuenta de inventario: {company.default_inventory_account}.")
    if company.default_inventory_account != STOCK_ACCOUNT:
        company.default_inventory_account = STOCK_ACCOUNT
        company.save(ignore_permissions=True)
        status = f"{status}; company-updated"
    return status


def _ensure_asset_category(name, fixed_asset_account, accumulated_depreciation_account, depreciation_expense_account, periods):
    if frappe.db.exists("Asset Category", name):
        doc = frappe.get_doc("Asset Category", name)
        accounts = [row for row in doc.accounts if row.company_name == COMPANY]
        books = list(doc.finance_books)
        if (
            len(accounts) != 1
            or accounts[0].fixed_asset_account != fixed_asset_account
            or accounts[0].accumulated_depreciation_account != accumulated_depreciation_account
            or accounts[0].depreciation_expense_account != depreciation_expense_account
            or len(books) != 1
            or books[0].depreciation_method != "Straight Line"
            or books[0].total_number_of_depreciations != periods
            or books[0].frequency_of_depreciation != 1
            or flt(books[0].salvage_value_percentage) != 10
        ):
            frappe.throw(f"La categoría de activo {name} tiene otra configuración.")
        return "existing"

    frappe.get_doc(
        {
            "doctype": "Asset Category",
            "asset_category_name": name,
            "enable_cwip_accounting": 0,
            "non_depreciable_category": 0,
            "accounts": [
                {
                    "company_name": COMPANY,
                    "fixed_asset_account": fixed_asset_account,
                    "accumulated_depreciation_account": accumulated_depreciation_account,
                    "depreciation_expense_account": depreciation_expense_account,
                }
            ],
            "finance_books": [
                {
                    "depreciation_method": "Straight Line",
                    "total_number_of_depreciations": periods,
                    "frequency_of_depreciation": 1,
                    "salvage_value_percentage": 10,
                }
            ],
        }
    ).insert(ignore_permissions=True)
    return "created"


def _ensure_asset_item(code, name, group, category):
    expected = {
        "item_name": name,
        "item_group": group,
        "stock_uom": "Unit",
        "is_stock_item": 0,
        "is_fixed_asset": 1,
        "asset_category": category,
        "disabled": 0,
    }
    if frappe.db.exists("Item", code):
        doc = frappe.get_doc("Item", code)
        if any(doc.get(field) != value for field, value in expected.items()):
            frappe.throw(f"El artículo de activo {code} tiene otra configuración.")
        return "existing"

    frappe.get_doc(
        {
            "doctype": "Item",
            "item_code": code,
            **expected,
            "purchase_uom": "Unit",
            "is_purchase_item": 1,
            "is_sales_item": 0,
            "auto_create_assets": 0,
            "include_item_in_manufacturing": 0,
            "description": name,
            "uoms": [{"uom": "Unit", "conversion_factor": 1}],
        }
    ).insert(ignore_permissions=True)
    return "created"


def _ensure_location(name, parent=None, is_group=0):
    if frappe.db.exists("Location", name):
        doc = frappe.get_doc("Location", name)
        if doc.parent_location != parent or int(doc.is_group) != is_group:
            frappe.throw(f"La ubicación {name} tiene otra estructura.")
        return "existing"
    frappe.get_doc(
        {
            "doctype": "Location",
            "location_name": name,
            "parent_location": parent,
            "is_group": is_group,
        }
    ).insert(ignore_permissions=True)
    return "created"


def _opening_stock_item(code, qty, rate, warehouse):
    stock_uom = frappe.db.get_value("Item", code, "stock_uom")
    return {
        "item_code": code,
        "qty": qty,
        "uom": stock_uom,
        "stock_uom": stock_uom,
        "conversion_factor": 1,
        "basic_rate": rate,
        "t_warehouse": warehouse,
        "expense_account": STOCK_ADJUSTMENT_ACCOUNT,
        "cost_center": COST_CENTER,
        "project": PROJECT,
    }


def _ensure_opening_stock():
    existing = frappe.get_all(
        "Stock Entry",
        filters={"remarks": OPENING_STOCK_REMARK, "docstatus": ["!=", 2]},
        pluck="name",
    )
    if len(existing) > 1:
        frappe.throw("Existe más de una entrada de inventario inicial CISE.")
    if existing:
        doc = frappe.get_doc("Stock Entry", existing[0])
        expected = {code: (flt(qty), flt(rate), warehouse) for code, qty, rate, warehouse in OPENING_STOCK}
        actual = {row.item_code: (flt(row.qty), flt(row.basic_rate), row.t_warehouse) for row in doc.items}
        if doc.docstatus != 1 or doc.purpose != "Material Receipt" or actual != expected:
            frappe.throw(f"La entrada {doc.name} no coincide con el inventario inicial aprobado.")
        return {"name": doc.name, "status": "existing", "total": doc.total_amount}

    doc = frappe.get_doc(
        {
            "doctype": "Stock Entry",
            "company": COMPANY,
            "purpose": "Material Receipt",
            "stock_entry_type": "Material Receipt",
            "posting_date": "2026-07-01",
            "posting_time": "08:00:00",
            "remarks": OPENING_STOCK_REMARK,
            "items": [
                _opening_stock_item(code, qty, rate, warehouse)
                for code, qty, rate, warehouse in OPENING_STOCK
            ],
        }
    )
    doc.set_missing_values()
    doc.insert(ignore_permissions=True)
    doc.submit()
    return {"name": doc.name, "status": "created", "total": doc.total_amount}


def _purchase_item(code, qty, rate, schedule_date):
    is_stock = frappe.db.get_value("Item", code, "is_stock_item")
    return {
        "item_code": code,
        "qty": qty,
        "rate": rate,
        "schedule_date": schedule_date,
        "warehouse": MATERIAL_WAREHOUSE if is_stock else None,
        "expense_account": GOODS_EXPENSE_ACCOUNT if is_stock else SERVICE_EXPENSE_ACCOUNT,
        "project": PROJECT,
        "cost_center": COST_CENTER,
    }


def _validate_purchase_order(doc, spec):
    reference, supplier, transaction_date, schedule_date, submit, items = spec
    if (
        doc.order_confirmation_no != reference
        or doc.supplier != supplier
        or str(doc.transaction_date) != transaction_date
        or str(doc.schedule_date) != schedule_date
        or doc.project != PROJECT
        or doc.docstatus != (1 if submit else 0)
    ):
        frappe.throw(f"La orden {doc.name} no coincide con {reference}.")
    expected = Counter((code, flt(qty), flt(rate)) for code, qty, rate in items)
    actual = Counter((row.item_code, flt(row.qty), flt(row.rate)) for row in doc.items)
    if actual != expected or any(row.project != PROJECT or row.cost_center != COST_CENTER for row in doc.items):
        frappe.throw(f"Las líneas de {doc.name} no coinciden con la propuesta aprobada.")


def _ensure_purchase_order(spec):
    reference, supplier, transaction_date, schedule_date, submit, items = spec
    existing = frappe.get_all(
        "Purchase Order",
        filters={"order_confirmation_no": reference, "docstatus": ["!=", 2]},
        pluck="name",
    )
    if len(existing) > 1:
        frappe.throw(f"Existe más de una orden con referencia {reference}.")
    if existing:
        doc = frappe.get_doc("Purchase Order", existing[0])
        _validate_purchase_order(doc, spec)
        return {"name": doc.name, "reference": reference, "status": "existing", "docstatus": doc.docstatus, "grand_total": doc.grand_total}

    doc = frappe.get_doc(
        {
            "doctype": "Purchase Order",
            "naming_series": "PUR-ORD-.YYYY.-",
            "supplier": supplier,
            "company": COMPANY,
            "transaction_date": transaction_date,
            "schedule_date": schedule_date,
            "order_confirmation_no": reference,
            "order_confirmation_date": transaction_date,
            "project": PROJECT,
            "currency": "NIO",
            "conversion_rate": 1,
            "buying_price_list": "Standard Buying",
            "price_list_currency": "NIO",
            "plc_conversion_rate": 1,
            "tax_category": "IVA",
            "taxes_and_charges": TAX_TEMPLATE,
            "items": [_purchase_item(code, qty, rate, schedule_date) for code, qty, rate in items],
        }
    )
    doc.flags.ignore_permissions = True
    doc.set_missing_values()
    for tax in doc.taxes:
        tax.cost_center = COST_CENTER
        tax.project = PROJECT
    doc.insert(ignore_permissions=True)
    if submit:
        doc.submit()
    _validate_purchase_order(doc, spec)
    return {"name": doc.name, "reference": reference, "status": "created", "docstatus": doc.docstatus, "grand_total": doc.grand_total}


def _ensure_asset(spec):
    name, item_code, purchase_date, available_date, cost, opening_depr, booked, location = spec
    existing = frappe.get_all(
        "Asset",
        filters={"asset_name": name, "docstatus": ["!=", 2]},
        pluck="name",
    )
    if len(existing) > 1:
        frappe.throw(f"Existe más de un activo llamado {name}.")
    if existing:
        doc = frappe.get_doc("Asset", existing[0])
        expected = {
            "item_code": item_code,
            "company": COMPANY,
            "location": location,
            "cost_center": COST_CENTER,
            "department": DEPARTMENT,
            "purchase_date": purchase_date,
            "available_for_use_date": available_date,
            "asset_type": "Existing Asset",
            "calculate_depreciation": 1,
            "docstatus": 1,
        }
        if any(str(doc.get(field)) != str(value) for field, value in expected.items()):
            frappe.throw(f"El activo {name} tiene otra configuración.")
        if flt(doc.net_purchase_amount) != flt(cost) or flt(doc.opening_accumulated_depreciation) != flt(opening_depr):
            frappe.throw(f"Los valores del activo {name} no coinciden.")
        return {"name": doc.name, "asset_name": name, "status": "existing", "value": doc.total_asset_cost}

    doc = frappe.get_doc(
        {
            "doctype": "Asset",
            "naming_series": "ACC-ASS-.YYYY.-",
            "asset_name": name,
            "item_code": item_code,
            "asset_owner": "Company",
            "company": COMPANY,
            "location": location,
            "cost_center": COST_CENTER,
            "department": DEPARTMENT,
            "purchase_date": purchase_date,
            "available_for_use_date": available_date,
            "asset_type": "Existing Asset",
            "asset_quantity": 1,
            "net_purchase_amount": cost,
            "calculate_depreciation": 1,
            "opening_accumulated_depreciation": opening_depr,
            "opening_number_of_booked_depreciations": booked,
            "maintenance_required": 1,
        }
    )
    doc.set_missing_values()
    doc.insert(ignore_permissions=True)
    doc.submit()
    return {"name": doc.name, "asset_name": name, "status": "created", "value": doc.total_asset_cost}


def configure():
    _validate_prerequisites()
    result = {
        "suppliers": {},
        "accounts": {},
        "asset_categories": {},
        "asset_items": {},
        "locations": {},
        "purchase_orders": [],
        "assets": [],
    }

    for name, group in SUPPLIERS:
        result["suppliers"][name] = _ensure_supplier(name, group)

    result["accounts"][STOCK_ACCOUNT] = _configure_inventory_account()
    for name, account_type in ASSET_ACCOUNT_TYPES.items():
        result["accounts"][name] = _normalize_asset_account(name, account_type)
    for name, account, accumulated, expense, periods in ASSET_CATEGORIES:
        result["asset_categories"][name] = _ensure_asset_category(name, account, accumulated, expense, periods)
    for code, name, group, category in ASSET_ITEMS:
        result["asset_items"][code] = _ensure_asset_item(code, name, group, category)

    result["locations"]["CISE"] = _ensure_location("CISE", is_group=1)
    for location in ("Patio de Maquinaria y Equipos", "Obra Estación Nueva Distrito 3"):
        result["locations"][location] = _ensure_location(location, "CISE", 0)

    result["opening_stock"] = _ensure_opening_stock()
    result["purchase_orders"] = [_ensure_purchase_order(spec) for spec in PURCHASE_ORDERS]
    result["assets"] = [_ensure_asset(spec) for spec in ASSETS]

    frappe.db.commit()
    frappe.clear_cache()
    result["counts"] = {
        "suppliers": len(SUPPLIERS),
        "opening_stock_lines": len(OPENING_STOCK),
        "purchase_orders": len(PURCHASE_ORDERS),
        "submitted_purchase_orders": sum(spec[4] for spec in PURCHASE_ORDERS),
        "draft_purchase_orders": sum(not spec[4] for spec in PURCHASE_ORDERS),
        "asset_categories": len(ASSET_CATEGORIES),
        "asset_items": len(ASSET_ITEMS),
        "assets": len(ASSETS),
    }
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
