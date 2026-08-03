from __future__ import annotations
"""
Inventory utility functions — stock balance, valuation, reorder detection.
All business logic lives here; controllers are kept thin.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, today


# ── FIFO Valuation ────────────────────────────────────────────────────────────

def get_fifo_cost(item_code: str, warehouse: str, qty: float) -> float:
    """
    Return the average cost per unit for issuing `qty` units using FIFO.
    Consumes incoming SLE layers oldest-first.
    Returns the weighted average rate (total_cost / qty).
    """
    qty = flt(qty)
    if qty <= 0:
        return 0.0

    # Incoming layers ordered oldest-first
    layers = frappe.db.sql("""
        SELECT actual_qty, incoming_rate
        FROM `tabStock Ledger Entry`
        WHERE item_code  = %(ic)s
          AND warehouse  = %(wh)s
          AND is_cancelled = 0
          AND actual_qty > 0
        ORDER BY posting_date ASC, posting_time ASC, creation ASC
    """, {"ic": item_code, "wh": warehouse}, as_dict=True)

    remaining  = qty
    total_cost = 0.0
    for layer in layers:
        if remaining <= 0:
            break
        layer_qty   = min(flt(layer.actual_qty), remaining)
        total_cost += layer_qty * flt(layer.incoming_rate)
        remaining  -= layer_qty

    return total_cost / qty if qty else 0.0


# ── Batch Selection (valuation-method-driven consumption order) ───────────────

def get_batches_for_outgoing(item_code: str, warehouse: str, qty: float,
                              valuation_method: str | None = None) -> list[dict]:
    """
    Return an ordered list of {"batch_no", "qty"} dicts covering `qty` units
    of `item_code` drawn from `warehouse`, consuming batches in the order
    dictated by the item's valuation method:

      FIFO            — oldest manufacturing_date first (first in, first out)
      LIFO            — newest manufacturing_date first (last in, first out)
      Moving Average  — no costing opinion on *which* batch to draw from, but
                         outgoing stock still has to come from somewhere, so
                         default to the same oldest-first order as FIFO. This
                         matters most in a pharma/Ayurvedic context: drawing
                         down older stock first reduces the chance of batches
                         expiring unused on the shelf.

    Only batches with a positive live balance in `warehouse` (computed from
    the Stock Ledger Entry, not the Batch.batch_qty/Batch.warehouse cache)
    are considered. Batches are consumed in order until `qty` is satisfied;
    a single call may return several batches if no one batch can cover the
    full requested qty. Raises if the combined available qty across all
    batches is insufficient — callers should catch and surface this as a
    user-facing error rather than silently under-allocating stock.
    """
    qty = flt(qty)
    if qty <= 0:
        return []

    if not valuation_method:
        valuation_method = frappe.db.get_value("Item", item_code, "valuation_method") or "Moving Average"

    order = "ASC" if valuation_method != "LIFO" else "DESC"
    # FIFO and Moving Average both consume oldest-first; LIFO reverses it.
    # Ties on manufacturing_date are left to natural row order (not disambiguated
    # further per product decision).

    # Live per-batch balance in this warehouse, aggregated straight from the
    # Stock Ledger Entry -- deliberately NOT Batch.warehouse/batch_qty.
    # Those are only a single-location cache (see stock_entry.py's
    # _adjust_batch_qty / the receiving-leg set_value("Batch", ..., "warehouse", ...)),
    # kept in sync solely by Stock Entry's own receiving legs. Any stock that
    # reached this batch through a different path -- an Opening Stock or
    # Purchase Invoice import, a manual ledger correction, or simply a batch
    # whose stock is genuinely split across more than one warehouse (which a
    # single warehouse field can never represent) -- leaves that cache stale
    # or plain wrong. This function then silently reported "0.0 available"
    # for a batch the ledger (and the Stock Items report, which already
    # aggregates the ledger directly) shows very much in stock. Reading the
    # ledger here too makes both agree and removes the staleness risk
    # entirely, at the cost of one extra join versus the cached fields.
    batches = frappe.db.sql(f"""
        SELECT sle.batch_no AS batch_no, SUM(sle.actual_qty) AS batch_qty,
               b.manufacturing_date AS manufacturing_date, b.creation AS creation
        FROM `tabStock Ledger Entry` sle
        INNER JOIN `tabBatch` b ON b.name = sle.batch_no
        WHERE sle.item_code = %(item_code)s
          AND sle.warehouse = %(warehouse)s
          AND sle.batch_no IS NOT NULL AND sle.batch_no != ''
          AND sle.is_cancelled = 0
          AND (b.disabled IS NULL OR b.disabled = 0)
        GROUP BY sle.batch_no
        HAVING batch_qty > 0.0001
        ORDER BY manufacturing_date {order}, creation {order}
    """, {"item_code": item_code, "warehouse": warehouse}, as_dict=True)

    allocations: list[dict] = []
    remaining = qty
    for b in batches:
        if remaining <= 0:
            break
        take = min(flt(b.batch_qty), remaining)
        if take <= 0:
            continue
        allocations.append({"batch_no": b.batch_no, "qty": take})
        remaining -= take

    if remaining > 0.0001:
        available = qty - remaining
        frappe.throw(_(
            "Insufficient batch-tracked stock for item <b>{0}</b> in warehouse <b>{1}</b>. "
            "Available across all batches: {2}, Required: {3}."
        ).format(item_code, warehouse, frappe.bold(available), frappe.bold(qty)))

    return allocations


def assert_batch_deletable(batch_no: str) -> None:
    """
    Block deleting a Batch master that still represents real stock or has
    ledger history.

    Why this matters: `batch_qty` is only a cache — the real stock lives in
    Bin (item+warehouse totals) and Stock Ledger Entry rows, neither of which
    is touched when a Batch document is deleted. Deleting the Batch anyway
    would:
      1. Leave existing Stock Ledger Entries pointing at a `batch_no` Link
         whose target no longer exists (orphaned reference).
      2. Make that quantity permanently unpickable by
         get_batches_for_outgoing() above -- it now reads live balances from
         the Stock Ledger Entry, but still INNER JOINs to `tabBatch` for
         manufacturing_date/disabled, so a missing Batch row still drops
         that quantity out of consideration entirely. Bin would still report
         the stock as available, but no future Stock Entry could ever
         actually issue it. That mismatch is a silent, hard-to-diagnose
         stock discrepancy.

    Callers should disable the batch instead (`disabled = 1`) once its stock
    is fully consumed, or issue a Stock Entry to zero it out first.
    """
    batch_qty = flt(frappe.db.get_value("Batch", batch_no, "batch_qty") or 0)
    if abs(batch_qty) > 0.0001:
        frappe.throw(_(
            "Batch <b>{0}</b> still holds <b>{1}</b> unit(s) of stock. "
            "Disable it instead, or issue a Stock Entry to move/consume its "
            "stock before deleting — deleting it now would leave that stock "
            "stranded in the warehouse total with no batch to draw it from."
        ).format(batch_no, frappe.bold(batch_qty)))

    if frappe.db.exists("Stock Ledger Entry", {"batch_no": batch_no}):
        frappe.throw(_(
            "Batch <b>{0}</b> has stock ledger history and cannot be deleted, "
            "as that would leave those transactions pointing at a batch that "
            "no longer exists. Disable it instead to keep it out of new "
            "transactions."
        ).format(batch_no))


# ── Reorder Check ─────────────────────────────────────────────────────────────

def check_reorder(item_code: str, warehouse: str) -> bool:
    """
    Return True if actual_qty < reorder_level for item+warehouse.
    - Always sends a Notification Log to System Managers (deduplicated).
    - If auto_po_enabled on the Item, also creates a draft Purchase Order.
    """
    bin_data = frappe.db.get_value(
        "Bin",
        {"item_code": item_code, "warehouse": warehouse},
        ["actual_qty", "reorder_level"],
        as_dict=True,
    )
    if not bin_data or not flt(bin_data.reorder_level):
        return False

    if flt(bin_data.actual_qty) >= flt(bin_data.reorder_level):
        return False

    item_doc = frappe.db.get_value(
        "Item", item_code,
        ["item_name", "reorder_qty", "reorder_supplier",
         "reorder_warehouse_override", "auto_po_enabled", "reorder_notes",
         "default_warehouse"],
        as_dict=True,
    ) or {}
    item_name = item_doc.get("item_name") or item_code
    subject   = f"Reorder Alert: {item_name} ({item_code})"

    # ── Notification (deduplicated per item, per user) ──────────────────────
    for user in frappe.get_all(
        "Has Role",
        filters={"role": "System Manager", "parenttype": "User"},
        fields=["parent"],
        distinct=True,
    ):
        # Dedup must be scoped to the recipient — checking existence without
        # for_user meant that once *any* System Manager had one unread alert
        # for this item, every other System Manager silently never got
        # notified at all, since the loop below never ran for anyone.
        already_notified = frappe.db.exists(
            "Notification Log",
            {"subject": subject, "document_type": "Bin", "read": 0, "for_user": user.parent},
        )
        if already_notified:
            continue
        try:
            frappe.get_doc({
                "doctype":       "Notification Log",
                "subject":       subject,
                "email_content": (
                    f"{item_name} ({item_code}) in <b>{warehouse}</b> — "
                    f"qty {flt(bin_data.actual_qty):.2f} is below "
                    f"reorder level {flt(bin_data.reorder_level):.2f}."
                ),
                "for_user":      user.parent,
                "document_type": "Bin",
                "type":          "Alert",
            }).insert(ignore_permissions=True)
        except Exception:
            pass

    # ── Auto PO ─────────────────────────────────────────────────────────────
    if item_doc.get("auto_po_enabled"):
        _auto_create_po(item_code, item_doc, warehouse)

    return True


def _auto_create_po(item_code: str, item_doc: dict, triggered_warehouse: str) -> None:
    """Create a draft PO from the item's saved reorder config. Errors are logged, not raised."""
    try:
        from frappe.utils import today

        # check_reorder can fire repeatedly while stock stays below the
        # reorder level (every stock-decreasing movement re-triggers it) —
        # without this guard, each call would create another draft PO for
        # the same item. Skip if an un-submitted auto-created PO for this
        # item already exists; once it's submitted/received or the person
        # deletes it, the next reorder check is free to create a new one.
        existing_draft = frappe.db.exists(
            "Purchase Order Item",
            {"item_code": item_code, "docstatus": 0},
        )
        if existing_draft:
            return

        supplier  = item_doc.get("reorder_supplier") or ""
        recv_wh   = (item_doc.get("reorder_warehouse_override")
                     or item_doc.get("default_warehouse")
                     or triggered_warehouse)
        order_qty = flt(item_doc.get("reorder_qty")) or 1
        notes     = item_doc.get("reorder_notes") or ""
        item_name = item_doc.get("item_name") or item_code

        company = (
            frappe.db.get_single_value("Books Settings", "default_company")
            or frappe.db.get_default("company")
            or ""
        )
        item_master = frappe.db.get_value(
            "Item", item_code,
            ["stock_uom", "standard_buying_rate", "description"],
            as_dict=True,
        ) or {}

        rate = flt(item_master.get("standard_buying_rate") or 0)
        po = frappe.get_doc({
            "doctype":          "Purchase Order",
            "supplier":         supplier,
            "transaction_date": today(),
            "company":          company,
            "set_warehouse":    recv_wh,
            "terms":            notes,
            "items": [{
                "item_code":   item_code,
                "item_name":   item_name,
                "description": item_master.get("description") or item_name,
                "qty":         order_qty,
                "uom":         item_master.get("stock_uom") or "Nos",
                "rate":        rate,
                "amount":      order_qty * rate,
            }],
        })
        po.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"Auto PO failed for {item_code}")


