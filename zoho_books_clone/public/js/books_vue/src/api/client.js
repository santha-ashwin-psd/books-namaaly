import { useConfirm } from "../composables/useConfirm.js";
import { useToast } from "../composables/useToast.js";
import { session } from "./session.js";

// ── Global read-only guard ──────────────────────────────────────────────────
// A "Books Viewer" (session.permissions.read_only) may view but never mutate.
// Every SPA write goes through apiPOST (incl. apiSave/apiSubmit/apiDelete/
// apiCancel which call it), so blocking mutating methods here makes the whole
// app read-only — no matter which page/button triggered it.
const _FRAPPE_WRITE = new Set([
  "frappe.client.insert", "frappe.client.set_value", "frappe.client.delete",
  "frappe.client.rename_doc", "frappe.client.cancel", "frappe.client.submit",
]);
const _WRITE_VERB = /(^|\.)(create|save|update|delete|submit|cancel|record|apply|convert|refund|mark|bulk|set_|pay|post|generate|remove|add|toggle|disable|enable|import|reconcile|close|run|duplicate|make|extend|reset|change|invite|connect|send|write_off|seed)[a-z_0-9]*$/;
function _isWriteMethod(m) {
  if (!m) return false;
  return _FRAPPE_WRITE.has(m) || _WRITE_VERB.test(m) || m.endsWith("ai_execute_pro_action");
}
function _assertWritable(method) {
  if (session.permissions && session.permissions.read_only && _isWriteMethod(method)) {
    throw new Error("Read-only access — your role can view but not make changes.");
  }
}

function _parseServerMessage(msg) {
  if (!msg) return "";
  let obj = msg;
  if (typeof msg === "string") {
    const trimmed = msg.trim();
    if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
      try { obj = JSON.parse(trimmed); } catch {}
    }
  }
  const text = (typeof obj === "object" ? obj.message : String(obj) || "");
  return text.replace(/<[^>]*>/g, "")
             .replace(/\\n/g, "\n").replace(/\\"/g, '"').replace(/^\s+|\s+$/g, "");
}

// frappe.msgprint(indicator=...) -> Toast type. Defaults to "info" for
// plain msgprints with no indicator (e.g. informational, non-alert messages).
function _indicatorToToastType(msg) {
  let obj = msg;
  if (typeof msg === "string") {
    const trimmed = msg.trim();
    if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
      try { obj = JSON.parse(trimmed); } catch { return "info"; }
    } else {
      return "info";
    }
  }
  const indicator = (typeof obj === "object" && obj.indicator) ? String(obj.indicator).toLowerCase() : "";
  if (indicator === "red") return "error";
  if (indicator === "orange" || indicator === "yellow") return "warning";
  if (indicator === "green") return "success";
  return "info";
}

