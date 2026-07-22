from __future__ import annotations
"""
Administration API — users, roles, profile, notifications, audit log.
All endpoints require an authenticated session (allow_guest=False by default).
"""
import secrets
import string

import frappe
from frappe import _
from frappe.utils import today, flt
from frappe.utils.password import update_password, check_password


BOOKS_ROLES = ("Books Admin", "Books Manager", "Accountant", "Books Viewer")
MODULE_FIELDS = (
    "mod_invoices", "mod_bills", "mod_payments", "mod_banking",
    "mod_inventory", "mod_accounts", "mod_reports", "mod_customers",
    "mod_taxes", "mod_admin",
)


def _is_global_admin(user: str | None = None) -> bool:
    """True for Administrator or System Manager — these users bypass the
    Books-Company-Member tenant check and operate against the first / default company."""
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    return "System Manager" in set(frappe.get_roles(user))


def _resolve_company_for(user: str | None = None) -> str:
    """Resolve the effective company for the given user. For global admins (no
    Books Company Member row required), falls back to Books Settings default_company,
    then to the first Books Company that exists. Returns "" if none can be resolved."""
    user = user or frappe.session.user
    co = frappe.db.get_value("Books Company Member", {"user": user}, "company")
    if co:
        return co
    if _is_global_admin(user):
        try:
            co = frappe.db.get_single_value("Books Settings", "default_company") or ""
        except Exception:
            co = ""
        if co and frappe.db.exists("Books Company", co):
            return co
        # Last-resort: any Books Company that exists.
        rows = frappe.get_all("Books Company", fields=["name"], limit=1, ignore_permissions=True)
        return rows[0]["name"] if rows else ""
    return ""


def _require_admin():
    """Allow Books Admin, System Manager, or Administrator."""
    if frappe.session.user == "Administrator":
        return
    roles = set(frappe.get_roles(frappe.session.user))
    if roles & {"System Manager", "Books Admin"}:
        return
    # Books Manager can read but not invite — see _require_company_admin
    frappe.throw(_("You do not have permission to perform this action"), frappe.PermissionError)


def _require_company_admin() -> str:
    """Stricter check: must be flagged as company admin in Books Company Member,
    or be a global admin (Administrator / System Manager). Returns the company name."""
    user = frappe.session.user
    if _is_global_admin(user):
        co = _resolve_company_for(user)
        if not co:
            frappe.throw(_("No Books Company exists yet. Create one first."), frappe.PermissionError)
        # Auto-create the member row so the global admin appears in the users list
        if user not in ("Administrator", "Guest") and not frappe.db.exists("Books Company Member", {"user": user}):
            try:
                m = frappe.new_doc("Books Company Member")
                m.user = user
                m.company = co
                m.books_role = "Books Admin"
                m.is_company_admin = 1
                m.invited_by = ""
                for f in MODULE_FIELDS:
                    m.set(f, 1)
                m.insert(ignore_permissions=True)
                frappe.db.commit()
            except Exception:
                pass
        return co
    row = frappe.db.get_value(
        "Books Company Member",
        {"user": user},
        ["company", "is_company_admin", "books_role"],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Your user is not linked to any Books Company."), frappe.PermissionError)
    if not (row.is_company_admin or row.books_role == "Books Admin"):
        frappe.throw(_("Only the company admin can perform this action."), frappe.PermissionError)
    return row.company


def _gen_temp_password(n: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))


# ─── Users (scoped to admin's company) ───────────────────────────────────────

def _company_member_row(user: str) -> dict | None:
    return frappe.db.get_value(
        "Books Company Member",
        {"user": user},
        ["name", "company", "books_role", "is_company_admin", *MODULE_FIELDS],
        as_dict=True,
    )


@frappe.whitelist()
def get_users_list():
    """Return users that belong to the current admin's company."""
    company = _require_company_admin()
    members = frappe.get_all(
        "Books Company Member",
        filters={"company": company},
        fields=["user", "books_role", "is_company_admin", "invited_by", "joined_on", *MODULE_FIELDS],
        ignore_permissions=True,
        order_by="joined_on asc",
        limit=500,
    )
    if not members:
        return []

    # The owner is the member with a blank invited_by (was never invited — created the company).
    # Fall back to the earliest joined_on if everyone has an invited_by value.
    owner_users = {m["user"] for m in members if not (m.get("invited_by") or "").strip()}
    if not owner_users:
        owner_users = {members[0]["user"]}  # oldest member by joined_on asc

    user_names = [m["user"] for m in members]
    user_rows = {
        u["name"]: u
        for u in frappe.get_all(
            "User",
            filters=[["name", "in", user_names]],
            fields=["name", "full_name", "email", "enabled", "last_login",
                    "creation", "user_image"],
            ignore_permissions=True,
        )
    }

    out = []
    for m in members:
        u = user_rows.get(m["user"], {})
        out.append({
            "name": m["user"],
            "email": m["user"],
            "full_name": u.get("full_name") or "",
            "user_image": u.get("user_image") or "",
            "enabled": bool(u.get("enabled")),
            "last_login": u.get("last_login"),
            "creation": u.get("creation"),
            "books_role": m["books_role"],
            "is_company_admin": bool(m["is_company_admin"]),
            "is_owner": m["user"] in owner_users,
            "modules": {f.removeprefix("mod_"): bool(m[f]) for f in MODULE_FIELDS},
            "joined_on": m["joined_on"],
        })
    # Sort: owner first, then by joined_on
    out.sort(key=lambda r: (0 if r["is_owner"] else 1, r.get("joined_on") or ""))
    return out


