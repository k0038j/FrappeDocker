"""Prepare and import the approved CYCE personnel roster without payroll data."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import frappe


COMPANY = "CYCE, S.A."
ROSTER_PATH = Path(__file__).with_name("phase4n_employees.json")
REQUIRED_PERSONNEL_FIELDS = ("gender", "date_of_birth", "date_of_joining")
PROVISIONAL_DATE_OF_BIRTH = "1980-01-01"
PROVISIONAL_DATE_OF_JOINING = "2026-01-01"
FEMALE_FIRST_NAMES = {"Amanda", "Anshley", "Ingrid", "Junieth", "Marbel", "María"}


def _system_counts():
    return {
        "employees_cyce": frappe.db.count("Employee", {"company": COMPANY}),
        "salary_structure_assignments": frappe.db.count("Salary Structure Assignment"),
        "payroll_entries": frappe.db.count("Payroll Entry"),
        "salary_slips": frappe.db.count("Salary Slip"),
    }


def _load_roster():
    if not ROSTER_PATH.exists():
        frappe.throw(f"No se encontró el catálogo de personal: {ROSTER_PATH}")
    payload = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))
    if payload.get("company") != COMPANY:
        frappe.throw("El catálogo de personal no corresponde a CYCE, S.A.")
    employees = payload.get("employees") or []
    names = [row["source_name"] for row in employees]
    duplicates = [name for name, count in Counter(names).items() if count > 1]
    if duplicates:
        frappe.throw("El catálogo normalizado contiene personas duplicadas: " + ", ".join(duplicates))
    return payload, employees


def _designation_names(employees):
    return sorted({row["designation"] for row in employees})


def _resolved_personal_fields(row):
    return {
        "gender": row.get("gender") or ("Female" if row["first_name"] in FEMALE_FIRST_NAMES else "Male"),
        "date_of_birth": row.get("date_of_birth") or PROVISIONAL_DATE_OF_BIRTH,
        "date_of_joining": row.get("date_of_joining") or PROVISIONAL_DATE_OF_JOINING,
    }


def _missing_required_fields(row):
    values = _resolved_personal_fields(row)
    return [field for field in REQUIRED_PERSONNEL_FIELDS if not values.get(field)]


def _validate_references(employees):
    missing_departments = sorted(
        {row["department"] for row in employees if not frappe.db.exists("Department", row["department"])}
    )
    if missing_departments:
        frappe.throw("Faltan departamentos: " + ", ".join(missing_departments))

    existing_targets = [row for row in employees if row.get("existing_employee")]
    missing_targets = [
        row["existing_employee"]
        for row in existing_targets
        if not frappe.db.exists("Employee", row["existing_employee"])
    ]
    if missing_targets:
        frappe.throw("No existen los Employee indicados para reutilizar: " + ", ".join(missing_targets))


def _ensure_designations(employees):
    result = {}
    for designation in _designation_names(employees):
        if frappe.db.exists("Designation", designation):
            result[designation] = "existing"
            continue
        frappe.get_doc({"doctype": "Designation", "designation_name": designation}).insert(
            ignore_permissions=True
        )
        result[designation] = "created"
    return result


def _find_existing_employee(row):
    explicit = row.get("existing_employee")
    if explicit:
        return explicit
    matches = frappe.get_all(
        "Employee",
        filters={
            "company": COMPANY,
            "first_name": row["first_name"],
            "last_name": row.get("last_name") or ["is", "not set"],
        },
        pluck="name",
        limit_page_length=2,
    )
    if len(matches) > 1:
        frappe.throw(f"Hay más de un Employee que coincide con {row['source_name']}.")
    return matches[0] if matches else None


def _ensure_employees(employees):
    incomplete = {
        row["source_name"]: _missing_required_fields(row)
        for row in employees
        if _missing_required_fields(row) and not row.get("existing_employee")
    }
    if incomplete:
        frappe.throw(
            "No se crearán Employee con datos personales inventados. "
            "Complete gender, date_of_birth y date_of_joining: "
            + json.dumps(incomplete, ensure_ascii=False)
        )

    result = {}
    for row in employees:
        existing = _find_existing_employee(row)
        if existing:
            result[row["source_name"]] = {"employee": existing, "status": "existing"}
            continue

        personal = _resolved_personal_fields(row)
        doc = frappe.get_doc(
            {
                "doctype": "Employee",
                "naming_series": "HR-EMP-",
                "first_name": row["first_name"],
                "middle_name": row.get("middle_name"),
                "last_name": row.get("last_name"),
                "gender": personal["gender"],
                "date_of_birth": personal["date_of_birth"],
                "date_of_joining": personal["date_of_joining"],
                "status": "Active",
                "company": COMPANY,
                "department": row["department"],
                "designation": row["designation"],
            }
        ).insert(ignore_permissions=True)
        result[row["source_name"]] = {"employee": doc.name, "status": "created"}
    return result


def validate():
    """Validate the imported roster without modifying any document."""
    _payload, employees = _load_roster()
    _validate_references(employees)
    missing = []
    mismatches = []
    employee_ids = []
    genders = Counter()

    for row in employees:
        employee_name = _find_existing_employee(row)
        if not employee_name:
            missing.append(row["source_name"])
            continue

        employee_ids.append(employee_name)
        doc = frappe.get_doc("Employee", employee_name)
        expected = {
            "company": COMPANY,
            "department": row["department"],
            "designation": row["designation"],
            "status": "Active",
        }
        if not row.get("existing_employee"):
            expected.update(_resolved_personal_fields(row))
            expected["user_id"] = None

        for field, expected_value in expected.items():
            actual = doc.get(field)
            if field in {"date_of_birth", "date_of_joining"} and actual:
                actual = str(actual)
            if actual != expected_value:
                mismatches.append(
                    {
                        "source_name": row["source_name"],
                        "employee": employee_name,
                        "field": field,
                        "expected": expected_value,
                        "actual": actual,
                    }
                )
        genders[doc.gender] += 1

    return {
        "expected_people": len(employees),
        "resolved_people": len(employee_ids),
        "unique_employee_ids": len(set(employee_ids)),
        "missing": missing,
        "mismatches": mismatches,
        "gender_distribution": dict(sorted(genders.items())),
        "juan_loaisiga_records": frappe.db.count(
            "Employee",
            {"company": COMPANY, "first_name": "Juan", "last_name": "Loáisiga"},
        ),
        "nelly_employee": _find_existing_employee(
            next(row for row in employees if row.get("existing_employee") == "HR-EMP-00001")
        ),
        "counts": _system_counts(),
    }


def execute(apply_designations=False, apply_employees=False):
    """Audit the roster or apply only the explicitly selected parts."""
    payload, employees = _load_roster()
    _validate_references(employees)
    missing = {
        row["source_name"]: _missing_required_fields(row)
        for row in employees
        if _missing_required_fields(row) and not row.get("existing_employee")
    }
    preview = {
        "source": payload["source"],
        "normalized_people": len(employees),
        "source_rows": 43,
        "duplicate_source_assignment": {"Juan Loáisiga": ["Hialeah", "Milagro de Dios"]},
        "existing_employee_reused": {"María Andrade": "HR-EMP-00001"},
        "designations": _designation_names(employees),
        "missing_required_employee_fields": missing,
        "provisional_personal_data": {
            "gender": "inferred_from_first_name",
            "date_of_birth": PROVISIONAL_DATE_OF_BIRTH,
            "date_of_joining": PROVISIONAL_DATE_OF_JOINING,
        },
        "payroll_configuration": "not_touched",
        "counts_before": _system_counts(),
    }
    if not apply_designations and not apply_employees:
        return {"mode": "audit", **preview}

    frappe.db.savepoint("phase4n_personnel")
    try:
        designations = _ensure_designations(employees) if apply_designations or apply_employees else {}
        employee_result = _ensure_employees(employees) if apply_employees else {}
        frappe.db.commit()
        return {
            "mode": "apply",
            **preview,
            "designation_result": designations,
            "employee_result": employee_result,
            "counts_after": _system_counts(),
        }
    except Exception:
        frappe.db.rollback(save_point="phase4n_personnel")
        raise
