from __future__ import annotations
import frappe
from frappe.utils import flt

# Bank Transaction.description is a Data field -- Frappe hard-caps those at
# 140 characters and raises CharacterLengthExceededError on insert() rather
# than truncating for you. Keep a couple of chars of margin.
_DESCRIPTION_MAX_LEN = 140


def _clip_description(text):
    """Trim text to fit Bank Transaction.description's 140-char Data field
    limit, appending an ellipsis when it had to cut anything so it's obvious
    on screen that this is a shortened copy -- the full text always still
    lives on the source Payment/Journal Entry's own (unlimited-length)
    remarks field.
    """
    text = text or ""
    if len(text) <= _DESCRIPTION_MAX_LEN:
        return text
    return text[: _DESCRIPTION_MAX_LEN - 1].rstrip() + "…"


def create_bank_transaction_row(
    bank_account_gl, date, credit, debit, company,
    currency="INR", description="", reference_number="",
    payment_entry=None, journal_entry=None,
):
    """Create an Unreconciled Bank Transaction row mirroring a real GL
    movement on a bank account, so the Banking page — and later, a real
    imported bank statement — has something to reconcile against.

    This row's GL posting is always skipped on submit (see
    BankTransaction._post_gl, which returns immediately when payment_entry
    OR journal_entry is set) because whatever created this movement
    (Payment Entry, Journal Entry/Contra Entry, etc.) already posted the
    real Dr/Cr entries. This row is a reconciliation mirror only.

    Status is deliberately "Unreconciled": it represents what the books
    expect happened, not a confirmation from the bank. It only becomes
    Reconciled once a matching statement line is imported and
    _find_existing_bank_transaction_match links the two (see
    api/docs.py::import_bank_statement_csv). Marking it Reconciled here
    would make it invisible to that matcher.

    bank_account_gl: the COA account (not the Bank Account record) —
    resolved to a Bank Account here so callers don't need to.
    """
    # NOTE: company names can differ in casing between where a Payment Entry/
    # Expense resolves its `company` and how the Bank Account record stores
    # it (see the LOWER(company) fixes throughout api/books_data.py and
    # api/docs.py for the same root cause). An exact-match dict filter here
    # silently returns nothing whenever casing doesn't line up — which was
    # why Bank Transaction rows weren't appearing for Invoice/Bill payments
    # even though a matching Bank Account record existed. Match
    # case-insensitively instead.
    rows = frappe.db.sql(
        """SELECT name FROM `tabBank Account`
           WHERE LOWER(TRIM(gl_account)) = LOWER(TRIM(%s))
             AND LOWER(company) = LOWER(%s)
           LIMIT 1""",
        (bank_account_gl, company),
    )
    bank_acc = rows[0][0] if rows else None
    if not bank_acc:
        # No Bank Account record linked — skip silently for Cash (expected).
        # For a genuine Bank-type GL account this is a real setup gap (the
        # transaction posts fine, it just won't show up for reconciliation),
        # so log it instead of failing silently forever.
        acct_type = frappe.db.get_value("Account", bank_account_gl, "account_type")
        if acct_type == "Bank":
            frappe.log_error(
                title="Bank Transaction mirror skipped",
                message=(
                    f"No Bank Account record found linking GL account '{bank_account_gl}' "
                    f"(company '{company}'). Bank Transaction mirror skipped — create a "
                    f"Bank Account under Banking → Accounts with this GL account set."
                ),
            )
        return None

    bt = frappe.get_doc({
        "doctype":          "Bank Transaction",
        "date":             date,
        "bank_account":     bank_acc,
        "credit":           flt(credit),   # Bank statement convention: credit = money IN
        "debit":            flt(debit),    # Bank statement convention: debit  = money OUT
        "currency":         currency or "INR",
        # description is a Data field -- Frappe hard-caps those at 140 chars
        # and insert() throws (rather than silently truncating) if exceeded.
        # A payment covering many invoices/bills can easily build a longer
        # remarks string upstream (e.g. "Payment against INV-1, INV-2, ...")
        # -- truncate defensively here so that never blocks the Bank
        # Transaction mirror from being created. The full, untruncated text
        # always still lives on the source Payment/Journal Entry's own
        # remarks field, which has no such length limit.
        "description":      _clip_description(description),
        "reference_number": reference_number,
        "payment_entry":    payment_entry,
        "journal_entry":    journal_entry,
        "status":           "Unreconciled",  # awaiting confirmation from an imported bank statement
        "company":          company,
    })
    # This row only mirrors a movement whose real Dr/Cr GL entries were
    # already posted by the source document (Payment Entry, Journal Entry,
    # Expense, ...). Skip _post_gl explicitly rather than relying solely on
    # payment_entry/journal_entry being set — callers like Expense have no
    # Journal Entry/Payment Entry to link to and would otherwise fail Link
    # validation if we faked one in just to trip that check.
    bt.flags.skip_gl_posting = True
    bt.insert(ignore_permissions=True)
    bt.flags.ignore_permissions = True
    bt.submit()
    frappe.db.commit()
    return bt.name


