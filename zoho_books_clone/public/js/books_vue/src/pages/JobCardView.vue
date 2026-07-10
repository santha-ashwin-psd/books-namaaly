<template>
<div class="sc-page">
  <div class="sc-sticky">
    <div class="sc-header">
      <div style="display:flex;align-items:center;gap:12px;">
        <button class="iv-back" @click="router.push('/manufacturing/job-card')"
          style="background:none;border:none;cursor:pointer;color:#2563eb;display:flex;align-items:center;gap:4px;font-weight:600;font-size:13px;padding:0;">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
          Back
        </button>
        <span class="sc-title">{{ isNew ? 'New Job Card' : doc.name }}</span>
        <div v-if="!isNew" class="inv-status-badge"
             style="font-size:12px;padding:3px 8px;border-radius:12px;"
             :style="statusStyle">
          {{ doc.status }}
        </div>
      </div>
      <div style="display:flex;gap:10px;">
        <button class="nim-btn" style="background:#fff;border:1px solid #e5e7eb;padding:8px 16px;border-radius:8px;font-weight:600;cursor:pointer;"
                @click="router.push('/manufacturing/job-card')" :disabled="saving">Cancel</button>
        <button class="sc-save-btn" @click="save" :disabled="saving || loading">
          <span v-if="saving" style="display:inline-block;width:12px;height:12px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .6s linear infinite;margin-right:6px;"></span>
          {{ isNew ? 'Save' : 'Save Changes' }}
        </button>
      </div>
    </div>
  </div>

  <div class="sc-body sc-body--narrow" v-if="loading">
    <div class="sc-col-main">
      <div class="sc-card"><div class="shimmer" style="height:160px"></div></div>
      <div class="sc-card"><div class="shimmer" style="height:200px"></div></div>
    </div>
  </div>

  <div class="sc-body sc-body--narrow" v-else>
    <div class="sc-col-main">

      <!-- ── Core Details ── -->
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>
          </div>
          <div>
            <div class="sc-card-title">Job Card Details</div>
            <div class="sc-card-subtitle">Work Order, Operation, and current status.</div>
          </div>
        </div>
        <div class="sc-divider"></div>

        <div class="sc-fg" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Work Order <span class="sc-required">*</span></label>
            <select class="nim-input" v-model="doc.work_order" :disabled="!isNew">
              <option value="">— Select Work Order —</option>
              <option v-for="w in workOrdersList" :key="w.name" :value="w.name">{{ w.name }}</option>
            </select>
          </div>
          <div class="nim-field">
            <label class="nim-label">Operation <span class="sc-required">*</span></label>
            <select class="nim-input" v-model="doc.operation">
              <option value="">— Select Operation —</option>
              <option v-for="o in operationsList" :key="o.name" :value="o.name">{{ o.name }}</option>
            </select>
          </div>
        </div>

        <div class="sc-fg" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Workstation</label>
            <select class="nim-input" v-model="doc.workstation">
              <option value="">— Select —</option>
              <option v-for="w in workstationsList" :key="w.name" :value="w.name">{{ w.name }}</option>
            </select>
          </div>
          <div class="nim-field">
            <label class="nim-label">Status</label>
            <select class="nim-input" v-model="doc.status">
              <option>Open</option>
              <option>Work In Progress</option>
              <option>Completed</option>
              <option>Cancelled</option>
            </select>
          </div>
        </div>

        <div class="sc-fg" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">For Quantity</label>
            <input type="number" class="nim-input" v-model.number="doc.for_quantity" min="0" step="any" />
            <div class="sc-field-hint">Planned production qty for this job.</div>
          </div>
          <div class="nim-field">
            <label class="nim-label">Employee</label>
            <input type="text" class="nim-input" v-model="doc.employee" placeholder="Operator name" />
          </div>
        </div>
      </div>

      <!-- ── Schedule ── -->
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon sc-card-icon--blue">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
          </div>
          <div><div class="sc-card-title">Schedule</div></div>
        </div>
        <div class="sc-divider"></div>

        <div class="sc-fg" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Planned Start</label>
            <input type="datetime-local" class="nim-input" v-model="doc.planned_start_time" />
          </div>
          <div class="nim-field">
            <label class="nim-label">Planned End</label>
            <input type="datetime-local" class="nim-input" v-model="doc.planned_end_time" />
          </div>
        </div>
        <div class="sc-fg">
          <div class="nim-field">
            <label class="nim-label">Actual Start</label>
            <input type="datetime-local" class="nim-input" v-model="doc.actual_start_time" />
          </div>
          <div class="nim-field">
            <label class="nim-label">Actual End</label>
            <input type="datetime-local" class="nim-input" v-model="doc.actual_end_time" />
          </div>
        </div>
      </div>

      <!-- ── Time Logs ── -->
      <div class="sc-card" style="padding:0;overflow:hidden;">
        <div class="sc-card-header" style="padding:16px 20px;justify-content:space-between;">
          <div style="display:flex;align-items:center;gap:14px;">
            <div class="sc-card-icon sc-card-icon--blue" style="width:32px;height:32px;border-radius:8px;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
            </div>
            <div>
              <div class="sc-card-title" style="font-size:15px;">Time Logs</div>
              <div class="sc-card-subtitle" v-if="doc.total_time_in_mins">Total: {{ fmtMins(doc.total_time_in_mins) }}</div>
            </div>
          </div>
        </div>

        <table style="width:100%;border-collapse:collapse;font-size:13.5px;text-align:left;">
          <thead>
            <tr style="background:#f8f9fc;border-top:1px solid #e8ecf2;border-bottom:1px solid #e8ecf2;color:#6b7280;">
              <th style="padding:10px 16px;font-weight:600;">From</th>
              <th style="padding:10px 16px;font-weight:600;">To</th>
              <th style="padding:10px 16px;font-weight:600;width:120px;">Time (Min)</th>
              <th style="padding:10px 16px;font-weight:600;">Employee</th>
              <th style="padding:10px 16px;width:44px;"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!doc.time_logs || !doc.time_logs.length">
              <td colspan="5" style="text-align:center;padding:24px;color:#9ca3af;">No time logs yet.</td>
            </tr>
            <tr v-for="(tl, idx) in doc.time_logs" :key="tl._uid" style="border-bottom:1px solid #e5e7eb;">
              <td style="padding:6px 16px;">
                <input type="datetime-local" class="nim-input" style="padding:6px 8px;font-size:12px;"
                       v-model="tl.from_time" @change="calcTimeDiff(tl)" />
              </td>
              <td style="padding:6px 16px;">
                <input type="datetime-local" class="nim-input" style="padding:6px 8px;font-size:12px;"
                       v-model="tl.to_time" @change="calcTimeDiff(tl)" />
              </td>
              <td style="padding:6px 16px;">
                <input type="number" class="nim-input" style="padding:6px 8px;text-align:right;"
                       v-model.number="tl.time_in_mins" min="0" step="any" readonly />
              </td>
              <td style="padding:6px 16px;">
                <input type="text" class="nim-input" style="padding:6px 8px;" v-model="tl.employee" placeholder="Name" />
              </td>
              <td style="padding:6px 16px;">
                <button class="inv-act-btn" style="color:#dc2626;" @click="doc.time_logs.splice(idx,1)" title="Remove">
                  <span v-html="icon('trash',13)"></span>
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <div style="padding:14px 20px;background:#f8f9fc;display:flex;gap:10px;align-items:center;">
          <button class="nim-btn" style="background:#fff;border:1px solid #e5e7eb;padding:6px 14px;border-radius:6px;font-weight:600;font-size:12px;cursor:pointer;"
                  @click="addTimeLog">
            <span v-html="icon('plus',12)" style="margin-right:4px;"></span> Add row
          </button>
          <span v-if="doc.total_time_in_mins" style="font-size:12px;color:#6b7280;margin-left:auto;">
            Total: <strong>{{ fmtMins(doc.total_time_in_mins) }}</strong>
          </span>
        </div>
      </div>

      <!-- ── Remarks ── -->
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-title">Remarks</div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-fg sc-fg--single">
          <div class="nim-field">
            <textarea class="nim-input" style="min-height:80px;resize:vertical;" v-model="doc.remarks" placeholder="Optional notes..."></textarea>
          </div>
        </div>
      </div>

    </div>
  </div>
