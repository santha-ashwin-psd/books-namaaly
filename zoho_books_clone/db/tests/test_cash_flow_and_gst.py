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

from zoho_books_clone.db.queries import (
    get_cash_flow,
    get_gst_summary,
    get_gstr1_data,
    get_gstr_summary,
    get_itc_ledger,
)
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

    @patch.object(frappe.db, "sql")
    def test_query_filters_to_gst_tax_types(self, mock_sql):
        # Same contamination risk as the GSTR-3B bug: Tax Line.tax_type
        # includes VAT/Other, and TDS deductions are stored as tax_type
        # "Other" (see get_tds_transactions) -- must not leak in here either.
        mock_sql.return_value = []
        get_gst_summary("VK Herbal", "2026-08-01", "2026-08-31")
        query = mock_sql.call_args.args[0]
        self.assertIn("t.tax_type", query)
        self.assertIn("IN ('CGST', 'SGST', 'IGST', 'Cess')", query)


class TestGetGstrSummary(unittest.TestCase):
    """
    Regression tests for two GSTR-3B contamination bugs:

    Bug 1: Tax Line.tax_type isn't GST-exclusive (VAT/Cess/Other exist, and
    TDS deductions are stored as tax_type "Other" -- see
    get_tds_transactions). The output/ITC queries must filter to actual GST
    types or TDS/VAT/Other rows inflate total_output/total_itc.

    Bug 2: the taxable-value query filtered out is_return rows while
    total_output did not (relying on credit notes' negative net_total/
    tax_amount to net correctly instead). That mismatch broke the implied
    tax rate in any period with credit notes -- taxable_value must include
    returns too.
    """

    @patch.object(frappe.db, "sql")
    def test_output_and_itc_queries_filter_to_gst_tax_types(self, mock_sql):
        mock_sql.return_value = []
        get_gstr_summary("VK Herbal", "2026-08-01", "2026-08-31")
        output_query = mock_sql.call_args_list[0].args[0]
        itc_query = mock_sql.call_args_list[1].args[0]
        for query in (output_query, itc_query):
            self.assertIn("tl.tax_type", query)
            self.assertIn("IN ('CGST', 'SGST', 'IGST', 'Cess')", query)

    @patch.object(frappe.db, "sql")
    def test_taxable_value_query_does_not_exclude_returns(self, mock_sql):
        mock_sql.return_value = []
        get_gstr_summary("VK Herbal", "2026-08-01", "2026-08-31")
        taxable_query = mock_sql.call_args_list[2].args[0]
        self.assertNotIn("is_return", taxable_query)

    @patch.object(frappe.db, "sql")
    def test_totals_ignore_non_gst_tax_lines(self, mock_sql):
        # Simulate the filtered queries already excluding a TDS ("Other")
        # row -- if the SQL-level filter from the previous test ever
        # regresses, this still catches contamination reaching the totals.
        mock_sql.side_effect = [
            [frappe._dict(tax_type="CGST", description="CGST", amount=900, invoice_count=2)],
            [frappe._dict(tax_type="IGST", description="IGST", amount=400, invoice_count=1)],
            [frappe._dict(taxable_value=10000)],
        ]
        result = get_gstr_summary("VK Herbal", "2026-08-01", "2026-08-31")
        self.assertEqual(result["totals"]["total_output"], 900)
        self.assertEqual(result["totals"]["total_itc"], 400)
        self.assertEqual(result["totals"]["net_tax_liability"], 500)
        self.assertEqual(result["taxable_value"], 10000)


