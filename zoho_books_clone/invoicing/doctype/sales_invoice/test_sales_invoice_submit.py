# Copyright (c) 2026, PS Digitise and Contributors
# See license.txt
"""
Tests for Sales Invoice -- on_submit / on_cancel: GL posting, the credit-note
(is_return) over-claim guard, reserved-qty release/restore against a linked
Sales Order, SO billed_qty reversal, pre-cancel payment guard, and the
linked E-Way Bill auto-cancel side effect.

Same bind-real-method-onto-a-stand-in pattern as
test_purchase_invoice_submit.py -- DB-free, exercises the actual controller
code.

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.invoicing.doctype.sales_invoice.test_sales_invoice_submit
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe

from zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice import SalesInvoice


class _Dict(SimpleNamespace):
    def get(self, key, default=None):
        return getattr(self, key, default)


def _item(item_code="ITEM-1", qty=5, warehouse=None):
    return SimpleNamespace(item_code=item_code, qty=qty, warehouse=warehouse)


def _make_si(items=None, docstatus=1, company="VK Herbal", is_return=0,
             return_against=None, sales_order=None, update_stock=0,
             grand_total=1000, outstanding_amount=1000, **overrides):
    doc = _Dict(
        doctype="Sales Invoice", name="SINV-2026-00001", items=items or [],
        docstatus=docstatus, company=company, is_return=is_return,
        return_against=return_against, sales_order=sales_order,
        update_stock=update_stock, grand_total=grand_total,
        outstanding_amount=outstanding_amount, set_warehouse=None,
        due_date=None, status=None, customer_name="Test Customer",
        customer="CUST-1",
    )
    doc.db_set = MagicMock()
    for k, v in overrides.items():
        setattr(doc, k, v)
    for name in ("on_submit", "on_cancel", "_release_reserved_qty",
                 "_reverse_billed_qty", "_check_no_payments_before_cancel",
                 "_auto_cancel_linked_eway_bill", "_maybe_auto_send_email",
                 "_get_currency_symbol"):
        setattr(doc, name, getattr(SalesInvoice, name).__get__(doc))
    return doc


class TestOnSubmitNormalInvoice(unittest.TestCase):

    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.post_sales_invoice")
    def test_sets_outstanding_and_status_submitted(self, mock_post):
        doc = _make_si(is_return=0, grand_total=1180)
        doc._maybe_auto_send_email = MagicMock()
        doc.on_submit()
        doc.db_set.assert_any_call("outstanding_amount", 1180, update_modified=False)
        doc.db_set.assert_any_call("status", "Submitted", update_modified=False)
        self.assertEqual(doc.outstanding_amount, 1180)
        self.assertEqual(doc.status, "Submitted")
        mock_post.assert_called_once_with(doc)

    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.post_sales_invoice")
    def test_releases_reserved_qty_when_update_stock_and_so_linked(self, mock_post):
        doc = _make_si(is_return=0, update_stock=1, sales_order="SO-0001")
        doc._maybe_auto_send_email = MagicMock()
        released = []
        doc._release_reserved_qty = lambda direction: released.append(direction)
        doc.on_submit()
        self.assertEqual(released, [-1])

    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.post_sales_invoice")
    def test_no_reserved_qty_release_without_update_stock(self, mock_post):
        doc = _make_si(is_return=0, update_stock=0, sales_order="SO-0001")
        doc._maybe_auto_send_email = MagicMock()
        doc._release_reserved_qty = MagicMock()
        doc.on_submit()
        doc._release_reserved_qty.assert_not_called()

    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.post_sales_invoice")
    def test_no_reserved_qty_release_without_so(self, mock_post):
        doc = _make_si(is_return=0, update_stock=1, sales_order=None)
        doc._maybe_auto_send_email = MagicMock()
        doc._release_reserved_qty = MagicMock()
        doc.on_submit()
        doc._release_reserved_qty.assert_not_called()

    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.post_sales_invoice")
    def test_calls_maybe_auto_send_email(self, mock_post):
        doc = _make_si(is_return=0)
        doc._maybe_auto_send_email = MagicMock()
        doc.on_submit()
        doc._maybe_auto_send_email.assert_called_once()


class TestOnSubmitCreditNote(unittest.TestCase):

    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.post_sales_invoice")
    def test_no_return_against_skips_guard_and_posts(self, mock_post):
        doc = _make_si(is_return=1, return_against=None, grand_total=-200)
        doc.on_submit()
        doc.db_set.assert_any_call("status", "Submitted", update_modified=False)
        self.assertEqual(doc.status, "Submitted")
        mock_post.assert_called_once_with(doc)

    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.post_sales_invoice")
    def test_does_not_touch_outstanding_amount_directly(self, mock_post):
        # is_return branch never calls db_set("outstanding_amount", ...) --
        # that's handled separately by the standalone Credit Note doctype /
        # _sync logic, not here.
        doc = _make_si(is_return=1, return_against=None, grand_total=-200,
                        outstanding_amount=1000)
        doc.on_submit()
        for call in doc.db_set.call_args_list:
            self.assertNotEqual(call.args[0], "outstanding_amount")

    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.post_sales_invoice")
    @patch.object(frappe.db, "sql")
    @patch.object(frappe.db, "get_value")
    def test_guard_passes_when_enough_claimable_remains(self, mock_get_value, mock_sql, mock_post):
        mock_get_value.return_value = 1000       # source SINV grand_total
        mock_sql.return_value = [[300]]           # already claimed by other credit notes
        doc = _make_si(is_return=1, return_against="SINV-2026-00000", grand_total=-500)
        doc.on_submit()  # remaining = 1000-300=700 >= 500 -> should not raise
        mock_post.assert_called_once_with(doc)

    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.post_sales_invoice")
    @patch.object(frappe.db, "sql")
    @patch.object(frappe.db, "get_value")
    def test_guard_blocks_when_claimable_value_exhausted(self, mock_get_value, mock_sql, mock_post):
        mock_get_value.return_value = 1000
        mock_sql.return_value = [[900]]           # only 100 remaining claimable
        doc = _make_si(is_return=1, return_against="SINV-2026-00000", grand_total=-500)
        with self.assertRaises(frappe.ValidationError):
            doc.on_submit()
        mock_post.assert_not_called()

    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.post_sales_invoice")
    @patch.object(frappe.db, "sql")
    @patch.object(frappe.db, "get_value")
    def test_guard_uses_abs_grand_total_not_outstanding(self, mock_get_value, mock_sql, mock_post):
        # Fully paid source invoice (outstanding=0) must still allow a
        # credit note as long as claimable value remains -- guard must be
        # based on grand_total minus already-claimed, not outstanding_amount.
        mock_get_value.return_value = 1000
        mock_sql.return_value = [[0]]
        doc = _make_si(is_return=1, return_against="SINV-2026-00000", grand_total=-1000)
        doc.on_submit()  # should not raise -- full 1000 still claimable
        mock_post.assert_called_once()


class TestOnCancel(unittest.TestCase):

    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.reverse_voucher")
    def test_sets_cancelled_status_and_reverses_gl(self, mock_reverse):
        doc = _make_si(is_return=0, sales_order=None)
        doc._auto_cancel_linked_eway_bill = MagicMock()
        doc.on_cancel()
        self.assertEqual(doc.status, "Cancelled")
        mock_reverse.assert_called_once_with("Sales Invoice", doc.name)

    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.reverse_voucher")
    def test_blocked_when_payments_exist(self, mock_reverse):
        doc = _make_si(is_return=0)
        doc._check_no_payments_before_cancel = MagicMock(
            side_effect=frappe.ValidationError("linked payment exists")
        )
        with self.assertRaises(frappe.ValidationError):
            doc.on_cancel()
        mock_reverse.assert_not_called()

    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.reverse_voucher")
    def test_normal_cancel_with_so_and_update_stock_restores_reserved_and_reverses_billed(self, mock_reverse):
        doc = _make_si(is_return=0, sales_order="SO-0001", update_stock=1)
        doc._release_reserved_qty = MagicMock()
        doc._reverse_billed_qty = MagicMock()
        doc._auto_cancel_linked_eway_bill = MagicMock()
        doc.on_cancel()
        doc._release_reserved_qty.assert_called_once_with(direction=+1)
        doc._reverse_billed_qty.assert_called_once()

    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.reverse_voucher")
    def test_no_reserved_qty_restore_without_update_stock(self, mock_reverse):
        doc = _make_si(is_return=0, sales_order="SO-0001", update_stock=0)
        doc._release_reserved_qty = MagicMock()
        doc._reverse_billed_qty = MagicMock()
        doc._auto_cancel_linked_eway_bill = MagicMock()
        doc.on_cancel()
        doc._release_reserved_qty.assert_not_called()
        doc._reverse_billed_qty.assert_called_once()  # SO reversal not gated on update_stock

    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.reverse_voucher")
    def test_no_billed_qty_reversal_without_so(self, mock_reverse):
        doc = _make_si(is_return=0, sales_order=None, update_stock=1)
        doc._release_reserved_qty = MagicMock()
        doc._reverse_billed_qty = MagicMock()
        doc._auto_cancel_linked_eway_bill = MagicMock()
        doc.on_cancel()
        doc._release_reserved_qty.assert_not_called()
        doc._reverse_billed_qty.assert_not_called()

    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.reverse_voucher")
    def test_calls_auto_cancel_linked_eway_bill(self, mock_reverse):
        doc = _make_si(is_return=0, sales_order=None)
        doc._auto_cancel_linked_eway_bill = MagicMock()
        doc.on_cancel()
        doc._auto_cancel_linked_eway_bill.assert_called_once()


class TestCheckNoPaymentsBeforeCancel(unittest.TestCase):

    @patch.object(frappe.db, "sql", return_value=[])
    def test_passes_when_no_linked_payments(self, mock_sql):
        doc = _make_si()
        doc._check_no_payments_before_cancel()  # should not raise

    @patch.object(frappe.db, "sql")
    def test_throws_when_submitted_payment_linked(self, mock_sql):
        mock_sql.return_value = [frappe._dict({"parent": "PE-0001"})]
        doc = _make_si()
        with self.assertRaises(frappe.ValidationError):
            doc._check_no_payments_before_cancel()


class TestAutoCancelLinkedEwayBill(unittest.TestCase):

    @patch.object(frappe.db, "get_value", return_value=None)
    def test_noop_when_no_active_eway_bill(self, mock_get_value):
        doc = _make_si()
        doc._auto_cancel_linked_eway_bill()  # should not raise / not touch anything

    @patch.object(frappe, "get_doc")
    @patch.object(frappe.db, "get_value", return_value="EWB-0001")
    def test_cancels_active_eway_bill(self, mock_get_value, mock_get_doc):
        ewb = MagicMock()
        mock_get_doc.return_value = ewb
        doc = _make_si()
        doc._auto_cancel_linked_eway_bill()
        self.assertEqual(ewb.status, "Cancelled")
        ewb.save.assert_called_once_with(ignore_permissions=True)

    @patch.object(frappe, "log_error")
    @patch.object(frappe, "get_doc", side_effect=Exception("boom"))
    @patch.object(frappe.db, "get_value", return_value="EWB-0001")
    def test_failure_to_cancel_eway_bill_does_not_raise(self, mock_get_value, mock_get_doc, mock_log_error):
        doc = _make_si()
        doc._auto_cancel_linked_eway_bill()  # should not raise
        mock_log_error.assert_called_once()


class TestReleaseReservedQty(unittest.TestCase):

    @patch("zoho_books_clone.inventory.utils.update_bin")
    @patch.object(frappe.db, "get_value", return_value=1)  # is_stock_item = True
    def test_releases_reserved_qty_on_row_warehouse(self, mock_get_value, mock_update_bin):
        row = _item(item_code="ITEM-1", qty=5, warehouse="WH-1")
        doc = _make_si(items=[row], company="VK Herbal")
        doc._release_reserved_qty(direction=-1)
        mock_update_bin.assert_called_once_with(
            item_code="ITEM-1", warehouse="WH-1",
            reserved_qty_delta=-5, company="VK Herbal",
        )

    @patch("zoho_books_clone.inventory.utils.update_bin")
    @patch.object(frappe.db, "get_value", return_value=0)  # not a stock item
    def test_skips_non_stock_items(self, mock_get_value, mock_update_bin):
        row = _item(item_code="SERVICE-1", qty=3, warehouse="WH-1")
        doc = _make_si(items=[row])
        doc._release_reserved_qty(direction=-1)
        mock_update_bin.assert_not_called()

    @patch("zoho_books_clone.inventory.utils.update_bin")
    def test_skips_zero_or_negative_qty_rows(self, mock_update_bin):
        row = _item(item_code="ITEM-1", qty=0, warehouse="WH-1")
        doc = _make_si(items=[row])
        doc._release_reserved_qty(direction=-1)
        mock_update_bin.assert_not_called()

    @patch("zoho_books_clone.inventory.utils.update_bin")
    def test_skips_rows_without_warehouse(self, mock_update_bin):
        row = _item(item_code="ITEM-1", qty=5, warehouse=None)
        doc = _make_si(items=[row], set_warehouse=None)
        doc._release_reserved_qty(direction=-1)
        mock_update_bin.assert_not_called()

    @patch("zoho_books_clone.inventory.utils.update_bin")
    @patch.object(frappe.db, "get_value", return_value=1)
    def test_falls_back_to_header_set_warehouse(self, mock_get_value, mock_update_bin):
        row = _item(item_code="ITEM-1", qty=5, warehouse=None)
        doc = _make_si(items=[row], set_warehouse="WH-DEFAULT")
        doc._release_reserved_qty(direction=1)
        mock_update_bin.assert_called_once_with(
            item_code="ITEM-1", warehouse="WH-DEFAULT",
            reserved_qty_delta=5, company="VK Herbal",
        )


class TestReverseBilledQty(unittest.TestCase):

    @patch("zoho_books_clone.api.docs._so_status_from_fulfillment", return_value="To Bill")
    @patch.object(frappe.db, "set_value")
    @patch.object(frappe.db, "sql")
    def test_decrements_billed_qty_on_matching_so_rows_in_order(self, mock_sql, mock_set_value, mock_status):
        row = _item(item_code="ITEM-1", qty=8)
        doc = _make_si(items=[row], sales_order="SO-0001")
        mock_sql.return_value = [
            frappe._dict({"name": "SOI-1", "billed_qty": 5}),
            frappe._dict({"name": "SOI-2", "billed_qty": 6}),
        ]
        doc._reverse_billed_qty()

        mock_set_value.assert_any_call("Sales Order Item", "SOI-1", "billed_qty", 0.0, update_modified=False)
        mock_set_value.assert_any_call("Sales Order Item", "SOI-2", "billed_qty", 3, update_modified=False)
        mock_status.assert_called_once_with("SO-0001")

    @patch("zoho_books_clone.api.docs._so_status_from_fulfillment", return_value="Billed")
    @patch.object(frappe.db, "set_value")
    @patch.object(frappe.db, "sql")
    def test_clamps_at_zero_never_goes_negative(self, mock_sql, mock_set_value, mock_status):
        row = _item(item_code="ITEM-1", qty=100)
        doc = _make_si(items=[row], sales_order="SO-0001")
        mock_sql.return_value = [frappe._dict({"name": "SOI-1", "billed_qty": 5})]
        doc._reverse_billed_qty()
        mock_set_value.assert_any_call("Sales Order Item", "SOI-1", "billed_qty", 0.0, update_modified=False)

    @patch("zoho_books_clone.api.docs._so_status_from_fulfillment", side_effect=Exception("boom"))
    @patch.object(frappe.db, "set_value")
    @patch.object(frappe.db, "sql")
    def test_status_refresh_failure_does_not_raise(self, mock_sql, mock_set_value, mock_status):
        row = _item(item_code="ITEM-1", qty=5)
        doc = _make_si(items=[row], sales_order="SO-0001")
        mock_sql.return_value = [frappe._dict({"name": "SOI-1", "billed_qty": 5})]
        doc._reverse_billed_qty()  # should not raise


class TestMaybeAutoSendEmail(unittest.TestCase):

    @patch.object(frappe.db, "get_value", return_value=0)  # auto_send off
    def test_noop_when_auto_send_disabled(self, mock_get_value):
        doc = _make_si()
        doc.send_invoice_email = MagicMock()
        doc._maybe_auto_send_email()
        doc.send_invoice_email.assert_not_called()

    @patch.object(frappe.db, "get_value", return_value=1)  # auto_send on
    def test_sends_when_auto_send_enabled(self, mock_get_value):
        doc = _make_si()
        doc.send_invoice_email = MagicMock()
        doc._maybe_auto_send_email()
        doc.send_invoice_email.assert_called_once()

    @patch.object(frappe, "log_error")
    @patch.object(frappe.db, "get_value", return_value=1)
    def test_mail_failure_is_logged_not_raised(self, mock_get_value, mock_log_error):
        doc = _make_si()
        doc.send_invoice_email = MagicMock(side_effect=Exception("smtp down"))
        doc._maybe_auto_send_email()  # should not raise
        mock_log_error.assert_called_once()

    @patch.object(frappe.db, "get_value", side_effect=Exception("no such company field"))
    def test_lookup_failure_treated_as_disabled(self, mock_get_value):
        doc = _make_si()
        doc.send_invoice_email = MagicMock()
        doc._maybe_auto_send_email()  # should not raise
        doc.send_invoice_email.assert_not_called()


if __name__ == "__main__":
    unittest.main()