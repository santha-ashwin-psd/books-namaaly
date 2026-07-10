<template>
<div class="psv-page">
  <div class="psv-sticky">
    <div class="psv-header">
      <div style="display:flex;align-items:center;gap:12px;">
        <button class="psv-back" @click="router.push('/manufacturing/packing-slip')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
          Back
        </button>
        <span class="psv-title">{{ isNew ? 'New Packing Slip' : ps.name }}</span>
        <div v-if="!isNew" class="psv-badge" :style="statusStyle">{{ ps.status }}</div>
      </div>
      <div style="display:flex;gap:10px;">
        <button class="psv-btn-outline" @click="router.push('/manufacturing/packing-slip')" :disabled="saving">Back</button>
        <button v-if="!isNew && ps.status!=='Cancelled'" class="psv-btn-danger" @click="cancelPS" :disabled="saving">Cancel</button>
        <button v-if="!isNew && ps.status==='In Progress'" class="psv-btn-success" @click="markPacked" :disabled="saving">Mark as Packed</button>
        <button class="psv-btn-primary" @click="save" :disabled="saving||loading">
          <span v-if="saving" class="psv-spinner"></span>
          {{ isNew ? 'Save Packing Slip' : 'Save Changes' }}
        </button>
      </div>
    </div>
  </div>

  <div class="psv-body">

    <!-- Header Card -->
    <div class="psv-card">
      <div class="psv-card-title">Packing Details</div>
      <div class="psv-divider"></div>
      <div class="psv-grid">
        <div class="psv-field">
          <label class="psv-label">Work Order <span class="psv-req">*</span></label>
          <select class="psv-input" v-model="ps.work_order" @change="onWOChange" :disabled="!isNew">
            <option value="">— Select —</option>
            <option v-for="w in workOrderList" :key="w.name" :value="w.name">{{ w.name }} — {{ w.production_item }}</option>
          </select>
        </div>
        <div class="psv-field">
          <label class="psv-label">Item Being Packed</label>
          <input class="psv-input" :value="ps.production_item || '—'" disabled />
        </div>
        <div class="psv-field">
          <label class="psv-label">Packing BOM</label>
          <input class="psv-input" :value="ps.bom || '—'" disabled />
        </div>
        <div class="psv-field">
          <label class="psv-label">Qty to Pack</label>
          <input type="number" class="psv-input" v-model="ps.qty_to_pack" min="0.001" step="any" :disabled="readOnly" />
        </div>
        <div class="psv-field">
          <label class="psv-label">Packing Date</label>
          <input type="date" class="psv-input" v-model="ps.packing_date" :disabled="readOnly" />
        </div>
        <div class="psv-field">
          <label class="psv-label">Packed By</label>
          <input class="psv-input" v-model="ps.packed_by" :disabled="readOnly" />
        </div>
      </div>
    </div>

    <!-- Items Card -->
    <div class="psv-card" style="overflow-x:auto;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
        <div class="psv-card-title">Items to Pack</div>
        <div style="display:flex;gap:8px;">
          <button v-if="!readOnly && ps.work_order" class="psv-btn-outline" style="font-size:12px;padding:5px 12px;" @click="loadItemsFromWO" :disabled="itemsLoading">
            {{ itemsLoading ? 'Loading…' : '↻ Reload from WO' }}
          </button>
          <button v-if="!readOnly" class="psv-btn-outline" style="font-size:12px;padding:5px 12px;" @click="addItem">+ Add Row</button>
        </div>
      </div>
      <div class="psv-divider"></div>
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead>
          <tr>
            <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-size:12px;font-weight:600;">Item</th>
            <th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-size:12px;font-weight:600;">Required Qty</th>
            <th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-size:12px;font-weight:600;">Packed Qty</th>
            <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-size:12px;font-weight:600;">UOM</th>
            <th v-if="!readOnly" style="width:36px;border-bottom:1px solid #e5e7eb;"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!ps.items || !ps.items.length">
            <td colspan="5" style="text-align:center;padding:24px;color:#9ca3af;">No items. Select a Work Order and click "Reload from WO".</td>
          </tr>
          <tr v-for="(row, idx) in ps.items" :key="idx" style="border-bottom:1px solid #f3f4f6;"
            :style="flt(row.packed_qty) >= flt(row.required_qty) - 0.001 && flt(row.required_qty) > 0 ? 'background:#f0fdf4;' : ''">
            <td style="padding:6px;">
              <select class="psv-input" style="padding:6px 10px;" v-model="row.item_code" :disabled="readOnly">
                <option value="">— Select —</option>
                <option v-for="i in itemsList" :key="i.name" :value="i.name">{{ i.item_name || i.name }}</option>
              </select>
            </td>
            <td style="padding:6px;"><input type="number" class="psv-input" style="padding:6px 10px;text-align:right;" v-model="row.required_qty" step="any" :disabled="readOnly" /></td>
            <td style="padding:6px;">
              <input type="number" class="psv-input" style="padding:6px 10px;text-align:right;" v-model="row.packed_qty" min="0" step="any"
                :style="flt(row.packed_qty) > flt(row.required_qty) ? 'border-color:#dc2626;' : ''" />
            </td>
            <td style="padding:6px;">
              <select class="psv-input" style="padding:6px 10px;" v-model="row.uom" :disabled="readOnly">
                <option value="">—</option>
                <option v-for="u in uomList" :key="u.name" :value="u.name">{{ u.name }}</option>
              </select>
            </td>
            <td v-if="!readOnly" style="padding:6px;text-align:center;">
              <button @click="ps.items.splice(idx,1)" style="background:none;border:none;color:#dc2626;cursor:pointer;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Progress summary -->
      <div v-if="ps.items && ps.items.length" style="padding:12px 8px;border-top:1px solid #f3f4f6;display:flex;gap:24px;font-size:13px;color:#6b7280;">
        <span><strong style="color:#111827;">{{ packedCount }}</strong> / {{ ps.items.length }} items fully packed</span>
        <span v-if="ps.status === 'Packed'" style="color:#16a34a;font-weight:600;">✓ All items packed</span>
      </div>
    </div>

    <!-- Remarks -->
    <div class="psv-card">
      <div class="psv-card-title">Remarks</div>
      <div class="psv-divider"></div>
      <textarea class="psv-input" rows="3" v-model="ps.remarks"></textarea>
    </div>

    <!-- Linked Work Order shortcut -->
    <div v-if="!isNew && ps.work_order" class="psv-card" style="display:flex;align-items:center;justify-content:space-between;">
      <div>
        <div class="psv-card-title" style="margin-bottom:4px;">Linked Work Order</div>
        <div style="font-size:13px;color:#6b7280;">{{ ps.work_order }}</div>
      </div>
      <button class="psv-btn-outline" @click="router.push(`/manufacturing/work-order/${ps.work_order}`)">Open Work Order ↗</button>
    </div>

  </div>
