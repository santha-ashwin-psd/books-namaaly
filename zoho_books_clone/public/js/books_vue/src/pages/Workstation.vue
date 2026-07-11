<template>
<div class="bomx-page">
  <div class="bomx-two-col">

    <!-- ══════════ LEFT: WORKSTATION LIST ══════════ -->
    <div class="bomx-list-panel">
      <div class="bomx-panel-hdr">
        <span class="bomx-panel-title">⚙️ All Workstations <span class="bomx-count">({{ sorted.length }})</span></span>
        <button class="bomx-btn bomx-btn-mfg bomx-btn-sm" @click="openAdd"><span v-html="icon('plus',12)"></span> New</button>
      </div>
      <select class="bomx-fi bomx-status-filter" v-model="filterStatus">
        <option value="">All Status</option>
        <option value="active">Active</option>
        <option value="inactive">Inactive</option>
      </select>
      <input class="bomx-search" v-model="search" type="text" placeholder="Search Workstations…"/>
      <div class="bomx-list">
        <template v-if="loading">
          <div v-for="n in 5" :key="n" class="bomx-item"><div class="shimmer" style="height:38px;border-radius:6px"></div></div>
        </template>
        <div v-else-if="!sorted.length" class="bomx-list-empty">No Workstations found</div>
        <div v-else v-for="row in sorted" :key="row.name"
             class="bomx-item" :class="{active: selectedName === row.name}"
             @click="selectWorkstation(row.name)">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px">
            <div class="bomx-item-name">{{ row.name }}</div>
            <span class="bomx-badge" :class="statusClass(row)">{{ statusLabel(row) }}</span>
          </div>
          <div class="bomx-item-meta">
            <span v-if="row.workstation_type">{{ row.workstation_type }}</span>
            <span v-if="row.workstation_type">•</span>
            <span>{{ fmtCurrency(row.hour_rate) }}/hr</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ══════════ RIGHT: WORKSTATION DETAIL ══════════ -->
    <div class="bomx-detail-panel">

      <!-- Empty state -->
      <div v-if="!selectedName" class="bomx-empty-state">
        <div class="bomx-empty-icon">⚙️</div>
        <div class="bomx-empty-title">Select a Workstation</div>
        <div class="bomx-empty-sub">Choose a Workstation from the list to view or edit its details.</div>
        <button class="bomx-btn bomx-btn-mfg" @click="openAdd"><span v-html="icon('plus',13)"></span> Create First Workstation</button>
      </div>

      <template v-else>
        <div v-if="detailLoading" class="bomx-empty-state"><div class="shimmer" style="height:200px;border-radius:10px"></div></div>

        <template v-else>
          <!-- Header -->
          <div class="bomx-detail-hdr">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px">
              <div style="min-width:0">
                <div class="bomx-detail-title">{{ isNew ? 'New Workstation' : (doc.workstation_name || doc.name) }}</div>
                <div class="bomx-detail-meta">
                  <span class="mono" v-if="!isNew">{{ doc.name }}</span>
                  <span v-if="!isNew">•</span>
                  <span class="bomx-badge" :class="statusClass(doc)" style="font-size:11px">{{ statusLabel(doc) }}</span>
                </div>
              </div>
              <div style="display:flex;gap:6px;flex-shrink:0;flex-wrap:wrap;justify-content:flex-end">
                <button class="bomx-btn bomx-btn-ghost-inv" @click="goBackToList">Back</button>
                <button class="bomx-btn bomx-btn-light" @click="save" :disabled="saving || detailLoading">
                  {{ saving ? 'Saving…' : (isNew ? 'Save Workstation' : 'Save Changes') }}
                </button>
              </div>
            </div>
          </div>

          <!-- Header fields -->
          <div class="bomx-hdr-fields" style="grid-template-columns:2fr 1fr">
            <div>
              <div class="bomx-hf-label">Workstation Name <span style="color:var(--bx-red)">*</span></div>
              <input class="bomx-fi" type="text" v-model="doc.workstation_name" :disabled="!isNew" placeholder="e.g., Assembly Station 1" style="width:100%"/>
              <div class="bomx-field-hint" v-if="!isNew">Name cannot be changed after creation.</div>
            </div>
            <div>
              <div class="bomx-hf-label">Job Capacity</div>
              <input class="bomx-fi" type="number" v-model.number="doc.capacity" min="1" step="any" style="width:100%"/>
              <div class="bomx-field-hint">Run parallel job cards.</div>
            </div>
          </div>

          <div class="bomx-hdr-fields" style="grid-template-columns:1fr 1fr">
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

          <div class="bomx-toggle-row">
            <label class="bomx-toggle"><input type="checkbox" v-model="doc.is_active" :true-value="1" :false-value="0"/> Is Active</label>
          </div>

          <div class="bomx-body">
            <div class="bomx-section-lbl">Operating Costs</div>
            <div class="bomx-hdr-fields" style="grid-template-columns:1fr 1fr;padding:0;border:none;background:none;margin-bottom:20px">
              <div>
                <div class="bomx-hf-label">Hourly Operating Cost <span style="color:var(--bx-red)">*</span></div>
                <div style="position:relative">
                  <span style="position:absolute;left:9px;top:8px;color:var(--bx-muted);font-weight:600;font-size:13px">₹</span>
                  <input class="bomx-fi" type="number" v-model.number="doc.hour_rate" min="0" step="any" style="width:100%;padding-left:24px"/>
                </div>
                <div class="bomx-field-hint">Used for calculating manufacturing costs.</div>
              </div>
              <div>
                <div class="bomx-hf-label">Working Hours Per Day</div>
                <input class="bomx-fi" type="number" v-model.number="doc.working_hours_per_day" min="0" max="24" step="any" style="width:100%"/>
                <div class="bomx-field-hint">Availability for production planning.</div>
              </div>
            </div>

            <div class="bomx-section-lbl">Description</div>
            <textarea class="bomx-fi" v-model="doc.description" style="width:100%;min-height:110px;resize:vertical" placeholder="Description of the workstation…"></textarea>
          </div>

          <!-- Footer -->
          <div class="bomx-footer">
            <button v-if="!isNew" class="bomx-btn bomx-btn-ghost-inv" style="color:var(--bx-red);border-color:rgba(201,42,42,.3)" @click="deleteFromDetail">Delete Workstation</button>
            <div style="flex:1"></div>
            <button class="bomx-btn bomx-btn-mfg" @click="save" :disabled="saving || detailLoading">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13"/><polyline points="7 3 7 8 15 8"/></svg>
              {{ saving ? 'Saving…' : (isNew ? 'Save Workstation' : 'Save Changes') }}
            </button>
          </div>
        </template>
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

