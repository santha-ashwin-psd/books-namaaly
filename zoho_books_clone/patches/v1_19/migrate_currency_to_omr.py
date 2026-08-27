"""
Patch v1_19: seed OMR into the Currency master and set it as the default
currency across every existing company, Books Settings/Global Defaults,
and Account — part of the India (INR) -> Oman (OMR) currency migration.

Background:
    Doctype defaults (Books Company, Sales/Purchase Invoice, Quotation,
    Sales Order, Price List, Item Price, Payment Entry, Account, Bank
    Account) were changed from "INR" to "OMR" in their JSON definitions,
    and books_setup/bootstrap.py now reads a company's own
    default_currency instead of hardcoding "INR" for new Accounts. Those
    changes only affect NEW documents / NEW companies going forward --
    this patch back-fills existing data so already-installed sites pick
    up OMR too.

What this patch does, in order:
    1. Seeds the OMR currency into the Currency master if absent
       (symbol ر.ع., 3-decimal Baisa fraction -- Oman uses 1000 baisa
       to the rial, not a 100-subunit currency like INR/USD).
    2. Sets default_currency = "OMR" on every existing company (Books
       Company) that is still on the old "INR" default, and on Books
       Settings / Global Defaults' default_currency singletons.
    3. Back-fills currency = "OMR" on every existing Account whose
       currency is still "INR" -- but ONLY for accounts with zero GL
       Entries against them. An account that already has posted
       transactions keeps its original transaction currency; changing
       the currency under live postings would misstate historical
       balances. Accounts with existing entries are left untouched and
       logged so they can be reviewed/re-created manually if needed.

Non-destructive: never deletes or touches GL Entries, Sales/Purchase
Invoices, or any other transactional document -- those keep whatever
currency they were posted in. Only touches master/setting records, and
only where doing so is safe. Idempotent, safe to re-run.
"""
import frappe

from zoho_books_clone.books_setup.install import _all_company_names


def execute():
    _seed_omr_currency()
    _set_default_currency_on_companies()
    _set_default_currency_on_settings()
    _backfill_account_currency()


def _seed_omr_currency():
    if frappe.db.exists("Currency", "OMR"):
        return
    frappe.get_doc({
        "doctype":        "Currency",
        "currency_name":  "OMR",
        "symbol":         "ر.ع.",
        "fraction":       "Baisa",
        "fraction_units": 1000,
        "number_format":  "#,###.###",
        "enabled":        1,
    }).insert(ignore_permissions=True)
    frappe.db.commit()


def _set_default_currency_on_companies():
    if not frappe.db.exists("DocType", "Books Company"):
        return
    updated = 0
    for company in _all_company_names():
        # NOTE: Books Company's currency field is named "currency", not
        # "default_currency" -- that name only applies to Books Settings /
        # Global Defaults. Using the wrong fieldname here throws
        # "Unknown column 'default_currency'" on bench migrate.
        current = frappe.db.get_value("Books Company", company, "currency")
        if current in (None, "", "INR"):
            frappe.db.set_value("Books Company", company, "currency", "OMR")
            updated += 1
    if updated:
        frappe.db.commit()
    frappe.logger().info(f"[v1_19] Set currency=OMR on {updated} compan(y/ies).")


def _set_default_currency_on_settings():
    for doctype in ("Books Settings", "Global Defaults"):
        try:
            if not frappe.db.exists("DocType", doctype):
                continue
            current = frappe.db.get_single_value(doctype, "default_currency")
            if current in (None, "", "INR"):
                frappe.db.set_single_value(doctype, "default_currency", "OMR")
        except Exception:
            # default_currency may not exist on every deployment's Global
            # Defaults singleton -- skip quietly rather than fail the patch.
            pass
    frappe.db.commit()


def _backfill_account_currency():
    if not frappe.db.exists("DocType", "Account"):
        return

    inr_accounts = frappe.get_all(
        "Account",
        filters={"currency": "INR"},
        pluck="name",
    )
    if not inr_accounts:
        return

    updated = 0
    skipped = 0
    for account in inr_accounts:
        has_entries = frappe.db.exists("General Ledger Entry", {"account": account})
        if has_entries:
            skipped += 1
            continue
        frappe.db.set_value("Account", account, "currency", "OMR")
        updated += 1

    if updated:
        frappe.db.commit()

    frappe.logger().info(
        f"[v1_19] Back-filled currency=OMR on {updated} Account(s); "
        f"skipped {skipped} account(s) that already have GL Entries "
        f"(left on their original currency -- review manually if needed)."
    )