def create_bank_transaction_from_payment_entry(pe):
    """Create Bank Transaction row(s) mirroring a submitted Payment Entry's
    bank leg. See create_bank_transaction_row for the full rationale.

    When bank_charges is set, this creates TWO separate Bank Transaction
    rows instead of one netted row — matching how the actual bank
    statement records it (the payment and the bank's charge show up as
    two distinct line items, not combined into one). The main row carries
    the full paid_amount; the charge row carries just the bank_charges
    amount as its own withdrawal, tagged with a distinct reference number
    so it doesn't collide with the main row during reconciliation/import
    matching. Together the two rows net out to the same real cash
    movement that post_payment_entry() posts to the Bank/Cash GL leg.

    Returns a list of the created Bank Transaction name(s) — one entry
    normally, two when bank_charges > 0.
    """
    bank_charges = flt(getattr(pe, "bank_charges", 0))
    ref = pe.reference_no or pe.name
    date = pe.payment_date or pe.posting_date

    if pe.payment_type == "Receive":
        bank_account_name = pe.paid_to
        main_deposit,    main_withdrawal    = flt(pe.paid_amount), 0.0
        charge_deposit,  charge_withdrawal  = 0.0, bank_charges
    else:  # Pay
        bank_account_name = pe.paid_from
        main_deposit,    main_withdrawal    = 0.0, flt(pe.paid_amount)
        charge_deposit,  charge_withdrawal  = 0.0, bank_charges

    names = [create_bank_transaction_row(
        bank_account_gl=bank_account_name,
        date=date,
        credit=main_deposit,
        debit=main_withdrawal,
        company=pe.company,
        currency=pe.currency or "INR",
        description=pe.remarks or f"Payment Entry {pe.name}",
        reference_number=ref,
        payment_entry=pe.name,
    )]

    if bank_charges:
        names.append(create_bank_transaction_row(
            bank_account_gl=bank_account_name,
            date=date,
            credit=charge_deposit,
            debit=charge_withdrawal,
            company=pe.company,
            currency=pe.currency or "INR",
            description=f"Bank charges — {pe.name}",
            reference_number=f"{ref}-CHG",
            payment_entry=pe.name,
        ))

    return [n for n in names if n]


