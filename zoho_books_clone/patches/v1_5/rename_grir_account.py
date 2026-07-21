"""
Patch v1_5: rename the GR/IR clearing account's display name from
"Stock Received But Not Billed" to "Stock Received" for every company.

Only the account_name / doc name (autoname "{account_name} - {company}")
changes. account_type stays "Stock Received But Not Billed" — that's a
fixed Select option baked into accounts/doctype/account/account.json and
is read by GL posting logic (accounts/inventory_gl.py GRIR_ACCOUNT_TYPE),
the balance sheet report, and Books Company account-type validation, so it
is left untouched. Renaming the Account doc automatically updates every
Link reference (Books Company.stock_received_not_billed, GL Entry rows,
etc.) via frappe.rename_doc.

Non-destructive and idempotent.
"""
import frappe

from zoho_books_clone.books_setup.bootstrap import _acc_name
from zoho_books_clone.books_setup.install import _all_company_names

OLD_NAME = "Stock Received But Not Billed"
NEW_NAME = "Stock Received"


def execute():
    if not frappe.db.exists("DocType", "Account"):
        return

    for company in _all_company_names():
        _rename_grir(company)

    frappe.db.commit()
    print("✅  v1_5: GR/IR account renamed to 'Stock Received' for all companies.")


def _rename_grir(company: str) -> None:
    old_full = _acc_name(OLD_NAME, company)
    new_full = _acc_name(NEW_NAME, company)

    if not frappe.db.exists("Account", old_full):
        return  # already renamed, or never seeded for this company

    if frappe.db.exists("Account", new_full):
        # Target already exists (e.g. re-run after a partial failure) —
        # nothing more to do here.
        return

    try:
        frappe.rename_doc("Account", old_full, new_full, force=True)
        frappe.db.set_value("Account", new_full, "account_name", NEW_NAME)
    except Exception as exc:
        frappe.log_error(
            title="Patch v1_5",
            message=f"v1_5: GR/IR rename — {company}/{OLD_NAME}: {exc}",
        )