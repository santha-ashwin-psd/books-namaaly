# Copyright (c) 2026, PS Digitise and Contributors
# See license.txt
"""
Tests for E Way Bill (invoicing/doctype/e_way_bill/e_way_bill.py) --
before_delete's server-side guard against deleting a still-Generated EWB
(the frontend hides the delete action for this status, but a direct
API/bulk call must be blocked too).

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.invoicing.doctype.e_way_bill.test_e_way_bill
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

import frappe

from zoho_books_clone.invoicing.doctype.e_way_bill.e_way_bill import EWayBill


def _make_ewb(status="Generated"):
    doc = SimpleNamespace(doctype="E Way Bill", name="EWB-2026-00001", status=status)
    doc.before_delete = EWayBill.before_delete.__get__(doc)
    return doc


class TestBeforeDelete(unittest.TestCase):

    def test_generated_ewb_cannot_be_deleted(self):
        doc = _make_ewb(status="Generated")
        with self.assertRaises(frappe.ValidationError):
            doc.before_delete()

    def test_cancelled_ewb_can_be_deleted(self):
        doc = _make_ewb(status="Cancelled")
        doc.before_delete()  # should not raise

    def test_expired_ewb_can_be_deleted(self):
        doc = _make_ewb(status="Expired")
        doc.before_delete()  # should not raise

    def test_draft_ewb_can_be_deleted(self):
        doc = _make_ewb(status="Draft")
        doc.before_delete()  # should not raise


if __name__ == "__main__":
    unittest.main()