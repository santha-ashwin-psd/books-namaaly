<template>
<div class="bomx-page">
  <div class="bomx-two-col">

    <!-- ══════════ LEFT: MATERIAL REQUEST LIST ══════════ -->
    <div class="bomx-list-panel">
      <div class="bomx-panel-hdr">
        <span class="bomx-panel-title">📦 All Material Requests <span class="bomx-count">({{ sorted.length }})</span></span>
        <button class="bomx-btn bomx-btn-mfg bomx-btn-sm" @click="openAdd"><span v-html="icon('plus',12)"></span> New</button>
      </div>
      <select class="bomx-fi bomx-status-filter" v-model="filterStatus">
        <option value="">All Status</option>
        <option v-for="s in statusOptions" :key="s" :value="s">{{ s }}</option>
      </select>
      <input class="bomx-search" v-model="search" type="text" placeholder="Search Material Requests…"/>
      <div class="bomx-list">
        <template v-if="loading">
          <div v-for="n in 5" :key="n" class="bomx-item"><div class="shimmer" style="height:38px;border-radius:6px"></div></div>
        </template>
        <div v-else-if="!sorted.length" class="bomx-list-empty">No Material Requests found</div>
        <div v-else v-for="row in sorted" :key="row.name"
             class="bomx-item" :class="{active: selectedName === row.name}"
             @click="selectMR(row.name)">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px">
            <div class="bomx-item-name">{{ row.name }}</div>
            <span class="bomx-badge" :class="statusClass(row)">{{ row.status }}</span>
          </div>
          <div class="bomx-item-meta">
            <span>{{ row.material_request_type || '—' }}</span>
            <span>•</span>
            <span class="mono">{{ fmtDate(row.posting_date) }}</span>
          </div>
          <div class="bomx-item-right" v-if="row.production_plan">
            <span style="font-size:12px;color:var(--bx-muted)">{{ row.production_plan }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ══════════ RIGHT: MATERIAL REQUEST DETAIL ══════════ -->
    <div class="bomx-detail-panel">

      <!-- Empty state -->
      <div v-if="!selectedName" class="bomx-empty-state">
        <div class="bomx-empty-icon">📦</div>
        <div class="bomx-empty-title">Select a Material Request</div>
        <div class="bomx-empty-sub">Choose a Material Request from the list to view or edit its items.</div>
        <button class="bomx-btn bomx-btn-mfg" @click="openAdd"><span v-html="icon('plus',13)"></span> Create Material Request</button>
      </div>

      <template v-else>
        <div v-if="loading" class="bomx-empty-state"><div class="shimmer" style="height:200px;border-radius:10px"></div></div>

        <template v-else>
          <!-- Header -->
          <div class="bomx-detail-hdr">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap">
              <div style="min-width:0">
                <div class="bomx-detail-title">{{ isNew ? 'New Material Request' : mr.name }}</div>
                <div class="bomx-detail-meta">
                  <span v-if="!isNew">{{ mr.material_request_type }}</span>
                  <span v-if="!isNew">•</span>
                  <span v-if="!isNew">{{ fmtDate(mr.posting_date) }}</span>
                  <span v-if="!isNew">•</span>
                  <span class="bomx-badge" :class="statusClass(mr)" style="font-size:11px" v-if="!isNew">{{ mr.status }}</span>
                </div>
              </div>
              <div style="display:flex;gap:6px;flex-shrink:0;flex-wrap:wrap;justify-content:flex-end">
                <button class="bomx-btn bomx-btn-ghost-inv" @click="goBackToList" :disabled="saving || submitting">Back</button>
                <button v-if="!isNew && mr.docstatus===2" class="bomx-btn bomx-btn-light" @click="amendMR" :disabled="submitting">
                  {{ submitting ? 'Amending…' : 'Amend' }}
                </button>
                <button v-if="!isNew && mr.docstatus===1" class="bomx-btn" style="background:var(--bx-redS);color:var(--bx-red)" @click="cancelMR" :disabled="submitting">
                  {{ submitting ? 'Cancelling…' : 'Cancel' }}
                </button>
                <button v-if="!isNew && mr.docstatus===0" class="bomx-btn bomx-btn-light" @click="submitMR" :disabled="submitting || saving">
                  {{ submitting ? 'Submitting…' : 'Submit' }}
                </button>
                <button v-if="!readOnly" class="bomx-btn bomx-btn-light" @click="save" :disabled="saving || loading">
                  {{ saving ? 'Saving…' : (isNew ? 'Save Material Request' : 'Save Changes') }}
                </button>
              </div>
            </div>
          </div>

          <!-- Header fields -->
          <div class="bomx-hdr-fields">
            <div>
              <div class="bomx-hf-label">Purpose <span style="color:var(--bx-red)">*</span></div>
              <select class="bomx-fi" v-model="mr.material_request_type" :disabled="readOnly" style="width:100%">
                <option value="Purchase">Purchase</option>
                <option value="Material Transfer">Material Transfer</option>
              </select>
            </div>
            <div>
              <div class="bomx-hf-label">Required By <span style="color:var(--bx-red)">*</span></div>
              <input class="bomx-fi" type="date" v-model="mr.posting_date" :disabled="readOnly" style="width:100%"/>
            </div>
          </div>
          <div class="bomx-toggle-row" v-if="mr.production_plan">
            <div class="bomx-field-hint" style="margin:0">
              Production Plan:
              <span class="bomx-link" @click="router.push(`/manufacturing/production-plan/${mr.production_plan}`)">{{ mr.production_plan }}</span>
            </div>
          </div>

          <!-- Body -->
          <div class="bomx-body">

            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
              <span class="bomx-section-lbl" style="margin-bottom:0">Items</span>
              <button v-if="!readOnly" class="bomx-btn bomx-btn-sm bomx-btn-light" style="color:var(--bx-mfgB);border:1px solid var(--bx-mfg)" @click="addItem">
                <span v-html="icon('plus',12)"></span> Add Row
              </button>
            </div>
            <div class="bomx-rm-cards" style="margin-bottom:20px">
              <div v-if="!mr.items || !mr.items.length" class="bomx-tree-empty">No items yet. Add a row or create from Production Plan.</div>
              <div v-for="(row, idx) in mr.items" :key="idx" class="bomx-rm-card">
                <div class="bomx-rm-card-hdr">
                  <span class="bomx-rm-card-title">{{ row.item_name || row.item_code || 'New Row' }}</span>
                  <button v-if="!readOnly" class="bomx-btn-icon danger" @click="mr.items.splice(idx,1)" title="Remove">
                    <span v-html="icon('trash',13)"></span>
                  </button>
                </div>
                <div class="bomx-rm-card-body">
                  <div class="bomx-rm-field" style="grid-column:span 2">
                    <label>Item</label>
                    <select class="bomx-fi" v-model="row.item_code" @change="onItemChange(row)" :disabled="readOnly">
                      <option value="">— Select Item —</option>
                      <option v-for="i in itemsList" :key="i.name" :value="i.name">{{ i.item_name || i.name }}</option>
                    </select>
                  </div>
                  <div class="bomx-rm-field">
                    <label>Required Qty</label>
                    <input class="bomx-fi bomx-fi-mono" type="number" v-model="row.required_qty" min="0.001" step="any" :disabled="readOnly"/>
                  </div>
                  <div class="bomx-rm-field">
                    <label>UOM</label>
                    <select class="bomx-fi" v-model="row.uom" :disabled="readOnly">
                      <option value="">—</option>
                      <option v-for="u in uomList" :key="u.name" :value="u.name">{{ u.name }}</option>
                    </select>
                  </div>
                  <div class="bomx-rm-field" style="grid-column:span 2">
                    <label>Warehouse</label>
                    <select class="bomx-fi" v-model="row.warehouse" :disabled="readOnly">
                      <option value="">— Select —</option>
                      <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>

            <div class="bomx-section-lbl">Remarks</div>
            <textarea class="bomx-fi" v-model="mr.remarks" rows="3" :disabled="readOnly" style="width:100%;min-height:90px;resize:vertical" placeholder="Optional notes…"></textarea>
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
import { apiGet, apiSave, apiList, apiSubmit, apiCancel, apiAmend, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { useConfirm } from "../composables/useConfirm.js";

const route = useRoute();
const router = useRouter();
const { toast } = useToast();
const { confirm } = useConfirm();

// ── LIST STATE ──────────────────────────────────────────────
const loading = ref(false);
const list = ref([]);
const search = ref("");
const filterStatus = ref("");

const statusOptions = ["Draft", "Submitted", "Ordered", "Cancelled"];

const selectedName = computed(() => (route.params.name && route.params.name !== "new") ? route.params.name : (route.params.name === "new" ? "new" : null));

async function loadList() {
  try {
    const fields = ["name", "material_request_type", "posting_date", "production_plan", "status", "docstatus", "modified"];
    const r = await apiList("Material Request", { fields, limit: 1000, order: "modified desc" });
    list.value = r || [];
  } catch (e) {
    toast("Could not load Material Requests: " + e.message, "error");
  }
}

const sorted = computed(() => {
  let r = list.value;
  if (filterStatus.value) r = r.filter(i => i.status === filterStatus.value);
  const q = search.value.toLowerCase().trim();
  if (q) r = r.filter(i => [i.name, i.material_request_type, i.production_plan].filter(Boolean).join(" ").toLowerCase().includes(q));
  return r;
});

function statusClass(row) {
  const s = row.status;
  if (s === "Submitted" || s === "Ordered") return "badge-active";
  if (s === "Cancelled") return "badge-cancelled";
  return "badge-obsolete";
}

function selectMR(name) {
  router.push(`/manufacturing/material-request/${name}`);
}
function openAdd() {
  router.push("/manufacturing/material-request/new");
}
function goBackToList() {
  router.push("/manufacturing/material-request");
}

// ── DETAIL STATE ─────────────────────────────────────────────
const isNew = computed(() => route.params.name === "new");
const saving = ref(false);
const submitting = ref(false);

function emptyMR() {
  return {
    doctype: "Material Request",
    material_request_type: "Purchase",
    status: "Draft",
    posting_date: new Date().toISOString().slice(0, 10),
    company: "",
    production_plan: "",
    items: [],
    remarks: "",
  };
}
const mr = ref(emptyMR());

const companiesList = ref([]);
const itemsList = ref([]);
const uomList = ref([]);
const warehouseList = ref([]);

const readOnly = computed(() => !isNew.value && (mr.value.docstatus === 1 || mr.value.docstatus === 2));

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

    await loadList();
    if (route.params.name && !isNew.value) await loadMR();
    else if (isNew.value) mr.value.company = co || "";
  } catch (e) {
    toast("Error loading data: " + e.message, "error");
  }
  loading.value = false;
});

