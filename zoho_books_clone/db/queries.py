from __future__ import annotations
"""
Central query library for Zoho Books Clone.
All raw SQL lives here — controllers import from this module
instead of writing inline SQL.
"""
import frappe
from frappe.utils import flt, today


# ── General Ledger ────────────────────────────────────────────────────────────
@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_gl_entries(
    from_date: str,
    to_date: str,
    company: str,
    account: str | None = None,
    party_type: str | None = None,
    party: str | None = None,
    voucher_no: str | None = None,
) -> list[dict]:
    """Return GL entries for a date range with optional filters."""
    conditions = [
        "is_cancelled = 0",
        "posting_date BETWEEN %(from_date)s AND %(to_date)s",
        "company = %(company)s",
    ]
    params: dict = {"from_date": from_date, "to_date": to_date, "company": company}

    if account:
        conditions.append("account = %(account)s")
        params["account"] = account
    if party_type:
        conditions.append("party_type = %(party_type)s")
        params["party_type"] = party_type
    if party:
        conditions.append("party = %(party)s")
        params["party"] = party
    if voucher_no:
        conditions.append("voucher_no = %(voucher_no)s")
        params["voucher_no"] = voucher_no

    where = " AND ".join(conditions)
    return frappe.db.sql(f"""
        SELECT
            gl.posting_date, gl.account, gl.voucher_type, gl.voucher_no,
            gl.party_type, gl.party, gl.debit, gl.credit, gl.remarks,
            COALESCE(c.customer_name, s.supplier_name) AS party_name
        FROM `tabGeneral Ledger Entry` gl
        LEFT JOIN `tabCustomer` c ON gl.party_type = 'Customer' AND c.name = gl.party
        LEFT JOIN `tabSupplier` s ON gl.party_type = 'Supplier' AND s.name = gl.party
        WHERE {where}
        ORDER BY gl.posting_date, gl.creation
    """, params, as_dict=True)

@frappe.whitelist()
def get_account_balance(account: str, as_of_date: str | None = None) -> float:
    """Net balance (debit - credit) for an account, optionally up to a date."""
    params: dict = {"account": account}
    date_cond = ""
    if as_of_date:
        date_cond = "AND posting_date <= %(as_of_date)s"
        params["as_of_date"] = as_of_date

    result = frappe.db.sql(f"""
        SELECT COALESCE(SUM(debit) - SUM(credit), 0) AS balance
        FROM `tabGeneral Ledger Entry`
        WHERE account = %(account)s AND is_cancelled = 0 {date_cond}
    """, params, as_dict=True)
    return flt(result[0].balance) if result else 0.0

@frappe.whitelist()
def get_account_balances_bulk(
    accounts: list[str], as_of_date: str | None = None
) -> dict[str, float]:
    """Return {account_name: balance} for a list of accounts (single query)."""
    if not accounts:
        return {}
    placeholders = ", ".join(["%s"] * len(accounts))
    date_cond = f"AND posting_date <= '{as_of_date}'" if as_of_date else ""
    rows = frappe.db.sql(f"""
        SELECT account, COALESCE(SUM(debit) - SUM(credit), 0) AS balance
        FROM `tabGeneral Ledger Entry`
        WHERE account IN ({placeholders}) AND is_cancelled = 0 {date_cond}
        GROUP BY account
    """, accounts, as_dict=True)
    return {r.account: flt(r.balance) for r in rows}


# ── Invoices ──────────────────────────────────────────────────────────────────

def get_outstanding_invoices(
    party_type: str,
    party: str,
    company: str | None = None,
) -> list[dict]:
    """Unpaid invoices for a customer or supplier."""
    dt = "Sales Invoice" if party_type == "Customer" else "Purchase Invoice"
    party_field = "customer" if dt == "Sales Invoice" else "supplier"
    filters: dict = {party_field: party, "docstatus": 1, "outstanding_amount": [">", 0]}
    if company:
        filters["company"] = company
    return frappe.get_all(
        dt,
        filters=filters,
        fields=["name", "posting_date", "due_date", "grand_total", "outstanding_amount", "currency"],
        order_by="due_date asc",
    )


def get_invoice_summary(company: str, from_date: str, to_date: str) -> dict:
    """Dashboard KPIs: total invoiced, total collected, outstanding."""
    row = frappe.db.sql("""
        SELECT
            COALESCE(SUM(grand_total),       0) AS total_invoiced,
            COALESCE(SUM(grand_total - outstanding_amount), 0) AS total_collected,
            COALESCE(SUM(outstanding_amount),0) AS total_outstanding
        FROM `tabSales Invoice`
        WHERE company = %(company)s
          AND docstatus = 1
          AND posting_date BETWEEN %(from_date)s AND %(to_date)s
    """, {"company": company, "from_date": from_date, "to_date": to_date}, as_dict=True)
    return row[0] if row else {}


def get_overdue_invoices(company: str) -> list[dict]:
    """All sales invoices past their due date with a balance."""
    return frappe.db.sql("""
        SELECT name, customer, customer_name, due_date,
               outstanding_amount, grand_total, currency
        FROM `tabSales Invoice`
        WHERE company = %(company)s
          AND docstatus = 1
          AND outstanding_amount > 0
          AND due_date < %(today)s
        ORDER BY due_date ASC
    """, {"company": company, "today": today()}, as_dict=True)


def get_top_customers(company: str, from_date: str, to_date: str, limit: int = 10) -> list[dict]:
    """Top customers by revenue in a period."""
    return frappe.db.sql("""
        SELECT customer, customer_name,
               COUNT(*) AS invoice_count,
               SUM(grand_total) AS total_revenue
        FROM `tabSales Invoice`
        WHERE company = %(company)s
          AND docstatus = 1
          AND posting_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY customer
        ORDER BY total_revenue DESC
        LIMIT %(limit)s
    """, {"company": company, "from_date": from_date, "to_date": to_date, "limit": limit}, as_dict=True)


# ── Payments ──────────────────────────────────────────────────────────────────

def get_payments_for_party(party_type: str, party: str, company: str) -> list[dict]:
    """All submitted payments for a party."""
    return frappe.get_all(
        "Payment Entry",
        filters={"party_type": party_type, "party": party, "company": company, "docstatus": 1},
        fields=["name", "payment_date", "payment_type", "paid_amount", "mode_of_payment"],
        order_by="payment_date desc",
    )


def get_payment_summary(company: str, from_date: str, to_date: str) -> dict:
    """Total received vs paid in a period."""
    row = frappe.db.sql("""
        SELECT
            COALESCE(SUM(CASE WHEN payment_type='Receive' THEN paid_amount ELSE 0 END),0) AS total_received,
            COALESCE(SUM(CASE WHEN payment_type='Pay'     THEN paid_amount ELSE 0 END),0) AS total_paid
        FROM `tabPayment Entry`
        WHERE company = %(company)s
          AND docstatus = 1
          AND payment_date BETWEEN %(from_date)s AND %(to_date)s
    """, {"company": company, "from_date": from_date, "to_date": to_date}, as_dict=True)
    return row[0] if row else {}


# ── Banking ───────────────────────────────────────────────────────────────────

def get_unreconciled_transactions(bank_account: str) -> list[dict]:
    """Bank transactions not yet matched to a payment entry."""
    return frappe.get_all(
        "Bank Transaction",
        filters={"bank_account": bank_account, "status": "Unreconciled", "docstatus": 1},
        fields=["name", "date", "description", "debit", "credit", "balance", "reference_number"],
        order_by="date asc",
    )


