"""
Banking API — whitelisted endpoints for banking workflow operations.

Covers:
  - get_bank_accounts_with_balances: Bank accounts with GL-computed balances
  - get_bank_account: Fetch a single Bank Account document (full fields)
  - save_bank_account: Create or update a Bank Account (bypasses modified conflict)
  - bounce_cheque: GL reversal when a cheque bounces
  - post_bank_transfer: inter-account fund transfer with GL posting
  - create_bank_gl_entry: JE for unmatched bank transactions (charges, interest)
"""
import frappe
from frappe import _
from frappe.utils import flt, today
from zoho_books_clone.api.session import _get_company
from zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry import (
    make_gl_entries,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _bank_gl(bank_account: str) -> str:
    gl = frappe.db.get_value("Bank Account", bank_account, "gl_account")
    if not gl:
        frappe.throw(_("Bank Account {0} has no GL account linked.").format(bank_account))
    return gl


def _company(bank_account: str) -> str:
    co = frappe.db.get_value("Bank Account", bank_account, "company")
    return co or frappe.db.get_default("company") or ""


def _clear_other_defaults(company: str, keep_name: str) -> None:
    """Enforce a single global default Bank Account per company.

    The default flag picks which account is pre-selected when recording
    payments/deposits/transfers — so exactly one account may hold it. When one
    is marked default, un-mark every other account for the same company.
    """
    others = frappe.get_all(
        "Bank Account",
        filters={"company": company, "is_default": 1, "name": ["!=", keep_name]},
        pluck="name",
    )
    for nm in others:
        frappe.db.set_value("Bank Account", nm, "is_default", 0, update_modified=False)


def _ensure_gl_account(account_name: str, company: str, currency: str = "INR") -> str:
    """
    Return a leaf GL Account for a bank account, creating one if needed.

    A Bank Account is useless without a linked ledger account — every transfer,
    cheque, and bank-charge entry resolves it via _bank_gl(). When the caller
    doesn't supply one, we auto-create a leaf Account (account_type='Bank')
    under the company's Bank group, mirroring Zoho's behaviour where naming a
    bank silently provisions its ledger.
    """
    # Find the Bank group to parent under; fall back to any Asset group.
    parent = frappe.db.get_value(
        "Account", {"company": company, "is_group": 1, "account_type": "Bank"}, "name"
    ) or frappe.db.get_value(
        "Account", {"company": company, "is_group": 1, "account_type": "Asset"}, "name"
    )
    if not parent:
        frappe.throw(_(
            "No Bank or Asset group account found for company {0}. "
            "Create a group account in the Chart of Accounts first, "
            "or pick a GL account manually."
        ).format(company))

    # Account name autoname is "{account_name} - {company}" — reuse if it exists.
    candidate = f"{account_name} - {company}"
    if frappe.db.exists("Account", candidate):
        return candidate

    acc = frappe.get_doc({
        "doctype":        "Account",
        "account_name":   account_name,
        "parent_account": parent,
        "is_group":       0,
        "account_type":   "Bank",
        "currency":       currency or "INR",
        "company":        company,
    })
    acc.insert(ignore_permissions=True)
    return acc.name


def _recalc_balance(bank_account: str) -> float:
    """
    Compute the live balance for a Bank Account as:
        opening_balance  +  SUM(credit) - SUM(debit)  from submitted Bank Transactions

    This is always per-account (not per-GL-account) so accounts that share the
    same GL account each get their own correct number.
    Persists the result back to current_balance so the field stays up to date.
    """
    opening = flt(frappe.db.get_value("Bank Account", bank_account, "opening_balance") or 0)
    row = frappe.db.sql("""
        SELECT COALESCE(SUM(credit) - SUM(debit), 0) AS net
        FROM `tabBank Transaction`
        WHERE bank_account = %s AND docstatus = 1
    """, bank_account, as_dict=True)
    net = flt(row[0].net) if row else 0.0
    live = opening + net
    # Persist so the field is always fresh; skip modified-time update to avoid conflicts.
    frappe.db.set_value("Bank Account", bank_account, "current_balance", live, update_modified=False)
    return live


# ─── Endpoints ────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False)
def get_bank_account(name: str) -> dict:
    """
    Return the full Bank Account document for a single account.
    Attaches the live per-account balance (opening + Bank Transaction net).
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    doc = frappe.get_doc("Bank Account", name)
    d = doc.as_dict()

    # Always use the per-account live formula, not the shared GL aggregate.
    d["current_balance"] = _recalc_balance(name)
    d["balance"]         = d["current_balance"]

    # Reconciliation stats
    total = frappe.db.count("Bank Transaction", {"bank_account": name, "docstatus": 1})
    reconciled = frappe.db.count("Bank Transaction", {"bank_account": name, "docstatus": 1, "status": "Reconciled"})
    d["reconcile_pct"] = round(reconciled / total * 100) if total else 0
    d["txn_count"]     = total

    return d


@frappe.whitelist(allow_guest=False, methods=["POST"])
def save_bank_account(
    account_name: str,
    bank_name: str = "",
    account_number: str = "",
    ifsc_code: str = "",
    branch: str = "",
    account_holder_name: str = "",
    micr_code: str = "",
    currency: str = "INR",
    account_type: str = "Current",
    gl_account: str = "",
    status: str = "Active",
    is_default: int = 0,
    company: str = "",
    existing_name: str = "",   # Frappe document name when editing
    opening_balance: float = 0.0,
    current_balance: float = 0.0,
) -> dict:
    """
    Create or update a Bank Account document.

    Key difference from frappe.client.save:
      - Fetches the latest `modified` from the DB before saving so Frappe's
        optimistic-locking check ("document modified after you opened it") never fires.
      - Uses ignore_permissions=True so the Books Manager role can write.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    # Bank accounts are sensitive — require Banking-module write access (and not
    # a read-only role) instead of relying solely on ignore_permissions=True below.
    from zoho_books_clone.utils.tenancy import get_user_company
    from zoho_books_clone.utils.access import require_module
    require_module("banking", write=True)

    if not account_name.strip():
        frappe.throw(_("Account name is required"))

    if not company:
        company = _get_company(frappe.session.user)
    if not company:
        frappe.throw(_("No company configured. Please set a default company in Books Settings."))

    # Never let a user create/edit a bank account for another company.
    _user_company = get_user_company(frappe.session.user)
    if _user_company and company != _user_company:
        frappe.throw(_("You cannot manage bank accounts for another company."), frappe.PermissionError)

    # A bank account is unusable without a ledger account — auto-provision one
    # (Zoho-style) when the caller didn't supply it. On edit, preserve any
    # ledger already linked rather than minting a duplicate.
    if not (gl_account or "").strip():
        existing_gl = (
            frappe.db.get_value("Bank Account", existing_name, "gl_account")
            if existing_name else None
        )
        gl_account = existing_gl or _ensure_gl_account(account_name.strip(), company, currency)

    # ── UPDATE existing document ───────────────────────────────────────────────
    if existing_name and frappe.db.exists("Bank Account", existing_name):
        doc = frappe.get_doc("Bank Account", existing_name)

        # Sync the `modified` field to whatever is currently in the DB so
        # Frappe's TimestampMismatch check passes without needing a page refresh.
        db_modified = frappe.db.get_value("Bank Account", existing_name, "modified")
        if db_modified:
            doc.modified = db_modified

        doc.account_name         = account_name
        doc.bank_name            = bank_name
        doc.account_number       = account_number
        doc.ifsc_code            = ifsc_code
        doc.branch               = branch
        doc.account_holder_name  = account_holder_name
        doc.micr_code            = micr_code
        doc.currency             = currency or "INR"
        doc.account_type         = account_type or "Current"
        doc.gl_account           = gl_account
        doc.status               = status or "Active"
        doc.is_default           = int(is_default or 0)
        doc.company              = company
        doc.opening_balance      = flt(opening_balance)
        doc.current_balance      = flt(current_balance)

        doc.save(ignore_permissions=True)
        if doc.is_default:
            _clear_other_defaults(company, doc.name)
        frappe.db.commit()
        return doc.as_dict()

    # ── CREATE new document ────────────────────────────────────────────────────
    # If the user entered a starting balance in the "Current Balance" field but
    # left Opening Balance at 0, treat it as the opening balance so the recalc
    # formula (opening + transactions) produces the correct result.
    effective_opening = flt(opening_balance) or flt(current_balance)

    doc = frappe.get_doc({
        "doctype":             "Bank Account",
        "account_name":        account_name,
        "bank_name":           bank_name,
        "account_number":      account_number,
        "ifsc_code":           ifsc_code,
        "branch":              branch,
        "account_holder_name": account_holder_name,
        "micr_code":           micr_code,
        "currency":            currency or "INR",
        "account_type":        account_type or "Current",
        "gl_account":          gl_account,
        "status":              status or "Active",
        "is_default":          int(is_default or 0),
        "company":             company,
        "opening_balance":     effective_opening,
        "current_balance":     effective_opening,
    })
    doc.insert(ignore_permissions=True)
    if doc.is_default:
        _clear_other_defaults(company, doc.name)
    frappe.db.commit()
    return doc.as_dict()


@frappe.whitelist(allow_guest=False)
def get_account_ledger(account: str, from_date: str = None, to_date: str = None) -> dict:
    """Chronological GL trail for a single account (e.g. a Cash or Bank account),
    with a running balance — lets a user trace money as it moves in, out, and
    between accounts (e.g. Cash -> Petty Cash -> Expense).
    """
    if not account:
        frappe.throw(_("Account is required."))

    conditions = ["IFNULL(is_cancelled, 0) = 0", "account = %(account)s"]
    params = {"account": account}
    if from_date:
        conditions.append("posting_date >= %(from_date)s")
        params["from_date"] = from_date
    if to_date:
        conditions.append("posting_date <= %(to_date)s")
        params["to_date"] = to_date

    where = " AND ".join(conditions)

    opening = 0.0
    if from_date:
        opening = flt(frappe.db.sql(
            f"""
            SELECT SUM(debit) - SUM(credit)
            FROM `tabGeneral Ledger Entry`
            WHERE IFNULL(is_cancelled,0)=0 AND account=%(account)s AND posting_date < %(from_date)s
            """,
            params,
        )[0][0] or 0)

    rows = frappe.db.sql(
        f"""
        SELECT posting_date, voucher_type, voucher_no, party_type, party,
               debit, credit, remarks, creation
        FROM `tabGeneral Ledger Entry`
        WHERE {where}
        ORDER BY posting_date, creation
        """,
        params,
        as_dict=True,
    )

    balance = opening
    for row in rows:
        balance += flt(row.debit) - flt(row.credit)
        row["balance"] = balance
        if row.voucher_type in ("Payment Entry", "Journal Entry"):
            row["direction"] = "in" if flt(row.debit) > 0 else "out"

    return {
        "account": account,
        "opening_balance": opening,
        "closing_balance": balance,
        "entries": rows,
    }


@frappe.whitelist()
def get_bank_accounts_with_balances(company: str = None) -> list:
    """
    Return all Bank Accounts for the company with their live GL balance,
    reconciliation stats, and recent transactions count.
    """
    if not company:
        company = _get_company(frappe.session.user)

    # Always include the stored balance fields so we display the per-account value,
    # not a shared GL aggregate.
    _FIELDS = [
        "name", "account_name", "bank_name", "account_number", "ifsc_code",
        "gl_account", "currency", "is_default", "account_type",
        "opening_balance", "current_balance",
    ]

    accounts = frappe.get_all(
        "Bank Account",
        filters={"company": company} if company else {},
        fields=_FIELDS,
        order_by="is_default desc, creation asc",
        limit=100,
        ignore_permissions=True,
    )

    for a in accounts:
        # ── Balance: always compute dynamically as
        #   opening_balance + SUM(credit - debit from submitted Bank Transactions)
        # This is per-account so accounts sharing a GL account get distinct balances.
        # We also persist the result to current_balance so it's always fresh.
        opening = flt(a.get("opening_balance"))
        txn_row = frappe.db.sql("""
            SELECT COALESCE(SUM(credit) - SUM(debit), 0) AS net
            FROM `tabBank Transaction`
            WHERE bank_account = %s AND docstatus = 1
        """, a["name"], as_dict=True)
        net = flt(txn_row[0].net) if txn_row else 0.0
        live = opening + net
        a["balance"] = live
        a["current_balance"] = live
        # Persist silently — no modified-time bump to avoid conflicts.
        frappe.db.set_value("Bank Account", a["name"], "current_balance", live, update_modified=False)

        # Reconciliation percentage
        total = frappe.db.count("Bank Transaction",
            {"bank_account": a["name"], "docstatus": 1})
        reconciled = frappe.db.count("Bank Transaction",
            {"bank_account": a["name"], "docstatus": 1, "status": "Reconciled"})
        a["reconcile_pct"] = round(reconciled / total * 100) if total else 0
        a["txn_count"] = total

    return accounts


@frappe.whitelist(allow_guest=False, methods=["POST"])
def bounce_cheque(payment_entry: str) -> dict:
    """
    Reverse GL entries when a cheque bounces.
    The original Payment Entry GL (DR Bank / CR Payable or DR Receivable / CR Bank)
    is unwound by creating reversing GL entries.
    """
    from zoho_books_clone.utils.access import require_module
    require_module("banking", write=True)

    from zoho_books_clone.accounts.accounting_engine import reverse_voucher

    doc = frappe.get_doc("Payment Entry", payment_entry)
    if doc.docstatus != 1:
        frappe.throw(_("Payment Entry {0} is not submitted — cannot reverse.").format(payment_entry))

    reverse_voucher("Payment Entry", payment_entry)
    frappe.db.set_value("Payment Entry", payment_entry,
                        {"cheque_status": "Bounced", "cheque_cleared_date": None},
                        update_modified=True)
    frappe.db.commit()
    return {"payment_entry": payment_entry, "cheque_status": "Bounced", "status": "GL Reversed"}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def post_bank_transfer(
    from_account: str,
    to_account: str,
    amount: str,
    date: str = None,
    purpose: str = "",
    description: str = "",
) -> dict:
    """
    Transfer funds between two bank accounts.

    GL impact:
      DR  to_account.gl_account   (funds arrive)
      CR  from_account.gl_account (funds leave)

    Creates a Bank Transaction record on each account for reconciliation.
    No income/expense impact — pure asset swap.
    """
    from zoho_books_clone.utils.access import require_module
    require_module("banking", write=True)

    amount_f = flt(amount)
    if amount_f <= 0:
        frappe.throw(_("Transfer amount must be positive."))
    if from_account == to_account:
        frappe.throw(_("Source and destination account must be different."))

    date = date or today()
    from_gl = _bank_gl(from_account)
    to_gl   = _bank_gl(to_account)
    company = _company(from_account)
    remark  = description or f"Transfer from {from_account} to {to_account}"

    # Shared reference so the two legs can be grouped back into one transfer
    # (for the Transfers list / delete). Stored on reference_number of both legs.
    xref = "TRF-" + frappe.generate_hash(length=10)

    # Bank Transaction — source account (withdrawal / debit).
    # skip_gl_posting flag: this API posts a single combined GL set below,
    # so the per-transaction _post_gl must not run (would double-post).
    bt_from = frappe.get_doc({
        "doctype": "Bank Transaction",
        "bank_account": from_account,
        "date": date,
        "description": f"Transfer to {to_account}" + (f" — {description}" if description else ""),
        "debit": amount_f,
        "credit": 0,
        "transaction_type": "Transfer",
        "status": "Reconciled",
        "reference_number": xref,
        "custom_transfer_purpose": purpose,
        "company": company,
    })
    bt_from.flags.ignore_permissions = True
    bt_from.flags.skip_gl_posting = True
    bt_from.insert()
    bt_from.submit()

    # Bank Transaction — destination account (deposit / credit)
    bt_to = frappe.get_doc({
        "doctype": "Bank Transaction",
        "bank_account": to_account,
        "date": date,
        "description": f"Transfer from {from_account}" + (f" — {description}" if description else ""),
        "debit": 0,
        "credit": amount_f,
        "transaction_type": "Transfer",
        "status": "Reconciled",
        "reference_number": xref,
        "custom_transfer_purpose": purpose,
        "company": company,
    })
    bt_to.flags.ignore_permissions = True
    bt_to.flags.skip_gl_posting = True
    bt_to.insert()
    bt_to.submit()

    # GL: DR to_gl / CR from_gl
    make_gl_entries([
        {
            "account": to_gl,
            "debit": amount_f,
            "credit": 0,
            "posting_date": date,
            "voucher_type": "Bank Transaction",
            "voucher_no": bt_from.name,
            "company": company,
            "remarks": remark,
        },
        {
            "account": from_gl,
            "debit": 0,
            "credit": amount_f,
            "posting_date": date,
            "voucher_type": "Bank Transaction",
            "voucher_no": bt_from.name,
            "company": company,
            "remarks": remark,
        },
    ])

    # Recalculate and persist the live balance for both accounts immediately
    # so the Bank Accounts page shows the correct number without a manual refresh.
    from_balance = _recalc_balance(from_account)
    to_balance   = _recalc_balance(to_account)
    frappe.db.commit()

    return {
        "from_transaction": bt_from.name,
        "to_transaction":   bt_to.name,
        "reference":        xref,
        "amount":           amount_f,
        "from_account":     from_account,
        "to_account":       to_account,
        "from_balance":     from_balance,
        "to_balance":       to_balance,
    }


@frappe.whitelist(allow_guest=False)
def get_bank_transfers(company: str = None) -> list:
    """
    List inter-account transfers (Bank Transactions of type 'Transfer'),
    grouped back into one row per transfer via the shared reference_number.

    Each row: { reference, date, from_account, to_account, amount, status,
                from_transaction, to_transaction }.
    Legacy transfers (no reference) are reconstructed from the outgoing leg.
    """
    import re
    if not company:
        company = _get_company(frappe.session.user)

    acct_names = frappe.get_all("Bank Account", filters={"company": company} if company else {}, pluck="name")
    if not acct_names:
        return []

    rows = frappe.get_all(
        "Bank Transaction",
        filters={"transaction_type": "Transfer", "docstatus": 1, "bank_account": ["in", acct_names]},
        fields=["name", "bank_account", "date", "description", "debit", "credit", "status", "reference_number","custom_transfer_purpose"],
        order_by="date desc, creation desc",
        limit=500,
    )

    groups = {}
    for r in rows:
        key = r.reference_number or r.name
        g = groups.setdefault(key, {
            "reference": r.reference_number or "", "date": r.date, "status": "Reconciled",
            "from_account": None, "to_account": None, "amount": 0.0,
            "from_transaction": None, "to_transaction": None, "_from_desc": "", "description": "","purpose": "",
        })
        if r.date and (not g["date"] or str(r.date) < str(g["date"])):
            g["date"] = r.date
        if flt(r.debit) > 0:
            g["from_account"] = r.bank_account
            g["amount"] = flt(r.debit)
            g["from_transaction"] = r.name
            g["_from_desc"] = r.description or ""
        if flt(r.credit) > 0:
            g["to_account"] = r.bank_account
            g["to_transaction"] = r.name
            if not g["amount"]:
                g["amount"] = flt(r.credit)
        if (r.status or "") != "Reconciled":
            g["status"] = "Unreconciled"
        if r.custom_transfer_purpose and not g["purpose"]:
            g["purpose"] = r.custom_transfer_purpose

    out = []
    for g in groups.values():
        # Skip credit-only legacy legs (inbound mirror already shown via its outbound leg).
        if not g["from_account"] and not g["from_transaction"]:
            continue
        # Extract user notes from the description field (format: "Transfer to X — <note>")
        raw_desc = g.get("_from_desc", "") or ""
        m = re.search(r" — (.+)$", raw_desc)
        if m:
            g["description"] = m.group(1).strip()
        if not g["to_account"]:
            m2 = re.search(r"Transfer to (.+?)(?: —|$)", raw_desc)
            if m2:
                g["to_account"] = m2.group(1).strip()
        g.pop("_from_desc", None)
        out.append(g)
    out.sort(key=lambda x: str(x.get("date") or ""), reverse=True)
    return out


@frappe.whitelist(allow_guest=False, methods=["POST"])
def delete_bank_transfer(reference: str = "", from_transaction: str = "") -> dict:
    """
    Delete a transfer: cancels + deletes both Bank Transaction legs and their
    GL entries. Identifies the legs by shared reference_number when available,
    otherwise just the single transaction passed in.
    """
    from zoho_books_clone.utils.access import require_module
    require_module("banking", write=True)
    names = []
    if reference:
        names = frappe.get_all("Bank Transaction",
                               filters={"reference_number": reference, "transaction_type": "Transfer"},
                               pluck="name")
    if from_transaction and from_transaction not in names:
        names.append(from_transaction)
    if not names:
        frappe.throw(_("Transfer not found."))

    from zoho_books_clone.accounts.central_validator import assert_not_locked
    for nm in names:
        # force=True bypasses before_delete hooks — run the lock check explicitly.
        assert_not_locked("Bank Transaction", nm)
        try:
            doc = frappe.get_doc("Bank Transaction", nm)
            if doc.docstatus == 1:
                doc.flags.ignore_permissions = True
                doc.cancel()
            frappe.delete_doc("Bank Transaction", nm, ignore_permissions=True, force=True)
        except frappe.ValidationError:
            raise  # surface lock/period errors to the caller
        except Exception:
            pass
        # Remove any GL entries posted against this transaction.
        frappe.db.delete("General Ledger Entry", {"voucher_no": nm})

    frappe.db.commit()
    return {"deleted": names}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def create_bank_gl_entry(
    bank_account: str,
    bank_transaction: str,
    gl_account: str,
    amount: str,
    txn_type: str,
    date: str = None,
    description: str = "",
) -> dict:
    """
    Create a GL Journal Entry for an unmatched bank transaction, then mark
    the transaction as Reconciled.

    txn_type "Debit"  (withdrawal / charge):
      DR  gl_account   (expense)
      CR  bank_gl      (bank decreases)

    txn_type "Credit" (deposit / interest):
      DR  bank_gl      (bank increases)
      CR  gl_account   (income)
    """
    from zoho_books_clone.utils.access import require_module
    require_module("banking", write=True)
    amount_f = flt(amount)
    date = date or today()
    bank_gl  = _bank_gl(bank_account)
    company  = _company(bank_account)
    remark   = description or f"Bank entry: {bank_transaction}"

    if txn_type == "Debit":
        entries = [
            {"account": gl_account, "debit": amount_f, "credit": 0},
            {"account": bank_gl,    "debit": 0,        "credit": amount_f},
        ]
    else:
        entries = [
            {"account": bank_gl,    "debit": amount_f, "credit": 0},
            {"account": gl_account, "debit": 0,        "credit": amount_f},
        ]

    for e in entries:
        e.update({
            "posting_date": date,
            "voucher_type": "Bank Transaction",
            "voucher_no": bank_transaction,
            "company": company,
            "remarks": remark,
        })

    make_gl_entries(entries)

    # Mark Bank Transaction as Reconciled
    try:
        doc = frappe.get_doc("Bank Transaction", bank_transaction)
        if doc.docstatus == 1:
            doc.status = "Reconciled"
            doc.clearance_date = date
            doc.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        pass

    return {
        "bank_transaction": bank_transaction,
        "gl_account": gl_account,
        "amount": amount_f,
        "txn_type": txn_type,
    }
@frappe.whitelist(allow_guest=False, methods=["POST"])
def reconcile_transactions(bank_account: str, transaction_names: str, clearance_date: str = None) -> dict:
    """
    Mark a list of Bank Transactions as Reconciled.
    transaction_names: JSON-encoded list of Bank Transaction names.
    """
    from zoho_books_clone.utils.access import require_module
    require_module("banking", write=True)
    import json
    names = json.loads(transaction_names or "[]")
    if not names:
        frappe.throw(_("No transactions provided."))

    date = clearance_date or today()
    ok = 0; fail = 0
    for name in names:
        try:
            row = frappe.db.get_value("Bank Transaction", name, ["docstatus", "status"], as_dict=True)
            if row and row.docstatus == 1 and row.status != "Reconciled":
                frappe.db.set_value("Bank Transaction", name,
                                    "status", "Reconciled",
                                    update_modified=False)
                ok += 1
        except Exception:
            fail += 1

    frappe.db.commit()
    # Refresh current_balance for the account
    live = _recalc_balance(bank_account)
    return {"ok": ok, "fail": fail, "current_balance": live}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def mark_transaction_reconciled(bank_transaction: str, clearance_date: str = None) -> dict:
    """
    Mark a single Bank Transaction as Reconciled.
    """
    from zoho_books_clone.utils.access import require_module
    require_module("banking", write=True)
    date = clearance_date or today()
    row = frappe.db.get_value("Bank Transaction", bank_transaction,
                              ["docstatus", "bank_account"], as_dict=True)
    if not row:
        frappe.throw(_("Transaction {0} not found.").format(bank_transaction))
    if row.docstatus != 1:
        frappe.throw(_("Transaction {0} is not submitted.").format(bank_transaction))
    frappe.db.set_value("Bank Transaction", bank_transaction,
                        "status", "Reconciled",
                        update_modified=False)
    frappe.db.commit()
    live = _recalc_balance(row.bank_account)
    return {"bank_transaction": bank_transaction, "status": "Reconciled", "current_balance": live}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def delete_bank_account(name: str) -> dict:
    """
    Fully delete a Bank Account and all its linked Bank Transactions / GL entries.

    Steps:
      1. Cancel + delete all submitted Bank Transactions for this account.
      2. Delete draft Bank Transactions.
      3. Delete GL Entries whose voucher_no was one of those transactions.
      4. Delete the Bank Account document itself.

    Uses ignore_permissions=True throughout so the Books Manager role
    can perform the deletion without a native Frappe delete permission.
    """
    from zoho_books_clone.utils.access import require_module
    require_module("banking", write=True)
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    if not frappe.db.exists("Bank Account", name):
        frappe.throw(_("Bank Account {0} does not exist.").format(name))

    # 1. Collect all linked Bank Transactions
    txn_names = frappe.db.get_all(
        "Bank Transaction",
        filters={"bank_account": name},
        pluck="name",
    )

    from zoho_books_clone.accounts.central_validator import assert_not_locked
    deleted_txns = []
    for txn_name in txn_names:
        # force=True bypasses before_delete hooks — run the lock check explicitly.
        assert_not_locked("Bank Transaction", txn_name)
        try:
            doc = frappe.get_doc("Bank Transaction", txn_name)
            if doc.docstatus == 1:
                doc.flags.ignore_permissions = True
                doc.cancel()
            frappe.delete_doc(
                "Bank Transaction", txn_name,
                ignore_permissions=True,
                force=True,
            )
            deleted_txns.append(txn_name)
        except frappe.ValidationError:
            raise  # surface lock/period errors to the caller
        except Exception as e:
            frappe.log_error("Could not delete Bank Transaction {0}: {1}".format(txn_name, e))

    # 2. Delete GL entries for those transactions
    if deleted_txns:
        frappe.db.delete(
            "General Ledger Entry",
            {"voucher_type": "Bank Transaction", "voucher_no": ["in", deleted_txns]},
        )

    # 3. Delete the Bank Account
    frappe.delete_doc("Bank Account", name, ignore_permissions=True, force=True)
    frappe.db.commit()

    return {"deleted": name, "transactions_removed": len(deleted_txns)}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def save_cheque(data):
    """
    Dedicated endpoint to safely create or update a Cheque (Payment Entry).
    Accepts simple parameters from the frontend and resolves the complex GL
    account requirements (paid_from, paid_to) automatically.
    """
    from zoho_books_clone.utils.access import require_module
    require_module("banking", write=True)
    import json
    if isinstance(data, str):
        data = json.loads(data)

    name = data.get("name")
    payment_type = data.get("payment_type") # "Receive" or "Pay"
    bank_account_name = data.get("bank_account")
    party = data.get("party")
    party_type = data.get("party_type")
    company = _get_company(frappe.session.user)

    if not company:
        frappe.throw("Company is required")

    # Resolve the Bank GL Account
    bank_gl = _bank_gl(bank_account_name)

    # Resolve AR/AP Account
    if payment_type == "Receive":
        ar_ap_gl = frappe.db.get_value("Account", {"account_type": "Receivable", "company": company, "is_group": 0}, "name")
        paid_from = ar_ap_gl
        paid_to = bank_gl
    else:
        ar_ap_gl = frappe.db.get_value("Account", {"account_type": "Payable", "company": company, "is_group": 0}, "name")
        paid_from = bank_gl
        paid_to = ar_ap_gl

    if not ar_ap_gl:
        frappe.throw(f"No default {'Receivable' if payment_type == 'Receive' else 'Payable'} account found for company {company}")

    doc = {
        "doctype": "Payment Entry",
        "payment_type": payment_type,
        "mode_of_payment": "Cheque",
        "party_type": party_type,
        "party": party,
        "company": company,
        "paid_from": paid_from,
        "paid_to": paid_to,
        "paid_amount": flt(data.get("paid_amount")),
        "payment_date": data.get("payment_date"),
        "reference_no": data.get("reference_no"),
        "reference_date": data.get("reference_date"),
        "remarks": data.get("remarks"),
        "cheque_status": data.get("cheque_status") or data.get("status") or "Issued",
    }

    if name and frappe.db.exists("Payment Entry", name):
        d = frappe.get_doc("Payment Entry", name)
        is_submitted = d.docstatus == 1
        d.update(doc)
        if is_submitted:
            d.flags.ignore_validate_update_after_submit = True
        d.save(ignore_permissions=True)
    else:
        d = frappe.get_doc(doc)
        d.insert(ignore_permissions=True)
    
    frappe.db.commit()
    return d.as_dict()