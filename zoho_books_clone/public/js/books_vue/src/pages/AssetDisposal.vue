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
      <button class="sales-btn-primary" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''" @click="openAdd"><span v-html="icon('plus',13)"></span> New Disposal</button>
    </div>
  </div>

  <div class="bk-kpi-grid">
    <div class="bk-kpi-card bk-kpi-accent clickable" @click="filterStatus=''">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#dbeafe"><span v-html="icon('file',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Total Disposals</div>
          <div class="bk-kpi-value">{{ list.length }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">scrap + sale</div>
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
        <div class="bk-kpi-icon" style="background:#dcfce7;color:#16a34a"><span v-html="icon('trend',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Total Gain</div>
          <div class="bk-kpi-value bk-kpi-green">{{ INR(totalGain) }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">sale &gt; net book value</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card bk-kpi-danger clickable" @click="filterStatus=''">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#fee2e2"><span v-html="icon('trend',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Total Loss</div>
          <div class="bk-kpi-value bk-kpi-red">{{ INR(totalLoss) }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">scrap + sale below NBV</div>
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
        <th class="ta-r">NET BOOK VALUE</th>
        <th class="ta-r">GAIN / (LOSS)</th>
        <th>STATUS</th>
        <th style="width:90px;text-align:center">ACTIONS</th>
      </tr></thead>
      <tbody>
        <template v-if="loading">
          <tr v-for="n in 6" :key="n" class="shimmer-row">
            <td><div class="shimmer" style="width:80px"></div></td>
            <td><div class="shimmer" style="width:110px"></div></td>
            <td><div class="shimmer" style="width:140px"></div></td>
            <td><div class="shimmer" style="width:60px"></div></td>
            <td><div class="shimmer" style="width:80px;margin-left:auto"></div></td>
            <td><div class="shimmer" style="width:80px;margin-left:auto"></div></td>
            <td><div class="shimmer" style="width:70px"></div></td>
            <td></td>
          </tr>
        </template>
        <template v-else>
          <tr v-for="row in paged" :key="row.name" class="inv-row" @click="openView(row)">
            <td class="text-muted mono-sm">{{ row.disposal_date }}</td>
            <td><span class="inv-link">{{ row.name }}</span></td>
            <td>{{ row.asset_name || row.asset }}<div class="asset-code">{{ row.asset }}</div></td>
            <td><span class="ad-type-badge" :class="row.disposal_type==='Sale' ? 'ad-type-sale' : 'ad-type-scrap'">{{ row.disposal_type }}</span></td>
            <td class="ta-r mono-sm">{{ INR(row.net_book_value_snapshot) }}</td>
            <td class="ta-r mono-sm" :class="flt(row.gain_loss_amount) >= 0 ? 'ad-gain' : 'ad-loss'">
              {{ flt(row.gain_loss_amount) >= 0 ? '+' : '' }}{{ INR(row.gain_loss_amount) }}
            </td>
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
                  <p class="bk-empty-title">No disposals match your filters</p>
                </template>
                <template v-else>
                  <p class="bk-empty-title">No asset disposals yet</p>
                  <p class="bk-empty-sub">Scrap or sell an asset to retire it from the register.</p>
                  <button class="bk-empty-btn" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''" @click="openAdd"><span v-html="icon('plus',13)"></span> New Disposal</button>
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
      <div v-else-if="!sorted.length" style="text-align:center;padding:40px;color:#868E96">No disposals found</div>
      <div v-else v-for="row in paged" :key="row.name" class="ii-mob-card" @click="openView(row)">
        <div class="ii-mob-card-main">
          <div class="ii-mob-card-top">
            <span class="inv-link">{{ row.name }}</span>
            <span class="inv-status-badge" :class="statusClass(row)">{{ statusLabel(row) }}</span>
          </div>
          <div style="font-size:12px;color:#6b7280;margin-top:4px">{{ row.asset_name || row.asset }} • {{ row.disposal_type }}</div>
          <div style="display:flex;justify-content:space-between;margin-top:6px;font-size:13px">
            <span class="mono-sm">{{ INR(row.net_book_value_snapshot) }}</span>
            <span class="mono-sm" :class="flt(row.gain_loss_amount) >= 0 ? 'ad-gain' : 'ad-loss'">{{ INR(row.gain_loss_amount) }}</span>
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
            <div class="inv-dh-title">{{ isNew ? 'New Asset Disposal' : disposal.name }}</div>
            <span v-if="isNew" class="add-status-badge">Draft</span>
            <span v-else class="inv-status-badge" :class="statusClass(disposal)">{{ statusLabel(disposal) }}</span>
          </div>
          <button class="inv-dclose" @click="closeDrawer" title="Close"><span v-html="icon('x',16)"></span></button>
        </div>

        <div class="inv-dbody">
          <template v-if="detailLoading">
            <div class="shimmer" style="height:200px;border-radius:10px"></div>
          </template>
          <template v-else>

            <div v-if="disposal.docstatus===1" class="ad-notice" :class="{'ad-notice-muted': !disposal.gl_posted}">
              <span v-html="icon(disposal.gl_posted ? 'check' : 'info',14)"></span>
              <span v-if="disposal.gl_posted">
                Submitted — {{ disposal.disposal_type }} posted. Asset {{ disposal.asset }} is now
                {{ disposal.disposal_type === 'Sale' ? 'Sold' : 'Scrapped' }}.
              </span>
              <span v-else>
                Submitted — no GL entries were posted (the underlying asset is an Existing Asset with no
                capitalization entry in this app). Only the asset's status was updated.
              </span>
            </div>

            <!-- Disposal details -->
            <div class="add-card">
              <div class="add-card-header" @click="collapsed.details = !collapsed.details">
                <div class="add-card-title">
                  <span class="add-card-title-icon"><span v-html="icon('trash',16)"></span></span>
                  Disposal Details
                </div>
                <span class="add-card-chevron" :class="{collapsed:collapsed.details}"><span v-html="icon('chevD',14)"></span></span>
              </div>
              <div class="add-card-body" :class="{collapsed:collapsed.details}">
                <div class="inv-fg inv-fg2">
                  <div>
                    <label class="inv-lbl">Asset <span class="inv-req">*</span></label>
                    <SearchableSelect
                      v-model="disposal.asset"
                      :options="assetOptions"
                      placeholder="Select asset to dispose"
                      :disabled="!readOnlyEditable"
                      @update:modelValue="onPickAsset"
                      @search="fetchAssets"
                    />
                  </div>
                  <div>
                    <label class="inv-lbl">Disposal Type <span class="inv-req">*</span></label>
                    <select v-model="disposal.disposal_type" class="inv-fi" :disabled="!readOnlyEditable">
                      <option value="Scrap">Scrap (no proceeds)</option>
                      <option value="Sale">Sale</option>
                    </select>
                  </div>
                  <div>
                    <label class="inv-lbl">Disposal Date <span class="inv-req">*</span></label>
                    <input v-model="disposal.disposal_date" type="date" class="inv-fi" :disabled="!readOnlyEditable"/>
                  </div>
                  <div>
                    <label class="inv-lbl">Company</label>
                    <input :value="disposal.company" class="inv-fi" disabled/>
                  </div>
                </div>

                <div v-if="selectedAsset" class="ad-preview-box">
                  <div class="ad-preview-row"><span>Purchase Cost</span><span class="mono-sm">{{ INR(selectedAsset.purchase_cost) }}</span></div>
                  <div class="ad-preview-row"><span>Accumulated Depreciation</span><span class="mono-sm">{{ INR(flt(selectedAsset.purchase_cost) - flt(selectedAsset.current_value)) }}</span></div>
                  <div class="ad-preview-row"><span>Net Book Value</span><span class="mono-sm fw-600">{{ INR(selectedAsset.current_value) }}</span></div>
                  <div v-if="disposal.disposal_type==='Sale'" class="ad-preview-row">
                    <span>Estimated Gain / (Loss)</span>
                    <span class="mono-sm fw-600" :class="estimatedGainLoss >= 0 ? 'ad-gain' : 'ad-loss'">{{ INR(estimatedGainLoss) }}</span>
                  </div>
                  <div v-else class="ad-preview-row">
                    <span>Estimated Loss (full NBV)</span>
                    <span class="mono-sm fw-600 ad-loss">{{ INR(-flt(selectedAsset.current_value)) }}</span>
                  </div>
                  <div v-if="selectedAsset.is_existing_asset" style="font-size:11px;color:#94a3b8;margin-top:6px">
                    Existing Asset — no capitalization entry exists for it, so no GL entries will be posted on submit; only the asset's status will change.
                  </div>
                </div>
              </div>
            </div>

            <!-- Sale details -->
            <div v-if="disposal.disposal_type==='Sale'" class="add-card">
              <div class="add-card-header" @click="collapsed.sale = !collapsed.sale">
                <div class="add-card-title">
                  <span class="add-card-title-icon"><span v-html="icon('rupee',16)"></span></span>
                  Sale Details
                </div>
                <span class="add-card-chevron" :class="{collapsed:collapsed.sale}"><span v-html="icon('chevD',14)"></span></span>
              </div>
              <div class="add-card-body" :class="{collapsed:collapsed.sale}">
                <div class="inv-fg inv-fg2">
                  <div>
                    <label class="inv-lbl">Sale Amount <span class="inv-req">*</span></label>
                    <input v-model.number="disposal.sale_amount" type="number" step="0.01" class="inv-fi" placeholder="0.00" :disabled="!readOnlyEditable"/>
                  </div>
                  <div>
                    <label class="inv-lbl">Receivable Account <span class="inv-req">*</span></label>
                    <SearchableSelect
                      v-model="disposal.receivable_account"
                      :options="receivableAccountOptions"
                      placeholder="Account debited for sale proceeds"
                      :disabled="!readOnlyEditable"
                      @search="fetchReceivableAccounts"
                    />
                  </div>
                </div>
              </div>
            </div>

            <!-- GL accounts -->
            <div class="add-card">
              <div class="add-card-header" @click="collapsed.gl = !collapsed.gl">
                <div class="add-card-title">
                  <span class="add-card-title-icon"><span v-html="icon('journal',16)"></span></span>
                  GL Accounts
                </div>
                <span class="add-card-chevron" :class="{collapsed:collapsed.gl}"><span v-html="icon('chevD',14)"></span></span>
              </div>
              <div class="add-card-body" :class="{collapsed:collapsed.gl}">
                <div class="inv-fg inv-fg2">
                  <div>
                    <label class="inv-lbl">Gain / Loss on Disposal Account <span class="inv-req">*</span></label>
                    <SearchableSelect
                      v-model="disposal.gain_loss_account"
                      :options="gainLossAccountOptions"
                      placeholder="Account for gain/loss on disposal"
                      :disabled="!readOnlyEditable"
                      @search="fetchGainLossAccounts"
                    />
                  </div>
                </div>
                <div style="margin-top:14px">
                  <label class="inv-lbl">Remarks</label>
                  <textarea v-model="disposal.remarks" class="inv-fi" rows="2" placeholder="Optional notes" :disabled="!readOnlyEditable"></textarea>
                </div>
              </div>
            </div>

            <!-- Posted snapshot (submitted only) -->
            <div v-if="disposal.docstatus===1" class="add-card">
              <div class="add-card-header" @click="collapsed.snapshot = !collapsed.snapshot">
                <div class="add-card-title">
                  <span class="add-card-title-icon"><span v-html="icon('check',16)"></span></span>
                  Posted Snapshot
                </div>
                <span class="add-card-chevron" :class="{collapsed:collapsed.snapshot}"><span v-html="icon('chevD',14)"></span></span>
              </div>
              <div class="add-card-body" :class="{collapsed:collapsed.snapshot}">
                <div class="ad-preview-box">
                  <div class="ad-preview-row"><span>Purchase Cost</span><span class="mono-sm">{{ INR(disposal.purchase_cost_snapshot) }}</span></div>
                  <div class="ad-preview-row"><span>Accumulated Depreciation</span><span class="mono-sm">{{ INR(disposal.accumulated_depreciation_snapshot) }}</span></div>
                  <div class="ad-preview-row"><span>Net Book Value</span><span class="mono-sm">{{ INR(disposal.net_book_value_snapshot) }}</span></div>
                  <div class="ad-preview-row"><span>Gain / (Loss)</span><span class="mono-sm fw-600" :class="flt(disposal.gain_loss_amount) >= 0 ? 'ad-gain' : 'ad-loss'">{{ INR(disposal.gain_loss_amount) }}</span></div>
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
          <template v-else-if="disposal.docstatus===1">
            <div class="add-footer-status">{{ disposal.name }} — submitted, GL {{ disposal.gl_posted ? 'posted' : 'not applicable' }}</div>
            <button class="add-btn-cancel" style="color:#dc2626" :disabled="cancelling || !$canDelete('inventory')" :title="!$canDelete('inventory') ? 'Not permitted' : ''" @click="cancelDisposal">
              <span v-html="icon('cancel',13)"></span> {{ cancelling ? 'Cancelling…' : 'Cancel Disposal' }}
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
import { useRoute, useRouter } from 'vue-router';
import { apiGet, apiList, apiSave, apiSubmit, apiCancel } from '@/api/client.js';
import { useToast } from '@/composables/useToast.js';
import { useConfirm } from '@/composables/useConfirm.js';
import { icon } from '@/utils/icons.js';
import SearchableSelect from '@/components/SearchableSelect.vue';
import Pagination from '@/components/Pagination.vue';

const route = useRoute();
const router = useRouter();
const toast = useToast();
const { confirm } = useConfirm();

function flt(n) { const x = Number(n); return isNaN(x) ? 0 : x; }
function INR(n) {
  if (n == null || isNaN(n)) return 'OMR 0.00';
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

const totalGain = computed(() =>
  list.value.filter(r => r.docstatus === 1 && flt(r.gain_loss_amount) > 0)
             .reduce((s, r) => s + flt(r.gain_loss_amount), 0)
);
const totalLoss = computed(() =>
  -list.value.filter(r => r.docstatus === 1 && flt(r.gain_loss_amount) < 0)
              .reduce((s, r) => s + flt(r.gain_loss_amount), 0)
);

async function loadList() {
  loading.value = true;
  try {
    const fields = [
      'name', 'asset', 'company', 'disposal_type', 'disposal_date',
      'purchase_cost_snapshot', 'accumulated_depreciation_snapshot',
      'net_book_value_snapshot', 'sale_amount', 'gain_loss_amount',
      'gl_posted', 'docstatus', 'modified',
    ];
    list.value = await apiList('Asset Disposal', { fields, limit: 1000, order: 'disposal_date desc' }) || [];
    // asset_name isn't a field on Asset Disposal itself -- resolve in bulk.
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
    toast.error('Failed to load disposals: ' + e.message);
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
// Editable while it's a fresh unsaved doc, or an already-saved Draft (docstatus 0).
const readOnlyEditable = computed(() => isNew.value || disposal.value.docstatus === 0);

const collapsed = reactive({ details: false, sale: false, gl: false, snapshot: false });

function emptyDisposal() {
  return {
    doctype: 'Asset Disposal',
    asset: '',
    company: window.__booksCompany || '',
    disposal_type: 'Scrap',
    disposal_date: todayLocal(),
    sale_amount: 0,
    receivable_account: '',
    gain_loss_account: '',
    remarks: '',
    docstatus: 0,
  };
}
const disposal = ref(emptyDisposal());

// ── Asset lookup / preview ──────────────────────────────────
const assetOptions = ref([]);
const assetInfoMap = ref({}); // name -> full row, used for the preview panel
const selectedAsset = computed(() => assetInfoMap.value[disposal.value.asset] || null);

const estimatedGainLoss = computed(() => {
  if (!selectedAsset.value) return 0;
  return flt(disposal.value.sale_amount) - flt(selectedAsset.value.current_value);
});

let assetSearchTimer = null;
function fetchAssets(q = '') {
  clearTimeout(assetSearchTimer);
  assetSearchTimer = setTimeout(async () => {
    try {
      const filters = [['docstatus', '=', 1], ['status', 'not in', ['Scrapped', 'Sold']]];
      if (q) filters.push(['asset_name', 'like', `%${q}%`]);
      const rows = await apiList('Asset', {
        fields: ['name', 'asset_name', 'asset_category', 'company', 'status', 'current_value', 'purchase_cost', 'is_existing_asset'],
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
  disposal.value.company = info.company || disposal.value.company;
}

// ── Accounts ─────────────────────────────────────────────────
const receivableAccounts = ref([]);
const receivableAccountOptions = computed(() => receivableAccounts.value.map(a => ({ value: a.name, label: a.account_name || a.name })));
async function fetchReceivableAccounts(q = '') {
  try {
    const filters = [['is_group', '=', 0], ['disabled', '=', 0], ['account_type', 'in', ['Receivable', 'Bank', 'Cash']]];
    if (q) filters.push(['name', 'like', `%${q}%`]);
    receivableAccounts.value = await apiList('Account', { fields: ['name', 'account_name'], filters, limit: 30, order: 'name asc' });
  } catch (e) {
    receivableAccounts.value = [];
  }
}

const gainLossAccounts = ref([]);
const gainLossAccountOptions = computed(() => gainLossAccounts.value.map(a => ({ value: a.name, label: a.account_name || a.name })));
async function fetchGainLossAccounts(q = '') {
  try {
    const filters = [['is_group', '=', 0], ['disabled', '=', 0]];
    if (q) filters.push(['name', 'like', `%${q}%`]);
    gainLossAccounts.value = await apiList('Account', { fields: ['name', 'account_name'], filters, limit: 30, order: 'name asc' });
  } catch (e) {
    gainLossAccounts.value = [];
  }
}

// ── Open / close / load ─────────────────────────────────────
function openAdd() {
  currentName.value = null;
  disposal.value = emptyDisposal();
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
    const doc = await apiGet('Asset Disposal', name);
    disposal.value = doc;
    if (doc.asset && !assetInfoMap.value[doc.asset]) {
      try { assetInfoMap.value[doc.asset] = await apiGet('Asset', doc.asset); } catch (e) { /* non-fatal */ }
    }
  } catch (e) {
    toast.error('Could not load ' + name + ': ' + e.message);
  }
  detailLoading.value = false;
}

// ── Save / Submit / Cancel ──────────────────────────────────
async function save(targetStatus) {
  if (!disposal.value.asset) { toast.error('Select an asset to dispose.'); return; }
  if (!disposal.value.disposal_date) { toast.error('Disposal Date is required.'); return; }
  if (!disposal.value.gain_loss_account) { toast.error('Gain / Loss on Disposal Account is required.'); return; }
  if (disposal.value.disposal_type === 'Sale' && !disposal.value.receivable_account) {
    toast.error('Receivable Account is required for a Sale disposal.'); return;
  }
  saving.value = true;
  try {
    const doc = { ...disposal.value };
    if (isNew.value) delete doc.name;
    if (!doc.company) doc.company = window.__booksCompany || '';
    const saved = await apiSave(doc);
    const savedName = saved?.name || doc.name;
    currentName.value = savedName;
    disposal.value = saved;

    if (targetStatus === 'Submitted' && saved?.docstatus !== 1) {
      try {
        await apiSubmit('Asset Disposal', savedName);
        await loadDetail(savedName);
        toast.success('Disposal submitted.');
      } catch (subErr) {
        toast.error('Saved as draft — submit failed: ' + (subErr.message || subErr));
        loadList();
        return;
      }
    } else {
      toast.success(isNew.value ? 'Disposal saved' : 'Disposal updated');
    }
    loadList();
  } catch (e) {
    toast.error('Failed to save disposal: ' + e.message);
  } finally {
    saving.value = false;
  }
}

async function cancelDisposal() {
  const ok = await confirm({
    title: 'Cancel Disposal',
    body: `Cancel ${disposal.value.name}? This reverses the GL entries (if any) and restores the asset to its previous status.`,
    okLabel: 'Cancel Disposal',
    okStyle: 'danger',
  });
  if (!ok) return;
  cancelling.value = true;
  try {
    await apiCancel('Asset Disposal', disposal.value.name);
    toast.success('Disposal cancelled.');
    await loadDetail(disposal.value.name);
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
  fetchReceivableAccounts();
  fetchGainLossAccounts();
});
</script>

<style scoped>
.asset-code { margin-top: 3px; color: #9ca3af; font-size: 11px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
.assets-mobile-cards { display: none; }
.ad-type-badge { padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; }
.ad-type-scrap { background: #fee2e2; color: #b91c1c; }
.ad-type-sale { background: #dbeafe; color: #1d4ed8; }
.ad-gain { color: #16a34a; }
.ad-loss { color: #dc2626; }
.ad-notice {
  background: #fff3bf; border: 1px solid rgba(230,119,0,.2); border-radius: 8px;
  padding: 10px 14px; margin-bottom: 18px; font-size: 13px; color: #e67700;
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.ad-notice-muted { background: #f1f5f9; border-color: #e2e8f0; color: #64748b; }
.ad-preview-box {
  margin-top: 14px; padding: 12px 14px; background: #f8f9fc; border: 1px solid #e2e8f0;
  border-radius: 8px; display: flex; flex-direction: column; gap: 6px;
}
.ad-preview-row { display: flex; justify-content: space-between; font-size: 12.5px; color: #475569; }
@media (max-width: 768px) {
  .inv-desktop-table { display: none; }
  .assets-mobile-cards { display: flex; flex-direction: column; gap: 10px; padding: 12px; }
}
</style>