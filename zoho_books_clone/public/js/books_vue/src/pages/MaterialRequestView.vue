<template>
<div class="mrv-page">
  <div class="mrv-sticky">
    <div class="mrv-header">
      <div style="display:flex;align-items:center;gap:12px;">
        <button class="mrv-back" @click="router.push('/manufacturing/material-request')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
          Back
        </button>
        <span class="mrv-title">{{ isNew ? 'New Material Request' : mr.name }}</span>
        <div v-if="!isNew" class="mrv-badge" :style="statusStyle">{{ mr.status }}</div>
      </div>
      <div style="display:flex;gap:10px;">
        <button class="mrv-btn-outline" @click="router.push('/manufacturing/material-request')" :disabled="saving||submitting">Back</button>
        <button v-if="!isNew && mr.docstatus===2" class="mrv-btn-primary" @click="amendMR" :disabled="submitting">{{ submitting ? 'Amending…' : 'Amend' }}</button>
        <button v-if="!isNew && mr.docstatus===1" class="mrv-btn-danger" @click="cancelMR" :disabled="submitting">{{ submitting ? 'Cancelling…' : 'Cancel' }}</button>
        <button v-if="!isNew && mr.docstatus===0" class="mrv-btn-primary" @click="submitMR" :disabled="submitting||saving">{{ submitting ? 'Submitting…' : 'Submit' }}</button>
        <button v-if="!readOnly" class="mrv-btn-primary" @click="save" :disabled="saving||loading">
          <span v-if="saving" class="mrv-spinner"></span>
          {{ isNew ? 'Save Material Request' : 'Save Changes' }}
        </button>
      </div>
    </div>
  </div>

  <div class="mrv-body">

    <!-- Details Card -->
    <div class="mrv-card">
      <div class="mrv-card-title">Request Details</div>
      <div class="mrv-divider"></div>
      <div class="mrv-grid">
        <div class="mrv-field">
          <label class="mrv-label">Purpose <span class="mrv-req">*</span></label>
          <select class="mrv-input" v-model="mr.material_request_type" :disabled="readOnly">
            <option value="Purchase">Purchase</option>
            <option value="Material Transfer">Material Transfer</option>
          </select>
        </div>
        <div class="mrv-field">
          <label class="mrv-label">Required By <span class="mrv-req">*</span></label>
          <input type="date" class="mrv-input" v-model="mr.posting_date" :disabled="readOnly" />
        </div>
        <div class="mrv-field">
          <label class="mrv-label">Company</label>
          <select class="mrv-input" v-model="mr.company" :disabled="readOnly">
            <option value="">— Select —</option>
            <option v-for="c in companiesList" :key="c.name" :value="c.name">{{ c.name }}</option>
          </select>
        </div>
        <div class="mrv-field">
          <label class="mrv-label">Production Plan</label>
          <input class="mrv-input" :value="mr.production_plan || '—'" disabled />
          <div v-if="mr.production_plan" class="mrv-hint" style="cursor:pointer;color:#2563eb;" @click="router.push(`/manufacturing/production-plan/${mr.production_plan}`)">View Production Plan ↗</div>
        </div>
      </div>
    </div>

    <!-- Items Card -->
    <div class="mrv-card" style="overflow-x:auto;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
        <div class="mrv-card-title">Items</div>
        <button v-if="!readOnly" class="mrv-btn-outline" @click="addItem" style="font-size:12px;padding:5px 12px;">+ Add Row</button>
      </div>
      <div class="mrv-divider"></div>
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead>
          <tr>
            <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-size:12px;font-weight:600;">Item</th>
            <th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-size:12px;font-weight:600;">Required Qty</th>
            <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-size:12px;font-weight:600;">UOM</th>
            <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-size:12px;font-weight:600;">Warehouse</th>
            <th v-if="!readOnly" style="width:36px;border-bottom:1px solid #e5e7eb;"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!mr.items || !mr.items.length">
            <td colspan="5" style="text-align:center;padding:24px;color:#9ca3af;">No items yet. Add a row or create from Production Plan.</td>
          </tr>
          <tr v-for="(row, idx) in mr.items" :key="idx" style="border-bottom:1px solid #f3f4f6;">
            <td style="padding:6px;">
              <select class="mrv-input" style="padding:6px 10px;" v-model="row.item_code" @change="onItemChange(row)" :disabled="readOnly">
                <option value="">— Select Item —</option>
                <option v-for="i in itemsList" :key="i.name" :value="i.name">{{ i.item_name || i.name }}</option>
              </select>
            </td>
            <td style="padding:6px;">
              <input type="number" class="mrv-input" style="padding:6px 10px;text-align:right;" v-model="row.required_qty" min="0.001" step="any" :disabled="readOnly" />
            </td>
            <td style="padding:6px;">
              <select class="mrv-input" style="padding:6px 10px;" v-model="row.uom" :disabled="readOnly">
                <option value="">—</option>
                <option v-for="u in uomList" :key="u.name" :value="u.name">{{ u.name }}</option>
              </select>
            </td>
            <td style="padding:6px;">
              <select class="mrv-input" style="padding:6px 10px;" v-model="row.warehouse" :disabled="readOnly">
                <option value="">— None —</option>
                <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
              </select>
            </td>
            <td v-if="!readOnly" style="padding:6px;text-align:center;">
              <button @click="mr.items.splice(idx,1)" style="background:none;border:none;color:#dc2626;cursor:pointer;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg></button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Remarks -->
    <div class="mrv-card">
      <div class="mrv-card-title">Remarks</div>
      <div class="mrv-divider"></div>
      <textarea class="mrv-input" rows="3" v-model="mr.remarks" :disabled="readOnly"></textarea>
    </div>

  </div>
