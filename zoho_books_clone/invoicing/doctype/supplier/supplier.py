import re
import frappe
from frappe import _
from frappe.model.document import Document

_GSTIN_RE = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')

class Supplier(Document):
    def validate(self):
        if not self.supplier_name:
            frappe.throw(_("Supplier Name is required"))
        if self.email_id and "@" not in self.email_id:
            frappe.throw(_("Please enter a valid email address"))
        if self.tax_id:
            self.tax_id = self.tax_id.strip().upper()
            if not _GSTIN_RE.match(self.tax_id):
                frappe.throw(_("Invalid GSTIN: {0}. Expected format: 22AAAAA0000A1Z5").format(self.tax_id))
        if not self.is_new() and self.has_value_changed("opening_balance"):
            from zoho_books_clone.accounts.opening_balance import guard_opening_balance_edit
            guard_opening_balance_edit("Supplier", self.name)

    def on_update(self):
        # Mirror of Customer.on_update — keep the opening balance posted as a
        # real Journal Entry against Accounts Payable. See
        # zoho_books_clone/accounts/opening_balance.py.
        if self.has_value_changed("opening_balance"):
            try:
                from zoho_books_clone.accounts.opening_balance import sync_party_opening_balance
                sync_party_opening_balance("Supplier", self.name, self.get("books_company"))
            except Exception as e:
                frappe.log_error(str(e), f"Opening balance sync failed for Supplier {self.name}")
                frappe.msgprint(
                    _("Supplier saved, but the opening balance could not be posted to the "
                      "ledger. Please check the Error Log and re-save once fixed."),
                    indicator="orange", alert=True,
                )

    def on_trash(self):
        from zoho_books_clone.accounts.opening_balance import guard_opening_balance_delete
        guard_opening_balance_delete("Supplier", self.name)

    @frappe.whitelist()
    def get_outstanding_bills(self):
        return frappe.get_all(
            "Purchase Invoice",
            filters={"supplier": self.name, "docstatus": 1, "outstanding_amount": [">", 0]},
            fields=["name", "posting_date", "due_date", "grand_total", "outstanding_amount"],
            order_by="due_date asc",
        )