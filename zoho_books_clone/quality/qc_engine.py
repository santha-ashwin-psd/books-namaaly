from __future__ import annotations
"""
QC Engine — zoho_books_clone.quality.qc_engine
===============================================
The 4th cross-cutting middleware layer (alongside _CV, _SL, _TN).

Wired via hooks.py doc_events to 7 doctypes on on_submit/before_submit,
and MUST run BEFORE _SL (stock_link) so QC state is known before stock moves.

Design:
  - Soft-warn mode  (default): msgprint, never raises
  - Hard-block mode (opt-in via Books Settings qc_hard_block=1): frappe.throw() blocks submit
  - QC coverage is tracked per reference-doc ROW (via each row's own
    `quality_inspection` Link, stamped at creation time), not just per
    item code — so two rows of the same item (different batches, a split
    receipt) are each independently gated rather than one row's passed
    inspection silently covering the other.

Public surface
--------------
check_qc_before_stock_link(doc, method=None)              -- on_submit hook (QC gate)
auto_create_qc_for_purchase_receipt(doc, method=None)     -- before_submit hook (PR)
auto_create_qc_for_purchase_invoice(doc, method=None)      -- before_submit hook (PI)
auto_create_qc_for_stock_entry(doc, method=None)          -- before_submit hook (SE Manufacture)
auto_create_qc_for_delivery_note(doc, method=None)        -- before_submit hook (DN)
auto_create_qc_for_sales_invoice(doc, method=None)        -- before_submit hook (SI)
doc_requires_qc(doc) -> bool
get_linked_qc_status(doc) -> str
create_qc_inspection_for_item(reference_type, reference_name, item_code, inspection_type, batch_no) -> str
get_qc_summary_for_doc(reference_type, reference_name) -> dict
"""

import frappe
from frappe import _
from frappe.utils import nowdate, flt


# --- Inspection type mapping --------------------------------------------------

_DOCTYPE_TO_INSPECTION_TYPE = {
    "Purchase Receipt":  "Incoming",
    "Purchase Invoice":  "Incoming",
    "Delivery Note":     "Outgoing",
    "Sales Invoice":     "Outgoing",
    "Stock Entry":       "In Process",
}

_ITEM_FLAG_FOR_INSPECTION_TYPE = {
    "Incoming":   "inspection_required_before_purchase",
    "Outgoing":   "inspection_required_before_delivery",
    "In Process": "inspection_required_before_manufacture",
}


# --- Point 4: QC Gate (on_submit) --------------------------------------------

def check_qc_before_stock_link(doc, method=None):
    """
    Called on_submit for: Purchase Receipt, Purchase Invoice,
    Delivery Note, Sales Invoice, Stock Entry.

    MUST be listed before _SL handlers in hooks.py doc_events.

    Flow:
      1. Books Settings master switch off -> skip
      2. No items require QC -> skip
      3. QC status is Pass -> proceed normally
      4. QC is Fail / Pending / Missing:
           if hard_block mode (Books Settings qc_hard_block=1) -> frappe.throw() -- blocks
           elif doc.flags.ignore_qc_warning -> log override + proceed
           else -> frappe.msgprint (orange) -> SPA shows confirm dialog
    """
    if not _qc_master_switch_on():
        return

    if not doc_requires_qc(doc):
        return

    summary = get_qc_summary_for_doc(doc.doctype, doc.name)
    status  = summary.get("overall_status", "Missing")

    if status == "Pass":
        return

    failed_items  = summary.get("failed_items", [])
    missing_items = summary.get("missing_items", [])
    all_problems  = failed_items + missing_items
    item_list     = ", ".join(all_problems[:5])
    if len(all_problems) > 5:
        item_list += f" ... (+{len(all_problems) - 5} more)"

    if status == "Fail":
        msg = _("QC Inspection <b>Failed</b> for item(s): {0}.").format(item_list)
    elif status == "Pending":
        msg = _("QC Inspection is still <b>Pending</b> for item(s): {0}.").format(item_list)
    else:
        msg = _("No QC Inspection found for item(s): {0}.").format(item_list)

    # Hard-block mode -- throw and stop submit entirely
    if _qc_hard_block_on(getattr(doc, "company", None)):
        frappe.throw(
            msg + "<br><br>" + _(
                "Submission blocked until QC is cleared. "
                "Please complete and submit a QC Inspection first."
            ),
            title=_("Quality Control -- Submission Blocked"),
        )
        return

    # Soft-warn with override
    if doc.flags.get("ignore_qc_warning"):
        _log_qc_override(doc, summary)
        frappe.msgprint(
            _("QC warning overridden for {0} {1}. Proceeding with submission.").format(
                doc.doctype, doc.name
            ),
            indicator="orange",
            title=_("QC Override Recorded"),
            alert=True,
        )
        return

    frappe.msgprint(
        msg + "<br><br>" + _("Submit anyway?"),
        indicator="orange",
        title=_("Quality Control Warning"),
        raise_exception=False,
    )


