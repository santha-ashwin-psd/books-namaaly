"""
Regression tests for zoho_books_clone.inventory.utils.compute_bin_valuation —
the pure function StockLedgerEntry._update_bin() now delegates to.

Existing-behavior tests here lock in the moving-average math exactly as it
worked before the Phase 3 (Landed Cost Voucher) change, so a regression in
Material Receipt / Material Issue / Material Transfer / Manufacture valuation
would fail loudly. The new value-only branch (actual_qty == 0, non-zero
stock_value_difference) is what Landed Cost Voucher relies on.

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.inventory.tests.test_bin_valuation
"""

import unittest

from zoho_books_clone.inventory.utils import compute_bin_valuation


class TestComputeBinValuation(unittest.TestCase):

    # ── Pre-existing behavior (Material Receipt / Issue / Transfer / Manufacture) ──

    def test_incoming_blends_moving_average(self):
        # 100 units @ 10 already in stock; receive 50 more @ 16.
        new_qty, new_value, new_rate = compute_bin_valuation(
            old_qty=100, old_value=1000, delta_qty=50, incoming_rate=16,
        )
        self.assertEqual(new_qty, 150)
        self.assertEqual(new_value, 1800)          # 1000 + 50*16
        self.assertAlmostEqual(new_rate, 12.0, places=4)

    def test_incoming_falls_back_to_valuation_rate_when_no_incoming_rate(self):
        new_qty, new_value, new_rate = compute_bin_valuation(
            old_qty=0, old_value=0, delta_qty=10, incoming_rate=0, valuation_rate=25,
        )
        self.assertEqual(new_qty, 10)
        self.assertEqual(new_value, 250)
        self.assertEqual(new_rate, 25)

    def test_outgoing_draws_down_at_bins_own_rate(self):
        # 100 units @ average rate 10 (value 1000). Issue 30 units.
        # Must use the bin's own rate (10), NOT some other rate passed in.
        new_qty, new_value, new_rate = compute_bin_valuation(
            old_qty=100, old_value=1000, delta_qty=-30,
            incoming_rate=0, valuation_rate=999,  # must be ignored for outgoing
        )
        self.assertEqual(new_qty, 70)
        self.assertEqual(new_value, 700)
        self.assertAlmostEqual(new_rate, 10.0, places=4)

    def test_outgoing_never_lets_sle_rate_corrupt_remaining_value(self):
        # Regression guard for the exact bug the original comment calls out:
        # an outgoing SLE with a stale/zero valuation_rate must not zero out
        # the value of the stock that stays behind.
        new_qty, new_value, new_rate = compute_bin_valuation(
            old_qty=10, old_value=1000, delta_qty=-5,
            incoming_rate=0, valuation_rate=0,
        )
        self.assertEqual(new_qty, 5)
        self.assertEqual(new_value, 500)           # NOT 0
        self.assertAlmostEqual(new_rate, 100.0, places=4)

    def test_value_floors_at_zero(self):
        # Shouldn't be reachable in practice (negative stock is blocked
        # upstream), but the floor must hold if it ever is.
        new_qty, new_value, new_rate = compute_bin_valuation(
            old_qty=5, old_value=50, delta_qty=-10, valuation_rate=10,
        )
        self.assertEqual(new_value, 0.0)
        self.assertEqual(new_rate, 0.0)  # new_qty <= 0 -> rate is 0

    def test_zero_delta_zero_difference_is_a_true_noop(self):
        new_qty, new_value, new_rate = compute_bin_valuation(
            old_qty=20, old_value=400, delta_qty=0, stock_value_difference=0,
        )
        self.assertEqual(new_qty, 20)
        self.assertEqual(new_value, 400)
        self.assertEqual(new_rate, 20.0)

    # ── New Phase 3 branch: Landed Cost Voucher value-only adjustment ──────────

    def test_value_only_adjustment_bumps_value_without_moving_qty(self):
        # 100 units on hand @ rate 100 (value 10,000). LCV capitalizes ₹700
        # of freight against this row — matches the client's worked example.
        new_qty, new_value, new_rate = compute_bin_valuation(
            old_qty=100, old_value=10000, delta_qty=0, stock_value_difference=700,
        )
        self.assertEqual(new_qty, 100)             # unchanged
        self.assertEqual(new_value, 10700)
        self.assertAlmostEqual(new_rate, 107.0, places=4)

    def test_value_only_adjustment_can_be_negative(self):
        # A Landed Cost Voucher cancellation reverses with a negative
        # stock_value_difference.
        new_qty, new_value, new_rate = compute_bin_valuation(
            old_qty=100, old_value=10700, delta_qty=0, stock_value_difference=-700,
        )
        self.assertEqual(new_qty, 100)
        self.assertEqual(new_value, 10000)
        self.assertAlmostEqual(new_rate, 100.0, places=4)

    def test_value_only_adjustment_floors_at_zero(self):
        new_qty, new_value, new_rate = compute_bin_valuation(
            old_qty=10, old_value=50, delta_qty=0, stock_value_difference=-500,
        )
        self.assertEqual(new_value, 0.0)
        self.assertEqual(new_rate, 0.0)

    def test_value_only_adjustment_on_empty_bin_does_not_crash(self):
        # Zero qty on hand: rate can't be computed (division by zero guarded),
        # so it resolves to 0 even though value nominally moved. Callers are
        # expected to skip rows with no remaining qty (see
        # LandedCostVoucher._create_valuation_sles) rather than rely on this.
        new_qty, new_value, new_rate = compute_bin_valuation(
            old_qty=0, old_value=0, delta_qty=0, stock_value_difference=700,
        )
        self.assertEqual(new_qty, 0)
        self.assertEqual(new_value, 700)
        self.assertEqual(new_rate, 0.0)


if __name__ == "__main__":
    unittest.main()