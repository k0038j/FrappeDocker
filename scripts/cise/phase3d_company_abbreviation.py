"""Audit and migrate the CYCE company abbreviation from CISE to CYCE.

The migration is deliberately narrow: it changes only the Company abbreviation,
the generated suffix of company-scoped master identifiers, and the links that
Frappe updates through ``rename_doc``.  Base names, account numbers, hierarchy,
transactions, quantities and monetary values are preserved.
"""

from __future__ import annotations

from collections import OrderedDict

import frappe
from frappe.model.rename_doc import rename_doc
from frappe.utils import flt


COMPANY = "CYCE, S.A."
OLD_ABBR = "CISE"
NEW_ABBR = "CYCE"
OLD_SUFFIX = f" - {OLD_ABBR}"
NEW_SUFFIX = f" - {NEW_ABBR}"

# Tree masters are renamed from leaves to roots so every parent link remains
# resolvable throughout the operation. Tax templates are ordinary documents.
SCOPED_DOCTYPES = OrderedDict(
    (
        ("Account", True),
        ("Department", True),
        ("Warehouse", True),
        ("Cost Center", True),
        ("Item Tax Template", False),
        ("Sales Taxes and Charges Template", False),
        ("Purchase Taxes and Charges Template", False),
    )
)

ACCOUNT_PROPERTY_SETTERS = {
    "Account-main-title_field": {
        "property": "title_field",
        "value": "account_name",
        "property_type": "Data",
    },
    "Account-main-show_title_field_in_link": {
        "property": "show_title_field_in_link",
        "value": "1",
        "property_type": "Check",
    },
}


def _normalize_name(value: str | None) -> str | None:
    if not value:
        return value
    if value.endswith(OLD_SUFFIX):
        return value[: -len(OLD_SUFFIX)] + " - {ABBR}"
    if value.endswith(NEW_SUFFIX):
        return value[: -len(NEW_SUFFIX)] + " - {ABBR}"
    return value


def _target_name(name: str) -> str:
    if not name.endswith(OLD_SUFFIX):
        frappe.throw(f"El identificador no termina en {OLD_SUFFIX}: {name}")
    return name[: -len(OLD_SUFFIX)] + NEW_SUFFIX


def _company_filters(doctype: str) -> dict:
    meta = frappe.get_meta(doctype)
    return {"company": COMPANY} if meta.has_field("company") else {}


def _affected_rows(doctype: str, tree: bool) -> list:
    fields = ["name"]
    if tree and frappe.get_meta(doctype).has_field("lft"):
        fields.append("lft")
    rows = frappe.get_all(
        doctype,
        filters={**_company_filters(doctype), "name": ["like", f"%{OLD_SUFFIX}"]},
        fields=fields,
        order_by="lft desc" if "lft" in fields else "name asc",
        limit_page_length=0,
    )
    return rows


def _counts(suffix: str) -> dict:
    result = {}
    for doctype in SCOPED_DOCTYPES:
        result[doctype] = frappe.db.count(
            doctype,
            {**_company_filters(doctype), "name": ["like", f"%{suffix}"]},
        )
    return result


def _gl_snapshot() -> dict:
    rows = frappe.get_all(
        "GL Entry",
        filters={"company": COMPANY, "is_cancelled": 0},
        fields=["debit", "credit"],
        limit_page_length=0,
    )
    return {
        "count": len(rows),
        "debit": flt(sum(flt(row.debit) for row in rows), 2),
        "credit": flt(sum(flt(row.credit) for row in rows), 2),
    }


def _account_structure() -> list[tuple]:
    rows = frappe.get_all(
        "Account",
        filters={"company": COMPANY},
        fields=[
            "name",
            "account_name",
            "account_number",
            "parent_account",
            "root_type",
            "account_type",
            "is_group",
        ],
        order_by="lft asc",
        limit_page_length=0,
    )
    return [
        (
            _normalize_name(row.name),
            row.account_name,
            row.account_number or "",
            _normalize_name(row.parent_account),
            row.root_type or "",
            row.account_type or "",
            int(row.is_group),
        )
        for row in rows
    ]


