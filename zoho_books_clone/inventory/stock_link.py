from __future__ import annotations
"""
Stock Link — Audit fixes P2/Audit-2 and P2/Audit-3.

Wires Sales Invoice and Purchase Invoice on_submit events (via hooks.py)
to automatically create Stock Entries that keep inventory in sync with
invoicing.

  Audit-2: Sales Invoice submit  → Material Issue  (stock deducted)
           GL: DR COGS / CR Inventory (at valuation rate)
  Audit-3: Purchase Invoice submit → Material Receipt (stock added)
           GL: DR Inventory / CR Stock Received But Not Billed (GR/IR)
           The Purchase Invoice itself clears GR/IR (DR GRIR / CR AP) for
           stock items — see accounts.inventory_gl / post_purchase_invoice.

Return documents (Sales/Purchase Invoice with is_return=1) carry negative
qty and flip the physical direction: a Sales Invoice return restocks via a
Material Receipt (valued at current moving-average rate); a debit note
(Purchase Invoice is_return=1) de-stocks via a Material Issue (valued at the
original purchase rate). See _is_return_doc / _apply_current_valuation_rate.

If an item has no warehouse resolved, or is not a stock item, that row is
silently skipped so that non-inventory invoices continue to work.  If the
entire invoice has no stock items the hook returns without creating any entry.
"""

import frappe
from frappe import _
from frappe.utils import flt, today


# ─── Public hook entry points ─────────────────────────────────────────────────

def on_sales_invoice_submit(doc, method=None):
    """
    Deduct stock for a Sales Invoice ONLY when 'Update Inventory on Submit' is
    checked (direct/cash sale with no Delivery Note). Normally the Delivery Note
    owns the stock movement, so a plain invoice posts no stock — preventing
    double counting.

    Return invoices (is_return=1) carry negative qty and represent goods
    coming BACK IN — build a Material Receipt instead of an Issue, valued at
    the item's current moving-average rate (row.rate here is the original
    selling price, not cost — see _apply_current_valuation_rate).
    """
    if not flt(getattr(doc, "update_stock", 0)):
        return
    is_return = _is_return_doc(doc)
    rows = _stock_rows(doc, direction="issue", zero_rate=not is_return)
    if not rows:
        return

    if is_return:
        _apply_current_valuation_rate(rows)
        entry_type = "Material Receipt"
        verb, verb_done = "restock (return)", "restocked"
    else:
        entry_type = "Material Issue"
        verb, verb_done = "deduction", "deducted"

    se = _build_stock_entry(
        entry_type=entry_type,
        posting_date=doc.posting_date or today(),
        company=doc.company,
        remarks=_("Auto stock {0} — Sales Invoice {1}").format(verb, doc.name),
        rows=rows,
        ref_doctype=doc.doctype,
        ref_docname=doc.name,
    )
    frappe.msgprint(
        _("Stock {0} automatically via {1}.").format(verb_done, frappe.bold(se.name)),
        indicator="green",
        alert=True,
    )


def on_sales_invoice_cancel(doc, method=None):
    """Reverse the auto-issue Stock Entry when a Sales Invoice is cancelled."""
    _cancel_linked_entries(doc.doctype, doc.name)


def on_purchase_invoice_submit(doc, method=None):
    """
    Receive stock for a Purchase Invoice ONLY when 'Update Inventory on Submit'
    is checked (direct purchase with no Purchase Receipt). Normally the Purchase
    Receipt owns the stock movement, so a plain bill posts no stock.

    Debit notes (is_return=1) carry negative qty and represent goods going
    BACK OUT — build a Material Issue instead of a Receipt, valued at the
    original line rate (the same rate the goods were capitalized at on
    receipt), so it reverses the exact inventory value that was added.
    """
    if not flt(getattr(doc, "update_stock", 0)):
        return
    is_return = _is_return_doc(doc)
    rows = _stock_rows(doc, direction="receipt")
    if not rows:
        return

    entry_type = "Material Issue" if is_return else "Material Receipt"
    verb, verb_done = ("de-stock (return)", "reduced") if is_return else ("receipt", "received")

    se = _build_stock_entry(
        entry_type=entry_type,
        posting_date=doc.posting_date or today(),
        company=doc.company,
        remarks=_("Auto stock {0} — Purchase Invoice {1}").format(verb, doc.name),
        rows=rows,
        ref_doctype=doc.doctype,
        ref_docname=doc.name,
    )
    frappe.msgprint(
        _("Stock {0} automatically via {1}.").format(verb_done, frappe.bold(se.name)),
        indicator="green",
        alert=True,
    )


