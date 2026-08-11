"""
Tests for assets/asset_quantity_adjustment_gl.py -- proportional
quantity/value write-off (e.g. "10 of 20 units damaged"), GL posting
against Fixed Asset / Accumulated Depreciation / Loss accounts, the
Asset.qty/purchase_cost/current_value shrink, and reversal on cancel.

Run with:
    bench run-tests --app zoho_books_clone --module zoho_books_clone.assets.tests.test_asset_quantity_adjustment_gl
"""

import unittest
from unittest.mock import MagicMock, patch

from zoho_books_clone.assets import asset_quantity_adjustment_gl


class _AttrDict(dict):
	def __getattr__(self, key):
		try:
			return self[key]
		except KeyError:
			return None


def _make_adjustment_doc(**overrides):
	doc = MagicMock()
	doc.name = "ASTQA-0001"
	doc.asset = "AST-0001"
	doc.adjustment_date = "2026-07-01"
	doc.damaged_qty = 10
	doc.reason = "10 units damaged in transit"
	doc.loss_account = "Loss on Damaged Assets - VK"
	doc.gl_posted = 0
	doc.qty_before = None
	doc.qty_after = None
	doc.purchase_cost_before = None
	doc.current_value_before = None
	doc.write_off_purchase_cost = None
	doc.write_off_accumulated_depreciation = None
	doc.write_off_net_book_value = None
	doc.purchase_cost_after = None
	doc.current_value_after = None
	for k, v in overrides.items():
		setattr(doc, k, v)
	return doc


