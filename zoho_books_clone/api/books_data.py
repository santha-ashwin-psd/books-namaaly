import frappe
import json
from frappe.utils import get_url, nowdate, flt
from zoho_books_clone.api.session import _get_company
from zoho_books_clone.db.validators import validate_fiscal_year

# Currencies to auto-refresh on the Settings page
_KNOWN_CURRENCIES = []  # INR-only: no external currencies to refresh


def get_live_exchange_rate(from_currency, to_currency="INR"):
    """
    Real-time exchange rate (from_currency → to_currency, default INR).
    Flow: same-day Frappe cache → live API → stale cache.
    """
    from_currency = (from_currency or "").upper().strip()
    to_currency   = (to_currency   or "INR").upper().strip()
    if from_currency == to_currency:
        return {"rate": 1.0, "source": "identity", "date": nowdate()}

    today = nowdate()

    # ── 1. Same-day cache ─────────────────────────────────────────────────────
    cached_name = frappe.db.get_value(
        "Currency Exchange",
        {"from_currency": from_currency, "to_currency": to_currency, "date": today},
        "name",
    )
    if cached_name:
        rate = frappe.db.get_value("Currency Exchange", cached_name, "exchange_rate")
        return {"rate": float(rate), "source": "cache", "date": today}

    # ── 2. Live fetch from free API (no key needed) ───────────────────────────
    try:
        import requests as _req
        base = from_currency.lower()
        resp = _req.get(
            f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{base}.json",
            timeout=6,
        )
        resp.raise_for_status()
        data = resp.json()
        rate_val = data.get(base, {}).get(to_currency.lower())
        if rate_val:
            rate_val = float(rate_val)
            # Cache in Frappe
            try:
                existing = frappe.db.exists("Currency Exchange",
                    {"from_currency": from_currency, "to_currency": to_currency, "date": today})
                if existing:
                    frappe.db.set_value("Currency Exchange", existing, "exchange_rate", rate_val)
                else:
                    doc = frappe.new_doc("Currency Exchange")
                    doc.from_currency  = from_currency
                    doc.to_currency    = to_currency
                    doc.exchange_rate  = rate_val
                    doc.date           = today
                    doc.insert(ignore_permissions=True)
                frappe.db.commit()
            except Exception as cache_err:
                frappe.log_error(str(cache_err), "Exchange Rate Cache Save")
            return {"rate": rate_val, "source": "live", "date": today}
    except Exception as api_err:
        frappe.log_error(str(api_err), "Live Exchange Rate API")

    # ── 3. Stale cache fallback ───────────────────────────────────────────────
    stale = frappe.db.get_value(
        "Currency Exchange",
        {"from_currency": from_currency, "to_currency": to_currency},
        ["exchange_rate", "date"],
        order_by="date desc",
        as_dict=True,
    )
    if stale:
        return {"rate": float(stale.exchange_rate), "source": "stale", "date": str(stale.date)}

    return {"rate": None, "source": "unavailable", "date": today}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def refresh_all_exchange_rates():
    """Fetch and cache live rates for all known currencies against INR. Called from Settings page."""
    results = {}
    for cur in _KNOWN_CURRENCIES:
        try:
            results[cur] = get_live_exchange_rate(cur, "INR")
        except Exception:
            results[cur] = {"rate": None, "source": "error"}
    return results


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_voucher_journal(voucher_type, voucher_no):
    """
    Return the General Ledger Entry rows for a single voucher (Invoice, Bill,
    Payment Entry, Expense, Credit/Debit Note, Journal Entry, etc.) so the UI
    can render a Zoho-style "Journal" tab: ACCOUNT | DEBIT | CREDIT.
    """
    rows = frappe.db.sql(
        """
        SELECT account, debit, credit, party_type, party, cost_center, currency
        FROM `tabGeneral Ledger Entry`
        WHERE voucher_type = %s AND voucher_no = %s AND is_cancelled = 0
        ORDER BY creation ASC
        """,
        (voucher_type, voucher_no),
        as_dict=True,
    )
    total_debit = sum(flt(r.debit) for r in rows)
    total_credit = sum(flt(r.credit) for r in rows)
    print(total_debit, total_credit)
    return {
        "rows": rows,
        "total_debit": total_debit,
        "total_credit": total_credit,
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_invoice_email_defaults(invoice_name):
    inv = frappe.get_doc("Sales Invoice", invoice_name)
    customer_email = frappe.db.get_value("Customer", inv.customer, "email_id") or ""
    subject = f"Invoice {inv.name} from {inv.company or frappe.db.get_default('company') or ''}"
    body = (
        f"Dear {inv.customer_name or inv.customer},<br><br>"
        f"Please find your invoice <b>{inv.name}</b> details below:<br><br>"
        f"<table style='border-collapse:collapse;font-size:14px'>"
        f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Invoice #</td><td><b>{inv.name}</b></td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Amount</td><td><b>₹{inv.grand_total:,.2f}</b></td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Due Date</td><td>{inv.due_date}</td></tr>"
        f"</table><br>"
        f"Kindly make the payment by the due date.<br><br>"
        f"Thanks for your business.<br><br>"
        f"Regards,<br>{inv.company or ''}"
    )
    return {
        "to": customer_email,
        "subject": subject,
        "body": body,
        "invoice_name": inv.name,
        "customer_name": inv.customer_name or inv.customer,
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def send_invoice_email(invoice_name, to, subject, body, cc=None):
    if not to:
        frappe.throw("Recipient email (To) is required.")
    # Books Manager is a custom role — skip frappe.has_permission() to avoid
    # false PermissionError; @frappe.whitelist(allow_guest=False) already blocks guests.
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)

    inv = frappe.get_doc("Sales Invoice", invoice_name)
    recipients = [e.strip() for e in to.split(",") if e.strip()]
    cc_list = [e.strip() for e in (cc or "").split(",") if e.strip()]

    # Try attaching PDF — silently skip if print format not found
    attachments = []
    try:
        pdf_attachment = frappe.attach_print(
            inv.doctype, inv.name,
            print_format="Sales Invoice",
            print_letterhead=False,
        )
        if pdf_attachment:
            attachments = [pdf_attachment]
    except Exception:
        pass

    # Company SMTP when configured, otherwise the platform (wecode) SMTP.
    from zoho_books_clone.utils.email_company import send_business_email
    send_business_email(
        to=recipients, subject=subject, html=body, company=inv.company,
        cc=cc_list or None, attachments=attachments or None,
    )

    # Log communication — "email_status" field does NOT exist in this Frappe version,
    # use only valid fields: sent_or_received, status
    try:
        comm = frappe.get_doc({
            "doctype": "Communication",
            "communication_type": "Communication",
            "communication_medium": "Email",
            "sent_or_received": "Sent",
            "subject": subject,
            "content": body,
            "sender": frappe.session.user,
            "recipients": to,
            "cc": cc or "",
            "reference_doctype": "Sales Invoice",
            "reference_name": invoice_name,
            "status": "Linked",
        })
        comm.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        # Communication log is non-critical — don't fail the send
        frappe.db.commit()

    return {"status": "sent", "to": to, "invoice": invoice_name}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_quote_email_defaults(quote_name):
    """Return pre-filled subject, body and recipient for a Quotation."""
    quot = frappe.get_doc("Quotation", quote_name)
    customer_email = frappe.db.get_value("Customer", quot.customer, "email_id") or ""
    company = quot.company or frappe.db.get_default("company") or ""
    items_html = "".join(
        f"<tr><td style='padding:6px 12px;border-bottom:1px solid #f0f2f5'>{r.item_name or r.item_code}</td>"
        f"<td style='padding:6px 12px;border-bottom:1px solid #f0f2f5;text-align:right'>{flt(r.qty):.2f}</td>"
        f"<td style='padding:6px 12px;border-bottom:1px solid #f0f2f5;text-align:right'>₹{flt(r.rate):,.2f}</td>"
        f"<td style='padding:6px 12px;border-bottom:1px solid #f0f2f5;text-align:right'>₹{flt(r.amount):,.2f}</td></tr>"
        for r in (quot.items or [])
    )
    body = (
        f"Dear {quot.customer_name or quot.customer},<br><br>"
        f"Thank you for your interest. Please find your quotation <b>{quot.name}</b> below.<br><br>"
        f"<table style='border-collapse:collapse;font-size:13px;width:100%;max-width:600px'>"
        f"<thead><tr style='background:#f8faff'>"
        f"<th style='padding:8px 12px;text-align:left;border-bottom:2px solid #e4e8f0'>Item</th>"
        f"<th style='padding:8px 12px;text-align:right;border-bottom:2px solid #e4e8f0'>Qty</th>"
        f"<th style='padding:8px 12px;text-align:right;border-bottom:2px solid #e4e8f0'>Rate</th>"
        f"<th style='padding:8px 12px;text-align:right;border-bottom:2px solid #e4e8f0'>Amount</th>"
        f"</tr></thead><tbody>{items_html}</tbody>"
        f"<tfoot><tr><td colspan='3' style='padding:8px 12px;text-align:right;font-weight:700'>Grand Total</td>"
        f"<td style='padding:8px 12px;text-align:right;font-weight:700;color:#2563EB'>₹{flt(quot.grand_total):,.2f}</td></tr></tfoot>"
        f"</table><br>"
        f"This quotation is valid until <b>{quot.valid_till or 'N/A'}</b>.<br><br>"
        f"Please reply to accept or discuss any changes.<br><br>"
        f"Regards,<br>{company}"
    )
    return {
        "to": customer_email,
        "subject": f"Quotation {quot.name} from {company}",
        "body": body,
        "quote_name": quot.name,
        "customer_name": quot.customer_name or quot.customer,
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def send_quote_email(quote_name, to, subject, body, cc=None):
    """Send a Quotation by email and mark it as Sent."""
    if not to:
        frappe.throw("Recipient email (To) is required.")
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)

    recipients = [e.strip() for e in to.split(",") if e.strip()]
    cc_list = [e.strip() for e in (cc or "").split(",") if e.strip()]

    # Company SMTP when configured, otherwise the platform (wecode) SMTP.
    from zoho_books_clone.utils.email_company import send_business_email
    send_business_email(
        to=recipients, subject=subject, html=body,
        company=frappe.db.get_value("Quotation", quote_name, "company"),
        cc=cc_list or None,
    )

    # Mark the quotation as Sent
    frappe.db.set_value("Quotation", quote_name, "status", "Sent", update_modified=True)
    frappe.db.commit()

    # Log communication
    try:
        comm = frappe.get_doc({
            "doctype": "Communication",
            "communication_type": "Communication",
            "communication_medium": "Email",
            "sent_or_received": "Sent",
            "subject": subject,
            "content": body,
            "sender": frappe.session.user,
            "recipients": to,
            "cc": cc or "",
            "reference_doctype": "Quotation",
            "reference_name": quote_name,
            "status": "Linked",
        })
        comm.insert(ignore_permissions=True)
    except Exception:
        pass

    return {"status": "sent", "to": to, "quote": quote_name}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def save_doc(doc):
    if isinstance(doc, str):
        doc = json.loads(doc)
    doctype = doc.get("doctype")
    if not doctype:
        frappe.throw("doctype is required")
    # Guest is already blocked by @frappe.whitelist; skip frappe.has_permission()
    # which rejects the Books Manager custom role on core Frappe doctypes.
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    from zoho_books_clone.utils.access import assert_can
    assert_can(doctype, "write")
    name = doc.get("name")
    if name and frappe.db.exists(doctype, name):
        d = frappe.get_doc(doctype, name)
        d.update(doc)
        d.save(ignore_permissions=True)
    else:
        d = frappe.get_doc(doc)
        d.insert(ignore_permissions=True)
    frappe.db.commit()
    return d.as_dict()


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def submit_doc(doctype, name, ignore_budget_warning=0):
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    from zoho_books_clone.utils.access import assert_can
    assert_can(doctype, "submit")
    d = frappe.get_doc(doctype, name)
    d.flags.ignore_permissions = True
    if int(ignore_budget_warning or 0) == 1:
        d.flags.ignore_budget_warning = True
    d.submit()
    frappe.db.commit()
    return d.as_dict()


# ─── Record Payment ───────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_payment_defaults(invoice_name):
    inv = frappe.get_doc("Sales Invoice", invoice_name)
    last_payment = frappe.db.sql(
        "SELECT COUNT(*) FROM `tabPayment Entry Reference` WHERE reference_name = %s",
        invoice_name
    )
    next_num = (last_payment[0][0] or 0) + 1
    outstanding = flt(getattr(inv, "outstanding_amount", None))
    if not outstanding:
        outstanding = flt(inv.grand_total) - flt(inv.advance_paid)
    company = inv.company or frappe.db.get_default("company")
    # Use LOWER() so we find accounts regardless of company name casing in the DB
    bank_accounts = frappe.db.sql(
        """SELECT name, account_type FROM `tabAccount`
           WHERE account_type IN ('Bank','Cash') AND is_group = 0
             AND LOWER(company) = LOWER(%s)
           ORDER BY account_type DESC""",
        (company,), as_dict=True
    )
    # Prefer our own Books Payment Mode; fall back to Frappe's Mode of Payment
    try:
        payment_mode_docs = frappe.get_all(
            "Books Payment Mode", filters={"enabled": 1}, fields=["mode_of_payment"], order_by="mode_of_payment"
        )
        payment_modes = [m.mode_of_payment for m in payment_mode_docs]
    except Exception:
        try:
            payment_mode_docs = frappe.get_all("Mode of Payment", fields=["name"], order_by="name")
            payment_modes = [m.name for m in payment_mode_docs]
        except Exception:
            payment_modes = ["Cash", "Bank Transfer", "UPI", "NEFT", "RTGS", "Cheque"]

    return {
        "invoice_name": inv.name,
        "customer_name": inv.customer_name or inv.customer,
        "customer": inv.customer,
        "grand_total": flt(inv.grand_total),
        "balance_due": outstanding,
        "currency": inv.currency or "INR",
        "payment_number": str(next_num),
        "payment_date": nowdate(),
        "bank_accounts": bank_accounts,
        "payment_modes": payment_modes,
        "company": company,
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])

