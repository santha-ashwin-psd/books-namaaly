from __future__ import annotations
"""
QC Hold Manager — zoho_books_clone.quality.qc_hold_manager
===========================================================
Manages the quarantine / QC hold lifecycle for items that fail QC Inspection.

When a QC Inspection is submitted with status=Fail, this module:
  1. Flags the item with qc_hold=1 on the Item master
  2. Optionally creates a Stock Entry to transfer stock to a quarantine warehouse

When QC Hold is released:
  - Disposition = "Release to Stock"  -> Stock Entry: quarantine -> original warehouse
  - Disposition = "Scrap"             -> Stock Entry: quarantine -> scrap warehouse
  - Disposition = "Return to Supplier" -> records return note (manual process)

Public surface
--------------
handle_qc_result(doc, method=None)           -- on_submit hook on QC Inspection
validate_approval_request(doc, method=None)  -- validate hook on QC Approval Request
place_on_hold(inspection_name, quarantine_warehouse, hold_reason) -> dict
release_from_hold(inspection_name, disposition, target_warehouse)  -> dict
get_quarantine_summary() -> list
"""

import frappe
from frappe import _
from frappe.utils import nowdate, flt


# --- validate hook on QC Approval Request ------------------------------------

def validate_approval_request(doc, method=None):
    """
    Validate hook for QC Approval Request.
    Delegates to the controller's own validate() so the rejection_reason
    requirement is enforced through the standard doc_events path as well
    as via the controller directly.
    """
    if doc.approval_status == "Rejected" and not (doc.rejection_reason or "").strip():
        frappe.throw(_(
            "Rejection Reason is required when rejecting a QC Approval Request."
        ))


# --- on_submit hook -----------------------------------------------------------

def handle_qc_result(doc, method=None):
    """
    Called on_submit of QC Inspection.
    If status = Fail and a quarantine warehouse is configured in Books Settings,
    automatically places the item on QC Hold and creates a QC Approval Request
    so a QA Manager can formally approve/reject the disposition.
    """
    if doc.status != "Fail":
        return

    # Read default quarantine warehouse from Books Settings
    quarantine_wh = None
    try:
        quarantine_wh = frappe.db.get_single_value("Books Settings", "default_quarantine_warehouse")
    except Exception:
        pass

    if not quarantine_wh:
        # No quarantine warehouse configured — just flag the item
        _flag_item_on_hold(doc.item, True)
        frappe.msgprint(
            _("QC Inspection Failed for {0}. Item flagged for QC Hold. "
              "Configure 'Default Quarantine Warehouse' in Books Settings "
              "to enable automatic stock transfer to quarantine.").format(doc.item),
            indicator="red",
            title=_("QC Failed — Item on Hold"),
        )
    else:
        try:
            place_on_hold(doc.name, quarantine_wh, f"Auto-hold: QC Inspection {doc.name} Failed")
        except Exception:
            frappe.log_error(
                title=f"QC Hold auto-placement failed for {doc.name}",
                message=frappe.get_traceback(),
            )

    # Auto-create a QC Approval Request for the QA manager to action
    try:
        from zoho_books_clone.api.qc_approval import create_qc_approval_request
        create_qc_approval_request(
            inspection_name=doc.name,
            reason=f"Auto-raised: QC Inspection {doc.name} resolved to Fail.",
        )
    except Exception:
        # Non-fatal — hold is already placed; log and continue
        frappe.log_error(
            title=f"QC Approval Request auto-creation failed for {doc.name}",
            message=frappe.get_traceback(),
        )


# --- place_on_hold ------------------------------------------------------------

