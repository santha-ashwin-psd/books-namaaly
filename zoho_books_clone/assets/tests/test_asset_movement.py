"""
Tests for assets/doctype/asset_movement/asset_movement.py -- Transfer /
Issue / Receipt purpose validation, snapshot defaulting, and the
apply-on-submit / revert-on-cancel state machine.

Run with:
    bench run-tests --app zoho_books_clone --module zoho_books_clone.assets.tests.test_asset_movement
"""

import unittest
from unittest.mock import MagicMock, patch

from zoho_books_clone.assets.doctype.asset_movement.asset_movement import AssetMovement


class _AttrDict(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            return None


def _make_movement(**overrides):
    m = MagicMock(spec=AssetMovement)
    m.asset = "AST-0001"
    m.company = None
    m.purpose = "Transfer"
    m.source_location = None
    m.source_department = None
    m.source_custodian = None
    m.target_location = None
    m.target_department = None
    m.target_custodian = None
    for k, v in overrides.items():
        setattr(m, k, v)
    return m


class TestFetchAssetSnapshot(unittest.TestCase):

    @patch("frappe.db.get_value")
    def test_stamps_company_from_asset(self, mock_get_value):
        mock_get_value.return_value = _AttrDict(
            {"company": "VK Herbal", "location": "Main Store", "department": "Production"}
        )
        m = _make_movement()
        AssetMovement._fetch_asset_snapshot(m)
        self.assertEqual(m.company, "VK Herbal")

    @patch("frappe.db.get_value")
    def test_defaults_source_fields_from_asset_when_blank(self, mock_get_value):
        mock_get_value.return_value = _AttrDict(
            {"company": "VK Herbal", "location": "Main Store", "department": "Production"}
        )
        m = _make_movement(source_location=None, source_department=None)
        AssetMovement._fetch_asset_snapshot(m)
        self.assertEqual(m.source_location, "Main Store")
        self.assertEqual(m.source_department, "Production")

    @patch("frappe.db.get_value")
    def test_does_not_override_explicit_source_fields(self, mock_get_value):
        mock_get_value.return_value = _AttrDict(
            {"company": "VK Herbal", "location": "Main Store", "department": "Production"}
        )
        m = _make_movement(source_location="Warehouse B")
        AssetMovement._fetch_asset_snapshot(m)
        self.assertEqual(m.source_location, "Warehouse B")

    @patch("frappe.db.get_value")
    def test_missing_asset_throws(self, mock_get_value):
        mock_get_value.return_value = None
        m = _make_movement()
        with self.assertRaises(Exception):
            AssetMovement._fetch_asset_snapshot(m)

    def test_no_asset_set_is_a_no_op(self):
        m = _make_movement(asset=None)
        AssetMovement._fetch_asset_snapshot(m)  # should not raise / not call DB


class TestValidatePurposeRequirements(unittest.TestCase):

    def _run(self, m):
        AssetMovement._validate_purpose_requirements(m)

    # ── Transfer ──────────────────────────────────────────────────────
    def test_transfer_requires_at_least_one_target(self):
        m = _make_movement(purpose="Transfer")
        with self.assertRaises(Exception):
            self._run(m)

    def test_transfer_with_target_location_passes(self):
        m = _make_movement(purpose="Transfer", source_location="A", target_location="B")
        self._run(m)  # should not raise

    def test_transfer_no_op_when_source_equals_target_throws(self):
        m = _make_movement(
            purpose="Transfer",
            source_location="A", target_location="A",
            source_department="D", target_department="D",
            source_custodian=None, target_custodian=None,
        )
        with self.assertRaises(Exception):
            self._run(m)

    # ── Issue ─────────────────────────────────────────────────────────
    def test_issue_requires_a_source(self):
        m = _make_movement(purpose="Issue", target_custodian="Ravi")
        with self.assertRaises(Exception):
            self._run(m)

    def test_issue_rejects_target_location_or_department(self):
        m = _make_movement(purpose="Issue", source_location="A", target_location="B")
        with self.assertRaises(Exception):
            self._run(m)

    def test_issue_with_source_and_target_custodian_passes(self):
        m = _make_movement(purpose="Issue", source_location="A", target_custodian="Ravi")
        self._run(m)  # should not raise

    # ── Receipt ───────────────────────────────────────────────────────
    def test_receipt_requires_target_location_or_department(self):
        m = _make_movement(purpose="Receipt", source_custodian="Ravi")
        with self.assertRaises(Exception):
            self._run(m)

    def test_receipt_with_target_location_passes(self):
        m = _make_movement(purpose="Receipt", source_custodian="Ravi", target_location="Main Store")
        self._run(m)  # should not raise


class TestApplyAndRevert(unittest.TestCase):

    @patch("frappe.get_doc")
    def test_apply_updates_asset_location_and_department(self, mock_get_doc):
        asset = MagicMock()
        mock_get_doc.return_value = asset
        m = _make_movement(target_location="Warehouse B", target_department="Sales")
        AssetMovement._apply_to_asset(m)
        asset.db_set.assert_any_call("location", "Warehouse B", update_modified=False)
        asset.db_set.assert_any_call("department", "Sales", update_modified=False)

    @patch("frappe.get_doc")
    def test_apply_is_no_op_when_no_target_fields(self, mock_get_doc):
        """An Issue movement (target_custodian only) shouldn't touch
        Asset.location/department -- those aren't company-location fields."""
        m = _make_movement(target_location=None, target_department=None, target_custodian="Ravi")
        AssetMovement._apply_to_asset(m)
        mock_get_doc.assert_not_called()

    @patch("frappe.get_doc")
    def test_revert_restores_source_snapshot(self, mock_get_doc):
        asset = MagicMock()
        mock_get_doc.return_value = asset
        m = _make_movement(source_location="Main Store", source_department="Production")
        AssetMovement._revert_asset(m)
        asset.db_set.assert_any_call("location", "Main Store", update_modified=False)
        asset.db_set.assert_any_call("department", "Production", update_modified=False)

    @patch("frappe.get_doc")
    def test_revert_with_blank_source_location_clears_it(self, mock_get_doc):
        asset = MagicMock()
        mock_get_doc.return_value = asset
        m = _make_movement(source_location=None, source_department=None)
        AssetMovement._revert_asset(m)
        asset.db_set.assert_any_call("location", "", update_modified=False)


if __name__ == "__main__":
    unittest.main()