def auto_match_bank_transactions():
    """Daily scheduler: try to auto-reconcile unmatched bank transactions.

    Only considers rows with no payment_entry yet (raw bank-fed movements
    that haven't been linked to anything). Rows auto-created from a
    Payment Entry submission (banking/utils.py::create_bank_transaction_
    from_payment_entry) already carry their payment_entry — they are
    intentionally left Unreconciled until a real imported bank statement
    line confirms them (see api/docs.py::import_bank_statement_csv).
    Matching them here against their own already-known PE would mark
    them Reconciled without any bank confirmation ever happening.
    """
    unmatched = frappe.get_all(
        "Bank Transaction",
        filters={
            "status": "Unreconciled",
            "docstatus": 1,
            "payment_entry": ["in", ["", None]],
        },
        fields=["name", "reference_number", "credit", "debit", "date", "bank_account"],
    )
    matched = 0
    for txn in unmatched:
        pe = _match_by_reference(txn) or _match_by_amount_and_date(txn)
        if pe:
            frappe.db.set_value("Bank Transaction", txn["name"], {
                "status": "Reconciled",
                "payment_entry": pe,
            })
            matched += 1
    if matched:
        frappe.db.commit()
    return matched


def _match_by_reference(txn: dict) -> str | None:
    if not txn.get("reference_number"):
        return None
    return frappe.db.get_value(
        "Payment Entry",
        {"reference_no": txn["reference_number"], "docstatus": 1},
        "name",
    )


def _match_by_amount_and_date(txn: dict) -> str | None:
    amount = flt(txn.get("credit") or txn.get("debit"))
    if not amount:
        return None
    result = frappe.db.sql("""
        SELECT name FROM `tabPayment Entry`
        WHERE (
            (payment_type = 'Receive' AND paid_amount - IFNULL(bank_charges, 0) = %s)
            OR (payment_type = 'Pay' AND paid_amount + IFNULL(bank_charges, 0) = %s)
        )
          AND ABS(DATEDIFF(payment_date, %s)) <= 2
          AND docstatus = 1
          AND name NOT IN (
              SELECT payment_entry FROM `tabBank Transaction`
              WHERE payment_entry IS NOT NULL AND payment_entry != ''
          )
        LIMIT 1
    """, (amount, amount, txn["date"]), as_dict=True)
    return result[0].name if result else None


@frappe.whitelist()
def find_matching_payment(
    bank_account: str, amount: float, date: str, reference: str | None = None
) -> list[dict]:
    """Return candidate Payment Entries for a bank transaction.

    Matches on the *net* bank-side amount (paid_amount adjusted for
    bank_charges) since that's what actually shows up on the bank statement,
    while still matching plain gross amounts for entries with no charges.
    """
    conditions = [
        "docstatus = 1",
        "("
        "  (payment_type = 'Receive' AND paid_amount - IFNULL(bank_charges, 0) = %(amount)s)"
        "  OR (payment_type = 'Pay' AND paid_amount + IFNULL(bank_charges, 0) = %(amount)s)"
        ")",
    ]
    params = {"amount": flt(amount)}

    if reference:
        conditions.append("(reference_no = %(ref)s OR reference_no LIKE %(ref_like)s)")
        params["ref"]      = reference
        params["ref_like"] = f"%{reference}%"

    where = " AND ".join(conditions)
    return frappe.db.sql(f"""
        SELECT name, payment_date, paid_amount, bank_charges, party, payment_type, mode_of_payment
        FROM `tabPayment Entry`
        WHERE {where}
          AND name NOT IN (
              SELECT COALESCE(payment_entry, '') FROM `tabBank Transaction`
              WHERE payment_entry IS NOT NULL
          )
        ORDER BY ABS(DATEDIFF(payment_date, %(date)s)) ASC
        LIMIT 10
    """, {**params, "date": date}, as_dict=True)


@frappe.whitelist()
def reconcile_transaction(bank_transaction: str, payment_entry: str) -> None:
    """Link a payment entry to a bank transaction and mark it reconciled."""
    if not frappe.db.exists("Payment Entry", payment_entry):
        frappe.throw(f"Payment Entry {payment_entry} not found")
    frappe.db.set_value("Bank Transaction", bank_transaction, {
        "status": "Reconciled",
        "payment_entry": payment_entry,
    })
    frappe.db.commit()