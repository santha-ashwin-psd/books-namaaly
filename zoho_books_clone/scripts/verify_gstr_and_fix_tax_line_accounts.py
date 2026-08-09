"""
verify_gstr_and_fix_tax_line_accounts.py

PART A — VERIFY GSTR-1 / GSTR-3B ARE CALCULATING CORRECTLY
------------------------------------------------------------
get_gstr1_data() and get_gstr_summary() (db/queries.py) compute everything
from Tax Line.tax_type / rate / tax_amount, grouped per invoice. They never
read the GL account or the Tax Template's applies_to. This means the
Payable-vs-Input bug never corrupted the *numbers* on GSTR filings -- only
the GL/balance-sheet classification. This script re-runs both queries for a
period and prints the totals so you can eyeball them against known invoice
counts/values.

PART B — FIX STALE Tax Line.account_head ON PURCHASE INVOICES
------------------------------------------------------------
The earlier fix (fix_existing_purchase_tax_templates.py) repointed
Purchase/Purchase-Order Item.tax_code and corrected already-posted GL Entry
accounts. It did NOT touch the Tax Line child-table rows already saved on
each Purchase Invoice/Debit Note -- those still carry the OLD account_head
(a *_Payable account) copied in at save time from the wrong template.

This matters because:
  1. get_itc_ledger() (GSTR-2A recon) displays account_head per line -- it
     will still show "CGST Payable" etc. even though GL is now correct.
  2. accounting_engine.py reverses GL on cancel/amend using
     tax.account_head -- if this is still wrong, cancelling one of these
     invoices later will re-post to the wrong account and undo the earlier
     GL fix.

This section finds every Tax Line row (parenttype = Purchase Invoice) whose
account_head is one of CGST/SGST/IGST Payable, and repoints it to the
matching Input account -- data-only, no recalculation, no doc events.

USAGE (bench console)
----------------------
>>> exec(open("/full/path/to/verify_gstr_and_fix_tax_line_accounts.py").read(), globals())
    # dry_run defaults to True; prints GSTR report + Tax Line report, changes nothing

>>> dry_run = False
>>> exec(open("/full/path/to/verify_gstr_and_fix_tax_line_accounts.py").read(), globals())
    # applies the Tax Line account_head fix
"""

import frappe
from frappe.utils import flt

try:
    dry_run
except NameError:
    dry_run = True

# Adjust these for the period/company you want to check
COMPANY = frappe.db.get_single_value("Books Settings", "default_company") or None
FROM_DATE = "2026-04-01"   # edit to your GST period
TO_DATE = "2026-08-09"     # edit to your GST period

PAYABLE_TO_INPUT = {
    "CGST Payable": "CGST Input",
    "SGST Payable": "SGST Input",
    "IGST Payable": "IGST Input",
}


def resolve_account(base_name, company):
    if frappe.db.exists("Account", base_name):
        return base_name
    scoped = f"{base_name} - {company}"
    if frappe.db.exists("Account", scoped):
        return scoped
    return None


def part_a_verify_gstr(company, from_date, to_date):
    from zoho_books_clone.db.queries import get_gstr_summary, get_gstr1_data

    print("=" * 70)
    print(f"PART A — GSTR verification for {company}, {from_date} to {to_date}")
    print("=" * 70)

    summary = get_gstr_summary(company, from_date, to_date)
    print("\n-- GSTR-3B style summary --")
    print(f"Taxable value (net_total, outward SIs): {summary['taxable_value']:.2f}")
    print(f"Total Output tax:  {summary['totals']['total_output']:.2f}")
    print(f"Total ITC:         {summary['totals']['total_itc']:.2f}")
    print(f"Net liability:     {summary['totals']['net_tax_liability']:.2f}")
    print("\nBy tax type:")
    for r in summary["net_by_type"]:
        print(f"  {r['tax_type']:6s}  output={r['output']:>12.2f}  itc={r['itc']:>12.2f}  net={r['net']:>12.2f}")

    g1 = get_gstr1_data(company, from_date, to_date)
    print("\n-- GSTR-1 --")
    print(f"B2B invoices: {g1['totals']['b2b_count']}   B2C invoices: {g1['totals']['b2c_count']}   CDNR: {g1['totals']['cdnr_count']}")
    print(f"Total taxable value: {g1['totals']['total_taxable']:.2f}")
    print(f"Total tax: {g1['totals']['total_tax']:.2f}")

    # Cross-check: GSTR-1 total_tax vs GSTR-3B total_output should match
    # (both sourced from Sales Invoice Tax Lines over the same period/company)
    diff = abs(g1["totals"]["total_tax"] - summary["totals"]["total_output"])
    print(f"\nCross-check GSTR-1 total_tax vs GSTR-3B total_output diff: {diff:.2f} "
          f"{'OK' if diff < 0.01 else '!! MISMATCH — investigate'}")


def part_b_fix_tax_line_accounts():
    print("\n" + "=" * 70)
    print("PART B — stale Tax Line.account_head on Purchase Invoices")
    print("=" * 70)

    rows = frappe.get_all(
        "Tax Line",
        filters={
            "parenttype": "Purchase Invoice",
            "account_head": ["in", list(PAYABLE_TO_INPUT.keys())],
        },
        fields=["name", "parent", "account_head", "tax_type", "tax_amount", "idx"],
    )

    print(f"Tax Line rows still on a Payable account: {len(rows)}")

    fixed, unresolved = [], []
    for row in rows:
        company = frappe.db.get_value("Purchase Invoice", row.parent, "company")
        new_base = PAYABLE_TO_INPUT[row.account_head]
        resolved = resolve_account(new_base, company)
        if not resolved:
            unresolved.append(row)
            continue
        fixed.append((row, resolved))
        if not dry_run:
            frappe.db.set_value("Tax Line", row.name, "account_head", resolved, update_modified=False)

    for row, resolved in fixed[:50]:
        print(f"  {row.parent} row#{row.idx} [{row.tax_type}] {row.account_head} -> {resolved} (amt={row.tax_amount})")
    if len(fixed) > 50:
        print(f"  ... and {len(fixed) - 50} more")

    if unresolved:
        print(f"\nUNRESOLVED (no matching Input account found — needs manual look): {len(unresolved)}")
        for row in unresolved:
            print(f"  {row.parent} row#{row.idx}: {row.account_head}")

    if not dry_run:
        frappe.db.commit()
        print(f"\nCommitted: {len(fixed)} Tax Line rows repointed.")
    else:
        print("\nDRY RUN — no changes made. Set dry_run = False and re-run to apply.")


if COMPANY:
    part_a_verify_gstr(COMPANY, FROM_DATE, TO_DATE)
else:
    print("Could not auto-resolve default company — edit COMPANY at top of script and re-run Part A manually:")
    print('  part_a_verify_gstr("Your Company Name", FROM_DATE, TO_DATE)')

part_b_fix_tax_line_accounts()