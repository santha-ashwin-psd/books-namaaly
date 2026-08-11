from __future__ import annotations
"""
Asset Quantity Adjustment GL — Phase 3 (final piece) of the "self-contained
fixed-asset lifecycle" build-out.

Covers a partial physical write-off of a multi-unit Asset record -- e.g.
"10 of 20 units damaged beyond repair" -- where the Asset itself is not
being fully disposed (see Asset Disposal for that), just reduced in
quantity and value.

This app treats a multi-unit purchase as a single Asset record: one
aggregate qty, one aggregate purchase_cost, one aggregate current_value,
and a depreciation schedule built on that aggregate cost basis (see
depreciation_engine.py). There is no per-unit Asset row to delete when
some units are destroyed, so writing off N of M units means proportionally
shrinking the aggregate figures instead:

    proportion = damaged_qty / qty_before
    write_off_purchase_cost              = purchase_cost_before * proportion
    accumulated_depreciation_before      = purchase_cost_before - current_value_before
    write_off_accumulated_depreciation   = accumulated_depreciation_before * proportion
    write_off_net_book_value             = write_off_purchase_cost - write_off_accumulated_depreciation

GL posting mirrors Asset Disposal's "Scrap" path (same three accounts,
same balancing identity: accumulated_depreciation + loss == cost removed),
just for the proportional slice instead of the whole asset:

    DR Accumulated Depreciation Account   write_off_accumulated_depreciation
    DR Loss Account (P&L)                 write_off_net_book_value
    CR Fixed Asset Account                write_off_purchase_cost

is_existing_asset assets skip the GL entry for the same reason
post_asset_capitalization/post_disposal_gl do: they never had a
capitalization entry posted through this app, so there's no Fixed Asset
Account balance here to relieve. Their qty/value are still adjusted.

Phase 5: after the qty/cost/current_value shrink is posted below, the
asset's remaining Pending depreciation schedule rows are re-derived
against the new, smaller current_value via
depreciation_posting.rederive_schedule() -- see that function's
docstring for exactly what "re-derived" means (amounts only; period
dates/boundaries are preserved). Already-Completed rows and their posted
GL are never touched.

A write-off is only ever partial by design: damaged_qty must be strictly
less than the asset's qty. Writing off the entire remaining quantity
should go through Asset Disposal instead, which carries its own status
transition (Scrapped/Sold) and Fixed Asset Account closure semantics that
this doctype does not attempt to duplicate.
"""

import frappe
from frappe import _
from frappe.utils import flt

from zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry import (
	make_gl_entries,
)
from zoho_books_clone.assets.asset_gl import get_category_accounts
from zoho_books_clone.assets.depreciation_posting import rederive_schedule

_VOUCHER_TYPE = "Asset Quantity Adjustment"


def validate_quantity_adjustment_setup(doc) -> None:
	if not doc.asset:
		return

	asset = frappe.db.get_value(
		"Asset",
		doc.asset,
		["docstatus", "status", "asset_category", "company", "is_existing_asset", "qty", "purchase_cost", "current_value"],
		as_dict=True,
	)
	if not asset:
		frappe.throw(_("Asset {0} not found.").format(doc.asset))

	if asset.docstatus != 1:
		frappe.throw(_("Asset {0} must be submitted before its quantity can be adjusted.").format(doc.asset))

	if asset.status in ("Scrapped", "Sold"):
		frappe.throw(_("Asset {0} has already been disposed ({1}) -- its quantity can no longer be adjusted.").format(doc.asset, asset.status))

	if doc.damaged_qty is None or flt(doc.damaged_qty) <= 0:
		frappe.throw(_("Quantity Written Off must be greater than zero."))

	if flt(doc.damaged_qty) >= flt(asset.qty):
		frappe.throw(
			_(
				"Quantity Written Off ({0}) must be less than the asset's current Qty ({1}). "
				"Use Asset Disposal instead if the entire remaining quantity is gone."
			).format(flt(doc.damaged_qty), flt(asset.qty))
		)

	if not doc.reason:
		frappe.throw(_("Reason is required."))

	if not doc.loss_account:
		frappe.throw(_("Loss on Damaged/Written-off Assets Account is required."))

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


