<template>
<div class="bomx-page">

  <!-- ══════════ STAT CARDS ══════════ -->
  <div class="bomx-stats-row">
    <div class="bomx-stat-card" style="border-left-color:var(--bx-mfg)">
      <div class="bomx-stat-label" style="color:var(--bx-mfg)">TOTAL WORKSTATIONS</div>
      <div class="bomx-stat-value">{{ list.length }}</div>
      <div class="bomx-stat-sub">All types</div>
    </div>
    <div class="bomx-stat-card" style="border-left-color:var(--bx-green)">
      <div class="bomx-stat-label" style="color:var(--bx-green)">ACTIVE</div>
      <div class="bomx-stat-value">{{ activeCount }}</div>
      <div class="bomx-stat-sub">Currently in use</div>
    </div>
    <div class="bomx-stat-card" style="border-left-color:var(--bx-muted)">
      <div class="bomx-stat-label" style="color:var(--bx-muted)">INACTIVE</div>
      <div class="bomx-stat-value">{{ inactiveCount }}</div>
      <div class="bomx-stat-sub">Not in use</div>
    </div>
    <div class="bomx-stat-card" style="border-left-color:var(--bx-amber)">
      <div class="bomx-stat-label" style="color:var(--bx-amber)">AVG COST / HOUR</div>
      <div class="bomx-stat-value">{{ fmtCurrency(avgHourRate) }}</div>
      <div class="bomx-stat-sub">Across all workstations</div>
    </div>
  </div>

  <!-- ══════════ TOOLBAR ══════════ -->
  <div class="bomx-toolbar">
    <div class="bomx-search-wrap">
      <span class="bomx-search-icon" v-html="icon('search',15)"></span>
      <input class="bomx-search-input" v-model="search" type="text" placeholder="Search workstations…"/>
    </div>
    <select class="bomx-fi" v-model="filterType" style="width:150px">
      <option value="">All Types</option>
      <option v-for="t in types" :key="t.name" :value="t.name">{{ t.name }}</option>
    </select>
    <select class="bomx-fi" v-model="filterStatus" style="width:130px">
      <option value="">All Status</option>
      <option value="active">Active</option>
      <option value="inactive">Inactive</option>
    </select>
    <div style="flex:1"></div>
    <span class="bomx-toolbar-count">{{ sorted.length }} workstation{{ sorted.length===1?'':'s' }}</span>
    <div class="bomx-view-toggle">
      <button type="button" :class="{active: viewMode==='grid'}" @click="viewMode='grid'" title="Grid view" v-html="icon('grid',15)"></button>
      <button type="button" :class="{active: viewMode==='list'}" @click="viewMode='list'" title="List view" v-html="icon('list',15)"></button>
    </div>
    <button class="bomx-btn bomx-btn-mfg" @click="openAdd"><span v-html="icon('plus',13)"></span> New Workstation</button>
  </div>

  <!-- ══════════ LOADING ══════════ -->
  <div v-if="loading" class="bomx-grid">
    <div v-for="n in 6" :key="n" class="bomx-ws-card"><div class="shimmer" style="height:190px;border-radius:var(--bx-radius)"></div></div>
  </div>

  <!-- ══════════ EMPTY ══════════ -->
  <div v-else-if="!sorted.length" class="bomx-empty-state">
    <div class="bomx-empty-icon">⚙️</div>
    <div class="bomx-empty-title">No Workstations found</div>
    <div class="bomx-empty-sub">Try adjusting your search or filters, or create a new workstation.</div>
    <button class="bomx-btn bomx-btn-mfg" @click="openAdd"><span v-html="icon('plus',13)"></span> Create Workstation</button>
  </div>

  <!-- ══════════ GRID VIEW ══════════ -->
  <div v-else-if="viewMode==='grid'" class="bomx-grid">
    <div v-for="row in sorted" :key="row.name" class="bomx-ws-card" @click="selectWorkstation(row.name)">
      <div class="bomx-ws-card-hdr">
        <div class="bomx-ws-icon">{{ typeIcon(row.workstation_type) }}</div>
        <div style="min-width:0;flex:1">
          <div class="bomx-ws-title">{{ row.workstation_name || row.name }}</div>
          <div class="bomx-ws-code mono">{{ row.name }}<span v-if="row.workstation_type"> · {{ row.workstation_type }}</span></div>
        </div>
      </div>
      <div class="bomx-ws-badges">
        <span class="bomx-badge" style="background:var(--bx-mfgS);color:var(--bx-mfgB)" v-if="row.workstation_type">{{ row.workstation_type }}</span>
        <span class="bomx-badge" :class="statusClass(row)">{{ statusLabel(row) }}</span>
      </div>
      <div class="bomx-ws-stats">
        <div>
          <div class="bomx-ws-stat-lbl">Job Capacity</div>
          <div class="bomx-ws-stat-val">{{ row.capacity ?? '—' }}</div>
        </div>
        <div>
          <div class="bomx-ws-stat-lbl">Cost / Hour</div>
          <div class="bomx-ws-stat-val">{{ fmtCurrency(row.hour_rate) }}</div>
        </div>
      </div>
      <div class="bomx-ws-footer">
        <span class="bomx-ws-loc">{{ row.warehouse || '—' }}</span>
        <div style="display:flex;gap:6px">
          <button class="bomx-btn-icon" @click.stop="selectWorkstation(row.name)" title="Edit"><span v-html="icon('edit',13)"></span></button>
          <button class="bomx-btn-icon danger" @click.stop="quickDelete(row)" title="Delete"><span v-html="icon('trash',13)"></span></button>
        </div>
      </div>
    </div>
  </div>

  <!-- ══════════ LIST VIEW ══════════ -->
  <div v-else class="bomx-table-wrap">
    <table class="bomx-table">
      <thead>
        <tr>
          <th>Code</th><th>Name</th><th>Type</th><th>Warehouse</th>
          <th>Job Capacity</th><th>Cost/Hr</th><th>Status</th><th style="width:80px"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in sorted" :key="row.name" @click="selectWorkstation(row.name)">
          <td class="mono">{{ row.name }}</td>
          <td style="font-weight:600;color:var(--bx-text)">{{ row.workstation_name || row.name }}</td>
          <td>
            <span class="bomx-badge" style="background:var(--bx-mfgS);color:var(--bx-mfgB)" v-if="row.workstation_type">{{ row.workstation_type }}</span>
            <span v-else style="color:var(--bx-muted)">—</span>
          </td>
          <td>{{ row.warehouse || '—' }}</td>
          <td>{{ row.capacity ?? '—' }}</td>
          <td>{{ fmtCurrency(row.hour_rate) }}</td>
          <td><span class="bomx-badge" :class="statusClass(row)">{{ statusLabel(row) }}</span></td>
          <td>
            <div style="display:flex;gap:6px;justify-content:flex-end">
              <button class="bomx-btn-icon" @click.stop="selectWorkstation(row.name)" title="Edit"><span v-html="icon('edit',13)"></span></button>
              <button class="bomx-btn-icon danger" @click.stop="quickDelete(row)" title="Delete"><span v-html="icon('trash',13)"></span></button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- ══════════ ADD / EDIT DRAWER ══════════ -->
  <div v-if="selectedName" class="bomx-overlay" @click.self="goBackToList">
    <div class="bomx-drawer">
      <div v-if="detailLoading" class="bomx-empty-state"><div class="shimmer" style="height:220px;border-radius:var(--bx-radius)"></div></div>

      <template v-else>
        <div class="bomx-drawer-hdr">
          <div style="min-width:0">
            <div class="bomx-drawer-title">{{ isNew ? 'New Workstation' : (doc.workstation_name || doc.name) }}</div>
            <div class="bomx-drawer-sub">Configure type, capacity, and costs</div>
          </div>
          <button class="bomx-drawer-close" @click="goBackToList" title="Close"><span v-html="icon('x',16)"></span></button>
        </div>

        <div class="bomx-drawer-tabs">
          <button type="button" class="bomx-drawer-tab" :class="{active: formTab==='details'}" @click="formTab='details'">Details</button>
          <button type="button" class="bomx-drawer-tab" :class="{active: formTab==='capacity'}" @click="formTab='capacity'">Capacity &amp; Costs</button>
        </div>

        <div class="bomx-drawer-body">
          <!-- ── Details tab ── -->
          <template v-if="formTab==='details'">
            <div class="bomx-hf-label">Workstation Name <span style="color:var(--bx-red)">*</span></div>
            <input class="bomx-fi" type="text" v-model="doc.workstation_name" :disabled="!isNew" placeholder="e.g., Assembly Station 1" style="width:100%;margin-bottom:4px"/>
            <div class="bomx-field-hint" v-if="!isNew" style="margin-bottom:16px">Name cannot be changed after creation.</div>
            <div v-else style="margin-bottom:16px"></div>

            <div class="bomx-drawer-grid-2">
              <div>
                <div class="bomx-hf-label">Workstation Type <span style="color:var(--bx-red)">*</span></div>
                <select class="bomx-fi" v-model="doc.workstation_type" style="width:100%">
                  <option value="">— Select Workstation Type —</option>
                  <option v-for="t in types" :key="t.name" :value="t.name">{{ t.name }}</option>
                </select>
              </div>
              <div>
                <div class="bomx-hf-label">Warehouse</div>
                <select class="bomx-fi" v-model="doc.warehouse" style="width:100%">
                  <option value="">— Select Warehouse —</option>
                  <option v-for="w in warehouses" :key="w.name" :value="w.name">{{ w.warehouse_name || w.name }}</option>
                </select>
              </div>
            </div>

            <div class="bomx-hf-label" style="margin-top:16px">Description</div>
            <textarea class="bomx-fi" v-model="doc.description" style="width:100%;min-height:100px;resize:vertical" placeholder="Machine specs, location, or any notes…"></textarea>

            <div class="bomx-drawer-toggle-card" style="margin-top:16px">
              <div>
                <div class="bomx-drawer-toggle-title">Is Active</div>
                <div class="bomx-drawer-toggle-sub">Available for scheduling and job cards</div>
              </div>
              <label class="bomx-switch">
                <input type="checkbox" v-model="doc.is_active" :true-value="1" :false-value="0"/>
                <span class="bomx-switch-track"><span class="bomx-switch-thumb"></span></span>
              </label>
            </div>
          </template>

          <!-- ── Capacity & Costs tab ── -->
          <template v-else>
            <div class="bomx-drawer-grid-2">
              <div>
                <div class="bomx-hf-label">Job Capacity</div>
                <input class="bomx-fi" type="number" v-model.number="doc.capacity" min="1" step="any" style="width:100%"/>
                <div class="bomx-field-hint">Run parallel job cards.</div>
              </div>
              <div>
                <div class="bomx-hf-label">Working Hours Per Day</div>
                <input class="bomx-fi" type="number" v-model.number="doc.working_hours_per_day" min="0" max="24" step="any" style="width:100%"/>
                <div class="bomx-field-hint">Availability for production planning.</div>
              </div>
            </div>

            <div style="margin-top:16px">
              <div class="bomx-hf-label">Hourly Operating Cost <span style="color:var(--bx-red)">*</span></div>
              <div style="position:relative">
                <span style="position:absolute;left:9px;top:8px;color:var(--bx-muted);font-weight:600;font-size:13px">₹</span>
                <input class="bomx-fi" type="number" v-model.number="doc.hour_rate" min="0" step="any" style="width:100%;padding-left:24px"/>
              </div>
              <div class="bomx-field-hint">Used for calculating manufacturing costs.</div>
            </div>
          </template>
        </div>

        <div class="bomx-drawer-footer">
          <button v-if="!isNew" class="bomx-btn bomx-btn-ghost" @click="deleteFromDetail">Delete Workstation</button>
          <div style="flex:1"></div>
          <button class="bomx-btn bomx-btn-outline" @click="goBackToList">Cancel</button>
          <button class="bomx-btn bomx-btn-mfg" @click="save" :disabled="saving || detailLoading">
            <span v-html="icon('save',13)"></span> {{ saving ? 'Saving…' : (isNew ? 'Save Workstation' : 'Save Changes') }}
          </button>
        </div>
      </template>
    </div>
  </div>