</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet, apiSave, apiList } from "../api/client.js";
import { useToast } from "../composables/useToast.js";

const route = useRoute();
const router = useRouter();
const { toast } = useToast();

const isNew = ref(false);
const loading = ref(false);
const saving = ref(false);

const doc = ref({
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
});

const workOrdersList = ref([]);
const operationsList = ref([]);
const workstationsList = ref([]);

let _uid = 0;
function nextUid() { return ++_uid; }
function ensureUids(rows) { (rows||[]).forEach(r => { if (!r._uid) r._uid = nextUid(); }); return rows; }

const statusStyle = computed(() => {
  const s = doc.value.status;
  if (s === "Completed")        return "background:#dcfce7;color:#16a34a";
  if (s === "Cancelled")        return "background:#fee2e2;color:#dc2626";
  if (s === "Work In Progress") return "background:#dbeafe;color:#1e40af";
  return "background:#fef3c7;color:#b45309";
});

onMounted(async () => {
  loading.value = true;
  try {
    const [wos, ops, wks] = await Promise.all([
      apiList("Work Order", { fields: ["name"], filters: [["docstatus", "=", 1]], limit: 2000, order: "name desc" }),
      apiList("Operation",  { fields: ["name"], filters: [["is_active", "=", 1]], limit: 1000, order: "name asc" }),
      apiList("Workstation",{ fields: ["name"], filters: [["is_active", "=", 1]], limit: 1000, order: "name asc" }),
    ]);
    workOrdersList.value  = wos || [];
    operationsList.value  = ops || [];
    workstationsList.value = wks || [];
  } catch (e) {
    toast("Could not load reference data", "error");
  }

  const name = route.params.name;
  if (name === "new") {
    isNew.value = true;
    loading.value = false;
    return;
  }

  try {
    const r = await apiGet("Job Card", name);
    if (r) {
      if (!r.time_logs) r.time_logs = [];
      ensureUids(r.time_logs);
      doc.value = r;
      // keep stale refs selectable
      if (r.work_order  && !workOrdersList.value.some(w => w.name === r.work_order))
        workOrdersList.value  = [{ name: r.work_order },  ...workOrdersList.value];
      if (r.operation   && !operationsList.value.some(o => o.name === r.operation))
        operationsList.value  = [{ name: r.operation },   ...operationsList.value];
      if (r.workstation && !workstationsList.value.some(w => w.name === r.workstation))
        workstationsList.value = [{ name: r.workstation }, ...workstationsList.value];
    }
  } catch (e) {
    toast("Could not load Job Card", "error");
    router.push("/manufacturing/job-card");
  }
  loading.value = false;
});