@frappe.whitelist(methods=["POST"])
def invite_user(email, first_name, last_name="", role="Books Viewer", modules=None):
    """Create a new user, link them to the admin's company, and email login credentials.
    `modules` is an optional dict like {"invoices": 1, "banking": 0, ...}."""
    company = _require_company_admin()
    email = email.strip().lower()

    if frappe.db.exists("User", email):
        frappe.throw(_("User {0} already exists").format(email))

    if role not in BOOKS_ROLES:
        frappe.throw(_("Invalid role: {0}").format(role))

    if isinstance(modules, str):
        try:
            import json
            modules = json.loads(modules)
        except Exception:
            modules = {}
    modules = modules or {}

    temp_password = _gen_temp_password()

    # ── Create User
    user = frappe.new_doc("User")
    user.email = email
    user.first_name = (first_name or "").strip() or email.split("@")[0]
    user.last_name = (last_name or "").strip()
    user.user_type = "System User"
    user.send_welcome_email = 0  # we send our own via system SMTP
    user.enabled = 1
    user.new_password = temp_password
    user.append("roles", {"role": role})
    user.insert(ignore_permissions=True)

    # ── Link to company
    member = frappe.new_doc("Books Company Member")
    member.user = email
    member.company = company
    member.books_role = role
    member.is_company_admin = 1 if role == "Books Admin" else 0
    member.invited_by = frappe.session.user

    if role == "Books Admin":
        for f in MODULE_FIELDS:
            member.set(f, 1)
    else:
        # Apply requested module toggles, defaulting to the doctype's default for unspecified fields
        for f in MODULE_FIELDS:
            key = f.removeprefix("mod_")
            if key in modules:
                member.set(f, 1 if int(modules[key]) else 0)

    member.insert(ignore_permissions=True)

    # Per-user company default
    try:
        frappe.defaults.set_user_default("company", company, user=email)
    except Exception:
        pass

    frappe.db.commit()

    # ── Send invite email via system SMTP
    _send_invite_email(email, user.first_name, company, temp_password, role)

    return {"success": True, "user": email, "company": company, "role": role}


def _send_invite_email(email: str, first_name: str, company: str, temp_password: str, role: str):
    from zoho_books_clone.utils.email_system import send_system_email
    site_url = frappe.utils.get_url()
    html = f"""
<div style="font-family:'DM Sans',sans-serif;max-width:520px;margin:0 auto;padding:32px 24px;background:#fff">
  <h2 style="color:#1A237E;font-size:22px;margin-bottom:8px">Welcome to Books, {first_name}!</h2>
  <p style="color:#555;line-height:1.6">
    You've been invited to join <b>{company}</b> on Books with the role <b>{role}</b>.
  </p>
  <div style="background:#F5F7FA;border-radius:10px;padding:20px;margin:20px 0">
    <div style="font-size:13px;color:#666;margin-bottom:6px">Sign in URL</div>
    <div style="font-size:15px;color:#0D1117;margin-bottom:14px"><a href="{site_url}/login" style="color:#3949AB">{site_url}/login</a></div>
    <div style="font-size:13px;color:#666;margin-bottom:6px">Email</div>
    <div style="font-size:15px;color:#0D1117;margin-bottom:14px"><b>{email}</b></div>
    <div style="font-size:13px;color:#666;margin-bottom:6px">Temporary password</div>
    <div style="font-size:18px;color:#1A237E;letter-spacing:2px"><b>{temp_password}</b></div>
  </div>
  <p style="color:#555;font-size:14px;line-height:1.6">
    Please sign in and change your password from <b>Profile → Change Password</b> immediately.
  </p>
</div>"""
    send_system_email(
        to=email,
        subject=f"You've been invited to {company} on Books",
        html=html,
        text_fallback=f"You've been invited to {company} on Books. Sign in at {site_url}/login with email {email} and temporary password {temp_password}. Please change your password after signing in.",
    )


@frappe.whitelist(methods=["POST"])
def update_user_role(user, role):
    """Replace all Books roles on a user with the given role.
    Restricted to users in the admin's company."""
    company = _require_company_admin()
    if role not in BOOKS_ROLES:
        frappe.throw(_("Invalid role"))

    member_name = frappe.db.get_value("Books Company Member", {"user": user, "company": company}, "name")
    if not member_name:
        frappe.throw(_("User {0} is not part of your company.").format(user))

    member = frappe.get_doc("Books Company Member", member_name)
    member.books_role = role
    if role == "Books Admin":
        member.is_company_admin = 1
        for f in MODULE_FIELDS:
            member.set(f, 1)
    member.save(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True}


@frappe.whitelist(methods=["POST"])
def set_user_permissions(user, modules):
    """Set module-level access toggles for a user in the admin's company.
    `modules` is a dict like {'invoices': 1, 'banking': 0}."""
    company = _require_company_admin()

    if isinstance(modules, str):
        import json
        modules = json.loads(modules)
    modules = modules or {}

    member_name = frappe.db.get_value("Books Company Member", {"user": user, "company": company}, "name")
    if not member_name:
        frappe.throw(_("User {0} is not part of your company.").format(user))

    member = frappe.get_doc("Books Company Member", member_name)
    if member.books_role == "Books Admin":
        frappe.throw(_("Books Admin always has full module access; toggles cannot be set."))

    for f in MODULE_FIELDS:
        key = f.removeprefix("mod_")
        if key in modules:
            member.set(f, 1 if int(modules[key]) else 0)

    member.save(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True}


@frappe.whitelist(methods=["POST"])
def toggle_user_active(user, enabled):
    """Enable or disable a user account (must be in admin's company)."""
    company = _require_company_admin()
    if user in ("Administrator", "Guest"):
        frappe.throw(_("Cannot disable this user"))
    if not frappe.db.exists("Books Company Member", {"user": user, "company": company}):
        frappe.throw(_("User {0} is not part of your company.").format(user))
    enabled_int = 1 if str(enabled).lower() in ("1", "true") else 0
    frappe.db.set_value("User", user, "enabled", enabled_int)
    frappe.db.commit()
    return {"success": True}


