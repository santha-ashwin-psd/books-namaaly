<template>
  <div class="list-page">

    <!-- ── Toolbar ── -->
    <div class="sales-toolbar">
      <div class="sales-search">
        <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
        <input v-model="search" placeholder="Search POs, vendors…" class="sales-search-input" />
      </div>
      <div class="sales-pills">
        <button v-for="t in tabs" :key="t.key"
          class="sales-pill" :class="{active:activeTab===t.key, ['pill-'+t.key]: t.key!=='all'}"
          @click="activeTab=t.key">
          {{ t.label }}
          <span v-if="t.key!=='all'" class="sales-pill-count">{{ counts[t.key] }}</span>
        </button>
      </div>
      <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;flex-wrap:nowrap;">
        <button class="sales-btn-ghost view-toggle-btn" @click="viewMode=viewMode==='table'?'grid':'table'" :title="viewMode==='table'?'Grid View':'List View'"><span v-html="icon(viewMode==='table'?'grid':'file',14)"></span></button>
        <button class="sales-btn-ghost" @click="load" title="Refresh"><span v-html="icon('refresh',14)"></span></button>
        <button class="sales-btn-ghost" @click="exportCSV" title="Export CSV"><span v-html="icon('download',14)"></span> CSV</button>
        <button class="sales-btn-primary" @click="openNew" :disabled="!$canWrite('bills')" :title="!$canWrite('bills') ? 'Read-only access' : ''">
          <span v-html="icon('plus',13)"></span> New Purchase Order
        </button>
      </div>
    </div>

    <!-- ── KPI Cards ── -->
    <div class="bk-kpi-grid">
      <div class="bk-kpi-card bk-kpi-accent clickable" @click="activeTab='all'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#dbeafe"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.8"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Total POs</div><div class="bk-kpi-value">{{ list.length }}</div><div class="bk-kpi-trend" :class="poTrends.total.up?'bk-trend-up':'bk-trend-down'">{{ poTrends.total.up?'↑':'↓' }} {{ poTrends.total.pct }}% vs last month</div></div></div></div>
      <div class="bk-kpi-card clickable" @click="activeTab='draft'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#e2e8f0"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="1.8"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Draft</div><div class="bk-kpi-value">{{ counts.draft }}</div><div class="bk-kpi-trend" :class="poTrends.draft.up?'bk-trend-up':'bk-trend-down'">{{ poTrends.draft.up?'↑':'↓' }} {{ poTrends.draft.pct }}% vs last month</div></div></div></div>
      <div class="bk-kpi-card bk-kpi-warn clickable" @click="activeTab='toReceive'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#fef3c7"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="1.8"><rect x="1" y="3" width="15" height="13" rx="1"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">To Receive</div><div class="bk-kpi-value bk-kpi-amber">{{ counts.toReceive }}</div><div class="bk-kpi-trend" :class="poTrends.receive.up?'bk-trend-up':'bk-trend-down'">{{ poTrends.receive.up?'↑':'↓' }} {{ poTrends.receive.pct }}% vs last month</div></div></div></div>
      <div class="bk-kpi-card bk-kpi-info clickable" @click="activeTab='toBill'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#cffafe"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#0891b2" stroke-width="1.8"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">To Bill</div><div class="bk-kpi-value bk-kpi-blue">{{ counts.toBill }}</div><div class="bk-kpi-trend" :class="poTrends.bill.up?'bk-trend-up':'bk-trend-down'">{{ poTrends.bill.up?'↑':'↓' }} {{ poTrends.bill.pct }}% vs last month</div></div></div></div>
      <div class="bk-kpi-card bk-kpi-danger clickable" @click="activeTab='cancelled'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#fee2e2"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Cancelled</div><div class="bk-kpi-value bk-kpi-red">{{ counts.cancelled }}</div><div class="bk-kpi-trend" :class="poTrends.cancelled.up?'bk-trend-down':'bk-trend-up'">{{ poTrends.cancelled.up?'↑':'↓' }} {{ poTrends.cancelled.pct }}% vs last month</div></div></div></div>
    </div>
    <div class="bk-stat-grid">
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">This Month</div><div class="bk-stat-value">{{ poThisMonth.count }}</div></div><div class="bk-stat-icon" style="background:#dbeafe;color:#2563eb"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg></div></div></div>
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">This Month Value</div><div class="bk-stat-value bk-kpi-blue" style="font-size:16px">{{ fmtCur(poThisMonth.value) }}</div></div><div class="bk-stat-icon" style="background:#cffafe;color:#0891b2"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/></svg></div></div></div>
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">Procurement Value</div><div class="bk-stat-value bk-kpi-green" style="font-size:16px">{{ fmtCur(summary.totalValue) }}</div></div><div class="bk-stat-icon" style="background:#dcfce7;color:#16a34a"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12"/><path d="M6 8h12"/><path d="m6 13 8.5 8"/><path d="M6 13h3"/><path d="M9 13c6.667 0 6.667-10 0-10"/></svg></div></div></div>
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">Closed</div><div class="bk-stat-value bk-kpi-green">{{ counts.closed }}</div></div><div class="bk-stat-icon" style="background:#dcfce7;color:#16a34a"><svg width="18" height="18" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="#16a34a" stroke-width="1.8"/><polyline points="7 12.5 10.5 16 17 9" stroke="#16a34a" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></div></div></div>
    </div>

    <!-- ── Bulk action bar ── -->
    <BulkActionBar :count="selected.size" @clear="selected=new Set()">
      <button @click="bulkEmail"><span v-html="icon('mail',13)"></span> Send Email</button>
      <button class="bab-danger" @click="bulkDelete">Delete</button>
      <button @click="exportCSV"><span v-html="icon('download',13)"></span> Export CSV</button>
    </BulkActionBar>

    <!-- ── Table ── -->
    <div class="inv-table-wrap">
      <template v-if="viewMode==='table'">
      <table class="inv-table po-desktop-table">
        <thead>
          <tr>
            <th style="width:32px"><input type="checkbox" @change="toggleAll" :checked="allChecked" /></th>
            <th @click="sortBy('name')" class="sortable">PO # <span v-html="sortArrow('name')"></span></th>
            <th @click="sortBy('supplier_name')" class="sortable">Vendor <span v-html="sortArrow('supplier_name')"></span></th>
            <th @click="sortBy('transaction_date')" class="sortable">Date <span v-html="sortArrow('transaction_date')"></span></th>
            <th @click="sortBy('expected_delivery_date')" class="sortable">Expected <span v-html="sortArrow('expected_delivery_date')"></span></th>
            <th>Status</th>
            <th @click="sortBy('grand_total')" class="sortable ta-r">Amount <span v-html="sortArrow('grand_total')"></span></th>
            <th style="width:120px;text-align:center">Actions</th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 6" :key="n"><td colspan="8"><div class="shimmer"></div></td></tr>
          </template>
          <template v-else>
            <tr v-for="o in paged" :key="o.name" class="inv-row" :class="{selected:selected.has(o.name)}">
              <td class="td-check"><input type="checkbox" :checked="selected.has(o.name)" @change="toggle(o.name)" /></td>
              <td class="td-id" @click="openView(o)"><DocLink doctype="Purchase Order" :name="o.name" /></td>
              <td class="td-customer" @click="openView(o)">{{ o.supplier_name || o.supplier || '—' }}</td>
              <td class="td-date text-muted mono-sm" @click="openView(o)">{{ fmtDate(o.transaction_date) }}</td>
              <td class="td-due mono-sm" @click="openView(o)" :class="isPastExpected(o)?'text-danger':'text-muted'">{{ fmtDate(o.expected_delivery_date)||'—' }}</td>
              <td class="td-status" @click="openView(o)"><span class="inv-status-badge" :class="badgeClass(o)">{{ displayStatus(o) }}</span></td>
              <td class="td-amount ta-r mono-sm" @click="openView(o)">{{ fmtCur(o.grand_total) }}</td>
              <td class="td-actions po-act-cell">
                <button class="inv-act-btn" @click="openView(o)" title="View"><span v-html="icon('eye',13)"></span></button>
                <button v-if="canEdit(o)" class="inv-act-btn" @click="openEdit(o)" title="Edit"><span v-html="icon('edit',13)"></span></button>
                <button class="inv-act-btn po-act-conv" v-if="canBill(o)" @click="openBillModal(o)" title="Bill"><span v-html="icon('arrow-right',13)"></span></button>
                <button v-if="canDelete(o)" class="inv-act-btn po-act-del" @click="deletePO(o)" title="Delete"><span v-html="icon('trash',13)"></span></button>
              </td>
            </tr>
            <tr v-if="!sorted.length"><td colspan="8" class="po-empty">No purchase orders match</td></tr>
          </template>
        </tbody>
      </table>

      <!-- Mobile cards (shown at ≤768px) -->
      <div class="po-mobile-cards">
        <template v-if="loading">
          <div v-for="n in 5" :key="n" class="po-mobile-card po-mc--skeleton">
            <div class="po-mc-shimmer" style="height:13px;width:55%;margin-bottom:8px"></div>
            <div class="po-mc-shimmer" style="height:11px;width:40%;margin-bottom:6px"></div>
            <div class="po-mc-shimmer" style="height:11px;width:65%"></div>
          </div>
        </template>
        <div v-else-if="!sorted.length" class="po-mc-empty">
          <div style="font-size:32px;margin-bottom:8px">🛒</div>
          <div>No purchase orders found</div>
        </div>
        <template v-else>
          <div v-for="o in paged" :key="o.name" class="po-mobile-card" @click="openView(o)">
            <div class="po-mc-top">
              <span class="po-mc-docno">{{ o.name }}</span>
              <span class="inv-status-badge" :class="badgeClass(o)">{{ displayStatus(o) }}</span>
            </div>
            <div class="po-mc-mid">{{ o.supplier_name || o.supplier || '—' }}</div>
            <div class="po-mc-meta">
              <span>{{ fmtDate(o.transaction_date) }}</span>
              <span class="po-mc-amount">{{ fmtCur(o.grand_total) }}</span>
            </div>
            <div v-if="o.expected_delivery_date" class="po-mc-sub" :class="isPastExpected(o)?'text-danger':''">Expected: {{ fmtDate(o.expected_delivery_date) }}</div>
            <div class="po-mc-footer">
              <button class="po-mc-btn" @click.stop="openView(o)">View</button>
              <button v-if="canEdit(o)" class="po-mc-btn" @click.stop="openEdit(o)">Edit</button>
              <button v-if="canDelete(o)" class="po-mc-btn po-mc-danger" @click.stop="deletePO(o)">Delete</button>
            </div>
          </div>
        </template>
      </div>
      </template>
      <!-- GRID MODE -->
      <template v-else>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px;padding:24px 24px 24px">
          <template v-if="loading">
            <div v-for="n in 8" :key="n" class="b-card" style="padding:16px">
              <div class="b-shimmer" style="height:12px;width:60%;border-radius:4px;margin-bottom:10px"></div>
              <div class="b-shimmer" style="height:14px;width:80%;border-radius:4px;margin-bottom:8px"></div>
              <div class="b-shimmer" style="height:11px;width:45%;border-radius:4px"></div>
            </div>
          </template>
          <div v-else-if="!sorted.length" style="grid-column:1/-1;text-align:center;padding:40px 16px;color:#9ca3af;font-size:13px">
            <div style="font-size:32px;margin-bottom:8px">🛒</div>
            <div>{{ search ? 'No purchase orders match your filters' : 'No purchase orders yet' }}</div>
            <button v-if="!search" class="nim-btn nim-btn-primary" :disabled="!$canWrite('bills')" :title="!$canWrite('bills') ? 'Read-only access' : ''" style="margin-top:14px" @click="openNew"><span v-html="icon('plus',13)"></span> New Purchase Order</button>
          </div>
          <template v-else>
            <div v-for="o in paged" :key="o.name"
              class="b-card b-card-body"
              style="cursor:pointer;padding:16px;display:flex;flex-direction:column;gap:8px"
              @click="openView(o)">
              <div style="display:flex;align-items:center;justify-content:space-between;gap:8px">
                <span style="font-size:12px;font-weight:700;color:#2563eb">{{ o.name }}</span>
                <span class="inv-status-badge" :class="badgeClass(o)">{{ displayStatus(o) }}</span>
              </div>
              <div style="font-size:13.5px;font-weight:600;color:#1a1d23;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ o.supplier_name || o.supplier || '—' }}</div>
              <div style="display:flex;justify-content:space-between;font-size:12px;color:#6b7280">
                <span>{{ fmtDate(o.transaction_date) }}</span>
                <span style="font-weight:700;color:#1a1d23">{{ fmtCur(o.grand_total) }}</span>
              </div>
              <div v-if="o.expected_delivery_date" style="font-size:11.5px;" :class="isPastExpected(o)?'text-danger':'text-muted'">
                Expected: {{ fmtDate(o.expected_delivery_date) }}
              </div>
              <div style="display:flex;gap:6px;border-top:1px solid #f3f4f6;padding-top:10px">
                <button class="inv-act-btn" @click.stop="openView(o)" title="View"><span v-html="icon('eye',13)"></span></button>
                <button v-if="canEdit(o)" class="inv-act-btn" @click.stop="openEdit(o)" title="Edit"><span v-html="icon('edit',13)"></span></button>
              </div>
            </div>
          </template>
        </div>
      </template>
    </div>

    <!-- ── Pagination ── -->
    <div v-if="!loading && sorted.length" style="padding:12px 4px 4px">
      <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="sorted.length" />
    </div>

    <!-- ── Create / Edit Drawer ── -->
    <div v-if="drawerOpen" class="inv-drawer-bg" @click.self="drawerOpen=false"></div>
    <div class="inv-drawer-panel po-edit-drawer" :class="{open:drawerOpen}">

      <!-- Header -->
      <div class="inv-dh">
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
          <div class="inv-dh-title">{{ editingName ? 'Edit Purchase Order' : 'New Purchase Order' }}</div>
          <span v-if="!editingName" class="po-draft-badge">Draft</span>
        </div>
        <button class="inv-dclose" @click="drawerOpen=false"><span v-html="icon('x',16)"></span></button>
      </div>

      <div class="inv-dbody">

        <!-- ══ CARD 1: Order Details ══ -->
        <div class="add-card">
          <div class="add-card-header" @click="poCollapsed.details=!poCollapsed.details">
            <div class="add-card-title">
              <span class="add-card-title-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>
              </span>
              Order Details
            </div>
            <span class="add-card-chevron" :class="{collapsed:poCollapsed.details}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
          </div>
          <div class="add-card-body" :class="{collapsed:poCollapsed.details}">
            <!-- Purchase Type toggle -->
            <div class="po-type-toggle">
              <span class="inv-lbl">Purchase Type</span>
              <div class="po-type-btns">
                <button type="button"
                  class="po-type-btn" :class="{active: form.purchase_type === 'Goods'}"
                  @click="form.purchase_type = 'Goods'; if(!form.set_warehouse) fetchWarehouses('')">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="3" width="15" height="13" rx="1"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>
                  Goods
                </button>
                <button type="button"
                  class="po-type-btn" :class="{active: form.purchase_type === 'Services'}"
                  @click="form.purchase_type = 'Services'; form.set_warehouse = ''">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
                  Services
                </button>
              </div>
            </div>
            <div class="add-details-grid">
              <div style="grid-column:1/-1">
                <label class="inv-lbl">Vendor <span class="inv-req">*</span></label>
                <SearchableSelect v-model="form.supplier" :options="vendors" placeholder="Select vendor…"
                  :createable="true" createDoctype="Supplier" @search="fetchVendors" />
              </div>
              <div>
                <label class="inv-lbl">Order Date <span class="inv-req">*</span></label>
                <input v-model="form.transaction_date" type="date" class="inv-fi" />
              </div>
              <div>
                <label class="inv-lbl">Expected Delivery</label>
                <input v-model="form.expected_delivery_date" type="date" class="inv-fi" />
              </div>
              <!-- Warehouse: only shown and required for Goods -->
              <div v-if="form.purchase_type === 'Goods'" style="grid-column:1/-1">
                <label class="inv-lbl">Receiving Warehouse <span class="inv-req">*</span></label>
                <SearchableSelect v-model="form.set_warehouse" :options="warehouses" placeholder="Select warehouse where goods will be received…"
                  :createable="true" :staticCreate="true" createLabel="+ Create Warehouse" createDoctype="Warehouse" @search="fetchWarehouses" @create="fetchWarehouses('')" />
              </div>
            </div>
          </div>
        </div>

        <!-- ══ CARD 2: Addresses ══ -->
        <div class="add-card">
          <div class="add-card-header" @click="poCollapsed.address=!poCollapsed.address">
            <div class="add-card-title">
              <span class="add-card-title-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
              </span>
              Addresses
            </div>
            <span class="add-card-chevron" :class="{collapsed:poCollapsed.address}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
          </div>
          <div class="add-card-body" :class="{collapsed:poCollapsed.address}">
            <div class="inv-fg inv-fg2">
              <!-- Billing Address -->
              <div>
                <label class="inv-lbl">Billing Address</label>
                <div class="po-addr-select-wrap">
                  <SearchableSelect
                    v-model="form.billing_address_name"
                    :options="vendorAddresses"
                    valueKey="name" labelKey="label"
                    placeholder="— Select —"
                    :createable="true" :staticCreate="true"
                    createLabel="+ Add New Address"
                    @select="onBillingAddrSelect"
                    @create="openAddrModal('billing')"
                  />
                </div>
                <div v-if="selectedBillingAddr" class="po-addr-card">
                  <div class="po-addr-card-type">{{ selectedBillingAddr.address_type || 'Billing' }}</div>
                  <div class="po-addr-card-text">{{ formatAddress(selectedBillingAddr) }}</div>
                </div>
              </div>
              <!-- Delivery Address -->
              <div>
                <label class="inv-lbl">Delivery Address</label>
                <div class="po-addr-select-wrap">
                  <SearchableSelect
                    v-model="form.delivery_address_name"
                    :options="vendorAddresses"
                    valueKey="name" labelKey="label"
                    placeholder="— Select —"
                    :createable="true" :staticCreate="true"
                    createLabel="+ Add New Address"
                    @select="onDeliveryAddrSelect"
                    @create="openAddrModal('delivery')"
                  />
                </div>
                <div v-if="selectedDeliveryAddr" class="po-addr-card">
                  <div class="po-addr-card-type">{{ selectedDeliveryAddr.address_type || 'Delivery' }}</div>
                  <div class="po-addr-card-text">{{ formatAddress(selectedDeliveryAddr) }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ══ CARD 3: Line Items ══ -->
        <div class="add-card">
          <div class="add-card-header" @click="poCollapsed.lines=!poCollapsed.lines">
            <div class="add-card-title">
              <span class="add-card-title-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
              </span>
              Line Items
              <span class="po-item-count">{{ lines.length }} item{{ lines.length !== 1 ? 's' : '' }}</span>
            </div>
            <span class="add-card-chevron" :class="{collapsed:poCollapsed.lines}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
          </div>
          <div class="add-card-body" :class="{collapsed:poCollapsed.lines}">
            <div class="po-item-cards">
              <div v-for="(line, idx) in lines" :key="line.id" class="po-item-card">
                <div class="po-item-card-header" @click="line.collapsed=!line.collapsed" style="cursor:pointer">
                  <span class="po-item-card-num">#{{ idx + 1 }}</span>
                  <span class="po-item-card-title">{{ line.item_code || 'Line Item Detail' }}</span>
                  <div class="po-item-card-subtotal">
                    <span class="po-item-card-subtotal-label">SUBTOTAL</span>
                    <span class="po-item-card-amount">{{ fmtCur(line.amount) }}</span>
                  </div>
                  <span class="po-item-card-chevron" :class="{collapsed:line.collapsed}">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
                  </span>
                  <button @click.stop="removeLine(line.id)" class="po-item-card-rm"><span v-html="icon('x',16)"></span></button>
                </div>
                <div class="po-item-card-body" v-show="!line.collapsed">
                  <div class="po-item-col po-item-col--left">
                    <div class="po-item-field">
                      <label>Item Name</label>
                      <SearchableSelect v-model="line.item_code" :options="items"
                        placeholder="Select item…" :createable="true" createDoctype="Item"
                        @search="fetchItems" @select="v=>onItemSelect(line,v)" />
                    </div>
                    <div class="po-item-field" style="margin-top:14px">
                      <label>Description</label>
                      <textarea v-model="line.description" class="inv-fi po-item-desc-ta" :class="{'field-error': line.description && line.description.length > 500}" rows="4" maxlength="500" placeholder="Enter item description…"></textarea>
                      <div class="exp-field-hint" :class="{'exp-field-hint-err': line.description && line.description.length >= 500}">{{ (line.description || '').length }}/500 characters</div>
                    </div>
                  </div>
                  <div class="po-item-col po-item-col--right">
                    <div class="po-item-field">
                      <label>Tax Template</label>
                      <select v-model="line.tax_code" class="inv-fi">
                        <option value="">— No Tax —</option>
                        <option v-for="t in taxTemplates" :key="t.name" :value="t.name">{{ t.template_name || t.name }}</option>
                      </select>
                    </div>
                    <div class="po-item-num-row">
                      <div class="po-item-field">
                        <label>Qty</label>
                        <input v-model.number="line.qty" type="number" min="0" step="0.001" class="inv-fi" :class="{'field-error': line.qty > 999999999}" @input="calcLine(line)" />
                        <div v-if="line.qty > 999999999" class="exp-field-hint exp-field-hint-err">Max 9 digits</div>
                      </div>
                      <div class="po-item-field">
                        <label>Rate (₹)</label>
                        <input v-model.number="line.rate" type="number" min="0" step="0.01" class="inv-fi" :class="{'field-error': line.rate > 999999999}" @input="calcLine(line)" />
                        <div v-if="line.rate > 999999999" class="exp-field-hint exp-field-hint-err">Max 9 digits</div>
                      </div>
                    </div>
                    <div class="po-item-hint">Pricing is calculated based on current inventory stock and regional tax policies.</div>
                  </div>
                </div>
              </div>
            </div>
            <button class="inv-add-line-btn" style="margin-top:10px" @click="addLine"><span v-html="icon('plus',12)"></span> Add Item</button>

            <!-- Totals -->
            <div class="po-totals" style="margin-top:16px">
              <div style="font-size:12px;color:#6b7280">Tax is applied per item via Item Tax Template.</div>
              <div class="po-totals-right">
                <div class="po-total-row"><span>Subtotal</span><span>{{ fmtCur(subtotal) }}</span></div>
                <template v-for="tl in taxLines" :key="tl.template">
                  <div class="po-total-row"><span>{{ tl.template }} ({{ tl.rate }}%)</span><span>{{ fmtCur(tl.amount) }}</span></div>
                </template>
                <div v-if="!taxLines.length" class="po-total-row"><span>Tax</span><span>{{ fmtCur(0) }}</span></div>
                <div class="po-total-row grand"><span>Total</span><span>{{ fmtCur(grandTotal) }}</span></div>
              </div>
            </div>
          </div>
        </div>

        <!-- ══ CARD 4: Terms & Conditions ══ -->
        <div class="add-card">
          <div class="add-card-header" @click="poCollapsed.terms=!poCollapsed.terms">
            <div class="add-card-title">
              <span class="add-card-title-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
              </span>
              Terms &amp; Conditions
            </div>
            <span class="add-card-chevron" :class="{collapsed:poCollapsed.terms}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
          </div>
          <div class="add-card-body" :class="{collapsed:poCollapsed.terms}">
            <textarea v-model="form.terms" rows="4" class="inv-fi" :class="{'field-error': form.terms && form.terms.length > 500}" maxlength="500" placeholder="Payment terms, delivery conditions, special notes…"></textarea>
            <div class="exp-field-hint" :class="{'exp-field-hint-err': form.terms && form.terms.length >= 500}">{{ (form.terms || '').length }}/500 characters</div>
          </div>
        </div>

      </div><!-- /inv-dbody -->

      <!-- Footer -->
      <div class="inv-dfooter">
        <div class="add-footer-status">{{ editingName ? 'Editing: ' + editingName : 'New purchase order — unsaved' }}</div>
        <div class="add-footer-actions">
          <button class="add-btn-cancel" @click="drawerOpen=false">Cancel</button>
          <button class="add-btn-draft" :disabled="drawerSaving" @click="savePO('Draft')">
            <span v-html="icon('save',13)"></span> {{ drawerSaving ? 'Saving…' : 'Save Draft' }}
          </button>
          <button class="add-btn-more" :disabled="drawerSaving"
            @click="savePO(form.purchase_type === 'Services' ? 'To Receive' : 'To Receive')">
            <span v-html="icon('check',13)"></span>
            {{ drawerSaving ? 'Saving…' : (form.purchase_type === 'Services' ? 'Confirm Order' : 'Issue PO') }}
          </button>
        </div>
      </div>
    </div>

    <!-- ── View Drawer ── -->
    <div v-if="viewOpen" class="inv-drawer-bg" @click.self="viewOpen=false"></div>
    <div class="inv-drawer-panel inv-view-page po-view-drawer" :class="{open:viewOpen && viewDoc}">
      <template v-if="viewDoc">

        <!-- Header: PO number + badge | Bill CTA + Close -->
        <div class="inv-view-header">
          <div class="inv-view-header-left">
            <div class="inv-view-title-row">
              <span class="inv-view-number">{{ viewDoc.name }}</span>
              <span class="inv-hdr-badge" :class="badgeClass(viewDoc)">{{ displayStatus(viewDoc) }}</span>
              <span class="po-type-badge" :class="(viewDoc.purchase_type||'Goods')=== 'Goods' ? 'po-type-goods' : 'po-type-services'">
                {{ viewDoc.purchase_type || 'Goods' }}
              </span>
            </div>
            <div class="inv-view-subtitle">
              {{ viewDoc.supplier_name || viewDoc.supplier }}
              <span v-if="viewDoc.expected_delivery_date"> · Expected {{ fmtDate(viewDoc.expected_delivery_date) }}
                <span v-if="isPastExpected(viewDoc)" class="text-danger"> (overdue)</span>
              </span>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;flex-wrap:nowrap">
            <button v-if="canBill(viewDoc)" class="inv-view-cta" @click="openBillModal(viewDoc)">
              <span v-html="icon('arrow-right',15)"></span> Convert to Bill
            </button>
            <button class="inv-ab-btn" style="padding:7px 12px;font-size:13px;white-space:nowrap" @click="viewOpen=false">
              <span v-html="icon('x',14)"></span> <span class="ab-label">Close</span>
            </button>
          </div>
        </div>

        <!-- Main white card -->
        <div class="inv-view-body">

          <!-- Status timeline -->
          <div class="inv-tl-wrap">
            <TimelineStepper :steps="timelineSteps" />
          </div>

          <!-- Action buttons bar -->
          <div class="inv-action-bar">
            <button v-if="canEdit(viewDoc)" class="inv-ab-btn" @click="openEdit(viewDoc);viewOpen=false">
              <span v-html="icon('edit',13)"></span> <span class="ab-label">Edit</span>
            </button>
            <button v-if="canEdit(viewDoc)" class="inv-ab-btn" style="color:#16a34a;border-color:rgba(22,163,106,.3)" @click="submitPO(viewDoc)">
              <span v-html="icon('check',13)"></span> <span class="ab-label">Submit</span>
            </button>
            <button class="inv-ab-btn" @click="emailPO(viewDoc)">
              <span v-html="icon('mail',13)"></span> <span class="ab-label">Email</span>
            </button>
            <div style="position:relative;display:inline-flex">
              <button class="inv-ab-btn inv-ab-dropdown" @click="showDownloadMenu=!showDownloadMenu">
                <span v-html="icon('download',13)"></span> <span class="ab-label">Download</span>
                <span class="inv-ab-caret">▾</span>
              </button>
              <div v-if="showDownloadMenu" class="inv-dl-menu">
                <div class="inv-dl-menu-header">Export Purchase Order</div>
                <button @click="downloadPOPdf('pdf')" class="inv-dl-menu-item">
                  <span class="inv-dl-menu-icon" v-html="icon('download',14)"></span>
                  <span class="inv-dl-menu-text">
                    <span class="inv-dl-menu-label">Download PDF</span>
                    <span class="inv-dl-menu-sub">Save to your device</span>
                  </span>
                </button>
                <button @click="downloadPOPdf('print')" class="inv-dl-menu-item">
                  <span class="inv-dl-menu-icon" v-html="icon('printer',14)"></span>
                  <span class="inv-dl-menu-text">
                    <span class="inv-dl-menu-label">Open &amp; Print</span>
                    <span class="inv-dl-menu-sub">Preview in new tab</span>
                  </span>
                </button>
              </div>
            </div>
            <button v-if="hasUnreceived && (viewDoc?.purchase_type || 'Goods') === 'Goods' && (viewDoc?.status||'').toLowerCase() !== 'draft' && (viewDoc?.status||'').toLowerCase() !== '' && (viewDoc?.status||'').toLowerCase() !== 'cancelled'" class="inv-ab-btn" @click="markAllReceived" :disabled="actionRunning">
              <span v-html="icon('truck',13)"></span> <span class="ab-label">Mark Received</span>
            </button>
            <span class="inv-ab-spacer"></span>
            <button v-if="canCancel(viewDoc)" class="inv-ab-btn inv-ab-danger" @click="cancelPO(viewDoc)">
              Cancel
            </button>
            <button v-if="canDelete(viewDoc)" class="inv-ab-btn inv-ab-danger" @click="deletePO(viewDoc)">
              <span v-html="icon('trash',13)"></span> <span class="ab-label">Delete</span>
            </button>
          </div>

          <!-- Tabs -->
          <div class="inv-view-tabs">
            <button class="inv-vtab" :class="{active:viewTab==='details'}" @click="viewTab='details'">Details</button>
            <button v-if="(viewDoc.purchase_type || 'Goods') === 'Goods'" class="inv-vtab" :class="{active:viewTab==='fulfill'}" @click="viewTab='fulfill'">Fulfillment</button>
            <button class="inv-vtab" :class="{active:viewTab==='links'}" @click="viewTab='links'">
              Linked <span v-if="links.bills.length>0" class="inv-vtab-count">{{ links.bills.length }}</span>
            </button>
          </div>

          <!-- ── Details tab ── -->
          <template v-if="viewTab==='details'">
            <div class="inv-tab-body">

              <!-- Meta cards row -->
              <div class="inv-details-meta">
                <div class="inv-details-meta-col col-customer">
                  <div class="inv-dmeta-icon-row">
                    <span class="inv-dmeta-icon" v-html="icon('user',13)"></span>
                    <span class="inv-dmeta-lbl">Vendor</span>
                  </div>
                  <div class="inv-dmeta-primary">{{ viewDoc.supplier_name || viewDoc.supplier }}</div>
                </div>
                <div class="inv-details-meta-col">
                  <div class="inv-dmeta-icon-row">
                    <span class="inv-dmeta-icon" v-html="icon('calendar',13)"></span>
                    <span class="inv-dmeta-lbl">PO Date</span>
                  </div>
                  <div class="inv-dmeta-date-val">{{ fmtDateLong(viewDoc.transaction_date) }}</div>
                  <div class="inv-dmeta-date-sub">{{ fmtDateDay(viewDoc.transaction_date) }}</div>
                </div>
                <div class="inv-details-meta-col">
                  <div class="inv-dmeta-icon-row">
                    <span class="inv-dmeta-icon" v-html="icon('calendar',13)"></span>
                    <span class="inv-dmeta-lbl">Expected Delivery</span>
                  </div>
                  <div class="inv-dmeta-date-val" :class="{'is-overdue':isPastExpected(viewDoc)}">
                    {{ fmtDateLong(viewDoc.expected_delivery_date) || '—' }}
                  </div>
                  <div class="inv-dmeta-date-sub" v-if="viewDoc.expected_delivery_date">{{ fmtDateDay(viewDoc.expected_delivery_date) }}</div>
                </div>
                <div class="inv-details-meta-col col-balance">
                  <div class="inv-dmeta-icon-row">
                    <span class="inv-dmeta-icon" v-html="icon('indianrupee',13)"></span>
                    <span class="inv-dmeta-lbl">Total Value</span>
                  </div>
                  <div class="inv-balance-val">{{ fmtCur(viewDoc.grand_total) }}</div>
                </div>
              </div>

              <!-- Warehouse (Goods only) -->
              <div v-if="viewDoc.set_warehouse" class="inv-dmeta-row" style="padding:8px 0 4px">
                <div class="inv-dmeta-icon-row">
                  <span class="inv-dmeta-icon"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="3" width="15" height="13" rx="1"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg></span>
                  <span class="inv-dmeta-lbl">Receiving Warehouse</span>
                </div>
                <div style="font-size:13px;font-weight:600;color:#111827;margin-top:2px">{{ viewDoc.set_warehouse }}</div>
              </div>

              <!-- Addresses -->
              <div v-if="viewDoc.billing_address_name || viewDoc.delivery_address_name || viewDoc.billing_address || viewDoc.delivery_address" class="inv-bottom-grid" style="display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:0 0 4px">
                <div v-if="viewDoc.billing_address_name || viewDoc.billing_address">
                  <div class="inv-dmeta-icon-row" style="margin-bottom:6px">
                    <span class="inv-dmeta-icon" v-html="icon('map-pin',13)"></span>
                    <span class="inv-dmeta-lbl">Billing Address</span>
                  </div>
                  <div class="po-addr-card" style="margin-top:0">
                    <div v-if="viewBillingAddr" class="po-addr-card-type">{{ viewBillingAddr.address_type || 'Billing' }}</div>
                    <div class="po-addr-card-text">{{ viewBillingAddr ? formatAddress(viewBillingAddr) : viewDoc.billing_address }}</div>
                  </div>
                </div>
                <div v-if="viewDoc.delivery_address_name || viewDoc.delivery_address">
                  <div class="inv-dmeta-icon-row" style="margin-bottom:6px">
                    <span class="inv-dmeta-icon" v-html="icon('map-pin',13)"></span>
                    <span class="inv-dmeta-lbl">Delivery Address</span>
                  </div>
                  <div class="po-addr-card" style="margin-top:0">
                    <div v-if="viewDeliveryAddr" class="po-addr-card-type">{{ viewDeliveryAddr.address_type || 'Shipping' }}</div>
                    <div class="po-addr-card-text">{{ viewDeliveryAddr ? formatAddress(viewDeliveryAddr) : viewDoc.delivery_address }}</div>
                  </div>
                </div>
              </div>

              <!-- Line items -->
              <div v-if="viewLoading" style="text-align:center;padding:32px;color:#6b7280;font-size:13px">Loading…</div>
              <template v-else-if="viewItems.length">
                <div class="inv-sec-lbl">Line Items <span class="po-item-count">{{ viewItems.length }} item{{ viewItems.length !== 1 ? 's' : '' }}</span></div>
                <div class="vi-line-cards">
                  <div v-for="(it, idx) in viewItems" :key="it.name" class="vi-line-card">
                    <div class="vi-line-card-header">
                      <span class="vi-line-num">#{{ idx + 1 }}</span>
                      <span class="vi-line-name">{{ it.item_name || it.item_code }}</span>
                      <span class="vi-line-amount">{{ fmtCur(it.amount) }}</span>
                    </div>
                    <div v-if="it.description" class="vi-line-desc">{{ it.description }}</div>
                    <div class="vi-line-meta">
                      <div class="vi-line-meta-item">
                        <span class="vi-meta-lbl">Qty</span>
                        <span class="vi-meta-val">{{ it.qty }}</span>
                      </div>
                      <div class="vi-line-meta-item">
                        <span class="vi-meta-lbl">Rate</span>
                        <span class="vi-meta-val">{{ fmtCur(it.rate) }}</span>
                      </div>
                      <div class="vi-line-meta-item vi-line-tax" v-if="it.tax_code">
                        <span class="vi-tax-badge">TAX</span>
                        <span class="vi-meta-val" style="color:#4f46e5">{{ it.tax_code }}</span>
                      </div>
                      <div class="vi-line-meta-item vi-line-tax" v-else>
                        <span class="vi-notax-badge">NO TAX</span>
                      </div>
                    </div>
                  </div>
                </div>
              </template>

              <!-- Tax Summary -->
              <template v-if="viewItems.length">
                <div class="po-view-totals">
                  <div class="po-view-totals-inner">
                    <div class="po-view-total-row">
                      <span>Subtotal</span>
                      <span>{{ fmtCur(viewSubtotal) }}</span>
                    </div>
                    <template v-if="viewTaxLines.length">
                      <div v-for="tl in viewTaxLines" :key="tl.template" class="po-view-total-row po-view-tax-row">
                        <span class="po-view-tax-label">
                          <span class="po-view-tax-badge">TAX</span>
                          {{ tl.template }}
                          <span class="po-view-tax-rate">{{ tl.rate }}%</span>
                        </span>
                        <span>{{ fmtCur(tl.amount) }}</span>
                      </div>
                    </template>
                    <div v-else class="po-view-total-row po-view-tax-row">
                      <span class="po-view-tax-label">
                        <span class="po-view-tax-badge po-view-tax-badge--none">NO TAX</span>
                        No taxes applied
                      </span>
                      <span>{{ fmtCur(0) }}</span>
                    </div>
                    <div class="po-view-total-row po-view-grand">
                      <span>Grand Total</span>
                      <span>{{ fmtCur(viewGrandTotal) }}</span>
                    </div>
                  </div>
                </div>
              </template>

              <!-- Terms -->
              <div v-if="viewDoc.terms" class="po-terms">
                <div class="po-meta-lbl">Terms &amp; Conditions</div>
                <div style="white-space:pre-wrap;font-size:12.5px;color:#374151;margin-top:4px;word-break:break-word;overflow-wrap:anywhere">{{ viewDoc.terms }}</div>
              </div>

            </div>
          </template>

          <!-- ── Fulfillment tab ── -->
          <template v-else-if="viewTab==='fulfill'">
            <div class="inv-tab-body">
              <div v-if="viewLoading" style="text-align:center;padding:32px;color:#6b7280;font-size:13px">Loading…</div>
              <template v-else-if="fulfill.lines.length">
                <div style="font-size:12px;color:#6b7280;margin-bottom:12px">Status: <strong>{{ fulfill.computed_status }}</strong></div>

                <!-- Desktop table -->
                <div class="po-fulfill-tbl po-fulfill-desktop">
                  <div class="po-fulfill-head">
                    <span>Item</span><span class="ta-r">Ordered</span><span class="ta-r">Received</span>
                    <span class="ta-r">Billed</span><span class="ta-r">Remaining</span>
                  </div>
                  <div v-for="l in fulfill.lines" :key="l.name" class="po-fulfill-row">
                    <span>{{ l.item_name || l.item_code }}</span>
                    <span class="ta-r mono-sm">{{ l.qty }}</span>
                    <span class="ta-r mono-sm" :class="l.received_qty>=l.qty?'text-success':'text-muted'">{{ l.received_qty }}</span>
                    <span class="ta-r mono-sm" :class="l.billed_qty>=l.qty?'text-success':'text-muted'">{{ l.billed_qty }}</span>
                    <span class="ta-r mono-sm text-danger">{{ l.remaining_to_receive }} / {{ l.remaining_to_bill }}</span>
                  </div>
                </div>

                <!-- Mobile cards -->
                <div class="po-fulfill-mobile">
                  <div v-for="l in fulfill.lines" :key="l.name" class="po-fulfill-card">
                    <div class="po-fulfill-card-name">{{ l.item_name || l.item_code }}</div>
                    <div class="po-fulfill-card-grid">
                      <div class="po-fulfill-card-cell">
                        <span class="po-fulfill-card-lbl">Ordered</span>
                        <span class="po-fulfill-card-val">{{ l.qty }}</span>
                      </div>
                      <div class="po-fulfill-card-cell">
                        <span class="po-fulfill-card-lbl">Received</span>
                        <span class="po-fulfill-card-val" :class="l.received_qty>=l.qty?'text-success':'text-muted'">{{ l.received_qty }}</span>
                      </div>
                      <div class="po-fulfill-card-cell">
                        <span class="po-fulfill-card-lbl">Billed</span>
                        <span class="po-fulfill-card-val" :class="l.billed_qty>=l.qty?'text-success':'text-muted'">{{ l.billed_qty }}</span>
                      </div>
                      <div class="po-fulfill-card-cell">
                        <span class="po-fulfill-card-lbl">Remaining</span>
                        <span class="po-fulfill-card-val text-danger">{{ l.remaining_to_receive }} / {{ l.remaining_to_bill }}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div v-if="hasUnreceived && (viewDoc?.status||'').toLowerCase() !== 'draft' && (viewDoc?.status||'').toLowerCase() !== '' && (viewDoc?.status||'').toLowerCase() !== 'cancelled'" style="display:flex;justify-content:flex-end;margin-top:12px">
                  <button class="inv-view-cta" @click="markAllReceived" :disabled="actionRunning">
                    <span v-html="icon('truck',14)"></span> Mark All Received
                  </button>
                </div>
              </template>
              <div v-else style="text-align:center;padding:48px;color:#9ca3af;font-size:13px">No line items.</div>
            </div>
          </template>

          <!-- ── Linked tab ── -->
          <template v-else-if="viewTab==='links'">
            <div class="inv-tab-body">
              <div v-if="viewLoading" style="text-align:center;padding:32px;color:#6b7280;font-size:13px">Loading…</div>
              <template v-else>
                <template v-if="links.bills.length">
                  <div class="inv-sec-lbl">Vendor Bills</div>

                  <!-- Desktop table -->
                  <div class="inv-items-wrap po-bills-desktop">
                    <table class="inv-items-table">
                      <thead>
                        <tr>
                          <th>Bill #</th>
                          <th>Date</th>
                          <th class="th-r">Outstanding</th>
                          <th class="th-r">Total</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="b in links.bills" :key="b.name">
                          <td><DocLink doctype="Purchase Invoice" :name="b.name" /></td>
                          <td class="text-muted mono-sm">{{ fmtDate(b.posting_date) }}</td>
                          <td class="td-r mono-sm text-danger">{{ fmtCur(b.outstanding_amount) }}</td>
                          <td class="td-r mono-sm" style="font-weight:600">{{ fmtCur(b.grand_total) }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  <!-- Mobile cards -->
                  <div class="po-bills-mobile">
                    <div v-for="b in links.bills" :key="b.name" class="po-bill-card">
                      <div class="po-bill-card-top">
                        <span class="po-bill-card-name">{{ b.name }}</span>
                        <span class="po-bill-card-total">{{ fmtCur(b.grand_total) }}</span>
                      </div>
                      <div class="po-bill-card-meta">
                        <span class="text-muted">{{ fmtDate(b.posting_date) }}</span>
                        <span>
                          <span class="po-bill-card-lbl">Outstanding:</span>
                          <span class="text-danger" style="font-weight:600;margin-left:4px">{{ fmtCur(b.outstanding_amount) }}</span>
                        </span>
                      </div>
                    </div>
                  </div>
                </template>
                <div v-if="!links.bills.length" style="text-align:center;padding:48px;color:#9ca3af;font-size:13px">
                  No linked bills yet.
                  <div v-if="canBill(viewDoc)" style="margin-top:12px">
                    <button class="inv-view-cta" @click="openBillModal(viewDoc)">
                      <span v-html="icon('arrow-right',14)"></span> Convert to Bill
                    </button>
                  </div>
                </div>
              </template>
            </div>
          </template>

        </div><!-- /inv-view-body -->
      </template>
      </div><!-- /inv-drawer-panel -->

    <!-- ── Add New Address Modal ── -->
    <div v-if="addrModal.open" class="inv-drawer-bg" @click.self="addrModal.open=false" style="z-index:60"></div>
    <div v-if="addrModal.open" class="po-apply-dialog">
      <div class="inv-dh" style="height:auto;padding:14px 18px">
        <div class="inv-dh-title">Add New Address</div>
        <button class="inv-dclose" @click="addrModal.open=false"><span v-html="icon('x',16)"></span></button>
      </div>
      <div class="inv-dbody" style="padding:16px 18px;display:flex;flex-direction:column;gap:12px">
        <div class="inv-fg inv-fg2">
          <div>
            <label class="inv-lbl">Address Title <span class="inv-req">*</span></label>
            <input v-model="addrModal.address_title" type="text" class="inv-fi" placeholder="e.g. Head Office" />
          </div>
          <div>
            <label class="inv-lbl">Address Type</label>
            <select v-model="addrModal.address_type" class="inv-fi">
              <option>Billing</option>
              <option>Shipping</option>
              <option>Office</option>
              <option>Personal</option>
              <option>Plant</option>
              <option>Postal</option>
              <option>Shop</option>
              <option>Subsidiary</option>
              <option>Warehouse</option>
              <option>Other</option>
            </select>
          </div>
        </div>
        <div>
          <label class="inv-lbl">Address Line 1 <span class="inv-req">*</span></label>
          <input v-model="addrModal.address_line1" type="text" class="inv-fi" placeholder="Street / Building" />
        </div>
        <div>
          <label class="inv-lbl">Address Line 2</label>
          <input v-model="addrModal.address_line2" type="text" class="inv-fi" placeholder="Area / Locality" />
        </div>
        <div class="inv-fg inv-fg2">
          <div>
            <label class="inv-lbl">City</label>
            <input v-model="addrModal.city" type="text" class="inv-fi" placeholder="City" />
          </div>
          <div>
            <label class="inv-lbl">Country</label>
            <select v-model="addrModal.country" class="inv-fi" @change="addrModal.state = ''">
              <option value="">— Select Country —</option>
              <option v-for="c in COUNTRIES" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>
        </div>
        <div class="inv-fg inv-fg2">
          <div>
            <label class="inv-lbl">State</label>
            <select v-if="statesFor(addrModal.country).length" v-model="addrModal.state" class="inv-fi">
              <option value="">— Select State —</option>
              <option v-for="s in statesFor(addrModal.country)" :key="s" :value="s">{{ s }}</option>
            </select>
            <input v-else v-model="addrModal.state" type="text" class="inv-fi" placeholder="State" />
          </div>
          <div>
            <label class="inv-lbl">Pin Code</label>
            <input v-model="addrModal.pincode" type="text" class="inv-fi" placeholder="PIN" />
          </div>
        </div>
      </div>
      <div class="inv-dfooter">
        <button class="form-btn form-btn-outline" @click="addrModal.open=false" :disabled="addrModal.saving">Cancel</button>
        <button class="form-btn form-btn-primary" :disabled="addrModal.saving" @click="saveNewAddress">
          {{ addrModal.saving ? 'Saving…' : 'Save Address' }}
        </button>
      </div>
    </div>

    <!-- ── Convert-to-Bill modal (partial-qty + 3-way warn) ── -->
    <div v-if="billModal.open" class="inv-drawer-bg" @click.self="billModal.open=false" style="z-index:60"></div>
    <div v-if="billModal.open" class="po-apply-dialog">
      <div class="inv-dh" style="height:auto;padding:14px 18px">
        <div class="inv-dh-title">Convert to Bill — {{ billModal.poName }}</div>
        <button class="inv-dclose" @click="billModal.open=false"><span v-html="icon('x',16)"></span></button>
      </div>
      <div class="inv-dbody">
        <div style="font-size:12.5px;color:#374151">Enter the quantity to bill for each line (defaults to remaining):</div>
        <div class="po-inv-tbl">
          <div class="po-inv-head">
            <span>Item</span><span class="ta-r">Recv'd</span><span class="ta-r">Remaining</span><span class="ta-r">Bill</span>
          </div>
          <div v-for="l in billModal.lines" :key="l.name">
            <div class="po-inv-row" :class="{warn:l.toBill > (l.received_qty - l.billed_qty)}">
              <span>{{ l.item_name||l.item_code }}</span>
              <span class="ta-r mono-sm text-muted">{{ l.received_qty }}</span>
              <span class="ta-r mono-sm text-muted">{{ l.remaining_to_bill }}</span>
              <input v-model.number="l.toBill" type="number" min="0" :max="l.remaining_to_bill" step="0.001"
                class="inv-fi ta-r" style="width:90px" />
            </div>
            <div v-if="l.has_batch_no" style="display:grid;grid-template-columns:2fr 1fr;gap:6px;margin:4px 0 8px">
              <SearchableSelect v-model="l.batch_no" :options="l.batchOptions" placeholder="Batch No — select existing or type to create new"
                createable @search="q => fetchBillBatches(l, q)" @select="opt => onBillBatchSelect(l, opt)" @create="val => onBillBatchCreate(l, val)" style="font-size:12px"/>
              <span style="font-size:11px;color:#9ca3af;align-self:center">{{ l.batchOptions.length ? 'Batch-tracked — required' : 'No batches yet — type a new code' }}</span>
            </div>
          </div>
        </div>
        <div v-if="threeWayMismatch" class="po-warn">
          ⚠ Billing more than received on at least one line. Three-way match will fail. Proceed only if approved.
        </div>
        <div class="inv-fg inv-fg2">
          <div>
            <label class="inv-lbl">Vendor Bill #</label>
            <input v-model="billModal.billNo" type="text" class="inv-fi" />
          </div>
          <div>
            <label class="inv-lbl">Vendor Bill Date</label>
            <input v-model="billModal.billDate" type="date" class="inv-fi" />
          </div>
          <div style="grid-column:1/-1">
            <label class="inv-lbl">Due Date</label>
            <input v-model="billModal.dueDate" type="date" class="inv-fi" />
          </div>
        </div>
        <div style="text-align:right;font-size:13px;color:#6b7280">
          Bill Total: <strong style="color:#111827">{{ fmtCur(billModalTotal) }}</strong>
        </div>
      </div>
      <div class="inv-dfooter">
        <button class="form-btn form-btn-outline" @click="billModal.open=false" :disabled="billModal.saving">Cancel</button>
        <button class="form-btn form-btn-primary" :disabled="billModal.saving||billModalTotal<=0" @click="submitBill">
          {{ billModal.saving ? 'Creating…' : `Create Bill ${fmtCur(billModalTotal)}` }}
        </button>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from "vue";
import { apiList, apiSave, apiGet, apiGET, apiPOST, apiDelete, apiSubmit, resolveCompany, refreshCsrfToken } from "../api/client.js";
import { COUNTRIES, statesFor } from "../composables/useCountryState.js";
import { useToast } from "../composables/useToast.js";
import { useEmailDialog } from "../composables/useEmailDialog.js";
import { useConfirm } from "../composables/useConfirm.js";
import { useLivePreview } from "../composables/useLivePreview.js";
import { icon } from "../utils/icons.js";
import { flt, fmtDate } from "../utils/format.js";
import { templateHeadlineRate } from "../composables/useTaxCalc.js";
function fmtDateLong(d) {
  if (!d) return '';
  const dt = new Date(d);
  return dt.toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric' });
}
function fmtDateDay(d) {
  if (!d) return '';
  const dt = new Date(d);
  return dt.toLocaleDateString('en-IN', { weekday:'short', day:'2-digit', month:'short', year:'numeric' });
}
import SearchableSelect from "../components/SearchableSelect.vue";
import SummaryStrip from "../components/SummaryStrip.vue";
import Pagination from "../components/Pagination.vue";
import { usePagination } from "../composables/usePagination.js";
import BulkActionBar from "../components/BulkActionBar.vue";
import TimelineStepper from "../components/TimelineStepper.vue";
import DocLink from "../components/DocLink.vue";
import { useRoute } from "vue-router";
import { useOpenFromQuery } from "../composables/useOpenFromQuery.js";

const { toast } = useToast();
const { confirm } = useConfirm();
const { printDoc, renderDocument, setCompany, refreshBranding } = useLivePreview();
async function printPO(d) { try { await refreshBranding(); } catch {} printDoc({ ...d, items: viewItems.value }, { title: "PURCHASE ORDER", partyLabel: "Vendor", partyField: "supplier_name", companyName: d?.company || "" }); }

const showDownloadMenu = ref(false);

function downloadPOPdf(mode = 'pdf') {
  showDownloadMenu.value = false;
  const doc = { ...viewDoc.value, items: viewItems.value };
  if (!doc?.name) return;
  const html = renderDocument(doc, {
    title: "PURCHASE ORDER",
    partyLabel: "Vendor",
    partyField: "supplier_name",
    companyName: doc.company || window.__booksCompany || "",
  });
  if (mode === 'print') {
    const win = window.open('', '_blank');
    if (!win) { toast('Pop-up blocked \u2014 allow pop-ups to print', 'error'); return; }
    win.document.write(html); win.document.close();
    setTimeout(() => { try { win.focus(); win.print(); } catch {} }, 600);
  } else {
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
    const objectUrl = URL.createObjectURL(blob);
    const win = window.open(objectUrl, '_blank');
    if (!win) { URL.revokeObjectURL(objectUrl); toast('Pop-up blocked \u2014 allow pop-ups to download', 'error'); return; }
    win.addEventListener('load', () => {
      try { win.document.title = `${doc.name}.pdf`; win.focus(); win.print(); } catch {}
      setTimeout(() => URL.revokeObjectURL(objectUrl), 5000);
    });
  }
}
function onDocClickForDownloadMenu(e) {
  if (!e.target.closest('.inv-ab-dropdown') && !e.target.closest('.inv-dl-menu')) {
    showDownloadMenu.value = false;
  }
}

const { openEmail } = useEmailDialog();

const activeTab = ref("all");
const tabs = [
  { key: "all",       label: "All" },
  { key: "draft",     label: "Draft" },
  { key: "toReceive", label: "To Receive" },
  { key: "toBill",    label: "To Bill" },
  { key: "closed",    label: "Closed" },
  { key: "cancelled", label: "Cancelled" },
];

const list = ref([]), loading = ref(false), search = ref(""), selected = ref(new Set());
const viewMode = ref("table"); // "table" | "grid"
const drawerOpen = ref(false), drawerSaving = ref(false), editingName = ref("");
const poCollapsed = reactive({ details: false, address: true, lines: false, terms: true });
const viewOpen = ref(false), viewDoc = ref(null), viewTab = ref("details");
const viewLoading = ref(false), viewItems = ref([]);
const fulfill = reactive({ lines: [], computed_status: "" });
const links = reactive({ bills: [], purchase_receipts: [] });
const vendors = ref([]), items = ref([]), lines = ref([]), taxAccountHead = ref("");
const taxTemplates = ref([]);
const sortCol = ref("transaction_date"), sortDir = ref("desc");
const actionRunning = ref(false);
const vendorAddresses = ref([]);
const addrModal = reactive({
  open: false, saving: false, forField: "",
  address_title: "", address_type: "Billing", address_line1: "", address_line2: "",
  city: "", state: "", pincode: "", country: "India",
});

let _id = 1;
const blankLine = () => ({ id: _id++, item_code: "", description: "", qty: 1, rate: 0, amount: 0, tax_code: "", collapsed: false });
const form = reactive({
  supplier: "", transaction_date: todayStr(), expected_delivery_date: expectedDefault(),
  billing_address: "", delivery_address: "",
  billing_address_name: "", delivery_address_name: "",
  set_warehouse: "", purchase_type: "Goods", terms: "",
});
const warehouses = ref([]);
async function fetchWarehouses(q = "") {
  try {
    const co = await resolveCompany();
    const rows = await apiList("Warehouse", { filters: [["company","=",co],["disabled","=",0],["is_group","=",0]], fields: ["name","parent_warehouse"], limit: 50 });
    warehouses.value = (rows || [])
      .filter(r => !q || r.name.toLowerCase().includes(q.toLowerCase()) || (r.parent_warehouse||"").toLowerCase().includes(q.toLowerCase()))
      .map(r => ({ label: r.parent_warehouse ? `${r.parent_warehouse} / ${r.name}` : r.name, value: r.name }));
  } catch { warehouses.value = []; }
}

const billModal = reactive({ open: false, saving: false, poName: "", lines: [],
  billNo: "", billDate: "", dueDate: "" });

function todayStr() { return new Date().toISOString().slice(0, 10); }
function expectedDefault() { const d = new Date(); d.setDate(d.getDate() + 7); return d.toISOString().slice(0, 10); }
function fmtCur(v) { return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 2 }).format(flt(v)); }

