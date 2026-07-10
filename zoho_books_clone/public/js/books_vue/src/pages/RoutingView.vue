<template>
<div class="sc-page">
  <div class="sc-sticky">
    <div class="sc-header">
      <div style="display:flex;align-items:center;gap:12px;">
        <button class="iv-back" @click="router.push('/manufacturing/routing')" style="background:none;border:none;cursor:pointer;color:#2563eb;display:flex;align-items:center;gap:4px;font-weight:600;font-size:13px;padding:0;">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
          Back
        </button>
        <span class="sc-title">{{ isNew ? 'New Routing' : doc.routing_name }}</span>
        <div v-if="!isNew" class="inv-status-badge"
             style="font-size:12px;padding:3px 8px;border-radius:12px;"
             :style="doc.is_active ? 'background:#dcfce7;color:#16a34a' : 'background:#fee2e2;color:#dc2626'">
          {{ doc.is_active ? 'Active' : 'Inactive' }}
        </div>
      </div>
      <div style="display:flex;gap:10px;">
        <button class="nim-btn" style="background:#fff;border:1px solid #e5e7eb;padding:8px 16px;border-radius:8px;font-weight:600;cursor:pointer;"
                @click="router.push('/manufacturing/routing')" :disabled="saving">Cancel</button>
        <button class="sc-save-btn" @click="save" :disabled="saving || loading">
          <span v-if="saving" style="display:inline-block;width:12px;height:12px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .6s linear infinite;margin-right:6px;"></span>
          {{ isNew ? 'Save' : 'Save Changes' }}
        </button>
      </div>
    </div>
  </div>

  <div class="sc-body sc-body--narrow" v-if="loading">
    <div class="sc-col-main">
      <div class="sc-card"><div class="shimmer" style="height:120px"></div></div>
      <div class="sc-card"><div class="shimmer" style="height:200px"></div></div>
    </div>
  </div>

  <div class="sc-body sc-body--narrow" v-else>
    <div class="sc-col-main">

      <!-- ── Settings card ── -->
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
          </div>
          <div>
            <div class="sc-card-title">Routing Details</div>
            <div class="sc-card-subtitle">Name and status of this operation sequence.</div>
          </div>
        </div>
        <div class="sc-divider"></div>

        <div class="sc-fg" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Routing Name <span class="sc-required">*</span></label>
            <input type="text" class="nim-input" v-model="doc.routing_name" :disabled="!isNew"
                   placeholder="e.g., Standard Assembly Line" />
            <div v-if="!isNew" class="sc-field-hint">Routing name cannot be changed after creation.</div>
          </div>
          <div class="nim-field" style="display:flex;align-items:flex-end;padding-bottom:4px;">
            <label class="sc-toggle-row" style="padding:8px;background:none;">
              <input type="checkbox" v-model="doc.is_active" :true-value="1" :false-value="0" style="margin-right:8px;"/>
              <span style="font-size:13px;font-weight:600;">Is Active</span>
            </label>
          </div>
        </div>

        <div class="sc-fg sc-fg--single" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Description</label>
            <textarea class="nim-input" style="min-height:80px;resize:vertical;" v-model="doc.description"
                      placeholder="Describe this routing (optional)..."></textarea>
          </div>
        </div>
      </div>

      <!-- ── Operations sequence card ── -->
      <div class="sc-card" style="padding:0;overflow:hidden;">
        <div class="sc-card-header" style="padding:16px 20px;">
          <div style="display:flex;align-items:center;gap:14px;">
            <div class="sc-card-icon sc-card-icon--blue" style="width:32px;height:32px;border-radius:8px;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>
            </div>
            <div>
              <div class="sc-card-title" style="font-size:15px;">Operations Sequence</div>
              <div class="sc-card-subtitle">Ordered list of operations performed in this routing.</div>
            </div>
          </div>
        </div>

        <table style="width:100%;border-collapse:collapse;font-size:13.5px;text-align:left;">
          <thead>
            <tr style="background:#f8f9fc;border-top:1px solid #e8ecf2;border-bottom:1px solid #e8ecf2;color:#6b7280;">
              <th style="padding:10px 16px;font-weight:600;width:52px;">Seq</th>
              <th style="padding:10px 16px;font-weight:600;">Operation <span style="color:#dc2626">*</span></th>
              <th style="padding:10px 16px;font-weight:600;">Workstation</th>
              <th style="padding:10px 16px;font-weight:600;width:130px;">Time (Min)</th>
              <th style="padding:10px 16px;font-weight:600;width:130px;">Hour Rate</th>
              <th style="padding:10px 16px;width:44px;"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!doc.operations || !doc.operations.length">
              <td colspan="6" style="text-align:center;padding:28px;color:#9ca3af;">
                No operations yet — click "Add row" below.
              </td>
            </tr>
            <tr v-for="(op, idx) in doc.operations" :key="op._uid"
                style="border-bottom:1px solid #e5e7eb;">
              <td style="padding:8px 16px;font-weight:600;color:#9ca3af;">{{ idx + 1 }}</td>
              <td style="padding:6px 16px;">
                <select class="nim-input" style="width:100%;padding:6px 10px;" v-model="op.operation"
                        @change="onOpChange(op)">
                  <option value="">— Select —</option>
                  <option v-for="o in operationsList" :key="o.name" :value="o.name">{{ o.name }}</option>
                </select>
              </td>
              <td style="padding:6px 16px;">
                <select class="nim-input" style="width:100%;padding:6px 10px;" v-model="op.workstation"
                        @change="onWorkstationChange(op)">
                  <option value="">— Select —</option>
                  <option v-for="w in workstationsList" :key="w.name" :value="w.name">{{ w.name }}</option>
                </select>
              </td>
              <td style="padding:6px 16px;">
                <input type="number" class="nim-input" style="width:100%;padding:6px 10px;"
                       v-model.number="op.time_in_mins" min="0" step="any" placeholder="0" />
              </td>
              <td style="padding:6px 16px;">
                <input type="number" class="nim-input" style="width:100%;padding:6px 10px;"
                       v-model.number="op.hour_rate" min="0" step="any" placeholder="0" />
              </td>
              <td style="padding:6px 16px;">
                <button class="inv-act-btn" style="color:#dc2626;" @click="doc.operations.splice(idx, 1)"
                        title="Remove row"><span v-html="icon('trash',13)"></span></button>
              </td>
            </tr>
          </tbody>
        </table>

        <div style="padding:14px 20px;background:#f8f9fc;display:flex;gap:10px;">
          <button class="nim-btn" style="background:#fff;border:1px solid #e5e7eb;padding:6px 14px;border-radius:6px;font-weight:600;font-size:12px;cursor:pointer;"
                  @click="addOp">
            <span v-html="icon('plus', 12)" style="margin-right:4px;"></span> Add row
          </button>
        </div>
      </div>

    </div>
  </div>
