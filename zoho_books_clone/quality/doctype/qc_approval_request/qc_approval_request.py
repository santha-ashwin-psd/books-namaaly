import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import nowdate


class QCApprovalRequest(Document):
    def validate(self):
        if self.approval_status == "Rejected" and not (self.rejection_reason or "").strip():
            frappe.throw(_("Rejection Reason is required when rejecting a QC Approval Request."))

    def before_save(self):
        if self.approval_status in ("Approved", "Rejected"):
            if not self.approved_by:
                self.approved_by = frappe.session.user
            if not self.approval_date:
                self.approval_date = nowdate()