function isPastExpected(o) {
  if (!o?.expected_delivery_date) return false;
  const s = (o.status||"").toLowerCase();
  if (s === "closed" || s === "billed" || s === "cancelled" || s === "received") return false;
  return new Date(o.expected_delivery_date) < new Date();
}
function displayStatus(o) { return (o?.status || "Draft").toUpperCase(); }
function badgeClass(o) {
  const s = (o?.status||"").toLowerCase();
  if (!s || s === "draft")  return "status-draft";
  if (s === "cancelled")    return "status-cancelled";
  if (s === "closed" || s === "billed") return "status-closed";
  if (s.includes("received") && !s.includes("partially")) return "status-submitted";
  if (s === "to receive" || s.includes("partially") || s === "sent" || s === "confirmed") return "status-open";
  return "status-submitted";
}
function headerBg(o) {
  const s = (o?.status||"").toLowerCase();
  if (s === "cancelled") return "linear-gradient(135deg,#7f1d1d,#dc2626)";
  if (s === "closed" || s === "billed") return "linear-gradient(135deg,#064e3b,#059669)";
  if (s === "to receive" || s.includes("partially") || s === "sent" || s === "confirmed") return "linear-gradient(135deg,#78350f,#d97706)";
  if (s === "received") return "linear-gradient(135deg,#1e3a5f,#1a6ef7)";
  return "linear-gradient(135deg,#374151,#6b7280)";
}
function canBill(o) {
  const s = (o?.status||"").toLowerCase();
  return s !== "draft" && s !== "" && s !== "cancelled" && s !== "closed" && s !== "billed";
}
function canEdit(o) {
  const s = (o?.status||"").toLowerCase();
  return s === "draft" || s === "";
}
function canCancel(o) {
  const s = (o?.status||"").toLowerCase();
  // Allow cancel from any status except already-cancelled
  return s !== "cancelled";
}
function canDelete(o) {
  const s = (o?.status||"").toLowerCase();
  // Only allow delete on draft or cancelled (never on live/closed orders)
  return s === "draft" || s === "" || s === "cancelled";
}