</div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useToast } from "../composables/useToast.js";
import { useConfirm } from "../composables/useConfirm.js";
import { apiGet, apiList, apiSave, apiDelete } from "../api/client.js";

const route = useRoute();
const router = useRouter();
const { toast } = useToast();
const { confirm } = useConfirm();

// ── LIST STATE ──────────────────────────────────────────────
const loading = ref(false);
const list = ref([]);
const search = ref("");
const filterStatus = ref("");
const filterType = ref("");
const viewMode = ref("grid"); // 'grid' | 'list'

const selectedName = computed(() => (route.params.name && route.params.name !== "new") ? route.params.name : (route.params.name === "new" ? "new" : null));

async function loadList() {
  loading.value = true;
  try {
    const fields = ["name", "workstation_name", "workstation_type", "warehouse", "capacity", "hour_rate", "is_active", "modified"];
    const r = await apiList("Workstation", { fields, limit: 1000, order: "modified desc" });
    list.value = r || [];
  } catch (e) {
    toast("Could not load Workstations", "error");
  }
  loading.value = false;
}

const sorted = computed(() => {
  let r = list.value;
  if (filterStatus.value === "active") r = r.filter(i => i.is_active);
  if (filterStatus.value === "inactive") r = r.filter(i => !i.is_active);
  if (filterType.value) r = r.filter(i => i.workstation_type === filterType.value);
  const q = search.value.toLowerCase().trim();
  if (q) r = r.filter(i => [i.name, i.workstation_name, i.workstation_type, i.warehouse].filter(Boolean).join(" ").toLowerCase().includes(q));
  return r;
});