# ── Stock Balance ─────────────────────────────────────────────────────────────

def get_stock_balance(item_code: str, warehouse: str, as_of_date: str | None = None) -> float:
    """
    Return the net stock qty for an item in a warehouse.
    Uses the Bin table for the latest balance (fastest), or
    falls back to summing Stock Ledger Entries up to a date.
    """
    if as_of_date and getdate(as_of_date) < getdate(today()):
        return _sle_balance(item_code, warehouse, as_of_date)

    qty = frappe.db.get_value(
        "Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty"
    )
    return flt(qty)


def _sle_balance(item_code: str, warehouse: str, as_of_date: str) -> float:
    result = frappe.db.sql("""
        SELECT COALESCE(SUM(actual_qty), 0) AS qty
        FROM `tabStock Ledger Entry`
        WHERE item_code = %(item_code)s
          AND warehouse  = %(warehouse)s
          AND is_cancelled = 0
          AND posting_date <= %(date)s
    """, {"item_code": item_code, "warehouse": warehouse, "date": as_of_date}, as_dict=True)
    return flt(result[0].qty) if result else 0.0


def get_stock_balance_bulk(item_codes: list[str], warehouse: str) -> dict[str, float]:
    """Return {item_code: actual_qty} for a list of items in one warehouse."""
    if not item_codes:
        return {}
    rows = frappe.get_all(
        "Bin",
        filters={"warehouse": warehouse, "item_code": ["in", item_codes]},
        fields=["item_code", "actual_qty"],
    )
    return {r.item_code: flt(r.actual_qty) for r in rows}


