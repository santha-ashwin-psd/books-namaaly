"""
Pure-function tests for the Manufacture Stock Entry FG/scrap GL split
(Phase 5 — Scrap/By-Product GL segregation).

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.accounts.tests.test_scrap_inventory_gl
"""

from __future__ import annotations

import unittest

from zoho_books_clone.accounts.inventory_gl import build_manufacture_incoming_gl_lines


class TestScrapInventoryGl(unittest.TestCase):

    def test_segregation_off_posts_single_combined_line(self):
        """Feature flag off (default) -- today's behavior, unaffected."""
        lines = build_manufacture_incoming_gl_lines(
            voucher_no="STE-0001",
            posting_date="2026-07-20",
            company="Demo Co",
            total_incoming_value=1000,
            scrap_incoming_value=150,
            inventory_account="Stock In Hand - Demo Co",
            scrap_account="Scrap / By-Product - Demo Co",
            segregate_scrap_gl=False,
        )
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["account"], "Stock In Hand - Demo Co")
        self.assertEqual(lines[0]["debit"], 1000)

    def test_no_scrap_value_posts_single_combined_line_even_when_flag_on(self):
        """Flag on but this entry has no scrap rows -- no split needed."""
        lines = build_manufacture_incoming_gl_lines(
            voucher_no="STE-0002",
            posting_date="2026-07-20",
            company="Demo Co",
            total_incoming_value=1000,
            scrap_incoming_value=0,
            inventory_account="Stock In Hand - Demo Co",
            scrap_account="Scrap / By-Product - Demo Co",
            segregate_scrap_gl=True,
        )
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["account"], "Stock In Hand - Demo Co")
        self.assertEqual(lines[0]["debit"], 1000)

    def test_segregation_on_with_configured_scrap_account_splits_lines(self):
        lines = build_manufacture_incoming_gl_lines(
            voucher_no="STE-0003",
            posting_date="2026-07-20",
            company="Demo Co",
            total_incoming_value=1000,
            scrap_incoming_value=150,
            inventory_account="Stock In Hand - Demo Co",
            scrap_account="Scrap / By-Product - Demo Co",
            segregate_scrap_gl=True,
        )
        self.assertEqual(len(lines), 2)
        by_acct = {r["account"]: r["debit"] for r in lines}
        self.assertEqual(by_acct["Stock In Hand - Demo Co"], 850)
        self.assertEqual(by_acct["Scrap / By-Product - Demo Co"], 150)
        self.assertEqual(sum(r["debit"] for r in lines), 1000)
        self.assertTrue(all(r["credit"] == 0 for r in lines))

    def test_segregation_on_without_configured_scrap_account_falls_back_to_inventory(self):
        """No Scrap account configured -- GL must still balance, so the
        scrap line falls back to the same inventory_account (this still
        produces two lines against the same account rather than merging
        them, so the scrap value stays traceable via remarks)."""
        lines = build_manufacture_incoming_gl_lines(
            voucher_no="STE-0004",
            posting_date="2026-07-20",
            company="Demo Co",
            total_incoming_value=1000,
            scrap_incoming_value=150,
            inventory_account="Stock In Hand - Demo Co",
            scrap_account=None,
            segregate_scrap_gl=True,
        )
        self.assertEqual(len(lines), 2)
        accounts = {r["account"] for r in lines}
        self.assertEqual(accounts, {"Stock In Hand - Demo Co"})
        self.assertEqual(sum(r["debit"] for r in lines), 1000)

    def test_all_scrap_no_fg_omits_fg_line(self):
        """Entire incoming value is scrap (e.g. a by-product-only run) --
        no FG line should be emitted since fg_incoming_value is zero."""
        lines = build_manufacture_incoming_gl_lines(
            voucher_no="STE-0005",
            posting_date="2026-07-20",
            company="Demo Co",
            total_incoming_value=150,
            scrap_incoming_value=150,
            inventory_account="Stock In Hand - Demo Co",
            scrap_account="Scrap / By-Product - Demo Co",
            segregate_scrap_gl=True,
        )
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["account"], "Scrap / By-Product - Demo Co")
        self.assertEqual(lines[0]["debit"], 150)

    def test_zero_total_incoming_value_returns_no_lines(self):
        lines = build_manufacture_incoming_gl_lines(
            voucher_no="STE-0006",
            posting_date="2026-07-20",
            company="Demo Co",
            total_incoming_value=0,
            scrap_incoming_value=0,
            inventory_account="Stock In Hand - Demo Co",
            scrap_account="Scrap / By-Product - Demo Co",
            segregate_scrap_gl=True,
        )
        self.assertEqual(lines, [])


if __name__ == "__main__":
    unittest.main()