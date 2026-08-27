<template>
<div class="list-page">

  <!-- ── Toolbar ── -->
  <div class="sales-toolbar">
    <div class="sales-search">
      <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
      <input v-model="search" placeholder="Search items, codes, groups…" class="sales-search-input"/>
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
      <select class="sales-select" v-model="filterGroup" title="Filter by item group">
        <option value="">All Groups</option>
        <option v-for="g in itemGroupsFull.filter(g => !g.is_group)" :key="g.name" :value="g.name">{{ g.name }}</option>
      </select>
      <button class="sales-btn-ghost view-toggle-btn" @click="viewMode=viewMode==='table'?'grid':'table'" :title="viewMode==='table'?'Grid View':'List View'"><span v-html="icon(viewMode==='table'?'grid':'file',14)"></span></button>
      <button class="sales-btn-ghost" @click="load" title="Refresh" :disabled="loading"><span v-html="icon('refresh',14)"></span></button>
      <button class="sales-btn-ghost" @click="exportCSV" title="Export CSV" :disabled="!filtered.length"><span v-html="icon('download',14)"></span> CSV</button>
      <button class="sales-btn-primary" @click="openAdd" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''"><span v-html="icon('plus',13)"></span> New Item</button>
    </div>
  </div>

  <!-- ── KPI Cards ── -->
  <div class="bk-kpi-grid">
    <div class="bk-kpi-card bk-kpi-accent clickable" @click="filterTab='all'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#dbeafe"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.8"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Total Items</div>
          <div class="bk-kpi-value">{{ list.length }}</div>
          <div class="bk-kpi-trend" :class="itemTrends.total.up?'bk-trend-up':'bk-trend-down'">{{ itemTrends.total.up?'↑':'↓' }} {{ itemTrends.total.pct }}% vs last month</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card bk-kpi-success clickable" @click="filterTab='active'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#dcfce7"><svg width="22" height="22" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="#16a34a" stroke-width="1.8"/><polyline points="7 12.5 10.5 16 17 9" stroke="#16a34a" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Active</div>
          <div class="bk-kpi-value bk-kpi-green">{{ counts.active }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">in catalog</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card clickable" @click="filterTab='inactive'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#f1f5f9"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#6b7280" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Inactive</div>
          <div class="bk-kpi-value">{{ counts.inactive }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">disabled</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card bk-kpi-warn clickable" @click="filterTab='stock'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#ede9fe"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" stroke-width="1.8"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Stock Items</div>
          <div class="bk-kpi-value" style="color:#7c3aed">{{ counts.stock }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">tracked in warehouses</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card bk-kpi-danger clickable" @click="filterTab='services'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#fee2e2"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="1.8"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Service Items</div>
          <div class="bk-kpi-value bk-kpi-red">{{ counts.services }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">no stock tracking</div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── Material Type breakdown ── -->
  <div class="bk-mat-strip">
    <div class="bk-mat-item clickable" @click="filterTab='rm'">
      <span class="bk-mat-dot" style="background:#15803d"></span>
      <span class="bk-mat-label">🌿 Raw Materials</span>
      <span class="bk-mat-count" style="color:#15803d">{{ counts.rm }}</span>
    </div>
    <div class="bk-mat-sep">|</div>
    <div class="bk-mat-item clickable" @click="filterTab='wip'">
      <span class="bk-mat-dot" style="background:#a16207"></span>
      <span class="bk-mat-label">⚙️ WIP</span>
      <span class="bk-mat-count" style="color:#a16207">{{ counts.wip }}</span>
    </div>
    <div class="bk-mat-sep">|</div>
    <div class="bk-mat-item clickable" @click="filterTab='fg'">
      <span class="bk-mat-dot" style="background:#1d4ed8"></span>
      <span class="bk-mat-label">✅ Finished Goods</span>
      <span class="bk-mat-count" style="color:#1d4ed8">{{ counts.fg }}</span>
    </div>
    <div class="bk-mat-sep">|</div>
    <div class="bk-mat-item clickable" @click="filterTab='pm'">
      <span class="bk-mat-dot" style="background:#6d28d9"></span>
      <span class="bk-mat-label">📦 Packing Materials</span>
      <span class="bk-mat-count" style="color:#6d28d9">{{ counts.pm }}</span>
    </div>
    <div class="bk-mat-sep">|</div>
    <div class="bk-mat-item clickable" @click="filterTab='scrap'">
      <span class="bk-mat-dot" style="background:#b45309"></span>
      <span class="bk-mat-label">♻️ Scrap Items</span>
      <span class="bk-mat-count" style="color:#b45309">{{ counts.scrap }}</span>
    </div>
    <div class="bk-mat-actions">
      <button class="bk-mat-add-btn" @click="openAdd('Raw Material')" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''">+ RM</button>
      <button class="bk-mat-add-btn bk-mat-add-wip" @click="openAdd('Work In Progress')" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''">+ WIP</button>
      <button class="bk-mat-add-btn bk-mat-add-fg" @click="openAdd('Finished Good')" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''">+ FG</button>
      <button class="bk-mat-add-btn bk-mat-add-pm" @click="openAdd('Packing Material')" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''">+ PM</button>
      <button class="bk-mat-add-btn bk-mat-add-scrap" @click="openAdd('Scrap Item')" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''">+ Scrap</button>
    </div>
  </div>

  <!-- ── Bulk action bar ── -->
  <BulkActionBar :count="selected.size" @clear="selected=new Set()">
    <button @click="bulkEnable" :disabled="!$canEdit('inventory')" :title="!$canEdit('inventory') ? 'Read-only access' : ''"><span v-html="icon('check',13)"></span> Enable</button>
    <button @click="bulkDisable" :disabled="!$canEdit('inventory')" :title="!$canEdit('inventory') ? 'Read-only access' : ''">Disable</button>
    <button @click="exportSelectedCSV"><span v-html="icon('download',13)"></span> Export Selected</button>
    <button class="bab-danger" @click="bulkDelete" :disabled="!$canDelete('inventory')" :title="!$canDelete('inventory') ? 'Not permitted' : ''">Delete</button>
  </BulkActionBar>

  <!-- Table view -->
  <div class="inv-table-wrap">
  <template v-if="viewMode==='table'">
    <table class="inv-table items-desktop-tbl">
      <thead><tr>
        <th class="th-check"><input type="checkbox" @change="toggleAll" :checked="allChecked"/></th>
        <th class="sortable" @click="sortBy('item_code')">Item Code <span v-html="sortArrow('item_code')"></span></th>
        <th class="sortable" @click="sortBy('item_name')">Name <span v-html="sortArrow('item_name')"></span></th>
        <th class="sortable col-hide-tablet" @click="sortBy('item_group')">Group <span v-html="sortArrow('item_group')"></span></th>
        <th class="sortable" @click="sortBy('item_type')">Type <span v-html="sortArrow('item_type')"></span></th>
        <th class="col-hide-tablet">UOM</th>
        <th class="ta-r sortable" @click="sortBy('standard_rate')">Rate (OMR) <span v-html="sortArrow('standard_rate')"></span></th>
        <th>Status</th>
        <th style="width:90px;text-align:center">Actions</th>
      </tr></thead>
      <tbody>
        <template v-if="loading"><tr v-for="n in 6" :key="n"><td colspan="10"><div class="shimmer"></div></td></tr></template>
        <tr v-else-if="!sorted.length"><td colspan="10" class="bk-empty-state"><div class="bk-empty-inner">
          <template v-if="search||filterGroup||filterTab!=='all'">
            <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.3"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <p class="bk-empty-title">No items match your filters</p>
          </template>
          <template v-else>
            <p class="bk-empty-title">No items yet</p>
            <p class="bk-empty-sub">Add your first item to start building your catalog.</p>
            <button class="bk-empty-btn" @click="openAdd" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''"><span v-html="icon('plus',13)"></span> New Item</button>
          </template>
        </div></td></tr>
        <tr v-else v-for="row in paged" :key="row.name" class="inv-row" :class="{selected:selected.has(row.name)}">
          <td class="td-check" @click.stop><input type="checkbox" :checked="selected.has(row.name)" @change="toggle(row.name)"/></td>
          <td @click="openView(row)" data-label="Code"><DocLink doctype="Item" :name="row.name">{{row.item_code||row.name}}</DocLink></td>
          <td class="fw-600" data-label="Name">
  <span @click="openView(row)">{{row.item_name}}</span>
  <span class="text-muted" style="font-size:11px;margin-left:6px;">
    ({{row.stock_uom || 'Nos'}})
  </span>
  <span v-if="row.has_variants" class="it-tpl-badge it-tpl-badge--link" @click.stop="openVariants(row)" title="Manage variants">Template ↗</span>
  <span v-else-if="row.variant_of" class="it-var-badge">Variant</span>
</td>
          <td @click="openView(row)" class="col-hide-tablet" data-label="Group"><span v-if="row.item_group" class="it-group-badge">{{row.item_group}}</span><span v-else class="text-muted">—</span></td>
          <td @click="openView(row)" data-label="Type">
            <span class="b-badge" style="font-size:11px"
              :style="row.item_type && ITEM_TYPE_COLOR[row.item_type] ? { background: ITEM_TYPE_COLOR[row.item_type].bg, color: ITEM_TYPE_COLOR[row.item_type].text } : {}">
              {{ ITEM_TYPE_ICONS[row.item_type] || '' }} {{row.item_type||'—'}}
            </span>
          </td>
          <td @click="openView(row)" class="text-muted col-hide-tablet mono-sm" data-label="UOM">{{row.stock_uom||'Nos'}}</td>
          <td @click="openView(row)" class="ta-r fw-600 mono-sm" data-label="Rate">{{fmt(row.standard_rate)}}</td>
          <td @click="openView(row)" data-label="Status"><span class="inv-status-badge" :class="row.disabled?'status-inactive':'status-active'">{{row.disabled?'Inactive':'Active'}}</span></td>
          <td style="text-align:center;white-space:nowrap" @click.stop>
            <button class="inv-act-btn" @click="openEdit(row)" :disabled="!$canEdit('inventory')" :title="!$canEdit('inventory') ? 'Read-only access' : 'Quick Edit'"><span v-html="icon('edit',13)"></span></button>
            <button class="inv-act-btn" style="color:#dc2626" @click="confirmDel(row)" :disabled="!$canDelete('inventory')" :title="!$canDelete('inventory') ? 'Not permitted' : 'Delete'"><span v-html="icon('trash',13)"></span></button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Mobile cards (hidden on desktop via CSS) -->
    <div class="items-mobile-cards">
      <template v-if="loading">
        <div v-for="n in 5" :key="n" class="b-shimmer" style="height:80px;border-radius:10px"></div>
      </template>
      <div v-else-if="!sorted.length" style="text-align:center;padding:40px;color:#868E96">No items found</div>
      <div v-else v-for="row in paged" :key="row.name" class="ii-mob-card" @click="openView(row)">
        <div class="ii-mob-card-main">
          <div class="ii-mob-card-top">
            <span class="fw-700" style="font-size:14px;color:#111827;line-height:1.3">
  {{row.item_name}}
  <span class="text-muted" style="font-size:11px;margin-left:5px;">
    ({{row.stock_uom || 'Nos'}})
  </span>
</span>
            <span class="inv-status-badge" :class="row.disabled?'status-inactive':'status-active'" style="flex-shrink:0">{{row.disabled?'Inactive':'Active'}}</span>
          </div>
          <div class="ii-mob-card-meta">
            <span class="inv-link" style="font-size:11.5px">{{row.item_code||row.name}}</span>
            <span class="text-muted" style="font-size:11px">·</span>
            <span v-if="row.item_group" class="it-group-badge" style="font-size:10.5px">{{row.item_group}}</span>
            <span class="b-badge b-badge-muted" style="font-size:10.5px">{{row.item_type||'—'}}</span>
          </div>
        </div>
        <div class="ii-mob-card-right">
          <div class="fw-700" style="font-size:14px;color:#2F9E44">OMR {{fmt(row.standard_rate)}}</div>
          <div class="text-muted" style="font-size:11px">{{row.stock_uom||'Nos'}}</div>
        </div>
        <div class="ii-mob-card-actions">
          <button @click.stop="openEdit(row)" class="ii-qa-btn ii-qa-edit" :disabled="!$canEdit('inventory')" :title="!$canEdit('inventory') ? 'Read-only access' : 'Edit'" v-html="icon('edit',13)"></button>
          <button @click.stop="confirmDel(row)" class="ii-qa-btn ii-qa-del" :disabled="!$canDelete('inventory')" :title="!$canDelete('inventory') ? 'Not permitted' : 'Delete'" v-html="icon('trash',13)"></button>
        </div>
      </div>
    </div>
  </template>

  <!-- Grid view -->
  <template v-else>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px;padding:16px">
      <div v-if="loading" v-for="n in 6" :key="n" class="b-shimmer" style="height:120px;border-radius:10px"></div>
      <div v-else-if="!sorted.length" style="grid-column:1/-1;text-align:center;padding:40px;color:#868E96">No items found</div>
      <div v-else v-for="row in paged" :key="row.name" class="b-card b-card-body ii-grid-card" @click="openView(row)">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">
          <span class="inv-status-badge" :class="row.disabled?'status-inactive':'status-active'" style="font-size:10.5px">{{row.disabled?'Inactive':'Active'}}</span>
          <div style="display:flex;align-items:center;gap:4px">
            <span class="b-badge b-badge-muted" style="font-size:10.5px">{{row.item_type||'—'}}</span>
            <button @click.stop="openEdit(row)" class="ii-qa-btn ii-qa-edit ii-card-edit" :disabled="!$canEdit('inventory')" :title="!$canEdit('inventory') ? 'Read-only access' : 'Quick Edit'" v-html="icon('edit',12)"></button>
          </div>
        </div>
       <div class="fw-700" style="font-size:14px;margin-bottom:3px;line-height:1.3">
  {{row.item_name}}
  <span style="font-size:12px;font-weight:400;color:#6b7280;margin-left:5px">
    ({{row.stock_uom || 'Nos'}})
  </span>
</div>
        <div class="text-muted" style="font-size:11px;margin-bottom:8px">{{row.item_code}}</div>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span v-if="row.item_group" class="it-group-badge" style="font-size:11px">{{row.item_group}}</span>
          <span v-else class="text-muted" style="font-size:12px">—</span>
          <span class="fw-700" style="font-size:13px;color:#2F9E44">{{fmt(row.standard_rate)}}</span>
        </div>
      </div>
    </div>
  </template>
  </div>

  <!-- ── Pagination ── -->
  <div v-if="!loading && sorted.length" style="padding:12px 4px 4px">
    <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="sorted.length" />
  </div>

  <!-- Delete confirm -->
  <Teleport to="body">
    <div v-if="showDel" style="position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:1000;display:flex;align-items:center;justify-content:center" @click.self="showDel=false">
      <div class="b-card b-card-body" style="max-width:400px;width:90%">
        <div style="font-size:15px;font-weight:700;margin-bottom:8px;color:#C92A2A">Delete Item?</div>
        <div style="font-size:13px;color:#374151;margin-bottom:20px">Delete <strong>{{delTarget?.item_name}}</strong>? This cannot be undone.</div>
        <div style="display:flex;gap:8px;justify-content:flex-end">
          <button class="b-btn b-btn-ghost" @click="showDel=false">Cancel</button>
          <button class="b-btn" style="background:#C92A2A;color:#fff;border-color:#C92A2A" :disabled="deleting || !$canDelete('inventory')" @click="doDelete">{{deleting?'Deleting…':'Yes, Delete'}}</button>
        </div>
      </div>
    </div>
  </Teleport>

  <ItemEditDrawer ref="itemDrawer" @saved="load" />
</div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { apiList, apiSave, apiDelete } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { usePagination } from "../composables/usePagination.js";
import { fmt, flt } from "../utils/format.js";
import { icon } from "../utils/icons.js";
import Pagination from "../components/Pagination.vue";
import BulkActionBar from "../components/BulkActionBar.vue";
import ItemEditDrawer from "../components/ItemEditDrawer.vue";
import DocLink from "../components/DocLink.vue";

const { toast } = useToast();
const router = useRouter();
const itemDrawer = ref(null);

const tabs = [
  { key: "all",       label: "All" },
  { key: "active",    label: "Active" },
  { key: "inactive",  label: "Inactive" },
  { key: "rm",        label: "Raw Materials" },
  { key: "wip",       label: "WIP" },
  { key: "fg",        label: "Finished Goods" },
  { key: "pm",        label: "Packing Materials" },
  { key: "stock",     label: "Stock Items" },
  { key: "services",  label: "Services" },
];

const list       = ref([]);
const loading    = ref(true);
const search     = ref("");
const filterTab  = ref("active");
const viewMode   = ref(window.innerWidth <= 480 ? "grid" : "table");
const deleting   = ref(false);
const showDel    = ref(false);
const delTarget  = ref(null);
const itemGroupsFull = ref([]);
const filterGroup   = ref("");

// Used to colour/label the Type column badge in the table.
const ITEM_TYPE_ICONS = {
  "Raw Material":     "🌿",
  "Work In Progress": "⚙️",
  "Finished Good":    "✅",
  "Packing Material": "📦",
  "Scrap Item":       "♻️",
  "Product":          "🛒",
  "Service":          "🛠️",
};
const ITEM_TYPE_COLOR = {
  "Raw Material":     { bg: "#dcfce7", text: "#15803d" },
  "Work In Progress": { bg: "#fef9c3", text: "#a16207" },
  "Finished Good":    { bg: "#dbeafe", text: "#1d4ed8" },
  "Packing Material": { bg: "#ede9fe", text: "#6d28d9" },
  "Scrap Item":       { bg: "#fef3c7", text: "#b45309" },
  "Product":          { bg: "#f1f5f9", text: "#475569" },
  "Service":          { bg: "#fee2e2", text: "#b91c1c" },
};

// Navigate to the dedicated Variant Manager page (used from the list badge).
function openVariants(row) {
  router.push({ name: "inventory-variants", params: { template: row.name } });
}

function openAdd(presetType) { itemDrawer.value?.openAdd(presetType); }
function openEdit(row) { itemDrawer.value?.openEdit(row); }

async function load() {
  loading.value = true;
  // The table only needs the Item list itself — fetch and paint that first,
  // instead of blocking on the item-group filter dropdown lookup below it.
  try {
    const rows = await apiList("Item", {
      fields: ["name","item_code","item_name","item_group","item_type","stock_uom","standard_rate","standard_buying_rate","disabled","is_stock_item","is_sales_item","is_purchase_item","has_variants","variant_of","creation","default_bom","quality_inspection_required","inspection_required_before_purchase","inspection_required_before_delivery","inspection_required_before_manufacture","min_order_qty","lead_time_days"],
      order: "item_name asc", limit: 100000,
    });
    list.value = rows || [];
  } catch { list.value = []; }
  loading.value = false;

  loadGroupFilterOptions();
}

// Feeds only the "Filter by item group" dropdown in the toolbar. The
// Add/Edit drawer's own reference data (groups, warehouses, tax templates,
// UOM, brand, accounts) is loaded internally by ItemEditDrawer.
async function loadGroupFilterOptions() {
  try {
    const g = await apiList("Item Group", { fields: ["name", "is_group"], order: "name asc", limit: 200 });
    itemGroupsFull.value = g || [];
  } catch { itemGroupsFull.value = []; }
}


const filtered = computed(() => {
  let r = list.value;
  if (filterTab.value === "active")   r = r.filter((i) => !i.disabled);
  if (filterTab.value === "inactive") r = r.filter((i) =>  i.disabled);
  if (filterTab.value === "services") r = r.filter((i) => !i.is_stock_item);
  if (filterTab.value === "stock")    r = r.filter((i) =>  i.is_stock_item);
  if (filterTab.value === "rm")       r = r.filter((i) => i.item_type === "Raw Material");
  if (filterTab.value === "wip")      r = r.filter((i) => i.item_type === "Work In Progress");
  if (filterTab.value === "fg")       r = r.filter((i) => i.item_type === "Finished Good");
  if (filterTab.value === "pm")       r = r.filter((i) => i.item_type === "Packing Material");
  if (filterTab.value === "scrap")    r = r.filter((i) => i.item_type === "Scrap Item");
  if (filterGroup.value) r = r.filter((i) => i.item_group === filterGroup.value);
  const q = search.value.toLowerCase().trim();
  if (q) r = r.filter((i) => ((i.item_name || "") + (i.item_code || "") + (i.item_group || "") + (i.item_type || "")).toLowerCase().includes(q));
  return r;
});

// ── Counts for KPI cards / filter pills ──
const counts = computed(() => ({
  active:   list.value.filter(i => !i.disabled).length,
  inactive: list.value.filter(i =>  i.disabled).length,
  stock:    list.value.filter(i =>  i.is_stock_item).length,
  services: list.value.filter(i => !i.is_stock_item).length,
  rm:       list.value.filter(i => i.item_type === "Raw Material").length,
  wip:      list.value.filter(i => i.item_type === "Work In Progress").length,
  fg:       list.value.filter(i => i.item_type === "Finished Good").length,
  pm:       list.value.filter(i => i.item_type === "Packing Material").length,
  scrap:    list.value.filter(i => i.item_type === "Scrap Item").length,
}));

// ── Secondary stats ──
const _ym  = () => { const d=new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; };
const _lym = () => { const d=new Date(); d.setMonth(d.getMonth()-1); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; };
const _trend = (a,b) => { if(!b&&!a) return {pct:0,up:true}; if(!b) return {pct:100,up:true}; const p=Math.round((a-b)/b*100); return {pct:Math.abs(p),up:p>=0}; };
const itemsThisMonth = computed(() => list.value.filter(i => (i.creation||"").startsWith(_ym())).length);
const itemTrends = computed(() => ({
  total: _trend(itemsThisMonth.value, list.value.filter(i => (i.creation||"").startsWith(_lym())).length),
}));
const avgRate = computed(() => {
  const p = list.value.filter(i => flt(i.standard_rate) > 0);
  return p.length ? p.reduce((s,i) => s + flt(i.standard_rate), 0) / p.length : 0;
});
const avgBuyingRate = computed(() => {
  const p = list.value.filter(i => flt(i.standard_buying_rate) > 0);
  return p.length ? p.reduce((s,i) => s + flt(i.standard_buying_rate), 0) / p.length : 0;
});
const groupCount = computed(() => new Set(list.value.filter(i => i.item_group).map(i => i.item_group)).size);

// ── Sorting ──
const sortCol = ref("item_name"), sortDir = ref("asc");
const sorted = computed(() => {
  const col = sortCol.value;
  return [...filtered.value].sort((a, b) => {
    const av = a[col] ?? "", bv = b[col] ?? "";
    const c = typeof av === "number" ? av - bv : String(av).localeCompare(String(bv));
    return sortDir.value === "asc" ? c : -c;
  });
});
function sortBy(col) {
  if (sortCol.value === col) sortDir.value = sortDir.value === "asc" ? "desc" : "asc";
  else { sortCol.value = col; sortDir.value = "asc"; }
}
function sortArrow(col) {
  if (sortCol.value !== col) return '<span style="color:#d1d5db">⇅</span>';
  return sortDir.value === "asc" ? "↑" : "↓";
}
const { page, pageSize, paged } = usePagination(sorted, { storageKey: "inventory-items" });

// ── Bulk selection ──
const selected = ref(new Set());
const allChecked = computed(() => sorted.value.length > 0 && sorted.value.every(i => selected.value.has(i.name)));
function toggle(n) { const s = new Set(selected.value); s.has(n) ? s.delete(n) : s.add(n); selected.value = s; }
function toggleAll(e) { selected.value = e.target.checked ? new Set(sorted.value.map(i => i.name)) : new Set(); }

async function bulkSetDisabled(disabled) {
  const names = [...selected.value];
  if (!names.length) return;
  try {
    await Promise.all(names.map(n => apiSave({ doctype: "Item", name: n, disabled: disabled ? 1 : 0 })));
    list.value = list.value.map(i => names.includes(i.name) ? { ...i, disabled: disabled ? 1 : 0 } : i);
    toast(`${names.length} item(s) ${disabled ? "disabled" : "enabled"}`);
    selected.value = new Set();
  } catch (e) { toast("Bulk update failed: " + e.message, "error"); }
}
function bulkEnable()  { bulkSetDisabled(false); }
function bulkDisable() { bulkSetDisabled(true); }

async function bulkDelete() {
  const names = [...selected.value];
  if (!names.length) return;
  if (!confirm(`Delete ${names.length} item(s)? This cannot be undone.`)) return;
  let okCount = 0;
  for (const n of names) {
    try { await apiDelete("Item", n); okCount++; } catch {}
  }
  list.value = list.value.filter(i => !names.includes(i.name));
  toast(`${okCount} of ${names.length} item(s) deleted`);
  selected.value = new Set();
}

function exportSelectedCSV() {
  const rows = list.value.filter(i => selected.value.has(i.name));
  if (!rows.length) return;
  const esc = v => { const s = v==null?"":String(v); return /[",\n]/.test(s) ? '"'+s.replace(/"/g,'""')+'"' : s; };
  const lines = [["Item Code","Item Name","Group","Type","UOM","Selling Rate","Buying Rate","Stock Item","Status"].join(",")];
  for (const i of rows) {
    lines.push([i.item_code||"",i.item_name||"",i.item_group||"",i.item_type||"",i.stock_uom||"",flt(i.standard_rate),flt(i.standard_buying_rate),i.is_stock_item?"Yes":"No",i.disabled?"Inactive":"Active"].map(esc).join(","));
  }
  const blob = new Blob(["﻿"+lines.join("\r\n")], {type:"text/csv;charset=utf-8;"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `items_selected_${new Date().toISOString().slice(0,10)}.csv`;
  a.click(); URL.revokeObjectURL(url);
  toast(`Exported ${rows.length} item(s)`);
}

function exportCSV() {
  const rows = filtered.value;
  if (!rows.length) return;
  const esc = v => { const s = v==null?"":String(v); return /[",\n]/.test(s) ? '"'+s.replace(/"/g,'""')+'"' : s; };
  const lines = [["Item Code","Item Name","Group","Type","UOM","Selling Rate","Buying Rate","Stock Item","Status"].join(",")];
  for (const i of rows) {
    lines.push([i.item_code||"",i.item_name||"",i.item_group||"",i.item_type||"",i.stock_uom||"",flt(i.standard_rate),flt(i.standard_buying_rate),i.is_stock_item?"Yes":"No",i.disabled?"Inactive":"Active"].map(esc).join(","));
  }
  const blob = new Blob(["﻿"+lines.join("\r\n")], {type:"text/csv;charset=utf-8;"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `items_${new Date().toISOString().slice(0,10)}.csv`;
  a.click(); URL.revokeObjectURL(url);
  toast(`Exported ${rows.length} item(s)`);
}

function openView(row) {
  router.push({ name: "item-view", params: { itemCode: row.name } });
}

function confirmDel(row) { delTarget.value = row; showDel.value = true; }

async function doDelete() {
  deleting.value = true;
  try {
    await apiDelete("Item", delTarget.value.name);
    list.value = list.value.filter((i) => i.name !== delTarget.value.name);
    toast("Item deleted");
    showDel.value = false;
  } catch (e) { toast("Delete failed: " + e.message, "error"); }
  finally { deleting.value = false; }
}

function onHashChange() {
  const h = window.location.hash;
  if (h === "#/inventory/items" || h.startsWith("#/inventory/items?") || h.startsWith("#/inventory/items/")) {
    load();
  }
}

onMounted(() => { load(); window.addEventListener("hashchange", onHashChange); });
onUnmounted(() => { window.removeEventListener("hashchange", onHashChange); });
</script>

<style>
/* ── Group filter select ── */
.it-group-filter-wrap {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.it-group-filter-select {
  border: 1.5px solid #e2e8f0;
  border-radius: 8px;
  padding: 5px 10px;
  font-size: 12.5px;
  color: #374151;
  background: #fff;
  outline: none;
  cursor: pointer;
  transition: border-color .15s;
  max-width: 160px;
}
.it-group-filter-select:focus { border-color: #3b82f6; }

/* ── Item Type pill group ── */
.it-type-pills {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  margin-top: 2px;
}
.it-type-pill {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 9px 12px;
  border: 1.5px solid #e2e8f0;
  border-radius: 9px;
  background: #f8fafc;
  font-size: 12.5px;
  font-weight: 600;
  color: #374151;
  cursor: pointer;
  transition: all .12s;
  text-align: left;
  font-family: inherit;
}
.it-type-pill:hover { background: #eff6ff; border-color: #93c5fd; color: #1d4ed8; }
.it-type-pill--active {
  background: #eff6ff;
  border-color: #2563eb;
  color: #1d4ed8;
  box-shadow: 0 0 0 2px rgba(37,99,235,.12);
}

/* ── Group badge ── */
.it-group-badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 9px;
  border-radius: 8px;
  background: #ede9fe;
  color: #5b21b6;
  white-space: nowrap;
}

/* ── Quick action buttons ── */
.ii-qa-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  background: transparent;
  transition: background .12s, color .12s;
  flex-shrink: 0;
}
.ii-qa-edit {
  color: #6b7280;
}
.ii-qa-edit:hover {
  background: #eff6ff;
  color: #2563eb;
}
.ii-qa-del {
  color: #6b7280;
}
.ii-qa-del:hover {
  background: #fff1f2;
  color: #dc2626;
}
/* Card edit button — slightly smaller, more compact */
.ii-card-edit {
  width: 24px;
  height: 24px;
  border-radius: 5px;
  opacity: 0;
  transition: opacity .15s, background .12s, color .12s;
}
.ii-grid-card:hover .ii-card-edit {
  opacity: 1;
}


/* ── Mobile cards (hidden by default, shown on mobile) ── */
.items-mobile-cards { display: none; flex-direction: column; gap: 8px; }
.ii-mob-card {
  background: #fff;
  border: 1px solid #E2E8F0;
  border-radius: 10px;
  padding: 12px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  transition: background .12s, box-shadow .12s;
}
.ii-mob-card:hover { background: #F8FAFC; box-shadow: 0 1px 6px rgba(0,0,0,.07); }
.ii-mob-card-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 5px; }
.ii-mob-card-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.ii-mob-card-meta { display: flex; align-items: center; gap: 5px; flex-wrap: wrap; }
.ii-mob-card-right { text-align: right; flex-shrink: 0; }
.ii-mob-card-actions { display: flex; gap: 4px; flex-shrink: 0; }

/* ── Responsive ── */

/* Base: table always scrollable */
.items-tbl-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
.items-tbl-wrap .b-table { min-width: 700px; width: 100%; }

@media (max-width: 1024px) {
  /* Tablet: hide GST% col (7) */
  .items-tbl-wrap .b-table th:nth-child(7),
  .items-tbl-wrap .b-table td:nth-child(7) { display: none; }
  .items-tbl-wrap .b-table { min-width: 620px; }
}

@media (max-width: 768px) {
  /* Toolbar: stack vertically */
  .b-action-bar { flex-direction: column !important; align-items: stretch !important; }
  .b-filter-row { overflow-x: auto; -webkit-overflow-scrolling: touch; flex-wrap: nowrap !important; padding-bottom: 2px; }
  /* Hide Group (3), UOM (5), GST% (7) */
  .items-tbl-wrap .b-table th:nth-child(3),
  .items-tbl-wrap .b-table td:nth-child(3),
  .items-tbl-wrap .b-table th:nth-child(5),
  .items-tbl-wrap .b-table td:nth-child(5),
  .items-tbl-wrap .b-table th:nth-child(7),
  .items-tbl-wrap .b-table td:nth-child(7) { display: none; }
  .items-tbl-wrap .b-table { min-width: 460px; }
}

@media (max-width: 480px) {
  .it-group-filter-wrap { display: none; }
  .view-toggle-btn { display: none !important; }
  /* Switch table → cards on mobile */
  .items-desktop-tbl { display: none !important; }
  .items-mobile-cards { display: flex !important; }
}

/* ── View Drawer ── */
.vd-backdrop {
  position: fixed; inset: 0;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(2px);
  z-index: 1000;
}
.vd-panel {
  position: fixed; top: 0; right: 0; bottom: 0;
  width: 480px; max-width: 100vw;
  background: #fff;
  z-index: 1001;
  display: flex; flex-direction: column;
  box-shadow: -8px 0 40px rgba(15,23,42,.14);
  transform: translateX(100%);
  transition: transform .26s cubic-bezier(.4,0,.2,1);
}
.vd-panel--open { transform: translateX(0); }

/* Header */
.vd-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 20px;
  background: #fff;
  border-bottom: 1px solid #f1f5f9;
  flex-shrink: 0;
  gap: 12px;
}
.vd-header-left { display: flex; align-items: center; gap: 14px; min-width: 0; flex: 1; }
.vd-avatar {
  width: 44px; height: 44px; border-radius: 12px;
  background: linear-gradient(135deg, #eff6ff, #dbeafe);
  border: 1.5px solid #bfdbfe;
  display: flex; align-items: center; justify-content: center;
  color: #2563eb; flex-shrink: 0;
}
.vd-header-info { min-width: 0; }
.vd-title {
  font-size: 15px; font-weight: 700; color: #0f172a;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  letter-spacing: -.01em;
}
.vd-subtitle {
  font-size: 12px; color: #94a3b8; margin-top: 2px;
  font-weight: 500;
}
.vd-header-right { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.vd-status-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px; border-radius: 20px;
  font-size: 11.5px; font-weight: 600;
}
.vd-status-dot {
  width: 6px; height: 6px; border-radius: 50%;
}
.vd-status-active { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
.vd-status-active .vd-status-dot { background: #16a34a; }
.vd-status-inactive { background: #f8fafc; color: #94a3b8; border: 1px solid #e2e8f0; }
.vd-status-inactive .vd-status-dot { background: #94a3b8; }
.vd-close-btn {
  width: 32px; height: 32px; border-radius: 8px;
  background: #f8fafc; border: 1.5px solid #e2e8f0;
  cursor: pointer; color: #64748b;
  display: flex; align-items: center; justify-content: center;
  transition: background .12s, color .12s;
}
.vd-close-btn:hover { background: #f1f5f9; color: #0f172a; }

/* Hero metrics */
.vd-hero {
  display: flex; align-items: stretch;
  padding: 0 20px;
  background: #fafbfc;
  border-bottom: 1px solid #f1f5f9;
  flex-shrink: 0;
}
.vd-metric {
  flex: 1; padding: 16px 10px; text-align: center;
}
.vd-metric-value {
  font-size: 18px; font-weight: 800; color: #0f172a;
  letter-spacing: -.02em; line-height: 1;
}
.vd-metric-green { color: #16a34a; }
.vd-metric-label {
  font-size: 10.5px; font-weight: 600; color: #94a3b8;
  text-transform: uppercase; letter-spacing: .06em; margin-top: 5px;
}
.vd-metric-divider {
  width: 1px; background: #f1f5f9; margin: 12px 0; flex-shrink: 0;
}
.vd-badge-type {
  display: inline-block; padding: 3px 10px; border-radius: 6px;
  background: #eff6ff; color: #2563eb;
  font-size: 12px; font-weight: 600; border: 1px solid #bfdbfe;
}

/* Body */
.vd-body {
  flex: 1; overflow-y: auto; background: #f8fafc;
  padding: 16px; display: flex; flex-direction: column; gap: 12px;
}

/* Cards */
.vd-card {
  background: #fff; border: 1px solid #e9edf2; border-radius: 12px;
  overflow: visible;
  box-shadow: 0 1px 3px rgba(15,23,42,.04);
  display: block !important;
}
.vd-card-header {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
  background: #fafbfc;
}
.vd-card-icon {
  width: 26px; height: 26px; border-radius: 7px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.vd-card-icon--blue { background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; }
.vd-card-icon--green { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
.vd-card-icon--purple { background: #f5f3ff; color: #7c3aed; border: 1px solid #ddd6fe; }
.vd-card-icon--gray { background: #f8fafc; color: #64748b; border: 1px solid #e2e8f0; }
.vd-card-title {
  font-size: 12px; font-weight: 700; color: #374151;
  text-transform: uppercase; letter-spacing: .05em;
}

/* Rows */
.vd-rows { padding: 4px 0; display: block !important; }
.vd-row {
  display: flex !important; align-items: center !important; justify-content: space-between !important;
  padding: 10px 16px !important; gap: 12px;
  border-bottom: 1px solid #f0f2f5 !important;
  visibility: visible !important; opacity: 1 !important;
  height: auto !important; overflow: visible !important;
}
.vd-row:last-child { border-bottom: none !important; }
.vd-row-label {
  font-size: 12px !important; font-weight: 500 !important; color: #9ca3af !important;
  white-space: nowrap; flex-shrink: 0;
  display: inline !important; visibility: visible !important;
}
.vd-row-val {
  font-size: 13px !important; font-weight: 500 !important; color: #1e293b !important;
  text-align: right;
  display: inline !important; visibility: visible !important;
}
.vd-row-val--code { color: #2563eb !important; font-size: 12.5px !important; }
.vd-row-val--muted { color: #c4c9d4 !important; font-size: 13px !important; }

/* Price grid */
.vd-price-grid {
  display: flex !important; gap: 0; padding: 14px 16px 2px;
  visibility: visible !important;
}
.vd-price-block { flex: 1; display: block !important; }
.vd-price-amount {
  font-size: 22px !important; font-weight: 800 !important; color: #1e293b !important;
  letter-spacing: -.03em; line-height: 1; display: block !important;
}
.vd-price-amount--sell { color: #16a34a !important; }
.vd-price-tag { font-size: 11px; font-weight: 500; color: #94a3b8; margin-top: 4px; display: block !important; }

/* Chips */
.vd-group-chip {
  display: inline-block; padding: 3px 10px; border-radius: 6px;
  background: #f5f3ff; color: #6d28d9; border: 1px solid #ddd6fe;
  font-size: 11.5px; font-weight: 600;
}
.vd-gst-chip {
  display: inline-block; padding: 3px 10px; border-radius: 6px;
  background: #fefce8; color: #a16207; border: 1px solid #fde68a;
  font-size: 11.5px; font-weight: 700;
}
.vd-stock-pill {
  display: inline-flex; align-items: center;
  padding: 3px 10px; border-radius: 20px; font-size: 11.5px; font-weight: 600;
}
.vd-stock-pill--on { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
.vd-stock-pill--off { background: #f8fafc; color: #94a3b8; border: 1px solid #e2e8f0; }

/* Description */
.vd-description {
  padding: 12px 16px; font-size: 13px; color: #4b5563; line-height: 1.6;
}

/* Footer */
.vd-footer {
  padding: 14px 20px; border-top: 1px solid #f1f5f9;
  display: flex; justify-content: flex-end; gap: 8px;
  background: #fff; flex-shrink: 0;
}
.vd-btn-ghost {
  padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 600;
  border: 1.5px solid #e2e8f0; background: #fff; color: #374151;
  cursor: pointer; transition: background .12s, border-color .12s;
}
.vd-btn-ghost:hover { background: #f8fafc; border-color: #cbd5e1; }
.vd-btn-primary {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 18px; border-radius: 8px; font-size: 13px; font-weight: 600;
  background: #2563eb; color: #fff; border: none; cursor: pointer;
  transition: background .12s, transform .1s;
  box-shadow: 0 1px 4px rgba(37,99,235,.25);
}
.vd-btn-primary:hover { background: #1d4ed8; transform: translateY(-1px); }
.vd-btn-primary:active { transform: translateY(0); }

@media (max-width: 480px) {
  .vd-panel { width: 100vw; }
  .vd-hero { gap: 0; }
  .vd-metric { padding: 14px 6px; }
  .vd-metric-value { font-size: 16px; }
}

/* Material type breakdown strip */
.bk-mat-strip {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
  background: #fff; border: 1px solid #e9edf2; border-radius: 10px;
  padding: 10px 16px; margin-bottom: 14px;
  box-shadow: 0 1px 3px rgba(15,23,42,.04);
}
.bk-mat-item { display: flex; align-items: center; gap: 6px; padding: 2px 6px; border-radius: 6px; cursor: pointer; }
.bk-mat-item:hover { background: #f1f5f9; }
.bk-mat-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.bk-mat-label { font-size: 12px; color: #374151; font-weight: 500; }
.bk-mat-count { font-size: 13px; font-weight: 700; min-width: 18px; text-align: right; }
.bk-mat-sep { color: #e2e8f0; font-size: 16px; }
.bk-mat-actions { margin-left: auto; display: flex; gap: 6px; }
.bk-mat-add-btn {
  padding: 4px 10px; border-radius: 6px; border: 1.5px solid #e2e8f0;
  font-size: 11px; font-weight: 700; cursor: pointer; background: #dcfce7; color: #15803d;
  transition: all .14s;
}
.bk-mat-add-btn:hover { opacity: 0.8; }
.bk-mat-add-wip  { background: #fef9c3; color: #a16207; }
.bk-mat-add-fg   { background: #dbeafe; color: #1d4ed8; }
.bk-mat-add-pm   { background: #ede9fe; color: #6d28d9; }
.bk-mat-add-scrap { background: #fef3c7; color: #b45309; }

.it-tpl-badge { margin-left:7px; padding:1px 7px; border-radius:11px; font-size:10px; font-weight:700; background:#eef2ff; color:#4f46e5; vertical-align:middle; }
.it-tpl-badge--link { cursor:pointer; }
.it-tpl-badge--link:hover { background:#4f46e5; color:#fff; }
.it-var-badge { margin-left:7px; padding:1px 7px; border-radius:11px; font-size:10px; font-weight:700; background:#f0fdf4; color:#16a34a; vertical-align:middle; }

</style>