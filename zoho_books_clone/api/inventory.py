"""
Inventory API — whitelisted endpoints called by the Books SPA.

All endpoints return plain dicts/lists that Vue can consume directly.
Heavy queries are delegated to inventory.utils or db.queries.
"""

import frappe
from frappe import _
from frappe.utils import flt, today, getdate
from zoho_books_clone.api.session import _get_company

from zoho_books_clone.inventory.utils import (
    get_stock_balance,
    get_stock_ledger,
    get_reorder_alerts,
    get_item_price,
    recalculate_bin,
    recalculate_all_bins,
)


# ── Stock Summary ─────────────────────────────────────────────────────────────

def _get_child_warehouses(warehouse_name):
    """Recursively collect all leaf warehouse names under a group warehouse."""
    children = frappe.get_all("Warehouse", filters={"parent_warehouse": warehouse_name}, fields=["name", "is_group"])
    result = []
    for c in children:
        if c.is_group:
            result.extend(_get_child_warehouses(c.name))
        else:
            result.append(c.name)
    return result


@frappe.whitelist(allow_guest=False)
def get_batches_for_item(item_code, search=None):
    """
    Return existing, non-disabled batches for a single item with LIVE qty
    computed from Stock Ledger Entries (across all warehouses).

    Batch.batch_qty is only an incrementally-adjusted cache (see
    stock_entry.py._adjust_batch_qty) and can drift from the real ledger
    over time. Batch pickers (Bill / Purchase Receipt / PO-to-Bill / Stock
    Entry) should show the true remaining qty, not the cached field, so
    this mirrors get_warehouse_batches's SLE aggregation but scoped to one
    item across all warehouses.
    """
    if not item_code:
        return []
    rows = frappe.db.sql("""
        SELECT sle.batch_no, SUM(sle.actual_qty) AS qty
        FROM `tabStock Ledger Entry` sle
        WHERE sle.item_code = %(item_code)s
          AND sle.batch_no IS NOT NULL AND sle.batch_no != ''
          AND sle.is_cancelled = 0
        GROUP BY sle.batch_no
        HAVING qty > 0
        ORDER BY sle.batch_no
    """, {"item_code": item_code}, as_dict=True)

    if not rows:
        return []

    batch_nos = [r.batch_no for r in rows]
    meta = {
        b.name: b for b in frappe.get_all(
            "Batch", filters={"name": ["in", batch_nos]},
            fields=["name", "manufacturing_date", "expiry_date", "disabled"],
        )
    }

    q = (search or "").lower().strip()
    out = []
    for r in rows:
        m = meta.get(r.batch_no) or {}
        if m.get("disabled"):
            continue
        if q and q not in r.batch_no.lower():
            continue
        out.append({
            "batch_no":           r.batch_no,
            "qty":                flt(r.qty),
            "manufacturing_date": m.get("manufacturing_date"),
            "expiry_date":        m.get("expiry_date"),
        })
    return out


@frappe.whitelist(allow_guest=False)
def get_warehouse_batches(warehouse):
    """
    Return batch-wise stock breakdown for every batch-tracked item in a warehouse.
    Response: { item_code: [ {batch_no, qty, manufacturing_date, expiry_date,
                               is_expired, expires_soon}, ... ], ... }
    Aggregates Stock Ledger Entry.actual_qty by item_code + batch_no so it always
    reflects the live ledger (not just the most recent Batch master values).
    For group warehouses, all child warehouse leaves are included.
    """
    if not warehouse:
        return {}

    warehouses = [warehouse]
    wh_doc = frappe.db.get_value("Warehouse", warehouse, "is_group")
    if wh_doc:
        children = _get_child_warehouses(warehouse)
        if not children:
            return {}
        warehouses = children

    rows = frappe.db.sql("""
        SELECT sle.item_code, sle.batch_no, SUM(sle.actual_qty) AS qty
        FROM `tabStock Ledger Entry` sle
        WHERE sle.warehouse IN %(warehouses)s
          AND sle.batch_no IS NOT NULL AND sle.batch_no != ''
          AND sle.is_cancelled = 0
        GROUP BY sle.item_code, sle.batch_no
        HAVING qty != 0
        ORDER BY sle.item_code, sle.batch_no
    """, {"warehouses": warehouses}, as_dict=True)

    if not rows:
        return {}

    batch_nos = list({r.batch_no for r in rows})
    batch_meta = {
        b.name: b for b in frappe.get_all(
            "Batch", filters={"name": ["in", batch_nos]},
            fields=["name", "manufacturing_date", "expiry_date"],
        )
    }

    today_date = getdate(today())
    out = {}
    for r in rows:
        meta = batch_meta.get(r.batch_no) or {}
        expiry = meta.get("expiry_date")
        days_to_expiry = (getdate(expiry) - today_date).days if expiry else None
        out.setdefault(r.item_code, []).append({
            "batch_no":            r.batch_no,
            "qty":                 flt(r.qty),
            "manufacturing_date":  meta.get("manufacturing_date"),
            "expiry_date":         expiry,
            "is_expired":          bool(expiry and days_to_expiry < 0),
            "expires_soon":        bool(expiry and 0 <= days_to_expiry <= 30),
        })
    return out