def _create_bank_transaction(pe):
    """Create a Bank Transaction row mirroring the Payment Entry bank leg.

    Called after a Payment Entry is submitted so the Banking / Transactions
    page shows the entry immediately, ready for reconciliation.

    For a Receive payment:  money comes IN  → credit on the bank account
    For a Pay payment:      money goes OUT  → debit  on the bank account
    """
    # Resolve which account is the bank/cash leg
    if pe.payment_type == "Receive":
        bank_account_name = pe.paid_to    # Bank/Cash account
        deposit   = flt(pe.paid_amount)
        withdrawal = 0.0
    else:  # Pay
        bank_account_name = pe.paid_from  # Bank/Cash account
        deposit   = 0.0
        withdrawal = flt(pe.paid_amount)

    # Look up the Bank Account document linked to this GL account
    bank_acc = frappe.db.get_value(
        "Bank Account", {"gl_account": bank_account_name, "company": pe.company}, "name"
    )
    if not bank_acc:
        # No Bank Account record linked — skip silently (Cash payments are fine without one)
        return None

    bt = frappe.get_doc({
        "doctype":        "Bank Transaction",
        "date":           pe.payment_date or pe.posting_date,
        "bank_account":   bank_acc,
        "credit":         deposit,    # Bank statement convention: credit = money IN (matches _set_balance/_post_gl)
        "debit":          withdrawal, # Bank statement convention: debit  = money OUT
        "currency":       pe.paid_to_account_currency or "INR",
        "description":    pe.remarks or f"Payment Entry {pe.name}",
        "reference_number": pe.reference_no or pe.name,
        "payment_entry":  pe.name,
        "status":         "Unreconciled",
        "company":        pe.company,
    })
    bt.insert(ignore_permissions=True)
    bt.flags.ignore_permissions = True
    bt.submit()
    frappe.db.commit()
    return bt.name

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def record_payment(
    invoice_name=None, amount_received=None, payment_date=None,
    payment_mode="Cash", deposit_to=None, bank_charges=0,
    reference_no=None, notes=None, tds_deducted=0, tds_amount=0, save_as_draft=False,
):
    from zoho_books_clone.utils.access import require_module
    require_module("payments", write=True)
    if not invoice_name:
        frappe.throw("invoice_name is required to record a payment.")
    if amount_received is None:
        frappe.throw("amount_received is required.")
    if not payment_date:
        payment_date = frappe.utils.nowdate()
    if isinstance(save_as_draft, str):
        save_as_draft = save_as_draft.lower() in ("true", "1", "yes")


    amount_received = flt(amount_received)
    bank_charges    = flt(bank_charges)
    tds_amount      = flt(tds_amount)

    if not amount_received:
        frappe.throw("Amount Received is required and must be greater than 0.")
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)

    inv      = frappe.get_doc("Sales Invoice", invoice_name)
    company  = inv.company or frappe.db.get_default("company")
    currency = inv.currency or "INR"

    # Fiscal year lock — block payments into a locked or closed period
    validate_fiscal_year(payment_date, company)

    # Resolve deposit_to first so we can derive the canonical company name from it.
    # Frappe validates that every account on a Payment Entry shares the same company
    # with a case-sensitive comparison, so the company on the Payment Entry MUST
    # exactly match the company stored on each account record.
    if not deposit_to:
        acct_type = "Cash" if payment_mode == "Cash" else "Bank"
        deposit_to = frappe.db.sql(
            """SELECT name FROM `tabAccount`
               WHERE account_type = %s AND LOWER(company) = LOWER(%s)
                 AND is_group = 0 AND disabled = 0
               LIMIT 1""",
            (acct_type, company), as_dict=True
        )
        deposit_to = deposit_to[0]["name"] if deposit_to else None

    if not deposit_to:
        frappe.throw("Could not find a Cash/Bank account. Please set one up under Accounts.")

    # Use the deposit_to account's own company as the canonical company name.
    # This is the authoritative value — the account itself knows its company.
    company = frappe.db.get_value("Account", deposit_to, "company") or company

    # Resolve Accounts Receivable — look up using the same canonical company.
    debtors_account = getattr(inv, "debit_to", None)
    if debtors_account:
        # Verify the invoice's debit_to account belongs to the same company
        # using case-insensitive comparison; if not, fall back to lookup.
        ar_company = frappe.db.get_value("Account", debtors_account, "company")
        if ar_company and ar_company.lower() != company.lower():
            debtors_account = None

    if not debtors_account:
        rows = frappe.db.sql(
            """SELECT name FROM `tabAccount`
               WHERE account_type = 'Receivable' AND LOWER(company) = LOWER(%s)
                 AND is_group = 0
               LIMIT 1""",
            (company,), as_dict=True
        )
        debtors_account = rows[0]["name"] if rows else None

    if not debtors_account:
        frappe.throw(
            f"No Receivable account found for company '{company}'. "
            "Please ensure the Chart of Accounts is set up under Accounts."
        )

    outstanding_amount = flt(getattr(inv, "outstanding_amount", None)) or (
        flt(inv.grand_total) - flt(getattr(inv, "advance_paid", 0))
    )

    pe = frappe.new_doc("Payment Entry")
    pe.payment_type               = "Receive"
    pe.company                    = company
    pe.posting_date               = payment_date
    pe.payment_date               = payment_date
    pe.mode_of_payment            = payment_mode
    pe.party_type                 = "Customer"
    pe.party                      = inv.customer
    pe.party_name                 = inv.customer_name or inv.customer
    pe.paid_from                  = debtors_account
    pe.paid_to                    = deposit_to
    pe.paid_amount                = amount_received
    pe.received_amount            = amount_received
    pe.source_exchange_rate       = 1
    pe.target_exchange_rate       = 1
    pe.paid_from_account_currency = currency
    pe.paid_to_account_currency   = currency
    pe.reference_no               = reference_no or f"PMT-{invoice_name}"
    pe.reference_date             = payment_date
    pe.remarks                    = notes or f"Payment against {invoice_name}"

    pe.append("references", {
        "reference_doctype":  "Sales Invoice",
        "reference_name":     invoice_name,
        "due_date":           inv.due_date,
        "total_amount":       flt(inv.grand_total),
        "outstanding_amount": outstanding_amount,
        "allocated_amount":   amount_received,
    })

    # Bank charges: your Payment Entry doctype has no deductions child table,
    # so we note the charge in remarks and reduce received_amount so the net
    # deposit to the bank account is accurate.
    if bank_charges > 0:
        net_received = amount_received - bank_charges
        pe.received_amount = net_received if net_received > 0 else amount_received
        charge_note = f" | Bank Charges: \u20b9{bank_charges:,.2f} (Net received: \u20b9{pe.received_amount:,.2f})"
        pe.remarks = (pe.remarks or "") + charge_note

    pe.insert(ignore_permissions=True)
    if not save_as_draft:
        pe.flags.ignore_permissions = True
        pe.submit()
        _create_bank_transaction(pe)
    frappe.db.commit()

    return {
        "status":        "draft" if save_as_draft else "submitted",
        "payment_entry": pe.name,
        "invoice":       invoice_name,
        "amount":        amount_received,
    }


@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_customer_outstanding_invoices(customer, company=None):
    """All submitted Sales Invoices for `customer` that still have money owed.

    Used to populate the invoice picker in the multi-invoice payment dialog.
    """
    from zoho_books_clone.utils.access import require_module
    require_module("payments", write=False)

    if not customer:
        frappe.throw("customer is required.")
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)

    if not company:
        company = frappe.db.get_default("company")

    filters = {
        "customer": customer,
        "docstatus": 1,
        "outstanding_amount": [">", 0],
    }
    if company:
        filters["company"] = company

    rows = frappe.get_all(
        "Sales Invoice",
        filters=filters,
        fields=["name", "posting_date", "due_date", "grand_total",
                "outstanding_amount", "currency", "status"],
        order_by="due_date asc, posting_date asc",
    )

    return {
        "customer": customer,
        "company": company,
        "invoices": rows,
        "total_outstanding": sum(flt(r.outstanding_amount) for r in rows),
    }


def _resolve_payment_accounts(company, payment_mode, deposit_to=None):
    """Shared account-resolution logic used by both record_payment and
    record_payment_multi. Returns (company, deposit_to, debtors_account).
    """
    if not deposit_to:
        acct_type = "Cash" if payment_mode == "Cash" else "Bank"
        rows = frappe.db.sql(
            """SELECT name FROM `tabAccount`
               WHERE account_type = %s AND LOWER(company) = LOWER(%s)
                 AND is_group = 0 AND disabled = 0
               LIMIT 1""",
            (acct_type, company), as_dict=True
        )
        deposit_to = rows[0]["name"] if rows else None

    if not deposit_to:
        frappe.throw("Could not find a Cash/Bank account. Please set one up under Accounts.")

    # The deposit_to account's own company is authoritative.
    company = frappe.db.get_value("Account", deposit_to, "company") or company

    rows = frappe.db.sql(
        """SELECT name FROM `tabAccount`
           WHERE account_type = 'Receivable' AND LOWER(company) = LOWER(%s)
             AND is_group = 0
           LIMIT 1""",
        (company,), as_dict=True
    )
    debtors_account = rows[0]["name"] if rows else None

    if not debtors_account:
        frappe.throw(
            f"No Receivable account found for company '{company}'. "
            "Please ensure the Chart of Accounts is set up under Accounts."
        )

    return company, deposit_to, debtors_account


@frappe.whitelist(allow_guest=False, methods=["POST"])
def record_payment_multi(
    customer=None, amount_received=None, payment_date=None,
    payment_mode="Cash", deposit_to=None, bank_charges=0,
    reference_no=None, notes=None, allocations=None, save_as_draft=False,
):
    """Record a single Payment Entry against MULTIPLE Sales Invoices at once.

    allocations: JSON list (or already-parsed list) of
        [{"invoice": "SINV-0001", "allocated_amount": 3000}, ...]
    The Payment Entry doctype already supports a multi-row `references`
    child table and validates/settles each row independently — this just
    builds that child table from `allocations` instead of a single invoice.
    """
    from zoho_books_clone.utils.access import require_module
    require_module("payments", write=True)

    if not customer:
        frappe.throw("customer is required to record a payment.")
    if amount_received is None:
        frappe.throw("amount_received is required.")
    if not payment_date:
        payment_date = frappe.utils.nowdate()
    if isinstance(save_as_draft, str):
        save_as_draft = save_as_draft.lower() in ("true", "1", "yes")
    if isinstance(allocations, str):
        allocations = json.loads(allocations or "[]")
    if not allocations:
        frappe.throw("At least one invoice allocation is required.")

    amount_received = flt(amount_received)
    bank_charges    = flt(bank_charges)

    if not amount_received:
        frappe.throw("Amount Received is required and must be greater than 0.")
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)

    # Normalise + validate allocation rows before touching any invoice.
    clean_allocations = []
    total_allocated = 0.0
    for row in allocations:
        inv_name = row.get("invoice") or row.get("invoice_name") or row.get("reference_name")
        amt = flt(row.get("allocated_amount"))
        if not inv_name:
            frappe.throw("Each allocation row must include an invoice name.")
        if amt <= 0:
            continue  # skip zero/blank rows rather than failing the whole payment
        clean_allocations.append({"invoice": inv_name, "allocated_amount": amt})
        total_allocated += amt

    if not clean_allocations:
        frappe.throw("At least one invoice must have an allocated amount greater than 0.")

    # Total allocated across invoices must exactly match the amount received.
    # (No advance/on-account concept yet — over/under-allocation is rejected
    # so cash and allocations never silently drift apart.)
    if round(total_allocated, 2) != round(amount_received, 2):
        frappe.throw(
            f"Total allocated ({total_allocated}) must equal Amount Received "
            f"({amount_received}). Adjust the per-invoice amounts or the total."
        )

    invoices = {}
    company = None
    currency = None
    for row in clean_allocations:
        inv = frappe.get_doc("Sales Invoice", row["invoice"])
        if inv.customer != customer:
            frappe.throw(f"Invoice {inv.name} does not belong to customer {customer}.")
        outstanding = flt(getattr(inv, "outstanding_amount", None))
        if not outstanding:
            outstanding = flt(inv.grand_total) - flt(getattr(inv, "advance_paid", 0))
        if row["allocated_amount"] > outstanding + 0.005:
            frappe.throw(
                f"Allocated amount {row['allocated_amount']} exceeds outstanding "
                f"{outstanding} for invoice {inv.name}."
            )
        invoices[inv.name] = (inv, outstanding)
        company = company or (inv.company or frappe.db.get_default("company"))
        currency = currency or (inv.currency or "INR")

    # Fiscal year lock — block payments into a locked or closed period
    validate_fiscal_year(payment_date, company)

    company, deposit_to, debtors_account = _resolve_payment_accounts(
        company, payment_mode, deposit_to
    )

    pe = frappe.new_doc("Payment Entry")
    pe.payment_type               = "Receive"
    pe.company                    = company
    pe.posting_date               = payment_date
    pe.payment_date               = payment_date
    pe.mode_of_payment            = payment_mode
    pe.party_type                 = "Customer"
    pe.party                      = customer
    pe.party_name                 = frappe.db.get_value("Customer", customer, "customer_name") or customer
    pe.paid_from                  = debtors_account
    pe.paid_to                    = deposit_to
    pe.paid_amount                = amount_received
    pe.received_amount            = amount_received
    pe.source_exchange_rate       = 1
    pe.target_exchange_rate       = 1
    pe.paid_from_account_currency = currency
    pe.paid_to_account_currency   = currency
    pe.reference_no               = reference_no or f"PMT-{customer}-{len(clean_allocations)}invoices"
    pe.reference_date             = payment_date
    invoice_list_str              = ", ".join(invoices.keys())
    pe.remarks                    = notes or f"Payment against {invoice_list_str}"

    for row in clean_allocations:
        inv, outstanding = invoices[row["invoice"]]
        pe.append("references", {
            "reference_doctype":  "Sales Invoice",
            "reference_name":     inv.name,
            "due_date":           inv.due_date,
            "total_amount":       flt(inv.grand_total),
            "outstanding_amount": outstanding,
            "allocated_amount":   row["allocated_amount"],
        })

    if bank_charges > 0:
        net_received = amount_received - bank_charges
        pe.received_amount = net_received if net_received > 0 else amount_received
        charge_note = f" | Bank Charges: \u20b9{bank_charges:,.2f} (Net received: \u20b9{pe.received_amount:,.2f})"
        pe.remarks = (pe.remarks or "") + charge_note

    pe.insert(ignore_permissions=True)
    if not save_as_draft:
        pe.flags.ignore_permissions = True
        pe.submit()
        _create_bank_transaction(pe)
    frappe.db.commit()

    return {
        "status":        "draft" if save_as_draft else "submitted",
        "payment_entry": pe.name,
        "customer":      customer,
        "amount":        amount_received,
        "invoices":      list(invoices.keys()),
    }


