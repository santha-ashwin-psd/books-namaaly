import frappe
from frappe.model.document import Document

from zoho_books_clone.assets.asset_repair_gl import (
    post_repair_gl,
    reverse_repair_gl,
    validate_repair_setup,
)


class AssetRepair(Document):

    def validate(self):
        if not self.company and self.asset:
            self.company = frappe.db.get_value("Asset", self.asset, "company")
        validate_repair_setup(self)

    def on_submit(self):
        post_repair_gl(self)

    def on_cancel(self):
        reverse_repair_gl(self)