</div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet, apiSave, apiList, apiSubmit, apiCancel, apiAmend, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";

const route = useRoute();
const router = useRouter();
const { toast } = useToast();

const isNew = computed(() => route.params.name === "new");
const loading = ref(true);
const saving = ref(false);
const submitting = ref(false);

const mr = ref({
  doctype: "Material Request",
  material_request_type: "Purchase",
  status: "Draft",
  posting_date: new Date().toISOString().slice(0, 10),
  company: "",
  production_plan: "",
  items: [],
  remarks: "",
});

const companiesList = ref([]);
const itemsList = ref([]);
const uomList = ref([]);
const warehouseList = ref([]);

const readOnly = computed(() => !isNew.value && (mr.value.docstatus === 1 || mr.value.docstatus === 2));

const statusStyle = computed(() => {
  const s = mr.value.status;
  if (s === "Submitted" || s === "Ordered") return "background:#dcfce7;color:#16a34a;";
  if (s === "Cancelled") return "background:#fee2e2;color:#dc2626;";
  return "background:#fef3c7;color:#b45309;";
});

onMounted(async () => {
  loading.value = true;
  try {
    const co = await resolveCompany();

    [companiesList.value, itemsList.value, uomList.value] = await Promise.all([
      apiList("Company", { fields: ["name"], limit: 500 }),
      apiList("Item", { fields: ["name", "item_name", "stock_uom"], limit: 5000, order: "name asc" }),
      apiList("UOM", { fields: ["name"], limit: 200, order: "name asc" }),
    ]);
    companiesList.value = companiesList.value || [];
    itemsList.value = itemsList.value || [];
    uomList.value = uomList.value || [];

    const whs = await apiList("Warehouse", {
      fields: ["name"],
      filters: co ? [["company", "=", co], ["is_group", "=", 0]] : [["is_group", "=", 0]],
      limit: 1000,
    });
    warehouseList.value = whs || [];

    if (isNew.value) {
      mr.value.company = co || "";
    } else {
      await loadMR();
    }
  } catch (e) {
    toast("Error loading data: " + e.message, "error");
  }
  loading.value = false;
});

async function loadMR() {
  const data = await apiGet("Material Request", route.params.name);
  mr.value = data;
  if (!mr.value.items) mr.value.items = [];
}

watch(() => route.params.name, () => {
  loadMR().catch((e) => toast("Error: " + e.message, "error"));
});

function addItem() {
  mr.value.items.push({ item_code: "", item_name: "", required_qty: 1, uom: "", warehouse: "" });
}

function onItemChange(row) {
  const item = itemsList.value.find(i => i.name === row.item_code);
  row.item_name = item ? item.item_name : "";
  row.uom = item ? item.stock_uom : "";
}

