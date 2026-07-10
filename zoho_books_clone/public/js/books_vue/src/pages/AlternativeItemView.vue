<template>
<div class="sc-page">
  <div class="sc-sticky">
    <div class="sc-header">
      <div style="display:flex;align-items:center;gap:12px;">
        <button class="iv-back" @click="router.push('/manufacturing/alternative-item')" style="background:none;border:none;cursor:pointer;color:#2563eb;display:flex;align-items:center;gap:4px;font-weight:600;font-size:13px;padding:0;">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
          Back
        </button>
        <span class="sc-title">{{ isNew ? 'New Alternative Item' : rec.name }}</span>
      </div>
      <div style="display:flex;gap:10px;">
        <button class="nim-btn" style="background:#fff;border:1px solid #e5e7eb;padding:8px 16px;border-radius:8px;font-weight:600;cursor:pointer;" @click="router.push('/manufacturing/alternative-item')">Cancel</button>
        <button v-if="!isNew" class="nim-btn" style="background:#fee2e2;color:#dc2626;border:1px solid #fecaca;padding:8px 16px;border-radius:8px;font-weight:600;cursor:pointer;" @click="deleteRec" :disabled="saving">Delete</button>
        <button class="sc-save-btn" @click="save" :disabled="saving || loading">{{ saving ? 'Saving…' : (isNew ? 'Save' : 'Update') }}</button>
      </div>
    </div>
  </div>

  <div v-if="loading" style="padding:60px;text-align:center;color:#9ca3af;">Loading…</div>
  <div v-else class="sc-body sc-body--narrow">
    <div class="sc-col-main">
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 3 21 3 21 8"></polyline><line x1="4" y1="20" x2="21" y2="3"></line><polyline points="21 16 21 21 16 21"></polyline><line x1="15" y1="15" x2="21" y2="21"></line></svg>
          </div>
          <div>
            <div class="sc-card-title">Alternative Item Mapping</div>
            <div class="sc-card-subtitle">Define a substitute item for use when the original is unavailable.</div>
          </div>
        </div>
        <div class="sc-divider"></div>

        <div class="sc-fg">
          <div class="nim-field">
            <label class="nim-label">Original Item <span class="sc-required">*</span></label>
            <select class="nim-input" v-model="rec.item_code" :disabled="!isNew">
              <option value="">— Select —</option>
              <option v-for="i in itemsList" :key="i.name" :value="i.name">{{ i.item_name || i.name }}</option>
            </select>
          </div>
          <div class="nim-field">
            <label class="nim-label">Alternative Item <span class="sc-required">*</span></label>
            <select class="nim-input" v-model="rec.alternative_item_code">
              <option value="">— Select —</option>
              <option v-for="i in itemsList" :key="i.name" :value="i.name">{{ i.item_name || i.name }}</option>
            </select>
          </div>
        </div>

        <div class="sc-fg" style="margin-top:14px;">
          <div class="nim-field">
            <label class="nim-label">Conversion Factor <span class="sc-required">*</span></label>
            <input type="number" class="nim-input" v-model="rec.conversion_factor" min="0.0001" step="any" />
            <div class="sc-field-hint">Qty of Alternative needed per 1 unit of Original.</div>
          </div>
          <div class="nim-field">
            <label class="nim-label">UOM</label>
            <select class="nim-input" v-model="rec.uom">
              <option value="">— None —</option>
              <option v-for="u in uomList" :key="u" :value="u">{{ u }}</option>
            </select>
          </div>
        </div>

        <div class="sc-fg sc-fg--single" style="margin-top:14px;">
          <label class="sc-toggle-row" style="padding:8px;background:none;"><input type="checkbox" v-model="rec.is_default" :true-value="1" :false-value="0" style="margin-right:8px;"/> <span style="font-size:13px;font-weight:600;">Mark as Default Substitute</span></label>
        </div>

        <div class="nim-field" style="margin-top:14px;">
          <label class="nim-label">Description / Reason</label>
          <textarea class="nim-input" rows="3" v-model="rec.description" placeholder="Why this is a valid alternative…"></textarea>
        </div>
      </div>
    </div>
  </div>
</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet, apiSave, apiList, apiCall } from "../api/client.js";
import { useToast } from "../composables/useToast.js";

const route = useRoute();
const router = useRouter();
const { toast } = useToast();

const isNew = computed(() => route.params.name === "new");
const loading = ref(true);
const saving = ref(false);

const rec = ref({
  doctype: "Alternative Item",
  item_code: "",
  alternative_item_code: "",
  conversion_factor: 1,
  uom: "",
  is_default: 0,
  description: "",
});

const itemsList = ref([]);
const uomList = ref([]);

onMounted(async () => {
  loading.value = true;
  try {
    const items = await apiList("Item", { fields: ["name", "item_name"], limit: 5000, order: "name asc" });
    itemsList.value = items || [];
    const uoms = await apiList("UOM", { fields: ["name"], limit: 200, order: "name asc" });
    uomList.value = (uoms || []).map(u => u.name);

    if (!isNew.value) {
      const data = await apiGet("Alternative Item", route.params.name);
      rec.value = data;
    }
  } catch (e) {
    toast("Error loading: " + e.message, "error");
    router.push("/manufacturing/alternative-item");
  }
  loading.value = false;
});

async function save() {
  if (!rec.value.item_code || !rec.value.alternative_item_code) {
    return toast("Original Item and Alternative Item are required", "error");
  }
  if (rec.value.item_code === rec.value.alternative_item_code) {
    return toast("Original and Alternative cannot be the same item", "error");
  }
  if (!rec.value.conversion_factor || rec.value.conversion_factor <= 0) {
    return toast("Conversion Factor must be greater than 0", "error");
  }
  saving.value = true;
  try {
    const doc = await apiSave(rec.value);
    toast(isNew.value ? "Alternative Item saved" : "Updated");
    if (isNew.value) {
      router.replace(`/manufacturing/alternative-item/${doc.name}`);
    } else {
      rec.value = doc;
    }
  } catch (e) {
    toast(e.message, "error");
  }
  saving.value = false;
}

async function deleteRec() {
  if (!confirm("Delete this alternative item mapping?")) return;
  saving.value = true;
  try {
    await apiCall("frappe.client.delete", { doctype: "Alternative Item", name: rec.value.name });
    toast("Deleted");
    router.push("/manufacturing/alternative-item");
  } catch (e) {
    toast(e.message, "error");
  }
  saving.value = false;
}
</script>
