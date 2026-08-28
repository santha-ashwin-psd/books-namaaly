"""
Authentication helpers — signup, OTP verification, onboarding.
All guest endpoints require allow_guest=True; post-login endpoints use the default session guard.
"""
import random
import string

import frappe
from frappe import _

from zoho_books_clone.utils.email_system import send_system_email


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _gen_otp(n=6):
    return "".join(random.choices(string.digits, k=n))


def _signup_cache_key(email):
    return f"books_signup:{email.strip().lower()}"


def _send_otp_email(email, first_name, otp):
    html = f"""
<div style="font-family:'DM Sans',sans-serif;max-width:480px;margin:0 auto;padding:32px 24px;background:#fff">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:28px">
    <div style="width:36px;height:36px;border-radius:9px;background:linear-gradient(135deg,#3949AB,#1A237E);
      display:flex;align-items:center;justify-content:center;font-weight:900;color:#fff;font-size:18px">B</div>
    <span style="font-size:18px;font-weight:700;color:#0D1117">Books</span>
  </div>
  <h2 style="color:#1A237E;font-size:22px;margin-bottom:8px">Verify your email</h2>
  <p style="color:#555;margin-bottom:24px;line-height:1.6">Hi {first_name}, use this code to activate your Books account:</p>
  <div style="background:#E8EAF6;border-radius:12px;padding:28px;text-align:center;margin-bottom:24px">
    <span style="font-size:40px;font-weight:800;letter-spacing:14px;color:#1A237E;">{otp}</span>
  </div>
  <p style="color:#888;font-size:13px;line-height:1.6">
    This code expires in <strong>30 minutes</strong>.<br>
    If you didn't request this, you can safely ignore this email.
  </p>
</div>"""
    send_system_email(
        to=email,
        subject="Verify your Books account",
        html=html,
        text_fallback=f"Hi {first_name}, your Books verification code is {otp}. It expires in 30 minutes.",
    )


# ─── Signup ───────────────────────────────────────────────────────────────────

