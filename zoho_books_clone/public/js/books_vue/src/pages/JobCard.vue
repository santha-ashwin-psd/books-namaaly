<template>
<div class="list-page">

  <!-- ── Toolbar ── -->
  <div class="sales-toolbar">
    <div class="sales-search">
      <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
      <input v-model="search" placeholder="Search Job Cards..." class="sales-search-input"/>
    </div>
    <div class="sales-pills">
      <button v-for="t in tabs" :key="t.key"
        class="sales-pill" :class="{active: filterTab===t.key}"
        @click="filterTab=t.key">
        {{ t.label }}
        <span v-if="t.key!=='all'" class="sales-pill-count">{{ counts[t.key] }}</span>
      </button>
    </div>
    <div class="sales-actions">
      <button class="sales-btn-ghost" @click="load" title="Refresh" :disabled="loading"><span v-html="icon('refresh',14)"></span></button>
      <button class="sales-btn-primary" @click="openAdd"><span v-html="icon('plus',13)"></span> Add Job Card</button>
    </div>
  </div>

  <!-- Bulk bar -->
  <div v-if="selected.size" class="inv-bulk-bar" style="margin:0 0 12px">
    <span class="inv-bulk-count">{{ selected.size }} selected</span>
    <button class="inv-bulk-btn inv-bulk-danger" @click="bulkDelete" :disabled="bulkBusy">
      <span v-html="icon('trash',13)"></span> Delete selected
    </button>
    <button class="inv-bulk-clear" @click="selected.clear()">✕ Clear</button>
  </div>

  <!-- Table -->
  <div class="inv-table-wrap">
    <table class="inv-table items-desktop-tbl">
      <thead><tr>
        <th class="th-check"><input type="checkbox" @change="toggleAll" :checked="allChecked"/></th>
        <th class="sortable" @click="sortBy('name')">Job Card <span v-html="sortArrow('name')"></span></th>
        <th class="sortable" @click="sortBy('work_order')">Work Order <span v-html="sortArrow('work_order')"></span></th>
        <th class="sortable" @click="sortBy('operation')">Operation <span v-html="sortArrow('operation')"></span></th>
        <th>Workstation</th>
        <th>Status</th>
        <th class="ta-r sortable" @click="sortBy('modified')">Modified <span v-html="sortArrow('modified')"></span></th>
        <th style="width:90px;text-align:center">Actions</th>
      </tr></thead>
      <tbody>
        <template v-if="loading"><tr v-for="n in 5" :key="n"><td colspan="8"><div class="shimmer"></div></td></tr></template>
        <tr v-else-if="!sorted.length"><td colspan="8" class="bk-empty-state"><div class="bk-empty-inner">
          <template v-if="search || filterTab!=='all'">
            <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.3"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <p class="bk-empty-title">No Job Cards match your filters</p>
          </template>
          <template v-else>
            <p class="bk-empty-title">No Job Cards yet</p>
            <p class="bk-empty-sub">Job Cards are auto-created when a Work Order is submitted for operations with batch tracking enabled.</p>
            <button class="bk-empty-btn" @click="openAdd"><span v-html="icon('plus',13)"></span> Add Job Card</button>
          </template>
        </div></td></tr>
        <tr v-else v-for="row in paged" :key="row.name" class="inv-row" :class="{selected: selected.has(row.name)}">
          <td class="td-check" @click.stop><input type="checkbox" :checked="selected.has(row.name)" @change="toggle(row.name)"/></td>
          <td @click="openView(row)" data-label="Job Card"><span class="inv-link fw-600">{{ row.name }}</span></td>
          <td @click="openView(row)" data-label="Work Order"><span class="text-muted">{{ row.work_order || '—' }}</span></td>
          <td @click="openView(row)" data-label="Operation"><span class="text-muted">{{ row.operation || '—' }}</span></td>
          <td @click="openView(row)" data-label="Workstation"><span class="text-muted">{{ row.workstation || '—' }}</span></td>
          <td @click="openView(row)" data-label="Status">
            <span class="inv-status-badge" :class="statusClass(row.status)">{{ row.status }}</span>
          </td>
          <td @click="openView(row)" class="ta-r text-muted mono-sm">{{ fmtDate(row.modified) }}</td>
          <td style="text-align:center;white-space:nowrap" @click.stop>
            <button class="inv-act-btn" style="color:#dc2626" @click="confirmDel(row)" title="Delete"><span v-html="icon('trash',13)"></span></button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <div class="sales-pagination" v-if="sorted.length > pageSize">
    <div class="sales-page-info">Showing {{ (page-1)*pageSize+1 }} – {{ Math.min(page*pageSize, sorted.length) }} of {{ sorted.length }}</div>
    <div class="sales-page-controls">
      <button class="sales-page-btn" :disabled="page<=1" @click="page--"><span v-html="icon('chevL',12)"></span></button>
      <button class="sales-page-btn" :disabled="page>=totalPages" @click="page++"><span v-html="icon('chevR',12)"></span></button>
    </div>
  </div>

