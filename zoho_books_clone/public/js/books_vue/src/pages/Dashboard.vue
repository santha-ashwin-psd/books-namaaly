<template>
  <div class="ov-wrap">

    <!-- ── Greeting / Hero ──────────────────────────────────────────────── -->
    <div class="ov-hero">
      <div class="ov-hero-left">
        <div class="ov-greeting">{{ greeting }}<span v-if="companyName">, {{ companyName }}</span></div>
        <div class="ov-subgreeting">Here's what's happening in your business today · {{ todayLabel }}</div>
      </div>
      <div class="ov-hero-right">
        <button class="ov-ghost-btn" @click="refreshAll" :disabled="anyLoading">
          <span v-html="iconRefresh" :class="{ 'ov-spin': anyLoading }"></span> Refresh
        </button>
        <button class="ov-primary-btn" @click="navTo('/invoices')">
          <span v-html="iconPlus"></span> New Invoice
        </button>
      </div>
    </div>

    <!-- ── KPI tiles ────────────────────────────────────────────────────── -->
    <div class="ov-kpi-grid">
      <div v-for="kpi in kpiCards" :key="kpi.key"
        class="ov-kpi" :class="kpi.accent"
        @click="kpi.route && navTo(kpi.route)" :style="kpi.route ? 'cursor:pointer' : ''">
        <div class="ov-kpi-head">
          <div class="ov-kpi-icon"><span v-html="kpi.icon"></span></div>
          <span v-if="!kpiLoading && trends[kpi.key]" class="ov-chip"
            :class="trends[kpi.key].up ? 'ov-chip-up' : 'ov-chip-down'">
            <span v-html="trends[kpi.key].up ? iconUp : iconDown"></span>{{ trends[kpi.key].pct }}%
          </span>
        </div>
        <div class="ov-kpi-label">{{ kpi.label }}</div>
        <div class="ov-kpi-value">
          <div v-if="kpiLoading" class="ov-shimmer" style="width:88px;height:24px;border-radius:6px"></div>
          <template v-else>{{ kpi.format === 'currency' ? fmt(kpis?.[kpi.key]) : (kpis?.[kpi.key] ?? 0) }}</template>
        </div>
        <div class="ov-kpi-foot">{{ kpi.sub }}</div>
      </div>
    </div>

    <!-- ── Main split: cash flow + net position ─────────────────────────── -->
    <div class="ov-main">

      <!-- Cash-flow / revenue area chart -->
      <div class="ov-card ov-chart-card">
        <div class="ov-card-head">
          <div>
            <div class="ov-card-title">Revenue Trend</div>
            <div class="ov-card-sub">Invoiced revenue over time</div>
          </div>
          <div class="ov-head-actions">
            <select class="ov-select" v-model.number="trendMonths" @change="loadTrend({ months: trendMonths })">
              <option :value="3">3 months</option>
              <option :value="6">6 months</option>
              <option :value="12">12 months</option>
            </select>
            <button class="ov-link" @click="navTo('/reports')">Reports →</button>
          </div>
        </div>

        <div class="ov-chart-total" v-if="!trendLoading && points.length">
          <span class="ov-chart-total-val">{{ fmt(trendTotal) }}</span>
          <span class="ov-chart-total-lbl">total · last {{ trendMonths }} months</span>
        </div>

        <div v-if="trendLoading" class="ov-shimmer" style="height:220px;border-radius:12px;margin-top:8px"></div>
        <div v-else-if="!points.length" class="ov-empty" style="min-height:220px">
          <div v-html="iconChart" class="ov-empty-icon"></div>
          <div class="ov-empty-title">No revenue yet</div>
          <div class="ov-empty-sub">Create your first invoice to see the trend.</div>
          <button class="ov-primary-btn ov-sm" @click="navTo('/invoices')"><span v-html="iconPlus"></span> New Invoice</button>
        </div>
        <div v-else class="ov-chart-wrap">
          <svg class="ov-svg" :viewBox="`0 0 ${svgW} ${svgH}`" preserveAspectRatio="none">
            <defs>
              <linearGradient id="ov-area" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#2563eb" stop-opacity=".28"/>
                <stop offset="100%" stop-color="#2563eb" stop-opacity="0"/>
              </linearGradient>
            </defs>
            <template v-for="(gl, i) in gridLines" :key="'g'+i">
              <line :x1="padL" :x2="svgW - padR" :y1="gl.y" :y2="gl.y" stroke="#eef2f7" stroke-width="1"/>
              <text :x="padL - 8" :y="gl.y + 4" text-anchor="end" class="ov-axis">{{ gl.label }}</text>
            </template>
            <path v-if="areaPath" :d="areaPath" fill="url(#ov-area)"/>
            <path v-if="linePath" :d="linePath" fill="none" stroke="#2563eb" stroke-width="2.5"
              stroke-linecap="round" stroke-linejoin="round"/>
            <g v-for="(pt, i) in points" :key="'p'+i">
              <circle :cx="pt.x" :cy="pt.y" r="4" fill="#fff" stroke="#2563eb" stroke-width="2.5">
                <title>{{ pt.label }}: {{ fmt(pt.revenue) }}</title>
              </circle>
              <text :x="pt.x" :y="svgH - 5" text-anchor="middle" class="ov-axis">{{ pt.label }}</text>
            </g>
          </svg>
        </div>
      </div>

      <!-- Net position: money in vs out -->
      <div class="ov-card ov-net-card">
        <div class="ov-card-head">
          <div>
            <div class="ov-card-title">Money In vs Out</div>
            <div class="ov-card-sub">Open receivables & payables</div>
          </div>
        </div>

        <div class="ov-net-body">
          <div class="ov-net-row">
            <div class="ov-net-dot ov-in"></div>
            <div class="ov-net-info">
              <div class="ov-net-lbl">Receivables (AR)</div>
              <div class="ov-net-val ov-tin">{{ fmt(arTotal) }}</div>
            </div>
          </div>
          <div class="ov-net-row">
            <div class="ov-net-dot ov-out"></div>
            <div class="ov-net-info">
              <div class="ov-net-lbl">Payables (AP)</div>
              <div class="ov-net-val ov-tout">{{ fmt(apTotal) }}</div>
            </div>
          </div>

          <div class="ov-net-bar" v-if="arTotal || apTotal">
            <div class="ov-net-bar-in" :style="{ width: inPct + '%' }"></div>
            <div class="ov-net-bar-out" :style="{ width: (100 - inPct) + '%' }"></div>
          </div>

          <div class="ov-net-split">
            <div class="ov-net-net">
              <span class="ov-net-net-lbl">Net position</span>
              <span class="ov-net-net-val" :class="(arTotal - apTotal) >= 0 ? 'ov-tin' : 'ov-tout'">
                {{ (arTotal - apTotal) >= 0 ? '+' : '' }}{{ fmt(arTotal - apTotal) }}
              </span>
            </div>
          </div>
        </div>

        <div class="ov-net-actions">
          <button class="ov-mini-btn" @click="navTo('/invoices')">View AR</button>
          <button class="ov-mini-btn" @click="navTo('/purchases')">View AP</button>
        </div>
      </div>
    </div>

    <!-- ── Aging (AR + AP) ──────────────────────────────────────────────── -->
    <div class="ov-card">
      <div class="ov-card-head">
        <div>
          <div class="ov-card-title">Aging Summary</div>
          <div class="ov-card-sub">How overdue your receivables & payables are</div>
        </div>
      </div>
      <div class="ov-aging-grid">
        <div class="ov-aging-col">
          <div class="ov-aging-head"><span class="ov-badge ov-badge-blue">Receivables</span><span class="ov-aging-tot">{{ fmt(agingTotal(aging)) }}</span></div>
          <div v-if="agingLoading" class="ov-aging-rows">
            <div v-for="n in 5" :key="n" class="ov-aging-row"><div class="ov-shimmer" style="height:8px;flex:1;border-radius:20px"></div></div>
          </div>
          <div v-else class="ov-aging-rows">
            <div v-for="b in agingRows(aging)" :key="b.key" class="ov-aging-row">
              <span class="ov-aging-lbl">{{ b.label }}</span>
              <div class="ov-aging-track"><div class="ov-aging-fill" :style="{ width: b.pct + '%', background: b.color }"></div></div>
              <span class="ov-aging-amt" :style="{ color: b.color }">{{ fmt(agingVal(aging, b.key)) }}</span>
            </div>
          </div>
        </div>
        <div class="ov-aging-col">
          <div class="ov-aging-head"><span class="ov-badge ov-badge-amber">Payables</span><span class="ov-aging-tot">{{ fmt(agingTotal(apAging)) }}</span></div>
          <div v-if="apAgingLoading" class="ov-aging-rows">
            <div v-for="n in 5" :key="n" class="ov-aging-row"><div class="ov-shimmer" style="height:8px;flex:1;border-radius:20px"></div></div>
          </div>
          <div v-else class="ov-aging-rows">
            <div v-for="b in agingRows(apAging)" :key="b.key" class="ov-aging-row">
              <span class="ov-aging-lbl">{{ b.label }}</span>
              <div class="ov-aging-track"><div class="ov-aging-fill" :style="{ width: b.pct + '%', background: b.color }"></div></div>
              <span class="ov-aging-amt" :style="{ color: b.color }">{{ fmt(agingVal(apAging, b.key)) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Lists: top customers + overdue ───────────────────────────────── -->
    <div class="ov-lists">
      <div class="ov-card">
        <div class="ov-card-head">
          <div class="ov-card-title">Top Customers</div>
          <button class="ov-link" @click="navTo('/customers')">View all</button>
        </div>
        <div v-if="dashLoading" class="ov-shimmer" style="height:150px;border-radius:10px"></div>
        <template v-else-if="dash?.top_customers?.length">
          <div class="ov-rank">
            <div v-for="(c, i) in dash.top_customers.slice(0,5)" :key="c.customer" class="ov-rank-row"
              @click="navTo('/customers/' + encodeURIComponent(c.customer))">
              <div class="ov-rank-badge" :class="'ov-rank-' + (i+1)">{{ i + 1 }}</div>
              <div class="ov-rank-info">
                <div class="ov-rank-name">{{ c.customer_name || c.customer }}</div>
                <div class="ov-rank-sub">{{ c.invoice_count }} invoice{{ c.invoice_count == 1 ? '' : 's' }}</div>
              </div>
              <div class="ov-rank-amt">{{ fmt(c.total_revenue) }}</div>
            </div>
          </div>
        </template>
        <div v-else class="ov-empty">
          <div v-html="iconUsers" class="ov-empty-icon"></div>
          <div class="ov-empty-title">No customers yet</div>
          <button class="ov-primary-btn ov-sm" @click="navTo('/customers')"><span v-html="iconPlus"></span> Add Customer</button>
        </div>
      </div>

      <div class="ov-card">
        <div class="ov-card-head">
          <div class="ov-card-title">Overdue Invoices</div>
          <span class="ov-badge" :class="dash?.overdue_invoices?.length ? 'ov-badge-red' : 'ov-badge-green'">
            {{ dash?.overdue_invoices?.length || 0 }} overdue
          </span>
        </div>
        <div v-if="dashLoading" class="ov-shimmer" style="height:150px;border-radius:10px"></div>
        <template v-else-if="dash?.overdue_invoices?.length">
          <div class="ov-od">
            <div v-for="inv in dash.overdue_invoices.slice(0,5)" :key="inv.name" class="ov-od-row"
              @click="navTo({ path: '/invoices', query: { open: inv.name } })">
              <div class="ov-od-info">
                <div class="ov-od-name">{{ inv.name }}</div>
                <div class="ov-od-sub">{{ inv.customer_name || inv.customer }}</div>
              </div>
              <div class="ov-od-right">
                <div class="ov-od-amt">{{ fmt(inv.outstanding_amount) }}</div>
                <div class="ov-od-due">due {{ fmtDate(inv.due_date) }}</div>
              </div>
            </div>
          </div>
        </template>
        <div v-else class="ov-empty">
          <div v-html="iconCheck" class="ov-empty-icon ov-ok"></div>
          <div class="ov-empty-title" style="color:#16a34a">All caught up!</div>
          <div class="ov-empty-sub">No overdue invoices.</div>
        </div>
      </div>
    </div>

    <!-- ── Activity timeline ────────────────────────────────────────────── -->
    <div class="ov-card">
      <div class="ov-card-head">
        <div class="ov-card-title">Recent Activity</div>
        <button class="ov-link" @click="navTo('/reports')">View all →</button>
      </div>
      <div v-if="activityLoading" class="ov-shimmer" style="height:120px;border-radius:10px"></div>
      <template v-else-if="activity?.length">
        <div class="ov-timeline">
          <div v-for="row in activity" :key="row.name" class="ov-tl-row" @click="openActivity(row)">
            <div class="ov-tl-dot" :class="actDotClass(row.doctype)"><span v-html="actIcon(row.doctype)"></span></div>
            <div class="ov-tl-body">
              <div class="ov-tl-desc">{{ activityDesc(row) }} · <span class="ov-tl-doc">{{ row.name }}</span></div>
              <div class="ov-tl-date">{{ fmtDate(row.date) }}</div>
            </div>
            <div class="ov-tl-amt" :class="row.doctype === 'Payment Entry' ? 'ov-tin' : ''">{{ fmt(row.amount) }}</div>
          </div>
        </div>
      </template>
      <div v-else class="ov-empty" style="padding:24px 0"><div class="ov-empty-sub">No recent activity</div></div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useFrappeCall, formatCurrency, formatDate } from "../composables/useFrappe.js";
import { apiGET } from "../api/client.js";

const router  = useRouter();
const fmt      = (v) => formatCurrency(v);
const fmtDate  = formatDate;
const navTo    = (p) => router.push(p);
const trendMonths = ref(6);

// ── Greeting ──
const companyName = ref(window.__booksCompany || "");
const greeting = computed(() => {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
});
const todayLabel = new Date().toLocaleDateString("en-IN", { weekday: "long", day: "2-digit", month: "long", year: "numeric" });

// ── API (same endpoints as the classic dashboard — real data) ──
const { data: dash,     loading: dashLoading,     execute: loadDash     } = useFrappeCall("zoho_books_clone.api.dashboard.get_home_dashboard");
const { data: kpis,     loading: kpiLoading,      execute: loadKpis     } = useFrappeCall("zoho_books_clone.db.aggregates.get_dashboard_kpis");
const { data: trend,    loading: trendLoading,    execute: loadTrend    } = useFrappeCall("zoho_books_clone.db.aggregates.get_monthly_revenue_trend");
const { data: aging,    loading: agingLoading,    execute: loadAging    } = useFrappeCall("zoho_books_clone.db.aggregates.get_aging_buckets");
const { data: apAging,  loading: apAgingLoading,  execute: loadApAging  } = useFrappeCall("zoho_books_clone.api.dashboard.get_ap_aging_buckets");
const { data: activity, loading: activityLoading, execute: loadActivity } = useFrappeCall("zoho_books_clone.api.dashboard.get_recent_activity");

const anyLoading = computed(() => kpiLoading.value || dashLoading.value || trendLoading.value || activityLoading.value);

function refreshAll() {
  loadDash(); loadKpis(); loadTrend({ months: trendMonths.value }); loadAging(); loadApAging(); loadActivity();
}
onMounted(() => {
  refreshAll();
  if (!companyName.value) {
    apiGET("zoho_books_clone.api.admin.get_company_settings")
      .then(d => { companyName.value = d?.default_company || ""; }).catch(() => {});
  }
});

function openActivity(row) {
  const path = { "Sales Invoice": "/invoices", "Purchase Invoice": "/purchases", "Payment Entry": "/payments" }[row.doctype];
  if (path) navTo({ path, query: { open: row.name } });
}

// ── Helpers ──
const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const monthLabel = (m) => m ? (MONTHS[parseInt(m.slice(5, 7)) - 1] ?? m.slice(5)) : "";
function fmtShort(v) {
  if (!v) return "0";
  // standard K/M grouping (was Indian Lakh/Crore — not applicable to OMR)
  if (v >= 1_000_000) return "OMR " + (v / 1_000_000).toFixed(1) + "M";
  if (v >= 1_000)      return "OMR " + (v / 1_000).toFixed(1) + "K";
  return "OMR " + v.toFixed(3);
}

// ── KPI tiles ──
const kpiCards = [
  { key: "month_revenue",     label: "Revenue (MTD)",   sub: "This month",       format: "currency", accent: "ov-a-blue",  icon: iconGlyph("rev"),   route: "/invoices", prevKey: "prev_month_revenue" },
  { key: "month_collected",   label: "Collected",       sub: "Payments in",      format: "currency", accent: "ov-a-green", icon: iconGlyph("check"), route: "/payments", prevKey: "prev_month_collected" },
  { key: "month_outstanding", label: "Outstanding",     sub: "Awaiting payment", format: "currency", accent: "ov-a-amber", icon: iconGlyph("clock"), route: "/invoices" },
  { key: "overdue_count",     label: "Overdue",         sub: "Needs attention",  format: "number",   accent: "ov-a-red",   icon: iconGlyph("alert"), route: "/invoices" },
];
const num = (v) => Number(v) || 0;
const trends = computed(() => {
  const out = {}, k = kpis.value;
  if (!k) return out;
  for (const c of kpiCards) {
    if (!c.prevKey) continue;
    const prev = num(k[c.prevKey]);
    if (prev <= 0) continue;
    const pct = ((num(k[c.key]) - prev) / prev) * 100;
    out[c.key] = { pct: Math.abs(pct).toFixed(0), up: pct >= 0 };
  }
  return out;
});

// ── Revenue chart ──
const svgW = 640, svgH = 220, padL = 48, padR = 12, padT = 18, padB = 26;
const rows = computed(() => trend.value || []);
const trendTotal = computed(() => rows.value.reduce((s, r) => s + (r.revenue || 0), 0));
const maxRevenue = computed(() => Math.max(...rows.value.map(r => r.revenue || 0), 1));
const gridLines = computed(() => {
  const max = maxRevenue.value, chartH = svgH - padT - padB;
  return [
    { y: padT,              label: fmtShort(max) },
    { y: padT + chartH / 2, label: fmtShort(max / 2) },
    { y: svgH - padB,       label: "0" },
  ];
});
const points = computed(() => {
  const r = rows.value;
  if (!r.length) return [];
  const max = maxRevenue.value, n = r.length;
  const step = n > 1 ? (svgW - padL - padR) / (n - 1) : 0;
  return r.map((row, i) => ({
    x: n > 1 ? padL + i * step : svgW / 2,
    y: padT + (1 - (row.revenue || 0) / max) * (svgH - padT - padB),
    label: monthLabel(row.month), revenue: row.revenue || 0,
  }));
});
const linePath = computed(() => {
  const p = points.value;
  return p.length < 2 ? "" : p.map((pt, i) => `${i ? "L" : "M"}${pt.x.toFixed(1)},${pt.y.toFixed(1)}`).join(" ");
});
const areaPath = computed(() => {
  const p = points.value;
  if (p.length < 2) return "";
  const base = svgH - padB;
  return p.map((pt, i) => `${i ? "L" : "M"}${pt.x.toFixed(1)},${pt.y.toFixed(1)}`).join(" ")
    + ` L${p.at(-1).x.toFixed(1)},${base} L${p[0].x.toFixed(1)},${base} Z`;
});

// ── Aging ──
const AGING_BUCKETS = [
  { key: "current", label: "Current",    color: "#16a34a" },
  { key: "1_30",    label: "1–30 days",  color: "#2563eb" },
  { key: "31_60",   label: "31–60 days", color: "#f59e0b" },
  { key: "61_90",   label: "61–90 days", color: "#fb923c" },
  { key: "over_90", label: "90+ days",   color: "#dc2626" },
];
const _d = (data) => (data?.value || data || {});
const agingVal = (data, key) => num(_d(data)[key]);
function agingRows(data) {
  const d = _d(data);
  const total = Object.values(d).reduce((a, v) => a + (v || 0), 0) || 1;
  return AGING_BUCKETS.map(b => ({ ...b, pct: Math.min(100, ((d[b.key] || 0) / total) * 100) }));
}
const agingTotal = (data) => Object.values(_d(data)).reduce((a, v) => a + (v || 0), 0);
const arTotal = computed(() => agingTotal(aging));
const apTotal = computed(() => agingTotal(apAging));
const inPct = computed(() => {
  const t = arTotal.value + apTotal.value;
  return t ? Math.round((arTotal.value / t) * 100) : 50;
});

// ── Activity ──
function activityDesc(row) {
  if (row.doctype === "Payment Entry") return `Payment from ${row.party || "—"}`;
  if (row.doctype === "Sales Invoice") return `Invoice · ${row.party || "—"}`;
  if (row.doctype === "Purchase Invoice") return `Bill · ${row.party || "—"}`;
  return row.party || row.name;
}
const actDotClass = (dt) => dt === "Sales Invoice" ? "ov-d-inv" : dt === "Purchase Invoice" ? "ov-d-bill" : "ov-d-pay";
function actIcon(dt) {
  if (dt === "Payment Entry") return iconGlyph("check");
  if (dt === "Purchase Invoice") return iconGlyph("bill");
  return iconGlyph("rev");
}

// ── Inline SVG glyphs ──
function iconGlyph(k) {
  const s = 'width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"';
  const map = {
    rev:   `<svg ${s}><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>`,
    check: `<svg ${s} stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>`,
    clock: `<svg ${s}><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
    alert: `<svg ${s}><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
    bill:  `<svg ${s}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`,
  };
  return map[k] || "";
}
const iconPlus    = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>`;
const iconRefresh = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>`;
const iconUp      = `<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="18 15 12 9 6 15"/></svg>`;
const iconDown    = `<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="6 9 12 15 18 9"/></svg>`;
const iconChart   = `<svg width="46" height="46" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.4"><rect x="2" y="3" width="20" height="14" rx="2"/><polyline points="5 10 9 6 13 10 17 7"/></svg>`;
const iconUsers   = `<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.4"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>`;
const iconCheck   = `<svg width="40" height="40" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="12" fill="#dcfce7"/><polyline points="7 12.5 10.5 16 17 9" stroke="#16a34a" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
</script>

<style scoped>
.ov-wrap {
  display: flex; flex-direction: column; gap: 16px;
  padding: 24px 28px;
  font-family: "Plus Jakarta Sans", Lato, system-ui, sans-serif;
  background: #f8fafc; min-height: 100%;
  color: #0f172a;
}

/* ── Hero ── */
.ov-hero {
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
  padding: 22px 26px; border-radius: 16px;
  background: linear-gradient(120deg, #1e3a8a 0%, #2563eb 55%, #3b82f6 100%);
  color: #fff; box-shadow: 0 10px 26px rgba(37,99,235,.22);
}
.ov-greeting { font-size: 21px; font-weight: 800; letter-spacing: -.02em; }
.ov-subgreeting { font-size: 12.5px; opacity: .85; margin-top: 3px; }
.ov-hero-right { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.ov-primary-btn {
  display: inline-flex; align-items: center; gap: 7px;
  background: #fff; color: #1d4ed8; border: none; border-radius: 10px;
  padding: 9px 16px; font-size: 13px; font-weight: 700; cursor: pointer;
  font-family: inherit; transition: transform .12s, box-shadow .12s;
}
.ov-primary-btn:hover { transform: translateY(-1px); box-shadow: 0 6px 16px rgba(0,0,0,.16); }
.ov-primary-btn.ov-sm { padding: 8px 14px; font-size: 12.5px; }
.ov-ghost-btn {
  display: inline-flex; align-items: center; gap: 7px;
  background: rgba(255,255,255,.14); color: #fff;
  border: 1px solid rgba(255,255,255,.28); border-radius: 10px;
  padding: 9px 14px; font-size: 12.5px; font-weight: 600; cursor: pointer;
  font-family: inherit; transition: background .12s;
}
.ov-ghost-btn:hover { background: rgba(255,255,255,.24); }
.ov-ghost-btn:disabled { opacity: .7; cursor: default; }
.ov-spin { display: inline-flex; animation: ov-rot 1s linear infinite; }
@keyframes ov-rot { to { transform: rotate(360deg); } }

/* ── KPI tiles ── */
.ov-kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.ov-kpi {
  position: relative; background: #fff; border: 1px solid #eef1f5;
  border-radius: 14px; padding: 16px 18px;
  box-shadow: 0 1px 2px rgba(15,23,42,.04);
  transition: box-shadow .15s, transform .15s;
  overflow: hidden;
}
.ov-kpi::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; }
.ov-kpi:hover { box-shadow: 0 8px 22px rgba(15,23,42,.09); transform: translateY(-2px); }
.ov-a-blue::before  { background: #2563eb; } .ov-a-blue  .ov-kpi-icon { background: #eff6ff; color: #2563eb; }
.ov-a-green::before { background: #16a34a; } .ov-a-green .ov-kpi-icon { background: #f0fdf4; color: #16a34a; }
.ov-a-amber::before { background: #f59e0b; } .ov-a-amber .ov-kpi-icon { background: #fff7ed; color: #ea580c; }
.ov-a-red::before   { background: #e11d48; } .ov-a-red   .ov-kpi-icon { background: #fff1f2; color: #e11d48; }
.ov-kpi-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.ov-kpi-icon { width: 34px; height: 34px; border-radius: 9px; display: flex; align-items: center; justify-content: center; }
.ov-chip { display: inline-flex; align-items: center; gap: 3px; font-size: 11px; font-weight: 700; padding: 3px 7px; border-radius: 20px; }
.ov-chip-up { background: #f0fdf4; color: #16a34a; } .ov-chip-down { background: #fef2f2; color: #dc2626; }
.ov-kpi-label { font-size: 11.5px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: .05em; }
.ov-kpi-value { font-size: 24px; font-weight: 800; letter-spacing: -.03em; margin-top: 3px; line-height: 1.15; }
.ov-kpi-foot { font-size: 11.5px; color: #94a3b8; margin-top: 2px; }

/* ── Cards ── */
.ov-card { background: #fff; border: 1px solid #eef1f5; border-radius: 14px; padding: 20px 22px; box-shadow: 0 1px 2px rgba(15,23,42,.04); }
.ov-card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.ov-card-title { font-size: 15px; font-weight: 700; color: #0f172a; }
.ov-card-sub { font-size: 12px; color: #94a3b8; margin-top: 2px; }
.ov-head-actions { display: flex; align-items: center; gap: 10px; }
.ov-link { background: none; border: none; cursor: pointer; font-size: 12.5px; font-weight: 600; color: #2563eb; font-family: inherit; padding: 0; }
.ov-link:hover { text-decoration: underline; }
.ov-select {
  background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; border-radius: 20px;
  padding: 5px 26px 5px 12px; font-size: 11.5px; font-weight: 600; font-family: inherit; cursor: pointer; outline: none;
  appearance: none; -webkit-appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 24 24' fill='none' stroke='%23475569' stroke-width='3'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat: no-repeat; background-position: right 10px center;
}

/* ── Main split ── */
.ov-main { display: grid; grid-template-columns: 1.9fr 1fr; gap: 16px; }
.ov-chart-card { display: flex; flex-direction: column; }
.ov-chart-total { display: flex; align-items: baseline; gap: 8px; }
.ov-chart-total-val { font-size: 22px; font-weight: 800; letter-spacing: -.03em; color: #0f172a; }
.ov-chart-total-lbl { font-size: 12px; color: #94a3b8; }
.ov-chart-wrap { width: 100%; margin-top: 6px; }
.ov-svg { width: 100%; height: 220px; display: block; overflow: visible; }
.ov-axis { font-size: 10.5px; fill: #94a3b8; font-family: inherit; }

/* ── Net position ── */
.ov-net-card { display: flex; flex-direction: column; }
.ov-net-body { display: flex; flex-direction: column; gap: 14px; flex: 1; }
.ov-net-row { display: flex; align-items: center; gap: 12px; }
.ov-net-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.ov-in { background: #16a34a; } .ov-out { background: #ea580c; }
.ov-net-info { display: flex; align-items: center; justify-content: space-between; flex: 1; }
.ov-net-lbl { font-size: 12.5px; color: #64748b; font-weight: 500; }
.ov-net-val { font-size: 16px; font-weight: 800; letter-spacing: -.02em; }
.ov-tin { color: #16a34a; } .ov-tout { color: #ea580c; }
.ov-net-bar { display: flex; height: 10px; border-radius: 20px; overflow: hidden; background: #f1f5f9; }
.ov-net-bar-in { background: #16a34a; } .ov-net-bar-out { background: #ea580c; }
.ov-net-split { margin-top: 2px; border-top: 1px solid #f1f5f9; padding-top: 12px; }
.ov-net-net { display: flex; align-items: center; justify-content: space-between; }
.ov-net-net-lbl { font-size: 12.5px; font-weight: 700; color: #334155; }
.ov-net-net-val { font-size: 17px; font-weight: 800; letter-spacing: -.02em; }
.ov-net-actions { display: flex; gap: 8px; margin-top: 16px; }
.ov-mini-btn { flex: 1; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 9px; padding: 8px; font-size: 12px; font-weight: 600; color: #475569; cursor: pointer; font-family: inherit; transition: all .12s; }
.ov-mini-btn:hover { border-color: #2563eb; color: #2563eb; background: #f4f8ff; }

/* ── Aging ── */
.ov-aging-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 26px; }
.ov-aging-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.ov-aging-tot { font-size: 13px; font-weight: 800; color: #0f172a; }
.ov-aging-rows { display: flex; flex-direction: column; gap: 12px; }
.ov-aging-row { display: grid; grid-template-columns: 74px 1fr 70px; align-items: center; gap: 10px; }
.ov-aging-lbl { font-size: 12px; color: #64748b; }
.ov-aging-track { background: #f1f5f9; border-radius: 20px; height: 8px; overflow: hidden; }
.ov-aging-fill { height: 100%; border-radius: 20px; transition: width .6s ease; }
.ov-aging-amt { font-size: 12px; font-weight: 700; text-align: right; }

/* ── Badges ── */
.ov-badge { display: inline-flex; align-items: center; padding: 3px 10px; border-radius: 20px; font-size: 11.5px; font-weight: 700; }
.ov-badge-blue { background: #eff6ff; color: #1d4ed8; } .ov-badge-amber { background: #fff7ed; color: #c2410c; }
.ov-badge-red  { background: #fef2f2; color: #b91c1c; } .ov-badge-green { background: #f0fdf4; color: #15803d; }

/* ── Lists ── */
.ov-lists { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.ov-rank, .ov-od { display: flex; flex-direction: column; }
.ov-rank-row { display: flex; align-items: center; gap: 12px; padding: 9px 6px; border-radius: 9px; cursor: pointer; transition: background .12s; }
.ov-rank-row:hover, .ov-od-row:hover { background: #f8fafc; }
.ov-rank-badge { width: 26px; height: 26px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 800; color: #fff; flex-shrink: 0; background: #94a3b8; }
.ov-rank-1 { background: #f59e0b; } .ov-rank-2 { background: #64748b; } .ov-rank-3 { background: #b45309; }
.ov-rank-info { flex: 1; min-width: 0; }
.ov-rank-name { font-size: 13px; font-weight: 600; color: #0f172a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ov-rank-sub { font-size: 11.5px; color: #94a3b8; }
.ov-rank-amt { font-size: 13px; font-weight: 700; color: #16a34a; }
.ov-od-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 6px; border-radius: 9px; cursor: pointer; transition: background .12s; border-bottom: 1px solid #f4f6f9; }
.ov-od-row:last-child { border-bottom: none; }
.ov-od-name { font-size: 13px; font-weight: 700; color: #2563eb; }
.ov-od-sub { font-size: 11.5px; color: #94a3b8; margin-top: 1px; }
.ov-od-right { text-align: right; }
.ov-od-amt { font-size: 13px; font-weight: 700; color: #dc2626; }
.ov-od-due { font-size: 11px; color: #94a3b8; margin-top: 1px; }

/* ── Timeline ── */
.ov-timeline { display: flex; flex-direction: column; }
.ov-tl-row { display: flex; align-items: center; gap: 12px; padding: 10px 6px; border-radius: 9px; cursor: pointer; transition: background .12s; }
.ov-tl-row:hover { background: #f8fafc; }
.ov-tl-dot { width: 30px; height: 30px; border-radius: 9px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.ov-d-inv  { background: #eff6ff; color: #2563eb; }
.ov-d-bill { background: #fff7ed; color: #ea580c; }
.ov-d-pay  { background: #f0fdf4; color: #16a34a; }
.ov-tl-body { flex: 1; min-width: 0; }
.ov-tl-desc { font-size: 13px; color: #334155; font-weight: 500; }
.ov-tl-doc { color: #2563eb; font-weight: 600; }
.ov-tl-date { font-size: 11.5px; color: #94a3b8; margin-top: 1px; }
.ov-tl-amt { font-size: 13px; font-weight: 700; color: #334155; flex-shrink: 0; }

/* ── Empty / shimmer ── */
.ov-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; padding: 30px 16px; text-align: center; }
.ov-empty-icon { opacity: .8; } .ov-empty-icon.ov-ok { opacity: 1; }
.ov-empty-title { font-size: 14px; font-weight: 700; color: #334155; }
.ov-empty-sub { font-size: 12.5px; color: #94a3b8; line-height: 1.5; max-width: 240px; }
.ov-shimmer { background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%); background-size: 200% 100%; animation: ov-sh 1.4s infinite; }
@keyframes ov-sh { 0% { background-position: 200% 0 } 100% { background-position: -200% 0 } }

/* ── Responsive ── */
@media (max-width: 1200px) {
  .ov-main { grid-template-columns: 1fr; }
  .ov-kpi-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 900px) {
  .ov-lists { grid-template-columns: 1fr; }
  .ov-aging-grid { grid-template-columns: 1fr; gap: 20px; }
}
@media (max-width: 768px) {
  .ov-wrap { padding: 16px; gap: 14px; }
  .ov-hero { flex-direction: column; align-items: flex-start; gap: 14px; padding: 18px 20px; }
  .ov-hero-right { width: 100%; }
  .ov-primary-btn { flex: 1; justify-content: center; }
}
@media (max-width: 480px) {
  .ov-wrap { padding: 12px 10px; gap: 12px; }
  .ov-kpi-grid { grid-template-columns: 1fr 1fr; gap: 10px; }
  .ov-kpi { padding: 13px 14px; }
  .ov-kpi-value { font-size: 20px; }
  .ov-card { padding: 16px 16px; border-radius: 12px; }
  .ov-greeting { font-size: 18px; }
  .ov-aging-row { grid-template-columns: 62px 1fr 62px; }
}
</style>