from __future__ import annotations
"""
QC Inspection Controller
========================
Submittable document — one per (reference_doc, item) pair.

validate():  Auto-evaluates every reading row → Accepted/Rejected.
             Sets overall status = Pass (all Accepted) or Fail (any Rejected).
             Computes summary counts: total_readings, accepted_readings, rejected_readings.

on_submit(): Logs the inspection event to Frappe Activity Log.
on_cancel(): Logs the cancellation to Frappe Activity Log and stamps the
             parent reference doc's qc_status (if present) as "Cancelled".
             Quarantine/hold reversal — cancelling the auto-created
             quarantine Stock Entry, clearing qc_hold, voiding a Pending
             QC Approval Request — is handled separately by
             qc_hold_manager.handle_qc_cancel, wired via hooks.py
             doc_events on_cancel for QC Inspection.
"""

import ast
import operator

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
        self._compute_qty_split()

    def on_submit(self):
        self._log_activity("Submitted")
        # Update a denormalised qc_status field on the reference doc (if present)
        self._stamp_reference_status()

    def on_cancel(self):
        self._log_activity("Cancelled")
        self._stamp_reference_status(cancelled=True)
        self._clear_row_link()

    def before_submit(self):
        if not self.readings:
            frappe.throw(_(
                "Cannot submit a QC Inspection with no readings. "
                "Please add at least one reading before submitting."
            ))

        pending_rows = [r for r in self.readings if (r.status or "Pending") == "Pending"]
        if pending_rows:
            frappe.throw(_(
                "Cannot submit — {0} reading row(s) are still <b>Pending</b>. "
                "Every reading must be filled in and resolved to Accepted or "
                "Rejected before the QC Inspection can be submitted, since a "
                "submitted document cannot be edited afterwards."
            ).format(len(pending_rows)))

        self._enforce_second_signoff()

    # ──────────────────────────────────────────────────────────────────────────
    # Core: reading evaluation
    # ──────────────────────────────────────────────────────────────────────────

    def _set_inspection_date(self):
        if not self.inspection_date:
            self.inspection_date = nowdate()

    def _enforce_second_signoff(self):
        """
        If this inspection's company has 'Require Second Sign-off on QC
        Inspections' enabled (Books Company.qc_require_second_signoff),
        Verified By must be set to a user distinct from Inspected By
        before submit. verified_by has existed on this doctype (and is
        already read into the COA context as the '2nd sign-off') but was
        never actually required anywhere -- a single inspector could
        always submit alone even at a company that expects dual
        sign-off on QC records. Fails open (no enforcement) if the
        company can't be resolved -- same as every other company-scoped
        QC setting in this app (see qc_hold_manager._get_company_qc_setting).
        """
        try:
            from zoho_books_clone.quality.qc_hold_manager import _get_inspection_company
            company = _get_inspection_company(self)
        except Exception:
            company = None

        if not company:
            return

        try:
            required = frappe.db.get_value("Books Company", company, "qc_require_second_signoff")
        except Exception:
            required = None

        if not required:
            return

        if not self.verified_by:
            frappe.throw(_(
                "This company requires a second sign-off on QC Inspections. "
                "Please set 'Verified By' before submitting."
            ))

        if self.verified_by == self.inspected_by:
            frappe.throw(_(
                "'Verified By' must be a different user from 'Inspected By' -- "
                "second sign-off requires two distinct reviewers."
            ))

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

    def _compute_qty_split(self):
        """
        Accepted/rejected qty (ERPNext-style partial pass/fail per row,
        rather than the previous whole-document-fails-entirely behaviour).

        - If inspected_qty isn't known (older records, or a reference
          doctype whose rows don't carry qty), skip entirely — nothing to
          split, and the whole-qty quarantine fallback in qc_hold_manager
          still applies.
        - If the inspector hasn't set a split yet (both 0/unset — the state
          left by qc_engine when it doesn't seed a qty), default it from the
          overall status: Fail -> all rejected, Pass/Pending -> all accepted.
          This keeps the common case (whole batch passes or whole batch
          fails) a no-op for the inspector.
        - If a split has been entered, just validate it sums to inspected_qty
          rather than silently overwriting a deliberate partial accept/reject.
        """
        if not flt(self.inspected_qty):
            return

        accepted = flt(self.accepted_qty)
        rejected = flt(self.rejected_qty)

        if not accepted and not rejected:
            if self.status == "Fail":
                self.rejected_qty = flt(self.inspected_qty)
                self.accepted_qty = 0
            else:
                self.accepted_qty = flt(self.inspected_qty)
                self.rejected_qty = 0
            return

        if flt(accepted + rejected) != flt(self.inspected_qty):
            frappe.throw(_(
                "Accepted Qty ({0}) + Rejected Qty ({1}) must equal "
                "Inspected Qty ({2})."
            ).format(accepted, rejected, self.inspected_qty))

        if rejected and self.status != "Fail":
            frappe.throw(_(
                "Rejected Qty is set but the overall inspection status is "
                "'{0}', not 'Fail'. A rejected quantity requires at least "
                "one Rejected reading."
            ).format(self.status))

    # ──────────────────────────────────────────────────────────────────────────
    # Activity log
    # ──────────────────────────────────────────────────────────────────────────

    def _log_activity(self, operation: str):
        try:
            frappe.get_doc({
                "doctype":          "Activity Log",
                "subject":          f"QC Inspection {operation}: {self.name}",
                "user":             frappe.session.user,
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

    def _clear_row_link(self):
        """
        Clear this inspection from any reference doc row's quality_inspection
        Link field so cancelling frees that row up for a fresh inspection
        (qc_engine's row-level "already covered" check keys off this link).
        Best-effort across every row on the reference doc since the
        inspection itself doesn't record which specific row it was
        stamped onto.
        """
        if not (self.reference_type and self.reference_name):
            return
        try:
            ref_doc = frappe.get_doc(self.reference_type, self.reference_name)
            for row in (getattr(ref_doc, "items", []) or []):
                if getattr(row, "quality_inspection", None) == self.name:
                    frappe.db.set_value(row.doctype, row.name, "quality_inspection", "",
                                         update_modified=False)
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
        min_raw = row.get("min_value")
        max_raw = row.get("max_value")
        # Distinguish "no range configured" (both left blank) from a
        # legitimate "must equal exactly 0" constraint (both explicitly 0).
        if min_raw in (None, "") and max_raw in (None, ""):
            return "Accepted"
        min_v = flt(min_raw)
        max_v = flt(max_raw)
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
            result = _safe_eval_formula(formula, {"reading": float(reading)})
            return "Accepted" if result else "Rejected"
        except Exception:
            return "Rejected"

    return "Pending"


# ─── Safe formula evaluator (replaces restricted-builtins eval()) ─────────────
#
# The "Formula" parameter type lets a template author supply an arbitrary
# boolean expression over `reading` (e.g. "reading > 0 and reading <= 5",
# or "flt(reading) == 7"). A raw eval() — even with __builtins__ stripped —
# is still a code-execution risk (attribute access, dunder tricks, etc. can
# often escape a naive restricted-builtins sandbox). Instead we walk a
# whitelisted AST: only literals, the `reading` name, arithmetic, comparison,
# boolean operators, and a single allowed `flt(...)` call are permitted.
# Anything else (attribute access, subscripting, function defs, imports,
# comprehensions, etc.) raises before any code can run.

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_ALLOWED_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
    ast.Not: operator.not_,
}
_ALLOWED_COMPARE = {
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
}
_ALLOWED_BOOLOPS = {ast.And: all, ast.Or: any}
_ALLOWED_FUNCS = {"flt": flt}


def _safe_eval_formula(formula: str, variables: dict):
    """Parse and evaluate a restricted boolean/arithmetic expression."""
    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Invalid formula syntax: {e}")
    return _eval_ast_node(tree.body, variables)


def _eval_ast_node(node, variables: dict):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, bool)):
            return node.value
        raise ValueError("Only numeric/boolean literals are allowed in formulas")

    if isinstance(node, ast.Name):
        if node.id in variables:
            return variables[node.id]
        raise ValueError(f"Unknown identifier in formula: {node.id!r}")

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_BINOPS:
            raise ValueError(f"Operator not allowed in formula: {op_type.__name__}")
        left = _eval_ast_node(node.left, variables)
        right = _eval_ast_node(node.right, variables)
        return _ALLOWED_BINOPS[op_type](left, right)

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_UNARYOPS:
            raise ValueError(f"Unary operator not allowed in formula: {op_type.__name__}")
        return _ALLOWED_UNARYOPS[op_type](_eval_ast_node(node.operand, variables))

    if isinstance(node, ast.Compare):
        left = _eval_ast_node(node.left, variables)
        result = True
        for op, comparator in zip(node.ops, node.comparators):
            op_type = type(op)
            if op_type not in _ALLOWED_COMPARE:
                raise ValueError(f"Comparison not allowed in formula: {op_type.__name__}")
            right = _eval_ast_node(comparator, variables)
            if not _ALLOWED_COMPARE[op_type](left, right):
                result = False
                break
            left = right
        return result

    if isinstance(node, ast.BoolOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_BOOLOPS:
            raise ValueError(f"Boolean operator not allowed in formula: {op_type.__name__}")
        values = [_eval_ast_node(v, variables) for v in node.values]
        return _ALLOWED_BOOLOPS[op_type](values)

    if isinstance(node, ast.Call):
        if (isinstance(node.func, ast.Name)
                and node.func.id in _ALLOWED_FUNCS
                and not node.keywords
                and len(node.args) == 1):
            arg = _eval_ast_node(node.args[0], variables)
            return _ALLOWED_FUNCS[node.func.id](arg)
        raise ValueError("Only flt(...) calls are allowed in formulas")

    raise ValueError(f"Disallowed expression in formula: {type(node).__name__}")