"""
Production Plan (MRP) transactional actions.

Doctype-agnostic create/save/submit/cancel/amend/list of Production Plan
itself is handled by api/docs.py's generic endpoints — this module only holds
the bespoke logic specific to running MRP:

  get_open_sales_orders     -- list Sales Orders that still have undelivered
                                qty, for the demand picker on the Production
                                Plan form.
  get_items_from_sales_orders
                             -- given a list of selected Sales Order names,
                                aggregate pending (qty - delivered_qty) per
                                item across all of them and resolve each
                                item's default submitted BOM, so the
                                Items-to-Manufacture table can be
                                populated/refreshed client-side.
  get_raw_materials          -- explode the BOM for every row in
                                Items-to-Manufacture (reusing the same
                                ratio logic as work_order_engine.get_bom_breakdown),
                                aggregate raw-material qty across all rows,
                                and compare against on-hand stock in the
                                plan's default source warehouse.
  create_work_orders         -- bulk-generate one Draft Work Order per
                                Items-to-Manufacture row (for whatever
                                planned qty doesn't already have a Work
                                Order), tagging each with this Production
                                Plan for traceability. Work Orders are left
                                in Draft so a person can review/adjust
                                before submitting — this endpoint doesn't
                                submit them.
"""

import frappe
from frappe import _
from frappe.utils import flt

from zoho_books_clone.utils.access import assert_can
from zoho_books_clone.utils.tenancy import assert_doc_in_user_company
from zoho_books_clone.inventory.utils import get_stock_balance_bulk


def _parse_list(val):
    if isinstance(val, str):
        val = frappe.parse_json(val)
    return val or []


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_open_sales_orders(company=None):
    """Sales Orders that still have at least one item with undelivered qty.
    Excludes Closed/Cancelled orders outright before checking item-level
    pending qty, since those are done regardless of what's left on paper."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Sales Order", "read")

    filters = {"status": ["not in", ["Closed", "Cancelled"]]}
    if company:
        filters["company"] = company

    orders = frappe.get_all(
        "Sales Order", filters=filters,
        fields=["name", "customer", "customer_name", "transaction_date",
                "delivery_date", "status", "grand_total"],
        order_by="transaction_date desc", limit_page_length=500,
    )
    if not orders:
        return []

    order_names = [o.name for o in orders]
    item_rows = frappe.get_all(
        "Sales Order Item", filters={"parent": ["in", order_names]},
        fields=["parent", "qty", "delivered_qty"],
    )
    pending_by_order = {}
    for r in item_rows:
        pending_by_order[r.parent] = pending_by_order.get(r.parent, 0) + (flt(r.qty) - flt(r.delivered_qty))

    return [o for o in orders if pending_by_order.get(o.name, 0) > 0.0001]


@frappe.whitelist(allow_guest=False, methods=["POST"])
def get_items_from_sales_orders(sales_orders):
    """Aggregate pending qty per item across the given Sales Orders and
    resolve each item's default submitted BOM. Read-only — does not save."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Sales Order", "read")

    sales_orders = _parse_list(sales_orders)
    sales_orders = [s for s in sales_orders if s]
    if not sales_orders:
        frappe.throw(_("Select at least one Sales Order."))

    rows = frappe.get_all(
        "Sales Order Item", filters={"parent": ["in", sales_orders]},
        fields=["parent", "item_code", "item_name", "qty", "delivered_qty", "uom"],
    )

    agg = {}
    for r in rows:
        pending = flt(r.qty) - flt(r.delivered_qty)
        if pending <= 0 or not r.item_code:
            continue
        entry = agg.setdefault(r.item_code, {
            "item_code": r.item_code,
            "item_name": r.item_name,
            "planned_qty": 0.0,
            "stock_uom": r.uom,
            # Multiple orders can contribute to the same item — keep the
            # ordered, de-duplicated list of contributing orders here and
            # join it into the free-text "sales_order" field below. A plain
            # substring check on the joined string (e.g. "SO-0001" being a
            # substring of "SO-00010") would wrongly skip genuinely new
            # orders, so track membership with the list itself instead.
            "_sales_orders": [],
        })
        entry["planned_qty"] += pending
        if r.parent not in entry["_sales_orders"]:
            entry["_sales_orders"].append(r.parent)

    items = list(agg.values())
    for it in items:
        it["sales_order"] = ", ".join(it.pop("_sales_orders"))
        # Only resolve to a BOM that's still submitted AND active — an
        # is_default BOM that's since been deactivated/superseded shouldn't
        # get silently pre-selected on the Items-to-Manufacture table.
        bom = frappe.db.get_value(
            "BOM",
            {"item": it["item_code"], "is_default": 1, "docstatus": 1, "is_active": 1},
            "name",
        ) or frappe.db.get_value(
            "BOM",
            {"item": it["item_code"], "docstatus": 1, "is_active": 1},
            "name",
        )
        it["bom_no"] = bom or ""

    return items


