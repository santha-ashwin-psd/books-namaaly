"""
Tests for assets/depreciation_engine.py — pure schedule-calculation logic
(no DB access; build_schedule() only touches the attributes it reads off
the passed-in `asset` object).

Run with:
    bench run-tests --app zoho_books_clone --module zoho_books_clone.assets.tests.test_depreciation_engine
"""

import unittest
from unittest.mock import MagicMock

from zoho_books_clone.assets.depreciation_engine import (
    build_schedule,
    _wdv_annual_rate,
    _wdv_monthly_rate,
)


def _make_asset(
    purchase_cost=120000,
    salvage_value=0,
    useful_life=5,
    available_for_use_date="2026-01-01",
    purchase_date="2026-01-01",
    depreciation_method="Straight Line",
    depreciation_posting_frequency="Annually",
):
    asset = MagicMock()
    asset.purchase_cost = purchase_cost
    asset.salvage_value = salvage_value
    asset.useful_life = useful_life
    asset.available_for_use_date = available_for_use_date
    asset.purchase_date = purchase_date
    asset.depreciation_method = depreciation_method
    asset.depreciation_posting_frequency = depreciation_posting_frequency
    return asset


class TestBuildScheduleGuards(unittest.TestCase):

    def test_zero_cost_returns_empty(self):
        asset = _make_asset(purchase_cost=0)
        self.assertEqual(build_schedule(asset), [])

    def test_zero_useful_life_returns_empty(self):
        asset = _make_asset(useful_life=0)
        self.assertEqual(build_schedule(asset), [])

    def test_no_dates_falls_back_to_getdate_of_none(self):
        """frappe.utils.getdate(None) returns today's date, not None -- so
        with both date fields blank, start_date is never falsy and the
        'no start date' guard in build_schedule is unreachable through this
        path. Confirms the actual (surprising) behavior rather than the
        guard we might assume exists: a schedule is still generated,
        anchored on today."""
        asset = _make_asset(available_for_use_date=None, purchase_date=None)
        rows = build_schedule(asset)
        self.assertEqual(len(rows), asset.useful_life)

    def test_salvage_greater_than_cost_returns_empty(self):
        """Nonsensical input -- engine refuses rather than depreciating upward."""
        asset = _make_asset(purchase_cost=1000, salvage_value=5000)
        self.assertEqual(build_schedule(asset), [])

    def test_negative_salvage_treated_as_zero(self):
        asset = _make_asset(purchase_cost=1000, salvage_value=-100, useful_life=1)
        rows = build_schedule(asset)
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[-1]["closing_value"], 0.0)


class TestAnnualStraightLine(unittest.TestCase):

    def test_five_year_straight_line_fully_depreciates(self):
        asset = _make_asset(purchase_cost=120000, salvage_value=0, useful_life=5,
                             depreciation_method="Straight Line", depreciation_posting_frequency="Annually")
        rows = build_schedule(asset)
        self.assertEqual(len(rows), 5)
        for row in rows:
            self.assertAlmostEqual(row["depreciation_amount"], 24000.0)
        self.assertAlmostEqual(rows[-1]["closing_value"], 0.0)

    def test_with_salvage_value_lands_exactly_on_salvage(self):
        asset = _make_asset(purchase_cost=100000, salvage_value=10000, useful_life=4,
                             depreciation_method="Straight Line", depreciation_posting_frequency="Annually")
        rows = build_schedule(asset)
        # (100000-10000)/4 = 22500 per year
        for row in rows:
            self.assertAlmostEqual(row["depreciation_amount"], 22500.0)
        self.assertAlmostEqual(rows[-1]["closing_value"], 10000.0)

    def test_opening_closing_chain_is_consistent(self):
        asset = _make_asset(purchase_cost=50000, salvage_value=0, useful_life=5)
        rows = build_schedule(asset)
        for i in range(1, len(rows)):
            self.assertAlmostEqual(rows[i]["opening_value"], rows[i - 1]["closing_value"])


