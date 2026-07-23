import frappe
from frappe import _
from frappe.utils import flt, nowdate
from frappe.model.document import Document
from zoho_books_clone.accounts.accounting_engine import post_expense, reverse_voucher


class Expense(Document):

    def validate(self):
        if not self.posting_date:
            self.posting_date = nowdate()
        if flt(self.amount) <= 0:
            frappe.throw(_("Amount must be greater than 0"))
        self._validate_expense_category_company()
        self._compute_totals()

    def _validate_expense_category_company(self):
        if not self.expense_type:
            return
        cat_company = frappe.db.get_value("Expense Category", self.expense_type, "company")
        if cat_company and self.company and cat_company != self.company:
            frappe.throw(_("Expense Category {0} belongs to {1}, not {2}").format(
                frappe.bold(self.expense_type), frappe.bold(cat_company), frappe.bold(self.company)))

    def _compute_totals(self):
        self.tax_amount = round(flt(self.amount) * flt(self.gst_rate) / 100, 2)
        self.total_amount = round(flt(self.amount) + flt(self.tax_amount), 2)

    def on_submit(self):
        self.status = "Submitted"
        frappe.db.set_value("Expense", self.name, "status", "Submitted", update_modified=False)
        post_expense(self)

    def on_cancel(self):
        self.status = "Cancelled"
        frappe.db.set_value("Expense", self.name, "status", "Cancelled", update_modified=False)
        reverse_voucher(self.doctype, self.name)