@frappe.whitelist(allow_guest=False, methods=["POST"])
def get_raw_materials(po_items, warehouse=None):
    """Explode BOMs for the given Items-to-Manufacture rows, aggregate raw
    material requirement across all of them, and compare against on-hand
    stock in `warehouse` (the plan's default source warehouse). Read-only."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("BOM", "read")

    from zoho_books_clone.manufacturing.work_order_engine import get_bom_breakdown

    po_items = _parse_list(po_items)
    po_items = [r for r in po_items if r.get("bom_no") and flt(r.get("planned_qty")) > 0]
    if not po_items:
        frappe.throw(_("Add items with a selected BOM and Planned Qty first."))

    # Reuse the same explosion logic Work Orders use so Packing BOMs (whose
    # materials live in packing_items + bulk_item, not the `items` table) and
    # Manufacturing/Sub-Assembly BOMs with sub-assembly or phantom rows (which
    # need recursive explosion down to leaf raw materials) are both handled
    # correctly — reading bom_doc.items directly here, as before, silently
    # produced zero rows for Packing BOMs and counted intermediate
    # sub-assembly items as if they were purchasable raw materials.
    agg = {}
    for row in po_items:
        breakdown = get_bom_breakdown(row["bom_no"], row["planned_qty"])
        for r in breakdown["items"]:
            entry = agg.setdefault(r["item_code"], {
                "item_code": r["item_code"], "item_name": r["item_name"],
                "uom": r["uom"], "required_qty": 0.0,
            })
            entry["required_qty"] += flt(r["required_qty"])

    item_codes = list(agg.keys())
    balances = get_stock_balance_bulk(item_codes, warehouse) if warehouse else {}

    results = []
    for code, entry in agg.items():
        available = flt(balances.get(code, 0))
        entry["available_qty"] = available
        entry["shortfall_qty"] = max(0.0, entry["required_qty"] - available)
        results.append(entry)

    results.sort(key=lambda r: r["item_code"])
    return results


@frappe.whitelist(allow_guest=False, methods=["POST"])
def create_work_orders(production_plan):
    """Create one Draft Work Order per Items-to-Manufacture row for
    whatever planned qty doesn't already have a Work Order. Left in Draft
    for review — this does not submit them."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Work Order", "write")

    pp = frappe.get_doc("Production Plan", production_plan)
    assert_doc_in_user_company(pp)
    if pp.docstatus != 1:
        frappe.throw(_("Production Plan must be submitted first."))

    if not pp.default_fg_warehouse:
        frappe.throw(_("Set a Default Finished Goods Warehouse on the Production Plan first."))

    created = []
    for row in pp.po_items:
        pending = flt(row.planned_qty) - flt(row.work_order_created_qty)
        if pending <= 0.0001:
            continue
        if not row.bom_no:
            frappe.throw(_("Row for {0}: no BOM selected — cannot create a Work Order.").format(row.item_code))

        wo = frappe.new_doc("Work Order")
        wo.bom = row.bom_no
        # production_item's fetch_from="bom.item" only runs in the browser
        # form controller — it does nothing on a server-side frappe.new_doc()
        # insert, and the field is mandatory, so without this line every row
        # here throws a MandatoryError before the first Work Order is even
        # created.
        wo.production_item = row.item_code
        wo.qty = pending
        wo.source_warehouse = pp.default_source_warehouse
        wo.wip_warehouse = pp.default_wip_warehouse
        wo.fg_warehouse = row.warehouse or pp.default_fg_warehouse
        wo.scrap_warehouse = pp.default_scrap_warehouse
        wo.company = pp.company
        wo.sales_order = row.sales_order
        wo.production_plan = pp.name
        wo.remarks = _("Auto-created from Production Plan {0}").format(pp.name)
        wo.insert(ignore_permissions=True)
        created.append(wo.name)

        row.db_set("work_order_created_qty", flt(row.work_order_created_qty) + pending, update_modified=False)

    if not created:
        frappe.throw(_("Nothing to create — every row already has a Work Order for its full Planned Qty."))

    pp.db_set("status", "Work Orders Created")
    frappe.db.commit()

    return created


