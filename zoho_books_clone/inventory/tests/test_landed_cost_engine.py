"""
Tests for the Landed Cost Voucher allocation engine (allocate_charges only —
it's pure and needs no DB/mocking; get_source_items needs a live frappe.db
and is exercised via bench's integration tests instead).

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.inventory.tests.test_landed_cost_engine
"""

import unittest

from zoho_books_clone.inventory.landed_cost_engine import (
    allocate_charges,
    compute_capitalizable_amount,
    compute_gl_scale_ratio,
)


class TestAllocateCharges(unittest.TestCase):

    def test_by_value_distributes_proportionally(self):
        items = [
            {"item_code": "A", "received_qty": 10, "purchase_amount": 8000},
            {"item_code": "B", "received_qty": 5, "purchase_amount": 2000},
        ]
        charges = [{"amount": 500}, {"amount": 200}]  # total 700

        result = allocate_charges(items, charges, "By Value")

        # 8000/10000 * 700 = 560, 2000/10000 * 700 = 140
        self.assertAlmostEqual(result[0]["allocated_amount"], 560.0, places=2)
        self.assertAlmostEqual(result[1]["allocated_amount"], 140.0, places=2)
        self.assertAlmostEqual(sum(r["allocated_amount"] for r in result), 700.0, places=2)

    def test_by_qty_distributes_proportionally(self):
        items = [
            {"item_code": "A", "received_qty": 30, "purchase_amount": 1000},
            {"item_code": "B", "received_qty": 10, "purchase_amount": 5000},
        ]
        charges = [{"amount": 400}]

        result = allocate_charges(items, charges, "By Qty")

        # 30/40 * 400 = 300, 10/40 * 400 = 100
        self.assertAlmostEqual(result[0]["allocated_amount"], 300.0, places=2)
        self.assertAlmostEqual(result[1]["allocated_amount"], 100.0, places=2)

    def test_rounding_remainder_lands_on_last_row(self):
        # 700 split three ways by equal purchase_amount -> 233.33 recurring
        items = [
            {"item_code": "A", "received_qty": 1, "purchase_amount": 100},
            {"item_code": "B", "received_qty": 1, "purchase_amount": 100},
            {"item_code": "C", "received_qty": 1, "purchase_amount": 100},
        ]
        charges = [{"amount": 700}]

        result = allocate_charges(items, charges, "By Value")

        total_allocated = sum(r["allocated_amount"] for r in result)
        self.assertAlmostEqual(total_allocated, 700.0, places=2)
        # First two rows rounded evenly; last row absorbs the leftover paisa.
        self.assertAlmostEqual(result[0]["allocated_amount"], 233.33, places=2)
        self.assertAlmostEqual(result[1]["allocated_amount"], 233.33, places=2)
        self.assertAlmostEqual(result[2]["allocated_amount"], 233.34, places=2)

    def test_zero_charge_leaves_valuation_unchanged(self):
        items = [{"item_code": "A", "received_qty": 10, "purchase_amount": 1000}]
        result = allocate_charges(items, [], "By Value")

        self.assertEqual(result[0]["allocated_amount"], 0.0)
        self.assertAlmostEqual(result[0]["new_valuation_rate"], 100.0, places=2)

    def test_single_item_source_gets_full_charge(self):
        items = [{"item_code": "A", "received_qty": 10, "purchase_amount": 10000}]
        charges = [{"amount": 500}, {"amount": 200}]

        result = allocate_charges(items, charges, "By Value")

        self.assertAlmostEqual(result[0]["allocated_amount"], 700.0, places=2)
        # (10000 + 700) / 10 = 1070
        self.assertAlmostEqual(result[0]["new_valuation_rate"], 1070.0, places=2)

    def test_zero_basis_falls_back_to_equal_split(self):
        # Free-sample rows: purchase_amount is 0 for every row, so "By Value"
        # can't weight by value — falls back to an equal split.
        items = [
            {"item_code": "A", "received_qty": 5, "purchase_amount": 0},
            {"item_code": "B", "received_qty": 5, "purchase_amount": 0},
        ]
        charges = [{"amount": 100}]

        result = allocate_charges(items, charges, "By Value")

        self.assertAlmostEqual(result[0]["allocated_amount"], 50.0, places=2)
        self.assertAlmostEqual(result[1]["allocated_amount"], 50.0, places=2)

    def test_empty_items_returns_empty(self):
        self.assertEqual(allocate_charges([], [{"amount": 100}], "By Value"), [])


