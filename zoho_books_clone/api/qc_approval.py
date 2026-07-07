from __future__ import annotations
"""
QC Approval Request API — zoho_books_clone/api/qc_approval.py
=============================================================
Whitelisted REST endpoints for the human QC Approval workflow.

The QC Approval Request is created automatically when a QC Inspection
resolves to "Fail" or "Hold" (qc_hold=1). A QA Manager then approves
or rejects the request, and only an Approved request allows stock_link
to release a QC hold.

Endpoints
---------
POST  create_qc_approval_request(inspection_name, reason="")
GET   list_qc_approval_requests(approval_status="Pending", page=0, page_len=50)
GET   get_qc_approval_request(request_name)
POST  approve_qc_approval_request(request_name, remarks="")
POST  reject_qc_approval_request(request_name, rejection_reason)
"""

import frappe
from frappe import _
from frappe.utils import nowdate


# ─── Roles that may approve / reject ─────────────────────────────────────────

_APPROVER_ROLES = {"Books Admin", "System Manager", "Administrator"}


def _require_approver():
    """Raise PermissionError if the caller is not in an approver role."""
    roles = set(frappe.get_roles(frappe.session.user))
    if not (roles & _APPROVER_ROLES):
        frappe.throw(
            _("Only Books Admin or System Manager can approve/reject QC Approval Requests."),
            frappe.PermissionError,
        )


