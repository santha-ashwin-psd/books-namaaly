"""
Packing Engine — actions related to Packing Slips and Packing BOMs.

create_packing_slip       -- auto-generate a Packing Slip from a submitted
                             Work Order whose BOM is of type 'Packing'.
                             Pre-populates the items list from the Packing
                             BOM's packing_items table and the bulk_item row,
                             scaled to qty_to_pack. Also traces the bulk item
                             back to the Work Order that produced it
                             (source_work_order) and pre-fills the bulk row's
                             batch from that run, so packing is tied to a
                             specific production batch rather than "whatever's
                             in the warehouse".
get_packing_slips          -- list Packing Slips linked to a specific Work
                             Order (used by the WorkOrderView to show a
                             linked-doc count).
get_packing_slips_sourced_from_work_order
                            -- the inverse lookup: Packing Slips that consumed
                             a given (bulk-producing) Work Order's output,
                             via source_work_order.
post_packing_consumption   -- the Manufacture Stock Entry for a fully-packed
                             Packing Slip: consumes the bulk item + packing
                             materials from source_warehouse and receives the
                             packed item (batch-aware, same shelf-life/
                             autoname pattern as Work Order completion) into
                             target_warehouse. Without this, a Packing Slip
                             only tracked packed_qty on paper and never
                             touched the stock ledger. Also absorbs the
                             slip's Packing Operating Cost (labor/overhead)
                             into the packed item's valuation, the same way
                             Work Order completion absorbs Total Operating
                             Cost -- see Phase 5 notes below.
_check_stock_availability  -- Phase 3 guardrail: both create_packing_slip()
                             (best-effort, against Manufacturing Settings'
                             Default Source Warehouse, since the slip's own
                             source_warehouse isn't chosen yet) and
                             post_packing_consumption() (hard check, against
                             the slip's actual source_warehouse) check the
                             bulk item's and every packing material's real
                             Bin qty before proceeding, and throw one message
                             naming every short item -- instead of letting
                             Stock Entry's own negative-stock guard fail deep
                             in the call stack on just the first short row.
get_bulk_packing_reconciliation
                            -- Phase 6: for a bulk-producing Work Order, show
                             qty produced vs. qty consumed across every linked
                             Packing Slip (posted and reserved-but-unposted
                             separately) vs. qty still sitting in the
                             warehouse, with a batch-level breakdown when the
                             bulk item is batch-tracked -- so shortages or
                             overpacking are visible at a glance instead of
                             only discoverable by chasing Stock Ledger Entries.
list_bulk_packing_reconciliations
                            -- Phase 6b: the fleet-wide version -- reconciles
                             every bulk-producing Work Order in a date range
                             (optionally filtered by status/company) and
                             returns them worst-first, so shortages surface
                             without opening each Work Order one at a time.
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate, getdate

from zoho_books_clone.utils.access import assert_can
from zoho_books_clone.utils.tenancy import assert_doc_in_user_company
from zoho_books_clone.inventory.utils import get_valuation_rate, get_stock_balance


def _allow_negative_stock():
    """Manufacturing Settings > Allow Negative Stock. Mirrors
    inventory/doctype/stock_entry/stock_entry.py's _allow_negative_stock() --
    the two guards should agree on when to block, since this one exists only
    to catch the shortage earlier and name every item at once, not to be a
    stricter policy than Stock Entry's own."""
    try:
        return bool(frappe.db.get_single_value("Manufacturing Settings", "allow_negative_stock"))
    except Exception:
        return False


def _get_default_source_warehouse():
    """Manufacturing Settings > Default Source Warehouse, or "" if unset/not
    yet migrated. Deliberately not importing work_order_engine's private
    _get_mfg_settings() -- this is the one field of it this module needs."""
    try:
        return frappe.db.get_single_value("Manufacturing Settings", "default_source_warehouse") or ""
    except Exception:
        return ""


