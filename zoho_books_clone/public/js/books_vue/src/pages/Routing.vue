<template>
<div class="bomx-page">

  <!-- ══════════ SUMMARY STRIP ══════════ -->
  <div class="bomx-sum-strip">
    <div class="bomx-sum-card">
      <div class="bomx-sc-bar" style="background:var(--bx-mfg)"></div>
      <div class="bomx-sc-lbl">Total Routings</div>
      <div class="bomx-sc-val">{{ list.length }}</div>
      <div class="bomx-sc-sub">{{ activeCount }} active</div>
    </div>
    <div class="bomx-sum-card">
      <div class="bomx-sc-bar" style="background:var(--bx-blue)"></div>
      <div class="bomx-sc-lbl" style="color:var(--bx-blue)">Total Steps</div>
      <div class="bomx-sc-val" style="color:var(--bx-blue)">{{ totalStepsAll }}</div>
      <div class="bomx-sc-sub">Across all routings</div>
    </div>
    <div class="bomx-sum-card">
      <div class="bomx-sc-bar" style="background:var(--bx-green)"></div>
      <div class="bomx-sc-lbl" style="color:var(--bx-green)">Cycle Time</div>
      <div class="bomx-sc-val" style="color:var(--bx-green)">{{ totalTime }} <span style="font-size:12px;font-weight:600">min</span></div>
      <div class="bomx-sc-sub">This routing</div>
    </div>
    <div class="bomx-sum-card">
      <div class="bomx-sc-bar" style="background:var(--bx-amber)"></div>
      <div class="bomx-sc-lbl" style="color:var(--bx-amber)">Est. Labour Cost</div>
      <div class="bomx-sc-val" style="color:var(--bx-amber)">₹{{ formatMoney(totalCost) }}</div>
      <div class="bomx-sc-sub">This routing</div>
    </div>
  </div>

  <div class="bomx-two-col">

    <!-- ══════════ LEFT: ROUTING LIST ══════════ -->
    <div class="bomx-list-panel">
      <div class="bomx-panel-hdr">
        <span class="bomx-panel-title">🧭 Routings <span class="bomx-count">({{ sorted.length }})</span></span>
        <button class="bomx-btn-icon-round" :disabled="!$canCreate('inventory')" @click="openAdd" :title="!$canCreate('inventory') ? 'Read-only access' : 'New Routing'">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        </button>
      </div>
      <select class="bomx-fi bomx-status-filter" v-model="filterStatus">
        <option value="">All Status</option>
        <option value="active">Active</option>
        <option value="inactive">Inactive</option>
      </select>
      <input class="bomx-search" v-model="search" type="text" placeholder="Search routings…"/>
      <div class="bomx-list">
        <template v-if="loading">
          <div v-for="n in 5" :key="n" class="bomx-item"><div class="shimmer" style="height:38px;border-radius:6px"></div></div>
        </template>
        <div v-else-if="!sorted.length" class="bomx-list-empty">No Routings found</div>
        <div v-else v-for="row in sorted" :key="row.name"
             class="bomx-item" :class="{active: selectedName === row.name}"
             @click="selectRouting(row.name)">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px">
            <div class="bomx-item-name">{{ row.name }}</div>
            <span class="bomx-badge" :class="statusClass(row)">{{ statusLabel(row) }}</span>
          </div>
          <div class="bomx-item-meta">
            <span>⚙️ {{ row.op_count != null ? row.op_count : 0 }} operation{{ row.op_count === 1 ? '' : 's' }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ══════════ RIGHT: ROUTING DETAIL ══════════ -->
    <div class="bomx-detail-panel">

      <!-- Empty state -->
      <div v-if="!selectedName" class="bomx-empty-state">
        <div class="bomx-empty-icon">🧭</div>
        <div class="bomx-empty-title">Select a Routing</div>
        <div class="bomx-empty-sub">Choose a Routing from the list to view or edit its operation sequence.</div>
        <button class="bomx-btn bomx-btn-mfg" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''" @click="openAdd"><span v-html="icon('plus',13)"></span> Create Routing</button>
      </div>

      <template v-else>
        <div v-if="detailLoading" class="bomx-empty-state"><div class="shimmer" style="height:200px;border-radius:10px"></div></div>

        <template v-else>
          <!-- Header -->
          <div class="bomx-detail-hdr">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px">
              <div style="min-width:0">
                <div class="bomx-detail-title">{{ isNew ? 'New Routing' : (doc.routing_name || doc.name) }}</div>
                <div class="bomx-detail-meta">
                  <span class="mono" v-if="!isNew">{{ doc.name }}</span>
                  <span v-if="!isNew">•</span>
                  <span class="bomx-badge" :class="statusClass(doc)" style="font-size:11px">{{ statusLabel(doc) }}</span>
                </div>
              </div>
              <div style="display:flex;gap:6px;flex-shrink:0;flex-wrap:wrap;justify-content:flex-end">
                <button class="bomx-btn bomx-btn-ghost-inv" @click="goBackToList">Back</button>
                <button class="bomx-btn bomx-btn-light" @click="save" :disabled="saving || detailLoading || !(isNew ? $canCreate('inventory') : $canEdit('inventory'))">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13"/><polyline points="7 3 7 8 15 8"/></svg>
                  {{ saving ? 'Saving…' : (isNew ? 'Save Routing' : 'Save Changes') }}
                </button>
              </div>
            </div>
          </div>

          <!-- Stats bar -->
          <div class="bomx-stats-bar">
            <div class="bomx-sbar-cell">
              <div class="bomx-sbar-lbl">Steps</div>
              <div class="bomx-sbar-val" style="color:var(--bx-mfg)">{{ (doc.operations || []).length }}</div>
            </div>
            <div class="bomx-sbar-cell">
              <div class="bomx-sbar-lbl">Total Cycle Time</div>
              <div class="bomx-sbar-val" style="color:var(--bx-blue)">{{ totalTime }}<span style="font-size:11px;font-weight:600"> min</span></div>
            </div>
            <div class="bomx-sbar-cell">
              <div class="bomx-sbar-lbl">Est. Labour Cost</div>
              <div class="bomx-sbar-val" style="color:var(--bx-green)">₹{{ formatMoney(totalCost) }}</div>
            </div>
            <div class="bomx-sbar-cell">
              <div class="bomx-sbar-lbl">Avg Rate / Op</div>
              <div class="bomx-sbar-val" style="color:var(--bx-amber)">₹{{ formatMoney(avgRate) }}</div>
            </div>
          </div>

          <!-- Tabs -->
          <div class="bomx-seq-tabs">
            <button class="bomx-seq-tab" :class="{active: activeTab==='flow'}" @click="activeTab='flow'">📊 Flow Diagram</button>
            <button class="bomx-seq-tab" :class="{active: activeTab==='sequence'}" @click="activeTab='sequence'">📋 Sequence Editor</button>
            <button class="bomx-seq-tab" :class="{active: activeTab==='linked_boms'}" @click="activeTab='linked_boms'">📄 Linked BOMs</button>
          </div>

          <div class="bomx-body">

            <!-- Flow Diagram tab (read-only visual) -->
            <div v-if="activeTab==='flow'">
              <div v-if="!doc.operations || !doc.operations.length" class="bomx-tree-empty">No operations added yet. Switch to the Sequence Editor tab to add one.</div>
              <div v-else class="bomx-flow-wrap">
                <template v-for="(op, idx) in doc.operations" :key="op._uid">
                  <div class="bomx-flow-step">
                    <div class="bomx-flow-seq">{{ idx + 1 }}</div>
                    <div class="bomx-flow-box">
                      <div class="bomx-flow-icon">⚙️</div>
                      <div class="bomx-flow-name">{{ op.operation || '— Not set —' }}</div>
                      <div class="bomx-flow-time" v-if="op.time_in_mins">{{ op.time_in_mins }} min</div>
                    </div>
                    <div class="bomx-flow-wc" v-if="op.workstation">{{ op.workstation }}</div>
                  </div>
                  <div class="bomx-flow-arrow" v-if="idx < doc.operations.length - 1">→</div>
                </template>
              </div>
            </div>

            <!-- Sequence Editor tab (editable) -->
            <div v-if="activeTab==='sequence'">
              <div class="bomx-section-lbl" style="display:flex;align-items:center;gap:6px">
                Operations Sequence <span class="bomx-count" v-if="doc.operations && doc.operations.length">({{ doc.operations.length }})</span>
              </div>
              <div class="bomx-rm-cards">
                <div v-if="!doc.operations || !doc.operations.length" class="bomx-tree-empty">No operations added.</div>
                <div class="bomx-rm-card" v-for="(op, idx) in doc.operations" :key="op._uid">
                  <div class="bomx-rm-card-hdr">
                    <span class="bomx-rm-card-num">{{ idx + 1 }}</span>
                    <span class="bomx-rm-card-title" style="font-weight:700;color:var(--bx-mfgB);flex:none">Step {{ idx + 1 }}</span>
                    <div style="flex:1"></div>
                    <button class="bomx-btn-icon" @click="moveOp(idx, -1)" :disabled="idx===0" title="Move up">
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="18 15 12 9 6 15"/></svg>
                    </button>
                    <button class="bomx-btn-icon" @click="moveOp(idx, 1)" :disabled="idx===doc.operations.length-1" title="Move down">
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
                    </button>
                    <button class="bomx-btn-icon danger bomx-rm-card-rm" @click="removeOp(idx)" title="Remove">
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                  </div>
                  <div class="bomx-rm-card-body" style="grid-template-columns:1fr 1fr">
                    <div class="bomx-rm-field">
                      <label>Operation <span style="color:var(--bx-red)">*</span></label>
                      <select class="bomx-fi" v-model="op.operation" @change="onOpChange(op)">
                        <option value="">— Select —</option>
                        <option v-for="o in operationsList" :key="o.name" :value="o.name">{{ o.name }}</option>
                      </select>
                    </div>
                    <div class="bomx-rm-field">
                      <label>Workstation</label>
                      <select class="bomx-fi" v-model="op.workstation" @change="onWorkstationChange(op)">
                        <option value="">— Select —</option>
                        <option v-for="w in workstationsList" :key="w.name" :value="w.name">{{ w.name }}</option>
                      </select>
                    </div>
                    <div class="bomx-rm-field">
                      <label>Time (Min)</label>
                      <input class="bomx-fi bomx-fi-mono" type="number" v-model.number="op.time_in_mins" min="0" step="any" placeholder="0"/>
                    </div>
                    <div class="bomx-rm-field">
                      <label>Hour Rate</label>
                      <input class="bomx-fi bomx-fi-mono" type="number" v-model.number="op.hour_rate" min="0" step="any" placeholder="0"/>
                    </div>
                  </div>
                </div>
              </div>
              <div class="bomx-add-row" @click="addOp">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                Add Operation
              </div>
            </div>

            <!-- Linked BOMs tab (read-only) -->
            <div v-if="activeTab==='linked_boms'">
              <div v-if="linkedBomsLoading" class="bomx-tree-empty">Loading…</div>
              <template v-else>
                <div v-if="!linkedBoms.length" class="bomx-tree-empty">This routing is not used in any Bill of Materials yet.</div>
                <template v-else>
                  <div class="bomx-section-lbl" style="margin-bottom:10px">This routing is used in the following Bills of Materials:</div>
                  <div class="bomx-linked-bom-list">
                    <div class="bomx-linked-bom-row" v-for="b in linkedBoms" :key="b.name">
                      <span class="bomx-tree-icon">📄</span>
                      <div class="bomx-linked-bom-info">
                        <div class="bomx-linked-bom-title">
                          {{ b.name }}<span v-if="b.bom_version"> v{{ b.bom_version }}</span>
                          — {{ b.item_name || b.item }}
                        </div>
                      </div>
                      <button class="bomx-btn bomx-btn-ghost" @click="router.push(`/manufacturing/bom/${b.name}`)">Open BOM</button>
                    </div>
                  </div>
                </template>
              </template>
            </div>

            <!-- Header fields -->
            <div class="bomx-section-lbl" style="margin-top:22px">Routing Details</div>
            <div class="bomx-hdr-fields-inline">
              <div>
                <div class="bomx-hf-label">Routing Name <span style="color:var(--bx-red)">*</span></div>
                <input class="bomx-fi" type="text" v-model="doc.routing_name" :disabled="!isNew" placeholder="e.g., Standard Assembly Line" style="width:100%"/>
                <div class="bomx-field-hint" v-if="!isNew">Routing name cannot be changed after creation.</div>
              </div>
              <label class="bomx-toggle"><input type="checkbox" v-model="doc.is_active" :true-value="1" :false-value="0"/> Is Active</label>
            </div>

            <!-- Description -->
            <div class="bomx-section-lbl" style="margin-top:22px">Description</div>
            <textarea class="bomx-fi" v-model="doc.description" style="width:100%;min-height:110px;resize:vertical" placeholder="Describe this routing (optional)…"></textarea>
          </div>

          <!-- Footer -->
          <div class="bomx-footer">
            <button v-if="!isNew" class="bomx-btn bomx-btn-ghost-inv" style="color:var(--bx-red);border-color:rgba(201,42,42,.3)" :disabled="!$canDelete('inventory')" :title="!$canDelete('inventory') ? 'Not permitted' : ''" @click="deleteFromDetail">Delete Routing</button>
            <div style="flex:1"></div>
            <button class="bomx-btn bomx-btn-mfg" @click="save" :disabled="saving || detailLoading || !(isNew ? $canCreate('inventory') : $canEdit('inventory'))">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13"/><polyline points="7 3 7 8 15 8"/></svg>
              {{ saving ? 'Saving…' : (isNew ? 'Save Routing' : 'Save Changes') }}
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
import { useToast } from "../composables/useToast.js";
import { useConfirm } from "../composables/useConfirm.js";
import { apiGet, apiList, apiSave, apiDelete } from "../api/client.js";

const route = useRoute();
const router = useRouter();
const { toast } = useToast();
const { confirm } = useConfirm();

// ── LIST STATE ──────────────────────────────────────────────
const loading = ref(false);
const list = ref([]);
const search = ref("");
const filterStatus = ref("");

const selectedName = computed(() => (route.params.name && route.params.name !== "new") ? route.params.name : (route.params.name === "new" ? "new" : null));

async function loadList() {
  loading.value = true;
  try {
    const rows = await apiList("Routing", { fields: ["name", "is_active", "modified"], limit: 1000, order: "modified desc" });
    const opCounts = await apiList("Routing Operation", { fields: ["parent", "count(*) as op_count"], limit: 2000 }).catch(() => []);
    const countMap = {};
    (opCounts || []).forEach(r => { countMap[r.parent] = (countMap[r.parent] || 0) + 1; });
    list.value = (rows || []).map(r => ({ ...r, op_count: countMap[r.name] || 0 }));
  } catch (e) {
    toast("Could not load Routings", "error");
  }
  loading.value = false;
}

const sorted = computed(() => {
  let r = list.value;
  if (filterStatus.value === "active") r = r.filter(i => i.is_active);
  if (filterStatus.value === "inactive") r = r.filter(i => !i.is_active);
  const q = search.value.toLowerCase().trim();
  if (q) r = r.filter(i => (i.name || "").toLowerCase().includes(q));
  return r;
});

function statusLabel(row) {
  return row.is_active ? "Active" : "Inactive";
}
function statusClass(row) {
  return row.is_active ? "badge-active" : "badge-obsolete";
}

// ── SUMMARY STRIP (display-only, derived from existing list/doc data) ──
const activeCount = computed(() => list.value.filter(r => r.is_active).length);
const totalStepsAll = computed(() => list.value.reduce((s, r) => s + (r.op_count || 0), 0));
function formatMoney(n) {
  return Number(n || 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function selectRouting(name) {
  router.push(`/manufacturing/routing/${name}`);
}
function openAdd() {
  router.push("/manufacturing/routing/new");
}
function goBackToList() {
  router.push("/manufacturing/routing");
}

async function isRoutingDeletable(row) {
  try {
    const inBom = await apiList("BOM", { fields: ["name"], filters: [["routing", "=", row.name]], limit: 1 });
    if (inBom && inBom.length) {
      toast(`${row.name} is linked to BOM ${inBom[0].name} and cannot be deleted.`, "error");
      return false;
    }
  } catch (e) {
    toast(`Could not verify whether ${row.name} is in use — try again.`, "error");
    return false;
  }
  return true;
}

async function deleteFromDetail() {
  const row = { name: doc.value.name };
  if (!(await isRoutingDeletable(row))) return;
  if (await confirm({ title: "Delete Routing?", body: `Delete "${row.name}"?`, okLabel: "Delete", okStyle: "danger" })) {
    try {
      await apiDelete("Routing", row.name);
      toast("Routing deleted");
      goBackToList();
      loadList();
    } catch (e) {
      toast("Could not delete: " + e.message, "error");
    }
  }
}

// ── DETAIL STATE ─────────────────────────────────────────────
const isNew = computed(() => route.params.name === "new");
const detailLoading = ref(false);
const saving = ref(false);

function emptyDoc() {
  return {
    doctype: "Routing",
    routing_name: "",
    is_active: 1,
    description: "",
    operations: [],
  };
}
const doc = ref(emptyDoc());
const activeTab = ref("flow");

watch(() => route.params.name, () => { activeTab.value = "flow"; linkedBoms.value = []; });

// ── LINKED BOMS TAB ──────────────────────────────────────────
const linkedBoms = ref([]);
const linkedBomsLoading = ref(false);

async function loadLinkedBoms() {
  if (isNew.value || !doc.value.name) { linkedBoms.value = []; return; }
  linkedBomsLoading.value = true;
  try {
    const boms = await apiList("BOM", {
      fields: ["name", "item", "bom_version", "is_default", "docstatus"],
      filters: [["routing", "=", doc.value.name]],
      limit: 500,
      order: "modified desc",
    });
    const rows = boms || [];
    const itemCodes = [...new Set(rows.map(r => r.item).filter(Boolean))];
    if (itemCodes.length) {
      const items = await apiList("Item", { fields: ["name", "item_name"], filters: [["name", "in", itemCodes]], limit: itemCodes.length });
      const nameMap = {};
      (items || []).forEach(i => { nameMap[i.name] = i.item_name; });
      rows.forEach(r => { r.item_name = nameMap[r.item] || r.item; });
    }
    linkedBoms.value = rows;
  } catch (e) {
    toast("Could not load linked BOMs", "error");
  }
  linkedBomsLoading.value = false;
}

watch(activeTab, (val) => {
  if (val === "linked_boms" && !linkedBomsLoading.value) loadLinkedBoms();
});

const totalTime = computed(() => (doc.value.operations || []).reduce((s, o) => s + (Number(o.time_in_mins) || 0), 0));
const totalCost = computed(() => (doc.value.operations || []).reduce((s, o) => s + ((Number(o.hour_rate) || 0) * (Number(o.time_in_mins) || 0) / 60), 0));
const avgRate = computed(() => {
  const ops = doc.value.operations || [];
  if (!ops.length) return 0;
  return ops.reduce((s, o) => s + (Number(o.hour_rate) || 0), 0) / ops.length;
});

const operationsList = ref([]);
const workstationsList = ref([]);

let _uidCounter = 0;
function nextUid() { return ++_uidCounter; }
function ensureUids(rows) {
  (rows || []).forEach(r => { if (!r._uid) r._uid = nextUid(); });
  return rows;
}

onMounted(async () => {
  loading.value = true;
  try {
    const [ops, wks] = await Promise.all([
      apiList("Operation", { fields: ["name"], filters: [["is_active", "=", 1]], limit: 1000, order: "name asc" }),
      apiList("Workstation", { fields: ["name", "hour_rate"], filters: [["is_active", "=", 1]], limit: 1000, order: "name asc" }),
    ]);
    operationsList.value = ops || [];
    workstationsList.value = wks || [];
  } catch (e) {
    toast("Could not load Operations / Workstations", "error");
  }
  await loadList();
  if (route.params.name) await loadDoc();
  loading.value = false;
});

watch(() => route.params.name, async (name) => {
  if (!name) { doc.value = emptyDoc(); return; }
  await loadDoc();
});

async function loadDoc() {
  if (isNew.value) {
    doc.value = emptyDoc();
    return;
  }
  detailLoading.value = true;
  try {
    const r = await apiGet("Routing", route.params.name);
    if (!r.operations) r.operations = [];
    ensureUids(r.operations);
    doc.value = r;
    // Keep already-saved-but-now-inactive Operations/Workstations selectable, so
    // the saved values don't silently vanish from the dropdowns.
    r.operations.forEach(op => {
      if (op.workstation && !workstationsList.value.some(w => w.name === op.workstation)) {
        workstationsList.value = [{ name: op.workstation, hour_rate: 0 }, ...workstationsList.value];
      }
      if (op.operation && !operationsList.value.some(o => o.name === op.operation)) {
        operationsList.value = [{ name: op.operation }, ...operationsList.value];
      }
    });
  } catch (e) {
    toast("Could not load Routing", "error");
    goBackToList();
  }
  detailLoading.value = false;
}

function addOp() {
  if (!doc.value.operations) doc.value.operations = [];
  doc.value.operations.push({ _uid: nextUid(), operation: "", workstation: "", time_in_mins: 0, hour_rate: 0 });
}
function removeOp(idx) {
  doc.value.operations.splice(idx, 1);
}
function moveOp(idx, dir) {
  const arr = doc.value.operations;
  const target = idx + dir;
  if (target < 0 || target >= arr.length) return;
  [arr[idx], arr[target]] = [arr[target], arr[idx]];
}

function onOpChange(op) {
  // Auto-fill workstation from Operation.default_workstation if workstation is blank
  if (op.operation && !op.workstation) {
    const found = operationsList.value.find(o => o.name === op.operation);
    if (found && found.default_workstation) {
      op.workstation = found.default_workstation;
      onWorkstationChange(op);
    }
  }
}

function onWorkstationChange(op) {
  if (!op.workstation) return;
  const w = workstationsList.value.find(x => x.name === op.workstation);
  if (w && w.hour_rate) op.hour_rate = w.hour_rate;
}

async function save() {
  if (!doc.value.routing_name || !doc.value.routing_name.trim()) {
    toast("Routing Name is mandatory", "error");
    return;
  }
  if (!doc.value.operations || doc.value.operations.length === 0) {
    toast("Add at least one Operation row", "error");
    return;
  }
  for (const op of doc.value.operations) {
    if (!op.operation) {
      toast("Each row must have an Operation selected", "error");
      return;
    }
  }

  saving.value = true;
  try {
    // Strip the client-only _uid before sending to the server.
    const payload = {
      ...doc.value,
      operations: (doc.value.operations || []).map(({ _uid, ...rest }) => rest),
    };
    const r = await apiSave(payload);
    toast(isNew.value ? "Routing created successfully" : "Saved successfully");
    if (!r.operations) r.operations = [];
    ensureUids(r.operations);
    if (isNew.value) {
      router.replace(`/manufacturing/routing/${r.name}`);
    } else {
      doc.value = r;
    }
    loadList();
  } catch (e) {
    toast(e.message || "Could not save", "error");
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

/* ── Summary strip ── */
.bomx-sum-strip { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:16px; }
.bomx-sum-card { background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); padding:13px 16px; position:relative; overflow:hidden; }
.bomx-sc-bar { position:absolute; top:0; left:0; width:3px; height:100%; }
.bomx-sc-lbl { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); margin-bottom:3px; }
.bomx-sc-val { font-size:21px; font-weight:700; font-family:var(--bx-mono, monospace); }
.bomx-sc-sub { font-size:11px; color:var(--bx-muted); margin-top:2px; }
@media (max-width:1000px) { .bomx-sum-strip { grid-template-columns:repeat(2,1fr); } }

.bomx-btn-icon-round { width:26px; height:26px; border-radius:50%; background:var(--bx-mfg); color:#fff; border:none; cursor:pointer; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0; }
.bomx-btn-icon-round:hover { background:var(--bx-mfgB); }

/* ── Detail stats bar ── */
.bomx-stats-bar { display:grid; grid-template-columns:repeat(4,1fr); border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); }
.bomx-sbar-cell { padding:12px 16px; border-right:1px solid var(--bx-border); display:flex; flex-direction:column; gap:2px; }
.bomx-sbar-cell:last-child { border-right:none; }
.bomx-sbar-lbl { font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); }
.bomx-sbar-val { font-size:17px; font-weight:700; font-family:var(--bx-mono, monospace); }
@media (max-width:640px) { .bomx-stats-bar { grid-template-columns:repeat(2,1fr); } }

/* ── Tabs ── */
.bomx-seq-tabs { display:flex; border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); padding:0 18px; }
.bomx-seq-tab { padding:9px 14px; font-size:13px; font-weight:600; cursor:pointer; border:none; background:none; color:var(--bx-muted); border-bottom:2px solid transparent; margin-bottom:-1px; transition:all .15s; }
.bomx-seq-tab.active { color:var(--bx-mfg); border-bottom-color:var(--bx-mfg); }
.bomx-seq-tab:hover:not(.active) { color:var(--bx-text); }

/* ── Flow diagram ── */
.bomx-flow-wrap { display:flex; align-items:flex-start; gap:0; overflow-x:auto; padding:16px 4px; flex-wrap:nowrap; }
.bomx-flow-step { display:flex; flex-direction:column; align-items:center; gap:6px; flex-shrink:0; min-width:110px; max-width:130px; }
.bomx-flow-seq { font-size:10px; font-weight:700; width:20px; height:20px; border-radius:50%; display:flex; align-items:center; justify-content:center; background:var(--bx-mfgS); color:var(--bx-mfgB); }
.bomx-flow-box { width:100px; min-height:64px; border-radius:8px; border:2px solid var(--bx-mfg); background:var(--bx-mfgS); display:flex; flex-direction:column; align-items:center; justify-content:center; gap:3px; text-align:center; padding:8px; transition:transform .15s, box-shadow .15s; }
.bomx-flow-box:hover { transform:translateY(-2px); box-shadow:0 4px 12px rgba(0,0,0,.1); }
.bomx-flow-icon { font-size:16px; }
.bomx-flow-name { font-size:11px; font-weight:700; line-height:1.25; color:var(--bx-mfgB); word-break:break-word; }
.bomx-flow-time { font-size:10px; color:var(--bx-muted); }
.bomx-flow-wc { font-size:10.5px; color:var(--bx-muted); text-align:center; }
.bomx-flow-arrow { color:#CDD5E0; font-size:20px; flex-shrink:0; margin:0 2px; align-self:center; margin-top:22px; }

.bomx-rm-card-num { width:22px; height:22px; border-radius:50%; background:var(--bx-mfgS); color:var(--bx-mfg); display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:700; flex-shrink:0; }
.bomx-hdr-fields-inline { display:flex; align-items:flex-end; gap:20px; flex-wrap:wrap; }
.bomx-hdr-fields-inline > div:first-child { flex:1; min-width:220px; }
.bomx-fi-mono { font-family:var(--bx-mono, monospace); }


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
.bomx-toggle-row { display:flex; gap:20px; padding:10px 22px 14px; flex-wrap:wrap; background:var(--bx-surf2); border-bottom:1px solid var(--bx-border); }
.bomx-toggle { display:flex; align-items:center; gap:6px; font-size:12.5px; font-weight:600; color:var(--bx-text); }

.bomx-body { padding:20px 22px; overflow-y:auto; flex:1; }
.bomx-section-lbl { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--bx-muted); margin-bottom:8px; }
.bomx-tree-empty { text-align:center; padding:20px; color:var(--bx-muted); font-size:13px; }
.bomx-tree-icon { font-size:14px; flex-shrink:0; }

/* ── Linked BOMs tab ── */
.bomx-linked-bom-list { display:flex; flex-direction:column; gap:8px; }
.bomx-linked-bom-row { display:flex; align-items:center; gap:10px; padding:12px 16px; background:var(--bx-surf2); border:1px solid var(--bx-border); border-radius:var(--bx-radius); }
.bomx-linked-bom-info { flex:1; min-width:0; }
.bomx-linked-bom-title { font-size:13.5px; font-weight:700; color:var(--bx-text); }
.bomx-btn-ghost { background:var(--bx-surface); color:#495057; border:1px solid #CDD5E0; }
.bomx-btn-ghost:hover:not(:disabled) { background:var(--bx-surf2); border-color:var(--bx-mfg); color:var(--bx-mfg); }
.bomx-add-row { display:flex; align-items:center; gap:8px; padding:8px 12px; color:var(--bx-mfg); cursor:pointer; font-size:13px; font-weight:600; border-radius:var(--bx-rsm); margin-top:4px; }
.bomx-add-row:hover { background:var(--bx-mfgS); }

/* ── Operation sequence cards ── */
.bomx-rm-cards { display:flex; flex-direction:column; gap:10px; }
.bomx-rm-card { background:#fff; border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; box-shadow:0 1px 3px rgba(16,24,40,.04); }
.bomx-rm-card-hdr { display:flex; align-items:center; gap:10px; padding:10px 14px; background:var(--bx-mfgS); border-bottom:1px solid var(--bx-border); }
.bomx-rm-card-title { flex:1; min-width:0; font-weight:600; }
.bomx-rm-card-rm { flex-shrink:0; }
.bomx-rm-card-body { display:grid; grid-template-columns:1fr 1fr; gap:10px; padding:12px 14px; }
.bomx-rm-field { display:flex; flex-direction:column; gap:4px; min-width:0; }
.bomx-rm-field label { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); }
.bomx-rm-field .bomx-fi { width:100%; }
@media (max-width:640px) {
  .bomx-rm-card-body { grid-template-columns:1fr; }
}

.bomx-footer { padding:12px 22px; border-top:1px solid var(--bx-border); background:var(--bx-surf2); display:flex; justify-content:space-between; align-items:center; gap:8px; }

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
.bomx-btn-icon:disabled { opacity:.35; cursor:not-allowed; }
.bomx-btn-icon:disabled:hover { border-color:var(--bx-border); color:var(--bx-muted); background:none; }
.bomx-btn-icon.danger { color:var(--bx-red); }
.bomx-btn-icon.danger:hover { background:var(--bx-redS); border-color:var(--bx-red); }

.shimmer { background:linear-gradient(90deg,#f1f3f5 25%,#e9ecef 37%,#f1f3f5 63%); background-size:400% 100%; animation:shimmer 1.4s ease infinite; }
@keyframes shimmer { 0%{background-position:100% 50%} 100%{background-position:0 50%} }
</style>