<template>
<div class="list-page">

  <!-- ── Toolbar ── -->
  <div class="sales-toolbar">
    <div class="sales-search">
      <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
      <input v-model="search" placeholder="Search by voucher#, asset…" class="sales-search-input"/>
    </div>
    <div class="sales-pills">
      <button v-for="f in FILTERS" :key="f.key" class="sales-pill" :class="{active:filterStatus===f.key}" @click="filterStatus=f.key">
        {{ f.label }}<span v-if="f.key" class="sales-pill-count">{{ counts[f.key] }}</span>
      </button>
    </div>
    <div class="sales-actions">
      <button class="sales-btn-ghost" @click="loadList" title="Refresh" :disabled="loading"><span v-html="icon('refresh',14)"></span></button>
      <button class="sales-btn-primary" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''" @click="openAdd"><span v-html="icon('plus',13)"></span> New Repair</button>
    </div>
  </div>

  <div class="bk-kpi-grid">
    <div class="bk-kpi-card bk-kpi-accent clickable" @click="filterStatus=''">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#dbeafe"><span v-html="icon('gear',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Total Repairs</div>
          <div class="bk-kpi-value">{{ list.length }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">capitalized + expensed</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card bk-kpi-success clickable" @click="filterStatus='submitted'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#dcfce7"><span v-html="icon('check',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Submitted</div>
          <div class="bk-kpi-value bk-kpi-green">{{ counts.submitted || 0 }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">GL posted</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card clickable" @click="filterStatus=''">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#eef2ff;color:#4338ca"><span v-html="icon('trend',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Capitalized</div>
          <div class="bk-kpi-value" style="color:#4338ca">{{ INR(totalCapitalized) }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">added to asset value</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card clickable" @click="filterStatus=''">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#fef3c7;color:#92400e"><span v-html="icon('rupee',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Expensed</div>
          <div class="bk-kpi-value bk-kpi-amber">{{ INR(totalExpensed) }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">period cost</div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── Table ── -->
  <div class="inv-table-wrap">
    <table class="inv-table inv-desktop-table">
      <thead><tr>
        <th>DATE</th>
        <th>VOUCHER#</th>
        <th>ASSET</th>
        <th>TYPE</th>
        <th class="ta-r">REPAIR COST</th>
        <th>DESCRIPTION</th>
        <th>STATUS</th>
        <th style="width:90px;text-align:center">ACTIONS</th>
      </tr></thead>
      <tbody>
        <template v-if="loading">
          <tr v-for="n in 6" :key="n" class="shimmer-row">
            <td><div class="shimmer" style="width:80px"></div></td>
            <td><div class="shimmer" style="width:110px"></div></td>
            <td><div class="shimmer" style="width:140px"></div></td>
            <td><div class="shimmer" style="width:80px"></div></td>
            <td><div class="shimmer" style="width:80px;margin-left:auto"></div></td>
            <td><div class="shimmer" style="width:160px"></div></td>
            <td><div class="shimmer" style="width:70px"></div></td>
            <td></td>
          </tr>
        </template>
        <template v-else>
          <tr v-for="row in paged" :key="row.name" class="inv-row" @click="openView(row)">
            <td class="text-muted mono-sm">{{ row.repair_date }}</td>
            <td><span class="inv-link">{{ row.name }}</span></td>
            <td>{{ row.asset_name || row.asset }}<div class="asset-code">{{ row.asset }}</div></td>
            <td><span class="ar-type-badge" :class="row.is_capitalized ? 'ar-type-cap' : 'ar-type-exp'">{{ row.is_capitalized ? 'Capitalized' : 'Expensed' }}</span></td>
            <td class="ta-r mono-sm">{{ INR(row.repair_cost) }}</td>
            <td class="text-muted" style="font-size:12.5px;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ row.description }}</td>
            <td><span class="inv-status-badge" :class="statusClass(row)">{{ statusLabel(row) }}</span></td>
            <td style="text-align:center" @click.stop>
              <button class="inv-act-btn" @click="openView(row)" title="View"><span v-html="icon('eye',13)"></span></button>
            </td>
          </tr>
          <tr v-if="!sorted.length">
            <td colspan="8" class="bk-empty-state">
              <div class="bk-empty-inner">
                <template v-if="search||filterStatus">
                  <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.3"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                  <p class="bk-empty-title">No repairs match your filters</p>
                </template>
                <template v-else>
                  <p class="bk-empty-title">No asset repairs yet</p>
                  <p class="bk-empty-sub">Log a repair to expense it or capitalize it onto the asset's value.</p>
                  <button class="bk-empty-btn" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''" @click="openAdd"><span v-html="icon('plus',13)"></span> New Repair</button>
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
      <div v-else-if="!sorted.length" style="text-align:center;padding:40px;color:#868E96">No repairs found</div>
      <div v-else v-for="row in paged" :key="row.name" class="ii-mob-card" @click="openView(row)">
        <div class="ii-mob-card-main">
          <div class="ii-mob-card-top">
            <span class="inv-link">{{ row.name }}</span>
            <span class="inv-status-badge" :class="statusClass(row)">{{ statusLabel(row) }}</span>
          </div>
          <div style="font-size:12px;color:#6b7280;margin-top:4px">{{ row.asset_name || row.asset }} • {{ row.is_capitalized ? 'Capitalized' : 'Expensed' }}</div>
          <div style="display:flex;justify-content:space-between;margin-top:6px;font-size:13px">
            <span class="mono-sm">{{ INR(row.repair_cost) }}</span>
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
            <div class="inv-dh-title">{{ isNew ? 'New Asset Repair' : repair.name }}</div>
            <span v-if="isNew" class="add-status-badge">Draft</span>
            <span v-else class="inv-status-badge" :class="statusClass(repair)">{{ statusLabel(repair) }}</span>
          </div>
          <button class="inv-dclose" @click="closeDrawer" title="Close"><span v-html="icon('x',16)"></span></button>
        </div>

        <div class="inv-dbody">
          <template v-if="detailLoading">
            <div class="shimmer" style="height:200px;border-radius:10px"></div>
          </template>
          <template v-else>

            <div v-if="repair.docstatus===1" class="ar-notice" :class="{'ar-notice-cap': repair.is_capitalized}">
              <span v-html="icon(repair.is_capitalized ? 'trend' : 'info',14)"></span>
              <span v-if="repair.is_capitalized">
                Submitted — {{ INR(repair.repair_cost) }} capitalized onto Asset {{ repair.asset }}'s purchase cost and
                current value. Depreciation schedule was not regenerated (see notes).
              </span>
              <span v-else>
                Submitted — {{ INR(repair.repair_cost) }} posted as a period expense. No change to the asset's value.
              </span>
            </div>

            <!-- Repair details -->
            <div class="add-card">
              <div class="add-card-header" @click="collapsed.details = !collapsed.details">
                <div class="add-card-title">
                  <span class="add-card-title-icon"><span v-html="icon('gear',16)"></span></span>
                  Repair Details
                </div>
                <span class="add-card-chevron" :class="{collapsed:collapsed.details}"><span v-html="icon('chevD',14)"></span></span>
              </div>
              <div class="add-card-body" :class="{collapsed:collapsed.details}">
                <div class="inv-fg inv-fg2">
                  <div>
                    <label class="inv-lbl">Asset <span class="inv-req">*</span></label>
                    <SearchableSelect
                      v-model="repair.asset"
                      :options="assetOptions"
                      placeholder="Select asset being repaired"
                      :disabled="!readOnlyEditable"
                      @update:modelValue="onPickAsset"
                      @search="fetchAssets"
                    />
                  </div>
                  <div>
                    <label class="inv-lbl">Repair Date <span class="inv-req">*</span></label>
                    <input v-model="repair.repair_date" type="date" class="inv-fi" :disabled="!readOnlyEditable"/>
                  </div>
                  <div>
                    <label class="inv-lbl">Repair Cost <span class="inv-req">*</span></label>
                    <input v-model.number="repair.repair_cost" type="number" step="0.01" class="inv-fi" placeholder="0.00" :disabled="!readOnlyEditable"/>
                  </div>
                  <div>
                    <label class="inv-lbl">Company</label>
                    <input :value="repair.company" class="inv-fi" disabled/>
                  </div>
                  <div style="grid-column:1 / -1">
                    <label class="inv-lbl">Description <span class="inv-req">*</span></label>
                    <textarea v-model="repair.description" class="inv-fi" rows="2" placeholder="What was repaired and why" :disabled="!readOnlyEditable"></textarea>
                  </div>
                </div>

                <div v-if="selectedAsset" class="ar-preview-box">
                  <div class="ar-preview-row"><span>Purchase Cost</span><span class="mono-sm">{{ INR(selectedAsset.purchase_cost) }}</span></div>
                  <div class="ar-preview-row"><span>Current Value</span><span class="mono-sm">{{ INR(selectedAsset.current_value) }}</span></div>
                  <div v-if="repair.is_capitalized" class="ar-preview-row">
                    <span>New Purchase Cost / Current Value (after repair)</span>
                    <span class="mono-sm fw-600" style="color:#4338ca">{{ INR(flt(selectedAsset.current_value) + flt(repair.repair_cost)) }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Capitalize toggle -->
            <div class="add-card">
              <div class="add-card-header" @click="collapsed.type = !collapsed.type">
                <div class="add-card-title">
                  <span class="add-card-title-icon"><span v-html="icon('journal',16)"></span></span>
                  Accounting Treatment
                </div>
                <span class="add-card-chevron" :class="{collapsed:collapsed.type}"><span v-html="icon('chevD',14)"></span></span>
              </div>
              <div class="add-card-body" :class="{collapsed:collapsed.type}">
                <label class="ar-cap-toggle" :class="{disabled: !readOnlyEditable}">
                  <input type="checkbox" v-model="repair.is_capitalized" :disabled="!readOnlyEditable"/>
                  <span>
                    <strong>Capitalize to Asset Value</strong>
                    <span class="ar-cap-sub">Extends useful life / capacity — adds the repair cost onto the asset's purchase cost instead of expensing it.</span>
                  </span>
                </label>

                <div class="inv-fg inv-fg2" style="margin-top:14px">
                  <div v-if="!repair.is_capitalized">
                    <label class="inv-lbl">Expense Account <span class="inv-req">*</span></label>
                    <SearchableSelect
                      v-model="repair.expense_account"
                      :options="expenseAccountOptions"
                      placeholder="Repair & maintenance expense account"
                      :disabled="!readOnlyEditable"
                      @search="fetchExpenseAccounts"
                    />
                  </div>
                  <div>
                    <label class="inv-lbl">Credit Account (Payable / Bank / Cash) <span class="inv-req">*</span></label>
                    <SearchableSelect
                      v-model="repair.credit_account"
                      :options="creditAccountOptions"
                      placeholder="Account credited for the repair"
                      :disabled="!readOnlyEditable"
                      @search="fetchCreditAccounts"
                    />
                  </div>
                </div>

                <p v-if="repair.is_capitalized" class="ar-hint">
                  Debits the Fixed Asset Account configured on the asset's category for this company. If none is
                  configured, submit will fail — add one under Asset Category → Accounting, or uncheck this to expense instead.
                </p>
              </div>
            </div>

            <!-- Posted snapshot (submitted only) -->
            <div v-if="repair.docstatus===1" class="add-card">
              <div class="add-card-header" @click="collapsed.snapshot = !collapsed.snapshot">
                <div class="add-card-title">
                  <span class="add-card-title-icon"><span v-html="icon('check',16)"></span></span>
                  Posted Snapshot
                </div>
                <span class="add-card-chevron" :class="{collapsed:collapsed.snapshot}"><span v-html="icon('chevD',14)"></span></span>
              </div>
              <div class="add-card-body" :class="{collapsed:collapsed.snapshot}">
                <div class="ar-preview-box">
                  <div class="ar-preview-row"><span>Repair Cost</span><span class="mono-sm">{{ INR(repair.repair_cost) }}</span></div>
                  <div class="ar-preview-row"><span>GL Posted</span><span class="mono-sm">{{ repair.gl_posted ? 'Yes' : 'No' }}</span></div>
                  <div class="ar-preview-row"><span>Capitalized Amount Applied</span><span class="mono-sm">{{ repair.capitalized_amount_applied ? 'Yes' : 'No' }}</span></div>
                </div>
              </div>
            </div>

          </template>
        </div>

        <!-- Footer -->
        <div class="inv-dfooter">
          <template v-if="readOnlyEditable">
            <button class="add-btn-cancel" @click="closeDrawer">Cancel</button>
            <button class="add-btn-draft" :disabled="saving || !(isNew ? $canCreate('inventory') : $canEdit('inventory'))" @click="save('Draft')">
              <span v-html="icon('save',13)"></span> Save Draft
            </button>
            <button class="add-btn-more" :disabled="saving || !(isNew ? $canCreate('inventory') : $canEdit('inventory'))" @click="save('Submitted')">
              <span v-html="icon('check',13)"></span> {{ saving ? 'Saving…' : 'Save & Submit' }}
            </button>
          </template>
          <template v-else-if="repair.docstatus===1">
            <div class="add-footer-status">{{ repair.name }} — submitted, GL {{ repair.gl_posted ? 'posted' : 'not posted' }}</div>
            <button class="add-btn-cancel" style="color:#dc2626" :disabled="cancelling || !$canDelete('inventory')" :title="!$canDelete('inventory') ? 'Not permitted' : ''" @click="cancelRepair">
              <span v-html="icon('cancel',13)"></span> {{ cancelling ? 'Cancelling…' : 'Cancel Repair' }}
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

function flt(n) { const x = Number(n); return isNaN(x) ? 0 : x; }
function INR(n) {
  if (n == null || isNaN(n)) return '₹0.00';
  return '₹' + Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
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
const page = ref(1);
const pageSize = ref(20);

const FILTERS = [
  { key: '', label: 'All' },
  { key: 'draft', label: 'Draft' },
  { key: 'submitted', label: 'Submitted' },
  { key: 'cancelled', label: 'Cancelled' },
];

const counts = computed(() => ({
  draft: list.value.filter(i => i.docstatus === 0).length,
  submitted: list.value.filter(i => i.docstatus === 1).length,
  cancelled: list.value.filter(i => i.docstatus === 2).length,
}));

const totalCapitalized = computed(() =>
  list.value.filter(r => r.docstatus === 1 && r.is_capitalized).reduce((s, r) => s + flt(r.repair_cost), 0)
);
const totalExpensed = computed(() =>
  list.value.filter(r => r.docstatus === 1 && !r.is_capitalized).reduce((s, r) => s + flt(r.repair_cost), 0)
);

async function loadList() {
  loading.value = true;
  try {
    const fields = [
      'name', 'asset', 'company', 'repair_date', 'description', 'repair_cost',
      'is_capitalized', 'expense_account', 'credit_account',
      'gl_posted', 'capitalized_amount_applied', 'docstatus', 'modified',
    ];
    list.value = await apiList('Asset Repair', { fields, limit: 1000, order: 'repair_date desc' }) || [];
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
    toast.error('Failed to load repairs: ' + e.message);
    list.value = [];
  }
  loading.value = false;
}

const sorted = computed(() => {
  let r = list.value;
  if (filterStatus.value === 'draft') r = r.filter(i => i.docstatus === 0);
  else if (filterStatus.value === 'submitted') r = r.filter(i => i.docstatus === 1);
  else if (filterStatus.value === 'cancelled') r = r.filter(i => i.docstatus === 2);
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
watch([search, filterStatus], () => { page.value = 1; });

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

// ── DRAWER STATE ─────────────────────────────────────────────
const drawerOpen = ref(false);
const currentName = ref(null);
const isNew = computed(() => currentName.value === null);
const detailLoading = ref(false);
const saving = ref(false);
const cancelling = ref(false);
const readOnlyEditable = computed(() => isNew.value || repair.value.docstatus === 0);

const collapsed = reactive({ details: false, type: false, snapshot: false });

function emptyRepair() {
  return {
    doctype: 'Asset Repair',
    asset: '',
    company: window.__booksCompany || '',
    repair_date: todayLocal(),
    description: '',
    repair_cost: 0,
    is_capitalized: 0,
    expense_account: '',
    credit_account: '',
    docstatus: 0,
  };
}
const repair = ref(emptyRepair());

// ── Asset lookup / preview ──────────────────────────────────
const assetOptions = ref([]);
const assetInfoMap = ref({});
const selectedAsset = computed(() => assetInfoMap.value[repair.value.asset] || null);

let assetSearchTimer = null;
function fetchAssets(q = '') {
  clearTimeout(assetSearchTimer);
  assetSearchTimer = setTimeout(async () => {
    try {
      const filters = [['docstatus', '=', 1], ['status', 'not in', ['Scrapped', 'Sold']]];
      if (q) filters.push(['asset_name', 'like', `%${q}%`]);
      const rows = await apiList('Asset', {
        fields: ['name', 'asset_name', 'asset_category', 'company', 'status', 'current_value', 'purchase_cost'],
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
  repair.value.company = info.company || repair.value.company;
}

// ── Accounts ─────────────────────────────────────────────────
const expenseAccounts = ref([]);
const expenseAccountOptions = computed(() => expenseAccounts.value.map(a => ({ value: a.name, label: a.account_name || a.name })));
async function fetchExpenseAccounts(q = '') {
  try {
    // This app's Account doctype has no root_type column -- filter by
    // account_type directly (same fix as AssetValueAdjustment.vue).
    const filters = [['is_group', '=', 0], ['disabled', '=', 0], ['account_type', '=', 'Expense']];
    if (q) filters.push(['name', 'like', `%${q}%`]);
    expenseAccounts.value = await apiList('Account', { fields: ['name', 'account_name'], filters, limit: 30, order: 'name asc' });
  } catch (e) {
    expenseAccounts.value = [];
  }
}

const creditAccounts = ref([]);
const creditAccountOptions = computed(() => creditAccounts.value.map(a => ({ value: a.name, label: a.account_name || a.name })));
async function fetchCreditAccounts(q = '') {
  try {
    const filters = [['is_group', '=', 0], ['disabled', '=', 0], ['account_type', 'in', ['Payable', 'Bank', 'Cash']]];
    if (q) filters.push(['name', 'like', `%${q}%`]);
    creditAccounts.value = await apiList('Account', { fields: ['name', 'account_name'], filters, limit: 30, order: 'name asc' });
  } catch (e) {
    creditAccounts.value = [];
  }
}

watch(() => repair.value.is_capitalized, (cap) => {
  if (cap) repair.value.expense_account = '';
});

// ── Open / close / load ─────────────────────────────────────
function openAdd() {
  currentName.value = null;
  repair.value = emptyRepair();
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
    const doc = await apiGet('Asset Repair', name);
    repair.value = doc;
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
  if (!repair.value.asset) { toast.error('Select an asset to repair.'); return false; }
  if (!repair.value.repair_date) { toast.error('Repair Date is required.'); return false; }
  if (!repair.value.description) { toast.error('Description is required.'); return false; }
  if (!flt(repair.value.repair_cost) || flt(repair.value.repair_cost) <= 0) { toast.error('Repair Cost must be greater than zero.'); return false; }
  if (!repair.value.credit_account) { toast.error('Credit Account is required.'); return false; }
  if (!repair.value.is_capitalized && !repair.value.expense_account) { toast.error('Expense Account is required when the repair is not capitalized.'); return false; }
  return true;
}

async function save(targetStatus) {
  if (!validate()) return;
  saving.value = true;
  try {
    const doc = { ...repair.value };
    if (isNew.value) delete doc.name;
    if (!doc.company) doc.company = window.__booksCompany || '';
    const saved = await apiSave(doc);
    const savedName = saved?.name || doc.name;
    currentName.value = savedName;
    repair.value = saved;

    if (targetStatus === 'Submitted' && saved?.docstatus !== 1) {
      try {
        await apiSubmit('Asset Repair', savedName);
        await loadDetail(savedName);
        toast.success('Repair submitted.');
      } catch (subErr) {
        toast.error('Saved as draft — submit failed: ' + (subErr.message || subErr));
        loadList();
        return;
      }
    } else {
      toast.success(isNew.value ? 'Repair saved' : 'Repair updated');
    }
    loadList();
  } catch (e) {
    toast.error('Failed to save repair: ' + e.message);
  } finally {
    saving.value = false;
  }
}

async function cancelRepair() {
  const ok = await confirm({
    title: 'Cancel Repair',
    body: `Cancel ${repair.value.name}? This reverses the GL entries and, if capitalized, undoes the value added to the asset.`,
    okLabel: 'Cancel Repair',
    okStyle: 'danger',
  });
  if (!ok) return;
  cancelling.value = true;
  try {
    await apiCancel('Asset Repair', repair.value.name);
    toast.success('Repair cancelled.');
    await loadDetail(repair.value.name);
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
  fetchExpenseAccounts();
  fetchCreditAccounts();
});
</script>

<style scoped>
.asset-code { margin-top: 3px; color: #9ca3af; font-size: 11px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
.assets-mobile-cards { display: none; }
.text-muted { color: #9ca3af; }
.mono-sm { font-size: 13px; }
.fw-600 { font-weight: 600; }
.ta-r { text-align: right; }
.ar-type-badge { padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; white-space: nowrap; }
.ar-type-cap { background: #eef2ff; color: #4338ca; }
.ar-type-exp { background: #fef3c7; color: #92400e; }
.ar-notice {
  background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 8px;
  padding: 10px 14px; margin-bottom: 18px; font-size: 13px; color: #475569;
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.ar-notice-cap { background: #eef2ff; border-color: rgba(67,56,202,.2); color: #4338ca; }
.ar-preview-box {
  margin-top: 14px; padding: 12px 14px; background: #f8f9fc; border: 1px solid #e2e8f0;
  border-radius: 8px; display: flex; flex-direction: column; gap: 6px;
}
.ar-preview-row { display: flex; justify-content: space-between; font-size: 12.5px; color: #475569; gap: 12px; }
.ar-cap-toggle {
  display: flex; align-items: flex-start; gap: 10px; cursor: pointer;
  padding: 10px 12px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fafbfc;
}
.ar-cap-toggle.disabled { cursor: not-allowed; opacity: .7; }
.ar-cap-toggle input { margin-top: 3px; width: 15px; height: 15px; accent-color: #1a6ef7; flex-shrink: 0; }
.ar-cap-toggle span { display: flex; flex-direction: column; gap: 3px; font-size: 13.5px; color: #111827; }
.ar-cap-sub { font-size: 12px; color: #6b7280; font-weight: 400; }
.ar-hint { margin: 12px 0 0; font-size: 12px; color: #94a3b8; line-height: 1.5; }
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