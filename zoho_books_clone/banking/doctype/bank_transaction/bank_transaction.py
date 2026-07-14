import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document
from zoho_books_clone.db.validators import validate_fiscal_year


class BankTransaction(Document):

    def validate(self):
        # Bank Transaction is not wired to central_validator, but _post_gl()
        # writes GL entries dated self.date on submit.  Guard that date here so
        # GL entries can never land in a closed or missing fiscal year.
        if self.date and self.bank_account:
            company = frappe.db.get_value("Bank Account", self.bank_account, "company") or ""
            if company:
                validate_fiscal_year(self.date, company)

        self._set_balance()

    def on_submit(self):
        self._post_gl()

    def on_cancel(self):
        self._reverse_gl()

    # ── Balance running total ─────────────────────────────────────────────────

    def _set_balance(self):
        last = frappe.db.sql("""
            SELECT balance FROM `tabBank Transaction`
            WHERE bank_account=%s AND date<=%s AND name!=%s AND docstatus=1
            ORDER BY date DESC, creation DESC LIMIT 1
        """, (self.bank_account, self.date, self.name or ""), as_dict=True)
        prev = flt(last[0].balance) if last else 0
        self.balance = prev + flt(self.credit) - flt(self.debit)

    # ── GL posting ────────────────────────────────────────────────────────────

    def _get_bank_gl_account(self):
        """Return the COA account linked to this bank account."""
        return frappe.db.get_value("Bank Account", self.bank_account, "gl_account") or ""

    def _post_gl(self):
        # Caller (e.g. post_bank_transfer) may post a single combined GL set
        # itself; skip the per-transaction posting in that case.
        if getattr(self.flags, "skip_gl_posting", False):
            return
        bank_account = self._get_bank_gl_account()
        if not bank_account:
            frappe.log_error(
                f"Bank Transaction {self.name}: no GL account linked to bank account "
                f"'{self.bank_account}'. GL skipped. Link a COA account under Banking → Accounts.",
                "Bank GL"
            )
            return

        company = frappe.db.get_value("Bank Account", self.bank_account, "company") or ""

        # Counterpart account: use the mapped_account (user-categorized Income/
        # Expense/etc account) if set, else a dedicated bank suspense account.
        # NOTE: Stock Adjustment is an inventory-valuation account and must
        # NEVER be used as a bank-transaction contra account.
        contra = (
            getattr(self, "mapped_account", None)
            or frappe.db.get_value(
                "Account",
                {"account_type": "Temporary", "is_group": 0, "company": company},
                "name"
            )
        )

        if not contra:
            frappe.throw(
                _(
                    "Bank Transaction {0}: no 'Categorize To' account set and no "
                    "suspense account (account_type = Temporary) found for company "
                    "{1}. Please set 'Categorize To' on the transaction, or create "
                    "a Temporary-type suspense account."
                ).format(self.name, company)
            )

        credit_amt = flt(self.credit)
        debit_amt  = flt(self.debit)

        if not credit_amt and not debit_amt:
            return

        gl_map = []
        if credit_amt:
            # Money IN: Dr Bank GL / Cr Contra
            gl_map = [
                {"account": bank_account, "debit": credit_amt, "credit": 0,
                 "voucher_type": "Bank Transaction", "voucher_no": self.name,
                 "posting_date": self.date, "company": company,
                 "remarks": self.description or f"Bank credit — {self.bank_account}"},
                {"account": contra, "debit": 0, "credit": credit_amt,
                 "voucher_type": "Bank Transaction", "voucher_no": self.name,
                 "posting_date": self.date, "company": company,
                 "remarks": self.description or f"Bank credit contra — {self.bank_account}"},
            ]
        elif debit_amt:
            # Money OUT: Cr Bank GL / Dr Contra
            gl_map = [
                {"account": contra, "debit": debit_amt, "credit": 0,
                 "voucher_type": "Bank Transaction", "voucher_no": self.name,
                 "posting_date": self.date, "company": company,
                 "remarks": self.description or f"Bank debit — {self.bank_account}"},
                {"account": bank_account, "debit": 0, "credit": debit_amt,
                 "voucher_type": "Bank Transaction", "voucher_no": self.name,
                 "posting_date": self.date, "company": company,
                 "remarks": self.description or f"Bank debit contra — {self.bank_account}"},
            ]

        try:
            from zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry import make_gl_entries
            make_gl_entries(gl_map)
        except Exception as e:
            frappe.log_error(f"Bank Transaction {self.name}: GL failed — {e}", "Bank GL")

    def _reverse_gl(self):
        try:
            from zoho_books_clone.accounts.accounting_engine import reverse_voucher
            reverse_voucher("Bank Transaction", self.name)
        except Exception:
            pass