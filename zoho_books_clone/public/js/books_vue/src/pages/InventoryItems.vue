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
      <button class="sales-btn-primary" @click="openAdd"><span v-html="icon('plus',13)"></span> New Item</button>
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
    <div class="bk-mat-actions">
      <button class="bk-mat-add-btn" @click="openAdd('Raw Material')">+ RM</button>
      <button class="bk-mat-add-btn bk-mat-add-wip" @click="openAdd('Work In Progress')">+ WIP</button>
      <button class="bk-mat-add-btn bk-mat-add-fg" @click="openAdd('Finished Good')">+ FG</button>
      <button class="bk-mat-add-btn bk-mat-add-pm" @click="openAdd('Packing Material')">+ PM</button>
    </div>
  </div>

  <!-- ── Bulk action bar ── -->
  <BulkActionBar :count="selected.size" @clear="selected=new Set()">
    <button @click="bulkEnable"><span v-html="icon('check',13)"></span> Enable</button>
    <button @click="bulkDisable">Disable</button>
    <button @click="exportSelectedCSV"><span v-html="icon('download',13)"></span> Export Selected</button>
    <button class="bab-danger" @click="bulkDelete">Delete</button>
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
        <th class="ta-r sortable" @click="sortBy('standard_rate')">Rate (₹) <span v-html="sortArrow('standard_rate')"></span></th>
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
            <button class="bk-empty-btn" @click="openAdd"><span v-html="icon('plus',13)"></span> New Item</button>
          </template>
        </div></td></tr>
        <tr v-else v-for="row in paged" :key="row.name" class="inv-row" :class="{selected:selected.has(row.name)}">
          <td class="td-check" @click.stop><input type="checkbox" :checked="selected.has(row.name)" @change="toggle(row.name)"/></td>
          <td @click="openView(row)" data-label="Code"><span class="inv-link">{{row.item_code||row.name}}</span></td>
          <td class="fw-600" data-label="Name"><span @click="openView(row)">{{row.item_name}}</span><span v-if="row.has_variants" class="it-tpl-badge it-tpl-badge--link" @click.stop="openVariants(row)" title="Manage variants">Template ↗</span><span v-else-if="row.variant_of" class="it-var-badge">Variant</span></td>
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
            <button class="inv-act-btn" @click="openEdit(row)" title="Quick Edit"><span v-html="icon('edit',13)"></span></button>
            <button class="inv-act-btn" style="color:#dc2626" @click="confirmDel(row)" title="Delete"><span v-html="icon('trash',13)"></span></button>
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
            <span class="fw-700" style="font-size:14px;color:#111827;line-height:1.3">{{row.item_name}}</span>
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
          <div class="fw-700" style="font-size:14px;color:#2F9E44">₹{{fmt(row.standard_rate)}}</div>
          <div class="text-muted" style="font-size:11px">{{row.stock_uom||'Nos'}}</div>
        </div>
        <div class="ii-mob-card-actions">
          <button @click.stop="openEdit(row)" class="ii-qa-btn ii-qa-edit" title="Edit" v-html="icon('edit',13)"></button>
          <button @click.stop="confirmDel(row)" class="ii-qa-btn ii-qa-del" title="Delete" v-html="icon('trash',13)"></button>
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
            <button @click.stop="openEdit(row)" class="ii-qa-btn ii-qa-edit ii-card-edit" title="Quick Edit" v-html="icon('edit',12)"></button>
          </div>
        </div>
        <div class="fw-700" style="font-size:14px;margin-bottom:3px;line-height:1.3">{{row.item_name}}</div>
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

  <!-- View Drawer -->
  <Teleport to="body">
    <div v-if="viewOpen" class="vd-backdrop" @click.self="viewOpen=false"></div>
    <div class="vd-panel" :class="viewOpen ? 'vd-panel--open' : ''">
      <template v-if="viewDoc">

        <!-- Header -->
        <div class="vd-header">
          <div class="vd-header-left">
            <div class="vd-avatar">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
            </div>
            <div class="vd-header-info">
              <div class="vd-title">{{ viewDoc.item_name }}</div>
              <div class="vd-subtitle">{{ viewDoc.item_code || viewDoc.name }}</div>
            </div>
          </div>
          <div class="vd-header-right">
            <span class="vd-status-pill" :class="viewDoc.disabled ? 'vd-status-inactive' : 'vd-status-active'">
              <span class="vd-status-dot"></span>
              {{ viewDoc.disabled ? 'Inactive' : 'Active' }}
            </span>
            <button class="vd-close-btn" @click="viewOpen=false">
              <span v-html="icon('x', 15)"></span>
            </button>
          </div>
        </div>

        <!-- Hero metrics row -->
        <div class="vd-hero">
          <div class="vd-metric">
            <div class="vd-metric-value vd-metric-green">{{ fmt(viewDoc.standard_rate) }}</div>
            <div class="vd-metric-label">Selling Rate</div>
          </div>
          <div class="vd-metric-divider"></div>
          <div class="vd-metric">
            <div class="vd-metric-value">{{ fmt(viewDoc.standard_buying_rate || 0) }}</div>
            <div class="vd-metric-label">Buying Rate</div>
          </div>
          <div class="vd-metric-divider"></div>
          <div class="vd-metric">
            <div class="vd-metric-value">
              <span class="vd-badge-type">{{ viewDoc.item_type || '—' }}</span>
            </div>
            <div class="vd-metric-label">Item Type</div>
          </div>
        </div>

        <!-- Body -->
        <div class="vd-body">

          <!-- Item Details card -->
          <div class="vd-card">
            <div class="vd-card-header">
              <div class="vd-card-icon vd-card-icon--blue">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              </div>
              <span class="vd-card-title">Item Details</span>
            </div>
            <div class="vd-rows">
              <div class="vd-row">
                <span class="vd-row-label">Item Code</span>
                <span class="vd-row-val vd-row-val--code">{{ viewDoc.item_code || viewDoc.name }}</span>
              </div>
              <div class="vd-row">
                <span class="vd-row-label">Item Group</span>
                <span class="vd-row-val">
                  <span v-if="viewDoc.item_group" class="vd-group-chip">{{ viewDoc.item_group }}</span>
                  <span v-else class="vd-row-val--muted">—</span>
                </span>
              </div>
              <div class="vd-row">
                <span class="vd-row-label">Default UOM</span>
                <span class="vd-row-val">{{ viewDoc.stock_uom || 'Nos' }}</span>
              </div>
              <div class="vd-row" v-if="viewDoc.brand">
                <span class="vd-row-label">Brand</span>
                <span class="vd-row-val">{{ viewDoc.brand }}</span>
              </div>
              <div class="vd-row" v-if="viewDoc.hsn_code">
                <span class="vd-row-label">HSN / SAC</span>
                <span class="vd-row-val vd-row-val--code">{{ viewDoc.hsn_code }}</span>
              </div>
            </div>
          </div>

          <!-- Pricing & Tax card -->
          <div class="vd-card">
            <div class="vd-card-header">
              <div class="vd-card-icon vd-card-icon--green">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
              </div>
              <span class="vd-card-title">Pricing & Tax</span>
            </div>
            <div class="vd-price-grid">
              <div class="vd-price-block">
                <div class="vd-price-amount vd-price-amount--sell">{{ fmt(viewDoc.standard_rate) }}</div>
                <div class="vd-price-tag">Selling Rate</div>
              </div>
              <div class="vd-price-block" v-if="viewDoc.standard_buying_rate">
                <div class="vd-price-amount">{{ fmt(viewDoc.standard_buying_rate) }}</div>
                <div class="vd-price-tag">Buying Rate</div>
              </div>
            </div>
            <div class="vd-rows" style="margin-top:10px">
              <div class="vd-row">
                <span class="vd-row-label">Tax Template</span>
                <span class="vd-row-val">
                  <span v-if="viewDoc.tax_code" class="vd-gst-chip">{{ viewDoc.tax_code }}</span>
                  <span v-else class="vd-row-val--muted">—</span>
                </span>
              </div>
            </div>
          </div>

          <!-- Inventory card -->
          <div class="vd-card">
            <div class="vd-card-header">
              <div class="vd-card-icon vd-card-icon--purple">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
              </div>
              <span class="vd-card-title">Inventory</span>
            </div>
            <div class="vd-rows">
              <div class="vd-row">
                <span class="vd-row-label">Stock Tracking</span>
                <span class="vd-row-val">
                  <span class="vd-stock-pill" :class="viewDoc.is_stock_item ? 'vd-stock-pill--on' : 'vd-stock-pill--off'">
                    {{ viewDoc.is_stock_item ? 'Tracked' : 'Not Tracked' }}
                  </span>
                </span>
              </div>
              <div class="vd-row" v-if="viewDoc.default_warehouse">
                <span class="vd-row-label">Default Warehouse</span>
                <span class="vd-row-val">{{ viewDoc.default_warehouse }}</span>
              </div>
              <div class="vd-row" v-if="viewDoc.valuation_method">
                <span class="vd-row-label">Valuation Method</span>
                <span class="vd-row-val">{{ viewDoc.valuation_method }}</span>
              </div>
            </div>
          </div>

          <!-- Description if present -->
          <div class="vd-card" v-if="viewDoc.description">
            <div class="vd-card-header">
              <div class="vd-card-icon vd-card-icon--gray">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="17" y1="10" x2="3" y2="10"/><line x1="21" y1="6" x2="3" y2="6"/><line x1="21" y1="14" x2="3" y2="14"/><line x1="13" y1="18" x2="3" y2="18"/></svg>
              </div>
              <span class="vd-card-title">Description</span>
            </div>
            <div class="vd-description">{{ viewDoc.description }}</div>
          </div>

        </div>

        <!-- Footer -->
        <div class="vd-footer">
          <button class="vd-btn-ghost" @click="viewOpen=false">Close</button>
          <button class="vd-btn-primary" @click="openEdit(viewDoc); viewOpen=false">
            <span v-html="icon('edit', 13)"></span> Edit Item
          </button>
        </div>

      </template>
    </div>
  </Teleport>

  <!-- Delete confirm -->
  <Teleport to="body">
    <div v-if="showDel" style="position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:1000;display:flex;align-items:center;justify-content:center" @click.self="showDel=false">
      <div class="b-card b-card-body" style="max-width:400px;width:90%">
        <div style="font-size:15px;font-weight:700;margin-bottom:8px;color:#C92A2A">Delete Item?</div>
        <div style="font-size:13px;color:#374151;margin-bottom:20px">Delete <strong>{{delTarget?.item_name}}</strong>? This cannot be undone.</div>
        <div style="display:flex;gap:8px;justify-content:flex-end">
          <button class="b-btn b-btn-ghost" @click="showDel=false">Cancel</button>
          <button class="b-btn" style="background:#C92A2A;color:#fff;border-color:#C92A2A" :disabled="deleting" @click="doDelete">{{deleting?'Deleting…':'Yes, Delete'}}</button>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- Add / Edit Drawer -->
  <Teleport to="body">
    <div v-if="showDrawer" class="ad-backdrop" @click.self="showDrawer=false"></div>
    <div class="ad-panel" :class="showDrawer ? 'ad-panel--open' : ''">

      <!-- Header -->
      <div class="ad-header">
        <div class="ad-header-left">
          <div class="ad-avatar" :class="drawerMode==='add' ? 'ad-avatar--add' : 'ad-avatar--edit'">
            <svg v-if="drawerMode==='add'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          </div>
          <div>
            <div class="ad-title">{{ drawerMode === 'add' ? 'New Item' : 'Edit Item' }}</div>
            <div class="ad-subtitle">{{ drawerMode === 'edit' ? form.item_code : 'Fill in the details below' }}</div>
          </div>
        </div>
        <button class="ad-close" @click="showDrawer=false">
          <span v-html="icon('x', 15)"></span>
        </button>
      </div>

      <!-- Tab nav -->
      <div class="ad-tabs">
        <button v-for="t in [{k:'basic',l:'Basic Info',icon:'📋'},{k:'pricing',l:'Pricing & Tax',icon:'💰'},{k:'inventory',l:'Inventory',icon:'📦'},{k:'variants',l:'Variants',icon:'🧩'}]"
          :key="t.k" class="ad-tab" :class="drawerTab===t.k ? 'ad-tab--active' : ''"
          @click="drawerTab=t.k">
          {{ t.l }}
        </button>
      </div>

      <!-- Body -->
      <div class="ad-body">

        <!-- ── Basic Info ── -->
        <template v-if="drawerTab==='basic'">
          <div class="ad-section">
            <div class="ad-section-title">Item Identity</div>
            <div class="ad-grid-2">
              <div class="ad-field">
                <label class="ad-label">Item Name <span class="ad-required">*</span></label>
                <input class="ad-input" v-model="form.item_name" placeholder="e.g. Laptop 15-inch"/>
              </div>
              <div class="ad-field">
                <label class="ad-label">Item Code <span class="ad-required">*</span></label>
                <input class="ad-input" v-model="form.item_code" placeholder="Auto-filled from name if blank"/>
              </div>
            </div>
            <div class="ad-field">
              <label class="ad-label">Item Group</label>
              <SearchableSelect v-model="form.item_group" :options="leafGroupOptions" placeholder="Search or create a group…" :createable="true" @create="createItemGroup"/>
            </div>
          </div>

          <div class="ad-section">
            <div class="ad-section-title">Item Type <span class="ad-hint" style="font-size:11px;font-weight:400">(sets stock & valuation defaults)</span></div>
            <div class="ad-type-grid">
              <button v-for="t in ITEM_TYPES" :key="t" type="button"
                class="ad-type-btn" :class="{ 'ad-type-btn--active': form.item_type === t }"
                @click="form.item_type = t; applyTypeDefaults(t)">
                <span class="ad-type-icon">{{ ITEM_TYPE_ICONS[t] }}</span>
                <span class="ad-type-label">{{ ITEM_TYPE_LABEL[t] || t }}</span>
              </button>
            </div>
            <div v-if="form.item_type" class="ad-type-info-strip" :style="{ background: ITEM_TYPE_COLOR[form.item_type]?.bg || '#f1f5f9', color: ITEM_TYPE_COLOR[form.item_type]?.text || '#475569' }">
              <span v-if="form.item_type==='Raw Material'">🌿 Raw herbs, minerals, and base ingredients used in manufacturing</span>
              <span v-else-if="form.item_type==='Work In Progress'">⚙️ Intermediate semi-finished goods in the production pipeline</span>
              <span v-else-if="form.item_type==='Finished Good'">✅ Final products ready for sale — capsules, tablets, oils, churnam, etc.</span>
              <span v-else-if="form.item_type==='Packing Material'">📦 Bottles, labels, cartons, foil, and other packaging components</span>
              <span v-else-if="form.item_type==='Service'">🛠️ Non-stock service — no inventory tracked</span>
              <span v-else>🛒 General sellable product</span>
            </div>
          </div>

          <div class="ad-section">
            <div class="ad-section-title">Additional Info</div>
            <div class="ad-grid-2">
              <div class="ad-field">
                <label class="ad-label">Default UOM <span class="ad-required">*</span></label>
                <select class="ad-input" v-model="form.stock_uom">
                  <option value="">— Select UOM —</option>
                  <option v-for="u in uomList" :key="u" :value="u">{{u}}</option>
                </select>
              </div>
              <div class="ad-field">
                <label class="ad-label">Brand</label>
                <select class="ad-input" v-model="form.brand">
                  <option value="">— Select —</option>
                  <option v-for="b in brandList" :key="b" :value="b">{{b}}</option>
                </select>
              </div>
            </div>
            <div class="ad-grid-2">
              <div class="ad-field">
                <label class="ad-label">HSN / SAC Code</label>
                <input class="ad-input" v-model="form.hsn_code" placeholder="e.g. 847130"/>
              </div>
            </div>
            <div class="ad-field">
              <label class="ad-label">Description</label>
              <textarea class="ad-input ad-textarea" v-model="form.description" rows="3" placeholder="Optional item description…"></textarea>
            </div>
          </div>

          <div class="ad-toggle-row">
            <div class="ad-toggle-left">
              <div class="ad-toggle-title">Mark as Inactive</div>
              <div class="ad-toggle-sub">Inactive items won't appear in transaction dropdowns</div>
            </div>
            <label class="ad-switch">
              <input type="checkbox" :checked="!!form.disabled" @change="form.disabled=($event.target.checked?1:0)"/>
              <span class="ad-switch-track"></span>
            </label>
          </div>
        </template>

        <!-- ── Pricing & Tax ── -->
        <template v-else-if="drawerTab==='pricing'">
          <div class="ad-section">
            <div class="ad-section-title">Rates</div>
            <div class="ad-grid-2">
              <div class="ad-field">
                <label class="ad-label">Selling Rate (₹)</label>
                <div class="ad-input-prefix-wrap">
                  <span class="ad-input-prefix">₹</span>
                  <input type="number" class="ad-input ad-input--prefixed" v-model="form.standard_rate" min="0" placeholder="0.00"/>
                </div>
              </div>
              <div class="ad-field">
                <label class="ad-label">Buying Rate (₹)</label>
                <div class="ad-input-prefix-wrap">
                  <span class="ad-input-prefix">₹</span>
                  <input type="number" class="ad-input ad-input--prefixed" v-model="form.standard_buying_rate" min="0" placeholder="0.00"/>
                </div>
              </div>
            </div>
          </div>

          <div class="ad-section">
            <div class="ad-section-title">Tax</div>
            <div class="ad-field">
              <label class="ad-label">Tax Template <span class="ad-required">*</span></label>
              <select class="ad-input" v-model="form.tax_code">
                <option value="">— Select —</option>
                <option v-for="t in taxTemplates" :key="t.name" :value="t.name">{{ t.label }}</option>
              </select>
              <div class="ad-hint" style="margin-top:6px">Tax on transactions is determined by the selected Tax Template.</div>
            </div>
          </div>

          <div class="ad-section">
            <div class="ad-section-title">Accounts</div>
            <div class="ad-field">
              <label class="ad-label">Income Account <span class="ad-required">*</span></label>
              <SearchableSelect v-model="form.income_account" :options="incomeAccounts" placeholder="Select income account…" :createable="true" createDoctype="Account" @create="reloadAccounts"/>
            </div>
            <div class="ad-field" style="margin-top:12px">
              <label class="ad-label">Expense Account <span class="ad-required">*</span></label>
              <SearchableSelect v-model="form.expense_account" :options="expenseAccounts" placeholder="Select expense account…" :createable="true" createDoctype="Account" @create="reloadAccounts"/>
            </div>
          </div>
        </template>

        <!-- ── Inventory ── -->
        <template v-else-if="drawerTab==='inventory'">
          <div class="ad-toggle-row" style="margin-bottom:20px">
            <div class="ad-toggle-left">
              <div class="ad-toggle-title">Track Inventory</div>
              <div class="ad-toggle-sub">Maintain stock levels and ledger for this item</div>
            </div>
            <label class="ad-switch">
              <input type="checkbox" :checked="!!form.is_stock_item" @change="form.is_stock_item=($event.target.checked?1:0)"/>
              <span class="ad-switch-track ad-switch-track--green"></span>
            </label>
          </div>

          <div class="ad-toggle-row" style="margin-bottom:20px" v-if="form.is_stock_item">
            <div class="ad-toggle-left">
              <div class="ad-toggle-title">Track by Batch</div>
              <div class="ad-toggle-sub">Require a Batch No, mfg & expiry date on every stock entry</div>
            </div>
            <label class="ad-switch">
              <input type="checkbox" :checked="!!form.has_batch_no" @change="form.has_batch_no=($event.target.checked?1:0)"/>
              <span class="ad-switch-track ad-switch-track--green"></span>
            </label>
          </div>

          <div class="ad-section" v-if="form.is_stock_item && form.has_batch_no">
            <div class="ad-section-title">Shelf Life</div>
            <div class="ad-grid-2">
              <div class="ad-field">
                <label class="ad-label">Shelf Life (Days)</label>
                <input type="number" class="ad-input" v-model="form.shelf_life_in_days" min="0"/>
                <div class="ad-toggle-sub" style="margin-top:4px">If set, a Batch's Expiry Date is auto-calculated from Manufacturing Date + Shelf Life when left blank.</div>
              </div>
            </div>
          </div>

          <div class="ad-section">
            <div class="ad-section-title">Stock Settings</div>
            <div class="ad-grid-2">
              <div class="ad-field">
                <label class="ad-label">Valuation Method</label>
                <select class="ad-input" v-model="form.valuation_method">
                  <option v-for="m in VAL_METHODS" :key="m" :value="m">{{m}}</option>
                </select>
              </div>
              <div class="ad-field">
                <label class="ad-label">Default Warehouse <span v-if="form.is_stock_item" class="ad-required">*</span></label>
                <SearchableSelect v-model="form.default_warehouse" :options="warehouses" value-key="name" label-key="label" placeholder="Select warehouse…"/>
              </div>
            </div>
            <div class="ad-grid-2" style="margin-top:12px">
              <div class="ad-field">
                <label class="ad-label">Reorder Level</label>
                <input type="number" class="ad-input" v-model="form.reorder_level" min="0"/>
              </div>
              <div class="ad-field">
                <label class="ad-label">Reorder Qty</label>
                <input type="number" class="ad-input" v-model="form.reorder_qty" min="0"/>
              </div>
            </div>
          </div>

          <div class="ad-section" v-if="form.is_stock_item">
            <div class="ad-section-title">Manufacturing</div>

            <div class="ad-field" v-if="form.item_type === 'Finished Good' || form.item_type === 'Work In Progress'">
              <label class="ad-label">Default BOM</label>
              <select class="ad-input" v-model="form.default_bom" :disabled="drawerMode !== 'edit'">
                <option value="">— Select —</option>
                <option v-for="b in bomOptions" :key="b.name" :value="b.name">{{ b.name }}{{ b.is_default ? ' (default)' : '' }}</option>
              </select>
              <div class="ad-toggle-sub" style="margin-top:4px" v-if="drawerMode !== 'edit'">Save the item first, then reopen it to link an active BOM here.</div>
              <div class="ad-toggle-sub" style="margin-top:4px" v-else-if="!bomOptions.length">No submitted, active BOM found for this item yet. Create one from Manufacturing → BOM, then reopen this item.</div>
              <div class="ad-toggle-sub" style="margin-top:4px" v-else>Auto-suggested when creating a Work Order for this item.</div>
            </div>

            <div class="ad-grid-2" :style="(form.item_type === 'Finished Good' || form.item_type === 'Work In Progress') ? 'margin-top:12px' : ''">
              <div class="ad-field">
                <label class="ad-label">Minimum Order Qty</label>
                <input type="number" class="ad-input" v-model="form.min_order_qty" min="0"/>
                <div class="ad-toggle-sub" style="margin-top:4px">Used for Material Request / Production Plan suggestions.</div>
              </div>
              <div class="ad-field">
                <label class="ad-label">Lead Time (Days)</label>
                <input type="number" class="ad-input" v-model="form.lead_time_days" min="0"/>
                <div class="ad-toggle-sub" style="margin-top:4px">Days between raising a request and receiving/producing this item.</div>
              </div>
            </div>

            <div style="margin-top:16px">
              <div class="ad-toggle-title" style="margin-bottom:8px">Quality Inspection Required</div>

              <div class="ad-toggle-row">
                <div class="ad-toggle-left">
                  <div class="ad-toggle-title">Before Purchase (Incoming)</div>
                  <div class="ad-toggle-sub">Require QC Inspection when this item is received (e.g. Purchase Receipt).</div>
                </div>
                <label class="ad-switch">
                  <input type="checkbox" :checked="!!form.inspection_required_before_purchase" @change="form.inspection_required_before_purchase=($event.target.checked?1:0)"/>
                  <span class="ad-switch-track ad-switch-track--green"></span>
                </label>
              </div>

              <div class="ad-toggle-row" style="margin-top:8px">
                <div class="ad-toggle-left">
                  <div class="ad-toggle-title">Before Delivery (Outgoing)</div>
                  <div class="ad-toggle-sub">Require QC Inspection before this item leaves (e.g. Delivery Note).</div>
                </div>
                <label class="ad-switch">
                  <input type="checkbox" :checked="!!form.inspection_required_before_delivery" @change="form.inspection_required_before_delivery=($event.target.checked?1:0)"/>
                  <span class="ad-switch-track ad-switch-track--green"></span>
                </label>
              </div>

              <div class="ad-toggle-row" style="margin-top:8px">
                <div class="ad-toggle-left">
                  <div class="ad-toggle-title">Before Manufacture (In Process)</div>
                  <div class="ad-toggle-sub">Require QC Inspection when this item is produced via a manufacturing/stock entry.</div>
                </div>
                <label class="ad-switch">
                  <input type="checkbox" :checked="!!form.inspection_required_before_manufacture" @change="form.inspection_required_before_manufacture=($event.target.checked?1:0)"/>
                  <span class="ad-switch-track ad-switch-track--green"></span>
                </label>
              </div>
            </div>
          </div>

          <div class="ad-info-banner">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            <p style="margin:0">To set or adjust stock quantities, go to <strong>Inventory → Warehouses</strong> → select a warehouse → click <strong>Adjust</strong> next to any item.</p>
          </div>
        </template>

        <!-- ── Variants ── -->
        <template v-else>
          <div v-if="drawerMode !== 'edit'" class="ad-empty-state">
            <div class="ad-empty-icon">🧩</div>
            <div class="ad-empty-title">Save the item first</div>
            <div class="ad-empty-sub">Create this item, then reopen it to configure attributes and generate variants.</div>
          </div>
          <template v-else>
            <div class="ad-toggle-row" style="margin-bottom:18px">
              <div class="ad-toggle-left">
                <div class="ad-toggle-title">Variant template</div>
                <div class="ad-toggle-sub">Define attributes (Size, Colour…) and generate a sellable item for each combination.</div>
              </div>
              <label class="ad-switch">
                <input type="checkbox" :checked="!!form.has_variants" @change="form.has_variants=($event.target.checked?1:0)"/>
                <span class="ad-switch-track ad-switch-track--green"></span>
              </label>
            </div>

            <template v-if="form.has_variants">
              <div class="vr-manage-cta">
                <div class="vr-manage-text">
                  <div class="vr-manage-title">Variant Manager</div>
                  <div class="vr-manage-sub">Define attributes, generate variants, and edit prices, SKUs &amp; stock on a dedicated page.</div>
                </div>
                <button class="ad-btn-primary" :disabled="openingVariants" @click="openVariantManager">
                  {{ openingVariants ? 'Opening…' : 'Open Variant Manager →' }}
                </button>
              </div>
            </template>
            <div v-else class="ad-empty-state" style="padding-top:8px">
              <div class="ad-empty-icon">🧩</div>
              <div class="ad-empty-sub">Turn on “Variant template” to define attributes and generate variants.</div>
            </div>
          </template>
        </template>

      </div>

      <!-- Footer -->
      <div class="ad-footer">
        <button class="ad-btn-ghost" @click="showDrawer=false">Cancel</button>
        <button class="ad-btn-primary" :disabled="saving" @click="saveItem">
          <svg v-if="saving" class="ad-spinner" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
          {{ saving ? 'Saving…' : (drawerMode === 'edit' ? 'Update Item' : 'Create Item') }}
        </button>
      </div>

    </div>
  </Teleport>
