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

Public surface
--------------
check_qc_before_stock_link(doc, method=None)              -- on_submit hook (QC gate)
auto_create_qc_for_purchase_receipt(doc, method=None)     -- before_submit hook (PR)
auto_create_qc_for_stock_entry(doc, method=None)          -- before_submit hook (SE Manufacture)
auto_create_qc_for_delivery_note(doc, method=None)        -- before_submit hook (DN)
auto_create_qc_for_sales_invoice(doc, method=None)        -- before_submit hook (SI)
doc_requires_qc(doc) -> bool
get_linked_qc_status(doc) -> str
create_qc_inspection_for_item(reference_type, reference_name, item_code, inspection_type) -> str
get_qc_summary_for_doc(reference_type, reference_name) -> dict
"""

import frappe
from frappe import _
from frappe.utils import nowdate


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
    if _qc_hard_block_on():
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

        # Skip if QC Inspection already exists (non-cancelled)
        existing = frappe.db.get_value(
            "QC Inspection",
            {
                "reference_type": doc.doctype,
                "reference_name": doc.name,
                "item": item_code,
                "docstatus": ["!=", 2],
            },
            "name",
        )
        if existing:
            continue

        try:
            qci_name = create_qc_inspection_for_item(
                doc.doctype, doc.name, item_code, inspection_type
            )
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


# --- Point 2: Auto-create QC for Purchase Receipt ----------------------------

def auto_create_qc_for_purchase_receipt(doc, method=None):
    """
    before_submit hook on Purchase Receipt.
    For every item with inspection_required_before_purchase=1,
    automatically creates a draft QC Inspection (if not already existing).
    Inspector receives a blue notification with the inspection name(s).
    """
    _auto_create_qc_for_rows(
        doc,
        flag_field="inspection_required_before_purchase",
        inspection_type="Incoming",
        success_message=_("QC Inspection(s) auto-created for {0} item(s): {1}. "
                           "Please complete readings before stock is accepted."),
        success_title=_("QC Inspections Created"),
    )


# --- Point 3: Auto-create QC for Finished Goods (Stock Entry Manufacture) ----

def auto_create_qc_for_stock_entry(doc, method=None):
    """
    before_submit hook on Stock Entry.
    For Manufacture type only: creates draft QC Inspection for finished goods
    (items going INTO stock — t_warehouse set — with inspection_required_before_manufacture=1).
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

    _auto_create_qc_for_rows(
        doc,
        flag_field="inspection_required_before_manufacture",
        inspection_type="In Process",
        success_message=_("Finished Goods QC Inspection(s) auto-created: {1}. "
                           "Please complete readings for the manufactured batch."),
        success_title=_("Finished Goods QC Created"),
        # Only finished goods rows (items being produced into t_warehouse)
        row_filter=lambda row: bool(getattr(row, "t_warehouse", None)),
        on_created=_stamp_work_order,
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

    inspected_items = {qi["item"]: qi for qi in inspections}

    doc = frappe.get_doc(reference_type, reference_name)
    flag_field = _ITEM_FLAG_FOR_INSPECTION_TYPE.get(inspection_type, "")
    items_needing_qc = []
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
            items_needing_qc.append(item_code)

    if not items_needing_qc:
        return {"overall_status": "Pass", "inspections": inspections,
                "passed_items": [], "failed_items": [], "pending_items": [],
                "missing_items": [], "total_items_requiring_qc": 0}

    passed  = []
    failed  = []
    pending = []
    missing = []

    for item_code in items_needing_qc:
        qi = inspected_items.get(item_code)
        if not qi:
            missing.append(item_code)
        elif qi["status"] == "Pass":
            passed.append(item_code)
        elif qi["status"] == "Fail":
            failed.append(item_code)
        else:
            pending.append(item_code)

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
        "total_items_requiring_qc": len(items_needing_qc),
    }


# --- create_qc_inspection_for_item -------------------------------------------

def create_qc_inspection_for_item(
    reference_type: str,
    reference_name: str,
    item_code: str,
    inspection_type: str | None = None,
) -> str:
    """
    Create a draft QC Inspection for a specific item on a reference document.
    Copies parameters from the resolved template (if any).
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
    qci.inspection_date        = nowdate()
    qci.inspected_by           = frappe.session.user
    qci.qc_inspection_template = template_name
    qci.status                 = "Pending"

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


def _qc_hard_block_on() -> bool:
    """Read qc_hard_block from Books Settings. Default False (soft-warn mode)."""
    try:
        val = frappe.db.get_single_value("Books Settings", "qc_hard_block")
        if val is None:
            return False
        return bool(int(val))
    except Exception:
        return False


def _log_qc_override(doc, summary: dict):
    """Write a permanent audit record when a user overrides a QC warning."""
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
            "user":              frappe.session.user,
            "operation":         "Submit",
            "status":            "Success",
            "reference_doctype": doc.doctype,
            "reference_name":    doc.name,
            "content":           content,
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        pass