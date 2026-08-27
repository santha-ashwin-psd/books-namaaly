<template>
<div class="list-page">

  <!-- Toolbar -->
  <div class="sales-toolbar">
    <div class="sales-search">
      <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
      <input v-model="search" placeholder="Search by voucher#, asset…" class="sales-search-input"/>
    </div>
    <div class="sales-actions">
      <button class="sales-btn-ghost" @click="loadList" title="Refresh" :disabled="loading"><span v-html="icon('refresh',14)"></span></button>
      <button class="sales-btn-primary" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''" @click="openAdd"><span v-html="icon('plus',13)"></span> New Write-off</button>
    </div>
  </div>

  <!-- Table -->
  <div class="inv-table-wrap">
    <table class="inv-table inv-desktop-table">
      <thead><tr>
        <th>DATE</th>
        <th>VOUCHER#</th>
        <th>ASSET</th>
        <th class="ta-r">QTY WRITTEN OFF</th>
        <th class="ta-r">LOSS (NBV)</th>
        <th>STATUS</th>
        <th style="width:90px;text-align:center">ACTIONS</th>
      </tr></thead>
      <tbody>
        <template v-if="loading">
          <tr v-for="n in 6" :key="n" class="shimmer-row">
            <td><div class="shimmer" style="width:80px"></div></td>
            <td><div class="shimmer" style="width:110px"></div></td>
            <td><div class="shimmer" style="width:140px"></div></td>
            <td><div class="shimmer" style="width:70px;margin-left:auto"></div></td>
            <td><div class="shimmer" style="width:70px;margin-left:auto"></div></td>
            <td><div class="shimmer" style="width:70px"></div></td>
            <td></td>
          </tr>
        </template>
        <template v-else>
          <tr v-for="row in filtered" :key="row.name" class="inv-row" @click="openView(row)">
            <td class="text-muted mono-sm">{{ row.adjustment_date }}</td>
            <td><span class="inv-link">{{ row.name }}</span></td>
            <td>{{ row.asset_name || row.asset }}<div class="asset-code">{{ row.asset }}</div></td>
            <td class="ta-r mono-sm">{{ row.damaged_qty }} <span class="text-muted">of {{ row.qty_before ?? '—' }}</span></td>
            <td class="ta-r mono-sm">{{ INR(row.write_off_net_book_value) }}</td>
            <td><span class="inv-status-badge" :class="statusClass(row)">{{ statusLabel(row) }}</span></td>
            <td style="text-align:center" @click.stop>
              <button class="inv-act-btn" @click="openView(row)" title="View"><span v-html="icon('eye',13)"></span></button>
            </td>
          </tr>
          <tr v-if="!filtered.length">
            <td colspan="7" class="bk-empty-state">
              <div class="bk-empty-inner">
                <p class="bk-empty-title">No quantity write-offs yet</p>
                <p class="bk-empty-sub">Record a partial damage/write-off when some — not all — units of a multi-unit asset are destroyed.</p>
                <button class="bk-empty-btn" :disabled="!$canCreate('inventory')" @click="openAdd"><span v-html="icon('plus',13)"></span> New Write-off</button>
              </div>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>

  <!-- Drawer -->
  <Teleport to="body">
    <div v-if="drawerOpen" class="inv-drawer-bg" @click.self="closeDrawer">
      <div class="inv-drawer-panel is-add">

        <div class="inv-dh">
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
            <div class="inv-dh-title">{{ isNew ? 'New Quantity Write-off' : doc.name }}</div>
            <span v-if="isNew" class="add-status-badge">Draft</span>
            <span v-else class="inv-status-badge" :class="statusClass(doc)">{{ statusLabel(doc) }}</span>
          </div>
          <button class="inv-dclose" @click="closeDrawer" title="Close"><span v-html="icon('x',16)"></span></button>
        </div>

        <div class="inv-dbody">
          <template v-if="detailLoading">
            <div class="shimmer" style="height:200px;border-radius:10px"></div>
          </template>
          <template v-else>

            <div v-if="doc.docstatus===1" class="aqa-notice">
              <span v-html="icon('check',14)"></span>
              <span>
                Submitted — {{ doc.damaged_qty }} of {{ doc.qty_before }} units written off Asset {{ doc.asset }}.
                Qty is now {{ doc.qty_after }}, Purchase Cost {{ INR(doc.purchase_cost_after) }}, Current Value {{ INR(doc.current_value_after) }}.
              </span>
            </div>

            <div class="add-card">
              <div class="add-card-body">
                <div class="inv-fg inv-fg2">
                  <div>
                    <label class="inv-lbl">Asset <span class="inv-req">*</span></label>
                    <SearchableSelect
                      v-model="doc.asset"
                      :options="assetOptions"
                      placeholder="Select asset"
                      :disabled="!readOnlyEditable"
                      @update:modelValue="onPickAsset"
                      @search="fetchAssets"
                    />
                  </div>
                  <div>
                    <label class="inv-lbl">Adjustment Date <span class="inv-req">*</span></label>
                    <input v-model="doc.adjustment_date" type="date" class="inv-fi" :disabled="!readOnlyEditable"/>
                  </div>
                  <div>
                    <label class="inv-lbl">Damaged / Written-off Qty <span class="inv-req">*</span></label>
                    <input v-model.number="doc.damaged_qty" type="number" step="1" min="0" class="inv-fi" placeholder="0" :disabled="!readOnlyEditable"/>
                    <div v-if="selectedAsset" style="font-size:11px;color:#94a3b8;margin-top:4px">
                      Current Qty on Asset: {{ selectedAsset.qty }}. Must be less than this — use Asset Disposal if all units are gone.
                    </div>
                  </div>
                  <div>
                    <label class="inv-lbl">Loss on Damaged Assets Account <span class="inv-req">*</span></label>
                    <SearchableSelect
                      v-model="doc.loss_account"
                      :options="lossAccountOptions"
                      placeholder="P&L expense account"
                      :disabled="!readOnlyEditable"
                      @search="fetchLossAccounts"
                    />
                  </div>
                  <div style="grid-column:1 / -1">
                    <label class="inv-lbl">Reason <span class="inv-req">*</span></label>
                    <textarea v-model="doc.reason" class="inv-fi" rows="2" placeholder="e.g. 10 of 20 units damaged in warehouse flooding" :disabled="!readOnlyEditable"></textarea>
                  </div>
                </div>

                <div v-if="selectedAsset && doc.damaged_qty" class="aqa-preview-box">
                  <div class="aqa-preview-row"><span>Remaining Qty</span><span class="mono-sm">{{ previewRemainingQty }}</span></div>
                  <div class="aqa-preview-row"><span>Purchase Cost Written Off</span><span class="mono-sm">{{ INR(previewCostWrittenOff) }}</span></div>
                  <div class="aqa-preview-row"><span>Accumulated Depreciation Written Off</span><span class="mono-sm">{{ INR(previewAccDepWrittenOff) }}</span></div>
                  <div class="aqa-preview-row fw-600"><span>Net Book Value Written Off (Loss)</span><span class="mono-sm">{{ INR(previewNbvWrittenOff) }}</span></div>
                </div>
                <p class="aqa-hint">
                  This is a client-side preview only — the server recalculates authoritatively on submit.
                  Depreciation schedule and GL fields below only appear once the write-off is actually posted.
                </p>
              </div>
            </div>

            <div v-if="doc.docstatus===1" class="add-card">
              <div class="add-card-body">
                <div class="aqa-preview-box">
                  <div class="aqa-preview-row"><span>Qty Before → After</span><span class="mono-sm">{{ doc.qty_before }} → {{ doc.qty_after }}</span></div>
                  <div class="aqa-preview-row"><span>Purchase Cost Before → After</span><span class="mono-sm">{{ INR(doc.purchase_cost_before) }} → {{ INR(doc.purchase_cost_after) }}</span></div>
                  <div class="aqa-preview-row"><span>Current Value Before → After</span><span class="mono-sm">{{ INR(doc.current_value_before) }} → {{ INR(doc.current_value_after) }}</span></div>
                  <div class="aqa-preview-row"><span>Accumulated Depreciation Written Off</span><span class="mono-sm">{{ INR(doc.write_off_accumulated_depreciation) }}</span></div>
                  <div class="aqa-preview-row fw-600"><span>Loss Posted</span><span class="mono-sm">{{ INR(doc.write_off_net_book_value) }}</span></div>
                  <div class="aqa-preview-row"><span>GL Posted</span><span class="mono-sm">{{ doc.gl_posted ? 'Yes' : 'No' }}</span></div>
                </div>
              </div>
            </div>

          </template>
        </div>

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
          <template v-else-if="doc.docstatus===1">
            <div class="add-footer-status">{{ doc.name }} — submitted, GL {{ doc.gl_posted ? 'posted' : 'not posted' }}</div>
            <button class="add-btn-cancel" style="color:#dc2626" :disabled="cancelling || !$canDelete('inventory')" @click="cancelDoc">
              <span v-html="icon('cancel',13)"></span> {{ cancelling ? 'Cancelling…' : 'Cancel' }}
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
import { ref, computed, onMounted } from 'vue';
import { apiGet, apiList, apiSave, apiSubmit, apiCancel } from '@/api/client.js';
import { useToast } from '@/composables/useToast.js';
import { icon } from '@/utils/icons.js';
import SearchableSelect from '@/components/SearchableSelect.vue';

