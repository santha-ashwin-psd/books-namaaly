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
get_or_create_coverage(doc, row, item_code, inspection_type, create_if_missing) -> dict
    -- single source of truth for row-level QC coverage; see QC Coverage doctype
reconcile_row_identity(doc, method=None)           -- before_save hook (all 5 QC-gated doctypes)
"""

from collections import defaultdict

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

    if doc.doctype == "Stock Entry":
        # This gate can never pass for a Stock Entry. doc_requires_qc already
        # narrows Stock Entry to Manufacture-type rows with t_warehouse set
        # (i.e. exactly the finished-goods/scrap receipt rows) -- and THIS
        # SAME submission's own before_submit hook, auto_create_qc_for_stock_entry,
        # is what creates the QC Inspection(s) for those rows, moments before
        # this on_submit hook runs. The finished good/scrap physically didn't
        # exist to inspect until this submission produced it, so its freshly
        # -created QC Inspection can never already be Pass by the time this
        # check runs -- in hard-block mode this frappe.throw()s on every
        # single Manufacture completion of a QC-required item, unconditionally,
        # with no way to ever satisfy it (the WO's own bookkeeping -- consumed_qty
        # /produced_qty/status -- never even runs, since the throw happens
        # inside se.submit() before complete_work_order reaches any of it).
        # In soft-warn mode it's equally pointless: it would msgprint-warn
        # every time too, for something not actually wrong.
        #
        # FG/scrap usability is already correctly gated downstream instead:
        # _stamp_and_route_fg_quarantine / _stamp_and_route_scrap_quarantine
        # (both called from THIS SAME before_submit hook) route the stock into
        # a quarantine warehouse it can't be consumed or shipped from until its
        # QC Inspection actually passes and qc_hold_manager releases it. That
        # already does this gate's job correctly for Stock Entry, so this gate
        # is a no-op here by design.
        return

    if not doc_requires_qc(doc):
        return

    summary = get_qc_summary_for_doc(doc.doctype, doc.name)
    status  = summary.get("overall_status", "Missing")

    if status == "Pass":
        return

    failed_items  = summary.get("failed_items", [])
    missing_items = summary.get("missing_items", [])
    pending_items = summary.get("pending_items", [])
    # Include pending_items too -- previously only failed/missing fed into
    # the message, so the "still Pending" branch below always rendered an
    # empty item list (all_problems + item_list would be blank whenever
    # status == "Pending" specifically, since pending rows never fell into
    # either of the other two buckets).
    all_problems  = failed_items + missing_items + pending_items
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
    created = []
    failed  = []
    for row in (getattr(doc, "items", []) or []):
        item_code = getattr(row, "item_code", None) or getattr(row, "item", None)
        if not item_code:
            continue
        if row_filter and not row_filter(row):
            continue
        if not frappe.db.get_value("Item", item_code, flag_field):
            continue

        # All coverage lookup/creation/race-handling now lives in one place
        # -- see get_or_create_coverage(). This used to be ~90 lines here
        # re-deriving "does this row have coverage" via the row's own link,
        # a dangling-link check, and a SELECT...FOR UPDATE by item+batch --
        # a second, independent implementation of the exact same question
        # get_qc_summary_for_doc also answers on its own. Two
        # implementations drifting out of sync is what let duplicate/
        # dangling QC Inspections reappear in different shapes.
        try:
            result = get_or_create_coverage(
                doc, row, item_code, inspection_type,
                create_if_missing=True,
                batch_no=getattr(row, "batch_no", None),
                inspected_qty=getattr(row, "qty", None) or getattr(row, "received_qty", None),
            )
        except Exception:
            frappe.log_error(
                title=f"QC auto-create failed for {item_code} on {doc.name}",
                message=frappe.get_traceback(),
            )
            failed.append(item_code)
            continue

        if result.get("created") and result.get("qci"):
            if on_created:
                on_created(result["qci"], row)
            created.append(result["qci"])

            # CRITICAL: commit now, not after the whole before_submit hook
            # chain / on_submit gate finishes. This runs before the parent
            # doc's own docstatus flip, so this commit only durably saves
            # the new QC Inspection + QC Coverage row -- it does NOT
            # prematurely submit `doc` itself.
            #
            # Without this: if the on_submit gate (check_qc_before_stock_
            # link, running later in the SAME request) then hard-blocks via
            # frappe.throw(), Frappe rolls back the ENTIRE transaction --
            # including the QC Inspection and QC Coverage rows just created
            # here, since they were never committed. The name Frappe
            # assigned it (e.g. "QCI-2026-00006") survives, because the
            # naming-series counter is bumped outside the document
            # transaction specifically so two parallel inserts never
            # collide on a name -- but the row itself vanishes. The user
            # sees an error message pointing at a QC Inspection that does
            # not exist anywhere, can never open it to complete it, and
            # every retry burns another series number the same way,
            # forever. Committing here is what makes the auto-created
            # inspection an actual, durable, completable work item instead
            # of a phantom reference in an error message.
            frappe.db.commit()

    if failed:
        # Previously this failure was only written to the Error Log and
        # never shown to the user -- the on_submit gate would then report
        # a plain "No QC Inspection found" with no indication that
        # auto-create had actually been attempted and failed. Surfacing it
        # here (still non-blocking; the submit-time gate below is what
        # actually stops submission) means a failed creation is visible at
        # the moment it happens, not just discoverable after the fact by
        # someone with Error Log access.
        frappe.msgprint(
            _("QC Inspection auto-creation failed for item(s): {0}. "
              "Check the Error Log for details, or create the QC Inspection "
              "manually before submitting.").format(", ".join(failed)),
            indicator="red",
            title=_("QC Auto-Create Failed"),
        )

    if created:
        frappe.msgprint(
            success_message.format(len(created), ", ".join(created)),
            indicator="blue",
            title=success_title,
            alert=True,
        )

    return created


# --- Unified coverage resolver (single source of truth) ---------------------

def get_or_create_coverage(
    doc,
    row,
    item_code: str,
    inspection_type: str,
    create_if_missing: bool = False,
    batch_no: str | None = None,
    inspected_qty: float | None = None,
) -> dict:
    """
    THE single function that answers "does this row already have QC
    coverage." Every caller -- the auto-create hooks (create_if_missing=
    True) and the read-only gate/summary (create_if_missing=False) -- goes
    through this instead of independently re-deriving coverage via
    item+batch matching. See QC_Flow_Redesign §5.

    Coverage is keyed on `source_row = f"{row.doctype}:{row.name}"`, stored
    in the `QC Coverage` doctype where source_row has a genuine DB unique
    index -- that index, not any lock, is what makes this safe under
    concurrency: two near-simultaneous submits for the same row can both
    reach the "create" branch below having both seen no coverage yet, but
    only one of their `QC Coverage` inserts can succeed. The loser catches
    the duplicate-key failure and re-reads the winner's row instead of
    ending up with two QC Inspections covering the same source_row.

    Returns {"qci": <name or None>, "status": "Pass"|"Fail"|"Pending"|"Missing",
             "created": bool}
    """
    row_name = getattr(row, "name", None)
    if not row_name:
        # No stable row identity to key coverage on (row hasn't actually
        # been saved yet). Fail safe to "no coverage" rather than guessing
        # via item/batch -- this should not normally happen, since every
        # call site here runs in before_submit/on_submit, after the parent
        # doc (and therefore its child rows) has already been saved once.
        return {"qci": None, "status": "Missing", "created": False}

    source_row = f"{row.doctype}:{row_name}"

    coverage_qci = frappe.db.get_value("QC Coverage", {"source_row": source_row}, "qc_inspection")

    if coverage_qci:
        qci_info = frappe.db.get_value(
            "QC Inspection", coverage_qci, ["docstatus", "status"], as_dict=True
        )
        if qci_info is None:
            # The QC Inspection this coverage row points at was deleted out
            # from under it (e.g. someone removed a bad/duplicate inspection
            # directly). A stale coverage row must not keep blocking a
            # legitimate re-inspection -- drop it and fall through exactly
            # as if this row had never had coverage.
            frappe.db.delete("QC Coverage", {"source_row": source_row})
            coverage_qci = None
        elif qci_info.docstatus == 2:
            # Cancelled QCI -- also not live coverage. Same cleanup.
            frappe.db.delete("QC Coverage", {"source_row": source_row})
            coverage_qci = None
        else:
            _stamp_row_link(row, coverage_qci)
            status = "Pending" if qci_info.docstatus == 0 else (qci_info.status or "Pending")
            return {"qci": coverage_qci, "status": status, "created": False}

    if not create_if_missing:
        return {"qci": None, "status": "Missing", "created": False}

    # Safeguard: refuse to silently spawn ANOTHER QCI for this item on this
    # reference doc if one is already sitting there unresolved (draft/
    # Pending). This is the exact failure mode that produced QCI-2026-00006/
    # 00007/00008 for one logical Bill line: each save minted a new
    # source_row (child row identity was unstable -- see save_doc fix), so
    # this function never found existing coverage and kept creating more.
    # That root cause is now fixed at the source, but this stays as
    # defense-in-depth for any other path that can re-trigger the pattern.
    # Fails LOUD (logs + msgprint) rather than silently creating a second
    # inspection an operator would have to notice and clean up by hand.
    existing_unresolved = frappe.get_all(
        "QC Inspection",
        filters={
            "reference_type": doc.doctype,
            "reference_name": doc.name,
            "item": item_code,
            "docstatus": ["<", 2],
            "status": ["in", ["Pending", ""]],
        },
        pluck="name",
    )
    if existing_unresolved:
        frappe.log_error(
            title=f"QC auto-create blocked: unresolved QCI series for {item_code} on {doc.doctype} {doc.name}",
            message=(
                f"Refused to create another QC Inspection for item {item_code} "
                f"on {doc.doctype} {doc.name} -- unresolved inspection(s) already "
                f"exist: {existing_unresolved}. This usually means the row's "
                f"identity is not stable across saves (source_row is being "
                f"regenerated), so get_or_create_coverage keeps missing the "
                f"existing coverage. Investigate row identity before creating "
                f"more inspections; do not just re-run submit."
            ),
        )
        frappe.msgprint(
            _(
                "Item {0} already has an unresolved QC Inspection ({1}) on this "
                "document. Not creating another -- please complete or cancel it "
                "first, or contact an admin if this keeps recurring."
            ).format(item_code, ", ".join(existing_unresolved)),
            indicator="red",
            title=_("QC Auto-Create Blocked"),
        )
        return {"qci": existing_unresolved[0], "status": "Pending", "created": False}

    qci_name = create_qc_inspection_for_item(
        doc.doctype, doc.name, item_code, inspection_type,
        batch_no=batch_no, inspected_qty=inspected_qty,
    )

    try:
        coverage = frappe.new_doc("QC Coverage")
        coverage.source_row    = source_row
        coverage.qc_inspection = qci_name
        coverage.insert(ignore_permissions=True)
    except Exception as e:
        # Duplicate-key = someone else's insert won the race between our
        # lookup above and our insert here. Anything else is a real error
        # and should propagate (caller logs it and treats the row as
        # failed, same as before).
        if not _is_duplicate_key_error(e):
            raise
        # Discard the QCI we just created -- it's an orphan, nothing points
        # at it -- and use the winner's instead. Deliberately NOT a
        # frappe.db.rollback(): this hook runs partway through submitting
        # `doc` inside a larger transaction, and rolling back here would
        # discard everything else that transaction has done so far. Only
        # the orphan draft we made is removed; it's safe to hard-delete
        # since nothing else can reference a draft that's milliseconds old.
        frappe.delete_doc("QC Inspection", qci_name, ignore_permissions=True,
                           force=True, delete_permanently=True)
        winner_qci = frappe.db.get_value("QC Coverage", {"source_row": source_row}, "qc_inspection")
        if not winner_qci:
            # Extremely unlikely (the winner's own insert would have to
            # have been rolled back between our failed insert and this
            # re-read) -- surface as Missing rather than raise, so this
            # row's submit gets one more chance next attempt instead of
            # hard-failing the whole document.
            return {"qci": None, "status": "Missing", "created": False}
        qci_info = frappe.db.get_value("QC Inspection", winner_qci, ["docstatus", "status"], as_dict=True)
        _stamp_row_link(row, winner_qci)
        status = "Pending" if (qci_info and qci_info.docstatus == 0) else ((qci_info and qci_info.status) or "Pending")
        return {"qci": winner_qci, "status": status, "created": False}

    _stamp_row_link(row, qci_name)
    return {"qci": qci_name, "status": "Pending", "created": True}


def _is_duplicate_key_error(exc: Exception) -> bool:
    """Best-effort detection of a DB duplicate-key/unique-constraint failure,
    across Frappe's own UniqueValidationError and the raw DB driver error."""
    name = exc.__class__.__name__
    if "UniqueValidationError" in name or "DuplicateEntryError" in name:
        return True
    msg = str(exc).lower()
    return "duplicate" in msg or "unique" in msg


