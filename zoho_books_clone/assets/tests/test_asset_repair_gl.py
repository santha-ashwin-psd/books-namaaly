"""
Tests for assets/asset_repair_gl.py -- capitalized vs. expensed repair GL
posting, the purchase_cost/current_value bump on capitalization, and
reversal on cancel.

Run with:
    bench run-tests --app zoho_books_clone --module zoho_books_clone.assets.tests.test_asset_repair_gl
"""

import unittest
from unittest.mock import MagicMock, patch

from zoho_books_clone.assets import asset_repair_gl


class _AttrDict(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            return None


def _make_repair_doc(**overrides):
    doc = MagicMock()
    doc.name = "ASTREP-0001"
    doc.asset = "AST-0001"
    doc.repair_date = "2026-07-01"
    doc.repair_cost = 5000
    doc.credit_account = "Creditors - VK"
    doc.is_capitalized = 0
    doc.expense_account = "Repairs & Maintenance - VK"
    doc.gl_posted = 0
    doc.capitalized_amount_applied = 0
    for k, v in overrides.items():
        setattr(doc, k, v)
    return doc


def _make_asset_doc(**overrides):
    doc = MagicMock()
    doc.name = "AST-0001"
    doc.asset_name = "Bottling Machine"
    doc.asset_category = "Machinery"
    doc.company = "VK Herbal"
    doc.purchase_cost = 100000
    doc.current_value = 60000
    for k, v in overrides.items():
        setattr(doc, k, v)
    return doc


class TestValidateRepairSetup(unittest.TestCase):

    def test_no_asset_is_a_no_op(self):
        doc = _make_repair_doc(asset=None)
        asset_repair_gl.validate_repair_setup(doc)  # should not raise

    def test_missing_credit_account_throws(self):
        doc = _make_repair_doc(credit_account=None)
        with self.assertRaises(Exception):
            asset_repair_gl.validate_repair_setup(doc)

    def test_expensed_without_expense_account_throws(self):
        doc = _make_repair_doc(is_capitalized=0, expense_account=None)
        with self.assertRaises(Exception):
            asset_repair_gl.validate_repair_setup(doc)

    def test_expensed_with_expense_account_passes(self):
        doc = _make_repair_doc(is_capitalized=0, expense_account="Repairs - VK")
        asset_repair_gl.validate_repair_setup(doc)  # should not raise

    @patch("zoho_books_clone.assets.asset_repair_gl.get_category_accounts")
    @patch("frappe.db.get_value")
    def test_capitalized_without_fixed_asset_account_throws(self, mock_get_value, mock_accounts):
        mock_get_value.return_value = _AttrDict({"asset_category": "Machinery", "company": "VK Herbal"})
        mock_accounts.return_value = {}
        doc = _make_repair_doc(is_capitalized=1)
        with self.assertRaises(Exception):
            asset_repair_gl.validate_repair_setup(doc)

    @patch("zoho_books_clone.assets.asset_repair_gl.get_category_accounts")
    @patch("frappe.db.get_value")
    def test_capitalized_with_fixed_asset_account_passes(self, mock_get_value, mock_accounts):
        mock_get_value.return_value = _AttrDict({"asset_category": "Machinery", "company": "VK Herbal"})
        mock_accounts.return_value = {"fixed_asset_account": "Fixed Assets - VK"}
        doc = _make_repair_doc(is_capitalized=1)
        asset_repair_gl.validate_repair_setup(doc)  # should not raise

    @patch("frappe.db.get_value")
    def test_capitalized_asset_not_found_throws(self, mock_get_value):
        mock_get_value.return_value = None
        doc = _make_repair_doc(is_capitalized=1)
        with self.assertRaises(Exception):
            asset_repair_gl.validate_repair_setup(doc)


class TestPostRepairGl(unittest.TestCase):

    @patch("zoho_books_clone.assets.asset_repair_gl.make_gl_entries")
    @patch("zoho_books_clone.assets.asset_repair_gl.frappe")
    def test_expensed_repair_debits_expense_account(self, mock_frappe, mock_gl):
        asset = _make_asset_doc()
        mock_frappe.get_doc.return_value = asset
        doc = _make_repair_doc(is_capitalized=0, expense_account="Repairs & Maintenance - VK")
        asset_repair_gl.post_repair_gl(doc)

        gl_map = mock_gl.call_args[0][0]
        total_debit = sum(r["debit"] for r in gl_map)
        total_credit = sum(r["credit"] for r in gl_map)
        self.assertEqual(total_debit, total_credit)

        by_account = {r["account"]: (r["debit"], r["credit"]) for r in gl_map}
        self.assertEqual(by_account["Repairs & Maintenance - VK"], (5000, 0))
        self.assertEqual(by_account["Creditors - VK"], (0, 5000))

        # Expensed repair must NOT touch the asset's cost/value.
        asset.db_set.assert_not_called()
        doc.db_set.assert_any_call("gl_posted", 1, update_modified=False)

    @patch("zoho_books_clone.assets.asset_repair_gl.get_category_accounts")
    @patch("zoho_books_clone.assets.asset_repair_gl.make_gl_entries")
    @patch("zoho_books_clone.assets.asset_repair_gl.frappe")
    def test_capitalized_repair_debits_fixed_asset_and_bumps_asset_value(self, mock_frappe, mock_gl, mock_accounts):
        asset = _make_asset_doc(purchase_cost=100000, current_value=60000)
        mock_frappe.get_doc.return_value = asset
        mock_accounts.return_value = {"fixed_asset_account": "Fixed Assets - VK"}
        doc = _make_repair_doc(is_capitalized=1, repair_cost=8000)
        asset_repair_gl.post_repair_gl(doc)

        gl_map = mock_gl.call_args[0][0]
        by_account = {r["account"]: (r["debit"], r["credit"]) for r in gl_map}
        self.assertEqual(by_account["Fixed Assets - VK"], (8000, 0))
        self.assertEqual(by_account["Creditors - VK"], (0, 8000))

        asset.db_set.assert_any_call("purchase_cost", 108000, update_modified=False)
        asset.db_set.assert_any_call("current_value", 68000, update_modified=False)
        doc.db_set.assert_any_call("capitalized_amount_applied", 1, update_modified=False)

    @patch("zoho_books_clone.assets.asset_repair_gl.make_gl_entries")
    def test_already_posted_is_idempotent(self, mock_gl):
        doc = _make_repair_doc(gl_posted=1)
        asset_repair_gl.post_repair_gl(doc)
        mock_gl.assert_not_called()

    def test_zero_repair_cost_throws(self):
        doc = _make_repair_doc(repair_cost=0)
        with self.assertRaises(Exception):
            asset_repair_gl.post_repair_gl(doc)


class TestReverseRepairGl(unittest.TestCase):

    @patch("zoho_books_clone.assets.asset_repair_gl.make_gl_entries")
    def test_no_op_if_never_posted(self, mock_gl):
        doc = _make_repair_doc(gl_posted=0)
        asset_repair_gl.reverse_repair_gl(doc)
        mock_gl.assert_not_called()

    @patch("zoho_books_clone.assets.asset_repair_gl.make_gl_entries")
    def test_expensed_reversal_does_not_touch_asset(self, mock_gl):
        doc = _make_repair_doc(gl_posted=1, capitalized_amount_applied=0)
        with patch("zoho_books_clone.assets.asset_repair_gl.frappe") as mock_frappe:
            asset_repair_gl.reverse_repair_gl(doc)
            mock_frappe.get_doc.assert_not_called()
        doc.db_set.assert_any_call("gl_posted", 0, update_modified=False)

    @patch("zoho_books_clone.assets.asset_repair_gl.make_gl_entries")
    @patch("zoho_books_clone.assets.asset_repair_gl.frappe")
    def test_capitalized_reversal_undoes_asset_value_bump(self, mock_frappe, mock_gl):
        asset = _make_asset_doc(purchase_cost=108000, current_value=68000)
        mock_frappe.get_doc.return_value = asset
        doc = _make_repair_doc(gl_posted=1, capitalized_amount_applied=1, repair_cost=8000)
        asset_repair_gl.reverse_repair_gl(doc)

        asset.db_set.assert_any_call("purchase_cost", 100000, update_modified=False)
        asset.db_set.assert_any_call("current_value", 60000, update_modified=False)
        doc.db_set.assert_any_call("capitalized_amount_applied", 0, update_modified=False)

    @patch("zoho_books_clone.assets.asset_repair_gl.frappe")
    @patch("zoho_books_clone.assets.asset_repair_gl.make_gl_entries")
    def test_gl_failure_does_not_raise_and_logs(self, mock_gl, mock_frappe):
        mock_gl.side_effect = Exception("GL boom")
        doc = _make_repair_doc(gl_posted=1)
        asset_repair_gl.reverse_repair_gl(doc)  # should not raise
        mock_frappe.log_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()