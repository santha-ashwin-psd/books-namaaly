from __future__ import annotations
"""
Perpetual inventory GL helpers — account resolution and purchase debit split.

Model B (GR/IR):
  Goods receipt (Stock Entry Material Receipt from PR / PI update_stock):
      DR Inventory Asset  /  CR Stock Received But Not Billed (GRIR)
  Purchase Invoice (stock items):
      DR GRIR  /  CR Accounts Payable
  Purchase Invoice (non-stock items):
      DR Expense  /  CR Accounts Payable
  Goods issue (Stock Entry Material Issue from DN / SI update_stock):
      DR COGS  /  CR Inventory Asset   (unchanged; lives on Stock Entry)

Sales Invoice itself never posts COGS — that would double-count when
update_stock / Delivery Note already created a Material Issue.
"""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt

# Account types used for perpetual inventory
STOCK_ACCOUNT_TYPE = "Stock"
GRIR_ACCOUNT_TYPE = "Stock Received But Not Billed"
COGS_ACCOUNT_TYPE = "Cost of Goods Sold"
STOCK_ADJUSTMENT_TYPE = "Stock Adjustment"

# Reference doctypes whose Material Receipt should clear through GRIR
_PURCHASE_RECEIPT_REFS = frozenset({"Purchase Receipt", "Purchase Invoice"})


def get_inventory_account(company: str, item_code: str | None = None) -> str | None:
    """Resolve Inventory Asset: Item override → Books Company default → CoA Stock."""
    if item_code:
        item_acct = frappe.db.get_value("Item", item_code, "inventory_account")
        if item_acct:
            return item_acct

    company_default = _books_company_account(company, "default_inventory_account")
    if company_default:
        return company_default

    return (
        _acct_by_name(company, "Stock In Hand")
        or _acct_by_type(company, STOCK_ACCOUNT_TYPE)
    )


def get_grir_account(company: str) -> str | None:
    """Resolve Stock Received But Not Billed (GR/IR clearing liability)."""
    company_default = _books_company_account(company, "stock_received_not_billed")
    if company_default:
        return company_default

    return (
        _acct_by_name(company, "Stock Received")
        or _acct_by_type(company, GRIR_ACCOUNT_TYPE)
    )


def get_cogs_account(company: str) -> str | None:
    """Resolve Cost of Goods Sold: Books Company default → CoA COGS → Expense."""
    company_default = _books_company_account(company, "default_cogs_account")
    if company_default:
        return company_default

    return (
        _acct_by_name(company, "Cost of Goods Sold")
        or _acct_by_type(company, COGS_ACCOUNT_TYPE)
        or _acct_by_type(company, "Expense")
    )


def get_stock_adjustment_account(company: str) -> str | None:
    return (
        _acct_by_name(company, "Stock Adjustment")
        or _acct_by_type(company, STOCK_ADJUSTMENT_TYPE)
        or _acct_by_type(company, "Temporary")
    )


def is_purchase_stock_receipt(reference_doctype: str | None) -> bool:
    """True when a Material Receipt came from a purchase voucher (use GRIR contra)."""
    return bool(reference_doctype) and reference_doctype in _PURCHASE_RECEIPT_REFS


def has_confirmed_receipt(doc) -> bool:
    """
    True when this Purchase Invoice can safely clear GR/IR for stock items —
    i.e. a Material Receipt crediting GR/IR is guaranteed to exist:

      (a) doc.update_stock is checked — stock_link auto-creates the Material
          Receipt from THIS document in the same submit, or
      (b) doc.purchase_order is set and at least one Purchase Receipt has
          already been submitted against it.

    Without this guard, a stock item billed via a standalone Purchase Invoice
    (no "Update Stock", no Purchase Receipt — a very common flow for
    businesses that don't use the receipt step) would debit GR/IR with
    nothing ever crediting it: a permanent dangling liability, and the
    Inventory Asset would never be recorded at all. That is strictly worse
    than the pre-perpetual-inventory behavior (plain Expense), so such lines
    must fall back to Expense instead — see classify_purchase_item_amounts.
    """
    if flt(getattr(doc, "update_stock", 0)):
        return True
    purchase_order = getattr(doc, "purchase_order", None)
    if not purchase_order:
        return False
    return bool(frappe.db.exists(
        "Purchase Receipt",
        {"purchase_order": purchase_order, "docstatus": 1},
    ))


