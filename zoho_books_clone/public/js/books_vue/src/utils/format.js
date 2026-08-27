// Formatting helpers ported verbatim from public/books.js:28-47.
// Identical signatures so legacy module ports are mechanical.

export function flt(v) { return parseFloat(v) || 0; }

export function fmt(v, c) {
  if (v == null || v === "") return "—";
  const currency = c || "OMR";
  try {
    return new Intl.NumberFormat("en-OM", {
      style: "currency",
      currency,
    }).format(v);
  } catch {
    // OMR uses 3-decimal Baisa; only force 2dp for currencies that use it.
    const symbol = currency === "OMR" ? "ر.ع. " : "";
    const decimals = currency === "OMR" ? 3 : 2;
    return symbol + Number(v).toLocaleString("en-OM", {
      minimumFractionDigits: decimals, maximumFractionDigits: decimals,
    });
  }
}

export function fmtDate(v) {
  if (!v) return "—";
  try {
    return new Date(v).toLocaleDateString("en-IN", {
      day: "2-digit", month: "short", year: "numeric",
    });
  } catch { return v; }
}

export function fmtShort(v) {
  if (!v) return "—";
  try {
    return new Date(v).toLocaleDateString("en-IN", {
      day: "2-digit", month: "short",
    });
  } catch { return v; }
}

export function today() {
  return new Date().toISOString().slice(0, 10);
}

export function isOverdue(inv) {
  return flt(inv.outstanding_amount) > 0
    && inv.due_date
    && new Date(inv.due_date) < new Date();
}

// Maps a GL voucher type to the SPA hash route. Mirrors books.js:50-59.
const STATUS_BADGE = {
  Paid: "b-badge-green", "Partly Paid": "b-badge-amber", Submitted: "b-badge-amber",
  Draft: "b-badge-muted", Cancelled: "b-badge-red", Overdue: "b-badge-red",
  Receive: "b-badge-green", Pay: "b-badge-red", Unreconciled: "b-badge-amber",
  Reconciled: "b-badge-green",
};

export function statusBadge(s) {
  return STATUS_BADGE[s] || "b-badge-muted";
}

// Frappe-style /app/ deep link helpers — used by some legacy components.
export function docUrl(doctype, name) {
  return "/app/" + doctype.toLowerCase().replace(/ /g, "-") + "/" + encodeURIComponent(name);
}

export function newDocUrl(doctype) {
  return "/app/" + doctype.toLowerCase().replace(/ /g, "-") + "/new";
}