function calcTimeDiff(tl) {
  if (!tl.from_time || !tl.to_time) { tl.time_in_mins = 0; return; }
  const diff = (new Date(tl.to_time) - new Date(tl.from_time)) / 60000;
  tl.time_in_mins = diff > 0 ? parseFloat(diff.toFixed(2)) : 0;
  doc.value.total_time_in_mins = (doc.value.time_logs || []).reduce((s, r) => s + (r.time_in_mins || 0), 0);
}

function addTimeLog() {
  if (!doc.value.time_logs) doc.value.time_logs = [];
  const now = new Date().toISOString().slice(0, 16);
  doc.value.time_logs.push({ _uid: nextUid(), from_time: now, to_time: "", time_in_mins: 0, employee: doc.value.employee || "" });
}

function fmtMins(m) {
  const h = Math.floor(m / 60), min = Math.round(m % 60);
  return h > 0 ? `${h}h ${min}m` : `${min}m`;
}

async function save() {
  if (!doc.value.work_order) return toast("Work Order is required", "error");
  if (!doc.value.operation)  return toast("Operation is required", "error");

  saving.value = true;
  try {
    const payload = {
      ...doc.value,
      time_logs: (doc.value.time_logs || []).map(({ _uid, ...rest }) => rest),
    };
    const r = await apiSave(payload);
    toast("Saved successfully");
    if (!r.time_logs) r.time_logs = [];
    ensureUids(r.time_logs);
    if (isNew.value) {
      router.replace(`/manufacturing/job-card/${r.name}`);
      isNew.value = false;
    }
    doc.value = r;
  } catch (e) {
    toast(e.message || "Could not save", "error");
  }
  saving.value = false;
}