@frappe.whitelist(allow_guest=False)
def get_stock_summary(warehouse=None, item_group=None, show_zero_stock=0):
    """
    Return current stock levels (from Bin) with item details.
    If warehouse is a group (is_group=1), aggregates all children recursively.
    """
    filters = {}
    is_group_wh = False
    if warehouse:
        wh_doc = frappe.db.get_value("Warehouse", warehouse, ["is_group", "name"], as_dict=True)
        if wh_doc and wh_doc.is_group:
            is_group_wh = True
            child_whs = _get_child_warehouses(warehouse)
            if child_whs:
                filters["warehouse"] = ["in", child_whs]
            else:
                return []  # Group with no children yet
        else:
            filters["warehouse"] = warehouse
    if not int(show_zero_stock):
        filters["actual_qty"] = [">", 0]

    bins = frappe.get_all(
        "Bin",
        filters=filters,
        fields=["item_code", "warehouse", "actual_qty", "reserved_qty",
                "ordered_qty", "projected_qty", "valuation_rate", "stock_value",
                "reorder_level", "reorder_qty", "stock_uom"],
        order_by="item_code asc",
        limit=2000,
    )

    # Enrich with item details
    item_codes = list({b.item_code for b in bins})
    item_map = {}
    if item_codes:
        items = frappe.get_all(
            "Item",
            filters={"name": ["in", item_codes]},
            fields=["name", "item_name", "item_group", "stock_uom", "disabled", "has_batch_no"],
        )
        for it in items:
            item_map[it.name] = it

    # For group warehouses aggregate all child bins by item_code
    if is_group_wh:
        agg = {}
        for b in bins:
            item = item_map.get(b.item_code, {})
            if item_group and item.get("item_group") != item_group:
                continue
            if b.item_code not in agg:
                agg[b.item_code] = {
                    "item_code":    b.item_code,
                    "item_name":    item.get("item_name") or b.item_code,
                    "item_group":   item.get("item_group") or "",
                    "warehouse":    warehouse,  # show parent name
                    "uom":          b.stock_uom or item.get("stock_uom") or "Nos",
                    "actual_qty":   0.0, "reserved_qty": 0.0, "ordered_qty": 0.0,
                    "projected_qty": 0.0, "stock_value": 0.0,
                    "valuation_rate": flt(b.valuation_rate),
                    "reorder_level": flt(b.reorder_level),
                    "reorder_qty":   flt(b.reorder_qty),
                    "has_batch_no":  1 if item.get("has_batch_no") else 0,
                }
            agg[b.item_code]["actual_qty"]    += flt(b.actual_qty)
            agg[b.item_code]["reserved_qty"]  += flt(b.reserved_qty)
            agg[b.item_code]["ordered_qty"]   += flt(b.ordered_qty)
            agg[b.item_code]["projected_qty"] += flt(b.projected_qty)
            agg[b.item_code]["stock_value"]   += flt(b.stock_value)
        return [dict(r, below_reorder=r["actual_qty"] < r["reorder_level"] if r["reorder_level"] else False)
                for r in agg.values()]

    result = []
    seen_codes = set()

    for b in bins:
        item = item_map.get(b.item_code, {})
        if item_group and item.get("item_group") != item_group:
            continue
        seen_codes.add(b.item_code)
        result.append({
            "item_code":       b.item_code,
            "item_name":       item.get("item_name") or b.item_code,
            "item_group":      item.get("item_group") or "",
            "warehouse":       b.warehouse,
            "uom":             b.stock_uom or item.get("stock_uom") or "Nos",
            "actual_qty":      flt(b.actual_qty),
            "reserved_qty":    flt(b.reserved_qty),
            "ordered_qty":     flt(b.ordered_qty),
            "projected_qty":   flt(b.projected_qty),
            "valuation_rate":  flt(b.valuation_rate),
            "stock_value":     flt(b.stock_value),
            "reorder_level":   flt(b.reorder_level),
            "reorder_qty":     flt(b.reorder_qty),
            "below_reorder":   flt(b.actual_qty) < flt(b.reorder_level) if b.reorder_level else False,
            "has_batch_no":    1 if item.get("has_batch_no") else 0,
        })

    # Also show items that have this warehouse as default_warehouse but no Bin yet (0 stock)
    if warehouse:
        try:
            default_items = frappe.get_all(
                "Item",
                filters={"default_warehouse": warehouse, "is_stock_item": 1, "disabled": 0},
                fields=["name", "item_name", "item_group", "stock_uom", "reorder_level", "reorder_qty"],
                limit=500,
            )
            for it in default_items:
                if it.name in seen_codes:
                    continue
                if item_group and it.get("item_group") != item_group:
                    continue
                result.append({
                    "item_code":      it.name,
                    "item_name":      it.item_name or it.name,
                    "item_group":     it.item_group or "",
                    "warehouse":      warehouse,
                    "uom":            it.stock_uom or "Nos",
                    "actual_qty":     0.0,
                    "reserved_qty":   0.0,
                    "ordered_qty":    0.0,
                    "projected_qty":  0.0,
                    "valuation_rate": 0.0,
                    "stock_value":    0.0,
                    "reorder_level":  flt(it.reorder_level),
                    "reorder_qty":    flt(it.reorder_qty),
                    "below_reorder":  False,
                    "no_stock_entry": True,
                })
        except Exception:
            pass

    return result


