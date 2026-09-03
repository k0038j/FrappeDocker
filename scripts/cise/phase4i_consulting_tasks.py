"""Configure the CISE consulting project, operational user, and demo tasks."""

from __future__ import annotations

import json

import frappe
from frappe.desk.form.assign_to import add as assign_to
from frappe.utils import flt, get_datetime, getdate


PROJECT_NAME = "Estudio de Suelos - Estación Nueva Distrito 3"
PROJECT_START = "2026-07-06"
PROJECT_END = "2026-10-02"

OPERATIONAL_USER = "coordinacion.consultoria@cise.com"
OPERATIONAL_USER_NAME = "Coordinación de Consultoría"
OPERATIONAL_ROLE = "Projects User"

TASKS = (
    {
        "subject": "Planificación y recopilación de información",
        "status": "Completed",
        "progress": 100,
        "exp_start_date": "2026-07-06 08:00:00",
        "exp_end_date": "2026-07-17 17:00:00",
        "description": "Definir alcance, entregables e información técnica de entrada.",
    },
    {
        "subject": "Trabajo de campo y toma de muestras",
        "status": "Completed",
        "progress": 100,
        "exp_start_date": "2026-07-20 08:00:00",
        "exp_end_date": "2026-08-07 17:00:00",
        "description": "Ejecutar reconocimiento, sondeos y toma controlada de muestras.",
    },
    {
        "subject": "Ensayos y análisis geotécnico",
        "status": "Completed",
        "progress": 100,
        "exp_start_date": "2026-08-10 08:00:00",
        "exp_end_date": "2026-08-28 17:00:00",
        "description": "Procesar ensayos y elaborar el análisis geotécnico preliminar.",
    },
    {
        "subject": "Revisión y entrega final",
        "status": "Working",
        "progress": 50,
        "exp_start_date": "2026-08-31 08:00:00",
        "exp_end_date": "2026-10-02 17:00:00",
        "description": "Revisar observaciones y preparar el informe geotécnico final.",
    },
)


def _get_project():
    project_ids = frappe.get_all(
        "Project", filters={"project_name": PROJECT_NAME}, pluck="name"
    )
    if len(project_ids) != 1:
        frappe.throw(
            f"Se esperaba un proyecto llamado {PROJECT_NAME!r}; "
            f"se encontraron {len(project_ids)}."
        )
    return frappe.get_doc("Project", project_ids[0])


def _ensure_operational_user() -> tuple[object, str]:
    if frappe.db.exists("User", OPERATIONAL_USER):
        user = frappe.get_doc("User", OPERATIONAL_USER)
        if user.first_name != OPERATIONAL_USER_NAME:
            frappe.throw(
                f"El correo {OPERATIONAL_USER} ya pertenece a "
                f"{user.full_name!r}; no se sobrescribió."
            )
        changed = False
        if not user.enabled:
            user.enabled = 1
            changed = True
        if user.user_type != "System User":
            frappe.throw(f"{OPERATIONAL_USER} no es un usuario del sistema.")
        if OPERATIONAL_ROLE not in {row.role for row in user.roles}:
            user.append("roles", {"role": OPERATIONAL_ROLE})
            changed = True
        if changed:
            user.save(ignore_permissions=True)
        return user, "updated" if changed else "existing"

    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": OPERATIONAL_USER,
            "first_name": OPERATIONAL_USER_NAME,
            "enabled": 1,
            "user_type": "System User",
            "language": "es",
            "send_welcome_email": 0,
            "roles": [{"role": OPERATIONAL_ROLE}],
        }
    )
    user.insert(ignore_permissions=True)
    return user, "created"


def _configure_project(project) -> str:
    if project.company != "CYCE, S.A.":
        frappe.throw(f"El proyecto pertenece a {project.company}, no a CYCE, S.A.")
    if project.department != "Coordinación de Consultoría - CISE":
        frappe.throw(f"Departamento inesperado: {project.department}.")
    if project.custom_linea_de_servicio != "Estudios de Suelos":
        frappe.throw(
            f"Línea de servicio inesperada: {project.custom_linea_de_servicio}."
        )

    changed = False
    if getdate(project.expected_start_date) != getdate(PROJECT_START):
        project.expected_start_date = PROJECT_START
        changed = True
    if getdate(project.expected_end_date) != getdate(PROJECT_END):
        project.expected_end_date = PROJECT_END
        changed = True
    if project.status != "Open":
        project.status = "Open"
        changed = True
    if project.is_active != "Yes":
        project.is_active = "Yes"
        changed = True
    if project.percent_complete_method != "Task Completion":
        project.percent_complete_method = "Task Completion"
        changed = True

    project_users = {row.user for row in project.users}
    if OPERATIONAL_USER not in project_users:
        project.append(
            "users",
            {
                "user": OPERATIONAL_USER,
                "view_attachments": 1,
                "welcome_email_sent": 1,
            },
        )
        changed = True

    if changed:
        project.save(ignore_permissions=True)
        return "updated"
    return "existing"


