"""
Tests for assets/asset_gl.py — capitalization, CWIP transfer, and reversal
GL posting. Frappe DB/GL calls are mocked; no bench/DB needed.

Run with:
    bench run-tests --app zoho_books_clone --module zoho_books_clone.assets.tests.test_asset_gl
"""

import unittest
from unittest.mock import MagicMock, patch

from zoho_books_clone.assets import asset_gl


def _make_asset_doc(**overrides):
    doc = MagicMock()
    doc.name = "AST-0001"
    doc.asset_name = "Bottling Machine"
    doc.asset_category = "Machinery"
    doc.company = "VK Herbal"
    doc.purchase_cost = 100000
    doc.purchase_date = "2026-01-01"
    doc.available_for_use_date = "2026-01-01"
    doc.credit_account = "Creditors - VK"
    doc.is_existing_asset = 0
    doc.capitalization_posted = 0
    doc.cwip_transferred = 0
    for k, v in overrides.items():
        setattr(doc, k, v)
    return doc


class TestValidateCapitalizationSetup(unittest.TestCase):

    def test_existing_asset_skips_validation(self):
        doc = _make_asset_doc(is_existing_asset=1, company=None)
        # Should not raise even though company is missing.
        asset_gl.validate_capitalization_setup(doc)

    def test_missing_company_throws(self):
        doc = _make_asset_doc(company=None)
        with self.assertRaises(Exception):
            asset_gl.validate_capitalization_setup(doc)

    @patch("zoho_books_clone.assets.asset_gl.get_category_accounts")
    def test_missing_fixed_asset_account_throws(self, mock_accounts):
        mock_accounts.return_value = {}
        doc = _make_asset_doc()
        with self.assertRaises(Exception):
            asset_gl.validate_capitalization_setup(doc)

    @patch("zoho_books_clone.assets.asset_gl.get_category_accounts")
    def test_missing_credit_account_throws(self, mock_accounts):
        mock_accounts.return_value = {"fixed_asset_account": "Fixed Assets - VK"}
        doc = _make_asset_doc(credit_account=None)
        with self.assertRaises(Exception):
            asset_gl.validate_capitalization_setup(doc)

    @patch("zoho_books_clone.assets.asset_gl.get_category_accounts")
    def test_fully_configured_passes(self, mock_accounts):
        mock_accounts.return_value = {"fixed_asset_account": "Fixed Assets - VK"}
        doc = _make_asset_doc()
        asset_gl.validate_capitalization_setup(doc)  # should not raise


class TestPostAssetCapitalization(unittest.TestCase):

    @patch("zoho_books_clone.assets.asset_gl.make_gl_entries")
    @patch("zoho_books_clone.assets.asset_gl.get_category_accounts")
    def test_posts_debit_fixed_asset_credit_credit_account(self, mock_accounts, mock_gl):
        mock_accounts.return_value = {"fixed_asset_account": "Fixed Assets - VK"}
        doc = _make_asset_doc()
        asset_gl.post_asset_capitalization(doc)

        mock_gl.assert_called_once()
        gl_map = mock_gl.call_args[0][0]
        self.assertEqual(len(gl_map), 2)

        debit_lines = [r for r in gl_map if r["debit"] > 0]
        credit_lines = [r for r in gl_map if r["credit"] > 0]
        self.assertEqual(debit_lines[0]["account"], "Fixed Assets - VK")
        self.assertEqual(debit_lines[0]["debit"], 100000)
        self.assertEqual(credit_lines[0]["account"], "Creditors - VK")
        self.assertEqual(credit_lines[0]["credit"], 100000)
        self.assertEqual(sum(r["debit"] for r in gl_map), sum(r["credit"] for r in gl_map))

        doc.db_set.assert_any_call("capitalization_posted", 1, update_modified=False)
        doc.db_set.assert_any_call("cwip_transferred", 1, update_modified=False)

    @patch("zoho_books_clone.assets.asset_gl.make_gl_entries")
    @patch("zoho_books_clone.assets.asset_gl.get_category_accounts")
    def test_routes_to_cwip_when_not_yet_available_for_use(self, mock_accounts, mock_gl):
        mock_accounts.return_value = {
            "fixed_asset_account": "Fixed Assets - VK",
            "cwip_account": "CWIP - VK",
        }
        doc = _make_asset_doc(purchase_date="2026-01-01", available_for_use_date="2026-06-01")
        asset_gl.post_asset_capitalization(doc)

        gl_map = mock_gl.call_args[0][0]
        debit_lines = [r for r in gl_map if r["debit"] > 0]
        self.assertEqual(debit_lines[0]["account"], "CWIP - VK")
        doc.db_set.assert_any_call("cwip_transferred", 0, update_modified=False)

    def test_existing_asset_skips_posting_entirely(self):
        doc = _make_asset_doc(is_existing_asset=1)
        with patch("zoho_books_clone.assets.asset_gl.make_gl_entries") as mock_gl:
            asset_gl.post_asset_capitalization(doc)
            mock_gl.assert_not_called()
            doc.db_set.assert_not_called()

    def test_already_posted_is_idempotent(self):
        doc = _make_asset_doc(capitalization_posted=1)
        with patch("zoho_books_clone.assets.asset_gl.make_gl_entries") as mock_gl:
            asset_gl.post_asset_capitalization(doc)
            mock_gl.assert_not_called()

    @patch("zoho_books_clone.assets.asset_gl.get_category_accounts")
    def test_zero_purchase_cost_throws(self, mock_accounts):
        mock_accounts.return_value = {"fixed_asset_account": "Fixed Assets - VK"}
        doc = _make_asset_doc(purchase_cost=0)
        with self.assertRaises(Exception):
            asset_gl.post_asset_capitalization(doc)