@frappe.whitelist(allow_guest=False)
def create_opening_stock():
    """
    Create and submit an Opening Stock (or Material Receipt) entry for an item.
    replace_existing=1 → always creates a Material Receipt regardless of prior SLEs.
    Returns the Stock Entry name.
    """
    from frappe.utils import today as frappe_today
    # Read from form_dict directly to avoid Frappe's argument-filtering stripping params
    fd = frappe.form_dict
    item_code      = fd.get("item_code") or ""
    item_name      = fd.get("item_name") or item_code
    warehouse      = fd.get("warehouse") or ""
    qty            = flt(fd.get("qty", 0))
    rate           = flt(fd.get("rate", 0))
    replace_existing = int(fd.get("replace_existing", 0))
    if qty <= 0:
        frappe.throw(_("Opening Stock qty must be greater than 0"))
    if not warehouse:
        frappe.throw(_("Warehouse is required for Opening Stock"))

    company = _get_company(frappe.session.user)

    # Determine entry type: Opening Stock if no prior SLEs, else Material Receipt
    prior = frappe.db.sql(
        """SELECT name FROM `tabStock Ledger Entry`
           WHERE item_code=%s AND warehouse=%s AND is_cancelled=0 LIMIT 1""",
        (item_code, warehouse), as_dict=True
    )
    entry_type = "Material Receipt" if (prior or int(replace_existing)) else "Opening Stock"

    se = frappe.get_doc({
        "doctype":          "Stock Entry",
        "stock_entry_type": entry_type,
        "posting_date":     frappe_today(),
        "company":          company,
        "remarks":          f"Opening stock for {item_code}",
        "items": [{
            "item_code":  item_code,
            "item_name":  item_name or item_code,
            "qty":        qty,
            "basic_rate": rate,
            "t_warehouse": warehouse,
        }],
    })
    # Pre-set name to bypass naming_series autoname entirely
    se.name = "SEC-" + frappe.generate_hash(txt=f"{item_code}{frappe.utils.now()}", length=8).upper()
    se.flags.ignore_permissions = True
    se.flags.ignore_links = True
    se.flags.ignore_mandatory = True
    se.insert()
    se.submit()
    frappe.db.commit()
    return {"stock_entry": se.name, "entry_type": entry_type, "qty": qty}


@frappe.whitelist(allow_guest=False)
def get_item_stock_detail(item_code, warehouse=None):
    """
    Return stock position for a single item across all (or one) warehouse(s).
    """
    filters = {"item_code": item_code}
    if warehouse:
        filters["warehouse"] = warehouse

    bins = frappe.get_all(
        "Bin",
        filters=filters,
        fields=["warehouse", "actual_qty", "reserved_qty", "ordered_qty",
                "projected_qty", "valuation_rate", "stock_value"],
    )

    item = frappe.get_value(
        "Item", item_code,
        ["item_name", "stock_uom", "item_group", "standard_rate"],
        as_dict=True,
    ) or {}

    return {
        "item_code":    item_code,
        "item_name":    item.get("item_name") or item_code,
        "stock_uom":    item.get("stock_uom") or "Nos",
        "item_group":   item.get("item_group") or "",
        "selling_rate": flt(item.get("standard_rate")),
        "warehouses":   [
            {
                "warehouse":     b.warehouse,
                "actual_qty":    flt(b.actual_qty),
                "reserved_qty":  flt(b.reserved_qty),
                "ordered_qty":   flt(b.ordered_qty),
                "projected_qty": flt(b.projected_qty),
                "valuation_rate":flt(b.valuation_rate),
                "stock_value":   flt(b.stock_value),
            }
            for b in bins
        ],
        "total_qty":   sum(flt(b.actual_qty) for b in bins),
        "total_value": sum(flt(b.stock_value) for b in bins),
    }