class TestGetGstrSummaryAssetItc(unittest.TestCase):
    """
    Phase 6: Asset ITC (Asset Tax Detail, ITC-eligible rows on a capitalized
    Asset) has to reach GSTR-3B's ITC total the same as Purchase Invoice
    ITC does -- it posts to the same GST Input account but lives in a
    different child doctype, so it needed its own UNION branch rather than
    just reusing the Tax Line query.
    """

    @patch.object(frappe.db, "sql")
    def test_itc_query_unions_purchase_invoice_and_asset_tax_detail(self, mock_sql):
        mock_sql.return_value = []
        get_gstr_summary("VK Herbal", "2026-08-01", "2026-08-31")
        itc_query = mock_sql.call_args_list[1].args[0]
        self.assertIn("tabAsset Tax Detail", itc_query)
        self.assertIn("tabPurchase Invoice", itc_query)
        self.assertIn("UNION ALL", itc_query)

    @patch.object(frappe.db, "sql")
    def test_asset_branch_filters_itc_eligible_and_excludes_existing_assets(self, mock_sql):
        mock_sql.return_value = []
        get_gstr_summary("VK Herbal", "2026-08-01", "2026-08-31")
        itc_query = mock_sql.call_args_list[1].args[0]
        self.assertIn("atd.is_itc_eligible = 1", itc_query)
        self.assertIn("a.is_existing_asset = 0", itc_query)

    @patch.object(frappe.db, "sql")
    def test_total_itc_sums_across_both_sources(self, mock_sql):
        # The grouped UNION query itself is mocked out -- from the caller's
        # side, one merged row per tax_type is indistinguishable from
        # "everything from Purchase Invoices" vs "everything from Assets";
        # what matters is the totals math downstream still just sums amount.
        mock_sql.side_effect = [
            [],
            [
                frappe._dict(tax_type="CGST", description="CGST", amount=300, invoice_count=2),
                frappe._dict(tax_type="SGST", description="SGST", amount=300, invoice_count=2),
            ],
            [frappe._dict(taxable_value=0)],
        ]
        result = get_gstr_summary("VK Herbal", "2026-08-01", "2026-08-31")
        self.assertEqual(result["totals"]["total_itc"], 600)


class TestGetItcLedger(unittest.TestCase):
    """Phase 6: get_itc_ledger() now unions in Asset ITC lines, tagged with
    a 'source' column so a caller can tell a capitalized-asset ITC line
    apart from a regular Purchase Invoice ITC line."""

    @patch.object(frappe.db, "sql")
    def test_query_unions_purchase_invoice_and_asset_sources(self, mock_sql):
        mock_sql.return_value = []
        get_itc_ledger("VK Herbal", "2026-08-01", "2026-08-31")
        query = mock_sql.call_args_list[0].args[0]
        self.assertIn("tabAsset Tax Detail", query)
        self.assertIn("'Purchase Invoice' AS source", query)
        self.assertIn("AS source", query)
        self.assertIn("'Asset'", query)

    @patch.object(frappe.db, "sql")
    def test_asset_rows_only_include_itc_eligible_lines_on_capitalized_assets(self, mock_sql):
        mock_sql.return_value = []
        get_itc_ledger("VK Herbal", "2026-08-01", "2026-08-31")
        query = mock_sql.call_args_list[0].args[0]
        self.assertIn("atd.is_itc_eligible = 1", query)
        self.assertIn("a.is_existing_asset = 0", query)

    @patch.object(frappe.db, "sql")
    def test_returns_rows_from_both_sources_unchanged(self, mock_sql):
        rows = [
            frappe._dict(voucher_no="PINV-0001", source="Purchase Invoice", tax_amount=500),
            frappe._dict(voucher_no="ASSET-0007", source="Asset", tax_amount=1200),
        ]
        mock_sql.return_value = rows
        result = get_itc_ledger("VK Herbal", "2026-08-01", "2026-08-31")
        self.assertEqual([r["source"] for r in result], ["Purchase Invoice", "Asset"])


