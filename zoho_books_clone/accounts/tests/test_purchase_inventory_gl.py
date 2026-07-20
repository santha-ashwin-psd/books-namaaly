"""
Pure-function tests for perpetual inventory purchase debit split (Model B GR/IR).

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.accounts.tests.test_purchase_inventory_gl
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from zoho_books_clone.accounts.inventory_gl import (
    build_purchase_invoice_debit_lines,
    classify_purchase_item_amounts,
    is_purchase_stock_receipt,
)


class TestPurchaseInventoryGl(unittest.TestCase):

    def test_purchase_receipt_refs_use_grir(self):
        self.assertTrue(is_purchase_stock_receipt("Purchase Receipt"))
        self.assertTrue(is_purchase_stock_receipt("Purchase Invoice"))
        self.assertFalse(is_purchase_stock_receipt("Stock Entry"))
        self.assertFalse(is_purchase_stock_receipt(None))

    def test_debit_lines_split_stock_and_expense(self):
        doc = SimpleNamespace(
            doctype="Purchase Invoice",
            name="PINV-001",
            posting_date="2026-07-20",
            company="Demo Co",
            fiscal_year="2026-2027 - Demo Co",
            cost_center="",
        )
        lines = build_purchase_invoice_debit_lines(
            doc,
            stock_total=800,
            expense_total=200,
            grir_account="Stock Received But Not Billed - Demo Co",
            expense_account="Office Supplies - Demo Co",
        )
        self.assertEqual(len(lines), 2)
        by_acct = {r["account"]: r["debit"] for r in lines}
        self.assertEqual(by_acct["Stock Received But Not Billed - Demo Co"], 800)
        self.assertEqual(by_acct["Office Supplies - Demo Co"], 200)
        self.assertEqual(sum(r["debit"] for r in lines), 1000)
        self.assertTrue(all(r["credit"] == 0 for r in lines))

    def test_stock_only_bill_does_not_require_expense_line(self):
        doc = SimpleNamespace(
            doctype="Purchase Invoice",
            name="PINV-002",
            posting_date="2026-07-20",
            company="Demo Co",
            fiscal_year="",
            cost_center="",
        )
        lines = build_purchase_invoice_debit_lines(
            doc,
            stock_total=500,
            expense_total=0,
            grir_account="Stock Received But Not Billed - Demo Co",
            expense_account=None,
        )
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["account"], "Stock Received But Not Billed - Demo Co")
        self.assertEqual(lines[0]["debit"], 500)

    def test_stock_bill_without_grir_throws(self):
        doc = SimpleNamespace(
            doctype="Purchase Invoice",
            name="PINV-003",
            posting_date="2026-07-20",
            company="Demo Co",
            fiscal_year="",
            cost_center="",
        )
        with self.assertRaises(Exception):
            build_purchase_invoice_debit_lines(
                doc,
                stock_total=100,
                expense_total=0,
                grir_account=None,
                expense_account="Expense - Demo Co",
            )

    @patch("zoho_books_clone.accounts.inventory_gl.frappe")
    def test_classify_splits_by_is_stock_item(self, mock_frappe):
        mock_frappe.db.get_all.return_value = [
            SimpleNamespace(name="STOCK-1", is_stock_item=1, inventory_account=None),
            SimpleNamespace(name="SVC-1", is_stock_item=0, inventory_account=None),
        ]
        # get_inventory_account fallback path when inventory_account is blank
        mock_frappe.db.exists.return_value = False
        mock_frappe.db.get_value.return_value = "Stock In Hand - Demo Co"

        doc = SimpleNamespace(
            company="Demo Co",
            items=[
                SimpleNamespace(item_code="STOCK-1", amount=400, qty=4, rate=100),
                SimpleNamespace(item_code="SVC-1", amount=100, qty=1, rate=100),
            ],
        )
        split = classify_purchase_item_amounts(doc)
        self.assertEqual(split["stock_total"], 400)
        self.assertEqual(split["expense_total"], 100)
        self.assertTrue(split["has_stock"])
        self.assertTrue(split["has_expense"])


if __name__ == "__main__":
    unittest.main()
