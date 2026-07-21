from __future__ import annotations
"""
Accounting Engine — P2/Issue 3
Central module that owns all GL map construction logic.

Every financial DocType calls into this module on submit/cancel instead of
building its own GL maps, ensuring a single place to audit and change posting rules.
"""
import re
import frappe
from frappe import _
from frappe.utils import flt
from zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry import (
    make_gl_entries,
)

_TDS_PATTERN = re.compile(r"TDS|194[A-Z]?|WITHHOLD|195|WITH.?HOLD", re.IGNORECASE)


def _is_tds_line(tax) -> bool:
    desc = (getattr(tax, "description", "") or "").strip()
    ttype = (getattr(tax, "tax_type", "") or getattr(tax, "charge_type", "") or "").strip()
    return bool(_TDS_PATTERN.search(desc) or _TDS_PATTERN.search(ttype))


def _get_tds_payable(company: str) -> str | None:
    acct = (
        frappe.db.get_value("Account", {"account_name": ["like", "%TDS Payable%"], "company": company, "is_group": 0}, "name")
        or frappe.db.get_value("Account", {"account_type": "Tax", "account_name": ["like", "%TDS%"], "company": company, "is_group": 0}, "name")
    )
    if acct:
        return acct

    # No TDS Payable account exists → create one, otherwise the posting engine
    # grosses Accounts Payable back up to the full bill value and the ledger
    # stops matching the bill's net-of-TDS Grand Total / balance due.
    parent = (
        frappe.db.get_value("Account", {"company": company, "is_group": 1, "account_type": "Liability", "account_name": ["like", "%Current Liabilit%"]}, "name")
        or frappe.db.get_value("Account", {"company": company, "is_group": 1, "account_type": "Liability"}, "name")
        or frappe.db.get_value("Account", {"company": company, "is_group": 1, "account_name": ["like", "%Liabilit%"]}, "name")
    )
    if not parent:
        return None
    try:
        doc = frappe.get_doc({
            "doctype": "Account",
            "account_name": "TDS Payable",
            "company": company,
            "account_type": "Liability",   # statutory dues owed to the tax dept
            "parent_account": parent,
            "is_group": 0,
        })
        doc.insert(ignore_permissions=True)
        return doc.name
    except Exception:
        frappe.log_error(frappe.get_traceback(), "TDS Payable auto-create failed")
        return None


def _get_round_off_account(company: str) -> str | None:
    """Account that absorbs the paise-level Round Off adjustment (Sec 170,
    CGST Act) between the pre-round (net + tax) total and the rounded
    Grand Total, so GL debits/credits stay balanced to the rupee."""
    acct = frappe.db.get_value(
        "Account",
        {"account_name": ["like", "%Round Off%"], "company": company, "is_group": 0},
        "name",
    )
    if acct:
        return acct

    parent = (
        frappe.db.get_value("Account", {"company": company, "is_group": 1, "account_name": ["like", "%Indirect Expense%"]}, "name")
        or frappe.db.get_value("Account", {"company": company, "is_group": 1, "account_type": "Expense"}, "name")
        or frappe.db.get_value("Account", {"company": company, "is_group": 1, "account_name": ["like", "%Expense%"]}, "name")
        or frappe.db.get_value("Account", {"company": company, "is_group": 1}, "name")
    )
    if not parent:
        return None
    try:
        doc = frappe.get_doc({
            "doctype": "Account",
            "account_name": "Round Off",
            "company": company,
            "account_type": "Expense",
            "parent_account": parent,
            "is_group": 0,
        })
        doc.insert(ignore_permissions=True)
        return doc.name
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"Round Off account auto-create failed for {company}")
        return None