def get_bank_balance(bank_account: str) -> float:
    """Latest running balance from bank transactions."""
    result = frappe.db.sql("""
        SELECT balance FROM `tabBank Transaction`
        WHERE bank_account = %s AND docstatus = 1
        ORDER BY date DESC, creation DESC
        LIMIT 1
    """, bank_account, as_dict=True)
    return flt(result[0].balance) if result else 0.0


# ── Reports ───────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_profit_and_loss(company: str, from_date: str, to_date: str) -> dict:
    """
    Return income, expense (including COGS and stock adjustments), and net profit.

    Account types included:
      Income             → revenue
      Expense            → operating expenses
      Cost of Goods Sold → COGS posted by Stock Entry on Material Issue
      Stock Adjustment   → contra credited when stock is received; offsets the
                           purchase expense so cost hits the P&L once (as COGS)

    Net Profit = Income − (Expense + COGS + Stock Adjustment) — this matches the
    retained-earnings roll-up in get_balance_sheet_totals, so both reports agree.
    """
    rows = frappe.db.sql("""
        SELECT a.account_type,
               COALESCE(SUM(g.credit) - SUM(g.debit), 0) AS amount
        FROM `tabGeneral Ledger Entry` g
        JOIN `tabAccount` a ON a.name = g.account
        WHERE g.company      = %(company)s
          AND g.is_cancelled  = 0
          AND g.posting_date BETWEEN %(from_date)s AND %(to_date)s
          AND a.account_type IN (
                "Income",
                "Expense",
                "Cost of Goods Sold",   -- COGS from inventory GL posting
                "Stock Adjustment"      -- contra for stock receipts
              )
        GROUP BY a.account_type
    """, {"company": company, "from_date": from_date, "to_date": to_date}, as_dict=True)

    totals = {r.account_type: flt(r.amount) for r in rows}
    income  = totals.get("Income", 0.0)
    # Debit-normal accounts: credit-debit gives a negative number → negate it.
    cogs      = -totals.get("Cost of Goods Sold", 0.0)
    expense   = -totals.get("Expense", 0.0)
    # Stock Adjustment usually carries a credit balance (stock received), which
    # comes out negative here — i.e. it reduces total expense.
    stock_adj = -totals.get("Stock Adjustment", 0.0)

    gross_profit = income - cogs
    net_profit   = gross_profit - expense - stock_adj

    return {
        "total_income":     income,
        "cogs":             cogs,
        "gross_profit":     gross_profit,
        "total_expense":    expense,
        "stock_adjustment": stock_adj,
        "net_profit":       net_profit,
    }


@frappe.whitelist()
def get_balance_sheet_totals(company: str, as_of_date: str) -> dict:
    """
    Asset, liability, equity totals as of a date.

    All account types are fetched; classification:
      Debit-normal assets  → Asset, Cash, Bank, Receivable, Stock
      Credit-normal liab.  → Liability, Payable
      Tax                  → net positive = ITC asset; net negative = GST liability
      Equity               → Equity (credit-normal)
    """
    rows = frappe.db.sql("""
        SELECT a.account_type,
               COALESCE(SUM(g.debit) - SUM(g.credit), 0) AS balance
        FROM `tabGeneral Ledger Entry` g
        JOIN `tabAccount` a ON a.name = g.account
        WHERE g.company     = %(company)s
          AND g.is_cancelled = 0
          AND g.posting_date <= %(as_of_date)s
        GROUP BY a.account_type
    """, {"company": company, "as_of_date": as_of_date}, as_dict=True)

    t = {r.account_type: flt(r.balance) for r in rows}

    # Debit-normal: positive balance = asset
    ASSET_TYPES = ("Asset", "Cash", "Bank", "Receivable", "Stock")
    raw_assets = sum(t.get(tp, 0.0) for tp in ASSET_TYPES)

    # Tax accounts: ITC accounts carry debit balance (asset);
    # GST Payable accounts carry credit balance (liability).
    # The net (debit-credit) tells us which side dominates.
    tax_net = t.get("Tax", 0.0)
    itc_asset    = max(tax_net, 0.0)   # positive → ITC on asset side
    gst_liability = abs(min(tax_net, 0.0))  # negative → GST payable

    # Credit-normal: debit-credit is negative for balances owed → negate (not
    # abs) so a net-debit balance (e.g. a supplier advance) reduces liabilities
    # instead of inflating them, keeping Assets = Liabilities + Equity intact.
    # "Stock Received But Not Billed" (GR/IR clearing) is credit-normal too —
    # goods received but not yet billed sit here as a liability until the
    # Purchase Invoice clears it. Without this it would fall through the
    # BS_TYPES catch-all below and get misclassified as a P&L result folded
    # into retained earnings instead of staying a period-end liability.
    payables        = -t.get("Payable", 0.0)
    other_liab      = -t.get("Liability", 0.0)
    grir_liability  = -t.get("Stock Received But Not Billed", 0.0)
    raw_liabilities = payables + other_liab + grir_liability

    inventory_value = t.get("Stock", 0.0)
    cash_and_bank   = t.get("Cash", 0.0) + t.get("Bank", 0.0)
    receivables     = t.get("Receivable", 0.0)
    other_assets    = t.get("Asset", 0.0)

    # Equity = capital accounts + current-period retained earnings.
    # Everything that isn't a balance-sheet-permanent account type is an income
    # statement (P&L) account whose net result belongs in retained earnings.
    # Because the trial balance nets to zero, this makes
    #   total_assets == total_liabilities + total_equity.
    BS_TYPES = {"Asset", "Cash", "Bank", "Receivable", "Stock",
                "Liability", "Payable", "Tax", "Equity",
                "Stock Received But Not Billed"}
    equity_capital    = -flt(t.get("Equity", 0.0))                 # credit-normal → positive
    retained_earnings = -sum(flt(bal) for atype, bal in t.items() if atype not in BS_TYPES)
    total_equity      = equity_capital + retained_earnings

    return {
        "total_assets":      raw_assets + itc_asset,
        "cash_and_bank":     cash_and_bank,
        "receivables":       receivables,
        "inventory_value":   inventory_value,
        "itc_receivable":    itc_asset,
        "other_assets":      other_assets,
        "total_liabilities": raw_liabilities + gst_liability,
        "payables":          payables,
        "gst_liability":     gst_liability,
        "other_liabilities": other_liab,
        "stock_received_not_billed": grir_liability,
        "total_equity":      total_equity,
        "equity_capital":    equity_capital,
        "retained_earnings": retained_earnings,
    }