class TestTransferCwipToFixedAsset(unittest.TestCase):

    @patch("zoho_books_clone.assets.asset_gl.make_gl_entries")
    @patch("zoho_books_clone.assets.asset_gl.get_category_accounts")
    @patch("zoho_books_clone.assets.asset_gl.frappe")
    def test_transfers_when_due(self, mock_frappe, mock_accounts, mock_gl):
        doc = _make_asset_doc(capitalization_posted=1, cwip_transferred=0,
                               available_for_use_date="2020-01-01")
        mock_frappe.get_doc.return_value = doc
        mock_frappe.utils.nowdate.return_value = "2026-01-01"
        mock_accounts.return_value = {
            "fixed_asset_account": "Fixed Assets - VK",
            "cwip_account": "CWIP - VK",
        }
        result = asset_gl.transfer_cwip_to_fixed_asset("AST-0001")
        self.assertTrue(result)
        gl_map = mock_gl.call_args[0][0]
        debit_lines = [r for r in gl_map if r["debit"] > 0]
        credit_lines = [r for r in gl_map if r["credit"] > 0]
        self.assertEqual(debit_lines[0]["account"], "Fixed Assets - VK")
        self.assertEqual(credit_lines[0]["account"], "CWIP - VK")
        doc.db_set.assert_any_call("cwip_transferred", 1, update_modified=False)

    @patch("zoho_books_clone.assets.asset_gl.make_gl_entries")
    @patch("zoho_books_clone.assets.asset_gl.frappe")
    def test_no_op_if_not_yet_capitalized(self, mock_frappe, mock_gl):
        doc = _make_asset_doc(capitalization_posted=0, cwip_transferred=0)
        mock_frappe.get_doc.return_value = doc
        result = asset_gl.transfer_cwip_to_fixed_asset("AST-0001")
        self.assertFalse(result)
        mock_gl.assert_not_called()

    @patch("zoho_books_clone.assets.asset_gl.make_gl_entries")
    @patch("zoho_books_clone.assets.asset_gl.frappe")
    def test_no_op_if_already_transferred(self, mock_frappe, mock_gl):
        doc = _make_asset_doc(capitalization_posted=1, cwip_transferred=1)
        mock_frappe.get_doc.return_value = doc
        result = asset_gl.transfer_cwip_to_fixed_asset("AST-0001")
        self.assertFalse(result)
        mock_gl.assert_not_called()


class TestReverseAssetCapitalization(unittest.TestCase):

    @patch("zoho_books_clone.assets.asset_gl.make_gl_entries")
    def test_reverses_capitalization_leg_only(self, mock_gl):
        doc = _make_asset_doc(capitalization_posted=1, cwip_transferred=0)
        asset_gl.reverse_asset_capitalization(doc)
        self.assertEqual(mock_gl.call_count, 1)  # only the capitalization leg
        _, kwargs = mock_gl.call_args
        self.assertTrue(kwargs.get("cancel"))
        doc.db_set.assert_any_call("capitalization_posted", 0, update_modified=False)

    @patch("zoho_books_clone.assets.asset_gl.make_gl_entries")
    def test_reverses_both_legs_when_cwip_transferred(self, mock_gl):
        doc = _make_asset_doc(capitalization_posted=1, cwip_transferred=1)
        asset_gl.reverse_asset_capitalization(doc)
        self.assertEqual(mock_gl.call_count, 2)  # CWIP transfer leg + capitalization leg

    @patch("zoho_books_clone.assets.asset_gl.make_gl_entries")
    def test_no_op_if_never_posted(self, mock_gl):
        doc = _make_asset_doc(capitalization_posted=0)
        asset_gl.reverse_asset_capitalization(doc)
        mock_gl.assert_not_called()
        doc.db_set.assert_not_called()

    @patch("zoho_books_clone.assets.asset_gl.frappe")
    @patch("zoho_books_clone.assets.asset_gl.make_gl_entries")
    def test_gl_failure_does_not_raise_and_logs(self, mock_gl, mock_frappe):
        """Best-effort reversal -- a GL-side failure must not block cancel."""
        mock_gl.side_effect = Exception("GL boom")
        doc = _make_asset_doc(capitalization_posted=1, cwip_transferred=0)
        asset_gl.reverse_asset_capitalization(doc)  # should not raise
        mock_frappe.log_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()