async function load() {
  loading.value = true;
  try {
    const co = await resolveCompany();
    list.value = await apiList("Purchase Order", {
      fields: ["name", "supplier", "supplier_name", "transaction_date", "expected_delivery_date", "status", "grand_total", "billed_amount", "billing_address", "delivery_address", "billing_address_name", "delivery_address_name"],
      filters: [["company", "=", co]],
      limit: 100000,
      order: "transaction_date desc, creation desc",
    });
  } catch (e) { toast.error(e.message || "Failed to load purchase orders"); }
  finally { loading.value = false; }
}
async function loadTaxAccount() {
  try {
    const r = await apiList("Account", { fields: ["name"], filters: [["account_type", "=", "Tax"], ["is_group", "=", 0]], limit: 1 });
    if (r?.length) taxAccountHead.value = r[0].name;
  } catch {}
  try {
    // Fetch all Item Tax Templates and their first tax rate
    const templates = await apiList("Tax Template", { fields: ["name", "template_name"], filters: [["disabled", "=", 0]], limit: 100, order: "template_name asc" });
    const withRates = await Promise.all((templates || []).map(async t => {
      try {
        const doc = await apiGet("Tax Template", t.name);
        const rate = templateHeadlineRate(doc?.taxes);
        const account = doc?.taxes?.[0]?.account_head || taxAccountHead.value;
        return { name: t.name, template_name: t.template_name, rate: Number(rate), account };
      } catch { return { name: t.name, template_name: t.template_name, rate: 0, account: taxAccountHead.value }; }
    }));
    taxTemplates.value = withRates;
  } catch { taxTemplates.value = []; }
}

