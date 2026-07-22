# Copyright (c) 2026
import frappe
from frappe.utils import flt
from frappe.model.document import Document
from zoho_books_clone.db.validators import validate_fiscal_year


class PurchaseOrder(Document):

    def validate(self):
        # Mirror SalesOrder: stamp fiscal_year so downstream GL and reports
        # can group by year without an extra query.
        if self.transaction_date and self.company:
            try:
                self.fiscal_year = validate_fiscal_year(self.transaction_date, self.company)
            except frappe.ValidationError:
                raise   # period lock / no-open-FY — must not be swallowed
            except Exception:
                self.fiscal_year = ""   # only suppress unexpected errors (e.g. table missing on install)
        self._calculate_totals()

    def _calculate_totals(self):
        for item in (self.items or []):
            item.amount = round(flt(item.qty) * flt(item.rate), 2)
        net = sum(flt(i.amount) for i in (self.items or []))
        for tax in (self.taxes or []):
            if flt(tax.rate) and not flt(tax.tax_amount):
                tax.tax_amount = round(net * flt(tax.rate) / 100, 2)
        tax_total = sum(flt(t.tax_amount) for t in (self.taxes or []))
        self.net_total   = round(net, 2)
        self.total_tax   = round(tax_total, 2)
        self.grand_total = round(net + tax_total, 2)

    def on_submit(self):
        self._update_ordered_qty(direction=+1)

    def on_cancel(self):
        self._update_ordered_qty(direction=-1)

    def _update_ordered_qty(self, direction: int):
        """Increase (submit) or decrease (cancel) ordered_qty in Bin for each PO line.

        On submit  → add the full line qty to ordered_qty.
        On cancel  → remove only what is still on-order, i.e. qty that has NOT yet
                     been billed.  Billed qty was already released by
                     PurchaseInvoice._release_ordered_qty when the PI was submitted,
                     so restoring the full row.qty would over-deflate ordered_qty.
        """
        from zoho_books_clone.inventory.utils import update_bin
        warehouse = getattr(self, "set_warehouse", None) or ""
        for row in (self.items or []):
            wh = getattr(row, "warehouse", None) or warehouse
            if not wh or not row.item_code:
                continue
            is_stock = frappe.db.get_value("Item", row.item_code, "is_stock_item")
            if not is_stock:
                continue
            # Bin.ordered_qty is tracked in stock UOM (same as actual_qty/
            # reserved_qty on the same Bin) — use qty_in_stock_uom, not the
            # raw purchase-UOM qty, or a "10 Box" line (stock_uom Kg,
            # conversion_factor 10) would only add 10 instead of 100 and
            # silently desync projected_qty from reality.
            from zoho_books_clone.inventory.utils import get_conversion_factor
            factor = flt(get_conversion_factor(row.item_code, getattr(row, "uom", None)) or 1)
            row_qty = flt(row.qty) * factor
            if direction == -1:
                # Cancel: only remove qty still on-order (not yet billed).
                billed = flt(getattr(row, "billed_qty", 0)) * factor
                still_ordered = max(0.0, row_qty - billed)
                if still_ordered <= 0:
                    continue
                delta = -still_ordered
            else:
                delta = row_qty
            update_bin(
                item_code=row.item_code,
                warehouse=wh,
                ordered_qty_delta=delta,
                company=self.company or "",
            )