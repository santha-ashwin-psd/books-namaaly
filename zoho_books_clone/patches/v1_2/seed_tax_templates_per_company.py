"""
Patch v1_2: make Tax Templates per-company.

Background:
    Tax Template autoname changed from `field:template_name` (globally unique)
    to `format:{template_name} - {company}`. Legacy default templates were
    seeded once, globally named (e.g. "GST 18% (Intra-State)") and tied to a
    single company. This patch:

      1. Renames each legacy default (name == template_name, old scheme) to the
         new per-company name. `tax_code` is a Link to Tax Template everywhere,
         so frappe.rename_doc(force=True) updates all references automatically.
      2. Seeds any missing default templates for EVERY company.

    Non-destructive and idempotent:
      - Only the known app-default template names are migrated; user-created
        templates are never touched.
      - Nothing is ever deleted.
      - Safe to re-run.
"""
import frappe

from zoho_books_clone.books_setup.bootstrap import (
    _seed_tax_templates,
    DEFAULT_TAX_TEMPLATE_NAMES,
)
from zoho_books_clone.books_setup.install import _all_company_names


def execute():
    if not frappe.db.exists("DocType", "Tax Template"):
        return

    # Reload Tax Template and Tax Template Detail doctypes to ensure
    # the new autoname format (format:{template_name} - {company}) is active.
    frappe.reload_doc("taxes", "doctype", "tax_template")
    frappe.reload_doc("taxes", "doctype", "tax_template_detail")

    default_company = (
        frappe.db.get_single_value("Books Settings", "default_company") or ""
    )
    companies = _all_company_names()

    # ── 1. Migrate legacy globally-named defaults → "{name} - {company}" ──
    for template_name in DEFAULT_TAX_TEMPLATE_NAMES:
        # Old-scheme record: its name equals the bare template_name.
        if not frappe.db.exists("Tax Template", template_name):
            continue

        company = frappe.db.get_value("Tax Template", template_name, "company") or default_company
        if not company:
            # Can't build a per-company name — leave it as-is rather than guess.
            continue

        new_name = f"{template_name} - {company}"
        if frappe.db.exists("Tax Template", new_name):
            continue

        if not frappe.db.get_value("Tax Template", template_name, "company"):
            frappe.db.set_value("Tax Template", template_name, "company", company, update_modified=False)
        try:
            frappe.rename_doc("Tax Template", template_name, new_name, force=True)
        except Exception as exc:
            frappe.log_error(
                title="Patch v1_2",
                message=f"v1_2 tax-template rename '{template_name}' → '{new_name}': {exc}",
            )

    # ── 2. Repair template_name pollution from rename ──
    # frappe.rename_doc also rewrites the autoname source field (template_name),
    # appending " - {company}". Restore the clean display name on every migrated
    # default so the UI shows "GST 18% (Intra-State)" rather than the suffix.
    for company in companies:
        for base in DEFAULT_TAX_TEMPLATE_NAMES:
            nm = f"{base} - {company}"
            if frappe.db.exists("Tax Template", nm) and frappe.db.get_value("Tax Template", nm, "template_name") != base:
                frappe.db.set_value("Tax Template", nm, "template_name", base, update_modified=False)

    # ── 3. Seed any missing defaults for every company ──
    for company in companies:
        _seed_tax_templates(company)

    frappe.db.commit()
    print("✅  v1_2: tax templates migrated to per-company and back-filled.")