const counts = computed(() => {
  const c = { draft:0, toReceive:0, toBill:0, closed:0, cancelled:0 };
  for (const o of list.value) {
    const s = (o.status||"draft").toLowerCase();
    if (s === "cancelled") c.cancelled++;
    else if (s === "closed" || s === "billed") c.closed++;
    else if (s === "draft") c.draft++;
    else if (s === "received") c.toBill++;
    else c.toReceive++;
  }
  return c;
});
const summary = computed(() => ({
  totalValue: list.value.filter(o => (o.status||"").toLowerCase() !== "cancelled")
    .reduce((s, o) => s + flt(o.grand_total), 0),
}));
const _poYM  = () => { const d=new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; };
const _poLYM = () => { const d=new Date(); d.setMonth(d.getMonth()-1); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; };
const _poTr  = (a,b) => { if(!b&&!a) return {pct:0,up:true}; if(!b) return {pct:100,up:true}; const p=Math.round((a-b)/b*100); return {pct:Math.abs(p),up:p>=0}; };
const poThisMonth = computed(()=>{ const ym=_poYM(); const r=list.value.filter(o=>(o.transaction_date||'').startsWith(ym)); return {count:r.length,value:r.reduce((s,o)=>s+flt(o.grand_total),0)}; });
const poTrends = computed(()=>({
  total:     _poTr(poThisMonth.value.count, list.value.filter(o=>(o.transaction_date||'').startsWith(_poLYM())).length),
  draft:     _poTr(counts.value.draft, list.value.filter(o=>(o.transaction_date||'').startsWith(_poLYM())&&o.docstatus===0).length),
  receive:   _poTr(counts.value.toReceive, list.value.filter(o=>(o.transaction_date||'').startsWith(_poLYM())&&(o.status||'').toLowerCase()!=='cancelled'&&(o.status||'').toLowerCase()!=='closed').length),
  bill:      _poTr(counts.value.toBill, list.value.filter(o=>(o.transaction_date||'').startsWith(_poLYM())&&(o.status||'').toLowerCase()==='received').length),
  cancelled: _poTr(counts.value.cancelled, list.value.filter(o=>(o.transaction_date||'').startsWith(_poLYM())&&(o.status||'').toLowerCase()==='cancelled').length),
}));