# ── Valuation ─────────────────────────────────────────────────────────────────

def get_valuation_rate(item_code: str, warehouse: str) -> float:
    """Return current moving-average valuation rate from Bin.

    Falls back to Item.standard_buying_rate when there's no Bin row (or the
    Bin rate is 0) for this item+warehouse, so callers don't silently
    consume/receive stock at zero cost. If even that fallback is unset, logs
    a warning so the zero-cost posting doesn't pass unnoticed.
    """
    rate = flt(frappe.db.get_value(
        "Bin", {"item_code": item_code, "warehouse": warehouse}, "valuation_rate"
    ))
    if rate:
        return rate

    fallback_rate = flt(frappe.db.get_value("Item", item_code, "standard_buying_rate"))
    if fallback_rate:
        frappe.log_error(
            title="Valuation rate fallback used",
            message=(
                f"No Bin valuation rate for item {item_code} in warehouse "
                f"{warehouse}. Falling back to Item.standard_buying_rate "
                f"({fallback_rate})."
            ),
        )
        return fallback_rate

    frappe.log_error(
        title="Zero-cost valuation rate",
        message=(
            f"Item {item_code} in warehouse {warehouse} has no Bin valuation "
            f"rate and no Item.standard_buying_rate set. Returning 0 -- this "
            f"item is about to post at zero cost."
        ),
    )
    return 0.0


