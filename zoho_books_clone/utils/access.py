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

# Granular permission-level enum (Phase 1). Each level implies everything
# below it. Stored on Books Company Member as lvl_<module> Select fields,
# alongside (not yet replacing) the legacy mod_<module> booleans above.
LEVELS = ("None", "View", "Create", "Edit", "Delete")
_LEVEL_INDEX = {lvl: i for i, lvl in enumerate(LEVELS)}
_LVL_FIELDS = tuple(f"lvl_{m}" for m in MODULES)

# Doctypes with is_submittable=1 in this app. "Delete"-level access on one of
# these means cancel, never frappe.client.delete (Frappe won't physically
# delete a submitted doc anyway) -- kept in sync manually against the
# doctype JSONs; verified as of the Phase 0 audit.
SUBMITTABLE_DOCTYPES = {
    "Sales Invoice", "Purchase Invoice", "Purchase Order", "Purchase Receipt",
    "Quotation", "Credit Note", "Delivery Note", "Expense", "Expense Claim",
    "Payment Entry", "Journal Entry", "Stock Entry", "Landed Cost Voucher",
    "Bank Transaction", "Material Request", "Work Order", "BOM",
    "Production Plan", "Asset", "Asset Movement", "Asset Repair",
    "Asset Value Adjustment", "Asset Disposal", "QC Inspection",
}

# assert_can's `action` -> minimum lvl_<module> required. "cancel" and
# "submit" stay at "Edit" deliberately: they're routine workflow actions
# (e.g. reversing a Work Order's Stock Entry, submitting a draft) gated
# identically to write today, not the destructive tier. Only "delete" (the
# generic delete_doc endpoint) requires the new "Delete" tier -- that's the
# actual new gate this phase introduces.
_ACTION_LEVEL = {
    "read": "View",
    "create": "Create",
    "write": "Edit",
    "submit": "Edit",
    "cancel": "Edit",
    "delete": "Delete",
}


def _level_at_least(level: str, threshold: str) -> bool:
    return _LEVEL_INDEX.get(level, 0) >= _LEVEL_INDEX.get(threshold, 0)


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
    "Landed Cost Voucher": "inventory",
    # Manufacturing
    "BOM": "inventory", "Work Order": "inventory", "Production Plan": "inventory",
    "Job Card": "inventory", "Material Request": "inventory",
    "Packing Slip": "inventory", "Alternative Item": "inventory",
    "Material Substitution Log": "inventory",
    "Routing": "inventory", "Operation": "inventory", "Workstation": "inventory",
    "Workstation Type": "inventory",
    "QC Inspection": "inventory", "QC Inspection Template": "inventory",
    "QC Approval Request": "inventory",
    # Assets (mapped to inventory to match Phase 4 frontend gating)
    "Asset": "inventory", "Asset Category": "inventory", "Asset Movement": "inventory",
    "Asset Repair": "inventory", "Asset Value Adjustment": "inventory",
    "Asset Disposal": "inventory", "Department": "inventory", "Maintenance Log": "inventory",
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


def module_for(doctype: str) -> str | None:
    """Return the module key gating `doctype`, or None when unmapped (allowed)."""
    return DOCTYPE_MODULE.get(doctype)


def _membership(user: str) -> dict:
    """Resolve the caller's capability snapshot.
    Keys: bypass, admin, readonly, no_member, role, mods{module: bool},
    levels{module: one of LEVELS}.

    `levels_customized` (Check field on Books Company Member) gates how
    `levels` is computed:
      - False (default, untouched members): `levels` is the max of the
        legacy mod_<module>-derived level (View for Books Viewer, Edit
        otherwise) and whatever lvl_<module> happens to hold. Since
        lvl_<module> Select fields default to "None" and are never written
        by admin.py's older code paths, this additive-only merge means a
        member row nobody has touched via the granular dialog keeps working
        exactly as before -- the "None" default can't accidentally revoke
        access it was never meant to affect.
      - True (admin explicitly saved granular levels via Module Access):
        lvl_<module> is trusted as-is, including an explicit "None" that
        restricts below what the mod_<module> checkbox alone would grant.
        This is what makes the level dropdown a real override once an admin
        has actually used it, without retroactively breaking every existing
        member the first time this feature shipped."""
    if _is_bypass(user):
        return {"bypass": True, "admin": True, "readonly": False, "no_member": False,
                "role": "Books Admin", "mods": {m: True for m in MODULES},
                "levels": {m: "Delete" for m in MODULES}}

    row = frappe.db.get_value(
        "Books Company Member", {"user": user},
        ["books_role", "is_company_admin", "levels_customized", *_MOD_FIELDS, *_LVL_FIELDS], as_dict=True,
    )
    if not row:
        # No membership and not a bypass user → no access (read-only, no modules).
        return {"bypass": False, "admin": False, "readonly": True, "no_member": True,
                "role": "", "mods": {m: False for m in MODULES},
                "levels": {m: "None" for m in MODULES}}

    admin = bool(row.get("is_company_admin"))
    readonly = (row.get("books_role") == "Books Viewer")
    mods = {m: (admin or bool(row.get(f"mod_{m}"))) for m in MODULES}
    customized = bool(row.get("levels_customized"))

    levels = {}
    for m in MODULES:
        if admin:
            levels[m] = "Delete"
            continue
        legacy = ("View" if readonly else "Edit") if mods[m] else "None"
        stored = row.get(f"lvl_{m}") or "None"
        if customized:
            # Admin has explicitly configured granular levels for this member
            # via Module Access -- trust lvl_<module> as-is, including an
            # explicit "None" that restricts below the checkbox.
            levels[m] = stored
        else:
            # Never explicitly configured -- lvl_<module> only holds its
            # Select-field default ("None") noise, not a real admin decision.
            # Keep the original additive-only behavior so untouched members
            # don't lose access this field wasn't meant to affect.
            levels[m] = stored if _LEVEL_INDEX.get(stored, 0) > _LEVEL_INDEX.get(legacy, 0) else legacy

    return {
        "bypass": False,
        "admin": admin,
        "readonly": readonly,
        "no_member": False,
        "role": row.get("books_role") or "",
        # Company admins implicitly hold every module.
        "mods": mods,
        "levels": levels,
    }