</div>
</template>

<script setup>
import { ref, onMounted } from "vue";
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
  doctype: "Routing",
  routing_name: "",
  is_active: 1,
  description: "",
  operations: [],
});

const operationsList = ref([]);
const workstationsList = ref([]);

let _uid = 0;
function nextUid() { return ++_uid; }
function ensureUids(rows) {
  (rows || []).forEach(r => { if (!r._uid) r._uid = nextUid(); });
  return rows;
}

onMounted(async () => {
  loading.value = true;
  try {
    const [ops, wks] = await Promise.all([
      apiList("Operation", { fields: ["name"], filters: [["is_active", "=", 1]], limit: 1000, order: "name asc" }),
      apiList("Workstation", { fields: ["name", "hour_rate"], filters: [["is_active", "=", 1]], limit: 1000, order: "name asc" }),
    ]);
    operationsList.value = ops || [];
    workstationsList.value = wks || [];
  } catch (e) {
    toast("Could not load Operations / Workstations", "error");
  }

  const name = route.params.name;
  if (name === "new") {
    isNew.value = true;
    loading.value = false;
    return;
  }

  try {
    const r = await apiGet("Routing", name);
    if (r) {
      if (!r.operations) r.operations = [];
      ensureUids(r.operations);
      doc.value = r;
      // keep an already-saved-but-now-inactive workstation selectable
      r.operations.forEach(op => {
        if (op.workstation && !workstationsList.value.some(w => w.name === op.workstation)) {
          workstationsList.value = [{ name: op.workstation, hour_rate: 0 }, ...workstationsList.value];
        }
        if (op.operation && !operationsList.value.some(o => o.name === op.operation)) {
          operationsList.value = [{ name: op.operation }, ...operationsList.value];
        }
      });
    }
  } catch (e) {
    toast("Could not load Routing", "error");
    router.push("/manufacturing/routing");
  }
  loading.value = false;
});

function addOp() {
  if (!doc.value.operations) doc.value.operations = [];
  doc.value.operations.push({ _uid: nextUid(), operation: "", workstation: "", time_in_mins: 0, hour_rate: 0 });
}

function onOpChange(op) {
  // Auto-fill workstation from Operation.default_workstation if workstation is blank
  if (op.operation && !op.workstation) {
    const found = operationsList.value.find(o => o.name === op.operation);
    if (found && found.default_workstation) {
      op.workstation = found.default_workstation;
      onWorkstationChange(op);
    }
  }
}

function onWorkstationChange(op) {
  if (!op.workstation) return;
  const w = workstationsList.value.find(x => x.name === op.workstation);
  if (w && w.hour_rate) op.hour_rate = w.hour_rate;
}

