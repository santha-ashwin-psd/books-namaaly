// Shared GST/VAT tax computation used by sales (Invoices, Credit Notes) and
// purchase (Bills, Debit Notes) documents so preview, save, and GL all agree.
//
// A Tax Template carries explicit component rows — each with its own tax_type
// (CGST / SGST / IGST / UTGST / Cess / VAT / Other), rate, and GL account_head.
// The template is the single source of truth for both rates AND accounts.
//
//   • GST  → the invoice picks components by place of supply:
//              intra-state = CGST + SGST (+ Cess),  inter-state = IGST (+ Cess).
//            One template can hold all of CGST, SGST and IGST and works both ways.
//   • VAT  → the VAT row(s), applied flat (no place-of-supply split).
//   • else → whatever rows the template defines, applied as-is.
//
// Legacy fallback: older templates that only expose a single summed `rate`
// (no rows) still work — GST is split rate/2 across CGST/SGST using the accounts
// passed in ctx.gst, matching the previous behaviour.
//
// Rows are aggregated by component + rate + account so multiple item lines
// sharing a template merge, while different rates stay distinct.

const num = (v) => Number(v) || 0;

// "33-Tamil Nadu" and "Tamil Nadu" must compare equal → strip a leading "NN-".
export function normState(s) {
  if (!s) return "";
  return String(s).replace(/^\s*\d+\s*-\s*/, "").trim().toLowerCase();
}

export function isIntraState(companyState, placeOfSupply) {
  const a = normState(companyState), b = normState(placeOfSupply);
  return !!(a && b && a === b);
}

// Component classification for GST place-of-supply selection.
const INTRA_COMPONENTS = new Set(["CGST", "SGST", "UTGST"]);
const INTER_COMPONENTS = new Set(["IGST"]);
const BOTH_COMPONENTS = new Set(["CESS"]); // Cess applies to both intra and inter

// Return the component rows of a template that apply for this document, given
// the GST regime and whether the sale is intra-state.
function applicableRows(t, intra, ctx) {
  const type = t.tax_type || "GST";
  const rows = t.taxes || t.rows || [];

  // ── Explicit-rows model (current) ───────────────────────────────────────────
  if (rows.length) {
    const out = [];
    for (const r of rows) {
      const rt = String(r.tax_type || "").toUpperCase();
      const rate = num(r.rate);
      if (!rate) continue;
      if (type === "GST") {
        // Skip the components that don't apply to this place of supply.
        if (INTER_COMPONENTS.has(rt) && intra) continue;
        if (INTRA_COMPONENTS.has(rt) && !intra) continue;
        // CGST/SGST intra, IGST inter, Cess both, anything else always included.
      }
      out.push({ tax_type: r.tax_type || type, rate, account_head: r.account_head || "" });
    }
    return out;
  }

  // ── Legacy single-rate fallback (pre-rework templates) ───────────────────────
  const total = num(t.rate);
  if (!total) return [];
  const gst = ctx.gst || {};
  if (type === "GST") {
    return intra
      ? [{ tax_type: "CGST", rate: total / 2, account_head: gst.cgst },
         { tax_type: "SGST", rate: total / 2, account_head: gst.sgst }]
      : [{ tax_type: "IGST", rate: total, account_head: gst.igst }];
  }
  if (type === "VAT") return [{ tax_type: "VAT", rate: total, account_head: t.account }];
  return [{ tax_type: "Other", rate: total, account_head: t.account }];
}

// Headline rate for list / estimate views (Quotes, Sales/Purchase Orders): the
// same-state (intra) total for GST — CGST + SGST (+ Cess) — else the inter total,
// else the sum of all rows. Estimate pages don't split by place of supply, so
// the intra total is the sensible default to show and compute a rough tax with.
export function templateHeadlineRate(taxes) {
  const rows = taxes || [];
  const sum = (a) => Math.round(a.reduce((s, r) => s + num(r.rate), 0) * 100) / 100;
  const has = (set) => rows.filter((r) => set.has(String(r.tax_type || "").toUpperCase()));
  const intra = has(new Set(["CGST", "SGST", "UTGST", "CESS"]));
  if (intra.length) return sum(intra);
  const inter = has(new Set(["IGST", "CESS"]));
  if (inter.length) return sum(inter);
  return sum(rows);
}

/**
 * @param lines     [{ amount, tax_code }]
 * @param templates [{ name, tax_type, rate (summed, legacy), account, taxes:[{tax_type,rate,account_head}] }]
 * @param ctx       { companyState, placeOfSupply, gst:{cgst,sgst,igst}(legacy fallback), defaultAccount }
 * @returns rows    [{ tax_type, description, rate, account_head, amount }]
 */
export function computeTaxRows(lines, templates, ctx = {}) {
  const intra = isIntraState(ctx.companyState, ctx.placeOfSupply);
  const agg = {};
  for (const l of lines || []) {
    const base = num(l.amount);
    if (!l.tax_code || !base) continue;
    const t = (templates || []).find((x) => x.name === l.tax_code);
    if (!t) continue;

    for (const comp of applicableRows(t, intra, ctx)) {
      const rate = num(comp.rate);
      if (!rate) continue;
      const acct = comp.account_head || ctx.defaultAccount || "";
      // Key by component + rate + account so identical components merge but a
      // differing account (rare) stays on its own line.
      const key = comp.tax_type + "@" + rate + "@" + acct;
      if (!agg[key]) {
        agg[key] = {
          tax_type: comp.tax_type,
          description: `${comp.tax_type} @ ${rate}%`,
          rate,
          account_head: acct,
          amount: 0,
        };
      }
      agg[key].amount += base * rate / 100;
    }
  }
  // Round once, after all lines for this component have been aggregated —
  // matches how the physical/e-invoice computes GST (tax on the total
  // taxable value, not the sum of individually-rounded per-line taxes).
  for (const row of Object.values(agg)) {
    row.amount = Math.round(row.amount * 100) / 100;
  }
  return Object.values(agg);
}