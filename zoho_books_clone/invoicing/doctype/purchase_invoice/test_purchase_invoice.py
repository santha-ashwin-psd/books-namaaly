# Copyright (c) 2026, PS Digitise and Contributors
# See license.txt
"""
Tests for Purchase Invoice (invoicing/doctype/purchase_invoice/purchase_invoice.py)
-- Part 1: the validate() pipeline (item/discount/tax calc, totals + round-off,
outstanding amount, account-type checks, status derivation).

Same bind-real-method-onto-a-stand-in pattern as the Stock Entry test suite --
DB-free, exercises the actual controller code, not a reimplementation of it.

Part 2 (on_submit/on_cancel: GL posting, debit notes, PO qty reversal) is a
separate file.

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.invoicing.doctype.purchase_invoice.test_purchase_invoice
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice


class _Dict(SimpleNamespace):
    """SimpleNamespace with a .get() so set_posting_time(doc.get(...)) works."""
    def get(self, key, default=None):
        return getattr(self, key, default)


def _item(qty=1, rate=100, discount_percentage=0, discount_amount=0, amount=0):
    return SimpleNamespace(qty=qty, rate=rate, discount_percentage=discount_percentage,
                            discount_amount=discount_amount, amount=amount)


def _tax(rate=0, tax_amount=0):
    return SimpleNamespace(rate=rate, tax_amount=tax_amount)


def _make_pinv(items=None, taxes=None, docstatus=0, company="VK Herbal",
               posting_date="2026-08-01", **overrides):
    doc = _Dict(
        doctype="Purchase Invoice", name="PINV-2026-00001", items=items or [],
        taxes=taxes or [], docstatus=docstatus, company=company,
        posting_date=posting_date, set_posting_time=0, posting_time=None,
        discount_type=None, additional_discount_percentage=0,
        additional_discount_amount=0, credit_to=None, expense_account=None,
        due_date=None, is_return=0, return_against=None, purchase_order=None,
        update_stock=0, fiscal_year=None,
    )
    for k, v in overrides.items():
        setattr(doc, k, v)
    for name in ("validate", "calculate_totals", "calculate_discount",
                 "set_outstanding_amount", "validate_accounts", "set_status"):
        setattr(doc, name, getattr(PurchaseInvoice, name).__get__(doc))
    return doc


class TestItemAndDiscountCalc(unittest.TestCase):

    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.validate_fiscal_year")
    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.validate_account_type")
    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.validate_account_company")
    def test_row_amount_is_qty_times_rate_minus_discount(self, mock_company, mock_type, mock_fy):
        mock_fy.return_value = "2026-2027"
        row = _item(qty=2, rate=150, discount_percentage=10)
        doc = _make_pinv(items=[row])
        doc.validate()
        # base = 300, discount_amount = 30, amount = 270
        self.assertEqual(row.discount_amount, 30)
        self.assertEqual(row.amount, 270)

    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.validate_fiscal_year")
    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.validate_account_type")
    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.validate_account_company")
    def test_flat_discount_amount_used_when_no_percentage(self, mock_company, mock_type, mock_fy):
        mock_fy.return_value = "2026-2027"
        row = _item(qty=1, rate=500, discount_percentage=0, discount_amount=50)
        doc = _make_pinv(items=[row])
        doc.validate()
        self.assertEqual(row.discount_amount, 50)
        self.assertEqual(row.amount, 450)

    def test_validate_throws_when_no_items(self):
        doc = _make_pinv(items=[])
        with self.assertRaises(frappe.ValidationError):
            doc.validate()


class TestCalculateDiscount(unittest.TestCase):

    def test_percentage_discount_derives_amount_from_subtotal(self):
        doc = _make_pinv(discount_type="Percentage", additional_discount_percentage=10)
        doc.calculate_discount(1000)
        self.assertEqual(doc.additional_discount_amount, 100)

    def test_amount_mode_takes_entered_value(self):
        doc = _make_pinv(discount_type="Amount", additional_discount_amount=75)
        doc.calculate_discount(1000)
        self.assertEqual(doc.additional_discount_amount, 75)
        self.assertEqual(doc.additional_discount_percentage, 0)

    def test_discount_clamped_to_subtotal(self):
        doc = _make_pinv(discount_type="Amount", additional_discount_amount=5000)
        doc.calculate_discount(1000)
        self.assertEqual(doc.additional_discount_amount, 1000)

    def test_discount_never_negative(self):
        doc = _make_pinv(discount_type="Amount", additional_discount_amount=-50)
        doc.calculate_discount(1000)
        self.assertEqual(doc.additional_discount_amount, 0)

    def test_defaults_to_percentage_mode_when_unset(self):
        doc = _make_pinv(discount_type=None, additional_discount_percentage=5)
        doc.calculate_discount(1000)
        self.assertEqual(doc.discount_type, "Percentage")
        self.assertEqual(doc.additional_discount_amount, 50)


class TestCalculateTotals(unittest.TestCase):

    def test_net_total_tax_and_grand_total(self):
        doc = _make_pinv(
            items=[_item(amount=1000)],
            taxes=[_tax(rate=18)],
        )
        doc.calculate_totals()
        self.assertEqual(doc.net_total, 1000)
        self.assertEqual(doc.total_tax, 180)
        self.assertEqual(doc.grand_total, 1180)
        self.assertEqual(doc.round_off, 0)

    def test_round_off_captures_paise_remainder(self):
        doc = _make_pinv(
            items=[_item(amount=333.33)],
            taxes=[_tax(rate=18)],
        )
        doc.calculate_totals()
        pre_round = 333.33 + round(333.33 * 0.18, 2)
        self.assertEqual(doc.grand_total, round(pre_round))
        self.assertAlmostEqual(doc.round_off, round(doc.grand_total - pre_round, 2))

    def test_additional_discount_reduces_net_before_tax(self):
        doc = _make_pinv(
            items=[_item(amount=1000)],
            taxes=[_tax(rate=10)],
            discount_type="Amount", additional_discount_amount=100,
        )
        doc.calculate_totals()
        # net = 1000 - 100 = 900; tax = 90
        self.assertEqual(doc.net_total, 900)
        self.assertEqual(doc.total_tax, 90)
        self.assertEqual(doc.grand_total, 990)

    def test_zero_rate_tax_rows_are_not_recomputed(self):
        tax = _tax(rate=0, tax_amount=999)  # stale value, should be left alone
        doc = _make_pinv(items=[_item(amount=500)], taxes=[tax])
        doc.calculate_totals()
        self.assertEqual(tax.tax_amount, 999)
        self.assertEqual(doc.total_tax, 999)


class TestSetOutstandingAmount(unittest.TestCase):

    def test_sets_outstanding_when_draft(self):
        doc = _make_pinv(docstatus=0, grand_total=1500)
        doc.set_outstanding_amount()
        self.assertEqual(doc.outstanding_amount, 1500)

    def test_does_not_touch_outstanding_when_submitted(self):
        doc = _make_pinv(docstatus=1, grand_total=1500, outstanding_amount=200)
        doc.set_outstanding_amount()
        self.assertEqual(doc.outstanding_amount, 200)


class TestValidateAccounts(unittest.TestCase):

    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.validate_account_type")
    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.validate_account_company")
    def test_credit_to_checked_for_payable_type(self, mock_company, mock_type):
        doc = _make_pinv(credit_to="Creditors - VK", expense_account=None)
        doc.validate_accounts()
        mock_company.assert_called_once_with("Creditors - VK", "VK Herbal")
        mock_type.assert_called_once_with("Creditors - VK", ["Payable"])

    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.validate_account_type")
    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.validate_account_company")
    def test_expense_account_checked_for_expense_or_cogs_type(self, mock_company, mock_type):
        doc = _make_pinv(credit_to=None, expense_account="Repairs - VK")
        doc.validate_accounts()
        mock_type.assert_called_once_with("Repairs - VK", ["Expense", "Cost of Goods Sold"])

    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.validate_account_type")
    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.validate_account_company")
    def test_no_accounts_set_is_a_noop(self, mock_company, mock_type):
        doc = _make_pinv(credit_to=None, expense_account=None)
        doc.validate_accounts()  # should not raise
        mock_company.assert_not_called()
        mock_type.assert_not_called()


class TestSetStatus(unittest.TestCase):

    def test_draft(self):
        doc = _make_pinv(docstatus=0)
        doc.set_status()
        self.assertEqual(doc.status, "Draft")

    def test_cancelled(self):
        doc = _make_pinv(docstatus=2)
        doc.set_status()
        self.assertEqual(doc.status, "Cancelled")

    def test_paid_when_outstanding_zero(self):
        doc = _make_pinv(docstatus=1, outstanding_amount=0, grand_total=1000)
        doc.set_status()
        self.assertEqual(doc.status, "Paid")

    def test_partly_paid(self):
        doc = _make_pinv(docstatus=1, outstanding_amount=400, grand_total=1000)
        doc.set_status()
        self.assertEqual(doc.status, "Partly Paid")

    def test_overdue_when_past_due_date(self):
        doc = _make_pinv(docstatus=1, outstanding_amount=1000, grand_total=1000,
                          due_date="2020-01-01")
        doc.set_status()
        self.assertEqual(doc.status, "Overdue")

    def test_submitted_when_not_yet_due(self):
        doc = _make_pinv(docstatus=1, outstanding_amount=1000, grand_total=1000,
                          due_date="2099-01-01")
        doc.set_status()
        self.assertEqual(doc.status, "Submitted")

    def test_submitted_when_no_due_date(self):
        doc = _make_pinv(docstatus=1, outstanding_amount=1000, grand_total=1000,
                          due_date=None)
        doc.set_status()
        self.assertEqual(doc.status, "Submitted")


class TestValidateFiscalYearHandling(unittest.TestCase):

    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.validate_fiscal_year")
    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.validate_account_type")
    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.validate_account_company")
    def test_fiscal_year_set_on_success(self, mock_company, mock_type, mock_fy):
        mock_fy.return_value = "2026-2027"
        doc = _make_pinv(items=[_item(amount=100)])
        doc.validate()
        self.assertEqual(doc.fiscal_year, "2026-2027")

    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.validate_fiscal_year")
    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.validate_account_type")
    @patch("zoho_books_clone.invoicing.doctype.purchase_invoice.purchase_invoice.validate_account_company")
    def test_fiscal_year_blanked_when_lookup_fails(self, mock_company, mock_type, mock_fy):
        # NOTE: this swallows the fiscal-year lock/closed-period error instead
        # of blocking save -- validate() must not raise even when
        # validate_fiscal_year() throws.
        mock_fy.side_effect = frappe.ValidationError("closed period")
        doc = _make_pinv(items=[_item(amount=100)])
        doc.validate()  # should not raise
        self.assertEqual(doc.fiscal_year, "")


if __name__ == "__main__":
    unittest.main()