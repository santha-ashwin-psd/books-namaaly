"""
Work Order transactional actions.

Everything doctype-agnostic (create/save/submit/cancel/amend/list Work Order
itself) is already handled by api/docs.py's generic endpoints — this module
only holds the bespoke logic that's specific to running a Work Order:

  get_default_bom_for_item -- resolve which BOM a new Work Order should
                          default to for a given Production Item (Item's
                          default_bom, falling back to any active submitted
                          BOM for that item), so the Work Order form can
                          auto-fill the BOM field on item selection.
  get_bom_breakdown   -- preview raw materials & operations from a BOM at a
                          given qty, so the Work Order form can populate/
                          refresh its child tables client-side before save.
  issue_materials      -- Material Transfer of raw materials into the WIP
                          warehouse (only relevant if a WIP warehouse is set).
  complete_work_order  -- the Manufacture Stock Entry: consumes raw
                          materials, receives the finished item (batch-aware,
                          reuses Batch's shelf-life auto-calc & auto-naming),
                          and posts recoverable scrap/by-products. Being a
                          plain "Manufacture" Stock Entry, it automatically
                          passes through the existing QC gate
                          (auto_create_qc_for_stock_entry) if the finished
                          item requires inspection — no bespoke QC wiring
                          needed here.
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate

from zoho_books_clone.utils.access import assert_can
from zoho_books_clone.utils.tenancy import assert_doc_in_user_company
from zoho_books_clone.inventory.utils import get_valuation_rate, get_conversion_factor, get_stock_balance_bulk


def _get_work_order(work_order):
    wo = frappe.get_doc("Work Order", work_order)
    if wo.docstatus != 1:
        frappe.throw(_("Work Order must be submitted first."))
    return wo


def _get_mfg_settings():
    """Return Manufacturing Settings singleton, falling back to safe defaults
    if the DocType hasn't been migrated yet."""
    try:
        return frappe.get_single("Manufacturing Settings")
    except Exception:
        return frappe._dict({
            "default_source_warehouse": "",
            "default_wip_warehouse": "",
            "default_fg_warehouse": "",
            "default_scrap_warehouse": "",
            "auto_create_job_cards": 1,
            "over_production_allowance_pct": 0,
            "allow_negative_stock": 0,
            "backflush_raw_materials_based_on": "BOM",
            "enable_scrap_reuse": 1,
        })


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_default_bom_for_item(item_code):
    """Resolve the BOM a new Work Order should default to for this
    Production Item, so the client can auto-fill the BOM field the moment
    the item is picked (still overridable — this is only a suggestion).

    Resolution order:
      1. Item.default_bom, if set and it still qualifies (submitted, active,
         actually built against this item, and not a Sub-Assembly BOM --
         guards against a stale link left over from a re-typed item, a
         cancelled/deactivated BOM, or a sub-assembly mistakenly set as an
         item's default).
      2. Otherwise, the most recently modified submitted+active
         Manufacturing/Packing BOM for this item (preferring one flagged
         is_default), matching the same lookup InventoryItems.vue uses to
         populate its own BOM picker.
      3. None, if the item has no usable BOM yet.

    Sub-Assembly BOMs are deliberately never suggested here -- they're meant
    to be consumed *inside* another BOM (via sub_assembly_bom linkage or
    auto-detected phantom), exploded automatically into the Work Order's
    materials/operations, not selected as a Work Order's own top-level BOM.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    if not item_code or not frappe.db.exists("Item", item_code):
        return {"bom": "", "source": "none"}

    default_bom = frappe.db.get_value("Item", item_code, "default_bom")
    if default_bom and frappe.db.exists("BOM", default_bom):
        bom_row = frappe.db.get_value(
            "BOM", default_bom, ["item", "docstatus", "is_active", "bom_type"], as_dict=True
        )
        if (
            bom_row
            and bom_row.item == item_code
            and bom_row.docstatus == 1
            and bom_row.is_active
            and bom_row.bom_type != "Sub-Assembly"
        ):
            return {"bom": default_bom, "source": "item_default"}

    fallback = frappe.get_all(
        "BOM",
        filters={
            "item": item_code,
            "docstatus": 1,
            "is_active": 1,
            "bom_type": ["!=", "Sub-Assembly"],
        },
        fields=["name"],
        order_by="is_default desc, modified desc",
        limit=1,
    )
    if fallback:
        return {"bom": fallback[0].name, "source": "fallback"}

    return {"bom": "", "source": "none"}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_bom_breakdown(bom, qty, work_order=None):
    """Preview the raw-material & operation rows a Work Order would get from
    this BOM at the given quantity. Read-only — does not save anything.

    Handles three BOM types:
      Manufacturing  — standard flat material list; rows with a sub_assembly_bom
                       are recursively exploded (max 5 levels deep) so the Work
                       Order sees only leaf raw materials.
      Sub-Assembly   — treated identically to Manufacturing in this context.
      Packing        — materials are packing_items + the bulk_item consumed at
                       bulk_qty_per_unit per packed unit.

    work_order (optional) -- when given, each returned item row is enriched
    with "source_warehouse": the matching Work Order Item row's own source
    warehouse override, if that row has one (WO Item rows can be sourced
    from a different warehouse per item than the WO's overall Default
    Source Warehouse). Used by the Packing Slip UI's "Reload from WO" so a
    packing material sourced from a dedicated warehouse doesn't silently
    fall back to whatever single "Consume Materials From" warehouse the
    slip happens to have set.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    bom_doc = frappe.get_doc("BOM", bom)
    if bom_doc.docstatus != 1:
        frappe.throw(_("Only a submitted BOM can be used on a Work Order."))

    ms = _get_mfg_settings()
    ratio = flt(qty) / flt(bom_doc.quantity or 1)

    exploded_operations = []
    if bom_doc.bom_type == "Packing":
        items = _explode_packing_bom(bom_doc, ratio, flt(qty))
    else:
        # Manufacturing or Sub-Assembly
        items = _explode_bom_items(bom_doc.items, ratio, depth=0, operations_acc=exploded_operations)
        items = _merge_duplicate_rows(items)

    if work_order and frappe.db.exists("Work Order", work_order):
        row_wh = {
            r.item_code: r.source_warehouse
            for r in frappe.get_doc("Work Order", work_order).items or []
            if r.source_warehouse
        }
        for row in items:
            row["source_warehouse"] = row_wh.get(row.get("item_code")) or ""

    # Operations defined on the top-level BOM, plus (below) any operations
    # belonging to sub-BOMs that _explode_bom_items flattened into raw
    # materials above. A row exploded via sub_assembly_bom OR an
    # auto-detected phantom BOM is NEVER built through its own separate
    # Work Order -- there is nowhere else that sub-BOM's labor/overhead
    # would ever be captured. Without pulling its Operations in here too,
    # that cost simply vanished: not double-counted, not deferred, just
    # silently missing from both Operating Cost and FG stock valuation for
    # every product that uses a sub-assembly/phantom BOM with its own
    # Operations table.
    # Sub-assembly operations are listed BEFORE the top-level BOM's own
    # operations. Job Cards are created in this same order (see Work
    # Order._create_job_cards), and a sub-assembly's process (e.g. "Mixing"
    # for an oil that later gets bottled) has to happen before the final
    # assembly/packing step (e.g. "Assembler") that consumes it -- so its
    # Job Card should exist, and appear in the list, first.
    top_level_operations = [{
        "operation": r.operation,
        "workstation": r.workstation,
        "planned_time_in_mins": flt(r.time_in_mins) * ratio,
        "hour_rate": flt(r.hour_rate),
        "cost": flt(r.cost) * ratio,
        "sub_assembly_bom": "",
        "sub_assembly_item": "",
        "sub_assembly_qty": 0,
    } for r in bom_doc.operations]
    operations = exploded_operations + top_level_operations

    scrap_items = [{
        "item_code": r.item_code,
        "qty": flt(r.qty) * ratio,
        "rate": flt(r.rate),
    } for r in (bom_doc.scrap_items or [])]

    return {
        "production_item": bom_doc.item,
        "item_name": frappe.db.get_value("Item", bom_doc.item, "item_name"),
        "stock_uom": frappe.db.get_value("Item", bom_doc.item, "stock_uom"),
        "bom_type": bom_doc.bom_type,
        "process_loss": flt(bom_doc.process_loss),
        "items": items,
        "operations": operations,
        "scrap_items": scrap_items,
        # Manufacturing Settings defaults for pre-filling Work Order warehouses
        "default_source_warehouse": ms.get("default_source_warehouse") or "",
        "default_wip_warehouse": ms.get("default_wip_warehouse") or "",
        "default_fg_warehouse": ms.get("default_fg_warehouse") or "",
        "default_scrap_warehouse": ms.get("default_scrap_warehouse") or "",
    }



def _explode_bom_items(rows, ratio, depth=0, _seen_boms=None, operations_acc=None, origin=None, origin_item=None, origin_qty=None):
    """Recursively flatten BOM Item rows up to MAX_DEPTH levels deep.

    Rows are exploded (replaced by their own sub-components) when either:
    a) the row has an explicit ``sub_assembly_bom`` link, OR
    b) the item has a phantom BOM (is_phantom_bom=1) — phantom sub-assemblies
       are always exploded because they are never stocked/issued as a separate
       intermediate item.

    All other rows pass through as-is (leaf raw materials).

    origin: the top-level sub_assembly_bom this branch descended from (set
    once at depth 0 and carried through deeper recursion unchanged), so a
    leaf material several levels deep from a sub-assembly still reports
    which top-level sub-assembly it belongs to. None for materials used
    directly on the parent BOM. Purely informational — used by the Work
    Order UI to group the (still-merged, still-correct) consumption rows by
    sub-assembly; it never affects qty/warehouse merge logic below.

    origin_item / origin_qty: the top-level sub-assembly's own production
    item and the quantity of it actually required for this Work Order (set
    together with ``origin`` at the same depth-0-to-1 descent and carried
    unchanged through deeper nesting, exactly like ``origin`` is). Tagged
    onto that branch's exploded operations so a Job Card created for a
    sub-assembly's process can show what it's actually producing and how
    much, instead of just the Work Order's own (unrelated) finished item
    and total qty.

    operations_acc: an optional list that any exploded sub-BOM's own
    Operations get appended to (scaled by that sub-BOM's ratio, same as its
    material rows), since an exploded row never gets a Work Order of its own
    to otherwise capture that labor/overhead in.
    """
    MAX_DEPTH = 5
    if _seen_boms is None:
        _seen_boms = set()
    if operations_acc is None:
        operations_acc = []

    result = []
    for r in rows:
        target_bom = r.sub_assembly_bom or ""

        # Auto-detect phantom BOM even without explicit sub_assembly_bom linkage
        if not target_bom:
            target_bom = frappe.db.get_value(
                "BOM",
                {"item": r.item_code, "is_phantom_bom": 1, "docstatus": 1, "is_active": 1},
                "name",
            ) or ""

        if target_bom and depth < MAX_DEPTH and target_bom not in _seen_boms:
            try:
                sub_doc = frappe.get_doc("BOM", target_bom)
                if sub_doc.docstatus == 1:
                    sub_ratio = flt(r.qty) * ratio / flt(sub_doc.quantity or 1)
                    _seen_boms.add(target_bom)
                    # Origin is fixed the moment we first descend into a
                    # sub-assembly (depth 0 -> 1) and carried unchanged
                    # through any further nested sub-assemblies below it, so
                    # everything under this branch reports back to the same
                    # top-level sub-assembly.
                    branch_origin = origin or target_bom
                    # Same fix-once-at-first-descent treatment as branch_origin:
                    # the sub-assembly's own item and how much of it this Work
                    # Order actually needs (r.qty * ratio == sub_ratio *
                    # sub_doc.quantity) — not recomputed for deeper nested
                    # sub-sub-assemblies, so every operation under this branch
                    # reports back to the same top-level production figure.
                    branch_item = origin_item or sub_doc.item
                    branch_qty = origin_qty if origin_qty is not None else flt(flt(r.qty) * ratio, 4)
                    for op in (sub_doc.operations or []):
                        operations_acc.append({
                            "operation": op.operation,
                            "workstation": op.workstation,
                            "planned_time_in_mins": flt(op.time_in_mins) * sub_ratio,
                            "hour_rate": flt(op.hour_rate),
                            "cost": flt(op.cost) * sub_ratio,
                            # Same origin used to tag this branch's material rows
                            # below -- lets the Work Order UI group/label this
                            # operation (and the Job Card created from it) by
                            # which sub-assembly it belongs to.
                            "sub_assembly_bom": branch_origin,
                            "sub_assembly_item": branch_item,
                            "sub_assembly_qty": branch_qty,
                        })
                    sub_items = _explode_bom_items(
                        sub_doc.items, sub_ratio, depth + 1, _seen_boms, operations_acc,
                        branch_origin, branch_item, branch_qty,
                    )
                    result.extend(sub_items)
                    continue
            except Exception:
                pass  # If sub-BOM can't be loaded, fall through to include item as-is

        conv = get_conversion_factor(r.item_code, r.uom)
        stock_uom = frappe.db.get_value("Item", r.item_code, "stock_uom") or r.uom
        result.append({
            "item_code": r.item_code,
            "item_name": r.item_name,
            "required_qty": flt(r.qty) * conv * ratio,
            "uom": stock_uom,
            "rate": flt(r.rate) / conv if conv else flt(r.rate),
            "amount": flt(r.rate) * flt(r.qty) * ratio,
            "source_warehouse": r.source_warehouse or "",
            "sub_assembly_bom": origin or "",
        })
    return result


