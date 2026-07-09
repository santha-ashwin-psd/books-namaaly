<template>
<div class="list-page">

  <!-- ── Toolbar ── -->
  <div class="sales-toolbar">
    <div class="sales-search">
      <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
      <input v-model="search" placeholder="Search Operations..." class="sales-search-input"/>
    </div>
    <div class="sales-pills">
      <button v-for="t in tabs" :key="t.key"
        class="sales-pill" :class="{active:filterTab===t.key, ['pill-'+t.key]: t.key!=='all'}"
        @click="filterTab=t.key">
        {{ t.label }}
        <span v-if="t.key!=='all'" class="sales-pill-count">{{ counts[t.key] }}</span>
      </button>
    </div>
    <div class="sales-actions">
      <button class="sales-btn-ghost" @click="load" title="Refresh" :disabled="loading"><span v-html="icon('refresh',14)"></span></button>
      <button class="sales-btn-primary" @click="openAdd"><span v-html="icon('plus',13)"></span> Add Operation</button>
    </div>
  </div>

  <!-- Bulk action bar -->
  <div v-if="selected.size" class="inv-bulk-bar" style="margin: 0 0 12px">
    <span class="inv-bulk-count">{{ selected.size }} selected</span>
    <button class="inv-bulk-btn inv-bulk-danger" @click="bulkDelete" :disabled="bulkBusy">
      <span v-html="icon('trash',13)"></span> Delete selected
    </button>
    <button class="inv-bulk-clear" @click="selected.clear()">✕ Clear</button>
  </div>

  <!-- Table view -->
  <div class="inv-table-wrap">
    <table class="inv-table items-desktop-tbl">
      <thead><tr>
        <th class="th-check"><input type="checkbox" @change="toggleAll" :checked="allChecked"/></th>
        <th class="sortable" @click="sortBy('name')">ID <span v-html="sortArrow('name')"></span></th>
        <th class="sortable" @click="sortBy('default_workstation')">Default Workstation <span v-html="sortArrow('default_workstation')"></span></th>
        <th>Status</th>
        <th class="ta-r sortable" @click="sortBy('modified')">Last Modified <span v-html="sortArrow('modified')"></span></th>
        <th style="width:90px;text-align:center">Actions</th>
      </tr></thead>
      <tbody>
        <template v-if="loading"><tr v-for="n in 6" :key="n"><td colspan="6"><div class="shimmer"></div></td></tr></template>
        <tr v-else-if="!sorted.length"><td colspan="6" class="bk-empty-state"><div class="bk-empty-inner">
          <template v-if="search||filterTab!=='all'">
            <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.3"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <p class="bk-empty-title">No operations match your filters</p>
          </template>
          <template v-else>
            <p class="bk-empty-title">No Operations yet</p>
            <p class="bk-empty-sub">Create your first Operation (e.g., Assembly, Packaging).</p>
            <button class="bk-empty-btn" @click="openAdd"><span v-html="icon('plus',13)"></span> Add Operation</button>
          </template>
        </div></td></tr>
        <tr v-else v-for="row in paged" :key="row.name" class="inv-row" :class="{selected:selected.has(row.name)}">
          <td class="td-check" @click.stop><input type="checkbox" :checked="selected.has(row.name)" @change="toggle(row.name)"/></td>
          <td @click="openView(row)" data-label="ID"><span class="inv-link fw-600">{{row.name}}</span></td>
          <td @click="openView(row)" data-label="Default Workstation"><span class="text-muted">{{row.default_workstation || '—'}}</span></td>
          <td @click="openView(row)" data-label="Status"><span class="inv-status-badge" :class="!row.is_active?'status-inactive':'status-active'">{{!row.is_active?'Inactive':'Active'}}</span></td>
          <td @click="openView(row)" class="ta-r text-muted mono-sm" data-label="Last Modified">{{fmtDate(row.modified)}}</td>
          <td style="text-align:center;white-space:nowrap" @click.stop>
            <button class="inv-act-btn" style="color:#dc2626" @click="confirmDel(row)" title="Delete"><span v-html="icon('trash',13)"></span></button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <div class="sales-pagination" v-if="sorted.length > pageSize">
    <div class="sales-page-info">Showing {{ (page - 1) * pageSize + 1 }} - {{ Math.min(page * pageSize, sorted.length) }} of {{ sorted.length }}</div>
    <div class="sales-page-controls">
      <button class="sales-page-btn" :disabled="page <= 1" @click="page--"><span v-html="icon('chevL',12)"></span></button>
      <button class="sales-page-btn" :disabled="page >= totalPages" @click="page++"><span v-html="icon('chevR',12)"></span></button>
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
  { key: "all",      label: "All" },
  { key: "active",   label: "Active" },
  { key: "inactive", label: "Inactive" },
];

onMounted(load);

watch([search, filterTab], () => { page.value = 1; });

async function load() {
  loading.value = true;
  try {
    const fields = ["name", "default_workstation", "is_active", "modified"];
    const r = await apiList("Operation", { fields, limit: 1000, order: "modified desc" });
    list.value = r || [];
  } catch (e) {
    toast("Could not load Operations", "error");
  }
  loading.value = false;
  selected.value.clear();
}