# --- Shared implementation behind every "auto-create QC" before_submit hook -

def _auto_create_qc_for_rows(
    doc,
    flag_field: str,
    inspection_type: str,
    success_message: str,
    success_title: str,
    row_filter=None,
    on_created=None,
) -> list:
    """
    Shared implementation behind every before_submit "auto-create a draft QC
    Inspection for flagged items" hook (Purchase Receipt, Stock Entry
    Manufacture, Delivery Note, Sales Invoice). These were previously four
    near-identical ~55-line copy-pasted blocks; a fix to the shared logic
    (existing-inspection check, error handling, etc.) had to be applied to
    each one separately and was easy to forget in the others.

    For every row in doc.items:
      - skip if it has no item_code
      - skip if row_filter(row) returns False (e.g. Stock Entry's
        finished-goods-only / t_warehouse rule)
      - skip if Item.<flag_field> is not set
      - skip if a non-cancelled QC Inspection already exists for this
        (reference_type, reference_name, item)
      - otherwise create one via create_qc_inspection_for_item(), then call
        on_created(qci_name, row) if given (e.g. Stock Entry's work_order stamp)

    Shows one summary msgprint if any inspections were created.
    success_message is a translated format string using {0}=count, {1}=names.
    Returns the list of created QC Inspection names.
    """
    if not _qc_master_switch_on():
        return []

    created = []
    for row in (getattr(doc, "items", []) or []):
        item_code = getattr(row, "item_code", None) or getattr(row, "item", None)
        if not item_code:
            continue
        if row_filter and not row_filter(row):
            continue
        if not frappe.db.get_value("Item", item_code, flag_field):
            continue

        # Skip if this row already has a QC Inspection linked and it's not
        # cancelled — checked at the row level (not just by item) so two
        # rows of the same item (different batches, or a split receipt)
        # each get their own inspection rather than one row's link being
        # mistaken for coverage of the other.
        existing = getattr(row, "quality_inspection", None)
        if existing and frappe.db.get_value("QC Inspection", existing, "docstatus") != 2:
            continue

        try:
            qci_name = create_qc_inspection_for_item(
                doc.doctype, doc.name, item_code, inspection_type,
                batch_no=getattr(row, "batch_no", None),
                inspected_qty=getattr(row, "qty", None) or getattr(row, "received_qty", None),
            )
            if getattr(row, "doctype", None) and getattr(row, "name", None) \
                    and frappe.db.has_column(row.doctype, "quality_inspection"):
                # Set the in-memory field on the row FIRST. This hook runs
                # in before_submit, before Frappe's own submit flow writes
                # the whole document (including this child table) back to
                # the DB via db_update() -- a frappe.db.set_value() alone,
                # with the in-memory `row.quality_inspection` still blank,
                # would get silently overwritten back to blank when that
                # later db_update() flushes memory over what we just wrote.
                # Setting it here as well as via db.set_value covers both
                # the in-flight submit (via memory) and any caller that
                # doesn't go through the normal submit flow afterward.
                row.quality_inspection = qci_name
                frappe.db.set_value(row.doctype, row.name, "quality_inspection", qci_name,
                                     update_modified=False)
            if on_created:
                on_created(qci_name, row)
            created.append(qci_name)
        except Exception:
            frappe.log_error(
                title=f"QC auto-create failed for {item_code} on {doc.name}",
                message=frappe.get_traceback(),
            )

    if created:
        frappe.msgprint(
            success_message.format(len(created), ", ".join(created)),
            indicator="blue",
            title=success_title,
            alert=True,
        )

    return created


