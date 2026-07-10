<template>
<div class="bomx-page">
  <div class="bomx-two-col">

    <!-- ══════════ LEFT: PRODUCTION PLAN LIST ══════════ -->
    <div class="bomx-list-panel">
      <div class="bomx-panel-hdr">
        <span class="bomx-panel-title">📅 All Production Plans <span class="bomx-count">({{ sorted.length }})</span></span>
        <button class="bomx-btn bomx-btn-mfg bomx-btn-sm" @click="openAdd"><span v-html="icon('plus',12)"></span> New</button>
      </div>
      <select class="bomx-fi bomx-status-filter" v-model="filterStatus">
        <option value="">All Status</option>
        <option v-for="s in statusOptions" :key="s" :value="s">{{ s }}</option>
      </select>
      <input class="bomx-search" v-model="search" type="text" placeholder="Search Production Plans…"/>
      <div class="bomx-list">
        <template v-if="loading">
          <div v-for="n in 5" :key="n" class="bomx-item"><div class="shimmer" style="height:38px;border-radius:6px"></div></div>
        </template>
        <div v-else-if="!sorted.length" class="bomx-list-empty">No Production Plans found</div>
        <div v-else v-for="row in sorted" :key="row.name"
             class="bomx-item" :class="{active: selectedName === row.name}"
             @click="selectPlan(row.name)">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px">
            <div class="bomx-item-name">{{ row.name }}</div>
            <span class="bomx-badge" :class="statusClass(row)">{{ row.status }}</span>
          </div>
          <div class="bomx-item-meta">
            <span class="mono">{{ fmtDate(row.posting_date) }}</span>
            <span v-if="row.company">•</span>
            <span v-if="row.company">{{ row.company }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ══════════ RIGHT: PRODUCTION PLAN DETAIL ══════════ -->
    <div class="bomx-detail-panel">

      <!-- Empty state -->
      <div v-if="!selectedName" class="bomx-empty-state">
        <div class="bomx-empty-icon">📅</div>
        <div class="bomx-empty-title">Select a Production Plan</div>
        <div class="bomx-empty-sub">Choose a Production Plan from the list to view demand, raw materials, and Work Orders.</div>
        <button class="bomx-btn bomx-btn-mfg" @click="openAdd"><span v-html="icon('plus',13)"></span> Create First Production Plan</button>
      </div>

      <template v-else>
        <div v-if="loading" class="bomx-empty-state"><div class="shimmer" style="height:200px;border-radius:10px"></div></div>

        <template v-else>
          <!-- Header -->
          <div class="bomx-detail-hdr">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap">
              <div style="min-width:0">
                <div class="bomx-detail-title">{{ isNew ? 'New Production Plan' : pp.name }}</div>
                <div class="bomx-detail-meta">
                  <span v-if="!isNew">{{ fmtDate(pp.posting_date) }}</span>
                  <span v-if="!isNew">•</span>
                  <span class="bomx-badge" :class="statusClass(pp)" style="font-size:11px" v-if="!isNew">{{ pp.status }}</span>
                </div>
              </div>
              <div style="display:flex;gap:6px;flex-shrink:0;flex-wrap:wrap;justify-content:flex-end">
                <button class="bomx-btn bomx-btn-ghost-inv" @click="goBackToList" :disabled="saving || submitting">Back</button>
                <button v-if="!isNew && pp.docstatus===2" class="bomx-btn bomx-btn-light" @click="amendPP" :disabled="submitting">
                  {{ submitting ? 'Amending…' : 'Amend' }}
                </button>
                <button v-if="!isNew && pp.docstatus===1" class="bomx-btn" style="background:var(--bx-redS);color:var(--bx-red)" @click="cancelPP" :disabled="submitting">
                  {{ submitting ? 'Cancelling…' : 'Cancel Plan' }}
                </button>
                <button v-if="!isNew && pp.docstatus===0" class="bomx-btn bomx-btn-light" @click="submitPP" :disabled="submitting || saving">
                  {{ submitting ? 'Submitting…' : 'Submit' }}
                </button>
                <button v-if="!readOnly" class="bomx-btn bomx-btn-light" @click="save" :disabled="saving || loading">
                  {{ saving ? 'Saving…' : (isNew ? 'Save Production Plan' : 'Save Changes') }}
                </button>
              </div>
            </div>
          </div>

          <!-- Tabs -->
          <div class="bomx-tabs">
            <button v-for="t in tabs" :key="t.id" class="bomx-tab" :class="{'bomx-tab--active': activeTab===t.id}" @click="activeTab=t.id">{{ t.label }}</button>
          </div>

          <div class="bomx-body">

            <!-- ── TAB: Plan ── -->
            <template v-if="activeTab==='plan'">
              <div class="bomx-section-lbl">Plan Details</div>
              <div class="bomx-hdr-fields" style="padding:0;border:none;background:none;grid-template-columns:1fr 1fr 1fr;margin-bottom:20px">
                <div>
                  <div class="bomx-hf-label">Posting Date</div>
                  <input class="bomx-fi" type="date" v-model="pp.posting_date" :disabled="readOnly" style="width:100%"/>
                </div>
              </div>

              <div class="bomx-section-lbl">Default Warehouses</div>
              <div class="bomx-hdr-fields" style="padding:0;border:none;background:none;grid-template-columns:1fr 1fr;margin-bottom:8px">
                <div>
                  <div class="bomx-hf-label">Default Source Warehouse (Raw Materials)</div>
                  <select class="bomx-fi" v-model="pp.default_source_warehouse" :disabled="readOnly" style="width:100%">
                    <option value="">— Select —</option>
                    <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
                  </select>
                  <div class="bomx-field-hint">Also the warehouse checked for availability on the Raw Materials tab.</div>
                </div>
                <div>
                  <div class="bomx-hf-label">Default Work-in-Progress Warehouse</div>
                  <select class="bomx-fi" v-model="pp.default_wip_warehouse" :disabled="readOnly" style="width:100%">
                    <option value="">— None —</option>
                    <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
                  </select>
                </div>
              </div>
              <div class="bomx-hdr-fields" style="padding:0;border:none;background:none;grid-template-columns:1fr 1fr;margin-bottom:20px">
                <div>
                  <div class="bomx-hf-label">Default Finished Goods Warehouse <span style="color:var(--bx-red)">*</span></div>
                  <select class="bomx-fi" v-model="pp.default_fg_warehouse" :disabled="readOnly" style="width:100%">
                    <option value="">— Select —</option>
                    <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
                  </select>
                </div>
                <div>
                  <div class="bomx-hf-label">Default Scrap / By-Product Warehouse</div>
                  <select class="bomx-fi" v-model="pp.default_scrap_warehouse" :disabled="readOnly" style="width:100%">
                    <option value="">— Defaults to Finished Goods Warehouse —</option>
                    <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
                  </select>
                </div>
              </div>

              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
                <div>
                  <div class="bomx-section-lbl" style="margin-bottom:2px">Demand from Sales Orders</div>
                  <div class="bomx-field-hint" style="margin-top:0">Optional — pull pending qty from open Sales Orders as a starting point.</div>
                </div>
                <div style="display:flex;gap:8px;flex-shrink:0" v-if="!readOnly">
                  <button class="bomx-btn bomx-btn-sm bomx-btn-light" style="color:var(--bx-mfgB);border:1px solid var(--bx-mfg)" @click="openSOPicker">
                    <span v-html="icon('plus',12)"></span> Add Sales Orders
                  </button>
                  <button class="bomx-btn bomx-btn-sm bomx-btn-light" style="color:var(--bx-mfgB);border:1px solid var(--bx-mfg)" @click="pullItemsFromSalesOrders" :disabled="itemsLoading || !pp.sales_orders.length">
                    {{ itemsLoading ? 'Pulling…' : 'Pull / Refresh Items' }}
                  </button>
                </div>
              </div>
              <div class="bomx-rm-cards" style="margin-bottom:20px">
                <div v-if="!pp.sales_orders || !pp.sales_orders.length" class="bomx-tree-empty">No Sales Orders added yet.</div>
                <div v-for="(so, idx) in pp.sales_orders" :key="idx" class="bomx-rm-card">
                  <div class="bomx-rm-card-hdr">
                    <span class="bomx-rm-card-title mono" style="font-weight:600">{{ so.sales_order }}</span>
                    <span style="font-size:12px;color:var(--bx-muted)">{{ so.status }}</span>
                    <button v-if="!readOnly" class="bomx-btn-icon danger" @click="pp.sales_orders.splice(idx,1)" title="Remove">
                      <span v-html="icon('trash',13)"></span>
                    </button>
                  </div>
                  <div class="bomx-rm-card-body" style="grid-template-columns:1fr 1fr">
                    <div class="bomx-rm-field"><label>Customer</label><div class="bomx-rm-static">{{ so.customer || '—' }}</div></div>
                    <div class="bomx-rm-field"><label>Delivery Date</label><div class="bomx-rm-static">{{ fmtDate(so.delivery_date) }}</div></div>
                  </div>
                </div>
              </div>

              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
                <span class="bomx-section-lbl" style="margin-bottom:0">Items to Manufacture</span>
                <button v-if="!readOnly" class="bomx-btn bomx-btn-sm bomx-btn-light" style="color:var(--bx-mfgB);border:1px solid var(--bx-mfg)" @click="addPOItem">
                  <span v-html="icon('plus',12)"></span> Add Row
                </button>
              </div>
              <div class="bomx-rm-cards">
                <div v-if="!pp.po_items || !pp.po_items.length" class="bomx-tree-empty">No items yet. Pull from Sales Orders above, or add a row manually.</div>
                <div v-for="(row, idx) in pp.po_items" :key="idx" class="bomx-rm-card">
                  <div class="bomx-rm-card-hdr">
                    <span class="bomx-rm-card-title">{{ row.item_name || row.item_code || 'New Row' }}</span>
                    <span v-if="flt(row.work_order_created_qty)" style="font-size:12px;color:var(--bx-muted)">WO: {{ fmt(row.work_order_created_qty) }}</span>
                    <button v-if="!readOnly" class="bomx-btn-icon danger" @click="pp.po_items.splice(idx,1)" title="Remove">
                      <span v-html="icon('trash',13)"></span>
                    </button>
                  </div>
                  <div class="bomx-rm-card-body">
                    <div class="bomx-rm-field" style="grid-column:span 2">
                      <label>Item to Manufacture</label>
                      <select class="bomx-fi" v-model="row.item_code" @change="onPOItemChange(row)" :disabled="readOnly">
                        <option value="">— Select —</option>
                        <option v-for="i in stockItems" :key="i.name" :value="i.name">{{ i.item_name || i.name }}</option>
                      </select>
                    </div>
                    <div class="bomx-rm-field" style="grid-column:span 2">
                      <label>BOM</label>
                      <select class="bomx-fi" v-model="row.bom_no" :disabled="readOnly">
                        <option value="">— Select Submitted BOM —</option>
                        <option v-for="b in bomsFor(row.item_code)" :key="b.name" :value="b.name">{{ b.name }}</option>
                      </select>
                    </div>
                    <div class="bomx-rm-field">
                      <label>Planned Qty</label>
                      <input class="bomx-fi bomx-fi-mono" type="number" v-model="row.planned_qty" min="0.01" step="any" :disabled="readOnly"/>
                    </div>
                    <div class="bomx-rm-field">
                      <label>FG Warehouse</label>
                      <select class="bomx-fi" v-model="row.warehouse" :disabled="readOnly">
                        <option value="">— Use Default —</option>
                        <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>
            </template>

            <!-- ── TAB: Raw Materials ── -->
            <template v-if="activeTab==='materials'">
              <div class="bomx-prod-card">
                <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap">
                  <div>
                    <div class="bomx-section-lbl" style="margin-bottom:2px">Raw Material Requirement</div>
                    <div style="font-size:12.5px;color:var(--bx-muted)">Explodes the BOM for every Item to Manufacture and compares against on-hand stock in the Default Source Warehouse.</div>
                  </div>
                  <div style="display:flex;gap:8px;flex-shrink:0">
                    <button v-if="!isNew && pp.docstatus===1 && hasShortfall" class="bomx-btn bomx-btn-sm bomx-btn-light" style="color:var(--bx-mfgB);border:1px solid var(--bx-mfg)" @click="createMaterialRequests" :disabled="actionLoading==='mr'">
                      {{ actionLoading === 'mr' ? 'Creating…' : 'Create Material Requests' }}
                    </button>
                    <button class="bomx-btn bomx-btn-mfg bomx-btn-sm" @click="calculateRawMaterials" :disabled="mrLoading || !pp.po_items.length">
                      {{ mrLoading ? 'Calculating…' : 'Calculate Requirement' }}
                    </button>
                  </div>
                </div>
              </div>

              <div class="bomx-rm-cards">
                <div v-if="!pp.mr_items || !pp.mr_items.length" class="bomx-tree-empty">No requirement calculated yet. Click "Calculate Requirement" above.</div>
                <div v-for="(m, idx) in pp.mr_items" :key="idx" class="bomx-rm-card">
                  <div class="bomx-rm-card-hdr">
                    <span class="bomx-rm-card-title">{{ m.item_name || m.item_code }}</span>
                    <span class="bomx-badge" :class="flt(m.shortfall_qty) > 0 ? 'badge-cancelled' : 'badge-active'">
                      {{ flt(m.shortfall_qty) > 0 ? 'Short ' + fmt(m.shortfall_qty) : 'OK' }}
                    </span>
                  </div>
                  <div class="bomx-rm-card-body" style="grid-template-columns:1fr 1fr">
                    <div class="bomx-rm-field"><label>Required Qty</label><div class="bomx-rm-static mono">{{ fmt(m.required_qty) }} {{ m.uom }}</div></div>
                    <div class="bomx-rm-field"><label>Available Qty</label><div class="bomx-rm-static mono">{{ fmt(m.available_qty) }}</div></div>
                  </div>
                </div>
              </div>
            </template>

            <!-- ── TAB: Work Orders ── -->
            <template v-if="activeTab==='work-orders'">
              <div v-if="isNew" class="bomx-tree-empty">Save and submit the Production Plan first to create Work Orders.</div>
              <template v-else>
                <div class="bomx-prod-card" v-if="pp.docstatus===1">
                  <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap">
                    <div>
                      <div class="bomx-section-lbl" style="margin-bottom:2px">Create Work Orders</div>
                      <div style="font-size:12.5px;color:var(--bx-muted)">Generates one Draft Work Order per row for whatever Planned Qty doesn't already have one. Review and submit each Work Order from there.</div>
                    </div>
                    <div style="display:flex;gap:8px;flex-shrink:0">
                      <button v-if="hasDraftWorkOrders" class="bomx-btn bomx-btn-sm bomx-btn-light" style="color:var(--bx-mfgB);border:1px solid var(--bx-mfg)" @click="bulkSubmitWorkOrders" :disabled="actionLoading==='bulk-submit'">
                        {{ actionLoading === 'bulk-submit' ? 'Submitting…' : 'Submit All Work Orders' }}
                      </button>
                      <button class="bomx-btn bomx-btn-mfg bomx-btn-sm" @click="createWorkOrders" :disabled="actionLoading || !pendingWOQty">
                        {{ actionLoading==='wo' ? 'Creating…' : 'Create Work Orders' }}
                      </button>
                    </div>
                  </div>
                  <div class="bomx-field-hint" v-if="!pendingWOQty">Every row already has a Work Order for its full Planned Qty.</div>
                </div>

                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
                  <span class="bomx-section-lbl" style="margin-bottom:0">Linked Work Orders</span>
                  <button class="bomx-btn bomx-btn-sm bomx-btn-light" style="color:var(--bx-mfgB);border:1px solid var(--bx-mfg)" @click="loadWorkOrders" :disabled="woLoading">Refresh</button>
                </div>
                <div class="bomx-rm-cards">
                  <div v-if="!workOrders.length" class="bomx-tree-empty">No Work Orders created yet.</div>
                  <div v-for="w in workOrders" :key="w.name" class="bomx-rm-card" style="cursor:pointer" @click="router.push(`/manufacturing/work-order/${w.name}`)">
                    <div class="bomx-rm-card-hdr">
                      <span class="bomx-rm-card-title mono" style="font-weight:600">{{ w.name }}</span>
                      <span class="bomx-badge" :class="woStatusClass(w)">{{ w.status }}</span>
                    </div>
                    <div class="bomx-rm-card-body" style="grid-template-columns:1fr 1fr">
                      <div class="bomx-rm-field"><label>Item</label><div class="bomx-rm-static">{{ w.item_name || w.production_item }}</div></div>
                      <div class="bomx-rm-field"><label>Qty</label><div class="bomx-rm-static mono">{{ fmt(w.qty) }}</div></div>
                    </div>
                  </div>
                </div>
              </template>
            </template>

            <!-- ── TAB: More Information ── -->
            <template v-if="activeTab==='more'">
              <div class="bomx-section-lbl">Remarks</div>
              <textarea class="bomx-fi" v-model="pp.remarks" rows="3" :disabled="readOnly" style="width:100%;min-height:90px;resize:vertical;margin-bottom:20px" placeholder="Optional notes…"></textarea>
              <template v-if="pp.amended_from">
                <div class="bomx-section-lbl">Amended From</div>
                <span class="bomx-link" @click="router.push(`/manufacturing/production-plan/${pp.amended_from}`)">{{ pp.amended_from }}</span>
              </template>
            </template>

          </div>
        </template>
      </template>
    </div>

  </div>

  <!-- Sales Order picker modal -->
  <div v-if="showSOPickerModal" class="bomx-modal-overlay" @click.self="showSOPickerModal=false">
    <div class="bomx-modal" style="width:560px;max-width:94vw">
      <div class="bomx-modal-title">Add Sales Orders</div>
      <div class="bomx-modal-body">
        <div v-if="soPickerLoading" class="bomx-tree-empty">Loading open Sales Orders…</div>
        <div v-else-if="!soPickerList.length" class="bomx-tree-empty">No open Sales Orders with pending delivery found.</div>
        <div v-else class="bomx-rm-cards" style="max-height:360px;overflow-y:auto">
          <div v-for="o in soPickerList" :key="o.name" class="bomx-rm-card" style="cursor:pointer" @click="toggleSOPick(o.name)">
            <div class="bomx-rm-card-hdr">
              <input type="checkbox" :checked="soPickerSelected.includes(o.name)" @click.stop="toggleSOPick(o.name)"/>
              <span class="bomx-rm-card-title mono" style="font-weight:600">{{ o.name }}</span>
              <span style="font-size:12px;color:var(--bx-muted)">{{ o.status }}</span>
            </div>
            <div class="bomx-rm-card-body" style="grid-template-columns:1fr 1fr">
              <div class="bomx-rm-field"><label>Customer</label><div class="bomx-rm-static">{{ o.customer_name }}</div></div>
              <div class="bomx-rm-field"><label>Delivery Date</label><div class="bomx-rm-static">{{ fmtDate(o.delivery_date) }}</div></div>
            </div>
          </div>
        </div>
      </div>
      <div class="bomx-modal-actions">
        <button class="bomx-btn" style="background:#fff;border:1px solid var(--bx-border)" @click="showSOPickerModal=false">Cancel</button>
        <button class="bomx-btn bomx-btn-mfg" @click="confirmSOPicker" :disabled="!soPickerSelected.length">Add {{ soPickerSelected.length || '' }}</button>
      </div>
    </div>
  </div>

</div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet, apiSave, apiList, apiSubmit, apiCancel, apiAmend, apiCall, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";

const ENGINE = "zoho_books_clone.manufacturing.production_plan_engine.";

const route = useRoute();
const router = useRouter();
const { toast } = useToast();

// ── LIST STATE ──────────────────────────────────────────────
const loading = ref(false);
const list = ref([]);
const search = ref("");
const filterStatus = ref("");

const statusOptions = ["Draft", "Submitted", "Work Orders Created", "Completed", "Cancelled"];

const selectedName = computed(() => (route.params.name && route.params.name !== "new") ? route.params.name : (route.params.name === "new" ? "new" : null));

async function loadList() {
  try {
    const fields = ["name", "posting_date", "company", "status", "docstatus", "modified"];
    const r = await apiList("Production Plan", { fields, limit: 1000, order: "modified desc" });
    list.value = r || [];
  } catch (e) {
    toast("Could not load Production Plans: " + e.message, "error");
  }
}

const sorted = computed(() => {
  let r = list.value;
  if (filterStatus.value) r = r.filter(i => i.status === filterStatus.value);
  const q = search.value.toLowerCase().trim();
  if (q) r = r.filter(i => (i.name || "").toLowerCase().includes(q));
  return r;
});

function statusClass(row) {
  if (row.status === "Completed" || row.status === "Work Orders Created") return "badge-active";
  if (row.status === "Cancelled") return "badge-cancelled";
  if (row.status === "Draft") return "badge-obsolete";
  return "badge-inprocess";
}
function woStatusClass(w) {
  if (w.status === "Completed") return "badge-active";
  if (w.status === "Cancelled") return "badge-cancelled";
  if (w.status === "Draft") return "badge-obsolete";
  if (w.status === "Stopped") return "badge-stopped";
  return "badge-inprocess";
}

function selectPlan(name) {
  router.push(`/manufacturing/production-plan/${name}`);
}
function openAdd() {
  router.push("/manufacturing/production-plan/new");
}
function goBackToList() {
  router.push("/manufacturing/production-plan");
}

// ── DETAIL STATE ─────────────────────────────────────────────
const isNew = computed(() => route.params.name === "new");
const saving = ref(false);
const submitting = ref(false);
const itemsLoading = ref(false);
const mrLoading = ref(false);
const actionLoading = ref(false);
const woLoading = ref(false);

const activeTab = ref("plan");
const tabs = [
  { id: "plan",         label: "Plan" },
  { id: "materials",    label: "Raw Materials" },
  { id: "work-orders",  label: "Work Orders" },
  { id: "more",          label: "More Information" },
];

function emptyPP() {
  return {
    doctype: "Production Plan",
    posting_date: new Date().toISOString().slice(0, 10),
    status: "Draft",
    company: "",
    default_source_warehouse: "",
    default_wip_warehouse: "",
    default_fg_warehouse: "",
    default_scrap_warehouse: "",
    sales_orders: [],
    po_items: [],
    mr_items: [],
    remarks: "",
  };
}
const pp = ref(emptyPP());

const stockItems = ref([]);
const bomList = ref([]);
const warehouseList = ref([]);
const workOrders = ref([]);

const EMPTY_PO_ITEM = () => ({ item_code: "", item_name: "", bom_no: "", planned_qty: 1, stock_uom: "", warehouse: "", sales_order: "", work_order_created_qty: 0 });

// docstatus: 0 = Draft, 1 = Submitted, 2 = Cancelled. Once submitted, the
// plan (items/warehouses/sales orders) is locked — from here on, progress
// happens only through Create Work Orders on the Work Orders tab.
const readOnly = computed(() => !isNew.value && (pp.value.docstatus === 1 || pp.value.docstatus === 2));

onMounted(async () => {
  loading.value = true;
  try {
    const co = await resolveCompany();
    if (isNew.value) pp.value.company = co;

    const stk = await apiList("Item", { fields: ["name", "item_name", "stock_uom"], filters: [["is_stock_item", "=", 1]], limit: 5000, order: "name asc" });
    stockItems.value = stk || [];

    const boms = await apiList("BOM", { fields: ["name", "item", "quantity", "is_default", "docstatus"], filters: [["docstatus", "=", 1]], limit: 2000, order: "name asc" });
    bomList.value = boms || [];

    const whs = await apiList("Warehouse", { fields: ["name"], filters: co ? [["company", "=", co], ["is_group", "=", 0]] : [["is_group", "=", 0]], limit: 1000, order: "name asc" });
    warehouseList.value = whs || [];

    await loadList();
    if (route.params.name) {
      await loadPP();
    } else {
      // New plan — prefill default warehouses from Manufacturing Settings
      try {
        const ms = await apiCall(
          "zoho_books_clone.manufacturing.doctype.manufacturing_settings.manufacturing_settings.get_manufacturing_defaults"
        );
        if (ms) {
          if (!pp.value.default_source_warehouse && ms.default_source_warehouse)
            pp.value.default_source_warehouse = ms.default_source_warehouse;
          if (!pp.value.default_wip_warehouse && ms.default_wip_warehouse)
            pp.value.default_wip_warehouse = ms.default_wip_warehouse;
          if (!pp.value.default_fg_warehouse && ms.default_fg_warehouse)
            pp.value.default_fg_warehouse = ms.default_fg_warehouse;
          if (!pp.value.default_scrap_warehouse && ms.default_scrap_warehouse)
            pp.value.default_scrap_warehouse = ms.default_scrap_warehouse;
        }
      } catch (e) {
        // non-fatal — settings may not be configured yet
      }
    }
  } catch (e) {
    toast("Error loading data: " + e.message, "error");
  }
  loading.value = false;
});

watch(() => route.params.name, async (name) => {
  activeTab.value = "plan";
  if (!name) { pp.value = emptyPP(); return; }
  loading.value = true;
  try {
    await loadPP();
  } catch (e) {
    toast("Error loading Production Plan: " + e.message, "error");
  }
  loading.value = false;
});

async function loadPP() {
  if (isNew.value) {
    pp.value = emptyPP();
    return;
  }
  const data = await apiGet("Production Plan", route.params.name);
  pp.value = data;
  if (!pp.value.sales_orders) pp.value.sales_orders = [];
  if (!pp.value.po_items) pp.value.po_items = [];
  if (!pp.value.mr_items) pp.value.mr_items = [];
  if (pp.value.docstatus === 1) await loadWorkOrders();
}

function bomsFor(itemCode) {
  if (!itemCode) return bomList.value;
  return bomList.value.filter(b => b.item === itemCode);
}

function onPOItemChange(row) {
  const item = stockItems.value.find(i => i.name === row.item_code);
  row.item_name = item ? item.item_name : "";
  row.stock_uom = item ? item.stock_uom : "";
  const candidates = bomsFor(row.item_code);
  const def = candidates.find(b => b.is_default) || candidates[0];
  row.bom_no = def ? def.name : "";
}

function addPOItem() { pp.value.po_items.push(EMPTY_PO_ITEM()); }

// ── Sales Order picker ──────────────────────────────────────────────────
const showSOPickerModal = ref(false);
const soPickerList = ref([]);
const soPickerSelected = ref([]);
const soPickerLoading = ref(false);

async function openSOPicker() {
  showSOPickerModal.value = true;
  soPickerSelected.value = [];
  soPickerLoading.value = true;
  try {
    const result = await apiCall(ENGINE + "get_open_sales_orders", { company: pp.value.company });
    const existing = new Set((pp.value.sales_orders || []).map(r => r.sales_order));
    soPickerList.value = (result || []).filter(o => !existing.has(o.name));
  } catch (e) {
    toast(e.message, "error");
  }
  soPickerLoading.value = false;
}

function toggleSOPick(name) {
  const i = soPickerSelected.value.indexOf(name);
  if (i >= 0) soPickerSelected.value.splice(i, 1);
  else soPickerSelected.value.push(name);
}

function confirmSOPicker() {
  const chosen = soPickerList.value.filter(o => soPickerSelected.value.includes(o.name));
  chosen.forEach(o => {
    pp.value.sales_orders.push({
      sales_order: o.name,
      customer: o.customer_name,
      delivery_date: o.delivery_date,
      status: o.status,
      grand_total: o.grand_total,
    });
  });
  showSOPickerModal.value = false;
}

async function pullItemsFromSalesOrders() {
  const soNames = (pp.value.sales_orders || []).map(r => r.sales_order).filter(Boolean);
  if (!soNames.length) return toast("Add at least one Sales Order first", "error");
  itemsLoading.value = true;
  try {
    const items = await apiCall(ENGINE + "get_items_from_sales_orders", { sales_orders: soNames });
    // Keep manually-added rows (no sales_order tag); replace SO-sourced rows
    // with the freshly aggregated set so re-pulling reflects any delivery
    // that's happened since.
    const manual = (pp.value.po_items || []).filter(r => !r.sales_order);
    pp.value.po_items = [...manual, ...(items || []).map(i => ({ ...EMPTY_PO_ITEM(), ...i }))];
    toast(`Pulled ${(items || []).length} item(s) from ${soNames.length} Sales Order(s)`);
  } catch (e) {
    toast(e.message, "error");
  }
  itemsLoading.value = false;
}

// ── Raw Materials ────────────────────────────────────────────────────────
async function calculateRawMaterials() {
  if (!pp.value.po_items.length) return toast("Add items to manufacture first", "error");
  mrLoading.value = true;
  try {
    const rows = pp.value.po_items.map(r => ({ item_code: r.item_code, bom_no: r.bom_no, planned_qty: r.planned_qty }));
    pp.value.mr_items = await apiCall(ENGINE + "get_raw_materials", { po_items: rows, warehouse: pp.value.default_source_warehouse || undefined });
    toast("Raw material requirement calculated");
  } catch (e) {
    toast(e.message, "error");
  }
  mrLoading.value = false;
}

// ── Work Orders ──────────────────────────────────────────────────────────
const pendingWOQty = computed(() => (pp.value.po_items || []).some(r => flt(r.planned_qty) - flt(r.work_order_created_qty) > 0.0001));
const hasShortfall = computed(() => (pp.value.mr_items || []).some(r => flt(r.shortfall_qty) > 0.0001));
const hasDraftWorkOrders = computed(() => workOrders.value.some(w => w.status === "Draft"));

async function loadWorkOrders() {
  woLoading.value = true;
  try {
    workOrders.value = await apiList("Work Order", {
      fields: ["name", "production_item", "item_name", "qty", "status"],
      filters: [["production_plan", "=", pp.value.name]],
      limit: 200, order: "creation desc",
    }) || [];
  } catch (e) { /* non-fatal */ }
  woLoading.value = false;
}

async function createWorkOrders() {
  actionLoading.value = "wo";
  try {
    const created = await apiCall(ENGINE + "create_work_orders", { production_plan: pp.value.name });
    toast(`Created ${created.length} Work Order(s)`);
    await loadPP();
  } catch (e) {
    toast(e.message, "error");
  }
  actionLoading.value = false;
}

async function bulkSubmitWorkOrders() {
  if (!confirm("Submit all Draft Work Orders linked to this Production Plan? They will be locked for editing.")) return;
  actionLoading.value = "bulk-submit";
  try {
    const result = await apiCall(ENGINE + "bulk_submit_work_orders", { production_plan: pp.value.name });
    const sub = (result.submitted || []).length;
    const err = (result.errors || []).length;
    if (err > 0) {
      toast(`Submitted ${sub}, but ${err} Work Order(s) failed — check each individually.`, "error");
    } else {
      toast(`${sub} Work Order(s) submitted successfully`);
    }
    await loadWorkOrders();
    await loadPP();
  } catch (e) {
    toast(e.message, "error");
  }
  actionLoading.value = false;
}

async function createMaterialRequests() {
  actionLoading.value = "mr";
  try {
    const names = await apiCall(ENGINE + "create_material_requests", { production_plan: pp.value.name });
    toast(`Material Request ${names[0]} created for shortfall items`);
  } catch (e) {
    toast(e.message, "error");
  }
  actionLoading.value = false;
}

// ── Save / Submit / Cancel / Amend ───────────────────────────────────────
async function save() {
  if (!pp.value.po_items || !pp.value.po_items.length) return toast("Add at least one item to manufacture", "error");
  if (!pp.value.default_fg_warehouse) return toast("Default Finished Goods Warehouse is required", "error");
  for (const r of pp.value.po_items) {
    if (!flt(r.planned_qty) || flt(r.planned_qty) <= 0) return toast(`Row for ${r.item_code || '(blank)'}: Planned Qty must be greater than 0`, "error");
  }

  saving.value = true;
  try {
    const doc = await apiSave(pp.value);
    toast(isNew.value ? "Production Plan created" : "Production Plan updated");
    if (isNew.value) {
      router.replace(`/manufacturing/production-plan/${doc.name}`);
    } else {
      pp.value = doc;
    }
    loadList();
  } catch (e) {
    toast(e.message, "error");
  }
  saving.value = false;
}

async function submitPP() {
  if (!pp.value.name) return;
  submitting.value = true;
  try {
    const doc = await apiSubmit("Production Plan", pp.value.name);
    pp.value = doc;
    toast("Production Plan submitted");
    loadList();
  } catch (e) {
    toast(e.message, "error");
  }
  submitting.value = false;
}

async function cancelPP() {
  if (!pp.value.name) return;
  if (!confirm("Cancel this Production Plan?")) return;
  submitting.value = true;
  try {
    const doc = await apiCancel("Production Plan", pp.value.name);
    pp.value = doc;
    toast("Production Plan cancelled");
    loadList();
  } catch (e) {
    toast(e.message, "error");
  }
  submitting.value = false;
}

async function amendPP() {
  if (!pp.value.name) return;
  submitting.value = true;
  try {
    const doc = await apiAmend("Production Plan", pp.value.name);
    toast(`New revision ${doc.name} created`);
    router.push(`/manufacturing/production-plan/${doc.name}`);
    loadList();
  } catch (e) {
    toast(e.message, "error");
  }
  submitting.value = false;
}

function flt(n) { const v = parseFloat(n); return isNaN(v) ? 0 : v; }
function fmt(n) {
  if (isNaN(n) || n == null) return "0.00";
  return Number(n).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function fmtDate(d) {
  if (!d) return "";
  const obj = new Date(d);
  if (isNaN(obj)) return d;
  return obj.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
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
  --bx-mfg:#B45309; --bx-mfgL:#D97706; --bx-mfgS:#FFFBEB; --bx-mfgB:#92400E;
  --bx-radius:10px; --bx-rsm:6px;
  padding: 16px;
}
.bomx-two-col { display:grid; grid-template-columns: 340px 1fr; gap:16px; align-items:start; }
@media (max-width:1000px) { .bomx-two-col { grid-template-columns: 1fr; } }

.mono { font-family: "DM Mono", ui-monospace, monospace; }

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

/* ── Badges ── */
.bomx-badge { display:inline-flex; align-items:center; padding:2px 8px; border-radius:20px; font-size:11px; font-weight:600; white-space:nowrap; }
.badge-active { background:var(--bx-greenS); color:var(--bx-green); }
.badge-obsolete { background:#F1F3F5; color:var(--bx-muted); }
.badge-cancelled { background:var(--bx-redS); color:var(--bx-red); }
.badge-stopped { background:var(--bx-amberS); color:var(--bx-amber); }
.badge-inprocess { background:var(--bx-blueS); color:var(--bx-blue); }

/* ── Detail panel ── */
.bomx-detail-panel { background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; display:flex; flex-direction:column; min-height: calc(100vh - 100px); }
.bomx-empty-state { text-align:center; padding:60px 20px; color:var(--bx-muted); }
.bomx-empty-icon { font-size:48px; margin-bottom:14px; }
.bomx-empty-title { font-size:16px; font-weight:700; color:var(--bx-text); margin-bottom:6px; }
.bomx-empty-sub { font-size:13px; line-height:1.6; max-width:280px; margin:0 auto 20px; }

.bomx-detail-hdr { padding:18px 22px; background:linear-gradient(135deg, var(--bx-mfgB), var(--bx-mfg)); }
.bomx-detail-title { font-size:18px; font-weight:700; color:#fff; margin-bottom:4px; }
.bomx-detail-meta { font-size:12.5px; color:rgba(255,255,255,.75); display:flex; align-items:center; gap:8px; flex-wrap:wrap; }

/* ── Tabs ── */
.bomx-tabs { display:flex; gap:2px; padding:0 22px; background:var(--bx-surf2); border-bottom:1px solid var(--bx-border); overflow-x:auto; scrollbar-width:none; }
.bomx-tabs::-webkit-scrollbar { display:none; }
.bomx-tab { padding:10px 14px; border:none; background:none; cursor:pointer; font-size:12.5px; font-weight:600; color:var(--bx-muted); white-space:nowrap; border-bottom:2px solid transparent; margin-bottom:-1px; transition:color .15s; }
.bomx-tab:hover { color:var(--bx-mfgB); }
.bomx-tab--active { color:var(--bx-mfgB); border-bottom-color:var(--bx-mfg); }

.bomx-hdr-fields { display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; padding:16px 22px; border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); }
.bomx-hf-label { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); margin-bottom:4px; }
.bomx-field-hint { font-size:12px; color:var(--bx-muted); margin-top:5px; }

.bomx-body { padding:20px 22px; overflow-y:auto; flex:1; }
.bomx-section-lbl { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--bx-muted); margin-bottom:8px; }
.bomx-tree-empty { text-align:center; padding:20px; color:var(--bx-muted); font-size:13px; }
.bomx-link { color:var(--bx-mfg); font-weight:600; cursor:pointer; }
.bomx-link:hover { text-decoration:underline; }

.bomx-prod-card { background:var(--bx-surf2); border:1px solid var(--bx-border); border-radius:var(--bx-radius); padding:16px; margin-bottom:16px; }

/* ── Child-row cards ── */
.bomx-rm-cards { display:flex; flex-direction:column; gap:10px; }
.bomx-rm-card { background:#fff; border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; box-shadow:0 1px 3px rgba(16,24,40,.04); }
.bomx-rm-card-hdr { display:flex; align-items:center; gap:10px; padding:10px 14px; background:var(--bx-mfgS); border-bottom:1px solid var(--bx-border); }
.bomx-rm-card-title { flex:1; min-width:0; font-weight:600; }
.bomx-rm-card-body { display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:10px; padding:12px 14px; }
.bomx-rm-field { display:flex; flex-direction:column; gap:4px; min-width:0; }
.bomx-rm-field label { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); }
.bomx-rm-field .bomx-fi { width:100%; }
.bomx-rm-static { font-size:13px; color:var(--bx-text); padding:7px 0; }
@media (max-width:640px) {
  .bomx-rm-card-body { grid-template-columns:1fr 1fr; }
}

/* ── Buttons / inputs ── */
.bomx-fi { border:1px solid #CDD5E0; border-radius:var(--bx-rsm); padding:7px 9px; font-size:13px; color:var(--bx-text); background:#fff; outline:none; }
.bomx-fi:focus { border-color:var(--bx-mfg); box-shadow:0 0 0 3px rgba(180,83,9,.1); }
.bomx-fi:disabled { background:#F8F9FC; color:var(--bx-muted); }
.bomx-fi-mono { font-family:"DM Mono",monospace; }
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

/* ── Modal ── */
.bomx-modal-overlay { position:fixed; inset:0; background:rgba(17,24,39,.5); display:flex; align-items:center; justify-content:center; z-index:1000; }
.bomx-modal { background:#fff; border-radius:12px; padding:22px; max-width:94vw; box-shadow:0 20px 50px rgba(0,0,0,.25); }
.bomx-modal-title { font-size:16px; font-weight:700; color:var(--bx-text); margin-bottom:14px; }
.bomx-modal-body { font-size:13.5px; color:var(--bx-text); line-height:1.5; }
.bomx-modal-actions { display:flex; justify-content:flex-end; gap:10px; margin-top:18px; }

.shimmer { background:linear-gradient(90deg,#f1f3f5 25%,#e9ecef 37%,#f1f3f5 63%); background-size:400% 100%; animation:shimmer 1.4s ease infinite; }
@keyframes shimmer { 0%{background-position:100% 50%} 100%{background-position:0 50%} }
</style>