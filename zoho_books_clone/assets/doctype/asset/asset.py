import frappe
from frappe.model.document import Document

from zoho_books_clone.assets.asset_gl import (
    post_asset_capitalization,
    reverse_asset_capitalization,
    validate_capitalization_setup,
)
from zoho_books_clone.assets.depreciation_engine import build_schedule

class Asset(Document):

    def validate(self):
        self.generate_depreciation_schedule()
        validate_capitalization_setup(self)

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