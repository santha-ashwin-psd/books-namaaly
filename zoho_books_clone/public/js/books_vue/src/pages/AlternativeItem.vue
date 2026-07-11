<template>
<div class="aix-page">
  <div class="aix-two-col">

    <!-- ══════════ LEFT: ALTERNATIVE ITEM LIST ══════════ -->
    <div class="aix-list-panel">
      <div class="aix-panel-hdr">
        <span class="aix-panel-title">🔀 Alternative Items <span class="aix-count">({{ filtered.length }})</span></span>
        <button class="aix-btn aix-btn-mfg aix-btn-sm" @click="openAdd"><span v-html="icon('plus',12)"></span> New</button>
      </div>
      <select class="aix-fi aix-status-filter" v-model="filterDefault" @change="page=0">
        <option value="">All Mappings</option>
        <option value="default">Default Only</option>
        <option value="non-default">Non-default Only</option>
      </select>
      <input class="aix-search" v-model="search" type="text" placeholder="Search by item code…"/>
      <div class="aix-list">
        <template v-if="loading">
          <div v-for="n in 5" :key="n" class="aix-item"><div class="shimmer" style="height:38px;border-radius:6px"></div></div>
        </template>
        <div v-else-if="!sorted.length" class="aix-list-empty">No Alternative Items found</div>
        <div v-else v-for="row in sorted" :key="row.name"
             class="aix-item" :class="{active: selectedName === row.name}"
             @click="selectRow(row.name)">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px">
            <div class="aix-item-name">{{ row.item_code }}</div>
            <span v-if="row.is_default" class="aix-badge badge-active">Default</span>
          </div>
          <div class="aix-item-meta">
            <span>→</span>
            <span>{{ row.alternative_item_code || '—' }}</span>
          </div>
          <div class="aix-item-right">
            <span style="font-size:12px;color:var(--bx-muted)">Factor:</span>
            <span class="mono" style="font-size:12.5px;font-weight:700;color:var(--bx-mfgB)">{{ row.conversion_factor }}</span>
            <span v-if="row.uom" style="font-size:12px;color:var(--bx-muted);margin-left:auto">{{ row.uom }}</span>
          </div>
        </div>
      </div>
      <!-- Pagination -->
      <div class="aix-list-pager">
        <span>{{ filtered.length ? page*pageSize+1 : 0 }}–{{ Math.min((page+1)*pageSize, filtered.length) }} of {{ filtered.length }}</span>
        <div style="display:flex;gap:6px;">
          <button class="aix-btn-icon" @click="page>0 && page--" :disabled="page===0">‹</button>
          <button class="aix-btn-icon" @click="(page+1)*pageSize<filtered.length && page++" :disabled="(page+1)*pageSize>=filtered.length">›</button>
        </div>
      </div>
    </div>

    <!-- ══════════ RIGHT: ALTERNATIVE ITEM DETAIL ══════════ -->
    <div class="aix-detail-panel">

      <!-- Empty state -->
      <div v-if="!selectedName" class="aix-empty-state">
        <div class="aix-empty-icon">🔀</div>
        <div class="aix-empty-title">Select an Alternative Item</div>
        <div class="aix-empty-sub">Choose a mapping from the list to view or edit it, or create a new substitute item mapping.</div>
        <button class="aix-btn aix-btn-mfg" @click="openAdd"><span v-html="icon('plus',13)"></span> Create First Mapping</button>
      </div>

      <template v-else>
        <div v-if="detailLoading" class="aix-empty-state"><div class="shimmer" style="height:200px;border-radius:10px"></div></div>

        <template v-else>
          <!-- Header -->
          <div class="aix-detail-hdr">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px">
              <div style="min-width:0">
                <div class="aix-detail-title">{{ isNew ? 'New Alternative Item' : (itemNameFor(rec.item_code) || rec.item_code) }}</div>
                <div class="aix-detail-meta">
                  <span class="mono" v-if="!isNew">{{ rec.name }}</span>
                  <span v-if="!isNew">•</span>
                  <span>→ {{ itemNameFor(rec.alternative_item_code) || rec.alternative_item_code || '—' }}</span>
                  <span v-if="rec.is_default">•</span>
                  <span v-if="rec.is_default" class="aix-badge badge-active" style="font-size:11px">Default</span>
                </div>
              </div>
              <div style="display:flex;gap:6px;flex-shrink:0;flex-wrap:wrap;justify-content:flex-end">
                <button class="aix-btn aix-btn-ghost-inv" @click="goBackToList">Back</button>
                <button v-if="!isNew" class="aix-btn aix-btn-light" style="color:#C92A2A" @click="deleteRec" :disabled="saving">
                  {{ saving ? 'Deleting…' : 'Delete' }}
                </button>
                <button class="aix-btn aix-btn-light" @click="save" :disabled="saving || loading">
                  {{ saving ? 'Saving…' : (isNew ? 'Save' : 'Update') }}
                </button>
              </div>
            </div>
          </div>

          <!-- Body -->
          <div class="aix-body">

            <div class="aix-section-lbl">Item Mapping</div>
            <div class="aix-fg">
              <div>
                <div class="aix-hf-label">Original Item <span class="aix-req">*</span></div>
                <select class="aix-fi" v-model="rec.item_code" :disabled="!isNew" style="width:100%">
                  <option value="">— Select —</option>
                  <option v-for="i in itemsList" :key="i.name" :value="i.name">{{ i.item_name || i.name }}</option>
                </select>
              </div>
              <div>
                <div class="aix-hf-label">Alternative Item <span class="aix-req">*</span></div>
                <select class="aix-fi" v-model="rec.alternative_item_code" style="width:100%">
                  <option value="">— Select —</option>
                  <option v-for="i in itemsList" :key="i.name" :value="i.name">{{ i.item_name || i.name }}</option>
                </select>
              </div>
            </div>

            <div class="aix-section-lbl" style="margin-top:20px;">Conversion</div>
            <div class="aix-fg">
              <div>
                <div class="aix-hf-label">Conversion Factor <span class="aix-req">*</span></div>
                <input type="number" class="aix-fi aix-fi-mono" v-model="rec.conversion_factor" min="0.0001" step="any" style="width:100%"/>
                <div class="aix-field-hint">Qty of Alternative needed per 1 unit of Original.</div>
              </div>
              <div>
                <div class="aix-hf-label">UOM</div>
                <select class="aix-fi" v-model="rec.uom" style="width:100%">
                  <option value="">— None —</option>
                  <option v-for="u in uomList" :key="u" :value="u">{{ u }}</option>
                </select>
              </div>
            </div>

            <div class="aix-toggle-row">
              <label class="aix-toggle"><input type="checkbox" v-model="rec.is_default" :true-value="1" :false-value="0"/> Mark as Default Substitute</label>
            </div>

            <div class="aix-section-lbl" style="margin-top:20px;">Notes</div>
            <div>
              <div class="aix-hf-label">Description / Reason</div>
              <textarea class="aix-fi" style="width:100%;resize:vertical;" rows="3" v-model="rec.description" placeholder="Why this is a valid alternative…"></textarea>
            </div>

          </div>

          <!-- Footer -->
          <div class="aix-footer">
            <button v-if="!isNew" class="aix-btn aix-btn-ghost-inv" style="color:var(--bx-red);border-color:rgba(201,42,42,.3)" @click="deleteRec" :disabled="saving">Delete Mapping</button>
            <div style="flex:1"></div>
            <button class="aix-btn aix-btn-mfg" @click="save" :disabled="saving || loading">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13"/><polyline points="7 3 7 8 15 8"/></svg>
              {{ saving ? 'Saving…' : (isNew ? 'Save Mapping' : 'Update Mapping') }}
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
import { apiGet, apiList, apiSave, apiCall } from "../api/client.js";
import { useToast } from "../composables/useToast.js";