def _sync_task_fields(task, definition: dict, dependency: str | None) -> bool:
    changed = False
    simple_fields = ("priority", "description")
    expected_simple = {"priority": "High", "description": definition["description"]}
    for fieldname in simple_fields:
        if task.get(fieldname) != expected_simple[fieldname]:
            task.set(fieldname, expected_simple[fieldname])
            changed = True

    for fieldname in ("exp_start_date", "exp_end_date"):
        if get_datetime(task.get(fieldname)) != get_datetime(definition[fieldname]):
            task.set(fieldname, definition[fieldname])
            changed = True

    expected_dependencies = [dependency] if dependency else []
    current_dependencies = [row.task for row in task.depends_on]
    if current_dependencies != expected_dependencies:
        task.set("depends_on", [])
        if dependency:
            task.append("depends_on", {"task": dependency})
        changed = True
    return changed


def _assign_task(task) -> str:
    assignment = frappe.db.exists(
        "ToDo",
        {
            "reference_type": "Task",
            "reference_name": task.name,
            "allocated_to": OPERATIONAL_USER,
        },
    )
    if assignment:
        return "existing"

    assign_to(
        {
            "assign_to": json.dumps([OPERATIONAL_USER]),
            "doctype": "Task",
            "name": task.name,
            "description": f"Responsable operativo de {task.subject}",
            "priority": "High",
        }
    )
    return "created"


def _ensure_tasks(project) -> list[dict]:
    results = []
    dependency = None

    for definition in TASKS:
        task_ids = frappe.get_all(
            "Task",
            filters={"project": project.name, "subject": definition["subject"]},
            pluck="name",
        )
        if len(task_ids) > 1:
            frappe.throw(
                f"Hay tareas duplicadas con asunto {definition['subject']!r}."
            )

        if task_ids:
            task = frappe.get_doc("Task", task_ids[0])
            task_state = "existing"
            if _sync_task_fields(task, definition, dependency):
                task.save(ignore_permissions=True)
                task_state = "updated"
        else:
            task = frappe.get_doc(
                {
                    "doctype": "Task",
                    "subject": definition["subject"],
                    "project": project.name,
                    "status": "Open",
                    "progress": 0,
                    "priority": "High",
                    "description": definition["description"],
                    "exp_start_date": definition["exp_start_date"],
                    "exp_end_date": definition["exp_end_date"],
                }
            )
            if dependency:
                task.append("depends_on", {"task": dependency})
            task.insert(ignore_permissions=True)
            task_state = "created"

        assignment_state = _assign_task(task)

        desired_status = definition["status"]
        desired_progress = definition["progress"]
        if task.status != desired_status or flt(task.progress) != flt(desired_progress):
            task.status = desired_status
            task.progress = desired_progress
            task.save(ignore_permissions=True)
            if task_state == "existing":
                task_state = "updated"

        results.append(
            {
                "task": task.name,
                "subject": task.subject,
                "status": task.status,
                "task_state": task_state,
                "assignment": assignment_state,
            }
        )
        dependency = task.name

    return results


def configure() -> dict:
    user, user_state = _ensure_operational_user()
    project = _get_project()
    project_state = _configure_project(project)
    tasks = _ensure_tasks(project)

    project.reload()
    if flt(project.percent_complete, 2) != 75.0:
        frappe.throw(
            f"El avance calculado fue {project.percent_complete} %, no 75 %."
        )

    frappe.db.commit()
    return {
        "user": user.name,
        "user_state": user_state,
        "project": project.name,
        "project_state": project_state,
        "percent_complete": project.percent_complete,
        "tasks": tasks,
    }


def execute() -> dict:
    """Entry point for ``bench --site <site> execute``."""
    try:
        result = configure()
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return result
    except Exception:
        frappe.db.rollback()
        raise