def _append_round_off_entry(gl_map: list[dict], doc, invert: bool = False) -> None:
    """Append the GL line for doc.round_off, if any, so debits == credits.

    round_off = grand_total - (net_total + tax_total). On a Sales Invoice
    grand_total sits on the *debit* leg (Receivable), so a positive
    round_off means debit > credit and the difference must be *credited*
    here (invert=False). On a Purchase Invoice grand_total sits on the
    *credit* leg (Payable) instead — the polarity is reversed, so a
    positive round_off there means credit > debit and the difference must
    be *debited* here (invert=True). Passing the wrong value doesn't fail
    loudly; it silently doubles the imbalance instead of closing it.
    """
    round_off = flt(getattr(doc, "round_off", 0))
    if not round_off:
        return
    if invert:
        round_off = -round_off
    account = _get_round_off_account(doc.company)
    if not account:
        frappe.throw(_("Please set up a Round Off account for {0} to submit this invoice").format(doc.company))
    gl_map.append({
        "account":      account,
        "debit":        -round_off if round_off < 0 else 0,
        "credit":       round_off if round_off > 0 else 0,
        "voucher_type": doc.doctype,
        "voucher_no":   doc.name,
        "posting_date": doc.posting_date,
        "company":      doc.company,
        "fiscal_year":  doc.fiscal_year or "",
        "cost_center":  doc.cost_center or "",
        "remarks":      f"Round Off \u2014 {doc.doctype} {doc.name}",
    })


# ─── Sales Invoice ─────────────────────────────────────────────────────────────

def post_sales_invoice(doc) -> None:
    """
    DR Receivable / CR Income (+ tax accounts) on Sales Invoice submit.

    COGS is NOT posted here. Stock leaving the warehouse (Delivery Note or
    Sales Invoice with Update Inventory) creates a Material Issue Stock Entry
    that posts DR COGS / CR Inventory at valuation rate. Posting COGS again on
    this invoice would double-count cost of sales.

    Return invoices (is_return=1, used for Credit Notes) carry negative
    qty/rate, so grand_total/net_total/tax_amount come out negative here.
    A ledger must never store a negative debit or credit — normalize by
    flipping the sign into the opposite column, same pattern already used
    in _append_round_off_entry. Net effect on account balances (which sum
    debit - credit) is unchanged; only which column the amount sits in.
    """
    _require(doc, "debit_to",      "Debit To (Accounts Receivable) account")
    _require(doc, "income_account","Income Account")

    grand_total = flt(doc.grand_total)
    net_total   = flt(doc.net_total)

    gl_map = [
        {
            "account":      doc.debit_to,
            "debit":        grand_total if grand_total >= 0 else 0,
            "credit":       -grand_total if grand_total < 0 else 0,
            "voucher_type": doc.doctype,
            "voucher_no":   doc.name,
            "posting_date": doc.posting_date,
            "party_type":   "Customer",
            "party":        doc.customer,
            "company":      doc.company,
            "fiscal_year":  doc.fiscal_year or "",
            "cost_center":  doc.cost_center or "",
            "remarks":      f"Invoice {doc.name} — {doc.customer_name or doc.customer}",
        },
        {
            "account":      doc.income_account,
            "debit":        -net_total if net_total < 0 else 0,
            "credit":       net_total if net_total >= 0 else 0,
            "voucher_type": doc.doctype,
            "voucher_no":   doc.name,
            "posting_date": doc.posting_date,
            "company":      doc.company,
            "fiscal_year":  doc.fiscal_year or "",
            "cost_center":  doc.cost_center or "",
            "remarks":      f"Income — Invoice {doc.name}",
        },
    ]
    for tax in (doc.taxes or []):
        tax_amount = flt(tax.tax_amount)
        if tax_amount and tax.account_head:
            gl_map.append({
                "account":      tax.account_head,
                "debit":        -tax_amount if tax_amount < 0 else 0,
                "credit":       tax_amount if tax_amount >= 0 else 0,
                "voucher_type": doc.doctype,
                "voucher_no":   doc.name,
                "posting_date": doc.posting_date,
                "company":      doc.company,
                "fiscal_year":  doc.fiscal_year or "",
                "cost_center":  doc.cost_center or "",
                "remarks":      f"{tax.description} — Invoice {doc.name}",
            })
    _append_round_off_entry(gl_map, doc)
    make_gl_entries(gl_map)


# ─── Purchase Invoice ──────────────────────────────────────────────────────────

