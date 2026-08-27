"""
Patch v1_18: seed "Input VAT" / "Output VAT" accounts and matching Tax
Templates for every company, for the Oman VAT migration (replaces the
disabled India-GST templates from v1_17).

Background:
    Oman levies a single-rate VAT (currently 5%) administered by the OTA --
    unlike India's GST there is no CGST/SGST/IGST split, just one Input
    (reclaimable on purchases) and one Output (payable on sales) tax line.
    useTaxCalc.js's tax breakdown helper already special-cases
    tax_type == "VAT" as a single-line item (see qPe() in the compiled
    bundle / its Vue source), so no engine change is needed -- only the
    account + Tax Template data.

What this patch seeds, per company (idempotent -- skips anything that
already exists by full name):
    Accounts:
      - "Input VAT"  (Tax, under Input Tax Credits)  -- reclaimable on Bills
      - "Output VAT" (Tax, under Current Liabilities) -- payable on Invoices
    Tax Templates:
      - "Output VAT 5%" (applies_to: Sales)    -> account_head: Output VAT
      - "Input VAT 5%"  (applies_to: Purchase) -> account_head: Input VAT
    Both templates use tax_type "VAT" (single tax line, no CGST/SGST/IGST
    split) and rate 5 (Oman's standard VAT rate as of this writing --
    change VAT_RATE below if the OTA rate changes or a different rate
    applies to your company).

Non-destructive and idempotent: only inserts rows that don't already
exist (checked by full account/document name); never renames, deletes,
or edits an existing Account or Tax Template. Safe to re-run.
"""
import frappe

from zoho_books_clone.books_setup.install import _all_company_names


VAT_RATE = 5  # Oman standard VAT rate (%) -- adjust if it changes

# (account_name, account_type, parent_name, is_group)
VAT_ACCOUNTS = [
    ("Input VAT",  "Tax", "Input Tax Credits",   0),
    ("Output VAT", "Tax", "Current Liabilities", 0),
]

# (template_name, applies_to, tax_type, description, account_name)
VAT_TAX_TEMPLATES = [
    (f"Output VAT {VAT_RATE}%", "Sales",    "VAT", f"VAT @ {VAT_RATE}%",     "Output VAT"),
    (f"Input VAT {VAT_RATE}%",  "Purchase", "VAT", f"VAT ITC @ {VAT_RATE}%", "Input VAT"),
]


def _acc_name(account_name: str, company: str) -> str:
    return f"{account_name} - {company}"


def execute():
    if not frappe.db.exists("DocType", "Account") or not frappe.db.exists("DocType", "Tax Template"):
        return

    frappe.reload_doc("accounts", "doctype", "account")
    frappe.reload_doc("taxes", "doctype", "tax_template")
    frappe.reload_doc("taxes", "doctype", "tax_template_detail")

    accounts_created = 0
    templates_created = 0

    for company in _all_company_names():
        # --- Accounts --------------------------------------------------
        for name, atype, parent, is_group in VAT_ACCOUNTS:
            full_name = _acc_name(name, company)
            if frappe.db.exists("Account", full_name):
                continue
            parent_full = _acc_name(parent, company) if parent else ""
            if parent_full and not frappe.db.exists("Account", parent_full):
                # Parent group (e.g. "Input Tax Credits - {company}") missing --
                # skip rather than fail; bootstrap.py's COA seeding creates it
                # for new companies, but a company set up before that group
                # existed may not have it. Fall back to placing under root
                # "Assets"/"Liabilities" so the account is never silently lost.
                fallback_parent = "Assets" if name == "Input VAT" else "Liabilities"
                parent_full = _acc_name(fallback_parent, company)
                if not frappe.db.exists("Account", parent_full):
                    frappe.log_error(
                        title="Books Bootstrap",
                        message=f"v1_18 VAT Account — {company}/{name}: "
                                f"no parent group found (tried '{parent}' and '{fallback_parent}'), skipped.",
                    )
                    continue
            try:
                currency = frappe.db.get_value("Books Company", company, "default_currency") or "OMR"
            except Exception:
                currency = "OMR"
            try:
                frappe.get_doc({
                    "doctype":        "Account",
                    "account_name":   name,
                    "account_type":   atype,
                    "parent_account": parent_full,
                    "is_group":       is_group,
                    "company":        company,
                    "currency":       currency,
                }).insert(ignore_permissions=True)
                accounts_created += 1
            except Exception as exc:
                frappe.log_error(
                    title="Books Bootstrap",
                    message=f"v1_18 VAT Account — {company}/{name}: {exc}",
                )

        # --- Tax Templates -----------------------------------------------
        def _acct(name):
            return frappe.db.get_value(
                "Account", {"account_name": name, "company": company, "is_group": 0}, "name"
            ) or _acc_name(name, company)

        for template_name, applies_to, tax_type, description, account_name in VAT_TAX_TEMPLATES:
            doc_name = f"{template_name} - {company}"
            if frappe.db.exists("Tax Template", doc_name):
                continue
            try:
                frappe.get_doc({
                    "doctype": "Tax Template",
                    "template_name": template_name,
                    "company": company,
                    "tax_type": tax_type,
                    "applies_to": applies_to,
                    "taxes": [
                        {
                            "tax_type": tax_type,
                            "description": description,
                            "rate": VAT_RATE,
                            "account_head": _acct(account_name),
                        }
                    ],
                }).insert(ignore_permissions=True)
                templates_created += 1
            except Exception as exc:
                frappe.log_error(
                    title="Books Bootstrap",
                    message=f"v1_18 VAT Tax Template — {company}/{template_name}: {exc}",
                )

    frappe.db.commit()
    frappe.logger().info(
        f"[v1_18] Seeded {accounts_created} VAT account(s) and "
        f"{templates_created} VAT Tax Template(s) across "
        f"{len(_all_company_names())} company(ies)."
    )