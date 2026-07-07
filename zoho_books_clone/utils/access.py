"""
Custom role / module authorization — layered ON TOP of Frappe's permissions and
the multi-tenant company isolation in utils/tenancy.py.

Capability model:
  • Each gated doctype maps to a module (DOCTYPE_MODULE). A user can touch a
    doctype only if their `mod_<module>` flag is on (read & write).
  • "Books Viewer" is read-only everywhere — every write is blocked.
  • Accountant / Books Manager can read AND write within their granted modules.
  • Company admins (is_company_admin) and bypass roles (Administrator /
    System Manager) have full access.
  • Unmapped doctypes default to allowed, so lookups / non-sensitive doctypes
    never break. A doctype must be explicitly mapped to be gated.

The membership flags live on the "Books Company Member" doctype and are the same
ones surfaced to the SPA by api/session._get_membership.
"""
import frappe
from frappe import _

from zoho_books_clone.utils.tenancy import _is_bypass, get_user_company

# Module keys (without the `mod_` prefix), matching api/session._MODULE_FIELDS.
MODULES = (
    "invoices", "bills", "payments", "banking", "inventory",
    "accounts", "reports", "customers", "taxes", "admin",
)
_MOD_FIELDS = tuple(f"mod_{m}" for m in MODULES)

# Doctype → module. Anything not listed is treated as unmapped (allowed).
DOCTYPE_MODULE = {
    # Sales / invoicing
    "Sales Invoice": "invoices", "Quotation": "invoices", "Sales Order": "invoices",
    "Credit Note": "invoices", "Delivery Note": "invoices", "Proforma Invoice": "invoices",
    # Purchases / bills
    "Purchase Invoice": "bills", "Purchase Order": "bills", "Expense": "bills",
    "Expense Claim": "bills", "Debit Note": "bills", "Purchase Receipt": "bills",
    # Payments
    "Payment Entry": "payments",
    # Banking
    "Bank Account": "banking", "Bank Transaction": "banking", "Bank Transfer": "banking",
    # Inventory
    "Item": "inventory", "Item Group": "inventory", "Warehouse": "inventory",
    "Stock Entry": "inventory", "Stock Ledger Entry": "inventory", "Price List": "inventory",
    # Accounting
    "Account": "accounts", "Journal Entry": "accounts", "Cost Center": "accounts",
    "Fiscal Year": "accounts", "General Ledger Entry": "accounts",
    # Contacts
    "Customer": "customers", "Supplier": "customers", "Contact": "customers", "Address": "customers",
    "Sales Person": "customers",
    # Taxes / GST
    "Tax Template": "taxes",
    "Tax Template Detail": "taxes",
    # Admin / settings
    "Books Company": "admin", "Books Company Member": "admin",
    "Books Settings": "admin", "Books Number Series": "admin",
}

_WRITE_ACTIONS = {"write", "create", "delete", "submit", "cancel"}


def module_for(doctype: str) -> str | None:
    """Return the module key gating `doctype`, or None when unmapped (allowed)."""
    return DOCTYPE_MODULE.get(doctype)


def _membership(user: str) -> dict:
    """Resolve the caller's capability snapshot.
    Keys: bypass, admin, readonly, no_member, role, mods{module: bool}."""
    if _is_bypass(user):
        return {"bypass": True, "admin": True, "readonly": False, "no_member": False,
                "role": "Books Admin", "mods": {m: True for m in MODULES}}

    row = frappe.db.get_value(
        "Books Company Member", {"user": user},
        ["books_role", "is_company_admin", *_MOD_FIELDS], as_dict=True,
    )
    if not row:
        # No membership and not a bypass user → no access (read-only, no modules).
        return {"bypass": False, "admin": False, "readonly": True, "no_member": True,
                "role": "", "mods": {m: False for m in MODULES}}

    admin = bool(row.get("is_company_admin"))
    return {
        "bypass": False,
        "admin": admin,
        "readonly": (row.get("books_role") == "Books Viewer"),
        "no_member": False,
        "role": row.get("books_role") or "",
        # Company admins implicitly hold every module.
        "mods": {m: (admin or bool(row.get(f"mod_{m}"))) for m in MODULES},
    }


def can_read(doctype: str, user: str | None = None) -> bool:
    m = _membership(user or frappe.session.user)
    if m["admin"]:
        return True
    mod = module_for(doctype)
    if mod is None:
        return True  # unmapped → allowed
    return m["mods"].get(mod, False)


def can_write(doctype: str, user: str | None = None) -> bool:
    m = _membership(user or frappe.session.user)
    if m["admin"]:
        return True
    if m["no_member"] or m["readonly"]:
        return False
    mod = module_for(doctype)
    if mod is None:
        return True  # unmapped → allowed for non-readonly members
    return m["mods"].get(mod, False)


def _deny(doctype: str, write: bool, user: str):
    m = _membership(user)
    if write and m["readonly"] and not m["no_member"]:
        msg = _("Your role ({0}) is read-only — you can't modify {1}.").format(
            m["role"] or "Books Viewer", doctype)
    else:
        mod = module_for(doctype)
        if mod:
            msg = _("You don't have access to the {0} module.").format(mod)
        else:
            msg = _("You don't have permission to {0} {1}.").format(
                "modify" if write else "view", doctype)
    frappe.throw(msg, frappe.PermissionError)


def assert_can(doctype: str, action: str = "read", user: str | None = None):
    """Raise frappe.PermissionError unless the caller may perform `action`
    (read | write | create | delete | submit | cancel) on `doctype`."""
    user = user or frappe.session.user
    if user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    write = action in _WRITE_ACTIONS
    if write:
        if not can_write(doctype, user):
            _deny(doctype, True, user)
    else:
        if not can_read(doctype, user):
            _deny(doctype, False, user)


def require_module(module: str, write: bool = False, user: str | None = None):
    """Enforce module access for standalone endpoints that aren't a single
    doctype save (e.g. GST/TDS posting, banking GL, bulk import)."""
    user = user or frappe.session.user
    if user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    m = _membership(user)
    if m["admin"]:
        return
    if write and (m["no_member"] or m["readonly"]):
        frappe.throw(_("Your role is read-only — you can't perform this action."),
                     frappe.PermissionError)
    if not m["mods"].get(module, False):
        frappe.throw(_("You don't have access to the {0} module.").format(module),
                     frappe.PermissionError)


def require_write(user: str | None = None):
    """Block read-only roles (and non-members) from any write/action, without
    requiring a specific module. Use for endpoints whose module is ambiguous
    (e.g. recurring/subscriptions, bulk operations). Admins/bypass pass."""
    user = user or frappe.session.user
    if user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    m = _membership(user)
    if m["admin"]:
        return
    if m["no_member"] or m["readonly"]:
        frappe.throw(_("Your role is read-only — you can't perform this action."),
                     frappe.PermissionError)


def is_readonly(user: str | None = None) -> bool:
    """True when the user is a read-only role (Books Viewer) — not admin/bypass."""
    m = _membership(user or frappe.session.user)
    return bool(m["readonly"] and not m["admin"])


def assert_company(company: str | None, user: str | None = None):
    """Reject a user-supplied `company` that isn't the caller's own company.
    Closes cross-company write/read holes on endpoints that take a company arg."""
    user = user or frappe.session.user
    if _is_bypass(user):
        return
    own = get_user_company(user)
    if not own or (company and company != own):
        frappe.throw(_("You don't have access to that company."), frappe.PermissionError)