@frappe.whitelist(methods=["POST"])
def remove_user_from_company(user):
    """Remove a user from the admin's company (deletes the membership row, disables the user)."""
    company = _require_company_admin()
    if user == frappe.session.user:
        frappe.throw(_("You cannot remove yourself."))

    member_name = frappe.db.get_value("Books Company Member", {"user": user, "company": company}, "name")
    if not member_name:
        frappe.throw(_("User {0} is not part of your company.").format(user))

    frappe.delete_doc("Books Company Member", member_name, ignore_permissions=True, force=True)
    frappe.db.set_value("User", user, "enabled", 0)
    frappe.db.commit()
    return {"success": True}


# ─── Backwards-compat aliases (the live SPA was built against earlier names) ──

@frappe.whitelist()
def get_company_members():
    """Alias for get_users_list — kept so the existing Team Members page works."""
    return get_users_list()


@frappe.whitelist(methods=["POST"])
def invite_member(email, first_name, last_name="", role="Books Viewer", password=None, modules=None):
    """Alias for invite_user. The legacy SPA also passes a `password` field, which we ignore
    (we always generate a temp password and email it via system SMTP). All other args pass through."""
    return invite_user(email=email, first_name=first_name, last_name=last_name,
                       role=role, modules=modules)


@frappe.whitelist(methods=["POST"])
def remove_member(user_email):
    """Alias for remove_user_from_company — legacy SPA uses `user_email` arg name."""
    return remove_user_from_company(user=user_email)


# ─── Profile ──────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_profile():
    """Return the current user's profile fields."""
    user = frappe.session.user
    doc = frappe.get_doc("User", user)
    return {
        "email": doc.email,
        "first_name": doc.first_name or "",
        "last_name": doc.last_name or "",
        "full_name": doc.full_name or "",
        "phone": doc.phone or "",
        "mobile_no": doc.mobile_no or "",
        "user_image": doc.user_image or "",
        "language": doc.language or "en",
        "time_zone": doc.time_zone or "",
    }


@frappe.whitelist()
def update_profile(first_name, last_name="", phone="", mobile_no=""):
    """Update the current user's profile."""
    user = frappe.session.user
    doc = frappe.get_doc("User", user)
    doc.first_name = first_name.strip()
    doc.last_name = (last_name or "").strip()
    doc.phone = phone or ""
    doc.mobile_no = mobile_no or ""
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True, "full_name": doc.full_name}


@frappe.whitelist()
def change_password(old_password, new_password):
    """Change the current user's password after verifying the old one."""
    user = frappe.session.user
    try:
        check_password(user, old_password)
    except Exception:
        frappe.throw(_("Current password is incorrect"))
    if len(new_password) < 8:
        frappe.throw(_("New password must be at least 8 characters"))
    update_password(user, new_password)
    frappe.db.commit()
    return {"success": True}


# ─── Notifications ────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_notifications():
    """Return a list of actionable notifications for the current user."""
    notifs = []

    try:
        member = frappe.db.get_value(
            "Books Company Member",
            {"user": frappe.session.user},
            "company",
        )
        company = member or frappe.db.get_single_value("Books Settings", "default_company") or ""
    except Exception:
        company = ""

    def _f(base):
        return base + ([["company", "=", company]] if company else [])

    # Overdue Sales Invoices
    try:
        for inv in frappe.get_all(
            "Sales Invoice",
            filters=_f([["docstatus","=",1],["outstanding_amount",">",0],["due_date","<",today()]]),
            fields=["name","customer_name","outstanding_amount","due_date"],
            limit=5, ignore_permissions=True,
        ):
            notifs.append({
                "type":"overdue_invoice","icon":"alert","color":"#C92A2A","bg":"#FFF5F5",
                "title":"Overdue Invoice",
                "body":f"{inv['name']} — {inv['customer_name']} — ₹{flt(inv['outstanding_amount']):,.2f}",
                "link":f"#/invoices/{inv['name']}","date":str(inv["due_date"]),
            })
    except Exception:
        pass

    # Bills due today or overdue
    try:
        for bill in frappe.get_all(
            "Purchase Invoice",
            filters=_f([["docstatus","=",1],["outstanding_amount",">",0],["due_date","<=",today()]]),
            fields=["name","supplier_name","outstanding_amount","due_date"],
            limit=5, ignore_permissions=True,
        ):
            notifs.append({
                "type":"bill_due","icon":"purchase","color":"#E67700","bg":"#FFF8F0",
                "title":"Bill Due",
                "body":f"{bill['name']} — {bill['supplier_name']} — ₹{flt(bill['outstanding_amount']):,.2f}",
                "link":"#/purchases","date":str(bill["due_date"]),
            })
    except Exception:
        pass

    # Reorder alerts
    try:
        for r in frappe.db.sql("""
            SELECT b.item_code, b.actual_qty, i.reorder_level
            FROM `tabBin` b JOIN `tabItem` i ON i.name=b.item_code
            WHERE i.reorder_level > 0 AND b.actual_qty <= i.reorder_level LIMIT 3
        """, as_dict=True):
            notifs.append({
                "type":"reorder","icon":"bell","color":"#1971C2","bg":"#E7F5FF",
                "title":"Low Stock Alert",
                "body":f"{r['item_code']} — Qty:{flt(r['actual_qty']):.0f} (Reorder at {flt(r['reorder_level']):.0f})",
                "link":"#/inventory/reorder-alerts","date":today(),
            })
    except Exception:
        pass

    return notifs


# ─── Audit Log ────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_audit_log(page=0, page_len=50):
    """Return recent document activity from Frappe's Activity Log."""
    _require_admin()
    page = int(page)
    page_len = min(int(page_len), 200)

    logs = frappe.db.sql("""
        SELECT
            al.name, al.user, al.creation,
            al.reference_doctype as doctype,
            al.reference_name as doc_name,
            al.operation,
            al.status
        FROM `tabActivity Log` al
        WHERE al.reference_doctype IN (
            'Sales Invoice','Purchase Invoice','Customer','Supplier',
            'Payment Entry','Journal Entry','Sales Order',
            'Purchase Order','Credit Note','Stock Entry'
        )
        ORDER BY al.creation DESC
        LIMIT %(len)s OFFSET %(off)s
    """, {"len": page_len, "off": page * page_len}, as_dict=True)

    return logs


