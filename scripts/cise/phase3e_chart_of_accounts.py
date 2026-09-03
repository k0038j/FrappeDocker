"""Install and validate the approved CYCE chart of accounts.

The script is intentionally idempotent.  It creates numbered CYCE accounts,
moves the previous unnumbered ERPNext chart below clearly marked legacy groups,
and updates operational defaults through the Frappe ORM.  It never rewrites GL
entries or deletes historical accounts.

Copy this module and ``phase3e_chart_of_accounts.json`` next to each other into
an installed app, then execute ``frappe.phase3e_chart_of_accounts.execute``.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import frappe
from frappe.utils import cint, flt


COMPANY = "CYCE, S.A."
ABBR = "CISE"
CATALOG_PATH = Path(__file__).with_name("phase3e_chart_of_accounts.json")

LEGACY_GROUPS = {
    "Asset": "LEGACY ERP - ACTIVOS (NO USAR)",
    "Liability": "LEGACY ERP - PASIVOS (NO USAR)",
    "Equity": "LEGACY ERP - PATRIMONIO (NO USAR)",
    "Income": "LEGACY ERP - INGRESOS (NO USAR)",
    "Expense": "LEGACY ERP - COSTOS Y GASTOS (NO USAR)",
}

COMPANY_DEFAULTS = {
    "default_bank_account": "1121",
    "default_cash_account": "1111",
    "default_receivable_account": "1149",
    "default_payable_account": "2111",
    "default_inventory_account": "1134",
    "stock_adjustment_account": "511098",
    "stock_received_but_not_billed": "2112",
    "default_expense_account": "511097",
    "default_income_account": "4100",
    "purchase_expense_account": "4410",
    "service_expense_account": "4410",
    "default_operating_cost_account": "4410",
    "accumulated_depreciation_account": "1390",
    "depreciation_expense_account": "511086",
}

ASSET_CATEGORY_ACCOUNTS = {
    "Vehículos y Transporte": ("1240", "1340", "511083"),
    "Maquinaria Pesada": ("1260", "1360", "511085"),
    "Equipos de Compactación": ("1290", "1390", "511086"),
}

DEMO_PURCHASE_REFERENCES = (
    "CISE-DEMO-OC-002",
    "CISE-DEMO-OC-003",
    "CISE-DEMO-OC-004",
    "CISE-DEMO-OC-005",
)
HISTORICAL_PURCHASE_ORDER = "PUR-ORD-2026-00001"


def _load_catalog():
    if not CATALOG_PATH.exists():
        frappe.throw(f"No se encontró el catálogo técnico: {CATALOG_PATH}")
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if payload.get("company") != COMPANY or payload.get("abbr") != ABBR:
        frappe.throw("El catálogo técnico no corresponde a CYCE, S.A. / CISE.")
    accounts = payload.get("accounts") or []
    numbers = [row["account_number"] for row in accounts]
    duplicates = sorted(number for number, count in Counter(numbers).items() if count > 1)
    if duplicates:
        frappe.throw(f"El catálogo técnico contiene códigos duplicados: {', '.join(duplicates)}")
    known = set(numbers)
    missing_parents = sorted(
        {row["parent"] for row in accounts if not row["parent"].startswith("ROOT:") and row["parent"] not in known}
    )
    if missing_parents:
        frappe.throw(f"El catálogo referencia padres inexistentes: {', '.join(missing_parents)}")
    return payload


def _roots():
    rows = frappe.get_all(
        "Account",
        filters={"company": COMPANY, "parent_account": ["is", "not set"]},
        fields=["name", "root_type"],
    )
    roots = {row.root_type: row.name for row in rows}
    missing = sorted(set(LEGACY_GROUPS) - set(roots))
    if missing:
        frappe.throw(f"Faltan cuentas raíz de CISE: {', '.join(missing)}")
    return roots


def _account_name(spec):
    return f"{spec['account_number']} - {spec['account_name']} - {ABBR}"


def _accounts_by_number(accounts):
    return {row["account_number"]: _account_name(row) for row in accounts}


def _gl_snapshot():
    entries = frappe.get_all(
        "GL Entry",
        filters={"company": COMPANY, "is_cancelled": 0},
        fields=["debit", "credit"],
        limit_page_length=0,
    )
    return {
        "count": len(entries),
        "debit": flt(sum(flt(row.debit) for row in entries), 2),
        "credit": flt(sum(flt(row.credit) for row in entries), 2),
    }


def _ensure_legacy_group(root_type, root_name):
    title = LEGACY_GROUPS[root_type]
    name = f"{title} - {ABBR}"
    if frappe.db.exists("Account", name):
        doc = frappe.get_doc("Account", name)
        expected = {
            "company": COMPANY,
            "parent_account": root_name,
            "root_type": root_type,
            "is_group": 1,
        }
        if any(doc.get(field) != value for field, value in expected.items()):
            frappe.throw(f"El grupo {name} existe con otra configuración.")
        return name, "existing"

    doc = frappe.get_doc(
        {
            "doctype": "Account",
            "account_name": title,
            "company": COMPANY,
            "parent_account": root_name,
            "is_group": 1,
            "root_type": root_type,
            "account_currency": "NIO",
        }
    ).insert(ignore_permissions=True)
    if doc.name != name:
        frappe.throw(f"El grupo legacy se creó con nombre inesperado: {doc.name}")
    return name, "created"


def _is_numbered(value):
    return bool(str(value or "").strip())


def _move_existing_chart(roots, legacy_names):
    result = []
    for root_type, root_name in roots.items():
        children = frappe.get_all(
            "Account",
            filters={"company": COMPANY, "parent_account": root_name},
            fields=["name", "account_number"],
            order_by="lft asc",
        )
        for row in children:
            if row.name == legacy_names[root_type] or _is_numbered(row.account_number):
                continue
            doc = frappe.get_doc("Account", row.name)
            doc.parent_account = legacy_names[root_type]
            doc.save(ignore_permissions=True)
            result.append(row.name)
    return result


def _resolve_parent(parent, roots, by_number):
    if parent.startswith("ROOT:"):
        return roots[parent.split(":", 1)[1]]
    return by_number[parent]


def _ensure_account(spec, roots, by_number):
    number = spec["account_number"]
    expected_name = _account_name(spec)
    matches = frappe.get_all(
        "Account",
        filters={"company": COMPANY, "account_number": number},
        pluck="name",
        limit_page_length=2,
    )
    if len(matches) > 1:
        frappe.throw(f"Existe más de una cuenta CISE con código {number}.")
    parent = _resolve_parent(spec["parent"], roots, by_number)
    expected = {
        "account_name": spec["account_name"],
        "account_number": number,
        "company": COMPANY,
        "parent_account": parent,
        "is_group": cint(spec["is_group"]),
        "account_type": spec.get("account_type") or "",
    }
    if matches:
        doc = frappe.get_doc("Account", matches[0])
        if doc.name != expected_name or any(doc.get(field) != value for field, value in expected.items()):
            frappe.throw(f"La cuenta {number} existe con otra estructura: {doc.name}")
        return doc.name, "existing"

    doc = frappe.get_doc(
        {
            "doctype": "Account",
            **expected,
            "account_currency": "NIO",
        }
    ).insert(ignore_permissions=True)
    if doc.name != expected_name:
        frappe.throw(f"La cuenta {number} se creó con nombre inesperado: {doc.name}")
    return doc.name, "created"


def _update_company_defaults(by_number):
    doc = frappe.get_doc("Company", COMPANY)
    meta = frappe.get_meta("Company")
    changed = {}
    for field, number in COMPANY_DEFAULTS.items():
        if not meta.has_field(field):
            continue
        target = by_number[number]
        if doc.get(field) != target:
            changed[field] = {"from": doc.get(field), "to": target}
            doc.set(field, target)
    if changed:
        doc.save(ignore_permissions=True)
    return changed


def _update_tax_templates(by_number):
    result = {}
    mappings = {
        "Purchase Taxes and Charges Template": by_number["1440"],
        "Sales Taxes and Charges Template": by_number["2137"],
    }
    for doctype, account in mappings.items():
        updated = []
        for name in frappe.get_all(doctype, filters={"company": COMPANY, "disabled": 0}, pluck="name"):
            doc = frappe.get_doc(doctype, name)
            if any(row.account_head != account for row in doc.taxes):
                for row in doc.taxes:
                    row.account_head = account
                doc.save(ignore_permissions=True)
                updated.append(name)
        result[doctype] = {"account": account, "updated": updated}
    return result


def _update_open_purchase_orders(by_number):
    result = {}
    tax_account = by_number["1440"]
    expense_account = by_number["4410"]
    for name in frappe.get_all(
        "Purchase Order",
        filters={"company": COMPANY, "docstatus": ["!=", 2]},
        pluck="name",
    ):
        doc = frappe.get_doc("Purchase Order", name)
        changes = []
        for row in doc.taxes:
            if row.account_head != tax_account:
                row.account_head = tax_account
                changes.append("tax")
        if doc.docstatus == 0:
            for row in doc.items:
                if row.expense_account != expense_account:
                    row.expense_account = expense_account
                    changes.append("expense")
        if changes:
            doc.save(ignore_permissions=True)
        result[name] = sorted(set(changes)) or ["unchanged"]
    return result


def _migrate_submitted_purchase_orders(by_number):
    """Amend untouched demo orders so their item accounts no longer point to legacy ledgers."""
    expense_account = by_number["4410"]
    tax_account = by_number["1440"]
    result = {}
    for reference in DEMO_PURCHASE_REFERENCES:
        active = frappe.get_all(
            "Purchase Order",
            filters={"company": COMPANY, "order_confirmation_no": reference, "docstatus": ["!=", 2]},
            pluck="name",
        )
        if len(active) != 1:
            frappe.throw(f"{reference} debe tener exactamente una orden activa; se encontraron {len(active)}.")
        current = frappe.get_doc("Purchase Order", active[0])
        if all(row.expense_account == expense_account for row in current.items):
            result[reference] = {"name": current.name, "status": "existing"}
            continue
        if current.docstatus != 1:
            frappe.throw(f"La orden {current.name} no está enviada ni lista para enmienda.")
        if any(flt(row.received_qty) or flt(row.billed_amt) for row in current.items):
            frappe.throw(f"La orden {current.name} tiene recepción o facturación y no se modificará.")

        before_total = flt(current.grand_total, 2)
        current.flags.ignore_permissions = True
        current.cancel()

        amended = frappe.copy_doc(current)
        amended.name = None
        amended.docstatus = 0
        amended.status = "Draft"
        amended.amended_from = current.name
        amended.flags.ignore_permissions = True
        for row in amended.items:
            row.expense_account = expense_account
        for row in amended.taxes:
            row.account_head = tax_account
        amended.insert(ignore_permissions=True)
        amended.submit()
        if flt(amended.grand_total, 2) != before_total:
            frappe.throw(f"La enmienda de {current.name} cambió el total de la orden.")
        result[reference] = {"cancelled": current.name, "name": amended.name, "status": "amended"}

    if frappe.db.exists("Purchase Order", HISTORICAL_PURCHASE_ORDER):
        historical = frappe.get_doc("Purchase Order", HISTORICAL_PURCHASE_ORDER)
        if historical.docstatus == 1 and historical.status != "Closed":
            if flt(historical.per_billed) != 100:
                frappe.throw(
                    f"La orden histórica {HISTORICAL_PURCHASE_ORDER} no está totalmente facturada; no se cerrará."
                )
            historical.update_status("Closed")
            result[HISTORICAL_PURCHASE_ORDER] = {"status": "closed"}
        else:
            result[HISTORICAL_PURCHASE_ORDER] = {"status": historical.status.lower()}
    return result


def _update_item_defaults(by_number):
    result = Counter()
    expense = by_number["4410"]
    income = by_number["4100"]
    for item_name in frappe.get_all("Item", filters={"disabled": 0}, pluck="name", limit_page_length=0):
        doc = frappe.get_doc("Item", item_name)
        row = next((entry for entry in doc.item_defaults if entry.company == COMPANY), None)
        if not row:
            continue
        changed = False
        if row.income_account != income:
            row.income_account = income
            changed = True
        if not doc.is_stock_item and row.expense_account != expense:
            row.expense_account = expense
            changed = True
        if changed:
            doc.save(ignore_permissions=True)
            result["updated"] += 1
        else:
            result["existing"] += 1
    return dict(result)


def _update_asset_categories(by_number):
    result = {}
    for category, numbers in ASSET_CATEGORY_ACCOUNTS.items():
        if not frappe.db.exists("Asset Category", category):
            frappe.throw(f"Falta la categoría de activo {category}.")
        doc = frappe.get_doc("Asset Category", category)
        rows = [row for row in doc.accounts if row.company_name == COMPANY]
        if len(rows) != 1:
            frappe.throw(f"{category} debe tener exactamente una configuración contable para CISE.")
        row = rows[0]
        expected = tuple(by_number[number] for number in numbers)
        actual = (
            row.fixed_asset_account,
            row.accumulated_depreciation_account,
            row.depreciation_expense_account,
        )
        if actual != expected:
            row.fixed_asset_account, row.accumulated_depreciation_account, row.depreciation_expense_account = expected
            doc.save(ignore_permissions=True)
            result[category] = "updated"
        else:
            result[category] = "existing"
    return result


def _tree_issues():
    rows = frappe.get_all(
        "Account",
        filters={"company": COMPANY},
        fields=["name", "parent_account", "lft", "rgt"],
        limit_page_length=0,
    )
    by_name = {row.name: row for row in rows}
    issues = []
    for row in rows:
        if row.lft >= row.rgt:
            issues.append(f"intervalo inválido: {row.name}")
        if row.parent_account:
            parent = by_name.get(row.parent_account)
            if not parent or not (parent.lft < row.lft < row.rgt < parent.rgt):
                issues.append(f"padre inválido: {row.name}")
    return issues


def _validate(accounts, roots, by_number, gl_before=None):
    missing = [number for number, name in by_number.items() if not frappe.db.exists("Account", name)]
    if missing:
        frappe.throw(f"No se crearon las cuentas CISE: {', '.join(missing)}")
    issues = _tree_issues()
    if issues:
        frappe.throw("El árbol contable quedó inconsistente: " + "; ".join(issues[:10]))

    numbered_top_level = {}
    legacy = {}
    for root_type, root_name in roots.items():
        numbered_top_level[root_type] = frappe.db.count(
            "Account",
            {"company": COMPANY, "parent_account": root_name, "account_number": ["is", "set"]},
        )
        legacy_name = f"{LEGACY_GROUPS[root_type]} - {ABBR}"
        legacy[root_type] = frappe.db.count("Account", {"company": COMPANY, "parent_account": legacy_name})

    gl_after = _gl_snapshot()
    if gl_before and gl_after != gl_before:
        frappe.throw(f"Los saldos contables cambiaron durante la migración: {gl_before} -> {gl_after}")

    company = frappe.get_doc("Company", COMPANY)
    defaults = {
        field: company.get(field)
        for field in COMPANY_DEFAULTS
        if frappe.get_meta("Company").has_field(field)
    }
    expected_defaults = {field: by_number[number] for field, number in COMPANY_DEFAULTS.items() if field in defaults}
    if defaults != expected_defaults:
        frappe.throw("Los valores predeterminados de la empresa no apuntan íntegramente al catálogo CYCE.")

    return {
        "catalog_accounts": len(accounts),
        "catalog_by_status": dict(Counter(row["status"] for row in accounts)),
        "bank_gl_accounts": [by_number[number] for number in ("1121", "1122", "1123", "1124")],
        "numbered_top_level": numbered_top_level,
        "legacy_children": legacy,
        "company_defaults": defaults,
        "gl": gl_after,
        "tree_issues": issues,
    }


def execute(apply=False):
    """Audit the plan or apply it when ``apply`` is truthy."""
    payload = _load_catalog()
    accounts = payload["accounts"]
    roots = _roots()
    by_number = _accounts_by_number(accounts)
    existing_numbers = frappe.get_all(
        "Account",
        filters={"company": COMPANY, "account_number": ["is", "set"]},
        fields=["name", "account_number"],
        limit_page_length=0,
    )
    conflicts = [
        row.name
        for row in existing_numbers
        if row.account_number in by_number and row.name != by_number[row.account_number]
    ]
    preview = {
        "mode": "apply" if apply else "audit",
        "catalog_accounts": len(accounts),
        "existing_numbered_accounts": len(existing_numbers),
        "conflicts": conflicts,
        "gl_before": _gl_snapshot(),
        "bank_gl_accounts_to_create": [by_number[number] for number in ("1121", "1122", "1123", "1124")],
        "legacy_strategy": LEGACY_GROUPS,
    }
    if conflicts:
        frappe.throw("Hay códigos contables que pertenecen a otra estructura: " + ", ".join(conflicts))
    if not apply:
        return preview

    frappe.db.savepoint("phase3e_cyce_chart")
    try:
        legacy_names = {}
        legacy_status = {}
        for root_type, root_name in roots.items():
            legacy_names[root_type], legacy_status[root_type] = _ensure_legacy_group(root_type, root_name)
        moved = _move_existing_chart(roots, legacy_names)

        account_status = Counter()
        for spec in accounts:
            _name, status = _ensure_account(spec, roots, by_number)
            account_status[status] += 1

        company_changes = _update_company_defaults(by_number)
        tax_templates = _update_tax_templates(by_number)
        purchase_orders = _update_open_purchase_orders(by_number)
        submitted_purchase_orders = _migrate_submitted_purchase_orders(by_number)
        item_defaults = _update_item_defaults(by_number)
        asset_categories = _update_asset_categories(by_number)

        validation = _validate(accounts, roots, by_number, preview["gl_before"])
        frappe.db.commit()
        frappe.clear_cache()
        return {
            **preview,
            "legacy_groups": legacy_status,
            "legacy_accounts_moved": moved,
            "account_status": dict(account_status),
            "company_changes": company_changes,
            "tax_templates": tax_templates,
            "purchase_orders": purchase_orders,
            "submitted_purchase_orders": submitted_purchase_orders,
            "item_defaults": item_defaults,
            "asset_categories": asset_categories,
            "validation": validation,
        }
    except Exception:
        frappe.db.rollback(save_point="phase3e_cyce_chart")
        raise
