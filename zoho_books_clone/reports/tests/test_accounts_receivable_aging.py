# Copyright (c) 2026, PS Digitise and Contributors
# See license.txt
"""
Tests for Accounts Receivable Aging (reports/report/accounts_receivable_aging/
accounts_receivable_aging.py) -- bucket boundary assignment (0-30 / 31-60 /
61-90 / 90+ days overdue, measured from due_date) and the not-yet-due case.

DB-free: frappe.get_all is mocked to return canned invoice rows.

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.reports.tests.test_accounts_receivable_aging
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

import frappe

from zoho_books_clone.reports.report.accounts_receivable_aging.accounts_receivable_aging import get_data


def _inv(name="SINV-1", customer="CUST-1", posting_date="2026-07-01",
         due_date="2026-07-01", outstanding_amount=1000):
    return frappe._dict(name=name, customer=customer, posting_date=posting_date,
                         due_date=due_date, outstanding_amount=outstanding_amount)


class TestBucketBoundaries(unittest.TestCase):

    @patch.object(frappe, "get_all")
    def test_exactly_zero_days_overdue_lands_in_first_bucket(self, mock_get_all):
        mock_get_all.return_value = [_inv(due_date="2026-08-08")]
        rows = get_data({"company": "VK Herbal", "as_of_date": "2026-08-08"})
        self.assertEqual(rows[0]["bucket_0_30"], 1000)
        self.assertEqual(rows[0]["bucket_31_60"], 0)

    @patch.object(frappe, "get_all")
    def test_boundary_at_30_days_still_first_bucket(self, mock_get_all):
        mock_get_all.return_value = [_inv(due_date="2026-07-09")]  # exactly 30 days before as_of
        rows = get_data({"company": "VK Herbal", "as_of_date": "2026-08-08"})
        self.assertEqual(rows[0]["bucket_0_30"], 1000)
        self.assertEqual(rows[0]["bucket_31_60"], 0)

    @patch.object(frappe, "get_all")
    def test_boundary_at_31_days_moves_to_second_bucket(self, mock_get_all):
        mock_get_all.return_value = [_inv(due_date="2026-07-08")]  # 31 days before as_of
        rows = get_data({"company": "VK Herbal", "as_of_date": "2026-08-08"})
        self.assertEqual(rows[0]["bucket_0_30"], 0)
        self.assertEqual(rows[0]["bucket_31_60"], 1000)

    @patch.object(frappe, "get_all")
    def test_boundary_at_90_vs_91_days(self, mock_get_all):
        mock_get_all.return_value = [
            _inv(name="SINV-90", due_date="2026-05-10"),   # 90 days before as_of
            _inv(name="SINV-91", due_date="2026-05-09"),   # 91 days before as_of
        ]
        rows = get_data({"company": "VK Herbal", "as_of_date": "2026-08-08"})
        row_90 = next(r for r in rows if r["name"] == "SINV-90")
        row_91 = next(r for r in rows if r["name"] == "SINV-91")
        self.assertEqual(row_90["bucket_61_90"], 1000)
        self.assertEqual(row_90["bucket_90plus"], 0)
        self.assertEqual(row_91["bucket_90plus"], 1000)
        self.assertEqual(row_91["bucket_61_90"], 0)

    @patch.object(frappe, "get_all")
    def test_not_yet_due_invoice_falls_in_no_bucket(self, mock_get_all):
        # due_date is in the future relative to as_of_date -- outstanding is
        # real, but it isn't "overdue" in any bucket yet.
        mock_get_all.return_value = [_inv(due_date="2026-09-01")]
        rows = get_data({"company": "VK Herbal", "as_of_date": "2026-08-08"})
        row = rows[0]
        self.assertEqual(row["outstanding"], 1000)
        self.assertEqual(row["bucket_0_30"], 0)
        self.assertEqual(row["bucket_31_60"], 0)
        self.assertEqual(row["bucket_61_90"], 0)
        self.assertEqual(row["bucket_90plus"], 0)

    @patch.object(frappe, "get_all")
    def test_only_open_invoices_for_company_are_queried(self, mock_get_all):
        mock_get_all.return_value = []
        get_data({"company": "VK Herbal", "as_of_date": "2026-08-08"})
        _, kwargs = mock_get_all.call_args
        self.assertEqual(kwargs["filters"]["docstatus"], 1)
        self.assertEqual(kwargs["filters"]["outstanding_amount"], [">", 0])
        self.assertEqual(kwargs["filters"]["company"], "VK Herbal")


if __name__ == "__main__":
    unittest.main()