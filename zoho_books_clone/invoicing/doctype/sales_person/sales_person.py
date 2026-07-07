import frappe
from frappe import _
from frappe.model.document import Document


class SalesPerson(Document):
    def validate(self):
        if not self.sales_person_name:
            frappe.throw(_("Sales Person Name is required"))
        if self.email_id and "@" not in self.email_id:
            frappe.throw(_("Please enter a valid email address"))
        if self.reports_to and self.reports_to == self.name:
            frappe.throw(_("Sales Person cannot report to themselves"))
        if self.commission_rate is not None and (self.commission_rate < 0 or self.commission_rate > 100):
            frappe.throw(_("Commission Rate must be between 0 and 100"))

    def after_insert(self):
        # Ensure a naming series counter exists
        pass

    @frappe.whitelist()
    def get_sales_invoices(self):
        return frappe.get_all(
            "Sales Invoice",
            filters={"sales_person": self.name, "docstatus": 1},
            fields=["name", "posting_date", "customer", "grand_total", "outstanding_amount"],
            order_by="posting_date desc",
        )