def post_quantity_adjustment_gl(doc) -> None:
	if doc.gl_posted:
		return

	validate_quantity_adjustment_setup(doc)

	asset = frappe.get_doc("Asset", doc.asset)
	qty_before = flt(asset.qty)
	purchase_cost_before = flt(asset.purchase_cost)
	current_value_before = flt(asset.current_value)
	damaged_qty = flt(doc.damaged_qty)

	proportion = (damaged_qty / qty_before) if qty_before else 0.0
	write_off_purchase_cost = round(purchase_cost_before * proportion, 2)
	accumulated_depreciation_before = purchase_cost_before - current_value_before
	write_off_accumulated_depreciation = round(accumulated_depreciation_before * proportion, 2)
	write_off_net_book_value = round(write_off_purchase_cost - write_off_accumulated_depreciation, 2)

	qty_after = qty_before - damaged_qty
	purchase_cost_after = round(purchase_cost_before - write_off_purchase_cost, 2)
	current_value_after = round(current_value_before - write_off_net_book_value, 2)

	doc.qty_before = qty_before
	doc.qty_after = qty_after
	doc.purchase_cost_before = purchase_cost_before
	doc.current_value_before = current_value_before
	doc.write_off_purchase_cost = write_off_purchase_cost
	doc.write_off_accumulated_depreciation = write_off_accumulated_depreciation
	doc.write_off_net_book_value = write_off_net_book_value
	doc.purchase_cost_after = purchase_cost_after
	doc.current_value_after = current_value_after

	if not asset.is_existing_asset and write_off_purchase_cost > 0:
		accounts = get_category_accounts(asset.asset_category, asset.company)
		remarks = (
			f"Asset quantity write-off ({damaged_qty} of {qty_before} units) "
			f"\u2014 {asset.asset_name} ({asset.name}), {doc.name}"
		)

		gl_map = []
		if write_off_accumulated_depreciation > 0:
			gl_map.append({
				"account": accounts["accumulated_depreciation_account"],
				"debit": write_off_accumulated_depreciation,
				"credit": 0,
				"voucher_type": _VOUCHER_TYPE,
				"voucher_no": doc.name,
				"posting_date": doc.adjustment_date,
				"company": asset.company,
				"remarks": remarks,
			})
		if write_off_net_book_value > 0.01:
			gl_map.append({
				"account": doc.loss_account,
				"debit": write_off_net_book_value,
				"credit": 0,
				"voucher_type": _VOUCHER_TYPE,
				"voucher_no": doc.name,
				"posting_date": doc.adjustment_date,
				"company": asset.company,
				"remarks": remarks,
			})
		elif write_off_net_book_value < -0.01:
			# Guard only: would mean accumulated depreciation exceeds the
			# proportional cost removed, which shouldn't happen given the
			# invariant accumulated_depreciation_before <= purchase_cost_before.
			gl_map.append({
				"account": doc.loss_account,
				"debit": 0,
				"credit": -write_off_net_book_value,
				"voucher_type": _VOUCHER_TYPE,
				"voucher_no": doc.name,
				"posting_date": doc.adjustment_date,
				"company": asset.company,
				"remarks": remarks,
			})
		gl_map.append({
			"account": accounts["fixed_asset_account"],
			"debit": 0,
			"credit": write_off_purchase_cost,
			"voucher_type": _VOUCHER_TYPE,
			"voucher_no": doc.name,
			"posting_date": doc.adjustment_date,
			"company": asset.company,
			"remarks": remarks,
		})

		make_gl_entries(gl_map)

	doc.db_set("gl_posted", 1, update_modified=False)
	doc.db_set("qty_before", qty_before, update_modified=False)
	doc.db_set("qty_after", qty_after, update_modified=False)
	doc.db_set("purchase_cost_before", purchase_cost_before, update_modified=False)
	doc.db_set("current_value_before", current_value_before, update_modified=False)
	doc.db_set("write_off_purchase_cost", write_off_purchase_cost, update_modified=False)
	doc.db_set("write_off_accumulated_depreciation", write_off_accumulated_depreciation, update_modified=False)
	doc.db_set("write_off_net_book_value", write_off_net_book_value, update_modified=False)
	doc.db_set("purchase_cost_after", purchase_cost_after, update_modified=False)
	doc.db_set("current_value_after", current_value_after, update_modified=False)

	asset.db_set("qty", qty_after, update_modified=False)
	asset.db_set("purchase_cost", purchase_cost_after, update_modified=False)
	asset.db_set("current_value", current_value_after, update_modified=False)

	rederive_schedule(asset.name, new_opening_value=current_value_after)


def reverse_quantity_adjustment_gl(doc) -> None:
	"""Best-effort reversal on cancel -- never blocks the cancel itself
	on a GL-side failure, same posture as the other Asset GL modules."""
	if not doc.gl_posted:
		return
	try:
		asset = frappe.get_doc("Asset", doc.asset)

		if not asset.is_existing_asset and flt(doc.write_off_purchase_cost):
			make_gl_entries(
				[{"voucher_type": _VOUCHER_TYPE, "voucher_no": doc.name}],
				cancel=True,
			)

		asset.db_set("qty", doc.qty_before, update_modified=False)
		asset.db_set("purchase_cost", doc.purchase_cost_before, update_modified=False)
		asset.db_set("current_value", doc.current_value_before, update_modified=False)
		doc.db_set("gl_posted", 0, update_modified=False)

		rederive_schedule(asset.name, new_opening_value=doc.current_value_before)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Asset quantity adjustment GL reversal failed")