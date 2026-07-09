<template>
<div class="sc-page">
  <div class="sc-sticky">
    <div class="sc-header">
      <div style="display:flex;align-items:center;gap:12px;">
        <button class="iv-back" @click="router.push('/manufacturing/operation')" style="background:none;border:none;cursor:pointer;color:#2563eb;display:flex;align-items:center;gap:4px;font-weight:600;font-size:13px;padding:0;">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
          Back
        </button>
        <span class="sc-title">{{ isNew ? 'New Operation' : doc.operation_name }}</span>
        <div v-if="!isNew" class="inv-status-badge" :class="doc.is_active?'status-active':'status-inactive'" style="font-size:12px;padding:3px 8px;border-radius:12px;" :style="doc.is_active?'background:#dcfce7;color:#16a34a':'background:#fee2e2;color:#dc2626'">
          {{ doc.is_active ? 'Active' : 'Inactive' }}
        </div>
      </div>
      <div style="display:flex;gap:10px;">
        <button class="nim-btn" style="background:#fff;border:1px solid #e5e7eb;padding:8px 16px;border-radius:8px;font-weight:600;cursor:pointer;" @click="router.push('/manufacturing/operation')" :disabled="saving">Cancel</button>
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
      <div class="sc-card"><div class="shimmer" style="height:80px"></div></div>
    </div>
  </div>

  <div class="sc-body sc-body--narrow" v-else>
    <div class="sc-col-main">
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
          </div>
          <div>
            <div class="sc-card-title">Operation Settings</div>
            <div class="sc-card-subtitle">General attributes for this operation.</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        
        <div class="sc-fg" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Name <span class="sc-required">*</span></label>
            <input type="text" class="nim-input" v-model="doc.operation_name" :disabled="!isNew" placeholder="e.g., Body Assembly" />
          </div>
          <div class="nim-field">
            <label class="sc-toggle-row" style="padding:8px;background:none;margin-top:24px;">
              <input type="checkbox" v-model="doc.is_corrective_operation" :true-value="1" :false-value="0" style="margin-right:8px;"/> 
              <span style="font-size:13px;font-weight:600;">Is Corrective Operation</span>
            </label>
          </div>
        </div>
        
        <div class="sc-fg sc-fg--single" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Default Workstation</label>
            <select class="nim-input" v-model="doc.default_workstation">
              <option value="">— Select Workstation —</option>
              <option v-for="w in workstations" :key="w.name" :value="w.name">{{ w.name }}</option>
            </select>
          </div>
        </div>

        <div class="sc-fg sc-fg--single" style="margin-top:20px;margin-bottom:14px">
          <div style="font-size:14px;font-weight:700;color:#374151;margin-bottom:8px;">Job Card</div>
          <label class="sc-toggle-row" style="padding:8px;background:none;border-bottom:1px solid #e5e7eb;padding-bottom:16px;">
            <input type="checkbox" v-model="doc.batch_size" :true-value="1" :false-value="0" style="margin-right:8px;"/> 
            <span style="font-size:13px;font-weight:600;">Create Job Card based on Batch Size</span>
          </label>
        </div>

        <div class="sc-fg sc-fg--single" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">QC Inspection Template</label>
            <select class="nim-input" v-model="doc.quality_inspection_template">
              <option value="">— Select Template —</option>
              <option v-for="t in templates" :key="t.name" :value="t.name">{{ t.name }}</option>
            </select>
          </div>
        </div>
      </div>

      <div class="sc-card" style="padding:0;overflow:hidden;">
        <div class="sc-card-header" style="padding:16px 20px;">
          <div style="display:flex;align-items:center;gap:14px;">
            <div class="sc-card-icon sc-card-icon--blue" style="width:32px;height:32px;border-radius:8px;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>
            </div>
            <div class="sc-card-title" style="font-size:15px;">Sub Operations</div>
          </div>
        </div>
        
        <table style="width:100%;border-collapse:collapse;font-size:13.5px;text-align:left;">
          <thead>
            <tr style="background:#f8f9fc;border-top:1px solid #e8ecf2;border-bottom:1px solid #e8ecf2;color:#6b7280;">
              <th style="padding:10px 20px;font-weight:600;width:50px;">No.</th>
              <th style="padding:10px 20px;font-weight:600;">Operation</th>
              <th style="padding:10px 20px;font-weight:600;width:150px;">Operation Time</th>
              <th style="padding:10px 20px;width:50px;"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!doc.sub_operations || !doc.sub_operations.length">
              <td colspan="4" style="text-align:center;padding:24px;color:#9ca3af;">No rows</td>
            </tr>
            <tr v-for="(sub, idx) in doc.sub_operations" :key="sub._uid" style="border-bottom:1px solid #e5e7eb;">
              <td style="padding:10px 20px;font-weight:600;color:#9ca3af;">{{ idx + 1 }}</td>
              <td style="padding:6px 20px;">
                <input type="text" class="nim-input" style="width:100%;padding:6px 10px;" v-model="sub.operation" placeholder="Sub-operation name" />
              </td>
              <td style="padding:6px 20px;">
                <input type="number" class="nim-input" style="width:100%;padding:6px 10px;" v-model.number="sub.operation_time" min="0" step="any" placeholder="Time" />
              </td>
              <td style="padding:6px 20px;">
                <button class="inv-act-btn" style="color:#dc2626;" @click="doc.sub_operations.splice(idx,1)" title="Remove Row"><span v-html="icon('trash',13)"></span></button>
              </td>
            </tr>
          </tbody>
        </table>
        
        <div style="padding:16px 20px;background:#f8f9fc;display:flex;gap:10px;">
          <button class="nim-btn" style="background:#fff;border:1px solid #e5e7eb;padding:6px 14px;border-radius:6px;font-weight:600;font-size:12px;cursor:pointer;" @click="addSubOp">Add row</button>
        </div>
      </div>

      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-title">Operation Description</div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-fg sc-fg--single">
          <div class="nim-field">
            <textarea class="nim-input" style="min-height:120px;resize:vertical;" v-model="doc.description" placeholder="Description..."></textarea>
          </div>
        </div>
        
        <div class="sc-fg sc-fg--single" style="margin-top:20px;">
          <div class="nim-field">
            <label class="sc-toggle-row" style="padding:8px;background:none;">
              <input type="checkbox" v-model="doc.is_active" :true-value="1" :false-value="0" style="margin-right:8px;"/> 
              <span style="font-size:13px;font-weight:600;">Is Active</span>
            </label>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { apiGet, apiSave, apiList } from '../api/client.js';