</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from "vue";
import { useRouter } from "vue-router";
import { apiList, apiGET, apiGet, apiPOST, apiSave, apiDelete, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { usePagination } from "../composables/usePagination.js";
import { fmt, fmtDate, flt } from "../utils/format.js";
import { icon } from "../utils/icons.js";
import SearchableSelect from "../components/SearchableSelect.vue";
import Pagination from "../components/Pagination.vue";
import BulkActionBar from "../components/BulkActionBar.vue";

const { toast } = useToast();
const router = useRouter();

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
const filterTab  = ref("all");
const viewMode   = ref(window.innerWidth <= 480 ? "grid" : "table");
const showDrawer = ref(false);
const drawerMode = ref("add");
const saving     = ref(false);
const deleting   = ref(false);
const showDel    = ref(false);
const delTarget  = ref(null);
const drawerTab  = ref("basic");
const viewOpen   = ref(false);
const viewDoc    = ref(null);
const itemGroups    = ref([]);
const itemGroupsFull = ref([]);
const filterGroup   = ref("");
const warehouses    = ref([]);
const taxTemplates  = ref([]);
const uomList       = ref([]);
const brandList     = ref([]);
const defaultAccounts = ref({ income: "", expense: "" });
const incomeAccounts  = ref([]);
const expenseAccounts = ref([]);
const bomOptions      = ref([]);   // Active, submitted BOMs for the item being edited

const form = reactive({
  name: "", item_code: "", item_name: "", item_group: "", item_type: "Product",
  stock_uom: "Nos", hsn_code: "", description: "", disabled: 0, brand: "",
  standard_rate: 0, standard_buying_rate: 0, gst_rate: 18, tax_code: "",
  income_account: "", expense_account: "",
  is_stock_item: 1, has_batch_no: 0, shelf_life_in_days: 0, valuation_method: "FIFO", default_warehouse: "",
  reorder_level: 0, reorder_qty: 0, opening_stock: 0,
  default_bom: "", quality_inspection_required: 0, min_order_qty: 0, lead_time_days: 0,
  inspection_required_before_purchase: 0, inspection_required_before_delivery: 0,
  inspection_required_before_manufacture: 0,
  has_variants: 0,
});

// ── Variants ──
const variantAttrs      = ref([]);   // [{ attribute, valuesText }]
const attributeOptions  = ref([]);   // Item Attribute masters for the picker
const variantsList      = ref([]);
const generatingVariants = ref(false);
const openingVariants = ref(false);
const splitValues = (s) => String(s || "").split(",").map(v => v.trim()).filter(Boolean);
const variantComboCount = computed(() =>
  variantAttrs.value.reduce((n, a) => {
    const c = splitValues(a.valuesText).length;
    return c ? n * c : n;
  }, variantAttrs.value.some(a => splitValues(a.valuesText).length) ? 1 : 0)
);
async function loadAttributeOptions() {
  try {
    const r = await apiList("Item Attribute", { fields: ["name"], order: "name asc", limit: 200 });
    attributeOptions.value = (r || []).map(a => ({ value: a.name, label: a.name }));
  } catch { attributeOptions.value = []; }
}
function addVariantAttr() { variantAttrs.value.push({ attribute: "", valuesText: "" }); }
function removeVariantAttr(i) { variantAttrs.value.splice(i, 1); }
async function createAttribute(name, i) {
  const nm = String(name || "").trim();
  if (!nm) return;
  try {
    await apiSave({ doctype: "Item Attribute", attribute_name: nm });
    await loadAttributeOptions();
    if (variantAttrs.value[i]) variantAttrs.value[i].attribute = nm;
    toast(`Attribute "${nm}" created`);
  } catch (e) { toast("Could not create attribute: " + e.message, "error"); }
}
// Navigate to the dedicated Variant Manager page (used from the list badge).
function openVariants(row) {
  router.push({ name: "inventory-variants", params: { template: row.name } });
}

// From the drawer: make sure the template item is saved (mark it as a variant
// template), then open the dedicated Variant Manager page.
async function openVariantManager() {
  openingVariants.value = true;
  try {
    form.has_variants = 1;
    const name = await saveItem({ close: false });
    if (!name) return;
    showDrawer.value = false;
    router.push({ name: "inventory-variants", params: { template: name } });
  } catch (e) { toast("Could not open Variant Manager: " + e.message, "error"); }
  finally { openingVariants.value = false; }
}

const ITEM_TYPES      = ["Raw Material", "Work In Progress", "Finished Good", "Packing Material", "Product", "Service"];
const ITEM_TYPE_ICONS = {
  "Raw Material":     "🌿",
  "Work In Progress": "⚙️",
  "Finished Good":    "✅",
  "Packing Material": "📦",
  "Product":          "🛒",
  "Service":          "🛠️",
};
const ITEM_TYPE_LABEL = {
  "Raw Material":     "Raw Material",
  "Work In Progress": "WIP",
  "Finished Good":    "Finished Good",
  "Packing Material": "Packing Material",
  "Product":          "Product",
  "Service":          "Service",
};
// Badge colours per material type
const ITEM_TYPE_COLOR = {
  "Raw Material":     { bg: "#dcfce7", text: "#15803d" },
  "Work In Progress": { bg: "#fef9c3", text: "#a16207" },
  "Finished Good":    { bg: "#dbeafe", text: "#1d4ed8" },
  "Packing Material": { bg: "#ede9fe", text: "#6d28d9" },
  "Product":          { bg: "#f1f5f9", text: "#475569" },
  "Service":          { bg: "#fee2e2", text: "#b91c1c" },
};
// Smart defaults: warehouse type and valuation per item type
const ITEM_TYPE_DEFAULTS = {
  "Raw Material":     { warehouse_type: "Raw Material Store", valuation: "FIFO",          is_stock: 1 },
  "Work In Progress": { warehouse_type: "WIP",                valuation: "Moving Average", is_stock: 1 },
  "Finished Good":    { warehouse_type: "Finished Goods",     valuation: "FIFO",           is_stock: 1 },
  "Packing Material": { warehouse_type: "Raw Material Store", valuation: "FIFO",           is_stock: 1 },
  "Product":          { warehouse_type: "",                   valuation: "FIFO",           is_stock: 1 },
  "Service":          { warehouse_type: "",                   valuation: "FIFO",           is_stock: 0 },
};
const VAL_METHODS     = ["FIFO", "Moving Average", "LIFO"];

const leafGroupOptions = computed(() =>
  itemGroupsFull.value.filter(g => !g.is_group).map(g => ({ value: g.name, label: g.name }))
);

async function load() {
  loading.value = true;
  try {
    const rows = await apiList("Item", {
      fields: ["name","item_code","item_name","item_group","item_type","stock_uom","standard_rate","standard_buying_rate","disabled","is_stock_item","has_variants","variant_of","creation","default_bom","quality_inspection_required","inspection_required_before_purchase","inspection_required_before_delivery","inspection_required_before_manufacture","min_order_qty","lead_time_days"],
      order: "item_name asc", limit: 500,
    });
    list.value = rows || [];
  } catch { list.value = []; }
  try {
    const g = await apiList("Item Group", { fields: ["name", "is_group"], order: "name asc", limit: 200 });
    itemGroupsFull.value = g || [];
    itemGroups.value = (g || []).map((r) => r.name);
  } catch { itemGroups.value = ["Raw Materials", "Herbs & Botanicals", "Minerals & Bhasmas", "Oils & Fats", "WIP - Semi Finished", "Finished Goods - Capsules", "Finished Goods - Tablets", "Finished Goods - Oils", "Finished Goods - Churnam", "Finished Goods - Kashayam", "Finished Goods - Lehyam", "Packing Materials - Primary", "Packing Materials - Secondary", "Services"]; }
  try {
    const wh = await apiList("Warehouse", {
      fields: ["name", "warehouse_name", "warehouse_type"],
      filters: [["disabled", "=", 0]], order: "warehouse_name asc", limit: 200,
    });
    warehouses.value = (wh || []).map((r) => ({
      name: r.name,
      label: (r.warehouse_name || r.name) + (r.warehouse_type ? " (" + r.warehouse_type + ")" : ""),
    }));
  } catch { warehouses.value = []; }
  try {
    const tt = await apiList("Tax Template", {
      fields: ["name", "template_name"],
      filters: [["disabled", "=", 0]],
      order: "template_name asc", limit: 100,
    });
    taxTemplates.value = (tt || []).map((r) => ({ name: r.name, label: r.template_name || r.name }));
  } catch { taxTemplates.value = []; }
  try {
    const uoms = await apiList("UOM", { fields: ["name"], order: "name asc", limit: 200 });
    uomList.value = (uoms || []).map((r) => r.name);
  } catch { uomList.value = ["Nos", "Kg", "Ltr", "Mtr", "Box", "Pcs", "Set", "Dozen"]; }
  try {
    const brands = await apiList("Brand", { fields: ["name"], filters: [["disabled", "=", 0]], order: "name asc", limit: 200 });
    brandList.value = (brands || []).map((r) => r.name);
  } catch { brandList.value = []; }
  try {
    const company = await resolveCompany();
    await loadAccountLists(company);
    // First income / expense account becomes the default for new items
    defaultAccounts.value = {
      income:  incomeAccounts.value[0]?.value  || "",
      expense: expenseAccounts.value[0]?.value || "",
    };
  } catch { defaultAccounts.value = { income: "", expense: "" }; incomeAccounts.value = []; expenseAccounts.value = []; }
  loading.value = false;
}

async function reloadGroups() {
  try {
    const g = await apiList("Item Group", { fields: ["name", "is_group"], order: "name asc", limit: 200 });
    itemGroupsFull.value = g || [];
    itemGroups.value = (g || []).map(r => r.name);
  } catch {}
}

async function createItemGroup(name) {
  if (!name?.trim()) return;
  try {
    await apiSave({ doctype: "Item Group", name: name.trim(), parent_item_group: "All Item Groups", is_group: 0 });
    await reloadGroups();
    form.item_group = name.trim();
    toast("Group \"" + name.trim() + "\" created");
  } catch (e) { toast("Could not create group: " + e.message, "error"); }
}

// Load income- and expense-class leaf accounts into separate dropdown lists.
// This app's Account doctype has no root_type column, so filter by account_type
// directly (Income; Expense covers Cost of Goods Sold).
async function loadAccountLists(company) {
  const toOpts = (rows) => (rows || []).map((a) => ({ value: a.name, label: a.name }));

  const fetchByType = async (typeFilter, scopeCompany) => {
    const filters = [["is_group", "=", 0]];
    if (scopeCompany) filters.push(["company", "=", scopeCompany]);
    filters.push(typeFilter);
    return await apiList("Account", { fields: ["name"], filters, order: "name asc", limit: 500 });
  };

  const incomeFilter  = ["account_type", "=", "Income"];
  const expenseFilter = ["account_type", "in", ["Expense", "Cost of Goods Sold"]];

  let income  = await fetchByType(incomeFilter, company);
  let expense = await fetchByType(expenseFilter, company);

  // Fallback: the resolved company had no matching accounts at all (stale/
  // mismatched company on Books Settings vs. what the Chart of Accounts was
  // seeded with). Retry without the company filter rather than leaving the
  // dropdown permanently empty.
  if (!income.length && !expense.length) {
    income  = await fetchByType(incomeFilter, "");
    expense = await fetchByType(expenseFilter, "");
  }

  incomeAccounts.value  = toOpts(income);
  expenseAccounts.value = toOpts(expense);
}

async function reloadAccounts() {
  try { await loadAccountLists(await resolveCompany()); } catch {}
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

async function openView(row) {
  viewDoc.value = row;
  viewOpen.value = true;
  // Fetch full doc to fill in any extra fields
  try {
    const full = await apiGET("zoho_books_clone.api.docs.get_doc", { doctype: "Item", name: row.name });
    if (full) viewDoc.value = { ...row, ...full };
  } catch {}
}

// Fetch active, submitted BOMs whose Production Item is this item, for the
// Default BOM picker. Only meaningful once the item exists (edit mode).
async function loadBomOptionsForItem(itemName) {
  if (!itemName) { bomOptions.value = []; return; }
  try {
    const r = await apiList("BOM", {
      fields: ["name", "item", "is_active", "is_default", "docstatus"],
      filters: [["item", "=", itemName], ["is_active", "=", 1], ["docstatus", "=", 1]],
      limit: 100, order: "is_default desc, modified desc",
    });
    bomOptions.value = r || [];
  } catch { bomOptions.value = []; }
}

// Keep the Default BOM picker's options in sync if the user flips item_type
// while the drawer is open (e.g. corrects a mis-set type mid-edit).
watch(() => form.item_type, (t) => {
  if (drawerMode.value === "edit" && (t === "Finished Good" || t === "Work In Progress")) {
    loadBomOptionsForItem(form.name);
  } else {
    bomOptions.value = [];
    form.default_bom = "";
  }
});

function applyTypeDefaults(type) {
  const d = ITEM_TYPE_DEFAULTS[type] || {};
  // Set is_stock_item
  form.is_stock_item = d.is_stock !== undefined ? d.is_stock : 1;
  // Set valuation method
  if (d.valuation) form.valuation_method = d.valuation;
  // Auto-select first matching warehouse if warehouse_type hint given
  if (d.warehouse_type && warehouses.value.length) {
    const match = warehouses.value.find(w => (w.label || "").toLowerCase().includes(d.warehouse_type.toLowerCase()));
    if (match) form.default_warehouse = match.name;
  }
}

function openAdd(presetType) {
  drawerMode.value = "add"; drawerTab.value = "basic";
  const defaultType = presetType || "Raw Material";
  const d = ITEM_TYPE_DEFAULTS[defaultType] || {};
  Object.assign(form, {
    name: "", item_code: "", item_name: "", item_group: "", item_type: defaultType,
    stock_uom: "Nos", hsn_code: "", description: "", disabled: 0, brand: "",
    standard_rate: 0, standard_buying_rate: 0, gst_rate: 18, tax_code: "",
    income_account:  defaultAccounts.value.income,
    expense_account: defaultAccounts.value.expense,
    is_stock_item: d.is_stock !== undefined ? d.is_stock : 1,
    has_batch_no: 0,
    shelf_life_in_days: 0,
    valuation_method: d.valuation || "FIFO",
    default_warehouse: "",
    reorder_level: 0, reorder_qty: 0, opening_stock: 0,
    default_bom: "", quality_inspection_required: 0, min_order_qty: 0, lead_time_days: 0,
    inspection_required_before_purchase: 0, inspection_required_before_delivery: 0,
    inspection_required_before_manufacture: 0,
  });
  // Auto-select warehouse matching type
  if (d.warehouse_type && warehouses.value.length) {
    const match = warehouses.value.find(w => (w.label || "").toLowerCase().includes(d.warehouse_type.toLowerCase()));
    if (match) form.default_warehouse = match.name;
  }
  bomOptions.value = [];
  variantAttrs.value = [];
  showDrawer.value = true;
}

async function openEdit(row) {
  drawerMode.value = "edit"; drawerTab.value = "basic";
  Object.assign(form, {
    ...row,
    hsn_code: "", description: "", standard_buying_rate: 0, brand: "",
    tax_code: "", income_account: "", expense_account: "",
    valuation_method: "FIFO", default_warehouse: "",
    reorder_level: 0, reorder_qty: 0, opening_stock: 0,
  });
  variantAttrs.value = [];
  showDrawer.value = true;
  try {
    const full = await apiGET("zoho_books_clone.api.docs.get_doc", { doctype: "Item", name: row.name });
    Object.assign(form, {
      hsn_code:             full.hsn_code             || "",
      description:          full.description          || "",
      standard_rate:        flt(full.standard_rate),
      standard_buying_rate: flt(full.standard_buying_rate),
      tax_code:             full.tax_code             || "",
      income_account:       full.income_account       || defaultAccounts.value.income,
      expense_account:      full.expense_account      || defaultAccounts.value.expense,
      is_stock_item:        full.is_stock_item ? 1 : 0,
      has_batch_no:         full.has_batch_no ? 1 : 0,
      shelf_life_in_days:   flt(full.shelf_life_in_days),
      valuation_method:     full.valuation_method     || "FIFO",
      default_warehouse:    full.default_warehouse    || "",
      reorder_level:        flt(full.reorder_level),
      reorder_qty:          flt(full.reorder_qty),
      opening_stock:        flt(full.opening_stock),
      disabled:             full.disabled ? 1 : 0,
      brand:                full.brand                || "",
      has_variants:         full.has_variants ? 1 : 0,
      default_bom:                 full.default_bom                 || "",
      quality_inspection_required: full.quality_inspection_required ? 1 : 0,
      inspection_required_before_purchase:    full.inspection_required_before_purchase    ? 1 : 0,
      inspection_required_before_delivery:    full.inspection_required_before_delivery    ? 1 : 0,
      inspection_required_before_manufacture: full.inspection_required_before_manufacture ? 1 : 0,
      min_order_qty:                flt(full.min_order_qty),
      lead_time_days:                full.lead_time_days ? parseInt(full.lead_time_days) : 0,
    });
    // Load BOM options for the picker now that we know the item's name/type.
    if (full.item_type === "Finished Good" || full.item_type === "Work In Progress") {
      loadBomOptionsForItem(row.name);
    } else {
      bomOptions.value = [];
    }
    // Rebuild the variant attribute builder: group stored rows by attribute.
    const groups = {};
    for (const r of (full.attributes || [])) {
      if (!r.attribute) continue;
      (groups[r.attribute] = groups[r.attribute] || []);
      if (r.attribute_value && !groups[r.attribute].includes(r.attribute_value)) groups[r.attribute].push(r.attribute_value);
    }
    variantAttrs.value = Object.entries(groups).map(([attribute, vals]) => ({ attribute, valuesText: vals.join(", ") }));
  } catch (e) { toast("Could not load full item details: " + e.message, "error"); }
}

// Required-field guard. Each entry: [is-invalid, message, tab to reveal].
function validateItem() {
  const checks = [
    [!form.item_name.trim(),                         "Item name is required",        "basic"],
    [!form.stock_uom,                                "Default UOM is required",      "basic"],
    [!form.tax_code,                                 "Tax Template is required",     "pricing"],
    [!form.income_account,                           "Income account is required",   "pricing"],
    [!form.expense_account,                          "Expense account is required",  "pricing"],
    [!!form.is_stock_item && !form.default_warehouse, "Default Warehouse is required when Track Inventory is on", "inventory"],
  ];
  for (const [bad, msg, tab] of checks) {
    if (bad) { drawerTab.value = tab; toast(msg, "error"); return false; }
  }
  return true;
}

async function saveItem({ close = true } = {}) {
  if (!validateItem()) return null;
  saving.value = true;
  try {
    const isEdit = drawerMode.value === "edit";
    const itemCode = form.item_code || form.item_name;
    const openingQty = flt(form.opening_stock);
    const openingRate = flt(form.standard_buying_rate) || flt(form.standard_rate) || 0;

    // Flatten the variant builder into Item Variant Attribute rows.
    const attributes = [];
    if (form.has_variants) {
      for (const a of variantAttrs.value) {
        if (!a.attribute) continue;
        for (const val of splitValues(a.valuesText)) attributes.push({ doctype: "Item Variant Attribute", attribute: a.attribute, attribute_value: val });
      }
    }

    const doc = {
      doctype: "Item", item_name: form.item_name, item_code: itemCode,
      item_group: form.item_group || "Products", item_type: form.item_type, stock_uom: form.stock_uom,
      hsn_code: form.hsn_code, description: form.description, disabled: form.disabled ? 1 : 0, brand: form.brand || "",
      standard_rate: flt(form.standard_rate), standard_buying_rate: flt(form.standard_buying_rate),
      tax_code: form.tax_code,
      income_account: form.income_account, expense_account: form.expense_account,
      is_stock_item: form.is_stock_item ? 1 : 0, has_batch_no: form.is_stock_item ? (form.has_batch_no ? 1 : 0) : 0,
      shelf_life_in_days: (form.is_stock_item && form.has_batch_no) ? flt(form.shelf_life_in_days) : 0,
      valuation_method: form.valuation_method,
      default_warehouse: form.default_warehouse, reorder_level: flt(form.reorder_level),
      reorder_qty: flt(form.reorder_qty), opening_stock: openingQty,
      has_variants: form.has_variants ? 1 : 0, attributes,
      default_bom: (form.item_type === "Finished Good" || form.item_type === "Work In Progress") ? (form.default_bom || "") : "",
      inspection_required_before_purchase:    form.inspection_required_before_purchase    ? 1 : 0,
      inspection_required_before_delivery:    form.inspection_required_before_delivery    ? 1 : 0,
      inspection_required_before_manufacture: form.inspection_required_before_manufacture ? 1 : 0,
      // Legacy field kept in sync (OR of the three) so any older reports/filters relying on it still work.
      quality_inspection_required: (form.inspection_required_before_purchase || form.inspection_required_before_delivery || form.inspection_required_before_manufacture) ? 1 : 0,
      min_order_qty: flt(form.min_order_qty),
      lead_time_days: form.lead_time_days ? parseInt(form.lead_time_days) : 0,
    };
    if (isEdit) doc.name = form.name;
    const saved = await apiSave(doc);
    const savedName = saved?.name || form.name || itemCode;
    form.name = savedName;

    // Opening stock is posted only when the item is first created — re-posting
    // on every edit would keep adding a Material Receipt and inflate inventory.
    if (!isEdit && form.is_stock_item && openingQty > 0 && form.default_warehouse) {
      try {
        const res = await apiPOST("zoho_books_clone.api.inventory.create_opening_stock", {
          item_code: savedName,
          item_name: form.item_name,
          warehouse: form.default_warehouse,
          qty: openingQty,
          rate: openingRate,
        });
        toast("Stock entry " + res.stock_entry + " created: +" + openingQty + " in " + form.default_warehouse);
      } catch (seErr) {
        toast("Item saved but stock entry failed: " + seErr.message, "error");
      }
    }

    await load();
    if (close) {
      toast(isEdit ? "Item updated" : "Item created");
      showDrawer.value = false;
    } else {
      // Keep the drawer open in edit mode (variant generation flow).
      drawerMode.value = "edit";
    }
    return savedName;
  } catch (e) { toast("Save failed: " + e.message, "error"); return null; }
  finally { saving.value = false; }
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

onMounted(() => { load(); loadAttributeOptions(); window.addEventListener("hashchange", onHashChange); });
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

/* ══════════════════════════════════════
   Add / Edit Drawer  (ad-*)
══════════════════════════════════════ */
.ad-backdrop {
  position: fixed; inset: 0;
  background: rgba(15,23,42,.45);
  backdrop-filter: blur(2px);
  z-index: 900;
}
.ad-panel {
  position: fixed; top: 0; right: 0; bottom: 0;
  width: 520px; max-width: 100vw;
  background: #fff; z-index: 901;
  display: flex; flex-direction: column;
  box-shadow: -8px 0 40px rgba(15,23,42,.14);
  transform: translateX(100%);
  transition: transform .26s cubic-bezier(.4,0,.2,1);
}
.ad-panel--open { transform: translateX(0); }

/* Header */
.ad-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 20px; background: #fff;
  border-bottom: 1px solid #f1f5f9; flex-shrink: 0; gap: 12px;
}
.ad-header-left { display: flex; align-items: center; gap: 14px; min-width: 0; }
.ad-avatar {
  width: 42px; height: 42px; border-radius: 12px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.ad-avatar--add { background: linear-gradient(135deg,#eff6ff,#dbeafe); border: 1.5px solid #bfdbfe; color: #2563eb; }
.ad-avatar--edit { background: linear-gradient(135deg,#f5f3ff,#ede9fe); border: 1.5px solid #ddd6fe; color: #7c3aed; }
.ad-title { font-size: 15px; font-weight: 700; color: #0f172a; letter-spacing: -.01em; }
.ad-subtitle { font-size: 12px; color: #94a3b8; margin-top: 2px; font-weight: 500; }
.ad-close {
  width: 32px; height: 32px; border-radius: 8px; flex-shrink: 0;
  background: #f8fafc; border: 1.5px solid #e2e8f0; cursor: pointer; color: #64748b;
  display: flex; align-items: center; justify-content: center;
  transition: background .12s, color .12s;
}
.ad-close:hover { background: #f1f5f9; color: #0f172a; }

/* Tabs */
.ad-tabs {
  display: flex; gap: 0;
  background: #f8fafc; border-bottom: 1px solid #e9edf2; flex-shrink: 0;
  overflow-x: auto; padding: 0 20px;
}
.ad-tab {
  padding: 11px 16px; font-size: 13px; font-weight: 600; border: none;
  background: transparent; cursor: pointer; color: #94a3b8; white-space: nowrap;
  border-bottom: 2px solid transparent; margin-bottom: -1px;
  transition: color .15s, border-color .15s;
}
.ad-tab:hover { color: #374151; }
.ad-tab--active { color: #2563eb; border-bottom-color: #2563eb; background: transparent; }

/* Body */
.ad-body {
  flex: 1; overflow-y: auto; background: #f8fafc;
  padding: 20px; display: flex; flex-direction: column; gap: 14px;
}

/* Sections */
.ad-section {
  background: #fff; border: 1px solid #e9edf2; border-radius: 12px;
  padding: 16px 18px; display: flex; flex-direction: column; gap: 14px;
  box-shadow: 0 1px 3px rgba(15,23,42,.04);
}
.ad-section-title {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .07em; color: #94a3b8; padding-bottom: 2px;
  border-bottom: 1px solid #f1f5f9; margin-bottom: -4px;
}

/* Fields */
.ad-field { display: flex; flex-direction: column; gap: 5px; }
.ad-label {
  font-size: 12px; font-weight: 600; color: #374151;
  display: flex; align-items: center; gap: 6px;
}
.ad-required { color: #dc2626; font-size: 13px; line-height: 1; }
.ad-hint {
  font-size: 10.5px; font-weight: 500; color: #94a3b8;
  background: #f1f5f9; padding: 1px 6px; border-radius: 4px; letter-spacing: .02em;
}
.ad-input {
  width: 100%; padding: 8px 11px; font-size: 13px; color: #1e293b;
  border: 1.5px solid #e2e8f0; border-radius: 8px; background: #fff;
  outline: none; transition: border-color .15s, box-shadow .15s;
  font-family: inherit; box-sizing: border-box;
}
.ad-input:focus { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,.1); }
.ad-input::placeholder { color: #c4cad4; }
.ad-textarea { resize: vertical; min-height: 80px; }

/* Prefix input */
.ad-input-prefix-wrap { position: relative; display: flex; align-items: center; }
.ad-input-prefix {
  position: absolute; left: 11px; font-size: 13px; font-weight: 600;
  color: #64748b; pointer-events: none; z-index: 1;
}
.ad-input--prefixed { padding-left: 26px; }

/* 2-col grid */
.ad-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

/* Item type selector */
.ad-type-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 8px;
}
.ad-type-btn {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 12px 10px; border: 1.5px solid #e2e8f0; border-radius: 10px;
  background: #f8fafc; cursor: pointer; transition: all .14s; font-family: inherit;
}
.ad-type-btn:hover { border-color: #93c5fd; background: #eff6ff; }
.ad-type-btn--active {
  border-color: #2563eb; background: #eff6ff;
  box-shadow: 0 0 0 3px rgba(37,99,235,.1);
}
.ad-type-icon { font-size: 20px; line-height: 1; }
.ad-type-label { font-size: 12px; font-weight: 600; color: #374151; }
.ad-type-btn--active .ad-type-label { color: #1d4ed8; }

/* Type info strip */
.ad-type-info-strip {
  margin-top: 10px; padding: 8px 12px; border-radius: 8px;
  font-size: 12px; font-weight: 500; line-height: 1.4;
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

/* Toggle row */
.ad-toggle-row {
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
  background: #fff; border: 1px solid #e9edf2; border-radius: 12px;
  padding: 14px 18px; box-shadow: 0 1px 3px rgba(15,23,42,.04);
}
.ad-toggle-left { flex: 1; min-width: 0; }
.ad-toggle-title { font-size: 13px; font-weight: 600; color: #1e293b; }
.ad-toggle-sub { font-size: 11.5px; color: #94a3b8; margin-top: 2px; }

/* Toggle switch */
.ad-switch { position: relative; display: inline-block; width: 40px; height: 22px; flex-shrink: 0; cursor: pointer; }
.ad-switch input { opacity: 0; width: 0; height: 0; }
.ad-switch-track {
  position: absolute; inset: 0; border-radius: 22px;
  background: #e2e8f0; transition: background .2s;
}
.ad-switch-track::after {
  content: ''; position: absolute; top: 3px; left: 3px;
  width: 16px; height: 16px; border-radius: 50%; background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,.15); transition: transform .2s;
}
.ad-switch input:checked + .ad-switch-track { background: #dc2626; }
.ad-switch-track--green.ad-switch-track { }
.ad-switch input:checked + .ad-switch-track--green { background: #16a34a; }
.ad-switch input:checked + .ad-switch-track::after { transform: translateX(18px); }

/* Info banner */
.ad-info-banner {
  display: flex; align-items: flex-start; gap: 8px;
  background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 10px;
  padding: 12px 14px; font-size: 12px; color: #1e40af; line-height: 1.6;
  word-break: normal; overflow-wrap: anywhere;
}
.ad-info-banner svg { flex-shrink: 0; margin-top: 2px; }

/* Empty state */
.ad-empty-state {
  flex: 1; display: flex; flex-direction: column; align-items: center;
  justify-content: center; text-align: center; padding: 60px 20px;
}
.ad-empty-icon { font-size: 40px; margin-bottom: 14px; }
.ad-empty-title { font-size: 15px; font-weight: 700; color: #1e293b; margin-bottom: 6px; }
.ad-empty-sub { font-size: 13px; color: #94a3b8; max-width: 260px; line-height: 1.5; }
.ad-empty-badge {
  margin-top: 14px; display: inline-block; padding: 4px 12px; border-radius: 20px;
  background: #f1f5f9; color: #94a3b8; font-size: 11.5px; font-weight: 600; letter-spacing: .04em;
}

.it-tpl-badge { margin-left:7px; padding:1px 7px; border-radius:11px; font-size:10px; font-weight:700; background:#eef2ff; color:#4f46e5; vertical-align:middle; }
.it-tpl-badge--link { cursor:pointer; }
.it-tpl-badge--link:hover { background:#4f46e5; color:#fff; }
.it-var-badge { margin-left:7px; padding:1px 7px; border-radius:11px; font-size:10px; font-weight:700; background:#f0fdf4; color:#16a34a; vertical-align:middle; }

/* Variant Manager CTA (drawer) */
.vr-manage-cta { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:16px 18px; background:#f8fafc; border:1px solid #eef2f7; border-radius:12px; }
.vr-manage-title { font-size:14px; font-weight:700; color:#111827; margin-bottom:4px; }
.vr-manage-sub { font-size:12.5px; color:#64748b; line-height:1.45; }

/* Variants tab */
.vr-add-attr { display:inline-flex; align-items:center; gap:5px; border:1px solid #e2e8f0; background:#fff; border-radius:7px; padding:4px 10px; font-size:12px; font-weight:600; color:#2563eb; cursor:pointer; font-family:inherit; }
.vr-add-attr:hover { background:#eff6ff; }
.vr-hint { font-size:12.5px; color:#94a3b8; padding:6px 0; }
.vr-attr-row { display:flex; gap:8px; align-items:center; margin-bottom:8px; }
.vr-attr-name { flex:0 0 170px; }
.vr-attr-vals { flex:1; }
.vr-attr-del { border:none; background:none; cursor:pointer; color:#dc2626; padding:4px; display:flex; align-items:center; }
.vr-gen-bar { display:flex; align-items:center; justify-content:space-between; gap:12px; margin:14px 0 6px; padding:12px 14px; background:#f8fafc; border:1px solid #eef2f7; border-radius:10px; }
.vr-gen-count { font-size:12.5px; font-weight:600; color:#475569; }
.vr-item { display:flex; align-items:center; justify-content:space-between; padding:10px 12px; border:1px solid #f1f5f9; border-radius:9px; margin-bottom:8px; }
.vr-item-code { font-size:13px; font-weight:600; color:#111827; }
.vr-item-attrs { font-size:11.5px; color:#94a3b8; margin-top:2px; }
.vr-item-rate { font-size:13px; font-weight:700; color:#16a34a; }

/* Footer */
.ad-footer {
  padding: 14px 20px; border-top: 1px solid #f1f5f9;
  display: flex; justify-content: flex-end; gap: 8px;
  background: #fff; flex-shrink: 0;
}
.ad-btn-ghost {
  padding: 9px 18px; border-radius: 8px; font-size: 13px; font-weight: 600;
  border: 1.5px solid #e2e8f0; background: #fff; color: #374151;
  cursor: pointer; transition: background .12s, border-color .12s;
}
.ad-btn-ghost:hover { background: #f8fafc; border-color: #cbd5e1; }
.ad-btn-primary {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 9px 20px; border-radius: 8px; font-size: 13px; font-weight: 600;
  background: #2563eb; color: #fff; border: none; cursor: pointer;
  transition: background .12s, transform .1s; box-shadow: 0 1px 4px rgba(37,99,235,.25);
}
.ad-btn-primary:hover:not(:disabled) { background: #1d4ed8; transform: translateY(-1px); }
.ad-btn-primary:active { transform: translateY(0); }
.ad-btn-primary:disabled { opacity: .65; cursor: not-allowed; transform: none; }

/* Spinner animation */
@keyframes ad-spin { to { transform: rotate(360deg); } }
.ad-spinner { animation: ad-spin .8s linear infinite; }

@media (max-width: 540px) {
  .ad-panel { width: 100vw; }
  .ad-grid-2 { grid-template-columns: 1fr; }
  .ad-type-grid { grid-template-columns: 1fr 1fr; }
}
</style>