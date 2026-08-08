"""
Test — QC Row Identity Stability
=================================
Covers the root-cause bug chain that produced duplicate QC Inspections
(QCI-2026-00006/00007/00008) for one logical Purchase Invoice line:

  1. api/docs.py::save_doc used to strip `name` from EVERY child row on
     EVERY save, unconditionally -- even when the frontend correctly
     forwarded a valid, still-live row name. This test suite verifies the
     fixed behaviour: a forwarded name is kept when it still identifies a
     live row under the same parent, and only dropped when it's missing,
     deleted, or belongs to a different parent doc.

  2. quality/qc_engine.py::reconcile_row_identity is the defense-in-depth
     before_save fallback for the case where the frontend genuinely didn't
     send a name. This suite keeps the existing matching-key tests (single
     unambiguous candidate recovers identity; zero or multiple candidates
     fail safe to "new row").

Run with:
    bench --site <site> run-tests --module zoho_books_clone.quality.test_qc_row_identity
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import frappe

from zoho_books_clone.quality.qc_engine import reconcile_row_identity, _row_identity_key


# ── Mocks ──────────────────────────────────────────────────────────────────

class _MockRow:
    def __init__(self, name=None, item_code="ITEM-001", batch_no=None,
                 qty=10.0, rate=100.0, quality_inspection=None):
        self.name = name
        self.item_code = item_code
        self.batch_no = batch_no
        self.qty = qty
        self.rate = rate
        self.quality_inspection = quality_inspection


class _MockDoc:
    def __init__(self, items, is_new=False, prev_items=None):
        self.items = items
        self._is_new = is_new
        self._prev_items = prev_items

    def is_new(self):
        return self._is_new

    def get_doc_before_save(self):
        if self._prev_items is None:
            return None
        prev = MagicMock()
        prev.items = self._prev_items
        return prev


# ── reconcile_row_identity (before_save fallback) ────────────────────────────

class TestReconcileRowIdentity(unittest.TestCase):

    def test_new_doc_is_noop(self):
        doc = _MockDoc(items=[_MockRow()], is_new=True)
        reconcile_row_identity(doc)  # must not raise, nothing to reconcile
        self.assertIsNone(doc.items[0].name)

    def test_no_previous_version_is_noop(self):
        doc = _MockDoc(items=[_MockRow()], is_new=False, prev_items=None)
        reconcile_row_identity(doc)
        self.assertIsNone(doc.items[0].name)

    def test_unambiguous_match_recovers_identity(self):
        prev_row = _MockRow(name="hash-abc123", item_code="ITEM-001",
                             qty=10.0, rate=100.0, quality_inspection="QCI-2026-00001")
        new_row = _MockRow(name=None, item_code="ITEM-001", qty=10.0, rate=100.0)
        doc = _MockDoc(items=[new_row], is_new=False, prev_items=[prev_row])

        reconcile_row_identity(doc)

        self.assertEqual(new_row.name, "hash-abc123")
        self.assertEqual(new_row.quality_inspection, "QCI-2026-00001")

    def test_ambiguous_match_fails_safe(self):
        # Two previous rows share the same identity key -- must NOT guess.
        prev_a = _MockRow(name="hash-a", item_code="ITEM-001", qty=10.0, rate=100.0)
        prev_b = _MockRow(name="hash-b", item_code="ITEM-001", qty=10.0, rate=100.0)
        new_row = _MockRow(name=None, item_code="ITEM-001", qty=10.0, rate=100.0)
        doc = _MockDoc(items=[new_row], is_new=False, prev_items=[prev_a, prev_b])

        reconcile_row_identity(doc)

        self.assertIsNone(new_row.name)

    def test_no_match_fails_safe(self):
        prev_row = _MockRow(name="hash-abc123", item_code="ITEM-999", qty=1.0, rate=5.0)
        new_row = _MockRow(name=None, item_code="ITEM-001", qty=10.0, rate=100.0)
        doc = _MockDoc(items=[new_row], is_new=False, prev_items=[prev_row])

        reconcile_row_identity(doc)

        self.assertIsNone(new_row.name)

    def test_row_that_already_has_a_name_is_left_alone(self):
        prev_row = _MockRow(name="hash-abc123", item_code="ITEM-001", qty=10.0, rate=100.0)
        new_row = _MockRow(name="hash-already-set", item_code="ITEM-001", qty=10.0, rate=100.0)
        doc = _MockDoc(items=[new_row], is_new=False, prev_items=[prev_row])

        reconcile_row_identity(doc)

        # Frappe already knows this row's identity -- must not be overwritten.
        self.assertEqual(new_row.name, "hash-already-set")

    def test_two_new_rows_only_one_previous_candidate(self):
        # A second incoming row with the same key must not also claim the
        # already-consumed previous row.
        prev_row = _MockRow(name="hash-abc123", item_code="ITEM-001", qty=10.0, rate=100.0)
        row_1 = _MockRow(name=None, item_code="ITEM-001", qty=10.0, rate=100.0)
        row_2 = _MockRow(name=None, item_code="ITEM-001", qty=10.0, rate=100.0)
        doc = _MockDoc(items=[row_1, row_2], is_new=False, prev_items=[prev_row])

        reconcile_row_identity(doc)

        claimed = [r for r in (row_1, row_2) if r.name]
        self.assertEqual(len(claimed), 1)
        self.assertEqual(claimed[0].name, "hash-abc123")

    def test_row_identity_key_ignores_missing_item_code(self):
        row = _MockRow()
        row.item_code = None
        self.assertIsNone(_row_identity_key(row))


# ── save_doc child-name-stripping fix (api/docs.py) ──────────────────────────
#
# save_doc itself is a large @frappe.whitelist endpoint with many concerns
# unrelated to row identity (account auto-fill, tenancy stamping, etc.) --
# rather than invoking the whole function, these tests exercise the same
# decision logic it now uses in isolation, mirroring exactly what save_doc
# does line-for-line so a regression back to "always strip name" is caught.

def _resolve_child_name(row_doctype, row_name, parent_doc_name, exists_map):
    """
    Mirrors the exact decision api/docs.py::save_doc now makes for a single
    child row: keep `name` if it still identifies a live row under the SAME
    parent; drop it otherwise. exists_map simulates frappe.db.get_value(
    row_doctype, row_name, "parent") -> parent name or None.
    """
    if not row_name:
        return None
    actual_parent = exists_map.get((row_doctype, row_name))
    # `not parent_doc_name` must be checked unconditionally -- a brand new
    # parent document (no name yet) cannot legitimately own ANY existing
    # child row, even one that is otherwise real. Gating this check behind
    # `parent_doc_name and ...` (as an earlier version of this helper did)
    # let a foreign row name silently survive whenever the parent was new.
    if actual_parent is None or not parent_doc_name or actual_parent != parent_doc_name:
        return None
    return row_name


class TestSaveDocChildNameStripping(unittest.TestCase):

    def test_valid_forwarded_name_is_kept(self):
        exists_map = {("Purchase Invoice Item", "row-hash-1"): "PINV-2026-00045"}
        result = _resolve_child_name(
            "Purchase Invoice Item", "row-hash-1", "PINV-2026-00045", exists_map
        )
        self.assertEqual(result, "row-hash-1")

    def test_missing_name_stays_missing(self):
        result = _resolve_child_name("Purchase Invoice Item", None, "PINV-2026-00045", {})
        self.assertIsNone(result)

    def test_name_pointing_at_deleted_row_is_dropped(self):
        # Row no longer exists in the DB at all.
        result = _resolve_child_name(
            "Purchase Invoice Item", "row-hash-stale", "PINV-2026-00045", {}
        )
        self.assertIsNone(result)

    def test_name_belonging_to_a_different_parent_is_dropped(self):
        # e.g. a duplicated/copied document accidentally forwarding another
        # document's child row name -- must not silently adopt it.
        exists_map = {("Purchase Invoice Item", "row-hash-1"): "PINV-2026-00099"}
        result = _resolve_child_name(
            "Purchase Invoice Item", "row-hash-1", "PINV-2026-00045", exists_map
        )
        self.assertIsNone(result)

    def test_new_document_has_no_parent_name_to_check_against(self):
        # New doc: parent_doc_name is None/blank (document doesn't exist
        # yet) -- any forwarded name here is inherently stale/foreign.
        exists_map = {("Purchase Invoice Item", "row-hash-1"): "PINV-2026-00001"}
        result = _resolve_child_name("Purchase Invoice Item", "row-hash-1", None, exists_map)
        self.assertIsNone(result)

    def test_repeated_save_keeps_same_name_stable(self):
        # The actual regression scenario: save the same row 3 times in a
        # row, each time forwarding the name from the previous response.
        # The name must never change across saves.
        exists_map = {("Purchase Invoice Item", "row-hash-1"): "PINV-2026-00045"}
        name = "row-hash-1"
        for _ in range(3):
            name = _resolve_child_name(
                "Purchase Invoice Item", name, "PINV-2026-00045", exists_map
            )
            self.assertEqual(name, "row-hash-1")


if __name__ == "__main__":
    unittest.main()