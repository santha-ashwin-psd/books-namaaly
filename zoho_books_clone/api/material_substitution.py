from __future__ import annotations
"""
Material Substitution API — zoho_books_clone/api/material_substitution.py
===========================================================================
Whitelisted endpoints for substituting a raw material on a Work Order with
one of its defined Alternative Items.

Two paths, chosen automatically from the *original* item's
`requires_substitution_approval` flag:

  * Not flagged (typical for packaging / excipients) — the substitution is
    applied immediately to the Work Order Item row. A Material Substitution
    Log is still written for the audit trail, but with status
    "Applied Immediately" — no approval step blocks production.

  * Flagged (typical for herbs / active ingredients) — a Material
    Substitution Log is created with status "Pending" and nothing changes
    on the Work Order yet. A Books Admin / System Manager must approve it
    (reason is always required) before the row is actually swapped. This
    mirrors classical Pratinidhi Dravya substitution: guarded, audited,
    reason-required.

Endpoints
---------
GET   get_substitution_options(work_order, work_order_item_row)
POST  request_material_substitution(work_order, work_order_item_row,
                                     alternative_item_code, reason)
GET   list_material_substitution_logs(approval_status="Pending", page=0, page_len=50)
POST  approve_material_substitution(log_name, remarks="")
POST  reject_material_substitution(log_name, rejection_reason)
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate

from zoho_books_clone.manufacturing import bom_engine, work_order_engine


_APPROVER_ROLES = {"Books Admin", "System Manager", "Administrator"}


def _require_approver():
    roles = set(frappe.get_roles(frappe.session.user))
    if not (roles & _APPROVER_ROLES):
        frappe.throw(
            _("Only Books Admin or System Manager can approve/reject Material Substitutions."),
            frappe.PermissionError,
        )


def _assert_work_order_company(work_order: str) -> None:
    """Material Substitution Log has no `company` field (so tenancy.py's
    permission_query_conditions never filters it) — scope via the parent
    Work Order's company instead."""
    from zoho_books_clone.utils.access import assert_company
    company = frappe.db.get_value("Work Order", work_order, "company")
    if company:
        assert_company(company)


