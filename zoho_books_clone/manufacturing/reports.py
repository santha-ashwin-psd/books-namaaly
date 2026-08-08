"""
Manufacturing Reports — read-only whitelisted APIs that power the
ManufacturingReports.vue dashboard.

All queries respect multi-tenant company isolation: Frappe's
permission_query_conditions hook already filters every `get_all` call,
so only rows the caller is allowed to see are returned.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from zoho_books_clone.utils.access import assert_can


# ─── helpers ─────────────────────────────────────────────────────────────────

def _parse_filters(filters):
    """Normalise filters dict coming from the frontend (JSON string or dict)."""
    if isinstance(filters, str):
        filters = frappe.parse_json(filters) or {}
    return filters or {}


def _date_filters(filters, date_field="creation"):
    """Build (from_date, to_date) from filters, defaulting to this month."""
    today = nowdate()
    from_date = filters.get("from_date") or frappe.utils.get_first_day(today)
    to_date = filters.get("to_date") or today
    return str(getdate(from_date)), str(getdate(to_date))


# ─── 1. Work Order Status Report ─────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_work_order_status_report(filters=None):
    """Return all Work Orders matching the given filters with completion %.

    Columns: name, production_item, item_name, qty, produced_qty,
             completion_pct, status, bom, company, creation.

    Filters: from_date, to_date (creation range), status (exact or 'All'),
             production_item.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Work Order", "read")

    f = _parse_filters(filters)
    from_date, to_date = _date_filters(f)

    conditions = [
        ["creation", ">=", from_date],
        ["creation", "<=", to_date],
    ]
    status_filter = f.get("status")
    if status_filter and status_filter != "All":
        conditions.append(["status", "=", status_filter])
    item_filter = f.get("production_item")
    if item_filter:
        conditions.append(["production_item", "=", item_filter])

    rows = frappe.get_all(
        "Work Order",
        filters=conditions,
        fields=["name", "production_item", "qty", "produced_qty",
                "status", "bom", "company", "creation", "docstatus"],
        order_by="creation desc",
        limit=500,
    )

    for r in rows:
        qty = flt(r.get("qty") or 0)
        produced = flt(r.get("produced_qty") or 0)
        r["completion_pct"] = round((produced / qty * 100) if qty else 0, 1)
        r["item_name"] = frappe.db.get_value("Item", r["production_item"], "item_name") or r["production_item"]

    summary = {
        "total": len(rows),
        "draft": sum(1 for r in rows if r["docstatus"] == 0),
        "submitted": sum(1 for r in rows if r["status"] == "Submitted"),
        "in_process": sum(1 for r in rows if r["status"] == "In Process"),
        "completed": sum(1 for r in rows if r["status"] == "Completed"),
        "stopped": sum(1 for r in rows if r["status"] == "Stopped"),
    }

    return {"rows": rows, "summary": summary}