const toast = useToast();

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

// ── LIST ──────────────────────────────────────────────
const loading = ref(false);
const list = ref([]);
const search = ref('');

async function loadList() {
  loading.value = true;
  try {
    const fields = [
      'name', 'asset', 'company', 'adjustment_date', 'reason', 'damaged_qty',
      'qty_before', 'qty_after', 'write_off_net_book_value', 'gl_posted', 'docstatus',
    ];
    list.value = await apiList('Asset Quantity Adjustment', { fields, limit: 1000, order: 'adjustment_date desc' }) || [];
    const assetNames = [...new Set(list.value.map(r => r.asset).filter(Boolean))];
    if (assetNames.length) {
      const rows = await apiList('Asset', { fields: ['name', 'asset_name'], filters: [['name', 'in', assetNames]], limit: assetNames.length });
      const byName = Object.fromEntries((rows || []).map(r => [r.name, r.asset_name]));
      list.value.forEach(r => { r.asset_name = byName[r.asset] || r.asset; });
    }
  } catch (e) {
    toast.error('Failed to load write-offs: ' + e.message);
    list.value = [];
  }
  loading.value = false;
}

const filtered = computed(() => {
  const q = search.value.toLowerCase().trim();
  if (!q) return list.value;
  return list.value.filter(i =>
    (i.name || '').toLowerCase().includes(q) ||
    (i.asset || '').toLowerCase().includes(q) ||
    (i.asset_name || '').toLowerCase().includes(q)
  );
});

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