# ─── Company Settings ─────────────────────────────────────────────────────────

@frappe.whitelist()
def get_company_settings():
    """Return all company settings from Books Company (profile + email/reminder flags)
    and invoice_prefix / auto_reconcile from Books Settings."""
    company_name = _resolve_company_for()

    result = {
        "default_company": company_name,
        "default_currency": "INR",
        "fiscal_year_start_month": "April",
        "invoice_prefix": "INV",
        "gstin": "",
        "gst_state": "",
        "logo_url": "",
        "pdf_template": "classic",
        "brand_color": "#1a6ef7",
        "company_logo": "",
        "company_address": "",
        "company_city": "",
        "company_state": "",
        "company_pincode": "",
        "company_phone": "",
        "company_email": "",
        "company_website": "",
        "bank_name": "",
        "bank_branch": "",
        "bank_account_no": "",
        "bank_ifsc": "",
        # Reminder / auto-send — now per-company on Books Company
        "auto_send_invoice": 0,
        "send_payment_reminders": 0,
        "reminder_days_before": 3,
        "reminder_days_after": 7,
        "auto_reconcile": 0,
        "lock_date": "",
    }

    # All company-specific fields (including reminder/email flags) come from Books Company
    if company_name and frappe.db.exists("Books Company", company_name):
        try:
            co = frappe.get_doc("Books Company", company_name)
            result["default_currency"]        = co.currency or "INR"
            result["fiscal_year_start_month"] = co.fiscal_year_start_month or "April"
            result["gstin"]                   = co.gstin or ""
            result["gst_state"]               = co.gst_state or ""
            result["logo_url"]                = co.logo_url or ""
            result["pdf_template"]            = co.pdf_template or "classic"
            result["brand_color"]             = co.brand_color or "#1a6ef7"
            result["company_logo"]            = co.company_logo or ""
            result["company_address"]         = co.address_line or ""
            result["company_city"]            = co.city or ""
            result["company_state"]           = co.state or ""
            result["company_pincode"]         = co.pincode or ""
            result["company_phone"]           = co.phone or ""
            result["company_email"]           = co.email or ""
            result["company_website"]         = co.website or ""
            # Per-company email / reminder flags (new fields on Books Company)
            result["auto_send_invoice"]       = int(co.auto_send_invoice or 0)
            result["send_payment_reminders"]  = int(co.send_payment_reminders or 0)
            result["reminder_days_before"]    = int(co.reminder_days_before or 3)
            result["reminder_days_after"]     = int(co.reminder_days_after or 7)
            # Period lock — stored on Books Company, drives central_validator
            result["lock_date"]               = str(co.lock_date or "")
        except Exception:
            pass

    # Non-company-specific settings still live in Books Settings
    try:
        settings = frappe.get_doc("Books Settings", "Books Settings")
        result["invoice_prefix"] = settings.get("invoice_prefix") or "INV"
        result["auto_reconcile"] = settings.get("auto_reconcile") or 0
    except Exception:
        pass

    # Default Bank Account — shown on printed invoices. Bank Account isn't
    # reliably linked back to Books Company, so just take whichever account
    # is flagged default (falling back to the first one that exists).
    try:
        bank_name = frappe.db.get_value("Bank Account", {"is_default": 1}, "name")
        if not bank_name:
            bank_name = frappe.db.get_value("Bank Account", {}, "name", order_by="creation asc")
        if bank_name:
            bank = frappe.get_doc("Bank Account", bank_name)
            result["bank_name"]       = bank.bank_name or ""
            result["bank_branch"]     = bank.branch or ""
            result["bank_account_no"] = bank.account_number or ""
            result["bank_ifsc"]       = bank.ifsc_code or ""
    except Exception:
        pass

    return result