const activeCount = computed(() => list.value.filter(i => i.is_active).length);
const inactiveCount = computed(() => list.value.filter(i => !i.is_active).length);
const avgHourRate = computed(() => {
  if (!list.value.length) return 0;
  const total = list.value.reduce((s, i) => s + (Number(i.hour_rate) || 0), 0);
  return total / list.value.length;
});

function statusLabel(row) {
  return row.is_active ? "Active" : "Inactive";
}
function statusClass(row) {
  return row.is_active ? "badge-active" : "badge-obsolete";
}

function typeIcon(type) {
  const t = (type || "").toLowerCase();
  if (t.includes("machine")) return "⚙️";
  if (t.includes("labour") || t.includes("labor")) return "🧑‍🏭";
  if (t.includes("assembly")) return "🧩";
  if (t.includes("quality")) return "✅";
  if (t.includes("paint") || t.includes("coat")) return "🎨";
  if (t.includes("pack")) return "📦";
  return "🏭";
}

function fmtCurrency(val) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val || 0);
}

function selectWorkstation(name) {
  router.push(`/manufacturing/workstation/${name}`);
}
function openAdd() {
  formTab.value = "details";
  router.push("/manufacturing/workstation/new");
}
function goBackToList() {
  router.push("/manufacturing/workstation");
}