# ─── Stage 2: Cash-in-Hand → Bank deposit (Contra) ────────────────────────────
#
# Accounting flow this implements:
#   Stage 1 (already handled by record_payment / BankCash.vue "New Cash Entry"):
#       Dr Cash-in-Hand   /   Cr Accounts Receivable   (customer pays cash)
#   Stage 2 (this section):
#       Dr Bank           /   Cr Cash-in-Hand          (cash physically banked)
#
# The client does not want to track deposit status per individual cash entry
# (no more picking specific receipts to bundle). Instead this is a running
# POOL: "yet to deposit" = all-time Cash In − all-time Cash Out − all-time
# already-deposited-to-bank, for a given Cash account. The user can deposit
# any amount up to that pooled balance (a partial deposit is allowed), and
# the next time they open the drawer the balance reflects what's left.
#
# Already-deposited-to-bank is tracked by summing the Cash-account credit
# leg of every Contra Journal Entry created via deposit_cash_to_bank() below
# (identified by voucher_type='Contra Entry' + a fixed remark marker).

_CASH_DEPOSIT_REMARK_PREFIX = "Cash deposited to bank:"


def _cash_account_balance(cash_account, company):
    """Pooled 'yet to deposit' balance for one Cash account: all-time cash
    received minus all-time cash paid out minus all-time already deposited.
    """
    total_in = flt(frappe.db.sql(
        """SELECT SUM(paid_amount) FROM `tabPayment Entry`
           WHERE docstatus = 1 AND payment_type = 'Receive'
             AND paid_to = %s AND LOWER(company) = LOWER(%s)""",
        (cash_account, company)
    )[0][0] or 0)

    total_out = flt(frappe.db.sql(
        """SELECT SUM(paid_amount) FROM `tabPayment Entry`
           WHERE docstatus = 1 AND payment_type = 'Pay'
             AND paid_from = %s AND LOWER(company) = LOWER(%s)""",
        (cash_account, company)
    )[0][0] or 0)

    total_deposited = flt(frappe.db.sql(
        """SELECT SUM(jea.credit)
           FROM `tabJournal Entry Account` jea
           INNER JOIN `tabJournal Entry` je ON je.name = jea.parent
           WHERE je.docstatus = 1 AND je.voucher_type = 'Contra Entry'
             AND jea.account = %s
             AND je.remark LIKE %s""",
        (cash_account, _CASH_DEPOSIT_REMARK_PREFIX + "%")
    )[0][0] or 0)

    return total_in - total_out - total_deposited


@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_undeposited_cash(company=None, exclude_account=None):
    """Pooled 'yet to deposit' cash balance, per Cash account, for this company.

    exclude_account: when the deposit destination itself is a Cash account
    (e.g. topping up Petty Cash from the general cash pool), pass its name
    here so it's excluded from both the source pool AND the destination
    list — money can't be moved from an account into itself.
    """
    company = company or frappe.db.get_default("company")
    if not company:
        frappe.throw("No company context found.")

    cash_accounts = frappe.db.sql(
        """SELECT name FROM `tabAccount`
           WHERE account_type = 'Cash' AND is_group = 0 AND LOWER(company) = LOWER(%s)
           ORDER BY name""",
        (company,), as_dict=True
    )
    cash_account_names = [c["name"] for c in cash_accounts]
    if not cash_account_names:
        return {"cash_accounts": [], "total_undeposited": 0, "bank_accounts": [], "destination_accounts": [], "company": company}

    breakdown = []
    for acc in cash_account_names:
        if exclude_account and acc == exclude_account:
            continue
        bal = _cash_account_balance(acc, company)
        breakdown.append({"account": acc, "undeposited": bal})

    bank_accounts = frappe.db.sql(
        """SELECT name FROM `tabAccount`
           WHERE account_type = 'Bank' AND is_group = 0 AND disabled = 0 AND LOWER(company) = LOWER(%s)
           ORDER BY name""",
        (company,), as_dict=True
    )

    # Every Bank account, plus every OTHER Cash account, is a valid deposit
    # destination — "Deposit" can mean banking the cash, or moving it into
    # a different cash bucket like Petty Cash.
    destination_accounts = (
        [{"name": b["name"], "account_type": "Bank"} for b in bank_accounts]
        + [{"name": acc, "account_type": "Cash"} for acc in cash_account_names if acc != exclude_account]
    )

    # Only positive balances are actually depositable cash-in-hand. A Cash
    # account can go negative if cash payments were booked against it faster
    # than receipts (data issue, or a "petty cash" account being topped up
    # from elsewhere) — that shortfall isn't real cash sitting in a drawer,
    # so it must not silently eat into what's shown as available to deposit.
    total_depositable = sum(max(b["undeposited"], 0) for b in breakdown)

    return {
        "cash_accounts": breakdown,
        "total_undeposited": total_depositable,
        "bank_accounts": [b["name"] for b in bank_accounts],
        "destination_accounts": destination_accounts,
        "company": company,
    }


@frappe.whitelist(allow_guest=False, methods=["POST"])
def deposit_cash_to_bank(amount, destination_account, deposit_date=None, notes=None, company=None):
    """Deposit/transfer a chosen amount (up to the pooled undeposited
    balance) of cash out of the Cash-in-Hand pool, as one Journal Entry.

    destination_account can be:
      - a Bank account  -> Contra Entry (Dr Bank / Cr Cash-in-Hand): cash
        physically banked.
      - another Cash account (e.g. Petty Cash) -> internal Cash-to-Cash
        transfer (Dr destination Cash / Cr Cash-in-Hand): topping up a
        petty cash float from the general cash pool.

    If the business has more than one source Cash account, the amount is
    drawn automatically across whichever accounts currently hold a positive
    balance (largest first, excluding the destination itself) so the user
    only ever sees and edits ONE pooled number. Partial deposits/transfers
    are allowed — whatever isn't moved stays in the pool for next time.
    """
    from zoho_books_clone.utils.access import require_module
    require_module("banking", write=True)

    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)

    amount = flt(amount)
    if amount <= 0:
        frappe.throw("Amount must be greater than 0.")
    if not destination_account:
        frappe.throw("Select where to deposit the cash (a bank or a cash account).")

    deposit_date = deposit_date or nowdate()
    company = company or frappe.db.get_default("company")

    dest_company = frappe.db.get_value("Account", destination_account, "company")
    if not dest_company:
        frappe.throw(f"Account '{destination_account}' not found.")
    company = dest_company  # canonical company, same pattern as record_payment

    dest_type = frappe.db.get_value("Account", destination_account, "account_type")
    if dest_type not in ("Bank", "Cash"):
        frappe.throw(f"'{destination_account}' must be a Bank or Cash account.")

    validate_fiscal_year(deposit_date, company)

    # Re-check the pooled balance server-side — never trust the amount as final truth.
    # Exclude the destination itself from the source pool (can't move money
    # from an account into itself).
    exclude = destination_account if dest_type == "Cash" else None
    data = get_undeposited_cash(company=company, exclude_account=exclude)
    available_total = flt(data["total_undeposited"])
    if amount > available_total + 0.005:  # small float tolerance
        frappe.throw(f"Only {available_total} is available to deposit.")

    # Greedily allocate the requested amount across source accounts with a
    # positive balance, largest balance first, so as few accounts as
    # possible are touched by any one deposit.
    eligible = sorted(
        [c for c in data["cash_accounts"] if flt(c["undeposited"]) > 0],
        key=lambda c: flt(c["undeposited"]),
        reverse=True,
    )
    if not eligible:
        frappe.throw("No undeposited cash available.")

    allocations = []  # list of (cash_account, portion)
    remaining_to_allocate = amount
    for c in eligible:
        if remaining_to_allocate <= 0:
            break
        portion = min(flt(c["undeposited"]), remaining_to_allocate)
        if portion > 0:
            allocations.append((c["account"], portion))
            remaining_to_allocate -= portion

    je = frappe.new_doc("Journal Entry")
    je.naming_series = "JV-.YYYY.-"
    je.voucher_type  = "Contra Entry"
    je.company       = company
    je.posting_date  = deposit_date
    je.remark        = f"{_CASH_DEPOSIT_REMARK_PREFIX} {notes}".strip() if notes else _CASH_DEPOSIT_REMARK_PREFIX
    je.append("accounts", {"account": destination_account, "debit": amount, "credit": 0})
    for cash_account, portion in allocations:
        je.append("accounts", {"account": cash_account, "debit": 0, "credit": portion})
    je.insert(ignore_permissions=True)
    je.flags.ignore_permissions = True
    je.submit()

    frappe.db.commit()

    remaining = available_total - amount
    return {
        "journal_entry": je.name,
        "destination_account": destination_account,
        "destination_type": dest_type,
        "cash_accounts": [a[0] for a in allocations],
        "amount": amount,
        "remaining": remaining,
    }

# ─── AI Assistant — Books AI with live DB queries (Tiers 1-3) ────────────────