const route = useRoute();
const router = useRouter();
const { toast } = useToast();

// ── LIST STATE ──────────────────────────────────────────────
const loading = ref(false);
const list = ref([]);
const search = ref("");
const filterDefault = ref("");
const page = ref(0);
const pageSize = 20;

const selectedName = computed(() => (route.params.name && route.params.name !== "new") ? route.params.name : (route.params.name === "new" ? "new" : null));

async function loadList() {
  loading.value = true;
  try {
    const fields = ["name", "item_code", "alternative_item_code", "conversion_factor", "uom", "is_default", "modified"];
    const r = await apiList("Alternative Item", { fields, limit: 1000, order: "modified desc" });
    list.value = r || [];
  } catch (e) {
    toast("Could not load Alternative Items", "error");
  }
  loading.value = false;
}

const filtered = computed(() => {
  let r = list.value;
  if (filterDefault.value === "default") r = r.filter(i => i.is_default);
  if (filterDefault.value === "non-default") r = r.filter(i => !i.is_default);
  const q = search.value.toLowerCase().trim();
  if (q) r = r.filter(i => [i.item_code, i.alternative_item_code, i.name].filter(Boolean).join(" ").toLowerCase().includes(q));
  return r;
});

const sorted = computed(() => filtered.value.slice(page.value * pageSize, (page.value + 1) * pageSize));

function selectRow(name) {
  router.push(`/manufacturing/alternative-item/${name}`);
}
function openAdd() {
  router.push("/manufacturing/alternative-item/new");
}
function goBackToList() {
  router.push("/manufacturing/alternative-item");
}

