"""
Customer / Supplier opening balances — posted as real GL, not just a field.

Problem this fixes
-------------------
`Customer.opening_balance` / `Supplier.opening_balance` used to be a bare
Currency field with no accounting weight behind it. Some read paths added it
into their totals by hand (Customers.vue list KPI, the detail-drawer summary
card); others didn't (the Statement tab, the vendor statement, the dashboard
aging buckets and receivables/payables KPIs, the Balance Sheet/Trial Balance).
Whichever endpoint you looked at, the answer disagreed — and the amount never
touched the General Ledger at all, so it was invisible to the Balance Sheet
and couldn't be partially settled like a real invoice.

Fix
---
Mirror what Zoho Books / ERPNext actually do: an opening balance is a real,
submitted, dated transaction against the party's control account.

    Customer (owes us):   Dr Accounts Receivable (party-tagged)  /  Cr Opening Balance Equity
    Supplier (we owe):    Dr Opening Balance Equity              /  Cr Accounts Payable (party-tagged)
    (flipped for a negative opening_balance — a credit balance)

posted via the existing Journal Entry doctype using its already-present but
unused `voucher_type = "Opening Entry"` (see journal_entry.py — it's exempt
from the fiscal-year-must-exist check, clearly built for exactly this and
never wired up to anything).

Once it's a real GL entry with `party_type`/`party` set, it becomes the single
source of truth. Every place that currently reads `Customer.opening_balance`
by hand should instead call `get_opening_balance()` below, so there's exactly
one code path instead of six slightly-different ones.

No new fields on Customer/Supplier are needed to track "the" opening JE for
update/cancel — we tag the party-side row with a distinguishing
`reference_type` ("Customer Opening Balance" / "Supplier Opening Balance")
and `reference_name` = the party, and look it up by that when the balance
changes.
"""
from __future__ import annotations
import frappe
from frappe.utils import flt, today


_REF_TYPE = {"Customer": "Customer Opening Balance", "Supplier": "Supplier Opening Balance"}
_CONTROL_ACCOUNT_TYPE = {"Customer": "Receivable", "Supplier": "Payable"}


def get_opening_balance(party_type: str, party: str) -> float:
    """Single source of truth for a party's opening balance amount.

    Every outstanding/statement/aging/dashboard query should call this
    instead of reading the `opening_balance` field directly — that's what
    let the Statement tab and vendor statement silently diverge from the
    list-page totals before this fix.
    """
    doctype = party_type if party_type in ("Customer", "Supplier") else None
    if not doctype:
        return 0.0
    return flt(frappe.db.get_value(doctype, party, "opening_balance") or 0)


def get_total_opening_balance(party_type: str, company: str) -> float:
    """Sum of all opening balances for every Customer/Supplier of `company`.
    Used by dashboard/aging totals, which aggregate across parties rather
    than looking at one at a time."""
    doctype = party_type if party_type in ("Customer", "Supplier") else None
    if not doctype:
        return 0.0
    total = frappe.db.sql(f"""
        SELECT COALESCE(SUM(opening_balance), 0) FROM `tab{doctype}`
        WHERE books_company=%s AND opening_balance IS NOT NULL
    """, company)
    return flt(total[0][0]) if total else 0.0


def _find_existing_opening_je(party_type: str, party: str) -> str | None:
    """The currently *active* (submitted, docstatus=1) opening JE for this
    party, if any.

    Must filter to docstatus=1 and order deterministically: every past
    sync_party_opening_balance() call leaves its cancelled JE's child row
    behind too (cancel never deletes, only reverses — correct for audit
    trail). Without the docstatus filter, a party edited more than once
    ends up with several "Journal Entry Account" rows sharing the same
    reference_type/reference_name — the *cancelled* ones from earlier
    edits and exactly one *submitted* one. `frappe.db.get_value` with no
    ORDER BY has no guaranteed row order, so it could return an
    already-cancelled JE; the caller would then see docstatus != 1, skip
    cancelling anything, and post a brand-new JE on top of the still-active
    one from the previous edit — silently doubling the GL balance.
    """
    return frappe.db.get_value(
        "Journal Entry Account",
        {"reference_type": _REF_TYPE[party_type], "reference_name": party, "docstatus": 1},
        "parent",
        order_by="creation desc",
    )


def _get_control_account(party_type: str, company: str) -> str | None:
    return frappe.db.get_value(
        "Account",
        {"account_type": _CONTROL_ACCOUNT_TYPE[party_type], "company": company, "is_group": 0},
        "name",
        order_by="name asc",
    )


