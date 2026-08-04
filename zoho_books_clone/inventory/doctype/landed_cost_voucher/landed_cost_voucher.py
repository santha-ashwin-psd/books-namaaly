from __future__ import annotations
"""
Landed Cost Voucher — capitalizes freight/transport/other charges into item
valuation for a Purchase Receipt or Purchase Invoice that has already posted
its normal Stock Entry and GL entries.

Phase 1: data model — defaults, source-document validation, total roll-ups.
Phase 2 (via inventory/landed_cost_engine.py): proportional allocation of the
combined charge pool across item rows (by value or qty), populating
items[].allocated_amount and items[].new_valuation_rate on every save.
Phase 3 (on_submit/on_cancel below): writes one value-only Stock Ledger Entry
per item row (actual_qty=0, stock_value_difference=allocated_amount) so the
allocation actually lands on Bin.stock_value/valuation_rate — reusing
StockLedgerEntry._update_bin(), now extended (inventory/utils.
compute_bin_valuation) to handle that value-only case. Cancel reverses the
same way Stock Entry does: mark the original SLEs is_cancelled and insert
mirror entries with the sign flipped.
Phase 4 (this file, _post_gl_entries): on submit, Dr Inventory Asset for
total_charges / Cr each charge row's own account for its allocated amount —
via general_ledger_entry.make_gl_entries(), the same posting path Stock
Entry uses. Sized per charge row, not a lump sum, so each ledger stays
traceable back to its source (Landed Cost Charge.reference_doctype/
reference_name). Cancel calls make_gl_entries(..., cancel=True), which
reverses (not deletes) the entries — this also closes out the GL half of
Phase 6's cancel/amend handling.

Phase 5 (this file, _validate_no_duplicate_charge_capitalization / the rewritten
_create_valuation_sles / the rewritten _post_gl_entries): guardrails.
  - Blocks capitalizing the same sourced charge (Landed Cost Charge.
    reference_doctype/reference_name) through more than one submitted LCV —
    prevents the exact double-count the client flagged, without blocking
    legitimate multiple LCVs against the same PR/PI for genuinely different
    charges (e.g. a freight bill now, a customs duty bill later).
  - Replaces the old silent full-skip for partially-issued stock with a
    proportional capitalization: if only part of a row's received_qty is
    still on hand, only that fraction of its allocated charge is capitalized
    into Bin value; the rest is left in its original expense account rather
    than force-fit into inventory that no longer holds that qty. This mirrors
    ERPNext's own limitation (landed cost can't retroactively correct COGS
    already posted for issued stock) but makes it visible and *balanced*:
    total_capitalized_amount is tracked on the parent and on each item row,
    and _post_gl_entries scales every charge's GL credit by the same
    capitalized/total ratio so Dr Inventory always equals the sum of what
    was actually written to Bin.stock_value — no phantom value.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today

from zoho_books_clone.inventory.landed_cost_engine import (
    allocate_charges,
    build_landed_cost_gl_map,
    compute_capitalizable_amount,
    compute_gl_scale_ratio,
    scale_charges_for_capitalization,
)
from zoho_books_clone.inventory.utils import get_valuation_rate
from zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry import make_gl_entries
from zoho_books_clone.db.validators import set_posting_time


class LandedCostVoucher(Document):

    # ── Validate ──────────────────────────────────────────────────────────

    def validate(self):
        self._set_defaults()
        set_posting_time(self)
        self._validate_source_document()
        self._validate_rows()
        self._validate_no_duplicate_charge_capitalization()
        self._snapshot_valuation_rates()
        self._calculate_totals()
        self._allocate()

    def _set_defaults(self):
        if not self.posting_date:
            self.posting_date = today()
        if not self.company:
            self.company = (
                frappe.db.get_single_value("Books Settings", "default_company")
                or frappe.db.get_default("company")
                or ""
            )
        if not self.distribution_method:
            self.distribution_method = "By Value"

    def _validate_source_document(self):
        """Exactly one of Purchase Receipt / Purchase Invoice, and it must
        already be submitted — an LCV reclassifies charges after the goods
        document has posted its own Stock Entry and GL entries."""
        has_pr = bool(self.purchase_receipt)
        has_pi = bool(self.purchase_invoice)

        if has_pr == has_pi:
            frappe.throw(
                _("Set exactly one of Purchase Receipt or Purchase Invoice, not both or neither.")
            )

        doctype, name = ("Purchase Receipt", self.purchase_receipt) if has_pr else (
            "Purchase Invoice", self.purchase_invoice
        )
        docstatus = frappe.db.get_value(doctype, name, "docstatus")
        if docstatus is None:
            frappe.throw(_("{0} {1} not found.").format(doctype, name))
        if docstatus != 1:
            frappe.throw(
                _("{0} {1} must be submitted before a Landed Cost Voucher can be created against it.").format(
                    doctype, name
                )
            )

    def _validate_rows(self):
        if not self.items:
            frappe.throw(_("Add at least one item row."))
        if not self.charges:
            frappe.throw(_("Add at least one charge row."))
        for row in self.items:
            if flt(row.received_qty) <= 0:
                frappe.throw(_("Row {0}: Received Qty must be greater than zero.").format(row.idx))
        for row in self.charges:
            if flt(row.amount) <= 0:
                frappe.throw(_("Row {0}: Charge Amount must be greater than zero.").format(row.idx))
            if not (row.reference_doctype and row.reference_name) and not row.paid_through:
                frappe.throw(
                    _(
                        "Row {0}: set either a Reference DocType/Name (if this charge was "
                        "already booked elsewhere) or a Paid Through account (so an Expense "
                        "entry can be created for it automatically on submit)."
                    ).format(row.idx)
                )

    def _validate_no_duplicate_charge_capitalization(self):
        """Block capitalizing the same sourced charge through more than one
        submitted Landed Cost Voucher. Only applies to charge rows that carry
        a reference_doctype/reference_name (a specific Purchase Invoice or
        Journal Entry the charge was booked against) — informal cash charges
        with no source document have nothing to dedupe against.

        This is a save-time check (validate() runs on every save, not just
        submit) so the conflict surfaces as early as possible, before the
        user has filled in the rest of the form.
        """
        for row in self.charges:
            if not (row.reference_doctype and row.reference_name):
                continue

            existing = frappe.db.sql(
                """
                select lcv.name
                from `tabLanded Cost Charge` lcc
                inner join `tabLanded Cost Voucher` lcv on lcv.name = lcc.parent
                where lcc.reference_doctype = %(rdt)s
                  and lcc.reference_name = %(rn)s
                  and lcv.docstatus = 1
                  and lcv.name != %(self_name)s
                limit 1
                """,
                {
                    "rdt": row.reference_doctype,
                    "rn": row.reference_name,
                    "self_name": self.name or "",
                },
                as_dict=True,
            )
            if existing:
                frappe.throw(
                    _(
                        "Row {0}: the charge from {1} {2} has already been capitalized "
                        "via Landed Cost Voucher {3}. Each charge source can only be "
                        "capitalized once — reclassifying it a second time would double-count it."
                    ).format(row.idx, row.reference_doctype, row.reference_name, existing[0].name)
                )

    def _calculate_totals(self):
        self.total_purchase_amount = sum(flt(row.purchase_amount) for row in self.items)
        self.total_charges = sum(flt(row.amount) for row in self.charges)

    def _snapshot_valuation_rates(self):
        """Capture Bin.valuation_rate once, the first time a row is saved —
        it's a point-in-time snapshot of "what the rate was when this LCV was
        created", not something that should drift on later edits/re-saves."""
        for row in self.items:
            if not row.valuation_rate and row.item_code and row.warehouse:
                row.valuation_rate = get_valuation_rate(row.item_code, row.warehouse)

    def _allocate(self):
        """Recompute allocated_amount / new_valuation_rate for every item row
        from the current charges, via the Phase 2 engine. Pure math on doc
        fields — no Bin or GL writes (Phase 3/4)."""
        items = [
            {
                "item_code": row.item_code,
                "received_qty": row.received_qty,
                "purchase_amount": row.purchase_amount,
            }
            for row in self.items
        ]
        charges = [{"amount": row.amount} for row in self.charges]

        allocated = allocate_charges(items, charges, self.distribution_method)
        for row, computed in zip(self.items, allocated):
            row.allocated_amount = computed["allocated_amount"]
            row.new_valuation_rate = computed["new_valuation_rate"]

    # ── Submit / Cancel ──────────────────────────────────────────────────

    def on_submit(self):
        self._create_expense_entries()
        total_capitalized = self._create_valuation_sles()
        self.db_set("total_capitalized_amount", total_capitalized, update_modified=False)
        self._post_gl_entries(total_capitalized)

    def on_cancel(self):
        self._reverse_valuation_sles()
        try:
            make_gl_entries(
                [{"voucher_type": "Landed Cost Voucher", "voucher_no": self.name}],
                cancel=True,
            )
        except Exception:
            # Mirrors Stock Entry.on_cancel: GL reversal is best-effort so a
            # GL-side failure never blocks the (higher-priority) stock
            # reversal that already happened above.
            frappe.log_error(frappe.get_traceback(), "Landed Cost GL reversal failed")

    def _default_expense_category(self) -> str | None:
        """Resolve the "Miscellaneous" Expense Category doc for this LCV's
        company, used only when a charge row has no expense_type set.
        expense_type is a Link to Expense Category, whose autoname format is
        "{category_name} - {company}" — so the bare word "Miscellaneous" is
        never itself a valid value; it has to be looked up per company.
        Falls back to None (Expense.insert() will then raise its own
        mandatory-field error) if that category was never seeded for this
        company, rather than guessing/creating one here.
        """
        return frappe.db.get_value(
            "Expense Category", {"category_name": "Miscellaneous", "company": self.company}
        )

    def _create_expense_entries(self):
        """For every charge row with no existing Reference DocType/Name (i.e.
        nothing was already booked for it via a separate Bill/Journal Entry),
        auto-create and submit a proper Expense record: Dr this charge's
        account / Cr Paid Through. This gives the charge a real audit-trail
        entry visible in the Expenses module/reports before _post_gl_entries
        reclassifies it out of that same account and into Inventory — net
        effect is Dr Inventory / Cr Paid Through, same as before, but now
        with a traceable Expense document in between instead of a bare GL
        credit with nothing backing it.

        Rows that already carry a reference (an existing Bill/Journal Entry)
        are left untouched — creating another Expense for those would
        double-book the charge.
        """
        for row in self.charges:
            if row.reference_doctype and row.reference_name:
                continue
            if not row.paid_through:
                # _validate_rows() already enforces this at save time, but
                # guard again here in case a row was force-set between save
                # and submit.
                frappe.throw(
                    _("Row {0}: Paid Through is required to auto-create its Expense entry.").format(row.idx)
                )

            expense = frappe.get_doc({
                "doctype": "Expense",
                "posting_date": self.posting_date,
                "expense_type": row.expense_type or self._default_expense_category(),
                "description": row.description or f"Landed cost charge — {self.name}",
                "amount": flt(row.amount),
                "expense_account": row.account,
                "paid_through": row.paid_through,
                "company": self.company,
                "vendor": row.supplier or None,
                "reference_no": self.name,
            })
            expense.insert(ignore_permissions=True)
            expense.submit()

            row.db_set("reference_doctype", "Expense", update_modified=False)
            row.db_set("reference_name", expense.name, update_modified=False)

    def _create_valuation_sles(self) -> float:
        """One value-only Stock Ledger Entry per item row that still has some
        capitalizable amount, sized to the fraction of received_qty that's
        still actually on hand.

        - Fully on hand (current_qty >= received_qty): capitalize the whole
          allocated_amount, same as before Phase 5.
        - Partially on hand (0 < current_qty < received_qty): capitalize only
          allocated_amount * (current_qty / received_qty). The remainder
          corresponds to stock that already left the warehouse before this
          voucher was submitted — its COGS was already posted at the old
          rate, and retroactively editing that posted COGS is out of scope
          (same limitation ERPNext has). That remainder is intentionally left
          in its original expense account: _post_gl_entries scales every
          charge's GL credit by the same ratio, so nothing is force-fit into
          inventory that Bin.stock_value doesn't actually reflect.
        - Fully issued (current_qty <= 0): nothing capitalized for this row.

        Returns the total amount actually capitalized across all rows, which
        the caller persists on the parent and passes to _post_gl_entries so
        the GL debit/credit always matches what was actually written to Bin.
        """
        total_capitalized = 0.0

        for row in self.items:
            allocated = flt(row.allocated_amount)
            if not allocated:
                row.db_set("capitalized_amount", 0, update_modified=False)
                continue

            current_qty = flt(frappe.db.get_value(
                "Bin", {"item_code": row.item_code, "warehouse": row.warehouse}, "actual_qty"
            ))
            received_qty = flt(row.received_qty)
            capitalized = compute_capitalizable_amount(allocated, received_qty, current_qty)

            if not capitalized:
                frappe.msgprint(
                    _(
                        "{0} in {1} has no remaining stock — its allocated charge of {2} "
                        "was not capitalized and remains a period expense."
                    ).format(row.item_code, row.warehouse, allocated),
                    indicator="orange", alert=True,
                )
                row.db_set("capitalized_amount", 0, update_modified=False)
                continue

            if capitalized < allocated:
                frappe.msgprint(
                    _(
                        "{0} in {1}: only part of the received qty is still on hand — "
                        "capitalized {2} of {3}; the remainder stays booked as a period expense."
                    ).format(row.item_code, row.warehouse, capitalized, allocated),
                    indicator="orange", alert=True,
                )

            row.db_set("capitalized_amount", capitalized, update_modified=False)
            total_capitalized += capitalized
            self._insert_valuation_sle(
                item_code=row.item_code,
                warehouse=row.warehouse,
                batch_no=row.batch_no,
                qty_after=current_qty,
                stock_value_difference=capitalized,
                is_cancelled=0,
                posting_time="00:00:00",
            )

        frappe.db.commit()
        return round(total_capitalized, 2)

    def _reverse_valuation_sles(self):
        sles = frappe.get_all(
            "Stock Ledger Entry",
            filters={"voucher_type": "Landed Cost Voucher", "voucher_no": self.name, "is_cancelled": 0},
            fields=["name", "item_code", "warehouse", "batch_no", "stock_value_difference", "posting_date"],
        )
        for sle in sles:
            # Mark original as cancelled — same convention Stock Entry uses,
            # so active-SLE sums (reports, valuation) see net zero.
            frappe.db.set_value("Stock Ledger Entry", sle.name, "is_cancelled", 1)

            current_qty = flt(frappe.db.get_value(
                "Bin", {"item_code": sle.item_code, "warehouse": sle.warehouse}, "actual_qty"
            ))
            self._insert_valuation_sle(
                item_code=sle.item_code,
                warehouse=sle.warehouse,
                batch_no=sle.batch_no,
                qty_after=current_qty,
                stock_value_difference=-flt(sle.stock_value_difference),
                is_cancelled=1,
                posting_time="00:00:01",
                posting_date=sle.posting_date,
            )

        frappe.db.commit()

    def _insert_valuation_sle(
        self, item_code, warehouse, batch_no, qty_after, stock_value_difference,
        is_cancelled, posting_time, posting_date=None,
    ):
        """Shared SLE-insert plumbing for both the original and the reversal
        entry. actual_qty is always 0 here — this never moves physical stock,
        only Bin.stock_value / Bin.valuation_rate (via
        StockLedgerEntry._update_bin()'s value-only branch)."""
        rate = get_valuation_rate(item_code, warehouse)
        sle = frappe.get_doc({
            "doctype": "Stock Ledger Entry",
            "item_code": item_code,
            "warehouse": warehouse,
            "batch_no": batch_no or None,
            "posting_date": posting_date or self.posting_date,
            "posting_time": posting_time,
            "voucher_type": "Landed Cost Voucher",
            "voucher_no": self.name,
            "company": self.company,
            "actual_qty": 0,
            "qty_after_transaction": qty_after,
            "incoming_rate": 0,
            "valuation_rate": rate,
            "stock_value": flt(qty_after) * rate,
            "stock_value_difference": stock_value_difference,
            "is_cancelled": is_cancelled,
        })
        sle.name = frappe.generate_hash(
            txt=f"{item_code}{warehouse}{frappe.utils.now()}", length=10
        )
        sle.flags.ignore_links = True
        sle.flags.ignore_mandatory = True
        sle.insert(ignore_permissions=True)
        # NOTE: do NOT touch Bin directly here — SLE.after_insert._update_bin()
        # is the single authoritative writer, same rule Stock Entry follows.

    # ── GL posting (Phase 4) ─────────────────────────────────────────────

    def _post_gl_entries(self, total_capitalized: float):
        """Dr Inventory Asset for total_capitalized (not total_charges — see
        Phase 5 docstring above) / Cr each charge row's own account, scaled by
        the same capitalized/total_charges ratio. Reclassifies the charge out
        of wherever it was originally booked — a Purchase Invoice's freight
        line, or an informal Journal/Payment Entry for the local transporter —
        and capitalizes it into stock, without creating a new liability (the
        source document already posted Dr Freight / Cr Payable or similar;
        this just moves it sideways into Dr Inventory / Cr Freight, netting
        the expense back to zero for whatever fraction was actually
        capitalized). Sized per charge row rather than one lump sum so each
        ledger line stays traceable back to its source via Landed Cost
        Charge.reference_doctype/reference_name.

        Scaling by ratio rather than by item keeps this simple and always
        balanced: a genuinely per-item-per-charge split would need the
        allocation engine to track a full charge×item matrix, which is more
        precision than this app's other costing (moving-average Bin
        valuation) already carries elsewhere. The un-capitalized remainder is
        simply left uncredited, i.e. it stays exactly where it already was.
        """
        if not flt(self.total_charges) or not flt(total_capitalized):
            return

        from zoho_books_clone.accounts.inventory_gl import get_inventory_account

        inventory_account = get_inventory_account(self.company) or self._get_account_by_type("Stock")
        if not inventory_account:
            frappe.log_error(
                f"Landed Cost Voucher {self.name}: no Stock-type account found for "
                f"company '{self.company}'. GL entries skipped.",
                "Landed Cost GL Posting",
            )
            return

        ratio = compute_gl_scale_ratio(total_capitalized, self.total_charges)
        charges = scale_charges_for_capitalization(
            [{"account": row.account, "amount": row.amount, "description": row.description} for row in self.charges],
            total_capitalized,
            self.total_charges,
        )

        gl_map = build_landed_cost_gl_map(
            inventory_account=inventory_account,
            charges=charges,
            voucher_no=self.name,
            posting_date=self.posting_date,
            posting_time=self.posting_time,
            company=self.company,
        )
        if gl_map:
            make_gl_entries(gl_map)

            if ratio < 1.0:
                frappe.msgprint(
                    _(
                        "Only {0} of {1} total charges was capitalized into inventory "
                        "— some received stock had already been issued before this "
                        "voucher was submitted. The remainder stays booked in its "
                        "original expense account."
                    ).format(total_capitalized, self.total_charges),
                    indicator="orange", alert=True,
                )

    def _get_account_by_type(self, account_type: str) -> str | None:
        """Return the account of the given type for this company.

        Previously picked "the first leaf account of this type" with no
        ORDER BY — harmless when a company has only one such account (the
        common case), but non-deterministic the moment a company has two:
        which one got debited depended on unspecified DB row order, and
        could silently change between runs.

        Now:
          1. For "Stock" specifically, prefer the canonical account every
             company is seeded with at signup — "Stock In Hand - {company}"
             (see books_setup/bootstrap.py's COA) — so the common case keeps
             hitting the same account it always has.
          2. Otherwise (or if that canonical account doesn't exist, e.g. it
             was renamed), fall back to a name-ordered pick so the result is
             at least stable and reproducible rather than DB-order-dependent.
        """
        if account_type == "Stock":
            canonical = f"Stock In Hand - {self.company}"
            if frappe.db.exists(
                "Account", {"name": canonical, "account_type": "Stock", "is_group": 0}
            ):
                return canonical

        row = frappe.db.get_value(
            "Account",
            {"account_type": account_type, "company": self.company, "is_group": 0},
            "name",
            order_by="name asc",
        )
        return row or None