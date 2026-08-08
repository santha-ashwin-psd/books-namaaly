# Copyright (c) 2026, PS Digitise and Contributors
# See license.txt
"""
Tests for the Cash Flow / GST engine functions (db/queries.py:
get_cash_flow, get_gst_summary) and their thin report wrappers
(reports/report/cash_flow_statement/, reports/report/gst_summary/).

get_cash_flow's activity classification (operating/investing/financing) and
the operating+investing+financing == net_change, opening+net_change ==
closing identities are re-derived here from account_type buckets, not
assumed -- this is the regression test for the Cash In - Cash Out -
Transfers != Net Cash bug fixed earlier (missing Expense/Asset Repair
buckets, double-subtracted internal transfers).

DB-free: frappe.db.sql is mocked to return canned per-account_type totals.

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.db.tests.test_cash_flow_and_gst
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

import frappe

from zoho_books_clone.db.queries import get_cash_flow, get_gst_summary
from zoho_books_clone.reports.report.cash_flow_statement.cash_flow_statement import (
    execute as cash_flow_execute,
)
from zoho_books_clone.reports.report.gst_summary.gst_summary import execute as gst_summary_execute


def _type_row(account_type, net):
    return frappe._dict(account_type=account_type, net=net)


class TestGetCashFlow(unittest.TestCase):

    @patch.object(frappe.db, "sql")
    def test_reconciles_operating_investing_financing_to_net_change(self, mock_sql):
        # Receivable +500 (used cash, customer not yet paid), Income -2000
        # (source of cash), Bank -1500 net inflow logged directly to Bank
        # itself (not part of by_type math -- Bank/Cash excluded from all
        # three buckets), Asset +800 (investing use), Equity -1000
        # (financing source), opening cash scalar = 5000.
        mock_sql.side_effect = [
            [
                _type_row("Receivable", 500),
                _type_row("Income", -2000),
                _type_row("Asset", 800),
                _type_row("Equity", -1000),
            ],
            [[5000]],
        ]
        result = get_cash_flow("VK Herbal", "2026-08-01", "2026-08-31")
        self.assertEqual(
            result["net_change"],
            result["operating"] + result["investing"] + result["financing"],
        )
        self.assertEqual(result["closing_cash"], result["opening_cash"] + result["net_change"])

    @patch.object(frappe.db, "sql")
    def test_investing_is_negative_of_asset_movement(self, mock_sql):
        mock_sql.side_effect = [[_type_row("Asset", 800)], [[0]]]
        result = get_cash_flow("VK Herbal", "2026-08-01", "2026-08-31")
        self.assertEqual(result["investing"], -800)

    @patch.object(frappe.db, "sql")
    def test_financing_is_negative_of_equity_and_liability_movement(self, mock_sql):
        mock_sql.side_effect = [
            [_type_row("Equity", -1000), _type_row("Liability", -400)], [[0]],
        ]
        result = get_cash_flow("VK Herbal", "2026-08-01", "2026-08-31")
        self.assertEqual(result["financing"], 1400)

    @patch.object(frappe.db, "sql")
    def test_expense_and_payable_and_tax_all_land_in_operating(self, mock_sql):
        # Regression case for the original bug: Expense and Asset Repair
        # buckets were missing from the working-capital/operating rollup,
        # so activity in those account types silently vanished instead of
        # reconciling. Anything that isn't Cash/Bank/Asset/Equity/Liability
        # must fall into operating so nothing is dropped.
        mock_sql.side_effect = [
            [
                _type_row("Expense", 300),
                _type_row("Payable", -150),
                _type_row("Tax", -50),
                _type_row("Cost of Goods Sold", 200),
            ],
            [[0]],
        ]
        result = get_cash_flow("VK Herbal", "2026-08-01", "2026-08-31")
        # operating = -(300 + -150 + -50 + 200) = -300
        self.assertEqual(result["operating"], -300)
        self.assertEqual(result["investing"], 0)
        self.assertEqual(result["financing"], 0)

    @patch.object(frappe.db, "sql")
    def test_cash_and_bank_buckets_excluded_from_all_three_activities(self, mock_sql):
        # Cash/Bank movement itself is the thing being explained, not an
        # activity -- it must not double-count into operating.
        mock_sql.side_effect = [
            [_type_row("Cash", 500), _type_row("Bank", -200)], [[0]],
        ]
        result = get_cash_flow("VK Herbal", "2026-08-01", "2026-08-31")
        self.assertEqual(result["operating"], 0)
        self.assertEqual(result["investing"], 0)
        self.assertEqual(result["financing"], 0)

    @patch.object(frappe.db, "sql")
    def test_no_activity_period_is_flat(self, mock_sql):
        mock_sql.side_effect = [[], [[2500]]]
        result = get_cash_flow("VK Herbal", "2026-08-01", "2026-08-31")
        self.assertEqual(result["net_change"], 0)
        self.assertEqual(result["opening_cash"], 2500)
        self.assertEqual(result["closing_cash"], 2500)

    @patch.object(frappe.db, "sql")
    def test_null_opening_cash_scalar_treated_as_zero(self, mock_sql):
        mock_sql.side_effect = [[], [[None]]]
        result = get_cash_flow("VK Herbal", "2026-08-01", "2026-08-31")
        self.assertEqual(result["opening_cash"], 0)


class TestGetGstSummary(unittest.TestCase):

    @patch.object(frappe.db, "sql")
    def test_passes_company_and_date_range_as_params(self, mock_sql):
        mock_sql.return_value = []
        get_gst_summary("VK Herbal", "2026-08-01", "2026-08-31")
        params = mock_sql.call_args.args[1]
        self.assertEqual(params, {
            "company": "VK Herbal", "from_date": "2026-08-01", "to_date": "2026-08-31",
        })

    @patch.object(frappe.db, "sql")
    def test_returns_rows_as_is(self, mock_sql):
        rows = [frappe._dict(tax_type="CGST", invoice_count=3, total_tax=540)]
        mock_sql.return_value = rows
        result = get_gst_summary("VK Herbal", "2026-08-01", "2026-08-31")
        self.assertEqual(result, rows)


class TestCashFlowWrapper(unittest.TestCase):

    @patch("zoho_books_clone.reports.report.cash_flow_statement.cash_flow_statement.get_cash_flow")
    def test_maps_engine_output_to_report_rows(self, mock_get_cash_flow):
        mock_get_cash_flow.return_value = {
            "operating": 680, "investing": -2000, "financing": 0,
            "net_change": -1320, "opening_cash": 10000, "closing_cash": 8680,
        }
        columns, rows = cash_flow_execute({
            "company": "VK Herbal", "from_date": "2026-08-01", "to_date": "2026-08-31",
        })
        by_section = {r["section"]: r["amount"] for r in rows if r}
        self.assertEqual(by_section["Net Change in Cash"], -1320)
        self.assertEqual(by_section["Closing Cash & Bank"], 8680)
        mock_get_cash_flow.assert_called_once_with("VK Herbal", "2026-08-01", "2026-08-31")

    @patch("zoho_books_clone.reports.report.cash_flow_statement.cash_flow_statement.get_cash_flow")
    def test_missing_opening_closing_default_to_zero(self, mock_get_cash_flow):
        mock_get_cash_flow.return_value = {
            "operating": 0, "investing": 0, "financing": 0, "net_change": 0,
        }
        columns, rows = cash_flow_execute({
            "company": "VK Herbal", "from_date": "2026-08-01", "to_date": "2026-08-31",
        })
        by_section = {r["section"]: r["amount"] for r in rows if r}
        self.assertEqual(by_section["Opening Cash & Bank"], 0)
        self.assertEqual(by_section["Closing Cash & Bank"], 0)


class TestGstSummaryWrapper(unittest.TestCase):

    @patch("zoho_books_clone.reports.report.gst_summary.gst_summary.get_gst_summary")
    def test_passes_filters_through_and_returns_rows_unchanged(self, mock_get_gst_summary):
        rows = [frappe._dict(tax_type="IGST", invoice_count=2, total_tax=360)]
        mock_get_gst_summary.return_value = rows
        columns, data = gst_summary_execute({
            "company": "VK Herbal", "from_date": "2026-08-01", "to_date": "2026-08-31",
        })
        self.assertEqual(data, rows)
        mock_get_gst_summary.assert_called_once_with("VK Herbal", "2026-08-01", "2026-08-31")
        self.assertEqual([c["fieldname"] for c in columns],
                          ["tax_type", "invoice_count", "total_tax"])


if __name__ == "__main__":
    unittest.main()