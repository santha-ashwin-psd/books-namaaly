# Copyright (c) 2026
import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document
from zoho_books_clone.db.validators import validate_fiscal_year


class PurchaseReceipt(Document):

    def validate(self):
        # Purchase Receipt is not wired to central_validator, so fiscal year
        # validation must run here.  Block saves into closed or missing periods
        # before any inventory or fulfilment logic runs.
        if self.posting_date and self.company:
            validate_fiscal_year(self.posting_date, self.company)

        if not self.items:
            frappe.throw(_("Purchase Receipt must have at least one item row."))
        for row in self.items:
            if flt(row.qty) <= 0:
                frappe.throw(_("Row {0}: qty must be > 0").format(row.idx))
        self.total_qty = sum(flt(r.qty) for r in self.items)

    def on_submit(self):
        self._adjust_po_received(direction=+1)
        self._release_ordered_qty(direction=-1)    # goods arrived → release "on order"
        self.db_set("status", "Submitted", update_modified=False)

    def on_cancel(self):
        self._adjust_po_received(direction=-1)
        self._release_ordered_qty(direction=+1)    # receipt reversed → restore "on order"
        self.db_set("status", "Cancelled", update_modified=False)

    def _release_ordered_qty(self, direction: int):
        """
        Release (direction=-1) or restore (direction=+1) ordered_qty in Bin
        when goods are received via this Purchase Receipt.

        actual_qty is managed separately by stock_link.py → Stock Entry.
        This method only touches ordered_qty and recalculates projected_qty.
        """
        from zoho_books_clone.inventory.utils import update_bin
        warehouse = getattr(self, "set_warehouse", None) or ""

        for row in self.items:
            wh = getattr(row, "warehouse", None) or warehouse
            if not wh or not row.item_code:
                continue
            is_stock = frappe.db.get_value("Item", row.item_code, "is_stock_item")
            if not is_stock:
                continue
            update_bin(
                item_code=row.item_code,
                warehouse=wh,
                ordered_qty_delta=direction * flt(row.qty),
                company=self.company or "",
            )

    def _adjust_po_received(self, direction: int):
        """Bump (direction=+1) or decrement (-1) received_qty on linked PO rows.

        Mirrors DeliveryNote._adjust_so_delivered: if a row carries an explicit
        po_item link, update that line directly; otherwise fall back to
        matching by item_code against the PO's remaining quantity so receipts
        still work even when the caller didn't set po_item.
        """
        if not self.purchase_order:
            return

        po_items = frappe.db.sql("""
            SELECT name, item_code, qty, received_qty
            FROM `tabPurchase Order Item` WHERE parent=%s ORDER BY idx
        """, (self.purchase_order,), as_dict=True)
        by_code = {}
        for r in po_items:
            by_code.setdefault(r.item_code, []).append(r)

        def _bump(po_item_id, qty):
            cur = flt(frappe.db.get_value("Purchase Order Item", po_item_id, "received_qty"))
            new_qty = max(0.0, cur + direction * flt(qty))
            frappe.db.set_value("Purchase Order Item", po_item_id, "received_qty",
                                new_qty, update_modified=False)

        for row in self.items:
            if row.po_item:
                _bump(row.po_item, row.qty)
                continue
            pool = by_code.get(row.item_code) or []
            remaining = flt(row.qty)
            for po_row in pool:
                if remaining <= 0:
                    break
                available = max(0.0, flt(po_row.qty) - flt(po_row.received_qty))
                if available <= 0 and direction > 0:
                    continue
                take = min(available, remaining) if direction > 0 else min(flt(po_row.received_qty), remaining)
                if take <= 0:
                    continue
                _bump(po_row.name, take)
                po_row.received_qty = flt(po_row.received_qty) + direction * take
                remaining -= take
        try:
            from zoho_books_clone.api.docs import _po_status_from_fulfillment
            new_status = _po_status_from_fulfillment(self.purchase_order)
            frappe.db.set_value("Purchase Order", self.purchase_order, "status",
                                new_status, update_modified=True)
        except Exception:
            pass