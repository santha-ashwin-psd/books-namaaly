# Copyright (c) 2026, PS Digitise and Contributors
# See license.txt
"""
Edge-case tests for Balance Sheet and Profit & Loss beyond the shared
fixture in test_financial_statements_roundtrip.py -- empty ledgers,
liability-only / equity-only books, and the "Stock Received But Not Billed"
classification called out in the source comment (must stay a liability,
not get swept into Net Profit by the NOT IN filter).

DB-free: frappe.db.sql is mocked to return canned rows.

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.reports.tests.test_balance_sheet_and_pnl
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

import frappe

from zoho_books_clone.reports.report.balance_sheet.balance_sheet import get_data as bs_get_data
from zoho_books_clone.reports.report.profit_and_loss.profit_and_loss import get_data as pnl_get_data


class TestBalanceSheetEdgeCases(unittest.TestCase):

    @patch.object(frappe.db, "sql")
    def test_empty_ledger_totals_are_zero(self, mock_sql):
        mock_sql.side_effect = [[], [frappe._dict(net=None)]]
        data = bs_get_data({"as_of_date": "2026-08-31", "company": "VK Herbal"})
        total_assets = next(r["balance"] for r in data if r.get("account") == "Total Assets")
        total_liab_eq = next(r["balance"] for r in data if r.get("account") == "Total Liabilities + Equity")
        self.assertEqual(total_assets, 0)
        self.assertEqual(total_liab_eq, 0)

    @patch.object(frappe.db, "sql")
    def test_stock_received_but_not_billed_stays_a_liability(self, mock_sql):
        # GR/IR clearing: goods received, not yet billed. Must land in
        # LIABILITY_TYPES, not fall through to the pnl NOT-IN bucket and get
        # misclassified as part of Net Profit.
        mock_sql.side_effect = [
            [frappe._dict(account="GR/IR Clearing - VK",
                           account_type="Stock Received But Not Billed", balance=-300)],
            [frappe._dict(net=0)],
        ]
        data = bs_get_data({"as_of_date": "2026-08-31", "company": "VK Herbal"})
        liability_row = next(r for r in data if r.get("account") == "GR/IR Clearing - VK")
        self.assertEqual(liability_row["type"], "Stock Received But Not Billed")
        self.assertEqual(liability_row["balance"], 300)  # sign-flipped to read positive
        total_liab_eq = next(r["balance"] for r in data if r.get("account") == "Total Liabilities + Equity")
        self.assertEqual(total_liab_eq, 300)

    @patch.object(frappe.db, "sql")
    def test_null_pnl_net_treated_as_zero(self, mock_sql):
        mock_sql.side_effect = [
            [frappe._dict(account="Bank - VK", account_type="Bank", balance=1000)],
            [frappe._dict(net=None)],
        ]
        data = bs_get_data({"as_of_date": "2026-08-31", "company": "VK Herbal"})
        net_profit_row = next(r for r in data if r.get("account") == "Net Profit (current period)")
        self.assertEqual(net_profit_row["balance"], 0)


class TestProfitAndLossEdgeCases(unittest.TestCase):

    @patch.object(frappe.db, "sql", return_value=[])
    def test_no_activity_gives_zero_net_profit(self, mock_sql):
        data = pnl_get_data({
            "from_date": "2026-08-01", "to_date": "2026-08-31", "company": "VK Herbal",
        })
        net = next(r["amount"] for r in data if r.get("account") == "Net Profit / Loss")
        self.assertEqual(net, 0)

    @patch.object(frappe.db, "sql")
    def test_income_only_no_expenses_is_pure_profit(self, mock_sql):
        mock_sql.return_value = [frappe._dict(account="Sales - VK", account_type="Income", amount=5000)]
        data = pnl_get_data({
            "from_date": "2026-08-01", "to_date": "2026-08-31", "company": "VK Herbal",
        })
        net = next(r["amount"] for r in data if r.get("account") == "Net Profit / Loss")
        total_expense = next(r["amount"] for r in data if r.get("account") == "Total Expenses")
        self.assertEqual(net, 5000)
        self.assertEqual(total_expense, 0)

    @patch.object(frappe.db, "sql")
    def test_stock_adjustment_credit_reduces_total_expense(self, mock_sql):
        # A Stock Adjustment credit balance (stock received in, valued)
        # should REDUCE total expense, not add to it -- confirms the sign
        # flip applies uniformly across all three expense-side types.
        mock_sql.return_value = [
            frappe._dict(account="COGS - VK", account_type="Cost of Goods Sold", amount=-800),
            frappe._dict(account="Stock Adjustment - VK", account_type="Stock Adjustment", amount=200),
        ]
        data = pnl_get_data({
            "from_date": "2026-08-01", "to_date": "2026-08-31", "company": "VK Herbal",
        })
        total_expense = next(r["amount"] for r in data if r.get("account") == "Total Expenses")
        # COGS flips -800 -> 800; Stock Adjustment flips 200 -> -200 (credit reduces expense)
        self.assertEqual(total_expense, 600)

    @patch.object(frappe.db, "sql")
    def test_expenses_exceeding_income_gives_negative_net_profit(self, mock_sql):
        mock_sql.return_value = [
            frappe._dict(account="Sales - VK", account_type="Income", amount=1000),
            frappe._dict(account="Rent - VK", account_type="Expense", amount=-1500),
        ]
        data = pnl_get_data({
            "from_date": "2026-08-01", "to_date": "2026-08-31", "company": "VK Herbal",
        })
        net = next(r["amount"] for r in data if r.get("account") == "Net Profit / Loss")
        self.assertEqual(net, -500)


if __name__ == "__main__":
    unittest.main()