function _parseResponse(json, status) {
  if (status === 401) {
    const dest = window.location.pathname + window.location.hash;
    window.location.href = "/login?redirect-to=" + encodeURIComponent(dest || "/books");
    throw new Error("Session expired");
  }
  if (
    status === 403 && json &&
    (json.exc_type === "CSRFTokenError" || (json.exc || "").includes("CSRFToken"))
  ) {
    fetch("/api/method/zoho_books_clone.api.session.get_books_session", {
      method: "GET", credentials: "same-origin",
    })
      .then(r => r.json())
      .then(d => { if (d.message?.csrf_token) window.frappe.csrf_token = d.message.csrf_token; })
      .catch(() => {});
  }
  if (json.exc || json.exc_type) {
    // Always throw — never fall through to return when server signals an exception.
    const excStr = (json.exc || "").replace(/\\n/g, "\n").replace(/\\"/g, '"');
    const match = excStr.match(/frappe\.exceptions\.\w+:\s*([^\n]+)/);
    if (match && match[1].trim()) {
      throw new Error(match[1].trim());
    }
    if (json._server_messages) {
      try {
        const msgs = JSON.parse(json._server_messages);
        const first = Array.isArray(msgs) ? msgs[0] : msgs;
        const text = _parseServerMessage(first);
        if (text) throw new Error(text);
      } catch (inner) {
        if (inner instanceof Error) throw inner;
      }
    }
    throw new Error(json.message || json.exc_type || "Server error " + status);
  }
  if (json._server_messages) {
    try {
      const msgs = JSON.parse(json._server_messages);
      const list = Array.isArray(msgs) ? msgs : [msgs];
      for (const m of list) {
        const text = _parseServerMessage(m);
        if (text) useToast().toast(text, _indicatorToToastType(m), 6000);
      }
    } catch (e) {}
  }
  return json.message;
}

export async function apiGET(method, params) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params || {})) {
    if (v === null || v === undefined) continue;
    qs.append(k, typeof v === "string" ? v : JSON.stringify(v));
  }
  const r = await fetch("/api/method/" + method + "?" + qs.toString(), {
    method: "GET",
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  let json;
  try { json = await r.json(); }
  catch { throw new Error("Non-JSON response (" + r.status + ")"); }
  return _parseResponse(json, r.status);
}

export async function refreshCsrfToken() {
  const meta = document.querySelector("meta[name='csrf-token']");
  if (meta) {
    const t = meta.getAttribute("content");
    if (t && t !== "None" && t !== "{{ csrf_token }}") {
      if (window.frappe) window.frappe.csrf_token = t;
      return t;
    }
  }
  if (
    window.frappe?.csrf_token &&
    window.frappe.csrf_token !== "None" &&
    window.frappe.csrf_token !== "{{ csrf_token }}"
  ) {
    return window.frappe.csrf_token;
  }
  const ck = document.cookie.split(";").map(c => c.trim()).find(c => c.startsWith("csrf_token="));
  if (ck) {
    const t = decodeURIComponent(ck.split("=").slice(1).join("="));
    if (t && t !== "None") {
      if (window.frappe) window.frappe.csrf_token = t;
      return t;
    }
  }
  try {
    const r = await fetch("/api/method/zoho_books_clone.api.session.get_books_session", {
      method: "GET", credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    const data = await r.json();
    const token = data?.message?.csrf_token;
    if (token && token !== "None") {
      if (window.frappe) window.frappe.csrf_token = token;
      return token;
    }
  } catch {}
  return "";
}

export async function apiPOST(method, args) {
  _assertWritable(method);
  const csrfToken = await refreshCsrfToken();
  const body = new URLSearchParams();
  for (const [k, v] of Object.entries(args || {})) {
    // Skip null/undefined — sending JSON.stringify(null) = "null" (string)
    // causes Frappe's Date validator to throw "null is not a valid date string"
    if (v === null || v === undefined) continue;
    body.append(k, typeof v === "string" ? v : JSON.stringify(v));
  }
  if (csrfToken) body.append("csrf_token", csrfToken);

  const r = await fetch("/api/method/" + method, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "X-Frappe-CSRF-Token": csrfToken || "",
      "Accept": "application/json",
    },
    body: body.toString(),
  });
  let json;
  try { json = await r.json(); }
  catch { throw new Error("Non-JSON response (" + r.status + ")"); }
  return _parseResponse(json, r.status);
}

export async function apiGet(doctype, name) {
  return await apiGET("zoho_books_clone.api.docs.get_doc", { doctype, name });
}

export async function apiSave(doc) {
  return await apiPOST("zoho_books_clone.api.docs.save_doc", { doc: JSON.stringify(doc) });
}

export async function apiSubmit(doctype, name, ignore_budget_warning = 0) {
  try {
    return await apiPOST("zoho_books_clone.api.docs.submit_doc", { doctype, name, ignore_budget_warning });
  } catch (err) {
    if (err.message && err.message.startsWith("BUDGET_WARNING: ")) {
      const warningText = err.message.replace("BUDGET_WARNING: ", "");
      const { confirm } = useConfirm();
      const approved = await confirm({
        title: "Budget Limit Exceeded",
        body: warningText,
        okLabel: "Submit anyway",
        cancelLabel: "Go back",
        okStyle: "primary",
      });
      if (approved) {
        return await apiSubmit(doctype, name, 1);
      } else {
        throw new Error("Submission cancelled by user");
      }
    }
    throw err;
  }
}

export async function apiDelete(doctype, name) {
  return await apiPOST("zoho_books_clone.api.docs.delete_doc", { doctype, name });
}

export async function apiCancel(doctype, name) {
  return await apiPOST("zoho_books_clone.api.docs.cancel_doc", { doctype, name });
}

export async function apiAmend(doctype, name) {
  return await apiPOST("zoho_books_clone.api.docs.amend_doc", { doctype, name });
}

// Doctypes with a native `company` field — filter by the current company.
const _CO_SCOPED = new Set([
  "Sales Invoice", "Purchase Invoice", "Quotation", "Sales Order", "Purchase Order",
  "Payment Entry", "Stock Entry", "Journal Entry", "Account", "Warehouse", "Cost Center",
  "Bank Account", "Expense Claim",
  "Fiscal Year", "Tax Template", "Landed Cost Voucher", "Expense Category",
]);

// Master types with no native company field — filtered by `books_company` custom field
// so all members of the same company share the same pool of records.
const _BOOKS_CO_SCOPED = new Set([
  "Customer", "Supplier", "Item", "Contact",
]);

export async function apiList(dt, opts = {}) {
  const filters = [...(opts.filters || [])];
  const co = window.__booksCompany || "";

  if ((_CO_SCOPED.has(dt) || _BOOKS_CO_SCOPED.has(dt))) {
    console.log("[BooksCompany][client.js] apiList(", dt, ") using window.__booksCompany =", co);
  }

  if (co && _CO_SCOPED.has(dt)) {
    if (!filters.some(f => Array.isArray(f) && f[0] === "company"))
      filters.push(["company", "=", co]);
  }

  if (co && _BOOKS_CO_SCOPED.has(dt)) {
    if (!filters.some(f => Array.isArray(f) && f[0] === "books_company"))
      filters.push(["books_company", "=", co]);
  }

  // Use the custom get_list endpoint that bypasses Frappe's role-permission
  // check — Books tenancy users may have no Frappe role assigned, so the
  // standard frappe.client.get_list returns empty for them.
  return await apiGET("zoho_books_clone.api.docs.get_list", {
    doctype:           dt,
    fields:            JSON.stringify(opts.fields || ["name"]),
    filters:           JSON.stringify(filters),
    order_by:          opts.order || "modified desc",
    limit_page_length: opts.limit || 50,
  }) || [];
}

export async function apiLinkValues(doctype, txt, filters) {
  const f = filters
    ? [...filters, ["name", "like", "%" + txt + "%"]]
    : [["name", "like", "%" + txt + "%"]];
  const co = window.__booksCompany || "";
  if (co && _BOOKS_CO_SCOPED.has(doctype)) {
    if (!f.some(x => Array.isArray(x) && x[0] === "books_company"))
      f.push(["books_company", "=", co]);
  }
  return await apiGET("frappe.client.get_list", {
    doctype,
    fields:            JSON.stringify(["name"]),
    filters:           JSON.stringify(f),
    limit_page_length: 10,
  }) || [];
}

// Legacy alias kept for any direct api() calls still in ported code.
export async function api(method, args) { return await apiGET(method, args); }

// Universal method caller — used by the Quality module and other API endpoints
// that accept both GET and POST. Sends as POST so CSRF is included.
export async function apiCall(method, args = {}) {
  return await apiPOST(method, args);
}


// Resolves the current company. Mirrors books.js:258-271.
export async function resolveCompany() {
  if (window.__booksCompany) {
    console.log("[BooksCompany][client.js] resolveCompany() returning CACHED value:", window.__booksCompany);
    return window.__booksCompany;
  }
  try {
    const r = await apiGET("frappe.client.get_value", {
      doctype:   "Books Settings",
      filters:   JSON.stringify({ name: "Books Settings" }),
      fieldname: JSON.stringify(["default_company"]),
    });
    const c = r?.default_company || "";
    console.log("[BooksCompany][client.js] resolveCompany() FETCHED from server (Books Settings.default_company):", c);
    window.__booksCompany = c;
    if (window.frappe?.boot?.sysdefaults) window.frappe.boot.sysdefaults.company = c;
    return c;
  } catch (e) {
    console.log("[BooksCompany][client.js] resolveCompany() FAILED, falling back to cached value:", window.__booksCompany, e);
    return window.__booksCompany || "";
  }
}

// Explicitly updates the cached company (window.__booksCompany + sysdefaults)
// without a round-trip to the server. Call this the moment the app knows the
// company name has changed (e.g. right after a rename succeeds) so every
// subsequent apiList/resolveCompany call in this session picks up the new
// name immediately instead of waiting on a page reload.
export function setBooksCompany(name) {
  const c = name || "";
  console.log("[BooksCompany][client.js] setBooksCompany() called with", name, "| previous value was", window.__booksCompany);
  window.__booksCompany = c;
  if (window.frappe?.boot?.sysdefaults) window.frappe.boot.sysdefaults.company = c;
  console.log("[BooksCompany][client.js] window.__booksCompany is now", window.__booksCompany);
  return c;
}