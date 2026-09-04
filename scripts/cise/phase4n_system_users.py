"""Create and link the explicitly authorized CYCE system users."""

from __future__ import annotations

import json
from pathlib import Path

import frappe


COMPANY = "CYCE, S.A."
USER_SPEC_PATH = Path(__file__).with_name("phase4n_system_users.json")


def _load_spec():
    if not USER_SPEC_PATH.exists():
        frappe.throw(f"No se encontró la especificación de usuarios: {USER_SPEC_PATH}")
    payload = json.loads(USER_SPEC_PATH.read_text(encoding="utf-8"))
    if payload.get("company") != COMPANY:
        frappe.throw("La especificación de usuarios no corresponde a CYCE, S.A.")
    users = payload.get("users") or []
    emails = [row["email"].lower() for row in users]
    employees = [row["employee"] for row in users]
    if len(emails) != len(set(emails)):
        frappe.throw("La especificación contiene correos duplicados.")
    if len(employees) != len(set(employees)):
        frappe.throw("La especificación contiene Employee duplicados.")
    return payload, users


def _role_names(user_name):
    return set(
        frappe.get_all(
            "Has Role",
            filters={"parent": user_name, "parenttype": "User"},
            pluck="role",
        )
    )


def _counts():
    return {
        "system_users": frappe.db.count("User", {"user_type": "System User"}),
        "cyce_employees": frappe.db.count("Employee", {"company": COMPANY}),
        "cyce_employees_with_user": frappe.db.count(
            "Employee", {"company": COMPANY, "user_id": ["is", "set"]}
        ),
        "salary_structure_assignments": frappe.db.count("Salary Structure Assignment"),
        "payroll_entries": frappe.db.count("Payroll Entry"),
        "salary_slips": frappe.db.count("Salary Slip"),
    }


def _audit(users):
    missing_employees = []
    missing_roles = []
    conflicts = []
    existing = []
    pending = []

    for row in users:
        if not frappe.db.exists("Employee", row["employee"]):
            missing_employees.append(row["employee"])
            continue

        employee = frappe.get_doc("Employee", row["employee"])
        if employee.company != COMPANY:
            conflicts.append(
                f"{row['employee']} pertenece a {employee.company}, no a {COMPANY}."
            )
        if employee.user_id and employee.user_id.lower() != row["email"].lower():
            conflicts.append(
                f"{row['employee']} ya está vinculado a {employee.user_id}."
            )

        for role in row.get("roles") or []:
            if not frappe.db.exists("Role", role):
                missing_roles.append(role)

        if frappe.db.exists("User", row["email"]):
            user = frappe.get_doc("User", row["email"])
            if user.user_type != "System User":
                conflicts.append(f"{row['email']} existe pero no es System User.")
            existing.append(row["email"])
        else:
            if row.get("existing_user"):
                conflicts.append(f"Falta el usuario existente esperado {row['email']}.")
            pending.append(row["email"])

    return {
        "authorized_users": len(users),
        "existing_users": sorted(existing),
        "pending_users": sorted(pending),
        "missing_employees": sorted(set(missing_employees)),
        "missing_roles": sorted(set(missing_roles)),
        "conflicts": conflicts,
    }


def _ensure_user(row, send_welcome_email=False):
    employee = frappe.get_doc("Employee", row["employee"])
    created = False

    if frappe.db.exists("User", row["email"]):
        user = frappe.get_doc("User", row["email"])
    else:
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": row["email"],
                "first_name": employee.first_name,
                "middle_name": employee.middle_name,
                "last_name": employee.last_name,
                "enabled": 1,
                "user_type": "System User",
                "send_welcome_email": 1 if send_welcome_email else 0,
                "roles": [{"role": role} for role in row.get("roles") or []],
            }
        ).insert(ignore_permissions=True)
        created = True

    if not row.get("preserve_existing_roles"):
        missing_roles = sorted(set(row.get("roles") or []) - _role_names(user.name))
        if missing_roles:
            user.add_roles(*missing_roles)

    if not employee.user_id:
        employee.user_id = user.name
        employee.save(ignore_permissions=True)

    return {"user": user.name, "employee": employee.name, "status": "created" if created else "existing"}


def execute(apply=False):
    """Audit or idempotently create only the users explicitly authorized."""
    payload, users = _load_spec()
    audit = _audit(users)
    preview = {
        "mode": "apply" if apply else "audit",
        "source": payload["source"],
        **audit,
        "welcome_email": "disabled",
        "passwords": "not_set",
        "counts_before": _counts(),
    }
    if audit["missing_employees"] or audit["missing_roles"] or audit["conflicts"]:
        frappe.throw(json.dumps(preview, ensure_ascii=False))
    if not apply:
        return preview

    frappe.db.savepoint("phase4n_system_users")
    try:
        result = {
            row["source_name"]: _ensure_user(
                row, send_welcome_email=payload.get("send_welcome_email", False)
            )
            for row in users
        }
        frappe.db.commit()
        return {**preview, "result": result, "counts_after": _counts()}
    except Exception:
        frappe.db.rollback(save_point="phase4n_system_users")
        raise


def validate():
    """Validate user, Employee link and minimum roles without writing."""
    _payload, users = _load_spec()
    authorized_employees = {row["employee"] for row in users}
    missing = []
    mismatches = []

    for row in users:
        if not frappe.db.exists("User", row["email"]):
            missing.append(row["email"])
            continue
        user = frappe.get_doc("User", row["email"])
        employee = frappe.get_doc("Employee", row["employee"])
        expected = {"enabled": 1, "user_type": "System User"}
        for field, expected_value in expected.items():
            if user.get(field) != expected_value:
                mismatches.append(
                    {"user": user.name, "field": field, "expected": expected_value, "actual": user.get(field)}
                )
        if employee.user_id != user.name:
            mismatches.append(
                {
                    "employee": employee.name,
                    "field": "user_id",
                    "expected": user.name,
                    "actual": employee.user_id,
                }
            )
        if not row.get("preserve_existing_roles"):
            for role in sorted(set(row.get("roles") or []) - _role_names(user.name)):
                mismatches.append({"user": user.name, "field": "role", "expected": role, "actual": None})

    linked = frappe.get_all(
        "Employee",
        filters={"company": COMPANY, "user_id": ["is", "set"]},
        fields=["name", "employee_name", "user_id"],
        order_by="name asc",
    )
    unexpected_links = [row for row in linked if row["name"] not in authorized_employees]
    return {
        "expected_users": len(users),
        "resolved_users": len(users) - len(missing),
        "missing": missing,
        "mismatches": mismatches,
        "linked_employees": linked,
        "unexpected_employee_user_links": unexpected_links,
        "counts": _counts(),
    }
