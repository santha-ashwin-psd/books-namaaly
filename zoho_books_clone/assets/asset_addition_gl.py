from __future__ import annotations
"""
Asset Addition — Phase 4 of the "self-contained fixed-asset lifecycle"
build-out. Covers replacing damaged/lost/stolen units with new ones,
either paid (a real purchase) or free (warranty/insurance honored in
kind, supplier goodwill).

Design decision (locked in chat before this was built): a replacement
does NOT blend qty/cost onto the original Asset record. It spins off a
brand-new Asset record with its own depreciation schedule, linked back
via Asset.replacement_of. Rationale: the replacement units were very
likely acquired on a different date, at a different cost, and the
original Asset's depreciation schedule may already be partway through
its life (or fully depreciated) -- forcing a blended average cost onto
that existing schedule would require re-deriving it mid-flight (exactly
the kind of live-schedule surgery this app deliberately defers -- see
depreciation_engine.py / asset_gl.py headers). A fresh Asset record with
its own clean schedule sidesteps all of that, at the cost of the asset
register showing the replacement as a separate line rather than a
qty bump on the original. Asset.replacement_of is the audit trail that
ties them back together.

This module does NOT duplicate the capitalization/tax GL logic that
already lives in asset_gl.py -- it reuses it wholesale by constructing a
real, ordinary Asset document and calling .insert()/.submit() on it:

  Paid Replacement:
    is_existing_asset = 0, taxable_value/taxes/credit_account carried
    over from this doc. Asset.calculate_totals() and
    asset_gl.post_asset_capitalization() run exactly as they would for
    any other new Asset purchase -- same ITC-eligible/blocked-credit tax
    split, same DR Fixed Asset (or CWIP) / CR Credit Account posting,
    same account validation and error messages. Nothing about that path
    is re-implemented here.

  Free Replacement (Warranty/Insurance):
    is_existing_asset = 1, purchase_cost/taxable_value = 0. This flag
    already means "not capitalized through this app's own GL" for every
    other module (asset_gl, asset_disposal_gl, depreciation_posting) --
    it's a natural fit for "zero GL impact, just restore qty", not a
    repurposing of the flag's meaning. A zero-cost asset also can't
    build a depreciation schedule (depreciation_engine.build_schedule
    requires cost > 0), which is correct: there's no cost basis to
    depreciate.

Asset Addition's own "posting" is therefore just orchestration: create
the child Asset, submit it, record the link both ways. Reversal on
cancel is a real document cancel of that child Asset (not a GL-entry
reversal like the other modules), and is deliberately NOT best-effort --
if the replacement Asset has already had depreciation posted or been
disposed, the Addition refuses to cancel rather than leaving orphaned
state.
"""

import frappe
from frappe import _
from frappe.utils import flt

from zoho_books_clone.assets.asset_gl import get_category_accounts

_PAID = "Paid Replacement"
_FREE = "Free Replacement (Warranty/Insurance)"


def calculate_addition_totals(doc) -> None:
	"""Mirrors Asset.calculate_totals() for the Paid Replacement case only
	-- same ITC-eligible/blocked-credit tax split. A Free Replacement is
	always zero cost, so its totals are just zeroed out here rather than
	left stale from a prior edit (e.g. addition_type switched after tax
	rows were entered)."""
	if doc.addition_type != _PAID:
		doc.taxable_value = 0
		doc.total_tax = 0
		doc.purchase_cost = 0
		doc.grand_total = 0
		return

	doc.taxable_value = flt(doc.taxable_value)

	eligible_tax = 0.0
	non_eligible_tax = 0.0
	for row in (doc.taxes or []):
		row.amount = round(doc.taxable_value * flt(row.rate) / 100, 2)
		if row.is_itc_eligible:
			eligible_tax += row.amount
		else:
			non_eligible_tax += row.amount

	doc.total_tax = round(eligible_tax + non_eligible_tax, 2)
	doc.purchase_cost = round(doc.taxable_value + non_eligible_tax, 2)
	doc.grand_total = round(doc.taxable_value + doc.total_tax, 2)