def _merge_duplicate_rows(rows):
    """Consolidate exploded raw-material rows that share the same item_code
    and source_warehouse into a single row.

    The same raw material can appear more than once when it's used both
    directly on the top BOM and inside one or more sub-assembly/phantom BOMs
    that get exploded into the flat list — without merging, the Work Order
    (and later the Manufacture Stock Entry) would carry two separate rows for
    the same item. Stock Entry's negative-stock guard checks each row against
    the warehouse's Bin qty independently and doesn't decrement for earlier
    rows in the same document, so split rows can jointly overconsume qty that
    a single merged row would correctly have blocked. The merge key (item +
    warehouse) must NOT be widened to include sub_assembly_bom, or that bug
    comes back — instead, distinct origins are collected onto the merged row
    as `sub_assembly_boms` purely for the Work Order UI to group/label rows
    by sub-assembly (a row touched by more than one sub-assembly, or by both
    a sub-assembly and the top BOM directly, just lists all of them there).
    """
    merged = {}
    order = []
    qty_by_origin = {}  # key -> {origin: accumulated_qty}, origin "" = direct on top BOM
    for r in rows:
        key = (r["item_code"], r.get("source_warehouse") or "")
        origin = r.get("sub_assembly_bom") or ""
        row_qty = flt(r["required_qty"])
        if key not in merged:
            m = dict(r)
            m["sub_assembly_boms"] = [origin] if origin else []
            merged[key] = m
            order.append(key)
            qty_by_origin[key] = {origin: row_qty}
        else:
            m = merged[key]
            m["required_qty"] = flt(m["required_qty"]) + row_qty
            m["amount"] = flt(m["amount"]) + flt(r["amount"])
            # Keep rate consistent with the merged qty/amount -- otherwise
            # rate keeps the first occurrence's value while amount reflects
            # both, so rate * required_qty != amount for merged rows.
            m["rate"] = m["amount"] / m["required_qty"] if m["required_qty"] else 0.0
            if origin and origin not in m["sub_assembly_boms"]:
                m["sub_assembly_boms"].append(origin)
            qty_by_origin[key][origin] = flt(qty_by_origin[key].get(origin, 0)) + row_qty
    for k in order:
        merged[k].pop("sub_assembly_bom", None)
        # Per-origin qty split, purely for the Work Order UI to show each
        # sub-assembly's correct portion of a shared row instead of lumping
        # it into one ambiguous "Shared / Multiple Sub-Assemblies" group.
        # The merged row above stays the single stock-consumption line --
        # this never changes required_qty/amount, only how the same qty is
        # attributed for display.
        merged[k]["sub_assembly_qty_breakdown"] = [
            {"bom": origin, "qty": qty} for origin, qty in qty_by_origin[k].items()
        ]
    return [merged[k] for k in order]


def _explode_packing_bom(bom_doc, ratio, qty_to_pack):
    """For Packing BOMs, the consumed materials are:
    1. The bulk item at bulk_qty_per_unit × qty_to_pack.
    2. All packing_items rows scaled by ratio.

    The bulk item scales directly with qty_to_pack, NOT with `ratio`
    (qty_to_pack / bom.quantity) -- bulk_qty_per_unit is defined as "per
    packed unit" and is independent of whatever batch size the BOM's own
    packing_items happen to be defined for. Using `ratio` here silently
    divided bulk consumption by bom.quantity for any Packing BOM whose
    Quantity field wasn't exactly 1.
    """
    result = []
    if bom_doc.bulk_item and flt(bom_doc.bulk_qty_per_unit) > 0:
        bulk_name = frappe.db.get_value("Item", bom_doc.bulk_item, "item_name") or bom_doc.bulk_item
        bulk_uom = frappe.db.get_value("Item", bom_doc.bulk_item, "stock_uom") or ""
        result.append({
            "item_code": bom_doc.bulk_item,
            "item_name": bulk_name,
            "required_qty": flt(bom_doc.bulk_qty_per_unit) * flt(qty_to_pack),
            "uom": bulk_uom,
            "rate": flt(bom_doc.bulk_rate),
            "amount": flt(bom_doc.bulk_rate) * flt(bom_doc.bulk_qty_per_unit) * flt(qty_to_pack),
            "source_warehouse": "",
        })
    for r in (bom_doc.packing_items or []):
        conv = get_conversion_factor(r.item_code, r.uom)
        stock_uom = frappe.db.get_value("Item", r.item_code, "stock_uom") or r.uom
        result.append({
            "item_code": r.item_code,
            "item_name": r.item_name,
            "required_qty": flt(r.qty) * conv * ratio,
            "uom": stock_uom,
            "rate": flt(r.rate) / conv if conv else flt(r.rate),
            "amount": flt(r.rate) * flt(r.qty) * ratio,
            "source_warehouse": "",
        })
    return result