const filtered = computed(() => {
  let r = list.value;
  if (activeTab.value !== "all") {
    r = r.filter(o => {
      const s = (o.status||"draft").toLowerCase();
      if (activeTab.value === "draft")     return s === "draft";
      if (activeTab.value === "cancelled") return s === "cancelled";
      if (activeTab.value === "closed")    return s === "closed" || s === "billed";
      if (activeTab.value === "toBill")    return s === "received";
      if (activeTab.value === "toReceive") return s !== "cancelled" && s !== "closed" && s !== "billed" && s !== "draft" && s !== "received";
      return true;
    });
  }
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    r = r.filter(x => (x.name || "").toLowerCase().includes(q)
      || (x.supplier_name || x.supplier || "").toLowerCase().includes(q));
  }
  return r;
});
const sorted = computed(() => {
  const col = sortCol.value;
  return [...filtered.value].sort((a, b) => {
    const av = a[col] ?? "", bv = b[col] ?? "";
    const c = typeof av === "number" ? av - bv : String(av).localeCompare(String(bv));
    return sortDir.value === "asc" ? c : -c;
  });
});
const { page, pageSize, paged } = usePagination(sorted, { storageKey: "purchase-orders" });
function sortBy(col) { if (sortCol.value === col) sortDir.value = sortDir.value === "asc" ? "desc" : "asc"; else { sortCol.value = col; sortDir.value = "asc"; } }
function sortArrow(col) { if (sortCol.value !== col) return '<span style="color:#d1d5db">⇅</span>'; return sortDir.value === "asc" ? "↑" : "↓"; }

const allChecked = computed(() => sorted.value.length > 0 && sorted.value.every(o => selected.value.has(o.name)));
function toggle(n) { const s = new Set(selected.value); s.has(n) ? s.delete(n) : s.add(n); selected.value = s; }
function toggleAll(e) { selected.value = e.target.checked ? new Set(sorted.value.map(o => o.name)) : new Set(); }

const subtotal = computed(() => lines.value.reduce((s, l) => s + flt(l.amount), 0));

// Group tax by template name → { name, rate, amount }
const taxLines = computed(() => {
  const map = {};
  for (const l of lines.value) {
    if (!l.tax_code || !l.amount) continue;
    const tmpl = taxTemplates.value.find(t => t.name === l.tax_code);
    const rate = tmpl?.rate ?? 0;
    if (!rate) continue;
    if (!map[l.tax_code]) map[l.tax_code] = { template: l.tax_code, rate, amount: 0 };
    map[l.tax_code].amount += Math.round(flt(l.amount) * rate / 100 * 100) / 100;
  }
  return Object.values(map);
});
const taxAmount = computed(() => taxLines.value.reduce((s, t) => s + t.amount, 0));
const grandTotal = computed(() => subtotal.value + taxAmount.value);

const hasUnreceived = computed(() => fulfill.lines.some(l => l.remaining_to_receive > 0));

// ── View drawer tax summary ───────────────────────────────────────────────
const viewSubtotal = computed(() => viewItems.value.reduce((s, i) => s + flt(i.amount), 0));

const viewTaxLines = computed(() => {
  const map = {};
  for (const i of viewItems.value) {
    if (!i.tax_code || !i.amount) continue;
    const tmpl = taxTemplates.value.find(t => t.name === i.tax_code);
    const rate = tmpl?.rate ?? 0;
    if (!rate) continue;
    if (!map[i.tax_code]) map[i.tax_code] = { template: i.tax_code, rate, amount: 0 };
    map[i.tax_code].amount += Math.round(flt(i.amount) * rate / 100 * 100) / 100;
  }
  return Object.values(map);
});

const viewTaxAmount = computed(() => viewTaxLines.value.reduce((s, t) => s + t.amount, 0));
const viewGrandTotal = computed(() => viewSubtotal.value + viewTaxAmount.value);

const timelineSteps = computed(() => {
  const o = viewDoc.value;
  if (!o) return [];
  const s = (o.status||"").toLowerCase();
  if (s === "cancelled") {
    return [
      { key:"draft", label:"Draft", done:true },
      { key:"sub",   label:"Issued", done:true },
      { key:"end",   label:"Cancelled", danger:true, current:true },
    ];
  }
  const received = s === "received" || s === "billed" || s === "closed";
  const billed   = s === "billed"   || s === "closed";
  const closed   = s === "closed";
  return [
    { key:"draft",    label:"Draft",    done:true },
    { key:"issued",   label:"Issued",   done:s!=="draft", current:s==="to receive"||s==="sent"||s==="confirmed" },
    { key:"received", label:"Received", done:received, current:s==="received" && !billed },
    { key:"billed",   label:"Billed",   done:billed, current:billed && !closed },
    { key:"closed",   label:"Closed",   done:closed, current:closed },
  ];
});

const billModalTotal = computed(() =>
  (billModal.lines || []).reduce((s, l) => s + flt(l.toBill) * flt(l.rate), 0)
);
const threeWayMismatch = computed(() =>
  (billModal.lines || []).some(l => flt(l.toBill) > (flt(l.received_qty) - flt(l.billed_qty)))
);

// ── Create / Edit ─────────────────────────────────────────────────────────
function openNew() {
  editingName.value = "";
  Object.assign(form, { supplier: "", transaction_date: todayStr(), expected_delivery_date: expectedDefault(), billing_address: "", delivery_address: "", billing_address_name: "", delivery_address_name: "", set_warehouse: "", purchase_type: "Goods", terms: "" });
  fetchWarehouses("");
  lines.value = [blankLine()];
  fetchVendors(""); fetchItems("");
  drawerOpen.value = true;
}
async function openEdit(o) {
  editingName.value = o.name;
  Object.assign(form, {
    supplier: o.supplier || "", transaction_date: o.transaction_date || todayStr(),
    expected_delivery_date: o.expected_delivery_date || expectedDefault(),
    billing_address: o.billing_address || "", delivery_address: o.delivery_address || "",
    billing_address_name: "", delivery_address_name: "",
    set_warehouse: "", purchase_type: o.purchase_type || "Goods", terms: o.terms || "",
  });
  lines.value = [blankLine()];
  fetchVendors(""); fetchItems(""); fetchWarehouses("");
  if (o.supplier) fetchVendorAddresses(o.supplier);
  drawerOpen.value = true;
  try {
    const doc = await apiGet("Purchase Order", o.name);
    if (doc?.items?.length) {
      lines.value = doc.items.map(i => ({
        id: _id++, item_code: i.item_code || "", description: i.description || "",
        qty: i.qty || 1, rate: i.rate || 0, amount: i.amount || 0,
        tax_code: i.tax_code || "",
      }));
    }
    if (doc?.set_warehouse) form.set_warehouse = doc.set_warehouse;
    if (doc?.terms) form.terms = doc.terms;
    // Restore address link fields — wait for vendorAddresses to load first
    if (doc?.billing_address_name || doc?.delivery_address_name) {
      await fetchVendorAddresses(doc.supplier || o.supplier);
      if (doc.billing_address_name) {
        form.billing_address_name = doc.billing_address_name;
        const a = vendorAddresses.value.find(x => x.name === doc.billing_address_name);
        if (a) form.billing_address = formatAddress(a);
      }
      if (doc.delivery_address_name) {
        form.delivery_address_name = doc.delivery_address_name;
        const a = vendorAddresses.value.find(x => x.name === doc.delivery_address_name);
        if (a) form.delivery_address = formatAddress(a);
      }
    }
  } catch {}
}
async function openView(o) {
  viewDoc.value = o;
  viewOpen.value = true;
  viewTab.value = "details";
  viewLoading.value = true;
  viewItems.value = [];
  fulfill.lines = []; fulfill.computed_status = "";
  links.bills = []; links.purchase_receipts = [];
  try {
    const [doc, ful, lnk] = await Promise.all([
      apiGet("Purchase Order", o.name),
      apiGET("zoho_books_clone.api.docs.get_purchase_order_fulfillment", { purchase_order: o.name }).catch(() => null),
      apiGET("zoho_books_clone.api.docs.get_purchase_order_links", { purchase_order: o.name }).catch(() => null),
    ]);
    viewItems.value = doc?.items || [];
    viewDoc.value = { ...o, ...doc };
    // Resolve address objects for view drawer cards
    const addrNames = [doc?.billing_address_name, doc?.delivery_address_name].filter(Boolean);
    for (const n of addrNames) {
      if (!viewAddressCache.value[n]) {
        apiGet("Address", n).then(a => { if (a) viewAddressCache.value = { ...viewAddressCache.value, [n]: a }; }).catch(() => {});
      }
    }
    if (ful) { fulfill.lines = ful.lines || []; fulfill.computed_status = ful.computed_status || ""; }
    if (lnk) { links.bills = lnk.bills || []; }
  } catch {}
  viewLoading.value = false;
}

async function fetchVendorAddresses(supplier) {
  if (!supplier) { vendorAddresses.value = []; return; }
  try {
    const links = await apiList("Dynamic Link", {
      fields: ["parent"], filters: [["link_doctype","=","Supplier"],["link_name","=",supplier],["parenttype","=","Address"]], limit: 50
    });
    if (!links?.length) { vendorAddresses.value = []; return; }
    const names = links.map(l => l.parent);
    const addrs = await Promise.all(names.map(n => apiGet("Address", n).catch(() => null)));
    vendorAddresses.value = addrs.filter(Boolean).map(a => {
      const rawTitle = a.address_title || a.name || "";
      // Strip leading supplier-name prefix Frappe auto-generates (e.g. "Acme Corp-Billing" → "Billing")
      const escaped = supplier.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const cleaned = rawTitle.replace(new RegExp("^" + escaped + "[-\\s]*", "i"), "").trim() || rawTitle;
      const title = cleaned || a.address_type || "Address";
      return {
        ...a,
        label: `${title}${a.city ? " — " + a.city : ""}${a.address_type ? " (" + a.address_type + ")" : ""}`,
      };
    });
  } catch { vendorAddresses.value = []; }
}

const selectedBillingAddr = computed(() =>
  vendorAddresses.value.find(a => a.name === form.billing_address_name) || null
);
const selectedDeliveryAddr = computed(() =>
  vendorAddresses.value.find(a => a.name === form.delivery_address_name) || null
);

// Resolved address objects for the view drawer
const viewAddressCache = ref({});
const viewBillingAddr = computed(() =>
  viewDoc.value?.billing_address_name ? (viewAddressCache.value[viewDoc.value.billing_address_name] || null) : null
);
const viewDeliveryAddr = computed(() =>
  viewDoc.value?.delivery_address_name ? (viewAddressCache.value[viewDoc.value.delivery_address_name] || null) : null
);

function formatAddress(a) {
  if (!a) return "";
  return [a.address_line1, a.address_line2, a.city, a.state, a.pincode, a.country]
    .filter(Boolean).join("\n");
}

function onBillingAddrSelect(opt) {
  form.billing_address = opt ? formatAddress(opt) : "";
}
function onDeliveryAddrSelect(opt) {
  form.delivery_address = opt ? formatAddress(opt) : "";
}
function openAddrModal(field) {
  const addrType = field === "billing" ? "Billing" : "Shipping";
  Object.assign(addrModal, { open: true, saving: false, forField: field, address_title: "", address_type: addrType, address_line1: "", address_line2: "", city: "", state: "", pincode: "", country: "India" });
}

async function saveNewAddress() {
  if (!addrModal.address_title.trim()) return toast.error("Address Title is required");
  if (!addrModal.address_line1.trim()) return toast.error("Address Line 1 is required");
  addrModal.saving = true;
  try {
    const doc = {
      doctype: "Address",
      address_title: addrModal.address_title,
      address_type: addrModal.address_type,
      address_line1: addrModal.address_line1,
      address_line2: addrModal.address_line2 || "",
      city: addrModal.city || "",
      state: addrModal.state || "",
      pincode: addrModal.pincode || "",
      country: addrModal.country || "India",
      links: form.supplier ? [{ doctype: "Address", link_doctype: "Supplier", link_name: form.supplier }] : [],
    };
    const saved = await apiSave(doc);
    toast.success("Address saved");
    await fetchVendorAddresses(form.supplier);
    const newAddr = vendorAddresses.value.find(a => a.name === saved?.name) || vendorAddresses.value[vendorAddresses.value.length - 1];
    if (newAddr) {
      if (addrModal.forField === "billing") {
        form.billing_address_name = newAddr.name;
        form.billing_address = formatAddress(newAddr);
      } else {
        form.delivery_address_name = newAddr.name;
        form.delivery_address = formatAddress(newAddr);
      }
    }
    addrModal.open = false;
  } catch (e) { toast.error(e.message || "Failed to save address"); }
  addrModal.saving = false;
}

async function fetchVendors(q = "") {
  try {
    const f = [["disabled", "=", 0]];
    if (q) f.push(["supplier_name", "like", "%" + q + "%"]);
    const r = await apiList("Supplier", { fields: ["name", "supplier_name"], filters: f, limit: 30, order: "supplier_name asc" });
    vendors.value = r.map(x => ({ ...x, label: x.supplier_name || x.name, value: x.name }));
  } catch { vendors.value = []; }
}
async function fetchItems(q = "") {
  try {
    const f = [["disabled", "=", 0]];
    if (q) f.push(["item_name", "like", "%" + q + "%"]);
    const r = await apiList("Item", { fields: ["name", "item_name", "description", "standard_rate", "standard_buying_rate", "stock_uom", "tax_code"], filters: [...f, ["has_variants", "=", 0], ["is_purchase_item", "=", 1]], limit: 30, order: "item_name asc" });
    items.value = r.map(x => ({ ...x, label: x.item_name || x.name, value: x.name, rate: x.standard_buying_rate || x.standard_rate || 0, description: x.description || "", tax_code: x.tax_code || "" }));
  } catch { items.value = []; }
}
async function onItemSelect(line, opt) {
  line.item_code = opt?.value ?? opt;
  if (opt?.rate !== undefined) { line.rate = Number(opt.rate) || 0; }
  if (opt?.item_name)   { line.item_name   = opt.item_name; }
  if (opt?.tax_code !== undefined) { line.tax_code = opt.tax_code || ""; }
  if (opt?.description) { line.description = opt.description; }
  else if (opt?.value) {
    // description not in option cache — fetch from Item doc directly
    try {
      const doc = await apiGet("Item", opt.value);
      if (doc?.description) line.description = doc.description;
      if (doc?.item_name)   line.item_name   = doc.item_name;
      if (doc?.tax_code) line.tax_code = doc.tax_code;
    } catch {}
  }
  calcLine(line);
}
function addLine() { lines.value.push(blankLine()); }
function removeLine(id) { if (lines.value.length > 1) lines.value = lines.value.filter(l => l.id !== id); }
function calcLine(l) { l.amount = Math.round(flt(l.qty) * flt(l.rate) * 100) / 100; }

