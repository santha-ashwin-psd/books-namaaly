from frappe.model.document import Document
from frappe.utils import flt
class PurchaseInvoiceItem(Document):
    def validate(self):
        self.amount = round(flt(self.qty)*flt(self.rate),2)
        from zoho_books_clone.inventory.utils import get_conversion_factor
        self.conversion_factor = get_conversion_factor(self.item_code, self.uom)
        self.qty_in_stock_uom = round(flt(self.qty) * flt(self.conversion_factor), 4)