# ─── 2. Stock Requirement Report ─────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_stock_requirement_report(filters=None):
    """Aggregate raw material requirements from open (submitted, non-completed)
    Work Orders vs current stock balance.

    Columns: item_code, item_name, required_qty, on_hand_qty, shortfall_qty,
             uom, source_warehouse, work_orders (count).

    Filters: warehouse (default source warehouse), status.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Work Order", "read")

    f = _parse_filters(filters)
    wo_status_filter = f.get("status") or "active"  # "active" = submitted + in-process

    # Get open Work Orders
    wo_status_conditions = []
    if wo_status_filter == "active":
        wo_status_conditions = [["status", "in", ["Submitted", "In Process"]]]
    elif wo_status_filter != "All":
        wo_status_conditions = [["status", "=", wo_status_filter]]

    open_wos = frappe.get_all(
        "Work Order",
        filters=[["docstatus", "=", 1]] + wo_status_conditions,
        fields=["name", "status"],
    )
    if not open_wos:
        return {"rows": [], "summary": {"total_items": 0, "shortfall_items": 0}}

    wo_names = [w.name for w in open_wos]

    # Aggregate raw material requirements across all open WOs
    item_map = {}
    for wo_name in wo_names:
        items = frappe.get_all(
            "Work Order Item",
            filters={"parent": wo_name},
            fields=["item_code", "required_qty", "consumed_qty", "uom", "source_warehouse"],
        )
        for row in items:
            ic = row.item_code
            pending = flt(row.required_qty) - flt(row.consumed_qty)
            if pending <= 0:
                continue
            if ic not in item_map:
                item_map[ic] = {
                    "item_code": ic,
                    "item_name": "",
                    "required_qty": 0.0,
                    "uom": row.uom or "",
                    "source_warehouse": row.source_warehouse or "",
                    "work_order_count": 0,
                }
            item_map[ic]["required_qty"] += pending
            item_map[ic]["work_order_count"] += 1
            if not item_map[ic]["source_warehouse"] and row.source_warehouse:
                item_map[ic]["source_warehouse"] = row.source_warehouse

    if not item_map:
        return {"rows": [], "summary": {"total_items": 0, "shortfall_items": 0}}

    # Resolve item names and stock balances in bulk
    item_codes = list(item_map.keys())
    item_names = frappe.get_all("Item", filters=[["name", "in", item_codes]], fields=["name", "item_name"])
    for i in item_names:
        if i.name in item_map:
            item_map[i.name]["item_name"] = i.item_name or i.name

    # Get on-hand stock per item (sum across all warehouses or filter by source_warehouse)
    warehouse_filter = f.get("warehouse")
    for ic in item_codes:
        try:
            wh = warehouse_filter or item_map[ic]["source_warehouse"] or None
            if wh:
                on_hand = frappe.db.get_value(
                    "Stock Ledger Entry",
                    {"item_code": ic, "warehouse": wh},
                    "sum(actual_qty)",
                ) or 0
            else:
                on_hand = frappe.db.sql(
                    "SELECT SUM(actual_qty) FROM `tabStock Ledger Entry` WHERE item_code = %s",
                    ic,
                )[0][0] or 0
        except Exception:
            on_hand = 0
        item_map[ic]["on_hand_qty"] = flt(on_hand)
        item_map[ic]["shortfall_qty"] = max(0.0, item_map[ic]["required_qty"] - flt(on_hand))

    rows = sorted(item_map.values(), key=lambda r: r["shortfall_qty"], reverse=True)
    shortfall_items = sum(1 for r in rows if r["shortfall_qty"] > 0.0001)

    return {
        "rows": rows,
        "summary": {
            "total_items": len(rows),
            "shortfall_items": shortfall_items,
        },
    }


# ─── 3. BOM Cost Analysis ─────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_bom_cost_analysis(filters=None):
    """Return submitted BOMs with their stored cost roll-up fields.

    Columns: name, item, item_name, bom_type, quantity, rm_cost, op_cost,
             scrap_value, total_cost, is_active, is_default, company.

    Filters: bom_type, item, is_active.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("BOM", "read")

    f = _parse_filters(filters)
    conditions = [["docstatus", "=", 1]]

    bom_type = f.get("bom_type")
    if bom_type and bom_type != "All":
        conditions.append(["bom_type", "=", bom_type])

    item_filter = f.get("item")
    if item_filter:
        conditions.append(["item", "=", item_filter])

    is_active = f.get("is_active")
    if is_active is not None and is_active != "":
        conditions.append(["is_active", "=", int(is_active)])

    rows = frappe.get_all(
        "BOM",
        filters=conditions,
        fields=["name", "item", "bom_type", "quantity", "rm_cost",
                "op_cost", "scrap_value", "total_cost",
                "is_active", "is_default", "company", "creation"],
        order_by="total_cost desc",
        limit=500,
    )

    for r in rows:
        r["item_name"] = frappe.db.get_value("Item", r["item"], "item_name") or r["item"]

    total_rm   = sum(flt(r["rm_cost"])    for r in rows)
    total_op   = sum(flt(r["op_cost"])    for r in rows)
    total_cost = sum(flt(r["total_cost"]) for r in rows)

    return {
        "rows": rows,
        "summary": {
            "total_boms":  len(rows),
            "total_rm":    total_rm,
            "total_op":    total_op,
            "total_cost":  total_cost,
        },
    }


