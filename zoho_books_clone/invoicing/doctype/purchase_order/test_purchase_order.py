# Copyright (c) 2026, PS Digitise and Contributors
# See license.txt
"""
Tests for Purchase Order (invoicing/doctype/purchase_order/purchase_order.py)
-- validate() (totals calc, fiscal year handling), on_submit/on_cancel
(_update_ordered_qty: Bin ordered_qty tracking in stock UOM, with the
cancel-path "only release what's still on-order, not yet billed" guard).

Same bind-real-method-onto-a-stand-in pattern as the other invoicing test
suites -- DB-free, exercises the actual controller code.

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.invoicing.doctype.purchase_order.test_purchase_order
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from zoho_books_clone.invoicing.doctype.purchase_order.purchase_order import PurchaseOrder


class _Dict(SimpleNamespace):
    def get(self, key, default=None):
        return getattr(self, key, default)


def _item(item_code="ITEM-1", qty=1, rate=100, amount=0, uom="Nos",
          warehouse=None, billed_qty=0):
    return SimpleNamespace(item_code=item_code, qty=qty, rate=rate, amount=amount,
                            uom=uom, warehouse=warehouse, billed_qty=billed_qty)


def _tax(rate=0, tax_amount=0):
    return SimpleNamespace(rate=rate, tax_amount=tax_amount)


def _make_po(items=None, taxes=None, company="VK Herbal",
             transaction_date="2026-08-01", **overrides):
    doc = _Dict(
        doctype="Purchase Order", name="PO-2026-00001", items=items or [],
        taxes=taxes or [], company=company, transaction_date=transaction_date,
        fiscal_year=None, set_warehouse=None,
    )
    for k, v in overrides.items():
        setattr(doc, k, v)
    for name in ("validate", "_calculate_totals", "on_submit", "on_cancel",
                 "_update_ordered_qty"):
        setattr(doc, name, getattr(PurchaseOrder, name).__get__(doc))
    return doc


class TestCalculateTotals(unittest.TestCase):

    def test_row_amount_and_totals(self):
        row = _item(qty=3, rate=200)
        doc = _make_po(items=[row], taxes=[_tax(rate=18)])
        doc._calculate_totals()
        self.assertEqual(row.amount, 600)
        self.assertEqual(doc.net_total, 600)
        self.assertEqual(doc.total_tax, 108)
        self.assertEqual(doc.grand_total, 708)

    def test_multiple_items_summed(self):
        doc = _make_po(items=[_item(qty=1, rate=300), _item(qty=2, rate=100)])
        doc._calculate_totals()
        self.assertEqual(doc.net_total, 500)

    def test_existing_nonzero_tax_amount_is_not_recomputed(self):
        tax = _tax(rate=18, tax_amount=999)  # stale
        doc = _make_po(items=[_item(qty=1, rate=1000)], taxes=[tax])
        doc._calculate_totals()
        self.assertEqual(tax.tax_amount, 999)
        self.assertEqual(doc.total_tax, 999)

    def test_no_items_gives_zero_totals(self):
        doc = _make_po(items=[])
        doc._calculate_totals()
        self.assertEqual(doc.net_total, 0)
        self.assertEqual(doc.grand_total, 0)


class TestValidateFiscalYearHandling(unittest.TestCase):

    @patch("zoho_books_clone.invoicing.doctype.purchase_order.purchase_order.validate_fiscal_year")
    def test_fiscal_year_set_on_success(self, mock_fy):
        mock_fy.return_value = "2026-2027"
        doc = _make_po(items=[_item(amount=100)])
        doc.validate()
        self.assertEqual(doc.fiscal_year, "2026-2027")

    @patch("zoho_books_clone.invoicing.doctype.purchase_order.purchase_order.validate_fiscal_year")
    def test_closed_period_error_is_surfaced(self, mock_fy):
        mock_fy.side_effect = frappe.ValidationError("closed period")
        doc = _make_po(items=[_item(amount=100)])
        with self.assertRaises(frappe.ValidationError):
            doc.validate()

    @patch("zoho_books_clone.invoicing.doctype.purchase_order.purchase_order.validate_fiscal_year")
    def test_fiscal_year_blanked_on_unexpected_error(self, mock_fy):
        mock_fy.side_effect = Exception("unexpected")
        doc = _make_po(items=[_item(amount=100)])
        doc.validate()  # should not raise
        self.assertEqual(doc.fiscal_year, "")

    def test_totals_still_calculated_without_company_or_date(self):
        doc = _make_po(items=[_item(qty=2, rate=50)], company=None, transaction_date=None)
        doc.validate()  # fiscal_year block skipped, but totals must still run
        self.assertEqual(doc.net_total, 100)


class TestOnSubmitOnCancel(unittest.TestCase):

    def test_on_submit_calls_update_ordered_qty_positive(self):
        doc = _make_po()
        calls = []
        doc._update_ordered_qty = lambda direction: calls.append(direction)
        doc.on_submit()
        self.assertEqual(calls, [1])

    def test_on_cancel_calls_update_ordered_qty_negative(self):
        doc = _make_po()
        calls = []
        doc._update_ordered_qty = lambda direction: calls.append(direction)
        doc.on_cancel()
        self.assertEqual(calls, [-1])


class TestUpdateOrderedQty(unittest.TestCase):

    @patch("zoho_books_clone.inventory.utils.update_bin")
    @patch("zoho_books_clone.inventory.utils.get_conversion_factor", return_value=10)
    @patch.object(frappe.db, "get_value", return_value=1)  # is_stock_item
    def test_submit_adds_stock_uom_equivalent_qty(self, mock_get_value, mock_factor, mock_update_bin):
        row = _item(item_code="ITEM-1", qty=3, uom="Box", warehouse="WH-1")
        doc = _make_po(items=[row], company="VK Herbal")
        doc._update_ordered_qty(direction=1)
        mock_update_bin.assert_called_once_with(
            item_code="ITEM-1", warehouse="WH-1",
            ordered_qty_delta=30,  # 3 * conversion factor 10
            company="VK Herbal",
        )

    @patch("zoho_books_clone.inventory.utils.update_bin")
    @patch.object(frappe.db, "get_value", return_value=0)  # not a stock item
    def test_skips_non_stock_items(self, mock_get_value, mock_update_bin):
        row = _item(item_code="SERVICE-1", qty=3, warehouse="WH-1")
        doc = _make_po(items=[row])
        doc._update_ordered_qty(direction=1)
        mock_update_bin.assert_not_called()

    @patch("zoho_books_clone.inventory.utils.update_bin")
    def test_skips_rows_without_warehouse(self, mock_update_bin):
        row = _item(item_code="ITEM-1", qty=5, warehouse=None)
        doc = _make_po(items=[row], set_warehouse=None)
        doc._update_ordered_qty(direction=1)
        mock_update_bin.assert_not_called()

    @patch("zoho_books_clone.inventory.utils.update_bin")
    @patch("zoho_books_clone.inventory.utils.get_conversion_factor", return_value=1)
    @patch.object(frappe.db, "get_value", return_value=1)
    def test_falls_back_to_header_set_warehouse(self, mock_get_value, mock_factor, mock_update_bin):
        row = _item(item_code="ITEM-1", qty=5, warehouse=None)
        doc = _make_po(items=[row], set_warehouse="WH-DEFAULT")
        doc._update_ordered_qty(direction=1)
        mock_update_bin.assert_called_once_with(
            item_code="ITEM-1", warehouse="WH-DEFAULT",
            ordered_qty_delta=5, company="VK Herbal",
        )

    @patch("zoho_books_clone.inventory.utils.update_bin")
    @patch("zoho_books_clone.inventory.utils.get_conversion_factor", return_value=1)
    @patch.object(frappe.db, "get_value", return_value=1)
    def test_cancel_releases_only_unbilled_remainder(self, mock_get_value, mock_factor, mock_update_bin):
        # Ordered 10, 4 already billed (and already released by
        # PurchaseInvoice._release_ordered_qty on that PI's submit) --
        # cancelling the PO must release only the remaining 6, not all 10.
        row = _item(item_code="ITEM-1", qty=10, warehouse="WH-1", billed_qty=4)
        doc = _make_po(items=[row])
        doc._update_ordered_qty(direction=-1)
        mock_update_bin.assert_called_once_with(
            item_code="ITEM-1", warehouse="WH-1",
            ordered_qty_delta=-6, company="VK Herbal",
        )

    @patch("zoho_books_clone.inventory.utils.update_bin")
    @patch("zoho_books_clone.inventory.utils.get_conversion_factor", return_value=1)
    @patch.object(frappe.db, "get_value", return_value=1)
    def test_cancel_skips_fully_billed_row(self, mock_get_value, mock_factor, mock_update_bin):
        row = _item(item_code="ITEM-1", qty=10, warehouse="WH-1", billed_qty=10)
        doc = _make_po(items=[row])
        doc._update_ordered_qty(direction=-1)
        mock_update_bin.assert_not_called()

    @patch("zoho_books_clone.inventory.utils.update_bin")
    @patch("zoho_books_clone.inventory.utils.get_conversion_factor", return_value=1)
    @patch.object(frappe.db, "get_value", return_value=1)
    def test_cancel_clamps_when_overbilled(self, mock_get_value, mock_factor, mock_update_bin):
        # Defensive: billed_qty somehow exceeding ordered qty must not flip
        # the release delta positive.
        row = _item(item_code="ITEM-1", qty=5, warehouse="WH-1", billed_qty=8)
        doc = _make_po(items=[row])
        doc._update_ordered_qty(direction=-1)
        mock_update_bin.assert_not_called()


if __name__ == "__main__":
    unittest.main()