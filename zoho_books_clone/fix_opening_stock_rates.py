"""
One-off data fix: backfill basic_rate on submitted "Opening Stock" Stock Entry
rows that were imported with rate = 0, using the Item's standard_rate as the
default.

Why a script and not just editing the form:
  - The entries are already submitted, so the UI won't let you edit basic_rate.
  - Even if it did, Stock Ledger Entry / Bin were already written with rate 0
    at submit time — editing the child row alone wouldn't fix those.

Why this is safe for "Opening Stock" specifically:
  - StockEntry._post_gl_entries() explicitly skips GL posting for the
    "Opening Stock" type (see stock_entry.py on_submit -> _post_gl_entries),
    so there are NO GL Entries to reconcile here — only Stock Ledger Entry,
    Bin, and Batch records.

IMPORTANT CAVEAT — read before running:
  This script overwrites Bin.valuation_rate directly. That is only correct if
  these Opening Stock entries are the FIRST stock movement for that
  item+warehouse (the normal case for go-live opening balances). If any of
  these items have already had a later Material Issue / Transfer / Manufacture
  that drew down stock using the old (zero) valuation rate, those downstream
  transactions were also mis-valued and this script will NOT fix them — you'd
  need a full valuation recompute for that item. For a fresh go-live import,
  this is very unlikely, but check first if you're not sure:

      frappe.get_all("Stock Ledger Entry",
          filters={"item_code": item_code, "creation": [">", "<opening import timestamp>"]})

HOW TO RUN:
  bench --site <your-site> execute zoho_books_clone.fix_opening_stock_rates.run

  (Copy this file into the app first, e.g. zoho_books_clone/zoho_books_clone/,
  or run the body directly in `bench --site <site> console`.)

  Dry run first (no writes) by calling run(dry_run=True) — it will print what
  it *would* change without touching the DB.
"""

import frappe
from frappe.utils import flt


def run(dry_run=False, stock_entry_type="Opening Stock"):
    entries = frappe.get_all(
        "Stock Entry",
        filters={"stock_entry_type": stock_entry_type, "docstatus": 1},
        pluck="name",
    )

    fixed_entries = 0
    fixed_rows = 0
    skipped_no_rate = []

    for name in entries:
        se = frappe.get_doc("Stock Entry", name)
        entry_changed = False

        for row in se.items:
            if flt(row.basic_rate):
                continue  # already has a rate, leave it alone

            rate = flt(frappe.db.get_value("Item", row.item_code, "standard_rate"))
            if not rate:
                skipped_no_rate.append((name, row.item_code))
                continue

            new_amount = round(flt(row.qty) * rate, 2)

            print(f"{name} / {row.item_code}: basic_rate 0 -> {rate}, amount -> {new_amount}"
                  + (" (dry run)" if dry_run else ""))

            if dry_run:
                entry_changed = True
                fixed_rows += 1
                continue

            # 1. Stock Entry Detail row itself
            frappe.db.set_value("Stock Entry Detail", row.name, {
                "basic_rate": rate,
                "amount": new_amount,
            }, update_modified=False)
            # Keep the in-memory row in sync too — the parent total below is
            # computed from se.items, and frappe.db.set_value() only touches
            # the DB, not this object. Without this line the row displays
            # correctly (it reads fresh from DB) but total_incoming_value
            # gets recomputed from the STALE in-memory rate=0 and stays 0.
            row.basic_rate = rate
            row.amount = new_amount

            # 2. Matching Stock Ledger Entry/entries for this row's incoming leg
            #    (Opening Stock only ever has a target warehouse leg — see
            #    SE_TYPE_DIRECTION in stock_entry.py).
            sles = frappe.get_all(
                "Stock Ledger Entry",
                filters={
                    "voucher_type": "Stock Entry",
                    "voucher_no": name,
                    "item_code": row.item_code,
                    "warehouse": row.t_warehouse,
                    "batch_no": row.batch_no or "",
                    "is_cancelled": 0,
                },
                fields=["name", "actual_qty", "qty_after_transaction"],
            )
            for sle in sles:
                new_stock_value = round(flt(sle.qty_after_transaction) * rate, 2)
                frappe.db.set_value("Stock Ledger Entry", sle.name, {
                    "incoming_rate": rate,
                    "valuation_rate": rate,
                    "stock_value": new_stock_value,
                    "stock_value_difference": round(flt(sle.actual_qty) * rate, 2),
                }, update_modified=False)

            # 3. Bin valuation — see the caveat in the module docstring above.
            bin_name = frappe.db.get_value(
                "Bin", {"item_code": row.item_code, "warehouse": row.t_warehouse}
            )
            if bin_name:
                bin_qty = flt(frappe.db.get_value("Bin", bin_name, "actual_qty"))
                frappe.db.set_value("Bin", bin_name, {
                    "valuation_rate": rate,
                    "stock_value": round(bin_qty * rate, 2),
                }, update_modified=False)

            # Note: this schema's Batch doctype has no rate/valuation field of
            # its own (only batch_qty), so there's nothing to fix there.

            entry_changed = True
            fixed_rows += 1

        if entry_changed and not dry_run:
            total_incoming = round(sum(flt(r.qty) * flt(r.basic_rate) for r in se.items), 2)
            frappe.db.set_value("Stock Entry", name, {
                "total_incoming_value": total_incoming,
                "value_difference": total_incoming,
            }, update_modified=False)
            fixed_entries += 1
        elif entry_changed:
            fixed_entries += 1

    if not dry_run:
        frappe.db.commit()

    print(f"\n{'Would fix' if dry_run else 'Fixed'} {fixed_rows} row(s) across {fixed_entries} entry(ies).")
    if skipped_no_rate:
        print(f"Skipped {len(skipped_no_rate)} row(s) with no standard_rate on the Item — set those manually:")
        for n, item in skipped_no_rate:
            print(f"  {n}: {item}")


def resync_totals(dry_run=False, stock_entry_type="Opening Stock"):
    """
    Recompute total_incoming_value / value_difference for every submitted
    entry of the given type from its CURRENT item rows, regardless of
    whether the rows themselves needed fixing.

    Run this if run() was already executed once with the old version of this
    script (the one that summed the stale in-memory basic_rate instead of the
    corrected value) — those entries now have correct item rows in the DB but
    a parent total that's still stuck at 0. run()'s "skip if basic_rate is
    already set" check means simply re-running run() won't touch them, since
    the row-level rate is no longer 0 — this function fixes the total
    directly instead, independent of that check.
    """
    entries = frappe.get_all(
        "Stock Entry",
        filters={"stock_entry_type": stock_entry_type, "docstatus": 1},
        fields=["name", "total_incoming_value"],
    )
    fixed = 0
    for e in entries:
        rows = frappe.get_all(
            "Stock Entry Detail", filters={"parent": e.name}, fields=["qty", "basic_rate"]
        )
        correct_total = round(sum(flt(r.qty) * flt(r.basic_rate) for r in rows), 2)
        if abs(correct_total - flt(e.total_incoming_value)) < 0.005:
            continue  # already correct, nothing to do

        print(f"{e.name}: total_incoming_value {e.total_incoming_value} -> {correct_total}"
              + (" (dry run)" if dry_run else ""))
        if not dry_run:
            frappe.db.set_value("Stock Entry", e.name, {
                "total_incoming_value": correct_total,
                "value_difference": correct_total,
            }, update_modified=False)
        fixed += 1

    if not dry_run:
        frappe.db.commit()
    print(f"\n{'Would resync' if dry_run else 'Resynced'} totals on {fixed} entry(ies).")