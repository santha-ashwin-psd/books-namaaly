"""
Packing Engine — actions related to Packing Slips and Packing BOMs.

create_packing_slip       -- auto-generate a Packing Slip from a submitted
                             Work Order whose BOM is of type 'Packing'.
                             Pre-populates the items list from the Packing
                             BOM's packing_items table and the bulk_item row,
                             scaled to qty_to_pack.
get_packing_slips          -- list Packing Slips linked to a specific Work
                             Order (used by the WorkOrderView to show a
                             linked-doc count).
post_packing_consumption   -- the Manufacture Stock Entry for a fully-packed
                             Packing Slip: consumes the bulk item + packing
                             materials from source_warehouse and receives the
                             packed item (batch-aware, same shelf-life/
                             autoname pattern as Work Order completion) into
                             target_warehouse. Without this, a Packing Slip
                             only tracked packed_qty on paper and never
                             touched the stock ledger.
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate

from zoho_books_clone.utils.access import assert_can
from zoho_books_clone.utils.tenancy import assert_doc_in_user_company
from zoho_books_clone.inventory.utils import get_valuation_rate


@frappe.whitelist(allow_guest=False, methods=["POST"])
def create_packing_slip(work_order, qty_to_pack=None):
    """Create a Draft Packing Slip for the given Work Order.

    The Work Order must be submitted and its BOM must be of type 'Packing'.
    qty_to_pack defaults to the remaining unfinished quantity on the WO.

    Returns the new Packing Slip name.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Packing Slip", "write")

    wo = frappe.get_doc("Work Order", work_order)
    if wo.docstatus != 1:
        frappe.throw(_("Work Order must be submitted before creating a Packing Slip."))

    bom_type = frappe.db.get_value("BOM", wo.bom, "bom_type")
    if bom_type != "Packing":
        frappe.throw(_(
            "Work Order {0} uses a {1} BOM. Packing Slips can only be created "
            "for Work Orders with a Packing BOM."
        ).format(wo.name, bom_type or "Manufacturing"))

    bom_doc = frappe.get_doc("BOM", wo.bom)
    qty_to_pack = flt(qty_to_pack) or (flt(wo.qty) - flt(wo.produced_qty))
    if qty_to_pack <= 0:
        frappe.throw(_("Work Order {0} is already fully completed.").format(wo.name))

    ratio = qty_to_pack / flt(bom_doc.quantity or 1)

    ps = frappe.new_doc("Packing Slip")
    ps.work_order = wo.name
    ps.production_item = wo.production_item
    ps.bom = wo.bom
    ps.qty_to_pack = qty_to_pack
    ps.packing_date = nowdate()
    ps.status = "Draft"

    # Bulk item row. Scales directly with qty_to_pack (bulk_qty_per_unit is
    # defined as "per packed unit"), NOT with `ratio` (qty_to_pack /
    # bom.quantity) -- ratio is only correct for packing_items, whose qty is
    # defined per the BOM's own batch quantity. Using ratio for the bulk
    # item would silently divide its consumption by bom.quantity for any
    # Packing BOM whose Quantity field isn't exactly 1.
    if bom_doc.bulk_item and flt(bom_doc.bulk_qty_per_unit) > 0:
        bulk_uom = frappe.db.get_value("Item", bom_doc.bulk_item, "stock_uom") or ""
        ps.append("items", {
            "item_code": bom_doc.bulk_item,
            "item_name": frappe.db.get_value("Item", bom_doc.bulk_item, "item_name") or bom_doc.bulk_item,
            "required_qty": flt(bom_doc.bulk_qty_per_unit) * qty_to_pack,
            "packed_qty": 0,
            "uom": bulk_uom,
        })

    # Packing materials
    for r in (bom_doc.packing_items or []):
        ps.append("items", {
            "item_code": r.item_code,
            "item_name": r.item_name or "",
            "required_qty": flt(r.qty) * ratio,
            "packed_qty": 0,
            "uom": r.uom or "",
        })

    if not ps.items:
        frappe.throw(_("Packing BOM {0} has no items — add packing materials first.").format(wo.bom))

    ps.insert(ignore_permissions=True)
    frappe.db.commit()

    return ps.name


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_packing_slips(work_order):
    """Return a summary list of Packing Slips for the given Work Order."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    return frappe.get_all(
        "Packing Slip",
        filters={"work_order": work_order},
        fields=["name", "status", "packing_date", "qty_to_pack", "packed_by"],
        order_by="creation desc",
        limit=50,
    )


@frappe.whitelist(allow_guest=False, methods=["POST"])
def post_packing_consumption(packing_slip, batch_no=None, manufacturing_date=None, expiry_date=None):
    """Post the Manufacture Stock Entry for a fully-packed Packing Slip.

    Consumes every item row's packed_qty from source_warehouse (the bulk
    item and packing materials — bottles, caps, labels, cartons) and
    receives qty_to_pack of the packed item into target_warehouse. This is
    the step that was previously missing: without it, packed_qty/status
    only recorded progress on the Packing Slip itself and never moved
    anything in the stock ledger, so packing material stock never actually
    went down.

    Can only be called once per Packing Slip — the resulting Stock Entry
    name is written back to `stock_entry`, and packing_slip.py's validate()
    locks the document (like Cancelled) once that field is set, so this
    can't silently double-post.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Stock Entry", "write")

    ps = frappe.get_doc("Packing Slip", packing_slip)
    assert_doc_in_user_company(ps)

    if ps.status == "Cancelled":
        frappe.throw(_("This Packing Slip is cancelled."))
    if ps.stock_entry:
        frappe.throw(_("Stock has already been posted for this Packing Slip ({0}).").format(ps.stock_entry))
    if ps.status != "Packed":
        frappe.throw(_("Mark the Packing Slip as fully Packed before posting stock consumption."))
    if not ps.items:
        frappe.throw(_("Packing Slip has no items to consume."))
    if not ps.source_warehouse:
        frappe.throw(_("Set 'Consume Materials From' warehouse before posting."))

    target_warehouse = ps.target_warehouse
    if not target_warehouse and ps.work_order:
        target_warehouse = frappe.db.get_value("Work Order", ps.work_order, "fg_warehouse")
    if not target_warehouse:
        frappe.throw(_(
            "Set 'Receive Packed Goods At' warehouse before posting "
            "(or link a Work Order with an FG Warehouse)."
        ))

    se = frappe.new_doc("Stock Entry")
    se.company = ps.company
    se.stock_entry_type = "Manufacture"
    se.posting_date = nowdate()
    se.work_order = ps.work_order or ""
    se.remarks = f"Packing consumption for Packing Slip {ps.name}"

    # Consume the bulk item + every packing material by its actual
    # packed_qty (not required_qty) -- a run that under- or over-consumed a
    # material relative to the plan should post what was really used, same
    # principle as Work Order completion using consume_qty rather than
    # required_qty.
    total_consumed_cost = 0.0
    any_consumed = False
    for row in ps.items:
        qty = flt(row.packed_qty)
        if qty <= 0:
            continue
        any_consumed = True
        rm_rate = get_valuation_rate(row.item_code, ps.source_warehouse)
        total_consumed_cost += qty * rm_rate
        item_row = {
            "item_code": row.item_code,
            "qty": qty,
            "s_warehouse": ps.source_warehouse,
            "basic_rate": rm_rate,
        }
        if row.batch_no:
            item_row["batch_no"] = row.batch_no
        se.append("items", item_row)

    if not any_consumed:
        frappe.throw(_("No items have a Packed Qty greater than zero."))

    # Receive the packed item. Batch-tracked items get a Batch pre-created
    # first (same pattern as Work Order completion) so Stock Entry's own
    # validation, which requires the Batch to already exist, passes.
    # Leaving batch_no blank lets Batch.autoname generate
    # {Item Code}-{Year}-{Sequence}, and leaving expiry_date blank lets
    # Batch.set_expiry_date_from_shelf_life derive it from shelf_life_in_days.
    qty_to_pack = flt(ps.qty_to_pack)
    if qty_to_pack <= 0:
        frappe.throw(_("Qty to Pack must be greater than zero."))
    fg_unit_rate = total_consumed_cost / qty_to_pack if qty_to_pack else 0.0

    fg_row = {
        "item_code": ps.production_item,
        "qty": qty_to_pack,
        "t_warehouse": target_warehouse,
        "basic_rate": fg_unit_rate,
    }
    if frappe.db.get_value("Item", ps.production_item, "has_batch_no"):
        if not batch_no or not frappe.db.exists("Batch", batch_no):
            new_batch = frappe.get_doc({
                "doctype": "Batch",
                "batch_no": batch_no or None,
                "item": ps.production_item,
                "warehouse": target_warehouse,
                "manufacturing_date": manufacturing_date or nowdate(),
                "expiry_date": expiry_date or None,
            })
            new_batch.insert(ignore_permissions=True)
            batch_no = new_batch.name
        fg_row["batch_no"] = batch_no
    se.append("items", fg_row)

    se.insert(ignore_permissions=True)
    se.submit()

    ps.db_set("stock_entry", se.name)
    ps.db_set("target_warehouse", target_warehouse)
    if batch_no:
        ps.db_set("posted_batch_no", batch_no)
    frappe.db.commit()

    return se.name