async function isWorkstationDeletable(row) {
  try {
    const [inOp, inWoOp, inBomOp, inJobCard] = await Promise.all([
      apiList("Operation", { fields: ["name"], filters: [["default_workstation", "=", row.name]], limit: 1 }),
      apiList("Work Order Operation", { fields: ["parent"], filters: [["workstation", "=", row.name]], limit: 1 }),
      apiList("BOM Operation", { fields: ["parent"], filters: [["workstation", "=", row.name]], limit: 1 }),
      apiList("Job Card", { fields: ["name"], filters: [["workstation", "=", row.name]], limit: 1 }),
    ]);
    if (inOp && inOp.length) {
      toast(`${row.name} is used as the default workstation on Operation ${inOp[0].name} and cannot be deleted.`, "error");
      return false;
    }
    if (inWoOp && inWoOp.length) {
      toast(`${row.name} is used by Work Order ${inWoOp[0].parent} and cannot be deleted.`, "error");
      return false;
    }
    if (inBomOp && inBomOp.length) {
      toast(`${row.name} is used by BOM ${inBomOp[0].parent} and cannot be deleted.`, "error");
      return false;
    }
    if (inJobCard && inJobCard.length) {
      toast(`${row.name} is referenced by Job Card ${inJobCard[0].name} and cannot be deleted.`, "error");
      return false;
    }
  } catch (e) {
    toast(`Could not verify whether ${row.name} is in use — try again.`, "error");
    return false;
  }
  return true;
}

