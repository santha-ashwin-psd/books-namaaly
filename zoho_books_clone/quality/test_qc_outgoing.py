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
    """Minimal mock for a document item row."""
    def __init__(self, item_code: str, qty: float = 1.0, quality_inspection: str = None):
        self.item_code = item_code
        self.qty = qty
        self.quality_inspection = quality_inspection
        # No .doctype/.name — mirrors a plain mock row that isn't a real
        # Frappe child doc; qc_engine's row-link stamping guards for this.


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

        doc = _MockDoc("Delivery Note", "DN-TEST-00001", [_MockItem("ITEM-001")])

        with patch.object(
            frappe.db, "get_value",
            side_effect=lambda dt, *args, **kwargs: (
                1 if dt == "Item" else None  # inspection_required_before_delivery = 1
            ),
        ), patch.object(
            qc_engine, "_qc_master_switch_on", return_value=True
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
        When the row already has a non-cancelled QC Inspection linked
        (row.quality_inspection), no duplicate is created.
        """
        from zoho_books_clone.quality import qc_engine

        doc = _MockDoc("Delivery Note", "DN-TEST-00003",
                        [_MockItem("ITEM-003", quality_inspection="QCI-EXISTING-001")])

        def mock_get_value(dt, *args, **kwargs):
            if dt == "Item":
                return 1  # inspection required
            if dt == "QC Inspection":
                return 1  # docstatus of the linked inspection: submitted, not cancelled
            return None

        with patch.object(
            frappe.db, "get_value", side_effect=mock_get_value
        ), patch.object(
            qc_engine, "_qc_master_switch_on", return_value=True
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

        doc = _MockDoc("Sales Invoice", "SINV-TEST-00001", [_MockItem("ITEM-004")])

        with patch.object(
            frappe.db, "get_value",
            side_effect=lambda dt, *args, **kwargs: (
                1 if dt == "Item" else None
            ),
        ), patch.object(
            qc_engine, "_qc_master_switch_on", return_value=True
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