# ── Inventory Adjustments ─────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["POST"])
def create_inventory_adjustment():
    """
    Zoho-style quantity adjustment: enter the new counted on-hand qty for an
    item+warehouse; we post the +/- delta as a 'Stock Adjustment' Stock Entry at
    the current valuation rate. The Stock Entry controller handles the SLE/Bin
    update and the GL (DR Inventory / CR adjustment account).
    """
    from frappe.utils import today as frappe_today
    fd = frappe.form_dict
    item_code = (fd.get("item_code") or "").strip()
    warehouse = (fd.get("warehouse") or "").strip()
    reason    = (fd.get("reason") or "").strip()
    notes     = (fd.get("notes") or "").strip()
    adj_account = (fd.get("adjustment_account") or "").strip()
    posting_date = fd.get("posting_date") or frappe_today()

    if not item_code:
        frappe.throw(_("Item is required"))
    if not warehouse:
        frappe.throw(_("Warehouse is required"))
    if fd.get("new_qty") in (None, ""):
        frappe.throw(_("New quantity is required"))

    new_qty = flt(fd.get("new_qty"))
    if new_qty < 0:
        frappe.throw(_("New quantity cannot be negative"))

    company = _get_company(frappe.session.user)

    bin_row = frappe.db.get_value(
        "Bin", {"item_code": item_code, "warehouse": warehouse},
        ["actual_qty", "valuation_rate"], as_dict=True,
    ) or {}
    current_qty = flt(bin_row.get("actual_qty"))
    rate = flt(bin_row.get("valuation_rate"))
    if not rate:
        item_rates = frappe.db.get_value(
            "Item", item_code, ["standard_buying_rate", "standard_rate"], as_dict=True
        ) or {}
        rate = flt(item_rates.get("standard_buying_rate")) or flt(item_rates.get("standard_rate")) or 0

    delta = new_qty - current_qty
    if abs(delta) < 0.0000001:
        frappe.throw(_("New quantity equals current quantity — nothing to adjust."))

    item_name = frappe.db.get_value("Item", item_code, "item_name") or item_code
    remark = reason + ((" — " + notes) if notes else "") if reason else (notes or f"Stock adjustment for {item_code}")

    se = frappe.get_doc({
        "doctype":          "Stock Entry",
        "stock_entry_type": "Stock Adjustment",
        "posting_date":     posting_date,
        "company":          company,
        "remarks":          remark,
        "adjustment_reason": reason or None,
        "adjustment_account": adj_account or None,
        "items": [{
            "item_code":  item_code,
            "item_name":  item_name,
            "qty":        delta,
            "basic_rate": rate,
            "t_warehouse": warehouse,
        }],
    })
    se.name = "SEC-" + frappe.generate_hash(txt=f"{item_code}{frappe.utils.now()}", length=8).upper()
    se.flags.ignore_permissions = True
    se.flags.ignore_links = True
    se.flags.ignore_mandatory = True
    se.insert()
    se.submit()
    frappe.db.commit()
    return {
        "stock_entry": se.name,
        "delta": delta,
        "new_qty": new_qty,
        "current_qty": current_qty,
        "rate": rate,
    }


