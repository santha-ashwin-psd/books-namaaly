"""
Bench console script — backfill Delivery Note Item.batch_no from the
linked auto-generated Stock Entry (stock_link.on_delivery_note_submit).

Why this works: pre-fix, Delivery Note Item had no batch_no field, but
the auto Stock Entry it spawned still required one for batch-tracked
items (StockEntry.validate()) — so any DN that submitted successfully
either wasn't batch-tracked, or had its Stock Entry's batch_no fixed
some other way (manual edit). Either way the Stock Entry Detail rows
are the source of truth; this just copies batch_no back onto the DN
Item rows so the new field isn't empty for old data.

Match strategy: for each submitted DN, pull its linked Stock Entry
(reference_doctype="Delivery Note", reference_name=dn.name, docstatus=1)
and its Stock Entry Detail rows. Match DN Item -> SE Detail by
(item_code, warehouse == s_warehouse), in row order, ONE-TO-ONE only —
if an item_code+warehouse combo appears more than once on either side,
skip it and report as ambiguous rather than guess.

Usage (bench console):
    exec(open("backfill_dn_batch_no.py").read())
    run()                # dry run, prints report, writes nothing
    run(commit=True)     # writes batch_no + db_commit
"""

import frappe
from collections import defaultdict


def run(commit=False):
    dn_rows = frappe.db.sql(
        """
        SELECT dni.name, dni.parent, dni.item_code, dni.warehouse
        FROM `tabDelivery Note Item` dni
        INNER JOIN `tabDelivery Note` dn ON dn.name = dni.parent
        WHERE dn.docstatus = 1
          AND (dni.batch_no IS NULL OR dni.batch_no = '')
          AND EXISTS (
              SELECT 1 FROM `tabItem` i
              WHERE i.item_code = dni.item_code AND i.has_batch_no = 1
          )
        """,
        as_dict=True,
    )

    if not dn_rows:
        print("nothing to backfill — no empty batch_no rows on batch-tracked items")
        return

    by_dn = defaultdict(list)
    for r in dn_rows:
        by_dn[r.parent].append(r)

    updated, ambiguous, no_se, no_match = [], [], [], []

    for dn_name, rows in by_dn.items():
        se_name = frappe.db.get_value(
            "Stock Entry",
            {"reference_doctype": "Delivery Note", "reference_name": dn_name, "docstatus": 1},
            "name",
        )
        if not se_name:
            no_se.extend(r.name for r in rows)
            continue

        se_details = frappe.db.sql(
            """
            SELECT item_code, s_warehouse, batch_no
            FROM `tabStock Entry Detail`
            WHERE parent = %s AND batch_no IS NOT NULL AND batch_no != ''
            """,
            se_name,
            as_dict=True,
        )

        # bucket SE rows by (item_code, s_warehouse)
        se_by_key = defaultdict(list)
        for d in se_details:
            se_by_key[(d.item_code, d.s_warehouse)].append(d.batch_no)

        for r in rows:
            key = (r.item_code, r.warehouse)
            candidates = se_by_key.get(key, [])
            if not candidates:
                no_match.append(r.name)
                continue
            if len(set(candidates)) > 1 or len(candidates) > 1:
                ambiguous.append((r.name, se_name, candidates))
                continue
            batch_no = candidates[0]
            updated.append((r.name, batch_no))
            if commit:
                frappe.db.set_value("Delivery Note Item", r.name, "batch_no", batch_no, update_modified=False)

    print(f"matched:    {len(updated)}")
    for name, batch_no in updated:
        print(f"  {name} -> {batch_no}")
    print(f"ambiguous:  {len(ambiguous)} (multiple/conflicting SE rows for same item+warehouse — not touched)")
    for name, se_name, candidates in ambiguous:
        print(f"  {name} (SE {se_name}): {candidates}")
    print(f"no SE found: {len(no_se)}  -> {no_se}")
    print(f"no matching SE row: {len(no_match)}  -> {no_match}")

    if commit:
        frappe.db.commit()
        print(f"\ncommitted {len(updated)} rows")
    else:
        print("\ndry run — nothing written. run(commit=True) to apply")