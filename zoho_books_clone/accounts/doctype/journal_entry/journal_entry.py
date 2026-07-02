# Copyright (c) 2026
import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document
from zoho_books_clone.accounts.accounting_engine import post_journal_entry, reverse_voucher
from zoho_books_clone.db.validators import validate_fiscal_year


class JournalEntry(Document):

    def validate(self):
        # Ensure posting_date falls inside an open, unlocked fiscal year before
        # any further checks — this guards against both "no FY found" and the
        # period lock_date, which central_validator._check_period_not_closed
        # does not cover (it only catches closed years, not missing ones).
        # Opening Entries are exempt (same as in central_validator): they set up
        # historical balances and may be dated before any fiscal year exists.
        if self.posting_date and self.company:
            if self.voucher_type == "Opening Entry":
                try:
                    self.fiscal_year = validate_fiscal_year(self.posting_date, self.company)
                except Exception:
                    self.fiscal_year = ""
            else:
                self.fiscal_year = validate_fiscal_year(self.posting_date, self.company)

        if not self.accounts:
            frappe.throw(_("Journal Entry must have at least one account row."))
        total_debit  = sum(flt(r.debit)  for r in self.accounts)
        total_credit = sum(flt(r.credit) for r in self.accounts)
        if abs(total_debit - total_credit) > 0.01:
            frappe.throw(_(
                "Journal Entry is not balanced — "
                "Total Debit {0} ≠ Total Credit {1}."
            ).format(
                frappe.bold(f"₹{total_debit:,.2f}"),
                frappe.bold(f"₹{total_credit:,.2f}"),
            ))
        self.total_debit  = round(total_debit,  2)
        self.total_credit = round(total_credit, 2)

    def on_submit(self):
        post_journal_entry(self)
        self.db_set("status", "Submitted", update_modified=False)

    def on_cancel(self):
        reverse_voucher(self.doctype, self.name)
        self.db_set("status", "Cancelled", update_modified=False)