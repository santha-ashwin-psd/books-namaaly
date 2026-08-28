<template>
  <div class="g3-page">

    <!-- ── Toolbar ── -->
    <div class="g3-toolbar">
      <div>
        <div class="g3-title">GSTR-3B</div>
        <div class="g3-sub">Monthly Self-Declaration — Outward Supplies, ITC &amp; Net Tax</div>
      </div>
      <div class="g3-controls">
        <select v-model="period" class="g3-select" @change="load">
          <option v-for="p in periods" :key="p.v" :value="p.v">{{ p.l }}</option>
        </select>
        <button class="g3-btn-ghost" @click="load" :disabled="loading">
          <span v-html="icon('refresh',13)" :style="loading?'animation:spin 1s linear infinite;display:inline-flex':''"></span>
        </button>
        <button v-if="data" class="g3-btn-ghost" @click="exportCSV"><span v-html="icon('download',13)"></span> CSV</button>
        <button class="g3-btn-primary" @click="load" :disabled="loading">{{ loading ? 'Computing…' : 'Compute' }}</button>
      </div>
    </div>

    <!-- ── Deadline banner ── -->
    <div class="g3-deadline" :class="dueSoon?'due-warn':'due-ok'">
      <span v-html="icon('calendar',12)"></span>
      GSTR-3B for <strong>{{ periodLabel }}</strong> — due <strong>{{ dueDate }}</strong>
      <span v-if="dueSoon" style="font-weight:600"> · deadline approaching</span>
    </div>

    <!-- ── Summary strip ── -->
    <div class="g3-sum-strip">
      <div class="g3-sum-card">
        <div class="g3-sum-lbl">Output Tax Liability</div>
        <div class="g3-sum-val" style="color:#dc2626">{{ data ? fmtCur(data.total_output) : '—' }}</div>
      </div>
      <div class="g3-sum-card">
        <div class="g3-sum-lbl">Input Tax Credit (ITC)</div>
        <div class="g3-sum-val" style="color:#16a34a">{{ data ? fmtCur(data.total_itc) : '—' }}</div>
      </div>
      <div class="g3-sum-card">
        <div class="g3-sum-lbl">Net Tax Payable</div>
        <div class="g3-sum-val" :style="data ? (netTax < 0 ? 'color:#16a34a' : netTax === 0 ? '' : 'color:#d97706') : ''">
          {{ data ? (netTax < 0 ? '− ' + fmtCur(-netTax) : fmtCur(netTax)) : '—' }}
        </div>
      </div>
    </div>

    <!-- Loading shimmer -->
    <div v-if="loading" class="g3-body-layout">
      <div class="g3-card">
        <div style="padding:16px"><div v-for="n in 6" :key="n" class="g3-shimmer" style="margin-bottom:10px"></div></div>
      </div>
      <div class="g3-card">
        <div style="padding:16px"><div v-for="n in 4" :key="n" class="g3-shimmer" style="margin-bottom:10px"></div></div>
      </div>
    </div>

    <!-- ── Two-column body ── -->
    <div v-else-if="data" class="g3-body-layout">

      <!-- LEFT: sections 3.1 and 4 -->
      <div class="g3-left">

        <!-- 3.1 Outward -->
        <div class="g3-card">
          <div class="g3-card-hdr">
            <span class="g3-card-title">3.1 — Outward Supplies</span>
            <span class="g3-meta-ct">{{ data.invoice_count }} invoices</span>
          </div>

          <!-- Desktop table -->
          <table class="g3-table desktop-table">
            <thead><tr>
              <th>Nature of Supply</th>
              <th class="ta-r">Taxable</th>
              <th class="ta-r">IGST</th>
              <th class="ta-r">CGST</th>
              <th class="ta-r">SGST</th>
            </tr></thead>
            <tbody>
              <tr class="g3-row">
                <td><span class="g3-sec">(a)</span> Taxable supplies</td>
                <td class="ta-r mono">{{ fmtCur(data.taxable_value) }}</td>
                <td class="ta-r mono">{{ fmtCur(data.out_igst) }}</td>
                <td class="ta-r mono">{{ fmtCur(data.out_cgst) }}</td>
                <td class="ta-r mono">{{ fmtCur(data.out_sgst) }}</td>
              </tr>
              <tr class="g3-row muted-row">
                <td><span class="g3-sec">(b)</span> Zero rated — exports / SEZ</td>
                <td class="ta-r mono">OMR 0.00</td>
                <td class="ta-r mono" colspan="3" style="text-align:center">—</td>
              </tr>
              <tr class="g3-row muted-row">
                <td><span class="g3-sec">(c)</span> Nil rated / exempted</td>
                <td class="ta-r mono">OMR 0.00</td>
                <td class="ta-r mono" colspan="3" style="text-align:center">—</td>
              </tr>
              <tr class="g3-row muted-row">
                <td><span class="g3-sec">(d)</span> Inward — reverse charge</td>
                <td class="ta-r mono">OMR 0.00</td>
                <td class="ta-r mono" colspan="3" style="text-align:center">—</td>
              </tr>
              <tr class="g3-total-row">
                <td><strong>Total Output Liability</strong></td>
                <td class="ta-r mono"><strong>{{ fmtCur(data.taxable_value) }}</strong></td>
                <td class="ta-r mono red"><strong>{{ fmtCur(data.out_igst) }}</strong></td>
                <td class="ta-r mono red"><strong>{{ fmtCur(data.out_cgst) }}</strong></td>
                <td class="ta-r mono red"><strong>{{ fmtCur(data.out_sgst) }}</strong></td>
              </tr>
            </tbody>
          </table>

          <!-- Mobile cards -->
          <div class="mobile-cards">
            <div class="mob-supply-card">
              <div class="mob-supply-label"><span class="g3-sec">(a)</span> Taxable supplies</div>
              <div class="mob-kv-grid">
                <span class="mob-kv-key">Taxable</span><span class="mob-kv-val mono">{{ fmtCur(data.taxable_value) }}</span>
                <span class="mob-kv-key">IGST</span><span class="mob-kv-val mono">{{ fmtCur(data.out_igst) }}</span>
                <span class="mob-kv-key">CGST</span><span class="mob-kv-val mono">{{ fmtCur(data.out_cgst) }}</span>
                <span class="mob-kv-key">SGST</span><span class="mob-kv-val mono">{{ fmtCur(data.out_sgst) }}</span>
              </div>
            </div>
            <div class="mob-supply-card muted">
              <div class="mob-supply-label"><span class="g3-sec">(b)</span> Zero rated — exports / SEZ</div>
              <div class="mob-kv-grid">
                <span class="mob-kv-key">Taxable</span><span class="mob-kv-val mono">OMR 0.00</span>
              </div>
            </div>
            <div class="mob-supply-card muted">
              <div class="mob-supply-label"><span class="g3-sec">(c)</span> Nil rated / exempted</div>
              <div class="mob-kv-grid">
                <span class="mob-kv-key">Taxable</span><span class="mob-kv-val mono">OMR 0.00</span>
              </div>
            </div>
            <div class="mob-supply-card muted">
              <div class="mob-supply-label"><span class="g3-sec">(d)</span> Inward — reverse charge</div>
              <div class="mob-kv-grid">
                <span class="mob-kv-key">Taxable</span><span class="mob-kv-val mono">OMR 0.00</span>
              </div>
            </div>
            <div class="mob-total-card">
              <div class="mob-supply-label"><strong>Total Output Liability</strong></div>
              <div class="mob-kv-grid">
                <span class="mob-kv-key">Taxable</span><span class="mob-kv-val mono fw6">{{ fmtCur(data.taxable_value) }}</span>
                <span class="mob-kv-key">IGST</span><span class="mob-kv-val mono fw6 red">{{ fmtCur(data.out_igst) }}</span>
                <span class="mob-kv-key">CGST</span><span class="mob-kv-val mono fw6 red">{{ fmtCur(data.out_cgst) }}</span>
                <span class="mob-kv-key">SGST</span><span class="mob-kv-val mono fw6 red">{{ fmtCur(data.out_sgst) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 4 ITC -->
        <div class="g3-card" style="margin-top:14px">
          <div class="g3-card-hdr">
            <span class="g3-card-title">4 — Eligible ITC</span>
            <span class="g3-meta-ct">{{ data.itc_invoice_count }} purchases</span>
          </div>

          <!-- Desktop table -->
          <table class="g3-table desktop-table">
            <thead><tr>
              <th>Details</th>
              <th class="ta-r">IGST</th>
              <th class="ta-r">CGST</th>
              <th class="ta-r">SGST</th>
            </tr></thead>
            <tbody>
              <tr class="g3-row">
                <td><span class="g3-sec">(A)</span> All other ITC — B2B purchases</td>
                <td class="ta-r mono">{{ fmtCur(data.itc_igst) }}</td>
                <td class="ta-r mono">{{ fmtCur(data.itc_cgst) }}</td>
                <td class="ta-r mono">{{ fmtCur(data.itc_sgst) }}</td>
              </tr>
              <tr class="g3-row muted-row">
                <td><span class="g3-sec">(B)</span> ITC Reversed — rule 42/43</td>
                <td class="ta-r mono">OMR 0.00</td>
                <td class="ta-r mono">OMR 0.00</td>
                <td class="ta-r mono">OMR 0.00</td>
              </tr>
              <tr class="g3-total-row">
                <td><strong>Net ITC Available</strong></td>
                <td class="ta-r mono green"><strong>{{ fmtCur(data.itc_igst) }}</strong></td>
                <td class="ta-r mono green"><strong>{{ fmtCur(data.itc_cgst) }}</strong></td>
                <td class="ta-r mono green"><strong>{{ fmtCur(data.itc_sgst) }}</strong></td>
              </tr>
            </tbody>
          </table>

          <!-- Mobile cards -->
          <div class="mobile-cards">
            <div class="mob-supply-card">
              <div class="mob-supply-label"><span class="g3-sec">(A)</span> All other ITC — B2B purchases</div>
              <div class="mob-kv-grid">
                <span class="mob-kv-key">IGST</span><span class="mob-kv-val mono">{{ fmtCur(data.itc_igst) }}</span>
                <span class="mob-kv-key">CGST</span><span class="mob-kv-val mono">{{ fmtCur(data.itc_cgst) }}</span>
                <span class="mob-kv-key">SGST</span><span class="mob-kv-val mono">{{ fmtCur(data.itc_sgst) }}</span>
              </div>
            </div>
            <div class="mob-supply-card muted">
              <div class="mob-supply-label"><span class="g3-sec">(B)</span> ITC Reversed — rule 42/43</div>
              <div class="mob-kv-grid">
                <span class="mob-kv-key">IGST</span><span class="mob-kv-val mono">OMR 0.00</span>
                <span class="mob-kv-key">CGST</span><span class="mob-kv-val mono">OMR 0.00</span>
                <span class="mob-kv-key">SGST</span><span class="mob-kv-val mono">OMR 0.00</span>
              </div>
            </div>
            <div class="mob-total-card">
              <div class="mob-supply-label"><strong>Net ITC Available</strong></div>
              <div class="mob-kv-grid">
                <span class="mob-kv-key">IGST</span><span class="mob-kv-val mono fw6 green">{{ fmtCur(data.itc_igst) }}</span>
                <span class="mob-kv-key">CGST</span><span class="mob-kv-val mono fw6 green">{{ fmtCur(data.itc_cgst) }}</span>
                <span class="mob-kv-key">SGST</span><span class="mob-kv-val mono fw6 green">{{ fmtCur(data.itc_sgst) }}</span>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- RIGHT: 5.1 summary + type breakdown -->
      <div class="g3-right">

        <!-- 5.1 Net Tax Payable -->
        <div class="g3-card">
          <div class="g3-card-hdr">
            <span class="g3-card-title">5.1 — Net Tax Payable</span>
          </div>
          <div class="g3-summary">
            <div class="g3-sum-row">
              <span class="g3-sum-label">Total Output Tax</span>
              <span class="g3-sum-amount red">{{ fmtCur(data.total_output) }}</span>
            </div>
            <div class="g3-sum-row">
              <span class="g3-sum-label">Less: ITC Available</span>
              <span class="g3-sum-amount green">− {{ fmtCur(data.total_itc) }}</span>
            </div>
            <div class="g3-sum-divider"></div>
            <div class="g3-sum-row g3-sum-final">
              <span class="g3-sum-label-lg">Net Tax Payable</span>
              <span class="g3-sum-amount-lg" :class="netTax < 0 ? 'green' : netTax === 0 ? '' : 'amber'">
                {{ netTax < 0 ? '− ' + fmtCur(-netTax) : fmtCur(netTax) }}
              </span>
            </div>
            <div v-if="netTax < 0" class="g3-refund-note">
              <span v-html="icon('info',12)"></span>
              ITC exceeds output — refund eligible (Form RFD-01)
            </div>
          </div>
        </div>

        <!-- Tax type breakdown -->
        <div v-if="data.net_by_type && data.net_by_type.length" class="g3-card" style="margin-top:14px">
          <div class="g3-card-hdr">
            <span class="g3-card-title">Tax Type Breakdown</span>
          </div>

          <!-- Desktop table -->
          <table class="g3-table desktop-table g3-type-table">
            <colgroup>
              <col style="width:22%">
              <col style="width:26%">
              <col style="width:26%">
              <col style="width:26%">
            </colgroup>
            <thead><tr>
              <th>Type</th>
              <th class="ta-r">Output</th>
              <th class="ta-r">ITC</th>
              <th class="ta-r">Net</th>
            </tr></thead>
            <tbody>
              <tr v-for="row in data.net_by_type" :key="row.tax_type" class="g3-row">
                <td><span class="g3-type-badge">{{ row.tax_type || '—' }}</span></td>
                <td class="ta-r mono red">{{ fmtCur(row.output) }}</td>
                <td class="ta-r mono green">{{ fmtCur(row.itc) }}</td>
                <td class="ta-r mono fw6" :class="row.net < 0 ? 'green' : row.net === 0 ? '' : 'amber'">
                  {{ row.net < 0 ? '− ' + fmtCur(-row.net) : fmtCur(row.net) }}
                </td>
              </tr>
            </tbody>
          </table>

          <!-- Mobile cards -->
          <div class="mobile-cards">
            <div v-for="row in data.net_by_type" :key="row.tax_type" class="mob-supply-card">
              <div class="mob-supply-label">
                <span class="g3-type-badge">{{ row.tax_type || '—' }}</span>
              </div>
              <div class="mob-kv-grid">
                <span class="mob-kv-key">Output</span><span class="mob-kv-val mono red">{{ fmtCur(row.output) }}</span>
                <span class="mob-kv-key">ITC</span><span class="mob-kv-val mono green">{{ fmtCur(row.itc) }}</span>
                <span class="mob-kv-key">Net</span>
                <span class="mob-kv-val mono fw6" :class="row.net < 0 ? 'green' : row.net === 0 ? '' : 'amber'">
                  {{ row.net < 0 ? '− ' + fmtCur(-row.net) : fmtCur(row.net) }}
                </span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- Placeholder -->
    <div v-else class="g3-placeholder">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" stroke-width="1.3"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
      <div class="g3-ph-title">Select a period and click Compute</div>
      <div class="g3-ph-sub">GSTR-3B data will appear here</div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { apiGET, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";
import { flt } from "../utils/format.js";

const { toast } = useToast();
const loading = ref(false);
const data    = ref(null);

const now = new Date();
function makePeriods() {
  const ps = [];
  for (let i = 0; i < 12; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const v = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}`;
    const l = d.toLocaleString("en-IN", { month:"long", year:"numeric" });
    ps.push({ v, l });
  }
  return ps;
}
const periods = makePeriods();
const period  = ref(periods[0].v);

const periodLabel = computed(() => periods.find(p => p.v === period.value)?.l || period.value);
const dueDate = computed(() => {
  const [yr, mo] = period.value.split("-");
  return new Date(+yr, +mo, 20).toLocaleDateString("en-IN", { day:"2-digit", month:"short", year:"numeric" });
});
const dueSoon = computed(() => {
  const [yr, mo] = period.value.split("-");
  const diff = (new Date(+yr, +mo, 20) - now) / 864e5;
  return diff >= 0 && diff <= 7;
});

const netTax = computed(() => data.value ? flt(data.value.total_output) - flt(data.value.total_itc) : 0);

async function load() {
  loading.value = true; data.value = null;
  try {
    const co = await resolveCompany();
    const [yr, mo] = period.value.split("-");
    const from = `${yr}-${mo}-01`;
    const last = new Date(+yr, +mo, 0).getDate();
    const to   = `${yr}-${mo}-${String(last).padStart(2,"0")}`;
    const summary = await apiGET("zoho_books_clone.db.queries.get_gstr_summary", { company:co, from_date:from, to_date:to });
    const byType = (list, type) => flt((list||[]).find(r=>r.tax_type===type)?.amount);
    data.value = {
      taxable_value: flt(summary?.taxable_value),
      out_igst: byType(summary?.output,"IGST"),
      out_cgst: byType(summary?.output,"CGST"),
      out_sgst: byType(summary?.output,"SGST"),
      itc_igst: byType(summary?.itc,"IGST"),
      itc_cgst: byType(summary?.itc,"CGST"),
      itc_sgst: byType(summary?.itc,"SGST"),
      total_output: flt(summary?.totals?.total_output),
      total_itc: flt(summary?.totals?.total_itc),
      net_by_type: summary?.net_by_type || [],
      invoice_count: (summary?.output||[]).reduce((s,r)=>s+(r.invoice_count||0),0),
      itc_invoice_count: (summary?.itc||[]).reduce((s,r)=>s+(r.invoice_count||0),0),
    };
  } catch (e) { toast.error(e.message||"Failed to compute GSTR-3B"); }
  finally { loading.value = false; }
}

function exportCSV() {
  if (!data.value) return;
  const d = data.value;
  const rows = [
    ["GSTR-3B Summary", period.value], [],
    ["Section","Description","IGST","CGST","SGST"],
    ["3.1(a)","Outward Taxable Supplies",d.out_igst,d.out_cgst,d.out_sgst],
    ["3.1(b)","Zero Rated",0,0,0], ["3.1(c)","Nil/Exempted",0,0,0], ["3.1(d)","Reverse Charge",0,0,0], [],
    ["4(A)","ITC Available",d.itc_igst,d.itc_cgst,d.itc_sgst], ["4(B)","ITC Reversed",0,0,0], [],
    ["5.1","Output Tax",d.total_output,"",""], ["5.1","Less ITC",d.total_itc,"",""], ["5.1","Net Tax Payable",netTax.value,"",""],
  ];
  const csv = rows.map(r=>r.map(v=>`"${String(v??'').replace(/"/g,'""')}"`).join(",")).join("\n");
  const a = document.createElement("a");
  a.href = "data:text/csv;charset=utf-8,"+encodeURIComponent(csv);
  a.download = `GSTR-3B_${period.value}.csv`; a.click();
}

function fmtCur(v) { return new Intl.NumberFormat("en-IN",{style:"currency",currency:"OMR",minimumFractionDigits:2}).format(flt(v)); }

onMounted(load);
</script>

<style scoped>
@keyframes spin    { to { transform: rotate(360deg); } }
@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }

.g3-page { display:flex; flex-direction:column; gap:14px; padding:24px; background:#f8fafc; min-height:100%; font-family:'Inter','Lato',system-ui,-apple-system,sans-serif; }

/* Toolbar */
.g3-toolbar { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px; background:#fff; border:1px solid #e5e7eb; border-radius:10px; padding:16px 20px; }
.g3-title { font-size:16px; font-weight:700; color:#111827; }
.g3-sub   { font-size:11.5px; color:#9ca3af; margin-top:2px; }
.g3-controls { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
.g3-select { border:1px solid #e2e8f0; border-radius:7px; padding:7px 11px; font:inherit; font-size:13px; outline:none; background:#fff; color:#111827; cursor:pointer; }
.g3-select:focus { border-color:#2563eb; }
.g3-btn-primary { display:inline-flex; align-items:center; gap:6px; background:#2563eb; color:#fff; border:none; border-radius:7px; padding:7px 14px; font-size:13px; font-weight:600; cursor:pointer; font-family:inherit; transition:background .15s; }
.g3-btn-primary:hover:not(:disabled) { background:#1d4ed8; }
.g3-btn-primary:disabled { opacity:.55; cursor:not-allowed; }
.g3-btn-ghost { display:inline-flex; align-items:center; gap:6px; background:#fff; border:1px solid #e5e7eb; border-radius:7px; padding:7px 11px; font-size:13px; font-weight:500; color:#374151; cursor:pointer; font-family:inherit; transition:all .15s; }
.g3-btn-ghost:hover:not(:disabled) { background:#f9fafb; }
.g3-btn-ghost:disabled { opacity:.45; cursor:not-allowed; }

/* Deadline */
.g3-deadline { display:flex; align-items:center; gap:8px; border-radius:8px; padding:9px 14px; font-size:12.5px; font-weight:500; }
.due-ok   { background:#f0fdf4; border:1px solid #bbf7d0; color:#15803d; }
.due-warn { background:#fffbeb; border:1px solid #fde68a; color:#b45309; }

/* Summary strip */
.g3-sum-strip { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; }
.g3-sum-card  { background:#fff; border:1px solid #e5e7eb; border-radius:10px; padding:14px 16px; }
.g3-sum-lbl   { font-size:11px; color:#6b7280; text-transform:uppercase; letter-spacing:.05em; margin-bottom:4px; }
.g3-sum-val   { font-size:18px; font-weight:700; color:#111827; }

/* Two-column body */
.g3-body-layout { display:grid; grid-template-columns:1fr minmax(0,360px); gap:14px; align-items:start; }
.g3-left  { display:flex; flex-direction:column; min-width:0; }
.g3-right { display:flex; flex-direction:column; min-width:0; }
@media(max-width:900px) { .g3-body-layout { grid-template-columns:1fr; gap:10px; } }

/* Cards */
.g3-card { background:#fff; border:1px solid #e5e7eb; border-radius:10px; overflow:hidden; min-width:0; }
.g3-card-hdr { display:flex; align-items:center; justify-content:space-between; padding:12px 16px; border-bottom:1px solid #f1f5f9; }
.g3-card-title { font-size:13px; font-weight:700; color:#111827; }
.g3-meta-ct { font-size:11.5px; color:#9ca3af; }

/* Table — shown on desktop, hidden on mobile */
.g3-table { width:100%; border-collapse:collapse; font-size:12.5px; table-layout:fixed; }
.g3-table thead tr { background:#f8fafc; }
.g3-table th { border-bottom:1px solid #e5e7eb; padding:8px 10px; font-size:10.5px; font-weight:700; color:#9ca3af; text-align:left; text-transform:uppercase; letter-spacing:.05em; overflow:hidden; }
.ta-r { text-align:right !important; }
.g3-row td { padding:9px 10px; border-bottom:1px solid #f8fafc; color:#374151; vertical-align:middle; font-size:12px; overflow:hidden; word-break:break-word; }
.g3-row:last-child td { border-bottom:none; }
.muted-row td { color:#9ca3af; }
.g3-total-row td { padding:9px 10px; background:#f8fafc; border-top:1.5px solid #e5e7eb; font-size:12px; }
.g3-sec { font-size:11px; font-weight:700; color:#9ca3af; margin-right:6px; }
.mono  { font-variant-numeric:tabular-nums; }
.fw6   { font-weight:600; }
.red   { color:#dc2626 !important; }
.green { color:#16a34a !important; }
.amber { color:#d97706 !important; }

/* 5.1 Summary panel */
.g3-summary { padding:16px; display:flex; flex-direction:column; gap:8px; }
.g3-sum-row { display:flex; align-items:center; justify-content:space-between; font-size:13px; }
.g3-sum-label { color:#6b7280; }
.g3-sum-amount { font-weight:600; font-variant-numeric:tabular-nums; font-size:13px; }
.g3-sum-divider { height:1px; background:#e5e7eb; margin:4px 0; }
.g3-sum-final { padding-top:2px; }
.g3-sum-label-lg  { font-size:14px; font-weight:700; color:#111827; }
.g3-sum-amount-lg { font-size:18px; font-weight:800; font-variant-numeric:tabular-nums; color:#d97706; }
.g3-refund-note { display:flex; align-items:center; gap:6px; background:#f0fdf4; border:1px solid #bbf7d0; color:#15803d; border-radius:6px; padding:8px 10px; font-size:12px; font-weight:500; margin-top:4px; }

/* Type badge */
.g3-type-badge { background:#f1f5f9; color:#374151; border:1px solid #e2e8f0; border-radius:4px; padding:2px 8px; font-size:11.5px; font-weight:700; }

/* Tax type breakdown table — compact numerics */
.g3-type-table td { font-size:11.5px !important; padding:8px 8px !important; }
.g3-type-table th { padding:7px 8px !important; font-size:10px !important; }
.g3-type-table .mono { font-size:11.5px; letter-spacing:-0.01em; }

/* Placeholder */
.g3-placeholder { display:flex; flex-direction:column; align-items:center; gap:8px; padding:64px; background:#fff; border:1px solid #e5e7eb; border-radius:10px; }
.g3-ph-title { font-size:14px; font-weight:600; color:#374151; }
.g3-ph-sub   { font-size:12.5px; color:#9ca3af; }

/* Shimmer */
.g3-shimmer { height:13px; background:linear-gradient(90deg,#f1f5f9 25%,#e2e8f0 50%,#f1f5f9 75%); border-radius:4px; animation:shimmer 1.4s infinite; background-size:200% 100%; }

/* Mobile card rows — hidden on desktop */
.mobile-cards { display:none; }

/* ── Mobile: ≤768px ── */
@media (max-width: 768px) {
  .g3-page      { padding: 14px; gap: 10px; }
  .g3-toolbar   { padding: 12px 14px; }
  .g3-sum-strip { grid-template-columns: repeat(2, 1fr) !important; }
  .g3-summary   { padding: 12px; }

  /* Hide desktop tables, show mobile cards */
  .desktop-table { display: none; }
  .mobile-cards  { display: block; }

  .mob-supply-card {
    padding: 12px 14px;
    border-bottom: 1px solid #f1f5f9;
  }
  .mob-supply-card.muted .mob-supply-label { color: #9ca3af; }
  .mob-supply-card:last-child { border-bottom: none; }

  .mob-total-card {
    padding: 12px 14px;
    background: #f8fafc;
    border-top: 1.5px solid #e5e7eb;
  }

  .mob-supply-label {
    font-size: 12.5px;
    color: #374151;
    margin-bottom: 8px;
  }

  .mob-kv-grid {
    display: grid;
    grid-template-columns: 80px 1fr;
    gap: 4px 8px;
    align-items: center;
  }

  .mob-kv-key {
    font-size: 11px;
    font-weight: 700;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: .04em;
  }

  .mob-kv-val {
    font-size: 12.5px;
    color: #374151;
    text-align: right;
  }
}

/* ── Small mobile: ≤480px ── */
@media (max-width: 480px) {
  .g3-page      { padding: 10px; gap: 8px; }
  .g3-toolbar   { padding: 10px 12px; }
  .g3-sum-strip { grid-template-columns: 1fr !important; }
  .g3-sum-val   { font-size: 15px; }
  .g3-sum-amount-lg { font-size: 15px; }
}
</style>