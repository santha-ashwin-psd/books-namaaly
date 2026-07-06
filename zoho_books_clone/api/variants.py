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


# ─── Variant Manager page ──────────────────────────────────────────────────────

def _variant_in_use(item_code: str) -> bool:
    """True when a variant is referenced by any transaction, so it can't be
    safely deleted or have its code (primary key) renamed."""
    for dt in ("Sales Invoice Item", "Purchase Invoice Item", "Stock Ledger Entry"):
        if frappe.db.exists(dt, {"item_code": item_code}):
            return True
    return False


@frappe.whitelist(allow_guest=False)
def get_variant_manager(template_item: str) -> dict:
    """Everything the Variant Manager page needs for one template in a single call:
    the template header + declared attributes, and every variant with its
    attribute values, on-hand stock (summed across warehouses) and an in-use flag."""
    if not can_read("Item"):
        return {"template": None, "variants": []}

    tmpl = frappe.get_doc("Item", template_item)
    template = {
        "name":          tmpl.name,
        "item_code":     tmpl.item_code,
        "item_name":     tmpl.item_name,
        "item_group":    tmpl.get("item_group"),
        "is_stock_item": int(tmpl.get("is_stock_item") or 0),
        "hsn_code":      tmpl.get("hsn_code"),
        "attributes":    _grouped_attributes(tmpl),
    }

    variants = frappe.get_all(
        "Item",
        filters={"variant_of": template_item},
        fields=["name", "item_code", "item_name", "hsn_code",
                "standard_rate", "standard_buying_rate", "disabled", "is_stock_item"],
        order_by="item_code asc",
    )
    for v in variants:
        v["attributes"] = frappe.get_all(
            "Item Variant Attribute",
            filters={"parent": v["name"], "parenttype": "Item"},
            fields=["attribute", "attribute_value"],
            order_by="idx asc",
        )
        agg = frappe.db.sql(
            """SELECT COALESCE(SUM(actual_qty), 0)  AS qty,
                      COALESCE(SUM(stock_value), 0) AS value
               FROM `tabBin` WHERE item_code = %s""",
            v["name"], as_dict=True,
        )
        v["actual_qty"]  = flt(agg[0].qty) if agg else 0.0
        v["stock_value"] = flt(agg[0].value) if agg else 0.0
        v["in_use"]      = _variant_in_use(v["name"])

    return {"template": template, "variants": variants}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def update_variant(
    item_code: str,
    item_name: str | None = None,
    standard_rate=None,
    standard_buying_rate=None,
    hsn_code: str | None = None,
    disabled=None,
    new_item_code: str | None = None,
) -> dict:
    """Update a single variant's editable fields. Renaming the code (SKU) is only
    allowed when the variant isn't used in any transaction, since the code is the
    Item's primary key."""
    require_module("inventory", write=True)
    if not frappe.db.exists("Item", item_code):
        frappe.throw(f"Variant {item_code} not found")

    updates: dict = {}
    if item_name is not None:
        updates["item_name"] = item_name
    if hsn_code is not None:
        updates["hsn_code"] = hsn_code
    if standard_rate is not None:
        updates["standard_rate"] = max(flt(standard_rate), 0)
    if standard_buying_rate is not None:
        updates["standard_buying_rate"] = max(flt(standard_buying_rate), 0)
    if disabled is not None:
        updates["disabled"] = int(frappe.utils.cint(disabled))
    if updates:
        frappe.db.set_value("Item", item_code, updates)

    renamed_to = None
    if new_item_code and new_item_code.strip() and new_item_code.strip() != item_code:
        target = new_item_code.strip()
        if _variant_in_use(item_code):
            frappe.throw(
                f"Cannot rename {item_code}: it is already used in transactions. "
                "Renaming would break existing invoices or stock records."
            )
        if frappe.db.exists("Item", target):
            frappe.throw(f"An item with code '{target}' already exists.")
        frappe.rename_doc("Item", item_code, target)
        frappe.db.set_value("Item", target, "item_code", target)
        renamed_to = target

    frappe.db.commit()
    return {"item_code": renamed_to or item_code, "renamed": bool(renamed_to)}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def bulk_update_variant_prices(
    variant_codes: str | list,
    field: str,
    mode: str,
    value=0,
    decimals: int = 2,
) -> dict:
    """Apply one price operation across many variants at once.
      field: 'selling' | 'buying'
      mode:  'set' | 'inc_pct' | 'inc_amt' | 'round'
    Returns the new rate per variant so the UI can patch state without reloading."""
    require_module("inventory", write=True)

    if isinstance(variant_codes, str):
        variant_codes = json.loads(variant_codes or "[]")
    if not variant_codes:
        frappe.throw("No variants selected.")

    fieldname = {"selling": "standard_rate", "buying": "standard_buying_rate"}.get(field)
    if not fieldname:
        frappe.throw("field must be 'selling' or 'buying'.")
    if mode not in ("set", "inc_pct", "inc_amt", "round"):
        frappe.throw("mode must be one of set / inc_pct / inc_amt / round.")

    val = flt(value)
    updated = []
    for code in variant_codes:
        current = flt(frappe.db.get_value("Item", code, fieldname))
        if mode == "set":
            new_rate = val
        elif mode == "inc_pct":
            new_rate = current * (1 + val / 100.0)
        elif mode == "inc_amt":
            new_rate = current + val
        else:  # round
            new_rate = current
        new_rate = round(max(new_rate, 0), int(decimals))
        frappe.db.set_value("Item", code, fieldname, new_rate)
        updated.append({"item_code": code, "field": field, "rate": new_rate})

    frappe.db.commit()
    return {"updated": updated, "count": len(updated)}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def delete_variant(item_code: str) -> dict:
    """Delete a variant Item, unless it is referenced by any transaction."""
    require_module("inventory", write=True)
    if not frappe.db.exists("Item", item_code):
        return {"deleted": item_code}
    if _variant_in_use(item_code):
        frappe.throw(
            f"Cannot delete {item_code}: it is used in invoices or stock records. "
            "Disable it instead."
        )
    frappe.delete_doc("Item", item_code, ignore_permissions=True)
    frappe.db.commit()
    return {"deleted": item_code}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def set_template_attributes(template_item: str, attributes: str | list) -> dict:
    """Replace the template's declared attribute/value rows, and make sure each
    referenced Item Attribute master carries those values (so they stay reusable).
    Call create_variants() afterwards to (re)generate the combinations."""
    require_module("inventory", write=True)

    if isinstance(attributes, str):
        attributes = json.loads(attributes or "[]")

    tmpl = frappe.get_doc("Item", template_item)
    tmpl.set("attributes", [])
    for row in attributes:
        attr = (row.get("attribute") or "").strip()
        vals = [str(v).strip() for v in (row.get("values") or []) if str(v).strip()]
        if not attr or not vals:
            continue
        # Flatten to one child row per value (matches _grouped_attributes' reader).
        for v in vals:
            tmpl.append("attributes", {"attribute": attr, "attribute_value": v})
        _merge_attribute_master(attr, vals)

    if not tmpl.get("has_variants"):
        tmpl.has_variants = 1
    tmpl.save(ignore_permissions=True)
    frappe.db.commit()
    return {"template": tmpl.name, "attributes": _grouped_attributes(tmpl)}


def _merge_attribute_master(attribute: str, values: list[str]) -> None:
    """Ensure the Item Attribute master exists and contains the given values."""
    if not frappe.db.exists("Item Attribute", attribute):
        doc = frappe.new_doc("Item Attribute")
        doc.attribute_name = attribute
        for v in values:
            doc.append("attribute_values", {"attribute_value": v})
        doc.insert(ignore_permissions=True)
        return
    doc = frappe.get_doc("Item Attribute", attribute)
    have = {r.attribute_value for r in (doc.attribute_values or [])}
    changed = False
    for v in values:
        if v not in have:
            doc.append("attribute_values", {"attribute_value": v})
            changed = True
    if changed:
        doc.save(ignore_permissions=True)
