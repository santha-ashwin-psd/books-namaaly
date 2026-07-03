// Shared GST/VAT tax computation used by sales (Invoices) and purchase (Bills)
// documents so preview, save, and GL all agree.
//
// A Tax Template carries a *total* rate and a tax_type (GST / VAT / Custom):
//   • GST  → split by place of supply: intra-state = CGST + SGST (rate/2 each),
//            inter-state = IGST (full rate).
//   • VAT  → single flat VAT line.
//   • else → single flat "Other" line at the total rate.
//
// Rows are aggregated by component + rate so multiple lines sharing a rate merge,
// while different rates stay distinct (e.g. "CGST @ 9%" vs "CGST @ 6%").

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

/**
 * @param lines     [{ amount, tax_code }]
 * @param templates [{ name, tax_type, rate (total), account }]
 * @param ctx       { companyState, placeOfSupply, gst: { cgst, sgst, igst }, defaultAccount }
 * @returns rows    [{ tax_type, description, rate, account_head, amount }]
 */
export function computeTaxRows(lines, templates, ctx = {}) {
  const intra = isIntraState(ctx.companyState, ctx.placeOfSupply);
  const gst = ctx.gst || {};
  const agg = {};
  for (const l of lines || []) {
    const base = num(l.amount);
    if (!l.tax_code || !base) continue;
    const t = (templates || []).find((x) => x.name === l.tax_code);
    if (!t) continue;
    const total = num(t.rate);
    if (!total) continue;
    const type = t.tax_type || "GST";

    let comps;
    if (type === "GST") {
      comps = intra
        ? [["CGST", total / 2, gst.cgst], ["SGST", total / 2, gst.sgst]]
        : [["IGST", total, gst.igst]];
    } else if (type === "VAT") {
      comps = [["VAT", total, t.account]];
    } else {
      comps = [["Other", total, t.account]];
    }

    for (const [ttype, rate, acct] of comps) {
      const key = ttype + "@" + rate;
      if (!agg[key]) {
        agg[key] = {
          tax_type: ttype,
          description: `${ttype} @ ${rate}%`,
          rate,
          account_head: acct || ctx.defaultAccount || "",
          amount: 0,
        };
      }
      agg[key].amount += Math.round(base * rate / 100 * 100) / 100;
    }
  }
  return Object.values(agg);
}
