<template>
<div class="list-page">

  <!-- ── Toolbar ── -->
  <div class="sales-toolbar">
    <div class="sales-search">
      <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
      <input v-model="searchTerm" placeholder="Search maintenance logs..." class="sales-search-input" autocomplete="off"/>
    </div>
    <div class="sales-pills">
      <button class="sales-pill" :class="{active: statusFilter==='all'}" @click="statusFilter='all'">
        All <span class="sales-pill-count">{{ list.length }}</span>
      </button>
      <button v-for="s in logStatuses" :key="s" class="sales-pill" :class="{active: statusFilter===s, ['pill-'+s]: true}" @click="statusFilter=s">
        {{ s }} <span class="sales-pill-count">{{ statusCounts[s] || 0 }}</span>
      </button>
    </div>
    <div class="sales-actions">
      <select class="sales-select" v-model="filterAsset" title="Filter by asset">
        <option value="">All Assets</option>
        <option v-for="a in allAssets" :key="a.name" :value="a.name">{{ a.asset_name || a.name }}</option>
      </select>
      <button class="sales-btn-ghost" title="Refresh" @click="load" :disabled="loading">
        <span v-html="icon('refresh',14)"></span>
      </button>
      <button class="sales-btn-ghost" @click="exportCSV" :disabled="!filteredLogs.length">
        <span v-html="icon('download',14)"></span> <span class="btn-label">CSV</span>
      </button>
      <button class="sales-btn-primary" @click="openNewLogForm">
        <span v-html="icon('plus',13)"></span> New Log
      </button>
    </div>
  </div>

  <!-- ── KPI Cards ── -->
  <div class="bk-kpi-grid bk-kpi-grid-4">
    <div class="bk-kpi-card bk-kpi-accent clickable" @click="statusFilter='all'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#dbeafe"><span v-html="icon('file',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Total Logs</div>
          <div class="bk-kpi-value">{{ list.length }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">maintenance records</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card bk-kpi-success clickable" @click="statusFilter='Completed'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#dcfce7"><span v-html="icon('check',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Completed</div>
          <div class="bk-kpi-value bk-kpi-green">{{ statusCounts.Completed || 0 }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">closed work orders</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card bk-kpi-warn clickable" @click="statusFilter='Pending'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#fef3c7"><span v-html="icon('calendar',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Pending</div>
          <div class="bk-kpi-value bk-kpi-amber">{{ statusCounts.Pending || 0 }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">awaiting service</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card clickable" @click="statusFilter='all'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#dcfce7"><span v-html="icon('rupee',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Total Cost</div>
          <div class="bk-kpi-value bk-kpi-green" style="font-size:20px">{{ fmt(totalCost) }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">across all logs</div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── Secondary Stat Cards ── -->
  <div class="bk-stat-grid">
    <div class="bk-stat-card">
      <div class="bk-stat-content">
        <div>
          <div class="bk-stat-label">Assets Serviced</div>
          <div class="bk-stat-value">{{ distinctAssets.length }}</div>
        </div>
        <div class="bk-stat-icon" style="background:#dbeafe;color:#2563eb"><span v-html="icon('box',18)"></span></div>
      </div>
    </div>
    <div class="bk-stat-card">
      <div class="bk-stat-content">
        <div>
          <div class="bk-stat-label">Avg. Cost</div>
          <div class="bk-stat-value bk-kpi-green" style="font-size:16px">{{ fmt(avgCost) }}</div>
        </div>
        <div class="bk-stat-icon" style="background:#dcfce7;color:#16a34a"><span v-html="icon('rupee',18)"></span></div>
      </div>
    </div>
    <div class="bk-stat-card">
      <div class="bk-stat-content">
        <div>
          <div class="bk-stat-label">Cancelled</div>
          <div class="bk-stat-value">{{ statusCounts.Cancelled || 0 }}</div>
        </div>
        <div class="bk-stat-icon" style="background:#fee2e2;color:#dc2626"><span v-html="icon('x',18)"></span></div>
      </div>
    </div>
    <div class="bk-stat-card">
      <div class="bk-stat-content">
        <div>
          <div class="bk-stat-label">Open Items</div>
          <div class="bk-stat-value bk-kpi-blue">{{ statusCounts.Pending || 0 }}</div>
        </div>
        <div class="bk-stat-icon" style="background:#fef3c7;color:#92400e"><span v-html="icon('alert',18)"></span></div>
      </div>
    </div>
  </div>

  <!-- ── Bulk action bar ── -->
  <div v-if="selected.size" class="inv-bulk-bar" style="margin:0">
    <span class="inv-bulk-count"><strong>{{ selected.size }}</strong> log{{ selected.size > 1 ? 's' : '' }} selected</span>
    <button class="inv-bulk-btn" @click="bulkSetStatus('Completed')" :disabled="bulkLoading"><span v-html="icon('check',13)"></span> Mark Completed</button>
    <button class="inv-bulk-btn" @click="bulkSetStatus('Pending')" :disabled="bulkLoading"><span v-html="icon('calendar',13)"></span> Mark Pending</button>
    <button class="inv-bulk-btn inv-bulk-danger" @click="bulkDelete" :disabled="bulkLoading"><span v-html="icon('trash',13)"></span> Delete</button>
    <button class="inv-bulk-clear" @click="clearSelection">✕ Clear</button>
  </div>

  <!-- ── Table ── -->
  <div class="inv-table-wrap">
    <table class="inv-table ml-desktop-tbl">
      <thead>
        <tr>
          <th class="th-check"><input type="checkbox" class="ml-checkbox" :checked="allChecked" @change="toggleAll"/></th>
          <th class="sortable" @click="sortBy('name')"><span class="dp-th-content">Log</span><span class="sort-arrow" v-html="sortArrow('name')"></span></th>
          <th class="sortable" @click="sortBy('asset')">Asset <span class="sort-arrow" v-html="sortArrow('asset')"></span></th>
          <th class="sortable" @click="sortBy('maintenance_date')">Date <span class="sort-arrow" v-html="sortArrow('maintenance_date')"></span></th>
          <th class="sortable" @click="sortBy('technician')">Technician <span class="sort-arrow" v-html="sortArrow('technician')"></span></th>
          <th class="ta-r sortable" @click="sortBy('cost')">Cost <span class="sort-arrow" v-html="sortArrow('cost')"></span></th>
          <th class="sortable" @click="sortBy('status')">Status <span class="sort-arrow" v-html="sortArrow('status')"></span></th>
          <th style="width:110px;text-align:center">Actions</th>
        </tr>
      </thead>
      <tbody>
        <template v-if="loading">
          <tr v-for="n in 5" :key="n" class="shimmer-row"><td colspan="8"><div class="shimmer" style="width:70%"></div></td></tr>
        </template>
        <tr v-else-if="!sortedLogs.length">
          <td colspan="8" class="bk-empty-state">
            <div class="bk-empty-inner">
              <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.3"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              <p class="bk-empty-title">{{ searchTerm || statusFilter !== 'all' ? 'No matching logs' : 'No maintenance logs yet' }}</p>
              <p v-if="searchTerm || statusFilter !== 'all' || filterAsset" class="bk-empty-sub">Try adjusting your search or filter</p>
              <p v-else class="bk-empty-sub">Add your first maintenance log to get started.</p>
              <button v-if="!searchTerm && !filterAsset && statusFilter === 'all'" class="bk-empty-btn" @click="openNewLogForm"><span v-html="icon('plus',13)"></span> New Log</button>
            </div>
          </td>
        </tr>
        <tr v-else v-for="log in pagedLogs" :key="log.name" class="inv-row" :class="{selected: selected.has(log.name)}">
          <td class="td-check" @click.stop><input type="checkbox" class="ml-checkbox" :checked="selected.has(log.name)" @change="toggle(log.name)"/></td>
          <td @click="openEditLogForm(log)" data-label="Log"><span class="inv-link">{{ log.name }}</span></td>
          <td @click="openEditLogForm(log)" data-label="Asset"><span v-if="log.asset" class="it-group-badge">{{ log.asset }}</span><span v-else class="text-muted">—</span></td>
          <td @click="openEditLogForm(log)" class="mono-sm text-muted" data-label="Date">{{ log.maintenance_date || '—' }}</td>
          <td @click="openEditLogForm(log)" class="text-muted" data-label="Technician">{{ log.technician || '—' }}</td>
          <td @click="openEditLogForm(log)" class="ta-r mono-sm fw-600" data-label="Cost">{{ fmt(log.cost || 0) }}</td>
          <td @click="openEditLogForm(log)" data-label="Status"><span class="inv-status-badge" :class="statusClass(log.status)">{{ log.status || 'Pending' }}</span></td>
          <td style="text-align:center;white-space:nowrap" @click.stop>
            <button class="inv-act-btn" @click="openEditLogForm(log)" title="Edit"><span v-html="icon('edit',13)"></span></button>
            <button class="inv-act-btn" style="color:#dc2626" @click="confirmDelete(log)" title="Delete"><span v-html="icon('trash',13)"></span></button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Mobile cards (shown at ≤768px) -->
    <div class="ml-mobile-cards">
      <template v-if="loading">
        <div v-for="n in 4" :key="n" class="b-shimmer" style="height:84px;border-radius:10px"></div>
      </template>
      <div v-else-if="!sortedLogs.length" class="ml-mobile-empty">
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" stroke-width="1.5" style="margin:0 auto 10px;display:block"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        <div>{{ searchTerm || statusFilter !== 'all' ? 'No matching logs' : 'No maintenance logs yet' }}</div>
      </div>
      <div v-else v-for="log in pagedLogs" :key="log.name" class="ii-mob-card" @click="openEditLogForm(log)">
        <div class="ii-mob-card-main">
          <div class="ii-mob-card-top">
            <span class="fw-700" style="font-size:14px;color:#111827;line-height:1.3">{{ log.name }}</span>
            <span class="inv-status-badge" :class="statusClass(log.status)" style="flex-shrink:0">{{ log.status || 'Pending' }}</span>
          </div>
          <div class="ii-mob-card-meta">
            <span class="text-muted" style="font-size:11.5px">{{ log.asset || '—' }} · {{ log.maintenance_date || '—' }}</span>
          </div>
        </div>
        <div class="ii-mob-card-right">
          <div class="fw-700" style="font-size:14px;color:#16a34a">{{ fmt(log.cost || 0) }}</div>
          <div class="text-muted" style="font-size:11px">{{ log.technician || '—' }}</div>
        </div>
        <div class="ii-mob-card-actions">
          <button @click.stop="openEditLogForm(log)" class="ii-qa-btn ii-qa-edit" title="Edit" v-html="icon('edit',13)"></button>
          <button @click.stop="confirmDelete(log)" class="ii-qa-btn ii-qa-del" title="Delete" v-html="icon('trash',13)"></button>
        </div>
      </div>
    </div>
  </div>

  <!-- ── Pagination ── -->
  <div v-if="!loading && sortedLogs.length" class="list-pagination" style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap">
    <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="sortedLogs.length" />
    <div class="dp-footer-info">
      Showing <strong>{{ pageStart }}</strong> to <strong>{{ pageEnd }}</strong> of <strong>{{ sortedLogs.length }}</strong> logs
    </div>
  </div>

  <MaintenanceLogForm
    v-if="showForm"
    :is-edit="isEdit"
    :log="selectedLog"
    @close="closeLogForm"
    @save="saveLog"
  />
</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { apiList, apiSave, apiDelete, apiCall } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { useConfirm } from "../composables/useConfirm.js";
import { usePagination } from "../composables/usePagination.js";
import { icon } from "../utils/icons.js";
import { fmt } from "../utils/format.js";
import Pagination from "../components/Pagination.vue";
import MaintenanceLogForm from "./MaintenanceLogForm.vue";

const { toast } = useToast();
const { confirm } = useConfirm();

const list = ref([]);
const loading = ref(false);
const searchTerm = ref("");
const statusFilter = ref("all");
const filterAsset = ref("");
const allAssets = ref([]);
const showForm = ref(false);
const isEdit = ref(false);
const selectedLog = ref(null);
const logStatuses = ["Completed", "Pending", "Cancelled"];
const selected = ref(new Set());
const bulkLoading = ref(false);

const distinctAssets = computed(() => {
  const assets = list.value.map(l => l.asset).filter(Boolean);
  return [...new Set(assets)].sort();
});

const statusCounts = computed(() => {
  const counts = {};
  for (const s of logStatuses) counts[s] = 0;
  for (const l of list.value) {
    if (counts[l.status] !== undefined) counts[l.status]++;
  }
  return counts;
});

const filteredLogs = computed(() => {
  let items = list.value;
  if (statusFilter.value !== "all") {
    items = items.filter(l => l.status === statusFilter.value);
  }
  if (filterAsset.value) {
    items = items.filter(l => l.asset === filterAsset.value);
  }
  if (searchTerm.value) {
    const term = searchTerm.value.toLowerCase();
    items = items.filter(l =>
      (l.name || "").toLowerCase().includes(term) ||
      (l.asset || "").toLowerCase().includes(term) ||
      (l.technician || "").toLowerCase().includes(term) ||
      (l.work_done || "").toLowerCase().includes(term)
    );
  }
  return items;
});

const sortKey = ref("");
const sortDir = ref(1);

function sortBy(key) {
  if (sortKey.value === key) sortDir.value *= -1;
  else { sortKey.value = key; sortDir.value = 1; }
}

const sortedLogs = computed(() => {
  if (!sortKey.value) return filteredLogs.value;
  const key = sortKey.value;
  const dir = sortDir.value;
  return [...filteredLogs.value].sort((a, b) => {
    const av = a[key] ?? "";
    const bv = b[key] ?? "";
    if (typeof av === "number" || typeof bv === "number") return ((parseFloat(av) || 0) - (parseFloat(bv) || 0)) * dir;
    return String(av).localeCompare(String(bv), undefined, { numeric: true }) * dir;
  });
});

const { page, pageSize, paged, totalItems } = usePagination(sortedLogs, { defaultPageSize: 25, storageKey: "maint-logs" });
const pagedLogs = paged;

const pageStart = computed(() => totalItems.value === 0 ? 0 : (page.value - 1) * pageSize.value + 1);
const pageEnd = computed(() => Math.min(totalItems.value, page.value * pageSize.value));

const totalCost = computed(() => list.value.reduce((sum, row) => sum + (parseFloat(row.cost) || 0), 0));

const avgCost = computed(() => {
  const costed = list.value.filter(l => parseFloat(l.cost) > 0);
  return costed.length ? costed.reduce((sum, l) => sum + parseFloat(l.cost), 0) / costed.length : 0;
});

const allChecked = computed(() => {
  return selected.value.size === pagedLogs.value.length && pagedLogs.value.length > 0;
});

function toggleAll() {
  if (allChecked.value) {
    selected.value.clear();
  } else {
    for (const log of pagedLogs.value) {
      selected.value.add(log.name);
    }
  }
}

function toggle(name) {
  if (selected.value.has(name)) {
    selected.value.delete(name);
  } else {
    selected.value.add(name);
  }
}

function clearSelection() {
  selected.value = new Set();
}

function sortArrow(key) {
  if (sortKey.value !== key) return "";
  return sortDir.value === 1 ? "&#9650;" : "&#9660;";
}

function statusClass(status) {
  const map = {
    "Completed": "status-active",
    "Pending": "status-partial",
    "Cancelled": "status-cancelled",
  };
  return map[status] || "status-partial";
}

async function bulkSetStatus(status) {
  if (!selected.value.size) return;
  bulkLoading.value = true;
  try {
    const names = [...selected.value];
    await Promise.all(names.map(name =>
      apiCall("frappe.client.set_value", { doctype: "Maintenance Log", name, field: "status", value: status })
    ));
    toast.success(`${names.length} log${names.length > 1 ? "s" : ""} marked ${status}`);
    clearSelection();
    await load();
  } catch (e) {
    toast.error("Failed to update logs: " + e.message);
  } finally {
    bulkLoading.value = false;
  }
}

async function bulkDelete() {
  if (!selected.value.size) return;
  const names = [...selected.value];
  const ok = await confirm({
    title: "Delete Maintenance Logs",
    body: `Are you sure you want to delete ${names.length} selected log${names.length > 1 ? "s" : ""}?`,
    okLabel: "Delete",
    okStyle: "danger",
  });
  if (!ok) return;
  bulkLoading.value = true;
  try {
    await Promise.all(names.map(name => apiDelete("Maintenance Log", name)));
    toast.success("Selected logs deleted");
    clearSelection();
    await load();
  } catch (e) {
    toast.error("Failed to delete logs: " + e.message);
  } finally {
    bulkLoading.value = false;
  }
}

function exportCSV() {
  const headers = ["Log", "Asset", "Date", "Technician", "Cost", "Status"];
  const rows = filteredLogs.value.map(l => [l.name, l.asset || "", l.maintenance_date || "", l.technician || "", l.cost || 0, l.status || "Pending"]);
  const csv = [headers, ...rows].map(row => row.map(v => `"${String(v ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "maintenance-logs.csv";
  a.click();
  URL.revokeObjectURL(url);
}

async function load() {
  loading.value = true;
  try {
    const [rows, assets] = await Promise.all([
      apiList("Maintenance Log", {
        fields: ["name", "asset", "maintenance_date", "technician", "cost", "work_done", "status"],
        order: "modified desc",
        limit: 500,
      }),
      apiList("Asset", {
        fields: ["name", "asset_name"],
        limit: 500,
      }),
    ]);
    list.value = rows || [];
    allAssets.value = assets || [];
  } catch (e) {
    toast.error("Failed to load logs: " + e.message);
    list.value = [];
    allAssets.value = [];
  } finally {
    loading.value = false;
  }
}

function openNewLogForm() {
  isEdit.value = false;
  selectedLog.value = null;
  showForm.value = true;
}

function openEditLogForm(log) {
  isEdit.value = true;
  selectedLog.value = log;
  showForm.value = true;
}

function closeLogForm() {
  showForm.value = false;
}

async function saveLog(formData) {
  try {
    const doc = {
      doctype: "Maintenance Log",
      ...formData,
    };
    if (!isEdit.value || !doc.name) {
      delete doc.name;
    }
    await apiSave(doc);
    toast.success(isEdit.value ? "Log updated" : "Log created");
    showForm.value = false;
    await load();
  } catch (e) {
    toast.error("Failed to save log: " + e.message);
  }
}

async function confirmDelete(log) {
  const ok = await confirm({
    title: "Delete Maintenance Log",
    body: `Are you sure you want to delete maintenance log ${log.name}?`,
    okLabel: "Delete",
    okStyle: "danger",
  });
  if (ok) await deleteLog(log.name);
}

async function deleteLog(name) {
  try {
    await apiDelete("Maintenance Log", name);
    toast.success("Log deleted");
    await load();
  } catch (e) {
    toast.error("Failed to delete log: " + e.message);
  }
}

onMounted(load);
</script>

<style scoped>
.ml-checkbox { width:15px;height:15px;cursor:pointer;accent-color:#1a6ef7; }
.bk-kpi-grid-4 { grid-template-columns: repeat(4, 1fr); }

.it-group-badge {
  display: inline-block;
  padding: 2px 9px;
  border-radius: 12px;
  background: #eef2ff;
  color: #4338ca;
  font-size: 11.5px;
  font-weight: 600;
  white-space: nowrap;
}
.fw-700 { font-weight: 700; }
.fw-600 { font-weight: 600; }
.ta-r { text-align: right; }
.text-muted { color: #9ca3af; }
.mono-sm { font-size: 13px; }
.bk-kpi-blue { color: #2563eb; }

/* Mobile cards */
.ml-mobile-cards { display: none; }
.dp-footer-info { font-size: 12.5px; color: #6b7280; }
.b-shimmer {
  height: 100%;
  border-radius: 8px;
  background: linear-gradient(90deg, #f0f2f5 25%, #e4e7ec 50%, #f0f2f5 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite;
}
@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@media (max-width: 768px) {
  .ml-desktop-tbl { display: none; }
  .ml-mobile-cards {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px;
  }
  .ml-mobile-empty {
    text-align: center;
    padding: 40px 16px;
    color: #9ca3af;
    font-size: 13px;
  }
  .bk-kpi-grid-4 { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 479px) {
  .bk-kpi-grid-4 { grid-template-columns: 1fr 1fr; }
}
</style>