def validate_addition_setup(doc) -> None:
	if not doc.original_asset:
		return

	original = frappe.db.get_value(
		"Asset",
		doc.original_asset,
		["docstatus", "asset_category", "company"],
		as_dict=True,
	)
	if not original:
		frappe.throw(_("Asset {0} not found.").format(doc.original_asset))

	if original.docstatus != 1:
		frappe.throw(_("Original Asset {0} must be submitted first.").format(doc.original_asset))

	if doc.qty is None or flt(doc.qty) <= 0:
		frappe.throw(_("Replacement Qty must be greater than zero."))

	if not doc.reason:
		frappe.throw(_("Reason is required."))

	if doc.addition_type not in (_PAID, _FREE):
		frappe.throw(_("Addition Type must be either {0} or {1}.").format(_PAID, _FREE))

	if doc.quantity_adjustment:
		linked_asset = frappe.db.get_value("Asset Quantity Adjustment", doc.quantity_adjustment, "asset")
		if linked_asset != doc.original_asset:
			frappe.throw(
				_("Quantity Adjustment {0} is against Asset {1}, not {2}.").format(
					doc.quantity_adjustment, linked_asset, doc.original_asset
				)
			)

	if doc.addition_type == _PAID:
		if flt(doc.taxable_value) <= 0:
			frappe.throw(_("Taxable Value must be greater than zero for a Paid Replacement."))
		if not doc.credit_account:
			frappe.throw(_("Credit Account (Payable / Bank / Cash) is required for a Paid Replacement."))

		accounts = get_category_accounts(original.asset_category, original.company)
		if not accounts.get("fixed_asset_account"):
			frappe.throw(
				_(
					"Asset Category {0} has no Fixed Asset Account configured for company {1}. "
					"Add a row under Asset Category \u2192 Accounting (per Company) first."
				).format(frappe.bold(original.asset_category), frappe.bold(original.company))
			)


def post_addition_gl(doc) -> None:
	"""Creates and submits the replacement Asset. Idempotent: doc.new_asset
	being set is the guard, same role gl_posted plays elsewhere."""
	if doc.new_asset:
		return

	validate_addition_setup(doc)

	original = frappe.get_doc("Asset", doc.original_asset)

	new_asset = frappe.new_doc("Asset")
	new_asset.asset_name = f"{original.asset_name} (Replacement \u2014 {doc.name})"
	new_asset.asset_category = original.asset_category
	new_asset.company = original.company
	new_asset.department = original.department
	new_asset.location = original.location
	new_asset.qty = flt(doc.qty)
	new_asset.purchase_date = doc.addition_date
	new_asset.available_for_use_date = doc.addition_date
	new_asset.depreciation_method = original.depreciation_method
	new_asset.depreciation_posting_frequency = original.depreciation_posting_frequency
	new_asset.useful_life = original.useful_life
	new_asset.salvage_value = original.salvage_value
	new_asset.replacement_of = original.name

	if doc.addition_type == _PAID:
		new_asset.is_existing_asset = 0
		new_asset.taxable_value = flt(doc.taxable_value)
		new_asset.credit_account = doc.credit_account
		new_asset.supplier = doc.supplier
		for row in (doc.taxes or []):
			new_asset.append("taxes", {
				"tax_type": row.tax_type,
				"rate": row.rate,
				"is_itc_eligible": row.is_itc_eligible,
				"account_head": row.account_head,
				"description": row.description,
			})
	else:
		new_asset.is_existing_asset = 1
		new_asset.taxable_value = 0
		new_asset.purchase_cost = 0

	new_asset.insert(ignore_permissions=True)
	new_asset.submit()

	doc.db_set("new_asset", new_asset.name, update_modified=False)
	doc.db_set("purchase_cost", flt(new_asset.purchase_cost), update_modified=False)


def reverse_addition_gl(doc) -> None:
	"""Cancels the replacement Asset this doc created. Deliberately NOT
	best-effort/log-and-continue like the other reverse_*_gl functions:
	failing to cancel a whole child Asset (vs. reversing a couple of GL
	lines) would leave the register in a confusing half-undone state, so
	a block here is surfaced to the user instead of swallowed."""
	if not doc.new_asset:
		return

	new_asset = frappe.get_doc("Asset", doc.new_asset)

	if new_asset.docstatus == 2:
		# Already cancelled independently -- nothing left to do.
		return

	if any(row.status == "Completed" for row in (new_asset.depreciation_schedule or [])):
		frappe.throw(
			_(
				"Cannot cancel {0}: the replacement Asset {1} already has posted depreciation. "
				"Reverse/handle that first, or cancel {1} directly."
			).format(doc.name, new_asset.name)
		)

	if new_asset.status in ("Scrapped", "Sold"):
		frappe.throw(
			_("Cannot cancel {0}: the replacement Asset {1} has already been disposed. Handle it directly instead.").format(
				doc.name, new_asset.name
			)
		)

	new_asset.cancel()