def _ai_parse_period(period):
    """Convert LLM period token or free text to (from_date, to_date, label)."""
    from frappe.utils import nowdate, getdate, add_months, get_first_day, get_last_day
    from datetime import date as _date
    today = getdate(nowdate())
    p = (period or "this_month").lower().replace(" ", "_")

    if "last_year" in p or "previous_year" in p:
        fy_s = _date(today.year - 1, 4, 1) if today.month >= 4 else _date(today.year - 2, 4, 1)
        fy_e = _date(today.year, 3, 31)     if today.month >= 4 else _date(today.year - 1, 3, 31)
        return fy_s.strftime("%Y-%m-%d"), fy_e.strftime("%Y-%m-%d"), "Last Financial Year"
    if "this_year" in p or "current_year" in p or "ytd" in p:
        fy_s = _date(today.year, 4, 1) if today.month >= 4 else _date(today.year - 1, 4, 1)
        return fy_s.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"), f"This Financial Year ({today.year})"
    if "this_quarter" in p or "quarter" in p:
        q_month = ((today.month - 1) // 3) * 3 + 1
        q_num   = (today.month - 1) // 3 + 1
        return _date(today.year, q_month, 1).strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"), f"Q{q_num} {today.year}"
    if "last_month" in p or "previous_month" in p:
        last  = add_months(nowdate(), -1)
        return get_first_day(last).strftime("%Y-%m-%d"), get_last_day(last).strftime("%Y-%m-%d"), "Last Month"
    # default: this month
    return get_first_day(nowdate()).strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"), f"This Month ({today.strftime('%B %Y')})"


# ── AI ASSISTANT — LLM layer ───────────────────────────────────────────────────

_AI_SYSTEM_PROMPT = """\
You are Books AI, a smart assistant embedded in a financial management app (like Zoho Books).
Understand what the user wants and return ONLY a valid JSON object — no markdown, no text outside JSON.

Response format:
{
  "intent": "<intent_name>",
  "reply": "<short conversational response, 1-2 sentences>",
  // ...extra fields depending on intent
}

CONVERSATIONAL intents (you write the full reply):
- "greeting"    — user says hi/hello/namaste etc.
- "help"        — user asks what you can do
- "thanks"      — user says thanks/great/ok
- "chitchat"    — casual smalltalk
- "unknown"     — you genuinely don't understand

DATA QUERY intents — FINANCE (backend fetches real numbers — write a 1-line intro in reply):
- "revenue"          — revenue/sales total. Add: "period": "this_month|last_month|this_quarter|this_year|last_year"
- "outstanding"      — total outstanding receivables
- "top_customers"    — top customers by revenue. Add: "limit": 5
- "overdue_count"    — count/amount of overdue invoices
- "unpaid_bills"     — unpaid purchase bills
- "payment_received" — total payments collected. Add: "period": "this_month|last_month|this_quarter|this_year"
- "expense_total"    — total purchase/expense amount. Add: "period": "this_month|last_month|this_quarter|this_year"
- "top_suppliers"    — top suppliers by purchase amount. Add: "limit": 5
- "profit_estimate"  — revenue minus expenses for a period. Add: "period": "..."
- "business_summary" — overall business health report (revenue, outstanding, overdue, inventory)

DATA QUERY intents — INVENTORY (backend fetches real numbers):
- "inventory_items"     — item count summary, optionally filtered. Add: "item_group": "...", "item_type": "Product|Service|Raw Material|Finished Good"
- "low_stock"           — items at or below their reorder level
- "top_selling_items"   — top items by quantity sold. Add: "period": "this_month|last_month|this_quarter|this_year", "limit": 5
- "item_groups_summary" — count of item groups and how many items each has
- "stock_value"         — total inventory value across all warehouses

NAVIGATION intents (app navigates — write a brief confirmation):
- "show_overdue"         — filter to overdue invoices
- "show_unpaid"          — filter to unpaid invoices
- "show_all_invoices"    — show all invoices
- "find_invoices"        — search invoices for a customer. Add: "customer": "extracted name"
- "show_bills"           — go to bills page
- "show_quotes"          — go to quotes
- "show_customers"       — go to customers list
- "show_suppliers"       — go to suppliers list
- "show_sales_orders"    — go to sales orders
- "show_purchase_orders" — go to purchase orders
- "show_dashboard"       — go to main dashboard
- "show_items"           — go to inventory items page
- "show_item_groups"     — go to item groups page
- "show_warehouses"      — go to warehouses page
- "show_inventory"       — go to inventory section
- "navigate"             — specific area. Add: "path": "/path"

CREATION WIZARD intents:
- "ask_for_info"           — you need more details before creating. Ask one specific question in reply.
- "create_invoice_confirm" — you have enough info, show preview for confirmation.
                             Add: "customer": "name", "items": [{"item_name":"..","qty":N,"rate":N}]
- "create_invoice"         — user just confirmed (said yes/ok/confirm/proceed). Same fields as above.

CREATION WIZARD RULES:
- If user wants to create invoice but no customer mentioned → use "ask_for_info", ask "Who is this invoice for?"
- If customer given but no items/amount → use "ask_for_info", ask "What should I add? (item, qty, rate)"
- Once you have customer + at least one item with amount → use "create_invoice_confirm" to show preview
- If user says yes/confirm/ok/proceed after a confirm preview → use "create_invoice"
- If user says cancel/no/never mind → use "thanks" and say it was cancelled

Rules:
- For greeting: mention capabilities across finance AND inventory (invoice wizard, revenue, stock levels, etc.).
- For help: list all categories (invoices wizard, finance queries, inventory queries, navigation).
- Always reply in the same language the user wrote in.
- Keep replies under 60 words.
"""

_SUMMARY_SYSTEM_PROMPT = """\
You are a financial analyst assistant. Given business metrics, write a concise health summary for the business owner.
Return ONLY valid JSON: {"reply": "your analysis here"}
Be specific with numbers. 3-5 sentences. Mention what's going well and what needs attention. Use ₹ for amounts.
"""

_EMAIL_SYSTEM_PROMPT = """\
You are a professional business email writer. Improve the given email to be professional, warm, and concise.
Return ONLY valid JSON: {"subject": "improved subject line", "body": "improved email body (max 120 words)"}
Keep the core message. Do not add unnecessary fluff. Use the invoice context if provided.
"""


class _RateLimit(Exception):
    pass


def _call_groq(conversation, system=None):
    import requests as _req
    api_key = frappe.conf.get("groq_api_key", "")
    if not api_key:
        raise Exception("groq_api_key not configured in site_config.json")
    resp = _req.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "system", "content": system or _AI_SYSTEM_PROMPT}] + conversation,
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": 600,
        },
        timeout=15,
    )
    if resp.status_code == 429:
        raise _RateLimit("Groq rate limit")
    resp.raise_for_status()
    return json.loads(resp.json()["choices"][0]["message"]["content"])


def _call_gemini(conversation, system=None):
    import requests as _req
    api_key = frappe.conf.get("gemini_api_key", "")
    if not api_key:
        raise Exception("gemini_api_key not configured in site_config.json")
    sys_prompt = system or _AI_SYSTEM_PROMPT
    contents = [
        {"role": "user",  "parts": [{"text": sys_prompt + "\n\nAcknowledge you understand."}]},
        {"role": "model", "parts": [{"text": '{"intent":"greeting","reply":"Understood, ready."}'}]},
    ]
    for m in conversation:
        role = "model" if m["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    resp = _req.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}",
        json={
            "contents": contents,
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2, "maxOutputTokens": 600},
        },
        timeout=20,
    )
    if resp.status_code == 429:
        raise _RateLimit("Gemini rate limit")
    resp.raise_for_status()
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


def _llm_parse(conversation, system=None):
    """Groq primary → Gemini fallback."""
    try:
        return _call_groq(conversation, system=system)
    except _RateLimit:
        frappe.log_error("Groq rate limit — using Gemini fallback", "AI Fallback")
        return _call_gemini(conversation, system=system)
    except Exception as exc:
        frappe.log_error(str(exc), "Groq error — using Gemini fallback")
        try:
            return _call_gemini(conversation, system=system)
        except Exception as exc2:
            frappe.log_error(str(exc2), "Gemini fallback also failed")
            raise


