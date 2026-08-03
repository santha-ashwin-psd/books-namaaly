# Copyright (c) 2026
import frappe
from frappe.utils import flt
from frappe.model.document import Document
from zoho_books_clone.db.validators import validate_fiscal_year


class SalesOrder(Document):

    def validate(self):
        self._check_fiscal_lock()
        self._calculate_totals()

    def _check_fiscal_lock(self):
        if self.transaction_date and self.company:
            try:
                self.fiscal_year = validate_fiscal_year(self.transaction_date, self.company)
            except Exception:
                raise  # surface lock/closed-year errors; ignore only missing FY on draft

    def _calculate_totals(self):
        for item in (self.items or []):
            base = round(flt(item.qty) * flt(item.rate), 2)
            item.discount_percentage = flt(item.discount_percentage)
            if item.discount_percentage:
                item.discount_amount = round(base * item.discount_percentage / 100, 2)
            else:
                item.discount_amount = flt(item.discount_amount)
            item.amount = round(base - item.discount_amount, 2)
        net = sum(flt(i.amount) for i in (self.items or []))
        for tax in (self.taxes or []):
            if flt(tax.rate) and not flt(tax.tax_amount):
                tax.tax_amount = round(net * flt(tax.rate) / 100, 2)
        tax_total = sum(flt(t.tax_amount) for t in (self.taxes or []))
        self.net_total   = round(net, 2)
        self.total_tax   = round(tax_total, 2)
        self.grand_total = round(net + tax_total, 2)

    def on_submit(self):
        self._update_reserved_qty(direction=+1)

    def on_cancel(self):
        self._update_reserved_qty(direction=-1)

    def _update_reserved_qty(self, direction: int):
        from zoho_books_clone.inventory.utils import update_bin
        warehouse = getattr(self, "set_warehouse", None) or ""
        for row in (self.items or []):
            wh = getattr(row, "warehouse", None) or warehouse
            if not wh or not row.item_code:
                continue
            is_stock = frappe.db.get_value("Item", row.item_code, "is_stock_item")
            if not is_stock:
                continue
            if direction == -1:
                billed = flt(getattr(row, "billed_qty", 0))
                still_reserved = max(0.0, flt(row.qty) - billed)
                if still_reserved <= 0:
                    continue
                delta = -still_reserved
            else:
                delta = flt(row.qty)
            update_bin(
                item_code=row.item_code,
                warehouse=wh,
                reserved_qty_delta=delta,
                company=self.company or "",
            )