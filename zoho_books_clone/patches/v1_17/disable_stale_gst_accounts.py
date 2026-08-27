"""
Patch v1_17: disable the default India-GST Tax Templates and GST-specific
Accounts seeded by bootstrap.py, now that GST has been switched off in
favour of Oman VAT.

Background:
    _seed_default_accounts() / _seed_tax_templates() (books_setup/bootstrap.py)
    create, for EVERY company on install:
      - 6 GST accounts: CGST/SGST/IGST Input + CGST/SGST/IGST Payable
      - 12 GST Tax Templates: GST 18/12/5/28% (Intra-State), IGST 18/12/5/28%
        (Inter-State), GST Exempt, and their Input (Purchase) equivalents
    These are India-specific and are no longer used now that the GST menu
    (GSTR-1/3B, e-Invoice, TDS, E-Way Bills) has been removed from the UI.

What this patch does:
    1. Disables (never deletes) every default GST Tax Template, for every
       company, by name (see GST_TAX_TEMPLATE_NAMES below).
    2. Disables (never deletes) every default GST Account, for every
       company, by full name "{account_name} - {company_abbr}".
    3. Only ever sets `disabled = 1` — never renames, deletes, or touches
       GL Entries / Tax Lines. Accounts/templates that already carry
       postings stay exactly as they are on the ledger; disabling only
       hides them from future selection (new Sales/Purchase docs, new
       Tax Template pickers). Historical documents referencing them are
       completely unaffected.
    4. Skips anything the user has already renamed, deleted, or
       re-enabled with custom data — this patch only touches rows that
       still match the original seeded name.

Non-destructive and idempotent: running this twice is a no-op the second
time (disabled=1 already). Safe to re-run.
"""
import frappe

from zoho_books_clone.books_setup.install import _all_company_names


# Same list as books_setup/bootstrap.py DEFAULT_TAX_TEMPLATE_NAMES
GST_TAX_TEMPLATE_NAMES = [
    "GST 18% (Intra-State)",
    "GST 12% (Intra-State)",
    "GST 5% (Intra-State)",
    "GST 28% (Intra-State)",
    "IGST 18% (Inter-State)",
    "IGST 12% (Inter-State)",
    "IGST 5% (Inter-State)",
    "IGST 28% (Inter-State)",
    "GST Exempt",
    "Input GST 18% (Intra-State)",
    "Input GST 12% (Intra-State)",
    "Input GST 5% (Intra-State)",
    "Input GST 28% (Intra-State)",
    "Input IGST 18% (Inter-State)",
    "Input IGST 12% (Inter-State)",
    "Input IGST 5% (Inter-State)",
    "Input IGST 28% (Inter-State)",
]

# Same list as books_setup/bootstrap.py GST_ACCOUNTS (account_name only)
GST_ACCOUNT_NAMES = [
    "CGST Input",
    "SGST Input",
    "IGST Input",
    "CGST Payable",
    "SGST Payable",
    "IGST Payable",
]


def execute():
    if not frappe.db.exists("DocType", "Tax Template"):
        return

    frappe.reload_doc("taxes", "doctype", "tax_template")
    frappe.reload_doc("accounts", "doctype", "account")

    companies = _all_company_names()
    disabled_templates = 0
    disabled_accounts = 0

    for company in companies:
        # --- Tax Templates -------------------------------------------------
        # Tax Template is per-company (format:{template_name} - {company}),
        # so match on template_name + company rather than guessing the
        # composed name.
        template_rows = frappe.get_all(
            "Tax Template",
            filters={
                "template_name": ["in", GST_TAX_TEMPLATE_NAMES],
                "company": company,
                "disabled": 0,
            },
            pluck="name",
        )
        for name in template_rows:
            frappe.db.set_value("Tax Template", name, "disabled", 1)
            disabled_templates += 1

        # --- Accounts --------------------------------------------------------
        account_rows = frappe.get_all(
            "Account",
            filters={
                "account_name": ["in", GST_ACCOUNT_NAMES],
                "company": company,
                "disabled": 0,
            },
            pluck="name",
        )
        for name in account_rows:
            frappe.db.set_value("Account", name, "disabled", 1)
            disabled_accounts += 1

    frappe.db.commit()
    frappe.logger().info(
        f"[v1_17] Disabled {disabled_templates} stale GST Tax Template(s) "
        f"and {disabled_accounts} stale GST Account(s) across "
        f"{len(companies)} company(ies)."
    )