@frappe.whitelist()
def save_company_settings(**kwargs):
    """Save all company-specific fields (including email/reminder flags) to Books Company;
    non-company settings (invoice_prefix, auto_reconcile) go to Books Settings."""
    _require_admin()
    company_name = _resolve_company_for()

    # Save all company-specific fields to Books Company
    if company_name and frappe.db.exists("Books Company", company_name):
        try:
            co = frappe.get_doc("Books Company", company_name)
            if "default_currency" in kwargs:
                co.currency = kwargs["default_currency"]
            if "fiscal_year_start_month" in kwargs:
                co.fiscal_year_start_month = kwargs["fiscal_year_start_month"]
            if "gstin" in kwargs:
                co.gstin = kwargs["gstin"]
            if "gst_state" in kwargs:
                co.gst_state = kwargs["gst_state"]
            if "logo_url" in kwargs:
                co.logo_url = kwargs["logo_url"]
            if "pdf_template" in kwargs:
                co.pdf_template = kwargs["pdf_template"]
            if "brand_color" in kwargs:
                co.brand_color = kwargs["brand_color"]
            if "company_logo" in kwargs:
                co.company_logo = kwargs["company_logo"]
            if "company_address" in kwargs:
                co.address_line = kwargs["company_address"]
            if "company_city" in kwargs:
                co.city = kwargs["company_city"]
            if "company_state" in kwargs:
                co.state = kwargs["company_state"]
            if "company_pincode" in kwargs:
                co.pincode = kwargs["company_pincode"]
            if "company_phone" in kwargs:
                co.phone = kwargs["company_phone"]
            if "company_email" in kwargs:
                co.email = kwargs["company_email"]
            if "company_website" in kwargs:
                co.website = kwargs["company_website"]
            # Per-company email / reminder flags (now live on Books Company)
            if "auto_send_invoice" in kwargs:
                co.auto_send_invoice = int(kwargs["auto_send_invoice"] or 0)
            if "send_payment_reminders" in kwargs:
                co.send_payment_reminders = int(kwargs["send_payment_reminders"] or 0)
            if "reminder_days_before" in kwargs:
                co.reminder_days_before = int(kwargs["reminder_days_before"] or 3)
            if "reminder_days_after" in kwargs:
                co.reminder_days_after = int(kwargs["reminder_days_after"] or 7)
            # Period lock — write back to Books Company
            if "lock_date" in kwargs:
                co.lock_date = kwargs["lock_date"] or None
            co.save(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(str(e), "save_company_settings: Books Company")

    # Non-company-specific settings still live in Books Settings
    try:
        settings = frappe.get_doc("Books Settings", "Books Settings")
    except Exception:
        settings = frappe.new_doc("Books Settings")
    for f in ["invoice_prefix", "auto_reconcile"]:
        if f in kwargs:
            settings.set(f, kwargs[f])
    settings.save(ignore_permissions=True)

    frappe.db.commit()
    return {"success": True}


# ─── Company rename ──────────────────────────────────────────────────────────
#
# Why this needs its own endpoint instead of a plain field edit:
# Books Company autonames on the company_name field (autoname: "field:company_name"),
# so the docname itself IS the company name text. Editing company_name via a normal
# doc.save() does NOT rename the document — Frappe only applies "field:" autoname on
# insert, never on update — so the docname (and therefore every place that stored
# the old name) silently keeps the stale value forever, which is exactly the "edit
# doesn't stick" symptom.
#
# On top of that, most doctypes in this app store `company` as a plain Data field
# (a copied string), not a real Link to Books Company — see Purchase/Sales Invoice,
# Payment Entry, Journal Entry, Account, GL Entry, Fiscal Year, Cost Center, Bank
# Account, Warehouse, Stock Entry/Ledger, Quotation, Sales/Purchase Order, Expense,
# Credit Note, E-Way Bill, Tax Template, Expense Claim, Bin. frappe.rename_doc()
# only cascades to real Link fields (Books Company Member, Purchase Receipt,
# Delivery Note, TDS Entry, Material Request, Job Card, Packing Slip, Work Order,
# BOM, Production Plan already use a proper Link and are handled automatically).
# Every Data-field table below has to be bulk-updated by hand, or those records
# silently keep pointing at a company name that no longer exists.
_COMPANY_DATA_FIELD_DOCTYPES = [
    "Tax Template", "Expense Claim", "Credit Note", "Quotation", "E Way Bill",
    "Purchase Invoice", "Sales Invoice", "Purchase Order", "Sales Order", "Expense",
    "Warehouse", "Stock Ledger Entry", "Stock Entry", "Bin", "Payment Entry",
    "Cost Center", "Account", "General Ledger Entry", "Journal Entry",
    "Fiscal Year", "Bank Account",
]


@frappe.whitelist(methods=["POST"])
def rename_company(old_name=None, new_name=None):
    """Rename a Books Company end-to-end: renames the doc itself, then cascades
    the new name into every table that stores `company` as a plain string field
    (see _COMPANY_DATA_FIELD_DOCTYPES) plus Books Settings.default_company.
    Real Link fields to Books Company are handled by frappe.rename_doc() itself.
    """
    _require_admin()

    old_name = (old_name or "").strip()
    new_name = (new_name or "").strip()
    if not old_name or not new_name:
        frappe.throw(_("Both the current and new company name are required."))
    if old_name == new_name:
        frappe.throw(_("New name is the same as the current name."))
    if not frappe.db.exists("Books Company", old_name):
        frappe.throw(_("Company '{0}' not found.").format(old_name))
    if frappe.db.exists("Books Company", new_name):
        frappe.throw(_("A company named '{0}' already exists.").format(new_name))

    # 1) Rename the document itself. merge=False since new_name must not already
    # exist (checked above). This also cascades to genuine Link fields pointing
    # at Books Company (Delivery Note, Purchase Receipt, TDS Entry, Material
    # Request, Job Card, Packing Slip, Work Order, BOM, Production Plan,
    # Books Company Member).
    frappe.rename_doc("Books Company", old_name, new_name, force=True)

    # 2) Resync the naming field itself — rename_doc changes the docname but
    # doesn't guarantee company_name is re-saved to match on every version.
    frappe.db.set_value("Books Company", new_name, "company_name", new_name, update_modified=False)

    # 3) Bulk-fix every plain-Data "company" column across the app. Direct SQL
    # since these are just string fields, not links — no doc events need to fire.
    updated = {}
    for doctype in _COMPANY_DATA_FIELD_DOCTYPES:
        table = "tab" + doctype
        if not frappe.db.table_exists(doctype):
            continue
        frappe.db.sql(
            f"UPDATE `{table}` SET `company` = %s WHERE `company` = %s",
            (new_name, old_name),
        )
        updated[doctype] = True

    # 4) Books Settings.default_company is also a plain string, not a Link.
    # IMPORTANT: Books Settings is a Single doctype, and Frappe caches Single
    # values aggressively. A raw frappe.db.set_value() writes the row correctly
    # but does NOT reliably invalidate that cache, so frappe.client.get_value
    # (which resolveCompany() on the frontend calls) keeps serving the stale
    # old name to every page indefinitely. Go through the real document API —
    # doc.save() properly busts the cache — instead of a direct SQL write.
    if frappe.db.exists("Books Settings", "Books Settings"):
        settings_doc = frappe.get_single("Books Settings")
        settings_doc.default_company = new_name
        settings_doc.save(ignore_permissions=True)

    # Belt-and-braces: explicitly clear every cache layer that could still be
    # holding the old name, for this request's cache and any other worker's.
    frappe.clear_document_cache("Books Settings", "Books Settings")
    frappe.clear_document_cache("Books Company", new_name)
    frappe.clear_document_cache("Books Company", old_name)
    frappe.clear_cache(doctype="Books Settings")

    # 5) Frappe's own defaults system, in case anything ever set it.
    try:
        if frappe.db.get_default("company") == old_name:
            frappe.db.set_default("company", new_name)
    except Exception:
        pass

    # 6) Per-user defaults. Signup/invite flows (auth.py, admin.py) call
    # frappe.defaults.set_user_default("company", ...) to snapshot the company
    # name onto each individual user at the time they joined. That snapshot is
    # a plain string on the DefaultValue doctype, completely independent of
    # the Books Company doc, so frappe.rename_doc() above has no way to touch
    # it. Crucially, _get_company() in session.py checks THIS value FIRST —
    # before Books Company Member and before Books Settings.default_company —
    # so leaving it stale means every existing user keeps resolving to the
    # old company name forever after a rename, regardless of what the
    # frontend caches. Walk every user whose default still points at the old
    # name and re-point it via the public API (which also clears their
    # defaults cache), rather than a raw SQL write.
    try:
        stale_users = frappe.db.sql(
            """SELECT parent FROM `tabDefaultValue`
               WHERE defkey = %s AND defvalue = %s AND parenttype = %s""",
            ("company", old_name, "__default"),
            as_dict=True,
        )
        for row in stale_users:
            if row.parent:
                frappe.defaults.set_user_default("company", new_name, user=row.parent)
    except Exception:
        frappe.log_error(title="rename_company: per-user default fixup failed")

    frappe.db.commit()
    return {"success": True, "old_name": old_name, "new_name": new_name, "updated_doctypes": list(updated.keys())}




@frappe.whitelist()
def get_books_lock_date():
    """Return the Books Lock Date for the current user's resolved company.
    Uses _resolve_company_for() so Books Company Member rows take priority
    over the global Books Settings default_company fallback.
    Returns { company, lock_date } so the frontend can show the correct context.
    """
    company = _resolve_company_for()
    lock_date = ""
    if company and frappe.db.exists("Books Company", company):
        lock_date = str(frappe.db.get_value("Books Company", company, "lock_date") or "")
    return {"company": company, "lock_date": lock_date}


@frappe.whitelist(methods=["POST"])
def set_books_lock_date(lock_date=None):
    """Set or clear the Books Lock Date for the current user's resolved company.
    Pass lock_date="" or lock_date=None to clear.
    """
    _require_admin()
    company = _resolve_company_for()
    if not company or not frappe.db.exists("Books Company", company):
        frappe.throw("Could not resolve company for the current user.")
    co = frappe.get_doc("Books Company", company)
    co.lock_date = lock_date or None
    co.save(ignore_permissions=True)
    frappe.db.commit()
    return {"company": company, "lock_date": str(co.lock_date or "")}

# ─── SMTP / Email Settings (per-company) ──────────────────────────────────────

def _admin_company() -> str:
    """Return the Books Company managed by the current admin. Throws if none.
    Global admins (Administrator / System Manager) fall back via _resolve_company_for."""
    company = _resolve_company_for()
    if not company:
        frappe.throw(_("Your user is not linked to any Books Company."))
    return company


@frappe.whitelist()
def get_email_settings():
    """Backwards-compat shim — older admin UI reads `{accounts:[...]}`.
    Wraps the company's SMTP config in the legacy shape so existing pages keep rendering."""
    _require_admin()
    company = _admin_company()
    doc = frappe.get_doc("Books Company", company)
    if not (doc.smtp_enabled and doc.smtp_server and doc.smtp_login):
        return {"accounts": []}
    return {"accounts": [{
        "name": company,
        "email_id": doc.smtp_from_email or doc.smtp_login,
        "smtp_server": doc.smtp_server,
        "smtp_port": int(doc.smtp_port or 587),
        "use_tls": int(doc.smtp_use_tls or 0),
        "use_ssl": int(doc.smtp_use_ssl or 0),
        "login_id": doc.smtp_login,
        "email_account_name": company,
    }]}


@frappe.whitelist()
def get_company_smtp():
    """Return the company's SMTP settings (password redacted) for the admin UI."""
    _require_admin()
    company = _admin_company()
    doc = frappe.get_doc("Books Company", company)
    return {
        "company": company,
        "smtp_enabled": int(doc.smtp_enabled or 0),
        "smtp_server": doc.smtp_server or "",
        "smtp_port": int(doc.smtp_port or 587),
        "smtp_use_tls": int(doc.smtp_use_tls or 0),
        "smtp_use_ssl": int(doc.smtp_use_ssl or 0),
        "smtp_login": doc.smtp_login or "",
        "smtp_password_set": bool(doc.smtp_password),
        "smtp_from_email": doc.smtp_from_email or "",
        "smtp_from_name": doc.smtp_from_name or "",
    }


@frappe.whitelist(methods=["POST"])
def save_company_smtp(
    smtp_enabled=0,
    smtp_server="",
    smtp_port=587,
    smtp_use_tls=1,
    smtp_use_ssl=0,
    smtp_login="",
    smtp_password=None,
    smtp_from_email="",
    smtp_from_name="",
):
    """Persist SMTP credentials on the admin's Books Company.
    smtp_password is only updated when explicitly provided (so re-saving the form
    without re-entering the password leaves the stored one untouched)."""
    _require_admin()
    company = _admin_company()
    doc = frappe.get_doc("Books Company", company)

    doc.smtp_enabled = 1 if int(smtp_enabled or 0) else 0
    doc.smtp_server = (smtp_server or "").strip()
    doc.smtp_port = int(smtp_port or 587)
    doc.smtp_use_tls = 1 if int(smtp_use_tls or 0) else 0
    doc.smtp_use_ssl = 1 if int(smtp_use_ssl or 0) else 0
    doc.smtp_login = (smtp_login or "").strip()
    if smtp_password not in (None, ""):
        doc.smtp_password = smtp_password
    doc.smtp_from_email = (smtp_from_email or "").strip() or doc.smtp_login
    doc.smtp_from_name = (smtp_from_name or "").strip() or company

    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True, "company": company}