</div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import { useToast } from "../composables/useToast.js";
import { useConfirm } from "../composables/useConfirm.js";
import { apiList, apiDelete } from "../api/client.js";

const router = useRouter();
const { toast } = useToast();
const { confirm } = useConfirm();

const loading = ref(false);
const list = ref([]);
const search = ref("");
const filterTab = ref("all");
const sortCol = ref("modified");
const sortAsc = ref(false);
const page = ref(1);
const pageSize = 50;
const selected = ref(new Set());
const bulkBusy = ref(false);

const tabs = [
  { key: "all",              label: "All" },
  { key: "Open",             label: "Open" },
  { key: "Work In Progress", label: "In Progress" },
  { key: "Completed",        label: "Completed" },
  { key: "Cancelled",        label: "Cancelled" },
];

onMounted(load);
watch([search, filterTab], () => { page.value = 1; });

async function load() {
  loading.value = true;
  try {
    list.value = await apiList("Job Card", {
      fields: ["name", "work_order", "operation", "workstation", "status", "modified"],
      limit: 2000, order: "modified desc",
    }) || [];
  } catch (e) {
    toast("Could not load Job Cards", "error");
  }
  loading.value = false;
  selected.value.clear();
}

const counts = computed(() => {
  const c = { all: list.value.length, "Open": 0, "Work In Progress": 0, "Completed": 0, "Cancelled": 0 };
  list.value.forEach(r => { if (c[r.status] !== undefined) c[r.status]++; });
  return c;
});

const filtered = computed(() => {
  let r = list.value;
  if (filterTab.value !== "all") r = r.filter(i => i.status === filterTab.value);
  const q = search.value.toLowerCase().trim();
  if (q) r = r.filter(i => [i.name, i.work_order, i.operation, i.workstation].filter(Boolean).join(" ").toLowerCase().includes(q));
  return r;
});

const sorted = computed(() => {
  const r = [...filtered.value];
  const c = sortCol.value, asc = sortAsc.value ? 1 : -1;
  r.sort((a, b) => { const va = a[c]||"", vb = b[c]||""; return va < vb ? -asc : va > vb ? asc : 0; });
  return r;
});

const totalPages = computed(() => Math.ceil(sorted.value.length / pageSize) || 1);
const paged = computed(() => sorted.value.slice((page.value-1)*pageSize, page.value*pageSize));
const allChecked = computed(() => paged.value.length > 0 && paged.value.every(r => selected.value.has(r.name)));

function toggleAll(e) { if (e.target.checked) paged.value.forEach(r => selected.value.add(r.name)); else paged.value.forEach(r => selected.value.delete(r.name)); }
function toggle(name) { if (selected.value.has(name)) selected.value.delete(name); else selected.value.add(name); }
function sortBy(col) { if (sortCol.value===col) sortAsc.value=!sortAsc.value; else { sortCol.value=col; sortAsc.value=true; } }
function sortArrow(col) { if (sortCol.value!==col) return ""; return icon(sortAsc.value?"arrowU":"arrowD", 11); }
function fmtDate(d) { if (!d) return ""; const o=new Date(d); return isNaN(o)?d:o.toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"}); }
function openAdd()     { router.push("/manufacturing/job-card/new"); }
function openView(row) { router.push(`/manufacturing/job-card/${row.name}`); }

function statusClass(s) {
  if (s==="Completed")        return "status-active";
  if (s==="Work In Progress") return "status-draft";
  if (s==="Cancelled")        return "status-inactive";
  return "status-pending";
}

async function confirmDel(row) {
  if (await confirm({ title: "Delete Job Card?", body: `Delete ${row.name}?`, okLabel: "Delete", okStyle: "danger" })) {
    try { await apiDelete("Job Card", row.name); toast("Job Card deleted"); load(); }
    catch (e) { toast("Could not delete: " + e.message, "error"); }
  }
}

async function bulkDelete() {
  const rows = list.value.filter(r => selected.value.has(r.name));
  if (!rows.length) return;
  if (!(await confirm({ title: `Delete ${rows.length} Job Card(s)?`, body: "This cannot be undone.", okLabel: "Delete", okStyle: "danger" }))) return;
  bulkBusy.value = true;
  let deleted = 0, skipped = 0;
  for (const row of rows) {
    try { await apiDelete("Job Card", row.name); deleted++; } catch { skipped++; }
  }
  bulkBusy.value = false;
  toast(`Deleted ${deleted}` + (skipped ? `, ${skipped} skipped` : ""));
  selected.value.clear();
  load();
}

const ICONS = {
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
  refresh:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>',
  plus:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
  trash:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>',
  arrowU: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="19" x2="12" y2="5"></line><polyline points="5 12 12 5 19 12"></polyline></svg>',
  arrowD: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><polyline points="19 12 12 19 5 12"></polyline></svg>',
  chevL:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>',
  chevR:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>',
};
function icon(name, size) { return (ICONS[name]||"").replace("<svg ", `<svg width="${size}" height="${size}" `); }
</script>