@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_ai_alerts():
    """Proactive business alerts — overdue invoices, due-soon, revenue drop."""
    from frappe.utils import nowdate, add_days, get_first_day, add_months, getdate
    import datetime
    company = _get_company(frappe.session.user)
    today   = nowdate()
    alerts  = []
    try:
        # Overdue invoices
        od = frappe.db.sql("""
            SELECT COUNT(*) cnt, COALESCE(SUM(outstanding_amount),0) tot
            FROM `tabSales Invoice`
            WHERE docstatus=1 AND outstanding_amount>0 AND due_date<%s AND company=%s
        """, (today, company), as_dict=True)[0]
        if int(od.cnt or 0):
            alerts.append({
                "type": "overdue", "icon": "⚠️",
                "text": f"{od.cnt} overdue invoice{'s' if int(od.cnt)!=1 else ''} — ₹{float(od.tot or 0):,.0f}",
                "action": "show_overdue",
            })
        # Due within 3 days (but not overdue)
        in3 = add_days(today, 3)
        soon = frappe.db.sql("""
            SELECT COUNT(*) cnt, COALESCE(SUM(outstanding_amount),0) tot
            FROM `tabSales Invoice`
            WHERE docstatus=1 AND outstanding_amount>0 AND due_date BETWEEN %s AND %s AND company=%s
        """, (today, in3, company), as_dict=True)[0]
        if int(soon.cnt or 0):
            alerts.append({
                "type": "due_soon", "icon": "🔔",
                "text": f"{soon.cnt} invoice{'s' if int(soon.cnt)!=1 else ''} due within 3 days — ₹{float(soon.tot or 0):,.0f}",
                "action": "show_unpaid",
            })
        # Low stock items
        try:
            ls = frappe.db.sql("""
                SELECT COUNT(DISTINCT i.item_code) AS cnt
                FROM `tabItem` i
                LEFT JOIN `tabBin` b ON b.item_code = i.item_code
                WHERE i.is_stock_item=1 AND i.disabled=0 AND i.reorder_level>0
                GROUP BY i.item_code HAVING COALESCE(SUM(b.actual_qty),0) <= i.reorder_level
            """, as_dict=True)
            ls_cnt = len(ls)
            if ls_cnt:
                alerts.append({
                    "type": "low_stock", "icon": "📦",
                    "text": f"{ls_cnt} item{'s' if ls_cnt != 1 else ''} at or below reorder level",
                    "action": "show_items",
                })
        except Exception:
            pass
        # Revenue drop vs last month
        this_start = get_first_day(today).strftime("%Y-%m-%d")
        last_start = get_first_day(add_months(today, -1)).strftime("%Y-%m-%d")
        last_end   = (getdate(this_start) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        this_rev = float(frappe.db.sql("""
            SELECT COALESCE(SUM(grand_total),0) tot FROM `tabSales Invoice`
            WHERE docstatus=1 AND company=%s AND posting_date>=%s
        """, (company, this_start))[0][0] or 0)
        last_rev = float(frappe.db.sql("""
            SELECT COALESCE(SUM(grand_total),0) tot FROM `tabSales Invoice`
            WHERE docstatus=1 AND company=%s AND posting_date BETWEEN %s AND %s
        """, (company, last_start, last_end))[0][0] or 0)
        if last_rev > 0 and this_rev < last_rev * 0.6:
            drop = int((1 - this_rev / last_rev) * 100)
            alerts.append({
                "type": "revenue_drop", "icon": "📉",
                "text": f"Revenue is down {drop}% vs last month",
                "action": None,
            })
    except Exception as exc:
        frappe.log_error(str(exc), "AI Alerts")
    return {"alerts": alerts, "count": len(alerts)}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def ai_enhance_email(subject, body, invoice_name=None):
    """AI-powered email enhancement for the email compose modal."""
    context = ""
    if invoice_name:
        try:
            inv = frappe.get_doc("Sales Invoice", invoice_name)
            context = (f"Invoice {inv.name} for {inv.customer_name or inv.customer}, "
                       f"amount ₹{flt(inv.grand_total):,.2f}, due date {inv.due_date or 'N/A'}.")
        except Exception:
            pass
    prompt = (
        f"Context: {context}\n"
        f"Current subject: {subject}\n"
        f"Current body:\n{body}\n\n"
        "Improve this email. Make it professional, warm, and concise."
    )
    try:
        result = _llm_parse([{"role": "user", "content": prompt}], system=_EMAIL_SYSTEM_PROMPT)
        return {
            "subject": result.get("subject") or subject,
            "body":    result.get("body")    or body,
        }
    except Exception as exc:
        frappe.log_error(str(exc), "AI Enhance Email")
        return {"subject": subject, "body": body}


@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_customer_outstanding():
    """Return {customer_name: outstanding_amount} for all customers with open invoices
    or a non-zero opening balance."""
    company = _get_company(frappe.session.user)
    rows = frappe.db.sql("""
        SELECT customer, COALESCE(SUM(outstanding_amount), 0) AS outstanding
        FROM `tabSales Invoice`
        WHERE docstatus=1 AND outstanding_amount>0 AND company=%s
        GROUP BY customer
    """, company, as_dict=True)
    out = {r.customer: float(r.outstanding or 0) for r in rows}

    openings = frappe.db.sql("""
        SELECT name, opening_balance FROM `tabCustomer`
        WHERE books_company=%s AND opening_balance IS NOT NULL AND opening_balance != 0
    """, company, as_dict=True)
    for o in openings:
        out[o.name] = out.get(o.name, 0) + float(o.opening_balance or 0)
    return out


@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_customer_last_invoice():
    """Return {customer: {name, date, amount}} of the most recent submitted Sales Invoice."""
    company = _get_company(frappe.session.user)
    rows = frappe.db.sql("""
        SELECT customer, name, posting_date, grand_total
        FROM `tabSales Invoice`
        WHERE docstatus=1 AND is_return=0 AND company=%s
        ORDER BY posting_date DESC, creation DESC
    """, company, as_dict=True)
    out = {}
    for r in rows:
        if r.customer not in out:   # first row per customer = most recent
            out[r.customer] = {
                "name": r.name,
                "date": str(r.posting_date) if r.posting_date else "",
                "amount": float(r.grand_total or 0),
            }
    return out


@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_vendor_last_bill():
    """Return {supplier: {name, date, amount}} of the most recent submitted Purchase Invoice."""
    company = _get_company(frappe.session.user)
    rows = frappe.db.sql("""
        SELECT supplier, name, posting_date, grand_total
        FROM `tabPurchase Invoice`
        WHERE docstatus=1 AND is_return=0 AND company=%s
        ORDER BY posting_date DESC, creation DESC
    """, company, as_dict=True)
    out = {}
    for r in rows:
        if r.supplier not in out:   # first row per supplier = most recent
            out[r.supplier] = {
                "name": r.name,
                "date": str(r.posting_date) if r.posting_date else "",
                "amount": float(r.grand_total or 0),
            }
    return out


@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_vendor_outstanding():
    """Return {supplier: outstanding_amount} for all suppliers with open bills
    or a non-zero opening balance."""
    company = _get_company(frappe.session.user)
    rows = frappe.db.sql("""
        SELECT supplier, COALESCE(SUM(outstanding_amount), 0) AS outstanding
        FROM `tabPurchase Invoice`
        WHERE docstatus=1 AND is_return=0 AND outstanding_amount>0 AND company=%s
        GROUP BY supplier
    """, company, as_dict=True)
    out = {r.supplier: float(r.outstanding or 0) for r in rows}

    openings = frappe.db.sql("""
        SELECT name, opening_balance FROM `tabSupplier`
        WHERE books_company=%s AND opening_balance IS NOT NULL AND opening_balance != 0
    """, company, as_dict=True)
    for o in openings:
        out[o.name] = out.get(o.name, 0) + float(o.opening_balance or 0)
    return out


_PRO_MODE_ADDENDUM = """

═══════════════════════════════════════════════════
PRO MODE — FULL APP CONTROL ENABLED
═══════════════════════════════════════════════════
You can now create and modify data. Always show a preview first using the _confirm variant.
After the user confirms (clicks the button or says yes/confirm/ok/proceed), use the non-confirm variant.

PRO CONFIRM intents (show preview card — never skip this step):
- "create_customer_confirm"   → Add: "customer_name":"...", "email":"...", "mobile_no":"..."
- "create_supplier_confirm"   → Add: "supplier_name":"...", "email":"...", "mobile_no":"..."
- "create_item_confirm"       → Add: "item_name":"...", "item_type":"Product|Service|Raw Material|Finished Good", "item_group":"...", "rate":N, "uom":"Nos"
- "create_quotation_confirm"  → Add: "customer":"...", "items":[{"item_name":"..","qty":N,"rate":N}]
- "create_payment_confirm"    → Add: "invoice":"INV-...", "amount":N, "mode":"Cash|Bank|Cheque", "customer":"..."
- "cancel_invoice_confirm"    → Add: "invoice":"INV-...", "customer":"...", "amount":N
- "update_item_price_confirm" → Add: "item_name":"...", "new_rate":N
- "create_purchase_order_confirm" → Add: "supplier":"...", "item_code":"...", "qty":N, "rate":N

PRO EXECUTE intents (only after user explicitly confirms):
- "create_customer"         — same fields as confirm
- "create_supplier"         — same fields as confirm
- "create_item"             — same fields as confirm
- "create_quotation"        — same fields as confirm
- "create_payment"          — same fields as confirm
- "cancel_invoice"          — Add: "invoice":"INV-..."
- "update_item_price"       — same fields as confirm
- "create_purchase_order"   — same fields as confirm

PRO RULES:
- ALWAYS use _confirm first. NEVER execute without showing a preview.
- cancel_invoice_confirm: warn "This cannot be easily undone."
- If you need more info before confirming, use "ask_for_info".
- If user cancels → "thanks" intent.
"""


@frappe.whitelist(allow_guest=False, methods=["POST"])
def ai_chat(messages, pro_mode=0, system=None):
    """
    Books AI — LLM-powered (Groq primary, Gemini fallback).
    Response: {reply: str, action: str|None, ...action_params}
    """
    if isinstance(messages, str):
        messages = json.loads(messages)

    # Keep last 14 turns to stay within token budget
    conversation = [
        {"role": m["role"], "content": m["content"]}
        for m in messages
        if m.get("role") in ("user", "assistant") and m.get("content")
    ][-14:]

    if not conversation:
        return {"reply": "I didn't catch that — what would you like to do?"}

    company = _get_company(frappe.session.user)
    sys_prompt = (_AI_SYSTEM_PROMPT + _PRO_MODE_ADDENDUM) if int(pro_mode or 0) else _AI_SYSTEM_PROMPT

    try:
        parsed = _llm_parse(conversation, system=sys_prompt)
    except Exception as exc:
        frappe.log_error(str(exc), "AI Chat — both LLMs failed")
        return {"reply": "The AI assistant is temporarily unavailable. Please try again in a moment."}

    intent = parsed.get("intent", "unknown")
    reply  = (parsed.get("reply") or "").strip()

    # ── DATA INTENTS — real DB numbers, never hallucinated ───────────────────
    if intent == "revenue":
        from_d, to_d, label = _ai_parse_period(parsed.get("period", "this_month"))
        try:
            row = frappe.db.sql("""
                SELECT COALESCE(SUM(grand_total),0) AS total, COUNT(*) AS cnt
                FROM `tabSales Invoice`
                WHERE docstatus=1 AND company=%s AND posting_date BETWEEN %s AND %s
            """, (company, from_d, to_d), as_dict=True)[0]
            return {"reply": f"📈 Revenue — {label}\n\nTotal: ₹{float(row.total or 0):,.2f}\nInvoices: {int(row.cnt or 0)}"}
        except Exception as e:
            frappe.log_error(str(e), "AI Revenue")
            return {"reply": "Couldn't fetch revenue data right now."}

    if intent == "outstanding":
        try:
            row = frappe.db.sql("""
                SELECT COALESCE(SUM(outstanding_amount),0) AS total, COUNT(*) AS cnt
                FROM `tabSales Invoice` WHERE docstatus=1 AND outstanding_amount>0 AND company=%s
            """, company, as_dict=True)[0]
            od = frappe.db.sql("""
                SELECT COALESCE(SUM(outstanding_amount),0) AS total, COUNT(*) AS cnt
                FROM `tabSales Invoice`
                WHERE docstatus=1 AND outstanding_amount>0 AND due_date<%s AND company=%s
            """, (nowdate(), company), as_dict=True)[0]
            msg = f"💰 Outstanding Receivables\n\nTotal: ₹{float(row.total or 0):,.2f} ({int(row.cnt or 0)} invoices)"
            if int(od.cnt or 0):
                msg += f"\nOf which overdue: ₹{float(od.total or 0):,.2f} ({int(od.cnt)} invoices)"
            return {"reply": msg, "action": "show_outstanding"}
        except Exception as e:
            frappe.log_error(str(e), "AI Outstanding")
            return {"reply": "Couldn't fetch outstanding data."}

    if intent == "top_customers":
        limit = min(int(parsed.get("limit") or 5), 10)
        try:
            rows = frappe.db.sql("""
                SELECT customer, SUM(grand_total) AS total, COUNT(*) AS cnt
                FROM `tabSales Invoice` WHERE docstatus=1 AND company=%s
                GROUP BY customer ORDER BY total DESC LIMIT %s
            """, (company, limit), as_dict=True)
            if not rows:
                return {"reply": "No invoice data found yet."}
            lines = "\n".join(
                f"{i+1}. {r.customer} — ₹{float(r.total):,.0f} ({int(r.cnt)} inv)"
                for i, r in enumerate(rows)
            )
            return {"reply": f"🏆 Top {limit} Customers\n\n{lines}"}
        except Exception as e:
            frappe.log_error(str(e), "AI Top Customers")
            return {"reply": "Couldn't fetch customer data."}

    if intent == "overdue_count":
        try:
            row = frappe.db.sql("""
                SELECT COUNT(*) AS cnt, COALESCE(SUM(outstanding_amount),0) AS total
                FROM `tabSales Invoice`
                WHERE docstatus=1 AND outstanding_amount>0 AND due_date<%s AND company=%s
            """, (nowdate(), company), as_dict=True)[0]
            cnt = int(row.cnt or 0)
            if cnt == 0:
                return {"reply": "✅ No overdue invoices — all caught up!"}
            return {"reply": f"⚠️ Overdue Invoices\n\nCount: {cnt}\nTotal: ₹{float(row.total or 0):,.2f}",
                    "action": "show_overdue"}
        except Exception as e:
            frappe.log_error(str(e), "AI Overdue Count")
            return {"reply": "Couldn't fetch overdue data."}

    if intent == "unpaid_bills":
        try:
            row = frappe.db.sql("""
                SELECT COUNT(*) AS cnt, COALESCE(SUM(outstanding_amount),0) AS total
                FROM `tabPurchase Invoice` WHERE docstatus=1 AND outstanding_amount>0 AND company=%s
            """, company, as_dict=True)[0]
            cnt = int(row.cnt or 0)
            if cnt == 0:
                return {"reply": "✅ No unpaid bills — you're all clear!", "action": "show_bills"}
            return {"reply": f"🧾 Unpaid Bills\n\nCount: {cnt}\nTotal: ₹{float(row.total or 0):,.2f}",
                    "action": "show_bills"}
        except Exception as e:
            frappe.log_error(str(e), "AI Bills")
            return {"reply": "Couldn't fetch bills data.", "action": "show_bills"}

    if intent == "payment_received":
        from_d, to_d, label = _ai_parse_period(parsed.get("period", "this_month"))
        try:
            row = frappe.db.sql("""
                SELECT COALESCE(SUM(paid_amount),0) AS total, COUNT(*) AS cnt
                FROM `tabPayment Entry`
                WHERE docstatus=1 AND payment_type='Receive' AND company=%s AND posting_date BETWEEN %s AND %s
            """, (company, from_d, to_d), as_dict=True)[0]
            return {"reply": f"💵 Payments Received — {label}\n\nTotal collected: ₹{float(row.total or 0):,.2f}\nPayment entries: {int(row.cnt or 0)}"}
        except Exception as e:
            frappe.log_error(str(e), "AI Payment Received")
            return {"reply": "Couldn't fetch payment data."}

    if intent == "expense_total":
        from_d, to_d, label = _ai_parse_period(parsed.get("period", "this_month"))
        try:
            row = frappe.db.sql("""
                SELECT COALESCE(SUM(grand_total),0) AS total, COUNT(*) AS cnt
                FROM `tabPurchase Invoice`
                WHERE docstatus=1 AND company=%s AND posting_date BETWEEN %s AND %s
            """, (company, from_d, to_d), as_dict=True)[0]
            return {"reply": f"🧾 Expenses — {label}\n\nTotal purchase amount: ₹{float(row.total or 0):,.2f}\nBills: {int(row.cnt or 0)}"}
        except Exception as e:
            frappe.log_error(str(e), "AI Expense Total")
            return {"reply": "Couldn't fetch expense data."}

    if intent == "profit_estimate":
        from_d, to_d, label = _ai_parse_period(parsed.get("period", "this_month"))
        try:
            rev = float(frappe.db.sql("""
                SELECT COALESCE(SUM(grand_total),0) FROM `tabSales Invoice`
                WHERE docstatus=1 AND company=%s AND posting_date BETWEEN %s AND %s
            """, (company, from_d, to_d))[0][0] or 0)
            exp = float(frappe.db.sql("""
                SELECT COALESCE(SUM(grand_total),0) FROM `tabPurchase Invoice`
                WHERE docstatus=1 AND company=%s AND posting_date BETWEEN %s AND %s
            """, (company, from_d, to_d))[0][0] or 0)
            profit = rev - exp
            sign = "📈" if profit >= 0 else "📉"
            return {"reply": f"{sign} Profit Estimate — {label}\n\nRevenue: ₹{rev:,.2f}\nExpenses: ₹{exp:,.2f}\nNet: ₹{profit:,.2f}\n\n(Estimate only — excludes non-invoice transactions)"}
        except Exception as e:
            frappe.log_error(str(e), "AI Profit Estimate")
            return {"reply": "Couldn't compute profit estimate."}

    if intent == "top_suppliers":
        limit = min(int(parsed.get("limit") or 5), 10)
        try:
            rows = frappe.db.sql("""
                SELECT supplier, SUM(grand_total) AS total, COUNT(*) AS cnt
                FROM `tabPurchase Invoice` WHERE docstatus=1 AND company=%s
                GROUP BY supplier ORDER BY total DESC LIMIT %s
            """, (company, limit), as_dict=True)
            if not rows:
                return {"reply": "No purchase data found yet."}
            lines = "\n".join(
                f"{i+1}. {r.supplier} — ₹{float(r.total):,.0f} ({int(r.cnt)} bills)"
                for i, r in enumerate(rows)
            )
            return {"reply": f"🏭 Top {limit} Suppliers\n\n{lines}"}
        except Exception as e:
            frappe.log_error(str(e), "AI Top Suppliers")
            return {"reply": "Couldn't fetch supplier data."}

    # ── INVENTORY INTENTS ─────────────────────────────────────────────────────
    if intent == "inventory_items":
        try:
            ig = (parsed.get("item_group") or "").strip()
            it = (parsed.get("item_type") or "").strip()
            where = ["disabled=0"]
            params = []
            if ig:
                where.append("item_group=%s"); params.append(ig)
            if it:
                where.append("item_type=%s"); params.append(it)
            w = " AND ".join(where)
            row = frappe.db.sql(f"""
                SELECT COUNT(*) AS cnt, COALESCE(SUM(is_stock_item),0) AS stock_cnt
                FROM `tabItem` WHERE {w}
            """, params, as_dict=True)[0]
            total = int(row.cnt or 0)
            stock = int(row.stock_cnt or 0)
            desc = ""
            if ig: desc += f" in group '{ig}'"
            if it: desc += f" of type '{it}'"
            return {"reply": f"📦 Items{desc}\n\nTotal active: {total}\nInventory tracked: {stock}\nNon-stock / service: {total - stock}",
                    "action": "show_items"}
        except Exception as e:
            frappe.log_error(str(e), "AI Inventory Items")
            return {"reply": "Couldn't fetch item data."}

    if intent == "low_stock":
        try:
            rows = frappe.db.sql("""
                SELECT i.item_name, i.item_code, i.reorder_level,
                       COALESCE(SUM(b.actual_qty),0) AS actual_qty
                FROM `tabItem` i
                LEFT JOIN `tabBin` b ON b.item_code = i.item_code
                WHERE i.is_stock_item=1 AND i.disabled=0 AND i.reorder_level>0
                GROUP BY i.item_code, i.item_name, i.reorder_level
                HAVING actual_qty <= i.reorder_level
                ORDER BY actual_qty ASC
                LIMIT 10
            """, as_dict=True)
            if not rows:
                return {"reply": "✅ All items are above their reorder levels — stock looks healthy!"}
            lines = "\n".join(
                f"• {r.item_name}: {int(r.actual_qty)} in stock (reorder at {int(r.reorder_level)})"
                for r in rows
            )
            return {"reply": f"⚠️ Low Stock Items ({len(rows)} found)\n\n{lines}", "action": "show_items"}
        except Exception as e:
            frappe.log_error(str(e), "AI Low Stock")
            return {"reply": "Couldn't fetch stock data."}

    if intent == "top_selling_items":
        from_d, to_d, label = _ai_parse_period(parsed.get("period", "this_month"))
        limit = min(int(parsed.get("limit") or 5), 10)
        try:
            rows = frappe.db.sql("""
                SELECT ii.item_name, SUM(ii.qty) AS total_qty, SUM(ii.amount) AS total_amt
                FROM `tabSales Invoice Item` ii
                JOIN `tabSales Invoice` si ON si.name = ii.parent
                WHERE si.docstatus=1 AND si.company=%s AND si.posting_date BETWEEN %s AND %s
                GROUP BY ii.item_name ORDER BY total_qty DESC LIMIT %s
            """, (company, from_d, to_d, limit), as_dict=True)
            if not rows:
                return {"reply": f"No sales data for {label}."}
            lines = "\n".join(
                f"{i+1}. {r.item_name} — {int(r.total_qty or 0)} units (₹{float(r.total_amt or 0):,.0f})"
                for i, r in enumerate(rows)
            )
            return {"reply": f"🔥 Top {limit} Selling Items — {label}\n\n{lines}"}
        except Exception as e:
            frappe.log_error(str(e), "AI Top Selling Items")
            return {"reply": "Couldn't fetch sales item data."}

    if intent == "item_groups_summary":
        try:
            groups = frappe.db.sql("""
                SELECT g.name, COUNT(i.name) AS item_cnt
                FROM `tabItem Group` g
                LEFT JOIN `tabItem` i ON i.item_group = g.name AND i.disabled=0
                WHERE g.is_group=0
                GROUP BY g.name ORDER BY item_cnt DESC LIMIT 10
            """, as_dict=True)
            total_groups = frappe.db.count("Item Group")
            if not groups:
                return {"reply": "No item groups found yet.", "action": "show_item_groups"}
            lines = "\n".join(f"• {r.name}: {int(r.item_cnt or 0)} items" for r in groups)
            return {"reply": f"📁 Item Groups (top {len(groups)} of {total_groups} total)\n\n{lines}",
                    "action": "show_item_groups"}
        except Exception as e:
            frappe.log_error(str(e), "AI Item Groups Summary")
            return {"reply": "Couldn't fetch item group data."}

    if intent == "stock_value":
        try:
            row = frappe.db.sql("""
                SELECT COALESCE(SUM(actual_qty * valuation_rate), 0) AS total_value,
                       COUNT(DISTINCT item_code) AS item_cnt
                FROM `tabBin`
                WHERE actual_qty > 0
            """, as_dict=True)[0]
            val = float(row.total_value or 0)
            items = int(row.item_cnt or 0)
            return {"reply": f"🏭 Total Stock Value\n\n₹{val:,.2f} across {items} item{'s' if items != 1 else ''} in stock"}
        except Exception as e:
            frappe.log_error(str(e), "AI Stock Value")
            return {"reply": "Couldn't fetch stock value."}

    # ── BUSINESS SUMMARY (Tier 5-C) ──────────────────────────────────────────
    if intent == "business_summary":
        try:
            today = nowdate()
            from_m, to_m, _ = _ai_parse_period("this_month")
            from_lm, to_lm, _ = _ai_parse_period("last_month")
            rev_m  = float(frappe.db.sql("SELECT COALESCE(SUM(grand_total),0) FROM `tabSales Invoice` WHERE docstatus=1 AND company=%s AND posting_date BETWEEN %s AND %s", (company, from_m, to_m))[0][0] or 0)
            rev_lm = float(frappe.db.sql("SELECT COALESCE(SUM(grand_total),0) FROM `tabSales Invoice` WHERE docstatus=1 AND company=%s AND posting_date BETWEEN %s AND %s", (company, from_lm, to_lm))[0][0] or 0)
            outstd = frappe.db.sql("SELECT COALESCE(SUM(outstanding_amount),0) cnt_tot, COUNT(*) cnt FROM `tabSales Invoice` WHERE docstatus=1 AND outstanding_amount>0 AND company=%s", company, as_dict=True)[0]
            overdue = frappe.db.sql("SELECT COUNT(*) cnt, COALESCE(SUM(outstanding_amount),0) tot FROM `tabSales Invoice` WHERE docstatus=1 AND outstanding_amount>0 AND due_date<%s AND company=%s", (today, company), as_dict=True)[0]
            top_cust = frappe.db.sql("SELECT customer, SUM(grand_total) tot FROM `tabSales Invoice` WHERE docstatus=1 AND company=%s GROUP BY customer ORDER BY tot DESC LIMIT 1", company, as_dict=True)
            bills = frappe.db.sql("SELECT COALESCE(SUM(outstanding_amount),0) tot FROM `tabPurchase Invoice` WHERE docstatus=1 AND outstanding_amount>0 AND company=%s", company)[0][0] or 0
            trend = ""
            if rev_lm > 0:
                pct = int((rev_m - rev_lm) / rev_lm * 100)
                trend = f"up {pct}%" if pct >= 0 else f"down {abs(pct)}%"
            data_ctx = (
                f"This month revenue: ₹{rev_m:,.0f} ({trend + ' vs last month' if trend else 'first month data'}).\n"
                f"Last month revenue: ₹{rev_lm:,.0f}.\n"
                f"Outstanding receivables: ₹{float(outstd.cnt_tot or 0):,.0f} ({int(outstd.cnt or 0)} invoices).\n"
                f"Overdue: {int(overdue.cnt or 0)} invoices worth ₹{float(overdue.tot or 0):,.0f}.\n"
                f"Top customer: {top_cust[0].customer if top_cust else 'N/A'}.\n"
                f"Unpaid bills owed: ₹{float(bills):,.0f}."
            )
            summary = _llm_parse([{"role": "user", "content": data_ctx}], system=_SUMMARY_SYSTEM_PROMPT)
            return {"reply": summary.get("reply", data_ctx)}
        except Exception as e:
            frappe.log_error(str(e), "AI Business Summary")
            return {"reply": "Couldn't generate summary right now."}

    # ── PRO MODE — CONFIRM PREVIEWS (LLM pass-through, execution via ai_execute_pro_action) ──
    _pro_confirm_intents = {
        "create_customer_confirm", "create_supplier_confirm", "create_item_confirm",
        "create_quotation_confirm", "create_payment_confirm",
        "cancel_invoice_confirm", "update_item_price_confirm",
        "create_purchase_order_confirm",
    }
    if intent in _pro_confirm_intents:
        result = {"reply": reply or "Here's what I'll do — confirm to proceed.", "action": intent}
        for k in ("customer_name", "supplier_name", "item_name", "item_type", "item_group",
                  "rate", "uom", "email", "mobile_no", "customer", "items",
                  "invoice", "amount", "mode", "new_rate", "old_rate",
                  "supplier", "item_code", "qty"):
            if parsed.get(k) is not None:
                result[k] = parsed[k]
        # Enrich cancel/payment with live invoice data
        if intent in ("cancel_invoice_confirm", "create_payment_confirm"):
            inv_name = (parsed.get("invoice") or "").strip()
            if inv_name:
                try:
                    inv = frappe.get_doc("Sales Invoice", inv_name)
                    result.setdefault("customer", inv.customer_name or inv.customer)
                    result.setdefault("amount", float(inv.outstanding_amount or inv.grand_total))
                except Exception:
                    pass
        if intent == "update_item_price_confirm":
            item_n = (parsed.get("item_name") or "").strip()
            if item_n and not parsed.get("old_rate"):
                try:
                    result["old_rate"] = float(frappe.db.get_value("Item", item_n, "standard_rate") or 0)
                except Exception:
                    pass
        return result

    # PRO MODE — EXECUTE (typed confirm path — button confirm goes via ai_execute_pro_action)
    _pro_execute_intents = {
        "create_customer", "create_supplier", "create_item",
        "create_quotation", "create_payment", "cancel_invoice", "update_item_price",
        "create_purchase_order",
    }
    if intent in _pro_execute_intents:
        return _run_pro_action(intent, parsed, company)

    # ── NAVIGATION INTENTS ────────────────────────────────────────────────────
    _simple_nav = {"show_overdue", "show_unpaid", "show_all_invoices", "show_bills",
                   "show_quotes", "show_customers", "show_suppliers", "show_sales_orders",
                   "show_purchase_orders", "show_dashboard",
                   "show_items", "show_item_groups", "show_warehouses", "show_inventory"}
    if intent in _simple_nav:
        return {"reply": reply or "Navigating now.", "action": intent}

    if intent == "find_invoices":
        customer = (parsed.get("customer") or "").strip()
        return {"reply": reply or f"Showing invoices for {customer}.", "action": "find_invoices", "customer": customer}

    if intent == "navigate":
        return {"reply": reply or "Navigating.", "action": "navigate", "path": parsed.get("path", "/")}

    # ── CREATION WIZARD (Tier 5-A) ────────────────────────────────────────────
    if intent == "ask_for_info":
        return {"reply": reply or "What details should I include?"}

    if intent == "create_invoice_confirm":
        result = {"reply": reply or "Here's what I'll create — confirm to proceed.", "action": "create_invoice_confirm"}
        if parsed.get("customer"): result["customer"] = parsed["customer"]
        if parsed.get("items"):    result["items"]    = parsed["items"]
        return result

    if intent == "create_invoice":
        result = {"reply": reply or "Opening new invoice.", "action": "create_invoice"}
        if parsed.get("customer"): result["customer"] = parsed["customer"]
        if parsed.get("items"):    result["items"]    = parsed["items"]
        return result

    # ── CONVERSATIONAL + UNKNOWN ──────────────────────────────────────────────
    return {"reply": reply or "I'm not sure about that. Type \"help\" to see what I can do."}


def _run_pro_action(action, data, company):
    """Execute a confirmed pro-mode action. `data` is a dict of parameters."""
    try:
        if action == "create_customer":
            name = (data.get("customer_name") or "").strip()
            if not name: return {"reply": "Customer name is required."}
            doc = frappe.new_doc("Customer")
            doc.customer_name = name
            doc.customer_group = "All Customer Groups"
            doc.customer_type  = "Individual"
            if data.get("email"):     doc.email_id   = data["email"]
            if data.get("mobile_no"): doc.mobile_no  = data["mobile_no"]
            doc.insert(ignore_permissions=True)
            return {"reply": f"✅ Customer **{name}** created.", "action": "show_customers"}

        if action == "create_supplier":
            name = (data.get("supplier_name") or "").strip()
            if not name: return {"reply": "Supplier name is required."}
            doc = frappe.new_doc("Supplier")
            doc.supplier_name  = name
            doc.supplier_group = "All Supplier Groups"
            doc.supplier_type  = "Individual"
            if data.get("email"):     doc.email_id  = data["email"]
            if data.get("mobile_no"): doc.mobile_no = data["mobile_no"]
            doc.insert(ignore_permissions=True)
            return {"reply": f"✅ Supplier **{name}** created.", "action": "show_suppliers"}

        if action == "create_item":
            name = (data.get("item_name") or "").strip()
            if not name: return {"reply": "Item name is required."}
            doc = frappe.new_doc("Item")
            doc.item_name  = name
            doc.item_code  = name
            doc.item_type  = data.get("item_type", "Product") or "Product"
            doc.item_group = data.get("item_group") or "All Item Groups"
            doc.stock_uom  = data.get("uom", "Nos") or "Nos"
            doc.standard_rate = float(data.get("rate") or 0)
            doc.insert(ignore_permissions=True)
            return {"reply": f"✅ Item **{name}** created at ₹{doc.standard_rate:,.2f}.", "action": "show_items"}

        if action == "create_quotation":
            customer = (data.get("customer") or "").strip()
            items    = data.get("items") or []
            if not customer: return {"reply": "Customer name is required."}
            if not items:    return {"reply": "Add at least one item to the quotation."}
            doc = frappe.new_doc("Quotation")
            doc.quotation_to     = "Customer"
            doc.party_name       = customer
            doc.transaction_date = nowdate()
            doc.company          = company
            for it in items:
                doc.append("items", {
                    "item_name": it.get("item_name", ""),
                    "item_code": it.get("item_name", ""),
                    "qty":       float(it.get("qty") or 1),
                    "rate":      float(it.get("rate") or 0),
                })
            doc.insert(ignore_permissions=True)
            return {"reply": f"✅ Quotation **{doc.name}** created for {customer} ({len(items)} item(s)).", "action": "show_quotes"}

        if action == "create_payment":
            inv_name = (data.get("invoice") or "").strip()
            amount   = float(data.get("amount") or 0)
            mode     = data.get("mode", "Cash") or "Cash"
            if not inv_name: return {"reply": "Invoice name is required to record a payment."}
            inv = frappe.get_doc("Sales Invoice", inv_name)
            if not amount: amount = float(inv.outstanding_amount)
            pe = frappe.new_doc("Payment Entry")
            pe.payment_type     = "Receive"
            pe.party_type       = "Customer"
            pe.party            = inv.customer
            pe.party_name       = inv.customer_name or inv.customer
            pe.company          = inv.company
            pe.posting_date     = nowdate()
            pe.mode_of_payment  = mode
            pe.paid_amount      = amount
            pe.received_amount  = amount
            pe.paid_to = (
                frappe.db.get_value("Company", inv.company, "default_bank_account") or
                frappe.db.get_value("Account", {"account_type": "Cash", "company": inv.company}, "name") or ""
            )
            pe.append("references", {
                "reference_doctype":   "Sales Invoice",
                "reference_name":      inv_name,
                "outstanding_amount":  inv.outstanding_amount,
                "allocated_amount":    min(amount, float(inv.outstanding_amount)),
            })
            pe.insert(ignore_permissions=True)
            pe.submit()
            status = "fully paid ✅" if amount >= float(inv.outstanding_amount) else "partially paid"
            return {"reply": f"✅ Payment of ₹{amount:,.2f} recorded for **{inv_name}** — now {status}.", "action": "show_all_invoices"}

        if action == "cancel_invoice":
            inv_name = (data.get("invoice") or "").strip()
            if not inv_name: return {"reply": "Invoice name is required."}
            inv = frappe.get_doc("Sales Invoice", inv_name)
            if inv.docstatus != 1:
                return {"reply": f"**{inv_name}** is not submitted (status: {inv.docstatus}). Only submitted invoices can be cancelled."}
            inv.cancel()
            return {"reply": f"✅ Invoice **{inv_name}** has been cancelled.", "action": "show_all_invoices"}

        if action == "update_item_price":
            item_name = (data.get("item_name") or "").strip()
            new_rate  = float(data.get("new_rate") or 0)
            if not item_name: return {"reply": "Item name is required."}
            frappe.db.set_value("Item", item_name, "standard_rate", new_rate)
            frappe.db.commit()
            return {"reply": f"✅ **{item_name}** price updated to ₹{new_rate:,.2f}.", "action": "show_items"}

        if action == "create_purchase_order":
            supplier  = (data.get("supplier") or "").strip()
            item_code = (data.get("item_code") or "").strip()
            qty       = float(data.get("qty") or 1)
            rate      = float(data.get("rate") or 0)
            if not supplier:  return {"reply": "Supplier name is required."}
            if not item_code: return {"reply": "Item code is required."}
            # Create and submit Purchase Order
            po = frappe.new_doc("Purchase Order")
            po.supplier      = supplier
            po.company       = company
            po.schedule_date = frappe.utils.add_days(nowdate(), 7)
            po.append("items", {
                "item_code":     item_code,
                "qty":           qty,
                "rate":          rate,
                "schedule_date": po.schedule_date,
            })
            po.insert(ignore_permissions=True)
            po.submit()
            # Also create a Material Receipt so stock is available immediately
            default_wh = (
                frappe.db.get_value("Warehouse", {"company": company, "is_group": 0}, "name") or
                frappe.db.get_value("Warehouse", {"is_group": 0}, "name") or ""
            )
            if default_wh:
                se = frappe.new_doc("Stock Entry")
                se.stock_entry_type = "Material Receipt"
                se.company          = company
                se.append("items", {
                    "item_code":  item_code,
                    "qty":        qty,
                    "basic_rate": rate,
                    "t_warehouse": default_wh,
                })
                se.insert(ignore_permissions=True)
                se.submit()
            frappe.db.commit()
            return {
                "reply": f"✅ Purchase order created and **{int(qty)} unit(s) of {item_code}** received into stock. You can now proceed with the invoice.",
                "action": None,
            }

        return {"reply": f"Unknown pro action: {action}"}
    except Exception as e:
        frappe.log_error(str(e), f"AI Pro Action — {action}")
        return {"reply": f"Action failed: {str(e)}"}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def ai_execute_pro_action(action, data):
    """
    Execute a confirmed pro-mode action directly (no LLM — button-confirm path).
    Called by the frontend when user clicks ✓ Confirm on a pro action card.
    """
    if isinstance(data, str):
        data = json.loads(data)
    company = _get_company(frappe.session.user)
    return _run_pro_action(action, data, company)


# ── COST CENTERS ──────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def _get_period_date_range(budget_period):
    """
    Return (from_date, to_date) strings for the given budget_period value.
    - Monthly   -> current calendar month (MTD)
    - Quarterly -> current fiscal quarter (QTD), Apr/Jul/Oct/Jan starts
    - Annual    -> current fiscal year (YTD), starts 1-Apr
    """
    from frappe.utils import nowdate, getdate, get_first_day, get_last_day, add_months
    from datetime import date as _date

    today = getdate(nowdate())
    period = (budget_period or "Annual").strip()

    if period == "Monthly":
        from_date = get_first_day(today).strftime("%Y-%m-%d")
        to_date   = get_last_day(today).strftime("%Y-%m-%d")
        return from_date, to_date

    if period == "Quarterly":
        # Fiscal quarters: Q1=Apr-Jun, Q2=Jul-Sep, Q3=Oct-Dec, Q4=Jan-Mar
        month = today.month
        if month in (4, 5, 6):
            q_start = _date(today.year, 4, 1)
        elif month in (7, 8, 9):
            q_start = _date(today.year, 7, 1)
        elif month in (10, 11, 12):
            q_start = _date(today.year, 10, 1)
        else:  # Jan, Feb, Mar
            q_start = _date(today.year, 1, 1)
        q_end = getdate(get_last_day(add_months(q_start.strftime("%Y-%m-%d"), 2)))
        return q_start.strftime("%Y-%m-%d"), q_end.strftime("%Y-%m-%d")

    # Annual (default) — fiscal year Apr 1 → Mar 31
    if today.month >= 4:
        fy_start = _date(today.year, 4, 1)
    else:
        fy_start = _date(today.year - 1, 4, 1)
    fy_end = _date(fy_start.year + 1, 3, 31)
    return fy_start.strftime("%Y-%m-%d"), fy_end.strftime("%Y-%m-%d")


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_cost_center_spend(company=None):
    """
    Actual net spend per cost center, summed from posted General Ledger Entries,
    scoped to each cost center's configured budget_period (Monthly / Quarterly / Annual).

    Calculates (debit - credit) for Expense and Income/Revenue accounts, so:
    - Purchase bill expense lines    -> counted as positive spend (debit)
    - Sales invoice income lines     -> counted as negative spend (credit)
    - Receivables/Payables/Bank/Cash -> excluded (balance sheet asset/liability accounts)

    Returns a map { cost_center_name: spend }.
    """
    if not company:
        company = _get_company(frappe.session.user)

    # Fetch all cost centers with their budget_period in a single query
    cc_rows = frappe.db.sql("""
        SELECT name, budget_period
        FROM `tabCost Center`
        WHERE company = %s
          AND IFNULL(disabled, 0) = 0
    """, (company,), as_dict=True)

    # Group cost centers by period so we issue at most 3 GL queries
    from collections import defaultdict
    period_to_ccs = defaultdict(list)
    for cc in cc_rows:
        period = (cc.budget_period or "Annual").strip()
        period_to_ccs[period].append(cc.name)

    result = {}

    for period, cc_names in period_to_ccs.items():
        from_date, to_date = _get_period_date_range(period)
        placeholders = ", ".join(["%s"] * len(cc_names))
        rows = frappe.db.sql("""
            SELECT gl.cost_center, SUM(gl.debit - gl.credit) AS spend
            FROM `tabGeneral Ledger Entry` gl
            JOIN `tabAccount` a ON a.name = gl.account
            WHERE gl.company = %s
              AND gl.cost_center IN ({placeholders})
              AND gl.posting_date BETWEEN %s AND %s
              AND IFNULL(gl.is_cancelled, 0) = 0
              AND a.account_type NOT IN (
                    'Receivable', 'Payable', 'Bank', 'Cash'
              )
            GROUP BY gl.cost_center
        """.format(placeholders=placeholders),
            (company, *cc_names, from_date, to_date),
            as_dict=True,
        )
        for r in rows:
            result[r.cost_center] = flt(r.spend)

    return result


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_cost_center_transactions(cost_center, company=None, period=None, limit=100):
    """
    The posted General Ledger lines that make up a single cost center's spend
    for its budget period — i.e. the drill-down behind get_cost_center_spend().

    Uses the same account filter as get_cost_center_spend (excludes Receivable /
    Payable / Bank / Cash) and the same period window, so the summed
    (debit - credit) of the returned rows reconciles to that cost center's
    spend figure.

    Returns a list of dicts ordered newest-first:
        posting_date, account, voucher_type, voucher_no, debit, credit, party, remarks
    """
    if not cost_center:
        return []
    if not company:
        company = _get_company(frappe.session.user)

    # Default to the cost center's own configured budget period.
    if not period:
        period = frappe.db.get_value("Cost Center", cost_center, "budget_period") or "Annual"

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 100
    limit = max(1, min(limit, 500))

    from_date, to_date = _get_period_date_range(period)

    return frappe.db.sql("""
        SELECT gl.posting_date, gl.account, gl.voucher_type, gl.voucher_no,
               gl.debit, gl.credit, gl.party, gl.remarks
        FROM `tabGeneral Ledger Entry` gl
        JOIN `tabAccount` a ON a.name = gl.account
        WHERE gl.company = %s
          AND gl.cost_center = %s
          AND gl.posting_date BETWEEN %s AND %s
          AND IFNULL(gl.is_cancelled, 0) = 0
          AND a.account_type NOT IN ('Receivable', 'Payable', 'Bank', 'Cash')
        ORDER BY gl.posting_date DESC, gl.creation DESC
        LIMIT %s
    """, (company, cost_center, from_date, to_date, limit), as_dict=True)


# ── CHART OF ACCOUNTS ─────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_chart_of_accounts(company=None):
    """Return all non-disabled accounts.
    Dynamically checks which columns exist in tabAccount so it works
    on plain Frappe installations that may not have root_type / opening_balance etc."""

    # ── 1. Discover available columns via SHOW COLUMNS ──────────────────────
    try:
        col_rows = frappe.db.sql("SHOW COLUMNS FROM `tabAccount`", as_dict=True)
        available = {r.get("Field") or r.get("field", "") for r in col_rows}
    except Exception:
        available = set()

    # Always-safe fields that exist in every Frappe Account doctype
    fields = ["name", "account_name", "account_number", "account_type",
              "is_group", "parent_account"]

    # Optional fields — only include if the column exists in this installation
    for opt in ["root_type", "opening_balance", "balance_must_be", "lft", "rgt", "disabled"]:
        if not available or opt in available:   # include if we couldn't detect columns
            fields.append(opt)

    # ── 2. Determine sort order ──────────────────────────────────────────────
    order_by = "lft asc" if ("lft" in fields) else "account_name asc"

    # ── 3. Build filters ─────────────────────────────────────────────────────
    filters = {}
    if "disabled" in fields:
        filters["disabled"] = 0
    if company:
        try:
            if frappe.db.has_column("Account", "company"):
                filters["company"] = company
        except Exception:
            pass

    # ── 4. Query ─────────────────────────────────────────────────────────────
    try:
        accounts = frappe.db.get_all(
            "Account",
            filters=filters,
            fields=fields,
            order_by=order_by,
            limit=1000
        )
    except Exception as e:
        frappe.log_error(title="get_chart_of_accounts SQL error", message=str(e))
        try:
            accounts = frappe.db.get_all(
                "Account",
                fields=["name", "account_name", "account_type", "is_group", "parent_account"],
                order_by="account_name asc",
                limit=1000
            )
        except Exception:
            accounts = []

    # ── 5. Remove Frappe template roots when company-specific roots exist ─────
    # Frappe ships bare root accounts ("Assets", "Equity", …) with no company.
    # When the company-filtered query still returns them (e.g. company column
    # absent), strip them so the caller only sees company-named accounts.
    _TEMPLATE_ROOT_NAMES = {
        "Assets", "Liabilities", "Liability",
        "Equity", "Income", "Expenses", "Expense",
    }
    root_groups = [a for a in accounts if not a.get("parent_account") and a.get("is_group")]
    has_company_roots = any(
        a.get("account_name", "") not in _TEMPLATE_ROOT_NAMES for a in root_groups
    )
    if has_company_roots:
        accounts = [
            a for a in accounts
            if not (
                a.get("account_name", "") in _TEMPLATE_ROOT_NAMES
                and not a.get("parent_account")
            )
        ]

    return accounts


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def save_account(op, name=None, account_name=None, account_number=None,
                 root_type=None, account_type=None, parent_account=None,
                 is_group=0, opening_balance=0, balance_must_be="Debit",
                 company=None):
    """Create or update an Account document.
    op = 'create' | 'update' | 'delete'
    (named 'op' instead of 'action' — Frappe v15 strips 'action' from form_dict)
    """
    from zoho_books_clone.utils.access import require_module
    require_module("accounts", write=True)
    if not company:
        company = _get_company(frappe.session.user)

    # Discover which optional fields exist in tabAccount
    _has = {}
    def _col_exists(col):
        if col not in _has:
            try:
                _has[col] = frappe.db.has_column("Account", col)
            except Exception:
                _has[col] = False
        return _has[col]

    if op == "create":
        if not account_name:
            frappe.throw("Account name is required")
        doc_dict = {
            "doctype": "Account",
            "account_name": account_name,
            "account_type": account_type or "",
            "is_group": int(is_group or 0),
        }
        if account_number and _col_exists("account_number"):
            doc_dict["account_number"] = account_number
        if root_type and _col_exists("root_type"):
            doc_dict["root_type"] = root_type
        if parent_account and _col_exists("parent_account"):
            doc_dict["parent_account"] = parent_account
        if opening_balance is not None and _col_exists("opening_balance"):
            doc_dict["opening_balance"] = float(opening_balance or 0)
        if balance_must_be and _col_exists("balance_must_be"):
            doc_dict["balance_must_be"] = balance_must_be
        if company and _col_exists("company"):
            doc_dict["company"] = company
        doc = frappe.get_doc(doc_dict)
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"name": doc.name, "status": "created"}

    elif op == "update":
        if not name:
            frappe.throw("Account name (document name) is required for update")
        doc = frappe.get_doc("Account", name)
        if account_name is not None:
            doc.account_name = account_name
        if account_number is not None and _col_exists("account_number"):
            doc.account_number = account_number
        if root_type is not None and _col_exists("root_type"):
            doc.root_type = root_type
        if account_type is not None:
            doc.account_type = account_type
        if parent_account is not None and _col_exists("parent_account"):
            doc.parent_account = parent_account
        if is_group is not None:
            doc.is_group = int(is_group)
        if opening_balance is not None and _col_exists("opening_balance"):
            doc.opening_balance = float(opening_balance)
        if balance_must_be is not None and _col_exists("balance_must_be"):
            doc.balance_must_be = balance_must_be
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return {"name": doc.name, "status": "updated"}

    elif op == "delete":
        if not name:
            frappe.throw("Account name is required for delete")
        frappe.delete_doc("Account", name, ignore_permissions=True)
        frappe.db.commit()
        return {"status": "deleted"}


