"""
Work Order transactional actions.

Everything doctype-agnostic (create/save/submit/cancel/amend/list Work Order
itself) is already handled by api/docs.py's generic endpoints — this module
only holds the bespoke logic that's specific to running a Work Order:

  get_bom_breakdown   -- preview raw materials & operations from a BOM at a
                          given qty, so the Work Order form can populate/
                          refresh its child tables client-side before save.
  issue_materials      -- Material Transfer of raw materials into the WIP
                          warehouse (only relevant if a WIP warehouse is set).
  complete_work_order  -- the Manufacture Stock Entry: consumes raw
                          materials, receives the finished item (batch-aware,
                          reuses Batch's shelf-life auto-calc & auto-naming),
                          and posts recoverable scrap/by-products. Being a
                          plain "Manufacture" Stock Entry, it automatically
                          passes through the existing QC gate
                          (auto_create_qc_for_stock_entry) if the finished
                          item requires inspection — no bespoke QC wiring
                          needed here.
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate

from zoho_books_clone.utils.access import assert_can


def _get_work_order(work_order):
    wo = frappe.get_doc("Work Order", work_order)
    if wo.docstatus != 1:
        frappe.throw(_("Work Order must be submitted first."))
    return wo


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_bom_breakdown(bom, qty):
    """Preview the raw-material & operation rows a Work Order would get from
    this BOM at the given quantity. Read-only — does not save anything."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    bom_doc = frappe.get_doc("BOM", bom)
    if bom_doc.docstatus != 1:
        frappe.throw(_("Only a submitted BOM can be used on a Work Order."))

    ratio = flt(qty) / flt(bom_doc.quantity or 1)

    items = [{
        "item_code": r.item_code,
        "item_name": r.item_name,
        "required_qty": flt(r.qty) * ratio,
        "uom": r.uom,
        "rate": flt(r.rate),
        "amount": flt(r.rate) * flt(r.qty) * ratio,
    } for r in bom_doc.items]

    operations = [{
        "operation": r.operation,
        "workstation": r.workstation,
        "planned_time_in_mins": flt(r.time_in_mins),
        "hour_rate": flt(r.hour_rate),
        "cost": flt(r.cost),
    } for r in bom_doc.operations]

    return {
        "production_item": bom_doc.item,
        "item_name": frappe.db.get_value("Item", bom_doc.item, "item_name"),
        "stock_uom": frappe.db.get_value("Item", bom_doc.item, "stock_uom"),
        "items": items,
        "operations": operations,
    }