@frappe.whitelist(methods=["POST"])
def send_test_email(to_email, use_overrides=0, **overrides):
    """Send a test email via the company's SMTP.
    If use_overrides=1 is passed (with smtp_* fields), tests those creds without saving them."""
    _require_admin()
    from zoho_books_clone.utils.email_company import test_company_smtp

    company = _admin_company()
    overrides_dict = None
    if int(use_overrides or 0):
        overrides_dict = {
            "smtp_server":     overrides.get("smtp_server", ""),
            "smtp_port":       overrides.get("smtp_port", 587),
            "smtp_use_tls":    overrides.get("smtp_use_tls", 1),
            "smtp_use_ssl":    overrides.get("smtp_use_ssl", 0),
            "smtp_login":      overrides.get("smtp_login", ""),
            "smtp_password":   overrides.get("smtp_password", ""),
            "smtp_from_email": overrides.get("smtp_from_email", ""),
            "smtp_from_name":  overrides.get("smtp_from_name", ""),
        }

    result = test_company_smtp(to=to_email, company=company, overrides=overrides_dict)
    if not result["success"]:
        frappe.throw(result["message"])
    return result


# ─── Number Series ────────────────────────────────────────────────────────────

_NS_DOCTYPE = "Books Number Series"

def _ns_fallback():
    """Return a static list when the custom doctype doesn't exist yet."""
    defaults = [
        ("INV-", "Sales Invoice", 4),
        ("PUR-", "Purchase Invoice", 4),
        ("SO-",  "Sales Order", 4),
        ("PO-",  "Purchase Order", 4),
        ("QTN-", "Quotation", 4),
        ("PAY-", "Payment Entry", 4),
        ("JE-",  "Journal Entry", 4),
        ("EXP-", "Expense Claim", 4),
        ("STE-", "Stock Entry", 4),
    ]
    result = []
    for prefix, doctype, padding in defaults:
        try:
            current = frappe.db.get_value("Series", {"name": prefix}, "current") or 0
        except Exception:
            current = 0
        result.append({"prefix": prefix, "doctype": doctype, "padding": padding, "current": int(current)})
    return result