def _stamp_row_link(row, qci_name: str):
    """
    Mirror the resolved QC Inspection onto the row's own `quality_inspection`
    field (in-memory and in the DB) purely for UI/display convenience --
    `QC Coverage.source_row` remains the actual source of truth, this field
    is not read back by get_or_create_coverage.
    """
    if not (getattr(row, "doctype", None) and getattr(row, "name", None)):
        return
    if not frappe.db.has_column(row.doctype, "quality_inspection"):
        return
    row.quality_inspection = qci_name
    frappe.db.set_value(row.doctype, row.name, "quality_inspection", qci_name,
                         update_modified=False)


# --- Backend defense-in-depth: row reconciliation on save --------------------

def reconcile_row_identity(doc, method=None):
    """
    before_save hook (every save, draft or submit) on every QC-gated
    doctype. See QC_Flow_Redesign §4.

    The backend never trusts the frontend to forward a child row's `name`.
    If a page ever rebuilds `items[]` from local state without forwarding
    `name` (the exact Bills.vue bug, as a *pattern* rather than a one-off),
    Frappe would treat every row as brand new on save -- silently losing
    the link between the row and any QC coverage it already had.

    For every incoming row that looks new (no `name` yet) but matches
    exactly one row in the previous saved version on
    (item_code, batch_no, qty, rate), recover that previous row's identity
    (name + quality_inspection) before Frappe's own save machinery runs.
    Ambiguous matches (zero or multiple candidates) are left alone --
    fails safe to "new row, no assumed coverage" rather than guessing wrong
    and attaching someone else's inspection.
    """
    if doc.is_new():
        return

    try:
        previous = doc.get_doc_before_save()
    except Exception:
        previous = None
    if not previous:
        return

    prev_items = getattr(previous, "items", []) or []
    if not prev_items:
        return

    prev_buckets = defaultdict(list)
    for prow in prev_items:
        key = _row_identity_key(prow)
        if key:
            prev_buckets[key].append(prow)

    for row in (getattr(doc, "items", []) or []):
        if getattr(row, "name", None):
            continue  # Frappe already has an identity for this row
        key = _row_identity_key(row)
        if not key:
            continue
        candidates = prev_buckets.get(key) or []
        if len(candidates) != 1:
            continue
        match = candidates[0]
        row.name = match.name
        if hasattr(row, "quality_inspection"):
            row.quality_inspection = getattr(match, "quality_inspection", None)
        # Consumed -- a second incoming row must not also claim this same
        # previous row.
        prev_buckets[key] = []