@frappe.whitelist()
def get_cash_flow(company: str, from_date: str, to_date: str) -> dict:
    """
    Indirect-method cash-flow statement that reconciles to the real movement in
    Cash & Bank: Operating + Investing + Financing = Net change in cash.

    Each activity line is the *negative* of the period movement (debit − credit)
    in its accounts — a rise in an asset uses cash, while profit or a rise in a
    liability/equity provides cash. Because a period's GL nets to zero, the three
    activities always sum to the actual change in cash.

      Operating  = P&L (Income, Expense, COGS, Stock Adjustment, Depreciation…)
                   + working capital (Receivable, Payable, Tax, Stock/Inventory)
      Investing  = fixed & other Asset accounts
      Financing  = Equity & Liability (capital / borrowings)
    """
    rows = frappe.db.sql("""
        SELECT a.account_type,
               COALESCE(SUM(g.debit) - SUM(g.credit), 0) AS net
        FROM `tabGeneral Ledger Entry` g
        JOIN `tabAccount` a ON a.name = g.account
        WHERE g.company      = %(company)s
          AND g.is_cancelled  = 0
          AND g.posting_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY a.account_type
    """, {"company": company, "from_date": from_date, "to_date": to_date}, as_dict=True)

    by_type = {r.account_type: flt(r.net) for r in rows}

    CASH      = {"Cash", "Bank"}
    INVESTING = {"Asset"}
    FINANCING = {"Equity", "Liability"}

    # Source of cash = decrease in a non-cash account (debit−credit negative),
    # hence the leading minus. Everything not cash/investing/financing is
    # operating (P&L + working capital) so nothing is dropped and it reconciles.
    investing = -sum(v for k, v in by_type.items() if k in INVESTING)
    financing = -sum(v for k, v in by_type.items() if k in FINANCING)
    operating = -sum(v for k, v in by_type.items() if k not in (CASH | INVESTING | FINANCING))
    net_change = operating + investing + financing

    opening_cash = flt(frappe.db.sql("""
        SELECT COALESCE(SUM(g.debit) - SUM(g.credit), 0)
        FROM `tabGeneral Ledger Entry` g
        JOIN `tabAccount` a ON a.name = g.account
        WHERE g.company = %(company)s AND IFNULL(g.is_cancelled, 0) = 0
          AND a.account_type IN ('Cash', 'Bank')
          AND g.posting_date < %(from_date)s
    """, {"company": company, "from_date": from_date})[0][0])

    return {
        "operating":    operating,
        "investing":    investing,
        "financing":    financing,
        "net_change":   net_change,
        "opening_cash": opening_cash,
        "closing_cash": opening_cash + net_change,
    }


# ── Tax ───────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_gst_summary(company: str, from_date: str, to_date: str) -> list[dict]:
    """GST collected by tax type (CGST, SGST, IGST) for a period."""
    return frappe.db.sql("""
        SELECT
            COALESCE(NULLIF(t.tax_type, ''), t.description) AS tax_type,
            COUNT(DISTINCT t.parent)                         AS invoice_count,
            SUM(t.tax_amount)                                AS total_tax
        FROM `tabTax Line` t
        JOIN `tabSales Invoice` si ON si.name = t.parent AND t.parenttype = 'Sales Invoice'
        WHERE si.company        = %(company)s
          AND si.docstatus      = 1
          AND si.posting_date   BETWEEN %(from_date)s AND %(to_date)s
          AND t.tax_amount      != 0
        GROUP BY tax_type
        ORDER BY tax_type
    """, {"company": company, "from_date": from_date, "to_date": to_date}, as_dict=True)


@frappe.whitelist()
def get_item_wise_sales(company: str, from_date: str, to_date: str) -> list[dict]:
    """Item-wise sales summary: qty sold, revenue, and avg rate per item for a period."""
    return frappe.db.sql("""
        SELECT
            sii.item_code                    AS item_code,
            sii.item_name                    AS item_name,
            sii.uom                          AS uom,
            COUNT(DISTINCT sii.parent)       AS invoice_count,
            SUM(sii.qty)                     AS qty_sold,
            SUM(sii.amount)                  AS total_amount,
            SUM(sii.discount_amount)         AS total_discount,
            CASE WHEN SUM(sii.qty) != 0
                 THEN SUM(sii.amount) / SUM(sii.qty)
                 ELSE 0 END                  AS avg_rate
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON si.name = sii.parent AND sii.parenttype = 'Sales Invoice'
        WHERE si.company      = %(company)s
          AND si.docstatus    = 1
          AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY sii.item_code, sii.item_name, sii.uom
        ORDER BY total_amount DESC
    """, {"company": company, "from_date": from_date, "to_date": to_date}, as_dict=True)


@frappe.whitelist()
def get_customer_wise_sales(company: str, from_date: str, to_date: str) -> list[dict]:
    """Customer-wise sales summary: invoice count, revenue, discount and outstanding per customer for a period."""
    return frappe.db.sql("""
        SELECT
            si.customer                        AS customer,
            si.customer_name                   AS customer_name,
            COUNT(si.name)                     AS invoice_count,
            SUM(si.net_total)                  AS net_total,
            SUM(si.additional_discount_amount) AS total_discount,
            SUM(si.total_tax)                  AS total_tax,
            SUM(si.grand_total)                AS total_amount,
            SUM(si.outstanding_amount)         AS outstanding_amount,
            CASE WHEN COUNT(si.name) != 0
                 THEN SUM(si.grand_total) / COUNT(si.name)
                 ELSE 0 END                    AS avg_invoice_value
        FROM `tabSales Invoice` si
        WHERE si.company      = %(company)s
          AND si.docstatus    = 1
          AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY si.customer, si.customer_name
        ORDER BY total_amount DESC
    """, {"company": company, "from_date": from_date, "to_date": to_date}, as_dict=True)


@frappe.whitelist()
def get_profit_wise_report(company: str, from_date: str, to_date: str) -> list[dict]:
    """
    Item-wise gross profit for a period: revenue vs. estimated cost and margin %.

    Cost basis: current average valuation rate per item, computed from the
    `Bin` table (SUM(stock_value) / SUM(actual_qty) across sellable
    warehouses), falling back to the item's `standard_buying_rate` when
    there's no stock/Bin data (e.g. service items or items with no remaining
    stock history). This is a current-cost estimate rather than a
    historical/FIFO cost at the time of each sale, since Sales Invoice Item
    does not itself store a cost field.

    WIP warehouses are deliberately excluded from the average: they hold
    in-process stock (raw materials staged for manufacture, partially
    finished goods) rather than sellable inventory, and blending their
    valuation in skews the cost of goods that were actually sold.
    """
    wip_warehouses = set(
        frappe.get_all(
            "Work Order",
            filters={"wip_warehouse": ["is", "set"]},
            pluck="wip_warehouse",
        )
    )
    default_wip = frappe.db.get_single_value("Manufacturing Settings", "default_wip_warehouse")
    if default_wip:
        wip_warehouses.add(default_wip)

    wip_cond = ""
    params = {"company": company, "from_date": from_date, "to_date": to_date}
    if wip_warehouses:
        wip_cond = "AND b.warehouse NOT IN %(wip_warehouses)s"
        params["wip_warehouses"] = tuple(wip_warehouses)

    return frappe.db.sql(f"""
        SELECT
            sii.item_code                        AS item_code,
            sii.item_name                        AS item_name,
            sii.uom                              AS uom,
            COUNT(DISTINCT sii.parent)           AS invoice_count,
            SUM(sii.qty)                         AS qty_sold,
            SUM(sii.amount)                      AS revenue,
            COALESCE(ic.avg_valuation_rate, i.standard_buying_rate, 0) AS cost_rate,
            SUM(sii.qty) * COALESCE(ic.avg_valuation_rate, i.standard_buying_rate, 0) AS total_cost,
            SUM(sii.amount) - SUM(sii.qty) * COALESCE(ic.avg_valuation_rate, i.standard_buying_rate, 0) AS profit,
            CASE WHEN SUM(sii.amount) != 0
                 THEN (SUM(sii.amount) - SUM(sii.qty) * COALESCE(ic.avg_valuation_rate, i.standard_buying_rate, 0))
                      / SUM(sii.amount) * 100
                 ELSE 0 END                      AS margin_pct
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON si.name = sii.parent AND sii.parenttype = 'Sales Invoice'
        JOIN `tabItem` i ON i.name = sii.item_code
        LEFT JOIN (
            SELECT b.item_code,
                   CASE WHEN SUM(b.actual_qty) > 0
                        THEN SUM(b.stock_value) / SUM(b.actual_qty)
                        ELSE 0 END AS avg_valuation_rate
            FROM `tabBin` b
            WHERE 1 = 1 {wip_cond}
            GROUP BY b.item_code
        ) ic ON ic.item_code = sii.item_code
        WHERE si.company      = %(company)s
          AND si.docstatus    = 1
          AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY sii.item_code, sii.item_name, sii.uom, ic.avg_valuation_rate, i.standard_buying_rate
        ORDER BY profit DESC
    """, params, as_dict=True)