async function savePO(newStatus) {
  if (!form.supplier) return toast.error("Vendor is required");
  if (!lines.value.some(l => l.item_code && flt(l.qty) > 0)) return toast.error("At least one item required");
  if (form.purchase_type === "Goods" && !form.set_warehouse) return toast.error("Receiving Warehouse is required for Goods orders");
  if ((form.terms || "").length > 500) return toast.error("Terms & Conditions cannot exceed 500 characters");
  for (const l of lines.value.filter(l => l.item_code)) {
    if (flt(l.qty) > 999999999) return toast.error(`Qty cannot exceed 9 digits for item "${l.item_code}"`);
    if (flt(l.rate) > 999999999) return toast.error(`Rate cannot exceed 9 digits for item "${l.item_code}"`);
    if ((l.description || "").length > 500) return toast.error(`Description too long for item "${l.item_code}" (max 500 characters)`);
  }
  drawerSaving.value = true;
  try {
    const company = await resolveCompany();
    // Build taxes array from unique tax_code entries on lines
    const taxMap = {};
    for (const l of lines.value.filter(l => l.item_code)) {
      if (!l.tax_code) continue;
      const tmpl = taxTemplates.value.find(t => t.name === l.tax_code);
      if (!tmpl) continue;
      if (!taxMap[l.tax_code]) {
        const desc = (l.tax_code || "").toUpperCase();
        const tax_type = desc.startsWith("CGST") ? "CGST"
          : desc.startsWith("SGST") ? "SGST"
          : desc.startsWith("IGST") ? "IGST"
          : desc.startsWith("CESS") ? "Cess"
          : "Other";
        taxMap[l.tax_code] = {
          doctype: "Tax Line",
          account_head: tmpl.account || taxAccountHead.value,
          description: l.tax_code,
          rate: tmpl.rate,
          tax_type,
        };
      }
    }
    const taxes = Object.values(taxMap);
    const doc = {
      doctype: "Purchase Order", company,
      supplier: form.supplier, transaction_date: form.transaction_date, purchase_type: form.purchase_type || "Goods",
      expected_delivery_date: form.expected_delivery_date || null,
      billing_address: form.billing_address || "",
      delivery_address: form.delivery_address || "",
      billing_address_name: form.billing_address_name || "",
      delivery_address_name: form.delivery_address_name || "",
      set_warehouse: form.set_warehouse || "",
      status: newStatus || "Draft",
      docstatus: newStatus === "Draft" ? 0 : 1,
      terms: form.terms || "",
      items: lines.value.filter(l => l.item_code).map(l => ({
        doctype: "Purchase Order Item", item_code: l.item_code,
        description: l.description || l.item_code,
        qty: flt(l.qty) || 1, rate: flt(l.rate), amount: flt(l.amount),
        tax_code: l.tax_code || "",
      })),
      taxes,
    };
    if (editingName.value) doc.name = editingName.value;
    const saved = await apiSave(doc);
    const msg = newStatus === "Draft" ? "saved as Draft" : "confirmed";
    toast.success(`Purchase Order ${saved?.name || ""} ${msg}`);
    drawerOpen.value = false;
    await load();
  } catch (e) { toast.error(e.message || "Failed to save PO"); }
  finally { drawerSaving.value = false; }
}

// ── Actions ───────────────────────────────────────────────────────────────
async function emailPO(o) {
  await openEmail({
    doctype: "Purchase Order", name: o.name, docLabel: `Purchase Order ${o.name}`,
    getDefaultsEndpoint: "zoho_books_clone.api.docs.get_purchase_order_email_defaults",
    sendEndpoint: "zoho_books_clone.api.docs.send_purchase_order_email",
    paramKey: "purchase_order",
    printConfig: { title: "PURCHASE ORDER", partyLabel: "Vendor", partyField: "supplier_name" },
  });
}

function openBillModal(o) {
  apiGET("zoho_books_clone.api.docs.get_purchase_order_fulfillment", { purchase_order: o.name })
    .then(async r => {
      const ful = r?.lines || [];
      const lines = ful.filter(l => l.remaining_to_bill > 0)
                  .map(l => ({ ...l, toBill: Math.min(l.remaining_to_bill, Math.max(0, l.received_qty - l.billed_qty)) || l.remaining_to_bill,
                               has_batch_no: 0, batch_no: "", batchOptions: [] }));
      // Resolve has_batch_no per item so the Batch No field shows up for
      // batch-tracked items when converting a PO to a Bill (the Bill's
      // update_stock=1 is what actually creates the incoming Stock Entry).
      const codes = [...new Set(lines.map(l => l.item_code).filter(Boolean))];
      if (codes.length) {
        try {
          const itemRows = await apiList("Item", { fields: ["name", "has_batch_no"], filters: [["name", "in", codes]], limit: codes.length });
          const flagMap = Object.fromEntries(itemRows.map(r => [r.name, r.has_batch_no ? 1 : 0]));
          lines.forEach(l => { l.has_batch_no = flagMap[l.item_code] || 0; if (l.has_batch_no) fetchBillBatches(l, ""); });
        } catch {}
      }
      Object.assign(billModal, {
        open: true, saving: false, poName: o.name,
        lines,
        billNo: "", billDate: todayStr(), dueDate: o.expected_delivery_date || todayStr(),
      });
      if (!billModal.lines.length) { billModal.open = false; toast.info("Nothing left to bill"); }
    })
    .catch(e => toast.error(e.message || "Failed to load fulfillment"));
}

// ── Batch helpers for Convert-to-Bill modal (mirrors PurchaseReceipts.vue) ──
async function fetchBillBatches(line, q = "") {
  if (!line.item_code) { line.batchOptions = []; return; }
  const itemCode = line.item_code;
  try {
    let rows = await apiGET("zoho_books_clone.api.inventory.get_batches_for_item", { item_code: itemCode, search: q || "" }) || [];
    if (!rows.length && !q) {
      // Fallback: the batch may be linked to a different Item record that
      // shares this item's display name (e.g. after a rename, or a
      // duplicate Item was created). Look up by item_name instead of code.
      try {
        const itemRows = await apiList("Item", { fields: ["name", "item_name"], filters: [["name", "=", itemCode]], limit: 1 });
        const itemName = itemRows[0]?.item_name;
        if (itemName) {
          const altItems = await apiList("Item", { fields: ["name"], filters: [["item_name", "=", itemName], ["name", "!=", itemCode]], limit: 5 });
          for (const alt of altItems) {
            const altRows = await apiGET("zoho_books_clone.api.inventory.get_batches_for_item", { item_code: alt.name, search: "" }) || [];
            if (altRows.length) { rows = altRows; break; }
          }
        }
      } catch {}
    }
    if (line.item_code !== itemCode) return; // item changed while awaiting
    line.batchOptions = rows.map(b => ({
      value: b.batch_no,
      label: (b.qty !== undefined && b.qty !== null) ? `${b.batch_no} (Qty: ${b.qty})` : b.batch_no,
    }));
  } catch { if (line.item_code === itemCode) line.batchOptions = []; }
}
function onBillBatchSelect(line, opt) {
  line.batch_no = opt?.value ?? opt;
}
function onBillBatchCreate(line, val) { line.batch_no = val; }
async function submitBill() {
  const lineMap = {};
  for (const l of billModal.lines) {
    if (flt(l.toBill) > 0) lineMap[l.name] = flt(l.toBill);
  }
  if (!Object.keys(lineMap).length) { toast.error("Enter at least one qty to bill"); return; }

  // Batch-tracked items must carry a Batch No before we let this go to the
  // backend — the Bill's update_stock=1 creates the incoming Stock Entry,
  // which fails its own "Batch No is required" check on submit otherwise.
  const batchNos = {};
  for (const l of billModal.lines) {
    if (!(flt(l.toBill) > 0)) continue;
    if (l.has_batch_no) {
      if (!l.batch_no) { toast.error(`${l.item_name || l.item_code} is batch-tracked — Batch No is required`); return; }
      const existing = await apiList("Batch", { fields: ["name", "disabled", "item"], filters: [["name", "=", l.batch_no]], limit: 1 }).catch(() => []);
      if (existing.length && existing[0].disabled) { toast.error(`Batch "${l.batch_no}" is disabled and can't be used.`); return; }
      if (existing.length && existing[0].item && existing[0].item !== l.item_code) {
        toast.error(`Batch "${l.batch_no}" already exists for item "${existing[0].item}", not "${l.item_code}".`); return;
      }
      batchNos[l.name] = l.batch_no;
    }
  }

  billModal.saving = true;
  try {
    const r = await apiPOST("zoho_books_clone.api.docs.convert_purchase_order_to_bill", {
      purchase_order: billModal.poName,
      line_qtys: JSON.stringify(lineMap),
      bill_no: billModal.billNo || "",
      bill_date: billModal.billDate || "",
      due_date: billModal.dueDate || "",
      batch_nos: JSON.stringify(batchNos),
    });
    toast.success(`Bill created: ${r?.bill}`);
    if (r?.three_way_warnings?.length) {
      toast.warn?.("3-way match: " + r.three_way_warnings.join("; ")) || toast.info("3-way mismatch — check fulfillment");
    }
    billModal.open = false;
    await load();
    if (viewDoc.value?.name === billModal.poName) await openView(viewDoc.value);
  } catch (e) { toast.error(e.message || "Convert failed"); }
  billModal.saving = false;
}

async function markAllReceived() {
  actionRunning.value = true;
  try {
    const r = await apiPOST("zoho_books_clone.api.docs.mark_po_received", { purchase_order: viewDoc.value.name });
    toast.success(`Marked ${r?.lines_updated || 0} line(s) received`);
    await load();
    if (viewDoc.value) await openView(viewDoc.value);
  } catch (e) { toast.error(e.message || "Mark received failed"); }
  actionRunning.value = false;
}

async function submitPO(o) {
  const label = (o?.purchase_type === "Services") ? "Confirm Order" : "Issue PO";
  if (!await confirm({ title: label, body: `Submit ${o.name}? This will confirm the order and it can no longer be edited.`, okLabel: label })) return;
  try {
    const submitted = await apiPOST("zoho_books_clone.api.docs.submit_purchase_order", { purchase_order: o.name });
    toast.success(`Purchase Order ${o.name} confirmed`);
    await load();
    await openView({ name: o.name });
  } catch (e) { toast.error(e.message || "Submit failed"); }
}
async function cancelPO(o) {
  if (!await confirm({ title: "Cancel Purchase Order", body: `Cancel ${o.name}? Linked bills must be cancelled separately.`, okLabel: "Cancel PO" })) return;
  try {
    await apiPOST("zoho_books_clone.api.docs.cancel_purchase_order_safe", { purchase_order: o.name });
    toast.success("Purchase Order cancelled");
    await load(); if (viewDoc.value?.name === o.name) await openView(o);
  } catch (e) { toast.error(e.message || "Cancel failed"); }
}
async function deletePO(o) {
  if (!await confirm({ title: "Delete Purchase Order", body: `Permanently delete ${o.name}?`, okLabel: "Delete" })) return;
  try {
    await apiDelete("Purchase Order", o.name);
    toast.success("Purchase Order deleted");
    viewOpen.value = false; await load();
  } catch (e) { toast.error(e.message || "Delete failed"); }
}

// ── Bulk actions ──────────────────────────────────────────────────────────
async function bulkDelete() {
  const drafts = sorted.value.filter(o => selected.value.has(o.name) && (!o.status || o.status === "Draft"));
  if (!drafts.length) { toast.info("Select drafts to delete"); return; }
  if (!await confirm({ title: "Delete Drafts", body: `Delete ${drafts.length} draft PO(s)?`, okLabel: "Delete" })) return;
  for (const o of drafts) { try { await apiDelete("Purchase Order", o.name); } catch {} }
  selected.value = new Set();
  toast.success(`Deleted ${drafts.length}`);
  await load();
}
async function bulkEmail() {
  const subs = sorted.value.filter(o => selected.value.has(o.name));
  if (!subs.length) { toast.info("No POs selected"); return; }
  let sent = 0;
  for (const o of subs) {
    const ok = await openEmail({
      doctype: "Purchase Order", name: o.name, docLabel: `Purchase Order ${o.name}`,
      getDefaultsEndpoint: "zoho_books_clone.api.docs.get_purchase_order_email_defaults",
      sendEndpoint: "zoho_books_clone.api.docs.send_purchase_order_email",
      paramKey: "purchase_order",
      printConfig: { title: "PURCHASE ORDER", partyLabel: "Vendor", partyField: "supplier_name" },
    });
    if (ok) sent++;
  }
  if (sent) toast.success(`Emailed ${sent} PO(s)`);
}

