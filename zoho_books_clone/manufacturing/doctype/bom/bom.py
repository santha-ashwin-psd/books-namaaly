import frappe
from frappe import _
from frappe.model.document import Document


class BOM(Document):
    def validate(self):
        self.bom_type = self.bom_type or "Manufacturing"

        if self.bom_type == "Packing":
            self.validate_packing_bom()
        else:
            self.validate_manufacturing_bom()

        # Carry the version number forward on amendment so it reads 2, 3, 4...
        # instead of resetting to 1 (amended_from is only set on the copy Frappe
        # creates when you amend a cancelled BOM).
        if self.amended_from and not self.is_new():
            pass  # version already set by set_version_on_amend at insert time

    def validate_manufacturing_bom(self):
        if not self.items or len(self.items) == 0:
            frappe.throw(_("BOM must have at least one Raw Material row before it can be saved."))

    def validate_packing_bom(self):
        if not self.bulk_item:
            frappe.throw(_("Packing BOM requires a Bulk Item to consume from."))
        if not self.bulk_qty_per_unit or self.bulk_qty_per_unit <= 0:
            frappe.throw(_("Packing BOM requires a positive Bulk Qty Consumed per Packed Unit."))
        if self.bulk_item == self.item:
            frappe.throw(_("Bulk Item cannot be the same as the Production Item being packed."))
        if not self.packing_items or len(self.packing_items) == 0:
            frappe.throw(_("Packing BOM must have at least one Packing Material row before it can be saved."))
        # Packing BOMs don't consume raw materials or run operations directly —
        # those belong to the Manufacturing BOM that produced the bulk item.
        if self.items:
            frappe.throw(_("Packing BOM should not have Raw Materials rows. Use the Packing Materials table instead."))
        if self.operations:
            frappe.throw(_("Packing BOM should not have Operations. Operations belong to the Manufacturing BOM."))

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
                   WHERE item = %s AND bom_type = %s AND name != %s AND docstatus = 1""",
                (self.item, self.bom_type, self.name),
            )
        # The BOM this one amends is no longer the active revision.
        if self.amended_from:
            frappe.db.set_value("BOM", self.amended_from, "is_active", 0)

    def on_cancel(self):
        self.is_active = 0
        self.db_set("is_active", 0)