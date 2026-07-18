"""
Tests for Phase 4 (bulk -> packed batch/expiry lineage): Batch's
_apply_source_batch_lineage(), which caps a new batch's expiry_date to its
source_batch_no's expiry_date and blocks packing/manufacturing from an
already-expired source batch.

Follows the same binding pattern as
inventory/tests/test_landed_cost_guardrails.py -- bind the real unbound
method onto a lightweight SimpleNamespace and mock frappe.db.get_value,
rather than constructing a full frappe.model.Document. Keeps this fast and
DB-free while still exercising the actual guardrail code.

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.inventory.tests.test_batch_lineage
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from zoho_books_clone.inventory.doctype.batch.batch import Batch


def _make_batch(source_batch_no=None, manufacturing_date=None, expiry_date=None):
    doc = SimpleNamespace(
        source_batch_no=source_batch_no,
        manufacturing_date=manufacturing_date,
        expiry_date=expiry_date,
    )
    doc._apply_source_batch_lineage = Batch._apply_source_batch_lineage.__get__(doc)
    return doc


class TestSourceBatchLineage(unittest.TestCase):

    def test_noop_when_no_source_batch(self):
        doc = _make_batch(source_batch_no=None, expiry_date="2027-01-01")
        doc._apply_source_batch_lineage()
        self.assertEqual(doc.expiry_date, "2027-01-01")

    @patch.object(frappe.db, "get_value")
    def test_noop_when_source_batch_missing(self, mock_get_value):
        mock_get_value.return_value = None
        doc = _make_batch(source_batch_no="BATCH-GONE", expiry_date="2027-01-01")
        doc._apply_source_batch_lineage()
        self.assertEqual(doc.expiry_date, "2027-01-01")

    @patch.object(frappe.db, "get_value")
    def test_noop_when_source_batch_has_no_expiry(self, mock_get_value):
        mock_get_value.return_value = {"expiry_date": None, "batch_no": "BULK-001"}
        doc = _make_batch(source_batch_no="BULK-001", expiry_date="2027-01-01")
        doc._apply_source_batch_lineage()
        self.assertEqual(doc.expiry_date, "2027-01-01")

    @patch.object(frappe.db, "get_value")
    def test_caps_expiry_to_earlier_source_expiry(self, mock_get_value):
        mock_get_value.return_value = {"expiry_date": "2026-12-01", "batch_no": "BULK-001"}
        doc = _make_batch(
            source_batch_no="BULK-001",
            manufacturing_date="2026-08-01",
            expiry_date="2028-01-01",  # e.g. from Item.shelf_life_in_days
        )
        doc._apply_source_batch_lineage()
        self.assertEqual(str(doc.expiry_date), "2026-12-01")

    @patch.object(frappe.db, "get_value")
    def test_leaves_expiry_untouched_when_already_earlier_than_source(self, mock_get_value):
        mock_get_value.return_value = {"expiry_date": "2028-06-01", "batch_no": "BULK-001"}
        doc = _make_batch(
            source_batch_no="BULK-001",
            manufacturing_date="2026-08-01",
            expiry_date="2026-12-01",
        )
        doc._apply_source_batch_lineage()
        self.assertEqual(doc.expiry_date, "2026-12-01")

    @patch.object(frappe.db, "get_value")
    def test_fills_blank_expiry_from_source(self, mock_get_value):
        mock_get_value.return_value = {"expiry_date": "2026-12-01", "batch_no": "BULK-001"}
        doc = _make_batch(
            source_batch_no="BULK-001",
            manufacturing_date="2026-08-01",
            expiry_date=None,
        )
        doc._apply_source_batch_lineage()
        self.assertEqual(str(doc.expiry_date), "2026-12-01")

    @patch.object(frappe.db, "get_value")
    def test_blocks_packing_from_already_expired_source(self, mock_get_value):
        mock_get_value.return_value = {"expiry_date": "2026-06-01", "batch_no": "BULK-001"}
        doc = _make_batch(
            source_batch_no="BULK-001",
            manufacturing_date="2026-08-01",  # after the source's expiry
            expiry_date=None,
        )
        with self.assertRaises(frappe.ValidationError):
            doc._apply_source_batch_lineage()

    @patch.object(frappe.db, "get_value")
    def test_allows_packing_on_source_expiry_date_itself(self, mock_get_value):
        mock_get_value.return_value = {"expiry_date": "2026-08-01", "batch_no": "BULK-001"}
        doc = _make_batch(
            source_batch_no="BULK-001",
            manufacturing_date="2026-08-01",
            expiry_date=None,
        )
        # Same-day boundary should not throw -- only strictly *after* expiry does.
        doc._apply_source_batch_lineage()
        self.assertEqual(str(doc.expiry_date), "2026-08-01")


if __name__ == "__main__":
    unittest.main()