@frappe.whitelist(allow_guest=False, methods=["POST"])
def create_batch_adjustment():
    """
    Batch-level counterpart to create_inventory_adjustment: correct the qty of
    a single batch within a warehouse (e.g. after a physical count finds a
    specific batch's on-hand quantity differs from the ledger).

    Posts the +/- delta as a 'Stock Adjustment' Stock Entry carrying the
    batch_no, exactly like a normal batch-tracked movement. That means it goes
    through the same controller path as every other Stock Entry:
      - Stock Ledger Entry is created for item+warehouse+batch (_make_sle)
      - Batch.batch_qty is adjusted by the same delta (_adjust_batch_qty)
      - Bin.actual_qty for the item is adjusted by the same delta (_sync_bin)
      - GL entries are posted for the delta value (_post_gl_entries)
    Since the delta is applied identically to the batch and to the item's
    overall Bin qty, SUM(batch qty) for the item always stays equal to the
    item's total actual_qty — this adjustment can't drift the two apart, and
    it never touches accounting outside the normal Stock Entry GL posting.
    """
    from frappe.utils import today as frappe_today
    fd = frappe.form_dict
    item_code = (fd.get("item_code") or "").strip()
    warehouse = (fd.get("warehouse") or "").strip()
    batch_no  = (fd.get("batch_no") or "").strip()
    reason    = (fd.get("reason") or "").strip()
    notes     = (fd.get("notes") or "").strip()
    adj_account = (fd.get("adjustment_account") or "").strip()
    posting_date = fd.get("posting_date") or frappe_today()

    if not item_code:
        frappe.throw(_("Item is required"))
    if not warehouse:
        frappe.throw(_("Warehouse is required"))
    if not batch_no:
        frappe.throw(_("Batch is required"))
    if fd.get("new_qty") in (None, ""):
        frappe.throw(_("New quantity is required"))

    new_qty = flt(fd.get("new_qty"))
    if new_qty < 0:
        frappe.throw(_("New quantity cannot be negative"))

    if not frappe.db.exists("Batch", batch_no):
        frappe.throw(_("Batch {0} does not exist").format(batch_no))
    batch_item = frappe.db.get_value("Batch", batch_no, "item")
    if batch_item and batch_item != item_code:
        frappe.throw(_("Batch {0} belongs to item {1}, not {2}").format(batch_no, batch_item, item_code))
    if frappe.db.get_value("Batch", batch_no, "disabled"):
        frappe.throw(_("Batch {0} is disabled and cannot be adjusted").format(batch_no))

    company = _get_company(frappe.session.user)

    # Current qty for THIS batch in THIS warehouse — read live off the ledger
    # (same aggregation get_warehouse_batches uses) so the delta we post is
    # relative to what the person is actually looking at on screen, not a
    # possibly-stale Batch.batch_qty snapshot.
    current_qty = flt(frappe.db.sql("""
        SELECT SUM(actual_qty) FROM `tabStock Ledger Entry`
        WHERE item_code=%s AND warehouse=%s AND batch_no=%s AND is_cancelled=0
    """, (item_code, warehouse, batch_no))[0][0] or 0)

    delta = new_qty - current_qty
    if abs(delta) < 0.0000001:
        frappe.throw(_("New quantity equals current batch quantity — nothing to adjust."))

    bin_row = frappe.db.get_value(
        "Bin", {"item_code": item_code, "warehouse": warehouse}, "valuation_rate",
    )
    rate = flt(bin_row)
    if not rate:
        item_rates = frappe.db.get_value(
            "Item", item_code, ["standard_buying_rate", "standard_rate"], as_dict=True
        ) or {}
        rate = flt(item_rates.get("standard_buying_rate")) or flt(item_rates.get("standard_rate")) or 0

    item_name = frappe.db.get_value("Item", item_code, "item_name") or item_code
    remark = (reason + ((" — " + notes) if notes else "") if reason
              else (notes or f"Batch stock adjustment for {item_code} / {batch_no}"))

    se = frappe.get_doc({
        "doctype":          "Stock Entry",
        "stock_entry_type": "Stock Adjustment",
        "posting_date":     posting_date,
        "company":          company,
        "remarks":          remark,
        "adjustment_reason": reason or None,
        "adjustment_account": adj_account or None,
        "items": [{
            "item_code":  item_code,
            "item_name":  item_name,
            "qty":        delta,
            "basic_rate": rate,
            "t_warehouse": warehouse,
            "batch_no":   batch_no,
        }],
    })
    se.name = "SEC-" + frappe.generate_hash(txt=f"{item_code}{batch_no}{frappe.utils.now()}", length=8).upper()
    se.flags.ignore_permissions = True
    se.flags.ignore_links = True
    se.flags.ignore_mandatory = True
    se.insert()
    se.submit()
    frappe.db.commit()

    new_bin_qty = flt(frappe.db.get_value(
        "Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty",
    ) or 0)

    return {
        "stock_entry": se.name,
        "delta": delta,
        "new_qty": new_qty,
        "current_qty": current_qty,
        "rate": rate,
        "item_actual_qty": new_bin_qty,
    }


@frappe.whitelist(allow_guest=False)
def get_inventory_adjustments(company=None):
    """List Stock-Adjustment entries (one row per entry, first item line)."""
    if not company:
        company = _get_company(frappe.session.user)
    rows = frappe.db.sql("""
        SELECT se.name, se.posting_date, se.docstatus, se.value_difference,
               se.adjustment_reason, se.remarks,
               sed.item_code, sed.item_name, sed.t_warehouse AS warehouse,
               sed.batch_no, sed.qty, sed.basic_rate
        FROM `tabStock Entry` se
        LEFT JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        WHERE se.stock_entry_type = 'Stock Adjustment' AND se.company = %s
        GROUP BY se.name
        ORDER BY se.posting_date DESC, se.creation DESC
        LIMIT 300
    """, (company,), as_dict=True)
    for r in rows:
        r["qty"] = flt(r.get("qty"))
        r["value"] = flt(r.get("qty")) * flt(r.get("basic_rate"))
    return rows


