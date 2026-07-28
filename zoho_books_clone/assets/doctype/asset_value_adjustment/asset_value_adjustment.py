import frappe
from frappe.model.document import Document

from zoho_books_clone.assets.asset_value_adjustment_gl import (
    post_adjustment_gl,
    reverse_adjustment_gl,
    validate_adjustment_setup,
)


class AssetValueAdjustment(Document):

    def validate(self):
        if not self.company and self.asset:
            self.company = frappe.db.get_value("Asset", self.asset, "company")
        validate_adjustment_setup(self)

    def on_submit(self):
        post_adjustment_gl(self)

    def on_cancel(self):
        reverse_adjustment_gl(self)