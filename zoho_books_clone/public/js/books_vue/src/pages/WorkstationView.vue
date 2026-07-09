<template>
<div class="sc-page">
  <div class="sc-sticky">
    <div class="sc-header">
      <div style="display:flex;align-items:center;gap:12px;">
        <button class="iv-back" @click="router.push('/manufacturing/workstation')" style="background:none;border:none;cursor:pointer;color:#2563eb;display:flex;align-items:center;gap:4px;font-weight:600;font-size:13px;padding:0;">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
          Back
        </button>
        <span class="sc-title">{{ isNew ? 'New Workstation' : doc.workstation_name }}</span>
        <div v-if="!isNew" class="inv-status-badge" :class="doc.is_active?'status-active':'status-inactive'" style="font-size:12px;padding:3px 8px;border-radius:12px;" :style="doc.is_active?'background:#dcfce7;color:#16a34a':'background:#fee2e2;color:#dc2626'">
          {{ doc.is_active ? 'Active' : 'Inactive' }}
        </div>
      </div>
      <div style="display:flex;gap:10px;">
        <button class="nim-btn" style="background:#fff;border:1px solid #e5e7eb;padding:8px 16px;border-radius:8px;font-weight:600;cursor:pointer;" @click="router.push('/manufacturing/workstation')" :disabled="saving">Cancel</button>
        <button class="sc-save-btn" @click="save" :disabled="saving || loading">
          <span v-if="saving" style="display:inline-block;width:12px;height:12px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .6s linear infinite;margin-right:6px;"></span>
          {{ isNew ? 'Save' : 'Save Changes' }}
        </button>
      </div>
    </div>
    <div class="sc-tabs">
      <button v-for="t in tabs" :key="t.id"
        class="sc-tab" :class="{ 'sc-tab--active': activeTab === t.id }"
        @click="activeTab = t.id">
        {{ t.label }}
      </button>
    </div>
  </div>

  <div v-if="loading" class="sc-body sc-body--narrow">
    <div class="sc-col-main">
      <div class="sc-card"><div class="shimmer" style="height:160px"></div></div>
    </div>
  </div>

  <div v-if="!loading && activeTab === 'details'" class="sc-body sc-body--narrow">
    <div class="sc-col-main">
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>
          </div>
          <div>
            <div class="sc-card-title">Workstation Details</div>
            <div class="sc-card-subtitle">General information and capacities.</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        
        <div class="sc-fg" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Workstation Name <span class="sc-required">*</span></label>
            <input type="text" class="nim-input" v-model="doc.workstation_name" :disabled="!isNew" placeholder="e.g., Assembly Station 1" />
          </div>
          <div class="nim-field">
            <label class="nim-label">Job Capacity</label>
            <input type="number" class="nim-input" v-model.number="doc.capacity" min="1" step="any" />
            <div class="sc-field-hint">Run parallel job cards in a workstation.</div>
          </div>
        </div>
        
        <div class="sc-fg" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Workstation Type <span class="sc-required">*</span></label>
            <select class="nim-input" v-model="doc.workstation_type">
              <option value="">— Select Workstation Type —</option>
              <option v-for="t in types" :key="t.name" :value="t.name">{{ t.name }}</option>
            </select>
          </div>
          <div class="nim-field">
            <label class="nim-label">Warehouse</label>
            <select class="nim-input" v-model="doc.warehouse">
              <option value="">— Select Warehouse —</option>
              <option v-for="w in warehouses" :key="w.name" :value="w.name">{{ w.warehouse_name || w.name }}</option>
            </select>
          </div>
        </div>

        <div class="sc-fg sc-fg--single" style="margin-bottom:14px">
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

  <div v-if="!loading && activeTab === 'costs'" class="sc-body sc-body--narrow">
    <div class="sc-col-main">
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>
          </div>
          <div>
            <div class="sc-card-title">Operating Costs</div>
            <div class="sc-card-subtitle">Cost to run this workstation per hour.</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-fg sc-fg--single" style="margin-bottom:14px">
          <div class="nim-field" style="max-width:300px;">
            <label class="nim-label">Hourly Operating Cost <span class="sc-required">*</span></label>
            <div style="position:relative">
              <span style="position:absolute;left:12px;top:9px;color:#6b7280;font-weight:600">₹</span>
              <input type="number" class="nim-input" v-model.number="doc.hour_rate" min="0" step="any" style="padding-left:26px" />
            </div>
            <div class="sc-field-hint">Used for calculating manufacturing costs.</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div v-if="!loading && activeTab === 'hours'" class="sc-body sc-body--narrow">
    <div class="sc-col-main">
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
          </div>
          <div>
            <div class="sc-card-title">Working Hours</div>
            <div class="sc-card-subtitle">Availability for production planning.</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-fg sc-fg--single" style="margin-bottom:14px">
          <div class="nim-field" style="max-width:300px;">
            <label class="nim-label">Working Hours Per Day</label>
            <input type="number" class="nim-input" v-model.number="doc.working_hours_per_day" min="0" max="24" step="any" />
          </div>
        </div>
      </div>
    </div>
  </div>

  <div v-if="!loading && activeTab === 'desc'" class="sc-body sc-body--narrow">
    <div class="sc-col-main">
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="6" x2="20" y2="6"></line><line x1="4" y1="12" x2="20" y2="12"></line><line x1="4" y1="18" x2="12" y2="18"></line></svg>
          </div>
          <div>
            <div class="sc-card-title">Description</div>
            <div class="sc-card-subtitle">Internal notes or specs.</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-fg sc-fg--single" style="margin-bottom:14px">
          <div class="nim-field">
            <textarea class="nim-input" style="min-height:120px;resize:vertical;" v-model="doc.description" placeholder="Description of the workstation..."></textarea>
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

