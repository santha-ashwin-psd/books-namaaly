from __future__ import annotations
"""
Multi-tenant data isolation.

Wires into Frappe's permission system so every list/get for a transactional
doctype is filtered by the user's company, and every save is rejected if the
document's company doesn't match the user's.

The permission_query_conditions hook injects a SQL WHERE clause into every
query Frappe runs against a doctype. has_permission is checked on individual
docs (the latter is the safety net for doc.get(), which doesn't go through
permission_query_conditions).
"""
import frappe


# Roles that bypass tenancy entirely (system-level admins).
_BYPASS_ROLES = {"Administrator", "System Manager"}


def _is_bypass(user: str) -> bool:
    if user == "Administrator":
        return True
    roles = set(frappe.get_roles(user))
    return bool(roles & _BYPASS_ROLES)


def get_user_company(user: str | None = None) -> str | None:
    """Return the Books Company name the user belongs to, or None."""
    user = user or frappe.session.user
    if not user or user in ("Guest", ""):
        return None
    if _is_bypass(user):
        return None  # bypass = no filter applied
    return frappe.db.get_value("Books Company Member", {"user": user}, "company")


def _meta_has_company(doctype: str) -> bool:
    """True if the doctype has a `company` field (Link or Data)."""
    try:
        meta = frappe.get_meta(doctype)
    except Exception:
        return False
    return bool(meta.has_field("company"))


def permission_query_conditions(user: str | None = None, doctype: str | None = None) -> str:
    """Inject a SQL WHERE fragment so users only see rows for their own company.

    Returns an empty string when:
      - The user is a system bypass role
      - The user has no company membership (defensive: see nothing rather than everything)
      - The doctype has no `company` field (nothing to filter on)

    Frappe calls this with (user) only — but we accept doctype for direct testing.
    """
    user = user or frappe.session.user
    if _is_bypass(user):
        return ""

    company = get_user_company(user)
    if not company:
        # Defensive default: an unmapped session-user sees nothing.
        return "1=0"

    # When called without `doctype`, Frappe injects this fragment via callback;
    # the actual doctype is determined by the call site. We can't resolve it
    # here, so return the generic fragment — Frappe wraps it in the right table alias.
    safe_company = frappe.db.escape(company)
    return f"`company` = {safe_company}"


def has_permission(doc, ptype: str = "read", user: str | None = None) -> bool | None:
    """Per-document tenancy check. Returning None means "no opinion" (let other
    permission hooks decide); True/False is decisive."""
    user = user or frappe.session.user
    if _is_bypass(user):
        return None

    # Read-only roles (Books Viewer) may view but never write/create/delete/
    # submit/cancel — blocks any permission-checked path (e.g. frappe.client.*).
    if ptype in ("write", "create", "delete", "submit", "cancel"):
        try:
            from zoho_books_clone.utils.access import is_readonly
            if is_readonly(user):
                return False
        except Exception:
            pass

    company = get_user_company(user)
    if not company:
        return False

    doc_company = getattr(doc, "company", None)
    if doc_company is None:
        return None  # doctype has no company field — no opinion
    return doc_company == company


def assert_doc_in_user_company(doc):
    """Raise PermissionError if the doc's company isn't the user's company.
    Called from the central validator on save/submit. No-op for bypass roles."""
    user = frappe.session.user
    if _is_bypass(user):
        return

    doc_company = getattr(doc, "company", None)
    if not doc_company:
        return  # _check_company in central_validator already enforces presence

    user_company = get_user_company(user)
    if not user_company:
        frappe.throw(
            "Your user is not linked to any Books Company. Contact your administrator.",
            frappe.PermissionError,
        )
    if doc_company != user_company:
        frappe.throw(
            f"You cannot save this {doc.doctype} for company '{doc_company}' — "
            f"your account belongs to '{user_company}'.",
            frappe.PermissionError,
        )


# ── Per-doctype query condition builders (for hooks.py wiring) ──────────────
# Frappe's permission_query_conditions hook is keyed by doctype, so we register
# a thin wrapper per doctype that calls the generic implementation.

def _make_qc(doctype: str):
    def _qc(user=None):
        if not _meta_has_company(doctype):
            return ""
        return permission_query_conditions(user=user)
    _qc.__name__ = f"qc_{doctype.lower().replace(' ', '_')}"
    return _qc