# ── Inventory ─────────────────────────────────────────────────────────────────
def get_stock_movement_summary(
    company: str,
    from_date: str,
    to_date: str,
    warehouse: str | None = None,
) -> list[dict]:
    """Total receipts and issues per item in a period."""
    wh_cond = "AND sle.warehouse = %(warehouse)s" if warehouse else ""
    params = {"company": company, "from_date": from_date, "to_date": to_date}
    if warehouse:
        params["warehouse"] = warehouse

    return frappe.db.sql(f"""
        SELECT
            sle.item_code,
            i.item_name,
            sle.warehouse,
            COALESCE(SUM(CASE WHEN sle.actual_qty > 0 THEN sle.actual_qty  ELSE 0 END), 0) AS total_in,
            COALESCE(SUM(CASE WHEN sle.actual_qty < 0 THEN -sle.actual_qty ELSE 0 END), 0) AS total_out,
            COALESCE(SUM(sle.actual_qty), 0) AS net_qty,
            COALESCE(SUM(sle.stock_value_difference), 0) AS net_value
        FROM `tabStock Ledger Entry` sle
        JOIN `tabItem` i ON i.name = sle.item_code
        WHERE sle.is_cancelled = 0
          AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s
          {wh_cond}
        GROUP BY sle.item_code, sle.warehouse
        ORDER BY ABS(SUM(sle.stock_value_difference)) DESC
    """, params, as_dict=True)


def get_slow_moving_items(
    company: str,
    days: int = 90,
    warehouse: str | None = None,
) -> list[dict]:
    """Items with no stock movement in the last N days that still have stock."""
    wh_cond      = "AND b.warehouse = %(warehouse)s" if warehouse else ""
    company_cond = "AND b.company   = %(company)s"   if company   else ""
    params: dict = {"days": days}
    if warehouse:
        params["warehouse"] = warehouse
    if company:
        params["company"] = company

    return frappe.db.sql(f"""
        SELECT
            b.item_code,
            i.item_name,
            b.warehouse,
            b.actual_qty,
            b.stock_value,
            b.valuation_rate,
            MAX(sle.posting_date) AS last_movement_date,
            DATEDIFF(CURDATE(), MAX(sle.posting_date)) AS days_since_movement
        FROM `tabBin` b
        JOIN `tabItem` i ON i.name = b.item_code
        LEFT JOIN `tabStock Ledger Entry` sle
            ON sle.item_code = b.item_code
            AND sle.warehouse = b.warehouse
            AND sle.is_cancelled = 0
        WHERE b.actual_qty > 0
          {wh_cond}
          {company_cond}
        GROUP BY b.item_code, b.warehouse
        HAVING last_movement_date IS NULL
            OR DATEDIFF(CURDATE(), last_movement_date) > %(days)s
        ORDER BY days_since_movement DESC
    """, params, as_dict=True)


def get_stock_ageing(
    warehouse: str | None = None,
    as_of_date: str | None = None,
) -> list[dict]:
    """FIFO-based stock ageing — how old is the stock on hand."""
    from frappe.utils import today as frappe_today
    date = as_of_date or frappe_today()
    wh_cond = "AND sle.warehouse = %(warehouse)s" if warehouse else ""
    params = {"date": date}
    if warehouse:
        params["warehouse"] = warehouse

    return frappe.db.sql(f"""
        SELECT
            sle.item_code,
            i.item_name,
            sle.warehouse,
            sle.posting_date AS receipt_date,
            sle.actual_qty   AS receipt_qty,
            sle.incoming_rate AS rate,
            DATEDIFF(%(date)s, sle.posting_date) AS age_days,
            sle.actual_qty * sle.incoming_rate    AS receipt_value
        FROM `tabStock Ledger Entry` sle
        JOIN `tabItem` i ON i.name = sle.item_code
        WHERE sle.actual_qty > 0
          AND sle.posting_date <= %(date)s
          AND sle.is_cancelled = 0
          {wh_cond}
        ORDER BY sle.item_code, sle.posting_date ASC
    """, params, as_dict=True)


def get_item_valuation_history(
    item_code: str,
    warehouse: str,
    from_date: str,
    to_date: str,
) -> list[dict]:
    """Valuation rate history for an item+warehouse over a period."""
    return frappe.db.sql("""
        SELECT
            posting_date,
            voucher_type,
            voucher_no,
            actual_qty,
            qty_after_transaction,
            valuation_rate,
            stock_value
        FROM `tabStock Ledger Entry`
        WHERE item_code  = %(item_code)s
          AND warehouse  = %(warehouse)s
          AND is_cancelled = 0
          AND posting_date BETWEEN %(from_date)s AND %(to_date)s
        ORDER BY posting_date, creation
    """, {"item_code": item_code, "warehouse": warehouse,
          "from_date": from_date, "to_date": to_date}, as_dict=True)


# ── Trial Balance ─────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_trial_balance(company: str, from_date: str, to_date: str) -> list[dict]:
    """Account-level trial balance: opening + period debits/credits + closing."""
    rows = frappe.db.sql("""
        SELECT
            gle.account,
            a.account_type,
            SUM(CASE WHEN gle.posting_date < %(from_date)s THEN gle.debit - gle.credit ELSE 0 END) AS opening,
            SUM(CASE WHEN gle.posting_date BETWEEN %(from_date)s AND %(to_date)s THEN gle.debit ELSE 0 END) AS debit,
            SUM(CASE WHEN gle.posting_date BETWEEN %(from_date)s AND %(to_date)s THEN gle.credit ELSE 0 END) AS credit
        FROM `tabGeneral Ledger Entry` gle
        JOIN `tabAccount` a ON a.name = gle.account
        WHERE gle.company      = %(company)s
          AND gle.is_cancelled  = 0
          AND gle.posting_date <= %(to_date)s
        GROUP BY gle.account, a.account_type
        ORDER BY gle.account
    """, {"company": company, "from_date": from_date, "to_date": to_date}, as_dict=True)

    for r in rows:
        r["closing"] = flt(r.get("opening")) + flt(r.get("debit")) - flt(r.get("credit"))

    return rows


# ── Inventory ↔ GL Reconciliation ────────────────────────────────────────────

