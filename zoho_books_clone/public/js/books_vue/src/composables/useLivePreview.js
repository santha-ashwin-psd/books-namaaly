// Shared print-template renderer — Classic / Modern / Minimal.
// All pages reuse these three templates by calling printDoc(doc, config).

import { reactive, computed } from "vue";

const _state = reactive({
  template: "classic",
  brandColor: "#1a6ef7",
  logo: "",
  company: "",
  companyGstin: "",
  companyAddress: "",
  companyCity: "",
  companyState: "",
  companyPincode: "",
  companyPhone: "",
  companyEmail: "",
  bankName: "",
  bankBranch: "",
  bankAccountNo: "",
  bankIfsc: "",
});

async function _loadBranding(company) {
  _state.company = company || "";
  try {
    const csrf = window.frappe?.csrf_token || "";
    const res = await fetch("/api/method/zoho_books_clone.api.admin.get_company_settings", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded", "X-Frappe-CSRF-Token": csrf },
      credentials: "same-origin",
      body: new URLSearchParams({}),
    });
    const data = await res.json();
    const d = data.message || {};
    if (d.pdf_template) _state.template   = d.pdf_template;
    if (d.brand_color)  _state.brandColor = d.brand_color;
    if (d.company_logo) _state.logo       = d.company_logo;
    _state.companyGstin    = d.gstin || "";
    _state.companyAddress  = d.company_address || "";
    _state.companyCity     = d.company_city || "";
    _state.companyState    = d.company_state || "";
    _state.companyPincode  = d.company_pincode || "";
    _state.companyPhone    = d.company_phone || "";
    _state.companyEmail    = d.company_email || "";
    _state.bankName        = d.bank_name || "";
    _state.bankBranch      = d.bank_branch || "";
    _state.bankAccountNo   = d.bank_account_no || "";
    _state.bankIfsc        = d.bank_ifsc || "";
  } catch {}
}

function _saveBranding() {
  // no-op: branding is managed centrally in Settings > Branding & Template
}