# ── GSTR / ITC Report endpoints (P3/Issue 9) ──────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_gstr_summary(company=None, from_date=None, to_date=None):
    """
    Return a GSTR-3B style summary:
      output  — taxes collected on Sales Invoices
      itc     — input tax credit from Purchase Invoices
      net     — output - ITC per tax type
      totals  — aggregate figures
    """
    from zoho_books_clone.db.queries import get_gstr_summary as _gstr
    from frappe.utils import nowdate

    if not company:
        company = _get_company(frappe.session.user)
    if not from_date:
        from_date = nowdate()[:8] + "01"      # first of current month
    if not to_date:
        to_date = nowdate()

    if not company:
        frappe.throw("Company is required")

    return _gstr(company=company, from_date=from_date, to_date=to_date)


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_itc_ledger(company=None, from_date=None, to_date=None):
    """
    Line-by-line ITC ledger from Purchase Invoices — for GSTR-2A reconciliation.
    """
    from zoho_books_clone.db.queries import get_itc_ledger as _itc
    from frappe.utils import nowdate

    if not company:
        company = _get_company(frappe.session.user)
    if not from_date:
        from_date = nowdate()[:8] + "01"
    if not to_date:
        to_date = nowdate()

    if not company:
        frappe.throw("Company is required")

    rows = _itc(company=company, from_date=from_date, to_date=to_date)
    return [dict(r) for r in rows]


