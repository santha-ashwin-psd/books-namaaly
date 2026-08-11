"""
Tests for assets/asset_addition_gl.py -- replacement-unit orchestration
(Paid vs. Free), which spins off a brand-new Asset document rather than
posting GL directly. These tests isolate the orchestration logic itself
(what gets copied onto the new Asset, when GL setup is pre-validated,
idempotency, cancel-safety) rather than re-testing Asset's own
capitalization GL, which is already covered by test_asset_gl.py.

Run with:
    bench run-tests --app zoho_books_clone --module zoho_books_clone.assets.tests.test_asset_addition_gl
"""

import unittest
from unittest.mock import MagicMock, patch

from zoho_books_clone.assets import asset_addition_gl


class _AttrDict(dict):
	def __getattr__(self, key):
		try:
			return self[key]
		except KeyError:
			return None


def _make_addition_doc(**overrides):
	doc = MagicMock()
	doc.name = "ASTADD-0001"
	doc.original_asset = "AST-0001"
	doc.quantity_adjustment = None
	doc.addition_type = "Paid Replacement"
	doc.addition_date = "2026-08-01"
	doc.qty = 10
	doc.reason = "Replacing 10 damaged units"
	doc.supplier = "ACME Supplies"
	doc.credit_account = "Creditors - VK"
	doc.taxable_value = 50000
	doc.taxes = []
	doc.total_tax = None
	doc.purchase_cost = None
	doc.grand_total = None
	doc.new_asset = None
	for k, v in overrides.items():
		setattr(doc, k, v)
	return doc


def _make_original_row(**overrides):
	"""What frappe.db.get_value(..., as_dict=True) returns for the original asset."""
	row = _AttrDict(
		docstatus=1,
		asset_category="Machinery",
		company="VK Herbal",
	)
	row.update(overrides)
	return row


def _make_original_doc(**overrides):
	"""What frappe.get_doc("Asset", original_asset) returns."""
	doc = MagicMock()
	doc.name = "AST-0001"
	doc.asset_name = "Bottling Machine"
	doc.asset_category = "Machinery"
	doc.company = "VK Herbal"
	doc.department = "Production"
	doc.location = "Plant 1"
	doc.depreciation_method = "Written Down Value"
	doc.depreciation_posting_frequency = "Annually"
	doc.useful_life = 10
	doc.salvage_value = 5000
	for k, v in overrides.items():
		setattr(doc, k, v)
	return doc


class TestCalculateAdditionTotals(unittest.TestCase):

	def test_free_replacement_zeroes_totals(self):
		doc = _make_addition_doc(addition_type="Free Replacement (Warranty/Insurance)", taxable_value=99999)
		asset_addition_gl.calculate_addition_totals(doc)
		self.assertEqual(doc.taxable_value, 0)
		self.assertEqual(doc.total_tax, 0)
		self.assertEqual(doc.purchase_cost, 0)
		self.assertEqual(doc.grand_total, 0)

	def test_paid_replacement_splits_itc_eligible_and_blocked_tax(self):
		tax_row_eligible = MagicMock(rate=18, is_itc_eligible=1)
		tax_row_blocked = MagicMock(rate=5, is_itc_eligible=0)
		doc = _make_addition_doc(taxable_value=10000, taxes=[tax_row_eligible, tax_row_blocked])

		asset_addition_gl.calculate_addition_totals(doc)

		self.assertEqual(tax_row_eligible.amount, 1800)
		self.assertEqual(tax_row_blocked.amount, 500)
		self.assertEqual(doc.total_tax, 2300)
		# purchase_cost = taxable_value + non-eligible tax only
		self.assertEqual(doc.purchase_cost, 10500)
		self.assertEqual(doc.grand_total, 12300)