def on_purchase_invoice_cancel(doc, method=None):
    """Reverse the auto-receipt Stock Entry when a Purchase Invoice is cancelled."""
    _cancel_linked_entries(doc.doctype, doc.name)


def on_delivery_note_submit(doc, method=None):
    """
    Goods dispatched → deduct stock from the dispatch warehouse.
    Issue is valued at FIFO cost (zero_rate) so selling price never becomes COGS.

    Skipped when the linked Sales Order was already invoiced directly with
    Update Inventory on — that Sales Invoice already deducted this stock.
    """
    if doc.sales_order and frappe.db.exists(
        "Sales Invoice",
        {"sales_order": doc.sales_order, "docstatus": 1, "update_stock": 1},
    ):
        frappe.msgprint(
            _("Stock not deducted — already dispatched via a direct Invoice "
              "for this Sales Order."),
            indicator="blue", alert=True,
        )
        return
    rows = _stock_rows(doc, direction="issue", zero_rate=True)
    if not rows:
        return
    se = _build_stock_entry(
        entry_type="Material Issue",
        posting_date=doc.posting_date or today(),
        company=doc.company,
        remarks=_("Auto stock issue — Delivery Note {0}").format(doc.name),
        rows=rows,
        ref_doctype=doc.doctype,
        ref_docname=doc.name,
    )
    frappe.msgprint(
        _("Stock deducted automatically via {0}.").format(frappe.bold(se.name)),
        indicator="green", alert=True,
    )


def on_delivery_note_cancel(doc, method=None):
    """Reverse the auto-issue Stock Entry when a Delivery Note is cancelled."""
    _cancel_linked_entries(doc.doctype, doc.name)


def on_purchase_receipt_submit(doc, method=None):
    """Goods received → add stock into the receiving warehouse at the line cost."""
    rows = _stock_rows(doc, direction="receipt")
    if not rows:
        return
    se = _build_stock_entry(
        entry_type="Material Receipt",
        posting_date=doc.posting_date or today(),
        company=doc.company,
        remarks=_("Auto stock receipt — Purchase Receipt {0}").format(doc.name),
        rows=rows,
        ref_doctype=doc.doctype,
        ref_docname=doc.name,
    )
    frappe.msgprint(
        _("Stock received automatically via {0}.").format(frappe.bold(se.name)),
        indicator="green", alert=True,
    )


def on_purchase_receipt_cancel(doc, method=None):
    """Reverse the auto-receipt Stock Entry when a Purchase Receipt is cancelled."""
    _cancel_linked_entries(doc.doctype, doc.name)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _is_return_doc(doc) -> bool:
    """True for Sales/Purchase Invoice return documents (Credit/Debit Note style)."""
    return bool(flt(getattr(doc, "is_return", 0)))


