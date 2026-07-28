import frappe
from frappe.model.document import Document

from zoho_books_clone.assets.asset_disposal_gl import (
    post_disposal_gl,
    reverse_disposal_gl,
    validate_disposal_setup,
)


class AssetDisposal(Document):

    def validate(self):
        if not self.company and self.asset:
            self.company = frappe.db.get_value("Asset", self.asset, "company")
        validate_disposal_setup(self)

    def on_submit(self):
        post_disposal_gl(self)

    def on_cancel(self):
        reverse_disposal_gl(self)