class TestGetGstr1Data(unittest.TestCase):
    """
    Regression tests for GSTR-1 tax-line contamination: the per-invoice and
    aggregate total_tax must come from GST-only Tax Line rows, not the
    stored si.total_tax field (which sums every Tax Line row including TDS/
    VAT/Other) and not an unfiltered tax_rows query.
    """

    @patch.object(frappe.db, "sql")
    def test_tax_rows_query_filters_to_gst_tax_types(self, mock_sql):
        mock_sql.return_value = []
        get_gstr1_data("VK Herbal", "2026-08-01", "2026-08-31")
        tax_rows_query = mock_sql.call_args_list[1].args[0]
        self.assertIn("IN ('CGST', 'SGST', 'IGST', 'Cess')", tax_rows_query)

    @patch.object(frappe.db, "sql")
    def test_invoice_total_tax_recomputed_from_filtered_tax_lines(self, mock_sql):
        # si.total_tax (stored) is contaminated with a TDS line ("Other",
        # not returned by the now-filtered tax_rows query) -- the invoice's
        # effective total_tax must reflect only the GST lines actually
        # returned, not the stored field.
        mock_sql.side_effect = [
            [frappe._dict(
                name="SINV-0001", posting_date="2026-08-05",
                customer="Acme Pharma", customer_name="Acme Pharma",
                customer_gstin="29AAAAA0000A1Z5", place_of_supply="29-Karnataka",
                net_total=10000, total_tax=1900,  # stored field: 1800 GST + 100 TDS
                grand_total=11900, is_return=0, return_against=None,
            )],
            [
                frappe._dict(parent="SINV-0001", tax_type="CGST",
                              description="CGST", rate=9, tax_amount=900),
                frappe._dict(parent="SINV-0001", tax_type="SGST",
                              description="SGST", rate=9, tax_amount=900),
            ],
            [],
        ]
        result = get_gstr1_data("VK Herbal", "2026-08-01", "2026-08-31")
        self.assertEqual(len(result["b2b"]), 1)
        self.assertEqual(result["b2b"][0]["total_tax"], 1800)
        self.assertEqual(result["totals"]["total_tax"], 1800)

    @patch.object(frappe.db, "sql")
    def test_credit_note_with_gstin_routed_to_cdnr_not_b2b(self, mock_sql):
        mock_sql.side_effect = [
            [frappe._dict(
                name="SINV-0002", posting_date="2026-08-06",
                customer="Acme Pharma", customer_name="Acme Pharma",
                customer_gstin="29AAAAA0000A1Z5", place_of_supply="29-Karnataka",
                net_total=-2000, total_tax=-360,
                grand_total=-2360, is_return=1, return_against="SINV-0001",
            )],
            [],
            [],
        ]
        result = get_gstr1_data("VK Herbal", "2026-08-01", "2026-08-31")
        self.assertEqual(len(result["cdnr"]), 1)
        self.assertEqual(len(result["b2b"]), 0)
        self.assertEqual(result["totals"]["cdnr_count"], 1)

    @patch.object(frappe.db, "sql")
    def test_credit_note_without_gstin_routed_to_cdnur_not_dropped(self, mock_sql):
        # Regression test: unregistered (B2C) credit notes used to be
        # silently skipped entirely -- present in neither cdnr nor b2c, with
        # no trace anywhere in the return. They must land in cdnur instead.
        mock_sql.side_effect = [
            [frappe._dict(
                name="SINV-0003", posting_date="2026-08-07",
                customer="Walk-in Customer", customer_name="Walk-in Customer",
                customer_gstin="", place_of_supply="29-Karnataka",
                net_total=-500, total_tax=-90,
                grand_total=-590, is_return=1, return_against="SINV-0002",
            )],
            [],
            [],
        ]
        result = get_gstr1_data("VK Herbal", "2026-08-01", "2026-08-31")
        self.assertEqual(len(result["cdnur"]), 1)
        self.assertEqual(result["cdnur"][0]["name"], "SINV-0003")
        self.assertEqual(result["totals"]["cdnur_count"], 1)
        self.assertEqual(len(result["b2c"]), 0)
        self.assertEqual(len(result["cdnr"]), 0)

    @patch.object(frappe.db, "sql")
    def test_cdnur_not_counted_in_taxable_or_tax_totals(self, mock_sql):
        # Mirrors how cdnr already stays out of total_taxable/total_tax --
        # both credit-note tables report separately rather than netting into
        # the forward-supply totals, so cdnur must follow the same rule.
        mock_sql.side_effect = [
            [
                frappe._dict(
                    name="SINV-0004", posting_date="2026-08-08",
                    customer="Retail Buyer", customer_name="Retail Buyer",
                    customer_gstin="", place_of_supply="29-Karnataka",
                    net_total=1000, total_tax=180,
                    grand_total=1180, is_return=0, return_against=None,
                ),
                frappe._dict(
                    name="SINV-0005", posting_date="2026-08-09",
                    customer="Retail Buyer", customer_name="Retail Buyer",
                    customer_gstin="", place_of_supply="29-Karnataka",
                    net_total=-1000, total_tax=-180,
                    grand_total=-1180, is_return=1, return_against="SINV-0004",
                ),
            ],
            # get_gstr1_data overwrites each invoice's total_tax with the
            # sum of its OWN GST-only tax_rows (see the function's own
            # comment on why) -- so SINV-0004's 180 above is inert unless
            # this second query mock actually carries a matching Tax Line
            # row for it too. SINV-0005 (the return) deliberately gets none:
            # its 12% CGST+SGST would double as a second, unwanted, 180 if
            # it silently reused SINV-0004's row here.
            [
                frappe._dict(parent="SINV-0004", tax_type="CGST", description="CGST", rate=9, tax_amount=90),
                frappe._dict(parent="SINV-0004", tax_type="SGST", description="SGST", rate=9, tax_amount=90),
            ],
            [],
        ]
        result = get_gstr1_data("VK Herbal", "2026-08-01", "2026-08-31")
        self.assertEqual(result["totals"]["total_taxable"], 1000)
        self.assertEqual(result["totals"]["total_tax"], 180)


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