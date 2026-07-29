<template>
<div class="psx-page">
  <div class="psx-two-col">

    <!-- ══════════ LEFT: PACKING SLIP LIST ══════════ -->
    <div class="psx-list-panel">
      <div class="psx-panel-hdr">
        <span class="psx-panel-title">📦 Packing Slips <span class="psx-count">({{ filtered.length }})</span></span>
        <button class="psx-btn psx-btn-mfg psx-btn-sm" @click="openAdd"><span v-html="icon('plus',12)"></span> New</button>
      </div>
      <select class="psx-fi psx-status-filter" v-model="filterStatus" @change="page=0">
        <option value="">All Status</option>
        <option value="Draft">Draft</option>
        <option value="In Progress">In Progress</option>
        <option value="Packed">Packed</option>
        <option value="Cancelled">Cancelled</option>
      </select>
      <input class="psx-search" v-model="search" type="text" placeholder="Search by name or work order…"/>
      <div class="psx-list">
        <template v-if="loading">
          <div v-for="n in 5" :key="n" class="psx-item"><div class="shimmer" style="height:38px;border-radius:6px"></div></div>
        </template>
        <div v-else-if="!sorted.length" class="psx-list-empty">No Packing Slips found</div>
        <div v-else v-for="row in sorted" :key="row.name"
             class="psx-item" :class="{active: selectedName === row.name}"
             @click="selectPS(row.name)">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px">
            <div class="psx-item-name">{{ row.production_item || row.name }}</div>
            <span class="psx-badge" :class="statusClass(row.status)">{{ row.status }}</span>
          </div>
          <div class="psx-item-meta">
            <span class="mono">{{ row.name }}</span>
            <span v-if="row.work_order">•</span>
            <span v-if="row.work_order">{{ row.work_order }}</span>
          </div>
          <div class="psx-item-right">
            <span style="font-size:12px;color:var(--bx-muted)">Qty:</span>
            <span class="mono" style="font-size:12.5px;font-weight:700;color:var(--bx-mfgB)">{{ fmt(row.qty_to_pack) }}</span>
            <span style="font-size:12px;color:var(--bx-muted);margin-left:auto">{{ fmtDate(row.packing_date) }}</span>
          </div>
        </div>
      </div>
      <!-- Pagination -->
      <div class="psx-list-pager">
        <span>{{ filtered.length ? page*pageSize+1 : 0 }}–{{ Math.min((page+1)*pageSize, filtered.length) }} of {{ filtered.length }}</span>
        <div style="display:flex;gap:6px;">
          <button class="psx-btn-icon" @click="page>0 && page--" :disabled="page===0">‹</button>
          <button class="psx-btn-icon" @click="(page+1)*pageSize<filtered.length && page++" :disabled="(page+1)*pageSize>=filtered.length">›</button>
        </div>
      </div>
    </div>

    <!-- ══════════ RIGHT: PACKING SLIP DETAIL ══════════ -->
    <div class="psx-detail-panel">

      <!-- Empty state -->
      <div v-if="!selectedName" class="psx-empty-state">
        <div class="psx-empty-icon">📄</div>
        <div class="psx-empty-title">Select a Packing Slip</div>
        <div class="psx-empty-sub">Choose a Packing Slip from the list to view or edit its details, or create a new one.</div>
        <button class="psx-btn psx-btn-mfg" @click="openAdd"><span v-html="icon('plus',13)"></span> Create Packing Slip</button>
      </div>

      <template v-else>
        <div v-if="detailLoading" class="psx-empty-state"><div class="shimmer" style="height:200px;border-radius:10px"></div></div>

        <template v-else>
          <!-- Header -->
          <div class="psx-detail-hdr">
            <div class="psx-hdr-flex">
              <div class="psx-hdr-info">
                <div class="psx-detail-title">{{ isNew ? 'New Packing Slip' : (ps.production_item || ps.name) }}</div>
                <div class="psx-detail-meta">
                  <span class="mono" v-if="!isNew">{{ ps.name }}</span>
                  <span v-if="!isNew">•</span>
                  <span>Qty to Pack: {{ ps.qty_to_pack || 0 }}</span>
                  <span>•</span>
                  <span class="psx-badge" :class="statusClass(ps.status)" style="font-size:11px">{{ ps.status }}</span>
                </div>
              </div>
              <div class="psx-hdr-actions">
                <button class="psx-btn psx-btn-ghost-inv" @click="goBackToList">Back</button>
                <button v-if="!isNew && ps.status!=='Cancelled'" class="psx-btn psx-btn-light" style="color:#C92A2A" @click="cancelPS" :disabled="saving">
                  {{ saving ? 'Cancelling…' : 'Cancel' }}
                </button>
                <button v-if="!isNew && ps.status==='In Progress'" class="psx-btn psx-btn-light" style="color:#2F9E44" @click="markPacked" :disabled="saving">
                  {{ saving ? 'Saving…' : 'Mark as Packed' }}
                </button>
                <button v-if="!isNew && ps.status==='Packed' && !ps.stock_entry" class="psx-btn psx-btn-mfg" @click="postStockConsumption" :disabled="postingStock || saving">
                  {{ postingStock ? 'Posting…' : '📦 Post Stock Consumption' }}
                </button>
                <button v-if="!readOnly" class="psx-btn psx-btn-light" @click="save" :disabled="saving || loading">
                  {{ saving ? 'Saving…' : (isNew ? 'Save' : 'Save Changes') }}
                </button>
              </div>
            </div>
          </div>

          <!-- Header fields -->
          <div class="psx-hdr-fields">
            <div>
              <div class="psx-hf-label">Work Order</div>
              <select class="psx-fi" v-model="ps.work_order" @change="onWOChange" :disabled="!isNew" style="width:100%">
                <option value="">— Select —</option>
                <option v-for="w in workOrderList" :key="w.name" :value="w.name">{{ w.name }} — {{ w.production_item }}</option>
              </select>
              <div v-if="!workOrderList.length" style="font-size:11px;color:#94a3b8;margin-top:4px">
                No submitted Work Orders on a Packing BOM found. Create a Work Order against a Packing-type BOM first.
              </div>
            </div>
            <div>
              <div class="psx-hf-label">Item Being Packed</div>
              <input class="psx-fi" :value="ps.production_item || '—'" disabled style="width:100%"/>
            </div>
            <div>
              <div class="psx-hf-label">Packing BOM</div>
              <input class="psx-fi" :value="ps.bom || '—'" disabled style="width:100%"/>
            </div>
            <div>
              <div class="psx-hf-label">Sourced From (Bulk WO)</div>
              <select class="psx-fi" v-model="ps.source_work_order" :disabled="readOnly" style="width:100%">
                <option value="">— None —</option>
                <option v-for="w in workOrderList" :key="w.name" :value="w.name">{{ w.name }} — {{ w.production_item }}</option>
              </select>
            </div>
            <div>
              <div class="psx-hf-label">Qty to Pack</div>
              <input class="psx-fi psx-fi-mono" type="number" v-model="ps.qty_to_pack" min="0.001" step="any" :disabled="readOnly" style="width:100%"/>
            </div>
            <div>
              <div class="psx-hf-label">Packing Date</div>
              <input class="psx-fi" type="date" v-model="ps.packing_date" :disabled="readOnly" style="width:100%"/>
            </div>
            <div>
              <div class="psx-hf-label">Packed By</div>
              <input class="psx-fi" v-model="ps.packed_by" :disabled="readOnly" style="width:100%"/>
            </div>
            <div>
              <div class="psx-hf-label">Consume Materials From</div>
              <select class="psx-fi" v-model="ps.source_warehouse" :disabled="postLocked" style="width:100%">
                <option value="">— Select —</option>
                <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
              </select>
            </div>
            <div>
              <div class="psx-hf-label">Receive Packed Goods At</div>
              <select class="psx-fi" v-model="ps.target_warehouse" :disabled="postLocked" style="width:100%">
                <option value="">— Defaults to Work Order FG Warehouse —</option>
                <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
              </select>
            </div>
            <div v-if="ps.stock_entry">
              <div class="psx-hf-label">Stock Entry Posted</div>
              <input class="psx-fi" :value="ps.stock_entry" disabled style="width:100%;color:var(--bx-green);font-weight:600;"/>
            </div>
          </div>

          <!-- Body -->
          <div class="psx-body">

            <!-- Items -->
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
              <div class="psx-section-lbl">Items to Pack</div>
              <div style="display:flex;gap:8px;">
                <button v-if="!readOnly && ps.work_order" class="psx-btn psx-btn-light psx-btn-sm" @click="loadItemsFromWO" :disabled="itemsLoading">
                  {{ itemsLoading ? 'Loading…' : '↻ Reload from WO' }}
                </button>
                <button v-if="!readOnly" class="psx-btn psx-btn-light psx-btn-sm" @click="addItem"><span v-html="icon('plus',11)"></span> Add Row</button>
              </div>
            </div>

            <div class="psx-item-cards">
              <div v-if="!ps.items || !ps.items.length" class="psx-tree-empty">No items. Select a Work Order and click "Reload from WO".</div>
              <div v-for="(row, idx) in ps.items" :key="idx" class="psx-item-card"
                :class="{ 'psx-item-card-done': flt(row.packed_qty) >= flt(row.required_qty) - 0.001 && flt(row.required_qty) > 0 }">
                <div class="psx-item-card-hdr">
                  <select class="psx-fi psx-fi-inline psx-item-card-title" v-model="row.item_code" :disabled="readOnly">
                    <option value="">— Select —</option>
                    <option v-for="i in itemsList" :key="i.name" :value="i.name">{{ i.item_name || i.name }}</option>
                  </select>
                  <button v-if="!readOnly" class="psx-btn-icon danger" @click="ps.items.splice(idx,1)">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                  </button>
                </div>
                <div class="psx-item-card-body">
                  <div class="psx-item-field">
                    <label>Required</label>
                    <input type="number" class="psx-fi psx-fi-mono" v-model="row.required_qty" step="any" :disabled="readOnly" />
                  </div>
                  <div class="psx-item-field">
                    <label>Packed</label>
                    <input type="number" class="psx-fi psx-fi-mono" v-model="row.packed_qty" min="0" step="any"
                      :style="flt(row.packed_qty) > flt(row.required_qty) ? 'border-color:var(--bx-red);' : ''" />
                  </div>
                  <div class="psx-item-field">
                    <label>UOM</label>
                    <select class="psx-fi" v-model="row.uom" :disabled="readOnly">
                      <option value="">—</option>
                      <option v-for="u in uomList" :key="u.name" :value="u.name">{{ u.name }}</option>
                    </select>
                  </div>
                  <div class="psx-item-field">
                    <label>Source Warehouse</label>
                    <select class="psx-fi" v-model="row.source_warehouse" :disabled="postLocked">
                      <option value="">— Use "Consume Materials From" above —</option>
                      <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
                    </select>
                  </div>
                  <div class="psx-item-field" v-if="row.batch_no || !readOnly">
                    <label>Batch</label>
                    <input class="psx-fi" v-model="row.batch_no" placeholder="—" :disabled="readOnly" />
                  </div>
                </div>
              </div>
            </div>

            <!-- Progress summary -->
            <div v-if="ps.items && ps.items.length" style="padding:12px 2px;display:flex;gap:24px;font-size:13px;color:var(--bx-muted);margin-top:6px;">
              <span><strong style="color:var(--bx-text);">{{ packedCount }}</strong> / {{ ps.items.length }} items fully packed</span>
              <span v-if="ps.status === 'Packed'" style="color:var(--bx-green);font-weight:600;">✓ All items packed</span>
            </div>

            <!-- Remarks -->
            <div style="margin-top:18px;">
              <div class="psx-section-lbl">Remarks</div>
              <textarea class="psx-fi" style="width:100%;resize:vertical;" rows="3" v-model="ps.remarks"></textarea>
            </div>

            <!-- Linked Work Order shortcut -->
            <div v-if="!isNew && ps.work_order" class="psx-lo-cell" style="margin-top:18px;display:flex;align-items:center;justify-content:space-between;">
              <div>
                <div class="psx-section-lbl" style="margin-bottom:2px;">Linked Work Order</div>
                <div style="font-size:13px;color:var(--bx-text);">{{ ps.work_order }}</div>
              </div>
              <span class="psx-link" @click="router.push(`/manufacturing/work-order/${ps.work_order}`)">Open Work Order ↗</span>
            </div>

            <!-- Sourced From (bulk WO) shortcut -->
            <div v-if="!isNew && ps.source_work_order" class="psx-lo-cell" style="margin-top:10px;display:flex;align-items:center;justify-content:space-between;">
              <div>
                <div class="psx-section-lbl" style="margin-bottom:2px;">Sourced From</div>
                <div style="font-size:13px;color:var(--bx-text);">Bulk item packed from {{ ps.source_work_order }}</div>
              </div>
              <span class="psx-link" @click="router.push(`/manufacturing/work-order/${ps.source_work_order}`)">Open Work Order ↗</span>
            </div>

          </div>

          <!-- Footer -->
          <div class="psx-footer">
            <div style="flex:1"></div>
            <button v-if="!readOnly" class="psx-btn psx-btn-mfg" @click="save" :disabled="saving || loading">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13"/><polyline points="7 3 7 8 15 8"/></svg>
              {{ saving ? 'Saving…' : (isNew ? 'Save Packing Slip' : 'Save Changes') }}
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
import { apiGet, apiList, apiSave, apiCall, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";

const route = useRoute();
const router = useRouter();
const { toast } = useToast();

// ── LIST STATE ──────────────────────────────────────────────
const loading = ref(false);
const list = ref([]);
const search = ref("");
const filterStatus = ref("");
const page = ref(0);
const pageSize = 20;

const selectedName = computed(() => (route.params.name && route.params.name !== "new") ? route.params.name : (route.params.name === "new" ? "new" : null));

async function loadList() {
  loading.value = true;
  try {
    const fields = ["name", "work_order", "production_item", "qty_to_pack", "packing_date", "status", "modified"];
    const r = await apiList("Packing Slip", { fields, limit: 1000, order: "modified desc" });
    list.value = r || [];
  } catch (e) {
    toast("Could not load Packing Slips", "error");
  }
  loading.value = false;
}

const filtered = computed(() => {
  let r = list.value;
  if (filterStatus.value) r = r.filter(i => i.status === filterStatus.value);
  const q = search.value.toLowerCase().trim();
  if (q) r = r.filter(i => [i.name, i.work_order, i.production_item].filter(Boolean).join(" ").toLowerCase().includes(q));
  return r;
});

const sorted = computed(() => filtered.value.slice(page.value * pageSize, (page.value + 1) * pageSize));

function statusClass(s) {
  if (s === "Packed") return "badge-active";
  if (s === "In Progress") return "badge-changed";
  if (s === "Cancelled") return "badge-removed";
  return "badge-draft";
}

function selectPS(name) {
  router.push(`/manufacturing/packing-slip/${name}`);
}
function openAdd() {
  router.push("/manufacturing/packing-slip/new");
}
function goBackToList() {
  router.push("/manufacturing/packing-slip");
}

// ── DETAIL STATE ─────────────────────────────────────────────
const isNew = computed(() => route.params.name === "new");
const detailLoading = ref(false);
const saving = ref(false);
const itemsLoading = ref(false);

function emptyPS() {
  return {
    doctype: "Packing Slip",
    work_order: "",
    production_item: "",
    bom: "",
    source_work_order: "",
    status: "Draft",
    qty_to_pack: 1,
    packing_date: new Date().toISOString().slice(0, 10),
    packed_by: "",
    source_warehouse: "",
    target_warehouse: "",
    stock_entry: "",
    posted_batch_no: "",
    items: [],
    remarks: "",
  };
}
const ps = ref(emptyPS());

const workOrderList = ref([]);
const itemsList = ref([]);
const uomList = ref([]);

const readOnly = computed(() => !isNew.value && (ps.value.status === "Packed" || ps.value.status === "Cancelled"));
// Warehouses (and the Post Stock Consumption action) lock only once stock
// has actually been posted -- they stay editable through "Packed" status so
// the user can pick warehouses before triggering the Stock Entry.
const postLocked = computed(() => !!ps.value.stock_entry || ps.value.status === "Cancelled");
const warehouseList = ref([]);
const postingStock = ref(false);
const packedCount = computed(() =>
  (ps.value.items || []).filter(r => flt(r.packed_qty) >= flt(r.required_qty) - 0.0001 && flt(r.required_qty) > 0).length
);

onMounted(async () => {
  loading.value = true;
  try {
    const co = await resolveCompany();
    const [wos, packingBoms, items, uoms, warehouses] = await Promise.all([
      apiList("Work Order", {
        fields: ["name", "production_item", "bom", "status", "qty", "produced_qty"],
        filters: [["docstatus", "=", 1], ["status", "!=", "Cancelled"]],
        limit: 500,
        order: "name desc",
      }),
      // A Packing Slip only ever consumes bulk stock into retail packs, which
      // is exactly what a "Packing" type BOM models (bulk_item + packing_items).
      // A regular "Manufacturing"/"Sub-Assembly" BOM explodes into raw
      // materials instead -- if a Work Order built on one of those slipped
      // through here, its raw-material breakdown would show up in the
      // Packing Slip's items table by mistake. Restricting the Work Order
      // picker to only Packing-BOM-backed orders prevents that at the source.
      apiList("BOM", {
        fields: ["name"],
        filters: [["bom_type", "=", "Packing"], ["docstatus", "=", 1]],
        limit: 2000,
      }),
      apiList("Item", { fields: ["name", "item_name", "stock_uom"], limit: 5000, order: "name asc" }),
      apiList("UOM", { fields: ["name"], limit: 200, order: "name asc" }),
      apiList("Warehouse", { fields: ["name"], filters: [["company", "=", co], ["is_group", "=", 0]], limit: 200, order: "name asc" }),
    ]);
    const packingBomNames = new Set((packingBoms || []).map(b => b.name));
    workOrderList.value = (wos || []).filter(w => packingBomNames.has(w.bom));
    itemsList.value = items || [];
    uomList.value = uoms || [];
    warehouseList.value = warehouses || [];
  } catch (e) {
    toast("Error loading manufacturing data: " + e.message, "error");
  }
  await loadList();
  if (route.params.name) await loadPS();
  loading.value = false;
});

watch(() => route.params.name, async (name) => {
  if (!name) { ps.value = emptyPS(); return; }
  await loadPS();
});

async function loadPS() {
  if (isNew.value) {
    ps.value = emptyPS();
    return;
  }
  detailLoading.value = true;
  try {
    const data = await apiGet("Packing Slip", route.params.name);
    ps.value = data;
    if (!ps.value.items) ps.value.items = [];
  } catch (e) {
    toast("Error loading Packing Slip: " + e.message, "error");
    goBackToList();
  }
  detailLoading.value = false;
}

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
      { bom: wo.bom, qty: flt(ps.value.qty_to_pack) || flt(wo.qty) || 1, work_order: wo.name }
    );
    ps.value.items = (breakdown.items || []).map(r => ({
      item_code: r.item_code,
      item_name: r.item_name || "",
      required_qty: r.required_qty,
      packed_qty: 0,
      uom: r.uom || "",
      source_warehouse: r.source_warehouse || "",
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
  ps.value.items.push({ item_code: "", item_name: "", required_qty: 1, packed_qty: 0, uom: "", source_warehouse: "" });
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
    loadList();
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
    loadList();
  } catch (e) {
    toast(e.message, "error");
  }
  saving.value = false;
}

async function postStockConsumption() {
  if (!ps.value.source_warehouse) return toast("Select a 'Consume Materials From' warehouse first", "error");
  postingStock.value = true;
  try {
    // Persist the chosen warehouses before posting, so the engine call
    // reads what's actually on screen rather than a stale saved value.
    const saved = await apiSave(ps.value);
    ps.value = saved;
    const stockEntry = await apiCall(
      "zoho_books_clone.manufacturing.packing_engine.post_packing_consumption",
      { packing_slip: ps.value.name }
    );
    toast(`Stock posted — ${stockEntry}`);
    await loadPS();
    loadList();
  } catch (e) {
    toast(e.message, "error");
  }
  postingStock.value = false;
}

async function cancelPS() {
  if (!confirm("Cancel this Packing Slip?")) return;
  saving.value = true;
  try {
    ps.value.status = "Cancelled";
    const doc = await apiSave(ps.value);
    ps.value = doc;
    toast("Packing Slip cancelled");
    loadList();
  } catch (e) {
    toast(e.message, "error");
  }
  saving.value = false;
}

// ── UTIL ─────────────────────────────────────────────────────
function flt(n) { const v = parseFloat(n); return isNaN(v) ? 0 : v; }
function fmt(n) { const v = parseFloat(n); return isNaN(v) ? "0.00" : v.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
function fmtDate(d) {
  if (!d) return "—";
  const o = new Date(d);
  return isNaN(o) ? d : o.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

const ICONS = {
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
};
function icon(name, size) {
  return (ICONS[name] || "").replace("<svg ", `<svg width="${size}" height="${size}" `);
}
</script>

<style scoped>
.psx-page {
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
.psx-two-col { display:grid; grid-template-columns: 340px 1fr; gap:16px; align-items:start; }
@media (max-width:1000px) { .psx-two-col { grid-template-columns: 1fr; } }


/* ── List panel ── */
.psx-list-panel { background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; display:flex; flex-direction:column; }
.psx-panel-hdr { padding:12px 14px; border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); display:flex; align-items:center; justify-content:space-between; gap:8px; }
.psx-panel-title { font-size:13px; font-weight:700; color:var(--bx-text); }
.psx-count { font-size:12px; font-weight:400; color:var(--bx-muted); }
.psx-status-filter { margin:8px 12px 0; width:calc(100% - 24px); font-size:12px; padding:6px 10px; }
.psx-search { width:100%; border:none; outline:none; font-size:13px; padding:10px 14px; margin-top:8px; border-bottom:1px solid var(--bx-border); background:#fff; color:var(--bx-text); }
.psx-search::placeholder { color:var(--bx-muted); }
.psx-list { overflow-y:auto; max-height: calc(100vh - 280px); }
.psx-list-empty { text-align:center; padding:32px; color:var(--bx-muted); font-size:13px; }
.psx-item { padding:12px 14px; border-bottom:1px solid #F1F3F5; cursor:pointer; transition:background .12s; display:flex; flex-direction:column; gap:4px; }
.psx-item:hover { background:#FAFBFF; }
.psx-item.active { background:var(--bx-mfgS); border-left:3px solid var(--bx-mfg); }
.psx-item-name { font-size:13.5px; font-weight:600; color:var(--bx-text); }
.psx-item-meta { display:flex; align-items:center; gap:6px; font-size:12px; color:var(--bx-muted); }
.psx-item-right { display:flex; align-items:center; gap:6px; margin-top:2px; }
.psx-list-pager { display:flex; align-items:center; justify-content:space-between; padding:8px 14px; border-top:1px solid var(--bx-border); background:var(--bx-surf2); font-size:11.5px; color:var(--bx-muted); }

/* ── Badges ── */
.psx-badge { display:inline-flex; align-items:center; padding:2px 8px; border-radius:20px; font-size:11px; font-weight:600; white-space:nowrap; }
.badge-active { background:var(--bx-greenS); color:var(--bx-green); }
.badge-draft { background:var(--bx-amberS); color:var(--bx-amber); }
.badge-obsolete { background:#F1F3F5; color:var(--bx-muted); }
.badge-changed { background:var(--bx-blueS); color:var(--bx-blue); }
.badge-removed { background:var(--bx-redS); color:var(--bx-red); }

/* ── Detail panel ── */
.psx-detail-panel { background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; display:flex; flex-direction:column; min-height: calc(100vh - 100px); }
.psx-empty-state { text-align:center; padding:60px 20px; color:var(--bx-muted); }
.psx-empty-icon { font-size:48px; margin-bottom:14px; }
.psx-empty-title { font-size:16px; font-weight:700; color:var(--bx-text); margin-bottom:6px; }
.psx-empty-sub { font-size:13px; line-height:1.6; max-width:280px; margin:0 auto 20px; }

.psx-detail-hdr { padding:18px 22px; background:linear-gradient(135deg, var(--bx-mfgB), var(--bx-mfg)); }
.psx-detail-title { font-size:18px; font-weight:700; color:#fff; margin-bottom:4px; }
.psx-hdr-flex { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; }
.psx-hdr-info { min-width:0; }
.psx-hdr-actions { display:flex; gap:6px; flex-shrink:0; flex-wrap:wrap; justify-content:flex-end; }
@media (max-width:640px) {
  .psx-detail-hdr { padding:14px 16px; }
  .psx-hdr-flex { flex-direction:column; align-items:stretch; }
  .psx-hdr-actions { justify-content:flex-start; }
  .psx-detail-title { font-size:16px; }
}
.psx-detail-meta { font-size:12.5px; color:rgba(255,255,255,.75); display:flex; align-items:center; gap:8px; flex-wrap:wrap; }

.psx-hdr-fields { display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; padding:16px 22px; border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); }
.psx-hf-label { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); margin-bottom:4px; }
@media (max-width:640px) { .psx-hdr-fields { grid-template-columns:1fr 1fr; } }

.psx-body { padding:20px 22px; overflow-y:auto; flex:1; }
.psx-section-lbl { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--bx-muted); margin-bottom:8px; }

/* ── Tree rows (items) ── */
.psx-tree-col-hdr { display:flex; align-items:center; padding:7px 10px 7px 12px; font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--bx-muted); border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); margin-bottom:4px; gap:8px; }
.psx-tree { display:flex; flex-direction:column; gap:2px; }
.psx-tree-empty { text-align:center; padding:20px; color:var(--bx-muted); font-size:13px; }
.psx-tree-row { display:flex; align-items:center; gap:8px; padding:8px 10px; border-radius:var(--bx-rsm); transition:background .1s; }
.psx-tree-row:hover { background:#F5F6FF; }
.psx-fi-inline { width:100%; }
.psx-tree-qty-inp { width:100%; text-align:right; }
.psx-tree-uom-inp { width:100%; }

.psx-lo-cell { background:var(--bx-surf2); border:1px solid var(--bx-border); border-radius:var(--bx-rsm); padding:12px 16px; }
.psx-link { color:var(--bx-mfg); font-weight:600; cursor:pointer; font-size:13px; }
.psx-link:hover { text-decoration:underline; }

/* ── Item cards (Items to Pack) ── */
.psx-item-cards { display:flex; flex-direction:column; gap:10px; }
.psx-item-card { background:#fff; border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; box-shadow:0 1px 3px rgba(16,24,40,.04); }
.psx-item-card-done { border-color:var(--bx-green); background:var(--bx-greenS); }
.psx-item-card-hdr { display:flex; align-items:center; gap:10px; padding:10px 12px; background:var(--bx-surf2); border-bottom:1px solid var(--bx-border); }
.psx-item-card-done .psx-item-card-hdr { background:var(--bx-greenS); }
.psx-item-card-title { flex:1; min-width:0; font-weight:600; }
.psx-item-card-body { display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; padding:12px 14px; }
.psx-item-field { display:flex; flex-direction:column; gap:4px; min-width:0; }
.psx-item-field label { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); }
.psx-item-field .psx-fi { width:100%; }
@media (max-width:480px) { .psx-item-card-body { grid-template-columns:1fr 1fr; } }

.psx-footer { padding:12px 22px; border-top:1px solid var(--bx-border); background:var(--bx-surf2); display:flex; justify-content:space-between; align-items:center; gap:8px; }

/* ── Buttons / inputs ── */
.psx-fi { border:1px solid #CDD5E0; border-radius:var(--bx-rsm); padding:7px 9px; font-size:13px; color:var(--bx-text); background:#fff; outline:none; }
.psx-fi:focus { border-color:var(--bx-mfg); box-shadow:0 0 0 3px rgba(180,83,9,.1); }
.psx-fi:disabled { background:#F8F9FC; color:var(--bx-muted); }
select.psx-fi {
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
select.psx-fi:disabled { background-image: none; padding-right: 9px; }
.psx-btn { display:inline-flex; align-items:center; gap:6px; padding:8px 16px; border-radius:var(--bx-rsm); font-size:13px; font-weight:600; cursor:pointer; border:1px solid transparent; line-height:1; white-space:nowrap; }
.psx-btn:disabled { opacity:.6; cursor:not-allowed; }
.psx-btn-sm { padding:6px 10px; font-size:12px; }
.psx-btn-mfg { background:var(--bx-mfg); color:#fff; }
.psx-btn-mfg:hover:not(:disabled) { background:var(--bx-mfgB); }
.psx-btn-light { background:rgba(255,255,255,.92); color:var(--bx-mfgB); border:1px solid var(--bx-border); }
.psx-btn-light:hover:not(:disabled) { background:#fff; }
.psx-btn-ghost-inv { background:rgba(255,255,255,.15); color:#fff; border-color:rgba(255,255,255,.3); }
.psx-btn-ghost-inv:hover:not(:disabled) { background:rgba(255,255,255,.25); }
.psx-btn-icon { background:none; border:1px solid var(--bx-border); border-radius:5px; cursor:pointer; padding:4px 6px; display:inline-flex; color:var(--bx-muted); }
.psx-btn-icon:hover { border-color:var(--bx-mfg); color:var(--bx-mfg); background:var(--bx-mfgS); }
.psx-btn-icon.danger { color:var(--bx-red); }
.psx-btn-icon.danger:hover { background:var(--bx-redS); border-color:var(--bx-red); }
.psx-btn-icon:disabled { opacity:.4; cursor:not-allowed; }

.shimmer { background:linear-gradient(90deg,#f1f3f5 25%,#e9ecef 37%,#f1f3f5 63%); background-size:400% 100%; animation:shimmer 1.4s ease infinite; }
@keyframes shimmer { 0%{background-position:100% 50%} 100%{background-position:0 50%} }
</style>