def _check_stock_availability(requirements, default_warehouse):
    """Guard against starting/posting a Packing Slip when the relevant
    warehouse doesn't actually have enough of a required item on hand.

    requirements -- list of {"item_code", "qty", "warehouse"(optional)}.
    Each row is checked against its own "warehouse" if given (a Work Order
    Item row can override its source warehouse per item -- e.g. packing
    material sourced from a dedicated Packing Store while the bulk item
    comes from the WO's main source warehouse); rows with no "warehouse"
    fall back to `default_warehouse`. Rows for the same (item, warehouse)
    pair are summed before checking.

    Raises a single error naming every short item (with the warehouse it
    was actually checked against), rather than letting the first short row
    fail deep inside Stock Entry's own negative-stock guard
    (inventory/doctype/stock_entry/stock_entry.py's validate()) with every
    other row's shortage still undiscovered until the next attempt.

    A row is skipped (not checked) only if it has neither its own warehouse
    nor a default_warehouse to fall back to -- nothing known to check yet.
    No-ops entirely if Manufacturing Settings > Allow Negative Stock is on
    (same setting Stock Entry itself respects).
    """
    if _allow_negative_stock():
        return

    needed = {}
    for r in requirements:
        item_code = r.get("item_code")
        qty = flt(r.get("qty"))
        warehouse = r.get("warehouse") or default_warehouse
        if not item_code or qty <= 0 or not warehouse:
            continue
        key = (item_code, warehouse)
        needed[key] = needed.get(key, 0.0) + qty

    shortages = []
    for (item_code, warehouse), qty in needed.items():
        available = get_stock_balance(item_code, warehouse)
        if available < qty:
            shortages.append((item_code, warehouse, available, qty))

    if shortages:
        item_names = {
            d.name: d.item_name
            for d in frappe.get_all(
                "Item", filters=[["name", "in", [s[0] for s in shortages]]], fields=["name", "item_name"]
            )
        }
        lines = []
        for item_code, warehouse, available, qty in shortages:
            name = item_names.get(item_code)
            label = f"{name} ({item_code})" if name and name != item_code else item_code
            lines.append(f"{label} · {warehouse} — needs {round(qty, 2)}, only {round(available, 2)} in stock")
        # One bullet per line (not a comma-joined sentence or inline <ul><li>
        # HTML) so the Vue frontend's shortfall-item-card dialog can parse
        # and render each short item on its own card -- see
        # parseShortfallItems() in WorkOrder.vue and _item_label()/
        # _bulleted() in work_order_engine.py, which use the same
        # "needs X, only Y in stock" wording.
        item_list = "\n".join(f"• {line}" for line in lines)
        frappe.throw(_(
            "Not enough stock to cover this Packing Slip:\n\n{0}"
        ).format(item_list))


