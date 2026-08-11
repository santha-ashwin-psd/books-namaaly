"""
Patch v1_16: Phase 7 back-fill for the "self-contained fixed-asset
lifecycle" build-out (Phases 0-6: tax/ITC on Asset, capitalization GL
split, Asset Quantity Adjustment, Asset Addition, depreciation
re-derivation, GSTR-3B/2A wiring).

Two things actually need back-filling on existing data. Everything else
in the 7-phase plan either introduced a brand-new doctype with no legacy
rows to migrate (Asset Quantity Adjustment, Asset Addition), or is
purely query-side (GSTR reporting reads live data, nothing is stored) --
see the docstring sections below for why those are deliberately left
alone.

PART A -- Asset.taxable_value / total_tax / grand_total
---------------------------------------------------------
New columns from Phase 1. Asset.calculate_totals() already has its own
backward-compatibility branch for this (taxable_value defaults to
purchase_cost when blank and there are no tax rows) -- but that branch
only ever runs inside Document.validate(), i.e. the next time someone
opens and saves the record. An Asset submitted before Phase 1 existed
and never touched again since sits with taxable_value/total_tax/
grand_total still NULL/0, which would under-report its capitalized value
anywhere those columns are read directly (e.g. a future report) instead
of through purchase_cost. Back-fill mirrors calculate_totals()'s own
fallback exactly: taxable_value = purchase_cost, total_tax = 0,
grand_total = purchase_cost. Only touches submitted (docstatus=1),
non-existing-asset (is_existing_asset=0) rows with no tax lines and a
positive purchase_cost -- is_existing_asset rows are explicitly exempted
from this bookkeeping by calculate_totals() itself, and a row that
already has tax lines was created after Phase 1 shipped (the taxes child
table didn't exist before) so it's already been through the real
calculate_totals() logic at least once.

PART B -- Depreciation schedules left un-re-derived by Phase 3, before
Phase 5 exists to fix them
---------------------------------------------------------
Every Asset Quantity Adjustment submitted between Phase 3 shipping and
Phase 5 shipping shrank its Asset's cost/qty/current_value but left the
remaining Pending Depreciation Schedule rows on the old, larger figures
(Phase 3's own msgprint flagged this at the time -- see
asset_quantity_adjustment_gl.py's superseded docstring). Phase 5 added
depreciation_posting.rederive_schedule(), which every *new* Quantity
Adjustment now calls automatically -- but it never ran retroactively for
adjustments that already posted. This back-fills that gap: for every
submitted Asset Quantity Adjustment, re-derive its Asset's schedule
against the Asset's current current_value. Calling rederive_schedule()
on an Asset that's already correct (e.g. adjusted after Phase 5 shipped,
or fully depreciated already) is a safe no-op -- it only db_sets rows
whose figures actually differ (see rederive_schedule's own `changed`
check), and it never touches Completed rows or their posted GL.

Both parts run in post_model_sync: Part A needs the Phase 1 columns to
exist; Part B needs the Asset Quantity Adjustment table (a new doctype
from Phase 3) to exist. Safe to re-run -- Part A is scoped to rows still
on the unset/default value, Part B is naturally idempotent via
rederive_schedule()'s own change-detection.
"""
import frappe
from frappe.utils import flt


def execute():
    _backfill_asset_tax_totals()
    _rederive_schedules_for_existing_quantity_adjustments()


def _backfill_asset_tax_totals():
    if not frappe.db.exists("DocType", "Asset"):
        return
    if not frappe.db.has_column("Asset", "taxable_value"):
        return  # Phase 1 schema hasn't landed yet

    rows = frappe.db.sql(
        """
        SELECT a.name, a.purchase_cost
        FROM `tabAsset` a
        WHERE a.docstatus = 1
          AND a.is_existing_asset = 0
          AND COALESCE(a.purchase_cost, 0) > 0
          AND COALESCE(a.taxable_value, 0) = 0
          AND NOT EXISTS (
              SELECT 1 FROM `tabAsset Tax Detail` t WHERE t.parent = a.name
          )
        """,
        as_dict=True,
    )

    for r in rows:
        cost = flt(r.purchase_cost)
        frappe.db.set_value(
            "Asset", r.name,
            {"taxable_value": cost, "total_tax": 0, "grand_total": cost},
            update_modified=False,
        )

    if rows:
        frappe.db.commit()
    print(
        f"\u2705  v1_16 (Part A): back-filled taxable_value/total_tax/grand_total "
        f"on {len(rows)} pre-Phase-1 Asset record(s)."
    )


def _rederive_schedules_for_existing_quantity_adjustments():
    if not frappe.db.exists("DocType", "Asset Quantity Adjustment"):
        return  # Phase 3 doctype doesn't exist on this site -- nothing to migrate

    from zoho_books_clone.assets.depreciation_posting import rederive_schedule

    asset_names = frappe.db.sql_list(
        """
        SELECT DISTINCT asset
        FROM `tabAsset Quantity Adjustment`
        WHERE docstatus = 1 AND gl_posted = 1
        """
    )

    rederived = 0
    for asset_name in asset_names:
        try:
            if rederive_schedule(asset_name):
                rederived += 1
        except Exception:
            # Never let one bad Asset block the rest of the back-fill --
            # same defensive posture as post_due_depreciation's per-asset
            # try/except in depreciation_posting.py.
            frappe.log_error(
                frappe.get_traceback(),
                f"v1_16 back-fill: rederive_schedule failed for Asset {asset_name}",
            )

    print(
        f"\u2705  v1_16 (Part B): checked {len(asset_names)} Asset(s) with a posted "
        f"Quantity Adjustment; re-derived {rederived} schedule(s) that were still "
        f"on stale pre-Phase-5 figures."
    )