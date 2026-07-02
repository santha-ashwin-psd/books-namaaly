from __future__ import annotations
"""
Item Variants API.

A template Item (`has_variants=1`) declares which attributes/values apply via its
`attributes` child table (one row per candidate value, e.g. Size→S, Size→M,
Colour→Red). `create_variants` expands those into concrete variant Items
(`variant_of` = template), each carrying its own attribute values and a copy of
the template's pricing/accounts. Variants are the sellable/stockable items;
templates are hidden from transaction pickers.
"""
import json
import itertools

import frappe
from frappe.utils import flt

from zoho_books_clone.utils.access import require_module, can_read


def _grouped_attributes(tmpl) -> dict:
    """{attribute_name: [values...]} from the template's `attributes` rows."""
    groups = {}
    for row in (tmpl.attributes or []):
        if not row.attribute:
            continue
        vals = groups.setdefault(row.attribute, [])
        if row.attribute_value and row.attribute_value not in vals:
            vals.append(row.attribute_value)
    return groups


def _cartesian(tmpl) -> list[dict]:
    groups = _grouped_attributes(tmpl)
    keys = list(groups.keys())
    combos = []
    for values in itertools.product(*[groups[k] for k in keys]):
        combos.append({keys[i]: values[i] for i in range(len(keys))})
    return combos


@frappe.whitelist(allow_guest=False, methods=["POST"])
def create_variants(template_item: str, combinations: str | None = None) -> dict:
    """Generate a variant Item for each attribute combination of the template.

    combinations (optional): JSON list of {attribute: value} dicts. When omitted,
    the full cartesian product of the template's declared attribute values is used.
    Existing variant codes are skipped (safe to re-run to add new combinations).
    """
    require_module("inventory", write=True)

    tmpl = frappe.get_doc("Item", template_item)

    if isinstance(combinations, str):
        combinations = json.loads(combinations or "null")
    if not combinations:
        combinations = _cartesian(tmpl)
    if not combinations:
        frappe.throw("No attribute values defined — add attributes and values first.")

    created, skipped = [], []
    for combo in combinations:
        # Deterministic code + readable name from the ordered values.
        values = [str(combo[k]).strip() for k in combo]
        code = f"{tmpl.item_code}-" + "-".join(values)
        if frappe.db.exists("Item", code):
            skipped.append(code)
            continue

        v = frappe.new_doc("Item")
        v.update({
            "item_code": code,
            "item_name": f"{tmpl.item_name} - " + ", ".join(values),
            "item_group": tmpl.item_group,
            "item_type": tmpl.item_type,
            "stock_uom": tmpl.stock_uom,
            "hsn_code": tmpl.get("hsn_code"),
            "standard_rate": flt(tmpl.get("standard_rate")),
            "standard_buying_rate": flt(tmpl.get("standard_buying_rate")),
            "tax_code": tmpl.get("tax_code"),
            "income_account": tmpl.get("income_account"),
            "expense_account": tmpl.get("expense_account"),
            "is_stock_item": tmpl.get("is_stock_item"),
            "valuation_method": tmpl.get("valuation_method"),
            "variant_of": tmpl.name,
            "has_variants": 0,
            "books_company": tmpl.get("books_company"),
        })
        for attr, val in combo.items():
            v.append("attributes", {"attribute": attr, "attribute_value": val})
        v.insert(ignore_permissions=True)
        created.append(v.name)

    if not tmpl.get("has_variants"):
        tmpl.db_set("has_variants", 1)

    return {"created": created, "skipped": skipped, "count": len(created)}


@frappe.whitelist(allow_guest=False)
def get_variants(template_item: str) -> list[dict]:
    """List the variant Items under a template with their attribute values."""
    if not can_read("Item"):
        return []
    rows = frappe.get_all(
        "Item",
        filters={"variant_of": template_item},
        fields=["name", "item_code", "item_name", "standard_rate", "standard_buying_rate", "disabled"],
        order_by="item_code asc",
    )
    for r in rows:
        r["attributes"] = frappe.get_all(
            "Item Variant Attribute",
            filters={"parent": r["name"], "parenttype": "Item"},
            fields=["attribute", "attribute_value"],
            order_by="idx asc",
        )
    return rows