# ─── Company Name Normalisation ───────────────────────────────────────────────

@frappe.whitelist(allow_guest=False)
def normalize_company_names():
    """
    One-time migration: pick the most-frequently used casing of the company
    name from tabAccount and normalise every other record to match it.

    Run via: bench execute zoho_books_clone.api.books_data.normalize_company_names
    Or call via the API (System Manager only).
    """
    if "System Manager" not in frappe.get_roles(frappe.session.user):
        frappe.throw("Only System Managers can run this migration.")

    # Find the canonical company name (most common casing in Account records)
    rows = frappe.db.sql(
        """SELECT company, COUNT(*) AS cnt
           FROM `tabAccount`
           WHERE company IS NOT NULL AND company != ''
           GROUP BY company
           ORDER BY cnt DESC
           LIMIT 1""",
        as_dict=True,
    )
    if not rows:
        return {"message": "No accounts found — nothing to normalise."}

    canonical = rows[0]["company"]

    # Tables and fields to normalise
    targets = [
        ("tabAccount",          "company"),
        ("tabSales Invoice",    "company"),
        ("tabPurchase Invoice", "company"),
        ("tabPayment Entry",    "company"),
        ("tabJournal Entry",    "company"),
        ("tabStock Entry",      "company"),
        ("tabGeneral Ledger Entry", "company"),
        ("tabStock Ledger Entry",   "company"),
        ("tabWarehouse",        "company"),
        ("tabCost Center",      "company"),
    ]

    updated = {}
    for table, field in targets:
        try:
            frappe.db.sql(
                f"UPDATE `{table}` SET `{field}` = %s "
                f"WHERE LOWER(`{field}`) = LOWER(%s) AND `{field}` != %s",
                (canonical, canonical, canonical),
            )
            count = frappe.db.sql("SELECT ROW_COUNT()")[0][0]
            if count:
                updated[table] = count
        except Exception:
            pass  # Table may not exist on this install

    frappe.db.commit()
    return {
        "canonical_company": canonical,
        "rows_updated": updated,
        "message": f"Normalised company name to '{canonical}' across {len(updated)} tables.",
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_invoice_payments(invoice_name):
    """Return all submitted payment entries linked to a Sales Invoice."""
    rows = frappe.db.sql("""
        SELECT pe.name, pe.payment_date AS posting_date, pe.mode_of_payment AS payment_mode,
               per.allocated_amount, pe.reference_no
          FROM `tabPayment Entry` pe
          JOIN `tabPayment Entry Reference` per ON per.parent = pe.name
         WHERE per.reference_name = %s AND pe.docstatus = 1
         ORDER BY pe.payment_date
    """, invoice_name, as_dict=True)
    return rows

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_customer_unused_credits():
    """
    Return {customer_name: available_credit} by summing unapplied balances across
    all submitted Credit Notes (Sales Invoice rows with is_return=1) per customer.

    Mirrors get_credit_note_balance in docs.py:
      balance = ABS(grand_total) - applied_via_PE_refs - applied_via_JE_contra
    """
    company = (
        frappe.defaults.get_user_default("company")
        or frappe.defaults.get_global_default("company")
    )

    # 1. All submitted Credit Notes (is_return=1 Sales Invoices) for this company
    cns = frappe.db.sql("""
        SELECT name, customer, ABS(grand_total) AS total
          FROM `tabSales Invoice`
         WHERE docstatus = 1
           AND is_return = 1
           AND company = %s
    """, company, as_dict=True)

    if not cns:
        return {}

    cn_names = [c.name for c in cns]
    cn_map = {c.name: {"customer": c.customer, "total": float(c.total or 0), "applied": 0.0}
              for c in cns}

    # 2. Applied via Payment Entry References
    placeholders = ",".join(["%s"] * len(cn_names))
    pe_rows = frappe.db.sql(f"""
        SELECT per.reference_name, SUM(ABS(per.allocated_amount)) AS applied
          FROM `tabPayment Entry Reference` per
          JOIN `tabPayment Entry` pe ON pe.name = per.parent
         WHERE per.reference_doctype = 'Sales Invoice'
           AND per.reference_name IN ({placeholders})
           AND pe.docstatus = 1
         GROUP BY per.reference_name
    """, cn_names, as_dict=True)
    for r in pe_rows:
        if r.reference_name in cn_map:
            cn_map[r.reference_name]["applied"] += float(r.applied or 0)

    # 3. Applied via Journal Entry contra rows (same logic as _je_applications_for_si)
    je_rows = frappe.db.sql(f"""
        SELECT jea.reference_name, SUM(ABS(jea.debit)) AS applied
          FROM `tabJournal Entry Account` jea
          JOIN `tabJournal Entry` je ON je.name = jea.parent
         WHERE jea.reference_type = 'Sales Invoice'
           AND jea.reference_name IN ({placeholders})
           AND je.docstatus = 1
         GROUP BY jea.reference_name
    """, cn_names, as_dict=True)
    for r in je_rows:
        if r.reference_name in cn_map:
            cn_map[r.reference_name]["applied"] += float(r.applied or 0)

    # 4. Sum remaining balance per customer
    result = {}
    for info in cn_map.values():
        balance = max(0.0, info["total"] - info["applied"])
        if balance > 0:
            result[info["customer"]] = result.get(info["customer"], 0.0) + balance

    return result

# ── Price List helpers ────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_price_list_detail(price_list_name):
    """Returns item_count, avg_rate, and active_count for a given price list."""
    today = frappe.utils.nowdate()
    rows = frappe.db.sql("""
        SELECT
            COUNT(*) AS item_count,
            COALESCE(AVG(price_list_rate), 0) AS avg_rate,
            SUM(
                CASE WHEN
                    (valid_from IS NULL OR valid_from <= %s) AND
                    (valid_upto IS NULL OR valid_upto >= %s)
                THEN 1 ELSE 0 END
            ) AS active_count
        FROM `tabItem Price`
        WHERE price_list = %s
    """, (today, today, price_list_name), as_dict=True)
    r = rows[0] if rows else {}
    return {
        "item_count":   int(r.get("item_count") or 0),
        "avg_rate":     float(r.get("avg_rate") or 0),
        "active_count": int(r.get("active_count") or 0),
    }


@frappe.whitelist(allow_guest=False, methods=["POST"])
def duplicate_price_list(source_name, new_name):
    """Creates a copy of source_name price list with all its item prices."""
    from zoho_books_clone.utils.access import require_module
    require_module("inventory", write=True)
    new_name = (new_name or "").strip()
    if not new_name:
        frappe.throw("New name is required")
    if frappe.db.exists("Price List", new_name):
        frappe.throw(f"A price list named '{new_name}' already exists")

    src = frappe.get_doc("Price List", source_name)
    new_pl = frappe.new_doc("Price List")
    new_pl.name            = new_name   # explicit name bypasses naming_series lookup
    new_pl.price_list_name = new_name
    new_pl.currency = src.currency
    new_pl.selling  = src.selling
    new_pl.buying   = src.buying
    new_pl.enabled  = 1
    new_pl.insert(ignore_permissions=True)

    prices = frappe.db.get_all(
        "Item Price",
        filters={"price_list": source_name},
        fields=["item_code", "item_name", "price_list_rate", "uom", "packing_unit", "valid_from", "valid_upto"],
        limit=2000,
    )
    for p in prices:
        np = frappe.new_doc("Item Price")
        np.price_list      = new_pl.name
        np.item_code       = p.item_code
        np.item_name       = p.item_name
        np.price_list_rate = p.price_list_rate
        np.uom             = p.uom or "Nos"
        np.packing_unit    = p.packing_unit
        np.valid_from      = p.valid_from
        np.valid_upto      = p.valid_upto
        np.insert(ignore_permissions=True)

    frappe.db.commit()
    return {"name": new_pl.name, "item_count": len(prices)}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def bulk_create_item_prices(price_list, rows_json):
    """Bulk-creates Item Price docs from a parsed CSV rows array."""
    from zoho_books_clone.utils.access import require_module
    require_module("inventory", write=True)
    import json as _json
    rows = _json.loads(rows_json) if isinstance(rows_json, str) else rows_json
    created, errors = 0, []
    for i, r in enumerate(rows):
        try:
            doc = frappe.new_doc("Item Price")
            doc.price_list      = price_list
            doc.item_code       = r.get("item_code", "").strip()
            doc.item_name       = r.get("item_name", "").strip() or doc.item_code
            doc.price_list_rate = float(r.get("price_list_rate") or r.get("rate") or 0)
            doc.uom             = r.get("uom", "Nos").strip() or "Nos"
            doc.packing_unit    = int(r.get("min_qty") or 0)
            doc.valid_from      = r.get("valid_from") or None
            doc.valid_upto      = r.get("valid_upto") or None
            doc.insert(ignore_permissions=True)
            created += 1
        except Exception as e:
            errors.append({"row": i + 1, "error": str(e)})
    frappe.db.commit()
    return {"created": created, "errors": errors}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_top_sold_items(limit=7):
    """Returns top N items by total quantity sold across submitted Sales Invoices.
    Falls back to most-recently-modified items if no sales history exists."""
    limit = int(limit or 7)
    rows = frappe.db.sql("""
        SELECT sii.item_code, sii.item_name, SUM(sii.qty) AS total_sold
        FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
        WHERE si.docstatus = 1
        GROUP BY sii.item_code, sii.item_name
        ORDER BY total_sold DESC
        LIMIT %s
    """, (limit,), as_dict=True)
    if not rows:
        rows = frappe.db.get_all(
            "Item",
            fields=["item_code", "item_name"],
            order_by="modified desc",
            limit=limit,
        )
    return rows


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_item_warehouse_stock(item_code):
    """Returns warehouses that have positive stock for the given item_code."""
    rows = frappe.db.get_all(
        "Bin",
        filters=[["item_code", "=", item_code], ["actual_qty", ">", 0]],
        fields=["warehouse", "actual_qty"],
        order_by="actual_qty desc",
        limit=10,
    )
    return rows