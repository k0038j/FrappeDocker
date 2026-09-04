"""Idempotent project normalization for the CISE demonstration site."""

from __future__ import annotations

import json

import frappe
from frappe.utils import flt, getdate


CONSTRUCTION_PROJECT_NAME = "Estación Nueva Distrito 3"
EXPECTED_SOURCE_DEPARTMENT = "Ejecución Comercial - CYCE"
CONSTRUCTION_DEPARTMENT = "Gestión de Proyectos de Construcción - CYCE"

CONSULTING_PROJECT = {
    "project_name": "Estudio de Suelos - Estación Nueva Distrito 3",
    "company": "CYCE, S.A.",
    "project_type": "Verticales",
    "custom_linea_de_servicio": "Estudios de Suelos",
    "department": "Coordinación de Consultoría - CYCE",
    "status": "Open",
    "priority": "High",
    "is_active": "Yes",
    "expected_start_date": "2026-07-06",
    "expected_end_date": "2026-10-02",
    "estimated_costing": 450_000,
    "percent_complete_method": "Task Completion",
}


def _get_unique_project_by_title(project_name: str):
    project_ids = frappe.get_all(
        "Project", filters={"project_name": project_name}, pluck="name"
    )
    if len(project_ids) != 1:
        frappe.throw(
            f"Se esperaba exactamente un proyecto llamado {project_name!r}; "
            f"se encontraron {len(project_ids)}."
        )
    return frappe.get_doc("Project", project_ids[0])


def _validate_operational_department(department_name: str, company: str) -> None:
    if not frappe.db.exists("Department", department_name):
        frappe.throw(f"No existe el departamento {department_name}.")

    department = frappe.get_doc("Department", department_name)
    if department.disabled:
        frappe.throw(f"El departamento {department_name} está deshabilitado.")
    if department.is_group:
        frappe.throw(f"El departamento {department_name} es un nodo agrupador.")
    if department.company != company:
        frappe.throw(
            f"El departamento {department_name} pertenece a "
            f"{department.company}, no a {company}."
        )


def normalize_construction_project() -> dict:
    project = _get_unique_project_by_title(CONSTRUCTION_PROJECT_NAME)
    _validate_operational_department(CONSTRUCTION_DEPARTMENT, project.company)

    previous_department = project.department
    if previous_department == CONSTRUCTION_DEPARTMENT:
        return {
            "project": project.name,
            "project_name": project.project_name,
            "department": project.department,
            "status": "existing",
        }

    if previous_department != EXPECTED_SOURCE_DEPARTMENT:
        frappe.throw(
            f"El departamento actual es {previous_department!r}; se esperaba "
            f"{EXPECTED_SOURCE_DEPARTMENT!r}. No se sobrescribió."
        )

    project.department = CONSTRUCTION_DEPARTMENT
    project.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "project": project.name,
        "project_name": project.project_name,
        "previous_department": previous_department,
        "department": project.department,
        "status": "updated",
    }


def _validate_consulting_masters() -> None:
    company = CONSULTING_PROJECT["company"]
    if not frappe.db.exists("Company", company):
        frappe.throw(f"No existe la empresa {company}.")

    if not frappe.db.exists("Project Type", CONSULTING_PROJECT["project_type"]):
        frappe.throw(
            f"No existe el tipo de proyecto {CONSULTING_PROJECT['project_type']}."
        )

    _validate_operational_department(CONSULTING_PROJECT["department"], company)

    service_line_name = CONSULTING_PROJECT["custom_linea_de_servicio"]
    if not frappe.db.exists("CISE Service Line", service_line_name):
        frappe.throw(f"No existe la línea de servicio {service_line_name}.")
    service_line = frappe.get_doc("CISE Service Line", service_line_name)
    if service_line.disabled:
        frappe.throw(f"La línea de servicio {service_line_name} está deshabilitada.")


def _assert_consulting_project_matches(project) -> None:
    date_fields = {"expected_start_date", "expected_end_date"}
    currency_fields = {"estimated_costing"}
    mismatches = {}

    for fieldname, expected in CONSULTING_PROJECT.items():
        current = project.get(fieldname)
        if fieldname in date_fields:
            matches = getdate(current) == getdate(expected)
        elif fieldname in currency_fields:
            matches = flt(current) == flt(expected)
        else:
            matches = current == expected
        if not matches:
            mismatches[fieldname] = {"current": current, "expected": expected}

    if mismatches:
        frappe.throw(
            "Ya existe el proyecto de consultoría con una ficha distinta: "
            + json.dumps(mismatches, ensure_ascii=False, default=str)
        )


def create_consulting_project() -> dict:
    _validate_consulting_masters()
    project_name = CONSULTING_PROJECT["project_name"]
    existing_ids = frappe.get_all(
        "Project", filters={"project_name": project_name}, pluck="name"
    )
    if len(existing_ids) > 1:
        frappe.throw(
            f"Existen {len(existing_ids)} proyectos llamados {project_name!r}."
        )
    if existing_ids:
        existing = frappe.get_doc("Project", existing_ids[0])
        _assert_consulting_project_matches(existing)
        return {
            "project": existing.name,
            "project_name": existing.project_name,
            "department": existing.department,
            "service_line": existing.custom_linea_de_servicio,
            "status": "existing",
        }

    project = frappe.get_doc(
        {
            "doctype": "Project",
            "naming_series": "PROJ-.####",
            **CONSULTING_PROJECT,
        }
    )
    project.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "project": project.name,
        "project_name": project.project_name,
        "department": project.department,
        "service_line": project.custom_linea_de_servicio,
        "status": "created",
    }


def execute() -> dict:
    """Entry point for ``bench --site <site> execute``."""
    try:
        result = normalize_construction_project()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result
    except Exception:
        frappe.db.rollback()
        raise


def execute_consulting_project() -> dict:
    """Create the independent consulting project through Frappe ORM."""
    try:
        result = create_consulting_project()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result
    except Exception:
        frappe.db.rollback()
        raise