import { useToast } from '../composables/useToast.js';

const route = useRoute();
const router = useRouter();
const { toast } = useToast();

const isNew = ref(false);
const loading = ref(false);
const saving = ref(false);

const doc = ref({
  doctype: "Operation",
  operation_name: "",
  default_workstation: "",
  is_corrective_operation: 0,
  batch_size: 0,
  quality_inspection_template: "",
  sub_operations: [],
  description: "",
  is_active: 1
});

const workstations = ref([]);
const templates = ref([]);

let _uidCounter = 0;
function nextUid() { return ++_uidCounter; }
function ensureSubUids(rows) {
  (rows || []).forEach(r => { if (!r._uid) r._uid = nextUid(); });
  return rows;
}

onMounted(async () => {
  loading.value = true;

  try {
    const [ws, tmpl] = await Promise.all([
      apiList("Workstation", { fields: ["name"], filters: [["is_active", "=", 1]], limit: 1000 }),
      apiList("QC Inspection Template", { fields: ["name"], limit: 1000 }),
    ]);
    workstations.value = ws || [];
    templates.value = tmpl || [];
  } catch (e) {
    toast("Could not load Workstations / QC Templates — some dropdowns may be empty", "error");
  }

  const name = route.params.name;
  if (name === 'new') {
    isNew.value = true;
    loading.value = false;
    return;
  }

  try {
    const r = await apiGet("Operation", name);
    if (r) {
      if (!r.sub_operations) r.sub_operations = [];
      ensureSubUids(r.sub_operations);
      doc.value = r;
      // Keep an already-set-but-now-inactive workstation selectable, so the
      // saved value doesn't silently vanish from the dropdown.
      if (r.default_workstation && !workstations.value.some(w => w.name === r.default_workstation)) {
        workstations.value = [{ name: r.default_workstation }, ...workstations.value];
      }
    }
  } catch (e) {
    toast("Could not load Operation", "error");
    router.push("/manufacturing/operation");
  }
  loading.value = false;
});

function addSubOp() {
  if (!doc.value.sub_operations) doc.value.sub_operations = [];
  doc.value.sub_operations.push({
    _uid: nextUid(),
    operation: "",
    operation_time: 0
  });
}

