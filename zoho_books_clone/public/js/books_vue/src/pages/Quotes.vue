<template>
<div class="inv-page">

  <!-- ── Unified toolbar ── -->
  <div class="sales-toolbar">
    <div class="sales-search">
      <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
      <input v-model="search" placeholder="Search quotes, customers…" class="sales-search-input"/>
    </div>
    <div class="sales-pills">
      <button v-for="t in tabs" :key="t.key" class="sales-pill" :class="{active:activeTab===t.key, ['pill-'+t.key]: t.key!=='all'}" @click="activeTab=t.key">
        {{ t.label }}<span v-if="t.key!=='all'" class="sales-pill-count">{{ counts[t.key] }}</span>
      </button>
    </div>
    <div class="sales-actions">
      <select v-model="filterCustomer" class="sales-select" title="Filter by customer">
        <option value="">All Customers</option>
        <option v-for="c in customers" :key="c.name" :value="c.name">{{ c.customer_name || c.label }}</option>
      </select>
      <button class="sales-btn-ghost view-toggle-btn" @click="viewMode=viewMode==='table'?'grid':'table'" :title="viewMode==='table'?'Grid View':'List View'"><span v-html="icon(viewMode==='table'?'grid':'file',14)"></span></button>
      <button class="sales-btn-ghost" @click="exportCSV" title="Export CSV"><span v-html="icon('download',14)"></span> CSV</button>
      <button class="sales-btn-ghost" @click="load" title="Refresh" :disabled="loading"><span v-html="icon('refresh',14)"></span></button>
      <button class="sales-btn-primary" @click="openNew" :disabled="!$canWrite('invoices')" :title="!$canWrite('invoices') ? 'Read-only access' : ''">
        <span v-html="icon('plus',13)"></span> New Quotation
      </button>
    </div>
  </div>

  <!-- ── KPI Cards ── -->
  <div class="bk-kpi-grid">
    <div class="bk-kpi-card bk-kpi-accent clickable" @click="activeTab='all'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#dbeafe">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.7"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
        </div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Total Quotes</div>
          <div class="bk-kpi-value">{{ list.length }}</div>
          <div class="bk-kpi-trend" :class="qtTrends.total.up?'bk-trend-up':'bk-trend-down'">{{ qtTrends.total.up?'↑':'↓' }} {{ qtTrends.total.pct }}% vs last month</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card clickable" @click="activeTab='draft'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#e2e8f0">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="1.7"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
        </div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Draft</div>
          <div class="bk-kpi-value">{{ counts.draft }}</div>
          <div class="bk-kpi-trend" :class="qtTrends.draft.up?'bk-trend-up':'bk-trend-down'">{{ qtTrends.draft.up?'↑':'↓' }} {{ qtTrends.draft.pct }}% vs last month</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card clickable" @click="activeTab='sent'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#cffafe">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#0891b2" stroke-width="1.7"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        </div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Sent</div>
          <div class="bk-kpi-value" style="color:#0891b2">{{ counts.sent }}</div>
          <div class="bk-kpi-trend" :class="qtTrends.sent.up?'bk-trend-up':'bk-trend-down'">{{ qtTrends.sent.up?'↑':'↓' }} {{ qtTrends.sent.pct }}% vs last month</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card bk-kpi-success clickable" @click="activeTab='converted'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#dcfce7">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="1.7"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>
        </div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Converted</div>
          <div class="bk-kpi-value bk-kpi-green">{{ counts.converted }}</div>
          <div class="bk-kpi-trend" :class="qtTrends.converted.up?'bk-trend-up':'bk-trend-down'">{{ qtTrends.converted.up?'↑':'↓' }} {{ qtTrends.converted.pct }}% vs last month</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card bk-kpi-warn clickable" @click="activeTab='expired'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#fef3c7">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="1.7"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        </div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Expired</div>
          <div class="bk-kpi-value bk-kpi-amber">{{ counts.expired }}</div>
          <div class="bk-kpi-trend" :class="qtTrends.expired.up?'bk-trend-down':'bk-trend-up'">{{ qtTrends.expired.up?'↑':'↓' }} {{ qtTrends.expired.pct }}% vs last month</div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── Secondary Stat Cards ── -->
  <div class="bk-stat-grid">
    <div class="bk-stat-card">
      <div class="bk-stat-content">
        <div>
          <div class="bk-stat-label">This Month</div>
          <div class="bk-stat-value">{{ thisMonthQuotes }}</div>
        </div>
        <div class="bk-stat-icon" style="background:#dbeafe;color:#2563eb">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
        </div>
      </div>
    </div>
    <div class="bk-stat-card">
      <div class="bk-stat-content">
        <div>
          <div class="bk-stat-label">Conversion Rate</div>
          <div class="bk-stat-value" style="color:#16a34a">{{ conversionRate }}</div>
        </div>
        <div class="bk-stat-icon" style="background:#dcfce7;color:#16a34a">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>
        </div>
      </div>
    </div>
    <div class="bk-stat-card">
      <div class="bk-stat-content">
        <div>
          <div class="bk-stat-label">Avg Quote Value</div>
          <div class="bk-stat-value" style="font-size:16px">{{ fmtCur(avgQuoteValue) }}</div>
        </div>
        <div class="bk-stat-icon" style="background:#e5e7eb;color:#6b7280">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
        </div>
      </div>
    </div>
    <div class="bk-stat-card">
      <div class="bk-stat-content">
        <div>
          <div class="bk-stat-label">Awaiting Reply</div>
          <div class="bk-stat-value" style="color:#0891b2">{{ counts.sent }}</div>
        </div>
        <div class="bk-stat-icon" style="background:#cffafe;color:#0891b2">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        </div>
      </div>
    </div>
  </div>

  <!-- ── Bulk actions bar ── -->
  <div v-if="selected.size>0" class="inv-bulk-bar">
    <span class="inv-bulk-count">{{ selected.size }} selected</span>
    <button class="inv-bulk-btn" @click="bulkEmail"><span v-html="icon('mail',13)"></span> Send Email</button>
    <button class="inv-bulk-btn" @click="bulkMarkSent">Mark as Sent</button>
    <button class="inv-bulk-btn" @click="bulkMarkExpired">Mark Expired</button>
    <button class="inv-bulk-btn inv-bulk-danger" @click="bulkDelete">Delete Drafts</button>
    <button class="inv-bulk-btn" @click="exportCSV"><span v-html="icon('download',13)"></span> Export CSV</button>
    <button class="inv-bulk-clear" @click="selected=new Set()">✕ Clear</button>
  </div>

  <!-- ── Table ── -->
  <div class="inv-table-wrap">
    <template v-if="viewMode==='table'">
    <table class="inv-table qt-desktop-table">
      <thead><tr>
        <th class="th-check"><input type="checkbox" @change="toggleAll" :checked="allChecked"/></th>
        <th class="sortable" @click="sortBy('transaction_date')">DATE <span class="sort-arrow">{{ sortArrowTxt('transaction_date') }}</span></th>
        <th class="sortable" @click="sortBy('name')">QUOTE # <span class="sort-arrow">{{ sortArrowTxt('name') }}</span></th>
        <th class="sortable" @click="sortBy('customer_name')">CUSTOMER <span class="sort-arrow">{{ sortArrowTxt('customer_name') }}</span></th>
        <th class="sortable" @click="sortBy('valid_till')">VALID TILL <span class="sort-arrow">{{ sortArrowTxt('valid_till') }}</span></th>
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
          <tr v-for="q in paged" :key="q.name" class="inv-row" :class="{selected:selected.has(q.name)}">
            <td class="td-check" @click.stop>
              <input type="checkbox" :checked="selected.has(q.name)" @change="toggle(q.name)"/>
            </td>
            <td @click="openView(q)" class="text-muted mono-sm">{{ fmtDate(q.transaction_date) }}</td>
            <td @click="openView(q)"><DocLink doctype="Quotation" :name="q.name" /></td>
            <td @click="openView(q)"><span class="inv-customer">{{ q.customer_name || q.customer || '—' }}</span></td>
            <td @click="openView(q)" :class="isExpired(q)?'text-danger':'text-muted'" class="mono-sm">{{ fmtDate(q.valid_till) || '—' }}</td>
            <td @click="openView(q)">
              <span class="inv-status-badge" :class="badgeClass(q)">{{ displayStatus(q) }}</span>
            </td>
            <td class="ta-r mono-sm" @click="openView(q)">{{ fmtCur(q.grand_total) }}</td>
            <td style="text-align:center" @click.stop>
              <div style="display:flex;gap:4px;justify-content:center">
                <button class="inv-act-btn" @click="openView(q)" title="View"><span v-html="icon('eye',13)"></span></button>
                <button v-if="q.docstatus===0" class="inv-act-btn" @click="openEdit(q)" title="Edit"><span v-html="icon('edit',13)"></span></button>
                <button v-if="canConvert(q)" class="inv-act-btn inv-act-pay" @click="openConvertModal(q)" title="Convert to Invoice / SO"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></button>
                <button v-if="q.docstatus!==1" class="inv-act-btn" style="color:#dc2626" @click.stop="deleteQT(q)" title="Delete"><span v-html="icon('trash',13)"></span></button>
              </div>
            </td>
          </tr>
          <tr v-if="!sorted.length">
            <td colspan="8" class="bk-empty-state">
              <div class="bk-empty-inner">
                <template v-if="search || filterCustomer">
                  <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.3"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                  <p class="bk-empty-title">No quotations match your filters</p>
                </template>
                <template v-else>
                  <div class="bk-empty-illus">
                    <svg width="80" height="96" viewBox="0 0 80 96" fill="none">
                      <rect x="10" y="8" width="60" height="80" rx="6" fill="#e2e8f0"/>
                      <rect x="14" y="12" width="52" height="72" rx="4" fill="#fff"/>
                      <rect x="22" y="26" width="36" height="3" rx="2" fill="#e2e8f0"/>
                      <rect x="22" y="34" width="28" height="3" rx="2" fill="#e2e8f0"/>
                      <rect x="22" y="42" width="32" height="3" rx="2" fill="#e2e8f0"/>
                      <rect x="22" y="58" width="20" height="3" rx="2" fill="#e2e8f0"/>
                      <rect x="22" y="66" width="24" height="3" rx="2" fill="#e2e8f0"/>
                      <rect x="8" y="22" width="20" height="20" rx="4" fill="#2563eb" opacity=".85"/>
                      <line x1="13" y1="32" x2="23" y2="32" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
                      <line x1="18" y1="27" x2="18" y2="37" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                  </div>
                  <p class="bk-empty-title">No quotations created yet</p>
                  <p class="bk-empty-sub">Create your first quotation to start managing customer proposals and track approvals.</p>
                  <button class="bk-empty-btn" @click="openNew">
                    <span v-html="icon('plus',13)"></span> New Quotation
                  </button>
                </template>
              </div>
            </td>
          </tr>
        </template>
      </tbody>
    </table>

    <!-- Mobile cards (shown at ≤768px) -->
    <div class="qt-mobile-cards">
      <template v-if="loading">
        <div v-for="n in 5" :key="n" class="qt-mobile-card qt-mc--skeleton">
          <div class="qt-mc-shimmer" style="height:13px;width:55%;margin-bottom:8px"></div>
          <div class="qt-mc-shimmer" style="height:11px;width:40%;margin-bottom:6px"></div>
          <div class="qt-mc-shimmer" style="height:11px;width:65%"></div>
        </div>
      </template>
      <div v-else-if="!sorted.length" class="qt-mc-empty">
        <div style="font-size:32px;margin-bottom:8px">📋</div>
        <div>No quotations found</div>
      </div>
      <template v-else>
        <div v-for="q in paged" :key="q.name" class="qt-mobile-card" @click="openView(q)">
          <div class="qt-mc-top">
            <span class="qt-mc-docno">{{ q.name }}</span>
            <span class="inv-status-badge" :class="badgeClass(q)">{{ displayStatus(q) }}</span>
          </div>
          <div class="qt-mc-mid">{{ q.customer_name || q.customer || '—' }}</div>
          <div class="qt-mc-meta">
            <span>{{ fmtDate(q.transaction_date) }}</span>
            <span class="qt-mc-amount">{{ fmtCur(q.grand_total) }}</span>
          </div>
          <div v-if="q.valid_till" class="qt-mc-sub" :class="isExpired(q)?'text-danger':''">Valid till: {{ fmtDate(q.valid_till) }}</div>
          <div class="qt-mc-footer">
            <button class="qt-mc-btn" @click.stop="openView(q)">View</button>
            <button v-if="q.docstatus===0" class="qt-mc-btn" @click.stop="openEdit(q)">Edit</button>
            <button v-if="q.docstatus!==1" class="qt-mc-btn qt-mc-danger" @click.stop="deleteQT(q)">Delete</button>
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
          <div style="font-size:32px;margin-bottom:8px">💬</div>
          <div>{{ search ? 'No quotations match your filters' : 'No quotations yet' }}</div>
          <button v-if="!search" class="nim-btn nim-btn-primary" :disabled="!$canWrite('invoices')" :title="!$canWrite('invoices') ? 'Read-only access' : ''" style="margin-top:14px" @click="openNew"><span v-html="icon('plus',13)"></span> New Quotation</button>
        </div>
        <template v-else>
          <div v-for="q in paged" :key="q.name"
            class="b-card b-card-body"
            style="cursor:pointer;padding:16px;display:flex;flex-direction:column;gap:8px"
            @click="openView(q)">
            <div style="display:flex;align-items:center;justify-content:space-between;gap:8px">
              <span style="font-size:12px;font-weight:700;color:#2563eb">{{ q.name }}</span>
              <span class="inv-status-badge" :class="badgeClass(q)">{{ displayStatus(q) }}</span>
            </div>
            <div style="font-size:13.5px;font-weight:600;color:#1a1d23;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ q.customer_name || q.customer || '—' }}</div>
            <div style="display:flex;justify-content:space-between;font-size:12px;color:#6b7280">
              <span>{{ fmtDate(q.transaction_date) }}</span>
              <span style="font-weight:700;color:#1a1d23">{{ fmtCur(q.grand_total) }}</span>
            </div>
            <div v-if="q.valid_till" style="font-size:11.5px;" :class="isExpired(q)?'text-danger':'text-muted'">
              Valid till: {{ fmtDate(q.valid_till) }}
            </div>
            <div style="display:flex;gap:6px;border-top:1px solid #f3f4f6;padding-top:10px">
              <button class="inv-act-btn" @click.stop="openView(q)" title="View"><span v-html="icon('eye',13)"></span></button>
              <button v-if="q.docstatus===0" class="inv-act-btn" @click.stop="openEdit(q)" title="Edit"><span v-html="icon('edit',13)"></span></button>
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
    <div v-if="drawerOpen" class="inv-drawer-bg" @click.self="drawerOpen=false">
      <div class="inv-drawer-panel" :class="{'inv-split':showPreview, 'is-add':!editingName}">

        <!-- Header -->
        <div class="inv-dh">
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
            <div class="inv-dh-title">{{ editingName ? 'Edit Quotation' : 'New Quotation' }}</div>
            <span v-if="!editingName" class="add-status-badge">Draft</span>

          </div>
          <div style="display:flex;align-items:center;gap:8px">
            <button class="inv-preview-toggle" @click="showPreview=!showPreview" :title="showPreview?'Hide preview':'Live preview'">
              <span v-html="icon('eye',13)"></span> {{ showPreview ? 'Hide' : 'Preview' }}
            </button>
            <button class="inv-dclose" @click="drawerOpen=false"><span v-html="icon('x',16)"></span></button>
          </div>
        </div>

        <!-- Content row: form + optional preview -->
        <div class="inv-content-row">
        <div class="inv-dbody">

          <!-- ══ CARD 2: Quote Details ══ -->
          <div class="add-card">
            <div class="add-card-header" @click="collapsed.details=!collapsed.details">
              <div class="add-card-title">
                <span class="add-card-title-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></span>
                Quote Details
              </div>
              <span class="add-card-chevron" :class="{collapsed:collapsed.details}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
              </span>
            </div>
            <div class="add-card-body" :class="{collapsed:collapsed.details}">
              <div class="add-details-grid">
                <div>
                  <label class="inv-lbl">Customer <span class="inv-req">*</span></label>
                  <SearchableSelect v-model="form.customer" :options="customers" placeholder="Select customer"
                    :createable="true" createDoctype="Customer"
                    @search="fetchCustomers" @update:modelValue="onCustomerChange"/>
                </div>
                <div>
                  <label class="inv-lbl">Quote Date <span class="inv-req">*</span></label>
                  <input v-model="form.transaction_date" type="date" class="inv-fi"/>
                </div>
                <div>
                  <label class="inv-lbl">Valid Till</label>
                  <input v-model="form.valid_till" type="date" class="inv-fi"/>
                </div>
              </div>
              <div class="add-details-row2">
                <div>
                  <label class="inv-lbl">Title / Project</label>
                  <input v-model="form.title" type="text" class="inv-fi" placeholder="Project name or short description"/>
                </div>
              </div>
            </div>
          </div>

          <!-- ══ CARD 3: Billing Address ══ -->
          <div class="add-card">
            <div class="add-card-header" @click="collapsed.billing=!collapsed.billing">
              <div class="add-card-title">
                <span class="add-card-title-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg></span>
                Billing Address
              </div>
              <span class="add-card-chevron" :class="{collapsed:collapsed.billing}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
              </span>
            </div>
            <div class="add-card-body" :class="{collapsed:collapsed.billing}">
              <div class="inv-fg inv-fg2">
                <!-- Billing Address -->
                <div>
                  <label class="inv-lbl">Billing Address <span v-if="addressLoading" style="color:#9ca3af;font-weight:400">(loading…)</span></label>
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
                <!-- Shipping Address -->
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
          </div>

          <!-- ══ CARD 4: Line Items ══ -->
          <div class="add-card">
            <div class="add-card-header" @click="collapsed.lines=!collapsed.lines">
              <div class="add-card-title">
                <span class="add-card-title-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg></span>
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
                        <label>Item Name <span class="inv-req">*</span></label>
                        <SearchableSelect v-model="line.item_code" :options="items"
                          placeholder="Search item or service"
                          :createable="true" createDoctype="Item"
                          @search="fetchItems" @select="opt => onItemSelect(line, opt)"/>
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
                          <label>HSN/SAC</label>
                          <input v-model="line.hsn_code" class="inv-fi" placeholder="HSN code"/>
                        </div>
                        <div class="po-item-field">
                          <label>UOM</label>
                          <select v-model="line.uom" class="inv-fi">
                            <option v-for="u in uomList" :key="u" :value="u">{{ u }}</option>
                          </select>
                        </div>
                      </div>
                      <div class="po-item-num-row">
                        <div class="po-item-field">
                          <label>Qty</label>
                          <input v-model.number="line.qty" type="number" min="0.001" step="0.001" class="inv-fi" @input="calcLine(line)"/>
                        </div>
                        <div class="po-item-field">
                          <label>Rate ({{ CURRENCY_SYMBOLS[form.currency] || '₹' }})</label>
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
                            <option v-for="t in taxTemplates" :key="t.name" :value="t.name">{{ t.template_name || t.name }}</option>
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
                  <div class="po-total-row"><span>Subtotal</span><span>{{ fmtCur(subtotal) }}</span></div>
                  <template v-for="tl in taxLines" :key="tl.template">
                    <div class="po-total-row"><span>{{ tl.template }} ({{ tl.rate }}%)</span><span>{{ fmtCur(tl.amount) }}</span></div>
                  </template>
                  <div v-if="!taxLines.length" class="po-total-row"><span>Tax</span><span>{{ fmtCur(0) }}</span></div>
                  <div class="po-total-row grand"><span>Grand Total</span><span>{{ fmtCur(grandTotal) }}</span></div>
                </div>
              </div>

              <div style="padding:6px 0 6px">
                <button class="add-notes-link" @click="collapsed.notes=false">
                  <span v-html="icon('plus',12)"></span> Add notes
                </button>
              </div>
            </div>
          </div>

          <!-- ══ CARD 5: Notes & Terms ══ -->
          <div class="add-card">
            <div class="add-card-header" @click="collapsed.notes=!collapsed.notes">
              <div class="add-card-title">
                <span class="add-card-title-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></span>
                Notes &amp; Terms
              </div>
              <span class="add-card-chevron" :class="{collapsed:collapsed.notes}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
              </span>
            </div>
            <div class="add-card-body" :class="{collapsed:collapsed.notes}">
              <div class="inv-fg inv-fg2">
                <div>
                  <label class="inv-lbl">Terms &amp; Conditions <span style="color:#9ca3af;font-weight:400">(printed on quote)</span></label>
                  <textarea v-model="form.terms" class="inv-fi" rows="3" maxlength="500" placeholder="Payment terms, delivery terms, validity…"></textarea>
                  <div class="exp-field-hint" :class="{'exp-field-hint-err': (form.terms||'').length >= 500}">{{ (form.terms||'').length }}/500 characters</div>
                </div>
                <div>
                  <label class="inv-lbl">Internal Remarks <span style="color:#9ca3af;font-weight:400">(not printed)</span></label>
                  <textarea v-model="form.remarks" class="inv-fi" rows="3" maxlength="500" placeholder="Internal notes for your team…"></textarea>
                  <div class="exp-field-hint" :class="{'exp-field-hint-err': (form.remarks||'').length >= 500}">{{ (form.remarks||'').length }}/500 characters</div>
                </div>
              </div>
            </div>
          </div>

        </div><!-- /inv-dbody -->

          <!-- Live preview pane -->
          <div v-if="showPreview" class="inv-preview-pane">
            <div class="inv-preview-toolbar">
              <span style="font-size:11px;font-weight:700;letter-spacing:.05em;color:#6b7280">LIVE PREVIEW</span>
              <div style="display:flex;gap:6px">
                <span style="font-size:11px;color:#9ca3af">{{ TEMPLATES.find(t=>t.key===selectedTemplate)?.label }}</span>
                <button class="inv-va-btn" style="font-size:11px;padding:4px 10px" @click="printQuote(previewData)">
                  <span v-html="icon('download',12)"></span> Print PDF
                </button>
              </div>
            </div>
            <iframe :srcdoc="previewHtml" class="inv-preview-iframe" sandbox="allow-same-origin"></iframe>
          </div>

        </div><!-- /inv-content-row -->

        <!-- Footer -->
        <div class="inv-dfooter">
          <div class="add-footer-status">{{ editingName ? 'Editing: '+editingName : 'New quotation — unsaved changes' }}</div>
          <div class="add-footer-actions">
            <button class="add-btn-cancel" @click="drawerOpen=false">Cancel</button>
            <button class="add-btn-draft" :disabled="drawerSaving" @click="saveQT('Draft')">Save Draft</button>
            <div style="position:relative">
              <button class="add-btn-more" :disabled="drawerSaving" @click="moreActionsOpen=!moreActionsOpen">
                {{ drawerSaving ? 'Saving…' : 'More Actions' }}
                <svg class="add-btn-more-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
              </button>
              <div v-if="moreActionsOpen" class="add-more-menu" v-click-outside="()=>moreActionsOpen=false">
                <button class="add-more-menu-item" @click="saveQT('Sent');moreActionsOpen=false">
                  <span v-html="icon('check',13)"></span> Submit Quote
                </button>
                <button class="add-more-menu-item" @click="saveQT('Draft', true);moreActionsOpen=false">
                  Save &amp; New
                </button>
                <button class="add-more-menu-item" @click="printQuote(previewData);moreActionsOpen=false">
                  <span v-html="icon('download',13)"></span> Save &amp; Print PDF
                </button>
              </div>
            </div>
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
              <span v-if="viewDoc.valid_till"> · Valid till {{ fmtDate(viewDoc.valid_till) }}
                <span v-if="isExpired(viewDoc)"> (expired)</span>
              </span>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <button v-if="canConvert(viewDoc)" class="inv-view-cta" @click="openConvertModal(viewDoc)">
              <span v-html="icon('repeat',14)"></span> Convert
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
                    <!-- pending: the CSS border ring is sufficient — no inner SVG needed -->
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
            <button v-if="viewDoc.docstatus===0" class="inv-ab-btn" @click="viewOpen=false;openEdit(viewDoc)">
              <span v-html="icon('edit',13)"></span> <span class="ab-label">Edit</span>
            </button>
            <button v-if="viewDoc.docstatus===0" class="inv-ab-btn inv-ab-submit" :disabled="viewSubmitting" @click="submitFromView(viewDoc)">
              <span v-html="icon('check',13)"></span> <span class="ab-label">{{ viewSubmitting ? 'Submitting…' : 'Submit' }}</span>
            </button>
            <button v-if="viewDoc.docstatus===1 && viewDoc.status!=='Converted' && viewDoc.status!=='Accepted'" class="inv-ab-btn quote-cancel-btn" :disabled="viewCancelling" @click="cancelQT(viewDoc)">
              <span v-html="icon('x-circle',13)"></span> <span class="ab-label">{{ viewCancelling ? 'Cancelling…' : 'Cancel' }}</span>
            </button>
            <button class="inv-ab-btn" @click="emailQT(viewDoc)">
              <span v-html="icon('mail',13)"></span> <span class="ab-label">Email</span>
            </button>
            <div style="position:relative;display:inline-flex">
              <button class="inv-ab-btn inv-ab-dropdown" @click="showDownloadMenu=!showDownloadMenu">
                <span v-html="icon('download',13)"></span> <span class="ab-label">Download</span>
                <span class="inv-ab-caret">▾</span>
              </button>
              <div v-if="showDownloadMenu" class="inv-dl-menu">
                <div class="inv-dl-menu-header">Export Quote</div>
                <button @click="downloadQuotePdf('pdf')" class="inv-dl-menu-item">
                  <span class="inv-dl-menu-icon" v-html="icon('download',14)"></span>
                  <span class="inv-dl-menu-text">
                    <span class="inv-dl-menu-label">Download PDF</span>
                    <span class="inv-dl-menu-sub">Save to your device</span>
                  </span>
                </button>
                <button @click="downloadQuotePdf('print')" class="inv-dl-menu-item">
                  <span class="inv-dl-menu-icon" v-html="icon('printer',14)"></span>
                  <span class="inv-dl-menu-text">
                    <span class="inv-dl-menu-label">Open &amp; Print</span>
                    <span class="inv-dl-menu-sub">Preview in new tab</span>
                  </span>
                </button>
              </div>
            </div>
            <button v-if="viewDoc.docstatus===1 && viewDoc.status!=='Accepted' && viewDoc.status!=='Converted' && effectiveStatus(viewDoc)!=='Expired'" class="inv-ab-btn" @click="markStatus(viewDoc,'Accepted')">
              <span v-html="icon('check',13)"></span> <span class="ab-label">Accept</span>
            </button>
            <button v-if="viewDoc.docstatus===1 && viewDoc.status!=='Declined' && viewDoc.status!=='Converted' && effectiveStatus(viewDoc)!=='Expired'" class="inv-ab-btn" @click="markStatus(viewDoc,'Declined')">
              <span v-html="icon('x',13)"></span> <span class="ab-label">Decline</span>
            </button>
            <button v-if="canConvert(viewDoc)" class="inv-ab-btn" style="color:#16a34a;border-color:rgba(22,163,106,.3)" @click="openConvertModal(viewDoc)">
              <span v-html="icon('repeat',13)"></span> <span class="ab-label">Convert</span>
            </button>
            <button v-if="viewDoc.docstatus!==1" class="inv-ab-btn quote-delete-btn" @click="deleteQT(viewDoc)">
              <span v-html="icon('trash',13)"></span> <span class="ab-label quote-delete-lbl">Delete</span>
            </button>
          </div>

          <!-- Tabs -->
          <div class="inv-view-tabs">
            <button class="inv-vtab" :class="{ active: viewTab==='details' }" @click="viewTab='details'">Details</button>
            <button class="inv-vtab" :class="{ active: viewTab==='conversions' }" @click="viewTab='conversions'">
              Conversions <span v-if="(conv.sales_orders.length+conv.sales_invoices.length)>0" class="inv-vtab-count">{{ conv.sales_orders.length + conv.sales_invoices.length }}</span>
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
                    <span class="inv-dmeta-lbl">Quote Date</span>
                  </div>
                  <div class="inv-dmeta-date-val">{{ fmtDate(viewDoc.transaction_date) }}</div>
                </div>
                <div class="inv-details-meta-col">
                  <div class="inv-dmeta-icon-row">
                    <span class="inv-dmeta-icon" v-html="icon('calendar',13)"></span>
                    <span class="inv-dmeta-lbl">Valid Till</span>
                  </div>
                  <div class="inv-dmeta-date-val" :class="{ 'is-overdue': isExpired(viewDoc) }">
                    {{ fmtDate(viewDoc.valid_till) || '—' }}
                  </div>
                </div>
                <div class="inv-details-meta-col">
                  <div class="inv-dmeta-icon-row">
                    <span class="inv-dmeta-icon" v-html="icon('indianrupee',13)"></span>
                    <span class="inv-dmeta-lbl">Grand Total</span>
                  </div>
                  <div class="inv-balance-val">
                    {{ fmtDocCur(viewDoc.grand_total, viewDoc) }}
                  </div>
                </div>
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
                        <th>HSN/SAC</th>
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
                        <td class="inv-dash">{{ it.hsn_code || '—' }}</td>
                        <td class="td-r" >{{ flt(it.qty) }}</td>
                        <td class="td-r" >{{ fmtDocCur(it.rate, viewDoc) }}</td>
                        <td class="td-r inv-dash">{{ it.discount_percentage ? it.discount_percentage+'%' : '—' }}</td>
                        <td class="td-r" style="font-weight:600">{{ fmtDocCur(it.amount, viewDoc) }}</td>
                      </tr>
                    </tbody>
                  </table>

                  <!-- Totals section -->
                  <div class="inv-totals-section">
                    <div class="inv-totals-inner">
                      <div class="inv-total-line">
                        <span class="t-lbl">Subtotal</span>
                        <span class="t-amt">{{ fmtDocCur(viewDoc.net_total != null ? viewDoc.net_total : (viewDoc.grand_total||0)-(viewDoc.total_tax||0), viewDoc) }}</span>
                      </div>
                      <template v-if="viewDoc.taxes&&viewDoc.taxes.length">
                        <div v-for="(tx,i) in viewDoc.taxes" :key="i" class="inv-total-line">
                          <span class="t-lbl">{{ tx.description||tx.account_head }}</span>
                          <span class="t-amt">{{ fmtDocCur(tx.tax_amount||tx.amount||0, viewDoc) }}</span>
                        </div>
                      </template>
                      <div class="inv-grand-total-line">
                        <span class="inv-grand-lbl">Grand Total</span>
                        <span class="inv-grand-amt">{{ fmtDocCur(viewDoc.grand_total, viewDoc) }}</span>
                      </div>
                    </div>
                  </div>
                </div>
                <div v-else style="color:#9ca3af;font-size:13px;padding:8px 0">No item details available.</div>
              </template>
            </div>

            <!-- Bottom grid: Address + Notes -->
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
              <!-- Notes & Terms card -->
              <div class="inv-bottom-card">
                <div class="inv-bottom-card-header">
                  <div class="inv-bottom-card-title">
                    <span v-html="icon('sticky-note',14)"></span> Notes &amp; Terms
                  </div>
                </div>
                <div class="inv-bottom-card-body">
                  <div v-if="viewDoc.terms||viewDoc.remarks">
                    <div v-if="viewDoc.terms" style="font-size:13px;color:#374151;margin-bottom:10px">
                      <div style="font-size:10.5px;font-weight:700;text-transform:uppercase;color:#9ca3af;margin-bottom:4px">Terms & Conditions</div>
                      <div style="white-space:pre-wrap">{{ viewDoc.terms }}</div>
                    </div>
                    <div v-if="viewDoc.remarks" style="font-size:13px;color:#374151">
                      <div style="font-size:10.5px;font-weight:700;text-transform:uppercase;color:#9ca3af;margin-bottom:4px">Internal Remarks</div>
                      {{ viewDoc.remarks }}
                    </div>
                  </div>
                  <div v-else class="inv-notes-empty">
                    <div class="inv-notes-empty-icon" v-html="icon('file-text',36)"></div>
                    <div class="inv-notes-empty-text">No notes added yet</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Footer -->
            <div class="inv-view-footer" v-if="viewDoc.owner">
              Created by {{ viewDoc.owner }} on {{ fmtDate(viewDoc.creation) }}
            </div>
          </template>

          <!-- ── Conversions tab ── -->
          <template v-else-if="viewTab==='conversions'">
            <div class="inv-tab-body">
              <div v-if="viewLoading" style="padding:24px;text-align:center;color:#9ca3af">Loading…</div>
              <template v-else>
                <div v-if="conv.sales_orders.length" class="inv-items-wrap" style="margin-bottom:16px">
                  <div style="padding:10px 14px;font-size:11px;font-weight:700;text-transform:uppercase;color:#6b7280;background:#f9fafb;border-bottom:1px solid #e8ecf0">Sales Orders</div>
                  <table class="inv-items-table">
                    <thead><tr>
                      <th>Order #</th><th>Date</th><th class="th-r">Amount</th>
                    </tr></thead>
                    <tbody>
                      <tr v-for="so in conv.sales_orders" :key="so.name">
                        <td><DocLink doctype="Sales Order" :name="so.name" /></td>
                        <td class="mono-sm">{{ fmtDate(so.transaction_date) }}</td>
                        <td class="td-r" style="font-weight:600">{{ fmtCur(so.grand_total, so.currency) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-if="conv.sales_invoices.length" class="inv-items-wrap">
                  <div style="padding:10px 14px;font-size:11px;font-weight:700;text-transform:uppercase;color:#6b7280;background:#f9fafb;border-bottom:1px solid #e8ecf0">Sales Invoices</div>
                  <table class="inv-items-table">
                    <thead><tr>
                      <th>Invoice #</th><th>Date</th><th class="th-r">Amount</th>
                    </tr></thead>
                    <tbody>
                      <tr v-for="si in conv.sales_invoices" :key="si.name">
                        <td><DocLink doctype="Sales Invoice" :name="si.name" /></td>
                        <td class="mono-sm">{{ fmtDate(si.posting_date) }}</td>
                        <td class="td-r" style="font-weight:600">{{ fmtCur(si.grand_total, si.currency) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-if="!conv.sales_orders.length && !conv.sales_invoices.length"
                  style="text-align:center;padding:48px;color:#9ca3af;font-size:13px">
                  Not converted yet.
                  <div v-if="canConvert(viewDoc)" style="margin-top:12px">
                    <button class="inv-view-cta" @click="openConvertModal(viewDoc)">Convert</button>
                  </div>
                </div>
              </template>
            </div>
          </template>

        </div><!-- /inv-view-body -->
      </div><!-- /inv-drawer-panel -->
    </div><!-- /inv-drawer-bg -->

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

    <!-- ── Convert modal ── -->
    <div v-if="convertModal.open" class="rp-backdrop" @click.self="convertModal.open=false">
      <div class="rp-dialog" style="max-width:520px">
        <div class="rp-dialog-header">
          <span class="rp-dialog-title">Convert Quotation — {{ convertModal.qtName }}</span>
          <button class="rp-close-btn" @click="convertModal.open=false">✕</button>
        </div>
        <div class="rp-body">
          <div style="font-size:13px;color:#374151;margin-bottom:12px">Choose how to convert this quote:</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
            <button style="background:#fff;border:2px solid;border-radius:10px;padding:14px;display:flex;align-items:center;gap:12px;cursor:pointer;text-align:left;font-family:inherit;transition:all .15s"
              :style="convertModal.target==='SO'?'border-color:#1a6ef7;background:#eff6ff;box-shadow:0 0 0 4px rgba(26,110,247,.1)':'border-color:#e5e7eb'"
              @click="convertModal.target='SO'">
              <div style="width:40px;height:40px;border-radius:8px;display:grid;place-items:center;font-weight:800;font-size:14px;background:#dcfce7;color:#16a34a;flex-shrink:0">SO</div>
              <div>
                <div style="font-weight:700">Sales Order</div>
                <div style="font-size:11.5px;color:#6b7280">Track fulfillment + delivery separately</div>
              </div>
            </button>
            <button style="background:#fff;border:2px solid;border-radius:10px;padding:14px;display:flex;align-items:center;gap:12px;cursor:pointer;text-align:left;font-family:inherit;transition:all .15s"
              :style="convertModal.target==='Invoice'?'border-color:#1a6ef7;background:#eff6ff;box-shadow:0 0 0 4px rgba(26,110,247,.1)':'border-color:#e5e7eb'"
              @click="convertModal.target='Invoice'">
              <div style="width:40px;height:40px;border-radius:8px;display:grid;place-items:center;font-weight:800;font-size:14px;background:#dbeafe;color:#1a6ef7;flex-shrink:0">$</div>
              <div>
                <div style="font-weight:700">Sales Invoice</div>
                <div style="font-size:11.5px;color:#6b7280">Bill the customer immediately</div>
              </div>
            </button>
          </div>
          <div v-if="convertModal.target==='SO'" style="margin-top:14px">
            <label class="inv-lbl">Delivery Date</label>
            <input v-model="convertModal.deliveryDate" type="date" class="inv-fi" />
          </div>
          <div v-if="convertModal.target==='Invoice'" style="margin-top:14px">
            <label class="inv-lbl">Due Date</label>
            <input v-model="convertModal.dueDate" type="date" class="inv-fi" />
          </div>
        </div>
        <div class="rp-footer">
          <button class="rp-btn rp-btn-outline" @click="convertModal.open=false" :disabled="convertModal.saving">Cancel</button>
          <button class="rp-btn" :disabled="convertModal.saving||!convertModal.target" @click="submitConvert">
            {{ convertModal.saving ? 'Converting…' : (convertModal.target ? `Convert to ${convertModal.target==='SO' ? 'Sales Order' : 'Invoice'}` : 'Choose target') }}
          </button>
        </div>
      </div>
    </div>

  </Teleport>
</div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted } from "vue";
import { apiList, apiSave, apiGet, apiGET, apiPOST, apiDelete, apiSubmit, apiCancel, resolveCompany, refreshCsrfToken } from "../api/client.js";
import { COUNTRIES, statesFor } from "../composables/useCountryState.js";
import { useToast } from "../composables/useToast.js";
import { usePermissions } from "../composables/usePermissions.js";
import { useRoute, useRouter } from "vue-router";
import { useEmailDialog } from "../composables/useEmailDialog.js";
import { useOpenFromQuery } from "../composables/useOpenFromQuery.js";
import { usePagination } from "../composables/usePagination.js";
import DocLink from "../components/DocLink.vue";
import Pagination from "../components/Pagination.vue";
import SummaryStrip from "../components/SummaryStrip.vue";
import { useConfirm } from "../composables/useConfirm.js";
import { useLivePreview } from "../composables/useLivePreview.js";
import { icon } from "../utils/icons.js";
import { flt, fmtDate } from "../utils/format.js";
import { templateHeadlineRate } from "../composables/useTaxCalc.js";
import SearchableSelect from "../components/SearchableSelect.vue";

const { toast } = useToast();
const { canWrite } = usePermissions();
const route = useRoute();
const router = useRouter();

function goToBrandingSettings() {
  router.push({ name: "settings-company", query: { tab: "branding" } });
}
const { confirm } = useConfirm();
const { setCompany, refreshBranding, renderDocument, printDoc } = useLivePreview();
const QT_PRINT_CFG = { title: "QUOTATION", partyLabel: "Quote To", partyField: "customer_name" };

// Map the page's local print-data shape onto the standard doc contract that
// useLivePreview.renderDocument expects (net_total / grand_total / taxes[].tax_amount).
function _toPrintDoc(data) {
  return {
    ...data,
    net_total: data.subtotal,
    total_taxes_and_charges: data.totalTax,
    grand_total: data.grandTotal,
    address_display: data.address_display || data.billing_address || "",
    taxes: (data.taxes || []).map(t => ({
      description: t.description || t.account_head || "",
      rate: t.rate,
      tax_amount: t.tax_amount != null ? t.tax_amount : t.amount,
    })),
  };
}
function _qtCfg(data) { return { ...QT_PRINT_CFG, companyName: data?.company || window.__booksCompany || "" }; }
const { openEmail } = useEmailDialog();

// ── Tabs ──────────────────────────────────────────────────────────────
const activeTab = ref("all");
const tabs = [
  { key: "all",       label: "All" },
  { key: "draft",     label: "Draft" },
  { key: "sent",      label: "Sent" },
  { key: "accepted",  label: "Accepted" },
  { key: "declined",  label: "Declined" },
  { key: "expired",   label: "Expired" },
  { key: "converted", label: "Converted" },
];

// ── Templates & branding ─────────────────────────────────────────────
const TEMPLATES = [
  { key: "classic", label: "Classic" },
  { key: "modern",  label: "Modern"  },
  { key: "minimal", label: "Minimal" },
];
const CURRENCY_SYMBOLS = { INR: "₹" };

// ── Tax presets ──────────────────────────────────────────────────────
const TAX_PRESETS = [
  { label: "GST 5%",   rows: [{ desc: "CGST @ 2.5%", rate: 2.5 }, { desc: "SGST @ 2.5%", rate: 2.5 }] },
  { label: "GST 12%",  rows: [{ desc: "CGST @ 6%",   rate: 6   }, { desc: "SGST @ 6%",   rate: 6   }] },
  { label: "GST 18%",  rows: [{ desc: "CGST @ 9%",   rate: 9   }, { desc: "SGST @ 9%",   rate: 9   }] },
  { label: "GST 28%",  rows: [{ desc: "CGST @ 14%",  rate: 14  }, { desc: "SGST @ 14%",  rate: 14  }] },
  { label: "IGST 5%",  rows: [{ desc: "IGST @ 5%",   rate: 5   }] },
  { label: "IGST 12%", rows: [{ desc: "IGST @ 12%",  rate: 12  }] },
  { label: "IGST 18%", rows: [{ desc: "IGST @ 18%",  rate: 18  }] },
  { label: "IGST 28%", rows: [{ desc: "IGST @ 28%",  rate: 28  }] },
];

// ── State ─────────────────────────────────────────────────────────────
const list        = ref([]);
const loading     = ref(false);
const search      = ref("");
const viewMode    = ref("table"); // "table" | "grid"
const selected    = ref(new Set());
const showPreview     = ref(false);
const selectedTemplate = ref("modern");
const brandColor      = ref("#1a6ef7");
const logoUrl         = ref("");
const logoUploading   = ref(false);
const drawerOpen  = ref(false);
const drawerSaving = ref(false);
const editingName = ref("");
const moreActionsOpen = ref(false);
const collapsed = reactive({ branding: false, details: false, billing: true, lines: false, notes: true });
const viewOpen    = ref(false);
const viewDoc        = ref(null);
const viewTab        = ref("details");
const viewLoading    = ref(false);
const viewSubmitting = ref(false);
const viewCancelling = ref(false);
const viewItems   = ref([]);
const addressLoading = ref(false);
const conv        = reactive({ sales_orders: [], sales_invoices: [] });
const customers   = ref([]);
const items       = ref([]);
const lines       = ref([]);
const taxTemplates   = ref([]);
const uomList        = ref([]);
const taxAccountHead = ref("");
const sortCol     = ref("transaction_date");
const sortDir     = ref("desc");
const filterCustomer = ref("");

const convertModal = reactive({
  open: false, saving: false, qtName: "",
  target: "", deliveryDate: "", dueDate: "",
});

// ── Helpers ───────────────────────────────────────────────────────────
function todayStr() { return new Date().toISOString().slice(0, 10); }
function validTillDefault() {
  const d = new Date(); d.setDate(d.getDate() + 30);
  return d.toISOString().slice(0, 10);
}
function fmtCur(v, currency) {
  const cur = currency || form.currency || "INR";
  const locale = cur === "INR" ? "en-IN" : "en-US";
  try {
    return new Intl.NumberFormat(locale, {
      style: "currency", currency: cur, minimumFractionDigits: 2,
    }).format(flt(v));
  } catch {
    return new Intl.NumberFormat("en-IN", {
      style: "currency", currency: "INR", minimumFractionDigits: 2,
    }).format(flt(v));
  }
}
function fmtDocCur(v, doc) {
  const cur = doc?.currency || "INR";
  const locale = cur === "INR" ? "en-IN" : "en-US";
  try {
    return new Intl.NumberFormat(locale, {
      style: "currency", currency: cur, minimumFractionDigits: 2,
    }).format(flt(v));
  } catch {
    return fmtCur(v);
  }
}

// ── Form ──────────────────────────────────────────────────────────────
const form = reactive({
  customer: "",
  transaction_date: todayStr(),
  valid_till: validTillDefault(),
  title: "",
  terms: "",
  remarks: "",
  billing_address: "",
  billing_address_name: "",
  shipping_address: "",
  shipping_address_name: "",
  currency: "INR",
  exchange_rate: 1,
  logo: "",  // stores the Frappe file URL from logo_attach field
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

// ── Blank line ───────────────────────────────────────────────────────
let _id = 1;
function blankLine() {
  return {
    id: _id++,
    item_code: "",
    item_name: "",
    description: "",
    hsn_code: "",
    qty: 1,
    rate: 0,
    uom: "Nos",
    discount_percentage: 0,
    discount_amount: 0,
    amount: 0,
    tax_code: "",
    collapsed: false,
  };
}

// ── Status helpers ────────────────────────────────────────────────────
function isExpired(q) {
  if (!q?.valid_till) return false;
  if (q.status === "Converted" || q.status === "Accepted" || q.status === "Declined" || q.status === "Lost") return false;
  return new Date(q.valid_till) < new Date();
}
function effectiveStatus(q) {
  if (
    q?.status === "Converted" || q?.status === "Accepted" ||
    q?.status === "Declined"  || q?.status === "Lost"
  ) return q.status;
  if (isExpired(q)) return "Expired";
  return q?.status || "Draft";
}
function displayStatus(q) { return effectiveStatus(q).toUpperCase(); }
function badgeClass(q) {
  const s = effectiveStatus(q);
  if (s === "Draft")                         return "status-draft";
  if (s === "Sent")                          return "status-unpaid";
  if (s === "Accepted")                      return "status-paid";
  if (s === "Converted")                     return "status-paid";
  if (s === "Declined" || s === "Lost")      return "status-cancelled";
  if (s === "Expired")                       return "status-overdue";
  return "status-draft";
}
function headerBg(q) {
  const s = effectiveStatus(q);
  if (s === "Converted") return "linear-gradient(135deg,#581c87,#a855f7)";
  if (s === "Accepted")  return "linear-gradient(135deg,#064e3b,#059669)";
  if (s === "Declined" || s === "Lost" || s === "Expired")
    return "linear-gradient(135deg,#7f1d1d,#dc2626)";
  if (s === "Sent")      return "linear-gradient(135deg,#1e3a5f,#1a6ef7)";
  return "linear-gradient(135deg,#1e3a5f,#2563eb)";
}
function sortArrowTxt(col) {
  if (sortCol.value !== col) return "";
  return sortDir.value === "asc" ? "↑" : "↓";
}
function canConvert(q) {
  if (q?.docstatus !== 1) return false;
  const s = effectiveStatus(q);
  return s !== "Converted" && s !== "Declined" && s !== "Lost" && s !== "Expired";
}

// ── Timeline ──────────────────────────────────────────────────────────
const timelineSteps = computed(() => {
  const q = viewDoc.value;
  if (!q) return [];
  const s = effectiveStatus(q);
  if (s === "Declined" || s === "Lost") {
    return [
      { key: "draft", label: "Draft", done: true },
      { key: "sent",  label: "Sent",  done: true },
      { key: "end",   label: "Declined", danger: true },
    ];
  }
  if (s === "Expired") {
    return [
      { key: "draft", label: "Draft", done: true },
      { key: "sent",  label: "Sent",  done: true },
      { key: "end",   label: "Expired", danger: true },
    ];
  }
  return [
    { key: "draft",     label: "Draft",     done: true },
    { key: "sent",      label: "Sent",      done: s !== "Draft" },
    { key: "accepted",  label: "Accepted",  done: s === "Accepted" || s === "Converted" },
    { key: "converted", label: "Converted", done: s === "Converted" },
  ];
});

const tlProgressWidth = computed(() => {
  const steps = timelineSteps.value;
  if (!steps.length) return "0%";
  const doneCount = steps.filter(s => s.done || s.danger).length;
  return Math.round(((doneCount - 1) / (steps.length - 1)) * 100) + "%";
});

// ── Load list ─────────────────────────────────────────────────────────
async function load() {
  loading.value = true;
  try {
    const co = await resolveCompany();
    list.value = await apiList("Quotation", {
      fields: ["name","customer","customer_name","transaction_date",
               "valid_till","status","docstatus","grand_total","title","currency"],
      filters: [["company","=",co]],
      limit: 100000,
      order: "transaction_date desc, creation desc",
    });
  } catch (e) {
    toast.error(e.message || "Failed to load quotations");
  } finally {
    loading.value = false;
  }
}

async function loadTaxAccount() {
  try {
    const co = await resolveCompany();
    const r = await apiList("Account", {
      fields: ["name"],
      filters: [
        ["company",       "=", co],
        ["account_type",  "=", "Tax"],
        ["is_group",      "=", 0],
      ],
      limit: 1,
    });
    if (r?.length) taxAccountHead.value = r[0].name;
  } catch {}
  try {
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

// ── Counts & filters ──────────────────────────────────────────────────
const counts = computed(() => {
  const c = { draft:0, sent:0, accepted:0, declined:0, expired:0, converted:0 };
  for (const q of list.value) {
    const s = effectiveStatus(q).toLowerCase();
    if      (s === "draft")                   c.draft++;
    else if (s === "sent")                    c.sent++;
    else if (s === "accepted")                c.accepted++;
    else if (s === "converted")               c.converted++;
    else if (s === "declined" || s === "lost") c.declined++;
    else if (s === "expired")                 c.expired++;
  }
  return c;
});

const filtered = computed(() => {
  let r = list.value;
  if (activeTab.value !== "all") {
    r = r.filter(q => {
      const s = effectiveStatus(q).toLowerCase();
      if (activeTab.value === "declined") return s === "declined" || s === "lost";
      return s === activeTab.value;
    });
  }
  if (filterCustomer.value) r = r.filter(q => q.customer === filterCustomer.value);
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    r = r.filter(x =>
      (x.name || "").toLowerCase().includes(q) ||
      (x.customer_name || x.customer || "").toLowerCase().includes(q) ||
      (x.title || "").toLowerCase().includes(q)
    );
  }
  return r;
});

const sorted = computed(() => {
  const col = sortCol.value;
  return [...filtered.value].sort((a, b) => {
    const av = a[col] ?? "", bv = b[col] ?? "";
    const c = typeof av === "number"
      ? av - bv
      : String(av).localeCompare(String(bv));
    return sortDir.value === "asc" ? c : -c;
  });
});

const { page, pageSize, paged } = usePagination(sorted, { storageKey: "quotes" });

// ── Month helpers ─────────────────────────────────────────────────────
const _qtYM  = () => { const d=new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; };
const _qtLYM = () => { const d=new Date(); d.setMonth(d.getMonth()-1); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; };
const _qtTr  = (a,b) => { if(!b&&!a) return {pct:0,up:true}; if(!b) return {pct:100,up:true}; const p=Math.round((a-b)/b*100); return {pct:Math.abs(p),up:p>=0}; };

// ── KPI card trends ───────────────────────────────────────────────────
const qtTrends = computed(() => {
  const thisYM = _qtYM(), lastYM = _qtLYM();
  const thisAll = list.value.filter(q => (q.transaction_date||'').startsWith(thisYM));
  const lastAll = list.value.filter(q => (q.transaction_date||'').startsWith(lastYM));
  const es = (q) => effectiveStatus(q).toLowerCase();
  return {
    total:     _qtTr(thisAll.length,                                lastAll.length),
    draft:     _qtTr(thisAll.filter(q=>es(q)==='draft').length,     lastAll.filter(q=>es(q)==='draft').length),
    sent:      _qtTr(thisAll.filter(q=>es(q)==='sent').length,      lastAll.filter(q=>es(q)==='sent').length),
    converted: _qtTr(thisAll.filter(q=>es(q)==='converted').length, lastAll.filter(q=>es(q)==='converted').length),
    expired:   _qtTr(thisAll.filter(q=>es(q)==='expired').length,   lastAll.filter(q=>es(q)==='expired').length),
  };
});

// ── Secondary stat cards ──────────────────────────────────────────────
const thisMonthQuotes = computed(() => list.value.filter(q=>(q.transaction_date||'').startsWith(_qtYM())).length);
const conversionRate = computed(() => {
  if (!list.value.length) return "0%";
  return ((counts.value.converted / list.value.length) * 100).toFixed(0) + "%";
});
const avgQuoteValue = computed(() => {
  const itms = list.value.filter(q => q.grand_total > 0);
  if (!itms.length) return 0;
  return itms.reduce((s, q) => s + flt(q.grand_total), 0) / itms.length;
});

function sortBy(col) {
  if (sortCol.value === col)
    sortDir.value = sortDir.value === "asc" ? "desc" : "asc";
  else { sortCol.value = col; sortDir.value = "asc"; }
}

// ── Selection ─────────────────────────────────────────────────────────
const allChecked = computed(() =>
  sorted.value.length > 0 && sorted.value.every(q => selected.value.has(q.name))
);
function toggle(n) {
  const s = new Set(selected.value);
  s.has(n) ? s.delete(n) : s.add(n);
  selected.value = s;
}
function toggleAll(e) {
  selected.value = e.target.checked
    ? new Set(sorted.value.map(q => q.name))
    : new Set();
}

// ── Totals ────────────────────────────────────────────────────────────
const subtotal = computed(() => lines.value.reduce((s, l) => s + flt(l.amount), 0));

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

// ── Fetch helpers ─────────────────────────────────────────────────────
async function fetchCustomers(q = "") {
  try {
    const f = [["disabled","=",0]];
    if (q) f.push(["customer_name","like","%" + q + "%"]);
    const r = await apiList("Customer", {
      fields: ["name","customer_name"], filters: f, limit: 30, order: "customer_name asc",
    });
    customers.value = r.map(x => ({ ...x, label: x.customer_name || x.name, value: x.name }));
  } catch { customers.value = []; }
}

async function fetchItems(q = "") {
  try {
    const f = [["disabled","=",0],["has_variants","=",0],["is_sales_item","=",1]];
    if (q) f.push(["item_name","like","%" + q + "%"]);
    const r = await apiList("Item", {
      fields: ["name","item_name","standard_rate","stock_uom","hsn_code","description"], filters: f, limit: 30, order: "item_name asc",
    });
    items.value = r.map(x => ({
      ...x,
      label:       x.item_name || x.name,
      value:       x.name,
      rate:        x.standard_rate || 0,
      uom:         x.stock_uom || "Nos",
      hsn_code:    x.hsn_code || "",
      description: x.description || "",
    }));
  } catch { items.value = []; }
}

// ── Line item helpers ─────────────────────────────────────────────────
function addLine() { lines.value.push(blankLine()); }
function removeLine(id) { lines.value = lines.value.filter(l => l.id !== id); }
function calcLine(line) {
  if (line.discount_percentage > 100) line.discount_percentage = 100;
  if (line.discount_percentage < 0)   line.discount_percentage = 0;
  const base = Math.round(flt(line.qty) * flt(line.rate) * 100) / 100;
  const disc = Math.round(base * flt(line.discount_percentage) / 100 * 100) / 100;
  line.discount_amount = disc;
  line.amount = base - disc;
}

async function onItemSelect(line, opt) {
  const code = opt?.value ?? opt;
  line.item_code = code;
  const found = items.value.find(i => i.name === code || i.value === code);
  if (found) {
    line.item_name  = found.item_name || found.label || code;
    line.rate       = flt(found.standard_rate ?? found.rate);
    line.uom        = found.stock_uom || found.uom || "Nos";
    if (found.hsn_code)    line.hsn_code    = found.hsn_code;
    if (found.description) line.description = found.description;
    if (found.tax_code !== undefined) line.tax_code = found.tax_code || "";
    calcLine(line);
  }
  if (code) {
    try {
      const doc = await apiGet("Item", code);
      if (doc?.item_name)    line.item_name  = doc.item_name;
      if (doc?.hsn_code)     line.hsn_code   = doc.hsn_code;
      if (doc?.description)  line.description = doc.description;
      if (doc?.tax_code)     line.tax_code   = doc.tax_code;
      if (!found) {
        line.rate = flt(doc.standard_rate || 0);
        line.uom  = doc.stock_uom || "Nos";
      }
      calcLine(line);
    } catch {}
  }
}

// ── Customer change ───────────────────────────────────────────────────
async function onCustomerChange() {
  form.billing_address = ""; form.billing_address_name = "";
  form.shipping_address = ""; form.shipping_address_name = "";
  if (!form.customer) { customerAddresses.value = []; return; }
  addressLoading.value = true;
  try {
    const custDoc = await apiGet("Customer", form.customer);
    form.currency = "INR";
    form.exchange_rate = 1;
    await fetchCustomerAddresses(form.customer);
    // Auto-select first billing address if available
    const firstBilling = customerAddresses.value.find(a => a.address_type === "Billing") || customerAddresses.value[0];
    if (firstBilling) {
      form.billing_address_name = firstBilling.name;
      form.billing_address = formatAddress(firstBilling);
    }
  } catch {}
  addressLoading.value = false;
}
watch(() => form.customer, (newVal) => { if (newVal) onCustomerChange(); });

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

// ── Logo helpers ──────────────────────────────────────────────────────
function logoSrc(url) {
  if (!url) return "";
  if (url.startsWith("data:") || url.startsWith("http")) return url;
  const base = (window.frappe?.boot?.site_url || window.location.origin).replace(/\/$/, "");
  return base + url;
}
function removeLogo() {
  form.logo = "";
  logoUrl.value = "";
  // logo is per-quote, not a branding preference
}

// ── Logo upload ───────────────────────────────────────────────────────
// Strategy:
//   - Existing quote (editingName set): upload immediately, linked to the doc.
//   - New quote (no docname yet): store as data URL; saveQT() will upload once
//     the doc is created and patch the `logo` field on it.
async function onLogoUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  e.target.value = "";
  if (file.size > 2 * 1024 * 1024) {
    toast.error("Logo must be smaller than 2 MB");
    return;
  }
  // Always show an instant preview via data URL
  const reader = new FileReader();
  reader.onload = ev => {
    form.logo = ev.target.result;
    logoUrl.value = ev.target.result;
  };
  reader.readAsDataURL(file);

  // Only upload immediately when editing an existing quote (docname known)
  if (!editingName.value) return; // saveQT() will handle it on save

  logoUploading.value = true;
  try {
    const fd = new FormData();
    fd.append("file", file, file.name);
    fd.append("is_private", "0");
    fd.append("folder", "Home/Attachments");
    fd.append("doctype", "Quotation");
    fd.append("docname", editingName.value);
    fd.append("fieldname", "logo");
    const res = await fetch("/api/method/upload_file", {
      method: "POST",
      headers: { "X-Frappe-CSRF-Token": window.csrf_token || frappe?.csrf_token || "" },
      body: fd,
    });
    const json = await res.json();
    const fileUrl = json?.message?.file_url || json?.file_url || "";
    if (fileUrl) {
      form.logo = fileUrl;
      logoUrl.value = fileUrl;
      // Patch the field on the existing doc right away so it survives a reload
      await apiPOST("frappe.client.set_value", {
        doctype: "Quotation",
        name: editingName.value,
        fieldname: "logo",
        value: fileUrl,
      });
    }
  } catch(err) {
    console.warn("Logo upload failed:", err);
    // Keep data URL so preview still works; will retry on next save
  }
  logoUploading.value = false;
}

// ── Open New ──────────────────────────────────────────────────────────
function openNew() {
  editingName.value = "";
  moreActionsOpen.value = false;
  Object.assign(collapsed, { branding: false, details: false, billing: true, lines: false, notes: true });
  Object.assign(form, {
    customer: "", transaction_date: todayStr(), valid_till: validTillDefault(),
    title: "", terms: "", remarks: "",
    billing_address: "", billing_address_name: "",
    shipping_address: "", shipping_address_name: "",
    currency: "INR", exchange_rate: 1, logo: "",
  });
  showPreview.value = false;
  lines.value = [blankLine()];
  fetchCustomers("");
  fetchItems("");
  drawerOpen.value = true;
}

// ── Open Edit ─────────────────────────────────────────────────────────
async function openEdit(q) {
  editingName.value = q.name;
  moreActionsOpen.value = false;
  Object.assign(collapsed, { branding: false, details: false, billing: true, lines: false, notes: true });
  Object.assign(form, {
    customer: q.customer || "", transaction_date: q.transaction_date || todayStr(),
    valid_till: q.valid_till || validTillDefault(), title: q.title || "",
    terms: q.terms || "", currency: q.currency || "INR",
    exchange_rate: q.exchange_rate || 1, remarks: "",
    billing_address: "", billing_address_name: "",
    shipping_address: "", shipping_address_name: "",
    logo: q.logo || q.logo_attach || "",
  });
  lines.value = [blankLine()];
  fetchCustomers("");
  fetchItems("");
  drawerOpen.value = true;
  try {
    const doc = await apiGet("Quotation", q.name);
    if (doc?.items?.length) {
      lines.value = doc.items.map((it) => ({
        id: _id++, item_code: it.item_code || "", item_name: it.item_name || it.item_code || "",
        description: it.description || "", hsn_code: it.hsn_code || "",
        qty: flt(it.qty) || 1, rate: flt(it.rate) || 0, uom: it.uom || "Nos",
        discount_percentage: flt(it.discount_percentage) || 0,
        discount_amount: flt(it.discount_amount) || 0, amount: flt(it.amount) || 0,
        tax_code: it.tax_code || "", collapsed: false,
      }));
    }
    if (doc?.terms)           form.terms           = doc.terms;
    if (doc?.title)           form.title           = doc.title;
    if (doc?.currency)        form.currency        = doc.currency;
    if (doc?.exchange_rate)   form.exchange_rate   = flt(doc.exchange_rate) || 1;
    if (doc?.remarks)         form.remarks         = doc.remarks;
    if (doc?.billing_address) form.billing_address = doc.billing_address;
    if (doc?.shipping_address) form.shipping_address = doc.shipping_address;
    if (doc?.logo)            form.logo            = doc.logo;
    else if (doc?.logo_attach) form.logo            = doc.logo_attach;
    // Restore address link fields
    if (doc?.billing_address_name || doc?.shipping_address_name) {
      await fetchCustomerAddresses(doc.customer || q.customer);
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
    } else if (q.customer) {
      await fetchCustomerAddresses(q.customer);
    }
  } catch {}
}

// ── Open View ─────────────────────────────────────────────────────────
async function openView(q) {
  viewDoc.value = q; viewOpen.value = true; viewTab.value = "details";
  viewLoading.value = true; viewItems.value = [];
  conv.sales_orders = []; conv.sales_invoices = [];
  try {
    const doc = await apiGet("Quotation", q.name);
    const merged = doc?.message || doc || {};
    viewDoc.value = { ...q, ...merged };
    let itms = merged.items || [];
    if (!itms.length) {
      try {
        itms = await apiList("Quotation Item", {
          fields: ["item_code","item_name","description","qty","rate","amount","uom","discount_percentage","hsn_code"],
          filters: [["parent","=",q.name]], limit: 200, order: "idx asc",
        }) || [];
      } catch {}
    }
    viewItems.value = itms;
  } catch (e) { console.warn("openView doc fetch failed:", e); }
  try {
    const convData = await apiGET("zoho_books_clone.api.docs.get_quote_conversions", { quotation_name: q.name });
    if (convData) {
      conv.sales_orders = convData.sales_orders || [];
      conv.sales_invoices = convData.sales_invoices || [];
    }
  } catch {}
  viewLoading.value = false;
}

// ── Save ──────────────────────────────────────────────────────────────
async function saveQT(newStatus, andNew = false) {
  if (!form.customer) return toast.error("Customer is required");
  if (!lines.value.some(l => l.item_code && flt(l.qty) > 0))
    return toast.error("At least one item required");
  if (lines.value.some(l => (l.description||'').length > 500)) return toast.error("Item description cannot exceed 500 characters");
  if ((form.terms||'').length > 500) return toast.error("Terms & Conditions cannot exceed 500 characters");
  if ((form.remarks||'').length > 500) return toast.error("Internal Remarks cannot exceed 500 characters");
  drawerSaving.value = true;
  try {
    const company = await resolveCompany();
    const qtItems = lines.value.filter(l => l.item_code).map(l => ({
      doctype: "Quotation Item", item_code: l.item_code,
      item_name: l.item_name || l.item_code,
      description: l.description || l.item_name || l.item_code,
      qty: flt(l.qty) || 1, rate: flt(l.rate), uom: l.uom || "Nos",
      amount: flt(l.amount), hsn_code: l.hsn_code || "",
      discount_percentage: flt(l.discount_percentage) || 0,
      tax_code: l.tax_code || "",
    }));
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
    // If form.logo is still a data URL it means the file hasn't been uploaded to
    // Frappe yet (new quote with no docname, or prior upload failed).
    // Strip it from the initial save — Frappe rejects base64 in an Attach field.
    const pendingDataUrl = (form.logo || "").startsWith("data:") ? form.logo : "";
    const resolvedLogoPath = pendingDataUrl ? "" : (form.logo || "");

    const doc = {
      doctype: "Quotation", company, party_name: form.customer,
      customer: form.customer, transaction_date: form.transaction_date,
      valid_till: form.valid_till || null, title: form.title || "",
      status: newStatus || "Draft", terms: form.terms || "",
      remarks: form.remarks || "",
      billing_address: form.billing_address || "", billing_address_name: form.billing_address_name || "",
      shipping_address: form.shipping_address || "", shipping_address_name: form.shipping_address_name || "",
      currency: form.currency || "INR",
      exchange_rate: form.currency === "INR" ? 1 : (flt(form.exchange_rate) || 1),
      items: qtItems, taxes,
      logo: resolvedLogoPath,
    };
    if (editingName.value) doc.name = editingName.value;
    const saved = await apiSave(doc);

    // Now that we have a docname, upload the pending logo and link it to the doc
    if (pendingDataUrl && saved?.name) {
      try {
        const [meta, b64] = pendingDataUrl.split(",");
        const mime = meta.match(/:(.*?);/)?.[1] || "image/png";
        const ext  = mime.split("/")[1]?.split("+")[0] || "png";
        const bytes = atob(b64);
        const arr = new Uint8Array(bytes.length);
        for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
        const blob = new Blob([arr], { type: mime });
        const fd = new FormData();
        fd.append("file", blob, `logo.${ext}`);
        fd.append("is_private", "0");
        fd.append("folder", "Home/Attachments");
        fd.append("doctype", "Quotation");
        fd.append("docname", saved.name);
        fd.append("fieldname", "logo");
        const res = await fetch("/api/method/upload_file", {
          method: "POST",
          headers: { "X-Frappe-CSRF-Token": window.csrf_token || frappe?.csrf_token || "" },
          body: fd,
        });
        const json = await res.json();
        const fileUrl = json?.message?.file_url || json?.file_url || "";
        if (fileUrl) {
          form.logo = fileUrl;
          logoUrl.value = fileUrl;
          // Patch logo on the already-saved doc so it persists
          await apiPOST("frappe.client.set_value", {
            doctype: "Quotation",
            name: saved.name,
            fieldname: "logo",
            value: fileUrl,
          });
        }
      } catch (uploadErr) {
        console.warn("Logo upload on save failed:", uploadErr);
        // Non-fatal: quote is saved, logo just won't persist
      }
    }

    if (newStatus === 'Sent' && saved?.name) {
      await apiSubmit("Quotation", saved.name);
      toast.success(`Quotation ${saved.name} submitted`);
      drawerOpen.value = false;
    } else if (andNew) {
      toast.success(`Quotation ${saved?.name || ""} saved — opening new quote`);
      openNew();
    } else {
      toast.success(`Quotation ${saved?.name || ""} saved`);
      drawerOpen.value = false;
    }
    await load();
  } catch (e) {
    toast.error(e.message || "Failed to save quotation");
  } finally {
    drawerSaving.value = false;
  }
}

// ── Actions ───────────────────────────────────────────────────────────
async function emailQT(q) {
  const ok = await openEmail({
    doctype: "Quotation", name: q.name, docLabel: `Quotation ${q.name}`,
    getDefaultsEndpoint: "zoho_books_clone.api.docs.get_quote_email_defaults",
    sendEndpoint: "zoho_books_clone.api.docs.send_quote_email",
    paramKey: "quotation_name",
    printConfig: { title: "QUOTATION", partyLabel: "Quote To", partyField: "customer_name" },
  });
  if (ok) await load();
}

async function markStatus(q, status) {
  if (!canWrite("invoices")) { toast("Read-only access", "error"); return; }
  const epMap = { Sent: "mark_quote_sent", Accepted: "mark_quote_accepted", Declined: "mark_quote_declined" };
  const ep = epMap[status];
  if (!ep) return;
  try {
    await apiPOST(`zoho_books_clone.api.docs.${ep}`, { quotation_name: q.name });
    toast.success(`Marked ${status}`);
    await load();
    if (viewDoc.value?.name === q.name) await openView(viewDoc.value);
  } catch (e) { toast.error(e.message || "Update failed"); }
}

function openConvertModal(q) {
  Object.assign(convertModal, {
    open: true, saving: false, qtName: q.name,
    target: "", deliveryDate: q.valid_till || todayStr(), dueDate: todayStr(),
  });
}
async function submitConvert() {
  if (!convertModal.target) return;
  convertModal.saving = true;
  try {
    const ep = convertModal.target === "SO"
      ? "zoho_books_clone.api.docs.convert_quote_to_sales_order"
      : "zoho_books_clone.api.docs.convert_quote_to_invoice";
    const payload = { quotation_name: convertModal.qtName };
    if (convertModal.target === "SO" && convertModal.deliveryDate) payload.delivery_date = convertModal.deliveryDate;
    if (convertModal.target === "Invoice" && convertModal.dueDate) payload.due_date = convertModal.dueDate;
    const r = await apiPOST(ep, payload);
    const created = r?.sales_order || r?.sales_invoice;
    toast.success(`Converted → ${convertModal.target === "SO" ? "Sales Order" : "Invoice"}: ${created}`);
    convertModal.open = false;
    await load();
    if (viewDoc.value?.name === convertModal.qtName) await openView(viewDoc.value);
  } catch (e) { toast.error(e.message || "Convert failed"); }
  convertModal.saving = false;
}

async function deleteQT(q) {
  if (!canWrite("invoices")) { toast("Read-only access", "error"); return; }
  if (!await confirm({ title: "Delete Quotation", body: `Permanently delete ${q.name}?`, okLabel: "Delete" })) return;
  try {
    await apiDelete("Quotation", q.name);
    toast.success("Quotation deleted");
    viewOpen.value = false;
    await load();
  } catch (e) { toast.error(e.message || "Delete failed"); }
}

async function submitFromView(q) {
  if (!q?.name) return;
  if (!await confirm({ title: "Submit Quotation", body: `Submit ${q.name}? It cannot be edited after submission.`, okLabel: "Submit", okStyle: "primary" })) return;
  viewSubmitting.value = true;
  try {
    await apiSubmit("Quotation", q.name);
    toast.success(`Quotation ${q.name} submitted`);
    await openView(q);
    await load();
  } catch (e) {
    toast.error(e.message || "Failed to submit quotation");
  } finally {
    viewSubmitting.value = false;
  }
}

async function cancelQT(q) {
  if (!canWrite("invoices")) { toast("Read-only access", "error"); return; }
  if (!q?.name) return;
  if (!await confirm({ title: 'Cancel Quotation', body: `Cancel ${q.name}? This will reverse the submission.`, okLabel: 'Cancel Quotation', okStyle: 'danger' })) return;
  viewCancelling.value = true;
  try {
    await apiCancel('Quotation', q.name);
    toast.success(`Quotation ${q.name} cancelled`);
    await openView(q);
    await load();
  } catch (e) {
    toast.error(e.message || 'Failed to cancel quotation');
  } finally {
    viewCancelling.value = false;
  }
}

// ── Bulk actions ──────────────────────────────────────────────────────
async function bulkDelete() {
  if (!canWrite("invoices")) { toast("Read-only access", "error"); return; }
  const drafts = sorted.value.filter(q => selected.value.has(q.name) && (q.status === "Draft" || !q.status));
  if (!drafts.length) { toast.info("No draft quotations selected"); return; }
  if (!await confirm({ title: "Delete Drafts", body: `Delete ${drafts.length} draft quotation(s)?`, okLabel: "Delete" })) return;
  for (const q of drafts) { try { await apiDelete("Quotation", q.name); } catch {} }
  selected.value = new Set();
  toast.success(`Deleted ${drafts.length} draft(s)`);
  await load();
}
async function bulkMarkSent() {
  if (!canWrite("invoices")) { toast("Read-only access", "error"); return; }
  const targets = sorted.value.filter(q => selected.value.has(q.name) && effectiveStatus(q) === "Draft");
  if (!targets.length) { toast.info("Select drafts to mark as sent"); return; }
  let done = 0;
  for (const q of targets) {
    try { await apiPOST("zoho_books_clone.api.docs.mark_quote_sent", { quotation_name: q.name }); done++; } catch {}
  }
  selected.value = new Set();
  toast.success(`Marked ${done} quote(s) as Sent`);
  await load();
}
async function bulkMarkExpired() {
  if (!canWrite("invoices")) { toast("Read-only access", "error"); return; }
  const targets = sorted.value.filter(q => selected.value.has(q.name));
  if (!targets.length) { toast.info("No quotes selected"); return; }
  try {
    await apiPOST("zoho_books_clone.api.docs.mark_quote_expired_bulk",
      { quotation_names: JSON.stringify(targets.map(q => q.name)) });
    selected.value = new Set();
    toast.success(`Marked ${targets.length} quote(s) as Expired`);
    await load();
  } catch (e) { toast.error(e.message || "Bulk expire failed"); }
}
async function bulkEmail() {
  if (!canWrite("invoices")) { toast("Read-only access", "error"); return; }
  const subs = sorted.value.filter(q => selected.value.has(q.name));
  if (!subs.length) { toast.info("No quotes selected"); return; }
  let sent = 0;
  for (const q of subs) {
    const ok = await openEmail({
      doctype: "Quotation", name: q.name, docLabel: `Quotation ${q.name}`,
      getDefaultsEndpoint: "zoho_books_clone.api.docs.get_quote_email_defaults",
      sendEndpoint: "zoho_books_clone.api.docs.send_quote_email",
      paramKey: "quotation_name",
      printConfig: { title: "QUOTATION", partyLabel: "Quote To", partyField: "customer_name" },
    });
    if (ok) sent++;
  }
  if (sent) { toast.success(`Emailed ${sent} quote(s)`); await load(); }
}

// ── Export CSV ────────────────────────────────────────────────────────
function exportCSV() {
  const rows = selected.value.size > 0
    ? sorted.value.filter(q => selected.value.has(q.name))
    : sorted.value;
  const head = ["Quote #","Customer","Date","Valid Till","Status","Amount"];
  const esc = v => `"${String(v ?? "").replace(/"/g,'""')}"`;
  const out = [head.map(esc).join(",")];
  for (const q of rows) {
    out.push([
      q.name, q.customer_name || q.customer,
      q.transaction_date, q.valid_till || "",
      effectiveStatus(q), Number(q.grand_total || 0).toFixed(2),
    ].map(esc).join(","));
  }
  const blob = new Blob(["﻿" + out.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `quotations_${todayStr()}.csv`;
  a.click(); URL.revokeObjectURL(url);
  toast.success(`CSV exported — ${rows.length} quote(s)`);
}

// ── Branding persistence ───────────────────────────────────────────────
async function loadBranding() {
  try {
    const csrf = window.frappe?.csrf_token || "";
    const res = await fetch("/api/method/zoho_books_clone.api.admin.get_company_settings", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded", "X-Frappe-CSRF-Token": csrf },
      credentials: "same-origin",
      body: new URLSearchParams({}),
    });
    const data = await res.json();
    const d = data.message || {};
    if (d.pdf_template) selectedTemplate.value = d.pdf_template;
    if (d.brand_color)  brandColor.value = d.brand_color;
    if (d.company_logo) logoUrl.value = d.company_logo;
  } catch {}
}

// ── Live preview ───────────────────────────────────────────────────────
const previewData = computed(() => ({
  name: editingName.value || "QT-PREVIEW",
  customer: form.customer,
  customer_name: customers.value.find(c => c.name === form.customer)?.customer_name || form.customer,
  transaction_date: form.transaction_date,
  valid_till: form.valid_till,
  title: form.title,
  billing_address: form.billing_address,
  currency: form.currency,
  items: lines.value.filter(l => l.item_code || l.item_name),
  taxes: taxLines.value.map(tl => ({ description: tl.template, rate: tl.rate, amount: tl.amount })),
  subtotal: subtotal.value,
  totalTax: taxAmount.value,
  grandTotal: grandTotal.value,
  terms: form.terms,
  company: window.__booksCompany || "",
}));

const previewHtml = computed(() =>
  renderDocument(_toPrintDoc(previewData.value), _qtCfg(previewData.value))
);

const showDownloadMenu = ref(false);

async function downloadQuotePdf(mode = 'pdf') {
  showDownloadMenu.value = false;
  if (!viewDoc.value?.name) return;
  // Pull the latest selected template from Company Settings before rendering.
  try { await refreshBranding(); } catch {}
  // Build the HTML the same way printQuote does, then download/print
  const doc = viewDoc.value;
  const data = {
    name: doc.name, customer: doc.customer,
    customer_name: doc.customer_name || doc.customer,
    transaction_date: doc.transaction_date, valid_till: doc.valid_till,
    title: doc.title || "", billing_address: doc.billing_address || doc.address_display || "",
    currency: doc.currency || "INR", items: doc.items || [], taxes: doc.taxes || [],
    subtotal: doc.net_total != null ? flt(doc.net_total) : flt(doc.grand_total) - flt(doc.total_tax),
    totalTax: flt(doc.total_tax), grandTotal: flt(doc.grand_total),
    terms: doc.terms || "", company: doc.company || window.__booksCompany || "",
  };
  const html = renderDocument(_toPrintDoc(data), _qtCfg(data));
  const blob = new Blob([html], { type: "text/html;charset=utf-8" });
  const objectUrl = URL.createObjectURL(blob);
  if (mode === 'print') {
    const win = window.open(objectUrl, "_blank");
    if (!win) { URL.revokeObjectURL(objectUrl); toast.error("Pop-up blocked — allow pop-ups to print"); return; }
    win.addEventListener("load", () => { try { win.focus(); win.print(); } catch {} });
  } else {
    const a = document.createElement("a");
    a.href = objectUrl;
    a.download = `${doc.name}.pdf`;
    a.click();
    URL.revokeObjectURL(objectUrl);
  }
}

function onDocClickForDownloadMenu(e) {
  if (!e.target.closest('.inv-ab-dropdown') && !e.target.closest('.inv-dl-menu')) {
    showDownloadMenu.value = false;
  }
}

async function printQuote(data) {
  try { await refreshBranding(); } catch {}
  if (data?.doctype === "Quotation" || data?.transaction_date) {
    const doc = data;
    data = {
      name: doc.name, customer: doc.customer,
      customer_name: doc.customer_name || doc.customer,
      transaction_date: doc.transaction_date, valid_till: doc.valid_till,
      title: doc.title || "", billing_address: doc.billing_address || doc.address_display || "",
      currency: doc.currency || "INR", items: doc.items || [], taxes: doc.taxes || [],
      subtotal: doc.net_total != null ? flt(doc.net_total) : flt(doc.grand_total) - flt(doc.total_tax),
      totalTax: flt(doc.total_tax), grandTotal: flt(doc.grand_total),
      terms: doc.terms || "", company: doc.company || window.__booksCompany || "",
    };
  }
  printDoc(_toPrintDoc(data), _qtCfg(data));
}

// ── Mount ─────────────────────────────────────────────────────────────
onMounted(async () => {
  document.addEventListener('click', onDocClickForDownloadMenu);
  await load();
  loadTaxAccount();
  loadBranding();
  try { setCompany(window.__booksCompany || await resolveCompany()); } catch {}
  fetchCustomers("");
  fetchItems("");
  (async () => { try { const r = await apiList("UOM", { fields: ["name"], order: "name asc", limit: 200 }); uomList.value = (r||[]).map(x=>x.name); } catch { uomList.value = ["Nos","Kg","Ltr","Mtr","Box","Pcs","Set","Dozen"]; } })();
  useOpenFromQuery({
    route,
    openByName: (n) => openView(list.value.find(r => r.name === n) || { name: n }),
  });
});
onUnmounted(() => document.removeEventListener('click', onDocClickForDownloadMenu));
</script>

<style>
@import '../styles/list.css';
@import '../styles/view.css';
@import '../styles/edit.css';
@import '../styles/add.css';

/* ── Readonly branding card (matches Invoices) ── */
.inv-brand-readonly { display: flex; flex-direction: column; gap: 12px; }
.inv-brand-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.inv-brand-lbl { font-size: 11px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: .5px; min-width: 90px; flex-shrink: 0; }
.inv-brand-tmpl-btns { display: flex; gap: 6px; flex-wrap: wrap; }
.inv-brand-tmpl-chip { display:inline-flex; align-items:center; gap:5px; padding:4px 10px; border-radius:6px; font-size:12px; font-weight:500; color:#6b7280; background:#f3f4f6; border:1px solid #e5e7eb; }
.inv-brand-tmpl-chip.active { background:#eff6ff; color:#2563eb; border-color:#bfdbfe; font-weight:600; }
.inv-brand-color-preview { display: flex; align-items: center; gap: 8px; }
.inv-brand-color-swatch { width: 20px; height: 20px; border-radius: 4px; border: 1px solid rgba(0,0,0,.1); flex-shrink: 0; }
.inv-brand-color-hex { font-size: 12px; font-weight: 600; color: #374151; }
.inv-brand-logo-preview { display: flex; align-items: center; }
.inv-brand-logo-thumb { height: 36px; max-width: 120px; object-fit: contain; border: 1px solid #e5e7eb; border-radius: 4px; padding: 2px; background: #fff; }
.inv-brand-logo-none { font-size: 12px; color: #9ca3af; font-style: italic; }
.inv-brand-settings-hint { font-size: 11.5px; color: #9ca3af; display: flex; align-items: center; gap: 5px; margin-top: 4px; }
.inv-brand-settings-link { color: #2563eb; text-decoration: none; font-weight: 500; }
.inv-brand-settings-link:hover { text-decoration: underline; }

/* ── Spin animation for logo upload ── */
@keyframes inv-spin { to { transform: rotate(360deg); } }
.inv-ab-submit { color:#2563eb !important; border-color:rgba(37,99,235,.3) !important; }
.inv-ab-submit:hover:not(:disabled) { background:#eff6ff !important; }
.inv-ab-submit:disabled { opacity:.55; cursor:not-allowed; }
.quote-cancel-btn { color: #d97706 !important; border-color: rgba(217,119,6,.3) !important; background: #fff; }
.quote-cancel-btn:hover:not(:disabled) { background: #fffbeb !important; }
.quote-cancel-btn:disabled { opacity: .55; cursor: not-allowed; }
.quote-delete-btn{color: #dc2626 !important;
    border-color: #dc262638;
    background: #fff;}
.quote-delete-lbl{    color: #dc2626;
    border-color: #dc262638;
    background: #fff;}
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
@media (max-width: 480px)   {
  .quote-delete-lbl{display: none !important;}
}
@media (max-width: 320px)   {
  .quote-delete-lbl{display: none !important;}
}

/* ── Mobile card view (Option A) ── */
.qt-mobile-cards { display: none; }
.qt-desktop-table { display: table; }

@media (max-width: 768px) {
  .qt-desktop-table { display: none !important; }
  .qt-mobile-cards { display: flex; flex-direction: column; gap: 0; background: #f8fafc; }
  .qt-mobile-card { background: #fff; border-bottom: 1px solid #e5e7eb; padding: 12px 14px; cursor: pointer; transition: background .12s; }
  .qt-mobile-card:active { background: #f8f9fc; }
  .qt-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .qt-mc-docno { font-size: 12px; font-weight: 700; color: #2563eb; }
  .qt-mc-mid { font-size: 13.5px; font-weight: 600; color: #1a1d23; margin-bottom: 4px; }
  .qt-mc-meta { display: flex; justify-content: space-between; font-size: 12px; color: #868e96; margin-bottom: 4px; }
  .qt-mc-amount { font-weight: 700; color: #1a1d23; }
  .qt-mc-sub { font-size: 11.5px; color: #868e96; margin-bottom: 8px; }
  .qt-mc-footer { display: flex; gap: 6px; margin-top: 8px; }
  .qt-mc-btn { flex: 1; padding: 6px 10px; border-radius: 7px; font-size: 12px; font-weight: 600; cursor: pointer; background: #f1f5f9; border: 1px solid #e2e8f0; color: #374151; }
  .qt-mc-danger { background: #fff1f2; border-color: #fecaca; color: #dc2626; }
  .qt-mc--skeleton { pointer-events: none; }
  .qt-mc-shimmer { border-radius: 6px; background: linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size: 200% 100%; animation: qt-shimmer 1.4s infinite; }
  @keyframes qt-shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
  .qt-mc-empty { text-align: center; padding: 32px 16px; color: #868e96; font-size: 13px; }
}
</style>