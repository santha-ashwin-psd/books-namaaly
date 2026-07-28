from __future__ import annotations
import frappe
from frappe.utils import flt


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
        "description":      description,
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
    """Create a Bank Transaction row mirroring a submitted Payment Entry's
    bank leg. See create_bank_transaction_row for the full rationale.
    """
    if pe.payment_type == "Receive":
        bank_account_name = pe.paid_to
        deposit    = flt(pe.paid_amount)
        withdrawal = 0.0
    else:  # Pay
        bank_account_name = pe.paid_from
        deposit    = 0.0
        withdrawal = flt(pe.paid_amount)

    return create_bank_transaction_row(
        bank_account_gl=bank_account_name,
        date=pe.payment_date or pe.posting_date,
        credit=deposit,
        debit=withdrawal,
        company=pe.company,
        currency=pe.currency or "INR",
        description=pe.remarks or f"Payment Entry {pe.name}",
        reference_number=pe.reference_no or pe.name,
        payment_entry=pe.name,
    )


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
        WHERE paid_amount = %s
          AND ABS(DATEDIFF(payment_date, %s)) <= 2
          AND docstatus = 1
          AND name NOT IN (
              SELECT payment_entry FROM `tabBank Transaction`
              WHERE payment_entry IS NOT NULL AND payment_entry != ''
          )
        LIMIT 1
    """, (amount, txn["date"]), as_dict=True)
    return result[0].name if result else None


@frappe.whitelist()
def find_matching_payment(
    bank_account: str, amount: float, date: str, reference: str | None = None
) -> list[dict]:
    """Return candidate Payment Entries for a bank transaction."""
    conditions = ["docstatus = 1", "paid_amount = %(amount)s"]
    params = {"amount": flt(amount)}

    if reference:
        conditions.append("(reference_no = %(ref)s OR reference_no LIKE %(ref_like)s)")
        params["ref"]      = reference
        params["ref_like"] = f"%{reference}%"

    where = " AND ".join(conditions)
    return frappe.db.sql(f"""
        SELECT name, payment_date, paid_amount, party, payment_type, mode_of_payment
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