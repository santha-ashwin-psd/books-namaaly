from __future__ import annotations
"""
Central Validation Layer — P2/Issue 10
Wired via hooks.py doc_events so every financial document passes through
one consistent set of safety checks before being saved or submitted.
"""
import frappe
from frappe import _
from frappe.utils import flt, getdate


# ─── Shared lock-check helper (also called directly from API delete functions) ─

def assert_not_locked(doctype: str, name: str) -> None:
    """
    Raise ValidationError if the named document's posting date falls within a
    locked period.  Called directly by API-layer delete functions that use
    ignore_permissions=True / force=True and therefore bypass before_delete hooks.
    """
    try:
        doc = frappe.get_doc(doctype, name)
    except frappe.DoesNotExistError:
        return  # already gone — nothing to guard
    _check_lock_date(doc)
    _check_fiscal_year_period_lock(doc)


# ─── Hook entry point ─────────────────────────────────────────────────────────

def on_validate(doc, _method=None):
    """
    Called for every financial doctype listed in hooks.py doc_events.
    Runs checks that apply across all document types.
    """
    _check_company(doc)
    _check_company_tenancy(doc)    # Multi-tenant guard: doc.company must match user's company
    _check_posting_date(doc)
    _check_positive_amounts(doc)
    _check_period_not_closed(doc)
    _check_lock_date(doc)          # Audit: per-company lock date (Books Company.lock_date)
    _check_fiscal_year_period_lock(doc)  # Per-fiscal-year period lock (Fiscal Year.lock_date)
    _check_sales_items_are_sellable(doc)     # Item.is_sales_item — see below
    _check_purchase_items_are_purchasable(doc)  # Item.is_purchase_item — see below


def _check_company_tenancy(doc):
    """User can only save documents for their own Books Company."""
    from zoho_books_clone.utils.tenancy import assert_doc_in_user_company
    assert_doc_in_user_company(doc)


def on_submit(doc, _method=None):
    """Extra guards run at submit time (after validate)."""
    _check_required_accounts(doc)
    _check_credit_limit(doc)
    check_budget_for_doc(doc)


def on_cancel(doc, _method=None):
    """
    Block cancellation of documents whose posting date falls in a locked period.
    Cancelling reverses GL entries and distorts closed-period financials just as
    much as creating a new document would — so the same lock rules apply.
    System Managers are exempt (same as for saves).
    """
    _check_lock_date(doc)
    _check_fiscal_year_period_lock(doc)


def before_delete(doc, _method=None):
    """
    Block deletion of documents whose posting date falls in a locked period.
    Draft documents can be deleted without submitting, so this guard is needed
    independently of on_cancel.
    """
    _check_lock_date(doc)
    _check_fiscal_year_period_lock(doc)



# ─── Individual checks ────────────────────────────────────────────────────────

def _check_company(doc):
    """Every financial document must belong to a company."""
    if not getattr(doc, "company", None):
        frappe.throw(_("Company is required on {0}").format(doc.doctype))

    # Only validate against the Company master if that DocType exists in this
    # installation. In standalone Frappe (without ERPNext), Company is stored as
    # a plain Data field, so there is no tabCompany to query.
    try:
        if (frappe.db.table_exists("tabCompany")
                and not frappe.db.exists("Company", doc.company)):
            frappe.throw(_(
                "Company '{0}' does not exist. Please set up your company first."
            ).format(doc.company))
    except frappe.exceptions.DoesNotExistError:
        pass   # Company DocType not registered in this installation — skip check
    except Exception:
        pass   # Any meta error — skip the check rather than blocking the save


def _check_posting_date(doc):
    """Posting date must be present and not obviously invalid."""
    date_field = _posting_date_field(doc)
    if not date_field:
        return
    date_val = getattr(doc, date_field, None)
    if not date_val:
        frappe.throw(_("Posting date is required on {0}").format(doc.doctype))
    try:
        getdate(date_val)
    except Exception:
        frappe.throw(_("Invalid posting date '{0}' on {1}").format(date_val, doc.doctype))


def _check_positive_amounts(doc):
    """Key monetary fields must be ≥ 0 (return/credit docs are exempt)."""
    # is_return=1 means this is a credit note or debit note — grand_total
    # will be negative by design (reversal of the original transaction).
    if getattr(doc, "is_return", 0):
        return
    for field in ("grand_total", "net_total", "paid_amount"):
        val = getattr(doc, field, None)
        if val is not None and flt(val) < 0:
            frappe.throw(_(
                "'{0}' cannot be negative on {1} {2}"
            ).format(field, doc.doctype, doc.name or ""))