const counts = computed(() => {
  const c = { all: list.value.length, active: 0, inactive: 0 };
  list.value.forEach(i => {
    if (i.is_active) c.active++;
    if (!i.is_active) c.inactive++;
  });
  return c;
});

const filtered = computed(() => {
  let r = list.value;
  if (filterTab.value === "active")   r = r.filter(i =>  i.is_active);
  if (filterTab.value === "inactive") r = r.filter(i => !i.is_active);
  
  const q = search.value.toLowerCase().trim();
  if (q) r = r.filter(i => [i.name, i.default_workstation].filter(Boolean).join(" ").toLowerCase().includes(q));
  return r;
});

const sorted = computed(() => {
  const r = [...filtered.value];
  const c = sortCol.value;
  const asc = sortAsc.value ? 1 : -1;
  r.sort((a, b) => {
    const va = a[c] || "";
    const vb = b[c] || "";
    if (va < vb) return -1 * asc;
    if (va > vb) return 1 * asc;
    return 0;
  });
  return r;
});

const totalPages = computed(() => Math.ceil(sorted.value.length / pageSize) || 1);
const paged = computed(() => sorted.value.slice((page.value - 1) * pageSize, page.value * pageSize));

const allChecked = computed(() => paged.value.length > 0 && paged.value.every(r => selected.value.has(r.name)));
function toggleAll(e) {
  if (e.target.checked) paged.value.forEach(r => selected.value.add(r.name));
  else paged.value.forEach(r => selected.value.delete(r.name));
}
function toggle(name) {
  if (selected.value.has(name)) selected.value.delete(name);
  else selected.value.add(name);
}

function sortBy(col) {
  if (sortCol.value === col) sortAsc.value = !sortAsc.value;
  else { sortCol.value = col; sortAsc.value = true; }
}

function sortArrow(col) {
  if (sortCol.value !== col) return "";
  return icon(sortAsc.value ? 'arrowU' : 'arrowD', 11);
}

function fmtDate(d) {
  if (!d) return "";
  const obj = new Date(d);
  if (isNaN(obj)) return d;
  return obj.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function openAdd() {
  router.push("/manufacturing/operation/new");
}

function openView(row) {
  router.push(`/manufacturing/operation/${row.name}`);
}

async function isOperationDeletable(row) {
  try {
    const [inBom, inWo] = await Promise.all([
      apiList("BOM Operation", { fields: ["parent"], filters: [["operation", "=", row.name]], limit: 1 }),
      apiList("Work Order Operation", { fields: ["parent"], filters: [["operation", "=", row.name]], limit: 1 }),
    ]);
    if (inBom && inBom.length) {
      toast(`${row.name} is used in BOM ${inBom[0].parent} and cannot be deleted.`, "error");
      return false;
    }
    if (inWo && inWo.length) {
      toast(`${row.name} is used in Work Order ${inWo[0].parent} and cannot be deleted.`, "error");
      return false;
    }
  } catch (e) {
    toast(`Could not verify whether ${row.name} is in use — try again.`, "error");
    return false;
  }
  return true;
}

async function confirmDel(row) {
  if (!(await isOperationDeletable(row))) return;
  if (await confirm({ title: "Delete Operation?", body: `Are you sure you want to delete ${row.name}?`, okLabel: "Delete", okStyle: "danger" })) {
    try {
      await apiDelete("Operation", row.name);
      toast("Operation deleted");
      load();
    } catch (e) {
      toast("Could not delete Operation: " + e.message, "error");
    }
  }
}

async function bulkDelete() {
  const rows = list.value.filter(r => selected.value.has(r.name));
  if (!rows.length) return;
  if (!(await confirm({
    title: "Delete selected Operations?",
    body: `Are you sure you want to delete ${rows.length} Operation${rows.length > 1 ? "s" : ""}?`,
    okLabel: "Delete",
    okStyle: "danger",
  }))) return;

  bulkBusy.value = true;
  let deleted = 0, skipped = 0;
  for (const row of rows) {
    if (!(await isOperationDeletable(row))) { skipped++; continue; }
    try {
      await apiDelete("Operation", row.name);
      deleted++;
    } catch (e) {
      skipped++;
    }
  }
  bulkBusy.value = false;

  if (deleted) toast(`Deleted ${deleted} Operation${deleted > 1 ? "s" : ""}` + (skipped ? `, ${skipped} skipped` : ""));
  else toast("No Operations were deleted", "error");

  selected.value.clear();
  load();
}

// ── Icons ─────────────────────────────────────────────────────────────
const ICONS = {
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
  refresh: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>',
  arrowU: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="19" x2="12" y2="5"></line><polyline points="5 12 12 5 19 12"></polyline></svg>',
  arrowD: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><polyline points="19 12 12 19 5 12"></polyline></svg>',
  chevL: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>',
  chevR: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>',
};
function icon(name, size) {
  return (ICONS[name] || "").replace("<svg ", `<svg width="${size}" height="${size}" `);
}
</script>