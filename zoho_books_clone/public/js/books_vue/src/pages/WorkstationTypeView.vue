<template>
<div class="sc-page">
  <div class="sc-sticky">
    <div class="sc-header">
      <div style="display:flex;align-items:center;gap:12px;">
        <button class="iv-back" @click="router.push('/manufacturing/workstation-type')" style="background:none;border:none;cursor:pointer;color:#2563eb;display:flex;align-items:center;gap:4px;font-weight:600;font-size:13px;padding:0;">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
          Back
        </button>
        <span class="sc-title">{{ isNew ? 'New Workstation Type' : doc.workstation_type_name }}</span>
        <div v-if="!isNew" class="inv-status-badge" :class="doc.is_active?'status-active':'status-inactive'" style="font-size:12px;padding:3px 8px;border-radius:12px;" :style="doc.is_active?'background:#dcfce7;color:#16a34a':'background:#fee2e2;color:#dc2626'">
          {{ doc.is_active ? 'Active' : 'Inactive' }}
        </div>
      </div>
      <div style="display:flex;gap:10px;">
        <button class="nim-btn" style="background:#fff;border:1px solid #e5e7eb;padding:8px 16px;border-radius:8px;font-weight:600;cursor:pointer;" @click="router.push('/manufacturing/workstation-type')" :disabled="saving">Cancel</button>
        <button class="sc-save-btn" @click="save" :disabled="saving || loading">
          <span v-if="saving" style="display:inline-block;width:12px;height:12px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .6s linear infinite;margin-right:6px;"></span>
          {{ isNew ? 'Save' : 'Save Changes' }}
        </button>
      </div>
    </div>
  </div>

  <div v-if="loading" class="sc-body sc-body--narrow">
    <div class="sc-col-main">
      <div class="sc-card"><div class="shimmer" style="height:160px"></div></div>
    </div>
  </div>

  <div v-else class="sc-body sc-body--narrow">
    <div class="sc-col-main">
      
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>
          </div>
          <div>
            <div class="sc-card-title">Workstation Type Details</div>
            <div class="sc-card-subtitle">General information and categorization.</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        
        <div class="sc-fg sc-fg--single" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Type Name <span class="sc-required">*</span></label>
            <input type="text" class="nim-input" v-model="doc.workstation_type_name" :disabled="!isNew" placeholder="e.g., Assembly Line" />
            <div class="sc-field-hint" v-if="!isNew">Name cannot be changed after creation.</div>
          </div>
        </div>

        <div class="sc-fg sc-fg--single" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Icon</label>
            <input type="text" class="nim-input" v-model="doc.icon" placeholder="e.g., an icon name or emoji" />
            <div class="sc-field-hint">Optional. Shown alongside this type where used.</div>
          </div>
        </div>

        <div class="sc-fg sc-fg--single" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Description</label>
            <textarea class="nim-input" style="min-height:80px;resize:vertical;" v-model="doc.description" placeholder="Briefly describe this workstation type..."></textarea>
          </div>
        </div>

        <div class="sc-fg sc-fg--single" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="sc-toggle-row" style="padding:8px;background:none;">
              <input type="checkbox" v-model="doc.is_active" :true-value="1" :false-value="0" style="margin-right:8px;"/> 
              <span style="font-size:13px;font-weight:600;">Is Active</span>
            </label>
            <div class="sc-field-hint" style="margin-left:24px;">Inactive types cannot be assigned to new workstations.</div>
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
import { apiGet, apiSave } from '../api/client.js';
import { useToast } from '../composables/useToast.js';

const route = useRoute();
const router = useRouter();
const { toast } = useToast();

const isNew = ref(false);
const loading = ref(false);
const saving = ref(false);

const doc = ref({
  doctype: "Workstation Type",
  workstation_type_name: "",
  description: "",
  icon: "",
  is_active: 1
});

onMounted(async () => {
  const name = route.params.name;
  if (name === 'new') {
    isNew.value = true;
    return;
  }
  loading.value = true;
  try {
    const r = await apiGet("Workstation Type", name);
    if (r) doc.value = r;
  } catch (e) {
    toast("Could not load Workstation Type", "error");
    router.push("/manufacturing/workstation-type");
  }
  loading.value = false;
});

async function save() {
  if (!doc.value.workstation_type_name) {
    toast("Workstation Type Name is mandatory", "error");
    return;
  }
  saving.value = true;
  try {
    const r = await apiSave(doc.value);
    toast("Saved successfully");
    if (isNew.value) {
      router.replace(`/manufacturing/workstation-type/${r.name}`);
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