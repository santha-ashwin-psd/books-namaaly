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

        if flt(self.packing_operating_cost) < 0:
            frappe.throw(_("Packing Operating Cost cannot be negative."))

        if self.source_work_order:
            if self.work_order and self.source_work_order == self.work_order:
                frappe.throw(_(
                    "Sourced From (Bulk WO) cannot be the same Work Order this "
                    "Packing Slip was created from."
                ))
            swo = frappe.db.get_value(
                "Work Order", self.source_work_order,
                ["docstatus", "production_item", "company", "bom"], as_dict=True
            )
            if not swo:
                frappe.throw(_("Source Work Order {0} does not exist.").format(self.source_work_order))
            if swo.docstatus != 1:
                frappe.throw(_(
                    "Source Work Order {0} must be submitted."
                ).format(self.source_work_order))
            if self.company and swo.company and swo.company != self.company:
                frappe.throw(_(
                    "Source Work Order {0} belongs to a different company."
                ).format(self.source_work_order))
            if swo.bom:
                source_bom_type = frappe.db.get_value("BOM", swo.bom, "bom_type")
                if source_bom_type == "Packing":
                    frappe.throw(_(
                        "Source Work Order {0} itself runs on a Packing BOM. 'Sourced "
                        "From' must point to the Manufacturing/Sub-Assembly Work Order "
                        "that produced the bulk item, not another Packing Slip's Work Order."
                    ).format(self.source_work_order))
            if self.bom:
                bulk_item = frappe.db.get_value("BOM", self.bom, "bulk_item")
                if bulk_item and swo.production_item != bulk_item:
                    frappe.throw(_(
                        "Source Work Order {0} produces {1}, but this Packing Slip's "
                        "BOM expects bulk item {2}."
                    ).format(self.source_work_order, swo.production_item, bulk_item))

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