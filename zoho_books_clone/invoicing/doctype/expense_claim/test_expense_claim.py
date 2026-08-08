# Copyright (c) 2026, PS Digitise and Contributors
# See license.txt
"""
Tests for Expense Claim (invoicing/doctype/expense_claim/expense_claim.py) --
validate() (claim date default, expense-line guards, total calc), on_submit
(status-only -- GL posting deferred to approve()), on_cancel (conditional GL
reversal, guarded by whether GL entries actually exist), and the whitelisted
approve/reject/mark_paid status-transition + budget-check + GL-posting
lifecycle.

Same bind-real-method-onto-a-stand-in pattern as the other invoicing test
suites -- DB-free, exercises the actual controller code.

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.invoicing.doctype.expense_claim.test_expense_claim
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe

from zoho_books_clone.invoicing.doctype.expense_claim.expense_claim import ExpenseClaim


class _Dict(SimpleNamespace):
    def get(self, key, default=None):
        return getattr(self, key, default)


def _row(amount=100, idx=1):
    return SimpleNamespace(amount=amount, idx=idx)


def _make_ec(expenses=None, claim_date=None, status=None, payable_account=None,
             **overrides):
    doc = _Dict(
        doctype="Expense Claim", name="EC-2026-00001", expenses=expenses or [],
        claim_date=claim_date, status=status, payable_account=payable_account,
        total_claimed_amount=0,
    )
    doc.db_set = MagicMock()
    for k, v in overrides.items():
        setattr(doc, k, v)
    for name in ("validate", "on_submit", "on_cancel", "approve", "reject", "mark_paid"):
        setattr(doc, name, getattr(ExpenseClaim, name).__get__(doc))
    return doc


class TestValidate(unittest.TestCase):

    def test_claim_date_defaults_when_blank(self):
        doc = _make_ec(expenses=[_row(amount=100)], claim_date=None)
        doc.validate()
        self.assertIsNotNone(doc.claim_date)

    def test_existing_claim_date_left_alone(self):
        doc = _make_ec(expenses=[_row(amount=100)], claim_date="2026-07-01")
        doc.validate()
        self.assertEqual(doc.claim_date, "2026-07-01")

    def test_throws_when_no_expense_lines(self):
        doc = _make_ec(expenses=[])
        with self.assertRaises(frappe.ValidationError):
            doc.validate()

    def test_throws_when_any_row_amount_not_positive(self):
        doc = _make_ec(expenses=[_row(amount=100), _row(amount=0, idx=2)])
        with self.assertRaises(frappe.ValidationError):
            doc.validate()

    def test_throws_when_row_amount_negative(self):
        doc = _make_ec(expenses=[_row(amount=-50)])
        with self.assertRaises(frappe.ValidationError):
            doc.validate()

    def test_total_claimed_amount_sums_all_rows(self):
        doc = _make_ec(expenses=[_row(amount=250.5), _row(amount=99.25, idx=2)])
        doc.validate()
        self.assertEqual(doc.total_claimed_amount, 349.75)


class TestOnSubmit(unittest.TestCase):

    def test_sets_status_submitted_no_gl_posting(self):
        doc = _make_ec()
        with patch("zoho_books_clone.invoicing.doctype.expense_claim.expense_claim.post_expense_claim") as mock_post:
            doc.on_submit()
            doc.db_set.assert_called_once_with("status", "Submitted")
            mock_post.assert_not_called()  # GL posting deferred to approve()


class TestOnCancel(unittest.TestCase):

    @patch("zoho_books_clone.invoicing.doctype.expense_claim.expense_claim.reverse_voucher")
    @patch.object(frappe.db, "exists", return_value=True)
    def test_reverses_gl_when_entries_exist(self, mock_exists, mock_reverse):
        doc = _make_ec()
        doc.on_cancel()
        doc.db_set.assert_called_once_with("status", "Cancelled")
        mock_reverse.assert_called_once_with("Expense Claim", doc.name)

    @patch("zoho_books_clone.invoicing.doctype.expense_claim.expense_claim.reverse_voucher")
    @patch.object(frappe.db, "exists", return_value=False)
    def test_no_gl_reversal_when_never_approved(self, mock_exists, mock_reverse):
        # A claim cancelled before approval never had GL entries posted --
        # reverse_voucher must not be called (it would error on nothing to reverse).
        doc = _make_ec()
        doc.on_cancel()
        mock_reverse.assert_not_called()


class TestApprove(unittest.TestCase):

    def test_throws_when_not_submitted(self):
        doc = _make_ec(status="Draft", payable_account="Creditors - VK")
        with self.assertRaises(frappe.ValidationError):
            doc.approve()

    def test_throws_when_already_approved(self):
        doc = _make_ec(status="Approved", payable_account="Creditors - VK")
        with self.assertRaises(frappe.ValidationError):
            doc.approve()

    def test_throws_without_payable_account(self):
        doc = _make_ec(status="Submitted", payable_account=None)
        with self.assertRaises(frappe.ValidationError):
            doc.approve()

    @patch("zoho_books_clone.invoicing.doctype.expense_claim.expense_claim.post_expense_claim")
    @patch("zoho_books_clone.accounts.central_validator.check_budget_for_doc")
    def test_runs_budget_check_before_posting(self, mock_budget, mock_post):
        doc = _make_ec(status="Submitted", payable_account="Creditors - VK")
        doc.approve()
        mock_budget.assert_called_once_with(doc)
        mock_post.assert_called_once_with(doc)

    @patch("zoho_books_clone.invoicing.doctype.expense_claim.expense_claim.post_expense_claim")
    @patch("zoho_books_clone.accounts.central_validator.check_budget_for_doc",
           side_effect=frappe.ValidationError("over budget"))
    def test_budget_violation_blocks_approval(self, mock_budget, mock_post):
        doc = _make_ec(status="Submitted", payable_account="Creditors - VK")
        with self.assertRaises(frappe.ValidationError):
            doc.approve()
        mock_post.assert_not_called()
        doc.db_set.assert_not_called()  # status never flipped to Approved

    @patch("zoho_books_clone.invoicing.doctype.expense_claim.expense_claim.post_expense_claim")
    @patch("zoho_books_clone.accounts.central_validator.check_budget_for_doc")
    def test_sets_status_and_approved_by(self, mock_budget, mock_post):
        doc = _make_ec(status="Submitted", payable_account="Creditors - VK")
        with patch.object(frappe, "session", SimpleNamespace(user="qc@vkherbal.test")):
            doc.approve()
        doc.db_set.assert_any_call("status", "Approved")
        doc.db_set.assert_any_call("approved_by", "qc@vkherbal.test")


class TestReject(unittest.TestCase):

    def test_throws_when_not_submitted(self):
        doc = _make_ec(status="Draft")
        with self.assertRaises(frappe.ValidationError):
            doc.reject()

    def test_sets_status_rejected(self):
        doc = _make_ec(status="Submitted")
        doc.reject()
        doc.db_set.assert_called_once_with("status", "Rejected")


class TestMarkPaid(unittest.TestCase):

    def test_throws_when_not_approved(self):
        doc = _make_ec(status="Submitted")
        with self.assertRaises(frappe.ValidationError):
            doc.mark_paid()

    def test_sets_status_paid(self):
        doc = _make_ec(status="Approved")
        doc.mark_paid()
        doc.db_set.assert_called_once_with("status", "Paid")


if __name__ == "__main__":
    unittest.main()