// ── DETAIL STATE ─────────────────────────────────────────────
const isNew = computed(() => route.params.name === "new");
const detailLoading = ref(false);
const saving = ref(false);

function emptyRec() {
  return {
    doctype: "Alternative Item",
    item_code: "",
    alternative_item_code: "",
    conversion_factor: 1,
    uom: "",
    is_default: 0,
    description: "",
  };
}
const rec = ref(emptyRec());

const itemsList = ref([]);
const uomList = ref([]);

function itemNameFor(code) {
  const i = itemsList.value.find(x => x.name === code);
  return i ? i.item_name : null;
}

onMounted(async () => {
  loading.value = true;
  try {
    const items = await apiList("Item", { fields: ["name", "item_name"], limit: 5000, order: "name asc" });
    itemsList.value = items || [];
    const uoms = await apiList("UOM", { fields: ["name"], limit: 200, order: "name asc" });
    uomList.value = (uoms || []).map(u => u.name);
  } catch (e) {
    toast("Error loading manufacturing data: " + e.message, "error");
  }
  await loadList();
  if (route.params.name) await loadRec();
  loading.value = false;
});

watch(() => route.params.name, async (name) => {
  if (!name) { rec.value = emptyRec(); return; }
  await loadRec();
});

async function loadRec() {
  if (isNew.value) {
    rec.value = emptyRec();
    return;
  }
  detailLoading.value = true;
  try {
    const data = await apiGet("Alternative Item", route.params.name);
    rec.value = data;
  } catch (e) {
    toast("Error loading Alternative Item: " + e.message, "error");
    goBackToList();
  }
  detailLoading.value = false;
}

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
    loadList();
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
    goBackToList();
    loadList();
  } catch (e) {
    toast(e.message, "error");
  }
  saving.value = false;
}

// ── UTIL ─────────────────────────────────────────────────────
const ICONS = {
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
};
function icon(name, size) {
  return (ICONS[name] || "").replace("<svg ", `<svg width="${size}" height="${size}" `);
}
</script>

<style scoped>
.aix-page {
  --bx-bg:#F3F4F6; --bx-surface:#FFFFFF; --bx-surf2:#F8F9FC; --bx-border:#E2E8F0;
  --bx-text:#1A1D23; --bx-muted:#868E96;
  --bx-green:#2F9E44; --bx-greenS:#EBFBEE;
  --bx-red:#C92A2A; --bx-redS:#FFF5F5;
  --bx-amber:#E67700; --bx-amberS:#FFF3BF;
  --bx-blue:#1971C2; --bx-blueS:#E7F5FF;
  --bx-mfg:#1a6ef7; --bx-mfgL:#2f74f5; --bx-mfgS:#EAF1FF; --bx-mfgB:#1e3a5f;
  --bx-radius:10px; --bx-rsm:6px;
  padding: 16px;
}
.aix-two-col { display:grid; grid-template-columns: 340px 1fr; gap:16px; align-items:start; }
@media (max-width:1000px) { .aix-two-col { grid-template-columns: 1fr; } }

.mono { font-family: "DM Mono", ui-monospace, monospace; }