def resolve_intended_warehouse(doc, row) -> str | None:
    """
    Phase 2 — public helper.

    Resolve the warehouse a row would land in under NORMAL (non-QC-routed)
    processing: row warehouse > doc.set_warehouse > item default_warehouse >
    Books Settings default. This is the exact same chain _stock_rows() below
    uses internally, exposed here so qc_engine.py's before_submit hooks
    (auto_create_qc_for_purchase_receipt / auto_create_qc_for_purchase_invoice)
    can stamp QC Inspection.target_warehouse with the row's ORIGINAL intended
    destination before this module's on_submit hook overrides the row to
    route into quarantine instead.

    Ordering this depends on: qc_engine's before_submit hook runs, and thus
    this function runs, before _stock_rows() ever executes for the same
    document (before_submit fires before on_submit) — so at the time this is
    called the row's warehouse fields are still exactly as the user entered
    them, unaffected by any quarantine routing decision.
    """
    item_code = getattr(row, "item_code", None) or getattr(row, "item", None)
    if not item_code:
        return None
    item_default_warehouse = frappe.db.get_value("Item", item_code, "default_warehouse")
    return (
        getattr(row, "warehouse", None)
        or getattr(doc, "set_warehouse", None)
        or item_default_warehouse
        or _default_warehouse(doc.company)
    )


def _apply_current_valuation_rate(rows: list[dict]) -> None:
    """
    Overwrite each row's basic_rate with the item's current moving-average
    valuation rate (from Bin).

    Used for return RECEIPTS (e.g. a Sales Invoice return coming back into
    stock) where row['basic_rate'] would otherwise be the original selling
    price captured in _stock_rows — wrong for valuing returned stock and for
    approximating the COGS reversal. This app doesn't lot-track the exact
    rate booked on the original sale, so this is the same "current average
    cost" approximation the Profit-wise report already documents and uses.
    """
    from zoho_books_clone.inventory.utils import get_valuation_rate
    for row in rows:
        row["basic_rate"] = flt(get_valuation_rate(row["item_code"], row["warehouse"]))


