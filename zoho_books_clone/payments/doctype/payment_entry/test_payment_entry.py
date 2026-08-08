# Copyright (c) 2026, PS Digitise and Contributors
# See license.txt
"""
Tests for Payment Entry (payments/doctype/payment_entry/payment_entry.py) --
validate() (paid_amount guard, payment_date default, fiscal lock,
validate_accounts direction-aware account-type checks, validate_references
allocation guards incl. the Journal-Entry opening-balance path), on_submit/
on_cancel (GL posting/reversal + linked invoice outstanding sync), and the
module-level _refresh_invoice_status status derivation.

Same bind-real-method-onto-a-stand-in pattern as the other invoicing test
suites -- DB-free, exercises the actual controller code.

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.payments.doctype.payment_entry.test_payment_entry
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe

from zoho_books_clone.payments.doctype.payment_entry.payment_entry import (
    PaymentEntry, _refresh_invoice_status,
)

# Captured before any test patches frappe.get_doc, so side_effects below can
# fall through to the real implementation for calls that aren't the one
# under test (e.g. Frappe's own internal System Settings lookup) instead of
# returning our fake object for EVERY doctype/name -- a blanket
# @patch.object(frappe, "get_doc") intercepts those internal calls too, and
# since frappe.get_cached_doc() caches whatever it gets back permanently for
# the process, that poisons System Settings for the rest of the test run
# (and even bench's own post-run scheduler teardown) with our fake object.
_REAL_GET_DOC = frappe.get_doc


def _get_doc_side_effect(expected_doctype, expected_name, fake_obj):
    def _side_effect(doctype, name=None, *args, **kwargs):
        if doctype == expected_doctype and name == expected_name:
            return fake_obj
        return _REAL_GET_DOC(doctype, name, *args, **kwargs)
    return _side_effect


class _Dict(SimpleNamespace):
    def get(self, key, default=None):
        return getattr(self, key, default)


def _ref(reference_doctype="Sales Invoice", reference_name="SINV-2026-00001",
         allocated_amount=100):
    return SimpleNamespace(reference_doctype=reference_doctype,
                            reference_name=reference_name,
                            allocated_amount=allocated_amount)


def _make_pe(references=None, paid_amount=1000, payment_type="Receive",
             company="VK Herbal", payment_date="2026-08-01",
             paid_from=None, paid_to=None, **overrides):
    doc = _Dict(
        doctype="Payment Entry", name="PE-2026-00001", references=references or [],
        paid_amount=paid_amount, payment_type=payment_type, company=company,
        payment_date=payment_date, paid_from=paid_from, paid_to=paid_to,
        fiscal_year=None,
    )
    doc.db_set = MagicMock()
    # Class-level constant, not an instance attribute -- our SimpleNamespace
    # stand-in doesn't inherit it from PaymentEntry, so copy it across.
    doc._ALLOWED_REFERENCE_DOCTYPES = PaymentEntry._ALLOWED_REFERENCE_DOCTYPES
    for k, v in overrides.items():
        setattr(doc, k, v)
    for name in ("validate", "_check_fiscal_lock", "validate_accounts",
                 "validate_references", "on_submit", "on_cancel",
                 "_update_invoice_outstanding"):
        setattr(doc, name, getattr(PaymentEntry, name).__get__(doc))
    return doc


class TestValidateTopLevel(unittest.TestCase):

    def test_throws_on_zero_paid_amount(self):
        doc = _make_pe(paid_amount=0)
        with self.assertRaises(frappe.ValidationError):
            doc.validate()

    def test_throws_on_negative_paid_amount(self):
        doc = _make_pe(paid_amount=-500)
        with self.assertRaises(frappe.ValidationError):
            doc.validate()

    def test_payment_date_defaults_when_blank(self):
        doc = _make_pe(payment_date=None)
        doc._check_fiscal_lock = MagicMock()
        doc.validate_accounts = MagicMock()
        doc.validate_references = MagicMock()
        doc.validate()
        self.assertIsNotNone(doc.payment_date)

    def test_calls_downstream_validators_in_order(self):
        doc = _make_pe()
        calls = []
        doc._check_fiscal_lock = lambda: calls.append("fiscal")
        doc.validate_accounts = lambda: calls.append("accounts")
        doc.validate_references = lambda: calls.append("references")
        doc.validate()
        self.assertEqual(calls, ["fiscal", "accounts", "references"])


class TestFiscalLock(unittest.TestCase):

    @patch("zoho_books_clone.payments.doctype.payment_entry.payment_entry.validate_fiscal_year")
    def test_sets_fiscal_year_on_success(self, mock_fy):
        mock_fy.return_value = "2026-2027"
        doc = _make_pe()
        doc._check_fiscal_lock()
        self.assertEqual(doc.fiscal_year, "2026-2027")

    @patch("zoho_books_clone.payments.doctype.payment_entry.payment_entry.validate_fiscal_year")
    def test_any_error_is_surfaced(self, mock_fy):
        mock_fy.side_effect = frappe.ValidationError("closed period")
        doc = _make_pe()
        with self.assertRaises(frappe.ValidationError):
            doc._check_fiscal_lock()

    def test_skipped_without_date_or_company(self):
        doc = _make_pe(payment_date=None, company=None)
        doc._check_fiscal_lock()  # should not raise
        self.assertIsNone(doc.fiscal_year)


class TestValidateAccounts(unittest.TestCase):

    @patch.object(frappe.db, "exists", return_value=False)
    def test_throws_when_paid_from_account_missing(self, mock_exists):
        doc = _make_pe(paid_from="Ghost Account", paid_to=None)
        with self.assertRaises(frappe.ValidationError):
            doc.validate_accounts()

    @patch.object(frappe.db, "exists", return_value=False)
    def test_throws_when_paid_to_account_missing(self, mock_exists):
        doc = _make_pe(paid_from=None, paid_to="Ghost Account")
        with self.assertRaises(frappe.ValidationError):
            doc.validate_accounts()

    @patch("zoho_books_clone.payments.doctype.payment_entry.payment_entry.validate_account_type")
    @patch("zoho_books_clone.payments.doctype.payment_entry.payment_entry.validate_account_company")
    @patch.object(frappe.db, "exists", return_value=True)
    def test_receive_checks_receivable_from_and_bank_cash_to(self, mock_exists, mock_company, mock_type):
        doc = _make_pe(payment_type="Receive", paid_from="Debtors - VK", paid_to="Bank - VK")
        doc.validate_accounts()
        mock_type.assert_any_call("Debtors - VK", ["Receivable"])
        mock_type.assert_any_call("Bank - VK", ["Bank", "Cash"])

    @patch("zoho_books_clone.payments.doctype.payment_entry.payment_entry.validate_account_type")
    @patch("zoho_books_clone.payments.doctype.payment_entry.payment_entry.validate_account_company")
    @patch.object(frappe.db, "exists", return_value=True)
    def test_pay_checks_bank_cash_from_and_payable_to(self, mock_exists, mock_company, mock_type):
        doc = _make_pe(payment_type="Pay", paid_from="Bank - VK", paid_to="Creditors - VK")
        doc.validate_accounts()
        mock_type.assert_any_call("Bank - VK", ["Bank", "Cash"])
        mock_type.assert_any_call("Creditors - VK", ["Payable"])

    @patch("zoho_books_clone.payments.doctype.payment_entry.payment_entry.validate_account_type")
    @patch("zoho_books_clone.payments.doctype.payment_entry.payment_entry.validate_account_company")
    @patch.object(frappe.db, "exists", return_value=True)
    def test_company_checked_for_both_accounts(self, mock_exists, mock_company, mock_type):
        doc = _make_pe(payment_type="Receive", paid_from="Debtors - VK",
                        paid_to="Bank - VK", company="VK Herbal")
        doc.validate_accounts()
        mock_company.assert_any_call("Debtors - VK", "VK Herbal")
        mock_company.assert_any_call("Bank - VK", "VK Herbal")

    @patch.object(frappe.db, "exists", return_value=True)
    def test_noop_without_either_account_set(self, mock_exists):
        doc = _make_pe(paid_from=None, paid_to=None)
        doc.validate_accounts()  # should not raise


class TestValidateReferences(unittest.TestCase):

    def test_throws_when_allocated_exceeds_paid_amount(self):
        doc = _make_pe(paid_amount=100, references=[_ref(allocated_amount=150)])
        with self.assertRaises(frappe.ValidationError):
            doc.validate_references()

    @patch.object(frappe.db, "get_value", return_value=200)
    def test_receive_cannot_reference_purchase_invoice(self, mock_get_value):
        doc = _make_pe(payment_type="Receive", paid_amount=100,
                        references=[_ref(reference_doctype="Purchase Invoice",
                                          reference_name="PINV-0001", allocated_amount=50)])
        with self.assertRaises(frappe.ValidationError):
            doc.validate_references()

    @patch.object(frappe.db, "get_value", return_value=200)
    def test_pay_cannot_reference_sales_invoice(self, mock_get_value):
        doc = _make_pe(payment_type="Pay", paid_amount=100,
                        references=[_ref(reference_doctype="Sales Invoice",
                                          reference_name="SINV-0001", allocated_amount=50)])
        with self.assertRaises(frappe.ValidationError):
            doc.validate_references()

    @patch.object(frappe.db, "get_value", return_value=200)
    def test_receive_against_sales_invoice_allowed(self, mock_get_value):
        doc = _make_pe(payment_type="Receive", paid_amount=100,
                        references=[_ref(reference_doctype="Sales Invoice",
                                          reference_name="SINV-0001", allocated_amount=50)])
        doc.validate_references()  # should not raise

    @patch.object(frappe.db, "get_value", return_value=None)
    def test_throws_when_referenced_invoice_not_found(self, mock_get_value):
        doc = _make_pe(payment_type="Receive", paid_amount=100,
                        references=[_ref(reference_doctype="Sales Invoice",
                                          reference_name="GHOST", allocated_amount=50)])
        with self.assertRaises(frappe.ValidationError):
            doc.validate_references()

    @patch.object(frappe.db, "get_value", return_value=30)
    def test_throws_when_allocated_exceeds_invoice_outstanding(self, mock_get_value):
        doc = _make_pe(payment_type="Receive", paid_amount=100,
                        references=[_ref(reference_doctype="Sales Invoice",
                                          reference_name="SINV-0001", allocated_amount=50)])
        with self.assertRaises(frappe.ValidationError):
            doc.validate_references()

    @patch("zoho_books_clone.accounts.opening_balance.get_opening_balance_outstanding", return_value=500)
    @patch.object(frappe.db, "get_value", return_value="CUST-1")
    def test_journal_entry_reference_uses_opening_balance_outstanding(
        self, mock_get_value, mock_opening_outstanding,
    ):
        # Real _REF_TYPE is used as-is (it's just a lookup key, not a value
        # we need to control) -- no need to patch it.
        doc = _make_pe(payment_type="Receive", paid_amount=1000,
                        references=[_ref(reference_doctype="Journal Entry",
                                          reference_name="JE-0001", allocated_amount=200)])
        doc.validate_references()  # should not raise
        mock_opening_outstanding.assert_called_once_with("Customer", "CUST-1")

    @patch.object(frappe.db, "get_value", return_value=None)
    def test_journal_entry_not_an_opening_balance_throws(self, mock_get_value):
        doc = _make_pe(payment_type="Receive", paid_amount=1000,
                        references=[_ref(reference_doctype="Journal Entry",
                                          reference_name="JE-0001", allocated_amount=200)])
        with self.assertRaises(frappe.ValidationError):
            doc.validate_references()

    @patch("zoho_books_clone.accounts.opening_balance.get_opening_balance_outstanding", return_value=100)
    @patch.object(frappe.db, "get_value", return_value="CUST-1")
    def test_journal_entry_allocated_exceeding_opening_outstanding_throws(
        self, mock_get_value, mock_opening_outstanding,
    ):
        doc = _make_pe(payment_type="Receive", paid_amount=1000,
                        references=[_ref(reference_doctype="Journal Entry",
                                          reference_name="JE-0001", allocated_amount=200)])
        with self.assertRaises(frappe.ValidationError):
            doc.validate_references()


class TestOnSubmitOnCancel(unittest.TestCase):

    @patch("zoho_books_clone.payments.doctype.payment_entry.payment_entry.post_payment_entry")
    def test_on_submit_posts_gl_then_updates_outstanding(self, mock_post):
        doc = _make_pe()
        doc._update_invoice_outstanding = MagicMock()
        doc.on_submit()
        mock_post.assert_called_once_with(doc)
        doc._update_invoice_outstanding.assert_called_once_with(cancel=False)

    @patch("zoho_books_clone.payments.doctype.payment_entry.payment_entry.reverse_voucher")
    def test_on_cancel_reverses_gl_then_restores_outstanding(self, mock_reverse):
        doc = _make_pe()
        doc._update_invoice_outstanding = MagicMock()
        doc.on_cancel()
        mock_reverse.assert_called_once_with("Payment Entry", doc.name)
        doc._update_invoice_outstanding.assert_called_once_with(cancel=True)


class TestUpdateInvoiceOutstanding(unittest.TestCase):

    @patch("zoho_books_clone.payments.doctype.payment_entry.payment_entry._refresh_invoice_status")
    @patch.object(frappe.db, "set_value")
    @patch.object(frappe.db, "get_value", return_value=1000)
    def test_submit_reduces_outstanding(self, mock_get_value, mock_set_value, mock_refresh):
        doc = _make_pe(references=[_ref(reference_doctype="Sales Invoice",
                                         reference_name="SINV-1", allocated_amount=400)])
        doc._update_invoice_outstanding(cancel=False)
        mock_set_value.assert_called_once_with(
            "Sales Invoice", "SINV-1", "outstanding_amount", 600, update_modified=False
        )
        mock_refresh.assert_called_once_with("Sales Invoice", "SINV-1", 600)

    @patch("zoho_books_clone.payments.doctype.payment_entry.payment_entry._refresh_invoice_status")
    @patch.object(frappe.db, "set_value")
    @patch.object(frappe.db, "get_value", return_value=600)
    def test_cancel_restores_outstanding(self, mock_get_value, mock_set_value, mock_refresh):
        doc = _make_pe(references=[_ref(reference_doctype="Sales Invoice",
                                         reference_name="SINV-1", allocated_amount=400)])
        doc._update_invoice_outstanding(cancel=True)
        mock_set_value.assert_called_once_with(
            "Sales Invoice", "SINV-1", "outstanding_amount", 1000, update_modified=False
        )

    @patch("zoho_books_clone.payments.doctype.payment_entry.payment_entry._refresh_invoice_status")
    @patch.object(frappe.db, "set_value")
    @patch.object(frappe.db, "get_value", return_value=100)
    def test_clamped_at_zero_never_negative(self, mock_get_value, mock_set_value, mock_refresh):
        doc = _make_pe(references=[_ref(reference_doctype="Sales Invoice",
                                         reference_name="SINV-1", allocated_amount=400)])
        doc._update_invoice_outstanding(cancel=False)
        mock_set_value.assert_called_once_with(
            "Sales Invoice", "SINV-1", "outstanding_amount", 0.0, update_modified=False
        )

    @patch.object(frappe.db, "set_value")
    @patch.object(frappe.db, "get_value")
    def test_journal_entry_reference_skipped(self, mock_get_value, mock_set_value):
        doc = _make_pe(references=[_ref(reference_doctype="Journal Entry",
                                         reference_name="JE-1", allocated_amount=400)])
        doc._update_invoice_outstanding(cancel=False)
        mock_set_value.assert_not_called()
        mock_get_value.assert_not_called()


class TestRefreshInvoiceStatus(unittest.TestCase):

    @patch.object(frappe.db, "set_value")
    @patch.object(frappe, "get_doc")
    def test_paid_when_outstanding_zero(self, mock_get_doc, mock_set_value):
        fake = SimpleNamespace(grand_total=1000, due_date=None)
        mock_get_doc.side_effect = _get_doc_side_effect("Sales Invoice", "SINV-1", fake)
        _refresh_invoice_status("Sales Invoice", "SINV-1", 0)
        mock_set_value.assert_called_once_with(
            "Sales Invoice", "SINV-1", "status", "Paid", update_modified=False
        )

    @patch.object(frappe.db, "set_value")
    @patch.object(frappe, "get_doc")
    def test_partly_paid(self, mock_get_doc, mock_set_value):
        fake = SimpleNamespace(grand_total=1000, due_date=None)
        mock_get_doc.side_effect = _get_doc_side_effect("Sales Invoice", "SINV-1", fake)
        _refresh_invoice_status("Sales Invoice", "SINV-1", 400)
        mock_set_value.assert_called_once_with(
            "Sales Invoice", "SINV-1", "status", "Partly Paid", update_modified=False
        )

    @patch.object(frappe.db, "set_value")
    @patch.object(frappe, "get_doc")
    def test_overdue_when_past_due_date(self, mock_get_doc, mock_set_value):
        # due_date is truthy here, so _refresh_invoice_status calls the real
        # today()/getdate() -- which internally may call frappe.get_doc for
        # System Settings. The side_effect must fall through to the real
        # get_doc for that call, not return our fake Sales Invoice for it too.
        fake = SimpleNamespace(grand_total=1000, due_date="2020-01-01")
        mock_get_doc.side_effect = _get_doc_side_effect("Sales Invoice", "SINV-1", fake)
        _refresh_invoice_status("Sales Invoice", "SINV-1", 1000)
        mock_set_value.assert_called_once_with(
            "Sales Invoice", "SINV-1", "status", "Overdue", update_modified=False
        )

    @patch.object(frappe.db, "set_value")
    @patch.object(frappe, "get_doc")
    def test_submitted_when_not_yet_due(self, mock_get_doc, mock_set_value):
        fake = SimpleNamespace(grand_total=1000, due_date="2099-01-01")
        mock_get_doc.side_effect = _get_doc_side_effect("Sales Invoice", "SINV-1", fake)
        _refresh_invoice_status("Sales Invoice", "SINV-1", 1000)
        mock_set_value.assert_called_once_with(
            "Sales Invoice", "SINV-1", "status", "Submitted", update_modified=False
        )


if __name__ == "__main__":
    unittest.main()