# ─── 4. Production Performance Report ────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_production_performance_report(filters=None):
    """Return completed or in-process Work Orders with yield and efficiency metrics.

    Columns: name, production_item, item_name, qty (planned), produced_qty,
             process_loss_qty, yield_pct, efficiency_pct, status, company, creation.

    Filters: from_date, to_date, status.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Work Order", "read")

    f = _parse_filters(filters)
    from_date, to_date = _date_filters(f)

    status_filter = f.get("status") or "Completed"

    conditions = [
        ["docstatus", "=", 1],
        ["creation", ">=", from_date],
        ["creation", "<=", to_date],
    ]
    if status_filter != "All":
        conditions.append(["status", "=", status_filter])

    rows = frappe.get_all(
        "Work Order",
        filters=conditions,
        fields=["name", "production_item", "qty", "produced_qty",
                "process_loss_qty", "status", "company", "creation"],
        order_by="creation desc",
        limit=500,
    )

    for r in rows:
        qty         = flt(r.get("qty") or 0)
        produced    = flt(r.get("produced_qty") or 0)
        loss        = flt(r.get("process_loss_qty") or 0)
        total_input = produced + loss
        r["item_name"]      = frappe.db.get_value("Item", r["production_item"], "item_name") or r["production_item"]
        r["yield_pct"]      = round((produced / total_input * 100) if total_input else 100.0, 2)
        r["efficiency_pct"] = round((produced / qty * 100) if qty else 0.0, 2)

    if not rows:
        return {"rows": [], "summary": {}}

    avg_yield = round(sum(r["yield_pct"] for r in rows) / len(rows), 2)
    avg_eff   = round(sum(r["efficiency_pct"] for r in rows) / len(rows), 2)
    total_planned  = sum(flt(r["qty"]) for r in rows)
    total_produced = sum(flt(r["produced_qty"]) for r in rows)

    return {
        "rows": rows,
        "summary": {
            "total_orders":    len(rows),
            "total_planned":   total_planned,
            "total_produced":  total_produced,
            "avg_yield_pct":   avg_yield,
            "avg_efficiency":  avg_eff,
        },
    }


# ─── 5. Bulk → Packed Reconciliation Report (Phase 6b) ───────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_bulk_packing_reconciliation_report(filters=None):
    """Thin wrapper around manufacturing.packing_engine.
    list_bulk_packing_reconciliations() that adapts it to the same
    filters-dict convention every other report on this dashboard uses, so
    ManufacturingReports.vue's generic runReport()/API_MAP plumbing didn't
    need a special case for this one tab.

    Columns: work_order, bulk_item, bulk_item_name, fg_warehouse,
             qty_planned, bulk_qty_produced, bulk_qty_consumed_posted,
             bulk_qty_reserved_unposted, bulk_qty_remaining_in_warehouse,
             bulk_qty_unaccounted, status, wo_status, planned_start_date.

    Filters: from_date, to_date (Work Order planned_start_date range,
             falling back to creation date -- see list_bulk_packing_
             reconciliations()'s own docstring), status ("shortage" /
             "overpack" / "reconciled" / "All"), company.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Work Order", "read")

    f = _parse_filters(filters)
    from_date, to_date = _date_filters(f)

    from zoho_books_clone.manufacturing.packing_engine import list_bulk_packing_reconciliations

    status_filter = f.get("status")
    if status_filter in (None, "All"):
        status_filter = None

    data = list_bulk_packing_reconciliations(
        from_date=from_date,
        to_date=to_date,
        status=status_filter,
        company=f.get("company"),
        limit=f.get("limit") or 200,
    )
    rows = data["rows"]

    summary = {
        "total": len(rows),
        "shortage": sum(1 for r in rows if r["status"] == "shortage"),
        "overpack": sum(1 for r in rows if r["status"] == "overpack"),
        "reconciled": sum(1 for r in rows if r["status"] == "reconciled"),
        "truncated": data["truncated"],
    }

    return {"rows": rows, "summary": summary}