# ─── Create ───────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def create_qc_approval_request(inspection_name: str, reason: str = "") -> dict:
    """
    Create a QC Approval Request for a submitted QC Inspection.
    Idempotent — returns the existing request if one already exists.

    Called automatically from qc_hold_manager.handle_qc_result when
    status=Fail.  Can also be called manually from the UI.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    # Validate that the QC Inspection exists
    if not frappe.db.exists("QC Inspection", inspection_name):
        frappe.throw(_("QC Inspection {0} does not exist.").format(inspection_name))

    qci = frappe.get_doc("QC Inspection", inspection_name)

    # Idempotency — return existing pending/open request
    existing = frappe.db.get_value(
        "QC Approval Request",
        {
            "qc_inspection": inspection_name,
            "approval_status": ["!=", "Rejected"],
        },
        "name",
    )
    if existing:
        return {
            "request_name": existing,
            "created": False,
            "message": "QC Approval Request already exists",
        }

    req = frappe.new_doc("QC Approval Request")
    req.qc_inspection   = inspection_name
    req.reference_type  = qci.reference_type
    req.reference_name  = qci.reference_name
    req.item            = qci.item
    req.inspection_type = qci.inspection_type
    req.approval_status = "Pending"
    req.requested_by    = frappe.session.user
    req.request_date    = nowdate()
    req.approval_remarks = reason or ""

    req.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "request_name": req.name,
        "created": True,
        "message": f"QC Approval Request {req.name} created",
    }


# ─── List ─────────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def list_qc_approval_requests(
    approval_status: str = "Pending",
    page: int = 0,
    page_len: int = 50,
) -> dict:
    """
    Return paginated list of QC Approval Requests.
    approval_status: "Pending" | "Approved" | "Rejected" | "all"
    """
    filters: dict = {}
    if approval_status and approval_status != "all":
        filters["approval_status"] = approval_status

    page_len = min(int(page_len), 200)
    page = int(page)

    try:
        requests = frappe.get_all(
            "QC Approval Request",
            filters=filters,
            fields=[
                "name", "qc_inspection", "item", "inspection_type",
                "reference_type", "reference_name",
                "approval_status", "requested_by", "request_date",
                "approved_by", "approval_date", "rejection_reason",
                "approval_remarks", "creation",
            ],
            order_by="creation desc",
            limit=page_len,
            start=page * page_len,
            ignore_permissions=True,
        )
        total = frappe.db.count("QC Approval Request", filters=filters)
    except Exception as e:
        frappe.log_error(title="list_qc_approval_requests error", message=frappe.get_traceback())
        return {"requests": [], "total": 0, "page": page, "page_len": page_len, "error": str(e)}

    return {
        "requests": requests,
        "total": total,
        "page": page,
        "page_len": page_len,
    }


# ─── Get ──────────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_qc_approval_request(request_name: str) -> dict:
    """Return a single QC Approval Request document."""
    doc = frappe.get_doc("QC Approval Request", request_name)
    return doc.as_dict()


# ─── Approve ──────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def approve_qc_approval_request(request_name: str, remarks: str = "") -> dict:
    """
    Approve a pending QC Approval Request.
    Only Books Admin / System Manager may approve.
    On approval: stamps approved_by, approval_date, and sets status=Approved.
    """
    _require_approver()

    doc = frappe.get_doc("QC Approval Request", request_name)
    if doc.approval_status != "Pending":
        frappe.throw(
            _("Only Pending requests can be approved. Current status: {0}.").format(doc.approval_status)
        )

    doc.approval_status  = "Approved"
    doc.approved_by      = frappe.session.user
    doc.approval_date    = nowdate()
    if remarks:
        doc.approval_remarks = remarks

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    # Stamp the approval on the linked QC Inspection (if columns exist)
    _stamp_approval_on_inspection(doc.qc_inspection, "Approved", frappe.session.user, nowdate())

    return {
        "request_name": request_name,
        "approval_status": "Approved",
        "approved_by": frappe.session.user,
        "message": f"QC Approval Request {request_name} approved.",
    }


# ─── Reject ───────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def reject_qc_approval_request(request_name: str, rejection_reason: str) -> dict:
    """
    Reject a pending QC Approval Request.
    Only Books Admin / System Manager may reject.
    Rejection reason is required.
    """
    _require_approver()

    if not (rejection_reason or "").strip():
        frappe.throw(_("Rejection Reason is required when rejecting a QC Approval Request."))

    doc = frappe.get_doc("QC Approval Request", request_name)
    if doc.approval_status != "Pending":
        frappe.throw(
            _("Only Pending requests can be rejected. Current status: {0}.").format(doc.approval_status)
        )

    doc.approval_status  = "Rejected"
    doc.approved_by      = frappe.session.user
    doc.approval_date    = nowdate()
    doc.rejection_reason = rejection_reason

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    # Stamp on the linked QC Inspection
    _stamp_approval_on_inspection(doc.qc_inspection, "Rejected", frappe.session.user, nowdate())

    return {
        "request_name": request_name,
        "approval_status": "Rejected",
        "approved_by": frappe.session.user,
        "message": f"QC Approval Request {request_name} rejected.",
    }


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _stamp_approval_on_inspection(
    inspection_name: str,
    status: str,
    by_user: str,
    on_date: str,
):
    """
    Stamp approval metadata onto the QC Inspection document itself
    (if the custom columns exist — guarded by has_column checks).
    This is purely informational denormalisation for COA print format convenience.
    """
    try:
        update = {}
        if frappe.db.has_column("QC Inspection", "approval_status"):
            update["approval_status"] = status
        if frappe.db.has_column("QC Inspection", "approved_by"):
            update["approved_by"] = by_user
        if frappe.db.has_column("QC Inspection", "approval_date"):
            update["approval_date"] = on_date
        if update:
            frappe.db.set_value(
                "QC Inspection", inspection_name, update, update_modified=False
            )
    except Exception:
        pass  # Non-fatal — COA can still read from QCAR doc


def get_approval_status_for_inspection(inspection_name: str) -> dict:
    """
    Utility (non-whitelisted) — look up the latest non-cancelled approval
    request for a QC Inspection.  Used by generate_coa() and
    check_qc_before_stock_link approval guard.
    Returns dict with keys: found, approval_status, approved_by, approval_date,
    rejection_reason, request_name.
    """
    row = frappe.db.get_value(
        "QC Approval Request",
        {"qc_inspection": inspection_name},
        [
            "name", "approval_status", "approved_by",
            "approval_date", "rejection_reason",
        ],
        as_dict=True,
        order_by="creation desc",
    )
    if not row:
        return {
            "found": False,
            "approval_status": None,
            "approved_by": None,
            "approval_date": None,
            "rejection_reason": None,
            "request_name": None,
        }
    return {
        "found": True,
        "approval_status": row.approval_status,
        "approved_by": row.approved_by,
        "approval_date": str(row.approval_date) if row.approval_date else None,
        "rejection_reason": row.rejection_reason,
        "request_name": row.name,
    }