async function save() {
  if (!doc.value.routing_name || !doc.value.routing_name.trim()) {
    toast("Routing Name is mandatory", "error");
    return;
  }
  if (!doc.value.operations || doc.value.operations.length === 0) {
    toast("Add at least one Operation row", "error");
    return;
  }
  for (const op of doc.value.operations) {
    if (!op.operation) {
      toast("Each row must have an Operation selected", "error");
      return;
    }
  }

  saving.value = true;
  try {
    const payload = {
      ...doc.value,
      operations: (doc.value.operations || []).map(({ _uid, ...rest }) => rest),
    };
    const r = await apiSave(payload);
    toast("Saved successfully");
    if (!r.operations) r.operations = [];
    ensureUids(r.operations);
    if (isNew.value) {
      router.replace(`/manufacturing/routing/${r.name}`);
      isNew.value = false;
    }
    doc.value = r;
  } catch (e) {
    toast(e.message || "Could not save", "error");
  }
  saving.value = false;
}

// ── Icons ──────────────────────────────────────────────────────────────
const ICONS = {
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>',
  plus:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
};
function icon(name, size) {
  return (ICONS[name] || "").replace("<svg ", `<svg width="${size}" height="${size}" `);
}
</script>

<style scoped>
@keyframes spin { to { transform: rotate(360deg) } }

.sc-page { background: #f0f2f5; padding-bottom: 32px; min-height: 100vh; }
.sc-sticky { position: sticky; top: 0; z-index: 20; background: #f0f2f5; }
.sc-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 18px 24px 0; margin-bottom: 24px; }
.sc-title { font-size: 20px; font-weight: 700; color: #1a1a2e; letter-spacing: -0.3px; }

.sc-save-btn {
  display: flex; align-items: center; gap: 7px; font-size: 13.5px; font-weight: 600;
  padding: 9px 20px; border-radius: 9px;
  background: linear-gradient(135deg, #2f74f5 0%, #1a6ef7 100%);
  border: none; color: #fff; cursor: pointer;
  box-shadow: 0 4px 12px rgba(26,110,247,.28), inset 0 1px 0 rgba(255,255,255,.18);
  transition: box-shadow .18s ease, transform .18s ease, filter .18s ease;
}
.sc-save-btn:hover:not(:disabled) { filter: brightness(1.04); transform: translateY(-1px); }
.sc-save-btn:active:not(:disabled) { transform: translateY(0); }
.sc-save-btn:disabled { opacity: .55; cursor: not-allowed; }

.sc-body { padding: 24px; display: grid; gap: 20px; align-content: start; }
.sc-body--narrow { max-width: 900px; margin: 0 auto; }
.sc-col-main { display: grid; gap: 20px; align-content: start; }

.sc-card {
  background: #fff; border: 1px solid #e8ecf2; border-radius: 14px; padding: 22px 24px;
  box-shadow: 0 1px 2px rgba(16,24,40,.04), 0 1px 3px rgba(16,24,40,.03);
  transition: box-shadow .2s ease, transform .2s ease, border-color .2s ease;
}
.sc-card:hover { box-shadow: 0 6px 20px rgba(16,24,40,.07), 0 2px 6px rgba(16,24,40,.04); border-color: #dbe3ee; transform: translateY(-1px); }
.sc-card-header { display: flex; align-items: center; gap: 14px; }
.sc-card-icon { width: 40px; height: 40px; border-radius: 11px; background: linear-gradient(135deg, #eaf1ff 0%, #dbe7ff 100%); color: #2563eb; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.sc-card-icon--blue { background: linear-gradient(135deg, #eaf1ff 0%, #dbe7ff 100%); color: #2563eb; }
.sc-card-title { font-size: 14px; font-weight: 700; color: #111827; }
.sc-card-subtitle { font-size: 12px; color: #9ca3af; margin-top: 2px; }
.sc-divider { height: 1px; background: #f3f4f6; margin: 18px 0; }
.sc-required { color: #dc2626; }
.sc-field-hint { font-size: 12px; color: #6b7280; margin-top: 4px; }

.sc-fg { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.sc-fg--single { grid-template-columns: 1fr; }

.nim-field { display: flex; flex-direction: column; gap: 6px; }
.nim-label { font-size: 13px; font-weight: 600; color: #374151; }
.nim-input { border: 1px solid #d1d5db; border-radius: 8px; padding: 10px 14px; font-size: 14px; color: #111827; outline: none; transition: border-color .15s, box-shadow .15s; background: #fff; }
.nim-input:focus { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,.1); }
.nim-btn { background: #fff; border: 1px solid #e5e7eb; padding: 8px 16px; border-radius: 8px; font-weight: 600; cursor: pointer; }

.sc-toggle-row { display: flex; align-items: center; cursor: pointer; }

.inv-act-btn { background: none; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; padding: 4px; border-radius: 6px; transition: background .15s; }
.inv-act-btn:hover { background: #fee2e2; }

@media (max-width: 600px) {
  .sc-fg { grid-template-columns: 1fr; }
}
</style>