@frappe.whitelist(allow_guest=False, methods=["POST"])
def issue_materials(work_order):
    """Material Transfer of all still-pending raw materials into the Work
    Order's WIP warehouse. Only meaningful if a WIP warehouse is set —
    otherwise Complete Work Order consumes straight from Source Warehouse
    and this step can be skipped entirely."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Stock Entry", "write")

    wo = _get_work_order(work_order)
    if not wo.wip_warehouse:
        frappe.throw(_(
            "Set a Work-in-Progress Warehouse on the Work Order to issue "
            "materials as a separate step, or skip straight to Complete Work Order."
        ))

    se = frappe.new_doc("Stock Entry")
    se.company = wo.company
    se.stock_entry_type = "Material Transfer"
    se.posting_date = nowdate()
    se.work_order = wo.name
    se.remarks = f"Material issue for Work Order {wo.name}"

    for row in wo.items:
        pending = flt(row.required_qty) - flt(row.transferred_qty)
        if pending <= 0:
            continue
        se.append("items", {
            "item_code": row.item_code,
            "qty": pending,
            "s_warehouse": row.source_warehouse or wo.source_warehouse,
            "t_warehouse": wo.wip_warehouse,
        })

    if not se.items:
        frappe.throw(_("All raw materials have already been issued for this Work Order."))

    se.insert(ignore_permissions=True)
    se.submit()

    for row in wo.items:
        row.db_set("transferred_qty", flt(row.required_qty), update_modified=False)
    if wo.status == "Submitted":
        wo.db_set("status", "In Process")
    frappe.db.commit()

    return se.name


@frappe.whitelist(allow_guest=False, methods=["POST"])
def complete_work_order(work_order, qty_manufactured, process_loss_qty=0,
                         scrap_items=None, batch_no=None,
                         manufacturing_date=None, expiry_date=None):
    """Create & submit the Manufacture Stock Entry for a batch of production
    against this Work Order. Can be called multiple times for partial
    completions until produced_qty reaches the planned qty.

    qty_manufactured  -- finished-good qty actually produced this run
    process_loss_qty  -- material that never became stock (evaporation,
                         trimming, spillage etc.) — logged for yield
                         reporting only, no stock movement
    scrap_items       -- optional list of {item_code, qty} recoverable
                         by-products that DO get a stock movement into
                         scrap_warehouse
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Stock Entry", "write")

    if isinstance(scrap_items, str):
        scrap_items = frappe.parse_json(scrap_items)
    scrap_items = scrap_items or []

    wo = _get_work_order(work_order)

    qty_manufactured = flt(qty_manufactured)
    process_loss_qty = flt(process_loss_qty)
    if qty_manufactured <= 0:
        frappe.throw(_("Quantity Manufactured must be greater than zero."))

    remaining = flt(wo.qty) - flt(wo.produced_qty)
    if qty_manufactured > remaining + 0.0001:
        frappe.throw(_(
            "Quantity Manufactured ({0}) exceeds the remaining planned qty ({1})."
        ).format(qty_manufactured, remaining))

    ratio = qty_manufactured / flt(wo.qty or 1)

    se = frappe.new_doc("Stock Entry")
    se.company = wo.company
    se.stock_entry_type = "Manufacture"
    se.posting_date = nowdate()
    se.work_order = wo.name
    se.remarks = f"Manufacture against Work Order {wo.name}"

    # Consume raw materials proportional to what's being completed this run.
    # Source is the WIP warehouse if materials were staged there via
    # issue_materials; otherwise straight from each row's own source
    # warehouse (or the Work Order's default).
    for row in wo.items:
        consume_qty = flt(row.required_qty) * ratio
        if consume_qty <= 0:
            continue
        s_wh = wo.wip_warehouse or row.source_warehouse or wo.source_warehouse
        if not s_wh:
            frappe.throw(_(
                "Row for {0}: no Source Warehouse set (on the Work Order Item, "
                "the Work Order's Default Source Warehouse, or a WIP Warehouse)."
            ).format(row.item_code))
        se.append("items", {
            "item_code": row.item_code,
            "qty": consume_qty,
            "s_warehouse": s_wh,
        })

    # Receive the finished good. If it's batch-tracked, pre-create the Batch
    # record first (same pattern the transaction pages use) so Stock Entry's
    # own validation — which requires the Batch to already exist — passes.
    # Leaving batch_no blank lets Batch.autoname generate
    # {Item Code}-{Year}-{Sequence}, and leaving expiry_date blank lets
    # Batch.set_expiry_date_from_shelf_life derive it from Item.shelf_life_in_days.
    fg_row = {"item_code": wo.production_item, "qty": qty_manufactured, "t_warehouse": wo.fg_warehouse}
    if frappe.db.get_value("Item", wo.production_item, "has_batch_no"):
        if not batch_no or not frappe.db.exists("Batch", batch_no):
            new_batch = frappe.get_doc({
                "doctype": "Batch",
                "batch_no": batch_no or None,
                "item": wo.production_item,
                "warehouse": wo.fg_warehouse,
                "manufacturing_date": manufacturing_date or nowdate(),
                "expiry_date": expiry_date or None,
            })
            new_batch.insert(ignore_permissions=True)
            batch_no = new_batch.name
        fg_row["batch_no"] = batch_no
    se.append("items", fg_row)

    # Recoverable scrap/by-products, if any.
    for s in scrap_items:
        s_qty = flt(s.get("qty"))
        if s_qty <= 0 or not s.get("item_code"):
            continue
        se.append("items", {
            "item_code": s["item_code"],
            "qty": s_qty,
            "t_warehouse": wo.scrap_warehouse or wo.fg_warehouse,
        })

    se.insert(ignore_permissions=True)
    se.submit()

    for row in wo.items:
        consume_qty = flt(row.required_qty) * ratio
        if consume_qty > 0:
            row.db_set("consumed_qty", flt(row.consumed_qty) + consume_qty, update_modified=False)

    new_produced_qty = flt(wo.produced_qty) + qty_manufactured
    wo.db_set("produced_qty", new_produced_qty)
    wo.db_set("process_loss_qty", flt(wo.process_loss_qty) + process_loss_qty)
    wo.db_set("status", "Completed" if new_produced_qty >= flt(wo.qty) - 0.0001 else "In Process")
    frappe.db.commit()

    return se.name