</div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet, apiSave, apiList, apiCall, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";

const ENGINE = "zoho_books_clone.manufacturing.packing_engine.";

const route = useRoute();
const router = useRouter();
const { toast } = useToast();

const isNew = computed(() => route.params.name === "new");
const loading = ref(true);
const saving = ref(false);
const itemsLoading = ref(false);

const ps = ref({
  doctype: "Packing Slip",
  work_order: "",
  production_item: "",
  bom: "",
  status: "Draft",
  qty_to_pack: 1,
  packing_date: new Date().toISOString().slice(0, 10),
  packed_by: "",
  items: [],
  remarks: "",
});

const workOrderList = ref([]);
const itemsList = ref([]);
const uomList = ref([]);

const readOnly = computed(() => !isNew.value && ps.value.status === "Packed");
const packedCount = computed(() =>
  (ps.value.items || []).filter(r => flt(r.packed_qty) >= flt(r.required_qty) - 0.0001 && flt(r.required_qty) > 0).length
);

const statusStyle = computed(() => {
  const s = ps.value.status;
  if (s === "Packed") return "background:#dcfce7;color:#16a34a;";
  if (s === "In Progress") return "background:#dbeafe;color:#1e40af;";
  if (s === "Cancelled") return "background:#fee2e2;color:#dc2626;";
  return "background:#fef3c7;color:#b45309;";
});

onMounted(async () => {
  loading.value = true;
  try {
    const co = await resolveCompany();

    const [wos, items, uoms] = await Promise.all([
      apiList("Work Order", {
        fields: ["name", "production_item", "bom", "status", "qty", "produced_qty"],
        filters: [["docstatus", "=", 1], ["status", "!=", "Cancelled"]],
        limit: 500,
        order: "name desc",
      }),
      apiList("Item", { fields: ["name", "item_name", "stock_uom"], limit: 5000, order: "name asc" }),
      apiList("UOM", { fields: ["name"], limit: 200, order: "name asc" }),
    ]);

    workOrderList.value = wos || [];
    itemsList.value = items || [];
    uomList.value = uoms || [];

    if (!isNew.value) await loadPS();
  } catch (e) {
    toast("Error loading data: " + e.message, "error");
  }
  loading.value = false;
});

async function loadPS() {
  const data = await apiGet("Packing Slip", route.params.name);
  ps.value = data;
  if (!ps.value.items) ps.value.items = [];
}

watch(() => route.params.name, () => {
  loadPS().catch(e => toast(e.message, "error"));
});

async function onWOChange() {
  const wo = workOrderList.value.find(w => w.name === ps.value.work_order);
  if (wo) {
    ps.value.production_item = wo.production_item || "";
    ps.value.bom = wo.bom || "";
    ps.value.qty_to_pack = Math.max(0, flt(wo.qty) - flt(wo.produced_qty));
    await loadItemsFromWO();
  }
}

