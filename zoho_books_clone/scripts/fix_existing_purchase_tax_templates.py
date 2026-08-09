"""
fix_existing_purchase_tax_templates.py

PROBLEM
-------
Bills.vue / DebitNotes.vue / PurchaseOrders.vue now filter the Tax Template
dropdown to templates where applies_to in ("Purchase", "Both"). That's correct
going forward, but it means any *already-saved* Purchase Invoice Item /
Purchase Order Item row whose tax_code still points at an old Sales-side
template (e.g. "GST 5% (Intra-State)") now shows a BLANK dropdown when the
document is opened for edit -- the stored value no longer matches any option
in the filtered list. This is what's happening on PINV-2026-00013 in the
screenshots: the read-only view still shows "GST 5% (Intra-State)" from the
raw stored tax_code, but Edit Bill shows an empty select.

This script is the data-fix pass: it walks every Purchase Invoice Item and
Purchase Order Item row (draft AND submitted, since drafts are exactly the
case in the screenshot) whose tax_code resolves to a Sales-applies_to
template, and repoints it at the matching "Input <name>" Purchase template
for the same company. It also re-checks GL Entries for submitted docs in
case fix_gst_gl_accounts.py was run before this data existed / missed rows,
so it's safe to re-run.

Debit Notes are Purchase Invoices with is_return=1 and share
Purchase Invoice Item, so they're covered automatically.

USAGE (bench console)
----------------------
>>> exec(open("apps/zoho_books_clone/zoho_books_clone/scripts/fix_existing_purchase_tax_templates.py").read())
    # runs in dry_run mode by default, prints a report, changes nothing

>>> dry_run = False
>>> exec(open("apps/zoho_books_clone/zoho_books_clone/scripts/fix_existing_purchase_tax_templates.py").read())
    # applies fixes
"""

import frappe

try:
    dry_run
except NameError:
    dry_run = False

PURCHASE_ITEM_DOCTYPES = ["Purchase Invoice Item", "Purchase Order Item"]

# parent doctype for each child table, and the fieldname on the parent
# that holds the child table (needed to reach company / docstatus)
PARENT_INFO = {
    "Purchase Invoice Item": {"parent_doctype": "Purchase Invoice", "parentfield": "items"},
    "Purchase Order Item": {"parent_doctype": "Purchase Order", "parentfield": "items"},
}


def get_sales_to_purchase_map():
    """Build {sales_template_name: purchase_template_name} per company,
    keyed by the full doc name (which includes ' - <company>')."""
    sales_templates = frappe.get_all(
        "Tax Template",
        filters={"applies_to": "Sales"},
        fields=["name", "template_name", "company"],
    )
    mapping = {}
    unmapped = []
    for t in sales_templates:
        purchase_name = f"Input {t.template_name} - {t.company}"
        if frappe.db.exists("Tax Template", purchase_name):
            mapping[t.name] = purchase_name
        else:
            unmapped.append(t.name)
    return mapping, unmapped


def fix_child_table(child_doctype, mapping, report):
    parent_doctype = PARENT_INFO[child_doctype]["parent_doctype"]

    rows = frappe.get_all(
        child_doctype,
        filters={"tax_code": ["in", list(mapping.keys())]},
        fields=["name", "parent", "parenttype", "tax_code", "idx"],
    )

    for row in rows:
        new_template = mapping[row.tax_code]
        parent_docstatus = frappe.db.get_value(parent_doctype, row.parent, "docstatus")

        report["rows"].append(
            {
                "doctype": child_doctype,
                "parent": row.parent,
                "row_idx": row.idx,
                "old_tax_code": row.tax_code,
                "new_tax_code": new_template,
                "parent_docstatus": parent_docstatus,
            }
        )

        if not dry_run:
            # frappe.db.set_value bypasses docstatus/validate locks, which we
            # need here since submitted Bills can't be saved normally.
            frappe.db.set_value(child_doctype, row.name, "tax_code", new_template, update_modified=False)