watch(() => route.params.name, async (name) => {
  if (!name) { mr.value = emptyMR(); return; }
  loading.value = true;
  try {
    if (isNew.value) {
      mr.value = emptyMR();
      const co = await resolveCompany();
      mr.value.company = co || "";
    } else {
      await loadMR();
    }
  } catch (e) {
    toast("Error loading Material Request: " + e.message, "error");
  }
  loading.value = false;
});

async function loadMR() {
  const data = await apiGet("Material Request", route.params.name);
  mr.value = data;
  if (!mr.value.items) mr.value.items = [];
}

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
    loadList();
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
    loadList();
  } catch (e) {
    toast(e.message, "error");
  }
  submitting.value = false;
}

async function cancelMR() {
  if (!(await confirm({ title: "Cancel Material Request?", body: "Cancel this Material Request?", okLabel: "Cancel Request", okStyle: "danger" }))) return;
  submitting.value = true;
  try {
    const doc = await apiCancel("Material Request", mr.value.name);
    mr.value = doc;
    toast("Cancelled");
    loadList();
  } catch (e) {
    toast(e.message, "error");
  }
  submitting.value = false;
}

async function amendMR() {
  submitting.value = true;
  try {
    const doc = await apiAmend("Material Request", mr.value.name);
    toast(`Revision ${doc.name} created`);
    router.push(`/manufacturing/material-request/${doc.name}`);
    loadList();
  } catch (e) {
    toast(e.message, "error");
  }
  submitting.value = false;
}

