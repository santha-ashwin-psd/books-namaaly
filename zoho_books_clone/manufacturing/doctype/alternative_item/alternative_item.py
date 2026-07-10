import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class AlternativeItem(Document):
    def validate(self):
        if self.item_code == self.alternative_item_code:
            frappe.throw(_("Original Item and Alternative Item cannot be the same."))
        if flt(self.conversion_factor) <= 0:
            frappe.throw(_("Conversion Factor must be greater than zero."))
