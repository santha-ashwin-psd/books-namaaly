"""
Tests for BOM cost calculation and BOM validation logic.

Run with:
    bench run-tests --app zoho_books_clone --module zoho_books_clone.manufacturing.tests.test_bom
"""

import unittest
from unittest.mock import MagicMock, patch
from frappe.utils import flt


# ---------------------------------------------------------------------------
# Helpers — build lightweight mock BOM doc objects without DB access
# ---------------------------------------------------------------------------

def _make_item_row(item_code, qty, rate, sub_assembly_bom=None):
    row = MagicMock()
    row.item_code = item_code
    row.item_name = item_code
    row.qty = qty
    row.rate = rate
    row.uom = "Nos"
    row.sub_assembly_bom = sub_assembly_bom
    row.source_warehouse = ""
    row.amount = 0.0
    return row


def _make_op_row(operation, time_in_mins, hour_rate):
    row = MagicMock()
    row.operation = operation
    row.time_in_mins = time_in_mins
    row.hour_rate = hour_rate
    row.cost = 0.0
    return row


def _make_scrap_row(item_code, qty, rate):
    row = MagicMock()
    row.item_code = item_code
    row.qty = qty
    row.rate = rate
    row.amount = 0.0
    return row


def _make_bom(bom_type="Manufacturing", items=None, operations=None, scrap_items=None,
               packing_items=None, bulk_item=None, bulk_qty_per_unit=1.0):
    bom = MagicMock()
    bom.bom_type = bom_type
    bom.items = items or []
    bom.operations = operations or []
    bom.scrap_items = scrap_items or []
    bom.packing_items = packing_items or []
    bom.bulk_item = bulk_item
    bom.bulk_qty_per_unit = bulk_qty_per_unit
    bom.quantity = 1.0
    bom.rm_cost = 0.0
    bom.op_cost = 0.0
    bom.scrap_value = 0.0
    bom.total_cost = 0.0
    bom.amended_from = None
    bom.company = ""
    bom.process_loss = 0.0
    bom.is_phantom_bom = 0
    return bom


# ---------------------------------------------------------------------------
# Unit tests for _calc_costs
# ---------------------------------------------------------------------------

class TestBOMCostCalc(unittest.TestCase):

    def _run_calc_costs(self, bom):
        """Run _calc_costs by importing and calling the method directly via unbound call."""
        from zoho_books_clone.manufacturing.doctype.bom.bom import BOM
        BOM._calc_costs(bom)

    def test_rm_cost_is_sum_of_qty_times_rate(self):
        items = [
            _make_item_row("RAW-001", qty=10, rate=50),
            _make_item_row("RAW-002", qty=5,  rate=100),
        ]
        bom = _make_bom(items=items)
        self._run_calc_costs(bom)
        # 10×50 + 5×100 = 500 + 500 = 1000
        self.assertAlmostEqual(bom.rm_cost, 1000.0)
        self.assertAlmostEqual(items[0].amount, 500.0)
        self.assertAlmostEqual(items[1].amount, 500.0)

    def test_op_cost_is_time_over_60_times_rate(self):
        ops = [
            _make_op_row("Mixing",    time_in_mins=60,  hour_rate=120),
            _make_op_row("Packaging", time_in_mins=30,  hour_rate=80),
        ]
        bom = _make_bom(operations=ops)
        self._run_calc_costs(bom)
        # 60/60×120 + 30/60×80 = 120 + 40 = 160
        self.assertAlmostEqual(bom.op_cost, 160.0)
        self.assertAlmostEqual(ops[0].cost, 120.0)
        self.assertAlmostEqual(ops[1].cost, 40.0)

    def test_scrap_value_and_total_cost(self):
        items  = [_make_item_row("RM-A", qty=10, rate=100)]
        scrap  = [_make_scrap_row("BY-001", qty=2, rate=15)]
        bom = _make_bom(items=items, scrap_items=scrap)
        self._run_calc_costs(bom)
        # rm=1000, op=0, scrap=30, total=970
        self.assertAlmostEqual(bom.rm_cost,    1000.0)
        self.assertAlmostEqual(bom.scrap_value,   30.0)
        self.assertAlmostEqual(bom.total_cost,   970.0)

    def test_packing_bom_uses_packing_items(self):
        """Packing BOM should cost from packing_items, not items."""
        packing = [
            _make_item_row("BOTTLE", qty=1, rate=5),
            _make_item_row("LABEL",  qty=1, rate=2),
        ]
        bom = _make_bom(bom_type="Packing", packing_items=packing)
        self._run_calc_costs(bom)
        self.assertAlmostEqual(bom.rm_cost, 7.0)  # 5+2

    def test_zero_rates(self):
        items = [_make_item_row("FREE-RM", qty=100, rate=0)]
        bom = _make_bom(items=items)
        self._run_calc_costs(bom)
        self.assertAlmostEqual(bom.rm_cost,   0.0)
        self.assertAlmostEqual(bom.total_cost, 0.0)

    def test_total_cost_cannot_go_below_zero_conceptually(self):
        """Sanity: if scrap > rm+op, total_cost is negative (the formula allows this
        — it is the caller's responsibility to have meaningful data)."""
        items = [_make_item_row("RM", qty=1, rate=10)]
        scrap = [_make_scrap_row("SCRAP", qty=100, rate=1)]
        bom   = _make_bom(items=items, scrap_items=scrap)
        self._run_calc_costs(bom)
        self.assertAlmostEqual(bom.total_cost, 10 - 100)  # = -90


