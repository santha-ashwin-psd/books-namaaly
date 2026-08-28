from __future__ import annotations
"""
Landed Cost Voucher — allocation engine.

get_source_items      -- pull item rows from the referenced Purchase Receipt /
                          Purchase Invoice (resolving warehouse the same way
                          stock_link._stock_rows does: row > doc.set_warehouse
                          > item default > company default) into the plain
                          dict shape a Landed Cost Voucher Item row expects.
allocate_charges       -- pure function: given item rows (purchase_amount,
                          received_qty) and charge rows (amount), proportionally
                          distribute the combined charge pool across items by
                          value or by qty, and derive each item's new
                          valuation rate. No DB access — safe to unit test in
                          isolation and to call from LandedCostVoucher.validate().
get_landed_cost_preview -- whitelisted endpoint combining the two above, for
                          the frontend to render a live preview before submit.

None of this writes to Bin or posts GL entries — that's Phase 3 (valuation)
and Phase 4 (GL reclassification).
"""

import json

import frappe
from frappe import _
from frappe.utils import flt

from zoho_books_clone.utils.access import assert_can
from zoho_books_clone.inventory.utils import get_valuation_rate

ROUND_PRECISION = 2


# ─── Pulling source rows ──────────────────────────────────────────────────────

def get_source_items(source_doctype: str, source_name: str) -> list[dict]:
    """Return one dict per stock item row on the referenced Purchase Receipt /
    Purchase Invoice, shaped for a Landed Cost Voucher Item row. Skips rows
    with no resolvable warehouse or a non-stock item, same as the auto stock
    entry builder in inventory/stock_link.py.
    """
    if source_doctype not in ("Purchase Receipt", "Purchase Invoice"):
        frappe.throw(_("Landed Cost Voucher source must be a Purchase Receipt or Purchase Invoice."))

    doc = frappe.get_doc(source_doctype, source_name)
    default_warehouse = _company_default_warehouse(doc.company)

    rows = []
    for row in (doc.items or []):
        item_code = getattr(row, "item_code", None)
        qty = flt(getattr(row, "qty", 0))
        if not item_code or qty <= 0:
            continue

        item_meta = frappe.db.get_value(
            "Item", item_code, ["is_stock_item", "default_warehouse"], as_dict=True
        ) or {}
        if not item_meta.get("is_stock_item"):
            continue

        warehouse = (
            getattr(row, "warehouse", None)
            or getattr(doc, "set_warehouse", None)
            or item_meta.get("default_warehouse")
            or default_warehouse
        )
        if not warehouse:
            continue

        rows.append({
            "item_code": item_code,
            "item_name": getattr(row, "item_name", None) or item_code,
            "warehouse": warehouse,
            "batch_no": getattr(row, "batch_no", None) or None,
            "received_qty": qty,
            "purchase_amount": flt(getattr(row, "amount", 0)) or flt(getattr(row, "rate", 0)) * qty,
            "valuation_rate": get_valuation_rate(item_code, warehouse),
            "reference_item_row": row.name,
        })

    if not rows:
        frappe.throw(
            _("No stock item rows with a resolvable warehouse were found on {0} {1}.").format(
                source_doctype, source_name
            )
        )
    return rows


def _company_default_warehouse(company: str | None) -> str | None:
    if not company:
        return None
    return frappe.db.get_value("Warehouse", {"company": company, "is_group": 0}, "name")


# ─── Allocation ────────────────────────────────────────────────────────────────

def allocate_charges(
    items: list[dict],
    charges: list[dict],
    distribution_method: str = "By Value",
) -> list[dict]:
    """Pure function — no DB access.

    items:   list of dicts with at least item_code, received_qty, purchase_amount.
             Returned copies gain allocated_amount and new_valuation_rate.
    charges: list of dicts with at least amount. Only the sum matters here —
             which account each charge nets against is a Phase 4 (GL) concern.
    distribution_method: "By Value" (basis = purchase_amount) or
             "By Qty" (basis = received_qty).

    Rounding: each row's share is rounded to 2 decimals; the leftover paisa
    from that rounding is dumped onto the last row so the allocated amounts
    always sum exactly to the total charge.
    """
    if not items:
        return []

    total_charges = sum(flt(c.get("amount")) for c in charges)
    result = [dict(row) for row in items]

    if total_charges == 0:
        for row in result:
            row["allocated_amount"] = 0.0
            row["new_valuation_rate"] = _rate(row)
        return result

    basis_key = "received_qty" if distribution_method == "By Qty" else "purchase_amount"
    bases = [flt(row.get(basis_key)) for row in result]
    total_basis = sum(bases)

    if total_basis <= 0:
        # Nothing to weight by (e.g. every purchase_amount is 0 for free-sample
        # rows) — fall back to an equal split across rows.
        bases = [1.0] * len(result)
        total_basis = float(len(result))

    running_total = 0.0
    for i, row in enumerate(result):
        if i == len(result) - 1:
            # Last row absorbs the rounding remainder.
            share = round(total_charges - running_total, ROUND_PRECISION)
        else:
            share = round(total_charges * (bases[i] / total_basis), ROUND_PRECISION)
            running_total += share
        row["allocated_amount"] = share
        row["new_valuation_rate"] = _rate(row)

    return result


