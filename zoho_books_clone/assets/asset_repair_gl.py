from __future__ import annotations
"""
Asset Repair GL — Phase 4, part 2 of the asset-management build-out.

Two mutually-exclusive postings depending on Asset Repair.is_capitalized:

  Capitalized (extends useful life/capacity -- added to the asset's value):
    DR Fixed Asset Account (from the asset's category+company, same
       lookup asset_gl.get_category_accounts uses for capitalization)
    CR Asset Repair.credit_account (Payable/Bank/Cash, picked explicitly
       -- same posture as Asset.credit_account, never defaulted)
    ...and repair_cost is added onto Asset.purchase_cost / current_value.

  Expensed (routine upkeep -- a period cost, not a value increase):
    DR Asset Repair.expense_account (picked explicitly -- this app has no
       per-category or per-company default Repair & Maintenance account)
    CR Asset Repair.credit_account

On cancel, the GL is reversed via the same general_ledger_entry path
every other financial doctype here uses, and -- if the repair was
capitalized -- the purchase_cost/current_value bump on the Asset is
undone too.

Deliberately NOT handled here (out of scope for this phase):
  - Regenerating the Asset's depreciation schedule against the new
    (higher) purchase_cost after a capitalized repair. Asset.
    generate_depreciation_schedule() already refuses to touch a schedule
    once any row is Completed (see depreciation_posting.py), so a
    capitalized repair on a partially-depreciated asset bumps
    current_value/purchase_cost but does NOT reflow future depreciation
    periods against the new cost -- that reallocation (spread the
    remaining net book value + repair cost over remaining life) is a
    real accounting policy choice, not a mechanical default, and is
    flagged here rather than guessed at.
"""

import frappe
from frappe import _
from frappe.utils import flt

from zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry import (
    make_gl_entries,
)
from zoho_books_clone.assets.asset_gl import get_category_accounts

_VOUCHER_TYPE = "Asset Repair"


def validate_repair_setup(doc) -> None:
    """Called from AssetRepair.validate() so setup gaps surface while
    still editing, not only at submit time."""
    if not doc.asset:
        return
    if not doc.credit_account:
        frappe.throw(_("Credit Account (Payable / Bank / Cash) is required."))

    if doc.is_capitalized:
        asset = frappe.db.get_value("Asset", doc.asset, ["asset_category", "company"], as_dict=True)
        if not asset:
            frappe.throw(_("Asset {0} not found.").format(doc.asset))
        accounts = get_category_accounts(asset.asset_category, asset.company)
        if not accounts.get("fixed_asset_account"):
            frappe.throw(
                _(
                    "Asset Category {0} has no Fixed Asset Account configured for company {1}. "
                    "Add a row under Asset Category \u2192 Accounting (per Company) first, or "
                    "uncheck Capitalize to Asset Value to expense this repair instead."
                ).format(frappe.bold(asset.asset_category), frappe.bold(asset.company))
            )
    else:
        if not doc.expense_account:
            frappe.throw(_("Expense Account is required when the repair is not capitalized."))


def post_repair_gl(doc) -> None:
    """DR (Fixed Asset Account | Expense Account) / CR credit_account for
    repair_cost. Skipped on a second submit-attempt if already posted."""
    if doc.gl_posted:
        return

    validate_repair_setup(doc)

    amount = flt(doc.repair_cost)
    if amount <= 0:
        frappe.throw(_("Repair Cost must be greater than zero."))

    asset = frappe.get_doc("Asset", doc.asset)

    if doc.is_capitalized:
        accounts = get_category_accounts(asset.asset_category, asset.company)
        debit_account = accounts.get("fixed_asset_account")
    else:
        debit_account = doc.expense_account

    remarks = f"Asset repair \u2014 {asset.asset_name} ({asset.name}), {doc.name}"

    gl_map = [
        {
            "account": debit_account,
            "debit": amount,
            "credit": 0,
            "voucher_type": _VOUCHER_TYPE,
            "voucher_no": doc.name,
            "posting_date": doc.repair_date,
            "company": asset.company,
            "remarks": remarks,
        },
        {
            "account": doc.credit_account,
            "debit": 0,
            "credit": amount,
            "voucher_type": _VOUCHER_TYPE,
            "voucher_no": doc.name,
            "posting_date": doc.repair_date,
            "company": asset.company,
            "remarks": remarks,
        },
    ]
    make_gl_entries(gl_map)
    doc.db_set("gl_posted", 1, update_modified=False)

    if doc.is_capitalized:
        asset.db_set("purchase_cost", flt(asset.purchase_cost) + amount, update_modified=False)
        asset.db_set("current_value", flt(asset.current_value) + amount, update_modified=False)
        doc.db_set("capitalized_amount_applied", 1, update_modified=False)


def reverse_repair_gl(doc) -> None:
    """Best-effort reversal on cancel -- never blocks the cancel itself
    on a GL-side failure, same posture as reverse_asset_capitalization."""
    if not doc.gl_posted:
        return
    try:
        make_gl_entries(
            [{"voucher_type": _VOUCHER_TYPE, "voucher_no": doc.name}],
            cancel=True,
        )
        doc.db_set("gl_posted", 0, update_modified=False)

        if doc.capitalized_amount_applied:
            asset = frappe.get_doc("Asset", doc.asset)
            amount = flt(doc.repair_cost)
            asset.db_set("purchase_cost", flt(asset.purchase_cost) - amount, update_modified=False)
            asset.db_set("current_value", flt(asset.current_value) - amount, update_modified=False)
            doc.db_set("capitalized_amount_applied", 0, update_modified=False)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Asset repair GL reversal failed")