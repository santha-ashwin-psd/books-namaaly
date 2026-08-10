# Copyright (c) 2026, PS Digitise and Contributors
# See license.txt
"""
Tests for TDS Entry (gst/doctype/tds_entry/tds_entry.py) -- before_insert's
tds_total auto-calc (rate + surcharge + cess) and after_insert's GL-posting
side effect, including the two different failure-handling paths: a fiscal-
year lock error is re-raised (blocks the insert with a clear reason), but
any other GL-posting failure (missing account, config issue) is logged and
swallowed so the TDS record itself is preserved for manual correction.

Same bind-real-method-onto-a-stand-in pattern as the other doctype test
suites -- DB-free, exercises the actual controller code.

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.gst.doctype.tds_entry.test_tds_entry
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe

from zoho_books_clone.gst.doctype.tds_entry.tds_entry import TDSEntry


class _Dict(SimpleNamespace):
    def get(self, key, default=None):
        return getattr(self, key, default)


def _make_tds(tds_total=0, amount=1000, rate=10, surcharge=0, cess=0,
              expense_account=None, voucher_no=None, company="VK Herbal",
              party="SUPP-1", section="194C", date="2026-08-01",
              remarks="", **overrides):
    doc = _Dict(
        doctype="TDS Entry", name="TDS-0001", tds_total=tds_total, amount=amount,
        rate=rate, surcharge=surcharge, cess=cess, expense_account=expense_account,
        voucher_no=voucher_no, company=company, party=party, section=section,
        date=date, remarks=remarks,
    )
    for k, v in overrides.items():
        setattr(doc, k, v)
    for name in ("before_insert", "after_insert"):
        setattr(doc, name, getattr(TDSEntry, name).__get__(doc))
    return doc


class TestBeforeInsert(unittest.TestCase):

    def test_computes_tds_total_from_rate_surcharge_cess(self):
        doc = _make_tds(tds_total=0, amount=10000, rate=10, surcharge=2, cess=1)
        doc.before_insert()
        # 10000 * (10+2+1)/100 = 1300
        self.assertEqual(doc.tds_total, 1300)

    def test_does_not_overwrite_explicit_tds_total(self):
        doc = _make_tds(tds_total=500, amount=10000, rate=10)
        doc.before_insert()
        self.assertEqual(doc.tds_total, 500)

    def test_noop_without_amount(self):
        doc = _make_tds(tds_total=0, amount=0, rate=10)
        doc.before_insert()
        self.assertEqual(doc.tds_total, 0)

    def test_noop_without_rate(self):
        doc = _make_tds(tds_total=0, amount=10000, rate=0)
        doc.before_insert()
        self.assertEqual(doc.tds_total, 0)


class TestAfterInsertGlPosting(unittest.TestCase):

    def test_noop_without_expense_account(self):
        doc = _make_tds(amount=10000, tds_total=1000, expense_account=None)
        with patch("zoho_books_clone.db.validators.validate_fiscal_year") as mock_fy:
            doc.after_insert()
            mock_fy.assert_not_called()

    def test_noop_when_voucher_no_already_set(self):
        # Already posted (e.g. re-insert path via save_tds_entry that sets
        # voucher_no) -- must not double-post.
        doc = _make_tds(amount=10000, tds_total=1000, expense_account="Expense - VK",
                         voucher_no="TDS-SUPP1-2026-08-01")
        with patch("zoho_books_clone.db.validators.validate_fiscal_year") as mock_fy:
            doc.after_insert()
            mock_fy.assert_not_called()

    @patch("zoho_books_clone.db.validators.validate_fiscal_year",
           side_effect=frappe.ValidationError("closed period"))
    def test_fiscal_year_lock_blocks_insert(self, mock_fy):
        doc = _make_tds(amount=10000, tds_total=1000, expense_account="Expense - VK")
        with self.assertRaises(frappe.ValidationError):
            doc.after_insert()

    @patch.object(frappe.db, "commit")
    @patch.object(frappe.db, "set_value")
    @patch("zoho_books_clone.api.gst.create_tds_entry")
    @patch("zoho_books_clone.db.validators.validate_fiscal_year")
    def test_successful_gl_posting_stamps_voucher_no(self, mock_fy, mock_create, mock_set_value, mock_commit):
        mock_create.return_value = {"voucher_no": "TDS-SUPP1-2026-08-01"}
        doc = _make_tds(amount=10000, tds_total=1000, expense_account="Expense - VK",
                         party="SUPP-1", section="194C", date="2026-08-01")
        doc.after_insert()
        mock_create.assert_called_once_with(
            company="VK Herbal", party="SUPP-1", expense_account="Expense - VK",
            amount="10000.0", tds_amount="1000.0", tds_section="194C",
            date="2026-08-01", remarks="",
        )
        mock_set_value.assert_called_once_with(
            "TDS Entry", "TDS-0001", "voucher_no", "TDS-SUPP1-2026-08-01"
        )
        mock_commit.assert_called_once()

    @patch("zoho_books_clone.api.gst.create_tds_entry", side_effect=frappe.ValidationError("no TDS Payable account"))
    @patch("zoho_books_clone.db.validators.validate_fiscal_year")
    def test_gl_validation_error_is_reraised(self, mock_fy, mock_create):
        doc = _make_tds(amount=10000, tds_total=1000, expense_account="Expense - VK")
        with self.assertRaises(frappe.ValidationError):
            doc.after_insert()

    @patch.object(frappe, "log_error")
    @patch("zoho_books_clone.api.gst.create_tds_entry", side_effect=Exception("account config missing"))
    @patch("zoho_books_clone.db.validators.validate_fiscal_year")
    def test_non_validation_gl_error_is_logged_not_raised(self, mock_fy, mock_create, mock_log_error):
        # The TDS Entry record itself must survive even when GL posting
        # fails for a non-fiscal reason -- preserved for manual correction.
        doc = _make_tds(amount=10000, tds_total=1000, expense_account="Expense - VK")
        doc.after_insert()  # should not raise
        mock_log_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()