"""
Patch v1_15: Phase 3 schema back-fill for the Scrap Reuse feature.

Three new columns land with this release:

  * Work Order Item.is_scrap_row       -- marks a row as the scrap-sourced
                                           split created by
                                           apply_partial_scrap_substitution().
                                           Defaults to 0; every row that
                                           predates this column is, by
                                           definition, not one of these
                                           (the function didn't exist yet),
                                           so 0 is not just the schema
                                           default but the factually correct
                                           value here too.
  * Work Order Item.scrap_reused_qty   -- cumulative original-UOM qty this
                                           row has had displaced onto a
                                           scrap sibling. No pre-existing row
                                           has ever gone through that path
                                           either, so this is correctly 0
                                           for all of them.
  * Material Substitution Log.substitution_type
                                        -- "Full Swap" / "Scrap Reuse".
                                           Every log row created before this
                                           release came from the whole-row
                                           apply_row_substitution() path --
                                           apply_partial_scrap_substitution()
                                           and its "Scrap Reuse" logs are
                                           new in this release -- so every
                                           existing log is unambiguously
                                           "Full Swap".

substitution_group (Work Order Item) is deliberately left NULL/blank rather
than back-filled to each row's own name: it's a positive signal that a row
has a scrap-split sibling, and no pre-existing row does. Leaving it blank
keeps that signal meaningful; apply_partial_scrap_substitution() sets it
correctly the first time it actually splits a row, going forward.

Runs after schema sync creates the columns (post_model_sync). Safe to
re-run -- every UPDATE is scoped to rows still on NULL/unset.
"""
import frappe


def execute():
    _backfill_work_order_item()
    _backfill_material_substitution_log()


def _backfill_work_order_item():
    if not frappe.db.has_column("Work Order Item", "is_scrap_row"):
        return  # schema sync for this column hasn't landed yet

    updated = frappe.db.sql("""
        UPDATE `tabWork Order Item`
        SET is_scrap_row = 0, scrap_reused_qty = 0
        WHERE is_scrap_row IS NULL OR scrap_reused_qty IS NULL
    """)
    frappe.db.commit()
    print(f"✅  v1_15: Work Order Item.is_scrap_row/scrap_reused_qty back-filled.")


def _backfill_material_substitution_log():
    if not frappe.db.exists("DocType", "Material Substitution Log"):
        return
    if not frappe.db.has_column("Material Substitution Log", "substitution_type"):
        return

    frappe.db.sql("""
        UPDATE `tabMaterial Substitution Log`
        SET substitution_type = 'Full Swap'
        WHERE substitution_type IS NULL OR substitution_type = ''
    """)
    frappe.db.commit()
    print(f"✅  v1_15: Material Substitution Log.substitution_type back-filled to 'Full Swap'.")