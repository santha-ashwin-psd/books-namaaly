from __future__ import annotations
"""
QC Inspection Controller
========================
Submittable document — one per (reference_doc, item) pair.

validate():  Auto-evaluates every reading row → Accepted/Rejected.
             Sets overall status = Pass (all Accepted) or Fail (any Rejected).
             Computes summary counts: total_readings, accepted_readings, rejected_readings.

on_submit(): Logs the inspection event to Frappe Activity Log.
on_cancel(): Clears any ignore_qc_warning flags on the parent reference doc.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate


class QCInspection(Document):

    # ──────────────────────────────────────────────────────────────────────────
    # Hooks
    # ──────────────────────────────────────────────────────────────────────────

    def validate(self):
        self._set_inspection_date()
        self._evaluate_readings()
        self._compute_status()
        self._compute_summary_counts()

    def on_submit(self):
        self._log_activity("Submitted")
        # Update a denormalised qc_status field on the reference doc (if present)
        self._stamp_reference_status()

    def on_cancel(self):
        self._log_activity("Cancelled")
        self._stamp_reference_status(cancelled=True)

    def before_submit(self):
        if not self.readings:
            frappe.throw(_(
                "Cannot submit a QC Inspection with no readings. "
                "Please add at least one reading before submitting."
            ))

    # ──────────────────────────────────────────────────────────────────────────
    # Core: reading evaluation
    # ──────────────────────────────────────────────────────────────────────────

    def _set_inspection_date(self):
        if not self.inspection_date:
            self.inspection_date = nowdate()

    def _evaluate_readings(self):
        """Evaluate each reading row against its template parameter criteria."""
        for row in (self.readings or []):
            row.status = _evaluate_reading_row(row)

    def _compute_status(self):
        """
        Overall status:
          - No readings → Pending
          - Any reading Rejected → Fail
          - All readings Accepted → Pass
          - Otherwise → Pending (some rows not yet filled)
        """
        readings = self.readings or []
        if not readings:
            self.status = "Pending"
            return
        statuses = [r.status for r in readings]
        if "Rejected" in statuses:
            self.status = "Fail"
        elif all(s == "Accepted" for s in statuses):
            self.status = "Pass"
        else:
            self.status = "Pending"

    def _compute_summary_counts(self):
        readings = self.readings or []
        self.total_readings    = len(readings)
        self.accepted_readings = sum(1 for r in readings if r.status == "Accepted")
        self.rejected_readings = sum(1 for r in readings if r.status == "Rejected")

    # ──────────────────────────────────────────────────────────────────────────
    # Activity log
    # ──────────────────────────────────────────────────────────────────────────

    def _log_activity(self, operation: str):
        try:
            frappe.get_doc({
                "doctype":          "Activity Log",
                "user":             frappe.session.user,
                "operation":        operation,
                "status":           "Success",
                "reference_doctype": self.doctype,
                "reference_name":   self.name,
                "content": (
                    f"QC Inspection {operation}: {self.name} | "
                    f"Type: {self.inspection_type} | "
                    f"Item: {self.item} | "
                    f"Reference: {self.reference_type} {self.reference_name} | "
                    f"Status: {self.status}"
                ),
            }).insert(ignore_permissions=True)
        except Exception:
            pass  # Never fail on logging

    # ──────────────────────────────────────────────────────────────────────────
    # Denormalised status stamp on parent doc
    # ──────────────────────────────────────────────────────────────────────────

    def _stamp_reference_status(self, cancelled: bool = False):
        """
        If the reference doctype has a `qc_status` field, update it
        with the current overall QC result for this item.
        This is a convenience stamp — the authoritative status lives here.
        """
        if not (self.reference_type and self.reference_name):
            return
        try:
            meta = frappe.get_meta(self.reference_type)
            if not meta.get_field("qc_status"):
                return
            new_status = "Cancelled" if cancelled else self.status
            frappe.db.set_value(
                self.reference_type, self.reference_name,
                "qc_status", new_status, update_modified=False
            )
        except Exception:
            pass


# ─── Standalone reading evaluator (also used by qc_engine) ────────────────────

def _evaluate_reading_row(row) -> str:
    """
    Returns 'Accepted', 'Rejected', or 'Pending' for a single reading row.
    Called both from QCInspection.validate() and from qc_engine helpers.
    """
    reading = (row.reading_value or "").strip()
    if not reading:
        return "Pending"  # Not yet filled in

    ptype = (row.parameter_type or "Numeric")

    if ptype == "Numeric":
        try:
            val = float(reading)
        except (ValueError, TypeError):
            return "Rejected"  # Non-numeric input for a numeric parameter
        min_v = flt(row.get("min_value"))
        max_v = flt(row.get("max_value"))
        # If both are 0, the template has no constraint set → accept
        if min_v == 0 and max_v == 0:
            return "Accepted"
        if min_v <= val <= max_v:
            return "Accepted"
        return "Rejected"

    elif ptype == "Non-Numeric":
        expected = (row.get("acceptance_criteria_value") or "").strip().lower()
        if not expected:
            return "Accepted"  # No criteria defined → accept anything
        if reading.lower() == expected:
            return "Accepted"
        return "Rejected"

    elif ptype == "Formula":
        formula = (row.get("formula") or "").strip()
        if not formula:
            return "Pending"
        try:
            result = eval(formula, {"__builtins__": {}}, {"reading": float(reading), "flt": flt})  # noqa: S307
            return "Accepted" if result else "Rejected"
        except Exception:
            return "Rejected"

    return "Pending"