def _normalize_company_name(name: str) -> str:
    """Trim and collapse internal whitespace."""
    return " ".join((name or "").strip().split())


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def check_email(email):
    """Live availability check for signup email. Returns {available: bool, reason}."""
    email = (email or "").strip().lower()
    if not email:
        return {"available": False, "reason": "empty", "email": email}
    if "@" not in email or "." not in email.split("@")[-1]:
        return {"available": False, "reason": "invalid", "email": email}
    taken = bool(frappe.db.exists("User", {"name": email}))
    return {"available": not taken, "reason": "taken" if taken else "ok", "email": email}


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def check_company_name(company_name):
    """Live availability check for the signup form. Returns {available: bool, name: str}."""
    name = _normalize_company_name(company_name)
    if not name:
        return {"available": False, "reason": "empty", "name": name}
    if len(name) < 2:
        return {"available": False, "reason": "too_short", "name": name}
    taken = bool(frappe.db.exists("Books Company", name))
    return {"available": not taken, "reason": "taken" if taken else "ok", "name": name}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def signup_user(first_name, email, password, company_name="", last_name=""):
    """Store signup data in cache and send a 6-digit verification OTP.
    Company name is mandatory and must be globally unique."""
    email = (email or "").strip().lower()
    first_name = (first_name or "").strip()
    password = password or ""
    company_name = _normalize_company_name(company_name)

    if not email or not first_name or not password:
        frappe.throw(_("Name, email, and password are required."))

    if not company_name:
        frappe.throw(_("Company name is required."))

    if len(company_name) < 2:
        frappe.throw(_("Company name must be at least 2 characters."))

    if "@" not in email or "." not in email.split("@")[-1]:
        frappe.throw(_("Please enter a valid email address."))

    if frappe.db.exists("User", email):
        frappe.throw(_("An account with this email already exists. Please sign in instead."))

    if frappe.db.exists("Books Company", company_name):
        frappe.throw(_("This company name is already registered. Please choose a different name."))

    if len(password) < 8:
        frappe.throw(_("Password must be at least 8 characters."))

    otp = _gen_otp()
    frappe.cache.set_value(
        _signup_cache_key(email),
        {
            "first_name": first_name,
            "last_name": (last_name or "").strip(),
            "email": email,
            "password": password,
            "company_name": company_name,
            "otp": otp,
        },
        expires_in_sec=1800,
    )

    _send_otp_email(email, first_name, otp)
    return {"success": True, "email": email}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def resend_signup_otp(email):
    """Regenerate and resend the signup OTP."""
    email = (email or "").strip().lower()
    key = _signup_cache_key(email)
    data = frappe.cache.get_value(key)
    if not data:
        frappe.throw(_("Signup session expired. Please start over."))

    new_otp = _gen_otp()
    data["otp"] = new_otp
    frappe.cache.set_value(key, data, expires_in_sec=1800)
    _send_otp_email(email, data["first_name"], new_otp)
    return {"success": True}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def verify_signup_otp(email, otp):
    """Verify the OTP; on success create the Books Company, the User, and the
    Books Company Member row that makes the signing-up user the company admin."""
    email = (email or "").strip().lower()
    otp = (otp or "").strip()

    key = _signup_cache_key(email)
    data = frappe.cache.get_value(key)

    if not data:
        frappe.throw(_("Verification session expired. Please sign up again."))

    if data.get("otp") != otp:
        frappe.throw(_("Invalid verification code. Please try again."))

    company_name = _normalize_company_name(data.get("company_name", ""))
    if not company_name:
        frappe.throw(_("Signup is missing a company name. Please start over."))

    if frappe.db.exists("Books Company", company_name):
        frappe.throw(_("This company name was registered while you were verifying. Please choose a different name."))

    try:
        # ── Create Books Company ────────────────────────────────────
        company_doc = frappe.new_doc("Books Company")
        company_doc.company_name = company_name
        company_doc.is_active = 1
        company_doc.currency = "OMR"
        company_doc.fiscal_year_start_month = "April"
        company_doc.email = email
        company_doc.insert(ignore_permissions=True)

        # ── Create User ──────────────────────────────────────────────
        user = frappe.new_doc("User")
        user.email = email
        user.first_name = data["first_name"]
        user.last_name = data.get("last_name", "")
        user.user_type = "System User"
        user.send_welcome_email = 0
        user.enabled = 1
        # Bypass Frappe's zxcvbn password policy — our app enforces its own minimum (8 chars).
        # Without this, signup fails with cryptic errors like "Capitalization doesn't help very much".
        user.flags.ignore_password_policy = True
        existing_roles = {r.role for r in (user.roles or [])}
        if "Books Admin" not in existing_roles:
            user.append("roles", {"role": "Books Admin"})
        user.insert(ignore_permissions=True)
        # Set the password AFTER insert using the raw update_password helper,
        # which doesn't re-run the policy check.
        from frappe.utils.password import update_password as _update_password
        _update_password(email, data["password"])

        # ── Link User → Company as the Admin ────────────────────────
        member = frappe.new_doc("Books Company Member")
        member.user = email
        member.company = company_name
        member.books_role = "Books Admin"
        member.is_company_admin = 1
        for f in ("mod_invoices", "mod_bills", "mod_payments", "mod_banking",
                  "mod_inventory", "mod_accounts", "mod_reports",
                  "mod_customers", "mod_taxes", "mod_admin"):
            member.set(f, 1)
        member.invited_by = email  # self-registered
        member.insert(ignore_permissions=True)

        # Per-user company default — keeps Frappe's default-company aware of tenancy.
        try:
            frappe.defaults.set_user_default("company", company_name, user=email)
        except Exception:
            pass

        # Best-effort: bootstrap a minimal Chart of Accounts + Fiscal Year.
        try:
            from zoho_books_clone.books_setup.bootstrap import bootstrap_company_data
            bootstrap_company_data(company_name)
        except Exception as exc:
            frappe.log_error(f"Books signup — bootstrap skipped: {exc}", "Books Auth")

        frappe.db.commit()
        frappe.cache.delete_value(key)

        return {"success": True, "user": email, "company": company_name}

    except Exception as exc:
        frappe.db.rollback()
        # Clean up any partial Books Company row to avoid blocking re-signup.
        try:
            if frappe.db.exists("Books Company", company_name):
                frappe.delete_doc("Books Company", company_name, ignore_permissions=True, force=True)
                frappe.db.commit()
        except Exception:
            pass
        frappe.throw(str(exc))


