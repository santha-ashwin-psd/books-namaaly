"""
Patch v1_6: seed the "Expense Category" master, scoped per company.

Expense.expense_type and Expense Claim Detail.expense_type used to be two
separate hardcoded Select fields with slightly different option lists:

  Expense:              Travel, Food & Meals, Accommodation, Office Supplies,
                         Utilities, Marketing, Software, Hardware, Training,
                         Miscellaneous
  Expense Claim Detail: Travel, Office Supplies, Utilities,
                         Meals & Entertainment, Software & Subscriptions,
                         Equipment & Fixtures, Professional Fees,
                         Communication, Other

Both fields are now Link fields against a single, company-enforced
"Expense Category" master (expense.json / expense_claim_detail.json),
mirroring the Tax Template pattern: company is a required field and
autoname is "format:{category_name} - {company}", so the same category
name can exist independently per company.

This patch seeds the union of both old lists (16 unique names) as Expense
Category records for EVERY existing Books Company, unchanged, so every
existing Expense / Expense Claim row still resolves to a valid Link value
for its own company -- no renaming or merging of the two lists, since that
would silently change data the client already has saved and reported on.

Must run after schema sync creates the Expense Category table.

Non-destructive and idempotent.
"""
import frappe

CATEGORIES = [
    # From Expense.expense_type
    "Travel", "Food & Meals", "Accommodation", "Office Supplies",
    "Utilities", "Marketing", "Software", "Hardware", "Training",
    "Miscellaneous",
    # From Expense Claim Detail.expense_type (dedup against the above)
    "Meals & Entertainment", "Software & Subscriptions",
    "Equipment & Fixtures", "Professional Fees", "Communication", "Other",
]


def execute():
    if not frappe.db.exists("DocType", "Expense Category"):
        return
    if not frappe.db.exists("DocType", "Books Company"):
        return

    companies = frappe.get_all("Books Company", pluck="name")
    seeded = 0

    for company in companies:
        for name in CATEGORIES:
            if frappe.db.exists("Expense Category", {"category_name": name, "company": company}):
                continue
            cat = frappe.get_doc({
                "doctype": "Expense Category",
                "category_name": name,
                "company": company,
            })
            cat.flags.ignore_permissions = True
            cat.flags.ignore_mandatory = True
            cat.insert()
            seeded += 1

    frappe.db.commit()
    print(f"seeded {seeded} Expense Category records across {len(companies)} companies.")