def post_purchase_invoice(doc) -> None:
    """
    Perpetual inventory (Model B — GR/IR) purchase posting:

      Stock items     → DR Stock Received But Not Billed (clears receipt credit)
      Non-stock items → DR Expense Account
      Input Tax Credit → DR each tax line's account_head
      Total payable    → CR Accounts Payable (grand_total)

    Stock quantity/value is capitalized on the Material Receipt Stock Entry
    (DR Inventory / CR GRIR). This invoice only clears GRIR for stock lines —
    it must NOT debit Inventory again, or stock would be double-capitalized.
    """
    from zoho_books_clone.accounts.inventory_gl import (
        build_purchase_invoice_debit_lines,
        classify_purchase_item_amounts,
        get_grir_account,
    )

    _require(doc, "credit_to", "Credit To (Accounts Payable) account")

    split = classify_purchase_item_amounts(doc)
    # Fallback when the bill has no item rows with amounts: treat full net as expense
    stock_total = split["stock_total"]
    expense_total = split["expense_total"]
    if not stock_total and not expense_total:
        expense_total = flt(doc.net_total)
        split["has_expense"] = expense_total > 0

    if split["has_expense"]:
        _require(doc, "expense_account", "Expense Account")

    if split.get("unconfirmed_stock_items"):
        frappe.msgprint(
            _(
                "{0}: stock item(s) {1} were posted to Expense, not Inventory — "
                "no Purchase Receipt or 'Update Stock' was found to confirm the "
                "goods were actually received. Capitalize via a Purchase Receipt "
                "or check 'Update Stock' on this bill to record them as inventory."
            ).format(doc.name, ", ".join(sorted(set(split["unconfirmed_stock_items"])))),
            indicator="orange",
            alert=True,
        )

    net_total   = flt(doc.net_total)
    grand_total = flt(doc.grand_total)
    total_tax   = flt(doc.total_tax) if hasattr(doc, "total_tax") else (grand_total - net_total)

    grir_account = get_grir_account(doc.company) if stock_total else None
    debit_lines = build_purchase_invoice_debit_lines(
        doc,
        stock_total=stock_total,
        expense_total=expense_total,
        grir_account=grir_account,
        expense_account=getattr(doc, "expense_account", None),
    )
    if not debit_lines:
        frappe.throw(_("Purchase Invoice {0} has no net amount to post").format(doc.name))

    gl_map = list(debit_lines)
    gl_map.append({
        "account":      doc.credit_to,
        "debit":        0,
        "credit":       grand_total,
        "voucher_type": doc.doctype,
        "voucher_no":   doc.name,
        "posting_date": doc.posting_date,
        "party_type":   "Supplier",
        "party":        doc.supplier,
        "company":      doc.company,
        "fiscal_year":  doc.fiscal_year or "",
        "cost_center":  doc.cost_center or "",
        "remarks":      f"Payable to {doc.supplier} — Bill {doc.name}",
    })

    # Separate TDS (deduction) lines from ITC (addition) lines
    tds_total = flt(0)
    for tax in (doc.taxes or []):
        if _is_tds_line(tax):
            tds_total += abs(flt(tax.tax_amount))

    # grand_total already reflects TDS deduction (vendor receives net).
    # Balance: CR AP (grand_total) + CR TDS Payable (tds_total) = DR cost legs + DR ITC.
    if tds_total > 0:
        tds_payable_acct = _get_tds_payable(doc.company)
        if tds_payable_acct:
            gl_map.append({
                "account":      tds_payable_acct,
                "debit":        0,
                "credit":       tds_total,
                "voucher_type": doc.doctype,
                "voucher_no":   doc.name,
                "posting_date": doc.posting_date,
                "company":      doc.company,
                "fiscal_year":  doc.fiscal_year or "",
                "cost_center":  doc.cost_center or "",
                "remarks":      f"TDS withheld — Bill {doc.name}",
            })
        else:
            for entry in gl_map:
                if entry["account"] == doc.credit_to:
                    entry["credit"] = round(grand_total + tds_total, 2)
                    break

    # DR individual ITC accounts per tax line (CGST, SGST, IGST, etc.) — skip TDS lines
    tax_lines_posted = flt(0)
    for tax in (doc.taxes or []):
        if _is_tds_line(tax):
            continue

        tax_amount = flt(tax.tax_amount)
        if not tax_amount:
            continue

        account = tax.account_head
        if not account:
            continue

        gl_map.append({
            "account":      account,
            # _is_tds_line() only catches negatives whose description/tax_type
            # text matches a TDS-ish pattern — any other negative-rate tax
            # component (return adjustment, differently-worded withholding,
            # etc.) must still be flipped into the credit column here, same
            # as post_sales_invoice's tax loop, so debit/credit never go
            # negative.
            "debit":        tax_amount if tax_amount > 0 else 0,
            "credit":       -tax_amount if tax_amount < 0 else 0,
            "voucher_type": doc.doctype,
            "voucher_no":   doc.name,
            "posting_date": doc.posting_date,
            "company":      doc.company,
            "fiscal_year":  doc.fiscal_year or "",
            "cost_center":  doc.cost_center or "",
            "remarks":      f"ITC — {tax.tax_type or tax.description or 'Tax'} — Bill {doc.name}",
        })
        tax_lines_posted += tax_amount

    # If no tax lines had account_heads, fold non-TDS tax into the primary cost debit
    # (prefer expense leg; else GRIR) so the entry remains balanced.
    non_tds_tax = total_tax + tds_total
    if not tax_lines_posted and non_tds_tax:
        fold_account = (
            getattr(doc, "expense_account", None)
            if expense_total
            else grir_account
        )
        for entry in gl_map:
            if fold_account and entry["account"] == fold_account and entry.get("debit"):
                entry["debit"] = round(flt(entry["debit"]) + non_tds_tax, 2)
                entry["remarks"] = f"Purchase cost (gross, no ITC accounts) — Bill {doc.name}"
                break

    _append_round_off_entry(gl_map, doc, invert=True)
    make_gl_entries(gl_map)


