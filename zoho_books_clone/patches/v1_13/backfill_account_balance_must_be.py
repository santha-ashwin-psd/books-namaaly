"""
Patch v1_13: back-fills Account.balance_must_be for every existing account.

`balance_must_be` (the "Balance Type" dropdown in the Chart of Accounts edit
drawer -- Debit/Credit) was being sent by the frontend and accepted by
`save_account()` all along, but the Account doctype never actually declared
this field in its schema. `save_account()` guards every optional write with
`frappe.db.has_column(...)`, so with no such column the value was silently
dropped on every save -- the UI looked like it saved, the request succeeded,
but nothing was ever written. This rework adds the column to account.json;
a JSON `default` only applies to rows inserted *after* the column exists, so
every pre-existing Account needs its balance_must_be explicitly set here or
it stays NULL forever.

Safe to re-run: only touches rows that are still NULL/empty.
"""
import frappe


def execute():
    if not frappe.db.exists("DocType", "Account"):
        return
    if not frappe.db.has_column("Account", "balance_must_be"):
        return  # schema sync for this column hasn't landed yet

    count = frappe.db.sql("""
        UPDATE `tabAccount`
        SET balance_must_be = 'Debit'
        WHERE balance_must_be IS NULL OR balance_must_be = ''
    """)
    frappe.db.commit()

    updated = frappe.db.sql("SELECT ROW_COUNT()")[0][0]
    print(
        f"✅  v1_13: balance_must_be back-filled to 'Debit' for {updated} "
        f"existing account(s) that had never stored a value for it. "
        f"Edit any account whose opening balance is naturally on the "
        f"credit side (e.g. a Payable) and switch it to Credit there."
    )