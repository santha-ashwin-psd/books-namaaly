<template>
  <div class="inv-page">

    <!-- ── Unified toolbar ── -->
    <div class="sales-toolbar">
      <div class="sales-search">
        <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
        <input v-model="search" placeholder="Search orders, customers…" class="sales-search-input"/>
      </div>
      <div class="sales-pills">
        <button v-for="t in tabs" :key="t.key" class="sales-pill" :class="{active:activeTab===t.key, ['pill-'+t.key]: t.key!=='all'}" @click="activeTab=t.key">
          {{ t.label }}<span v-if="t.key!=='all'" class="sales-pill-count">{{ counts[t.key] }}</span>
        </button>
      </div>
      <div class="sales-actions">
        <button class="sales-btn-ghost view-toggle-btn" @click="viewMode=viewMode==='table'?'grid':'table'" :title="viewMode==='table'?'Grid View':'List View'"><span v-html="icon(viewMode==='table'?'grid':'file',14)"></span></button>
        <button class="sales-btn-ghost" @click="exportCSV" title="Export CSV"><span v-html="icon('download',14)"></span> CSV</button>
        <button class="sales-btn-ghost" @click="load" title="Refresh" :disabled="loading"><span v-html="icon('refresh',14)"></span></button>
        <button class="sales-btn-primary" :disabled="!$canCreate('invoices')" :title="!$canCreate('invoices') ? 'Read-only access' : ''" @click="openNew">
          <span v-html="icon('plus',13)"></span> New Sales Order
        </button>
      </div>
    </div>

    <!-- ── KPI Cards ── -->
    <div class="bk-kpi-grid">
      <div class="bk-kpi-card bk-kpi-accent clickable" @click="activeTab='all'">
        <div class="bk-kpi-inner">
          <div class="bk-kpi-icon" style="background:#dbeafe">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.8"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>
          </div>
          <div class="bk-kpi-body">
            <div class="bk-kpi-label">Total Orders</div>
            <div class="bk-kpi-value">{{ list.length }}</div>
            <div class="bk-kpi-trend" :class="soTrends.total.up?'bk-trend-up':'bk-trend-down'">{{ soTrends.total.up?'↑':'↓' }} {{ soTrends.total.pct }}% vs last month</div>
          </div>
        </div>
      </div>
      <div class="bk-kpi-card clickable" @click="activeTab='draft'">
        <div class="bk-kpi-inner">
          <div class="bk-kpi-icon" style="background:#e2e8f0">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="1.8"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          </div>
          <div class="bk-kpi-body">
            <div class="bk-kpi-label">Draft</div>
            <div class="bk-kpi-value">{{ counts.draft }}</div>
            <div class="bk-kpi-trend" :class="soTrends.draft.up?'bk-trend-up':'bk-trend-down'">{{ soTrends.draft.up?'↑':'↓' }} {{ soTrends.draft.pct }}% vs last month</div>
          </div>
        </div>
      </div>
      <div class="bk-kpi-card bk-kpi-warn clickable" @click="activeTab='toDeliver'">
        <div class="bk-kpi-inner">
          <div class="bk-kpi-icon" style="background:#fef3c7">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="1.8"><rect x="1" y="3" width="15" height="13" rx="1"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>
          </div>
          <div class="bk-kpi-body">
            <div class="bk-kpi-label">To Deliver</div>
            <div class="bk-kpi-value bk-kpi-amber">{{ counts.toDeliver }}</div>
            <div class="bk-kpi-trend" :class="soTrends.deliver.up?'bk-trend-up':'bk-trend-down'">{{ soTrends.deliver.up?'↑':'↓' }} {{ soTrends.deliver.pct }}% vs last month</div>
          </div>
        </div>
      </div>
      <div class="bk-kpi-card bk-kpi-success clickable" @click="activeTab='closed'">
        <div class="bk-kpi-inner">
          <div class="bk-kpi-icon" style="background:#dcfce7">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="#16a34a" stroke-width="1.8"/><polyline points="7 12.5 10.5 16 17 9" stroke="#16a34a" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
          <div class="bk-kpi-body">
            <div class="bk-kpi-label">Closed</div>
            <div class="bk-kpi-value bk-kpi-green">{{ counts.closed }}</div>
            <div class="bk-kpi-trend" :class="soTrends.closed.up?'bk-trend-up':'bk-trend-down'">{{ soTrends.closed.up?'↑':'↓' }} {{ soTrends.closed.pct }}% vs last month</div>
          </div>
        </div>
      </div>
      <div class="bk-kpi-card bk-kpi-danger clickable" @click="activeTab='cancelled'">
        <div class="bk-kpi-inner">
          <div class="bk-kpi-icon" style="background:#fee2e2">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
          </div>
          <div class="bk-kpi-body">
            <div class="bk-kpi-label">Cancelled</div>
            <div class="bk-kpi-value bk-kpi-red">{{ counts.cancelled }}</div>
            <div class="bk-kpi-trend" :class="soTrends.cancelled.up?'bk-trend-down':'bk-trend-up'">{{ soTrends.cancelled.up?'↑':'↓' }} {{ soTrends.cancelled.pct }}% vs last month</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Secondary Stats ── -->
    <div class="bk-stat-grid">
      <div class="bk-stat-card">
        <div class="bk-stat-content">
          <div>
            <div class="bk-stat-label">This Month</div>
            <div class="bk-stat-value">{{ soThisMonth.count }}</div>
          </div>
          <div class="bk-stat-icon" style="background:#dbeafe;color:#2563eb">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
          </div>
        </div>
      </div>
      <div class="bk-stat-card">
        <div class="bk-stat-content">
          <div>
            <div class="bk-stat-label">This Month Value</div>
            <div class="bk-stat-value" style="color:#16a34a;font-size:16px">{{ fmtCur(soThisMonth.value) }}</div>
          </div>
          <div class="bk-stat-icon" style="background:#dcfce7;color:#16a34a">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/></svg>
          </div>
        </div>
      </div>
      <div class="bk-stat-card">
        <div class="bk-stat-content">
          <div>
            <div class="bk-stat-label">Pipeline Value</div>
            <div class="bk-stat-value" style="color:#16a34a;font-size:16px">{{ fmtCur(summary.totalValue) }}</div>
          </div>
          <div class="bk-stat-icon" style="background:#dcfce7;color:#16a34a">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12"/><path d="M6 8h12"/><path d="m6 13 8.5 8"/><path d="M6 13h3"/><path d="M9 13c6.667 0 6.667-10 0-10"/></svg>
          </div>
        </div>
      </div>
      <div class="bk-stat-card">
        <div class="bk-stat-content">
          <div>
            <div class="bk-stat-label">To Invoice</div>
            <div class="bk-stat-value" style="color:#0891b2">{{ counts.toInvoice }}</div>
          </div>
          <div class="bk-stat-icon" style="background:#cffafe;color:#0891b2">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Bulk actions bar ── -->
    <div v-if="selected.size>0" class="inv-bulk-bar">
      <span class="inv-bulk-count">{{ selected.size }} selected</span>
      <button class="inv-bulk-btn" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="bulkEmail"><span v-html="icon('mail',13)"></span> Send Email</button>
      <button class="inv-bulk-btn inv-bulk-danger" :disabled="!$canDelete('invoices')" :title="!$canDelete('invoices') ? 'Not permitted' : ''" @click="bulkDelete">Delete</button>
      <button class="inv-bulk-btn" @click="exportCSV"><span v-html="icon('download',13)"></span> Export CSV</button>
      <button class="inv-bulk-clear" @click="selected=new Set()">✕ Clear</button>
    </div>

    <!-- ── Table ── -->
    <div class="inv-table-wrap">
      <template v-if="viewMode==='table'">
      <table class="inv-table so-desktop-table">
        <thead><tr>
          <th class="th-check"><input type="checkbox" @change="toggleAll" :checked="allChecked"/></th>
          <th class="sortable" @click="sortBy('transaction_date')">DATE <span class="sort-arrow">{{ sortArrowTxt('transaction_date') }}</span></th>
          <th class="sortable" @click="sortBy('name')">ORDER # <span class="sort-arrow">{{ sortArrowTxt('name') }}</span></th>
          <th class="sortable" @click="sortBy('customer_name')">CUSTOMER <span class="sort-arrow">{{ sortArrowTxt('customer_name') }}</span></th>
          <th class="sortable" @click="sortBy('delivery_date')">DELIVERY <span class="sort-arrow">{{ sortArrowTxt('delivery_date') }}</span></th>
          <th class="sortable" @click="sortBy('status')">STATUS <span class="sort-arrow">{{ sortArrowTxt('status') }}</span></th>
          <th class="ta-r sortable" @click="sortBy('grand_total')">AMOUNT <span class="sort-arrow">{{ sortArrowTxt('grand_total') }}</span></th>
          <th style="width:120px;text-align:center">ACTIONS</th>
        </tr></thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 7" :key="n" class="shimmer-row">
              <td><div class="shimmer" style="width:14px;height:14px;border-radius:3px"></div></td>
              <td><div class="shimmer" style="width:80px"></div></td>
              <td><div class="shimmer" style="width:110px"></div></td>
              <td><div class="shimmer" style="width:130px"></div></td>
              <td><div class="shimmer" style="width:80px"></div></td>
              <td><div class="shimmer" style="width:90px"></div></td>
              <td><div class="shimmer" style="width:80px;margin-left:auto"></div></td>
              <td></td>
            </tr>
          </template>
          <template v-else>
            <tr v-for="o in paged" :key="o.name" class="inv-row" :class="{selected:selected.has(o.name)}">
              <td class="td-check" @click.stop>
                <input type="checkbox" :checked="selected.has(o.name)" @change="toggle(o.name)"/>
              </td>
              <td @click="openView(o)" class="text-muted mono-sm">{{ fmtDate(o.transaction_date) }}</td>
              <td @click="openView(o)"><DocLink doctype="Sales Order" :name="o.name" /></td>
              <td @click="openView(o)"><span class="inv-customer">{{ o.customer_name || o.customer || '—' }}</span></td>
              <td @click="openView(o)" :class="isPastDelivery(o)?'text-danger':'text-muted'" class="mono-sm">{{ fmtDate(o.delivery_date)||'—' }}</td>
              <td @click="openView(o)">
                <span class="inv-status-badge" :class="badgeClass(o)">{{ displayStatus(o) }}</span>
              </td>
              <td class="ta-r mono-sm" @click="openView(o)">{{ fmtCur(o.grand_total) }}</td>
              <td style="text-align:center" @click.stop>
                <div style="display:flex;gap:4px;justify-content:center">
                  <button class="inv-act-btn" @click="openView(o)" title="View"><span v-html="icon('eye',13)"></span></button>
                  <button v-if="isDraft(o)" class="inv-act-btn" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : 'Edit'" @click="openEdit(o)"><span v-html="icon('edit',13)"></span></button>
                  <button v-if="canDeliver(o)" class="inv-act-btn" style="color:#d97706" :disabled="!$canCreate('invoices')" :title="!$canCreate('invoices') ? 'Read-only access' : 'Create Delivery Note'" @click="openDeliverModal(o)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg></button>
                  <button v-if="canInvoice(o)" class="inv-act-btn inv-act-pay" :disabled="!$canCreate('invoices')" :title="!$canCreate('invoices') ? 'Read-only access' : 'Invoice'" @click="openInvoiceModal(o)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></button>
                  <button v-if="canDelete(o)" class="inv-act-btn" style="color:#dc2626" @click.stop="deleteSO(o)" title="Delete"><span v-html="icon('trash',13)"></span></button>
                </div>
              </td>
            </tr>
            <tr v-if="!sorted.length">
              <td colspan="8" class="bk-empty-state">
                <div class="bk-empty-inner">
                  <template v-if="search">
                    <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.3"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                    <p class="bk-empty-title">No sales orders match</p>
                  </template>
                  <template v-else>
                    <div class="bk-empty-illus">
                      <svg width="80" height="80" viewBox="0 0 80 80" fill="none"><rect x="8" y="18" width="64" height="48" rx="6" fill="#e2e8f0"/><rect x="12" y="22" width="56" height="40" rx="4" fill="#fff"/><rect x="20" y="32" width="40" height="3" rx="2" fill="#e2e8f0"/><rect x="20" y="40" width="30" height="3" rx="2" fill="#e2e8f0"/><rect x="20" y="48" width="35" height="3" rx="2" fill="#e2e8f0"/><rect x="56" y="56" width="14" height="14" rx="3" fill="#2563eb" opacity=".8"/><line x1="60" y1="63" x2="66" y2="63" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/><line x1="63" y1="60" x2="63" y2="66" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/></svg>
                    </div>
                    <p class="bk-empty-title">No sales orders yet</p>
                    <p class="bk-empty-sub">Create a sales order to track customer fulfilment.</p>
                    <button class="bk-empty-btn" :disabled="!$canCreate('invoices')" @click="openNew"><span v-html="icon('plus',13)"></span> New Sales Order</button>
                  </template>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>

      <!-- Mobile cards (shown at ≤768px) -->
      <div class="so-mobile-cards">
        <template v-if="loading">
          <div v-for="n in 5" :key="n" class="so-mobile-card so-mc--skeleton">
            <div class="so-mc-shimmer" style="height:13px;width:55%;margin-bottom:8px"></div>
            <div class="so-mc-shimmer" style="height:11px;width:40%;margin-bottom:6px"></div>
            <div class="so-mc-shimmer" style="height:11px;width:65%"></div>
          </div>
        </template>
        <div v-else-if="!sorted.length" class="so-mc-empty">
          <div style="font-size:32px;margin-bottom:8px">📦</div>
          <div>No sales orders found</div>
        </div>
        <template v-else>
          <div v-for="o in paged" :key="o.name" class="so-mobile-card" @click="openView(o)">
            <div class="so-mc-top">
              <span class="so-mc-docno">{{ o.name }}</span>
              <span class="inv-status-badge" :class="badgeClass(o)">{{ displayStatus(o) }}</span>
            </div>
            <div class="so-mc-mid">{{ o.customer_name || o.customer || '—' }}</div>
            <div class="so-mc-meta">
              <span>{{ fmtDate(o.transaction_date) }}</span>
              <span class="so-mc-amount">{{ fmtCur(o.grand_total) }}</span>
            </div>
            <div v-if="o.delivery_date" class="so-mc-sub" :class="isPastDelivery(o)?'text-danger':''">Delivery: {{ fmtDate(o.delivery_date) }}</div>
            <div class="so-mc-footer">
              <button class="so-mc-btn" @click.stop="openView(o)">View</button>
              <button v-if="isDraft(o)" class="so-mc-btn" @click.stop="openEdit(o)">Edit</button>
              <button v-if="canDelete(o)" class="so-mc-btn so-mc-danger" @click.stop="deleteSO(o)">Delete</button>
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
            <div style="font-size:32px;margin-bottom:8px">📦</div>
            <div>{{ search ? 'No orders match your filters' : 'No sales orders yet' }}</div>
            <button v-if="!search" class="nim-btn nim-btn-primary" :disabled="!$canCreate('invoices')" :title="!$canCreate('invoices') ? 'Read-only access' : ''" style="margin-top:14px" @click="openNew"><span v-html="icon('plus',13)"></span> New Sales Order</button>
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
              <div style="font-size:13.5px;font-weight:600;color:#1a1d23;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ o.customer_name || o.customer || '—' }}</div>
              <div style="display:flex;justify-content:space-between;font-size:12px;color:#6b7280">
                <span>{{ fmtDate(o.transaction_date) }}</span>
                <span style="font-weight:700;color:#1a1d23">{{ fmtCur(o.grand_total) }}</span>
              </div>
              <div v-if="o.delivery_date" style="font-size:11.5px;" :class="isPastDelivery(o)?'text-danger':'text-muted'">
                Delivery: {{ fmtDate(o.delivery_date) }}
              </div>
              <div style="display:flex;gap:6px;border-top:1px solid #f3f4f6;padding-top:10px">
                <button class="inv-act-btn" @click.stop="openView(o)" title="View"><span v-html="icon('eye',13)"></span></button>
                <button v-if="isDraft(o)" class="inv-act-btn" @click.stop="openEdit(o)" title="Edit"><span v-html="icon('edit',13)"></span></button>
                <button v-if="canDelete(o)" class="inv-act-btn" style="color:#dc2626" @click.stop="deleteSO(o)" title="Delete"><span v-html="icon('trash',13)"></span></button>
              </div>
            </div>
          </template>
        </div>
      </template>
    </div>
    <div v-if="!loading && sorted.length" style="padding:12px 0px 4px">
      <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="sorted.length" />
    </div>

    <!-- ══ Modals / Drawers ══ -->
    <Teleport to="body">

      <!-- ── Create / Edit Drawer ── -->
      <div v-if="drawerOpen" class="inv-drawer-bg" @click.self="!editingName ? null : drawerOpen=false">
        <div class="inv-drawer-panel" :class="{'is-add':!editingName}">

          <!-- Header -->
          <div class="inv-dh">
            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
              <div class="inv-dh-title">{{ editingName ? 'Edit Sales Order' : 'New Sales Order' }}</div>
              <span v-if="!editingName" class="add-status-badge">Draft</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px">
              <button class="inv-dclose" @click="drawerOpen=false"><span v-html="icon('x',16)"></span></button>
            </div>
          </div>

          <!-- Body -->
          <div class="inv-content-row">
          <div class="inv-dbody">

            <!-- Order Details Card -->
            <div class="add-card">
              <div class="add-card-header" @click="collapsed.details=!collapsed.details">
                <div class="add-card-title">
                  <span class="add-card-title-icon">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>
                  </span>
                  Order Details
                </div>
                <span class="add-card-chevron" :class="{collapsed:collapsed.details}">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
                </span>
              </div>
              <div class="add-card-body" :class="{collapsed:collapsed.details}">
                <div class="inv-fg" style="grid-template-columns:1fr 1fr 1fr">
                  <div style="grid-column:1/3">
                    <label class="inv-lbl">Customer <span class="inv-req">*</span></label>
                    <SearchableSelect v-model="form.customer" :options="customers" placeholder="Select customer…"
                      :createable="true" createDoctype="Customer"
                      @search="fetchCustomers" @update:modelValue="onCustomerChange" />
                  </div>
                  <div>
                    <label class="inv-lbl">Order Date <span class="inv-req">*</span></label>
                    <input v-model="form.transaction_date" type="date" class="inv-fi"/>
                  </div>
                  <div>
                    <label class="inv-lbl">Delivery Date</label>
                    <input v-model="form.delivery_date" type="date" class="inv-fi"/>
                  </div>
                  <div>
                    <label class="inv-lbl">Customer PO #</label>
                    <input v-model="form.po_number" type="text" class="inv-fi" placeholder="Customer's purchase order #"/>
                  </div>
                  <div style="grid-column:1/-1">
                    <div style="font-size:12px;font-weight:600;color:#374151;margin-bottom:8px">
                      Addresses <span v-if="addressLoading" style="color:#9ca3af;font-weight:400">(loading…)</span>
                    </div>
                    <div class="inv-fg inv-fg2">
                      <div>
                        <label class="inv-lbl">Billing Address</label>
                        <div class="po-addr-select-wrap">
                          <SearchableSelect
                            v-model="form.billing_address_name"
                            :options="customerAddresses"
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
                      <div>
                        <label class="inv-lbl">Shipping Address</label>
                        <div class="po-addr-select-wrap">
                          <SearchableSelect
                            v-model="form.shipping_address_name"
                            :options="customerAddresses"
                            valueKey="name" labelKey="label"
                            placeholder="— Select —"
                            :createable="true" :staticCreate="true"
                            createLabel="+ Add New Address"
                            @select="onShippingAddrSelect"
                            @create="openAddrModal('shipping')"
                          />
                        </div>
                        <div v-if="selectedShippingAddr" class="po-addr-card">
                          <div class="po-addr-card-type">{{ selectedShippingAddr.address_type || 'Shipping' }}</div>
                          <div class="po-addr-card-text">{{ formatAddress(selectedShippingAddr) }}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div style="grid-column:1/-1">
                    <label class="inv-lbl">Dispatch Warehouse <span class="inv-req">*</span></label>
                    <SearchableSelect v-model="form.set_warehouse" :options="warehouses" placeholder="Select warehouse stock will be dispatched from…"
                      :createable="true" :staticCreate="true" createLabel="+ Create Warehouse" createDoctype="Warehouse" @search="fetchWarehouses" @create="fetchWarehouses('')" />
                    <div v-if="form.set_warehouse" style="font-size:11px;color:#6b7280;margin-top:4px">Stock will be deducted from this warehouse when invoiced</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Line Items Card -->
            <div class="add-card">
              <div class="add-card-header" @click="collapsed.lines=!collapsed.lines">
                <div class="add-card-title">
                  <span class="add-card-title-icon">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
                  </span>
                  Line Items
                </div>
                <div style="display:flex;align-items:center;gap:8px" @click.stop>
                  <button class="add-lines-add-btn" @click="addLine">
                    <span v-html="icon('plus',13)"></span> Add Item
                  </button>
                  <span class="add-card-chevron" :class="{collapsed:collapsed.lines}" @click="collapsed.lines=!collapsed.lines">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
                  </span>
                </div>
              </div>
              <div class="add-card-body" :class="{collapsed:collapsed.lines}" style="padding:16px 16px 8px">
                <div class="po-item-cards">
                  <div v-for="(line, idx) in lines" :key="line.id" class="po-item-card">
                    <div class="po-item-card-header" @click="line.collapsed=!line.collapsed">
                      <span class="po-item-card-num">#{{ idx + 1 }}</span>
                      <span class="po-item-card-title">{{ line.item_code || 'Line Item' }}</span>
                      <div class="po-item-card-subtotal">
                        <span class="po-item-card-subtotal-label">SUBTOTAL</span>
                        <span class="po-item-card-amount">{{ fmtCur(lineAmount(line)) }}</span>
                      </div>
                      <span class="po-item-card-chevron" :class="{collapsed:line.collapsed}">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
                      </span>
                      <button @click.stop="removeLine(line.id)" class="po-item-card-rm"><span v-html="icon('x',16)"></span></button>
                    </div>
                    <div class="po-item-card-body" v-show="!line.collapsed">
                      <div class="po-item-col po-item-col--left">
                        <div class="po-item-field">
                          <label>Item Name <span class="inv-req">*</span></label>
                          <SearchableSelect v-model="line.item_code" :options="items"
                            placeholder="Search item…" :createable="true" createDoctype="Item"
                            @search="fetchItems" @select="v=>onItemSelect(line,v)"/>
                        </div>
                        <div class="po-item-field" style="margin-top:14px">
                          <label>Description</label>
                          <textarea v-model="line.description" class="inv-fi po-item-desc-ta" rows="4" maxlength="500" placeholder="Enter item description…"></textarea>
                          <div class="exp-field-hint" :class="{'exp-field-hint-err': (line.description||'').length >= 500}">{{ (line.description||'').length }}/500</div>
                        </div>
                      </div>
                      <div class="po-item-col po-item-col--right">
                        <div class="po-item-num-row">
                          <div class="po-item-field">
                            <label>UOM</label>
                            <select v-model="line.uom" class="inv-fi">
                              <option v-for="u in uomList" :key="u" :value="u">{{ u }}</option>
                            </select>
                          </div>
                          <div class="po-item-field">
                            <label>Available Stock</label>
                            <div class="so-stock-badge" :class="line.available_stock === null ? 'so-stock-na' : line.available_stock <= 0 ? 'so-stock-zero' : 'so-stock-ok'">
                              <span v-if="line.available_stock === null">—</span>
                              <span v-else>{{ line.available_stock }} {{ line.uom || 'Nos' }}</span>
                            </div>
                          </div>
                        </div>
                        <div class="po-item-num-row">
                          <div class="po-item-field">
                            <label>Qty</label>
                            <input v-model.number="line.qty" type="number" min="0" step="0.001" class="inv-fi" @input="calcLine(line)"/>
                          </div>
                          <div class="po-item-field">
                            <label>Rate ({{ currencySymbol }})</label>
                            <input v-model.number="line.rate" type="number" min="0" step="0.01" class="inv-fi" @input="calcLine(line)"/>
                          </div>
                        </div>
                        <div class="po-item-num-row">
                          <div class="po-item-field">
                            <label>Discount %</label>
                            <input v-model.number="line.discount_percentage" type="number" min="0" max="100" step="0.1" class="inv-fi" @input="calcLine(line)" placeholder="0"/>
                          </div>
                          <div class="po-item-field">
                            <label>Tax Template</label>
                            <select v-model="line.tax_code" class="inv-fi">
                              <option value="">— No Tax —</option>
                              <option v-for="t in taxTemplates" :key="t.name" :value="t.name">{{ t.name }}</option>
                            </select>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <button class="inv-add-line-btn" style="margin-top:12px" @click="addLine">
                  <span v-html="icon('plus',12)"></span> Add Item
                </button>

                <!-- Totals -->
                <div class="po-totals" style="margin-top:16px">
                  <div style="font-size:12px;color:#6b7280">Tax is applied per item via Tax Template.</div>
                  <div class="po-totals-right">
                    <div class="po-total-row"><span>Subtotal</span><span>{{ fmtAmt(subtotal) }}</span></div>
                    <template v-for="tl in taxLines" :key="tl.template">
                      <div class="po-total-row"><span>{{ tl.template }} ({{ tl.rate }}%)</span><span>{{ fmtAmt(tl.amount) }}</span></div>
                    </template>
                    <div v-if="!taxLines.length" class="po-total-row"><span>Tax</span><span>{{ fmtAmt(0) }}</span></div>
                    <div class="po-total-row grand"><span>Grand Total</span><span>{{ fmtAmt(grandTotal) }}</span></div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Terms & Notes Card -->
            <div class="add-card">
              <div class="add-card-header" @click="collapsed.notes=!collapsed.notes">
                <div class="add-card-title">
                  <span class="add-card-title-icon">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                  </span>
                  Terms & Notes
                </div>
                <span class="add-card-chevron" :class="{collapsed:collapsed.notes}">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
                </span>
              </div>
              <div class="add-card-body" :class="{collapsed:collapsed.notes}">
                <div>
                  <label class="inv-lbl">Terms & Conditions <span style="color:#9ca3af;font-weight:400">(printed on order)</span></label>
                  <textarea v-model="form.terms" rows="3" class="inv-fi" style="resize:vertical" maxlength="500" placeholder="Payment terms, delivery terms…"></textarea>
                  <div class="exp-field-hint" :class="{'exp-field-hint-err': (form.terms||'').length >= 500}">{{ (form.terms||'').length }}/500 characters</div>
                </div>
              </div>
            </div>

          </div><!-- /inv-dbody -->
          </div><!-- /inv-content-row -->

          <!-- Footer -->
          <div class="inv-dfooter">
            <div class="add-footer-status">{{ editingName ? 'Editing: ' + editingName : 'New sales order — unsaved changes' }}</div>
            <div class="add-footer-actions">
              <button class="add-btn-cancel" @click="drawerOpen=false">Cancel</button>
              <button class="add-btn-draft" :disabled="drawerSaving" @click="saveSO('Draft')">
                <span v-html="icon('save',13)"></span> Save Draft
              </button>
              <button class="add-btn-more" :disabled="drawerSaving" @click="saveSO('To Deliver')">
                <span v-html="icon('check',13)"></span> {{ drawerSaving ? 'Saving…' : 'Confirm Order' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- ── View Drawer ── -->
      <div v-if="viewOpen&&viewDoc" class="inv-drawer-bg" @click.self="viewOpen=false">
        <div class="inv-drawer-panel inv-drawer-wide inv-view-page">

          <!-- Top header -->
          <div class="inv-view-header">
            <div class="inv-view-header-left">
              <div class="inv-view-title-row">
                <span class="inv-view-number">{{ viewDoc.name }}</span>
                <span class="inv-hdr-badge" :class="badgeClass(viewDoc)">{{ displayStatus(viewDoc) }}</span>
              </div>
              <div class="inv-view-subtitle">
                <span class="inv-cust-link">
                  <DocLink doctype="Customer" :name="viewDoc.customer" :mono-style="false">{{ viewDoc.customer_name||viewDoc.customer }}</DocLink>
                </span>
                <span v-if="viewDoc.delivery_date"> · Delivery {{ fmtDate(viewDoc.delivery_date) }}
                  <span v-if="isPastDelivery(viewDoc)" style="color:#fca5a5"> (overdue)</span>
                </span>
              </div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
              <button v-if="canDeliver(viewDoc)" class="inv-view-cta" style="background:#d97706" :disabled="!$canCreate('invoices')" :title="!$canCreate('invoices') ? 'Read-only access' : ''" @click="openDeliverModal(viewDoc)">
                <span v-html="icon('truck',14)"></span> Create Delivery Note
              </button>
              <button v-if="canInvoice(viewDoc)" class="inv-view-cta" :disabled="!$canCreate('invoices')" :title="!$canCreate('invoices') ? 'Read-only access' : ''" @click="openInvoiceModal(viewDoc)">
                <span v-html="icon('repeat',14)"></span> Invoice
              </button>
              <button class="inv-ab-btn" style="padding:7px 12px;font-size:13px" @click="viewOpen=false">
                <span v-html="icon('x',14)"></span> <span class="ab-label">Close</span>
              </button>
            </div>
          </div>

          <!-- Main white card -->
          <div class="inv-view-body">

            <!-- Status timeline -->
            <div class="inv-tl-wrap">
              <div class="inv-tl">
                <div class="inv-tl-progress" :style="{ width: tlProgressWidth }"></div>
                <template v-for="(step, i) in timelineSteps" :key="i">
                  <div class="inv-tl-step"
                       :class="{ 'tl-done': step.done && !step.danger, 'tl-danger': step.danger, 'tl-pending': !step.done && !step.danger }">
                    <div class="inv-tl-dot"
                         :style="step.done && !step.danger ? 'background:#16a34a;border-color:#16a34a;color:#fff' : step.danger ? 'background:#dc2626;border-color:#dc2626;color:#fff' : ''">
                      <span v-if="step.done && !step.danger" v-html="icon('check',14)"></span>
                      <span v-else-if="step.danger" style="font-size:11px;font-weight:800">!</span>
                    </div>
                    <div class="inv-tl-label"
                         :style="step.done && !step.danger ? 'color:#16a34a;font-weight:700' : ''">
                      {{ step.label }}
                    </div>
                  </div>
                </template>
              </div>
            </div>

            <!-- Action buttons bar -->
            <div class="inv-action-bar">
              <button v-if="isDraft(viewDoc)" class="inv-ab-btn" @click="viewOpen=false;openEdit(viewDoc)">
                <span v-html="icon('edit',13)"></span> <span class="ab-label">Edit</span>
              </button>
              <button class="inv-ab-btn" @click="emailSO(viewDoc)">
                <span v-html="icon('mail',13)"></span> <span class="ab-label">Email</span>
              </button>
              <div style="position:relative;display:inline-flex">
                <button class="inv-ab-btn inv-ab-dropdown" @click="showDownloadMenu=!showDownloadMenu">
                  <span v-html="icon('download',13)"></span> <span class="ab-label">Download</span>
                  <span class="inv-ab-caret">▾</span>
                </button>
                <div v-if="showDownloadMenu" class="inv-dl-menu">
                  <div class="inv-dl-menu-header">Export Sales Order</div>
                  <button @click="downloadSOPdf('pdf')" class="inv-dl-menu-item">
                    <span class="inv-dl-menu-icon" v-html="icon('download',14)"></span>
                    <span class="inv-dl-menu-text">
                      <span class="inv-dl-menu-label">Download PDF</span>
                      <span class="inv-dl-menu-sub">Save to your device</span>
                    </span>
                  </button>
                  <button @click="downloadSOPdf('print')" class="inv-dl-menu-item">
                    <span class="inv-dl-menu-icon" v-html="icon('printer',14)"></span>
                    <span class="inv-dl-menu-text">
                      <span class="inv-dl-menu-label">Open &amp; Print</span>
                      <span class="inv-dl-menu-sub">Preview in new tab</span>
                    </span>
                  </button>
                </div>
              </div>
              <button v-if="canDeliver(viewDoc)" class="inv-ab-btn" style="color:#d97706;border-color:rgba(217,119,6,.3)" :disabled="!$canCreate('invoices')" :title="!$canCreate('invoices') ? 'Read-only access' : ''" @click="openDeliverModal(viewDoc)">
                <span v-html="icon('truck',13)"></span> <span class="ab-label">Delivery Note</span>
              </button>
              <button v-if="canInvoice(viewDoc)" class="inv-ab-btn" style="color:#16a34a;border-color:rgba(22,163,106,.3)" :disabled="!$canCreate('invoices')" :title="!$canCreate('invoices') ? 'Read-only access' : ''" @click="openInvoiceModal(viewDoc)">
                <span v-html="icon('repeat',13)"></span> <span class="ab-label">Invoice</span>
              </button>
              <button v-if="isDraft(viewDoc)" class="inv-ab-btn" style="color:#16a34a;border-color:rgba(22,163,106,.3)" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="submitSO(viewDoc)">
                <span v-html="icon('check',13)"></span> <span class="ab-label">Submit</span>
              </button>
              <button v-if="canCancel(viewDoc)" class="inv-ab-btn inv-ab-danger" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="cancelSO(viewDoc)">
                <span v-html="icon('x',13)"></span> <span class="ab-label">Cancel</span>
              </button>
              <button v-if="canDelete(viewDoc)" class="inv-ab-btn inv-ab-danger" :disabled="!$canDelete('invoices')" :title="!$canDelete('invoices') ? 'Not permitted' : ''" @click="deleteSO(viewDoc)">
                <span v-html="icon('trash',13)"></span> <span class="ab-label">Delete</span>
              </button>
            </div>

            <!-- Tabs -->
            <div class="inv-view-tabs">
              <button class="inv-vtab" :class="{ active: viewTab==='details' }" @click="viewTab='details'">Details</button>
              <button class="inv-vtab" :class="{ active: viewTab==='fulfill' }" @click="viewTab='fulfill'">Fulfillment</button>
              <button class="inv-vtab" :class="{ active: viewTab==='links' }" @click="viewTab='links'">
                Linked <span v-if="links.sales_invoices.length>0" class="inv-vtab-count">{{ links.sales_invoices.length }}</span>
              </button>
            </div>

            <!-- ── Details tab ── -->
            <template v-if="viewTab==='details'">
              <div class="inv-tab-body">

                <!-- Details meta row -->
                <div class="inv-details-meta">
                  <div class="inv-details-meta-col col-customer">
                    <div class="inv-dmeta-icon-row">
                      <span class="inv-dmeta-icon" v-html="icon('user',13)"></span>
                      <span class="inv-dmeta-lbl">Customer</span>
                    </div>
                    <div class="inv-dmeta-primary">
                      <DocLink doctype="Customer" :name="viewDoc.customer" :mono-style="false">{{ viewDoc.customer_name||viewDoc.customer }}</DocLink>
                    </div>
                  </div>
                  <div class="inv-details-meta-col">
                    <div class="inv-dmeta-icon-row">
                      <span class="inv-dmeta-icon" v-html="icon('calendar',13)"></span>
                      <span class="inv-dmeta-lbl">Order Date</span>
                    </div>
                    <div class="inv-dmeta-date-val">{{ fmtDate(viewDoc.transaction_date) }}</div>
                  </div>
                  <div class="inv-details-meta-col">
                    <div class="inv-dmeta-icon-row">
                      <span class="inv-dmeta-icon" v-html="icon('calendar',13)"></span>
                      <span class="inv-dmeta-lbl">Delivery Date</span>
                    </div>
                    <div class="inv-dmeta-date-val" :class="{ 'is-overdue': isPastDelivery(viewDoc) }">
                      {{ fmtDate(viewDoc.delivery_date) || '—' }}
                    </div>
                  </div>
                  <div class="inv-details-meta-col">
                    <div class="inv-dmeta-icon-row">
                      <span class="inv-dmeta-icon" v-html="icon('indianrupee',13)"></span>
                      <span class="inv-dmeta-lbl">Grand Total</span>
                      <span v-if="viewDoc.currency && viewDoc.currency !== 'INR'" style="font-size:10px;font-weight:700;background:#eff6ff;color:#2563eb;border:1px solid #bfdbfe;border-radius:4px;padding:1px 5px;margin-left:4px">{{ viewDoc.currency }}</span>
                    </div>
                    <div class="inv-balance-val">
                      {{ fmtAmt(viewDoc.grand_total, viewDoc.currency) }}
                    </div>
                  </div>
                </div>

                <div v-if="viewDoc.set_warehouse" style="margin-top:10px;display:flex;align-items:center;gap:8px;font-size:12.5px">
                  <span style="color:#6b7280;font-weight:600">Dispatch Warehouse:</span>
                  <span style="background:#eff6ff;border:1px solid #bfdbfe;color:#1d4ed8;border-radius:5px;padding:2px 10px;font-weight:600;display:inline-flex;align-items:center;gap:5px"><span v-html="icon('warehouse',12)"></span>{{ viewDoc.set_warehouse }}</span>
                </div>

                <div v-if="viewLoading" style="padding:24px;text-align:center;color:#9ca3af">Loading details…</div>

                <template v-else>
                  <!-- Line items table -->
                  <div v-if="viewItems.length" class="inv-items-wrap">
                    <table class="inv-items-table">
                      <thead>
                        <tr>
                          <th style="width:36px">#</th>
                          <th>Item &amp; Description</th>
                          <th class="th-r">Qty</th>
                          <th class="th-r">Rate</th>
                          <th class="th-r">Discount</th>
                          <th class="th-r">Amount</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(it,i) in viewItems" :key="i">
                          <td class="inv-item-num">{{ i+1 }}</td>
                          <td>
                            <div class="inv-item-name">{{ it.item_name||it.item_code }}</div>
                            <div v-if="it.description" class="inv-item-desc">{{ it.description }}</div>
                          </td>
                          <td class="td-r">{{ flt(it.qty) }}</td>
                          <td class="td-r">{{ fmtAmt(it.rate, viewDoc.currency) }}</td>
                          <td class="td-r inv-dash">{{ flt(it.discount_percentage) ? flt(it.discount_percentage) + '%' : '—' }}</td>
                          <td class="td-r" style="font-weight:600">{{ fmtAmt(it.amount, viewDoc.currency) }}</td>
                        </tr>
                      </tbody>
                    </table>

                    <!-- Totals section -->
                    <div class="inv-totals-section">
                      <div class="inv-totals-inner">
                        <div v-if="viewSubtotal" class="inv-total-line">
                          <span class="t-lbl">Subtotal</span>
                          <span class="t-amt">{{ fmtAmt(viewSubtotal, viewDoc.currency) }}</span>
                        </div>
                        <div v-if="viewDiscountTotal" class="inv-total-line">
                          <span class="t-lbl">Discount</span>
                          <span class="t-amt">-{{ fmtAmt(viewDiscountTotal, viewDoc.currency) }}</span>
                        </div>
                        <template v-if="viewDoc.taxes && viewDoc.taxes.length">
                          <div v-for="(tx,i) in viewDoc.taxes" :key="i" class="inv-total-line">
                            <span class="t-lbl">{{ tx.description || tx.account_head }}</span>
                            <span class="t-amt">{{ fmtAmt(tx.tax_amount || 0, viewDoc.currency) }}</span>
                          </div>
                        </template>
                        <div class="inv-grand-total-line">
                          <span class="inv-grand-lbl">Grand Total</span>
                          <span class="inv-grand-amt">{{ fmtAmt(viewDoc.grand_total, viewDoc.currency) }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div v-else style="color:#9ca3af;font-size:13px;padding:8px 0">No item details available.</div>
                </template>
              </div>

              <!-- Bottom grid: Notes -->
              <div style="margin:5px">
                <!-- Address card -->
                <div v-if="viewDoc.billing_address||viewDoc.shipping_address" class="inv-bottom-card" style="margin-bottom:5px">
                  <div class="inv-bottom-card-header">
                    <div class="inv-bottom-card-title"><span v-html="icon('map-pin',14)"></span> Addresses</div>
                  </div>
                  <div class="inv-bottom-card-body">
                    <div class="view-address-grid">
                      <div v-if="viewDoc.billing_address">
                        <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px">
                          <span v-html="icon('map-pin',12)" style="color:#6b7280"></span>
                          <span style="font-size:10.5px;font-weight:700;text-transform:uppercase;color:#6b7280;letter-spacing:0.5px">Billing Address</span>
                        </div>
                        <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px 14px">
                          <span style="display:inline-block;background:#dbeafe;color:#2563eb;font-size:10px;font-weight:700;text-transform:uppercase;padding:2px 8px;border-radius:20px;letter-spacing:0.4px;margin-bottom:8px">Billing</span>
                          <div style="font-size:13px;color:#374151;line-height:1.65;">{{ displayAddr(viewDoc.billing_address) }}</div>
                        </div>
                      </div>
                      <div v-if="viewDoc.shipping_address">
                        <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px">
                          <span v-html="icon('map-pin',12)" style="color:#6b7280"></span>
                          <span style="font-size:10.5px;font-weight:700;text-transform:uppercase;color:#6b7280;letter-spacing:0.5px">Shipping Address</span>
                        </div>
                        <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px 14px">
                          <span style="display:inline-block;background:#dbeafe;color:#2563eb;font-size:10px;font-weight:700;text-transform:uppercase;padding:2px 8px;border-radius:20px;letter-spacing:0.4px;margin-bottom:8px">Shipping</span>
                          <div style="font-size:13px;color:#374151;line-height:1.65;">{{ displayAddr(viewDoc.shipping_address) }}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <!-- Terms & Notes card -->
                <div class="inv-bottom-card">
                  <div class="inv-bottom-card-header">
                    <div class="inv-bottom-card-title">
                      <span v-html="icon('sticky-note',14)"></span> Terms &amp; Notes
                    </div>
                  </div>
                  <div class="inv-bottom-card-body">
                    <div v-if="viewDoc.terms">
                      <div style="font-size:13px;color:#374151;word-break: break-word;">{{ viewDoc.terms }}</div>
                    </div>
                    <div v-else class="inv-notes-empty">
                      <div class="inv-notes-empty-icon" v-html="icon('file-text',36)"></div>
                      <div class="inv-notes-empty-text">No terms added yet</div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Footer -->
              <div class="inv-view-footer" v-if="viewDoc.owner">
                Created by {{ viewDoc.owner }} on {{ fmtDate(viewDoc.creation) }}
              </div>
            </template>

            <!-- ── Fulfillment tab ── -->
            <template v-if="viewTab==='fulfill'">
              <div class="inv-tab-body">
                <div v-if="viewLoading" style="padding:24px;text-align:center;color:#9ca3af">Loading…</div>
                <template v-else-if="fulfill.lines.length">
                  <div style="font-size:12px;color:#6b7280;margin-bottom:12px">
                    Status: <strong>{{ fulfill.computed_status }}</strong>
                  </div>
                  <div class="inv-items-wrap">
                    <table class="inv-items-table">
                      <thead>
                        <tr>
                          <th>Item</th>
                          <th class="th-r">Ordered</th>
                          <th class="th-r">Delivered</th>
                          <th class="th-r">Invoiced</th>
                          <th class="th-r">Remaining</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="l in fulfill.lines" :key="l.name">
                          <td>{{ l.item_name||l.item_code }}</td>
                          <td class="td-r mono-sm">{{ l.qty }}</td>
                          <td class="td-r mono-sm" :class="l.delivered_qty>=l.qty?'text-success':'text-muted'">{{ l.delivered_qty }}</td>
                          <td class="td-r mono-sm" :class="l.billed_qty>=l.qty?'text-success':'text-muted'">{{ l.billed_qty }}</td>
                          <td class="td-r mono-sm text-danger">{{ l.remaining_to_deliver }} / {{ l.remaining_to_bill }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  <div v-if="hasUndelivered && !isDraft(viewDoc) && (viewDoc?.status||'').toLowerCase() !== 'cancelled'" style="display:flex;gap:8px;justify-content:flex-end;margin-top:12px">
                    <button class="inv-ab-btn" style="color:#d97706;border-color:rgba(217,119,6,.3)" @click="openDeliverModal(viewDoc)" :disabled="actionRunning || !$canCreate('invoices')" :title="!$canCreate('invoices') ? 'Read-only access' : ''">
                      <span v-html="icon('truck',13)"></span> <span class="ab-label">Create Delivery Note</span>
                    </button>
                  </div>
                </template>
                <div v-else style="text-align:center;padding:24px;color:#9ca3af;font-size:13px">No line items.</div>
              </div>
            </template>

            <!-- ── Links tab ── -->
            <template v-if="viewTab==='links'">
              <div class="inv-tab-body">
                <div v-if="viewLoading" style="padding:24px;text-align:center;color:#9ca3af">Loading…</div>
                <template v-else>
                  <div v-if="viewDoc.ref_quote" style="margin-bottom:16px">
                    <div style="font-size:11px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px">Originating Quote</div>
                    <div style="padding:10px 14px;border:1px solid #e8ecf0;border-radius:6px;background:#fff;display:flex;align-items:center;justify-content:space-between">
                      <DocLink doctype="Quotation" :name="viewDoc.ref_quote" />
                      <span class="text-muted">Quotation</span>
                    </div>
                  </div>
                  <div v-if="links.delivery_challans.length" style="margin-bottom:16px">
                    <div style="font-size:11px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px">Delivery Notes</div>
                    <div class="inv-items-wrap">
                      <table class="inv-items-table">
                        <thead>
                          <tr>
                            <th>Delivery Note #</th>
                            <th>Date</th>
                            <th class="th-r">Qty</th>
                            <th>Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="dn in links.delivery_challans" :key="dn.name">
                            <td><DocLink doctype="Delivery Note" :name="dn.name" /></td>
                            <td class="mono-sm text-muted">{{ fmtDate(dn.posting_date) }}</td>
                            <td class="td-r mono-sm">{{ dn.total_qty }}</td>
                            <td class="mono-sm">{{ dn.status }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                  <div v-if="links.sales_invoices.length">
                    <div style="font-size:11px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px">Sales Invoices</div>
                    <div class="inv-items-wrap">
                      <table class="inv-items-table">
                        <thead>
                          <tr>
                            <th>Invoice #</th>
                            <th>Date</th>
                            <th class="th-r">Outstanding</th>
                            <th class="th-r">Total</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="si in links.sales_invoices" :key="si.name">
                            <td><DocLink doctype="Sales Invoice" :name="si.name" /></td>
                            <td class="mono-sm text-muted">{{ fmtDate(si.posting_date) }}</td>
                            <td class="td-r mono-sm">{{ fmtCur(si.outstanding_amount) }}</td>
                            <td class="td-r mono-sm" style="font-weight:600">{{ fmtCur(si.grand_total) }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                  <div v-if="!viewDoc.ref_quote && !links.sales_invoices.length && !links.delivery_challans.length"
                    style="text-align:center;padding:48px;color:#9ca3af;font-size:13px">
                    No linked documents yet.
                  </div>
                </template>
              </div>
            </template>

          </div><!-- /inv-view-body -->
        </div><!-- /inv-drawer-panel -->
      </div><!-- /inv-drawer-bg -->

      <!-- ── Convert-to-Invoice modal ── -->
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
              <option>Billing</option><option>Shipping</option><option>Office</option>
              <option>Postal</option><option>Warehouse</option><option>Other</option>
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
          <div><label class="inv-lbl">City</label><input v-model="addrModal.city" type="text" class="inv-fi" placeholder="City" /></div>
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
          <div><label class="inv-lbl">Pin Code</label><input v-model="addrModal.pincode" type="text" class="inv-fi" placeholder="PIN" /></div>
        </div>
      </div>
      <div class="inv-dfooter">
        <button class="form-btn form-btn-outline" @click="addrModal.open=false" :disabled="addrModal.saving">Cancel</button>
        <button class="form-btn form-btn-primary" :disabled="addrModal.saving" @click="saveNewAddress">
          {{ addrModal.saving ? 'Saving…' : 'Save Address' }}
        </button>
      </div>
    </div>

      <div v-if="invModal.open" class="rp-backdrop" @click.self="invModal.open=false">
        <div class="rp-dialog" style="max-width:640px">
          <div class="rp-dialog-header">
            <span class="rp-dialog-title">Convert to Invoice — {{ invModal.soName }}</span>
            <button class="rp-close-btn" @click="invModal.open=false">✕</button>
          </div>
          <div class="rp-body">
            <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:12px">
              <div style="font-size:12.5px;color:#374151;">Enter the quantity to invoice for each line:</div>
              <div v-if="invModal.warehouse" style="display:inline-flex; align-items:center; background:#eff6ff; color:#2563eb; border: 1px solid #bfdbfe; padding: 4px 8px; font-weight: 500; font-size: 12px; border-radius: 6px;">
                <span v-html="icon('warehouse', 14)" style="margin-right: 6px;"></span>{{ invModal.warehouse }}
              </div>
            </div>
            <div style="border:1px solid #e8ecf0;border-radius:8px;overflow:hidden;margin-bottom:14px">
              <!-- Header -->
              <div class="inv-ci-grid inv-ci-header" :style="invModalNeedsBatch ? 'grid-template-columns: 2fr 2.5fr 1.2fr 1.2fr 1.8fr 1.8fr;' : 'grid-template-columns: 2fr 3fr 1.5fr 1.5fr 2fr;'">
                <span>Item Code</span>
                <span>Item Name</span>
                <span class="ta-c">WH QTY</span>
                <span class="ta-c">REMAINING</span>
                <span class="ta-c">INVOICE QTY</span>
                <span v-if="invModalNeedsBatch" class="ta-c">BATCH</span>
              </div>
              <!-- Fully-invoiced lines (read-only) -->
              <div v-for="l in invModal.allLines.filter(l => l.remaining_to_bill <= 0)" :key="'done-'+l.name"
                class="inv-ci-grid inv-ci-row inv-ci-done" :style="invModalNeedsBatch ? 'grid-template-columns: 2fr 2.5fr 1.2fr 1.2fr 1.8fr 1.8fr;' : 'grid-template-columns: 2fr 3fr 1.5fr 1.5fr 2fr;'">
                <div style="font-weight:600;color:#374151;font-size:12.5px">{{ l.item_code }}</div>
                <div style="font-size:12.5px;color:#6b7280">{{ l.item_name || '—' }}</div>
                <span class="ta-c mono-sm" style="color:#9ca3af">{{ l.warehouse_qty || 0 }}</span>
                <span class="ta-c mono-sm" style="color:#9ca3af">0</span>
                <span class="ta-c mono-sm" style="color:#9ca3af">—</span>
                <span v-if="invModalNeedsBatch" class="ta-c" style="font-size:12px;color:#6b7280">{{ (l.invoiced_batches && l.invoiced_batches.length) ? l.invoiced_batches.map(b => b.batch_no).join(', ') : '' }}</span>
              </div>
              <!-- Pending lines (editable) -->
              <template v-for="l in invModal.lines" :key="l.name">
                <div class="inv-ci-grid inv-ci-row" :style="invModalNeedsBatch ? 'grid-template-columns: 2fr 2.5fr 1.2fr 1.2fr 1.8fr 1.8fr;' : 'grid-template-columns: 2fr 3fr 1.5fr 1.5fr 2fr;'">
                  <div style="font-weight:600;color:#111827;font-size:12.5px">{{ l.item_code }}</div>
                  <div style="font-size:12.5px;color:#6b7280">{{ l.item_name || '—' }}</div>
                  <span class="ta-c mono-sm text-muted">{{ l.warehouse_qty || 0 }}</span>
                  <span class="ta-c mono-sm text-muted">{{ l.remaining_to_bill }}</span>
                  <div style="text-align:center">
                    <input v-model.number="l.toInvoice" type="number" min="0" :max="l.remaining_to_bill" step="0.001"
                      class="inv-ci" style="width:70px;text-align:center"/>
                  </div>
                  <SearchableSelect v-if="invModalNeedsBatch && l.has_batch_no" v-model="l.batch_no"
                    :options="l.batchOptions" placeholder="Select"
                    @update:modelValue="onInvBatchSelect(l, $event)"
                    :title="!l.batchOptions.length ? 'No batches with stock yet' : ''"
                    style="width:70px; margin:0 auto; text-align:left"/>
                  <span v-else-if="invModalNeedsBatch"></span>
                </div>
                <div v-if="l.has_batch_no && !l.batch_no" class="po-items-error-row" style="padding:4px 10px;font-size:11.5px;color:#b91c1c;background:#fef2f2">
                  <span v-html="icon('alert-circle',12)"></span> {{ l.item_name || l.item_code }} is batch-tracked — select a Batch No
                </div>
              </template>
            </div>
            <div>
              <label class="inv-lbl">Due Date</label>
              <input v-model="invModal.dueDate" type="date" class="inv-fi" style="max-width:200px"/>
            </div>
            <div style="text-align:right;font-size:13px;color:#6b7280;margin-top:12px">
              Invoice Total: <strong style="color:#1a6ef7;font-size:15px;">{{ fmtCur(invModalTotal) }}</strong>
            </div>
          </div>
          <div class="rp-footer">
            <button class="rp-btn rp-btn-outline" @click="invModal.open=false" :disabled="invModal.saving">Cancel</button>
            <button class="rp-btn inv-create-btn" :disabled="invModal.saving||invModalTotal<=0" @click="submitInvoice">
              <span v-if="invModal.saving" class="inv-create-spinner"></span>
              <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/>
              </svg>
              {{ invModal.saving ? 'Creating Invoice…' : `Create Invoice ${fmtCur(invModalTotal)}` }}
            </button>
          </div>
        </div>
      </div>

      <!-- ── Create Delivery Note modal ── -->
      <div v-if="deliverModal.open" class="rp-backdrop" @click.self="deliverModal.open=false">
        <div class="rp-dialog" style="max-width:640px">
          <div class="rp-dialog-header">
            <span class="rp-dialog-title">Create Delivery Note — {{ deliverModal.soName }}</span>
            <button class="rp-close-btn" @click="deliverModal.open=false">✕</button>
          </div>
          <div class="rp-body">
            <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:12px">
              <div style="font-size:12.5px;color:#374151;">Enter the quantity to deliver for each line:</div>
              <div v-if="deliverModal.warehouse" style="display:inline-flex; align-items:center; background:#eff6ff; color:#2563eb; border: 1px solid #bfdbfe; padding: 4px 8px; font-weight: 500; font-size: 12px; border-radius: 6px;">
                <span v-html="icon('warehouse', 14)" style="margin-right: 6px;"></span>{{ deliverModal.warehouse }}
              </div>
            </div>
            <div style="border:1px solid #e8ecf0;border-radius:8px;overflow:hidden;margin-bottom:14px">
              <div class="inv-ci-grid inv-ci-header" :style="deliverModalNeedsBatch ? 'grid-template-columns: 2fr 2.5fr 1.2fr 1.2fr 1.8fr 1.8fr;' : 'grid-template-columns: 2fr 3fr 1.5fr 1.5fr 2fr;'">
                <span>Item Code</span>
                <span>Item Name</span>
                <span class="ta-c">WH QTY</span>
                <span class="ta-c">REMAINING</span>
                <span class="ta-c">DELIVER QTY</span>
                <span v-if="deliverModalNeedsBatch" class="ta-c">BATCH</span>
              </div>
              <div v-for="l in deliverModal.allLines.filter(l => l.remaining_to_deliver <= 0)" :key="'done-'+l.name"
                class="inv-ci-grid inv-ci-row inv-ci-done" :style="deliverModalNeedsBatch ? 'grid-template-columns: 2fr 2.5fr 1.2fr 1.2fr 1.8fr 1.8fr;' : 'grid-template-columns: 2fr 3fr 1.5fr 1.5fr 2fr;'">
                <div style="font-weight:600;color:#374151;font-size:12.5px">{{ l.item_code }}</div>
                <div style="font-size:12.5px;color:#6b7280">{{ l.item_name || '—' }}</div>
                <span class="ta-c mono-sm" style="color:#9ca3af">{{ l.warehouse_qty || 0 }}</span>
                <span class="ta-c mono-sm" style="color:#9ca3af">0</span>
                <span class="ta-c mono-sm" style="color:#9ca3af">—</span>
                <span v-if="deliverModalNeedsBatch" class="ta-c" style="font-size:12px;color:#6b7280">{{ (l.delivered_batches && l.delivered_batches.length) ? l.delivered_batches.map(b => b.batch_no).join(', ') : '' }}</span>
              </div>
              <template v-for="l in deliverModal.lines" :key="l.name">
                <div class="inv-ci-grid inv-ci-row" :style="deliverModalNeedsBatch ? 'grid-template-columns: 2fr 2.5fr 1.2fr 1.2fr 1.8fr 1.8fr;' : 'grid-template-columns: 2fr 3fr 1.5fr 1.5fr 2fr;'">
                  <div style="font-weight:600;color:#111827;font-size:12.5px">{{ l.item_code }}</div>
                  <div style="font-size:12.5px;color:#6b7280">{{ l.item_name || '—' }}</div>
                  <span class="ta-c mono-sm text-muted">{{ l.warehouse_qty || 0 }}</span>
                  <span class="ta-c mono-sm text-muted">{{ l.remaining_to_deliver }}</span>
                  <div style="text-align:center">
                    <input v-model.number="l.toDeliver" type="number" min="0" :max="l.remaining_to_deliver" step="0.001"
                      class="inv-ci" style="width:70px;text-align:center"/>
                  </div>
                  <SearchableSelect v-if="deliverModalNeedsBatch && l.has_batch_no" v-model="l.batch_no"
                    :options="l.batchOptions" placeholder="Select"
                    @update:modelValue="onDeliverBatchSelect(l, $event)"
                    :title="!l.batchOptions.length ? 'No batches with stock yet' : ''"
                    style="width:70px; margin:0 auto; text-align:left"/>
                  <span v-else-if="deliverModalNeedsBatch"></span>
                </div>
                <div v-if="l.has_batch_no && !l.batch_no" class="po-items-error-row" style="padding:4px 10px;font-size:11.5px;color:#b91c1c;background:#fef2f2">
                  <span v-html="icon('alert-circle',12)"></span> {{ l.item_name || l.item_code }} is batch-tracked — select a Batch No
                </div>
              </template>
            </div>
            <div class="inv-fg inv-fg2">
              <div>
                <label class="inv-lbl">LR No.</label>
                <input v-model="deliverModal.lrNo" type="text" class="inv-fi" placeholder="Transporter LR / AWB no." />
              </div>
              <div>
                <label class="inv-lbl">Transporter</label>
                <input v-model="deliverModal.transporterName" type="text" class="inv-fi" placeholder="Transporter name" />
              </div>
            </div>
          </div>
          <div class="rp-footer">
            <button class="rp-btn rp-btn-outline" @click="deliverModal.open=false" :disabled="deliverModal.saving">Cancel</button>
            <button class="rp-btn inv-create-btn" :disabled="deliverModal.saving||deliverModalQty<=0" @click="submitDeliver">
              <span v-if="deliverModal.saving" class="inv-create-spinner"></span>
              <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>
              {{ deliverModal.saving ? 'Creating…' : 'Create Delivery Note' }}
            </button>
          </div>
        </div>
      </div>

    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from "vue";
import { apiList, apiSave, apiGet, apiGET, apiPOST, apiDelete, apiSubmit, resolveCompany, refreshCsrfToken } from "../api/client.js";
import { COUNTRIES, statesFor } from "../composables/useCountryState.js";
import { useToast } from "../composables/useToast.js";
import { usePermissions } from "../composables/usePermissions.js";
import { useRoute } from "vue-router";
import { useEmailDialog } from "../composables/useEmailDialog.js";
import { useOpenFromQuery } from "../composables/useOpenFromQuery.js";
import { usePagination } from "../composables/usePagination.js";
import DocLink from "../components/DocLink.vue";
import Pagination from "../components/Pagination.vue";
import { useConfirm } from "../composables/useConfirm.js";
import { useLivePreview } from "../composables/useLivePreview.js";
import { icon } from "../utils/icons.js";
import { flt, fmtDate } from "../utils/format.js";
import { templateHeadlineRate } from "../composables/useTaxCalc.js";
import SearchableSelect from "../components/SearchableSelect.vue";

const { toast } = useToast();
const { canCreate, canEdit, canDelete: canDeleteModule } = usePermissions();
const route = useRoute();
const { confirm } = useConfirm();
const { printDoc, renderDocument, setCompany, refreshBranding } = useLivePreview();
async function printSO(d) { try { await refreshBranding(); } catch {} printDoc({ ...d, items: viewItems.value }, { title: "SALES ORDER", partyLabel: "Customer", partyField: "customer_name", companyName: d?.company || "" }); }

const showDownloadMenu = ref(false);

function downloadSOPdf(mode = 'pdf') {
  showDownloadMenu.value = false;
  const doc = { ...viewDoc.value, items: viewItems.value };
  if (!doc?.name) return;
  const html = renderDocument(doc, {
    title: "SALES ORDER",
    partyLabel: "Customer",
    partyField: "customer_name",
    companyName: doc.company || window.__booksCompany || "",
  });
  if (mode === 'print') {
    const win = window.open('', '_blank');
    if (!win) { toast('Pop-up blocked — allow pop-ups to print', 'error'); return; }
    win.document.write(html); win.document.close();
    setTimeout(() => { try { win.focus(); win.print(); } catch {} }, 600);
  } else {
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
    const objectUrl = URL.createObjectURL(blob);
    const win = window.open(objectUrl, '_blank');
    if (!win) { URL.revokeObjectURL(objectUrl); toast('Pop-up blocked — allow pop-ups to download', 'error'); return; }
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
  { key: "toDeliver", label: "To Deliver" },
  { key: "toInvoice", label: "To Invoice" },
  { key: "closed",    label: "Closed" },
  { key: "cancelled", label: "Cancelled" },
];

const list = ref([]), loading = ref(false), search = ref(""), selected = ref(new Set());
const viewMode = ref("table"); // "table" | "grid"
const drawerOpen = ref(false), drawerSaving = ref(false), editingName = ref("");
const viewOpen = ref(false), viewDoc = ref(null), viewTab = ref("details");
const viewLoading = ref(false), viewItems = ref([]);
// Sum of per-line discounts and the pre-discount subtotal for the SO being
// viewed — item.amount from the backend is already post-discount, so the
// "Subtotal" line must add the discount back to show the correct gross figure.
const viewDiscountTotal = computed(() => Math.round(viewItems.value.reduce((s, it) => s + flt(it.discount_amount), 0) * 100) / 100);
const viewSubtotal = computed(() => Math.round(viewItems.value.reduce((s, it) => s + flt(it.amount), 0) * 100) / 100 + viewDiscountTotal.value);
const fulfill = reactive({ lines: [], computed_status: "" });
const links = reactive({ sales_invoices: [], delivery_challans: [] });
const customers = ref([]), items = ref([]), lines = ref([]), taxAccountHead = ref(""), taxTemplates = ref([]);
const uomList = ref(["Nos", "Kg", "Ltr", "Hrs", "Pcs", "Box", "Mtr", "Set"]);
const addressLoading = ref(false);
const sortCol = ref("transaction_date"), sortDir = ref("desc");
const actionRunning = ref(false);

// ── Collapsible state for add/edit cards ──
const collapsed = reactive({ details: false, lines: false, notes: true });

let _id = 1;
const blankLine = () => ({ id: _id++, item_code: "", description: "", qty: 1, rate: 0, uom: "Nos", discount_percentage: 0, discount_amount: 0, amount: 0, tax_code: "", available_stock: null, collapsed: false });
const form = reactive({
  customer: "", transaction_date: todayStr(), delivery_date: deliveryDefault(),
  po_number: "",
  billing_address: "", billing_address_name: "",
  shipping_address: "", shipping_address_name: "",
  set_warehouse: "", terms: "",
  currency: "INR", exchange_rate: 1,
});

// ── Address state ─────────────────────────────────────────────────────
const customerAddresses = ref([]);
const addrModal = reactive({
  open: false, saving: false, forField: "billing",
  address_title: "", address_type: "Billing",
  address_line1: "", address_line2: "", city: "", state: "", pincode: "", country: "India",
});
const selectedBillingAddr  = computed(() => customerAddresses.value.find(a => a.name === form.billing_address_name) || null);
const selectedShippingAddr = computed(() => customerAddresses.value.find(a => a.name === form.shipping_address_name) || null);
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

const invModal = reactive({ open: false, saving: false, soName: "", lines: [], allLines: [], dueDate: "" });
const deliverModal = reactive({ open: false, saving: false, soName: "", warehouse: "", lines: [], allLines: [], lrNo: "", transporterName: "" });

function todayStr() { return new Date().toISOString().slice(0, 10); }
function deliveryDefault() { const d = new Date(); d.setDate(d.getDate() + 14); return d.toISOString().slice(0, 10); }
const currencySymbol = "OMR ";
function fmtAmt(v) {
  return "OMR " + Math.abs(flt(v)).toLocaleString("en-OM", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
}
function fmtCur(v) { return fmtAmt(v); }

function isPastDelivery(o) {
  if (!o?.delivery_date) return false;
  const s = (o.status||"").toLowerCase();
  if (s === "closed" || s === "invoiced" || s === "cancelled") return false;
  return new Date(o.delivery_date) < new Date();
}
function displayStatus(o) {
  const s = o?.status;
  if (!s) return "DRAFT";
  return s.toUpperCase();
}
function badgeClass(o) {
  const s = (o?.status||"").toLowerCase();
  if (!s || s === "draft")  return "status-draft";
  if (s === "cancelled")    return "status-cancelled";
  if (s === "closed" || s === "invoiced") return "status-paid";
  if (s.includes("delivered") && !s.includes("partially")) return "status-partial";
  if (s === "to deliver" || s.includes("partially"))      return "status-overdue";
  return "status-unpaid";
}
function headerBg(o) {
  const s = (o?.status||"").toLowerCase();
  if (s === "cancelled") return "linear-gradient(135deg,#7f1d1d,#dc2626)";
  if (s === "closed" || s === "invoiced") return "linear-gradient(135deg,#064e3b,#059669)";
  if (s === "to deliver" || s.includes("partially"))    return "linear-gradient(135deg,#78350f,#d97706)";
  if (s === "delivered") return "linear-gradient(135deg,#1e3a5f,#1a6ef7)";
  return "linear-gradient(135deg,#374151,#6b7280)";
}
// NOTE: Sales Order is is_submittable=0 (see sales_order.json), so docstatus
// stays 0 for every SO regardless of status — it is NOT a valid signal for
// "has this order been confirmed". Use `status !== "Draft"` instead.
function canInvoice(o) {
  const s = (o?.status||"").toLowerCase();
  if (!s || s === "draft") return false;
  return s !== "cancelled" && s !== "closed" && s !== "invoiced";
}
function canDeliver(o) {
  const s = (o?.status||"").toLowerCase();
  if (!s || s === "draft") return false;
  return s !== "cancelled" && s !== "closed" && s !== "delivered";
}
function canCancel(o) {
  const s = (o?.status||"").toLowerCase();
  if (!s || s === "draft") return false;
  // Only cancel confirmed orders that are not already terminal
  return s !== "cancelled" && s !== "closed" && s !== "invoiced";
}
function canDelete(o) {
  const s = (o?.status||"").toLowerCase();
  // Only allow delete on draft or cancelled (never on live/closed orders)
  return s === "draft" || s === "" || s === "cancelled";
}
function isDraft(o) {
  const s = (o?.status||"").toLowerCase();
  return !s || s === "draft";
}

async function load() {
  loading.value = true;
  try {
    const co = await resolveCompany();
    list.value = await apiList("Sales Order", {
      fields: ["name", "customer", "customer_name", "transaction_date", "delivery_date", "status", "docstatus", "grand_total", "billed_amount", "ref_quote", "po_number"],
      filters: [["company", "=", co]],
      limit: 100000,
      order: "transaction_date desc, creation desc",
    });
  } catch (e) { toast.error(e.message || "Failed to load sales orders"); }
  finally { loading.value = false; }
}
async function loadTaxAccount() {
  try {
    const r = await apiList("Account", { fields: ["name"], filters: [["account_type", "=", "Tax"], ["is_group", "=", 0]], limit: 1 });
    if (r?.length) taxAccountHead.value = r[0].name;
  } catch {}
  try {
    const templates = await apiList("Tax Template", { fields: ["name"], filters: [["disabled", "=", 0], ["applies_to", "in", ["Sales", "Both"]]], limit: 100, order: "name asc" });
    const withRates = await Promise.all((templates || []).map(async t => {
      try {
        const doc = await apiGet("Tax Template", t.name);
        const rate = templateHeadlineRate(doc?.taxes);
        const account = doc?.taxes?.[0]?.account_head || taxAccountHead.value;
        return { name: t.name, rate: Number(rate), account };
      } catch { return { name: t.name, rate: 0, account: taxAccountHead.value }; }
    }));
    taxTemplates.value = withRates;
  } catch { taxTemplates.value = []; }
}

const counts = computed(() => {
  const c = { draft:0, toDeliver:0, toInvoice:0, closed:0, cancelled:0 };
  for (const o of list.value) {
    const s = (o.status||"draft").toLowerCase();
    if (s === "cancelled") c.cancelled++;
    else if (s === "closed" || s === "invoiced") c.closed++;
    else if (s === "draft") c.draft++;
    else if (s === "delivered") c.toInvoice++;
    else c.toDeliver++;
  }
  return c;
});
const summary = computed(() => ({
  totalValue: list.value.filter(o => (o.status||"").toLowerCase() !== "cancelled")
    .reduce((s, o) => s + flt(o.grand_total), 0),
}));
const _soYM  = () => { const d=new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; };
const _soLYM = () => { const d=new Date(); d.setMonth(d.getMonth()-1); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; };
const _soTr  = (a,b) => { if(!b&&!a) return {pct:0,up:true}; if(!b) return {pct:100,up:true}; const p=Math.round((a-b)/b*100); return {pct:Math.abs(p),up:p>=0}; };
const soThisMonth = computed(()=>{ const ym=_soYM(); const r=list.value.filter(o=>(o.transaction_date||'').startsWith(ym)); return {count:r.length,value:r.reduce((s,o)=>s+flt(o.grand_total),0)}; });
const soTrends = computed(()=>({
  total:     _soTr(soThisMonth.value.count, list.value.filter(o=>(o.transaction_date||'').startsWith(_soLYM())).length),
  draft:     _soTr(counts.value.draft, list.value.filter(o=>(o.transaction_date||'').startsWith(_soLYM())&&(!o.status||(o.status||'').toLowerCase()==='draft')).length),
  deliver:   _soTr(counts.value.toDeliver, list.value.filter(o=>{ if(!(o.transaction_date||'').startsWith(_soLYM())) return false; const s=(o.status||'draft').toLowerCase(); return s!=='cancelled'&&s!=='closed'&&s!=='invoiced'&&s!=='draft'&&s!=='delivered'; }).length),
  closed:    _soTr(counts.value.closed, list.value.filter(o=>(o.transaction_date||'').startsWith(_soLYM())&&((o.status||'').toLowerCase()==='closed'||(o.status||'').toLowerCase()==='invoiced')).length),
  cancelled: _soTr(counts.value.cancelled, list.value.filter(o=>(o.transaction_date||'').startsWith(_soLYM())&&(o.status||'').toLowerCase()==='cancelled').length),
}));

const filtered = computed(() => {
  let r = list.value;
  if (activeTab.value !== "all") {
    r = r.filter(o => {
      const s = (o.status||"draft").toLowerCase();
      if (activeTab.value === "draft")     return s === "draft";
      if (activeTab.value === "cancelled") return s === "cancelled";
      if (activeTab.value === "closed")    return s === "closed" || s === "invoiced";
      if (activeTab.value === "toInvoice") return s === "delivered";
      if (activeTab.value === "toDeliver") return s !== "cancelled" && s !== "closed" && s !== "invoiced" && s !== "draft" && s !== "delivered";
      return true;
    });
  }
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    r = r.filter(x => (x.name || "").toLowerCase().includes(q)
      || (x.customer_name || x.customer || "").toLowerCase().includes(q)
      || (x.po_number || "").toLowerCase().includes(q));
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

const { page, pageSize, paged } = usePagination(sorted, { storageKey: "sales-orders" });

function sortBy(col) { if (sortCol.value === col) sortDir.value = sortDir.value === "asc" ? "desc" : "asc"; else { sortCol.value = col; sortDir.value = "asc"; } }
function sortArrowTxt(col) { if (sortCol.value !== col) return ""; return sortDir.value === "asc" ? "↑" : "↓"; }

const allChecked = computed(() => sorted.value.length > 0 && sorted.value.every(o => selected.value.has(o.name)));
function toggle(n) { const s = new Set(selected.value); s.has(n) ? s.delete(n) : s.add(n); selected.value = s; }
function toggleAll(e) { selected.value = e.target.checked ? new Set(sorted.value.map(o => o.name)) : new Set(); }

const subtotal = computed(() => lines.value.reduce((s, l) => s + lineAmount(l), 0));

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

const taxAmount  = computed(() => taxLines.value.reduce((s, t) => s + t.amount, 0));
const grandTotal = computed(() => subtotal.value + taxAmount.value);

const hasUndelivered = computed(() => fulfill.lines.some(l => l.remaining_to_deliver > 0));

const timelineSteps = computed(() => {
  const o = viewDoc.value;
  if (!o) return [];
  const s = (o.status||"").toLowerCase();
  if (s === "cancelled") {
    return [
      { key:"draft", label:"Draft", done:true },
      { key:"sub",   label:"Submitted", done:true },
      { key:"end",   label:"Cancelled", danger:true, current:true },
    ];
  }
  const delivered = s === "delivered" || s === "invoiced" || s === "closed";
  const invoiced  = s === "invoiced"  || s === "closed";
  const closed    = s === "closed";
  return [
    { key:"draft",     label:"Draft",     done:true },
    { key:"submitted", label:"Submitted", done:s!=="draft", current:s==="to deliver"||s==="submitted" },
    { key:"delivered", label:"Delivered", done:delivered, current:s==="delivered" && !invoiced },
    { key:"invoiced",  label:"Invoiced",  done:invoiced, current:invoiced && !closed },
    { key:"closed",    label:"Closed",    done:closed, current:closed },
  ];
});

const tlProgressWidth = computed(() => {
  const steps = timelineSteps.value;
  if (!steps.length) return "0%";
  const doneCount = steps.filter(s => s.done || s.danger).length;
  return Math.round(((doneCount - 1) / (steps.length - 1)) * 100) + "%";
});

const invModalTotal = computed(() =>
  (invModal.lines || []).reduce((s, l) => s + flt(l.toInvoice) * flt(l.rate), 0)
);
const invModalNeedsBatch = computed(() =>
  (invModal.lines || []).some(l => l.has_batch_no)
);
const deliverModalNeedsBatch = computed(() =>
  (deliverModal.lines || []).some(l => l.has_batch_no)
);
const deliverModalQty = computed(() =>
  (deliverModal.lines || []).reduce((s, l) => s + flt(l.toDeliver), 0)
);

// ── Create / Edit ─────────────────────────────────────────────────────────
function openNew() {
  editingName.value = "";
  Object.assign(form, { customer: "", transaction_date: todayStr(), delivery_date: deliveryDefault(), po_number: "", billing_address: "", billing_address_name: "", shipping_address: "", shipping_address_name: "", set_warehouse: "", terms: "", currency: "INR", exchange_rate: 1 });
  customerAddresses.value = [];
  lines.value = [blankLine()];
  Object.assign(collapsed, { details: false, lines: false, notes: true });
  fetchCustomers(""); fetchItems(""); fetchWarehouses("");
  drawerOpen.value = true;
}
async function openEdit(o) {
  editingName.value = o.name;
  Object.assign(form, {
    customer: o.customer || "", transaction_date: o.transaction_date || todayStr(),
    delivery_date: o.delivery_date || deliveryDefault(), po_number: o.po_number || "",
    billing_address: "", billing_address_name: "",
    shipping_address: "", shipping_address_name: "",
    set_warehouse: "", terms: o.terms || "",
    currency: o.currency || "INR", exchange_rate: o.exchange_rate || 1,
  });
  lines.value = [blankLine()];
  Object.assign(collapsed, { details: false, lines: false, notes: true });
  fetchCustomers(""); fetchItems(""); fetchWarehouses("");
  drawerOpen.value = true;
  try {
    const doc = await apiGet("Sales Order", o.name);
    if (doc?.items?.length) {
      lines.value = doc.items.map(i => ({
        id: _id++, item_code: i.item_code || "", description: i.description || "",
        qty: i.qty || 1, rate: i.rate || 0, amount: i.amount || 0,
        uom: i.uom || "Nos",
        discount_percentage: flt(i.discount_percentage) || 0,
        discount_amount: flt(i.discount_amount) || 0,
        tax_code: i.tax_code || "", collapsed: false, available_stock: null,
      }));
      if (doc?.set_warehouse) {
        for (const l of lines.value) fetchStockForLine(l);
      }
    }
    if (doc?.terms) form.terms = doc.terms;
    if (doc?.currency) { form.currency = doc.currency; form.exchange_rate = doc.exchange_rate || 1; }
    if (doc?.billing_address)  form.billing_address  = doc.billing_address;
    if (doc?.shipping_address) form.shipping_address = doc.shipping_address;
    if (doc?.billing_address_name || doc?.shipping_address_name) {
      await fetchCustomerAddresses(doc.customer || o.customer);
      if (doc.billing_address_name) {
        form.billing_address_name = doc.billing_address_name;
        const a = customerAddresses.value.find(x => x.name === doc.billing_address_name);
        if (a) form.billing_address = formatAddress(a);
      }
      if (doc.shipping_address_name) {
        form.shipping_address_name = doc.shipping_address_name;
        const a = customerAddresses.value.find(x => x.name === doc.shipping_address_name);
        if (a) form.shipping_address = formatAddress(a);
      }
    } else if (o.customer) {
      await fetchCustomerAddresses(o.customer);
    }
    if (doc?.set_warehouse) form.set_warehouse = doc.set_warehouse;
  } catch {}
}
async function openView(o) {
  viewDoc.value = o;
  viewOpen.value = true;
  viewTab.value = "details";
  viewLoading.value = true;
  viewItems.value = [];
  fulfill.lines = []; fulfill.computed_status = "";
  links.sales_invoices = []; links.delivery_challans = [];
  try {
    const [doc, ful, lnk] = await Promise.all([
      apiGet("Sales Order", o.name),
      apiGET("zoho_books_clone.api.docs.get_sales_order_fulfillment", { sales_order: o.name }).catch(() => null),
      apiGET("zoho_books_clone.api.docs.get_sales_order_links", { sales_order: o.name }).catch(() => null),
    ]);
    viewItems.value = doc?.items || [];
    viewDoc.value = { ...o, ...doc };
    if (ful) { fulfill.lines = ful.lines || []; fulfill.computed_status = ful.computed_status || ""; }
    if (lnk) { links.sales_invoices = lnk.sales_invoices || []; }
  } catch (e) {
    toast.error(e.message || "Failed to load Sales Order details");
  }
  viewLoading.value = false;
}

async function fetchCustomers(q = "") {
  try {
    const f = [["disabled", "=", 0]];
    if (q) f.push(["customer_name", "like", "%" + q + "%"]);
    const r = await apiList("Customer", { fields: ["name", "customer_name"], filters: f, limit: 30, order: "customer_name asc" });
    customers.value = r.map(x => ({ ...x, label: x.customer_name || x.name, value: x.name }));
  } catch { customers.value = []; }
}

async function onCustomerChange() {
  form.billing_address = ""; form.billing_address_name = "";
  form.shipping_address = ""; form.shipping_address_name = "";
  if (!form.customer) { customerAddresses.value = []; return; }
  addressLoading.value = true;
  try {
    const [, custDoc] = await Promise.all([
      fetchCustomerAddresses(form.customer),
      apiGet("Customer", form.customer).catch(() => null),
    ]);
    const firstBilling = customerAddresses.value.find(a => a.address_type === "Billing") || customerAddresses.value[0];
    if (firstBilling) { form.billing_address_name = firstBilling.name; form.billing_address = formatAddress(firstBilling); }
    const firstShipping = customerAddresses.value.find(a => a.address_type === "Shipping");
    if (firstShipping) { form.shipping_address_name = firstShipping.name; form.shipping_address = formatAddress(firstShipping); }
    if (custDoc?.default_currency) {
      form.currency = custDoc.default_currency;
      form.exchange_rate = form.currency !== "INR" ? (await fetchRate(form.currency, "INR") || 1) : 1;
    }
  } catch {}
  addressLoading.value = false;
}

async function fetchCustomerAddresses(customer) {
  if (!customer) { customerAddresses.value = []; return; }
  try {
    const links = await apiList("Dynamic Link", {
      fields: ["parent"], filters: [["link_doctype","=","Customer"],["link_name","=",customer],["parenttype","=","Address"]], limit: 50
    });
    if (!links?.length) { customerAddresses.value = []; return; }
    const names = links.map(l => l.parent).filter(Boolean);
    const addrs = await Promise.all(names.map(n => apiGet("Address", n).catch(() => null)));
    customerAddresses.value = addrs.filter(Boolean).map(a => {
      const rawTitle = a.address_title || a.name || "";
      const escaped  = customer.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const cleaned  = rawTitle.replace(new RegExp("^" + escaped + "[-\\s]*", "i"), "").trim() || rawTitle;
      const title    = cleaned || a.address_type || "Address";
      return { ...a, label: `${title}${a.city ? " — " + a.city : ""}${a.address_type ? " (" + a.address_type + ")" : ""}` };
    });
  } catch { customerAddresses.value = []; }
}
function formatAddress(a) {
  if (!a) return "";
  return [a.address_line1, a.address_line2, a.city, a.state, a.pincode, a.country].filter(Boolean).join("\n");
}
function displayAddr(text) {
  if (!text) return "";
  return text.includes("\n") ? text : text.split(", ").join("\n");
}
function onBillingAddrSelect(opt) {
  form.billing_address = opt ? formatAddress(opt) : "";
}
function onShippingAddrSelect(opt) {
  form.shipping_address = opt ? formatAddress(opt) : "";
}
function openAddrModal(field) {
  Object.assign(addrModal, { open: true, saving: false, forField: field, address_title: "", address_type: field === "billing" ? "Billing" : "Shipping", address_line1: "", address_line2: "", city: "", state: "", pincode: "", country: "India" });
}
async function saveNewAddress() {
  if (!addrModal.address_title.trim()) return toast.error("Address Title is required");
  if (!addrModal.address_line1.trim()) return toast.error("Address Line 1 is required");
  addrModal.saving = true;
  try {
    const doc = {
      doctype: "Address",
      address_title: addrModal.address_title, address_type: addrModal.address_type,
      address_line1: addrModal.address_line1, address_line2: addrModal.address_line2 || "",
      city: addrModal.city || "", state: addrModal.state || "",
      pincode: addrModal.pincode || "", country: addrModal.country || "India",
      links: form.customer ? [{ doctype: "Address", link_doctype: "Customer", link_name: form.customer }] : [],
    };
    const saved = await apiSave(doc);
    toast.success("Address saved");
    await fetchCustomerAddresses(form.customer);
    const newAddr = customerAddresses.value.find(a => a.name === saved?.name) || customerAddresses.value[customerAddresses.value.length - 1];
    if (newAddr) {
      if (addrModal.forField === "billing") {
        form.billing_address_name = newAddr.name; form.billing_address = formatAddress(newAddr);
      } else {
        form.shipping_address_name = newAddr.name; form.shipping_address = formatAddress(newAddr);
      }
    }
    addrModal.open = false;
  } catch (e) { toast.error(e.message || "Failed to save address"); }
  addrModal.saving = false;
}
async function fetchItems(q = "") {
  try {
    const f = [["disabled", "=", 0], ["is_sales_item", "=", 1]];
    if (q) f.push(["item_name", "like", "%" + q + "%"]);
    const r = await apiList("Item", { fields: ["name", "item_name", "standard_rate", "stock_uom", "description"], filters: [...f, ["has_variants", "=", 0]], limit: 30, order: "item_name asc" });
    items.value = r.map(x => ({ ...x, label: x.item_name || x.name, value: x.name, rate: x.standard_rate || 0, uom: x.stock_uom || "Nos", description: x.description || "" }));
  } catch { items.value = []; }
}
async function onItemSelect(line, opt) {
  const code = opt?.value ?? opt;
  line.item_code = code;
  const found = items.value.find(i => i.name === code || i.value === code);
  if (found) {
    line.rate = flt(found.standard_rate ?? found.rate);
    if (found.description) line.description = found.description;
    if (found.tax_code !== undefined) line.tax_code = found.tax_code || "";
    line.uom = found.uom || found.stock_uom || "Nos";
    calcLine(line);
  }
  if (code) {
    try {
      const doc = await apiGet("Item", code);
      if (doc?.description)  line.description = doc.description;
      if (doc?.tax_code)     line.tax_code    = doc.tax_code;
      if (doc?.stock_uom)    line.uom         = doc.stock_uom;
      if (!found) line.rate = flt(doc.standard_rate || 0);
      calcLine(line);
    } catch {}
    fetchStockForLine(line);
  }
}
function addLine() { lines.value.push(blankLine()); }
function removeLine(id) { if (lines.value.length > 1) lines.value = lines.value.filter(l => l.id !== id); }
function calcLine(l) {
  if (l.discount_percentage > 100) l.discount_percentage = 100;
  if (l.discount_percentage < 0)   l.discount_percentage = 0;
  const base = flt(l.qty) * flt(l.rate);
  const disc = Math.round(base * flt(l.discount_percentage) / 100 * 100) / 100;
  l.discount_amount = disc;
  l.amount = Math.round((base - disc) * 100) / 100;
}
// Pure, side-effect-free version of the same math, used directly in the
// template/totals so displayed figures are always derived live from the
// current qty/rate/discount_percentage on every render — they never depend
// on calcLine() having already run for the exact keystroke that changed them.
function lineAmount(l) {
  const base = flt(l.qty) * flt(l.rate);
  const pct = Math.min(100, Math.max(0, flt(l.discount_percentage)));
  const disc = Math.round(base * pct / 100 * 100) / 100;
  return Math.round((base - disc) * 100) / 100;
}

async function fetchStockForLine(line) {
  if (!line.item_code || !form.set_warehouse) { line.available_stock = null; return; }
  try {
    const r = await apiList("Bin", {
      filters: [["item_code", "=", line.item_code], ["warehouse", "=", form.set_warehouse]],
      fields: ["actual_qty"], limit: 1,
    });
    line.available_stock = r?.length ? flt(r[0].actual_qty) : 0;
  } catch { line.available_stock = null; }
}

async function saveSO(newStatus) {
  if (!(editingName.value ? canEdit("invoices") : canCreate("invoices"))) return toast.error("Read-only access");
  if (!form.customer) return toast.error("Customer is required");
  if (!lines.value.some(l => l.item_code && flt(l.qty) > 0)) return toast.error("At least one item required");
  if (!form.set_warehouse) return toast.error("Dispatch Warehouse is required");
  if (lines.value.some(l => (l.description||'').length > 500)) return toast.error("Item description cannot exceed 500 characters");
  if ((form.terms||'').length > 500) return toast.error("Terms & Conditions cannot exceed 500 characters");
  drawerSaving.value = true;
  try {
    const company = await resolveCompany();
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
          doctype: "Tax Line", charge_type: "On Net Total",
          account_head: tmpl.account || taxAccountHead.value,
          description: l.tax_code, rate: tmpl.rate, tax_type,
        };
      }
    }
    const taxes = Object.values(taxMap);
    const doc = {
      doctype: "Sales Order", company,
      customer: form.customer, transaction_date: form.transaction_date,
      delivery_date: form.delivery_date || null,
      po_number: form.po_number || "",
      billing_address: form.billing_address || "", billing_address_name: form.billing_address_name || "",
      shipping_address: form.shipping_address || "", shipping_address_name: form.shipping_address_name || "",
      set_warehouse: form.set_warehouse || "",
      status: newStatus || "Draft",
      // Sales Order is is_submittable=0 — docstatus is never settable here
      // and Frappe silently drops it; status is the only confirm signal.
      terms: form.terms || "",
      currency: form.currency || "INR",
      exchange_rate: form.currency === "INR" ? 1 : (form.exchange_rate || 1),
      items: lines.value.filter(l => l.item_code).map(l => { calcLine(l); return {
        doctype: "Sales Order Item", item_code: l.item_code,
        description: l.description || l.item_code,
        qty: flt(l.qty) || 1, rate: flt(l.rate), amount: flt(l.amount),
        uom: l.uom || "Nos",
        discount_percentage: flt(l.discount_percentage) || 0,
        discount_amount: flt(l.discount_amount) || 0,
        tax_code: l.tax_code || "",
      }; }),
      taxes,
    };
    if (editingName.value) doc.name = editingName.value;
    const saved = await apiSave(doc);
    const msg = newStatus === "Draft" ? "saved as Draft" : "confirmed";
    toast.success(`Sales Order ${saved?.name || ""} ${msg}`);
    drawerOpen.value = false;
    await load();
  } catch (e) { toast.error(e.message || "Failed to save order"); }
  finally { drawerSaving.value = false; }
}

// ── Actions ───────────────────────────────────────────────────────────────
async function emailSO(o) {
  await openEmail({
    doctype: "Sales Order", name: o.name, docLabel: `Sales Order ${o.name}`,
    getDefaultsEndpoint: "zoho_books_clone.api.docs.get_sales_order_email_defaults",
    sendEndpoint: "zoho_books_clone.api.docs.send_sales_order_email",
    paramKey: "sales_order",
    printConfig: { title: "SALES ORDER", partyLabel: "Customer", partyField: "customer_name" },
  });
}


function onInvBatchSelect(line, opt) {
  line.batch_no = opt?.value ?? opt;
}
// Delivery Note batches are scoped to the SO's dispatch warehouse (not the
// item globally) — a batch with zero stock in that warehouse would let the
// user pick it here but fail downstream when the auto Stock Entry tries to
// issue from it. get_warehouse_batches returns qty per item for a single
// warehouse in one call, so this fetches once per modal-open rather than
// once per line.
//
// EXCEPTION: if this SO line was already delivered under a batch (an
// earlier partial Delivery Note against the same row — see
// get_sales_order_fulfillment's delivered_batches), a later delivery of
// the remaining qty should stick to that SAME batch rather than let the
// user pick a different one from the whole warehouse — a split delivery
// across batches for one SO line is confusing for traceability and for
// the invoice, which now sources its own batch options from what was
// actually delivered. So those lines skip the warehouse-wide fetch and
// use delivered_batches directly (auto-filled when there's just one).
async function fetchModalBatches(warehouse, lines) {
  const batchLines = lines.filter(l => l.has_batch_no);
  const alreadyDelivered = batchLines.filter(l => Array.isArray(l.delivered_batches) && l.delivered_batches.length);
  const needsFetch = batchLines.filter(l => !(Array.isArray(l.delivered_batches) && l.delivered_batches.length));

  for (const l of alreadyDelivered) {
    l.batchOptions = l.delivered_batches.map(b => ({ value: b.batch_no, label: `${b.batch_no} (delivered:${flt(b.qty)})` }));
    if (l.delivered_batches.length === 1) l.batch_no = l.delivered_batches[0].batch_no;
  }

  if (!warehouse || !needsFetch.length) {
    needsFetch.forEach(l => { l.batchOptions = []; });
    return;
  }
  try {
    const byItem = await apiGET("zoho_books_clone.api.inventory.get_warehouse_batches", { warehouse }) || {};
    for (const l of needsFetch) {
      const rows = byItem[l.item_code] || [];
      l.batchOptions = rows.map(b => ({ value: b.batch_no, label: `${b.batch_no} (qty:${flt(b.qty)})` }));
    }
  } catch {
    needsFetch.forEach(l => { l.batchOptions = []; });
  }
}
function onDeliverBatchSelect(line, opt) {
  line.batch_no = opt?.value ?? opt;
}
function openInvoiceModal(o) {
  apiGET("zoho_books_clone.api.docs.get_sales_order_fulfillment", { sales_order: o.name })
    .then(async (r) => {
      const ful = r?.lines || [];
      const pending = ful.filter(l => l.remaining_to_bill > 0)
                        .map(l => ({
                          ...l,
                          toInvoice: (r.warehouse && l.warehouse_qty !== undefined) ? Math.max(0, Math.min(l.remaining_to_bill, l.warehouse_qty)) : l.remaining_to_bill,
                          batch_no: "",
                          batchOptions: []
                        }));
      Object.assign(invModal, {
        open: true, saving: false, soName: o.name,
        warehouse: r?.warehouse || "",
        allLines: ful,
        lines: pending,
        dueDate: o.delivery_date || todayStr(),
      });
      if (!invModal.lines.length) { invModal.open = false; toast.info("Nothing left to invoice"); return; }
      // Load batch options for batch-tracked pending lines. IMPORTANT: iterate
      // invModal.lines (the reactive proxy), not the raw `pending` array —
      // `pending` still points at the plain objects created above, and
      // Vue's reactive() only wraps a value when it's *read* through the
      // proxy. Mutating l.batchOptions on the raw `pending` elements bypasses
      // the proxy's set trap entirely: the fetch succeeds and the data lands
      // in memory, but no reactivity trigger fires, so the dropdown never
      // re-renders. Reading through invModal.lines gives back the proxied
      // (reactive) line objects, so the same mutation is tracked correctly.
      await fetchModalBatches(invModal.warehouse, invModal.lines);
    })
    .catch(e => toast.error(e.message || "Failed to load fulfillment"));
}
async function submitInvoice() {
  if (!canCreate("invoices")) { toast.error("Read-only access"); return; }
  const lineMap = {};
  const batchMap = {};
  const insufficientItems = [];
  for (const l of invModal.lines) {
    const qty = flt(l.toInvoice);
    if (qty > 0) {
      lineMap[l.name] = qty;
      if (l.has_batch_no && l.batch_no) batchMap[l.name] = l.batch_no;
      if (l.warehouse_qty !== undefined && qty > flt(l.warehouse_qty)) {
        insufficientItems.push(`- ${l.item_code} (Req: ${qty}, Avail: ${flt(l.warehouse_qty)})`);
      }
    }
  }
  if (!Object.keys(lineMap).length) { toast.error("Enter at least one qty to invoice"); return; }
  
  if (insufficientItems.length > 0 && invModal.warehouse) {
    const msg = `The following items have insufficient stock in warehouse ${invModal.warehouse}:\n\n${insufficientItems.join('\n')}\n\nDo you want to proceed anyway?`;
    if (!await confirm({ title: "Insufficient Stock", body: msg, okLabel: "Proceed", okStyle: "danger" })) {
      return;
    }
  }

  invModal.saving = true;
  try {
    const r = await apiPOST("zoho_books_clone.api.docs.convert_sales_order_to_invoice", {
      sales_order: invModal.soName,
      line_qtys: JSON.stringify(lineMap),
      batch_nos: JSON.stringify(batchMap),
      due_date: invModal.dueDate || "",
    });
    toast.success(`Invoice created: ${r?.sales_invoice}`);
    invModal.open = false;
    await load();
    if (viewDoc.value?.name === invModal.soName) await openView(viewDoc.value);
  } catch (e) { toast.error(e.message || "Convert failed"); }
  invModal.saving = false;
}

function openDeliverModal(o) {
  apiGET("zoho_books_clone.api.docs.get_sales_order_fulfillment", { sales_order: o.name })
    .then(async (r) => {
      const ful = r?.lines || [];
      const pending = ful.filter(l => l.remaining_to_deliver > 0)
                        .map(l => ({
                          ...l,
                          toDeliver: (r.warehouse && l.warehouse_qty !== undefined) ? Math.max(0, Math.min(l.remaining_to_deliver, l.warehouse_qty)) : l.remaining_to_deliver,
                          batch_no: "",
                          batchOptions: []
                        }));
      Object.assign(deliverModal, {
        open: true, saving: false, soName: o.name,
        warehouse: r?.warehouse || "",
        allLines: ful,
        lines: pending,
        lrNo: "", transporterName: "",
      });
      if (!deliverModal.lines.length) { deliverModal.open = false; toast.info("Nothing left to deliver"); return; }
      // Same reactivity gotcha as openInvoiceModal above — pass
      // deliverModal.lines (the reactive proxy), not the raw `pending`
      // array, so batchOptions mutations actually trigger a re-render.
      await fetchModalBatches(deliverModal.warehouse, deliverModal.lines);
    })
    .catch(e => toast.error(e.message || "Failed to load fulfillment"));
}
async function submitDeliver() {
  if (!canCreate("invoices")) { toast.error("Read-only access"); return; }
  const lineMap = {};
  const batchMap = {};
  const insufficientItems = [];
  for (const l of deliverModal.lines) {
    const qty = flt(l.toDeliver);
    if (qty > 0) {
      lineMap[l.name] = qty;
      if (l.has_batch_no && l.batch_no) batchMap[l.name] = l.batch_no;
      if (l.warehouse_qty !== undefined && qty > flt(l.warehouse_qty)) {
        insufficientItems.push(`- ${l.item_code} (Req: ${qty}, Avail: ${flt(l.warehouse_qty)})`);
      }
    }
  }
  if (!Object.keys(lineMap).length) { toast.error("Enter at least one qty to deliver"); return; }
  const missingBatch = deliverModal.lines.find(l => flt(l.toDeliver) > 0 && l.has_batch_no && !l.batch_no);
  if (missingBatch) { toast.error(`Select a Batch No for ${missingBatch.item_name || missingBatch.item_code}`); return; }

  if (insufficientItems.length > 0 && deliverModal.warehouse) {
    const msg = `The following items have insufficient stock in warehouse ${deliverModal.warehouse}:\n\n${insufficientItems.join('\n')}\n\nDo you want to proceed anyway?`;
    if (!await confirm({ title: "Insufficient Stock", body: msg, okLabel: "Proceed", okStyle: "danger" })) {
      return;
    }
  }

  deliverModal.saving = true;
  try {
    const r = await apiPOST("zoho_books_clone.api.docs.create_delivery_note_from_so", {
      sales_order: deliverModal.soName,
      line_qtys: JSON.stringify(lineMap),
      batch_nos: JSON.stringify(batchMap),
      lr_no: deliverModal.lrNo || "",
      transporter_name: deliverModal.transporterName || "",
    });
    toast.success(`Delivery Note created: ${r?.delivery_note}`);
    deliverModal.open = false;
    await load();
    if (viewDoc.value?.name === deliverModal.soName) await openView(viewDoc.value);
  } catch (e) { toast.error(e.message || "Create Delivery Note failed"); }
  deliverModal.saving = false;
}

async function submitSO(o) {
  if (!canEdit("invoices")) { toast.error("Read-only access"); return; }
  if (!await confirm({ title: "Submit Sales Order", body: `Submit ${o.name}? This will confirm the order and it can no longer be edited.`, okLabel: "Submit" })) return;
  try {
    const submitted = await apiPOST("zoho_books_clone.api.docs.submit_sales_order", { sales_order: o.name });
    toast.success(`Sales Order ${o.name} confirmed`);
    await load();
    await openView({ name: o.name });
  } catch (e) { toast.error(e.message || "Submit failed"); }
}
async function cancelSO(o) {
  if (!canEdit("invoices")) { toast("Read-only access", "error"); return; }
  if (!await confirm({ title: "Cancel Sales Order", body: `Cancel ${o.name}? Linked invoices must be cancelled separately.`, okLabel: "Cancel SO" })) return;
  try {
    await apiPOST("zoho_books_clone.api.docs.cancel_sales_order_safe", { sales_order: o.name });
    toast.success("Sales Order cancelled");
    await load(); if (viewDoc.value?.name === o.name) await openView(o);
  } catch (e) { toast.error(e.message || "Cancel failed"); }
}
async function deleteSO(o) {
  if (!canDeleteModule("invoices")) { toast("Not permitted", "error"); return; }
  if (!await confirm({ title: "Delete Sales Order", body: `Permanently delete ${o.name}?`, okLabel: "Delete" })) return;
  try {
    await apiDelete("Sales Order", o.name);
    toast.success("Sales Order deleted");
    viewOpen.value = false; await load();
  } catch (e) { toast.error(e.message || "Delete failed"); }
}

// ── Bulk actions ──────────────────────────────────────────────────────────
async function bulkDelete() {
  if (!canDeleteModule("invoices")) { toast("Not permitted", "error"); return; }
  const drafts = sorted.value.filter(o => selected.value.has(o.name) && (!o.status || o.status === "Draft"));
  if (!drafts.length) { toast.info("Select drafts to delete"); return; }
  if (!await confirm({ title: "Delete Drafts", body: `Delete ${drafts.length} draft order(s)?`, okLabel: "Delete" })) return;
  for (const o of drafts) { try { await apiDelete("Sales Order", o.name); } catch {} }
  selected.value = new Set();
  toast.success(`Deleted ${drafts.length}`);
  await load();
}
async function bulkEmail() {
  if (!canEdit("invoices")) { toast("Read-only access", "error"); return; }
  const subs = sorted.value.filter(o => selected.value.has(o.name));
  if (!subs.length) { toast.info("No orders selected"); return; }
  let sent = 0;
  for (const o of subs) {
    const ok = await openEmail({
      doctype: "Sales Order", name: o.name, docLabel: `Sales Order ${o.name}`,
      getDefaultsEndpoint: "zoho_books_clone.api.docs.get_sales_order_email_defaults",
      sendEndpoint: "zoho_books_clone.api.docs.send_sales_order_email",
      paramKey: "sales_order",
      printConfig: { title: "SALES ORDER", partyLabel: "Customer", partyField: "customer_name" },
    });
    if (ok) sent++;
  }
  if (sent) toast.success(`Emailed ${sent} order(s)`);
}

function exportCSV() {
  const rows = selected.value.size
    ? sorted.value.filter(o => selected.value.has(o.name))
    : sorted.value;
  if (!rows.length) return;
  const head = ["Order #","Customer","Date","Delivery","Status","PO #","Amount"];
  const esc = v => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const out = [head.map(esc).join(",")];
  for (const o of rows) {
    out.push([o.name, o.customer_name || o.customer, o.transaction_date, o.delivery_date || "",
      o.status || "Draft", o.po_number || "", Number(o.grand_total || 0).toFixed(2)].map(esc).join(","));
  }
  const blob = new Blob(["﻿" + out.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `sales_orders_${todayStr()}.csv`;
  a.click(); URL.revokeObjectURL(url);
  toast.success(`CSV exported — ${rows.length} order(s)`);
}

watch(() => form.set_warehouse, () => {
  for (const l of lines.value) fetchStockForLine(l);
});

onMounted(async () => { setCompany(window.__booksCompany || "");
  document.addEventListener('click', onDocClickForDownloadMenu);
  await load();
  loadTaxAccount();
  apiList("UOM", { fields: ["name"], order: "name asc", limit: 200 })
    .then(r => { if (r && r.length) uomList.value = r.map(u => u.name); })
    .catch(() => {});
  useOpenFromQuery({
    route,
    openByName: (n) => openView(list.value.find(x => x.name === n) || { name: n }),
  });
});
onUnmounted(() => document.removeEventListener('click', onDocClickForDownloadMenu));
</script>

<style>
@import '../styles/list.css';
@import '../styles/view.css';
@import '../styles/edit.css';
@import '../styles/add.css';

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
.inv-dl-menu-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.inv-dl-menu-label {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
  white-space: nowrap;
}
.inv-dl-menu-sub {
  font-size: 11px;
  color: #9ca3af;
  white-space: nowrap;
}
.inv-ab-caret { font-size: 10px; opacity: .6; margin-left: 1px; }

@media (max-width: 480px) {
  .view-toggle-btn { display: none !important; }
}
</style>

<style scoped>
.inv-ci-grid {
  display: grid;
  grid-template-columns: minmax(0,1fr) minmax(0,1fr) 100px 110px;
  gap: 10px;
  padding: 8px 14px;
  align-items: center;
}
.inv-ci-grid-batch {
  grid-template-columns: minmax(0,1fr) minmax(0,1fr) 90px 100px 150px;
}
.inv-ci-header {
  background: #f8fafc;
  font-size: 11px;
  font-weight: 700;
  color: #9ca3af;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  border-bottom: 1px solid #e8ecf0;
}
.inv-ci-row {
  border-top: 1px solid #f3f4f6;
  font-size: 12.5px;
}
.inv-ci-done {
  background: #f9fafb;
  opacity: 0.8;
}
.inv-ci-done-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: #d1fae5;
  color: #065f46;
  font-size: 10.5px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 12px;
  white-space: nowrap;
}
.inv-create-btn {
  background: linear-gradient(135deg, #1a6ef7 0%, #1558d6 100%);
  color: #fff;
  border: 1px solid #1558d6;
  border-radius: 8px;
  padding: 9px 20px;
  font-size: 13.5px;
  font-weight: 700;
  gap: 7px;
  box-shadow: 0 2px 8px rgba(26,110,247,0.25);
  transition: box-shadow 0.15s, transform 0.1s;
  letter-spacing: 0.01em;
}
.inv-create-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #155fd4 0%, #1047b8 100%);
  box-shadow: 0 4px 16px rgba(26,110,247,0.35);
  transform: translateY(-1px);
}
.inv-create-btn:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 1px 4px rgba(26,110,247,0.2);
}
.inv-create-btn:disabled {
  background: #93aef5;
  border-color: #93aef5;
  box-shadow: none;
}
.inv-create-spinner {
  display: inline-block;
  width: 13px;
  height: 13px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: inv-spin 0.7s linear infinite;
  flex-shrink: 0;
}
@keyframes inv-spin { to { transform: rotate(360deg); } }

.so-stock-badge {
  display: inline-flex;
  align-items: center;
  margin-top: 6px;
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 6px;
  min-width: 60px;
}
.so-stock-ok   { background: #d1fae5; color: #065f46; }
.so-stock-zero { background: #fee2e2; color: #991b1b; }
.so-stock-na   { background: #f3f4f6; color: #9ca3af; }

/* ── Mobile card view (Option A) ── */
.so-mobile-cards { display: none; }
.so-desktop-table { display: table; }

@media (max-width: 768px) {
  .so-desktop-table { display: none !important; }
  .so-mobile-cards { display: flex; flex-direction: column; gap: 0; background: #f8fafc; }
  .so-mobile-card { background: #fff; border-bottom: 1px solid #e5e7eb; padding: 12px 14px; cursor: pointer; transition: background .12s; }
  .so-mobile-card:active { background: #f8f9fc; }
  .so-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .so-mc-docno { font-size: 12px; font-weight: 700; color: #2563eb; }
  .so-mc-mid { font-size: 13.5px; font-weight: 600; color: #1a1d23; margin-bottom: 4px; }
  .so-mc-meta { display: flex; justify-content: space-between; font-size: 12px; color: #868e96; margin-bottom: 4px; }
  .so-mc-amount { font-weight: 700; color: #1a1d23; }
  .so-mc-sub { font-size: 11.5px; color: #868e96; margin-bottom: 8px; }
  .so-mc-footer { display: flex; gap: 6px; margin-top: 8px; }
  .so-mc-btn { flex: 1; padding: 6px 10px; border-radius: 7px; font-size: 12px; font-weight: 600; cursor: pointer; background: #f1f5f9; border: 1px solid #e2e8f0; color: #374151; }
  .so-mc-danger { background: #fff1f2; border-color: #fecaca; color: #dc2626; }
  .so-mc--skeleton { pointer-events: none; }
  .so-mc-shimmer { border-radius: 6px; background: linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size: 200% 100%; animation: so-shimmer 1.4s infinite; }
  @keyframes so-shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
  .so-mc-empty { text-align: center; padding: 32px 16px; color: #868e96; font-size: 13px; }
}
</style>