def _rate(row: dict) -> float:
    qty = flt(row.get("received_qty"))
    if qty <= 0:
        return 0.0
    return round((flt(row.get("purchase_amount")) + flt(row.get("allocated_amount"))) / qty, 4)


# ─── Partial-consumption capitalization (Phase 5) ──────────────────────────────

def compute_capitalizable_amount(
    allocated_amount: float, received_qty: float, current_qty: float
) -> float:
    """Pure function — no DB access.

    An item row's allocated_amount was computed assuming all of received_qty
    is still on hand. By the time the voucher is actually submitted, some of
    that qty may have already been issued/sold — retroactively editing the
    COGS already posted for that portion is out of scope, so only the
    still-on-hand fraction of the charge gets capitalized into Bin value.

      current_qty >= received_qty  -> capitalize the full allocated_amount
      0 < current_qty < received_qty -> capitalize allocated_amount *
                                         (current_qty / received_qty)
      current_qty <= 0             -> capitalize nothing

    current_qty is clamped to received_qty before the ratio is taken, so
    stock received later from an unrelated purchase never inflates how much
    of *this* charge gets capitalized.
    """
    allocated_amount = flt(allocated_amount)
    received_qty = flt(received_qty)
    current_qty = flt(current_qty)

    if not allocated_amount or received_qty <= 0:
        return 0.0

    capitalizable_qty = min(current_qty, received_qty)
    if capitalizable_qty <= 0:
        return 0.0
    if capitalizable_qty >= received_qty:
        return round(allocated_amount, ROUND_PRECISION)
    return round(allocated_amount * (capitalizable_qty / received_qty), ROUND_PRECISION)


def compute_gl_scale_ratio(total_capitalized: float, total_charges: float) -> float:
    """Pure function — no DB access. The fraction of total_charges that was
    actually capitalized, used to scale every charge row's GL credit so
    Dr Inventory (== total_capitalized) always equals the sum of the scaled
    credits by construction. Clamped to 1.0 as a defensive ceiling — rounding
    on individual rows should never let the sum exceed the total, but the
    clamp makes that a guarantee rather than an assumption.
    """
    total_charges = flt(total_charges)
    if total_charges <= 0:
        return 0.0
    return min(flt(total_capitalized) / total_charges, 1.0)


def scale_charges_for_capitalization(
    charges: list[dict], total_capitalized: float, total_charges: float
) -> list[dict]:
    """Pure function — no DB access. Scale each charge row's amount by
    (total_capitalized / total_charges) for GL posting.

    Rounding each row independently (round(amount * ratio, 2) per row) can
    let the rows' sum drift a paisa or two away from total_capitalized in
    partial-capitalization cases — Bin.stock_value (built from item rows
    that already use last-row-absorbs-the-remainder rounding) and the GL Dr
    Inventory line (built from these charge rows) would then disagree by
    that same paisa or two. This mirrors allocate_charges()'s rounding rule
    exactly: every row but the last is rounded normally, and the last
    nonzero row absorbs whatever remainder is needed so
    sum(row["amount"] for row in result) always equals
    round(total_capitalized, ROUND_PRECISION) exactly.

    Returns a list of {"account", "amount", "description"} dicts for rows
    whose scaled amount is nonzero, in original charge order.
    """
    total_charges = flt(total_charges)
    total_capitalized = flt(total_capitalized)
    if total_charges <= 0 or total_capitalized <= 0:
        return []

    ratio = min(total_capitalized / total_charges, 1.0)

    nonzero_rows = [row for row in charges if flt(row.get("amount"))]
    if not nonzero_rows:
        return []

    target_total = round(total_capitalized, ROUND_PRECISION)
    last_idx = len(nonzero_rows) - 1
    running_total = 0.0
    result = []

    for i, row in enumerate(nonzero_rows):
        if i == last_idx:
            # Last row absorbs the rounding remainder so the sum is exact.
            amount = round(target_total - running_total, ROUND_PRECISION)
        else:
            amount = round(flt(row.get("amount")) * ratio, ROUND_PRECISION)
            running_total += amount
        if not amount:
            continue
        result.append({
            "account": row.get("account"),
            "amount": amount,
            "description": row.get("description"),
        })

    return result


# ─── GL map builder (Phase 4) ──────────────────────────────────────────────────

