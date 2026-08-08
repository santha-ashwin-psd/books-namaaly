# Copyright (c) 2026, PS Digitise and Contributors
# See license.txt
"""
Tests for Sales Order (invoicing/doctype/sales_order/sales_order.py) --
validate() (item/discount calc, totals, fiscal year lock), on_submit/
on_cancel (_update_reserved_qty: Bin reserved_qty tracking, with the
cancel-path "only release what's still reserved, not yet billed" guard).

Same bind-real-method-onto-a-stand-in pattern as the other invoicing test
suites -- DB-free, exercises the actual controller code.

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.invoicing.doctype.sales_order.test_sales_order
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from zoho_books_clone.invoicing.doctype.sales_order.sales_order import SalesOrder


class _Dict(SimpleNamespace):
    def get(self, key, default=None):
        return getattr(self, key, default)


def _item(item_code="ITEM-1", qty=1, rate=100, discount_percentage=0,
          discount_amount=0, amount=0, warehouse=None, billed_qty=0):
    return SimpleNamespace(item_code=item_code, qty=qty, rate=rate,
                            discount_percentage=discount_percentage,
                            discount_amount=discount_amount, amount=amount,
                            warehouse=warehouse, billed_qty=billed_qty)


def _tax(rate=0, tax_amount=0):
    return SimpleNamespace(rate=rate, tax_amount=tax_amount)


def _make_so(items=None, taxes=None, company="VK Herbal",
             transaction_date="2026-08-01", **overrides):
    doc = _Dict(
        doctype="Sales Order", name="SO-2026-00001", items=items or [],
        taxes=taxes or [], company=company, transaction_date=transaction_date,
        fiscal_year=None, set_warehouse=None,
    )
    for k, v in overrides.items():
        setattr(doc, k, v)
    for name in ("validate", "_check_fiscal_lock", "_calculate_totals",
                 "on_submit", "on_cancel", "_update_reserved_qty"):
        setattr(doc, name, getattr(SalesOrder, name).__get__(doc))
    return doc


class TestCalculateTotals(unittest.TestCase):

    def test_row_amount_is_qty_times_rate_minus_discount(self):
        row = _item(qty=2, rate=150, discount_percentage=10)
        doc = _make_so(items=[row])
        doc._calculate_totals()
        # base = 300, discount_amount = 30, amount = 270
        self.assertEqual(row.discount_amount, 30)
        self.assertEqual(row.amount, 270)

    def test_flat_discount_amount_used_when_no_percentage(self):
        row = _item(qty=1, rate=500, discount_percentage=0, discount_amount=50)
        doc = _make_so(items=[row])
        doc._calculate_totals()
        self.assertEqual(row.amount, 450)

    def test_net_tax_and_grand_total(self):
        doc = _make_so(items=[_item(qty=1, rate=1000)], taxes=[_tax(rate=18)])
        doc._calculate_totals()
        self.assertEqual(doc.net_total, 1000)
        self.assertEqual(doc.total_tax, 180)
        self.assertEqual(doc.grand_total, 1180)

    def test_existing_nonzero_tax_amount_is_not_recomputed(self):
        tax = _tax(rate=18, tax_amount=999)
        doc = _make_so(items=[_item(qty=1, rate=1000)], taxes=[tax])
        doc._calculate_totals()
        self.assertEqual(tax.tax_amount, 999)

    def test_no_items_gives_zero_totals(self):
        doc = _make_so(items=[])
        doc._calculate_totals()
        self.assertEqual(doc.net_total, 0)
        self.assertEqual(doc.grand_total, 0)


class TestFiscalLock(unittest.TestCase):

    @patch("zoho_books_clone.invoicing.doctype.sales_order.sales_order.validate_fiscal_year")
    def test_fiscal_year_set_on_success(self, mock_fy):
        mock_fy.return_value = "2026-2027"
        doc = _make_so()
        doc._check_fiscal_lock()
        self.assertEqual(doc.fiscal_year, "2026-2027")

    @patch("zoho_books_clone.invoicing.doctype.sales_order.sales_order.validate_fiscal_year")
    def test_closed_period_error_is_surfaced(self, mock_fy):
        mock_fy.side_effect = frappe.ValidationError("closed period")
        doc = _make_so()
        with self.assertRaises(frappe.ValidationError):
            doc._check_fiscal_lock()

    @patch("zoho_books_clone.invoicing.doctype.sales_order.sales_order.validate_fiscal_year")
    def test_any_exception_is_surfaced_not_just_validation_error(self, mock_fy):
        # NOTE: unlike Purchase Order / Sales Invoice / Purchase Invoice
        # (which swallow only unexpected non-ValidationError exceptions),
        # Sales Order's `except Exception: raise` re-raises everything
        # unconditionally. The docstring/comment ("ignore only missing FY
        # on draft") does not match this code -- nothing is actually
        # ignored here. Characterizing current behavior, not endorsing it.
        mock_fy.side_effect = Exception("some transient lookup failure")
        doc = _make_so()
        with self.assertRaises(Exception):
            doc._check_fiscal_lock()

    def test_skipped_without_transaction_date_or_company(self):
        doc = _make_so(transaction_date=None, company=None)
        doc._check_fiscal_lock()  # should not raise
        self.assertIsNone(doc.fiscal_year)


class TestOnSubmitOnCancel(unittest.TestCase):

    def test_on_submit_calls_update_reserved_qty_positive(self):
        doc = _make_so()
        calls = []
        doc._update_reserved_qty = lambda direction: calls.append(direction)
        doc.on_submit()
        self.assertEqual(calls, [1])

    def test_on_cancel_calls_update_reserved_qty_negative(self):
        doc = _make_so()
        calls = []
        doc._update_reserved_qty = lambda direction: calls.append(direction)
        doc.on_cancel()
        self.assertEqual(calls, [-1])


class TestUpdateReservedQty(unittest.TestCase):

    @patch("zoho_books_clone.inventory.utils.update_bin")
    @patch.object(frappe.db, "get_value", return_value=1)  # is_stock_item
    def test_submit_reserves_full_row_qty(self, mock_get_value, mock_update_bin):
        row = _item(item_code="ITEM-1", qty=7, warehouse="WH-1")
        doc = _make_so(items=[row], company="VK Herbal")
        doc._update_reserved_qty(direction=1)
        mock_update_bin.assert_called_once_with(
            item_code="ITEM-1", warehouse="WH-1",
            reserved_qty_delta=7, company="VK Herbal",
        )

    @patch("zoho_books_clone.inventory.utils.update_bin")
    @patch.object(frappe.db, "get_value", return_value=0)  # not a stock item
    def test_skips_non_stock_items(self, mock_get_value, mock_update_bin):
        row = _item(item_code="SERVICE-1", qty=3, warehouse="WH-1")
        doc = _make_so(items=[row])
        doc._update_reserved_qty(direction=1)
        mock_update_bin.assert_not_called()

    @patch("zoho_books_clone.inventory.utils.update_bin")
    def test_skips_rows_without_warehouse(self, mock_update_bin):
        row = _item(item_code="ITEM-1", qty=5, warehouse=None)
        doc = _make_so(items=[row], set_warehouse=None)
        doc._update_reserved_qty(direction=1)
        mock_update_bin.assert_not_called()

    @patch("zoho_books_clone.inventory.utils.update_bin")
    @patch.object(frappe.db, "get_value", return_value=1)
    def test_falls_back_to_header_set_warehouse(self, mock_get_value, mock_update_bin):
        row = _item(item_code="ITEM-1", qty=5, warehouse=None)
        doc = _make_so(items=[row], set_warehouse="WH-DEFAULT")
        doc._update_reserved_qty(direction=1)
        mock_update_bin.assert_called_once_with(
            item_code="ITEM-1", warehouse="WH-DEFAULT",
            reserved_qty_delta=5, company="VK Herbal",
        )

    @patch("zoho_books_clone.inventory.utils.update_bin")
    @patch.object(frappe.db, "get_value", return_value=1)
    def test_cancel_releases_only_unbilled_remainder(self, mock_get_value, mock_update_bin):
        # Ordered 10, 4 already invoiced (already released by
        # SalesInvoice._release_reserved_qty on that SI's submit) --
        # cancelling the SO must release only the remaining 6.
        row = _item(item_code="ITEM-1", qty=10, warehouse="WH-1", billed_qty=4)
        doc = _make_so(items=[row])
        doc._update_reserved_qty(direction=-1)
        mock_update_bin.assert_called_once_with(
            item_code="ITEM-1", warehouse="WH-1",
            reserved_qty_delta=-6, company="VK Herbal",
        )

    @patch("zoho_books_clone.inventory.utils.update_bin")
    @patch.object(frappe.db, "get_value", return_value=1)
    def test_cancel_skips_fully_billed_row(self, mock_get_value, mock_update_bin):
        row = _item(item_code="ITEM-1", qty=10, warehouse="WH-1", billed_qty=10)
        doc = _make_so(items=[row])
        doc._update_reserved_qty(direction=-1)
        mock_update_bin.assert_not_called()

    @patch("zoho_books_clone.inventory.utils.update_bin")
    @patch.object(frappe.db, "get_value", return_value=1)
    def test_cancel_clamps_when_overbilled(self, mock_get_value, mock_update_bin):
        row = _item(item_code="ITEM-1", qty=5, warehouse="WH-1", billed_qty=8)
        doc = _make_so(items=[row])
        doc._update_reserved_qty(direction=-1)
        mock_update_bin.assert_not_called()


if __name__ == "__main__":
    unittest.main()