def _tree_issues(doctype: str) -> list[str]:
    meta = frappe.get_meta(doctype)
    if not (meta.has_field("lft") and meta.has_field("rgt")):
        return []
    fields = ["name", "lft", "rgt"]
    parent_field = next(
        (
            field.fieldname
            for field in meta.fields
            if field.fieldtype == "Link" and field.options == doctype and field.fieldname.startswith("parent_")
        ),
        None,
    )
    if parent_field:
        fields.append(parent_field)
    rows = frappe.get_all(
        doctype,
        filters=_company_filters(doctype),
        fields=fields,
        limit_page_length=0,
    )
    by_name = {row.name: row for row in rows}
    issues = []
    for row in rows:
        if row.lft >= row.rgt:
            issues.append(f"intervalo inválido: {row.name}")
        parent_name = row.get(parent_field) if parent_field else None
        if parent_name:
            parent = by_name.get(parent_name)
            if not parent or not (parent.lft < row.lft < row.rgt < parent.rgt):
                issues.append(f"padre inválido: {row.name}")
    return issues


def _normalized_tree_issues() -> dict[str, list[str]]:
    result = {}
    for doctype, tree in SCOPED_DOCTYPES.items():
        if not tree:
            continue
        issues = _tree_issues(doctype)
        normalized = []
        for issue in issues:
            normalized.append(
                issue.replace(OLD_SUFFIX, " - {ABBR}").replace(NEW_SUFFIX, " - {ABBR}")
            )
        result[doctype] = sorted(normalized)
    return result


def _property_setter_audit() -> dict:
    result = {}
    for name, expected in ACCOUNT_PROPERTY_SETTERS.items():
        if not frappe.db.exists("Property Setter", name):
            result[name] = "absent"
            continue
        doc = frappe.get_doc("Property Setter", name)
        actual = {
            "property": doc.property,
            "value": str(doc.value),
            "property_type": doc.property_type,
        }
        result[name] = "expected" if actual == expected else {"unexpected": actual}
    return result


def _remove_visual_property_setters() -> dict:
    result = {}
    audit = _property_setter_audit()
    for name, status in audit.items():
        if isinstance(status, dict):
            frappe.throw(f"El Property Setter {name} ya no coincide con el ajuste temporal: {status}")
        if status == "absent":
            result[name] = "absent"
            continue
        frappe.delete_doc("Property Setter", name, ignore_permissions=True, force=True)
        result[name] = "deleted"
    frappe.clear_cache(doctype="Account")
    return result


def _assert_no_collisions(plan: dict[str, list[dict]]) -> None:
    collisions = []
    for doctype, rows in plan.items():
        for row in rows:
            target = _target_name(row["name"])
            if frappe.db.exists(doctype, target):
                collisions.append(f"{doctype}: {row['name']} -> {target}")
    if collisions:
        frappe.throw("Existen destinos que impedirían la migración: " + "; ".join(collisions[:20]))


def _rename_scoped_documents(plan: dict[str, list[dict]]) -> dict:
    result = {}
    # rename_doc normally clears the entire site cache after every document.
    # For this closed, prevalidated batch that is redundant and extremely slow.
    # Document caches are still cleared by rename_doc; the global site cache is
    # cleared once after the complete batch and again after commit.
    original_clear_cache = frappe.clear_cache
    frappe.clear_cache = lambda *args, **kwargs: None
    try:
        for doctype, rows in plan.items():
            renamed = []
            for row in rows:
                old_name = row["name"]
                new_name = _target_name(old_name)
                rename_doc(
                    doctype,
                    old_name,
                    new_name,
                    force=True,
                    merge=False,
                    ignore_permissions=True,
                    show_alert=False,
                    rebuild_search=False,
                )
                renamed.append({"from": old_name, "to": new_name})
            result[doctype] = renamed
    finally:
        frappe.clear_cache = original_clear_cache
        original_clear_cache()
    return result


