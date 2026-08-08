# Copyright (c) 2026, PS Digitise and Contributors
# See license.txt
"""
Tests for Stock Entry cancel/reversal -- Part 2:
_guard_manufacturing_links, on_cancel, _reverse_sle.

Same bind-real-method-onto-a-stand-in pattern as test_stock_entry.py
(Part 1) -- DB-free, exercises the actual controller code.

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.inventory.doctype.stock_entry.test_stock_entry_cancel
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import frappe

from zoho_books_clone.inventory.doctype.stock_entry.stock_entry import StockEntry


def _flags(ignore_manufacturing_guard=False):
    d = {"ignore_manufacturing_guard": ignore_manufacturing_guard}
    return SimpleNamespace(get=lambda k, default=None: d.get(k, default))


def _make_se(stock_entry_type="Manufacture", name="STE-2026-00001", company="VK Herbal",
             work_order=None, ignore_manufacturing_guard=False, **overrides):
    doc = SimpleNamespace(
        doctype="Stock Entry", name=name, stock_entry_type=stock_entry_type,
        company=company, work_order=work_order,
        flags=_flags(ignore_manufacturing_guard),
    )
    for k, v in overrides.items():
        setattr(doc, k, v)
    for name_ in ("_guard_manufacturing_links", "on_cancel", "_reverse_sle", "_adjust_batch_qty"):
        setattr(doc, name_, getattr(StockEntry, name_).__get__(doc))
    return doc


def _sle(name="SLE-1", item_code="ITEM-1", warehouse="WH-1", batch_no=None,
         actual_qty=-5, valuation_rate=100, stock_value_difference=-500,
         posting_date="2026-08-01"):
    return SimpleNamespace(
        name=name, item_code=item_code, warehouse=warehouse, batch_no=batch_no,
        actual_qty=actual_qty, valuation_rate=valuation_rate,
        stock_value_difference=stock_value_difference, posting_date=posting_date,
    )


class TestGuardManufacturingLinks(unittest.TestCase):

    def test_noop_when_flag_set(self):
        doc = _make_se(stock_entry_type="Manufacture", work_order="WO-1",
                        ignore_manufacturing_guard=True)
        doc._guard_manufacturing_links()  # should not raise, no DB calls needed

    def test_noop_for_non_manufacturing_types(self):
        doc = _make_se(stock_entry_type="Material Issue", work_order="WO-1")
        doc._guard_manufacturing_links()  # should not raise

    @patch.object(frappe.db, "get_value")
    def test_blocks_when_linked_to_packing_slip(self, mock_get_value):
        mock_get_value.return_value = "PKG-0001"
        doc = _make_se(stock_entry_type="Material Transfer", work_order=None)
        with self.assertRaises(frappe.ValidationError):
            doc._guard_manufacturing_links()

    @patch.object(frappe.db, "get_value")
    def test_blocks_when_linked_to_work_order(self, mock_get_value):
        def side_effect(doctype, filters=None, fieldname=None):
            if doctype == "Packing Slip":
                return None
            if doctype == "Work Order":
                return "In Process"
            return None
        mock_get_value.side_effect = side_effect
        doc = _make_se(stock_entry_type="Manufacture", work_order="WO-1")
        with self.assertRaises(frappe.ValidationError):
            doc._guard_manufacturing_links()

    @patch.object(frappe.db, "get_value")
    def test_packing_slip_checked_before_work_order(self, mock_get_value):
        # A packing-consumption entry sets work_order too -- packing slip
        # must win so the person is routed to reverse_packing_consumption(),
        # not the Work Order flow.
        def side_effect(doctype, filters=None, fieldname=None):
            if doctype == "Packing Slip":
                return "PKG-0001"
            if doctype == "Work Order":
                return "In Process"
            return None
        mock_get_value.side_effect = side_effect
        doc = _make_se(stock_entry_type="Manufacture", work_order="WO-1")
        with self.assertRaises(frappe.ValidationError) as ctx:
            doc._guard_manufacturing_links()
        self.assertIn("Packing Slip", str(ctx.exception))

    @patch.object(frappe.db, "get_value")
    def test_passes_when_no_links(self, mock_get_value):
        mock_get_value.return_value = None
        doc = _make_se(stock_entry_type="Manufacture", work_order=None)
        doc._guard_manufacturing_links()  # should not raise


class TestOnCancel(unittest.TestCase):

    def test_on_cancel_runs_guard_then_reverse_sle_then_reverses_gl(self):
        doc = _make_se(stock_entry_type="Material Issue")
        calls = []
        doc._guard_manufacturing_links = lambda: calls.append("guard")
        doc._reverse_sle = lambda: calls.append("reverse_sle")
        with patch("zoho_books_clone.accounts.accounting_engine.reverse_voucher") as mock_rev:
            doc.on_cancel()
            mock_rev.assert_called_once_with("Stock Entry", doc.name)
        self.assertEqual(calls, ["guard", "reverse_sle"])

    def test_on_cancel_swallows_gl_reversal_failure(self):
        doc = _make_se(stock_entry_type="Material Issue")
        doc._guard_manufacturing_links = lambda: None
        doc._reverse_sle = lambda: None
        with patch("zoho_books_clone.accounts.accounting_engine.reverse_voucher",
                   side_effect=Exception("GL boom")):
            doc.on_cancel()  # should not raise -- stock reversal already happened


class TestReverseSle(unittest.TestCase):

    @patch("frappe.utils.now", return_value="2026-08-01 10:00:00")
    @patch("frappe.generate_hash", return_value="hash1")
    @patch.object(frappe.db, "commit")
    @patch.object(frappe, "get_doc")
    @patch.object(frappe.db, "set_value")
    @patch.object(frappe.db, "get_value")
    @patch.object(frappe, "get_all")
    def test_marks_original_cancelled_and_creates_negated_reversal(
        self, mock_get_all, mock_get_value, mock_set_value, mock_get_doc, mock_commit, mock_hash, mock_now
    ):
        mock_get_all.return_value = [_sle(actual_qty=-5, stock_value_difference=-500,
                                           valuation_rate=100)]
        mock_get_value.return_value = 10  # current Bin.actual_qty
        rev_doc = MagicMock()
        mock_get_doc.return_value = rev_doc

        doc = _make_se(name="STE-2026-00001")
        doc._reverse_sle()

        # original SLE marked cancelled
        mock_set_value.assert_any_call("Stock Ledger Entry", "SLE-1", "is_cancelled", 1)

        # reversal SLE built with negated qty/value, flagged cancelled
        rev_kwargs = mock_get_doc.call_args[0][0]
        self.assertEqual(rev_kwargs["actual_qty"], 5)          # negation of -5
        self.assertEqual(rev_kwargs["stock_value_difference"], 500)  # negation of -500
        self.assertEqual(rev_kwargs["qty_after_transaction"], 15)    # 10 + 5
        self.assertEqual(rev_kwargs["is_cancelled"], 1)
        rev_doc.insert.assert_called_once_with(ignore_permissions=True)
        mock_commit.assert_called_once()

    @patch("frappe.utils.now", return_value="2026-08-01 10:00:00")
    @patch("frappe.generate_hash", return_value="hash1")
    @patch.object(frappe.db, "commit")
    @patch.object(frappe, "get_doc")
    @patch.object(frappe.db, "set_value")
    @patch.object(frappe.db, "get_value")
    @patch.object(frappe, "get_all")
    def test_adjusts_batch_qty_when_batch_present(
        self, mock_get_all, mock_get_value, mock_set_value, mock_get_doc, mock_commit, mock_hash, mock_now
    ):
        mock_get_all.return_value = [_sle(batch_no="BATCH-1", actual_qty=-5)]
        mock_get_value.return_value = 0
        mock_get_doc.return_value = MagicMock()

        doc = _make_se(name="STE-2026-00001")
        adjust_calls = []
        doc._adjust_batch_qty = lambda batch_no, delta: adjust_calls.append((batch_no, delta))
        doc._reverse_sle()

        self.assertEqual(adjust_calls, [("BATCH-1", 5)])  # rev_qty = -(-5) = 5

    @patch("frappe.utils.now", return_value="2026-08-01 10:00:00")
    @patch("frappe.generate_hash", return_value="hash1")
    @patch.object(frappe.db, "commit")
    @patch.object(frappe, "get_doc")
    @patch.object(frappe.db, "set_value")
    @patch.object(frappe.db, "get_value")
    @patch.object(frappe, "get_all")
    def test_no_batch_adjustment_when_batch_no_absent(
        self, mock_get_all, mock_get_value, mock_set_value, mock_get_doc, mock_commit, mock_hash, mock_now
    ):
        mock_get_all.return_value = [_sle(batch_no=None)]
        mock_get_value.return_value = 0
        mock_get_doc.return_value = MagicMock()

        doc = _make_se(name="STE-2026-00001")
        doc._adjust_batch_qty = MagicMock()
        doc._reverse_sle()
        doc._adjust_batch_qty.assert_not_called()

    @patch("frappe.utils.now", return_value="2026-08-01 10:00:00")
    @patch("frappe.generate_hash", return_value="hash1")
    @patch.object(frappe.db, "commit")
    @patch.object(frappe, "get_doc")
    @patch.object(frappe.db, "set_value")
    @patch.object(frappe.db, "get_value")
    @patch.object(frappe, "get_all")
    def test_reverses_every_active_sle_for_this_voucher(
        self, mock_get_all, mock_get_value, mock_set_value, mock_get_doc, mock_commit, mock_hash, mock_now
    ):
        mock_get_all.return_value = [
            _sle(name="SLE-1", item_code="ITEM-1", warehouse="WH-1", actual_qty=-5),
            _sle(name="SLE-2", item_code="ITEM-2", warehouse="WH-2", actual_qty=8),
        ]
        mock_get_value.return_value = 0
        mock_get_doc.return_value = MagicMock()

        doc = _make_se(name="STE-2026-00001")
        doc._reverse_sle()

        self.assertEqual(mock_get_doc.call_count, 2)
        mock_set_value.assert_any_call("Stock Ledger Entry", "SLE-1", "is_cancelled", 1)
        mock_set_value.assert_any_call("Stock Ledger Entry", "SLE-2", "is_cancelled", 1)

    @patch.object(frappe.db, "commit")
    @patch.object(frappe, "get_all")
    def test_noop_when_no_active_sles(self, mock_get_all, mock_commit):
        mock_get_all.return_value = []
        doc = _make_se(name="STE-2026-00001")
        doc._reverse_sle()  # should not raise
        mock_commit.assert_called_once()

    @patch.object(frappe, "get_all")
    def test_only_queries_non_cancelled_sles_for_this_voucher(self, mock_get_all):
        mock_get_all.return_value = []
        doc = _make_se(name="STE-2026-00001")
        with patch.object(frappe.db, "commit"):
            doc._reverse_sle()
        _, kwargs = mock_get_all.call_args
        self.assertEqual(kwargs["filters"], {
            "voucher_type": "Stock Entry", "voucher_no": "STE-2026-00001", "is_cancelled": 0,
        })


if __name__ == "__main__":
    unittest.main()