async function save() {
  if (!mr.value.posting_date) return toast("Required By date is required", "error");
  if (!mr.value.items.length) return toast("Add at least one item", "error");
  for (const r of mr.value.items) {
    if (!r.item_code) return toast("Select an item for every row", "error");
    if (!r.required_qty || r.required_qty <= 0) return toast(`Required Qty must be > 0 for ${r.item_code}`, "error");
  }
  saving.value = true;
  try {
    const doc = await apiSave(mr.value);
    toast(isNew.value ? "Material Request created" : "Material Request updated");
    if (isNew.value) {
      router.replace(`/manufacturing/material-request/${doc.name}`);
    } else {
      mr.value = doc;
    }
  } catch (e) {
    toast(e.message, "error");
  }
  saving.value = false;
}

async function submitMR() {
  if (!mr.value.name) return;
  submitting.value = true;
  try {
    const doc = await apiSubmit("Material Request", mr.value.name);
    mr.value = doc;
    toast("Material Request submitted");
  } catch (e) { toast(e.message, "error"); }
  submitting.value = false;
}

async function cancelMR() {
  if (!confirm("Cancel this Material Request?")) return;
  submitting.value = true;
  try {
    const doc = await apiCancel("Material Request", mr.value.name);
    mr.value = doc;
    toast("Cancelled");
  } catch (e) { toast(e.message, "error"); }
  submitting.value = false;
}

async function amendMR() {
  submitting.value = true;
  try {
    const doc = await apiAmend("Material Request", mr.value.name);
    toast(`Revision ${doc.name} created`);
    router.push(`/manufacturing/material-request/${doc.name}`);
  } catch (e) { toast(e.message, "error"); }
  submitting.value = false;
}
</script>

<style scoped>
@keyframes spin { to { transform: rotate(360deg) } }
.mrv-spinner { display:inline-block;width:11px;height:11px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .6s linear infinite;margin-right:6px; }

.mrv-page { background:#f0f2f5;min-height:100vh;padding-bottom:32px; }
.mrv-sticky { position:sticky;top:0;z-index:20;background:#f0f2f5; }
.mrv-header { display:flex;align-items:center;justify-content:space-between;gap:12px;padding:18px 24px 0; }
.mrv-title { font-size:20px;font-weight:700;color:#1a1a2e; }
.mrv-badge { font-size:12px;padding:3px 8px;border-radius:12px;font-weight:600; }
.mrv-back { background:none;border:none;cursor:pointer;color:#2563eb;display:flex;align-items:center;gap:4px;font-weight:600;font-size:13px;padding:0; }
.mrv-body { padding:24px;max-width:900px;margin:0 auto;display:grid;gap:20px;align-content:start; }

.mrv-card { background:#fff;border:1px solid #e8ecf2;border-radius:14px;padding:22px 24px;box-shadow:0 1px 2px rgba(16,24,40,.04); }
.mrv-card-title { font-size:14px;font-weight:700;color:#111827; }
.mrv-divider { height:1px;background:#f3f4f6;margin:14px 0; }

.mrv-grid { display:grid;grid-template-columns:1fr 1fr;gap:14px; }
.mrv-field { display:flex;flex-direction:column;gap:6px; }
.mrv-label { font-size:13px;font-weight:600;color:#374151; }
.mrv-req { color:#dc2626; }
.mrv-hint { font-size:12px;color:#6b7280;margin-top:3px; }

.mrv-input { border:1px solid #d1d5db;border-radius:8px;padding:10px 14px;font-size:14px;color:#111827;outline:none;transition:border-color .15s;background:#fff;width:100%;box-sizing:border-box; }
.mrv-input:focus { border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.1); }
.mrv-input:disabled { background:#f8fafc;color:#6b7280;cursor:default; }

.mrv-btn-primary { display:flex;align-items:center;gap:6px;font-size:13.5px;font-weight:600;padding:9px 20px;border-radius:9px;background:linear-gradient(135deg,#2f74f5,#1a6ef7);border:none;color:#fff;cursor:pointer; }
.mrv-btn-primary:disabled { opacity:.6;cursor:not-allowed; }
.mrv-btn-outline { padding:8px 16px;border-radius:8px;background:#fff;border:1px solid #e5e7eb;font-weight:600;cursor:pointer;font-size:13px; }
.mrv-btn-danger { padding:8px 16px;border-radius:8px;background:#fee2e2;color:#dc2626;border:1px solid #fecaca;font-weight:600;cursor:pointer;font-size:13px; }

@media (max-width:600px) { .mrv-grid { grid-template-columns:1fr; } }
</style>