def _make_asset_row(**overrides):
	"""What frappe.db.get_value(..., as_dict=True) returns inside validate_quantity_adjustment_setup."""
	row = _AttrDict(
		docstatus=1,
		status="Submitted",
		asset_category="Machinery",
		company="VK Herbal",
		is_existing_asset=0,
		qty=20,
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
	doc.is_existing_asset = 0
	doc.qty = 20
	doc.purchase_cost = 100000
	doc.current_value = 60000
	for k, v in overrides.items():
		setattr(doc, k, v)
	return doc


class TestValidateQuantityAdjustmentSetup(unittest.TestCase):

	def test_no_asset_is_a_no_op(self):
		doc = _make_adjustment_doc(asset=None)
		asset_quantity_adjustment_gl.validate_quantity_adjustment_setup(doc)  # should not raise

	@patch("frappe.db.get_value")
	def test_asset_not_found_throws(self, mock_get_value):
		mock_get_value.return_value = None
		doc = _make_adjustment_doc()
		with self.assertRaises(Exception):
			asset_quantity_adjustment_gl.validate_quantity_adjustment_setup(doc)

	@patch("frappe.db.get_value")
	def test_unsubmitted_asset_throws(self, mock_get_value):
		mock_get_value.return_value = _make_asset_row(docstatus=0)
		doc = _make_adjustment_doc()
		with self.assertRaises(Exception):
			asset_quantity_adjustment_gl.validate_quantity_adjustment_setup(doc)

	@patch("frappe.db.get_value")
	def test_disposed_asset_throws(self, mock_get_value):
		mock_get_value.return_value = _make_asset_row(status="Scrapped")
		doc = _make_adjustment_doc()
		with self.assertRaises(Exception):
			asset_quantity_adjustment_gl.validate_quantity_adjustment_setup(doc)

	@patch("frappe.db.get_value")
	def test_zero_damaged_qty_throws(self, mock_get_value):
		mock_get_value.return_value = _make_asset_row()
		doc = _make_adjustment_doc(damaged_qty=0)
		with self.assertRaises(Exception):
			asset_quantity_adjustment_gl.validate_quantity_adjustment_setup(doc)

	@patch("frappe.db.get_value")
	def test_negative_damaged_qty_throws(self, mock_get_value):
		mock_get_value.return_value = _make_asset_row()
		doc = _make_adjustment_doc(damaged_qty=-5)
		with self.assertRaises(Exception):
			asset_quantity_adjustment_gl.validate_quantity_adjustment_setup(doc)

	@patch("frappe.db.get_value")
	def test_damaged_qty_equal_to_asset_qty_throws(self, mock_get_value):
		mock_get_value.return_value = _make_asset_row(qty=20)
		doc = _make_adjustment_doc(damaged_qty=20)
		with self.assertRaises(Exception):
			asset_quantity_adjustment_gl.validate_quantity_adjustment_setup(doc)

	@patch("frappe.db.get_value")
	def test_damaged_qty_above_asset_qty_throws(self, mock_get_value):
		mock_get_value.return_value = _make_asset_row(qty=20)
		doc = _make_adjustment_doc(damaged_qty=25)
		with self.assertRaises(Exception):
			asset_quantity_adjustment_gl.validate_quantity_adjustment_setup(doc)

	@patch("frappe.db.get_value")
	def test_missing_reason_throws(self, mock_get_value):
		mock_get_value.return_value = _make_asset_row()
		doc = _make_adjustment_doc(reason=None)
		with self.assertRaises(Exception):
			asset_quantity_adjustment_gl.validate_quantity_adjustment_setup(doc)

	@patch("frappe.db.get_value")
	def test_missing_loss_account_throws(self, mock_get_value):
		mock_get_value.return_value = _make_asset_row()
		doc = _make_adjustment_doc(loss_account=None)
		with self.assertRaises(Exception):
			asset_quantity_adjustment_gl.validate_quantity_adjustment_setup(doc)

	@patch("zoho_books_clone.assets.asset_quantity_adjustment_gl.get_category_accounts")
	@patch("frappe.db.get_value")
	def test_missing_fixed_asset_account_throws(self, mock_get_value, mock_accounts):
		mock_get_value.return_value = _make_asset_row()
		mock_accounts.return_value = {"accumulated_depreciation_account": "Accum Depr - VK"}
		doc = _make_adjustment_doc()
		with self.assertRaises(Exception):
			asset_quantity_adjustment_gl.validate_quantity_adjustment_setup(doc)

	@patch("zoho_books_clone.assets.asset_quantity_adjustment_gl.get_category_accounts")
	@patch("frappe.db.get_value")
	def test_valid_adjustment_passes(self, mock_get_value, mock_accounts):
		mock_get_value.return_value = _make_asset_row()
		mock_accounts.return_value = {
			"fixed_asset_account": "Fixed Asset - VK",
			"accumulated_depreciation_account": "Accum Depr - VK",
		}
		doc = _make_adjustment_doc()
		asset_quantity_adjustment_gl.validate_quantity_adjustment_setup(doc)  # should not raise

	@patch("frappe.db.get_value")
	def test_existing_asset_skips_account_check(self, mock_get_value):
		"""Like capitalization/depreciation/disposal (but unlike Value
		Adjustment): an is_existing_asset never had a capitalization entry
		posted, so no Fixed Asset / Accumulated Depreciation account is
		required for it here."""
		mock_get_value.return_value = _make_asset_row(is_existing_asset=1)
		doc = _make_adjustment_doc()
		asset_quantity_adjustment_gl.validate_quantity_adjustment_setup(doc)  # should not raise


class TestPostQuantityAdjustmentGl(unittest.TestCase):
	"""validate_quantity_adjustment_setup is exercised on its own above, so
	these patch it out to isolate the posting/proportional-write-off math."""

	@patch("zoho_books_clone.assets.asset_quantity_adjustment_gl.validate_quantity_adjustment_setup")
	@patch("zoho_books_clone.assets.asset_quantity_adjustment_gl.get_category_accounts")
	@patch("zoho_books_clone.assets.asset_quantity_adjustment_gl.make_gl_entries")
	@patch("zoho_books_clone.assets.asset_quantity_adjustment_gl.frappe")
	def test_proportional_write_off_balances_and_posts_correct_accounts(
		self, mock_frappe, mock_gl, mock_accounts, mock_validate
	):
		# 10 of 20 units (50%) written off; cost 100000, current_value 60000
		# => accumulated_depreciation_before = 40000
		# => write_off_purchase_cost = 50000, write_off_accum_dep = 20000, loss = 30000
		asset = _make_asset_doc(qty=20, purchase_cost=100000, current_value=60000)
		mock_frappe.get_doc.return_value = asset
		mock_accounts.return_value = {
			"fixed_asset_account": "Fixed Asset - VK",
			"accumulated_depreciation_account": "Accum Depr - VK",
		}
		doc = _make_adjustment_doc(damaged_qty=10)

		asset_quantity_adjustment_gl.post_quantity_adjustment_gl(doc)

		gl_map = mock_gl.call_args[0][0]
		total_debit = sum(r["debit"] for r in gl_map)
		total_credit = sum(r["credit"] for r in gl_map)
		self.assertEqual(total_debit, total_credit)

		by_account = {r["account"]: (r["debit"], r["credit"]) for r in gl_map}
		self.assertEqual(by_account["Accum Depr - VK"], (20000, 0))
		self.assertEqual(by_account["Loss on Damaged Assets - VK"], (30000, 0))
		self.assertEqual(by_account["Fixed Asset - VK"], (0, 50000))

		asset.db_set.assert_any_call("qty", 10, update_modified=False)
		asset.db_set.assert_any_call("purchase_cost", 50000, update_modified=False)
		asset.db_set.assert_any_call("current_value", 30000, update_modified=False)

		doc.db_set.assert_any_call("gl_posted", 1, update_modified=False)
		doc.db_set.assert_any_call("qty_before", 20, update_modified=False)
		doc.db_set.assert_any_call("qty_after", 10, update_modified=False)
		doc.db_set.assert_any_call("write_off_purchase_cost", 50000, update_modified=False)
		doc.db_set.assert_any_call("write_off_accumulated_depreciation", 20000, update_modified=False)
		doc.db_set.assert_any_call("write_off_net_book_value", 30000, update_modified=False)

	@patch("zoho_books_clone.assets.asset_quantity_adjustment_gl.validate_quantity_adjustment_setup")
	@patch("zoho_books_clone.assets.asset_quantity_adjustment_gl.get_category_accounts")
	@patch("zoho_books_clone.assets.asset_quantity_adjustment_gl.make_gl_entries")
	@patch("zoho_books_clone.assets.asset_quantity_adjustment_gl.frappe")
	def test_fully_depreciated_units_post_no_loss_line(
		self, mock_frappe, mock_gl, mock_accounts, mock_validate
	):
		# Fully depreciated asset (current_value == 0): the written-off
		# slice's accumulated depreciation equals its cost, so there's no
		# loss line, only Accum Depr DR / Fixed Asset CR.
		asset = _make_asset_doc(qty=20, purchase_cost=100000, current_value=0)
		mock_frappe.get_doc.return_value = asset
		mock_accounts.return_value = {
			"fixed_asset_account": "Fixed Asset - VK",
			"accumulated_depreciation_account": "Accum Depr - VK",
		}
		doc = _make_adjustment_doc(damaged_qty=10)

		asset_quantity_adjustment_gl.post_quantity_adjustment_gl(doc)

		gl_map = mock_gl.call_args[0][0]
		accounts_used = {r["account"] for r in gl_map}
		self.assertNotIn("Loss on Damaged Assets - VK", accounts_used)
		by_account = {r["account"]: (r["debit"], r["credit"]) for r in gl_map}
		self.assertEqual(by_account["Accum Depr - VK"], (50000, 0))
		self.assertEqual(by_account["Fixed Asset - VK"], (0, 50000))

	@patch("zoho_books_clone.assets.asset_quantity_adjustment_gl.validate_quantity_adjustment_setup")
	@patch("zoho_books_clone.assets.asset_quantity_adjustment_gl.frappe")
	def test_existing_asset_updates_values_without_gl(self, mock_frappe, mock_validate):
		asset = _make_asset_doc(qty=20, purchase_cost=100000, current_value=60000, is_existing_asset=1)
		mock_frappe.get_doc.return_value = asset
		doc = _make_adjustment_doc(damaged_qty=10)

		with patch("zoho_books_clone.assets.asset_quantity_adjustment_gl.make_gl_entries") as mock_gl:
			asset_quantity_adjustment_gl.post_quantity_adjustment_gl(doc)
			mock_gl.assert_not_called()

		asset.db_set.assert_any_call("qty", 10, update_modified=False)
		asset.db_set.assert_any_call("purchase_cost", 50000, update_modified=False)
		asset.db_set.assert_any_call("current_value", 30000, update_modified=False)

	@patch("zoho_books_clone.assets.asset_quantity_adjustment_gl.make_gl_entries")
	def test_already_posted_is_idempotent(self, mock_gl):
		doc = _make_adjustment_doc(gl_posted=1)
		asset_quantity_adjustment_gl.post_quantity_adjustment_gl(doc)
		mock_gl.assert_not_called()


class TestReverseQuantityAdjustmentGl(unittest.TestCase):

	@patch("zoho_books_clone.assets.asset_quantity_adjustment_gl.make_gl_entries")
	def test_no_op_if_never_posted(self, mock_gl):
		doc = _make_adjustment_doc(gl_posted=0)
		asset_quantity_adjustment_gl.reverse_quantity_adjustment_gl(doc)
		mock_gl.assert_not_called()

	@patch("zoho_books_clone.assets.asset_quantity_adjustment_gl.make_gl_entries")
	@patch("zoho_books_clone.assets.asset_quantity_adjustment_gl.frappe")
	def test_reversal_restores_qty_and_value_and_clears_gl_posted(self, mock_frappe, mock_gl):
		asset = _make_asset_doc(qty=10, purchase_cost=50000, current_value=30000, is_existing_asset=0)
		mock_frappe.get_doc.return_value = asset
		doc = _make_adjustment_doc(
			gl_posted=1,
			qty_before=20,
			purchase_cost_before=100000,
			current_value_before=60000,
			write_off_purchase_cost=50000,
		)

		asset_quantity_adjustment_gl.reverse_quantity_adjustment_gl(doc)

		mock_gl.assert_called_once_with(
			[{"voucher_type": "Asset Quantity Adjustment", "voucher_no": doc.name}],
			cancel=True,
		)
		asset.db_set.assert_any_call("qty", 20, update_modified=False)
		asset.db_set.assert_any_call("purchase_cost", 100000, update_modified=False)
		asset.db_set.assert_any_call("current_value", 60000, update_modified=False)
		doc.db_set.assert_called_once_with("gl_posted", 0, update_modified=False)

	@patch("zoho_books_clone.assets.asset_quantity_adjustment_gl.make_gl_entries")
	@patch("zoho_books_clone.assets.asset_quantity_adjustment_gl.frappe")
	def test_reversal_skips_gl_for_existing_asset(self, mock_frappe, mock_gl):
		asset = _make_asset_doc(qty=10, is_existing_asset=1)
		mock_frappe.get_doc.return_value = asset
		doc = _make_adjustment_doc(
			gl_posted=1,
			qty_before=20,
			purchase_cost_before=100000,
			current_value_before=60000,
			write_off_purchase_cost=50000,
		)

		asset_quantity_adjustment_gl.reverse_quantity_adjustment_gl(doc)

		mock_gl.assert_not_called()
		doc.db_set.assert_called_once_with("gl_posted", 0, update_modified=False)

	@patch("zoho_books_clone.assets.asset_quantity_adjustment_gl.frappe")
	@patch("zoho_books_clone.assets.asset_quantity_adjustment_gl.make_gl_entries")
	def test_gl_failure_does_not_raise_and_logs(self, mock_gl, mock_frappe):
		mock_gl.side_effect = Exception("GL boom")
		asset = _make_asset_doc(is_existing_asset=0)
		mock_frappe.get_doc.return_value = asset
		doc = _make_adjustment_doc(
			gl_posted=1,
			qty_before=20,
			purchase_cost_before=100000,
			current_value_before=60000,
			write_off_purchase_cost=50000,
		)
		asset_quantity_adjustment_gl.reverse_quantity_adjustment_gl(doc)  # should not raise
		mock_frappe.log_error.assert_called_once()


if __name__ == "__main__":
	unittest.main()