class TestValidateAdditionSetup(unittest.TestCase):

	def test_no_original_asset_is_a_no_op(self):
		doc = _make_addition_doc(original_asset=None)
		asset_addition_gl.validate_addition_setup(doc)  # should not raise

	@patch("frappe.db.get_value")
	def test_asset_not_found_throws(self, mock_get_value):
		mock_get_value.return_value = None
		doc = _make_addition_doc()
		with self.assertRaises(Exception):
			asset_addition_gl.validate_addition_setup(doc)

	@patch("frappe.db.get_value")
	def test_unsubmitted_original_throws(self, mock_get_value):
		mock_get_value.return_value = _make_original_row(docstatus=0)
		doc = _make_addition_doc()
		with self.assertRaises(Exception):
			asset_addition_gl.validate_addition_setup(doc)

	@patch("frappe.db.get_value")
	def test_zero_qty_throws(self, mock_get_value):
		mock_get_value.return_value = _make_original_row()
		doc = _make_addition_doc(qty=0)
		with self.assertRaises(Exception):
			asset_addition_gl.validate_addition_setup(doc)

	@patch("frappe.db.get_value")
	def test_missing_reason_throws(self, mock_get_value):
		mock_get_value.return_value = _make_original_row()
		doc = _make_addition_doc(reason=None)
		with self.assertRaises(Exception):
			asset_addition_gl.validate_addition_setup(doc)

	@patch("frappe.db.get_value")
	def test_mismatched_quantity_adjustment_throws(self, mock_get_value):
		def _side_effect(doctype, *args, **kwargs):
			if doctype == "Asset":
				return _make_original_row()
			if doctype == "Asset Quantity Adjustment":
				return "AST-9999"  # different asset than original_asset
			return None
		mock_get_value.side_effect = _side_effect
		doc = _make_addition_doc(quantity_adjustment="ASTQA-0001")
		with self.assertRaises(Exception):
			asset_addition_gl.validate_addition_setup(doc)

	@patch("frappe.db.get_value")
	def test_matching_quantity_adjustment_passes(self, mock_get_value):
		def _side_effect(doctype, *args, **kwargs):
			if doctype == "Asset":
				return _make_original_row()
			if doctype == "Asset Quantity Adjustment":
				return "AST-0001"  # matches original_asset
			return None
		mock_get_value.side_effect = _side_effect
		doc = _make_addition_doc(quantity_adjustment="ASTQA-0001")
		with patch("zoho_books_clone.assets.asset_addition_gl.get_category_accounts") as mock_accounts:
			mock_accounts.return_value = {"fixed_asset_account": "Fixed Asset - VK"}
			asset_addition_gl.validate_addition_setup(doc)  # should not raise

	@patch("frappe.db.get_value")
	def test_paid_requires_positive_taxable_value(self, mock_get_value):
		mock_get_value.return_value = _make_original_row()
		doc = _make_addition_doc(taxable_value=0)
		with self.assertRaises(Exception):
			asset_addition_gl.validate_addition_setup(doc)

	@patch("frappe.db.get_value")
	def test_paid_requires_credit_account(self, mock_get_value):
		mock_get_value.return_value = _make_original_row()
		doc = _make_addition_doc(credit_account=None)
		with self.assertRaises(Exception):
			asset_addition_gl.validate_addition_setup(doc)

	@patch("zoho_books_clone.assets.asset_addition_gl.get_category_accounts")
	@patch("frappe.db.get_value")
	def test_paid_requires_fixed_asset_account_configured(self, mock_get_value, mock_accounts):
		mock_get_value.return_value = _make_original_row()
		mock_accounts.return_value = {}
		doc = _make_addition_doc()
		with self.assertRaises(Exception):
			asset_addition_gl.validate_addition_setup(doc)

	@patch("frappe.db.get_value")
	def test_free_replacement_skips_paid_only_checks(self, mock_get_value):
		mock_get_value.return_value = _make_original_row()
		doc = _make_addition_doc(
			addition_type="Free Replacement (Warranty/Insurance)",
			taxable_value=0,
			credit_account=None,
		)
		asset_addition_gl.validate_addition_setup(doc)  # should not raise