# ---------------------------------------------------------------------------
# Unit tests for _explode_bom_items (phantom + sub-assembly)
# ---------------------------------------------------------------------------

class TestExplodeBomItems(unittest.TestCase):

    def _explode(self, rows, ratio=1.0, depth=0):
        from zoho_books_clone.manufacturing.work_order_engine import _explode_bom_items
        return _explode_bom_items(rows, ratio, depth)

    def test_flat_list_passthrough(self):
        rows = [
            _make_item_row("RM-A", qty=5, rate=10),
            _make_item_row("RM-B", qty=3, rate=20),
        ]
        result = self._explode(rows, ratio=2.0)
        self.assertEqual(len(result), 2)
        self.assertAlmostEqual(result[0]["required_qty"], 10.0)  # 5×2
        self.assertAlmostEqual(result[1]["required_qty"], 6.0)   # 3×2

    @patch("frappe.db.get_value")
    @patch("frappe.get_doc")
    def test_sub_assembly_exploded(self, mock_get_doc, mock_db_get_value):
        """A row with sub_assembly_bom should be replaced by its sub-BOM's items."""
        mock_db_get_value.return_value = None  # no phantom BOM auto-detection

        sub_items = [_make_item_row("LEAF-A", qty=2, rate=5)]
        sub_bom = _make_bom(items=sub_items)
        sub_bom.docstatus = 1
        sub_bom.quantity = 1.0
        mock_get_doc.return_value = sub_bom

        rows = [_make_item_row("SEMI-FINISHED", qty=4, rate=100, sub_assembly_bom="BOM-SEMI")]
        result = self._explode(rows, ratio=1.0)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["item_code"], "LEAF-A")
        self.assertAlmostEqual(result[0]["required_qty"], 8.0)  # 4×1 × 2

    @patch("frappe.db.get_value")
    def test_phantom_bom_auto_detected(self, mock_db_get_value):
        """If db.get_value returns a phantom BOM name for an item, it should be exploded."""
        # db.get_value("BOM", {"item": ..., "is_phantom_bom": 1 ...}, "name") → "BOM-PHANTOM"
        # We simulate phantom detection by patching the lookup
        # and then patching frappe.get_doc to return an explodable sub-BOM.
        with patch("frappe.get_doc") as mock_get_doc:
            mock_db_get_value.return_value = "BOM-PHANTOM"
            leaf = [_make_item_row("LEAF-X", qty=3, rate=10)]
            phantom_bom = _make_bom(items=leaf)
            phantom_bom.docstatus = 1
            phantom_bom.quantity = 1.0
            mock_get_doc.return_value = phantom_bom

            rows = [_make_item_row("PHANTOM-ITEM", qty=2, rate=50, sub_assembly_bom="")]
            result = self._explode(rows, ratio=1.0)

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["item_code"], "LEAF-X")
            self.assertAlmostEqual(result[0]["required_qty"], 6.0)  # 2×3

    @patch("frappe.db.get_value")
    @patch("frappe.get_doc")
    def test_circular_reference_guard(self, mock_get_doc, mock_db_get_value):
        """A BOM that references itself must not loop infinitely."""
        mock_db_get_value.return_value = None
        # Build a sub-bom that references the same row again
        row = _make_item_row("LOOP-ITEM", qty=1, rate=10, sub_assembly_bom="BOM-LOOP")
        loop_bom = _make_bom(items=[row])
        loop_bom.docstatus = 1
        loop_bom.quantity = 1.0
        mock_get_doc.return_value = loop_bom

        rows = [_make_item_row("LOOP-ITEM", qty=1, rate=10, sub_assembly_bom="BOM-LOOP")]
        # Should not raise; MAX_DEPTH prevents infinite recursion
        result = self._explode(rows, ratio=1.0, depth=0)
        self.assertIsInstance(result, list)


