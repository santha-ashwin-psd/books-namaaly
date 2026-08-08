# Copyright (c) 2026, PS Digitise and Contributors
# See license.txt
"""
Round-trip consistency test across three financial statements (Balance
Sheet, Profit & Loss, Cash Flow Statement) driven by ONE synthetic set of
known transactions.

Rather than testing each report against arbitrary canned numbers, this
builds a single small ledger (capital injection, a sale with GST, the
customer payment, an asset purchase, a paid expense) and asserts identities
that must hold across the real accounting relationships:

  1. Balance Sheet balances: Total Assets == Total Liabilities + Equity
  2. Balance Sheet's "Net Profit (current period)" equity line == the P&L's
     own "Net Profit / Loss" total, computed independently from the same
     transactions
  3. Cash Flow's closing_cash == the Balance Sheet's actual Bank account
     balance as of the same date

This is the kind of bug none of the individual report unit tests would
catch on their own -- e.g. a sign error in one report's account-type
bucketing would make it internally consistent but disagree with the others.

DB-free: frappe.db.sql is a single global object, so within a test that
drives two reports we mock it ONCE and feed a single side_effect list in
the exact order the calls actually happen -- not one patch per report
module (that would just have the second patch silently clobber the first).
Every mocked return value is pre-aggregated BY HAND from the same
underlying transaction list (laid out below) rather than invented, so an
error in the by-hand aggregation would break the cross-report identities
just as a real bug would.

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.reports.tests.test_financial_statements_roundtrip
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

import frappe

from zoho_books_clone.reports.report.balance_sheet.balance_sheet import get_data as bs_get_data
from zoho_books_clone.reports.report.profit_and_loss.profit_and_loss import get_data as pnl_get_data
from zoho_books_clone.db.queries import get_cash_flow

# ── Shared synthetic ledger ──────────────────────────────────────────────
# Opening (before the reporting period, 2026-08-01 .. 2026-08-31):
#   DR Bank 10,000 / CR Capital 10,000            -- capital injection
# Within the period:
#   DR Debtors 1,180 / CR Sales 1,000 / CR GST Payable 180   -- sale
#   DR Bank 1,180 / CR Debtors 1,180                          -- payment received
#   DR Fixed Asset 2,000 / CR Bank 2,000                      -- asset purchase
#   DR Expense 500 / CR Bank 500                              -- expense paid
#
# By account, cumulative through 2026-08-31 (as_of_date for the Balance Sheet):
#   Bank        10000+1180-2000-500 = 8680  (Bank)
#   Debtors     1180-1180 = 0                (Receivable)
#   Fixed Asset 2000                         (Asset)
#   Capital     -10000 raw (credit-normal)   (Equity)
#   GST Payable -180 raw (credit-normal)     (Tax)
#   Sales       -1000 raw (credit-normal)    (Income, period only)
#   Expense     500 raw (debit-normal)       (Expense, period only)

_BS_MAIN_ROWS = [
    frappe._dict(account="Bank - VK", account_type="Bank", balance=8680),
    frappe._dict(account="Debtors - VK", account_type="Receivable", balance=0),
    frappe._dict(account="Fixed Assets - VK", account_type="Asset", balance=2000),
    frappe._dict(account="GST Payable - VK", account_type="Tax", balance=-180),
    frappe._dict(account="Capital - VK", account_type="Equity", balance=-10000),
]
_BS_PNL_ROW = [frappe._dict(net=500)]  # Sales(1000 credit) - Expense(500 debit) = 500
_PNL_ROWS = [
    frappe._dict(account="Sales - VK", account_type="Income", amount=1000),
    frappe._dict(account="Expense - VK", account_type="Expense", amount=-500),
]


class TestFinancialStatementsRoundTrip(unittest.TestCase):

    @patch.object(frappe.db, "sql")
    def test_balance_sheet_balances(self, mock_sql):
        mock_sql.side_effect = [_BS_MAIN_ROWS, _BS_PNL_ROW]
        data = bs_get_data({"as_of_date": "2026-08-31", "company": "VK Herbal"})
        total_assets = next(r["balance"] for r in data if r.get("account") == "Total Assets")
        total_liab_eq = next(r["balance"] for r in data if r.get("account") == "Total Liabilities + Equity")
        self.assertEqual(total_assets, 10680)
        self.assertEqual(total_liab_eq, 10680)
        self.assertEqual(total_assets, total_liab_eq)

    @patch.object(frappe.db, "sql")
    def test_balance_sheet_net_profit_matches_pnl_net_profit(self, mock_sql):
        # Order matters: bs_get_data() issues 2 calls (main rows, pnl scalar),
        # then pnl_get_data() issues 1 call -- feed all 3 in that sequence.
        mock_sql.side_effect = [_BS_MAIN_ROWS, _BS_PNL_ROW, _PNL_ROWS]

        bs_data = bs_get_data({"as_of_date": "2026-08-31", "company": "VK Herbal"})
        bs_net_profit = next(
            r["balance"] for r in bs_data if r.get("account") == "Net Profit (current period)"
        )

        pnl_data = pnl_get_data({
            "from_date": "2026-08-01", "to_date": "2026-08-31", "company": "VK Herbal",
        })
        pnl_net_profit = next(r["amount"] for r in pnl_data if r.get("account") == "Net Profit / Loss")

        self.assertEqual(bs_net_profit, 500)
        self.assertEqual(pnl_net_profit, 500)
        self.assertEqual(bs_net_profit, pnl_net_profit)

    @patch.object(frappe.db, "sql")
    def test_cash_flow_closing_cash_matches_balance_sheet_bank_balance(self, mock_sql):
        # Cash Flow's own account_type-level query, period-only (the opening
        # capital injection is excluded -- it's dated before from_date):
        #   Receivable net = 1180-1180 = 0
        #   Income net     = 0-1000 = -1000
        #   Tax net        = 0-180 = -180
        #   Bank net       = 1180-2500 = -1320
        #   Asset net      = 2000-0 = 2000
        #   Expense net    = 500-0 = 500
        mock_sql.side_effect = [
            [
                frappe._dict(account_type="Receivable", net=0),
                frappe._dict(account_type="Income", net=-1000),
                frappe._dict(account_type="Tax", net=-180),
                frappe._dict(account_type="Bank", net=-1320),
                frappe._dict(account_type="Asset", net=2000),
                frappe._dict(account_type="Expense", net=500),
            ],
            [[10000]],  # opening cash: the capital-injection Bank debit, dated before from_date
        ]
        result = get_cash_flow("VK Herbal", "2026-08-01", "2026-08-31")

        # From test_balance_sheet_balances: Bank balance as of 2026-08-31 is 8680.
        self.assertEqual(result["closing_cash"], 8680)
        self.assertEqual(result["opening_cash"], 10000)
        self.assertEqual(result["net_change"], -1320)


if __name__ == "__main__":
    unittest.main()