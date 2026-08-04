import frappe
from frappe.model.document import Document

from zoho_books_clone.assets.asset_repair_gl import (
    post_repair_gl,
    reverse_repair_gl,
    validate_repair_setup,
)


class AssetRepair(Document):
    # TODO: Asset.status In Maintenance / Out of Order are not set anywhere.
    # Deliberately skipped -- this doctype logs a repair as a single
    # retroactive event (repair_date + cost, submitted once it's already
    # done), not a start/end pair of events. There's no "asset went down"
    # trigger to flip status to In Maintenance and no "asset came back"
    # trigger to flip it back. Revisit if/when this doctype (or a new one)
    # gains an actual open/close workflow for an outage.

    def validate(self):
        if not self.company and self.asset:
            self.company = frappe.db.get_value("Asset", self.asset, "company")
        validate_repair_setup(self)

    def on_submit(self):
        post_repair_gl(self)

    def on_cancel(self):
        reverse_repair_gl(self)