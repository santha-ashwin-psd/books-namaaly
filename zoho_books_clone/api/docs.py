import frappe
import json
from frappe import _
from frappe.utils import flt, today, getdate
from zoho_books_clone.api.session import _get_company
from zoho_books_clone.db.validators import validate_fiscal_year


# ─── Default account resolution ───────────────────────────────────────────────
#
# Both Sales-side postings (Sales Invoice, Credit Note, Quotation/Sales-Order
# -> Invoice) and Purchase-side postings (Purchase Invoice) need a fallback
# account whenever the caller didn't supply one explicitly (e.g. the Item
# master has no income_account/expense_account set, or the frontend line
# didn't carry one through).
#
# frappe.db.get_value(..., {"account_type": X}) is NOT deterministic when more
# than one leaf account shares the same account_type — e.g. "Sales Revenue"
# and "Other Income" are both account_type "Income"; "Rent", "Salaries &
# Wages", "Office Supplies" and the two Freight/Transport "-Inward" charge
# accounts are all account_type "Expense". Picking "any" account of that type
# means postings can land on the wrong account, silently, per-save.
#
# The fix: always try an exact account_name match first (the account the app
# was actually designed around — see books_setup/bootstrap.py), and only fall
# back to "first leaf account of this type" — with a deterministic ORDER BY —
# if that named account is genuinely missing from this company's chart of
# accounts.

def _find_account(account_types, company, preferred_name=None):
    """Resolve a fallback Account for `company`.

    1. If `preferred_name` is given, prefer the leaf account with that exact
       account_name (e.g. "Sales Revenue", "Cost of Goods Sold").
    2. Otherwise (or if that account doesn't exist for this company), fall
       back to the first leaf account matching any of `account_types`, tried
       in the given priority order, deterministically (ORDER BY name).
    """
    if preferred_name:
        val = frappe.db.get_value(
            "Account",
            {"account_name": preferred_name, "company": company, "is_group": 0},
            "name",
        )
        if val:
            return val
    for at in account_types:
        val = frappe.db.get_value(
            "Account",
            {"account_type": at, "company": company, "is_group": 0},
            "name",
            order_by="name asc",
        )
        if val:
            return val
    return None


def _default_income_account(company):
    """Default Sales/Income account: prefer "Sales Revenue", else any Income-type account."""
    return _find_account(
        ["Income", "Income Account", "Direct Income", "Sales"],
        company,
        preferred_name="Sales Revenue",
    )


def _default_expense_account(company):
    """Default Purchase/COGS account: prefer "Cost of Goods Sold", else any Expense-type account.

    Note the account_types list intentionally puts "Cost of Goods Sold" before
    the generic "Expense" type — with the old ordering, ["Expense", ...] was
    tried first and matched Rent/Salaries & Wages/Office Supplies/etc. before
    "Cost of Goods Sold" was ever reached, since a generic Expense-type
    account always exists.
    """
    return _find_account(
        ["Cost of Goods Sold", "Expenses Included In Valuation", "Expense", "Expense Account"],
        company,
        preferred_name="Cost of Goods Sold",
    )


# ─── Email Template helpers ───────────────────────────────────────────────────

def _resolve_company_for_user():
    """Return the Books Company for the current session user."""
    user = frappe.session.user
    name = frappe.db.get_value("Books Company Member", {"user": user}, "company")
    if not name:
        name = frappe.db.get_single_value("Books Settings", "default_company") or ""
    return name


def _get_email_template(template_short_name):
    """Look up a company-scoped Email Template and return (subject, body) or (None, None).

    Templates are stored as "<Company>::<short_name>" in Frappe's Email Template
    doctype (see admin.py save_email_template). Returns the raw template strings
    so callers can substitute {{variable}} placeholders themselves.
    """
    try:
        company = _resolve_company_for_user()
        if not company:
            return None, None
        full_name = f"{company}::{template_short_name}"
        if not frappe.db.exists("Email Template", full_name):
            return None, None
        doc = frappe.get_doc("Email Template", full_name)
        return (doc.subject or None), (doc.response or None)
    except Exception:
        return None, None


def _render_template(tpl, variables):
    """Replace {{key}} placeholders in a template string with actual values."""
    if not tpl:
        return tpl
    for k, v in variables.items():
        tpl = tpl.replace("{{" + k + "}}", str(v) if v is not None else "")
    return tpl


def _recalculate_invoice_outstanding(invoice_name):
    """Recalculate and persist outstanding_amount for a submitted Sales Invoice.

    Called after editing items on a submitted invoice so that outstanding_amount
    reflects the new grand_total minus any payments already recorded.
    """
    try:
        inv = frappe.db.get_value(
            "Sales Invoice", invoice_name,
            ["grand_total", "outstanding_amount", "due_date", "docstatus"],
            as_dict=True,
        )
        if not inv or inv.docstatus != 1:
            return

        total_paid = flt(frappe.db.sql("""
            SELECT COALESCE(SUM(per.allocated_amount), 0)
            FROM `tabPayment Entry Reference` per
            JOIN `tabPayment Entry` pe ON pe.name = per.parent
            WHERE per.reference_name = %s AND pe.docstatus = 1
        """, (invoice_name,))[0][0])

        new_outstanding = max(0.0, round(flt(inv.grand_total) - total_paid, 2))

        if new_outstanding <= 0:
            new_status = "Paid"
        elif new_outstanding < flt(inv.grand_total):
            new_status = "Partly Paid"
        elif inv.due_date and getdate(str(inv.due_date)) < getdate(today()):
            new_status = "Overdue"
        else:
            new_status = "Submitted"

        frappe.db.set_value(
            "Sales Invoice", invoice_name,
            {"outstanding_amount": new_outstanding, "status": new_status},
            update_modified=False,
        )
    except Exception as exc:
        frappe.log_error(
            f"_recalculate_invoice_outstanding: {invoice_name} — {exc}",
            "Invoice Outstanding Recalc",
        )


# ── Multi-tenant guards for the generic doc API ───────────────────────────────
# get_doc / get_list deliberately run with ignore_permissions=True (Books custom
# roles aren't recognised by Frappe's core permission check). We therefore must
# re-apply company tenancy here so a user can never read another company's data,
# rather than trusting client-supplied filters.

def _tenancy_company_field(doctype):
    """Return the field this doctype is scoped by ('company' or 'books_company'),
    or None for global/shared doctypes (UOM, Currency, Books Settings, …)."""
    try:
        meta = frappe.get_meta(doctype)
    except Exception:
        return None
    if meta.has_field("company"):
        return "company"
    if meta.has_field("books_company"):
        return "books_company"
    return None


def _inject_tenancy_filters(doctype, filters):
    """Force a company filter onto a list query for non-bypass users.
    Returns (filters, allowed); allowed=False means the caller should see nothing."""
    from zoho_books_clone.utils.tenancy import get_user_company, _is_bypass
    user = frappe.session.user
    if _is_bypass(user):
        return filters, True
    field = _tenancy_company_field(doctype)
    if not field:
        return filters, True  # global doctype — no tenancy to enforce
    company = get_user_company(user)
    if not company:
        return filters, False  # unmapped session user → see nothing
    if isinstance(filters, dict):
        filters.setdefault(field, company)
        return filters, True
    filters = list(filters or [])
    if not any(isinstance(f, (list, tuple)) and len(f) >= 1 and f[0] == field for f in filters):
        filters.append([field, "=", company])
    return filters, True


def _assert_doc_tenancy(doc):
    """Raise PermissionError if a single doc belongs to another company."""
    from zoho_books_clone.utils.tenancy import get_user_company, _is_bypass
    user = frappe.session.user
    if _is_bypass(user):
        return
    field = _tenancy_company_field(doc.doctype)
    if not field:
        return
    doc_company = doc.get(field)
    if not doc_company:
        return  # unscoped / legacy record — no opinion (matches tenancy hooks)
    user_company = get_user_company(user)
    if not user_company or doc_company != user_company:
        frappe.throw("Not permitted", frappe.PermissionError)


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_doc(doctype, name):
    """
    Fetch a single document with ignore_permissions=True so the Books Manager
    custom role can read any doctype (frappe.client.get blocks custom roles).
    @frappe.whitelist(allow_guest=False) already blocks unauthenticated callers,
    and _assert_doc_tenancy enforces company isolation.
    """
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    from zoho_books_clone.utils.access import assert_can
    assert_can(doctype, "read")
    # Set ignore_permissions BEFORE fetching so frappe.get_doc doesn't run
    # Frappe's internal role-permission check (which blocks the Books Manager role).
    frappe.flags.ignore_permissions = True
    try:
        doc = frappe.get_doc(doctype, name)
        _assert_doc_tenancy(doc)
        return doc.as_dict()
    finally:
        frappe.flags.ignore_permissions = False


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_stock_entry_line_counts(names=None):
    """
    Bulk item-count / batch-count lookup for a list of Stock Entry names, in a
    single grouped query. Used by the Opening Stock list (and similar list
    views) so it doesn't have to fire one full frappe.get_doc() per row just
    to count child rows — that N+1 pattern is what made the list slow to load.
    Returns {name: {"item_count": n, "batch_count": n}, ...}.
    """
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    from zoho_books_clone.utils.access import assert_can
    assert_can("Stock Entry", "read")

    if isinstance(names, str):
        names = json.loads(names)
    names = [n for n in (names or []) if n]
    if not names:
        return {}

    rows = frappe.db.sql(
        """
        SELECT parent,
               COUNT(*) AS item_count,
               SUM(CASE WHEN IFNULL(batch_no, '') != '' THEN 1 ELSE 0 END) AS batch_count
        FROM `tabStock Entry Detail`
        WHERE parent IN %(names)s
        GROUP BY parent
        """,
        {"names": names},
        as_dict=True,
    )
    return {r.parent: {"item_count": int(r.item_count or 0), "batch_count": int(r.batch_count or 0)} for r in rows}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_list(doctype, fields=None, filters=None, order_by="modified desc", limit_page_length=50, start=0):
    """
    Permission-free list endpoint that mirrors frappe.client.get_list.
    Books tenancy users may have no Frappe role (login is via custom auth flow),
    so the built-in get_list raises PermissionError. This wrapper bypasses that
    check after confirming the caller is authenticated.

    The Vue SPA uses this through src/api/client.js → apiList(). The client adds
    tenancy filters too, but this endpoint no longer trusts them — it re-injects
    the company filter server-side so a tampered client can't read other tenants.
    """
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)

    # Module read gating — a user without the module flag gets an empty list
    # rather than another tenant's or another module's data.
    from zoho_books_clone.utils.access import can_read
    if not can_read(doctype):
        return []

    if isinstance(fields, str):
        try:
            fields = json.loads(fields)
        except Exception:
            fields = [fields]
    if isinstance(filters, str):
        try:
            filters = json.loads(filters)
        except Exception:
            filters = []

    filters, allowed = _inject_tenancy_filters(doctype, filters or [])
    if not allowed:
        return []

    return frappe.get_list(
        doctype,
        fields=fields or ["name"],
        filters=filters,
        order_by=order_by,
        start=int(start or 0),
        limit_page_length=int(limit_page_length or 50),
        ignore_permissions=True,
    )


# ─── Fiscal Year CRUD (company-resolved server-side) ─────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_fiscal_years():
    """Return all Fiscal Year records for the current user's resolved company.
    Uses _resolve_company_for() so Books Company Member rows take priority
    over Books Settings default_company.  Also returns legacy rows where
    company IS NULL (global rows created before per-company support).
    Response: { company, years: [ {name, year_label, year_start_date,
                                    year_end_date, is_closed, lock_date} ] }
    """
    from zoho_books_clone.api.admin import _resolve_company_for
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    company = _resolve_company_for()
    if company:
        rows = frappe.db.sql("""
            SELECT name, year, year_start_date, year_end_date, is_closed,
                   company, lock_date
            FROM `tabFiscal Year`
            WHERE LOWER(company) = LOWER(%s)
            ORDER BY year_start_date DESC
            LIMIT 100
        """, (company,), as_dict=True)
    else:
        rows = frappe.db.sql("""
            SELECT name, year, year_start_date, year_end_date, is_closed,
                   company, lock_date
            FROM `tabFiscal Year`
            ORDER BY year_start_date DESC
            LIMIT 100
        """, as_dict=True)
    # Derive a display label: strip " - CompanyName" suffix added at creation time
    for r in rows:
        raw = r.get("year") or r.get("name") or ""
        co_suffix = " - " + (r.get("company") or "")
        r["year_label"] = raw[:-len(co_suffix)] if r.get("company") and raw.endswith(co_suffix) else raw
        r["year_start_date"] = str(r["year_start_date"] or "")
        r["year_end_date"]   = str(r["year_end_date"] or "")
        r["lock_date"]       = str(r["lock_date"] or "")
    return {"company": company, "years": rows}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def save_fiscal_year(year_label, start_date, end_date, doc_name=None):
    """Create or update a Fiscal Year for the current user's resolved company.
    year_label  – short label like "2025-26" (without company suffix)
    start_date  – YYYY-MM-DD
    end_date    – YYYY-MM-DD
    doc_name    – existing document name to update; omit to create new
    Returns the saved document as a dict.
    """
    from zoho_books_clone.utils.access import require_module
    require_module("accounts", write=True)
    from zoho_books_clone.api.admin import _resolve_company_for
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    company = _resolve_company_for()
    # The year field (= document name via autoname=field:year) is suffixed with
    # the company so each company's years are unique in the shared table.
    year_label = (year_label or "").strip()
    if not year_label:
        frappe.throw("year_label is required")
    full_year = (year_label + " - " + company) if company else year_label
    effective_name = doc_name or full_year
    if frappe.db.exists("Fiscal Year", effective_name):
        d = frappe.get_doc("Fiscal Year", effective_name)
        d.year_start_date = start_date
        d.year_end_date   = end_date
        d.save(ignore_permissions=True)
    else:
        d = frappe.get_doc({
            "doctype":         "Fiscal Year",
            "year":            full_year,
            "year_start_date": start_date,
            "year_end_date":   end_date,
            "company":         company,
        })
        d.insert(ignore_permissions=True)
    frappe.db.commit()
    result = d.as_dict()
    # Attach the clean display label so the frontend can use it immediately
    co_suffix = " - " + (company or "")
    raw = result.get("year") or result.get("name") or ""
    result["year_label"] = raw[:-len(co_suffix)] if company and raw.endswith(co_suffix) else raw
    result["year_start_date"] = str(result.get("year_start_date") or "")
    result["year_end_date"]   = str(result.get("year_end_date") or "")
    result["lock_date"]       = str(result.get("lock_date") or "")
    return result


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_invoice_email_defaults(invoice_name):
    """
    Return pre-filled To, Subject, and body for the Send Email dialog.
    Uses the customer's email_id and the invoice's grand_total / due_date.
    If a company-scoped Email Template named "Sales Invoice" exists it is used
    (with {{variable}} substitution); otherwise falls back to the built-in body.
    """
    inv = frappe.get_doc("Sales Invoice", invoice_name)
    customer_email = frappe.db.get_value("Customer", inv.customer, "email_id") or ""

    variables = {
        "customer_name": inv.customer_name or inv.customer,
        "invoice_no":    inv.name,
        "amount":        f"{inv.grand_total:,.2f}",
        "due_date":      str(inv.due_date or ""),
        "company":       inv.company or "",
    }

    tpl_subject, tpl_body = _get_email_template("Sales Invoice")
    if tpl_subject or tpl_body:
        subject = _render_template(tpl_subject or "Invoice {{invoice_no}} from {{company}}", variables)
        body    = _render_template(tpl_body or "", variables)
    else:
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
        "from_email": frappe.session.user,
    }


def _email_attachment(doctype, name, print_format, pdf_html=None, filename=None):
    """Build the email PDF attachment.

    Prefer caller-supplied HTML (rendered from the user's selected branding
    template in Company Settings) so the emailed PDF matches exactly what the
    user downloads on screen. Fall back to the Frappe print format otherwise.
    """
    if pdf_html:
        try:
            from frappe.utils.pdf import get_pdf
            return [{"fname": "%s.pdf" % (filename or name), "fcontent": get_pdf(pdf_html)}]
        except Exception:
            frappe.log_error(frappe.get_traceback(), "email pdf_html render failed")
    try:
        return [frappe.attach_print(doctype, name, print_format=print_format, print_letterhead=True)]
    except Exception:
        return []


@frappe.whitelist(allow_guest=False, methods=["POST"])
def render_pdf_from_html(pdf_html, filename=None):
    """Render client-side print HTML (the same Classic/Modern/Minimal
    templates used for on-screen preview and email attachments) to a real
    PDF via wkhtmltopdf, and stream it back as a file download.

    This exists because "Download PDF" previously relied on the browser's
    own print-to-PDF dialog (`window.print()`), whose Margins/Headers-and-
    footers settings silently override anything the template sets via CSS
    `@page` rules — so users saw inconsistent margins and stray browser
    chrome (URL/date/page-number) no matter how the template CSS was tuned.
    Rendering server-side with wkhtmltopdf means the template's own CSS is
    the only thing controlling the page layout.
    """
    from frappe.utils.pdf import get_pdf
    content = get_pdf(pdf_html)
    frappe.local.response.filename = filename or "document.pdf"
    frappe.local.response.filecontent = content
    frappe.local.response.type = "download"


def _send_business_email(recipients, cc_list, subject, body, reference_doctype,
                         reference_name, attachments=None, company=None):
    """Send a customer/vendor-facing email.

    Routing is centralised in utils/email_company.send_business_email:
    the company's own SMTP is used when it's enabled & configured under
    Settings → Email, otherwise the platform (wecode) SMTP — which always works
    out of the box — is used by default. `reference_doctype`/`reference_name`
    are accepted for call-site clarity (and future logging)."""
    from zoho_books_clone.utils.email_company import send_business_email
    send_business_email(
        to=recipients, subject=subject, html=body, company=company,
        cc=cc_list or None, attachments=attachments or None,
    )


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def send_invoice_email(invoice_name, to, subject, body, cc=None, pdf_html=None):
    """
    Send invoice email via the company's own SMTP (Settings → Email), falling
    back to Frappe's configured mailer when the company hasn't set it up.
    Attaches a PDF of the invoice (rendered from the selected branding template
    when pdf_html is supplied by the client).
    """
    if not to:
        frappe.throw("Recipient email (To) is required.")

    # Validate invoice exists and user has permission
    if not frappe.has_permission("Sales Invoice", "read", invoice_name):
        frappe.throw("Not permitted", frappe.PermissionError)
    from zoho_books_clone.utils.access import require_module
    require_module("invoices")

    inv = frappe.get_doc("Sales Invoice", invoice_name)

    # Build recipient list (support comma-separated)
    recipients = [e.strip() for e in to.split(",") if e.strip()]
    cc_list = [e.strip() for e in (cc or "").split(",") if e.strip()]

    # Attach PDF of the invoice — selected template when provided
    attachments = _email_attachment(inv.doctype, inv.name, "Sales Invoice", pdf_html)

    # Send via the company's own SMTP (Settings → Email), falling back to
    # Frappe's configured mailer when the company hasn't set it up.
    _send_business_email(
        recipients, cc_list, subject, body, "Sales Invoice", invoice_name,
        attachments=attachments, company=inv.company,
    )

    # Log a communication record so it appears in the timeline
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

    return {"status": "sent", "to": to, "invoice": invoice_name}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def save_doc(doc):
    """
    Save (create or update) a document.
    Called by the Books SPA via POST so large payloads don't hit URL limits.
    @frappe.whitelist(allow_guest=False) already blocks unauthenticated callers;
    we skip frappe.has_permission() because Books Manager is a custom role that
    is not in Frappe's Role Permission Manager for core doctypes.
    """
    if isinstance(doc, str):
        doc = json.loads(doc)

    doctype = doc.get("doctype")
    if not doctype:
        frappe.throw("doctype is required")

    # Block unauthenticated requests (belt-and-suspenders; whitelist already does this)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)

    # Custom role/module authorization (on top of tenancy): read-only roles and
    # users without the relevant module flag cannot create or edit.
    from zoho_books_clone.utils.access import assert_can
    assert_can(doctype, "write")

    # Strip stale child-row metadata so Frappe replaces genuinely-orphaned rows
    # cleanly instead of trying to look up old hash names that no longer exist.
    #
    # CRITICAL: `name` must NOT be blanket-stripped. Doing so unconditionally
    # (as this used to) throws away a valid, currently-forwarded row name on
    # every single save of every existing document -- even when the frontend
    # correctly sent it (e.g. Bills.vue's saveBill(submit) forwards `l.name`).
    # Frappe's child-table diffing then sees "no name" and treats the row as
    # brand new, deleting the real row and inserting a fresh one with a new
    # hash name. Anything keyed on child-row identity (QC Coverage.source_row
    # being the concrete case) loses its link on every save as a result, and
    # `reconcile_row_identity`'s (item_code, batch_no, qty, rate) matching is
    # only a best-effort fallback for this -- it can't recover an ambiguous
    # or slightly-changed row, so this must be fixed at the source instead.
    #
    # A row's `name` is kept when it still genuinely identifies a live row
    # under this same parent document; it is only dropped (so Frappe inserts
    # a fresh row instead of erroring) when it's missing, or stale/foreign
    # (points at a row that doesn't exist, or exists under a different
    # parent -- e.g. a duplicated/copied document).
    _CHILD_META_KEYS_NO_NAME = ("parent", "parenttype", "parentfield", "owner",
                                "creation", "modified", "modified_by")
    _meta = frappe.get_meta(doctype)
    _table_fieldnames = {tf.fieldname: tf.options for tf in _meta.get_table_fields()}
    for key, val in doc.items():
        if not isinstance(val, list):
            continue
        child_doctype = _table_fieldnames.get(key)
        for row in val:
            if not isinstance(row, dict):
                continue
            for mk in _CHILD_META_KEYS_NO_NAME:
                row.pop(mk, None)
            row_name = row.get("name")
            if not row_name:
                continue
            row_doctype = row.get("doctype") or child_doctype
            if not row_doctype:
                row.pop("name", None)
                continue
            actual_parent = frappe.db.get_value(row_doctype, row_name, "parent")
            _doc_name = doc.get("name")
            # Strip when: the row doesn't exist at all: OR this is a brand
            # new parent document (no name yet -- nothing can legitimately
            # already own a child row, so any forwarded name here, even one
            # pointing at a real row, must be foreign/stale); OR the row
            # exists but under a different parent. `not _doc_name` must be
            # checked on its own (not gated behind `actual_parent`) --
            # a falsy _doc_name alone is always disqualifying.
            if actual_parent is None or not _doc_name or actual_parent != _doc_name:
                row.pop("name", None)

    # Auto-stamp books_company for master types that have no native company field
    _MASTER_TYPES = {"Customer", "Supplier", "Item", "Contact", "Sales Person"}
    if doctype in _MASTER_TYPES and not doc.get("books_company"):
        from zoho_books_clone.utils.tenancy import get_user_company, _is_bypass
        if not _is_bypass(frappe.session.user):
            _uc = get_user_company(frappe.session.user)
            if _uc:
                doc["books_company"] = _uc

    # Auto-fill mandatory account fields Frappe requires but the UI doesn't expose.
    # Uses the shared _find_account / _default_income_account / _default_expense_account
    # helpers (module level, above) so "Sales Revenue" / "Cost of Goods Sold" are
    # preferred deterministically instead of an arbitrary same-type account.
    _company = doc.get("company")

    if doctype == "Sales Invoice":
        if not doc.get("debit_to"):
            _ar = _find_account(["Receivable"], _company)
            if _ar:
                doc["debit_to"] = _ar
        # Item-level income_account (set via the Item master, or picked on the
        # line by the frontend) always wins — this fallback only fires for
        # rows/headers that genuinely have nothing set.
        _income = _default_income_account(_company)
        if _income:
            # Set on header (used by accounting_engine.post_sales_invoice)
            if not doc.get("income_account"):
                doc["income_account"] = _income
            # Set on each item row for Frappe's own validation
            for item in doc.get("items") or []:
                if isinstance(item, dict) and not item.get("income_account"):
                    item["income_account"] = _income

    if doctype == "Purchase Invoice":
        if not doc.get("credit_to"):
            _ap = _find_account(["Payable"], _company)
            if _ap:
                doc["credit_to"] = _ap
        # Item-level expense_account (set via the Item master, or picked on the
        # line by the frontend) always wins — this fallback only fires for
        # rows/headers that genuinely have nothing set.
        _expense = _default_expense_account(_company)
        if _expense:
            # Set on header (used by accounting_engine.post_purchase_invoice)
            if not doc.get("expense_account"):
                doc["expense_account"] = _expense
            # Set on each item row
            for item in doc.get("items") or []:
                if isinstance(item, dict) and not item.get("expense_account"):
                    item["expense_account"] = _expense

    name = doc.get("name")
    if name and frappe.db.exists(doctype, name):
        d = frappe.get_doc(doctype, name)

        # Item.name is autoname="field:item_code" -- Frappe only derives `name`
        # from that field on insert, never on update. If we just d.update(doc)
        # + d.save() here, the item_code field silently changes while the doc's
        # real identity (name) does not, desyncing it from every other doctype's
        # item_code link (Stock Ledger Entry, invoice/PO lines, BOM, etc). Rename
        # explicitly first so the identity and the displayed code stay in sync.
        if doctype == "Item":
            new_item_code = (doc.get("item_code") or "").strip()
            if new_item_code and new_item_code != d.name:
                old_item_code = d.name
                frappe.rename_doc(doctype, old_item_code, new_item_code)

                # frappe.rename_doc only auto-updates fields with fieldtype
                # Link/Dynamic Link and options="Item". These five child tables
                # store item_code as plain Data (copied at the time the SO/PO/
                # Quotation/DN/Purchase Receipt line was created), so rename_doc
                # has no way to know they reference this Item -- left alone they'd
                # keep pointing at the old, now-renamed code forever, breaking
                # Order->Invoice conversion, DN-vs-SO reconciliation, and PO->Bill/
                # Receipt matching, all of which join on item_code.
                for _dt in (
                    "Sales Order Item", "Quotation Item",
                    "Purchase Order Item", "Purchase Receipt Item",
                    "Delivery Note Item",
                ):
                    frappe.db.set_value(
                        _dt, {"item_code": old_item_code}, "item_code", new_item_code,
                        update_modified=False,
                    )

                d = frappe.get_doc(doctype, new_item_code)
                doc["name"] = new_item_code
                name = new_item_code

        is_submitted = d.docstatus == 1
        d.update(doc)
        if is_submitted:
            # Submitted documents are normally immutable in Frappe.
            # child rows added via d.update() have no DB name yet, so
            # validate_update_after_submit would throw DoesNotExistError on them.
            d.flags.ignore_validate_update_after_submit = True
            # ignore_validate_update_after_submit skips ALL validate hooks, including
            # the period lock checks. Run them explicitly so submitted docs in locked
            # periods cannot be silently edited.
            from zoho_books_clone.accounts.central_validator import (
                _check_lock_date, _check_fiscal_year_period_lock, _check_period_not_closed
            )
            _check_period_not_closed(d)
            _check_lock_date(d)
            _check_fiscal_year_period_lock(d)
        d.save(ignore_permissions=True)
        # For submitted Sales Invoices, recalculate outstanding_amount after the
        # items have been updated (grand_total changes but outstanding_amount is
        # only auto-synced during on_submit for first-time submissions).
        if is_submitted and doctype == "Sales Invoice" and not getattr(d, "is_return", 0):
            _recalculate_invoice_outstanding(d.name)
    else:
        # New document: must call insert() explicitly.
        # frappe.get_doc(dict) with name already set does NOT mark the doc as
        # new (is_new() returns False), so save() would call db_update() and
        # raise DoesNotExistError.  insert() always creates a new row.

        # Auto-supply naming_series for doctypes that use autoname="naming_series:"
        # but where the SPA doesn't expose the series picker.
        _NAMING_DEFAULTS = {
            "Journal Entry":    "JV-.YYYY.-",
            "Payment Entry":    "PAY-.YYYY.-.#####",
            "Sales Invoice":    "INV-.YYYY.-.#####",
            "Purchase Invoice": "PINV-.YYYY.-.#####",
            "Auto Repeat":      "SUBS-.YYYY.-.#####",
            "Item Price":       "IP-.YYYY.-.#####",
        }
        if doctype in _NAMING_DEFAULTS and not doc.get("naming_series"):
            doc["naming_series"] = _NAMING_DEFAULTS[doctype]

        d = frappe.get_doc(doc)
        d.insert(ignore_permissions=True)
    frappe.db.commit()
    return d.as_dict()