@frappe.whitelist()
def get_inventory_reconciliation(company: str) -> dict:
    """
    Perpetual inventory audit check: does the Stock Ledger's operational view
    of stock value (Bin.stock_value, moving-average) agree with the GL's
    financial view (Inventory Asset account balance)?

    These are two independently-maintained ledgers (Stock Ledger Entry / Bin
    vs General Ledger Entry) that only stay in sync because every Stock Entry
    posts both together. This report is the tripwire that catches drift —
    e.g. a manual Journal Entry into the Inventory account, a GL posting
    failure that Stock Entry logged and swallowed (see StockEntry._post_gl_entries
    error handling), or an account misconfiguration — immediately instead of
    at year-end audit.

    Grouped by resolved inventory account (Item override → Books Company
    default → CoA "Stock" type) since a company can have more than one
    Inventory Asset ledger. Also reports the Stock Received But Not Billed
    (GR/IR) balance for context — a nonzero GRIR is normal (goods received,
    bill not yet booked) and is NOT counted as drift.
    """
    from zoho_books_clone.accounts.inventory_gl import get_grir_account, get_inventory_account

    default_account = get_inventory_account(company)

    items = frappe.db.sql("""
        SELECT b.item_code, i.item_name, b.warehouse, b.actual_qty,
               b.valuation_rate, b.stock_value, i.inventory_account
        FROM `tabBin` b
        INNER JOIN `tabWarehouse` w ON w.name = b.warehouse
        INNER JOIN `tabItem` i ON i.name = b.item_code
        WHERE w.company = %(company)s
          AND i.is_stock_item = 1
          AND b.actual_qty != 0
        ORDER BY b.item_code, b.warehouse
    """, {"company": company}, as_dict=True)

    for row in items:
        row["resolved_account"] = row.inventory_account or default_account

    accounts = sorted({
        row["resolved_account"] for row in items if row["resolved_account"]
    } | ({default_account} if default_account else set()))

    account_summary = []
    total_bin_value = 0.0
    total_gl_balance = 0.0
    for account in accounts:
        bin_value = sum(flt(row.stock_value) for row in items if row["resolved_account"] == account)
        gl_balance = flt(frappe.db.sql("""
            SELECT COALESCE(SUM(debit) - SUM(credit), 0)
            FROM `tabGeneral Ledger Entry`
            WHERE account = %(account)s AND company = %(company)s
              AND IFNULL(is_cancelled, 0) = 0
        """, {"account": account, "company": company})[0][0])
        difference = round(bin_value - gl_balance, 2)
        account_summary.append({
            "account": account,
            "bin_stock_value": round(bin_value, 2),
            "gl_balance": round(gl_balance, 2),
            "difference": difference,
            "is_reconciled": abs(difference) < 0.01,
        })
        total_bin_value += bin_value
        total_gl_balance += gl_balance

    grir_account = get_grir_account(company)
    grir_balance = 0.0
    if grir_account:
        grir_balance = flt(frappe.db.sql("""
            SELECT COALESCE(SUM(credit) - SUM(debit), 0)
            FROM `tabGeneral Ledger Entry`
            WHERE account = %(account)s AND company = %(company)s
              AND IFNULL(is_cancelled, 0) = 0
        """, {"account": grir_account, "company": company})[0][0])

    return {
        "accounts": account_summary,
        "items": items,
        "total_bin_value": round(total_bin_value, 2),
        "total_gl_balance": round(total_gl_balance, 2),
        "total_difference": round(total_bin_value - total_gl_balance, 2),
        "is_reconciled": abs(total_bin_value - total_gl_balance) < 0.01,
        "grir_account": grir_account,
        "grir_balance": round(grir_balance, 2),
    }


# ── AR Aging ──────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_ar_aging(company: str, as_of_date: str) -> list[dict]:
    """Accounts Receivable aging by customer with standard buckets."""
    rows = frappe.db.sql("""
        SELECT
            si.customer,
            si.customer_name,
            si.name             AS invoice,
            si.posting_date,
            si.due_date,
            si.outstanding_amount,
            DATEDIFF(%(as_of_date)s, si.due_date) AS overdue_days
        FROM `tabSales Invoice` si
        WHERE si.company      = %(company)s
          AND si.docstatus    = 1
          AND si.outstanding_amount > 0
        ORDER BY si.customer, si.posting_date
    """, {"company": company, "as_of_date": as_of_date}, as_dict=True)

    # Bucket into aging groups per customer
    buckets = {}
    for r in rows:
        cust = r["customer"]
        if cust not in buckets:
            buckets[cust] = {"customer": cust, "customer_name": r.get("customer_name", cust),
                             "current": 0, "days_1_30": 0, "days_31_60": 0,
                             "days_61_90": 0, "days_90_plus": 0, "total": 0}
        b = buckets[cust]
        amt = flt(r["outstanding_amount"])
        days = r["overdue_days"] or 0
        if days <= 0:
            b["current"] += amt
        elif days <= 30:
            b["days_1_30"] += amt
        elif days <= 60:
            b["days_31_60"] += amt
        elif days <= 90:
            b["days_61_90"] += amt
        else:
            b["days_90_plus"] += amt
        b["total"] += amt

    return list(buckets.values())


# ── AP Aging ──────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_ap_aging(company: str, as_of_date: str) -> list[dict]:
    """Accounts Payable aging by supplier with standard buckets."""
    rows = frappe.db.sql("""
        SELECT
            pi.supplier,
            pi.supplier_name,
            pi.name             AS invoice,
            pi.posting_date,
            pi.due_date,
            pi.outstanding_amount,
            DATEDIFF(%(as_of_date)s, pi.due_date) AS overdue_days
        FROM `tabPurchase Invoice` pi
        WHERE pi.company      = %(company)s
          AND pi.docstatus    = 1
          AND pi.outstanding_amount > 0
        ORDER BY pi.supplier, pi.posting_date
    """, {"company": company, "as_of_date": as_of_date}, as_dict=True)

    buckets = {}
    for r in rows:
        sup = r["supplier"]
        if sup not in buckets:
            buckets[sup] = {"supplier": sup, "supplier_name": r.get("supplier_name", sup),
                            "current": 0, "days_1_30": 0, "days_31_60": 0,
                            "days_61_90": 0, "days_90_plus": 0, "total": 0}
        b = buckets[sup]
        amt = flt(r["outstanding_amount"])
        days = r["overdue_days"] or 0
        if days <= 0:
            b["current"] += amt
        elif days <= 30:
            b["days_1_30"] += amt
        elif days <= 60:
            b["days_31_60"] += amt
        elif days <= 90:
            b["days_61_90"] += amt
        else:
            b["days_90_plus"] += amt
        b["total"] += amt

    return list(buckets.values())


# ── Customer Statement ────────────────────────────────────────────────────────