# ─── Options ──────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_substitution_options(work_order: str, work_order_item_row: str) -> dict:
    """Return the available Alternative Items for a given Work Order Item
    row, plus whether picking one will need approval.

    Scrap Reuse feature, Phase 2: each option is annotated with live stock
    availability (available_qty / best_warehouse / warehouse breakdown) so
    the picker can show e.g. "120 kg available" instead of a blind item
    list, and so the frontend can grey out / warn on an alternative that
    looks good on paper but has nothing in stock right now.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    item_code = frappe.db.get_value("Work Order Item", work_order_item_row, "item_code")
    if not item_code:
        frappe.throw(_("Work Order Item row {0} not found.").format(work_order_item_row))

    options = bom_engine.get_alternative_items(item_code)

    company = frappe.db.get_value("Work Order", work_order, "company")
    from zoho_books_clone.inventory.utils import get_stock_by_warehouse
    for opt in options:
        warehouses = get_stock_by_warehouse(opt["alternative_item_code"], company)
        opt["available_qty"] = sum(w["qty"] for w in warehouses)
        opt["best_warehouse"] = warehouses[0]["warehouse"] if warehouses else None
        opt["warehouses"] = warehouses

    return {"item_code": item_code, "options": options}


# ─── Request ──────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["POST"])
def request_material_substitution(work_order: str, work_order_item_row: str,
                                   alternative_item_code: str, reason: str) -> dict:
    if frappe.session.user == "Guest":
        frappe.throw(_(""), frappe.PermissionError)

    from zoho_books_clone.utils.access import assert_can
    assert_can("Material Substitution Log", "create")
    _assert_work_order_company(work_order)

    if not (reason or "").strip():
        frappe.throw(_("A reason is required for any material substitution."))

    row = frappe.get_doc("Work Order Item", work_order_item_row)
    if row.parent != work_order:
        frappe.throw(_("Work Order Item row does not belong to {0}.").format(work_order))

    mapping = frappe.db.get_value(
        "Alternative Item",
        {"item_code": row.item_code, "alternative_item_code": alternative_item_code},
        ["conversion_factor"],
        as_dict=True,
    )
    if not mapping:
        frappe.throw(_(
            "{0} is not a defined Alternative Item for {1}. Add it under "
            "Manufacturing > Alternative Items first."
        ).format(alternative_item_code, row.item_code))

    requires_approval = bool(
        frappe.db.get_value("Item", row.item_code, "requires_substitution_approval")
    )

    log = frappe.new_doc("Material Substitution Log")
    log.work_order = work_order
    log.work_order_item_row = work_order_item_row
    log.original_item_code = row.item_code
    log.alternative_item_code = alternative_item_code
    log.conversion_factor = mapping.conversion_factor
    log.original_required_qty = row.required_qty
    log.new_required_qty = flt(row.required_qty) * flt(mapping.conversion_factor or 1)
    log.reason = reason
    log.substitution_type = "Full Swap"
    log.requires_approval = 1 if requires_approval else 0
    log.requested_by = frappe.session.user
    log.request_date = nowdate()

    if requires_approval:
        log.approval_status = "Pending"
        log.insert(ignore_permissions=True)
        frappe.db.commit()
        return {
            "status": "Pending",
            "log_name": log.name,
            "message": _(
                "{0} requires approval before substitution — request sent for review."
            ).format(row.item_code),
        }

    log.approval_status = "Applied Immediately"
    log.approved_by = frappe.session.user
    log.approval_date = nowdate()
    log.insert(ignore_permissions=True)

    result = work_order_engine.apply_row_substitution(
        work_order, work_order_item_row, alternative_item_code,
        mapping.conversion_factor, reason,
    )
    frappe.db.commit()

    return {
        "status": "Applied",
        "log_name": log.name,
        "row": result,
        "message": _("Substituted {0} \u2192 {1}.").format(
            log.original_item_code, alternative_item_code
        ),
    }


# ─── Request (Scrap Reuse — partial) ────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["POST"])
def request_scrap_reuse(work_order: str, work_order_item_row: str,
                         scrap_item_code: str, scrap_qty: float, reason: str) -> dict:
    """Scrap Reuse feature, Phase 3: request that PART of a raw-material
    row's required qty be filled from recovered scrap (see
    work_order_engine.apply_partial_scrap_substitution), instead of
    request_material_substitution's whole-row swap.

    Same approval branching as request_material_substitution -- keyed off
    the ORIGINAL item's requires_substitution_approval flag, not the scrap
    item's -- so a herb/active-ingredient row still routes scrap reuse
    through Books Admin approval exactly like a full swap would, while
    packaging/excipient rows apply immediately either way.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_(""), frappe.PermissionError)

    from zoho_books_clone.utils.access import assert_can
    assert_can("Material Substitution Log", "create")
    _assert_work_order_company(work_order)

    if not (reason or "").strip():
        frappe.throw(_("A reason is required for any material substitution."))

    scrap_qty = flt(scrap_qty)
    if scrap_qty <= 0:
        frappe.throw(_("Scrap Qty must be greater than zero."))

    row = frappe.get_doc("Work Order Item", work_order_item_row)
    if row.parent != work_order:
        frappe.throw(_("Work Order Item row does not belong to {0}.").format(work_order))

    original_item_code = row.original_item_code or row.item_code

    mapping = frappe.db.get_value(
        "Alternative Item",
        {"item_code": original_item_code, "alternative_item_code": scrap_item_code},
        ["conversion_factor", "source_type"],
        as_dict=True,
    )
    if not mapping:
        frappe.throw(_(
            "{0} is not a defined Alternative Item for {1}. Add it under "
            "Manufacturing > Alternative Items first."
        ).format(scrap_item_code, original_item_code))
    if mapping.source_type != "Recycled Scrap":
        frappe.throw(_(
            "{0} is mapped as a Fresh Stock alternative for {1}, not Recycled "
            "Scrap. Use Substitute Material for a fresh-stock swap instead."
        ).format(scrap_item_code, original_item_code))

    requires_approval = bool(
        frappe.db.get_value("Item", original_item_code, "requires_substitution_approval")
    )

    log = frappe.new_doc("Material Substitution Log")
    log.work_order = work_order
    log.work_order_item_row = work_order_item_row
    log.original_item_code = original_item_code
    log.alternative_item_code = scrap_item_code
    log.substitution_type = "Scrap Reuse"
    log.conversion_factor = mapping.conversion_factor
    log.original_required_qty = row.required_qty
    log.scrap_qty = scrap_qty
    log.reason = reason
    log.requires_approval = 1 if requires_approval else 0
    log.requested_by = frappe.session.user
    log.request_date = nowdate()

    if requires_approval:
        log.approval_status = "Pending"
        log.insert(ignore_permissions=True)
        frappe.db.commit()
        return {
            "status": "Pending",
            "log_name": log.name,
            "message": _(
                "{0} requires approval before scrap reuse — request sent for review."
            ).format(original_item_code),
        }

    log.approval_status = "Applied Immediately"
    log.approved_by = frappe.session.user
    log.approval_date = nowdate()
    log.insert(ignore_permissions=True)

    from zoho_books_clone.manufacturing.work_order_engine import apply_partial_scrap_substitution
    result = apply_partial_scrap_substitution(
        work_order, work_order_item_row, scrap_item_code, scrap_qty, reason,
    )

    log.new_required_qty = result["original_row"]["new_required_qty"]
    log.scrap_warehouse = result["scrap_row"]["source_warehouse"]
    log.new_work_order_item_row = result["scrap_row"]["work_order_item_row"]
    log.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "Applied",
        "log_name": log.name,
        "result": result,
        "message": _("{0} of {1} scrap applied against {2}.").format(
            scrap_qty, scrap_item_code, original_item_code
        ),
    }