async function quickDelete(row) {
  if (!(await isWorkstationDeletable(row))) return;
  if (await confirm({ title: "Delete Workstation?", body: `Are you sure you want to delete ${row.name}?`, okLabel: "Delete", okStyle: "danger" })) {
    try {
      await apiDelete("Workstation", row.name);
      toast("Workstation deleted");
      loadList();
    } catch (e) {
      toast("Could not delete Workstation: " + e.message, "error");
    }
  }
}

async function deleteFromDetail() {
  const row = { name: doc.value.name };
  if (!(await isWorkstationDeletable(row))) return;
  if (await confirm({ title: "Delete Workstation?", body: `Are you sure you want to delete ${row.name}?`, okLabel: "Delete", okStyle: "danger" })) {
    try {
      await apiDelete("Workstation", row.name);
      toast("Workstation deleted");
      goBackToList();
      loadList();
    } catch (e) {
      toast("Could not delete Workstation: " + e.message, "error");
    }
  }
}

// ── DETAIL / DRAWER STATE ─────────────────────────────────────
const isNew = computed(() => route.params.name === "new");
const detailLoading = ref(false);
const saving = ref(false);
const formTab = ref("details"); // 'details' | 'capacity'

function emptyDoc() {
  return {
    doctype: "Workstation",
    workstation_name: "",
    workstation_type: "",
    warehouse: "",
    capacity: 1,
    working_hours_per_day: 8,
    hour_rate: 0,
    description: "",
    is_active: 1,
  };
}
const doc = ref(emptyDoc());

const types = ref([]);
const warehouses = ref([]);

async function loadDropdowns() {
  try {
    types.value = await apiList("Workstation Type", { fields: ["name", "is_active"], filters: [["is_active", "=", 1]], limit: 1000 }) || [];
    warehouses.value = await apiList("Warehouse", { fields: ["name", "warehouse_name"], limit: 1000 }) || [];
  } catch (e) {
    toast("Could not load Workstation Types / Warehouses — some dropdowns may be empty", "error");
  }
}

onMounted(async () => {
  loading.value = true;
  await loadList();
  await loadDropdowns();
  if (route.params.name) await loadDoc();
  loading.value = false;
});

watch(() => route.params.name, async (name) => {
  formTab.value = "details";
  if (!name) { doc.value = emptyDoc(); return; }
  await loadDoc();
});

async function loadDoc() {
  if (isNew.value) {
    doc.value = emptyDoc();
    return;
  }
  detailLoading.value = true;
  try {
    const r = await apiGet("Workstation", route.params.name);
    doc.value = r;
    if (r.workstation_type && !types.value.some(t => t.name === r.workstation_type)) {
      types.value = [{ name: r.workstation_type }, ...types.value];
    }
  } catch (e) {
    toast("Could not load Workstation", "error");
    goBackToList();
  }
  detailLoading.value = false;
}

async function save() {
  if (!doc.value.workstation_name) {
    toast("Workstation Name is mandatory", "error");
    formTab.value = "details";
    return;
  }
  if (!doc.value.workstation_type) {
    toast("Workstation Type is mandatory", "error");
    formTab.value = "details";
    return;
  }
  saving.value = true;
  try {
    const r = await apiSave(doc.value);
    toast(isNew.value ? "Workstation created successfully" : "Saved successfully");
    if (isNew.value) {
      router.replace(`/manufacturing/workstation/${r.name}`);
    } else {
      doc.value = r;
    }
    loadList();
  } catch (e) {
    toast(e.message || "Could not save", "error");
  }
  saving.value = false;
}

// ── UTIL ─────────────────────────────────────────────────────
const ICONS = {
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
  grid: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>',
  list: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>',
  edit: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>',
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>',
  x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>',
  save: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path><polyline points="17 21 17 13 7 13"></polyline><polyline points="7 3 7 8 15 8"></polyline></svg>',
};
function icon(name, size) {
  return (ICONS[name] || "").replace("<svg ", `<svg width="${size}" height="${size}" `);
}
</script>