@frappe.whitelist(allow_guest=False)
def get_default_adjustment_account(company=None):
    """Return the company's Stock Adjustment leaf account (for prefilling the UI)."""
    if not company:
        company = _get_company(frappe.session.user)
    name = frappe.db.get_value(
        "Account",
        {"account_type": "Stock Adjustment", "company": company, "is_group": 0},
        "name",
    )
    return {"account": name or ""}


# ── Stock Ledger ──────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False)
def get_stock_ledger_entries(item_code=None, warehouse=None,
                              from_date=None, to_date=None, limit=200):
    """Paginated stock movement history."""
    return get_stock_ledger(
        item_code=item_code or None,
        warehouse=warehouse or None,
        from_date=from_date or None,
        to_date=to_date or None,
        limit=int(limit),
    )


# ── Reorder Alerts ────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False)
def get_reorder_items(company=None):
    """Return items that have fallen below their reorder level."""
    return get_reorder_alerts(company=company or None)


@frappe.whitelist(allow_guest=False)
def get_reorder_dashboard(company=None):
    """
    Return all stock items that have a reorder_level set, with their current
    stock and saved reorder config (supplier, auto_po_enabled, etc.).
    Used by the Reorder Management page.
    """
    items = frappe.get_all(
        "Item",
        filters={"reorder_level": [">", 0], "disabled": 0, "is_stock_item": 1},
        fields=[
            "name as item_code", "item_name", "stock_uom",
            "reorder_level", "reorder_qty",
            "default_warehouse",
            "reorder_supplier", "reorder_warehouse_override",
            "auto_po_enabled", "reorder_notes",
        ],
        order_by="item_name asc",
    )

    if not items:
        return []

    # Resolve actual_qty: sum across all warehouses (or scoped to company's warehouses)
    item_codes = [i["item_code"] for i in items]
    wh_filter  = {}
    if company:
        wh_filter["company"] = company

    bins = frappe.get_all(
        "Bin",
        filters={"item_code": ["in", item_codes], **wh_filter},
        fields=["item_code", "actual_qty"],
    )
    qty_map = {}
    for b in bins:
        qty_map[b.item_code] = qty_map.get(b.item_code, 0) + flt(b.actual_qty)

    for item in items:
        item["actual_qty"]     = flt(qty_map.get(item["item_code"], 0))
        item["below_reorder"]  = item["actual_qty"] < flt(item["reorder_level"])
        item["shortage_qty"]   = max(flt(item["reorder_level"]) - item["actual_qty"], 0)
        item["auto_po_enabled"] = int(item.get("auto_po_enabled") or 0)

    return items


@frappe.whitelist(allow_guest=False, methods=["POST"])
def save_item_reorder_config(item_code, supplier="", warehouse_override="",
                              reorder_qty=None, reorder_level=None,
                              auto_po_enabled=0, notes=""):
    """Save reorder config fields directly on the Item document."""
    if not frappe.db.exists("Item", item_code):
        frappe.throw(f"Item {item_code} not found")

    updates = {
        "reorder_supplier":           supplier or None,
        "reorder_warehouse_override": warehouse_override or None,
        "auto_po_enabled":            int(auto_po_enabled),
        "reorder_notes":              notes or "",
    }
    if reorder_qty is not None:
        updates["reorder_qty"] = flt(reorder_qty)
    if reorder_level is not None:
        updates["reorder_level"] = flt(reorder_level)

    frappe.db.set_value("Item", item_code, updates)
    frappe.db.commit()
    return {"success": True}


# ── Valuation Report ─────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False)
def get_stock_valuation_report(warehouse=None, as_of_date=None):
    """
    Stock valuation summary — total value per warehouse, and grand total.
    """
    filters = {"actual_qty": [">", 0]}
    if warehouse:
        filters["warehouse"] = warehouse

    bins = frappe.get_all(
        "Bin",
        filters=filters,
        fields=["warehouse", "stock_value"],
    )

    by_warehouse: dict[str, float] = {}
    for b in bins:
        by_warehouse[b.warehouse] = by_warehouse.get(b.warehouse, 0) + flt(b.stock_value)

    grand_total = sum(by_warehouse.values())

    return {
        "as_of_date":   as_of_date or today(),
        "by_warehouse": [{"warehouse": k, "stock_value": v} for k, v in sorted(by_warehouse.items())],
        "grand_total":  grand_total,
    }