qc_sales_invoice    = _make_qc("Sales Invoice")
qc_purchase_invoice = _make_qc("Purchase Invoice")
qc_payment_entry    = _make_qc("Payment Entry")
qc_journal_entry    = _make_qc("Journal Entry")
qc_credit_note      = _make_qc("Credit Note")
qc_sales_order      = _make_qc("Sales Order")
qc_purchase_order   = _make_qc("Purchase Order")
qc_quotation        = _make_qc("Quotation")
qc_account          = _make_qc("Account")
qc_cost_center      = _make_qc("Cost Center")
qc_warehouse        = _make_qc("Warehouse")
qc_stock_entry      = _make_qc("Stock Entry")
qc_bank_account     = _make_qc("Bank Account")
qc_bank_transaction = _make_qc("Bank Transaction")
qc_expense          = _make_qc("Expense")
qc_expense_claim    = _make_qc("Expense Claim")


# ── Per-doctype has_permission wrappers ─────────────────────────────────────

def _make_hp(_doctype: str):
    def _hp(doc, ptype="read", user=None):
        return has_permission(doc, ptype=ptype, user=user)
    return _hp


hp_sales_invoice    = _make_hp("Sales Invoice")
hp_purchase_invoice = _make_hp("Purchase Invoice")
hp_payment_entry    = _make_hp("Payment Entry")
hp_journal_entry    = _make_hp("Journal Entry")
hp_credit_note      = _make_hp("Credit Note")
hp_sales_order      = _make_hp("Sales Order")
hp_purchase_order   = _make_hp("Purchase Order")
hp_quotation        = _make_hp("Quotation")
hp_account          = _make_hp("Account")
hp_cost_center      = _make_hp("Cost Center")
hp_warehouse        = _make_hp("Warehouse")
hp_stock_entry      = _make_hp("Stock Entry")
hp_bank_account     = _make_hp("Bank Account")
hp_bank_transaction = _make_hp("Bank Transaction")
hp_expense          = _make_hp("Expense")
hp_expense_claim    = _make_hp("Expense Claim")


# ── Master doctypes: Customer, Supplier, Item, Contact ──────────────────────
# These have no native `company` field in Frappe's schema, so we use a custom
# `books_company` field seeded by install.py for company-scoped isolation.

def _qc_books_company(user=None):
    """Permission query condition for doctypes using `books_company` instead of `company`."""
    user = user or frappe.session.user
    if _is_bypass(user):
        return ""
    company = get_user_company(user)
    if not company:
        return "1=0"
    safe_company = frappe.db.escape(company)
    # Allow records with no books_company set (legacy/unseeded data) to remain visible
    # so existing records are not suddenly hidden after the migration.
    return f"(`books_company` = {safe_company} OR `books_company` IS NULL OR `books_company` = '')"


def _hp_books_company(doc, ptype="read", user=None):
    """Per-document tenancy check for doctypes using `books_company`."""
    user = user or frappe.session.user
    if _is_bypass(user):
        return None
    company = get_user_company(user)
    if not company:
        return False
    doc_company = getattr(doc, "books_company", None)
    if not doc_company:
        return None  # unseeded legacy record — no opinion, allow
    return doc_company == company


def _default_books_company() -> str | None:
    """Resolve a company to stamp when the user has no member mapping
    (e.g. bypass-role users in a single-company setup)."""
    return (
        frappe.db.get_single_value("Books Settings", "default_company")
        or frappe.db.get_value("Books Company", {}, "name")
        or None
    )


def auto_stamp_books_company(doc, method=None):
    """
    doc_events before_insert handler.
    Stamps `books_company` with the current user's company so every new
    Customer / Supplier / Item / Contact is automatically isolated to the
    right company. Bypass-role users (Books Admin / System Manager) have no
    member mapping, so we fall back to the default/sole company — otherwise
    the record would be left unscoped and hidden by the company-filtered list.
    """
    if getattr(doc, "books_company", None):
        return  # already set (e.g. sent by UI or re-insertion)
    company = get_user_company(frappe.session.user) or _default_books_company()
    if company:
        doc.books_company = company


qc_customer = lambda user=None: _qc_books_company(user)  # noqa: E731
qc_supplier = lambda user=None: _qc_books_company(user)  # noqa: E731
qc_item     = lambda user=None: _qc_books_company(user)  # noqa: E731
qc_contact  = lambda user=None: _qc_books_company(user)  # noqa: E731