@frappe.whitelist()
def place_on_hold(
    inspection_name: str,
    quarantine_warehouse: str,
    hold_reason: str = "",
) -> dict:
    """
    Place an item on QC Hold after a failed QC Inspection.
    1. Flags Item.qc_hold = 1
    2. Updates QC Inspection with qc_hold=1, quarantine_warehouse, hold_reason
    3. Creates a Stock Entry to move stock to quarantine warehouse (if source warehouse known)
    Returns: {"status": "ok", "stock_entry": name_or_None, "message": "..."}
    """
    qci = frappe.get_doc("QC Inspection", inspection_name)

    if qci.status not in ("Fail", "Pending"):
        frappe.throw(_("QC Hold can only be placed on Failed or Pending inspections."))

    # Flag the item
    _flag_item_on_hold(qci.item, True)

    # Stamp the QC Inspection (if fields exist)
    _stamp_qc_hold_fields(inspection_name, quarantine_warehouse, hold_reason, on_hold=True)

    # Try to create a quarantine Stock Entry
    se_name = _create_quarantine_stock_entry(qci, quarantine_warehouse, hold_reason)

    msg = _("Item {0} placed on QC Hold. Stock moved to quarantine warehouse: {1}.").format(
        qci.item, quarantine_warehouse
    ) if se_name else _("Item {0} placed on QC Hold (no stock transfer — configure warehouses).").format(
        qci.item
    )

    frappe.msgprint(msg, indicator="orange", title=_("QC Hold Placed"), alert=True)

    return {
        "status": "ok",
        "stock_entry": se_name,
        "message": msg,
    }


# --- release_from_hold --------------------------------------------------------

@frappe.whitelist()
def release_from_hold(
    inspection_name: str,
    disposition: str,
    target_warehouse: str = "",
) -> dict:
    """
    Release an item from QC Hold.
    disposition options:
      - "Release to Stock"    -> Stock Entry: quarantine -> target_warehouse
      - "Scrap"               -> Stock Entry: quarantine -> scrap (no target)
      - "Return to Supplier"  -> Records note; no stock entry (manual process)

    Returns: {"status": "ok", "stock_entry": name_or_None, "message": "..."}
    """
    if disposition not in ("Release to Stock", "Scrap", "Return to Supplier"):
        frappe.throw(_("Invalid disposition. Choose: Release to Stock, Scrap, or Return to Supplier."))

    # QC Hold can only be released once the QA Manager has formally Approved
    # the linked QC Approval Request — a Pending or Rejected request must
    # never allow stock to leave quarantine.
    from zoho_books_clone.api.qc_approval import get_approval_status_for_inspection
    approval = get_approval_status_for_inspection(inspection_name)
    if not approval.get("found"):
        frappe.throw(_(
            "Cannot release QC Hold: no QC Approval Request found for {0}. "
            "A QA Manager must review and approve the disposition first."
        ).format(inspection_name))
    if approval.get("approval_status") != "Approved":
        frappe.throw(_(
            "Cannot release QC Hold: the linked QC Approval Request {0} is "
            "<b>{1}</b>, not Approved. Stock cannot leave quarantine until "
            "a QA Manager approves the request."
        ).format(approval.get("request_name"), approval.get("approval_status")))

    qci = frappe.get_doc("QC Inspection", inspection_name)
    item_code = qci.item

    # Get quarantine warehouse from QC Inspection
    quarantine_wh = None
    try:
        quarantine_wh = frappe.db.get_value("QC Inspection", inspection_name, "quarantine_warehouse")
    except Exception:
        pass

    if not quarantine_wh:
        try:
            quarantine_wh = frappe.db.get_single_value("Books Settings", "default_quarantine_warehouse")
        except Exception:
            pass

    se_name = None

    if disposition == "Release to Stock":
        if not target_warehouse:
            frappe.throw(_("Target warehouse is required for 'Release to Stock'."))
        if quarantine_wh:
            se_name = _create_release_stock_entry(item_code, quarantine_wh, target_warehouse, inspection_name)

    elif disposition == "Scrap":
        scrap_wh = None
        try:
            scrap_wh = frappe.db.get_single_value("Books Settings", "default_scrap_warehouse")
        except Exception:
            pass
        if quarantine_wh and scrap_wh:
            se_name = _create_release_stock_entry(item_code, quarantine_wh, scrap_wh, inspection_name,
                                                   purpose="Material Transfer", note="Scrapped after QC Fail")

    elif disposition == "Return to Supplier":
        # Record-keeping only — actual return is a manual process
        frappe.get_doc({
            "doctype": "Activity Log",
            "user": frappe.session.user,
            "operation": "Update",
            "status": "Success",
            "reference_doctype": "QC Inspection",
            "reference_name": inspection_name,
            "content": f"QC Hold Released — Disposition: Return to Supplier. Item: {item_code}.",
        }).insert(ignore_permissions=True)

    # Clear the hold flag
    _flag_item_on_hold(item_code, False)
    _stamp_qc_hold_fields(inspection_name, quarantine_wh or "", "", on_hold=False)

    frappe.db.commit()

    msg = _("QC Hold released for {0}. Disposition: {1}.").format(item_code, disposition)
    return {"status": "ok", "stock_entry": se_name, "message": msg}