# ─── Debit Note (Purchase Return) ──────────────────────────────────────────────

def post_debit_note(doc, return_type: str = "expense") -> None:
    """
    Post GL for a Debit Note (Purchase Invoice with is_return=1), split PER
    LINE by stock vs non-stock (see inventory_gl.classify_debit_note_item_amounts)
    instead of forcing the whole document into one bucket:
      Stock lines    → DR AP / CR Inventory  (stock leaves, liability reduces)
      Non-stock lines → DR AP / CR Expense   (cost is reversed)
    Tax lines with an account_head also reverse the ITC taken on the original
    bill (CR the input-tax account), so the payable reduction stays tax-inclusive.

    Debit note items carry negative qty, so grand_total/net_total/tax amounts
    are negative — post their absolute values on the reversing sides. The DN
    must sit as a DEBIT balance on AP (see apply_debit_note_to_bill), so the
    amounts here have to be positive.

    The legacy `return_type` param is kept only as a fallback for the rare
    case the per-line split resolves to nothing (e.g. no item rows).
    """
    from zoho_books_clone.accounts.inventory_gl import (
        classify_debit_note_item_amounts,
        get_inventory_account,
    )

    ap_account = getattr(doc, "credit_to", None) or _acct_by_type(doc.company, "Payable")
    if not ap_account:
        frappe.log_error(
            f"Debit Note {doc.name}: no Payable account found. GL skipped.",
            "Debit Note GL"
        )
        return

    amount = abs(flt(doc.grand_total))
    fy = getattr(doc, "fiscal_year", "") or ""

    split = classify_debit_note_item_amounts(doc)
    stock_total = split["stock_total"]
    expense_total = split["expense_total"]
    if not stock_total and not expense_total:
        # No item-level amounts resolved — fall back to the legacy whole-doc flag.
        if return_type == "inventory":
            stock_total = amount
        else:
            expense_total = amount

    gl_map = [
        {
            "account":      ap_account,
            "debit":        amount,
            "credit":       0,
            "voucher_type": doc.doctype,
            "voucher_no":   doc.name,
            "posting_date": doc.posting_date,
            "party_type":   "Supplier",
            "party":        doc.supplier,
            "company":      doc.company,
            "fiscal_year":  fy,
            "remarks":      f"Debit Note — reduce payable — {doc.name}",
        },
    ]

    # Reverse ITC per tax line where an account is known; anything without an
    # account falls into the expense/stock reversal so the entry stays balanced.
    tax_reversed = flt(0)
    for tax in (getattr(doc, "taxes", None) or []):
        tax_amount = abs(flt(tax.tax_amount))
        if not tax_amount or not tax.account_head:
            continue
        gl_map.append({
            "account":      tax.account_head,
            "debit":        0,
            "credit":       tax_amount,
            "voucher_type": doc.doctype,
            "voucher_no":   doc.name,
            "posting_date": doc.posting_date,
            "company":      doc.company,
            "fiscal_year":  fy,
            "remarks":      f"Debit Note — ITC reversal — {doc.name}",
        })
        tax_reversed += tax_amount

    # Fold any rounding/leftover-tax difference into whichever cost bucket is
    # non-zero so the entry always balances exactly against (amount - tax_reversed).
    remainder = round(amount - tax_reversed, 2)
    cost_total = round(stock_total + expense_total, 2)
    diff = round(remainder - cost_total, 2)
    if diff:
        if expense_total or not stock_total:
            expense_total = round(expense_total + diff, 2)
        else:
            stock_total = round(stock_total + diff, 2)

    if flt(stock_total):
        inventory_account = get_inventory_account(doc.company) or _acct_by_type(doc.company, "Stock")
        if not inventory_account:
            frappe.log_error(
                f"Debit Note {doc.name}: no Inventory account found. GL skipped.",
                "Debit Note GL"
            )
            return
        gl_map.append({
            "account":      inventory_account,
            "debit":        0,
            "credit":       round(stock_total, 2),
            "voucher_type": doc.doctype,
            "voucher_no":   doc.name,
            "posting_date": doc.posting_date,
            "company":      doc.company,
            "fiscal_year":  fy,
            "remarks":      f"Debit Note — Inventory reversal — {doc.name}",
        })

    if flt(expense_total):
        expense_account = (
            getattr(doc, "expense_account", None)
            or _acct_by_type(doc.company, "Expense")
        )
        if not expense_account:
            frappe.log_error(
                f"Debit Note {doc.name}: no Expense account found. GL skipped.",
                "Debit Note GL"
            )
            return
        gl_map.append({
            "account":      expense_account,
            "debit":        0,
            "credit":       round(expense_total, 2),
            "voucher_type": doc.doctype,
            "voucher_no":   doc.name,
            "posting_date": doc.posting_date,
            "company":      doc.company,
            "fiscal_year":  fy,
            "remarks":      f"Debit Note — Expense reversal — {doc.name}",
        })

    make_gl_entries(gl_map)


