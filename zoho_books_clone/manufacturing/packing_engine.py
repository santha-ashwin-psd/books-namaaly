"""
Packing Engine — actions related to Packing Slips and Packing BOMs.

create_packing_slip   -- auto-generate a Packing Slip from a submitted Work
                         Order whose BOM is of type 'Packing'. Pre-populates
                         the items list from the Packing BOM's packing_items
                         table and the bulk_item row, scaled to qty_to_pack.
get_packing_slips     -- list Packing Slips linked to a specific Work Order
                         (used by the WorkOrderView to show a linked-doc count).
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate

from zoho_books_clone.utils.access import assert_can


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

    # Bulk item row
    if bom_doc.bulk_item and flt(bom_doc.bulk_qty_per_unit) > 0:
        bulk_uom = frappe.db.get_value("Item", bom_doc.bulk_item, "stock_uom") or ""
        ps.append("items", {
            "item_code": bom_doc.bulk_item,
            "item_name": frappe.db.get_value("Item", bom_doc.bulk_item, "item_name") or bom_doc.bulk_item,
            "required_qty": flt(bom_doc.bulk_qty_per_unit) * ratio,
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