@frappe.whitelist(allow_guest=False, methods=["POST"])
def issue_materials(work_order):
    """Material Transfer of all still-pending raw materials into the Work
    Order's WIP warehouse. Only meaningful if a WIP warehouse is set —
    otherwise Complete Work Order consumes straight from Source Warehouse
    and this step can be skipped entirely.

    Whether a short item can be *partially* issued now depends on its
    Item Group's "Allow Partial Material Issue" flag:

    - Item Group has the flag checked -> partial issue is allowed for that
      item. Whatever IS available gets moved to WIP now (even 0, i.e.
      fully skipped for this run), and the shortfall stays pending for a
      later call. A short item like this never blocks anyone else.
    - Item Group does NOT have the flag checked (the default) -> that item
      must be FULLY in stock (available >= pending) for the transfer to
      proceed AT ALL. If even one such item is short, NOTHING is issued
      for ANY item this run -- the whole Issue Materials call is blocked
      and no Stock Entry is created, until that item's stock is topped up
      (or its Item Group is switched to allow partial issue)."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Stock Entry", "write")

    wo = _get_work_order(work_order)
    assert_doc_in_user_company(wo)
    if wo.status == "Stopped":
        frappe.throw(_("Work Order is stopped. Resume it before issuing materials."))
    if not wo.wip_warehouse:
        frappe.throw(_(
            "Set a Work-in-Progress Warehouse on the Work Order to issue "
            "materials as a separate step, or skip straight to Complete Work Order."
        ))

    pending_rows = []
    for row in wo.items:
        pending = flt(row.required_qty) - flt(row.transferred_qty)
        if pending > 0:
            pending_rows.append((row, row.source_warehouse or wo.source_warehouse, pending))

    if not pending_rows:
        frappe.throw(_("All raw materials have already been issued for this Work Order."))

    by_warehouse = {}
    for row, wh, pending in pending_rows:
        by_warehouse.setdefault(wh, []).append(row.item_code)

    balances = {}
    for wh, item_codes in by_warehouse.items():
        balances[wh] = get_stock_balance_bulk(item_codes, wh)

    # Item -> Item Group, and Item Group -> Allow Partial Material Issue,
    # fetched in bulk so we don't hit the DB per row.
    item_codes_all = list({row.item_code for row, _wh, _pending in pending_rows})
    item_group_by_item = {
        d.name: d.item_group for d in frappe.get_all(
            "Item", filters={"name": ["in", item_codes_all]},
            fields=["name", "item_group"],
        )
    }
    item_groups_all = list({g for g in item_group_by_item.values() if g})
    partial_allowed_groups = set()
    if item_groups_all:
        partial_allowed_groups = {
            d.name for d in frappe.get_all(
                "Item Group",
                filters={"name": ["in", item_groups_all], "allow_partial_issue": 1},
                fields=["name"],
            )
        }

    def _partial_allowed_for(item_code):
        return item_group_by_item.get(item_code) in partial_allowed_groups

    # ── Blocking pre-check ────────────────────────────────────────────
    # Any pending row whose Item Group does NOT allow partial issue must
    # be FULLY available, or the entire Issue Materials call is blocked --
    # no Stock Entry is created for any item, not even the ones that ARE
    # fully in stock. This has to be checked up front, before we touch
    # anything, since a single non-partial short item invalidates the
    # whole run.
    blockers = []
    for row, wh, pending in pending_rows:
        if _partial_allowed_for(row.item_code):
            continue
        available = flt(balances.get(wh, {}).get(row.item_code))
        if available < pending:
            blockers.append(f"{row.item_code} (needs {pending}, only {available} in stock)")

    if blockers:
        frappe.throw(_(
            "Cannot issue materials — the following item(s) are not fully in stock and "
            "their Item Group doesn't allow partial issue: {0}. Either bring these items "
            "fully into stock, or mark their Item Group as \"Allow Partial Material Issue\" "
            "if short/partial transfers should be allowed for them."
        ).format(", ".join(blockers)))

    se = frappe.new_doc("Stock Entry")
    se.company = wo.company
    se.stock_entry_type = "Material Transfer"
    se.posting_date = nowdate()
    se.work_order = wo.name
    se.remarks = f"Material issue for Work Order {wo.name}"

    issued_rows = []
    skipped = []

    for row, wh, pending in pending_rows:
        available = flt(balances.get(wh, {}).get(row.item_code))

        if available <= 0:
            # Only reachable for partial-allowed items (blockers above
            # already ruled out non-partial items being short at all).
            skipped.append(row.item_code)
            continue

        qty_to_issue = pending if available >= pending else available
        if qty_to_issue < pending:
            skipped.append(f"{row.item_code} (only {qty_to_issue} of {pending} available)")

        se.append("items", {
            "item_code": row.item_code,
            "qty": qty_to_issue,
            "s_warehouse": wh,
            "t_warehouse": wo.wip_warehouse,
        })
        issued_rows.append((row, qty_to_issue))

    if not se.items:
        frappe.throw(_(
            "None of the pending raw materials are currently in stock at their "
            "source warehouse(s), so nothing could be issued. Skipped: {0}"
        ).format(", ".join(skipped)))

    se.insert(ignore_permissions=True)
    se.submit()

    for row, qty_to_issue in issued_rows:
        row.db_set("transferred_qty", flt(row.transferred_qty) + qty_to_issue, update_modified=False)
    if wo.status == "Submitted":
        wo.db_set("status", "In Process")
    _set_operations_status(wo, "In Process", skip_statuses={"Completed"})
    frappe.db.commit()

    if skipped:
        frappe.msgprint(_(
            "Materials issued via {0}. The following item(s) were skipped due to "
            "insufficient stock and remain pending: {1}"
        ).format(se.name, ", ".join(skipped)), indicator="orange", alert=True)

    return se.name


def _consume_qty_for_row(row, wo, consumption_ratio, ms):
    """How much of this row's raw material to consume for this completion run.

    "BOM" (default) — proportional to the BOM's planned qty (required_qty),
    scaled by how much of the Work Order's total qty this run covers.

    "Material Transferred for Manufacture" — proportional to what was
    actually staged into WIP for this row (transferred_qty), not the
    theoretical BOM requirement, so consumption reflects real shop-floor
    transfers rather than the plan. Falls back to the BOM basis for any row
    that was never transferred (e.g. no WIP warehouse configured), and is
    capped so a run can never consume more than remains un-consumed of what
    was transferred.
    """
    basis = ms.get("backflush_raw_materials_based_on") or "BOM"
    if basis == "Material Transferred for Manufacture" and flt(row.transferred_qty) > 0:
        row_ratio = flt(row.transferred_qty) / flt(wo.qty or 1)
        consume_qty = row_ratio * consumption_ratio * flt(wo.qty or 1)
        remaining_transferred = flt(row.transferred_qty) - flt(row.consumed_qty)
        return max(min(consume_qty, remaining_transferred), 0)
    return flt(row.required_qty) * consumption_ratio


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_scrap_reuse_shortfall_warnings(work_order):
    """Scrap Reuse feature, Phase 8 -- proactive edge-case check for "scrap
    stock going short mid-production".

    apply_partial_scrap_substitution only checks scrap availability at the
    moment it's applied; it doesn't reserve stock, so by the time this Work
    Order is actually completed, another Work Order (or a manual Stock
    Entry) could have already drawn down the same scrap warehouse below
    what this row still needs. complete_work_order's own pre-consumption
    check (see the is_scrap_row branch in its raw-material loop) is the
    authoritative gate and will still throw if this happens -- this
    endpoint exists purely so WorkOrder.vue can warn about it BEFORE the
    person opens the Complete Work Order modal and fills in qty, instead of
    only finding out from an error after clicking Complete.

    Returns a list of {work_order_item_row, item_code, source_warehouse,
    required_qty, available_qty, shortfall} for every not-yet-fully-
    consumed scrap-split row whose current stock in its own
    source_warehouse has fallen below its remaining required_qty. Empty
    list means no shortfall right now.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    wo = _get_work_order(work_order)
    assert_doc_in_user_company(wo)

    if wo.wip_warehouse:
        # Consumption sources from WIP once materials are issued, not
        # straight from the scrap row's own warehouse -- see
        # complete_work_order's s_wh resolution. The shortfall this checks
        # for can't occur once WIP is in the picture (issue_materials
        # itself already applies its own stock guard at transfer time).
        return []

    from zoho_books_clone.inventory.utils import get_stock_balance_bulk

    scrap_rows = [
        r for r in wo.items
        if r.is_scrap_row and flt(r.required_qty) - flt(r.consumed_qty) > 0.0001 and r.source_warehouse
    ]
    if not scrap_rows:
        return []

    by_warehouse = {}
    for r in scrap_rows:
        by_warehouse.setdefault(r.source_warehouse, []).append(r)

    warnings = []
    for warehouse, rows in by_warehouse.items():
        balances = get_stock_balance_bulk(list({r.item_code for r in rows}), warehouse)
        for r in rows:
            remaining_required = flt(r.required_qty) - flt(r.consumed_qty)
            available = flt(balances.get(r.item_code, 0.0))
            if available < remaining_required - 0.0001:
                warnings.append({
                    "work_order_item_row": r.name,
                    "item_code": r.item_code,
                    "source_warehouse": warehouse,
                    "required_qty": remaining_required,
                    "available_qty": available,
                    "shortfall": remaining_required - available,
                })
    return warnings


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_job_card_scrap_items(work_order):
    """Flatten every Scrap Item row logged on this Work Order's own Job
    Cards (see JobCard._calc_scrap_items), across every operation, into a
    single list the Complete Work Order dialog can use as its starting
    rows -- what actually came off the floor per operation, rather than a
    BOM-proportional guess. Cancelled Job Cards are excluded (their rows
    never happened as far as production is concerned).

    Each row is returned with its Job Card and Operation so the dialog can
    show where it came from; the caller (complete_work_order) only reads
    item_code/qty/rate/is_process_loss and ignores the rest, same as any
    other scrap_items row.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    wo = _get_work_order(work_order)
    assert_doc_in_user_company(wo)

    job_cards = frappe.get_all(
        "Job Card",
        filters={"work_order": work_order, "status": ["!=", "Cancelled"]},
        fields=["name", "operation"],
    )
    if not job_cards:
        return []
    jc_operation = {jc.name: jc.operation for jc in job_cards}

    rows = frappe.get_all(
        "Job Card Scrap Item",
        filters={"parent": ["in", list(jc_operation.keys())]},
        fields=["parent", "item_code", "item_name", "qty", "rate", "is_process_loss"],
        order_by="parent asc, idx asc",
    )
    for r in rows:
        r["job_card"] = r.pop("parent")
        r["operation"] = jc_operation.get(r["job_card"], "")
    return rows


@frappe.whitelist(allow_guest=False)
def complete_work_order(work_order, qty_manufactured, process_loss_qty=0,
                         scrap_items=None, batch_no=None,
                         manufacturing_date=None, expiry_date=None,
                         close_on_loss_reconciliation=0, over_production_qty=0):
    """Create & submit the Manufacture Stock Entry for a batch of production
    against this Work Order. Can be called multiple times for partial
    completions until produced_qty reaches the planned qty.

    qty_manufactured  -- finished-good qty actually produced this run
    over_production_qty -- explicit qty, entered per-completion in the
                         Complete Work Order dialog, that this run is
                         allowed to exceed the planned qty by (e.g. planned
                         qty is 1000, actual yield is 1250 -- the caller
                         passes qty_manufactured=1250 (or split across runs)
                         and over_production_qty=250 to justify the excess
                         for THIS call only). Widens the completion cap in
                         addition to (not instead of) Manufacturing
                         Settings' Over-Production Allowance %, so a
                         one-off yield variance doesn't require raising a
                         global % that would then apply to every Work
                         Order. Purely a per-call authorization + audit
                         trail -- it does not change how qty_manufactured
                         itself is consumed, costed, or moved to the FG
                         warehouse; that happens exactly as it always has,
                         for the full qty_manufactured amount. The
                         cumulative total across all completions is kept
                         on wo.over_production_qty for reporting.
    process_loss_qty  -- manual/legacy process-loss qty for this run
                         (material that never became stock — evaporation,
                         trimming, spillage etc. — logged for yield
                         reporting only, no stock movement). Kept as a
                         standalone override for callers who haven't moved
                         to per-row process loss yet; see is_process_loss
                         below for the row-level equivalent, which is
                         summed INTO this rather than replacing it.
    scrap_items       -- optional list of row dicts, each either:
                           - recoverable: {item_code, qty, rate?, batch_no?}
                             -- gets a real Stock Entry line into
                             scrap_warehouse, exactly as before.
                           - process loss: {qty, is_process_loss: 1} --
                             item_code is not required (there's nothing to
                             recover). No stock line is created; qty is
                             instead added to process_loss_qty above before
                             any of the consumption/costing math below runs,
                             so it's indistinguishable downstream from a
                             qty passed via the manual process_loss_qty arg.
    close_on_loss_reconciliation -- if truthy, a Work Order can also be
                         marked Completed once cumulative produced_qty +
                         process_loss_qty (not produced_qty alone) reaches
                         wo.qty -- i.e. the planned qty is treated as raw
                         material *input* that's now fully accounted for
                         between finished goods and process loss (e.g. an
                         Ayurvedic decoction: 8kg produced + 2kg loss fully
                         reconciles a 10kg planned batch). When falsy
                         (default), behavior is unchanged from before this
                         flag existed: only produced_qty counts toward
                         completion. This is a pure per-call flag -- the
                         engine does not read Manufacturing Settings for it;
                         the caller (API layer) is responsible for resolving
                         any UI default before calling in.

                         If this run would push (cumulative produced_qty +
                         cumulative process_loss_qty) beyond wo.qty while
                         this flag is set, the call is blocked with an
                         error -- more raw material cannot be consumed than
                         was ever issued for the batch. This check is
                         independent of the existing Over-Production
                         Allowance % path below, which continues to govern
                         produced_qty vs wo.qty exactly as before regardless
                         of this flag.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Stock Entry", "write")

    if isinstance(scrap_items, str):
        scrap_items = frappe.parse_json(scrap_items)
    scrap_items = scrap_items or []

    # Row-level process loss (is_process_loss=1 scrap rows) is folded into
    # process_loss_qty up front, before consumption_ratio and everything
    # downstream of it is computed -- this is what makes the two mechanisms
    # (manual param vs. per-row flag) additive and interchangeable rather
    # than needing two separate code paths through the rest of the function.
    scrap_process_loss_qty = sum(
        flt(s.get("qty")) for s in scrap_items
        if s.get("is_process_loss") and flt(s.get("qty")) > 0
    )

    wo = _get_work_order(work_order)
    assert_doc_in_user_company(wo)
    if wo.status == "Stopped":
        frappe.throw(_("Work Order is stopped. Resume it before recording completion."))

    bom_type = frappe.db.get_value("BOM", wo.bom, "bom_type")
    if bom_type == "Packing":
        frappe.throw(_(
            "Work Order {0} uses a Packing BOM. Use a Packing Slip to record "
            "its completion instead of completing the Work Order directly."
        ).format(wo.name))

    qty_manufactured = flt(qty_manufactured)
    process_loss_qty = flt(process_loss_qty) + scrap_process_loss_qty
    over_production_qty = flt(over_production_qty)
    if qty_manufactured <= 0:
        frappe.throw(_("Quantity Manufactured must be greater than zero."))
    if over_production_qty < 0:
        frappe.throw(_("Over Production Qty cannot be negative."))
    if over_production_qty > qty_manufactured:
        frappe.throw(_(
            "Over Production Qty ({0}) cannot exceed Quantity Manufactured ({1})."
        ).format(over_production_qty, qty_manufactured))

    # When a WIP warehouse is configured, consumption below is sourced from
    # it (not source_warehouse), so any row still short on transferred_qty
    # vs required_qty means WIP doesn't actually hold enough of that item
    # yet. The Vue page disables Complete Work Order for this same reason,
    # but this is the real guard -- it also covers Job Card auto-completion
    # and any other caller that reaches this function directly.
    if wo.wip_warehouse:
        pending = [
            f"{r.item_code} ({flt(r.transferred_qty)}/{flt(r.required_qty)})"
            for r in wo.items
            if flt(r.transferred_qty) < flt(r.required_qty) - 0.0001
        ]
        if pending:
            frappe.throw(_(
                "All raw materials must be issued to WIP before completing this "
                "Work Order. Pending: {0}"
            ).format(", ".join(pending)))

    # Recoverable scrap rows need somewhere to land. complete_work_order
    # falls back to fg_warehouse when scrap_warehouse isn't set (below), so
    # only fail here if BOTH are empty -- catching it up front with a clear
    # message instead of letting it surface deep inside Stock Entry
    # validation once the recoverable rows are appended.
    has_recoverable_scrap = any(
        not s.get("is_process_loss") and flt(s.get("qty")) > 0 and s.get("item_code")
        for s in scrap_items
    )
    if has_recoverable_scrap and not (wo.scrap_warehouse or wo.fg_warehouse):
        frappe.throw(_(
            "Work Order {0} has no Scrap Warehouse or Finished Goods Warehouse set. "
            "Set one of these before recording scrap/by-product rows."
        ).format(wo.name))

    # Lock the Work Order row for the rest of this transaction so two
    # concurrent completions against the same Work Order can't both read
    # produced_qty, both pass the over-production check, and both commit --
    # the second call blocks here until the first one's transaction ends.
    frappe.db.sql("SELECT name FROM `tabWork Order` WHERE name=%s FOR UPDATE", (wo.name,))
    # Re-read produced_qty and process_loss_qty now that we hold the lock:
    # the copies on `wo` (loaded before the lock) may be stale if we just
    # waited behind another completion.
    current_produced_qty = flt(frappe.db.get_value("Work Order", wo.name, "produced_qty"))
    current_process_loss_qty = flt(frappe.db.get_value("Work Order", wo.name, "process_loss_qty"))
    current_total_operating_cost = flt(frappe.db.get_value("Work Order", wo.name, "total_operating_cost"))
    current_operating_cost_absorbed_total = flt(
        frappe.db.get_value("Work Order", wo.name, "operating_cost_absorbed_total")
    )

    ms = _get_mfg_settings()
    over_pct = flt(ms.get("over_production_allowance_pct", 0))
    # Settings % (auto-applies to every Work Order) and the explicit
    # per-call over_production_qty (typed once, for this batch only) are
    # additive -- either alone can open up the cap, and together they
    # stack. This lets a one-off yield variance be authorized right in the
    # Complete Work Order dialog without touching the global % setting.
    max_allowed = flt(wo.qty) * (1.0 + over_pct / 100.0) + over_production_qty
    new_total = current_produced_qty + qty_manufactured

    # The actual overshoot THIS run contributes above the planned qty --
    # i.e. how far new_total sits above wo.qty, minus how far
    # current_produced_qty already sat above wo.qty. This is the same
    # quantity used further down to grow the cumulative wo.over_production_qty
    # tracker, and it's deliberately NOT the same as the raw
    # over_production_qty argument: that argument is only a ceiling the
    # caller is authorizing (used above to widen max_allowed), not a
    # trustworthy measure of how much of this run is actually bonus. A run
    # that's still partly or wholly within the planned qty must still pull
    # material for that portion regardless of what over_production_qty was
    # typed into the dialog -- see material_basis_qty below, which uses
    # this_run_over_qty rather than over_production_qty for exactly that
    # reason.
    this_run_over_qty = (
        max(0.0, new_total - flt(wo.qty)) - max(0.0, current_produced_qty - flt(wo.qty))
    )

    if new_total > max_allowed + 0.0001:
        if over_production_qty > 0:
            frappe.throw(_(
                "Total produced qty ({0}) would exceed the planned qty ({1}) plus the "
                "Over Production Qty entered ({2}) (max {3}). Increase Over Production "
                "Qty in the Complete Work Order dialog to allow this."
            ).format(new_total, wo.qty, over_production_qty, max_allowed))
        elif over_pct > 0:
            frappe.throw(_(
                "Total produced qty ({0}) would exceed the planned qty ({1}) plus the "
                "{2}% over-production allowance (max {3}). Enter an Over Production Qty "
                "in the Complete Work Order dialog to allow more."
            ).format(new_total, wo.qty, over_pct, max_allowed))
        else:
            frappe.throw(_(
                "Quantity Manufactured ({0}) exceeds the remaining planned qty ({1}). "
                "If this run genuinely produced more than planned, enter the extra in "
                "\"Over Production Qty\" in the Complete Work Order dialog. If the "
                "difference is process loss instead (e.g. evaporation/trimming/spillage), "
                "check \"this completes the batch\" and enter the loss in Process Loss / "
                "Wastage Qty instead."
            ).format(qty_manufactured, flt(wo.qty) - current_produced_qty))

    close_on_loss_reconciliation = bool(frappe.utils.cint(close_on_loss_reconciliation))

    # When loss-reconciliation is requested, produced+loss can never be
    # allowed to exceed the planned qty -- that would mean consuming more
    # raw material than was ever issued for this batch. This is separate
    # from (and checked in addition to) the Over-Production Allowance %
    # guard above, which only ever looks at produced_qty.
    if close_on_loss_reconciliation:
        new_total_with_loss = current_produced_qty + qty_manufactured + current_process_loss_qty + process_loss_qty
        if new_total_with_loss > flt(wo.qty) + 0.0001:
            frappe.throw(_(
                "Produced qty plus process loss ({0}) would exceed the planned qty ({1}). "
                "Cannot consume more raw material than was issued for this batch."
            ).format(new_total_with_loss, wo.qty))

    # Whether this run brings the Work Order to full completion -- computed
    # up front (rather than re-derived after the Stock Entry is posted) so
    # both the operating-cost true-up and the process-loss split below can
    # use it while building this run's Stock Entry.
    #
    # Base rule (always applies): produced_qty alone reaching wo.qty.
    # Loss-reconciliation rule (only when the flag is set): produced_qty +
    # process_loss_qty together reaching wo.qty also counts as final --
    # this lets a batch close when the shortfall from planned qty is fully
    # explained by process loss rather than sitting open forever. When the
    # flag is off, this OR clause is simply never true and behavior is
    # unchanged from before it existed.
    is_final = new_total >= flt(wo.qty) - 0.0001
    if close_on_loss_reconciliation:
        cumulative_produced_and_loss = (
            current_produced_qty + qty_manufactured + current_process_loss_qty + process_loss_qty
        )
        is_final = is_final or (cumulative_produced_and_loss >= flt(wo.qty) - 0.0001)


    # Raw materials are consumed for the FULL quantity that left the
    # process -- both what became finished stock (qty_manufactured) and
    # what was lost in-process (process_loss_qty, e.g. evaporation/trimming/
    # spillage). Scaling consumption by qty_manufactured alone would under-
    # consume raw material stock any time there's process loss, leaving
    # material "in stock" on paper that was actually used up on the floor.
    #
    # this_run_over_qty (computed above, from actual produced_qty history --
    # NOT the raw over_production_qty argument) is carved OUT of this basis
    # first: it's an explicit yield improvement -- the same raw material
    # batch simply produced more finished units than the BOM ratio predicted
    # (e.g. 1kg of material was transferred/issued expecting 1kg output, but
    # the actual process yielded 6kg). It is NOT "make a bigger batch" and
    # must never scale up how much raw material this run tries to consume --
    # doing so would try to pull WIP/source stock for material that was
    # never issued for the extra qty in the first place, and previously
    # threw "Insufficient stock" for exactly that reason. material_basis_qty
    # is what actually determines raw material AND operating cost
    # consumption below; qty_manufactured (the full amount, over-production
    # included) is still what gets received into the FG warehouse and what
    # the resulting material+operating cost pool is spread across per unit
    # (see fg_unit_rate below) -- so the bonus units simply come out
    # cheaper per unit, which is the correct economics of a yield gain.
    #
    # Using this_run_over_qty here (instead of the raw over_production_qty
    # argument) matters for two bugs it fixes: (1) a caller passing
    # over_production_qty larger than what this run actually overshot by
    # (e.g. mis-estimating, or a straddling run where only part of it is
    # above wo.qty) can no longer under-consume material for units that were
    # still within the planned qty; (2) since this_run_over_qty is derived
    # from produced_qty history rather than trusted user input, it can never
    # exceed qty_manufactured itself, so material_basis_qty can never go
    # negative or silently zero out consumption for a run that's mostly or
    # entirely within plan.
    material_basis_qty = max(0.0, qty_manufactured - this_run_over_qty)
    consumption_ratio = (material_basis_qty + process_loss_qty) / flt(wo.qty or 1)

    se = frappe.new_doc("Stock Entry")
    se.company = wo.company
    se.stock_entry_type = "Manufacture"
    se.posting_date = nowdate()
    se.work_order = wo.name
    se.remarks = f"Manufacture against Work Order {wo.name}"

    # Consume raw materials proportional to what's being completed this run.
    # Source is the WIP warehouse if materials were staged there via
    # issue_materials; otherwise straight from each row's own source
    # warehouse (or the Work Order's default).
    #
    # Each row's rate is looked up and set explicitly here (rather than left
    # for Stock Entry's own auto-fill) so we can total the real consumed
    # cost and use it to value the finished good below -- Stock Entry's
    # auto-fill only ever rates outgoing/consumption rows, never incoming
    # ones, so without this the FG receipt has no cost basis to draw from.
    total_consumed_cost = 0.0
    blockers = []
    allow_negative = ms.get("allow_negative_stock")
    
    # Pre-check all rows for stock availability before failing on the first one
    for row in wo.items:
        consume_qty = _consume_qty_for_row(row, wo, consumption_ratio, ms)
        if consume_qty <= 0:
            continue
        s_wh = wo.wip_warehouse or row.source_warehouse or wo.source_warehouse
        if not s_wh:
            continue
        if not allow_negative:
            available = get_stock_balance_bulk([row.item_code], s_wh).get(row.item_code, 0.0)
            if flt(available) < consume_qty - 0.0001:
                # Same format as issue_materials so the Vue frontend can parse it if needed
                blockers.append(f"{row.item_code} (needs {consume_qty}, only {flt(available)} in stock)")

    if blockers:
        frappe.throw(_(
            "Cannot complete Work Order — the following item(s) are not fully in stock in their source warehouse: {0}. "
            "Either bring these items fully into stock, or enable negative stock."
        ).format(", ".join(blockers)))
    for row in wo.items:
        consume_qty = _consume_qty_for_row(row, wo, consumption_ratio, ms)
        if consume_qty <= 0:
            continue
        s_wh = wo.wip_warehouse or row.source_warehouse or wo.source_warehouse
        if not s_wh:
            frappe.throw(_(
                "Row for {0}: no Source Warehouse set (on the Work Order Item, "
                "the Work Order's Default Source Warehouse, or a WIP Warehouse)."
            ).format(row.item_code))
        # Edge case (Phase 8): a scrap-split row's stock can have gone short
        # between apply_partial_scrap_substitution and this completion run.
        # This is now covered by the generic bulk check above, but we keep
        # this comment block for historical context.
        rm_rate = get_valuation_rate(row.item_code, s_wh)
        total_consumed_cost += consume_qty * rm_rate
        se.append("items", {
            "item_code": row.item_code,
            "qty": consume_qty,
            "s_warehouse": s_wh,
            "basic_rate": rm_rate,
        })

    # Recoverable scrap/by-products are valued first (at whatever rate the
    # caller supplied, falling back to the item's current valuation rate in
    # the scrap warehouse) and their value is credited OUT of the consumed
    # cost before the remainder is spread across the finished good -- scrap
    # that can be resold/reused shouldn't inflate the FG's cost.
    scrap_warehouse = wo.scrap_warehouse or wo.fg_warehouse
    total_scrap_value = 0.0
    scrap_rows_to_append = []
    for s in scrap_items:
        if s.get("is_process_loss"):
            # Already folded into process_loss_qty above -- no stock line,
            # no item required, no value recovered.
            continue
        s_qty = flt(s.get("qty"))
        if s_qty <= 0 or not s.get("item_code"):
            continue
        s_rate = flt(s.get("rate"))
        if not s_rate:
            s_rate = get_valuation_rate(s["item_code"], scrap_warehouse)
        total_scrap_value += s_qty * s_rate
        scrap_rows_to_append.append((s, s_qty, s_rate))

    # Operating Cost allocation: spread the Work Order's Total Operating Cost
    # (labor/overhead from the Operations table, see work_order.py::
    # calculate_operating_cost) across the finished good, same as raw
    # material cost is. Uses consumption_ratio (material_basis_qty +
    # process_loss_qty, scaled against wo.qty) rather than qty_manufactured
    # alone -- the time/labor behind process_loss_qty was genuinely spent
    # too, same reasoning as why raw material consumption already includes
    # it (see consumption_ratio above), so operating cost should absorb into
    # the FG that did come out on the same basis, not be under-applied.
    # Bonus over-production qty is excluded from this basis the same way it
    # is from material consumption -- no extra labor/machine time was spent
    # to get the extra yield, so it shouldn't absorb extra operating cost
    # either; it still shares in the resulting cost pool per unit below.
    #
    # Note: total_operating_cost can itself change between partial
    # completions (Actual Operating Cost rises as more Job Card time is
    # logged), so the per-unit rate used here is a snapshot at the moment of
    # this completion -- each run absorbs cost at whatever rate was current
    # when it was recorded, rather than being retroactively rebalanced
    # across earlier runs. This mirrors how raw material valuation rates are
    # also snapshotted per run.
    operating_cost_this_run = 0.0
    if flt(wo.qty) > 0:
        operating_cost_this_run = current_total_operating_cost * consumption_ratio

    # True-up on the final completion: total_operating_cost can drift between
    # partial completions as planned time gets replaced by actual logged
    # time (see calculate_operating_cost), so the sum of
    # operating_cost_this_run across every partial run generally won't equal
    # the final total_operating_cost -- the gap was previously never
    # reconciled anywhere (unlike the raw-material side, which already has
    # manufacturing_variance_loss for its own shortfall pool). On the run
    # that completes the Work Order, absorb whatever is left instead of the
    # snapshot-based share, so cumulative absorption lines up exactly with
    # the now-final total_operating_cost.
    if is_final:
        operating_cost_this_run = current_total_operating_cost - current_operating_cost_absorbed_total

    # Process loss beyond the BOM's expected % (process_loss_percent,
    # snapshotted onto the Work Order at creation from BOM.process_loss) is
    # abnormal -- e.g. a spill or an operator error, not the shrinkage the
    # BOM already accounts for. Loss within the expected % stays capitalized
    # into FG cost same as before; only the excess is carved out and
    # expensed via manufacturing_variance_loss instead of inflating
    # fg_unit_rate.
    expected_loss_qty_this_run = flt(wo.process_loss_percent) / 100.0 * material_basis_qty
    abnormal_loss_qty = max(0.0, process_loss_qty - expected_loss_qty_this_run)
    total_consumed_qty_this_run = material_basis_qty + process_loss_qty
    rm_unit_cost_this_run = (
        total_consumed_cost / total_consumed_qty_this_run if total_consumed_qty_this_run > 0 else 0.0
    )
    abnormal_loss_value = abnormal_loss_qty * rm_unit_cost_this_run

    # Whatever consumed cost is left after crediting out scrap value gets
    # spread across the qty actually manufactured this run. This also
    # absorbs the cost of any NORMAL process_loss_qty (that material was
    # consumed too, per consumption_ratio above, but never became stock of
    # its own) into the finished good that did come out -- the standard
    # costing treatment for in-process loss. Abnormal loss (abnormal_loss_value,
    # carved out above) is deliberately excluded from this pool so it never
    # capitalizes into fg_unit_rate.
    #
    # In the unusual case where total_scrap_value alone exceeds the
    # available cost pool (total_consumed_cost + operating_cost_this_run),
    # the naive rate would go negative -- clamped to 0 below. That clamp
    # would otherwise silently strand the shortfall as an uncleared debit
    # balance in the WIP account forever (nothing ever credits it out).
    # manufacturing_variance_loss captures exactly that shortfall (plus any
    # abnormal process loss) so _post_gl_entries can write it off to a
    # loss/variance account instead.
    raw_pool = total_consumed_cost - total_scrap_value + operating_cost_this_run - abnormal_loss_value
    fg_unit_rate = 0.0
    manufacturing_variance_loss = abnormal_loss_value
    if qty_manufactured > 0:
        fg_unit_rate = max(raw_pool, 0.0) / qty_manufactured
        if raw_pool < 0:
            manufacturing_variance_loss += -raw_pool

    se.remarks += f" (operating cost absorbed this run: {operating_cost_this_run:.2f})"
    if abnormal_loss_value:
        se.remarks += f" (abnormal process loss expensed: {abnormal_loss_value:.2f})"
    se.operating_cost_absorbed = operating_cost_this_run
    se.manufacturing_variance_loss = manufacturing_variance_loss
    se.process_loss_qty = process_loss_qty
    # this_run_over_qty (not the raw over_production_qty argument -- see
    # material_basis_qty above) stored on the entry so reverse_wo_completion
    # can roll back exactly this run's contribution to wo.over_production_qty
    # instead of leaving it stale after a reversal.
    se.over_production_qty = this_run_over_qty

    # Receive the finished good. If it's batch-tracked, pre-create the Batch
    # record first (same pattern the transaction pages use) so Stock Entry's
    # own validation — which requires the Batch to already exist — passes.
    # Leaving batch_no blank lets Batch.autoname generate
    # {Item Code}-{Year}-{Sequence}, and leaving expiry_date blank lets
    # Batch.set_expiry_date_from_shelf_life derive it from Item.shelf_life_in_days.
    fg_row = {
        "item_code": wo.production_item,
        "qty": qty_manufactured,
        "t_warehouse": wo.fg_warehouse,
        "basic_rate": fg_unit_rate,
    }
    if frappe.db.get_value("Item", wo.production_item, "has_batch_no"):
        if not batch_no or not frappe.db.exists("Batch", batch_no):
            new_batch = frappe.get_doc({
                "doctype": "Batch",
                "batch_no": batch_no or None,
                "item": wo.production_item,
                "warehouse": wo.fg_warehouse,
                "manufacturing_date": manufacturing_date or nowdate(),
                "expiry_date": expiry_date or None,
            })
            new_batch.insert(ignore_permissions=True)
            batch_no = new_batch.name
        fg_row["batch_no"] = batch_no
    se.append("items", fg_row)

    # Recoverable scrap/by-products, if any. Mirror the FG handling above:
    # batch-tracked scrap items need a Batch pre-created before Stock Entry's
    # own validation (which requires the Batch to already exist) will let the
    # row through. A caller can pass an explicit batch_no (and now rate) per
    # scrap item via {"item_code": ..., "qty": ..., "rate": ..., "batch_no": ...};
    # otherwise a batch is auto-generated the same way the FG batch is, and
    # the rate falls back to the scrap warehouse's current valuation rate
    # (computed above, before this row existed to skew that valuation).
    for s, s_qty, s_rate in scrap_rows_to_append:
        scrap_row = {
            "item_code": s["item_code"], "qty": s_qty, "t_warehouse": scrap_warehouse,
            "basic_rate": s_rate, "is_scrap_item": 1,
        }
        if frappe.db.get_value("Item", s["item_code"], "has_batch_no"):
            s_batch_no = s.get("batch_no")
            if not s_batch_no or not frappe.db.exists("Batch", s_batch_no):
                new_scrap_batch = frappe.get_doc({
                    "doctype": "Batch",
                    "batch_no": s_batch_no or None,
                    "item": s["item_code"],
                    "warehouse": scrap_warehouse,
                    "manufacturing_date": manufacturing_date or nowdate(),
                })
                new_scrap_batch.insert(ignore_permissions=True)
                s_batch_no = new_scrap_batch.name
            scrap_row["batch_no"] = s_batch_no
        se.append("items", scrap_row)



    se.insert(ignore_permissions=True)
    se.submit()

    for row in wo.items:
        consume_qty = _consume_qty_for_row(row, wo, consumption_ratio, ms)
        if consume_qty > 0:
            current_consumed_qty = flt(frappe.db.get_value("Work Order Item", row.name, "consumed_qty"))
            row.db_set("consumed_qty", current_consumed_qty + consume_qty, update_modified=False)

    new_produced_qty = new_total  # == current_produced_qty + qty_manufactured
    wo.db_set("produced_qty", new_produced_qty)
    wo.db_set("process_loss_qty", current_process_loss_qty + process_loss_qty)
    # Incremental over-production contributed by THIS run only -- already
    # computed above (as this_run_over_qty) so material_basis_qty and this
    # cumulative tracker always agree on how much of the run was bonus.
    # Computed the way it is (rather than just adding qty_manufactured
    # whenever over_production_qty was passed) so it stays correct across
    # partial completions: a run that's still entirely within the planned
    # qty contributes 0 here even if a caller passed a nonzero
    # over_production_qty just to widen the cap check above.
    current_over_qty = flt(frappe.db.get_value("Work Order", wo.name, "over_production_qty"))
    if this_run_over_qty > 0:
        wo.db_set("over_production_qty", current_over_qty + this_run_over_qty)
    wo.db_set("operating_cost_absorbed_total", current_operating_cost_absorbed_total + operating_cost_this_run)
    is_complete = is_final
    wo.db_set("status", "Completed" if is_complete else "In Process")
    if is_complete:
        # Work Order is fully done -- finalize every operation as Completed,
        # even if a Job Card lagged behind (e.g. someone forgot to close the
        # last Job Card). This is the one point where forcing the status is
        # correct, since there's no more production left to track against it.
        _set_operations_status(wo, "Completed")
        if new_produced_qty < flt(wo.qty) - 0.0001:
            # This run only reached is_final via the close_on_loss_reconciliation
            # OR-clause above (produced_qty + process_loss_qty >= wo.qty),
            # not via produced_qty alone. Stamp that durably alongside status
            # so _stamp_wo_completed's guard -- which only checks produced_qty
            # by default -- can still recognise this Work Order as genuinely
            # finished if it ever needs to self-heal a stuck status later
            # (e.g. from the QC-pass release path). Without this, a WO closed
            # via loss reconciliation would look "not yet done" to that guard
            # and the self-heal would incorrectly no-op.
            wo.db_set("qty_reconciled_via_loss", 1)
    else:
        # Partial completion: still in progress. Bring not-yet-started rows
        # up to "In Process" but never downgrade an operation a Job Card has
        # already marked Completed -- that would erase real progress every
        # time another partial completion is recorded.
        _set_operations_status(wo, "In Process", skip_statuses={"Completed"})

    # If the Work Order is now fully completed and it belongs to a Production
    # Plan, check whether all linked WOs are also done — if so, close the plan.
    if is_complete and wo.production_plan:
        from zoho_books_clone.manufacturing.production_plan_engine import maybe_complete_production_plan
        maybe_complete_production_plan(wo.production_plan)

    frappe.db.commit()

    if is_complete:
        _stamp_wo_completed(wo.name)

    return se.name


