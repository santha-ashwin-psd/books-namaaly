import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate


class PackingSlip(Document):
    def before_insert(self):
        """Derive company from the parent Work Order for multi-tenant isolation."""
        if not self.company and self.work_order:
            self.company = frappe.db.get_value("Work Order", self.work_order, "company") or ""

    def validate(self):
        if not self.packing_date:
            self.packing_date = nowdate()
        if not self.items:
            frappe.throw(_("Packing Slip must have at least one item."))
        for row in self.items:
            if flt(row.packed_qty) > flt(row.required_qty):
                frappe.throw(_(
                    "Row for {0}: Packed Qty ({1}) cannot exceed Required Qty ({2})."
                ).format(row.item_code, row.packed_qty, row.required_qty))

    def on_update(self):
        self._sync_status()

    def _sync_status(self):
        """Auto-advance status based on packed quantities."""
        if self.status == "Cancelled":
            return
        all_packed = all(
            flt(r.packed_qty) >= flt(r.required_qty) - 0.0001
            for r in (self.items or [])
        )
        any_packed = any(flt(r.packed_qty) > 0.0001 for r in (self.items or []))
        new_status = self.status
        if all_packed:
            new_status = "Packed"
        elif any_packed:
            new_status = "In Progress"
        if new_status != self.status:
            self.db_set("status", new_status)
