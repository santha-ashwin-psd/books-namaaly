<template>
<div class="bomx-page">

  <!-- ══════════ FULL-WIDTH LIST VIEW (always mounted; drawer overlays on top) ══════════ -->
  <div class="bomx-list-view">
    <div class="bomx-list-toolbar">
      <span class="bomx-panel-title">🗂️ All Job Cards <span class="bomx-count">({{ sorted.length }})</span></span>
      <button class="bomx-btn bomx-btn-mfg" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''" @click="openAdd"><span v-html="icon('plus',13)"></span> New Job Card</button>
    </div>

    <div class="bomx-pp-sumstrip">
      <div class="bomx-pp-sc">
        <div class="bomx-pp-sc-bar" style="background:var(--bx-mfg)"></div>
        <div class="bomx-pp-sc-val">{{ countTotal }}</div>
        <div class="bomx-pp-sc-lbl">Total</div>
      </div>
      <div class="bomx-pp-sc">
        <div class="bomx-pp-sc-bar" style="background:var(--bx-amber)"></div>
        <div class="bomx-pp-sc-val" style="color:var(--bx-amber)">{{ countOpen }}</div>
        <div class="bomx-pp-sc-lbl">Open</div>
      </div>
      <div class="bomx-pp-sc">
        <div class="bomx-pp-sc-bar" style="background:var(--bx-blue)"></div>
        <div class="bomx-pp-sc-val" style="color:var(--bx-blue)">{{ countWIP }}</div>
        <div class="bomx-pp-sc-lbl">In Progress</div>
      </div>
      <div class="bomx-pp-sc">
        <div class="bomx-pp-sc-bar" style="background:var(--bx-green)"></div>
        <div class="bomx-pp-sc-val" style="color:var(--bx-green)">{{ countCompleted }}</div>
        <div class="bomx-pp-sc-lbl">Completed</div>
      </div>
    </div>

    <div class="bomx-list-filters">
      <select class="bomx-fi bomx-status-filter" v-model="filterStatus">
        <option value="">All Status</option>
        <option value="Open">Open</option>
        <option value="Work In Progress">Work In Progress</option>
        <option value="Completed">Completed</option>
        <option value="Cancelled">Cancelled</option>
      </select>
      <input class="bomx-fi bomx-search-full" v-model="search" type="text" placeholder="Search Job Card, Work Order, Operation…"/>
    </div>

    <div class="bomx-jc-grid">
      <template v-if="loading">
        <div v-for="n in 6" :key="n" class="bomx-jc"><div class="shimmer" style="height:150px;border-radius:10px"></div></div>
      </template>
      <div v-else-if="!sorted.length" class="bomx-list-empty">No Job Cards found</div>
      <div v-else v-for="row in sorted" :key="row.name" class="bomx-jc" :class="'jc-status-' + statusSlug(row.status)" @click="selectJobCard(row.name)">
        <div class="bomx-jc-hdr">
          <div class="bomx-jc-icon" :class="'jc-icon-' + statusSlug(row.status)"><span v-html="icon('card',17)"></span></div>
          <div style="flex:1;min-width:0">
            <div class="bomx-jc-id mono">{{ row.name }}</div>
            <div class="bomx-jc-op">{{ row.operation || '—' }}</div>
            <div class="bomx-jc-wo">{{ row.work_order }}<span v-if="row.workstation"> • {{ row.workstation }}</span></div>
            <div class="bomx-jc-sub" v-if="row.sub_assembly_bom">🧩 {{ subAssemblyBomLabel(row.sub_assembly_bom) }}</div>
          </div>
          <span class="bomx-badge" :class="statusClass(row)" style="flex-shrink:0">{{ statusLabel(row) }}</span>
        </div>
        <div class="bomx-jc-body">
          <div class="bomx-jc-stat">
            <div class="bomx-jc-stat-lbl">Operator</div>
            <div class="bomx-jc-stat-val">{{ row.employee || 'Unassigned' }}</div>
          </div>
          <div class="bomx-jc-stat">
            <div class="bomx-jc-stat-lbl">For Quantity</div>
            <div class="bomx-jc-stat-val mono">{{ row.for_quantity || '—' }}</div>
          </div>
          <div class="bomx-jc-stat" style="grid-column:1/-1">
            <div class="bomx-jc-stat-lbl">Total Time</div>
            <div class="bomx-jc-stat-val mono">{{ row.total_time_in_mins ? fmtMins(row.total_time_in_mins) : '—' }}</div>
          </div>
          <div class="bomx-jc-stat" style="grid-column:1/-1" v-if="jcItemName(row)">
            <div class="bomx-jc-stat-lbl">Item</div>
            <div class="bomx-jc-stat-val bomx-jc-stat-val-wrap">{{ jcItemName(row) }}</div>
          </div>
        </div>
        <div class="bomx-jc-foot">
          <span class="mono">{{ fmtDate(row.modified) }}</span>
          <button class="bomx-btn bomx-btn-sm bomx-btn-light" style="color:var(--bx-mfgB);border:1px solid var(--bx-mfg)" @click.stop="selectJobCard(row.name)">
            Open <span v-html="icon('open',11)"></span>
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- ══════════ DRAWER: Job Card Detail (overlays the list, doesn't replace it) ══════════ -->
  <Transition name="jc-drawer-fade">
    <div v-if="selectedName" class="jc-drawer-bg" @click="handleBgClick">
      <div class="jc-drawer-panel" @click.stop>

        <div v-if="detailLoading" class="jc-drawer-hdr">
          <div class="shimmer" style="height:34px;border-radius:6px;width:70%"></div>
        </div>
        <div v-else class="jc-drawer-hdr">
          <div style="min-width:0">
            <div class="jc-drawer-title">{{ isNew ? 'New Job Card' : (jobCardItemName || doc.name) }}</div>
            <div class="jc-drawer-sub">{{ drawerSubtitle }}</div>
          </div>
          <div style="display:flex;gap:8px;align-items:center;flex-shrink:0">
            <span class="bomx-badge jc-drawer-badge" :class="statusClass(doc)">{{ statusLabel(doc) }}</span>
            <button class="jc-drawer-close" @click="goBackToList" title="Close">✕</button>
          </div>
        </div>

        <div v-if="detailLoading" class="jc-drawer-body">
          <div class="shimmer" style="height:180px;border-radius:10px"></div>
        </div>

        <template v-else>
          <div class="jc-drawer-body">

            <!-- Header fields -->
            <div class="bomx-hdr-fields" style="border:1px solid var(--bx-border);border-radius:var(--bx-radius);margin-bottom:16px">
              <div>
                <div class="bomx-hf-label">Work Order <span style="color:var(--bx-red)">*</span></div>
                <select class="bomx-fi" v-model="doc.work_order" :disabled="!isNew" style="width:100%" :title="doc.work_order">
                  <option value="">— Select Work Order —</option>
                  <option v-for="w in workOrdersList" :key="w.name" :value="w.name">{{ w.name }}</option>
                </select>
                <div class="bomx-field-hint" v-if="jobCardItemName">Manufactures: <strong>{{ jobCardItemName }}</strong></div>
                <div class="bomx-field-hint" v-if="doc.sub_assembly_bom">🧩 Sub-assembly: <strong>{{ subAssemblyBomLabel(doc.sub_assembly_bom) }}</strong></div>
              </div>
              <div>
                <div class="bomx-hf-label">Operation <span style="color:var(--bx-red)">*</span></div>
                <select v-if="groupedJcOperationRows.length" class="bomx-fi" v-model="selectedWoOpRow" style="width:100%">
                  <option value="">— Select Operation —</option>
                  <optgroup v-for="grp in groupedJcOperationRows" :key="grp.key" :label="grp.label">
                    <option v-for="row in grp.rows" :key="row.name" :value="row.name">
                      {{ row.operation }}{{ jcExistsForWoOpRow(row.name) ? ' (already has a Job Card)' : '' }}
                    </option>
                  </optgroup>
                </select>
                <select v-else class="bomx-fi" v-model="doc.operation" style="width:100%" :title="doc.operation">
                  <option value="">— Select Operation —</option>
                  <option v-for="o in operationsList" :key="o.name" :value="o.name">{{ o.name }}</option>
                </select>
                <div class="bomx-field-hint" v-if="groupedJcOperationRows.length">Pick the specific sub-assembly (or Final Assembly) step this card is for.</div>
              </div>
              <div>
                <div class="bomx-hf-label">Workstation</div>
                <select class="bomx-fi" v-model="doc.workstation" style="width:100%" :title="doc.workstation">
                  <option value="">— Select —</option>
                  <option v-for="w in workstationsList" :key="w.name" :value="w.name">{{ w.name }}</option>
                </select>
              </div>
            </div>
            <div class="jc-drawer-toggle-row">
              <div style="min-width:150px">
                <div class="bomx-hf-label">Status</div>
                <select class="bomx-fi" v-model="doc.status" style="width:100%">
                  <option>Open</option>
                  <option>Work In Progress</option>
                  <option>Completed</option>
                  <option>Cancelled</option>
                </select>
              </div>
              <div style="min-width:120px">
                <div class="bomx-hf-label">For Quantity</div>
                <input class="bomx-fi bomx-fi-mono" type="number" v-model.number="doc.for_quantity" min="0" step="any" style="width:100%"/>
              </div>
              <div style="flex:1;min-width:150px">
                <div class="bomx-hf-label">Employee</div>
                <input class="bomx-fi" type="text" v-model="doc.employee" placeholder="Operator name" style="width:100%"/>
              </div>
            </div>

            <!-- Schedule -->
            <div class="bomx-section-lbl">Schedule</div>
            <div class="bomx-hdr-fields" style="padding:0;border:none;background:none;margin-bottom:8px">
              <div>
                <div class="bomx-hf-label">Planned Start</div>
                <input class="bomx-fi" type="datetime-local" v-model="doc.planned_start_time" style="width:100%"/>
              </div>
              <div>
                <div class="bomx-hf-label">Planned End</div>
                <input class="bomx-fi" type="datetime-local" v-model="doc.planned_end_time" style="width:100%"/>
              </div>
            </div>
            <div class="bomx-hdr-fields" style="padding:0;border:none;background:none;margin-bottom:20px">
              <div>
                <div class="bomx-hf-label">Actual Start</div>
                <input class="bomx-fi" type="datetime-local" v-model="doc.actual_start_time" style="width:100%"/>
              </div>
              <div>
                <div class="bomx-hf-label">Actual End</div>
                <input class="bomx-fi" type="datetime-local" v-model="doc.actual_end_time" style="width:100%"/>
              </div>
            </div>

            <!-- Time Logs -->
            <div class="bomx-section-lbl" style="display:flex;align-items:center;justify-content:space-between">
              <span>Time Logs</span>
              <span v-if="doc.total_time_in_mins" style="text-transform:none;font-weight:600;color:var(--bx-mfgB)">Total: {{ fmtMins(doc.total_time_in_mins) }}</span>
            </div>
            <div class="bomx-rm-cards" style="margin-bottom:8px">
              <div v-if="!doc.time_logs || !doc.time_logs.length" class="bomx-tree-empty">No time logs yet.</div>
              <div v-for="(tl, idx) in doc.time_logs" :key="tl._uid" class="bomx-rm-card">
                <div class="bomx-rm-card-hdr">
                  <div class="bomx-rm-card-title">
                    Log #{{ idx + 1 }}
                    <span v-if="tl.from_time && !tl.to_time" class="bomx-badge badge-wip" style="margin-left:6px;font-size:10px">Running</span>
                  </div>
                  <button v-if="!tl.from_time || tl.to_time" class="bomx-btn bomx-btn-sm" style="background:var(--bx-greenS);color:var(--bx-green)" @click="startTimeLog(tl)">▶ Start</button>
                  <button v-else class="bomx-btn bomx-btn-sm" style="background:var(--bx-redS);color:var(--bx-red)" @click="stopTimeLog(tl)">■ Stop</button>
                  <div class="bomx-rm-card-amt" v-if="tl.time_in_mins">
                    <span class="bomx-rm-card-amt-lbl">Duration</span>
                    <span class="mono" style="font-size:13px;font-weight:700;color:var(--bx-mfgB)">{{ fmtMins(tl.time_in_mins) }}</span>
                  </div>
                  <button class="bomx-btn-icon danger" @click="removeTimeLog(idx)" title="Remove">
                    <span v-html="icon('trash',13)"></span>
                  </button>
                </div>
                <div class="bomx-rm-card-body" style="grid-template-columns:1fr 1fr">
                  <div class="bomx-rm-field">
                    <label>From</label>
                    <input class="bomx-fi" type="datetime-local" v-model="tl.from_time" @change="calcTimeDiff(tl)"/>
                  </div>
                  <div class="bomx-rm-field">
                    <label>To</label>
                    <input class="bomx-fi" type="datetime-local" v-model="tl.to_time" @change="calcTimeDiff(tl)"/>
                  </div>
                  <div class="bomx-rm-field">
                    <label>Time (Min)</label>
                    <input class="bomx-fi bomx-fi-mono" type="number" v-model.number="tl.time_in_mins" readonly/>
                  </div>
                  <div class="bomx-rm-field">
                    <label>Employee</label>
                    <input class="bomx-fi" type="text" v-model="tl.employee" placeholder="Name"/>
                  </div>
                </div>
                <div v-if="tl._invalidRange" class="bomx-field-hint" style="color:var(--bx-red);font-weight:600;padding:0 14px 10px">
                  ⚠ To Time is before From Time — fix this row before saving.
                </div>
              </div>
            </div>
            <div class="bomx-add-row" @click="addTimeLog">
              <span v-html="icon('plus',13)"></span> Add Time Log
            </div>

            <!-- Remarks -->
            <div class="bomx-section-lbl" style="margin-top:20px">Remarks</div>
            <textarea class="bomx-fi" v-model="doc.remarks" style="width:100%;min-height:90px;resize:vertical" placeholder="Optional notes…"></textarea>
          </div>

          <!-- Footer -->
          <div class="jc-drawer-footer">
            <button v-if="!isNew" class="bomx-btn bomx-btn-ghost-inv" style="color:var(--bx-red);border-color:rgba(201,42,42,.3);background:#fff" :disabled="!$canDelete('inventory')" @click="deleteFromDetail">Delete</button>
            <div style="flex:1"></div>
            <button class="bomx-btn bomx-btn-light" style="border:1px solid var(--bx-border);color:var(--bx-text)" @click="goBackToList" :disabled="saving">Close</button>
            <button class="bomx-btn bomx-btn-mfg" @click="save" :disabled="saving || detailLoading || !(isNew ? $canCreate('inventory') : $canEdit('inventory'))">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13"/><polyline points="7 3 7 8 15 8"/></svg>
              {{ saving ? 'Saving…' : (isNew ? 'Save Job Card' : 'Save Changes') }}
            </button>
          </div>
        </template>
      </div>
    </div>
  </Transition>

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
const filterStatus = ref(typeof route.query.status === "string" ? route.query.status : "");

const selectedName = computed(() => (route.params.name && route.params.name !== "new") ? route.params.name : (route.params.name === "new" ? "new" : null));

async function loadList() {
  loading.value = true;
  try {
    const fields = ["name", "work_order", "operation", "workstation", "status", "employee", "for_quantity", "total_time_in_mins", "modified", "sub_assembly_bom", "sub_assembly_item"];
    const r = await apiList("Job Card", { fields, limit: 2000, order: "modified desc" });
    list.value = r || [];
    await loadWorkOrderItemNames(list.value.map(i => i.work_order));
    await loadSubAssemblyBomNames(list.value.map(i => i.sub_assembly_bom));
    await loadItemNames(list.value.map(i => i.sub_assembly_item));
  } catch (e) {
    toast("Could not load Job Cards", "error");
  }
  loading.value = false;
}

// ── Work Order → Production Item lookup (Job Card itself has no item field;
// the item being manufactured belongs to its Work Order) ────────────────────
const workOrderItemMap = ref({});
function itemNameFor(woName) {
  const w = workOrderItemMap.value[woName];
  if (!w) return "";
  return w.item_name || w.production_item || "";
}
async function loadWorkOrderItemNames(names) {
  const unique = [...new Set((names || []).filter(Boolean))].filter(n => !workOrderItemMap.value[n]);
  if (!unique.length) return;
  try {
    const rows = await apiList("Work Order", { fields: ["name", "production_item", "item_name"], filters: [["name", "in", unique]], limit: unique.length });
    (rows || []).forEach(r => { workOrderItemMap.value[r.name] = r; });
  } catch (e) {
    // Non-critical — cards just fall back to showing the Work Order id.
  }
}

// ── Generic Item code → Item Name cache, shared by the Sub-Assembly BOM
// label lookup below and by Job Cards' own sub_assembly_item field ─────────
const itemNameMap = ref({});
async function loadItemNames(codes) {
  const unique = [...new Set((codes || []).filter(Boolean))].filter(c => !itemNameMap.value[c]);
  if (!unique.length) return;
  try {
    const rows = await apiList("Item", { fields: ["name", "item_name"], filters: [["name", "in", unique]], limit: unique.length });
    (rows || []).forEach(r => { itemNameMap.value[r.name] = r.item_name || r.name; });
  } catch (e) {
    // Non-critical — falls back to showing the raw item code.
  }
}

// ── Sub-Assembly BOM → Production Item lookup, so the badge can read
// "BOM-code — Item Name" the same way the Work Order's Components/
// Operations tabs label their sub-assembly groups. BOM itself has no
// item_name field -- only `item` (a Link) -- so the name comes from the
// Item cache above. ─────────────────────────────────────────────────────
const subAssemblyBomNameMap = ref({});
function subAssemblyBomLabel(bomName) {
  if (!bomName) return "";
  const b = subAssemblyBomNameMap.value[bomName];
  const name = b && itemNameMap.value[b.item];
  return name ? `${bomName} — ${name}` : bomName;
}
async function loadSubAssemblyBomNames(names) {
  const unique = [...new Set((names || []).filter(Boolean))].filter(n => !subAssemblyBomNameMap.value[n]);
  if (!unique.length) return;
  try {
    const rows = await apiList("BOM", { fields: ["name", "item"], filters: [["name", "in", unique]], limit: unique.length });
    (rows || []).forEach(r => { subAssemblyBomNameMap.value[r.name] = r; });
    await loadItemNames(rows.map(r => r.item));
  } catch (e) {
    // Non-critical — badge just falls back to showing the raw BOM code.
  }
}

// A card tied to a sub-assembly should show what THAT sub-assembly
// produces, not the Work Order's (unrelated) finished item -- e.g. a card
// for "BOM-2026-00004" should show its own item, not the final product the
// whole Work Order eventually makes.
function jcItemName(row) {
  if (row.sub_assembly_item) return itemNameMap.value[row.sub_assembly_item] || row.sub_assembly_item;
  return itemNameFor(row.work_order);
}

const sorted = computed(() => {
  let r = list.value;
  if (filterStatus.value) r = r.filter(i => i.status === filterStatus.value);
  const q = search.value.toLowerCase().trim();
  if (q) r = r.filter(i => [i.name, i.work_order, i.operation, i.workstation].filter(Boolean).join(" ").toLowerCase().includes(q));
  return r;
});

const countTotal = computed(() => list.value.length);
const countOpen = computed(() => list.value.filter(i => (i.status || "Open") === "Open").length);
const countWIP = computed(() => list.value.filter(i => i.status === "Work In Progress").length);
const countCompleted = computed(() => list.value.filter(i => i.status === "Completed").length);

function statusSlug(status) {
  return (status || "Open").toLowerCase().replace(/\s+/g, "-");
}

function statusLabel(row) { return row.status || "Open"; }
function statusClass(row) {
  const s = row.status;
  if (s === "Completed")        return "badge-active";
  if (s === "Cancelled")        return "badge-obsolete";
  if (s === "Work In Progress") return "badge-wip";
  return "badge-open";
}

function selectJobCard(name) {
  router.push(`/manufacturing/job-card/${name}`);
}
function openAdd() {
  router.push("/manufacturing/job-card/new");
}
function goBackToList() {
  router.push("/manufacturing/job-card");
}
function handleBgClick() {
  if (!saving.value) goBackToList();
}

async function deleteFromDetail() {
  const name = doc.value.name;
  if (await confirm({ title: "Delete Job Card?", body: `Are you sure you want to delete ${name}?`, okLabel: "Delete", okStyle: "danger" })) {
    try {
      await apiDelete("Job Card", name);
      toast("Job Card deleted");
      goBackToList();
      loadList();
    } catch (e) {
      toast("Could not delete Job Card: " + e.message, "error");
    }
  }
}

// ── DETAIL STATE ─────────────────────────────────────────────
const isNew = computed(() => route.params.name === "new");
const detailLoading = ref(false);
const saving = ref(false);

function emptyDoc() {
  return {
    doctype: "Job Card",
    work_order: "",
    operation: "",
    wo_operation_name: "",
    sub_assembly_bom: "",
    sub_assembly_item: "",
    workstation: "",
    status: "Open",
    for_quantity: 1,
    employee: "",
    planned_start_time: "",
    planned_end_time: "",
    actual_start_time: "",
    actual_end_time: "",
    time_logs: [],
    total_time_in_mins: 0,
    remarks: "",
  };
}
const doc = ref(emptyDoc());
const jobCardItemName = computed(() => {
  if (doc.value.sub_assembly_item) return itemNameMap.value[doc.value.sub_assembly_item] || doc.value.sub_assembly_item;
  return itemNameFor(doc.value.work_order);
});
const drawerSubtitle = computed(() => {
  const parts = [];
  if (!isNew.value) parts.push(doc.value.name);
  if (doc.value.work_order) parts.push(doc.value.work_order);
  if (doc.value.operation) parts.push(doc.value.operation);
  if (doc.value.workstation) parts.push(doc.value.workstation);
  if (doc.value.sub_assembly_bom) parts.push(`🧩 ${subAssemblyBomLabel(doc.value.sub_assembly_bom)}`);
  return parts.join(" · ");
});
watch(() => doc.value.sub_assembly_bom, (b) => { if (b) loadSubAssemblyBomNames([b]); });

const workOrdersList = ref([]);
const operationsList = ref([]);
const workstationsList = ref([]);

// ── Work Order's own Operation rows (with sub-assembly tags), so a Job
// Card can be tied to a *specific* row -- e.g. "Cutting" under sub-assembly
// BOM-2026-00004 vs the same "Cutting" operation name under BOM-2026-00008
// -- rather than just the generic Operation master, which has no notion of
// which sub-assembly's process it's for. ─────────────────────────────────
const workOrderOperations = ref([]);
async function loadWorkOrderOperations(woName) {
  workOrderOperations.value = [];
  if (!woName) return;
  try {
    const r = await apiGet("Work Order", woName);
    workOrderOperations.value = r.operations || [];
    const subs = workOrderOperations.value.map(o => o.sub_assembly_bom).filter(Boolean);
    if (subs.length) await loadSubAssemblyBomNames(subs);
  } catch (e) {
    // Non-critical -- falls back to the plain Operation dropdown below.
  }
}
watch(() => doc.value.work_order, (wo) => {
  if (wo) { loadWorkOrderItemNames([wo]); loadWorkOrderOperations(wo); }
  else { workOrderOperations.value = []; }
});

const groupedJcOperationRows = computed(() => {
  const ops = workOrderOperations.value || [];
  const direct = [];
  const bySub = new Map();
  ops.forEach((op) => {
    const sub = op.sub_assembly_bom || "";
    if (!sub) direct.push(op);
    else { if (!bySub.has(sub)) bySub.set(sub, []); bySub.get(sub).push(op); }
  });
  const groups = [];
  [...bySub.keys()].sort().forEach((sub) => {
    groups.push({ key: sub, label: subAssemblyBomLabel(sub), rows: bySub.get(sub) });
  });
  if (direct.length) groups.push({ key: "__direct__", label: "Final Assembly", rows: direct });
  return groups;
});

// A row already used by another (non-cancelled) Job Card is marked, not
// hidden -- someone may legitimately need a second card for a re-worked
// operation, but shouldn't pick it by accident thinking it's untouched.
function jcExistsForWoOpRow(rowName) {
  return (list.value || []).some(jc => jc.wo_operation_name === rowName && jc.name !== doc.value.name && jc.status !== "Cancelled");
}

// v-model bridge: selecting a specific Work Order Operation row fills in
// operation / workstation / sub_assembly_bom together, so they can't get
// out of sync with each other.
const selectedWoOpRow = computed({
  get: () => doc.value.wo_operation_name || "",
  set: (val) => {
    doc.value.wo_operation_name = val;
    const row = workOrderOperations.value.find(r => r.name === val);
    if (row) {
      doc.value.operation = row.operation || "";
      doc.value.workstation = row.workstation || "";
      doc.value.sub_assembly_bom = row.sub_assembly_bom || "";
    }
  },
});

let _uid = 0;
function nextUid() { return ++_uid; }
function ensureUids(rows) { (rows || []).forEach(r => { if (!r._uid) r._uid = nextUid(); }); return rows; }

async function loadDropdowns() {
  try {
    const [wos, ops, wks] = await Promise.all([
      apiList("Work Order", { fields: ["name"], filters: [["docstatus", "=", 1], ["status", "not in", ["Completed", "Stopped", "Cancelled"]]], limit: 2000, order: "name desc" }),
      apiList("Operation",  { fields: ["name"], filters: [["is_active", "=", 1]], limit: 1000, order: "name asc" }),
      apiList("Workstation",{ fields: ["name"], filters: [["is_active", "=", 1]], limit: 1000, order: "name asc" }),
    ]);
    workOrdersList.value   = wos || [];
    operationsList.value   = ops || [];
    workstationsList.value = wks || [];
  } catch (e) {
    toast("Could not load reference data", "error");
  }
}

onMounted(async () => {
  loading.value = true;
  await loadList();
  await loadDropdowns();
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
    // Deep-link support: Work Order page can send users here pre-filled via
    // /manufacturing/job-card/new?work_order=X&operation=Y&workstation=Z
    if (route.query.work_order) doc.value.work_order = route.query.work_order;
    if (route.query.operation) doc.value.operation = route.query.operation;
    if (route.query.wo_operation_name) doc.value.wo_operation_name = route.query.wo_operation_name;
    if (route.query.workstation) doc.value.workstation = route.query.workstation;
    if (route.query.for_quantity) doc.value.for_quantity = Number(route.query.for_quantity) || 1;
    if (route.query.sub_assembly_bom) doc.value.sub_assembly_bom = route.query.sub_assembly_bom;
    if (route.query.work_order && !workOrdersList.value.some(w => w.name === route.query.work_order))
      workOrdersList.value = [{ name: route.query.work_order }, ...workOrdersList.value];
    return;
  }
  detailLoading.value = true;
  try {
    const r = await apiGet("Job Card", route.params.name);
    if (!r.time_logs) r.time_logs = [];
    ensureUids(r.time_logs);
    doc.value = r;
    if (r.work_order) await loadWorkOrderItemNames([r.work_order]);
    if (r.sub_assembly_bom) await loadSubAssemblyBomNames([r.sub_assembly_bom]);
    // keep stale refs selectable
    if (r.work_order && !workOrdersList.value.some(w => w.name === r.work_order))
      workOrdersList.value = [{ name: r.work_order }, ...workOrdersList.value];
    if (r.operation && !operationsList.value.some(o => o.name === r.operation))
      operationsList.value = [{ name: r.operation }, ...operationsList.value];
    if (r.workstation && !workstationsList.value.some(w => w.name === r.workstation))
      workstationsList.value = [{ name: r.workstation }, ...workstationsList.value];
  } catch (e) {
    toast("Could not load Job Card", "error");
    goBackToList();
  }
  detailLoading.value = false;
}

function calcTimeDiff(tl) {
  if (!tl.from_time || !tl.to_time) { tl.time_in_mins = 0; tl._invalidRange = false; recomputeTotal(); return; }
  const diff = (new Date(tl.to_time) - new Date(tl.from_time)) / 60000;
  if (diff > 0) {
    tl.time_in_mins = parseFloat(diff.toFixed(2));
    tl._invalidRange = false;
  } else {
    // Don't silently zero this out and hide the problem — flag the row so the
    // user sees exactly which one is wrong, right where they're editing it,
    // instead of finding out from a generic toast after clicking Save.
    tl.time_in_mins = 0;
    tl._invalidRange = true;
  }
  recomputeTotal();
}

function recomputeTotal() {
  doc.value.total_time_in_mins = (doc.value.time_logs || []).reduce((s, r) => s + (r.time_in_mins || 0), 0);
}

function removeTimeLog(idx) {
  doc.value.time_logs.splice(idx, 1);
  recomputeTotal();
}

function startTimeLog(tl) {
  tl.from_time = new Date().toISOString().slice(0, 16);
  tl.to_time = "";
  tl.time_in_mins = 0;
  tl._invalidRange = false;
  recomputeTotal();
}

function stopTimeLog(tl) {
  tl.to_time = new Date().toISOString().slice(0, 16);
  calcTimeDiff(tl);
}

function addTimeLog() {
  if (!doc.value.time_logs) doc.value.time_logs = [];
  doc.value.time_logs.push({ _uid: nextUid(), from_time: "", to_time: "", time_in_mins: 0, employee: doc.value.employee || "" });
}

function fmtMins(m) {
  const h = Math.floor(m / 60), min = Math.round(m % 60);
  return h > 0 ? `${h}h ${min}m` : `${min}m`;
}
function fmtDate(d) {
  if (!d) return "";
  const obj = new Date(d);
  if (isNaN(obj)) return d;
  return obj.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

async function save() {
  if (!doc.value.work_order) return toast("Work Order is required", "error");
  if (!doc.value.operation)  return toast("Operation is required", "error");
  if ((doc.value.time_logs || []).some(tl => tl._invalidRange)) {
    return toast("Fix the time log row where To Time is before From Time", "error");
  }

  saving.value = true;
  try {
    const payload = {
      ...doc.value,
      time_logs: (doc.value.time_logs || []).map(({ _uid, _invalidRange, ...rest }) => rest),
    };
    const r = await apiSave(payload);
    toast(isNew.value ? "Job Card created successfully" : "Saved successfully");
    if (!r.time_logs) r.time_logs = [];
    ensureUids(r.time_logs);
    if (isNew.value) {
      router.replace(`/manufacturing/job-card/${r.name}`);
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
  plus:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>',
  open:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="7" y1="17" x2="17" y2="7"></line><polyline points="7 7 17 7 17 17"></polyline></svg>',
  chevronLeft: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>',
  card: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="9" y1="13" x2="15" y2="13"></line><line x1="9" y1="17" x2="13" y2="17"></line></svg>',
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
.bomx-list-view { display:flex; flex-direction:column; gap:14px; }

/* ── List toolbar ── */
.bomx-list-toolbar { display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap; }
.bomx-panel-title { font-size:16px; font-weight:700; color:var(--bx-text); }
.bomx-count { font-size:13px; font-weight:400; color:var(--bx-muted); }

/* ── Filters row ── */
.bomx-list-filters { display:flex; gap:10px; flex-wrap:wrap; }
.bomx-status-filter { width:200px; }
.bomx-search-full { flex:1; min-width:220px; }
.bomx-list-empty { grid-column:1/-1; text-align:center; padding:40px; color:var(--bx-muted); font-size:13px; background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); }

/* ── Summary strip (list view) ── */
.bomx-pp-sumstrip { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; }
.bomx-pp-sc { position:relative; background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); padding:12px 14px 12px 18px; text-align:left; overflow:hidden; }
.bomx-pp-sc-bar { position:absolute; top:0; left:0; width:3px; height:100%; }
.bomx-pp-sc-val { font-size:20px; font-weight:700; font-family:var(--bx-mono); color:var(--bx-text); }
.bomx-pp-sc-lbl { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.03em; color:var(--bx-muted); margin-top:2px; }

/* ── Job Card grid ── */
.bomx-jc-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:14px; }
.bomx-jc { background:var(--bx-surface); border:1.5px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; cursor:pointer; transition:all .15s; }
.bomx-jc:hover { border-color:var(--bx-mfgL); box-shadow:0 4px 16px rgba(26,110,247,.1); transform:translateY(-1px); }
.bomx-jc.jc-status-open { border-left:4px solid var(--bx-amber); }
.bomx-jc.jc-status-work-in-progress { border-left:4px solid var(--bx-blue); }
.bomx-jc.jc-status-completed { border-left:4px solid var(--bx-green); opacity:.9; }
.bomx-jc.jc-status-cancelled { border-left:4px solid var(--bx-muted); opacity:.75; }
.bomx-jc-hdr { padding:12px 14px; border-bottom:1px solid var(--bx-border); display:flex; align-items:flex-start; gap:10px; }
.bomx-jc-icon { width:36px; height:36px; border-radius:8px; display:flex; align-items:center; justify-content:center; flex-shrink:0; background:var(--bx-surf2); color:var(--bx-muted); }
.bomx-jc-icon.jc-icon-open { background:var(--bx-amberS); color:var(--bx-amber); }
.bomx-jc-icon.jc-icon-work-in-progress { background:var(--bx-blueS); color:var(--bx-blue); }
.bomx-jc-icon.jc-icon-completed { background:var(--bx-greenS); color:var(--bx-green); }
.bomx-jc-id { font-size:11px; font-weight:700; color:var(--bx-mfgB); }
.bomx-jc-op { font-size:14px; font-weight:700; color:var(--bx-text); margin:2px 0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.bomx-jc-wo { font-size:11.5px; color:var(--bx-muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.bomx-jc-sub { font-size:11px; color:var(--bx-mfgB); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; margin-top:2px; }
.bomx-jc-body { padding:10px 14px; display:grid; grid-template-columns:1fr 1fr; gap:8px; }
.bomx-jc-stat { display:flex; flex-direction:column; gap:2px; min-width:0; }
.bomx-jc-stat-lbl { font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); }
.bomx-jc-stat-val { font-size:13.5px; font-weight:700; color:var(--bx-text); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.bomx-jc-stat-val-wrap { white-space:normal; overflow-wrap:break-word; overflow:visible; text-overflow:clip; }
.bomx-jc-foot { padding:8px 14px; background:var(--bx-surf2); border-top:1px solid var(--bx-border); display:flex; align-items:center; justify-content:space-between; gap:8px; font-size:12px; color:var(--bx-muted); }

/* ── Badges ── */
.bomx-badge { display:inline-flex; align-items:center; padding:2px 8px; border-radius:20px; font-size:11px; font-weight:600; white-space:nowrap; }
.badge-active { background:var(--bx-greenS); color:var(--bx-green); }
.badge-obsolete { background:#F1F3F5; color:var(--bx-muted); }
.badge-wip { background:var(--bx-blueS); color:var(--bx-blue); }
.badge-open { background:var(--bx-amberS); color:var(--bx-amber); }

.bomx-hdr-fields { display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; padding:16px 22px; border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); }
.bomx-hf-label { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); margin-bottom:4px; }
.bomx-field-hint { font-size:12px; color:var(--bx-muted); margin-top:5px; }
.bomx-toggle-row { display:flex; gap:20px; padding:14px 22px; flex-wrap:wrap; background:var(--bx-surf2); border-bottom:1px solid var(--bx-border); }
.bomx-toggle { display:flex; align-items:center; gap:6px; font-size:12.5px; font-weight:600; color:var(--bx-text); }

.bomx-section-lbl { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--bx-muted); margin-bottom:8px; }

/* ══════════ Drawer (Job Card detail slides over the list) ══════════ */
.jc-drawer-bg {
  position: fixed; inset: 0; z-index: 900;
  background: rgba(15,17,23,.45);
  display: flex; justify-content: flex-end;
}
.jc-drawer-panel {
  width: 700px; max-width: 97vw; height: 100%;
  background: var(--bx-surface);
  display: flex; flex-direction: column;
  box-shadow: -20px 0 60px rgba(0,0,0,.18);
}
.jc-drawer-hdr {
  flex-shrink: 0;
  padding: 16px 22px;
  background: linear-gradient(135deg, var(--bx-mfgB), var(--bx-mfg));
  display: flex; align-items: flex-start; justify-content: space-between; gap: 12px;
}
.jc-drawer-title { font-size: 17px; font-weight: 700; color: #fff; margin-bottom: 3px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.jc-drawer-sub { font-size: 12.5px; color: rgba(255,255,255,.75); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.jc-drawer-badge { background: rgba(255,255,255,.92) !important; }
.jc-drawer-close {
  background: rgba(255,255,255,.2); border: none; cursor: pointer; color: #fff;
  width: 28px; height: 28px; border-radius: 6px; font-size: 14px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
  transition: background .15s;
}
.jc-drawer-close:hover { background: rgba(255,255,255,.32); }
.jc-drawer-toggle-row { display:flex; gap:16px; padding:14px 22px; flex-wrap:wrap; border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); }
.jc-drawer-body { flex: 1; overflow-y: auto; padding: 20px 22px; }
.jc-drawer-footer {
  flex-shrink: 0; padding: 14px 22px; border-top: 1px solid var(--bx-border);
  background: var(--bx-surf2); display: flex; justify-content: flex-end; align-items: center; gap: 8px;
}

/* Backdrop fade */
.jc-drawer-fade-enter-active, .jc-drawer-fade-leave-active { transition: background-color .22s ease; }
.jc-drawer-fade-enter-from, .jc-drawer-fade-leave-to { background-color: rgba(15,17,23,0) !important; }

/* Panel slide, driven off the same enter/leave classes as the backdrop */
.jc-drawer-panel { transition: transform .22s ease; transform: translateX(0); }
.jc-drawer-fade-enter-from .jc-drawer-panel,
.jc-drawer-fade-leave-to .jc-drawer-panel { transform: translateX(100%); }

/* ── Time log cards (reuse rm-card pattern) ── */
.bomx-rm-cards { display:flex; flex-direction:column; gap:10px; }
.bomx-rm-card { background:#fff; border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; box-shadow:0 1px 3px rgba(16,24,40,.04); }
.bomx-rm-card-hdr { display:flex; align-items:center; gap:10px; padding:10px 14px; background:var(--bx-mfgS); border-bottom:1px solid var(--bx-border); }
.bomx-rm-card-title { flex:1; min-width:0; font-weight:600; font-size:13px; }
.bomx-rm-card-amt { display:flex; flex-direction:column; align-items:flex-end; flex-shrink:0; gap:1px; }
.bomx-rm-card-amt-lbl { font-size:9.5px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; color:var(--bx-muted); }
.bomx-rm-card-body { display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:10px; padding:12px 14px; }
.bomx-rm-field { display:flex; flex-direction:column; gap:4px; min-width:0; }
.bomx-rm-field label { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); }
.bomx-rm-field .bomx-fi { width:100%; }
@media (max-width:640px) { .bomx-rm-card-body { grid-template-columns:1fr 1fr; } }

.bomx-tree-empty { text-align:center; padding:20px; color:var(--bx-muted); font-size:13px; }
.bomx-add-row { display:flex; align-items:center; gap:8px; padding:8px 12px; color:var(--bx-mfg); cursor:pointer; font-size:13px; font-weight:600; border-radius:var(--bx-rsm); }
.bomx-add-row:hover { background:var(--bx-mfgS); }

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
.bomx-btn-icon.danger { color:var(--bx-red); }
.bomx-btn-icon.danger:hover { background:var(--bx-redS); border-color:var(--bx-red); }

.shimmer { background:linear-gradient(90deg,#f1f3f5 25%,#e9ecef 37%,#f1f3f5 63%); background-size:400% 100%; animation:shimmer 1.4s ease infinite; }
@keyframes shimmer { 0%{background-position:100% 50%} 100%{background-position:0 50%} }

/* ── Mobile responsive ── */
@media (max-width:768px) {
  .bomx-page { padding:10px; overflow-x:hidden; }
  .bomx-list-view { gap:10px; }
  .bomx-jc-grid { grid-template-columns:1fr; }
  .bomx-pp-sumstrip { grid-template-columns:repeat(2,1fr); }
  .bomx-status-filter { width:100%; }

  .jc-drawer-panel { width:100vw; max-width:100vw; }
  .jc-drawer-hdr { padding:14px 16px; }
  .jc-drawer-toggle-row { padding:10px 16px 12px; gap:14px; }
  .jc-drawer-body { padding:14px 16px; }
  .bomx-hdr-fields { grid-template-columns:1fr; padding:12px 16px; gap:10px; }

  .bomx-rm-card-body { grid-template-columns:1fr 1fr; }
  .jc-drawer-footer { flex-wrap:wrap; }
}

@media (max-width:420px) {
  .bomx-rm-card-body { grid-template-columns:1fr; }
}
</style>