from __future__ import annotations
"""
Asset capitalization GL — Phase 1+2 of the asset-management accounting build-out.

Phase 1 (schema): Asset Category now carries a child table (`accounts`,
Asset Category Account) mapping each Company to its Fixed Asset /
Accumulated Depreciation / Depreciation Expense / CWIP accounts — the same
"account defaults live on the category, keyed by company" shape ERPNext
uses, and consistent with this app's own per-company default pattern
(Books Company.default_inventory_account etc. in accounts/inventory_gl.py).

Phase 2 (this file): on Asset submit, post a capitalization entry —

    DR Fixed Asset Account (from the asset's category+company)
    DR GST Input Account (per Asset Tax Detail row, only for rows with
                           is_itc_eligible checked — see below)
    CR Asset.credit_account (Payable, for a supplier-billed purchase, or
                              Bank/Cash, for a cash purchase)

for `purchase_cost` (+ any ITC-eligible tax). Non-ITC-eligible tax is not
a separate GL line here — Asset.calculate_totals() already folds it into
`purchase_cost`, so it rides along on the Fixed Asset/CWIP debit like any
other blocked-credit cost. ITC-eligible tax lines (Asset Tax Detail rows
with is_itc_eligible checked) debit a GST Input account instead — either
the row's own `account_head` override, or the category's default
`gst_input_account` — since that portion is a recoverable input credit,
not part of the asset's book value. validate_capitalization_setup()
requires gst_input_account to be configured whenever eligible tax is
present. On cancel, reverse it via the same
general_ledger_entry.make_gl_entries(cancel=True) path every other
financial doctype in this app uses (Sales/Purchase Invoice, Landed Cost
Voucher, Stock Entry) — entries are reversed, not deleted, preserving the
audit trail.

Not yet covered (left for a later phase, deliberately — see chat plan):
  - Linking to Purchase Invoice's own GL (no "Is Fixed Asset" line flag
    exists yet on Purchase Invoice) — this posts a self-contained entry
    instead, so `credit_account` must be picked explicitly, the same way
    Purchase Invoice requires an explicit `credit_to`.
  - Disposal/scrap/sale GL.

CWIP (capitalize to CWIP first, move to Fixed Asset on "available for
use") — implemented below, adapted from how ERPNext handles it. ERPNext
triggers CWIP off Purchase Receipt/Invoice for a fixed-asset item; this
app has no such integration, so the same two-step pattern is triggered
off Asset submit instead:

  - On Asset submit, if the category+company has a cwip_account
    configured AND available_for_use_date is later than purchase_date
    (i.e. the asset isn't ready for use yet), capitalization posts to
    CWIP instead of Fixed Asset: DR CWIP Account / CR credit_account.
    `cwip_transferred` is left 0.
  - Once available_for_use_date arrives, assets/cwip_posting.py's daily
    scheduled job transfers it: DR Fixed Asset Account / CR CWIP
    Account, for the same purchase_cost, and sets cwip_transferred = 1.
  - If no cwip_account is configured for the category+company, or
    available_for_use_date is not later than purchase_date, capitalization
    posts straight to Fixed Asset as before (cwip_transferred defaults to
    1 -- "nothing left to transfer").
  - On cancel, both legs are reversed if both were posted (see
    reverse_asset_capitalization below).

Phase 3 (assets/depreciation_engine.py + assets/depreciation_posting.py):
  periodic depreciation postings (DR Depreciation Expense / CR Accumulated
  Depreciation) now exist as their own modules rather than living here —
  depreciation posts per Depreciation Schedule row on a schedule, not once
  on Asset submit like capitalization does, so it needs its own scheduled
  job and idempotency handling. get_category_accounts() below is reused
  by depreciation_posting.py rather than duplicated.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate

from zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry import (
    make_gl_entries,
)

_VOUCHER_TYPE = "Asset"
_CWIP_VOUCHER_TYPE = "Asset CWIP Transfer"


def _cwip_voucher_no(asset_name: str) -> str:
    return f"{asset_name}-CWIP"


def _needs_cwip(doc, accounts: dict) -> bool:
    """True if this asset should capitalize to CWIP rather than straight
    to Fixed Asset: the category+company has a CWIP account configured,
    and the asset isn't ready for use as of its purchase date."""
    if not accounts.get("cwip_account"):
        return False
    if not doc.available_for_use_date or not doc.purchase_date:
        return False
    return getdate(doc.available_for_use_date) > getdate(doc.purchase_date)


