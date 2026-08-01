"""
Tests for assets/asset_disposal_gl.py -- Scrap/Sale disposal GL posting,
gain/loss computation, and reversal on cancel.

Run with:
    bench run-tests --app zoho_books_clone --module zoho_books_clone.assets.tests.test_asset_disposal_gl
"""

import unittest
from unittest.mock import MagicMock, patch

from zoho_books_clone.assets import asset_disposal_gl


class _AttrDict(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            return None


def _asset_row(**overrides):
    row = {
        "docstatus": 1,
        "status": "Submitted",
        "asset_category": "Machinery",
        "company": "VK Herbal",
        "is_existing_asset": 0,
        "current_value": 40000,
        "purchase_cost": 100000,
    }
    row.update(overrides)
    return _AttrDict(row)


def _make_disposal_doc(**overrides):
    doc = MagicMock()
    doc.name = "ASTDIS-0001"
    doc.asset = "AST-0001"
    doc.disposal_type = "Scrap"
    doc.disposal_date = "2026-07-01"
    doc.gain_loss_account = "Gain/Loss on Disposal - VK"
    doc.receivable_account = None
    doc.sale_amount = 0
    doc.gl_posted = 0
    for k, v in overrides.items():
        setattr(doc, k, v)
    return doc


class TestValidateDisposalSetup(unittest.TestCase):

    @patch("frappe.db.get_value")
    def test_unsubmitted_asset_throws(self, mock_get_value):
        mock_get_value.return_value = _asset_row(docstatus=0)
        doc = _make_disposal_doc()
        with self.assertRaises(Exception):
            asset_disposal_gl.validate_disposal_setup(doc)

    @patch("frappe.db.get_value")
    def test_already_disposed_throws(self, mock_get_value):
        mock_get_value.return_value = _asset_row(status="Scrapped")
        doc = _make_disposal_doc()
        with self.assertRaises(Exception):
            asset_disposal_gl.validate_disposal_setup(doc)

    @patch("frappe.db.get_value")
    def test_missing_gain_loss_account_throws(self, mock_get_value):
        mock_get_value.return_value = _asset_row()
        doc = _make_disposal_doc(gain_loss_account=None)
        with self.assertRaises(Exception):
            asset_disposal_gl.validate_disposal_setup(doc)

    @patch("zoho_books_clone.assets.asset_disposal_gl.get_category_accounts")
    @patch("frappe.db.get_value")
    def test_sale_without_receivable_account_throws(self, mock_get_value, mock_accounts):
        mock_get_value.return_value = _asset_row()
        mock_accounts.return_value = {
            "fixed_asset_account": "Fixed Assets - VK",
            "accumulated_depreciation_account": "Accum Dep - VK",
        }
        doc = _make_disposal_doc(disposal_type="Sale", sale_amount=50000, receivable_account=None)
        with self.assertRaises(Exception):
            asset_disposal_gl.validate_disposal_setup(doc)

    @patch("zoho_books_clone.assets.asset_disposal_gl.get_category_accounts")
    @patch("frappe.db.get_value")
    def test_missing_category_accounts_throws(self, mock_get_value, mock_accounts):
        mock_get_value.return_value = _asset_row()
        mock_accounts.return_value = {}
        doc = _make_disposal_doc()
        with self.assertRaises(Exception):
            asset_disposal_gl.validate_disposal_setup(doc)

    @patch("zoho_books_clone.assets.asset_disposal_gl.get_category_accounts")
    @patch("frappe.db.get_value")
    def test_existing_asset_skips_category_account_check(self, mock_get_value, mock_accounts):
        """is_existing_asset assets never had a capitalization entry, so no
        Fixed Asset / Accum Dep accounts are required to dispose them."""
        mock_get_value.return_value = _asset_row(is_existing_asset=1)
        doc = _make_disposal_doc()
        asset_disposal_gl.validate_disposal_setup(doc)  # should not raise
        mock_accounts.assert_not_called()


class TestPostDisposalGlScrap(unittest.TestCase):

    def _asset_doc(self, **overrides):
        doc = MagicMock()
        doc.name = "AST-0001"
        doc.asset_name = "Bottling Machine"
        doc.asset_category = "Machinery"
        doc.company = "VK Herbal"
        doc.status = "Submitted"
        doc.is_existing_asset = 0
        doc.purchase_cost = 100000
        doc.current_value = 40000
        for k, v in overrides.items():
            setattr(doc, k, v)
        return doc

    @patch("zoho_books_clone.assets.asset_disposal_gl.make_gl_entries")
    @patch("zoho_books_clone.assets.asset_disposal_gl.get_category_accounts")
    @patch("zoho_books_clone.assets.asset_disposal_gl.frappe")
    def test_scrap_posts_balanced_entry_full_loss(self, mock_frappe, mock_accounts, mock_gl):
        """Scrap = no proceeds, so the entire NBV is a loss."""
        asset = self._asset_doc()
        mock_frappe.get_doc.return_value = asset
        mock_accounts.return_value = {
            "fixed_asset_account": "Fixed Assets - VK",
            "accumulated_depreciation_account": "Accum Dep - VK",
        }
        doc = _make_disposal_doc(disposal_type="Scrap")
        asset_disposal_gl.post_disposal_gl(doc)

        gl_map = mock_gl.call_args[0][0]
        total_debit = sum(r["debit"] for r in gl_map)
        total_credit = sum(r["credit"] for r in gl_map)
        self.assertAlmostEqual(total_debit, total_credit)

        by_account = {r["account"]: (r["debit"], r["credit"]) for r in gl_map}
        self.assertEqual(by_account["Accum Dep - VK"], (60000, 0))       # 100000-40000
        self.assertEqual(by_account["Fixed Assets - VK"], (0, 100000))
        # Full loss = NBV (40000), booked as a debit to gain/loss.
        self.assertEqual(by_account["Gain/Loss on Disposal - VK"], (40000, 0))

        asset.db_set.assert_any_call("status", "Scrapped", update_modified=False)
        asset.db_set.assert_any_call("is_active", 0, update_modified=False)

    @patch("zoho_books_clone.assets.asset_disposal_gl.make_gl_entries")
    @patch("zoho_books_clone.assets.asset_disposal_gl.get_category_accounts")
    @patch("zoho_books_clone.assets.asset_disposal_gl.frappe")
    def test_sale_above_nbv_books_a_gain(self, mock_frappe, mock_accounts, mock_gl):
        asset = self._asset_doc(current_value=40000)
        mock_frappe.get_doc.return_value = asset
        mock_accounts.return_value = {
            "fixed_asset_account": "Fixed Assets - VK",
            "accumulated_depreciation_account": "Accum Dep - VK",
        }
        doc = _make_disposal_doc(disposal_type="Sale", sale_amount=55000,
                                  receivable_account="Debtors - VK")
        asset_disposal_gl.post_disposal_gl(doc)

        gl_map = mock_gl.call_args[0][0]
        total_debit = sum(r["debit"] for r in gl_map)
        total_credit = sum(r["credit"] for r in gl_map)
        self.assertAlmostEqual(total_debit, total_credit)

        by_account = {r["account"]: (r["debit"], r["credit"]) for r in gl_map}
        self.assertEqual(by_account["Debtors - VK"], (55000, 0))
        # Gain = 55000 - 40000 = 15000, booked as a credit.
        self.assertEqual(by_account["Gain/Loss on Disposal - VK"], (0, 15000))
        self.assertEqual(doc.gain_loss_amount, 15000)

        asset.db_set.assert_any_call("status", "Sold", update_modified=False)

    @patch("zoho_books_clone.assets.asset_disposal_gl.make_gl_entries")
    @patch("zoho_books_clone.assets.asset_disposal_gl.get_category_accounts")
    @patch("zoho_books_clone.assets.asset_disposal_gl.frappe")
    def test_sale_below_nbv_books_a_loss(self, mock_frappe, mock_accounts, mock_gl):
        asset = self._asset_doc(current_value=40000)
        mock_frappe.get_doc.return_value = asset
        mock_accounts.return_value = {
            "fixed_asset_account": "Fixed Assets - VK",
            "accumulated_depreciation_account": "Accum Dep - VK",
        }
        doc = _make_disposal_doc(disposal_type="Sale", sale_amount=25000,
                                  receivable_account="Debtors - VK")
        asset_disposal_gl.post_disposal_gl(doc)

        gl_map = mock_gl.call_args[0][0]
        by_account = {r["account"]: (r["debit"], r["credit"]) for r in gl_map}
        # Loss = 25000 - 40000 = -15000 -> debit gain/loss for 15000.
        self.assertEqual(by_account["Gain/Loss on Disposal - VK"], (15000, 0))
        self.assertEqual(doc.gain_loss_amount, -15000)

    @patch("zoho_books_clone.assets.asset_disposal_gl.make_gl_entries")
    @patch("zoho_books_clone.assets.asset_disposal_gl.frappe")
    def test_existing_asset_updates_status_without_gl(self, mock_frappe, mock_gl):
        """is_existing_asset assets skip GL entirely -- status flip only."""
        asset = self._asset_doc(is_existing_asset=1, current_value=40000)
        mock_frappe.get_doc.return_value = asset
        doc = _make_disposal_doc(disposal_type="Scrap")
        asset_disposal_gl.post_disposal_gl(doc)
        mock_gl.assert_not_called()
        asset.db_set.assert_any_call("status", "Scrapped", update_modified=False)

    @patch("zoho_books_clone.assets.asset_disposal_gl.make_gl_entries")
    def test_already_posted_is_idempotent(self, mock_gl):
        doc = _make_disposal_doc(gl_posted=1)
        asset_disposal_gl.post_disposal_gl(doc)
        mock_gl.assert_not_called()


class TestReverseDisposalGl(unittest.TestCase):

    @patch("zoho_books_clone.assets.asset_disposal_gl.make_gl_entries")
    @patch("zoho_books_clone.assets.asset_disposal_gl.frappe")
    def test_reverses_gl_and_restores_asset_status(self, mock_frappe, mock_gl):
        asset = MagicMock()
        asset.is_existing_asset = 0
        mock_frappe.get_doc.return_value = asset
        doc = _make_disposal_doc(gl_posted=1, previous_asset_status="Submitted")
        asset_disposal_gl.reverse_disposal_gl(doc)

        mock_gl.assert_called_once()
        _, kwargs = mock_gl.call_args
        self.assertTrue(kwargs.get("cancel"))
        asset.db_set.assert_any_call("status", "Submitted", update_modified=False)
        asset.db_set.assert_any_call("is_active", 1, update_modified=False)
        doc.db_set.assert_any_call("gl_posted", 0, update_modified=False)

    @patch("zoho_books_clone.assets.asset_disposal_gl.make_gl_entries")
    @patch("zoho_books_clone.assets.asset_disposal_gl.frappe")
    def test_existing_asset_reversal_skips_gl_call(self, mock_frappe, mock_gl):
        asset = MagicMock()
        asset.is_existing_asset = 1
        mock_frappe.get_doc.return_value = asset
        doc = _make_disposal_doc(gl_posted=1, previous_asset_status="Submitted")
        asset_disposal_gl.reverse_disposal_gl(doc)
        mock_gl.assert_not_called()

    @patch("zoho_books_clone.assets.asset_disposal_gl.make_gl_entries")
    def test_no_op_if_never_posted(self, mock_gl):
        doc = _make_disposal_doc(gl_posted=0)
        asset_disposal_gl.reverse_disposal_gl(doc)
        mock_gl.assert_not_called()

    @patch("zoho_books_clone.assets.asset_disposal_gl.frappe")
    @patch("zoho_books_clone.assets.asset_disposal_gl.make_gl_entries")
    def test_gl_failure_does_not_raise_and_logs(self, mock_gl, mock_frappe):
        mock_gl.side_effect = Exception("GL boom")
        mock_frappe.get_doc.side_effect = Exception("nested boom too")
        doc = _make_disposal_doc(gl_posted=1)
        asset_disposal_gl.reverse_disposal_gl(doc)  # should not raise
        mock_frappe.log_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()