def _get_opening_balance_equity_account(company: str) -> str | None:
    """Find (or create) "Opening Balance Equity - {company}", mirroring the
    account-seeding pattern already used in books_setup/install.py."""
    existing = frappe.db.get_value(
        "Account",
        {"account_name": "Opening Balance Equity", "company": company, "is_group": 0},
        "name",
    )
    if existing:
        return existing

    equity_parent = frappe.db.get_value(
        "Account", {"account_name": "Equity", "company": company, "is_group": 1}, "name"
    )
    try:
        acc = frappe.get_doc({
            "doctype":        "Account",
            "account_name":   "Opening Balance Equity",
            "account_type":   "Equity",
            "parent_account": equity_parent or "",
            "is_group":       0,
            "company":        company,
            "currency":       "INR",
        })
        acc.insert(ignore_permissions=True)
        return acc.name
    except Exception as e:
        # Most likely cause: another save for the same (new) company created
        # this account a moment ago (DuplicateEntryError) — re-check for it
        # before giving up, or that party's opening balance would silently
        # never get posted (nothing else re-triggers this sync later).
        retry = frappe.db.get_value(
            "Account",
            {"account_name": "Opening Balance Equity", "company": company, "is_group": 0},
            "name",
        )
        if retry:
            return retry
        frappe.log_error(str(e), "Opening Balance Equity account create")
        return None


def guard_opening_balance_delete(party_type: str, party: str) -> None:
    """Block deleting a Customer/Supplier that still has a submitted opening
    Journal Entry referencing it — otherwise the JE (and the GL balance it
    posted) survives as an orphan pointing at a party that no longer exists,
    with a party-tagged GL row that can never be reconciled or explained.
    Call from Customer/Supplier.on_trash().
    """
    if party_type not in ("Customer", "Supplier"):
        return
    existing = _find_existing_opening_je(party_type, party)
    if existing:
        frappe.throw(
            frappe._(
                "Cannot delete {0} {1}: it has an active opening balance entry ({2}). "
                "Set the opening balance to 0 and save first, so it can be cancelled."
            ).format(party_type, party, existing)
        )


def get_opening_balance_outstanding(party_type: str, party: str) -> float:
    """How much of the party's opening-balance JE is still unpaid.

    There's no `outstanding_amount` field on Journal Entry (unlike Sales/
    Purchase Invoice), so this is computed on the fly: the original
    party-row amount on the opening JE, minus whatever's already been
    allocated to it by submitted Payment Entries.
    """
    je = _find_existing_opening_je(party_type, party)
    if not je:
        return 0.0
    row = frappe.db.get_value(
        "Journal Entry Account",
        {"parent": je, "reference_type": _REF_TYPE[party_type], "reference_name": party},
        ["debit", "credit"], as_dict=True,
    )
    if not row:
        return 0.0
    original = abs(flt(row.debit) - flt(row.credit))
    paid = flt(frappe.db.sql("""
        SELECT COALESCE(SUM(per.allocated_amount), 0)
        FROM `tabPayment Entry Reference` per
        INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent
        WHERE per.reference_doctype = 'Journal Entry'
          AND per.reference_name = %s
          AND pe.docstatus = 1
    """, je)[0][0])
    return max(0.0, original - paid)


def guard_opening_balance_edit(party_type: str, party: str) -> None:
    """Block changing a Customer/Supplier's opening_balance once a payment has
    already been recorded against its opening Journal Entry.

    sync_party_opening_balance() reposts a changed opening balance by
    cancelling the old JE and posting a fresh one — but Frappe refuses to
    cancel a Journal Entry that a submitted Payment Entry still references,
    and that refusal (a raw LinkExistsError) used to leak straight to the
    user as a confusing "Cannot delete or cancel because ... is linked with
    Payment Entry ..." toast, with the Customer/Supplier record left
    silently unsaved. Catching it here, in validate() rather than the
    on_update() ledger-sync step, means it blocks the save with a clear
    explanation instead of getting swallowed or surfacing raw.
    """
    if party_type not in ("Customer", "Supplier"):
        return
    je = _find_existing_opening_je(party_type, party)
    if not je:
        return
    payments = frappe.db.sql("""
        SELECT DISTINCT pe.name
        FROM `tabPayment Entry Reference` per
        INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent
        WHERE per.reference_doctype = 'Journal Entry'
          AND per.reference_name = %s
          AND pe.docstatus = 1
    """, je, as_dict=True)
    if not payments:
        return
    frappe.throw(
        frappe._(
            "Cannot change the opening balance for {0}: it has already been paid "
            "(via Payment Entry {1}). Cancel that payment first, then update the "
            "opening balance."
        ).format(party, ", ".join(p.name for p in payments)),
        title=frappe._("Opening Balance Already Paid"),
    )


@frappe.whitelist()
def get_opening_balance_payment_info(party_type: str, party: str) -> dict:
    """Feeds the "Pay" button on the Customer/Supplier detail page: is there
    an active opening JE, how much is still outstanding on it, and which
    accounts should a Payment Entry against it use."""
    if party_type not in ("Customer", "Supplier"):
        frappe.throw(frappe._("Invalid party type"))

    je = _find_existing_opening_je(party_type, party)
    if not je:
        return {"has_opening_je": False}

    company = frappe.db.get_value("Journal Entry", je, "company")
    outstanding = get_opening_balance_outstanding(party_type, party)
    party_account = _get_control_account(party_type, company)
    bank_cash_accounts = frappe.get_all(
        "Account",
        filters={"account_type": ["in", ["Bank", "Cash"]], "company": company, "is_group": 0},
        fields=["name", "account_type"],
        order_by="account_type asc, name asc",
    )
    return {
        "has_opening_je": True,
        "journal_entry": je,
        "outstanding": outstanding,
        "party_account": party_account,
        "company": company,
        "bank_cash_accounts": bank_cash_accounts,
    }