def build_landed_cost_gl_map(
    inventory_account: str,
    charges: list[dict],
    voucher_no: str,
    posting_date,
    company: str,
    posting_time=None,
) -> list[dict]:
    """Pure function — no DB access. Builds the balanced gl_map for
    general_ledger_entry.make_gl_entries(): one Dr Inventory Asset line for
    the combined total, one Cr line per charge row for its own amount into
    its own account. Debit always equals credit by construction (both derive
    from the same charges list), so this can never fail
    _validate_gl_balance — verified in tests/test_landed_cost_gl.py.
    """
    total_charges = sum(flt(c.get("amount")) for c in charges)
    if total_charges <= 0:
        return []

    gl_map = [{
        "account": inventory_account,
        "debit": total_charges,
        "credit": 0,
        "voucher_type": "Landed Cost Voucher",
        "voucher_no": voucher_no,
        "posting_date": posting_date,
        "posting_time": posting_time,
        "company": company,
        "remarks": f"Landed cost capitalized — {voucher_no}",
    }]
    for c in charges:
        amount = flt(c.get("amount"))
        if not amount:
            continue
        gl_map.append({
            "account": c.get("account"),
            "debit": 0,
            "credit": amount,
            "voucher_type": "Landed Cost Voucher",
            "voucher_no": voucher_no,
            "posting_date": posting_date,
            "posting_time": posting_time,
            "company": company,
            "remarks": c.get("description") or f"Reclassified into inventory — {voucher_no}",
        })
    return gl_map


# ─── Frontend preview endpoint ─────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["POST"])
def get_landed_cost_preview(source_doctype, source_name, charges, distribution_method="By Value"):
    """Live preview for the LCV form: pull the source document's item rows and
    show what each item's allocated charge / new valuation rate would be for
    the charge rows the user has drafted so far — before anything is saved.

    charges: JSON-encoded list of {"amount": ...} dicts (account/description
    are irrelevant to the allocation math and ignored here).
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    assert_can("Landed Cost Voucher", "read")

    if isinstance(charges, str):
        charges = json.loads(charges or "[]")

    items = get_source_items(source_doctype, source_name)
    allocated_items = allocate_charges(items, charges, distribution_method)

    return {
        "items": allocated_items,
        "total_purchase_amount": sum(flt(r["purchase_amount"]) for r in allocated_items),
        "total_charges": sum(flt(c.get("amount")) for c in charges),
        "distribution_method": distribution_method,
    }


# ─── Reporting visibility (Phase 8) ─────────────────────────────────────────────

@frappe.whitelist(allow_guest=False)
def get_landed_cost_breakdown(pairs):
    """Read-only helper powering the landed-cost visibility in Stock Valuation
    and BOM raw-material rows: for each item_code+warehouse pair, split the
    current Bin.valuation_rate into a base (purchase) rate and a landed-cost
    rate, so the UI can show "OMR 10,000 base + OMR 700 landed = OMR 10,700" instead of
    just a single opaque number.

    The landed portion is derived from the same active Stock Ledger Entries
    Phase 3/5 write (voucher_type="Landed Cost Voucher", is_cancelled=0) —
    summing stock_value_difference per bin gives exactly how much of
    Bin.stock_value is currently landed-cost, divided by actual_qty for a
    per-unit rate. No new source of truth is introduced; this only reads and
    re-presents what _create_valuation_sles / _update_bin already wrote.

    pairs: JSON-encoded list of {"item_code": ..., "warehouse": ...}.
    Returns a dict keyed "item_code::warehouse" -> {valuation_rate, base_rate,
    landed_rate, has_landed_cost}.
    """
    if isinstance(pairs, str):
        pairs = json.loads(pairs or "[]")
    if not pairs:
        return {}

    item_codes = list({p.get("item_code") for p in pairs if p.get("item_code")})
    warehouses = list({p.get("warehouse") for p in pairs if p.get("warehouse")})
    if not item_codes or not warehouses:
        return {}

    bins = frappe.get_all(
        "Bin",
        filters={"item_code": ["in", item_codes], "warehouse": ["in", warehouses]},
        fields=["item_code", "warehouse", "valuation_rate", "actual_qty"],
    )
    bin_map = {f"{b.item_code}::{b.warehouse}": b for b in bins}

    sle_rows = frappe.get_all(
        "Stock Ledger Entry",
        filters={
            "voucher_type": "Landed Cost Voucher",
            "is_cancelled": 0,
            "item_code": ["in", item_codes],
            "warehouse": ["in", warehouses],
        },
        fields=["item_code", "warehouse", "sum(stock_value_difference) as landed_value"],
        group_by="item_code, warehouse",
    )
    landed_map = {f"{r.item_code}::{r.warehouse}": flt(r.landed_value) for r in sle_rows}

    result = {}
    for p in pairs:
        item_code, warehouse = p.get("item_code"), p.get("warehouse")
        if not item_code or not warehouse:
            continue
        key = f"{item_code}::{warehouse}"
        b = bin_map.get(key)
        rate = flt(b.valuation_rate) if b else 0.0
        qty = flt(b.actual_qty) if b else 0.0
        landed_value = landed_map.get(key, 0.0)
        landed_rate = (landed_value / qty) if qty else 0.0
        result[key] = {
            "valuation_rate": rate,
            "landed_rate": landed_rate,
            "base_rate": rate - landed_rate,
            "has_landed_cost": bool(landed_value),
        }
    return result