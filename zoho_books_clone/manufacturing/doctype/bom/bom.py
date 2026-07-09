import frappe
from frappe import _
from frappe.model.document import Document


class BOM(Document):
    def validate(self):
        if not self.items or len(self.items) == 0:
            frappe.throw(_("BOM must have at least one Raw Material row before it can be saved."))

        # Carry the version number forward on amendment so it reads 2, 3, 4...
        # instead of resetting to 1 (amended_from is only set on the copy Frappe
        # creates when you amend a cancelled BOM).
        if self.amended_from and not self.is_new():
            pass  # version already set by set_version_on_amend at insert time

    def before_insert(self):
        if self.amended_from:
            prev_version = frappe.db.get_value("BOM", self.amended_from, "bom_version") or 1
            self.bom_version = int(prev_version) + 1
            # A new revision starts as the active one; the row it amends should
            # not keep competing as "default" once superseded.
            self.is_active = 1

    def on_submit(self):
        # Only one submitted, active BOM should be flagged default per item —
        # supersede any earlier default BOM for the same production item.
        if self.is_default:
            frappe.db.sql(
                """UPDATE `tabBOM` SET is_default = 0
                   WHERE item = %s AND name != %s AND docstatus = 1""",
                (self.item, self.name),
            )
        # The BOM this one amends is no longer the active revision.
        if self.amended_from:
            frappe.db.set_value("BOM", self.amended_from, "is_active", 0)

    def on_cancel(self):
        self.is_active = 0
        self.db_set("is_active", 0)