def get_valuation_rate_bulk(item_codes: list[str], warehouse: str) -> dict[str, float]:
    """Return {item_code: valuation_rate} for a list of items in one warehouse."""
    if not item_codes or not warehouse:
        return {}
    rows = frappe.get_all(
        "Bin",
        filters={"warehouse": warehouse, "item_code": ["in", item_codes]},
        fields=["item_code", "valuation_rate"],
    )
    return {r.item_code: flt(r.valuation_rate) for r in rows}


def compute_bin_valuation(
    old_qty: float,
    old_value: float,
    delta_qty: float,
    incoming_rate: float = 0.0,
    valuation_rate: float = 0.0,
    stock_value_difference: float = 0.0,
) -> tuple[float, float, float]:
    """Pure moving-average valuation math — the single source of truth for how
    a stock movement (or value-only adjustment) changes a Bin's qty/value/rate.
    No DB access, so it's directly unit-testable; StockLedgerEntry._update_bin()
    calls this rather than duplicating the branching logic inline.

    Returns (new_qty, new_value, new_rate).

    - delta_qty > 0 (incoming): blend the new layer's cost into the running
      value. incoming_rate is what this stock actually cost; valuation_rate
      is the fallback if incoming_rate wasn't supplied.
    - delta_qty < 0 (outgoing): draw down at the bin's OWN existing average
      rate — never at valuation_rate/incoming_rate off the moving SLE, which
      can be 0/FIFO/stale and would otherwise corrupt the value of the stock
      that's staying put.
    - delta_qty == 0 and stock_value_difference != 0: a value-only adjustment
      (e.g. a Landed Cost Voucher capitalizing freight/duty into stock that's
      already on hand) — shift stock_value by stock_value_difference without
      touching qty.
    - delta_qty == 0 and stock_value_difference == 0: no-op.
    """
    new_qty = flt(old_qty) + flt(delta_qty)

    if delta_qty > 0:
        in_rate = flt(incoming_rate) or flt(valuation_rate)
        new_value = flt(old_value) + (flt(delta_qty) * in_rate)
    elif delta_qty < 0:
        existing_rate = (flt(old_value) / flt(old_qty)) if flt(old_qty) else 0.0
        new_value = flt(old_value) + (flt(delta_qty) * existing_rate)  # delta_qty negative
    elif flt(stock_value_difference) != 0:
        new_value = flt(old_value) + flt(stock_value_difference)
    else:
        new_value = flt(old_value)

    new_value = max(0.0, new_value)
    new_rate = (new_value / new_qty) if new_qty > 0 else 0.0
    return new_qty, new_value, new_rate


