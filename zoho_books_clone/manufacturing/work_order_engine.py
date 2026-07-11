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
from zoho_books_clone.inventory.utils import get_valuation_rate


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
         and actually built against this item — guards against a stale
         link left over from a re-typed item or a cancelled/deactivated BOM).
      2. Otherwise, the most recently modified submitted+active BOM for this
         item (preferring one flagged is_default), matching the same lookup
         InventoryItems.vue uses to populate its own BOM picker.
      3. None, if the item has no usable BOM yet.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    if not item_code or not frappe.db.exists("Item", item_code):
        return {"bom": "", "source": "none"}

    default_bom = frappe.db.get_value("Item", item_code, "default_bom")
    if default_bom and frappe.db.exists("BOM", default_bom):
        bom_row = frappe.db.get_value(
            "BOM", default_bom, ["item", "docstatus", "is_active"], as_dict=True
        )
        if bom_row and bom_row.item == item_code and bom_row.docstatus == 1 and bom_row.is_active:
            return {"bom": default_bom, "source": "item_default"}

    fallback = frappe.get_all(
        "BOM",
        filters={"item": item_code, "docstatus": 1, "is_active": 1},
        fields=["name"],
        order_by="is_default desc, modified desc",
        limit=1,
    )
    if fallback:
        return {"bom": fallback[0].name, "source": "fallback"}

    return {"bom": "", "source": "none"}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_bom_breakdown(bom, qty):
    """Preview the raw-material & operation rows a Work Order would get from
    this BOM at the given quantity. Read-only — does not save anything.

    Handles three BOM types:
      Manufacturing  — standard flat material list; rows with a sub_assembly_bom
                       are recursively exploded (max 5 levels deep) so the Work
                       Order sees only leaf raw materials.
      Sub-Assembly   — treated identically to Manufacturing in this context.
      Packing        — materials are packing_items + the bulk_item consumed at
                       bulk_qty_per_unit per packed unit.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    bom_doc = frappe.get_doc("BOM", bom)
    if bom_doc.docstatus != 1:
        frappe.throw(_("Only a submitted BOM can be used on a Work Order."))

    ms = _get_mfg_settings()
    ratio = flt(qty) / flt(bom_doc.quantity or 1)

    if bom_doc.bom_type == "Packing":
        items = _explode_packing_bom(bom_doc, ratio)
    else:
        # Manufacturing or Sub-Assembly
        items = _explode_bom_items(bom_doc.items, ratio, depth=0)
        items = _merge_duplicate_rows(items)

    operations = [{
        "operation": r.operation,
        "workstation": r.workstation,
        "planned_time_in_mins": flt(r.time_in_mins) * ratio,
        "hour_rate": flt(r.hour_rate),
        "cost": flt(r.cost) * ratio,
    } for r in bom_doc.operations]

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


def _explode_bom_items(rows, ratio, depth=0, _seen_boms=None):
    """Recursively flatten BOM Item rows up to MAX_DEPTH levels deep.

    Rows are exploded (replaced by their own sub-components) when either:
    a) the row has an explicit ``sub_assembly_bom`` link, OR
    b) the item has a phantom BOM (is_phantom_bom=1) — phantom sub-assemblies
       are always exploded because they are never stocked/issued as a separate
       intermediate item.

    All other rows pass through as-is (leaf raw materials).
    """
    MAX_DEPTH = 5
    if _seen_boms is None:
        _seen_boms = set()

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
                    sub_items = _explode_bom_items(sub_doc.items, sub_ratio, depth + 1, _seen_boms)
                    result.extend(sub_items)
                    continue
            except Exception:
                pass  # If sub-BOM can't be loaded, fall through to include item as-is

        result.append({
            "item_code": r.item_code,
            "item_name": r.item_name,
            "required_qty": flt(r.qty) * ratio,
            "uom": r.uom,
            "rate": flt(r.rate),
            "amount": flt(r.rate) * flt(r.qty) * ratio,
            "source_warehouse": r.source_warehouse or "",
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
    a single merged row would correctly have blocked.
    """
    merged = {}
    order = []
    for r in rows:
        key = (r["item_code"], r.get("source_warehouse") or "")
        if key not in merged:
            merged[key] = dict(r)
            order.append(key)
        else:
            m = merged[key]
            m["required_qty"] = flt(m["required_qty"]) + flt(r["required_qty"])
            m["amount"] = flt(m["amount"]) + flt(r["amount"])
    return [merged[k] for k in order]