@frappe.whitelist(allow_guest=False, methods=["POST"])
def submit_doc(doctype, name, ignore_budget_warning=0):
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)

    from zoho_books_clone.utils.access import assert_can
    assert_can(doctype, "submit")

    d = frappe.get_doc(doctype, name)
    d.flags.ignore_permissions = True
    if int(ignore_budget_warning or 0) == 1:
        d.flags.ignore_budget_warning = True
    try:
        d.submit()
    except (frappe.ValidationError, frappe.PermissionError):
        # Already a friendly, actionable message (frappe.throw from validate/
        # on_submit hooks, budget warnings, etc.) — let it through as-is.
        raise
    except Exception as e:
        # Anything else (e.g. a raw DB error from a bad/stale account
        # reference reaching an insert) would otherwise surface to the
        # frontend as just the exception class name with no context. Wrap
        # it so the person at least knows which document and what failed.
        frappe.db.rollback()
        frappe.log_error(
            title=f"submit_doc failed: {doctype} {name}",
            message=frappe.get_traceback(),
        )
        frappe.throw(
            _("Could not submit {0} {1}: {2}").format(doctype, name, str(e))
        )
    frappe.db.commit()

    # After submitting a return Sales Invoice (Credit Note), update the parent
    # invoice's outstanding_amount and status. This mirrors what create_credit_note
    # does for the direct-submit path so the draft→submit path stays consistent.
    if doctype == "Sales Invoice" and getattr(d, "is_return", 0) and getattr(d, "return_against", None):
        _sync_parent_invoice_after_cn_submit(d.name, d.return_against, d.grand_total)

    # Payment Entry doctype-agnostic drawers (Payments.vue, BankCash.vue,
    # CustomerProfile.vue, Customers.vue, Vendors.vue) all save a draft via
    # save_doc and then submit it through this generic endpoint, unlike the
    # Sales/Purchase Invoice "Record Payment" flows (books_data.py::record_payment,
    # and this file's create_payment_entry_against_purchase_invoice(s)) which
    # build + submit their own Payment Entry inline and already call
    # _create_bank_transaction themselves. Those inline flows never reach this
    # generic path, so there's no risk of a duplicate Bank Transaction mirror
    # here — but without this, any Payment Entry submitted through the generic
    # drawers (including "Bank Transfer" mode payments from Payments.vue) never
    # got mirrored to Banking at all.
    if doctype == "Payment Entry":
        _create_bank_transaction(d)

    return d.as_dict()


def _sync_parent_invoice_after_cn_submit(cn_name, against_inv, cn_grand_total):
    """Reduce the parent invoice outstanding by the CN's grand total and update its status."""
    if not against_inv or not frappe.db.exists("Sales Invoice", against_inv):
        return
    try:
        parent = frappe.db.get_value(
            "Sales Invoice", against_inv,
            ["outstanding_amount", "grand_total", "due_date", "docstatus"], as_dict=True,
        )
        if not parent or parent.docstatus != 1:
            return
        cn_total        = abs(flt(cn_grand_total))
        if cn_total <= 0:
            # grand_total may not be in memory yet — reload from DB
            cn_total = abs(flt(frappe.db.get_value("Sales Invoice", cn_name, "grand_total")))
        new_outstanding = max(0.0, round(flt(parent.outstanding_amount) - cn_total, 2))
        if new_outstanding <= 0:
            new_status = "Paid"
        elif new_outstanding < flt(parent.grand_total):
            new_status = "Partly Paid"
        elif parent.due_date and getdate(str(parent.due_date)) < getdate(today()):
            new_status = "Overdue"
        else:
            new_status = "Submitted"
        frappe.db.set_value(
            "Sales Invoice", against_inv,
            {"outstanding_amount": new_outstanding, "status": new_status},
            update_modified=False,
        )
        frappe.db.commit()
    except Exception as exc:
        frappe.log_error(
            f"_sync_parent_invoice_after_cn_submit: CN={cn_name} parent={against_inv} — {exc}",
            "CN Submit Sync",
        )

@frappe.whitelist(allow_guest=False, methods=["POST"])
def cancel_doc(doctype, name):
    """Cancel a submitted document."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    from zoho_books_clone.utils.access import assert_can
    assert_can(doctype, "cancel")
    d = frappe.get_doc(doctype, name)
    d.flags.ignore_permissions = True
    d.cancel()
    frappe.db.commit()
    return d.as_dict()


@frappe.whitelist(allow_guest=False, methods=["POST"])
def amend_doc(doctype, name):
    """Create a fresh draft copy of a cancelled document, linked back via
    `amended_from`, so the person can edit and resubmit it as the next
    revision. Generic — works for any doctype with an `amended_from` field
    (BOM, Sales Invoice, Purchase Invoice, Stock Entry, etc.); doctype-specific
    behaviour (e.g. BOM's version-number bump) belongs in that doctype's own
    before_insert/on_submit hooks, not here.
    """
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    from zoho_books_clone.utils.access import assert_can
    assert_can(doctype, "create")

    src = frappe.get_doc(doctype, name)
    if src.docstatus != 2:
        frappe.throw(_("Only a cancelled document can be amended."))

    meta = frappe.get_meta(doctype)
    if not meta.has_field("amended_from"):
        frappe.throw(_("{0} does not support amendment.").format(doctype))

    existing = frappe.db.get_value(doctype, {"amended_from": name}, "name")
    if existing:
        frappe.throw(_(
            "{0} has already been amended as {1}. Open that document instead "
            "of amending {0} again."
        ).format(name, existing))

    new_doc = frappe.copy_doc(src)
    new_doc.amended_from = src.name
    new_doc.docstatus = 0
    new_doc.flags.ignore_permissions = True
    new_doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return new_doc.as_dict()


@frappe.whitelist(allow_guest=False, methods=["POST"])
def delete_doc(doctype, name):
    """Delete a document via GET — no CSRF needed."""
    # Guard: only the logged-in user (session) must have at least read access.
    # We then use ignore_permissions=True on the actual delete so Frappe's
    # internal role-based checks (which can block custom roles like 'Books Manager')
    # don't prevent deletion after we've confirmed the session is valid.
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)

    from zoho_books_clone.utils.access import assert_can
    assert_can(doctype, "delete")

    # force=True bypasses before_delete hooks, so we run the lock check explicitly
    # before handing off to Frappe's delete path.
    from zoho_books_clone.accounts.central_validator import assert_not_locked
    assert_not_locked(doctype, name)

    # force=True also bypasses Frappe's normal "linked document" check, which
    # would otherwise stop a Batch with live Stock Ledger Entries from being
    # deleted. Batch.batch_qty and Stock Ledger Entry rows aren't touched by
    # deleting the Batch master, so without this guard the batch's stock stays
    # in the warehouse's Bin total but becomes unpickable by future Stock
    # Entries (get_batches_for_outgoing only sees rows still in `tabBatch`).
    if doctype == "Batch":
        from zoho_books_clone.inventory.utils import assert_batch_deletable
        assert_batch_deletable(name)

    # force=True above means Journal Entry.on_trash (which cleans up its
    # mirror Bank Transaction reconciliation rows) never fires — do it here
    # explicitly, or the Banking page is left with a dangling
    # journal_entry reference to a document that no longer exists.
    if doctype == "Journal Entry":
        je_doc = frappe.get_doc("Journal Entry", name)
        je_doc._cleanup_mirror_bank_transactions()

    frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
    frappe.db.commit()
    return {"message": "deleted"}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def safe_delete_party(doctype, name):
    """Delete a Customer/Supplier only when it has no transactions.

    Frappe blocks party deletion when linked Address/Contact records exist, so
    those are cleaned up first (only when not shared with another party). If the
    party has any bills/invoices/orders/payments, deletion is refused with a
    clear message so the user disables it instead.
    """
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    if doctype not in ("Customer", "Supplier"):
        frappe.throw("safe_delete_party only supports Customer or Supplier")

    from zoho_books_clone.utils.access import assert_can, assert_company
    assert_can(doctype, "delete")
    # Customer/Supplier are looked up below via frappe.db.count/get_all, which
    # bypass Frappe's has_permission hook (that's a doc-level check; these
    # are raw queries) -- without this, a member of a different company could
    # delete another company's party just by naming it.
    assert_company(frappe.db.get_value(doctype, name, "books_company"))

    if doctype == "Customer":
        checks = [("Sales Invoice", "customer"), ("Sales Order", "customer"),
                  ("Quotation", "customer"), ("Delivery Note", "customer")]
    else:
        checks = [("Purchase Invoice", "supplier"), ("Purchase Order", "supplier"),
                  ("Purchase Receipt", "supplier")]

    blocking = []
    for dt, fld in checks:
        try:
            cnt = frappe.db.count(dt, {fld: name})
        except Exception:
            cnt = 0
        if cnt:
            blocking.append(f"{cnt} {dt}{'s' if cnt > 1 else ''}")

    pe_cnt = frappe.db.count("Payment Entry", {"party_type": doctype, "party": name})
    if pe_cnt:
        blocking.append(f"{pe_cnt} Payment Entr{'ies' if pe_cnt > 1 else 'y'}")

    if blocking:
        frappe.throw(
            f"Cannot delete {name} — it has existing transactions "
            f"({', '.join(blocking)}). Disable it instead."
        )

    # Clean up linked Address / Contact (only if not shared with another party)
    for linked_dt in ("Address", "Contact"):
        links = frappe.get_all(
            "Dynamic Link",
            filters={"link_doctype": doctype, "link_name": name, "parenttype": linked_dt},
            fields=["parent"],
        )
        for l in links:
            shared = frappe.get_all(
                "Dynamic Link",
                filters={"parent": l.parent, "parenttype": linked_dt,
                         "link_name": ["!=", name]},
                limit=1,
            )
            if not shared:
                try:
                    frappe.delete_doc(linked_dt, l.parent, ignore_permissions=True, force=True)
                except Exception:
                    pass

    frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
    frappe.db.commit()
    return {"message": "deleted"}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_invoice_apply_summary(invoice_name):
    """Return a breakdown of Amount, Paid, Previous Credits, and Outstanding for an invoice."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)

    inv = frappe.db.get_value(
        "Sales Invoice", invoice_name,
        ["grand_total", "outstanding_amount", "customer", "customer_name",
         "posting_date", "due_date", "status"],
        as_dict=True,
    )
    if not inv:
        frappe.throw(f"Invoice {invoice_name} not found")

    grand_total = flt(inv.grand_total)
    outstanding = flt(inv.outstanding_amount)

    # Total paid via Payment Entries
    pe_refs = frappe.get_all(
        "Payment Entry Reference",
        filters={"reference_name": invoice_name, "reference_doctype": "Sales Invoice"},
        fields=["parent", "allocated_amount"],
    )
    total_paid = 0.0
    for ref in pe_refs:
        docstatus = frappe.db.get_value("Payment Entry", ref.parent, "docstatus")
        if docstatus == 1:
            total_paid += flt(ref.allocated_amount)

    # Previous credits = total reduction minus payments
    total_credits = max(0.0, round(grand_total - outstanding - total_paid, 2))

    return {
        "grand_total":      round(grand_total, 2),
        "total_paid":       round(total_paid, 2),
        "total_credits":    total_credits,
        "outstanding":      round(outstanding, 2),
        "customer_name":    inv.customer_name or inv.customer,
        "posting_date":     str(inv.posting_date or ""),
        "due_date":         str(inv.due_date or ""),
        "status":           inv.status or "",
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_invoice_payments(invoice_name):
    """Return submitted Payment Entries linked to a Sales Invoice."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    refs = frappe.get_all(
        "Payment Entry Reference",
        filters={"reference_name": invoice_name, "reference_doctype": "Sales Invoice"},
        fields=["parent", "allocated_amount"],
    )
    if not refs:
        return []
    pe_names = list({r.parent for r in refs})
    result = []
    for pe_name in pe_names:
        pe = frappe.db.get_value(
            "Payment Entry", pe_name,
            ["name", "payment_date", "paid_amount", "mode_of_payment", "reference_no", "docstatus", "bank_charges"],
            as_dict=True,
        )
        if pe:
            result.append(pe)
    result.sort(key=lambda x: x.get("payment_date") or "", reverse=True)
    return result


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def cancel_invoice_with_payments(invoice_name):
    """Cancel all linked Payment Entries, then cancel the Sales Invoice."""
    from zoho_books_clone.utils.access import require_module
    require_module("invoices", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    refs = frappe.get_all(
        "Payment Entry Reference",
        filters={"reference_name": invoice_name},
        fields=["parent"],
    )
    pe_names = list({r.parent for r in refs})
    cancelled_pes = []
    for pe_name in pe_names:
        pe_doc = frappe.get_doc("Payment Entry", pe_name)
        if pe_doc.docstatus == 1:
            pe_doc.cancel()
            cancelled_pes.append(pe_name)
    inv_doc = frappe.get_doc("Sales Invoice", invoice_name)
    inv_doc.cancel()
    frappe.db.commit()
    return {"cancelled_payments": cancelled_pes, "cancelled_invoice": invoice_name}


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Bill (Purchase Invoice) helpers, mirroring the Sales Invoice set
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_bill_payments(bill_name):
    """Return submitted Payment Entries linked to a Purchase Invoice (Bill)."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    refs = frappe.get_all(
        "Payment Entry Reference",
        filters={"reference_name": bill_name, "reference_doctype": "Purchase Invoice"},
        fields=["parent", "allocated_amount"],
    )
    if not refs:
        return []
    pe_names = list({r.parent for r in refs})
    result = []
    for pe_name in pe_names:
        pe = frappe.db.get_value(
            "Payment Entry", pe_name,
            ["name", "payment_date", "paid_amount", "mode_of_payment", "reference_no", "docstatus", "bank_charges"],
            as_dict=True,
        )
        if pe:
            result.append(pe)
    result.sort(key=lambda x: x.get("payment_date") or "", reverse=True)
    return result


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_bill_email_defaults(bill_name):
    """Pre-fill the Send Email dialog for a Bill. Uses 'Purchase Invoice' template if saved."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    bill = frappe.get_doc("Purchase Invoice", bill_name)
    supplier_email = frappe.db.get_value("Supplier", bill.supplier, "email_id") or ""

    variables = {
        "customer_name": bill.supplier_name or bill.supplier,
        "invoice_no":    bill.name,
        "amount":        f"{bill.grand_total:,.2f}",
        "due_date":      str(bill.due_date or ""),
        "company":       bill.company or "",
    }

    tpl_subject, tpl_body = _get_email_template("Purchase Invoice")
    if tpl_subject or tpl_body:
        subject = _render_template(tpl_subject or "Bill {{invoice_no}} from {{company}}", variables)
        body    = _render_template(tpl_body or "", variables)
    else:
        subject = f"Bill {bill.name} from {bill.company or ''}"
        body = (
            f"Dear {bill.supplier_name or bill.supplier},<br><br>"
            f"Please find your bill <b>{bill.name}</b> details below:<br><br>"
            f"<table style='border-collapse:collapse;font-size:14px'>"
            f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Bill #</td><td><b>{bill.name}</b></td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Amount</td><td><b>₹{bill.grand_total:,.2f}</b></td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Due Date</td><td>{bill.due_date or '—'}</td></tr>"
            f"</table><br>"
            f"Regards,<br>{bill.company or ''}"
        )
    return {
        "to": supplier_email,
        "subject": subject,
        "body": body,
        "bill_name": bill.name,
        "supplier_name": bill.supplier_name or bill.supplier,
        "from_email": frappe.session.user,
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def send_bill_email(bill_name, to, subject, body, cc=None, pdf_html=None):
    """Send a bill email; attaches the bill PDF when print format exists."""
    if not to:
        frappe.throw("Recipient email (To) is required.")
    from zoho_books_clone.utils.access import require_module
    require_module("bills")
    if not frappe.has_permission("Purchase Invoice", "read", bill_name):
        frappe.throw("Not permitted", frappe.PermissionError)

    bill = frappe.get_doc("Purchase Invoice", bill_name)
    recipients = [e.strip() for e in to.split(",") if e.strip()]
    cc_list = [e.strip() for e in (cc or "").split(",") if e.strip()]
    attachments = _email_attachment(bill.doctype, bill.name, "Purchase Invoice", pdf_html)

    _send_business_email(
        recipients, cc_list, subject, body, "Purchase Invoice", bill_name,
        attachments=attachments, company=bill.company,
    )
    comm = frappe.get_doc({
        "doctype": "Communication", "communication_type": "Communication",
        "communication_medium": "Email", "sent_or_received": "Sent",
        "subject": subject, "content": body, "sender": frappe.session.user,
        "recipients": to, "cc": cc or "",
        "reference_doctype": "Purchase Invoice", "reference_name": bill_name,
        "status": "Linked",
    })
    comm.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "sent", "to": to, "bill": bill_name}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])

def _create_bank_transaction(pe):
    from zoho_books_clone.banking.utils import create_bank_transaction_from_payment_entry
    return create_bank_transaction_from_payment_entry(pe)
@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_bill_payment_defaults(bill_name):
    """Vendor-side equivalent of books_data.get_payment_defaults — supplies
    the bank/cash accounts and payment modes the Pay Vendor dialog needs.
    """
    bill = frappe.get_doc("Purchase Invoice", bill_name)
    outstanding = flt(getattr(bill, "outstanding_amount", None))
    if not outstanding:
        outstanding = flt(bill.grand_total) - flt(getattr(bill, "advance_paid", 0))
    company = bill.company or frappe.db.get_default("company")
    bank_accounts = frappe.db.sql(
        """SELECT name, account_type FROM `tabAccount`
           WHERE account_type IN ('Bank','Cash') AND is_group = 0
             AND LOWER(company) = LOWER(%s)
           ORDER BY account_type DESC""",
        (company,), as_dict=True
    )
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
        "bill_name": bill.name,
        "supplier_name": bill.supplier_name or bill.supplier,
        "supplier": bill.supplier,
        "grand_total": flt(bill.grand_total),
        "balance_due": outstanding,
        "currency": bill.currency or "INR",
        "payment_date": today(),
        "bank_accounts": bank_accounts,
        "payment_modes": payment_modes,
        "company": company,
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def record_vendor_payment(bill_name, amount_paid=None, payment_date=None,
                          payment_mode="Cash", paid_from="", bank_charges=0,
                          reference_no="", notes="", save_as_draft=0,
                          # accept identical keys the receive-side dialog uses, for symmetry
                          amount_received=None, deposit_to=""):
    """Create a Payment Entry against a Purchase Invoice (vendor payment)."""
    from zoho_books_clone.utils.access import require_module
    require_module("payments", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)

    amount = flt(amount_paid or amount_received or 0)
    if amount <= 0:
        frappe.throw("Amount must be greater than zero")

    bill = frappe.get_doc("Purchase Invoice", bill_name)
    if bill.docstatus != 1:
        frappe.throw("Bill must be submitted before recording payment")

    company = bill.company or _get_company(frappe.session.user)

    # Fiscal year lock — block payments into a locked or closed period
    validate_fiscal_year(payment_date or today(), company)
    bank = paid_from or deposit_to or frappe.db.get_value(
        "Account", {"account_type": ["in", ["Bank", "Cash"]], "company": company, "is_group": 0}, "name"
    )
    ap = frappe.db.get_value(
        "Account", {"account_type": "Payable", "company": company, "is_group": 0}, "name"
    )

    pe = frappe.get_doc({
        "doctype": "Payment Entry",
        "payment_type": "Pay",
        "company": company,
        "party_type": "Supplier",
        "party": bill.supplier,
        "party_name": bill.supplier_name or bill.supplier,
        "paid_from": bank,
        "paid_to": ap,
        "paid_amount": amount,
        "currency": bill.currency or "INR",
        "received_amount": amount,
        "source_exchange_rate": 1,
        "target_exchange_rate": 1,
        "reference_no": reference_no or bill.name,
        "reference_date": payment_date or today(),
        "posting_date": payment_date or today(),
        "payment_date": payment_date or today(),
        "mode_of_payment": payment_mode,
        "bank_charges": flt(bank_charges) or 0,
        "remarks": (notes or "") + (f" | Bank Charges: \u20b9{flt(bank_charges):,.2f}" if flt(bank_charges) else ""),
        "references": [{
            "reference_doctype": "Purchase Invoice",
            "reference_name": bill.name,
            "total_amount": bill.grand_total,
            "outstanding_amount": bill.outstanding_amount,
            "allocated_amount": amount,
        }],
    })
    pe.flags.ignore_permissions = True
    pe.flags.ignore_mandatory = True
    pe.insert()
    if not int(save_as_draft or 0):
        pe.submit()
        _create_bank_transaction(pe)
    frappe.db.commit()
    return {"payment_entry": pe.name, "bill": bill.name}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def record_vendor_payment_multi(
    supplier=None, amount_paid=None, payment_date=None,
    payment_mode="Cash", paid_from=None, bank_charges=0,
    reference_no=None, notes=None, allocations=None, save_as_draft=False,
    # accept the receive-side dialog's key names too, for symmetry
    amount_received=None, deposit_to=None,
):
    """Vendor-side equivalent of books_data.record_payment_multi — records a
    single Payment Entry (Pay) against MULTIPLE Purchase Invoices (bills) for
    one supplier at once.

    allocations: JSON list (or already-parsed list) of
        [{"bill": "PINV-0001", "allocated_amount": 3000}, ...]
    ("invoice"/"reference_name" keys are also accepted per row, for symmetry
    with the customer-side allocations shape.)
    """
    from zoho_books_clone.utils.access import require_module
    require_module("payments", write=True)

    if not supplier:
        frappe.throw("supplier is required to record a payment.")
    amount = flt(amount_paid or amount_received or 0)
    if amount <= 0:
        frappe.throw("Amount must be greater than zero.")
    if not payment_date:
        payment_date = today()
    if isinstance(save_as_draft, str):
        save_as_draft = save_as_draft.lower() in ("true", "1", "yes")
    if isinstance(allocations, str):
        allocations = json.loads(allocations or "[]")
    if not allocations:
        frappe.throw("At least one bill allocation is required.")
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)

    bank_charges = flt(bank_charges)

    # Normalise + validate allocation rows before touching any bill.
    clean_allocations = []
    total_allocated = 0.0
    for row in allocations:
        bill_name = row.get("bill") or row.get("invoice") or row.get("reference_name")
        amt = flt(row.get("allocated_amount"))
        if not bill_name:
            frappe.throw("Each allocation row must include a bill name.")
        if amt <= 0:
            continue  # skip zero/blank rows rather than failing the whole payment
        clean_allocations.append({"bill": bill_name, "allocated_amount": amt})
        total_allocated += amt

    if not clean_allocations:
        frappe.throw("At least one bill must have an allocated amount greater than 0.")

    # Total allocated across bills must exactly match the amount paid.
    # (No advance/on-account concept yet — over/under-allocation is rejected
    # so cash and allocations never silently drift apart.)
    if round(total_allocated, 2) != round(amount, 2):
        frappe.throw(
            f"Total allocated ({total_allocated}) must equal Amount "
            f"({amount}). Adjust the per-bill amounts or the total."
        )

    bills = {}
    company = None
    currency = None
    for row in clean_allocations:
        bill = frappe.get_doc("Purchase Invoice", row["bill"])
        if bill.docstatus != 1:
            frappe.throw(f"Bill {bill.name} must be submitted before recording payment.")
        if bill.supplier != supplier:
            frappe.throw(f"Bill {bill.name} does not belong to supplier {supplier}.")
        outstanding = flt(getattr(bill, "outstanding_amount", None))
        if not outstanding:
            outstanding = flt(bill.grand_total) - flt(getattr(bill, "advance_paid", 0))
        if row["allocated_amount"] > outstanding + 0.005:
            frappe.throw(
                f"Allocated amount {row['allocated_amount']} exceeds outstanding "
                f"{outstanding} for bill {bill.name}."
            )
        bills[bill.name] = (bill, outstanding)
        company = company or (bill.company or _get_company(frappe.session.user))
        currency = currency or (bill.currency or "INR")

    # Fiscal year lock — block payments into a locked or closed period
    validate_fiscal_year(payment_date, company)

    bank = paid_from or deposit_to or frappe.db.get_value(
        "Account", {"account_type": ["in", ["Bank", "Cash"]], "company": company, "is_group": 0}, "name"
    )
    if not bank:
        frappe.throw("Could not find a Cash/Bank account. Please set one up under Accounts.")
    ap = frappe.db.get_value(
        "Account", {"account_type": "Payable", "company": company, "is_group": 0}, "name"
    )
    if not ap:
        frappe.throw(
            f"No Payable account found for company '{company}'. "
            "Please ensure the Chart of Accounts is set up under Accounts."
        )

    pe = frappe.new_doc("Payment Entry")
    pe.payment_type          = "Pay"
    pe.company                = company
    pe.posting_date           = payment_date
    pe.payment_date           = payment_date
    pe.mode_of_payment        = payment_mode
    pe.party_type             = "Supplier"
    pe.party                  = supplier
    pe.party_name             = frappe.db.get_value("Supplier", supplier, "supplier_name") or supplier
    pe.paid_from              = bank
    pe.paid_to                = ap
    pe.paid_amount            = amount
    pe.received_amount        = amount
    pe.source_exchange_rate   = 1
    pe.target_exchange_rate   = 1
    pe.currency                = currency or "INR"
    pe.reference_no           = reference_no or f"PMT-{supplier}-{len(clean_allocations)}bills"
    pe.reference_date         = payment_date
    bill_list_str              = ", ".join(bills.keys())
    pe.remarks                 = notes or f"Payment against {bill_list_str}"

    for row in clean_allocations:
        bill, outstanding = bills[row["bill"]]
        pe.append("references", {
            "reference_doctype":  "Purchase Invoice",
            "reference_name":     bill.name,
            "due_date":           bill.due_date,
            "total_amount":       flt(bill.grand_total),
            "outstanding_amount": outstanding,
            "allocated_amount":   row["allocated_amount"],
        })

    if bank_charges > 0:
        # NOTE: paid_amount must stay at the full amount — it's what's
        # allocated against the bill references above, and shrinking it here
        # used to leave allocated_amount (full bill total) exceeding
        # paid_amount, or silently under-clearing the bill. bank_charges is
        # now posted as its own GL line (see accounting_engine.py) instead.
        pe.bank_charges = bank_charges
        pe.remarks = (pe.remarks or "") + f" | Bank Charges: \u20b9{bank_charges:,.2f}"

    pe.flags.ignore_permissions = True
    pe.flags.ignore_mandatory = True
    pe.insert()
    if not save_as_draft:
        pe.submit()
        _create_bank_transaction(pe)
    frappe.db.commit()

    return {
        "status":        "draft" if save_as_draft else "submitted",
        "payment_entry": pe.name,
        "supplier":      supplier,
        "amount":        amount,
        "bills":         list(bills.keys()),
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def cancel_bill_with_payments(bill_name):
    """Cancel linked Payment Entries first, then cancel the Bill (mirror of invoice cascade)."""
    from zoho_books_clone.utils.access import require_module
    require_module("bills", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    refs = frappe.get_all(
        "Payment Entry Reference",
        filters={"reference_name": bill_name},
        fields=["parent"],
    )
    pe_names = list({r.parent for r in refs})
    cancelled_pes = []
    for pe_name in pe_names:
        pe_doc = frappe.get_doc("Payment Entry", pe_name)
        if pe_doc.docstatus == 1:
            pe_doc.cancel()
            cancelled_pes.append(pe_name)
    bill_doc = frappe.get_doc("Purchase Invoice", bill_name)
    bill_doc.cancel()
    frappe.db.commit()
    return {"cancelled_payments": cancelled_pes, "cancelled_bill": bill_name}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_debit_notes(bill_name):
    """Return debit notes (return purchase invoices) against a Bill."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    return frappe.get_all(
        "Purchase Invoice",
        filters={"return_against": bill_name, "is_return": 1, "docstatus": ["!=", 2]},
        fields=["name", "grand_total", "posting_date", "docstatus"],
    )


