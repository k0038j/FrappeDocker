import json

import frappe


PAYROLL_ENTRY = "HR-PRUN-2026-00002"
MONTHLY_ENTRY = "HR-PRUN-2026-00001"
EXPECTED_TOTAL = 187423.08
EXPECTED_ACCOUNTS = {
    "511010 - Sueldos y salarios - CYCE": {"debit": 187423.08, "credit": 0.0},
    "2138 - Retencion Inss Laboral - CYCE": {"debit": 0.0, "credit": 13119.61},
    "2131 - IR Salarios - CYCE": {"debit": 0.0, "credit": 11996.04},
    "2121 - Sueldos y Salarios por Pagar - CYCE": {"debit": 0.0, "credit": 162307.43},
}


def close_enough(actual, expected, tolerance=0.05):
    return abs(float(actual or 0) - float(expected)) <= tolerance


def run():
    entry = frappe.get_doc("Payroll Entry", PAYROLL_ENTRY)
    if entry.docstatus != 0 or not entry.salary_slips_submitted:
        raise RuntimeError(f"Unexpected quincenal Payroll Entry state: {entry.as_dict()}")

    slips = [
        frappe.get_doc("Salary Slip", name)
        for name in frappe.get_all(
            "Salary Slip",
            filters={"payroll_entry": PAYROLL_ENTRY, "docstatus": 1},
            pluck="name",
            order_by="employee",
        )
    ]
    if len(slips) != 23:
        raise RuntimeError(f"Expected 23 submitted quincenal Salary Slips, found {len(slips)}")
    if any(slip.journal_entry for slip in slips):
        raise RuntimeError("A quincenal Salary Slip is already linked to a Journal Entry")
    if frappe.db.count(
        "Salary Slip", {"payroll_entry": MONTHLY_ENTRY, "docstatus": 1, "journal_entry": ["is", "set"]}
    ):
        raise RuntimeError("Monthly Salary Slips are unexpectedly linked before Stage 8B")

    journal_entries_before = set(frappe.get_all("Journal Entry", pluck="name"))

    try:
        entry.make_accrual_jv_entry(slips)

        journal_entries_after = set(frappe.get_all("Journal Entry", pluck="name"))
        created = sorted(journal_entries_after - journal_entries_before)
        if len(created) != 1:
            raise RuntimeError(f"Expected one new Journal Entry, found {created}")

        journal_entry = frappe.get_doc("Journal Entry", created[0])
        if (
            journal_entry.docstatus != 1
            or journal_entry.voucher_type != "Journal Entry"
            or journal_entry.company != "CYCE, S.A."
            or str(journal_entry.posting_date) != "2026-09-15"
            or not close_enough(journal_entry.total_debit, EXPECTED_TOTAL)
            or not close_enough(journal_entry.total_credit, EXPECTED_TOTAL)
        ):
            raise RuntimeError(f"Unexpected Journal Entry header: {journal_entry.as_dict()}")

        account_totals = {}
        for row in journal_entry.accounts:
            bucket = account_totals.setdefault(row.account, {"debit": 0.0, "credit": 0.0})
            bucket["debit"] += float(row.debit_in_account_currency or 0)
            bucket["credit"] += float(row.credit_in_account_currency or 0)
        account_totals = {
            account: {
                "debit": round(amounts["debit"], 2),
                "credit": round(amounts["credit"], 2),
            }
            for account, amounts in account_totals.items()
        }
        if set(account_totals) != set(EXPECTED_ACCOUNTS):
            raise RuntimeError(f"Unexpected accounts in Journal Entry: {account_totals}")
        for account, expected in EXPECTED_ACCOUNTS.items():
            for side in ("debit", "credit"):
                if not close_enough(account_totals[account][side], expected[side]):
                    raise RuntimeError(
                        f"Unexpected {side} for {account}: {account_totals[account][side]}"
                    )

        linked = frappe.db.count(
            "Salary Slip",
            {"payroll_entry": PAYROLL_ENTRY, "docstatus": 1, "journal_entry": journal_entry.name},
        )
        if linked != 23:
            raise RuntimeError(f"Expected 23 linked quincenal Salary Slips, found {linked}")
        if frappe.db.count(
            "Salary Slip", {"payroll_entry": MONTHLY_ENTRY, "docstatus": 1, "journal_entry": ["is", "set"]}
        ):
            raise RuntimeError("Monthly Salary Slips changed during Stage 8A")

        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        raise

    print(
        json.dumps(
            {
                "stage": "8A",
                "payroll_entry": PAYROLL_ENTRY,
                "journal_entry": journal_entry.name,
                "docstatus": journal_entry.docstatus,
                "posting_date": str(journal_entry.posting_date),
                "total_debit": round(float(journal_entry.total_debit), 2),
                "total_credit": round(float(journal_entry.total_credit), 2),
                "accounts": account_totals,
                "linked_salary_slips": linked,
                "monthly_links_unchanged": True,
            },
            ensure_ascii=False,
        )
    )


run()