class TestAnnualWDV(unittest.TestCase):

    def test_wdv_rate_converges_toward_salvage(self):
        rate = _wdv_annual_rate(cost=100000, salvage=10000, life_years=5)
        self.assertGreater(rate, 0)
        self.assertLess(rate, 1)

    def test_wdv_schedule_ends_at_salvage(self):
        asset = _make_asset(purchase_cost=100000, salvage_value=10000, useful_life=5,
                             depreciation_method="Written Down Value", depreciation_posting_frequency="Annually")
        rows = build_schedule(asset)
        self.assertAlmostEqual(rows[-1]["closing_value"], 10000.0, places=2)

    def test_wdv_depreciation_amount_declines_each_period(self):
        asset = _make_asset(purchase_cost=100000, salvage_value=10000, useful_life=5,
                             depreciation_method="Written Down Value", depreciation_posting_frequency="Annually")
        rows = build_schedule(asset)
        amounts = [r["depreciation_amount"] for r in rows]
        for i in range(1, len(amounts)):
            self.assertLess(amounts[i], amounts[i - 1])

    def test_wdv_zero_salvage_uses_notional_basis_and_still_converges(self):
        """Zero salvage: engine uses a 1%-of-cost notional rate basis so the
        WDV rate is finite, but the schedule still ends at real salvage (0)."""
        asset = _make_asset(purchase_cost=100000, salvage_value=0, useful_life=5,
                             depreciation_method="Written Down Value", depreciation_posting_frequency="Annually")
        rows = build_schedule(asset)
        self.assertAlmostEqual(rows[-1]["closing_value"], 0.0, places=2)


class TestMonthlyProRation(unittest.TestCase):

    def test_mid_month_start_prorates_first_period_only(self):
        asset = _make_asset(purchase_cost=120000, salvage_value=0, useful_life=1,
                             available_for_use_date="2026-01-16", purchase_date="2026-01-16",
                             depreciation_method="Straight Line", depreciation_posting_frequency="Monthly")
        rows = build_schedule(asset)
        # Full monthly amount would be 120000/12=10000; the first (partial)
        # period must be strictly less than a full month's amount.
        full_month = 120000 / 12
        self.assertTrue(rows[0]["is_pro_rata"])
        self.assertLess(rows[0]["depreciation_amount"], full_month)
        # Every period after the first is a full calendar month, none flagged pro-rata.
        for row in rows[1:-1]:
            self.assertFalse(row["is_pro_rata"])

    def test_first_of_month_start_is_not_pro_rated(self):
        asset = _make_asset(purchase_cost=120000, salvage_value=0, useful_life=1,
                             available_for_use_date="2026-01-01", purchase_date="2026-01-01",
                             depreciation_method="Straight Line", depreciation_posting_frequency="Monthly")
        rows = build_schedule(asset)
        self.assertFalse(rows[0]["is_pro_rata"])
        self.assertAlmostEqual(rows[0]["depreciation_amount"], 120000 / 12)

    def test_monthly_schedule_fully_depreciates_to_salvage(self):
        asset = _make_asset(purchase_cost=60000, salvage_value=0, useful_life=1,
                             available_for_use_date="2026-03-10", purchase_date="2026-03-10",
                             depreciation_method="Straight Line", depreciation_posting_frequency="Monthly")
        rows = build_schedule(asset)
        self.assertEqual(len(rows), 12)
        self.assertAlmostEqual(rows[-1]["closing_value"], 0.0)

    def test_true_up_balloons_residual_into_final_row(self):
        """The partial first period contributes less than a full period, so
        without a true-up the schedule would leave a small residual above
        salvage after the nominal number of periods -- confirm it's balanced
        into the last row instead."""
        asset = _make_asset(purchase_cost=100000, salvage_value=0, useful_life=1,
                             available_for_use_date="2026-06-20", purchase_date="2026-06-20",
                             depreciation_method="Written Down Value", depreciation_posting_frequency="Monthly")
        rows = build_schedule(asset)
        self.assertAlmostEqual(rows[-1]["closing_value"], 0.0, places=2)


if __name__ == "__main__":
    unittest.main()