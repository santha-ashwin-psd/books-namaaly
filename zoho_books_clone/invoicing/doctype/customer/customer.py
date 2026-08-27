import re
import frappe
from frappe import _
from frappe.model.document import Document

_GSTIN_RE = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')

class Customer(Document):
    def validate(self):
        if not self.customer_name:
            frappe.throw(_("Customer Name is required"))
        if self.email_id and "@" not in self.email_id:
            frappe.throw(_("Please enter a valid email address"))
        # GST/GSTIN format enforcement disabled — Oman uses VAT registration numbers, not GSTIN
        # if self.tax_id:
        #     self.tax_id = self.tax_id.strip().upper()
        #     if not _GSTIN_RE.match(self.tax_id):
        #         frappe.throw(_("Invalid GSTIN: {0}. Expected format: 22AAAAA0000A1Z5").format(self.tax_id))
        if self.tax_id:
            self.tax_id = self.tax_id.strip().upper()
        if not self.is_new() and self.has_value_changed("opening_balance"):
            from zoho_books_clone.accounts.opening_balance import guard_opening_balance_edit
            guard_opening_balance_edit("Customer", self.name)

    def after_insert(self):
        # Ensure a naming series counter exists
        pass

    def on_update(self):
        # Keep the opening balance's GL footprint (a Journal Entry against
        # Accounts Receivable) in sync whenever the field changes — see
        # zoho_books_clone/accounts/opening_balance.py for why this exists.
        # Wrapped defensively: a company whose chart of accounts isn't fully
        # set up yet should never block saving the Customer itself.
        if self.has_value_changed("opening_balance"):
            try:
                from zoho_books_clone.accounts.opening_balance import sync_party_opening_balance
                sync_party_opening_balance("Customer", self.name, self.get("books_company"))
            except Exception as e:
                frappe.log_error(str(e), f"Opening balance sync failed for Customer {self.name}")
                # The Customer save still succeeds (deliberate — see above),
                # but failing silently means the field and the ledger go out
                # of sync with no visible warning. Surface it as a
                # non-blocking alert so the user at least knows to check.
                frappe.msgprint(
                    _("Customer saved, but the opening balance could not be posted to the "
                      "ledger. Please check the Error Log and re-save once fixed."),
                    indicator="orange", alert=True,
                )

    def on_trash(self):
        from zoho_books_clone.accounts.opening_balance import guard_opening_balance_delete
        guard_opening_balance_delete("Customer", self.name)

    @frappe.whitelist()
    def get_outstanding_invoices(self):
        return frappe.get_all(
            "Sales Invoice",
            filters={"customer": self.name, "docstatus": 1, "outstanding_amount": [">", 0]},
            fields=["name", "posting_date", "due_date", "grand_total", "outstanding_amount"],
            order_by="due_date asc",
        )