@frappe.whitelist()
def get_number_series():
    """Return all configured number series."""
    _require_admin()
    try:
        if not frappe.db.table_exists(f"tab{_NS_DOCTYPE}"):
            return _ns_fallback()
        rows = frappe.get_all(
            _NS_DOCTYPE,
            fields=["name", "prefix", "doctype_name as doctype", "padding", "current"],
            limit=100,
        )
        if not rows:
            return _ns_fallback()
        return rows
    except Exception:
        return _ns_fallback()


@frappe.whitelist()
def save_number_series(prefix, doctype="", current=0, padding=4):  # noqa: ARG001 — doctype/padding kept for API compat
    """Save or update a number series entry."""
    _require_admin()
    try:
        # Update Frappe's built-in Series table directly
        existing = frappe.db.get_value("Series", {"name": prefix}, "name")
        if existing:
            frappe.db.set_value("Series", prefix, "current", int(current))
        else:
            doc = frappe.new_doc("Series")
            doc.name = prefix
            doc.current = int(current)
            doc.db_insert()
        frappe.db.commit()
        return {"success": True}
    except Exception as e:
        frappe.throw(str(e))


@frappe.whitelist()
def reset_number_series(prefix, doctype=""):  # noqa: ARG001 — doctype kept for API compat
    """Reset a number series back to 0."""
    _require_admin()
    try:
        frappe.db.set_value("Series", prefix, "current", 0)
        frappe.db.commit()
        return {"success": True}
    except Exception:
        return {"success": True, "note": "Series not found in database"}


# ─── Email Templates ──────────────────────────────────────────────────────────
# We store templates in Frappe's built-in "Email Template" doctype but prefix
# them with the company name so each company's templates are isolated.
# Stored name format: "<Company>::<template_name>"

def _et_full_name(company: str, short_name: str) -> str:
    return f"{company}::{short_name.strip()}"


def _et_strip(company: str, full_name: str) -> str:
    prefix = f"{company}::"
    return full_name[len(prefix):] if full_name.startswith(prefix) else full_name


@frappe.whitelist()
def get_email_templates():
    """List Email Templates belonging to the current user's company."""
    company = _admin_company()
    prefix = f"{company}::"
    try:
        rows = frappe.get_all(
            "Email Template",
            fields=["name", "subject", "use_html", "modified"],
            filters=[["name", "like", prefix + "%"]],
            limit=200,
            ignore_permissions=True,
        )
        # Strip the company prefix from the name before returning to the UI
        for r in rows:
            r["name"] = _et_strip(company, r["name"])
        return rows
    except Exception:
        return []


@frappe.whitelist()
def get_email_template(name):
    """Fetch a single Email Template with body (short name, company-scoped)."""
    company = _admin_company()
    full_name = _et_full_name(company, name)
    try:
        doc = frappe.get_doc("Email Template", full_name)
        return {
            "name": _et_strip(company, doc.name),
            "subject": doc.subject or "",
            "response": doc.response or "",
            "use_html": doc.use_html or 0,
        }
    except Exception:
        return {}


