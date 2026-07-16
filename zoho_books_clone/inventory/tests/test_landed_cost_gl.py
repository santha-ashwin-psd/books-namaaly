"""
Tests for build_landed_cost_gl_map() — the pure function that constructs the
Dr Inventory / Cr-per-charge gl_map for general_ledger_entry.make_gl_entries().

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.inventory.tests.test_landed_cost_gl
"""

import unittest

from zoho_books_clone.inventory.landed_cost_engine import build_landed_cost_gl_map


class TestBuildLandedCostGlMap(unittest.TestCase):

    def test_single_charge_balances(self):
        gl_map = build_landed_cost_gl_map(
            inventory_account="Stock In Hand - VK",
            charges=[{"account": "Freight & Parcel Charges - Inward - VK", "amount": 500, "description": "KPN freight"}],
            voucher_no="LCV-2026-00001",
            posting_date="2026-07-16",
            company="VK Herbal",
        )
        total_debit = sum(r["debit"] for r in gl_map)
        total_credit = sum(r["credit"] for r in gl_map)
        self.assertEqual(total_debit, total_credit)
        self.assertEqual(total_debit, 500)
        self.assertEqual(len(gl_map), 2)  # one Dr Inventory + one Cr charge

    def test_multiple_charges_each_get_own_traceable_line(self):
        # Matches the client's worked example: 500 freight + 200 local transport.
        gl_map = build_landed_cost_gl_map(
            inventory_account="Stock In Hand - VK",
            charges=[
                {"account": "Freight & Parcel Charges - Inward - VK", "amount": 500, "description": "KPN freight"},
                {"account": "Local Transport Charges - Inward - VK", "amount": 200, "description": "Local transporter"},
            ],
            voucher_no="LCV-2026-00001",
            posting_date="2026-07-16",
            company="VK Herbal",
        )
        self.assertEqual(len(gl_map), 3)  # one Dr + two separate Cr lines

        dr_lines = [r for r in gl_map if r["debit"] > 0]
        cr_lines = [r for r in gl_map if r["credit"] > 0]
        self.assertEqual(len(dr_lines), 1)
        self.assertEqual(dr_lines[0]["debit"], 700)
        self.assertEqual(dr_lines[0]["account"], "Stock In Hand - VK")

        self.assertEqual(len(cr_lines), 2)
        # Each charge stays on its own line at its own amount/account — not
        # merged into a lump sum — so it's traceable back to its source.
        self.assertEqual(
            {(r["account"], r["credit"]) for r in cr_lines},
            {
                ("Freight & Parcel Charges - Inward - VK", 500),
                ("Local Transport Charges - Inward - VK", 200),
            },
        )
        self.assertEqual(sum(r["credit"] for r in cr_lines), 700)

    def test_every_line_carries_the_same_voucher_reference(self):
        gl_map = build_landed_cost_gl_map(
            inventory_account="Stock In Hand - VK",
            charges=[{"account": "Freight & Parcel Charges - Inward - VK", "amount": 500}],
            voucher_no="LCV-2026-00042",
            posting_date="2026-07-16",
            company="VK Herbal",
        )
        for row in gl_map:
            self.assertEqual(row["voucher_type"], "Landed Cost Voucher")
            self.assertEqual(row["voucher_no"], "LCV-2026-00042")
            self.assertEqual(row["company"], "VK Herbal")

    def test_zero_amount_charge_row_is_skipped(self):
        gl_map = build_landed_cost_gl_map(
            inventory_account="Stock In Hand - VK",
            charges=[
                {"account": "Freight & Parcel Charges - Inward - VK", "amount": 500},
                {"account": "Local Transport Charges - Inward - VK", "amount": 0},
            ],
            voucher_no="LCV-2026-00001",
            posting_date="2026-07-16",
            company="VK Herbal",
        )
        self.assertEqual(len(gl_map), 2)  # Dr + only the one non-zero Cr

    def test_no_charges_returns_empty(self):
        self.assertEqual(
            build_landed_cost_gl_map(
                inventory_account="Stock In Hand - VK",
                charges=[],
                voucher_no="LCV-2026-00001",
                posting_date="2026-07-16",
                company="VK Herbal",
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()