function _esc(s) {
  return String(s ?? "").replace(/[&<>"']/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function _fmt(v, currency) {
  const symbol = (currency && currency !== "INR") ? (currency + " ") : "₹";
  return symbol + Number(v || 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function _numberToWords(n) {
  n = Math.round(Number(n) || 0);
  if (n === 0) return "Rupees Zero Only";
  const ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
    "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"];
  const tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"];
  function two(x) {
    if (x < 20) return ones[x];
    return tens[Math.floor(x / 10)] + (x % 10 ? " " + ones[x % 10] : "");
  }
  function three(x) {
    if (x >= 100) return ones[Math.floor(x / 100)] + " Hundred" + (x % 100 ? " " + two(x % 100) : "");
    return two(x);
  }
  let parts = [];
  let crore = Math.floor(n / 10000000); n %= 10000000;
  let lakh = Math.floor(n / 100000); n %= 100000;
  let thousand = Math.floor(n / 1000); n %= 1000;
  let rest = n;
  if (crore) parts.push(three(crore) + " Crore");
  if (lakh) parts.push(three(lakh) + " Lakh");
  if (thousand) parts.push(three(thousand) + " Thousand");
  if (rest) parts.push(three(rest));
  return "Rupees " + parts.join(" ") + " Only";
}
function _today() {
  return new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}
function _logoSrc(url) {
  if (!url) return "";
  if (url.startsWith("data:") || url.startsWith("http")) return url;
  return (window.frappe?.boot?.site_url || window.location.origin).replace(/\/$/, "") + url;
}
// formatAddress() (used across the SPA when an address is picked) always
// joins fields in this fixed order, one per line: address_line1,
// [address_line2], city, state, pincode, [country]. Reflow that into the
// two-line "street, street2" / "City, State - Pincode" layout used on print.
function _formatAddrLines(raw) {
  let lines = String(raw || "").split("\n").map(s => s.trim()).filter(Boolean);
  if (!lines.length) return [];
  if (lines.length > 1 && /^india$/i.test(lines[lines.length - 1])) lines.pop();
  if (lines.length <= 1) return lines;
  let pincode = "";
  if (/^\d{4,8}$/.test(lines[lines.length - 1])) pincode = lines.pop();
  const state = lines.length ? lines.pop() : "";
  const city = lines.length ? lines.pop() : "";
  const streetLine = lines.join(", ");
  const cityStateLine = [city, state].filter(Boolean).join(", ") + (pincode ? " - " + pincode : "");
  return [streetLine, cityStateLine].filter(Boolean);
}

// ── TEMPLATE 1: "Classic" — formal letterhead, ruled frame ────────────────────
function _renderClassic(doc, cfg) {
  const brand    = _state.brandColor;
  const logo     = _logoSrc(_state.logo);
  const currency = doc.currency || "INR";
  const netTotal = doc.net_total != null ? doc.net_total
    : (doc.grand_total || 0) - (doc.total_taxes_and_charges ?? doc.total_tax ?? (doc.taxes || []).reduce((s, t) => s + (t.tax_amount || 0), 0));
  const party    = doc[cfg.partyField] || doc.customer || doc.supplier || "";
  const docDate  = doc.posting_date || doc.transaction_date || "";
  const includeMrp = cfg.includeMrp && (doc.items || []).some(it => Number(it.mrp) > 0);
  const hasIgst  = (doc.items || []).some(it => Number(it.igst_rate) > 0);
  const hasCgst  = (doc.items || []).some(it => Number(it.cgst_rate) > 0 || Number(it.sgst_rate) > 0);
  const includeGst = cfg.includeGst !== false && (hasIgst || hasCgst);
  const totalTax = doc.total_taxes_and_charges ?? (doc.taxes || []).reduce((s, t) => s + (t.tax_amount || 0), 0);
  const roundOff = doc.grand_total != null ? Math.round((doc.grand_total - (netTotal + totalTax)) * 100) / 100 : 0;
  const amountWords = doc.in_words || _numberToWords(Math.round(doc.grand_total || 0));

  function _fmtExpiry(d) {
    if (!d) return "";
    const dt = new Date(d);
    if (isNaN(dt)) return "";
    return dt.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "2-digit" }).replace(/ /g, "-");
  }
  const items = (doc.items || []).map((it, i) => `
    <tr>
      <td class="c">${i + 1}</td>
      <td>
        <div class="inm">${_esc(it.item_name || it.item_code)}</div>
        ${it.description && it.description !== it.item_name ? `<div class="ids">${_esc(it.description)}</div>` : ""}
        ${it.batch_no ? `<div class="ids">Batch: ${_esc(it.batch_no)} (${Number(it.qty || 0)})${it.batch_expiry_date ? ` (exp ${_fmtExpiry(it.batch_expiry_date)})` : ""}</div>` : ""}
      </td>
      ${cfg.includeHsn ? `<td class="c nw">${_esc(it.gst_hsn_code || it.hsn_code || "—")}</td>` : ""}
      <td class="r nw">${Number(it.qty || 0)}</td>
      <td class="c nw">${_esc(it.uom || "Nos")}</td>
      <td class="r nw">${_fmt(it.rate, currency)}</td>
      ${cfg.includeDiscount ? `<td class="c nw">${Number(it.discount_percentage || 0)}%</td>` : ""}
      ${includeGst ? `<td class="r nw">${_fmt(it.taxable_amount != null ? it.taxable_amount : it.amount, currency)}</td>` : ""}
      ${includeGst ? (hasIgst ? `<td class="c nw">${Number(it.igst_rate || 0).toFixed(2)}%</td>` : `<td class="c nw">${Number(it.cgst_rate || 0).toFixed(2)}%</td><td class="c nw">${Number(it.sgst_rate || 0).toFixed(2)}%</td>`) : ""}
      ${includeMrp ? `<td class="r nw">${it.mrp ? _fmt(it.mrp, currency) : "—"}</td>` : ""}
      <td class="r b nw">${_fmt(it.amount, currency)}</td>
    </tr>`).join("");
  const taxRows = (doc.taxes || []).map(t => {
    const label = t.description || t.account_head || "";
    const hasRate = t.rate && !/%/.test(label);
    return `<tr><td class="tl">${_esc(label)}${hasRate ? ` (${Number(t.rate)}%)` : ""}</td><td class="r">${_fmt(t.tax_amount || 0, currency)}</td></tr>`;
  }).join("");
  const colspan = 6 + (cfg.includeHsn ? 1 : 0) + (cfg.includeDiscount ? 1 : 0) + (includeMrp ? 1 : 0) + (includeGst ? (hasIgst ? 2 : 3) : 0);

  return `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>
<title>${_esc(cfg.title)} — ${_esc(doc.name)}</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:Georgia,'Times New Roman',serif;color:#1a1a1a;background:#fff;font-size:12.5px;line-height:1.55;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .sheet{max-width:980px;margin:0 auto;padding:40px}
  .frame{border:1.5px solid #1c1c1c;padding:28px 30px}
  /* Letterhead */
  .hdr{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;font-family:Arial,Helvetica,sans-serif}
  .hdr-l .co{font-size:29px;font-weight:700;color:#111;letter-spacing:-.01em;font-family:Arial,Helvetica,sans-serif}
  .hdr-l .addr{font-size:11px;font-weight:600;color:#111;margin-top:8px;line-height:1.55}
  .hdr-l .contact{margin-top:8px;font-size:11px;color:#111;display:flex;flex-direction:row;flex-wrap:wrap;gap:16px}
  .hdr-l .contact .ci{display:flex;align-items:center;gap:6px}
  .hdr-l .contact svg{width:12px;height:12px;flex-shrink:0}
  .hdr-r{flex-shrink:0}
  .hdr-r img{max-height:110px;max-width:170px;object-fit:contain;display:block}
  .title{text-align:center;font-size:19px;font-weight:800;letter-spacing:.05em;color:#111;margin:28px 0 20px;font-family:Arial,Helvetica,sans-serif}
  .hdr-bot{display:flex;justify-content:space-between;align-items:flex-end;font-family:Arial,sans-serif;font-size:11.5px;color:#111;padding-bottom:16px;margin-bottom:18px;border-bottom:1px solid #ddd}
  .hdr-bot .hb-r{text-align:right}
  .hdr-bot .hb-r div+div{margin-top:3px}
  .hdr-bot b{font-weight:700}
  /* Parties row */
  .pr{display:flex;justify-content:space-between;gap:24px;margin-bottom:6px;font-family:Arial,sans-serif}
  .pr .blk{font-size:12px}
  .pr .blk.r{text-align:right}
  .pr .l{font-size:9.5px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:${brand};margin-bottom:3px}
  .pr .nm{font-weight:700;font-size:13.5px;color:#111;font-family:Georgia,serif}
  .pr .sub{color:#555;font-size:11px;margin-top:2px;white-space:pre-line;line-height:1.45}
  .pr .kv{margin-top:6px}
  hr.sep{border:none;border-top:1px solid #ddd;margin:16px 0}
  /* Billing / Shipping address table */
  .addr-table{display:flex;border:1.5px solid #1c1c1c;margin:10px 0 16px;font-family:Arial,sans-serif}
  .addr-col{flex:1;min-width:0}
  .addr-col+.addr-col{border-left:1.5px solid #1c1c1c}
  .addr-h{font-size:12px;font-weight:700;color:#111;padding:8px 12px;border-bottom:1.5px solid #1c1c1c}
  .addr-body{padding:10px 12px}
  .addr-ct{font-size:12px;color:#111;margin-bottom:2px}
  .addr-nm{font-size:12px;font-weight:700;color:#111;margin-bottom:4px}
  .addr-ln{font-size:12px;color:#111;line-height:1.6}
  /* Table */
  table.it{width:100%;border-collapse:collapse;font-size:12px;font-family:Arial,sans-serif;margin-top:4px}
  table.it th{background:#fff;color:#111;padding:9px 9px;font-size:11.5px;font-weight:700;letter-spacing:0;text-transform:none;text-align:left;border:1px solid #1c1c1c;white-space:nowrap}
  table.it th.r{text-align:right}table.it th.c{text-align:center}
  table.it td{padding:11px 9px;border:1px solid #1c1c1c;vertical-align:top;word-break:break-word;overflow-wrap:anywhere}
  table.it td.nw{white-space:nowrap}
  .it .inm{font-weight:700;color:#1a1a1a;font-family:Georgia,serif}
  .it .ids{font-size:10.5px;color:#666;margin-top:2px}
  .it .r{text-align:right}.it .c{text-align:center}.it .b{font-weight:700}
  /* Totals */
  .tot-wrap{display:flex;justify-content:space-between;gap:20px;margin-top:16px;align-items:flex-start}
  .tot-left{flex:1;min-width:0;display:flex;gap:20px;align-items:flex-start}
  .tot-left>div{flex:1;min-width:0}
  .tt{width:300px;flex-shrink:0;border:1px solid #ccc;font-family:Arial,sans-serif}
  .tt tr td{padding:7px 14px;font-size:12.5px;border-bottom:1px solid #eee}
  .tt .tl{color:#555}.tt .r{text-align:right}
  .tt .grand td{background:${brand};color:#fff;font-weight:700;font-size:14px;border:none}
  /* Notes / sign */
  .notes{margin-bottom:12px;font-family:Arial,sans-serif;font-size:11.5px;color:#444;line-height:1.6}
  .notes .h{font-weight:700;color:${brand};font-size:10px;text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px}
  .words{font-family:Arial,sans-serif;font-size:12px;color:#1a1a1a;font-weight:700;line-height:1.5}
  .words .h{font-weight:700;color:${brand};font-size:10px;text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px;font-family:Arial,sans-serif}
  .bank{font-family:Arial,sans-serif;font-size:11.5px;color:#333;line-height:1.65;margin-bottom:12px}
  .bank .h{font-weight:700;color:#111;font-size:12px;margin-bottom:4px}
  .bank b{font-weight:700;color:#111}
  .sig{display:flex;justify-content:space-between;gap:40px;margin-top:40px;font-family:Arial,sans-serif}
  .sig div{flex:1;border-top:1px solid #999;padding-top:6px;font-size:10px;color:#777;text-align:center}
  .ft{text-align:center;margin-top:18px;font-size:9.5px;color:#999;font-family:Arial,sans-serif;font-style:italic}
  @media print{.sheet{padding:0;max-width:none}}
</style></head><body><div class="sheet"><div class="frame">
  <div class="hdr">
    <div class="hdr-l">
      <div class="co">${_esc(doc.company || cfg.companyName || "")}</div>
      ${_state.companyAddress ? `<div class="addr">${_esc(_state.companyAddress)}${(_state.companyCity || _state.companyPincode) ? `,<br/>${_esc(_state.companyCity || "")}${_state.companyPincode ? ", " + _esc(_state.companyPincode) : ""}` : ""}</div>` : ""}
      ${(_state.companyPhone || _state.companyEmail) ? `<div class="contact">
        ${_state.companyPhone ? `<span class="ci"><svg viewBox="0 0 24 24" fill="#111"><path d="M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2a1 1 0 0 1 1.02-.24c1.12.37 2.33.57 3.57.57a1 1 0 0 1 1 1V20a1 1 0 0 1-1 1C10.61 21 3 13.39 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.24.2 2.45.57 3.57a1 1 0 0 1-.25 1.02z"/></svg>${_esc(_state.companyPhone)}</span>` : ""}
        ${_state.companyEmail ? `<span class="ci"><svg viewBox="0 0 24 24" fill="#111"><path d="M2 5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2zm2.4.2 7.1 6.2a.8.8 0 0 0 1 0l7.1-6.2a.6.6 0 0 0-.4-1H4.8a.6.6 0 0 0-.4 1"/></svg>${_esc(_state.companyEmail)}</span>` : ""}
      </div>` : ""}
    </div>
    ${logo ? `<div class="hdr-r"><img src="${_esc(logo)}"/></div>` : ""}
  </div>
  <div class="title">${_esc(cfg.title)}</div>
  <div class="hdr-bot" style="border-bottom:none">
    <div class="hb-l">${(doc.company_gstin || doc.gstin || _state.companyGstin) ? `<b>GSTIN :</b> ${_esc(doc.company_gstin || doc.gstin || _state.companyGstin)}` : ""}</div>
    <div class="hb-r">
      <div><b>${_esc(cfg.title)} No. :</b> ${_esc(doc.name || "")}</div>
      <div><b>Date :</b> ${_esc(docDate)}</div>
    </div>
  </div>
  ${(() => {
    const billLines = _formatAddrLines(doc.billing_address || doc.address_display || "");
    const shipLines = _formatAddrLines(doc.shipping_address || doc.billing_address || doc.address_display || "");
    const gstin = doc.customer_gstin || doc.supplier_gstin || "";
    const phone = doc.customer_mobile || doc.contact_mobile || doc.contact_phone || "";
    const contactNm = doc.contact_display || "";
    const companyNm = doc.customer_company_name || doc.supplier_company_name || "";
    const col = (label, lines) => `
      <div class="addr-col">
        <div class="addr-h">${label}</div>
        <div class="addr-body">
          ${contactNm ? `<div class="addr-ct">${_esc(contactNm)}</div>` : ""}
          <div class="addr-nm">${_esc(party)}</div>
          ${companyNm ? `<div class="addr-nm">${_esc(companyNm)}</div>` : ""}
          ${lines.map(l => `<div class="addr-ln">${_esc(l)}</div>`).join("")}
          ${gstin ? `<div class="addr-ln"><b>GSTIN :</b> ${_esc(gstin)}</div>` : ""}
          ${phone ? `<div class="addr-ln"><b>Phone :</b> ${_esc(phone)}</div>` : ""}
        </div>
      </div>`;
    if (!billLines.length && !shipLines.length && !gstin && !phone && !companyNm) return "";
    return `<div class="addr-table">${col("Billing Address", billLines)}${col("Shipping Address", shipLines)}</div>`;
  })()}
  <table class="it">
    <thead><tr>
      <th class="c" style="width:30px">#</th><th>Item &amp; Description</th>
      ${cfg.includeHsn ? `<th class="c" style="width:78px">HSN/SAC</th>` : ""}
      <th class="r" style="width:44px">Qty</th><th class="c" style="width:50px">UOM</th>
      <th class="r" style="width:82px">Rate</th>
      ${cfg.includeDiscount ? `<th class="c" style="width:56px">Disc</th>` : ""}
      ${includeGst ? `<th class="r" style="width:82px">Taxable</th>` : ""}
      ${includeGst ? (hasIgst ? `<th class="c" style="width:58px">IGST</th>` : `<th class="c" style="width:58px">CGST</th><th class="c" style="width:58px">SGST</th>`) : ""}
      ${includeMrp ? `<th class="r" style="width:76px">MRP</th>` : ""}
      <th class="r" style="width:96px">Amount</th>
    </tr></thead>
    <tbody>${items || `<tr><td colspan="${colspan}" style="text-align:center;color:#999;padding:24px">No items</td></tr>`}</tbody>
  </table>
  <div class="tot-wrap">
    <div class="tot-left">
      <div>
        ${doc.terms || doc.customer_note ? `<div class="notes"><div class="h">${doc.customer_note ? "Note" : "Terms &amp; Conditions"}</div>${_esc(doc.customer_note || doc.terms)}</div>` : ""}
        ${doc.remarks ? `<div class="notes"><div class="h">Remarks</div>${_esc(doc.remarks)}</div>` : ""}
        ${_state.bankName || _state.bankAccountNo ? `<div class="bank">
          <div class="h">Bank Details :</div>
          ${_state.bankName ? `Bank Name : ${_esc(_state.bankName)}<br/>` : ""}
          ${_state.bankBranch ? `Branch : ${_esc(_state.bankBranch)}<br/>` : ""}
          ${_state.bankAccountNo ? `Account No. : ${_esc(_state.bankAccountNo)}<br/>` : ""}
          ${_state.bankIfsc ? `IFSC : ${_esc(_state.bankIfsc)}` : ""}
        </div>` : ""}
      </div>
      <div class="words"><div class="h">Total Amount in Words</div>${_esc(amountWords)}</div>
    </div>
    <table class="tt">
      <tr><td class="tl">Total Before Tax</td><td class="r">${_fmt(netTotal, currency)}</td></tr>
      ${taxRows}
      ${doc.discount_amount ? `<tr><td class="tl" style="color:#b91c1c">Discount</td><td class="r" style="color:#b91c1c">− ${_fmt(doc.discount_amount, currency)}</td></tr>` : ""}
      ${roundOff ? `<tr><td class="tl">Round Off</td><td class="r">${roundOff > 0 ? "" : "− "}${_fmt(Math.abs(roundOff), currency)}</td></tr>` : ""}
      <tr class="grand"><td>Grand Total</td><td class="r">${_fmt(doc.grand_total, currency)}</td></tr>
    </table>
  </div>
  <div class="sig"><div>Prepared By</div><div>Authorised Signatory</div><div>Receiver's Signature</div></div>
  <div class="ft">This is a computer-generated document. · ${_esc(doc.company || "")} · ${_esc(doc.name)} · Printed ${_today()}</div>
</div></div></body></html>`;
}

// ── TEMPLATE 2: "Modern" — rounded cards, soft, contemporary ──────────────────
function _renderModern(doc, cfg) {
  const brand    = _state.brandColor;
  const logo     = _logoSrc(_state.logo);
  const currency = doc.currency || "INR";
  const netTotal = doc.net_total != null ? doc.net_total
    : (doc.grand_total || 0) - (doc.total_taxes_and_charges ?? doc.total_tax ?? (doc.taxes || []).reduce((s, t) => s + (t.tax_amount || 0), 0));
  const party    = doc[cfg.partyField] || doc.customer || doc.supplier || "";
  const docDate  = doc.posting_date || doc.transaction_date || "";

  const items = (doc.items || []).map((it, i) => `
    <tr>
      <td><div class="inm">${_esc(it.item_name || it.item_code)}</div>
        ${it.description && it.description !== it.item_name ? `<div class="ids">${_esc(it.description)}</div>` : ""}
        ${cfg.includeHsn && (it.gst_hsn_code || it.hsn_code) ? `<div class="ihs">HSN ${_esc(it.gst_hsn_code || it.hsn_code)}</div>` : ""}
      </td>
      <td class="r">${Number(it.qty || 0)} <span class="mut">${_esc(it.uom || "")}</span></td>
      <td class="r">${_fmt(it.rate, currency)}</td>
      ${cfg.includeDiscount ? `<td class="c mut">${Number(it.discount_percentage || 0)}%</td>` : ""}
      <td class="r b">${_fmt(it.amount, currency)}</td>
    </tr>`).join("");
  const colspan = 4 + (cfg.includeDiscount ? 1 : 0);

  return `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>
<title>${_esc(cfg.title)} — ${_esc(doc.name)}</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Inter',system-ui,-apple-system,sans-serif;color:#1f2937;background:#f1f5f9;font-size:12.5px;line-height:1.5;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .page{max-width:900px;margin:0 auto;padding:28px}
  /* Hero card */
  .hero{background:${brand};color:#fff;border-radius:18px;padding:26px 30px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 10px 30px ${brand}40}
  .hero .co{font-size:21px;font-weight:800;letter-spacing:-.01em}
  .hero img{max-height:46px;max-width:130px;object-fit:contain;background:#fff;border-radius:10px;padding:6px;margin-bottom:10px;display:block}
  .hero .gst{font-size:10.5px;opacity:.85;margin-top:4px}
  .hero .rt{text-align:right}
  .hero .badge{font-size:10px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;opacity:.85}
  .hero .num{font-size:26px;font-weight:800;margin-top:2px;line-height:1}
  .hero .dt{font-size:11px;opacity:.85;margin-top:6px}
  /* Info chips */
  .chips{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0}
  .chip{background:#fff;border-radius:12px;padding:10px 16px;box-shadow:0 2px 8px rgba(15,23,42,.06);font-size:11.5px}
  .chip .l{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#94a3b8}
  .chip .v{font-weight:700;color:#0f172a;margin-top:2px}
  /* Party cards */
  .cards{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:18px}
  .card{background:#fff;border-radius:14px;padding:16px 18px;box-shadow:0 2px 8px rgba(15,23,42,.06)}
  .card .l{font-size:9.5px;font-weight:800;text-transform:uppercase;letter-spacing:.07em;color:${brand};margin-bottom:5px}
  .card .nm{font-size:14px;font-weight:800;color:#0f172a}
  .card .sub{font-size:11px;color:#64748b;margin-top:3px;white-space:pre-line;line-height:1.45}
  /* Items card */
  .tbl-card{background:#fff;border-radius:14px;padding:8px 10px;box-shadow:0 2px 8px rgba(15,23,42,.06)}
  table{width:100%;border-collapse:collapse;font-size:12.5px}
  thead th{text-align:left;padding:12px 12px;font-size:9.5px;font-weight:800;text-transform:uppercase;letter-spacing:.06em;color:#94a3b8;border-bottom:2px solid #eef2f7}
  thead th.r{text-align:right}thead th.c{text-align:center}
  tbody td{padding:13px 12px;border-bottom:1px solid #f4f6f9;vertical-align:top;word-break:break-word;overflow-wrap:anywhere}
  tbody tr:last-child td{border-bottom:none}
  .inm{font-weight:700;color:#0f172a}.ids{font-size:10.5px;color:#64748b;margin-top:2px}.ihs{font-size:10px;color:#94a3b8;margin-top:2px}
  .r{text-align:right}.c{text-align:center}.b{font-weight:800}.mut{color:#94a3b8;font-size:10.5px}
  /* Totals */
  .tw{display:flex;justify-content:flex-end;margin-top:16px}
  .tt{width:300px;background:#fff;border-radius:14px;padding:8px 18px;box-shadow:0 2px 8px rgba(15,23,42,.06)}
  .tt .row{display:flex;justify-content:space-between;padding:8px 0;font-size:12.5px;color:#64748b;border-bottom:1px solid #f4f6f9}
  .tt .row span:last-child{color:#0f172a;font-weight:600}
  .tt .grand{display:flex;justify-content:space-between;align-items:center;margin:10px -18px -8px;padding:14px 18px;background:${brand};color:#fff;border-radius:0 0 14px 14px;font-weight:800;font-size:15px}
  .notes{background:#fff;border-radius:14px;padding:14px 18px;margin-top:16px;box-shadow:0 2px 8px rgba(15,23,42,.06);font-size:11.5px;color:#374151;line-height:1.6}
  .notes .h{font-size:9.5px;font-weight:800;text-transform:uppercase;letter-spacing:.06em;color:${brand};margin-bottom:4px}
  .sig{display:flex;gap:18px;margin-top:26px}
  .sig div{flex:1;border-top:1.5px solid #cbd5e1;padding-top:7px;font-size:10px;color:#94a3b8;text-align:center}
  .ft{text-align:center;margin-top:18px;font-size:10px;color:#a8b3c1}
  @media print{body{background:#fff}.page{padding:0;max-width:none}.hero{box-shadow:none}.chip,.card,.tbl-card,.tt,.notes{box-shadow:none;border:1px solid #eef2f7}}
</style></head><body><div class="page">
  <div class="hero">
    <div>
      ${logo ? `<img src="${_esc(logo)}"/>` : ""}
      <div class="co">${_esc(doc.company || cfg.companyName || "")}</div>
      ${doc.company_gstin || doc.gstin ? `<div class="gst">GSTIN: ${_esc(doc.company_gstin || doc.gstin)}</div>` : ""}
    </div>
    <div class="rt">
      <div class="badge">${_esc(cfg.title)}</div>
      <div class="num">${_esc(doc.name || "")}</div>
      <div class="dt">${_esc(docDate)}${doc.status ? " · " + _esc(doc.status) : ""}</div>
    </div>
  </div>
  <div class="chips">
    <div class="chip"><div class="l">Date</div><div class="v">${_esc(docDate)}</div></div>
    ${doc.due_date ? `<div class="chip"><div class="l">Due Date</div><div class="v">${_esc(doc.due_date)}</div></div>` : ""}
    ${doc.valid_till ? `<div class="chip"><div class="l">Valid Till</div><div class="v">${_esc(doc.valid_till)}</div></div>` : ""}
    ${doc.delivery_date ? `<div class="chip"><div class="l">Delivery</div><div class="v">${_esc(doc.delivery_date)}</div></div>` : ""}
    ${doc.po_no ? `<div class="chip"><div class="l">PO Number</div><div class="v">${_esc(doc.po_no)}</div></div>` : ""}
    ${doc.place_of_supply ? `<div class="chip"><div class="l">Place of Supply</div><div class="v">${_esc(doc.place_of_supply)}</div></div>` : ""}
  </div>
  <div class="cards">
    <div class="card"><div class="l">From</div><div class="nm">${_esc(doc.company || cfg.companyName || "")}</div>${doc.company_gstin || doc.gstin ? `<div class="sub">GSTIN: ${_esc(doc.company_gstin || doc.gstin)}</div>` : ""}</div>
    <div class="card"><div class="l">${_esc(cfg.partyLabel)}</div><div class="nm">${_esc(party)}</div>${doc.address_display ? `<div class="sub">${_esc(doc.address_display)}</div>` : ""}${doc.customer_gstin || doc.supplier_gstin ? `<div class="sub">GSTIN: ${_esc(doc.customer_gstin || doc.supplier_gstin)}</div>` : ""}</div>
  </div>
  <div class="tbl-card"><table>
    <thead><tr>
      <th>Item</th><th class="r" style="width:96px">Qty</th><th class="r" style="width:110px">Rate</th>
      ${cfg.includeDiscount ? `<th class="c" style="width:52px">Disc</th>` : ""}
      <th class="r" style="width:120px">Amount</th>
    </tr></thead>
    <tbody>${items || `<tr><td colspan="${colspan}" style="text-align:center;color:#94a3b8;padding:28px">No items</td></tr>`}</tbody>
  </table></div>
  <div class="tw"><div class="tt">
    <div class="row"><span>Subtotal</span><span>${_fmt(netTotal, currency)}</span></div>
    ${(doc.taxes || []).map(t => `<div class="row"><span>${_esc(t.description || t.account_head)}</span><span>${_fmt(t.tax_amount || 0, currency)}</span></div>`).join("")}
    ${doc.discount_amount ? `<div class="row"><span style="color:#dc2626">Discount</span><span style="color:#dc2626">− ${_fmt(doc.discount_amount, currency)}</span></div>` : ""}
    <div class="grand"><span>Grand Total</span><span>${_fmt(doc.grand_total, currency)}</span></div>
  </div></div>
  ${doc.terms || doc.customer_note ? `<div class="notes"><div class="h">${doc.customer_note ? "Note" : "Terms & Conditions"}</div>${_esc(doc.customer_note || doc.terms)}</div>` : ""}
  ${doc.remarks ? `<div class="notes"><div class="h">Remarks</div>${_esc(doc.remarks)}</div>` : ""}
  <div class="sig"><div>Prepared By</div><div>Authorised Signatory</div><div>Receiver's Signature</div></div>
  <div class="ft">${_esc(doc.name)} · Printed ${_today()}</div>
</div></body></html>`;
}

// ── TEMPLATE 3: "Minimal" — Swiss, monochrome, single accent line ─────────────
function _renderMinimal(doc, cfg) {
  const brand    = _state.brandColor;
  const logo     = _logoSrc(_state.logo);
  const currency = doc.currency || "INR";
  const netTotal = doc.net_total != null ? doc.net_total
    : (doc.grand_total || 0) - (doc.total_taxes_and_charges ?? doc.total_tax ?? (doc.taxes || []).reduce((s, t) => s + (t.tax_amount || 0), 0));
  const party    = doc[cfg.partyField] || doc.customer || doc.supplier || "";
  const docDate  = doc.posting_date || doc.transaction_date || "";

  const items = (doc.items || []).map((it, i) => `
    <tr>
      <td class="n">${String(i + 1).padStart(2, "0")}</td>
      <td>
        <span class="inm">${_esc(it.item_name || it.item_code)}</span>
        ${it.description && it.description !== it.item_name ? `<div class="ids">${_esc(it.description)}</div>` : ""}
      </td>
      ${cfg.includeHsn ? `<td class="c mono">${_esc(it.gst_hsn_code || it.hsn_code || "—")}</td>` : ""}
      <td class="r mono">${Number(it.qty || 0)} ${_esc(it.uom || "")}</td>
      <td class="r mono">${_fmt(it.rate, currency)}</td>
      ${cfg.includeDiscount ? `<td class="r mono">${Number(it.discount_percentage || 0) ? Number(it.discount_percentage) + "%" : "—"}</td>` : ""}
      <td class="r mono b">${_fmt(it.amount, currency)}</td>
    </tr>`).join("");
  const colspan = 5 + (cfg.includeHsn ? 1 : 0) + (cfg.includeDiscount ? 1 : 0);

  return `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>
<title>${_esc(cfg.title)} — ${_esc(doc.name)}</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Inter','Helvetica Neue',Arial,sans-serif;color:#111;background:#fff;font-size:12px;line-height:1.6;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .mono{font-variant-numeric:tabular-nums;font-feature-settings:"tnum"}
  .page{max-width:780px;margin:0 auto;padding:64px 60px}
  .accent{height:4px;width:48px;background:${brand};margin-bottom:28px}
  /* Header */
  .hdr{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:44px}
  .hdr .co{font-size:18px;font-weight:700;letter-spacing:-.01em;display:flex;align-items:center;gap:10px}
  .hdr .co img{max-height:30px;max-width:90px;object-fit:contain}
  .hdr .gst{font-size:10px;color:#999;margin-top:4px;font-weight:400}
  .hdr .rt{text-align:right}
  .hdr .t{font-size:10px;font-weight:600;letter-spacing:.34em;text-transform:uppercase;color:#999}
  .hdr .num{font-size:17px;font-weight:700;margin-top:4px}
  /* Meta grid */
  .meta{display:grid;grid-template-columns:repeat(4,1fr);gap:18px 24px;margin-bottom:38px}
  .meta .m .l{font-size:8.5px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#bbb}
  .meta .m .v{font-size:12px;font-weight:600;color:#111;margin-top:3px}
  .meta .m .v.sub{font-weight:400;color:#555;font-size:11px;white-space:pre-line;line-height:1.4}
  /* Table */
  table{width:100%;border-collapse:collapse;font-size:12px}
  thead th{text-align:left;padding:0 4px 10px;font-size:8.5px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#bbb;border-bottom:1px solid #111}
  thead th.r{text-align:right}thead th.c{text-align:center}
  tbody td{padding:13px 4px;border-bottom:1px solid #f0f0f0;vertical-align:top;word-break:break-word;overflow-wrap:anywhere}
  tbody tr:last-child td{border-bottom:none}
  .n{color:#ccc;width:30px;font-variant-numeric:tabular-nums}
  .inm{font-weight:600}.ids{font-size:10.5px;color:#888;margin-top:2px}
  .r{text-align:right}.c{text-align:center}.b{font-weight:700}
  /* Totals */
  .tw{display:flex;justify-content:flex-end;margin-top:8px}
  .tt{width:280px}
  .tt .row{display:flex;justify-content:space-between;padding:7px 0;font-size:12px;color:#777}
  .tt .row span:last-child{color:#111}
  .tt .grand{display:flex;justify-content:space-between;align-items:baseline;margin-top:10px;padding-top:14px;border-top:3px solid ${brand};font-size:18px;font-weight:700;color:#111}
  .tt .grand .amt{color:${brand}}
  /* Notes */
  .notes{margin-top:40px;display:grid;grid-template-columns:1fr 1fr;gap:28px}
  .notes .h{font-size:8.5px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#bbb;margin-bottom:6px}
  .notes .bd{font-size:11.5px;color:#444;line-height:1.6}
  .sig{display:flex;gap:30px;margin-top:54px}
  .sig div{flex:1;border-top:1px solid #ccc;padding-top:6px;font-size:9.5px;color:#aaa;letter-spacing:.04em}
  .ft{margin-top:34px;font-size:9px;color:#ccc;letter-spacing:.06em;text-transform:uppercase}
  @media print{.page{padding:44px 40px;max-width:none}}
</style></head><body><div class="page">
  <div class="accent"></div>
  <div class="hdr">
    <div>
      <div class="co">${logo ? `<img src="${_esc(logo)}"/>` : ""}${_esc(doc.company || cfg.companyName || "")}</div>
      ${doc.company_gstin || doc.gstin ? `<div class="gst">GSTIN ${_esc(doc.company_gstin || doc.gstin)}</div>` : ""}
    </div>
    <div class="rt"><div class="t">${_esc(cfg.title)}</div><div class="num mono">${_esc(doc.name || "")}</div></div>
  </div>
  <div class="meta">
    <div class="m" style="grid-column:span 2"><div class="l">${_esc(cfg.partyLabel)}</div><div class="v">${_esc(party)}</div>${doc.address_display ? `<div class="v sub">${_esc(doc.address_display)}</div>` : ""}${doc.customer_gstin || doc.supplier_gstin ? `<div class="v sub">GSTIN ${_esc(doc.customer_gstin || doc.supplier_gstin)}</div>` : ""}</div>
    <div class="m"><div class="l">Date</div><div class="v mono">${_esc(docDate)}</div></div>
    ${doc.due_date ? `<div class="m"><div class="l">Due</div><div class="v mono">${_esc(doc.due_date)}</div></div>` : (doc.valid_till ? `<div class="m"><div class="l">Valid Till</div><div class="v mono">${_esc(doc.valid_till)}</div></div>` : "<div class='m'></div>")}
    ${doc.po_no ? `<div class="m"><div class="l">PO Number</div><div class="v mono">${_esc(doc.po_no)}</div></div>` : ""}
    ${doc.place_of_supply ? `<div class="m"><div class="l">Place of Supply</div><div class="v">${_esc(doc.place_of_supply)}</div></div>` : ""}
  </div>
  <table>
    <thead><tr>
      <th style="width:30px">No</th><th>Item</th>
      ${cfg.includeHsn ? `<th class="c" style="width:70px">HSN/SAC</th>` : ""}
      <th class="r" style="width:96px">Qty</th><th class="r" style="width:100px">Rate</th>
      ${cfg.includeDiscount ? `<th class="r" style="width:52px">Disc</th>` : ""}
      <th class="r" style="width:110px">Amount</th>
    </tr></thead>
    <tbody>${items || `<tr><td colspan="${colspan}" style="text-align:center;color:#bbb;padding:24px">No items</td></tr>`}</tbody>
  </table>
  <div class="tw"><div class="tt">
    <div class="row"><span>Subtotal</span><span class="mono">${_fmt(netTotal, currency)}</span></div>
    ${(doc.taxes || []).map(t => `<div class="row"><span>${_esc(t.description || t.account_head)}</span><span class="mono">${_fmt(t.tax_amount || 0, currency)}</span></div>`).join("")}
    ${doc.discount_amount ? `<div class="row"><span style="color:#b91c1c">Discount</span><span class="mono" style="color:#b91c1c">− ${_fmt(doc.discount_amount, currency)}</span></div>` : ""}
    <div class="grand"><span>Total</span><span class="amt mono">${_fmt(doc.grand_total, currency)}</span></div>
  </div></div>
  ${(doc.remarks || doc.terms || doc.customer_note) ? `<div class="notes">
    ${doc.remarks ? `<div><div class="h">Remarks</div><div class="bd">${_esc(doc.remarks)}</div></div>` : "<div></div>"}
    ${doc.terms || doc.customer_note ? `<div><div class="h">${doc.customer_note ? "Note" : "Terms"}</div><div class="bd">${_esc(doc.customer_note || doc.terms)}</div></div>` : ""}
  </div>` : ""}
  <div class="sig"><div>Prepared By</div><div>Authorised Signatory</div><div>Receiver's Signature</div></div>
  <div class="ft">${_esc(doc.company || "")} — ${_esc(doc.name)} — Printed ${_today()}</div>
</div></body></html>`;
}


// ── Public API ────────────────────────────────────────────────────────────────
export function useLivePreview() {
  function setCompany(c)    { return _loadBranding(c); }
  function refreshBranding() { return _loadBranding(_state.company); }
  function setTemplate(t)   { _state.template = t; _saveBranding(); }
  function setBrandColor(c) { _state.brandColor = c; _saveBranding(); }
  function setLogo(l)       { _state.logo = l; _saveBranding(); }

  function renderDocument(doc, config) {
    const cfg = {
      title:        "INVOICE",
      partyLabel:   "Bill To",
      partyField:   "customer_name",
      companyName:  "",
      includeHsn:   true,
      includeDiscount: true,
      ...config,
    };
    if (_state.template === "modern")  return _renderModern(doc, cfg);
    if (_state.template === "minimal") return _renderMinimal(doc, cfg);
    return _renderClassic(doc, cfg);
  }

  function printDoc(doc, config) {
    const html = renderDocument(doc, config);
    const safeHtml = html.replace(/"/g, "&quot;");
    const shell = `<!DOCTYPE html><html><head><meta charset="utf-8"/>
<title>Print — ${doc?.name || ""}</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Inter',system-ui,sans-serif;background:#e5e7eb;min-height:100vh}
  .toolbar{position:sticky;top:0;z-index:10;background:#fff;padding:10px 18px;
    border-bottom:1px solid #e5e7eb;display:flex;align-items:center;gap:10px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
  .tb-lbl{font-size:11.5px;font-weight:700;color:#374151;letter-spacing:.04em;margin-right:4px}
  .tbtn{font:inherit;font-size:12px;padding:6px 14px;border-radius:6px;border:1px solid #e5e7eb;
    background:#fff;color:#374151;cursor:pointer;font-weight:500;transition:all .15s}
  .tbtn.active{background:#1a6ef7;color:#fff;border-color:#1a6ef7}
  .tbtn:hover:not(.active){background:#f9fafb;border-color:#cbd5e1}
  .sep{width:1px;height:22px;background:#e5e7eb;margin:0 4px}
  .print-btn{margin-left:auto;background:#1a6ef7;color:#fff;border:none;padding:7px 16px;
    border-radius:7px;font-weight:700;cursor:pointer;font:inherit;font-size:12.5px;
    display:flex;align-items:center;gap:6px;transition:background .15s}
  .print-btn:hover{background:#1558d0}
  .doc-wrap{max-width:900px;margin:20px auto;background:#fff;
    box-shadow:0 4px 24px rgba(0,0,0,.1);border-radius:4px;overflow:hidden}
  iframe{border:none;width:100%;min-height:1100px;display:block}
  @media print{.toolbar{display:none!important}.doc-wrap{box-shadow:none;margin:0;max-width:none;border-radius:0}}
</style></head><body>
<div class="toolbar">
  <span class="tb-lbl">PRINT PREVIEW</span>
  <div class="sep"></div>
  <button class="tbtn ${_state.template === "classic" ? "active" : ""}" data-t="classic">Classic</button>
  <button class="tbtn ${_state.template === "modern"  ? "active" : ""}" data-t="modern">Modern</button>
  <button class="tbtn ${_state.template === "minimal" ? "active" : ""}" data-t="minimal">Minimal</button>
  <button class="print-btn" onclick="window.print()">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
      <polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
      <rect x="6" y="14" width="12" height="8"/>
    </svg>
    Print
  </button>
</div>
<div class="doc-wrap"><iframe id="frm" srcdoc="${safeHtml}"></iframe></div>
<script>
  document.querySelectorAll('.tbtn').forEach(b => b.onclick = () => {
    document.querySelectorAll('.tbtn').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    if (window.opener && !window.opener.closed) {
      window.opener.postMessage({
        kind: 'switch-template',
        template: b.dataset.t,
        doc: ${JSON.stringify(doc || {})},
        config: ${JSON.stringify(config || {})}
      }, '*');
    }
  });
  // Auto-resize iframe to content height
  const frm = document.getElementById('frm');
  frm.onload = () => {
    try {
      const h = frm.contentDocument.documentElement.scrollHeight;
      if (h > 400) frm.style.minHeight = h + 'px';
    } catch {}
  };
<\/script>
</body></html>`;
    const w = window.open("", "_blank");
    if (!w) return;
    w.document.open(); w.document.write(shell); w.document.close();
  }

  if (typeof window !== "undefined" && !window.__bvLivePreviewListener) {
    window.__bvLivePreviewListener = true;
    window.addEventListener("message", (ev) => {
      const d = ev.data || {};
      if (d.kind === "switch-template" && d.template) {
        setTemplate(d.template);
        if (d.doc && d.config) printDoc(d.doc, d.config);
      }
    });
  }

  const template   = computed({ get: () => _state.template,   set: setTemplate });
  const brandColor = computed({ get: () => _state.brandColor, set: setBrandColor });
  const logo       = computed({ get: () => _state.logo,       set: setLogo });

  return { state: _state, template, brandColor, logo, setCompany, refreshBranding, renderDocument, printDoc };
}