def get_total_stock_value(warehouse: str | None = None, company: str | None = None) -> float:
    """Sum of stock_value across all Bins, optionally filtered."""
    filters = {}
    if warehouse:
        filters["warehouse"] = warehouse
    if company:
        filters["company"] = company
    rows = frappe.get_all("Bin", filters=filters, fields=["stock_value"])
    return sum(flt(r.stock_value) for r in rows)


# ── Reorder Alerts ────────────────────────────────────────────────────────────

def get_reorder_alerts(company: str | None = None) -> list[dict]:
    """
    Return items where actual_qty < reorder_level.
    Joins Bin with Item to get reorder thresholds.
    """
    company_cond = "AND b.company = %(company)s" if company else ""
    params = {"company": company} if company else {}

    return frappe.db.sql(f"""
        SELECT
            b.item_code,
            i.item_name,
            b.warehouse,
            b.actual_qty,
            b.reorder_level,
            b.reorder_qty,
            b.stock_uom,
            b.valuation_rate,
            (b.reorder_qty - b.actual_qty) AS shortage_qty
        FROM `tabBin` b
        JOIN `tabItem` i ON i.name = b.item_code
        WHERE b.reorder_level > 0
          AND b.actual_qty < b.reorder_level
          AND (i.disabled IS NULL OR i.disabled = 0)
          {company_cond}
        ORDER BY (b.reorder_level - b.actual_qty) DESC
    """, params, as_dict=True)


# ── Item Price Lookup ─────────────────────────────────────────────────────────

def get_item_price(item_code: str, price_list: str, uom: str | None = None,
                   as_of_date: str | None = None) -> float:
    """Return effective price_list_rate for an item + price list combination."""
    from zoho_books_clone.inventory.doctype.item_price.item_price import ItemPrice
    return ItemPrice.get_price(item_code, price_list, uom=uom, as_of_date=as_of_date)


# ── UOM Conversion ─────────────────────────────────────────────────────────────
#
# Single source of truth for "how many stock_uom units is 1 of this UOM".
# Every transaction doctype (Purchase Order/Invoice Item, Sales Order/Invoice
# Item, Stock Entry Detail, ...) must call this instead of reading an Item's
# uom_conversions table directly, so the lookup/fallback rules below only
# live in one place.