<style scoped>
.bomx-page {
  --bx-bg:#F3F4F6; --bx-surface:#FFFFFF; --bx-surf2:#F8F9FC; --bx-border:#E2E8F0;
  --bx-text:#1A1D23; --bx-muted:#868E96;
  --bx-green:#2F9E44; --bx-greenS:#EBFBEE;
  --bx-red:#C92A2A; --bx-redS:#FFF5F5;
  --bx-amber:#E67700; --bx-amberS:#FFF3BF;
  --bx-blue:#1971C2; --bx-blueS:#E7F5FF;
  --bx-violet:#7048E8; --bx-violetS:#F3F0FF;
  --bx-mfg:#1a6ef7; --bx-mfgL:#2f74f5; --bx-mfgS:#EAF1FF; --bx-mfgB:#1e3a5f;
  --bx-radius:10px; --bx-rsm:6px;
  padding: 16px;
}
.mono { font-family: 'SFMono-Regular', Consolas, monospace; }

/* ── Stat cards ── */
.bomx-stats-row { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:16px; }
@media (max-width:900px) { .bomx-stats-row { grid-template-columns:repeat(2,1fr); } }
@media (max-width:520px) { .bomx-stats-row { grid-template-columns:1fr; } }
.bomx-stat-card { background:var(--bx-surface); border:1px solid var(--bx-border); border-left:4px solid var(--bx-mfg); border-radius:var(--bx-radius); padding:16px 18px; }
.bomx-stat-label { font-size:11px; font-weight:700; letter-spacing:.05em; text-transform:uppercase; margin-bottom:8px; }
.bomx-stat-value { font-size:26px; font-weight:800; color:var(--bx-text); line-height:1.1; }
.bomx-stat-sub { font-size:12px; color:var(--bx-muted); margin-top:4px; }