function fmtDate(d) {
  if (!d) return "—";
  const o = new Date(d);
  if (isNaN(o)) return d;
  return o.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

// ── UTIL ─────────────────────────────────────────────────────
const ICONS = {
  plus:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>',
};
function icon(name, size) {
  return (ICONS[name] || "").replace("<svg ", `<svg width="${size}" height="${size}" `);
}
</script>

<style scoped>
.bomx-page {
  --bx-bg:#F3F4F6; --bx-surface:#FFFFFF; --bx-surf2:#F8F9FC; --bx-border:#E2E8F0;
  --bx-text:#1A1D23; --bx-muted:#868E96;
  --bx-green:#2F9E44; --bx-greenS:#EBFBEE;
  --bx-red:#C92A2A; --bx-redS:#FFF5F5;
  --bx-amber:#E67700; --bx-amberS:#FFF3BF;
  --bx-blue:#1971C2; --bx-blueS:#E7F5FF;
  --bx-violet:#7048E8; --bx-violetS:#F3F0FF;
  --bx-mfg:#1a6ef7; --bx-mfgL:#2f74f5; --bx-mfgS:#EAF1FF; --bx-mfgB:#1e3a5f;
  --bx-radius:10px; --bx-rsm:6px;
  padding: 16px;
}
.bomx-two-col { display:grid; grid-template-columns: 340px 1fr; gap:16px; align-items:start; }
@media (max-width:1000px) { .bomx-two-col { grid-template-columns: 1fr; } }


/* ── List panel ── */
.bomx-list-panel { background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; display:flex; flex-direction:column; }
.bomx-panel-hdr { padding:12px 14px; border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); display:flex; align-items:center; justify-content:space-between; gap:8px; }
.bomx-panel-title { font-size:13px; font-weight:700; color:var(--bx-text); }
.bomx-count { font-size:12px; font-weight:400; color:var(--bx-muted); }
.bomx-status-filter { margin:8px 12px 0; width:calc(100% - 24px); font-size:12px; padding:6px 10px; }
.bomx-search { width:100%; border:none; outline:none; font-size:13px; padding:10px 14px; margin-top:8px; border-bottom:1px solid var(--bx-border); background:#fff; color:var(--bx-text); }
.bomx-search::placeholder { color:var(--bx-muted); }
.bomx-list { overflow-y:auto; max-height: calc(100vh - 230px); }
.bomx-list-empty { text-align:center; padding:32px; color:var(--bx-muted); font-size:13px; }
.bomx-item { padding:12px 14px; border-bottom:1px solid #F1F3F5; cursor:pointer; transition:background .12s; display:flex; flex-direction:column; gap:4px; }
.bomx-item:hover { background:#FAFBFF; }
.bomx-item.active { background:var(--bx-mfgS); border-left:3px solid var(--bx-mfg); }
.bomx-item-name { font-size:13.5px; font-weight:600; color:var(--bx-text); }
.bomx-item-meta { display:flex; align-items:center; gap:6px; font-size:12px; color:var(--bx-muted); }
.bomx-item-right { display:flex; align-items:center; gap:6px; margin-top:2px; }

/* ── Badges ── */
.bomx-badge { display:inline-flex; align-items:center; padding:2px 8px; border-radius:20px; font-size:11px; font-weight:600; white-space:nowrap; }
.badge-active { background:var(--bx-greenS); color:var(--bx-green); }
.badge-obsolete { background:var(--bx-amberS); color:var(--bx-amber); }
.badge-cancelled { background:var(--bx-redS); color:var(--bx-red); }

/* ── Detail panel ── */
.bomx-detail-panel { background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; display:flex; flex-direction:column; min-height: calc(100vh - 100px); }
.bomx-empty-state { text-align:center; padding:60px 20px; color:var(--bx-muted); }
.bomx-empty-icon { font-size:48px; margin-bottom:14px; }
.bomx-empty-title { font-size:16px; font-weight:700; color:var(--bx-text); margin-bottom:6px; }
.bomx-empty-sub { font-size:13px; line-height:1.6; max-width:280px; margin:0 auto 20px; }

.bomx-detail-hdr { padding:18px 22px; background:linear-gradient(135deg, var(--bx-mfgB), var(--bx-mfg)); }
.bomx-detail-title { font-size:18px; font-weight:700; color:#fff; margin-bottom:4px; }
.bomx-detail-meta { font-size:12.5px; color:rgba(255,255,255,.75); display:flex; align-items:center; gap:8px; flex-wrap:wrap; }

.bomx-hdr-fields { display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; padding:16px 22px; border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); }
.bomx-hf-label { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); margin-bottom:4px; }
.bomx-field-hint { font-size:12px; color:var(--bx-muted); margin-top:5px; }
.bomx-toggle-row { display:flex; gap:20px; padding:12px 22px; flex-wrap:wrap; background:var(--bx-surf2); border-bottom:1px solid var(--bx-border); }

.bomx-body { padding:20px 22px; overflow-y:auto; flex:1; }
.bomx-section-lbl { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--bx-muted); margin-bottom:8px; }
.bomx-tree-empty { text-align:center; padding:20px; color:var(--bx-muted); font-size:13px; }
.bomx-link { color:var(--bx-mfg); font-weight:600; cursor:pointer; }
.bomx-link:hover { text-decoration:underline; }

/* ── Child-row cards ── */
.bomx-rm-cards { display:flex; flex-direction:column; gap:10px; }
.bomx-rm-card { background:#fff; border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; box-shadow:0 1px 3px rgba(16,24,40,.04); }
.bomx-rm-card-hdr { display:flex; align-items:center; gap:10px; padding:10px 14px; background:var(--bx-mfgS); border-bottom:1px solid var(--bx-border); }
.bomx-rm-card-title { flex:1; min-width:0; font-weight:600; }
.bomx-rm-card-body { display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:10px; padding:12px 14px; }
.bomx-rm-field { display:flex; flex-direction:column; gap:4px; min-width:0; }
.bomx-rm-field label { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); }
.bomx-rm-field .bomx-fi { width:100%; }
@media (max-width:640px) {
  .bomx-rm-card-body { grid-template-columns:1fr 1fr; }
}

/* ── Buttons / inputs ── */
.bomx-fi { border:1px solid #CDD5E0; border-radius:var(--bx-rsm); padding:7px 9px; font-size:13px; color:var(--bx-text); background:#fff; outline:none; }
.bomx-fi:focus { border-color:var(--bx-mfg); box-shadow:0 0 0 3px rgba(180,83,9,.1); }
.bomx-fi:disabled { background:#F8F9FC; color:var(--bx-muted); }
select.bomx-fi {
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
select.bomx-fi:disabled { background-image: none; padding-right: 9px; }
.bomx-btn { display:inline-flex; align-items:center; gap:6px; padding:8px 16px; border-radius:var(--bx-rsm); font-size:13px; font-weight:600; cursor:pointer; border:1px solid transparent; line-height:1; white-space:nowrap; }
.bomx-btn:disabled { opacity:.6; cursor:not-allowed; }
.bomx-btn-sm { padding:6px 10px; font-size:12px; }
.bomx-btn-mfg { background:var(--bx-mfg); color:#fff; }
.bomx-btn-mfg:hover:not(:disabled) { background:var(--bx-mfgB); }
.bomx-btn-light { background:rgba(255,255,255,.92); color:var(--bx-mfgB); }
.bomx-btn-light:hover:not(:disabled) { background:#fff; }
.bomx-btn-ghost-inv { background:rgba(255,255,255,.15); color:#fff; border-color:rgba(255,255,255,.3); }
.bomx-btn-ghost-inv:hover:not(:disabled) { background:rgba(255,255,255,.25); }
.bomx-btn-icon { background:none; border:1px solid var(--bx-border); border-radius:5px; cursor:pointer; padding:4px 6px; display:inline-flex; color:var(--bx-muted); }
.bomx-btn-icon:hover { border-color:var(--bx-mfg); color:var(--bx-mfg); background:var(--bx-mfgS); }
.bomx-btn-icon.danger { color:var(--bx-red); }
.bomx-btn-icon.danger:hover { background:var(--bx-redS); border-color:var(--bx-red); }

.shimmer { background:linear-gradient(90deg,#f1f3f5 25%,#e9ecef 37%,#f1f3f5 63%); background-size:400% 100%; animation:shimmer 1.4s ease infinite; }
@keyframes shimmer { 0%{background-position:100% 50%} 100%{background-position:0 50%} }
</style>