# ─── 6. Scrap & Manufacturing Variance Report ────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_scrap_variance_report(filters=None):
    """Return recovered scrap value and abnormal manufacturing variance loss
    per Manufacture Stock Entry, so scrap recovery and abnormal write-offs
    (see work_order_engine.complete_work_order's manufacturing_variance_loss)
    are visible in aggregate/report form instead of only inline on each
    Work Order's Cost Breakdown / Linked Stock Entries cards.

    Columns: stock_entry, posting_date, work_order, production_item,
             item_name, scrap_value, manufacturing_variance_loss.

    Filters: from_date, to_date (Stock Entry posting_date range).
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Work Order", "read")

    f = _parse_filters(filters)
    from_date, to_date = _date_filters(f, date_field="posting_date")

    # One query, with scrap value pre-summed across every is_scrap_item=1
    # row on that entry via LEFT JOIN + GROUP BY -- avoids an N+1 query per
    # Stock Entry for what would otherwise be a second child-table lookup
    # per row.
    rows = frappe.db.sql(
        """
        SELECT
            se.name AS stock_entry,
            se.posting_date,
            se.work_order,
            se.manufacturing_variance_loss,
            COALESCE(SUM(sed.qty * sed.basic_rate), 0) AS scrap_value
        FROM `tabStock Entry` se
        LEFT JOIN `tabStock Entry Detail` sed
            ON sed.parent = se.name AND sed.is_scrap_item = 1
        WHERE se.docstatus = 1
          AND se.stock_entry_type = 'Manufacture'
          AND se.work_order IS NOT NULL AND se.work_order != ''
          AND se.posting_date >= %s AND se.posting_date <= %s
        GROUP BY se.name
        HAVING scrap_value > 0 OR se.manufacturing_variance_loss > 0
        ORDER BY se.posting_date DESC
        LIMIT 500
        """,
        (from_date, to_date),
        as_dict=True,
    )

    if not rows:
        return {"rows": [], "summary": {}}

    # Batch-fetch each row's Work Order -> production_item -> item_name,
    # rather than a lookup per row.
    wo_names = list({r.work_order for r in rows})
    wo_items = {
        w.name: w.production_item
        for w in frappe.get_all("Work Order", filters=[["name", "in", wo_names]], fields=["name", "production_item"])
    }
    item_codes = list({v for v in wo_items.values() if v})
    item_names = {
        i.name: i.item_name
        for i in frappe.get_all("Item", filters=[["name", "in", item_codes]], fields=["name", "item_name"])
    }

    for r in rows:
        r["scrap_value"] = flt(r["scrap_value"])
        r["manufacturing_variance_loss"] = flt(r["manufacturing_variance_loss"])
        r["production_item"] = wo_items.get(r["work_order"]) or ""
        r["item_name"] = item_names.get(r["production_item"]) or r["production_item"]

    summary = {
        "total_entries":       len(rows),
        "total_scrap_value":   sum(r["scrap_value"] for r in rows),
        "total_variance_loss": sum(r["manufacturing_variance_loss"] for r in rows),
    }

    return {"rows": rows, "summary": summary}


# ─── 7. Scrap Reuse Savings Report ───────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_scrap_reuse_savings_report(filters=None):
    """Scrap Reuse feature, Phase 7 -- the actual cost impact of every
    applied Scrap Reuse action (Material Substitution Log entries with
    substitution_type='Scrap Reuse' and approval_status in Approved /
    Applied Immediately -- Pending/Rejected never touched the Work Order,
    so they carry no cost impact).

    Per log entry:
      displaced_qty      -- how much of the ORIGINAL raw material's
                             required_qty this action displaced, in the
                             original item's own UOM (original_required_qty
                             - new_required_qty, i.e. this action's own
                             delta -- not the row's cumulative total if
                             scrap was reused against it more than once,
                             since each call gets its own log entry).
      fresh_cost_avoided -- displaced_qty * the ORIGINAL row's fresh rate,
                             read from the Work Order Item row itself
                             (work_order_item_row -- see
                             apply_partial_scrap_substitution, which keeps
                             that row's `rate` unchanged across the split,
                             so it's still the fresh-material rate that was
                             in effect at split time, not a rate that could
                             have drifted since).
      scrap_cost_incurred -- scrap_qty * the scrap row's rate, read from
                             the new Work Order Item row (new_work_order_item_row
                             -- the scrap valuation rate resolved by
                             _resolve_scrap_warehouse at split time).
      savings             -- fresh_cost_avoided - scrap_cost_incurred. This
                             is the whole point of the feature (see Phase 6
                             plan): positive savings means scrap was cheaper
                             than the fresh material it displaced. Can be
                             negative in principle (e.g. an unusually
                             overvalued scrap warehouse) -- shown as-is
                             rather than clamped, so a negative-savings
                             pattern is visible instead of hidden.

    Columns: log_name, work_order, original_item_code, alternative_item_code
             (the scrap item), displaced_qty, scrap_qty, fresh_unit_rate,
             scrap_unit_rate, fresh_cost_avoided, scrap_cost_incurred,
             savings, requested_by, request_date, approval_status.

    Filters: from_date, to_date (Material Substitution Log request_date
             range), work_order (optional exact match).
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Work Order", "read")

    f = _parse_filters(filters)
    from_date, to_date = _date_filters(f, date_field="request_date")

    log_filters = {
        "substitution_type": "Scrap Reuse",
        "approval_status": ["in", ["Approved", "Applied Immediately"]],
        "request_date": ["between", [from_date, to_date]],
    }
    if f.get("work_order"):
        log_filters["work_order"] = f["work_order"]

    logs = frappe.get_all(
        "Material Substitution Log",
        filters=log_filters,
        fields=[
            "name", "work_order", "work_order_item_row", "new_work_order_item_row",
            "original_item_code", "alternative_item_code",
            "original_required_qty", "new_required_qty", "scrap_qty",
            "requested_by", "request_date", "approval_status",
        ],
        order_by="request_date desc",
        limit=500,
        ignore_permissions=True,
    )

    if not logs:
        return {"rows": [], "summary": {}}

    # Batch-fetch every fresh/scrap row's rate in one query rather than two
    # lookups per log entry.
    row_names = list({l.work_order_item_row for l in logs} | {l.new_work_order_item_row for l in logs if l.new_work_order_item_row})
    row_rates = {
        r.name: flt(r.rate)
        for r in frappe.get_all("Work Order Item", filters=[["name", "in", row_names]], fields=["name", "rate"])
    }

    rows = []
    for l in logs:
        displaced_qty = flt(l.original_required_qty) - flt(l.new_required_qty)
        fresh_unit_rate = row_rates.get(l.work_order_item_row, 0.0)
        scrap_unit_rate = row_rates.get(l.new_work_order_item_row, 0.0)
        fresh_cost_avoided = displaced_qty * fresh_unit_rate
        scrap_cost_incurred = flt(l.scrap_qty) * scrap_unit_rate
        rows.append({
            "log_name": l.name,
            "work_order": l.work_order,
            "original_item_code": l.original_item_code,
            "alternative_item_code": l.alternative_item_code,
            "displaced_qty": displaced_qty,
            "scrap_qty": flt(l.scrap_qty),
            "fresh_unit_rate": fresh_unit_rate,
            "scrap_unit_rate": scrap_unit_rate,
            "fresh_cost_avoided": fresh_cost_avoided,
            "scrap_cost_incurred": scrap_cost_incurred,
            "savings": fresh_cost_avoided - scrap_cost_incurred,
            "requested_by": l.requested_by,
            "request_date": str(l.request_date) if l.request_date else "",
            "approval_status": l.approval_status,
        })

    summary = {
        "total_actions":        len(rows),
        "total_fresh_avoided":  sum(r["fresh_cost_avoided"] for r in rows),
        "total_scrap_cost":     sum(r["scrap_cost_incurred"] for r in rows),
        "total_savings":        sum(r["savings"] for r in rows),
    }

    return {"rows": rows, "summary": summary}