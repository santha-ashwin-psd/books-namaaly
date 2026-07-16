"""
Diagnostic: trace why an item's Bin valuation_rate looks wrong.

Run with:
    bench --site <your-site> execute zoho_books_clone.db.queries.diagnose_item_valuation --args "['Aadhari Sahacharadi Kashayam 200ml','Item-01','Agasthya Rasayanam 250gm','Allergycure Capsules 60Nos']"

Or paste this as a one-off in `bench console`:
    from zoho_books_clone.db.queries import diagnose_item_valuation
    diagnose_item_valuation(["Aadhari Sahacharadi Kashayam 200ml", "Item-01"])
"""
import frappe


def diagnose_item_valuation(item_names):
    """
    For each item name given, resolve the item_code and print:
      - current Bin rows (warehouse, actual_qty, stock_value, valuation_rate)
      - the full Stock Ledger Entry history (what pushed the valuation rate up/down)
      - whether the item is a manufactured item (has a BOM) and its last Work Order cost
    """
    if isinstance(item_names, str):
        import json
        item_names = json.loads(item_names)

    for name in item_names:
        item_code = frappe.db.get_value(
            "Item", {"item_name": name}, "name"
        ) or frappe.db.get_value("Item", name, "name")
        if not item_code:
            print(f"\n=== {name}: ITEM NOT FOUND ===")
            continue

        print(f"\n=== {name} ({item_code}) ===")

        bins = frappe.db.sql("""
            SELECT warehouse, actual_qty, stock_value, valuation_rate
            FROM `tabBin` WHERE item_code = %s
        """, item_code, as_dict=True)
        print("-- Bin rows --")
        for b in bins:
            print(f"  {b.warehouse}: qty={b.actual_qty} stock_value={b.stock_value} valuation_rate={b.valuation_rate}")

        sle = frappe.db.sql("""
            SELECT posting_date, voucher_type, voucher_no, actual_qty,
                   incoming_rate, valuation_rate, stock_value_difference, warehouse
            FROM `tabStock Ledger Entry`
            WHERE item_code = %s AND is_cancelled = 0
            ORDER BY posting_date, posting_time, creation
        """, item_code, as_dict=True)
        print(f"-- Stock Ledger Entry history ({len(sle)} rows) --")
        for s in sle:
            print(f"  {s.posting_date}  {s.voucher_type:<18} {s.voucher_no:<15} "
                  f"qty={s.actual_qty:>8}  in_rate={s.incoming_rate:>10}  "
                  f"running_valuation={s.valuation_rate:>10}  warehouse={s.warehouse}")

        has_bom = frappe.db.exists("BOM", {"item": item_code, "is_active": 1})
        print(f"-- Has active BOM (manufactured item): {bool(has_bom)}")
        if has_bom:
            bom_rate = frappe.db.get_value("BOM", has_bom, "total_cost")
            bom_qty = frappe.db.get_value("BOM", has_bom, "quantity") or 1
            print(f"   BOM {has_bom}: total_cost={bom_rate} for qty={bom_qty} "
                  f"=> BOM cost/unit={frappe.utils.flt(bom_rate)/frappe.utils.flt(bom_qty):.2f}")

        item = frappe.db.get_value(
            "Item", item_code, ["stock_uom", "standard_buying_rate", "standard_rate"], as_dict=True
        )
        print(f"-- Item master: stock_uom={item.stock_uom}  "
              f"standard_buying_rate={item.standard_buying_rate}  standard_rate={item.standard_rate}")