def classify_purchase_item_amounts(doc) -> dict:
    """
    Split purchase invoice net amounts by stock vs non-stock.

    A stock item only routes to Inventory/GR/IR when has_confirmed_receipt(doc)
    is True; otherwise it falls back to Expense (with the caller warning the
    user) rather than silently stranding a GR/IR debit with no matching credit.

    Returns:
        {
            "stock_total": float,          # sum of amounts capitalized via GR/IR
            "expense_total": float,        # sum for non-stock / unconfirmed-receipt items
            "stock_by_account": {inventory_account: amount, ...},
            "has_stock": bool,
            "has_expense": bool,
            "unconfirmed_stock_items": [item_code, ...],  # stock items expensed for lack of a receipt
        }
    """
    stock_total = 0.0
    expense_total = 0.0
    stock_by_account: dict[str, float] = defaultdict(float)
    unconfirmed_stock_items: list[str] = []

    item_codes = [
        getattr(row, "item_code", None)
        for row in (doc.items or [])
        if getattr(row, "item_code", None)
    ]
    stock_flags = {}
    inventory_accounts = {}
    if item_codes:
        for row in frappe.db.get_all(
            "Item",
            filters={"name": ["in", list(set(item_codes))]},
            fields=["name", "is_stock_item", "inventory_account"],
        ):
            stock_flags[row.name] = int(row.is_stock_item or 0)
            inventory_accounts[row.name] = row.inventory_account

    receipt_confirmed = has_confirmed_receipt(doc)

    for row in (doc.items or []):
        amount = flt(getattr(row, "amount", None))
        if not amount:
            amount = round(flt(getattr(row, "qty", 0)) * flt(getattr(row, "rate", 0)), 2)
        if not amount:
            continue

        item_code = getattr(row, "item_code", None)
        is_stock = bool(item_code and stock_flags.get(item_code))

        if is_stock and receipt_confirmed:
            stock_total += amount
            inv_acct = inventory_accounts.get(item_code) or get_inventory_account(
                doc.company, item_code
            )
            if inv_acct:
                stock_by_account[inv_acct] += amount
        else:
            expense_total += amount
            if is_stock:
                unconfirmed_stock_items.append(item_code)

    return {
        "stock_total": round(stock_total, 2),
        "expense_total": round(expense_total, 2),
        "stock_by_account": {k: round(v, 2) for k, v in stock_by_account.items()},
        "has_stock": stock_total > 0,
        "has_expense": expense_total > 0,
        "unconfirmed_stock_items": unconfirmed_stock_items,
    }


def build_purchase_invoice_debit_lines(
    doc,
    *,
    stock_total: float,
    expense_total: float,
    grir_account: str | None,
    expense_account: str | None,
) -> list[dict]:
    """
    Pure builder for the debit side of a purchase invoice (net cost only).

    Stock → GRIR; non-stock → Expense. Caller still adds AP credit, ITC, TDS,
    and round-off.
    """
    lines: list[dict] = []
    base = {
        "voucher_type": doc.doctype,
        "voucher_no": doc.name,
        "posting_date": doc.posting_date,
        "company": doc.company,
        "fiscal_year": getattr(doc, "fiscal_year", "") or "",
        "cost_center": getattr(doc, "cost_center", "") or "",
    }

    if flt(stock_total):
        if not grir_account:
            frappe.throw(_(
                "Cannot post stock purchase for {0}: no Stock Received But Not Billed "
                "(GR/IR) account found. Set it on Books Company or create an account "
                "with type 'Stock Received But Not Billed'."
            ).format(doc.company))
        lines.append({
            **base,
            "account": grir_account,
            "debit": flt(stock_total),
            "credit": 0,
            "remarks": f"Stock purchase (GR/IR clear) — Bill {doc.name}",
        })

    if flt(expense_total):
        if not expense_account:
            frappe.throw(_(
                "Please set the Expense Account on {0} — this bill includes "
                "non-stock items."
            ).format(doc.name or "this document"))
        lines.append({
            **base,
            "account": expense_account,
            "debit": flt(expense_total),
            "credit": 0,
            "remarks": f"Purchase cost (non-stock) — Bill {doc.name}",
        })

    return lines


def invoice_has_stock_items(doc) -> bool:
    """True if any line item is a stock item (for debit-note return_type)."""
    for row in (doc.items or []):
        item_code = getattr(row, "item_code", None)
        if item_code and frappe.db.get_value("Item", item_code, "is_stock_item"):
            return True
    return False