def get_conversion_factor(item_code: str, uom: str | None) -> float:
    """
    Return the factor to multiply a qty entered in `uom` by to get the
    equivalent qty in the item's stock_uom.

    Rules:
      - No item_code, no uom, or uom == the item's stock_uom → 1.0
        (entry UOM already IS the stock UOM; conversion is a no-op).
      - uom matches a row in the item's `uom_conversions` child table →
        that row's conversion_factor.
      - uom is set but has no matching row (e.g. a stale/typo'd UOM, or
        the item's conversions were never configured for it) → falls back
        to 1.0 rather than throwing, so a bad/missing UOM never silently
        multiplies a quantity by some unrelated factor; callers that need
        to *require* a configured conversion should check for that
        explicitly rather than rely on this function to fail loudly.
    """
    if not item_code or not uom:
        return 1.0

    stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")
    if not stock_uom or uom == stock_uom:
        return 1.0

    factor = frappe.db.get_value(
        "Item UOM Conversion Detail",
        {"parent": item_code, "parenttype": "Item", "uom": uom},
        "conversion_factor",
    )
    return flt(factor) if factor else 1.0


def get_qty_in_stock_uom(item_code: str, qty: float, uom: str | None) -> float:
    """Convenience wrapper: qty entered in `uom` → equivalent qty in stock_uom."""
    return flt(qty) * get_conversion_factor(item_code, uom)


# ── Stock Ledger History ──────────────────────────────────────────────────────

def get_stock_ledger(
    item_code: str | None = None,
    warehouse: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 500,
) -> list[dict]:
    """Paginated stock ledger history with optional filters."""
    conditions = ["is_cancelled = 0"]
    params: dict = {}

    if item_code:
        conditions.append("item_code = %(item_code)s")
        params["item_code"] = item_code
    if warehouse:
        conditions.append("warehouse = %(warehouse)s")
        params["warehouse"] = warehouse
    if from_date:
        conditions.append("posting_date >= %(from_date)s")
        params["from_date"] = from_date
    if to_date:
        conditions.append("posting_date <= %(to_date)s")
        params["to_date"] = to_date

    where = " AND ".join(conditions)
    params["limit"] = int(limit)

    return frappe.db.sql(f"""
        SELECT
            name, item_code, warehouse, posting_date, voucher_type, voucher_no,
            actual_qty, qty_after_transaction, incoming_rate, valuation_rate,
            stock_value, stock_value_difference
        FROM `tabStock Ledger Entry`
        WHERE {where}
        ORDER BY posting_date DESC, creation DESC
        LIMIT %(limit)s
    """, params, as_dict=True)


# ── Bin Recalculation (Audit-5) ───────────────────────────────────────────────

def recalculate_bin(item_code: str, warehouse: str) -> dict:
    """
    Audit-5: Recompute the Bin balance from the authoritative Stock Ledger Entries
    and write it back to the Bin table.

    Use this when you suspect Bin drift (e.g., after direct DB edits, cancelled
    entries, or a concurrency incident).  Returns a dict describing what changed.

    This function is idempotent — calling it multiple times is safe.
    """
    # Sum all active SLEs for this item+warehouse
    result = frappe.db.sql("""
        SELECT
            COALESCE(SUM(actual_qty),            0) AS total_qty,
            COALESCE(SUM(stock_value_difference), 0) AS total_value
        FROM `tabStock Ledger Entry`
        WHERE item_code    = %(item_code)s
          AND warehouse    = %(warehouse)s
          AND is_cancelled = 0
    """, {"item_code": item_code, "warehouse": warehouse}, as_dict=True)

    correct_qty   = flt(result[0].total_qty)   if result else 0.0
    correct_value = flt(result[0].total_value) if result else 0.0
    correct_rate  = (correct_value / correct_qty) if correct_qty else 0.0

    bin_name = frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse})

    if not bin_name:
        # Create the Bin so future queries have a record to read
        b = frappe.get_doc({
            "doctype":        "Bin",
            "item_code":      item_code,
            "warehouse":      warehouse,
            "actual_qty":     correct_qty,
            "reserved_qty":   0,
            "ordered_qty":    0,
            "projected_qty":  correct_qty,
            "valuation_rate": correct_rate,
            "stock_value":    correct_value,
        })
        b.flags.ignore_links = True
        b.flags.ignore_mandatory = True
        b.insert(ignore_permissions=True)
        return {
            "item_code": item_code,
            "warehouse": warehouse,
            "status":    "created",
            "new_qty":   correct_qty,
            "new_value": correct_value,
        }

    old_qty   = flt(frappe.db.get_value("Bin", bin_name, "actual_qty"))
    old_value = flt(frappe.db.get_value("Bin", bin_name, "stock_value"))
    ordered   = flt(frappe.db.get_value("Bin", bin_name, "ordered_qty"))
    reserved  = flt(frappe.db.get_value("Bin", bin_name, "reserved_qty"))

    frappe.db.set_value("Bin", bin_name, {
        "actual_qty":     correct_qty,
        "stock_value":    correct_value,
        "valuation_rate": correct_rate,
        "projected_qty":  correct_qty + ordered - reserved,
    }, update_modified=True)

    return {
        "item_code":    item_code,
        "warehouse":    warehouse,
        "status":       "recalculated",
        "old_qty":      old_qty,
        "new_qty":      correct_qty,
        "qty_drift":    correct_qty - old_qty,
        "old_value":    old_value,
        "new_value":    correct_value,
        "value_drift":  correct_value - old_value,
    }


