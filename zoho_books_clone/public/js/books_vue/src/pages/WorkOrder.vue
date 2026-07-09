<template>
<div class="list-page">

  <!-- ── Toolbar ── -->
  <div class="sales-toolbar">
    <div class="sales-search">
      <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
      <input v-model="search" placeholder="Search Work Orders, items…" class="sales-search-input"/>
    </div>
    <div class="sales-pills">
      <button v-for="t in tabs" :key="t.key"
        class="sales-pill" :class="{active:filterTab===t.key, ['pill-'+t.key]: t.key!=='all'}"
        @click="filterTab=t.key">
        {{ t.label }}
        <span v-if="t.key!=='all'" class="sales-pill-count">{{ counts[t.key] || 0 }}</span>
      </button>
    </div>
    <div class="sales-actions">
      <button class="sales-btn-ghost" @click="load" title="Refresh" :disabled="loading"><span v-html="icon('refresh',14)"></span></button>
      <button class="sales-btn-primary" @click="openAdd"><span v-html="icon('plus',13)"></span> New Work Order</button>
    </div>
  </div>

  <!-- Table view -->
  <div class="inv-table-wrap">
    <table class="inv-table items-desktop-tbl">
      <thead><tr>
        <th class="sortable" @click="sortBy('name')">Work Order <span v-html="sortArrow('name')"></span></th>
        <th class="sortable" @click="sortBy('production_item')">Item to Manufacture <span v-html="sortArrow('production_item')"></span></th>
        <th>BOM</th>
        <th class="ta-r sortable" @click="sortBy('qty')">Qty <span v-html="sortArrow('qty')"></span></th>
        <th class="ta-r">Produced</th>
        <th>Status</th>
        <th class="ta-r sortable" @click="sortBy('modified')">Last Modified <span v-html="sortArrow('modified')"></span></th>
      </tr></thead>
      <tbody>
        <template v-if="loading"><tr v-for="n in 6" :key="n"><td colspan="7"><div class="shimmer"></div></td></tr></template>
        <tr v-else-if="!sorted.length"><td colspan="7" class="bk-empty-state"><div class="bk-empty-inner">
          <template v-if="search||filterTab!=='all'">
            <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.3"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <p class="bk-empty-title">No Work Orders match your filters</p>
          </template>
          <template v-else>
            <p class="bk-empty-title">No Work Orders yet</p>
            <p class="bk-empty-sub">Create a Work Order from a submitted BOM to start production.</p>
            <button class="bk-empty-btn" @click="openAdd"><span v-html="icon('plus',13)"></span> New Work Order</button>
          </template>
        </div></td></tr>
        <tr v-else v-for="row in paged" :key="row.name" class="inv-row" @click="openView(row)">
          <td data-label="Work Order"><span class="inv-link">{{row.name}}</span></td>
          <td class="fw-600" data-label="Item to Manufacture">{{row.item_name || row.production_item}}</td>
          <td data-label="BOM" class="text-muted mono-sm">{{row.bom}}</td>
          <td class="ta-r" data-label="Qty">{{fmtNum(row.qty)}} {{row.stock_uom}}</td>
          <td class="ta-r" data-label="Produced">{{fmtNum(row.produced_qty)}}</td>
          <td data-label="Status">
            <span class="inv-status-badge" :class="statusClass(row)">{{ row.status }}</span>
          </td>
          <td class="ta-r text-muted mono-sm" data-label="Last Modified">{{fmtDate(row.modified)}}</td>
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
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useToast } from "../composables/useToast.js";
import { apiList } from "../api/client.js";

const router = useRouter();
const { toast } = useToast();

const loading = ref(false);
const list = ref([]);
const search = ref("");
const filterTab = ref("all");
const sortCol = ref("modified");
const sortAsc = ref(false);
const page = ref(1);
const pageSize = 50;

const tabs = [
  { key: "all",         label: "All" },
  { key: "Draft",        label: "Draft" },
  { key: "Submitted",    label: "Submitted" },
  { key: "In Process",   label: "In Process" },
  { key: "Completed",    label: "Completed" },
  { key: "Cancelled",    label: "Cancelled" },
];

onMounted(load);

async function load() {
  loading.value = true;
  try {
    const fields = ["name", "production_item", "item_name", "bom", "qty", "stock_uom",
                     "produced_qty", "status", "docstatus", "modified"];
    const r = await apiList("Work Order", { fields, limit: 1000, order: "modified desc" });
    list.value = r || [];
  } catch (e) {
    toast("Could not load Work Orders: " + e.message, "error");
  }
  loading.value = false;
}

const counts = computed(() => {
  const c = {};
  list.value.forEach(i => { c[i.status] = (c[i.status] || 0) + 1; });
  return c;
});

const filtered = computed(() => {
  let r = list.value;
  if (filterTab.value !== "all") r = r.filter(i => i.status === filterTab.value);

  const q = search.value.toLowerCase().trim();
  if (q) r = r.filter(i => ((i.item_name || "") + (i.production_item || "") + (i.bom || "") + i.name).toLowerCase().includes(q));
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

function sortBy(col) {
  if (sortCol.value === col) sortAsc.value = !sortAsc.value;
  else { sortCol.value = col; sortAsc.value = true; }
}

function sortArrow(col) {
  if (sortCol.value !== col) return "";
  return icon(sortAsc.value ? 'arrowU' : 'arrowD', 11);
}

function statusClass(row) {
  if (row.status === "Completed") return "status-active";
  if (row.status === "Cancelled") return "status-inactive";
  if (row.status === "Draft") return "status-inactive";
  return "status-active";
}

function fmtNum(n) {
  if (n === undefined || n === null) return "0";
  return Number(n).toLocaleString("en-IN", { maximumFractionDigits: 3 });
}

function fmtDate(d) {
  if (!d) return "";
  const obj = new Date(d);
  if (isNaN(obj)) return d;
  return obj.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function openAdd() {
  router.push("/manufacturing/work-order/new");
}

function openView(row) {
  router.push(`/manufacturing/work-order/${row.name}`);
}

// ── Icons ─────────────────────────────────────────────────────────────
const ICONS = {
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
  refresh: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
  arrowU: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="19" x2="12" y2="5"></line><polyline points="5 12 12 5 19 12"></polyline></svg>',
  arrowD: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><polyline points="19 12 12 19 5 12"></polyline></svg>',
  chevL: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>',
  chevR: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>',
};
function icon(name, size) {
  return (ICONS[name] || "").replace("<svg ", `<svg width="${size}" height="${size}" `);
}
</script>