def get_category_accounts(asset_category: str, company: str) -> dict:
    """Fixed Asset / Accumulated Depreciation / Depreciation Expense / CWIP
    accounts configured for this category+company. Empty dict if the
    category has no row set up for that company yet."""
    if not asset_category or not company:
        return {}
    row = frappe.db.get_value(
        "Asset Category Account",
        {"parenttype": "Asset Category", "parent": asset_category, "company": company},
        [
            "fixed_asset_account",
            "accumulated_depreciation_account",
            "depreciation_expense_account",
            "cwip_account",
            "gst_input_account",
        ],
        as_dict=True,
    )
    return row or {}


def _validate_account_ref(account: str, company: str, label: str) -> None:
    """Verify `account` is a real, usable Account for `company`. Raises a
    friendly frappe.throw for any problem, instead of letting a bad/stale
    account name reach make_gl_entries() and fail as a raw DB error at
    submit time (foreign key / constraint failure surfacing as an opaque
    OperationalError with no actionable message)."""
    row = frappe.db.get_value(
        "Account", account, ["company", "is_group", "disabled"], as_dict=True
    )
    if not row:
        frappe.throw(
            _("{0} {1} does not exist. Check the account configured under "
              "Asset Category \u2192 Accounting (per Company).").format(
                label, frappe.bold(account)
            )
        )
    if row.company != company:
        frappe.throw(
            _("{0} {1} belongs to company {2}, not {3}. Fix the account "
              "configured under Asset Category \u2192 Accounting (per Company).").format(
                label, frappe.bold(account), frappe.bold(row.company), frappe.bold(company)
            )
        )
    if row.is_group:
        frappe.throw(
            _("{0} {1} is a group account and cannot be posted to directly. "
              "Pick a leaf account instead.").format(label, frappe.bold(account))
        )
    if row.disabled:
        frappe.throw(
            _("{0} {1} is disabled and cannot be posted to.").format(label, frappe.bold(account))
        )


def validate_capitalization_setup(doc) -> None:
    """Called from Asset.validate() so the person finds out about missing
    setup while still editing, not only at submit time."""
    if doc.is_existing_asset:
        return

    if not doc.company:
        frappe.throw(_("Company is required before this asset can be submitted."))

    accounts = get_category_accounts(doc.asset_category, doc.company)
    if not accounts.get("fixed_asset_account"):
        frappe.throw(
            _(
                "Asset Category {0} has no Fixed Asset Account configured for company {1}. "
                "Add a row under Asset Category \u2192 Accounting (per Company) first."
            ).format(frappe.bold(doc.asset_category), frappe.bold(doc.company))
        )
    _validate_account_ref(accounts["fixed_asset_account"], doc.company, "Fixed Asset Account")

    if accounts.get("cwip_account"):
        _validate_account_ref(accounts["cwip_account"], doc.company, "CWIP Account")

    eligible_tax = sum(
        flt(row.amount) for row in (doc.taxes or []) if row.is_itc_eligible
    )
    if eligible_tax:
        if not accounts.get("gst_input_account"):
            frappe.throw(
                _(
                    "Asset Category {0} has no GST Input Account configured for company {1}, "
                    "but this asset has ITC-eligible tax lines. Add a GST Input Account under "
                    "Asset Category \u2192 Accounting (per Company), or uncheck ITC Eligible "
                    "on the relevant tax row(s) if this credit is actually blocked."
                ).format(frappe.bold(doc.asset_category), frappe.bold(doc.company))
            )
        _validate_account_ref(accounts["gst_input_account"], doc.company, "GST Input Account")

    if not doc.credit_account:
        frappe.throw(
            _("Credit Account (Payable / Bank / Cash) is required to capitalize this asset.")
        )
    _validate_account_ref(doc.credit_account, doc.company, "Credit Account")


