from __future__ import annotations
"""
Quality Control API — zoho_books_clone/api/qc.py
=================================================
Whitelisted REST endpoints consumed by the SPA's Quality module.

Endpoints:
  GET  get_qc_status(reference_type, reference_name)
  GET  get_qc_inspections_for_doc(reference_type, reference_name)
  GET  get_inspection_detail(inspection_name)
  GET  get_templates()
  GET  get_template_detail(template_name)
  GET  check_template_usage(template_name)   -- count of QC Inspections referencing a template
  POST update_template(template_name, ...)   -- atomic parent+parameters save
  POST create_qc_inspection(reference_type, reference_name, item_code, inspection_type)
  POST update_qc_inspection(inspection_name, ...)  -- edit a Draft inspection's header fields
  POST apply_qc_template(inspection_name, template_name=None) -- (re-)attach a template + rebuild readings for a Draft
  POST save_qc_readings(inspection_name, readings_json)
  POST submit_qc_inspection(inspection_name)
  POST cancel_qc_inspection(inspection_name)
  GET  get_items_requiring_qc(reference_type, reference_name)
  GET  list_inspections(filters_json)
  GET  get_qc_dashboard_stats(company)
  GET  generate_coa(inspection_name)         -- render Certificate of Analysis HTML
"""

import json
import frappe
from frappe import _
from frappe.utils import nowdate, flt

from zoho_books_clone.quality.qc_engine import (
    create_qc_inspection_for_item,
    get_qc_summary_for_doc,
    get_linked_qc_status,
    _DOCTYPE_TO_INSPECTION_TYPE,
    _ITEM_FLAG_FOR_INSPECTION_TYPE,
    _resolve_template,
    _populate_readings_from_template,
)


