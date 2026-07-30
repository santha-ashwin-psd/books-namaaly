"""
Permission-gap lint: flags @frappe.whitelist() functions in api/*.py that
look like they mutate data (call .insert/.save/.submit/.cancel/db_set/
set_value/delete/rename_doc/etc.) but never call one of the module/action
guards from utils/access.py.

This is a static heuristic, not a permission engine -- it can't see what a
called helper function does, so:
  - False negatives are possible (a guard called only inside a shared helper
    won't be seen). Endpoints that already delegate to a guarded helper are
    fine even if this script still lists them; check by hand.
  - False positives are expected for genuinely guest/pre-membership flows
    (signup, password reset, OTP) -- list them in ALLOWLIST below with a
    one-line reason instead of adding an inline guard that wouldn't make
    sense pre-authentication.

Usage:
    python scripts/check_permission_gaps.py          # human-readable report
    python scripts/check_permission_gaps.py --ci      # exit 1 if any
                                                          non-allowlisted gap found

Run from the app root (zoho_books_clone/).
"""
from __future__ import annotations

import ast
import glob
import sys

GUARD_NAMES = {
    "assert_can", "require_module", "require_write",
    "_require_admin", "_require_company_admin", "assert_company",
}
CAN_CHECK_NAMES = {"can_read", "can_write", "can_create", "can_edit", "can_delete"}
WRITE_SIGNS = {
    "insert", "save", "delete_doc", "submit", "cancel", "db_set",
    "set_value", "delete", "rename_doc",
}

# (file, function): reason it's intentionally unguarded.
ALLOWLIST = {
    ("api/auth.py", "signup_user"): "pre-auth: creates the account itself",
    ("api/auth.py", "resend_signup_otp"): "pre-auth: no session yet",
    ("api/auth.py", "verify_signup_otp"): "pre-auth: no session yet",
    ("api/auth.py", "send_password_reset_otp"): "pre-auth: no session yet",
    ("api/auth.py", "reset_password_with_otp"): "pre-auth: no session yet",
    ("api/auth.py", "send_login_otp"): "pre-auth: no session yet",
    ("api/admin.py", "update_profile"): (
        "self-service: always writes to frappe.session.user's own User doc "
        "(never a doctype/company a module or tenancy check would gate) — "
        "the caller's identity is the only relevant check, and that's "
        "already enforced by @frappe.whitelist()'s default allow_guest=False"
    ),
}


def find_gaps(root: str = "api"):
    gaps = []
    for path in sorted(glob.glob(f"{root}/*.py")):
        src = open(path, encoding="utf-8").read()
        try:
            tree = ast.parse(src, filename=path)
        except SyntaxError as e:
            print(f"SYNTAX ERROR parsing {path}: {e}", file=sys.stderr)
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            wl_deco = None
            for d in node.decorator_list:
                call = d if isinstance(d, ast.Call) else None
                func = call.func if call else d
                name = getattr(func, "attr", getattr(func, "id", None))
                if name == "whitelist":
                    wl_deco = d
                    break
            if wl_deco is None:
                continue

            body_src = ast.get_source_segment(src, node) or ""
            has_guard = any(f"{g}(" in body_src for g in GUARD_NAMES)
            has_can_check = any(f"{c}(" in body_src for c in CAN_CHECK_NAMES)
            has_write_sign = any(
                f".{w}(" in body_src or f"frappe.{w}(" in body_src for w in WRITE_SIGNS
            )

            if has_write_sign and not (has_guard or has_can_check):
                gaps.append((path, node.name, node.lineno))
    return gaps


def main():
    ci_mode = "--ci" in sys.argv
    gaps = find_gaps()

    unallowed = [g for g in gaps if (g[0], g[1]) not in ALLOWLIST]
    allowed = [g for g in gaps if (g[0], g[1]) in ALLOWLIST]

    if unallowed:
        print("Whitelisted endpoints with write signals but no permission guard:\n")
        for path, func, line in unallowed:
            print(f"  {path}:{line}  {func}()")
        print(f"\n{len(unallowed)} gap(s). Add assert_can/require_module/require_write, "
              f"or add to ALLOWLIST in this script with a reason if intentional.")
    else:
        print("No un-allowlisted permission gaps found.")

    if allowed:
        print(f"\n({len(allowed)} allowlisted, skipped: "
              f"{', '.join(f[1] for f in allowed)})")

    if ci_mode and unallowed:
        sys.exit(1)


if __name__ == "__main__":
    main()