def post_asset_capitalization(doc) -> None:
    """DR Fixed Asset Account / CR doc.credit_account for purchase_cost.
    Skipped for existing/opening assets (already reflected in the books
    elsewhere) and for a second submit-attempt if already posted."""
    if doc.is_existing_asset:
        return
    if doc.capitalization_posted:
        return

    validate_capitalization_setup(doc)

    amount = flt(doc.purchase_cost)
    if amount <= 0:
        frappe.throw(_("Purchase Cost must be greater than zero to capitalize this asset."))

    accounts = get_category_accounts(doc.asset_category, doc.company)
    fixed_asset_account = accounts.get("fixed_asset_account")
    goes_to_cwip = _needs_cwip(doc, accounts)
    debit_account = accounts.get("cwip_account") if goes_to_cwip else fixed_asset_account

    remarks = f"Asset capitalized \u2014 {doc.asset_name} ({doc.name})" + (
        " (to CWIP)" if goes_to_cwip else ""
    )

    # ITC-eligible tax lines each debit a GST input account — the row's own
    # account_head override if set, else the category's default
    # gst_input_account (validate_capitalization_setup already confirmed
    # this exists when eligible tax is present). Grouped by account so two
    # rows pointing at the same account net into a single GL line.
    itc_by_account: dict[str, float] = {}
    for row in (doc.taxes or []):
        if not row.is_itc_eligible or not flt(row.amount):
            continue
        acct = row.account_head or accounts.get("gst_input_account")
        itc_by_account[acct] = itc_by_account.get(acct, 0) + flt(row.amount)
    total_itc = sum(itc_by_account.values())

    gl_map = [
        {
            "account": debit_account,
            "debit": amount,
            "credit": 0,
            "voucher_type": _VOUCHER_TYPE,
            "voucher_no": doc.name,
            "posting_date": doc.purchase_date,
            "company": doc.company,
            "remarks": remarks,
        },
    ]
    for acct, tax_amount in itc_by_account.items():
        gl_map.append(
            {
                "account": acct,
                "debit": round(tax_amount, 2),
                "credit": 0,
                "voucher_type": _VOUCHER_TYPE,
                "voucher_no": doc.name,
                "posting_date": doc.purchase_date,
                "company": doc.company,
                "remarks": f"{remarks} (Input GST)",
            }
        )
    gl_map.append(
        {
            "account": doc.credit_account,
            "debit": 0,
            "credit": round(amount + total_itc, 2),
            "voucher_type": _VOUCHER_TYPE,
            "voucher_no": doc.name,
            "posting_date": doc.purchase_date,
            "company": doc.company,
            "remarks": remarks,
        }
    )

    make_gl_entries(gl_map)
    doc.db_set("capitalization_posted", 1, update_modified=False)
    doc.db_set("cwip_transferred", 0 if goes_to_cwip else 1, update_modified=False)


def transfer_cwip_to_fixed_asset(asset_name: str) -> bool:
    """DR Fixed Asset Account / CR CWIP Account for purchase_cost, once
    available_for_use_date has arrived. Called by assets/cwip_posting.py's
    daily job; also safe to call directly/manually. Returns True if a
    transfer was posted, False if there was nothing due."""
    doc = frappe.get_doc("Asset", asset_name)

    if not doc.capitalization_posted or doc.cwip_transferred:
        return False
    if not doc.available_for_use_date or getdate(doc.available_for_use_date) > getdate(frappe.utils.nowdate()):
        return False

    accounts = get_category_accounts(doc.asset_category, doc.company)
    fixed_asset_account = accounts.get("fixed_asset_account")
    cwip_account = accounts.get("cwip_account")
    if not fixed_asset_account or not cwip_account:
        frappe.log_error(
            f"Asset {asset_name} is due for CWIP transfer but its category+company "
            f"is missing Fixed Asset Account and/or CWIP Account.",
            "CWIP transfer: missing account setup",
        )
        return False

    amount = flt(doc.purchase_cost)
    remarks = f"CWIP transfer \u2014 {doc.asset_name} ({doc.name})"
    gl_map = [
        {
            "account": fixed_asset_account,
            "debit": amount,
            "credit": 0,
            "voucher_type": _CWIP_VOUCHER_TYPE,
            "voucher_no": _cwip_voucher_no(doc.name),
            "posting_date": doc.available_for_use_date,
            "company": doc.company,
            "remarks": remarks,
        },
        {
            "account": cwip_account,
            "debit": 0,
            "credit": amount,
            "voucher_type": _CWIP_VOUCHER_TYPE,
            "voucher_no": _cwip_voucher_no(doc.name),
            "posting_date": doc.available_for_use_date,
            "company": doc.company,
            "remarks": remarks,
        },
    ]
    make_gl_entries(gl_map)
    doc.db_set("cwip_transferred", 1, update_modified=False)
    return True


def reverse_asset_capitalization(doc) -> None:
    """Best-effort reversal on cancel — mirrors Landed Cost Voucher /
    Stock Entry: never block the cancel itself on a GL-side failure.
    Reverses the CWIP transfer leg too, if one was posted, before the
    original capitalization leg."""
    if not doc.capitalization_posted:
        return
    try:
        if doc.cwip_transferred:
            make_gl_entries(
                [{"voucher_type": _CWIP_VOUCHER_TYPE, "voucher_no": _cwip_voucher_no(doc.name)}],
                cancel=True,
            )
        make_gl_entries(
            [{"voucher_type": _VOUCHER_TYPE, "voucher_no": doc.name}],
            cancel=True,
        )
        doc.db_set("capitalization_posted", 0, update_modified=False)
        doc.db_set("cwip_transferred", 0, update_modified=False)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Asset capitalization GL reversal failed")