def _stock_rows(doc, direction: str, zero_rate: bool = False) -> list[dict]:
    """
    Return a list of dicts (one per item row) for items that:
      - have a non-zero qty
      - are marked as stock items in the Item master
      - have a resolved warehouse
        (row warehouse > doc set_warehouse > item default_warehouse > Books default)

    direction: "issue" = outgoing (Sales), "receipt" = incoming (Purchase)
    zero_rate: when True (Delivery Note issue), leave basic_rate at 0 so the
        Stock Entry controller values the issue at FIFO cost (not the selling
        price). Receipts pass the line rate (purchase cost).

    Return documents (doc.is_return=1) carry NEGATIVE qty by design — the
    physical stock movement uses the magnitude; the caller decides the
    actual direction (entry_type) by inspecting doc.is_return itself.
    """
    is_return = _is_return_doc(doc)
    default_warehouse = _default_warehouse(doc.company)
    rows = []

    for row in (doc.items or []):
        item_code = getattr(row, "item_code", None)
        qty       = flt(getattr(row, "qty", 0))
        # Purchase Receipt rows carry an accepted/rejected split — only the
        # accepted portion should actually land in stock. Other reference
        # doctypes (Delivery Note, Sales Invoice, ...) don't have this field,
        # so getattr falls through to the full qty exactly as before.
        # Valuation must use the item's NET (post-discount) cost, not the
        # gross line rate — row.rate is the pre-discount unit price, while
        # row.amount already has any line-level discount_amount subtracted
        # (see PurchaseInvoice.validate(): item.amount = base - discount_amount,
        # but item.rate itself is left untouched). Deriving the per-unit rate
        # from amount/qty instead of trusting row.rate keeps stock valued at
        # what was actually paid, per Ind AS 2 / AS 2 (trade discounts are
        # excluded from inventory cost). Purchase Receipt Item has no discount
        # fields, so amount == rate * qty there and this is a no-op for PR.
        # NOTE: amount is computed against the row's full (ordered/billed)
        # qty, not accepted_qty — so the denominator here must be that same
        # full qty, or a partial-acceptance row would have its rate inflated.
        full_purchase_uom_qty = qty
        row_amount = flt(getattr(row, "amount", 0))
        net_rate_per_purchase_uom = (
            round(row_amount / full_purchase_uom_qty, 6) if full_purchase_uom_qty else flt(getattr(row, "rate", 0))
        )

        accepted_qty = getattr(row, "accepted_qty", None)
        has_accepted_qty = accepted_qty is not None and accepted_qty != ""
        if has_accepted_qty:
            qty = flt(accepted_qty)

        # Phase 4: Purchase Invoice/Receipt Item rows may be entered in a
        # Purchase UOM distinct from the item's stock_uom — row.qty (or
        # accepted_qty) above is in THAT uom, while Bin/Batch/the Stock
        # Ledger always deal in stock_uom. Recompute the factor live here
        # via get_conversion_factor() rather than trusting row.conversion_factor:
        # that field is only as fresh as the last save, and the row we get
        # in this hook can be the doc as it existed when queued rather than
        # a fully re-validated instance — a stale/zero conversion_factor
        # would silently post raw purchase-uom qty as if it were stock_uom
        # (e.g. 10 Box landing as 10 Kg instead of 100 Kg). Recomputing
        # straight from the Item's UOM Conversions is cheap and always
        # correct. Sales-side rows (Delivery Note, Sales Invoice) have no
        # uom mismatch scenario here — get_conversion_factor returns 1.0
        # for them (uom == stock_uom), a no-op.
        from zoho_books_clone.inventory.utils import get_conversion_factor
        conversion_factor = flt(get_conversion_factor(item_code, getattr(row, "uom", None)) or 1)
        if conversion_factor != 1.0:
            qty = flt(qty) * conversion_factor

        if is_return:
            qty = abs(qty)
        if not item_code or qty <= 0:
            continue

        # Only process stock items
        item_meta = frappe.db.get_value(
            "Item", item_code, ["is_stock_item", "default_warehouse"], as_dict=True
        ) or {}
        if not item_meta.get("is_stock_item"):
            continue

        warehouse = (
            getattr(row, "warehouse", None)
            or getattr(doc, "set_warehouse", None)
            or item_meta.get("default_warehouse")
            or default_warehouse
        )
        # Phase 2 — QC quarantine routing.
        # Only applies to incoming rows (receipt, not a return/debit-note
        # going back out) for items flagged inspection_required_before_purchase.
        # Overrides ONLY this row's destination warehouse — every other
        # (unflagged) row on the same document still lands wherever it was
        # already headed above. qc_engine.py's before_submit hook (which
        # runs before this on_submit hook per hooks.py doc_events ordering)
        # has already created the QC Inspection and stamped its
        # target_warehouse with this same `warehouse` value computed above,
        # so Phase 3's release-on-pass has a record of where to send stock
        # once QC clears it.
        if direction == "receipt" and not is_return:
            warehouse = _maybe_route_to_quarantine(row, item_code, doc, warehouse)

        if not warehouse:
            frappe.msgprint(
                _(
                    "No warehouse found for item {0} — skipped from auto stock entry. "
                    "Set a default warehouse in Books Settings."
                ).format(frappe.bold(item_code)),
                indicator="orange",
                alert=True,
            )
            continue

        rows.append({
            "item_code":  item_code,
            "item_name":  getattr(row, "item_name", None) or item_code,
            "qty":        qty,
            # net_rate_per_purchase_uom was entered per conversion_factor's uom
            # (e.g. per Pack) — divide by the same factor so basic_rate lines
            # up with the stock-uom qty above (no-op when conversion_factor is 1).
            "basic_rate": 0 if zero_rate else net_rate_per_purchase_uom / conversion_factor,
            "warehouse":  warehouse,
            # Batch-tracked receipts (e.g. Purchase Receipt rows) carry their
            # own batch_no — forward it so the auto-generated Stock Entry
            # satisfies StockEntry.validate()'s "Batch No is required" check
            # instead of failing on submit. Non-batch-tracked / outgoing rows
            # simply carry None here and are unaffected.
            "batch_no":   getattr(row, "batch_no", None) or None,
        })

    return rows


