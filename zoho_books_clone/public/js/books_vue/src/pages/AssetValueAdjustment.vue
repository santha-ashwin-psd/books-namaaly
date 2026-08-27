<template>
<div class="list-page">

  <!-- ── Toolbar ── -->
  <div class="sales-toolbar">
    <div class="sales-search">
      <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
      <input v-model="search" placeholder="Search by voucher#, asset…" class="sales-search-input"/>
    </div>
    <div class="sales-pills">
      <button v-for="f in TYPE_FILTERS" :key="f.key" class="sales-pill" :class="{active:filterType===f.key}" @click="filterType=f.key">
        {{ f.label }}<span v-if="f.key" class="sales-pill-count">{{ typeCounts[f.key] || 0 }}</span>
      </button>
    </div>
    <div class="sales-actions">
      <button class="sales-btn-ghost" @click="loadList" title="Refresh" :disabled="loading"><span v-html="icon('refresh',14)"></span></button>
      <button class="sales-btn-primary" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''" @click="openAdd"><span v-html="icon('plus',13)"></span> New Adjustment</button>
    </div>
  </div>

  <div class="bk-kpi-grid">
    <div class="bk-kpi-card bk-kpi-accent clickable" @click="filterStatus=''">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#dbeafe"><span v-html="icon('balance',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Total Adjustments</div>
          <div class="bk-kpi-value">{{ list.length }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">impairment + revaluation</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card bk-kpi-success clickable" @click="filterStatus='submitted'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#dcfce7"><span v-html="icon('check',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Submitted</div>
          <div class="bk-kpi-value bk-kpi-green">{{ statusCounts.submitted || 0 }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">GL posted</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card clickable" @click="filterType='Impairment (Write-down)'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#fee2e2;color:#b91c1c"><span v-html="icon('trend',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Total Impairment</div>
          <div class="bk-kpi-value" style="color:#b91c1c">{{ INR(totalImpairment) }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">write-downs</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card clickable" @click="filterType='Revaluation (Write-up)'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#dcfce7;color:#15803d"><span v-html="icon('trend',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Total Revaluation</div>
          <div class="bk-kpi-value" style="color:#15803d">{{ INR(totalRevaluation) }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">write-ups</div>
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
        <th class="ta-r">BEFORE</th>
        <th class="ta-r">AFTER</th>
        <th class="ta-r">Δ AMOUNT</th>
        <th>STATUS</th>
        <th style="width:90px;text-align:center">ACTIONS</th>
      </tr></thead>
      <tbody>
        <template v-if="loading">
          <tr v-for="n in 6" :key="n" class="shimmer-row">
            <td><div class="shimmer" style="width:80px"></div></td>
            <td><div class="shimmer" style="width:110px"></div></td>
            <td><div class="shimmer" style="width:140px"></div></td>
            <td><div class="shimmer" style="width:90px"></div></td>
            <td><div class="shimmer" style="width:70px;margin-left:auto"></div></td>
            <td><div class="shimmer" style="width:70px;margin-left:auto"></div></td>
            <td><div class="shimmer" style="width:70px;margin-left:auto"></div></td>
            <td><div class="shimmer" style="width:70px"></div></td>
            <td></td>
          </tr>
        </template>
        <template v-else>
          <tr v-for="row in paged" :key="row.name" class="inv-row" @click="openView(row)">
            <td class="text-muted mono-sm">{{ row.adjustment_date }}</td>
            <td><span class="inv-link">{{ row.name }}</span></td>
            <td>{{ row.asset_name || row.asset }}<div class="asset-code">{{ row.asset }}</div></td>
            <td><span class="ava-type-badge" :class="row.adjustment_type==='Impairment (Write-down)' ? 'ava-type-down' : 'ava-type-up'">{{ shortType(row.adjustment_type) }}</span></td>
            <td class="ta-r mono-sm text-muted">{{ INR(row.current_value_before ?? row._preview_before) }}</td>
            <td class="ta-r mono-sm">{{ INR(row.new_value) }}</td>
            <td class="ta-r mono-sm fw-600" :class="deltaClass(row)">{{ deltaDisplay(row) }}</td>
            <td><span class="inv-status-badge" :class="statusClass(row)">{{ statusLabel(row) }}</span></td>
            <td style="text-align:center" @click.stop>
              <button class="inv-act-btn" @click="openView(row)" title="View"><span v-html="icon('eye',13)"></span></button>
            </td>
          </tr>
          <tr v-if="!sorted.length">
            <td colspan="9" class="bk-empty-state">
              <div class="bk-empty-inner">
                <template v-if="search||filterStatus||filterType">
                  <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.3"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                  <p class="bk-empty-title">No adjustments match your filters</p>
                </template>
                <template v-else>
                  <p class="bk-empty-title">No value adjustments yet</p>
                  <p class="bk-empty-sub">Record an impairment or revaluation to change an asset's carrying value outside the depreciation schedule.</p>
                  <button class="bk-empty-btn" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''" @click="openAdd"><span v-html="icon('plus',13)"></span> New Adjustment</button>
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
      <div v-else-if="!sorted.length" style="text-align:center;padding:40px;color:#868E96">No adjustments found</div>
      <div v-else v-for="row in paged" :key="row.name" class="ii-mob-card" @click="openView(row)">
        <div class="ii-mob-card-main">
          <div class="ii-mob-card-top">
            <span class="inv-link">{{ row.name }}</span>
            <span class="inv-status-badge" :class="statusClass(row)">{{ statusLabel(row) }}</span>
          </div>
          <div style="font-size:12px;color:#6b7280;margin-top:4px">{{ row.asset_name || row.asset }} • {{ shortType(row.adjustment_type) }}</div>
          <div style="display:flex;justify-content:space-between;margin-top:6px;font-size:13px">
            <span class="mono-sm">{{ INR(row.new_value) }}</span>
            <span class="mono-sm fw-600" :class="deltaClass(row)">{{ deltaDisplay(row) }}</span>
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
            <div class="inv-dh-title">{{ isNew ? 'New Value Adjustment' : adj.name }}</div>
            <span v-if="isNew" class="add-status-badge">Draft</span>
            <span v-else class="inv-status-badge" :class="statusClass(adj)">{{ statusLabel(adj) }}</span>
          </div>
          <button class="inv-dclose" @click="closeDrawer" title="Close"><span v-html="icon('x',16)"></span></button>
        </div>

        <div class="inv-dbody">
          <template v-if="detailLoading">
            <div class="shimmer" style="height:200px;border-radius:10px"></div>
          </template>
          <template v-else>

            <div v-if="adj.docstatus===1" class="ava-notice" :class="{'ava-notice-down': adj.adjustment_type==='Impairment (Write-down)'}">
              <span v-html="icon('check',14)"></span>
              <span>
                Submitted — Asset {{ adj.asset }}'s current value moved from {{ INR(adj.current_value_before) }} to
                {{ INR(adj.new_value) }} ({{ adj.adjustment_amount > 0 ? '+' : '' }}{{ INR(adj.adjustment_amount) }}).
                Original purchase cost is untouched.
              </span>
            </div>

            <!-- Adjustment details -->
            <div class="add-card">
              <div class="add-card-header" @click="collapsed.details = !collapsed.details">
                <div class="add-card-title">
                  <span class="add-card-title-icon"><span v-html="icon('balance',16)"></span></span>
                  Adjustment Details
                </div>
                <span class="add-card-chevron" :class="{collapsed:collapsed.details}"><span v-html="icon('chevD',14)"></span></span>
              </div>
              <div class="add-card-body" :class="{collapsed:collapsed.details}">
                <div class="inv-fg inv-fg2">
                  <div>
                    <label class="inv-lbl">Asset <span class="inv-req">*</span></label>
                    <SearchableSelect
                      v-model="adj.asset"
                      :options="assetOptions"
                      placeholder="Select asset to adjust"
                      :disabled="!readOnlyEditable"
                      @update:modelValue="onPickAsset"
                      @search="fetchAssets"
                    />
                  </div>
                  <div>
                    <label class="inv-lbl">Adjustment Date <span class="inv-req">*</span></label>
                    <input v-model="adj.adjustment_date" type="date" class="inv-fi" :disabled="!readOnlyEditable"/>
                  </div>
                  <div>
                    <label class="inv-lbl">Adjustment Type <span class="inv-req">*</span></label>
                    <select v-model="adj.adjustment_type" class="inv-fi" disabled>
                      <option value="Impairment (Write-down)">Impairment (Write-down)</option>
                      <option value="Revaluation (Write-up)">Revaluation (Write-up)</option>
                    </select>
                  </div>
                  <div>
                    <label class="inv-lbl">Company</label>
                    <input :value="adj.company" class="inv-fi" disabled/>
                  </div>
                  <div style="grid-column:1 / -1">
                    <label class="inv-lbl">Reason <span class="inv-req">*</span></label>
                    <textarea v-model="adj.reason" class="inv-fi" rows="2" placeholder="Why the asset's value is being adjusted" :disabled="!readOnlyEditable"></textarea>
                  </div>
                </div>
                <p class="ava-hint">Adjustment Type is inferred automatically from New Value vs. Current Value below — pick New Value first.</p>
              </div>
            </div>

            <!-- Value change -->
            <div class="add-card">
              <div class="add-card-header" @click="collapsed.value = !collapsed.value">
                <div class="add-card-title">
                  <span class="add-card-title-icon"><span v-html="icon('trend',16)"></span></span>
                  Value Change
                </div>
                <span class="add-card-chevron" :class="{collapsed:collapsed.value}"><span v-html="icon('chevD',14)"></span></span>
              </div>
              <div class="add-card-body" :class="{collapsed:collapsed.value}">
                <div class="inv-fg inv-fg2">
                  <div>
                    <label class="inv-lbl">Current Value (Before)</label>
                    <input :value="INR(currentValueBefore)" class="inv-fi" disabled/>
                  </div>
                  <div>
                    <label class="inv-lbl">New Value <span class="inv-req">*</span></label>
                    <input v-model.number="adj.new_value" type="number" step="0.01" class="inv-fi" placeholder="0.00" :disabled="!readOnlyEditable"/>
                  </div>
                </div>

                <div v-if="selectedAsset" class="ava-preview-box">
                  <div class="ava-preview-row"><span>Original Purchase Cost</span><span class="mono-sm">{{ INR(selectedAsset.purchase_cost) }}</span></div>
                  <div class="ava-preview-row"><span>Current Value</span><span class="mono-sm">{{ INR(currentValueBefore) }}</span></div>
                  <div class="ava-preview-row" v-if="adj.new_value !== null && adj.new_value !== ''">
                    <span>{{ livePreviewAmount < 0 ? 'Impairment (Write-down)' : 'Revaluation (Write-up)' }}</span>
                    <span class="mono-sm fw-600" :class="livePreviewAmount < 0 ? 'ava-neg' : 'ava-pos'">
                      {{ livePreviewAmount > 0 ? '+' : '' }}{{ INR(livePreviewAmount) }}
                    </span>
                  </div>
                  <div v-if="flt(adj.new_value) > flt(selectedAsset.purchase_cost)" class="ava-warn">
                    New Value cannot exceed original Purchase Cost ({{ INR(selectedAsset.purchase_cost) }}).
                  </div>
                </div>
              </div>
            </div>

            <!-- Accounts -->
            <div class="add-card">
              <div class="add-card-header" @click="collapsed.accounts = !collapsed.accounts">
                <div class="add-card-title">
                  <span class="add-card-title-icon"><span v-html="icon('journal',16)"></span></span>
                  Accounting
                </div>
                <span class="add-card-chevron" :class="{collapsed:collapsed.accounts}"><span v-html="icon('chevD',14)"></span></span>
              </div>
              <div class="add-card-body" :class="{collapsed:collapsed.accounts}">
                <div class="inv-fg inv-fg2">
                  <div>
                    <label class="inv-lbl">{{ livePreviewAmount < 0 ? 'Impairment Loss Account' : 'Revaluation Surplus Account' }} <span class="inv-req">*</span></label>
                    <SearchableSelect
                      v-model="adj.adjustment_account"
                      :options="adjustmentAccountOptions"
                      placeholder="P&L / reserve account for the adjustment"
                      :disabled="!readOnlyEditable"
                      @search="fetchAdjustmentAccounts"
                    />
                  </div>
                </div>
                <p class="ava-hint">
                  The offsetting leg always posts to the asset category's Accumulated Depreciation Account for this
                  company — that account isn't picked here, it's resolved automatically at submit.
                </p>
              </div>
            </div>

            <!-- Posted snapshot -->
            <div v-if="adj.docstatus===1" class="add-card">
              <div class="add-card-header" @click="collapsed.snapshot = !collapsed.snapshot">
                <div class="add-card-title">
                  <span class="add-card-title-icon"><span v-html="icon('check',16)"></span></span>
                  Posted Snapshot
                </div>
                <span class="add-card-chevron" :class="{collapsed:collapsed.snapshot}"><span v-html="icon('chevD',14)"></span></span>
              </div>
              <div class="add-card-body" :class="{collapsed:collapsed.snapshot}">
                <div class="ava-preview-box">
                  <div class="ava-preview-row"><span>Current Value (Before)</span><span class="mono-sm">{{ INR(adj.current_value_before) }}</span></div>
                  <div class="ava-preview-row"><span>New Value</span><span class="mono-sm">{{ INR(adj.new_value) }}</span></div>
                  <div class="ava-preview-row"><span>Adjustment Amount</span><span class="mono-sm fw-600" :class="adj.adjustment_amount < 0 ? 'ava-neg' : 'ava-pos'">{{ adj.adjustment_amount > 0 ? '+' : '' }}{{ INR(adj.adjustment_amount) }}</span></div>
                  <div class="ava-preview-row"><span>GL Posted</span><span class="mono-sm">{{ adj.gl_posted ? 'Yes' : 'No' }}</span></div>
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
          <template v-else-if="adj.docstatus===1">
            <div class="add-footer-status">{{ adj.name }} — submitted, GL {{ adj.gl_posted ? 'posted' : 'not posted' }}</div>
            <button class="add-btn-cancel" style="color:#dc2626" :disabled="cancelling || !$canDelete('inventory')" :title="!$canDelete('inventory') ? 'Not permitted' : ''" @click="cancelAdjustment">
              <span v-html="icon('cancel',13)"></span> {{ cancelling ? 'Cancelling…' : 'Cancel Adjustment' }}
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
  if (n === null || n === undefined || n === '' || isNaN(n)) return 'OMR 0.00';
  return 'OMR ' + Number(n).toLocaleString('en-OM', { minimumFractionDigits: 3, maximumFractionDigits: 3 });
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
const filterType = ref('');
const page = ref(1);
const pageSize = ref(20);

const TYPE_FILTERS = [
  { key: '', label: 'All' },
  { key: 'Impairment (Write-down)', label: 'Impairment' },
  { key: 'Revaluation (Write-up)', label: 'Revaluation' },
];

const statusCounts = computed(() => ({
  draft: list.value.filter(i => i.docstatus === 0).length,
  submitted: list.value.filter(i => i.docstatus === 1).length,
  cancelled: list.value.filter(i => i.docstatus === 2).length,
}));

const typeCounts = computed(() => {
  const counts = {};
  for (const t of ['Impairment (Write-down)', 'Revaluation (Write-up)']) {
    counts[t] = list.value.filter(i => i.adjustment_type === t).length;
  }
  return counts;
});

const totalImpairment = computed(() =>
  list.value.filter(r => r.docstatus === 1 && r.adjustment_type === 'Impairment (Write-down)')
    .reduce((s, r) => s + Math.abs(flt(r.adjustment_amount)), 0)
);
const totalRevaluation = computed(() =>
  list.value.filter(r => r.docstatus === 1 && r.adjustment_type === 'Revaluation (Write-up)')
    .reduce((s, r) => s + Math.abs(flt(r.adjustment_amount)), 0)
);

async function loadList() {
  loading.value = true;
  try {
    const fields = [
      'name', 'asset', 'company', 'adjustment_type', 'adjustment_date', 'reason',
      'current_value_before', 'new_value', 'adjustment_amount', 'adjustment_account',
      'gl_posted', 'docstatus', 'modified',
    ];
    list.value = await apiList('Asset Value Adjustment', { fields, limit: 1000, order: 'adjustment_date desc' }) || [];
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
    toast.error('Failed to load adjustments: ' + e.message);
    list.value = [];
  }
  loading.value = false;
}

const sorted = computed(() => {
  let r = list.value;
  if (filterStatus.value === 'draft') r = r.filter(i => i.docstatus === 0);
  else if (filterStatus.value === 'submitted') r = r.filter(i => i.docstatus === 1);
  else if (filterStatus.value === 'cancelled') r = r.filter(i => i.docstatus === 2);
  if (filterType.value) r = r.filter(i => i.adjustment_type === filterType.value);
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
watch([search, filterStatus, filterType], () => { page.value = 1; });

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
function shortType(t) {
  if (t === 'Impairment (Write-down)') return 'Impairment';
  if (t === 'Revaluation (Write-up)') return 'Revaluation';
  return t || '—';
}
function deltaDisplay(row) {
  const amt = row.adjustment_amount;
  if (amt !== undefined && amt !== null && amt !== 0) {
    return (amt > 0 ? '+' : '') + INR(amt);
  }
  // Draft rows: no posted delta yet, derive a preview from new_value vs before if known.
  if (row.current_value_before != null) {
    const d = flt(row.new_value) - flt(row.current_value_before);
    return (d > 0 ? '+' : '') + INR(d);
  }
  return '—';
}
function deltaClass(row) {
  const amt = row.adjustment_amount ?? (row.current_value_before != null ? flt(row.new_value) - flt(row.current_value_before) : 0);
  return amt < 0 ? 'ava-neg' : (amt > 0 ? 'ava-pos' : '');
}

// ── DRAWER STATE ─────────────────────────────────────────────
const drawerOpen = ref(false);
const currentName = ref(null);
const isNew = computed(() => currentName.value === null);
const detailLoading = ref(false);
const saving = ref(false);
const cancelling = ref(false);
const readOnlyEditable = computed(() => isNew.value || adj.value.docstatus === 0);

const collapsed = reactive({ details: false, value: false, accounts: false, snapshot: false });

function emptyAdjustment() {
  return {
    doctype: 'Asset Value Adjustment',
    asset: '',
    company: window.__booksCompany || '',
    adjustment_type: 'Impairment (Write-down)',
    adjustment_date: todayLocal(),
    reason: '',
    new_value: null,
    adjustment_account: '',
    docstatus: 0,
  };
}
const adj = ref(emptyAdjustment());

// current_value_before is only stamped by the backend after submit; before
// that, source it live from the selected asset so the preview works while editing.
const currentValueBefore = computed(() => {
  if (adj.value.docstatus === 1 && adj.value.current_value_before != null) return adj.value.current_value_before;
  return selectedAsset.value ? flt(selectedAsset.value.current_value) : 0;
});

const livePreviewAmount = computed(() => {
  if (adj.value.new_value === null || adj.value.new_value === '') return 0;
  return flt(adj.value.new_value) - currentValueBefore.value;
});

// Keep adjustment_type in sync with the sign of the live preview while editing —
// backend enforces this at validate() too, this just avoids a round-trip error.
watch(livePreviewAmount, (amt) => {
  if (!readOnlyEditable.value) return;
  if (adj.value.new_value === null || adj.value.new_value === '') return;
  if (amt < 0) adj.value.adjustment_type = 'Impairment (Write-down)';
  else if (amt > 0) adj.value.adjustment_type = 'Revaluation (Write-up)';
});

// ── Asset lookup / preview ──────────────────────────────────
const assetOptions = ref([]);
const assetInfoMap = ref({});
const selectedAsset = computed(() => assetInfoMap.value[adj.value.asset] || null);

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
  adj.value.company = info.company || adj.value.company;
}

// ── Accounts ─────────────────────────────────────────────────
const adjustmentAccounts = ref([]);
const adjustmentAccountOptions = computed(() => adjustmentAccounts.value.map(a => ({ value: a.name, label: a.account_name || a.name })));
async function fetchAdjustmentAccounts(q = '') {
  try {
    // This app's Account doctype has no root_type column (see
    // ItemEditDrawer.vue's loadAccountLists for the same fix) -- filter by
    // account_type directly. Expense/Income/Equity are valid account_type
    // values here too, so no other change is needed.
    const filters = [['is_group', '=', 0], ['disabled', '=', 0], ['account_type', 'in', ['Expense', 'Income', 'Equity']]];
    if (q) filters.push(['name', 'like', `%${q}%`]);
    adjustmentAccounts.value = await apiList('Account', { fields: ['name', 'account_name'], filters, limit: 30, order: 'name asc' });
  } catch (e) {
    adjustmentAccounts.value = [];
  }
}

// ── Open / close / load ─────────────────────────────────────
function openAdd() {
  currentName.value = null;
  adj.value = emptyAdjustment();
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
    const doc = await apiGet('Asset Value Adjustment', name);
    adj.value = doc;
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
  if (!adj.value.asset) { toast.error('Select an asset to adjust.'); return false; }
  if (!adj.value.adjustment_date) { toast.error('Adjustment Date is required.'); return false; }
  if (!adj.value.reason) { toast.error('Reason is required.'); return false; }
  if (adj.value.new_value === null || adj.value.new_value === '' || flt(adj.value.new_value) < 0) {
    toast.error('New Value must be zero or greater.'); return false;
  }
  if (selectedAsset.value && flt(adj.value.new_value) > flt(selectedAsset.value.purchase_cost)) {
    toast.error(`New Value cannot exceed the asset's original Purchase Cost (${INR(selectedAsset.value.purchase_cost)}).`);
    return false;
  }
  if (flt(adj.value.new_value) === currentValueBefore.value) {
    toast.error('New Value is the same as the asset\'s Current Value — nothing to adjust.');
    return false;
  }
  if (!adj.value.adjustment_account) { toast.error('Impairment Loss / Revaluation Surplus Account is required.'); return false; }
  return true;
}

async function save(targetStatus) {
  if (!validate()) return;
  saving.value = true;
  try {
    const doc = { ...adj.value };
    if (isNew.value) delete doc.name;
    if (!doc.company) doc.company = window.__booksCompany || '';
    const saved = await apiSave(doc);
    const savedName = saved?.name || doc.name;
    currentName.value = savedName;
    adj.value = saved;

    if (targetStatus === 'Submitted' && saved?.docstatus !== 1) {
      try {
        await apiSubmit('Asset Value Adjustment', savedName);
        await loadDetail(savedName);
        toast.success('Adjustment submitted.');
      } catch (subErr) {
        toast.error('Saved as draft — submit failed: ' + (subErr.message || subErr));
        loadList();
        return;
      }
    } else {
      toast.success(isNew.value ? 'Adjustment saved' : 'Adjustment updated');
    }
    loadList();
  } catch (e) {
    toast.error('Failed to save adjustment: ' + e.message);
  } finally {
    saving.value = false;
  }
}

async function cancelAdjustment() {
  const ok = await confirm({
    title: 'Cancel Adjustment',
    body: `Cancel ${adj.value.name}? This reverses the GL entries and restores Asset ${adj.value.asset}'s current value to ${INR(adj.value.current_value_before)}.`,
    okLabel: 'Cancel Adjustment',
    okStyle: 'danger',
  });
  if (!ok) return;
  cancelling.value = true;
  try {
    await apiCancel('Asset Value Adjustment', adj.value.name);
    toast.success('Adjustment cancelled.');
    await loadDetail(adj.value.name);
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
  fetchAdjustmentAccounts();
});
</script>

<style scoped>
.asset-code { margin-top: 3px; color: #9ca3af; font-size: 11px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
.assets-mobile-cards { display: none; }
.text-muted { color: #9ca3af; }
.mono-sm { font-size: 13px; }
.fw-600 { font-weight: 600; }
.ta-r { text-align: right; }
.ava-pos { color: #15803d; }
.ava-neg { color: #b91c1c; }
.ava-type-badge { padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; white-space: nowrap; }
.ava-type-down { background: #fee2e2; color: #b91c1c; }
.ava-type-up { background: #dcfce7; color: #15803d; }
.ava-notice {
  background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 8px;
  padding: 10px 14px; margin-bottom: 18px; font-size: 13px; color: #475569;
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.ava-notice-down { background: #fef2f2; border-color: rgba(185,28,28,.15); color: #991b1b; }
.ava-preview-box {
  margin-top: 14px; padding: 12px 14px; background: #f8f9fc; border: 1px solid #e2e8f0;
  border-radius: 8px; display: flex; flex-direction: column; gap: 6px;
}
.ava-preview-row { display: flex; justify-content: space-between; font-size: 12.5px; color: #475569; gap: 12px; }
.ava-warn { margin-top: 6px; font-size: 12px; color: #b91c1c; font-weight: 500; }
.ava-hint { margin: 12px 0 0; font-size: 12px; color: #94a3b8; line-height: 1.5; }
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