@frappe.whitelist(allow_guest=False, methods=["POST"])
def bulk_submit_work_orders(production_plan):
    """Submit all Draft Work Orders linked to this Production Plan at once.
    Returns a dict with counts: submitted, skipped (already submitted), errors."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Work Order", "write")

    pp = frappe.get_doc("Production Plan", production_plan)
    assert_doc_in_user_company(pp)
    if pp.docstatus != 1:
        frappe.throw(_("Production Plan must be submitted first."))

    draft_wos = frappe.get_all(
        "Work Order",
        filters={"production_plan": production_plan, "docstatus": 0},
        fields=["name"],
    )

    submitted = []
    errors = []
    for wo_row in draft_wos:
        try:
            wo = frappe.get_doc("Work Order", wo_row.name)
            wo.submit()
            submitted.append(wo.name)
        except Exception as exc:
            errors.append({"name": wo_row.name, "error": str(exc)})

    frappe.db.commit()
    return {"submitted": submitted, "errors": errors}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def create_material_requests(production_plan):
    """Create one Material Request (Purpose = Purchase) from the shortfall rows
    in the Production Plan's Raw Materials tab (mr_items table). Only rows with
    shortfall_qty > 0 are included. Returns the list of Material Request names."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Work Order", "read")

    pp = frappe.get_doc("Production Plan", production_plan)
    assert_doc_in_user_company(pp)
    if pp.docstatus != 1:
        frappe.throw(_("Production Plan must be submitted before creating Material Requests."))

    shortfall_rows = [r for r in (pp.mr_items or []) if flt(r.shortfall_qty) > 0.0001]
    if not shortfall_rows:
        frappe.throw(_(
            "No shortfall found. Run 'Calculate Requirement' on the Raw Materials tab "
            "first, or there is no shortfall to procure."
        ))

    mr = frappe.new_doc("Material Request")
    mr.material_request_type = "Purchase"
    mr.company = pp.company
    mr.production_plan = pp.name
    mr.remarks = _("Auto-created from Production Plan {0}").format(pp.name)
    for row in shortfall_rows:
        mr.append("items", {
            "item_code": row.item_code,
            "item_name": row.item_name,
            "required_qty": flt(row.shortfall_qty),
            "uom": row.uom,
            "warehouse": pp.default_source_warehouse or "",
        })
    mr.insert(ignore_permissions=True)
    frappe.db.commit()

    return [mr.name]


def maybe_complete_production_plan(production_plan_name):
    """Called after a Work Order is completed. If every Work Order linked to the
    Production Plan is now Completed, set the PP status to 'Completed'."""
    if not production_plan_name:
        return
    all_wos = frappe.get_all(
        "Work Order",
        filters={"production_plan": production_plan_name, "docstatus": 1},
        fields=["status"],
    )
    if not all_wos:
        return
    if all(wo.status == "Completed" for wo in all_wos):
        frappe.db.set_value("Production Plan", production_plan_name, "status", "Completed")