"""
Asset Reports — Phase 6, part 1 of the asset-management build-out.

Read-only whitelisted APIs, same conventions as manufacturing/reports.py:
filters-dict in, {"rows": [...], "summary": {...}} out. Multi-tenant
isolation is enforced by Frappe's own permission_query_conditions on
every get_all() call, same as every other report in this app.

Part 1: Asset Register -- the master listing of every asset with its
current book position (original cost, accumulated depreciation, net
book value) and lifecycle status in one row.
Part 2: CWIP Register -- assets capitalized but not yet transferred out
of Capital Work-in-Progress.
Part 3: Depreciation Forecast -- upcoming (and, optionally, already-
posted) Depreciation Schedule rows across assets, for cash-flow /
expense planning.
Part 4: Disposal Report -- submitted Asset Disposal records with their
gain/loss position, for Scrap and Sale alike.

All four are backend-only as of this writing -- no Vue frontend/route
exists yet for any of them (see Asset.vue / router.js). Wiring these
into the SPA is separate, later work.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, date_diff, add_months

from zoho_books_clone.utils.access import assert_can

_DISPOSED_STATUSES = ("Scrapped", "Sold")


def _parse_filters(filters):
    if isinstance(filters, str):
        filters = frappe.parse_json(filters) or {}
    return filters or {}


# ─── Asset Register ───────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_asset_register_report(filters=None):
    """Return every Asset (submitted, unless include_draft is set) with its
    current book position.

    Columns: name, asset_name, asset_category, company, status,
             location, department, purchase_date, available_for_use_date,
             purchase_cost, accumulated_depreciation, current_value
             (= net book value), depreciation_method,
             depreciation_posting_frequency, is_existing_asset, is_active.

    Filters: company, asset_category, status ("All" / exact / "Active"
             meaning not Scrapped/Sold), location, department,
             as_on_date (only assets purchased on/before this date),
             include_draft (bool, default false -- draft Assets have no
             capitalization GL yet and no meaningful book value).
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Asset", "read")

    f = _parse_filters(filters)

    conditions = []
    if not f.get("include_draft"):
        conditions.append(["docstatus", "=", 1])
    else:
        conditions.append(["docstatus", "!=", 2])  # exclude cancelled either way

    if f.get("company"):
        conditions.append(["company", "=", f["company"]])
    if f.get("asset_category"):
        conditions.append(["asset_category", "=", f["asset_category"]])
    if f.get("location"):
        conditions.append(["location", "=", f["location"]])
    if f.get("department"):
        conditions.append(["department", "=", f["department"]])

    status_filter = f.get("status")
    if status_filter and status_filter not in ("All",):
        if status_filter == "Active":
            conditions.append(["status", "not in", list(_DISPOSED_STATUSES)])
        else:
            conditions.append(["status", "=", status_filter])

    as_on_date = f.get("as_on_date")
    if as_on_date:
        conditions.append(["purchase_date", "<=", str(getdate(as_on_date))])

    rows = frappe.get_all(
        "Asset",
        filters=conditions,
        fields=[
            "name", "asset_name", "asset_category", "company", "status",
            "location", "department", "purchase_date", "available_for_use_date",
            "purchase_cost", "current_value", "depreciation_method",
            "depreciation_posting_frequency", "useful_life", "salvage_value",
            "is_existing_asset", "is_active", "docstatus",
        ],
        order_by="asset_category asc, purchase_date asc",
        limit=1000,
    )

    for r in rows:
        purchase_cost = flt(r.get("purchase_cost"))
        current_value = flt(r.get("current_value")) if r.get("current_value") is not None else purchase_cost
        r["current_value"] = current_value
        r["accumulated_depreciation"] = max(0.0, purchase_cost - current_value)

    total_cost = sum(flt(r["purchase_cost"]) for r in rows)
    total_accum_dep = sum(flt(r["accumulated_depreciation"]) for r in rows)
    total_nbv = sum(flt(r["current_value"]) for r in rows)
    active_count = sum(1 for r in rows if r["status"] not in _DISPOSED_STATUSES)
    disposed_count = sum(1 for r in rows if r["status"] in _DISPOSED_STATUSES)

    by_category = {}
    for r in rows:
        cat = r.get("asset_category") or "Uncategorized"
        bucket = by_category.setdefault(cat, {"count": 0, "purchase_cost": 0.0, "current_value": 0.0})
        bucket["count"] += 1
        bucket["purchase_cost"] += flt(r["purchase_cost"])
        bucket["current_value"] += flt(r["current_value"])

    return {
        "rows": rows,
        "summary": {
            "total_assets": len(rows),
            "active_count": active_count,
            "disposed_count": disposed_count,
            "total_purchase_cost": total_cost,
            "total_accumulated_depreciation": total_accum_dep,
            "total_net_book_value": total_nbv,
        },
        "by_category": [
            {"asset_category": cat, **vals} for cat, vals in sorted(by_category.items())
        ],
    }


