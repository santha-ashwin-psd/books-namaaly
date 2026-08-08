"""
Tests for assets/asset_value_adjustment_gl.py -- impairment (write-down)
vs. revaluation (write-up) GL posting against the Accumulated
Depreciation Account, the Asset.current_value bump/undo, and reversal
on cancel.

Run with:
    bench run-tests --app zoho_books_clone --module zoho_books_clone.assets.tests.test_asset_value_adjustment_gl
"""

import unittest
from unittest.mock import MagicMock, patch

from zoho_books_clone.assets import asset_value_adjustment_gl


class _AttrDict(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            return None


def _make_adjustment_doc(**overrides):
    doc = MagicMock()
    doc.name = "ASTADJ-0001"
    doc.asset = "AST-0001"
    doc.adjustment_date = "2026-07-01"
    doc.adjustment_type = "Impairment (Write-down)"
    doc.new_value = 50000
    doc.adjustment_account = "Impairment Loss - VK"
    doc.gl_posted = 0
    doc.current_value_before = None
    doc.adjustment_amount = None
    for k, v in overrides.items():
        setattr(doc, k, v)
    return doc


def _make_asset_row(**overrides):
    """What frappe.db.get_value(..., as_dict=True) returns inside validate_adjustment_setup."""
    row = _AttrDict(
        docstatus=1,
        status="Submitted",
        asset_category="Machinery",
        company="VK Herbal",
        purchase_cost=100000,
        current_value=60000,
    )
    row.update(overrides)
    return row


def _make_asset_doc(**overrides):
    """What frappe.get_doc("Asset", ...) returns inside post/reverse."""
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


class TestValidateAdjustmentSetup(unittest.TestCase):

    def test_no_asset_is_a_no_op(self):
        doc = _make_adjustment_doc(asset=None)
        asset_value_adjustment_gl.validate_adjustment_setup(doc)  # should not raise

    @patch("frappe.db.get_value")
    def test_asset_not_found_throws(self, mock_get_value):
        mock_get_value.return_value = None
        doc = _make_adjustment_doc()
        with self.assertRaises(Exception):
            asset_value_adjustment_gl.validate_adjustment_setup(doc)

    @patch("frappe.db.get_value")
    def test_unsubmitted_asset_throws(self, mock_get_value):
        mock_get_value.return_value = _make_asset_row(docstatus=0)
        doc = _make_adjustment_doc()
        with self.assertRaises(Exception):
            asset_value_adjustment_gl.validate_adjustment_setup(doc)

    @patch("frappe.db.get_value")
    def test_disposed_asset_throws(self, mock_get_value):
        mock_get_value.return_value = _make_asset_row(status="Scrapped")
        doc = _make_adjustment_doc()
        with self.assertRaises(Exception):
            asset_value_adjustment_gl.validate_adjustment_setup(doc)

    @patch("frappe.db.get_value")
    def test_negative_new_value_throws(self, mock_get_value):
        mock_get_value.return_value = _make_asset_row()
        doc = _make_adjustment_doc(new_value=-1)
        with self.assertRaises(Exception):
            asset_value_adjustment_gl.validate_adjustment_setup(doc)

    @patch("frappe.db.get_value")
    def test_new_value_above_purchase_cost_throws(self, mock_get_value):
        mock_get_value.return_value = _make_asset_row(purchase_cost=100000)
        doc = _make_adjustment_doc(new_value=150000, adjustment_type="Revaluation (Write-up)")
        with self.assertRaises(Exception):
            asset_value_adjustment_gl.validate_adjustment_setup(doc)

    @patch("frappe.db.get_value")
    def test_new_value_equal_to_current_value_throws(self, mock_get_value):
        mock_get_value.return_value = _make_asset_row(current_value=60000)
        doc = _make_adjustment_doc(new_value=60000)
        with self.assertRaises(Exception):
            asset_value_adjustment_gl.validate_adjustment_setup(doc)

    @patch("frappe.db.get_value")
    def test_writedown_with_wrong_type_throws(self, mock_get_value):
        mock_get_value.return_value = _make_asset_row(current_value=60000)
        doc = _make_adjustment_doc(new_value=50000, adjustment_type="Revaluation (Write-up)")
        with self.assertRaises(Exception):
            asset_value_adjustment_gl.validate_adjustment_setup(doc)

    @patch("frappe.db.get_value")
    def test_writeup_with_wrong_type_throws(self, mock_get_value):
        mock_get_value.return_value = _make_asset_row(current_value=60000)
        doc = _make_adjustment_doc(new_value=70000, adjustment_type="Impairment (Write-down)")
        with self.assertRaises(Exception):
            asset_value_adjustment_gl.validate_adjustment_setup(doc)

    @patch("frappe.db.get_value")
    def test_missing_adjustment_account_throws(self, mock_get_value):
        mock_get_value.return_value = _make_asset_row(current_value=60000)
        doc = _make_adjustment_doc(new_value=50000, adjustment_account=None)
        with self.assertRaises(Exception):
            asset_value_adjustment_gl.validate_adjustment_setup(doc)

    @patch("zoho_books_clone.assets.asset_value_adjustment_gl.get_category_accounts")
    @patch("frappe.db.get_value")
    def test_missing_accumulated_depreciation_account_throws(self, mock_get_value, mock_accounts):
        mock_get_value.return_value = _make_asset_row(current_value=60000)
        mock_accounts.return_value = {}
        doc = _make_adjustment_doc(new_value=50000)
        with self.assertRaises(Exception):
            asset_value_adjustment_gl.validate_adjustment_setup(doc)

    @patch("zoho_books_clone.assets.asset_value_adjustment_gl.get_category_accounts")
    @patch("frappe.db.get_value")
    def test_valid_impairment_passes(self, mock_get_value, mock_accounts):
        mock_get_value.return_value = _make_asset_row(current_value=60000)
        mock_accounts.return_value = {"accumulated_depreciation_account": "Accum Depr - VK"}
        doc = _make_adjustment_doc(new_value=50000, adjustment_type="Impairment (Write-down)")
        asset_value_adjustment_gl.validate_adjustment_setup(doc)  # should not raise

    @patch("zoho_books_clone.assets.asset_value_adjustment_gl.get_category_accounts")
    @patch("frappe.db.get_value")
    def test_valid_revaluation_passes(self, mock_get_value, mock_accounts):
        mock_get_value.return_value = _make_asset_row(current_value=60000)
        mock_accounts.return_value = {"accumulated_depreciation_account": "Accum Depr - VK"}
        doc = _make_adjustment_doc(new_value=70000, adjustment_type="Revaluation (Write-up)")
        asset_value_adjustment_gl.validate_adjustment_setup(doc)  # should not raise

    @patch("frappe.db.get_value")
    def test_existing_asset_not_skipped(self, mock_get_value):
        """Unlike capitalization/depreciation/disposal, an is_existing_asset
        (opening) asset must NOT be exempted -- it still needs a full
        Accumulated Depreciation Account check."""
        mock_get_value.return_value = _make_asset_row(current_value=60000)
        with patch("zoho_books_clone.assets.asset_value_adjustment_gl.get_category_accounts") as mock_accounts:
            mock_accounts.return_value = {}
            doc = _make_adjustment_doc(new_value=50000)
            with self.assertRaises(Exception):
                asset_value_adjustment_gl.validate_adjustment_setup(doc)


class TestPostAdjustmentGl(unittest.TestCase):
    """validate_adjustment_setup is exercised on its own above, so these
    patch it out to isolate the posting/value-bump behaviour."""

    @patch("zoho_books_clone.assets.asset_value_adjustment_gl.validate_adjustment_setup")
    @patch("zoho_books_clone.assets.asset_value_adjustment_gl.get_category_accounts")
    @patch("zoho_books_clone.assets.asset_value_adjustment_gl.make_gl_entries")
    @patch("zoho_books_clone.assets.asset_value_adjustment_gl.frappe")
    def test_impairment_debits_adjustment_account_credits_accum_depr(
        self, mock_frappe, mock_gl, mock_accounts, mock_validate
    ):
        asset = _make_asset_doc(purchase_cost=100000, current_value=60000)
        mock_frappe.get_doc.return_value = asset
        mock_accounts.return_value = {"accumulated_depreciation_account": "Accum Depr - VK"}
        doc = _make_adjustment_doc(new_value=50000, adjustment_type="Impairment (Write-down)")

        asset_value_adjustment_gl.post_adjustment_gl(doc)

        gl_map = mock_gl.call_args[0][0]
        total_debit = sum(r["debit"] for r in gl_map)
        total_credit = sum(r["credit"] for r in gl_map)
        self.assertEqual(total_debit, total_credit)

        by_account = {r["account"]: (r["debit"], r["credit"]) for r in gl_map}
        self.assertEqual(by_account["Impairment Loss - VK"], (10000, 0))
        self.assertEqual(by_account["Accum Depr - VK"], (0, 10000))

        # Asset value moves to new_value (both directions update current_value,
        # unlike Asset Repair which only touches the asset when capitalized).
        asset.db_set.assert_called_once_with("current_value", 50000, update_modified=False)
        doc.db_set.assert_any_call("current_value_before", 60000, update_modified=False)
        doc.db_set.assert_any_call("adjustment_amount", -10000, update_modified=False)
        doc.db_set.assert_any_call("gl_posted", 1, update_modified=False)

    @patch("zoho_books_clone.assets.asset_value_adjustment_gl.validate_adjustment_setup")
    @patch("zoho_books_clone.assets.asset_value_adjustment_gl.get_category_accounts")
    @patch("zoho_books_clone.assets.asset_value_adjustment_gl.make_gl_entries")
    @patch("zoho_books_clone.assets.asset_value_adjustment_gl.frappe")
    def test_revaluation_debits_accum_depr_credits_adjustment_account(
        self, mock_frappe, mock_gl, mock_accounts, mock_validate
    ):
        asset = _make_asset_doc(purchase_cost=100000, current_value=60000)
        mock_frappe.get_doc.return_value = asset
        mock_accounts.return_value = {"accumulated_depreciation_account": "Accum Depr - VK"}
        doc = _make_adjustment_doc(new_value=75000, adjustment_account="Revaluation Reserve - VK",
                                     adjustment_type="Revaluation (Write-up)")

        asset_value_adjustment_gl.post_adjustment_gl(doc)

        gl_map = mock_gl.call_args[0][0]
        by_account = {r["account"]: (r["debit"], r["credit"]) for r in gl_map}
        self.assertEqual(by_account["Accum Depr - VK"], (15000, 0))
        self.assertEqual(by_account["Revaluation Reserve - VK"], (0, 15000))

        doc.db_set.assert_any_call("adjustment_amount", 15000, update_modified=False)

    @patch("zoho_books_clone.assets.asset_value_adjustment_gl.validate_adjustment_setup")
    @patch("zoho_books_clone.assets.asset_value_adjustment_gl.get_category_accounts")
    @patch("zoho_books_clone.assets.asset_value_adjustment_gl.make_gl_entries")
    @patch("zoho_books_clone.assets.asset_value_adjustment_gl.frappe")
    def test_asset_current_value_updated_to_new_value(self, mock_frappe, mock_gl, mock_accounts, mock_validate):
        asset = _make_asset_doc(purchase_cost=100000, current_value=60000)
        mock_frappe.get_doc.return_value = asset
        mock_accounts.return_value = {"accumulated_depreciation_account": "Accum Depr - VK"}
        doc = _make_adjustment_doc(new_value=45000, adjustment_type="Impairment (Write-down)")

        asset_value_adjustment_gl.post_adjustment_gl(doc)

        # Original purchase_cost is left untouched -- only current_value moves.
        asset.db_set.assert_called_once_with("current_value", 45000, update_modified=False)

    @patch("zoho_books_clone.assets.asset_value_adjustment_gl.make_gl_entries")
    def test_already_posted_is_idempotent(self, mock_gl):
        doc = _make_adjustment_doc(gl_posted=1)
        asset_value_adjustment_gl.post_adjustment_gl(doc)
        mock_gl.assert_not_called()


class TestReverseAdjustmentGl(unittest.TestCase):

    @patch("zoho_books_clone.assets.asset_value_adjustment_gl.make_gl_entries")
    def test_no_op_if_never_posted(self, mock_gl):
        doc = _make_adjustment_doc(gl_posted=0)
        asset_value_adjustment_gl.reverse_adjustment_gl(doc)
        mock_gl.assert_not_called()

    @patch("zoho_books_clone.assets.asset_value_adjustment_gl.make_gl_entries")
    @patch("zoho_books_clone.assets.asset_value_adjustment_gl.frappe")
    def test_reversal_restores_current_value_before_and_clears_gl_posted(self, mock_frappe, mock_gl):
        asset = _make_asset_doc(current_value=50000)
        mock_frappe.get_doc.return_value = asset
        doc = _make_adjustment_doc(gl_posted=1, current_value_before=60000)

        asset_value_adjustment_gl.reverse_adjustment_gl(doc)

        mock_gl.assert_called_once_with(
            [{"voucher_type": "Asset Value Adjustment", "voucher_no": doc.name}],
            cancel=True,
        )
        asset.db_set.assert_called_once_with("current_value", 60000, update_modified=False)
        doc.db_set.assert_called_once_with("gl_posted", 0, update_modified=False)

    @patch("zoho_books_clone.assets.asset_value_adjustment_gl.frappe")
    @patch("zoho_books_clone.assets.asset_value_adjustment_gl.make_gl_entries")
    def test_gl_failure_does_not_raise_and_logs(self, mock_gl, mock_frappe):
        mock_gl.side_effect = Exception("GL boom")
        doc = _make_adjustment_doc(gl_posted=1, current_value_before=60000)
        asset_value_adjustment_gl.reverse_adjustment_gl(doc)  # should not raise
        mock_frappe.log_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()