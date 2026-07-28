<template>
<div class="list-page">

  <!-- ── Toolbar ── -->
  <div class="sales-toolbar">
    <div class="sales-search">
      <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
      <input v-model="search" placeholder="Search by movement#, asset…" class="sales-search-input"/>
    </div>
    <div class="sales-pills">
      <button v-for="f in PURPOSE_FILTERS" :key="f.key" class="sales-pill" :class="{active:filterPurpose===f.key}" @click="filterPurpose=f.key">
        {{ f.label }}<span v-if="f.key" class="sales-pill-count">{{ purposeCounts[f.key] || 0 }}</span>
      </button>
    </div>
    <div class="sales-actions">
      <button class="sales-btn-ghost" @click="loadList" title="Refresh" :disabled="loading"><span v-html="icon('refresh',14)"></span></button>
      <button class="sales-btn-primary" @click="openAdd"><span v-html="icon('plus',13)"></span> New Movement</button>
    </div>
  </div>

  <div class="bk-kpi-grid">
    <div class="bk-kpi-card bk-kpi-accent clickable" @click="filterStatus=''">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#dbeafe"><span v-html="icon('truck',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Total Movements</div>
          <div class="bk-kpi-value">{{ list.length }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">transfer + issue + receipt</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card bk-kpi-success clickable" @click="filterStatus='submitted'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#dcfce7"><span v-html="icon('check',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Submitted</div>
          <div class="bk-kpi-value bk-kpi-green">{{ statusCounts.submitted || 0 }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">applied to assets</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card clickable" @click="filterStatus='draft'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#fef3c7"><span v-html="icon('edit',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Draft</div>
          <div class="bk-kpi-value bk-kpi-amber">{{ statusCounts.draft || 0 }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">not yet applied</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card clickable" @click="filterPurpose=''">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#eef2ff"><span v-html="icon('box',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Assets Moved</div>
          <div class="bk-kpi-value">{{ distinctAssets }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">unique assets touched</div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── Table ── -->
  <div class="inv-table-wrap">
    <table class="inv-table inv-desktop-table">
      <thead><tr>
        <th>DATE</th>
        <th>MOVEMENT#</th>
        <th>ASSET</th>
        <th>PURPOSE</th>
        <th>FROM</th>
        <th>TO</th>
        <th>STATUS</th>
        <th style="width:90px;text-align:center">ACTIONS</th>
      </tr></thead>
      <tbody>
        <template v-if="loading">
          <tr v-for="n in 6" :key="n" class="shimmer-row">
            <td><div class="shimmer" style="width:80px"></div></td>
            <td><div class="shimmer" style="width:110px"></div></td>
            <td><div class="shimmer" style="width:140px"></div></td>
            <td><div class="shimmer" style="width:70px"></div></td>
            <td><div class="shimmer" style="width:100px"></div></td>
            <td><div class="shimmer" style="width:100px"></div></td>
            <td><div class="shimmer" style="width:70px"></div></td>
            <td></td>
          </tr>
        </template>
        <template v-else>
          <tr v-for="row in paged" :key="row.name" class="inv-row" @click="openView(row)">
            <td class="text-muted mono-sm">{{ row.movement_date }}</td>
            <td><span class="inv-link">{{ row.name }}</span></td>
            <td>{{ row.asset_name || row.asset }}<div class="asset-code">{{ row.asset }}</div></td>
            <td><span class="am-purpose-badge" :class="purposeClass(row.purpose)">{{ row.purpose }}</span></td>
            <td class="text-muted" style="font-size:12.5px">{{ fromSummary(row) }}</td>
            <td class="text-muted" style="font-size:12.5px">{{ toSummary(row) }}</td>
            <td><span class="inv-status-badge" :class="statusClass(row)">{{ statusLabel(row) }}</span></td>
            <td style="text-align:center" @click.stop>
              <button class="inv-act-btn" @click="openView(row)" title="View"><span v-html="icon('eye',13)"></span></button>
            </td>
          </tr>
          <tr v-if="!sorted.length">
            <td colspan="8" class="bk-empty-state">
              <div class="bk-empty-inner">
                <template v-if="search||filterStatus||filterPurpose">
                  <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.3"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                  <p class="bk-empty-title">No movements match your filters</p>
                </template>
                <template v-else>
                  <p class="bk-empty-title">No asset movements yet</p>
                  <p class="bk-empty-sub">Record a transfer, issue or receipt to track where an asset is.</p>
                  <button class="bk-empty-btn" @click="openAdd"><span v-html="icon('plus',13)"></span> New Movement</button>
                </template>
              </div>
            </td>
          </tr>
        </template>
      </tbody>
    </table>

    <div class="assets-mobile-cards">
      <template v-if="loading">
        <div v-for="n in 4" :key="n" class="b-shimmer" style="height:86px;border-radius:10px"></div>
      </template>
      <div v-else-if="!sorted.length" style="text-align:center;padding:40px;color:#868E96">No movements found</div>
      <div v-else v-for="row in paged" :key="row.name" class="ii-mob-card" @click="openView(row)">
        <div class="ii-mob-card-main">
          <div class="ii-mob-card-top">
            <span class="inv-link">{{ row.name }}</span>
            <span class="inv-status-badge" :class="statusClass(row)">{{ statusLabel(row) }}</span>
          </div>
          <div style="font-size:12px;color:#6b7280;margin-top:4px">{{ row.asset_name || row.asset }} • {{ row.purpose }}</div>
          <div style="display:flex;justify-content:space-between;margin-top:6px;font-size:12px;color:#475569">
            <span>{{ fromSummary(row) }}</span>
            <span>→ {{ toSummary(row) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div v-if="!loading && sorted.length" style="padding:12px 0px 4px">
    <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="sorted.length"/>
  </div>

  <!-- ══ Drawer ══ -->
  <Teleport to="body">
    <div v-if="drawerOpen" class="inv-drawer-bg" @click.self="closeDrawer">
      <div class="inv-drawer-panel is-add">

        <div class="inv-dh">
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
            <div class="inv-dh-title">{{ isNew ? 'New Asset Movement' : movement.name }}</div>
            <span v-if="isNew" class="add-status-badge">Draft</span>
            <span v-else class="inv-status-badge" :class="statusClass(movement)">{{ statusLabel(movement) }}</span>
          </div>
          <button class="inv-dclose" @click="closeDrawer" title="Close"><span v-html="icon('x',16)"></span></button>
        </div>

        <div class="inv-dbody">
          <template v-if="detailLoading">
            <div class="shimmer" style="height:200px;border-radius:10px"></div>
          </template>
          <template v-else>

            <div v-if="movement.docstatus===1" class="am-notice">
              <span v-html="icon('check',14)"></span>
              <span>
                Submitted — Asset {{ movement.asset }} location/department updated to the target values below.
              </span>
            </div>

            <!-- Movement details -->
            <div class="add-card">
              <div class="add-card-header" @click="collapsed.details = !collapsed.details">
                <div class="add-card-title">
                  <span class="add-card-title-icon"><span v-html="icon('truck',16)"></span></span>
                  Movement Details
                </div>
                <span class="add-card-chevron" :class="{collapsed:collapsed.details}"><span v-html="icon('chevD',14)"></span></span>
              </div>
              <div class="add-card-body" :class="{collapsed:collapsed.details}">
                <div class="inv-fg inv-fg2">
                  <div>
                    <label class="inv-lbl">Asset <span class="inv-req">*</span></label>
                    <SearchableSelect
                      v-model="movement.asset"
                      :options="assetOptions"
                      placeholder="Select asset to move"
                      :disabled="!readOnlyEditable"
                      @update:modelValue="onPickAsset"
                      @search="fetchAssets"
                    />
                  </div>
                  <div>
                    <label class="inv-lbl">Purpose <span class="inv-req">*</span></label>
                    <select v-model="movement.purpose" class="inv-fi" :disabled="!readOnlyEditable">
                      <option value="Transfer">Transfer</option>
                      <option value="Issue">Issue</option>
                      <option value="Receipt">Receipt</option>
                    </select>
                  </div>
                  <div>
                    <label class="inv-lbl">Movement Date <span class="inv-req">*</span></label>
                    <input v-model="movement.movement_date" type="date" class="inv-fi" :disabled="!readOnlyEditable"/>
                  </div>
                  <div>
                    <label class="inv-lbl">Company</label>
                    <input :value="movement.company" class="inv-fi" disabled/>
                  </div>
                </div>

                <div v-if="selectedAsset" class="am-preview-box">
                  <div class="am-preview-row"><span>Current Location</span><span class="mono-sm">{{ selectedAsset.location || '—' }}</span></div>
                  <div class="am-preview-row"><span>Current Department</span><span class="mono-sm">{{ selectedAsset.department || '—' }}</span></div>
                </div>

                <p class="am-purpose-hint">{{ purposeHint }}</p>
              </div>
            </div>

            <!-- From -->
            <div class="add-card">
              <div class="add-card-header" @click="collapsed.from = !collapsed.from">
                <div class="add-card-title">
                  <span class="add-card-title-icon"><span v-html="icon('warehouse',16)"></span></span>
                  From
                </div>
                <span class="add-card-chevron" :class="{collapsed:collapsed.from}"><span v-html="icon('chevD',14)"></span></span>
              </div>
              <div class="add-card-body" :class="{collapsed:collapsed.from}">
                <div class="inv-fg inv-fg2">
                  <div>
                    <label class="inv-lbl">Source Location</label>
                    <input v-model="movement.source_location" type="text" class="inv-fi" placeholder="Defaults to asset's current location" :disabled="!readOnlyEditable"/>
                  </div>
                  <div>
                    <label class="inv-lbl">Source Department</label>
                    <SearchableSelect
                      v-model="movement.source_department"
                      :options="departmentOptions"
                      placeholder="Defaults to asset's current department"
                      :disabled="!readOnlyEditable"
                      @search="fetchDepartments"
                    />
                  </div>
                  <div>
                    <label class="inv-lbl">Source Custodian</label>
                    <input v-model="movement.source_custodian" type="text" class="inv-fi" placeholder="Person currently holding the asset" :disabled="!readOnlyEditable"/>
                  </div>
                </div>
              </div>
            </div>

            <!-- To -->
            <div class="add-card">
              <div class="add-card-header" @click="collapsed.to = !collapsed.to">
                <div class="add-card-title">
                  <span class="add-card-title-icon"><span v-html="icon('order',16)"></span></span>
                  To
                </div>
                <span class="add-card-chevron" :class="{collapsed:collapsed.to}"><span v-html="icon('chevD',14)"></span></span>
              </div>
              <div class="add-card-body" :class="{collapsed:collapsed.to}">
                <div class="inv-fg inv-fg2">
                  <div>
                    <label class="inv-lbl">Target Location</label>
                    <input v-model="movement.target_location" type="text" class="inv-fi" placeholder="Where the asset is going" :disabled="!readOnlyEditable || movement.purpose==='Issue'"/>
                  </div>
                  <div>
                    <label class="inv-lbl">Target Department</label>
                    <SearchableSelect
                      v-model="movement.target_department"
                      :options="departmentOptions"
                      placeholder="Department it's moving to"
                      :disabled="!readOnlyEditable || movement.purpose==='Issue'"
                      @search="fetchDepartments"
                    />
                  </div>
                  <div>
                    <label class="inv-lbl">Target Custodian</label>
                    <input v-model="movement.target_custodian" type="text" class="inv-fi" placeholder="Person receiving the asset" :disabled="!readOnlyEditable"/>
                  </div>
                </div>
              </div>
            </div>

            <!-- Reference & Remarks -->
            <div class="add-card">
              <div class="add-card-header" @click="collapsed.ref = !collapsed.ref">
                <div class="add-card-title">
                  <span class="add-card-title-icon"><span v-html="icon('file',16)"></span></span>
                  Reference &amp; Remarks
                </div>
                <span class="add-card-chevron" :class="{collapsed:collapsed.ref}"><span v-html="icon('chevD',14)"></span></span>
              </div>
              <div class="add-card-body" :class="{collapsed:collapsed.ref}">
                <div class="inv-fg inv-fg2">
                  <div>
                    <label class="inv-lbl">Reference Document Type</label>
                    <input v-model="movement.reference_doctype" type="text" class="inv-fi" placeholder="e.g. Material Request" :disabled="!readOnlyEditable"/>
                  </div>
                  <div>
                    <label class="inv-lbl">Reference Document Name</label>
                    <input v-model="movement.reference_name" type="text" class="inv-fi" :disabled="!readOnlyEditable || !movement.reference_doctype"/>
                  </div>
                </div>
                <div style="margin-top:14px">
                  <label class="inv-lbl">Remarks</label>
                  <textarea v-model="movement.remarks" class="inv-fi" rows="2" placeholder="Optional notes" :disabled="!readOnlyEditable"></textarea>
                </div>
              </div>
            </div>

          </template>
        </div>

        <!-- Footer -->
        <div class="inv-dfooter">
          <template v-if="readOnlyEditable">
            <button class="add-btn-cancel" @click="closeDrawer">Cancel</button>
            <button class="add-btn-draft" :disabled="saving" @click="save('Draft')">
              <span v-html="icon('save',13)"></span> Save Draft
            </button>
            <button class="add-btn-more" :disabled="saving" @click="save('Submitted')">
              <span v-html="icon('check',13)"></span> {{ saving ? 'Saving…' : 'Save & Submit' }}
            </button>
          </template>
          <template v-else-if="movement.docstatus===1">
            <div class="add-footer-status">{{ movement.name }} — submitted, applied to asset</div>
            <button class="add-btn-cancel" style="color:#dc2626" :disabled="cancelling" @click="cancelMovement">
              <span v-html="icon('cancel',13)"></span> {{ cancelling ? 'Cancelling…' : 'Cancel Movement' }}
            </button>
          </template>
          <template v-else>
            <button class="add-btn-cancel" @click="closeDrawer">Close</button>
          </template>
        </div>

      </div>
    </div>
  </Teleport>
</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { apiGet, apiList, apiSave, apiSubmit, apiCancel } from '@/api/client.js';
import { useToast } from '@/composables/useToast.js';
import { useConfirm } from '@/composables/useConfirm.js';
import { icon } from '@/utils/icons.js';
import SearchableSelect from '@/components/SearchableSelect.vue';
import Pagination from '@/components/Pagination.vue';

const toast = useToast();
const { confirm } = useConfirm();

function todayLocal() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

// ── LIST STATE ──────────────────────────────────────────────
const loading = ref(false);
const list = ref([]);
const search = ref('');
const filterStatus = ref('');
const filterPurpose = ref('');
const page = ref(1);
const pageSize = ref(20);

const PURPOSE_FILTERS = [
  { key: '', label: 'All' },
  { key: 'Transfer', label: 'Transfer' },
  { key: 'Issue', label: 'Issue' },
  { key: 'Receipt', label: 'Receipt' },
];

const statusCounts = computed(() => ({
  draft: list.value.filter(i => i.docstatus === 0).length,
  submitted: list.value.filter(i => i.docstatus === 1).length,
  cancelled: list.value.filter(i => i.docstatus === 2).length,
}));

const purposeCounts = computed(() => {
  const counts = {};
  for (const p of ['Transfer', 'Issue', 'Receipt']) {
    counts[p] = list.value.filter(i => i.purpose === p).length;
  }
  return counts;
});

const distinctAssets = computed(() => new Set(list.value.map(r => r.asset).filter(Boolean)).size);

async function loadList() {
  loading.value = true;
  try {
    const fields = [
      'name', 'asset', 'company', 'purpose', 'movement_date',
      'source_location', 'source_department', 'source_custodian',
      'target_location', 'target_department', 'target_custodian',
      'docstatus', 'modified',
    ];
    list.value = await apiList('Asset Movement', { fields, limit: 1000, order: 'movement_date desc' }) || [];
    const assetNames = [...new Set(list.value.map(r => r.asset).filter(Boolean))];
    if (assetNames.length) {
      const rows = await apiList('Asset', {
        fields: ['name', 'asset_name'],
        filters: [['name', 'in', assetNames]],
        limit: assetNames.length,
      });
      const byName = Object.fromEntries((rows || []).map(r => [r.name, r.asset_name]));
      list.value.forEach(r => { r.asset_name = byName[r.asset] || r.asset; });
    }
  } catch (e) {
    toast.error('Failed to load movements: ' + e.message);
    list.value = [];
  }
  loading.value = false;
}

const sorted = computed(() => {
  let r = list.value;
  if (filterStatus.value === 'draft') r = r.filter(i => i.docstatus === 0);
  else if (filterStatus.value === 'submitted') r = r.filter(i => i.docstatus === 1);
  else if (filterStatus.value === 'cancelled') r = r.filter(i => i.docstatus === 2);
  if (filterPurpose.value) r = r.filter(i => i.purpose === filterPurpose.value);
  const q = search.value.toLowerCase().trim();
  if (q) r = r.filter(i =>
    (i.name || '').toLowerCase().includes(q) ||
    (i.asset || '').toLowerCase().includes(q) ||
    (i.asset_name || '').toLowerCase().includes(q)
  );
  return r;
});

const paged = computed(() => {
  const start = (page.value - 1) * pageSize.value;
  return sorted.value.slice(start, start + pageSize.value);
});
watch([search, filterStatus, filterPurpose], () => { page.value = 1; });

function statusLabel(row) {
  if (row.docstatus === 1) return 'Submitted';
  if (row.docstatus === 2) return 'Cancelled';
  return 'Draft';
}
function statusClass(row) {
  if (row.docstatus === 1) return 'status-submitted';
  if (row.docstatus === 2) return 'status-cancelled';
  return 'status-draft';
}
function purposeClass(purpose) {
  if (purpose === 'Issue') return 'am-purpose-issue';
  if (purpose === 'Receipt') return 'am-purpose-receipt';
  return 'am-purpose-transfer';
}
function fromSummary(row) {
  return [row.source_location, row.source_department, row.source_custodian].filter(Boolean).join(' / ') || '—';
}
function toSummary(row) {
  return [row.target_location, row.target_department, row.target_custodian].filter(Boolean).join(' / ') || '—';
}

// ── DRAWER STATE ─────────────────────────────────────────────
const drawerOpen = ref(false);
const currentName = ref(null);
const isNew = computed(() => currentName.value === null);
const detailLoading = ref(false);
const saving = ref(false);
const cancelling = ref(false);
// Editable while it's a fresh unsaved doc, or an already-saved Draft (docstatus 0).
const readOnlyEditable = computed(() => isNew.value || movement.value.docstatus === 0);

const collapsed = reactive({ details: false, from: false, to: false, ref: true });

function emptyMovement() {
  return {
    doctype: 'Asset Movement',
    asset: '',
    company: window.__booksCompany || '',
    purpose: 'Transfer',
    movement_date: todayLocal(),
    source_location: '',
    source_department: '',
    source_custodian: '',
    target_location: '',
    target_department: '',
    target_custodian: '',
    reference_doctype: '',
    reference_name: '',
    remarks: '',
    docstatus: 0,
  };
}
const movement = ref(emptyMovement());

const purposeHint = computed(() => {
  const p = movement.value.purpose;
  if (p === 'Transfer') return 'Moves the asset between company locations, departments, or custodians. Fill in at least one Target field.';
  if (p === 'Issue') return 'Moves the asset out to a custodian (e.g. field staff) — leave Target Location/Department blank, use Target Custodian only.';
  if (p === 'Receipt') return 'Returns the asset to a company location — Target Location and/or Target Department is required.';
  return '';
});

watch(() => movement.value.purpose, (p) => {
  if (p === 'Issue') {
    movement.value.target_location = '';
    movement.value.target_department = '';
  }
});

// ── Asset lookup / preview ──────────────────────────────────
const assetOptions = ref([]);
const assetInfoMap = ref({});
const selectedAsset = computed(() => assetInfoMap.value[movement.value.asset] || null);

let assetSearchTimer = null;
function fetchAssets(q = '') {
  clearTimeout(assetSearchTimer);
  assetSearchTimer = setTimeout(async () => {
    try {
      const filters = [['docstatus', '=', 1]];
      if (q) filters.push(['asset_name', 'like', `%${q}%`]);
      const rows = await apiList('Asset', {
        fields: ['name', 'asset_name', 'company', 'location', 'department'],
        filters, limit: 30, order: 'asset_name asc',
      });
      assetOptions.value = (rows || []).map(r => ({ value: r.name, label: r.asset_name ? `${r.asset_name} (${r.name})` : r.name }));
      for (const r of rows || []) assetInfoMap.value[r.name] = r;
    } catch (e) {
      assetOptions.value = [];
    }
  }, 250);
}

async function onPickAsset(name) {
  if (!name) return;
  let info = assetInfoMap.value[name];
  if (!info) {
    try {
      info = await apiGet('Asset', name);
      assetInfoMap.value[name] = info;
    } catch (e) {
      toast.error('Could not load asset: ' + e.message);
      return;
    }
  }
  movement.value.company = info.company || movement.value.company;
  // Only prefill source_* when the person hasn't already typed something --
  // the backend does this too on save, this just previews it sooner.
  if (!movement.value.source_location) movement.value.source_location = info.location || '';
  if (!movement.value.source_department) movement.value.source_department = info.department || '';
}

// ── Departments ──────────────────────────────────────────────
const departments = ref([]);
const departmentOptions = computed(() => departments.value.map(d => ({ value: d.name, label: d.department_name || d.name })));
async function fetchDepartments(q = '') {
  try {
    const filters = [];
    if (q) filters.push(['name', 'like', `%${q}%`]);
    departments.value = await apiList('Department', { fields: ['name', 'department_name'], filters, limit: 30, order: 'name asc' });
  } catch (e) {
    departments.value = [];
  }
}

// ── Open / close / load ─────────────────────────────────────
function openAdd() {
  currentName.value = null;
  movement.value = emptyMovement();
  drawerOpen.value = true;
}
function openView(row) {
  currentName.value = row.name;
  drawerOpen.value = true;
  loadDetail(row.name);
}
function closeDrawer() {
  drawerOpen.value = false;
}

async function loadDetail(name) {
  detailLoading.value = true;
  try {
    const doc = await apiGet('Asset Movement', name);
    movement.value = doc;
    if (doc.asset && !assetInfoMap.value[doc.asset]) {
      try { assetInfoMap.value[doc.asset] = await apiGet('Asset', doc.asset); } catch (e) { /* non-fatal */ }
    }
  } catch (e) {
    toast.error('Could not load ' + name + ': ' + e.message);
  }
  detailLoading.value = false;
}

// ── Save / Submit / Cancel ──────────────────────────────────
function validate() {
  if (!movement.value.asset) { toast.error('Select an asset to move.'); return false; }
  if (!movement.value.movement_date) { toast.error('Movement Date is required.'); return false; }
  const m = movement.value;
  if (m.purpose === 'Transfer' && !(m.target_location || m.target_department || m.target_custodian)) {
    toast.error('Transfer requires at least one of Target Location, Target Department or Target Custodian.');
    return false;
  }
  if (m.purpose === 'Issue' && !(m.source_location || m.source_department || m.source_custodian)) {
    toast.error('Issue requires at least one of Source Location, Source Department or Source Custodian.');
    return false;
  }
  if (m.purpose === 'Receipt' && !(m.target_location || m.target_department)) {
    toast.error('Receipt requires Target Location and/or Target Department.');
    return false;
  }
  return true;
}

async function save(targetStatus) {
  if (!validate()) return;
  saving.value = true;
  try {
    const doc = { ...movement.value };
    if (isNew.value) delete doc.name;
    if (!doc.company) doc.company = window.__booksCompany || '';
    const saved = await apiSave(doc);
    const savedName = saved?.name || doc.name;
    currentName.value = savedName;
    movement.value = saved;

    if (targetStatus === 'Submitted' && saved?.docstatus !== 1) {
      try {
        await apiSubmit('Asset Movement', savedName);
        await loadDetail(savedName);
        toast.success('Movement submitted.');
      } catch (subErr) {
        toast.error('Saved as draft — submit failed: ' + (subErr.message || subErr));
        loadList();
        return;
      }
    } else {
      toast.success(isNew.value ? 'Movement saved' : 'Movement updated');
    }
    loadList();
  } catch (e) {
    toast.error('Failed to save movement: ' + e.message);
  } finally {
    saving.value = false;
  }
}

async function cancelMovement() {
  const ok = await confirm({
    title: 'Cancel Movement',
    body: `Cancel ${movement.value.name}? This reverts the asset's location/department back to this movement's source values.`,
    okLabel: 'Cancel Movement',
    okStyle: 'danger',
  });
  if (!ok) return;
  cancelling.value = true;
  try {
    await apiCancel('Asset Movement', movement.value.name);
    toast.success('Movement cancelled.');
    await loadDetail(movement.value.name);
    loadList();
  } catch (e) {
    toast.error('Cancel failed: ' + e.message);
  } finally {
    cancelling.value = false;
  }
}

onMounted(() => {
  loadList();
  fetchAssets();
  fetchDepartments();
});
</script>

<style scoped>
.asset-code { margin-top: 3px; color: #9ca3af; font-size: 11px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
.assets-mobile-cards { display: none; }
.text-muted { color: #9ca3af; }
.mono-sm { font-size: 13px; }
.am-purpose-badge { padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; white-space: nowrap; }
.am-purpose-transfer { background: #dbeafe; color: #1d4ed8; }
.am-purpose-issue { background: #fee2e2; color: #b91c1c; }
.am-purpose-receipt { background: #dcfce7; color: #15803d; }
.am-notice {
  background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 8px;
  padding: 10px 14px; margin-bottom: 18px; font-size: 13px; color: #475569;
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.am-preview-box {
  margin-top: 14px; padding: 12px 14px; background: #f8f9fc; border: 1px solid #e2e8f0;
  border-radius: 8px; display: flex; flex-direction: column; gap: 6px;
}
.am-preview-row { display: flex; justify-content: space-between; font-size: 12.5px; color: #475569; }
.am-purpose-hint { margin: 12px 0 0; font-size: 12px; color: #94a3b8; line-height: 1.5; }
.b-shimmer {
  height: 100%;
  border-radius: 8px;
  background: linear-gradient(90deg, #f0f2f5 25%, #e4e7ec 50%, #f0f2f5 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite;
}
@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
@media (max-width: 768px) {
  .inv-desktop-table { display: none; }
  .assets-mobile-cards { display: flex; flex-direction: column; gap: 10px; padding: 12px; }
}
</style>