def _check_period_not_closed(doc):
    """
    If the fiscal year covering the posting date is closed, block the save.
    This is a lighter check than validate_fiscal_year (which also handles lock_date);
    here we just guard against accidentally saving to a closed year.
    """
    # Opening Entries are exempt — they establish historical balances and must
    # be allowed to post to any date, including dates in closed/locked periods.
    if getattr(doc, "voucher_type", None) == "Opening Entry":
        return

    date_field = _posting_date_field(doc)
    company    = getattr(doc, "company", None)
    if not date_field or not company:
        return
    posting_date = getattr(doc, date_field, None)
    if not posting_date:
        return
    closed = frappe.db.sql("""
        SELECT name FROM `tabFiscal Year`
        WHERE company         = %s
          AND is_closed        = 1
          AND year_start_date <= %s
          AND year_end_date   >= %s
        LIMIT 1
    """, (company, posting_date, posting_date))
    if closed:
        frappe.throw(_(
            "Fiscal Year {0} is closed. Re-open it before posting to {1}."
        ).format(closed[0][0], posting_date))


def _check_lock_date(doc):
    """
    Audit: Strict period lock — block any save/submit on a document whose
    posting date falls on or before the Books Lock Date configured per company
    in Books Company.  System Managers are exempt so they can perform corrections.
    """
    # Opening Entries are always exempt — they set up historical balances.
    if getattr(doc, "voucher_type", None) == "Opening Entry":
        return

    company = getattr(doc, "company", None)
    if not company:
        return

    try:
        lock_date = frappe.db.get_value("Books Company", company, "lock_date")
    except Exception:
        return   # Books Company may not exist yet during install

    if not lock_date:
        return

    date_field = _posting_date_field(doc)
    if not date_field:
        return

    posting_date = getattr(doc, date_field, None)
    if not posting_date:
        return

    if getdate(posting_date) <= getdate(lock_date):
        frappe.throw(_(
            "The period up to {0} is locked. You cannot create or edit {1} documents "
            "dated on or before the lock date. Contact your System Manager to unlock the period."
        ).format(frappe.bold(lock_date), doc.doctype))


def _check_sales_items_are_sellable(doc):
    """
    Every line item on a sales-facing document must be flagged as a Sales
    Item (Item.is_sales_item = 1). The item pickers in the Sales module UI
    already filter these out, but this is a server-side backstop for
    anything that bypasses the UI — API calls, data imports, or older
    clients — same as ERPNext enforces is_sales_item itself.

    Items where is_sales_item is still NULL (not yet touched by the
    v1_4 back-fill patch, e.g. a brand-new install mid-migration) are
    allowed through rather than blocked — NULL means "unknown", not
    "explicitly not a sales item", and matches the patch's own
    visible-everywhere default for anything it has no opinion about.
    """
    if doc.doctype not in ("Sales Invoice", "Sales Order", "Quotation", "Delivery Note", "Credit Note"):
        return

    for row in (getattr(doc, "items", []) or []):
        item_code = getattr(row, "item_code", None)
        if not item_code:
            continue
        is_sales_item = frappe.db.get_value("Item", item_code, "is_sales_item")
        if is_sales_item is not None and not is_sales_item:
            frappe.throw(_(
                "Row {0}: Item {1} is not marked as a Sales Item and cannot be added to a {2}."
            ).format(row.idx, frappe.bold(item_code), doc.doctype))


def _check_purchase_items_are_purchasable(doc):
    """
    Mirror of _check_sales_items_are_sellable() for the purchase side: every
    line item on a purchase-facing document must be flagged as a Purchase
    Item (Item.is_purchase_item = 1). Debit Notes are Purchase Invoice
    (is_return=1) in this app, not a separate doctype, so they're covered
    automatically by the "Purchase Invoice" check below — no extra entry
    needed.

    Same NULL-is-allowed rule as the sales-side check: an Item that hasn't
    been touched by the v1_4 back-fill patch yet is let through rather than
    blocked.
    """
    if doc.doctype not in ("Purchase Invoice", "Purchase Order", "Purchase Receipt"):
        return

    for row in (getattr(doc, "items", []) or []):
        item_code = getattr(row, "item_code", None)
        if not item_code:
            continue
        is_purchase_item = frappe.db.get_value("Item", item_code, "is_purchase_item")
        if is_purchase_item is not None and not is_purchase_item:
            frappe.throw(_(
                "Row {0}: Item {1} is not marked as a Purchase Item and cannot be added to a {2}."
            ).format(row.idx, frappe.bold(item_code), doc.doctype))