def _stamp_wo_completed(work_order: str) -> None:
    """Idempotent safety-net: force this Work Order's status/operations to
    Completed and commit, on its own. Called both at the end of a completing
    run above, and again from qc_hold_manager._do_quarantine_release once a
    QC-required FG batch actually clears quarantine -- see the call there for
    why a second call site exists at all.

    complete_work_order already sets status="Completed" unconditionally the
    moment produced_qty reaches wo.qty (see is_complete above), regardless of
    whether that FG still needs QC -- QC hasn't even run yet at that point in
    the function, so gating completion on it there isn't an option. That
    write and this one both land in the SAME request/transaction as the
    Stock Entry submission just above, which is exactly the situation
    reported as leaving status stuck on "In Process" despite qty/stock
    being fully correct: something in this function's own tail can throw
    after Stock Entry submission (which durably commits on its own via
    Frappe's stock-ledger posting) but before this function's closing
    frappe.db.commit() -- rolling back only the trailing db_set() calls
    while the physical Stock Entry (and any QC Inspection created from it)
    survives. A second, independent call from the QC-pass release path
    re-asserts the same end state without touching stock again, so a Work
    Order that's physically done but stuck "In Process" self-heals the
    moment its QC clears, with no re-consumption risk -- this only ever
    writes status/operations, never qty or stock.
    """
    wo = frappe.get_doc("Work Order", work_order)
    if wo.status in ("Completed", "Cancelled"):
        return
    # Base rule: produced_qty alone reached the planned qty. Loss-reconciliation
    # rule: this Work Order was already durably flagged (in complete_work_order,
    # at the same time as this same trailing block set produced_qty/process_loss_qty)
    # as having been closed via produced_qty + process_loss_qty reaching wo.qty
    # instead. Without the second clause, a Work Order that was legitimately
    # completed via loss reconciliation would never satisfy produced_qty >= qty
    # on its own, and this self-heal would incorrectly no-op forever for it.
    produced_reached_qty = flt(wo.produced_qty) >= flt(wo.qty) - 0.0001
    loss_reconciled_complete = (
        bool(wo.get("qty_reconciled_via_loss"))
        and (flt(wo.produced_qty) + flt(wo.process_loss_qty)) >= flt(wo.qty) - 0.0001
    )
    if not (produced_reached_qty or loss_reconciled_complete):
        return
    wo.db_set("status", "Completed")
    _set_operations_status(wo, "Completed")
    if wo.production_plan:
        from zoho_books_clone.manufacturing.production_plan_engine import maybe_complete_production_plan
        maybe_complete_production_plan(wo.production_plan)
    frappe.db.commit()


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_actual_absorbed_cost(work_order):
    """Return the actual (as opposed to planned/BOM-snapshot) cost absorbed
    into the finished good so far, for the Vue Cost Breakdown panel's
    Planned-vs-Actual comparison. Sums the finished-good receipt row's
    amount (qty * fg_unit_rate, which already nets raw material + operating
    cost - scrap credit, per complete_work_order()) across every submitted
    Manufacture Stock Entry linked to this Work Order.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    wo = _get_work_order(work_order)
    assert_doc_in_user_company(wo)

    rows = frappe.db.sql(
        """
        SELECT sed.amount
        FROM `tabStock Entry Detail` sed
        INNER JOIN `tabStock Entry` se ON se.name = sed.parent
        WHERE se.work_order = %s
          AND se.docstatus = 1
          AND se.stock_entry_type = 'Manufacture'
          AND sed.item_code = %s
          AND sed.t_warehouse IS NOT NULL AND sed.t_warehouse != ''
        """,
        (wo.name, wo.production_item),
        as_dict=True,
    )
    actual_cost = sum(flt(r.amount) for r in rows)

    # Abnormal process loss / scrap-shortfall write-offs (see
    # complete_work_order's manufacturing_variance_loss) -- summed across
    # every completion run so the Cost Breakdown panel can show the total
    # that was expensed rather than capitalized into FG cost, instead of
    # that figure sitting invisibly in the GL.
    variance_loss = flt(frappe.db.sql(
        """
        SELECT SUM(manufacturing_variance_loss)
        FROM `tabStock Entry`
        WHERE work_order = %s AND docstatus = 1 AND stock_entry_type = 'Manufacture'
        """,
        (wo.name,),
    )[0][0] or 0)

    return {
        "actual_cost": actual_cost,
        "produced_qty": flt(wo.produced_qty),
        "manufacturing_variance_loss": variance_loss,
    }


def _set_operations_status(wo, status, skip_statuses=None):
    """Bulk-update Work Order Operation rows to the given status.

    Each operation's status is also driven independently by its own Job
    Card (see job_card.py's _sync_wo_operation_status), which can put a row
    further ahead than this bulk update. Rows whose current status is in
    skip_statuses are left untouched so this call never downgrades progress
    that was already recorded elsewhere -- e.g. a Job Card marking an
    operation Completed shouldn't get silently reset to "In Process" just
    because materials were issued or another partial completion happened.
    """
    if not wo.operations:
        return
    skip_statuses = skip_statuses or set()
    for op in wo.operations:
        if op.status in skip_statuses:
            continue
        op.db_set("status", status, update_modified=False)


@frappe.whitelist(allow_guest=False, methods=["POST"])
def stop_work_order(work_order):
    """Mark a submitted Work Order as Stopped, preventing further material
    issue or completion until it is resumed."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Work Order", "write")

    wo = _get_work_order(work_order)
    assert_doc_in_user_company(wo)
    # Lock the row so a stop can't race a concurrent complete/resume call.
    frappe.db.sql("SELECT name FROM `tabWork Order` WHERE name=%s FOR UPDATE", (wo.name,))
    wo.reload()
    if wo.status in ("Completed", "Cancelled"):
        frappe.throw(_("Cannot stop a {0} Work Order.").format(wo.status))
    if wo.status == "Stopped":
        frappe.throw(_("Work Order is already stopped."))

    wo.db_set("status", "Stopped")
    _set_operations_status(wo, "Stopped", skip_statuses={"Completed"})
    frappe.db.commit()
    return "Stopped"