# ─── CWIP Register ─────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_cwip_register_report(filters=None):
    """Assets currently sitting in Capital Work-in-Progress -- capitalized
    (capitalization_posted=1) but not yet transferred to Fixed Asset
    (cwip_transferred=0). See assets/asset_gl.py and assets/cwip_posting.py
    for how an asset gets into and out of this state.

    Columns: name, asset_name, asset_category, company, purchase_date,
             available_for_use_date, purchase_cost (= CWIP balance),
             days_in_cwip, is_overdue (available_for_use_date has already
             arrived but the daily transfer job hasn't cleared it yet --
             worth investigating, usually a missing Fixed Asset Account
             on the category+company).

    Filters: company, asset_category.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Asset", "read")

    f = _parse_filters(filters)

    conditions = [
        ["docstatus", "=", 1],
        ["capitalization_posted", "=", 1],
        ["cwip_transferred", "=", 0],
    ]
    if f.get("company"):
        conditions.append(["company", "=", f["company"]])
    if f.get("asset_category"):
        conditions.append(["asset_category", "=", f["asset_category"]])

    rows = frappe.get_all(
        "Asset",
        filters=conditions,
        fields=[
            "name", "asset_name", "asset_category", "company",
            "purchase_date", "available_for_use_date", "purchase_cost",
        ],
        order_by="available_for_use_date asc",
        limit=1000,
    )

    today = getdate(nowdate())
    for r in rows:
        r["days_in_cwip"] = date_diff(today, getdate(r["purchase_date"])) if r.get("purchase_date") else None
        r["is_overdue"] = bool(
            r.get("available_for_use_date") and getdate(r["available_for_use_date"]) <= today
        )

    total_cwip_balance = sum(flt(r["purchase_cost"]) for r in rows)
    overdue_count = sum(1 for r in rows if r["is_overdue"])

    return {
        "rows": rows,
        "summary": {
            "total_in_cwip": len(rows),
            "total_cwip_balance": total_cwip_balance,
            "overdue_count": overdue_count,
        },
    }


# ─── Depreciation Forecast ─────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_depreciation_forecast_report(filters=None):
    """Depreciation Schedule rows across assets -- upcoming by default, for
    expense/cash-flow planning; can also include already-posted rows for a
    combined view. Depreciation Schedule is a child table of Asset (not its
    own doctype in the DB sense of having independent permissions), so
    eligible Asset names are resolved first and the child rows are then
    pulled in bulk via parent/parenttype -- same shape as
    depreciation_posting.py's own row selection, but read-only and across
    many assets at once instead of one.

    Columns: asset, asset_name, asset_category, company, period_no, year,
             depreciation_date, opening_value, depreciation_amount,
             closing_value, status, is_pro_rata, gl_posting_applicable
             (false for is_existing_asset assets -- see depreciation_
             posting.py's own skip of those; their schedule rows are shown
             here for reference but will never flip to Completed via the
             posting job).

    Filters: company, asset_category, status ("Pending" default / "Completed"
             / "All"), from_date, to_date (depreciation_date range -- default
             is today through 12 months out when status is Pending/All and
             no explicit range is given), limit (default 1000).
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Asset", "read")

    f = _parse_filters(filters)

    asset_conditions = [["docstatus", "=", 1]]
    if f.get("company"):
        asset_conditions.append(["company", "=", f["company"]])
    if f.get("asset_category"):
        asset_conditions.append(["asset_category", "=", f["asset_category"]])

    assets = frappe.get_all(
        "Asset",
        filters=asset_conditions,
        fields=["name", "asset_name", "asset_category", "company", "is_existing_asset"],
        limit=5000,
    )
    if not assets:
        return {"rows": [], "summary": {"total_rows": 0, "total_forecast_amount": 0.0}, "by_month": []}

    asset_map = {a["name"]: a for a in assets}
    asset_names = list(asset_map.keys())

    status_filter = f.get("status") or "Pending"
    from_date = f.get("from_date")
    to_date = f.get("to_date")
    if not from_date and not to_date and status_filter in ("Pending", "All"):
        # Default forecast window: today through 12 months out. Without this,
        # "All"/"Pending" on a mature install returns every remaining year of
        # every asset's schedule, which isn't what "forecast" implies.
        from_date = nowdate()
        to_date = str(add_months(getdate(nowdate()), 12))

    schedule_conditions = [
        ["parent", "in", asset_names],
        ["parenttype", "=", "Asset"],
    ]
    if status_filter != "All":
        schedule_conditions.append(["status", "=", status_filter])
    if from_date:
        schedule_conditions.append(["depreciation_date", ">=", str(getdate(from_date))])
    if to_date:
        schedule_conditions.append(["depreciation_date", "<=", str(getdate(to_date))])

    rows = frappe.get_all(
        "Depreciation Schedule",
        filters=schedule_conditions,
        fields=[
            "parent as asset", "period_no", "year", "depreciation_date",
            "opening_value", "depreciation_amount", "closing_value",
            "status", "is_pro_rata",
        ],
        order_by="depreciation_date asc",
        limit=int(f.get("limit") or 1000),
    )

    by_month = {}
    for r in rows:
        a = asset_map.get(r["asset"], {})
        r["asset_name"] = a.get("asset_name") or r["asset"]
        r["asset_category"] = a.get("asset_category")
        r["company"] = a.get("company")
        r["gl_posting_applicable"] = not bool(a.get("is_existing_asset"))

        month_key = str(getdate(r["depreciation_date"]))[:7] if r.get("depreciation_date") else "unknown"
        bucket = by_month.setdefault(month_key, {"month": month_key, "count": 0, "amount": 0.0})
        bucket["count"] += 1
        bucket["amount"] += flt(r["depreciation_amount"])

    total_forecast_amount = sum(flt(r["depreciation_amount"]) for r in rows)

    return {
        "rows": rows,
        "summary": {
            "total_rows": len(rows),
            "total_forecast_amount": total_forecast_amount,
            "assets_covered": len({r["asset"] for r in rows}),
        },
        "by_month": [by_month[k] for k in sorted(by_month.keys())],
    }


