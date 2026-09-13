import frappe


COMPANY = "CYCE, S.A."
PAYROLL_PAYABLE = "2121 - Sueldos y Salarios por Pagar - CYCE"
BASIC_COMPONENT = "Basic"
BASIC_EXPENSE = "511010 - Sueldos y salarios - CYCE"


def validate_account(account_name, expected_root_type):
    account = frappe.db.get_value(
        "Account",
        account_name,
        ["company", "root_type", "is_group", "disabled"],
        as_dict=True,
    )
    if not account:
        raise RuntimeError(f"Missing account: {account_name}")
    if account.company != COMPANY:
        raise RuntimeError(f"Account belongs to another company: {account_name}")
    if account.root_type != expected_root_type or account.is_group or account.disabled:
        raise RuntimeError(f"Account is not an enabled leaf {expected_root_type} account: {account_name}")


validate_account(PAYROLL_PAYABLE, "Liability")
validate_account(BASIC_EXPENSE, "Expense")

changes = []

company = frappe.get_doc("Company", COMPANY)
current_payable = company.default_payroll_payable_account
if current_payable and current_payable != PAYROLL_PAYABLE:
    raise RuntimeError(f"Company already has another payroll payable account: {current_payable}")
if current_payable != PAYROLL_PAYABLE:
    company.default_payroll_payable_account = PAYROLL_PAYABLE
    company.save(ignore_permissions=True)
    changes.append({"Company.default_payroll_payable_account": PAYROLL_PAYABLE})

basic = frappe.get_doc("Salary Component", BASIC_COMPONENT)
company_rows = [row for row in basic.accounts if row.company == COMPANY]
if company_rows and any(row.account != BASIC_EXPENSE for row in company_rows):
    raise RuntimeError("Basic already has a different account for CYCE, S.A.")
if not company_rows:
    basic.append("accounts", {"company": COMPANY, "account": BASIC_EXPENSE})
    basic.save(ignore_permissions=True)
    changes.append({"Basic.account": BASIC_EXPENSE})

frappe.db.commit()
print({"changes": changes})
