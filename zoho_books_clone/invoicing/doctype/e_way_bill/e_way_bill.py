# Copyright (c) 2026
import frappe
from frappe import _
from frappe.model.document import Document


class EWayBill(Document):
    def before_delete(self):
        """Only Cancelled or Expired EWBs may be deleted.

        The frontend already hides the delete action for 'Generated' rows,
        but that's a UI-only guard — enforce it server-side too so a direct
        API/bulk call can't remove a still-active E-Way Bill.
        """
        if self.status == "Generated":
            frappe.throw(
                _("Cannot delete E-Way Bill {0} — it is still Generated. Cancel it first.")
                .format(self.name)
            )