# --- Phase 2: stamp target_warehouse before quarantine routing overrides row -

def _stamp_qc_target_warehouse(doc, row, qci_name):
    """
    Shared on_created callback for the Incoming (Purchase Receipt / Purchase
    Invoice) auto-create hooks.

    Stamps QC Inspection.target_warehouse with the row's ORIGINAL intended
    destination warehouse — computed via stock_link.resolve_intended_warehouse
    using the exact same resolution chain _stock_rows() uses — BEFORE
    stock_link's on_submit hook (which runs after this before_submit hook per
    hooks.py doc_events ordering) has a chance to override the row and route
    it into quarantine instead.

    Without this, once Phase 2's routing sends a flagged row's stock into
    quarantine, there would be no record left anywhere of where that stock
    was originally headed — Phase 3's release-on-pass would have nothing to
    release TO.

    Best-effort: never blocks QC Inspection creation if the stamp fails, and
    is a no-op on databases that haven't migrated the target_warehouse
    column yet (Phase 0's own guard, checked here again defensively).
    """
    if not frappe.db.has_column("QC Inspection", "target_warehouse"):
        return
    try:
        from zoho_books_clone.inventory.stock_link import resolve_intended_warehouse
        intended = resolve_intended_warehouse(doc, row)
        if intended:
            frappe.db.set_value(
                "QC Inspection", qci_name, "target_warehouse", intended,
                update_modified=False,
            )
    except Exception:
        frappe.log_error(
            title=f"Failed to stamp target_warehouse on {qci_name}",
            message=frappe.get_traceback(),
        )


# --- Point 2: Auto-create QC for Purchase Receipt ----------------------------

def auto_create_qc_for_purchase_receipt(doc, method=None):
    """
    before_submit hook on Purchase Receipt.
    For every item with inspection_required_before_purchase=1,
    automatically creates a draft QC Inspection (if not already existing).
    Inspector receives a blue notification with the inspection name(s).

    Phase 2: also stamps target_warehouse (see _stamp_qc_target_warehouse)
    so quarantine routing in stock_link.py has somewhere to release stock to.
    """
    _auto_create_qc_for_rows(
        doc,
        flag_field="inspection_required_before_purchase",
        inspection_type="Incoming",
        success_message=_("QC Inspection(s) auto-created for {0} item(s): {1}. "
                           "Please complete readings before stock is accepted."),
        success_title=_("QC Inspections Created"),
        on_created=lambda qci_name, row: _stamp_qc_target_warehouse(doc, row, qci_name),
    )


# --- Phase 1: Auto-create QC for Purchase Invoice -----------------------------

def auto_create_qc_for_purchase_invoice(doc, method=None):
    """
    before_submit hook on Purchase Invoice.

    Mirrors auto_create_qc_for_purchase_receipt above -- this app also moves
    stock on Purchase Invoice submit (see stock_link.on_purchase_invoice_submit),
    but until now Purchase Invoice was the only one of the five QC-gated
    doctypes with no before_submit auto-create hook at all, so a flagged item
    coming in through a Purchase Invoice (rather than a Purchase Receipt) got
    no QC Inspection created and, in soft-warn mode (the default), sailed
    straight into usable stock with nothing but a dismissible msgprint.

    Phase 2: where the stock lands now DOES change for flagged items --
    stock_link._stock_rows() routes the flagged row into quarantine instead
    of its normally-resolved warehouse. This hook stamps target_warehouse
    (see _stamp_qc_target_warehouse) with that normally-resolved warehouse
    before that override happens, so it's on record for Phase 3's release.
    """
    _auto_create_qc_for_rows(
        doc,
        flag_field="inspection_required_before_purchase",
        inspection_type="Incoming",
        success_message=_("QC Inspection(s) auto-created for {0} item(s): {1}. "
                           "Please complete readings before stock is accepted."),
        success_title=_("QC Inspections Created"),
        on_created=lambda qci_name, row: _stamp_qc_target_warehouse(doc, row, qci_name),
    )


# --- Point 3: Auto-create QC for Finished Goods (Stock Entry Manufacture) ----