# --- get_quarantine_summary ---------------------------------------------------

@frappe.whitelist()
def get_quarantine_summary() -> list:
    """
    Return all items currently on QC Hold.
    Returns list of dicts with item, quarantine_warehouse, inspection, reason, date.
    """
    try:
        rows = frappe.get_all(
            "QC Inspection",
            filters={"docstatus": 1, "status": "Fail"},
            fields=["name", "item", "item_name", "inspection_date", "reference_type",
                    "reference_name", "inspected_by"],
            order_by="inspection_date desc",
            ignore_permissions=True,
        )
        # Enrich with qc_hold field if it exists
        result = []
        has_qc_hold = frappe.db.has_column("QC Inspection", "qc_hold")
        has_qwh     = frappe.db.has_column("QC Inspection", "quarantine_warehouse")
        for r in rows:
            if has_qc_hold:
                r["on_hold"] = bool(frappe.db.get_value("QC Inspection", r["name"], "qc_hold"))
            else:
                r["on_hold"] = True  # Assume hold for all failed inspections
            if has_qwh:
                r["quarantine_warehouse"] = frappe.db.get_value(
                    "QC Inspection", r["name"], "quarantine_warehouse"
                )
            result.append(r)
        return result
    except Exception:
        return []


# --- Stock Entry helpers ------------------------------------------------------

def _create_quarantine_stock_entry(qci, quarantine_warehouse: str, reason: str) -> str | None:
    """
    Create a Stock Entry to move stock from the source warehouse (from the reference doc)
    to the quarantine warehouse.
    """
    try:
        source_wh = _get_source_warehouse(qci)
        if not source_wh:
            return None

        # Get qty from reference doc item row
        qty = _get_item_qty_from_reference(qci)
        if not flt(qty):
            return None

        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = "Material Transfer"
        se.purpose          = "Material Transfer"
        se.remarks          = f"QC Hold: {reason} | QC Inspection: {qci.name}"
        se.append("items", {
            "item_code":     qci.item,
            "qty":           qty,
            "s_warehouse":   source_wh,
            "t_warehouse":   quarantine_warehouse,
            "basic_rate":    frappe.db.get_value("Item", qci.item, "last_purchase_rate") or 0,
        })
        se.insert(ignore_permissions=True)
        se.submit()
        frappe.db.commit()
        return se.name
    except Exception:
        frappe.log_error(
            title="Quarantine Stock Entry failed",
            message=frappe.get_traceback(),
        )
        return None


