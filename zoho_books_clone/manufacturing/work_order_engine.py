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
from zoho_books_clone.inventory.utils import get_valuation_rate, get_conversion_factor


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
    for r in rows:
        key = (r["item_code"], r.get("source_warehouse") or "")
        origin = r.get("sub_assembly_bom") or ""
        if key not in merged:
            m = dict(r)
            m["sub_assembly_boms"] = [origin] if origin else []
            merged[key] = m
            order.append(key)
        else:
            m = merged[key]
            m["required_qty"] = flt(m["required_qty"]) + flt(r["required_qty"])
            m["amount"] = flt(m["amount"]) + flt(r["amount"])
            # Keep rate consistent with the merged qty/amount -- otherwise
            # rate keeps the first occurrence's value while amount reflects
            # both, so rate * required_qty != amount for merged rows.
            m["rate"] = m["amount"] / m["required_qty"] if m["required_qty"] else 0.0
            if origin and origin not in m["sub_assembly_boms"]:
                m["sub_assembly_boms"].append(origin)
    for k in order:
        merged[k].pop("sub_assembly_bom", None)
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
    and this step can be skipped entirely."""
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

    se = frappe.new_doc("Stock Entry")
    se.company = wo.company
    se.stock_entry_type = "Material Transfer"
    se.posting_date = nowdate()
    se.work_order = wo.name
    se.remarks = f"Material issue for Work Order {wo.name}"

    for row in wo.items:
        pending = flt(row.required_qty) - flt(row.transferred_qty)
        if pending <= 0:
            continue
        se.append("items", {
            "item_code": row.item_code,
            "qty": pending,
            "s_warehouse": row.source_warehouse or wo.source_warehouse,
            "t_warehouse": wo.wip_warehouse,
        })

    if not se.items:
        frappe.throw(_("All raw materials have already been issued for this Work Order."))

    se.insert(ignore_permissions=True)
    se.submit()

    for row in wo.items:
        row.db_set("transferred_qty", flt(row.required_qty), update_modified=False)
    if wo.status == "Submitted":
        wo.db_set("status", "In Process")
    _set_operations_status(wo, "In Process", skip_statuses={"Completed"})
    frappe.db.commit()

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
                         manufacturing_date=None, expiry_date=None):
    """Create & submit the Manufacture Stock Entry for a batch of production
    against this Work Order. Can be called multiple times for partial
    completions until produced_qty reaches the planned qty.

    qty_manufactured  -- finished-good qty actually produced this run
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
    if qty_manufactured <= 0:
        frappe.throw(_("Quantity Manufactured must be greater than zero."))

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
    max_allowed = flt(wo.qty) * (1.0 + over_pct / 100.0)
    new_total = current_produced_qty + qty_manufactured
    if new_total > max_allowed + 0.0001:
        if over_pct > 0:
            frappe.throw(_(
                "Total produced qty ({0}) would exceed the planned qty ({1}) plus the "
                "{2}% over-production allowance (max {3})."
            ).format(new_total, wo.qty, over_pct, max_allowed))
        else:
            frappe.throw(_(
                "Quantity Manufactured ({0}) exceeds the remaining planned qty ({1}). "
                "Increase Over-Production Allowance % in Manufacturing Settings to allow this."
            ).format(qty_manufactured, flt(wo.qty) - current_produced_qty))

    # Whether this run brings the Work Order to full completion -- computed
    # up front (rather than re-derived after the Stock Entry is posted) so
    # both the operating-cost true-up and the process-loss split below can
    # use it while building this run's Stock Entry.
    is_final = new_total >= flt(wo.qty) - 0.0001


    # Raw materials are consumed for the FULL quantity that left the
    # process -- both what became finished stock (qty_manufactured) and
    # what was lost in-process (process_loss_qty, e.g. evaporation/trimming/
    # spillage). Scaling consumption by qty_manufactured alone would under-
    # consume raw material stock any time there's process loss, leaving
    # material "in stock" on paper that was actually used up on the floor.
    consumption_ratio = (qty_manufactured + process_loss_qty) / flt(wo.qty or 1)

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
    # material cost is. Uses consumption_ratio (qty_manufactured +
    # process_loss_qty, scaled against wo.qty) rather than qty_manufactured
    # alone -- the time/labor behind process_loss_qty was genuinely spent
    # too, same reasoning as why raw material consumption already includes
    # it (see consumption_ratio above), so operating cost should absorb into
    # the FG that did come out on the same basis, not be under-applied.
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
    expected_loss_qty_this_run = flt(wo.process_loss_percent) / 100.0 * qty_manufactured
    abnormal_loss_qty = max(0.0, process_loss_qty - expected_loss_qty_this_run)
    total_consumed_qty_this_run = qty_manufactured + process_loss_qty
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

    new_produced_qty = current_produced_qty + qty_manufactured
    wo.db_set("produced_qty", new_produced_qty)
    wo.db_set("process_loss_qty", current_process_loss_qty + process_loss_qty)
    wo.db_set("operating_cost_absorbed_total", current_operating_cost_absorbed_total + operating_cost_this_run)
    is_complete = is_final
    wo.db_set("status", "Completed" if is_complete else "In Process")
    if is_complete:
        # Work Order is fully done -- finalize every operation as Completed,
        # even if a Job Card lagged behind (e.g. someone forgot to close the
        # last Job Card). This is the one point where forcing the status is
        # correct, since there's no more production left to track against it.
        _set_operations_status(wo, "Completed")
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

    return se.name


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

    process_loss_qty is not rolled back: it never moved any stock (it's a
    reporting-only figure for material that was consumed but never became
    stock), so leaving it as-is doesn't desync anything against the stock
    ledger.
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

    se.flags.ignore_manufacturing_guard = True
    se.cancel()

    for row in consumption_rows:
        matches = _wo_items_for_reversal(wo, row.item_code, row.s_warehouse)
        _rollback_qty_across_rows(matches, row.qty, "consumed_qty")

    new_produced_qty = max(flt(wo.produced_qty) - qty_manufactured, 0)
    wo.db_set("produced_qty", new_produced_qty)

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

    frappe.db.commit()
    return "Reversed"