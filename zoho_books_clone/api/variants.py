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
from frappe.utils import flt, cint

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


# Child doctypes that reference an Item by item_code. A variant showing up in
# any of these is "in use" — its code becomes read-only and it can't be deleted
# (disable it instead).
_ITEM_USAGE_DOCTYPES = [
    "Sales Invoice Item", "Purchase Invoice Item", "Credit Note Item",
    "Sales Order Item", "Purchase Order Item", "Delivery Note Item",
    "Quotation Item", "Purchase Receipt Item", "Stock Entry Detail",
    "Stock Ledger Entry",
]


def _items_in_use(codes: list[str]) -> set[str]:
    """Subset of `codes` referenced by any transaction/stock-movement doctype."""
    in_use, remaining = set(), set(codes)
    for doctype in _ITEM_USAGE_DOCTYPES:
        if not remaining:
            break
        rows = frappe.get_all(
            doctype, filters={"item_code": ["in", list(remaining)]},
            fields=["item_code"], distinct=True,
        )
        found = {r.item_code for r in rows}
        in_use |= found
        remaining -= found
    return in_use


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


@frappe.whitelist(allow_guest=False)
def get_variant_manager(template_item: str) -> dict:
    """Everything the Variant Manager page needs in one call: the template's
    declared attributes plus its variants, each enriched with live stock and
    an `in_use` flag (referenced by any transaction/stock-movement doctype)."""
    if not can_read("Item"):
        frappe.throw("Not permitted", frappe.PermissionError)

    if not frappe.db.exists("Item", template_item):
        frappe.throw("Template item not found")

    tmpl = frappe.get_doc("Item", template_item)
    if not tmpl.get("has_variants"):
        frappe.throw("This item is not a variant template")

    variants = get_variants(template_item)
    codes = [v["name"] for v in variants]

    stock_by_code = {}
    if codes:
        placeholders = ", ".join(["%s"] * len(codes))
        for row in frappe.db.sql(
            f"""
            SELECT item_code, SUM(actual_qty) AS actual_qty, SUM(stock_value) AS stock_value
            FROM `tabBin`
            WHERE item_code IN ({placeholders})
            GROUP BY item_code
            """,
            tuple(codes),
            as_dict=True,
        ):
            stock_by_code[row.item_code] = row

    in_use_codes = _items_in_use(codes) if codes else set()

    for v in variants:
        s = stock_by_code.get(v["name"])
        v["actual_qty"] = flt(s.actual_qty) if s else 0.0
        v["stock_value"] = flt(s.stock_value) if s else 0.0
        v["in_use"] = v["name"] in in_use_codes

    return {
        "template": {
            "item_code": tmpl.item_code,
            "item_name": tmpl.item_name,
            "is_stock_item": tmpl.get("is_stock_item"),
            "attributes": _grouped_attributes(tmpl),
        },
        "variants": variants,
    }


@frappe.whitelist(allow_guest=False, methods=["POST"])
def set_template_attributes(template_item: str, attributes=None) -> dict:
    """Rebuild the template's declared attribute/value rows from the editor's
    [{attribute, values: [...]}] shape (one child row per attribute value)."""
    require_module("inventory", write=True)

    tmpl = frappe.get_doc("Item", template_item)

    if isinstance(attributes, str):
        attributes = json.loads(attributes or "[]")

    tmpl.set("attributes", [])
    for row in (attributes or []):
        attr = str((row or {}).get("attribute") or "").strip()
        if not attr:
            continue
        seen = set()
        for val in (row or {}).get("values") or []:
            val = str(val).strip()
            if val and val not in seen:
                seen.add(val)
                tmpl.append("attributes", {"attribute": attr, "attribute_value": val})

    if not tmpl.get("has_variants"):
        tmpl.has_variants = 1

    tmpl.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def update_variant(
    item_code: str,
    item_name: str | None = None,
    standard_rate=None,
    standard_buying_rate=None,
    disabled=None,
    new_item_code: str | None = None,
) -> dict:
    """Save edits to a single variant row (name/prices/active toggle), plus an
    optional SKU rename. Only the fields actually passed are touched."""
    require_module("inventory", write=True)

    doc = frappe.get_doc("Item", item_code)
    if not doc.get("variant_of"):
        frappe.throw("Not a variant item")

    if item_name is not None:
        doc.item_name = item_name
    if standard_rate is not None:
        doc.standard_rate = flt(standard_rate)
    if standard_buying_rate is not None:
        doc.standard_buying_rate = flt(standard_buying_rate)
    if disabled is not None:
        doc.disabled = cint(disabled)
    doc.save(ignore_permissions=True)

    final_code, renamed = doc.name, False
    if new_item_code and new_item_code != doc.name:
        if _items_in_use([doc.name]):
            frappe.throw("Item is used in transactions — code can't change")
        if frappe.db.exists("Item", new_item_code):
            frappe.throw(f"Item code {new_item_code} already exists")
        frappe.rename_doc("Item", doc.name, new_item_code, ignore_permissions=True)
        final_code, renamed = new_item_code, True

    frappe.db.commit()
    return {"item_code": final_code, "renamed": renamed}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def delete_variant(item_code: str) -> dict:
    """Delete a variant Item outright. Blocked if it's referenced anywhere —
    disable it instead in that case."""
    require_module("inventory", write=True)

    doc = frappe.get_doc("Item", item_code)
    if not doc.get("variant_of"):
        frappe.throw("Not a variant item")
    if _items_in_use([item_code]):
        frappe.throw("Item is used in transactions — disable it instead")

    frappe.delete_doc("Item", item_code, ignore_permissions=True)
    frappe.db.commit()
    return {"deleted": item_code}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def bulk_update_variant_prices(variant_codes, field: str, mode: str, value=0, decimals: int = 2) -> dict:
    """Apply a rate change across many variants at once.

    field: "selling" -> standard_rate, "buying" -> standard_buying_rate.
    mode: "set" (absolute value), "inc_pct" (± percent, pass a negative value
    to decrease), "inc_amt" (± flat amount), or "round" (round the current
    rate to `decimals` places, ignoring `value`).
    """
    require_module("inventory", write=True)

    if isinstance(variant_codes, str):
        variant_codes = json.loads(variant_codes or "[]")
    if not variant_codes:
        frappe.throw("No variants selected")
    if field not in ("selling", "buying"):
        frappe.throw(f"Unknown field: {field}")
    if mode not in ("set", "inc_pct", "inc_amt", "round"):
        frappe.throw(f"Unknown mode: {mode}")

    fieldname = "standard_rate" if field == "selling" else "standard_buying_rate"
    value = flt(value)
    decimals = cint(decimals)

    updated = []
    for code in variant_codes:
        current = flt(frappe.db.get_value("Item", code, fieldname))
        if mode == "set":
            new_rate = value
        elif mode == "inc_pct":
            new_rate = current * (1 + value / 100)
        elif mode == "inc_amt":
            new_rate = current + value
        else:  # round
            new_rate = current

        new_rate = max(0, round(flt(new_rate), decimals))
        frappe.db.set_value("Item", code, fieldname, new_rate)
        updated.append({"item_code": code, "rate": new_rate})

    frappe.db.commit()
    return {"updated": updated, "count": len(updated)}