def recalculate_all_bins(warehouse: str | None = None) -> list[dict]:
    """
    Recalculate every Bin from SLEs, optionally scoped to a single warehouse.
    Also creates Bins for item+warehouse pairs that have SLEs but no Bin yet.
    Returns a list of recalculation result dicts (one per item+warehouse pair).
    """
    wh_cond = "AND warehouse = %(warehouse)s" if warehouse else ""
    params  = {"warehouse": warehouse} if warehouse else {}

    # Collect all distinct item+warehouse pairs from active SLEs
    pairs = frappe.db.sql(f"""
        SELECT DISTINCT item_code, warehouse
        FROM `tabStock Ledger Entry`
        WHERE is_cancelled = 0
        {wh_cond}
        ORDER BY item_code, warehouse
    """, params, as_dict=True)

    return [recalculate_bin(p.item_code, p.warehouse) for p in pairs]


# ── Bin Upsert (helper for controllers) ──────────────────────────────────────

def get_or_create_bin(item_code: str, warehouse: str, company: str = "") -> str:
    """Return name of Bin for item+warehouse, creating it if necessary."""
    name = frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse})
    if name:
        return name

    if not company:
        company = (
            frappe.db.get_single_value("Books Settings", "default_company")
            or frappe.db.get_default("company")
            or ""
        )

    uom = frappe.db.get_value("Item", item_code, "stock_uom") or "Nos"
    reorder_level = frappe.db.get_value("Item", item_code, "reorder_level") or 0
    reorder_qty   = frappe.db.get_value("Item", item_code, "reorder_qty")   or 0

    bin_doc = frappe.get_doc({
        "doctype": "Bin",
        "item_code": item_code,
        "warehouse": warehouse,
        "company": company,
        "stock_uom": uom,
        "actual_qty": 0,
        "reserved_qty": 0,
        "ordered_qty": 0,
        "projected_qty": 0,
        "stock_value": 0,
        "valuation_rate": 0,
        "reorder_level": reorder_level,
        "reorder_qty": reorder_qty,
    })
    bin_doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return bin_doc.name


# ── Bin Delta Update ──────────────────────────────────────────────────────────

