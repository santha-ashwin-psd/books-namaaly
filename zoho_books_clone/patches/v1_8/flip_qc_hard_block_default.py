"""
Patch v1_8: Phase 4 of the QC quarantine-workflow rework -- flips
Books Company.qc_hard_block to on (1) by default.

qc_hard_block already existed before this rework (default "0" -- soft-warn:
a dismissible confirm dialog on QC-flagged submit). Phase 4 changes the
field's own JSON default to "1" for newly created companies, but a JSON
`default` only applies to rows inserted after the change -- every existing
Books Company record already has an explicit 0 stored, which a schema
default can never retroactively touch. Without this patch, every
pre-existing company would silently stay in soft-warn mode forever, which
defeats the point of "flip to hard-block by default".

This back-fill only touches companies still sitting on the OLD default (0)
-- if a company was ever explicitly turned on (1), it's already there and
untouched; there is no way to distinguish "explicitly set to 0" from "never
touched, still at the old default" after the fact, so -- consistent with
how this app's other Phase 0/4 back-fills treat unset booleans -- every
0/NULL is treated as "still at the old default" and moved to the new one.
Sites that deliberately want soft-warn for a given company can simply
uncheck it again afterwards; it's a one-click setting, not a data migration.
"""
import frappe


def execute():
    if not frappe.db.exists("DocType", "Books Company"):
        return
    if not frappe.db.has_column("Books Company", "qc_hard_block"):
        return  # schema sync for this column hasn't landed yet

    companies = frappe.db.get_all(
        "Books Company",
        filters={"qc_hard_block": ["in", [0, None]]},
        fields=["name"],
    )
    if not companies:
        print("✅  v1_8: no companies needed qc_hard_block flipped -- all already on.")
        return

    frappe.db.sql(
        """
        UPDATE `tabBooks Company`
        SET qc_hard_block = 1
        WHERE qc_hard_block = 0 OR qc_hard_block IS NULL
        """
    )
    frappe.db.commit()

    names = ", ".join(c.name for c in companies)
    print(
        f"✅  v1_8: qc_hard_block flipped to on (1) for {len(companies)} "
        f"compan{'y' if len(companies) == 1 else 'ies'}: {names}. "
        f"QC-flagged submits are now hard-blocked by default for these -- "
        f"uncheck 'Hard Block on QC Failure' on a given Books Company to "
        f"restore the old soft-warn behaviour there."
    )