def _explode_packing_bom(bom_doc, ratio):
    """For Packing BOMs, the consumed materials are:
    1. The bulk item at bulk_qty_per_unit × ratio.
    2. All packing_items rows scaled by ratio.
    """
    result = []
    if bom_doc.bulk_item and flt(bom_doc.bulk_qty_per_unit) > 0:
        bulk_name = frappe.db.get_value("Item", bom_doc.bulk_item, "item_name") or bom_doc.bulk_item
        bulk_uom = frappe.db.get_value("Item", bom_doc.bulk_item, "stock_uom") or ""
        result.append({
            "item_code": bom_doc.bulk_item,
            "item_name": bulk_name,
            "required_qty": flt(bom_doc.bulk_qty_per_unit) * ratio,
            "uom": bulk_uom,
            "rate": 0.0,
            "amount": 0.0,
            "source_warehouse": "",
        })
    for r in (bom_doc.packing_items or []):
        result.append({
            "item_code": r.item_code,
            "item_name": r.item_name,
            "required_qty": flt(r.qty) * ratio,
            "uom": r.uom,
            "rate": flt(r.rate),
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


@frappe.whitelist(allow_guest=False, methods=["POST"])
def complete_work_order(work_order, qty_manufactured, process_loss_qty=0,
                         scrap_items=None, batch_no=None,
                         manufacturing_date=None, expiry_date=None):
    """Create & submit the Manufacture Stock Entry for a batch of production
    against this Work Order. Can be called multiple times for partial
    completions until produced_qty reaches the planned qty.

    qty_manufactured  -- finished-good qty actually produced this run
    process_loss_qty  -- material that never became stock (evaporation,
                         trimming, spillage etc.) — logged for yield
                         reporting only, no stock movement
    scrap_items       -- optional list of {item_code, qty} recoverable
                         by-products that DO get a stock movement into
                         scrap_warehouse
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Stock Entry", "write")

    if isinstance(scrap_items, str):
        scrap_items = frappe.parse_json(scrap_items)
    scrap_items = scrap_items or []

    wo = _get_work_order(work_order)
    assert_doc_in_user_company(wo)
    if wo.status == "Stopped":
        frappe.throw(_("Work Order is stopped. Resume it before recording completion."))

    qty_manufactured = flt(qty_manufactured)
    process_loss_qty = flt(process_loss_qty)
    if qty_manufactured <= 0:
        frappe.throw(_("Quantity Manufactured must be greater than zero."))

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
        consume_qty = flt(row.required_qty) * consumption_ratio
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
        s_qty = flt(s.get("qty"))
        if s_qty <= 0 or not s.get("item_code"):
            continue
        s_rate = flt(s.get("rate"))
        if not s_rate:
            s_rate = get_valuation_rate(s["item_code"], scrap_warehouse)
        total_scrap_value += s_qty * s_rate
        scrap_rows_to_append.append((s, s_qty, s_rate))

    # Whatever consumed cost is left after crediting out scrap value gets
    # spread across the qty actually manufactured this run. This also
    # absorbs the cost of any process_loss_qty (that material was consumed
    # too, per consumption_ratio above, but never became stock of its own)
    # into the finished good that did come out -- the standard costing
    # treatment for in-process loss.
    fg_unit_rate = 0.0
    if qty_manufactured > 0:
        fg_unit_rate = max(total_consumed_cost - total_scrap_value, 0.0) / qty_manufactured

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
        scrap_row = {"item_code": s["item_code"], "qty": s_qty, "t_warehouse": scrap_warehouse, "basic_rate": s_rate}
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
        consume_qty = flt(row.required_qty) * consumption_ratio
        if consume_qty > 0:
            current_consumed_qty = flt(frappe.db.get_value("Work Order Item", row.name, "consumed_qty"))
            row.db_set("consumed_qty", current_consumed_qty + consume_qty, update_modified=False)

    new_produced_qty = current_produced_qty + qty_manufactured
    wo.db_set("produced_qty", new_produced_qty)
    wo.db_set("process_loss_qty", current_process_loss_qty + process_loss_qty)
    is_complete = new_produced_qty >= flt(wo.qty) - 0.0001
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