# ─── Disposal Report ────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_disposal_report(filters=None):
    """Submitted Asset Disposal records with their gain/loss position.
    Reads the snapshot fields written by assets/asset_disposal_gl.py.
    post_disposal_gl() at posting time (purchase_cost_snapshot,
    accumulated_depreciation_snapshot, net_book_value_snapshot,
    gain_loss_amount) rather than re-deriving them from the live Asset, so
    a disposal's reported figures always match what its own GL entry
    actually posted, even if the Asset was touched afterwards.

    Columns: name, asset, asset_name, asset_category, company,
             disposal_type, disposal_date, purchase_cost_snapshot,
             accumulated_depreciation_snapshot, net_book_value_snapshot,
             sale_amount, gain_loss_amount, gl_posted.

    Filters: company, disposal_type ("Scrap" / "Sale" / "All"),
             from_date, to_date (disposal_date range), asset_category.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Asset", "read")

    f = _parse_filters(filters)

    conditions = [["docstatus", "=", 1]]
    if f.get("company"):
        conditions.append(["company", "=", f["company"]])

    disposal_type = f.get("disposal_type")
    if disposal_type and disposal_type != "All":
        conditions.append(["disposal_type", "=", disposal_type])

    if f.get("from_date"):
        conditions.append(["disposal_date", ">=", str(getdate(f["from_date"]))])
    if f.get("to_date"):
        conditions.append(["disposal_date", "<=", str(getdate(f["to_date"]))])

    rows = frappe.get_all(
        "Asset Disposal",
        filters=conditions,
        fields=[
            "name", "asset", "company", "disposal_type", "disposal_date",
            "purchase_cost_snapshot", "accumulated_depreciation_snapshot",
            "net_book_value_snapshot", "sale_amount", "gain_loss_amount",
            "gl_posted",
        ],
        order_by="disposal_date desc",
        limit=1000,
    )

    if not rows:
        return {"rows": [], "summary": {"total_disposals": 0}, "by_type": []}

    asset_names = list({r["asset"] for r in rows if r.get("asset")})
    asset_info = {
        a["name"]: a
        for a in frappe.get_all(
            "Asset",
            filters=[["name", "in", asset_names]] if asset_names else [],
            fields=["name", "asset_name", "asset_category"],
        )
    }
    category_filter = f.get("asset_category")
    if category_filter:
        rows = [r for r in rows if asset_info.get(r["asset"], {}).get("asset_category") == category_filter]

    for r in rows:
        info = asset_info.get(r["asset"], {})
        r["asset_name"] = info.get("asset_name") or r["asset"]
        r["asset_category"] = info.get("asset_category")

    total_proceeds = sum(flt(r["sale_amount"]) for r in rows)
    total_gain = sum(flt(r["gain_loss_amount"]) for r in rows if flt(r["gain_loss_amount"]) > 0)
    total_loss = sum(-flt(r["gain_loss_amount"]) for r in rows if flt(r["gain_loss_amount"]) < 0)

    by_type = {}
    for r in rows:
        t = r["disposal_type"]
        bucket = by_type.setdefault(t, {"disposal_type": t, "count": 0, "net_book_value": 0.0, "gain_loss": 0.0})
        bucket["count"] += 1
        bucket["net_book_value"] += flt(r["net_book_value_snapshot"])
        bucket["gain_loss"] += flt(r["gain_loss_amount"])

    return {
        "rows": rows,
        "summary": {
            "total_disposals": len(rows),
            "scrapped_count": sum(1 for r in rows if r["disposal_type"] == "Scrap"),
            "sold_count": sum(1 for r in rows if r["disposal_type"] == "Sale"),
            "total_sale_proceeds": total_proceeds,
            "total_gain": total_gain,
            "total_loss": total_loss,
            "net_gain_loss": total_gain - total_loss,
        },
        "by_type": list(by_type.values()),
    }