def classify_debit_note_item_amounts(doc) -> dict:
    """
    Split a Debit Note's (Purchase Invoice is_return=1) return amount by
    stock vs non-stock, PER LINE — mirroring classify_purchase_item_amounts
    instead of forcing the whole document into one bucket via a single
    return_type flag.

    Classification mirrors what the ORIGINAL bill actually capitalized: when
    linked via return_against, receipt-confirmation is evaluated against the
    ORIGINAL Purchase Invoice's update_stock/purchase_order (a debit note
    itself rarely carries those) — because that's what determined whether
    Inventory or Expense was actually debited at purchase time. A stock item
    only credits Inventory here if the original bill would have confirmed
    receipt; otherwise it credits Expense, so the reversal always matches
    what was actually posted, not just what the item master says today.

    Without a return_against link (standalone debit note), falls back to a
    per-item is_stock_item check only.

    Returns the same shape as classify_purchase_item_amounts (qty magnitudes
    — debit note items carry negative qty, but amount is always taken as
    abs()).
    """
    stock_total = 0.0
    expense_total = 0.0
    stock_by_account: dict[str, float] = defaultdict(float)

    receipt_confirmed = True
    return_against = getattr(doc, "return_against", None)
    if return_against and frappe.db.exists("Purchase Invoice", return_against):
        try:
            original = frappe.get_doc("Purchase Invoice", return_against)
            receipt_confirmed = has_confirmed_receipt(original)
        except Exception:
            receipt_confirmed = True

    item_codes = [
        getattr(row, "item_code", None)
        for row in (doc.items or [])
        if getattr(row, "item_code", None)
    ]
    stock_flags = {}
    inventory_accounts = {}
    if item_codes:
        for row in frappe.db.get_all(
            "Item",
            filters={"name": ["in", list(set(item_codes))]},
            fields=["name", "is_stock_item", "inventory_account"],
        ):
            stock_flags[row.name] = int(row.is_stock_item or 0)
            inventory_accounts[row.name] = row.inventory_account

    for row in (doc.items or []):
        amount = abs(flt(getattr(row, "amount", None)))
        if not amount:
            amount = abs(round(flt(getattr(row, "qty", 0)) * flt(getattr(row, "rate", 0)), 2))
        if not amount:
            continue

        item_code = getattr(row, "item_code", None)
        is_stock = bool(item_code and stock_flags.get(item_code))

        if is_stock and receipt_confirmed:
            stock_total += amount
            inv_acct = inventory_accounts.get(item_code) or get_inventory_account(
                doc.company, item_code
            )
            if inv_acct:
                stock_by_account[inv_acct] += amount
        else:
            expense_total += amount

    return {
        "stock_total": round(stock_total, 2),
        "expense_total": round(expense_total, 2),
        "stock_by_account": {k: round(v, 2) for k, v in stock_by_account.items()},
        "has_stock": stock_total > 0,
        "has_expense": expense_total > 0,
    }


def reconcile_stock_vs_gl(company: str) -> dict:
    """
    Compare Bin stock_value totals to Inventory Asset GL balance.

    Returns a summary dict suitable for a reconciliation report / desk page.
    Drift does not throw — callers decide how to surface it.
    """
    bin_value = flt(frappe.db.sql(
        """
        SELECT COALESCE(SUM(b.stock_value), 0)
        FROM `tabBin` b
        INNER JOIN `tabWarehouse` w ON w.name = b.warehouse
        WHERE w.company = %s
        """,
        company,
    )[0][0])

    inventory_account = get_inventory_account(company)
    gl_balance = 0.0
    if inventory_account:
        gl_balance = flt(frappe.db.sql(
            """
            SELECT COALESCE(SUM(debit) - SUM(credit), 0)
            FROM `tabGeneral Ledger Entry`
            WHERE account = %s AND company = %s AND IFNULL(is_cancelled, 0) = 0
            """,
            (inventory_account, company),
        )[0][0])

    return {
        "company": company,
        "inventory_account": inventory_account,
        "bin_stock_value": round(bin_value, 2),
        "gl_inventory_balance": round(gl_balance, 2),
        "difference": round(bin_value - gl_balance, 2),
        "is_reconciled": abs(bin_value - gl_balance) < 0.01,
    }


# ─── private ──────────────────────────────────────────────────────────────────

def _books_company_account(company: str, field: str) -> str | None:
    if not company or not frappe.db.exists("DocType", "Books Company"):
        return None
    try:
        return frappe.db.get_value("Books Company", company, field) or None
    except Exception:
        return None


def _acct_by_type(company: str, account_type: str) -> str | None:
    return frappe.db.get_value(
        "Account",
        {"account_type": account_type, "company": company, "is_group": 0},
        "name",
    ) or None


def _acct_by_name(company: str, account_name: str) -> str | None:
    return frappe.db.get_value(
        "Account",
        {"account_name": account_name, "company": company, "is_group": 0},
        "name",
    ) or None