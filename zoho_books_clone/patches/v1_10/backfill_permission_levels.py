"""
Patch v1_10: back-fill the new `lvl_<module>` permission-level fields on
Books Company Member from the existing `books_role` / `is_company_admin` /
`mod_<module>` fields.

Mapping (see Phase 0 decision):
    bypass / is_company_admin        -> "Delete" for every module
    Books Viewer,  mod_<module> = 1  -> "View"
    Books Viewer,  mod_<module> = 0  -> "None"
    Accountant/Manager, mod_<module> = 1 -> "Edit"
    Accountant/Manager, mod_<module> = 0 -> "None"

Deliberately caps non-admin roles at "Edit" rather than "Delete": the old
boolean model had no delete/cancel distinction at all, so jumping straight
to "Delete" on migration would silently grant capability nobody explicitly
had before. "Delete" stays an opt-in a company admin grants afterward.

Must run after schema sync creates the lvl_* columns (post_model_sync).
Idempotent: only fills rows where every lvl_* is still unset/"None", so
re-running after an admin has already customized levels is a no-op for them.
"""
import frappe

MODULES = (
    "invoices", "bills", "payments", "banking", "inventory",
    "accounts", "reports", "customers", "taxes", "admin",
)
MOD_FIELDS = tuple(f"mod_{m}" for m in MODULES)
LVL_FIELDS = tuple(f"lvl_{m}" for m in MODULES)


def execute():
    if not frappe.db.exists("DocType", "Books Company Member"):
        return

    rows = frappe.get_all(
        "Books Company Member",
        fields=["name", "books_role", "is_company_admin", *MOD_FIELDS, *LVL_FIELDS],
    )

    updated = 0
    for row in rows:
        # Skip rows an admin has already hand-configured post-migration.
        if any((row.get(f) or "None") != "None" for f in LVL_FIELDS):
            continue

        is_admin = bool(row.get("is_company_admin"))
        is_viewer = (row.get("books_role") == "Books Viewer") and not is_admin

        values = {}
        for mod_f, lvl_f in zip(MOD_FIELDS, LVL_FIELDS):
            if is_admin:
                values[lvl_f] = "Delete"
            elif not row.get(mod_f):
                values[lvl_f] = "None"
            elif is_viewer:
                values[lvl_f] = "View"
            else:
                values[lvl_f] = "Edit"

        frappe.db.set_value("Books Company Member", row["name"], values, update_modified=False)
        updated += 1

    frappe.db.commit()
    print(f"✅  v1_10: back-filled permission levels for {updated} Books Company Member row(s).")