# ─── Status & summary ─────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_qc_status(reference_type: str, reference_name: str) -> dict:
    """Return the overall QC status for a document — used by the SPA badge/toolbar."""
    summary = get_qc_summary_for_doc(reference_type, reference_name)
    return {
        "reference_type":  reference_type,
        "reference_name":  reference_name,
        "overall_status":  summary["overall_status"],
        "passed_items":    summary["passed_items"],
        "failed_items":    summary["failed_items"],
        "pending_items":   summary["pending_items"],
        "missing_items":   summary["missing_items"],
        "total_requiring": summary["total_items_requiring_qc"],
        "inspections":     summary["inspections"],
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_qc_inspections_for_doc(reference_type: str, reference_name: str) -> list:
    """Return all QC Inspections (any docstatus) linked to a document."""
    return frappe.get_all(
        "QC Inspection",
        filters={"reference_type": reference_type, "reference_name": reference_name},
        fields=[
            "name", "item", "item_name", "inspection_type", "status",
            "inspection_date", "inspected_by", "verified_by",
            "total_readings", "accepted_readings", "rejected_readings",
            "docstatus", "remarks",
        ],
        ignore_permissions=True,
        order_by="creation desc",
    )


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_inspection_detail(inspection_name: str) -> dict:
    """Return full QC Inspection document including readings."""
    doc = frappe.get_doc("QC Inspection", inspection_name)
    d = doc.as_dict()
    return d


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_items_requiring_qc(reference_type: str, reference_name: str) -> list:
    """
    Return a list of items on the document that have inspection_required_* set.
    Used by the SPA to show 'Create QC' button only for eligible items.
    """
    inspection_type = _DOCTYPE_TO_INSPECTION_TYPE.get(reference_type, "Incoming")
    flag_field = _ITEM_FLAG_FOR_INSPECTION_TYPE.get(inspection_type, "")
    if not flag_field:
        return []

    try:
        doc = frappe.get_doc(reference_type, reference_name)
    except Exception:
        return []

    result = []
    for row in (getattr(doc, "items", []) or []):
        item_code = getattr(row, "item_code", None) or getattr(row, "item", None)
        if not item_code:
            continue
        if flag_field and frappe.db.get_value("Item", item_code, flag_field):
            # Check if a QCI already exists for this item+doc
            existing = frappe.db.get_value(
                "QC Inspection",
                {"reference_type": reference_type, "reference_name": reference_name,
                 "item": item_code, "docstatus": ["!=", 2]},
                ["name", "status", "docstatus"],
                as_dict=True,
            )
            result.append({
                "item_code":       item_code,
                "item_name":       frappe.db.get_value("Item", item_code, "item_name") or item_code,
                "qty":             getattr(row, "qty", 0),
                "has_inspection":  bool(existing),
                "inspection_name": (existing or {}).get("name"),
                "inspection_status": (existing or {}).get("status"),
                "inspection_docstatus": (existing or {}).get("docstatus"),
            })
    return result


# ─── Templates ────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_templates(inspection_type: str = None, item_code: str = None) -> list:
    """Return all QC Inspection Templates, optionally filtered."""
    filters = {}
    if inspection_type:
        filters["inspection_type"] = ["in", [inspection_type, "All", ""]]
    if item_code:
        filters["item"] = item_code
    templates = frappe.get_all(
        "QC Inspection Template",
        filters=filters,
        fields=["name", "template_name", "item", "item_group", "inspection_type", "description"],
        order_by="template_name asc",
        ignore_permissions=True,
    )
    # Attach parameter count for each template
    if templates:
        names = [t["name"] for t in templates]
        counts = frappe.db.sql(
            """
            SELECT parent, COUNT(*) AS cnt
            FROM `tabQC Inspection Template Parameter`
            WHERE parent IN %(names)s
            GROUP BY parent
            """,
            {"names": names},
            as_dict=True,
        )
        count_map = {row["parent"]: row["cnt"] for row in counts}
        for t in templates:
            t["parameter_count"] = count_map.get(t["name"], 0)
    return templates


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_template_detail(template_name: str) -> dict:
    """Return full template with parameters."""
    doc = frappe.get_doc("QC Inspection Template", template_name)
    return doc.as_dict()


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def check_template_usage(template_name: str) -> dict:
    """Return how many QC Inspections reference this template, so the UI can
    warn before (or block) deletion."""
    count = frappe.db.count(
        "QC Inspection", filters={"qc_inspection_template": template_name}
    )
    return {"template_name": template_name, "inspection_count": count}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def update_template(
    template_name: str,
    template_name_new: str = None,
    item: str = None,
    item_group: str = None,
    inspection_type: str = "All",
    description: str = None,
    parameters_json: str = "[]",
) -> dict:
    """
    Update a QC Inspection Template's parent fields and fully replace its
    parameter child table in a single atomic save.

    Loads the doc via frappe.get_doc() (rather than accepting a client-built
    doc dict for frappe.client.save) so `modified` always matches the DB row
    — a client-cached dict never carries a current `modified` value, which
    otherwise trips Frappe's TimestampMismatchError on every edit, not just
    genuinely stale ones.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    if not frappe.db.exists("QC Inspection Template", template_name):
        frappe.throw(_("QC Inspection Template {0} does not exist.").format(template_name))

    doc = frappe.get_doc("QC Inspection Template", template_name)

    new_name = (template_name_new or "").strip()
    if new_name:
        doc.template_name = new_name
    doc.item = (item or "").strip() or None
    doc.item_group = (item_group or "").strip() or None
    doc.inspection_type = inspection_type or "All"
    doc.description = (description or "").strip() or None

    try:
        parameters = json.loads(parameters_json) if isinstance(parameters_json, str) else (parameters_json or [])
    except Exception:
        frappe.throw(_("Invalid parameters payload."))

    doc.set("parameters", [])
    for p in parameters:
        ptype = p.get("parameter_type") or "Numeric"
        doc.append("parameters", {
            "parameter": p.get("parameter"),
            "parameter_type": ptype,
            "min_value": p.get("min_value") if ptype == "Numeric" else None,
            "max_value": p.get("max_value") if ptype == "Numeric" else None,
            "acceptance_criteria_value": p.get("acceptance_criteria_value") if ptype == "Non-Numeric" else None,
            "formula": p.get("formula") if ptype == "Formula" else None,
        })

    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return doc.as_dict()


# ─── Create / Edit / Submit ───────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def create_qc_inspection(
    reference_type: str,
    reference_name: str,
    item_code: str,
    inspection_type: str = None,
) -> dict:
    """
    Create a draft QC Inspection for a specific item on a reference doc.
    Returns the new inspection name + full document.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    # Validate that the reference document exists
    if not frappe.db.exists(reference_type, reference_name):
        frappe.throw(
            _("Reference document {0} {1} does not exist.").format(reference_type, reference_name)
        )

    # Validate that the item exists
    if not frappe.db.exists("Item", item_code):
        frappe.throw(_("Item {0} does not exist.").format(item_code))

    # Check if one already exists (non-cancelled)
    existing = frappe.db.get_value(
        "QC Inspection",
        {
            "reference_type": reference_type,
            "reference_name": reference_name,
            "item": item_code,
            "docstatus": ["!=", 2],
        },
        "name",
    )
    if existing:
        return {"inspection_name": existing, "created": False, "message": "Inspection already exists"}

    try:
        inspection_name = create_qc_inspection_for_item(
            reference_type, reference_name, item_code, inspection_type
        )
    except Exception as e:
        frappe.log_error(
            title="create_qc_inspection failed",
            message=frappe.get_traceback(),
        )
        frappe.throw(
            _("Failed to create QC Inspection: {0}").format(str(e))
        )

    doc = frappe.get_doc("QC Inspection", inspection_name)
    return {"inspection_name": inspection_name, "created": True, "doc": doc.as_dict()}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def update_qc_inspection(
    inspection_name: str,
    inspection_type: str = None,
    reference_type: str = None,
    reference_name: str = None,
    item_code: str = None,
    sample_size: float = 1,
    inspection_date: str = None,
    remarks: str = "",
) -> dict:
    """
    Update the header fields of a draft QC Inspection (Inspection Type,
    Reference Doc, Item, Sample Size, Inspection Date, Remarks). Readings are
    edited separately via save_qc_readings(). Only Draft (docstatus 0)
    inspections can be edited — a submitted document is immutable.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    if not frappe.db.exists("QC Inspection", inspection_name):
        frappe.throw(_("QC Inspection {0} does not exist.").format(inspection_name))

    doc = frappe.get_doc("QC Inspection", inspection_name)

    if doc.docstatus != 0:
        frappe.throw(_("Only draft QC Inspections can be edited."))

    if reference_type and reference_name:
        if not frappe.db.exists(reference_type, reference_name):
            frappe.throw(
                _("Reference document {0} {1} does not exist.").format(reference_type, reference_name)
            )
        doc.reference_type = reference_type
        doc.reference_name = reference_name

    if item_code:
        if not frappe.db.exists("Item", item_code):
            frappe.throw(_("Item {0} does not exist.").format(item_code))
        doc.item = item_code
        doc.item_name = frappe.db.get_value("Item", item_code, "item_name") or item_code

    if inspection_type:
        doc.inspection_type = inspection_type
    if inspection_date:
        doc.inspection_date = inspection_date
    doc.sample_size = flt(sample_size) or 1
    doc.remarks = remarks or None

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {"inspection_name": doc.name, "doc": doc.as_dict()}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def apply_qc_template(inspection_name: str, template_name: str = None) -> dict:
    """
    (Re-)attach a QC Inspection Template to a Draft QC Inspection and rebuild
    its Readings table from that template's parameters.

    Template resolution normally only runs once, at creation time (see
    create_qc_inspection_for_item / _resolve_template). If no matching
    template existed yet at that moment, the inspection is stuck permanently
    with an empty readings table -- editing header fields via
    update_qc_inspection() never re-resolves or re-populates it. This
    endpoint lets the user manually pick a template (or ask the system to
    re-resolve one automatically by omitting template_name) for an existing
    Draft inspection.

    Only Draft (docstatus 0) inspections can be modified, matching the same
    rule enforced for header edits and reading edits.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    if not frappe.db.exists("QC Inspection", inspection_name):
        frappe.throw(_("QC Inspection {0} does not exist.").format(inspection_name))

    doc = frappe.get_doc("QC Inspection", inspection_name)

    if doc.docstatus != 0:
        frappe.throw(_("Only draft QC Inspections can have their template changed."))

    template_name = (template_name or "").strip()
    if not template_name:
        template_name = _resolve_template(doc.item, doc.inspection_type)
        if not template_name:
            frappe.throw(
                _("No matching QC Inspection Template was found for this item/inspection type. Please select one manually.")
            )

    if not frappe.db.exists("QC Inspection Template", template_name):
        frappe.throw(_("QC Inspection Template {0} does not exist.").format(template_name))

    # Wipe any existing readings and rebuild from the (possibly new) template.
    # Previously entered reading values are intentionally discarded -- they
    # were captured against a different (or no) parameter set and can't be
    # meaningfully carried over to the new one.
    doc.set("readings", [])
    doc.qc_inspection_template = template_name
    _populate_readings_from_template(doc, template_name)

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {"inspection_name": doc.name, "doc": doc.as_dict()}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def save_qc_readings(inspection_name: str, readings_json: str) -> dict:
    """
    Save reading values for a draft QC Inspection.
    readings_json: JSON array of {idx, reading_value, remarks}
    Status is auto-computed by the controller's validate().
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    readings = json.loads(readings_json) if isinstance(readings_json, str) else readings_json
    doc = frappe.get_doc("QC Inspection", inspection_name)

    if doc.docstatus != 0:
        frappe.throw(_("Only draft QC Inspections can be edited."))

    # Update reading values by idx or order
    for upd in readings:
        idx = int(upd.get("idx", 0)) - 1
        if 0 <= idx < len(doc.readings):
            doc.readings[idx].reading_value = upd.get("reading_value", "")
            doc.readings[idx].remarks = upd.get("remarks", "")

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "inspection_name": inspection_name,
        "status":          doc.status,
        "accepted":        doc.accepted_readings,
        "rejected":        doc.rejected_readings,
        "total":           doc.total_readings,
        "readings":        [r.as_dict() for r in doc.readings],
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def submit_qc_inspection(inspection_name: str) -> dict:
    """Submit a QC Inspection. Status (Pass/Fail) is auto-computed on validate."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    doc = frappe.get_doc("QC Inspection", inspection_name)
    if doc.docstatus != 0:
        frappe.throw(_("QC Inspection {0} is not in Draft state.").format(inspection_name))

    doc.flags.ignore_permissions = True
    doc.submit()
    frappe.db.commit()

    return {
        "inspection_name": inspection_name,
        "status":          doc.status,
        "docstatus":       doc.docstatus,
        "accepted":        doc.accepted_readings,
        "rejected":        doc.rejected_readings,
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def cancel_qc_inspection(inspection_name: str) -> dict:
    """Cancel a submitted QC Inspection (Books Admin only)."""
    roles = set(frappe.get_roles(frappe.session.user))
    if not (roles & {"Books Admin", "System Manager", "Administrator"}):
        frappe.throw(_("Only Books Admin can cancel a QC Inspection."), frappe.PermissionError)

    doc = frappe.get_doc("QC Inspection", inspection_name)
    if doc.docstatus != 1:
        frappe.throw(_("Only submitted QC Inspections can be cancelled."))

    doc.flags.ignore_permissions = True
    doc.cancel()
    frappe.db.commit()
    return {"inspection_name": inspection_name, "docstatus": 2, "status": "Cancelled"}


# ─── List view ────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def list_inspections(
    filters_json: str = None,
    page: int = 0,
    page_len: int = 50,
) -> dict:
    """
    Paginated list of QC Inspections with optional filters.
    filters_json: JSON object e.g. {"inspection_type":"Incoming","status":"Fail"}
    """
    base_filters = []
    if filters_json:
        flt_dict = json.loads(filters_json) if isinstance(filters_json, str) else filters_json
        for k, v in flt_dict.items():
            base_filters.append([k, "=", v])

    page_len = min(int(page_len), 200)
    page     = int(page)

    try:
        inspections = frappe.get_all(
            "QC Inspection",
            filters=base_filters,
            fields=[
                "name", "inspection_type", "status", "reference_type", "reference_name",
                "item", "item_name", "inspection_date", "inspected_by",
                "total_readings", "accepted_readings", "rejected_readings",
                "docstatus", "creation",
            ],
            order_by="creation desc",
            limit=page_len,
            start=page * page_len,
            ignore_permissions=True,
        )
        total = frappe.db.count("QC Inspection", filters=base_filters)
    except Exception as e:
        # Table may not exist yet (bench migrate not yet run)
        frappe.log_error(title="list_inspections error", message=frappe.get_traceback())
        return {"inspections": [], "total": 0, "page": page, "page_len": page_len,
                "error": str(e)}

    return {
        "inspections": inspections,
        "total": total,
        "page": page,
        "page_len": page_len,
    }


# ─── Dashboard stats ──────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_qc_dashboard_stats(company: str = None) -> dict:
    """
    Return QC stats for the dashboard / Quality Overview page.
    """
    from zoho_books_clone.api.session import _get_company
    company = company or _get_company(frappe.session.user)

    today = nowdate()

    def _count(filters):
        return frappe.db.count("QC Inspection", filters) or 0

    total       = _count({"docstatus": 1})
    passed      = _count({"docstatus": 1, "status": "Pass"})
    failed      = _count({"docstatus": 1, "status": "Fail"})
    pending     = _count({"docstatus": 0})
    today_count = _count({"inspection_date": today})

    pass_rate = round((passed / total * 100), 1) if total > 0 else 0

    # Trend: last 7 days
    trend = frappe.db.sql("""
        SELECT inspection_date, COUNT(*) as cnt,
               SUM(CASE WHEN status='Pass' THEN 1 ELSE 0 END) as passed,
               SUM(CASE WHEN status='Fail' THEN 1 ELSE 0 END) as failed
        FROM `tabQC Inspection`
        WHERE docstatus = 1 AND inspection_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        GROUP BY inspection_date
        ORDER BY inspection_date ASC
    """, as_dict=True)

    # Top failed items
    top_failed = frappe.db.sql("""
        SELECT item, item_name, COUNT(*) as fail_count
        FROM `tabQC Inspection`
        WHERE docstatus = 1 AND status = 'Fail'
        GROUP BY item, item_name
        ORDER BY fail_count DESC
        LIMIT 5
    """, as_dict=True)

    # Inspection type breakdown
    breakdown = frappe.db.sql("""
        SELECT inspection_type,
               COUNT(*) as total,
               SUM(CASE WHEN status='Pass' THEN 1 ELSE 0 END) as passed,
               SUM(CASE WHEN status='Fail' THEN 1 ELSE 0 END) as failed
        FROM `tabQC Inspection`
        WHERE docstatus = 1
        GROUP BY inspection_type
    """, as_dict=True)

    return {
        "total":        total,
        "passed":       passed,
        "failed":       failed,
        "pending":      pending,
        "today":        today_count,
        "pass_rate":    pass_rate,
        "trend":        trend,
        "top_failed":   top_failed,
        "breakdown":    breakdown,
    }


# ─── Certificate of Analysis (COA) ────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def generate_coa(inspection_name: str) -> dict:
    """
    Render the Certificate of Analysis HTML for a submitted QC Inspection.
    Returns dict: {"html": "<html>...", "inspection_name": ..., "status": ...}

    QC Inspection field → COA section mapping
    ------------------------------------------
    name                → coa_number (document identifier)
    status              → status banner + watermark
    item                → Product/Item Details → item_code
    item_name           → Product/Item Details → item_name
    reference_type      → Reference Document → reference_type
    reference_name      → Reference Document → reference_name
    inspection_type     → Reference Document → inspection_type
    qc_inspection_template → Reference Document → template_used
    batch_no            → Product/Item Details → batch_no
    work_order          → Product/Item Details → work_order
    inspection_date     → Inspection Details → inspection_date
    inspected_by        → Inspection Details → inspected_by
    verified_by         → Inspection Details → verified_by (optional 2nd sign-off)
    readings[].template_parameter → Test Parameters table → parameter
    readings[].parameter_type     → type column
    readings[].min_value / max_value / acceptance_criteria_value → specification
    readings[].reading_value      → actual_value
    readings[].status             → result (Accepted/Rejected/Pending)
    readings[].remarks            → remarks column
    total_readings, accepted_readings, rejected_readings → Summary strip
    QC Approval Request.approval_status → Inspection Details → QC Approval
    QC Approval Request.approved_by     → Signature block → QA Manager
    QC Approval Request.approval_date   → Signature block → Date
    remarks             → Remarks / Observations section
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    if not frappe.db.exists("QC Inspection", inspection_name):
        frappe.throw(_("QC Inspection {0} does not exist.").format(inspection_name))

    doc = frappe.get_doc("QC Inspection", inspection_name)

    if doc.docstatus != 1:
        status_label = {0: _("Draft"), 2: _("Cancelled")}.get(doc.docstatus, str(doc.docstatus))
        frappe.throw(_(
            "Cannot generate a Certificate of Analysis for QC Inspection {0} — "
            "it is <b>{1}</b>. Only submitted QC Inspections can produce a COA."
        ).format(inspection_name, status_label))

    # Company name
    company_name = ""
    try:
        company_name = frappe.db.get_single_value("Global Defaults", "default_company") or ""
    except Exception:
        pass

    # Approval info from QC Approval Request
    from zoho_books_clone.api.qc_approval import get_approval_status_for_inspection
    appr = get_approval_status_for_inspection(inspection_name)

    # Item enrichment
    dosage_form = ""
    item_group  = ""
    try:
        dosage_form = frappe.db.get_value("Item", doc.item, "dosage_form") or ""
        item_group  = frappe.db.get_value("Item", doc.item, "item_group") or ""
    except Exception:
        pass

    # Build parameters list
    parameters = []
    for rd in (doc.readings or []):
        if rd.parameter_type == "Numeric":
            spec = f"{rd.min_value or ''} – {rd.max_value or ''}"
        elif rd.parameter_type == "Non-Numeric":
            spec = rd.acceptance_criteria_value or ""
        else:
            spec = rd.formula or ""

        result = "Accepted" if rd.status == "Accepted" else ("Rejected" if rd.status == "Rejected" else "Pending")
        parameters.append({
            "parameter":    rd.template_parameter or "",
            "type":         rd.parameter_type or "",
            "specification": spec,
            "actual_value": rd.reading_value or "",
            "result":       result,
            "remarks":      rd.remarks or "",
        })

    # Template context — must match every {{ variable }} in certificate_of_analysis.html
    context = {
        "coa_number":        doc.name,
        "status":            doc.status,
        "company_name":      company_name,
        "generated_on":      frappe.utils.nowdate(),
        "generated_by":      frappe.session.user,
        # Product
        "item_code":         doc.item,
        "item_name":         doc.item_name or doc.item,
        "dosage_form":       dosage_form,
        "item_group":        item_group,
        "batch_no":          getattr(doc, "batch_no", "") or "",
        "work_order":        getattr(doc, "work_order", "") or "",
        # Reference
        "reference_type":    doc.reference_type,
        "reference_name":    doc.reference_name,
        "inspection_type":   doc.inspection_type,
        "template_used":     doc.qc_inspection_template or "",
        # Inspection
        "inspection_date":   str(doc.inspection_date) if doc.inspection_date else "",
        "inspected_by":      doc.inspected_by or "",
        "verified_by":       doc.verified_by or "",
        # Summary
        "total_readings":    doc.total_readings or 0,
        "accepted_readings": doc.accepted_readings or 0,
        "rejected_readings": doc.rejected_readings or 0,
        # Test parameters
        "parameters":        parameters,
        # Remarks
        "remarks":           doc.remarks or "",
        # Approval
        "approval_status":   appr["approval_status"] or "N/A",
        "approved_by":       appr["approved_by"] or "",
        "approval_date":     appr["approval_date"] or "",
    }

    template_path = "zoho_books_clone/templates/print_formats/certificate_of_analysis.html"
    html = frappe.render_template(template_path, context)

    return {
        "html":             html,
        "inspection_name": inspection_name,
        "status":          doc.status,
        "coa_number":      doc.name,
    }