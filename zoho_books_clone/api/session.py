import frappe
import frappe.sessions

# Import MODULES (not the private _MOD_FIELDS) so this stays the single
# source of truth shared with utils/access.py rather than a second list
# that could drift out of sync with it.
from zoho_books_clone.utils.access import MODULES, _membership as _access_membership

_SYSTEM_USERS = {"Administrator", "Guest"}
_MODULE_FIELDS = tuple(f"mod_{m}" for m in MODULES)


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

    Delegates the actual capability resolution to utils.access._membership()
    (Phase 1's granular level engine) so this file and access.py can never
    drift apart on who's an admin / what "read-only" means / what a module
    flag resolves to — there is exactly one place that logic lives now.

    Adds `levels`: {module: "None"|"View"|"Create"|"Edit"|"Delete"} on top of
    the legacy mod_<module> booleans (kept as-is for existing SPA code —
    usePermissions().can()/canWrite() still read those) so the frontend can
    move to granular per-action gating (Phase 4) without a breaking payload
    change today."""
    m = _access_membership(user)
    read_only = bool(m["readonly"] and not m["admin"])
    return {
        "books_role":       m["role"],
        "is_company_admin": m["admin"],
        "read_only":        read_only,
        **{f"mod_{mod}": bool(m["mods"].get(mod)) for mod in MODULES},
        "levels":           dict(m["levels"]),
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