def _validate(before: dict, expected_counts: dict) -> dict:
    company = frappe.get_doc("Company", COMPANY)
    if company.abbr != NEW_ABBR:
        frappe.throw(f"La empresa conserva una abreviatura inesperada: {company.abbr}")

    old_counts = _counts(OLD_SUFFIX)
    if any(old_counts.values()):
        frappe.throw(f"Persisten identificadores con {OLD_SUFFIX}: {old_counts}")

    new_counts = _counts(NEW_SUFFIX)
    if new_counts != expected_counts:
        frappe.throw(f"Los conteos migrados no coinciden: {expected_counts} -> {new_counts}")

    after_gl = _gl_snapshot()
    if after_gl != before["gl"]:
        frappe.throw(f"Los importes contables cambiaron: {before['gl']} -> {after_gl}")

    after_accounts = _account_structure()
    if after_accounts != before["account_structure"]:
        frappe.throw("La estructura o los atributos del plan de cuentas cambiaron durante el renombrado.")

    tree_issues = _normalized_tree_issues()
    if tree_issues != before["tree_issues"]:
        frappe.throw(
            "Los avisos de integridad de los árboles cambiaron durante la migración: "
            f"{before['tree_issues']} -> {tree_issues}"
        )

    property_setters = _property_setter_audit()
    if any(status != "absent" for status in property_setters.values()):
        frappe.throw(f"No se revirtió completamente la personalización visual: {property_setters}")

    return {
        "company_abbr": company.abbr,
        "old_suffix_counts": old_counts,
        "new_suffix_counts": new_counts,
        "gl": after_gl,
        "account_count": len(after_accounts),
        "tree_issues": tree_issues,
        "property_setters": property_setters,
    }


def execute(apply: bool = False) -> dict:
    """Audit the migration, or apply it when ``apply`` is truthy."""
    company = frappe.get_doc("Company", COMPANY)
    if company.abbr not in (OLD_ABBR, NEW_ABBR):
        frappe.throw(f"Abreviatura inesperada en {COMPANY}: {company.abbr}")

    plan = {
        doctype: _affected_rows(doctype, tree)
        for doctype, tree in SCOPED_DOCTYPES.items()
    }
    _assert_no_collisions(plan)
    affected_counts = {doctype: len(rows) for doctype, rows in plan.items()}
    preview = {
        "mode": "apply" if apply else "audit",
        "company": COMPANY,
        "current_abbr": company.abbr,
        "target_abbr": NEW_ABBR,
        "affected_counts": affected_counts,
        "property_setters": _property_setter_audit(),
        "gl": _gl_snapshot(),
        "account_count": frappe.db.count("Account", {"company": COMPANY}),
    }
    if not apply:
        return preview

    # A second run is a pure validation pass.
    if company.abbr == NEW_ABBR:
        if any(affected_counts.values()):
            frappe.throw("La empresa ya usa CYCE, pero todavía existen identificadores con el sufijo anterior.")
        before = {
            "gl": preview["gl"],
            "account_structure": _account_structure(),
            "tree_issues": _normalized_tree_issues(),
        }
        return {**preview, "status": "already_migrated", "validation": _validate(before, _counts(NEW_SUFFIX))}

    before = {
        "gl": preview["gl"],
        "account_structure": _account_structure(),
        "tree_issues": _normalized_tree_issues(),
    }
    frappe.db.savepoint("phase3d_company_abbreviation")
    try:
        visual_revert = _remove_visual_property_setters()
        # Company.abbr is set_only_once in ERPNext. A controlled migration must
        # bypass that form-level guard while still using Frappe's database API
        # and transaction. It is updated before renaming because Department and
        # Cost Center rebuild their target names from the current abbreviation
        # in their before_rename hooks.
        frappe.db.set_value("Company", COMPANY, "abbr", NEW_ABBR, update_modified=True)
        frappe.clear_document_cache("Company", COMPANY)

        renamed = _rename_scoped_documents(plan)

        validation = _validate(before, affected_counts)
        frappe.db.commit()
        frappe.clear_cache()
        return {
            **preview,
            "status": "migrated",
            "visual_revert": visual_revert,
            "renamed_counts": {doctype: len(rows) for doctype, rows in renamed.items()},
            "validation": validation,
        }
    except Exception:
        frappe.db.rollback(save_point="phase3d_company_abbreviation")
        frappe.clear_cache()
        raise