def _check_credit_limit(doc):
    """
    Block Sales Invoice submission if the customer's outstanding balance
    plus this invoice would exceed their configured credit limit.
    Only applies to Sales Invoices where the customer has a non-zero credit_limit.
    """
    if doc.doctype != "Sales Invoice":
        return

    customer = getattr(doc, "customer", None)
    if not customer:
        return

    credit_limit = flt(frappe.db.get_value("Customer", customer, "credit_limit"))
    if not credit_limit:
        return  # no limit configured — allow

    # Sum all outstanding invoices for this customer
    outstanding = flt(frappe.db.sql("""
        SELECT COALESCE(SUM(outstanding_amount), 0)
        FROM `tabSales Invoice`
        WHERE customer = %s AND docstatus = 1 AND outstanding_amount > 0
    """, (customer,))[0][0])

    new_total = outstanding + flt(doc.grand_total)
    if new_total > credit_limit:
        frappe.throw(_(
            "Credit limit exceeded for customer <b>{0}</b>. "
            "Limit: {1}, Current outstanding: {2}, This invoice: {3}, "
            "Total would be: {4}. Please collect pending payments or increase the credit limit."
        ).format(
            customer,
            frappe.bold(frappe.format_value(credit_limit, {"fieldtype": "Currency"})),
            frappe.bold(frappe.format_value(outstanding, {"fieldtype": "Currency"})),
            frappe.bold(frappe.format_value(flt(doc.grand_total), {"fieldtype": "Currency"})),
            frappe.bold(frappe.format_value(new_total, {"fieldtype": "Currency"})),
        ))


def _check_required_accounts(doc):
    """On submit, ensure the accounts that drive GL entries are set."""
    checks = {
        "Sales Invoice":    [("debit_to", "Debit To (AR)"), ("income_account", "Income Account")],
        "Purchase Invoice": [("credit_to", "Credit To (AP)"), ("expense_account", "Expense Account")],
        "Payment Entry":    [("paid_from", "Paid From"), ("paid_to", "Paid To")],
        "Credit Note":      [("debit_to", "Debit To (AR)"), ("income_account", "Income Account")],
    }
    for field, label in checks.get(doc.doctype, []):
        if not getattr(doc, field, None):
            frappe.throw(_(
                "'{0}' is required before submitting {1}"
            ).format(label, doc.doctype))


def check_budget_for_doc(doc):
    """
    Check if this document would cause the cost center's spend to exceed its budget
    or cross the warning threshold, based on the cost center's budget settings.
    """
    if doc.doctype not in ("Purchase Invoice", "Expense", "Expense Claim", "Journal Entry"):
        return

    # Debit notes / returns decrease overall spending, so they are exempt from budget enforcement
    if getattr(doc, "is_return", 0):
        return

    from zoho_books_clone.api.books_data import get_cost_center_spend

    def validate_cc_budget(cost_center, amount):
        if not cost_center or amount <= 0:
            return

        if not frappe.db.exists("Cost Center", cost_center):
            return

        cc = frappe.get_doc("Cost Center", cost_center)
        if cc.disabled or not cc.budget or cc.budget_action == "None":
            return

        company = getattr(doc, "company", None) or frappe.defaults.get_user_default("company")
        current_spend = get_cost_center_spend(company).get(cost_center, 0.0)
        new_spend = current_spend + amount

        if new_spend > cc.budget:
            msg = _(
                "Cost Center <b>{0}</b> has exceeded its budget.<br>"
                "Annual Budget: {1}<br>"
                "Current Spent: {2}<br>"
                "New Transaction Amount: {3}<br>"
                "Total Spent would be: {4}"
            ).format(
                cost_center,
                frappe.bold(frappe.format_value(cc.budget, {"fieldtype": "Currency"})),
                frappe.bold(frappe.format_value(current_spend, {"fieldtype": "Currency"})),
                frappe.bold(frappe.format_value(amount, {"fieldtype": "Currency"})),
                frappe.bold(frappe.format_value(new_spend, {"fieldtype": "Currency"})),
            )
            if cc.budget_action == "Stop":
                frappe.throw(msg, title=_("Budget Exceeded"))
            elif cc.budget_action == "Warn":
                if not getattr(doc.flags, "ignore_budget_warning", False):
                    frappe.throw("BUDGET_WARNING: " + msg, title=_("Budget Warning"))
        elif cc.alert_pct and new_spend >= cc.budget * (flt(cc.alert_pct) / 100.0):
            msg = _(
                "Budget Warning: Cost Center <b>{0}</b> has reached {1}% of its budget.<br>"
                "Annual Budget: {2}<br>"
                "Current Spent: {3}<br>"
                "New Transaction Amount: {4}<br>"
                "Total Spent: {5}"
            ).format(
                cost_center,
                cc.alert_pct,
                frappe.bold(frappe.format_value(cc.budget, {"fieldtype": "Currency"})),
                frappe.bold(frappe.format_value(current_spend, {"fieldtype": "Currency"})),
                frappe.bold(frappe.format_value(amount, {"fieldtype": "Currency"})),
                frappe.bold(frappe.format_value(new_spend, {"fieldtype": "Currency"})),
            )
            if not getattr(doc.flags, "ignore_budget_warning", False):
                frappe.throw("BUDGET_WARNING: " + msg, title=_("Budget Alert"))

    # Gather cost centers and their transaction amounts
    cc_amounts = {}
    if doc.doctype == "Purchase Invoice":
        cc = getattr(doc, "cost_center", None)
        if cc:
            cc_amounts[cc] = cc_amounts.get(cc, 0.0) + flt(doc.grand_total)
    elif doc.doctype == "Expense":
        cc = getattr(doc, "cost_center", None)
        if cc:
            cc_amounts[cc] = cc_amounts.get(cc, 0.0) + (flt(doc.total_amount) or flt(doc.amount))
    elif doc.doctype == "Expense Claim":
        cc = getattr(doc, "cost_center", None)
        if cc:
            cc_amounts[cc] = cc_amounts.get(cc, 0.0) + flt(doc.total_claimed_amount)
    elif doc.doctype == "Journal Entry":
        for row in getattr(doc, "accounts", []):
            row_cc = getattr(row, "cost_center", None) or getattr(doc, "cost_center", None)
            if row_cc:
                account_type = frappe.db.get_value("Account", row.account, "account_type")
                if account_type not in ('Receivable', 'Payable', 'Bank', 'Cash'):
                    net_amount = flt(row.debit) - flt(row.credit)
                    cc_amounts[row_cc] = cc_amounts.get(row_cc, 0.0) + net_amount

    # Validate budget for each cost center
    for cc, amt in cc_amounts.items():
        if amt > 0:
            validate_cc_budget(cc, amt)