def _acct_by_type(company: str, account_type: str) -> str | None:
    return frappe.db.get_value(
        "Account",
        {"account_type": account_type, "company": company, "is_group": 0},
        "name",
    ) or None


# ─── Payment Entry ─────────────────────────────────────────────────────────────

def post_payment_entry(doc) -> None:
    """
    Post GL entries for a Payment Entry.
    Receive: DR Bank/Cash, CR Receivable
    Pay:     DR Payable,   CR Bank/Cash
    """
    _require(doc, "paid_from", "Paid From account")
    _require(doc, "paid_to",   "Paid To account")

    if doc.payment_type == "Receive":
        gl_map = [
            {
                "account":      doc.paid_to,       # Bank / Cash — increases
                "debit":        flt(doc.paid_amount),
                "credit":       0,
                "voucher_type": doc.doctype,
                "voucher_no":   doc.name,
                "posting_date": doc.payment_date,
                "company":      doc.company,
                "remarks":      f"Payment received — {doc.name}",
            },
            {
                "account":      doc.paid_from,     # Receivable — decreases
                "debit":        0,
                "credit":       flt(doc.paid_amount),
                "voucher_type": doc.doctype,
                "voucher_no":   doc.name,
                "posting_date": doc.payment_date,
                "party_type":   doc.party_type,
                "party":        doc.party,
                "company":      doc.company,
                "remarks":      f"Received from {doc.party} — {doc.name}",
            },
        ]
    elif doc.payment_type == "Pay":
        gl_map = [
            {
                "account":      doc.paid_to,       # Payable — decreases
                "debit":        flt(doc.paid_amount),
                "credit":       0,
                "voucher_type": doc.doctype,
                "voucher_no":   doc.name,
                "posting_date": doc.payment_date,
                "party_type":   doc.party_type,
                "party":        doc.party,
                "company":      doc.company,
                "remarks":      f"Payment to {doc.party} — {doc.name}",
            },
            {
                "account":      doc.paid_from,     # Bank / Cash — decreases
                "debit":        0,
                "credit":       flt(doc.paid_amount),
                "voucher_type": doc.doctype,
                "voucher_no":   doc.name,
                "posting_date": doc.payment_date,
                "company":      doc.company,
                "remarks":      f"Payment made — {doc.name}",
            },
        ]
    else:
        frappe.throw(_("Payment type '{0}' not supported").format(doc.payment_type))

    make_gl_entries(gl_map)


# ─── Journal Entry ─────────────────────────────────────────────────────────────

