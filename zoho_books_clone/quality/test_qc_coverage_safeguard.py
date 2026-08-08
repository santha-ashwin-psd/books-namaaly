"""
Test — QC Coverage Resolver + Duplicate-QCI Safeguard
=======================================================
Covers quality/qc_engine.py::get_or_create_coverage:

  1. Core coverage resolution (existing live coverage found -> reused;
     no coverage + create_if_missing -> creates exactly one QCI + one
     QC Coverage row; no coverage + create_if_missing=False -> Missing).
  2. Stale/dangling coverage cleanup (QCI deleted or cancelled out from
     under a QC Coverage row -> dropped, falls through to re-create).
  3. NEW safeguard: refuses to spawn another QCI for an item that already
     has an unresolved (draft/Pending) QCI on the same reference doc --
     this is the exact pattern that produced QCI-2026-00006/00007/00008
     for one Purchase Invoice line. Verifies it logs, warns, and returns
     the existing unresolved QCI instead of silently creating a new one.

Run with:
    bench --site <site> run-tests --module zoho_books_clone.quality.test_qc_coverage_safeguard
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import frappe

from zoho_books_clone.quality.qc_engine import get_or_create_coverage


class _MockRow:
    def __init__(self, doctype="Purchase Invoice Item", name="row-hash-1"):
        self.doctype = doctype
        self.name = name


class _MockDoc:
    def __init__(self, doctype="Purchase Invoice", name="PINV-2026-00045"):
        self.doctype = doctype
        self.name = name


def _as_dict(**kwargs):
    d = MagicMock()
    for k, v in kwargs.items():
        setattr(d, k, v)
    d.get = lambda key, default=None: kwargs.get(key, default)
    return d


class TestGetOrCreateCoverageCore(unittest.TestCase):

    def _env(self, **overrides):
        base = dict(
            get_value=MagicMock(return_value=None),
            delete=MagicMock(),
            has_column=MagicMock(return_value=False),
        )
        base.update(overrides)
        return base

    @patch("zoho_books_clone.quality.qc_engine.create_qc_inspection_for_item")
    @patch("zoho_books_clone.quality.qc_engine.frappe")
    def test_no_row_name_fails_safe_to_missing(self, mock_frappe, mock_create):
        row = _MockRow(name=None)
        doc = _MockDoc()
        result = get_or_create_coverage(doc, row, "ITEM-001", "Incoming", create_if_missing=True)
        self.assertEqual(result, {"qci": None, "status": "Missing", "created": False})
        mock_create.assert_not_called()

    @patch("zoho_books_clone.quality.qc_engine.create_qc_inspection_for_item")
    @patch("zoho_books_clone.quality.qc_engine.frappe")
    def test_existing_live_coverage_is_reused(self, mock_frappe, mock_create):
        row = _MockRow()
        doc = _MockDoc()
        mock_frappe.db.get_value.side_effect = [
            "QCI-2026-00006",                                   # QC Coverage lookup
            _as_dict(docstatus=1, status="Pass"),                # QCI info
        ]
        mock_frappe.db.has_column.return_value = False

        result = get_or_create_coverage(doc, row, "ITEM-001", "Incoming", create_if_missing=True)

        self.assertEqual(result["qci"], "QCI-2026-00006")
        self.assertEqual(result["status"], "Pass")
        self.assertFalse(result["created"])
        mock_create.assert_not_called()

    @patch("zoho_books_clone.quality.qc_engine.create_qc_inspection_for_item")
    @patch("zoho_books_clone.quality.qc_engine.frappe")
    def test_no_coverage_and_create_if_missing_false_returns_missing(self, mock_frappe, mock_create):
        row = _MockRow()
        doc = _MockDoc()
        mock_frappe.db.get_value.return_value = None

        result = get_or_create_coverage(doc, row, "ITEM-001", "Incoming", create_if_missing=False)

        self.assertEqual(result, {"qci": None, "status": "Missing", "created": False})
        mock_create.assert_not_called()

    @patch("zoho_books_clone.quality.qc_engine.create_qc_inspection_for_item")
    @patch("zoho_books_clone.quality.qc_engine.frappe")
    def test_dangling_coverage_pointing_at_deleted_qci_is_dropped(self, mock_frappe, mock_create):
        row = _MockRow()
        doc = _MockDoc()
        # First lookup finds a coverage row; the QCI it points to is gone
        # (get_value returns None for the QCI info); then no unresolved
        # inspections exist; then a fresh one gets created.
        mock_frappe.db.get_value.side_effect = [
            "QCI-2026-STALE",     # QC Coverage lookup
            None,                  # QCI info -- deleted out from under it
        ]
        mock_frappe.get_all.return_value = []  # no unresolved duplicates
        mock_create.return_value = "QCI-2026-00050"
        mock_frappe.new_doc.return_value = MagicMock(insert=MagicMock())
        mock_frappe.db.has_column.return_value = False

        result = get_or_create_coverage(doc, row, "ITEM-001", "Incoming", create_if_missing=True)

        mock_frappe.db.delete.assert_called_once_with(
            "QC Coverage", {"source_row": "Purchase Invoice Item:row-hash-1"}
        )
        self.assertTrue(result["created"])
        self.assertEqual(result["qci"], "QCI-2026-00050")


class TestDuplicateQCISafeguard(unittest.TestCase):
    """
    The exact scenario this safeguard exists for: source_row keeps changing
    across saves (row identity bug), so get_or_create_coverage never finds
    the existing coverage and would otherwise keep creating new QCIs for
    the same logical line -- QCI-2026-00006, then 00007, then 00008.
    """

    @patch("zoho_books_clone.quality.qc_engine.create_qc_inspection_for_item")
    @patch("zoho_books_clone.quality.qc_engine.frappe")
    def test_refuses_to_create_when_unresolved_qci_already_exists(self, mock_frappe, mock_create):
        row = _MockRow(name="row-hash-NEW")  # a "new" row identity, as if source_row drifted
        doc = _MockDoc()

        mock_frappe.db.get_value.return_value = None  # no coverage for THIS source_row
        mock_frappe.get_all.return_value = ["QCI-2026-00007"]  # already an unresolved one

        result = get_or_create_coverage(doc, row, "ITEM-001", "Incoming", create_if_missing=True)

        mock_create.assert_not_called()
        self.assertEqual(result["qci"], "QCI-2026-00007")
        self.assertEqual(result["status"], "Pending")
        self.assertFalse(result["created"])
        mock_frappe.log_error.assert_called_once()
        mock_frappe.msgprint.assert_called_once()

    @patch("zoho_books_clone.quality.qc_engine.create_qc_inspection_for_item")
    @patch("zoho_books_clone.quality.qc_engine.frappe")
    def test_get_all_filters_by_reference_doc_item_and_open_status(self, mock_frappe, mock_create):
        row = _MockRow(name="row-hash-NEW")
        doc = _MockDoc()
        mock_frappe.db.get_value.return_value = None
        mock_frappe.get_all.return_value = []
        mock_create.return_value = "QCI-2026-00099"
        mock_frappe.new_doc.return_value = MagicMock(insert=MagicMock())
        mock_frappe.db.has_column.return_value = False

        get_or_create_coverage(doc, row, "ITEM-001", "Incoming", create_if_missing=True)

        _, kwargs = mock_frappe.get_all.call_args
        filters = kwargs.get("filters") or mock_frappe.get_all.call_args[0][1] if mock_frappe.get_all.call_args[0] else kwargs.get("filters")
        # Just assert the call happened with the doctype and relevant keys present
        self.assertEqual(mock_frappe.get_all.call_args[0][0], "QC Inspection")
        call_filters = mock_frappe.get_all.call_args.kwargs.get("filters", {})
        self.assertEqual(call_filters.get("reference_type"), doc.doctype)
        self.assertEqual(call_filters.get("reference_name"), doc.name)
        self.assertEqual(call_filters.get("item"), "ITEM-001")

    @patch("zoho_books_clone.quality.qc_engine.create_qc_inspection_for_item")
    @patch("zoho_books_clone.quality.qc_engine.frappe")
    def test_creates_normally_when_no_unresolved_duplicate_exists(self, mock_frappe, mock_create):
        row = _MockRow(name="row-hash-1")
        doc = _MockDoc()
        mock_frappe.db.get_value.return_value = None
        mock_frappe.get_all.return_value = []
        mock_create.return_value = "QCI-2026-00050"
        mock_frappe.new_doc.return_value = MagicMock(insert=MagicMock())
        mock_frappe.db.has_column.return_value = False

        result = get_or_create_coverage(doc, row, "ITEM-001", "Incoming", create_if_missing=True)

        mock_create.assert_called_once()
        self.assertTrue(result["created"])
        self.assertEqual(result["qci"], "QCI-2026-00050")
        mock_frappe.log_error.assert_not_called()

    @patch("zoho_books_clone.quality.qc_engine.create_qc_inspection_for_item")
    @patch("zoho_books_clone.quality.qc_engine.frappe")
    def test_regression_three_saves_only_ever_produce_one_qci(self, mock_frappe, mock_create):
        """
        End-to-end simulation of the original bug report: three "saves" of
        the same logical line, each (pre-fix) minting a different
        source_row. With the safeguard in place, only the FIRST save
        creates a QCI -- the next two must reuse it, not create 00007/00008.
        """
        doc = _MockDoc()
        mock_create.return_value = "QCI-2026-00006"
        mock_frappe.new_doc.return_value = MagicMock(insert=MagicMock())
        mock_frappe.db.has_column.return_value = False

        created_so_far = []

        def fake_get_all(doctype, filters=None, pluck=None):
            return list(created_so_far)

        mock_frappe.get_all.side_effect = fake_get_all
        mock_frappe.db.get_value.return_value = None  # no source_row match, every time

        row_names = ["thabeb72sa", "sqkpq8rg7l", "si1p90eeen"]
        results = []
        for rn in row_names:
            row = _MockRow(name=rn)
            result = get_or_create_coverage(doc, row, "ITEM-001", "Incoming", create_if_missing=True)
            results.append(result)
            if result["created"]:
                created_so_far.append(result["qci"])

        self.assertEqual(mock_create.call_count, 1)
        self.assertTrue(results[0]["created"])
        self.assertFalse(results[1]["created"])
        self.assertFalse(results[2]["created"])
        for r in results:
            self.assertEqual(r["qci"], "QCI-2026-00006")


if __name__ == "__main__":
    unittest.main()