@frappe.whitelist(allow_guest=False, methods=["POST"])
def recalculate_operating_cost(work_order, refresh_hour_rates=False):
    """Recompute Planned/Actual/Total Operating Cost for a Work Order and
    write them via db_set.

    Needed because these fields normally only get freshly computed inside
    Work Order.validate() -- which a submitted Work Order stops going
    through for most of its lifecycle. complete_work_order() advances
    status/produced_qty with db_set() (bypassing validate() by design, so a
    completion can't be blocked by unrelated validation), and Job Card time
    roll-ups also write straight to the child row with db_set(). So a
    Work Order whose Operations table had hour_rate = 0 at the moment it was
    loaded from the BOM (e.g. the BOM's operation didn't have a rate set
    yet, or an older BOM version was used) stays stuck at
    ₹0.00 Operating Cost forever with no natural trigger to fix it --
    even after the BOM is corrected.

    refresh_hour_rates=True additionally re-pulls hour_rate from each row's
    linked Operation's current BOM Operation entry isn't tracked directly,
    so instead it re-reads the *current* Workstation.hour_rate for each row
    (the same source BOM.vue uses to auto-fill hour_rate) as a best-effort
    resync when the original BOM's rate was simply never captured. Leave
    this off to only recompute cost from whatever hour_rate is already
    stored on each row.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Work Order", "write")

    refresh_hour_rates = frappe.parse_json(refresh_hour_rates) if isinstance(refresh_hour_rates, str) else refresh_hour_rates

    wo = _get_work_order(work_order)
    assert_doc_in_user_company(wo)

    if refresh_hour_rates:
        for row in (wo.operations or []):
            if not row.workstation:
                continue
            ws_rate = frappe.db.get_value("Workstation", row.workstation, "hour_rate")
            if ws_rate:
                row.db_set("hour_rate", flt(ws_rate), update_modified=False)
        wo.reload()

    wo.calculate_operating_cost()
    wo.db_set("planned_operating_cost", wo.planned_operating_cost)
    wo.db_set("actual_operating_cost", wo.actual_operating_cost)
    wo.db_set("total_operating_cost", wo.total_operating_cost)
    frappe.db.commit()

    return {
        "planned_operating_cost": wo.planned_operating_cost,
        "actual_operating_cost": wo.actual_operating_cost,
        "additional_operating_cost": flt(wo.additional_operating_cost),
        "total_operating_cost": wo.total_operating_cost,
    }


def apply_row_substitution(work_order, work_order_item_row, alternative_item_code,
                            conversion_factor, reason):
    """Internal (non-whitelisted) helper — actually mutates a Work Order Item
    row to point at the alternative item, scaling required_qty by the
    conversion factor. Called either immediately (packaging/excipient path,
    no approval needed) or once a Material Substitution Log is approved
    (herb/active-ingredient path). Only allowed before any of that row's
    material has been consumed, so substitution never rewrites history for
    partially-consumed batches.

    Returns the updated row as a dict for the caller to report back.
    """
    wo = _get_work_order(work_order)
    assert_doc_in_user_company(wo)
    if wo.status in ("Completed", "Cancelled", "Stopped"):
        frappe.throw(_("Cannot substitute materials on a {0} Work Order.").format(wo.status))

    row = next((r for r in wo.items if r.name == work_order_item_row), None)
    if not row:
        frappe.throw(_("Work Order Item row {0} not found.").format(work_order_item_row))
    if flt(row.consumed_qty) > 0:
        frappe.throw(_(
            "{0} has already been partly or fully consumed on this Work Order "
            "and can no longer be substituted."
        ).format(row.item_code))

    alt_item = frappe.db.get_value(
        "Item", alternative_item_code, ["item_name", "stock_uom"], as_dict=True
    )
    if not alt_item:
        frappe.throw(_("Alternative item {0} does not exist.").format(alternative_item_code))

    original_item_code = row.original_item_code or row.item_code
    new_required_qty = flt(row.required_qty) * flt(conversion_factor or 1)

    # Recompute rate/amount against the alternative item's current valuation
    # rate (same convention _consume_qty_for_row/complete_work_order use at
    # actual-costing time) -- otherwise the row (and the Vue "Raw Material
    # Cost" total) keeps showing the replaced item's cost until the BOM is
    # reloaded. Purely a display/reporting fix; actual completion-time
    # costing already looks up its own rate fresh and is unaffected.
    s_wh = row.source_warehouse or wo.wip_warehouse or wo.source_warehouse
    new_rate = get_valuation_rate(alternative_item_code, s_wh) if s_wh else 0.0
    new_amount = new_rate * new_required_qty

    row.db_set("original_item_code", original_item_code, update_modified=False)
    row.db_set("item_code", alternative_item_code, update_modified=False)
    row.db_set("item_name", alt_item.item_name, update_modified=False)
    row.db_set("uom", alt_item.stock_uom, update_modified=False)
    row.db_set("required_qty", new_required_qty, update_modified=False)
    row.db_set("rate", new_rate, update_modified=False)
    row.db_set("amount", new_amount, update_modified=False)
    row.db_set("is_substituted", 1, update_modified=False)
    row.db_set("substitution_reason", reason or "", update_modified=False)
    frappe.db.commit()

    return {
        "work_order_item_row": row.name,
        "original_item_code": original_item_code,
        "alternative_item_code": alternative_item_code,
        "new_required_qty": new_required_qty,
        "new_rate": new_rate,
        "new_amount": new_amount,
    }


def _compute_scrap_split(current_required_qty, current_scrap_reused_qty, scrap_qty,
                          conversion_factor, max_substitution_pct):
    """Pure math for one partial-scrap-substitution call against a single
    Work Order Item row -- kept dependency-free (no frappe/DB access) so it
    can be unit-tested directly, the same way TestOverProductionAllowance/
    TestLossReconciliation replicate complete_work_order's arithmetic.

    conversion_factor is the Alternative Item mapping's factor: how many
    units of the scrap item are equivalent to 1 unit of the original raw
    material (same convention apply_row_substitution uses: new_required_qty
    = required_qty * conversion_factor). scrap_qty is given directly in the
    scrap item's own stock UOM (matching Bin.actual_qty / get_stock_by_warehouse),
    so it has to be converted back into the original item's UOM to know how
    much of the row's required_qty it actually displaces:

        original_equivalent_qty = scrap_qty / conversion_factor

    The row's full original requirement never changes across repeated
    calls: required_qty + scrap_reused_qty is an invariant (each call moves
    some of it from one side to the other), so max_substitution_pct is
    always enforced against that same baseline regardless of how many
    partial substitutions have already been applied to this row.

    Returns a dict with original_equivalent_qty / new_required_qty /
    new_scrap_reused_qty / max_allowed_scrap_reused_qty, or raises
    ValueError with a caller-friendly message if the request is invalid
    (caller wraps this in frappe.throw).
    """
    conversion_factor = 1.0 if conversion_factor is None else conversion_factor
    if conversion_factor <= 0:
        raise ValueError("Alternative Item conversion factor must be greater than zero.")
    if scrap_qty <= 0:
        raise ValueError("Scrap Qty must be greater than zero.")

    original_baseline = current_required_qty + current_scrap_reused_qty
    original_equivalent_qty = scrap_qty / conversion_factor

    max_pct = max_substitution_pct if max_substitution_pct and max_substitution_pct > 0 else 100.0
    max_allowed_scrap_reused_qty = original_baseline * max_pct / 100.0
    new_scrap_reused_qty = current_scrap_reused_qty + original_equivalent_qty

    if new_scrap_reused_qty > max_allowed_scrap_reused_qty + 0.0001:
        raise ValueError(
            f"This would let scrap cover {new_scrap_reused_qty:.4f} of "
            f"{original_baseline:.4f} required, exceeding the {max_pct:g}% "
            f"Max Substitution cap ({max_allowed_scrap_reused_qty:.4f})."
        )

    new_required_qty = current_required_qty - original_equivalent_qty
    if new_required_qty < -0.0001:
        raise ValueError(
            f"Scrap Qty {scrap_qty:.4f} is equivalent to {original_equivalent_qty:.4f} "
            f"of the original item, more than the {current_required_qty:.4f} still "
            f"required on this row."
        )

    return {
        "original_equivalent_qty": original_equivalent_qty,
        "new_required_qty": max(new_required_qty, 0.0),
        "new_scrap_reused_qty": new_scrap_reused_qty,
        "max_allowed_scrap_reused_qty": max_allowed_scrap_reused_qty,
    }


def _resolve_scrap_warehouse(scrap_item_code, company, scrap_qty, preferred_warehouse=None):
    """Pick a single warehouse to draw `scrap_qty` of `scrap_item_code`
    from. A Work Order Item row carries exactly one source_warehouse, so
    the new scrap-split row has to be satisfiable from one warehouse --
    unlike get_substitution_options' informational available_qty (which
    sums across every warehouse), this has to actually pick one.

    QC gate (Phase 8): a company's configured RM/FG quarantine warehouse(s)
    are excluded from consideration entirely, even if they physically hold
    enough qty. Recovered scrap items flagged
    inspection_required_before_manufacture get routed into quarantine at
    receipt (see qc_engine.auto_create_qc_for_stock_entry's scrap-row
    branch) precisely so they can't be reused until QC passes -- letting
    this function still pick a quarantine warehouse because it happens to
    have the qty would silently defeat that gate.

    Preference order:
      1. preferred_warehouse (the Work Order's own scrap_warehouse, if set)
         -- kept even if it doesn't have enough, PROVIDED nothing else does
         either, so the error message points at the warehouse the person
         actually expected to draw from.
      2. Any warehouse (highest qty first, per get_stock_by_warehouse's own
         ordering) that alone covers scrap_qty.

    Returns (warehouse, valuation_rate). Throws if nothing covers it.
    """
    from zoho_books_clone.inventory.utils import get_stock_by_warehouse
    from zoho_books_clone.quality.qc_hold_manager import _is_quarantine_warehouse

    warehouses = [
        w for w in get_stock_by_warehouse(scrap_item_code, company)
        if not _is_quarantine_warehouse(w["warehouse"], company)
    ]
    by_name = {w["warehouse"]: w for w in warehouses}

    if preferred_warehouse and not _is_quarantine_warehouse(preferred_warehouse, company) \
            and by_name.get(preferred_warehouse, {}).get("qty", 0) >= scrap_qty:
        w = by_name[preferred_warehouse]
        return w["warehouse"], flt(w["valuation_rate"])

    for w in warehouses:
        if flt(w["qty"]) >= scrap_qty:
            return w["warehouse"], flt(w["valuation_rate"])

    total_available = sum(flt(w["qty"]) for w in warehouses)
    frappe.throw(_(
        "Not enough {0} in stock in any single warehouse to cover {1} (stock "
        "sitting in QC quarantine doesn't count -- it hasn't passed inspection "
        "yet). Total available outside quarantine across all warehouses: {2}."
    ).format(scrap_item_code, scrap_qty, total_available))


def apply_partial_scrap_substitution(work_order, work_order_item_row, scrap_item_code,
                                      scrap_qty, reason):
    """Scrap Reuse feature, Phase 3 -- the partial reuse engine.

    Splits a Work Order Item row so PART of its required qty is filled from
    previously-recovered scrap (drawn from the Scrap Warehouse) while the
    rest stays on the original raw material, instead of apply_row_substitution's
    all-or-nothing whole-row swap. Two Work Order Item rows come out of
    this:

      - the ORIGINAL row, `required_qty` reduced by however much of it the
        scrap displaces (item_code unchanged);
      - a NEW row for the scrap portion: item_code = scrap_item_code,
        required_qty = scrap_qty, source_warehouse = wherever the scrap was
        drawn from, is_scrap_row = 1.

    Both rows share `substitution_group` (the original row's own name) so
    reporting/UI can reassemble "how much of this requirement came from
    scrap vs. fresh stock" even after several calls against the same row.

    Can be called more than once against the same original row (e.g. more
    scrap becomes available later) -- each call further reduces the
    original row's required_qty and adds/tops up scrap. Reuses the same
    guards as apply_row_substitution (no completed/cancelled/stopped WO, no
    already-consumed material) plus an extra transferred_qty guard: once
    material has been staged into WIP for this row, splitting it would
    misattribute that transfer between the resulting rows, so it's blocked
    the same way consumed_qty already is.

    Returns a dict describing both rows for the caller to report back.
    """
    wo = _get_work_order(work_order)
    assert_doc_in_user_company(wo)
    if wo.status in ("Completed", "Cancelled", "Stopped"):
        frappe.throw(_("Cannot substitute materials on a {0} Work Order.").format(wo.status))

    ms = _get_mfg_settings()
    if not ms.get("enable_scrap_reuse", 1):
        frappe.throw(_(
            "Scrap Reuse is currently disabled company-wide (Manufacturing Settings "
            "\u2192 Enable Scrap Reuse). Ask a Books Admin to turn it back on, or use "
            "Substitute Material for a Fresh Stock alternative instead."
        ))

    row = next((r for r in wo.items if r.name == work_order_item_row), None)
    if not row:
        frappe.throw(_("Work Order Item row {0} not found.").format(work_order_item_row))
    if row.is_scrap_row:
        frappe.throw(_(
            "{0} is itself a scrap-sourced row (split off from another row). "
            "Select the original raw-material row to reuse more scrap against it."
        ).format(row.item_code))
    if flt(row.consumed_qty) > 0:
        frappe.throw(_(
            "{0} has already been partly or fully consumed on this Work Order "
            "and can no longer be split for scrap reuse."
        ).format(row.item_code))
    if flt(row.transferred_qty) > 0:
        frappe.throw(_(
            "{0} has already been transferred to WIP on this Work Order. Reusing "
            "scrap against it now would misattribute that transfer between the "
            "resulting rows -- reuse scrap before issuing materials for this row."
        ).format(row.item_code))

    scrap_qty = flt(scrap_qty)
    original_item_code = row.original_item_code or row.item_code

    mapping = frappe.db.get_value(
        "Alternative Item",
        {"item_code": original_item_code, "alternative_item_code": scrap_item_code},
        ["conversion_factor", "source_type", "max_substitution_pct"],
        as_dict=True,
    )
    if not mapping:
        frappe.throw(_(
            "{0} is not a defined Alternative Item for {1}. Add it under "
            "Manufacturing > Alternative Items first."
        ).format(scrap_item_code, original_item_code))
    if mapping.source_type != "Recycled Scrap":
        frappe.throw(_(
            "{0} is mapped as a Fresh Stock alternative for {1}, not Recycled "
            "Scrap. Use Substitute Material for a fresh-stock swap instead."
        ).format(scrap_item_code, original_item_code))

    try:
        split = _compute_scrap_split(
            current_required_qty=flt(row.required_qty),
            current_scrap_reused_qty=flt(row.scrap_reused_qty),
            scrap_qty=scrap_qty,
            conversion_factor=flt(mapping.conversion_factor),
            max_substitution_pct=flt(mapping.max_substitution_pct),
        )
    except ValueError as e:
        frappe.throw(_(str(e)))

    preferred_wh = wo.scrap_warehouse or _get_mfg_settings().get("default_scrap_warehouse")
    scrap_wh, scrap_rate = _resolve_scrap_warehouse(
        scrap_item_code, wo.company, scrap_qty, preferred_warehouse=preferred_wh
    )

    scrap_item = frappe.db.get_value(
        "Item", scrap_item_code, ["item_name", "stock_uom"], as_dict=True
    )
    if not scrap_item:
        frappe.throw(_("Scrap item {0} does not exist.").format(scrap_item_code))

    # Original row: shrink required_qty by whatever the scrap displaces,
    # keep its existing rate (the fresh-material rate hasn't changed), and
    # record the running total so a later call's max_substitution_pct check
    # is against the row's true original baseline, not just what's left.
    new_amount = flt(row.rate) * split["new_required_qty"]
    group_key = row.substitution_group or row.name
    row.db_set("required_qty", split["new_required_qty"], update_modified=False)
    row.db_set("amount", new_amount, update_modified=False)
    row.db_set("scrap_reused_qty", split["new_scrap_reused_qty"], update_modified=False)
    row.db_set("is_substituted", 1, update_modified=False)
    row.db_set("substitution_reason", reason or "", update_modified=False)
    row.db_set("substitution_group", group_key, update_modified=False)

    # New scrap-split row. Table field on Work Order isn't allow_on_submit,
    # so appending to it post-submit needs ignore_validate_update_after_submit
    # -- same pattern production_plan_engine.py uses for mr_items.
    scrap_amount = scrap_rate * scrap_qty
    new_row = wo.append("items", {
        "item_code": scrap_item_code,
        "item_name": scrap_item.item_name,
        "uom": scrap_item.stock_uom,
        "required_qty": scrap_qty,
        "source_warehouse": scrap_wh,
        "rate": scrap_rate,
        "amount": scrap_amount,
        "original_item_code": original_item_code,
        "is_scrap_row": 1,
        "is_substituted": 1,
        "substitution_reason": reason or "",
        "substitution_group": group_key,
        # Carry over the original row's sub-assembly origin(s) so the split-
        # off scrap row still groups under the right sub-assembly in
        # WorkOrder.vue's groupedWoItems (see _merge_duplicate_rows) instead
        # of always falling into "Direct Raw Materials" -- it's the same
        # requirement, just partially resourced from scrap.
        "sub_assembly_boms": row.sub_assembly_boms or "",
        # Same reasoning -- carry the qty breakdown text as-is so the split-
        # off row still shows under the right sub-assembly group(s). Not
        # re-proportioned to the smaller scrap_qty; it's informational only.
        "sub_assembly_qty_breakdown": row.sub_assembly_qty_breakdown or "",
    })
    wo.flags.ignore_validate_update_after_submit = True
    wo.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "original_row": {
            "work_order_item_row": row.name,
            "item_code": row.item_code,
            "new_required_qty": split["new_required_qty"],
            "new_amount": new_amount,
            "scrap_reused_qty": split["new_scrap_reused_qty"],
        },
        "scrap_row": {
            "work_order_item_row": new_row.name,
            "item_code": scrap_item_code,
            "required_qty": scrap_qty,
            "source_warehouse": scrap_wh,
            "rate": scrap_rate,
            "amount": scrap_amount,
        },
        "substitution_group": group_key,
    }


def _wo_items_for_reversal(wo, item_code, warehouse_hint):
    """Find the Work Order Item row(s) a Stock Entry row should be rolled
    back against.

    Matching purely by item_code (as reverse_material_issue and
    reverse_manufacture_entry used to) silently misattributes to whichever
    row happens to appear FIRST whenever a Work Order has more than one raw
    material row for the same item -- a supported case, since each row can
    carry its own source_warehouse (see WorkOrder.validate()) and
    WorkOrder.vue's "+ Add Material" has no dedup. Narrowing by warehouse
    first resolves the common case; if that's still ambiguous (e.g.
    consumption routed every row through a shared WIP warehouse), the
    caller splits the quantity proportionally across all matches instead of
    dumping it all on one row.
    """
    candidates = [r for r in wo.items if r.item_code == item_code]
    if len(candidates) <= 1:
        return candidates
    narrowed = [
        r for r in candidates
        if (r.source_warehouse or wo.source_warehouse) == warehouse_hint
    ]
    return narrowed if len(narrowed) == 1 else candidates


def _rollback_qty_across_rows(matches, total_qty, field):
    """Subtract total_qty from `field` (transferred_qty / consumed_qty)
    across one or more matched rows, weighted by required_qty when more
    than one row matches -- see _wo_items_for_reversal."""
    if not matches:
        return
    if len(matches) == 1:
        row = matches[0]
        current = flt(getattr(row, field))
        row.db_set(field, max(current - flt(total_qty), 0), update_modified=False)
        return
    total_weight = sum(flt(r.required_qty) for r in matches) or len(matches)
    for row in matches:
        weight = (flt(row.required_qty) / total_weight) if total_weight else (1.0 / len(matches))
        share = flt(total_qty) * weight
        current = flt(getattr(row, field))
        row.db_set(field, max(current - share, 0), update_modified=False)


@frappe.whitelist(allow_guest=False, methods=["POST"])
def resume_work_order(work_order):
    """Resume a previously stopped Work Order, restoring it to In Process
    (or Submitted if no production has been recorded yet)."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Work Order", "write")

    wo = frappe.get_doc("Work Order", work_order)
    if wo.docstatus != 1:
        frappe.throw(_("Work Order must be submitted."))
    # Lock the row so a resume can't race a concurrent stop/complete call.
    frappe.db.sql("SELECT name FROM `tabWork Order` WHERE name=%s FOR UPDATE", (wo.name,))
    wo.reload()
    if wo.status != "Stopped":
        frappe.throw(_("Work Order is not stopped."))

    resume_status = "In Process" if flt(wo.produced_qty) > 0 else "Submitted"
    wo.db_set("status", resume_status)
    # Operation rows don't have a "Submitted" state (only Pending/In Process/
    # Completed/Stopped) — Pending is the equivalent starting point. Either
    # way, never downgrade a row a Job Card already marked Completed.
    _set_operations_status(
        wo, "In Process" if resume_status == "In Process" else "Pending",
        skip_statuses={"Completed"},
    )
    frappe.db.commit()
    return resume_status