async function loadItemsFromWO() {
  if (!ps.value.work_order) return;
  const wo = workOrderList.value.find(w => w.name === ps.value.work_order);
  if (!wo || !wo.bom) return toast("No BOM found on the selected Work Order", "error");
  itemsLoading.value = true;
  try {
    const breakdown = await apiCall(
      "zoho_books_clone.manufacturing.work_order_engine.get_bom_breakdown",
      { bom: wo.bom, qty: flt(ps.value.qty_to_pack) || flt(wo.qty) || 1 }
    );
    ps.value.items = (breakdown.items || []).map(r => ({
      item_code: r.item_code,
      item_name: r.item_name || "",
      required_qty: r.required_qty,
      packed_qty: 0,
      uom: r.uom || "",
    }));
    if (!ps.value.items.length) {
      toast("No materials found in BOM. Make sure the Packing BOM has packing materials.", "error");
    }
  } catch (e) {
    toast(e.message, "error");
  }
  itemsLoading.value = false;
}

function addItem() {
  ps.value.items.push({ item_code: "", item_name: "", required_qty: 1, packed_qty: 0, uom: "" });
}

async function save() {
  if (!ps.value.work_order) return toast("Select a Work Order", "error");
  if (!ps.value.items.length) return toast("Add at least one item", "error");
  saving.value = true;
  try {
    const doc = await apiSave(ps.value);
    toast(isNew.value ? "Packing Slip created" : "Packing Slip updated");
    if (isNew.value) {
      router.replace(`/manufacturing/packing-slip/${doc.name}`);
    } else {
      ps.value = doc;
    }
  } catch (e) {
    toast(e.message, "error");
  }
  saving.value = false;
}

async function markPacked() {
  saving.value = true;
  try {
    ps.value.status = "Packed";
    for (const row of ps.value.items) {
      if (flt(row.packed_qty) < flt(row.required_qty)) {
        row.packed_qty = row.required_qty;
      }
    }
    const doc = await apiSave(ps.value);
    ps.value = doc;
    toast("Packing Slip marked as Packed");
  } catch (e) {
    toast(e.message, "error");
  }
  saving.value = false;
}

async function cancelPS() {
  if (!confirm("Cancel this Packing Slip?")) return;
  saving.value = true;
  try {
    ps.value.status = "Cancelled";
    const doc = await apiSave(ps.value);
    ps.value = doc;
    toast("Packing Slip cancelled");
  } catch (e) {
    toast(e.message, "error");
  }
  saving.value = false;
}

function flt(n) { const v = parseFloat(n); return isNaN(v) ? 0 : v; }
</script>

<style scoped>
@keyframes spin { to { transform: rotate(360deg) } }
.psv-spinner { display:inline-block;width:11px;height:11px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .6s linear infinite;margin-right:6px; }

.psv-page { background:#f0f2f5;min-height:100vh;padding-bottom:32px; }
.psv-sticky { position:sticky;top:0;z-index:20;background:#f0f2f5; }
.psv-header { display:flex;align-items:center;justify-content:space-between;gap:12px;padding:18px 24px 14px; }
.psv-title { font-size:20px;font-weight:700;color:#1a1a2e; }
.psv-badge { font-size:12px;padding:3px 8px;border-radius:12px;font-weight:600; }
.psv-back { background:none;border:none;cursor:pointer;color:#2563eb;display:flex;align-items:center;gap:4px;font-weight:600;font-size:13px;padding:0; }
.psv-body { padding:24px;max-width:920px;margin:0 auto;display:grid;gap:20px;align-content:start; }

.psv-card { background:#fff;border:1px solid #e8ecf2;border-radius:14px;padding:22px 24px;box-shadow:0 1px 2px rgba(16,24,40,.04); }
.psv-card-title { font-size:14px;font-weight:700;color:#111827; }
.psv-divider { height:1px;background:#f3f4f6;margin:14px 0; }

.psv-grid { display:grid;grid-template-columns:1fr 1fr;gap:14px; }
.psv-field { display:flex;flex-direction:column;gap:6px; }
.psv-label { font-size:13px;font-weight:600;color:#374151; }
.psv-req { color:#dc2626; }

.psv-input { border:1px solid #d1d5db;border-radius:8px;padding:10px 14px;font-size:14px;color:#111827;outline:none;transition:border-color .15s;background:#fff;width:100%;box-sizing:border-box; }
.psv-input:focus { border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.1); }
.psv-input:disabled { background:#f8fafc;color:#6b7280;cursor:default; }

.psv-btn-primary { display:flex;align-items:center;gap:6px;font-size:13.5px;font-weight:600;padding:9px 20px;border-radius:9px;background:linear-gradient(135deg,#2f74f5,#1a6ef7);border:none;color:#fff;cursor:pointer; }
.psv-btn-primary:disabled { opacity:.6;cursor:not-allowed; }
.psv-btn-outline { padding:8px 16px;border-radius:8px;background:#fff;border:1px solid #e5e7eb;font-weight:600;cursor:pointer;font-size:13px; }
.psv-btn-danger { padding:8px 16px;border-radius:8px;background:#fee2e2;color:#dc2626;border:1px solid #fecaca;font-weight:600;cursor:pointer;font-size:13px; }
.psv-btn-success { padding:8px 16px;border-radius:8px;background:#dcfce7;color:#16a34a;border:1px solid #86efac;font-weight:600;cursor:pointer;font-size:13px; }

@media (max-width:600px) { .psv-grid { grid-template-columns:1fr; } }
</style>