def post_journal_entry(doc) -> None:
    """Post GL entries from Journal Entry accounts child table."""
    # Resolve fiscal year from posting_date since Journal Entry has no fiscal_year field
    fy = ""
    try:
        fy_doc = frappe.db.sql(
            "SELECT name FROM `tabFiscal Year` WHERE year_start_date <= %s AND year_end_date >= %s LIMIT 1",
            (doc.posting_date, doc.posting_date), as_dict=True
        )
        fy = fy_doc[0].name if fy_doc else ""
    except Exception:
        pass

    gl_map = []
    for row in (doc.accounts or []):
        if flt(row.debit) or flt(row.credit):
            gl_map.append({
                "account":      row.account,
                "debit":        flt(row.debit),
                "credit":       flt(row.credit),
                "voucher_type": doc.doctype,
                "voucher_no":   doc.name,
                "posting_date": doc.posting_date,
                "party_type":   row.party_type or "",
                "party":        row.party or "",
                "company":      doc.company,
                "fiscal_year":  fy,
                "cost_center":  getattr(row, "cost_center", None) or getattr(doc, "cost_center", None) or "",
                "remarks":      doc.remark or f"Journal Entry {doc.name}",
            })
    if not gl_map:
        frappe.throw(_("Journal Entry has no account rows with debit or credit"))
    make_gl_entries(gl_map)


# ─── Expense ───────────────────────────────────────────────────────────────────

def post_expense(doc) -> None:
    """DR Expense Account / CR Paid-Through (Bank or Cash) on Expense submit."""
    _require(doc, "expense_account", "Expense Account")
    _require(doc, "paid_through",    "Paid Through Account")

    total = flt(doc.total_amount) or flt(doc.amount)
    gl_map = [
        {
            "account":      doc.expense_account,
            "debit":        total,
            "credit":       0,
            "voucher_type": doc.doctype,
            "voucher_no":   doc.name,
            "posting_date": doc.posting_date,
            "company":      doc.company,
            "cost_center":  doc.cost_center or "",
            "remarks":      doc.description or doc.name,
        },
        {
            "account":      doc.paid_through,
            "debit":        0,
            "credit":       total,
            "voucher_type": doc.doctype,
            "voucher_no":   doc.name,
            "posting_date": doc.posting_date,
            "company":      doc.company,
            "cost_center":  doc.cost_center or "",
            "remarks":      doc.description or doc.name,
        },
    ]
    make_gl_entries(gl_map)


# ─── Expense Claim ─────────────────────────────────────────────────────────────

def post_expense_claim(doc) -> None:
    """DR Expense Account per line / CR Employee Payable on Expense Claim approval."""
    _require(doc, "payable_account", "Payable Account")

    # Resolve a default expense account for lines that don't carry one
    default_exp_acct = frappe.db.get_value(
        "Account",
        {"account_type": "Expense", "company": doc.company, "is_group": 0},
        "name",
    )

    gl_map = []
    for row in (doc.expenses or []):
        exp_acct = default_exp_acct
        if not exp_acct:
            frappe.throw(
                _("No Expense Account found for company {0}. "
                  "Please create one before approving.").format(doc.company)
            )
        gl_map.append({
            "account":      exp_acct,
            "debit":        flt(row.amount),
            "credit":       0,
            "voucher_type": doc.doctype,
            "voucher_no":   doc.name,
            "posting_date": row.expense_date or doc.claim_date,
            "company":      doc.company,
            "cost_center":  doc.cost_center or "",
            "remarks":      row.description or row.expense_type or "Expense Claim",
        })

    gl_map.append({
        "account":      doc.payable_account,
        "debit":        0,
        "credit":       flt(doc.total_claimed_amount),
        "voucher_type": doc.doctype,
        "voucher_no":   doc.name,
        "posting_date": doc.claim_date,
        "company":      doc.company,
        "cost_center":  doc.cost_center or "",
        "remarks":      f"Expense Claim {doc.name} — {doc.employee_name}",
    })
    make_gl_entries(gl_map)


# ─── Reversal (cancel) ─────────────────────────────────────────────────────────

def reverse_voucher(voucher_type: str, voucher_no: str) -> None:
    """Create reversing GL entries for any voucher (used on cancel)."""
    make_gl_entries(
        [{"voucher_type": voucher_type, "voucher_no": voucher_no}],
        cancel=True,
    )


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _require(doc, field: str, label: str) -> None:
    if not getattr(doc, field, None):
        frappe.throw(_("Please set the '{0}' field on {1}").format(label, doc.name or "this document"))