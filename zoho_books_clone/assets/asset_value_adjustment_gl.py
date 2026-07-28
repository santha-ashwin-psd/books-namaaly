from __future__ import annotations
"""
Asset Value Adjustment GL — Phase 5, part 2 (final piece) of the
asset-management build-out. Covers impairment (write-down) and
revaluation (write-up) of an asset's carrying value outside the normal
depreciation schedule.

Both directions post against the asset's Accumulated Depreciation
Account rather than the Fixed Asset Account:

  Impairment (new_value < current_value):
    DR adjustment_account (Impairment Loss, P&L)
    CR Accumulated Depreciation Account

  Revaluation (new_value > current_value):
    DR Accumulated Depreciation Account
    CR adjustment_account (Revaluation Surplus/Reserve)

Why Accumulated Depreciation and not Fixed Asset Account: this app
derives an asset's net book value elsewhere (Asset Disposal GL) as
purchase_cost - current_value, i.e. it treats "everything that has
reduced value below original cost" as accumulated depreciation. Routing
impairment/revaluation through the same account keeps that invariant
true after an adjustment, so a later disposal's accumulated-depreciation
DR line and gain/loss calc stay correct without special-casing
adjustments. Original purchase_cost (and therefore the depreciation
schedule's opening_value trail) is left untouched -- an impairment
changes what the asset is worth, not what it originally cost.

Unlike capitalization/depreciation/disposal, this does NOT skip
is_existing_asset assets: an opening asset can still need impairment or
revaluation even though it was never capitalized through this app's own
GL, so the Accumulated Depreciation Account is still required and still
posted to.
"""

import frappe
from frappe import _
from frappe.utils import flt

from zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry import (
    make_gl_entries,
)
from zoho_books_clone.assets.asset_gl import get_category_accounts

_VOUCHER_TYPE = "Asset Value Adjustment"


def validate_adjustment_setup(doc) -> None:
    if not doc.asset:
        return

    asset = frappe.db.get_value(
        "Asset",
        doc.asset,
        ["docstatus", "status", "asset_category", "company", "purchase_cost", "current_value"],
        as_dict=True,
    )
    if not asset:
        frappe.throw(_("Asset {0} not found.").format(doc.asset))

    if asset.docstatus != 1:
        frappe.throw(_("Asset {0} must be submitted before its value can be adjusted.").format(doc.asset))

    if asset.status in ("Scrapped", "Sold"):
        frappe.throw(_("Asset {0} has already been disposed ({1}) -- its value can no longer be adjusted.").format(doc.asset, asset.status))

    if doc.new_value is None or flt(doc.new_value) < 0:
        frappe.throw(_("New Value must be zero or greater."))

    if flt(doc.new_value) > flt(asset.purchase_cost):
        frappe.throw(_("New Value cannot exceed the asset's original Purchase Cost ({0}).").format(frappe.bold(asset.purchase_cost)))

    if flt(doc.new_value) == flt(asset.current_value):
        frappe.throw(_("New Value is the same as the asset's Current Value -- nothing to adjust."))

    is_writedown = flt(doc.new_value) < flt(asset.current_value)
    if is_writedown and doc.adjustment_type != "Impairment (Write-down)":
        frappe.throw(_("New Value is lower than Current Value -- Adjustment Type must be Impairment (Write-down)."))
    if not is_writedown and doc.adjustment_type != "Revaluation (Write-up)":
        frappe.throw(_("New Value is higher than Current Value -- Adjustment Type must be Revaluation (Write-up)."))

    if not doc.adjustment_account:
        frappe.throw(_("Impairment Loss / Revaluation Surplus Account is required."))

    accounts = get_category_accounts(asset.asset_category, asset.company)
    if not accounts.get("accumulated_depreciation_account"):
        frappe.throw(
            _(
                "Asset Category {0} has no Accumulated Depreciation Account configured for company {1}. "
                "Add it under Asset Category \u2192 Accounting (per Company) first."
            ).format(frappe.bold(asset.asset_category), frappe.bold(asset.company))
        )


def post_adjustment_gl(doc) -> None:
    if doc.gl_posted:
        return

    validate_adjustment_setup(doc)

    asset = frappe.get_doc("Asset", doc.asset)
    current_value_before = flt(asset.current_value)
    new_value = flt(doc.new_value)
    amount = new_value - current_value_before  # negative = impairment, positive = revaluation

    doc.current_value_before = current_value_before
    doc.adjustment_amount = amount

    accounts = get_category_accounts(asset.asset_category, asset.company)
    accumulated_depreciation_account = accounts["accumulated_depreciation_account"]
    remarks = f"Asset value adjustment ({doc.adjustment_type}) \u2014 {asset.asset_name} ({asset.name}), {doc.name}"
    magnitude = abs(amount)

    if amount < 0:
        gl_map = [
            {
                "account": doc.adjustment_account,
                "debit": magnitude,
                "credit": 0,
                "voucher_type": _VOUCHER_TYPE,
                "voucher_no": doc.name,
                "posting_date": doc.adjustment_date,
                "company": asset.company,
                "remarks": remarks,
            },
            {
                "account": accumulated_depreciation_account,
                "debit": 0,
                "credit": magnitude,
                "voucher_type": _VOUCHER_TYPE,
                "voucher_no": doc.name,
                "posting_date": doc.adjustment_date,
                "company": asset.company,
                "remarks": remarks,
            },
        ]
    else:
        gl_map = [
            {
                "account": accumulated_depreciation_account,
                "debit": magnitude,
                "credit": 0,
                "voucher_type": _VOUCHER_TYPE,
                "voucher_no": doc.name,
                "posting_date": doc.adjustment_date,
                "company": asset.company,
                "remarks": remarks,
            },
            {
                "account": doc.adjustment_account,
                "debit": 0,
                "credit": magnitude,
                "voucher_type": _VOUCHER_TYPE,
                "voucher_no": doc.name,
                "posting_date": doc.adjustment_date,
                "company": asset.company,
                "remarks": remarks,
            },
        ]

    make_gl_entries(gl_map)

    doc.db_set("gl_posted", 1, update_modified=False)
    doc.db_set("current_value_before", current_value_before, update_modified=False)
    doc.db_set("adjustment_amount", amount, update_modified=False)

    asset.db_set("current_value", new_value, update_modified=False)


def reverse_adjustment_gl(doc) -> None:
    """Best-effort reversal on cancel -- never blocks the cancel itself
    on a GL-side failure, same posture as the other Asset GL modules."""
    if not doc.gl_posted:
        return
    try:
        make_gl_entries(
            [{"voucher_type": _VOUCHER_TYPE, "voucher_no": doc.name}],
            cancel=True,
        )
        asset = frappe.get_doc("Asset", doc.asset)
        asset.db_set("current_value", doc.current_value_before, update_modified=False)
        doc.db_set("gl_posted", 0, update_modified=False)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Asset value adjustment GL reversal failed")