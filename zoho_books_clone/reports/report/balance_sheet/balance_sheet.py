import frappe
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}
    return get_columns(), get_data(filters)


def get_columns():
    return [
        {"label":"Account",    "fieldname":"account","fieldtype":"Link","options":"Account","width":250},
        {"label":"Type",       "fieldname":"type",   "fieldtype":"Data","width":120},
        {"label":"Balance",    "fieldname":"balance","fieldtype":"Currency","width":150},
    ]


ASSET_TYPES     = ("Asset", "Cash", "Bank", "Receivable", "Stock")
# "Stock Received But Not Billed" (GR/IR clearing) is a credit-normal
# liability — goods received but not yet billed. Must be listed here, or it
# falls outside ASSET+LIABILITY+EQUITY and gets swept into "Net Profit" by
# the NOT IN %(bs_types)s query below (misclassifying a balance-sheet-
# permanent liability as a period P&L result).
LIABILITY_TYPES = ("Liability", "Payable", "Tax", "Stock Received But Not Billed")
EQUITY_TYPES    = ("Equity",)


def get_data(filters: dict) -> list[dict]:
    rows = frappe.db.sql("""
        SELECT g.account, a.account_type,
               SUM(g.debit) - SUM(g.credit) AS balance
        FROM `tabGeneral Ledger Entry` g
        JOIN `tabAccount` a ON a.name = g.account
        WHERE IFNULL(g.is_cancelled, 0) = 0
          AND g.posting_date <= %(as_of_date)s
          AND g.company = %(company)s
          AND a.account_type IN %(types)s
        GROUP BY g.account
        ORDER BY a.account_type, g.account
    """, {**filters, "types": ASSET_TYPES + LIABILITY_TYPES + EQUITY_TYPES}, as_dict=True)

    # Net Profit so far = every income-statement account (i.e. any account type
    # that isn't a balance-sheet permanent type) → rolled into equity. Covers
    # Income, Expense, Cost of Goods Sold, Stock Adjustment, Depreciation, etc.
    pnl = frappe.db.sql("""
        SELECT SUM(g.credit) - SUM(g.debit) AS net
        FROM `tabGeneral Ledger Entry` g
        JOIN `tabAccount` a ON a.name = g.account
        WHERE IFNULL(g.is_cancelled, 0) = 0
          AND g.posting_date <= %(as_of_date)s
          AND g.company = %(company)s
          AND a.account_type NOT IN %(bs_types)s
    """, {**filters, "bs_types": ASSET_TYPES + LIABILITY_TYPES + EQUITY_TYPES}, as_dict=True)
    net_profit = flt((pnl[0] or {}).get("net") or 0)

    # Balance signs: assets/expenses naturally have positive (debit-credit);
    # liabilities/equity/income are negative (debit-credit) — flip them so
    # they read as positive in the report.
    for r in rows:
        if r.account_type in LIABILITY_TYPES + EQUITY_TYPES:
            r.balance = flt(r.balance) * -1

    def section(label, types, extra=None):
        items = [r for r in rows if r.account_type in types]
        total = sum(flt(r.balance) for r in items)
        if extra:
            total += flt(extra.get("balance") or 0)
        out = [{"account": f"── {label} ──", "type": "", "balance": None}]
        out.extend({"account": r.account, "type": r.account_type, "balance": r.balance} for r in items)
        if extra:
            out.append(extra)
        out.append({"account": f"Total {label}", "type": "", "balance": total})
        return out, total

    assets,      ta = section("ASSETS",      ASSET_TYPES)
    liabilities, tl = section("LIABILITIES", LIABILITY_TYPES)
    equity,      te = section(
        "EQUITY", EQUITY_TYPES,
        extra={"account": "Net Profit (current period)", "type": "Equity", "balance": net_profit},
    )

    data = assets + [{}] + liabilities + [{}] + equity
    data.append({})
    data.append({"account": "Total Assets",                "type": "", "balance": ta})
    data.append({"account": "Total Liabilities + Equity",  "type": "", "balance": tl + te})
    return data
