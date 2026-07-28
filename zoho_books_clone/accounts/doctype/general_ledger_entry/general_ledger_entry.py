import frappe
from frappe import _
from frappe.utils import flt, today as _today
from frappe.model.document import Document


class GeneralLedgerEntry(Document):
    pass


# ─── Public API ───────────────────────────────────────────────────────────────

def make_gl_entries(gl_map: list[dict], cancel: bool = False) -> list[str]:
    """
    Create or reverse General Ledger Entries.

    Creation: each dict must have account, debit, credit, voucher_type,
              voucher_no, posting_date, company.
    Cancellation: pass [{"voucher_type": "...", "voucher_no": "..."}]
                  Entries are REVERSED (not deleted) to preserve audit trail.

    Returns the list of newly-created GL Entry names, in the same order as
    gl_map, when cancel=False (empty list on cancel — reversal touches
    existing rows rather than returning new ones). Existing callers that
    ignore the return value are unaffected.
    """
    if not cancel:
        _validate_gl_balance(gl_map)

    affected_accounts: set[str] = set()
    created_names: list[str] = []

    for entry in gl_map:
        if cancel:
            accounts = _reverse_gl_entries(
                entry.get("voucher_type"), entry.get("voucher_no")
            )
            affected_accounts.update(accounts)
        else:
            account = entry.get("account")
            if not account:
                frappe.throw(_("GL entry missing 'account' field: {0}").format(entry))
            created_names.append(_create_gl_entry(entry))
            affected_accounts.add(account)

    for account in affected_accounts:
        _update_account_balance(account)

    return created_names


def set_voucher_gl_suspended(voucher_type: str, voucher_no: str, suspended: bool) -> None:
    """
    Toggle whether an already-posted voucher's GL entries count toward
    account balances, without touching the entries themselves.

    Used for reconciliation-style linking — e.g. matching a Bank Transaction
    to a Payment Entry — where the same real-world cash movement must not be
    counted twice. The linked voucher's own entries are suspended
    (is_cancelled=1) while the match holds, and restored (is_cancelled=0) if
    the match is later undone. Unlike reverse_voucher(), this doesn't write
    audit-trail reversal rows and is safe to call repeatedly in either
    direction as a match is made and unmade.
    """
    frappe.db.sql("""
        UPDATE `tabGeneral Ledger Entry`
        SET is_cancelled = %s
        WHERE voucher_type = %s AND voucher_no = %s AND is_reversal = 0
    """, (1 if suspended else 0, voucher_type, voucher_no))

    affected = frappe.db.sql("""
        SELECT DISTINCT account FROM `tabGeneral Ledger Entry`
        WHERE voucher_type = %s AND voucher_no = %s AND is_reversal = 0
    """, (voucher_type, voucher_no), as_dict=True)
    for row in affected:
        _update_account_balance(row.account)


def recompute_outstanding_from_gl(doctype: str, docname: str) -> float:
    """
    Compute the true outstanding amount for an invoice by comparing
    what the GL says the receivable/payable balance is for this voucher.

    Returns the outstanding amount and writes it back to the document.
    """
    # Determine which account holds the outstanding (debit_to / credit_to)
    party_account = frappe.db.get_value(
        doctype, docname,
        "debit_to" if doctype == "Sales Invoice" else "credit_to"
    )
    if not party_account:
        return 0.0

    # For Sales Invoice: AR was debited on submit; payments credit it.
    # Outstanding = net debit remaining on that account for this voucher_no.
    result = frappe.db.sql("""
        SELECT COALESCE(SUM(debit) - SUM(credit), 0) AS outstanding
        FROM `tabGeneral Ledger Entry`
        WHERE account      = %s
          AND voucher_no   = %s
          AND is_cancelled = 0
    """, (party_account, docname), as_dict=True)

    # Also include payment entries that reference this doc
    payments = frappe.db.sql("""
        SELECT COALESCE(SUM(gle.credit) - SUM(gle.debit), 0) AS paid
        FROM `tabGeneral Ledger Entry` gle
        JOIN `tabPayment Entry Reference` per
          ON per.parent = gle.voucher_no
        WHERE gle.account      = %s
          AND per.reference_name = %s
          AND gle.is_cancelled = 0
          AND gle.voucher_type = 'Payment Entry'
    """, (party_account, docname), as_dict=True)

    # Also include Journal Entry contras that reference this doc (e.g. applying a
    # debit/credit note via a contra JE on AP/AR). Read directly from JEA — joining
    # to GLE on (voucher_no, account) would double-count when the same JE has
    # multiple rows on the party account.
    # For SI (AR side, outstanding=DR), a credit row settles it.
    # For PI (AP side, outstanding=CR), a debit row settles it.
    if doctype == "Purchase Invoice":
        je_settlement = frappe.db.sql("""
            SELECT COALESCE(SUM(jea.debit) - SUM(jea.credit), 0) AS settled
            FROM `tabJournal Entry Account` jea
            JOIN `tabJournal Entry` je ON je.name = jea.parent
            WHERE jea.account = %s AND jea.reference_name = %s
              AND je.docstatus = 1
        """, (party_account, docname), as_dict=True)
    else:
        je_settlement = frappe.db.sql("""
            SELECT COALESCE(SUM(jea.credit) - SUM(jea.debit), 0) AS settled
            FROM `tabJournal Entry Account` jea
            JOIN `tabJournal Entry` je ON je.name = jea.parent
            WHERE jea.account = %s AND jea.reference_name = %s
              AND je.docstatus = 1
        """, (party_account, docname), as_dict=True)

    invoice_debit  = flt(result[0].outstanding) if result else 0.0
    payment_credit = flt(payments[0].paid) if payments else 0.0
    je_credit      = flt(je_settlement[0].settled) if je_settlement else 0.0

    # ── Sign logic ────────────────────────────────────────────────────────────
    # Sales Invoice:  DR AR on submit  → invoice_debit  > 0 (net debit on AR)
    #                 CR AR on payment → payment_credit > 0 (net credit on AR)
    #                 outstanding = invoice_debit - payment_credit  ✓
    #
    # Purchase Invoice: CR AP on submit  → invoice_debit  < 0 (net credit, not debit, on AP)
    #                   DR AP on payment → payment_credit < 0 (net debit, not credit, on AP)
    #                   amount_owed  = -invoice_debit             (positive)
    #                   amount_paid  = -payment_credit            (positive)
    #                   outstanding  = amount_owed - amount_paid
    #                                = (-invoice_debit) - (-payment_credit)
    #                                = -invoice_debit + payment_credit      ← NOTE: + not -
    #
    #   BUG if you write "- payment_credit": since payment_credit is already negative,
    #   subtracting it ADDS to outstanding instead of reducing it.
    if doctype == "Purchase Invoice":
        outstanding = max(0.0, -invoice_debit + payment_credit - je_credit)
    else:
        outstanding = max(0.0, invoice_debit - payment_credit - je_credit)

    frappe.db.set_value(doctype, docname, "outstanding_amount", outstanding,
                        update_modified=False)
    return outstanding


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _validate_gl_balance(gl_map: list[dict]) -> None:
    """P0/Issue 2 — Reject unbalanced GL entry sets before posting."""
    total_debit  = sum(flt(e.get("debit",  0)) for e in gl_map)
    total_credit = sum(flt(e.get("credit", 0)) for e in gl_map)
    if abs(total_debit - total_credit) > 0.01:
        frappe.throw(_(
            "Unbalanced GL entries: total debit {0} ≠ total credit {1}. "
            "All debits must equal all credits."
        ).format(
            frappe.bold(f"₹{total_debit:,.2f}"),
            frappe.bold(f"₹{total_credit:,.2f}"),
        ))


