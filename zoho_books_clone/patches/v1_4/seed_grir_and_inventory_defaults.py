"""
Patch v1_4: seed Stock Received But Not Billed (GR/IR) for every existing company,
and back-fill Books Company inventory account defaults when blank.

Background:
    Perpetual inventory Model B credits GR/IR on purchase-linked Material Receipt
    and debits the same account on Purchase Invoice for stock items. New companies
    get this account via bootstrap COA; existing companies need a one-time back-fill.

Non-destructive and idempotent.
"""
import frappe

from zoho_books_clone.books_setup.bootstrap import _acc_name
from zoho_books_clone.books_setup.install import _all_company_names

GRIR_NAME = "Stock Received But Not Billed"
GRIR_TYPE = "Stock Received But Not Billed"
PARENT_NAME = "Current Liabilities"


def execute():
    if not frappe.db.exists("DocType", "Account"):
        return

    for company in _all_company_names():
        _seed_grir(company)
        _backfill_books_company_defaults(company)

    frappe.db.commit()
    print("✅  v1_4: GR/IR account and inventory defaults back-filled for all companies.")


def _seed_grir(company: str) -> None:
    parent_full = _acc_name(PARENT_NAME, company)
    if not frappe.db.exists("Account", parent_full):
        frappe.log_error(
            title="Patch v1_4",
            message=(
                f"v1_4: skipping GR/IR seed for '{company}' — "
                f"parent account '{parent_full}' not found."
            ),
        )
        return

    full_name = _acc_name(GRIR_NAME, company)
    if frappe.db.exists("Account", full_name):
        # Ensure account_type is correct even if the leaf already existed under
        # a generic Liability type from a manual create.
        existing_type = frappe.db.get_value("Account", full_name, "account_type")
        if existing_type != GRIR_TYPE:
            frappe.db.set_value("Account", full_name, "account_type", GRIR_TYPE)
        return

    try:
        frappe.get_doc({
            "doctype": "Account",
            "account_name": GRIR_NAME,
            "account_type": GRIR_TYPE,
            "parent_account": parent_full,
            "is_group": 0,
            "company": company,
            "currency": "INR",
        }).insert(ignore_permissions=True)
    except Exception as exc:
        frappe.log_error(
            title="Patch v1_4",
            message=f"v1_4: GR/IR seed — {company}/{GRIR_NAME}: {exc}",
        )


def _backfill_books_company_defaults(company: str) -> None:
    if not frappe.db.exists("DocType", "Books Company"):
        return
    if not frappe.db.exists("Books Company", company):
        return

    updates = {}
    mapping = {
        "default_inventory_account": ("Stock In Hand", "Stock"),
        "stock_received_not_billed": (GRIR_NAME, GRIR_TYPE),
        "default_cogs_account": ("Cost of Goods Sold", "Cost of Goods Sold"),
    }
    for field, (acct_name, acct_type) in mapping.items():
        current = frappe.db.get_value("Books Company", company, field)
        if current:
            continue
        acct = (
            frappe.db.get_value(
                "Account",
                {"account_name": acct_name, "company": company, "is_group": 0},
                "name",
            )
            or frappe.db.get_value(
                "Account",
                {"account_type": acct_type, "company": company, "is_group": 0},
                "name",
            )
        )
        if acct:
            updates[field] = acct

    if updates:
        frappe.db.set_value("Books Company", company, updates)