# ── Item Price ────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False)
def get_item_price_list(item_code=None, price_list=None, as_of_date=None):
    """
    Return active Item Prices, optionally filtered by item or price list.
    """
    filters = {}
    if item_code:
        filters["item_code"] = item_code
    if price_list:
        filters["price_list"] = price_list

    prices = frappe.get_all(
        "Item Price",
        filters=filters,
        fields=["name", "item_code", "item_name", "price_list",
                "uom", "currency", "valid_from", "valid_upto", "price_list_rate"],
        order_by="item_code asc, valid_from desc",
        limit=1000,
    )

    date = as_of_date or today()
    result = []
    for p in prices:
        if p.valid_from and getdate(p.valid_from) > getdate(date):
            continue
        if p.valid_upto and getdate(p.valid_upto) < getdate(date):
            continue
        result.append(p)

    return result


@frappe.whitelist(allow_guest=False)
def get_price_for_item(item_code, price_list, uom=None, as_of_date=None):
    """Return a single effective rate for an item + price list (used by invoice line-fill)."""
    return {
        "item_code":       item_code,
        "price_list":      price_list,
        "price_list_rate": get_item_price(item_code, price_list, uom=uom, as_of_date=as_of_date),
    }


# ── Warehouse List ────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False)
def get_warehouses(disabled=0):
    """Return all active warehouses for dropdowns."""
    filters = {}
    if not int(disabled):
        filters["disabled"] = 0
    return frappe.get_all(
        "Warehouse",
        filters=filters,
        fields=["name", "warehouse_name", "warehouse_type", "parent_warehouse",
                "city", "is_group", "disabled"],
        order_by="warehouse_name asc",
    )


# ── Quick Stock Check ─────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False)
def check_stock_availability(item_code, warehouse, required_qty):
    """
    Used by Sales Order / Invoice to verify stock before confirming.
    Returns {available, sufficient, shortage}.
    """
    available = get_stock_balance(item_code, warehouse)
    req = flt(required_qty)
    return {
        "item_code":    item_code,
        "warehouse":    warehouse,
        "available_qty":available,
        "required_qty": req,
        "sufficient":   available >= req,
        "shortage":     max(0, req - available),
    }


# ── Dashboard KPIs (for Inventory section) ───────────────────────────────────

@frappe.whitelist(allow_guest=False)
def get_inventory_kpis(company=None):
    """
    Return key inventory metrics for the dashboard:
    - Total stock value
    - Items below reorder level
    - Total items tracked
    - Warehouses with stock
    """
    filters = {"actual_qty": [">", 0]}
    if company:
        filters["company"] = company

    bins = frappe.get_all("Bin", filters=filters,
                          fields=["item_code", "warehouse", "stock_value"])

    unique_items = len({b.item_code for b in bins})
    unique_wh    = len({b.warehouse for b in bins})
    total_value  = sum(flt(b.stock_value) for b in bins)

    reorder = get_reorder_alerts(company=company or None)

    return {
        "total_stock_value":   total_value,
        "unique_items_in_stock": unique_items,
        "warehouses_with_stock": unique_wh,
        "reorder_alerts":      len(reorder),
        "reorder_items":       reorder[:10],   # top-10 most critical
    }


# ── Bin Recalculation (Audit-5) ───────────────────────────────────────────────

@frappe.whitelist(allow_guest=False)
def recalculate_bin_from_ledger(item_code, warehouse):
    """
    Audit-5: Recompute a single Bin balance from Stock Ledger Entries.
    Use when you suspect Bin drift after cancellations or direct DB edits.
    Returns a summary of the before/after values.
    """
    return recalculate_bin(item_code, warehouse)


@frappe.whitelist(allow_guest=False)
def recalculate_all_bins_from_ledger(warehouse=None):
    """
    Audit-5: Recompute all Bin balances from Stock Ledger Entries.
    Optionally scoped to a single warehouse.
    Returns a list of per-Bin result dicts with drift information.
    """
    return recalculate_all_bins(warehouse=warehouse or None)


