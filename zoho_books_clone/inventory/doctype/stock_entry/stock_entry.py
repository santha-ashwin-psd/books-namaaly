from __future__ import annotations
"""
Stock Entry — records every physical stock movement.
On submit: creates Stock Ledger Entries → Bin is updated automatically.
On cancel: reverses all SLEs (sets is_cancelled=1 and creates mirror entries).

Audit fixes applied:
  - Negative stock blocked in _validate_items (P2/Audit-1)
  - GL entries posted on submit for Material Issue/Receipt (P2/Audit-4)
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today
from zoho_books_clone.db.validators import validate_fiscal_year


SE_TYPE_DIRECTION = {
    "Material Receipt":  {"s": False, "t": True},
    "Material Issue":    {"s": True,  "t": False},
    "Material Transfer": {"s": True,  "t": True},
    "Opening Stock":     {"s": False, "t": True},
    "Manufacture":       {"s": True,  "t": True},
    "Stock Adjustment":  {"s": False, "t": True},  # manual correction; qty can be +/-
}


def _allow_negative_stock():
    """Manufacturing Settings > Allow Negative Stock. Defaults to blocking
    (False) if the setting hasn't been migrated/configured yet."""
    try:
        return bool(frappe.db.get_single_value("Manufacturing Settings", "allow_negative_stock"))
    except Exception:
        return False


def _segregate_scrap_gl():
    """Manufacturing Settings > Segregate Scrap/By-Product GL (opt-in Phase 5
    feature). Defaults to off (False) if unset or the setting hasn't been
    migrated yet, so existing companies keep posting scrap through the same
    inventory_account as FG until they explicitly opt in."""
    try:
        return bool(frappe.db.get_single_value("Manufacturing Settings", "segregate_scrap_gl"))
    except Exception:
        return False