@frappe.whitelist()
def get_customer_statement(customer: str, company: str = "") -> dict:
    """Outstanding invoices + payment history for a customer."""
    if not company:
        from zoho_books_clone.api.session import _get_company
        company = _get_company(frappe.session.user) or ""
    if not company:
        frappe.throw("No default company configured. Please set one in Books Settings.")
    invoices = frappe.db.sql("""
        SELECT name, posting_date, due_date, grand_total, outstanding_amount, currency,
               CASE WHEN due_date < CURDATE() AND outstanding_amount > 0 THEN 1 ELSE 0 END AS is_overdue
        FROM `tabSales Invoice`
        WHERE company = %(company)s AND customer = %(customer)s AND docstatus = 1
          AND outstanding_amount > 0
        ORDER BY due_date ASC
    """, {"company": company, "customer": customer}, as_dict=True)

    payments = frappe.db.sql("""
        SELECT name, payment_date, paid_amount, mode_of_payment
        FROM `tabPayment Entry`
        WHERE company = %(company)s AND party = %(customer)s AND party_type = 'Customer'
          AND docstatus = 1
        ORDER BY payment_date DESC
        LIMIT 20
    """, {"company": company, "customer": customer}, as_dict=True)

    total_outstanding = sum(flt(i["outstanding_amount"]) for i in invoices)
    overdue_amount    = sum(flt(i["outstanding_amount"]) for i in invoices if i["is_overdue"])

    cust = frappe.db.get_value("Customer", customer,
                               ["customer_name", "email_id", "mobile_no"], as_dict=True) or {}

    return {
        "customer": customer,
        "customer_name": cust.get("customer_name", customer),
        "email": cust.get("email_id", ""),
        "mobile": cust.get("mobile_no", ""),
        "invoices": invoices,
        "payments": payments,
        "total_outstanding": total_outstanding,
        "overdue_amount": overdue_amount,
    }


@frappe.whitelist()
def send_customer_statement(customer: str, company: str) -> dict:
    """Email the account statement to the customer."""
    data = get_customer_statement(customer, company)
    email = data.get("email", "")
    if not email:
        frappe.throw("No email address on file for this customer.")

    cname = data["customer_name"]
    rows_html = "".join(
        f"<tr><td>{i['name']}</td><td>{i['posting_date']}</td><td>{i['due_date']}</td>"
        f"<td style='text-align:right'>₹{flt(i['outstanding_amount']):,.2f}</td>"
        f"<td style='color:{'#c92a2a' if i['is_overdue'] else '#2f9e44'}'>"
        f"{'Overdue' if i['is_overdue'] else 'Due'}</td></tr>"
        for i in data["invoices"]
    )

    body = f"""
<p>Dear {cname},</p>
<p>Please find your account statement from <b>{company}</b> as of today.</p>
<table border="1" cellpadding="6" cellspacing="0"
  style="border-collapse:collapse;font-size:13px;width:100%">
  <thead style="background:#f3f4f6">
    <tr><th>Invoice</th><th>Date</th><th>Due Date</th><th>Outstanding</th><th>Status</th></tr>
  </thead>
  <tbody>{rows_html}</tbody>
  <tfoot>
    <tr style="font-weight:700;background:#f3f4f6">
      <td colspan="3">Total Outstanding</td>
      <td style="text-align:right">₹{data['total_outstanding']:,.2f}</td><td></td>
    </tr>
  </tfoot>
</table>
<p>Please arrange payment at your earliest convenience. Thank you.</p>
<p>Regards,<br>{company}</p>
"""
    frappe.sendmail(
        recipients=[email],
        subject=f"Account Statement – {company}",
        message=body,
        reference_doctype="Customer",
        reference_name=customer,
    )
    return {"sent": True, "email": email}


# ── P&L Monthly Breakdown ────────────────────────────────────────────────────

@frappe.whitelist()
def get_pl_monthly_breakdown(company: str, from_date: str, to_date: str) -> list[dict]:
    """Monthly income vs expense for sparkline / bar charts."""
    rows = frappe.db.sql("""
        SELECT
            DATE_FORMAT(gle.posting_date, '%%Y-%%m') AS month,
            SUM(CASE WHEN a.account_type = 'Income'
                     THEN gle.credit - gle.debit ELSE 0 END) AS income,
            SUM(CASE WHEN a.account_type IN ('Expense', 'Cost of Goods Sold', 'Stock Adjustment')
                     THEN gle.debit - gle.credit ELSE 0 END) AS expense
        FROM `tabGeneral Ledger Entry` gle
        JOIN `tabAccount` a ON a.name = gle.account
        WHERE gle.company    = %(company)s
          AND gle.is_cancelled = 0
          AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
          AND a.account_type IN ('Income', 'Expense', 'Cost of Goods Sold', 'Stock Adjustment')
        GROUP BY DATE_FORMAT(gle.posting_date, '%%Y-%%m')
        ORDER BY month
    """, {"company": company, "from_date": from_date, "to_date": to_date}, as_dict=True)

    for r in rows:
        r["profit"] = flt(r.get("income")) - flt(r.get("expense"))

    return rows


# ── GST / ITC Report (P3/Issue 9) ─────────────────────────────────────────────
@frappe.whitelist()
def get_gstr_summary(company: str, from_date: str, to_date: str) -> dict:
    """
    Build a GSTR-3B style summary:
      - Output tax  : taxes collected on submitted Sales Invoices
      - Input tax (ITC): taxes paid on submitted Purchase Invoices
      - Net liability : output - ITC
    Returns a dict with 'output', 'itc', and 'net' sections, each a list of
    {"tax_type": str, "amount": float} rows plus a totals dict.
    """
    # ── Output tax (from Sales Invoices) ──────────────────────────────────────
    output_rows = frappe.db.sql("""
        SELECT
            COALESCE(NULLIF(tl.tax_type, ''), tl.description) AS tax_type,
            tl.description,
            SUM(tl.tax_amount)      AS amount,
            COUNT(DISTINCT si.name) AS invoice_count
        FROM `tabTax Line` tl
        JOIN `tabSales Invoice` si
          ON si.name = tl.parent AND tl.parenttype = 'Sales Invoice'
        WHERE si.company        = %(company)s
          AND si.docstatus      = 1
          AND si.posting_date   BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY tax_type, tl.description
        ORDER BY tax_type
    """, {"company": company, "from_date": from_date, "to_date": to_date},
    as_dict=True)

    # ── Input Tax Credit (from Purchase Invoices) ─────────────────────────────
    itc_rows = frappe.db.sql("""
        SELECT
            COALESCE(NULLIF(tl.tax_type, ''), tl.description) AS tax_type,
            tl.description,
            SUM(tl.tax_amount)      AS amount,
            COUNT(DISTINCT pi.name) AS invoice_count
        FROM `tabTax Line` tl
        JOIN `tabPurchase Invoice` pi
          ON pi.name = tl.parent AND tl.parenttype = 'Purchase Invoice'
        WHERE pi.company        = %(company)s
          AND pi.docstatus      = 1
          AND pi.posting_date   BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY tax_type, tl.description
        ORDER BY tax_type
    """, {"company": company, "from_date": from_date, "to_date": to_date},
    as_dict=True)

    total_output = sum(flt(r.amount) for r in output_rows)
    total_itc    = sum(flt(r.amount) for r in itc_rows)

    # Taxable value = sum of net_total on outward SIs for the period
    taxable_row = frappe.db.sql("""
        SELECT COALESCE(SUM(net_total), 0) AS taxable_value
        FROM `tabSales Invoice`
        WHERE company = %(company)s AND docstatus = 1 AND is_return = 0
          AND posting_date BETWEEN %(from_date)s AND %(to_date)s
    """, {"company": company, "from_date": from_date, "to_date": to_date}, as_dict=True)
    taxable_value = flt(taxable_row[0].taxable_value) if taxable_row else 0.0

    # ── Net payable by tax type ────────────────────────────────────────────────
    output_by_type = {r.tax_type: flt(r.amount) for r in output_rows}
    itc_by_type    = {r.tax_type: flt(r.amount) for r in itc_rows}
    all_types      = sorted(set(list(output_by_type) + list(itc_by_type)))

    net_rows = [
        {
            "tax_type":  t,
            "output":    output_by_type.get(t, 0.0),
            "itc":       itc_by_type.get(t, 0.0),
            "net":       output_by_type.get(t, 0.0) - itc_by_type.get(t, 0.0),
        }
        for t in all_types
    ]

    return {
        "output":         [dict(r) for r in output_rows],
        "itc":            [dict(r) for r in itc_rows],
        "net_by_type":    net_rows,
        "taxable_value":  taxable_value,
        "totals": {
            "total_output":      total_output,
            "total_itc":         total_itc,
            "net_tax_liability": total_output - total_itc,
        },
    }


