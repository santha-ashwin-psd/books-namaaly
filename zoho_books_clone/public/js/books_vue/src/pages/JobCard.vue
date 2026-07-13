<template>
<div class="bomx-page">
  <div class="bomx-two-col">

    <!-- ══════════ LEFT: JOB CARD LIST ══════════ -->
    <div class="bomx-list-panel">
      <div class="bomx-panel-hdr">
        <span class="bomx-panel-title">🗂️ All Job Cards <span class="bomx-count">({{ sorted.length }})</span></span>
        <button class="bomx-btn bomx-btn-mfg bomx-btn-sm" @click="openAdd"><span v-html="icon('plus',12)"></span> New</button>
      </div>
      <select class="bomx-fi bomx-status-filter" v-model="filterStatus">
        <option value="">All Status</option>
        <option value="Open">Open</option>
        <option value="Work In Progress">Work In Progress</option>
        <option value="Completed">Completed</option>
        <option value="Cancelled">Cancelled</option>
      </select>
      <input class="bomx-search" v-model="search" type="text" placeholder="Search Job Card, Work Order, Operation…"/>
      <div class="bomx-list">
        <template v-if="loading">
          <div v-for="n in 5" :key="n" class="bomx-item"><div class="shimmer" style="height:38px;border-radius:6px"></div></div>
        </template>
        <div v-else-if="!sorted.length" class="bomx-list-empty">No Job Cards found</div>
        <div v-else v-for="row in sorted" :key="row.name"
             class="bomx-item" :class="{active: selectedName === row.name}"
             @click="selectJobCard(row.name)">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px">
            <div class="bomx-item-name">{{ row.name }}</div>
            <span class="bomx-badge" :class="statusClass(row)">{{ statusLabel(row) }}</span>
          </div>
          <div class="bomx-item-meta">
            <span v-if="row.work_order">{{ row.work_order }}</span>
            <span v-if="row.work_order && row.operation">•</span>
            <span v-if="row.operation">{{ row.operation }}</span>
          </div>
          <div class="bomx-item-right" v-if="row.workstation">
            <span style="font-size:12px;color:var(--bx-muted)">{{ row.workstation }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ══════════ RIGHT: JOB CARD DETAIL ══════════ -->
    <div class="bomx-detail-panel">

      <!-- Empty state -->
      <div v-if="!selectedName" class="bomx-empty-state">
        <div class="bomx-empty-icon">🗂️</div>
        <div class="bomx-empty-title">Select a Job Card</div>
        <div class="bomx-empty-sub">Choose a Job Card from the list to view schedule, time logs, and status.</div>
        <button class="bomx-btn bomx-btn-mfg" @click="openAdd"><span v-html="icon('plus',13)"></span> Create Job Card</button>
      </div>

      <template v-else>
        <div v-if="detailLoading" class="bomx-empty-state"><div class="shimmer" style="height:200px;border-radius:10px"></div></div>

        <template v-else>
          <!-- Header -->
          <div class="bomx-detail-hdr">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px">
              <div style="min-width:0">
                <div class="bomx-detail-title">{{ isNew ? 'New Job Card' : doc.name }}</div>
                <div class="bomx-detail-meta">
                  <span v-if="!isNew && doc.work_order">{{ doc.work_order }}</span>
                  <span v-if="!isNew && doc.work_order && doc.operation">•</span>
                  <span v-if="doc.operation">{{ doc.operation }}</span>
                  <span v-if="doc.operation">•</span>
                  <span class="bomx-badge" :class="statusClass(doc)" style="font-size:11px">{{ statusLabel(doc) }}</span>
                </div>
              </div>
              <div style="display:flex;gap:6px;flex-shrink:0;flex-wrap:wrap;justify-content:flex-end">
                <button class="bomx-btn bomx-btn-ghost-inv" @click="goBackToList">Back</button>
                <button class="bomx-btn bomx-btn-light" @click="save" :disabled="saving || detailLoading">
                  {{ saving ? 'Saving…' : (isNew ? 'Save Job Card' : 'Save Changes') }}
                </button>
              </div>
            </div>
          </div>

          <!-- Header fields -->
          <div class="bomx-hdr-fields">
            <div>
              <div class="bomx-hf-label">Work Order <span style="color:var(--bx-red)">*</span></div>
              <select class="bomx-fi" v-model="doc.work_order" :disabled="!isNew" style="width:100%" :title="doc.work_order">
                <option value="">— Select Work Order —</option>
                <option v-for="w in workOrdersList" :key="w.name" :value="w.name">{{ w.name }}</option>
              </select>
            </div>
            <div>
              <div class="bomx-hf-label">Operation <span style="color:var(--bx-red)">*</span></div>
              <select class="bomx-fi" v-model="doc.operation" style="width:100%" :title="doc.operation">
                <option value="">— Select Operation —</option>
                <option v-for="o in operationsList" :key="o.name" :value="o.name">{{ o.name }}</option>
              </select>
            </div>
            <div>
              <div class="bomx-hf-label">Workstation</div>
              <select class="bomx-fi" v-model="doc.workstation" style="width:100%" :title="doc.workstation">
                <option value="">— Select —</option>
                <option v-for="w in workstationsList" :key="w.name" :value="w.name">{{ w.name }}</option>
              </select>
            </div>
          </div>
          <div class="bomx-toggle-row" style="align-items:flex-end;gap:24px">
            <div style="min-width:160px">
              <div class="bomx-hf-label">Status</div>
              <select class="bomx-fi" v-model="doc.status" style="width:100%">
                <option>Open</option>
                <option>Work In Progress</option>
                <option>Completed</option>
                <option>Cancelled</option>
              </select>
            </div>
            <div style="min-width:140px">
              <div class="bomx-hf-label">For Quantity</div>
              <input class="bomx-fi bomx-fi-mono" type="number" v-model.number="doc.for_quantity" min="0" step="any" style="width:100%"/>
            </div>
            <div style="flex:1;min-width:160px">
              <div class="bomx-hf-label">Employee</div>
              <input class="bomx-fi" type="text" v-model="doc.employee" placeholder="Operator name" style="width:100%"/>
            </div>
          </div>

          <!-- Body -->
          <div class="bomx-body">

            <!-- Schedule -->
            <div class="bomx-section-lbl">Schedule</div>
            <div class="bomx-hdr-fields" style="padding:0;border:none;background:none;margin-bottom:8px">
              <div>
                <div class="bomx-hf-label">Planned Start</div>
                <input class="bomx-fi" type="datetime-local" v-model="doc.planned_start_time" style="width:100%"/>
              </div>
              <div>
                <div class="bomx-hf-label">Planned End</div>
                <input class="bomx-fi" type="datetime-local" v-model="doc.planned_end_time" style="width:100%"/>
              </div>
            </div>
            <div class="bomx-hdr-fields" style="padding:0;border:none;background:none;margin-bottom:20px">
              <div>
                <div class="bomx-hf-label">Actual Start</div>
                <input class="bomx-fi" type="datetime-local" v-model="doc.actual_start_time" style="width:100%"/>
              </div>
              <div>
                <div class="bomx-hf-label">Actual End</div>
                <input class="bomx-fi" type="datetime-local" v-model="doc.actual_end_time" style="width:100%"/>
              </div>
            </div>

            <!-- Time Logs -->
            <div class="bomx-section-lbl" style="display:flex;align-items:center;justify-content:space-between">
              <span>Time Logs</span>
              <span v-if="doc.total_time_in_mins" style="text-transform:none;font-weight:600;color:var(--bx-mfgB)">Total: {{ fmtMins(doc.total_time_in_mins) }}</span>
            </div>
            <div class="bomx-rm-cards" style="margin-bottom:8px">
              <div v-if="!doc.time_logs || !doc.time_logs.length" class="bomx-tree-empty">No time logs yet.</div>
              <div v-for="(tl, idx) in doc.time_logs" :key="tl._uid" class="bomx-rm-card">
                <div class="bomx-rm-card-hdr">
                  <div class="bomx-rm-card-title">
                    Log #{{ idx + 1 }}
                    <span v-if="tl.from_time && !tl.to_time" class="bomx-badge badge-wip" style="margin-left:6px;font-size:10px">Running</span>
                  </div>
                  <button v-if="!tl.from_time || tl.to_time" class="bomx-btn bomx-btn-sm" style="background:var(--bx-greenS);color:var(--bx-green)" @click="startTimeLog(tl)">▶ Start</button>
                  <button v-else class="bomx-btn bomx-btn-sm" style="background:var(--bx-redS);color:var(--bx-red)" @click="stopTimeLog(tl)">■ Stop</button>
                  <div class="bomx-rm-card-amt" v-if="tl.time_in_mins">
                    <span class="bomx-rm-card-amt-lbl">Duration</span>
                    <span class="mono" style="font-size:13px;font-weight:700;color:var(--bx-mfgB)">{{ fmtMins(tl.time_in_mins) }}</span>
                  </div>
                  <button class="bomx-btn-icon danger" @click="removeTimeLog(idx)" title="Remove">
                    <span v-html="icon('trash',13)"></span>
                  </button>
                </div>
                <div class="bomx-rm-card-body">
                  <div class="bomx-rm-field">
                    <label>From</label>
                    <input class="bomx-fi" type="datetime-local" v-model="tl.from_time" @change="calcTimeDiff(tl)"/>
                  </div>
                  <div class="bomx-rm-field">
                    <label>To</label>
                    <input class="bomx-fi" type="datetime-local" v-model="tl.to_time" @change="calcTimeDiff(tl)"/>
                  </div>
                  <div class="bomx-rm-field">
                    <label>Time (Min)</label>
                    <input class="bomx-fi bomx-fi-mono" type="number" v-model.number="tl.time_in_mins" readonly/>
                  </div>
                  <div class="bomx-rm-field">
                    <label>Employee</label>
                    <input class="bomx-fi" type="text" v-model="tl.employee" placeholder="Name"/>
                  </div>
                </div>
                <div v-if="tl._invalidRange" class="bomx-field-hint" style="color:var(--bx-red);font-weight:600;padding:0 14px 10px">
                  ⚠ To Time is before From Time — fix this row before saving.
                </div>
              </div>
            </div>
            <div class="bomx-add-row" @click="addTimeLog">
              <span v-html="icon('plus',13)"></span> Add Time Log
            </div>

            <!-- Remarks -->
            <div class="bomx-section-lbl" style="margin-top:20px">Remarks</div>
            <textarea class="bomx-fi" v-model="doc.remarks" style="width:100%;min-height:90px;resize:vertical" placeholder="Optional notes…"></textarea>
          </div>

          <!-- Footer -->
          <div class="bomx-footer">
            <button v-if="!isNew" class="bomx-btn bomx-btn-ghost-inv" style="color:var(--bx-red);border-color:rgba(201,42,42,.3)" @click="deleteFromDetail">Delete Job Card</button>
            <div style="flex:1"></div>
            <button class="bomx-btn bomx-btn-mfg" @click="save" :disabled="saving || detailLoading">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13"/><polyline points="7 3 7 8 15 8"/></svg>
              {{ saving ? 'Saving…' : (isNew ? 'Save Job Card' : 'Save Changes') }}
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
const filterStatus = ref(typeof route.query.status === "string" ? route.query.status : "");

const selectedName = computed(() => (route.params.name && route.params.name !== "new") ? route.params.name : (route.params.name === "new" ? "new" : null));

async function loadList() {
  loading.value = true;
  try {
    const fields = ["name", "work_order", "operation", "workstation", "status", "modified"];
    const r = await apiList("Job Card", { fields, limit: 2000, order: "modified desc" });
    list.value = r || [];
  } catch (e) {
    toast("Could not load Job Cards", "error");
  }
  loading.value = false;
}

const sorted = computed(() => {
  let r = list.value;
  if (filterStatus.value) r = r.filter(i => i.status === filterStatus.value);
  const q = search.value.toLowerCase().trim();
  if (q) r = r.filter(i => [i.name, i.work_order, i.operation, i.workstation].filter(Boolean).join(" ").toLowerCase().includes(q));
  return r;
});

function statusLabel(row) { return row.status || "Open"; }
function statusClass(row) {
  const s = row.status;
  if (s === "Completed")        return "badge-active";
  if (s === "Cancelled")        return "badge-obsolete";
  if (s === "Work In Progress") return "badge-wip";
  return "badge-open";
}

function selectJobCard(name) {
  router.push(`/manufacturing/job-card/${name}`);
}
function openAdd() {
  router.push("/manufacturing/job-card/new");
}
function goBackToList() {
  router.push("/manufacturing/job-card");
}

async function deleteFromDetail() {
  const name = doc.value.name;
  if (await confirm({ title: "Delete Job Card?", body: `Are you sure you want to delete ${name}?`, okLabel: "Delete", okStyle: "danger" })) {
    try {
      await apiDelete("Job Card", name);
      toast("Job Card deleted");
      goBackToList();
      loadList();
    } catch (e) {
      toast("Could not delete Job Card: " + e.message, "error");
    }
  }
}

// ── DETAIL STATE ─────────────────────────────────────────────
const isNew = computed(() => route.params.name === "new");
const detailLoading = ref(false);
const saving = ref(false);

function emptyDoc() {
  return {
    doctype: "Job Card",
    work_order: "",
    operation: "",
    workstation: "",
    status: "Open",
    for_quantity: 1,
    employee: "",
    planned_start_time: "",
    planned_end_time: "",
    actual_start_time: "",
    actual_end_time: "",
    time_logs: [],
    total_time_in_mins: 0,
    remarks: "",
  };
}
const doc = ref(emptyDoc());

const workOrdersList = ref([]);
const operationsList = ref([]);
const workstationsList = ref([]);

let _uid = 0;
function nextUid() { return ++_uid; }
function ensureUids(rows) { (rows || []).forEach(r => { if (!r._uid) r._uid = nextUid(); }); return rows; }

async function loadDropdowns() {
  try {
    const [wos, ops, wks] = await Promise.all([
      apiList("Work Order", { fields: ["name"], filters: [["docstatus", "=", 1], ["status", "not in", ["Completed", "Stopped", "Cancelled"]]], limit: 2000, order: "name desc" }),
      apiList("Operation",  { fields: ["name"], filters: [["is_active", "=", 1]], limit: 1000, order: "name asc" }),
      apiList("Workstation",{ fields: ["name"], filters: [["is_active", "=", 1]], limit: 1000, order: "name asc" }),
    ]);
    workOrdersList.value   = wos || [];
    operationsList.value   = ops || [];
    workstationsList.value = wks || [];
  } catch (e) {
    toast("Could not load reference data", "error");
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
    // Deep-link support: Work Order page can send users here pre-filled via
    // /manufacturing/job-card/new?work_order=X&operation=Y&workstation=Z
    if (route.query.work_order) doc.value.work_order = route.query.work_order;
    if (route.query.operation) doc.value.operation = route.query.operation;
    if (route.query.workstation) doc.value.workstation = route.query.workstation;
    if (route.query.work_order && !workOrdersList.value.some(w => w.name === route.query.work_order))
      workOrdersList.value = [{ name: route.query.work_order }, ...workOrdersList.value];
    return;
  }
  detailLoading.value = true;
  try {
    const r = await apiGet("Job Card", route.params.name);
    if (!r.time_logs) r.time_logs = [];
    ensureUids(r.time_logs);
    doc.value = r;
    // keep stale refs selectable
    if (r.work_order && !workOrdersList.value.some(w => w.name === r.work_order))
      workOrdersList.value = [{ name: r.work_order }, ...workOrdersList.value];
    if (r.operation && !operationsList.value.some(o => o.name === r.operation))
      operationsList.value = [{ name: r.operation }, ...operationsList.value];
    if (r.workstation && !workstationsList.value.some(w => w.name === r.workstation))
      workstationsList.value = [{ name: r.workstation }, ...workstationsList.value];
  } catch (e) {
    toast("Could not load Job Card", "error");
    goBackToList();
  }
  detailLoading.value = false;
}

function calcTimeDiff(tl) {
  if (!tl.from_time || !tl.to_time) { tl.time_in_mins = 0; tl._invalidRange = false; recomputeTotal(); return; }
  const diff = (new Date(tl.to_time) - new Date(tl.from_time)) / 60000;
  if (diff > 0) {
    tl.time_in_mins = parseFloat(diff.toFixed(2));
    tl._invalidRange = false;
  } else {
    // Don't silently zero this out and hide the problem — flag the row so the
    // user sees exactly which one is wrong, right where they're editing it,
    // instead of finding out from a generic toast after clicking Save.
    tl.time_in_mins = 0;
    tl._invalidRange = true;
  }
  recomputeTotal();
}

function recomputeTotal() {
  doc.value.total_time_in_mins = (doc.value.time_logs || []).reduce((s, r) => s + (r.time_in_mins || 0), 0);
}

function removeTimeLog(idx) {
  doc.value.time_logs.splice(idx, 1);
  recomputeTotal();
}

function startTimeLog(tl) {
  tl.from_time = new Date().toISOString().slice(0, 16);
  tl.to_time = "";
  tl.time_in_mins = 0;
  tl._invalidRange = false;
  recomputeTotal();
}

function stopTimeLog(tl) {
  tl.to_time = new Date().toISOString().slice(0, 16);
  calcTimeDiff(tl);
}

function addTimeLog() {
  if (!doc.value.time_logs) doc.value.time_logs = [];
  doc.value.time_logs.push({ _uid: nextUid(), from_time: "", to_time: "", time_in_mins: 0, employee: doc.value.employee || "" });
}

function fmtMins(m) {
  const h = Math.floor(m / 60), min = Math.round(m % 60);
  return h > 0 ? `${h}h ${min}m` : `${min}m`;
}

async function save() {
  if (!doc.value.work_order) return toast("Work Order is required", "error");
  if (!doc.value.operation)  return toast("Operation is required", "error");
  if ((doc.value.time_logs || []).some(tl => tl._invalidRange)) {
    return toast("Fix the time log row where To Time is before From Time", "error");
  }

  saving.value = true;
  try {
    const payload = {
      ...doc.value,
      time_logs: (doc.value.time_logs || []).map(({ _uid, _invalidRange, ...rest }) => rest),
    };
    const r = await apiSave(payload);
    toast(isNew.value ? "Job Card created successfully" : "Saved successfully");
    if (!r.time_logs) r.time_logs = [];
    ensureUids(r.time_logs);
    if (isNew.value) {
      router.replace(`/manufacturing/job-card/${r.name}`);
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
  plus:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>',
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
.bomx-item-right { display:flex; align-items:center; gap:6px; }

/* ── Badges ── */
.bomx-badge { display:inline-flex; align-items:center; padding:2px 8px; border-radius:20px; font-size:11px; font-weight:600; white-space:nowrap; }
.badge-active { background:var(--bx-greenS); color:var(--bx-green); }
.badge-obsolete { background:#F1F3F5; color:var(--bx-muted); }
.badge-wip { background:var(--bx-blueS); color:var(--bx-blue); }
.badge-open { background:var(--bx-amberS); color:var(--bx-amber); }

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
.bomx-toggle-row { display:flex; gap:20px; padding:14px 22px; flex-wrap:wrap; background:var(--bx-surf2); border-bottom:1px solid var(--bx-border); }
.bomx-toggle { display:flex; align-items:center; gap:6px; font-size:12.5px; font-weight:600; color:var(--bx-text); }

.bomx-body { padding:20px 22px; overflow-y:auto; flex:1; }
.bomx-section-lbl { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--bx-muted); margin-bottom:8px; }

/* ── Time log cards (reuse rm-card pattern) ── */
.bomx-rm-cards { display:flex; flex-direction:column; gap:10px; }
.bomx-rm-card { background:#fff; border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; box-shadow:0 1px 3px rgba(16,24,40,.04); }
.bomx-rm-card-hdr { display:flex; align-items:center; gap:10px; padding:10px 14px; background:var(--bx-mfgS); border-bottom:1px solid var(--bx-border); }
.bomx-rm-card-title { flex:1; min-width:0; font-weight:600; font-size:13px; }
.bomx-rm-card-amt { display:flex; flex-direction:column; align-items:flex-end; flex-shrink:0; gap:1px; }
.bomx-rm-card-amt-lbl { font-size:9.5px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; color:var(--bx-muted); }
.bomx-rm-card-body { display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:10px; padding:12px 14px; }
.bomx-rm-field { display:flex; flex-direction:column; gap:4px; min-width:0; }
.bomx-rm-field label { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); }
.bomx-rm-field .bomx-fi { width:100%; }
@media (max-width:640px) { .bomx-rm-card-body { grid-template-columns:1fr 1fr; } }

.bomx-tree-empty { text-align:center; padding:20px; color:var(--bx-muted); font-size:13px; }
.bomx-add-row { display:flex; align-items:center; gap:8px; padding:8px 12px; color:var(--bx-mfg); cursor:pointer; font-size:13px; font-weight:600; border-radius:var(--bx-rsm); }
.bomx-add-row:hover { background:var(--bx-mfgS); }

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
.bomx-btn-icon { background:none; border:1px solid var(--bx-border); border-radius:5px; cursor:pointer; padding:4px 6px; display:inline-flex; color:var(--bx-muted); }
.bomx-btn-icon:hover { border-color:var(--bx-mfg); color:var(--bx-mfg); background:var(--bx-mfgS); }
.bomx-btn-icon.danger { color:var(--bx-red); }
.bomx-btn-icon.danger:hover { background:var(--bx-redS); border-color:var(--bx-red); }

.shimmer { background:linear-gradient(90deg,#f1f3f5 25%,#e9ecef 37%,#f1f3f5 63%); background-size:400% 100%; animation:shimmer 1.4s ease infinite; }
@keyframes shimmer { 0%{background-position:100% 50%} 100%{background-position:0 50%} }

/* ── Mobile responsive ── */
@media (max-width:768px) {
  .bomx-page { padding:10px; overflow-x:hidden; }
  .bomx-two-col { gap:12px; }
  .bomx-list { max-height:280px; }
  .bomx-detail-panel { min-height:auto; }

  .bomx-detail-hdr { padding:14px 16px; }
  .bomx-hdr-fields { grid-template-columns:1fr; padding:12px 16px; gap:10px; }
  .bomx-toggle-row { padding:10px 16px 12px; gap:14px; }
  .bomx-body { padding:14px 16px; }

  .bomx-rm-card-body { grid-template-columns:1fr 1fr; }
  .bomx-footer { flex-direction:column; align-items:stretch; gap:10px; }
}

@media (max-width:420px) {
  .bomx-rm-card-body { grid-template-columns:1fr; }
}
</style>