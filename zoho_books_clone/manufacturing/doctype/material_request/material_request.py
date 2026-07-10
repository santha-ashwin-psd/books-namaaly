import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate


class MaterialRequest(Document):
    def validate(self):
        if not self.posting_date:
            self.posting_date = nowdate()
        if not self.items:
            frappe.throw(_("Material Request must have at least one item."))
        for row in self.items:
            if not row.required_qty or row.required_qty <= 0:
                frappe.throw(_("Row for {0}: Required Qty must be greater than zero.").format(row.item_code))

    def on_submit(self):
        self.db_set("status", "Submitted")

    def on_cancel(self):
        self.db_set("status", "Cancelled")