def _je_applications_for_pi(pi_name):
    """Internal helper — returns submitted Journal Entry Account rows that reference
    `pi_name`. Custom schema uses simple `debit` / `credit` columns.
    """
    rows = frappe.db.sql("""
        SELECT jea.parent, jea.debit AS dr, jea.credit AS cr,
               je.posting_date, je.docstatus
        FROM `tabJournal Entry Account` jea
        JOIN `tabJournal Entry` je ON je.name = jea.parent
        WHERE jea.reference_type = 'Purchase Invoice' AND jea.reference_name = %s
          AND je.docstatus = 1
    """, (pi_name,), as_dict=True)
    return rows


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_debit_note_balance(debit_note_name):
    """Calculate remaining (unapplied) balance on a debit note.

    balance = |grand_total| − applied, where applied includes both
    Payment Entry References AND Journal Entry contra entries that reference this DN.
    """
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    dn = frappe.db.get_value("Purchase Invoice", debit_note_name,
                             ["grand_total", "docstatus", "supplier", "supplier_name"], as_dict=True)
    if not dn:
        return {"name": debit_note_name, "total": 0, "applied": 0, "balance": 0}
    total = abs(flt(dn.grand_total))
    applied = 0
    # 1) Payment Entry references (rarely used for DN, kept for completeness)
    pe_refs = frappe.get_all(
        "Payment Entry Reference",
        filters={"reference_name": debit_note_name, "reference_doctype": "Purchase Invoice"},
        fields=["parent", "allocated_amount"],
    )
    for r in pe_refs:
        if frappe.db.get_value("Payment Entry", r.parent, "docstatus") == 1:
            applied += abs(flt(r.allocated_amount))
    # 2) Journal Entry contra rows (the apply_debit_note_to_bill path).
    # In the corrected JE shape, the DN's reference row sits on the CREDIT side
    # of AP (it cancels the DN's debit-balance). Sum credit, not debit.
    for jea in _je_applications_for_pi(debit_note_name):
        applied += abs(flt(jea.cr))
    return {
        "name": debit_note_name, "supplier": dn.supplier, "supplier_name": dn.supplier_name,
        "total": total, "applied": applied, "balance": max(0, total - applied),
        "docstatus": dn.docstatus,
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def apply_debit_note_to_bill(debit_note, bill, amount):
    """Apply DN credit to a vendor bill via a Journal Entry (contra entry on AP).

    This is the accounting-correct path: a single JE with two AP rows — debits the
    DN reference (reducing its credit balance) and credits the bill reference
    (reducing its outstanding). A Payment Entry can't carry two references that
    each allocate the full amount (sum_allocated > paid_amount), which is why we
    use a JE here.
    """
    from zoho_books_clone.utils.access import require_module
    require_module("bills", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    amount = abs(flt(amount))
    if amount <= 0:
        frappe.throw("Amount must be > 0")

    dn = frappe.get_doc("Purchase Invoice", debit_note)
    bill_doc = frappe.get_doc("Purchase Invoice", bill)
    if dn.docstatus != 1 or bill_doc.docstatus != 1:
        frappe.throw("Both debit note and bill must be submitted")
    if dn.supplier != bill_doc.supplier:
        frappe.throw("Debit note and bill must be for the same vendor")

    balance_info = get_debit_note_balance(debit_note)
    if amount > flt(balance_info["balance"]) + 0.01:
        frappe.throw(f"Cannot apply more than available balance ({balance_info['balance']})")

    company = bill_doc.company
    ap = (bill_doc.credit_to or dn.credit_to
          or frappe.db.get_value("Account",
                                 {"account_type": "Payable", "company": company, "is_group": 0},
                                 "name"))

    je = frappe.get_doc({
        "doctype": "Journal Entry",
        "naming_series": "JE-DN-.YYYY.-.####",
        "voucher_type": "Credit Note",
        "company": company,
        "posting_date": today(),
        "remark": f"Apply Debit Note {dn.name} to Bill {bill}",
        "accounts": [
            # DEBIT side ref-Bill — reduces the Bill's outstanding payable
            # (Bill outstanding lives on CR side of AP; debiting AP reduces it).
            {
                "account": ap,
                "party_type": "Supplier",
                "party": bill_doc.supplier,
                "debit": amount,
                "credit": 0,
                "reference_type": "Purchase Invoice",
                "reference_name": bill,
            },
            # CREDIT side ref-DN — settles the DN's debit-balance to zero
            # (DN sits as a debit on AP; crediting AP cancels it).
            {
                "account": ap,
                "party_type": "Supplier",
                "party": dn.supplier,
                "debit": 0,
                "credit": amount,
                "reference_type": "Purchase Invoice",
                "reference_name": dn.name,
            },
        ],
    })
    je.flags.ignore_permissions = True
    je.flags.ignore_mandatory = True
    je.insert()
    je.submit()
    # Recompute outstanding on the bill so the list/drawer reflects the reduction.
    try:
        from zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry import recompute_outstanding_from_gl
        recompute_outstanding_from_gl("Purchase Invoice", bill)
    except Exception as exc:
        frappe.log_error(f"recompute_outstanding failed for {bill}: {exc}", "apply_debit_note_to_bill")
    frappe.db.commit()
    return {"journal_entry": je.name, "debit_note": debit_note, "bill": bill, "applied": amount}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_debit_note_applications(debit_note_name):
    """Return bills this debit note has been applied to (via JE contra entries, with
    legacy Payment Entry references included for forwards-compatibility)."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    apps = []
    # Journal Entry path (primary)
    je_rows = _je_applications_for_pi(debit_note_name)
    for jea in je_rows:
        # Look for the sibling row in the same JE that references a DIFFERENT PI (the bill)
        siblings = frappe.db.sql("""
            SELECT reference_name, debit AS dr, credit AS cr
            FROM `tabJournal Entry Account`
            WHERE parent = %s AND reference_type='Purchase Invoice'
              AND reference_name != %s
        """, (jea.parent, debit_note_name), as_dict=True)
        for s in siblings:
            apps.append({
                "bill": s.reference_name,
                "amount": abs(flt(s.cr or s.dr)),
                "date": jea.posting_date,
                "payment_entry": jea.parent,   # JE name; key kept for UI compatibility
            })
    # Legacy Payment Entry path
    pe_refs = frappe.get_all(
        "Payment Entry Reference",
        filters={"reference_name": debit_note_name, "reference_doctype": "Purchase Invoice"},
        fields=["parent", "allocated_amount"],
    )
    for r in pe_refs:
        pe = frappe.db.get_value("Payment Entry", r.parent,
                                 ["name", "posting_date", "docstatus"], as_dict=True)
        if not pe or pe.docstatus != 1:
            continue
        siblings = frappe.get_all(
            "Payment Entry Reference",
            filters={"parent": r.parent, "reference_doctype": "Purchase Invoice"},
            fields=["reference_name", "allocated_amount"],
        )
        for s in siblings:
            if s.reference_name and s.reference_name != debit_note_name:
                apps.append({
                    "bill": s.reference_name,
                    "amount": abs(flt(s.allocated_amount)),
                    "date": pe.posting_date,
                    "payment_entry": pe.name,
                })
    return apps


@frappe.whitelist(allow_guest=False)
def get_party_last_items(party_type, party, limit=10):
    """
    Return the items from the most recent submitted document for a customer or vendor.
    party_type: "Customer" → searches Sales Invoice then Quotation
    party_type: "Supplier" → searches Purchase Invoice then Purchase Order
    Returns list of {item_name, item_code, description, qty, rate} dicts.
    """
    limit = int(limit)

    def _fetch_items(item_doctype, parent_name):
        """Select item fields that exist in this table; description is optional."""
        has_desc = frappe.db.has_column(item_doctype, "description")
        desc_col  = ", description" if has_desc else ""
        return frappe.db.sql("""
            SELECT item_name, item_code{desc} , qty, rate
            FROM `tab{idt}`
            WHERE parent = %(parent)s
            ORDER BY idx ASC LIMIT %(limit)s
        """.format(desc=desc_col, idt=item_doctype),
            {"parent": parent_name, "limit": limit}, as_dict=True)

    def _latest_parent(doctype, party_field):
        row = frappe.db.sql("""
            SELECT name FROM `tab{dt}`
            WHERE `{pf}` = %(party)s AND docstatus = 1
            ORDER BY modified DESC LIMIT 1
        """.format(dt=doctype, pf=party_field), {"party": party}, as_dict=True)
        if not row:
            row = frappe.db.sql("""
                SELECT name FROM `tab{dt}`
                WHERE `{pf}` = %(party)s
                ORDER BY modified DESC LIMIT 1
            """.format(dt=doctype, pf=party_field), {"party": party}, as_dict=True)
        return row[0].name if row else None

    if party_type == "Customer":
        for doctype, item_doctype, party_field in [
            ("Sales Invoice", "Sales Invoice Item", "customer"),
            ("Quotation",     "Quotation Item",     "customer"),
            ("Sales Order",   "Sales Order Item",   "customer"),
        ]:
            parent_name = _latest_parent(doctype, party_field)
            if parent_name:
                items = _fetch_items(item_doctype, parent_name)
                if items:
                    return {"source": parent_name, "source_doctype": doctype, "items": items}

    elif party_type == "Supplier":
        for doctype, item_doctype, party_field in [
            ("Purchase Invoice", "Purchase Invoice Item", "supplier"),
            ("Purchase Order",   "Purchase Order Item",   "supplier"),
        ]:
            parent_name = _latest_parent(doctype, party_field)
            if parent_name:
                items = _fetch_items(item_doctype, parent_name)
                if items:
                    return {"source": parent_name, "source_doctype": doctype, "items": items}

    return {"source": None, "items": []}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def create_debit_note():
    """
    Create and submit a Debit Note (Purchase Invoice with is_return=1).
    Posts correct GL: DR Accounts Payable / CR Expense (or Inventory if goods returned).
    If reason is 'Goods Returned' and a warehouse is given, also creates a
    Material Issue Stock Entry to physically reduce inventory.
    Reads all params from frappe.form_dict to handle nested items JSON.
    """
    from zoho_books_clone.utils.access import require_module
    require_module("bills", write=True)
    fd = frappe.form_dict
    vendor       = fd.get("vendor") or ""
    against_bill = fd.get("against_bill") or None
    date         = fd.get("date") or today()
    reason       = fd.get("reason") or ""
    remark       = fd.get("remark") or ""
    cost_center  = fd.get("cost_center") or ""
    draft_only   = frappe.utils.cint(fd.get("draft_only") or 0)
    warehouse    = fd.get("warehouse") or ""
    items_raw    = fd.get("items") or "[]"

    if isinstance(items_raw, str):
        items_raw = json.loads(items_raw)

    taxes_raw    = fd.get("taxes") or "[]"
    if isinstance(taxes_raw, str):
        taxes_raw = json.loads(taxes_raw)

    if not vendor:
        frappe.throw("Vendor is required")
    if not reason:
        frappe.throw("Reason is required")
    if not items_raw:
        frappe.throw("At least one item is required")

    company = _get_company(frappe.session.user)

    ap_account = frappe.db.get_value(
        "Account", {"account_type": "Payable", "company": company, "is_group": 0}, "name"
    )
    expense_account = _default_expense_account(company)

    pi_items = [
        {
            "item_code":      it.get("item_code") or it.get("item_name") or "",
            "item_name":      it.get("item_name") or it.get("item_code") or "",
            "description":    it.get("description") or it.get("item_name") or "",
            "hsn_code":       it.get("hsn_code") or "",
            "uom":            it.get("uom") or "Nos",
            "qty":            -abs(flt(it.get("qty", 1))),
            "rate":           flt(it.get("rate", 0)),
            "discount_percentage": flt(it.get("discount_percentage", 0)),
            "discount_amount":     flt(it.get("discount_amount", 0)),
            "amount":         -abs(flt(it.get("amount", 0))) or None,
            "expense_account": it.get("expense_account") or expense_account,
            "tax_code":       it.get("tax_code") or "",
            "batch_no":       it.get("batch_no") or None,
            "batch_expiry_date": it.get("batch_expiry_date") or None,
        }
        for it in items_raw if (it.get("item_code") or it.get("item_name"))
    ]

    supplier_display = frappe.db.get_value("Supplier", vendor, "supplier_name") or vendor
    pi = frappe.get_doc({
        "doctype":          "Purchase Invoice",
        "is_return":        1,
        "company":          company,
        "supplier":         vendor,
        "supplier_name":    supplier_display,
        "return_against":   against_bill,
        "posting_date":     date,
        "remark":           remark,
        "cost_center":      cost_center,
        "credit_to":        ap_account,
        "expense_account":  expense_account,
        "update_stock":     1 if reason == "Goods Returned" else 0,
        "items":            pi_items,
        "taxes": [
            {
                "charge_type":  "On Net Total",
                "description":  t.get("description") or t.get("tax_type") or "Tax",
                "account_head": t.get("tax_type") or "",
                "rate":         flt(t.get("rate", 0)),
            }
            for t in taxes_raw if t.get("tax_type")
        ],
    })
    pi.name = "DN-" + frappe.generate_hash(
        txt=f"{vendor}{frappe.utils.now()}", length=8
    ).upper()
    pi.flags.ignore_permissions = True
    pi.flags.ignore_links = True
    pi.flags.ignore_mandatory = True
    pi.insert()

    # Draft-only path: just save, no GL posting, no stock movement
    if draft_only:
        frappe.db.commit()
        return {"debit_note": pi.name}

    pi.submit()
    frappe.db.commit()

    # If goods physically returned, create a Material Issue to remove from stock
    se_name = None
    if reason == "Goods Returned" and warehouse:
        se_items = [
            {
                "item_code":   it.get("item_name") or it.get("item_code") or "",
                "item_name":   it.get("item_name") or "",
                "qty":         flt(it.get("qty", 1)),
                "basic_rate":  flt(it.get("rate", 0)),
                "s_warehouse": warehouse,
            }
            for it in items_raw if (it.get("item_name") or it.get("item_code"))
        ]
        if se_items:
            try:
                se = frappe.get_doc({
                    "doctype":          "Stock Entry",
                    "stock_entry_type": "Material Issue",
                    "posting_date":     date,
                    "company":          company,
                    "from_warehouse":   warehouse,
                    "remarks":          f"Goods returned to vendor — Debit Note {pi.name}",
                    "items":            se_items,
                })
                se.name = "SE-DN-" + frappe.generate_hash(
                    txt=f"{pi.name}{frappe.utils.now()}", length=8
                ).upper()
                se.flags.ignore_permissions = True
                se.flags.ignore_links = True
                se.flags.ignore_mandatory = True
                se.insert()
                se.submit()
                frappe.db.commit()
                se_name = se.name
            except Exception as exc:
                frappe.log_error(
                    f"Debit Note {pi.name}: Stock Entry failed — {exc}",
                    "Debit Note Stock Movement"
                )
                frappe.msgprint(
                    f"Debit Note issued, but stock movement failed: {exc}",
                    indicator="orange", alert=True
                )

    # Recompute the parent bill's outstanding from GL. Without this, a stale
    # write earlier in the submit pipeline inflates the bill's outstanding by the
    # DN amount (the bill's own AP CR + the DN's negative-debit posting confuse
    # the central status recalculation). recompute_outstanding_from_gl uses only
    # rows where voucher_no == bill.name plus its sibling PE/JE settlements, so
    # it returns the correct figure.
    if against_bill and frappe.db.exists("Purchase Invoice", against_bill):
        try:
            from zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry import recompute_outstanding_from_gl
            recompute_outstanding_from_gl("Purchase Invoice", against_bill)
            frappe.db.commit()
        except Exception as exc:
            frappe.log_error(
                f"recompute_outstanding failed for parent bill {against_bill}: {exc}",
                "create_debit_note",
            )

    return {
        "debit_note":  pi.name,
        "stock_entry": se_name,
        "return_type": "inventory" if reason == "Goods Returned" else "expense",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Credit Note (Sales Invoice with is_return=1) helpers
# ─────────────────────────────────────────────────────────────────────────────

def _je_applications_for_si(si_name):
    """JEA rows that reference a Sales Invoice (CN or regular SI), submitted JEs only."""
    return frappe.db.sql("""
        SELECT jea.parent, jea.debit AS dr, jea.credit AS cr,
               je.posting_date, je.docstatus
        FROM `tabJournal Entry Account` jea
        JOIN `tabJournal Entry` je ON je.name = jea.parent
        WHERE jea.reference_type = 'Sales Invoice' AND jea.reference_name = %s
          AND je.docstatus = 1
    """, (si_name,), as_dict=True)


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_credit_note_balance(credit_note_name):
    """Available (unapplied) credit on a CN. applied = settled via JE contra + PE refs."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    cn = frappe.db.get_value("Sales Invoice", credit_note_name,
                             ["grand_total", "docstatus", "customer", "customer_name"], as_dict=True)
    if not cn:
        return {"name": credit_note_name, "total": 0, "applied": 0, "balance": 0}
    total = abs(flt(cn.grand_total))
    applied = 0
    pe_refs = frappe.get_all(
        "Payment Entry Reference",
        filters={"reference_name": credit_note_name, "reference_doctype": "Sales Invoice"},
        fields=["parent", "allocated_amount"],
    )
    for r in pe_refs:
        if frappe.db.get_value("Payment Entry", r.parent, "docstatus") == 1:
            applied += abs(flt(r.allocated_amount))
    # For AR-side CN, the row that REDUCES its credit is on the debit side.
    for jea in _je_applications_for_si(credit_note_name):
        applied += abs(flt(jea.dr))
    return {
        "name": credit_note_name, "customer": cn.customer, "customer_name": cn.customer_name,
        "total": total, "applied": applied, "balance": max(0, total - applied),
        "docstatus": cn.docstatus,
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def apply_credit_note_to_invoice(credit_note, invoice, amount):
    """Apply CN credit to a customer invoice via Journal Entry (contra entry on AR)."""
    from zoho_books_clone.utils.access import require_module
    require_module("invoices", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    amount = abs(flt(amount))
    if amount <= 0:
        frappe.throw("Amount must be > 0")

    cn = frappe.get_doc("Sales Invoice", credit_note)
    inv = frappe.get_doc("Sales Invoice", invoice)
    if cn.docstatus != 1 or inv.docstatus != 1:
        frappe.throw("Both credit note and invoice must be submitted")
    if cn.customer != inv.customer:
        frappe.throw("Credit note and invoice must be for the same customer")

    balance_info = get_credit_note_balance(credit_note)
    cn_balance = flt(balance_info["balance"])
    if amount > cn_balance + 0.01:
        frappe.throw(f"Cannot apply more than available credit balance ({cn_balance})")

    inv_outstanding = flt(inv.outstanding_amount)
    if inv_outstanding <= 0:
        frappe.throw(f"Invoice {invoice} has no outstanding amount to apply credit against")
    if amount > inv_outstanding + 0.01:
        frappe.throw(
            f"Amount {amount} exceeds invoice outstanding {inv_outstanding}. "
            f"Maximum applicable: {inv_outstanding}"
        )
    # Cap to the lesser of credit balance and invoice outstanding
    amount = round(min(amount, cn_balance, inv_outstanding), 2)

    company = inv.company
    ar = (inv.debit_to or cn.debit_to
          or frappe.db.get_value("Account",
                                 {"account_type": "Receivable", "company": company, "is_group": 0},
                                 "name"))

    je = frappe.get_doc({
        "doctype": "Journal Entry",
        "naming_series": "JE-CN-.YYYY.-.####",
        "voucher_type": "Credit Note",
        "company": company,
        "posting_date": today(),
        "remark": f"Apply Credit Note {cn.name} to Invoice {invoice}",
        "accounts": [
            # DEBIT side — neutralises the CN's credit balance
            {
                "account": ar, "party_type": "Customer", "party": cn.customer,
                "debit": amount, "credit": 0,
                "reference_type": "Sales Invoice", "reference_name": cn.name,
            },
            # CREDIT side — reduces the Invoice's outstanding receivable
            {
                "account": ar, "party_type": "Customer", "party": inv.customer,
                "debit": 0, "credit": amount,
                "reference_type": "Sales Invoice", "reference_name": invoice,
            },
        ],
    })
    je.flags.ignore_permissions = True
    je.flags.ignore_mandatory = True
    je.insert()
    je.submit()

    # ── Step 1: Direct outstanding update (guaranteed, no silent failures) ──
    # Do this first so the invoice is always updated even if recompute fails.
    direct_outstanding = max(0.0, round(inv_outstanding - amount, 2))
    frappe.db.set_value("Sales Invoice", invoice, "outstanding_amount",
                        direct_outstanding, update_modified=False)

    # ── Step 2: Recompute from GL/JEA for accuracy (e.g. multiple applies) ──
    try:
        from zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry import recompute_outstanding_from_gl
        recompute_outstanding_from_gl("Sales Invoice", invoice)
    except Exception as exc:
        frappe.log_error(f"recompute_outstanding failed for {invoice}: {exc}",
                         "apply_credit_note_to_invoice")

    # ── Step 3: Refresh status based on updated outstanding ─────────────────
    new_status = None
    outstanding_now = None
    try:
        outstanding_now = flt(frappe.db.get_value("Sales Invoice", invoice, "outstanding_amount"))
        inv_grand_total = flt(frappe.db.get_value("Sales Invoice", invoice, "grand_total"))
        inv_due_date    = frappe.db.get_value("Sales Invoice", invoice, "due_date")
        if outstanding_now <= 0:
            new_status = "Paid"
        elif outstanding_now < inv_grand_total:
            new_status = "Partly Paid"
        elif inv_due_date and getdate(inv_due_date) < getdate(today()):
            new_status = "Overdue"
        else:
            new_status = "Submitted"
        frappe.db.set_value("Sales Invoice", invoice, "status", new_status, update_modified=True)
    except Exception as exc:
        frappe.log_error(f"status update failed for {invoice}: {exc}",
                         "apply_credit_note_to_invoice")

    frappe.db.commit()
    return {
        "journal_entry":       je.name,
        "credit_note":         credit_note,
        "invoice":             invoice,
        "applied":             amount,
        "invoice_status":      new_status,
        "invoice_outstanding": outstanding_now if outstanding_now is not None else direct_outstanding,
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_credit_note_applications(credit_note_name):
    """List invoices this CN has been applied to (JE contras + legacy PE refs)."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    apps = []
    for jea in _je_applications_for_si(credit_note_name):
        siblings = frappe.db.sql("""
            SELECT reference_name, debit AS dr, credit AS cr
            FROM `tabJournal Entry Account`
            WHERE parent = %s AND reference_type='Sales Invoice'
              AND reference_name != %s
        """, (jea.parent, credit_note_name), as_dict=True)
        for s in siblings:
            apps.append({
                "invoice": s.reference_name,
                "amount": abs(flt(s.cr or s.dr)),
                "date": jea.posting_date,
                "payment_entry": jea.parent,
                "ref_doctype": "Journal Entry",
            })
    pe_refs = frappe.get_all(
        "Payment Entry Reference",
        filters={"reference_name": credit_note_name, "reference_doctype": "Sales Invoice"},
        fields=["parent", "allocated_amount"],
    )
    for r in pe_refs:
        pe = frappe.db.get_value("Payment Entry", r.parent,
                                 ["name", "posting_date", "docstatus"], as_dict=True)
        if not pe or pe.docstatus != 1:
            continue
        siblings = frappe.get_all(
            "Payment Entry Reference",
            filters={"parent": r.parent, "reference_doctype": "Sales Invoice"},
            fields=["reference_name", "allocated_amount"],
        )
        for s in siblings:
            if s.reference_name and s.reference_name != credit_note_name:
                apps.append({
                    "invoice": s.reference_name,
                    "amount": abs(flt(s.allocated_amount)),
                    "date": pe.posting_date,
                    "payment_entry": pe.name,
                    "ref_doctype": "Payment Entry",
                })
    return apps


@frappe.whitelist(allow_guest=False, methods=["POST"])
def cancel_debit_note(name):
    """Cancel a submitted debit note.

    Mirrors cancel_credit_note()'s JE-cleanup step, which the generic
    cancel_doc() endpoint (previously used for this from the SPA) does not
    do: a debit note applied to a bill via apply_debit_note_to_bill() is
    linked by a submitted Journal Entry referencing the DN's own name
    (reference_type='Purchase Invoice'). Calling d.cancel() directly on a
    DN that still has such a JE outstanding either fails on Frappe's
    submitted-document link check, or — if it doesn't — leaves a dangling
    JE pointing at a now-cancelled voucher, corrupting the AP ledger.

    Unlike cancel_credit_note(), there's no manual "restore source bill
    outstanding" step here: PurchaseInvoice.on_cancel() already calls
    self._adjust_source_bill_outstanding(direction=+1) for is_return docs,
    so that happens automatically inside dn.cancel() below.
    """
    from zoho_books_clone.utils.access import require_module
    require_module("bills", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)

    dn = frappe.get_doc("Purchase Invoice", name)
    if dn.docstatus != 1:
        frappe.throw(f"Debit note {name} is not in a submitted state")

    # ── Step 1: cancel any JE-based applications that reference this DN ──────
    je_refs = frappe.db.sql("""
        SELECT DISTINCT jea.parent
        FROM `tabJournal Entry Account` jea
        JOIN `tabJournal Entry` je ON je.name = jea.parent
        WHERE jea.reference_type = 'Purchase Invoice'
          AND jea.reference_name = %s
          AND je.docstatus = 1
    """, (name,), as_dict=True)

    for row in je_refs:
        try:
            je_doc = frappe.get_doc("Journal Entry", row.parent)
            je_doc.cancel()
        except Exception as exc:
            frappe.log_error(
                f"cancel_debit_note: could not cancel JE {row.parent} for DN {name}: {exc}",
                "DN Cancel JE",
            )

    # ── Step 2: cancel the debit note itself (restores bill outstanding
    #    automatically via PurchaseInvoice.on_cancel()) ───────────────────────
    dn.reload()  # refresh after JE cancellations
    dn.cancel()

    frappe.db.commit()
    return {"status": "cancelled", "name": name, "bill_restored": dn.return_against}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def cancel_credit_note(name):
    """Cancel a submitted credit note and restore the against invoice's outstanding amount.

    Steps:
      1. Cancel any JE-based applications (JEs that reference this CN).
      2. Cancel the credit note itself (reverse GL entries).
      3. Add back the CN's grand_total to the parent invoice's outstanding_amount.
    """
    from zoho_books_clone.utils.access import require_module
    require_module("invoices", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)

    cn = frappe.get_doc("Sales Invoice", name)
    if cn.docstatus != 1:
        frappe.throw(f"Credit note {name} is not in a submitted state")

    against_inv = cn.return_against
    cn_total    = abs(flt(cn.grand_total))

    # ── Step 1: cancel any JE-based applications that reference this CN ──────
    je_refs = frappe.db.sql("""
        SELECT DISTINCT jea.parent
        FROM `tabJournal Entry Account` jea
        JOIN `tabJournal Entry` je ON je.name = jea.parent
        WHERE jea.reference_type = 'Sales Invoice'
          AND jea.reference_name = %s
          AND je.docstatus = 1
    """, (name,), as_dict=True)

    for row in je_refs:
        try:
            je_doc = frappe.get_doc("Journal Entry", row.parent)
            je_doc.cancel()
        except Exception as exc:
            frappe.log_error(
                f"cancel_credit_note: could not cancel JE {row.parent} for CN {name}: {exc}",
                "CN Cancel JE",
            )

    # ── Step 2: cancel the credit note itself ─────────────────────────────────
    cn.reload()  # refresh after JE cancellations
    cn.cancel()

    # ── Step 3: restore the parent invoice's outstanding ─────────────────────
    if against_inv and frappe.db.exists("Sales Invoice", against_inv):
        parent = frappe.db.get_value(
            "Sales Invoice", against_inv,
            ["outstanding_amount", "grand_total", "due_date", "docstatus"], as_dict=True,
        )
        if parent and parent.docstatus == 1:
            new_outstanding = min(
                flt(parent.grand_total),
                round(flt(parent.outstanding_amount) + cn_total, 2),
            )
            if new_outstanding <= 0:
                new_status = "Paid"
            elif new_outstanding < flt(parent.grand_total):
                new_status = "Partly Paid"
            elif parent.due_date and getdate(str(parent.due_date)) < getdate(today()):
                new_status = "Overdue"
            else:
                new_status = "Submitted"
            frappe.db.set_value(
                "Sales Invoice", against_inv,
                {"outstanding_amount": new_outstanding, "status": new_status},
                update_modified=False,
            )

    frappe.db.commit()
    return {"status": "cancelled", "name": name, "invoice_restored": against_inv}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_invoice_credit_applications(invoice_name):
    """Return all credit notes that have been applied to a specific invoice.

    Covers two cases:
    1. Direct creation — CN created with return_against = invoice_name
       (no JE exists; the CN itself is the credit entry).
    2. JE-based application — CN applied after creation via apply_credit_note_to_invoice,
       which creates a Journal Entry referencing both the CN and the invoice.
    """
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)

    seen_cn = set()
    apps = []

    # ── Case 1: direct creation (return_against) ──────────────────────────────
    direct_cns = frappe.db.sql("""
        SELECT name, grand_total, posting_date
        FROM `tabSales Invoice`
        WHERE return_against = %s AND is_return = 1 AND docstatus = 1
    """, (invoice_name,), as_dict=True)

    for cn in direct_cns:
        seen_cn.add(cn.name)
        apps.append({
            "credit_note":   cn.name,
            "amount":        abs(flt(cn.grand_total)),
            "date":          cn.posting_date,
            "journal_entry": None,
            "type":          "direct",
        })

    # ── Case 2: JE-based applications ─────────────────────────────────────────
    je_rows = frappe.db.sql("""
        SELECT jea.parent, je.posting_date
        FROM `tabJournal Entry Account` jea
        JOIN `tabJournal Entry` je ON je.name = jea.parent
        WHERE jea.reference_type = 'Sales Invoice' AND jea.reference_name = %s
          AND je.docstatus = 1
    """, (invoice_name,), as_dict=True)

    seen_je = set()
    for row in je_rows:
        if row.parent in seen_je:
            continue
        seen_je.add(row.parent)
        siblings = frappe.db.sql("""
            SELECT jea.reference_name, jea.debit AS dr, jea.credit AS cr
            FROM `tabJournal Entry Account` jea
            WHERE jea.parent = %s
              AND jea.reference_type = 'Sales Invoice'
              AND jea.reference_name != %s
        """, (row.parent, invoice_name), as_dict=True)
        for s in siblings:
            if s.reference_name in seen_cn:
                continue  # already captured via direct creation
            is_cn = frappe.db.get_value("Sales Invoice", s.reference_name, "is_return")
            if is_cn:
                seen_cn.add(s.reference_name)
                apps.append({
                    "credit_note":   s.reference_name,
                    "amount":        abs(flt(s.cr or s.dr)),
                    "date":          row.posting_date,
                    "journal_entry": row.parent,
                    "type":          "applied",
                })

    apps.sort(key=lambda x: x.get("date") or "", reverse=True)
    return apps


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_bill_debit_applications(bill_name):
    """Return all debit notes applied against a Bill (direct return_against + JE-based)."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)

    seen_dn = set()
    apps = []

    # Case 1: Direct creation (return_against = bill_name)
    direct_dns = frappe.db.sql("""
        SELECT name, grand_total, posting_date
        FROM `tabPurchase Invoice`
        WHERE return_against = %s AND is_return = 1 AND docstatus = 1
    """, (bill_name,), as_dict=True)

    for dn in direct_dns:
        seen_dn.add(dn.name)
        apps.append({
            "debit_note":    dn.name,
            "amount":        abs(flt(dn.grand_total)),
            "date":          dn.posting_date,
            "journal_entry": None,
            "type":          "direct",
        })

    # Case 2: JE-based applications (via apply_debit_note_to_bill)
    je_rows = frappe.db.sql("""
        SELECT jea.parent, je.posting_date
        FROM `tabJournal Entry Account` jea
        JOIN `tabJournal Entry` je ON je.name = jea.parent
        WHERE jea.reference_type = 'Purchase Invoice' AND jea.reference_name = %s
          AND je.docstatus = 1
    """, (bill_name,), as_dict=True)

    seen_je = set()
    for row in je_rows:
        if row.parent in seen_je:
            continue
        seen_je.add(row.parent)
        siblings = frappe.db.sql("""
            SELECT jea.reference_name, jea.debit AS dr, jea.credit AS cr
            FROM `tabJournal Entry Account` jea
            WHERE jea.parent = %s
              AND jea.reference_type = 'Purchase Invoice'
              AND jea.reference_name != %s
        """, (row.parent, bill_name), as_dict=True)
        for s in siblings:
            if s.reference_name in seen_dn:
                continue
            is_dn = frappe.db.get_value("Purchase Invoice", s.reference_name, "is_return")
            if is_dn:
                seen_dn.add(s.reference_name)
                apps.append({
                    "debit_note":    s.reference_name,
                    "amount":        abs(flt(s.dr or s.cr)),
                    "date":          row.posting_date,
                    "journal_entry": row.parent,
                    "type":          "applied",
                })

    apps.sort(key=lambda x: x.get("date") or "", reverse=True)
    return apps


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def refund_credit_note(credit_note_name, amount, refund_mode="Bank Transfer",
                      paid_to="", reference_no=""):
    """Refund the available CN balance back to the customer as a Payment Entry (pay-out)."""
    from zoho_books_clone.utils.access import require_module
    require_module("invoices", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    amount = abs(flt(amount))
    if amount <= 0:
        frappe.throw("Refund amount must be > 0")

    cn = frappe.get_doc("Sales Invoice", credit_note_name)
    if cn.docstatus != 1:
        frappe.throw("Credit Note must be submitted to refund")

    balance_info = get_credit_note_balance(credit_note_name)
    if amount > flt(balance_info["balance"]) + 0.01:
        frappe.throw(f"Cannot refund more than available balance ({balance_info['balance']})")

    company = cn.company
    bank = paid_to or frappe.db.get_value(
        "Account", {"account_type": ["in", ["Bank", "Cash"]], "company": company, "is_group": 0},
        "name",
    )
    ar = cn.debit_to or frappe.db.get_value(
        "Account", {"account_type": "Receivable", "company": company, "is_group": 0}, "name",
    )

    # Refund as a Journal Entry: DR AR (settles CN credit) / CR Bank (money out).
    # Avoids the PE validator that forbids Pay→Receivable.
    je = frappe.get_doc({
        "doctype": "Journal Entry",
        "naming_series": "JE-REFUND-.YYYY.-.####",
        "voucher_type": "Bank Entry",
        "company": company,
        "posting_date": today(),
        "remark": f"Refund of Credit Note {cn.name} ({refund_mode})"
                  + (f" — ref {reference_no}" if reference_no else ""),
        "accounts": [
            # DEBIT side — reduces the CN's outstanding credit (settles it)
            {
                "account": ar, "party_type": "Customer", "party": cn.customer,
                "debit": amount, "credit": 0,
                "reference_type": "Sales Invoice", "reference_name": cn.name,
            },
            # CREDIT side — money leaves the bank
            {
                "account": bank, "debit": 0, "credit": amount,
            },
        ],
    })
    je.flags.ignore_permissions = True
    je.flags.ignore_mandatory = True
    je.insert()
    je.submit()
    frappe.db.commit()
    return {"journal_entry": je.name, "credit_note": credit_note_name, "refunded": amount}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_credit_note_email_defaults(credit_note_name):
    """Pre-fill the Send Email dialog for a Credit Note. Uses 'Credit Note' template if saved."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    cn = frappe.get_doc("Sales Invoice", credit_note_name)
    cust_email = frappe.db.get_value("Customer", cn.customer, "email_id") or ""

    variables = {
        "customer_name": cn.customer_name or cn.customer,
        "invoice_no":    cn.name,
        "amount":        f"{abs(cn.grand_total):,.2f}",
        "due_date":      str(cn.posting_date or ""),
        "company":       cn.company or "",
    }

    tpl_subject, tpl_body = _get_email_template("Credit Note")
    if tpl_subject or tpl_body:
        subject = _render_template(tpl_subject or "Credit Note {{invoice_no}} from {{company}}", variables)
        body    = _render_template(tpl_body or "", variables)
    else:
        subject = f"Credit Note {cn.name} from {cn.company or ''}"
        body = (
            f"Dear {cn.customer_name or cn.customer},<br><br>"
            f"Please find your credit note <b>{cn.name}</b> details below:<br><br>"
            f"<table style='border-collapse:collapse;font-size:14px'>"
            f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Credit Note #</td><td><b>{cn.name}</b></td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Amount</td><td><b>₹{abs(cn.grand_total):,.2f}</b></td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Date</td><td>{cn.posting_date}</td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Against Invoice</td><td>{cn.return_against or '—'}</td></tr>"
            f"</table><br>"
            f"This credit note may be applied against your open invoices or refunded.<br><br>"
            f"Regards,<br>{cn.company or ''}"
        )
    return {
        "to": cust_email, "subject": subject, "body": body,
        "credit_note_name": cn.name,
        "customer_name": cn.customer_name or cn.customer,
        "from_email": frappe.session.user,
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def send_credit_note_email(credit_note_name, to, subject, body, cc=None, pdf_html=None):
    if not to:
        frappe.throw("Recipient email (To) is required.")
    from zoho_books_clone.utils.access import require_module
    require_module("invoices")
    if not frappe.has_permission("Sales Invoice", "read", credit_note_name):
        frappe.throw("Not permitted", frappe.PermissionError)
    cn = frappe.get_doc("Sales Invoice", credit_note_name)
    recipients = [e.strip() for e in to.split(",") if e.strip()]
    cc_list = [e.strip() for e in (cc or "").split(",") if e.strip()]
    attachments = _email_attachment(cn.doctype, cn.name, "Sales Invoice", pdf_html)
    _send_business_email(
        recipients, cc_list, subject, body, "Sales Invoice", credit_note_name,
        attachments=attachments, company=cn.company,
    )
    comm = frappe.get_doc({
        "doctype": "Communication", "communication_type": "Communication",
        "communication_medium": "Email", "sent_or_received": "Sent",
        "subject": subject, "content": body, "sender": frappe.session.user,
        "recipients": to, "cc": cc or "",
        "reference_doctype": "Sales Invoice", "reference_name": credit_note_name,
        "status": "Linked",
    })
    comm.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "sent", "to": to, "credit_note": credit_note_name}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_debit_note_email_defaults(debit_note_name):
    """Pre-fill the Send Email dialog for a Debit Note. Uses 'Debit Note' template if saved."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    dn = frappe.get_doc("Purchase Invoice", debit_note_name)
    vendor_email = frappe.db.get_value("Supplier", dn.supplier, "email_id") or ""

    variables = {
        "customer_name": dn.supplier_name or dn.supplier,
        "invoice_no":    dn.name,
        "amount":        f"{abs(dn.grand_total):,.2f}",
        "due_date":      str(dn.posting_date or ""),
        "company":       dn.company or "",
    }

    tpl_subject, tpl_body = _get_email_template("Debit Note")
    if tpl_subject or tpl_body:
        subject = _render_template(tpl_subject or "Debit Note {{invoice_no}} from {{company}}", variables)
        body    = _render_template(tpl_body or "", variables)
    else:
        subject = f"Debit Note {dn.name} from {dn.company or ''}"
        body = (
            f"Dear {dn.supplier_name or dn.supplier},<br><br>"
            f"Please find your debit note <b>{dn.name}</b> details below:<br><br>"
            f"<table style='border-collapse:collapse;font-size:14px'>"
            f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Debit Note #</td><td><b>{dn.name}</b></td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Amount</td><td><b>₹{abs(dn.grand_total):,.2f}</b></td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Date</td><td>{dn.posting_date}</td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Against Bill</td><td>{dn.return_against or '—'}</td></tr>"
            f"</table><br>"
            f"This debit note may be applied against your open bills.<br><br>"
            f"Regards,<br>{dn.company or ''}"
        )
    return {
        "to": vendor_email, "subject": subject, "body": body,
        "debit_note_name": dn.name,
        "supplier_name": dn.supplier_name or dn.supplier,
        "from_email": frappe.session.user,
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def send_debit_note_email(debit_note_name, to, subject, body, cc=None, pdf_html=None):
    if not to:
        frappe.throw("Recipient email (To) is required.")
    from zoho_books_clone.utils.access import require_module
    require_module("bills")
    if not frappe.has_permission("Purchase Invoice", "read", debit_note_name):
        frappe.throw("Not permitted", frappe.PermissionError)
    dn = frappe.get_doc("Purchase Invoice", debit_note_name)
    recipients = [e.strip() for e in to.split(",") if e.strip()]
    cc_list = [e.strip() for e in (cc or "").split(",") if e.strip()]
    attachments = _email_attachment(dn.doctype, dn.name, "Purchase Invoice", pdf_html)
    _send_business_email(
        recipients, cc_list, subject, body, "Purchase Invoice", debit_note_name,
        attachments=attachments, company=dn.company,
    )
    comm = frappe.get_doc({
        "doctype": "Communication", "communication_type": "Communication",
        "communication_medium": "Email", "sent_or_received": "Sent",
        "subject": subject, "content": body, "sender": frappe.session.user,
        "recipients": to, "cc": cc or "",
        "reference_doctype": "Purchase Invoice", "reference_name": debit_note_name,
        "status": "Linked",
    })
    comm.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "sent", "to": to, "debit_note": debit_note_name}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_credit_notes(invoice_name):
    """Return existing credit notes (return invoices) against a given Sales Invoice."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    cns = frappe.get_all(
        "Sales Invoice",
        filters={"return_against": invoice_name, "is_return": 1, "docstatus": ["!=", 2]},
        fields=["name", "grand_total", "posting_date", "docstatus"],
    )
    return cns


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def create_credit_note():
    """
    Create and submit a Credit Note.
    Posts correct GL via CreditNote.on_submit(): DR Income / CR AR.
    If reason is 'Goods Returned' and a warehouse is given, also creates a
    Material Receipt Stock Entry to bring goods back into stock.
    """
    from zoho_books_clone.utils.access import require_module
    require_module("invoices", write=True)
    fd = frappe.form_dict
    customer     = fd.get("customer") or ""
    against_inv  = fd.get("against_invoice") or None
    date         = fd.get("date") or today()
    reason       = fd.get("reason") or ""
    notes        = fd.get("notes") or ""
    cost_center  = fd.get("cost_center") or ""
    warehouse    = fd.get("warehouse") or ""
    items_raw    = json.loads(fd.get("items") or "[]")
    taxes_raw    = json.loads(fd.get("taxes") or "[]")

    if not customer:
        frappe.throw("Customer is required")
    if not items_raw:
        frappe.throw("At least one item is required")

    # Validate: CN total must not exceed the parent invoice's outstanding amount
    if against_inv and frappe.db.exists("Sales Invoice", against_inv):
        inv_data = frappe.db.get_value(
            "Sales Invoice", against_inv,
            ["grand_total", "outstanding_amount", "docstatus"], as_dict=True
        )
        if inv_data and inv_data.docstatus == 1:
            new_cn_total = sum(abs(flt(it.get("qty", 1))) * flt(it.get("rate", 0)) for it in items_raw)
            inv_outstanding = flt(inv_data.outstanding_amount)
            if new_cn_total > inv_outstanding + 0.01:
                frappe.throw(
                    f"Credit note total {frappe.format_value(new_cn_total, 'Currency')} "
                    f"exceeds the invoice outstanding amount "
                    f"{frappe.format_value(inv_outstanding, 'Currency')}. "
                    f"Reduce the quantities or amounts."
                )

    company = _get_company(frappe.session.user)

    ar_account = frappe.db.get_value(
        "Account", {"account_type": "Receivable", "company": company, "is_group": 0}, "name"
    )
    income_account = _default_income_account(company)

    cn_items = [
        {
            "item_code":      it.get("item_code") or it.get("item_name") or "",
            "item_name":      it.get("item_name") or it.get("item_code") or "",
            "description":    it.get("description") or it.get("item_name") or "",
            "hsn_code":       it.get("hsn_code") or "",
            "uom":            it.get("uom") or "Nos",
            "qty":            -abs(flt(it.get("qty", 1))),
            "rate":           flt(it.get("rate", 0)),
            "discount_percentage": flt(it.get("discount_percentage", 0)),
            "discount_amount":     flt(it.get("discount_amount", 0)),
            "amount":         -abs(flt(it.get("amount", 0))) or None,
            "income_account": it.get("income_account") or income_account,
            "tax_code":       it.get("tax_code") or "",
            "batch_no":       it.get("batch_no") or None,
            "batch_expiry_date": it.get("batch_expiry_date") or None,
        }
        for it in items_raw if (it.get("item_code") or it.get("item_name"))
    ]

    cn_taxes = [
        {
            "charge_type":  "On Net Total",
            "description":  t.get("description") or t.get("tax_type") or "Tax",
            "account_head": t.get("tax_type") or "",
            "rate":         flt(t.get("rate", 0)),
        }
        for t in taxes_raw
        if t.get("tax_type")
    ]

    customer_display = frappe.db.get_value("Customer", customer, "customer_name") or customer
    cn = frappe.get_doc({
        "doctype":          "Sales Invoice",
        "is_return":        1,
        "company":          company,
        "customer":         customer,
        "customer_name":    customer_display,
        "return_against":   against_inv,
        "posting_date":     date,
        "remarks":          (reason + (" — " + notes if notes else "")),
        "cost_center":      cost_center,
        "debit_to":         ar_account,
        "income_account":   income_account,
        "update_stock":     1 if reason == "Goods Returned" else 0,
        "items":            cn_items,
        "taxes":            cn_taxes,
    })
    from datetime import date as _date
    _year = _date.today().year
    cn.name = frappe.model.naming.make_autoname(f"CN-{_year}-.#####")
    cn.flags.ignore_permissions = True
    cn.flags.ignore_links = True
    cn.flags.ignore_mandatory = True
    cn.insert()
    cn.submit()
    frappe.db.commit()

    # If goods returned by customer, create Material Receipt to restock.
    # Restock at COST (current valuation / FIFO), never the invoice's selling
    # rate — receiving at selling price would write inventory up by the margin
    # and overstate profit via the Stock Adjustment contra.
    def _restock_rate(item_code, selling_rate):
        rate = flt(frappe.db.get_value(
            "Bin", {"item_code": item_code, "warehouse": warehouse}, "valuation_rate"))
        if not rate:
            try:
                from zoho_books_clone.inventory.utils import get_fifo_cost
                rate = flt(get_fifo_cost(item_code, warehouse, 1))
            except Exception:
                rate = 0
        return rate or flt(selling_rate)

    se_name = None
    if reason == "Goods Returned" and warehouse:
        se_items = [
            {
                "item_code":   it.get("item_name") or it.get("item_code") or "",
                "item_name":   it.get("item_name") or "",
                "qty":         flt(it.get("qty", 1)),
                "basic_rate":  _restock_rate(it.get("item_name") or it.get("item_code") or "",
                                             it.get("rate", 0)),
                "t_warehouse": warehouse,
            }
            for it in items_raw if (it.get("item_name") or it.get("item_code"))
        ]
        if se_items:
            try:
                se = frappe.get_doc({
                    "doctype":          "Stock Entry",
                    "stock_entry_type": "Material Receipt",
                    "posting_date":     date,
                    "company":          company,
                    "to_warehouse":     warehouse,
                    "remarks":          f"Customer return — Credit Note {cn.name}",
                    "items":            se_items,
                })
                se.name = "SE-CN-" + frappe.generate_hash(
                    txt=f"{cn.name}{frappe.utils.now()}", length=8
                ).upper()
                se.flags.ignore_permissions = True
                se.flags.ignore_links = True
                se.flags.ignore_mandatory = True
                se.insert()
                se.submit()
                frappe.db.commit()
                se_name = se.name
            except Exception as exc:
                frappe.log_error(
                    f"Credit Note {cn.name}: Stock Entry failed — {exc}",
                    "Credit Note Stock Movement"
                )
                frappe.msgprint(
                    f"Credit note issued, but stock receipt failed: {exc}",
                    indicator="orange", alert=True
                )

    # Directly reduce parent invoice outstanding using the shared helper.
    if against_inv:
        _sync_parent_invoice_after_cn_submit(cn.name, against_inv, cn.grand_total)

    return {
        "credit_note": cn.name,
        "stock_entry": se_name,
        "return_type": "inventory" if reason == "Goods Returned" else "adjustment",
    }


@frappe.whitelist(allow_guest=False, methods=["POST"])
def save_credit_note_draft():
    """Create or update a Credit Note draft with sequential CN- naming."""
    from zoho_books_clone.utils.access import require_module
    require_module("invoices", write=True)
    fd = frappe.form_dict
    name        = fd.get("name") or ""
    customer    = fd.get("customer") or ""
    against_inv = fd.get("against_invoice") or None
    date        = fd.get("date") or today()
    reason      = fd.get("reason") or ""
    notes       = fd.get("notes") or ""
    cost_center = fd.get("cost_center") or ""
    items_raw   = json.loads(fd.get("items") or "[]")
    taxes_raw   = json.loads(fd.get("taxes") or "[]")

    if not customer:
        frappe.throw(_("Customer is required"))

    company = _get_company(frappe.session.user)
    ar_account = frappe.db.get_value(
        "Account", {"account_type": "Receivable", "company": company, "is_group": 0}, "name"
    )
    income_account = _default_income_account(company)
    customer_display = frappe.db.get_value("Customer", customer, "customer_name") or customer

    cn_items = [
        {
            "item_code":      it.get("item_code") or "",
            "item_name":      it.get("item_name") or it.get("item_code") or "",
            "description":    it.get("description") or it.get("item_code") or "",
            "hsn_code":       it.get("hsn_code") or "",
            "uom":            it.get("uom") or "Nos",
            "qty":            -abs(flt(it.get("qty", 1))),
            "rate":           flt(it.get("rate", 0)),
            "discount_percentage": flt(it.get("discount_percentage", 0)),
            "discount_amount":     flt(it.get("discount_amount", 0)),
            "amount":         -abs(flt(it.get("amount", 0))) or None,
            "income_account": it.get("income_account") or income_account,
            "tax_code":       it.get("tax_code") or "",
            "batch_no":       it.get("batch_no") or None,
            "batch_expiry_date": it.get("batch_expiry_date") or None,
        }
        for it in items_raw if (it.get("item_code") or it.get("item_name"))
    ]
    cn_taxes = [
        {
            "charge_type":  "On Net Total",
            "description":  t.get("description") or t.get("tax_type") or "Tax",
            "account_head": t.get("tax_type") or "",
            "rate":         flt(t.get("rate", 0)),
        }
        for t in taxes_raw
        if t.get("tax_type")
    ]

    remarks = (reason + (" — " + notes if notes else ""))

    if name and frappe.db.exists("Sales Invoice", name):
        cn = frappe.get_doc("Sales Invoice", name)
        if cn.docstatus != 0:
            frappe.throw(_("Cannot edit a submitted credit note"))
        cn.customer = customer
        cn.customer_name = customer_display
        cn.return_against = against_inv or None
        cn.posting_date = date
        cn.remarks = remarks
        cn.cost_center = cost_center or cn.cost_center or ""
        cn.debit_to = cn.debit_to or ar_account
        cn.income_account = cn.income_account or income_account
        cn.update_stock = 1 if reason == "Goods Returned" else 0
        cn.items = []
        for it in cn_items:
            cn.append("items", it)
        cn.taxes = []
        for tx in cn_taxes:
            cn.append("taxes", tx)
        cn.flags.ignore_permissions = True
        cn.flags.ignore_mandatory = True
        cn.save()
    else:
        cn = frappe.get_doc({
            "doctype":        "Sales Invoice",
            "is_return":      1,
            "company":        company,
            "customer":       customer,
            "customer_name":  customer_display,
            "return_against": against_inv or None,
            "posting_date":   date,
            "remarks":        remarks,
            "cost_center":    cost_center,
            "debit_to":       ar_account,
            "income_account": income_account,
            "update_stock":   1 if reason == "Goods Returned" else 0,
            "items":          cn_items,
            "taxes":          cn_taxes,
        })
        from datetime import date as _date
        _year = _date.today().year
        cn.name = frappe.model.naming.make_autoname(f"CN-{_year}-.#####")
        cn.flags.ignore_permissions = True
        cn.flags.ignore_links = True
        cn.flags.ignore_mandatory = True
        cn.insert()

    frappe.db.commit()
    return {"ok": True, "name": cn.name}


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Quotation lifecycle + conversions
# ─────────────────────────────────────────────────────────────────────────────

def _set_quote_status(quotation_name, status):
    """Update Quotation.status without triggering full save validation."""
    if not frappe.db.exists("Quotation", quotation_name):
        frappe.throw(f"Quotation {quotation_name} not found")
    frappe.db.set_value("Quotation", quotation_name, "status", status, update_modified=True)
    frappe.db.commit()
    return status


@frappe.whitelist(allow_guest=False, methods=["POST"])
def mark_quote_sent(quotation_name):
    """Mark a quote as sent (sets status='Sent'). Auto-fired by Send Email too."""
    from zoho_books_clone.utils.access import require_module
    require_module("invoices", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    return {"name": quotation_name, "status": _set_quote_status(quotation_name, "Sent")}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def mark_quote_accepted(quotation_name):
    from zoho_books_clone.utils.access import require_module
    require_module("invoices", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    return {"name": quotation_name, "status": _set_quote_status(quotation_name, "Accepted")}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def mark_quote_declined(quotation_name, reason=""):
    from zoho_books_clone.utils.access import require_module
    require_module("invoices", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    _set_quote_status(quotation_name, "Declined")
    if reason:
        notes = frappe.db.get_value("Quotation", quotation_name, "notes") or ""
        sep = "\n\n" if notes else ""
        frappe.db.set_value("Quotation", quotation_name, "notes",
                            f"{notes}{sep}Declined: {reason}", update_modified=True)
        frappe.db.commit()
    return {"name": quotation_name, "status": "Declined", "reason": reason}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def mark_quote_expired_bulk(quotation_names):
    """Bulk-set status='Expired' for the given quotations."""
    from zoho_books_clone.utils.access import require_module
    require_module("invoices", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    if isinstance(quotation_names, str):
        quotation_names = json.loads(quotation_names)
    out = []
    for q in (quotation_names or []):
        try:
            _set_quote_status(q, "Expired")
            out.append({"name": q, "ok": True})
        except Exception as exc:
            out.append({"name": q, "ok": False, "error": str(exc)})
    return out


def _quote_items_to_doc_items(quote_doc, target_item_doctype):
    """Map Quotation Item rows into the target child-table dict format."""
    rows = []
    for it in (quote_doc.items or []):
        rows.append({
            "doctype": target_item_doctype,
            "item_code":           it.item_code,
            "item_name":           it.item_name or it.item_code,
            "description":         it.description or it.item_name or it.item_code,
            "qty":                 flt(it.qty) or 1,
            "uom":                 getattr(it, "uom", "") or "Nos",
            "rate":                flt(it.rate),
            "amount":              flt(it.amount),
            "hsn_code":            getattr(it, "hsn_code", "") or "",
            "discount_percentage": getattr(it, "discount_percentage", "") or "",
            "tax_code":            getattr(it, "tax_code", "") or "",
        })
    return rows


@frappe.whitelist(allow_guest=False, methods=["POST"])
def convert_quote_to_sales_order(quotation_name, delivery_date=""):
    """Create a Sales Order from a Quotation; flips the quote status to Converted."""
    from zoho_books_clone.utils.access import require_module
    require_module("invoices", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    qd = frappe.get_doc("Quotation", quotation_name)
    so = frappe.get_doc({
        "doctype": "Sales Order",
        "company":               qd.company,
        "customer":              qd.customer,
        "customer_name":         qd.customer_name,
        "transaction_date":      today(),
        "delivery_date":         delivery_date or qd.valid_till or today(),
        "ref_quote":             qd.name,
        "terms":                 getattr(qd, "terms", "") or "",
        "billing_address":       getattr(qd, "billing_address", "") or "",
        "billing_address_name":  getattr(qd, "billing_address_name", "") or "",
        "shipping_address":      getattr(qd, "shipping_address", "") or "",
        "shipping_address_name": getattr(qd, "shipping_address_name", "") or "",
        "items":                 _quote_items_to_doc_items(qd, "Sales Order Item"),
        "taxes":                 [
            {"doctype": "Tax Line",
             "charge_type": getattr(t, "charge_type", "On Net Total"),
             "account_head": getattr(t, "account_head", ""),
             "description": getattr(t, "description", ""),
             "rate": flt(getattr(t, "rate", 0))}
            for t in (qd.taxes or [])
        ],
    })
    so.flags.ignore_permissions = True
    so.flags.ignore_mandatory = True
    so.insert()
    _set_quote_status(quotation_name, "Converted")
    return {"sales_order": so.name, "quotation": quotation_name}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def convert_quote_to_invoice(quotation_name, due_date="", warehouse="", batch_nos=None):
    """Create a Sales Invoice directly from a Quotation.

    batch_nos: optional {quotation_item_name: batch_no} map for batch-tracked
    items — required per-line since this invoice is the doc that deducts stock
    (a Quotation has no prior Delivery Note)."""
    from zoho_books_clone.utils.access import require_module
    require_module("invoices", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    if isinstance(batch_nos, str):
        try:
            batch_nos = json.loads(batch_nos) if batch_nos else None
        except json.JSONDecodeError:
            batch_nos = None
    batch_nos = {str(k): v for k, v in (batch_nos or {}).items()}

    qd = frappe.get_doc("Quotation", quotation_name)
    ar = frappe.db.get_value(
        "Account", {"account_type": "Receivable", "company": qd.company, "is_group": 0}, "name"
    )
    inc = _default_income_account(qd.company)

    item_codes = list({it.item_code for it in (qd.items or []) if it.item_code})
    batch_flags = {}
    if item_codes:
        batch_flags = {
            x["name"]: x["has_batch_no"]
            for x in frappe.get_all("Item", filters={"name": ["in", item_codes]},
                                    fields=["name", "has_batch_no"])
        }

    items = _quote_items_to_doc_items(qd, "Sales Invoice Item")
    for it, qi in zip(items, qd.items or []):
        it["income_account"] = it.get("income_account") or inc
        if batch_flags.get(qi.item_code):
            batch_no = (batch_nos.get(str(qi.name)) or "").strip()
            if not batch_no:
                frappe.throw(_(
                    "Row #{0}: {1} is a batch-tracked item — select a Batch No before converting"
                ).format(qi.idx, qi.item_name or qi.item_code))
            it["batch_no"] = batch_no

    si = frappe.get_doc({
        "doctype":               "Sales Invoice",
        "company":               qd.company,
        "customer":              qd.customer,
        "posting_date":          today(),
        "due_date":              due_date or today(),
        "debit_to":              ar,
        "income_account":        inc,
        "notes":                 f"From Quotation {qd.name}",
        "update_stock":          1,
        "set_warehouse":         warehouse or "",
        "billing_address":       getattr(qd, "billing_address", "") or "",
        "billing_address_name":  getattr(qd, "billing_address_name", "") or "",
        "shipping_address":      getattr(qd, "shipping_address", "") or "",
        "shipping_address_name": getattr(qd, "shipping_address_name", "") or "",
        "items":                 items,
        "taxes": [
            {"doctype": "Tax Line",
             "charge_type": getattr(t, "charge_type", "On Net Total"),
             "account_head": getattr(t, "account_head", ""),
             "description": getattr(t, "description", ""),
             "rate": flt(getattr(t, "rate", 0))}
            for t in (qd.taxes or [])
        ],
    })
    si.flags.ignore_permissions = True
    si.flags.ignore_mandatory = True
    si.insert()
    _set_quote_status(quotation_name, "Converted")
    return {"sales_invoice": si.name, "quotation": quotation_name}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_quote_conversions(quotation_name):
    """Return any Sales Orders / Sales Invoices linked back to this Quotation."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    sos = frappe.get_all("Sales Order",
        filters={"ref_quote": quotation_name},
        fields=["name", "transaction_date", "grand_total", "status"],
    )
    sis = frappe.db.sql("""
        SELECT name, posting_date, grand_total, status, outstanding_amount
        FROM `tabSales Invoice`
        WHERE notes LIKE %s AND is_return = 0
        ORDER BY posting_date DESC
    """, ("%From Quotation " + quotation_name + "%",), as_dict=True)
    return {"sales_orders": sos or [], "sales_invoices": sis or []}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_quote_email_defaults(quotation_name):
    """Pre-fill the Send Email dialog for a Quotation. Uses 'Quotation' template if saved."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    qd = frappe.get_doc("Quotation", quotation_name)
    cust_email = frappe.db.get_value("Customer", qd.customer, "email_id") or ""

    variables = {
        "customer_name": qd.customer_name or qd.customer,
        "invoice_no":    qd.name,
        "amount":        f"{qd.grand_total:,.2f}",
        "due_date":      str(qd.valid_till or ""),
        "company":       qd.company or "",
    }

    tpl_subject, tpl_body = _get_email_template("Quotation")
    if tpl_subject or tpl_body:
        subject = _render_template(tpl_subject or "Quotation {{invoice_no}} from {{company}}", variables)
        body    = _render_template(tpl_body or "", variables)
    else:
        subject = f"Quotation {qd.name} from {qd.company or ''}"
        body = (
            f"Dear {qd.customer_name or qd.customer},<br><br>"
            f"Please find your quotation <b>{qd.name}</b> details below:<br><br>"
            f"<table style='border-collapse:collapse;font-size:14px'>"
            f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Quotation #</td><td><b>{qd.name}</b></td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Amount</td><td><b>₹{qd.grand_total:,.2f}</b></td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Date</td><td>{qd.transaction_date}</td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Valid Till</td><td>{qd.valid_till or '—'}</td></tr>"
            f"</table><br>"
            f"Looking forward to your confirmation.<br><br>"
            f"Regards,<br>{qd.company or ''}"
        )
    return {
        "to": cust_email, "subject": subject, "body": body,
        "quotation_name": qd.name,
        "customer_name": qd.customer_name or qd.customer,
        "from_email": frappe.session.user,
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def send_quote_email(quotation_name, to, subject, body, cc=None, pdf_html=None):
    """Send a quote email and auto-flip status to 'Sent'."""
    if not to:
        frappe.throw("Recipient email (To) is required.")
    from zoho_books_clone.utils.access import require_module
    require_module("invoices")
    if not frappe.has_permission("Quotation", "read", quotation_name):
        frappe.throw("Not permitted", frappe.PermissionError)
    qd = frappe.get_doc("Quotation", quotation_name)
    recipients = [e.strip() for e in to.split(",") if e.strip()]
    cc_list = [e.strip() for e in (cc or "").split(",") if e.strip()]
    attachments = _email_attachment(qd.doctype, qd.name, "Quotation", pdf_html)
    _send_business_email(
        recipients, cc_list, subject, body, "Quotation", quotation_name,
        attachments=attachments, company=qd.company,
    )
    comm = frappe.get_doc({
        "doctype": "Communication", "communication_type": "Communication",
        "communication_medium": "Email", "sent_or_received": "Sent",
        "subject": subject, "content": body, "sender": frappe.session.user,
        "recipients": to, "cc": cc or "",
        "reference_doctype": "Quotation", "reference_name": quotation_name,
        "status": "Linked",
    })
    comm.insert(ignore_permissions=True)
    # Auto-flip status to Sent if still Draft
    cur = frappe.db.get_value("Quotation", quotation_name, "status")
    if cur in (None, "", "Draft"):
        _set_quote_status(quotation_name, "Sent")
    frappe.db.commit()
    return {"status": "sent", "to": to, "quotation": quotation_name}


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — Sales Order fulfillment + conversions
# This build has no Delivery Challan doctype, so DC conversion is replaced by a
# manual "Mark Delivered" action that sets delivered_qty on selected SO lines.
# ─────────────────────────────────────────────────────────────────────────────

def _so_status_from_fulfillment(so_name):
    """Compute a fulfillment-aware status: To Deliver / Partially Delivered /
    Delivered / Invoiced / Closed."""
    rows = frappe.get_all("Sales Order Item",
        filters={"parent": so_name},
        fields=["qty", "delivered_qty", "billed_qty"])
    if not rows:
        return "Submitted"
    total_qty = sum(flt(r.qty) for r in rows)
    delivered = sum(flt(r.delivered_qty) for r in rows)
    billed    = sum(flt(r.billed_qty) for r in rows)
    if total_qty <= 0:
        return "Submitted"
    if billed >= total_qty - 0.001 and delivered >= total_qty - 0.001:
        return "Closed"
    if billed >= total_qty - 0.001:
        return "Invoiced"
    if delivered >= total_qty - 0.001:
        return "Delivered"
    if delivered > 0 or billed > 0:
        return "Partially Delivered"
    return "To Deliver"


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_sales_order_fulfillment(sales_order):
    """Per-line: qty, delivered_qty, billed_qty, remaining_to_deliver, remaining_to_bill."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    rows = frappe.get_all("Sales Order Item",
        filters={"parent": sales_order},
        fields=["name", "item_code", "item_name", "qty", "rate", "amount",
                "delivered_qty", "billed_qty"],
        order_by="idx asc")
    # Collect item codes that are missing item_name and fetch from Item master
    item_codes = [r["item_code"] for r in rows if r.get("item_code")]
    missing = [r["item_code"] for r in rows if not r.get("item_name") and r.get("item_code")]
    if missing:
        item_names = {
            x["name"]: x["item_name"]
            for x in frappe.get_all("Item", filters={"name": ["in", missing]},
                                    fields=["name", "item_name"])
        }
        for r in rows:
            if not r.get("item_name") and r.get("item_code"):
                r["item_name"] = item_names.get(r["item_code"]) or r["item_code"]
    # has_batch_no per item, so the Convert-to-Invoice / Deliver modals know
    # which lines need a Batch No picker.
    batch_flags = {}
    if item_codes:
        batch_flags = {
            x["name"]: x["has_batch_no"]
            for x in frappe.get_all("Item", filters={"name": ["in", item_codes]},
                                    fields=["name", "has_batch_no"])
        }
    so_warehouse = frappe.db.get_value("Sales Order", sales_order, "set_warehouse")

    # Batches this SO line was actually DISPATCHED under, per submitted
    # Delivery Note (Delivery Note Item.so_item was stamped with the SO Item
    # row's name by create_delivery_note_from_so). The invoice must bill
    # against the SAME batch that physically left the warehouse — letting
    # the Convert-to-Invoice picker offer any in-stock batch (the old
    # get_batches_for_item global list) meant a user could invoice a
    # different batch than what was actually delivered, which is wrong for
    # batch/lot traceability (and for COGS if batches are valued
    # differently). So: for rows with at least one delivered batch, the
    # frontend restricts the picker to just these (and auto-fills when
    # there's only one), instead of falling back to the global item list.
    so_item_ids = [r["name"] for r in rows if batch_flags.get(r["item_code"])]
    delivered_batches = {}
    if so_item_ids:
        dn_batch_rows = frappe.db.sql("""
            SELECT dni.so_item, dni.batch_no, SUM(dni.qty) AS qty
            FROM `tabDelivery Note Item` dni
            INNER JOIN `tabDelivery Note` dn ON dn.name = dni.parent
            WHERE dn.docstatus = 1
              AND dn.sales_order = %(so)s
              AND dni.so_item IN %(so_items)s
              AND dni.batch_no IS NOT NULL AND dni.batch_no != ''
            GROUP BY dni.so_item, dni.batch_no
            ORDER BY dni.batch_no
        """, {"so": sales_order, "so_items": [int(x) for x in so_item_ids]}, as_dict=True)
        for d in dn_batch_rows:
            delivered_batches.setdefault(str(d.so_item), []).append(
                {"batch_no": d.batch_no, "qty": flt(d.qty)}
            )

    # Same idea for what's actually been INVOICED so far (Sales Invoice
    # Item also carries so_item — see convert_sales_order_to_invoice).
    # Used to show which batch a fully-invoiced line was billed under,
    # since that can in principle differ from delivered_batches (e.g. a
    # direct invoice with update_stock that never went through a DN at
    # all) — don't assume delivery batch == invoiced batch.
    invoiced_batches = {}
    if so_item_ids:
        si_batch_rows = frappe.db.sql("""
            SELECT sii.so_item, sii.batch_no, SUM(sii.qty) AS qty
            FROM `tabSales Invoice Item` sii
            INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
            WHERE si.docstatus = 1
              AND si.sales_order = %(so)s
              AND sii.so_item IN %(so_items)s
              AND sii.batch_no IS NOT NULL AND sii.batch_no != ''
            GROUP BY sii.so_item, sii.batch_no
            ORDER BY sii.batch_no
        """, {"so": sales_order, "so_items": [int(x) for x in so_item_ids]}, as_dict=True)
        for d in si_batch_rows:
            invoiced_batches.setdefault(str(d.so_item), []).append(
                {"batch_no": d.batch_no, "qty": flt(d.qty)}
            )

    for r in rows:
        r["remaining_to_deliver"] = max(0.0, flt(r["qty"]) - flt(r["delivered_qty"]))
        r["remaining_to_bill"]    = max(0.0, flt(r["qty"]) - flt(r["billed_qty"]))
        r["has_batch_no"] = 1 if batch_flags.get(r["item_code"]) else 0
        r["warehouse_qty"] = 0.0
        r["delivered_batches"] = delivered_batches.get(str(r["name"]), [])
        r["invoiced_batches"] = invoiced_batches.get(str(r["name"]), [])
        if so_warehouse and r.get("item_code"):
            bin_qty = frappe.db.get_value("Bin", {"item_code": r["item_code"], "warehouse": so_warehouse}, "actual_qty")
            r["warehouse_qty"] = flt(bin_qty)

    return {
        "lines": rows, 
        "computed_status": _so_status_from_fulfillment(sales_order),
        "warehouse": so_warehouse
    }


@frappe.whitelist(allow_guest=False, methods=["POST"])
def mark_so_delivered(sales_order, line_qtys=None):
    """Mark selected SO lines as delivered. line_qtys is {item_row_name: qty_to_add}
    or null/empty to mark ALL remaining qty delivered on every line."""
    from zoho_books_clone.utils.access import require_module
    require_module("invoices", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    if isinstance(line_qtys, str):
        try:
            line_qtys = json.loads(line_qtys) if line_qtys else None
        except json.JSONDecodeError:
            line_qtys = None

    so = frappe.get_doc("Sales Order", sales_order)
    warehouse = getattr(so, "set_warehouse", "") or ""
    company   = getattr(so, "company", "") or ""

    rows = frappe.get_all("Sales Order Item",
        filters={"parent": sales_order},
        fields=["name", "item_code", "qty", "delivered_qty"])
    if line_qtys:
        line_qtys = {str(k): v for k, v in line_qtys.items()}
    updated = 0
    for r in rows:
        remaining = max(0.0, flt(r.qty) - flt(r.delivered_qty))
        if remaining <= 0:
            continue
        if line_qtys:
            add = flt(line_qtys.get(str(r.name), 0))
            if add <= 0:
                continue
            add = min(add, remaining)
        else:
            add = remaining
        new_delivered = flt(r.delivered_qty) + add
        frappe.db.set_value("Sales Order Item", r.name, "delivered_qty",
                            new_delivered, update_modified=False)
        # NOTE: do NOT touch reserved_qty here.
        # reserved_qty is released only when the Sales Invoice is submitted
        # (via SI._release_reserved_qty).  Releasing it here as well would
        # free the reservation before the invoice is raised, causing
        # projected_qty to show more available stock than actually exists.
        updated += 1
    # Update parent status
    new_status = _so_status_from_fulfillment(sales_order)
    frappe.db.set_value("Sales Order", sales_order, "status", new_status,
                        update_modified=True)
    frappe.db.commit()
    return {"sales_order": sales_order, "lines_updated": updated, "status": new_status}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def convert_sales_order_to_invoice(sales_order, line_qtys=None, batch_nos=None, due_date=""):
    """Create a Sales Invoice from an SO (partial or full).
    line_qtys = {sales_order_item_name: qty_to_invoice}; null → invoice remaining.
    batch_nos = {sales_order_item_name: batch_no}; only needed for batch-tracked items
    where the invoice is the doc that deducts stock (no prior Delivery Note)."""
    from zoho_books_clone.utils.access import require_module
    require_module("invoices", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    if isinstance(line_qtys, str):
        try:
            line_qtys = json.loads(line_qtys) if line_qtys else None
        except json.JSONDecodeError:
            line_qtys = None
    if isinstance(batch_nos, str):
        try:
            batch_nos = json.loads(batch_nos) if batch_nos else None
        except json.JSONDecodeError:
            batch_nos = None
    batch_nos = {str(k): v for k, v in (batch_nos or {}).items()}

    so = frappe.get_doc("Sales Order", sales_order)
    company = so.company
    ar = frappe.db.get_value("Account",
        {"account_type": "Receivable", "company": company, "is_group": 0}, "name")
    inc = _default_income_account(company)

    si_items = []
    line_updates = []  # (so_item_name, qty_to_bill)
    # Normalise dict keys to strings — JSON dict keys come in as strings even when
    # Frappe's auto-increment row names are stored as integers.
    if line_qtys:
        line_qtys = {str(k): v for k, v in line_qtys.items()}

    # Stock ownership rule (mirrors inventory/stock_link.py):
    #   SO -> Delivery Note -> Invoice  => DN already deducted stock;
    #                                      the invoice must NOT deduct it again.
    #   SO -> Invoice (no DN)           => invoice is the only stock movement,
    #                                      so it should deduct on submit.
    has_delivery_note = frappe.db.exists(
        "Delivery Note", {"sales_order": so.name, "docstatus": 1}
    )
    auto_update_stock = 0 if has_delivery_note else 1

    item_codes = list({it.item_code for it in (so.items or []) if it.item_code})
    batch_flags = {}
    if item_codes:
        batch_flags = {
            x["name"]: x["has_batch_no"]
            for x in frappe.get_all("Item", filters={"name": ["in", item_codes]},
                                    fields=["name", "has_batch_no"])
        }

    for it in (so.items or []):
        remaining = max(0.0, flt(it.qty) - flt(it.billed_qty))
        if remaining <= 0:
            continue
        if line_qtys:
            qty_bill = min(flt(line_qtys.get(str(it.name), 0)), remaining)
        else:
            qty_bill = remaining
        if qty_bill <= 0:
            continue

        # Batch No — only required when this invoice is the doc that will
        # actually deduct stock (no prior Delivery Note); otherwise Sales
        # Invoice.validate_batches() clears it anyway.
        batch_no = ""
        if auto_update_stock and batch_flags.get(it.item_code):
            batch_no = (batch_nos.get(str(it.name)) or "").strip()
            if not batch_no:
                frappe.throw(_(
                    "Row #{0}: {1} is a batch-tracked item — select a Batch No before invoicing"
                ).format(it.idx, it.item_name or it.item_code))

        si_items.append({
            "doctype": "Sales Invoice Item",
            "item_code":           it.item_code,
            "item_name":           it.item_name or it.item_code,
            "description":         it.description or it.item_name or it.item_code,
            "qty":                 qty_bill,
            "uom":                 getattr(it, "uom", "") or "Nos",
            "rate":                flt(it.rate),
            "amount":              flt(it.rate) * qty_bill,
            "income_account":      inc,
            "hsn_code":            getattr(it, "hsn_code", "") or "",
            "discount_percentage": getattr(it, "discount_percentage", "") or "",
            "tax_code":            getattr(it, "tax_code", "") or "",
            "batch_no":            batch_no,
            "so_item":             int(it.name) if str(it.name).isdigit() else 0,
        })
        line_updates.append((it.name, qty_bill))

    if not si_items:
        frappe.throw("Nothing left to invoice on this Sales Order")

    si = frappe.get_doc({
        "doctype":               "Sales Invoice",
        "company":               company,
        "customer":              so.customer,
        "posting_date":          today(),
        "due_date":              due_date or so.delivery_date or today(),
        "debit_to":              ar,
        "income_account":        inc,
        "sales_order":           so.name,
        "notes":                 f"From Sales Order {so.name}",
        "update_stock":          auto_update_stock,
        "set_warehouse":         getattr(so, "set_warehouse", "") or "",
        "billing_address":       getattr(so, "billing_address", "") or "",
        "billing_address_name":  getattr(so, "billing_address_name", "") or "",
        "shipping_address":      getattr(so, "shipping_address", "") or "",
        "shipping_address_name": getattr(so, "shipping_address_name", "") or "",
        "items":                 si_items,
        "taxes": [
            {"doctype": "Tax Line",
             "charge_type": getattr(t, "charge_type", "On Net Total"),
             "account_head": getattr(t, "account_head", ""),
             "description": getattr(t, "description", ""),
             "rate": flt(getattr(t, "rate", 0))}
            for t in (so.taxes or [])
        ],
    })
    si.flags.ignore_permissions = True
    si.flags.ignore_mandatory = True
    si.insert()
    si.submit()
    # Update billed_qty on SO lines
    for so_item_name, qty in line_updates:
        cur = flt(frappe.db.get_value("Sales Order Item", so_item_name, "billed_qty"))
        frappe.db.set_value("Sales Order Item", so_item_name, "billed_qty",
                            cur + qty, update_modified=False)
    # Refresh SO status
    new_status = _so_status_from_fulfillment(sales_order)
    frappe.db.set_value("Sales Order", sales_order, "status", new_status, update_modified=True)
    frappe.db.commit()
    return {"sales_invoice": si.name, "sales_order": sales_order, "status": new_status}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_sales_order_links(sales_order):
    """Return Sales Invoices linked back to this SO (via SI.sales_order field)."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    sis = frappe.get_all("Sales Invoice",
        filters={"sales_order": sales_order, "is_return": 0},
        fields=["name", "posting_date", "grand_total", "outstanding_amount", "status", "docstatus"],
        order_by="posting_date desc")
    dns = frappe.get_all("Delivery Note",
        filters={"sales_order": sales_order},
        fields=["name", "posting_date", "delivery_date", "total_qty", "status", "docstatus"],
        order_by="posting_date desc")
    return {"sales_invoices": sis or [], "delivery_challans": dns or []}



@frappe.whitelist(allow_guest=False, methods=["POST"])
def submit_sales_order(sales_order):
    """Submit a draft Sales Order — mirrors save_doc(docstatus=1) used by the add drawer."""
    from zoho_books_clone.utils.access import require_module
    require_module("invoices", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    # Sales Order is not a submittable doctype (is_submittable=0).
    # "Submitting" means transitioning status from Draft → To Deliver.
    so = frappe.get_doc("Sales Order", sales_order)
    if (so.status or "Draft") != "Draft":
        return so.as_dict()  # already confirmed — return current state
    frappe.db.set_value("Sales Order", sales_order, {
        "status": "To Deliver",
    }, update_modified=True)
    frappe.db.commit()
    so.reload()
    return so.as_dict()


@frappe.whitelist(allow_guest=False, methods=["POST"])
def cancel_sales_order_safe(sales_order):
    """Cancel an SO only if it has no submitted downstream invoices."""
    from zoho_books_clone.utils.access import require_module
    require_module("invoices", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    submitted_sis = frappe.get_all("Sales Invoice",
        filters={"sales_order": sales_order, "docstatus": 1, "is_return": 0},
        fields=["name", "outstanding_amount"])
    if submitted_sis:
        names = ", ".join(s.name for s in submitted_sis)
        frappe.throw(
            f"Cannot cancel — {len(submitted_sis)} submitted invoice(s) exist: {names}. "
            f"Cancel those invoices first."
        )
    so = frappe.get_doc("Sales Order", sales_order)
    if so.docstatus == 1:
        so.flags.ignore_permissions = True
        so.cancel()
    else:
        # non-submittable build: just set status
        frappe.db.set_value("Sales Order", sales_order, "status", "Cancelled",
                            update_modified=True)
    frappe.db.commit()
    return {"sales_order": sales_order, "status": "Cancelled"}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_sales_order_email_defaults(sales_order):
    """Pre-fill Send Email dialog for a Sales Order. Uses 'Sales Order' template if saved."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    so = frappe.get_doc("Sales Order", sales_order)
    cust_email = frappe.db.get_value("Customer", so.customer, "email_id") or ""

    variables = {
        "customer_name": so.customer_name or so.customer,
        "invoice_no":    so.name,
        "amount":        f"{so.grand_total:,.2f}",
        "due_date":      str(so.delivery_date or ""),
        "company":       so.company or "",
    }

    tpl_subject, tpl_body = _get_email_template("Sales Order")
    if tpl_subject or tpl_body:
        subject = _render_template(tpl_subject or "Sales Order {{invoice_no}} from {{company}}", variables)
        body    = _render_template(tpl_body or "", variables)
    else:
        subject = f"Sales Order {so.name} from {so.company or ''}"
        body = (
            f"Dear {so.customer_name or so.customer},<br><br>"
            f"Confirmation of your Sales Order:<br><br>"
            f"<table style='border-collapse:collapse;font-size:14px'>"
            f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Order #</td><td><b>{so.name}</b></td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Amount</td><td><b>₹{so.grand_total:,.2f}</b></td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Order Date</td><td>{so.transaction_date}</td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Delivery Date</td><td>{so.delivery_date or '—'}</td></tr>"
            f"</table><br>"
            f"Thank you for your order.<br><br>"
            f"Regards,<br>{so.company or ''}"
        )
    return {
        "to": cust_email, "subject": subject, "body": body,
        "sales_order_name": so.name,
        "customer_name": so.customer_name or so.customer,
        "from_email": frappe.session.user,
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def send_sales_order_email(sales_order, to, subject, body, cc=None, pdf_html=None):
    if not to:
        frappe.throw("Recipient email (To) is required.")
    from zoho_books_clone.utils.access import require_module
    require_module("invoices")
    if not frappe.has_permission("Sales Order", "read", sales_order):
        frappe.throw("Not permitted", frappe.PermissionError)
    so = frappe.get_doc("Sales Order", sales_order)
    recipients = [e.strip() for e in to.split(",") if e.strip()]
    cc_list = [e.strip() for e in (cc or "").split(",") if e.strip()]
    attachments = _email_attachment(so.doctype, so.name, "Sales Order", pdf_html)
    _send_business_email(
        recipients, cc_list, subject, body, "Sales Order", sales_order,
        attachments=attachments, company=so.company,
    )
    comm = frappe.get_doc({
        "doctype": "Communication", "communication_type": "Communication",
        "communication_medium": "Email", "sent_or_received": "Sent",
        "subject": subject, "content": body, "sender": frappe.session.user,
        "recipients": to, "cc": cc or "",
        "reference_doctype": "Sales Order", "reference_name": sales_order,
        "status": "Linked",
    })
    comm.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "sent", "to": to, "sales_order": sales_order}


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 — Purchase Order receipt + conversions (mirror of Phase 4)
# Purchase Receipt doctype does not exist in this build, so receipt tracking is
# done via a manual mark_po_received action that bumps received_qty per line.
# ─────────────────────────────────────────────────────────────────────────────

def _po_status_from_fulfillment(po_name):
    rows = frappe.get_all("Purchase Order Item",
        filters={"parent": po_name},
        fields=["qty", "received_qty", "billed_qty"])
    if not rows:
        return "Submitted"
    total_qty = sum(flt(r.qty) for r in rows)
    received  = sum(flt(r.received_qty) for r in rows)
    billed    = sum(flt(r.billed_qty)   for r in rows)
    if total_qty <= 0:
        return "Submitted"
    if billed >= total_qty - 0.001 and received >= total_qty - 0.001:
        return "Closed"
    if billed >= total_qty - 0.001:
        return "Billed"
    if received >= total_qty - 0.001:
        return "Received"
    if received > 0 or billed > 0:
        return "Partially Received"
    return "To Receive"


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_purchase_order_fulfillment(purchase_order):
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    rows = frappe.get_all("Purchase Order Item",
        filters={"parent": purchase_order},
        fields=["name", "item_code", "item_name", "qty", "rate", "amount",
                "received_qty", "billed_qty"],
        order_by="idx asc")
    for r in rows:
        r["remaining_to_receive"] = max(0.0, flt(r["qty"]) - flt(r["received_qty"]))
        r["remaining_to_bill"]    = max(0.0, flt(r["qty"]) - flt(r["billed_qty"]))
    return {"lines": rows, "computed_status": _po_status_from_fulfillment(purchase_order)}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def mark_po_received(purchase_order, line_qtys=None):
    from zoho_books_clone.utils.access import require_module
    require_module("bills", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    if isinstance(line_qtys, str):
        try:
            line_qtys = json.loads(line_qtys) if line_qtys else None
        except json.JSONDecodeError:
            line_qtys = None
    if line_qtys:
        line_qtys = {str(k): v for k, v in line_qtys.items()}

    po = frappe.get_doc("Purchase Order", purchase_order)
    warehouse = getattr(po, "set_warehouse", "") or ""
    company   = getattr(po, "company", "") or ""

    rows = frappe.get_all("Purchase Order Item",
        filters={"parent": purchase_order},
        fields=["name", "item_code", "qty", "received_qty"])
    updated = 0
    for r in rows:
        remaining = max(0.0, flt(r.qty) - flt(r.received_qty))
        if remaining <= 0:
            continue
        if line_qtys:
            add = flt(line_qtys.get(str(r.name), 0))
            if add <= 0:
                continue
            add = min(add, remaining)
        else:
            add = remaining
        new_received = flt(r.received_qty) + add
        frappe.db.set_value("Purchase Order Item", r.name, "received_qty",
                            new_received, update_modified=False)
        # NOTE: do NOT touch ordered_qty here.
        # ordered_qty is released only when the Purchase Invoice is submitted
        # (via PI._release_ordered_qty).  Releasing it here would free the
        # on-order commitment before the bill is raised, making projected_qty
        # show more incoming stock than actually expected.
        updated += 1
    new_status = _po_status_from_fulfillment(purchase_order)
    frappe.db.set_value("Purchase Order", purchase_order, "status", new_status,
                        update_modified=True)
    frappe.db.commit()
    return {"purchase_order": purchase_order, "lines_updated": updated, "status": new_status}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def convert_purchase_order_to_bill(purchase_order, line_qtys=None, bill_no="",
                                   bill_date="", due_date="", batch_nos=None):
    """Create a Bill (Purchase Invoice) from a PO (partial or full).

    batch_nos: optional {po_item_name: batch_no} map for batch-tracked items.
    Bill creation sets update_stock=1 (this is the actual stock-in point for
    goods on a PO — see stock_link.on_purchase_invoice_submit), so batch-
    tracked items must carry a batch_no or the auto-generated Stock Entry
    fails StockEntry.validate()'s "Batch No is required" check.
    """
    from zoho_books_clone.utils.access import require_module
    require_module("bills", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    if isinstance(line_qtys, str):
        try:
            line_qtys = json.loads(line_qtys) if line_qtys else None
        except json.JSONDecodeError:
            line_qtys = None
    if line_qtys:
        line_qtys = {str(k): v for k, v in line_qtys.items()}
    if isinstance(batch_nos, str):
        try:
            batch_nos = json.loads(batch_nos) if batch_nos else None
        except json.JSONDecodeError:
            batch_nos = None
    if batch_nos:
        batch_nos = {str(k): v for k, v in batch_nos.items()}

    po = frappe.get_doc("Purchase Order", purchase_order)
    company = po.company
    ap = frappe.db.get_value("Account",
        {"account_type": "Payable", "company": company, "is_group": 0}, "name")
    exp = _default_expense_account(company)

    pi_items = []
    line_updates = []
    three_way_warnings = []
    for it in (po.items or []):
        remaining_to_bill = max(0.0, flt(it.qty) - flt(it.billed_qty))
        if remaining_to_bill <= 0:
            continue
        if line_qtys:
            qty_bill = min(flt(line_qtys.get(str(it.name), 0)), remaining_to_bill)
        else:
            qty_bill = remaining_to_bill
        if qty_bill <= 0:
            continue
        # Three-way match check: warn if billing more than has been received
        if (flt(it.billed_qty) + qty_bill) > flt(it.received_qty):
            three_way_warnings.append(
                f"{it.item_name or it.item_code}: billing {qty_bill} "
                f"but only {flt(it.received_qty) - flt(it.billed_qty)} received"
            )

        # Batch-tracked items must carry a Batch No — this Bill's
        # update_stock=1 is what actually creates the incoming Stock Entry
        # (via stock_link.on_purchase_invoice_submit), and StockEntry.validate()
        # rejects batch-tracked rows with no batch_no.
        has_batch_no = frappe.db.get_value("Item", it.item_code, "has_batch_no")
        batch_no = (batch_nos or {}).get(str(it.name)) if has_batch_no else None
        if has_batch_no:
            if not batch_no:
                frappe.throw(_(
                    "Item {0} is batch-tracked — select or create a Batch No before billing."
                ).format(it.item_name or it.item_code))
            existing = frappe.db.get_value("Batch", batch_no, ["item", "disabled"], as_dict=True)
            if existing:
                if existing.disabled:
                    frappe.throw(_("Batch {0} is disabled and cannot be used.").format(batch_no))
                if existing.item and existing.item != it.item_code:
                    frappe.throw(_(
                        "Batch {0} belongs to item {1}, not {2}."
                    ).format(batch_no, existing.item, it.item_code))
            else:
                # Pre-create the Batch record so the auto-generated Stock
                # Entry can resolve batch_no as a valid Link on submit —
                # mirrors the Purchase Receipt flow.
                b = frappe.get_doc({
                    "doctype": "Batch",
                    "batch_no": batch_no,
                    "item": it.item_code,
                    "batch_qty": 0,
                })
                b.flags.ignore_permissions = True
                b.insert()

        pi_items.append({
            "doctype": "Purchase Invoice Item",
            "item_code":   it.item_code,
            "item_name":   it.item_name or it.item_code,
            "description": it.description or it.item_name or it.item_code,
            "qty":         qty_bill,
            "uom":         getattr(it, "uom", "") or "Nos",
            "rate":        flt(it.rate),
            "amount":      flt(it.rate) * qty_bill,
            "expense_account": exp,
            "batch_no":    batch_no,
            "tax_code":    getattr(it, "tax_code", None),
        })
        line_updates.append((it.name, qty_bill))

    if not pi_items:
        frappe.throw("Nothing left to bill on this Purchase Order")
    pi_taxes = []

    for tax in po.taxes:
        pi_taxes.append({
            "doctype": "Tax Line",
            "tax_type": tax.tax_type,
            "description": tax.description,
            "rate": flt(tax.rate),
            "tax_amount": flt(tax.tax_amount),
            "account_head": tax.account_head,
            "included_in_print_rate": tax.included_in_print_rate,
        })

    pi = frappe.get_doc({
        "doctype":         "Purchase Invoice",
        "company":         company,
        "supplier":        po.supplier,
        "posting_date":    today(),
        "due_date":        due_date or today(),
        "bill_no":         bill_no or "",
        "bill_date":       bill_date or None,
        "credit_to":       ap,
        "expense_account": exp,
        "purchase_order":  po.name,
        "remark":          f"From Purchase Order {po.name}",
        "update_stock":    1,
        "set_warehouse":   getattr(po, "set_warehouse", "") or "",
        "items":           pi_items,
        "taxes": pi_taxes,
    })
    pi.flags.ignore_permissions = True
    pi.flags.ignore_mandatory = True
    pi.insert()
    pi.submit()
    # Update billed_qty on PO lines
    for poi_name, qty in line_updates:
        cur = flt(frappe.db.get_value("Purchase Order Item", poi_name, "billed_qty"))
        frappe.db.set_value("Purchase Order Item", poi_name, "billed_qty",
                            cur + qty, update_modified=False)
    new_status = _po_status_from_fulfillment(purchase_order)
    frappe.db.set_value("Purchase Order", purchase_order, "status", new_status,
                        update_modified=True)
    frappe.db.commit()
    return {
        "bill": pi.name, "purchase_order": purchase_order,
        "status": new_status,
        "three_way_warnings": three_way_warnings,
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_purchase_order_links(purchase_order):
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    bills = frappe.get_all("Purchase Invoice",
        filters={"purchase_order": purchase_order, "is_return": 0},
        fields=["name", "posting_date", "grand_total", "outstanding_amount", "status", "docstatus"],
        order_by="posting_date desc")
    prs = frappe.get_all("Purchase Receipt",
        filters={"purchase_order": purchase_order},
        fields=["name", "posting_date", "total_qty", "status", "docstatus"],
        order_by="posting_date desc")
    return {"bills": bills or [], "purchase_receipts": prs or []}



@frappe.whitelist(allow_guest=False, methods=["POST"])
def submit_purchase_order(purchase_order):
    """Submit a draft Purchase Order — mirrors save_doc(docstatus=1) used by the add drawer."""
    from zoho_books_clone.utils.access import require_module
    require_module("bills", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    # Purchase Order is a submittable doctype (is_submittable=1).
    po = frappe.get_doc("Purchase Order", purchase_order)
    if po.docstatus == 1:
        return po.as_dict()  # already submitted — return current state
    if po.docstatus != 0:
        frappe.throw("Cannot submit — Purchase Order is not in draft state")
    po.flags.ignore_permissions = True
    po.status = "To Receive"
    po.submit()
    frappe.db.set_value("Purchase Order", purchase_order, "status", "To Receive", update_modified=False)
    frappe.db.commit()
    po.reload()
    return po.as_dict()


@frappe.whitelist(allow_guest=False, methods=["POST"])
def cancel_purchase_order_safe(purchase_order):
    from zoho_books_clone.utils.access import require_module
    require_module("bills", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    submitted_bills = frappe.get_all("Purchase Invoice",
        filters={"purchase_order": purchase_order, "docstatus": 1, "is_return": 0},
        fields=["name"])
    if submitted_bills:
        names = ", ".join(b.name for b in submitted_bills)
        frappe.throw(
            f"Cannot cancel — {len(submitted_bills)} submitted bill(s) exist: {names}. "
            f"Cancel those bills first."
        )
    po = frappe.get_doc("Purchase Order", purchase_order)
    if po.docstatus == 1:
        po.flags.ignore_permissions = True
        po.cancel()
    else:
        frappe.db.set_value("Purchase Order", purchase_order, "status", "Cancelled",
                            update_modified=True)
    frappe.db.commit()
    return {"purchase_order": purchase_order, "status": "Cancelled"}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_purchase_order_email_defaults(purchase_order):
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    po = frappe.get_doc("Purchase Order", purchase_order)
    supplier_email = frappe.db.get_value("Supplier", po.supplier, "email_id") or ""

    variables = {
        "customer_name": po.supplier_name or po.supplier,
        "invoice_no":    po.name,
        "amount":        f"{po.grand_total:,.2f}",
        "due_date":      str(po.expected_delivery_date or ""),
        "company":       po.company or "",
    }

    tpl_subject, tpl_body = _get_email_template("Purchase Order")
    if tpl_subject or tpl_body:
        subject = _render_template(tpl_subject or "Purchase Order {{invoice_no}} from {{company}}", variables)
        body    = _render_template(tpl_body or "", variables)
    else:
        subject = f"Purchase Order {po.name} from {po.company or ''}"
        body = (
            f"Dear {po.supplier_name or po.supplier},<br><br>"
            f"Please find our Purchase Order:<br><br>"
            f"<table style='border-collapse:collapse;font-size:14px'>"
            f"<tr><td style='padding:4px 12px 4px 0;color:#666'>PO #</td><td><b>{po.name}</b></td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Amount</td><td><b>₹{po.grand_total:,.2f}</b></td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Order Date</td><td>{po.transaction_date}</td></tr>"
            f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Expected Delivery</td><td>{po.expected_delivery_date or '—'}</td></tr>"
            f"</table><br>"
            f"Please confirm receipt and expected dispatch.<br><br>"
            f"Regards,<br>{po.company or ''}"
        )
    return {
        "to": supplier_email, "subject": subject, "body": body,
        "purchase_order_name": po.name,
        "supplier_name": po.supplier_name or po.supplier,
        "from_email": frappe.session.user,
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def send_purchase_order_email(purchase_order, to, subject, body, cc=None, pdf_html=None):
    if not to:
        frappe.throw("Recipient email (To) is required.")
    from zoho_books_clone.utils.access import require_module
    require_module("bills")
    if not frappe.has_permission("Purchase Order", "read", purchase_order):
        frappe.throw("Not permitted", frappe.PermissionError)
    po = frappe.get_doc("Purchase Order", purchase_order)
    recipients = [e.strip() for e in to.split(",") if e.strip()]
    cc_list = [e.strip() for e in (cc or "").split(",") if e.strip()]
    attachments = _email_attachment(po.doctype, po.name, "Purchase Order", pdf_html)
    _send_business_email(
        recipients, cc_list, subject, body, "Purchase Order", purchase_order,
        attachments=attachments, company=po.company,
    )
    comm = frappe.get_doc({
        "doctype": "Communication", "communication_type": "Communication",
        "communication_medium": "Email", "sent_or_received": "Sent",
        "subject": subject, "content": body, "sender": frappe.session.user,
        "recipients": to, "cc": cc or "",
        "reference_doctype": "Purchase Order", "reference_name": purchase_order,
        "status": "Linked",
    })
    comm.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "sent", "to": to, "purchase_order": purchase_order}


# ─────────────────────────────────────────────────────────────────────────────
# Tier 2 / Phase 6 — Vendor (Supplier) statement + transaction history
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_vendor_summary(vendor):
    """Return aggregate vendor stats: total outstanding payable, available DN credit,
    counts of open bills + open DNs, latest transaction date."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    if not frappe.db.exists("Supplier", vendor):
        return {"vendor": vendor, "outstanding": 0, "dn_credit": 0,
                "open_bill_count": 0, "open_dn_count": 0, "last_txn_date": None}

    bills = frappe.get_all("Purchase Invoice",
        filters={"supplier": vendor, "is_return": 0, "docstatus": 1},
        fields=["outstanding_amount", "posting_date"])
    outstanding = sum(flt(b.outstanding_amount) for b in bills if flt(b.outstanding_amount) > 0)
    open_bill_count = sum(1 for b in bills if flt(b.outstanding_amount) > 0)

    from zoho_books_clone.accounts.opening_balance import get_opening_balance, get_opening_balance_outstanding
    opening_balance = get_opening_balance("Supplier", vendor)
    outstanding += get_opening_balance_outstanding("Supplier", vendor)

    dns = frappe.get_all("Purchase Invoice",
        filters={"supplier": vendor, "is_return": 1, "docstatus": 1},
        fields=["name"])
    dn_credit = 0
    open_dn_count = 0
    for d in dns:
        bal = get_debit_note_balance(d.name)
        if flt(bal.get("balance", 0)) > 0:
            dn_credit += flt(bal["balance"])
            open_dn_count += 1

    last_dates = [b.posting_date for b in bills if b.posting_date]
    return {
        "vendor": vendor,
        "outstanding": outstanding,
        "opening_balance": opening_balance,
        "dn_credit": dn_credit,
        "open_bill_count": open_bill_count,
        "open_dn_count": open_dn_count,
        "last_txn_date": max(last_dates) if last_dates else None,
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_vendor_transactions(vendor, limit=50):
    """Return a unified, dated transaction history: Bills, Debit Notes, Payments."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    limit = int(limit)
    txns = []

    for b in frappe.get_all("Purchase Invoice",
        filters={"supplier": vendor, "is_return": 0, "docstatus": ["!=", 2]},
        fields=["name", "posting_date", "grand_total", "outstanding_amount", "docstatus", "status"],
        order_by="posting_date desc", limit_page_length=limit):
        txns.append({
            "type": "Bill", "name": b.name, "date": b.posting_date,
            "amount": flt(b.grand_total), "outstanding": flt(b.outstanding_amount),
            "docstatus": b.docstatus, "status": b.status,
        })

    for d in frappe.get_all("Purchase Invoice",
        filters={"supplier": vendor, "is_return": 1, "docstatus": ["!=", 2]},
        fields=["name", "posting_date", "grand_total", "docstatus", "return_against", "status"],
        order_by="posting_date desc", limit_page_length=limit):
        txns.append({
            "type": "Debit Note", "name": d.name, "date": d.posting_date,
            "amount": -abs(flt(d.grand_total)), "outstanding": 0,
            "docstatus": d.docstatus, "status": d.status,
            "related": d.return_against,
        })

    # Payment Entries (Pay-type, to this supplier). This build uses `payment_date`.
    pes = frappe.db.sql("""
        SELECT name, payment_date, paid_amount, mode_of_payment, docstatus
        FROM `tabPayment Entry`
        WHERE party_type='Supplier' AND party=%s AND payment_type='Pay' AND docstatus!=2
        ORDER BY payment_date DESC LIMIT %s
    """, (vendor, limit), as_dict=True)
    for p in pes:
        txns.append({
            "type": "Payment", "name": p.name, "date": p.payment_date,
            "amount": -abs(flt(p.paid_amount)), "outstanding": 0,
            "docstatus": p.docstatus, "status": p.mode_of_payment or "Payment",
        })

    txns.sort(key=lambda x: (x.get("date") or "", x.get("name") or ""), reverse=True)
    return txns[:limit]


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_vendor_statement(vendor, from_date=None, to_date=None):
    """Account statement: chronological list with running balance.

    Includes the vendor's opening balance (if any) as the first row, dated
    before any other transaction, so the running balance actually reflects
    it — this endpoint used to ignore opening_balance completely.
    """
    from zoho_books_clone.accounts.opening_balance import get_opening_balance

    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    fd = frappe._dict({"from_date": from_date, "to_date": to_date})
    rows = []

    opening_balance = get_opening_balance("Supplier", vendor)
    if opening_balance:
        rows.append({"date": None, "ref": "Opening Balance",
                     "type": "Opening Balance", "debit": 0, "credit": flt(opening_balance)})

    bills = frappe.get_all("Purchase Invoice",
        filters={"supplier": vendor, "docstatus": 1, "is_return": 0},
        fields=["name", "posting_date", "grand_total"],
        order_by="posting_date asc")
    for b in bills:
        if fd.from_date and str(b.posting_date) < fd.from_date: continue
        if fd.to_date   and str(b.posting_date) > fd.to_date:   continue
        rows.append({"date": b.posting_date, "ref": b.name,
                     "type": "Bill", "debit": 0, "credit": flt(b.grand_total)})

    dns = frappe.get_all("Purchase Invoice",
        filters={"supplier": vendor, "docstatus": 1, "is_return": 1},
        fields=["name", "posting_date", "grand_total"],
        order_by="posting_date asc")
    for d in dns:
        if fd.from_date and str(d.posting_date) < fd.from_date: continue
        if fd.to_date   and str(d.posting_date) > fd.to_date:   continue
        rows.append({"date": d.posting_date, "ref": d.name,
                     "type": "Debit Note", "debit": abs(flt(d.grand_total)), "credit": 0})

    pes = frappe.db.sql("""
        SELECT name, payment_date, paid_amount, mode_of_payment
        FROM `tabPayment Entry`
        WHERE party_type='Supplier' AND party=%s AND payment_type='Pay' AND docstatus=1
        ORDER BY payment_date ASC
    """, (vendor,), as_dict=True)
    for p in pes:
        if fd.from_date and str(p.payment_date) < fd.from_date: continue
        if fd.to_date   and str(p.payment_date) > fd.to_date:   continue
        rows.append({"date": p.payment_date, "ref": p.name,
                     "type": "Payment", "debit": flt(p.paid_amount), "credit": 0,
                     "mode_of_payment": p.mode_of_payment or ""})

    rows.sort(key=lambda r: (str(r["date"]) if r["date"] else "", r["ref"] or ""))
    running = 0.0
    for r in rows:
        running += flt(r["credit"]) - flt(r["debit"])
        r["balance"] = running

    total_billed = sum(flt(r["credit"]) for r in rows if r["type"] == "Bill")
    total_paid   = sum(flt(r["debit"])  for r in rows if r["type"] == "Payment")
    total_dn     = sum(flt(r["debit"])  for r in rows if r["type"] == "Debit Note")

    return {
        "vendor": vendor, "from_date": from_date, "to_date": to_date,
        "rows": rows,
        "totals": {
            "billed": total_billed, "paid": total_paid,
            "debit_notes": total_dn, "closing_balance": running,
        },
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_vendor_email_defaults(vendor):
    """Email template defaults for sending a statement to a vendor."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    v = frappe.db.get_value("Supplier", vendor,
        ["supplier_name", "email_id", "books_company"], as_dict=True)
    if not v:
        frappe.throw(f"Supplier {vendor} not found")
    summary = get_vendor_summary(vendor)
    subject = f"Account Statement — {v.supplier_name}"
    body = (
        f"Dear {v.supplier_name},<br><br>"
        f"Please find your account statement below.<br><br>"
        f"<table style='border-collapse:collapse;font-size:14px'>"
        f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Total Outstanding</td>"
        f"<td><b>₹{summary['outstanding']:,.2f}</b></td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Open Bills</td>"
        f"<td>{summary['open_bill_count']}</td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Unused Debit-Note Credits</td>"
        f"<td>₹{summary['dn_credit']:,.2f}</td></tr>"
        f"</table><br>"
        f"Regards,<br>{v.books_company or ''}"
    )
    return {
        "to": v.email_id or "", "subject": subject, "body": body,
        "vendor": vendor, "supplier_name": v.supplier_name,
        "from_email": frappe.session.user,
    }


@frappe.whitelist(allow_guest=False, methods=["POST"])
def send_vendor_statement_email(vendor, to, subject, body, cc=None):
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    if not to:
        frappe.throw("Recipient email (To) is required.")
    from zoho_books_clone.utils.access import require_module, assert_company
    require_module("customers")
    # Supplier is only ever touched via frappe.db.get_value below, never
    # frappe.get_doc, so Frappe's has_permission hook never runs here --
    # without this, any company member could email another company's
    # vendor statement just by naming the Supplier.
    assert_company(frappe.db.get_value("Supplier", vendor, "books_company"))

    recipients = [e.strip() for e in to.split(",") if e.strip()]
    cc_list = [e.strip() for e in (cc or "").split(",") if e.strip()]
    _send_business_email(
        recipients, cc_list, subject, body, "Supplier", vendor,
        company=frappe.db.get_value("Supplier", vendor, "books_company"),
    )
    comm = frappe.get_doc({
        "doctype": "Communication", "communication_type": "Communication",
        "communication_medium": "Email", "sent_or_received": "Sent",
        "subject": subject, "content": body, "sender": frappe.session.user,
        "recipients": to, "cc": cc or "",
        "reference_doctype": "Supplier", "reference_name": vendor,
        "status": "Linked",
    })
    comm.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "sent", "to": to, "vendor": vendor}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def bulk_set_vendor_disabled(vendor_names, disabled):
    """Bulk enable/disable. vendor_names = list/json list. disabled = 0|1."""
    from zoho_books_clone.utils.access import require_module
    require_module("customers", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    if isinstance(vendor_names, str):
        vendor_names = json.loads(vendor_names)
    disabled = int(disabled)
    done = 0
    for v in (vendor_names or []):
        try:
            frappe.db.set_value("Supplier", v, "disabled", disabled, update_modified=True)
            done += 1
        except Exception:
            pass
    frappe.db.commit()
    return {"updated": done, "disabled": disabled}


# ─────────────────────────────────────────────────────────────────────────────
# Tier 2 / Phase 7 — Customer statement + transaction history (mirror of vendors)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_customer_summary(customer):
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    if not frappe.db.exists("Customer", customer):
        return {"customer": customer, "outstanding": 0, "cn_credit": 0,
                "open_invoice_count": 0, "open_cn_count": 0, "last_txn_date": None}

    invs = frappe.get_all("Sales Invoice",
        filters={"customer": customer, "is_return": 0, "docstatus": 1},
        fields=["outstanding_amount", "posting_date"])
    outstanding = sum(flt(i.outstanding_amount) for i in invs if flt(i.outstanding_amount) > 0)
    open_inv_count = sum(1 for i in invs if flt(i.outstanding_amount) > 0)

    from zoho_books_clone.accounts.opening_balance import get_opening_balance, get_opening_balance_outstanding
    opening_balance = get_opening_balance("Customer", customer)
    outstanding += get_opening_balance_outstanding("Customer", customer)

    cns = frappe.get_all("Sales Invoice",
        filters={"customer": customer, "is_return": 1, "docstatus": 1},
        fields=["name"])
    cn_credit = 0
    open_cn_count = 0
    for c in cns:
        bal = get_credit_note_balance(c.name)
        if flt(bal.get("balance", 0)) > 0:
            cn_credit += flt(bal["balance"])
            open_cn_count += 1

    last_dates = [i.posting_date for i in invs if i.posting_date]
    return {
        "customer": customer,
        "outstanding": outstanding,
        "opening_balance": opening_balance,
        "cn_credit": cn_credit,
        "open_invoice_count": open_inv_count,
        "open_cn_count": open_cn_count,
        "last_txn_date": max(last_dates) if last_dates else None,
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_customer_transactions(customer, limit=50):
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    limit = int(limit)
    txns = []

    for i in frappe.get_all("Sales Invoice",
        filters={"customer": customer, "is_return": 0, "docstatus": ["!=", 2]},
        fields=["name", "posting_date", "grand_total", "outstanding_amount", "docstatus", "status"],
        order_by="posting_date desc", limit_page_length=limit):
        txns.append({
            "type": "Invoice", "name": i.name, "date": i.posting_date,
            "amount": flt(i.grand_total), "outstanding": flt(i.outstanding_amount),
            "docstatus": i.docstatus, "status": i.status,
        })

    for c in frappe.get_all("Sales Invoice",
        filters={"customer": customer, "is_return": 1, "docstatus": ["!=", 2]},
        fields=["name", "posting_date", "grand_total", "docstatus", "return_against", "status"],
        order_by="posting_date desc", limit_page_length=limit):
        txns.append({
            "type": "Credit Note", "name": c.name, "date": c.posting_date,
            "amount": -abs(flt(c.grand_total)), "outstanding": 0,
            "docstatus": c.docstatus, "status": c.status,
            "related": c.return_against,
        })

    pes = frappe.db.sql("""
        SELECT name, payment_date, paid_amount, mode_of_payment, docstatus
        FROM `tabPayment Entry`
        WHERE party_type='Customer' AND party=%s AND payment_type='Receive' AND docstatus!=2
        ORDER BY payment_date DESC LIMIT %s
    """, (customer, limit), as_dict=True)
    for p in pes:
        txns.append({
            "type": "Payment", "name": p.name, "date": p.payment_date,
            "amount": -abs(flt(p.paid_amount)), "outstanding": 0,
            "docstatus": p.docstatus, "status": p.mode_of_payment or "Payment",
        })

    txns.sort(key=lambda x: (x.get("date") or "", x.get("name") or ""), reverse=True)
    return txns[:limit]


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_customer_statement(customer, from_date=None, to_date=None):
    """Customer statement (AR perspective): Invoice = debit (owed), Payment/CN = credit.

    Includes the customer's opening balance (if any) as the first row — this
    endpoint used to ignore opening_balance completely.
    """
    from zoho_books_clone.accounts.opening_balance import get_opening_balance

    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    fd = frappe._dict({"from_date": from_date, "to_date": to_date})
    rows = []

    opening_balance = get_opening_balance("Customer", customer)
    if opening_balance:
        rows.append({"date": None, "ref": "Opening Balance",
                     "type": "Opening Balance", "debit": flt(opening_balance), "credit": 0})

    invs = frappe.get_all("Sales Invoice",
        filters={"customer": customer, "docstatus": 1, "is_return": 0},
        fields=["name", "posting_date", "grand_total"],
        order_by="posting_date asc")
    for i in invs:
        if fd.from_date and str(i.posting_date) < fd.from_date: continue
        if fd.to_date   and str(i.posting_date) > fd.to_date:   continue
        rows.append({"date": i.posting_date, "ref": i.name,
                     "type": "Invoice", "debit": flt(i.grand_total), "credit": 0})

    cns = frappe.get_all("Sales Invoice",
        filters={"customer": customer, "docstatus": 1, "is_return": 1},
        fields=["name", "posting_date", "grand_total"],
        order_by="posting_date asc")
    for c in cns:
        if fd.from_date and str(c.posting_date) < fd.from_date: continue
        if fd.to_date   and str(c.posting_date) > fd.to_date:   continue
        rows.append({"date": c.posting_date, "ref": c.name,
                     "type": "Credit Note", "debit": 0, "credit": abs(flt(c.grand_total))})

    pes = frappe.db.sql("""
        SELECT name, payment_date, paid_amount, mode_of_payment
        FROM `tabPayment Entry`
        WHERE party_type='Customer' AND party=%s AND payment_type='Receive' AND docstatus=1
        ORDER BY payment_date ASC
    """, (customer,), as_dict=True)
    for p in pes:
        if fd.from_date and str(p.payment_date) < fd.from_date: continue
        if fd.to_date   and str(p.payment_date) > fd.to_date:   continue
        rows.append({"date": p.payment_date, "ref": p.name,
                     "type": "Payment", "debit": 0, "credit": flt(p.paid_amount),
                     "mode_of_payment": p.mode_of_payment or ""})

    rows.sort(key=lambda r: (str(r["date"]) if r["date"] else "", r["ref"] or ""))
    running = 0.0
    for r in rows:
        running += flt(r["debit"]) - flt(r["credit"])
        r["balance"] = running

    total_inv  = sum(flt(r["debit"])  for r in rows if r["type"] == "Invoice")
    total_paid = sum(flt(r["credit"]) for r in rows if r["type"] == "Payment")
    total_cn   = sum(flt(r["credit"]) for r in rows if r["type"] == "Credit Note")

    return {
        "customer": customer, "from_date": from_date, "to_date": to_date,
        "rows": rows,
        "totals": {
            "invoiced": total_inv, "paid": total_paid,
            "credit_notes": total_cn, "closing_balance": running,
        },
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_customer_email_defaults(customer):
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    c = frappe.db.get_value("Customer", customer,
        ["customer_name", "email_id", "books_company"], as_dict=True)
    if not c:
        frappe.throw(f"Customer {customer} not found")
    summary = get_customer_summary(customer)
    subject = f"Account Statement — {c.customer_name}"
    body = (
        f"Dear {c.customer_name},<br><br>"
        f"Please find your account statement below.<br><br>"
        f"<table style='border-collapse:collapse;font-size:14px'>"
        f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Total Outstanding</td>"
        f"<td><b>₹{summary['outstanding']:,.2f}</b></td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Open Invoices</td>"
        f"<td>{summary['open_invoice_count']}</td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0;color:#666'>Available Credit Notes</td>"
        f"<td>₹{summary['cn_credit']:,.2f}</td></tr>"
        f"</table><br>"
        f"Kindly settle the open invoices at your earliest.<br><br>"
        f"Regards,<br>{c.books_company or ''}"
    )
    return {
        "to": c.email_id or "", "subject": subject, "body": body,
        "customer": customer, "customer_name": c.customer_name,
        "from_email": frappe.session.user,
    }


@frappe.whitelist(allow_guest=False, methods=["POST"])
def send_customer_statement_email(customer, to, subject, body, cc=None):
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    if not to:
        frappe.throw("Recipient email (To) is required.")
    from zoho_books_clone.utils.access import require_module, assert_company
    require_module("customers")
    assert_company(frappe.db.get_value("Customer", customer, "books_company"))

    recipients = [e.strip() for e in to.split(",") if e.strip()]
    cc_list = [e.strip() for e in (cc or "").split(",") if e.strip()]
    _send_business_email(
        recipients, cc_list, subject, body, "Customer", customer,
        company=frappe.db.get_value("Customer", customer, "books_company"),
    )
    comm = frappe.get_doc({
        "doctype": "Communication", "communication_type": "Communication",
        "communication_medium": "Email", "sent_or_received": "Sent",
        "subject": subject, "content": body, "sender": frappe.session.user,
        "recipients": to, "cc": cc or "",
        "reference_doctype": "Customer", "reference_name": customer,
        "status": "Linked",
    })
    comm.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "sent", "to": to, "customer": customer}


# ─────────────────────────────────────────────────────────────────────────────
# Tier 2 / Phase 8 — Payments (Payment Entry — unified across SI / PI / CN / DN)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_payment_applications(payment_entry_name):
    """Return the list of invoices/bills/CNs/DNs this Payment Entry was applied to."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    refs = frappe.get_all(
        "Payment Entry Reference",
        filters={"parent": payment_entry_name},
        fields=["reference_doctype", "reference_name", "allocated_amount", "outstanding_amount"],
    )
    apps = []
    for r in refs:
        cur_out = None
        is_return = 0
        total = None
        if r.reference_doctype in ("Sales Invoice", "Purchase Invoice"):
            row = frappe.db.get_value(r.reference_doctype, r.reference_name,
                ["outstanding_amount", "is_return", "grand_total", "docstatus"], as_dict=True)
            if row:
                cur_out = row.outstanding_amount
                is_return = row.is_return or 0
                total = abs(flt(row.grand_total))
        apps.append({
            "ref_doctype": r.reference_doctype,
            "ref_name": r.reference_name,
            "allocated": abs(flt(r.allocated_amount)),
            "total": total,
            "outstanding_now": flt(cur_out) if cur_out is not None else None,
            "is_return": is_return,
        })
    return apps


@frappe.whitelist(allow_guest=False, methods=["POST"])
def cancel_payment_entry_safe(payment_entry_name):
    """Cancel a Payment Entry; outstanding on linked invoices/bills will recompute via GL hooks."""
    from zoho_books_clone.utils.access import require_module
    require_module("payments", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    pe = frappe.get_doc("Payment Entry", payment_entry_name)
    if pe.docstatus != 1:
        frappe.throw(f"Payment Entry {payment_entry_name} is not submitted")
    pe.flags.ignore_permissions = True
    pe.cancel()
    frappe.db.commit()
    return {"payment_entry": payment_entry_name, "status": "Cancelled"}


# ─────────────────────────────────────────────────────────────────────────────
# Tier 2 / Phase 9 — Expense summary (custom `Expense` doctype, not HR's Expense Claim)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_expense_summary(company=None, from_date=None, to_date=None):
    """Aggregate expenses for the company dashboard / Expenses page summary strip."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    company = company or _get_company(frappe.session.user)
    filters = {"company": company}
    if from_date: filters["posting_date"] = [">=", from_date]
    if to_date:
        # merge with above filter if present
        if "posting_date" in filters:
            filters["posting_date"] = ["between", [from_date, to_date]]
        else:
            filters["posting_date"] = ["<=", to_date]

    rows = frappe.get_all("Expense",
        filters=filters,
        fields=["name", "posting_date", "expense_type", "amount", "tax_amount",
                "total_amount", "status", "docstatus", "vendor"])
    total = sum(flt(r.total_amount) or flt(r.amount) for r in rows)
    by_category = {}
    for r in rows:
        cat = r.expense_type or "Uncategorized"
        by_category[cat] = by_category.get(cat, 0) + (flt(r.total_amount) or flt(r.amount))
    return {
        "company": company, "from_date": from_date, "to_date": to_date,
        "total_count": len(rows),
        "total_amount": total,
        "by_category": sorted(by_category.items(), key=lambda kv: -kv[1]),
        "draft_count":     sum(1 for r in rows if r.docstatus == 0),
        "submitted_count": sum(1 for r in rows if r.docstatus == 1),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tier 3 — Banking: dashboard summary + reconciliation match
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_banking_summary(company=None):
    """Headline KPIs + per-account balances for the Banking dashboard."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    company = company or _get_company(frappe.session.user)

    accounts = frappe.get_all("Bank Account",
        filters={"company": company},
        fields=["name", "account_name", "bank_name", "account_number",
                "currency", "gl_account", "is_default", "current_balance"],
        order_by="account_name asc")

    # Live balance from GL for each linked gl_account
    from zoho_books_clone.db.queries import get_account_balance
    for a in accounts:
        if a.gl_account:
            try:
                a["live_balance"] = flt(get_account_balance(a.gl_account))
            except Exception:
                a["live_balance"] = flt(a.current_balance)
        else:
            a["live_balance"] = flt(a.current_balance)

    total_balance = sum(flt(a.get("live_balance")) for a in accounts)

    # Recent bank transactions across all accounts
    recent = frappe.db.sql("""
        SELECT bt.name, bt.bank_account, bt.date, bt.description,
               bt.debit, bt.credit, bt.status, bt.reference_number
        FROM `tabBank Transaction` bt
        ORDER BY bt.date DESC, bt.creation DESC
        LIMIT 20
    """, as_dict=True)

    # Unreconciled count
    unrec = frappe.db.sql("""
        SELECT COUNT(*) AS c FROM `tabBank Transaction`
        WHERE status IN ('Unreconciled','Pending') OR status IS NULL
    """, as_dict=True)
    unrec_count = unrec[0].c if unrec else 0

    # Recent transfers (JE voucher_type=Bank Entry)
    transfers = frappe.db.sql("""
        SELECT name, posting_date, total_debit, remark, docstatus
        FROM `tabJournal Entry`
        WHERE company=%s AND voucher_type='Bank Entry'
        ORDER BY posting_date DESC LIMIT 10
    """, (company,), as_dict=True)

    return {
        "company": company,
        "accounts": accounts,
        "account_count": len(accounts),
        "total_balance": total_balance,
        "recent_transactions": recent,
        "unreconciled_count": unrec_count,
        "recent_transfers": transfers,
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_bank_reconciliation(bank_account, from_date, to_date):
    """Pull bank transactions + linked GL movements for reconciliation."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    # Bank Transaction uses `debit`/`credit`, not deposit/withdrawal
    bts = frappe.db.sql("""
        SELECT name, date, description, debit, credit, balance,
               reference_number, status, payment_entry
        FROM `tabBank Transaction`
        WHERE bank_account=%(b)s AND date BETWEEN %(f)s AND %(t)s
        ORDER BY date ASC, creation ASC
    """, {"b": bank_account, "f": from_date, "t": to_date}, as_dict=True)

    # Resolve the linked GL account on this Bank Account
    gl_account = frappe.db.get_value("Bank Account", bank_account, "gl_account")
    gles = []
    gl_balance = 0
    if gl_account:
        gles = frappe.db.sql("""
            SELECT name, posting_date, debit, credit, voucher_type, voucher_no, remarks
            FROM `tabGeneral Ledger Entry`
            WHERE account=%(a)s AND posting_date BETWEEN %(f)s AND %(t)s AND is_cancelled=0
            ORDER BY posting_date ASC
        """, {"a": gl_account, "f": from_date, "t": to_date}, as_dict=True)
        gl_balance = sum(flt(g.debit) - flt(g.credit) for g in gles)

    bank_balance = sum(flt(b.debit) - flt(b.credit) for b in bts)
    reconciled = sum(1 for b in bts if (b.status or "").lower() in ("reconciled","matched"))

    return {
        "bank_account": bank_account,
        "gl_account": gl_account,
        "from_date": from_date, "to_date": to_date,
        "bank_transactions": bts,
        "gl_entries": gles,
        "bank_balance": bank_balance,
        "gl_balance": gl_balance,
        "difference": gl_balance - bank_balance,
        "total_count": len(bts),
        "reconciled_count": reconciled,
        "unreconciled_count": len(bts) - reconciled,
    }


@frappe.whitelist(allow_guest=False, methods=["POST"])
def reconcile_bank_transaction(bank_transaction_name, payment_entry_name=None):
    """Mark a Bank Transaction as reconciled, optionally linking a Payment Entry.

    When linked to a Payment Entry, the Bank Transaction's own GL posting is
    suspended — the Payment Entry already recorded the real accounting impact
    of this cash movement, so keeping both live double-counts it on the
    Bank/Cash ledger. The Bank Transaction becomes a reconciliation record
    confirming the bank feed agrees with the Payment Entry, not a second
    independent posting.
    """
    from zoho_books_clone.utils.access import require_module
    require_module("banking", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    updates = {"status": "Reconciled"}
    if payment_entry_name and frappe.db.exists("Payment Entry", payment_entry_name):
        updates["payment_entry"] = payment_entry_name
    for k, v in updates.items():
        frappe.db.set_value("Bank Transaction", bank_transaction_name, k, v, update_modified=True)

    linked_payment = payment_entry_name or frappe.db.get_value(
        "Bank Transaction", bank_transaction_name, "payment_entry"
    )
    if linked_payment:
        from zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry import set_voucher_gl_suspended
        set_voucher_gl_suspended("Bank Transaction", bank_transaction_name, True)

    frappe.db.commit()
    return {"bank_transaction": bank_transaction_name, "status": "Reconciled",
            "payment_entry": payment_entry_name}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def unreconcile_bank_transaction(bank_transaction_name):
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    from zoho_books_clone.utils.access import require_module, assert_company
    require_module("banking", write=True)
    # Writes below are raw frappe.db.set_value calls, which bypass Frappe's
    # has_permission hook entirely -- without this, a member of a different
    # company could unreconcile another company's Bank Transaction by name.
    assert_company(frappe.db.get_value("Bank Transaction", bank_transaction_name, "company"))

    had_payment_entry = frappe.db.get_value("Bank Transaction", bank_transaction_name, "payment_entry")
    frappe.db.set_value("Bank Transaction", bank_transaction_name, "status",
                        "Unreconciled", update_modified=True)
    frappe.db.set_value("Bank Transaction", bank_transaction_name, "payment_entry",
                        None, update_modified=True)

    # If matching a Payment Entry had suspended this transaction's own GL
    # posting, restore it now that the two are no longer linked — otherwise
    # this cash movement would vanish from the ledger entirely.
    if had_payment_entry:
        from zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry import set_voucher_gl_suspended
        set_voucher_gl_suspended("Bank Transaction", bank_transaction_name, False)

    frappe.db.commit()
    return {"bank_transaction": bank_transaction_name, "status": "Unreconciled"}


# ─────────────────────────────────────────────────────────────────────────────
# Cheque lifecycle: Issued → Cleared / Bounced / Cancelled
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_cheque_list(company=None, status=None):
    """List all Payment Entries with mode_of_payment='Cheque' + their lifecycle state."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    company = company or _get_company(frappe.session.user)
    # Guard: cheque_status column may not exist if bench migrate hasn't run yet
    cols = {r[0] for r in frappe.db.sql(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='tabPayment Entry' AND COLUMN_NAME='cheque_status'"
    )}
    if "cheque_status" not in cols:
        return []
    where = ["mode_of_payment='Cheque'", "company=%(co)s"]
    params = {"co": company}
    if status:
        where.append("cheque_status=%(st)s")
        params["st"] = status
    rows = frappe.db.sql(f"""
        SELECT name, party_type, party, party_name, payment_type, payment_date,
               paid_amount, reference_no, reference_date, mode_of_payment,
               cheque_status, cheque_cleared_date, cheque_bounce_reason,
               docstatus
        FROM `tabPayment Entry`
        WHERE {' AND '.join(where)}
        ORDER BY payment_date DESC, creation DESC
        LIMIT 200
    """, params, as_dict=True)
    for r in rows:
        if not r.cheque_status:
            r.cheque_status = "Issued"
    return rows


@frappe.whitelist(allow_guest=False, methods=["POST"])
def update_cheque_status(payment_entry_name, new_status, cleared_date=None, bounce_reason=None):
    """Transition a cheque between Issued → Cleared / Bounced / Cancelled."""
    from zoho_books_clone.utils.access import require_module
    require_module("banking", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    if new_status not in ("Issued", "Cleared", "Bounced", "Cancelled"):
        frappe.throw(f"Invalid cheque status: {new_status}")
    pe = frappe.db.get_value("Payment Entry", payment_entry_name,
        ["mode_of_payment", "docstatus"], as_dict=True)
    if not pe:
        frappe.throw(f"Payment Entry {payment_entry_name} not found")
    if pe.mode_of_payment != "Cheque":
        frappe.throw("Cheque status can only be set on Cheque-mode Payment Entries")

    updates = {"cheque_status": new_status}
    if new_status == "Cleared":
        updates["cheque_cleared_date"] = cleared_date or today()
        updates["cheque_bounce_reason"] = None
    elif new_status == "Bounced":
        if not bounce_reason:
            frappe.throw("Bounce reason is required when marking a cheque as Bounced")
        updates["cheque_bounce_reason"] = bounce_reason
        updates["cheque_cleared_date"] = None
    elif new_status == "Cancelled":
        updates["cheque_cleared_date"] = None
    elif new_status == "Issued":
        updates["cheque_cleared_date"] = None
        updates["cheque_bounce_reason"] = None

    for k, v in updates.items():
        frappe.db.set_value("Payment Entry", payment_entry_name, k, v, update_modified=True)
    frappe.db.commit()
    return {"payment_entry": payment_entry_name, "cheque_status": new_status, **updates}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_cheque_summary(company=None):
    """Counts + total values per cheque lifecycle state."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    company = company or _get_company(frappe.session.user)
    # Guard: cheque_status column may not exist if bench migrate hasn't run yet
    cols = {r[0] for r in frappe.db.sql(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='tabPayment Entry' AND COLUMN_NAME='cheque_status'"
    )}
    if "cheque_status" not in cols:
        return {
            "by_state": {}, "total_count": 0, "total_value": 0,
            "issued":    {"count": 0, "total": 0},
            "cleared":   {"count": 0, "total": 0},
            "bounced":   {"count": 0, "total": 0},
            "cancelled": {"count": 0, "total": 0},
        }
    rows = frappe.db.sql("""
        SELECT COALESCE(cheque_status,'Issued') AS state,
               COUNT(*) AS cnt,
               COALESCE(SUM(paid_amount),0) AS total
        FROM `tabPayment Entry`
        WHERE mode_of_payment='Cheque' AND company=%s
        GROUP BY COALESCE(cheque_status,'Issued')
    """, (company,), as_dict=True)
    by_state = {r.state: {"count": r["cnt"], "total": flt(r["total"])} for r in rows}
    total_count = sum(s["count"] for s in by_state.values())
    total_value = sum(s["total"] for s in by_state.values())
    return {
        "by_state": by_state, "total_count": total_count, "total_value": total_value,
        "issued":   by_state.get("Issued",    {"count": 0, "total": 0}),
        "cleared":  by_state.get("Cleared",   {"count": 0, "total": 0}),
        "bounced":  by_state.get("Bounced",   {"count": 0, "total": 0}),
        "cancelled":by_state.get("Cancelled", {"count": 0, "total": 0}),
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def suggest_payment_matches(bank_transaction_name, date_tolerance_days=7, amount_tolerance=0.01):
    """Suggest Payment Entries that likely match a Bank Transaction.

    Score formula: amount match (0-60) + date proximity (0-30) + reference
    match (0-10). Returns top 5 candidates by score, descending.
    """
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    bt = frappe.db.get_value("Bank Transaction", bank_transaction_name,
        ["bank_account", "date", "debit", "credit", "description", "reference_number", "status"],
        as_dict=True)
    if not bt:
        frappe.throw(f"Bank Transaction {bank_transaction_name} not found")
    if (bt.status or "").lower() in ("reconciled", "matched"):
        return {"already_reconciled": True, "matches": []}

    # Bank-side amount + direction:
    #   debit on BTXN  = money OUT of bank (Pay type PE expected)
    #   credit on BTXN = money INTO bank (Receive type PE expected)
    amount = flt(bt.debit) if flt(bt.debit) > 0 else flt(bt.credit)
    pe_type_pref = "Pay" if flt(bt.debit) > 0 else "Receive"
    if amount <= 0:
        return {"matches": [], "reason": "Bank Transaction has no amount"}

    from datetime import timedelta
    from frappe.utils import getdate
    date_obj = getdate(bt.date)
    days = int(date_tolerance_days)
    tol = flt(amount_tolerance) * amount  # 1% by default

    # Candidate PEs within ± days, amount within tol
    candidates = frappe.db.sql("""
        SELECT name, payment_type, party, party_name, party_type,
               payment_date, paid_amount, mode_of_payment, reference_no, docstatus
        FROM `tabPayment Entry`
        WHERE docstatus = 1
          AND ABS(paid_amount - %(amt)s) <= %(tol)s
          AND payment_date BETWEEN %(d1)s AND %(d2)s
        ORDER BY ABS(DATEDIFF(payment_date, %(centre)s)) ASC
        LIMIT 25
    """, {
        "amt": amount, "tol": max(0.01, tol),
        "d1": date_obj - timedelta(days=days),
        "d2": date_obj + timedelta(days=days),
        "centre": date_obj,
    }, as_dict=True)

    # Exclude PEs already linked to another BTXN
    already_linked = frappe.db.sql_list("""
        SELECT payment_entry FROM `tabBank Transaction`
        WHERE payment_entry IS NOT NULL AND payment_entry != ''
    """)
    candidates = [c for c in candidates if c.name not in already_linked]

    desc = (bt.description or "").lower()
    ref  = (bt.reference_number or "").lower()
    scored = []
    for c in candidates:
        score = 0
        # Amount match — closer is better (max 60)
        diff = abs(flt(c.paid_amount) - amount)
        score += max(0, 60 - (diff / max(amount, 1)) * 1000)
        # Date proximity — same day = 30, decay over `days`
        ddiff = abs((getdate(c.payment_date) - date_obj).days)
        score += max(0, 30 - (ddiff * 30 / max(days, 1)))
        # Type alignment — Receive/Pay match
        if c.payment_type == pe_type_pref:
            score += 5
        # Reference match — exact wins, partial helps
        cref = (c.reference_no or "").lower()
        if cref and (cref == ref or (ref and (cref in ref or ref in cref))):
            score += 10
        elif cref and desc and cref in desc:
            score += 5
        # Party hit in description
        pname = (c.party_name or c.party or "").lower()
        if pname and pname in desc:
            score += 5
        scored.append({**c, "score": round(score, 1)})

    scored.sort(key=lambda x: -x["score"])
    return {
        "bank_transaction": bank_transaction_name,
        "bt_amount": amount,
        "bt_direction": "in" if flt(bt.debit) > 0 else "out",
        "matches": scored[:5],
    }


def _parse_statement_date(raw):
    """Best-effort date parser: handles ISO/slash/dash strings and Excel
    serial-date numbers (in case a spreadsheet cell wasn't text-formatted)."""
    from frappe.utils import getdate
    raw = (raw or "").strip()
    if not raw:
        return None
    # Excel serial date (e.g. "45678" or "45678.0")
    try:
        serial = float(raw)
        if 20000 < serial < 60000:  # sane range for modern dates
            from datetime import datetime, timedelta
            epoch = datetime(1899, 12, 30)  # Excel's day-0, accounting for its leap-year bug
            return (epoch + timedelta(days=serial)).date()
    except ValueError:
        pass
    # getdate() only reliably parses ISO "YYYY-MM-DD" strings and raises
    # InvalidDateError on anything else — but bank statements commonly use
    # DD-MM-YYYY / DD/MM/YYYY (India) or MM/DD/YYYY. Try those explicitly
    # before giving up, otherwise every non-ISO row in the file gets
    # silently skipped as "no valid date".
    from datetime import datetime as _dt
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y", "%Y/%m/%d"):
        try:
            return _dt.strptime(raw, fmt).date()
        except ValueError:
            continue
    try:
        return getdate(raw)
    except Exception:
        return None


def _find_existing_bank_transaction_match(bank_account, date, debit, credit, exclude_names):
    """Look for an already-existing Bank Transaction that represents the same
    real-world movement as an incoming statement row.

    Every Payment Entry submission auto-creates its own mirror Bank Transaction
    (see api/books_data.py::_create_bank_transaction), already Unreconciled and
    already on this bank_account. So a statement row usually isn't a "new"
    transaction at all — it's confirmation that one of these mirrors cleared.
    Matching against that existing row (and marking IT reconciled) is what
    reconciliation means; inserting a second row for the same money movement
    creates a duplicate and double-counts the balance.

    Only auto-matches on an exact, unambiguous date + debit + credit match.
    """
    candidates = frappe.db.sql("""
        SELECT name FROM `tabBank Transaction`
        WHERE docstatus = 1
          AND bank_account = %(bank_account)s
          AND status != 'Reconciled'
          AND date = %(date)s
          AND ABS(debit - %(debit)s) <= 0.01
          AND ABS(credit - %(credit)s) <= 0.01
    """, {"bank_account": bank_account, "date": date, "debit": debit, "credit": credit}, as_dict=True)

    candidates = [c for c in candidates if c.name not in exclude_names]
    if len(candidates) != 1:
        return None  # none, or ambiguous — leave for manual reconciliation
    return candidates[0].name


def _auto_reconcile_bank_transaction(bt, already_linked):
    """Fallback match against a raw Payment Entry (no mirror Bank Transaction
    exists — e.g. it was made before a Bank Account/GL link existed). Only
    used when _find_existing_bank_transaction_match found nothing, since most
    Payment Entries already have their own mirror row.
    Returns the matched Payment Entry name, or None.
    """
    amount = flt(bt.debit) if flt(bt.debit) > 0 else flt(bt.credit)
    if amount <= 0:
        return None
    pe_type_pref = "Pay" if flt(bt.debit) > 0 else "Receive"

    candidates = frappe.db.sql("""
        SELECT name, payment_type, paid_amount, payment_date
        FROM `tabPayment Entry`
        WHERE docstatus = 1
          AND payment_type = %(pe_type)s
          AND payment_date = %(date)s
          AND ABS(paid_amount - %(amt)s) <= 0.01
    """, {"pe_type": pe_type_pref, "date": bt.date, "amt": amount}, as_dict=True)

    candidates = [c for c in candidates if c.name not in already_linked]
    if len(candidates) != 1:
        return None  # no match, or ambiguous — leave for manual reconciliation
    return candidates[0].name


def _suggest_account_for_description(description, bank_account):
    """Look at previously-categorized Bank Transactions (mapped_account set,
    submitted) for a similar description on this bank account, and suggest
    whatever account was used last time. Cheap keyword-ish match: exact
    description first, then a substring match on the first few words —
    good enough for recurring statement lines (e.g. 'ATM CHG', 'NEFT-XXX')
    without needing real ML/fuzzy matching.

    Filtered by bank_account, not company — Bank Transaction has no
    `company` field of its own (company is only reachable via the linked
    Bank Account), so filtering directly on "company" 500s with an unknown
    column error.
    """
    if not description:
        return None
    exact = frappe.db.get_value(
        "Bank Transaction",
        {"description": description, "bank_account": bank_account, "docstatus": 1,
         "mapped_account": ["is", "set"]},
        "mapped_account", order_by="modified desc",
    )
    if exact:
        return exact
    key = " ".join(description.split()[:2])  # first couple words, e.g. "NEFT-", "ATM"
    if not key:
        return None
    row = frappe.db.get_value(
        "Bank Transaction",
        {"description": ["like", f"%{key}%"], "bank_account": bank_account, "docstatus": 1,
         "mapped_account": ["is", "set"]},
        "mapped_account", order_by="modified desc",
    )
    return row


@frappe.whitelist(allow_guest=False, methods=["POST"])
def get_bank_statement_headers(csv_data):
    """Step 0 of import: just the header row + a few sample rows, so the
    frontend can render a column-mapper (\"which column is Date, which is
    Debit...\") before any real parsing happens. Needed because bank
    exports vary wildly — a header the guess-based parser doesn't
    recognise (e.g. a truncated \"Descriptio\" from Excel, or a bank's own
    label like \"Withdrawal Amt\") used to silently skip every row.
    """
    import csv as _csv
    from io import StringIO
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    raw_text = (csv_data or "").lstrip("\ufeff")
    reader = _csv.DictReader(StringIO(raw_text))
    headers = reader.fieldnames or []
    sample_rows = []
    for i, row in enumerate(reader):
        if i >= 3:
            break
        sample_rows.append({h: (row.get(h) or "").strip() for h in headers})
    return {"headers": headers, "sample_rows": sample_rows}


def _parse_statement_rows(csv_data, column_map=None):
    """Shared CSV parsing for preview + (legacy) direct import. Returns a
    list of dicts: date, description, reference, debit, credit — or None
    entries for unparseable rows (caller decides whether to skip/report).

    column_map, if given, is {"date": "<source header>", "description": "...",
    "reference": "...", "debit": "...", "credit": "...", "amount": "...",
    "type": "..."} — exactly which source column the person picked in the
    mapping panel for each target field. Any target left unmapped ("")
    is simply not read. When column_map is omitted entirely (legacy
    direct-import callers), falls back to the old guess-by-common-header-name
    behaviour so nothing already relying on it breaks.
    """
    import csv as _csv
    from io import StringIO
    csv_data = (csv_data or "").lstrip("\ufeff")
    reader = _csv.DictReader(StringIO(csv_data))
    cm = column_map or {}
    out = []
    for raw in reader:
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}

        def col(target, *fallback_keys):
            src = (cm.get(target) or "").strip().lower()
            if src:
                return row.get(src, "")
            if column_map is not None:
                return ""  # explicit map given but this field left unmapped — don't guess
            for fk in fallback_keys:
                v = row.get(fk)
                if v:
                    return v
            return ""

        raw_date = col("date", "date", "transaction_date", "posting_date")
        date = _parse_statement_date(raw_date)
        desc = col("description", "description", "narration", "particulars")
        ref  = col("reference", "reference", "reference_number", "ref no")
        debit  = flt(col("debit", "debit") or 0)
        credit = flt(col("credit", "credit") or 0)
        if not (debit or credit):
            amt = flt(col("amount", "amount") or 0)
            typ = (col("type", "type", "dr/cr") or "").upper()
            if typ.startswith("D"): debit = amt
            elif typ.startswith("C"): credit = amt
        out.append({
            "date": str(date) if date else None,
            "description": desc, "reference": ref,
            "debit": debit, "credit": credit,
            "valid": bool(date and (debit or credit) > 0),
        })
    return out


@frappe.whitelist(allow_guest=False, methods=["POST"])
def preview_bank_statement_csv(bank_account, csv_data, column_map=None):
    """Step 1 of the import flow: parse the file and classify every row,
    but insert/submit nothing yet. The mapping panel renders this so the
    person can review/override before anything hits the ledger.

    Each row comes back tagged with an `action`:
      - "reconcile": matches an existing mirror Bank Transaction / raw
        Payment Entry exactly (same logic as the old auto-import) — no
        account needed, just confirms a mirror row cleared.
      - "map": no match found — needs an account. `suggested_account` is
        filled in from prior categorizations of a similar description if
        one exists, otherwise null (falls back to Suspense on confirm
        unless the person picks something in the panel).
      - "skip": row couldn't be parsed (bad date / zero amount).
    """
    from zoho_books_clone.utils.access import require_module
    require_module("banking", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    if not bank_account or not frappe.db.exists("Bank Account", bank_account):
        frappe.throw("Bank Account is required")
    company = frappe.db.get_value("Bank Account", bank_account, "company")
    if not company:
        frappe.throw(f"Bank Account {bank_account} has no company set — cannot import transactions.")

    if isinstance(column_map, str) and column_map.strip():
        column_map = frappe.parse_json(column_map)
    if not column_map:
        column_map = None

    already_linked = set(frappe.db.sql_list("""
        SELECT payment_entry FROM `tabBank Transaction`
        WHERE payment_entry IS NOT NULL AND payment_entry != ''
    """))
    matched_this_batch = set()
    linked_this_batch = set()

    out = []
    for row in _parse_statement_rows(csv_data, column_map):
        if not row["valid"]:
            out.append({**row, "action": "skip"})
            continue

        existing_match = _find_existing_bank_transaction_match(
            bank_account, row["date"], row["debit"], row["credit"], matched_this_batch
        )
        if existing_match:
            matched_this_batch.add(existing_match)
            out.append({**row, "action": "reconcile", "match_name": existing_match, "match_type": "bank_transaction"})
            continue

        pe_amount = row["debit"] if row["debit"] > 0 else row["credit"]
        pe_type_pref = "Pay" if row["debit"] > 0 else "Receive"
        pe_candidates = frappe.db.sql("""
            SELECT name FROM `tabPayment Entry`
            WHERE docstatus = 1 AND payment_type = %(t)s AND payment_date = %(d)s
              AND ABS(paid_amount - %(a)s) <= 0.01
        """, {"t": pe_type_pref, "d": row["date"], "a": pe_amount}, as_dict=True)
        pe_candidates = [c.name for c in pe_candidates if c.name not in already_linked and c.name not in linked_this_batch]
        if len(pe_candidates) == 1:
            linked_this_batch.add(pe_candidates[0])
            out.append({**row, "action": "reconcile", "match_name": pe_candidates[0], "match_type": "payment_entry"})
            continue

        out.append({
            **row, "action": "map",
            "suggested_account": _suggest_account_for_description(row["description"], bank_account),
        })

    return {"rows": out, "bank_account": bank_account, "company": company}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def confirm_bank_statement_import(bank_account, rows):
    """Step 2: the person has reviewed the preview panel and (optionally)
    picked an account per unmatched row. `rows` is the list returned by
    preview_bank_statement_csv, each optionally carrying a `mapped_account`
    the person chose (or blank/omitted, which falls back to the company's
    Temporary-type suspense account on submit — see BankTransaction._post_gl).
    Only rows with action in ("reconcile", "map") are processed; "skip" rows
    are ignored here since they were already surfaced in the preview.
    """
    from zoho_books_clone.utils.access import require_module
    require_module("banking", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    if not bank_account or not frappe.db.exists("Bank Account", bank_account):
        frappe.throw("Bank Account is required")
    company = frappe.db.get_value("Bank Account", bank_account, "company")
    if not company:
        frappe.throw(f"Bank Account {bank_account} has no company set — cannot import transactions.")

    if isinstance(rows, str):
        rows = frappe.parse_json(rows)

    already_linked = set(frappe.db.sql_list("""
        SELECT payment_entry FROM `tabBank Transaction`
        WHERE payment_entry IS NOT NULL AND payment_entry != ''
    """))

    created, reconciled, mapped_to_suspense, errors = [], 0, 0, []
    for idx, row in enumerate(rows or []):
        action = row.get("action")
        bt = None
        try:
            if action == "reconcile":
                if row.get("match_type") == "bank_transaction":
                    frappe.db.set_value("Bank Transaction", row["match_name"], {"status": "Reconciled"}, update_modified=True)
                    reconciled += 1
                elif row.get("match_type") == "payment_entry" and row["match_name"] not in already_linked:
                    bt = frappe.get_doc({
                        "doctype": "Bank Transaction", "bank_account": bank_account, "company": company,
                        "date": row["date"], "description": (row.get("description") or "")[:140],
                        "debit": flt(row.get("debit")), "credit": flt(row.get("credit")),
                        "reference_number": (row.get("reference") or "")[:80],
                        "status": "Reconciled", "payment_entry": row["match_name"],
                    })
                    bt.flags.ignore_permissions = True
                    bt.flags.ignore_mandatory = True
                    bt.flags.skip_gl_posting = True  # the Payment Entry already posted the real GL
                    bt.insert(); bt.submit()
                    already_linked.add(row["match_name"])
                    reconciled += 1
            elif action == "map":
                mapped_account = (row.get("mapped_account") or "").strip() or None
                bt = frappe.get_doc({
                    "doctype": "Bank Transaction", "bank_account": bank_account, "company": company,
                    "date": row["date"], "description": (row.get("description") or "")[:140],
                    "debit": flt(row.get("debit")), "credit": flt(row.get("credit")),
                    "reference_number": (row.get("reference") or "")[:80],
                    "status": "Unreconciled", "mapped_account": mapped_account,
                })
                bt.flags.ignore_permissions = True
                bt.flags.ignore_mandatory = True
                bt.insert(); bt.submit()
                created.append(bt.name)
                if not mapped_account:
                    mapped_to_suspense += 1
        except Exception as e:
            frappe.log_error(f"Bank statement row import failed: {e}", "confirm_bank_statement_import")
            # bt.insert() may have succeeded even though bt.submit() failed
            # (e.g. no Categorize To account and no fallback Suspense
            # account) — that leaves an orphaned draft Bank Transaction
            # behind. Clean it up so retrying this row doesn't collide with
            # a stray draft, and so it doesn't quietly show up elsewhere.
            if bt is not None and getattr(bt, "name", None) and frappe.db.exists("Bank Transaction", bt.name):
                try:
                    if frappe.db.get_value("Bank Transaction", bt.name, "docstatus") == 0:
                        frappe.delete_doc("Bank Transaction", bt.name, ignore_permissions=True, force=True)
                except Exception:
                    pass
            errors.append({
                "index": idx,
                "date": row.get("date"),
                "description": row.get("description"),
                "message": str(e),
            })

    frappe.db.commit()
    return {
        "created": created, "count": len(created), "reconciled": reconciled,
        "mapped_to_suspense": mapped_to_suspense, "errors": errors, "bank_account": bank_account,
    }


@frappe.whitelist(allow_guest=False, methods=["POST"])
def import_bank_statement_csv(bank_account, csv_data):
    """Parse a CSV string (also used for Excel files converted to CSV
    client-side). CSV columns expected (case-insensitive, lenient):
    date, description, debit, credit (or amount + type=DR/CR).

    For each row:
      1. First look for an existing Unreconciled Bank Transaction on this
         account with the same date/debit/credit (the mirror auto-created
         when a Payment Entry was submitted) — if found, mark THAT row
         Reconciled. No duplicate is created.
      2. Otherwise, fall back to matching a raw Payment Entry that has no
         mirror yet.
      3. Otherwise, create a new Unreconciled Bank Transaction (a genuine
         bank-only movement — charges, interest, etc. — not yet in the books).

    Returns counts of created vs matched-and-reconciled rows.
    """
    from zoho_books_clone.utils.access import require_module
    require_module("banking", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    if not bank_account or not frappe.db.exists("Bank Account", bank_account):
        frappe.throw("Bank Account is required")

    # Bank Transaction is a financial document — central_validator.on_validate
    # requires `company` to be set, but it's never on the CSV, so it must be
    # resolved from the Bank Account itself.
    company = frappe.db.get_value("Bank Account", bank_account, "company")
    if not company:
        frappe.throw(f"Bank Account {bank_account} has no company set — cannot import transactions.")

    import csv as _csv
    from io import StringIO
    # Strip a UTF-8 BOM if present — otherwise it glues onto the first header
    # (e.g. "Date" becomes "\ufeffDate"), that column never matches row.get("date"),
    # and every row in the file gets silently skipped.
    csv_data = (csv_data or "").lstrip("\ufeff")
    reader = _csv.DictReader(StringIO(csv_data))

    # Payment Entries already linked to some Bank Transaction — never re-link these.
    already_linked = set(frappe.db.sql_list("""
        SELECT payment_entry FROM `tabBank Transaction`
        WHERE payment_entry IS NOT NULL AND payment_entry != ''
    """))
    # Existing Bank Transactions matched within this same import batch —
    # never match two statement rows onto the same existing mirror row.
    matched_this_batch = set()

    created = []
    skipped = 0
    auto_reconciled = 0
    for raw in reader:
        # Lower-case keys for tolerance
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        raw_date = row.get("date") or row.get("transaction_date") or row.get("posting_date")
        date = _parse_statement_date(raw_date)
        if not date:
            skipped += 1; continue
        desc = row.get("description") or row.get("narration") or row.get("particulars") or ""
        ref  = row.get("reference") or row.get("reference_number") or row.get("ref no") or ""
        debit  = flt(row.get("debit") or 0)
        credit = flt(row.get("credit") or 0)
        if not (debit or credit):
            # fall back to amount + type
            amt = flt(row.get("amount") or 0)
            typ = (row.get("type") or row.get("dr/cr") or "").upper()
            if typ.startswith("D"): debit = amt
            elif typ.startswith("C"): credit = amt
        if debit + credit <= 0:
            skipped += 1; continue

        try:
            # 1. Does an existing (mirror) Bank Transaction already represent
            #    this exact movement? If so, reconcile it in place — don't
            #    create a duplicate row for the same money movement.
            existing_match = _find_existing_bank_transaction_match(
                bank_account, date, debit, credit, matched_this_batch
            )
            if existing_match:
                frappe.db.set_value("Bank Transaction", existing_match, {
                    "status": "Reconciled",
                }, update_modified=True)
                matched_this_batch.add(existing_match)
                auto_reconciled += 1
                continue  # nothing new created for this row

            # 2. No mirror row — create a new Bank Transaction for this
            #    statement line (bank-only movement, or a Payment Entry made
            #    before any Bank Account/GL link existed).
            bt = frappe.get_doc({
                "doctype": "Bank Transaction",
                "bank_account": bank_account,
                "company": company,
                "date": date, "description": desc[:140],
                "debit": debit, "credit": credit,
                "reference_number": ref[:80],
                "status": "Unreconciled",
            })
            bt.flags.ignore_permissions = True
            bt.flags.ignore_mandatory = True
            bt.insert()
            bt.submit()
            created.append(bt.name)

            # 2b. Fall back to a raw Payment Entry match (no mirror existed).
            match = _auto_reconcile_bank_transaction(bt, already_linked)
            if match:
                frappe.db.set_value("Bank Transaction", bt.name, {
                    "status": "Reconciled",
                    "payment_entry": match,
                }, update_modified=True)
                already_linked.add(match)
                auto_reconciled += 1
        except Exception as e:
            frappe.log_error(f"Bank statement row import failed: {e}", "import_bank_statement_csv")
            skipped += 1
    frappe.db.commit()
    return {"created": created, "count": len(created), "skipped": skipped,
            "auto_reconciled": auto_reconciled, "bank_account": bank_account}


# ─────────────────────────────────────────────────────────────────────────────
# Standalone Delivery Note + Purchase Receipt creators (from SO/PO).
# These create real submittable documents that adjust SO/PO qty via the
# controllers' on_submit hooks. Useful when you want a printable voucher
# instead of just per-line qty tracking.
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["POST"])
def create_delivery_note_from_so(sales_order, line_qtys=None, batch_nos=None, lr_no="", transporter_name="", remarks=""):
    """Create + submit a Delivery Note from a Sales Order.
    line_qtys = {sales_order_item_row_name: qty_to_deliver}; null → all remaining.
    batch_nos = {sales_order_item_row_name: batch_no}; required for batch-tracked
    items — the Delivery Note is what actually deducts stock (via
    stock_link.on_delivery_note_submit's auto Stock Entry), so Stock Entry's
    own "Batch No is required" validation will otherwise fail the submit with
    no clear indication why. Mirrors convert_sales_order_to_invoice's batch
    handling for the direct-invoice-with-stock-deduction path.
    """
    from zoho_books_clone.utils.access import require_module
    require_module("invoices", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    if isinstance(line_qtys, str):
        try: line_qtys = json.loads(line_qtys) if line_qtys else None
        except json.JSONDecodeError: line_qtys = None
    if line_qtys:
        line_qtys = {str(k): v for k, v in line_qtys.items()}
    if isinstance(batch_nos, str):
        try: batch_nos = json.loads(batch_nos) if batch_nos else None
        except json.JSONDecodeError: batch_nos = None
    batch_nos = {str(k): v for k, v in (batch_nos or {}).items()}

    so = frappe.get_doc("Sales Order", sales_order)

    # NOTE: if this SO was already invoiced directly with update_stock=1,
    # the Sales Invoice already deducted stock and released the reservation.
    # This Delivery Note is still created/saved as a dispatch record, but
    # DeliveryNote.on_submit / stock_link.on_delivery_note_submit detect that
    # (via _stock_owned_by_invoice / a DB check) and skip touching stock or
    # reserved_qty a second time — see invoicing/doctype/delivery_note and
    # inventory/stock_link.py.

    _default_wh = frappe.db.get_single_value("Books Settings", "default_warehouse") or None
    # The Sales Order's own dispatch warehouse takes priority over the item's
    # default warehouse and the global fallback — previously this was ignored
    # entirely, so every DN silently reverted to the global default warehouse.
    so_wh = getattr(so, "set_warehouse", None) or None

    item_codes = list({it.item_code for it in (so.items or []) if it.item_code})
    batch_flags = {}
    if item_codes:
        batch_flags = {
            x["name"]: x["has_batch_no"]
            for x in frappe.get_all("Item", filters={"name": ["in", item_codes]},
                                    fields=["name", "has_batch_no"])
        }

    dn_items = []
    for it in (so.items or []):
        remaining = max(0.0, flt(it.qty) - flt(it.delivered_qty))
        if remaining <= 0: continue
        if line_qtys:
            q = min(flt(line_qtys.get(str(it.name), 0)), remaining)
        else:
            q = remaining
        if q <= 0: continue
        # SO Item child rows use autoincrement names — coerce robustly.
        try:
            so_item_id = int(it.name)
        except (TypeError, ValueError):
            so_item_id = 0
        item_wh = so_wh or frappe.db.get_value("Item", it.item_code, "default_warehouse") or _default_wh

        # Delivery Note is what actually deducts stock (stock_link.py's auto
        # Stock Entry) — batch-tracked items MUST carry a batch here, or the
        # auto Stock Entry's own submit fails with "Batch No is required"
        # and rolls back the whole Delivery Note with no clear error.
        batch_no = ""
        if batch_flags.get(it.item_code):
            batch_no = (batch_nos.get(str(it.name)) or "").strip()
            if not batch_no:
                frappe.throw(_(
                    "Row #{0}: {1} is a batch-tracked item - select a Batch No before delivering"
                ).format(it.idx, it.item_name or it.item_code))

        dn_items.append({
            "doctype": "Delivery Note Item",
            "item_code":   it.item_code,
            "item_name":   it.item_name or it.item_code,
            "description": it.description or it.item_name or it.item_code,
            "qty":         q,
            "uom":         getattr(it, "uom", "") or "Nos",
            "rate":        flt(it.rate),
            "amount":      flt(it.rate) * q,
            "so_item":     so_item_id,
            "warehouse":   item_wh or "",
            "batch_no":    batch_no,
        })
    if not dn_items:
        frappe.throw("Nothing left to deliver on this Sales Order")

    dn = frappe.get_doc({
        "doctype": "Delivery Note",
        "company":          so.company,
        "customer":         so.customer,
        "customer_name":    so.customer_name,
        "posting_date":     today(),
        "sales_order":      so.name,
        "delivery_date":    so.delivery_date or today(),
        "lr_no":            lr_no or "",
        "transporter_name": transporter_name or "",
        "remarks":          remarks or "",
        "set_warehouse":    so_wh or _default_wh or "",
        "shipping_address":      getattr(so, "shipping_address", "") or "",
        "shipping_address_name": getattr(so, "shipping_address_name", "") or "",
        "billing_address":       getattr(so, "billing_address", "") or "",
        "billing_address_name":  getattr(so, "billing_address_name", "") or "",
        "items":            dn_items,
    })
    dn.flags.ignore_permissions = True
    dn.flags.ignore_mandatory = True
    dn.insert()
    dn.submit()
    frappe.db.commit()
    return {"delivery_note": dn.name, "sales_order": sales_order,
            "total_qty": dn.total_qty}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def create_purchase_receipt_from_po(purchase_order, line_qtys=None, supplier_delivery_note="", remarks=""):
    """Create + submit a Purchase Receipt from a Purchase Order."""
    from zoho_books_clone.utils.access import require_module
    require_module("bills", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    if isinstance(line_qtys, str):
        try: line_qtys = json.loads(line_qtys) if line_qtys else None
        except json.JSONDecodeError: line_qtys = None
    if line_qtys:
        line_qtys = {str(k): v for k, v in line_qtys.items()}

    po = frappe.get_doc("Purchase Order", purchase_order)
    _default_wh = frappe.db.get_single_value("Books Settings", "default_warehouse") or None
    pr_items = []
    for it in (po.items or []):
        remaining = max(0.0, flt(it.qty) - flt(it.received_qty))
        if remaining <= 0: continue
        if line_qtys:
            q = min(flt(line_qtys.get(str(it.name), 0)), remaining)
        else:
            q = remaining
        if q <= 0: continue
        item_wh = frappe.db.get_value("Item", it.item_code, "default_warehouse") or _default_wh
        pr_items.append({
            "doctype": "Purchase Receipt Item",
            "item_code":   it.item_code,
            "item_name":   it.item_name or it.item_code,
            "description": it.description or it.item_name or it.item_code,
            "qty":         q,
            "uom":         getattr(it, "uom", "") or "Nos",
            "rate":        flt(it.rate),
            "amount":      flt(it.rate) * q,
            "po_item":     int(it.name) if str(it.name).isdigit() else 0,
            "warehouse":   item_wh or "",
        })
    if not pr_items:
        frappe.throw("Nothing left to receive on this Purchase Order")

    pr = frappe.get_doc({
        "doctype": "Purchase Receipt",
        "company":                  po.company,
        "supplier":                 po.supplier,
        "supplier_name":            po.supplier_name,
        "posting_date":             today(),
        "purchase_order":           po.name,
        "supplier_delivery_note":   supplier_delivery_note or "",
        "remarks":                  remarks or "",
        "set_warehouse":            _default_wh or "",
        "items":                    pr_items,
    })
    pr.flags.ignore_permissions = True
    pr.flags.ignore_mandatory = True
    pr.insert()
    pr.submit()
    frappe.db.commit()
    return {"purchase_receipt": pr.name, "purchase_order": purchase_order,
            "total_qty": pr.total_qty}


# ─────────────────────────────────────────────────────────────────────────────
# Tier 3 — Logistics: derived Delivery Challan & Purchase Receipt views.
# Neither doctype exists in this build, so we synthesise the lists from
# Sales Order Item.delivered_qty and Purchase Order Item.received_qty.
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_delivery_challan_list(company=None, limit=200):
    """List Delivery Notes (real submittable docs) + any SOs with delivered_qty
    that don't yet have a DN (derived fallback). Real DNs are shown first.
    """
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    company = company or _get_company(frappe.session.user)

    # 1) Real Delivery Notes
    dns = frappe.db.sql("""
        SELECT name, customer, customer_name, posting_date, delivery_date,
               sales_order, status, total_qty, lr_no, transporter_name,
               docstatus, 'real' AS source
        FROM `tabDelivery Note`
        WHERE company = %(co)s
        ORDER BY posting_date DESC, creation DESC
        LIMIT %(lim)s
    """, {"co": company, "lim": int(limit)}, as_dict=True)
    # Map fields to the legacy template shape
    out = []
    sos_with_dn = set()
    for d in dns:
        if d.sales_order: sos_with_dn.add(d.sales_order)
        out.append({
            "name":          d.name,
            "sales_order":   d.sales_order or "",
            "customer":      d.customer, "customer_name": d.customer_name,
            "posting_date":  d.posting_date,
            "delivery_date": d.delivery_date or d.posting_date,
            "lr_no":         d.lr_no, "transporter_name": d.transporter_name,
            "status":        d.status or ("Cancelled" if d.docstatus == 2 else "Submitted"),
            "challan_status": "Cancelled" if d.docstatus == 2 else "Submitted",
            "qty_delivered": flt(d.total_qty),
            "qty_ordered":   flt(d.total_qty),
            "pct_delivered": 100.0,
            "docstatus":     d.docstatus,
            "source":        "real",
        })

    # 2) Derived rows for SOs that have delivered_qty but no DN yet
    rows = frappe.db.sql("""
        SELECT
            so.name AS sales_order,
            so.customer, so.customer_name,
            so.transaction_date, so.delivery_date, so.status,
            so.grand_total,
            SUM(soi.qty)            AS qty_ordered,
            SUM(soi.delivered_qty)  AS qty_delivered,
            SUM(soi.billed_qty)     AS qty_billed
        FROM `tabSales Order` so
        JOIN `tabSales Order Item` soi ON soi.parent = so.name
        WHERE so.company = %(co)s
          AND so.status NOT IN ('Cancelled', 'Draft')
        GROUP BY so.name
        HAVING SUM(soi.delivered_qty) > 0
        ORDER BY so.transaction_date DESC
        LIMIT %(lim)s
    """, {"co": company, "lim": int(limit)}, as_dict=True)
    for r in rows:
        if r.sales_order in sos_with_dn:
            continue   # already have a real DN for this SO
        ordered = flt(r.qty_ordered); delivered = flt(r.qty_delivered)
        r["name"]            = r.sales_order   # legacy template uses .name
        r["challan_status"]  = (
            "Cancelled"           if r.status == "Cancelled" else
            "Fully Delivered"     if delivered >= ordered - 0.001 else
            "Partially Delivered"
        )
        r["pct_delivered"]   = round(100 * delivered / ordered, 1) if ordered else 0
        r["source"]          = "derived"
        r["docstatus"]       = 2 if r.status == "Cancelled" else 1
        out.append(r)
    return out[:int(limit)]


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_delivery_challan_lines(sales_order):
    """Per-line delivery detail for a Sales Order (used by the DC view drawer)."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    rows = frappe.get_all("Sales Order Item",
        filters={"parent": sales_order, "delivered_qty": [">", 0]},
        fields=["name", "item_code", "item_name", "description",
                "qty", "uom", "rate", "amount", "delivered_qty", "billed_qty"],
        order_by="idx asc")
    return rows


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_purchase_receipt_list(company=None, limit=200):
    """List Purchase Receipts (real submittable docs) + any POs with received_qty
    that don't yet have a PR (derived fallback)."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    company = company or _get_company(frappe.session.user)

    # 1) Real Purchase Receipts
    prs = frappe.db.sql("""
        SELECT name, supplier, supplier_name, posting_date, purchase_order,
               status, total_qty, supplier_delivery_note, docstatus
        FROM `tabPurchase Receipt`
        WHERE company = %(co)s
        ORDER BY posting_date DESC, creation DESC
        LIMIT %(lim)s
    """, {"co": company, "lim": int(limit)}, as_dict=True)
    out = []
    pos_with_pr = set()
    for p in prs:
        if p.purchase_order: pos_with_pr.add(p.purchase_order)
        out.append({
            "name":                  p.name,
            "purchase_order":        p.purchase_order or "",
            "supplier":              p.supplier, "supplier_name": p.supplier_name,
            "posting_date":          p.posting_date,
            "supplier_delivery_note":p.supplier_delivery_note,
            "status":                p.status or ("Cancelled" if p.docstatus == 2 else ("Draft" if p.docstatus == 0 else "Submitted")),
            "receipt_status":        "Cancelled" if p.docstatus == 2 else ("Draft" if p.docstatus == 0 else "Submitted"),
            "qty_received":          flt(p.total_qty),
            "qty_ordered":           flt(p.total_qty),
            "pct_received":          100.0 if p.docstatus == 1 else 0.0,
            "docstatus":             p.docstatus,
            "source":                "real",
        })

    # 2) Derived rows for POs without a real PR
    rows = frappe.db.sql("""
        SELECT
            po.name AS purchase_order,
            po.supplier, po.supplier_name,
            po.transaction_date, po.expected_delivery_date, po.status,
            po.grand_total,
            SUM(poi.qty)           AS qty_ordered,
            SUM(poi.received_qty)  AS qty_received,
            SUM(poi.billed_qty)    AS qty_billed
        FROM `tabPurchase Order` po
        JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
        WHERE po.company = %(co)s
          AND po.status NOT IN ('Cancelled', 'Draft')
        GROUP BY po.name
        HAVING SUM(poi.received_qty) > 0
        ORDER BY po.transaction_date DESC
        LIMIT %(lim)s
    """, {"co": company, "lim": int(limit)}, as_dict=True)
    for r in rows:
        if r.purchase_order in pos_with_pr:
            continue
        ordered = flt(r.qty_ordered); received = flt(r.qty_received)
        r["name"]           = r.purchase_order
        r["receipt_status"] = (
            "Cancelled"          if r.status == "Cancelled" else
            "Fully Received"     if received >= ordered - 0.001 else
            "Partially Received"
        )
        r["pct_received"]   = round(100 * received / ordered, 1) if ordered else 0
        r["source"]         = "derived"
        r["docstatus"]      = 2 if r.status == "Cancelled" else 1
        out.append(r)
    return out[:int(limit)]


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_purchase_receipt_lines(purchase_order):
    """Per-line receipt detail for a Purchase Order."""
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    rows = frappe.get_all("Purchase Order Item",
        filters={"parent": purchase_order, "received_qty": [">", 0]},
        fields=["name", "item_code", "item_name", "description",
                "qty", "uom", "rate", "amount", "received_qty", "billed_qty"],
        order_by="idx asc")
    return rows


@frappe.whitelist(allow_guest=False, methods=["POST"])
def bulk_set_customer_disabled(customer_names, disabled):
    from zoho_books_clone.utils.access import require_module
    require_module("customers", write=True)
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    if isinstance(customer_names, str):
        customer_names = json.loads(customer_names)
    disabled = int(disabled)
    done = 0
    for c in (customer_names or []):
        try:
            frappe.db.set_value("Customer", c, "disabled", disabled, update_modified=True)
            done += 1
        except Exception:
            pass
    frappe.db.commit()
    return {"updated": done, "disabled": disabled}


@frappe.whitelist(allow_guest=False)
def get_accounts():
    """Safely fetch accounts filtered by company, bypassing REST get_list overrides."""
    company = frappe.form_dict.get("company") or ""

    # Resolve company from Books Settings when not supplied by caller
    if not company:
        company = _get_company(frappe.session.user)

    def get_list_by_type(account_type=None, scope_company=None):
        """Return leaf accounts matching the given type.

        scope_company controls company filtering:
          - truthy str  → filter by that company
          - ""          → no company filter (global fallback)
          - None        → use the outer `company` variable
        """
        effective = company if scope_company is None else scope_company
        f = {"is_group": 0, "disabled": 0}
        if effective:
            f["company"] = effective
        if account_type:
            f["account_type"] = account_type
        try:
            return [
                {"name": a.name, "account_type": a.account_type}
                for a in frappe.get_all("Account", filters=f, fields=["name", "account_type"])
            ]
        except Exception:
            return []

    # Primary query — scoped to the resolved company
    res = {
        "ar":     get_list_by_type(account_type="Receivable"),
        "income": get_list_by_type(account_type="Income"),
        "bank":   get_list_by_type(account_type=["in", ["Bank", "Cash"]]),
        "ap":     get_list_by_type(account_type="Payable"),
    }

    # Fallback 1: category empty → try all accounts for the same company (no type filter)
    all_accs = None
    for key in res:
        if not res[key]:
            if all_accs is None:
                all_accs = get_list_by_type()
            res[key] = all_accs

    # Fallback 2: if the company itself had no accounts (stale/wrong company name),
    # retry the entire query without any company filter so the UI is never blank.
    if not any(res.values()):
        res = {
            "ar":     get_list_by_type(account_type="Receivable", scope_company=""),
            "income": get_list_by_type(account_type="Income",      scope_company=""),
            "bank":   get_list_by_type(account_type=["in", ["Bank", "Cash"]], scope_company=""),
            "ap":     get_list_by_type(account_type="Payable",     scope_company=""),
        }
        all_global = None
        for key in res:
            if not res[key]:
                if all_global is None:
                    all_global = get_list_by_type(scope_company="")
                res[key] = all_global

    return res


# ─────────────────────────────────────────────────────────────────────────────
# Write-off & Refund helpers
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["POST"])
def write_off_credit_note(credit_note_name, write_off_account=None):
    """Write off the remaining balance on a Credit Note via Journal Entry.

    The CN sits as a credit balance on AR (the customer is owed); the write-off
    debits AR (referencing the CN, so it counts as applied) and credits the
    write-off/expense account.
    """
    from zoho_books_clone.utils.access import require_module
    require_module("invoices", write=True)
    company = _get_company(frappe.session.user)
    cn = frappe.get_doc("Sales Invoice", credit_note_name)
    if cn.docstatus != 1:
        frappe.throw("Credit note must be submitted before writing off")

    bal_data = get_credit_note_balance(credit_note_name)
    balance = flt(bal_data.get("balance", 0))
    if balance <= 0:
        frappe.throw("No outstanding balance to write off")

    ar_account = cn.debit_to or frappe.db.get_value(
        "Account", {"account_type": "Receivable", "company": company, "is_group": 0}, "name"
    )
    if not write_off_account:
        write_off_account = (
            frappe.db.get_value("Account", {"account_type": "Write Off", "company": company, "is_group": 0}, "name")
            or frappe.db.get_value("Account", {"account_type": "Expense", "company": company, "is_group": 0}, "name")
        )
    if not write_off_account:
        frappe.throw("No write-off or expense account found for the company")

    je = frappe.get_doc({
        "doctype": "Journal Entry",
        "naming_series": "JV-.YYYY.-",
        "company": company,
        "posting_date": today(),
        "voucher_type": "Journal Entry",
        "remark": f"Write off remaining balance on Credit Note {credit_note_name}",
        "accounts": [
            {
                "account": ar_account,
                "debit": balance,
                "credit": 0,
                "party_type": "Customer",
                "party": cn.customer,
                "reference_type": "Sales Invoice",
                "reference_name": credit_note_name,
            },
            {
                "account": write_off_account,
                "debit": 0,
                "credit": balance,
            },
        ],
    })
    je.flags.ignore_permissions = True
    je.insert()
    je.submit()
    frappe.db.commit()
    return {"journal_entry": je.name}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def refund_debit_note(debit_note_name, amount, refund_mode="Bank Transfer", reference_no=""):
    """Receive a cash refund from the vendor against a Debit Note balance.

    The DN sits as a debit balance on AP; the refund debits Cash/Bank and
    credits AP (referencing the DN, so it counts as applied).
    """
    from zoho_books_clone.utils.access import require_module
    require_module("bills", write=True)
    company = _get_company(frappe.session.user)
    dn = frappe.get_doc("Purchase Invoice", debit_note_name)
    if dn.docstatus != 1:
        frappe.throw("Debit note must be submitted before processing a refund")

    amount = flt(amount)
    if amount <= 0:
        frappe.throw("Refund amount must be greater than 0")

    ap_account = dn.credit_to or frappe.db.get_value(
        "Account", {"account_type": "Payable", "company": company, "is_group": 0}, "name"
    )
    account_type = "Cash" if refund_mode == "Cash" else "Bank"
    cash_bank_account = frappe.db.get_value(
        "Account", {"account_type": account_type, "company": company, "is_group": 0}, "name"
    ) or frappe.db.get_value(
        "Account", {"account_type": ["in", ["Bank", "Cash"]], "company": company, "is_group": 0}, "name"
    )
    if not cash_bank_account:
        frappe.throw(f"No {account_type} account found for the company")

    je = frappe.get_doc({
        "doctype": "Journal Entry",
        "naming_series": "JV-.YYYY.-",
        "company": company,
        "posting_date": today(),
        "voucher_type": "Cash Entry" if refund_mode == "Cash" else "Bank Entry",
        "remark": f"Refund received from vendor against Debit Note {debit_note_name}"
                  + (f" — Ref: {reference_no}" if reference_no else ""),
        "accounts": [
            {
                "account": cash_bank_account,
                "debit": amount,
                "credit": 0,
            },
            {
                "account": ap_account,
                "debit": 0,
                "credit": amount,
                "party_type": "Supplier",
                "party": dn.supplier,
                "reference_type": "Purchase Invoice",
                "reference_name": debit_note_name,
            },
        ],
    })
    je.flags.ignore_permissions = True
    je.insert()
    je.submit()
    frappe.db.commit()
    return {"journal_entry": je.name}