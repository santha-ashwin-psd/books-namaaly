"""
Cross-doctype validation helpers.
Called from DocType controllers before saving/submitting.
"""
import frappe
from frappe import _
from frappe.utils import getdate, nowtime


def set_posting_time(doc) -> None:
    """
    ERPNext-style posting_time auto-stamping (Phase 2 of the posting_time
    rollout — see the posting_date/posting_time field pair added in Phase 1).

    Call this at the top of validate() for any doctype carrying the
    set_posting_time / posting_time field pair.

    - set_posting_time unchecked (default): posting_time is force-stamped
      with the current time on every save, so it always reflects when the
      document was actually saved and can't be hand-edited while the
      checkbox is off.
    - set_posting_time checked: the user-entered posting_time is left as-is,
      allowing backdated entries with a specific time. If left blank while
      checked, falls back to the current time so a blank value never reaches
      GL Entry / Stock Ledger Entry ordering.
    """
    if not doc.get("set_posting_time"):
        doc.posting_time = nowtime()
    elif not doc.posting_time:
        doc.posting_time = nowtime()


def validate_fiscal_year(posting_date: str, company: str) -> str:
    """
    Return fiscal year name for the given posting date + company.
    Throws if:
      - no open fiscal year covers the date, OR
      - the posting_date falls on or before the period lock_date (P1/Issue 6)
    """
    fy = frappe.db.sql("""
        SELECT name, lock_date FROM `tabFiscal Year`
        WHERE (LOWER(company) = LOWER(%(company)s) OR company IS NULL OR company = '')
          AND is_closed         = 0
          AND year_start_date  <= %(date)s
          AND year_end_date    >= %(date)s
        ORDER BY (company IS NULL OR company = '') ASC
        LIMIT 1
    """, {"company": company, "date": posting_date}, as_dict=True)

    if not fy:
        frappe.throw(
            _("No open Fiscal Year found for date {0} in company {1}").format(
                posting_date, company
            )
        )

    # Fiscal Year period lock check
    lock_date = fy[0].get("lock_date")
    if lock_date and getdate(posting_date) <= getdate(lock_date):
        frappe.throw(_(
            "Posting date {0} is on or before the period lock date {1}. "
            "Remove the lock date on the Fiscal Year to post to this period."
        ).format(posting_date, lock_date))

    # Per-company Books Lock Date check — reads from Books Company, not the global Books Settings
    try:
        books_lock = frappe.db.get_value("Books Company", company, "lock_date")
        if books_lock and getdate(posting_date) <= getdate(books_lock):
            frappe.throw(_(
                "The period up to {0} is locked. You cannot post to a date on or before "
                "the Books Lock Date. Contact your System Manager to unlock the period."
            ).format(books_lock))
    except frappe.ValidationError:
        raise
    except Exception:
        pass  # Books Company may not exist during install

    return fy[0].name


def validate_account_company(account: str, company: str) -> None:
    """Ensure an account belongs to the given company (case-insensitive)."""
    acc_company = frappe.db.get_value("Account", account, "company")
    if acc_company and acc_company.lower() != (company or "").lower():
        frappe.throw(
            _("Account {0} belongs to company {1}, not {2}").format(account, acc_company, company)
        )


def validate_account_type(account: str, expected_types: list[str]) -> None:
    """Ensure an account is one of the expected types."""
    acc_type = frappe.db.get_value("Account", account, "account_type")
    if acc_type not in expected_types:
        frappe.throw(
            _("Account {0} must be of type {1}, found {2}").format(
                account, "/".join(expected_types), acc_type
            )
        )


def validate_no_future_date(date_str: str, field_label: str) -> None:
    """Prevent future posting dates (configurable — enable in Books Settings)."""
    allow_future = frappe.db.get_single_value("Books Settings", "allow_future_dates")
    if not allow_future and getdate(date_str) > getdate():
        frappe.throw(_("{0} cannot be a future date").format(field_label))


def validate_duplicate_bill(supplier: str, bill_no: str, bill_date: str) -> None:
    """Prevent duplicate purchase invoices for the same supplier bill number."""
    if not bill_no:
        return
    existing = frappe.db.get_value(
        "Purchase Invoice",
        {"supplier": supplier, "bill_no": bill_no, "bill_date": bill_date, "docstatus": ["!=", 2]},
        "name",
    )
    if existing:
        frappe.throw(
            _("Duplicate bill: invoice {0} already recorded for supplier {1} with bill no {2}").format(
                existing, supplier, bill_no
            )
        )