def _resolve_fg_quarantine_warehouse(company: str | None) -> str | None:
    """
    Phase 5 — resolve the FG quarantine warehouse for a company, falling
    back to the RM one if no FG-specific warehouse is configured. Mirrors
    the fallback Books Company.default_fg_quarantine_warehouse's own field
    description already promises.
    """
    if not company:
        return None
    fg_wh = frappe.db.get_value("Books Company", company, "default_fg_quarantine_warehouse")
    if fg_wh:
        return fg_wh
    return frappe.db.get_value("Books Company", company, "default_quarantine_warehouse")


def _stamp_and_route_fg_quarantine(doc, row, qci_name):
    """
    Phase 5 — on_created callback for Manufacturing finished-goods QC rows.

    Unlike Purchase Receipt/Invoice (Phase 2), Stock Entry Manufacture IS
    the physical stock movement itself — there's no separate stock_link.py
    proxy document building a derived Stock Entry afterward. So quarantine
    routing here means mutating THIS row's own t_warehouse directly,
    in-memory, right now in before_submit — before Frappe's standard submit
    flow builds the stock ledger entries from exactly these in-memory rows.

    Order matters: target_warehouse must be captured from row.t_warehouse
    BEFORE it gets overridden, same as Phase 2's before_submit stamping for
    Purchase Receipt/Invoice.

      1. Stamp QC Inspection.target_warehouse with the row's original,
         intended FG destination (whatever the Work Order / user had set
         t_warehouse to).
      2. Resolve this company's FG quarantine warehouse (see
         _resolve_fg_quarantine_warehouse).
      3. If one is configured, override row.t_warehouse to it and stamp
         quarantine_warehouse + release_status="Not Released" on the QC
         Inspection — the exact same bookkeeping Phase 2's
         stock_link._maybe_route_to_quarantine does for incoming rows, so
         Phase 3's _release_quarantine_on_pass (qc_hold_manager.py) can
         release finished goods out of FG quarantine the same way it
         already releases raw materials out of RM quarantine, with no
         changes needed there.
      4. If no quarantine warehouse is configured at all, this is a no-op
         beyond the target_warehouse stamp — the row lands wherever it was
         already headed, unchanged (soft-warn only, same as Purchase before
         Phase 2 for a company that hasn't set one up yet).
    """
    if not frappe.db.has_column("QC Inspection", "target_warehouse"):
        return
    try:
        original_t_warehouse = getattr(row, "t_warehouse", None)
        if original_t_warehouse:
            frappe.db.set_value(
                "QC Inspection", qci_name, "target_warehouse", original_t_warehouse,
                update_modified=False,
            )

        fg_quarantine_wh = _resolve_fg_quarantine_warehouse(getattr(doc, "company", None))
        if not fg_quarantine_wh:
            return  # nothing configured -- row stays exactly where it was

        row.t_warehouse = fg_quarantine_wh

        update = {}
        if frappe.db.has_column("QC Inspection", "release_status"):
            update["release_status"] = "Not Released"
        if frappe.db.has_column("QC Inspection", "quarantine_warehouse"):
            update["quarantine_warehouse"] = fg_quarantine_wh
        if update:
            frappe.db.set_value("QC Inspection", qci_name, update, update_modified=False)
    except Exception:
        frappe.log_error(
            title=f"FG quarantine routing failed for {qci_name}",
            message=frappe.get_traceback(),
        )


def auto_create_qc_for_stock_entry(doc, method=None):
    """
    before_submit hook on Stock Entry.
    For Manufacture type only: creates draft QC Inspection for finished goods
    (items going INTO stock — t_warehouse set — with inspection_required_before_manufacture=1).

    Phase 5: also routes each flagged finished-goods row into FG quarantine
    (see _stamp_and_route_fg_quarantine) instead of its normally-set
    t_warehouse — the same pre-emptive-quarantine-at-creation pattern Phase 2
    applies to incoming Purchase rows, adapted for the fact that Stock Entry
    is itself the physical movement rather than something stock_link.py
    proxies.
    """
    if getattr(doc, "stock_entry_type", "") != "Manufacture":
        return

    def _stamp_work_order(qci_name, row):
        # Stamp work_order traceability if column exists
        if (frappe.db.has_column("QC Inspection", "work_order")
                and getattr(doc, "work_order", None)):
            frappe.db.set_value(
                "QC Inspection", qci_name, "work_order", doc.work_order,
                update_modified=False,
            )

    def _on_created(qci_name, row):
        _stamp_work_order(qci_name, row)
        _stamp_and_route_fg_quarantine(doc, row, qci_name)

    _auto_create_qc_for_rows(
        doc,
        flag_field="inspection_required_before_manufacture",
        inspection_type="In Process",
        success_message=_("Finished Goods QC Inspection(s) auto-created: {1}. "
                           "Please complete readings for the manufactured batch."),
        success_title=_("Finished Goods QC Created"),
        # Only finished goods rows (items being produced into t_warehouse)
        row_filter=lambda row: bool(getattr(row, "t_warehouse", None)),
        on_created=_on_created,
    )