@frappe.whitelist(allow_guest=False, methods=["POST"])
def reverse_material_issue(work_order, stock_entry):
    """Undo a Material Transfer created by issue_materials(): cancels the
    Stock Entry (reversing the WIP stock movement) and rolls back
    transferred_qty on the affected Work Order Item rows so they go back
    to being "pending" for a future issue.

    Only allowed if none of the transferred material has been consumed yet
    (consumed_qty == 0 on every affected row) -- otherwise the WIP stock
    this transfer put in place may already be gone into a Manufacture
    entry, and reversing it here would leave that completion unbacked.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Stock Entry", "cancel")

    wo = frappe.get_doc("Work Order", work_order)
    if wo.docstatus != 1:
        frappe.throw(_("Work Order must be submitted."))
    assert_doc_in_user_company(wo)

    se = frappe.get_doc("Stock Entry", stock_entry)
    if se.docstatus != 1:
        frappe.throw(_("Stock Entry {0} is not submitted.").format(se.name))
    if se.stock_entry_type != "Material Transfer" or se.work_order != wo.name:
        frappe.throw(_(
            "Stock Entry {0} is not a Material Transfer linked to Work Order {1}."
        ).format(se.name, wo.name))

    frappe.db.sql("SELECT name FROM `tabWork Order` WHERE name=%s FOR UPDATE", (wo.name,))
    wo.reload()

    affected = [row for row in se.items if row.t_warehouse == wo.wip_warehouse]
    for row in affected:
        matches = _wo_items_for_reversal(wo, row.item_code, row.s_warehouse)
        if any(flt(m.consumed_qty) > 0 for m in matches):
            frappe.throw(_(
                "Cannot reverse: {0} transferred by this entry has already been "
                "partly or fully consumed against this Work Order."
            ).format(row.item_code))

    se.flags.ignore_manufacturing_guard = True
    se.cancel()

    for row in affected:
        matches = _wo_items_for_reversal(wo, row.item_code, row.s_warehouse)
        _rollback_qty_across_rows(matches, row.qty, "transferred_qty")

    still_transferred = any(
        flt(frappe.db.get_value("Work Order Item", r.name, "transferred_qty")) > 0
        for r in wo.items
    )
    if wo.status == "In Process" and flt(wo.produced_qty) <= 0 and not still_transferred:
        wo.db_set("status", "Submitted")
        _set_operations_status(wo, "Pending", skip_statuses={"Completed"})

    frappe.db.commit()
    return "Reversed"


@frappe.whitelist(allow_guest=False, methods=["POST"])
def reverse_manufacture_entry(work_order, stock_entry):
    """Undo a completion recorded by complete_work_order(): cancels the
    Manufacture Stock Entry (reversing both the raw-material consumption
    and the finished-goods/scrap receipt) and rolls back produced_qty,
    each affected row's consumed_qty, and operating_cost_absorbed_total on
    the Work Order.

    Only the most recent Manufacture Stock Entry for this Work Order can be
    reversed -- reversing an earlier one out of order would leave
    produced_qty/consumed_qty inconsistent with completions recorded after
    it. Reverse later completions first if there are any.

    operating_cost_absorbed_total IS rolled back (by the reversed entry's
    own operating_cost_absorbed) even though the GL reversal from se.cancel()
    is already exact on its own -- this field feeds the final-run true-up in
    complete_work_order (operating_cost_this_run = current_total_operating_cost
    - current_operating_cost_absorbed_total), so leaving it stale would
    under-absorb operating cost into whatever completion replaces this one.

    process_loss_qty IS rolled back (by the reversed entry's own
    process_loss_qty, stored on the Stock Entry for exactly this purpose).
    It never moved any stock on its own, so the stock ledger was never at
    risk either way -- but close_on_loss_reconciliation completions
    (complete_work_order) read cumulative process_loss_qty to decide both
    the over-consumption block and the is_final OR-clause, so leaving it
    stale here would let a reversed run's loss keep counting against future
    completions.

    over_production_qty IS rolled back too (by the reversed entry's own
    over_production_qty, stored on the Stock Entry the same way
    process_loss_qty is). It never moved any stock on its own either -- but
    it's the cumulative figure any over-production reporting reads, so
    leaving it stale here would permanently overstate a Work Order's
    over-production after the very run that caused it is reversed.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Stock Entry", "cancel")

    wo = frappe.get_doc("Work Order", work_order)
    if wo.docstatus != 1:
        frappe.throw(_("Work Order must be submitted."))
    assert_doc_in_user_company(wo)

    se = frappe.get_doc("Stock Entry", stock_entry)
    if se.docstatus != 1:
        frappe.throw(_("Stock Entry {0} is not submitted.").format(se.name))
    if se.stock_entry_type != "Manufacture" or se.work_order != wo.name:
        frappe.throw(_(
            "Stock Entry {0} is not a Manufacture entry linked to Work Order {1}."
        ).format(se.name, wo.name))

    frappe.db.sql("SELECT name FROM `tabWork Order` WHERE name=%s FOR UPDATE", (wo.name,))
    wo.reload()

    later = frappe.get_all(
        "Stock Entry",
        filters={
            "work_order": wo.name,
            "stock_entry_type": "Manufacture",
            "docstatus": 1,
            "creation": [">", se.creation],
        },
        limit=1,
    )
    if later:
        frappe.throw(_(
            "A later completion ({0}) exists for this Work Order. Reverse it first."
        ).format(later[0].name))

    qty_manufactured = sum(
        flt(r.qty) for r in se.items
        if r.item_code == wo.production_item and r.t_warehouse
    )
    consumption_rows = [r for r in se.items if r.s_warehouse]
    # Captured before se.cancel() -- cancel() doesn't clear the Stock Entry's
    # own fields, but read it now regardless so this doesn't depend on that.
    operating_cost_absorbed_this_entry = flt(se.operating_cost_absorbed)
    process_loss_qty_this_entry = flt(se.process_loss_qty)
    over_production_qty_this_entry = flt(se.over_production_qty)

    se.flags.ignore_manufacturing_guard = True
    se.cancel()

    for row in consumption_rows:
        matches = _wo_items_for_reversal(wo, row.item_code, row.s_warehouse)
        _rollback_qty_across_rows(matches, row.qty, "consumed_qty")

    new_produced_qty = max(flt(wo.produced_qty) - qty_manufactured, 0)
    wo.db_set("produced_qty", new_produced_qty)

    # Roll back this run's contribution to process_loss_qty too. This never
    # moved any stock on its own, but close_on_loss_reconciliation completions
    # (complete_work_order) now read cumulative process_loss_qty to decide
    # both the over-consumption block and the is_final OR-clause -- leaving
    # it stale here would let a reversed run's loss keep counting against
    # future completions, wrongly blocking a fresh attempt at the full
    # planned qty or marking the Work Order reconciled too early.
    new_process_loss_qty = max(flt(wo.process_loss_qty) - process_loss_qty_this_entry, 0)
    wo.db_set("process_loss_qty", new_process_loss_qty)

    # Roll back this run's contribution to over_production_qty too. This
    # never moved any stock on its own (see material_basis_qty in
    # complete_work_order), but it's the cumulative figure any over-production
    # reporting reads -- leaving it stale here would permanently overstate
    # how much a Work Order actually over-produced after a reversal undoes
    # the very run that caused it.
    new_over_production_qty = max(flt(wo.over_production_qty) - over_production_qty_this_entry, 0)
    wo.db_set("over_production_qty", new_over_production_qty)

    # Defensive check for pre-migration data the v1_11 backfill couldn't
    # fully resolve: if this reversal leaves process_loss_qty > 0 on the
    # Work Order but there are no OTHER submitted Manufacture entries left
    # to account for it (i.e. this really did look like the entry that
    # should have carried all of it, yet a remainder persists), the stored
    # figure is unreliable rather than wrong-but-explainable. Flag it for
    # manual review instead of letting it silently keep influencing future
    # over-consumption / is_final checks in complete_work_order.
    if new_process_loss_qty > 0.0001:
        remaining_entries = frappe.get_all(
            "Stock Entry",
            filters={
                "work_order": wo.name,
                "stock_entry_type": "Manufacture",
                "docstatus": 1,
                "name": ["!=", se.name],
            },
            limit=1,
        )
        if not remaining_entries:
            frappe.msgprint(_(
                "Work Order {0} still shows {1} of process loss after this reversal, "
                "but no other completion remains to account for it. This likely predates "
                "per-entry process-loss tracking and could not be fully attributed by the "
                "v1_11 backfill -- please review process_loss_qty on this Work Order manually."
            ).format(wo.name, new_process_loss_qty), indicator="orange", alert=True)

    # Without this, the next completion's final-run true-up (complete_work_order:
    # operating_cost_this_run = current_total_operating_cost -
    # current_operating_cost_absorbed_total) reads a stale, too-high absorbed
    # total left over from the reversed run and under-absorbs operating cost
    # into the corrected completion -- silently misstating FG/WIP valuation
    # even though the GL reversal itself (via se.cancel() above) is exact.
    new_operating_cost_absorbed_total = max(
        flt(wo.operating_cost_absorbed_total) - operating_cost_absorbed_this_entry, 0
    )
    wo.db_set("operating_cost_absorbed_total", new_operating_cost_absorbed_total)

    still_transferred = any(flt(r.transferred_qty) > 0 for r in wo.items)
    new_status = "In Process" if (new_produced_qty > 0 or still_transferred) else "Submitted"
    wo.db_set("status", new_status)
    _set_operations_status(
        wo, "In Process" if new_status == "In Process" else "Pending",
        skip_statuses={"Completed"},
    )

    # This reversal always moves status away from "Completed", so any
    # qty_reconciled_via_loss stamp from the reversed run is now stale --
    # without clearing it, a later unrelated self-heal call (e.g. from the
    # QC-pass release path, triggered by some other QC Inspection entirely)
    # could read the leftover flag and incorrectly re-mark this Work Order
    # Completed even though the run that earned that flag was just undone.
    if wo.get("qty_reconciled_via_loss"):
        wo.db_set("qty_reconciled_via_loss", 0)

    frappe.db.commit()
    return "Reversed"