<template>
  <div class="list-page">

    <!-- ── Header ── -->
    <div class="ds-header">
      <div class="ds-header-left">
        <h1 class="ds-title">Depreciation Schedules</h1>
        <p class="ds-subtitle">Projected depreciation for every depreciable asset, by method and useful life</p>
      </div>
      <div class="ds-header-right">
        <button class="sales-btn-ghost" title="Refresh" @click="load" :disabled="loading">
          <span v-html="icon('refresh',14)"></span>
        </button>
        <button class="sales-btn-ghost" @click="exportAllCSV" :disabled="!depreciableAssets.length">
          <span v-html="icon('download',14)"></span> <span class="btn-label">CSV</span>
        </button>
      </div>
    </div>

    <!-- ── Global KPI cards ── -->
    <div class="bk-kpi-grid bk-kpi-grid-4">
      <div class="bk-kpi-card bk-kpi-accent">
        <div class="bk-kpi-inner">
          <div class="bk-kpi-icon" style="background:#dbeafe"><span v-html="icon('box',22)"></span></div>
          <div class="bk-kpi-body">
            <div class="bk-kpi-label">Depreciable Assets</div>
            <div class="bk-kpi-value">{{ depreciableAssets.length }}</div>
            <div class="bk-kpi-trend bk-trend-neutral">of {{ list.length }} total</div>
          </div>
        </div>
      </div>
      <div class="bk-kpi-card">
        <div class="bk-kpi-inner">
          <div class="bk-kpi-icon" style="background:#dcfce7"><span v-html="icon('rupee',22)"></span></div>
          <div class="bk-kpi-body">
            <div class="bk-kpi-label">Depreciable Value</div>
            <div class="bk-kpi-value bk-kpi-green" style="font-size:20px">{{ fmt(globalSum.cost) }}</div>
            <div class="bk-kpi-trend bk-trend-neutral">cost − salvage</div>
          </div>
        </div>
      </div>
      <div class="bk-kpi-card bk-kpi-warn">
        <div class="bk-kpi-inner">
          <div class="bk-kpi-icon" style="background:#fef3c7"><span v-html="icon('trend',22)"></span></div>
          <div class="bk-kpi-body">
            <div class="bk-kpi-label">Accumulated to Date</div>
            <div class="bk-kpi-value bk-kpi-amber" style="font-size:20px">{{ fmt(globalSum.toDate) }}</div>
            <div class="bk-kpi-trend bk-trend-neutral">booked so far</div>
          </div>
        </div>
      </div>
      <div class="bk-kpi-card">
        <div class="bk-kpi-inner">
          <div class="bk-kpi-icon" style="background:#dbeafe"><span v-html="icon('percent',22)"></span></div>
          <div class="bk-kpi-body">
            <div class="bk-kpi-label">Current Book Value</div>
            <div class="bk-kpi-value bk-kpi-blue" style="font-size:20px">{{ fmt(globalSum.bookValue) }}</div>
            <div class="bk-kpi-trend bk-trend-neutral">net of depreciation</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Toolbar ── -->
    <div class="sales-toolbar">
      <div class="sales-search">
        <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
        <input v-model="searchTerm" placeholder="Search assets..." class="sales-search-input" autocomplete="off"/>
      </div>
      <div class="sales-pills">
        <button class="sales-pill" :class="{active: methodFilter==='all'}" @click="methodFilter='all'">
          All <span class="sales-pill-count">{{ depreciableAssets.length }}</span>
        </button>
        <button v-for="m in methods" :key="m" class="sales-pill" :class="{active: methodFilter===m}" @click="methodFilter=m">
          {{ m }} <span class="sales-pill-count">{{ methodCounts[m] || 0 }}</span>
        </button>
      </div>
      <div class="sales-actions">
        <select class="sales-select" v-model="filterCategory" title="Filter by category">
          <option value="">All Categories</option>
          <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
        </select>
      </div>
    </div>

    <!-- ── Asset ledger list ── -->
    <div class="inv-table-wrap">
      <table class="inv-table ds-desktop-tbl">
        <thead>
          <tr>
            <th class="sortable" @click="sortBy('asset_name')"><span class="dp-th-content">Asset</span><span class="sort-arrow" v-html="sortArrow('asset_name')"></span></th>
            <th class="sortable" @click="sortBy('asset_category')">Category <span class="sort-arrow" v-html="sortArrow('asset_category')"></span></th>
            <th class="sortable" @click="sortBy('depreciation_method')">Method <span class="sort-arrow" v-html="sortArrow('depreciation_method')"></span></th>
            <th class="ta-r sortable" @click="sortBy('purchase_cost')">Cost <span class="sort-arrow" v-html="sortArrow('purchase_cost')"></span></th>
            <th class="ta-r sortable" @click="sortBy('useful_life')">Life (Yrs) <span class="sort-arrow" v-html="sortArrow('useful_life')"></span></th>
            <th class="ta-r sortable" @click="sortBy('annual')">Annual Dep. <span class="sort-arrow" v-html="sortArrow('annual')"></span></th>
            <th class="ta-r sortable" @click="sortBy('bookValue')">Book Value <span class="sort-arrow" v-html="sortArrow('bookValue')"></span></th>
            <th style="width:120px;text-align:center">Schedule</th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 5" :key="n" class="shimmer-row"><td colspan="8"><div class="shimmer" style="width:70%"></div></td></tr>
          </template>
          <tr v-else-if="!filteredAssets.length">
            <td colspan="8" class="bk-empty-state">
              <div class="bk-empty-inner">
                <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.3"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                <p class="bk-empty-title">{{ searchTerm || methodFilter !== 'all' || filterCategory ? 'No matching assets' : 'No depreciable assets yet' }}</p>
                <p v-if="searchTerm || methodFilter !== 'all' || filterCategory" class="bk-empty-sub">Try adjusting your search or filter</p>
                <p v-else class="bk-empty-sub">Add an asset with a purchase cost and useful life to build a schedule.</p>
              </div>
            </td>
          </tr>
          <tr v-for="a in pagedAssets" :key="a.name" class="inv-row" :class="{selected: selectedName === a.name}">
            <td @click="openSchedule(a)" data-label="Asset"><span class="inv-link">{{ a.asset_name || a.name }}</span><div class="asset-code">{{ a.name }}</div></td>
            <td @click="openSchedule(a)" data-label="Category"><span v-if="a.asset_category" class="it-group-badge">{{ a.asset_category }}</span><span v-else class="text-muted">—</span></td>
            <td @click="openSchedule(a)" data-label="Method"><span class="ds-method-badge" :class="methodClass(a.depreciation_method)">{{ a.depreciation_method || '—' }}</span></td>
            <td @click="openSchedule(a)" class="ta-r mono-sm fw-600" data-label="Cost">{{ fmt(a.purchase_cost || 0) }}</td>
            <td @click="openSchedule(a)" class="ta-r mono-sm text-muted" data-label="Life">{{ a.useful_life || '—' }}</td>
            <td @click="openSchedule(a)" class="ta-r mono-sm" data-label="Annual Dep.">{{ fmt(a._summary.annual) }}</td>
            <td @click="openSchedule(a)" class="ta-r mono-sm fw-600" data-label="Book Value" style="color:#2563eb">{{ fmt(a._summary.bookValue) }}</td>
            <td style="text-align:center" @click.stop>
              <button class="inv-act-btn" :class="{'inv-act-active': selectedName === a.name}" @click="openSchedule(a)" :title="selectedName === a.name ? 'Hide schedule' : 'View schedule'">
                <span v-html="icon('chart',13)"></span> View
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Mobile cards -->
      <div class="ds-mobile-cards">
        <template v-if="loading">
          <div v-for="n in 4" :key="n" class="b-shimmer" style="height:88px;border-radius:10px"></div>
        </template>
        <div v-else-if="!filteredAssets.length" class="ds-mobile-empty">
          <div>{{ searchTerm || methodFilter !== 'all' || filterCategory ? 'No matching assets' : 'No depreciable assets yet' }}</div>
        </div>
        <div v-else v-for="a in pagedAssets" :key="a.name" class="ii-mob-card" @click="openSchedule(a)">
          <div class="ii-mob-card-main">
            <div class="ii-mob-card-top">
              <span class="fw-700" style="font-size:14px;color:#111827;line-height:1.3">{{ a.asset_name || a.name }}</span>
              <span class="ds-method-badge" :class="methodClass(a.depreciation_method)">{{ a.depreciation_method || '—' }}</span>
            </div>
            <div class="ii-mob-card-meta">
              <span class="inv-link" style="font-size:11.5px">{{ a.name }}</span>
              <span v-if="a.asset_category" class="it-group-badge" style="font-size:10.5px">{{ a.asset_category }}</span>
            </div>
          </div>
          <div class="ii-mob-card-right">
            <div class="fw-700" style="font-size:14px;color:#2563eb">{{ fmt(a._summary.bookValue) }}</div>
            <div class="text-muted" style="font-size:11px">cost {{ fmt(a.purchase_cost || 0) }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Pagination ── -->
    <div v-if="!loading && filteredAssets.length" class="list-pagination" style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap">
      <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="filteredAssets.length" />
      <div class="dp-footer-info">
        Showing <strong>{{ pageStart }}</strong> to <strong>{{ pageEnd }}</strong> of <strong>{{ filteredAssets.length }}</strong> assets
      </div>
    </div>

    <!-- ── Projection panel ── -->
    <div v-if="selectedAsset" ref="panelRef" class="ds-panel">
      <div class="ds-panel-head">
        <div>
          <div class="ds-panel-title">{{ selectedAsset.asset_name || selectedAsset.name }}</div>
          <div class="ds-panel-sub">{{ selectedAsset.name }} · {{ selectedAsset.asset_category || 'Uncategorized' }} · {{ selectedAsset.depreciation_method || 'Straight Line' }}</div>
        </div>
        <div class="ds-panel-actions">
          <button class="sales-btn-ghost" @click="exportScheduleCSV(selectedAsset)"><span v-html="icon('download',13)"></span> Schedule CSV</button>
          <button class="sales-btn-ghost" @click="goToAsset(selectedAsset)"><span v-html="icon('edit',13)"></span> Edit Asset</button>
          <button class="sales-btn-ghost" @click="selectedName = null"><span v-html="icon('x',14)"></span></button>
        </div>
      </div>

      <div class="ds-summary-grid">
        <div class="ds-summary-card">
          <div class="ds-sc-label">Original Cost</div>
          <div class="ds-sc-value">{{ fmt(sel._summary.cost) }}</div>
        </div>
        <div class="ds-summary-card">
          <div class="ds-sc-label">Salvage Value</div>
          <div class="ds-sc-value">{{ fmt(sel._summary.salvage) }}</div>
        </div>
        <div class="ds-summary-card">
          <div class="ds-sc-label">Annual Depreciation</div>
          <div class="ds-sc-value" style="color:#92400e">{{ fmt(sel._summary.annual) }}</div>
        </div>
        <div class="ds-summary-card">
          <div class="ds-sc-label">Accumulated (to date)</div>
          <div class="ds-sc-value" style="color:#92400e">{{ fmt(sel._summary.toDate) }}</div>
        </div>
        <div class="ds-summary-card ds-sc-accent">
          <div class="ds-sc-label">Current Book Value</div>
          <div class="ds-sc-value" style="color:#2563eb">{{ fmt(sel._summary.bookValue) }}</div>
        </div>
        <div class="ds-summary-card">
          <div class="ds-sc-label">Total Depreciation</div>
          <div class="ds-sc-value" style="color:#16a34a">{{ fmt(sel._summary.totalDep) }}</div>
        </div>
      </div>

      <div class="ds-panel-section">
        <div class="ds-section-title">Depreciation Trend</div>
        <DepreciationChart :rows="sel.rows" />
      </div>

      <div class="ds-panel-section">
        <div class="ds-section-title">Schedule ({{ sel.rows.length }} {{ sel.rows.length === 1 ? 'year' : 'years' }})</div>
        <div class="inv-table-wrap">
          <table class="inv-table ds-schedule-tbl">
            <thead>
              <tr>
                <th>Year</th>
                <th>Date</th>
                <th class="ta-r">Opening Value</th>
                <th class="ta-r">Depreciation</th>
                <th class="ta-r">Accumulated</th>
                <th class="ta-r">Closing Value</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in sel.rows" :key="row.year" class="inv-row">
                <td class="fw-600">{{ row.year }}</td>
                <td class="mono-sm text-muted">{{ fmtDate(row.depreciation_date) }}</td>
                <td class="ta-r mono-sm">{{ fmt(row.opening_value) }}</td>
                <td class="ta-r mono-sm fw-600">{{ fmt(row.depreciation_amount) }}</td>
                <td class="ta-r mono-sm text-muted">{{ fmt(row.accumulated_value) }}</td>
                <td class="ta-r mono-sm fw-600" style="color:#2563eb">{{ fmt(row.closing_value) }}</td>
                <td><span class="inv-status-badge status-draft">{{ row.status }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from "vue";
import { useRouter } from "vue-router";
import { apiList } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";
import { fmt, fmtDate } from "../utils/format.js";
import { computeSchedule, scheduleSummary } from "../composables/useDepreciation.js";
import Pagination from "../components/Pagination.vue";
import DepreciationChart from "../components/DepreciationChart.vue";

const router = useRouter();
const toast = useToast();


const list = ref([]);
const loading = ref(false);
const searchTerm = ref("");
const methodFilter = ref("all");
const filterCategory = ref("");
const categories = ref([]);
const methods = ["Straight Line", "Written Down Value"];

const page = ref(1);
const pageSize = ref(20);
const selectedName = ref(null);
const panelRef = ref(null);

const depreciableAssets = computed(() =>
  list.value
    .filter(a => parseFloat(a.purchase_cost) > 0 && parseInt(a.useful_life) > 0)
    .map(a => {
      const rows = computeSchedule(a);
      const _summary = scheduleSummary(a, rows);
      return { ...a, _rows: rows, _summary };
    })
);

const methodCounts = computed(() => {
  const c = {};
  for (const m of methods) c[m] = 0;
  for (const a of depreciableAssets.value) {
    if (c[a.depreciation_method] !== undefined) c[a.depreciation_method]++;
  }
  return c;
});

const globalSum = computed(() => {
  const cost = depreciableAssets.value.reduce((s, a) => s + a._summary.cost - a._summary.salvage, 0);
  const toDate = depreciableAssets.value.reduce((s, a) => s + a._summary.toDate, 0);
  const bookValue = depreciableAssets.value.reduce((s, a) => s + a._summary.bookValue, 0);
  return { cost: depreciableAssets.value.reduce((s, a) => s + a._summary.cost, 0), toDate, bookValue };
});

const sortKey = ref("asset_name");
const sortDir = ref(1);

function sortBy(key) {
  if (sortKey.value === key) sortDir.value *= -1;
  else { sortKey.value = key; sortDir.value = 1; }
}
function sortArrow(key) {
  if (sortKey.value !== key) return "";
  return sortDir.value === 1 ? "&#9650;" : "&#9660;";
}

const filteredAssets = computed(() => {
  let items = depreciableAssets.value;
  if (methodFilter.value !== "all") {
    items = items.filter(a => a.depreciation_method === methodFilter.value);
  }
  if (filterCategory.value) {
    items = items.filter(a => a.asset_category === filterCategory.value);
  }
  if (searchTerm.value) {
    const t = searchTerm.value.toLowerCase();
    items = items.filter(a =>
      (a.asset_name || "").toLowerCase().includes(t) ||
      (a.name || "").toLowerCase().includes(t) ||
      (a.asset_category || "").toLowerCase().includes(t)
    );
  }
  const key = sortKey.value;
  const dir = sortDir.value;
  return [...items].sort((a, b) => {
    let av = a[key];
    let bv = b[key];
    if (key === "annual") { av = a._summary.annual; bv = b._summary.annual; }
    if (key === "bookValue") { av = a._summary.bookValue; bv = b._summary.bookValue; }
    av = av ?? ""; bv = bv ?? "";
    if (typeof av === "number" || typeof bv === "number") return ((parseFloat(av) || 0) - (parseFloat(bv) || 0)) * dir;
    return String(av).localeCompare(String(bv), undefined, { numeric: true }) * dir;
  });
});

const pagedAssets = computed(() => {
  const start = (page.value - 1) * pageSize.value;
  return filteredAssets.value.slice(start, start + pageSize.value);
});
const pageStart = computed(() => filteredAssets.value.length === 0 ? 0 : (page.value - 1) * pageSize.value + 1);
const pageEnd = computed(() => Math.min(filteredAssets.value.length, page.value * pageSize.value));

const selectedAsset = computed(() => depreciableAssets.value.find(a => a.name === selectedName.value) || null);
const sel = computed(() => selectedAsset.value ? { ...selectedAsset.value, rows: selectedAsset.value._rows, _summary: selectedAsset.value._summary } : null);

function methodClass(method) {
  if (method === "Written Down Value") return "ds-method-wdv";
  return "ds-method-sl";
}

function openSchedule(a) {
  if (selectedName.value === a.name) {
    selectedName.value = null;
    return;
  }
  selectedName.value = a.name;
  nextTick(() => panelRef.value?.scrollIntoView({ behavior: "smooth", block: "start" }));
}

function goToAsset(a) {
  router.push({ name: "asset-details", params: { id: a.name } });
}

function exportCSVFor(rows, assetName, filename) {
  const headers = ["Year", "Date", "Opening Value", "Depreciation", "Accumulated", "Closing Value", "Status"];
  const dataRows = rows.map(r => [r.year, r.depreciation_date || "", r.opening_value || 0, r.depreciation_amount || 0, r.accumulated_value || 0, r.closing_value || 0, r.status || "Pending"]);
  const csv = [headers, ...dataRows].map(row => row.map(v => `"${String(v ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function exportScheduleCSV(a) {
  exportCSVFor(a._rows, a.name, `depreciation-${a.name}.csv`);
}

function exportAllCSV() {
  const headers = ["Asset", "Category", "Method", "Cost", "Salvage", "Useful Life", "Annual Depreciation", "Accumulated to Date", "Book Value"];
  const rows = depreciableAssets.value.map(a => [
    a.asset_name || a.name, a.asset_category || "", a.depreciation_method || "",
    a._summary.cost, a._summary.salvage, a._summary.life, a._summary.annual, a._summary.toDate, a._summary.bookValue,
  ]);
  const csv = [headers, ...rows].map(row => row.map(v => `"${String(v ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "depreciation-schedules.csv";
  link.click();
  URL.revokeObjectURL(url);
}

async function load() {
  loading.value = true;
  try {
    const assets = await apiList("Asset", {
      fields: [
        "name", "asset_name", "asset_category", "status",
        "purchase_cost", "salvage_value", "useful_life",
        "depreciation_method", "purchase_date", "current_value",
      ],
      order: "asset_name asc",
      limit: 500,
    });
    list.value = assets || [];
    categories.value = Array.from(new Set((assets || []).map(a => a.asset_category).filter(Boolean))).sort();
  } catch (e) {
    toast.error("Failed to load assets: " + e.message);
    list.value = [];
    categories.value = [];
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.ds-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}
.ds-header-right { display: flex; gap: 8px; }
.ds-title { font-size: 22px; font-weight: 700; color: #111827; margin: 0; }
.ds-subtitle { font-size: 13px; color: #6b7280; margin: 4px 0 0; }

.ds-desktop-tbl { display: table; }
.ds-mobile-cards { display: none; }
.dp-footer-info { font-size: 12.5px; color: #6b7280; }
.btn-label { font-size: 13px; }

.ds-method-badge {
  display: inline-block;
  padding: 2px 9px;
  border-radius: 12px;
  font-size: 11.5px;
  font-weight: 600;
  white-space: nowrap;
}
.ds-method-sl { background: #eef2ff; color: #4338ca; }
.ds-method-wdv { background: #fef3c7; color: #92400e; }

.inv-act-active { background: #e0edff; color: #1d4ed8; }

.asset-code {
  margin-top: 3px;
  color: #9ca3af;
  font-size: 11px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.text-muted { color: #9ca3af; }
.mono-sm { font-size: 13px; }
.ta-r { text-align: right; }
.fw-600 { font-weight: 600; }
.fw-700 { font-weight: 700; }

/* Projection panel */
.ds-panel {
  margin-top: 22px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(16,24,40,0.04);
  overflow: hidden;
  scroll-margin-top: 20px;
}
.ds-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 18px;
  border-bottom: 1px solid #eef2f7;
  flex-wrap: wrap;
}
.ds-panel-title { font-size: 16px; font-weight: 700; color: #111827; }
.ds-panel-sub { font-size: 12.5px; color: #6b7280; margin-top: 2px; }
.ds-panel-actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }

.ds-summary-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 10px;
  padding: 16px 18px;
}
.ds-summary-card {
  background: #f8fafc;
  border: 1px solid #eef2f7;
  border-radius: 10px;
  padding: 12px;
  text-align: center;
}
.ds-summary-card.ds-sc-accent { background: #eff6ff; border-color: #dbeafe; }
.ds-sc-label { font-size: 11px; color: #6b7280; font-weight: 600; text-transform: uppercase; letter-spacing: 0.02em; }
.ds-sc-value { font-size: 17px; font-weight: 700; color: #111827; margin-top: 4px; }

.ds-panel-section { padding: 4px 18px 18px; }
.ds-section-title { font-size: 13.5px; font-weight: 700; color: #374151; margin: 10px 0 10px; }

@media (max-width: 1100px) {
  .ds-summary-grid { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 768px) {
  .ds-desktop-tbl { display: none; }
  .ds-mobile-cards {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px;
  }
  .ds-mobile-empty { text-align: center; padding: 30px 16px; color: #9ca3af; font-size: 13px; }
  .ds-summary-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>