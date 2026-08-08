# Copyright (c) 2026, PS Digitise and Contributors
# See license.txt
"""
Tests for Sales Invoice (invoicing/doctype/sales_invoice/sales_invoice.py)
-- validate() pipeline: item/discount calc, batch validation, totals +
GST round-off, outstanding amount, account-type checks, status derivation,
due date, customer GSTIN autofill.

Same bind-real-method-onto-a-stand-in pattern as the Purchase Invoice test
suite (test_purchase_invoice.py) -- DB-free, exercises the actual controller
code, not a reimplementation of it.

on_submit/on_cancel (GL posting, credit-note over-claim guard, SO qty
reversal) is a separate file: test_sales_invoice_submit.py.

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.invoicing.doctype.sales_invoice.test_sales_invoice_validate
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice import SalesInvoice


class _Dict(SimpleNamespace):
    """SimpleNamespace with a .get() so set_posting_time(doc.get(...)) works."""
    def get(self, key, default=None):
        return getattr(self, key, default)


def _item(item_code="ITEM-1", item_name=None, qty=1, rate=100, discount_percentage=0,
          discount_amount=0, amount=0, idx=1, batch_no=None, batch_expiry_date=None):
    return SimpleNamespace(
        item_code=item_code, item_name=item_name or item_code, qty=qty, rate=rate,
        discount_percentage=discount_percentage, discount_amount=discount_amount,
        amount=amount, idx=idx, batch_no=batch_no, batch_expiry_date=batch_expiry_date,
    )


def _tax(rate=0, tax_amount=0):
    return SimpleNamespace(rate=rate, tax_amount=tax_amount)


def _make_si(items=None, taxes=None, docstatus=0, company="VK Herbal",
             posting_date="2026-08-01", **overrides):
    doc = _Dict(
        doctype="Sales Invoice", name="SINV-2026-00001", items=items or [],
        taxes=taxes or [], docstatus=docstatus, company=company,
        posting_date=posting_date, set_posting_time=0, posting_time=None,
        discount_type=None, additional_discount_percentage=0,
        additional_discount_amount=0, debit_to=None, income_account=None,
        due_date=None, is_return=0, return_against=None, sales_order=None,
        update_stock=0, fiscal_year=None, customer=None, customer_gstin=None,
        payment_terms=None,
    )
    for k, v in overrides.items():
        setattr(doc, k, v)
    for name in ("validate", "validate_items", "validate_batches", "calculate_totals",
                 "calculate_discount", "set_outstanding_amount", "validate_accounts",
                 "set_status", "set_due_date", "_set_customer_gstin"):
        setattr(doc, name, getattr(SalesInvoice, name).__get__(doc))
    return doc


class TestItemAndDiscountCalc(unittest.TestCase):

    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.validate_fiscal_year")
    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.validate_account_type")
    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.validate_account_company")
    def test_row_amount_is_qty_times_rate_minus_discount(self, mock_company, mock_type, mock_fy):
        mock_fy.return_value = "2026-2027"
        row = _item(qty=2, rate=150, discount_percentage=10)
        doc = _make_si(items=[row])
        doc.validate()
        # base = 300, discount_amount = 30, amount = 270
        self.assertEqual(row.discount_amount, 30)
        self.assertEqual(row.amount, 270)

    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.validate_fiscal_year")
    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.validate_account_type")
    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.validate_account_company")
    def test_flat_discount_amount_used_when_no_percentage(self, mock_company, mock_type, mock_fy):
        mock_fy.return_value = "2026-2027"
        row = _item(qty=1, rate=500, discount_percentage=0, discount_amount=50)
        doc = _make_si(items=[row])
        doc.validate()
        self.assertEqual(row.discount_amount, 50)
        self.assertEqual(row.amount, 450)

    def test_validate_items_throws_when_no_items(self):
        doc = _make_si(items=[])
        with self.assertRaises(frappe.ValidationError):
            doc.validate_items()

    def test_qty_must_be_positive_for_normal_invoice(self):
        row = _item(qty=0, rate=100)
        doc = _make_si(items=[row], is_return=0)
        with self.assertRaises(frappe.ValidationError):
            doc.validate_items()

    def test_negative_qty_allowed_for_return_invoice(self):
        row = _item(qty=-2, rate=100)
        doc = _make_si(items=[row], is_return=1)
        doc.validate_items()  # should not raise
        # base = -200, amount = -200
        self.assertEqual(row.amount, -200)


class TestValidateBatches(unittest.TestCase):

    def test_skipped_for_return_invoices(self):
        row = _item(batch_no=None)
        doc = _make_si(items=[row], is_return=1, update_stock=1)
        doc.validate_batches()  # should not raise / not touch batch fields

    def test_skipped_and_clears_batch_when_update_stock_off(self):
        row = _item(batch_no="BATCH-1", batch_expiry_date="2026-12-31")
        doc = _make_si(items=[row], is_return=0, update_stock=0)
        doc.validate_batches()
        self.assertIsNone(row.batch_no)
        self.assertIsNone(row.batch_expiry_date)

    @patch.object(frappe.db, "get_value", return_value=0)  # has_batch_no = False
    def test_non_batch_item_clears_batch_fields(self, mock_get_value):
        row = _item(batch_no="STALE", batch_expiry_date="2026-01-01")
        doc = _make_si(items=[row], is_return=0, update_stock=1)
        doc.validate_batches()
        self.assertIsNone(row.batch_no)
        self.assertIsNone(row.batch_expiry_date)

    @patch.object(frappe.db, "get_value", return_value=1)  # has_batch_no = True
    def test_missing_batch_no_throws(self, mock_get_value):
        row = _item(batch_no=None)
        doc = _make_si(items=[row], is_return=0, update_stock=1)
        with self.assertRaises(frappe.ValidationError):
            doc.validate_batches()

    @patch.object(frappe.db, "sql")
    @patch.object(frappe.db, "get_value")
    def test_batch_not_found_throws(self, mock_get_value, mock_sql):
        mock_get_value.side_effect = [1, None]  # has_batch_no=True, then Batch lookup=None
        row = _item(batch_no="GHOST")
        doc = _make_si(items=[row], is_return=0, update_stock=1)
        with self.assertRaises(frappe.ValidationError):
            doc.validate_batches()

    @patch.object(frappe.db, "get_value")
    def test_batch_belonging_to_other_item_throws(self, mock_get_value):
        mock_get_value.side_effect = [
            1,  # has_batch_no
            frappe._dict({"item": "OTHER-ITEM", "expiry_date": None, "disabled": 0}),
        ]
        row = _item(item_code="ITEM-1", batch_no="B1")
        doc = _make_si(items=[row], is_return=0, update_stock=1)
        with self.assertRaises(frappe.ValidationError):
            doc.validate_batches()

    @patch.object(frappe.db, "get_value")
    def test_disabled_batch_throws(self, mock_get_value):
        mock_get_value.side_effect = [
            1,
            frappe._dict({"item": "ITEM-1", "expiry_date": None, "disabled": 1}),
        ]
        row = _item(item_code="ITEM-1", batch_no="B1")
        doc = _make_si(items=[row], is_return=0, update_stock=1)
        with self.assertRaises(frappe.ValidationError):
            doc.validate_batches()

    @patch.object(frappe.db, "get_value")
    def test_expired_batch_throws(self, mock_get_value):
        mock_get_value.side_effect = [
            1,
            frappe._dict({"item": "ITEM-1", "expiry_date": "2020-01-01", "disabled": 0}),
        ]
        row = _item(item_code="ITEM-1", batch_no="B1")
        doc = _make_si(items=[row], is_return=0, update_stock=1, posting_date="2026-08-01")
        with self.assertRaises(frappe.ValidationError):
            doc.validate_batches()

    @patch.object(frappe.db, "sql")
    @patch.object(frappe.db, "get_value")
    def test_qty_exceeding_available_batch_stock_throws(self, mock_get_value, mock_sql):
        mock_get_value.side_effect = [
            1,
            frappe._dict({"item": "ITEM-1", "expiry_date": None, "disabled": 0}),
        ]
        mock_sql.return_value = [[50]]  # available_qty
        row = _item(item_code="ITEM-1", batch_no="B1", qty=60)
        doc = _make_si(items=[row], is_return=0, update_stock=1)
        with self.assertRaises(frappe.ValidationError):
            doc.validate_batches()

    @patch.object(frappe.db, "sql")
    @patch.object(frappe.db, "get_value")
    def test_qty_within_available_batch_stock_passes(self, mock_get_value, mock_sql):
        mock_get_value.side_effect = [
            1,
            frappe._dict({"item": "ITEM-1", "expiry_date": None, "disabled": 0}),
        ]
        mock_sql.return_value = [[50]]
        row = _item(item_code="ITEM-1", batch_no="B1", qty=40)
        doc = _make_si(items=[row], is_return=0, update_stock=1)
        doc.validate_batches()  # should not raise


class TestCalculateDiscount(unittest.TestCase):

    def test_percentage_discount_derives_amount_from_subtotal(self):
        doc = _make_si(discount_type="Percentage", additional_discount_percentage=10)
        doc.calculate_discount(1000)
        self.assertEqual(doc.additional_discount_amount, 100)

    def test_amount_mode_takes_entered_value(self):
        doc = _make_si(discount_type="Amount", additional_discount_amount=75)
        doc.calculate_discount(1000)
        self.assertEqual(doc.additional_discount_amount, 75)
        self.assertEqual(doc.additional_discount_percentage, 0)

    def test_discount_clamped_to_subtotal(self):
        doc = _make_si(discount_type="Amount", additional_discount_amount=5000)
        doc.calculate_discount(1000)
        self.assertEqual(doc.additional_discount_amount, 1000)

    def test_discount_never_negative(self):
        doc = _make_si(discount_type="Amount", additional_discount_amount=-50)
        doc.calculate_discount(1000)
        self.assertEqual(doc.additional_discount_amount, 0)

    def test_defaults_to_percentage_mode_when_unset(self):
        doc = _make_si(discount_type=None, additional_discount_percentage=5)
        doc.calculate_discount(1000)
        self.assertEqual(doc.discount_type, "Percentage")
        self.assertEqual(doc.additional_discount_amount, 50)


class TestCalculateTotals(unittest.TestCase):

    def test_net_total_tax_and_grand_total(self):
        doc = _make_si(items=[_item(amount=1000)], taxes=[_tax(rate=18)])
        doc.calculate_totals()
        self.assertEqual(doc.net_total, 1000)
        self.assertEqual(doc.total_tax, 180)
        self.assertEqual(doc.grand_total, 1180)
        self.assertEqual(doc.round_off, 0)

    def test_round_off_captures_paise_remainder(self):
        doc = _make_si(items=[_item(amount=333.33)], taxes=[_tax(rate=18)])
        doc.calculate_totals()
        pre_round = 333.33 + round(333.33 * 0.18, 2)
        self.assertEqual(doc.grand_total, round(pre_round))
        self.assertAlmostEqual(doc.round_off, round(doc.grand_total - pre_round, 2))

    def test_additional_discount_reduces_net_before_tax(self):
        doc = _make_si(
            items=[_item(amount=1000)], taxes=[_tax(rate=10)],
            discount_type="Amount", additional_discount_amount=100,
        )
        doc.calculate_totals()
        # net = 1000 - 100 = 900; tax = 90
        self.assertEqual(doc.net_total, 900)
        self.assertEqual(doc.total_tax, 90)
        self.assertEqual(doc.grand_total, 990)

    def test_zero_rate_tax_rows_are_not_recomputed(self):
        tax = _tax(rate=0, tax_amount=999)  # stale value, should be left alone
        doc = _make_si(items=[_item(amount=500)], taxes=[tax])
        doc.calculate_totals()
        self.assertEqual(tax.tax_amount, 999)
        self.assertEqual(doc.total_tax, 999)


class TestSetOutstandingAmount(unittest.TestCase):

    def test_sets_outstanding_when_draft(self):
        doc = _make_si(docstatus=0, grand_total=1500)
        doc.set_outstanding_amount()
        self.assertEqual(doc.outstanding_amount, 1500)

    def test_does_not_touch_outstanding_when_submitted(self):
        doc = _make_si(docstatus=1, grand_total=1500, outstanding_amount=200)
        doc.set_outstanding_amount()
        self.assertEqual(doc.outstanding_amount, 200)

    def test_return_invoice_is_noop(self):
        doc = _make_si(docstatus=0, grand_total=-500, is_return=1, outstanding_amount="unset")
        doc.set_outstanding_amount()
        self.assertEqual(doc.outstanding_amount, "unset")  # left untouched


class TestValidateAccounts(unittest.TestCase):

    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.validate_account_type")
    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.validate_account_company")
    def test_debit_to_checked_for_receivable_type(self, mock_company, mock_type):
        doc = _make_si(debit_to="Debtors - VK", income_account=None)
        doc.validate_accounts()
        mock_company.assert_called_once_with("Debtors - VK", "VK Herbal")
        mock_type.assert_called_once_with("Debtors - VK", ["Receivable"])

    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.validate_account_type")
    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.validate_account_company")
    def test_income_account_checked_for_income_type(self, mock_company, mock_type):
        doc = _make_si(debit_to=None, income_account="Sales - VK")
        doc.validate_accounts()
        mock_type.assert_called_once_with("Sales - VK", ["Income"])

    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.validate_account_type")
    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.validate_account_company")
    def test_no_accounts_set_is_a_noop(self, mock_company, mock_type):
        doc = _make_si(debit_to=None, income_account=None)
        doc.validate_accounts()  # should not raise
        mock_company.assert_not_called()
        mock_type.assert_not_called()


class TestSetStatus(unittest.TestCase):

    def test_draft(self):
        doc = _make_si(docstatus=0)
        doc.set_status()
        self.assertEqual(doc.status, "Draft")

    def test_cancelled(self):
        doc = _make_si(docstatus=2)
        doc.set_status()
        self.assertEqual(doc.status, "Cancelled")

    def test_paid_when_outstanding_zero(self):
        doc = _make_si(docstatus=1, outstanding_amount=0, grand_total=1000)
        doc.set_status()
        self.assertEqual(doc.status, "Paid")

    def test_partly_paid(self):
        doc = _make_si(docstatus=1, outstanding_amount=400, grand_total=1000)
        doc.set_status()
        self.assertEqual(doc.status, "Partly Paid")

    def test_overdue_when_past_due_date(self):
        doc = _make_si(docstatus=1, outstanding_amount=1000, grand_total=1000,
                        due_date="2020-01-01")
        doc.set_status()
        self.assertEqual(doc.status, "Overdue")

    def test_submitted_when_not_yet_due(self):
        doc = _make_si(docstatus=1, outstanding_amount=1000, grand_total=1000,
                        due_date="2099-01-01")
        doc.set_status()
        self.assertEqual(doc.status, "Submitted")

    def test_submitted_when_no_due_date(self):
        doc = _make_si(docstatus=1, outstanding_amount=1000, grand_total=1000,
                        due_date=None)
        doc.set_status()
        self.assertEqual(doc.status, "Submitted")


class TestSetDueDate(unittest.TestCase):

    def test_falls_back_to_posting_date_without_payment_terms(self):
        doc = _make_si(due_date=None, payment_terms=None, posting_date="2026-08-01")
        doc.set_due_date()
        self.assertEqual(doc.due_date, "2026-08-01")

    def test_existing_due_date_left_alone(self):
        doc = _make_si(due_date="2026-09-15", posting_date="2026-08-01")
        doc.set_due_date()
        self.assertEqual(doc.due_date, "2026-09-15")

    @patch("zoho_books_clone.books_setup.doctype.payment_terms.payment_terms.get_due_date")
    def test_uses_payment_terms_when_set(self, mock_get_due_date):
        mock_get_due_date.return_value = "2026-09-01"
        doc = _make_si(due_date=None, payment_terms="Net 30", posting_date="2026-08-01")
        doc.set_due_date()
        self.assertEqual(doc.due_date, "2026-09-01")
        mock_get_due_date.assert_called_once_with("Net 30", "2026-08-01")

    @patch("zoho_books_clone.books_setup.doctype.payment_terms.payment_terms.get_due_date",
           side_effect=Exception("boom"))
    def test_falls_back_to_posting_date_when_payment_terms_lookup_fails(self, mock_get_due_date):
        doc = _make_si(due_date=None, payment_terms="Net 30", posting_date="2026-08-01")
        doc.set_due_date()
        self.assertEqual(doc.due_date, "2026-08-01")


class TestSetCustomerGstin(unittest.TestCase):

    @patch.object(frappe.db, "get_value", return_value="29ABCDE1234F1Z5")
    def test_autofills_gstin_from_customer_when_blank(self, mock_get_value):
        doc = _make_si(customer="CUST-1", customer_gstin=None)
        doc._set_customer_gstin()
        self.assertEqual(doc.customer_gstin, "29ABCDE1234F1Z5")

    @patch.object(frappe.db, "get_value")
    def test_does_not_overwrite_existing_gstin(self, mock_get_value):
        doc = _make_si(customer="CUST-1", customer_gstin="27XXXXX0000X1Z1")
        doc._set_customer_gstin()
        self.assertEqual(doc.customer_gstin, "27XXXXX0000X1Z1")
        mock_get_value.assert_not_called()

    @patch.object(frappe.db, "get_value")
    def test_noop_without_customer(self, mock_get_value):
        doc = _make_si(customer=None, customer_gstin=None)
        doc._set_customer_gstin()
        mock_get_value.assert_not_called()


class TestValidateFiscalYearHandling(unittest.TestCase):

    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.validate_fiscal_year")
    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.validate_account_type")
    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.validate_account_company")
    def test_fiscal_year_set_on_success(self, mock_company, mock_type, mock_fy):
        mock_fy.return_value = "2026-2027"
        doc = _make_si(items=[_item(amount=100)])
        doc.validate()
        self.assertEqual(doc.fiscal_year, "2026-2027")

    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.validate_fiscal_year")
    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.validate_account_type")
    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.validate_account_company")
    def test_closed_period_error_is_surfaced_not_swallowed(self, mock_company, mock_type, mock_fy):
        # ValidationError (e.g. lock_date / closed fiscal year) must propagate
        # -- only unexpected/non-ValidationError exceptions are swallowed.
        mock_fy.side_effect = frappe.ValidationError("closed period")
        doc = _make_si(items=[_item(amount=100)])
        with self.assertRaises(frappe.ValidationError):
            doc.validate()

    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.validate_fiscal_year")
    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.validate_account_type")
    @patch("zoho_books_clone.invoicing.doctype.sales_invoice.sales_invoice.validate_account_company")
    def test_fiscal_year_blanked_when_unexpected_error(self, mock_company, mock_type, mock_fy):
        # Only non-ValidationError exceptions are swallowed (missing FY on
        # draft is OK) -- validate() must not raise in that case.
        mock_fy.side_effect = Exception("unexpected lookup failure")
        doc = _make_si(items=[_item(amount=100)])
        doc.validate()  # should not raise
        self.assertIsNone(doc.fiscal_year)  # left untouched, not blanked


if __name__ == "__main__":
    unittest.main()