def _create_release_stock_entry(
    item_code: str,
    from_warehouse: str,
    to_warehouse: str,
    inspection_name: str,
    purpose: str = "Material Transfer",
    note: str = "",
) -> str | None:
    """Create a Stock Entry to release stock from quarantine."""
    try:
        # Get qty from quarantine stock (actual available qty)
        qty = flt(frappe.db.get_value(
            "Bin",
            {"item_code": item_code, "warehouse": from_warehouse},
            "actual_qty",
        ))
        if not qty:
            frappe.msgprint(
                _("No stock found in quarantine warehouse {0} for item {1}.").format(
                    from_warehouse, item_code
                ),
                indicator="orange",
            )
            return None

        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = purpose
        se.purpose          = purpose
        se.remarks = f"QC Hold Release | QC Inspection: {inspection_name}" + (f" | {note}" if note else "")
        se.append("items", {
            "item_code":   item_code,
            "qty":         qty,
            "s_warehouse": from_warehouse,
            "t_warehouse": to_warehouse,
        })
        se.insert(ignore_permissions=True)
        se.submit()
        frappe.db.commit()
        return se.name
    except Exception:
        frappe.log_error(
            title="QC Hold Release Stock Entry failed",
            message=frappe.get_traceback(),
        )
        return None


def _get_source_warehouse(qci) -> str | None:
    """
    Infer the source warehouse from the reference document.

    - Purchase Receipt / Purchase Invoice (Incoming): stock lands in the row's
      `warehouse` (or `t_warehouse` for stock-updating invoices) — that's the
      warehouse to pull from into quarantine.
    - Stock Entry (In Process / Manufacture): finished goods land in `t_warehouse`.
    - Delivery Note / Sales Invoice (Outgoing): stock is picked from the row's
      `warehouse` (or `s_warehouse` for stock-updating invoices) before dispatch.
    """
    try:
        doc = frappe.get_doc(qci.reference_type, qci.reference_name)
        for row in (getattr(doc, "items", []) or []):
            ic = getattr(row, "item_code", None) or getattr(row, "item", None)
            if ic != qci.item:
                continue

            if qci.reference_type in ("Purchase Receipt", "Purchase Invoice"):
                return getattr(row, "warehouse", None) or getattr(row, "t_warehouse", None)
            elif qci.reference_type == "Stock Entry":
                return getattr(row, "t_warehouse", None)
            elif qci.reference_type in ("Delivery Note", "Sales Invoice"):
                return getattr(row, "warehouse", None) or getattr(row, "s_warehouse", None)
    except Exception:
        pass
    return None


def _get_item_qty_from_reference(qci) -> float:
    """Get item quantity from the reference document's items table."""
    try:
        doc = frappe.get_doc(qci.reference_type, qci.reference_name)
        for row in (getattr(doc, "items", []) or []):
            ic = getattr(row, "item_code", None) or getattr(row, "item", None)
            if ic == qci.item:
                return flt(getattr(row, "qty", 0) or getattr(row, "received_qty", 0))
    except Exception:
        pass
    return 0.0


# --- Item flag helpers --------------------------------------------------------

def _flag_item_on_hold(item_code: str, on_hold: bool):
    """Set/clear the qc_hold custom field on the Item master."""
    try:
        if frappe.db.has_column("Item", "qc_hold"):
            frappe.db.set_value("Item", item_code, "qc_hold", 1 if on_hold else 0,
                                update_modified=False)
    except Exception:
        pass


def _stamp_qc_hold_fields(
    inspection_name: str,
    quarantine_warehouse: str,
    hold_reason: str,
    on_hold: bool,
):
    """Stamp qc_hold, quarantine_warehouse, hold_reason on QC Inspection (if fields exist)."""
    try:
        update = {}
        if frappe.db.has_column("QC Inspection", "qc_hold"):
            update["qc_hold"] = 1 if on_hold else 0
        if quarantine_warehouse and frappe.db.has_column("QC Inspection", "quarantine_warehouse"):
            update["quarantine_warehouse"] = quarantine_warehouse
        if hold_reason and frappe.db.has_column("QC Inspection", "hold_reason"):
            update["hold_reason"] = hold_reason
        if update:
            frappe.db.set_value("QC Inspection", inspection_name, update, update_modified=False)
    except Exception:
        pass