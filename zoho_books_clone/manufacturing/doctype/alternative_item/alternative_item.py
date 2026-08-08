import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class AlternativeItem(Document):
    def validate(self):
        if self.item_code == self.alternative_item_code:
            frappe.throw(_("Original Item and Alternative Item cannot be the same."))
        if flt(self.conversion_factor) <= 0:
            frappe.throw(_("Conversion Factor must be greater than zero."))
        self._set_source_type()

    def _set_source_type(self):
        """source_type is never user-set -- it's derived from the Alternative
        Item's own Item Type so the two can never drift apart. An Item typed
        "Scrap Item" makes this mapping a scrap-reuse substitution; anything
        else is a normal Fresh Stock alternative.

        max_substitution_pct only means something for scrap reuse (it caps
        how much of a Work Order row may be filled from recovered scrap
        rather than fresh material), so it's forced back to 100 for Fresh
        Stock mappings rather than left showing a stale/meaningless value.
        """
        alt_item_type = frappe.db.get_value("Item", self.alternative_item_code, "item_type")
        self.source_type = "Recycled Scrap" if alt_item_type == "Scrap Item" else "Fresh Stock"

        if self.source_type == "Fresh Stock":
            self.max_substitution_pct = 100
        else:
            pct = flt(self.max_substitution_pct) or 100
            if pct <= 0 or pct > 100:
                frappe.throw(_("Max Substitution % must be between 0 and 100."))
            self.max_substitution_pct = pct