def _reverse_gl_entries(voucher_type: str, voucher_no: str) -> set[str]:
    """
    P0/Issue 1 — Preserve audit trail by creating reversing entries
    instead of deleting the originals.
    Returns set of affected account names for balance refresh.
    """
    # Idempotency: if reversals already exist for this voucher, skip.
    already = frappe.db.sql("""
        SELECT COUNT(*) FROM `tabGeneral Ledger Entry`
        WHERE voucher_type = %s AND voucher_no = %s AND is_reversal = 1
    """, (voucher_type, voucher_no))[0][0]
    if already:
        return set()

    rows = frappe.db.sql("""
        SELECT name, account, debit, credit, party_type, party,
               cost_center, currency, company, fiscal_year, is_opening
        FROM `tabGeneral Ledger Entry`
        WHERE voucher_type = %s AND voucher_no = %s
          AND is_cancelled = 0 AND is_reversal = 0
    """, (voucher_type, voucher_no), as_dict=True)

    affected: set[str] = set()
    reversal_date = _today()

    for row in rows:
        # Mark the original entry as cancelled
        frappe.db.set_value(
            "General Ledger Entry", row.name, "is_cancelled", 1,
            update_modified=False
        )
        # Post a mirror entry with debit ↔ credit swapped, also marked cancelled
        # so reports (which filter is_cancelled=0) see net zero effect from the
        # cancelled voucher. Audit trail preserved: rows still exist with flags.
        _create_gl_entry({
            "account":      row.account,
            "debit":        flt(row.credit),   # swap
            "credit":       flt(row.debit),    # swap
            "voucher_type": voucher_type,
            "voucher_no":   voucher_no,
            "posting_date": reversal_date,
            "party_type":   row.party_type or "",
            "party":        row.party or "",
            "cost_center":  row.cost_center or "",
            "currency":     row.currency or "INR",
            "remarks":      f"Reversal of GL Entry {row.name}",
            "company":      row.company,
            "fiscal_year":  row.fiscal_year or "",
            "is_opening":   row.is_opening or 0,
            "is_reversal":  1,
            "is_cancelled": 1,
        })
        affected.add(row.account)

    return affected


def _create_gl_entry(entry: dict) -> str:
    doc = frappe.new_doc("General Ledger Entry")
    # Drop empty fiscal_year so Frappe doesn't try to validate a Link to ""
    clean = {k: v for k, v in entry.items() if not (k == "fiscal_year" and not v)}
    doc.update(clean)
    doc.flags.ignore_permissions = True
    doc.flags.ignore_mandatory   = True
    doc.insert()
    return doc.name


def _update_account_balance(account: str) -> None:
    """Recompute account balance from all active (non-cancelled) GL entries."""
    if not account:
        return
    res = frappe.db.sql("""
        SELECT COALESCE(SUM(debit) - SUM(credit), 0) AS balance
        FROM `tabGeneral Ledger Entry`
        WHERE account = %s AND is_cancelled = 0
    """, account, as_dict=True)
    balance = flt(res[0].balance) if res else 0.0
    frappe.db.set_value("Account", account, "balance", balance,
                        update_modified=False)