def _maybe_route_to_quarantine(row, item_code: str, doc, intended_warehouse: str | None) -> str | None:
    """
    Phase 2 — QC quarantine routing for a single incoming row.

    If Item.inspection_required_before_purchase is set AND the receiving
    company has a Default Quarantine Warehouse (Raw Material) configured on
    Books Company, this row's stock lands there instead of intended_warehouse
    — untouched, unusable stock until an explicit release (Phase 3) moves it
    to target_warehouse on Pass. If either condition isn't met, the row is
    returned unchanged so existing behaviour (soft-warn only) is preserved
    exactly — e.g. for companies that haven't configured a quarantine
    warehouse yet, still a no-op precisely as it was before this phase.

    Also flips the linked QC Inspection's release_status to "Not Released"
    now that stock has actually been quarantined (as opposed to
    target_warehouse, which qc_engine.py already stamped at before_submit
    time regardless of whether routing ends up happening here).
    """
    if not frappe.db.get_value("Item", item_code, "inspection_required_before_purchase"):
        return intended_warehouse

    quarantine_wh = frappe.db.get_value(
        "Books Company", doc.company, "default_quarantine_warehouse"
    )
    if not quarantine_wh:
        return intended_warehouse

    qci_name = getattr(row, "quality_inspection", None)
    if qci_name:
        # Phase 3 (release-on-pass) and the Fail path both need to know,
        # without re-deriving it, exactly where this row's stock is sitting
        # right now — stamp it here, once, at the moment routing actually
        # happens (as opposed to target_warehouse, which qc_engine.py
        # stamps unconditionally at before_submit time regardless of
        # whether routing ends up occurring).
        update = {}
        if frappe.db.has_column("QC Inspection", "release_status"):
            update["release_status"] = "Not Released"
        if frappe.db.has_column("QC Inspection", "quarantine_warehouse"):
            update["quarantine_warehouse"] = quarantine_wh
        if update:
            frappe.db.set_value("QC Inspection", qci_name, update, update_modified=False)

    return quarantine_wh


def _build_stock_entry(
    entry_type: str,
    posting_date: str,
    company: str,
    remarks: str,
    rows: list[dict],
    ref_doctype: str,
    ref_docname: str,
) -> "frappe.Document":
    """Create, insert, and submit a Stock Entry; returns the submitted document."""
    warehouse_key = "t_warehouse" if entry_type == "Material Receipt" else "s_warehouse"

    items = [
        {
            "item_code":    r["item_code"],
            "item_name":    r["item_name"],
            "qty":          r["qty"],
            "basic_rate":   r["basic_rate"],
            warehouse_key:  r["warehouse"],
            **({"batch_no": r["batch_no"]} if r.get("batch_no") else {}),
        }
        for r in rows
    ]

    se = frappe.get_doc({
        "doctype":          "Stock Entry",
        "stock_entry_type": entry_type,
        "posting_date":     posting_date,
        "company":          company,
        "remarks":          remarks,
        # Store the originating voucher for traceability
        "reference_doctype": ref_doctype,
        "reference_name":    ref_docname,
        "items":            items,
    })
    se.flags.ignore_permissions = True
    se.insert()
    se.submit()
    return se


def _cancel_linked_entries(ref_doctype: str, ref_docname: str) -> None:
    """Cancel any submitted Stock Entries that were auto-created for a voucher."""
    linked = frappe.get_all(
        "Stock Entry",
        filters={
            "reference_doctype": ref_doctype,
            "reference_name":    ref_docname,
            "docstatus":         1,   # submitted only
        },
        fields=["name"],
    )
    for row in linked:
        se = frappe.get_doc("Stock Entry", row.name)
        se.flags.ignore_permissions = True
        se.cancel()


def _default_warehouse(company: str | None) -> str | None:
    """Return the default warehouse configured in Books Settings, if any."""
    try:
        return frappe.db.get_single_value("Books Settings", "default_warehouse") or None
    except Exception:
        return None