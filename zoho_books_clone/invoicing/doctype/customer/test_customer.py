# Copyright (c) 2026, PS Digitise and Contributors
# See license.txt
"""
Tests for Customer (invoicing/doctype/customer/customer.py) -- validate()
guards (required name, email format, GSTIN format + normalization, the
opening-balance-edit guard once already-posted), the on_update opening
balance GL sync (with its deliberate non-blocking failure handling), and
on_trash's delete guard.

Same bind-real-method-onto-a-stand-in pattern as the other doctype test
suites -- DB-free, exercises the actual controller code.

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.invoicing.doctype.customer.test_customer
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe

from zoho_books_clone.invoicing.doctype.customer.customer import Customer


class _Dict(SimpleNamespace):
    def get(self, key, default=None):
        return getattr(self, key, default)


def _make_customer(customer_name="Acme Herbal Traders", email_id=None, tax_id=None,
                    is_new=False, changed_fields=None, **overrides):
    doc = _Dict(
        doctype="Customer", name="CUST-0001", customer_name=customer_name,
        email_id=email_id, tax_id=tax_id, books_company="VK Herbal",
    )
    doc.is_new = MagicMock(return_value=is_new)
    _changed = set(changed_fields or [])
    doc.has_value_changed = MagicMock(side_effect=lambda f: f in _changed)
    for k, v in overrides.items():
        setattr(doc, k, v)
    for name in ("validate", "after_insert", "on_update", "on_trash"):
        setattr(doc, name, getattr(Customer, name).__get__(doc))
    return doc


class TestValidateBasics(unittest.TestCase):

    def test_throws_without_customer_name(self):
        doc = _make_customer(customer_name=None)
        with self.assertRaises(frappe.ValidationError):
            doc.validate()

    def test_throws_on_malformed_email(self):
        doc = _make_customer(email_id="not-an-email")
        with self.assertRaises(frappe.ValidationError):
            doc.validate()

    def test_valid_email_passes(self):
        doc = _make_customer(email_id="ap@acmeherbal.test")
        doc.validate()  # should not raise

    def test_blank_email_is_fine(self):
        doc = _make_customer(email_id=None)
        doc.validate()  # should not raise


class TestValidateGstin(unittest.TestCase):

    def test_valid_gstin_passes_and_is_normalized(self):
        doc = _make_customer(tax_id=" 29abcde1234f1z5 ")
        doc.validate()
        self.assertEqual(doc.tax_id, "29ABCDE1234F1Z5")

    def test_malformed_gstin_throws(self):
        doc = _make_customer(tax_id="NOT-A-GSTIN")
        with self.assertRaises(frappe.ValidationError):
            doc.validate()

    def test_wrong_length_gstin_throws(self):
        doc = _make_customer(tax_id="29ABCDE1234F1Z")  # one char short
        with self.assertRaises(frappe.ValidationError):
            doc.validate()

    def test_blank_gstin_skips_check(self):
        doc = _make_customer(tax_id=None)
        doc.validate()  # should not raise


class TestOpeningBalanceEditGuard(unittest.TestCase):

    @patch("zoho_books_clone.accounts.opening_balance.guard_opening_balance_edit")
    def test_guard_called_when_opening_balance_changed_on_existing_customer(self, mock_guard):
        doc = _make_customer(is_new=False, changed_fields=["opening_balance"])
        doc.validate()
        mock_guard.assert_called_once_with("Customer", "CUST-0001")

    @patch("zoho_books_clone.accounts.opening_balance.guard_opening_balance_edit")
    def test_guard_skipped_for_new_customer(self, mock_guard):
        doc = _make_customer(is_new=True, changed_fields=["opening_balance"])
        doc.validate()
        mock_guard.assert_not_called()

    @patch("zoho_books_clone.accounts.opening_balance.guard_opening_balance_edit")
    def test_guard_skipped_when_opening_balance_unchanged(self, mock_guard):
        doc = _make_customer(is_new=False, changed_fields=[])
        doc.validate()
        mock_guard.assert_not_called()

    @patch("zoho_books_clone.accounts.opening_balance.guard_opening_balance_edit",
           side_effect=frappe.ValidationError("payment already recorded against opening JE"))
    def test_guard_violation_blocks_save(self, mock_guard):
        doc = _make_customer(is_new=False, changed_fields=["opening_balance"])
        with self.assertRaises(frappe.ValidationError):
            doc.validate()


class TestOnUpdateOpeningBalanceSync(unittest.TestCase):

    @patch("zoho_books_clone.accounts.opening_balance.sync_party_opening_balance")
    def test_syncs_when_opening_balance_changed(self, mock_sync):
        doc = _make_customer(changed_fields=["opening_balance"])
        doc.on_update()
        mock_sync.assert_called_once_with("Customer", "CUST-0001", "VK Herbal")

    @patch("zoho_books_clone.accounts.opening_balance.sync_party_opening_balance")
    def test_noop_when_opening_balance_unchanged(self, mock_sync):
        doc = _make_customer(changed_fields=[])
        doc.on_update()
        mock_sync.assert_not_called()

    @patch.object(frappe, "msgprint")
    @patch.object(frappe, "log_error")
    @patch("zoho_books_clone.accounts.opening_balance.sync_party_opening_balance",
           side_effect=Exception("chart of accounts not set up"))
    def test_sync_failure_does_not_block_save(self, mock_sync, mock_log_error, mock_msgprint):
        # Deliberate: a company without a full chart of accounts must still
        # be able to save the Customer -- the failure is logged and
        # surfaced as a non-blocking alert, not raised.
        doc = _make_customer(changed_fields=["opening_balance"])
        doc.on_update()  # should not raise
        mock_log_error.assert_called_once()
        mock_msgprint.assert_called_once()


class TestOnTrash(unittest.TestCase):

    @patch("zoho_books_clone.accounts.opening_balance.guard_opening_balance_delete")
    def test_delegates_to_delete_guard(self, mock_guard):
        doc = _make_customer()
        doc.on_trash()
        mock_guard.assert_called_once_with("Customer", "CUST-0001")

    @patch("zoho_books_clone.accounts.opening_balance.guard_opening_balance_delete",
           side_effect=frappe.ValidationError("active opening balance entry"))
    def test_delete_blocked_when_guard_raises(self, mock_guard):
        doc = _make_customer()
        with self.assertRaises(frappe.ValidationError):
            doc.on_trash()


if __name__ == "__main__":
    unittest.main()