hp_customer = lambda doc, ptype="read", user=None: _hp_books_company(doc, ptype, user)  # noqa: E731
hp_supplier = lambda doc, ptype="read", user=None: _hp_books_company(doc, ptype, user)  # noqa: E731
hp_item     = lambda doc, ptype="read", user=None: _hp_books_company(doc, ptype, user)  # noqa: E731
hp_contact  = lambda doc, ptype="read", user=None: _hp_books_company(doc, ptype, user)  # noqa: E731


def auto_stamp_company(doc, method=None):
    """doc_events before_insert handler for manufacturing DocTypes.
    Stamps `company` from the user's Books Company membership when the field
    is empty — ensures multi-tenant isolation even on API-created records.
    Bypass users (System Manager / Administrator) get the default company."""
    if getattr(doc, "company", None):
        return
    company = get_user_company(frappe.session.user)
    if not company and _is_bypass(frappe.session.user):
        company = (
            frappe.db.get_single_value("Books Settings", "default_company")
            or frappe.db.get_value("Company", {}, "name")
        )
    if company:
        doc.company = company


# ── Manufacturing DocTypes (use the `company` field like transactional docs) ─

qc_bom              = _make_qc("BOM")
qc_work_order       = _make_qc("Work Order")
qc_production_plan  = _make_qc("Production Plan")
qc_job_card         = _make_qc("Job Card")
qc_material_request = _make_qc("Material Request")
qc_packing_slip     = _make_qc("Packing Slip")

hp_bom              = _make_hp("BOM")
hp_work_order       = _make_hp("Work Order")
hp_production_plan  = _make_hp("Production Plan")
hp_job_card         = _make_hp("Job Card")
hp_material_request = _make_hp("Material Request")
hp_packing_slip     = _make_hp("Packing Slip")

# ── Assets (uses the `company` field like Manufacturing/transactional docs) ─

qc_asset = _make_qc("Asset")
hp_asset = _make_hp("Asset")

# ── Asset Category (master record — uses `books_company`, like Customer/Item) ─
# Unlike Asset, Asset Category has no native `company` field: one category can
# hold per-company accounting rows in its child table, but the category itself
# is a shared master, so it's isolated the same way as Customer/Supplier/Item/Contact.

qc_asset_category = lambda user=None: _qc_books_company(user)  # noqa: E731
hp_asset_category  = lambda doc, ptype="read", user=None: _hp_books_company(doc, ptype, user)  # noqa: E731

# ── Asset sub-doctypes with their own `company` field ────────────────────────
# Depreciation Schedule is a child table (istable=1) of Asset — no independent
# list/get access, so it inherits isolation from its parent and needs no entry here.

qc_asset_disposal         = _make_qc("Asset Disposal")
qc_asset_repair           = _make_qc("Asset Repair")
qc_asset_movement         = _make_qc("Asset Movement")
qc_asset_value_adjustment = _make_qc("Asset Value Adjustment")

hp_asset_disposal         = _make_hp("Asset Disposal")
hp_asset_repair           = _make_hp("Asset Repair")
hp_asset_movement         = _make_hp("Asset Movement")
hp_asset_value_adjustment = _make_hp("Asset Value Adjustment")


# ── Maintenance Log: no `company` field, only an `asset` Link ───────────────
# Filtered via subquery against Asset.company instead of a direct column match.

def qc_maintenance_log(user: str | None = None) -> str:
    user = user or frappe.session.user
    if _is_bypass(user):
        return ""
    company = get_user_company(user)
    if not company:
        return "1=0"
    safe_company = frappe.db.escape(company)
    return (
        "`asset` in (select `name` from `tabAsset` "
        f"where `company` = {safe_company})"
    )


def hp_maintenance_log(doc, ptype: str = "read", user: str | None = None) -> bool | None:
    user = user or frappe.session.user
    if _is_bypass(user):
        return None
    if ptype in ("write", "create", "delete", "submit", "cancel"):
        try:
            from zoho_books_clone.utils.access import is_readonly
            if is_readonly(user):
                return False
        except Exception:
            pass
    company = get_user_company(user)
    if not company:
        return False
    asset = getattr(doc, "asset", None)
    if not asset:
        return None  # no opinion — let central_validator catch missing asset on save
    asset_company = frappe.db.get_value("Asset", asset, "company")
    if not asset_company:
        return None
    return asset_company == company