def sync_party_opening_balance(party_type: str, party: str, company: str | None = None) -> None:
    """Reconcile the GL with the current value of Customer/Supplier.opening_balance.

    Idempotent — safe to call on every save. Cancels the previous opening
    Journal Entry (if any) and, if the new balance is non-zero, posts a fresh
    one dated today. (A cancel + repost keeps this simple and auditable;
    amending in place would need to fight Frappe's submitted-doc immutability
    for a field that changes rarely.)
    """
    if party_type not in ("Customer", "Supplier"):
        return

    # Row-level lock on the party for the rest of this DB transaction (same
    # pattern as stock_ledger_entry.py / work_order_engine.py). Two saves of
    # the same Customer/Supplier landing at the same instant (double-click,
    # two tabs) would otherwise both read "no active JE yet" via
    # _find_existing_opening_je() before either had committed, and both post
    # a fresh JE — doubling the GL balance. Serializing here means the
    # second call blocks until the first commits, then sees the first's
    # submitted JE and cancels it correctly instead of stacking on top.
    frappe.db.sql(f"SELECT name FROM `tab{party_type}` WHERE name=%s FOR UPDATE", party)

    amount = get_opening_balance(party_type, party)

    # 1. Cancel any previous opening entry for this party — the old amount is
    #    no longer valid whether the new one is zero or just different.
    # Preserve its posting_date (an opening balance should stay dated at
    # whenever it was first set, e.g. the books' start date — not silently
    # drift to "today" every time someone re-saves the customer, or a
    # Balance Sheet run as of a past date would understate/omit it).
    old_je = _find_existing_opening_je(party_type, party)
    posting_date = None
    if old_je and frappe.db.exists("Journal Entry", old_je):
        je_doc = frappe.get_doc("Journal Entry", old_je)
        posting_date = je_doc.posting_date
        if je_doc.docstatus == 1:
            try:
                je_doc.cancel()
            except Exception as e:
                # Do NOT fall through to posting a new JE — the old one is
                # still active, so doing so would double the GL balance.
                # Leave Customer/Supplier.opening_balance as the source of
                # truth showing the *intended* value; the mismatch with GL
                # will surface on the next successful sync attempt.
                frappe.log_error(str(e), f"Cancel opening JE {old_je} for {party}")
                return

    if not amount:
        return

    if not company:
        company = frappe.db.get_value(party_type, party, "books_company") or None
    if not company:
        try:
            company = frappe.db.get_single_value("Books Settings", "default_company")
        except Exception:
            company = None
    if not company:
        frappe.log_error(f"No company resolvable for {party_type} {party}", "Opening Balance sync")
        return

    party_account = _get_control_account(party_type, company)
    if not party_account:
        frappe.log_error(
            f"No {_CONTROL_ACCOUNT_TYPE[party_type]} account found for company {company}",
            "Opening Balance sync",
        )
        return
    equity_account = _get_opening_balance_equity_account(company)
    if not equity_account:
        return

    # Positive opening_balance: Customer owes us / we owe Supplier (normal case).
    # Negative: a credit balance — flip the debit/credit columns, never store
    # a negative amount in a ledger column.
    debit_amt  = amount if amount > 0 else 0
    credit_amt = -amount if amount < 0 else 0

    if party_type == "Customer":
        party_row   = {"debit": debit_amt, "credit": credit_amt}
        equity_row  = {"debit": credit_amt, "credit": debit_amt}
    else:
        # Supplier: a positive opening_balance is money we owe them, i.e. a
        # credit to Accounts Payable, so the columns are swapped vs Customer.
        party_row   = {"debit": credit_amt, "credit": debit_amt}
        equity_row  = {"debit": debit_amt, "credit": credit_amt}

    party_name = frappe.db.get_value(
        party_type, party, "customer_name" if party_type == "Customer" else "supplier_name"
    ) or party

    je = frappe.get_doc({
        "doctype":      "Journal Entry",
        "naming_series": "JE-.YYYY.-",
        "voucher_type": "Opening Entry",
        "posting_date": posting_date or today(),
        "company":      company,
        "remark":       f"Opening balance for {party_name} ({party})",
        "accounts": [
            {
                "account":         party_account,
                "party_type":      party_type,
                "party":           party,
                "debit":           party_row["debit"],
                "credit":          party_row["credit"],
                "reference_type":  _REF_TYPE[party_type],
                "reference_name":  party,
                "remarks":         f"Opening balance — {party_name}",
            },
            {
                "account": equity_account,
                "debit":   equity_row["debit"],
                "credit":  equity_row["credit"],
                "remarks": f"Opening balance offset — {party_name}",
            },
        ],
    })
    je.insert(ignore_permissions=True)
    je.submit()