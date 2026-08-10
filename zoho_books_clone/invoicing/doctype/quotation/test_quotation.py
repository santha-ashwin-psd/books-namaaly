# Copyright (c) 2026, PS Digitise and Contributors
# See license.txt
"""
Tests for Quotation (invoicing/doctype/quotation/quotation.py) --
item/tax totals calc and the fiscal-year lock check.

Same bind-real-method-onto-a-stand-in pattern as the other invoicing test
suites -- DB-free, exercises the actual controller code.

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.invoicing.doctype.quotation.test_quotation
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from zoho_books_clone.invoicing.doctype.quotation.quotation import Quotation


class _Dict(SimpleNamespace):
    def get(self, key, default=None):
        return getattr(self, key, default)


def _item(qty=1, rate=100, amount=0):
    return SimpleNamespace(qty=qty, rate=rate, amount=amount)


def _tax(rate=0, tax_amount=0):
    return SimpleNamespace(rate=rate, tax_amount=tax_amount)


def _make_quotation(items=None, taxes=None, company="VK Herbal",
                     transaction_date="2026-08-01", **overrides):
    doc = _Dict(
        doctype="Quotation", name="QTN-2026-00001", items=items or [],
        taxes=taxes or [], company=company, transaction_date=transaction_date,
        fiscal_year=None,
    )
    for k, v in overrides.items():
        setattr(doc, k, v)
    for name in ("validate", "_check_fiscal_lock", "_calculate_totals"):
        setattr(doc, name, getattr(Quotation, name).__get__(doc))
    return doc


class TestCalculateTotals(unittest.TestCase):

    def test_row_amount_and_totals(self):
        row = _item(qty=3, rate=200)
        doc = _make_quotation(items=[row], taxes=[_tax(rate=18)])
        doc._calculate_totals()
        self.assertEqual(row.amount, 600)
        self.assertEqual(doc.net_total, 600)
        self.assertEqual(doc.total_tax, 108)
        self.assertEqual(doc.grand_total, 708)

    def test_multiple_items_summed(self):
        doc = _make_quotation(items=[_item(qty=1, rate=300), _item(qty=2, rate=100)])
        doc._calculate_totals()
        self.assertEqual(doc.net_total, 500)

    def test_existing_nonzero_tax_amount_is_not_recomputed(self):
        tax = _tax(rate=18, tax_amount=999)  # stale from a prior save
        doc = _make_quotation(items=[_item(qty=1, rate=1000)], taxes=[tax])
        doc._calculate_totals()
        self.assertEqual(tax.tax_amount, 999)
        self.assertEqual(doc.total_tax, 999)

    def test_no_items_gives_zero_totals(self):
        doc = _make_quotation(items=[])
        doc._calculate_totals()
        self.assertEqual(doc.net_total, 0)
        self.assertEqual(doc.grand_total, 0)


class TestFiscalLock(unittest.TestCase):

    @patch("zoho_books_clone.invoicing.doctype.quotation.quotation.validate_fiscal_year")
    def test_fiscal_year_set_on_success(self, mock_fy):
        mock_fy.return_value = "2026-2027"
        doc = _make_quotation()
        doc._check_fiscal_lock()
        self.assertEqual(doc.fiscal_year, "2026-2027")

    @patch("zoho_books_clone.invoicing.doctype.quotation.quotation.validate_fiscal_year")
    def test_closed_period_error_is_surfaced(self, mock_fy):
        mock_fy.side_effect = frappe.ValidationError("closed period")
        doc = _make_quotation()
        with self.assertRaises(frappe.ValidationError):
            doc._check_fiscal_lock()

    @patch("zoho_books_clone.invoicing.doctype.quotation.quotation.validate_fiscal_year")
    def test_any_exception_is_surfaced_not_just_validation_error(self, mock_fy):
        # Same pattern as Sales Order's _check_fiscal_lock: `except
        # Exception: raise` re-raises everything unconditionally, unlike
        # Purchase Order / Sales Invoice / Purchase Invoice which swallow
        # only unexpected non-ValidationError exceptions. Characterizing
        # current behavior, not endorsing it.
        mock_fy.side_effect = Exception("some transient lookup failure")
        doc = _make_quotation()
        with self.assertRaises(Exception):
            doc._check_fiscal_lock()

    def test_skipped_without_transaction_date_or_company(self):
        doc = _make_quotation(transaction_date=None, company=None)
        doc._check_fiscal_lock()  # should not raise
        self.assertIsNone(doc.fiscal_year)

    @patch("zoho_books_clone.invoicing.doctype.quotation.quotation.validate_fiscal_year")
    def test_validate_calls_both_steps(self, mock_fy):
        mock_fy.return_value = "2026-2027"
        doc = _make_quotation(items=[_item(qty=2, rate=50)])
        doc.validate()
        self.assertEqual(doc.fiscal_year, "2026-2027")
        self.assertEqual(doc.net_total, 100)


if __name__ == "__main__":
    unittest.main()