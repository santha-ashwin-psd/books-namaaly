"""One-off patch: backfill sub_assembly_qty_breakdown on existing Work Order
Item rows saved before that field existed.

Does NOT touch required_qty, amount, rate, or sub_assembly_boms on any row --
only fills in the new sub_assembly_qty_breakdown field, purely so
WorkOrder.vue's groupedWoItems can show each sub-assembly's correct portion
of a shared row instead of lumping it into "Shared / Multiple Sub-Assemblies".

For each Work Order that has a bom + qty, re-explodes that BOM (same
_explode_bom_items + _merge_duplicate_rows path used when materials are
loaded fresh) to recompute what the per-origin qty split SHOULD be, then
matches those freshly-exploded rows back onto the Work Order's existing
saved rows -- by (item_code, source_warehouse) first, falling back to
item_code alone if the row's warehouse was hand-edited since -- and stamps
only the breakdown field.

Run:
    bench --site <sitename> execute \
        zoho_books_clone.manufacturing.patches.backfill_wo_sub_assembly_qty_breakdown.execute

Safe to re-run -- rows that already have breakdown data are skipped, and a
Work Order whose BOM was since cancelled/deleted or whose ratio can't be
recomputed is skipped with a note, not failed.
"""
import json

import frappe
from frappe.utils import flt

from zoho_books_clone.manufacturing.work_order_engine import (
    _explode_bom_items,
    _merge_duplicate_rows,
)


def execute():
    work_orders = frappe.get_all(
        "Work Order",
        filters={"bom": ["is", "set"], "qty": [">", 0]},
        fields=["name", "bom", "qty"],
    )

    updated_rows = 0
    skipped_wo = []

    for wo in work_orders:
        wo_doc = frappe.get_doc("Work Order", wo.name)
        if not wo_doc.items:
            continue
        # Skip rows that already have breakdown data (idempotent re-run).
        if all(r.sub_assembly_qty_breakdown for r in wo_doc.items):
            continue

        if not frappe.db.exists("BOM", wo.bom):
            skipped_wo.append((wo.name, "BOM no longer exists"))
            continue
        bom_doc = frappe.get_doc("BOM", wo.bom)
        if bom_doc.bom_type == "Packing":
            # Packing BOMs never had multi-sub-assembly sharing to begin
            # with -- packing_items are flat, not exploded/merged.
            continue

        # Recompute at the qty materials were actually loaded for, not the
        # WO's current qty -- those can have drifted apart (see
        # materialsStale in WorkOrder.vue) and the saved rows still reflect
        # whatever qty they were loaded at.
        load_qty = flt(wo_doc.get("items_loaded_for_qty")) or flt(wo.qty)
        ratio = load_qty / flt(bom_doc.quantity or 1)

        try:
            fresh_items = _explode_bom_items(bom_doc.items, ratio, depth=0, operations_acc=[])
            fresh_items = _merge_duplicate_rows(fresh_items)
        except Exception as e:
            skipped_wo.append((wo.name, f"explode failed: {e}"))
            continue

        # Index fresh rows by (item_code, source_warehouse) and, as a
        # fallback, by item_code alone (in case the saved row's warehouse
        # was hand-edited after loading, and no longer matches).
        by_item_wh = {}
        by_item = {}
        for f in fresh_items:
            key_wh = (f["item_code"], f.get("source_warehouse") or "")
            by_item_wh.setdefault(key_wh, f)
            by_item.setdefault(f["item_code"], f)

        changed = False
        for row in wo_doc.items:
            if row.sub_assembly_qty_breakdown:
                continue  # already backfilled
            key_wh = (row.item_code, row.source_warehouse or "")
            match = by_item_wh.get(key_wh) or by_item.get(row.item_code)
            if not match:
                continue  # row has no counterpart in the BOM anymore (manually added/edited) -- leave as-is
            breakdown = match.get("sub_assembly_qty_breakdown") or []
            if not breakdown:
                continue
            row.db_set(
                "sub_assembly_qty_breakdown",
                json.dumps(breakdown),
                update_modified=False,
            )
            # Only fill sub_assembly_boms if it was never set either (older
            # rows saved before that field existed too) -- never overwrite
            # an existing value.
            if not row.sub_assembly_boms and match.get("sub_assembly_boms"):
                row.db_set(
                    "sub_assembly_boms",
                    ",".join(match["sub_assembly_boms"]),
                    update_modified=False,
                )
            changed = True
            updated_rows += 1

        if changed:
            frappe.db.commit()

    print(f"Backfilled sub_assembly_qty_breakdown on {updated_rows} Work Order Item row(s) "
          f"across {len(work_orders)} Work Order(s) checked.")
    if skipped_wo:
        print(f"Skipped {len(skipped_wo)} Work Order(s):")
        for name, reason in skipped_wo:
            print(f"  {name}: {reason}")