@frappe.whitelist(allow_guest=False, methods=["POST"])
def reverse_packing_consumption(packing_slip):
    """Undo the Manufacture Stock Entry posted by post_packing_consumption():
    cancels that Stock Entry (reversing the bulk/packing-material
    consumption and the packed-item receipt) and clears the Packing Slip's
    stock_entry/target_warehouse/posted_batch_no so it's unlocked and can
    be corrected or reposted.

    packed_qty and status on the slip's item rows are left untouched --
    they describe physical packing progress, which reversing the stock
    posting doesn't undo.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Stock Entry", "cancel")

    ps = frappe.get_doc("Packing Slip", packing_slip)
    assert_doc_in_user_company(ps)

    if ps.status == "Cancelled":
        frappe.throw(_("This Packing Slip is cancelled."))
    if not ps.stock_entry:
        frappe.throw(_("No stock has been posted for this Packing Slip yet."))

    se = frappe.get_doc("Stock Entry", ps.stock_entry)
    if se.docstatus != 1:
        frappe.throw(_("Linked Stock Entry {0} is not submitted.").format(se.name))

    se.flags.ignore_manufacturing_guard = True
    se.cancel()

    ps.db_set("stock_entry", "")
    ps.db_set("target_warehouse", "")
    ps.db_set("posted_batch_no", "")

    frappe.db.commit()
    return "Reversed"