def update_bin(
    item_code: str,
    warehouse: str,
    actual_qty_delta: float = 0.0,
    reserved_qty_delta: float = 0.0,
    ordered_qty_delta: float = 0.0,
    company: str = "",
    incoming_rate: float = 0.0,
) -> None:
    """
    Apply signed deltas to a Bin row (creating it if needed) and keep
    projected_qty, stock_value, and valuation_rate consistent.

    Call this from every document that moves stock or changes commitments:
      - Sales Order submit/cancel  → reserved_qty_delta ±qty
      - Purchase Order submit/cancel → ordered_qty_delta ±qty
      - Purchase Receipt submit/cancel → actual_qty_delta ±qty, ordered_qty_delta ∓qty
      - Delivery Note submit/cancel → actual_qty_delta ∓qty, reserved_qty_delta ∓qty
    """
    bin_name = get_or_create_bin(item_code, warehouse, company)

    row = frappe.db.get_value(
        "Bin", bin_name,
        ["actual_qty", "reserved_qty", "ordered_qty", "stock_value", "valuation_rate"],
        as_dict=True,
    )

    new_actual   = max(0.0, flt(row.actual_qty)   + flt(actual_qty_delta))
    new_reserved = max(0.0, flt(row.reserved_qty) + flt(reserved_qty_delta))
    new_ordered  = max(0.0, flt(row.ordered_qty)  + flt(ordered_qty_delta))
    new_projected = new_actual + new_ordered - new_reserved

    # Recalculate stock value using moving-average when actual stock changes
    if flt(actual_qty_delta) != 0 and flt(incoming_rate) > 0:
        added_value = flt(actual_qty_delta) * flt(incoming_rate)
        new_stock_value = max(0.0, flt(row.stock_value) + added_value)
        new_valuation = new_stock_value / new_actual if new_actual > 0 else 0.0
    elif flt(actual_qty_delta) < 0:
        # Stock going out: reduce value proportionally
        rate = flt(row.valuation_rate) or 0.0
        new_stock_value = max(0.0, flt(row.stock_value) + flt(actual_qty_delta) * rate)
        new_valuation = new_stock_value / new_actual if new_actual > 0 else 0.0
    else:
        new_stock_value = flt(row.stock_value)
        new_valuation   = flt(row.valuation_rate)

    frappe.db.set_value("Bin", bin_name, {
        "actual_qty":     round(new_actual,    4),
        "reserved_qty":   round(new_reserved,  4),
        "ordered_qty":    round(new_ordered,   4),
        "projected_qty":  round(new_projected, 4),
        "stock_value":    round(new_stock_value, 2),
        "valuation_rate": round(new_valuation,   4),
    }, update_modified=True)


# ── Stock Ledger Entry Creator ────────────────────────────────────────────────

def make_sle(
    item_code: str,
    warehouse: str,
    actual_qty: float,
    voucher_type: str,
    voucher_no: str,
    company: str = "",
    incoming_rate: float = 0.0,
    posting_date: str = "",
) -> None:
    """Insert a Stock Ledger Entry row and update the Bin accordingly."""
    from frappe.utils import today, nowtime

    if not posting_date:
        posting_date = today()

    bin_name = get_or_create_bin(item_code, warehouse, company)
    qty_after = flt(frappe.db.get_value("Bin", bin_name, "actual_qty")) + flt(actual_qty)
    val_rate  = flt(frappe.db.get_value("Bin", bin_name, "valuation_rate")) or flt(incoming_rate)

    # Outgoing: use current valuation rate; Incoming: use supplied rate or existing rate
    if flt(actual_qty) > 0:
        rate_to_use = flt(incoming_rate) or val_rate
    else:
        rate_to_use = val_rate

    stock_val_diff = flt(actual_qty) * rate_to_use

    frappe.get_doc({
        "doctype":                "Stock Ledger Entry",
        "item_code":              item_code,
        "warehouse":              warehouse,
        "posting_date":           posting_date,
        "posting_time":           nowtime(),
        "voucher_type":           voucher_type,
        "voucher_no":             voucher_no,
        "company":                company,
        "actual_qty":             round(flt(actual_qty), 4),
        "qty_after_transaction":  round(qty_after, 4),
        "incoming_rate":          round(rate_to_use, 4) if flt(actual_qty) > 0 else 0,
        "valuation_rate":         round(rate_to_use, 4),
        "stock_value":            round(max(0, qty_after * rate_to_use), 2),
        "stock_value_difference": round(stock_val_diff, 2),
        "is_cancelled":           0,
    }).insert(ignore_permissions=True)