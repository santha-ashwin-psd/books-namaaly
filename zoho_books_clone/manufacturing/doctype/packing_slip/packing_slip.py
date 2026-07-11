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
        if not self.is_new():
            prev_status, prev_stock_entry = frappe.db.get_value(
                "Packing Slip", self.name, ["status", "stock_entry"]
            )
            if prev_status == "Cancelled":
                frappe.throw(_("This Packing Slip is cancelled and cannot be edited."))
            if prev_stock_entry:
                # Stock has already been consumed/received for this slip via
                # post_packing_consumption. Any further edit here (qty,
                # warehouses, items) would silently drift from what was
                # actually posted to the stock ledger, so the slip is locked
                # once stock_entry is set -- same treatment as Cancelled.
                frappe.throw(_(
                    "Stock has already been posted for this Packing Slip ({0}) "
                    "and it can no longer be edited."
                ).format(prev_stock_entry))

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
        if all_packed:
            new_status = "Packed"
        elif any_packed:
            new_status = "In Progress"
        else:
            new_status = "Draft"
        if new_status != self.status:
            self.db_set("status", new_status)