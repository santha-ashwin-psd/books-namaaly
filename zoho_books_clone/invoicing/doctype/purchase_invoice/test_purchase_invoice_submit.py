# Copyright (c) 2026, PS Digitise and Contributors
# See license.txt
"""
Tests for Purchase Invoice -- Part 2: on_submit / on_cancel, the debit-note
(is_return) claimable-value guard, and PO ordered/billed qty reversal.

Same bind-real-method-onto-a-stand-in pattern as Part 1
(test_purchase_invoice.py) -- DB-free, exercises the actual controller code.

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.invoicing.doctype.purchase_invoice.test_purchase_invoice_submit
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe

from zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice


class _Dict(SimpleNamespace):
    def get(self, key, default=None):
        return getattr(self, key, default)


def _item(item_code="ITEM-1", qty=5, uom="Nos", warehouse=None):
    return SimpleNamespace(item_code=item_code, qty=qty, uom=uom, warehouse=warehouse)


def _make_pinv(items=None, docstatus=1, company="VK Herbal", is_return=0,
               return_against=None, purchase_order=None, update_stock=0,
               grand_total=1000, outstanding_amount=1000, **overrides):
    doc = _Dict(
        doctype="Purchase Invoice", name="PINV-2026-00001", items=items or [],
        docstatus=docstatus, company=company, is_return=is_return,
        return_against=return_against, purchase_order=purchase_order,
        update_stock=update_stock, grand_total=grand_total,
        outstanding_amount=outstanding_amount, set_warehouse=None,
        due_date=None, status=None,
    )
    doc.db_set = MagicMock()
    for k, v in overrides.items():
        setattr(doc, k, v)
    for name in ("on_submit", "on_cancel", "_release_ordered_qty",
                 "_reverse_billed_qty", "_adjust_source_bill_outstanding"):
        setattr(doc, name, getattr(PurchaseInvoice, name).__get__(doc))
    return doc


class TestOnSubmitNormalInvoice(unittest.TestCase):

    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.post_purchase_invoice")
    def test_sets_outstanding_and_status_submitted(self, mock_post):
        doc = _make_pinv(is_return=0, grand_total=1180)
        doc.on_submit()
        doc.db_set.assert_any_call("outstanding_amount", 1180, update_modified=False)
        doc.db_set.assert_any_call("status", "Submitted", update_modified=False)
        self.assertEqual(doc.outstanding_amount, 1180)
        self.assertEqual(doc.status, "Submitted")
        mock_post.assert_called_once_with(doc)

    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.post_purchase_invoice")
    def test_releases_ordered_qty_when_update_stock_and_po_linked(self, mock_post):
        doc = _make_pinv(is_return=0, update_stock=1, purchase_order="PO-0001")
        released = []
        doc._release_ordered_qty = lambda direction: released.append(direction)
        doc.on_submit()
        self.assertEqual(released, [-1])

    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.post_purchase_invoice")
    def test_no_ordered_qty_release_without_update_stock(self, mock_post):
        doc = _make_pinv(is_return=0, update_stock=0, purchase_order="PO-0001")
        doc._release_ordered_qty = MagicMock()
        doc.on_submit()
        doc._release_ordered_qty.assert_not_called()

    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.post_purchase_invoice")
    def test_no_ordered_qty_release_without_po(self, mock_post):
        doc = _make_pinv(is_return=0, update_stock=1, purchase_order=None)
        doc._release_ordered_qty = MagicMock()
        doc.on_submit()
        doc._release_ordered_qty.assert_not_called()


class TestOnSubmitDebitNote(unittest.TestCase):

    @patch("zoho_books_clone.accounts.accounting_engine.post_debit_note")
    def test_no_return_against_skips_guard_and_posts(self, mock_post_dn):
        doc = _make_pinv(is_return=1, return_against=None, grand_total=-200)
        doc._adjust_source_bill_outstanding = MagicMock()
        doc.on_submit()
        doc.db_set.assert_any_call("outstanding_amount", 0, update_modified=False)
        doc.db_set.assert_any_call("status", "Paid", update_modified=False)
        mock_post_dn.assert_called_once_with(doc)
        doc._adjust_source_bill_outstanding.assert_called_once_with(direction=-1)

    @patch("zoho_books_clone.accounts.accounting_engine.post_debit_note")
    @patch.object(frappe.db, "sql")
    @patch.object(frappe.db, "get_value")
    def test_guard_passes_when_enough_claimable_remains(self, mock_get_value, mock_sql, mock_post_dn):
        mock_get_value.return_value = 1000       # source PINV grand_total
        mock_sql.return_value = [[300]]           # already claimed by other debit notes
        doc = _make_pinv(is_return=1, return_against="PINV-2026-00000", grand_total=-500)
        doc._adjust_source_bill_outstanding = MagicMock()
        doc.on_submit()  # remaining = 1000-300=700 >= 500 -> should not raise
        mock_post_dn.assert_called_once_with(doc)

    @patch("zoho_books_clone.accounts.accounting_engine.post_debit_note")
    @patch.object(frappe.db, "sql")
    @patch.object(frappe.db, "get_value")
    def test_guard_blocks_when_claimable_value_exhausted(self, mock_get_value, mock_sql, mock_post_dn):
        mock_get_value.return_value = 1000
        mock_sql.return_value = [[900]]           # only 100 remaining claimable
        doc = _make_pinv(is_return=1, return_against="PINV-2026-00000", grand_total=-500)
        with self.assertRaises(frappe.ValidationError):
            doc.on_submit()
        mock_post_dn.assert_not_called()

    @patch("zoho_books_clone.accounts.accounting_engine.post_debit_note")
    @patch.object(frappe.db, "sql")
    @patch.object(frappe.db, "get_value")
    def test_guard_uses_abs_grand_total_not_outstanding(self, mock_get_value, mock_sql, mock_post_dn):
        # Fully paid source bill (outstanding=0) must still allow a debit
        # note as long as claimable value remains -- guard must be based on
        # grand_total minus already-claimed, not on outstanding_amount.
        mock_get_value.return_value = 1000
        mock_sql.return_value = [[0]]
        doc = _make_pinv(is_return=1, return_against="PINV-2026-00000", grand_total=-1000)
        doc._adjust_source_bill_outstanding = MagicMock()
        doc.on_submit()  # should not raise -- full 1000 still claimable
        mock_post_dn.assert_called_once()


class TestOnCancel(unittest.TestCase):

    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.reverse_voucher")
    def test_sets_cancelled_status_and_reverses_gl(self, mock_reverse):
        doc = _make_pinv(is_return=0, purchase_order=None)
        doc.on_cancel()
        self.assertEqual(doc.status, "Cancelled")
        self.assertEqual(doc.outstanding_amount, 0)
        mock_reverse.assert_called_once_with("Purchase Invoice", doc.name)

    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.reverse_voucher")
    def test_debit_note_cancel_restores_source_bill_outstanding(self, mock_reverse):
        doc = _make_pinv(is_return=1, return_against="PINV-2026-00000")
        doc._adjust_source_bill_outstanding = MagicMock()
        doc.on_cancel()
        doc._adjust_source_bill_outstanding.assert_called_once_with(direction=+1)

    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.reverse_voucher")
    def test_normal_cancel_with_po_and_update_stock_releases_and_reverses(self, mock_reverse):
        doc = _make_pinv(is_return=0, purchase_order="PO-0001", update_stock=1)
        doc._release_ordered_qty = MagicMock()
        doc._reverse_billed_qty = MagicMock()
        doc.on_cancel()
        doc._release_ordered_qty.assert_called_once_with(direction=+1)
        doc._reverse_billed_qty.assert_called_once()

    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.reverse_voucher")
    def test_normal_cancel_without_update_stock_only_reverses_billed_qty(self, mock_reverse):
        doc = _make_pinv(is_return=0, purchase_order="PO-0001", update_stock=0)
        doc._release_ordered_qty = MagicMock()
        doc._reverse_billed_qty = MagicMock()
        doc.on_cancel()
        doc._release_ordered_qty.assert_not_called()
        doc._reverse_billed_qty.assert_called_once()

    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.reverse_voucher")
    def test_normal_cancel_without_po_touches_nothing_po_related(self, mock_reverse):
        doc = _make_pinv(is_return=0, purchase_order=None, update_stock=1)
        doc._release_ordered_qty = MagicMock()
        doc._reverse_billed_qty = MagicMock()
        doc.on_cancel()
        doc._release_ordered_qty.assert_not_called()
        doc._reverse_billed_qty.assert_not_called()


class TestReleaseOrderedQty(unittest.TestCase):

    @patch("zoho_books_clone.inventory.utils.update_bin")
    @patch("zoho_books_clone.inventory.utils.get_conversion_factor", return_value=10)
    @patch.object(frappe.db, "get_value", return_value=1)  # is_stock_item = True
    def test_releases_stock_uom_equivalent_qty(self, mock_get_value, mock_factor, mock_update_bin):
        row = _item(item_code="ITEM-1", qty=3, uom="Box", warehouse="WH-1")
        doc = _make_pinv(items=[row], company="VK Herbal")
        doc._release_ordered_qty(direction=-1)
        mock_update_bin.assert_called_once_with(
            item_code="ITEM-1", warehouse="WH-1",
            ordered_qty_delta=-30,  # 3 * conversion factor 10
            company="VK Herbal",
        )

    @patch("zoho_books_clone.inventory.utils.update_bin")
    @patch.object(frappe.db, "get_value", return_value=0)  # not a stock item
    def test_skips_non_stock_items(self, mock_get_value, mock_update_bin):
        row = _item(item_code="SERVICE-1", qty=3, warehouse="WH-1")
        doc = _make_pinv(items=[row])
        doc._release_ordered_qty(direction=-1)
        mock_update_bin.assert_not_called()

    @patch("zoho_books_clone.inventory.utils.update_bin")
    def test_skips_zero_or_negative_qty_rows(self, mock_update_bin):
        row = _item(item_code="ITEM-1", qty=0, warehouse="WH-1")
        doc = _make_pinv(items=[row])
        doc._release_ordered_qty(direction=-1)
        mock_update_bin.assert_not_called()

    @patch("zoho_books_clone.inventory.utils.update_bin")
    def test_skips_rows_without_warehouse(self, mock_update_bin):
        row = _item(item_code="ITEM-1", qty=5, warehouse=None)
        doc = _make_pinv(items=[row], set_warehouse=None)
        doc._release_ordered_qty(direction=-1)
        mock_update_bin.assert_not_called()

    @patch("zoho_books_clone.inventory.utils.update_bin")
    @patch("zoho_books_clone.inventory.utils.get_conversion_factor", return_value=1)
    @patch.object(frappe.db, "get_value", return_value=1)
    def test_falls_back_to_header_set_warehouse(self, mock_get_value, mock_factor, mock_update_bin):
        row = _item(item_code="ITEM-1", qty=5, warehouse=None)
        doc = _make_pinv(items=[row], set_warehouse="WH-DEFAULT")
        doc._release_ordered_qty(direction=1)
        mock_update_bin.assert_called_once_with(
            item_code="ITEM-1", warehouse="WH-DEFAULT",
            ordered_qty_delta=5, company="VK Herbal",
        )


class TestReverseBilledQty(unittest.TestCase):

    @patch("zoho_books_clone.api.docs._po_status_from_fulfillment", return_value="To Bill")
    @patch.object(frappe.db, "set_value")
    @patch.object(frappe.db, "sql")
    def test_decrements_billed_qty_on_matching_po_rows_in_order(self, mock_sql, mock_set_value, mock_status):
        row = _item(item_code="ITEM-1", qty=8)
        doc = _make_pinv(items=[row], purchase_order="PO-0001")
        mock_sql.return_value = [
            frappe._dict({"name": "POI-1", "billed_qty": 5}),
            frappe._dict({"name": "POI-2", "billed_qty": 6}),
        ]
        doc._reverse_billed_qty()

        mock_set_value.assert_any_call("Purchase Order Item", "POI-1", "billed_qty", 0.0, update_modified=False)
        mock_set_value.assert_any_call("Purchase Order Item", "POI-2", "billed_qty", 3, update_modified=False)
        mock_status.assert_called_once_with("PO-0001")

    @patch("zoho_books_clone.api.docs._po_status_from_fulfillment", return_value="Billed")
    @patch.object(frappe.db, "set_value")
    @patch.object(frappe.db, "sql")
    def test_clamps_at_zero_never_goes_negative(self, mock_sql, mock_set_value, mock_status):
        row = _item(item_code="ITEM-1", qty=100)
        doc = _make_pinv(items=[row], purchase_order="PO-0001")
        mock_sql.return_value = [frappe._dict({"name": "POI-1", "billed_qty": 5})]
        doc._reverse_billed_qty()
        mock_set_value.assert_any_call("Purchase Order Item", "POI-1", "billed_qty", 0.0, update_modified=False)

    @patch("zoho_books_clone.api.docs._po_status_from_fulfillment", side_effect=Exception("boom"))
    @patch.object(frappe.db, "set_value")
    @patch.object(frappe.db, "sql")
    def test_status_refresh_failure_does_not_raise(self, mock_sql, mock_set_value, mock_status):
        row = _item(item_code="ITEM-1", qty=5)
        doc = _make_pinv(items=[row], purchase_order="PO-0001")
        mock_sql.return_value = [frappe._dict({"name": "POI-1", "billed_qty": 5})]
        doc._reverse_billed_qty()  # should not raise


class TestAdjustSourceBillOutstanding(unittest.TestCase):

    @patch.object(frappe.db, "get_value")
    def test_noop_without_return_against(self, mock_get_value):
        doc = _make_pinv(return_against=None)
        doc._adjust_source_bill_outstanding(direction=-1)
        mock_get_value.assert_not_called()

    @patch.object(frappe.db, "get_value", return_value=None)
    def test_noop_when_source_bill_missing(self, mock_get_value):
        doc = _make_pinv(return_against="PINV-GONE")
        doc._adjust_source_bill_outstanding(direction=-1)  # should not raise

    @patch.object(frappe.db, "set_value")
    @patch.object(frappe.db, "get_value")
    def test_reduces_outstanding_and_marks_paid(self, mock_get_value, mock_set_value):
        mock_get_value.return_value = SimpleNamespace(
            outstanding_amount=1000, grand_total=1000, due_date=None, docstatus=1
        )
        doc = _make_pinv(return_against="PINV-SRC", grand_total=-1000)
        doc._adjust_source_bill_outstanding(direction=-1)
        mock_set_value.assert_called_once_with(
            "Purchase Invoice", "PINV-SRC",
            {"outstanding_amount": 0.0, "status": "Paid"},
            update_modified=False,
        )

    @patch.object(frappe.db, "set_value")
    @patch.object(frappe.db, "get_value")
    def test_restores_outstanding_on_cancel_reversal(self, mock_get_value, mock_set_value):
        mock_get_value.return_value = SimpleNamespace(
            outstanding_amount=0, grand_total=1000, due_date=None, docstatus=1
        )
        doc = _make_pinv(return_against="PINV-SRC", grand_total=-300)
        doc._adjust_source_bill_outstanding(direction=+1)
        mock_set_value.assert_called_once_with(
            "Purchase Invoice", "PINV-SRC",
            {"outstanding_amount": 300, "status": "Partly Paid"},
            update_modified=False,
        )

    @patch.object(frappe.db, "set_value")
    @patch.object(frappe.db, "get_value")
    def test_never_goes_negative(self, mock_get_value, mock_set_value):
        mock_get_value.return_value = SimpleNamespace(
            outstanding_amount=100, grand_total=1000, due_date=None, docstatus=1
        )
        doc = _make_pinv(return_against="PINV-SRC", grand_total=-500)
        doc._adjust_source_bill_outstanding(direction=-1)
        mock_set_value.assert_called_once_with(
            "Purchase Invoice", "PINV-SRC",
            {"outstanding_amount": 0.0, "status": "Paid"},
            update_modified=False,
        )

    @patch.object(frappe.db, "set_value")
    @patch.object(frappe.db, "get_value")
    def test_cancelled_source_bill_status_stays_cancelled(self, mock_get_value, mock_set_value):
        mock_get_value.return_value = SimpleNamespace(
            outstanding_amount=1000, grand_total=1000, due_date=None, docstatus=2
        )
        doc = _make_pinv(return_against="PINV-SRC", grand_total=-200)
        doc._adjust_source_bill_outstanding(direction=-1)
        mock_set_value.assert_called_once_with(
            "Purchase Invoice", "PINV-SRC",
            {"outstanding_amount": 800, "status": "Cancelled"},
            update_modified=False,
        )


if __name__ == "__main__":
    unittest.main()