@frappe.whitelist(allow_guest=False, methods=["POST"])
def create_packing_slip(work_order, qty_to_pack=None):
    """Create a Draft Packing Slip for the given Work Order.

    The Work Order must be submitted and its BOM must be of type 'Packing'.
    qty_to_pack defaults to the remaining unfinished quantity on the WO.

    Returns the new Packing Slip name.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Packing Slip", "write")

    wo = frappe.get_doc("Work Order", work_order)
    if wo.docstatus != 1:
        frappe.throw(_("Work Order must be submitted before creating a Packing Slip."))

    bom_type = frappe.db.get_value("BOM", wo.bom, "bom_type")
    if bom_type != "Packing":
        frappe.throw(_(
            "Work Order {0} uses a {1} BOM. Packing Slips can only be created "
            "for Work Orders with a Packing BOM."
        ).format(wo.name, bom_type or "Manufacturing"))

    bom_doc = frappe.get_doc("BOM", wo.bom)
    qty_to_pack = flt(qty_to_pack) or (flt(wo.qty) - flt(wo.produced_qty))
    if qty_to_pack <= 0:
        frappe.throw(_("Work Order {0} is already fully completed.").format(wo.name))

    ratio = qty_to_pack / flt(bom_doc.quantity or 1)

    ps = frappe.new_doc("Packing Slip")
    ps.work_order = wo.name
    ps.production_item = wo.production_item
    ps.bom = wo.bom
    ps.qty_to_pack = qty_to_pack
    ps.packing_date = nowdate()
    ps.status = "Draft"

    # Trace this Packing Slip back to whichever Work Order actually produced
    # the bulk stock it's about to consume, so packing isn't just "whatever's
    # in the warehouse" -- it's tied to a specific production run. We pick
    # the most recently touched submitted Work Order (Completed or still
    # In Process, i.e. partially produced) in this company whose production
    # item matches the Packing BOM's bulk_item. This is a best-effort default
    # (there may be several candidate runs); the field stays editable so the
    # user can point it at a different run if this guess is wrong.
    source_wo_name = None
    source_batch_no = None
    source_batch_expiry = None
    source_available_qty = 0.0
    if bom_doc.bulk_item:
        # Only a Work Order whose OWN BOM is Manufacturing/Sub-Assembly can be
        # a valid bulk source -- a Work Order running on a Packing BOM didn't
        # manufacture anything, it just repacked something else, so wiring
        # source_work_order to it would trace back to the wrong stage (or
        # even create a packing-sourced-from-packing loop) if its output item
        # code happens to collide with this slip's bulk_item.
        candidate = frappe.db.sql("""
            SELECT wo.name AS name
            FROM `tabWork Order` wo
            INNER JOIN `tabBOM` b ON b.name = wo.bom
            WHERE wo.production_item = %(bulk_item)s
              AND wo.docstatus = 1
              AND wo.company = %(company)s
              AND wo.status IN ('Completed', 'In Process')
              AND b.bom_type != 'Packing'
            ORDER BY wo.modified DESC
            LIMIT 1
        """, {"bulk_item": bom_doc.bulk_item, "company": wo.company}, as_dict=True)
        source_wo_name = candidate[0].name if candidate else None
        if source_wo_name:
            ps.source_work_order = source_wo_name
            source_fg_wh = frappe.db.get_value("Work Order", source_wo_name, "fg_warehouse")
            if source_fg_wh:
                source_available_qty = get_stock_balance(bom_doc.bulk_item, source_fg_wh)
                if frappe.db.get_value("Item", bom_doc.bulk_item, "has_batch_no"):
                    latest_batch = frappe.get_all(
                        "Batch",
                        filters={
                            "item": bom_doc.bulk_item,
                            "warehouse": source_fg_wh,
                            "batch_qty": [">", 0],
                        },
                        fields=["name", "expiry_date"],
                        order_by="manufacturing_date desc, creation desc",
                        limit=1,
                    )
                    if latest_batch:
                        source_batch_no = latest_batch[0].name
                        source_batch_expiry = latest_batch[0].expiry_date

    # Row-level source warehouse: mirror whatever the Work Order Item row for
    # this item is set to. A WO Item row can override its own source
    # warehouse per item (e.g. a packing material sourced from a dedicated
    # Packing Store while the bulk item comes from the WO's main source
    # warehouse) -- without carrying that over, every Packing Slip row would
    # fall back to the single "Consume Materials From" field, which can only
    # hold one warehouse, so any item actually sourced from somewhere else
    # would wrongly get checked/consumed against the wrong warehouse.
    wo_item_warehouse = {
        row.item_code: row.source_warehouse for row in (wo.items or []) if row.source_warehouse
    }

    # Bulk item row. Scales directly with qty_to_pack (bulk_qty_per_unit is
    # defined as "per packed unit"), NOT with `ratio` (qty_to_pack /
    # bom.quantity) -- ratio is only correct for packing_items, whose qty is
    # defined per the BOM's own batch quantity. Using ratio for the bulk
    # item would silently divide its consumption by bom.quantity for any
    # Packing BOM whose Quantity field isn't exactly 1.
    if bom_doc.bulk_item and flt(bom_doc.bulk_qty_per_unit) > 0:
        bulk_uom = frappe.db.get_value("Item", bom_doc.bulk_item, "stock_uom") or ""
        ps.append("items", {
            "item_code": bom_doc.bulk_item,
            "item_name": frappe.db.get_value("Item", bom_doc.bulk_item, "item_name") or bom_doc.bulk_item,
            "required_qty": flt(bom_doc.bulk_qty_per_unit) * qty_to_pack,
            "packed_qty": 0,
            "uom": bulk_uom,
            "batch_no": source_batch_no or "",
            "source_warehouse": wo_item_warehouse.get(bom_doc.bulk_item) or "",
        })

    # Packing materials
    for r in (bom_doc.packing_items or []):
        ps.append("items", {
            "item_code": r.item_code,
            "item_name": r.item_name or "",
            "required_qty": flt(r.qty) * ratio,
            "packed_qty": 0,
            "source_warehouse": wo_item_warehouse.get(r.item_code) or "",
            "uom": r.uom or "",
        })

    if not ps.items:
        frappe.throw(_("Packing BOM {0} has no items — add packing materials first.").format(wo.bom))

    # Best-effort guardrail at creation time: the slip's own source_warehouse
    # isn't chosen yet (that happens later, in the UI, before packing starts),
    # so check each item against its actual source: the row's own
    # source_warehouse (copied above from the matching Work Order Item row,
    # if that row had its own override -- e.g. a packing material sourced
    # from a dedicated Packing Store while the bulk item comes from the WO's
    # main source warehouse), falling back to the WO's overall
    # source_warehouse, then to Manufacturing Settings' Default Source
    # Warehouse. Checking every row against a single warehouse here would
    # throw false shortages for items actually sourced from a different,
    # fully-stocked warehouse. If nothing is set anywhere yet there's nothing
    # to check against yet -- the hard check in post_packing_consumption()
    # below still catches a real shortage right before stock is actually
    # posted.
    fallback_wh = wo.source_warehouse or _get_default_source_warehouse()
    _check_stock_availability(
        [
            {
                "item_code": r.item_code,
                "qty": r.required_qty,
                "warehouse": r.source_warehouse or fallback_wh,
            }
            for r in ps.items
        ],
        fallback_wh,
    )

    ps.insert(ignore_permissions=True)

    if source_wo_name:
        frappe.msgprint(_(
            "Bulk item {0} traced to Work Order {1}{2} — {3} {4} available in its FG warehouse.{5}"
        ).format(
            bom_doc.bulk_item,
            source_wo_name,
            _(" (Batch {0})").format(source_batch_no) if source_batch_no else "",
            round(flt(source_available_qty), 2),
            frappe.db.get_value("Item", bom_doc.bulk_item, "stock_uom") or "",
            _(" This batch expires {0} — the packed item's own batch can't outlive it.").format(
                source_batch_expiry
            ) if source_batch_expiry else "",
        ), indicator="blue")

    frappe.db.commit()

    return ps.name


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_packing_slips(work_order):
    """Return a summary list of Packing Slips for the given Work Order."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    return frappe.get_all(
        "Packing Slip",
        filters={"work_order": work_order},
        fields=["name", "status", "packing_date", "qty_to_pack", "packed_by"],
        order_by="creation desc",
        limit=50,
    )


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_packing_slips_sourced_from_work_order(work_order):
    """Return a summary list of Packing Slips whose source_work_order points
    at this Work Order -- i.e. Packing Slips that packed bulk stock this
    (Manufacturing/Sub-Assembly-BOM) Work Order produced. Used by the bulk
    Work Order's page to show a "Packed via: PS-xxxx" trail, the inverse of
    get_packing_slips() above (which looks up by the Packing Slip's own
    work_order, i.e. the Packing-BOM Work Order it was created from)."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    return frappe.get_all(
        "Packing Slip",
        filters={"source_work_order": work_order},
        fields=["name", "status", "packing_date", "qty_to_pack", "work_order"],
        order_by="creation desc",
        limit=50,
    )


@frappe.whitelist(allow_guest=False, methods=["POST"])
def post_packing_consumption(packing_slip, batch_no=None, manufacturing_date=None, expiry_date=None):
    """Post the Manufacture Stock Entry for a fully-packed Packing Slip.

    Consumes every item row's packed_qty from source_warehouse (the bulk
    item and packing materials — bottles, caps, labels, cartons) and
    receives qty_to_pack of the packed item into target_warehouse. This is
    the step that was previously missing: without it, packed_qty/status
    only recorded progress on the Packing Slip itself and never moved
    anything in the stock ledger, so packing material stock never actually
    went down.

    Can only be called once per Packing Slip — the resulting Stock Entry
    name is written back to `stock_entry`, and packing_slip.py's validate()
    locks the document (like Cancelled) once that field is set, so this
    can't silently double-post.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Stock Entry", "write")

    ps = frappe.get_doc("Packing Slip", packing_slip)
    assert_doc_in_user_company(ps)

    if ps.status == "Cancelled":
        frappe.throw(_("This Packing Slip is cancelled."))
    if ps.stock_entry:
        frappe.throw(_("Stock has already been posted for this Packing Slip ({0}).").format(ps.stock_entry))
    if ps.status != "Packed":
        frappe.throw(_("Mark the Packing Slip as fully Packed before posting stock consumption."))
    if not ps.items:
        frappe.throw(_("Packing Slip has no items to consume."))
    if not ps.source_warehouse:
        frappe.throw(_("Set 'Consume Materials From' warehouse before posting."))

    # Check every item's actual Bin qty in source_warehouse against its
    # packed_qty (what's about to be consumed) up front, and name every
    # short item in one message -- rather than letting the first short row
    # fail deep inside Stock Entry's own negative-stock guard once se.insert()
    # below is already underway, with the rest of the rows unchecked.
    # Group by each row's own source_warehouse (falling back to the slip's
    # source_warehouse) so a row-level override is checked against the
    # warehouse it will actually be consumed from, not always ps.source_warehouse.
    _reqs_by_warehouse = {}
    for row in ps.items:
        wh = row.source_warehouse or ps.source_warehouse
        _reqs_by_warehouse.setdefault(wh, []).append(
            {"item_code": row.item_code, "qty": row.packed_qty}
        )
    for wh, reqs in _reqs_by_warehouse.items():
        _check_stock_availability(reqs, wh)

    # Phase 4 (bulk -> packed batch/expiry lineage): if the bulk item is
    # batch-tracked, this run must be sourced from exactly one identified
    # lot -- packing from "whatever batch, auto-picked" (Stock Entry's own
    # generic batch validation would happily accept any valid batch_no, and
    # get_batches_for_outgoing() would happily split across several) breaks
    # lot traceability, since a packed batch's expiry/potency depends on
    # which specific bulk lot went into it. So the row's batch_no is
    # required, must belong to the bulk item, must not be disabled, must not
    # already be expired, and must hold enough qty to cover this run on its
    # own -- if it doesn't, the run should be split into separate Packing
    # Slips per bulk batch rather than silently blending lots.
    bulk_item = frappe.db.get_value("BOM", ps.bom, "bulk_item") if ps.bom else None
    bulk_source_batch_no = None
    if bulk_item and frappe.db.get_value("Item", bulk_item, "has_batch_no"):
        bulk_row = next((r for r in ps.items if r.item_code == bulk_item), None)
        if bulk_row and flt(bulk_row.packed_qty) > 0:
            if not bulk_row.batch_no:
                frappe.throw(_(
                    "Bulk item {0} is batch-tracked -- select which Batch this "
                    "run is packed from (the item row's Batch No) before "
                    "posting. This is required for lot traceability and so "
                    "the packed item's own batch can inherit the correct "
                    "expiry."
                ).format(bulk_item))
            batch_doc = frappe.db.get_value(
                "Batch", bulk_row.batch_no,
                ["item", "batch_qty", "disabled", "expiry_date"], as_dict=True,
            )
            if not batch_doc:
                frappe.throw(_("Batch {0} does not exist.").format(bulk_row.batch_no))
            if batch_doc.item != bulk_item:
                frappe.throw(_(
                    "Batch {0} belongs to item {1}, not the bulk item {2}."
                ).format(bulk_row.batch_no, batch_doc.item, bulk_item))
            if batch_doc.disabled:
                frappe.throw(_("Batch {0} is disabled and cannot be used.").format(bulk_row.batch_no))
            if batch_doc.expiry_date and getdate(batch_doc.expiry_date) < getdate(nowdate()):
                frappe.throw(_(
                    "Bulk Batch {0} expired on {1} and cannot be packed."
                ).format(bulk_row.batch_no, batch_doc.expiry_date))
            if flt(batch_doc.batch_qty) < flt(bulk_row.packed_qty):
                frappe.throw(_(
                    "Insufficient stock in bulk Batch {0}. Available: {1}, "
                    "Required: {2}. Packing must be sourced from a single "
                    "lot -- split this run across multiple Packing Slips "
                    "against different batches if one lot can't cover it."
                ).format(
                    bulk_row.batch_no,
                    round(flt(batch_doc.batch_qty), 2),
                    round(flt(bulk_row.packed_qty), 2),
                ))
            bulk_source_batch_no = bulk_row.batch_no

    target_warehouse = ps.target_warehouse
    if not target_warehouse and ps.work_order:
        target_warehouse = frappe.db.get_value("Work Order", ps.work_order, "fg_warehouse")
    if not target_warehouse:
        frappe.throw(_(
            "Set 'Receive Packed Goods At' warehouse before posting "
            "(or link a Work Order with an FG Warehouse)."
        ))

    se = frappe.new_doc("Stock Entry")
    se.company = ps.company
    se.stock_entry_type = "Manufacture"
    se.posting_date = nowdate()
    se.work_order = ps.work_order or ""
    se.remarks = f"Packing consumption for Packing Slip {ps.name}"

    # Consume the bulk item + every packing material by its actual
    # packed_qty (not required_qty) -- a run that under- or over-consumed a
    # material relative to the plan should post what was really used, same
    # principle as Work Order completion using consume_qty rather than
    # required_qty.
    total_consumed_cost = 0.0
    any_consumed = False
    for row in ps.items:
        qty = flt(row.packed_qty)
        if qty <= 0:
            continue
        any_consumed = True
        row_source_warehouse = row.source_warehouse or ps.source_warehouse
        rm_rate = get_valuation_rate(row.item_code, row_source_warehouse)
        total_consumed_cost += qty * rm_rate
        item_row = {
            "item_code": row.item_code,
            "qty": qty,
            "s_warehouse": row_source_warehouse,
            "basic_rate": rm_rate,
        }
        if row.batch_no:
            item_row["batch_no"] = row.batch_no
        se.append("items", item_row)

    if not any_consumed:
        frappe.throw(_("No items have a Packed Qty greater than zero."))

    # Receive the packed item. Batch-tracked items get a Batch pre-created
    # first (same pattern as Work Order completion) so Stock Entry's own
    # validation, which requires the Batch to already exist, passes.
    # Leaving batch_no blank lets Batch.autoname generate
    # {Item Code}-{Year}-{Sequence}, and leaving expiry_date blank lets
    # Batch.set_expiry_date_from_shelf_life derive it from shelf_life_in_days.
    qty_to_pack = flt(ps.qty_to_pack)
    if qty_to_pack <= 0:
        frappe.throw(_("Qty to Pack must be greater than zero."))

    # Phase 5: absorb this run's packing labor/overhead into the packed
    # item's valuation, mirroring how complete_work_order() absorbs a Work
    # Order's Total Operating Cost into its finished good. Packing BOMs
    # can't carry an Operations table (bom.py's validate_packing_bom()
    # rejects one -- that belongs to the Manufacturing BOM that produced
    # the bulk item), so there's no per-run cost to pro-rate the way
    # consumption_ratio does on the Work Order side; the whole run's cost
    # is entered directly on the slip and absorbed in full into
    # qty_to_pack. Unlike Work Order completion there's no scrap credited
    # out here, so the pool can't go negative and there's nothing to clamp
    # or write off -- fg_unit_rate is a straight sum.
    operating_cost_this_run = flt(ps.packing_operating_cost)
    fg_unit_rate = (total_consumed_cost + operating_cost_this_run) / qty_to_pack if qty_to_pack else 0.0

    se.remarks += f" (packing operating cost absorbed: {operating_cost_this_run:.2f})"
    se.operating_cost_absorbed = operating_cost_this_run

    fg_row = {
        "item_code": ps.production_item,
        "qty": qty_to_pack,
        "t_warehouse": target_warehouse,
        "basic_rate": fg_unit_rate,
    }
    if frappe.db.get_value("Item", ps.production_item, "has_batch_no"):
        if not batch_no or not frappe.db.exists("Batch", batch_no):
            new_batch = frappe.get_doc({
                "doctype": "Batch",
                "batch_no": batch_no or None,
                "item": ps.production_item,
                "warehouse": target_warehouse,
                "manufacturing_date": manufacturing_date or nowdate(),
                "expiry_date": expiry_date or None,
                # Phase 4 lineage: Batch.validate()'s _apply_source_batch_lineage()
                # will cap this new batch's expiry_date to bulk_source_batch_no's
                # own expiry_date if it's earlier than whatever was passed in
                # above (or than what shelf_life_in_days alone would compute) --
                # a packed batch can never outlive the bulk lot it was filled
                # from. Only set when the bulk item is batch-tracked (validated
                # above); left None otherwise, same as before this phase.
                "source_batch_no": bulk_source_batch_no or None,
            })
            new_batch.insert(ignore_permissions=True)
            batch_no = new_batch.name
        fg_row["batch_no"] = batch_no
    se.append("items", fg_row)

    se.insert(ignore_permissions=True)
    se.submit()

    ps.db_set("stock_entry", se.name)
    ps.db_set("target_warehouse", target_warehouse)
    if batch_no:
        ps.db_set("posted_batch_no", batch_no)

    # Sync the Work Order the same way complete_work_order() does for a
    # Manufacturing BOM: without this, produced_qty/status never move for a
    # Packing-BOM Work Order at all, which meant create_packing_slip()'s
    # "qty_to_pack = wo.qty - wo.produced_qty" default kept coming back as
    # the FULL original qty forever, and the "Create Packing Slip" button
    # (gated on status != 'Completed') never went away -- nothing stopped
    # an unlimited number of Packing Slips from being created and posted
    # for the same Work Order, each one consuming more bulk item/packing
    # materials and receiving more finished stock with no cap at all.
    if ps.work_order:
        frappe.db.sql("SELECT name FROM `tabWork Order` WHERE name=%s FOR UPDATE", (ps.work_order,))
        wo = frappe.get_doc("Work Order", ps.work_order)
        current_produced_qty = flt(frappe.db.get_value("Work Order", wo.name, "produced_qty"))
        new_produced_qty = current_produced_qty + qty_to_pack
        wo.db_set("produced_qty", new_produced_qty)
        if new_produced_qty >= flt(wo.qty) - 0.0001:
            wo.db_set("status", "Completed")
        else:
            wo.db_set("status", "In Process")

    frappe.db.commit()

    return se.name
