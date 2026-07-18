import frappe
from urllib.parse import quote_plus

no_cache = 1
no_sitemap = 1

def get_context(context):
    if not frappe.session.user or frappe.session.user == "Guest":
        request_path = frappe.request.path if hasattr(frappe, "request") and frappe.request else "/books"
        # Never let the redirect target be an auth route itself — that's what
        # causes ERR_TOO_MANY_REDIRECTS when this page is reached via a
        # catch-all website_route_rule that also matches /login.
        if request_path.startswith("/login"):
            request_path = "/books"
        frappe.local.flags.redirect_location = f"/login?redirect-to={quote_plus(request_path)}"
        raise frappe.Redirect