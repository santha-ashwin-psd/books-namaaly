import frappe
from frappe.model.document import Document
from frappe.utils import flt


class PurchaseReceiptItem(Document):
    def validate(self):
        # Mirror Purchase Order/Invoice Item: resolve this row's UOM against
        # the Item's UOM Conversions so a receipt entered in a Purchase UOM
        # (e.g. Box) is later converted to the Item's Stock UOM (e.g. Kg)
        # before it hits the stock ledger. Previously this doctype had no
        # conversion_factor at all, so stock_link.py silently added the raw
        # entered qty (e.g. "10 Box") as if it were already in Kg.
        from zoho_books_clone.inventory.utils import get_conversion_factor
        self.conversion_factor = get_conversion_factor(self.item_code, self.uom)
        # accepted_qty (not qty) is what actually lands in stock — see
        # PurchaseReceipt.validate(), which derives accepted_qty from qty.
        self.qty_in_stock_uom = round(flt(self.accepted_qty) * flt(self.conversion_factor), 4)