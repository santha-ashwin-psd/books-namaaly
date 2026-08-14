import frappe
from frappe import _
from frappe.utils import flt, today, getdate
from frappe.model.document import Document
from zoho_books_clone.accounts.accounting_engine import (
    post_sales_invoice, reverse_voucher,
)
from zoho_books_clone.db.validators import (
    validate_fiscal_year, validate_account_company, validate_account_type,
    set_posting_time,
)


class SalesInvoice(Document):

    def validate(self):
        set_posting_time(self)
        self.validate_items()
        self.validate_batches()
        self.calculate_totals()
        self.set_outstanding_amount()
        self.validate_accounts()
        self.set_status()
        self.set_due_date()
        self._set_customer_gstin()
        if self.posting_date and self.company:
            try:
                self.fiscal_year = validate_fiscal_year(self.posting_date, self.company)
            except frappe.ValidationError:
                raise  # surface lock_date / closed-year errors
            except Exception:
                pass  # ignore only unexpected errors (missing FY on draft is OK)

    def _set_customer_gstin(self):
        if self.customer and not self.customer_gstin:
            gstin = frappe.db.get_value("Customer", self.customer, "tax_id")
            if gstin:
                self.customer_gstin = gstin

    def validate_items(self):
        if not self.items:
            frappe.throw(_("Please add at least one item"))
        for item in self.items:
            # Return invoices (credit notes) carry negative qty by design
            if not self.is_return and flt(item.qty) <= 0:
                frappe.throw(_("Qty must be > 0 for {0}").format(item.item_name))
            base = round(flt(item.qty) * flt(item.rate), 2)
            item.discount_percentage = flt(item.discount_percentage)
            if item.discount_percentage:
                item.discount_amount = round(base * item.discount_percentage / 100, 2)
            else:
                item.discount_amount = flt(item.discount_amount)
            item.amount = round(base - item.discount_amount, 2)

    def validate_batches(self):
        """For batch-tracked items, a Batch No is mandatory and the row's Qty
        can never exceed that batch's currently available stock (live SLE
        balance, summed across warehouses) — e.g. Batch B1 has 50 in stock:
        an invoice line for 40 is fine, 60 is rejected.

        Skipped for return invoices (credit notes): those carry negative qty
        and put stock back in, so the "don't oversell a batch" check doesn't
        apply the same way.

        Also skipped entirely when update_stock is off: a plain
        accounting-only Sales Invoice (stock is owned by a separate Delivery
        Note, or this item was never meant to hit the stock ledger from here)
        never touches a batch, so demanding one here would block an
        otherwise-valid invoice for no reason.
        """
        if self.is_return:
            return
        if not flt(getattr(self, "update_stock", 0)):
            for item in self.items:
                item.batch_no = None
                item.batch_expiry_date = None
            return
        for item in self.items:
            if not item.item_code or flt(item.qty) <= 0:
                continue
            has_batch_no = frappe.db.get_value("Item", item.item_code, "has_batch_no")
            if not has_batch_no:
                item.batch_no = None
                item.batch_expiry_date = None
                continue

            if not item.batch_no:
                frappe.throw(_(
                    "Row #{0}: {1} is a batch-tracked item — Batch No is required"
                ).format(item.idx, item.item_name or item.item_code))

            batch = frappe.db.get_value(
                "Batch", item.batch_no, ["item", "expiry_date", "disabled"], as_dict=True
            )
            if not batch:
                frappe.throw(_(
                    "Row #{0}: Batch {1} does not exist"
                ).format(item.idx, item.batch_no))
            if batch.item and batch.item != item.item_code:
                frappe.throw(_(
                    "Row #{0}: Batch {1} belongs to item {2}, not {3}"
                ).format(item.idx, item.batch_no, batch.item, item.item_code))
            if batch.disabled:
                frappe.throw(_(
                    "Row #{0}: Batch {1} is disabled and cannot be sold"
                ).format(item.idx, item.batch_no))
            if batch.expiry_date and self.posting_date and getdate(batch.expiry_date) < getdate(self.posting_date):
                frappe.throw(_(
                    "Row #{0}: Batch {1} expired on {2} and cannot be invoiced"
                ).format(item.idx, item.batch_no, batch.expiry_date))

            item.batch_expiry_date = batch.expiry_date

            # Scoped to the row's actual warehouse (not a global item+batch sum
            # across every warehouse) -- a batch split across warehouses could
            # otherwise pass this check using stock that physically sits
            # elsewhere, letting the invoice submit and then post the
            # warehouse it actually draws from negative. See
            # inventory.utils.get_batch_qty_in_warehouse for the same fix
            # applied to Stock Entry's own guard.
            #
            # Sales Invoice Item has no warehouse field of its own -- reuse
            # stock_link.resolve_intended_warehouse(), the same set_warehouse >
            # item default_warehouse > Books default chain stock_link.py's
            # on_sales_invoice_submit() will actually deduct from, so this
            # check and the real deduction always agree on which warehouse.
            from zoho_books_clone.inventory.utils import get_batch_qty_in_warehouse
            from zoho_books_clone.inventory.stock_link import resolve_intended_warehouse
            warehouse = resolve_intended_warehouse(self, item)
            if warehouse:
                available_qty = get_batch_qty_in_warehouse(item.batch_no, warehouse)
            else:
                # No warehouse resolved yet on this row -- fall back to the old
                # global check rather than blocking on an unrelated warehouse
                # resolution gap; stock_link.py resolves the real warehouse at
                # submit time and Stock Entry's own (now warehouse-scoped)
                # guard is the final backstop either way.
                available_qty = flt(frappe.db.sql("""
                    SELECT SUM(actual_qty) FROM `tabStock Ledger Entry`
                    WHERE item_code = %s AND batch_no = %s AND is_cancelled = 0
                """, (item.item_code, item.batch_no))[0][0] or 0)

            if flt(item.qty) > available_qty:
                frappe.throw(_(
                    "Row #{0}: {1} — Batch {2} exceeds available stock "
                    "(Available: {3}, Entered: {4})"
                ).format(item.idx, item.item_name or item.item_code, item.batch_no,
                         available_qty, flt(item.qty)))

    def calculate_totals(self):
        subtotal = sum(flt(i.amount) for i in self.items)
        self.calculate_discount(subtotal)
        net = subtotal - flt(self.additional_discount_amount)
        for tax in (self.taxes or []):
            # A rate-based tax line is always derived from the current net
            # total — recompute on every save so later edits to items/
            # discounts are reflected, not just the first time the row goes
            # from 0 to non-zero. Only tax lines with no rate (rate=0, e.g.
            # a manually entered flat charge) keep whatever tax_amount the
            # user typed in directly.
            if flt(tax.rate):
                tax.tax_amount = round(net * flt(tax.rate) / 100, 2)
        tax_total = sum(flt(t.tax_amount) for t in (self.taxes or []))
        self.net_total = round(net, 2)
        self.total_tax = round(tax_total, 2)
        # GST rule (Sec 170, CGST Act): the invoice total is rounded off to
        # the nearest rupee, with the adjustment shown as its own "Round
        # Off" line — e.g. a computed total of ₹35,503.59 is invoiced (and
        # collected) as ₹35,504.00. Without this the saved grand_total just
        # carries the raw paise remainder straight into the list/ledger.
        pre_round_total = net + tax_total
        self.grand_total = round(pre_round_total)
        self.round_off = round(self.grand_total - pre_round_total, 2)

    def calculate_discount(self, subtotal):
        """Common invoice-level discount applied on the items subtotal,
        before tax. Percentage mode derives the amount from subtotal;
        Amount mode is taken as entered (clamped to the subtotal)."""
        self.discount_type = self.discount_type or "Percentage"
        if self.discount_type == "Percentage":
            self.additional_discount_percentage = flt(self.additional_discount_percentage)
            self.additional_discount_amount = round(
                subtotal * self.additional_discount_percentage / 100, 2
            )
        else:
            self.additional_discount_percentage = 0
            self.additional_discount_amount = round(flt(self.additional_discount_amount), 2)
        # Never let discount exceed subtotal or go negative
        self.additional_discount_amount = max(
            0.0, min(flt(self.additional_discount_amount), subtotal)
        )

    def set_outstanding_amount(self):
        # For credit notes, outstanding is always 0 (balance tracked separately)
        if self.is_return:
            return
        if self.docstatus == 0:
            # Draft: always keep outstanding_amount in sync with grand_total
            # so that editing items reflects the correct balance immediately
            self.outstanding_amount = self.grand_total

    def validate_accounts(self):
        if self.debit_to:
            validate_account_company(self.debit_to, self.company)
            validate_account_type(self.debit_to, ["Receivable"])
        if self.income_account:
            validate_account_company(self.income_account, self.company)
            validate_account_type(self.income_account, ["Income"])

    def set_status(self):
        if self.docstatus == 2:
            self.status = "Cancelled"
        elif self.docstatus == 1:
            if flt(self.outstanding_amount) <= 0:
                self.status = "Paid"
            elif flt(self.outstanding_amount) < flt(self.grand_total):
                self.status = "Partly Paid"
            elif self.due_date and getdate(self.due_date) < getdate(today()):
                self.status = "Overdue"
            else:
                self.status = "Submitted"
        else:
            self.status = "Draft"

    def set_due_date(self):
        if not self.due_date:
            # Try payment terms first
            if self.payment_terms and self.posting_date:
                try:
                    from zoho_books_clone.books_setup.doctype.payment_terms.payment_terms import get_due_date
                    self.due_date = get_due_date(self.payment_terms, self.posting_date)
                    return
                except Exception:
                    pass
            self.due_date = self.posting_date

    def on_submit(self):
        if getattr(self, "is_return", 0):
            cn_amount = abs(flt(self.grand_total))

            # Guard: check that the source invoice still has enough unclaimed
            # value. Capped against grand_total minus what prior credit notes
            # have already claimed against it — mirrors the analogous debit
            # note guard in purchase_invoice.py::on_submit(). Without this,
            # credit notes could be submitted with no ceiling at all, and
            # _sync_parent_invoice_after_cn_submit() would silently clamp the
            # parent's outstanding_amount to 0 rather than reject the
            # over-claim, masking data-entry mistakes (e.g. issuing several
            # credit notes that together exceed the original invoice value).
            if getattr(self, "return_against", None):
                src_grand_total = abs(flt(frappe.db.get_value(
                    "Sales Invoice", self.return_against, "grand_total"
                ) or 0))
                already_claimed = abs(flt(frappe.db.sql("""
                    SELECT COALESCE(SUM(grand_total), 0)
                    FROM `tabSales Invoice`
                    WHERE return_against = %s AND is_return = 1
                      AND docstatus = 1 AND name != %s
                """, (self.return_against, self.name))[0][0]))
                remaining_claimable = src_grand_total - already_claimed
                if remaining_claimable < cn_amount - 0.01:
                    frappe.throw(_(
                        "Cannot submit Credit Note {0}: the Sales Invoice {1} "
                        "already has its claimable value fully used "
                        "(remaining: ₹{2:,.2f}, this note: ₹{3:,.2f})."
                    ).format(
                        self.name,
                        self.return_against,
                        remaining_claimable,
                        cn_amount,
                    ))

            self.db_set("status", "Submitted", update_modified=False)
            self.status = "Submitted"
            post_sales_invoice(self)
        else:
            new_outstanding = flt(self.grand_total)
            self.outstanding_amount = new_outstanding
            self.status = "Submitted"
            self.db_set("outstanding_amount", new_outstanding, update_modified=False)
            self.db_set("status", "Submitted", update_modified=False)
            post_sales_invoice(self)
            if getattr(self, "update_stock", 0) and getattr(self, "sales_order", None):
                self._release_reserved_qty(direction=-1)
            self._maybe_auto_send_email()

    def _maybe_auto_send_email(self):
        """Send invoice email automatically if the per-company flag is on."""
        try:
            auto_send = frappe.db.get_value("Books Company", self.company, "auto_send_invoice")
        except Exception:
            auto_send = 0
        if not auto_send:
            return
        try:
            self.send_invoice_email()
        except Exception as e:
            # Log but never let a mail failure break the submission
            frappe.log_error(str(e), f"Auto-send invoice email failed for {self.name}")

    def on_cancel(self):
        self.status = "Cancelled"
        self._check_no_payments_before_cancel()
        reverse_voucher(self.doctype, self.name)
        if getattr(self, "update_stock", 0) and getattr(self, "sales_order", None):
            self._release_reserved_qty(direction=+1)
        # Reverse billed_qty on linked SO lines so the SO becomes re-invoiceable
        if getattr(self, "sales_order", None):
            self._reverse_billed_qty()
        self._auto_cancel_linked_eway_bill()

    def _auto_cancel_linked_eway_bill(self):
        """A cancelled invoice can't legally move goods, so any still-active
        E-Way Bill generated against it must be cancelled too — otherwise it's
        left dangling as 'Generated' against a voided invoice."""
        active_ewb = frappe.db.get_value(
            "E Way Bill", {"invoice_no": self.name, "status": "Generated"}, "name"
        )
        if not active_ewb:
            return
        try:
            ewb = frappe.get_doc("E Way Bill", active_ewb)
            ewb.status = "Cancelled"
            ewb.cancellation_reason = _("Auto-cancelled: linked Sales Invoice {0} was cancelled").format(self.name)
            ewb.save(ignore_permissions=True)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Failed to auto-cancel E Way Bill for cancelled invoice {self.name}",
            )

    def _reverse_billed_qty(self):
        """Decrement billed_qty on the linked Sales Order lines and refresh SO status.

        Matches by the exact SO Item row (row.so_item) when present — this is
        the correct path for every invoice created after so_item was added to
        Sales Invoice Item. Falls back to item_code-based matching only for
        older invoices that predate that field (so_item will be 0/unset on
        those rows), preserving the previous behaviour for historical data.
        """
        so_name = self.sales_order
        for row in (self.items or []):
            if not row.item_code or flt(row.qty) <= 0:
                continue
            so_item_id = getattr(row, "so_item", None)
            if so_item_id:
                cur = flt(frappe.db.get_value("Sales Order Item", so_item_id, "billed_qty"))
                take = min(cur, flt(row.qty))
                if take > 0:
                    frappe.db.set_value(
                        "Sales Order Item", so_item_id, "billed_qty",
                        max(0.0, cur - take), update_modified=False,
                    )
                continue
            # Legacy fallback: no so_item stored on this row — match by
            # item_code across the SO's rows (may misattribute across
            # multiple rows of the same item, same as before this fix).
            so_rows = frappe.db.sql("""
                SELECT name, billed_qty FROM `tabSales Order Item`
                WHERE parent = %s AND item_code = %s
                ORDER BY idx
            """, (so_name, row.item_code), as_dict=True)
            remaining_to_reverse = flt(row.qty)
            for sr in so_rows:
                if remaining_to_reverse <= 0:
                    break
                take = min(flt(sr.billed_qty), remaining_to_reverse)
                if take <= 0:
                    continue
                frappe.db.set_value(
                    "Sales Order Item", sr.name, "billed_qty",
                    max(0.0, flt(sr.billed_qty) - take),
                    update_modified=False,
                )
                remaining_to_reverse -= take
        # Recalculate SO status so the Invoice button reappears
        try:
            from zoho_books_clone.api.docs import _so_status_from_fulfillment
            new_status = _so_status_from_fulfillment(so_name)
            frappe.db.set_value("Sales Order", so_name, "status",
                                new_status, update_modified=True)
        except Exception:
            pass

    def _release_reserved_qty(self, direction: int):
        """Release (direction=-1) or restore (+1) reserved_qty when invoicing directly against an SO."""
        from zoho_books_clone.inventory.utils import update_bin
        warehouse = getattr(self, "set_warehouse", None) or ""
        for row in (self.items or []):
            wh = getattr(row, "warehouse", None) or warehouse
            if not wh or not row.item_code:
                continue
            qty = flt(row.qty)
            if qty <= 0:
                continue
            is_stock = frappe.db.get_value("Item", row.item_code, "is_stock_item")
            if not is_stock:
                continue
            update_bin(
                item_code=row.item_code,
                warehouse=wh,
                reserved_qty_delta=direction * qty,
                company=self.company or "",
            )

    def _check_no_payments_before_cancel(self):
        linked = frappe.db.sql("""
            SELECT per.parent FROM `tabPayment Entry Reference` per
            JOIN `tabPayment Entry` pe ON pe.name = per.parent
            WHERE per.reference_name = %s AND pe.docstatus = 1
        """, self.name, as_dict=True)
        if linked:
            frappe.throw(_(
                "Cannot cancel {0} — linked payment(s) exist: {1}"
            ).format(self.name, ", ".join(r.parent for r in linked)))

    def _get_currency_symbol(self):
        cur = self.currency or "INR"
        sym = frappe.db.get_value("Currency", cur, "symbol")
        return sym or (cur + " ")

    @frappe.whitelist()
    def send_invoice_email(self):
        customer_email = frappe.db.get_value("Customer", self.customer, "email_id")
        if not customer_email:
            frappe.throw(_("Customer {0} has no email").format(self.customer))

        sym = self._get_currency_symbol()
        cur = self.currency or "INR"
        subject = f"Invoice {self.name} ({cur})"
        body = (
            f"Dear {self.customer_name},<br><br>"
            f"Please find your invoice <b>{self.name}</b> for "
            f"<b>{sym}{self.grand_total:,.2f} {cur}</b>.<br>"
            f"Due date: {self.due_date}<br><br>"
            f"Regards,<br>{self.company or ''}"
        )

        # Use frappe.sendmail so Frappe creates an Email Queue entry visible
        # under Home > Email > Email Queue. This is the only correct way to
        # send email from on_submit — attach_print is NOT used here because it
        # requires a named Print Format doctype record ("Sales Invoice") that
        # may not exist, which would crash silently and produce no queue entry.
        # The manual Send Email button (EmailDialog -> docs.send_invoice_email)
        # handles PDF attachment when the user explicitly sends.
        frappe.sendmail(
            recipients=[customer_email],
            subject=subject,
            message=body,
            reference_doctype=self.doctype,
            reference_name=self.name,
            now=False,  # queue it — correct for on_submit context
        )

    @frappe.whitelist()
    def get_payment_status(self):
        payments = frappe.db.sql("""
            SELECT pe.name, pe.payment_date, per.allocated_amount
            FROM `tabPayment Entry` pe
            JOIN `tabPayment Entry Reference` per ON per.parent = pe.name
            WHERE per.reference_name = %s AND pe.docstatus = 1
            ORDER BY pe.payment_date
        """, self.name, as_dict=True)
        return {
            "payments":           payments,
            "total_paid":         sum(flt(p.allocated_amount) for p in payments),
            "outstanding_amount": self.outstanding_amount,
            "grand_total":        self.grand_total,
        }