# ── Report Drill-Down (Audit Part 3 — Limited Report Drill-Down) ──────────────

@frappe.whitelist()
def get_account_ledger(
    account: str,
    company: str,
    from_date: str,
    to_date: str,
    party_type: str = None,
    party: str = None,
) -> dict:
    """
    Drill-down: full GL ledger for a single account in a date range.
    Returns opening balance, all period movements, closing balance.
    Used when the user clicks an account balance in P&L / Balance Sheet.
    """
    # Opening balance (all entries before from_date)
    opening_result = frappe.db.sql("""
        SELECT COALESCE(SUM(debit) - SUM(credit), 0) AS opening
        FROM `tabGeneral Ledger Entry`
        WHERE account     = %(account)s
          AND company     = %(company)s
          AND is_cancelled = 0
          AND posting_date < %(from_date)s
    """, {"account": account, "company": company, "from_date": from_date}, as_dict=True)
    opening = flt(opening_result[0].opening) if opening_result else 0.0

    # Period entries
    conds = [
        "account = %(account)s",
        "company = %(company)s",
        "is_cancelled = 0",
        "posting_date BETWEEN %(from_date)s AND %(to_date)s",
    ]
    params = {"account": account, "company": company,
              "from_date": from_date, "to_date": to_date}

    if party_type:
        conds.append("party_type = %(party_type)s")
        params["party_type"] = party_type
    if party:
        conds.append("party = %(party)s")
        params["party"] = party

    where = " AND ".join(conds)
    entries = frappe.db.sql(f"""
        SELECT
            name, posting_date, voucher_type, voucher_no,
            party_type, party, debit, credit, remarks,
            (SUM(debit - credit) OVER (
                ORDER BY posting_date, creation
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) + %(opening)s) AS running_balance
        FROM `tabGeneral Ledger Entry`
        WHERE {where}
        ORDER BY posting_date, creation
    """, {**params, "opening": opening}, as_dict=True)

    total_debit  = sum(flt(e.debit)  for e in entries)
    total_credit = sum(flt(e.credit) for e in entries)
    closing      = opening + total_debit - total_credit

    return {
        "account":     account,
        "from_date":   from_date,
        "to_date":     to_date,
        "opening":     opening,
        "total_debit": total_debit,
        "total_credit":total_credit,
        "closing":     closing,
        "entries":     [dict(e) for e in entries],
    }


@frappe.whitelist()
def get_voucher_detail(voucher_type: str, voucher_no: str) -> dict:
    """
    Drill-down: all GL entries for a single voucher (invoice, payment, etc.).
    Also returns metadata about the source document.
    Used when clicking any voucher_no link in ledger or report views.
    """
    gl_entries = frappe.db.sql("""
        SELECT
            name, posting_date, account, party_type, party,
            debit, credit, remarks, voucher_type, voucher_no,
            is_cancelled, is_reversal
        FROM `tabGeneral Ledger Entry`
        WHERE voucher_type = %(vt)s AND voucher_no = %(vn)s
        ORDER BY posting_date, creation
    """, {"vt": voucher_type, "vn": voucher_no}, as_dict=True)

    total_debit  = sum(flt(e.debit)  for e in gl_entries if not e.is_cancelled)
    total_credit = sum(flt(e.credit) for e in gl_entries if not e.is_cancelled)

    # Fetch lightweight source doc fields for context
    extra = {}
    try:
        if voucher_type in ("Sales Invoice",):
            extra = frappe.get_value(voucher_type, voucher_no,
                ["customer", "customer_name", "grand_total", "outstanding_amount"],
                as_dict=True) or {}
        elif voucher_type in ("Purchase Invoice",):
            extra = frappe.get_value(voucher_type, voucher_no,
                ["supplier", "grand_total", "outstanding_amount"],
                as_dict=True) or {}
        elif voucher_type == "Payment Entry":
            extra = frappe.get_value(voucher_type, voucher_no,
                ["party_type", "party", "paid_amount", "payment_type"],
                as_dict=True) or {}
        elif voucher_type == "Stock Entry":
            extra = frappe.get_value(voucher_type, voucher_no,
                ["stock_entry_type", "total_outgoing_value", "total_incoming_value"],
                as_dict=True) or {}
    except Exception:
        pass

    return {
        "voucher_type":  voucher_type,
        "voucher_no":    voucher_no,
        "gl_entries":    [dict(e) for e in gl_entries],
        "total_debit":   total_debit,
        "total_credit":  total_credit,
        "is_balanced":   abs(total_debit - total_credit) < 0.01,
        "source_doc":    dict(extra) if extra else {},
    }


@frappe.whitelist()
def get_pl_account_breakdown(
    company: str, from_date: str, to_date: str, account_type: str = "Income"
) -> list[dict]:
    """
    Drill-down: P&L breakdown by individual account within a type (Income/Expense).
    Click Income total → see each income account with its amount.
    Click an account → get_account_ledger for full transactions.
    """
    return frappe.db.sql("""
        SELECT
            gle.account,
            a.account_type,
            COALESCE(SUM(gle.credit) - SUM(gle.debit), 0) AS amount,
            COUNT(DISTINCT gle.voucher_no) AS transaction_count
        FROM `tabGeneral Ledger Entry` gle
        JOIN `tabAccount` a ON a.name = gle.account
        WHERE gle.company      = %(company)s
          AND gle.is_cancelled  = 0
          AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
          AND a.account_type   = %(account_type)s
        GROUP BY gle.account, a.account_type
        ORDER BY ABS(SUM(gle.credit) - SUM(gle.debit)) DESC
    """, {"company": company, "from_date": from_date,
          "to_date": to_date, "account_type": account_type}, as_dict=True)


