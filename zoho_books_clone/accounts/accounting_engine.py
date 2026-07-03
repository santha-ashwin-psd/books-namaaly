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


# ─── Sales Invoice ─────────────────────────────────────────────────────────────

def post_sales_invoice(doc) -> None:
    """DR Receivable / CR Income (+ tax accounts) on Sales Invoice submit."""
    _require(doc, "debit_to",      "Debit To (Accounts Receivable) account")
    _require(doc, "income_account","Income Account")

    gl_map = [
        {
            "account":      doc.debit_to,
            "debit":        flt(doc.grand_total),
            "credit":       0,
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
            "debit":        0,
            "credit":       flt(doc.net_total),
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
        if flt(tax.tax_amount) and tax.account_head:
            gl_map.append({
                "account":      tax.account_head,
                "debit":        0,
                "credit":       flt(tax.tax_amount),
                "voucher_type": doc.doctype,
                "voucher_no":   doc.name,
                "posting_date": doc.posting_date,
                "company":      doc.company,
                "fiscal_year":  doc.fiscal_year or "",
                "cost_center":  doc.cost_center or "",
                "remarks":      f"{tax.description} — Invoice {doc.name}",
            })
    make_gl_entries(gl_map)


# ─── Purchase Invoice ──────────────────────────────────────────────────────────

def post_purchase_invoice(doc) -> None:
    """
    DR Expense (net_total) + DR ITC Tax Accounts / CR Payable (grand_total).

    Correctly separates:
      - Net purchase cost   → Expense account (debit = net_total)
      - Input Tax Credit    → Each tax line's account_head (debit = tax_amount)
      - Total payable       → AP account (credit = grand_total)

    This ensures GST ITC is tracked per tax type in the GL, enabling accurate
    GSTR-2A reconciliation via get_itc_ledger().
    """
    _require(doc, "credit_to",       "Credit To (Accounts Payable) account")
    _require(doc, "expense_account", "Expense Account")

    net_total   = flt(doc.net_total)
    grand_total = flt(doc.grand_total)
    total_tax   = flt(doc.total_tax) if hasattr(doc, "total_tax") else (grand_total - net_total)

    gl_map = [
        # DR Expense account for net purchase cost (excluding tax)
        {
            "account":      doc.expense_account,
            "debit":        net_total,
            "credit":       0,
            "voucher_type": doc.doctype,
            "voucher_no":   doc.name,
            "posting_date": doc.posting_date,
            "company":      doc.company,
            "fiscal_year":  doc.fiscal_year or "",
            "cost_center":  doc.cost_center or "",
            "remarks":      f"Purchase cost (net) — Bill {doc.name}",
        },
        # CR Payable for full amount owed to supplier
        {
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
        },
    ]

    # Separate TDS (deduction) lines from ITC (addition) lines
    tds_total = flt(0)
    for tax in (doc.taxes or []):
        if _is_tds_line(tax):
            tds_total += abs(flt(tax.tax_amount))

    # grand_total already reflects TDS deduction (vendor receives net).
    # Balance: CR AP (grand_total) + CR TDS Payable (tds_total) = DR Expense + DR ITC.
    if tds_total > 0:
        tds_payable_acct = _get_tds_payable(doc.company)
        if tds_payable_acct:
            # CR TDS Payable — withheld amount goes to government; AP stays at grand_total (net)
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
            # No TDS Payable account — gross up AP so GL stays balanced
            for entry in gl_map:
                if entry["account"] == doc.credit_to:
                    entry["credit"] = round(grand_total + tds_total, 2)
                    break

    # DR individual ITC accounts per tax line (CGST, SGST, IGST, etc.) — skip TDS lines
    tax_lines_posted = flt(0)
    for tax in (doc.taxes or []):
        if _is_tds_line(tax):
            continue  # TDS handled above via TDS Payable, not as ITC debit

        tax_amount = flt(tax.tax_amount)
        if not tax_amount:
            continue

        account = tax.account_head
        if not account:
            # No specific account — fall into the expense line (already included in net fallback)
            continue

        gl_map.append({
            "account":      account,
            "debit":        tax_amount,
            "credit":       0,
            "voucher_type": doc.doctype,
            "voucher_no":   doc.name,
            "posting_date": doc.posting_date,
            "company":      doc.company,
            "fiscal_year":  doc.fiscal_year or "",
            "cost_center":  doc.cost_center or "",
            "remarks":      f"ITC — {tax.tax_type or tax.description or 'Tax'} — Bill {doc.name}",
        })
        tax_lines_posted += tax_amount

    # If no tax lines had account_heads, the tax was already included in the
    # expense debit via grand_total fallback. We need to adjust: swap net_total
    # debit back to grand_total so the entry remains balanced.
    non_tds_tax = total_tax + tds_total  # total_tax already has TDS as negative; add back abs to get non-TDS portion
    if not tax_lines_posted and non_tds_tax:
        for entry in gl_map:
            if entry["account"] == doc.expense_account:
                entry["debit"] = net_total + non_tds_tax
                entry["remarks"] = f"Purchase cost (gross, no ITC accounts) — Bill {doc.name}"
                break

    make_gl_entries(gl_map)


# ─── Debit Note (Purchase Return) ──────────────────────────────────────────────

def post_debit_note(doc, return_type: str = "expense") -> None:
    """
    Post GL for a Debit Note (Purchase Invoice with is_return=1).
      Goods Returned → DR AP / CR Inventory  (stock leaves, liability reduces)
      Overcharged etc → DR AP / CR Expense   (cost is reversed)
    Tax lines with an account_head also reverse the ITC taken on the original
    bill (CR the input-tax account), so the payable reduction stays tax-inclusive.

    Debit note items carry negative qty, so grand_total/net_total/tax amounts
    are negative — post their absolute values on the reversing sides. The DN
    must sit as a DEBIT balance on AP (see apply_debit_note_to_bill), so the
    amounts here have to be positive.
    """
    ap_account = getattr(doc, "credit_to", None) or _acct_by_type(doc.company, "Payable")
    if not ap_account:
        frappe.log_error(
            f"Debit Note {doc.name}: no Payable account found. GL skipped.",
            "Debit Note GL"
        )
        return

    if return_type == "inventory":
        cr_account = _acct_by_type(doc.company, "Stock")
        cr_label = "Inventory"
    else:
        cr_account = (
            getattr(doc, "expense_account", None)
            or _acct_by_type(doc.company, "Expense")
        )
        cr_label = "Expense"

    if not cr_account:
        frappe.log_error(
            f"Debit Note {doc.name}: no {cr_label} account found. GL skipped.",
            "Debit Note GL"
        )
        return

    amount = abs(flt(doc.grand_total))
    fy = getattr(doc, "fiscal_year", "") or ""

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

    gl_map.append({
        "account":      cr_account,
        "debit":        0,
        "credit":       round(amount - tax_reversed, 2),
        "voucher_type": doc.doctype,
        "voucher_no":   doc.name,
        "posting_date": doc.posting_date,
        "company":      doc.company,
        "fiscal_year":  fy,
        "remarks":      f"Debit Note — {cr_label} reversal — {doc.name}",
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