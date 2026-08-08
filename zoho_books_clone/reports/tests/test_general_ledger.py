# Copyright (c) 2026, PS Digitise and Contributors
# See license.txt
"""
Tests for the General Ledger report (reports/report/general_ledger/
general_ledger.py) -- optional filter -> WHERE clause construction and the
running-balance accumulation.

DB-free: frappe.db.sql is mocked to return canned rows; we assert on the
query text/params actually passed and on the running-balance math applied
to those rows.

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.reports.tests.test_general_ledger
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

import frappe

from zoho_books_clone.reports.report.general_ledger.general_ledger import get_data


def _row(posting_date="2026-08-01", voucher_type="Sales Invoice", voucher_no="SINV-1",
         account="Debtors - VK", party_type=None, party=None, debit=0, credit=0, remarks=""):
    return frappe._dict(
        posting_date=posting_date, voucher_type=voucher_type, voucher_no=voucher_no,
        account=account, party_type=party_type, party=party, debit=debit, credit=credit,
        remarks=remarks,
    )


class TestRunningBalance(unittest.TestCase):

    @patch.object(frappe.db, "sql")
    def test_balance_accumulates_in_row_order(self, mock_sql):
        mock_sql.return_value = [
            _row(debit=1000, credit=0),
            _row(debit=0, credit=400),
            _row(debit=200, credit=0),
        ]
        rows = get_data({"from_date": "2026-08-01", "to_date": "2026-08-31"})
        self.assertEqual([r["balance"] for r in rows], [1000, 600, 800])

    @patch.object(frappe.db, "sql")
    def test_empty_result_is_empty_list(self, mock_sql):
        mock_sql.return_value = []
        rows = get_data({"from_date": "2026-08-01", "to_date": "2026-08-31"})
        self.assertEqual(rows, [])


class TestFilterConditions(unittest.TestCase):

    @patch.object(frappe.db, "sql", return_value=[])
    def test_base_conditions_always_present(self, mock_sql):
        get_data({"from_date": "2026-08-01", "to_date": "2026-08-31"})
        query = mock_sql.call_args.args[0]
        self.assertIn("IFNULL(is_cancelled, 0) = 0", query)
        self.assertIn("posting_date BETWEEN %(from_date)s AND %(to_date)s", query)
        # None of the optional filters were supplied -- must not appear.
        for clause in ("company = ", "account = ", "party_type = ", "party = ", "voucher_no = "):
            self.assertNotIn(clause, query)

    @patch.object(frappe.db, "sql", return_value=[])
    def test_optional_filters_each_add_their_own_clause(self, mock_sql):
        get_data({
            "from_date": "2026-08-01", "to_date": "2026-08-31",
            "company": "VK Herbal", "account": "Debtors - VK",
            "party_type": "Customer", "party": "CUST-1",
            "voucher_no": "SINV-1",
        })
        query = mock_sql.call_args.args[0]
        for clause in ("company = %(company)s", "account = %(account)s",
                       "party_type = %(party_type)s", "party = %(party)s",
                       "voucher_no = %(voucher_no)s"):
            self.assertIn(clause, query)

    @patch.object(frappe.db, "sql", return_value=[])
    def test_filters_dict_passed_through_as_params(self, mock_sql):
        filters = {"from_date": "2026-08-01", "to_date": "2026-08-31", "company": "VK Herbal"}
        get_data(filters)
        params = mock_sql.call_args.args[1]
        self.assertEqual(params, filters)


if __name__ == "__main__":
    unittest.main()