async function save() {
  if (!doc.value.operation_name) {
    toast("Operation Name is mandatory", "error");
    return;
  }
  saving.value = true;
  try {
    // Strip the client-only _uid before sending to the server.
    const payload = {
      ...doc.value,
      sub_operations: (doc.value.sub_operations || []).map(({ _uid, ...rest }) => rest),
    };
    const r = await apiSave(payload);
    toast("Saved successfully");
    if (!r.sub_operations) r.sub_operations = [];
    ensureSubUids(r.sub_operations);
    if (isNew.value) {
      router.replace(`/manufacturing/operation/${r.name}`);
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
};
function icon(name, size) {
  return (ICONS[name] || "").replace("<svg ", `<svg width="${size}" height="${size}" `);
}
</script>

<style scoped>
@keyframes spin { to { transform: rotate(360deg) } }

/* ── Page ──────────────────────────────────────────────────────────── */
.sc-page {
  background: #f0f2f5;
  padding-bottom: 32px;
  min-height: 100vh;
}

/* ── Sticky ────────────────────────────────────────────────────────── */
.sc-sticky {
  position: sticky;
  top: 0;
  z-index: 20;
  background: #f0f2f5;
}
.sc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 24px 0;
  margin-bottom: 24px;
}
.sc-title {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a2e;
  letter-spacing: -0.3px;
}
.sc-save-btn {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 13.5px;
  font-weight: 600;
  padding: 9px 20px;
  border-radius: 9px;
  background: linear-gradient(135deg, #2f74f5 0%, #1a6ef7 100%);
  border: none;
  color: #fff;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(26,110,247,.28), inset 0 1px 0 rgba(255,255,255,.18);
  transition: box-shadow .18s ease, transform .18s ease, filter .18s ease;
}
.sc-save-btn:hover:not(:disabled) {
  filter: brightness(1.04);
  box-shadow: 0 6px 18px rgba(26,110,247,.36), inset 0 1px 0 rgba(255,255,255,.2);
  transform: translateY(-1px);
}
.sc-save-btn:active:not(:disabled) { transform: translateY(0); box-shadow: 0 2px 8px rgba(26,110,247,.3); }

/* ── Body layouts ──────────────────────────────────────────────────── */
.sc-body {
  padding: 24px;
  display: grid;
  gap: 20px;
  align-content: start;
}
.sc-body--narrow { max-width: 900px; margin: 0 auto; }
.sc-col-main { display: grid; gap: 20px; align-content: start; }

/* ── Cards ─────────────────────────────────────────────────────────── */
.sc-card {
  background: #fff;
  border: 1px solid #e8ecf2;
  border-radius: 14px;
  padding: 22px 24px;
  box-shadow: 0 1px 2px rgba(16,24,40,.04), 0 1px 3px rgba(16,24,40,.03);
  transition: box-shadow .2s ease, transform .2s ease, border-color .2s ease;
}
.sc-card:hover {
  box-shadow: 0 6px 20px rgba(16,24,40,.07), 0 2px 6px rgba(16,24,40,.04);
  border-color: #dbe3ee;
  transform: translateY(-1px);
}
.sc-card-header { display: flex; align-items: center; gap: 14px; }
.sc-card-icon {
  width: 40px; height: 40px; border-radius: 11px;
  background: linear-gradient(135deg, #eaf1ff 0%, #dbe7ff 100%);
  color: #2563eb; display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; box-shadow: inset 0 0 0 1px rgba(37,99,235,.08), 0 2px 6px rgba(37,99,235,.12);
}
.sc-card-icon--blue { background: linear-gradient(135deg, #eaf1ff 0%, #dbe7ff 100%); color: #2563eb; }
.sc-card-title { font-size: 14px; font-weight: 700; color: #111827; }
.sc-card-subtitle { font-size: 12px; color: #9ca3af; margin-top: 2px; }
.sc-divider { height: 1px; background: #f3f4f6; margin: 18px 0; }
.sc-required { color: #dc2626; }

/* ── Form grid ─────────────────────────────────────────────────────── */
.sc-fg { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.sc-fg--single { grid-template-columns: 1fr; }
.sc-fg--three  { grid-template-columns: 1fr 1fr 1fr; }

.sc-input--readonly { background: #f8fafc; color: #475569; cursor: default; }
.sc-input--readonly:focus { border-color: #e4e8f0; box-shadow: none; }
.sc-field-hint {
  display: flex; align-items: center; gap: 5px; margin-top: 5px; font-size: 12px; color: #6b7280;
}

.sc-upload-btn {
  display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px;
  border: 1.5px solid #2563eb; border-radius: 8px; background: #fff;
  color: #2563eb; font-size: 12.5px; font-weight: 600; cursor: pointer; transition: background .15s; white-space: nowrap;
}
.sc-upload-btn:hover { background: #eff6ff; }

/* Global nim styles used inside this component for form fields */
.nim-field { display: flex; flex-direction: column; gap: 6px; }
.nim-label { font-size: 13px; font-weight: 600; color: #374151; }
.nim-input {
  border: 1px solid #d1d5db; border-radius: 8px; padding: 10px 14px;
  font-size: 14px; color: #111827; outline: none; transition: border-color .15s, box-shadow .15s;
  background: #fff;
}
.nim-input:focus { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,.1); }

@media (max-width: 600px) {
  .sc-fg, .sc-fg--three { grid-template-columns: 1fr; }
}

/* Base button override specifically for row deletion in tables */
.inv-act-btn { background: none; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; padding: 4px; border-radius: 6px; transition: background .15s; }
.inv-act-btn:hover { background: #fee2e2; }
</style>