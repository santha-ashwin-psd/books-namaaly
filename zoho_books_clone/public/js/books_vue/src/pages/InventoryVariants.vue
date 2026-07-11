<template>
<div class="b-page iv-root">

  <!-- ══ Header ══ -->
  <div class="iv-head">
    <button class="iv-back" @click="goBack" title="Back to Items">
      <span v-html="icon('arrow-left', 16)"></span>
    </button>
    <div class="iv-head-info">
      <div class="iv-head-title">
        <span v-html="icon('box', 17)"></span>
        {{ template?.item_name || route.params.template }}
        <span class="iv-count-chip">{{ variants.length }} variant{{ variants.length === 1 ? '' : 's' }}</span>
      </div>
      <div class="iv-head-sub">
        <span class="iv-code-badge">{{ template?.item_code || route.params.template }}</span>
        Manage attributes, prices, SKUs and stock for every variant.
      </div>
    </div>
  </div>

  <template v-if="loading">
    <div class="b-card b-card-body iv-shimmer b-shimmer"></div>
    <div class="b-card b-card-body iv-shimmer b-shimmer" style="height:220px"></div>
  </template>

  <template v-else-if="!template">
    <div class="b-card b-card-body iv-empty">
      <div class="iv-empty-icon">🧩</div>
      <div class="iv-empty-title">Template not found</div>
      <div class="iv-empty-sub">This item is not a variant template. <a class="iv-link" @click="goBack">Back to Items</a></div>
    </div>
  </template>

  <template v-else>

    <!-- ══ Attributes editor ══ -->
    <div class="b-card iv-card">
      <div class="iv-card-head" @click="attrsOpen = !attrsOpen">
        <div class="iv-card-title">
          <span v-html="icon('gear', 15)"></span> Attributes
        </div>
        <div class="iv-card-head-right">
          <span class="iv-combo-count">{{ comboCount }} combination{{ comboCount === 1 ? '' : 's' }}</span>
          <span class="iv-chevron" :class="{ open: attrsOpen }" v-html="icon('arrow-right', 14)"></span>
        </div>
      </div>
      <div v-show="attrsOpen" class="iv-card-body">
        <div v-if="!attrRows.length" class="iv-hint">Add an attribute (e.g. Colour) and its values (Red, Green, Blue).</div>
        <div v-for="(a, i) in attrRows" :key="i" class="iv-attr-row">
          <SearchableSelect v-model="a.attribute" :options="attributeOptions" placeholder="Attribute"
            :createable="true" @create="createAttribute($event, i)" class="iv-attr-name" />
          <input v-model="a.valuesText" class="iv-input iv-attr-vals" placeholder="Values, comma-separated (Red, Green, Blue)" />
          <button class="iv-icon-btn iv-icon-danger" @click="removeAttrRow(i)" title="Remove" :disabled="!$canWrite('inventory')">
            <span v-html="icon('trash', 14)"></span>
          </button>
        </div>
        <div class="iv-attr-actions">
          <button class="b-btn b-btn-ghost" @click="addAttrRow" :disabled="!$canWrite('inventory')">
            <span v-html="icon('plus', 13)"></span> Add attribute
          </button>
          <div class="iv-attr-actions-right">
            <span class="iv-gen-preview">{{ comboCount }} variant{{ comboCount === 1 ? '' : 's' }} will exist after regenerating</span>
            <button class="b-btn b-btn-primary" :disabled="regenerating || !comboCount || !$canWrite('inventory')" @click="saveAndRegenerate">
              <span v-html="icon('refresh', 13)"></span> {{ regenerating ? 'Regenerating…' : 'Save & Regenerate' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ══ Bulk price bar ══ -->
    <div v-if="variants.length" class="b-card iv-bulk">
      <div class="iv-bulk-title"><span v-html="icon('rupee', 14)"></span> Bulk price change</div>
      <div class="iv-bulk-controls">
        <select v-model="bulk.field" class="iv-input iv-bulk-select">
          <option value="selling">Selling rate</option>
          <option value="buying">Buying rate</option>
        </select>
        <select v-model="bulk.op" class="iv-input iv-bulk-select">
          <option value="set">Set to</option>
          <option value="inc_pct">Increase %</option>
          <option value="dec_pct">Decrease %</option>
          <option value="inc_amt">Increase ₹</option>
          <option value="dec_amt">Decrease ₹</option>
          <option value="round">Round to nearest</option>
        </select>
        <input v-if="bulk.op !== 'round'" v-model.number="bulk.value" type="number" min="0" step="0.01"
          class="iv-input iv-bulk-value" placeholder="0.00" />
        <span v-else class="iv-bulk-round-note">whole number</span>
        <div class="iv-bulk-scope">
          <label class="iv-radio"><input type="radio" value="selected" v-model="bulk.scope" /> Selected ({{ selectedCodes.length }})</label>
          <label class="iv-radio"><input type="radio" value="all" v-model="bulk.scope" /> All ({{ variants.length }})</label>
        </div>
        <button class="b-btn b-btn-primary" :disabled="applyingBulk || !$canWrite('inventory') || (bulk.scope === 'selected' && !selectedCodes.length)"
          @click="applyBulk">
          {{ applyingBulk ? 'Applying…' : 'Apply' }}
        </button>
      </div>
    </div>

    <!-- ══ Variants table ══ -->
    <div class="b-card iv-table-card">
      <div v-if="!variants.length" class="iv-empty">
        <div class="iv-empty-icon">🧩</div>
        <div class="iv-empty-title">No variants yet</div>
        <div class="iv-empty-sub">Define attributes above and click <b>Save &amp; Regenerate</b> to create them.</div>
      </div>

      <div v-else class="iv-table-wrap">
        <table class="iv-table">
          <thead>
            <tr>
              <th class="iv-th-check"><input type="checkbox" :checked="allSelected" @change="toggleAll" /></th>
              <th>Variant</th>
              <th>SKU / Code</th>
              <th class="ta-r">Selling ₹</th>
              <th class="ta-r">Buying ₹</th>
              <th v-if="template.is_stock_item" class="ta-r iv-th-stock">Stock</th>
              <th class="ta-c">Active</th>
              <th class="ta-r iv-th-actions">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="v in variants" :key="v.name" :class="{ 'iv-row-dirty': dirty.has(v.name), 'iv-row-off': v.disabled }">
              <td class="td-check iv-td-check">
                <input type="checkbox" :checked="selected.has(v.name)" @change="toggleOne(v.name)" />
              </td>
              <td class="td-variant" data-label="Variant">
                <div class="iv-var-name">
                  <input v-model="v.item_name" class="iv-input iv-name-input" @input="markDirty(v.name)" :disabled="!$canWrite('inventory')" />
                </div>
                <div class="iv-var-attrs">
                  <span v-for="a in v.attributes" :key="a.attribute" class="iv-attr-chip">{{ a.attribute_value }}</span>
                  <span v-if="!v.attributes.length" class="text-muted">—</span>
                </div>
              </td>
              <td class="td-sku" data-label="SKU">
                <input v-model="v.item_code" class="iv-input iv-sku-input mono-sm"
                  @input="markDirty(v.name)" :disabled="!$canWrite('inventory') || v.in_use"
                  :title="v.in_use ? 'Used in transactions — code can\'t change' : ''" />
                <div v-if="v.in_use" class="iv-inuse-tag">in use</div>
              </td>
              <td class="td-sell ta-r" data-label="Selling ₹">
                <input v-model.number="v.standard_rate" type="number" min="0" step="0.01"
                  class="iv-input iv-rate-input ta-r" @input="markDirty(v.name)" :disabled="!$canWrite('inventory')" />
              </td>
              <td class="td-buy ta-r" data-label="Buying ₹">
                <input v-model.number="v.standard_buying_rate" type="number" min="0" step="0.01"
                  class="iv-input iv-rate-input ta-r" @input="markDirty(v.name)" :disabled="!$canWrite('inventory')" />
              </td>
              <td v-if="template.is_stock_item" class="td-stock ta-r" data-label="Stock">
                <div class="iv-stock-qty" :class="{ 'iv-stock-zero': !v.actual_qty }">{{ fmtQty(v.actual_qty) }}</div>
                <div class="iv-stock-val">₹{{ fmt(v.stock_value) }}</div>
              </td>
              <td class="td-active ta-c" data-label="Active">
                <label class="iv-switch">
                  <input type="checkbox" :checked="!v.disabled" @change="toggleActive(v)" :disabled="!$canWrite('inventory')" />
                  <span class="iv-switch-track"></span>
                </label>
              </td>
              <td class="td-actions ta-r">
                <button v-if="dirty.has(v.name)" class="iv-icon-btn iv-icon-save" @click="saveVariant(v)" title="Save changes">
                  <span v-html="icon('save', 14)"></span>
                </button>
                <button class="iv-icon-btn iv-icon-danger" @click="askDelete(v)"
                  :disabled="!$canWrite('inventory') || v.in_use"
                  :title="v.in_use ? 'Used in transactions — disable instead' : 'Delete variant'">
                  <span v-html="icon('trash', 14)"></span>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </template>

  <!-- Delete confirm -->
  <Teleport to="body">
    <div v-if="delTarget" class="iv-modal-overlay" @click.self="delTarget = null">
      <div class="iv-modal">
        <div class="iv-modal-title">Delete variant?</div>
        <div class="iv-modal-body">
          <b>{{ delTarget.item_code }}</b> will be permanently removed. This can't be undone.
        </div>
        <div class="iv-modal-actions">
          <button class="b-btn b-btn-ghost" @click="delTarget = null">Cancel</button>
          <button class="b-btn iv-btn-danger" :disabled="deleting" @click="confirmDelete">
            {{ deleting ? 'Deleting…' : 'Delete' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGET, apiPOST, apiList, apiGet, apiSave } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { fmt, flt } from "../utils/format.js";
import { icon } from "../utils/icons.js";
import SearchableSelect from "../components/SearchableSelect.vue";

const route  = useRoute();
const router = useRouter();
const { toast } = useToast();

const templateId = computed(() => route.params.template);
const loading    = ref(true);
const template   = ref(null);
const variants   = ref([]);
const selected   = reactive(new Set());
const dirty      = reactive(new Set());

const attrsOpen  = ref(true);
const attrRows   = ref([]);            // [{ attribute, valuesText }]
const attributeOptions = ref([]);
const regenerating = ref(false);

const bulk = reactive({ field: "selling", op: "set", value: 0, scope: "all" });
const applyingBulk = ref(false);

const delTarget = ref(null);
const deleting  = ref(false);

const splitValues = (s) => String(s || "").split(",").map(v => v.trim()).filter(Boolean);
const fmtQty = (q) => Number(q || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });

// ── computed ──
const comboCount = computed(() =>
  attrRows.value.reduce((n, a) => {
    const c = splitValues(a.valuesText).length;
    return c ? n * c : n;
  }, attrRows.value.some(a => splitValues(a.valuesText).length) ? 1 : 0)
);
const selectedCodes = computed(() => [...selected]);
const allSelected = computed(() => variants.value.length > 0 && selected.size === variants.value.length);

// ── selection ──
function toggleOne(name) { selected.has(name) ? selected.delete(name) : selected.add(name); }
function toggleAll() {
  if (allSelected.value) selected.clear();
  else variants.value.forEach(v => selected.add(v.name));
}
function markDirty(name) { dirty.add(name); }

// ── load ──
async function load() {
  loading.value = true;
  selected.clear(); dirty.clear();
  try {
    const res = await apiGET("zoho_books_clone.api.variants.get_variant_manager", { template_item: templateId.value });
    template.value = res?.template || null;
    variants.value = res?.variants || [];
    // Seed the attribute editor from the template's declared attributes.
    const attrs = template.value?.attributes || {};
    attrRows.value = Object.keys(attrs).map(k => ({ attribute: k, valuesText: (attrs[k] || []).join(", ") }));
    if (!attrRows.value.length) attrRows.value = [{ attribute: "", valuesText: "" }];
  } catch (e) {
    template.value = null;
    toast("Could not load variants: " + e.message, "error");
  }
  loading.value = false;
}

async function loadAttributeOptions() {
  try {
    const r = await apiList("Item Attribute", { fields: ["name"], order: "name asc", limit: 200 });
    attributeOptions.value = (r || []).map(a => ({ value: a.name, label: a.name }));
  } catch { attributeOptions.value = []; }
}

// ── attributes ──
function addAttrRow() { attrRows.value.push({ attribute: "", valuesText: "" }); }
function removeAttrRow(i) { attrRows.value.splice(i, 1); }
async function createAttribute(name, i) {
  const nm = String(name || "").trim();
  if (!nm) return;
  try {
    await apiSave({ doctype: "Item Attribute", attribute_name: nm });
    await loadAttributeOptions();
    if (attrRows.value[i]) attrRows.value[i].attribute = nm;
    toast(`Attribute "${nm}" created`);
  } catch (e) { toast("Could not create attribute: " + e.message, "error"); }
}

async function saveAndRegenerate() {
  if (!comboCount.value) return;
  regenerating.value = true;
  try {
    const attributes = attrRows.value
      .filter(a => a.attribute && splitValues(a.valuesText).length)
      .map(a => ({ attribute: a.attribute, values: splitValues(a.valuesText) }));
    await apiPOST("zoho_books_clone.api.variants.set_template_attributes", {
      template_item: templateId.value, attributes,
    });
    const res = await apiPOST("zoho_books_clone.api.variants.create_variants", {
      template_item: templateId.value,
    });
    toast(`Generated ${res.count} variant(s)` + (res.skipped?.length ? ` · ${res.skipped.length} already existed` : ""));
    await load();
  } catch (e) { toast("Regenerate failed: " + e.message, "error"); }
  finally { regenerating.value = false; }
}

// ── per-variant ──
async function saveVariant(v) {
  try {
    const res = await apiPOST("zoho_books_clone.api.variants.update_variant", {
      item_code: v.name,
      item_name: v.item_name,
      standard_rate: flt(v.standard_rate),
      standard_buying_rate: flt(v.standard_buying_rate),
      new_item_code: v.item_code !== v.name ? v.item_code : null,
    });
    if (res.renamed) { v.name = res.item_code; }
    v.item_code = res.item_code;
    dirty.delete(v.name);
    toast("Variant saved");
  } catch (e) { toast("Save failed: " + e.message, "error"); }
}

async function toggleActive(v) {
  const nowDisabled = v.disabled ? 0 : 1;
  try {
    await apiPOST("zoho_books_clone.api.variants.update_variant", { item_code: v.name, disabled: nowDisabled });
    v.disabled = nowDisabled;
    toast(nowDisabled ? "Variant disabled" : "Variant enabled");
  } catch (e) { toast("Update failed: " + e.message, "error"); }
}

function askDelete(v) { delTarget.value = v; }
async function confirmDelete() {
  if (!delTarget.value) return;
  deleting.value = true;
  try {
    await apiPOST("zoho_books_clone.api.variants.delete_variant", { item_code: delTarget.value.name });
    variants.value = variants.value.filter(x => x.name !== delTarget.value.name);
    selected.delete(delTarget.value.name);
    toast("Variant deleted");
    delTarget.value = null;
  } catch (e) { toast("Delete failed: " + e.message, "error"); }
  finally { deleting.value = false; }
}

// ── bulk ──
async function applyBulk() {
  const codes = bulk.scope === "all" ? variants.value.map(v => v.name) : selectedCodes.value;
  if (!codes.length) { toast("No variants to update", "error"); return; }
  // Map the friendly ops onto the backend's (mode, value).
  let mode = bulk.op, value = flt(bulk.value);
  if (bulk.op === "dec_pct") { mode = "inc_pct"; value = -value; }
  else if (bulk.op === "inc_amt") { mode = "inc_amt"; }
  else if (bulk.op === "dec_amt") { mode = "inc_amt"; value = -value; }
  else if (bulk.op === "round") { mode = "round"; value = 0; }
  applyingBulk.value = true;
  try {
    const res = await apiPOST("zoho_books_clone.api.variants.bulk_update_variant_prices", {
      variant_codes: codes, field: bulk.field, mode,
      value, decimals: bulk.op === "round" ? 0 : 2,
    });
    const field = bulk.field === "selling" ? "standard_rate" : "standard_buying_rate";
    const byCode = Object.fromEntries((res.updated || []).map(r => [r.item_code, r.rate]));
    variants.value.forEach(v => { if (byCode[v.name] != null) { v[field] = byCode[v.name]; dirty.delete(v.name); } });
    toast(`Updated ${res.count} variant(s)`);
  } catch (e) { toast("Bulk update failed: " + e.message, "error"); }
  finally { applyingBulk.value = false; }
}

function goBack() { router.push({ name: "inventory-items" }); }

onMounted(() => { load(); loadAttributeOptions(); });
</script>

<style scoped>
.iv-root { padding: 20px 24px 40px; max-width: 1180px; margin: 0 auto; }

/* Header */
.iv-head { display: flex; align-items: flex-start; gap: 14px; margin-bottom: 18px; }
.iv-back {
  flex-shrink: 0; width: 38px; height: 38px; border-radius: 9px; border: 1px solid #E5E7EB;
  background: #fff; color: #374151; cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: all .15s;
}
.iv-back:hover { background: #F3F4F6; border-color: #D1D5DB; }
.iv-head-info { min-width: 0; }
.iv-head-title { display: flex; align-items: center; gap: 9px; font-size: 20px; font-weight: 700; color: #111827; }
.iv-count-chip { font-size: 12px; font-weight: 600; color: #4C6EF5; background: #EEF2FF; padding: 3px 10px; border-radius: 999px; }
.iv-head-sub { margin-top: 5px; font-size: 13px; color: #6B7280; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.iv-code-badge { font-size: 11.5px; background: #F3F4F6; color: #374151; padding: 2px 8px; border-radius: 5px; }

/* Cards */
.iv-card, .iv-bulk, .iv-table-card { margin-bottom: 16px; }
.iv-card-head {
  display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; cursor: pointer;
  user-select: none;
}
.iv-card-title { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 700; color: #111827; }
.iv-card-head-right { display: flex; align-items: center; gap: 12px; }
.iv-combo-count { font-size: 12px; color: #6B7280; }
.iv-chevron { transition: transform .2s; color: #9CA3AF; display: inline-flex; }
.iv-chevron.open { transform: rotate(90deg); }
.iv-card-body { padding: 0 18px 18px; border-top: 1px solid #F3F4F6; padding-top: 16px; }
.iv-hint { font-size: 12.5px; color: #9CA3AF; margin-bottom: 12px; }

/* Attribute rows */
.iv-attr-row { display: flex; gap: 10px; margin-bottom: 10px; align-items: center; }
.iv-attr-name { width: 200px; flex-shrink: 0; }
.iv-attr-vals { flex: 1; }
.iv-attr-actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 14px; flex-wrap: wrap; }
.iv-attr-actions-right { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.iv-gen-preview { font-size: 12px; color: #6B7280; }

/* Inputs */
.iv-input {
  border: 1px solid #E5E7EB; border-radius: 7px; padding: 7px 10px; font-size: 13px; color: #111827;
  background: #fff; outline: none; transition: border-color .15s, box-shadow .15s; width: 100%;
}
.iv-input:focus { border-color: #4C6EF5; box-shadow: 0 0 0 3px rgba(76,110,245,.12); }
.iv-input:disabled { background: #F9FAFB; color: #9CA3AF; cursor: not-allowed; }

/* Bulk bar */
.iv-bulk { padding: 14px 18px; }
.iv-bulk-title { display: flex; align-items: center; gap: 7px; font-size: 13px; font-weight: 700; color: #111827; margin-bottom: 12px; }
.iv-bulk-controls { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.iv-bulk-select { width: auto; min-width: 130px; }
.iv-bulk-value { width: 120px; }
.iv-bulk-round-note { font-size: 12px; color: #9CA3AF; }
.iv-bulk-scope { display: flex; gap: 14px; margin-left: 4px; }
.iv-radio { display: flex; align-items: center; gap: 5px; font-size: 12.5px; color: #374151; cursor: pointer; }

/* Table */
.iv-table-wrap { overflow-x: auto; }
.iv-table { width: 100%; border-collapse: collapse; }
.iv-table thead th {
  text-align: left; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .04em;
  color: #6B7280; padding: 12px 14px; border-bottom: 1px solid #E5E7EB; white-space: nowrap; background: #FAFBFC;
}
.iv-table tbody td { padding: 10px 14px; border-bottom: 1px solid #F3F4F6; vertical-align: middle; }
.iv-table tbody tr:hover { background: #FAFBFC; }
.iv-row-dirty { background: #FFFBEB !important; }
.iv-row-off { opacity: .62; }
.ta-r { text-align: right; } .ta-c { text-align: center; }
.iv-th-check { width: 34px; } .iv-th-actions { width: 92px; } .iv-th-stock { width: 110px; }

.iv-var-name { margin-bottom: 5px; }
.iv-name-input { font-weight: 600; font-size: 13px; }
.iv-var-attrs { display: flex; gap: 5px; flex-wrap: wrap; }
.iv-attr-chip { font-size: 10.5px; font-weight: 600; color: #4C6EF5; background: #EEF2FF; padding: 2px 8px; border-radius: 5px; }
.iv-sku-input { max-width: 200px; }
.iv-inuse-tag { font-size: 9.5px; color: #B45309; margin-top: 3px; text-transform: uppercase; letter-spacing: .03em; }
.iv-rate-input { max-width: 120px; margin-left: auto; }
.iv-stock-qty { font-weight: 700; font-size: 13px; color: #059669; }
.iv-stock-qty.iv-stock-zero { color: #9CA3AF; }
.iv-stock-val { font-size: 11px; color: #9CA3AF; }

/* Switch */
.iv-switch { position: relative; display: inline-block; width: 38px; height: 21px; cursor: pointer; }
.iv-switch input { opacity: 0; width: 0; height: 0; }
.iv-switch-track { position: absolute; inset: 0; background: #D1D5DB; border-radius: 999px; transition: .18s; }
.iv-switch-track::before { content: ""; position: absolute; height: 15px; width: 15px; left: 3px; top: 3px; background: #fff; border-radius: 50%; transition: .18s; }
.iv-switch input:checked + .iv-switch-track { background: #22C55E; }
.iv-switch input:checked + .iv-switch-track::before { transform: translateX(17px); }
.iv-switch input:disabled + .iv-switch-track { opacity: .5; cursor: not-allowed; }

/* Icon buttons */
.iv-icon-btn {
  width: 30px; height: 30px; border-radius: 7px; border: 1px solid #E5E7EB; background: #fff; color: #6B7280;
  cursor: pointer; display: inline-flex; align-items: center; justify-content: center; transition: all .15s; margin-left: 4px;
}
.iv-icon-btn:hover:not(:disabled) { background: #F3F4F6; }
.iv-icon-btn:disabled { opacity: .4; cursor: not-allowed; }
.iv-icon-save { color: #16A34A; border-color: #BBF7D0; background: #F0FDF4; }
.iv-icon-danger:hover:not(:disabled) { color: #DC2626; border-color: #FECACA; background: #FEF2F2; }

/* Empty / misc */
.iv-empty { text-align: center; padding: 48px 20px; }
.iv-empty-icon { font-size: 34px; margin-bottom: 10px; }
.iv-empty-title { font-size: 15px; font-weight: 700; color: #374151; margin-bottom: 5px; }
.iv-empty-sub { font-size: 13px; color: #9CA3AF; }
.iv-link { color: #4C6EF5; cursor: pointer; text-decoration: underline; }
.iv-shimmer { height: 90px; margin-bottom: 16px; }

/* Modal */
.iv-modal-overlay { position: fixed; inset: 0; background: rgba(17,24,39,.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.iv-modal { background: #fff; border-radius: 12px; padding: 22px; width: 380px; max-width: 92vw; box-shadow: 0 20px 50px rgba(0,0,0,.25); }
.iv-modal-title { font-size: 16px; font-weight: 700; color: #111827; margin-bottom: 8px; }
.iv-modal-body { font-size: 13.5px; color: #4B5563; line-height: 1.5; margin-bottom: 20px; }
.iv-modal-actions { display: flex; justify-content: flex-end; gap: 10px; }
.iv-btn-danger { background: #DC2626; color: #fff; }
.iv-btn-danger:hover:not(:disabled) { background: #B91C1C; }

/* ── Responsive: card layout on narrow screens ── */
@media (max-width: 720px) {
  .iv-root { padding: 14px 12px 32px; }
  .iv-bulk-controls { gap: 8px; }
  .iv-bulk-select, .iv-bulk-value { flex: 1 1 130px; }
}
@media (max-width: 560px) {
  .iv-table thead { display: none; }
  .iv-table, .iv-table tbody, .iv-table tr, .iv-table td { display: block; width: 100%; }
  .iv-table tbody tr {
    border: 1px solid #E5E7EB; border-radius: 10px; margin-bottom: 12px; padding: 6px 4px; position: relative;
  }
  .iv-table tbody td { border: none; padding: 7px 12px; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
  .iv-table tbody td::before {
    content: attr(data-label); font-size: 11px; font-weight: 600; color: #9CA3AF; text-transform: uppercase; letter-spacing: .03em; flex-shrink: 0;
  }
  .iv-td-check { position: absolute; top: 8px; right: 8px; padding: 0 !important; }
  .iv-td-check::before { display: none; }
  .td-actions { justify-content: flex-end; }
  .td-actions::before { content: "Actions"; }
  .iv-rate-input, .iv-sku-input, .iv-name-input { max-width: 60%; }
  .iv-var-attrs { justify-content: flex-end; }
}
</style>
