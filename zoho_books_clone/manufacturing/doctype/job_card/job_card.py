import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, time_diff_in_seconds


class JobCard(Document):
    def before_insert(self):
        """Derive company from the parent Work Order for multi-tenant isolation."""
        if not self.company and self.work_order:
            self.company = frappe.db.get_value("Work Order", self.work_order, "company") or ""

    def validate(self):
        self._calc_total_time()

    def _calc_total_time(self):
        total = 0.0
        for row in (self.time_logs or []):
            if row.from_time and row.to_time:
                diff_secs = time_diff_in_seconds(row.to_time, row.from_time)
                if diff_secs < 0:
                    frappe.throw(
                        _("Time log row: To Time cannot be before From Time.")
                    )
                row.time_in_mins = flt(diff_secs) / 60
            total += flt(row.time_in_mins)
        self.total_time_in_mins = total

    def on_update(self):
        # 4.5 — sync status back to the linked Work Order Operation row
        if self.wo_operation_name and self.status:
            _sync_wo_operation_status(self.wo_operation_name, self.status)
            _sync_wo_operation_actual_time(self.wo_operation_name)

    def on_cancel(self):
        if self.wo_operation_name:
            _sync_wo_operation_status(self.wo_operation_name, "Pending")
            _sync_wo_operation_actual_time(self.wo_operation_name)


def _sync_wo_operation_status(wo_op_name, job_card_status):
    """Map Job Card status → Work Order Operation status and write it."""
    STATUS_MAP = {
        "Open":             "Pending",
        "Work In Progress": "In Process",
        "Completed":        "Completed",
        "Cancelled":        "Pending",
    }
    mapped = STATUS_MAP.get(job_card_status, "Pending")
    try:
        frappe.db.set_value("Work Order Operation", wo_op_name, "status", mapped)
    except Exception:
        pass


def _sync_wo_operation_actual_time(wo_op_name):
    """Roll up actual time worked into the Work Order Operation row.

    Job Card.total_time_in_mins was being calculated from time logs
    (_calc_total_time above) but never written anywhere the Work Order could
    see it, so 'Actual Time (Minutes)' on every Work Order Operation stayed
    permanently 0 regardless of how much was actually logged — planned-vs-
    actual time and any reporting built on it was silently unusable.

    Summed across every non-cancelled Job Card against this row rather than
    just `self`, since a re-worked operation can have more than one Job Card
    (e.g. the first was scrapped/cancelled and a fresh one created) and the
    Work Order Operation should reflect total real time spent either way.
    """
    total = frappe.db.sql(
        """SELECT SUM(total_time_in_mins) FROM `tabJob Card`
           WHERE wo_operation_name = %s AND status != 'Cancelled'""",
        (wo_op_name,),
    )[0][0]
    try:
        frappe.db.set_value("Work Order Operation", wo_op_name, "actual_time_in_mins", flt(total))
    except Exception:
        pass