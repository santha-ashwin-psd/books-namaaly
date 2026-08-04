<template>
<div class="arx-page">
  <div class="arx-panel">

    <!-- Header -->
    <div class="arx-hdr">
      <div>
        <div class="arx-hdr-title">📊 Asset Reports</div>
        <div class="arx-hdr-sub">{{ tabs.find(t => t.id === activeTab)?.desc }}</div>
      </div>
      <div class="arx-hdr-actions">
        <button v-if="result" class="arx-btn arx-btn-light" @click="exportCSV">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          Export CSV
        </button>
        <button class="arx-btn arx-btn-ast" @click="runReport" :disabled="loading">
          <span v-if="loading" class="arx-spinner"></span>
          <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
          {{ loading ? 'Running…' : 'Run Report' }}
        </button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="arx-tabs">
      <button v-for="t in tabs" :key="t.id"
        class="arx-tab" :class="{ active: activeTab === t.id }"
        @click="activeTab = t.id; result = null">
        <span class="arx-tab-ic">{{ t.icon }}</span> {{ t.label }}
      </button>
    </div>

    <!-- Filters -->
    <div class="arx-filters">
      <div>
        <div class="arx-hf-label">Company</div>
        <SearchableSelect
          v-model="filters.company"
          :options="companyOptions"
          placeholder="All companies"
        />
      </div>
      <div>
        <div class="arx-hf-label">Asset Category</div>
        <SearchableSelect
          v-model="filters.asset_category"
          :options="categoryOptions"
          placeholder="All categories"
        />
      </div>

      <div v-if="activeTab === 'register'">
        <div class="arx-hf-label">Status</div>
        <select class="arx-fi" v-model="filters.status">
          <option value="All">All</option>
          <option value="Active">Active</option>
          <option value="Draft">Draft</option>
          <option value="Submitted">Submitted</option>
          <option value="Scrapped">Scrapped</option>
          <option value="Sold">Sold</option>
        </select>
      </div>
      <div v-if="activeTab === 'register'">
        <div class="arx-hf-label">As On Date</div>
        <input type="date" class="arx-fi" v-model="filters.as_on_date" />
      </div>
      <div v-if="activeTab === 'register'">
        <div class="arx-hf-label">Include Draft</div>
        <select class="arx-fi" v-model="filters.include_draft">
          <option :value="false">No</option>
          <option :value="true">Yes</option>
        </select>
      </div>

      <template v-if="activeTab === 'forecast'">
        <div>
          <div class="arx-hf-label">Status</div>
          <select class="arx-fi" v-model="filters.status">
            <option value="Pending">Pending</option>
            <option value="Completed">Completed</option>
            <option value="All">All</option>
          </select>
        </div>
        <div>
          <div class="arx-hf-label">From Date</div>
          <input type="date" class="arx-fi" v-model="filters.from_date" />
        </div>
        <div>
          <div class="arx-hf-label">To Date</div>
          <input type="date" class="arx-fi" v-model="filters.to_date" />
        </div>
      </template>

      <template v-if="activeTab === 'disposal'">
        <div>
          <div class="arx-hf-label">Disposal Type</div>
          <select class="arx-fi" v-model="filters.disposal_type">
            <option value="All">All</option>
            <option value="Scrap">Scrap</option>
            <option value="Sale">Sale</option>
          </select>
        </div>
        <div>
          <div class="arx-hf-label">From Date</div>
          <input type="date" class="arx-fi" v-model="filters.from_date" />
        </div>
        <div>
          <div class="arx-hf-label">To Date</div>
          <input type="date" class="arx-fi" v-model="filters.to_date" />
        </div>
      </template>
    </div>

    <!-- Body -->
    <div class="arx-body">

      <div v-if="loading" class="shimmer" style="height:220px;border-radius:10px"></div>

      <template v-else-if="result">
        <!-- KPI strip -->
        <div v-if="summary" class="arx-kpi-grid" :style="`grid-template-columns:repeat(${summaryKpis.length},1fr)`">
          <div v-for="kpi in summaryKpis" :key="kpi.label" class="arx-kpi-cell">
            <div class="arx-kpi-lbl">{{ kpi.label }}</div>
            <div class="arx-kpi-val" :style="kpi.color ? `color:${kpi.color}` : ''">{{ kpi.value }}</div>
          </div>
        </div>

        <!-- ── Asset Register ── -->
        <div v-if="activeTab === 'register'" class="arx-table-wrap">
          <div v-if="!result.rows.length" class="arx-empty">No assets found for the selected filters.</div>
          <table v-else class="arx-table">
            <thead>
              <tr>
                <th>Asset</th><th>Category</th><th>Location</th>
                <th style="text-align:right;">Purchase Cost</th>
                <th style="text-align:right;">Accum. Depreciation</th>
                <th style="text-align:right;">Net Book Value</th>
                <th>Status</th><th>Purchased</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in result.rows" :key="r.name" class="arx-row" @click="router.push(`/assets/${r.name}`)">
                <td class="arx-link">{{ r.asset_name || r.name }}<div class="arx-sub">{{ r.name }}</div></td>
                <td class="arx-sub">{{ categoryLabel(r.asset_category) || '—' }}</td>
                <td class="arx-sub">{{ r.location || '—' }}</td>
                <td style="text-align:right;">{{ fmt(r.purchase_cost) }}</td>
                <td style="text-align:right;">{{ fmt(r.accumulated_depreciation) }}</td>
                <td style="text-align:right;font-weight:700;color:var(--bx-astB);">{{ fmt(r.current_value) }}</td>
                <td><span class="arx-badge" :class="statusClass(r.status)">{{ r.status }}</span></td>
                <td class="arx-sub">{{ r.purchase_date?.slice(0,10) }}</td>
              </tr>
            </tbody>
            <tfoot>
              <tr class="arx-tfoot">
                <td colspan="3">Totals</td>
                <td style="text-align:right;">{{ fmt(result.summary.total_purchase_cost) }}</td>
                <td style="text-align:right;">{{ fmt(result.summary.total_accumulated_depreciation) }}</td>
                <td style="text-align:right;color:var(--bx-astB);">{{ fmt(result.summary.total_net_book_value) }}</td>
                <td colspan="2"></td>
              </tr>
            </tfoot>
          </table>
          <div v-if="result.rows.length" class="arx-cards-wrap">
            <div v-for="r in result.rows" :key="r.name" class="arx-rcard" @click="router.push(`/assets/${r.name}`)">
              <div class="arx-rcard-top">
                <span class="arx-link">{{ r.asset_name || r.name }}</span>
                <span class="arx-badge" :class="statusClass(r.status)">{{ r.status }}</span>
              </div>
              <div class="arx-sub">{{ r.name }} · {{ categoryLabel(r.asset_category) || '—' }} · {{ r.location || '—' }}</div>
              <div class="arx-rcard-meta">
                <div><span class="arx-rcard-mlbl">Cost</span>{{ fmt(r.purchase_cost) }}</div>
                <div><span class="arx-rcard-mlbl">Accum. Dep.</span>{{ fmt(r.accumulated_depreciation) }}</div>
                <div><span class="arx-rcard-mlbl">NBV</span><span style="font-weight:700;color:var(--bx-astB);">{{ fmt(r.current_value) }}</span></div>
                <div><span class="arx-rcard-mlbl">Purchased</span>{{ r.purchase_date?.slice(0,10) }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- ── CWIP Register ── -->
        <div v-if="activeTab === 'cwip'" class="arx-table-wrap">
          <div v-if="!result.rows.length" class="arx-empty">No assets currently in Capital Work-in-Progress.</div>
          <table v-else class="arx-table">
            <thead>
              <tr>
                <th>Asset</th><th>Category</th>
                <th style="text-align:right;">CWIP Balance</th>
                <th style="text-align:right;">Days in CWIP</th>
                <th>Available For Use</th><th>Purchased</th><th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in result.rows" :key="r.name" class="arx-row" @click="router.push(`/assets/${r.name}`)" :style="r.is_overdue ? 'background:var(--bx-redS);' : ''">
                <td class="arx-link">{{ r.asset_name || r.name }}<div class="arx-sub">{{ r.name }}</div></td>
                <td class="arx-sub">{{ categoryLabel(r.asset_category) || '—' }}</td>
                <td style="text-align:right;font-weight:700;color:var(--bx-astB);">{{ fmt(r.purchase_cost) }}</td>
                <td style="text-align:right;">{{ r.days_in_cwip ?? '—' }}</td>
                <td class="arx-sub">{{ r.available_for_use_date?.slice(0,10) || '—' }}</td>
                <td class="arx-sub">{{ r.purchase_date?.slice(0,10) }}</td>
                <td>
                  <span v-if="r.is_overdue" class="arx-badge badge-removed">Overdue</span>
                  <span v-else class="arx-badge badge-changed">In CWIP</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="result.rows.length" class="arx-cards-wrap">
            <div v-for="r in result.rows" :key="r.name" class="arx-rcard" @click="router.push(`/assets/${r.name}`)" :style="r.is_overdue ? 'background:var(--bx-redS);' : ''">
              <div class="arx-rcard-top">
                <span class="arx-link">{{ r.asset_name || r.name }}</span>
                <span v-if="r.is_overdue" class="arx-badge badge-removed">Overdue</span>
                <span v-else class="arx-badge badge-changed">In CWIP</span>
              </div>
              <div class="arx-sub">{{ r.name }} · {{ categoryLabel(r.asset_category) || '—' }}</div>
              <div class="arx-rcard-meta">
                <div><span class="arx-rcard-mlbl">Balance</span>{{ fmt(r.purchase_cost) }}</div>
                <div><span class="arx-rcard-mlbl">Days in CWIP</span>{{ r.days_in_cwip ?? '—' }}</div>
                <div><span class="arx-rcard-mlbl">For Use</span>{{ r.available_for_use_date?.slice(0,10) || '—' }}</div>
                <div><span class="arx-rcard-mlbl">Purchased</span>{{ r.purchase_date?.slice(0,10) }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- ── Depreciation Forecast ── -->
        <div v-if="activeTab === 'forecast'" class="arx-table-wrap">
          <div v-if="!result.rows.length" class="arx-empty">No depreciation schedule rows found for the selected filters.</div>
          <table v-else class="arx-table">
            <thead>
              <tr>
                <th>Asset</th><th>Category</th>
                <th style="text-align:right;">Period</th>
                <th>Dep. Date</th>
                <th style="text-align:right;">Opening</th>
                <th style="text-align:right;">Depreciation</th>
                <th style="text-align:right;">Closing</th>
                <th>Status</th><th>GL?</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(r,i) in result.rows" :key="r.asset + '-' + r.period_no + '-' + i" class="arx-row" @click="router.push(`/assets/${r.asset}`)">
                <td class="arx-link">{{ r.asset_name }}<div class="arx-sub">{{ r.asset }}</div></td>
                <td class="arx-sub">{{ categoryLabel(r.asset_category) || '—' }}</td>
                <td style="text-align:right;">{{ r.period_no }}<span v-if="r.is_pro_rata" class="arx-sub"> (pro-rata)</span></td>
                <td class="arx-sub">{{ r.depreciation_date?.slice(0,10) }}</td>
                <td style="text-align:right;">{{ fmt(r.opening_value) }}</td>
                <td style="text-align:right;font-weight:700;color:var(--bx-astB);">{{ fmt(r.depreciation_amount) }}</td>
                <td style="text-align:right;">{{ fmt(r.closing_value) }}</td>
                <td><span class="arx-badge" :class="statusClass(r.status)">{{ r.status }}</span></td>
                <td class="arx-sub">{{ r.gl_posting_applicable ? '✓' : '—' }}</td>
              </tr>
            </tbody>
            <tfoot>
              <tr class="arx-tfoot">
                <td colspan="5">Total Forecast</td>
                <td style="text-align:right;color:var(--bx-astB);">{{ fmt(result.summary.total_forecast_amount) }}</td>
                <td colspan="3"></td>
              </tr>
            </tfoot>
          </table>
          <div v-if="result.rows.length" class="arx-cards-wrap">
            <div v-for="(r,i) in result.rows" :key="r.asset + '-' + r.period_no + '-' + i" class="arx-rcard" @click="router.push(`/assets/${r.asset}`)">
              <div class="arx-rcard-top">
                <span class="arx-link">{{ r.asset_name }}</span>
                <span class="arx-badge" :class="statusClass(r.status)">{{ r.status }}</span>
              </div>
              <div class="arx-sub">{{ r.asset }} · {{ categoryLabel(r.asset_category) || '—' }} · {{ r.depreciation_date?.slice(0,10) }}</div>
              <div class="arx-rcard-meta">
                <div><span class="arx-rcard-mlbl">Period</span>{{ r.period_no }}{{ r.is_pro_rata ? ' (pro-rata)' : '' }}</div>
                <div><span class="arx-rcard-mlbl">Opening</span>{{ fmt(r.opening_value) }}</div>
                <div><span class="arx-rcard-mlbl">Dep.</span><span style="font-weight:700;color:var(--bx-astB);">{{ fmt(r.depreciation_amount) }}</span></div>
                <div><span class="arx-rcard-mlbl">Closing</span>{{ fmt(r.closing_value) }}</div>
                <div><span class="arx-rcard-mlbl">GL?</span>{{ r.gl_posting_applicable ? '✓' : '—' }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- ── Disposal Report ── -->
        <div v-if="activeTab === 'disposal'" class="arx-table-wrap">
          <div v-if="!result.rows.length" class="arx-empty">No disposals found for the selected filters.</div>
          <table v-else class="arx-table">
            <thead>
              <tr>
                <th>Disposal</th><th>Asset</th><th>Type</th><th>Date</th>
                <th style="text-align:right;">NBV at Disposal</th>
                <th style="text-align:right;">Sale Amount</th>
                <th style="text-align:right;">Gain / (Loss)</th>
                <th>GL Posted</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in result.rows" :key="r.name" class="arx-row" @click="router.push(`/assets/disposals?open=${r.name}`)">
                <td class="arx-link" style="font-size:12px;">{{ r.name }}</td>
                <td>{{ r.asset_name }}<div class="arx-sub">{{ r.asset }}</div></td>
                <td><span class="arx-badge" :class="r.disposal_type==='Sale' ? 'badge-changed' : 'badge-removed'">{{ r.disposal_type }}</span></td>
                <td class="arx-sub">{{ r.disposal_date?.slice(0,10) }}</td>
                <td style="text-align:right;">{{ fmt(r.net_book_value_snapshot) }}</td>
                <td style="text-align:right;">{{ fmt(r.sale_amount) }}</td>
                <td style="text-align:right;font-weight:700;" :style="r.gain_loss_amount >= 0 ? 'color:var(--bx-green);' : 'color:var(--bx-red);'">{{ fmt(r.gain_loss_amount) }}</td>
                <td>{{ r.gl_posted ? '✓' : '—' }}</td>
              </tr>
            </tbody>
            <tfoot>
              <tr class="arx-tfoot">
                <td colspan="4">Totals</td>
                <td style="text-align:right;">{{ fmt(result.summary.total_sale_proceeds - (result.summary.total_sale_proceeds - result.rows.reduce((a,r)=>a+parseFloat(r.net_book_value_snapshot||0),0))) }}</td>
                <td style="text-align:right;">{{ fmt(result.summary.total_sale_proceeds) }}</td>
                <td style="text-align:right;" :style="result.summary.net_gain_loss >= 0 ? 'color:var(--bx-green);' : 'color:var(--bx-red);'">{{ fmt(result.summary.net_gain_loss) }}</td>
                <td></td>
              </tr>
            </tfoot>
          </table>
          <div v-if="result.rows.length" class="arx-cards-wrap">
            <div v-for="r in result.rows" :key="r.name" class="arx-rcard" @click="router.push(`/assets/disposals?open=${r.name}`)">
              <div class="arx-rcard-top">
                <span class="arx-link" style="font-size:12px;">{{ r.name }}</span>
                <span class="arx-badge" :class="r.disposal_type==='Sale' ? 'badge-changed' : 'badge-removed'">{{ r.disposal_type }}</span>
              </div>
              <div class="arx-rcard-title">{{ r.asset_name }}</div>
              <div class="arx-sub">{{ r.asset }} · {{ r.disposal_date?.slice(0,10) }}</div>
              <div class="arx-rcard-meta">
                <div><span class="arx-rcard-mlbl">NBV</span>{{ fmt(r.net_book_value_snapshot) }}</div>
                <div><span class="arx-rcard-mlbl">Sale Amt</span>{{ fmt(r.sale_amount) }}</div>
                <div><span class="arx-rcard-mlbl">Gain/(Loss)</span><span :style="r.gain_loss_amount >= 0 ? 'color:var(--bx-green);font-weight:700;' : 'color:var(--bx-red);font-weight:700;'">{{ fmt(r.gain_loss_amount) }}</span></div>
                <div><span class="arx-rcard-mlbl">GL Posted</span>{{ r.gl_posted ? '✓' : '—' }}</div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- Empty state before first run -->
      <div v-else class="arx-empty-state">
        <div class="arx-empty-icon">📊</div>
        <div class="arx-empty-title">No report generated yet</div>
        <div class="arx-empty-sub">Set your filters above and click "Run Report" to view results.</div>
      </div>

    </div>
  </div>
</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { apiCall, apiList, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import SearchableSelect from "../components/SearchableSelect.vue";

const router = useRouter();
const { toast } = useToast();

const activeTab = ref("register");
const tabs = [
  { id: "register", label: "Asset Register",       icon: "📒", desc: "Every asset with its current book position: cost, accumulated depreciation, and net book value." },
  { id: "cwip",     label: "CWIP Register",         icon: "🏗️", desc: "Assets capitalized but not yet transferred out of Capital Work-in-Progress." },
  { id: "forecast", label: "Depreciation Forecast", icon: "📉", desc: "Upcoming (or posted) depreciation schedule rows across assets, for expense planning." },
  { id: "disposal", label: "Disposal Report",       icon: "🗑️", desc: "Submitted disposals — Scrap and Sale alike — with their gain/loss position." },
];

const today = new Date().toISOString().slice(0, 10);
const twelveMonthsOut = (() => {
  const d = new Date();
  d.setMonth(d.getMonth() + 12);
  return d.toISOString().slice(0, 10);
})();

const filters = ref({
  company: "",
  asset_category: "",
  status: "All",
  as_on_date: "",
  include_draft: false,
  from_date: "",
  to_date: "",
  disposal_type: "All",
});

const loading = ref(false);
const result = ref(null);

const API_MAP = {
  register: "zoho_books_clone.assets.reports.get_asset_register_report",
  cwip:     "zoho_books_clone.assets.reports.get_cwip_register_report",
  forecast: "zoho_books_clone.assets.reports.get_depreciation_forecast_report",
  disposal: "zoho_books_clone.assets.reports.get_disposal_report",
};

async function runReport() {
  loading.value = true;
  result.value = null;
  try {
    const payload = { ...filters.value };
    // forecast's own default 12-month window only kicks in server-side when
    // from_date/to_date are both empty -- mirror that here so switching into
    // the forecast tab with dates left over from a different tab doesn't
    // silently narrow its window.
    if (activeTab.value === "forecast" && !payload.from_date && !payload.to_date &&
        (payload.status === "Pending" || payload.status === "All")) {
      // leave blank; backend fills in today..+12mo
    }
    const data = await apiCall(API_MAP[activeTab.value], { filters: payload });
    result.value = data;
  } catch (e) {
    toast("Report failed: " + e.message, "error");
  }
  loading.value = false;
}

const summary = computed(() => result.value?.summary || null);

const summaryKpis = computed(() => {
  if (!summary.value) return [];
  const s = summary.value;
  if (activeTab.value === "register") return [
    { label: "Total Assets", value: s.total_assets },
    { label: "Active", value: s.active_count, color: "var(--bx-green)" },
    { label: "Disposed", value: s.disposed_count, color: "var(--bx-red)" },
    { label: "Total Cost", value: fmt(s.total_purchase_cost) },
    { label: "Net Book Value", value: fmt(s.total_net_book_value), color: "var(--bx-astB)" },
  ];
  if (activeTab.value === "cwip") return [
    { label: "In CWIP", value: s.total_in_cwip },
    { label: "CWIP Balance", value: fmt(s.total_cwip_balance), color: "var(--bx-astB)" },
    { label: "Overdue", value: s.overdue_count, color: s.overdue_count > 0 ? "var(--bx-red)" : "var(--bx-green)" },
  ];
  if (activeTab.value === "forecast") return [
    { label: "Schedule Rows", value: s.total_rows },
    { label: "Assets Covered", value: s.assets_covered },
    { label: "Total Forecast", value: fmt(s.total_forecast_amount), color: "var(--bx-astB)" },
  ];
  if (activeTab.value === "disposal") return [
    { label: "Disposals", value: s.total_disposals },
    { label: "Scrapped", value: s.scrapped_count },
    { label: "Sold", value: s.sold_count },
    { label: "Total Proceeds", value: fmt(s.total_sale_proceeds) },
    { label: "Net Gain/(Loss)", value: fmt(s.net_gain_loss), color: s.net_gain_loss >= 0 ? "var(--bx-green)" : "var(--bx-red)" },
  ];
  return [];
});

function fmt(val) {
  const n = parseFloat(val) || 0;
  return n.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function statusClass(status) {
  const map = {
    "Completed":  "badge-active",
    "Active":     "badge-active",
    "Submitted":  "badge-draft",
    "Pending":    "badge-changed",
    "Scrapped":   "badge-removed",
    "Sold":       "badge-changed",
    "Draft":      "badge-obsolete",
    "Cancelled":  "badge-obsolete",
  };
  return map[status] || "badge-obsolete";
}

function exportCSV() {
  if (!result.value?.rows?.length) return;
  const rows = result.value.rows;
  const keys = Object.keys(rows[0]);
  const lines = [
    keys.join(","),
    ...rows.map(r => keys.map(k => JSON.stringify(r[k] ?? "")).join(","))
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `asset-${activeTab.value}-report-${today}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Company / Asset Category filter options ──
const companyOptions = ref([]);
const categoryOptions = ref([]);
const categoryLabelMap = computed(() => {
  const map = {};
  for (const c of categoryOptions.value) map[c.value] = c.label;
  return map;
});
function categoryLabel(id) {
  return id ? (categoryLabelMap.value[id] || id) : "";
}

async function loadFilterOptions() {
  try {
    const companies = await apiList("Company", { fields: ["name"], limit: 200, order: "name asc" });
    companyOptions.value = (companies || []).map(c => ({ label: c.name, value: c.name }));
  } catch (e) { /* non-fatal */ }
  try {
    const cats = await apiList("Asset Category", { fields: ["name", "category_name"], limit: 500, order: "category_name asc" });
    categoryOptions.value = (cats || []).map(c => ({ label: c.category_name || c.name, value: c.name }));
  } catch (e) { /* non-fatal */ }
}

onMounted(async () => {
  try {
    const co = await resolveCompany();
    if (co) filters.value.company = co;
  } catch (e) { /* non-fatal */ }
  await loadFilterOptions();
  runReport();
});
</script>

<style scoped>
.arx-page {
  --bx-bg:#F3F4F6; --bx-surface:#FFFFFF; --bx-surf2:#F8F9FC; --bx-border:#E2E8F0;
  --bx-text:#1A1D23; --bx-muted:#868E96;
  --bx-green:#2F9E44; --bx-greenS:#EBFBEE;
  --bx-red:#C92A2A; --bx-redS:#FFF5F5;
  --bx-amber:#E67700; --bx-amberS:#FFF3BF;
  --bx-blue:#1971C2; --bx-blueS:#E7F5FF;
  --bx-ast:#7048e8; --bx-astL:#845ef7; --bx-astS:#F3F0FF; --bx-astB:#4c2a99;
  --bx-radius:10px; --bx-rsm:6px;
  padding: 16px;
}
.arx-panel { background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; display:flex; flex-direction:column; min-height: calc(100vh - 32px); }

.arx-hdr { padding:18px 22px; background:linear-gradient(135deg, var(--bx-astB), var(--bx-ast)); display:flex; align-items:flex-start; justify-content:space-between; gap:12px; flex-wrap:wrap; }
.arx-hdr-title { font-size:18px; font-weight:700; color:#fff; margin-bottom:4px; }
.arx-hdr-sub { font-size:12.5px; color:rgba(255,255,255,.75); }
.arx-hdr-actions { display:flex; gap:8px; flex-wrap:wrap; }

.arx-tabs { display:flex; border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); padding:0 22px; overflow-x:auto;overflow-y:hidden; }
.arx-tab { display:flex; align-items:center; gap:6px; padding:10px 16px; font-size:13px; font-weight:600; cursor:pointer; border:none; background:none; color:var(--bx-muted); border-bottom:2px solid transparent; margin-bottom:-1px; white-space:nowrap; }
.arx-tab-ic { font-size:13px; }
.arx-tab.active { color:var(--bx-ast); border-bottom-color:var(--bx-ast); }

.arx-filters { display:flex; gap:12px; flex-wrap:wrap; align-items:flex-end; padding:16px 22px; border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); }
.arx-hf-label { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); margin-bottom:4px; }

.arx-body { padding:20px 22px; overflow-y:auto; flex:1; }

/* ── KPI strip ── */
.arx-kpi-grid { display:grid; gap:10px; margin-bottom:18px; }
.arx-kpi-cell { background:var(--bx-astS); border:1px solid rgba(112,72,232,.15); border-radius:var(--bx-rsm); padding:12px 14px; }
.arx-kpi-lbl { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-ast); margin-bottom:4px; }
.arx-kpi-val { font-size:19px; font-weight:700; color:var(--bx-text); }
@media (max-width:900px) { .arx-kpi-grid { grid-template-columns:1fr 1fr !important; } }

/* ── Table ── */
.arx-table-wrap { overflow-x:auto; border:1px solid var(--bx-border); border-radius:var(--bx-rsm); }
.arx-empty { text-align:center; padding:32px; color:var(--bx-muted); font-size:13px; }
.arx-table { width:100%; border-collapse:collapse; font-size:13px; }
.arx-table th { text-align:left; padding:8px 12px; border-bottom:1px solid var(--bx-border); color:var(--bx-muted); font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; background:var(--bx-surf2); white-space:nowrap; }
.arx-table td { padding:9px 12px; border-bottom:1px solid #F1F3F5; vertical-align:middle; }
.arx-row { cursor:pointer; transition:background .1s; }
.arx-row:hover { background:#FAFBFF; }
.arx-link { color:var(--bx-ast); font-weight:600; }
.arx-sub { font-size:11px; color:var(--bx-muted); }
.arx-tfoot td { background:var(--bx-astS); font-weight:700; color:var(--bx-astB); }

/* ── Badges ── */
.arx-badge { display:inline-flex; align-items:center; padding:2px 8px; border-radius:20px; font-size:11px; font-weight:600; white-space:nowrap; }
.badge-active { background:var(--bx-greenS); color:var(--bx-green); }
.badge-draft { background:var(--bx-amberS); color:var(--bx-amber); }
.badge-obsolete { background:#F1F3F5; color:var(--bx-muted); }
.badge-changed { background:var(--bx-blueS); color:var(--bx-blue); }
.badge-removed { background:var(--bx-redS); color:var(--bx-red); }

/* ── Empty state ── */
.arx-empty-state { text-align:center; padding:60px 20px; color:var(--bx-muted); }
.arx-empty-icon { font-size:48px; margin-bottom:14px; }
.arx-empty-title { font-size:16px; font-weight:700; color:var(--bx-text); margin-bottom:6px; }
.arx-empty-sub { font-size:13px; line-height:1.6; max-width:320px; margin:0 auto; }

/* ── Buttons / inputs ── */
.arx-fi { border:1px solid #CDD5E0; border-radius:var(--bx-rsm); padding:7px 9px; font-size:13px; color:var(--bx-text); background:#fff; outline:none; min-width:140px; }
.arx-fi:focus { border-color:var(--bx-ast); box-shadow:0 0 0 3px rgba(112,72,232,.1); }
select.arx-fi {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  padding-right: 30px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%239ca3af' stroke-width='2.5'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
}
.arx-btn { display:inline-flex; align-items:center; gap:6px; padding:8px 16px; border-radius:var(--bx-rsm); font-size:13px; font-weight:600; cursor:pointer; border:1px solid transparent; line-height:1; white-space:nowrap; }
.arx-btn:disabled { opacity:.6; cursor:not-allowed; }
.arx-btn-ast { background:var(--bx-ast); color:#fff; }
.arx-btn-ast:hover:not(:disabled) { background:var(--bx-astB); }
.arx-btn-light { background:#fff; color:var(--bx-astB); border:1px solid var(--bx-border); }
.arx-btn-light:hover:not(:disabled) { background:var(--bx-surf2); }

.arx-spinner { display:inline-block;width:11px;height:11px;border:2px solid rgba(255,255,255,.4);border-top-color:#fff;border-radius:50%;animation:spin .6s linear infinite; }
@keyframes spin { to { transform: rotate(360deg) } }

.shimmer { background:linear-gradient(90deg,#f1f3f5 25%,#e9ecef 37%,#f1f3f5 63%); background-size:400% 100%; animation:shimmer 1.4s ease infinite; }
@keyframes shimmer { 0%{background-position:100% 50%} 100%{background-position:0 50%} }

/* ── Mobile report cards ── */
.arx-cards-wrap { display:none; flex-direction:column; gap:10px; }
.arx-rcard { background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-rsm); padding:12px 14px; cursor:pointer; transition:background .1s; }
.arx-rcard:hover { background:#FAFBFF; }
.arx-rcard-top { display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:6px; }
.arx-rcard-title { font-size:13.5px; font-weight:600; color:var(--bx-text); margin-bottom:2px; }
.arx-rcard-meta { display:grid; grid-template-columns:1fr 1fr; gap:8px 14px; font-size:12.5px; color:var(--bx-text); padding-top:8px; margin-top:8px; border-top:1px solid #F1F3F5; }
.arx-rcard-mlbl { display:block; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); margin-bottom:1px; }

@media (max-width:680px) {
  .arx-table-wrap > .arx-table { display:none; }
  .arx-cards-wrap { display:flex; }
}

@media (max-width:600px) {
  .arx-page { padding:8px; }
  .arx-panel { min-height:calc(100vh - 16px); }
  .arx-hdr { padding:14px 16px; }
  .arx-hdr-title { font-size:16px; }
  .arx-btn { padding:8px 12px; font-size:12.5px; }
  .arx-tabs { padding:0 12px; }
  .arx-filters { padding:12px 14px; gap:10px; }
  .arx-fi { min-width:0; flex:1; }
  .arx-filters > div { flex:1; min-width:130px; }
  .arx-body { padding:14px; }
  .arx-kpi-grid { grid-template-columns:1fr 1fr !important; }
  .arx-rcard-meta { grid-template-columns:1fr 1fr; }
}
</style>