const selectedName = computed(() => (route.params.name && route.params.name !== "new") ? route.params.name : (route.params.name === "new" ? "new" : null));

async function loadList() {
  loading.value = true;
  try {
    const fields = ["name", "workstation_type", "hour_rate", "is_active", "modified"];
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
  const q = search.value.toLowerCase().trim();
  if (q) r = r.filter(i => [i.name, i.workstation_type].filter(Boolean).join(" ").toLowerCase().includes(q));
  return r;
});

function statusLabel(row) {
  return row.is_active ? "Active" : "Inactive";
}
function statusClass(row) {
  return row.is_active ? "badge-active" : "badge-obsolete";
}

function fmtCurrency(val) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val || 0);
}

function selectWorkstation(name) {
  router.push(`/manufacturing/workstation/${name}`);
}
function openAdd() {
  router.push("/manufacturing/workstation/new");
}
function goBackToList() {
  router.push("/manufacturing/workstation");
}

async function isWorkstationDeletable(row) {
  try {
    const [inOp, inWoOp, inBomOp] = await Promise.all([
      apiList("Operation", { fields: ["name"], filters: [["default_workstation", "=", row.name]], limit: 1 }),
      apiList("Work Order Operation", { fields: ["parent"], filters: [["workstation", "=", row.name]], limit: 1 }),
      apiList("BOM Operation", { fields: ["parent"], filters: [["workstation", "=", row.name]], limit: 1 }),
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
  } catch (e) {
    toast(`Could not verify whether ${row.name} is in use — try again.`, "error");
    return false;
  }
  return true;
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

// ── DETAIL STATE ─────────────────────────────────────────────
const isNew = computed(() => route.params.name === "new");
const detailLoading = ref(false);
const saving = ref(false);

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
    // Keep an already-set-but-now-inactive workstation type selectable, so
    // the saved value doesn't silently vanish from the dropdown.
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
    return;
  }
  if (!doc.value.workstation_type) {
    toast("Workstation Type is mandatory", "error");
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
.bomx-two-col { display:grid; grid-template-columns: 340px 1fr; gap:16px; align-items:start; }
@media (max-width:1000px) { .bomx-two-col { grid-template-columns: 1fr; } }

.mono { font-family: "DM Mono", ui-monospace, monospace; }

/* ── List panel ── */
.bomx-list-panel { background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; display:flex; flex-direction:column; }
.bomx-panel-hdr { padding:12px 14px; border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); display:flex; align-items:center; justify-content:space-between; gap:8px; }
.bomx-panel-title { font-size:13px; font-weight:700; color:var(--bx-text); }
.bomx-count { font-size:12px; font-weight:400; color:var(--bx-muted); }
.bomx-status-filter { margin:8px 12px 0; width:calc(100% - 24px); font-size:12px; padding:6px 10px; }
.bomx-search { width:100%; border:none; outline:none; font-size:13px; padding:10px 14px; margin-top:8px; border-bottom:1px solid var(--bx-border); background:#fff; color:var(--bx-text); }
.bomx-search::placeholder { color:var(--bx-muted); }
.bomx-list { overflow-y:auto; max-height: calc(100vh - 230px); }
.bomx-list-empty { text-align:center; padding:32px; color:var(--bx-muted); font-size:13px; }
.bomx-item { padding:12px 14px; border-bottom:1px solid #F1F3F5; cursor:pointer; transition:background .12s; display:flex; flex-direction:column; gap:4px; }
.bomx-item:hover { background:#FAFBFF; }
.bomx-item.active { background:var(--bx-mfgS); border-left:3px solid var(--bx-mfg); }
.bomx-item-name { font-size:13.5px; font-weight:600; color:var(--bx-text); }
.bomx-item-meta { display:flex; align-items:center; gap:6px; font-size:12px; color:var(--bx-muted); }

/* ── Badges ── */
.bomx-badge { display:inline-flex; align-items:center; padding:2px 8px; border-radius:20px; font-size:11px; font-weight:600; white-space:nowrap; }
.badge-active { background:var(--bx-greenS); color:var(--bx-green); }
.badge-obsolete { background:#F1F3F5; color:var(--bx-muted); }

/* ── Detail panel ── */
.bomx-detail-panel { background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; display:flex; flex-direction:column; min-height: calc(100vh - 100px); }
.bomx-empty-state { text-align:center; padding:60px 20px; color:var(--bx-muted); }
.bomx-empty-icon { font-size:48px; margin-bottom:14px; }
.bomx-empty-title { font-size:16px; font-weight:700; color:var(--bx-text); margin-bottom:6px; }
.bomx-empty-sub { font-size:13px; line-height:1.6; max-width:280px; margin:0 auto 20px; }

.bomx-detail-hdr { padding:18px 22px; background:linear-gradient(135deg, var(--bx-mfgB), var(--bx-mfg)); }
.bomx-detail-title { font-size:18px; font-weight:700; color:#fff; margin-bottom:4px; }
.bomx-detail-meta { font-size:12.5px; color:rgba(255,255,255,.75); display:flex; align-items:center; gap:8px; flex-wrap:wrap; }

.bomx-hdr-fields { display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; padding:16px 22px; border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); }
.bomx-hf-label { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); margin-bottom:4px; }
.bomx-field-hint { font-size:12px; color:var(--bx-muted); margin-top:5px; }
.bomx-toggle-row { display:flex; gap:20px; padding:10px 22px 14px; flex-wrap:wrap; background:var(--bx-surf2); border-bottom:1px solid var(--bx-border); }
.bomx-toggle { display:flex; align-items:center; gap:6px; font-size:12.5px; font-weight:600; color:var(--bx-text); }

.bomx-body { padding:20px 22px; overflow-y:auto; flex:1; }
.bomx-section-lbl { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--bx-muted); margin-bottom:8px; }

.bomx-footer { padding:12px 22px; border-top:1px solid var(--bx-border); background:var(--bx-surf2); display:flex; justify-content:space-between; align-items:center; gap:8px; }

/* ── Buttons / inputs ── */
.bomx-fi { border:1px solid #CDD5E0; border-radius:var(--bx-rsm); padding:7px 9px; font-size:13px; color:var(--bx-text); background:#fff; outline:none; }
.bomx-fi:focus { border-color:var(--bx-mfg); box-shadow:0 0 0 3px rgba(180,83,9,.1); }
.bomx-fi:disabled { background:#F8F9FC; color:var(--bx-muted); }
select.bomx-fi {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  padding-right: 30px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%239ca3af' stroke-width='2.5'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
}
select.bomx-fi:disabled { background-image: none; padding-right: 9px; }
.bomx-btn { display:inline-flex; align-items:center; gap:6px; padding:8px 16px; border-radius:var(--bx-rsm); font-size:13px; font-weight:600; cursor:pointer; border:1px solid transparent; line-height:1; white-space:nowrap; }
.bomx-btn:disabled { opacity:.6; cursor:not-allowed; }
.bomx-btn-sm { padding:6px 10px; font-size:12px; }
.bomx-btn-mfg { background:var(--bx-mfg); color:#fff; }
.bomx-btn-mfg:hover:not(:disabled) { background:var(--bx-mfgB); }
.bomx-btn-light { background:rgba(255,255,255,.92); color:var(--bx-mfgB); }
.bomx-btn-light:hover:not(:disabled) { background:#fff; }
.bomx-btn-ghost-inv { background:rgba(255,255,255,.15); color:#fff; border-color:rgba(255,255,255,.3); }
.bomx-btn-ghost-inv:hover:not(:disabled) { background:rgba(255,255,255,.25); }

.shimmer { background:linear-gradient(90deg,#f1f3f5 25%,#e9ecef 37%,#f1f3f5 63%); background-size:400% 100%; animation:shimmer 1.4s ease infinite; }
@keyframes shimmer { 0%{background-position:100% 50%} 100%{background-position:0 50%} }
</style>