# ---------------------------------------------------------------------------
# Unit tests for BOM comparison helper logic
# ---------------------------------------------------------------------------

class TestCompareBoms(unittest.TestCase):

    def _compare(self, m1, m2):
        """Drive the comparison dict-building logic directly (no DB)."""
        all_items = sorted(set(m1) | set(m2))
        results = []
        for ic in all_items:
            r1, r2 = m1.get(ic), m2.get(ic)
            if r1 and r2:
                status = "unchanged" if (r1["qty"] == r2["qty"] and r1["rate"] == r2["rate"]) else "changed"
            elif r1:
                status = "removed"
            else:
                status = "added"
            results.append({"item_code": ic, "status": status})
        return results

    def test_same_items_marked_same(self):
        m = {"RM-A": {"qty": 10, "rate": 5, "uom": "Nos", "item_name": "RM-A"}}
        diff = self._compare(m, m)
        self.assertEqual(diff[0]["status"], "unchanged")

    def test_added_item_detected(self):
        m1 = {"RM-A": {"qty": 10, "rate": 5, "uom": "Nos", "item_name": "RM-A"}}
        m2 = {
            "RM-A": {"qty": 10, "rate": 5, "uom": "Nos", "item_name": "RM-A"},
            "RM-B": {"qty": 2,  "rate": 8, "uom": "Nos", "item_name": "RM-B"},
        }
        diff = self._compare(m1, m2)
        statuses = {d["item_code"]: d["status"] for d in diff}
        self.assertEqual(statuses["RM-A"], "unchanged")
        self.assertEqual(statuses["RM-B"], "added")

    def test_removed_item_detected(self):
        m1 = {"RM-A": {"qty": 10, "rate": 5, "uom": "Nos", "item_name": "RM-A"}}
        m2 = {}
        diff = self._compare(m1, m2)
        self.assertEqual(diff[0]["status"], "removed")

    def test_changed_qty_detected(self):
        m1 = {"RM-A": {"qty": 10, "rate": 5, "uom": "Nos", "item_name": "RM-A"}}
        m2 = {"RM-A": {"qty": 15, "rate": 5, "uom": "Nos", "item_name": "RM-A"}}
        diff = self._compare(m1, m2)
        self.assertEqual(diff[0]["status"], "changed")


# ---------------------------------------------------------------------------
# Unit tests for Alternative Item DocType validate
# ---------------------------------------------------------------------------

class TestAlternativeItemValidate(unittest.TestCase):

    def _run_validate(self, item_code, alt_code, conversion=1.0):
        import frappe
        doc = MagicMock()
        doc.item_code = item_code
        doc.alternative_item_code = alt_code
        doc.conversion_factor = conversion
        from zoho_books_clone.manufacturing.doctype.alternative_item.alternative_item import AlternativeItem
        # Temporarily suppress frappe.throw in unit context
        with patch("frappe.throw") as mock_throw:
            AlternativeItem.validate(doc)
            return mock_throw

    def test_self_reference_throws(self):
        mock_throw = self._run_validate("ITEM-A", "ITEM-A")
        mock_throw.assert_called_once()

    def test_zero_conversion_throws(self):
        mock_throw = self._run_validate("ITEM-A", "ITEM-B", conversion=0)
        mock_throw.assert_called_once()

    def test_negative_conversion_throws(self):
        mock_throw = self._run_validate("ITEM-A", "ITEM-B", conversion=-1)
        mock_throw.assert_called_once()

    def test_valid_alternative_passes(self):
        mock_throw = self._run_validate("ITEM-A", "ITEM-B", conversion=1.5)
        mock_throw.assert_not_called()


if __name__ == "__main__":
    unittest.main()