# ─── List ─────────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def list_material_substitution_logs(
    approval_status: str = "Pending", page: int = 0, page_len: int = 50
) -> dict:
    filters: dict = {}
    if approval_status and approval_status != "all":
        filters["approval_status"] = approval_status

    page_len = min(int(page_len), 200)
    page = int(page)

    logs = frappe.get_all(
        "Material Substitution Log",
        filters=filters,
        fields=[
            "name", "work_order", "work_order_item_row",
            "original_item_code", "alternative_item_code", "conversion_factor",
            "original_required_qty", "new_required_qty", "reason",
            "requires_approval", "approval_status",
            "requested_by", "request_date", "approved_by", "approval_date",
            "rejection_reason", "approval_remarks", "creation",
            # Scrap Reuse feature, Phase 7: distinct log entries -- without
            # these, MaterialSubstitutions.vue's list/drawer had no way to
            # tell a Scrap Reuse action apart from a Full Swap, or show its
            # scrap-specific details.
            "substitution_type", "scrap_qty", "scrap_warehouse", "new_work_order_item_row",
        ],
        order_by="creation desc",
        limit=page_len,
        start=page * page_len,
        ignore_permissions=True,
    )
    total = frappe.db.count("Material Substitution Log", filters=filters)

    return {"logs": logs, "total": total, "page": page, "page_len": page_len}


# ─── Approve / Reject ──────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def approve_material_substitution(log_name: str, remarks: str = "") -> dict:
    _require_approver()

    from zoho_books_clone.utils.access import assert_can
    assert_can("Material Substitution Log", "write")

    doc = frappe.get_doc("Material Substitution Log", log_name)
    if doc.approval_status != "Pending":
        frappe.throw(_(
            "Only Pending substitutions can be approved. Current status: {0}."
        ).format(doc.approval_status))

    _assert_work_order_company(doc.work_order)

    if doc.substitution_type == "Scrap Reuse":
        result = work_order_engine.apply_partial_scrap_substitution(
            doc.work_order, doc.work_order_item_row, doc.alternative_item_code,
            doc.scrap_qty, doc.reason,
        )
        doc.new_required_qty = result["original_row"]["new_required_qty"]
        doc.scrap_warehouse = result["scrap_row"]["source_warehouse"]
        doc.new_work_order_item_row = result["scrap_row"]["work_order_item_row"]
    else:
        result = work_order_engine.apply_row_substitution(
            doc.work_order, doc.work_order_item_row, doc.alternative_item_code,
            doc.conversion_factor, doc.reason,
        )

    doc.approval_status = "Approved"
    doc.approved_by = frappe.session.user
    doc.approval_date = nowdate()
    if remarks:
        doc.approval_remarks = remarks
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "log_name": log_name,
        "approval_status": "Approved",
        "row": result,
        "message": _("Substitution approved and applied to {0}.").format(doc.work_order),
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def reject_material_substitution(log_name: str, rejection_reason: str) -> dict:
    _require_approver()

    from zoho_books_clone.utils.access import assert_can
    assert_can("Material Substitution Log", "write")

    if not (rejection_reason or "").strip():
        frappe.throw(_("Rejection Reason is required when rejecting a Material Substitution."))

    doc = frappe.get_doc("Material Substitution Log", log_name)
    if doc.approval_status != "Pending":
        frappe.throw(_(
            "Only Pending substitutions can be rejected. Current status: {0}."
        ).format(doc.approval_status))

    _assert_work_order_company(doc.work_order)

    doc.approval_status = "Rejected"
    doc.approved_by = frappe.session.user
    doc.approval_date = nowdate()
    doc.rejection_reason = rejection_reason
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "log_name": log_name,
        "approval_status": "Rejected",
        "message": _("Substitution request rejected — no changes made to {0}.").format(doc.work_order),
    }