/* ── List panel ── */
.aix-list-panel { background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; display:flex; flex-direction:column; }
.aix-panel-hdr { padding:12px 14px; border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); display:flex; align-items:center; justify-content:space-between; gap:8px; }
.aix-panel-title { font-size:13px; font-weight:700; color:var(--bx-text); }
.aix-count { font-size:12px; font-weight:400; color:var(--bx-muted); }
.aix-status-filter { margin:8px 12px 0; width:calc(100% - 24px); font-size:12px; padding:6px 10px; }
.aix-search { width:100%; border:none; outline:none; font-size:13px; padding:10px 14px; margin-top:8px; border-bottom:1px solid var(--bx-border); background:#fff; color:var(--bx-text); }
.aix-search::placeholder { color:var(--bx-muted); }
.aix-list { overflow-y:auto; max-height: calc(100vh - 280px); }
.aix-list-empty { text-align:center; padding:32px; color:var(--bx-muted); font-size:13px; }
.aix-item { padding:12px 14px; border-bottom:1px solid #F1F3F5; cursor:pointer; transition:background .12s; display:flex; flex-direction:column; gap:4px; }
.aix-item:hover { background:#FAFBFF; }
.aix-item.active { background:var(--bx-mfgS); border-left:3px solid var(--bx-mfg); }
.aix-item-name { font-size:13.5px; font-weight:600; color:var(--bx-text); }
.aix-item-meta { display:flex; align-items:center; gap:6px; font-size:12px; color:var(--bx-muted); }
.aix-item-right { display:flex; align-items:center; gap:6px; margin-top:2px; }
.aix-list-pager { display:flex; align-items:center; justify-content:space-between; padding:8px 14px; border-top:1px solid var(--bx-border); background:var(--bx-surf2); font-size:11.5px; color:var(--bx-muted); }

/* ── Badges ── */
.aix-badge { display:inline-flex; align-items:center; padding:2px 8px; border-radius:20px; font-size:11px; font-weight:600; white-space:nowrap; }
.badge-active { background:var(--bx-greenS); color:var(--bx-green); }

/* ── Detail panel ── */
.aix-detail-panel { background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; display:flex; flex-direction:column; min-height: calc(100vh - 100px); }
.aix-empty-state { text-align:center; padding:60px 20px; color:var(--bx-muted); }
.aix-empty-icon { font-size:48px; margin-bottom:14px; }
.aix-empty-title { font-size:16px; font-weight:700; color:var(--bx-text); margin-bottom:6px; }
.aix-empty-sub { font-size:13px; line-height:1.6; max-width:280px; margin:0 auto 20px; }

.aix-detail-hdr { padding:18px 22px; background:linear-gradient(135deg, var(--bx-mfgB), var(--bx-mfg)); }
.aix-detail-title { font-size:18px; font-weight:700; color:#fff; margin-bottom:4px; }
.aix-detail-meta { font-size:12.5px; color:rgba(255,255,255,.75); display:flex; align-items:center; gap:8px; flex-wrap:wrap; }

.aix-body { padding:20px 22px; overflow-y:auto; flex:1; }
.aix-section-lbl { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--bx-muted); margin-bottom:8px; }
.aix-fg { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
@media (max-width:640px) { .aix-fg { grid-template-columns:1fr; } }
.aix-hf-label { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); margin-bottom:4px; }
.aix-req { color:var(--bx-red); }
.aix-field-hint { font-size:12px; color:var(--bx-muted); margin-top:5px; }
.aix-toggle-row { display:flex; gap:20px; padding:14px 0 0; flex-wrap:wrap; }
.aix-toggle { display:flex; align-items:center; gap:6px; font-size:12.5px; font-weight:600; color:var(--bx-text); }

.aix-footer { padding:12px 22px; border-top:1px solid var(--bx-border); background:var(--bx-surf2); display:flex; justify-content:space-between; align-items:center; gap:8px; }

/* ── Buttons / inputs ── */
.aix-fi { border:1px solid #CDD5E0; border-radius:var(--bx-rsm); padding:7px 9px; font-size:13px; color:var(--bx-text); background:#fff; outline:none; }
.aix-fi:focus { border-color:var(--bx-mfg); box-shadow:0 0 0 3px rgba(180,83,9,.1); }
.aix-fi:disabled { background:#F8F9FC; color:var(--bx-muted); }
.aix-fi-mono { font-family:"DM Mono",monospace; }
select.aix-fi {
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
select.aix-fi:disabled { background-image: none; padding-right: 9px; }
.aix-btn { display:inline-flex; align-items:center; gap:6px; padding:8px 16px; border-radius:var(--bx-rsm); font-size:13px; font-weight:600; cursor:pointer; border:1px solid transparent; line-height:1; white-space:nowrap; }
.aix-btn:disabled { opacity:.6; cursor:not-allowed; }
.aix-btn-sm { padding:6px 10px; font-size:12px; }
.aix-btn-mfg { background:var(--bx-mfg); color:#fff; }
.aix-btn-mfg:hover:not(:disabled) { background:var(--bx-mfgB); }
.aix-btn-light { background:rgba(255,255,255,.92); color:var(--bx-mfgB); border:1px solid var(--bx-border); }
.aix-btn-light:hover:not(:disabled) { background:#fff; }
.aix-btn-ghost-inv { background:rgba(255,255,255,.15); color:#fff; border-color:rgba(255,255,255,.3); }
.aix-btn-ghost-inv:hover:not(:disabled) { background:rgba(255,255,255,.25); }
.aix-btn-icon { background:none; border:1px solid var(--bx-border); border-radius:5px; cursor:pointer; padding:4px 6px; display:inline-flex; color:var(--bx-muted); }
.aix-btn-icon:hover { border-color:var(--bx-mfg); color:var(--bx-mfg); background:var(--bx-mfgS); }
.aix-btn-icon:disabled { opacity:.4; cursor:not-allowed; }

.shimmer { background:linear-gradient(90deg,#f1f3f5 25%,#e9ecef 37%,#f1f3f5 63%); background-size:400% 100%; animation:shimmer 1.4s ease infinite; }
@keyframes shimmer { 0%{background-position:100% 50%} 100%{background-position:0 50%} }
</style>