# --- Point 5: Auto-create QC for Delivery Note (Outgoing) -------------------

def auto_create_qc_for_delivery_note(doc, method=None):
    """
    before_submit hook on Delivery Note.
    For every item with inspection_required_before_delivery=1,
    automatically creates a draft QC Inspection (if not already existing).
    Inspector receives a blue notification with the inspection name(s).
    """
    _auto_create_qc_for_rows(
        doc,
        flag_field="inspection_required_before_delivery",
        inspection_type="Outgoing",
        success_message=_("Outgoing QC Inspection(s) auto-created for {0} item(s): {1}. "
                           "Please complete readings before goods are dispatched."),
        success_title=_("Outgoing QC Inspections Created"),
    )


# --- Point 6: Auto-create QC for Sales Invoice (Outgoing) -------------------

def auto_create_qc_for_sales_invoice(doc, method=None):
    """
    before_submit hook on Sales Invoice.
    For every item with inspection_required_before_delivery=1,
    automatically creates a draft QC Inspection (if not already existing).
    Uses the same Outgoing inspection type as Delivery Note per
    _DOCTYPE_TO_INSPECTION_TYPE.
    Inspector receives a blue notification with the inspection name(s).
    """
    _auto_create_qc_for_rows(
        doc,
        flag_field="inspection_required_before_delivery",
        inspection_type="Outgoing",
        success_message=_("Outgoing QC Inspection(s) auto-created for {0} item(s): {1}. "
                           "Please complete readings before invoice is finalised."),
        success_title=_("Outgoing QC Inspections Created"),
    )


# --- doc_requires_qc ---------------------------------------------------------

def doc_requires_qc(doc) -> bool:
    """
    Return True if ANY item row on the document has the relevant
    inspection_required_* flag set on the Item master.
    """
    inspection_type = _DOCTYPE_TO_INSPECTION_TYPE.get(doc.doctype)
    if not inspection_type:
        return False

    if doc.doctype == "Stock Entry":
        if getattr(doc, "stock_entry_type", "") != "Manufacture":
            return False

    flag_field = _ITEM_FLAG_FOR_INSPECTION_TYPE.get(inspection_type)
    if not flag_field:
        return False

    items = getattr(doc, "items", []) or []
    for row in items:
        item_code = getattr(row, "item_code", None) or getattr(row, "item", None)
        if not item_code:
            continue
        # Stock Entry rows can be raw materials being consumed
        # (s_warehouse set, t_warehouse blank) as well as finished goods
        # being produced (t_warehouse set). Only finished-goods rows are
        # ever QC'd — auto_create_qc_for_stock_entry and
        # get_qc_summary_for_doc both already apply this same filter; it
        # must be applied here too, or this function can report "QC
        # required" for a raw-material row that no other part of the QC
        # flow will ever create or look for an inspection against.
        if doc.doctype == "Stock Entry" and not getattr(row, "t_warehouse", None):
            continue
        flag_val = frappe.db.get_value("Item", item_code, flag_field)
        if flag_val:
            return True
    return False


# --- get_linked_qc_status ----------------------------------------------------

def get_linked_qc_status(doc) -> str:
    """Look up QC Inspection(s) referencing this doc. Returns: Pass|Fail|Pending|Missing"""
    summary = get_qc_summary_for_doc(doc.doctype, doc.name)
    return summary.get("overall_status", "Missing")


# --- get_qc_summary_for_doc --------------------------------------------------

