<template>
<div class="list-page">

  <!-- ── Toolbar ── -->
  <div class="sales-toolbar">
    <div class="sales-search">
      <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
      <input v-model="search" placeholder="Search assets..." class="sales-search-input"/>
    </div>
    <div class="sales-pills">
      <button v-for="t in tabs" :key="t.key"
        class="sales-pill" :class="{active:filterTab===t.key, ['pill-'+t.key]: t.key!=='all'}"
        @click="filterTab=t.key">
        {{ t.label }}
        <span v-if="t.key!=='all'" class="sales-pill-count">{{ counts[t.key] }}</span>
      </button>
    </div>
    <div class="sales-actions">
      <select class="sales-select" v-model="filterGroup" title="Filter by asset category">
        <option value="">All Categories</option>
        <option v-for="g in assetCategories" :key="g.name" :value="g.name">{{ g.name }}</option>
      </select>
      <button class="sales-btn-ghost view-toggle-btn" @click="viewMode=viewMode==='table'?'grid':'table'" :title="viewMode==='table'?'Grid View':'List View'"><span v-html="icon(viewMode==='table'?'grid':'file',14)"></span></button>
      <button class="sales-btn-ghost" @click="load" title="Refresh" :disabled="loading"><span v-html="icon('refresh',14)"></span></button>
      <button class="sales-btn-ghost" @click="exportCSV" title="Export CSV" :disabled="!filtered.length"><span v-html="icon('download',14)"></span> CSV</button>
      <button class="sales-btn-primary" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''" @click="openAdd"><span v-html="icon('plus',13)"></span> New Asset</button>
    </div>
  </div>

  <div class="bk-kpi-grid">
    <div class="bk-kpi-card bk-kpi-accent clickable" @click="filterTab='all'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#dbeafe"><span v-html="icon('file',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Total Assets</div>
          <div class="bk-kpi-value">{{ list.length }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">registered assets</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card bk-kpi-success clickable" @click="filterTab='Submitted'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#dcfce7"><span v-html="icon('check',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Submitted</div>
          <div class="bk-kpi-value bk-kpi-green">{{ counts.Submitted || 0 }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">capitalized</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card bk-kpi-warn clickable" @click="filterTab='Partially Depreciated'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#fef3c7"><span v-html="icon('refresh',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Partially Depreciated</div>
          <div class="bk-kpi-value bk-kpi-amber">{{ counts['Partially Depreciated'] || 0 }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">in schedule</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card clickable" @click="filterTab='Fully Depreciated'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#f1f5f9"><span v-html="icon('folder',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Fully Depreciated</div>
          <div class="bk-kpi-value">{{ counts['Fully Depreciated'] || 0 }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">book value closed</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card bk-kpi-danger clickable" @click="filterTab='Scrapped'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#fee2e2"><span v-html="icon('trash',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Scrapped</div>
          <div class="bk-kpi-value bk-kpi-red">{{ counts.Scrapped || 0 }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">disposed assets</div>
        </div>
      </div>
    </div>
  </div>

  <div class="bk-stat-grid">
    <div class="bk-stat-card">
      <div class="bk-stat-content">
        <div>
          <div class="bk-stat-label">Purchase Value</div>
          <div class="bk-stat-value bk-kpi-green" style="font-size:16px">{{ fmt(summary.purchaseValue) }}</div>
        </div>
        <div class="bk-stat-icon" style="background:#dcfce7;color:#16a34a"><span v-html="icon('trend',18)"></span></div>
      </div>
    </div>
    <div class="bk-stat-card">
      <div class="bk-stat-content">
        <div>
          <div class="bk-stat-label">Categories</div>
          <div class="bk-stat-value">{{ summary.categories }}</div>
        </div>
        <div class="bk-stat-icon" style="background:#cffafe;color:#0891b2"><span v-html="icon('grid',18)"></span></div>
      </div>
    </div>
    <div class="bk-stat-card">
      <div class="bk-stat-content">
        <div>
          <div class="bk-stat-label">Draft</div>
          <div class="bk-stat-value">{{ counts.Draft || 0 }}</div>
        </div>
        <div class="bk-stat-icon" style="background:#e2e8f0;color:#475569"><span v-html="icon('edit',18)"></span></div>
      </div>
    </div>
    <div class="bk-stat-card">
      <div class="bk-stat-content">
        <div>
          <div class="bk-stat-label">Sold</div>
          <div class="bk-stat-value bk-kpi-blue">{{ counts.Sold || 0 }}</div>
        </div>
        <div class="bk-stat-icon" style="background:#dbeafe;color:#2563eb"><span v-html="icon('file',18)"></span></div>
      </div>
    </div>
  </div>
   
<!-- ── Bulk action bar (appears when assets are selected) ── -->
  <div v-if="selected.size" class="inv-bulk-bar" style="margin:12px 0 0">
    <span class="inv-bulk-count"><strong>{{ selected.size }}</strong> asset{{ selected.size > 1 ? 's' : '' }} selected</span>
    <button class="inv-bulk-btn" @click="bulkSetActive(true)" :disabled="bulkLoading || !$canEdit('inventory')"><span v-html="icon('check',13)"></span> Enable</button>
    <button class="inv-bulk-btn" @click="bulkSetActive(false)" :disabled="bulkLoading || !$canEdit('inventory')"><span v-html="icon('cancel',13)"></span> Disable</button>
    <button class="inv-bulk-btn inv-bulk-danger" @click="bulkDelete" :disabled="bulkLoading || !$canDelete('inventory')" :title="!$canDelete('inventory') ? 'Not permitted' : ''"><span v-html="icon('trash',13)"></span> Delete</button>
    <button class="inv-bulk-clear" @click="clearSelection">✕ Clear</button>
  </div>


  <!-- Table view -->
  <div class="inv-table-wrap">
  <template v-if="viewMode==='table'">
    <table class="inv-table assets-desktop-tbl">
      <thead><tr>
        <th class="th-check"><input type="checkbox" @change="toggleAll" :checked="allChecked"/></th>
        <th class="sortable" @click="sortBy('asset_name')">Asset Name <span v-html="sortArrow('asset_name')"></span></th>
        <th class="sortable" @click="sortBy('asset_category')">Category <span v-html="sortArrow('asset_category')"></span></th>
        <th class="sortable" @click="sortBy('purchase_date')">Purchase Date <span v-html="sortArrow('purchase_date')"></span></th>
        <th class="ta-r sortable" @click="sortBy('purchase_cost')">Purchase Cost <span v-html="sortArrow('purchase_cost')"></span></th>
        <th class="sortable" @click="sortBy('status')">Status <span v-html="sortArrow('status')"></span></th>
        <th style="width:110px;text-align:center">Actions</th>
      </tr></thead>
      <tbody>
        <template v-if="loading"><tr v-for="n in 6" :key="n"><td colspan="7"><div class="shimmer"></div></td></tr></template>
        <tr v-else-if="!sorted.length"><td colspan="7" class="bk-empty-state"><div class="bk-empty-inner">
          <template v-if="search||filterGroup||filterTab!=='all'">
            <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.3"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <p class="bk-empty-title">No assets match your filters</p>
          </template>
          <template v-else>
            <p class="bk-empty-title">No assets yet</p>
            <p class="bk-empty-sub">Add your first asset to start building your catalog.</p>
            <button class="bk-empty-btn" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''" @click="openAdd"><span v-html="icon('plus',13)"></span> New Asset</button>
          </template>
        </div></td></tr>
        <tr v-else v-for="row in paged" :key="row.name" class="inv-row" :class="{selected:selected.has(row.name)}">
          <td class="td-check" @click.stop><input type="checkbox" :checked="selected.has(row.name)" @change="toggle(row.name)"/></td>
          <td @click="openView(row)" data-label="Asset Name"><span class="inv-link">{{row.asset_name || row.name}}</span><div class="asset-code">{{ row.name }}</div></td>
          <td @click="openView(row)" data-label="Asset Category"><span v-if="row.asset_category" class="it-group-badge">{{row.asset_category}}</span><span v-else class="text-muted">-</span></td>
          <td @click="openView(row)" class="mono-sm text-muted" data-label="Purchase Date">{{ fmtDate(row.purchase_date) }}</td>
          <td @click="openView(row)" class="ta-r mono-sm fw-600" data-label="Purchase Cost">{{ fmt(row.purchase_cost || 0) }}</td>
          <td @click="openView(row)" data-label="Status"><span class="inv-status-badge" :class="statusClass(row.status)">{{row.status || 'Draft'}}</span></td>
          <td style="text-align:center;white-space:nowrap" @click.stop>
            <button class="inv-act-btn" @click="openView(row)" title="View"><span v-html="icon('eye',13)"></span></button>
            <button class="inv-act-btn" @click="openEdit(row)" :disabled="!$canEdit('inventory')" title="Quick Edit"><span v-html="icon('edit',13)"></span></button>
            <button class="inv-act-btn" style="color:#dc2626" @click="confirmDel(row)" :disabled="!$canDelete('inventory')" title="Delete"><span v-html="icon('trash',13)"></span></button>
          </td>
        </tr>
      </tbody>
    </table>

    <div class="assets-mobile-cards">
      <template v-if="loading">
        <div v-for="n in 5" :key="n" class="b-shimmer" style="height:86px;border-radius:10px"></div>
      </template>
      <div v-else-if="!sorted.length" style="text-align:center;padding:40px;color:#868E96">No assets found</div>
      <div v-else v-for="row in paged" :key="row.name" class="ii-mob-card" @click="openView(row)">
        <div class="ii-mob-card-main">
          <div class="ii-mob-card-top">
            <span class="fw-700" style="font-size:14px;color:#111827;line-height:1.3">{{ row.asset_name || row.name }}</span>
            <span class="inv-status-badge" :class="statusClass(row.status)" style="flex-shrink:0">{{ row.status || 'Draft' }}</span>
          </div>
          <div class="ii-mob-card-meta">
            <span class="inv-link" style="font-size:11.5px">{{ row.name }}</span>
            <span v-if="row.asset_category" class="it-group-badge" style="font-size:10.5px">{{ row.asset_category }}</span>
          </div>
        </div>
        <div class="ii-mob-card-right">
          <div class="fw-700" style="font-size:14px;color:#2F9E44">{{ fmt(row.purchase_cost || 0) }}</div>
          <div class="text-muted" style="font-size:11px">{{ fmtDate(row.purchase_date) }}</div>
        </div>
        <div class="ii-mob-card-actions">
          <button @click.stop="openEdit(row)" class="ii-qa-btn ii-qa-edit" :disabled="!$canEdit('inventory')" title="Edit" v-html="icon('edit',13)"></button>
          <button @click.stop="confirmDel(row)" class="ii-qa-btn ii-qa-del" :disabled="!$canDelete('inventory')" title="Delete" v-html="icon('trash',13)"></button>
        </div>
      </div>
    </div>
  </template>

  <!-- Grid view -->
    <template v-else>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px;padding:16px">
      <div v-if="loading" v-for="n in 6" :key="n" class="b-shimmer" style="height:120px;border-radius:10px"></div>
      <div v-else-if="!sorted.length" style="grid-column:1/-1;text-align:center;padding:40px;color:#868E96">No assets found</div>
      <div v-else v-for="row in paged" :key="row.name" class="b-card b-card-body ii-grid-card" @click="openView(row)">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">
          <span class="inv-status-badge" :class="row.status==='Fully Depreciated'?'status-inactive':'status-active'" style="font-size:10.5px">{{row.status}}</span>
          <div style="display:flex;align-items:center;gap:4px">
            <button @click.stop="openEdit(row)" class="ii-qa-btn ii-qa-edit ii-card-edit" :disabled="!$canEdit('inventory')" title="Quick Edit" v-html="icon('edit',12)"></button>
          </div>
        </div>
        <div class="fw-700" style="font-size:14px;margin-bottom:3px;line-height:1.3">{{row.asset_name || row.name}}</div>
        <div class="text-muted" style="font-size:11px;margin-bottom:8px">{{row.name}}</div>
        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px">
          <span v-if="row.asset_category" class="it-group-badge" style="font-size:11px">{{row.asset_category}}</span>
          <span v-else class="text-muted" style="font-size:12px">-</span>
          <span class="fw-700" style="font-size:13px;color:#2F9E44">{{fmt(row.purchase_cost || 0)}}</span>
        </div>
      </div>
    </div>
  </template>
  </div>

  <!-- ── Pagination ── -->
  <div v-if="!loading && sorted.length" style="padding:12px 4px 4px">
    <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="sorted.length" />
  </div>
</div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from '@/composables/useToast.js';
import { useConfirm } from '@/composables/useConfirm.js';
import { icon } from '@/utils/icons.js';
import Pagination from '@/components/Pagination.vue';
import { fmt, fmtDate } from '@/utils/format.js';
import { apiList, apiDelete, apiCall } from '@/api/client.js';

const router = useRouter();
const { confirm } = useConfirm();
const toast = useToast();

const loading = ref(true);
const list = ref([]);
const assetCategories = ref([]);
const search = ref('');
const filterTab = ref('all');
const filterGroup = ref('');
const viewMode = ref('table');
const page = ref(1);
const pageSize = ref(20);
const selected = ref(new Set());
const bulkLoading = ref(false);
const sortKey = ref('asset_name');
const sortDir = ref(1);

const tabs = [
  { key: 'all', label: 'All' },
  { key: 'Draft', label: 'Draft' },
  { key: 'Submitted', label: 'Submitted' },
  { key: 'Partially Depreciated', label: 'Partially Depreciated' },
  { key: 'Fully Depreciated', label: 'Fully Depreciated' },
  { key: 'Scrapped', label: 'Scrapped' },
  { key: 'Sold', label: 'Sold' },
];

const counts = computed(() => {
  const c = {};
  for (const t of tabs) {
    if (t.key !== 'all') {
      c[t.key] = list.value.filter(i => i.status === t.key).length;
    }
  }
  return c;
});

const summary = computed(() => {
  const categories = new Set(list.value.map(i => i.asset_category).filter(Boolean)).size;
  const purchaseValue = list.value.reduce((sum, i) => sum + (parseFloat(i.purchase_cost) || 0), 0);
  return { categories, purchaseValue };
});

const filtered = computed(() => {
  let result = list.value;
  if (filterTab.value !== 'all') {
    result = result.filter(i => i.status === filterTab.value);
  }
  if (filterGroup.value) {
    result = result.filter(i => i.asset_category === filterGroup.value);
  }
  if (search.value) {
    const s = search.value.toLowerCase();
    result = result.filter(i =>
      i.asset_name.toLowerCase().includes(s) ||
      (i.asset_category && i.asset_category.toLowerCase().includes(s))
    );
  }
  return result;
});

const sorted = computed(() => {
  const key = sortKey.value;
  const dir = sortDir.value;
  return [...filtered.value].sort((a, b) => {
    const av = a[key] ?? '';
    const bv = b[key] ?? '';
    if (typeof av === 'number' || typeof bv === 'number') return ((parseFloat(av) || 0) - (parseFloat(bv) || 0)) * dir;
    return String(av).localeCompare(String(bv), undefined, { numeric: true }) * dir;
  });
});

const paged = computed(() => {
  const start = (page.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return sorted.value.slice(start, end);
});

const allChecked = computed(() => {
  return selected.value.size === paged.value.length && paged.value.length > 0;
});

function toggleAll() {
  if (allChecked.value) {
    selected.value.clear();
  } else {
    for (const row of paged.value) {
      selected.value.add(row.name);
    }
  }
}

function toggle(name) {
  if (selected.value.has(name)) {
    selected.value.delete(name);
  } else {
    selected.value.add(name);
  }
}

function clearSelection() {
  selected.value = new Set();
}

function sortBy(key) {
  if (sortKey.value === key) sortDir.value *= -1;
  else { sortKey.value = key; sortDir.value = 1; }
}

function sortArrow(key) {
  if (sortKey.value !== key) return '';
  return sortDir.value === 1 ? '&#9650;' : '&#9660;';
}

function statusClass(status) {
  const map = {
    Draft: 'status-draft',
    Submitted: 'status-active',
    'Partially Depreciated': 'status-partial',
    'Fully Depreciated': 'status-inactive',
    Scrapped: 'status-cancelled',
    Sold: 'status-paid',
    'In Maintenance': 'status-maintenance',
    'Out of Order': 'status-danger',
  };
  return map[status] || 'status-draft';
}

async function load() {
  loading.value = true;
  try {
    const assets = await apiList('Asset', {
      fields: [
        'name', 'asset_name', 'status', 'asset_category', 'purchase_date', 
        'purchase_cost', 'supplier', 'location', 'department',
        'depreciation_method', 'useful_life', 'salvage_value', 
        'last_maintenance_date', 'next_maintenance_date', 'maintenance_frequency_days',
        'description', 'is_active'
      ],
      order: 'asset_name asc',
      limit: 500,
    });
    list.value = assets;
    assetCategories.value = Array.from(new Set(assets.map(a => a.asset_category).filter(Boolean))).map(name => ({ name }));
  } catch (e) {
    toast.error('Failed to load assets: ' + e.message);
    list.value = [];
    assetCategories.value = [];
  } finally {
    loading.value = false;
  }
}

function openAdd() {
  router.push({ name: 'asset-details', params: { id: 'new' } });
}

function openView(row) {
  router.push({ name: 'asset-details', params: { id: row.name } });
}

function openEdit(row) {
  router.push({ name: 'asset-details', params: { id: row.name } });
}

async function confirmDel(row) {
  const ok = await confirm({
    title: 'Delete Asset',
    body: `Are you sure you want to delete asset ${row.asset_name || row.name}?`,
    okLabel: 'Delete',
    okStyle: 'danger',
  });
  if (ok) await del(row.name);
}

async function del(name) {
  await apiDelete('Asset', name);
  toast.success('Asset deleted');
  load();
}

async function bulkSetActive(value) {
  if (!selected.value.size) return;
  bulkLoading.value = true;
  try {
    const names = [...selected.value];
    await Promise.all(names.map(name =>
      apiCall('frappe.client.set_value', { doctype: 'Asset', name, field: 'is_active', value })
    ));
    toast.success(`${names.length} asset${names.length > 1 ? 's' : ''} ${value ? 'enabled' : 'disabled'}`);
    clearSelection();
    load();
  } catch (e) {
    toast.error('Failed to update assets: ' + e.message);
  } finally {
    bulkLoading.value = false;
  }
}

async function bulkDelete() {
  if (!selected.value.size) return;
  const names = [...selected.value];
  const ok = await confirm({
    title: 'Delete Assets',
    body: `Are you sure you want to delete ${names.length} selected asset${names.length > 1 ? 's' : ''}?`,
    okLabel: 'Delete',
    okStyle: 'danger',
  });
  if (!ok) return;
  bulkLoading.value = true;
  try {
    await Promise.all(names.map(name => apiDelete('Asset', name)));
    toast.success('Selected assets deleted');
    clearSelection();
    load();
  } catch (e) {
    toast.error('Failed to delete assets: ' + e.message);
  } finally {
    bulkLoading.value = false;
  }
}

function exportCSV() {
  const headers = ['Asset ID', 'Asset Name', 'Category', 'Purchase Date', 'Purchase Cost', 'Status'];
  const rows = filtered.value.map(r => [r.name, r.asset_name || '', r.asset_category || '', r.purchase_date || '', r.purchase_cost || 0, r.status || '']);
  const csv = [headers, ...rows].map(row => row.map(v => `"${String(v ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'assets.csv';
  a.click();
  URL.revokeObjectURL(url);
}

onMounted(load);
</script>

<style scoped>
.asset-code {
  margin-top: 3px;
  color: #9ca3af;
  font-size: 11px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.assets-mobile-cards { display: none; }
.status-draft { background:#f1f5f9; color:#475569; }
.status-partial { background:#fef3c7; color:#92400e; }
.status-cancelled { background:#fee2e2; color:#b91c1c; }
.status-paid { background:#dbeafe; color:#1d4ed8; }
.status-maintenance { background:#fef9c3; color:#a16207; }
.status-danger { background:#fecaca; color:#991b1b; }
@media (max-width: 768px) {
  .assets-desktop-tbl { display: none; }
  .assets-mobile-cards {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px;
  }
}
</style>