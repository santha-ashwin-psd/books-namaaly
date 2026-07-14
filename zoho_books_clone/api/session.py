import frappe
import frappe.sessions

from zoho_books_clone.utils.tenancy import _is_bypass

_SYSTEM_USERS = {"Administrator", "Guest"}

_MODULE_FIELDS = (
    "mod_invoices", "mod_bills", "mod_payments", "mod_banking", "mod_inventory",
    "mod_accounts", "mod_reports", "mod_customers", "mod_taxes", "mod_admin",
)


def _get_company(user: str) -> str:
    """
    Resolve the active company for this specific user.
    Order: per-user default → Books Company Member row → Books Settings default.
    Returns empty string if none of those resolve.
    """
    try:
        val = frappe.defaults.get_user_default("company", user)
        if val:
            print(f"[BooksCompany][session.py] _get_company({user}) resolved from PER-USER DEFAULT: {val}")
            return val
    except Exception:
        pass

    try:
        val = frappe.db.get_value("Books Company Member", {"user": user}, "company")
        if val:
            print(f"[BooksCompany][session.py] _get_company({user}) resolved from Books Company Member: {val}")
            return val
    except Exception:
        pass

    try:
        val = frappe.db.get_single_value("Books Settings", "default_company")
        if val:
            print(f"[BooksCompany][session.py] _get_company({user}) resolved from Books Settings.default_company: {val}")
            return val
    except Exception:
        pass

    print(f"[BooksCompany][session.py] _get_company({user}) resolved to EMPTY STRING (no source matched)")
    return ""


def _is_new_user(user: str) -> bool:
    if user in _SYSTEM_USERS:
        return False
    try:
        return not frappe.defaults.get_user_default("books_tutorial_done", user)
    except Exception:
        return False


def _get_membership(user: str) -> dict:
    """Return the user's Books Company Member fields needed for SPA permission gating.

    Bypass roles (Administrator / System Manager) get all module flags = True
    and a synthetic admin role, since they see everything anyway. Users without
    a membership row get all flags = False — the SPA will route them to a
    "no access" state rather than crash."""
    flags = {f: False for f in _MODULE_FIELDS}

    if _is_bypass(user):
        return {
            "books_role":       "Books Admin",
            "is_company_admin": True,
            "read_only":        False,
            **{f: True for f in _MODULE_FIELDS},
        }

    row = frappe.db.get_value(
        "Books Company Member",
        {"user": user},
        ["books_role", "is_company_admin", *_MODULE_FIELDS],
        as_dict=True,
    )
    if not row:
        return {"books_role": "", "is_company_admin": False, "read_only": True, **flags}

    # Company admins implicitly get every module.
    if row.get("is_company_admin"):
        for f in _MODULE_FIELDS:
            row[f] = 1

    # Normalise int/None → bool for the JSON payload.
    is_admin = bool(row.get("is_company_admin"))
    return {
        "books_role":       row.get("books_role") or "",
        "is_company_admin": is_admin,
        # Read-only when the role is Books Viewer and not a company admin.
        "read_only":        (row.get("books_role") == "Books Viewer") and not is_admin,
        **{f: bool(row.get(f)) for f in _MODULE_FIELDS},
    }


@frappe.whitelist(allow_guest=False)
def get_books_session():
    """Returns session info needed to bootstrap the Books Vue SPA, including
    the user's module-permission flags so the shell can render in one round trip."""
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)

    try:
        fullname = frappe.utils.get_fullname(user) or user
    except Exception:
        fullname = user

    try:
        csrf = frappe.sessions.get_csrf_token()
    except Exception:
        csrf = ""

    return {
        "user":        user,
        "fullname":    fullname,
        "csrf_token":  csrf,
        "company":     _get_company(user),
        "is_new_user": _is_new_user(user),
        "permissions": _get_membership(user),
    }


@frappe.whitelist(methods=["POST"])
def mark_tutorial_done():
    user = frappe.session.user
    if user and user not in _SYSTEM_USERS:
        try:
            frappe.defaults.set_user_default("books_tutorial_done", "1", user)
            frappe.db.commit()
        except Exception:
            pass
    return {"ok": True}