<template>
<div class="wh-page">

  <!-- ════════════════════════════════════════════
       TOOLBAR
       ════════════════════════════════════════════ -->
  <!-- Backdrop to close filter dropdown -->
  <div v-if="filterDDOpen" class="wh-dd-backdrop" @click="filterDDOpen = false"></div>

  <div class="wh-toolbar">

    <!-- Group dropdown -->
    <div class="wh-group-wrap">
      <span class="wh-group-prefix">Group</span>
      <div class="wh-group-select-wrap">
        <select v-model="selectedGroupName" class="wh-group-select">
          <option value="">— Select group —</option>
          <option v-for="g in groups" :key="g.name" :value="g.name">
            {{ whMeta(g.warehouse_type).icon }} {{ g.warehouse_name || g.name }}
          </option>
        </select>
        <span class="wh-group-chev" v-html="icon('chevD', 12)"></span>
      </div>
    </div>

    <!-- Filter dropdown -->
    <div class="wh-filter-dd-wrap">
      <button class="wh-filter-dd-btn" :class="{ 'wh-filter-dd-btn--active': filterType !== 'All' }" @click="filterDDOpen = !filterDDOpen">
        <span>{{ filterType === 'All' ? 'All Types' : whMeta(filterType).icon + ' ' + filterType }}</span>
        <span class="wh-filter-dd-chev" :class="{ 'wh-filter-dd-chev--open': filterDDOpen }" v-html="icon('chevD', 11)"></span>
      </button>
      <div v-if="filterDDOpen" class="wh-filter-dd-menu">
        <div
          v-for="t in ['All', ...WH_TYPES]" :key="t"
          class="wh-filter-dd-item" :class="{ 'wh-filter-dd-item--active': filterType === t }"
          @click="filterType = t; filterDDOpen = false"
        >
          <span class="wh-filter-dd-icon">{{ t === 'All' ? '🏭' : whMeta(t).icon }}</span>
          <span>{{ t === 'All' ? 'All Types' : t }}</span>
          <span v-if="filterType === t" class="wh-filter-dd-check" v-html="icon('check', 13)"></span>
        </div>
      </div>
    </div>

    <!-- View toggle pill -->
    <div class="wh-view-toggle">
      <button class="wh-vt-btn" :class="{ 'wh-vt-btn--active': viewMode === 'cards' }" @click="viewMode = 'cards'">
        <span v-html="icon('grid', 13)"></span><span class="wh-btn-label"> Cards</span>
      </button>
      <button class="wh-vt-btn" :class="{ 'wh-vt-btn--active': viewMode === 'tree' }" @click="viewMode = 'tree'">
        <span v-html="icon('list', 13)"></span><span class="wh-btn-label"> Tree</span>
      </button>
    </div>

    <!-- Spacer -->
    <div style="flex:1"></div>

    <!-- Actions + search (right side) -->
    <div class="wh-tb-actions">
      <button class="wh-action-btn" @click="load">
        <span v-html="icon('refresh', 14)"></span>
      </button>
      <button class="wh-action-btn wh-action-btn--primary" @click="openAddChild">
        <span v-html="icon('plus', 13)"></span><span class="wh-btn-label"> New Warehouse</span>
      </button>
    </div>

    <!-- Search (right corner) -->
    <div class="wh-tb-search-wrap">
      <span v-html="icon('search')" class="wh-tb-search-icon"></span>
      <input v-model="search" class="wh-tb-search-input" placeholder="Search…" />
    </div>

  </div>

  <!-- ════════════════════════════════════════════
       MAIN CONTENT (scrollable)
       ════════════════════════════════════════════ -->
  <div class="wh-layout" :class="{ 'wh-layout--tree': viewMode === 'tree' }">

  <!-- ── Tree Sidebar ── -->
  <div v-if="viewMode === 'tree'" class="wh-tree-panel">
    <div class="wh-tree-head">
      <span class="wh-tree-head-icon">🌳</span>
      <span>Warehouse Tree</span>
      <button class="wh-tree-expand-all" @click="toggleAllTree">
        {{ treeAllExpanded ? 'Collapse All' : 'Expand All' }}
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="wh-tree-loading">
      <div v-for="i in 5" :key="i" class="b-shimmer" style="height:36px;border-radius:8px;margin-bottom:4px"></div>
    </div>

    <!-- Tree nodes -->
    <div v-else class="wh-tree-body">
      <template v-for="node in treeRoots" :key="node.name">
        <!-- Root / Group node -->
        <div
          class="wh-tree-node wh-tree-node--group"
          :class="{ 'wh-tree-node--selected': selectedWH?.name === node.name }"
          @click="treeSelectGroup(node)"
        >
          <span
            class="wh-tree-caret"
            :class="{ 'wh-tree-caret--open': treeExpanded[node.name] }"
            @click.stop="toggleNode(node.name)"
            v-html="icon('chevD', 11)"
          ></span>
          <span class="wh-tree-node-icon" :style="{ background: whMeta(node.warehouse_type).bg }">
            {{ whMeta(node.warehouse_type).icon }}
          </span>
          <span class="wh-tree-node-label">{{ node.warehouse_name || node.name }}</span>
          <span v-if="treeChildren(node.name).length" class="wh-tree-badge">
            {{ treeChildren(node.name).length }}
          </span>
          <span v-if="node.disabled" class="wh-tree-off">off</span>
        </div>

        <!-- Children (shown when expanded) -->
        <template v-if="treeExpanded[node.name]">
          <div
            v-for="child in treeChildren(node.name)"
            :key="child.name"
            class="wh-tree-node wh-tree-node--child"
            :class="{
              'wh-tree-node--selected': selectedChild?.name === child.name,
              'wh-tree-node--disabled': child.disabled
            }"
            @click="treeSelectChild(node, child)"
          >
            <span class="wh-tree-node-icon wh-tree-node-icon--sm" :style="{ background: whMeta(child.warehouse_type).bg }">
              {{ whMeta(child.warehouse_type).icon }}
            </span>
            <span class="wh-tree-node-label">{{ child.warehouse_name || child.name }}</span>
            <span v-if="child.disabled" class="wh-tree-off">off</span>
          </div>
          <!-- No children empty hint -->
          <div v-if="!treeChildren(node.name).length" class="wh-tree-empty-child">
            <span>No warehouses</span>
            <button class="wh-tree-add-btn" @click.stop="treeOpenAddChild(node)">+ Add</button>
          </div>
        </template>
      </template>

      <!-- Completely empty -->
      <div v-if="!treeRoots.length" class="wh-tree-empty">
        <div style="font-size:28px;margin-bottom:6px">🏭</div>
        <div style="font-size:12px;color:#94a3b8">No warehouse groups yet</div>
        <button class="wh-action-btn wh-action-btn--primary" style="margin-top:10px;font-size:12px" @click="openAddGroup">+ Create Group</button>
      </div>
    </div>

    <!-- Tree footer actions -->
    <div class="wh-tree-footer">
      <button class="wh-action-btn wh-action-btn--primary" style="width:100%;justify-content:center" @click="openAddGroup">
        <span v-html="icon('plus', 12)"></span> New Warehouse Group
      </button>
    </div>
  </div>

  <div class="wh-content">

    <!-- No groups exist at all -->
    <div v-if="!loading && !groups.length" class="wh-empty-state">
      <div class="wh-empty-icon">🏭</div>
      <div class="wh-empty-title">No warehouse groups yet</div>
      <div class="wh-empty-sub">Create a group warehouse first to start organizing stock</div>
      <button class="wh-action-btn wh-action-btn--primary" style="margin-top:18px" @click="openAddGroup">
        <span v-html="icon('plus', 13)"></span> Create Warehouse Group
      </button>
    </div>

    <!-- No group selected -->
    <div v-else-if="!selectedWH && !loading" class="wh-empty-state">
      <div class="wh-empty-icon">👆</div>
      <div class="wh-empty-title">Select a warehouse group</div>
      <div class="wh-empty-sub">Choose a group from the dropdown above</div>
    </div>

    <template v-else-if="selectedWH">

      <!-- ── Section header ── -->
      <div class="wh-section-header">
        <div class="wh-section-title">
          <span>{{ whMeta(selectedWH.warehouse_type).icon }}</span>
          {{ selectedWH.warehouse_name || selectedWH.name }}
          <span v-if="childWarehouses.length" class="wh-stock-count">{{ childWarehouses.length }}</span>
        </div>
        <div style="display:flex;gap:8px;align-items:center">
          <button class="wh-action-btn" @click="openEdit(selectedWH)">
            <span v-html="icon('edit', 13)"></span> Edit Group
          </button>
          <button class="wh-action-btn wh-action-btn--danger" @click="confirmDel(selectedWH)">
            <span v-html="icon('trash', 13)"></span>
          </button>
        </div>
      </div>

      <!-- ── Loading shimmer ── -->
      <div v-if="loading" class="wh-cards-grid wh-cards-gap">
        <div v-for="i in 4" :key="i" class="wh-card-shimmer">
          <div class="b-shimmer" style="height:44px;width:44px;border-radius:12px;flex-shrink:0"></div>
          <div style="flex:1">
            <div class="b-shimmer" style="height:16px;border-radius:4px;margin-bottom:8px;width:75%"></div>
            <div class="b-shimmer" style="height:12px;border-radius:4px;width:50%"></div>
          </div>
        </div>
      </div>

      <!-- ── No children ── -->
      <div v-else-if="!childWarehouses.length" class="wh-no-children">
        <div style="font-size:32px;margin-bottom:8px">🏭</div>
        <div style="font-size:14px;font-weight:700;color:#334155;margin-bottom:4px">No warehouses in this group</div>
        <div style="font-size:13px;color:#94a3b8;margin-bottom:14px">Add a warehouse to start tracking stock</div>
        <button class="wh-action-btn wh-action-btn--primary" @click="openAddChild">
          <span v-html="icon('plus', 13)"></span> Add Warehouse
        </button>
      </div>

      <!-- ── Child warehouse cards ── -->
      <div v-else class="wh-cards-grid wh-cards-gap">
        <div
          v-for="child in childWarehouses" :key="child.name"
          class="wh-card"
          :class="{
            'wh-card--active':   selectedChild?.name === child.name,
            'wh-card--disabled': child.disabled
          }"
          @click="selectChild(child)"
        >
          <div class="wh-card-top">
            <div class="wh-card-icon" :style="{ background: whMeta(child.warehouse_type).bg }">
              {{ whMeta(child.warehouse_type).icon }}
            </div>
            <div class="wh-card-info">
              <div class="wh-card-name">{{ child.warehouse_name || child.name }}</div>
              <div class="wh-card-meta">
                <span v-if="child.city" class="wh-card-city">📍 {{ child.city }}{{ child.state ? ', ' + child.state : '' }}</span>
              </div>
            </div>
            <div class="wh-card-right">
              <span class="wh-badge"
                :style="{ background: whMeta(child.warehouse_type).bg, color: whMeta(child.warehouse_type).color }">
                {{ child.warehouse_type || 'Stores' }}
              </span>
              <span v-if="child.is_group" class="wh-badge wh-badge-blue">Group</span>
              <span v-if="child.disabled" class="wh-badge wh-badge-red">Off</span>
            </div>
          </div>
          <div class="wh-card-footer wh-card-footer--actions" @click.stop>
            <button
              class="wh-adj-btn"
              :class="{ 'wh-adj-btn--active': selectedChild?.name === child.name }"
              @click="openNewAdjustment(child)"
            >
              <span v-html="icon('plus', 11)"></span> Add Stock
            </button>
            <button v-if="!child.is_group" class="wh-action-btn" style="padding:5px 10px" @click="openTransfer(child)" title="Transfer stock to another warehouse">
              <span v-html="icon('truck', 13)"></span>
            </button>
            <button class="wh-action-btn" style="padding:5px 10px" @click="openEdit(child)">
              <span v-html="icon('edit', 13)"></span>
            </button>
            <button class="wh-action-btn wh-action-btn--danger" style="padding:5px 10px" @click="confirmDel(child)">
              <span v-html="icon('trash', 13)"></span>
            </button>
          </div>
        </div>
      </div>

      <!-- ── Stock summary table ── -->
      <div class="wh-stock-section">

        <!-- Stats strip -->
        <div v-if="stockItems.length && !stockLoading" class="wh-stats-strip">
          <div class="wh-stat-chip wh-stat-chip--blue">
            <span class="wh-stat-chip-icon">💰</span>
            <div>
              <div class="wh-stat-chip-lbl">Total Value</div>
              <div class="wh-stat-chip-val">{{ fmt(whStats.value) }}</div>
            </div>
          </div>
          <div class="wh-stat-chip wh-stat-chip--green">
            <span class="wh-stat-chip-icon">📦</span>
            <div>
              <div class="wh-stat-chip-lbl">Items in Stock</div>
              <div class="wh-stat-chip-val">{{ whStats.items }}</div>
            </div>
          </div>
          <div class="wh-stat-chip wh-stat-chip--purple">
            <span class="wh-stat-chip-icon">📋</span>
              <div>
              <div class="wh-stat-chip-lbl">Ordered Qty</div>
              <div class="wh-stat-chip-val">{{ whStats.ordered.toFixed(2) }}</div>
            </div>
          </div>
          <div class="wh-stat-chip wh-stat-chip--orange">
            <span class="wh-stat-chip-icon">🔒</span>
            <div>
              <div class="wh-stat-chip-lbl">Reserved Qty</div>
              <div class="wh-stat-chip-val">{{ whStats.reserved.toFixed(2) }}</div>
            </div>
          </div>
          <div class="wh-stat-chip wh-stat-chip--indigo">
            <span class="wh-stat-chip-icon">📊</span>
            <div>
              <div class="wh-stat-chip-lbl">Projected Qty</div>
              <div class="wh-stat-chip-val">{{ whStats.projected.toFixed(2) }}</div>
            </div>
          </div>
        </div>

        <!-- Table header -->
        <div class="wh-stock-header">
          <div class="wh-stock-title">
            Stock Items
            <span v-if="selectedChild" class="wh-stock-scope">
              — {{ selectedChild.warehouse_name || selectedChild.name }}
            </span>
            <span v-else class="wh-stock-scope">— All ({{ selectedWH.warehouse_name || selectedWH.name }})</span>
            <span v-if="stockItems.length" class="wh-stock-count">{{ stockItems.length }}</span>
          </div>
          <div class="wh-stock-actions">
            <button v-if="selectedChild" class="wh-action-btn" @click="selectedChild = null; loadStockForWarehouse(selectedWH.name)">
              <span v-html="icon('x', 12)"></span> Clear
            </button>
            <button class="wh-action-btn" @click="loadStockForWarehouse(selectedChild?.name || selectedWH.name)">
              <span v-html="icon('refresh', 13)"></span>
            </button>
          </div>
        </div>

        <!-- Loading -->
        <div v-if="stockLoading" class="wh-stock-shimmer">
          <div class="b-shimmer" style="height:42px;border-radius:6px;margin-bottom:6px"></div>
          <div class="b-shimmer" style="height:42px;border-radius:6px;margin-bottom:6px"></div>
          <div class="b-shimmer" style="height:42px;border-radius:6px;margin-bottom:6px"></div>
          <div class="b-shimmer" style="height:42px;border-radius:6px"></div>
        </div>

        <!-- Empty -->
        <div v-else-if="!stockItems.length" class="wh-stock-empty">
          <div style="font-size:36px;margin-bottom:10px">📭</div>
          <div class="wh-stock-empty-title">No stock data</div>
          <div class="wh-stock-empty-sub">No stock found in this warehouse group yet</div>
        </div>

        <!-- Stock data: mobile cards + desktop table (toggled via CSS) -->
        <template v-else>
        <div class="wh-tbl-mobile">
          <div v-for="r in stockItems" :key="'mc-' + r.item_code" class="wh-stock-mc">
            <div class="wh-smc-top">
              <div class="wh-smc-name-wrap">
                <div class="wh-smc-name">{{ r.item_name }}</div>
                <div class="wh-smc-code">{{ r.item_code }}</div>
              </div>
              <span v-if="r.below_reorder" class="wh-status-low">⚠ Low</span>
              <span v-else class="wh-status-ok">✓ OK</span>
            </div>
            <div class="wh-smc-grid">
              <div class="wh-smc-cell">
                <div class="wh-smc-lbl">Actual Qty</div>
                <div class="wh-smc-val wh-smc-qty">{{ flt(r.actual_qty).toFixed(2) }}</div>
              </div>
              <div class="wh-smc-cell">
                <div class="wh-smc-lbl">Reserved</div>
                <div class="wh-smc-val wh-smc-reserved">{{ flt(r.reserved_qty).toFixed(2) }}</div>
              </div>
              <div class="wh-smc-cell">
                <div class="wh-smc-lbl">Ordered</div>
                <div class="wh-smc-val wh-smc-ordered">{{ flt(r.ordered_qty).toFixed(2) }}</div>
              </div>
              <div class="wh-smc-cell">
                <div class="wh-smc-lbl">Val. Rate</div>
                <div class="wh-smc-val">{{ fmt(r.valuation_rate) }}</div>
              </div>
              <div class="wh-smc-cell wh-smc-cell--value">
                <div class="wh-smc-lbl">Stock Value</div>
                <div class="wh-smc-val wh-smc-value">{{ fmt(r.stock_value) }}</div>
              </div>
            </div>
            <div class="wh-smc-footer">
              <span v-if="r.item_group" class="wh-smc-tag">{{ r.item_group }}</span>
              <span v-if="r.uom" class="wh-smc-tag">{{ r.uom }}</span>
              <button v-if="r.has_batch_no" class="wh-smc-batch-toggle" @click="toggleBatches(r.item_code)">
                {{ batchesFor(r.item_code).length }} batch{{ batchesFor(r.item_code).length===1?'':'es' }} {{ expandedRows[r.item_code] ? '▲' : '▼' }}
              </button>
              <button v-if="adjustTargetWH" class="wh-adj-btn wh-smc-adj" @click="openAdjustment(r)">
                <span v-html="icon('edit', 12)"></span> {{ r.has_batch_no ? 'Adjust Batches' : 'Adjust' }}
              </button>
            </div>
            <div v-if="r.has_batch_no && expandedRows[r.item_code]" class="wh-smc-batch-list">
              <div v-if="!batchesFor(r.item_code).length" class="wh-batch-empty">No batch-wise ledger entries yet</div>
              <div v-for="b in batchesFor(r.item_code)" :key="b.batch_no" class="wh-smc-batch-row">
                <div>
                  <div class="wh-batch-no">{{ b.batch_no }}</div>
                  <div class="wh-batch-date" style="margin-top:2px">{{ fmtBatchDate(b.manufacturing_date) }} → {{ fmtBatchDate(b.expiry_date) }}</div>
                </div>
                <div style="text-align:right">
                  <div class="wh-batch-qty">{{ flt(b.qty).toFixed(2) }}</div>
                  <span v-if="b.is_expired" class="wh-batch-flag wh-batch-flag--expired">Expired</span>
                  <span v-else-if="b.expires_soon" class="wh-batch-flag wh-batch-flag--soon">Soon</span>
                  <button v-if="adjustTargetWH" class="wh-adj-btn wh-smc-adj" style="margin-top:6px" @click.stop="openBatchAdjustment(r, b)">
                    <span v-html="icon('edit', 12)"></span> Adjust
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Desktop Table -->
        <div class="wh-tbl-wrap wh-tbl-desktop">
          <table class="wh-tbl">
            <thead>
              <tr>
                <th class="wh-th" style="width:24px"></th>
                <th class="wh-th">Item</th>
                <th class="wh-th wh-th-hide-sm">Group</th>
                <th class="wh-th wh-th-hide-sm">UOM</th>
                <th class="wh-th wh-th-r">Actual Qty</th>
                <th class="wh-th wh-th-r wh-th-hide-md">Reserved</th>
                <th class="wh-th wh-th-r wh-th-hide-md">Ordered</th>
                <th class="wh-th wh-th-r wh-th-hide-md">Val. Rate</th>
                <th class="wh-th wh-th-r">Stock Value</th>
                <th class="wh-th wh-th-c">Status</th>
                <th v-if="adjustTargetWH" class="wh-th wh-th-c">Adjust</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="r in stockItems" :key="r.item_code">
              <tr class="wh-tr" :class="{ 'wh-tr-clickable': r.has_batch_no }" @click="r.has_batch_no && toggleBatches(r.item_code)">
                <td class="wh-td wh-td-c">
                  <span v-if="r.has_batch_no" class="wh-expand-chevron" :class="{ 'wh-expand-chevron--open': expandedRows[r.item_code] }">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
                  </span>
                </td>
                <td class="wh-td">
                  <div class="wh-item-name">{{ r.item_name }}</div>
                  <div class="wh-item-code">{{ r.item_code }}</div>
                </td>
                <td class="wh-td wh-td-muted wh-th-hide-sm">{{ r.item_group || '—' }}</td>
                <td class="wh-td wh-td-muted wh-th-hide-sm">{{ r.uom || 'Nos' }}</td>
                <td class="wh-td wh-td-r wh-td-qty">{{ flt(r.actual_qty).toFixed(2) }}</td>
                <td class="wh-td wh-td-r wh-td-reserved wh-th-hide-md">{{ flt(r.reserved_qty).toFixed(2) }}</td>
                <td class="wh-td wh-td-r wh-td-ordered wh-th-hide-md">{{ flt(r.ordered_qty).toFixed(2) }}</td>
                <td class="wh-td wh-td-r wh-th-hide-md">{{ fmt(r.valuation_rate) }}</td>
                <td class="wh-td wh-td-r wh-td-value">{{ fmt(r.stock_value) }}</td>
                <td class="wh-td wh-td-c">
                  <span v-if="r.below_reorder" class="wh-status-low">⚠ Low</span>
                  <span v-else class="wh-status-ok">✓ OK</span>
                </td>
                <td v-if="adjustTargetWH" class="wh-td wh-td-c" @click.stop>
                  <button class="wh-adj-btn" @click="openAdjustment(r)">
                    <span v-html="icon('edit', 12)"></span> {{ r.has_batch_no ? 'Adjust Batches' : 'Adjust' }}
                  </button>
                </td>
              </tr>
              <tr v-if="r.has_batch_no && expandedRows[r.item_code]" class="wh-batch-row">
                <td :colspan="adjustTargetWH ? 10 : 9" style="padding:0">
                  <div class="wh-batch-panel">
                    <div v-if="!batchesFor(r.item_code).length" class="wh-batch-empty">No batch-wise ledger entries for this item yet</div>
                    <table v-else class="wh-batch-tbl">
                      <thead><tr>
                        <th>Batch No</th><th>Mfg Date</th><th>Expiry Date</th><th class="ta-r">Qty</th><th></th>
                        <th v-if="adjustTargetWH"></th>
                      </tr></thead>
                      <tbody>
                        <tr v-for="b in batchesFor(r.item_code)" :key="b.batch_no">
                          <td class="wh-batch-no">{{ b.batch_no }}</td>
                          <td class="wh-batch-date">{{ fmtBatchDate(b.manufacturing_date) }}</td>
                          <td class="wh-batch-date">{{ fmtBatchDate(b.expiry_date) }}</td>
                          <td class="wh-batch-qty">{{ flt(b.qty).toFixed(2) }}</td>
                          <td>
                            <span v-if="b.is_expired" class="wh-batch-flag wh-batch-flag--expired">Expired</span>
                            <span v-else-if="b.expires_soon" class="wh-batch-flag wh-batch-flag--soon">Expires soon</span>
                          </td>
                          <td v-if="adjustTargetWH" @click.stop>
                            <button class="wh-adj-btn" @click="openBatchAdjustment(r, b)">
                              <span v-html="icon('edit', 12)"></span> Adjust
                            </button>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </td>
              </tr>
              </template>
            </tbody>
          </table>
        </div>
        </template>
      </div>

    </template>
  </div>
  </div><!-- /.wh-layout -->

  <!-- ════════════════════════════════════════════
       TELEPORT: all modals
       ════════════════════════════════════════════ -->
  <Teleport to="body">

    <!-- ── Stock Adjustment drawer ── -->
    <div v-if="adjDrawer.open" class="nim-overlay" @click.self="adjDrawer.open=false">
      <div class="nim-dialog" style="width:480px">
        <div class="nim-dialog-header">
          <div>
            <div style="font-size:15px;font-weight:700;color:#1A1D23">{{ adjDrawer.batch_no ? 'Adjust Batch Stock' : 'Adjust Stock' }}</div>
            <div style="font-size:12px;color:#868E96;margin-top:2px">{{ adjDrawer.warehouse }}<span v-if="adjDrawer.batch_no"> · Batch {{ adjDrawer.batch_no }}</span></div>
          </div>
          <button class="nim-close" @click="adjDrawer.open=false">✕</button>
        </div>
        <div class="nim-dialog-body" style="display:flex;flex-direction:column;gap:16px">
          <div v-if="adjDrawer.pick_item">
            <label class="nim-label">Item <span style="color:#dc2626">*</span></label>
            <SearchableSelect v-model="adjDrawer.item_code" :options="allItems"
              value-key="name" label-key="item_name" placeholder="Search item to add stock…" />
          </div>
          <div v-if="adjDrawer.pick_item && adjDrawer.pickedHasBatch" style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:10px 14px;font-size:12.5px;color:#b91c1c">
            {{ adjDrawer.item_name }} is batch-tracked. This quick-add can't set a Batch No — use the
            <strong>Opening Stock</strong> or <strong>Stock Entries</strong> page to bring in stock with a batch.
          </div>
          <div v-if="adjDrawer.item_code" style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:12px 14px;display:flex;align-items:center;gap:14px">
            <div style="width:40px;height:40px;background:#eff6ff;border-radius:8px;display:flex;align-items:center;justify-content:center;flex-shrink:0" v-html="icon('box',18)"></div>
            <div>
              <div style="font-size:13.5px;font-weight:700;color:#111827">{{ adjDrawer.item_name }}</div>
              <div style="font-size:11.5px;color:#6b7280;margin-top:2px;">{{ adjDrawer.item_code }}</div>
            </div>
            <div style="margin-left:auto;text-align:right">
              <div style="font-size:11px;color:#9ca3af;text-transform:uppercase;letter-spacing:.04em">{{ adjDrawer.batch_no ? 'Current Batch Qty' : 'Current Qty' }}</div>
              <div style="font-size:18px;font-weight:700;color:#2563eb;">{{ adjDrawer.current_qty }}</div>
            </div>
          </div>
          <div v-if="adjDrawer.batch_no" style="background:#faf5ff;border:1px solid #ede9fe;border-radius:8px;padding:10px 14px;font-size:12px;color:#6b21a8;display:flex;justify-content:space-between;align-items:center">
            <span>Item total in this warehouse</span>
            <span style="font-weight:700">{{ flt(adjDrawer.item_total_qty).toFixed(2) }}</span>
          </div>
          <div>
            <label class="nim-label">New Quantity <span style="color:#dc2626">*</span></label>
            <input v-model.number="adjDrawer.new_qty" type="number" min="0" step="0.001" class="nim-input"
              :placeholder="`Current: ${adjDrawer.current_qty}`" style="font-size:16px;font-weight:600;" />
            <div v-if="adjDrawer.new_qty !== '' && adjDrawer.new_qty !== null" style="margin-top:6px;font-size:12.5px">
              <span :style="{color: adjDrawer.new_qty > adjDrawer.current_qty ? '#16a34a' : adjDrawer.new_qty < adjDrawer.current_qty ? '#dc2626' : '#6b7280', fontWeight:600}">
                {{ adjDrawer.new_qty > adjDrawer.current_qty ? `+${(adjDrawer.new_qty - adjDrawer.current_qty).toFixed(3)} increase` :
                   adjDrawer.new_qty < adjDrawer.current_qty ? `${(adjDrawer.new_qty - adjDrawer.current_qty).toFixed(3)} decrease` : 'No change' }}
              </span>
              <span v-if="adjDrawer.batch_no" style="color:#9ca3af;margin-left:6px">
                — item total will become {{ (flt(adjDrawer.item_total_qty) + (flt(adjDrawer.new_qty) - flt(adjDrawer.current_qty))).toFixed(2) }}
              </span>
            </div>
          </div>
          <div>
            <label class="nim-label">Reason <span style="color:#dc2626">*</span></label>
            <select v-model="adjDrawer.reason" class="nim-input">
              <option value="">— Select reason —</option>
              <option value="Opening Stock">Opening Stock</option>
              <option value="Physical Count Correction">Physical Count Correction</option>
              <option value="Damage / Spoilage">Damage / Spoilage</option>
              <option value="Theft / Loss">Theft / Loss</option>
              <option value="Return to Stock">Return to Stock</option>
              <option value="Other">Other</option>
            </select>
          </div>
          <div>
            <label class="nim-label">Notes (optional)</label>
            <textarea v-model="adjDrawer.notes" rows="2" class="nim-input" placeholder="Any additional details…" style="resize:vertical"></textarea>
          </div>
        </div>
        <div class="nim-dialog-footer">
          <button class="nim-btn nim-btn-ghost" @click="adjDrawer.open=false">Cancel</button>
          <button class="nim-btn" style="background:#2563eb;color:#fff;border-color:#2563eb"
            :disabled="adjDrawer.saving || !adjDrawer.item_code || adjDrawer.new_qty==='' || adjDrawer.new_qty===null || !adjDrawer.reason || (adjDrawer.pick_item && adjDrawer.pickedHasBatch)"
            @click="submitAdjustment">
            {{ adjDrawer.saving ? 'Saving…' : 'Save Adjustment' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ── Add/Edit drawer ── -->
    <div v-if="showDrawer" class="nim-overlay" @click.self="showDrawer=false">
      <div class="nim-dialog" style="width:560px">
        <div class="nim-header">
          <div class="nim-header-title">{{ drawerMode==='add' ? 'New Warehouse' : 'Edit Warehouse' }}</div>
          <button class="nim-close" @click="showDrawer=false"><span v-html="icon('x')"></span></button>
        </div>
        <div class="nim-body">
          <div class="nim-section-label">Warehouse Details</div>
          <div class="nim-grid-2 nim-mb">
            <div>
              <label class="nim-label">Warehouse Name <span class="nim-req">*</span></label>
              <input class="nim-input" v-model="form.warehouse_name" placeholder="e.g. Main Store"/>
            </div>
            <div>
              <label class="nim-label">Warehouse Type</label>
              <select class="nim-input" v-model="form.warehouse_type">
                <option v-for="t in WH_TYPES" :key="t" :value="t">{{ WH_TYPE_META[t].icon }} {{ t }}</option>
              </select>
            </div>
          </div>
          <div class="nim-mb">
            <label class="nim-label">Parent Warehouse</label>
            <SearchableSelect v-model="form.parent_warehouse" :options="parentOptions"
              value-key="name" label-key="label" placeholder="— (top-level) —"/>
          </div>
          <div class="nim-section-label">Address</div>
          <div class="nim-grid-2 nim-mb">
            <div><label class="nim-label">Address</label><input class="nim-input" v-model="form.address_line1" placeholder="Street address"/></div>
            <div><label class="nim-label">City</label><input class="nim-input" v-model="form.city" placeholder="City"/></div>
            <div>
              <label class="nim-label">Country</label>
              <select class="nim-input" v-model="form.country" @change="form.state=''">
                <option value="">— Select Country —</option>
                <option v-for="c in COUNTRIES" :key="c">{{ c }}</option>
              </select>
            </div>
            <div>
              <label class="nim-label">State / Province</label>
              <select v-if="statesFor(form.country).length" class="nim-input" v-model="form.state">
                <option value="">— Select State —</option>
                <option v-for="s in statesFor(form.country)" :key="s" :value="s">{{ s }}</option>
              </select>
              <input v-else class="nim-input" v-model="form.state" placeholder="Enter state / province"/>
            </div>
            <div><label class="nim-label">Pincode</label><input class="nim-input" v-model="form.pincode" placeholder="Pincode"/></div>
          </div>
          <div class="nim-section-label">Flags</div>
          <div style="display:flex;gap:24px">
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer;font-size:13px">
              <input type="checkbox" :checked="form.is_group" @change="form.is_group=$event.target.checked?1:0"
                style="width:16px;height:16px;cursor:pointer"/> Is Group
            </label>
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer;font-size:13px">
              <input type="checkbox" :checked="form.disabled" @change="form.disabled=$event.target.checked?1:0"
                style="width:16px;height:16px;cursor:pointer"/> Disabled
            </label>
          </div>
        </div>
        <div class="nim-footer">
          <div></div>
          <div style="display:flex;gap:10px">
            <button class="nim-btn nim-btn-ghost" @click="showDrawer=false">Cancel</button>
            <button class="nim-btn nim-btn-primary" :disabled="saving" @click="saveWarehouse">
              <span v-html="icon('check')"></span> {{ saving ? 'Saving…' : 'Save' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Stock Transfer modal ── -->
    <div v-if="showTransfer" class="nim-overlay" @click.self="showTransfer=false">
      <div class="nim-dialog" style="width:480px">
        <div class="nim-header">
          <div class="nim-header-title">Stock Transfer</div>
          <button class="nim-close" @click="showTransfer=false"><span v-html="icon('x')"></span></button>
        </div>
        <div class="nim-body">
          <div class="nim-mb">
            <label class="nim-label">From Warehouse</label>
            <SearchableSelect v-model="transferForm.from_warehouse" :options="list.filter(w=>!w.is_group)" placeholder="Source warehouse"/>
          </div>
          <div class="nim-mb">
            <label class="nim-label">To Warehouse <span class="nim-req">*</span></label>
            <SearchableSelect v-model="transferForm.to_warehouse"
              :options="list.filter(w=>!w.is_group&&w.name!==transferForm.from_warehouse)" placeholder="Target warehouse"/>
          </div>
          <div class="nim-mb">
            <label class="nim-label">Item <span class="nim-req">*</span></label>
            <SearchableSelect v-model="transferForm.item_code" :options="allItems"
              value-key="name" label-key="item_name" placeholder="Select item"/>
          </div>
          <div class="nim-mb">
            <label class="nim-label">Quantity <span class="nim-req">*</span></label>
            <input class="nim-input" type="number" min="0.001" step="0.001" v-model="transferForm.qty"/>
          </div>
        </div>
        <div class="nim-footer">
          <div></div>
          <div style="display:flex;gap:10px">
            <button class="nim-btn nim-btn-ghost" @click="showTransfer=false">Cancel</button>
            <button class="nim-btn nim-btn-primary" :disabled="transferSaving" @click="doTransfer">
              <span v-html="icon('check')"></span> {{ transferSaving ? 'Processing…' : 'Create Transfer' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Delete confirm ── -->
    <div v-if="showDel" class="nim-overlay" @click.self="showDel=false">
      <div style="background:#fff;border-radius:12px;padding:28px 32px;max-width:420px;width:100%;margin:auto">
        <div style="font-size:16px;font-weight:700;color:#1A1D23;margin-bottom:8px">Delete Warehouse?</div>
        <div style="font-size:14px;color:#868E96;margin-bottom:24px">Delete <b>{{ delTarget?.warehouse_name }}</b>? This cannot be undone.</div>
        <div style="display:flex;gap:10px;justify-content:flex-end">
          <button class="nim-btn nim-btn-ghost" @click="showDel=false">Cancel</button>
          <button class="nim-btn" style="background:#C92A2A;color:#fff;border-color:#C92A2A" @click="doDelete">Yes, Delete</button>
        </div>
      </div>
    </div>

  </Teleport>
</div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from "vue";
import { apiList, apiGET, apiPOST, apiSave, apiSubmit, apiDelete, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { fmt, flt } from "../utils/format.js";
import { icon } from "../utils/icons.js";
import SearchableSelect from "../components/SearchableSelect.vue";
import { COUNTRIES, statesFor } from "../composables/useCountryState.js";

const { toast } = useToast();

/* ── View mode ── */
const viewMode = ref("cards"); // 'cards' | 'tree'

/* ── Ayurvedic warehouse tree presets ── */
const AYURVEDIC_GROUPS = [
  { label: "RM Store",    type: "Raw Material",     icon: "🧲" },
  { label: "Quarantine",  type: "Virtual",           icon: "🔒" },
  { label: "WIP",         type: "Work In Progress",  icon: "🔧" },
  { label: "FG Store",    type: "Finished Goods",    icon: "📦" },
  { label: "Dispatch",    type: "Transit",           icon: "🚚" },
];

/* ── Tree expand state: { [groupName]: boolean } ── */
const treeExpanded = reactive({});

const WH_TYPE_META = {
  "Stores":           { icon: "🏪", color: "#2563eb", bg: "#F3F0FF" },
  "Finished Goods":   { icon: "📦", color: "#1971C2", bg: "#E7F5FF" },
  "Raw Material":     { icon: "🧲", color: "#2F9E44", bg: "#EBFBEE" },
  "Work In Progress": { icon: "🔧", color: "#E67700", bg: "#FFF3BF" },
  "Transit":          { icon: "🚚", color: "#C92A2A", bg: "#FFF5F5" },
  "Virtual":          { icon: "🔒", color: "#868E96", bg: "#F8F9FA" },
  "Scrap":            { icon: "♻️", color: "#5C7CFA", bg: "#EDF2FF" },
};
const WH_DEFAULT = { icon: "🏭", color: "#495057", bg: "#F1F3F5" };
const WH_TYPES = Object.keys(WH_TYPE_META);

const list           = ref([]);
const loading        = ref(false);
const selectedWH     = ref(null);    // currently selected warehouse GROUP
const selectedChild  = ref(null);    // currently selected child warehouse
const stockItems     = ref([]);
const stockLoading   = ref(false);
const warehouseBatches = ref({});
const expandedRows     = ref({});
const search         = ref("");
const filterType     = ref("All");
const filterDDOpen   = ref(false);

const adjDrawer = reactive({
  open: false, saving: false, pick_item: false,
  item_code: "", item_name: "", warehouse: "",
  current_qty: 0, new_qty: "", reason: "", notes: "",
  batch_no: "", item_total_qty: 0, pickedHasBatch: false,
});
const showDrawer     = ref(false);
const showTransfer   = ref(false);
const showDel        = ref(false);
const delTarget      = ref(null);
const drawerMode     = ref("add");
const saving         = ref(false);
const transferSaving = ref(false);
const allItems       = ref([]);

const form = reactive({
  name: "", warehouse_name: "", warehouse_type: "Stores",
  parent_warehouse: "", city: "", country: "India", state: "", address_line1: "", pincode: "",
  is_group: 0, disabled: 0,
});
const transferForm = reactive({
  from_warehouse: "", to_warehouse: "", item_code: "", qty: 1,
});

function whMeta(type) { return WH_TYPE_META[type] || WH_DEFAULT; }

// Groups dropdown
const groups = computed(() => list.value.filter((w) => w.is_group));

const WH_GROUP_KEY = "wh_selected_group";

const selectedGroupName = computed({
  get: () => selectedWH.value?.name || "",
  set: (val) => {
    localStorage.setItem(WH_GROUP_KEY, val);
    const g = list.value.find((w) => w.name === val);
    if (g) {
      selectedWH.value = g;
      selectedChild.value = null;
      loadStockForWarehouse(g.name);
    }
  },
});

// Child warehouses of selected group, filtered by search + type
const childWarehouses = computed(() => {
  if (!selectedWH.value) return [];
  let result = list.value.filter((w) => w.parent_warehouse === selectedWH.value.name);
  const q = search.value.toLowerCase().trim();
  if (q) {
    result = result.filter((w) =>
      (w.warehouse_name || w.name).toLowerCase().includes(q) ||
      (w.city || "").toLowerCase().includes(q)
    );
  }
  if (filterType.value !== "All") {
    result = result.filter((w) => (w.warehouse_type || "Stores") === filterType.value);
  }
  return result;
});

// The specific leaf warehouse to adjust stock against. Adjustment always
// needs one concrete warehouse (you can't post stock to a group, and "All"
// scope can span several leaves so we can't guess which one a batch's stock
// is really sitting in) — EXCEPT the very common case where the selected
// group has exactly one leaf underneath it, in which case "All" and "that
// one warehouse" mean the same thing, so we resolve it automatically rather
// than forcing an extra click.
const adjustTargetWH = computed(() => {
  if (selectedChild.value && !selectedChild.value.is_group) return selectedChild.value;
  const leaves = childWarehouses.value.filter((w) => !w.is_group);
  if (!selectedChild.value && leaves.length === 1) return leaves[0];
  return null;
});

const whStats = computed(() => {
  if (!stockItems.value.length) return { value: 0, items: 0, reserved: 0, ordered: 0, projected: 0 };
  return {
    value:     stockItems.value.reduce((s, r) => s + flt(r.stock_value),   0),
    items:     stockItems.value.length,
    reserved:  stockItems.value.reduce((s, r) => s + flt(r.reserved_qty),  0),
    ordered:   stockItems.value.reduce((s, r) => s + flt(r.ordered_qty),   0),
    projected: stockItems.value.reduce((s, r) => s + flt(r.projected_qty), 0),
  };
});

async function load() {
  loading.value = true;
  try {
    list.value = await apiList("Warehouse", {
      fields: ["name","warehouse_name","warehouse_type","parent_warehouse",
               "city","state","address_line1","pincode","is_group","disabled"],
      limit: 500,
    }) || [];
    // Auto-select: restore last-used group, else fall back to first group
    if (!selectedWH.value) {
      const saved = localStorage.getItem(WH_GROUP_KEY);
      const pick = (saved && list.value.find((w) => w.is_group && w.name === saved))
                   || list.value.find((w) => w.is_group);
      if (pick) {
        selectedWH.value = pick;
        loadStockForWarehouse(pick.name);
      }
    }
    initTreeExpand();
  } catch { list.value = []; toast("Could not load warehouses", "error"); }
  loading.value = false;
}

async function loadStockForWarehouse(name) {
  stockLoading.value = true;
  stockItems.value = [];
  warehouseBatches.value = {};
  expandedRows.value = {};
  try {
    const [stock, batches] = await Promise.all([
      apiGET("zoho_books_clone.api.inventory.get_stock_summary", { warehouse: name }),
      apiGET("zoho_books_clone.api.inventory.get_warehouse_batches", { warehouse: name }).catch(() => ({})),
    ]);
    stockItems.value = stock || [];
    warehouseBatches.value = batches || {};
  } catch { stockItems.value = []; }
  stockLoading.value = false;
}

function toggleBatches(itemCode) {
  expandedRows.value = { ...expandedRows.value, [itemCode]: !expandedRows.value[itemCode] };
}
function batchesFor(itemCode) {
  return warehouseBatches.value[itemCode] || [];
}
function fmtBatchDate(d) {
  if (!d) return "—";
  try { return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }); }
  catch { return d; }
}

async function loadItems() {
  try { allItems.value = await apiList("Item", { fields: ["name","item_name","has_batch_no"], limit: 500, order: "item_name asc" }) || []; }
  catch {}
}

function selectChild(child) {
  if (selectedChild.value?.name === child.name) {
    selectedChild.value = null;
    loadStockForWarehouse(selectedWH.value.name);
  } else {
    selectedChild.value = child;
    loadStockForWarehouse(child.name);
  }
}

function openNewAdjustment(wh) {
  Object.assign(adjDrawer, {
    open: true, saving: false, pick_item: true,
    item_code: "", item_name: "",
    warehouse: wh?.name || "",
    current_qty: 0, new_qty: "", reason: "Opening Stock", notes: "",
    batch_no: "", item_total_qty: 0, pickedHasBatch: false,
  });
}

function openAdjustment(row) {
  if (row.has_batch_no) {
    // Batch-tracked items can't be adjusted as one lump qty — the backend
    // requires a Batch No on every movement for these items, and blindly
    // picking one would break the "sum of batches == item total" guarantee.
    // Point the person at the per-batch Adjust buttons instead.
    expandedRows.value = { ...expandedRows.value, [row.item_code]: true };
    toast(`${row.item_name || row.item_code} is batch-tracked — adjust individual batches below instead of the item total.`, "error");
    return;
  }
  Object.assign(adjDrawer, {
    open: true, saving: false, pick_item: false,
    item_code:   row.item_code,
    item_name:   row.item_name || row.item_code,
    warehouse:   adjustTargetWH.value?.name || "",
    current_qty: flt(row.actual_qty),
    new_qty:     flt(row.actual_qty),
    reason:      "", notes: "",
    batch_no: "", item_total_qty: 0,
  });
}

function openBatchAdjustment(row, batch) {
  // Batch adjustments only make sense against a specific leaf warehouse
  // (never a warehouse group), same restriction the row-level Adjust
  // button already enforces via v-if="adjustTargetWH".
  Object.assign(adjDrawer, {
    open: true, saving: false, pick_item: false,
    item_code:   row.item_code,
    item_name:   row.item_name || row.item_code,
    warehouse:   adjustTargetWH.value?.name || "",
    current_qty: flt(batch.qty),
    new_qty:     flt(batch.qty),
    reason:      "", notes: "",
    batch_no:    batch.batch_no,
    item_total_qty: flt(row.actual_qty),
  });
}

// When an item is picked in "Add Stock" mode, fill its name and current qty
// (best-effort from the currently loaded stock; defaults to 0 for a new item).
// Also flag batch-tracked items — this quick-add flow can't post stock
// without a Batch No, so it needs to steer the person to the batch-aware
// Stock Entries / Opening Stock page instead of letting the save fail.
watch(() => adjDrawer.item_code, (code) => {
  if (!adjDrawer.pick_item || !code) return;
  const it = allItems.value.find((i) => i.name === code);
  adjDrawer.item_name = it?.item_name || code;
  adjDrawer.pickedHasBatch = !!it?.has_batch_no;
  const row = stockItems.value.find((r) => r.item_code === code);
  adjDrawer.current_qty = row ? flt(row.actual_qty) : 0;
});

async function submitAdjustment() {
  if (adjDrawer.pick_item && adjDrawer.pickedHasBatch) {
    return toast(`${adjDrawer.item_name} is batch-tracked — add its opening stock from the Opening Stock or Stock Entries page so a Batch No can be set.`, "error");
  }
  if (adjDrawer.new_qty === "" || adjDrawer.new_qty === null) return toast("New quantity is required", "error");
  if (!adjDrawer.reason) return toast("Please select a reason", "error");
  if (!adjDrawer.item_code) return toast("Item is required", "error");
  adjDrawer.saving = true;
  try {
    if (adjDrawer.batch_no) {
      await apiPOST("zoho_books_clone.api.inventory.create_batch_adjustment", {
        item_code: adjDrawer.item_code,
        warehouse: adjDrawer.warehouse,
        batch_no:  adjDrawer.batch_no,
        new_qty:   adjDrawer.new_qty,
        reason:    adjDrawer.reason,
        notes:     adjDrawer.notes || "",
      });
      toast(`Batch adjusted — ${adjDrawer.batch_no} set to ${adjDrawer.new_qty}`, "success");
    } else {
      await apiPOST("zoho_books_clone.api.inventory.create_inventory_adjustment", {
        item_code: adjDrawer.item_code,
        warehouse: adjDrawer.warehouse,
        new_qty:   adjDrawer.new_qty,
        reason:    adjDrawer.reason,
        notes:     adjDrawer.notes || "",
      });
      toast(`Stock adjusted — ${adjDrawer.item_code} set to ${adjDrawer.new_qty}`, "success");
    }
    adjDrawer.open = false;
    if (selectedWH.value) await loadStockForWarehouse(selectedChild.value?.name || selectedWH.value.name);
  } catch (e) {
    toast(e.message || "Adjustment failed", "error");
  } finally {
    adjDrawer.saving = false;
  }
}

function openAddGroup() {
  drawerMode.value = "add";
  Object.assign(form, {
    name: "", warehouse_name: "", warehouse_type: "Stores",
    parent_warehouse: "", city: "", state: "", address_line1: "", pincode: "",
    is_group: 1, disabled: 0,
  });
  showDrawer.value = true;
}

function openAddChild() {
  drawerMode.value = "add";
  Object.assign(form, {
    name: "", warehouse_name: "", warehouse_type: "Stores",
    parent_warehouse: selectedWH.value?.name || "",
    city: "", state: "", address_line1: "", pincode: "",
    is_group: 0, disabled: 0,
  });
  showDrawer.value = true;
}

function openEdit(wh) {
  drawerMode.value = "edit";
  Object.assign(form, {
    name: wh.name,
    warehouse_name: wh.warehouse_name || wh.name,
    warehouse_type: wh.warehouse_type || "Stores",
    parent_warehouse: wh.parent_warehouse || "",
    city: wh.city || "", state: wh.state || "",
    address_line1: wh.address_line1 || "", pincode: wh.pincode || "",
    is_group: wh.is_group ? 1 : 0,
    disabled: wh.disabled ? 1 : 0,
  });
  showDrawer.value = true;
}

async function saveWarehouse() {
  if (!form.warehouse_name.trim()) { toast("Warehouse name is required", "error"); return; }
  saving.value = true;
  try {
    const company = await resolveCompany();
    const newName = form.warehouse_name.trim();
    const oldName = form.name;

    let activeName = oldName;
    if (drawerMode.value === "edit" && newName !== oldName) {
      await apiPOST("frappe.client.rename_doc", {
        doctype: "Warehouse", old_name: oldName, new_name: newName,
        merge: JSON.stringify(false),
      });
      activeName = newName;
    }

    const changes = {
      doctype: "Warehouse", name: activeName,
      warehouse_name: newName, warehouse_type: form.warehouse_type,
      parent_warehouse: form.parent_warehouse || "",
      city: form.city.trim(), state: form.state.trim(),
      address_line1: form.address_line1.trim(), pincode: form.pincode.trim(),
      is_group: form.is_group ? 1 : 0, disabled: form.disabled ? 1 : 0, company,
    };
    let doc = changes;
    if (drawerMode.value === "edit") {
      const fresh = await apiGET("zoho_books_clone.api.docs.get_doc", { doctype: "Warehouse", name: activeName });
      doc = { ...fresh, ...changes };
    }
    const saved = await apiSave(doc);
    await load();

    if (saved && !list.value.some((w) => w.name === saved.name)) {
      list.value = [saved, ...list.value];
    }
    if (drawerMode.value === "edit" && saved) {
      const updated = list.value.find((w) => w.name === saved.name);
      if (updated && selectedWH.value?.name === saved.name) {
        selectedWH.value = updated;
      }
    }

    toast(drawerMode.value === "edit" ? "Warehouse updated" : "Warehouse created");
    showDrawer.value = false;
  } catch (e) { toast("Save failed: " + e.message, "error"); }
  saving.value = false;
}

function openTransfer(wh) {
  Object.assign(transferForm, {
    from_warehouse: (wh && !wh.is_group) ? wh.name : "",
    to_warehouse: "", item_code: "", qty: 1,
  });
  showTransfer.value = true;
}

async function doTransfer() {
  if (!transferForm.from_warehouse || !transferForm.to_warehouse || !transferForm.item_code) {
    toast("Source warehouse, target warehouse and item are required", "error"); return;
  }
  if (flt(transferForm.qty) <= 0) { toast("Transfer quantity must be greater than 0", "error"); return; }
  if (transferForm.from_warehouse === transferForm.to_warehouse) {
    toast("Source and target must be different", "error"); return;
  }
  // Ensure the source warehouse actually holds enough of the item.
  try {
    const d = await apiGET("zoho_books_clone.api.inventory.get_item_stock_detail",
      { item_code: transferForm.item_code, warehouse: transferForm.from_warehouse });
    const avail = flt(d?.warehouses?.[0]?.actual_qty);
    if (flt(transferForm.qty) > avail) {
      toast(`Not enough stock in ${transferForm.from_warehouse} — need ${flt(transferForm.qty)}, available ${avail}.`, "error");
      return;
    }
  } catch { /* balance lookup failed — don't block the transfer */ }
  transferSaving.value = true;
  try {
    const company = await resolveCompany();
    const saved = await apiSave({
      doctype: "Stock Entry", company,
      stock_entry_type: "Material Transfer",
      posting_date: new Date().toISOString().slice(0,10),
      from_warehouse: transferForm.from_warehouse,
      to_warehouse:   transferForm.to_warehouse,
      items: [{ doctype: "Stock Entry Detail", item_code: transferForm.item_code,
                qty: flt(transferForm.qty), s_warehouse: transferForm.from_warehouse,
                t_warehouse: transferForm.to_warehouse }],
    });
    await apiSubmit("Stock Entry", saved.name);
    toast("Stock transfer created");
    showTransfer.value = false;
    if (selectedWH.value) loadStockForWarehouse(selectedWH.value.name);
  } catch (e) { toast("Transfer failed: " + e.message, "error"); }
  transferSaving.value = false;
}

function confirmDel(wh) { delTarget.value = wh; showDel.value = true; }

async function doDelete() {
  try {
    await apiDelete("Warehouse", delTarget.value.name);
    list.value = list.value.filter((w) => w.name !== delTarget.value.name);
    if (selectedWH.value?.name === delTarget.value.name) {
      selectedWH.value = null;
      stockItems.value = [];
    }
    toast("Warehouse deleted");
    showDel.value = false;
  } catch (e) { toast("Delete failed: " + e.message, "error"); }
}

const parentOptions = computed(() =>
  list.value.filter((w) => w.is_group).map((w) => ({ name: w.name, label: w.warehouse_name || w.name }))
);

/* ════════════════════════════════════════════════
   WAREHOUSE TREE helpers
   ════════════════════════════════════════════════ */

// Root nodes: warehouses with no parent (or parent not in list) that are groups
const treeRoots = computed(() => {
  const names = new Set(list.value.map((w) => w.name));
  return list.value.filter((w) => w.is_group && (!w.parent_warehouse || !names.has(w.parent_warehouse)));
});

// Direct children of a given parent name
function treeChildren(parentName) {
  return list.value.filter((w) => !w.is_group && w.parent_warehouse === parentName);
}

// Whether all roots are expanded
const treeAllExpanded = computed(() =>
  treeRoots.value.length > 0 && treeRoots.value.every((n) => treeExpanded[n.name])
);

function toggleNode(name) {
  treeExpanded[name] = !treeExpanded[name];
}

function toggleAllTree() {
  const expand = !treeAllExpanded.value;
  treeRoots.value.forEach((n) => { treeExpanded[n.name] = expand; });
}

function treeSelectGroup(node) {
  treeExpanded[node.name] = !treeExpanded[node.name]; // toggle expand on click
  selectedChild.value = null;
  if (selectedWH.value?.name !== node.name) {
    selectedWH.value = node;
    loadStockForWarehouse(node.name);
  }
}

function treeSelectChild(groupNode, child) {
  selectedWH.value = groupNode;
  if (selectedChild.value?.name === child.name) {
    selectedChild.value = null;
    loadStockForWarehouse(groupNode.name);
  } else {
    selectedChild.value = child;
    loadStockForWarehouse(child.name);
  }
}

function treeOpenAddChild(groupNode) {
  selectedWH.value = groupNode;
  openAddChild();
}

// Auto-expand all roots once list loads
function initTreeExpand() {
  treeRoots.value.forEach((n) => {
    if (!(n.name in treeExpanded)) treeExpanded[n.name] = true;
  });
}

onMounted(() => { load(); loadItems(); });
</script>

<style>
/* ════════════════════════════════════════════════════════════════
   WAREHOUSES PAGE
   ════════════════════════════════════════════════════════════════ */

.wh-page {
  display: flex;
  flex-direction: column;
  background: #f1f4f8;
  overflow: hidden;
}

/* ── Toolbar ── */
.wh-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 24px;
  background: #fff;
  border-bottom: 1px solid #e8edf5;
  flex-shrink: 0;
  flex-wrap: wrap;
}

/* ── Group dropdown ── */
.wh-group-wrap {
  display: flex;
  align-items: center;
  gap: 0;
  background: #f8fafc;
  border: 1.5px solid #e2e8f0;
  border-radius: 9px;
  overflow: hidden;
  flex-shrink: 0;
}
.wh-group-prefix {
  padding: 0 10px;
  font-size: 11.5px;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: .05em;
  background: #f1f4f8;
  border-right: 1px solid #e2e8f0;
  height: 36px;
  display: flex;
  align-items: center;
  white-space: nowrap;
}
.wh-group-select-wrap {
  position: relative;
  display: flex;
  align-items: center;
}
.wh-group-select {
  appearance: none;
  -webkit-appearance: none;
  border: none;
  background: transparent;
  padding: 0 32px 0 12px;
  height: 36px;
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
  cursor: pointer;
  outline: none;
  min-width: 160px;
}
.wh-group-chev {
  position: absolute;
  right: 10px;
  pointer-events: none;
  color: #94a3b8;
  display: flex;
  align-items: center;
}

/* ── Search ── */
.wh-tb-search-wrap {
  position: relative;
  flex: 0 0 200px;
}
.wh-tb-search-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  pointer-events: none;
  width: 14px;
}
.wh-tb-search-input {
  width: 100%;
  border: 1.5px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 10px 8px 32px;
  font-size: 13px;
  color: #1e293b;
  outline: none;
  background: #f8fafc;
  transition: border-color .15s, background .15s;
  box-sizing: border-box;
}
.wh-tb-search-input:focus { border-color: #3b82f6; background: #fff; }

/* ── Filter dropdown ── */
.wh-dd-backdrop {
  position: fixed;
  inset: 0;
  z-index: 199;
}

.wh-filter-dd-wrap {
  position: relative;
  flex-shrink: 0;
}

.wh-filter-dd-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 13px;
  font-size: 13px;
  font-weight: 600;
  border: 1.5px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  color: #374151;
  cursor: pointer;
  transition: background .12s, border-color .12s;
  white-space: nowrap;
}
.wh-filter-dd-btn:hover { background: #eff6ff; border-color: #93c5fd; color: #2563eb; }
.wh-filter-dd-btn--active { background: #eff6ff; border-color: #2563eb; color: #2563eb; }

.wh-filter-dd-chev {
  color: #94a3b8;
  display: flex;
  align-items: center;
  transition: transform .18s ease;
}
.wh-filter-dd-chev--open { transform: rotate(180deg); }

.wh-filter-dd-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  background: #fff;
  border: 1.5px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 8px 28px rgba(0,0,0,.13);
  min-width: 210px;
  padding: 6px;
  z-index: 200;
}

.wh-filter-dd-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  cursor: pointer;
  transition: background .1s;
}
.wh-filter-dd-item:hover { background: #f1f5f9; }
.wh-filter-dd-item--active { background: #eff6ff !important; color: #2563eb; font-weight: 700; }

.wh-filter-dd-icon { font-size: 16px; flex-shrink: 0; }
.wh-filter-dd-check { margin-left: auto; color: #2563eb; display: flex; align-items: center; }

/* ── Toolbar actions ── */
.wh-tb-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

/* ── Main content (scrollable) ── */
.wh-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px 24px 40px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ── Section header ── */
.wh-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.wh-section-title {
  font-size: 16px;
  font-weight: 800;
  color: #0f172a;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ── No-children state ── */
.wh-no-children {
  text-align: center;
  padding: 32px 20px;
  background: #fff;
  border-radius: 14px;
  border: 1.5px dashed #e2e8f0;
}

/* ── Cards grid ── */
.wh-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
}
.wh-cards-gap { margin-bottom: 4px; }

/* ── Warehouse card ── */
.wh-card {
  background: #fff;
  border: 1.5px solid #e8edf5;
  border-radius: 14px;
  padding: 16px 16px 0;
  display: flex;
  flex-direction: column;
  transition: box-shadow .15s, border-color .15s;
}
.wh-card { cursor: pointer; }
.wh-card:hover { box-shadow: 0 4px 18px rgba(0,0,0,.09); border-color: #93c5fd; }
.wh-card--active {
  border-color: #2563eb !important;
  box-shadow: 0 0 0 3px rgba(37,99,235,.12), 0 4px 18px rgba(0,0,0,.09) !important;
  background: #f8fbff !important;
}
.wh-card--active .wh-card-name { color: #2563eb; }
.wh-card--disabled { opacity: .55; }

.wh-card-top {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}
.wh-card-icon {
  width: 42px;
  height: 42px;
  border-radius: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}
.wh-card-info { flex: 1; min-width: 0; }
.wh-card-name {
  font-size: 13.5px;
  font-weight: 700;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 4px;
}
.wh-card-meta { display: flex; flex-direction: column; gap: 2px; }
.wh-card-city { font-size: 11.5px; color: #94a3b8; }
.wh-card-right { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; flex-shrink: 0; }

.wh-card-footer {
  border-top: 1px solid #f1f4f8;
  padding: 10px 0 12px;
  margin-top: auto;
}
.wh-card-footer--actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* ── Card shimmer ── */
.wh-card-shimmer {
  background: #fff;
  border: 1.5px solid #e8edf5;
  border-radius: 14px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 88px;
}

/* ── Empty state ── */
.wh-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: #94a3b8;
  text-align: center;
  padding: 40px;
}
.wh-empty-icon  { font-size: 56px; margin-bottom: 14px; }
.wh-empty-title { font-size: 17px; font-weight: 700; color: #334155; margin-bottom: 6px; }
.wh-empty-sub   { font-size: 13.5px; color: #94a3b8; max-width: 280px; line-height: 1.5; }

/* ── Badges ── */
.wh-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 9px;
  border-radius: 20px;
  white-space: nowrap;
}
.wh-badge-blue { background: #eff6ff; color: #2563eb; }
.wh-badge-red  { background: #fee2e2; color: #dc2626; }

/* ── Action buttons ── */
.wh-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  font-size: 13px;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  transition: background .12s, box-shadow .12s, transform .1s;
  border: 1.5px solid #e2e8f0;
  background: #fff;
  color: #374151;
  white-space: nowrap;
}
.wh-action-btn:hover { background: #f8fafc; box-shadow: 0 2px 6px rgba(0,0,0,.08); }
.wh-action-btn:active { transform: translateY(1px); }

.wh-action-btn--primary {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: #fff; border-color: transparent;
  box-shadow: 0 2px 6px rgba(37,99,235,.3);
}
.wh-action-btn--primary:hover { opacity: .9; background: linear-gradient(135deg, #3b82f6, #2563eb); }

.wh-action-btn--danger {
  color: #dc2626; border-color: #fca5a5; background: #fff5f5;
}
.wh-action-btn--danger:hover { background: #fee2e2; }

/* ── Stats strip ── */
.wh-stats-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid #f1f4f8;
}

.wh-stat-chip {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #f8fafc;
  border-radius: 10px;
  padding: 12px 14px;
  border: 1px solid #e8edf5;
  border-top: 3px solid transparent;
}
.wh-stat-chip-icon { font-size: 20px; flex-shrink: 0; }
.wh-stat-chip-lbl {
  font-size: 10px;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: .05em;
  margin-bottom: 3px;
  white-space: nowrap;
}
.wh-stat-chip-val { font-size: 16px; font-weight: 800; color: #0f172a; }
.wh-stat-chip--blue   .wh-stat-chip-val { color: #2563eb; }
.wh-stat-chip--green  .wh-stat-chip-val { color: #16a34a; }
.wh-stat-chip--orange .wh-stat-chip-val { color: #ea580c; }
.wh-stat-chip--indigo .wh-stat-chip-val { color: #4f46e5; }
.wh-stat-chip--purple .wh-stat-chip-val { color: #7c3aed; }

/* ── Stock section ── */
.wh-stock-section {
  background: #fff;
  border-radius: 14px;
  border: 1px solid #e8edf5;
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
  overflow: hidden;
}
.wh-stock-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px 12px;
  border-bottom: 1px solid #f1f4f8;
}
.wh-stock-title {
  font-size: 14px;
  font-weight: 800;
  color: #0f172a;
  display: flex;
  align-items: center;
  gap: 8px;
}
.wh-stock-count {
  font-size: 11px;
  font-weight: 700;
  background: #e2e8f0;
  color: #475569;
  padding: 1px 8px;
  border-radius: 20px;
}
.wh-stock-actions { display: flex; gap: 6px; }
.wh-stock-shimmer { padding: 16px 20px; }
.wh-stock-empty {
  padding: 48px 20px;
  text-align: center;
  color: #94a3b8;
}
.wh-stock-empty-title { font-size: 14px; font-weight: 700; color: #334155; margin-bottom: 5px; }
.wh-stock-empty-sub   { font-size: 12.5px; color: #94a3b8; }

/* ── Stock table ── */
.wh-tbl-wrap { overflow-x: auto; }
.wh-tbl { width: 100%; border-collapse: collapse; min-width: 520px; }

.wh-th {
  padding: 10px 14px;
  font-size: 10.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .05em;
  color: #64748b;
  background: #f8fafc;
  border-bottom: 1px solid #e8edf5;
  white-space: nowrap;
}
.wh-th-r { text-align: right; }
.wh-th-c { text-align: center; }

.wh-tr { border-bottom: 1px solid #f1f4f8; transition: background .1s; }
.wh-tr:last-child { border-bottom: none; }
.wh-tr:hover { background: #f8fafc; }

.wh-td { padding: 11px 14px; font-size: 13px; color: #1e293b; vertical-align: middle; }
.wh-td-muted   { color: #64748b; font-size: 12.5px; }
.wh-td-r       { text-align: right; }
.wh-td-c       { text-align: center; }
.wh-td-qty     { font-weight: 700; color: #16a34a; }
.wh-td-reserved { color: #ea580c; }
.wh-td-ordered  { color: #7c3aed; }
.wh-td-value   { font-weight: 700; color: #2563eb; }

.wh-item-name { font-size: 13px; font-weight: 600; color: #0f172a; }
.wh-item-code { font-size: 11px; color: #94a3b8; margin-top: 2px; }

.wh-status-low {
  font-size: 10.5px; font-weight: 700;
  background: #fff7ed; color: #c2410c;
  padding: 2px 8px; border-radius: 10px;
  white-space: nowrap;
}
.wh-status-ok {
  font-size: 10.5px; font-weight: 700;
  background: #f0fdf4; color: #15803d;
  padding: 2px 8px; border-radius: 10px;
  white-space: nowrap;
}

/* ── Batch breakdown ── */
.wh-tr-clickable { cursor: pointer; }
.wh-expand-chevron {
  display: inline-flex; align-items: center; justify-content: center;
  width: 18px; height: 18px; color: #94a3b8;
  transition: transform .15s ease;
}
.wh-expand-chevron--open { transform: rotate(180deg); color: #2563eb; }
.wh-batch-row td { border-bottom: 1px solid #f3f4f6; }
.wh-batch-panel { background: #f8fafc; padding: 10px 14px 10px 46px; }
.wh-batch-empty { font-size: 12px; color: #9ca3af; padding: 6px 0; }
.wh-batch-tbl { width: 100%; border-collapse: collapse; font-size: 12px; }
.wh-batch-tbl th {
  text-align: left; font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .04em; color: #9ca3af; padding: 4px 8px;
}
.wh-batch-tbl td { padding: 6px 8px; border-top: 1px solid #e5e7eb; }
.wh-batch-no { font-weight: 600; color: #0f172a; }
.wh-batch-date { color: #6b7280; }
.wh-batch-qty { font-weight: 600; color: #0f172a; }
.wh-batch-flag {
  font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 9px; white-space: nowrap;
}
.wh-batch-flag--expired { background: #fee2e2; color: #b91c1c; }
.wh-batch-flag--soon { background: #fff7ed; color: #c2410c; }

.wh-smc-batch-toggle {
  background: #eff6ff; color: #2563eb; border: none; border-radius: 6px;
  font-size: 11px; font-weight: 600; padding: 3px 8px; cursor: pointer;
}
.wh-smc-batch-list {
  margin-top: 8px; border-top: 1px dashed #e5e7eb; padding-top: 8px;
  display: flex; flex-direction: column; gap: 8px;
}
.wh-smc-batch-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }

/* ── Adjust button ── */
.wh-adj-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 11px;
  font-size: 12px;
  font-weight: 600;
  border: 1.5px solid #e2e8f0;
  border-radius: 7px;
  background: #f8fafc;
  color: #374151;
  cursor: pointer;
  transition: background .12s, border-color .12s;
  white-space: nowrap;
}
.wh-adj-btn:hover { background: #eff6ff; border-color: #93c5fd; color: #2563eb; }
.wh-adj-btn--active {
  background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
  color: #fff !important;
  border-color: transparent !important;
  box-shadow: 0 2px 6px rgba(37,99,235,.3);
}

.wh-stock-scope {
  font-size: 13px;
  font-weight: 500;
  color: #64748b;
}

/* ── misc ── */
.wh-btn-label { }
.wh-th-hide-sm { display: table-cell; }
.wh-th-hide-md { display: table-cell; }

/* ── Mobile card view for stock items (hidden on desktop, shown at ≤480px) ── */
.wh-tbl-mobile { display: none; flex-direction: column; gap: 0; }
.wh-tbl-desktop { display: block; }

.wh-stock-mc {
  border-bottom: 1px solid #f1f4f8;
  padding: 12px 16px;
  background: #fff;
}
.wh-stock-mc:last-child { border-bottom: none; }

.wh-smc-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}
.wh-smc-name-wrap { flex: 1; min-width: 0; }
.wh-smc-name {
  font-size: 13.5px;
  font-weight: 700;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.wh-smc-code {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
}

.wh-smc-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  border: 1px solid #e8edf5;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 10px;
}
.wh-smc-cell {
  padding: 9px 12px;
  border-right: 1px solid #e8edf5;
  border-bottom: 1px solid #e8edf5;
}
.wh-smc-cell:nth-child(2n) { border-right: none; }
.wh-smc-cell:nth-last-child(-n+2) { border-bottom: none; }
.wh-smc-cell--value { background: #f8faff; }

.wh-smc-lbl {
  font-size: 9.5px;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: .05em;
  margin-bottom: 3px;
}
.wh-smc-val {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}
.wh-smc-qty      { color: #16a34a; }
.wh-smc-reserved { color: #ea580c; }
.wh-smc-ordered  { color: #7c3aed; }
.wh-smc-value    { color: #2563eb; font-weight: 700; }

.wh-smc-footer {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.wh-smc-tag {
  font-size: 11px;
  font-weight: 600;
  color: #475569;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 5px;
  padding: 2px 8px;
}
.wh-smc-adj {
  margin-left: auto;
  font-size: 11.5px;
  padding: 4px 10px;
}

/* ════════════════════════════════════════════
   TABLET  (≤ 768 px)
   ════════════════════════════════════════════ */
@media (max-width: 768px) {
  .wh-toolbar { padding: 10px 16px; gap: 8px; }
  .wh-tb-search-wrap { flex: 0 0 160px; }
  .wh-content { padding: 16px; gap: 14px; }
  .wh-cards-grid { grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; }
  .wh-stats-strip { grid-template-columns: repeat(2, 1fr); gap: 8px; }
  .wh-th-hide-md { display: none; }
  .nim-dialog { max-width: 95vw !important; }
}

/* ════════════════════════════════════════════
   MOBILE  (≤ 480 px)
   ════════════════════════════════════════════ */
@media (max-width: 480px) {
  .wh-toolbar { flex-wrap: wrap; padding: 10px 12px; gap: 8px; }
  .wh-group-wrap {order: 0; }
  .wh-filter-dd-menu{ right: 0; left: auto; }
  .wh-group-select { min-width: 0; width: 100%; }
  .wh-tb-search-wrap { flex: 1 1 auto; order: 2; }
  .wh-tb-search-input { width: 100%; }
  .wh-filter-dd-wrap { order: 1; }
  .wh-tb-actions { order: 1; }
  .wh-btn-label { display: none; }

  .wh-content { padding: 12px; gap: 12px; }
  .wh-cards-grid { grid-template-columns: 1fr; gap: 10px; }
  .wh-stats-strip { grid-template-columns: repeat(2, 1fr); gap: 8px; padding: 12px; }
  .wh-stat-chip { padding: 10px 10px; }
  .wh-stat-chip-val { font-size: 14px; }

  .wh-th-hide-sm { display: none; }
  .wh-tbl { min-width: 360px; }

  .wh-section-header { flex-direction: column; align-items: flex-start; gap: 8px; }

  /* ── Stock table → card swap ── */
  .wh-tbl-desktop { display: none !important; }
  .wh-tbl-mobile  { display: flex; flex-direction: column; }
}

/* ════════════════════════════════════════════════════════════════
   LAYOUT: tree sidebar + content
   ════════════════════════════════════════════════════════════════ */

.wh-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* In cards mode wh-content fills all space, wh-layout acts like a passthrough */
.wh-layout:not(.wh-layout--tree) .wh-content {
  flex: 1;
}

/* In tree mode: sidebar left, content right */
.wh-layout--tree {
  flex-direction: row;
}
.wh-layout--tree .wh-content {
  flex: 1;
  overflow-y: auto;
}

/* ── View toggle pill ── */
.wh-view-toggle {
  display: inline-flex;
  border: 1.5px solid #e2e8f0;
  border-radius: 9px;
  overflow: hidden;
  flex-shrink: 0;
}
.wh-vt-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 13px;
  font-size: 12.5px;
  font-weight: 600;
  color: #64748b;
  background: #f8fafc;
  border: none;
  cursor: pointer;
  transition: background .12s, color .12s;
  white-space: nowrap;
}
.wh-vt-btn + .wh-vt-btn { border-left: 1px solid #e2e8f0; }
.wh-vt-btn:hover { background: #eff6ff; color: #2563eb; }
.wh-vt-btn--active {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: #fff;
}
.wh-vt-btn--active:hover { background: linear-gradient(135deg, #3b82f6, #1d4ed8); }

/* ════════════════════════════════════════════════════════════════
   WAREHOUSE TREE PANEL
   ════════════════════════════════════════════════════════════════ */

.wh-tree-panel {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-right: 1.5px solid #e8edf5;
  overflow: hidden;
}

.wh-tree-head {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 12px 14px 10px;
  font-size: 12px;
  font-weight: 700;
  color: #374151;
  border-bottom: 1px solid #f1f4f8;
  flex-shrink: 0;
}
.wh-tree-head-icon { font-size: 15px; }
.wh-tree-expand-all {
  margin-left: auto;
  font-size: 10.5px;
  font-weight: 600;
  color: #3b82f6;
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  white-space: nowrap;
}
.wh-tree-expand-all:hover { background: #eff6ff; }

.wh-tree-loading { padding: 12px; }

.wh-tree-body {
  flex: 1;
  overflow-y: auto;
  padding: 6px 0;
}

/* ── Tree node base ── */
.wh-tree-node {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 7px 12px;
  cursor: pointer;
  user-select: none;
  transition: background .1s;
  position: relative;
}
.wh-tree-node:hover { background: #f8fafc; }
.wh-tree-node--selected { background: #eff6ff !important; }
.wh-tree-node--disabled { opacity: .55; }

/* Group nodes */
.wh-tree-node--group {
  font-size: 12.5px;
  font-weight: 700;
  color: #1e293b;
  border-bottom: 1px solid #f8fafc;
}

/* Child nodes (indented) */
.wh-tree-node--child {
  padding-left: 32px;
  font-size: 12px;
  font-weight: 500;
  color: #374151;
}

/* Caret for expand/collapse */
.wh-tree-caret {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  transition: transform .18s;
  flex-shrink: 0;
  border-radius: 4px;
}
.wh-tree-caret:hover { background: #e2e8f0; color: #2563eb; }
.wh-tree-caret--open { transform: rotate(0deg); }
/* default (closed): point right */
.wh-tree-caret:not(.wh-tree-caret--open) { transform: rotate(-90deg); }

/* Node icon bubble */
.wh-tree-node-icon {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  flex-shrink: 0;
}
.wh-tree-node-icon--sm {
  width: 20px;
  height: 20px;
  border-radius: 5px;
  font-size: 11px;
}

.wh-tree-node-label {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Count badge */
.wh-tree-badge {
  font-size: 10px;
  font-weight: 700;
  background: #e0e7ff;
  color: #3730a3;
  border-radius: 10px;
  padding: 1px 7px;
  white-space: nowrap;
  flex-shrink: 0;
}

/* Disabled/off tag */
.wh-tree-off {
  font-size: 9.5px;
  font-weight: 700;
  background: #fee2e2;
  color: #991b1b;
  border-radius: 4px;
  padding: 1px 5px;
  flex-shrink: 0;
}

/* Empty child hint */
.wh-tree-empty-child {
  padding: 5px 12px 5px 34px;
  font-size: 11px;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 8px;
  font-style: italic;
}
.wh-tree-add-btn {
  font-size: 10.5px;
  font-weight: 700;
  color: #3b82f6;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0 2px;
}
.wh-tree-add-btn:hover { text-decoration: underline; }

/* Empty state in tree panel */
.wh-tree-empty {
  padding: 32px 16px;
  text-align: center;
  color: #94a3b8;
}

/* Tree footer */
.wh-tree-footer {
  padding: 10px 12px;
  border-top: 1px solid #f1f4f8;
  flex-shrink: 0;
}

/* ── Tree: tablet / mobile ── */
@media (max-width: 768px) {
  .wh-tree-panel { width: 200px; }
}
@media (max-width: 480px) {
  .wh-layout--tree { flex-direction: column; }
  .wh-tree-panel {
    width: 100%;
    max-height: 220px;
    border-right: none;
    border-bottom: 1.5px solid #e8edf5;
  }
  .wh-tree-body { max-height: 150px; }
}
</style>