# ─── Password Reset via OTP ──────────────────────────────────────────────────

def _reset_cache_key(email):
    return f"books_pwd_reset:{email.strip().lower()}"


def _send_reset_otp_email(email, otp):
    html = f"""
<div style="font-family:'DM Sans',sans-serif;max-width:480px;margin:0 auto;padding:32px 24px;background:#fff">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:28px">
    <div style="width:36px;height:36px;border-radius:9px;background:linear-gradient(135deg,#3949AB,#1A237E);
      display:flex;align-items:center;justify-content:center;font-weight:900;color:#fff;font-size:18px">B</div>
    <span style="font-size:18px;font-weight:700;color:#0D1117">Books</span>
  </div>
  <h2 style="color:#1A237E;font-size:22px;margin-bottom:8px">Reset your password</h2>
  <p style="color:#555;margin-bottom:24px;line-height:1.6">Use this 6-digit code to reset your Books password:</p>
  <div style="background:#E8EAF6;border-radius:12px;padding:28px;text-align:center;margin-bottom:24px">
    <span style="font-size:40px;font-weight:800;letter-spacing:14px;color:#1A237E;">{otp}</span>
  </div>
  <p style="color:#888;font-size:13px;line-height:1.6">
    This code expires in <strong>15 minutes</strong>.<br>
    If you didn't request a password reset, you can safely ignore this email.
  </p>
</div>"""
    return send_system_email(
        to=email,
        subject="Reset your Books password",
        html=html,
        text_fallback=f"Your Books password reset code is {otp}. It expires in 15 minutes.",
    )


@frappe.whitelist(allow_guest=True, methods=["POST"])
def send_password_reset_otp(email):
    """Send a 6-digit OTP to the user's email for password reset. Always returns success to prevent email enumeration."""
    email = (email or "").strip().lower()

    # Case-insensitive lookup — Frappe stores email as-entered but MySQL compare is case-insensitive
    canonical = frappe.db.get_value("User", {"name": email}, "name") or \
                frappe.db.get_value("User", {"email": email}, "name")
    if not canonical:
        # User not found — log silently and return (don't reveal whether account exists)
        frappe.log_error(f"Password reset requested for unknown email: {email}", "Books Auth")
        return {"success": True}

    email = canonical.strip().lower()
    otp = _gen_otp()
    frappe.cache.set_value(_reset_cache_key(email), {"otp": otp}, expires_in_sec=900)
    ok = _send_reset_otp_email(email, otp)
    if not ok:
        frappe.log_error(f"Password reset OTP send FAILED for {email}", "Books Auth")
    return {"success": True}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def verify_reset_otp(email, otp):
    """Check the reset OTP without changing the password. Throws on mismatch."""
    email = (email or "").strip().lower()
    otp = (otp or "").strip()
    key = _reset_cache_key(email)
    data = frappe.cache.get_value(key)
    if not data or data.get("otp") != otp:
        frappe.throw(_("Invalid or expired verification code. Please try again."))
    return {"success": True}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def reset_password_with_otp(email, otp, new_password):
    """Verify the reset OTP and update the user's password."""
    email = (email or "").strip().lower()
    otp = (otp or "").strip()
    new_password = new_password or ""

    key = _reset_cache_key(email)
    data = frappe.cache.get_value(key)

    if not data or data.get("otp") != otp:
        frappe.throw(_("Invalid or expired verification code. Please try again."))

    if len(new_password) < 8:
        frappe.throw(_("Password must be at least 8 characters."))

    user = frappe.get_doc("User", email)
    user.new_password = new_password
    user.save(ignore_permissions=True)
    frappe.db.commit()
    frappe.cache.delete_value(key)

    return {"success": True}


# ─── Login via OTP ("Use one-time code instead") ─────────────────────────────

def _login_otp_cache_key(email):
    return f"books_login_otp:{email.strip().lower()}"