@frappe.whitelist()
def save_email_template(name, subject, response="", use_html=0):
    """Create or update an Email Template (company-scoped)."""
    _require_admin()
    company = _admin_company()
    full_name = _et_full_name(company, name)
    use_html = int(use_html) if str(use_html).isdigit() else (1 if use_html in (True, "true", "True") else 0)
    if frappe.db.exists("Email Template", full_name):
        doc = frappe.get_doc("Email Template", full_name)
        doc.subject = subject
        doc.response = response
        doc.use_html = use_html
        doc.save(ignore_permissions=True)
    else:
        doc = frappe.new_doc("Email Template")
        # Frappe's Email Template uses autoname="field:template_name", so we
        # must set the naming field, not doc.name directly.
        doc.template_name = full_name
        doc.subject = subject
        doc.response = response
        doc.use_html = use_html
        doc.insert(ignore_permissions=True, set_name=full_name)
    frappe.db.commit()
    return {"success": True, "name": _et_strip(company, doc.name)}


@frappe.whitelist()
def delete_email_template(name):
    """Delete an Email Template (company-scoped)."""
    _require_admin()
    company = _admin_company()
    full_name = _et_full_name(company, name)
    frappe.delete_doc("Email Template", full_name, ignore_permissions=True, force=True)
    frappe.db.commit()
    return {"success": True}


@frappe.whitelist()
def get_email_template_for_doc(doc_type, short_name):
    """Resolve a company-scoped email template and return rendered subject+body fields.
    Used by email-defaults endpoints to apply saved templates."""
    company = _admin_company()
    full_name = _et_full_name(company, short_name)
    try:
        doc = frappe.get_doc("Email Template", full_name)
        return {
            "subject": doc.subject or "",
            "response": doc.response or "",
            "use_html": doc.use_html or 0,
        }
    except Exception:
        return None


# ─── Payment Terms ────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_payment_terms():
    """List all Payment Term documents."""
    try:
        return frappe.get_all(
            "Payment Term",
            fields=["name", "due_date_based_on", "payment_days",
                    "discount_percentage", "discount_days", "description"],
            limit=200,
            ignore_permissions=True,
        )
    except Exception:
        return []


@frappe.whitelist()
def save_payment_term(name, due_date_based_on="Day(s) after invoice date",
                      payment_days=30, discount_days=0, discount_percentage=0,
                      description=""):
    """Create or update a Payment Term."""
    _require_admin()
    payment_days = int(payment_days or 0)
    discount_days = int(discount_days or 0)
    discount_percentage = float(discount_percentage or 0)
    if frappe.db.exists("Payment Term", name):
        doc = frappe.get_doc("Payment Term", name)
    else:
        doc = frappe.new_doc("Payment Term")
        doc.payment_term_name = name
    doc.due_date_based_on = due_date_based_on
    doc.payment_days = payment_days
    doc.discount_days = discount_days
    doc.discount_percentage = discount_percentage
    doc.description = description or ""
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True, "name": doc.name}


@frappe.whitelist()
def delete_payment_term(name):
    """Delete a Payment Term."""
    _require_admin()
    frappe.delete_doc("Payment Term", name, ignore_permissions=True, force=True)
    frappe.db.commit()
    return {"success": True}


@frappe.whitelist()
def get_currency_rates():
    """Return the most recent exchange rate for each currency pair from Currency Exchange."""
    try:
        rows = frappe.get_all(
            "Currency Exchange",
            fields=["from_currency", "to_currency", "exchange_rate", "date"],
            order_by="date desc",
            limit=200,
            ignore_permissions=True,
        )
        # Keep only the latest entry per from_currency
        seen = {}
        for r in rows:
            key = r["from_currency"]
            if key not in seen:
                seen[key] = {
                    "currency_code": r["from_currency"],
                    "from_currency": r["from_currency"],
                    "to_currency":   r["to_currency"],
                    "exchange_rate": flt(r["exchange_rate"]),
                    "date":          str(r["date"]),
                }
        return list(seen.values())
    except Exception:
        return []


# ── SSO / Social Login ────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False)
def get_sso_providers():
    """Return config status for Google and Microsoft SSO."""
    result = {}
    for provider in ("Google", "Office 365"):
        key_name = frappe.scrub(provider)
        exists = frappe.db.exists("Social Login Key", key_name)
        if exists:
            doc = frappe.get_doc("Social Login Key", key_name)
            result[provider] = {
                "enabled": bool(doc.enable_social_login),
                "client_id": doc.client_id or "",
                "has_secret": bool(doc.client_secret),
            }
        else:
            result[provider] = {"enabled": False, "client_id": "", "has_secret": False}
    return result


@frappe.whitelist(allow_guest=False, methods=["POST"])
def save_sso_provider(provider, client_id, client_secret="", enabled=1):
    """Create or update a Social Login Key for Google or Microsoft."""
    _require_admin()
    if provider not in ("Google", "Office 365"):
        frappe.throw("Only Google and Office 365 are supported")

    key_name = frappe.scrub(provider)
    exists = frappe.db.exists("Social Login Key", key_name)

    if exists:
        doc = frappe.get_doc("Social Login Key", key_name)
    else:
        # Use Frappe's built-in preset to populate all OAuth URLs
        doc = frappe.new_doc("Social Login Key")
        doc.social_login_provider = provider
        doc.get_social_login_provider(provider, initialize=True)

    doc.enable_social_login = int(enabled)
    doc.client_id = client_id
    if client_secret:
        doc.client_secret = client_secret

    doc.flags.ignore_permissions = True
    if exists:
        doc.save()
    else:
        doc.insert()
    frappe.db.commit()
    return {"status": "ok", "provider": provider, "enabled": doc.enable_social_login}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def disable_sso_provider(provider):
    """Disable a Social Login Key without deleting it."""
    _require_admin()
    if provider not in ("Google", "Office 365"):
        frappe.throw("Only Google and Office 365 are supported")
    key_name = frappe.scrub(provider)
    if frappe.db.exists("Social Login Key", key_name):
        frappe.db.set_value("Social Login Key", key_name, "enable_social_login", 0)
        frappe.db.commit()
    return {"status": "ok"}