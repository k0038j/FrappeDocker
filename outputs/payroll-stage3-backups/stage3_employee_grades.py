import json

import frappe


MONTHLY_GRADE = "Nomina Mensual INSS"
BIMONTHLY_GRADE = "Nomina Quincenal INSS"
EXCLUDED_EMPLOYEE = "HR-EMP-00002"

MONTHLY_EMPLOYEES = (
    "HR-EMP-00001",
    "HR-EMP-00003",
    "HR-EMP-00004",
    "HR-EMP-00005",
    "HR-EMP-00006",
    "HR-EMP-00007",
    "HR-EMP-00008",
    "HR-EMP-00009",
    "HR-EMP-00010",
    "HR-EMP-00011",
    "HR-EMP-00012",
    "HR-EMP-00013",
    "HR-EMP-00014",
    "HR-EMP-00015",
    "HR-EMP-00016",
)

BIMONTHLY_EMPLOYEES = (
    "HR-EMP-00017",
    "HR-EMP-00018",
    "HR-EMP-00019",
    "HR-EMP-00020",
    "HR-EMP-00021",
    "HR-EMP-00022",
    "HR-EMP-00023",
    "HR-EMP-00024",
    "HR-EMP-00025",
    "HR-EMP-00026",
    "HR-EMP-00027",
    "HR-EMP-00028",
    "HR-EMP-00029",
    "HR-EMP-00030",
    "HR-EMP-00031",
    "HR-EMP-00032",
    "HR-EMP-00033",
    "HR-EMP-00036",
    "HR-EMP-00037",
    "HR-EMP-00038",
    "HR-EMP-00040",
    "HR-EMP-00041",
    "HR-EMP-00042",
)


assignments = {
    **{employee: MONTHLY_GRADE for employee in MONTHLY_EMPLOYEES},
    **{employee: BIMONTHLY_GRADE for employee in BIMONTHLY_EMPLOYEES},
}

if len(assignments) != 38:
    raise RuntimeError(f"Expected 38 unique assignments, found {len(assignments)}")
if EXCLUDED_EMPLOYEE in assignments:
    raise RuntimeError("Augusto Garcia must not be assigned to a payroll grade")

for grade in (MONTHLY_GRADE, BIMONTHLY_GRADE):
    if not frappe.db.exists("Employee Grade", grade):
        raise RuntimeError(f"Missing Employee Grade: {grade}")

expected_active = set(assignments) | {EXCLUDED_EMPLOYEE}
active_rows = frappe.get_all(
    "Employee",
    filters={"status": "Active"},
    fields=["name", "employee_name", "grade"],
)
active_by_name = {row.name: row for row in active_rows}

if set(active_by_name) != expected_active:
    missing = sorted(expected_active - set(active_by_name))
    unexpected = sorted(set(active_by_name) - expected_active)
    raise RuntimeError(f"Active employee set changed. Missing={missing}; unexpected={unexpected}")

allowed_current_grades = {None, "", MONTHLY_GRADE, BIMONTHLY_GRADE}
conflicts = [
    {"employee": code, "grade": active_by_name[code].grade}
    for code in assignments
    if active_by_name[code].grade not in allowed_current_grades
]
if conflicts:
    raise RuntimeError(f"Unexpected existing grades: {conflicts}")

changed = []
unchanged = []
for employee, target_grade in assignments.items():
    current_grade = active_by_name[employee].grade or ""
    if current_grade == target_grade:
        unchanged.append(employee)
        continue
    frappe.db.set_value("Employee", employee, "grade", target_grade, update_modified=True)
    changed.append({"employee": employee, "from": current_grade or None, "to": target_grade})

excluded_current_grade = active_by_name[EXCLUDED_EMPLOYEE].grade or ""
excluded_changed = False
if excluded_current_grade:
    frappe.db.set_value("Employee", EXCLUDED_EMPLOYEE, "grade", None, update_modified=True)
    excluded_changed = True

frappe.db.commit()

verification = frappe.get_all(
    "Employee",
    filters={"status": "Active"},
    fields=["name", "employee_name", "grade"],
    order_by="name",
)
monthly_count = sum(row.grade == MONTHLY_GRADE for row in verification)
bimonthly_count = sum(row.grade == BIMONTHLY_GRADE for row in verification)
excluded_grade = next(row.grade for row in verification if row.name == EXCLUDED_EMPLOYEE)

if monthly_count != 15 or bimonthly_count != 23 or excluded_grade:
    raise RuntimeError(
        "Post-commit verification failed: "
        f"monthly={monthly_count}, bimonthly={bimonthly_count}, excluded_grade={excluded_grade!r}"
    )

print(
    json.dumps(
        {
            "changed": len(changed),
            "unchanged": len(unchanged),
            "monthly": monthly_count,
            "bimonthly": bimonthly_count,
            "augusto_grade": excluded_grade,
            "augusto_was_cleared": excluded_changed,
        },
        ensure_ascii=False,
    )
)
