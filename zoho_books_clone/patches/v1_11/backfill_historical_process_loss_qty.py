"""
Patch v1_11: back-fill Stock Entry.process_loss_qty for Manufacture entries
created before that field existed on the Stock Entry doctype.

Background
----------
complete_work_order() used to record process loss ONLY on the Work Order
(wo.process_loss_qty += process_loss_qty). The per-entry
Stock Entry.process_loss_qty field was added later specifically so
reverse_manufacture_entry() could roll back exactly the amount each
individual completion contributed. Every Manufacture Stock Entry created
before that field existed defaults to process_loss_qty = 0, even though
some of them genuinely carried process loss at the time.

If one of those pre-existing entries is ever reversed, the rollback in
reverse_manufacture_entry() reads se.process_loss_qty = 0 and subtracts
nothing, leaving wo.process_loss_qty permanently inflated by whatever that
entry actually lost. That stale total then wrongly feeds the
over-consumption guard and the loss-reconciliation is_final check in
complete_work_order() for every future completion of that Work Order.

Heuristic
---------
There is no way to recover, per historical entry, exactly how much loss
each one carried -- the amount was only ever summed onto the Work Order.
The best available attribution: process loss is overwhelmingly reconciled
on the FINAL Manufacture entry for a Work Order (that's the entry that
closes the batch and explains the shortfall between produced_qty and
planned qty). So for every submitted Work Order that currently shows
process_loss_qty > 0 but whose Manufacture Stock Entries all show
process_loss_qty = 0 (i.e. entirely pre-migration), attribute the Work
Order's full historical process_loss_qty to its chronologically LAST
submitted Manufacture Stock Entry.

This is a best-effort backfill, not a perfect reconstruction. It fixes the
common case (loss recorded once, at batch close) so a reversal of that
final entry now correctly rolls back the Work Order's process_loss_qty.
It will under-attribute in the rarer case where a Work Order had process
loss recorded across MULTIPLE pre-migration entries (mid-run losses on
non-final completions) -- those still can't be individually recovered.
reverse_manufacture_entry() carries a defensive frappe.msgprint for that
remaining edge case (see that function) rather than silently understating
the rollback.

Idempotent: only touches Stock Entries that still show process_loss_qty
in (0, None) -- once a value is backfilled (or genuinely recorded going
forward), re-running this patch is a no-op for that row.
"""
import frappe
from frappe.utils import flt


def execute():
    if not frappe.db.exists("DocType", "Work Order"):
        return
    if not frappe.db.has_column("Stock Entry", "process_loss_qty"):
        return

    work_orders = frappe.get_all(
        "Work Order",
        filters={"docstatus": 1, "process_loss_qty": [">", 0]},
        fields=["name", "process_loss_qty"],
    )

    updated = 0
    for wo in work_orders:
        entries = frappe.get_all(
            "Stock Entry",
            filters={
                "work_order": wo.name,
                "stock_entry_type": "Manufacture",
                "docstatus": 1,
            },
            fields=["name", "process_loss_qty", "creation"],
            order_by="creation asc",
        )
        if not entries:
            continue

        # If any entry already carries a non-zero process_loss_qty, this
        # Work Order isn't purely pre-migration -- leave it alone rather
        # than risk double-counting on top of a genuinely-recorded value.
        if any(flt(e.process_loss_qty) > 0 for e in entries):
            continue

        last_entry = entries[-1]
        frappe.db.set_value(
            "Stock Entry", last_entry.name, "process_loss_qty", flt(wo.process_loss_qty)
        )
        updated += 1

    if updated:
        frappe.db.commit()
        frappe.logger().info(
            f"[v1_11 backfill_historical_process_loss_qty] "
            f"back-filled process_loss_qty on the final Manufacture entry "
            f"for {updated} Work Order(s)."
        )