class StockEntry(Document):

    # ── Validate ──────────────────────────────────────────────────────────────

    def validate(self):
        self._set_defaults()
        self._validate_fiscal_year()
        self._validate_items()
        self._calculate_totals()

    def _set_defaults(self):
        if not self.posting_date:
            self.posting_date = today()
        if not self.company:
            self.company = (
                frappe.db.get_single_value("Books Settings", "default_company")
                or frappe.db.get_default("company")
                or ""
            )

    def _validate_fiscal_year(self):
        """Block saves into closed or missing fiscal years.

        Stock Entry is not wired to central_validator, and its GL entries post
        on submit with posting_date — so the year check must happen here, after
        _set_defaults() has guaranteed both fields are non-empty.
        Opening Stock is exempt: it establishes historical balances and must be
        allowed to post to any date, matching the exemption in central_validator.
        """
        if self.stock_entry_type == "Opening Stock":
            return
        if self.posting_date and self.company:
            validate_fiscal_year(self.posting_date, self.company)

    def _auto_assign_outgoing_batches(self, direction):
        """
        For outgoing rows (Material Issue / Material Transfer — entry types
        with a source warehouse) on batch-tracked items where the caller
        didn't specify a Batch No, pick batches automatically using the
        item's valuation method (FIFO/LIFO/Moving Average — see
        get_batches_for_outgoing).

        This is what lets auto-generated Stock Entries (Delivery Note, Sales
        Invoice, Purchase Invoice — see inventory/stock_link.py, which never
        sets batch_no) actually succeed for batch-tracked items instead of
        failing the "Batch No is required" check below. Manual entry rows
        that already carry a batch_no are left untouched.

        Note: Stock Adjustment (qty can be negative, no s_warehouse) isn't
        covered here — a negative-qty Stock Adjustment reduces stock via a
        t_warehouse SLE, not the s_warehouse path this method walks. If
        batch-tracked items need adjustment-down support with auto batch
        selection, that needs its own code path keyed off t_warehouse.

        A single row can expand into several rows if one batch can't cover
        the full requested qty — the resulting rows are spread across as
        many batches as needed, oldest-first for FIFO/Moving Average or
        newest-first for LIFO.
        """
        if not direction.get("s"):
            return  # entry type has no source-warehouse leg (e.g. Stock Adjustment)

        from zoho_books_clone.inventory.utils import get_batches_for_outgoing, get_conversion_factor

        new_items = []
        changed = False

        for row in self.items:
            needs_auto = (
                row.s_warehouse
                and row.item_code
                and not row.batch_no
                and flt(row.qty) > 0
                and frappe.db.get_value("Item", row.item_code, "has_batch_no")
            )
            if not needs_auto:
                new_items.append(row)
                continue

            # Batch balances (Batch.batch_qty) and Bin.actual_qty are always
            # stock_uom-denominated -- convert this row's entry-uom qty to
            # stock_uom before asking which batches can cover it, or a row
            # entered in a Purchase/Sales UOM (e.g. "2 Pack") would only ever
            # be checked against "2" units of batch stock instead of the
            # 30 Kg it actually represents.
            conversion_factor = get_conversion_factor(row.item_code, row.uom)
            stock_qty = flt(row.qty) * conversion_factor

            valuation_method = frappe.db.get_value("Item", row.item_code, "valuation_method")
            allocations = get_batches_for_outgoing(
                row.item_code, row.s_warehouse, stock_qty, valuation_method
            )
            changed = True

            for alloc in allocations:
                # Build a plain dict copy of the row's fields — Stock Entry
                # Detail rows are re-inserted as part of the parent's items
                # table on save via self.set(), so a dict is sufficient (no
                # need for frappe.copy_doc, which targets whole documents).
                row_dict = row.as_dict()
                row_dict.pop("name", None)   # let Frappe assign fresh child names
                row_dict["idx"] = None
                row_dict["batch_no"] = alloc["batch_no"]
                # alloc["qty"] comes back in stock_uom (that's what we asked
                # get_batches_for_outgoing to cover) -- convert back to this
                # row's own entry uom so qty/basic_rate/amount stay in the
                # terms they were entered in. qty_in_stock_uom is re-derived
                # from this further down (_validate_items), landing back on
                # alloc["qty"].
                row_dict["qty"] = (
                    round(flt(alloc["qty"]) / conversion_factor, 4)
                    if conversion_factor else flt(alloc["qty"])
                )
                new_items.append(row_dict)

        if changed:
            self.set("items", new_items)

    def _validate_items(self):
        if not self.items:
            frappe.throw(_("At least one item is required in the Stock Entry."))

        from zoho_books_clone.inventory.utils import get_conversion_factor

        direction = SE_TYPE_DIRECTION.get(self.stock_entry_type, {})
        self._auto_assign_outgoing_batches(direction)

        for i, row in enumerate(self.items, start=1):
            if not row.item_code:
                frappe.throw(_(f"Row {i}: Item Code is required."))

            # Auto-fill item name if blank
            if not row.item_name:
                row.item_name = frappe.db.get_value("Item", row.item_code, "item_name") or row.item_code

            # Auto-fill warehouses from header defaults
            if direction.get("s") and not row.s_warehouse:
                row.s_warehouse = self.from_warehouse
            if direction.get("t") and not row.t_warehouse:
                row.t_warehouse = self.to_warehouse

            # Phase 4: resolve this row's stock_uom-equivalent qty up front.
            # Computed directly here (not just read off row.qty_in_stock_uom)
            # so it's correct even for rows that were just built as raw dicts
            # in _auto_assign_outgoing_batches above and haven't been through
            # StockEntryDetail's own validate() yet -- every stock-balance
            # check and the SLE itself must key off this, not row.qty, since
            # Bin/Batch/SLE quantities are always stock_uom-denominated while
            # row.qty is whatever UOM this row was entered in.
            row.conversion_factor = get_conversion_factor(row.item_code, row.uom)
            row.qty_in_stock_uom = round(flt(row.qty) * flt(row.conversion_factor), 4)
            stock_qty = flt(row.qty_in_stock_uom)

            # Validate warehouse requirements.
            # Manufacture is the one type where a single Stock Entry mixes two
            # kinds of row: raw-material consumption (source only) and
            # finished-goods/scrap receipt (target only) — the BOM/Work Order
            # pattern. So for Manufacture we only require that a row set at
            # least one side, not both; _make_sle() already creates the SLE
            # for whichever side is actually populated on each row. Material
            # Transfer (the other s+t type) genuinely moves the same item
            # from one warehouse to another on every row, so it keeps the
            # strict both-required check.
            if self.stock_entry_type == "Manufacture":
                if not row.s_warehouse and not row.t_warehouse:
                    frappe.throw(_(f"Row {i}: set a Source Warehouse (raw material consumed) or a Target Warehouse (finished good/scrap received)."))
            else:
                if direction.get("s") and not row.s_warehouse:
                    frappe.throw(_(f"Row {i}: Source Warehouse is required for {self.stock_entry_type}."))
                if direction.get("t") and not row.t_warehouse:
                    frappe.throw(_(f"Row {i}: Target Warehouse is required for {self.stock_entry_type}."))

            # Validate qty: Stock Adjustment allows negative (stock reduction correction)
            if self.stock_entry_type == "Stock Adjustment":
                if flt(row.qty) == 0:
                    frappe.throw(_(f"Row {i}: Qty cannot be zero for Stock Adjustment."))
            else:
                if flt(row.qty) <= 0:
                    frappe.throw(_(f"Row {i}: Qty must be greater than 0."))

            # Audit-1: Block negative stock — check available qty before outgoing
            # movements, unless Manufacturing Settings > Allow Negative Stock is on.
            if direction.get("s") and row.s_warehouse and not _allow_negative_stock():
                available = flt(frappe.db.get_value(
                    "Bin",
                    {"item_code": row.item_code, "warehouse": row.s_warehouse},
                    "actual_qty",
                ) or 0)
                if available < stock_qty:
                    frappe.throw(_(
                        "Row {0}: Insufficient stock for item <b>{1}</b> in warehouse <b>{2}</b>. "
                        "Available: {3}, Required: {4}."
                    ).format(i, row.item_code, row.s_warehouse,
                             frappe.bold(available), frappe.bold(stock_qty)))

            # Batch validation: items flagged Has Batch No must carry a Batch No
            # on every line, and the batch itself must actually exist (it should
            # already have been created client-side, but enforce it server-side
            # too since Stock Entry can be created via API/import directly).
            has_batch_no = frappe.db.get_value("Item", row.item_code, "has_batch_no")
            if has_batch_no:
                if not row.batch_no:
                    frappe.throw(_(
                        "Row {0}: Item <b>{1}</b> is batch-tracked — Batch No is required."
                    ).format(i, row.item_code))
                if not frappe.db.exists("Batch", row.batch_no):
                    frappe.throw(_(
                        "Row {0}: Batch <b>{1}</b> does not exist."
                    ).format(i, row.batch_no))
                if frappe.db.get_value("Batch", row.batch_no, "disabled"):
                    frappe.throw(_(
                        "Row {0}: Batch <b>{1}</b> is disabled and cannot be used."
                    ).format(i, row.batch_no))
                batch_item = frappe.db.get_value("Batch", row.batch_no, "item")
                if batch_item and batch_item != row.item_code:
                    frappe.throw(_(
                        "Row {0}: Batch <b>{1}</b> belongs to item <b>{2}</b>, not <b>{3}</b>."
                    ).format(i, row.batch_no, batch_item, row.item_code))

                # Outgoing batch-tracked movements must not exceed that batch's
                # own remaining qty (separate from the item's overall Bin qty,
                # since a warehouse can hold several batches of the same item).
                if direction.get("s") and row.s_warehouse:
                    batch_qty = flt(frappe.db.get_value("Batch", row.batch_no, "batch_qty") or 0)
                    if batch_qty < stock_qty:
                        frappe.throw(_(
                            "Row {0}: Insufficient stock in batch <b>{1}</b>. "
                            "Available: {2}, Required: {3}."
                        ).format(i, row.batch_no, frappe.bold(batch_qty), frappe.bold(stock_qty)))
            elif row.batch_no:
                # Item isn't batch-tracked but a batch_no slipped through (e.g. stale
                # client state) — clear it rather than silently posting bad data.
                row.batch_no = None

            # Default outgoing rows to the warehouse's current moving-average
            # cost when no rate was explicitly entered. This must match what
            # StockLedgerEntry._update_bin() will actually draw down on
            # submit — using a separately-computed FIFO rate here would let
            # the row's recorded amount (and any COGS GL entry built from
            # total_outgoing_value) drift away from what the Bin really lost.
            if direction.get("s") and not flt(row.basic_rate) and row.s_warehouse:
                try:
                    from zoho_books_clone.inventory.utils import get_valuation_rate
                    avg_rate = get_valuation_rate(row.item_code, row.s_warehouse)
                    if avg_rate:
                        # get_valuation_rate() is always per stock_uom (it
                        # reads straight off the Bin) -- scale it up to this
                        # row's own entry uom (e.g. per Pack) by its
                        # conversion_factor so row.amount (= qty * basic_rate,
                        # both in entry-uom terms) still comes out right.
                        row.basic_rate = avg_rate * (flt(row.conversion_factor) or 1)
                except Exception:
                    pass  # fall back to 0

            # Calculate row amount
            row.amount = flt(row.qty) * flt(row.basic_rate)

    def _calculate_totals(self):
        # Split by what's actually populated on EACH row, not by the entry
        # type's direction flags. Manufacture (and any other s+t type) mixes
        # rows that only have one side set on a single Stock Entry -- e.g. a
        # raw-material consumption row (s_warehouse only) and a finished-good
        # receipt row (t_warehouse only). Using the type-level flags counted
        # every row into BOTH outgoing and incoming, which made
        # total_outgoing_value == total_incoming_value (and value_difference
        # == 0) for every single Manufacture entry by construction, hiding
        # any real value created or lost in production. Material Transfer
        # rows genuinely carry both warehouses on the same row and are
        # unaffected by this change -- they still count in both sums.
        outgoing = sum(flt(r.amount) for r in self.items if r.s_warehouse)
        incoming = sum(flt(r.amount) for r in self.items if r.t_warehouse)
        self.total_outgoing_value = outgoing
        self.total_incoming_value = incoming
        self.value_difference = incoming - outgoing

    # ── Submit ────────────────────────────────────────────────────────────────

    def on_submit(self):
        self._make_sle()
        self._post_gl_entries()   # Audit-4: link inventory to accounting

    def _make_sle(self):
        direction = SE_TYPE_DIRECTION.get(self.stock_entry_type, {})

        for row in self.items:
            # Phase 4: the Stock Ledger/Bin/Batch always deal in stock_uom,
            # never the row's entry uom -- post qty_in_stock_uom (set on
            # every row by _validate_items, which has already run by the
            # time on_submit -> _make_sle executes), not row.qty.
            #
            # row.amount (= row.qty * row.basic_rate, both in entry-uom
            # terms, from _validate_items) is already the correct total
            # monetary value for this row regardless of UOM -- dividing it
            # by the stock-uom qty gives the equivalent per-stock-uom rate,
            # so SLE valuation and row.amount/the GL entries built from
            # total_incoming_value/total_outgoing_value always agree, even
            # when conversion_factor != 1. Falls back to basic_rate (already
            # per stock_uom when conversion_factor is 1, the common case)
            # if stock_qty is somehow zero.
            stock_qty = flt(row.qty_in_stock_uom) or flt(row.qty)
            rate = (flt(row.amount) / stock_qty) if stock_qty else flt(row.basic_rate)

            # Outgoing SLE (from source warehouse)
            if direction.get("s") and row.s_warehouse:
                self._create_sle(
                    item_code=row.item_code,
                    warehouse=row.s_warehouse,
                    actual_qty=-stock_qty,
                    incoming_rate=0,
                    valuation_rate=rate,
                    stock_value_difference=-flt(row.amount),
                    batch_no=row.batch_no,
                )

            # Incoming SLE (into target warehouse)
            if direction.get("t") and row.t_warehouse:
                self._create_sle(
                    item_code=row.item_code,
                    warehouse=row.t_warehouse,
                    actual_qty=stock_qty,
                    incoming_rate=rate,
                    valuation_rate=rate,
                    stock_value_difference=flt(row.amount),
                    batch_no=row.batch_no,
                )

        frappe.db.commit()

    def _create_sle(self, item_code, warehouse, actual_qty,
                    incoming_rate, valuation_rate, stock_value_difference, batch_no=None):
        # Compute qty_after_transaction from current Bin
        current_qty = flt(
            frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty")
        )
        qty_after = current_qty + actual_qty

        sle = frappe.get_doc({
            "doctype": "Stock Ledger Entry",
            "item_code": item_code,
            "warehouse": warehouse,
            "batch_no": batch_no or None,
            "posting_date": self.posting_date,
            "posting_time": self.posting_time or "00:00:00",
            "voucher_type": "Stock Entry",
            "voucher_no": self.name,
            "company": self.company,
            "actual_qty": actual_qty,
            "qty_after_transaction": qty_after,
            "incoming_rate": incoming_rate,
            "valuation_rate": valuation_rate,
            "stock_value": flt(qty_after) * flt(valuation_rate),
            "stock_value_difference": stock_value_difference,
            "is_cancelled": 0,
        })
        # Pre-set name so Frappe skips the naming_series autoname lookup entirely
        sle.name = frappe.generate_hash(txt=f"{item_code}{warehouse}{frappe.utils.now()}", length=10)
        sle.flags.ignore_links = True
        sle.flags.ignore_mandatory = True
        sle.insert(ignore_permissions=True)
        # NOTE: do NOT call _sync_bin here — SLE.after_insert._update_bin() is the
        # single authoritative writer for actual_qty.  Calling _sync_bin as well
        # would decrement/increment actual_qty a second time on every SLE insert.

        # Keep the Batch record's own qty in sync with the movement, independent
        # of the item-level Bin aggregate (a warehouse can hold several batches
        # of the same item, so Bin qty alone can't tell batches apart).
        if batch_no:
            self._adjust_batch_qty(batch_no, actual_qty)
            if actual_qty > 0:
                # This leg received the batch into `warehouse` — that's where it
                # physically sits now. Batch.warehouse is a single-location field
                # (the model assumes one batch lives in one warehouse at a time,
                # same assumption get_batches_for_outgoing() and
                # assert_batch_deletable() already make), so keep it pointed at
                # wherever the batch was most recently received. Without this,
                # a batch created via Opening Stock in Warehouse A and later
                # moved by a Material Transfer to Warehouse B would still show
                # warehouse=A forever — get_batches_for_outgoing() filters by
                # warehouse, so it would silently stop finding that batch for
                # any future outgoing movement out of B.
                # Outgoing legs (actual_qty < 0) don't touch this: the batch is
                # leaving that warehouse, not settling there.
                frappe.db.set_value("Batch", batch_no, "warehouse", warehouse)

    def _adjust_batch_qty(self, batch_no, delta_qty):
        if not batch_no or not frappe.db.exists("Batch", batch_no):
            return
        current = flt(frappe.db.get_value("Batch", batch_no, "batch_qty") or 0)
        frappe.db.set_value("Batch", batch_no, "batch_qty", current + flt(delta_qty))

    def _sync_bin(self, item_code, warehouse, new_qty, valuation_rate, _=None):
        """Create or update the Bin record for item+warehouse after an SLE."""
        bin_name = frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse})
        new_value = flt(new_qty) * flt(valuation_rate)
        if bin_name:
            old_reserved = flt(frappe.db.get_value("Bin", bin_name, "reserved_qty"))
            old_ordered  = flt(frappe.db.get_value("Bin", bin_name, "ordered_qty"))
            frappe.db.set_value("Bin", bin_name, {
                "actual_qty":     new_qty,
                "stock_value":    new_value,
                "valuation_rate": valuation_rate if new_qty else 0,
                "projected_qty":  new_qty + old_ordered - old_reserved,
            }, update_modified=True)
        else:
            b = frappe.get_doc({
                "doctype":        "Bin",
                "item_code":      item_code,
                "warehouse":      warehouse,
                "actual_qty":     new_qty,
                "reserved_qty":   0,
                "ordered_qty":    0,
                "projected_qty":  new_qty,
                "valuation_rate": valuation_rate if new_qty else 0,
                "stock_value":    new_value,
            })
            b.flags.ignore_links = True
            b.flags.ignore_mandatory = True
            b.insert(ignore_permissions=True)

        # Trigger reorder check after every bin update
        try:
            from zoho_books_clone.inventory.utils import check_reorder
            check_reorder(item_code, warehouse)
        except Exception:
            pass

    def _post_gl_entries(self):
        """
        Audit-4: Post GL entries so inventory movements reflect in accounting.
        Material Issue:    DR COGS / CR Inventory Asset   (stock leaves)
        Material Receipt:  DR Inventory Asset / CR GRIR (purchase-linked)
                           or CR Stock Adjustment (manual / opening)
        Material Transfer: no net GL impact (value stays in inventory).
        Manufacture:       DR Work In Progress / CR Inventory Asset  (raw materials consumed)
                            DR Inventory Asset / CR Work In Progress  (FG + scrap received)
                            When Manufacturing Settings > Segregate Scrap/By-Product GL is
                            on, the FG+scrap debit above splits into two lines by row
                            (is_scrap_item): scrap debits get_scrap_account() (falling back
                            to Inventory Asset if unconfigured) while FG keeps debiting
                            Inventory Asset -- the WIP credit stays one combined line.
                            The two WIP legs net to the process-loss variance whenever
                            incoming value differs from outgoing value, which is the normal
                            case since FG/scrap value reflects the BOM cost roll-up rather
                            than a 1:1 mirror of raw material cost.
                            DR Loss/Variance / CR Work In Progress  (only when scrap value
                            exceeds the absorbable cost pool -- see manufacturing_variance_loss)
        """
        if self.stock_entry_type not in (
            "Material Issue", "Material Receipt", "Stock Adjustment", "Manufacture"
        ):
            return

        from zoho_books_clone.accounts.inventory_gl import (
            get_cogs_account,
            get_grir_account,
            get_inventory_account,
            get_scrap_account,
            get_stock_adjustment_account,
            is_purchase_stock_receipt,
        )

        inventory_account = get_inventory_account(self.company) or self._get_account_by_type("Stock")
        if not inventory_account:
            frappe.log_error(
                f"Stock Entry {self.name}: no Stock-type account found for company "
                f"'{self.company}'. GL entries skipped.",
                "Inventory GL Posting"
            )
            return

        if self.stock_entry_type == "Material Issue":
            # Stock leaving — debit COGS, credit Inventory
            cogs_account = get_cogs_account(self.company)
            if not cogs_account:
                frappe.log_error(
                    f"Stock Entry {self.name}: no COGS or Expense account found for company "
                    f"'{self.company}'. GL entries skipped. "
                    "Create an account with type 'Cost of Goods Sold' or 'Expense'.",
                    "Inventory GL Posting"
                )
                return
            gl_map = [
                {
                    "account":      cogs_account,
                    "debit":        flt(self.total_outgoing_value),
                    "credit":       0,
                    "voucher_type": "Stock Entry",
                    "voucher_no":   self.name,
                    "posting_date": self.posting_date,
                    "company":      self.company,
                    "remarks":      f"COGS — Stock Issue {self.name}",
                },
                {
                    "account":      inventory_account,
                    "debit":        0,
                    "credit":       flt(self.total_outgoing_value),
                    "voucher_type": "Stock Entry",
                    "voucher_no":   self.name,
                    "posting_date": self.posting_date,
                    "company":      self.company,
                    "remarks":      f"Inventory reduction — Stock Issue {self.name}",
                },
            ]
        elif self.stock_entry_type == "Manufacture":
            # Raw materials leave inventory into WIP; finished goods/scrap come
            # back out of WIP into inventory. Two independent DR/CR pairs (not
            # a single netted pair) so both legs show up on the WIP ledger even
            # when outgoing and incoming value differ (process loss/gain).
            wip_account = (
                self._get_account_by_type("Work In Progress")
                or self._get_account_by_type("Stock")
                or inventory_account   # fallback if no dedicated WIP account exists yet for this company
            )
            gl_map = []
            if flt(self.total_outgoing_value):
                gl_map += [
                    {
                        "account":      wip_account,
                        "debit":        flt(self.total_outgoing_value),
                        "credit":       0,
                        "voucher_type": "Stock Entry",
                        "voucher_no":   self.name,
                        "posting_date": self.posting_date,
                        "company":      self.company,
                        "remarks":      f"WIP — raw materials consumed {self.name}",
                    },
                    {
                        "account":      inventory_account,
                        "debit":        0,
                        "credit":       flt(self.total_outgoing_value),
                        "voucher_type": "Stock Entry",
                        "voucher_no":   self.name,
                        "posting_date": self.posting_date,
                        "company":      self.company,
                        "remarks":      f"Inventory reduction — raw materials issued to WIP {self.name}",
                    },
                ]
            if flt(self.total_incoming_value):
                # Split the combined FG+scrap debit by row (is_scrap_item)
                # when Manufacturing Settings > Segregate Scrap/By-Product GL
                # is on, so recoverable scrap posts to its own ledger account
                # for audit/reporting instead of blending into FG inventory.
                # The WIP credit leg stays a single total_incoming_value line
                # either way -- the manufacturing variance write-off logic
                # below nets against that one WIP leg and is untouched by
                # this split.
                from zoho_books_clone.accounts.inventory_gl import (
                    build_manufacture_incoming_gl_lines,
                )

                incoming_rows = [r for r in self.items if r.t_warehouse]
                scrap_incoming_value = sum(
                    flt(r.amount) for r in incoming_rows if flt(getattr(r, "is_scrap_item", 0))
                )

                gl_map += build_manufacture_incoming_gl_lines(
                    voucher_no=self.name,
                    posting_date=self.posting_date,
                    company=self.company,
                    total_incoming_value=flt(self.total_incoming_value),
                    scrap_incoming_value=flt(scrap_incoming_value),
                    inventory_account=inventory_account,
                    scrap_account=get_scrap_account(self.company),
                    segregate_scrap_gl=_segregate_scrap_gl(),
                )

                gl_map.append({
                    "account":      wip_account,
                    "debit":        0,
                    "credit":       flt(self.total_incoming_value),
                    "voucher_type": "Stock Entry",
                    "voucher_no":   self.name,
                    "posting_date": self.posting_date,
                    "company":      self.company,
                    "remarks":      f"WIP — finished goods/scrap received {self.name}",
                })
            if flt(self.operating_cost_absorbed):
                # Fund WIP with the labor/overhead absorbed into this run's FG
                # valuation (see work_order_engine.py::complete_work_order and
                # packing_engine.py::post_packing_consumption -- both set
                # operating_cost_absorbed the same way), crediting a
                # contra-expense account -- the labor cost is being
                # capitalized into inventory instead of expensed outright.
                #
                # The WIP debit below is NOT optional: the total_incoming_value
                # block above already credited wip_account for the FG's full
                # valuation, which was built from fg_unit_rate INCLUDING this
                # operating cost (see complete_work_order's fg_unit_rate calc).
                # If this debit were skipped, wip_account would be credited for
                # more than it was ever debited -- the GL entry would be left
                # unbalanced by exactly operating_cost_absorbed. So instead of
                # skipping the entries entirely when no Expense account exists,
                # fall back through progressively less-ideal contra accounts,
                # and only as an absolute last resort self-balance against
                # wip_account's own inventory fallback so the entry still nets
                # to zero and posts cleanly.
                operating_cost_account = (
                    self._get_account_by_type("Expense")
                    or self._get_account_by_type("Cost of Goods Sold")
                    or self._get_account_by_type("Stock Adjustment")
                    or inventory_account
                )
                if operating_cost_account == inventory_account:
                    frappe.log_error(
                        f"Stock Entry {self.name}: Work Order {self.work_order} absorbed "
                        f"operating cost {self.operating_cost_absorbed} into FG valuation but no "
                        f"Expense, Cost of Goods Sold, or Stock Adjustment account exists for "
                        f"company '{self.company}'. Falling back to crediting the Stock account "
                        "so GL still balances -- create a proper Expense-type account for this "
                        "company and re-post a correcting Journal Entry to reclassify it.",
                        "Inventory GL Posting"
                    )
                gl_map += [
                    {
                        "account":      wip_account,
                        "debit":        flt(self.operating_cost_absorbed),
                        "credit":       0,
                        "voucher_type": "Stock Entry",
                        "voucher_no":   self.name,
                        "posting_date": self.posting_date,
                        "company":      self.company,
                        "remarks":      f"WIP — operating cost absorbed {self.name}",
                    },
                    {
                        "account":      operating_cost_account,
                        "debit":        0,
                        "credit":       flt(self.operating_cost_absorbed),
                        "voucher_type": "Stock Entry",
                        "voucher_no":   self.name,
                        "posting_date": self.posting_date,
                        "company":      self.company,
                        "remarks":      f"Operating cost (labor/overhead) capitalized into WIP {self.name}",
                    },
                ]
            if flt(self.manufacturing_variance_loss):
                # Recoverable scrap value exceeded what this run's raw
                # material + operating cost could absorb, so the FG receipt
                # above was valued at (or clamped to) less than the true
                # cost pool. Without this leg that shortfall would sit as a
                # stranded, never-cleared debit balance in wip_account
                # forever. Write it off here to a loss/variance account so
                # WIP nets back to zero for this entry, same self-balancing
                # fallback chain as the operating cost leg above.
                variance_account = (
                    self._get_account_by_type("Cost of Goods Sold")
                    or self._get_account_by_type("Expense")
                    or self._get_account_by_type("Stock Adjustment")
                    or inventory_account
                )
                if variance_account == inventory_account:
                    frappe.log_error(
                        f"Stock Entry {self.name}: Work Order {self.work_order} could not "
                        f"absorb {self.manufacturing_variance_loss} of scrap/consumption "
                        f"variance into FG valuation (scrap value exceeded the available "
                        f"cost pool), and no Cost of Goods Sold, Expense, or Stock "
                        f"Adjustment account exists for company '{self.company}'. Falling "
                        "back to crediting the Stock account so GL still balances -- create "
                        "a proper loss/variance account for this company and re-post a "
                        "correcting Journal Entry to reclassify it.",
                        "Inventory GL Posting"
                    )
                gl_map += [
                    {
                        "account":      variance_account,
                        "debit":        flt(self.manufacturing_variance_loss),
                        "credit":       0,
                        "voucher_type": "Stock Entry",
                        "voucher_no":   self.name,
                        "posting_date": self.posting_date,
                        "company":      self.company,
                        "remarks":      f"Manufacturing variance — unabsorbed cost written off {self.name}",
                    },
                    {
                        "account":      wip_account,
                        "debit":        0,
                        "credit":       flt(self.manufacturing_variance_loss),
                        "voucher_type": "Stock Entry",
                        "voucher_no":   self.name,
                        "posting_date": self.posting_date,
                        "company":      self.company,
                        "remarks":      f"WIP — variance written off {self.name}",
                    },
                ]
            if not gl_map:
                return
        else:
            # Material Receipt / Stock Adjustment — debit Inventory, credit the
            # contra.
            #
            # Purchase-linked receipts (PR / PI update_stock) credit GR/IR so the
            # later Purchase Invoice can clear that liability instead of
            # expensing the goods. Manual / opening receipts still use Stock
            # Adjustment (or a user-chosen adjustment_account).
            use_grir = (
                self.stock_entry_type == "Material Receipt"
                and is_purchase_stock_receipt(getattr(self, "reference_doctype", None))
            )
            if use_grir:
                adj_account = get_grir_account(self.company)
                if not adj_account:
                    frappe.log_error(
                        f"Stock Entry {self.name}: purchase receipt has no GR/IR account "
                        f"for company '{self.company}'. Falling back to Stock Adjustment.",
                        "Inventory GL Posting",
                    )
                    adj_account = (
                        getattr(self, "adjustment_account", None)
                        or get_stock_adjustment_account(self.company)
                        or inventory_account
                    )
                contra_remarks = f"Stock received not billed (GR/IR) — {self.name}"
            else:
                adj_account = (
                    getattr(self, "adjustment_account", None)
                    or get_stock_adjustment_account(self.company)
                    or inventory_account
                )
                contra_remarks = f"Stock received — {self.name}"

            gl_map = [
                {
                    "account":      inventory_account,
                    "debit":        flt(self.total_incoming_value),
                    "credit":       0,
                    "voucher_type": "Stock Entry",
                    "voucher_no":   self.name,
                    "posting_date": self.posting_date,
                    "company":      self.company,
                    "remarks":      f"Inventory addition — Stock Receipt {self.name}",
                },
                {
                    "account":      adj_account,
                    "debit":        0,
                    "credit":       flt(self.total_incoming_value),
                    "voucher_type": "Stock Entry",
                    "voucher_no":   self.name,
                    "posting_date": self.posting_date,
                    "company":      self.company,
                    "remarks":      contra_remarks,
                },
            ]

        try:
            from zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry import (
                make_gl_entries,
            )
            make_gl_entries(gl_map)
        except Exception as exc:
            # GL failure must not roll back the stock movement itself.
            # Log and alert; the accountant can reconcile manually.
            frappe.log_error(
                f"Stock Entry {self.name}: GL posting failed — {exc}",
                "Inventory GL Posting"
            )
            frappe.msgprint(
                _(
                    "Stock updated, but GL entries could not be posted automatically. "
                    "Please post a Journal Entry manually for {0}."
                ).format(self.name),
                indicator="orange",
                alert=True,
            )

    def _get_account_by_type(self, account_type: str) -> str | None:
        """Return the name of the first leaf account of the given type for this company."""
        row = frappe.db.get_value(
            "Account",
            {"account_type": account_type, "company": self.company, "is_group": 0},
            "name",
        )
        return row or None

    # ── Cancel ────────────────────────────────────────────────────────────────

    def _guard_manufacturing_links(self):
        """Block direct cancellation of a Stock Entry that a Work Order or
        Packing Slip depends on.

        Reversing this Stock Entry's SLEs alone would correctly undo the
        stock movement, but nothing here rolls back the Work Order's
        produced_qty/consumed_qty/transferred_qty/status, or a Packing
        Slip's stock_entry/status — those fields would be left claiming
        production/consumption that no longer exists in the stock ledger.
        Rather than reconcile all of that from a generic Stock Entry cancel,
        route the person to the manufacturing doc's own reversal flow.
        """
        if self.flags.get("ignore_manufacturing_guard"):
            # Set by work_order_engine.reverse_manufacture_entry /
            # reverse_material_issue / packing_engine.reverse_packing_consumption
            # once they've already rolled back the Work Order / Packing Slip
            # fields that depend on this Stock Entry. Cancelling directly
            # (bypassing this guard) is only safe when called from there.
            return

        if self.stock_entry_type not in ("Manufacture", "Material Transfer"):
            return

        # Checked before the Work Order check below: post_packing_consumption()
        # sets work_order on the Stock Entry it creates too (so it can be found/
        # filtered per Work Order), which meant a packing-consumption entry
        # always matched the generic "cancel it via the Work Order" branch
        # first and never reached this one -- routing the person to reverse
        # production from the Work Order (wrong, and not even a supported
        # path for a packing entry) instead of the correct
        # reverse_packing_consumption() flow.
        linked_packing_slip = frappe.db.get_value(
            "Packing Slip", {"stock_entry": self.name}, "name"
        )
        if linked_packing_slip:
            frappe.throw(_(
                "This Stock Entry was generated from Packing Slip {0} and cannot "
                "be cancelled directly — cancelling it here would reverse the "
                "stock movement without clearing the Packing Slip's stock_entry/"
                "status, leaving it permanently locked out of sync with the stock "
                "ledger. Reverse the consumption from the Packing Slip instead."
            ).format(linked_packing_slip))

        if self.work_order:
            wo_status = frappe.db.get_value("Work Order", self.work_order, "status")
            frappe.throw(_(
                "This Stock Entry was generated from Work Order {0} (currently {1}) "
                "and cannot be cancelled directly — cancelling it here would reverse "
                "the stock movement without updating the Work Order's produced/"
                "consumed/transferred quantities and status, leaving them out of "
                "sync with the stock ledger. Use the Work Order's own actions "
                "(Stop/reverse production there) instead."
            ).format(self.work_order, wo_status))

    def on_cancel(self):
        self._guard_manufacturing_links()
        self._reverse_sle()
        # Reverse GL entries that were posted on submit
        try:
            from zoho_books_clone.accounts.accounting_engine import reverse_voucher
            reverse_voucher("Stock Entry", self.name)
        except Exception:
            pass   # GL reversal is best-effort; stock reversal is the primary action

    def _reverse_sle(self):
        sles = frappe.get_all(
            "Stock Ledger Entry",
            filters={"voucher_type": "Stock Entry", "voucher_no": self.name, "is_cancelled": 0},
            fields=["name", "item_code", "warehouse", "batch_no", "actual_qty", "valuation_rate",
                    "stock_value_difference", "posting_date"],
        )
        for sle in sles:
            # Mark original as cancelled
            frappe.db.set_value("Stock Ledger Entry", sle.name, "is_cancelled", 1)

            # Create reversal entry
            current_qty = flt(
                frappe.db.get_value("Bin", {"item_code": sle.item_code, "warehouse": sle.warehouse}, "actual_qty")
            )
            rev_qty = -flt(sle.actual_qty)
            qty_after = current_qty + rev_qty

            # Mirror the GL reversal convention: the reversal row is ALSO flagged
            # is_cancelled=1, so active-SLE sums (reports, FIFO layers, ageing)
            # see net zero from a cancelled voucher. Leaving it active would
            # double-count the cancellation and, for issue reversals, inject a
            # bogus 0-rate FIFO layer into future COGS. Bin quantities stay
            # correct either way because _update_bin runs on insert regardless.
            rev = frappe.get_doc({
                "doctype": "Stock Ledger Entry",
                "item_code": sle.item_code,
                "warehouse": sle.warehouse,
                "batch_no": sle.batch_no or None,
                "posting_date": sle.posting_date,
                "posting_time": "00:00:01",
                "voucher_type": "Stock Entry",
                "voucher_no": self.name,
                "company": self.company,
                "actual_qty": rev_qty,
                "qty_after_transaction": qty_after,
                "incoming_rate": 0,
                "valuation_rate": flt(sle.valuation_rate),
                "stock_value": flt(qty_after) * flt(sle.valuation_rate),
                "stock_value_difference": -flt(sle.stock_value_difference),
                "is_cancelled": 1,
            })
            rev.name = frappe.generate_hash(txt=f"{sle.item_code}{sle.warehouse}{frappe.utils.now()}rev", length=10)
            rev.flags.ignore_links = True
            rev.flags.ignore_mandatory = True
            rev.insert(ignore_permissions=True)
            # NOTE: do NOT call _sync_bin here — SLE.after_insert._update_bin() handles it.

            # Mirror the qty back onto the Batch record too.
            if sle.batch_no:
                self._adjust_batch_qty(sle.batch_no, rev_qty)

        frappe.db.commit()