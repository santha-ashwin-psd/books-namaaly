"""
Patch v1_7: Phase 0 schema back-fill for the QC quarantine-workflow rework.

Two independent, additive back-fills — neither changes existing behavior,
they only fill in columns that are new in this release so later phases
(1-6) have real data to work with instead of NULLs.

1. Books Company.default_fg_quarantine_warehouse
   ---------------------------------------------
   New field, sibling to the existing default_quarantine_warehouse (which
   from this release on is documented as the RM/incoming-goods quarantine
   bin). This app does NOT seed warehouses under any fixed "RM Quarantine"/
   "FG Quarantine" naming convention (see books_setup/install.py — it only
   auto-seeds Stores/Transit/Manufacturing/Scrap, named "{Type}-{company}",
   no abbreviation suffix), so this patch cannot assume a name pattern.
   Instead, for each company with a blank default_fg_quarantine_warehouse:
     a. If default_quarantine_warehouse is already set and a sibling
        warehouse exists for the same company whose name swaps "RM" for
        "FG" (case-insensitive, whatever the site's own naming turns out
        to be), use that.
     b. Otherwise, look for any warehouse belonging to this company whose
        name contains both "FG" and "Quarantine".
     c. If neither matches, leave it blank and just count it — this is a
        genuinely new field with no reliable source of truth to infer from,
        so an unmatched company needs a human to set it once via Books
        Company settings rather than the patch guessing wrong.
   Never overwrites a value someone has already set explicitly.

2. QC Inspection.release_status
   ------------------------------
   New field, default "N/A" — but a JSON `default` only applies to rows
   inserted after the field exists, so every QC Inspection created before
   this patch has NULL here. Left as NULL, `eval:doc.release_status ==
   "Not Released"`-style checks in later phases would silently skip every
   pre-existing record. Back-fill classification, in order (each rule only
   touches rows the previous rule left NULL):
     - qc_hold = 1                              -> "Not Released"
       (still sitting in quarantine right now)
     - qc_hold = 0 AND quarantine_stock_entry set -> "Released"
       (was quarantined at some point and has since come back out, via the
       existing place_on_hold/release_from_hold flow in qc_hold_manager.py)
     - everything else (status was never Fail, or Fail with no quarantine
       Stock Entry ever created) -> "N/A"

target_warehouse is deliberately NOT back-filled here: for a QC Inspection
created before Phase 1/2 exist, there is no reliable way to reconstruct
"the warehouse this row would have landed in had it not been quarantined"
after the fact — the reference document's row may since have been
overwritten by the very routing this rework introduces. It stays blank on
old rows; only Inspections auto-created from Phase 1 onward will have it
stamped at creation time. release_from_hold() already falls back to asking
for a target_warehouse explicitly when one isn't stamped, so this is safe.
"""
import frappe


def execute():
    _backfill_fg_quarantine_warehouse()
    _backfill_release_status()


def _backfill_fg_quarantine_warehouse():
    if not frappe.db.exists("DocType", "Books Company"):
        return
    if not frappe.db.has_column("Books Company", "default_fg_quarantine_warehouse"):
        return  # schema sync for this column hasn't landed yet — shouldn't
                 # happen from [post_model_sync], but cheap insurance if this
                 # is ever invoked manually out of normal migrate order.

    companies = frappe.db.get_all(
        "Books Company",
        filters={"default_fg_quarantine_warehouse": ["in", ["", None]]},
        fields=["name", "default_quarantine_warehouse"],
    )

    updated = 0
    unmatched = []
    for c in companies:
        candidate = None

        # (a) Derive from the existing RM quarantine warehouse's own name,
        # if one is configured and follows an RM/FG naming pair.
        if c.default_quarantine_warehouse and "rm" in c.default_quarantine_warehouse.lower():
            import re
            maybe = re.sub("rm", "FG", c.default_quarantine_warehouse, count=1, flags=re.IGNORECASE)
            if maybe != c.default_quarantine_warehouse and frappe.db.exists("Warehouse", maybe):
                candidate = maybe

        # (b) Fall back to searching this company's own warehouses for
        # anything that looks like an FG quarantine bin.
        if not candidate:
            candidate = frappe.db.get_value(
                "Warehouse",
                {
                    "company": c.name,
                    "warehouse_name": ["like", "%FG%"],
                    "disabled": 0,
                },
                "name",
            )
            if candidate and "quarantine" not in candidate.lower():
                candidate = None  # matched an FG warehouse, but not a quarantine one — don't guess

        if candidate:
            frappe.db.set_value(
                "Books Company", c.name, "default_fg_quarantine_warehouse",
                candidate, update_modified=False,
            )
            updated += 1
        else:
            unmatched.append(c.name)

    if updated:
        frappe.db.commit()
    print(f"✅  v1_7: default_fg_quarantine_warehouse back-filled for {updated} compan{'y' if updated == 1 else 'ies'}.")
    if unmatched:
        print(
            "⚠️  v1_7: could not auto-match an FG quarantine warehouse for: "
            + ", ".join(unmatched)
            + " — set 'Default Quarantine Warehouse (Finished Goods)' manually on these "
              "Books Company records (falls back to the RM one until then)."
        )


def _backfill_release_status():
    if not frappe.db.exists("DocType", "QC Inspection"):
        return
    if not frappe.db.has_column("QC Inspection", "release_status"):
        return
    if not frappe.db.has_column("QC Inspection", "qc_hold"):
        return

    # Still in quarantine right now.
    frappe.db.sql(
        """
        UPDATE `tabQC Inspection`
        SET release_status = 'Not Released'
        WHERE qc_hold = 1 AND (release_status IS NULL OR release_status = '')
        """
    )

    # Was quarantined at some point (has a quarantine Stock Entry on record)
    # and is no longer on hold -- i.e. already released via the existing
    # place_on_hold/release_from_hold flow before this field existed.
    if frappe.db.has_column("QC Inspection", "quarantine_stock_entry"):
        frappe.db.sql(
            """
            UPDATE `tabQC Inspection`
            SET release_status = 'Released'
            WHERE qc_hold = 0
              AND quarantine_stock_entry IS NOT NULL
              AND quarantine_stock_entry != ''
              AND (release_status IS NULL OR release_status = '')
            """
        )

    # Everything else never touched quarantine at all.
    frappe.db.sql(
        """
        UPDATE `tabQC Inspection`
        SET release_status = 'N/A'
        WHERE release_status IS NULL OR release_status = ''
        """
    )

    frappe.db.commit()
    print("✅  v1_7: QC Inspection.release_status back-filled for existing records.")