# ─── Helper ───────────────────────────────────────────────────────────────────

def _posting_date_field(doc) -> str | None:
    """Return the name of the date field used as posting date for this doctype."""
    return {
        "Sales Invoice":    "posting_date",
        "Purchase Invoice": "posting_date",
        "Payment Entry":    "payment_date",
        "Journal Entry":    "posting_date",
        "Credit Note":      "posting_date",
        "Expense":          "posting_date",
        "Expense Claim":    "claim_date",
        # Phase 2: goods and banking documents added to central_validator
        "Purchase Receipt": "posting_date",
        "Stock Entry":      "posting_date",
        "Bank Transaction": "date",
        "Purchase Order":   "transaction_date",
        # Phase 3: pre-sales and GST documents added so Books lock date
        # and fiscal-year period lock are enforced consistently.
        "Sales Order":      "transaction_date",
        "Quotation":        "transaction_date",
        "Delivery Note":    "posting_date",
        "TDS Entry":        "date",
    }.get(doc.doctype)


def _check_fiscal_year_period_lock(doc):
    """
    Block saves/submits when the posting date falls within a locked period
    on the matching Fiscal Year record (lock_date field).
    """
    if getattr(doc, "voucher_type", None) == "Opening Entry":
        return

    date_field = _posting_date_field(doc)
    company = getattr(doc, "company", None)
    if not date_field or not company:
        return

    posting_date = getattr(doc, date_field, None)
    if not posting_date:
        return

    # Find the fiscal year covering this posting date for this company
    fy = frappe.db.sql("""
        SELECT name, lock_date FROM `tabFiscal Year`
        WHERE (LOWER(company) = LOWER(%s) OR company IS NULL OR company = '')
          AND year_start_date <= %s
          AND year_end_date   >= %s
        ORDER BY year_start_date DESC
        LIMIT 1
    """, (company, posting_date, posting_date), as_dict=True)

    if not fy or not fy[0].get("lock_date"):
        return

    if getdate(posting_date) <= getdate(fy[0]["lock_date"]):
        frappe.throw(_(
            "The accounting period up to {0} is locked in Fiscal Year {1}. "
            "You cannot create or edit {2} documents dated on or before this date. "
            "Unlock the period in Fiscal Years settings to proceed."
        ).format(
            frappe.bold(str(fy[0]["lock_date"])),
            frappe.bold(fy[0]["name"]),
            doc.doctype,
        ))