def get_qc_summary_for_doc(reference_type: str, reference_name: str) -> dict:
    """
    Return full QC status summary for all items on the document.
    Returns dict with overall_status, inspections, passed/failed/pending/missing item lists.

    Row-scoped, not item-scoped: matching used to be done purely by item
    code across the whole document, so if the same item appeared on two
    rows (e.g. two different batches, or a partial receipt split across
    rows) one row's QC Inspection would silently "cover" the other row
    too. Each row's own `quality_inspection` Link (stamped at creation
    time by create_qc_inspection_for_item / the manual-create API) is now
    checked first, so each row is tracked independently. Older inspections
    created before this link existed won't have it set on their row, so we
    fall back to the legacy by-item match for those specifically.
    """
    inspection_type = _DOCTYPE_TO_INSPECTION_TYPE.get(reference_type)

    inspections = frappe.get_all(
        "QC Inspection",
        filters={
            "reference_type": reference_type,
            "reference_name": reference_name,
            "docstatus": 1,
        },
        fields=["name", "item", "status", "inspection_type", "inspection_date", "inspected_by"],
        ignore_permissions=True,
    )

    inspections_by_name = {qi["name"]: qi for qi in inspections}
    # Legacy fallback only: first inspection found for a given item, used
    # solely for rows whose own quality_inspection link is blank.
    legacy_by_item = {}
    for qi in inspections:
        legacy_by_item.setdefault(qi["item"], qi)

    doc = frappe.get_doc(reference_type, reference_name)
    flag_field = _ITEM_FLAG_FOR_INSPECTION_TYPE.get(inspection_type, "")
    rows_needing_qc = []
    for row in (getattr(doc, "items", []) or []):
        item_code = getattr(row, "item_code", None) or getattr(row, "item", None)
        if not item_code:
            continue
        # Stock Entry rows can represent raw materials being consumed
        # (s_warehouse set, t_warehouse blank) as well as finished goods
        # being produced (t_warehouse set). Only finished-goods rows are
        # ever QC'd here — same restriction auto_create_qc_for_stock_entry
        # and doc_requires_qc already apply — otherwise a raw material row
        # flagged inspection_required_before_manufacture would demand a QC
        # Inspection that auto-create never creates, an unresolvable
        # "Missing QC" status.
        if reference_type == "Stock Entry" and not getattr(row, "t_warehouse", None):
            continue
        if flag_field and frappe.db.get_value("Item", item_code, flag_field):
            rows_needing_qc.append((row, item_code))

    if not rows_needing_qc:
        return {"overall_status": "Pass", "inspections": inspections,
                "passed_items": [], "failed_items": [], "pending_items": [],
                "missing_items": [], "total_items_requiring_qc": 0}

    passed  = []
    failed  = []
    pending = []
    missing = []

    for row, item_code in rows_needing_qc:
        batch = getattr(row, "batch_no", None)
        label = f"{item_code} (Batch {batch})" if batch else item_code

        qi = None
        row_qi_name = getattr(row, "quality_inspection", None)
        if row_qi_name:
            qi = inspections_by_name.get(row_qi_name)
        if not qi:
            qi = legacy_by_item.get(item_code)

        if not qi:
            missing.append(label)
        elif qi["status"] == "Pass":
            passed.append(label)
        elif qi["status"] == "Fail":
            failed.append(label)
        else:
            pending.append(label)

    if failed:
        overall = "Fail"
    elif missing:
        overall = "Missing"
    elif pending:
        overall = "Pending"
    else:
        overall = "Pass"

    return {
        "overall_status":           overall,
        "inspections":              inspections,
        "passed_items":             passed,
        "failed_items":             failed,
        "pending_items":            pending,
        "missing_items":            missing,
        "total_items_requiring_qc": len(rows_needing_qc),
    }


# --- create_qc_inspection_for_item -------------------------------------------