@frappe.whitelist(allow_guest=False, methods=["POST"])
def reverse_packing_consumption(packing_slip):
    """Undo the Manufacture Stock Entry posted by post_packing_consumption():
    cancels that Stock Entry (reversing the bulk/packing-material
    consumption and the packed-item receipt) and clears the Packing Slip's
    stock_entry/target_warehouse/posted_batch_no so it's unlocked and can
    be corrected or reposted.

    packed_qty and status on the slip's item rows are left untouched --
    they describe physical packing progress, which reversing the stock
    posting doesn't undo.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Stock Entry", "cancel")

    ps = frappe.get_doc("Packing Slip", packing_slip)
    assert_doc_in_user_company(ps)

    if ps.status == "Cancelled":
        frappe.throw(_("This Packing Slip is cancelled."))
    if not ps.stock_entry:
        frappe.throw(_("No stock has been posted for this Packing Slip yet."))

    se = frappe.get_doc("Stock Entry", ps.stock_entry)
    if se.docstatus != 1:
        frappe.throw(_("Linked Stock Entry {0} is not submitted.").format(se.name))

    packed_qty_reversed = flt(ps.qty_to_pack)

    se.flags.ignore_manufacturing_guard = True
    se.cancel()

    ps.db_set("stock_entry", "")
    ps.db_set("target_warehouse", "")
    ps.db_set("posted_batch_no", "")

    # Mirror the roll-back that reverse_manufacture_entry() does for the
    # Manufacturing-BOM path -- undo exactly what post_packing_consumption()
    # added, so produced_qty/status stay in sync with the stock ledger
    # instead of still claiming this Packing Slip's qty was produced after
    # its stock movement has been reversed.
    if ps.work_order:
        frappe.db.sql("SELECT name FROM `tabWork Order` WHERE name=%s FOR UPDATE", (ps.work_order,))
        wo = frappe.get_doc("Work Order", ps.work_order)
        current_produced_qty = flt(frappe.db.get_value("Work Order", wo.name, "produced_qty"))
        new_produced_qty = max(current_produced_qty - packed_qty_reversed, 0.0)
        wo.db_set("produced_qty", new_produced_qty)
        wo.db_set("status", "In Process" if new_produced_qty > 0 else "Submitted")

    frappe.db.commit()
    return "Reversed"


def _reconcile_bulk_work_order(wo, include_detail=True):
    """Core Phase 6 reconciliation math for one bulk-producing Work Order --
    shared by get_bulk_packing_reconciliation() (single-WO, full detail) and
    list_bulk_packing_reconciliations() (fleet-wide, summary only) so the two
    can't drift apart on what "reconciled" actually means.

    `wo` -- a loaded Work Order doc (Manufacturing/Sub-Assembly BOM type;
    caller is responsible for that check, see _assert_bulk_producing_work_order).
    `include_detail` -- when False, skips the per-Packing-Slip and per-batch
    breakdowns (each an extra query per row) -- the fleet report only needs
    the summary numbers to flag which Work Orders need a closer look; the
    detail is one click away on the Work Order's own page.

    Returns the same shape documented on get_bulk_packing_reconciliation(),
    minus "packing_slips"/"batches" when include_detail=False.
    """
    bulk_item = wo.production_item
    has_batch_no = bool(frappe.db.get_value("Item", bulk_item, "has_batch_no"))

    slip_rows = frappe.get_all(
        "Packing Slip",
        filters={"source_work_order": wo.name},
        fields=["name", "status", "stock_entry"],
        order_by="creation desc",
    )

    posted_total = 0.0
    reserved_total = 0.0
    slips = []
    per_batch = {}  # batch_no -> {"posted": x, "reserved": y}

    for slip in slip_rows:
        bulk_row = frappe.db.get_value(
            "Packing Slip Item",
            {"parent": slip.name, "item_code": bulk_item},
            ["packed_qty", "batch_no"],
            as_dict=True,
        )
        packed_qty = flt(bulk_row.packed_qty) if bulk_row else 0.0
        batch_no = bulk_row.batch_no if bulk_row else None
        is_posted = bool(slip.stock_entry)

        if slip.status != "Cancelled":
            if is_posted:
                posted_total += packed_qty
            else:
                reserved_total += packed_qty

        if include_detail and batch_no:
            bucket = per_batch.setdefault(batch_no, {"posted": 0.0, "reserved": 0.0})
            if slip.status != "Cancelled":
                if is_posted:
                    bucket["posted"] += packed_qty
                else:
                    bucket["reserved"] += packed_qty

        if include_detail:
            slips.append({
                "name": slip.name,
                "status": slip.status,
                "bulk_packed_qty": packed_qty,
                "batch_no": batch_no,
                "stock_posted": is_posted,
                "stock_entry": slip.stock_entry,
            })

    remaining_in_warehouse = get_stock_balance(bulk_item, wo.fg_warehouse) if wo.fg_warehouse else 0.0
    bulk_qty_produced = flt(wo.produced_qty)
    unaccounted = bulk_qty_produced - posted_total - remaining_in_warehouse

    tolerance = 0.01
    if abs(unaccounted) <= tolerance:
        status = "reconciled"
    elif unaccounted > 0:
        status = "shortage"
    else:
        status = "overpack"

    result = {
        "work_order": wo.name,
        "bulk_item": bulk_item,
        "bulk_item_name": frappe.db.get_value("Item", bulk_item, "item_name"),
        "fg_warehouse": wo.fg_warehouse,
        "qty_planned": flt(wo.qty),
        "bulk_qty_produced": bulk_qty_produced,
        "bulk_qty_consumed_posted": posted_total,
        "bulk_qty_reserved_unposted": reserved_total,
        "bulk_qty_remaining_in_warehouse": remaining_in_warehouse,
        "bulk_qty_unaccounted": unaccounted,
        "status": status,
    }

    if not include_detail:
        return result

    result["packing_slips"] = slips

    if has_batch_no:
        batches = []
        for batch_no, bucket in per_batch.items():
            batch_qty = flt(frappe.db.get_value("Batch", batch_no, "batch_qty") or 0)
            batch_unaccounted = None
            # Only meaningful for a batch still sitting in the bulk WO's own
            # fg_warehouse -- a batch that's been fully moved/consumed
            # elsewhere doesn't have a single warehouse balance to reconcile
            # against here.
            batch_warehouse = frappe.db.get_value("Batch", batch_no, "warehouse")
            if batch_warehouse == wo.fg_warehouse:
                batch_unaccounted = batch_qty - bucket["reserved"]  # reserved not yet posted still sits in the batch qty
            batches.append({
                "batch_no": batch_no,
                "bulk_qty_consumed_posted": bucket["posted"],
                "bulk_qty_reserved_unposted": bucket["reserved"],
                "batch_qty_remaining": batch_qty,
                "batch_qty_unaccounted": batch_unaccounted,
            })
        result["batches"] = batches

    return result


def _assert_bulk_producing_work_order(wo):
    """Throw if `wo` runs on a Packing BOM -- it's the consumer, not the
    producer, of bulk stock, and has no reconciliation of its own to run."""
    bom_type = frappe.db.get_value("BOM", wo.bom, "bom_type") if wo.bom else None
    if bom_type == "Packing":
        frappe.throw(_(
            "Work Order {0} runs on a Packing BOM -- it's the consumer, not "
            "the producer, of bulk stock. Run this reconciliation against the "
            "Manufacturing/Sub-Assembly-BOM Work Order that produced the bulk "
            "item instead (see its 'Packed via' trail)."
        ).format(wo.name))


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_bulk_packing_reconciliation(work_order):
    """Phase 6: reconcile a bulk-producing Work Order's output against every
    Packing Slip that drew on it, so shortages/overpacking are visible at a
    glance instead of only discoverable by chasing Stock Ledger Entries.

    `work_order` must be a Manufacturing/Sub-Assembly-BOM Work Order (the one
    that produced the bulk item) -- the same doc get_packing_slips_sourced_
    from_work_order() looks up Packing Slips against via source_work_order.

    Returns:
      bulk_item / bulk_item_name / fg_warehouse -- what was produced, and where
      qty_planned / bulk_qty_produced           -- from the Work Order itself
      bulk_qty_consumed_posted                  -- summed bulk-row packed_qty
                                                    across Packing Slips whose
                                                    stock has actually been
                                                    posted (stock_entry set) --
                                                    i.e. what's really left the
                                                    stock ledger so far
      bulk_qty_reserved_unposted                -- summed bulk-row packed_qty
                                                    on slips that have recorded
                                                    physical packing progress
                                                    but not yet posted stock
                                                    (still Draft/In Progress/
                                                    Packed with no stock_entry).
                                                    Not yet a stock movement,
                                                    but a claim against the
                                                    bulk item that will become
                                                    one -- surfaced separately
                                                    so it isn't mistaken for
                                                    stock actually consumed.
      bulk_qty_remaining_in_warehouse           -- current Bin balance of the
                                                    bulk item in fg_warehouse
      bulk_qty_unaccounted                      -- produced - posted consumed
                                                    - remaining in warehouse.
                                                    Should sit at ~0 if every
                                                    unit produced is either
                                                    still in the warehouse or
                                                    has gone out through a
                                                    posted Packing Slip. A
                                                    nonzero value means bulk
                                                    stock moved through some
                                                    other channel (a manual
                                                    Stock Entry, a Delivery
                                                    Note, a Stock Adjustment,
                                                    etc.) that this Work Order
                                                    /Packing Slip chain doesn't
                                                    know about.
      status                                    -- "reconciled" if
                                                    bulk_qty_unaccounted is
                                                    within a small rounding
                                                    tolerance of zero,
                                                    "shortage" if positive
                                                    (produced more than can be
                                                    traced to warehouse stock
                                                    or a posted Packing Slip),
                                                    "overpack" if negative
                                                    (more left than was ever
                                                    produced -- e.g. a Stock
                                                    Adjustment topped up this
                                                    warehouse from elsewhere).
      packing_slips                             -- one row per linked Packing
                                                    Slip: name, status,
                                                    qty_to_pack, the bulk row's
                                                    packed_qty and batch_no,
                                                    whether stock is posted,
                                                    and the Stock Entry name.
      batches                                   -- only present when the bulk
                                                    item is batch-tracked: the
                                                    same posted/reserved/
                                                    remaining/unaccounted
                                                    breakdown, but per bulk
                                                    Batch No, so a shortage can
                                                    be traced to the specific
                                                    lot it happened on rather
                                                    than just the item as a
                                                    whole.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    wo = frappe.get_doc("Work Order", work_order)
    assert_doc_in_user_company(wo)
    _assert_bulk_producing_work_order(wo)

    return _reconcile_bulk_work_order(wo, include_detail=True)


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def list_bulk_packing_reconciliations(from_date=None, to_date=None, status=None,
                                       company=None, limit=200):
    """Phase 6b: fleet-wide view of get_bulk_packing_reconciliation() --
    "show me every bulk Work Order with a shortage this month" -- instead of
    having to open each Work Order's own page one at a time.

    from_date / to_date -- optional window on the Work Order's
                          planned_start_date (falls back to creation date
                          for older records with no planned_start_date set).
                          Both bounds inclusive; either may be omitted for an
                          open-ended range.
    status              -- optional filter to just "shortage", "overpack",
                          or "reconciled". Omit (or "All") for everything.
    company             -- optional Books Company filter, for multi-company
                          instances.
    limit               -- max rows to compute (default 200) -- each row
                          costs a handful of queries (Packing Slip lookup +
                          a Bin read), so this is capped rather than
                          unbounded even though the underlying Work Order
                          filter could return more.

    Returns {"rows": [...], "truncated": bool} where each row is the summary
    shape from _reconcile_bulk_work_order(..., include_detail=False) plus
    the Work Order's status/production_item/produced_qty for context. Rows
    are sorted worst-first (largest |bulk_qty_unaccounted|) so the Work
    Orders most worth investigating surface at the top regardless of the
    status filter chosen.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    status = (status or "").strip()
    if status and status not in ("shortage", "overpack", "reconciled"):
        frappe.throw(_("Invalid status filter: {0}").format(status))

    limit = min(int(flt(limit) or 200), 500)

    conditions = [
        "wo.docstatus = 1",
        "wo.produced_qty > 0",
        "b.bom_type != 'Packing'",
    ]
    params = {}

    if company:
        conditions.append("wo.company = %(company)s")
        params["company"] = company

    if from_date:
        conditions.append("COALESCE(wo.planned_start_date, wo.creation) >= %(from_date)s")
        params["from_date"] = from_date
    if to_date:
        conditions.append("COALESCE(wo.planned_start_date, wo.creation) <= %(to_date)s")
        params["to_date"] = to_date

    where = " AND ".join(conditions)

    # Only fetch a bounded pool of candidate Work Orders to run the (more
    # expensive, per-row) reconciliation math against -- a company running
    # this for the first time on a large history could otherwise trigger
    # thousands of Packing Slip/Bin lookups in one call. Pull a healthy
    # multiple of `limit` candidates so the worst-first sort still has
    # enough to choose from after status filtering, without going unbounded.
    candidate_pool = min(limit * 5, 2000)
    wo_names = frappe.db.sql(f"""
        SELECT wo.name
        FROM `tabWork Order` wo
        JOIN `tabBOM` b ON b.name = wo.bom
        WHERE {where}
        ORDER BY COALESCE(wo.planned_start_date, wo.creation) DESC
        LIMIT %(candidate_pool)s
    """, {**params, "candidate_pool": candidate_pool}, as_dict=True)

    rows = []
    for r in wo_names:
        wo = frappe.get_doc("Work Order", r.name)
        try:
            assert_doc_in_user_company(wo)
        except Exception:
            continue  # skip Work Orders outside the caller's company scope

        recon = _reconcile_bulk_work_order(wo, include_detail=False)
        if status and recon["status"] != status:
            continue

        recon["wo_status"] = wo.status
        recon["planned_start_date"] = wo.planned_start_date
        rows.append(recon)

    rows.sort(key=lambda r: abs(flt(r["bulk_qty_unaccounted"])), reverse=True)

    truncated = len(wo_names) >= candidate_pool
    return {"rows": rows[:limit], "truncated": truncated}