function exportCSV() {
  const rows = selected.value.size
    ? sorted.value.filter(p => selected.value.has(p.name))
    : sorted.value;
  if (!rows.length) return;
  const head = ["PO #","Vendor","Date","Expected","Status","Amount"];
  const esc = v => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const out = [head.map(esc).join(",")];
  for (const o of rows) {
    out.push([o.name, o.supplier_name || o.supplier, o.transaction_date, o.expected_delivery_date || "",
      o.status || "Draft", Number(o.grand_total || 0).toFixed(2)].map(esc).join(","));
  }
  const blob = new Blob(["﻿" + out.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `purchase_orders_${todayStr()}.csv`;
  a.click(); URL.revokeObjectURL(url);
  toast.success(`CSV exported — ${rows.length} PO(s)`);
}

const route = useRoute();
onMounted(async () => {
  setCompany(window.__booksCompany || "");
  document.addEventListener('click', onDocClickForDownloadMenu);
  await load();
  loadTaxAccount();
  useOpenFromQuery({ route, openByName: (n) => openView(list.value.find(o => o.name === n) || { name: n }) });
});
onUnmounted(() => document.removeEventListener('click', onDocClickForDownloadMenu));

watch(() => form.supplier, (val) => {
  vendorAddresses.value = [];
  form.billing_address_name = ""; form.billing_address = "";
  form.delivery_address_name = ""; form.delivery_address = "";
  if (val) fetchVendorAddresses(val);
});
</script>

<style>
/* ── Download dropdown menu ── */
.inv-dl-menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  z-index: 999;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0,0,0,.13), 0 2px 6px rgba(0,0,0,.06);
  min-width: 210px;
  padding: 6px;
  animation: dl-menu-in .12s ease;
}
@keyframes dl-menu-in {
  from { opacity: 0; transform: translateY(-4px); }
  to   { opacity: 1; transform: translateY(0); }
}
.inv-dl-menu-header {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .8px;
  text-transform: uppercase;
  color: #9ca3af;
  padding: 4px 10px 6px;
}
.inv-dl-menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 10px;
  border-radius: 7px;
  font-family: inherit;
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
  transition: background .12s;
}
.inv-dl-menu-item:hover { background: #f1f5f9; }
.inv-dl-menu-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  background: #eef3fd;
  border-radius: 7px;
  color: #1a6ef7;
  flex-shrink: 0;
}
.inv-dl-menu-item:hover .inv-dl-menu-icon { background: #dce8fd; }
.inv-dl-menu-text { display: flex; flex-direction: column; gap: 1px; }
.inv-dl-menu-label { font-size: 13px; font-weight: 600; color: #111827; white-space: nowrap; }
.inv-dl-menu-sub { font-size: 11px; color: #9ca3af; white-space: nowrap; }
.inv-ab-caret { font-size: 10px; opacity: .6; margin-left: 1px; }
</style>

<style scoped>
/* ── Edit/Create drawer slide animation ── */
.inv-drawer-panel {
  position: fixed;
  top: 0;
  right: -600px;
  bottom: 0;
  width: 600px;
  max-width: 96vw;
  z-index: 8100;
  transition: right .22s ease;
}
.inv-drawer-panel.open { right: 0; }
.po-edit-drawer { width: 720px; right: -720px; transition: right .22s ease; position: fixed; top: 0; bottom: 0; max-width: 96vw; z-index: 8100; background: #fff; display: flex; flex-direction: column; }

/* ── View drawer: Invoice-style full panel ── */
.inv-drawer-bg { position:fixed; inset:0; z-index:8000; background:rgba(15,23,42,.45); display:flex; justify-content:flex-end; backdrop-filter:blur(2px); }
.inv-drawer-wide { width:800px; max-width:96vw; }
.inv-view-page { display:flex; flex-direction:column; height:100%; background:#f5f6f8; overflow:hidden; }
.inv-view-header { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:20px 24px 12px; background:#f5f6f8; flex-wrap:nowrap; flex-shrink:0; }
.inv-view-header-left { display:flex; flex-direction:column; gap:4px; }
.inv-view-title-row { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.inv-view-number { font-size:20px; font-weight:800; color:#1a1a2e; letter-spacing:-.01em; }
.inv-view-subtitle { font-size:13px; color:#6b7280; margin-top:1px; }
.inv-hdr-badge { display:inline-flex; align-items:center; padding:3px 10px; border-radius:4px; font-size:11px; font-weight:700; letter-spacing:.04em; white-space:nowrap; }
.inv-view-cta { display:inline-flex; align-items:center; gap:7px; background:#1a6ef7; color:#fff; border:none; border-radius:7px; padding:9px 18px; font-size:13.5px; font-weight:700; cursor:pointer; white-space:nowrap; }
.inv-view-cta:hover { background:#155fd4; }
.inv-view-cta:disabled { opacity:.55; cursor:not-allowed; }
.inv-view-body { flex:1; display:flex; flex-direction:column; gap:0; margin:0 16px 16px; background:#fff; border:1px solid #e5e7eb; border-radius:10px; overflow-y:auto; }
.inv-tl-wrap { padding:20px 28px; border-bottom:1px solid #e5e7eb; background:#fff; }
.inv-action-bar { display:flex; align-items:center; gap:8px; padding:12px 20px; border-bottom:1px solid #e5e7eb; flex-wrap:wrap; background:#fff; }
.inv-ab-btn { display:inline-flex; align-items:center; gap:6px; border:1px solid #e2e8f0; background:#fff; color:#374151; border-radius:6px; padding:7px 14px; font-size:13px; font-weight:600; cursor:pointer; white-space:nowrap; }
.inv-ab-btn:hover { border-color:#94a3b8; background:#f8fafc; }
.inv-ab-btn:disabled { opacity:.5; cursor:not-allowed; }
.inv-ab-btn.inv-ab-danger { color:#dc2626; border-color:rgba(220,38,38,.25); }
.inv-ab-btn.inv-ab-danger:hover { background:#fef2f2; border-color:#dc2626; }
.inv-ab-spacer { flex:1; }
.inv-view-tabs { display:flex; gap:0; border-bottom:1.5px solid #e5e7eb; padding:0 20px; background:#fff; flex-shrink:0; }
.inv-vtab { background:none; border:none; border-bottom:2.5px solid transparent; padding:11px 18px; margin-bottom:-1.5px; font-size:13.5px; font-weight:600; color:#6b7280; cursor:pointer; display:inline-flex; align-items:center; gap:6px; white-space:nowrap; }
.inv-vtab.active { color:#1a6ef7; border-bottom-color:#1a6ef7; }
.inv-vtab-count { font-size:10.5px; font-weight:700; padding:1px 6px; border-radius:10px; background:#e5e7eb; color:#374151; }
.inv-tab-body { padding:20px; display:flex; flex-direction:column; gap:16px; }
.inv-details-meta { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; padding:16px;border-bottom:1px solid #e5e7eb; }
.inv-dmeta-icon-row { display:flex; align-items:center; gap:6px; margin-bottom:6px; }
.inv-dmeta-icon { width:22px; height:22px; border-radius:5px; background:#dbeafe; color:#2563eb; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.inv-dmeta-lbl { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:#9ca3af; }
.inv-dmeta-primary { font-size:14px; font-weight:700; color:#1a1a2e; }
.inv-dmeta-date-val { font-size:15px; font-weight:700; color:#1a1a2e; }
.inv-dmeta-date-val.is-overdue { color:#dc2626; }
.inv-sec-lbl { font-size:10.5px; font-weight:700; letter-spacing:.6px; text-transform:uppercase; color:#9ca3af; margin-bottom:8px; margin-top:4px; padding-top:16px; border-top:1px solid #f0f2f5; }
.inv-sec-lbl:first-child { border-top:none; padding-top:0; margin-top:0; }
.inv-items-wrap { border:1px solid #e5e7eb; border-radius:8px; overflow:hidden; }
.inv-items-table { width:100%; border-collapse:collapse; font-size:13px; }
.inv-items-table th { padding:9px 14px; background:#f8fafc; border-bottom:1px solid #e8ecf0; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:#9ca3af; text-align:left; }
.inv-items-table td { padding:10px 14px; border-bottom:1px solid #f0f2f5; color:#374151; vertical-align:top; word-break:break-word; overflow-wrap:anywhere; max-width:0; }
.inv-items-table tr:last-child td { border-bottom:none; }
.th-r { text-align:right; }
.td-r { text-align:right; }

/* ── Meta grid (view details tab) ── */
.po-meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.po-meta-lbl { font-size: 11px; color: #9ca3af; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 2px; }

/* ── View items column grid ── */
.po-view-items { display: flex; flex-direction: column; border: 1px solid #e5e7eb; border-radius: 6px; }
.po-view-items-head { display: grid; grid-template-columns: 2.5fr 70px 90px 100px; gap: 8px; background: #f9fafb; padding: 8px 12px; font-size: 11px; font-weight: 700; color: #6b7280; text-transform: uppercase; }
.po-view-items-row { display: grid; grid-template-columns: 2.5fr 70px 90px 100px; gap: 8px; padding: 8px 12px; border-top: 1px solid #f3f4f6; align-items: center; font-size: 12.5px; }

/* ── Totals block ── */
.po-totals { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.po-totals-right { display: flex; flex-direction: column; gap: 4px; min-width: 220px; }
.po-total-row { display: flex; justify-content: space-between; gap: 16px; font-size: 13px; color: #374151; padding: 3px 0; }
.po-total-row.grand { font-weight: 700; font-size: 14px; color: #111827; border-top: 1px solid #e5e7eb; padding-top: 6px; }

/* ── Edit drawer line items grid ── */
/* ---- Line Item Cards ---- */
.po-item-cards { display: flex; flex-direction: column; gap: 12px; }
.po-item-card { background: #fff; border: 1px solid #dde3f0; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(99,102,241,.07); }
.po-item-card-header { display: flex; align-items: center; gap: 10px; padding: 12px 16px; background: linear-gradient(135deg,#eef2ff 0%,#f5f7ff 100%); border-bottom: 1px solid #dde3f0; }
.po-item-card-num { font-size: 11px; font-weight: 800; color: #4f46e5; background: #e0e7ff; border-radius: 5px; padding: 3px 8px; letter-spacing:.02em; }
.po-item-card-title { font-size: 15px; font-weight: 700; color: #1e40af; }
.po-item-card-subtotal { display: flex; flex-direction: column; align-items: flex-end; margin-left: auto; }
.po-item-card-subtotal-label { font-size: 9.5px; font-weight: 700; color: #9ca3af; letter-spacing: .08em; }
.po-item-card-amount { font-size: 20px; font-weight: 800; color: #111827; font-variant-numeric: tabular-nums; line-height: 1.1; }
.po-item-card-chevron { display:flex; align-items:center; color:#9ca3af; transition:transform .2s; margin-left:4px; }
.po-item-card-chevron.collapsed { transform:rotate(-90deg); }
.po-item-card-rm { background: none; border: none; cursor: pointer; color: #9ca3af; padding: 6px; border-radius: 6px; display: flex; align-items: center; margin-left: 8px; }
.po-item-card-rm:hover { background: #fee2e2; color: #ef4444; }
.po-item-card-body { display: grid; grid-template-columns: 1fr 1fr; gap: 0; }
.po-item-col { padding: 16px; display: flex; flex-direction: column; }
.po-item-col--left { border-right: 1px solid #f0f2f8; }
.po-item-col--right { gap: 14px; }
.po-item-field { display: flex; flex-direction: column; gap: 5px; }
.po-item-field label { font-size: 10.5px; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: .06em; }
.po-item-field .inv-fi { font-size: 13.5px; }
.po-item-desc-ta { resize: vertical; min-height: 90px; font-size: 13px; line-height: 1.5; }
.po-item-num-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.po-item-hint { font-size: 12px; font-style: italic; color: #6b7280; background: #f0f4ff; border-radius: 8px; padding: 10px 12px; line-height: 1.5; margin-top: auto; }

/* ── Fulfillment table ── */
.po-fulfill-tbl { display: flex; flex-direction: column; border: 1px solid #e5e7eb; border-radius: 6px; overflow: hidden; }
.po-fulfill-head { display: grid; grid-template-columns: 2fr 80px 100px 90px 110px; gap: 8px; background: #f9fafb; padding: 8px 12px; font-size: 11px; font-weight: 700; color: #6b7280; text-transform: uppercase; }
.po-fulfill-row { display: grid; grid-template-columns: 2fr 80px 100px 90px 110px; gap: 8px; padding: 8px 12px; border-top: 1px solid #f3f4f6; align-items: center; font-size: 12.5px; }

/* ── Misc view helpers ── */
.po-terms { padding: 10px 12px; background: #f8fafc; border-radius: 6px; overflow: hidden; word-break: break-word; overflow-wrap: anywhere; }
.po-item-desc-clamp { font-size:11px; color:#9ca3af; margin-top:3px; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; word-break:break-word; overflow-wrap:anywhere; line-height:1.5; }
.po-link-row { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 8px; padding: 8px 12px; border: 1px solid #e5e7eb; border-radius: 6px; font-size: 12.5px; align-items: center; }
.po-act-cell { display: flex; gap: 4px; justify-content: flex-end; cursor: default !important; }
.po-act-conv { background: #eff6ff; border-color: #2563eb; color: #2563eb; }
.po-act-conv:hover { background: #dbeafe; }
.po-act-del:hover { background: #fee2e2; color: #dc2626; border-color: #fca5a5; }
.po-empty { text-align: center; color: #9ca3af; padding: 48px !important; cursor: default !important; }

/* ── Convert-to-Bill modal ── */
.po-apply-dialog { position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 560px; max-width: 96vw; background: #fff; border-radius: 12px; box-shadow: 0 12px 40px rgba(0,0,0,.2); z-index: 8100; display: flex; flex-direction: column; overflow: hidden; }
.po-inv-tbl { display: flex; flex-direction: column; border: 1px solid #e5e7eb; border-radius: 6px; overflow: hidden; }
.po-inv-head { display: grid; grid-template-columns: 2fr 80px 90px 110px; gap: 8px; background: #f9fafb; padding: 8px 12px; font-size: 11px; font-weight: 700; color: #6b7280; text-transform: uppercase; }
.po-inv-row { display: grid; grid-template-columns: 2fr 80px 90px 110px; gap: 8px; padding: 8px 12px; border-top: 1px solid #f3f4f6; align-items: center; font-size: 12.5px; }
.po-inv-row.warn { background: #fef3c7; }
.po-warn { background: #fef3c7; border: 1px solid #fcd34d; border-radius: 6px; padding: 10px 12px; font-size: 12.5px; color: #92400e; }

/* ── Drawer add/edit cards (matches Invoice) ── */
.add-card { border: 1px solid #e8ecf0; border-radius: 10px; overflow: hidden; background: #fff; margin-bottom: 12px; }
.add-card-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; cursor: pointer; user-select: none; background: #f8fafc; }
.add-card-header:hover { background: #f1f4f8; }
.add-card-title { display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 700; color: #1a1a2e; }
.add-card-title-icon { width: 28px; height: 28px; border-radius: 7px; background: #dbeafe; color: #2563eb; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.add-card-chevron { color: #9ca3af; transition: transform .2s; display: flex; }
.add-card-chevron.collapsed { transform: rotate(-90deg); }
.add-card-body { padding: 16px; border-top: 1px solid #e8ecf0; }
.add-card-body.collapsed { display: none; }
.add-details-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }

/* ── Item count badge in card title ── */
.po-item-count { font-size: 11px; font-weight: 600; background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; border-radius: 12px; padding: 1px 8px; margin-left: 4px; }

/* ── Draft badge in drawer header ── */
.po-draft-badge { display: inline-flex; align-items: center; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; background: rgba(255,255,255,.15); color: rgba(255,255,255,.85); border: 1px solid rgba(255,255,255,.25); }

/* ── Footer action buttons (matches Invoice add-btn-*) ── */
.add-footer-status { font-size: 12px; color: #9ca3af; }
.add-footer-actions { display: flex; align-items: center; gap: 8px; }
.add-btn-cancel { background: none; border: 1px solid #e8ecf0; border-radius: 7px; padding: 7px 16px; font-size: 13px; font-weight: 600; color: #6b7280; cursor: pointer; }
.add-btn-cancel:hover { border-color: #374151; color: #374151; }

.add-btn-draft:disabled { opacity: .5; cursor: not-allowed; }
.add-btn-primary { display: inline-flex; align-items: center; gap: 6px; background: #1a6ef7; color: #fff; border: none; border-radius: 7px; padding: 7px 18px; font-size: 13px; font-weight: 600; cursor: pointer; }
.add-btn-primary:hover { background: #155fd4; }
.add-btn-primary:disabled { opacity: .5; cursor: not-allowed; }

/* -- Purchase Type Toggle ----------------------------------------- */
.po-type-toggle { display: flex; align-items: center; gap: 12px; padding: 10px 0 14px; border-bottom: 1px solid #f0f2f5; margin-bottom: 14px; }
.po-type-lbl { font-size: 12px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: .04em; white-space: nowrap; }
.po-type-btns { display: flex; gap: 0; border: 1.5px solid #e2e8f0; border-radius: 8px; overflow: hidden; background: #f8fafc; }
.po-type-btn { display: inline-flex; align-items: center; gap: 6px; padding: 6px 16px; font-size: 12.5px; font-weight: 600; color: #6b7280; background: transparent; border: none; cursor: pointer; transition: all .15s; }
.po-type-btn + .po-type-btn { border-left: 1.5px solid #e2e8f0; }
.po-type-btn:hover { background: #f1f5f9; color: #374151; }
.po-type-btn.active { background: #1a6ef7; color: #fff; }
.po-type-btn.active svg { stroke: #fff; }

/* -- Purchase Type Badge (view header) ----------------------------- */
.po-type-badge { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 20px; font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; }
.po-type-goods { background: #dbeafe; color: #1d4ed8; }

/* ── Address dropdown + card ── */
.po-addr-select { appearance: none; padding-right: 28px; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%239ca3af' stroke-width='2.5'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E"); background-repeat: no-repeat; background-position: right 10px center; }
.po-addr-card { margin-top: 8px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; display: flex; flex-direction: column; gap: 5px; }
.po-addr-card-type { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: #2563eb; background: #dbeafe; display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 10px; align-self: flex-start; }
.po-addr-card-text { font-size: 12.5px; color: #374151; line-height: 1.65; }
.po-type-services { background: #f0fdf4; color: #15803d; }

/* ── Inline field hints / validation ── */
.exp-field-hint { font-size:11.5px; color:#9ca3af; margin-top:4px; text-align:right; }
.exp-field-hint-err { color:#dc2626; font-weight:600; }
.po-view-drawer { width: 900px; right: -900px; transition: right .22s ease; position: fixed; top: 0; bottom: 0; background: #f5f6f8; display: flex; flex-direction: column; overflow-y: auto; }
/* ── View drawer tax / totals summary ── */
.po-view-totals { display: flex; justify-content: flex-end; padding: 4px 0 8px; }
.po-view-totals-inner { display: flex; flex-direction: column; gap: 5px; min-width: 260px; background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 9px; padding: 14px 18px; }
.po-view-total-row { display: flex; justify-content: space-between; align-items: center; gap: 24px; font-size: 13px; color: #374151; padding: 2px 0; }
.po-view-tax-row { color: #6b7280; font-size: 12.5px; }
.po-view-tax-label { display: flex; align-items: center; gap: 7px; }
.po-view-tax-badge { font-size: 9px; font-weight: 800; letter-spacing: .06em; padding: 2px 6px; border-radius: 4px; background: #dbeafe; color: #1d4ed8; flex-shrink: 0; }
.po-view-tax-badge--none { background: #f3f4f6; color: #9ca3af; }
.po-view-tax-rate { font-size: 11px; font-weight: 700; color: #1d4ed8; background: #eff6ff; border-radius: 4px; padding: 1px 5px; }
.po-view-grand { font-weight: 800; font-size: 15px; color: #111827; border-top: 1.5px solid #e5e7eb; margin-top: 4px; padding-top: 8px; }

/* ── View drawer line item cards ── */
.vi-line-cards { display:flex; flex-direction:column; gap:10px; }
.vi-line-card { background:#fff; border:1px solid #e2e8f0; border-radius:10px; overflow:hidden; }
.vi-line-card-header { display:flex; align-items:center; gap:10px; padding:11px 16px; background:linear-gradient(135deg,#f0f4ff 0%,#f8fafc 100%); border-bottom:1px solid #e8edf5; }
.vi-line-num { font-size:10.5px; font-weight:800; color:#4f46e5; background:#e0e7ff; border-radius:5px; padding:2px 7px; letter-spacing:.02em; flex-shrink:0; }
.vi-line-name { font-size:14px; font-weight:700; color:#1e293b; flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.vi-line-amount { font-size:16px; font-weight:800; color:#111827; font-variant-numeric:tabular-nums; flex-shrink:0; }
.vi-line-desc { padding:8px 16px; font-size:12px; color:#6b7280; line-height:1.55; border-bottom:1px solid #f0f2f5; background:#fafbfc; word-break:break-word; overflow-wrap:anywhere; }
.vi-line-meta { display:flex; align-items:center; gap:12px; padding:10px 16px; flex-wrap:wrap; }
.vi-line-meta-item { display:flex; flex-direction:column; gap:2px; }
.vi-meta-lbl { font-size:9.5px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; color:#9ca3af; }
.vi-meta-val { font-size:13px; font-weight:600; color:#374151; font-variant-numeric:tabular-nums; }
.vi-line-meta-sep { font-size:16px; color:#d1d5db; font-weight:300; margin-top:10px; }
.vi-line-tax { margin-left:auto; flex-direction:row; align-items:center; gap:6px; }
.vi-tax-badge { font-size:9px; font-weight:800; letter-spacing:.06em; padding:2px 6px; border-radius:4px; background:#e0e7ff; color:#4f46e5; flex-shrink:0; }
.vi-notax-badge { font-size:9px; font-weight:800; letter-spacing:.06em; padding:2px 6px; border-radius:4px; background:#f3f4f6; color:#9ca3af; }

/* ══════════════════════════════════════════════════
   RESPONSIVE MEDIA QUERIES
   ══════════════════════════════════════════════════ */

/* ── Small desktop (≤ 1024px) ── */
@media (max-width: 1024px) {
  .po-edit-drawer  { width: 660px; right: -660px; }
  .po-view-drawer  { width: 800px; right: -800px; }
  .inv-drawer-wide { width: 740px; }

  .bk-kpi-grid  { grid-template-columns: repeat(3, 1fr); }
  .bk-stat-grid { grid-template-columns: repeat(2, 1fr); }

  .po-view-items-head,
  .po-view-items-row { grid-template-columns: 2fr 70px 80px 90px; }

  .po-fulfill-head,
  .po-fulfill-row { grid-template-columns: 2fr 70px 90px 80px 90px; }
}

/* ── Tablet (≤ 768px) ── */
@media (max-width: 768px) {
  /* Table: allow horizontal scroll so columns don't compress into blur */
  .inv-table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
  .inv-table { min-width: 560px; }

  /* Drawers go full-screen */
  .po-edit-drawer   { width: 100% !important; right: -100% !important; max-width: 100%; }
  .po-view-drawer   { width: 100% !important; right: -100% !important; max-width: 100%; }
  .inv-drawer-panel { width: 100% !important; right: -100% !important; max-width: 100%; }
  .inv-drawer-wide  { width: 100%; max-width: 100%; }
  /* .open must override the right: -100% !important above */
  .po-edit-drawer.open,
  .po-view-drawer.open,
  .inv-drawer-panel.open { right: 0 !important; }

  /* KPI / stat grids */
  .bk-kpi-grid  { grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .bk-stat-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }

  /* Toolbar: let pills + buttons wrap */
  .sales-toolbar { flex-wrap: wrap; gap: 8px; }

  /* View header: tighter padding, keep single row (no wrap) */
  .inv-view-header { padding: 12px 14px 10px; gap: 8px; }
  .inv-view-header-left { flex: 1 1 auto; min-width: 0; }
  .inv-view-cta { flex-shrink: 0; }

  /* Details meta */
  .inv-details-meta { grid-template-columns: repeat(2, 1fr); }
  .po-meta-grid     { grid-template-columns: repeat(2, 1fr); }

  /* Address grid */
  .inv-bottom-grid { grid-template-columns: 1fr; gap: 12px; }

  /* View items table: keep item name + amount only */
  .po-view-items-head { grid-template-columns: 1fr 90px; }
  .po-view-items-row  { grid-template-columns: 1fr 90px; }
  .po-view-items-head > *:nth-child(2),
  .po-view-items-head > *:nth-child(3),
  .po-view-items-row  > *:nth-child(2),
  .po-view-items-row  > *:nth-child(3) { display: none; }

  /* Fulfillment table: replaced by cards at ≤768px (see bottom of styles) */

  /* Totals block */
  .po-totals { flex-direction: column; gap: 12px; }
  .po-totals-right { min-width: unset; width: 100%; }

  /* Modals */
  .po-apply-dialog { width: 96vw; }

  /* Action bar */
  .inv-action-bar { padding: 10px 14px; gap: 6px; }
  .inv-ab-btn     { padding: 6px 10px; font-size: 12px; }

  /* Convert-to-bill table: 3 cols */
  .po-inv-head { grid-template-columns: 2fr 80px 100px; }
  .po-inv-row  { grid-template-columns: 2fr 80px 100px; }
  .po-inv-head > *:nth-child(4),
  .po-inv-row  > *:nth-child(4) { display: none; }

  /* Linked doc rows */
  .po-link-row { grid-template-columns: 1fr 1fr; gap: 6px; font-size: 12px; }
}

/* ── Mobile (≤ 480px) ── */
@media (max-width: 480px) {
  /* KPI + stat grids: single column */
  .bk-kpi-grid  { grid-template-columns: 1fr; }
  .bk-stat-grid { grid-template-columns: 1fr; }

  /* View header */
  .inv-view-number { font-size: 17px; }
  .inv-view-cta    { padding: 9px 14px; font-size: 13px; }

  /* Details meta: single column */
  .inv-details-meta { grid-template-columns: 1fr; }
  .po-meta-grid     { grid-template-columns: 1fr; }

  /* Item card body stacks */
  .po-item-card-body { grid-template-columns: 1fr; }
  .po-item-col--left { border-right: none; border-bottom: 1px solid #f0f2f8; }

  /* Numeric row in item card */
  .po-item-num-row { grid-template-columns: 1fr; }

  /* Additional details grid */
  .add-details-grid { grid-template-columns: 1fr; }

  /* Edit drawer footer buttons */
  .add-footer-actions { flex-wrap: wrap; width: 100%; }
  .add-btn-cancel,
  .add-btn-primary { flex: 1 1 auto; justify-content: center; text-align: center; }

  /* Purchase type toggle */
  .po-type-toggle { flex-wrap: wrap; }
  .po-type-btns   { width: 100%; }
  .po-type-btn    { flex: 1; justify-content: center; }

  /* View item card meta */
  .vi-line-meta { gap: 8px; }
  .vi-meta-val  { font-size: 12px; }

  /* Totals panel */
  .po-view-totals-inner { min-width: unset; width: 100%; }

  /* Modal: near full width */
  .po-apply-dialog { width: 98vw; height: 450px; border-radius: 8px; }

  /* Tabs */
  .inv-vtab { padding: 9px 12px; font-size: 12.5px; }

  /* Timeline */
  .inv-tl-wrap { padding: 14px 16px; }

  /* Action bar */
  .inv-action-bar { gap: 4px; padding: 8px 12px; }
  .inv-ab-btn     { padding: 5px 8px; font-size: 11.5px; }

  /* Linked doc rows */
  .po-link-row { grid-template-columns: 1fr; }

  /* Timeline wrapper: no extra padding on mobile, component handles its own */
  .inv-tl-wrap { padding: 0; }

  /* Fulfillment + linked bills: replaced by mobile cards at ≤768px */
}

/* ── Mobile card layout override (≤ 425px) ── */
/* ── Mobile card view (Option A) ── */
.po-mobile-cards { display: none; }
.po-desktop-table { display: table; }

@media (max-width: 768px) {
  .po-desktop-table { display: none !important; }
  .po-mobile-cards { display: flex; flex-direction: column; gap: 0; background: #f8fafc; }
  .po-mobile-card { background: #fff; border-bottom: 1px solid #e5e7eb; padding: 12px 14px; cursor: pointer; transition: background .12s; }
  .po-mobile-card:active { background: #f8f9fc; }
  .po-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .po-mc-docno { font-size: 12px; font-weight: 700; color: #2563eb; }
  .po-mc-mid { font-size: 13.5px; font-weight: 600; color: #1a1d23; margin-bottom: 4px; }
  .po-mc-meta { display: flex; justify-content: space-between; font-size: 12px; color: #868e96; margin-bottom: 4px; }
  .po-mc-amount { font-weight: 700; color: #1a1d23; }
  .po-mc-sub { font-size: 11.5px; color: #868e96; margin-bottom: 8px; }
  .po-mc-footer { display: flex; gap: 6px; margin-top: 8px; }
  .po-mc-btn { flex: 1; padding: 6px 10px; border-radius: 7px; font-size: 12px; font-weight: 600; cursor: pointer; background: #f1f5f9; border: 1px solid #e2e8f0; color: #374151; }
  .po-mc-danger { background: #fff1f2; border-color: #fecaca; color: #dc2626; }
  .po-mc--skeleton { pointer-events: none; }
  .po-mc-shimmer { border-radius: 6px; background: linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size: 200% 100%; animation: po-shimmer 1.4s infinite; }
  @keyframes po-shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
  .po-mc-empty { text-align: center; padding: 32px 16px; color: #868e96; font-size: 13px; }
}

@media (max-width: 425px) {
  /*
   * Use explicit grid-row / grid-column instead of named areas.
   * list.css assigns grid-area names; overriding with row/column numbers
   * has higher specificity (scoped attr selector) and bypasses named-area
   * inheritance so td-date::before cannot leak into the id row.
   */
  .inv-table tbody .inv-row .td-customer { grid-row: 1 !important; grid-column: 1 !important; }
  .inv-table tbody .inv-row .td-amount   { grid-row: 1 !important; grid-column: 2 !important; }
  .inv-table tbody .inv-row .td-date     { grid-row: 2 !important; grid-column: 1 !important; }
  .inv-table tbody .inv-row .td-status   { grid-row: 2 / 5 !important; grid-column: 2 !important; }
  .inv-table tbody .inv-row .td-id       { grid-row: 3 !important; grid-column: 1 !important; }
  .inv-table tbody .inv-row .td-actions  { grid-row: 4 !important; grid-column: 1 !important; }

  /* PO# cell: kill ANY ::before content, style as blue link.
   * Use high-specificity selector to beat Invoices.vue global rule
   * ".inv-table tbody td:nth-child(2)::before { content:'Date:' !important }" (0-2-2).
   * This selector compiles to 0-4-1 which wins. */
  .td-id { padding: 0 14px 4px !important; cursor: pointer !important; }
  .inv-table tbody .inv-row .td-id::before { content: none !important; display: none !important; font-size: 0 !important; }
  .td-id .inv-link {
    font-size: 12px !important;
    font-weight: 600 !important;
    color: #1a6ef7 !important;
    text-decoration: underline !important;
    text-underline-offset: 2px !important;
  }
  .td-id .inv-link:hover { color: #155fd4 !important; }

  /* Vendor row: prominent */
  .td-customer {
    font-size: 15px !important;
    font-weight: 700 !important;
    color: #1a1a2e !important;
  }

  /* Amount: smaller font so it doesn't truncate on narrow screens */
  .td-amount {
    font-size: 14px !important;
    letter-spacing: -0.02em !important;
  }
}


@media (max-width: 480px) {
  .view-toggle-btn { display: none !important; }
}

/* ── Fulfillment mobile/desktop visibility ── */
.po-fulfill-mobile { display: none; }
.po-fulfill-desktop { display: flex; }

/* ── Linked bills mobile/desktop visibility ── */
.po-bills-mobile  { display: none; }
.po-bills-desktop { display: block; }

/* ── Fulfillment mobile cards ── */
.po-fulfill-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 8px;
}
.po-fulfill-card-name {
  font-size: 13.5px;
  font-weight: 700;
  color: #1a1d23;
  margin-bottom: 10px;
}
.po-fulfill-card-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 12px;
}
.po-fulfill-card-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.po-fulfill-card-lbl {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .05em;
  color: #9ca3af;
}
.po-fulfill-card-val {
  font-size: 14px;
  font-weight: 700;
  color: #374151;
  font-variant-numeric: tabular-nums;
}

/* ── Linked bills mobile cards ── */
.po-bill-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 8px;
}
.po-bill-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.po-bill-card-name {
  font-size: 13px;
  font-weight: 700;
  color: #2563eb;
}
.po-bill-card-total {
  font-size: 15px;
  font-weight: 800;
  color: #111827;
  font-variant-numeric: tabular-nums;
}
.po-bill-card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: #6b7280;
  flex-wrap: wrap;
  gap: 4px;
}
.po-bill-card-lbl {
  font-size: 11px;
  color: #9ca3af;
}

@media (max-width: 768px) {
  .po-fulfill-desktop { display: none !important; }
  .po-fulfill-mobile  { display: block; }

  .po-bills-desktop { display: none !important; }
  .po-bills-mobile  { display: block; }
}
</style>