// ── DRAWER ────────────────────────────────────────────
const drawerOpen = ref(false);
const currentName = ref(null);
const isNew = computed(() => currentName.value === null);
const detailLoading = ref(false);
const saving = ref(false);
const cancelling = ref(false);
const readOnlyEditable = computed(() => isNew.value || doc.value.docstatus === 0);

function emptyDoc() {
  return {
    doctype: 'Asset Quantity Adjustment',
    asset: '',
    company: window.__booksCompany || '',
    adjustment_date: todayLocal(),
    damaged_qty: null,
    reason: '',
    loss_account: '',
    docstatus: 0,
  };
}
const doc = ref(emptyDoc());

// ── Asset lookup / client-side preview (mirrors post_quantity_adjustment_gl) ──
const assetOptions = ref([]);
const assetInfoMap = ref({});
const selectedAsset = computed(() => assetInfoMap.value[doc.value.asset] || null);

let assetSearchTimer = null;
function fetchAssets(q = '') {
  clearTimeout(assetSearchTimer);
  assetSearchTimer = setTimeout(async () => {
    try {
      const filters = [['docstatus', '=', 1], ['status', 'not in', ['Scrapped', 'Sold']]];
      if (q) filters.push(['asset_name', 'like', `%${q}%`]);
      const rows = await apiList('Asset', {
        fields: ['name', 'asset_name', 'asset_category', 'company', 'status', 'qty', 'current_value', 'purchase_cost'],
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
  if (!assetInfoMap.value[name]) {
    try { assetInfoMap.value[name] = await apiGet('Asset', name); }
    catch (e) { toast.error('Could not load asset: ' + e.message); return; }
  }
  doc.value.company = assetInfoMap.value[name].company || doc.value.company;
}

const previewProportion = computed(() => {
  if (!selectedAsset.value || !doc.value.damaged_qty || !flt(selectedAsset.value.qty)) return 0;
  return flt(doc.value.damaged_qty) / flt(selectedAsset.value.qty);
});
const previewRemainingQty = computed(() => {
  if (!selectedAsset.value) return '—';
  return flt(selectedAsset.value.qty) - flt(doc.value.damaged_qty);
});
const previewCostWrittenOff = computed(() =>
  selectedAsset.value ? flt(selectedAsset.value.purchase_cost) * previewProportion.value : 0
);
const previewAccDepWrittenOff = computed(() => {
  if (!selectedAsset.value) return 0;
  const accDepBefore = flt(selectedAsset.value.purchase_cost) - flt(selectedAsset.value.current_value);
  return accDepBefore * previewProportion.value;
});
const previewNbvWrittenOff = computed(() => previewCostWrittenOff.value - previewAccDepWrittenOff.value);

// ── Loss accounts ──
const lossAccounts = ref([]);
const lossAccountOptions = computed(() => lossAccounts.value.map(a => ({ value: a.name, label: a.account_name || a.name })));
async function fetchLossAccounts(q = '') {
  try {
    const filters = [['is_group', '=', 0], ['disabled', '=', 0], ['account_type', 'in', ['Expense', 'Income', 'Equity']]];
    if (q) filters.push(['name', 'like', `%${q}%`]);
    lossAccounts.value = await apiList('Account', { fields: ['name', 'account_name'], filters, limit: 30, order: 'name asc' });
  } catch (e) {
    lossAccounts.value = [];
  }
}

// ── Open / close / load ──
function openAdd() {
  currentName.value = null;
  doc.value = emptyDoc();
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
    const d = await apiGet('Asset Quantity Adjustment', name);
    doc.value = d;
    if (d.asset && !assetInfoMap.value[d.asset]) {
      try { assetInfoMap.value[d.asset] = await apiGet('Asset', d.asset); } catch (e) { /* non-fatal */ }
    }
  } catch (e) {
    toast.error('Could not load ' + name + ': ' + e.message);
  }
  detailLoading.value = false;
}

// ── Save / Submit / Cancel ──
function validate() {
  if (!doc.value.asset) { toast.error('Select an asset.'); return false; }
  if (!doc.value.adjustment_date) { toast.error('Adjustment Date is required.'); return false; }
  if (!doc.value.damaged_qty || flt(doc.value.damaged_qty) <= 0) { toast.error('Damaged Qty must be greater than 0.'); return false; }
  if (selectedAsset.value && flt(doc.value.damaged_qty) >= flt(selectedAsset.value.qty)) {
    toast.error(`Damaged Qty must be less than the asset's current Qty (${selectedAsset.value.qty}). Use Asset Disposal if all units are gone.`);
    return false;
  }
  if (!doc.value.reason) { toast.error('Reason is required.'); return false; }
  if (!doc.value.loss_account) { toast.error('Loss on Damaged Assets Account is required.'); return false; }
  return true;
}

async function save(targetStatus) {
  if (!validate()) return;
  saving.value = true;
  try {
    const payload = { ...doc.value };
    if (isNew.value) delete payload.name;
    if (!payload.company) payload.company = window.__booksCompany || '';
    const saved = await apiSave(payload);
    const savedName = saved?.name || payload.name;
    currentName.value = savedName;
    doc.value = saved;

    if (targetStatus === 'Submitted' && saved?.docstatus !== 1) {
      try {
        await apiSubmit('Asset Quantity Adjustment', savedName);
        await loadDetail(savedName);
        toast.success('Write-off submitted.');
      } catch (subErr) {
        toast.error('Saved as draft — submit failed: ' + (subErr.message || subErr));
        loadList();
        return;
      }
    } else {
      toast.success(isNew.value ? 'Write-off saved' : 'Write-off updated');
    }
    loadList();
  } catch (e) {
    toast.error('Failed to save: ' + e.message);
  } finally {
    saving.value = false;
  }
}

async function cancelDoc() {
  cancelling.value = true;
  try {
    await apiCancel('Asset Quantity Adjustment', doc.value.name);
    toast.success('Write-off cancelled.');
    await loadDetail(doc.value.name);
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
  fetchLossAccounts();
});
</script>

<style scoped>
.asset-code { margin-top: 3px; color: #9ca3af; font-size: 11px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
.text-muted { color: #9ca3af; }
.mono-sm { font-size: 13px; }
.fw-600 { font-weight: 600; }
.ta-r { text-align: right; }
.aqa-notice {
  background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 8px;
  padding: 10px 14px; margin-bottom: 18px; font-size: 13px; color: #475569;
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.aqa-preview-box {
  margin-top: 14px; padding: 12px 14px; background: #f8f9fc; border: 1px solid #e2e8f0;
  border-radius: 8px; display: flex; flex-direction: column; gap: 6px;
}
.aqa-preview-row { display: flex; justify-content: space-between; font-size: 12.5px; color: #475569; gap: 12px; }
.aqa-hint { margin: 12px 0 0; font-size: 12px; color: #94a3b8; line-height: 1.5; }
</style>