/* ── Toolbar ── */
.bomx-toolbar { display:flex; align-items:center; gap:10px; flex-wrap:wrap; background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); padding:12px 14px; margin-bottom:16px; }
.bomx-search-wrap { position:relative; flex:1 1 220px; min-width:180px; }
.bomx-search-icon { position:absolute; left:10px; top:50%; transform:translateY(-50%); color:var(--bx-muted); display:flex; }
.bomx-search-input { width:100%; border:1px solid #CDD5E0; border-radius:var(--bx-rsm); padding:8px 10px 8px 32px; font-size:13px; color:var(--bx-text); outline:none; }
.bomx-search-input:focus { border-color:var(--bx-mfg); box-shadow:0 0 0 3px rgba(26,110,247,.1); }
.bomx-toolbar-count { font-size:12.5px; color:var(--bx-muted); white-space:nowrap; }
.bomx-view-toggle { display:flex; border:1px solid var(--bx-border); border-radius:var(--bx-rsm); overflow:hidden; }
.bomx-view-toggle button { display:flex; align-items:center; justify-content:center; width:32px; height:32px; background:#fff; border:none; color:var(--bx-muted); cursor:pointer; border-right:1px solid var(--bx-border); }
.bomx-view-toggle button:last-child { border-right:none; }
.bomx-view-toggle button.active { background:var(--bx-mfgS); color:var(--bx-mfg); }
.bomx-view-toggle button:hover:not(.active) { background:var(--bx-surf2); }

/* ── Grid view ── */
.bomx-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(280px, 1fr)); gap:14px; }
.bomx-ws-card { background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); padding:16px; cursor:pointer; transition:box-shadow .15s, border-color .15s; display:flex; flex-direction:column; gap:12px; }
.bomx-ws-card:hover { border-color:var(--bx-mfg); box-shadow:0 2px 10px rgba(16,24,40,.06); }
.bomx-ws-card-hdr { display:flex; align-items:flex-start; gap:10px; }
.bomx-ws-icon { width:40px; height:40px; border-radius:9px; background:var(--bx-mfgS); display:flex; align-items:center; justify-content:center; font-size:18px; flex-shrink:0; }
.bomx-ws-title { font-size:14.5px; font-weight:700; color:var(--bx-text); line-height:1.3; }
.bomx-ws-code { font-size:11.5px; color:var(--bx-muted); margin-top:2px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.bomx-ws-badges { display:flex; gap:6px; flex-wrap:wrap; }
.bomx-ws-stats { display:grid; grid-template-columns:1fr 1fr; gap:10px; padding-top:12px; border-top:1px solid #F1F3F5; }
.bomx-ws-stat-lbl { font-size:10px; font-weight:700; letter-spacing:.04em; text-transform:uppercase; color:var(--bx-muted); margin-bottom:2px; }
.bomx-ws-stat-val { font-size:15px; font-weight:700; color:var(--bx-text); }
.bomx-ws-footer { display:flex; align-items:center; justify-content:space-between; gap:8px; padding-top:12px; border-top:1px solid #F1F3F5; }
.bomx-ws-loc { font-size:12px; color:var(--bx-muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }

/* ── List / table view ── */
.bomx-table-wrap { background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:auto; }
.bomx-table { width:100%; border-collapse:collapse; font-size:13px; }
.bomx-table thead th { text-align:left; font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); background:var(--bx-surf2); padding:10px 14px; border-bottom:1px solid var(--bx-border); white-space:nowrap; }
.bomx-table tbody td { padding:11px 14px; border-bottom:1px solid #F1F3F5; color:var(--bx-text); white-space:nowrap; }
.bomx-table tbody tr { cursor:pointer; transition:background .12s; }
.bomx-table tbody tr:hover { background:#FAFBFF; }
.bomx-table tbody tr:last-child td { border-bottom:none; }

/* ── Empty state ── */
.bomx-empty-state { text-align:center; padding:60px 20px; color:var(--bx-muted); background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); }
.bomx-empty-icon { font-size:48px; margin-bottom:14px; }
.bomx-empty-title { font-size:16px; font-weight:700; color:var(--bx-text); margin-bottom:6px; }
.bomx-empty-sub { font-size:13px; line-height:1.6; max-width:320px; margin:0 auto 20px; }

/* ── Badges ── */
.bomx-badge { display:inline-flex; align-items:center; padding:2px 8px; border-radius:20px; font-size:11px; font-weight:600; white-space:nowrap; }
.badge-active { background:var(--bx-greenS); color:var(--bx-green); }
.badge-obsolete { background:#F1F3F5; color:var(--bx-muted); }

/* ── Buttons ── */
.bomx-btn { display:inline-flex; align-items:center; gap:6px; padding:8px 16px; border-radius:var(--bx-rsm); font-size:13px; font-weight:600; cursor:pointer; border:1px solid transparent; line-height:1; white-space:nowrap; }
.bomx-btn:disabled { opacity:.6; cursor:not-allowed; }
.bomx-btn-mfg { background:var(--bx-mfg); color:#fff; }
.bomx-btn-mfg:hover:not(:disabled) { background:var(--bx-mfgB); }
.bomx-btn-outline { background:#fff; color:var(--bx-text); border-color:var(--bx-border); }
.bomx-btn-outline:hover:not(:disabled) { background:var(--bx-surf2); }
.bomx-btn-ghost { background:none; color:var(--bx-red); border-color:rgba(201,42,42,.3); }
.bomx-btn-ghost:hover:not(:disabled) { background:var(--bx-redS); }
.bomx-btn-icon { background:none; border:1px solid var(--bx-border); border-radius:6px; cursor:pointer; padding:5px 7px; display:inline-flex; color:var(--bx-muted); }
.bomx-btn-icon:hover { border-color:var(--bx-mfg); color:var(--bx-mfg); background:var(--bx-mfgS); }
.bomx-btn-icon.danger:hover { color:var(--bx-red); background:var(--bx-redS); border-color:var(--bx-red); }

/* ── Inputs ── */
.bomx-fi { border:1px solid #CDD5E0; border-radius:var(--bx-rsm); padding:7px 9px; font-size:13px; color:var(--bx-text); background:#fff; outline:none; }
.bomx-fi:focus { border-color:var(--bx-mfg); box-shadow:0 0 0 3px rgba(26,110,247,.1); }
.bomx-fi:disabled { background:#F8F9FC; color:var(--bx-muted); }
select.bomx-fi {
  appearance: none; -webkit-appearance:none; -moz-appearance:none;
  padding-right: 30px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%239ca3af' stroke-width='2.5'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat:no-repeat; background-position:right 10px center;
}
select.bomx-fi:disabled { background-image: none; padding-right: 9px; }
.bomx-hf-label { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); margin-bottom:6px; }
.bomx-field-hint { font-size:12px; color:var(--bx-muted); margin-top:5px; }

/* ── Drawer ── */
.bomx-overlay { position:fixed; inset:0; background:rgba(17,24,39,.5); display:flex; justify-content:flex-end; z-index:1000; }
.bomx-drawer { width:560px; max-width:94vw; height:100%; background:#fff; box-shadow:-8px 0 30px rgba(0,0,0,.15); display:flex; flex-direction:column; animation: bx-slide-in .18s ease-out; }
@keyframes bx-slide-in { from { transform:translateX(24px); opacity:0; } to { transform:translateX(0); opacity:1; } }
.bomx-drawer-hdr { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; padding:20px 22px; background:linear-gradient(135deg, var(--bx-mfgB), var(--bx-mfg)); color:#fff; }
.bomx-drawer-title { font-size:18px; font-weight:700; }
.bomx-drawer-sub { font-size:12.5px; color:rgba(255,255,255,.8); margin-top:3px; }
.bomx-drawer-close { background:rgba(255,255,255,.15); border:1px solid rgba(255,255,255,.3); color:#fff; border-radius:7px; width:32px; height:32px; display:flex; align-items:center; justify-content:center; cursor:pointer; flex-shrink:0; }
.bomx-drawer-close:hover { background:rgba(255,255,255,.25); }
.bomx-drawer-tabs { display:flex; gap:4px; padding:0 22px; border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); }
.bomx-drawer-tab { padding:12px 6px; margin-right:18px; background:none; border:none; border-bottom:2px solid transparent; font-size:13px; font-weight:600; color:var(--bx-muted); cursor:pointer; }
.bomx-drawer-tab.active { color:var(--bx-mfg); border-bottom-color:var(--bx-mfg); }
.bomx-drawer-tab:hover:not(.active) { color:var(--bx-text); }
.bomx-drawer-body { padding:20px 22px; overflow-y:auto; flex:1; }
.bomx-drawer-grid-2 { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
@media (max-width:480px) { .bomx-drawer-grid-2 { grid-template-columns:1fr; } }
.bomx-drawer-toggle-card { display:flex; align-items:center; justify-content:space-between; gap:12px; background:var(--bx-mfgS); border-radius:var(--bx-rsm); padding:12px 14px; }
.bomx-drawer-toggle-title { font-size:13px; font-weight:600; color:var(--bx-text); }
.bomx-drawer-toggle-sub { font-size:11.5px; color:var(--bx-muted); margin-top:2px; }
.bomx-drawer-footer { display:flex; align-items:center; gap:10px; padding:14px 22px; border-top:1px solid var(--bx-border); background:var(--bx-surf2); }

/* ── Toggle switch ── */
.bomx-switch { position:relative; display:inline-block; flex-shrink:0; }
.bomx-switch input { opacity:0; width:0; height:0; position:absolute; }
.bomx-switch-track { display:block; width:38px; height:22px; background:#CDD5E0; border-radius:999px; transition:background .15s; cursor:pointer; }
.bomx-switch-thumb { display:block; width:16px; height:16px; background:#fff; border-radius:50%; margin:3px; transition:transform .15s; box-shadow:0 1px 2px rgba(0,0,0,.2); }
.bomx-switch input:checked + .bomx-switch-track { background:var(--bx-mfg); }
.bomx-switch input:checked + .bomx-switch-track .bomx-switch-thumb { transform:translateX(16px); }

.shimmer { background:linear-gradient(90deg,#f1f3f5 25%,#e9ecef 37%,#f1f3f5 63%); background-size:400% 100%; animation:shimmer 1.4s ease infinite; }
@keyframes shimmer { 0%{background-position:100% 50%} 100%{background-position:0 50%} }
</style>