@frappe.whitelist(allow_guest=True, methods=["POST"])
def send_login_otp(email):
    """Send a 6-digit login OTP so users can sign in without their password."""
    email = (email or "").strip().lower()
    if not frappe.db.exists("User", {"name": email}):
        # Don't reveal whether account exists
        return {"success": True}
    otp = _gen_otp()
    frappe.cache.set_value(_login_otp_cache_key(email), {"otp": otp}, expires_in_sec=600)
    html = f"""
<div style="font-family:'DM Sans',sans-serif;max-width:480px;margin:0 auto;padding:32px 24px;background:#fff">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:28px">
    <div style="width:36px;height:36px;border-radius:9px;background:linear-gradient(135deg,#3949AB,#1A237E);
      display:flex;align-items:center;justify-content:center;font-weight:900;color:#fff;font-size:18px">B</div>
    <span style="font-size:18px;font-weight:700;color:#0D1117">Books</span>
  </div>
  <h2 style="color:#1A237E;font-size:22px;margin-bottom:8px">Your sign-in code</h2>
  <p style="color:#555;margin-bottom:24px;line-height:1.6">Use this 6-digit code to sign in to Books:</p>
  <div style="background:#E8EAF6;border-radius:12px;padding:28px;text-align:center;margin-bottom:24px">
    <span style="font-size:40px;font-weight:800;letter-spacing:14px;color:#1A237E;">{otp}</span>
  </div>
  <p style="color:#888;font-size:13px;line-height:1.6">
    This code expires in <strong>10 minutes</strong>.<br>
    If you didn't request this, you can safely ignore this email.
  </p>
</div>"""
    send_system_email(
        to=email,
        subject="Your Books sign-in code",
        html=html,
        text_fallback=f"Your Books sign-in code is {otp}. It expires in 10 minutes.",
    )
    return {"success": True}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def verify_login_otp(email, otp):
    """Verify the login OTP and create a Frappe session."""
    email = (email or "").strip().lower()
    otp = (otp or "").strip()
    key = _login_otp_cache_key(email)
    data = frappe.cache.get_value(key)
    if not data or data.get("otp") != otp:
        frappe.throw(_("Invalid or expired code. Please try again."))
    frappe.cache.delete_value(key)
    # Create a real Frappe session for this user
    frappe.local.login_manager.login_as(email)
    frappe.db.commit()
    return {"success": True, "user": email}


# ─── Onboarding ───────────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def complete_onboarding(
    company_name="",
    gstin="",
    gst_state="",
    invoice_prefix="INV",
    currency="OMR",
    fy_start="04-01",
):
    """Save initial company settings and bootstrap COA + FY after the onboarding wizard."""
    from zoho_books_clone.books_setup.bootstrap import bootstrap_company_data

    try:
        # Per-user company default — keeps each signup isolated
        if company_name:
            try:
                frappe.defaults.set_user_default("company", company_name, user=frappe.session.user)
            except Exception:
                pass

        # Update Books Settings (singleton) — only write fields that haven't
        # been set yet so that a second user's onboarding doesn't overwrite the
        # global defaults for the first company.
        try:
            for field, val in [
                ("default_company",  company_name),
                ("gstin",            gstin),
                ("gst_state",        gst_state),
                ("invoice_prefix",   invoice_prefix or "INV"),
                ("default_currency", currency or "OMR"),
            ]:
                if val:
                    cur = frappe.db.get_single_value("Books Settings", field)
                    if not cur:
                        frappe.db.set_single_value("Books Settings", field, val)
        except Exception as exc:
            frappe.log_error(f"Books Settings update — {exc}", "Books Onboarding")

        # Always set the per-user company default
        if company_name:
            try:
                frappe.defaults.set_user_default(
                    "company", company_name, user=frappe.session.user
                )
            except Exception:
                pass

        # Seed COA + Fiscal Year for this company (idempotent)
        if company_name:
            try:
                bootstrap_company_data(company_name, fy_start or "04-01")
            except Exception as exc:
                frappe.log_error(f"Bootstrap — {exc}", "Books Onboarding")

        frappe.db.commit()
        return {"success": True}

    except Exception as exc:
        frappe.log_error(str(exc), "Books Onboarding")
        return {"success": True, "note": "Settings partially saved — you can update them in Company Setup"}