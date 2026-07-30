// Session bootstrap. Loads /api/method/.../get_books_session before the
// app mounts so usePermissions(), useUser(), and the API client all have
// company + CSRF + module flags ready synchronously after `await`.

import { reactive } from "vue";

// Reactive shared session — everything the shell needs after boot.
export const session = reactive({
  user:        "",
  fullname:    "",
  company:     "",
  isNewUser:   false,
  permissions: {
    books_role:       "",
    is_company_admin: false,
    read_only:        false,
    mod_invoices:     false,
    mod_bills:        false,
    mod_payments:     false,
    mod_banking:      false,
    mod_inventory:    false,
    mod_accounts:     false,
    mod_reports:      false,
    mod_customers:    false,
    mod_taxes:        false,
    mod_admin:        false,
    // Per-module granular level ("None"|"View"|"Create"|"Edit"|"Delete"),
    // added in Phase 3 alongside the legacy mod_* booleans above (which
    // usePermissions().can()/canWrite() still read — this is additive).
    // Populated from get_books_session()'s `levels` payload; empty until
    // bootstrapSession() resolves, same as the mod_* flags above.
    levels: {},
  },
  ready: false,
});

const TUTORIAL_KEY = (user) => `books_tut_done:${user}`;
const SESSION_USER_KEY = "books_session_user";

export async function bootstrapSession() {
  // Ensure window.frappe shape exists for the API client + legacy ports.
  if (!window.frappe) {
    window.frappe = { session: {}, boot: { sysdefaults: { company: "" } } };
  }
  if (!window.frappe.session) window.frappe.session = {};
  if (!window.frappe.boot) window.frappe.boot = { sysdefaults: { company: "" } };

  let data;
  try {
    const r = await fetch("/api/method/zoho_books_clone.api.session.get_books_session", {
      method: "GET", credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    if (r.status === 401 || r.status === 403) {
      const dest = window.location.pathname + window.location.hash;
      // Use replace() so the books page isn't added to browser history,
      // preventing a back-button loop between dashboard and login.
      window.location.replace("/login?redirect-to=" + encodeURIComponent(dest || "/books"));
      return false;   // signal: do NOT mount the app
    }
    const json = await r.json();
    data = json?.message;
  } catch (e) {
    console.error("[Books] session bootstrap failed", e);
    return;
  }
  if (!data) return;

  // If the user has changed since the last session (different login on the
  // same browser), nuke per-user cached state — same intent as legacy
  // clearUserCache() at books.js:27843.
  try {
    const prev = localStorage.getItem(SESSION_USER_KEY);
    if (prev && prev !== data.user) {
      Object.keys(localStorage)
        .filter(k => k.startsWith("books_") || k.startsWith("zb_"))
        .forEach(k => localStorage.removeItem(k));
    }
    localStorage.setItem(SESSION_USER_KEY, data.user);
  } catch {}

  session.user        = data.user        || "";
  session.fullname    = data.fullname    || data.user || "";
  session.company     = data.company     || "";
  session.isNewUser   = !!data.is_new_user;
  Object.assign(session.permissions, data.permissions || {});
  session.ready       = true;

  // Mirror to globals the API client + legacy ports already read.
  window.frappe.csrf_token       = data.csrf_token || "";
  window.frappe.session.user     = data.user;
  window.frappe.session.fullname = data.fullname;
  window.frappe.boot.sysdefaults.company = data.company || "";
  window.__booksCompany          = data.company || "";
  window.__booksUser             = { fullname: data.fullname, books_role: session.permissions.books_role };

  // Tutorial overlay flag — checked by TutorialOverlay.vue.
  try {
    const dismissed = localStorage.getItem(TUTORIAL_KEY(data.user)) === "1";
    window.__booksIsNewUser = session.isNewUser && !dismissed;
  } catch {
    window.__booksIsNewUser = session.isNewUser;
  }
}

export function markTutorialDone() {
  try { localStorage.setItem(TUTORIAL_KEY(session.user), "1"); } catch {}
  window.__booksIsNewUser = false;
  // Fire-and-forget server update — not load-bearing.
  fetch("/api/method/zoho_books_clone.api.session.mark_tutorial_done", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "X-Frappe-CSRF-Token": window.frappe?.csrf_token || "",
    },
  }).catch(() => {});
}