# ── Manual Stock Entry ────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False)
def create_stock_entry():
    """
    Create and submit a manual Stock Entry.
    Reads all parameters from frappe.form_dict.

    Required fields:
      entry_type  — "Material Receipt" | "Material Issue" | "Material Transfer"
                    | "Stock Adjustment" | "Opening Stock"
      items       — JSON list of {item_code, item_name, qty, basic_rate,
                                  t_warehouse?, s_warehouse?}

    Optional:
      posting_date, remarks, from_warehouse, to_warehouse
    """
    import json
    fd = frappe.form_dict

    entry_type   = fd.get("entry_type") or ""
    items_raw    = fd.get("items") or "[]"
    posting_date = fd.get("posting_date") or today()
    remarks      = fd.get("remarks") or ""
    from_wh      = fd.get("from_warehouse") or ""
    to_wh        = fd.get("to_warehouse") or ""

    VALID_TYPES = ("Material Receipt", "Material Issue", "Material Transfer",
                   "Stock Adjustment", "Opening Stock")
    if entry_type not in VALID_TYPES:
        frappe.throw(f"Invalid entry_type '{entry_type}'. Must be one of: {', '.join(VALID_TYPES)}")

    if isinstance(items_raw, str):
        items = json.loads(items_raw)
    else:
        items = list(items_raw)

    if not items:
        frappe.throw("At least one item is required.")

    # Apply header-level warehouses as defaults for each row
    for row in items:
        if from_wh and not row.get("s_warehouse"):
            row["s_warehouse"] = from_wh
        if to_wh and not row.get("t_warehouse"):
            row["t_warehouse"] = to_wh

    company = _get_company(frappe.session.user)

    se = frappe.get_doc({
        "doctype":           "Stock Entry",
        "stock_entry_type":  entry_type,
        "posting_date":      posting_date,
        "company":           company,
        "from_warehouse":    from_wh,
        "to_warehouse":      to_wh,
        "remarks":           remarks,
        "items":             items,
    })
    se.name = "SEC-" + frappe.generate_hash(
        txt=f"{entry_type}{frappe.utils.now()}", length=8
    ).upper()
    se.flags.ignore_permissions = True
    se.flags.ignore_links = True
    se.flags.ignore_mandatory = True
    se.insert()
    se.submit()
    frappe.db.commit()

    return {
        "stock_entry":  se.name,
        "entry_type":   entry_type,
        "items_count":  len(items),
        "posting_date": posting_date,
    }


@frappe.whitelist(allow_guest=False)
def get_stock_entries(entry_type=None, from_date=None, to_date=None, warehouse=None, limit=100):
    """Return submitted stock entries with optional filters."""
    filters = {"docstatus": 1}
    if entry_type:
        filters["stock_entry_type"] = entry_type
    if from_date:
        filters["posting_date"] = [">=", from_date]
    if to_date:
        if "posting_date" in filters:
            filters["posting_date"] = ["between", [from_date or "2000-01-01", to_date]]
        else:
            filters["posting_date"] = ["<=", to_date]
    if warehouse:
        filters["from_warehouse"] = warehouse

    entries = frappe.get_all(
        "Stock Entry",
        filters=filters,
        fields=["name", "stock_entry_type", "posting_date", "company",
                "from_warehouse", "to_warehouse", "remarks",
                "total_outgoing_value", "total_incoming_value"],
        order_by="posting_date desc, creation desc",
        limit=int(limit),
    )
    # Attach items to each entry
    for se in entries:
        se["items"] = frappe.get_all(
            "Stock Entry Detail",
            filters={"parent": se.name},
            fields=["item_code", "item_name", "qty", "basic_rate", "amount",
                    "s_warehouse", "t_warehouse"],
        )
    return entries


# ── Reorder → Purchase Order ──────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["POST"])
def create_po_from_reorder(items=None, supplier=None, company=None):
    """
    Create a draft Purchase Order from a list of reorder items.
    `items` is a JSON list of {item_code, qty, warehouse} dicts.
    Returns the new PO name.
    """
    import json
    from frappe.utils import flt, today

    if isinstance(items, str):
        items = json.loads(items)
    if not items:
        frappe.throw("No items provided")

    if not company:
        company = (
            frappe.db.get_single_value("Books Settings", "default_company")
            or frappe.db.get_default("company")
            or ""
        )

    po_items = []
    for row in items:
        item_code = row.get("item_code")
        if not item_code:
            continue
        item_doc = frappe.get_cached_doc("Item", item_code)
        qty = flt(row.get("qty")) or flt(
            frappe.db.get_value("Bin",
                {"item_code": item_code, "warehouse": row.get("warehouse")},
                "reorder_qty") or 0
        )
        if qty <= 0:
            qty = 1
        rate = flt(item_doc.get("standard_buying_rate") or item_doc.get("standard_rate") or 0)
        po_items.append({
            "item_code":  item_code,
            "item_name":  item_doc.item_name,
            "description": item_doc.description or item_doc.item_name,
            "qty":        qty,
            "uom":        item_doc.stock_uom or "Nos",
            "rate":       rate,
            "amount":     qty * rate,
        })

    po = frappe.get_doc({
        "doctype":          "Purchase Order",
        "supplier":         supplier or "",
        "transaction_date": today(),
        "company":          company,
        "items":            po_items,
    })
    po.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": po.name}