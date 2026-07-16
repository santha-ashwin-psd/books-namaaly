"""
Patch v1_3: back-fill the three Landed Cost Voucher charge accounts
(Freight & Parcel Charges - Inward, Local Transport Charges - Inward,
Freight & Courier Charges - Outward) for every EXISTING company.

Background:
    _seed_coa()'s COA list now includes these three accounts, so any NEW
    company created after this patch gets them automatically via
    bootstrap_company_data(). Companies that already existed before this
    change (e.g. VK Herbal) never ran that seeding step for these rows, so
    this patch runs the same idempotent insert logic against every company
    already in the system.

Non-destructive and idempotent: only inserts accounts that don't already
exist (checked by full account name "{account_name} - {company}"); never
renames or deletes anything. Safe to re-run.
"""
import frappe

from zoho_books_clone.books_setup.bootstrap import _acc_name
from zoho_books_clone.books_setup.install import _all_company_names

LANDED_COST_CHARGE_ACCOUNTS = [
    # (account_name, account_type, parent_name)
    ("Freight & Parcel Charges - Inward", "Expense", "Operating Expenses"),
    ("Local Transport Charges - Inward", "Expense", "Operating Expenses"),
    ("Freight & Courier Charges - Outward", "Expense", "Operating Expenses"),
]


def execute():
    if not frappe.db.exists("DocType", "Account"):
        return

    for company in _all_company_names():
        # Operating Expenses must already exist for this company (it's part
        # of the original COA every company was bootstrapped with); skip if
        # somehow missing rather than guessing a parent.
        parent_full = _acc_name("Operating Expenses", company)
        if not frappe.db.exists("Account", parent_full):
            frappe.log_error(
                title="Patch v1_3",
                message=(
                    f"v1_3: skipping landed-cost account seed for '{company}' — "
                    f"parent account '{parent_full}' not found."
                ),
            )
            continue

        for name, atype, parent in LANDED_COST_CHARGE_ACCOUNTS:
            full_name = _acc_name(name, company)
            if frappe.db.exists("Account", full_name):
                continue
            try:
                frappe.get_doc({
                    "doctype": "Account",
                    "account_name": name,
                    "account_type": atype,
                    "parent_account": parent_full,
                    "is_group": 0,
                    "company": company,
                    "currency": "INR",
                }).insert(ignore_permissions=True)
            except Exception as exc:
                frappe.log_error(
                    title="Patch v1_3",
                    message=f"v1_3: landed-cost account seed — {company}/{name}: {exc}",
                )

    frappe.db.commit()
    print("✅  v1_3: Landed Cost Voucher charge accounts back-filled for all companies.")