def _row_identity_key(row):
    item_code = getattr(row, "item_code", None) or getattr(row, "item", None)
    if not item_code:
        return None
    return (
        item_code,
        getattr(row, "batch_no", None),
        flt(getattr(row, "qty", None)),
        flt(getattr(row, "rate", None)),
    )


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


def _resolve_rm_quarantine_warehouse(company: str | None) -> str | None:
    """Scrap Reuse feature, Phase 8 -- resolve the RM quarantine warehouse
    for a company. Recovered scrap becomes a RAW MATERIAL again the moment
    it's reused (see work_order_engine.apply_partial_scrap_substitution),
    so it belongs in the RM quarantine, not FG's -- mirrors
    _resolve_fg_quarantine_warehouse's fallback shape but doesn't fall back
    to the FG warehouse, since scrap awaiting QC has no business sitting
    alongside finished-goods holds.
    """
    if not company:
        return None
    return frappe.db.get_value("Books Company", company, "default_quarantine_warehouse")


def _stamp_and_route_quarantine(doc, row, qci_name, quarantine_wh):
    """Shared body behind _stamp_and_route_fg_quarantine and the Phase 8
    scrap-row routing below -- both mutate THIS row's own t_warehouse
    in-memory before_submit (Stock Entry is the physical movement itself,
    unlike Purchase Receipt/Invoice's stock_link.py proxy) and stamp the
    same QC Inspection bookkeeping (target_warehouse / release_status /
    quarantine_warehouse) so qc_hold_manager's existing release-on-pass
    flow (_release_quarantine_on_pass) works identically for either kind
    of row with no changes needed there.
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

        if not quarantine_wh:
            return  # nothing configured -- row stays exactly where it was

        row.t_warehouse = quarantine_wh

        update = {}
        if frappe.db.has_column("QC Inspection", "release_status"):
            update["release_status"] = "Not Released"
        if frappe.db.has_column("QC Inspection", "quarantine_warehouse"):
            update["quarantine_warehouse"] = quarantine_wh
        if update:
            frappe.db.set_value("QC Inspection", qci_name, update, update_modified=False)
    except Exception:
        frappe.log_error(
            title=f"Quarantine routing failed for {qci_name}",
            message=frappe.get_traceback(),
        )


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
    _stamp_and_route_quarantine(
        doc, row, qci_name, _resolve_fg_quarantine_warehouse(getattr(doc, "company", None))
    )


def _stamp_and_route_scrap_quarantine(doc, row, qci_name):
    """Scrap Reuse feature, Phase 8 -- on_created callback for recoverable
    scrap/by-product rows whose Item has inspection_required_before_manufacture
    set. Same mechanics as _stamp_and_route_fg_quarantine, routed to the RM
    quarantine warehouse instead of FG's (see _resolve_rm_quarantine_warehouse).

    This closes the gap that let a QC-flagged scrap item go straight from
    "recovered on this Work Order" to "reused as a raw material on another
    Work Order" (apply_partial_scrap_substitution) with no inspection ever
    happening in between -- auto_create_qc_for_stock_entry previously
    excluded every scrap/by-product row from QC entirely (see the
    docstring on that function), which was correct for NOT spuriously
    QC'ing every scrap row, but also meant a row that genuinely SHOULD be
    inspected never was. Once routed here, work_order_engine.
    _resolve_scrap_warehouse refuses to pick this warehouse as a scrap
    source until qc_hold_manager's pass flow releases it back out.
    """
    _stamp_and_route_quarantine(
        doc, row, qci_name, _resolve_rm_quarantine_warehouse(getattr(doc, "company", None))
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

    Phase 8: a second, separate pass does the same for recoverable
    scrap/by-product rows (is_scrap_item=1) whose OWN Item has
    inspection_required_before_manufacture set, routing them into RM
    quarantine instead -- see _stamp_and_route_scrap_quarantine.
    """
    if getattr(doc, "stock_entry_type", "") != "Manufacture":
        return

    # Resolve the actual production item so the row filter below can tell
    # the finished-goods receipt row apart from scrap/by-product rows --
    # both carry t_warehouse (scrap is received into scrap_warehouse too),
    # so filtering on "has a t_warehouse" alone let a scrap item's own
    # inspection_required_before_manufacture flag spuriously create a
    # "Finished Goods QC" inspection for the scrap item, and — via
    # _stamp_and_route_fg_quarantine below — reroute real recoverable scrap
    # stock into the FG quarantine warehouse instead of scrap_warehouse.
    production_item = None
    if getattr(doc, "work_order", None):
        production_item = frappe.db.get_value("Work Order", doc.work_order, "production_item")

    def _is_fg_row(row):
        if not getattr(row, "t_warehouse", None):
            return False
        if production_item:
            return row.item_code == production_item
        return True  # no Work Order linked -- fall back to the old behaviour

    def _is_scrap_row_for_qc(row):
        # Recoverable scrap/by-product rows only -- see complete_work_order,
        # which stamps is_scrap_item=1 on exactly these rows (as opposed to
        # the FG receipt row, or a plain raw-material consumption row which
        # has no t_warehouse at all). Deliberately does NOT also require
        # is_scrap_row on the Work Order Item side -- that flag lives on the
        # SOURCE row a scrap-split raw material was drawn from, not on this
        # Stock Entry's incoming scrap receipt row, which is an unrelated
        # concept that happens to share a similar name.
        return bool(getattr(row, "t_warehouse", None)) and bool(getattr(row, "is_scrap_item", None))

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
        # Only the finished-goods receipt row(s) -- see _is_fg_row above.
        row_filter=_is_fg_row,
        on_created=_on_created,
    )

    # Scrap Reuse feature, Phase 8 -- QC-required scrap items via
    # qc_hold_manager. Recoverable scrap/by-product rows were previously
    # EXCLUDED from QC entirely by design (see the comment above on
    # production_item/_is_fg_row) -- correct for not spuriously QC'ing every
    # scrap row using the FG item's own flag, but it also meant a scrap
    # item that genuinely has inspection_required_before_manufacture=1 on
    # its own Item master was never inspected before being available for
    # apply_partial_scrap_substitution to pull back into another Work
    # Order's raw materials. This is a second, separate
    # _auto_create_qc_for_rows pass scoped to exactly those rows, routed
    # into RM quarantine (see _stamp_and_route_scrap_quarantine) instead of
    # scrap_warehouse -- work_order_engine._resolve_scrap_warehouse then
    # refuses to source scrap reuse from a quarantine warehouse, so
    # quarantined scrap can't be reused until it passes.
    def _on_scrap_created(qci_name, row):
        _stamp_work_order(qci_name, row)
        _stamp_and_route_scrap_quarantine(doc, row, qci_name)

    _auto_create_qc_for_rows(
        doc,
        flag_field="inspection_required_before_manufacture",
        inspection_type="In Process",
        success_message=_("Scrap/By-Product QC Inspection(s) auto-created: {1}. "
                           "This scrap is held in quarantine until inspection passes."),
        success_title=_("Scrap QC Created"),
        row_filter=_is_scrap_row_for_qc,
        on_created=_on_scrap_created,
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

    Row-scoped, not item-scoped: coverage for every row is resolved through
    get_or_create_coverage() (create_if_missing=False, read-only -- this
    function must never mutate state, only observe it), which is keyed on
    QC Coverage.source_row -- a genuine DB-unique key per (child_doctype,
    child_row_name). The legacy item-code fallback matching that used to
    live here (falling back to "first inspection found for this item" when
    a row's own link was blank) has been removed entirely: it's what let
    two different rows' statuses bleed into each other, and source_row is
    now authoritative so it's no longer needed.
    """
    inspection_type = _DOCTYPE_TO_INSPECTION_TYPE.get(reference_type)

    # Still returned for display/reporting purposes (e.g. listing every
    # inspection tied to this doc), just no longer used to resolve
    # per-row status below.
    inspections = frappe.get_all(
        "QC Inspection",
        filters={
            "reference_type": reference_type,
            "reference_name": reference_name,
            "docstatus": ["in", [0, 1]],
        },
        fields=["name", "item", "status", "inspection_type", "inspection_date",
                "inspected_by", "docstatus"],
        ignore_permissions=True,
    )

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

        result = get_or_create_coverage(
            doc, row, item_code, inspection_type, create_if_missing=False,
        )
        status   = result["status"]
        qci_name = result["qci"]

        if status == "Missing" or not qci_name:
            missing.append(label)
        elif status == "Pending":
            # Include the QC Inspection's own name so the message points
            # the user at exactly which draft to go finish, rather than
            # just repeating the item label with nothing to act on.
            pending.append(f"{label} [{qci_name}]")
        elif status == "Pass":
            passed.append(label)
        elif status == "Fail":
            failed.append(label)
        else:
            pending.append(f"{label} [{qci_name}]")

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