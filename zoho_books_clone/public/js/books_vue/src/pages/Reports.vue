<template>
  <div class="page-reports">

    <!-- Report selector tabs -->
    <div class="report-tabs">
      <button
        v-for="r in reports"
        :key="r.key"
        class="report-tab"
        :class="{ active: activeReport === r.key }"
        @click="activeReport = r.key"
      >
        <span v-html="r.icon"></span>
        {{ r.label }}
      </button>
    </div>

    <!-- Date range picker (hidden for aging reports which use as-of-date) -->
    <div class="books-card date-range-bar">
      <template v-if="['ar','ap'].includes(activeReport)">
        <label class="dr-label">As of Date</label>
        <input type="date" v-model="toDate" class="dr-input" />
      </template>
      <template v-else>
        <label class="dr-label">From</label>
        <input type="date" v-model="fromDate" class="dr-input" />
        <label class="dr-label">To</label>
        <input type="date" v-model="toDate" class="dr-input" />
      </template>
      <button class="books-btn books-btn-primary" @click="runReport">Run Report</button>
      <button v-if="['ar','ap'].includes(activeReport) && (arAging.length||apAging.length)"
        class="books-btn" style="background:#EBFBEE;color:#2F9E44;border:1px solid #8CE99A"
        @click="exportAgingCSV">
        Export CSV
      </button>
    </div>

    <!-- P&L -->
    <div v-if="activeReport === 'pl'" class="books-card report-card">
      <div class="books-card-title">Profit & Loss</div>
      <template v-if="plLoading"><div class="loading-shimmer" style="height:120px;border-radius:8px"></div></template>
      <template v-else-if="pl">
        <div class="pl-row income">
          <span>Total Income</span>
          <span class="mono green">{{ fmt(pl.total_income) }}</span>
        </div>
        <div class="pl-row expense">
          <span>Total Expense</span>
          <span class="mono red">{{ fmt(pl.total_expense) }}</span>
        </div>
        <div class="pl-divider"></div>
        <div class="pl-row net" :class="pl.net_profit >= 0 ? 'profit' : 'loss'">
          <span>Net Profit</span>
          <span class="mono">{{ fmt(pl.net_profit) }}</span>
        </div>
      </template>
      <div v-else class="empty-msg">Run the report to see results.</div>
    </div>

    <!-- P&L Monthly Chart -->
    <div v-if="activeReport === 'pl' && plMonthly.length" class="books-card report-card">
      <div class="books-card-title" style="margin-bottom:16px">Monthly Trend</div>
      <div style="overflow-x:auto">
        <div style="display:flex;align-items:flex-end;gap:6px;min-width:400px;height:140px;padding:0 4px">
          <div v-for="m in plMonthly" :key="m.month" style="flex:1;display:flex;flex-direction:column;align-items:center;gap:3px">
            <div style="width:100%;display:flex;flex-direction:column;align-items:center;gap:2px;flex:1;justify-content:flex-end">
              <div :style="{width:'60%',background:'#4C6EF5',borderRadius:'3px 3px 0 0',height:barH(m.income)+'px',minHeight:'2px',transition:'height .3s'}" :title="'Income: ₹'+fmtN(m.income)"></div>
            </div>
            <div style="width:100%;display:flex;flex-direction:column;align-items:center;gap:2px;flex:1;justify-content:flex-end">
              <div :style="{width:'60%',background:'#FA5252',borderRadius:'3px 3px 0 0',height:barH(m.expense)+'px',minHeight:'2px',transition:'height .3s'}" :title="'Expense: ₹'+fmtN(m.expense)"></div>
            </div>
            <div style="font-size:10px;color:#868E96;margin-top:4px;white-space:nowrap">{{m.month.slice(5)}}</div>
          </div>
        </div>
        <div style="display:flex;gap:16px;justify-content:center;margin-top:10px;font-size:11.5px">
          <span style="display:flex;align-items:center;gap:4px"><span style="width:10px;height:10px;background:#4C6EF5;border-radius:2px;display:inline-block"></span>Income</span>
          <span style="display:flex;align-items:center;gap:4px"><span style="width:10px;height:10px;background:#FA5252;border-radius:2px;display:inline-block"></span>Expense</span>
        </div>
      </div>
    </div>

    <!-- Balance sheet -->
    <div v-if="activeReport === 'bs'" class="books-card report-card">
      <div class="books-card-title">Balance Sheet</div>
      <template v-if="bsLoading"><div class="loading-shimmer" style="height:120px;border-radius:8px"></div></template>
      <template v-else-if="bs">
        <div class="bs-grid">
          <div class="bs-block assets">
            <div class="bs-section-title">Assets</div>
            <div class="bs-amount">{{ fmt(bs.total_assets) }}</div>
          </div>
          <div class="bs-block liabilities">
            <div class="bs-section-title">Liabilities</div>
            <div class="bs-amount">{{ fmt(bs.total_liabilities) }}</div>
          </div>
          <div class="bs-block equity">
            <div class="bs-section-title">Equity</div>
            <div class="bs-amount">{{ fmt(bs.total_equity) }}</div>
            <div v-if="bs.retained_earnings != null" class="bs-eq-sub">
              <span>Capital {{ fmt(bs.equity_capital) }}</span>
              <span>Retained {{ fmt(bs.retained_earnings) }}</span>
            </div>
          </div>
        </div>
        <div class="bs-balance-check" :class="bsBalanced ? 'bs-ok' : 'bs-bad'">
          <span class="bs-bc-icon">{{ bsBalanced ? '✓' : '✕' }}</span>
          Assets = Liabilities + Equity
          <span class="bs-bc-eq">{{ fmt(bs.total_assets) }} = {{ fmt(bs.total_liabilities) }} + {{ fmt(bs.total_equity) }}</span>
        </div>
      </template>
      <div v-else class="empty-msg">Run the report to see results.</div>
    </div>

    <!-- Cash flow -->
    <div v-if="activeReport === 'cf'" class="books-card report-card">
      <div class="books-card-title">Cash Flow</div>
      <template v-if="cfLoading"><div class="loading-shimmer" style="height:120px;border-radius:8px"></div></template>
      <template v-else-if="cf">
        <div class="cf-rows">
          <div class="cf-row"><span>Operating Activities</span><span class="mono" :class="cf.operating >= 0 ? 'green':'red'">{{ fmt(cf.operating) }}</span></div>
          <div class="cf-row"><span>Investing Activities</span><span class="mono" :class="cf.investing >= 0 ? 'green':'red'">{{ fmt(cf.investing) }}</span></div>
          <div class="cf-row"><span>Financing Activities</span><span class="mono" :class="cf.financing >= 0 ? 'green':'red'">{{ fmt(cf.financing) }}</span></div>
          <div class="pl-divider"></div>
          <div class="cf-row net"><span>Net Change</span><span class="mono" :class="cf.net_change >= 0 ? 'green':'red'">{{ fmt(cf.net_change) }}</span></div>
        </div>
      </template>
      <div v-else class="empty-msg">Run the report to see results.</div>
    </div>

    <!-- GST Summary -->
    <div v-if="activeReport === 'gst'" class="books-card report-card">
      <div class="books-card-title">GST Summary</div>
      <template v-if="gstLoading"><div class="loading-shimmer" style="height:80px;border-radius:8px"></div></template>
      <template v-else-if="gst?.length">
        <div class="gst-cards">
          <div v-for="g in gst" :key="g.tax_type" class="gst-card">
            <div class="gst-card-header">
              <span class="badge badge-blue">{{ g.tax_type }}</span>
            </div>
            <div class="gst-card-body">
              <div class="gst-kv">
                <span class="gst-kv-label">Invoice Count</span>
                <span class="gst-kv-value mono-sm">{{ g.invoice_count }}</span>
              </div>
              <div class="gst-kv">
                <span class="gst-kv-label">Total Tax</span>
                <span class="gst-kv-value mono-sm green fw-600">{{ fmt(g.total_tax) }}</span>
              </div>
            </div>
          </div>
        </div>
      </template>
      <div v-else class="empty-msg">Run the report to see results.</div>
    </div>

    <!-- AR Aging -->
    <div v-if="activeReport === 'ar'" class="books-card report-card">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
        <div class="books-card-title" style="margin:0">Accounts Receivable Aging</div>
        <div v-if="arAging.length" style="font-size:12.5px;color:#868E96">
          Total: <span style="font-weight:700;color:#C92A2A">₹{{fmtN(arAging.reduce((s,r)=>s+r.total,0))}}</span>
        </div>
      </div>
      <template v-if="arLoading"><div class="loading-shimmer" style="height:120px;border-radius:8px"></div></template>
      <template v-else-if="arAging.length">
        <div class="aging-cards">
          <div v-for="r in arAging" :key="r.customer" class="aging-card">
            <div class="aging-card-name">{{ r.customer_name || r.customer }}</div>
            <div class="aging-buckets">
              <div class="aging-bucket">
                <span class="bucket-label">Current</span>
                <span class="bucket-val mono-sm">{{ r.current > 0 ? fmtAmt(r.current) : '—' }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">1–30 days</span>
                <span class="bucket-val mono-sm" :class="r.days_1_30>0?'text-warn':''">{{ r.days_1_30 > 0 ? fmtAmt(r.days_1_30) : '—' }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">31–60 days</span>
                <span class="bucket-val mono-sm" :class="r.days_31_60>0?'text-danger':''">{{ r.days_31_60 > 0 ? fmtAmt(r.days_31_60) : '—' }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">61–90 days</span>
                <span class="bucket-val mono-sm" :class="r.days_61_90>0?'text-danger':''">{{ r.days_61_90 > 0 ? fmtAmt(r.days_61_90) : '—' }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">90+ days</span>
                <span class="bucket-val mono-sm" :class="r.days_90_plus>0?'text-danger fw-700':''">{{ r.days_90_plus > 0 ? fmtAmt(r.days_90_plus) : '—' }}</span>
              </div>
            </div>
            <div class="aging-card-total">
              <span class="bucket-label">Total</span>
              <span class="mono-sm fw-700 text-danger">{{ fmtAmt(r.total) }}</span>
            </div>
          </div>
          <!-- Totals summary card -->
          <div class="aging-card aging-card-totals">
            <div class="aging-card-name fw-700">TOTAL</div>
            <div class="aging-buckets">
              <div class="aging-bucket">
                <span class="bucket-label">Current</span>
                <span class="bucket-val mono-sm fw-700">{{ fmtAmt(arAging.reduce((s,r)=>s+r.current,0)) }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">1–30 days</span>
                <span class="bucket-val mono-sm fw-700">{{ fmtAmt(arAging.reduce((s,r)=>s+r.days_1_30,0)) }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">31–60 days</span>
                <span class="bucket-val mono-sm fw-700">{{ fmtAmt(arAging.reduce((s,r)=>s+r.days_31_60,0)) }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">61–90 days</span>
                <span class="bucket-val mono-sm fw-700">{{ fmtAmt(arAging.reduce((s,r)=>s+r.days_61_90,0)) }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">90+ days</span>
                <span class="bucket-val mono-sm fw-700 text-danger">{{ fmtAmt(arAging.reduce((s,r)=>s+r.days_90_plus,0)) }}</span>
              </div>
            </div>
            <div class="aging-card-total">
              <span class="bucket-label">Total</span>
              <span class="mono-sm fw-700 text-danger">{{ fmtAmt(arAging.reduce((s,r)=>s+r.total,0)) }}</span>
            </div>
          </div>
        </div>
      </template>
      <div v-else class="empty-msg">{{arRan ? 'No outstanding receivables as of this date.' : 'Run the report to see results.'}}</div>
    </div>

    <!-- AP Aging -->
    <div v-if="activeReport === 'ap'" class="books-card report-card">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
        <div class="books-card-title" style="margin:0">Accounts Payable Aging</div>
        <div v-if="apAging.length" style="font-size:12.5px;color:#868E96">
          Total: <span style="font-weight:700;color:#C92A2A">₹{{fmtN(apAging.reduce((s,r)=>s+r.total,0))}}</span>
        </div>
      </div>
      <template v-if="apLoading"><div class="loading-shimmer" style="height:120px;border-radius:8px"></div></template>
      <template v-else-if="apAging.length">
        <div class="aging-cards">
          <div v-for="r in apAging" :key="r.supplier" class="aging-card">
            <div class="aging-card-name">{{ r.supplier_name || r.supplier }}</div>
            <div class="aging-buckets">
              <div class="aging-bucket">
                <span class="bucket-label">Current</span>
                <span class="bucket-val mono-sm">{{ r.current > 0 ? fmtAmt(r.current) : '—' }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">1–30 days</span>
                <span class="bucket-val mono-sm" :class="r.days_1_30>0?'text-warn':''">{{ r.days_1_30 > 0 ? fmtAmt(r.days_1_30) : '—' }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">31–60 days</span>
                <span class="bucket-val mono-sm" :class="r.days_31_60>0?'text-danger':''">{{ r.days_31_60 > 0 ? fmtAmt(r.days_31_60) : '—' }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">61–90 days</span>
                <span class="bucket-val mono-sm" :class="r.days_61_90>0?'text-danger':''">{{ r.days_61_90 > 0 ? fmtAmt(r.days_61_90) : '—' }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">90+ days</span>
                <span class="bucket-val mono-sm" :class="r.days_90_plus>0?'text-danger fw-700':''">{{ r.days_90_plus > 0 ? fmtAmt(r.days_90_plus) : '—' }}</span>
              </div>
            </div>
            <div class="aging-card-total">
              <span class="bucket-label">Total</span>
              <span class="mono-sm fw-700 text-danger">{{ fmtAmt(r.total) }}</span>
            </div>
          </div>
          <!-- Totals summary card -->
          <div class="aging-card aging-card-totals">
            <div class="aging-card-name fw-700">TOTAL</div>
            <div class="aging-buckets">
              <div class="aging-bucket">
                <span class="bucket-label">Current</span>
                <span class="bucket-val mono-sm fw-700">{{ fmtAmt(apAging.reduce((s,r)=>s+r.current,0)) }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">1–30 days</span>
                <span class="bucket-val mono-sm fw-700">{{ fmtAmt(apAging.reduce((s,r)=>s+r.days_1_30,0)) }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">31–60 days</span>
                <span class="bucket-val mono-sm fw-700">{{ fmtAmt(apAging.reduce((s,r)=>s+r.days_31_60,0)) }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">61–90 days</span>
                <span class="bucket-val mono-sm fw-700">{{ fmtAmt(apAging.reduce((s,r)=>s+r.days_61_90,0)) }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">90+ days</span>
                <span class="bucket-val mono-sm fw-700 text-danger">{{ fmtAmt(apAging.reduce((s,r)=>s+r.days_90_plus,0)) }}</span>
              </div>
            </div>
            <div class="aging-card-total">
              <span class="bucket-label">Total</span>
              <span class="mono-sm fw-700 text-danger">{{ fmtAmt(apAging.reduce((s,r)=>s+r.total,0)) }}</span>
            </div>
          </div>
        </div>
      </template>
      <div v-else class="empty-msg">{{apRan ? 'No outstanding payables as of this date.' : 'Run the report to see results.'}}</div>
    </div>

    <!-- Trial Balance -->
    <div v-if="activeReport === 'tb'" class="books-card report-card">
      <div class="books-card-title">Trial Balance</div>
      <template v-if="tbLoading"><div class="loading-shimmer" style="height:200px;border-radius:8px"></div></template>
      <template v-else-if="tb?.length">
        <div class="tb-cards">
          <div v-for="row in tb" :key="row.account" class="tb-card">
            <div class="tb-card-top">
              <div class="tb-account-name">{{ row.account }}</div>
              <span class="badge badge-muted" style="font-size:10.5px">{{ row.account_type }}</span>
            </div>
            <div class="tb-buckets">
              <div class="tb-bucket">
                <span class="bucket-label">Opening</span>
                <span class="bucket-val mono-sm" :class="row.opening<0?'red':''">{{ fmtAmt(row.opening||0) }}</span>
              </div>
              <div class="tb-bucket">
                <span class="bucket-label">Debit</span>
                <span class="bucket-val mono-sm green">{{ fmtAmt(row.debit||0) }}</span>
              </div>
              <div class="tb-bucket">
                <span class="bucket-label">Credit</span>
                <span class="bucket-val mono-sm red">{{ fmtAmt(row.credit||0) }}</span>
              </div>
              <div class="tb-bucket">
                <span class="bucket-label">Closing</span>
                <span class="bucket-val mono-sm fw-600" :class="row.closing<0?'red':'green'">{{ fmtAmt(row.closing||0) }}</span>
              </div>
            </div>
          </div>
        </div>
      </template>
      <div v-else class="empty-msg">Run the report to see results.</div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { useFrappeCall, formatCurrency } from "../composables/useFrappe.js";
import { apiGET, resolveCompany } from "../api/client.js";

const fmt    = formatCurrency;
const fmtAmt = (v) => v != null ? "₹" + Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "—";
const fmtN   = (v) => Number(v||0).toLocaleString("en-IN", { maximumFractionDigits: 0 });

const today    = new Date();
const fromDate = ref(new Date(today.getFullYear(), today.getMonth(), 1).toISOString().slice(0,10));
const toDate   = ref(today.toISOString().slice(0,10));
const activeReport = ref("pl");

const { data: pl,  loading: plLoading,  execute: loadPl  } = useFrappeCall("zoho_books_clone.db.queries.get_profit_and_loss");
const { data: bs,  loading: bsLoading,  execute: loadBs  } = useFrappeCall("zoho_books_clone.db.queries.get_balance_sheet_totals");
const { data: cf,  loading: cfLoading,  execute: loadCf  } = useFrappeCall("zoho_books_clone.db.queries.get_cash_flow");
const { data: gst, loading: gstLoading, execute: loadGst } = useFrappeCall("zoho_books_clone.db.queries.get_gst_summary");
const { data: tb,  loading: tbLoading,  execute: loadTb  } = useFrappeCall("zoho_books_clone.db.queries.get_trial_balance");

const arAging  = ref([]);
const apAging  = ref([]);
const plMonthly = ref([]);
const arLoading = ref(false);
const apLoading = ref(false);
const arRan = ref(false);
const apRan = ref(false);

const bsBalanced = computed(() => {
  if (!bs.value) return false;
  const a = Number(bs.value.total_assets) || 0;
  const l = Number(bs.value.total_liabilities) || 0;
  const e = Number(bs.value.total_equity) || 0;
  return Math.abs(a - (l + e)) < 1;
});
const maxMonthlyVal = computed(() => Math.max(...plMonthly.value.flatMap(m => [m.income||0, m.expense||0]), 1));
function barH(v) { return Math.round((Math.max(0,v) / maxMonthlyVal.value) * 80); }

async function runReport() {
  const company = await resolveCompany();
  const args = { company, from_date: fromDate.value, to_date: toDate.value };
  if (activeReport.value === "pl") {
    await loadPl(args);
    try {
      plMonthly.value = await apiGET("zoho_books_clone.db.queries.get_pl_monthly_breakdown", args) || [];
    } catch { plMonthly.value = []; }
  }
  if (activeReport.value === "bs")  await loadBs({ company, as_of_date: toDate.value });
  if (activeReport.value === "cf")  await loadCf(args);
  if (activeReport.value === "gst") await loadGst(args);
  if (activeReport.value === "tb")  await loadTb(args);
  if (activeReport.value === "ar") {
    arLoading.value = true; arRan.value = true;
    try { arAging.value = await apiGET("zoho_books_clone.db.queries.get_ar_aging", { company, as_of_date: toDate.value }) || []; }
    catch { arAging.value = []; }
    arLoading.value = false;
  }
  if (activeReport.value === "ap") {
    apLoading.value = true; apRan.value = true;
    try { apAging.value = await apiGET("zoho_books_clone.db.queries.get_ap_aging", { company, as_of_date: toDate.value }) || []; }
    catch { apAging.value = []; }
    apLoading.value = false;
  }
}

function exportAgingCSV() {
  const isAR = activeReport.value === "ar";
  const rows = isAR ? arAging.value : apAging.value;
  const nameCol = isAR ? "Customer" : "Vendor";
  const keyCol  = isAR ? "customer_name" : "supplier_name";
  const header = [nameCol,"Current","1-30 Days","31-60 Days","61-90 Days","90+ Days","Total"].join(",");
  const lines = rows.map(r =>
    [r[keyCol]||r[isAR?'customer':'supplier'], r.current, r.days_1_30, r.days_31_60, r.days_61_90, r.days_90_plus, r.total]
      .join(",")
  );
  const csv = [header, ...lines].join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = (isAR ? "ar_aging" : "ap_aging") + "_" + toDate.value + ".csv";
  a.click();
  URL.revokeObjectURL(url);
}

const reports = [
  { key: "pl",  label: "Profit & Loss",  icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/></svg>` },
  { key: "bs",  label: "Balance Sheet",  icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="18" rx="2"/><line x1="8" y1="3" x2="8" y2="21"/></svg>` },
  { key: "cf",  label: "Cash Flow",      icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 1l4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><path d="M7 23l-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>` },
  { key: "gst", label: "GST Summary",    icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>` },
  { key: "ar",  label: "AR Aging",       icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>` },
  { key: "ap",  label: "AP Aging",       icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 8 14"/></svg>` },
  { key: "tb",  label: "Trial Balance",  icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>` },
];
</script>

<style scoped>
.page-reports { display: flex; flex-direction: column; gap: 16px; padding: 24px; }
.report-tabs  { display: flex; gap: 8px; flex-wrap: wrap; }
.report-tab {
  display: flex; align-items: center; gap: 7px;
  padding: 8px 16px; border-radius: var(--radius-sm);
  border: 1px solid var(--border); background: var(--surface);
  color: var(--text-3); cursor: pointer; font-size: 13px; font-weight: 600;
  transition: all .15s; font-family: var(--font);
}
.report-tab:hover { border-color: var(--accent); color: var(--text); }
.report-tab.active { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }

.date-range-bar {
  display: flex; align-items: center; gap: 12px; padding: 14px 20px; flex-wrap: wrap;
}
.dr-label { font-size: 12px; font-family: var(--font); color: var(--text-3); letter-spacing: .06em; }
.dr-input {
  background: var(--surface-2); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 6px 10px; color: var(--text);
  font-size: 12.5px; font-family: var(--font); outline: none;
}
.dr-input:focus { border-color: var(--accent); }

.pl-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 0; border-bottom: 1px solid var(--border); font-size: 14px;
}
.pl-row.net { border-bottom: none; font-size: 16px; font-weight: 700; margin-top: 4px; }
.pl-row.profit .mono { color: var(--green); }
.pl-row.loss   .mono { color: var(--red);   }
.pl-divider { height: 2px; background: var(--border); margin: 4px 0; }

.bs-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
@media (max-width: 700px) { .bs-grid { grid-template-columns: 1fr; } }
.bs-block { background: var(--surface-2); border-radius: var(--radius-sm); padding: 18px; }
.bs-section-title { font-size: 10.5px; letter-spacing: .1em; text-transform: uppercase; color: var(--text-3); margin-bottom: 10px; }
.assets .bs-amount    { color: var(--accent); font-size: 20px; font-weight: 700; }
.liabilities .bs-amount { color: var(--red);    font-size: 20px; font-weight: 700; }
.equity .bs-amount    { color: var(--amber);  font-size: 20px; font-weight: 700; }
.bs-eq-sub { display:flex; gap:10px; flex-wrap:wrap; margin-top:6px; font-size:11px; color:#94a3b8; }
.bs-balance-check {
  margin-top: 14px; display:flex; align-items:center; gap:8px; flex-wrap:wrap;
  padding: 10px 14px; border-radius: 8px; font-size: 12.5px; font-weight: 600;
}
.bs-balance-check.bs-ok  { background:#f0fdf4; color:#15803d; border:1px solid #bbf7d0; }
.bs-balance-check.bs-bad { background:#fef2f2; color:#b91c1c; border:1px solid #fecaca; }
.bs-bc-icon { font-weight:800; }
.bs-bc-eq { margin-left:auto; font-family:var(--mono,monospace); font-weight:500; opacity:.85; }

.cf-rows { display: flex; flex-direction: column; gap: 0; }
.cf-row { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid var(--border); font-size: 14px; }
.cf-row.net { border-bottom: none; font-weight: 700; font-size: 15px; margin-top: 4px; }

.aging-table th, .aging-table td { padding: 9px 12px; white-space: nowrap; }
.aging-total { background: #F8F9FA; }
.aging-totals-row td { border-top: 2px solid #E2E8F0; background: #F8F9FA; }

/* GST Cards */
.gst-cards { display: flex; flex-direction: column; gap: 10px; }
.gst-card { background: var(--surface-2); border-radius: var(--radius-sm); padding: 14px 16px; }
.gst-card-header { margin-bottom: 10px; }
.gst-card-body { display: flex; flex-direction: column; gap: 6px; }
.gst-kv { display: flex; justify-content: space-between; align-items: center; font-size: 13px; }
.gst-kv-label { color: var(--text-3); font-size: 12px; }
.gst-kv-value { font-weight: 600; }

/* Aging Cards */
.aging-cards { display: flex; flex-direction: column; gap: 10px; }
.aging-card {
  background: var(--surface-2); border-radius: var(--radius-sm);
  padding: 14px 16px; border: 1px solid var(--border);
}
.aging-card-totals { border: 2px solid var(--border); background: #F8F9FA; }
.aging-card-name { font-size: 13.5px; font-weight: 600; color: var(--text); margin-bottom: 10px; }
.aging-buckets { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; margin-bottom: 10px; }
@media (max-width: 600px) { .aging-buckets { grid-template-columns: repeat(2, 1fr); } }
.aging-bucket { display: flex; flex-direction: column; gap: 3px; }
.bucket-label { font-size: 10.5px; color: var(--text-3); text-transform: uppercase; letter-spacing: .05em; }
.bucket-val { font-size: 13px; }
.aging-card-total {
  display: flex; justify-content: space-between; align-items: center;
  padding-top: 10px; border-top: 1px solid var(--border); font-size: 13px;
}

/* Trial Balance Cards */
.tb-cards { display: flex; flex-direction: column; gap: 10px; }
.tb-card {
  background: var(--surface-2); border-radius: var(--radius-sm);
  padding: 14px 16px; border: 1px solid var(--border);
}
.tb-card-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; margin-bottom: 12px; }
.tb-account-name { font-size: 13px; font-weight: 600; color: var(--text); line-height: 1.4; }
.tb-buckets { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
@media (max-width: 500px) { .tb-buckets { grid-template-columns: repeat(2, 1fr); } }
.tb-bucket { display: flex; flex-direction: column; gap: 3px; }
.text-warn   { color: #E67700; }
.text-danger { color: #C92A2A; }
.fw-600 { font-weight: 600; }
.fw-700 { font-weight: 700; }

.mono-sm  {font-size: 13px; }
.green    { color: var(--green); }
.red      { color: var(--red);   }
.ta-r     { text-align: right; }
.empty-msg { text-align: center; padding: 32px; color: var(--text-3); font-size: 13px; }

.badge { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 10px; font-size: 11.5px; font-weight: 600; }
.badge-blue  { background: #E7F5FF; color: #1971C2; }
.badge-muted { background: #F1F3F5; color: #868E96; }

@media (max-width: 768px) {
  .date-range-bar { padding: 12px 14px; gap: 8px; }
  .report-card { overflow-x: auto; }
}
@media (max-width: 480px) {
  .page-reports { padding: 12px; gap: 12px; }
  .dr-input { width: 100%; }
}
</style>