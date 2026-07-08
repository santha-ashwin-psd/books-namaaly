from frappe.model.document import Document
from frappe.utils import flt

class SalesInvoiceItem(Document):
    def validate(self):
        base = round(flt(self.qty) * flt(self.rate), 2)
        self.discount_percentage = flt(self.discount_percentage)
        if self.discount_percentage:
            self.discount_amount = round(base * self.discount_percentage / 100, 2)
        else:
            self.discount_amount = flt(self.discount_amount)
        self.amount = round(base - self.discount_amount, 2)