def can_read(doctype: str, user: str | None = None) -> bool:
    # Delegates to _can_at_level (View threshold) instead of the raw mods
    # boolean, so an explicit lvl_<module>="None" (once levels_customized)
    # actually blocks read access -- same fix as require_module() below and
    # the frontend's can(). Additive for untouched members, so no behavior
    # change for anyone who hasn't used the granular dropdown.
    return _can_at_level(doctype, "View", user)


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


def _can_at_level(doctype: str, threshold: str, user: str | None = None) -> bool:
    """Granular check: does the caller hold at least `threshold` (one of
    LEVELS) on the module gating `doctype`? Unmapped doctypes fall back to
    the legacy behavior -- allowed for View, allowed for anything else
    unless the caller is read-only/unmapped -- so lookups and non-sensitive
    doctypes keep working exactly as before."""
    m = _membership(user or frappe.session.user)
    if m["admin"]:
        return True
    mod = module_for(doctype)
    if mod is None:
        if threshold == "View":
            return True
        return not (m["no_member"] or m["readonly"])
    return _level_at_least(m["levels"].get(mod, "None"), threshold)


def can_create(doctype: str, user: str | None = None) -> bool:
    return _can_at_level(doctype, "Create", user)


def can_edit(doctype: str, user: str | None = None) -> bool:
    return _can_at_level(doctype, "Edit", user)


def can_delete(doctype: str, user: str | None = None) -> bool:
    """"Delete"-level check. For SUBMITTABLE_DOCTYPES this gates the
    document's cancel/void action, not physical row deletion -- see
    SUBMITTABLE_DOCTYPES docstring."""
    return _can_at_level(doctype, "Delete", user)


def _deny(doctype: str, action: str, threshold: str, user: str):
    m = _membership(user)
    if threshold != "View" and m["readonly"] and not m["admin"] and not m["no_member"]:
        msg = _("Your role ({0}) is read-only — you can't modify {1}.").format(
            m["role"] or "Books Viewer", doctype)
    else:
        mod = module_for(doctype)
        if mod:
            have = m["levels"].get(mod, "None")
            msg = _("Your {0} access ({1}) doesn't allow you to {2} {3}.").format(
                mod, have, action, doctype)
        else:
            msg = _("You don't have permission to {0} {1}.").format(action, doctype)
    frappe.throw(msg, frappe.PermissionError)


def assert_can(doctype: str, action: str = "read", user: str | None = None):
    """Raise frappe.PermissionError unless the caller may perform `action`
    (read | write | create | delete | submit | cancel) on `doctype`.

    Routes through the granular lvl_<module> levels via _ACTION_LEVEL. Every
    action except "delete" maps to the same threshold ("View" or "Edit") the
    old can_read/can_write boolean checks enforced, so existing call sites
    behave identically. "delete" now requires the new "Delete" tier -- the
    one real behavior change this phase introduces, and only for the
    generic delete_doc endpoint, which is the sole caller using it today."""
    user = user or frappe.session.user
    if user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    threshold = _ACTION_LEVEL.get(action, "Edit")
    if not _can_at_level(doctype, threshold, user):
        _deny(doctype, action, threshold, user)


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
    # Level-aware (was: raw mods boolean, which ignored an explicit
    # lvl_<module>="None" set via the granular Permission Levels dropdown).
    # Threshold is "Edit" for write calls, "View" for read calls -- additive
    # for untouched members (mirrors the old boolean), authoritative once
    # levels_customized is set for this member.
    threshold = "Edit" if write else "View"
    if not _level_at_least(m["levels"].get(module, "None"), threshold):
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