class TestComputeCapitalizableAmount(unittest.TestCase):
    """Phase 5 guardrail — partial-consumption capitalization math."""

    def test_fully_on_hand_capitalizes_full_amount(self):
        self.assertAlmostEqual(
            compute_capitalizable_amount(allocated_amount=500, received_qty=100, current_qty=100),
            500.0, places=2,
        )

    def test_more_on_hand_than_received_still_caps_at_full_amount(self):
        # e.g. a second, unrelated purchase topped up the same bin later —
        # current_qty (150) must not inflate the capitalized amount beyond
        # what this row's own charge actually covers.
        self.assertAlmostEqual(
            compute_capitalizable_amount(allocated_amount=500, received_qty=100, current_qty=150),
            500.0, places=2,
        )

    def test_partially_on_hand_capitalizes_proportional_share(self):
        # 40 of 100 units still on hand -> 40% of the OMR 500 charge.
        self.assertAlmostEqual(
            compute_capitalizable_amount(allocated_amount=500, received_qty=100, current_qty=40),
            200.0, places=2,
        )

    def test_fully_issued_capitalizes_nothing(self):
        self.assertEqual(
            compute_capitalizable_amount(allocated_amount=500, received_qty=100, current_qty=0),
            0.0,
        )

    def test_negative_current_qty_capitalizes_nothing(self):
        self.assertEqual(
            compute_capitalizable_amount(allocated_amount=500, received_qty=100, current_qty=-5),
            0.0,
        )

    def test_zero_allocated_amount_short_circuits(self):
        self.assertEqual(
            compute_capitalizable_amount(allocated_amount=0, received_qty=100, current_qty=100),
            0.0,
        )

    def test_zero_received_qty_short_circuits(self):
        self.assertEqual(
            compute_capitalizable_amount(allocated_amount=500, received_qty=0, current_qty=10),
            0.0,
        )

    def test_matches_the_client_example(self):
        # ABC Herbs raw materials: OMR 10,000 base, OMR 700 landed cost, all still
        # on hand -> the full OMR 700 capitalizes, landed cost = OMR 10,700.
        capitalized = compute_capitalizable_amount(
            allocated_amount=700, received_qty=100, current_qty=100
        )
        self.assertAlmostEqual(capitalized, 700.0, places=2)


class TestComputeGlScaleRatio(unittest.TestCase):
    """Phase 5 guardrail — GL credit scaling so Dr Inventory always equals
    the sum of what was actually written to Bin.stock_value."""

    def test_full_capitalization_gives_ratio_one(self):
        self.assertAlmostEqual(compute_gl_scale_ratio(700, 700), 1.0, places=4)

    def test_partial_capitalization_gives_proportional_ratio(self):
        self.assertAlmostEqual(compute_gl_scale_ratio(200, 500), 0.4, places=4)

    def test_zero_capitalization_gives_zero_ratio(self):
        self.assertEqual(compute_gl_scale_ratio(0, 500), 0.0)

    def test_zero_total_charges_never_divides_by_zero(self):
        self.assertEqual(compute_gl_scale_ratio(0, 0), 0.0)

    def test_ratio_is_clamped_at_one(self):
        # Defensive: rounding on individual rows should never let capitalized
        # exceed total_charges, but the clamp makes that a guarantee.
        self.assertAlmostEqual(compute_gl_scale_ratio(701, 700), 1.0, places=4)


if __name__ == "__main__":
    unittest.main()