def create_qc_inspection_for_item(
    reference_type: str,
    reference_name: str,
    item_code: str,
    inspection_type: str | None = None,
    batch_no: str | None = None,
    inspected_qty: float | None = None,
) -> str:
    """
    Create a draft QC Inspection for a specific item on a reference document.
    Copies parameters from the resolved template (if any).
    batch_no, when given (e.g. from a Stock Entry Detail / Purchase Receipt
    Item row that carries batch tracking), is stamped onto the inspection so
    batch-level traceability survives into QC records. Not every reference
    doctype's rows carry a batch (e.g. Delivery Note / Sales Invoice items in
    this app don't), so this is left blank in that case rather than guessed.
    inspected_qty, when given, seeds accepted_qty/rejected_qty so the
    inspector can adjust the accept/reject split before submitting rather
    than having to type the full qty in from scratch.
    Returns the new QC Inspection name.
    """
    if not inspection_type:
        inspection_type = _DOCTYPE_TO_INSPECTION_TYPE.get(reference_type, "Incoming")

    template_name = _resolve_template(item_code, inspection_type)
    item_name_val = frappe.db.get_value("Item", item_code, "item_name") or item_code

    qci = frappe.new_doc("QC Inspection")
    qci.inspection_type        = inspection_type
    qci.reference_type         = reference_type
    qci.reference_name         = reference_name
    qci.item                   = item_code
    qci.item_name              = item_name_val
    qci.batch_no                = batch_no or ""
    qci.inspection_date        = nowdate()
    qci.inspected_by           = frappe.session.user
    qci.qc_inspection_template = template_name
    qci.status                 = "Pending"

    if inspected_qty:
        qci.inspected_qty = flt(inspected_qty)
        # Sane starting point: assume the whole qty passes until readings say
        # otherwise. _compute_qty_split on the controller re-derives this
        # from the accept/reject split on submit, so this is just a UI default.
        qci.accepted_qty = flt(inspected_qty)
        qci.rejected_qty = 0

    if template_name:
        _populate_readings_from_template(qci, template_name)

    try:
        qci.insert(ignore_permissions=True)
    except Exception as e:
        raise frappe.ValidationError(
            _("Could not save QC Inspection: {0}").format(str(e))
        )

    return qci.name


def _resolve_template(item_code: str, inspection_type: str) -> str | None:
    """
    Template resolution priority (high -> low):
    1. Item.default_qc_inspection_template (explicit item-level override)
    2. Template where item = item_code + inspection_type matches
    3. Template where dosage_form matches item's dosage_form
    4. Template where item_group matches + inspection_type matches
    5. Generic template (no item/dosage/group, inspection_type = All)

    Within levels 2-4, an exact inspection_type match always outranks an
    "All"/blank inspection_type template for the same item/dosage/group —
    this is enforced with two explicit queries rather than an
    order_by="inspection_type desc" sort, which only happened to work
    because "All" and "" both sort alphabetically before every current
    inspection_type value ("Incoming", "In Process", "Outgoing") and would
    silently break if a new type were ever added starting with a letter
    at or before "A".
    """
    # Level 1: explicit item-level template
    try:
        tmpl = frappe.db.get_value("Item", item_code, "default_qc_inspection_template")
        if tmpl:
            return tmpl
    except Exception:
        pass

    # Level 2: item-code specific template — exact inspection_type first,
    # then "All"/blank for the same item.
    try:
        tmpl = frappe.db.get_value(
            "QC Inspection Template", {"item": item_code, "inspection_type": inspection_type}, "name",
        )
        if not tmpl:
            tmpl = frappe.db.get_value(
                "QC Inspection Template",
                {"item": item_code, "inspection_type": ["in", ["All", ""]]},
                "name",
            )
        if tmpl:
            return tmpl
    except Exception:
        pass

    # Level 3: dosage_form match (Ayurvedic) — exact inspection_type first,
    # then "All"/blank for the same dosage_form.
    dosage_form = None
    try:
        dosage_form = frappe.db.get_value("Item", item_code, "dosage_form")
    except Exception:
        pass

    if dosage_form:
        try:
            tmpl = frappe.db.get_value(
                "QC Inspection Template",
                {"dosage_form": dosage_form, "inspection_type": inspection_type},
                "name",
            )
            if not tmpl:
                tmpl = frappe.db.get_value(
                    "QC Inspection Template",
                    {"dosage_form": dosage_form, "inspection_type": ["in", ["All", ""]]},
                    "name",
                )
            if tmpl:
                return tmpl
        except Exception:
            pass

    # Level 4: item_group match — exact inspection_type first, then
    # "All"/blank for the same item_group.
    item_group = frappe.db.get_value("Item", item_code, "item_group")
    if item_group:
        try:
            tmpl = frappe.db.get_value(
                "QC Inspection Template",
                {"item_group": item_group, "inspection_type": inspection_type},
                "name",
            )
            if not tmpl:
                tmpl = frappe.db.get_value(
                    "QC Inspection Template",
                    {"item_group": item_group, "inspection_type": ["in", ["All", ""]]},
                    "name",
                )
            if tmpl:
                return tmpl
        except Exception:
            pass

    # Level 5: generic fallback — must also exclude templates scoped to a
    # dosage_form or item_group. Without this, a dosage/group-specific
    # template with no `item` set could be mistakenly picked up here as
    # the generic fallback instead of only being matched at Level 3/4.
    try:
        tmpl = frappe.db.get_value(
            "QC Inspection Template",
            {
                "item": ["in", ["", None]],
                "dosage_form": ["in", ["", None]],
                "item_group": ["in", ["", None]],
                "inspection_type": ["in", [inspection_type, "All"]],
            },
            "name",
        )
        return tmpl
    except Exception:
        return None