@frappe.whitelist()
def get_party_ledger(
    party_type: str,
    party: str,
    company: str,
    from_date: str = None,
    to_date: str = None,
) -> dict:
    """
    Drill-down: complete ledger for a customer or supplier — all invoices,
    payments, and outstanding per document.  Used in customer/supplier cards.
    """
    inv_dt     = "Sales Invoice"    if party_type == "Customer" else "Purchase Invoice"
    party_fld  = "customer"         if party_type == "Customer" else "supplier"

    inv_filters = {party_fld: party, "company": company, "docstatus": 1}
    if from_date and to_date:
        inv_filters["posting_date"] = ["between", [from_date, to_date]]
    elif from_date:
        inv_filters["posting_date"] = [">=", from_date]
    elif to_date:
        inv_filters["posting_date"] = ["<=", to_date]

    invoices = frappe.get_all(
        inv_dt,
        filters=inv_filters,
        fields=["name", "posting_date", "due_date", "grand_total",
                "outstanding_amount", "status", "currency"],
        order_by="posting_date desc",
        limit=500,
    )

    pay_filters = {"party_type": party_type, "party": party,
                   "company": company, "docstatus": 1}
    payments = frappe.get_all(
        "Payment Entry",
        filters=pay_filters,
        fields=["name", "payment_date", "payment_type", "paid_amount", "mode_of_payment"],
        order_by="payment_date desc",
        limit=200,
    )

    total_invoiced    = sum(flt(i.grand_total)        for i in invoices)
    total_outstanding = sum(flt(i.outstanding_amount) for i in invoices)
    total_paid        = total_invoiced - total_outstanding

    return {
        "party_type":        party_type,
        "party":             party,
        "total_invoiced":    total_invoiced,
        "total_paid":        total_paid,
        "total_outstanding": total_outstanding,
        "invoices":          [dict(i) for i in invoices],
        "payments":          [dict(p) for p in payments],
    }


def get_itc_ledger(company: str, from_date: str, to_date: str) -> list[dict]:
    """
    Line-by-line ITC ledger — every tax line on every submitted Purchase Invoice.
    Useful for GSTR-2A reconciliation.
    """
    return frappe.db.sql("""
        SELECT
            pi.name            AS voucher_no,
            pi.posting_date,
            pi.supplier,
            pi.bill_no,
            pi.bill_date,
            COALESCE(NULLIF(tl.tax_type, ''), tl.description) AS tax_type,
            tl.description,
            tl.rate            AS tax_rate,
            tl.tax_amount,
            tl.account_head
        FROM `tabTax Line` tl
        JOIN `tabPurchase Invoice` pi
          ON pi.name = tl.parent AND tl.parenttype = 'Purchase Invoice'
        WHERE pi.company        = %(company)s
          AND pi.docstatus      = 1
          AND pi.posting_date   BETWEEN %(from_date)s AND %(to_date)s
        ORDER BY pi.posting_date, pi.name, tl.idx
    """, {"company": company, "from_date": from_date, "to_date": to_date},
    as_dict=True)


@frappe.whitelist()
def get_gstr1_data(company: str, from_date: str, to_date: str) -> dict:
    """
    GSTR-1 structured data:
    - b2b: invoices with customer GSTIN (registered buyers)
    - b2c: invoices without GSTIN (unregistered / consumer)
    - cdnr: credit notes for B2B customers
    - hsn_summary: HSN-wise taxable + tax amounts
    """
    params = {"company": company, "from_date": from_date, "to_date": to_date}

    invoices = frappe.db.sql("""
        SELECT
            si.name, si.posting_date, si.customer, si.customer_name,
            COALESCE(NULLIF(si.customer_gstin,''), c.tax_id, '') AS customer_gstin,
            si.place_of_supply, si.net_total, si.total_tax, si.grand_total,
            si.is_return, si.return_against
        FROM `tabSales Invoice` si
        LEFT JOIN `tabCustomer` c ON c.name = si.customer
        WHERE si.company = %(company)s
          AND si.docstatus = 1
          AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
        ORDER BY si.posting_date, si.name
    """, params, as_dict=True)

    # Tax lines for each invoice
    tax_rows = frappe.db.sql("""
        SELECT tl.parent, tl.tax_type, tl.description, tl.rate, tl.tax_amount
        FROM `tabTax Line` tl
        JOIN `tabSales Invoice` si ON si.name = tl.parent AND tl.parenttype = 'Sales Invoice'
        WHERE si.company = %(company)s AND si.docstatus = 1
          AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
    """, params, as_dict=True)

    taxes_by_inv = {}
    for t in tax_rows:
        taxes_by_inv.setdefault(t.parent, []).append(t)

    # HSN summary from SI items
    hsn_rows = frappe.db.sql("""
        SELECT
            COALESCE(NULLIF(ii.hsn_code,''), 'Not Set') AS hsn_code,
            SUM(ii.amount) AS taxable_value,
            COUNT(DISTINCT si.name) AS invoice_count
        FROM `tabSales Invoice Item` ii
        JOIN `tabSales Invoice` si ON si.name = ii.parent
        WHERE si.company = %(company)s AND si.docstatus = 1
          AND si.is_return = 0
          AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY hsn_code
        ORDER BY taxable_value DESC
    """, params, as_dict=True)

    b2b, b2c, cdnr = [], [], []
    for inv in invoices:
        inv["taxes"] = taxes_by_inv.get(inv.name, [])
        if inv.is_return:
            if inv.customer_gstin:
                cdnr.append(inv)
            # Skip unregistered credit notes (B2CS debit note — rare, omit for now)
        else:
            if inv.customer_gstin:
                b2b.append(inv)
            else:
                b2c.append(inv)

    total_taxable = sum(flt(i.net_total) for i in b2b + b2c)
    total_tax = sum(flt(i.total_tax) for i in b2b + b2c)

    return {
        "b2b": [dict(r) for r in b2b],
        "b2c": [dict(r) for r in b2c],
        "cdnr": [dict(r) for r in cdnr],
        "hsn_summary": [dict(r) for r in hsn_rows],
        "totals": {
            "b2b_count": len(b2b),
            "b2c_count": len(b2c),
            "cdnr_count": len(cdnr),
            "total_taxable": total_taxable,
            "total_tax": total_tax,
        },
    }


@frappe.whitelist()
def get_tds_transactions(company: str, from_date: str = None, to_date: str = None) -> list:
    """
    TDS deductions: Purchase Invoice tax lines where the tax_type / description
    indicates a TDS section (194C, 194J, 194I, TDS, etc.).
    Falls back to ALL tax lines on PIs when no TDS-specific lines exist.
    """
    params = {"company": company}
    date_clause = ""
    if from_date and to_date:
        date_clause = "AND pi.posting_date BETWEEN %(from_date)s AND %(to_date)s"
        params["from_date"] = from_date
        params["to_date"] = to_date

    rows = frappe.db.sql(f"""
        SELECT
            pi.name, pi.posting_date,
            pi.supplier, pi.supplier_name,
            pi.grand_total AS gross_amount,
            pi.grand_total,
            tl.tax_type, tl.description AS tds_section,
            tl.rate, tl.tax_amount AS tds_amount,
            (pi.grand_total - tl.tax_amount) AS net_payment
        FROM `tabTax Line` tl
        JOIN `tabPurchase Invoice` pi ON pi.name = tl.parent AND tl.parenttype = 'Purchase Invoice'
        WHERE pi.company = %(company)s
          AND pi.docstatus = 1
          {date_clause}
          AND (
            UPPER(COALESCE(tl.tax_type,'')) LIKE '%%TDS%%'
            OR UPPER(COALESCE(tl.description,'')) LIKE '%%TDS%%'
            OR UPPER(COALESCE(tl.description,'')) REGEXP '194[A-Z]?'
            OR UPPER(COALESCE(tl.description,'')) REGEXP '195'
            OR UPPER(COALESCE(tl.description,'')) LIKE '%%WITHHOLD%%'
          )
        ORDER BY pi.posting_date DESC, pi.name
    """, params, as_dict=True)

    if not rows:
        # No TDS-specific lines — return empty (don't confuse GST tax lines with TDS)
        return []

    return [dict(r) for r in rows]