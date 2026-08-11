import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document

from zoho_books_clone.assets.asset_gl import (
    post_asset_capitalization,
    reverse_asset_capitalization,
    validate_capitalization_setup,
)
from zoho_books_clone.assets.depreciation_engine import build_schedule

class Asset(Document):

    def validate(self):
        if not (self.asset_name or "").strip():
            frappe.throw(_("Asset Name is required."))
        if not self.asset_category:
            frappe.throw(_("Asset Category is required."))
        if not self.qty:
            self.qty = 1
        self.calculate_totals()
        self.generate_depreciation_schedule()
        if self.docstatus == 1:
            # Only enforce full capitalization setup (Fixed Asset Account,
            # GST Input Account if needed, Credit Account) at submit time.
            # validate() also runs on every plain Draft save -- Frappe sets
            # docstatus=1 before calling validate() during doc.submit(), so
            # this still fires before on_submit()/post_asset_capitalization,
            # just no longer blocks saving an incomplete Draft.
            validate_capitalization_setup(self)

    def calculate_totals(self):
        """Mirrors PurchaseInvoice.calculate_totals(): tax lines are
        calculated on taxable_value, then split by is_itc_eligible —
        eligible tax is claimable input credit (not part of the asset's
        book value); non-eligible tax is a blocked credit that gets
        folded into the capitalized Purchase Cost instead. Existing
        assets (is_existing_asset) and assets with no tax lines behave
        exactly as before this field was added.
        """
        if self.is_existing_asset:
            # Legacy/opening assets: purchase_cost is whatever was typed
            # in directly, matching pre-tax-schema behaviour. Don't
            # overwrite it or force taxable_value/tax bookkeeping on
            # something that isn't being capitalized through this doctype.
            self.purchase_cost = flt(self.purchase_cost)
            self.taxable_value = 0
            self.total_tax = 0
            self.grand_total = self.purchase_cost
            self.taxes = []
            if self.purchase_cost <= 0:
                frappe.throw(_("Purchase Cost must be greater than zero."))
            return

        self.taxable_value = flt(self.taxable_value)
        if not self.taxable_value and self.purchase_cost and not (self.taxes or []):
            # Backward compatibility: a record saved before this field
            # existed (or one where the user is still typing straight
            # into Purchase Cost with no tax lines) is treated as
            # taxable_value == purchase_cost, tax = 0.
            self.taxable_value = flt(self.purchase_cost)

        eligible_tax = 0.0
        non_eligible_tax = 0.0
        for row in (self.taxes or []):
            if flt(row.rate) < 0:
                frappe.throw(_("Tax rate cannot be negative (row: {0}).").format(row.tax_type or row.idx))
            row.amount = round(self.taxable_value * flt(row.rate) / 100, 2)
            if row.is_itc_eligible:
                eligible_tax += row.amount
            else:
                non_eligible_tax += row.amount

        self.total_tax = round(eligible_tax + non_eligible_tax, 2)
        self.purchase_cost = round(self.taxable_value + non_eligible_tax, 2)
        self.grand_total = round(self.taxable_value + self.total_tax, 2)

        if self.purchase_cost <= 0 and not self.is_existing_asset:
            frappe.throw(_("Taxable Value must be greater than zero."))

    def on_submit(self):
        # Nothing set this before -- the old free-text status dropdown was
        # the only thing that ever touched it. Depreciation posting later
        # moves this on to Partially/Fully Depreciated, and Asset Disposal
        # moves it to Scrapped/Sold; this is just the initial value.
        self.status = "Submitted"
        post_asset_capitalization(self)

    def on_cancel(self):
        reverse_asset_capitalization(self)

    def generate_depreciation_schedule(self):
        # Regenerating a schedule after any period has already been posted
        # would silently discard the posted GL history recorded on those
        # rows (see depreciation_posting.py). Once a schedule has live
        # postings, further edits to the asset's depreciation inputs
        # (method/frequency/life/salvage) must not blow that away here.
        if any(
            row.status == "Completed" for row in (self.depreciation_schedule or [])
        ):
            return

        self.depreciation_schedule = []

        rows = build_schedule(self)
        for row in rows:
            self.append("depreciation_schedule", row)

        self.current_value = self.purchase_cost if rows else self.current_value