const activeTab = ref('details');
const tabs = [
  { id: 'details', label: 'Details' },
  { id: 'costs', label: 'Operating Costs' },
  { id: 'hours', label: 'Working Hours' },
  { id: 'desc', label: 'Description' }
];

const doc = ref({
  doctype: "Workstation",
  workstation_name: "",
  workstation_type: "",
  warehouse: "",
  capacity: 1,
  working_hours_per_day: 8,
  hour_rate: 0,
  description: "",
  is_active: 1
});

const types = ref([]);
const warehouses = ref([]);

onMounted(async () => {
  loading.value = true;
  
  // Fetch active workstation types and warehouses
  try {
    types.value = await apiList("Workstation Type", { fields: ["name", "is_active"], filters: [["is_active", "=", 1]], limit: 1000 }) || [];
    warehouses.value = await apiList("Warehouse", { fields: ["name", "warehouse_name"], limit: 1000 }) || [];
  } catch (e) {
    toast("Could not load Workstation Types / Warehouses — some dropdowns may be empty", "error");
  }

  const name = route.params.name;
  if (name === 'new') {
    isNew.value = true;
    loading.value = false;
    return;
  }
  
  try {
    const r = await apiGet("Workstation", name);
    if (r) {
      doc.value = r;
      // Keep an already-set-but-now-inactive workstation type selectable, so
      // the saved value doesn't silently vanish from the dropdown.
      if (r.workstation_type && !types.value.some(t => t.name === r.workstation_type)) {
        types.value = [{ name: r.workstation_type }, ...types.value];
      }
    }
  } catch (e) {
    toast("Could not load Workstation", "error");
    router.push("/manufacturing/workstation");
  }
  loading.value = false;
});

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
    toast("Saved successfully");
    if (isNew.value) {
      router.replace(`/manufacturing/workstation/${r.name}`);
      isNew.value = false;
      doc.value = r;
    } else {
      doc.value = r;
    }
  } catch (e) {
    toast(e.message || "Could not save", "error");
  }
  saving.value = false;
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

/* ── Tabs ──────────────────────────────────────────────────────────── */
.sc-tabs {
  display: flex;
  border-bottom: 2px solid #e4e8f0;
  padding: 0 24px;
  margin-top: 14px;
  overflow-x: auto;
  scrollbar-width: none;
}
.sc-tabs::-webkit-scrollbar { display: none; }
.sc-tab {
  padding: 10px 18px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: #868e96;
  white-space: nowrap;
  border-bottom: 2px solid transparent;
  border-radius: 8px 8px 0 0;
  margin-bottom: -2px;
  transition: color .15s, background .15s;
}
.sc-tab:hover { color: #374151; background: rgba(37,99,235,.05); }
.sc-tab--active { color: #2563eb; border-bottom-color: #2563eb; background: linear-gradient(180deg, rgba(37,99,235,.06), rgba(37,99,235,0)); }

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
  .sc-tabs { mask-image: linear-gradient(to right, transparent 0, black 16px, black calc(100% - 16px), transparent 100%); -webkit-mask-image: linear-gradient(to right, transparent 0, black 16px, black calc(100% - 16px), transparent 100%); }
}
</style>