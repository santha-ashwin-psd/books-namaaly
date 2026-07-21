import frappe
from frappe import _
from frappe.utils import flt, today, getdate
from frappe.model.document import Document
from zoho_books_clone.accounts.accounting_engine import (
    post_purchase_invoice, reverse_voucher,
)
from zoho_books_clone.db.validators import (
    validate_fiscal_year, validate_account_company, validate_account_type
)


class PurchaseInvoice(Document):

    def validate(self):
        if not self.items:
            frappe.throw(_("Please add at least one item"))
        for item in self.items:
            item.amount = round(flt(item.qty) * flt(item.rate), 2)
        self.calculate_totals()
        self.set_outstanding_amount()
        self.validate_accounts()
        self.set_status()
        if self.posting_date and self.company:
            try:
                self.fiscal_year = validate_fiscal_year(self.posting_date, self.company)
            except Exception:
                self.fiscal_year = ""

    def calculate_totals(self):
        net = sum(flt(i.qty) * flt(i.rate) for i in self.items)
        for tax in (self.taxes or []):
            if flt(tax.rate) and not flt(tax.tax_amount):
                tax.tax_amount = round(net * flt(tax.rate) / 100, 2)
        tax_total = sum(flt(t.tax_amount) for t in (self.taxes or []))
        self.net_total = round(net, 2)
        self.total_tax = round(tax_total, 2)
        # GST rule (Sec 170, CGST Act): the invoice total is rounded off to
        # the nearest rupee, with the adjustment shown as its own "Round
        # Off" line — same treatment as Sales Invoice. Without this, the
        # paise-level remainder between (net + tax) and the whole-rupee
        # grand_total previously had nowhere to go, so the AP credit posted
        # in post_purchase_invoice() (which uses grand_total) could land a
        # few paise off from the debit legs (which use net_total/tax_total)
        # — an out-of-balance GL entry that made_gl_entries() would reject.
        pre_round_total = net + tax_total
        self.grand_total = round(pre_round_total)
        self.round_off = round(self.grand_total - pre_round_total, 2)

    def set_outstanding_amount(self):
        if self.docstatus == 0:
            self.outstanding_amount = self.grand_total

    def validate_accounts(self):
        if self.credit_to:
            validate_account_company(self.credit_to, self.company)
            validate_account_type(self.credit_to, ["Payable"])
        if self.expense_account:
            validate_account_company(self.expense_account, self.company)
            validate_account_type(self.expense_account, ["Expense", "Cost of Goods Sold"])

    def set_status(self):
        if self.docstatus == 2:   self.status = "Cancelled"
        elif self.docstatus == 1:
            if flt(self.outstanding_amount) <= 0:                            self.status = "Paid"
            elif flt(self.outstanding_amount) < flt(self.grand_total):       self.status = "Partly Paid"
            elif self.due_date and getdate(self.due_date) < getdate(today()): self.status = "Overdue"
            else:                                                             self.status = "Submitted"
        else:
            self.status = "Draft"

    def on_submit(self):
        if getattr(self, "is_return", 0):
            from zoho_books_clone.accounts.accounting_engine import post_debit_note
            dn_amount = abs(flt(self.grand_total))

            # Guard: check that the source bill still has enough outstanding
            if getattr(self, "return_against", None):
                src_outstanding = flt(frappe.db.get_value(
                    "Purchase Invoice", self.return_against, "outstanding_amount"
                ) or 0)
                if src_outstanding < dn_amount - 0.01:
                    frappe.throw(_(
                        "Cannot submit Debit Note {0}: the Purchase Invoice {1} "
                        "already has its balance fully claimed "
                        "(remaining: ₹{2:,.2f}, this note: ₹{3:,.2f})."
                    ).format(
                        self.name,
                        self.return_against,
                        src_outstanding,
                        dn_amount,
                    ))

            # A return doesn't create new debt; it offsets the source bill.
            self.db_set("outstanding_amount", 0, update_modified=False)
            self.db_set("status", "Paid", update_modified=False)
            # post_debit_note splits the return per line (stock vs non-stock)
            # itself now — see inventory_gl.classify_debit_note_item_amounts.
            post_debit_note(self)
            self._adjust_source_bill_outstanding(direction=-1)
        else:
            self.db_set("outstanding_amount", self.grand_total, update_modified=False)
            self.db_set("status", "Submitted", update_modified=False)
            self.outstanding_amount = self.grand_total
            self.status = "Submitted"
            post_purchase_invoice(self)
            # Release ordered_qty now that the bill is raised against the PO
            if getattr(self, "update_stock", 0) and getattr(self, "purchase_order", None):
                self._release_ordered_qty(direction=-1)

    def on_cancel(self):
        self.status = "Cancelled"
        self.outstanding_amount = 0
        reverse_voucher(self.doctype, self.name)
        if getattr(self, "is_return", 0):
            self._adjust_source_bill_outstanding(direction=+1)
        # Restore ordered_qty and reverse billed_qty when a normal bill is cancelled
        if not getattr(self, "is_return", 0) and getattr(self, "purchase_order", None):
            if getattr(self, "update_stock", 0):
                self._release_ordered_qty(direction=+1)
            self._reverse_billed_qty()

    def _release_ordered_qty(self, direction: int):
        """Release (direction=-1) or restore (+1) ordered_qty when billing against a PO."""
        from zoho_books_clone.inventory.utils import update_bin
        warehouse = getattr(self, "set_warehouse", None) or ""
        for row in (self.items or []):
            wh = getattr(row, "warehouse", None) or warehouse
            if not wh or not row.item_code:
                continue
            if flt(row.qty) <= 0:
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

    def _reverse_billed_qty(self):
        """Decrement billed_qty on linked PO lines and refresh PO status."""
        po_name = self.purchase_order
        for row in (self.items or []):
            if not row.item_code or flt(row.qty) <= 0:
                continue
            po_rows = frappe.db.sql("""
                SELECT name, billed_qty FROM `tabPurchase Order Item`
                WHERE parent = %s AND item_code = %s
                ORDER BY idx
            """, (po_name, row.item_code), as_dict=True)
            remaining_to_reverse = flt(row.qty)
            for pr in po_rows:
                if remaining_to_reverse <= 0:
                    break
                take = min(flt(pr.billed_qty), remaining_to_reverse)
                if take <= 0:
                    continue
                frappe.db.set_value(
                    "Purchase Order Item", pr.name, "billed_qty",
                    max(0.0, flt(pr.billed_qty) - take),
                    update_modified=False,
                )
                remaining_to_reverse -= take
        try:
            from zoho_books_clone.api.docs import _po_status_from_fulfillment
            new_status = _po_status_from_fulfillment(po_name)
            frappe.db.set_value("Purchase Order", po_name, "status",
                                new_status, update_modified=True)
        except Exception:
            pass

    def _adjust_source_bill_outstanding(self, direction: int):
        """Reduce (direction=-1) or restore (+1) outstanding on the source PINV.

        Always uses abs(grand_total) because debit note items carry negative qty,
        making grand_total negative. Without abs(), direction=-1 would ADD to
        outstanding instead of reducing it.
        """
        if not getattr(self, "return_against", None):
            return
        src = frappe.db.get_value(
            "Purchase Invoice", self.return_against,
            ["outstanding_amount", "grand_total", "due_date", "docstatus"],
            as_dict=True,
        )
        if not src:
            return
        dn_amount = abs(flt(self.grand_total))
        new_outstanding = max(0.0, round(flt(src.outstanding_amount) + direction * dn_amount, 2))
        if src.docstatus == 1:
            if flt(new_outstanding) <= 0:                            new_status = "Paid"
            elif flt(new_outstanding) < flt(src.grand_total):        new_status = "Partly Paid"
            elif src.due_date and getdate(src.due_date) < getdate(today()): new_status = "Overdue"
            else:                                                    new_status = "Submitted"
        else:
            new_status = "Cancelled" if src.docstatus == 2 else "Draft"
        frappe.db.set_value(
            "Purchase Invoice", self.return_against,
            {"outstanding_amount": new_outstanding, "status": new_status},
            update_modified=False,
        )