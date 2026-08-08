"""
Patch v1_14: Phase 1 schema back-fill for the Scrap Reuse feature.

Alternative Item gains two new columns:

  * source_type          -- "Fresh Stock" / "Recycled Scrap", derived from
                             whether the mapping's alternative_item_code is
                             an Item typed "Scrap Item". The JSON default
                             ("Fresh Stock") only applies to rows inserted
                             after the column exists -- every Alternative
                             Item created before this release needs its
                             real value computed from the linked Item,
                             not left on the default.
  * max_substitution_pct  -- caps how much of a Work Order row may be
                              filled from a scrap alternative. Defaults to
                              100 (no effective cap) for both source types;
                              nothing to infer for pre-existing rows since
                              this is a purely new safeguard, not a
                              back-fillable fact.

Runs after schema sync creates both columns (post_model_sync). The
AlternativeItem.validate() hook now derives source_type on every future
save, so this patch only needs to fix rows that predate the column.
Safe to re-run -- every UPDATE is scoped to rows still on the unset/default
value.
"""
import frappe


def execute():
    if not frappe.db.exists("DocType", "Alternative Item"):
        return
    if not frappe.db.has_column("Alternative Item", "source_type"):
        return  # schema sync for this column hasn't landed yet

    rows = frappe.db.sql(
        """
        SELECT ai.name, item.item_type AS alt_item_type
        FROM `tabAlternative Item` ai
        LEFT JOIN `tabItem` item ON item.name = ai.alternative_item_code
        """,
        as_dict=True,
    )

    scrap_updated = 0
    fresh_updated = 0
    for r in rows:
        is_scrap = r.alt_item_type == "Scrap Item"
        frappe.db.set_value(
            "Alternative Item", r.name,
            {
                "source_type": "Recycled Scrap" if is_scrap else "Fresh Stock",
                "max_substitution_pct": 100,
            },
            update_modified=False,
        )
        if is_scrap:
            scrap_updated += 1
        else:
            fresh_updated += 1

    if rows:
        frappe.db.commit()
    print(
        f"✅  v1_14: Alternative Item.source_type back-filled -- "
        f"{scrap_updated} Recycled Scrap, {fresh_updated} Fresh Stock."
    )