def fix_gl_entries(mapping, report):
    """Catch any GL Entry still posted to a *_Payable account on a
    Purchase Invoice voucher (submitted docs only -- GL only exists post-submit).
    Re-derives the correct Input account from the Tax Template Detail rows
    of the (now-corrected) tax template on each line."""

    payable_to_input = {
        "CGST Payable": "CGST Input",
        "SGST Payable": "SGST Input",
        "IGST Payable": "IGST Input",
    }

    bad_gl_rows = frappe.get_all(
        "General Ledger Entry",
        filters={
            "voucher_type": "Purchase Invoice",
            "account": ["in", list(payable_to_input.keys())],
        },
        fields=["name", "voucher_no", "account", "debit", "credit", "company"],
    )

    for gl in bad_gl_rows:
        new_account_base = payable_to_input[gl.account]
        # accounts in this app are company-scoped by name convention
        # elsewhere in the codebase (see fix_gst_gl_accounts.py precedent) --
        # resolve the company-scoped account name defensively.
        candidate = new_account_base
        if not frappe.db.exists("Account", candidate):
            candidate = f"{new_account_base} - {gl.company}"
        if not frappe.db.exists("Account", candidate):
            report["gl_unresolved"].append(gl)
            continue

        report["gl_rows"].append(
            {
                "gl_name": gl.name,
                "voucher_no": gl.voucher_no,
                "old_account": gl.account,
                "new_account": candidate,
                "debit": gl.debit,
                "credit": gl.credit,
            }
        )

        if not dry_run:
            frappe.db.set_value("General Ledger Entry", gl.name, "account", candidate, update_modified=False)


def run():
    report = {"rows": [], "gl_rows": [], "gl_unresolved": [], "unmapped_templates": []}

    mapping, unmapped = get_sales_to_purchase_map()
    report["unmapped_templates"] = unmapped

    for child_doctype in PURCHASE_ITEM_DOCTYPES:
        if frappe.db.exists("DocType", child_doctype):
            fix_child_table(child_doctype, mapping, report)

    fix_gl_entries(mapping, report)

    if not dry_run:
        frappe.db.commit()

    print("=" * 70)
    print(f"DRY RUN: {dry_run}")
    print(f"Sales templates with no matching Input template found: {len(report['unmapped_templates'])}")
    for u in report["unmapped_templates"]:
        print(f"  UNMAPPED: {u}")
    print("-" * 70)
    print(f"Line items to fix: {len(report['rows'])}")
    draft_count = sum(1 for r in report["rows"] if r["parent_docstatus"] == 0)
    submitted_count = sum(1 for r in report["rows"] if r["parent_docstatus"] == 1)
    print(f"  draft: {draft_count}  submitted: {submitted_count}")
    for r in report["rows"][:50]:
        print(f"  [{r['doctype']}] {r['parent']} row#{r['row_idx']} (docstatus={r['parent_docstatus']}): "
              f"{r['old_tax_code']} -> {r['new_tax_code']}")
    if len(report["rows"]) > 50:
        print(f"  ... and {len(report['rows']) - 50} more")
    print("-" * 70)
    print(f"GL Entries to fix: {len(report['gl_rows'])}")
    for g in report["gl_rows"][:50]:
        print(f"  {g['voucher_no']}: {g['old_account']} -> {g['new_account']} (dr={g['debit']} cr={g['credit']})")
    if len(report["gl_rows"]) > 50:
        print(f"  ... and {len(report['gl_rows']) - 50} more")
    if report["gl_unresolved"]:
        print(f"  UNRESOLVED (needs manual account mapping): {len(report['gl_unresolved'])}")
        for g in report["gl_unresolved"]:
            print(f"    {g.voucher_no}: {g.account}")
    print("=" * 70)
    if dry_run:
        print("This was a DRY RUN. No data changed. Set dry_run = False and re-run to apply.")
    else:
        print("Changes committed.")

    return report


_report = run()