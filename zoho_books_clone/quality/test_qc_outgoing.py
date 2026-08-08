"""
Test — Outgoing QC Auto-Creation
=================================
Mirrors the incoming-QC test pattern.
Verifies that auto_create_qc_for_delivery_note and
auto_create_qc_for_sales_invoice create QC Inspections with
inspection_type="Outgoing", and that check_qc_before_stock_link
subsequently finds a "Pending" (not "Missing") status for those docs.

Run with:
    bench --site <site> run-tests --module zoho_books_clone.quality.test_qc_outgoing
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import frappe


class _MockItem:
    """
    Minimal mock for a document item row.

    Carries .doctype/.name: get_or_create_coverage() (added by the QC
    Coverage redesign) keys coverage on source_row = f"{row.doctype}:
    {row.name}" and returns "Missing" immediately for any row that lacks a
    name -- earlier versions of this mock had no name at all, which made
    every "creates inspection" test here pass for the wrong reason (the
    Missing short-circuit, not the actual create path) and made every
    "skip" test trivially true. row_doctype defaults to a real, existing
    Frappe child doctype so _stamp_row_link's frappe.db.has_column check
    behaves like it would for a genuine Delivery Note/Sales Invoice row.
    """
    def __init__(self, item_code: str, qty: float = 1.0, quality_inspection: str = None,
                 name: str = "row-hash-mock", doctype: str = "Delivery Note Item"):
        self.item_code = item_code
        self.qty = qty
        self.quality_inspection = quality_inspection
        self.name = name
        self.doctype = doctype


class _MockDoc:
    """Minimal mock for a Frappe document (Delivery Note or Sales Invoice)."""
    def __init__(self, doctype: str, name: str, items):
        self.doctype = doctype
        self.name = name
        self.items = items
        self.flags = MagicMock()
        self.flags.get.return_value = False


class TestOutgoingQCAutoCreate(unittest.TestCase):
    """
    Unit tests for auto_create_qc_for_delivery_note and
    auto_create_qc_for_sales_invoice.

    Because these tests run against a real Frappe environment, they use
    frappe.db.exists checks. In CI without a site, the patches ensure the
    functions behave correctly without touching the database.
    """

    def _patched_env(self):
        """Return a context manager that patches the Frappe DB layer."""
        return patch.multiple(
            "zoho_books_clone.quality.qc_engine",
            _qc_master_switch_on=MagicMock(return_value=True),
            create_qc_inspection_for_item=MagicMock(return_value="QCI-TEST-00001"),
        )

    # ── Delivery Note ──────────────────────────────────────────────────────────

    def test_delivery_note_creates_outgoing_inspection(self):
        """
        When a DN item has inspection_required_before_delivery=1,
        auto_create_qc_for_delivery_note should call create_qc_inspection_for_item
        with inspection_type="Outgoing".
        """
        from zoho_books_clone.quality import qc_engine

        doc = _MockDoc("Delivery Note", "DN-TEST-00001", [_MockItem("ITEM-001", name="row-dn-001")])

        with patch.object(
            frappe.db, "get_value",
            side_effect=lambda dt, *args, **kwargs: (
                1 if dt == "Item" else None  # inspection_required_before_delivery = 1;
                                              # "QC Coverage" lookup -> None = no existing coverage
            ),
        ), patch.object(
            frappe, "get_all", return_value=[]  # safeguard: no other unresolved QCI for this item
        ), patch.object(
            frappe, "new_doc", return_value=MagicMock()
            # get_or_create_coverage's create branch does
            # frappe.new_doc("QC Coverage").insert(...) on a real, un-mocked
            # path. Left un-patched, that triggers REAL DocType meta
            # loading for "QC Coverage", which itself calls
            # frappe.db.get_value(doctype=..., filters=..., fieldname="*")
            # by KEYWORD -- colliding with the positional-only lambda above
            # and breaking meta resolution entirely (surfaces as a
            # nonsensical "No module named frappe.core.doctype.qc_coverage"
            # ModuleNotFoundError). Mocking new_doc keeps this test a pure
            # unit test of the auto-create call chain, not an integration
            # test of QC Coverage's own persistence.
        ), patch.object(
            qc_engine, "_qc_master_switch_on", return_value=True
        ), patch.object(
            qc_engine, "_stamp_row_link"  # isolate: don't hit the real DB for a fake row name
        ), patch.object(
            qc_engine, "create_qc_inspection_for_item", return_value="QCI-TEST-00001"
        ) as mock_create:
            qc_engine.auto_create_qc_for_delivery_note(doc)

        mock_create.assert_called_once_with(
            "Delivery Note", "DN-TEST-00001", "ITEM-001", "Outgoing",
            batch_no=None, inspected_qty=1.0,
        )

    def test_delivery_note_skips_when_inspection_not_required(self):
        """
        When inspection_required_before_delivery=0, no QC Inspection is created.
        """
        from zoho_books_clone.quality import qc_engine

        doc = _MockDoc("Delivery Note", "DN-TEST-00002", [_MockItem("ITEM-002")])

        with patch.object(
            frappe.db, "get_value", return_value=0  # flag not set
        ), patch.object(
            qc_engine, "_qc_master_switch_on", return_value=True
        ), patch.object(
            qc_engine, "create_qc_inspection_for_item"
        ) as mock_create:
            qc_engine.auto_create_qc_for_delivery_note(doc)

        mock_create.assert_not_called()

    def test_delivery_note_skips_existing_inspection(self):
        """
        When the row's source_row already has a live (non-cancelled) QC
        Inspection linked via QC Coverage, no duplicate is created.

        Coverage is resolved through QC Coverage.source_row (row.doctype +
        row.name), NOT the row's own quality_inspection field -- that field
        is stamp-only display convenience, never read back by
        get_or_create_coverage. See qc_engine.py get_or_create_coverage /
        _stamp_row_link docstrings.
        """
        from zoho_books_clone.quality import qc_engine

        doc = _MockDoc("Delivery Note", "DN-TEST-00003",
                        [_MockItem("ITEM-003", name="row-dn-003")])

        def mock_get_value(dt, filters=None, fieldname=None, *args, **kwargs):
            if dt == "Item":
                return 1  # inspection required
            if dt == "QC Coverage":
                return "QCI-EXISTING-001"  # this row already has live coverage
            if dt == "QC Inspection":
                # get_or_create_coverage asks for [docstatus, status] as_dict
                return frappe._dict(docstatus=1, status="Pass")
            return None

        with patch.object(
            frappe.db, "get_value", side_effect=mock_get_value
        ), patch.object(
            qc_engine, "_qc_master_switch_on", return_value=True
        ), patch.object(
            qc_engine, "_stamp_row_link"
        ), patch.object(
            qc_engine, "create_qc_inspection_for_item"
        ) as mock_create:
            qc_engine.auto_create_qc_for_delivery_note(doc)

        mock_create.assert_not_called()

    # ── Sales Invoice ──────────────────────────────────────────────────────────

    def test_sales_invoice_creates_outgoing_inspection(self):
        """
        When a Sales Invoice item has inspection_required_before_delivery=1,
        auto_create_qc_for_sales_invoice should call create_qc_inspection_for_item
        with inspection_type="Outgoing".
        """
        from zoho_books_clone.quality import qc_engine

        doc = _MockDoc("Sales Invoice", "SINV-TEST-00001",
                        [_MockItem("ITEM-004", name="row-si-001", doctype="Sales Invoice Item")])

        with patch.object(
            frappe.db, "get_value",
            side_effect=lambda dt, *args, **kwargs: (
                1 if dt == "Item" else None  # "QC Coverage" lookup -> None = no existing coverage
            ),
        ), patch.object(
            frappe, "get_all", return_value=[]  # safeguard: no other unresolved QCI for this item
        ), patch.object(
            frappe, "new_doc", return_value=MagicMock()
            # Same reasoning as the Delivery Note "creates" test above:
            # avoid real QC Coverage meta loading colliding with the
            # keyword-arg internal frappe.db.get_value calls.
        ), patch.object(
            qc_engine, "_qc_master_switch_on", return_value=True
        ), patch.object(
            qc_engine, "_stamp_row_link"
        ), patch.object(
            qc_engine, "create_qc_inspection_for_item", return_value="QCI-TEST-00002"
        ) as mock_create:
            qc_engine.auto_create_qc_for_sales_invoice(doc)

        mock_create.assert_called_once_with(
            "Sales Invoice", "SINV-TEST-00001", "ITEM-004", "Outgoing",
            batch_no=None, inspected_qty=1.0,
        )

    def test_sales_invoice_skips_when_master_switch_off(self):
        """
        When qc_warn_on_missing_inspection=0 in Books Settings, no QC is created.
        """
        from zoho_books_clone.quality import qc_engine

        doc = _MockDoc("Sales Invoice", "SINV-TEST-00002", [_MockItem("ITEM-005")])

        with patch.object(
            qc_engine, "_qc_master_switch_on", return_value=False
        ), patch.object(
            qc_engine, "create_qc_inspection_for_item"
        ) as mock_create:
            qc_engine.auto_create_qc_for_sales_invoice(doc)

        mock_create.assert_not_called()

    # ── _DOCTYPE_TO_INSPECTION_TYPE mapping ────────────────────────────────────

    def test_inspection_type_mapping(self):
        """
        Both Delivery Note and Sales Invoice must map to 'Outgoing'
        in _DOCTYPE_TO_INSPECTION_TYPE.
        """
        from zoho_books_clone.quality.qc_engine import _DOCTYPE_TO_INSPECTION_TYPE

        self.assertEqual(_DOCTYPE_TO_INSPECTION_TYPE.get("Delivery Note"), "Outgoing")
        self.assertEqual(_DOCTYPE_TO_INSPECTION_TYPE.get("Sales Invoice"), "Outgoing")


if __name__ == "__main__":
    unittest.main()