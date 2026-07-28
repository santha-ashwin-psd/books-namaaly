from __future__ import annotations
"""
Asset Disposal GL — Phase 5, part 1 of the asset-management build-out.

Handles both disposal_type values with one shared posting path:

  Scrap (no proceeds):
    DR Accumulated Depreciation Account   (depreciation posted so far)
    DR/CR Gain/Loss on Disposal Account   (always a loss = full NBV, unless NBV is 0)
    CR Fixed Asset Account                (original purchase_cost)

  Sale (with proceeds):
    DR Accumulated Depreciation Account
    DR Receivable Account                 (sale_amount)
    DR/CR Gain/Loss on Disposal Account   (loss if sale_amount < NBV, gain if >)
    CR Fixed Asset Account

Accumulated depreciation for the GL entry is derived as
  purchase_cost - current_value
rather than summed from the Depreciation Schedule's Completed rows.
Both should agree, but deriving it this way means the disposal entry
always balances by construction even if a capitalized Asset Repair or
manual current_value edit ever put the two slightly out of step --
correctness of the GL takes priority over reproducing the schedule's own
running total exactly.

is_existing_asset assets never had a capitalization entry posted (see
asset_gl.py), so there is no Fixed Asset Account balance for this app's
GL to relieve -- disposing one just updates Asset.status, no GL entry.
"""

import frappe
from frappe import _
from frappe.utils import flt

from zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry import (
    make_gl_entries,
)
from zoho_books_clone.assets.asset_gl import get_category_accounts

_VOUCHER_TYPE = "Asset Disposal"
_DISPOSED_STATUS = {"Scrap": "Scrapped", "Sale": "Sold"}


def validate_disposal_setup(doc) -> None:
    if not doc.asset:
        return

    asset = frappe.db.get_value(
        "Asset",
        doc.asset,
        ["docstatus", "status", "asset_category", "company", "is_existing_asset", "current_value", "purchase_cost"],
        as_dict=True,
    )
    if not asset:
        frappe.throw(_("Asset {0} not found.").format(doc.asset))

    if asset.docstatus != 1:
        frappe.throw(_("Asset {0} must be submitted before it can be disposed.").format(doc.asset))

    if asset.status in ("Scrapped", "Sold"):
        frappe.throw(_("Asset {0} has already been disposed ({1}).").format(doc.asset, asset.status))

    if not doc.gain_loss_account:
        frappe.throw(_("Gain / Loss on Disposal Account is required."))

    if not asset.is_existing_asset:
        accounts = get_category_accounts(asset.asset_category, asset.company)
        missing = [
            label
            for key, label in (
                ("fixed_asset_account", "Fixed Asset Account"),
                ("accumulated_depreciation_account", "Accumulated Depreciation Account"),
            )
            if not accounts.get(key)
        ]
        if missing:
            frappe.throw(
                _(
                    "Asset Category {0} is missing {1} for company {2}. "
                    "Add these under Asset Category \u2192 Accounting (per Company) first."
                ).format(frappe.bold(asset.asset_category), ", ".join(missing), frappe.bold(asset.company))
            )

    if doc.disposal_type == "Sale" and not doc.receivable_account:
        frappe.throw(_("Receivable Account is required for a Sale disposal."))


def post_disposal_gl(doc) -> None:
    if doc.gl_posted:
        return

    validate_disposal_setup(doc)

    asset = frappe.get_doc("Asset", doc.asset)
    doc.previous_asset_status = asset.status

    purchase_cost = flt(asset.purchase_cost)
    nbv = flt(asset.current_value)
    accumulated_depreciation = purchase_cost - nbv
    sale_amount = flt(doc.sale_amount) if doc.disposal_type == "Sale" else 0.0
    gain_loss = sale_amount - nbv  # positive = gain, negative = loss

    doc.purchase_cost_snapshot = purchase_cost
    doc.accumulated_depreciation_snapshot = accumulated_depreciation
    doc.net_book_value_snapshot = nbv
    doc.gain_loss_amount = gain_loss

    if not asset.is_existing_asset:
        accounts = get_category_accounts(asset.asset_category, asset.company)
        remarks = f"Asset disposal ({doc.disposal_type}) \u2014 {asset.asset_name} ({asset.name}), {doc.name}"

        gl_map = []
        if accumulated_depreciation > 0:
            gl_map.append({
                "account": accounts["accumulated_depreciation_account"],
                "debit": accumulated_depreciation,
                "credit": 0,
                "voucher_type": _VOUCHER_TYPE,
                "voucher_no": doc.name,
                "posting_date": doc.disposal_date,
                "company": asset.company,
                "remarks": remarks,
            })
        if sale_amount > 0:
            gl_map.append({
                "account": doc.receivable_account,
                "debit": sale_amount,
                "credit": 0,
                "voucher_type": _VOUCHER_TYPE,
                "voucher_no": doc.name,
                "posting_date": doc.disposal_date,
                "company": asset.company,
                "remarks": remarks,
            })
        if gain_loss > 0.01:
            gl_map.append({
                "account": doc.gain_loss_account,
                "debit": 0,
                "credit": gain_loss,
                "voucher_type": _VOUCHER_TYPE,
                "voucher_no": doc.name,
                "posting_date": doc.disposal_date,
                "company": asset.company,
                "remarks": remarks,
            })
        elif gain_loss < -0.01:
            gl_map.append({
                "account": doc.gain_loss_account,
                "debit": -gain_loss,
                "credit": 0,
                "voucher_type": _VOUCHER_TYPE,
                "voucher_no": doc.name,
                "posting_date": doc.disposal_date,
                "company": asset.company,
                "remarks": remarks,
            })
        gl_map.append({
            "account": accounts["fixed_asset_account"],
            "debit": 0,
            "credit": purchase_cost,
            "voucher_type": _VOUCHER_TYPE,
            "voucher_no": doc.name,
            "posting_date": doc.disposal_date,
            "company": asset.company,
            "remarks": remarks,
        })

        make_gl_entries(gl_map)

    doc.db_set("gl_posted", 1, update_modified=False)
    doc.db_set("previous_asset_status", asset.status, update_modified=False)
    doc.db_set("purchase_cost_snapshot", purchase_cost, update_modified=False)
    doc.db_set("accumulated_depreciation_snapshot", accumulated_depreciation, update_modified=False)
    doc.db_set("net_book_value_snapshot", nbv, update_modified=False)
    doc.db_set("gain_loss_amount", gain_loss, update_modified=False)

    asset.db_set("status", _DISPOSED_STATUS[doc.disposal_type], update_modified=False)
    asset.db_set("is_active", 0, update_modified=False)


def reverse_disposal_gl(doc) -> None:
    """Best-effort reversal on cancel -- never blocks the cancel itself
    on a GL-side failure, same posture as reverse_asset_capitalization."""
    if not doc.gl_posted:
        return
    try:
        asset = frappe.get_doc("Asset", doc.asset)

        if not asset.is_existing_asset:
            make_gl_entries(
                [{"voucher_type": _VOUCHER_TYPE, "voucher_no": doc.name}],
                cancel=True,
            )

        asset.db_set("status", doc.previous_asset_status or "Submitted", update_modified=False)
        asset.db_set("is_active", 1, update_modified=False)
        doc.db_set("gl_posted", 0, update_modified=False)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Asset disposal GL reversal failed")