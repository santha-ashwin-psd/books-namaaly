"""
Credit Note — P1/Issue 5
Reverses a Sales Invoice's income and receivable GL entries.

GL on submit:
  DR  Income Account        grand_total   (reduce income)
  CR  Accounts Receivable   grand_total   (reduce what customer owes)

GL on cancel:
  Reversing entries are created by make_gl_entries(cancel=True),
  which swaps debit/credit — restoring the original balance.
"""
import frappe
from frappe import _
from frappe.utils import flt, today, getdate
from frappe.model.document import Document
from zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry import make_gl_entries
from zoho_books_clone.db.validators import (
    validate_fiscal_year, validate_account_company, validate_account_type,
)


class CreditNote(Document):

    def validate(self):
        self._calculate_totals()
        self._set_status()
        if not self.posting_date:
            self.posting_date = today()
        if self.posting_date and self.company:
            try:
                self.fiscal_year = validate_fiscal_year(self.posting_date, self.company)
            except frappe.ValidationError:
                raise  # surface lock_date / closed-year errors
            except Exception:
                pass  # ignore only unexpected errors (missing FY on draft is caught above)
        self._validate_accounts()

    def _calculate_totals(self):
        net = sum(flt(i.qty) * flt(i.rate) for i in (self.items or []))
        for tax in (self.taxes or []):
            if flt(tax.rate) and not flt(tax.tax_amount):
                tax.tax_amount = round(net * flt(tax.rate) / 100, 2)
        tax_total = sum(flt(t.tax_amount) for t in (self.taxes or []))
        self.net_total   = round(net, 2)
        self.total_tax   = round(tax_total, 2)
        self.grand_total = round(net + tax_total, 2)

    def _set_status(self):
        if   self.docstatus == 2: self.status = "Cancelled"
        elif self.docstatus == 1: self.status = "Submitted"
        else:                     self.status = "Draft"

    def _validate_accounts(self):
        if self.debit_to:
            validate_account_company(self.debit_to, self.company)
            validate_account_type(self.debit_to, ["Receivable"])
        if self.income_account:
            validate_account_company(self.income_account, self.company)
            validate_account_type(self.income_account, ["Income"])

    def on_submit(self):
        self.status = "Submitted"
        if not self.grand_total:
            frappe.throw(_("Credit Note has zero value — cannot submit"))
        self._make_gl_entries()
        self._maybe_restock_items()
        # If this CN is linked to an invoice, restore outstanding on that invoice
        if self.return_against:
            self._update_source_invoice_outstanding()

    def _maybe_restock_items(self):
        """
        Physically restock returned goods when 'Restock Returned Items' is
        checked — a plain Credit Note only reverses Income/AR and, before
        this, never touched stock or cost at all (a customer return that
        never restored inventory or reversed COGS).

        Builds a Material Receipt Stock Entry (reusing stock_link's helpers)
        valued at each item's current moving-average rate — this app doesn't
        lot-track the exact COGS rate booked on the original sale, so this
        is the same approximation the Sales Invoice return path and the
        Profit-wise report already use.

        Deliberately does NOT post a separate DR Inventory / CR COGS entry:
        the Stock Entry's own GL posting already debits Inventory and
        credits Stock Adjustment (this reference doctype isn't a purchase
        voucher, so inventory_gl.is_purchase_stock_receipt is False). Adding
        a second GL leg here would double-count the Inventory debit.
        get_profit_and_loss already nets Stock Adjustment against
        Income/Expense/COGS the same way COGS would be, so the P&L bottom
        line is unaffected by which of the two accounts is used.
        """
        if not flt(getattr(self, "restock_items", 0)):
            return
        from zoho_books_clone.inventory.stock_link import (
            _apply_current_valuation_rate,
            _build_stock_entry,
            _stock_rows,
        )
        rows = _stock_rows(self, direction="issue", zero_rate=False)
        if not rows:
            return
        _apply_current_valuation_rate(rows)
        se = _build_stock_entry(
            entry_type="Material Receipt",
            posting_date=self.posting_date or today(),
            company=self.company,
            remarks=_("Auto stock restock — Credit Note {0}").format(self.name),
            rows=rows,
            ref_doctype=self.doctype,
            ref_docname=self.name,
        )
        frappe.msgprint(
            _("Stock restocked automatically via {0}.").format(frappe.bold(se.name)),
            indicator="green",
            alert=True,
        )

    def _make_gl_entries(self):
        if not self.debit_to:
            frappe.throw(_("Please set the Debit To (AR) account"))
        if not self.income_account:
            frappe.throw(_("Please set the Income Account"))

        # Credit note reverses the original sale:
        #   DR Income (reduce income)  |  CR Receivable (reduce debt owed by customer)
        gl_map = [
            {
                "account":      self.income_account,
                "debit":        self.net_total,
                "credit":       0,
                "voucher_type": self.doctype,
                "voucher_no":   self.name,
                "posting_date": self.posting_date,
                "company":      self.company,
                "fiscal_year":  self.fiscal_year or "",
                "remarks":      f"Credit Note {self.name} — income reversal",
            },
            {
                "account":      self.debit_to,
                "debit":        0,
                "credit":       self.grand_total,
                "voucher_type": self.doctype,
                "voucher_no":   self.name,
                "posting_date": self.posting_date,
                "party_type":   "Customer",
                "party":        self.customer,
                "company":      self.company,
                "fiscal_year":  self.fiscal_year or "",
                "remarks":      f"Credit Note {self.name} — receivable reduction for {self.customer}",
            },
        ]
        # Tax reversals
        for tax in (self.taxes or []):
            if flt(tax.tax_amount) and tax.account_head:
                gl_map.append({
                    "account":      tax.account_head,
                    "debit":        flt(tax.tax_amount),
                    "credit":       0,
                    "voucher_type": self.doctype,
                    "voucher_no":   self.name,
                    "posting_date": self.posting_date,
                    "company":      self.company,
                    "fiscal_year":  self.fiscal_year or "",
                    "remarks":      f"Tax reversal — {tax.description} on {self.name}",
                })
        make_gl_entries(gl_map)

    def _update_source_invoice_outstanding(self):
        """
        Reduce outstanding on the source Sales Invoice by this CN's value —
        the customer's liability for this invoice is reduced by the returned amount.
        If the invoice was already fully paid, outstanding goes negative, indicating
        the customer is owed a refund / has a credit balance.
        """
        si = frappe.db.get_value(
            "Sales Invoice", self.return_against,
            ["outstanding_amount", "grand_total", "due_date", "docstatus"],
            as_dict=True,
        )
        if not si:
            return
        new_outstanding = flt(si.outstanding_amount) - flt(self.grand_total)
        new_status = _compute_si_status(
            si.docstatus, new_outstanding, si.grand_total, si.due_date
        )
        frappe.db.set_value(
            "Sales Invoice", self.return_against,
            {"outstanding_amount": new_outstanding, "status": new_status},
            update_modified=False,
        )

    def on_cancel(self):
        self.status = "Cancelled"
        make_gl_entries(
            [{"voucher_type": self.doctype, "voucher_no": self.name}],
            cancel=True,
        )
        from zoho_books_clone.inventory.stock_link import _cancel_linked_entries
        _cancel_linked_entries(self.doctype, self.name)
        # Undo the outstanding adjustment on the source invoice
        if self.return_against:
            si = frappe.db.get_value(
                "Sales Invoice", self.return_against,
                ["outstanding_amount", "grand_total", "due_date", "docstatus"],
                as_dict=True,
            )
            if si:
                restored = flt(si.outstanding_amount) + flt(self.grand_total)
                new_status = _compute_si_status(
                    si.docstatus, restored, si.grand_total, si.due_date
                )
                frappe.db.set_value(
                    "Sales Invoice", self.return_against,
                    {"outstanding_amount": restored, "status": new_status},
                    update_modified=False,
                )


def _compute_si_status(docstatus, outstanding, grand_total, due_date):
    """Mirror of SalesInvoice.set_status — used when adjusting SI outside its own lifecycle."""
    if docstatus == 2:
        return "Cancelled"
    if docstatus != 1:
        return "Draft"
    if flt(outstanding) <= 0:
        return "Paid"
    if flt(outstanding) < flt(grand_total):
        return "Partly Paid"
    if due_date and getdate(due_date) < getdate(today()):
        return "Overdue"
    return "Submitted"