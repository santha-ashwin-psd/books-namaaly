import frappe
from frappe.utils import flt, today
from frappe.model.document import Document


class BankAccount(Document):

    def after_insert(self):
        self._post_opening_gl()

    def on_update(self):
        # Lock this row for the rest of the transaction first: two saves of
        # the same Bank Account landing at the same instant (double-click,
        # a retried request) would otherwise both run the exists() check
        # before either had committed its GL entries, and both post an
        # opening entry — doubling the GL balance. Same race, same fix as
        # sync_party_opening_balance() in accounts/opening_balance.py.
        frappe.db.sql("SELECT name FROM `tabBank Account` WHERE name=%s FOR UPDATE", self.name)
        if self.gl_account:
            has_gle = frappe.db.exists(
                "General Ledger Entry",
                {"voucher_type": "Bank Account", "voucher_no": self.name}
            )
            if not has_gle:
                self._post_opening_gl()
            else:
                self._sync_opening_gl()

    def _sync_opening_gl(self):
        opening = flt(self.opening_balance)
        
        # Suspense / Equity account for the other leg
        suspense = frappe.db.get_value(
            "Account",
            {"account_type": ["in", ["Equity", "Temporary", "Stock Adjustment"]], "is_group": 0, "company": self.company or ""},
            "name"
        ) or self.gl_account  # self-balancing fallback

        entries = frappe.get_all(
            "General Ledger Entry",
            filters={"voucher_type": "Bank Account", "voucher_no": self.name},
            fields=["name", "account"]
        )

        from zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry import _update_account_balance
        
        for entry in entries:
            is_bank_leg = (entry.account == self.gl_account)
            # If the account is neither the bank nor the suspense, skip it
            if not is_bank_leg and entry.account != suspense:
                continue
                
            if opening >= 0:
                debit = opening if is_bank_leg else 0.0
                credit = 0.0 if is_bank_leg else opening
            else:
                debit = 0.0 if is_bank_leg else abs(opening)
                credit = abs(opening) if is_bank_leg else 0.0

            frappe.db.set_value(
                "General Ledger Entry", entry.name,
                {"debit": debit, "credit": credit},
                update_modified=False
            )
            _update_account_balance(entry.account)

    def _post_opening_gl(self):
        opening = flt(self.opening_balance)
        if not opening or not self.gl_account:
            return

        # Suspense / Equity account for the other leg
        suspense = frappe.db.get_value(
            "Account",
            {"account_type": ["in", ["Equity", "Temporary", "Stock Adjustment"]], "is_group": 0, "company": self.company or ""},
            "name"
        ) or self.gl_account  # self-balancing fallback

        if opening >= 0:
            bank_debit, bank_credit = opening, 0.0
            susp_debit, susp_credit = 0.0, opening
        else:
            bank_debit, bank_credit = 0.0, abs(opening)
            susp_debit, susp_credit = abs(opening), 0.0

        gl_map = [
            {
                "account":      self.gl_account,
                "debit":        bank_debit,
                "credit":       bank_credit,
                "voucher_type": "Bank Account",
                "voucher_no":   self.name,
                "posting_date": today(),
                "company":      self.company or "",
                "remarks":      f"Opening balance — {self.account_name or self.name}",
            },
            {
                "account":      suspense,
                "debit":        susp_debit,
                "credit":       susp_credit,
                "voucher_type": "Bank Account",
                "voucher_no":   self.name,
                "posting_date": today(),
                "company":      self.company or "",
                "remarks":      f"Opening balance contra — {self.account_name or self.name}",
            },
        ]
        try:
            from zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry import make_gl_entries
            make_gl_entries(gl_map)
        except Exception as e:
            frappe.log_error(f"Bank Account {self.name}: opening GL failed — {e}", "Bank GL")