"""
BOM Engine — advanced read-only APIs for Bill of Materials analysis.

get_bom_tree       -- multi-level indented explosion of a BOM into a flat list
                      of nodes with a ``level`` field for indenting in the UI.
compare_boms       -- side-by-side diff of raw materials and operations between
                      two BOMs — highlights added, removed, and changed rows.
get_alternative_items
                   -- list Alternative Item substitutions defined for an item.
"""

import frappe
from frappe import _
from frappe.utils import flt

from zoho_books_clone.utils.access import assert_can


# ─── BOM Tree ────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_bom_tree(bom, qty=1):
    """Return a flat list of BOM nodes with ``level`` numbers for rendering an
    indented multi-level explosion tree.

    Each node:
        level            -- 0 = direct child of top BOM, 1 = child of sub-assembly, …
        item_code
        item_name
        qty              -- actual quantity needed at this path (scaled)
        uom
        rate             -- unit price from BOM row
        amount           -- qty × rate
        sub_assembly_bom -- linked sub-assembly BOM name, if any
        is_phantom       -- True if the sub-assembly BOM is marked phantom
        has_sub_assembly -- True if this row has a sub-assembly BOM
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("BOM", "read")

    result = []
    _build_tree(bom, flt(qty) or 1.0, level=0, result=result, seen=frozenset())
    return result


def _build_tree(bom_name, qty, level, result, seen, max_depth=6):
    if level > max_depth or bom_name in seen:
        return
    seen = seen | {bom_name}

    try:
        bom_doc = frappe.get_doc("BOM", bom_name)
    except frappe.DoesNotExistError:
        return
    if bom_doc.docstatus != 1:
        return

    ratio = qty / flt(bom_doc.quantity or 1)
    source_rows = bom_doc.packing_items if bom_doc.bom_type == "Packing" else (bom_doc.items or [])

    for r in source_rows:
        sub_bom = r.sub_assembly_bom or ""
        is_phantom = False

        # Auto-detect phantom sub-assembly even without explicit linkage
        if not sub_bom:
            sub_bom = frappe.db.get_value(
                "BOM",
                {"item": r.item_code, "is_phantom_bom": 1, "docstatus": 1, "is_active": 1},
                "name",
            ) or ""
            if sub_bom:
                is_phantom = True

        node_qty = flt(r.qty) * ratio
        node = {
            "level": level,
            "item_code": r.item_code,
            "item_name": r.item_name or frappe.db.get_value("Item", r.item_code, "item_name") or r.item_code,
            "qty": node_qty,
            "uom": r.uom or "",
            "rate": flt(r.rate),
            "amount": flt(r.rate) * node_qty,
            "sub_assembly_bom": sub_bom,
            "is_phantom": is_phantom,
            "has_sub_assembly": bool(sub_bom),
        }
        result.append(node)

        if sub_bom and sub_bom not in seen:
            _build_tree(sub_bom, node_qty, level + 1, result, seen, max_depth)


# ─── BOM Comparison ──────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def compare_boms(bom1, bom2):
    """Return a structured side-by-side diff between two BOMs.

    Returns:
        {
          bom1: { name, item, qty, total_cost, bom_type },
          bom2: { … },
          materials: [ { item_code, item_name, bom1_qty, bom1_uom, bom1_rate,
                         bom2_qty, bom2_uom, bom2_rate, status } ],
          operations: [ { operation, bom1_time, bom1_rate,
                          bom2_time, bom2_rate, status } ],
        }

    ``status`` for each row is one of: "unchanged" | "changed" | "added" | "removed"
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("BOM", "read")

    if bom1 == bom2:
        frappe.throw(_("Select two different BOMs to compare."))

    b1 = frappe.get_doc("BOM", bom1)
    b2 = frappe.get_doc("BOM", bom2)

    def _items_map(bom_doc):
        rows = bom_doc.packing_items if bom_doc.bom_type == "Packing" else (bom_doc.items or [])
        return {
            r.item_code: {
                "item_code": r.item_code,
                "item_name": r.item_name or r.item_code,
                "qty": flt(r.qty),
                "uom": r.uom or "",
                "rate": flt(r.rate),
            }
            for r in rows
        }

    m1, m2 = _items_map(b1), _items_map(b2)
    all_items = sorted(set(m1) | set(m2))
    materials = []
    for ic in all_items:
        r1, r2 = m1.get(ic), m2.get(ic)
        if r1 and r2:
            status = "unchanged" if (r1["qty"] == r2["qty"] and r1["rate"] == r2["rate"]) else "changed"
        elif r1:
            status = "removed"
        else:
            status = "added"
        materials.append({
            "item_code": ic,
            "item_name": (r1 or r2)["item_name"],
            "bom1_qty": r1["qty"] if r1 else None,
            "bom1_uom": r1["uom"] if r1 else "",
            "bom1_rate": r1["rate"] if r1 else None,
            "bom2_qty": r2["qty"] if r2 else None,
            "bom2_uom": r2["uom"] if r2 else "",
            "bom2_rate": r2["rate"] if r2 else None,
            "status": status,
        })

    ops1 = {r.operation: {"time": flt(r.time_in_mins), "rate": flt(r.hour_rate)} for r in b1.operations}
    ops2 = {r.operation: {"time": flt(r.time_in_mins), "rate": flt(r.hour_rate)} for r in b2.operations}
    all_ops = sorted(set(ops1) | set(ops2))
    operations = []
    for op in all_ops:
        o1, o2 = ops1.get(op), ops2.get(op)
        if o1 and o2:
            status = "unchanged" if (o1["time"] == o2["time"] and o1["rate"] == o2["rate"]) else "changed"
        elif o1:
            status = "removed"
        else:
            status = "added"
        operations.append({
            "operation": op,
            "bom1_time": o1["time"] if o1 else None,
            "bom1_rate": o1["rate"] if o1 else None,
            "bom2_time": o2["time"] if o2 else None,
            "bom2_rate": o2["rate"] if o2 else None,
            "status": status,
        })

    return {
        "bom1": {
            "name": b1.name, "item": b1.item, "qty": b1.quantity,
            "total_cost": flt(b1.total_cost), "bom_type": b1.bom_type,
        },
        "bom2": {
            "name": b2.name, "item": b2.item, "qty": b2.quantity,
            "total_cost": flt(b2.total_cost), "bom_type": b2.bom_type,
        },
        "materials": materials,
        "operations": operations,
    }


# ─── Alternative Items ───────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_alternative_items(item_code):
    """Return all Alternative Item substitutions defined for the given item."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    if not frappe.db.exists("DocType", "Alternative Item"):
        return []

    return frappe.get_all(
        "Alternative Item",
        filters={"item_code": item_code},
        fields=["alternative_item_code", "conversion_factor", "uom", "is_default", "description"],
        order_by="is_default desc, alternative_item_code asc",
    )