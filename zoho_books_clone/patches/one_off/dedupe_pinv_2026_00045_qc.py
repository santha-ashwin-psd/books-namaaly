"""
One-off cleanup: PINV-2026-00045 duplicate QC Inspections.

NOT wired into patches.txt -- this fixes ONE specific document's bad state
left over from the row-identity bug in save_doc (now fixed; see api/docs.py
and quality/qc_engine.py get_or_create_coverage). Run manually, once, via:

    bench --site <site> execute zoho_books_clone.patches.one_off.dedupe_pinv_2026_00045_qc.run

State going in (confirmed via QC Coverage list):
    - QCI-2026-00006  Pass      <- the real, correct inspection
    - QCI-2026-00007  Pending   <- orphaned duplicate, same logical line
    - QCI-2026-00008  Pending   <- orphaned duplicate, same logical line
  Three different QC Coverage.source_row values point at these, one per
  child-row hash name PINV-2026-00045's item row was given on three
  successive (buggy) saves.

What this does:
    1. Reads PINV-2026-00045's CURRENT item rows (post-fix, so the row
       names are now stable) and finds the row matching QCI-2026-00006's
       item_code/batch_no -- that's the real, live row.
    2. Re-points that row's QC Coverage (and quality_inspection field) at
       QCI-2026-00006 using the row's CURRENT name/source_row, so
       get_or_create_coverage finds it on the next submit attempt.
    3. Deletes the two stale QC Coverage rows pointing at 00007/00008.
    4. Cancels QCI-2026-00007 and QCI-2026-00008 (they're drafts --
       docstatus 0 -- so this is delete, not cancel; adjusts either way
       below) so they don't linger as confusing dangling records.
    5. Does NOT submit PINV-2026-00045 -- leaves that as a manual final
       step so you can eyeball the result first.

Safe to re-run: every step checks current state before acting.
"""

import frappe
from frappe import _


PINV_NAME = "PINV-2026-00045"
GOOD_QCI = "QCI-2026-00006"
BAD_QCIS = ["QCI-2026-00007", "QCI-2026-00008"]


def run():
    if not frappe.db.exists("Purchase Invoice", PINV_NAME):
        print(f"{PINV_NAME} not found -- nothing to do.")
        return
    if not frappe.db.exists("QC Inspection", GOOD_QCI):
        print(f"{GOOD_QCI} not found -- aborting, check names before re-running.")
        return

    good_info = frappe.db.get_value(
        "QC Inspection", GOOD_QCI, ["item", "batch_no", "status", "docstatus"], as_dict=True
    )
    if good_info.docstatus != 1 or good_info.status != "Pass":
        print(f"{GOOD_QCI} is not a submitted Pass (docstatus={good_info.docstatus}, "
              f"status={good_info.status}) -- aborting, confirm this is really the keeper.")
        return

    pinv = frappe.get_doc("Purchase Invoice", PINV_NAME)
    matches = [
        row for row in pinv.items
        if row.item_code == good_info.item
        and (row.batch_no or None) == (good_info.batch_no or None)
    ]
    if len(matches) != 1:
        print(f"Expected exactly 1 current row matching {GOOD_QCI}'s item/batch on "
              f"{PINV_NAME}, found {len(matches)}. Aborting -- resolve manually.")
        return

    real_row = matches[0]
    real_source_row = f"{real_row.doctype}:{real_row.name}"
    print(f"Real live row: {real_source_row}")

    # 1. Point the real row's coverage at the good QCI.
    existing_good_coverage = frappe.db.get_value(
        "QC Coverage", {"source_row": real_source_row}, "name"
    )
    if existing_good_coverage:
        frappe.db.set_value("QC Coverage", existing_good_coverage, "qc_inspection", GOOD_QCI)
        print(f"Updated existing QC Coverage {existing_good_coverage} -> {GOOD_QCI}")
    else:
        cov = frappe.new_doc("QC Coverage")
        cov.source_row = real_source_row
        cov.qc_inspection = GOOD_QCI
        cov.insert(ignore_permissions=True)
        print(f"Created QC Coverage {cov.name} ({real_source_row} -> {GOOD_QCI})")

    if hasattr(real_row, "quality_inspection"):
        frappe.db.set_value(real_row.doctype, real_row.name, "quality_inspection", GOOD_QCI,
                             update_modified=False)
        print(f"Stamped {real_row.doctype} {real_row.name}.quality_inspection = {GOOD_QCI}")

    # 2 & 3. Clean up the orphaned duplicates.
    for bad_qci in BAD_QCIS:
        if not frappe.db.exists("QC Inspection", bad_qci):
            print(f"{bad_qci} already gone, skipping.")
            continue

        deleted_coverage = frappe.db.delete("QC Coverage", {"qc_inspection": bad_qci})
        print(f"Deleted {deleted_coverage} QC Coverage row(s) pointing at {bad_qci}")

        bad_docstatus = frappe.db.get_value("QC Inspection", bad_qci, "docstatus")
        if bad_docstatus == 0:
            frappe.delete_doc("QC Inspection", bad_qci, ignore_permissions=True,
                               force=True, delete_permanently=True)
            print(f"Deleted draft {bad_qci}")
        elif bad_docstatus == 1:
            bad_doc = frappe.get_doc("QC Inspection", bad_qci)
            bad_doc.flags.ignore_permissions = True
            bad_doc.cancel()
            print(f"Cancelled submitted {bad_qci}")
        else:
            print(f"{bad_qci} already cancelled (docstatus=2), leaving as-is.")

    frappe.db.commit()
    print(
        f"\nDone. {PINV_NAME} row {real_row.name} now covered by {GOOD_QCI} (Pass). "
        f"Duplicates {BAD_QCIS} cleaned up. Submit {PINV_NAME} through the normal "
        f"flow next -- the QC gate should now see Pass and let it through cleanly."
    )