def _populate_readings_from_template(qci, template_name: str):
    """Copy template parameters into QC Inspection Reading rows."""
    tmpl = frappe.get_doc("QC Inspection Template", template_name)
    for param in (tmpl.parameters or []):
        qci.append("readings", {
            "template_parameter":        param.parameter,
            "parameter_type":            param.parameter_type,
            "min_value":                 param.get("min_value"),
            "max_value":                 param.get("max_value"),
            "acceptance_criteria_value": param.get("acceptance_criteria_value"),
            "formula":                   param.get("formula"),
            "reading_value":             "",
            "status":                    "Pending",
        })


# --- Helpers -----------------------------------------------------------------

def _qc_master_switch_on() -> bool:
    """Read qc_warn_on_missing_inspection from Books Settings. Default True."""
    try:
        val = frappe.db.get_single_value("Books Settings", "qc_warn_on_missing_inspection")
        if val is None:
            return True
        return bool(int(val))
    except Exception:
        return True


def _qc_hard_block_on(company: str | None = None) -> bool:
    """
    Read qc_hard_block from Books Company for the given company. Books
    Settings is a single global doctype and is NOT company-enforced -- this
    must never be read from there in a multi-tenant app -- a hard-block flag
    set by one company would silently block submissions for every other
    company too.

    Phase 4: default is now True (hard-block ON) once a company is known and
    the field is unset -- previously this defaulted to False (soft-warn),
    matching the field's old default of "0" on Books Company. The field's
    own JSON default is now "1" for newly created companies; the per-field
    None-fallback below covers existing companies/sites where the column
    exists but happens to hold NULL (pre-migration edge case) rather than an
    explicit 0 or 1. If doc.company itself is blank (should not normally
    happen), there is no company-scoped setting to check at all -- this
    stays conservative and returns False rather than hard-blocking something
    we can't attribute to any company's configuration.
    """
    if not company:
        return False
    try:
        val = frappe.db.get_value("Books Company", company, "qc_hard_block")
        if val is None:
            return True
        return bool(int(val))
    except Exception:
        return True


def _log_qc_override(doc, summary: dict):
    """Write an audit record when a user overrides a QC warning."""
    try:
        failed  = summary.get("failed_items", [])
        missing = summary.get("missing_items", [])
        pending = summary.get("pending_items", [])
        content = (
            f"QC Override by {frappe.session.user} on {doc.doctype} {doc.name}. "
            f"Status was: {summary.get('overall_status')}. "
            f"Failed items: {failed}. Missing items: {missing}. Pending items: {pending}."
        )
        frappe.get_doc({
            "doctype":           "Activity Log",
            "subject":           f"QC Override on {doc.doctype} {doc.name}",
            "user":              frappe.session.user,
            "status":            "Success",
            "reference_doctype": doc.doctype,
            "reference_name":    doc.name,
            "content":           content,
        }).insert(ignore_permissions=True)
        # No manual commit here (previously present): this hook runs
        # partway through the submit of `doc` (a Purchase Receipt /
        # Delivery Note / etc.), inside the same DB transaction. A manual
        # commit at this point would irrevocably commit that document's
        # docstatus=1 submission early, before the rest of the submit
        # hook chain finishes -- if a later hook in the same chain then
        # threw, the request would report failure while the document was
        # already durably submitted underneath it. Frappe commits the
        # whole request as one atomic unit on success (or rolls it all
        # back together on an unhandled exception); this audit log entry
        # rides along with that same guarantee rather than jumping ahead
        # of it.
    except Exception:
        pass