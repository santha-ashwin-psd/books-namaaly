from __future__ import annotations
"""
Asset depreciation posting — Phase 3 (final piece).

depreciation_engine.py calculates the schedule; this module is the only
place that turns a due, Pending Depreciation Schedule row into a GL entry:

    DR Depreciation Expense Account (from the asset's category+company)
    CR Accumulated Depreciation Account (from the asset's category+company)

Runs daily via hooks.scheduler_events, but is written so it can also be
called directly/tested against a single asset. Idempotent: a row is only
ever posted once (status flips Pending -> Completed and gl_entry records
the voucher_no), and re-running the job just skips rows that are already
Completed or not yet due.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry import (
    make_gl_entries,
)
from zoho_books_clone.assets.asset_gl import get_category_accounts
from zoho_books_clone.assets.depreciation_engine import recompute_pending_rows

_VOUCHER_TYPE = "Asset Depreciation"


def post_due_depreciation(asset_name: str | None = None) -> list[str]:
    """Post every due, Pending depreciation row across all submitted,
    active assets (or just `asset_name` if given). Returns the list of
    Asset names touched. Never lets one asset's failure block the rest --
    logs and moves on, same pattern as reverse_asset_capitalization."""
    filters = {"docstatus": 1, "is_active": 1}
    if asset_name:
        filters["name"] = asset_name

    asset_names = frappe.get_all("Asset", filters=filters, pluck="name")
    posted_for: list[str] = []

    for name in asset_names:
        try:
            if _post_due_rows_for_asset(name):
                posted_for.append(name)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(), f"Depreciation posting failed for Asset {name}"
            )

    return posted_for


def _post_due_rows_for_asset(asset_name: str) -> bool:
    asset = frappe.get_doc("Asset", asset_name)

    if asset.is_existing_asset:
        # Opening-balance assets aren't capitalized through this app's GL,
        # so their depreciation isn't posted through it either -- consistent
        # with post_asset_capitalization's own is_existing_asset skip.
        return False

    due_rows = [
        row
        for row in (asset.depreciation_schedule or [])
        if row.status == "Pending" and getdate(row.depreciation_date) <= getdate(nowdate())
    ]
    if not due_rows:
        return False

    accounts = get_category_accounts(asset.asset_category, asset.company)
    depreciation_expense_account = accounts.get("depreciation_expense_account")
    accumulated_depreciation_account = accounts.get("accumulated_depreciation_account")

    if not depreciation_expense_account or not accumulated_depreciation_account:
        frappe.log_error(
            f"Asset Category {asset.asset_category} is missing Depreciation Expense / "
            f"Accumulated Depreciation account for company {asset.company} -- "
            f"cannot post due depreciation for Asset {asset_name}.",
            "Depreciation posting: missing account setup",
        )
        return False

    any_posted = False
    for row in due_rows:
        amount = flt(row.depreciation_amount)
        if amount <= 0:
            # Nothing to post (can legitimately happen on a fully-clamped
            # final row) -- mark it Completed without a zero-value GL entry.
            row.db_set("status", "Completed", update_modified=False)
            continue

        voucher_no = f"{asset.name}-DEP-{row.period_no or row.year}"

        gl_map = [
            {
                "account": depreciation_expense_account,
                "debit": amount,
                "credit": 0,
                "voucher_type": _VOUCHER_TYPE,
                "voucher_no": voucher_no,
                "posting_date": row.depreciation_date,
                "company": asset.company,
                "remarks": f"Depreciation \u2014 {asset.asset_name} ({asset.name}), period {row.period_no or row.year}",
            },
            {
                "account": accumulated_depreciation_account,
                "debit": 0,
                "credit": amount,
                "voucher_type": _VOUCHER_TYPE,
                "voucher_no": voucher_no,
                "posting_date": row.depreciation_date,
                "company": asset.company,
                "remarks": f"Depreciation \u2014 {asset.asset_name} ({asset.name}), period {row.period_no or row.year}",
            },
        ]
        make_gl_entries(gl_map)

        row.db_set("status", "Completed", update_modified=False)
        row.db_set("gl_entry", voucher_no, update_modified=False)
        any_posted = True

    if any_posted:
        # Book value after the latest posted period, kept in sync for
        # Asset Register / dashboard display without regenerating the
        # schedule (generate_depreciation_schedule() now refuses to touch
        # a schedule once any row is Completed).
        completed_rows = [
            r for r in asset.depreciation_schedule if r.status == "Completed"
        ]
        if completed_rows:
            latest = max(completed_rows, key=lambda r: (r.period_no or r.year or 0))
            asset.db_set("current_value", latest.closing_value, update_modified=False)

        # Nothing set Asset.status here before. Safe to overwrite unconditionally:
        # this function only ever runs against is_active assets (see the filters
        # in post_due_depreciation), and Asset Disposal clears is_active before
        # it sets Scrapped/Sold, so a disposed asset never reaches this branch.
        all_completed = all(
            r.status == "Completed" for r in asset.depreciation_schedule
        )
        asset.db_set(
            "status",
            "Fully Depreciated" if all_completed else "Partially Depreciated",
            update_modified=False,
        )

    return any_posted


def rederive_schedule(asset_name: str, new_opening_value: float | None = None) -> bool:
    """Phase 5: re-derive the remaining Pending Depreciation Schedule rows
    on `asset_name` after its cost/qty was shrunk outside the normal
    depreciation cycle (currently: Asset Quantity Adjustment). Completed
    rows -- and their posted GL -- are never touched.

    Caller convention: call this AFTER the caller has already updated
    Asset.current_value/purchase_cost via db_set (Asset Quantity
    Adjustment does this itself), then pass that same new current_value
    in as `new_opening_value` -- or omit it to fall back to reading
    asset.current_value off the doc as re-fetched here. An explicit value
    is preferred so this function never has to guess whether a caller's
    db_set has actually landed on a stale in-memory copy of the doc.

    Returns True if any Pending row's figures actually changed, False if
    there was nothing to re-derive (no schedule at all, or every row
    already Completed -- the schedule is done, "future rows" is empty by
    definition).
    """
    asset = frappe.get_doc("Asset", asset_name)
    rows = list(asset.depreciation_schedule or [])
    if not rows:
        return False

    rows.sort(key=lambda r: (r.period_no or r.year or 0))
    pending_rows = [r for r in rows if r.status == "Pending"]
    if not pending_rows:
        return False

    opening_value = flt(new_opening_value) if new_opening_value is not None else flt(asset.current_value)

    # recompute_pending_rows is pure/DB-free -- feed it plain dicts, not
    # live child docs, then write the results back explicitly below.
    row_dicts = [
        {
            "opening_value": flt(r.opening_value),
            "depreciation_amount": flt(r.depreciation_amount),
            "closing_value": flt(r.closing_value),
        }
        for r in pending_rows
    ]
    recompute_pending_rows(
        row_dicts,
        opening_value=opening_value,
        salvage=flt(asset.salvage_value),
        method=asset.depreciation_method or "Straight Line",
    )

    changed = False
    for row, values in zip(pending_rows, row_dicts):
        if (
            abs(flt(row.opening_value) - values["opening_value"]) > 0.005
            or abs(flt(row.depreciation_amount) - values["depreciation_amount"]) > 0.005
            or abs(flt(row.closing_value) - values["closing_value"]) > 0.005
        ):
            row.db_set("opening_value", values["opening_value"], update_modified=False)
            row.db_set("depreciation_amount", values["depreciation_amount"], update_modified=False)
            row.db_set("closing_value", values["closing_value"], update_modified=False)
            changed = True

    if changed:
        frappe.msgprint(
            _(
                "Re-derived {0} remaining depreciation period(s) on {1} against the "
                "updated book value of {2}."
            ).format(len(pending_rows), asset.name, opening_value),
            indicator="blue",
            alert=True,
        )

    return changed