const ICONS = {
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>',
  plus:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
};
function icon(name, size) { return (ICONS[name]||"").replace("<svg ",`<svg width="${size}" height="${size}" `); }
</script>

<style scoped>
@keyframes spin { to { transform: rotate(360deg) } }
.sc-page { background:#f0f2f5; padding-bottom:32px; min-height:100vh; }
.sc-sticky { position:sticky; top:0; z-index:20; background:#f0f2f5; }
.sc-header { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:18px 24px 0; margin-bottom:24px; }
.sc-title { font-size:20px; font-weight:700; color:#1a1a2e; letter-spacing:-0.3px; }
.sc-save-btn { display:flex; align-items:center; gap:7px; font-size:13.5px; font-weight:600; padding:9px 20px; border-radius:9px; background:linear-gradient(135deg,#2f74f5 0%,#1a6ef7 100%); border:none; color:#fff; cursor:pointer; box-shadow:0 4px 12px rgba(26,110,247,.28); transition:filter .18s,transform .18s; }
.sc-save-btn:hover:not(:disabled) { filter:brightness(1.04); transform:translateY(-1px); }
.sc-save-btn:disabled { opacity:.55; cursor:not-allowed; }
.sc-body { padding:24px; display:grid; gap:20px; align-content:start; }
.sc-body--narrow { max-width:900px; margin:0 auto; }
.sc-col-main { display:grid; gap:20px; align-content:start; }
.sc-card { background:#fff; border:1px solid #e8ecf2; border-radius:14px; padding:22px 24px; box-shadow:0 1px 2px rgba(16,24,40,.04); transition:box-shadow .2s,transform .2s,border-color .2s; }
.sc-card:hover { box-shadow:0 6px 20px rgba(16,24,40,.07); border-color:#dbe3ee; transform:translateY(-1px); }
.sc-card-header { display:flex; align-items:center; gap:14px; }
.sc-card-icon { width:40px; height:40px; border-radius:11px; background:linear-gradient(135deg,#eaf1ff,#dbe7ff); color:#2563eb; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.sc-card-icon--blue { background:linear-gradient(135deg,#eaf1ff,#dbe7ff); color:#2563eb; }
.sc-card-title { font-size:14px; font-weight:700; color:#111827; }
.sc-card-subtitle { font-size:12px; color:#9ca3af; margin-top:2px; }
.sc-divider { height:1px; background:#f3f4f6; margin:18px 0; }
.sc-required { color:#dc2626; }
.sc-field-hint { font-size:12px; color:#6b7280; margin-top:4px; }
.sc-fg { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
.sc-fg--single { grid-template-columns:1fr; }
.nim-field { display:flex; flex-direction:column; gap:6px; }
.nim-label { font-size:13px; font-weight:600; color:#374151; }
.nim-input { border:1px solid #d1d5db; border-radius:8px; padding:10px 14px; font-size:14px; color:#111827; outline:none; transition:border-color .15s,box-shadow .15s; background:#fff; }
.nim-input:focus { border-color:#2563eb; box-shadow:0 0 0 3px rgba(37,99,235,.1); }
.nim-btn { background:#fff; border:1px solid #e5e7eb; padding:8px 16px; border-radius:8px; font-weight:600; cursor:pointer; }
.inv-act-btn { background:none; border:none; cursor:pointer; display:flex; align-items:center; justify-content:center; padding:4px; border-radius:6px; transition:background .15s; }
.inv-act-btn:hover { background:#fee2e2; }
@media (max-width:600px) { .sc-fg { grid-template-columns:1fr; } }
</style>