class TestPostAdditionGl(unittest.TestCase):
	"""validate_addition_setup is exercised on its own above, so these
	patch it out to isolate what gets built onto the new Asset."""

	@patch("zoho_books_clone.assets.asset_addition_gl.validate_addition_setup")
	@patch("zoho_books_clone.assets.asset_addition_gl.frappe")
	def test_paid_replacement_builds_new_asset_and_submits(self, mock_frappe, mock_validate):
		original = _make_original_doc()
		mock_frappe.get_doc.return_value = original
		new_asset = MagicMock()
		new_asset.name = "AST-0099"
		new_asset.purchase_cost = 10500
		mock_frappe.new_doc.return_value = new_asset

		tax_row = MagicMock(tax_type="CGST", rate=9, is_itc_eligible=1, account_head=None, description=None)
		doc = _make_addition_doc(taxable_value=10000, taxes=[tax_row])

		asset_addition_gl.post_addition_gl(doc)

		self.assertEqual(new_asset.is_existing_asset, 0)
		self.assertEqual(new_asset.taxable_value, 10000)
		self.assertEqual(new_asset.credit_account, "Creditors - VK")
		self.assertEqual(new_asset.replacement_of, "AST-0001")
		self.assertEqual(new_asset.asset_category, "Machinery")
		self.assertEqual(new_asset.depreciation_method, "Written Down Value")
		new_asset.append.assert_called_once_with("taxes", {
			"tax_type": "CGST",
			"rate": 9,
			"is_itc_eligible": 1,
			"account_head": None,
			"description": None,
		})
		new_asset.insert.assert_called_once_with(ignore_permissions=True)
		new_asset.submit.assert_called_once()

		doc.db_set.assert_any_call("new_asset", "AST-0099", update_modified=False)
		doc.db_set.assert_any_call("purchase_cost", 10500, update_modified=False)

	@patch("zoho_books_clone.assets.asset_addition_gl.validate_addition_setup")
	@patch("zoho_books_clone.assets.asset_addition_gl.frappe")
	def test_free_replacement_marks_existing_asset_zero_cost(self, mock_frappe, mock_validate):
		original = _make_original_doc()
		mock_frappe.get_doc.return_value = original
		new_asset = MagicMock()
		new_asset.name = "AST-0100"
		new_asset.purchase_cost = 0
		mock_frappe.new_doc.return_value = new_asset

		doc = _make_addition_doc(addition_type="Free Replacement (Warranty/Insurance)", taxable_value=0, credit_account=None)

		asset_addition_gl.post_addition_gl(doc)

		self.assertEqual(new_asset.is_existing_asset, 1)
		self.assertEqual(new_asset.taxable_value, 0)
		self.assertEqual(new_asset.purchase_cost, 0)
		new_asset.append.assert_not_called()
		new_asset.insert.assert_called_once_with(ignore_permissions=True)
		new_asset.submit.assert_called_once()

	@patch("zoho_books_clone.assets.asset_addition_gl.frappe")
	def test_already_processed_is_idempotent(self, mock_frappe):
		doc = _make_addition_doc(new_asset="AST-0099")
		asset_addition_gl.post_addition_gl(doc)
		mock_frappe.new_doc.assert_not_called()


class TestReverseAdditionGl(unittest.TestCase):

	@patch("zoho_books_clone.assets.asset_addition_gl.frappe")
	def test_no_op_if_no_new_asset(self, mock_frappe):
		doc = _make_addition_doc(new_asset=None)
		asset_addition_gl.reverse_addition_gl(doc)
		mock_frappe.get_doc.assert_not_called()

	@patch("zoho_books_clone.assets.asset_addition_gl.frappe")
	def test_no_op_if_already_cancelled(self, mock_frappe):
		new_asset = MagicMock(docstatus=2)
		mock_frappe.get_doc.return_value = new_asset
		doc = _make_addition_doc(new_asset="AST-0099")
		asset_addition_gl.reverse_addition_gl(doc)
		new_asset.cancel.assert_not_called()

	@patch("zoho_books_clone.assets.asset_addition_gl.frappe")
	def test_cancels_clean_replacement_asset(self, mock_frappe):
		row = MagicMock(status="Pending")
		new_asset = MagicMock(docstatus=1, status="Submitted", depreciation_schedule=[row])
		mock_frappe.get_doc.return_value = new_asset
		doc = _make_addition_doc(new_asset="AST-0099")

		asset_addition_gl.reverse_addition_gl(doc)

		new_asset.cancel.assert_called_once()

	@patch("zoho_books_clone.assets.asset_addition_gl.frappe")
	def test_blocks_cancel_if_depreciation_already_posted(self, mock_frappe):
		mock_frappe.throw.side_effect = Exception("blocked")
		row = MagicMock(status="Completed")
		new_asset = MagicMock(docstatus=1, status="Submitted", depreciation_schedule=[row])
		mock_frappe.get_doc.return_value = new_asset
		doc = _make_addition_doc(new_asset="AST-0099")

		with self.assertRaises(Exception):
			asset_addition_gl.reverse_addition_gl(doc)
		new_asset.cancel.assert_not_called()

	@patch("zoho_books_clone.assets.asset_addition_gl.frappe")
	def test_blocks_cancel_if_replacement_already_disposed(self, mock_frappe):
		mock_frappe.throw.side_effect = Exception("blocked")
		new_asset = MagicMock(docstatus=1, status="Scrapped", depreciation_schedule=[])
		mock_frappe.get_doc.return_value = new_asset
		doc = _make_addition_doc(new_asset="AST-0099")

		with self.assertRaises(Exception):
			asset_addition_gl.reverse_addition_gl(doc)
		new_asset.cancel.assert_not_called()


if __name__ == "__main__":
	unittest.main()