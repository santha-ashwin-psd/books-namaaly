"""
Tests for the Landed Cost Voucher Phase 5 guardrail that lives on the
controller (not the pure engine): _validate_no_duplicate_charge_capitalization.

This one touches frappe.db.sql, so it's exercised the same way
quality/test_qc_outgoing.py tests controller methods — by binding the real
unbound method to a lightweight stand-in object and mocking frappe.db.sql,
rather than constructing a full frappe.model.Document. That keeps the test
fast and DB-free while still exercising the actual guardrail code (not a
reimplementation of it).

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.inventory.tests.test_landed_cost_guardrails
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from zoho_books_clone.inventory.doctype.landed_cost_voucher.landed_cost_voucher import (
    LandedCostVoucher,
)


def _make_lcv(charges, name="LCV-2026-00002"):
    """A SimpleNamespace with just enough shape (.charges, .name) for the
    guardrail method to run against, with the real method bound onto it."""
    doc = SimpleNamespace(charges=charges, name=name)
    doc._validate_no_duplicate_charge_capitalization = (
        LandedCostVoucher._validate_no_duplicate_charge_capitalization.__get__(doc)
    )
    return doc


def _charge_row(reference_doctype=None, reference_name=None, idx=1):
    return SimpleNamespace(
        reference_doctype=reference_doctype, reference_name=reference_name, idx=idx
    )


class TestDuplicateChargeCapitalizationGuardrail(unittest.TestCase):

    @patch.object(frappe.db, "sql")
    def test_blocks_when_charge_already_capitalized_elsewhere(self, mock_sql):
        mock_sql.return_value = [{"name": "LCV-2026-00001"}]
        doc = _make_lcv([_charge_row("Purchase Invoice", "PINV-2026-0001")])

        with self.assertRaises(Exception):
            doc._validate_no_duplicate_charge_capitalization()

    @patch.object(frappe.db, "sql")
    def test_allows_when_charge_not_previously_capitalized(self, mock_sql):
        mock_sql.return_value = []
        doc = _make_lcv([_charge_row("Purchase Invoice", "PINV-2026-0002")])

        doc._validate_no_duplicate_charge_capitalization()  # should not raise
        self.assertTrue(mock_sql.called)

    @patch.object(frappe.db, "sql")
    def test_query_excludes_the_voucher_being_saved_itself(self, mock_sql):
        # Re-saving/re-submitting the SAME voucher must not trip its own
        # guardrail — the query passes self_name to exclude it.
        mock_sql.return_value = []
        doc = _make_lcv(
            [_charge_row("Purchase Invoice", "PINV-2026-0003")], name="LCV-2026-00009"
        )

        doc._validate_no_duplicate_charge_capitalization()

        _, kwargs_or_params = mock_sql.call_args[0], mock_sql.call_args[0][1]
        self.assertEqual(kwargs_or_params["self_name"], "LCV-2026-00009")

    @patch.object(frappe.db, "sql")
    def test_charge_rows_without_a_reference_are_skipped_entirely(self, mock_sql):
        # Informal cash charges (no linked Purchase Invoice / Journal Entry)
        # have nothing to dedupe against — must not even query.
        doc = _make_lcv([_charge_row(reference_doctype=None, reference_name=None)])

        doc._validate_no_duplicate_charge_capitalization()

        mock_sql.assert_not_called()

    @patch.object(frappe.db, "sql")
    def test_multiple_different_charges_against_same_source_all_pass(self, mock_sql):
        # Two genuinely different charges (different reference_name) against
        # what might be the same Purchase Receipt are both fine — dedup is
        # keyed on the charge's own source document, not the PR/PI.
        mock_sql.return_value = []
        doc = _make_lcv([
            _charge_row("Purchase Invoice", "PINV-2026-0004", idx=1),
            _charge_row("Journal Entry", "JE-2026-0011", idx=2),
        ])

        doc._validate_no_duplicate_charge_capitalization()
        self.assertEqual(mock_sql.call_count, 2)


if __name__ == "__main__":
    unittest.main()