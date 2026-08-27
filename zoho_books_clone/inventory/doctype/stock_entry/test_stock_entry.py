# Copyright (c) 2026, PS Digitise and Contributors
# See license.txt
"""
Tests for Stock Entry (inventory/doctype/stock_entry/stock_entry.py) --
Part 1: validation, totals, and on_submit (SLE creation + GL posting).

Stock Entry moves real inventory and posts GL on submit, so this exercises
the actual controller code rather than reimplementing it, using the same
bind-real-method-onto-a-stand-in pattern as
inventory/tests/test_landed_cost_guardrails.py -- keeps tests fast/DB-free
while still running the real _validate_items/_make_sle/_post_gl_entries.

Part 2 (cancel/reversal, manufacturing-link guard) is a separate file.

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.inventory.doctype.stock_entry.test_stock_entry
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe

from zoho_books_clone.inventory.doctype.stock_entry.stock_entry import StockEntry


def _row(item_code="ITEM-1", qty=10, uom="Nos", s_warehouse=None, t_warehouse=None,
         batch_no=None, basic_rate=100, amount=None, is_scrap_item=0, idx=1):
    return SimpleNamespace(
        item_code=item_code, item_name=None, qty=qty, uom=uom,
        s_warehouse=s_warehouse, t_warehouse=t_warehouse, batch_no=batch_no,
        basic_rate=basic_rate, amount=amount if amount is not None else qty * basic_rate,
        conversion_factor=1, qty_in_stock_uom=qty, is_scrap_item=is_scrap_item, idx=idx,
    )


def _make_se(stock_entry_type="Material Issue", items=None, company="VK Herbal",
             posting_date="2026-08-01", posting_time="10:00:00", **overrides):
    doc = SimpleNamespace(
        doctype="Stock Entry", name="STE-2026-00001",
        stock_entry_type=stock_entry_type, items=items or [],
        company=company, posting_date=posting_date, posting_time=posting_time,
        from_warehouse=None, to_warehouse=None,
        total_outgoing_value=0, total_incoming_value=0, value_difference=0,
        operating_cost_absorbed=0, manufacturing_variance_loss=0,
        work_order=None, reference_doctype=None, reference_name=None,
        adjustment_account=None, flags=SimpleNamespace(get=lambda k, default=None: None),
    )
    for k, v in overrides.items():
        setattr(doc, k, v)
    for name in ("_set_defaults", "_validate_fiscal_year", "_auto_assign_outgoing_batches",
                 "_validate_items", "_calculate_totals", "validate",
                 "_make_sle", "_create_sle", "_adjust_batch_qty", "_sync_bin",
                 "_post_gl_entries", "_get_account_by_type", "on_submit"):
        setattr(doc, name, getattr(StockEntry, name).__get__(doc))
    return doc


class TestValidateItems(unittest.TestCase):

    @patch.object(frappe.db, "get_value")
    def test_empty_items_throws(self, mock_get_value):
        doc = _make_se(items=[])
        with self.assertRaises(frappe.ValidationError):
            doc._validate_items()

    @patch.object(frappe.db, "exists")
    @patch.object(frappe.db, "get_value")
    def test_zero_qty_throws_for_material_issue(self, mock_get_value, mock_exists):
        mock_get_value.return_value = 0  # has_batch_no etc
        doc = _make_se(items=[_row(qty=0, s_warehouse="WH-1")])
        with self.assertRaises(frappe.ValidationError):
            doc._validate_items()

    @patch.object(frappe.db, "exists")
    @patch.object(frappe.db, "get_value")
    def test_stock_adjustment_allows_negative_qty(self, mock_get_value, mock_exists):
        mock_get_value.return_value = 0  # not batch-tracked
        row = _row(qty=-5, t_warehouse="WH-1")
        doc = _make_se(stock_entry_type="Stock Adjustment", items=[row])
        doc._validate_items()  # should not raise
        self.assertEqual(row.qty_in_stock_uom, -5)

    @patch.object(frappe.db, "exists")
    @patch.object(frappe.db, "get_value")
    def test_missing_source_warehouse_throws(self, mock_get_value, mock_exists):
        mock_get_value.return_value = 0
        doc = _make_se(stock_entry_type="Material Issue", items=[_row(s_warehouse=None)])
        with self.assertRaises(frappe.ValidationError):
            doc._validate_items()

    @patch.object(frappe.db, "get_value")
    def test_negative_stock_blocked_by_default(self, mock_get_value):
        def side_effect(doctype, filters=None, fieldname=None):
            if doctype == "Item":
                return 0
            if doctype == "Bin":
                return 3  # less than qty=10 requested
            if doctype == "Manufacturing Settings":
                return 0
            return None
        mock_get_value.side_effect = side_effect
        doc = _make_se(items=[_row(qty=10, s_warehouse="WH-1")])
        with self.assertRaises(frappe.ValidationError):
            doc._validate_items()

    @patch.object(frappe.db, "get_single_value")
    @patch.object(frappe.db, "get_value")
    def test_negative_stock_allowed_when_setting_enabled(self, mock_get_value, mock_single):
        mock_single.return_value = 1  # allow_negative_stock = True
        def side_effect(doctype, filters=None, fieldname=None):
            if doctype == "Item":
                return 0
            if doctype == "Bin":
                return 3
            return None
        mock_get_value.side_effect = side_effect
        doc = _make_se(items=[_row(qty=10, s_warehouse="WH-1")])
        doc._validate_items()  # should not raise

    @patch.object(frappe.db, "get_value")
    def test_batch_tracked_item_without_batch_no_throws(self, mock_get_value):
        def side_effect(doctype, filters=None, fieldname=None):
            if doctype == "Item" and fieldname == "has_batch_no":
                return 1
            if doctype == "Item" and fieldname == "valuation_method":
                return "FIFO"
            if doctype == "Manufacturing Settings":
                return 0
            return None
        mock_get_value.side_effect = side_effect
        doc = _make_se(items=[_row(t_warehouse="WH-1", batch_no=None)],
                        stock_entry_type="Material Receipt")
        with self.assertRaises(frappe.ValidationError):
            doc._validate_items()

    @patch.object(frappe.db, "exists")
    @patch.object(frappe.db, "get_value")
    def test_batch_belonging_to_other_item_throws(self, mock_get_value, mock_exists):
        mock_exists.return_value = True
        def side_effect(doctype, filters=None, fieldname=None):
            if doctype == "Item":
                return 1
            if doctype == "Batch" and fieldname == "disabled":
                return 0
            if doctype == "Batch" and fieldname == "item":
                return "OTHER-ITEM"
            return None
        mock_get_value.side_effect = side_effect
        doc = _make_se(items=[_row(t_warehouse="WH-1", batch_no="BATCH-1")],
                        stock_entry_type="Material Receipt")
        with self.assertRaises(frappe.ValidationError):
            doc._validate_items()

    @patch.object(frappe.db, "exists")
    @patch.object(frappe.db, "get_value")
    def test_batch_no_cleared_when_item_not_batch_tracked(self, mock_get_value, mock_exists):
        mock_get_value.return_value = 0  # has_batch_no = 0 everywhere
        row = _row(t_warehouse="WH-1", batch_no="STALE-BATCH")
        doc = _make_se(items=[row], stock_entry_type="Material Receipt")
        doc._validate_items()
        self.assertIsNone(row.batch_no)

    @patch.object(frappe.db, "exists")
    @patch.object(frappe.db, "get_value")
    def test_manufacture_row_needs_at_least_one_warehouse(self, mock_get_value, mock_exists):
        mock_get_value.return_value = 0
        doc = _make_se(stock_entry_type="Manufacture",
                        items=[_row(s_warehouse=None, t_warehouse=None)])
        with self.assertRaises(frappe.ValidationError):
            doc._validate_items()

    @patch.object(frappe.db, "exists")
    @patch.object(frappe.db, "get_value")
    def test_row_amount_computed_from_qty_and_rate(self, mock_get_value, mock_exists):
        mock_get_value.return_value = 0
        row = _row(qty=4, basic_rate=250, t_warehouse="WH-1", amount=0)
        doc = _make_se(stock_entry_type="Material Receipt", items=[row])
        doc._validate_items()
        self.assertEqual(row.amount, 1000)


class TestCalculateTotals(unittest.TestCase):

    def test_material_issue_totals_outgoing_only(self):
        doc = _make_se(stock_entry_type="Material Issue", items=[
            _row(s_warehouse="WH-1", qty=5, basic_rate=100),  # amount 500
        ])
        doc._calculate_totals()
        self.assertEqual(doc.total_outgoing_value, 500)
        self.assertEqual(doc.total_incoming_value, 0)
        self.assertEqual(doc.value_difference, -500)

    def test_material_transfer_counts_both_sides_same_row(self):
        doc = _make_se(stock_entry_type="Material Transfer", items=[
            _row(s_warehouse="WH-1", t_warehouse="WH-2", qty=5, basic_rate=100),
        ])
        doc._calculate_totals()
        self.assertEqual(doc.total_outgoing_value, 500)
        self.assertEqual(doc.total_incoming_value, 500)
        self.assertEqual(doc.value_difference, 0)

    def test_manufacture_does_not_fake_balance_across_rows(self):
        # raw material consumed (source only) + FG received (target only),
        # different values -- must NOT net to zero by construction.
        doc = _make_se(stock_entry_type="Manufacture", items=[
            _row(item_code="RAW", s_warehouse="WH-1", qty=10, basic_rate=50),   # 500 out
            _row(item_code="FG", t_warehouse="WH-2", qty=1, basic_rate=800),    # 800 in
        ])
        doc._calculate_totals()
        self.assertEqual(doc.total_outgoing_value, 500)
        self.assertEqual(doc.total_incoming_value, 800)
        self.assertEqual(doc.value_difference, 300)


class TestMakeSle(unittest.TestCase):

    @patch("frappe.utils.now", return_value="2026-08-01 10:00:00")
    @patch("frappe.generate_hash", return_value="hash1")
    @patch.object(frappe.db, "commit")
    @patch.object(frappe, "get_doc")
    @patch.object(frappe.db, "get_value")
    def test_material_issue_creates_negative_outgoing_sle(self, mock_get_value, mock_get_doc, mock_commit, mock_hash, mock_now):
        mock_get_value.return_value = 20  # current Bin qty
        sle_doc = MagicMock()
        mock_get_doc.return_value = sle_doc

        row = _row(item_code="ITEM-1", s_warehouse="WH-1", qty=5, basic_rate=100,
                    amount=500)
        row.qty_in_stock_uom = 5
        doc = _make_se(stock_entry_type="Material Issue", items=[row])
        doc._make_sle()

        sle_kwargs = mock_get_doc.call_args[0][0]
        self.assertEqual(sle_kwargs["actual_qty"], -5)
        self.assertEqual(sle_kwargs["warehouse"], "WH-1")
        self.assertEqual(sle_kwargs["stock_value_difference"], -500)
        sle_doc.insert.assert_called_once_with(ignore_permissions=True)

    @patch("frappe.utils.now", return_value="2026-08-01 10:00:00")
    @patch("frappe.generate_hash", return_value="hash1")
    @patch.object(frappe.db, "commit")
    @patch.object(frappe, "get_doc")
    @patch.object(frappe.db, "get_value")
    def test_material_receipt_creates_positive_incoming_sle(self, mock_get_value, mock_get_doc, mock_commit, mock_hash, mock_now):
        mock_get_value.return_value = 0
        sle_doc = MagicMock()
        mock_get_doc.return_value = sle_doc

        row = _row(item_code="ITEM-1", t_warehouse="WH-2", qty=8, basic_rate=50,
                    amount=400)
        row.qty_in_stock_uom = 8
        doc = _make_se(stock_entry_type="Material Receipt", items=[row])
        doc._make_sle()

        sle_kwargs = mock_get_doc.call_args[0][0]
        self.assertEqual(sle_kwargs["actual_qty"], 8)
        self.assertEqual(sle_kwargs["warehouse"], "WH-2")
        self.assertEqual(sle_kwargs["stock_value_difference"], 400)

    @patch("frappe.utils.now", return_value="2026-08-01 10:00:00")
    @patch("frappe.generate_hash", return_value="hash1")
    @patch.object(frappe.db, "commit")
    @patch.object(frappe, "get_doc")
    @patch.object(frappe.db, "get_value")
    def test_material_transfer_creates_both_legs(self, mock_get_value, mock_get_doc, mock_commit, mock_hash, mock_now):
        mock_get_value.return_value = 10
        mock_get_doc.return_value = MagicMock()

        row = _row(item_code="ITEM-1", s_warehouse="WH-1", t_warehouse="WH-2",
                    qty=3, basic_rate=100, amount=300)
        row.qty_in_stock_uom = 3
        doc = _make_se(stock_entry_type="Material Transfer", items=[row])
        doc._make_sle()

        self.assertEqual(mock_get_doc.call_count, 2)
        actual_qtys = sorted(c[0][0]["actual_qty"] for c in mock_get_doc.call_args_list)
        self.assertEqual(actual_qtys, [-3, 3])


class TestPostGlEntries(unittest.TestCase):

    @patch("zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry.make_gl_entries")
    @patch("zoho_books_clone.accounts.inventory_gl.get_cogs_account")
    @patch("zoho_books_clone.accounts.inventory_gl.get_inventory_account")
    def test_material_issue_debits_cogs_credits_inventory(self, mock_inv_acct, mock_cogs_acct, mock_gl):
        mock_inv_acct.return_value = "Inventory Asset - VK"
        mock_cogs_acct.return_value = "COGS - VK"
        doc = _make_se(stock_entry_type="Material Issue", total_outgoing_value=500)
        doc._post_gl_entries()

        gl_map = mock_gl.call_args[0][0]
        by_account = {r["account"]: (r["debit"], r["credit"]) for r in gl_map}
        self.assertEqual(by_account["COGS - VK"], (500, 0))
        self.assertEqual(by_account["Inventory Asset - VK"], (0, 500))
        total_debit = sum(r["debit"] for r in gl_map)
        total_credit = sum(r["credit"] for r in gl_map)
        self.assertEqual(total_debit, total_credit)

    @patch("frappe.log_error")
    @patch("zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry.make_gl_entries")
    @patch("zoho_books_clone.accounts.inventory_gl.get_cogs_account")
    @patch("zoho_books_clone.accounts.inventory_gl.get_inventory_account")
    def test_material_issue_skips_gl_when_no_cogs_account(self, mock_inv_acct, mock_cogs_acct, mock_gl, mock_log):
        mock_inv_acct.return_value = "Inventory Asset - VK"
        mock_cogs_acct.return_value = None
        doc = _make_se(stock_entry_type="Material Issue", total_outgoing_value=500)
        doc._post_gl_entries()
        mock_gl.assert_not_called()
        mock_log.assert_called_once()

    @patch("zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry.make_gl_entries")
    @patch("zoho_books_clone.accounts.inventory_gl.get_stock_adjustment_account")
    @patch("zoho_books_clone.accounts.inventory_gl.is_purchase_stock_receipt", return_value=False)
    @patch("zoho_books_clone.accounts.inventory_gl.get_inventory_account")
    def test_material_receipt_manual_debits_inventory_credits_adjustment(
        self, mock_inv_acct, mock_is_purchase, mock_adj_acct, mock_gl
    ):
        mock_inv_acct.return_value = "Inventory Asset - VK"
        mock_adj_acct.return_value = "Stock Adjustment - VK"
        doc = _make_se(stock_entry_type="Material Receipt", total_incoming_value=750)
        doc._post_gl_entries()

        gl_map = mock_gl.call_args[0][0]
        by_account = {r["account"]: (r["debit"], r["credit"]) for r in gl_map}
        self.assertEqual(by_account["Inventory Asset - VK"], (750, 0))
        self.assertEqual(by_account["Stock Adjustment - VK"], (0, 750))

    @patch("zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry.make_gl_entries")
    @patch("zoho_books_clone.accounts.inventory_gl.get_grir_account")
    @patch("zoho_books_clone.accounts.inventory_gl.is_purchase_stock_receipt", return_value=True)
    @patch("zoho_books_clone.accounts.inventory_gl.get_inventory_account")
    def test_purchase_linked_receipt_credits_grir_not_adjustment(
        self, mock_inv_acct, mock_is_purchase, mock_grir_acct, mock_gl
    ):
        mock_inv_acct.return_value = "Inventory Asset - VK"
        mock_grir_acct.return_value = "GR/IR - VK"
        doc = _make_se(stock_entry_type="Material Receipt", total_incoming_value=900,
                        reference_doctype="Purchase Invoice")
        doc._post_gl_entries()

        gl_map = mock_gl.call_args[0][0]
        by_account = {r["account"]: (r["debit"], r["credit"]) for r in gl_map}
        self.assertEqual(by_account["Inventory Asset - VK"], (900, 0))
        self.assertEqual(by_account["GR/IR - VK"], (0, 900))

    @patch("zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry.make_gl_entries")
    def test_material_transfer_posts_no_gl(self, mock_gl):
        doc = _make_se(stock_entry_type="Material Transfer", total_outgoing_value=500,
                        total_incoming_value=500)
        doc._post_gl_entries()
        mock_gl.assert_not_called()

    @patch("frappe.msgprint")
    @patch("frappe.log_error")
    @patch("zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry.make_gl_entries",
           side_effect=Exception("DB down"))
    @patch("zoho_books_clone.accounts.inventory_gl.get_cogs_account")
    @patch("zoho_books_clone.accounts.inventory_gl.get_inventory_account")
    def test_gl_posting_failure_does_not_raise(self, mock_inv_acct, mock_cogs_acct, mock_gl, mock_log, mock_msg):
        mock_inv_acct.return_value = "Inventory Asset - VK"
        mock_cogs_acct.return_value = "COGS - VK"
        doc = _make_se(stock_entry_type="Material Issue", total_outgoing_value=500)
        doc._post_gl_entries()  # should not raise -- stock movement must not roll back
        mock_log.assert_called_once()
        mock_msg.assert_called_once()


class TestOnSubmit(unittest.TestCase):

    @patch.object(frappe.db, "commit")
    def test_on_submit_calls_make_sle_then_post_gl(self, mock_commit):
        doc = _make_se(stock_entry_type="Material Issue")
        calls = []
        doc._make_sle = lambda: calls.append("sle")
        doc._post_gl_entries = lambda: calls.append("gl")
        doc.on_submit()
        self.assertEqual(calls, ["sle", "gl"])
        # commit now happens once, in on_submit(), after both steps --
        # not inside _make_sle() partway through (see stock_link fix).
        mock_commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()