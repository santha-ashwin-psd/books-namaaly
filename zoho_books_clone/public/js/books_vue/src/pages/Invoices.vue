<template>
<div class="inv-page">

  <!-- ── Unified toolbar (matches e-Way Bills) ── -->
  <div class="sales-toolbar">
    <div class="sales-search">
      <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
      <input v-model="search" placeholder="Search invoices, customers, PO…" class="sales-search-input"/>
    </div>
    <div class="sales-pills">
      <button v-for="f in FILTERS" :key="f.key" class="sales-pill" :class="{ active: activeFilter===f.key, ['pill-'+f.key]: f.key!=='all' }" @click="activeFilter=f.key">
        {{ f.label }}<span v-if="f.key!=='all'" class="sales-pill-count">{{ counts[f.key] }}</span>
      </button>
    </div>
    <div class="sales-actions">
      <select v-model="filterCustomer" class="sales-select" title="Filter by customer">
        <option value="">All Customers</option>
        <option v-for="c in customers" :key="c.name" :value="c.name">{{ c.customer_name }}</option>
      </select>
      <select v-model="dateRange" class="sales-select" title="Date range">
        <option v-for="dr in DATE_RANGES" :key="dr.key" :value="dr.key">{{ dr.label }}</option>
      </select>
      <button class="sales-btn-ghost view-toggle-btn" @click="viewMode=viewMode==='table'?'grid':'table'" :title="viewMode==='table'?'Grid View':'List View'"><span v-html="icon(viewMode==='table'?'grid':'file',14)"></span></button>
      <button class="sales-btn-ghost" @click="exportCSV" title="Export CSV"><span v-html="icon('download',14)"></span> CSV</button>
      <button class="sales-btn-ghost" @click="load" title="Refresh" :disabled="loading"><span v-html="icon('refresh',14)"></span></button>
      <button class="sales-btn-primary" @click="openAdd" :disabled="!$canCreate('invoices')" :title="!$canCreate('invoices') ? 'Read-only access' : ''">
        <span v-html="icon('plus',13)"></span> New Invoice
      </button>
    </div>
  </div>

  <!-- Custom-date inputs surface below toolbar only when needed -->
  <div v-if="dateRange==='custom'" class="sales-custom-date">
    <span style="font-size:12px;color:#6b7280;font-weight:600">Date range:</span>
    <input type="date" v-model="customFrom" class="sales-date-input"/>
    <span style="color:#9ca3af;font-size:12px">to</span>
    <input type="date" v-model="customTo" class="sales-date-input"/>
  </div>

  <!-- ── KPI Cards ── -->
  <div class="bk-kpi-grid">
    <div class="bk-kpi-card bk-kpi-accent clickable" @click="activeFilter='all'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#dbeafe"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.8"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/></svg></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Total Invoices</div>
          <div class="bk-kpi-value">{{ list.length }}</div>
          <div class="bk-kpi-trend" :class="invTrends.total.up?'bk-trend-up':'bk-trend-down'">{{ invTrends.total.up?'↑':'↓' }} {{ invTrends.total.pct }}% vs last month</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card clickable" @click="activeFilter='Draft'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#e2e8f0"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="1.8"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Draft</div>
          <div class="bk-kpi-value">{{ counts.Draft }}</div>
          <div class="bk-kpi-trend" :class="invTrends.draft.up?'bk-trend-up':'bk-trend-down'">{{ invTrends.draft.up?'↑':'↓' }} {{ invTrends.draft.pct }}% vs last month</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card bk-kpi-warn clickable" @click="activeFilter='Unpaid'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#fef3c7"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Unpaid</div>
          <div class="bk-kpi-value bk-kpi-amber">{{ counts.Unpaid }}</div>
          <div class="bk-kpi-trend" :class="invTrends.unpaid.up?'bk-trend-up':'bk-trend-down'">{{ invTrends.unpaid.up?'↑':'↓' }} {{ invTrends.unpaid.pct }}% vs last month</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card bk-kpi-danger clickable" @click="activeFilter='Overdue'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#fee2e2"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="1.8"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Overdue</div>
          <div class="bk-kpi-value bk-kpi-red">{{ counts.Overdue }}</div>
          <div class="bk-kpi-trend" :class="invTrends.overdue.up?'bk-trend-down':'bk-trend-up'">{{ invTrends.overdue.up?'↑':'↓' }} {{ invTrends.overdue.pct }}% vs last month</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card bk-kpi-success clickable" @click="activeFilter='Paid'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#dcfce7"><svg width="22" height="22" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="#16a34a" stroke-width="1.8"/><polyline points="7 12.5 10.5 16 17 9" stroke="#16a34a" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Paid</div>
          <div class="bk-kpi-value bk-kpi-green">{{ counts.Paid }}</div>
          <div class="bk-kpi-trend" :class="invTrends.paid.up?'bk-trend-up':'bk-trend-down'">{{ invTrends.paid.up?'↑':'↓' }} {{ invTrends.paid.pct }}% vs last month</div>
        </div>
      </div>
    </div>
  </div>
  <!-- Secondary stats -->
  <div class="bk-stat-grid inv-mobile-summary">
    <div class="bk-stat-card inv-stat-count"><div class="bk-stat-content"><div><div class="bk-stat-label">This Month</div><div class="bk-stat-value">{{ invThisMonth.count }}</div></div><div class="bk-stat-icon" style="background:#dbeafe;color:#2563eb"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg></div></div></div>
    <div class="bk-stat-card inv-stat-revenue"><div class="bk-stat-content"><div><div class="bk-stat-label">This Month Revenue</div><div class="bk-stat-value" style="font-size:16px">{{ fmtAmt(invThisMonth.revenue) }}</div></div><div class="bk-stat-icon" style="background:#dcfce7;color:#16a34a"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12"/><path d="M6 8h12"/><path d="m6 13 8.5 8"/><path d="M6 13h3"/><path d="M9 13c6.667 0 6.667-10 0-10"/></svg></div></div></div>
    <div class="bk-stat-card inv-stat-receivable"><div class="bk-stat-content"><div><div class="bk-stat-label">Total Receivable</div><div class="bk-stat-value bk-kpi-amber" style="font-size:16px">{{ fmtAmt(summary.totalDue) }}</div></div><div class="bk-stat-icon" style="background:#fef3c7;color:#d97706"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg></div></div></div>
    <div class="bk-stat-card inv-stat-average"><div class="bk-stat-content"><div><div class="bk-stat-label">Avg Invoice Value</div><div class="bk-stat-value" style="font-size:16px">{{ fmtAmt(invAvg) }}</div></div><div class="bk-stat-icon" style="background:#e5e7eb;color:#6b7280"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg></div></div></div>
  </div>

  <!-- ── Bulk actions bar ── -->
  <div v-if="selectedRows.size>0" class="inv-bulk-bar">
    <span class="inv-bulk-count">{{ selectedRows.size }} selected</span>
    <button class="inv-bulk-btn inv-bulk-pay" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="bulkPayment">₹ Record Payment</button>
    <button class="inv-bulk-btn" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="bulkEmail"><span v-html="icon('mail',13)"></span> Send Email</button>
    <button class="inv-bulk-btn" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="bulkCancel">Cancel Submitted</button>
    <button class="inv-bulk-btn inv-bulk-danger" :disabled="!$canDelete('invoices')" :title="!$canDelete('invoices') ? 'Not permitted' : ''" @click="bulkDelete">Delete Drafts</button>
    <button class="inv-bulk-btn" @click="exportCSV"><span v-html="icon('download',13)"></span> Export CSV</button>
    <button class="inv-bulk-clear" @click="selectedRows=new Set()">✕ Clear</button>
  </div>

  <!-- ── Table ── -->
  <div class="inv-table-wrap">
    <template v-if="viewMode==='table'">
    <table class="inv-table inv-desktop-table">
      <thead><tr>
        <th class="th-check"><input type="checkbox" @change="toggleAll" :checked="allSelected"/></th>
        <th class="sortable" @click="sort('posting_date')">DATE <span class="sort-arrow">{{ sortArrow('posting_date') }}</span></th>
        <th class="sortable" @click="sort('name')">INVOICE# <span class="sort-arrow">{{ sortArrow('name') }}</span></th>
        <th class="sortable" @click="sort('customer_name')">CUSTOMER <span class="sort-arrow">{{ sortArrow('customer_name') }}</span></th>
        <th class="sortable" @click="sort('due_date')">DUE DATE <span class="sort-arrow">{{ sortArrow('due_date') }}</span></th>
        <th class="sortable" @click="sort('status')">STATUS <span class="sort-arrow">{{ sortArrow('status') }}</span></th>
        <th class="ta-r sortable" @click="sort('grand_total')">AMOUNT <span class="sort-arrow">{{ sortArrow('grand_total') }}</span></th>
        <th class="ta-r sortable" @click="sort('outstanding_amount')">BALANCE DUE <span class="sort-arrow">{{ sortArrow('outstanding_amount') }}</span></th>
        <th style="width:80px;text-align:center">ACTIONS</th>
      </tr></thead>
      <tbody>
        <template v-if="loading">
          <tr v-for="n in 7" :key="n" class="shimmer-row">
            <td><div class="shimmer" style="width:14px;height:14px;border-radius:3px"></div></td>
            <td><div class="shimmer" style="width:80px"></div></td>
            <td><div class="shimmer" style="width:110px"></div></td>
            <td><div class="shimmer" style="width:130px"></div></td>
            <td><div class="shimmer" style="width:90px"></div></td>
            <td><div class="shimmer" style="width:80px"></div></td>
            <td><div class="shimmer" style="width:80px;margin-left:auto"></div></td>
            <td><div class="shimmer" style="width:80px;margin-left:auto"></div></td>
            <td></td>
          </tr>
        </template>
        <template v-else>
          <tr v-for="inv in paged" :key="inv.name" class="inv-row" :class="{ selected: selectedRows.has(inv.name) }">
            <td class="td-check" @click.stop>
              <input type="checkbox" :checked="selectedRows.has(inv.name)" @change="toggleRow(inv.name)"/>
            </td>
            <td @click="openView(inv)" class="text-muted mono-sm">{{ fmtDate(inv.posting_date) }}</td>
            <td @click="openView(inv)"><DocLink doctype="Sales Invoice" :name="inv.name" /></td>
            <td @click="openView(inv)"><span class="inv-customer">{{ inv.customer_name||inv.customer }}</span></td>
            <td @click="openView(inv)" :class="isOverdue(inv)?'text-danger':'text-muted'" class="mono-sm">{{ fmtDate(inv.due_date) }}</td>
            <td @click="openView(inv)">
              <span class="inv-status-badge" :class="statusCls(inv)">{{ statusLabel(inv) }}</span>
              <span v-if="inv.docstatus===1 && inv.customer_gstin && !inv.is_return"
                class="ei-status-dot"
                :class="inv.irn && inv.einvoice_status!=='Cancelled' ? 'ei-dot-green' : inv.einvoice_status==='Cancelled' ? 'ei-dot-grey' : 'ei-dot-orange'"
                :title="inv.irn && inv.einvoice_status!=='Cancelled' ? 'e-Invoice: IRN Generated' : inv.einvoice_status==='Cancelled' ? 'e-Invoice: Cancelled' : 'e-Invoice: IRN Pending'">
              </span>
            </td>
            <td class="ta-r mono-sm" @click="openView(inv)">{{ fmtAmt(inv.grand_total) }}</td>
            <td class="ta-r mono-sm" @click="openView(inv)" :class="inv.outstanding_amount>0?'text-danger':'text-success'">
              {{ fmtAmt(inv.outstanding_amount) }}
            </td>
            <td style="text-align:center" @click.stop>
              <div class="inv-row-actions" style="display:flex;gap:4px;justify-content:center">
                <button class="inv-act-btn" @click="openView(inv)" title="View"><span v-html="icon('eye',13)"></span></button>
                <button v-if="inv.docstatus===0" class="inv-act-btn" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : 'Edit'" @click="openEdit(inv)"><span v-html="icon('edit',13)"></span></button>
                <button v-if="inv.docstatus===0||inv.docstatus===2" class="inv-act-btn" style="color:#dc2626" :disabled="!$canDelete('invoices')" :title="!$canDelete('invoices') ? 'Not permitted' : 'Delete'" @click.stop="confirmAction('delete',inv)"><span v-html="icon('trash',13)"></span></button>
                <button v-if="inv.outstanding_amount>0&&inv.docstatus===1" class="inv-act-btn inv-act-pay" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : 'Record Payment'" @click="openPayment(inv)">₹</button>
              </div>
            </td>
          </tr>
          <tr v-if="!sorted.length">
            <td colspan="10" class="bk-empty-state">
              <div class="bk-empty-inner">
                <template v-if="search||filterCustomer">
                  <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.3"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                  <p class="bk-empty-title">No invoices match your filters</p>
                </template>
                <template v-else>
                  <div class="bk-empty-illus"><svg width="80" height="96" viewBox="0 0 80 96" fill="none"><rect x="10" y="8" width="60" height="80" rx="6" fill="#e2e8f0"/><rect x="14" y="12" width="52" height="72" rx="4" fill="#fff"/><rect x="22" y="26" width="36" height="3" rx="2" fill="#e2e8f0"/><rect x="22" y="34" width="28" height="3" rx="2" fill="#e2e8f0"/><rect x="22" y="42" width="32" height="3" rx="2" fill="#e2e8f0"/><rect x="22" y="58" width="20" height="3" rx="2" fill="#e2e8f0"/><rect x="22" y="66" width="24" height="3" rx="2" fill="#e2e8f0"/><rect x="8" y="22" width="20" height="20" rx="4" fill="#2563eb" opacity=".85"/><line x1="13" y1="32" x2="23" y2="32" stroke="#fff" stroke-width="2" stroke-linecap="round"/><line x1="18" y1="27" x2="18" y2="37" stroke="#fff" stroke-width="2" stroke-linecap="round"/></svg></div>
                  <p class="bk-empty-title">No invoices created yet</p>
                  <p class="bk-empty-sub">Create your first invoice to start tracking payments and revenue.</p>
                  <button class="bk-empty-btn" :disabled="!$canCreate('invoices')" @click="openAdd"><span v-html="icon('plus',13)"></span> New Invoice</button>
                </template>
              </div>
            </td>
          </tr>
        </template>
      </tbody>
    </table>

    <!-- Mobile cards (shown at ≤768px, hidden on desktop) -->
    <div class="inv-mobile-cards">
      <template v-if="loading">
        <div v-for="n in 5" :key="n" class="inv-mobile-card inv-mc--skeleton">
          <div class="inv-mc-shimmer" style="height:13px;width:55%;margin-bottom:8px"></div>
          <div class="inv-mc-shimmer" style="height:11px;width:40%;margin-bottom:6px"></div>
          <div class="inv-mc-shimmer" style="height:11px;width:65%"></div>
        </div>
      </template>
      <div v-else-if="!sorted.length" class="inv-mc-empty">
        <div style="font-size:32px;margin-bottom:8px">📄</div>
        <div>No invoices found</div>
      </div>
      <template v-else>
        <div v-for="inv in paged" :key="inv.name" class="inv-mobile-card" @click="openView(inv)">
          <div class="inv-mc-top">
            <span class="inv-mc-docno">{{ inv.name }}</span>
            <span class="inv-status-badge" :class="statusCls(inv)">{{ statusLabel(inv) }}</span>
          </div>
          <div class="inv-mc-mid">{{ inv.customer_name || inv.customer }}</div>
          <div class="inv-mc-meta">
            <span>{{ fmtDate(inv.posting_date) }}</span>
            <span class="inv-mc-amount">{{ fmtAmt(inv.grand_total) }}</span>
          </div>
          <div v-if="inv.outstanding_amount > 0" class="inv-mc-balance">
            Due: {{ fmtDate(inv.due_date) }} · Balance: <span :class="isOverdue(inv)?'text-danger':''">{{ fmtAmt(inv.outstanding_amount) }}</span>
          </div>
          <div class="inv-mc-footer">
            <button class="inv-mc-btn" @click.stop="openView(inv)">View</button>
            <button v-if="inv.docstatus===0" class="inv-mc-btn" :disabled="!$canEdit('invoices')" @click.stop="openEdit(inv)">Edit</button>
            <button v-if="inv.outstanding_amount>0&&inv.docstatus===1" class="inv-mc-btn inv-mc-pay" :disabled="!$canEdit('invoices')" @click.stop="openPayment(inv)">Pay</button>
            <button v-if="inv.docstatus===0||inv.docstatus===2" class="inv-mc-btn inv-mc-danger" :disabled="!$canDelete('invoices')" @click.stop="confirmAction('delete',inv)">Delete</button>
          </div>
        </div>
      </template>
    </div>
    </template>
      <!-- GRID MODE (desktop card view) -->
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
            <div style="font-size:32px;margin-bottom:8px">📄</div>
            <div>{{ search || filterCustomer ? 'No invoices match your filters' : 'No invoices yet' }}</div>
            <button v-if="!search && !filterCustomer" class="nim-btn nim-btn-primary" :disabled="!$canCreate('invoices')" :title="!$canCreate('invoices') ? 'Read-only access' : ''" style="margin-top:14px" @click="openAdd"><span v-html="icon('plus',13)"></span> New Invoice</button>
          </div>
          <template v-else>
            <div v-for="inv in paged" :key="inv.name"
              class="b-card b-card-body"
              style="cursor:pointer;padding:16px;display:flex;flex-direction:column;gap:8px"
              @click="openView(inv)">
              <div style="display:flex;align-items:center;justify-content:space-between;gap:8px">
                <span style="font-size:12px;font-weight:700;color:#2563eb">{{ inv.name }}</span>
                <span class="inv-status-badge" :class="statusCls(inv)">{{ statusLabel(inv) }}</span>
              </div>
              <div style="font-size:13.5px;font-weight:600;color:#1a1d23;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ inv.customer_name || inv.customer }}</div>
              <div style="display:flex;justify-content:space-between;font-size:12px;color:#6b7280">
                <span>{{ fmtDate(inv.posting_date) }}</span>
                <span style="font-weight:700;color:#1a1d23">{{ fmtAmt(inv.grand_total) }}</span>
              </div>
              <div v-if="inv.outstanding_amount > 0" style="font-size:11.5px;color:#dc2626">
                Balance: {{ fmtAmt(inv.outstanding_amount) }}
              </div>
              <div style="display:flex;gap:6px;border-top:1px solid #f3f4f6;padding-top:10px">
                <button class="inv-act-btn" @click.stop="openView(inv)" title="View"><span v-html="icon('eye',13)"></span></button>
                <button v-if="inv.docstatus===0" class="inv-act-btn" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : 'Edit'" @click.stop="openEdit(inv)"><span v-html="icon('edit',13)"></span></button>
                <button v-if="inv.outstanding_amount>0&&inv.docstatus===1" class="inv-act-btn inv-act-pay" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : 'Record Payment'" @click.stop="openPayment(inv)">₹</button>
                <button v-if="inv.docstatus===0||inv.docstatus===2" class="inv-act-btn" style="color:#dc2626" :disabled="!$canDelete('invoices')" :title="!$canDelete('invoices') ? 'Not permitted' : 'Delete'" @click.stop="confirmAction('delete',inv)"><span v-html="icon('trash',13)"></span></button>
              </div>
            </div>
          </template>
        </div>
      </template>
  </div>
  <div v-if="!loading && sorted.length" style="padding:12px 0px 4px">
    <Pagination
      v-model:page="page"
      v-model:page-size="pageSize"
      :total-items="sorted.length"
    />
  </div>

  <!-- ══ Modals / Drawers ══ -->
  <Teleport to="body">

    <!-- ── Create / Edit Drawer ── -->
    <div v-if="drawerOpen" class="inv-drawer-bg inv-addedit-bg" @click.self="!editingName ? null : drawerOpen=false">
      <div class="inv-drawer-panel inv-new-drawer inv-addedit-panel" :class="{'inv-split':showPreview, 'is-add':!editingName}">

        <!-- ── Header ── -->
        <div class="inv-dh">
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
            <div class="inv-dh-title">{{ editingName ? 'Edit Invoice' : 'New Invoice' }}</div>
            <span v-if="!editingName" class="add-status-badge">Draft</span>
            <span v-if="!editingName" class="add-autosave-notice">
              <span class="add-autosave-dot"></span>
            </span>
          </div>
          <div style="display:flex;align-items:center;gap:8px">
            <button class="inv-preview-toggle" @click="showPreview=!showPreview" :title="showPreview?'Hide preview':'Live preview'">
              <span v-html="icon('eye',13)"></span> {{ showPreview ? 'Hide' : 'Preview' }}
            </button>
            <button class="inv-dclose" @click="drawerOpen=false"><span v-html="icon('x',16)"></span></button>
          </div>
        </div>

        <!-- ── Content row: form + optional preview ── -->
        <div class="inv-content-row">
        <div class="inv-dbody" style="padding:5px;">

          <!-- ══ CARD 2: Invoice Details ══ -->
          <div class="add-card">
            <div class="add-card-header" @click="collapsed.details=!collapsed.details">
              <div class="add-card-title">
                <span class="add-card-title-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></span>
                Invoice Details
              </div>
              <span class="add-card-chevron" :class="{collapsed:collapsed.details}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
              </span>
            </div>
            <div class="add-card-body" :class="{collapsed:collapsed.details}">
              <!-- Row 1: Customer (wide) | Invoice Date | Valid Till -->
              <div class="add-details-grid">
                <div>
                  <label class="inv-lbl">Customer <span class="inv-req">*</span></label>
                  <SearchableSelect v-model="form.customer" :options="customers"
                    placeholder="Select customer"
                    :createable="true" createDoctype="Customer"
                    @update:modelValue="onCustomerChange"/>
                </div>
                <div>
                  <label class="inv-lbl">Invoice Date <span class="inv-req">*</span></label>
                  <input v-model="form.posting_date" type="date" class="inv-fi"/>
                </div>
                <div>
                  <label class="inv-lbl">Due Date</label>
                  <input v-model="form.due_date" type="date" class="inv-fi"/>
                </div>
              </div>
              <!-- Lower section: field rows on the left, inventory toggle card on the right -->
              <div class="inv-details-lower">
                <div class="inv-details-lower-main">
                  <!-- Row 2: Title / Project | Payment Terms | Cost Center | Price List -->
                  <div class="inv-details-row2-4col">
                    <div>
                      <label class="inv-lbl">Title / Project</label>
                      <input v-model="form.po_no" class="inv-fi" placeholder="Project name or short description"/>
                    </div>
                    <div>
                      <label class="inv-lbl">Payment Terms</label>
                      <select v-model="form.payment_terms" class="inv-fi" @change="applyPaymentTerms">
                        <option value="">— Select Payment Terms —</option>
                        <option v-for="t in PAYMENT_TERMS" :key="t" :value="t">{{ t }}</option>
                      </select>
                    </div>
                    <div>
                      <label class="inv-lbl">Cost Center</label>
                      <select v-model="form.cost_center" class="inv-fi">
                        <option value="">— Select —</option>
                        <option v-for="cc in costCenters" :key="cc" :value="cc">{{ cc }}</option>
                      </select>
                    </div>
                    <div>
                      <label class="inv-lbl">Price List</label>
                      <select v-model="form.price_list" class="inv-fi" @change="onPriceListChange(form.price_list)">
                        <option value="">Select price list (optional)</option>
                        <option v-for="pl in priceLists" :key="pl.value" :value="pl.value">{{ pl.label }}</option>
                      </select>
                    </div>
                  </div>
                  <!-- Sales Person | Place of supply -->
                  <div class="inv-details-2col">
                    <div>
                      <label class="inv-lbl">Sales Person</label>
                      <SearchableSelect v-model="form.sales_person" :options="salesPersons"
                        placeholder="Select sales person"/>
                    </div>
                    <div>
                      <label class="inv-lbl">Place of Supply</label>
                      <div v-if="isOverseas" class="inv-fi" style="background:#dbeafe;color:#1d4ed8;font-size:12px;display:flex;align-items:center;gap:6px;padding:8px 10px;border-color:#bfdbfe">
                        <span>🌐</span> Outside India — Not applicable for export invoices
                      </div>
                      <select v-else v-model="form.place_of_supply" class="inv-fi">
                        <option value="">— Select State —</option>
                        <option v-for="s in INDIAN_STATES" :key="s" :value="s">{{ s }}</option>
                      </select>
                    </div>
                  </div>
                </div>
                <!-- Inventory card — stock is always deducted on submit; warehouse is mandatory -->
                <div class="inv-details-toggle-col">
                  <div class="inv-inv-block inv-on">
                    <div class="inv-inv-toggle-row">
                      <div class="inv-inv-icon" v-html="icon('box',16)"></div>
                      <div class="inv-inv-text">
                        <div class="inv-inv-title">Deduct Inventory on Submit</div>
                        <div class="inv-inv-sub">Stock reduces from the selected warehouse when this invoice is submitted</div>
                      </div>
                    </div>
                    <div class="inv-inv-wh-row">
                      <label class="inv-lbl" style="margin-bottom:6px">Dispatch Warehouse <span style="color:#dc2626">*</span></label>
                      <SearchableSelect v-model="form.set_warehouse" :options="warehouses" placeholder="Select warehouse stock will be dispatched from…" @search="fetchWarehouses" />
                    </div>
                  </div>
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
                <button v-if="form.customer" class="inv-add-line-btn inv-copy-btn" @click="copyLastItems" title="Copy items from last invoice">
                  <span v-html="icon('copy',12)"></span> Copy Last
                </button>
                <button class="add-lines-add-btn inv-scan-btn" @click="openScanCamera" title="Scan a barcode to add an item">
                  <span v-html="icon('qr',13)"></span> Scan Barcode
                </button>
                <button class="add-lines-add-btn" @click="addLine">
                  <span v-html="icon('plus',13)"></span> Add Item
                </button>
                <span class="add-card-chevron" :class="{collapsed:collapsed.lines}" @click="collapsed.lines=!collapsed.lines">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
                </span>
              </div>
            </div>
            <div class="add-card-body" :class="{collapsed:collapsed.lines}" style="padding:16px 16px 8px">

              <!-- Export/SEZ notices -->
              <div v-if="isOverseas" style="background:#dbeafe;border:1px solid #bfdbfe;border-radius:6px;padding:10px 14px;margin-bottom:12px;font-size:12.5px;color:#1e40af;display:flex;align-items:flex-start;gap:8px">
                <span style="font-size:15px;flex-shrink:0">🌐</span>
                <div><strong>Export Invoice — Zero Rated Supply</strong><br/>GST is not applicable on exports. Ensure you have a valid LUT or pay IGST and claim refund.</div>
              </div>
              <div v-else-if="isSEZ" style="background:#f3f0ff;border:1px solid #c4b5fd;border-radius:6px;padding:10px 14px;margin-bottom:12px;font-size:12.5px;color:#4c1d95;display:flex;align-items:flex-start;gap:8px">
                <span style="font-size:15px;flex-shrink:0">🏭</span>
                <div><strong>SEZ Supply — Zero Rated</strong><br/>Apply IGST @ 0% or supply under LUT/Bond without payment of tax.</div>
              </div>

              <div class="po-items-table-wrap">
                <table class="po-items-table">
                  <thead>
                    <tr>
                      <th class="th-num">#</th>
                      <th class="th-item">ITEM NAME &amp; DESCRIPTION</th>
                      <th class="th-hsn">HSN/SAC</th>
                      <th class="th-uom">UOM</th>
                      <th class="th-mrp">MRP ({{ currencySymbol }})</th>
                      <th class="th-qty">QTY</th>
                      <th class="th-rate">RATE ({{ currencySymbol }})</th>
                      <th class="th-disc">DISC %</th>
                      <th class="th-tax">TAX TEMPLATE</th>
                      <th class="th-batch">BATCH NO</th>
                      <th class="th-expiry">EXP DATE</th>
                      <th class="th-subtotal">SUBTOTAL</th>
                      <th class="th-rm"></th>
                    </tr>
                  </thead>
                  <tbody>
                    <template v-for="(line, idx) in lines" :key="line.id">
                    <tr class="po-items-row">
                      <td class="td-num"><span class="po-row-num">#{{ idx + 1 }}</span></td>
                      <td class="td-item">
                        <SearchableSelect v-model="line.item_code" :options="items"
                          placeholder="Search item or service"
                          :createable="true" createDoctype="Item"
                          @update:modelValue="onItemChange(line)"/>
                        <!-- <textarea v-model="line.description" class="inv-fi po-row-desc-ta" rows="2" maxlength="500" placeholder="Enter item description…"></textarea>
                        <div class="exp-field-hint" :class="{'exp-field-hint-err': (line.description||'').length >= 500}">{{ (line.description||'').length }}/500</div> -->
                      </td>
                      <td class="td-hsn" data-label="HSN/SAC"><input v-model="line.hsn_code" class="inv-fi" placeholder="HSN code"/></td>
                      <td class="td-uom" data-label="UOM">
                        <select v-model="line.uom" class="inv-fi">
                          <option v-for="u in uomList" :key="u" :value="u">{{ u }}</option>
                        </select>
                      </td>
                      <td class="td-mrp" data-label="MRP"><input :value="fmtN(line._standardRate)" type="text" readonly disabled class="inv-fi" style="background:#f3f4f6;color:#6b7280;cursor:not-allowed"/></td>
                      <td class="td-qty" data-label="Qty"><input v-model.number="line.qty" type="number" min="0.001" step="0.001" class="inv-fi" @input="onLineQtyChange(line)"/></td>
                      <td class="td-rate" data-label="Rate"><input v-model.number="line.rate" type="number" min="0" step="0.01" class="inv-fi" @input="calcLine(line)"/></td>
                      <td class="td-disc" data-label="Disc %"><input v-model.number="line.discount_percentage" type="number" min="0" max="100" step="0.1" class="inv-fi" @input="calcLine(line)" placeholder="0"/></td>
                      <td class="td-tax" data-label="Tax">
                        <select v-model="line.tax_code" class="inv-fi">
                          <option value="">— No Tax —</option>
                          <option v-for="t in taxTemplates" :key="t.name" :value="t.name">{{ t.template_name || t.name }}</option>
                        </select>
                      </td>
                      <td class="td-batch" data-label="Batch No">
                        <template v-if="line.has_batch_no">
                          <SearchableSelect v-model="line.batch_no" :options="line.batchOptions" placeholder="Select batch"
                            @search="q => fetchLineBatches(line, q)" @select="opt => onLineBatchSelect(line, opt)" style="font-size:12px"
                            :title="batchQtyError(line) || (!line.batchOptions.length ? 'No batches with stock yet' : '')"/>
                        </template>
                        <span v-else style="color:#cbd5e1;font-size:12px">—</span>
                      </td>
                      <td class="td-expiry" data-label="Exp Date">
                        <span v-if="line.has_batch_no && line.batch_no && line.batch_expiry_date" style="font-size:12px;color:#374151">{{ fmtDate(line.batch_expiry_date) }}</span>
                        <span v-else style="color:#cbd5e1;font-size:12px">—</span>
                      </td>
                      <td class="td-availqty" style="display:none;">
                        <span v-if="line.has_batch_no && line.batch_no && line._batchQty!=null" style="font-size:12px;color:#374151">{{ line._batchQty }}</span>
                        <span v-else style="color:#cbd5e1;font-size:12px">—</span>
                      </td>
                      <td class="td-subtotal" data-label="Subtotal">
                        <span class="po-row-subtotal-label">SUBTOTAL</span>
                        <span class="po-row-subtotal-amt">{{ fmtAmt(line.amount) }}</span>
                        <span v-if="lineTaxBreakup(line).length" class="po-row-subtotal-total">Total: {{ fmtAmt(lineAmountWithTax(line)) }}</span>
                      </td>
                      <td class="td-rm"><button @click="removeLine(line.id)" class="po-item-card-rm"><span v-html="icon('x',16)"></span></button></td>
                    </tr>
                    <tr v-if="line.has_batch_no && batchQtyError(line)" class="po-items-error-row">
                      <td colspan="14"><div class="po-items-banner-inner"><span v-html="icon('alert-circle',12)"></span> {{ batchQtyError(line) }}</div></td>
                    </tr>
                    <tr v-else-if="line.has_batch_no && !line.batchOptions.length" class="po-items-warn-row">
                      <td colspan="14"><div class="po-items-banner-inner"><span v-html="icon('alert-circle',12)"></span> No batches with stock yet for this item</div></td>
                    </tr>
                    </template>
                  </tbody>
                </table>
              </div>

              <button class="inv-add-line-btn" style="margin-top:12px" @click="addLine">
                <span v-html="icon('plus',12)"></span> Add Item
              </button>

              <!-- Totals -->
              <div class="po-totals" style="margin-top:16px">
                <div style="font-size:12px;color:#6b7280">Tax is applied per item via Tax Template.</div>
                <div class="po-totals-right">
                  <div class="po-total-row"><span>Subtotal</span><span>{{ fmtAmt(subtotal) }}</span></div>
                  <div class="po-total-row" style="align-items:center">
                    <span>Discount</span>
                    <span style="display:flex;gap:6px;align-items:center;justify-content:flex-end">
                      <select v-model="form.discount_type" class="inv-fi" style="width:74px;padding:2px 4px">
                        <option value="Percentage">%</option>
                        <option value="Amount">₹</option>
                      </select>
                      <input
                        v-if="form.discount_type==='Percentage'"
                        v-model.number="form.additional_discount_percentage"
                        type="number" min="0" max="100" step="0.1"
                        class="inv-fi" style="width:72px;text-align:right" placeholder="0"
                      />
                      <input
                        v-else
                        v-model.number="form.additional_discount_amount"
                        type="number" min="0" :max="subtotal" step="0.01"
                        class="inv-fi" style="width:90px;text-align:right" placeholder="0"
                      />
                    </span>
                  </div>
                  <div v-if="discountAmount" class="po-total-row"><span>Discount Amount</span><span>-{{ fmtAmt(discountAmount) }}</span></div>
                  <div class="po-total-row"><span>Net Total</span><span>{{ fmtAmt(netTotal) }}</span></div>
                  <template v-for="tl in taxLines" :key="tl.template">
                    <div class="po-total-row"><span>{{ tl.template }} ({{ tl.rate }}%)</span><span>{{ fmtAmt(tl.amount) }}</span></div>
                  </template>
                  <div v-if="!taxLines.length" class="po-total-row"><span>Tax</span><span>{{ fmtAmt(0) }}</span></div>
                  <div v-if="roundOff" class="po-total-row"><span>Round Off</span><span>{{ roundOff>0?'+':'' }}{{ fmtAmt(roundOff) }}</span></div>
                  <div class="po-total-row grand"><span>Grand Total</span><span>{{ fmtAmt(grandTotal) }}</span></div>
                </div>
              </div>

              <!-- Add notes link -->
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
                  <label class="inv-lbl">Customer Note <span style="color:#9ca3af;font-weight:400">(printed on invoice)</span></label>
                  <textarea v-model="form.terms" class="inv-fi" rows="3" maxlength="500" placeholder="Visible to customer on the invoice…"></textarea>
                  <div class="exp-field-hint" :class="{'exp-field-hint-err': (form.terms||'').length >= 500}">{{ (form.terms||'').length }}/500 characters</div>
                </div>
                <div>
                  <label class="inv-lbl">Internal Remarks <span style="color:#9ca3af;font-weight:400">(not printed)</span></label>
                  <textarea v-model="form.remarks" class="inv-fi" rows="3" maxlength="500" placeholder="Internal notes for your team…"></textarea>
                  <div class="exp-field-hint" :class="{'exp-field-hint-err': (form.remarks||'').length >= 500}">{{ (form.remarks||'').length }}/500 characters</div>
                </div>
              </div>
              <!-- Save As status selector -->
              <div style="margin-top:14px;max-width:320px">
                <label class="inv-lbl">Save As</label>
                <select v-model="form.docstatus" class="inv-fi">
                  <option :value="0">Draft</option>
                  <option :value="1">Submit (Post to Ledger)</option>
                </select>
                <div style="font-size:11px;color:#9ca3af;margin-top:4px">Submitted invoices are posted to the ledger and can be paid against.</div>
              </div>
            </div>
          </div>

        </div><!-- /inv-dbody -->

          <!-- Live preview pane -->
          <div v-if="showPreview" class="inv-preview-pane">
            <div class="inv-preview-toolbar">
              <span style="font-size:11px;font-weight:700;letter-spacing:.05em;color:#6b7280">LIVE PREVIEW</span>
              <!-- <div style="display:flex;gap:6px">
                <span style="font-size:11px;color:#9ca3af">{{ TEMPLATES.find(t=>t.key===selectedTemplate)?.label }}</span>
                <button class="add-btn-draft" style="font-size:11px;padding:4px 10px" @click="printInvoice(previewData)">
                  <span v-html="icon('download',12)"></span> Print PDF
                </button>
              </div> -->
            </div>
            <iframe :srcdoc="previewHtml" class="inv-preview-iframe" sandbox="allow-same-origin"></iframe>
          </div>

        </div><!-- /inv-content-row -->

        <!-- ── Footer ── -->
        <div class="inv-dfooter">
          <div class="add-footer-status">{{ editingName ? 'Editing: ' + editingName : 'New invoice — unsaved changes' }}</div>
          <div class="add-footer-actions">
            <button class="add-btn-cancel" @click="drawerOpen=false">Cancel</button>
            <button class="add-btn-draft" :disabled="drawerSaving" @click="saveInvoice(0)">
              Save Draft
            </button>
            <div style="position:relative">
              <button class="add-btn-more" :disabled="drawerSaving" @click="moreActionsOpen=!moreActionsOpen">
                {{ drawerSaving ? 'Saving…' : 'More Actions' }}
                <svg class="add-btn-more-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
              </button>
              <div v-if="moreActionsOpen" class="add-more-menu" v-click-outside="()=>moreActionsOpen=false">
                <button class="add-more-menu-item" :disabled="drawerSaving" @click="saveInvoice(1);moreActionsOpen=false">
                  <span v-html="icon('check',13)"></span> Submit Invoice
                </button>
                <button class="add-more-menu-item" :disabled="drawerSaving" @click="saveInvoice(0, true);moreActionsOpen=false">
                  Save &amp; New
                </button>
                <button class="add-more-menu-item" @click="printInvoice(previewData);moreActionsOpen=false">
                  <span v-html="icon('download',13)"></span> Save &amp; Print PDF
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── View Drawer ── -->
    <!-- ══ INVOICE VIEW — right-side drawer ══ -->
    <div v-if="viewOpen&&viewInv" class="inv-drawer-bg" @click.self="viewOpen=false">
    <div class="inv-drawer-panel inv-drawer-wide inv-view-page">

      <!-- Top header: number + badge | Receive Payment CTA -->
      <div class="inv-view-header">
        <div style="
              display: flex;
              justify-content: space-between;
              width: -webkit-fill-available;
          ">
        <div class="inv-view-header-left">
          <div class="inv-view-title-row">
            <span class="inv-view-number">{{ viewInv.name }}</span>
            <span class="inv-hdr-badge" :class="statusCls(viewInv)">{{ statusLabel(viewInv) }}</span>
          </div>
          <div class="inv-view-subtitle">
            <span class="inv-cust-link" @click="viewOpen=false">
              <DocLink doctype="Customer" :name="viewInv.customer" :mono-style="false">{{ viewInv.customer_name||viewInv.customer }}</DocLink>
            </span>
            <span v-if="viewInv.due_date"> · Due on {{ fmtDate(viewInv.due_date) }}
              <span v-if="isOverdue(viewInv)"> ({{ overdueDays(viewInv) }}d overdue)</span>
            </span>
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
          <button v-if="viewInv.outstanding_amount>0&&viewInv.docstatus===1"
                  class="inv-view-cta"
                  :disabled="!$canEdit('invoices')"
                  :title="!$canEdit('invoices') ? 'Read-only access' : ''"
                  @click="openPayment(viewInv)">
            <span v-html="icon('indianrupee',15)"></span> <div class="ab-label"> Receive Payment</div>
          </button>
          <button class="inv-ab-btn" style="padding:7px 12px;font-size:13px" @click="viewOpen=false">
            <span v-html="icon('x',14)"></span> <span class="ab-label">Close</span>
          </button>
        </div>
      </div>
      </div>

      <!-- Main white card -->
      <div class="inv-view-body">

        <!-- Status timeline -->
        <div class="inv-tl-wrap">
          <div class="inv-tl">
            <!-- solid progress line behind completed steps -->
            <div class="inv-tl-progress"
                 :style="{ width: tlProgressWidth }"></div>
            <template v-for="(step, i) in timelineSteps" :key="i">
              <div class="inv-tl-step"
                   :class="{ 'tl-done': step.done && !step.danger, 'tl-danger': step.danger, 'tl-success': step.success, 'tl-pending': !step.done && !step.danger }">
                <div class="inv-tl-dot">
                  <span v-if="step.done && !step.danger" v-html="icon('check',14)"></span>
                  <span v-else-if="step.danger" style="font-size:11px;font-weight:800">!</span>
                  <span v-else v-html="icon(step.icon||'circle',14)"></span>
                </div>
                <div class="inv-tl-label">{{ step.label }}</div>
                <div class="inv-tl-date">{{ step.date ? fmtDate(step.date) : '—' }}</div>
              </div>
            </template>
          </div>
        </div>

        <!-- Action buttons bar -->
        <div class="inv-action-bar">
          <button v-if="viewInv.docstatus===0" class="inv-ab-btn" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="viewOpen=false;openEdit(viewInv)">
            <span v-html="icon('edit',13)"></span> <span class="ab-label">Edit</span>
          </button>
          <button v-if="viewInv.docstatus===0" class="inv-ab-btn" style="color:#16a34a;border-color:rgba(22,163,106,.3)" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="submitInv(viewInv)">
            <span v-html="icon('check',13)"></span> <span class="ab-label">Submit</span>
          </button>
          <button class="inv-ab-btn" :disabled="!$canCreate('invoices')" :title="!$canCreate('invoices') ? 'Read-only access' : ''" @click="duplicateInvoice(viewInv)">
            <span v-html="icon('copy',13)"></span> <span class="ab-label">Duplicate</span>
          </button>
          <div style="position:relative;display:inline-flex">
            <button class="inv-ab-btn inv-ab-dropdown" @click="showDownloadMenu=!showDownloadMenu">
              <span v-html="icon('download',13)"></span> <span class="ab-label">Download</span>
              <span class="inv-ab-caret">▾</span>
            </button>
            <div v-if="showDownloadMenu" class="inv-dl-menu">
              <div class="inv-dl-menu-header">Export Invoice</div>
              <button @click="downloadInvoicePdf('pdf')" class="inv-dl-menu-item">
                <span class="inv-dl-menu-icon" v-html="icon('download',14)"></span>
                <span class="inv-dl-menu-text">
                  <span class="inv-dl-menu-label">Download PDF</span>
                  <span class="inv-dl-menu-sub">Custom template · Save to device</span>
                </span>
              </button>
              <button @click="downloadInvoicePdf('print')" class="inv-dl-menu-item">
                <span class="inv-dl-menu-icon" v-html="icon('printer',14)"></span>
                <span class="inv-dl-menu-text">
                  <span class="inv-dl-menu-label">Open &amp; Print</span>
                  <span class="inv-dl-menu-sub">Custom template · New tab</span>
                </span>
              </button>
            </div>
          </div>
          <button class="inv-ab-btn" @click="openEmail(viewInv)">
            <span v-html="icon('mail',13)"></span> <span class="ab-label">Send Email</span>
          </button>
          <button v-if="viewInv.docstatus===1 && !viewInv.is_return" class="inv-ab-btn" @click="openCreditNote(viewInv)">
            <span v-html="icon('creditnote',13)"></span> <span class="ab-label">Credit Note</span>
          </button>
          <button v-if="viewInv.docstatus===1&&!viewInv.is_return" class="inv-ab-btn" @click="makeRecurring(viewInv)">
            <span v-html="icon('repeat',13)"></span> <span class="ab-label">Make Recurring</span>
          </button>
          <button v-if="viewInv.docstatus===1" class="inv-ab-btn inv-ab-danger" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="confirmAction('cancel', viewInv)">
            Cancel
          </button>
          <button v-if="viewInv.docstatus===0||viewInv.docstatus===2" class="inv-ab-btn inv-ab-danger" :disabled="!$canDelete('invoices')" :title="!$canDelete('invoices') ? 'Not permitted' : ''" @click="confirmAction('delete', viewInv)">
            <span v-html="icon('delete',13)"></span> <span class="ab-label">Delete</span>
          </button>
        </div>

        <!-- Tabs -->
        <div class="inv-view-tabs">
          <button class="inv-vtab" :class="{ active: viewTab==='details' }" @click="viewTab='details'">Details</button>
          <button class="inv-vtab" :class="{ active: viewTab==='payments' }" @click="viewTab='payments';loadPayments(viewInv.name)">
            Payments
            <span v-if="viewPayments.length + viewCreditApps.length > 0" class="inv-vtab-count">{{ viewPayments.length + viewCreditApps.length }}</span>
          </button>
          <button v-if="viewInv.docstatus===1 && !viewInv.is_return" class="inv-vtab" :class="{ active: viewTab==='einvoice' }" @click="viewTab='einvoice'; fetchCompanyGstin()">
            e-Invoice
            <span v-if="viewInv.irn && viewInv.einvoice_status!=='Cancelled'" class="inv-vtab-count" style="background:#dcfce7;color:#16a34a">✓</span>
            <span v-else-if="viewInv.customer_gstin && !viewInv.irn" class="inv-vtab-count" style="background:#fff7ed;color:#ea580c">!</span>
          </button>
        </div>

        <!-- ── Details tab ── -->
        <template v-if="viewTab==='details'">
          <div class="inv-tab-body">

            <!-- Details meta row: Customer | Invoice Date | Due Date | Place of Supply | Balance Due -->
            <div class="inv-details-meta">
              <!-- Customer -->
              <div class="inv-details-meta-col col-customer">
                <div class="inv-dmeta-icon-row">
                  <span class="inv-dmeta-icon" v-html="icon('user',13)"></span>
                  <span class="inv-dmeta-lbl">Customer</span>
                </div>
                <div class="inv-dmeta-primary">
                  <DocLink doctype="Customer" :name="viewInv.customer" :mono-style="false">{{ viewInv.customer_name||viewInv.customer }}</DocLink>
                </div>
                <div v-if="viewInv.contact_email" class="inv-dmeta-secondary">{{ viewInv.contact_email }}</div>
                <div v-if="viewInv.contact_mobile" class="inv-dmeta-tertiary">{{ viewInv.contact_mobile }}</div>
                
              </div>

              <!-- Invoice Date -->
              <div class="inv-details-meta-col">
                <div class="inv-dmeta-icon-row">
                  <span class="inv-dmeta-icon" v-html="icon('calendar',13)"></span>
                  <span class="inv-dmeta-lbl">Invoice Date</span>
                </div>
                <div class="inv-dmeta-date-val">{{ fmtDateLong(viewInv.posting_date) }}</div>
                <div class="inv-dmeta-date-sub">{{ fmtDateDay(viewInv.posting_date) }}<template v-if="viewInv.posting_time"> · {{ viewInv.posting_time }}</template></div>
              </div>

              <!-- Due Date -->
              <div class="inv-details-meta-col">
                <div class="inv-dmeta-icon-row">
                  <span class="inv-dmeta-icon" v-html="icon('calendar',13)"></span>
                  <span class="inv-dmeta-lbl">Due Date</span>
                </div>
                <div class="inv-dmeta-date-val" :class="{ 'is-overdue': isOverdue(viewInv) }">
                  {{ fmtDateLong(viewInv.due_date) || '—' }}
                </div>
                <div class="inv-dmeta-date-sub" v-if="viewInv.due_date">{{ fmtDateDay(viewInv.due_date) }}</div>
              </div>

              <!-- Place of Supply -->
              <div class="inv-details-meta-col">
                <div class="inv-dmeta-icon-row">
                  <span class="inv-dmeta-icon" v-html="icon('map-pin',13)"></span>
                  <span class="inv-dmeta-lbl">Place of Supply</span>
                </div>
                <div class="inv-dmeta-date-val" style="font-size:14px">{{ viewInv.place_of_supply || '—' }}</div>
              </div>

              <!-- Balance Due -->
              <div class="inv-details-meta-col col-balance">
                <div class="inv-dmeta-icon-row">
                  <span class="inv-dmeta-icon" v-html="icon('indianrupee',13)"></span>
                  <span class="inv-dmeta-lbl">Balance Due</span>
                </div>
                <div class="inv-balance-val"
                     :class="{ 'is-paid': viewInv.outstanding_amount===0, 'is-zero': viewInv.outstanding_amount===0 }">
                  {{ fmtAmt(viewInv.outstanding_amount, viewInv.currency) }}
                </div>
                <button v-if="viewInv.outstanding_amount>0&&viewInv.docstatus===1"
                        class="inv-rec-pay-btn"
                        :disabled="!$canEdit('invoices')"
                        :title="!$canEdit('invoices') ? 'Read-only access' : ''"
                        @click="openPayment(viewInv)">
                  Record Payment
                </button>
              </div>
            </div>

            <div v-if="viewLoading" style="padding:24px;text-align:center;color:#9ca3af">Loading details…</div>

            <template v-else>
              <!-- Line items table -->
              <div v-if="viewInv.items&&viewInv.items.length" class="inv-items-wrap" style="overflow:scroll;">
                <table class="inv-items-table"  style="overflow:scroll;">
                  <thead>
                    <tr>
                      <th style="width:36px">#</th>
                      <th>Item &amp; Description</th>
                      <th>HSN/SAC</th>
                      <th class="th-r">MRP (₹)</th>
                      <th class="th-r">Qty</th>
                      <th class="th-r">Rate (₹)</th>
                      <th class="th-r">Discount (₹)</th>
                      <th>Tax Template</th>
                      <th>Batch No</th>
                      <th>Expiry Date</th>
                      <th class="th-r">Amount (₹)</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(it,i) in viewInv.items" :key="i">
                      <td class="inv-item-num">{{ i+1 }}</td>
                      <td>
                        <div class="inv-item-name">{{ it.item_name||it.item_code }}</div>
                        <div v-if="it.description" class="inv-item-desc">{{ it.description }}</div>
                      </td>
                      <td class="inv-dash">{{ it.hsn_code || '—' }}</td>
                      <td class="td-r inv-dash">{{ flt(it.mrp) ? fmtN(it.mrp) : '—' }}</td>
                      <td class="td-r" >{{ flt(it.qty) }}</td>
                      <td class="td-r" >{{ fmtN(it.rate) }}</td>
                      <td class="td-r inv-dash">{{ lineDiscount(it) ? fmtN(lineDiscount(it)) : '—' }}</td>
                      <td class="inv-dash">{{ taxTemplateLabel(it.tax_code) }}</td>
                      <td class="inv-dash">{{ it.batch_no || '—' }}</td>
                      <td class="inv-dash">{{ it.batch_expiry_date ? fmtDate(it.batch_expiry_date) : '—' }}</td>
                      <td class="td-r" style="font-weight:600">{{ fmtN(it.amount) }}</td>
                    </tr>
                  </tbody>
                </table>

                <!-- Totals section inside table wrap -->
                <div class="inv-totals-section">
                  <div class="inv-totals-inner">
                    <div class="inv-total-line">
                      <span class="t-lbl">Subtotal</span>
                      <span class="t-amt">{{ fmtAmt(viewSubtotal, viewInv.currency) }}</span>
                    </div>
                    <div v-if="viewDiscountTotal" class="inv-total-line">
                      <span class="t-lbl">Item Discount</span>
                      <span class="t-amt">-{{ fmtAmt(viewDiscountTotal, viewInv.currency) }}</span>
                    </div>
                    <div v-if="viewAdditionalDiscount" class="inv-total-line">
                      <span class="t-lbl">Discount{{ viewInv.discount_type==='Percentage' && viewInv.additional_discount_percentage ? ' (' + viewInv.additional_discount_percentage + '%)' : '' }}</span>
                      <span class="t-amt">-{{ fmtAmt(viewAdditionalDiscount, viewInv.currency) }}</span>
                    </div>
                    <div v-if="viewDiscountTotal || viewAdditionalDiscount" class="inv-total-line">
                      <span class="t-lbl">Net Total</span>
                      <span class="t-amt">{{ fmtAmt(viewNetTotal, viewInv.currency) }}</span>
                    </div>
                    <template v-if="viewInv.taxes&&viewInv.taxes.length">
                      <div v-for="(tx,i) in viewInv.taxes" :key="i" class="inv-total-line">
                        <span class="t-lbl">{{ tx.description||tx.account_head }}</span>
                        <span class="t-amt">{{ fmtAmt(tx.tax_amount||tx.amount||0, viewInv.currency) }}</span>
                      </div>
                    </template>
                    <div v-else class="inv-total-line">
                      <span class="t-lbl">Tax (0%)</span>
                      <span class="t-amt">{{ fmtAmt(0, viewInv.currency) }}</span>
                    </div>
                    <div v-if="viewRoundOff" class="inv-total-line">
                      <span class="t-lbl">Round Off</span>
                      <span class="t-amt">{{ viewRoundOff>0?'+':'' }}{{ fmtAmt(viewRoundOff, viewInv.currency) }}</span>
                    </div>
                    <div class="inv-grand-total-line">
                      <span class="inv-grand-lbl">Grand Total</span>
                      <span class="inv-grand-amt">{{ fmtAmt(viewGrandTotal, viewInv.currency) }}</span>
                    </div>
                  </div>
                </div>

                <!-- Amount in words -->
                <div v-if="viewInv.in_words" class="inv-amount-words">
                  Amount in words: {{ viewInv.in_words }}
                </div>
              </div>
              <div v-else style="color:#9ca3af;font-size:13px;padding:8px 0">No item details available.</div>
              <div v-if="viewInv.cost_center" style="margin-top:10px;display:flex;align-items:center;gap:8px;font-size:12.5px">
                <span style="color:#6b7280;font-weight:600">Cost Center:</span>
                <span style="background:#f0fdf4;border:1px solid #bbf7d0;color:#15803d;border-radius:5px;padding:2px 10px;font-weight:600">{{ viewInv.cost_center }}</span>
              </div>
              <div v-if="viewInv.sales_person" style="margin-top:10px;display:flex;align-items:center;gap:8px;font-size:12.5px">
                <span style="color:#6b7280;font-weight:600">Sales Person:</span>
                <span style="background:#faf5ff;border:1px solid #e9d5ff;color:#7e22ce;border-radius:5px;padding:2px 10px;font-weight:600">{{ salesPersonLabel(viewInv.sales_person) }}</span>
              </div>
              <div v-if="viewInv.set_warehouse||viewInv.price_list" style="margin-top:10px;display:flex;align-items:center;flex-wrap:wrap;gap:8px;font-size:12.5px">
                <template v-if="viewInv.set_warehouse">
                  <span style="color:#6b7280;font-weight:600">Dispatch Warehouse:</span>
                  <span style="background:#eff6ff;border:1px solid #bfdbfe;color:#1d4ed8;border-radius:5px;padding:2px 10px;font-weight:600;display:inline-flex;align-items:center;gap:5px"><span v-html="icon('warehouse',12)"></span>{{ viewInv.set_warehouse }}</span>
                </template>
                <template v-if="viewInv.price_list">
                  <span style="color:#6b7280;font-weight:600">Price List:</span>
                  <span style="background:#faf5ff;border:1px solid #e9d5ff;color:#7e22ce;border-radius:5px;padding:2px 10px;font-weight:600;display:inline-flex;align-items:center;gap:5px"><span v-html="icon('badge',12)"></span>{{ viewInv.price_list }}</span>
                </template>
              </div>
            </template>
          </div>

          <!-- Activity + Notes bottom grid -->
          <div >
            <!-- Address card -->
            <div v-if="viewInv.billing_address||viewInv.shipping_address" class="inv-bottom-card" style="margin:5px">
              <div class="inv-bottom-card-header">
                <div class="inv-bottom-card-title"><span v-html="icon('map-pin',14)"></span> Addresses</div>
              </div>
              <div class="inv-bottom-card-body">
                <div class="view-address-grid">
                  <div v-if="viewInv.billing_address">
                    <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px">
                      <span v-html="icon('map-pin',12)" style="color:#6b7280"></span>
                      <span style="font-size:10.5px;font-weight:700;text-transform:uppercase;color:#6b7280;letter-spacing:0.5px">Billing Address</span>
                    </div>
                    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px 14px">
                      <span style="display:inline-block;background:#dbeafe;color:#2563eb;font-size:10px;font-weight:700;text-transform:uppercase;padding:2px 8px;border-radius:20px;letter-spacing:0.4px;margin-bottom:8px">Billing</span>
                      <div style="font-size:13px;color:#374151;line-height:1.65;">{{ displayAddr(viewInv.billing_address) }}</div>
                    </div>
                  </div>
                  <div v-if="viewInv.shipping_address">
                    <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px">
                      <span v-html="icon('map-pin',12)" style="color:#6b7280"></span>
                      <span style="font-size:10.5px;font-weight:700;text-transform:uppercase;color:#6b7280;letter-spacing:0.5px">Shipping Address</span>
                    </div>
                    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px 14px">
                      <span style="display:inline-block;background:#dbeafe;color:#2563eb;font-size:10px;font-weight:700;text-transform:uppercase;padding:2px 8px;border-radius:20px;letter-spacing:0.4px;margin-bottom:8px">Shipping</span>
                      <div style="font-size:13px;color:#374151;line-height:1.65;">{{ displayAddr(viewInv.shipping_address) }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div style="display:flex;margin:5px">
            <!-- Journal (debit/credit ledger) -->
              <div class="inv-bottom-card" style="margin-right:5px;">
                <div class="inv-bottom-card-header">
                  <div class="inv-bottom-card-title">
                    <span v-html="icon('journal',14)"></span> Journal
                  </div>
                </div>
                <div class="inv-bottom-card-body">
                  <template v-if="viewInv.docstatus===1">
                    <JournalTab
                      voucher-type="Sales Invoice"
                      :voucher-no="viewInv.name"
                      label="Invoice"
                      :currency="viewInv.currency || 'INR'"
                    />
                  </template>
                  <div v-else style="color:#9ca3af;font-size:13px;padding:8px 0">Journal entries are posted once the invoice is submitted.</div>
                </div>
              </div>

              <!-- Notes -->
              <div class="inv-bottom-card">
                <div class="inv-bottom-card-header">
                  <div class="inv-bottom-card-title">
                    <span class="inv-bottom-card-title-icon" v-html="icon('sticky-note',14)"></span> Notes
                  </div>
                </div>
                <div class="inv-bottom-card-body">
                  <div v-if="viewInv.terms||viewInv.remarks">
                    <div v-if="viewInv.terms" style="font-size:13px;color:#374151;margin-bottom:10px">
                      <div style="font-size:10.5px;font-weight:700;text-transform:uppercase;color:#9ca3af;margin-bottom:4px">Customer Note</div>
                      {{ viewInv.terms }}
                    </div>
                    <div v-if="viewInv.remarks" style="font-size:13px;color:#374151">
                      <div style="font-size:10.5px;font-weight:700;text-transform:uppercase;color:#9ca3af;margin-bottom:4px">Internal Remarks</div>
                      {{ viewInv.remarks }}
                    </div>
                  </div>
                  <div v-else class="inv-notes-empty">
                    <div class="inv-notes-empty-icon" v-html="icon('file-text',36)"></div>
                    <div class="inv-notes-empty-text">No notes added yet</div>
                    <div class="inv-notes-empty-sub">Add internal notes for this invoice.</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="inv-view-footer" v-if="viewInv.owner">
            Created by {{ viewInv.owner }} on {{ fmtDateTime(viewInv.creation) }}
          </div>
        </template>

        <!-- ── Payments tab ── -->
        <template v-else-if="viewTab==='payments'">
          <div class="inv-tab-body">
            <div v-if="viewPaymentsLoading" style="padding:24px;text-align:center;color:#9ca3af">Loading payments…</div>
            <template v-else>
              <!-- Cash / bank payments -->
              <div v-if="viewPayments.length" class="inv-items-wrap">
                <div class="inv-pay-section-lbl">Payments Received</div>
                <table class="inv-items-table inv-payments-tbl">
                  <thead>
                    <tr>
                      <th>Payment #</th>
                      <th>Date</th>
                      <th>Mode</th>
                      <th>Reference</th>
                      <th class="th-r">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(p,i) in viewPayments" :key="i">
                      <td><DocLink doctype="Payment Entry" :name="p.payment_entry || p.name" /></td>
                      <td class="mono-sm">{{ fmtDate(p.payment_date) }}</td>
                      <td>{{ p.mode_of_payment||'—' }}</td>
                      <td class="text-muted mono-sm">{{ p.reference_no||'—' }}</td>
                      <td class="td-r">
                        <div style="font-weight:600;color:#059669">{{ fmtAmt(p.paid_amount) }}</div>
                        <div v-if="flt(p.bank_charges) > 0" style="font-size:10.5px;color:#dc2626;font-weight:500">
                          − {{ fmtAmt(p.bank_charges) }} bank charges
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- Credit note applications -->
              <div v-if="viewCreditApps.length" class="inv-items-wrap" style="margin-top:12px">
                <div class="inv-pay-section-lbl inv-pay-section-lbl-cn">Credit Notes</div>
                <table class="inv-items-table inv-payments-tbl">
                  <thead>
                    <tr>
                      <th>Credit Note</th>
                      <th>Date</th>
                      <th>Type</th>
                      <th>Reference</th>
                      <th class="th-r">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(a,i) in viewCreditApps" :key="i">
                      <td><DocLink doctype="Sales Invoice" :name="a.credit_note" /></td>
                      <td class="mono-sm">{{ fmtDate(a.date) }}</td>
                      <td>
                        <span v-if="a.type==='direct'" class="inv-cn-badge inv-cn-badge-direct">Return / Issued</span>
                        <span v-else class="inv-cn-badge inv-cn-badge-applied">Applied</span>
                      </td>
                      <td>
                        <DocLink v-if="a.journal_entry" doctype="Journal Entry" :name="a.journal_entry" />
                        <span v-else class="text-muted mono-sm">—</span>
                      </td>
                      <td class="td-r" style="font-weight:600;width: -webkit-fill-available !important;color:#7c3aed">{{ fmtAmt(a.amount) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div v-if="!viewPayments.length && !viewCreditApps.length" style="text-align:center;padding:48px;color:#9ca3af;font-size:13px">
                No payments recorded against this invoice.
                <div v-if="viewInv.outstanding_amount>0&&viewInv.docstatus===1" style="margin-top:12px">
                  <button class="inv-view-cta" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="openPayment(viewInv)">
                    <span v-html="icon('indianrupee',14)"></span> Record Payment
                  </button>
                </div>
              </div>
            </template>
          </div>
        </template>

        <!-- ── e-Invoice tab ── -->
        <template v-else-if="viewTab==='einvoice'">
          <div class="inv-tab-body" style="display:flex;flex-direction:column;gap:0;padding:16px 20px">

            <!-- Status row -->
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
              <div style="font-size:13px;font-weight:600;color:#374151">e-Invoice Status</div>
              <span class="ei-inline-badge" :class="viewInv.irn && viewInv.einvoice_status!=='Cancelled' ? 'badge-green' : viewInv.einvoice_status==='Cancelled' ? 'badge-grey' : 'badge-orange'">
                {{ viewInv.irn && viewInv.einvoice_status!=='Cancelled' ? 'IRN Generated' : viewInv.einvoice_status==='Cancelled' ? 'Cancelled' : 'Pending IRN' }}
              </span>
            </div>

            <!-- Company GSTIN not configured warning -->
            <div v-if="!companyGstinLoading && !companyGstin" style="display:flex;align-items:flex-start;gap:10px;background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:12px 14px;font-size:12.5px;color:#991b1b;line-height:1.5;margin-bottom:12px">
              <span style="flex-shrink:0;margin-top:1px;font-size:15px">⚠️</span>
              <div>
                <div style="font-weight:700;margin-bottom:2px">Company GSTIN not configured</div>
                <div>Set your company's GSTIN under <strong>Books Company → GSTIN</strong> to enable IRN generation.</div>
              </div>
            </div>

            <!-- No customer GSTIN warning -->
            <div v-if="!viewInv.customer_gstin" style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:12px 14px;font-size:12.5px;color:#92400e;line-height:1.5;margin-bottom:12px">
              <span style="font-weight:700">Customer GSTIN missing.</span> Add Tax ID on the Customer record to enable e-Invoice generation.
            </div>

            <!-- IRN details when generated -->
            <template v-if="viewInv.irn">
              <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#6b7280;margin-bottom:6px">IRN</div>
              <div style="background:#f8faff;border:1px solid #dbeafe;border-radius:8px;padding:12px 14px;display:flex;align-items:flex-start;gap:8px;margin-bottom:10px">
                <div style="font-size:10.5px;color:#1e40af;word-break:break-all;line-height:1.7;flex:1">{{ viewInv.irn }}</div>
                <button @click="copyViewIRN" style="background:none;border:1px solid #dbeafe;border-radius:6px;padding:4px 8px;cursor:pointer;color:#2563eb;font-size:12px;flex-shrink:0">
                  {{ eiCopied ? '✓ Copied' : 'Copy' }}
                </button>
              </div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:14px">
                <div style="background:#f8f9fc;border:1px solid #e8ecf0;border-radius:8px;padding:10px 12px">
                  <div style="font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#868e96">Ack No.</div>
                  <div style="font-size:12.5px;font-weight:600;color:#1a1d23;margin-top:3px;">{{ viewInv.ack_no || '—' }}</div>
                </div>
                <div style="background:#f8f9fc;border:1px solid #e8ecf0;border-radius:8px;padding:10px 12px">
                  <div style="font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#868e96">Ack Date</div>
                  <div style="font-size:12.5px;font-weight:600;color:#1a1d23;margin-top:3px">{{ fmtDate(viewInv.ack_date) || '—' }}</div>
                </div>
              </div>
              <!-- QR Code -->
              <div v-if="viewInv.einvoice_status !== 'Cancelled'" style="display:flex;flex-direction:column;align-items:center;gap:8px;margin-bottom:14px">
                <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#6b7280">QR Code</div>
                <div style="background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:12px;display:inline-flex">
                  <IrnQrCode :irn="viewInv.irn" :size="160" />
                </div>
              </div>
              <!-- Cancel button -->
              <div v-if="viewInv.einvoice_status !== 'Cancelled'" style="display:flex;justify-content:flex-end">
                <button class="ei-action-btn danger" :disabled="eiCancelling || !$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="cancelInvIRN">
                  {{ eiCancelling ? 'Cancelling…' : 'Cancel IRN' }}
                </button>
              </div>
            </template>

            <!-- Pending — generate or manual -->
            <template v-else-if="viewInv.customer_gstin">
              <div v-if="!eiManualMode" style="display:flex;flex-direction:column;align-items:center;gap:14px;padding:24px 0">
                <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" stroke-width="1.3"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>
                <div style="font-size:13px;color:#6b7280;text-align:center">No IRN generated yet for this invoice</div>
                <div style="display:flex;gap:8px">
                  <button class="ei-action-btn primary" :disabled="eiGenerating || !companyGstin || !$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : (!companyGstin ? 'Company GSTIN not configured. Set it under Books Company → GSTIN.' : '')" @click="generateInvIRN">
                    <span v-if="eiGenerating" style="display:inline-block;animation:spin 1s linear infinite">↻</span>
                    {{ eiGenerating ? 'Generating…' : 'Generate IRN' }}
                  </button>
                  <button class="ei-action-btn outline" :disabled="!companyGstin || !$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : (!companyGstin ? 'Company GSTIN not configured. Set it under Books Company → GSTIN.' : '')" @click="eiManualMode=true">Enter Manually</button>
                </div>
              </div>
              <!-- Manual entry form -->
              <div v-else style="display:flex;flex-direction:column;gap:10px">
                <div style="font-size:13px;font-weight:600;color:#374151">Enter IRN Manually</div>
                <div>
                  <label style="font-size:11.5px;font-weight:600;color:#374151;display:block;margin-bottom:4px">IRN (64-char hex) *</label>
                  <input v-model="eiManualIrn" class="ei-input" placeholder="64-character hex from NIC portal" maxlength="64" style="font-size:11.5px" />
                </div>
                <div>
                  <label style="font-size:11.5px;font-weight:600;color:#374151;display:block;margin-bottom:4px">Ack No. *</label>
                  <input v-model="eiManualAckNo" class="ei-input" placeholder="Acknowledgement number" />
                </div>
                <div>
                  <label style="font-size:11.5px;font-weight:600;color:#374151;display:block;margin-bottom:4px">Ack Date</label>
                  <input v-model="eiManualAckDate" type="date" class="ei-input" />
                </div>
                <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:4px">
                  <button class="ei-action-btn outline" @click="eiManualMode=false">Cancel</button>
                  <button class="ei-action-btn primary" :disabled="eiManualSaving || !$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="saveInvManualIRN">
                    {{ eiManualSaving ? 'Saving…' : 'Save IRN' }}
                  </button>
                </div>
              </div>
            </template>

          </div>
        </template>

        </div><!-- /inv-view-body -->
    </div><!-- /inv-drawer-panel inv-view-page -->
    </div><!-- /inv-drawer-bg -->

    <!-- Phase 0.9 purge: Payment / Email / Credit Note inline modals removed. Handled by globally mounted PaymentDialog / EmailDialog / ReturnNoteDialog. -->

    <!-- ── Confirm Modal (cancel / delete) ── -->
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

    <div v-if="confirmModal.open" class="rp-backdrop" @click.self="confirmModal.open=false">
      <div class="rp-dialog" style="max-width:440px">
        <div class="rp-dialog-header">
          <span class="rp-dialog-title">{{ confirmModal.title }}</span>
          <button class="rp-close-btn" @click="confirmModal.open=false">✕</button>
        </div>
        <div class="rp-body">
          <p style="font-size:13px;color:#374151;margin:0 0 12px">{{ confirmModal.message }}</p>
          <div v-if="confirmModal.payments.length" style="border:1px solid #fca5a5;border-radius:8px;overflow:hidden;margin-bottom:8px">
            <div style="background:#fee2e2;padding:8px 12px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:#b91c1c;display:grid;grid-template-columns:1fr 1fr 1fr 1fr">
              <span>Payment</span><span>Mode</span><span>Date</span><span style="text-align:right">Amount</span>
            </div>
            <div v-for="p in confirmModal.payments" :key="p.name" style="padding:8px 12px;font-size:12.5px;display:grid;grid-template-columns:1fr 1fr 1fr 1fr;border-top:1px solid #fee2e2">
              <span class="mono-sm" style="color:#374151">{{ p.name }}</span>
              <span style="color:#6b7280">{{ p.mode_of_payment||'—' }}</span>
              <span class="mono-sm" style="color:#6b7280">{{ fmtDate(p.payment_date) }}</span>
              <span style="text-align:right;font-weight:600;color:#059669">{{ fmtAmt(p.paid_amount) }}</span>
            </div>
          </div>
          <p v-if="confirmModal.payments.length" style="font-size:12px;color:#b91c1c;margin:8px 0 0">The payment(s) above will also be cancelled. This cannot be undone.</p>
        </div>
        <div class="rp-footer">
          <button class="rp-btn rp-btn-outline" @click="confirmModal.open=false">Keep Invoice</button>
          <button class="rp-btn" style="background:#dc2626;border-color:#dc2626;color:#fff" :disabled="confirmModal.loading" @click="confirmModal.action()">
            {{ confirmModal.loading ? 'Processing…' : confirmModal.actionLabel }}
          </button>
        </div>
      </div>
    </div>

    <!-- ── Barcode scan modal (camera) ── -->
    <div v-if="scanCameraOpen" class="rp-bg" @click.self="closeScanCamera">
      <div class="rp-modal" style="max-width:420px">
        <div class="rp-header">
          <h3>Scan Item Barcode</h3>
          <button class="inv-dclose" @click="closeScanCamera"><span v-html="icon('x',16)"></span></button>
        </div>
        <div style="padding:16px">
          <div v-if="scanCameraError" style="font-size:13px;color:#b91c1c;background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:12px">
            {{ scanCameraError }}
          </div>
          <template v-else>
            <video ref="scanVideoRef" autoplay playsinline muted style="width:100%;border-radius:8px;background:#000"></video>
            <p style="font-size:12px;color:#6b7280;margin-top:10px;text-align:center">Point the camera at the item's barcode</p>
          </template>
          <p style="font-size:11.5px;color:#9ca3af;margin-top:8px;text-align:center">
            Tip: a USB/Bluetooth barcode scanner also works directly — just scan while this invoice is open.
          </p>
        </div>
      </div>
    </div>

  </Teleport>
</div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiList, apiGet, apiGET, apiPOST, apiSave, apiSubmit, apiDelete, apiCancel, resolveCompany, refreshCsrfToken } from "../api/client.js";
import { COUNTRIES, statesFor } from "../composables/useCountryState.js";
import { useToast } from "../composables/useToast.js";
import { usePermissions } from "../composables/usePermissions.js";
import { useEmailDialog } from "../composables/useEmailDialog.js";
import { usePaymentDialog } from "../composables/usePaymentDialog.js";
import { useMakeRecurring } from "../composables/useMakeRecurring.js";
import { useOpenFromQuery } from "../composables/useOpenFromQuery.js";
import { usePagination } from "../composables/usePagination.js";
import DocLink from "../components/DocLink.vue";
import JournalTab from "../components/JournalTab.vue";
import Pagination from "../components/Pagination.vue";
import SummaryStrip from "../components/SummaryStrip.vue";
import { useReturnNote } from "../composables/useReturnNote.js";
import { icon } from "../utils/icons.js";
import { flt, fmtDate } from "../utils/format.js";
import SearchableSelect from "../components/SearchableSelect.vue";
import IrnQrCode from "../components/IrnQrCode.vue";
import { useLivePreview } from "../composables/useLivePreview.js";
import { computeTaxRows, computeDiscountAmount, applyDiscountToLines } from "../composables/useTaxCalc.js";
import { useBarcodeScanner } from "../composables/useBarcodeScanner.js";

const { toast } = useToast();
const { canCreate, canEdit, canDelete } = usePermissions();
const route = useRoute();
const router = useRouter();

function goToBrandingSettings() {
  router.push({ name: "settings-company", query: { tab: "branding" } });
}

// ── e-Invoice state ────────────────────────────────────────────────────
const eiGenerating   = ref(false);
const eiCancelling   = ref(false);
const eiCopied       = ref(false);
const eiManualMode   = ref(false);
const eiManualSaving = ref(false);
const eiManualIrn    = ref("");
const eiManualAckNo  = ref("");
const eiManualAckDate = ref(new Date().toISOString().slice(0, 10));
const companyGstin   = ref("");
const companyGstinLoading = ref(false);

async function fetchCompanyGstin() {
  if (companyGstin.value || companyGstinLoading.value) return;
  companyGstinLoading.value = true;
  try {
    const co = await resolveCompany();
    console.log("[BooksCompany][Invoices.vue] fetchCompanyGstin() resolveCompany() ->", co);
    const cd = await apiGET("zoho_books_clone.api.docs.get_doc", { doctype: "Books Company", name: co });
    companyGstin.value = cd?.gstin || "";
  } catch { companyGstin.value = ""; }
  finally { companyGstinLoading.value = false; }
}

async function generateInvIRN() {
  if (!canEdit("invoices")) { toast.error("Read-only access"); return; }
  eiGenerating.value = true;
  try {
    const res = await apiPOST("zoho_books_clone.api.gst.generate_irn", { invoice_name: viewInv.value.name });
    Object.assign(viewInv.value, res);
    const idx = list.value.findIndex(i => i.name === viewInv.value.name);
    if (idx >= 0) Object.assign(list.value[idx], res);
    toast.success("IRN generated successfully");
  } catch (e) { toast.error(e.message || "Failed to generate IRN"); }
  finally { eiGenerating.value = false; }
}

async function cancelInvIRN() {
  if (!canEdit("invoices")) { toast.error("Read-only access"); return; }
  eiCancelling.value = true;
  try {
    await apiPOST("zoho_books_clone.api.gst.cancel_irn", { invoice_name: viewInv.value.name });
    viewInv.value.einvoice_status = "Cancelled";
    const idx = list.value.findIndex(i => i.name === viewInv.value.name);
    if (idx >= 0) list.value[idx].einvoice_status = "Cancelled";
    toast.success("IRN cancelled");
  } catch (e) { toast.error(e.message || "Failed to cancel IRN"); }
  finally { eiCancelling.value = false; }
}

async function saveInvManualIRN() {
  if (!canEdit("invoices")) { toast.error("Read-only access"); return; }
  if (!eiManualIrn.value || eiManualIrn.value.length !== 64) return toast.error("IRN must be exactly 64 characters");
  if (!eiManualAckNo.value) return toast.error("Ack No. is required");
  eiManualSaving.value = true;
  try {
    const res = await apiPOST("zoho_books_clone.api.gst.save_irn_manual", {
      invoice_name: viewInv.value.name,
      irn:      eiManualIrn.value,
      ack_no:   eiManualAckNo.value,
      ack_date: eiManualAckDate.value,
    });
    Object.assign(viewInv.value, res);
    const idx = list.value.findIndex(i => i.name === viewInv.value.name);
    if (idx >= 0) Object.assign(list.value[idx], res);
    eiManualMode.value = false;
    toast.success("IRN saved");
  } catch (e) { toast.error(e.message || "Failed to save IRN"); }
  finally { eiManualSaving.value = false; }
}

async function copyViewIRN() {
  if (!viewInv.value?.irn) return;
  try {
    await navigator.clipboard.writeText(viewInv.value.irn);
    eiCopied.value = true;
    setTimeout(() => { eiCopied.value = false; }, 1800);
  } catch { toast.error("Copy failed"); }
}

// ── Constants ─────────────────────────────────────────────────────────
const PAY_MODES = ["Cash","Cheque","Bank Transfer","UPI","NEFT","RTGS","IMPS","Credit Card","Debit Card","DD"];
const FILTERS   = [
  { key:"all",     label:"All" },
  { key:"Draft",   label:"Draft" },
  { key:"Unpaid",  label:"Unpaid" },
  { key:"Overdue", label:"Overdue" },
  { key:"Paid",    label:"Paid" },
];
const DATE_RANGES = [
  { key:"all",        label:"All Time" },
  { key:"this_month", label:"This Month" },
  { key:"last_month", label:"Last Month" },
  { key:"custom",     label:"Custom" },
];
const PAYMENT_TERMS = ["Due on Receipt","Net 7","Net 15","Net 30","Net 45","Net 60","Net 90"];
const TAX_PRESETS = [
  { label:"GST 5%",   rows:[{desc:"CGST @ 2.5%",rate:2.5},{desc:"SGST @ 2.5%",rate:2.5}] },
  { label:"GST 12%",  rows:[{desc:"CGST @ 6%",  rate:6},  {desc:"SGST @ 6%",  rate:6}]   },
  { label:"GST 18%",  rows:[{desc:"CGST @ 9%",  rate:9},  {desc:"SGST @ 9%",  rate:9}]   },
  { label:"GST 28%",  rows:[{desc:"CGST @ 14%", rate:14}, {desc:"SGST @ 14%", rate:14}]  },
  { label:"IGST 5%",  rows:[{desc:"IGST @ 5%",  rate:5}]  },
  { label:"IGST 12%", rows:[{desc:"IGST @ 12%", rate:12}] },
  { label:"IGST 18%", rows:[{desc:"IGST @ 18%", rate:18}] },
  { label:"IGST 28%", rows:[{desc:"IGST @ 28%", rate:28}] },
];
const IGST_PRESETS = [
  { label:"IGST 5%",  rows:[{desc:"IGST @ 5%",  rate:5}]  },
  { label:"IGST 12%", rows:[{desc:"IGST @ 12%", rate:12}] },
  { label:"IGST 18%", rows:[{desc:"IGST @ 18%", rate:18}] },
  { label:"IGST 28%", rows:[{desc:"IGST @ 28%", rate:28}] },
];
const INDIAN_STATES = [
  "01-Jammu and Kashmir","02-Himachal Pradesh","03-Punjab","04-Chandigarh","05-Uttarakhand",
  "06-Haryana","07-Delhi","08-Rajasthan","09-Uttar Pradesh","10-Bihar","11-Sikkim",
  "12-Arunachal Pradesh","13-Nagaland","14-Manipur","15-Mizoram","16-Tripura","17-Meghalaya",
  "18-Assam","19-West Bengal","20-Jharkhand","21-Odisha","22-Chhattisgarh","23-Madhya Pradesh",
  "24-Gujarat","26-Dadra and Nagar Haveli","27-Maharashtra","29-Karnataka","30-Goa",
  "31-Lakshadweep","32-Kerala","33-Tamil Nadu","34-Puducherry","35-Andaman and Nicobar Islands",
  "36-Telangana","37-Andhra Pradesh","38-Ladakh","97-Other Territory",
];
// Customer/Address "state" is usually stored as plain text ("Tamil Nadu")
// while the Place of Supply dropdown uses GST-coded labels ("33-Tamil Nadu").
// Match on the name portion so auto-fill lands on a real dropdown option.
function matchIndianState(raw) {
  const clean = String(raw || "").replace(/^\s*\d+\s*-\s*/, "").trim().toLowerCase();
  if (!clean) return "";
  return INDIAN_STATES.find(s => s.split("-").slice(1).join("-").toLowerCase() === clean) || "";
}
const CURRENCY_SYMBOLS = { INR: "₹" };
const TEMPLATES = [
  { key:"classic", label:"Classic" },
  { key:"modern",  label:"Modern"  },
  { key:"minimal", label:"Minimal" },
];

// ── State ─────────────────────────────────────────────────────────────
const list         = ref([]);
const loading      = ref(false);
const viewMode     = ref("table"); // "table" | "grid"
const customers    = ref([]);
const salesPersons = ref([]);
const priceLists = ref([]);
const items        = ref([]);
const uomList      = ref(["Nos", "Kg", "Ltr", "Hrs", "Pcs", "Box"]);
const activeFilter = ref("all");
const search       = ref("");
const selectedRows = ref(new Set());
const sortKey      = ref("posting_date");
const sortDir      = ref(-1);
const dateRange    = ref("all");
const customFrom   = ref("");
const customTo     = ref("");
const filterCustomer = ref("");
const taxAccountHead    = ref("");
const selectedTemplate  = ref("classic");
const brandColor        = ref("#1a6ef7");
const companyLogo       = ref("");
// logoUrl removed — logo is now per-invoice via form.logo (from doc.logo_attach)
const showPreview       = ref(false);

// ── Drawer (create/edit) ───────────────────────────────────────────────
const drawerOpen   = ref(false);
const editingName  = ref(null);
const drawerSaving = ref(false);
// Map of fiscal year name -> lock_date fetched from server; used to block saves
// to locked periods before even hitting the API.
const fyLockDates = ref([]);  // [{start, end, lock_date}]
const addressLoading = ref(false);
const moreActionsOpen = ref(false);
const collapsed = reactive({ branding: false, details: false, billing: true, lines: false, notes: true });
const form = reactive({
  customer:"", posting_date:"", due_date:"", po_no:"",
  payment_terms:"", place_of_supply:"33-Tamil Nadu", billing_address:"",
  billing_address_name:"", shipping_address:"", shipping_address_name:"",
  terms:"", remarks:"", docstatus:0,
  currency:"INR", exchange_rate:1, gst_treatment:"",
  price_list:"",
  update_stock:1, set_warehouse:"",
  logo:"",
  cost_center:"", sales_person:"",
  discount_type:"Percentage", additional_discount_percentage:0, additional_discount_amount:0,
});
const customerBillingAddrs  = ref([]);
const customerShippingAddrs = ref([]);
const sameAsBillingAddr     = ref(false);
const customerAddresses     = ref([]);
const addrModal = reactive({
  open: false, saving: false, forField: "billing",
  address_title: "", address_type: "Billing",
  address_line1: "", address_line2: "", city: "", state: "", pincode: "", country: "India",
});
const selectedBillingAddr  = computed(() => customerAddresses.value.find(a => a.name === form.billing_address_name) || null);
const selectedShippingAddr = computed(() => customerAddresses.value.find(a => a.name === form.shipping_address_name) || null);
const lines   = ref([]);
const warehouses = ref([]);
async function fetchWarehouses(q=""){try{const co=await resolveCompany();const r=await apiList("Warehouse",{fields:["name","parent_warehouse"],filters:[["company","=",co],["is_group","=",0],...(q?[["name","like",`%${q}%`]]:[])],limit:30});warehouses.value=r.map(x=>({label:x.parent_warehouse?`${x.parent_warehouse} / ${x.name}`:x.name,value:x.name}));}catch{warehouses.value=[];}}
const costCenters = ref([]);
async function fetchCostCenters(){try{const co=await resolveCompany();const r=await apiGET("frappe.client.get_list",{doctype:"Cost Center",fields:JSON.stringify(["name"]),filters:JSON.stringify([["disabled","=",0],["company","=",co],["is_group","=",0]]),order_by:"name asc",limit_page_length:100})||[];costCenters.value=r.map(c=>c.name);}catch{costCenters.value=[];}}
const taxTemplates = ref([]);
function taxTemplateLabel(code){ if(!code) return '—'; const t=taxTemplates.value.find(x=>x.name===code); return t ? (t.template_name||t.name) : code; }
const companyGstState = ref("");                              // for GST intra/inter split
const gstAccounts = ref({ output_cgst:"", output_sgst:"", output_igst:"" });

// ── View drawer ────────────────────────────────────────────────────────
const viewOpen    = ref(false);
const viewInv     = ref(null);
const viewTab     = ref("details");
const viewLoading = ref(false);
const viewPayments = ref([]);
const viewCreditApps = ref([]);
const viewPaymentsLoading = ref(false);

// Phase 0.9 purge — payModal / emailModal / cnModal removed.
// Their UX is now delegated to globally mounted PaymentDialog / EmailDialog /
// ReturnNoteDialog via useEmailDialog / usePaymentDialog / useReturnNote.

// ── Confirm modal ──────────────────────────────────────────────────────
const confirmModal = reactive({ open:false, loading:false, title:"", message:"", actionLabel:"Confirm", action: null, payments:[] });

// ── Helpers ────────────────────────────────────────────────────────────
const currencySymbol = computed(() => CURRENCY_SYMBOLS[form.currency] || "₹");
function fmtAmt(v, currency) {
  const cur = currency || form.currency || "INR";
  const sym = CURRENCY_SYMBOLS[cur] || "₹";
  const locale = cur === "INR" ? "en-IN" : "en-US";
  return sym + Number(v||0).toLocaleString(locale,{minimumFractionDigits:2,maximumFractionDigits:2});
}
const isOverseas = computed(() => form.gst_treatment === "Overseas");
const isSEZ = computed(() => form.gst_treatment === "SEZ");
function todayStr() { return new Date().toISOString().slice(0,10); }
function dueDateDefault() { const d=new Date(); d.setDate(d.getDate()+30); return d.toISOString().slice(0,10); }

function isOverdue(inv) { return inv.docstatus!==2&&inv.outstanding_amount>0&&inv.due_date&&new Date(inv.due_date)<new Date(); }
function statusLabel(inv) {
  if (inv.docstatus===2) return "CANCELLED";
  if (isOverdue(inv)) { const days=Math.floor((Date.now()-new Date(inv.due_date))/86400000); return `OVERDUE ${days}d`; }
  return (inv.status||(inv.docstatus===0?"Draft":"Unpaid")).toUpperCase();
}
function statusCls(inv) {
  if (inv.docstatus===2) return "status-cancelled";
  if (isOverdue(inv)) return "status-overdue";
  const s=(inv.status||"").toLowerCase();
  if (s==="paid") return "status-paid";
  if (s==="submitted"||s==="unpaid"||s==="partly paid") return "status-unpaid";
  if (s==="cancelled") return "status-cancelled";
  return "status-draft";
}
function statusBg(inv) {
  if (inv.docstatus===2) return "linear-gradient(135deg,#7f1d1d,#dc2626)";
  if (isOverdue(inv)) return "linear-gradient(135deg,#7f1d1d,#dc2626)";
  const s=(inv.status||"").toLowerCase();
  if (s==="paid") return "linear-gradient(135deg,#064e3b,#059669)";
  if (s==="submitted"||s==="unpaid"||s==="partly paid") return "linear-gradient(135deg,#78350f,#d97706)";
  return "linear-gradient(135deg,#1e3a5f,#2563eb)";
}
function pillCls(k) { return {Draft:"pc-muted",Unpaid:"pc-amber",Overdue:"pc-red",Paid:"pc-green"}[k]||"pc-muted"; }

// ── Computed ───────────────────────────────────────────────────────────
const counts = computed(()=>({
  Draft:   list.value.filter(i=>i.docstatus===0).length,
  Unpaid:  list.value.filter(i=>!isOverdue(i)&&i.outstanding_amount>0&&i.docstatus===1).length,
  Overdue: list.value.filter(isOverdue).length,
  Paid:    list.value.filter(i=>i.outstanding_amount<=0&&i.docstatus===1).length,
}));
const summary = computed(()=>({
  unpaidCount:  list.value.filter(i=>i.outstanding_amount>0&&!isOverdue(i)).length,
  overdueCount: list.value.filter(isOverdue).length,
  totalDue:     list.value.reduce((s,i)=>s+flt(i.outstanding_amount),0),
}));
const _thisYM = () => { const d=new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; };
const _lastYM = () => { const d=new Date(); d.setMonth(d.getMonth()-1); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; };
const _trend = (a, b) => { if(!b&&!a) return {pct:0,up:true}; if(!b) return {pct:100,up:true}; const p=Math.round((a-b)/b*100); return {pct:Math.abs(p),up:p>=0}; };
const invThisMonth = computed(() => { const ym=_thisYM(); const r=list.value.filter(i=>(i.posting_date||'').startsWith(ym)); return {count:r.length,revenue:r.reduce((s,i)=>s+flt(i.grand_total),0)}; });
const _invLastCount = computed(() => { const ym=_lastYM(); return list.value.filter(i=>(i.posting_date||'').startsWith(ym)).length; });
const invAvg = computed(() => { const p=list.value.filter(i=>i.grand_total>0); return p.length?p.reduce((s,i)=>s+flt(i.grand_total),0)/p.length:0; });
const invTrends = computed(() => ({
  total:  _trend(invThisMonth.value.count, _invLastCount.value),
  draft:  _trend(counts.value.Draft, list.value.filter(i=>(i.posting_date||'').startsWith(_lastYM())&&i.docstatus===0).length),
  unpaid: _trend(counts.value.Unpaid, list.value.filter(i=>(i.posting_date||'').startsWith(_lastYM())&&i.outstanding_amount>0&&i.docstatus===1).length),
  overdue:_trend(counts.value.Overdue, list.value.filter(i=>(i.posting_date||'').startsWith(_lastYM())&&isOverdue(i)).length),
  paid:   _trend(counts.value.Paid, list.value.filter(i=>(i.posting_date||'').startsWith(_lastYM())&&i.outstanding_amount<=0&&i.docstatus===1).length),
}));
const allSelected = computed(()=>sorted.value.length>0&&sorted.value.every(i=>selectedRows.value.has(i.name)));

const filtered = computed(()=>{
  let r=list.value;
  // Date range
  const now=new Date();
  if (dateRange.value!=="all") {
    let from,to;
    if (dateRange.value==="this_month") { from=new Date(now.getFullYear(),now.getMonth(),1); to=new Date(now.getFullYear(),now.getMonth()+1,0); }
    else if (dateRange.value==="last_month") { from=new Date(now.getFullYear(),now.getMonth()-1,1); to=new Date(now.getFullYear(),now.getMonth(),0); }
    else if (dateRange.value==="custom"&&customFrom.value&&customTo.value) { from=new Date(customFrom.value); to=new Date(customTo.value); }
    if (from&&to) r=r.filter(i=>{ const d=new Date(i.posting_date); return d>=from&&d<=to; });
  }
  // Customer filter
  if (filterCustomer.value) r=r.filter(i=>i.customer===filterCustomer.value);
  // Status filter
  if (activeFilter.value==="Draft")   r=r.filter(i=>i.docstatus===0);
  else if (activeFilter.value==="Overdue") r=r.filter(isOverdue);
  else if (activeFilter.value==="Unpaid")  r=r.filter(i=>!isOverdue(i)&&i.outstanding_amount>0&&i.docstatus===1);
  else if (activeFilter.value==="Paid")    r=r.filter(i=>i.outstanding_amount<=0&&i.docstatus===1);
  // Search
  const q=search.value.toLowerCase();
  if (q) r=r.filter(i=>(i.name+(i.customer_name||"")+(i.customer||"")+(i.po_no||"")).toLowerCase().includes(q));
  return r;
});

const sorted = computed(()=>[...filtered.value].sort((a,b)=>{
  const va=a[sortKey.value]??"",vb=b[sortKey.value]??"";
  if (va<vb) return -1*sortDir.value; if (va>vb) return 1*sortDir.value; return 0;
}));

const { page, pageSize, paged } = usePagination(sorted, { storageKey: "invoices" });

// Exact (unrounded) line value — qty*rate less the line discount, computed
// at full precision. Used only for the invoice-level Subtotal so it matches
// the source invoice's truncation behaviour; per-line `amount` stays rounded
// to 2dp for display/storage (matches the printed per-item Amount column).
function exactLineAmount(l) {
  const base = flt(l.qty) * flt(l.rate);
  return base - base * flt(l.discount_percentage) / 100;
}
// The source invoice truncates (not rounds) its printed Subtotal from the
// unrounded total across all lines — summing pre-rounded per-line amounts
// instead overstates it by a paisa (e.g. ₹33,812.95 vs the correct ₹33,812.94).
const subtotal = computed(()=>Math.floor(lines.value.reduce((s,l)=>s+exactLineAmount(l),0)*100)/100);

// Common invoice-level discount, applied on the subtotal before tax —
// mirrors SalesInvoice.calculate_discount() in sales_invoice.py.
const discountAmount = computed(()=>computeDiscountAmount(
  subtotal.value,
  form.discount_type,
  form.discount_type === "Amount" ? form.additional_discount_amount : form.additional_discount_percentage,
));
// Keep the Amount field in sync for display when type=Percentage (read-only there).
watch(discountAmount, (v)=>{ if (form.discount_type === "Percentage") form.additional_discount_amount = v; });
// Net total after the invoice-level discount, before tax.
const netTotal = computed(()=>Math.round((subtotal.value - discountAmount.value)*100)/100);
// Lines with the discount spread proportionally, so per-line tax_code/rate
// taxation is computed on each item's correct post-discount taxable value.
const discountedLines = computed(()=>applyDiscountToLines(lines.value, discountAmount.value));

const taxLines = computed(()=>
  computeTaxRows(discountedLines.value, taxTemplates.value, {
    companyState: companyGstState.value,
    placeOfSupply: form.place_of_supply,
    gst: { cgst: gstAccounts.value.output_cgst, sgst: gstAccounts.value.output_sgst, igst: gstAccounts.value.output_igst },
    defaultAccount: taxAccountHead.value,
  }).map(r=>({ template:r.description, description:r.description, tax_type:r.tax_type, rate:r.rate, account_head:r.account_head, amount:r.amount }))
);

// Per-line GST breakup (e.g. "CGST 2.5% ₹226.60", "SGST 2.5% ₹226.60") — same
// engine as the invoice-level taxLines, just scoped to a single line so each
// item card can show its own tax like the printed invoice's per-item columns.
function lineTaxBreakup(line) {
  if (!line.tax_code || !flt(line.amount)) return [];
  return computeTaxRows([line], taxTemplates.value, {
    companyState: companyGstState.value,
    placeOfSupply: form.place_of_supply,
    gst: { cgst: gstAccounts.value.output_cgst, sgst: gstAccounts.value.output_sgst, igst: gstAccounts.value.output_igst },
    defaultAccount: taxAccountHead.value,
  });
}
function lineTaxTotal(line) { return lineTaxBreakup(line).reduce((s,t)=>s+t.amount,0); }

// Attach per-item CGST/SGST/IGST % (and the taxable/pre-tax amount) to a set
// of print-ready item rows, so the printed table can show a rate column per
// tax component the same way the physical/reference invoice does.
function withItemTaxRates(items, placeOfSupply){
  return (items||[]).map(it=>{
    const rows = it.tax_code && flt(it.amount) ? computeTaxRows(
      [{ amount: flt(it.amount), tax_code: it.tax_code }],
      taxTemplates.value,
      { companyState: companyGstState.value, placeOfSupply: placeOfSupply ?? form.place_of_supply, defaultAccount: taxAccountHead.value }
    ) : [];
    const rate = (type) => rows.find(r=>r.tax_type===type)?.rate || 0;
    return { ...it, taxable_amount: flt(it.amount), cgst_rate: rate("CGST"), sgst_rate: rate("SGST"), igst_rate: rate("IGST") };
  });
}
// Line Total (incl. GST) must be rounded ONCE on the combined value — adding
// the already-rounded Amount to the already-rounded GST (double rounding)
// overstates it by a paisa vs. the source invoice's printed Amount column
// (e.g. ₹9,517.15 instead of the correct ₹9,517.14).
function lineAmountWithTax(line) {
  const exact = exactLineAmount(line);
  const rateTotal = lineTaxBreakup(line).reduce((s,t)=>s+t.rate,0);
  return Math.round(exact * (1 + rateTotal / 100) * 100) / 100;
}

const taxAmount  = computed(()=>taxLines.value.reduce((s,t)=>s+t.amount,0));
// GST rule (Sec 170, CGST Act): the invoice total is rounded off to the
// nearest rupee. Without this step the app's total (e.g. ₹35,503.61) will
// never match the printed/e-invoice total (₹35,504.00), which always
// carries an explicit Round Off line.
const preRoundTotal = computed(()=>netTotal.value+taxAmount.value);
const roundOff   = computed(()=>Math.round((Math.round(preRoundTotal.value)-preRoundTotal.value)*100)/100);
const grandTotal = computed(()=>Math.round(preRoundTotal.value));

const previewData = computed(()=>({
  name: editingName.value||"INV-PREVIEW",
  customer: form.customer,
  customer_name: customers.value.find(c=>c.name===form.customer)?.customer_name||form.customer,
  customer_company_name: customers.value.find(c=>c.name===form.customer)?.company_name||"",
  posting_date: form.posting_date,
  due_date: form.due_date,
  po_no: form.po_no,
  place_of_supply: form.place_of_supply,
  billing_address: form.billing_address,
  items: withItemTaxRates(lines.value.filter(l=>l.item_code||l.item_name)),
  taxes: taxLines.value.map(tl=>({description:tl.template,rate:tl.rate,amount:tl.amount})),
  subtotal: subtotal.value,
  discountAmount: discountAmount.value,
  totalTax: taxAmount.value,
  grandTotal: grandTotal.value,
  terms: form.terms,
  company: window.__booksCompany||"",
  logo: logoSrc(form.logo),
}));

// ── Shared print/preview renderer (active template from Company Settings) ──
const { setCompany, refreshBranding, renderDocument, printDoc } = useLivePreview();
const INV_PRINT_CFG = { title: "INVOICE", partyLabel: "Bill To", partyField: "customer_name", includeHsn: true, includeDiscount: true, includeMrp: true };

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
function _invCfg(data) { return { ...INV_PRINT_CFG, companyName: data?.company || window.__booksCompany || "" }; }

const previewHtml = computed(()=>renderDocument(_toPrintDoc(previewData.value), _invCfg(previewData.value)));

// Sum of per-line discounts for the invoice being viewed, plus the
// pre-discount subtotal (qty*rate before any line discount is applied).
// viewInv.net_total from the backend is already POST-discount, so the
// "Subtotal" line must add the discount back to show the correct gross figure.
// Resilient per-line discount lookup: prefer the stored discount_amount, but
// fall back to deriving it from qty*rate vs amount (or discount_percentage)
// in case discount_amount was lost/never persisted for an older/edge-case row.
function lineDiscount(it){
  const stored = flt(it.discount_amount);
  if (stored) return stored;
  const base = Math.round(flt(it.qty)*flt(it.rate)*100)/100;
  const fromAmount = Math.round((base - flt(it.amount))*100)/100;
  if (fromAmount > 0.004) return fromAmount;
  if (flt(it.discount_percentage)) return Math.round(base*flt(it.discount_percentage)/100*100)/100;
  return 0;
}
const viewDiscountTotal = computed(()=>{
  if (!viewInv.value?.items) return 0;
  return Math.round(viewInv.value.items.reduce((s,it)=>s+lineDiscount(it),0)*100)/100;
});
// Invoice-level common discount (on subtotal, applied after per-line
// discounts) — stored directly on the doc by the backend.
const viewAdditionalDiscount = computed(()=>flt(viewInv.value?.additional_discount_amount));
const viewSubtotal = computed(()=>{
  if (!viewInv.value) return 0;
  const net = viewInv.value.net_total != null ? flt(viewInv.value.net_total) : flt(viewInv.value.grand_total)-flt(viewInv.value.total_tax);
  return Math.round((net + viewDiscountTotal.value + viewAdditionalDiscount.value)*100)/100;
});
// Same round-off fix as the edit form's Grand Total: the stored grand_total
// on older/unrounded documents is just net + tax with no invoice-level
// rounding, so recompute it here rather than trusting the raw field.
const viewNetTotal = computed(()=>Math.round((viewSubtotal.value - viewDiscountTotal.value - viewAdditionalDiscount.value)*100)/100);
const viewTaxTotal = computed(()=>{
  if (!viewInv.value?.taxes?.length) return 0;
  return viewInv.value.taxes.reduce((s,t)=>s+flt(t.tax_amount!=null?t.tax_amount:t.amount),0);
});
const viewPreRoundTotal = computed(()=>viewNetTotal.value + viewTaxTotal.value);
const viewRoundOff = computed(()=>Math.round((Math.round(viewPreRoundTotal.value)-viewPreRoundTotal.value)*100)/100);
const viewGrandTotal = computed(()=>Math.round(viewPreRoundTotal.value));

const timelineSteps = computed(()=>{
  if (!viewInv.value) return [];
  const inv=viewInv.value;
  const isPaid=inv.outstanding_amount<=0&&inv.docstatus===1;
  const isSubmitted=inv.docstatus>=1;
  const isCancelled=inv.docstatus===2;
  if (isCancelled) return [
    {label:"Draft",   done:true, icon:"file-text",  date:inv.creation},
    {label:"Submitted",done:true,icon:"send",        date:inv.modified},
    {label:"Cancelled",done:true,danger:true,icon:"x-circle", date:inv.modified},
  ];
  return [
    {label:"Draft",   done:true,       icon:"file-text", date:inv.creation},
    {label:"Sent",    done:isSubmitted, icon:"send",      date:isSubmitted?inv.modified:null},
    {label:"Paid",    done:isPaid,      icon:"indianrupees", date:isPaid?inv.modified:null},
    ...(!isPaid ? [{label:"Overdue", done:isOverdue(inv), danger:isOverdue(inv), icon:"alert-circle", date:isOverdue(inv)?inv.due_date:null}] : []),
  ];
});

// Progress line width for timeline (% across the step dots)
const tlProgressWidth = computed(()=>{
  const steps = timelineSteps.value;
  if (!steps.length) return '0%';
  const doneCount = steps.filter(s=>s.done).length;
  if (doneCount === 0) return '0%';
  // width between first and last done dot as % of total line
  const pct = ((doneCount - 1) / (steps.length - 1)) * 100;
  return pct + '%';
});

const showDownloadMenu = ref(false);

async function downloadInvoicePdf(mode = 'pdf') {
  showDownloadMenu.value = false;
  const inv = viewInv.value;
  if (!inv) return;

  // Pull the latest selected template from Company Settings before rendering.
  try { await refreshBranding(); } catch {}

  // Build the same data shape used by the create/edit preview
  const data = {
    name: inv.name,
    customer: inv.customer,
    customer_name: inv.customer_name,
    customer_company_name: customers.value.find(c=>c.name===inv.customer)?.company_name||"",
    posting_date: inv.posting_date,
    due_date: inv.due_date,
    po_no: inv.po_no,
    place_of_supply: inv.place_of_supply,
    billing_address: inv.billing_address || '',
    billing_address_name: inv.billing_address_name || '',
    shipping_address: inv.shipping_address || '',
    shipping_address_name: inv.shipping_address_name || '',
    customer_gstin: inv.customer_gstin || '',
    customer_mobile: inv.customer_mobile || '',
    items: withItemTaxRates(inv.items || [], inv.place_of_supply),
    taxes: inv.taxes || [],
    subtotal: inv.net_total != null ? flt(inv.net_total) : flt(inv.grand_total) - flt(inv.total_tax),
    totalTax: flt(inv.total_tax),
    grandTotal: flt(inv.grand_total),
    terms: inv.terms || '',
    company: inv.company || window.__booksCompany || '',
    logo: logoSrc(inv.logo || ''),
    in_words: inv.in_words || '',
  };

  // Render using the same template + branding as the live preview
  const html = renderDocument(_toPrintDoc(data), _invCfg(data));

  if (mode === 'print') {
    // Open rendered HTML in a new window and trigger print dialog
    const win = window.open('', '_blank');
    if (!win) { toast('Pop-up blocked — allow pop-ups to print', 'error'); return; }
    win.document.write(html);
    win.document.close();
    setTimeout(() => { try { win.focus(); win.print(); } catch {} }, 600);
  } else {
    // Render to a real PDF server-side (wkhtmltopdf) instead of using the
    // browser's print-to-PDF dialog — that dialog's own Margins/Headers
    // settings otherwise silently override the template's CSS, causing
    // inconsistent page margins and stray browser chrome in the output.
    try {
      const csrf = window.frappe?.csrf_token || "";
      const res = await fetch('/api/method/zoho_books_clone.api.docs.render_pdf_from_html', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Frappe-CSRF-Token': csrf },
        credentials: 'same-origin',
        body: new URLSearchParams({ pdf_html: html, filename: `${inv.name}.pdf` }),
      });
      if (!res.ok) throw new Error('PDF generation failed');
      const blob = await res.blob();
      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = objectUrl;
      a.download = `${inv.name}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(objectUrl), 5000);
    } catch (e) {
      toast('Failed to generate PDF', 'error');
    }
  }
}

// close download menu when clicking outside
function onDocClickForDownloadMenu(e) {
  if (!e.target.closest('.inv-ab-dropdown') && !e.target.closest('.inv-dl-menu-item')) {
    showDownloadMenu.value = false;
  }
}
onMounted(() => { document.addEventListener('click', onDocClickForDownloadMenu); fetchCostCenters(); loadFYLockDates(); });
onUnmounted(() => document.removeEventListener('click', onDocClickForDownloadMenu));

// ── New date / format helpers ───────────────────────────────────────────
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
function fmtDateTime(d) {
  if (!d) return '';
  const dt = new Date(d);
  return dt.toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric' })
    + ', ' + dt.toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit' });
}
function fmtN(n) {
  if (n==null) return '—';
  return Number(n).toLocaleString('en-IN', { minimumFractionDigits:2, maximumFractionDigits:2 });
}
function overdueDays(inv) {
  if (!inv?.due_date) return 0;
  return Math.max(0, Math.floor((Date.now() - new Date(inv.due_date)) / 86400000));
}

// ── Load ───────────────────────────────────────────────────────────────
async function load() {
  loading.value=true;
  try {
    // Exclude credit notes (is_return=1) — those live on /credit-notes.
    list.value=await apiList("Sales Invoice",{
      fields:["name","customer","customer_name","posting_date","due_date",
              "grand_total","outstanding_amount","status","docstatus","po_no",
              "customer_gstin","irn","einvoice_status","ack_no","ack_date"],
      filters:[["is_return","=",0]],
      limit:100000, order: "posting_date desc, creation desc",
    })||[];
  } catch { list.value=[]; toast("Could not load invoices","error"); }
  loading.value=false;
}
async function loadCustomers() {
  try { const r=await apiList("Customer",{fields:["name","customer_name","company_name"],filters:[["disabled","=",0]],limit:100000,order:"customer_name asc"})||[]; customers.value=r.map(x=>({...x,value:x.name,label:x.customer_name||x.name})); } catch {}
}
async function loadSalesPersons() {
  try { const r=await apiList("Sales Person",{fields:["name","sales_person_name"],filters:[["disabled","=",0]],limit:100000,order:"sales_person_name asc"})||[]; salesPersons.value=r.map(x=>({...x,value:x.name,label:x.sales_person_name||x.name})); } catch {}
}
async function loadPriceLists() {
  try {
    const r=await apiList("Price List",{fields:["name","price_list_name","currency","selling"],filters:[["enabled","=",1],["selling","=",1]],limit:100,order:"price_list_name asc"})||[];
    priceLists.value=r.map(x=>({...x,value:x.name,label:x.price_list_name||x.name}));
  } catch { priceLists.value=[]; }
}
// Item Price tiers are cached per (item_code, price_list) pair for the life
// of the drawer session, since the same item/price-list combo is re-resolved
// on every line edit, qty change, and price-list switch. Each price list can
// have multiple tiers for the same item, keyed by packing_unit (= "Min Qty"
// in the Price List editor) — the correct tier is the highest packing_unit
// that is <= the line's qty, falling back to the lowest tier available.
const _itemPriceTierCache = new Map();
async function fetchItemPriceTiers(item_code, price_list) {
  const key = `${item_code}||${price_list}`;
  if (_itemPriceTierCache.has(key)) return _itemPriceTierCache.get(key);
  let tiers = [];
  try {
    const r = await apiList("Item Price", {
      fields: ["price_list_rate", "packing_unit"],
      filters: [["item_code","=",item_code],["price_list","=",price_list]],
      limit: 50,
    }) || [];
    tiers = r
      .map(x => ({ min_qty: flt(x.packing_unit) || 0, rate: flt(x.price_list_rate) }))
      .sort((a, b) => a.min_qty - b.min_qty);
  } catch { tiers = []; }
  _itemPriceTierCache.set(key, tiers);
  return tiers;
}
async function fetchItemPriceRate(item_code, price_list, qty) {
  if (!item_code || !price_list) return null;
  const tiers = await fetchItemPriceTiers(item_code, price_list);
  if (!tiers.length) return null;
  const q = flt(qty) || 0;
  // Only tiers whose min_qty the ordered qty actually meets are eligible;
  // among those, the one with the highest min_qty wins. If qty doesn't meet
  // any tier's minimum (e.g. tier requires 5+ but qty is 1), there's no
  // price-list override — the item's standard rate applies instead.
  let best = null;
  for (const t of tiers) {
    if (t.min_qty <= q && (best === null || t.min_qty > best.min_qty)) best = t;
  }
  return best ? best.rate : null;
}
// Re-resolve rates for every line already on the invoice when the Price
// List selection changes, so existing lines pick up the new list's pricing
// (falling back to whatever rate they already had if the new list has no
// Item Price entry for that item).
async function onPriceListChange() {
  _itemPriceTierCache.clear();
  for (const line of lines.value) {
    if (!line.item_code) continue;
    const rate = form.price_list ? await fetchItemPriceRate(line.item_code, form.price_list, line.qty) : null;
    line.rate = (rate !== null && rate > 0) ? rate : (line._standardRate ?? line.rate);
    calcLine(line);
  }
}
// Re-resolve a single line's rate when its qty changes, so quantity-based
// price-list tiers (e.g. "5+ units get a lower rate") kick in as the user
// types, not just when the item or price list is first chosen. If qty drops
// back below every tier's minimum, the rate reverts to the item's standard
// rate rather than keeping the stale tiered rate.
async function onLineQtyChange(line) {
  calcLine(line);
  if (line.item_code && form.price_list) {
    const rate = await fetchItemPriceRate(line.item_code, form.price_list, line.qty);
    line.rate = (rate !== null && rate > 0) ? rate : (line._standardRate ?? line.rate);
    calcLine(line);
  }
}
// ── Batch picker (batch-tracked items only) ─────────────────────────────
// Mirrors the Bills.vue pattern: search existing batches for the item, show
// each option's live available Qty, and let the row track the currently
// selected batch's Qty/expiry so batchQtyError() can enforce it client-side
// (the same check is re-run server-side in Sales Invoice.validate_batches).
async function fetchLineBatches(line, q = "") {
  if (!line.item_code) { line.batchOptions = []; return; }
  const itemCode = line.item_code;
  try {
    const rows = await apiGET("zoho_books_clone.api.inventory.get_batches_for_item", { item_code: itemCode, search: q || "" }) || [];
    if (line.item_code !== itemCode) return; // item changed again while awaiting
    line.batchOptions = rows.map(b => ({
      value: b.batch_no,
      label: `${b.batch_no}(qty:${flt(b.qty)})`,
      qty: flt(b.qty),
      expiry_date: b.expiry_date || "",
    }));
    // Keep the already-selected batch's Qty/expiry in sync with fresh data.
    if (line.batch_no) {
      const m = line.batchOptions.find(o => o.value === line.batch_no);
      if (m) { line._batchQty = m.qty; line.batch_expiry_date = m.expiry_date; }
    }
  } catch { if (line.item_code === itemCode) line.batchOptions = []; }
}
function onLineBatchSelect(line, opt) {
  line.batch_no = opt?.value ?? opt;
  const m = line.batchOptions.find(o => o.value === line.batch_no);
  line._batchQty = m ? m.qty : null;
  line.batch_expiry_date = m ? m.expiry_date : "";
}
// Returns a human-readable error string when the entered Qty exceeds the
// selected batch's available stock, or "" when the row is fine. Used both to
// show an inline warning and to block Save/Submit until it's resolved.
// Batch selection is only mandatory when this invoice will actually move
// stock (form.update_stock) — a plain accounting-only invoice (Delivery Note
// or nothing owns the stock movement) never touches a batch, so requiring
// one here would block otherwise-valid invoices for no reason.
function batchQtyError(line) {
  if (!line.has_batch_no || !line.item_code || !form.update_stock) return "";
  if (!line.batch_no) return `${line.item_name || line.item_code} is batch-tracked — select a Batch No`;
  if (line._batchQty == null) return "";
  if (flt(line.qty) > flt(line._batchQty)) {
    return `${line.item_name || line.item_code} — Batch ${line.batch_no} exceeds stock (Available: ${line._batchQty}, Entered: ${flt(line.qty)})`;
  }
  return "";
}

function salesPersonLabel(id) {
  const sp = salesPersons.value.find(p => p.name === id);
  return sp ? sp.label : id;
}
async function loadItems() {
  try { const r=await apiList("Item",{fields:["name","item_name","barcode","standard_rate","mrp","stock_uom","description","hsn_code","income_account"],filters:[["disabled","=",0],["has_variants","=",0],["is_sales_item","=",1]],limit:100000,order:"item_name asc"})||[]; items.value=r.map(x=>({...x,value:x.name,label:x.item_name||x.name})); } catch {}
}
async function loadTaxAccount() {
  try {
    const co=await resolveCompany();
    console.log("[BooksCompany][Invoices.vue] loadTaxAccount() resolveCompany() (Account lookup) ->", co);
    const r=await apiList("Account",{fields:["name"],filters:[["company","=",co],["account_type","=","Tax"],["is_group","=",0]],limit:1});
    taxAccountHead.value=r[0]?.name||"";
  } catch {}
  try {
    const templates=await apiList("Tax Template",{fields:["name","template_name","tax_type"],filters:[["disabled","=",0]],limit:100,order:"template_name asc"});
    const withRates=await Promise.all((templates||[]).map(async t=>{
      try{
        const doc=await apiGet("Tax Template",t.name);
        // Keep the full component rows — computeTaxRows reads them (with per-row
        // account heads) and picks CGST+SGST vs IGST by Place of Supply. `rate`
        // (summed) is retained only for legacy fallback / simple estimate views.
        const rows=(doc?.taxes||[]);
        const rate=rows.reduce((s,r)=>s+(Number(r.rate)||0),0);
        const account=rows?.[0]?.account_head||taxAccountHead.value;
        return{name:t.name,template_name:t.template_name,tax_type:t.tax_type||doc?.tax_type||"GST",rate:Number(rate),account,taxes:rows};
      }catch{return{name:t.name,template_name:t.template_name,tax_type:t.tax_type||"GST",rate:0,account:taxAccountHead.value,taxes:[]};}
    }));
    taxTemplates.value=withRates;
  }catch{taxTemplates.value=[];}
  // Company GST state + Output GST accounts for intra/inter split.
  try {
    const co=await resolveCompany();
    console.log("[BooksCompany][Invoices.vue] loadTaxAccount() resolveCompany() (GST state lookup) ->", co);
    const bc=await apiGet("Books Company",co);
    companyGstState.value=bc?.gst_state||bc?.state||"";
    gstAccounts.value=await apiGET("zoho_books_clone.api.gst.get_gst_accounts",{company:co})||{};
  } catch {}
}

// ── Sorting & selection ────────────────────────────────────────────────
function sort(key) { sortKey.value===key?(sortDir.value*=-1):(sortKey.value=key,sortDir.value=-1); }
function sortArrow(k) { return sortKey.value!==k?"":sortDir.value===1?"↑":"↓"; }
function toggleAll(e) { if(e.target.checked) sorted.value.forEach(i=>selectedRows.value.add(i.name)); else selectedRows.value.clear(); selectedRows.value=new Set(selectedRows.value); }
function toggleRow(name) { const s=new Set(selectedRows.value); s.has(name)?s.delete(name):s.add(name); selectedRows.value=s; }

// ── Line item helpers ──────────────────────────────────────────────────
function addLine() { lines.value.push({id:Date.now(),item_code:"",item_name:"",description:"",hsn_code:"",qty:1,rate:0,uom:"Nos",discount_percentage:0,discount_amount:0,amount:0,tax_code:"",income_account:"",collapsed:false,has_batch_no:0,batch_no:"",batch_expiry_date:"",batchOptions:[],_batchQty:null}); }

// ── Barcode scanning ──────────────────────────────────────────────────
// Resolves a scanned code to an Item and either bumps the qty of an
// existing line for that item, or fills the first empty line / appends a
// new one. Works for both the hardware-scanner (keyboard-wedge) and
// camera scan paths — both funnel into this one handler.
async function handleBarcodeScan(code) {
  code = (code || "").trim();
  if (!code) return;
  if (!drawerOpen.value) { toast("Open an invoice to scan items into it", "error"); return; }
  let item = items.value.find(i => i.barcode === code) || items.value.find(i => i.name === code);
  if (!item) {
    try { item = await apiGET("zoho_books_clone.api.inventory.get_item_by_barcode", { barcode: code }); } catch { item = null; }
  }
  if (!item) { toast(`No item found for barcode "${code}"`, "error"); return; }

  const existing = lines.value.find(l => l.item_code === item.name);
  if (existing) {
    existing.qty = flt(existing.qty) + 1;
    onLineQtyChange(existing);
    calcLine(existing);
    toast(`${existing.item_name || item.name}: qty ${existing.qty}`, "success");
    return;
  }
  let line = lines.value.find(l => !l.item_code);
  if (!line) {
    line = {id:Date.now(),item_code:"",item_name:"",description:"",hsn_code:"",qty:1,rate:0,uom:"Nos",discount_percentage:0,discount_amount:0,amount:0,tax_code:"",income_account:"",collapsed:false,has_batch_no:0,batch_no:"",batch_expiry_date:"",batchOptions:[],_batchQty:null};
    lines.value.push(line);
  }
  line.item_code = item.name;
  await onItemChange(line);
  toast(`Added ${line.item_name || item.name}`, "success");
}

const { cameraSupported: scanCameraSupported, cameraOpen: scanCameraOpen, cameraError: scanCameraError, videoRef: scanVideoRef, openCamera: openScanCamera, closeCamera: closeScanCamera }
  = useBarcodeScanner({ onScan: handleBarcodeScan });
function removeLine(id) { lines.value=lines.value.filter(l=>l.id!==id); }
function calcLine(line) {
  if (line.discount_percentage > 100) line.discount_percentage = 100;
  if (line.discount_percentage < 0)   line.discount_percentage = 0;
  const base=Math.round(flt(line.qty)*flt(line.rate)*100)/100;
  const disc=Math.round(base*flt(line.discount_percentage)/100*100)/100;
  line.discount_amount=disc;
  line.amount=base-disc;
}

async function onItemChange(line) {
  // Item changed — any previously selected batch no longer applies.
  line.batch_no=""; line.batch_expiry_date=""; line.batchOptions=[]; line._batchQty=null; line.has_batch_no=0;
  const it=items.value.find(i=>i.name===line.item_code);
  if (it) {
    line.item_name=it.item_name||it.name;
    line.rate=flt(it.standard_rate);
    line._standardRate=flt(it.mrp)||flt(it.standard_rate);
    line.uom=it.stock_uom||"Nos";
    if (it.description) line.description=it.description;
    if (it.hsn_code) line.hsn_code=it.hsn_code;
    // Carry the Item master's own Default Income Account onto the line, so
    // the backend fallback in save_doc (Sales Revenue) is only used when the
    // Item genuinely has no income_account of its own.
    line.income_account=it.income_account||"";
    calcLine(line);
  }
  if (line.item_code) {
    try {
      const doc=await apiGet("Item",line.item_code);
      if (doc?.item_name) line.item_name=doc.item_name;
      if (doc?.description) line.description=doc.description;
      if (doc?.hsn_code) line.hsn_code=doc.hsn_code;
      if (!flt(line.rate)&&doc?.standard_rate) { line.rate=flt(doc.standard_rate); }
      line._standardRate=flt(doc?.mrp)||flt(doc?.standard_rate)||line._standardRate||0;
      if (doc?.stock_uom) line.uom=doc.stock_uom;
      if (doc?.tax_code) line.tax_code=doc.tax_code;
      if (doc?.income_account) line.income_account=doc.income_account;
      line.has_batch_no=doc?.has_batch_no?1:0;
      calcLine(line);
    } catch {}
    if (line.has_batch_no) await fetchLineBatches(line, "");
  }
  // Price List override: when a Price List is selected on the invoice and it
  // has an explicit Item Price for this item, that rate takes priority over
  // the Item's standard_rate looked up above. If the current qty doesn't meet
  // any tier's minimum, fetchItemPriceRate returns null and the standard rate
  // (already set above) is left in place.
  if (line.item_code && form.price_list) {
    const plRate = await fetchItemPriceRate(line.item_code, form.price_list, line.qty);
    if (plRate !== null && plRate > 0) { line.rate = plRate; calcLine(line); }
  }
}

// ── Payment Terms ──────────────────────────────────────────────────────
function applyPaymentTerms() {
  if (!form.posting_date||!form.payment_terms) return;
  const days={"Due on Receipt":0,"Net 7":7,"Net 15":15,"Net 30":30,"Net 45":45,"Net 60":60,"Net 90":90}[form.payment_terms]??30;
  const d=new Date(form.posting_date); d.setDate(d.getDate()+days);
  form.due_date=d.toISOString().slice(0,10);
}

// ── Customer change: auto-fill address, currency, GST treatment ───────
async function onCustomerChange() {
  form.billing_address=""; form.billing_address_name="";
  form.shipping_address=""; form.shipping_address_name="";
  customerAddresses.value=[];
  if (!form.customer) return;
  addressLoading.value=true;
  try {
    const custDoc = await apiGet("Customer", form.customer);
    form.currency = "INR";
    form.exchange_rate = 1;
    // Apply payment terms
    if (custDoc?.payment_terms && !form.payment_terms) { form.payment_terms = custDoc.payment_terms; applyPaymentTerms(); }
    // Apply GST treatment
    form.gst_treatment = custDoc?.gst_treatment || "";
    if (form.gst_treatment === "Overseas" || form.gst_treatment === "SEZ") {
      lines.value.forEach(l => { l.tax_code = ""; });
      if (form.gst_treatment === "Overseas") form.place_of_supply = "";
    }
    // Load addresses from master
    await fetchCustomerAddresses(form.customer);
    const firstBilling = customerAddresses.value.find(a => a.address_type === "Billing") || customerAddresses.value[0];
    if (firstBilling) { form.billing_address_name = firstBilling.name; form.billing_address = formatAddress(firstBilling); }
    const firstShipping = customerAddresses.value.find(a => a.address_type === "Shipping");
    if (firstShipping) { form.shipping_address_name = firstShipping.name; form.shipping_address = formatAddress(firstShipping); }
    // Auto-fill Place of Supply so GST tax templates (which key off intra vs.
    // inter-state) apply out of the box — previously this stayed blank unless
    // picked manually, which silently zeroed CGST/SGST-only templates.
    if (form.gst_treatment !== "Overseas" && !form.place_of_supply) {
      form.place_of_supply = matchIndianState(firstBilling?.state) || matchIndianState(custDoc?.state) || "";
    }
  } catch {}
  addressLoading.value=false;
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
      if (addrModal.forField === "billing") { form.billing_address_name = newAddr.name; form.billing_address = formatAddress(newAddr); }
      else { form.shipping_address_name = newAddr.name; form.shipping_address = formatAddress(newAddr); }
    }
    addrModal.open = false;
  } catch (e) { toast.error(e.message || "Failed to save address"); }
  addrModal.saving = false;
}

// ── Copy last items ────────────────────────────────────────────────────
async function copyLastItems() {
  if (!form.customer) return;
  try {
    const r=await apiGET("zoho_books_clone.api.docs.get_party_last_items",{party_type:"Customer",party:form.customer,limit:20});
    if (r?.items?.length) {
      const newLines=r.items.map((it,i)=>({id:Date.now()+i,item_code:it.item_code||"",item_name:it.item_name||"",description:it.description||"",hsn_code:"",qty:flt(it.qty)||1,rate:flt(it.rate)||0,uom:"Nos",discount_percentage:0,discount_amount:0,amount:Math.round(flt(it.qty)*flt(it.rate)*100)/100,tax_code:it.tax_code||"",income_account:it.income_account||"",collapsed:false,has_batch_no:0,batch_no:"",batch_expiry_date:"",batchOptions:[],_batchQty:null}));
      lines.value=[...lines.value,...newLines];
      // Resolve has_batch_no for the copied lines so batch-tracked items
      // immediately show the Batch No picker instead of only after a manual
      // item re-select.
      for (const line of newLines) {
        if (!line.item_code) continue;
        try {
          line.has_batch_no = (await apiList("Item", { fields: ["has_batch_no"], filters: [["name","=",line.item_code]], limit: 1 }))[0]?.has_batch_no ? 1 : 0;
        } catch { continue; }
        if (line.has_batch_no) await fetchLineBatches(line, "");
      }
      toast("Copied "+r.items.length+" items from last invoice");
    } else toast("No previous items found for this customer","info");
  } catch (e) { toast("Could not copy items: "+e.message,"error"); }
}

// ── Drawer open ────────────────────────────────────────────────────────
function openAdd() {
  editingName.value=null;
  moreActionsOpen.value=false;
  Object.assign(collapsed,{branding:false,details:false,billing:true,lines:false,notes:true});
  lines.value=[{id:Date.now(),item_code:"",item_name:"",description:"",hsn_code:"",qty:1,rate:0,uom:"Nos",discount_percentage:0,discount_amount:0,amount:0,tax_code:"",income_account:"",collapsed:false,has_batch_no:0,batch_no:"",batch_expiry_date:"",batchOptions:[],_batchQty:null}];
  Object.assign(form,{customer:"",posting_date:todayStr(),due_date:dueDateDefault(),po_no:"",payment_terms:"Net 30",place_of_supply:"33-Tamil Nadu",billing_address:"",billing_address_name:"",shipping_address:"",shipping_address_name:"",terms:"",remarks:"",docstatus:0,currency:"INR",exchange_rate:1,gst_treatment:"",price_list:"",update_stock:1,set_warehouse:"",logo:"",cost_center:"",sales_person:"",discount_type:"Percentage",additional_discount_percentage:0,additional_discount_amount:0});
  customerAddresses.value=[];
  customerBillingAddrs.value=[]; customerShippingAddrs.value=[]; sameAsBillingAddr.value=false;
  fetchWarehouses("");
  drawerOpen.value=true;
}
async function openEdit(inv) {
  editingName.value=inv.name;
  Object.assign(form,{customer:inv.customer||"",currency:inv.currency||"INR",exchange_rate:inv.exchange_rate||1,price_list:inv.price_list||"",posting_date:inv.posting_date||todayStr(),due_date:inv.due_date||dueDateDefault(),po_no:"",payment_terms:"",place_of_supply:"33-Tamil Nadu",billing_address:"",billing_address_name:"",shipping_address:"",shipping_address_name:"",terms:"",remarks:"",docstatus:inv.docstatus||0,update_stock:1,set_warehouse:"",sales_person:inv.sales_person||"",discount_type:"Percentage",additional_discount_percentage:0,additional_discount_amount:0});
  customerAddresses.value=[];
  lines.value=[{id:Date.now(),item_code:"",item_name:"",description:"",hsn_code:"",qty:1,rate:0,uom:"Nos",discount_percentage:0,discount_amount:0,amount:0,tax_code:"",income_account:"",collapsed:false,has_batch_no:0,batch_no:"",batch_expiry_date:"",batchOptions:[],_batchQty:null}];
  fetchWarehouses("");
  drawerOpen.value=true;
  const [doc] = await Promise.all([
    apiGet("Sales Invoice",inv.name).catch(()=>({})),
    fetchCustomerAddresses(inv.customer||""),
  ]);
  if (doc && doc.name) {
    Object.assign(form,{
      customer:doc.customer||"",posting_date:doc.posting_date||todayStr(),due_date:doc.due_date||dueDateDefault(),
      po_no:doc.po_no||"",payment_terms:doc.payment_terms||"",place_of_supply:doc.place_of_supply||"",
      billing_address:doc.billing_address||"",billing_address_name:doc.billing_address_name||"",
      shipping_address:doc.shipping_address||"",shipping_address_name:doc.shipping_address_name||"",
      terms:doc.terms||"",remarks:doc.remarks||"",docstatus:doc.docstatus||0,
      currency:doc.currency||"INR",exchange_rate:doc.exchange_rate||1,gst_treatment:doc.gst_category||"",
      price_list:doc.price_list||"",
      update_stock:1,set_warehouse:doc.set_warehouse||"",
      logo:doc.logo||"",cost_center:doc.cost_center||"",sales_person:doc.sales_person||"",
      discount_type:doc.discount_type||"Percentage",
      additional_discount_percentage:flt(doc.additional_discount_percentage)||0,
      additional_discount_amount:flt(doc.additional_discount_amount)||0,
    });
    lines.value=(doc.items||[]).map((it,i)=>({id:Date.now()+i,item_code:it.item_code||"",item_name:it.item_name||"",description:it.description||"",hsn_code:it.hsn_code||"",qty:flt(it.qty)||1,rate:flt(it.rate)||0,_standardRate:flt(it.mrp)||0,uom:it.uom||"Nos",discount_percentage:flt(it.discount_percentage)||0,discount_amount:flt(it.discount_amount)||0,amount:flt(it.amount)||0,tax_code:it.tax_code||"",income_account:it.income_account||"",collapsed:false,has_batch_no:0,batch_no:it.batch_no||"",batch_expiry_date:it.batch_expiry_date||"",batchOptions:[],_batchQty:null}));
    if (!lines.value.length) addLine();
    // Base Price is a read-only reference showing the Item's own standard_rate
    // (independent of whatever rate/discount ended up on the saved line), so
    // it needs to be resolved from the Item master rather than the invoice row.
    await Promise.all(lines.value.map(async (line) => {
      if (!line.item_code) return;
      const it = items.value.find(i => i.name === line.item_code);
      if (it) { line._standardRate = flt(it.mrp) || flt(it.standard_rate); } else {
        try { const idoc = await apiGet("Item", line.item_code); line._standardRate = flt(idoc?.mrp) || flt(idoc?.standard_rate) || 0; } catch { line._standardRate = 0; }
      }
      // Resolve has_batch_no so the Batch No picker shows up for batch-tracked
      // items already saved on this invoice, and load its batch options so the
      // saved batch's live Available Qty / expiry can be checked against.
      try {
        line.has_batch_no = (await apiList("Item", { fields: ["has_batch_no"], filters: [["name","=",line.item_code]], limit: 1 }))[0]?.has_batch_no ? 1 : 0;
      } catch { line.has_batch_no = 0; }
      if (line.has_batch_no) await fetchLineBatches(line, "");
    }));
  }
}
async function openView(inv) {
  viewInv.value=inv; viewOpen.value=true; viewTab.value="details"; viewPayments.value=[]; viewCreditApps.value=[]; viewLoading.value=true;
  try { const full=await apiGet("Sales Invoice",inv.name); viewInv.value=full; } catch {}
  viewLoading.value=false;
}

// ── Save invoice ───────────────────────────────────────────────────────
// Fetch fiscal year lock dates so we can block saves client-side immediately.
async function loadFYLockDates() {
  try {
    const co = await resolveCompany();
    const rows = await apiList("Fiscal Year", {
      fields: ["name", "year_start_date", "year_end_date", "lock_date"],
      filters: [["is_closed", "=", 0]],
      limit: 50,
    }).catch(() => []);
    fyLockDates.value = (rows || [])
      .filter(r => r.lock_date)
      .map(r => ({ start: r.year_start_date, end: r.year_end_date, lock_date: r.lock_date }));
  } catch { fyLockDates.value = []; }
}

function checkPostingDateLocked(posting_date) {
  if (!posting_date) return null;
  for (const fy of fyLockDates.value) {
    if (posting_date >= fy.start && posting_date <= fy.end) {
      if (posting_date <= fy.lock_date) return fy.lock_date;
    }
  }
  return null;
}

async function saveInvoice(docstatus, andNew = false) {
  if (!(editingName.value ? canEdit("invoices") : canCreate("invoices"))) { toast("Read-only access", "error"); return; }
  if (!form.customer) { toast("Customer is required","error"); return; }
  if (!form.posting_date) { toast("Invoice date is required","error"); return; }
  if (lines.value.some(l => (l.description||'').length > 500)) { toast("Item description cannot exceed 500 characters","error"); return; }
  if ((form.terms||'').length > 500) { toast("Customer Note cannot exceed 500 characters","error"); return; }
  if ((form.remarks||'').length > 500) { toast("Internal Remarks cannot exceed 500 characters","error"); return; }
  if (!lines.value.some(l=>l.item_code&&flt(l.qty)>0)) { toast("Add at least one line item","error"); return; }
  if (!form.set_warehouse) { toast("Dispatch Warehouse is required","error"); return; }
  // Batch-tracked lines must have a batch selected, and can't sell more than
  // that batch currently has in stock (also enforced server-side).
  const batchErr = lines.value.filter(l=>l.item_code).map(batchQtyError).find(Boolean);
  if (batchErr) { toast(batchErr,"error"); return; }
  // Check if the posting date falls in a locked fiscal period before hitting the server.
  const lockedUpTo = checkPostingDateLocked(form.posting_date);
  if (lockedUpTo) {
    toast(`This period is locked up to ${lockedUpTo}. Unlock the period in Fiscal Years settings to save this invoice.`, "error");
    return;
  }
  drawerSaving.value=true;
  try {
    const company=await resolveCompany();
    const invItems=lines.value.filter(l=>l.item_code).map(l=>({item_code:l.item_code,item_name:l.item_name||l.item_code,description:l.description||l.item_name||l.item_code,qty:flt(l.qty),rate:flt(l.rate),mrp:flt(l._standardRate)||0,uom:l.uom||"Nos",amount:flt(l.amount),hsn_code:l.hsn_code||"",discount_percentage:flt(l.discount_percentage)||0,discount_amount:flt(l.discount_amount)||0,tax_code:l.tax_code||"",income_account:l.income_account||"",batch_no:l.has_batch_no?(l.batch_no||""):"",batch_expiry_date:l.has_batch_no?(l.batch_expiry_date||""):""}));
    const taxes=computeTaxRows(discountedLines.value.filter(l=>l.item_code), taxTemplates.value, {
      companyState: companyGstState.value,
      placeOfSupply: form.place_of_supply,
      gst: { cgst: gstAccounts.value.output_cgst, sgst: gstAccounts.value.output_sgst, igst: gstAccounts.value.output_igst },
      defaultAccount: taxAccountHead.value,
    }).map(r=>({doctype:"Tax Line",charge_type:"On Net Total",account_head:r.account_head,description:r.description,rate:r.rate,tax_type:r.tax_type,tax_amount:r.amount}));
    const shipAddr=sameAsBillingAddr.value?form.billing_address:form.shipping_address||"";

    // If form.logo is still a data URL it means the background upload failed or
    // this is a brand-new invoice (no docname yet). Strip it from the initial
    // save payload — Frappe will reject a base64 blob in a Link/Attach field.
    const pendingDataUrl = (form.logo||"").startsWith("data:") ? form.logo : "";
    const resolvedLogoPath = pendingDataUrl ? "" : (form.logo || "");

    const doc={doctype:"Sales Invoice",customer:form.customer,posting_date:form.posting_date,due_date:form.due_date||form.posting_date,po_no:form.po_no||"",payment_terms:form.payment_terms||"",billing_address:form.billing_address||"",billing_address_name:form.billing_address_name||"",shipping_address:shipAddr,shipping_address_name:form.shipping_address_name||"",place_of_supply:form.place_of_supply||"",remarks:form.remarks||"",terms:form.terms||"",items:invItems,taxes,company,currency:form.currency||"INR",price_list:form.price_list||"",exchange_rate:form.currency==="INR"?1:(form.exchange_rate||1),gst_category:form.gst_treatment==="Overseas"?"Overseas":form.gst_treatment==="SEZ"?"SEZ":"Regular",update_stock:1,set_warehouse:form.set_warehouse||"",logo:resolvedLogoPath,cost_center:form.cost_center||"",sales_person:form.sales_person||"",discount_type:form.discount_type||"Percentage",additional_discount_percentage:form.discount_type==="Percentage"?flt(form.additional_discount_percentage):0,additional_discount_amount:flt(discountAmount.value)};
    if (editingName.value) doc.name=editingName.value;
    const saved=await apiSave(doc);
    // Lock onto the saved docname right away — if a stray second saveInvoice()
    // call slips in before this function returns (e.g. a fast double-click),
    // it must see this as an update to the same invoice, not build another
    // nameless doc and insert a duplicate Sales Invoice.
    if (saved?.name) editingName.value = saved.name;

    // Now we have a docname — upload the pending logo and link it to the doc.
    if (pendingDataUrl && saved?.name) {
      try {
        const [meta, b64] = pendingDataUrl.split(",");
        const mime = meta.match(/:(.*?);/)?.[1] || "image/png";
        const ext  = mime.split("/")[1]?.split("+")[0] || "png";
        const bytes = atob(b64);
        const arr = new Uint8Array(bytes.length);
        for (let i=0;i<bytes.length;i++) arr[i]=bytes.charCodeAt(i);
        const blob = new Blob([arr], {type: mime});
        const fd = new FormData();
        fd.append("file", blob, `logo.${ext}`);
        fd.append("is_private", "0");
        fd.append("folder", "Home/Attachments");
        fd.append("doctype", "Sales Invoice");
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
          // Patch logo_attach on the already-saved doc so it persists
          await apiPOST("frappe.client.set_value", {
            doctype: "Sales Invoice",
            name: saved.name,
            fieldname: "logo",
            value: fileUrl,
          });
        }
      } catch(uploadErr) {
        console.warn("Logo upload on save failed:", uploadErr);
        // Non-fatal: invoice is saved, logo just won't be persisted
      }
    }

    if (docstatus===1) await apiSubmit("Sales Invoice",saved.name);
    await load();
    if (andNew) {
      toast("Invoice saved as draft — opening new invoice");
      openAdd();
    } else {
      toast(docstatus===1?"Invoice submitted":"Invoice saved as draft");
      drawerOpen.value=false;
    }
  } catch(e) { toast("Save failed: "+e.message,"error"); }
  drawerSaving.value=false;
}

// ── Payment modal ──────────────────────────────────────────────────────
// Phase 0.9 — delegates to the globally mounted PaymentDialog. Same UX as Bills
// (vendor payments) but `direction:"receive"` for customer side.
async function openPayment(inv) {
  if (!canEdit("invoices")) { toast("Read-only access", "error"); return; }
  const { openPayment: openShared } = usePaymentDialog();
  const paymentName = await openShared({
    direction: "receive",
    doctype: "Sales Invoice", name: inv.name,
    party: inv.customer, partyLabel: inv.customer_name || inv.customer,
    balance: flt(inv.outstanding_amount),
    getDefaultsEndpoint: "zoho_books_clone.api.books_data.get_payment_defaults",
    sendEndpoint:        "zoho_books_clone.api.books_data.record_payment",
    paramKey: "invoice_name",
  });
  if (paymentName) {
    await load();
    if (viewOpen.value && viewInv.value?.name === inv.name) await openView(inv);
  }
}
// submitPayment() removed — PaymentDialog handles submission.

// ── Load payments (view tab) ───────────────────────────────────────────
async function loadPayments(invName) {
  if (viewPayments.value.length || viewCreditApps.value.length) return;
  viewPaymentsLoading.value = true;
  try {
    const [payments, creditApps] = await Promise.all([
      apiGET("zoho_books_clone.api.docs.get_invoice_payments", { invoice_name: invName }).catch(() => []),
      apiGET("zoho_books_clone.api.docs.get_invoice_credit_applications", { invoice_name: invName }).catch(() => []),
    ]);
    viewPayments.value = payments || [];
    viewCreditApps.value = creditApps || [];
  } catch(e) { console.warn("loadPayments failed:", e.message); viewPayments.value = []; viewCreditApps.value = []; }
  viewPaymentsLoading.value = false;
}

// ── Email ──────────────────────────────────────────────────────────────
async function openEmail(inv) {
  // Phase 0.9 refactor — delegate to the globally mounted EmailDialog.
  // This gives Invoices the same email UX as Bills / Quotes / SO / PO and
  // removes ~50 lines of inline modal duplication. The legacy inline modal
  // template + sendEmail/enhanceEmail handlers remain in the file as fallback
  // but are no longer opened (emailModal.open stays false).
  const { openEmail: openShared } = useEmailDialog();
  await openShared({
    doctype: "Sales Invoice", name: inv.name, docLabel: `Invoice ${inv.name}`,
    getDefaultsEndpoint: "zoho_books_clone.api.docs.get_invoice_email_defaults",
    sendEndpoint:        "zoho_books_clone.api.docs.send_invoice_email",
    enhanceEndpoint:     "zoho_books_clone.api.books_data.ai_enhance_email",
    paramKey: "invoice_name",
    printConfig: { title: "INVOICE", partyLabel: "Bill To", partyField: "customer_name" },
  });
}
// sendEmail / enhanceEmail removed — EmailDialog handles both via its
// `sendEndpoint` + `enhanceEndpoint` props.

// ── Duplicate ──────────────────────────────────────────────────────────
async function duplicateInvoice(inv) {
  if (!canCreate("invoices")) { toast("Read-only access", "error"); return; }
  try {
    const doc=await apiGet("Sales Invoice",inv.name);
    delete doc.name; doc.docstatus=0; doc.posting_date=todayStr(); doc.due_date=dueDateDefault(); doc.outstanding_amount=0; doc.status="Draft";
    (doc.items||[]).forEach(it=>{ delete it.name; });
    (doc.taxes||[]).forEach(tx=>{ delete tx.name; });
    const saved=await apiSave(doc);
    toast("Duplicated as "+saved.name);
    await load();
  } catch(e) { toast("Duplicate failed: "+e.message,"error"); }
}

// ── Cancel / Delete ────────────────────────────────────────────────────
async function submitInv(inv) {
  if (!canEdit("invoices")) { toast("Read-only access", "error"); return; }
  Object.assign(confirmModal, {
    open: true, loading: false, payments: [],
    title: "Submit Invoice",
    message: `Submit ${inv.name}? This will post it to the ledger and it can no longer be edited.`,
    actionLabel: "Submit Invoice",
    action: async () => {
      confirmModal.loading = true;
      try {
        await apiSubmit("Sales Invoice", inv.name);
        // Check auto_send_invoice setting for contextual toast only.
        // The actual email is fired server-side inside on_submit so it
        // works regardless of how the invoice is submitted.
        try {
          const csrf = window.frappe?.csrf_token || "";
          const res = await fetch("/api/method/zoho_books_clone.api.admin.get_company_settings", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded", "X-Frappe-CSRF-Token": csrf },
            credentials: "same-origin",
            body: new URLSearchParams({}),
          });
          const data = await res.json();
          const autoSend = (data.message || {}).auto_send_invoice;
          toast(autoSend ? "Invoice submitted \u2014 email sent to customer" : "Invoice submitted");
        } catch {
          toast("Invoice submitted");
        }
        confirmModal.open = false;
        await load();
        await openView({ name: inv.name });
      } catch(e) {
        confirmModal.open = false;
        if (e.message !== "Submission cancelled by user") toast(e.message || "Submit failed", "error");
      }
    },
  });
}
async function confirmAction(action, inv) {
  if (action === "delete" ? !canDelete("invoices") : !canEdit("invoices")) { toast(action === "delete" ? "Not permitted" : "Read-only access", "error"); return; }
  if (action==="cancel") {
    const isPaid = inv.outstanding_amount <= 0 && inv.docstatus === 1;
    if (isPaid) {
      // Load linked payments so we can show them in the dialog
      let payments = [];
      try { payments = await apiGET("zoho_books_clone.api.docs.get_invoice_payments", {invoice_name: inv.name}) || []; } catch(e) { /* show dialog anyway */ }
      Object.assign(confirmModal, {
        open: true, loading: false, payments,
        title: "Cancel Invoice & Payment",
        message: `Cancel invoice ${inv.name}? This will reverse all GL entries.`,
        actionLabel: "Cancel Invoice & Payment",
        action: async () => {
          confirmModal.loading = true;
          try {
            await apiPOST("zoho_books_clone.api.docs.cancel_invoice_with_payments", {invoice_name: inv.name});
            toast("Invoice and linked payment(s) cancelled");
            confirmModal.open = false;
            viewOpen.value = false;
            await load();
          } catch(e) {
            toast(e.message || "Cancel failed", "error");
            confirmModal.loading = false;
          }
        },
      });
    } else {
      Object.assign(confirmModal,{open:true,loading:false,payments:[],title:"Cancel Invoice",message:`Cancel ${inv.name}? This will reverse all GL entries. This cannot be undone.`,actionLabel:"Cancel Invoice",action:async()=>{confirmModal.loading=true;try{await apiCancel("Sales Invoice",inv.name);toast("Invoice cancelled");viewOpen.value=false;await load();}catch(e){toast(e.message||"Cancel failed","error");}confirmModal.open=false;}});
    }
  } else {
    Object.assign(confirmModal,{open:true,loading:false,payments:[],title:"Delete Invoice",message:`Permanently delete draft ${inv.name}? This cannot be undone.`,actionLabel:"Delete",action:async()=>{confirmModal.loading=true;try{await apiDelete("Sales Invoice",inv.name);toast("Invoice deleted");viewOpen.value=false;await load();}catch(e){toast(e.message||"Delete failed","error");}confirmModal.open=false;}});
  }
}

// ── Credit Note ────────────────────────────────────────────────────────
// Phase 0.9 — delegates to the globally mounted ReturnNoteDialog. The shared
// dialog already pre-fills items from the invoice and warns about existing CNs.
async function openCreditNote(inv) {
  // Always re-fetch the invoice to get the latest items, taxes, and outstanding
  let freshInv = inv;
  try { freshInv = await apiGet("Sales Invoice", inv.name); } catch {}

  const { openReturnNote } = useReturnNote();
  const result = await openReturnNote({
    kind: "credit",
    parentName: freshInv.name,
    party: freshInv.customer,
    items: (freshInv.items || []).map(it => ({
      item_code: it.item_code, item_name: it.item_name,
      description: it.description, qty: it.qty, rate: it.rate,
      uom: it.uom, batch_no: it.batch_no, batch_expiry_date: it.batch_expiry_date,
    })),
    taxes: (freshInv.taxes || []).map(t => ({
      tax_type: t.account_head, description: t.description, rate: t.rate,
    })),
    invoiceTotal: flt(freshInv.grand_total),
    existingEndpoint: "zoho_books_clone.api.docs.get_credit_notes",
    createEndpoint:   "zoho_books_clone.api.docs.create_credit_note",
    paramKey:  "invoice_name",
    partyKey:  "customer",
    parentKey: "against_invoice",
  });
  if (result) { viewOpen.value = false; await load(); }
}
// submitCreditNote removed — ReturnNoteDialog handles submission via its
// `createEndpoint` prop. openCreditNote() above now resolves a promise with
// the created CN name.

// ── Make Recurring ─────────────────────────────────────────────────────
async function makeRecurring(inv) {
  const { openMakeRecurring } = useMakeRecurring();
  const subName = await openMakeRecurring({
    doctype: "Sales Invoice",
    name: inv.name,
    partyLabel: inv.customer_name || inv.customer || "",
    amount: inv.grand_total || 0,
  });
  if (subName) toast(`Recurring subscription ${subName} created`);
}

// ── Bulk actions ───────────────────────────────────────────────────────
async function bulkDelete() {
  if (!canDelete("invoices")) { toast("Not permitted", "error"); return; }
  const drafts=sorted.value.filter(i=>selectedRows.value.has(i.name)&&i.docstatus===0);
  if (!drafts.length) { toast("No draft invoices selected","info"); return; }
  for (const inv of drafts) { try { await apiDelete("Sales Invoice",inv.name); } catch {} }
  selectedRows.value=new Set(); toast(`Deleted ${drafts.length} draft invoice(s)`); await load();
}
async function bulkCancel() {
  if (!canEdit("invoices")) { toast("Read-only access", "error"); return; }
  const submitted=sorted.value.filter(i=>selectedRows.value.has(i.name)&&i.docstatus===1);
  if (!submitted.length) { toast("No submitted invoices selected","info"); return; }
  let done=0, failed=0;
  for (const inv of submitted) {
    try {
      const isPaid = inv.outstanding_amount <= 0;
      if (isPaid) {
        await apiPOST("zoho_books_clone.api.docs.cancel_invoice_with_payments", {invoice_name: inv.name});
      } else {
        await apiCancel("Sales Invoice", inv.name);
      }
      done++;
    } catch(e) { failed++; toast(`${inv.name}: ${e.message||"cancel failed"}`, "error"); }
  }
  selectedRows.value=new Set();
  if (done) toast(`Cancelled ${done} invoice(s)${failed?`, ${failed} failed`:""}`);
  await load();
}
async function bulkPayment() {
  if (!canEdit("invoices")) { toast("Read-only access", "error"); return; }
  const payable = sorted.value.filter(i =>
    selectedRows.value.has(i.name) && i.docstatus === 1 && flt(i.outstanding_amount) > 0
  );
  if (!payable.length) {
    toast("No payable invoices selected — must be submitted with a balance due", "info");
    return;
  }
  const customers = new Set(payable.map(i => i.customer));
  if (customers.size > 1) {
    toast("Select invoices from a single customer to record one payment together", "error");
    return;
  }
  const { openPayment: openShared } = usePaymentDialog();
  const paymentName = await openShared({
    multi: true,
    direction: "receive",
    party: payable[0].customer,
    partyLabel: payable[0].customer_name || payable[0].customer,
    invoices: payable.map(i => ({
      name: i.name,
      due_date: i.due_date,
      outstanding_amount: flt(i.outstanding_amount),
    })),
    getDefaultsEndpoint: "zoho_books_clone.api.books_data.get_payment_defaults",
    sendEndpoint: "zoho_books_clone.api.books_data.record_payment_multi",
    paramKey: "invoice_name",
  });
  if (paymentName) {
    selectedRows.value = new Set();
    toast(`Payment recorded across ${payable.length} invoice(s)`);
    await load();
  }
}
async function bulkEmail() {
  if (!canEdit("invoices")) { toast("Read-only access", "error"); return; }
  const sel=sorted.value.filter(i=>selectedRows.value.has(i.name));
  if (!sel.length) return;
  if (sel.length===1) { openEmail(sel[0]); return; }
  toast(`Bulk email for ${sel.length} invoices — opening first invoice`,"info");
  openEmail(sel[0]);
}

// ── Export CSV ─────────────────────────────────────────────────────────
function exportCSV() {
  const source = selectedRows.value.size > 0
    ? sorted.value.filter(i => selectedRows.value.has(i.name))
    : sorted.value;
  if (!source.length) { toast("No invoices to export", "info"); return; }
  const headers=["Date","Invoice#","PO Number","Customer","Status","Due Date","Amount","Balance Due"];
  const rows=source.map(i=>[i.posting_date,i.name,i.po_no||"",i.customer_name||i.customer,statusLabel(i),i.due_date||"",i.grand_total,i.outstanding_amount]);
  const csv=[headers,...rows].map(r=>r.map(c=>`"${String(c).replace(/"/g,'""')}"`).join(",")).join("\n");
  const blob=new Blob(["﻿"+csv],{type:"text/csv;charset=utf-8"}); const url=URL.createObjectURL(blob);
  const a=document.createElement("a"); a.href=url; a.download=`invoices_${todayStr()}.csv`; a.click(); URL.revokeObjectURL(url);
  const label = selectedRows.value.size > 0 ? `${source.length} selected invoice(s)` : `${source.length} invoice(s)`;
  toast(`CSV exported — ${label}`);
}

// ── Branding persistence — loaded from Books Company settings ──
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
    if (d.company_logo) companyLogo.value = d.company_logo;
  } catch {}
}

// ── Logo helpers ────────────────────────────────────────────────────────
// Convert a Frappe file path (/files/...) or data-URL to a usable src for the PDF renderer.
function logoSrc(path) {
  if (!path) return "";
  if (path.startsWith("data:") || path.startsWith("http")) return path;
  // Frappe stores relative paths like /files/logo.png — prefix with origin.
  return (window.location.origin || "") + path;
}

// Upload a logo file to Frappe and store the returned URL in form.logo.
// Strategy:
//   - Existing invoice (editingName set): upload immediately, linked to the doc.
//   - New invoice (no docname yet): store as data URL; saveInvoice() will upload
//     once the doc is created and patch logo_attach on it.
const logoUploading = ref(false);
async function onLogoUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  // Always show an instant preview via data URL
  const reader = new FileReader();
  reader.onload = ev => { form.logo = ev.target.result; };
  reader.readAsDataURL(file);

  // Only upload immediately when editing an existing invoice (docname known)
  if (!editingName.value) return; // saveInvoice() will handle it on save

  logoUploading.value = true;
  try {
    const fd = new FormData();
    fd.append("file", file, file.name);
    fd.append("is_private", "0");
    fd.append("folder", "Home/Attachments");
    fd.append("doctype", "Sales Invoice");
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
      // Also patch the field on the existing doc right away so it survives a
      // page reload even if the user doesn't click Save again.
      await apiPOST("frappe.client.set_value", {
        doctype: "Sales Invoice",
        name: editingName.value,
        fieldname: "logo",
        value: fileUrl,
      });
    }
  } catch(err) {
    console.warn("Logo upload failed:", err);
    // Keep data URL so the preview still works; will retry on next save
  }
  logoUploading.value = false;
}

function removeLogo() {
  form.logo = "";
  const inp = document.getElementById("inv-logo-file-input");
  if (inp) inp.value = "";
}


async function printInvoice(data) {
  try { await refreshBranding(); } catch {}
  printDoc(_toPrintDoc(data), _invCfg(data));
}

function printViewInvoice() {
  const inv=viewInv.value;
  if (!inv) return;
  printInvoice({
    name:inv.name, customer:inv.customer, customer_name:inv.customer_name,
    customer_company_name: customers.value.find(c=>c.name===inv.customer)?.company_name||"",
    posting_date:inv.posting_date, due_date:inv.due_date, po_no:inv.po_no,
    place_of_supply:inv.place_of_supply,
    billing_address:inv.billing_address||"", billing_address_name:inv.billing_address_name||"",
    shipping_address:inv.shipping_address||"", shipping_address_name:inv.shipping_address_name||"",
    customer_gstin:inv.customer_gstin||"", customer_mobile:inv.customer_mobile||"",
    items:withItemTaxRates(inv.items||[], inv.place_of_supply), taxes:inv.taxes||[],
    subtotal:(inv.net_total != null ? flt(inv.net_total) : flt(inv.grand_total)-flt(inv.total_tax)),
    totalTax:flt(inv.total_tax), grandTotal:flt(inv.grand_total),
    terms:inv.terms||"", company:inv.company||window.__booksCompany||"",
    logo:logoSrc(inv.logo||""),
  });
}

onMounted(async () => {
  console.log("[BooksCompany][Invoices.vue] onMounted() start, window.__booksCompany =", window.__booksCompany);
  await load();
  loadCustomers(); loadSalesPersons(); loadItems(); loadTaxAccount(); loadBranding(); loadPriceLists();
  apiList("UOM", { fields: ["name"], order: "name asc", limit: 200 })
    .then(r => { if (r && r.length) uomList.value = r.map(u => u.name); })
    .catch(() => {});
  try { setCompany(window.__booksCompany || await resolveCompany()); } catch {}

  // Cross-document deep link: /invoices?open=INV-...
  useOpenFromQuery({
    route,
    openByName: (n) => {
      const row = list.value.find(r => r.name === n) || { name: n };
      openView(row);
    },
  });

  // Apply AI-driven URL params (set by AppShell AI handlers via router.push)
  const q = route.query;
  if (q.ai_filter) {
    activeFilter.value = q.ai_filter;          // "Overdue" | "Unpaid" | "Draft" | "Paid"
  }
  if (q.ai_search) {
    search.value = decodeURIComponent(q.ai_search);
    activeFilter.value = "all";
  }
  if (q.ai_create) {
    openAdd();
    nextTick(() => {
      if (q.ai_customer) form.customer = decodeURIComponent(q.ai_customer);
      if (q.ai_item) {
        lines.value = [{
          id: Date.now(), item_code: "",
          item_name:  decodeURIComponent(q.ai_item),
          description: "", hsn_code: "",
          qty:    Number(q.ai_qty)    || 1,
          rate:   Number(q.ai_rate)   || 0,
          uom:    "Nos",
          discount_percentage: 0, discount_amount: 0,
          amount: Number(q.ai_amount) || 0,
        }];
      }
    });
  }
});

// Re-apply AI params when query changes (user is already on page when AI fires)
watch(() => route.query, (q) => {
  if (!q) return;
  if (q.ai_filter) activeFilter.value = q.ai_filter;
  if (q.ai_search) { search.value = decodeURIComponent(q.ai_search); activeFilter.value = "all"; }
  if (q.ai_create) {
    openAdd();
    nextTick(() => {
      if (q.ai_customer) form.customer = decodeURIComponent(q.ai_customer);
      if (q.ai_item) {
        lines.value = [{
          id: Date.now(), item_code: "",
          item_name:  decodeURIComponent(q.ai_item),
          description: "", hsn_code: "",
          qty:    Number(q.ai_qty)    || 1,
          rate:   Number(q.ai_rate)   || 0,
          uom:    "Nos",
          discount_percentage: 0, discount_amount: 0,
          amount: Number(q.ai_amount) || 0,
        }];
      }
    });
  }
});
</script>

<style>
@import '../styles/list.css';
@import '../styles/view.css';
@import '../styles/edit.css';
@import '../styles/add.css';

/* ─── Invoice-specific overrides ─── */
.inv-page { display:flex; flex-direction:column; gap:16px; padding:24px; min-height:100%; color:#1a1a2e; background:#f5f6f8; }

/* Legacy toolbar */
.inv-toolbar { display:flex; align-items:center; justify-content:space-between; padding:16px 24px 12px; border-bottom:1px solid #e8ecf0; gap:12px; flex-wrap:wrap; }
.inv-heading { font-size:16px; font-weight:700; color:#1a1a2e; margin:0; }
.inv-toolbar-right { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
.inv-search-wrap { display:flex; align-items:center; gap:7px; border:1px solid #ffffff; border-radius:20px; padding:6px 12px; background:#f9fafb; }
.inv-search-input { border:none; outline:none; background:transparent; font-size:13px; width:200px; color:#374151; }
.inv-btn-primary { display:inline-flex; align-items:center; gap:6px; background:#1a6ef7; color:#fff; border:none; border-radius:6px; padding:7px 16px; font-size:13px; font-weight:600; cursor:pointer; }
.inv-btn-primary:hover { background:#155fd4; } .inv-btn-primary:disabled { opacity:.55; cursor:not-allowed; }
.inv-btn-ghost { display:inline-flex; align-items:center; gap:6px; background:#fff; color:#374151; border:1px solid #e8ecf0; border-radius:6px; padding:7px 12px; font-size:13px; font-weight:500; cursor:pointer; }
.inv-btn-ghost:hover { border-color:#374151; }

/* ── Summary strip ── */
.inv-sum-strip { display:grid; grid-template-columns:repeat(4,1fr); border-bottom:1px solid #e8ecf0; }
.inv-sum-card { padding:14px 24px; border-right:1px solid #e8ecf0; }
.inv-sum-card:last-child { border-right:none; }
.inv-sum-lbl { font-size:10.5px; font-weight:600; text-transform:uppercase; letter-spacing:.05em; color:#9ca3af; margin-bottom:4px; }
.inv-sum-val { font-size:20px; font-weight:700; color:#1a1a2e; }

/* ── Filter bar ── */
.inv-filter-bar { display:flex; align-items:center; justify-content:space-between; padding:10px 24px; border-bottom:1px solid #e8ecf0; flex-wrap:wrap; gap:8px; }
.inv-pills { display:flex; gap:6px; flex-wrap:wrap; }
.inv-pill { display:inline-flex; align-items:center; gap:6px; padding:5px 12px; border-radius:20px; font-size:12.5px; font-weight:600; border:1.5px solid #e8ecf0; background:#fff; color:#6b7280; cursor:pointer; }
.inv-pill:hover { border-color:#1a6ef7; color:#1a6ef7; }
.inv-pill.active { background:#eaf1ff; border-color:#1a6ef7; color:#1a6ef7; }
.inv-pill-count { font-size:10.5px; font-weight:700; padding:1px 6px; border-radius:12px; }
.pc-muted { background:#e5e7eb; color:#6b7280; } .pc-amber { background:#fef3c7; color:#d97706; }
.pc-red   { background:#fee2e2; color:#dc2626; } .pc-green { background:#d1fae5; color:#059669; }
.inv-filter-right { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
.inv-date-btns { display:flex; gap:4px; }
.inv-date-btn { border:1px solid #e8ecf0; background:#fff; color:#6b7280; border-radius:6px; padding:4px 10px; font-size:12px; font-weight:600; cursor:pointer; }
.inv-date-btn:hover { border-color:#1a6ef7; color:#1a6ef7; }
.inv-date-btn.active { background:#eaf1ff; border-color:#1a6ef7; color:#1a6ef7; }
.inv-date-input { border:1px solid #e8ecf0; border-radius:6px; padding:4px 8px; font-size:12px; outline:none; }
.inv-filter-select { border:1px solid #e8ecf0; border-radius:6px; padding:5px 8px; font-size:12.5px; outline:none; background:#fff; cursor:pointer; color:#374151; }

/* ── Bulk bar ── */
.inv-bulk-bar { display:flex; align-items:center; gap:10px; padding:10px 16px; background:#eff6ff; border:1px solid #bfdbfe; border-radius:10px; flex-wrap:wrap; }
.inv-bulk-count { font-size:13px; font-weight:700; color:#1d4ed8; }
.inv-bulk-btn { display:inline-flex; align-items:center; gap:5px; border:1px solid #bfdbfe; background:#fff; color:#374151; border-radius:6px; padding:5px 12px; font-size:12.5px; font-weight:600; cursor:pointer; }
.inv-bulk-btn:hover { border-color:#374151; }
.inv-bulk-danger { border-color:rgba(220,38,38,.3); color:#dc2626; }
.inv-bulk-danger:hover { background:#fee2e2; }
.inv-bulk-pay { border-color:rgba(26,110,247,.3); color:#1a6ef7; }
.inv-bulk-pay:hover { background:#eaf1ff; }
.inv-bulk-clear { background:none; border:none; color:#6b7280; font-size:12px; cursor:pointer; margin-left:auto; }
.inv-bulk-clear:hover { color:#374151; }

/* ── Table ── */
.inv-table-wrap { background:#fff; border:1px solid #e5e7eb; border-radius:10px; overflow:hidden; overflow-x:auto; }
.inv-table { width:100%; border-collapse:collapse; font-size:13px; }
.inv-table th { padding:10px 14px; border-bottom:2px solid #e8ecf0; font-size:11px; font-weight:600; letter-spacing:normal; color:#6b7280; text-align:left; white-space:nowrap; background:#f9f9fb; user-select:none; }
.inv-table th.sortable { cursor:pointer; } .inv-table th.sortable:hover { color:#1a6ef7; }
.sort-arrow { font-size:10px; margin-left:2px; color:#1a6ef7; }
.th-check { width:40px; padding-left:20px; }
.inv-table td { padding:11px 14px; border-bottom:1px solid #f0f2f5; color:#374151; vertical-align:middle; cursor:pointer; }
.td-check { cursor:default; padding-left:20px; }
.inv-row:hover td { background:#f8faff; } .inv-row.selected td { background:#eaf1ff; }
.inv-table tr:last-child td { border-bottom:none; }
.inv-link { color:#1a6ef7; font-weight:600; } .inv-customer { font-weight:600; color:#1a1a2e; }
.mono-sm { font-size:12.5px; } .ta-r { text-align:right; }
.text-danger { color:#dc2626; } .text-success { color:#059669; } .text-muted { color:#9ca3af; }

/* ── Status badges ── */
.inv-status-badge { display:inline-flex; align-items:center; padding:3px 10px; border-radius:4px; font-size:10.5px; font-weight:700; letter-spacing:.04em; white-space:nowrap; }
.status-overdue  { color:#dc2626; background:transparent; } .status-paid { color:#059669; background:#d1fae5; }
.status-unpaid   { color:#d97706; background:#fef3c7; }    .status-draft { color:#6b7280; background:#f3f4f6; }
.status-cancelled{ color:#dc2626; background:#fee2e2; }

/* ── Action buttons ── */
.inv-act-btn { background:none; border:1px solid #e8ecf0; border-radius:5px; padding:4px 6px; cursor:pointer; color:#6b7280; display:inline-flex; align-items:center; }
.inv-act-btn:hover { border-color:#374151; color:#374151; }
.inv-act-pay { border-color:rgba(26,110,247,.3); color:#1a6ef7; font-weight:700; font-size:11px; }
.inv-act-pay:hover { background:#eaf1ff; }

/* ── Shimmer ── */
.shimmer { height:12px; border-radius:4px; background:linear-gradient(90deg,#f0f2f5 25%,#e4e7ec 50%,#f0f2f5 75%); background-size:200% 100%; animation:shimmer 1.4s infinite; }
@keyframes shimmer { 0%{background-position:200% 0}100%{background-position:-200% 0} }

/* ── Empty state ── */
.empty-state { padding:48px 0 !important; text-align:center; cursor:default !important; }
.empty-inner { display:flex; flex-direction:column; align-items:center; gap:10px; color:#9ca3af; font-size:13px; }

/* ── Drawer ── */
.inv-drawer-bg { position:fixed; inset:0; z-index:8000; background:rgba(15,23,42,.45); display:flex; justify-content:flex-end; backdrop-filter:blur(2px); }
.inv-drawer-panel { width:720px; max-width:96vw; height:100%; background:#fff; display:flex; flex-direction:column; box-shadow:-20px 0 60px rgba(0,0,0,.15); overflow:hidden; }
.inv-drawer-wide { width:800px; }
.inv-dh { display:flex; align-items:center; justify-content:space-between; padding:18px 24px; background:linear-gradient(135deg,#1e3a5f,#1a6ef7); flex-shrink:0; }
.inv-dh-title { color:#fff; font-size:16px; font-weight:700; }
.inv-dh-sub   { color:rgba(255,255,255,.75); font-size:12px; margin-top:2px; }
.inv-dclose { background:rgba(255,255,255,.15); border:none; cursor:pointer; width:30px; height:30px; border-radius:8px; color:#fff; display:grid; place-items:center; }
.inv-dbody { flex:1; overflow-y:auto; padding:20px 24px; }
.inv-dfooter { padding:14px 24px; border-top:1px solid #e8ecf0; display:flex; justify-content:space-between; align-items:center; background:#f8fafc; flex-shrink:0; }

/* ── Status timeline ── */
.inv-view-item-row { display:grid; grid-template-columns:2fr .7fr .7fr 1fr .7fr 1fr; gap:8px; padding:9px 14px; border-bottom:1px solid #f0f2f5; font-size:13px; }
.inv-view-item-row:last-child { border-bottom:none; }

/* ── Form helpers ── */
.inv-req { color:#dc2626; }
.inv-sec-lbl { font-size:10.5px; font-weight:700; letter-spacing:.6px; text-transform:uppercase; color:#9ca3af; margin-bottom:12px; margin-top:4px; padding-top:16px; border-top:1px solid #f0f2f5; }
.inv-sec-lbl:first-child { border-top:none; padding-top:0; margin-top:0; }
.inv-pay-section-lbl { font-size:10.5px; font-weight:700; letter-spacing:.6px; text-transform:uppercase; color:#6b7280; margin-bottom:6px; }
.inv-pay-section-lbl-cn { color:#7c3aed; }
.inv-cn-badge { font-size:11px; font-weight:600; padding:2px 8px; border-radius:4px; }
.inv-cn-badge-direct  { background:#ede9fe; color:#6d28d9; }
.inv-cn-badge-applied { background:#d1fae5; color:#065f46; }
.inv-fg { display:grid; gap:12px; margin-bottom:14px; }
.inv-fg2 { grid-template-columns:1fr 1fr; } .inv-fg3 { grid-template-columns:1fr 1fr 1fr; }
.inv-lbl { display:block; font-size:11.5px; font-weight:600; color:#495057; margin-bottom:5px; }
.inv-fi { width:100%; border:1px solid #e2e8f0; border-radius:6px; padding:7px 10px; font-size:13px; font-family:inherit; outline:none; box-sizing:border-box; }
.inv-details-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 14px 16px; margin-top: 14px; }
@media (max-width: 700px) { .inv-details-2col { grid-template-columns: 1fr; } }

/* ── Invoice Details: lower section (fields left, inventory card right) ── */
.inv-details-lower { display: flex; align-items: stretch; gap: 16px; margin-top: 14px; }
.inv-details-lower-main { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; }
.inv-details-row2-4col { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px 16px; }
.inv-details-toggle-col { width: 280px; flex-shrink: 0; display: flex; }
.inv-details-toggle-col .inv-inv-block { width: 100%; }
@media (max-width: 900px) {
  .inv-details-lower { flex-direction: column; }
  .inv-details-toggle-col { width: 100%; }
}
@media (max-width: 700px) { .inv-details-row2-4col { grid-template-columns: 1fr 1fr; } }
@media (max-width: 480px) { .inv-details-row2-4col { grid-template-columns: 1fr; } }
.inv-inv-block { border-radius:10px; padding:14px 16px; display:flex; flex-direction:column; gap:12px; transition:background .2s,border-color .2s; }
.inv-inv-block.inv-on  { background:#eff6ff; border:1.5px solid #93c5fd; }
.inv-inv-block.inv-off { background:#f9fafb; border:1.5px solid #e5e7eb; }
.inv-inv-toggle-row { display:flex; align-items:center; gap:12px; }
.inv-inv-icon { width:32px; height:32px; border-radius:8px; background:#dbeafe; color:#2563eb; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.inv-inv-block.inv-off .inv-inv-icon { background:#f3f4f6; color:#9ca3af; }
.inv-inv-text { flex:1; }
.inv-inv-title { font-size:13px; font-weight:700; color:#111827; }
.inv-inv-sub { font-size:11.5px; color:#6b7280; margin-top:2px; line-height:1.4; }
.inv-inv-wh-row { display:flex; flex-direction:column; padding-top:4px; border-top:1px solid #bfdbfe; }
.inv-inv-switch { position:relative; display:inline-block; width:42px; height:24px; flex-shrink:0; }
.inv-inv-switch input { opacity:0; width:0; height:0; }
.inv-inv-slider { position:absolute; cursor:pointer; inset:0; background:#d1d5db; border-radius:24px; transition:.2s; }
.inv-inv-slider:before { content:""; position:absolute; height:18px; width:18px; left:3px; bottom:3px; background:#fff; border-radius:50%; transition:.2s; }
.inv-inv-switch input:checked + .inv-inv-slider { background:#2563eb; }
.inv-inv-switch input:checked + .inv-inv-slider:before { transform:translateX(18px); }
.inv-fi:focus { border-color:#1a6ef7; box-shadow:0 0 0 3px rgba(26,110,247,.08); }
.inv-fi[type="number"]::-webkit-outer-spin-button,
.inv-fi[type="number"]::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.inv-fi[type="number"] { -moz-appearance: textfield; appearance: textfield; }

/* ── Line items table (row) layout ── */
.po-items-table-wrap { border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden; }
.po-items-table { width: 100%; table-layout: fixed; border-collapse: collapse; }
.po-items-table thead th {
  background: #f8fafc; border-bottom: 1px solid #e5e7eb;
  font-size: 10px; font-weight: 700; color: #6b7280; text-transform: uppercase;
  letter-spacing: .02em; text-align: left; padding: 8px 4px; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis;
}
.po-items-table .th-num { width: 4%; }
.po-items-table .th-item { width: 16%; }
.po-items-table .th-hsn { width: 10%; }
.po-items-table .th-uom { width: 6%; }
.po-items-table .th-qty { width: 5%; }
.po-items-table .th-rate { width: 9%; }
.po-items-table .th-mrp { width: 6%; }
.po-items-table .th-disc { width: 6%; }
.po-items-table .th-tax { width: 9%; }
.po-items-table .th-batch { width: 7%; }
.po-items-table .th-expiry { width: 8%; }
.po-items-table .th-availqty { width: 0; }
.po-items-table .th-subtotal { width: 10%; text-align: right; }
.po-items-table .th-rm { width: 4%; }
.po-items-row { border-bottom: 1px solid #f0f2f8; }
.po-items-row:hover { background: #fafbfe; }
.po-items-row td { padding: 8px 3px; vertical-align: middle; overflow: hidden; }
.po-items-row .td-num { text-align: center; }
.po-row-num { font-size: 11px; font-weight: 800; color: #4f46e5; background: #e0e7ff; border-radius: 5px; padding: 3px 8px; letter-spacing: .02em; white-space: nowrap; }
.po-row-desc-ta { resize: vertical; min-height: 46px; font-size: 12.5px; line-height: 1.4; margin-top: 8px; width: 100%; box-sizing: border-box; }
.po-items-row .td-subtotal { text-align: right; white-space: normal; word-break: break-word; }
.po-row-subtotal-label { display: block; font-size: 9.5px; font-weight: 700; color: #9ca3af; letter-spacing: .08em; }
.po-row-subtotal-amt { display: block; font-size: 15px; font-weight: 800; color: #111827; font-variant-numeric: tabular-nums; line-height: 1.2; }
.po-row-subtotal-tax { display: block; font-size: 10px; color: #6b7280; margin-top: 2px; word-break: break-word; }
.po-row-subtotal-total { display: block; font-size: 10.5px; font-weight: 700; color: #1a1d23; margin-top: 2px; white-space: nowrap; }
.po-items-row .td-rm { text-align: center; }
/* ── Common control height for every field in the row ── */
.po-items-row .inv-fi,
.po-items-row select.inv-fi { height: 36px; box-sizing: border-box; }
.po-items-row .ss-wrap,
.po-items-row .ss-trigger {
  height: 36px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
}
.po-items-row .td-hsn .inv-fi,
.po-items-row .td-qty .inv-fi,
.po-items-row .td-rate .inv-fi,
.po-items-row .td-mrp .inv-fi,
.po-items-row .td-disc .inv-fi,
.po-items-row .td-tax .inv-fi { width: 100%; box-sizing: border-box; padding: 0 6px; font-size: 11.5px; }
.po-items-row .td-uom .inv-fi { width: 100%; box-sizing: border-box; padding: 0 16px 0 6px; font-size: 11.5px; }
.po-items-row .td-item, .po-items-row .td-hsn, .po-items-row .td-uom,
.po-items-row .td-mrp, .po-items-row .td-qty, .po-items-row .td-rate,
.po-items-row .td-disc, .po-items-row .td-batch { vertical-align: middle; }
.po-items-row .td-batch, .po-items-row .td-expiry, .po-items-row .td-availqty { white-space: normal; }
.po-items-row .td-expiry span, .po-items-row .td-availqty span { display: flex; align-items: center; height: 36px; }
.po-items-tax-row td { padding: 0 10px 10px; border-bottom: 1px solid #f0f2f8; }
.po-items-error-row, .po-items-warn-row { border-bottom: 1px solid #f0f2f8; }
.po-items-error-row td, .po-items-warn-row td { padding: 0; }
.po-items-banner-inner {
  padding: 6px 12px 10px 44px; font-size: 11.5px; font-weight: 600;
  display: flex; align-items: center; gap: 5px; white-space: normal;
}
.po-items-error-row .po-items-banner-inner { color: #dc2626; }
.po-items-warn-row .po-items-banner-inner { color: #9ca3af; font-weight: 500; }
.inv-add-line-btn { display:inline-flex; align-items:center; gap:5px; border:1px solid rgba(26,110,247,.3); background:#eaf1ff; color:#1a6ef7; border-radius:6px; padding:5px 12px; font-size:12.5px; font-weight:600; cursor:pointer; }
.inv-copy-btn { background:#f0fdf4; border-color:rgba(5,150,105,.3); color:#059669; }

/* ── Line items table ── */
.inv-lines-tbl { width:100%; border-collapse:collapse; font-size:13px; }
.inv-lines-tbl th { padding:7px 8px; background:#f8fafc; border-bottom:1px solid #e8ecf0; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:#9ca3af; text-align:left; }
.inv-lines-tbl td { padding:4px 6px; border-bottom:1px solid #f0f2f5; }
.inv-ci { width:100%; border:1px solid #e2e8f0; border-radius:5px; padding:5px 7px; font-size:12.5px; font-family:inherit; outline:none; }
.inv-ci:focus { border-color:#1a6ef7; }
.inv-ci-r { text-align:right; }
.inv-rm-line { background:#fff0f0; border:1px solid #fecaca; border-radius:6px; width:30px; height:30px; cursor:pointer; color:#dc2626; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0; padding:0; }
.inv-rm-line:hover { background:#fee2e2; border-color:#dc2626; }

/* ── Tax section ── */
.inv-totals-wrap { border-top:1px solid #e8ecf0; padding:14px 16px; background:#f5f7fa; display:flex; flex-direction:column; gap:0; }
.inv-tax-section { width:100%; }
.inv-tax-header { display:flex; align-items:flex-start; flex-direction:column; gap:8px; margin-bottom:12px; }
.inv-tax-title { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; color:#9ca3af; margin-bottom:2px; }
.inv-tax-presets { display:flex; gap:6px; flex-wrap:wrap; width:100%; }
.inv-preset-btn { border:1px solid #d1d5db; background:#fff; color:#374151; border-radius:20px; padding:5px 12px; font-size:12px; font-weight:600; cursor:pointer; white-space:nowrap; transition:border-color .15s,color .15s,background .15s; line-height:1.3; }
.inv-preset-btn:hover { border-color:#1a6ef7; color:#1a6ef7; background:#eef4ff; }
.inv-preset-btn.active { background:#1a6ef7; border-color:#1a6ef7; color:#fff; }
.inv-preset-custom { border-color:#1a6ef7; color:#1a6ef7; background:#fff; }
.inv-preset-custom:hover { background:#eef4ff; }
.inv-preset-clear { border-color:#dc2626; color:#dc2626; background:#fff; }
.inv-preset-clear:hover { background:#fef2f2; }
/* Tax row cards */
.inv-tax-tbl { width:100%; border-collapse:separate; border-spacing:0 8px; font-size:13px; }
.inv-tax-tbl thead { display:none; }
.inv-tax-tbl tbody tr { background:#fff; border:1px solid #e3e8ef; border-radius:10px; box-shadow:0 1px 3px rgba(0,0,0,.06); display:block; padding:12px 14px; margin-bottom:8px; }
.inv-tax-tbl tbody tr td:nth-child(1) { display:flex; align-items:center; gap:8px; padding:0 0 8px 0; border:none; }
.inv-tax-tbl tbody tr td:nth-child(1) .inv-ci { flex:1; min-width:0; }
.inv-tax-tbl tbody tr td:nth-child(2) { display:block; padding:0 0 8px 0; border:none; }
.inv-tax-tbl tbody tr td:nth-child(2) .inv-ci { text-align:right; width:100%; }
.inv-tax-tbl tbody tr td:nth-child(3) { display:flex; justify-content:space-between; align-items:center; padding:6px 0 0 0; border-top:1px solid #f0f2f5; border-left:none; border-right:none; border-bottom:none; }
.inv-tax-tbl tbody tr td:nth-child(3)::before { content:'AMOUNT'; font-size:9.5px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; color:#9ca3af; }
.inv-tax-amt-val { font-size:14px; font-weight:700; color:#1a1a2e; text-align:right; }

/* ── Totals ── */
.inv-totals { width:100%; display:flex; flex-direction:column; gap:5px; align-items:stretch; margin-top:14px; padding-top:14px; border-top:1px solid #e3e8ef; }
.inv-total-row { display:flex; justify-content:space-between; align-items:center; width:100%; font-size:13px; color:#374151; padding:3px 0; }
.inv-total-amt { font-weight:600; font-size:13px; text-align:right; }
.inv-grand-total { border-top:1px solid #e8ecf0; padding-top:10px; margin-top:5px; font-weight:700; font-size:14px; }

/* ══ Record Payment ══ */

/* ── Template / branding bar ── */
.inv-tmpl-bar { display:flex; align-items:flex-start; gap:24px; padding:9px 22px; border-bottom:1px solid #e8ecf0; background:#f8fafc; flex-shrink:0; flex-wrap:wrap; }
.inv-tmpl-group { display:flex; flex-direction:column; gap:4px; }
.inv-tmpl-lbl { font-size:9.5px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:#9ca3af; }
.inv-tmpl-btns { display:flex; gap:4px; }
.inv-tmpl-btn { border:1px solid #e8ecf0; background:#fff; color:#374151; border-radius:5px; padding:4px 11px; font-size:12px; font-weight:600; cursor:pointer; }
.inv-tmpl-btn:hover { border-color:#1a6ef7; color:#1a6ef7; }
.inv-tmpl-btn.active { background:#eaf1ff; border-color:#1a6ef7; color:#1a6ef7; }
.inv-color-pick { width:34px; height:26px; border:1px solid #e8ecf0; border-radius:5px; cursor:pointer; padding:2px 3px; }
.inv-color-val { font-size:12px; color:#374151; }
.inv-logo-input { border:1px solid #e2e8f0; border-radius:5px; padding:4px 8px; font-size:12px; outline:none; width:100%; max-width:300px; }
.inv-logo-input:focus { border-color:#1a6ef7; }
.inv-preview-toggle { display:inline-flex; align-items:center; gap:5px; background:rgba(255,255,255,.15); border:1px solid rgba(255,255,255,.3); color:#fff; border-radius:6px; padding:5px 11px; font-size:12px; font-weight:600; cursor:pointer; }
.inv-preview-toggle:hover { background:rgba(255,255,255,.25); }

/* ── 3-panel / preview layout ── */
.inv-split { width:min(1400px,98vw) !important; }
.inv-content-row { flex:1; display:flex; overflow:hidden; min-height:0; }
.inv-content-row .inv-dbody { flex:1; overflow-y:auto; min-width:0; }
.inv-preview-pane { width:480px; flex-shrink:0; border-left:1px solid #e8ecf0; display:flex; flex-direction:column; background:#e8ecf0; overflow:hidden; }
.inv-preview-toolbar { display:flex; align-items:center; justify-content:space-between; padding:8px 12px; background:#fff; border-bottom:1px solid #e8ecf0; flex-shrink:0; }
.inv-preview-iframe { flex:1; border:none; width:100%; min-height:0; background:#fff; }
/* ── Invoice view drawer overrides ── */
.inv-view-page { display:flex; flex-direction:column; overflow-y:auto; background:#f5f6f8; }
.inv-view-page .inv-view-header { padding:16px 20px 10px; flex-shrink:0; }
.inv-view-page .inv-view-body { margin:0 16px 16px; }
.inv-view-page .inv-bottom-grid { padding:0 0 4px; }
.inv-view-page .inv-tab-body { padding:16px; }

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

/* ── Mobile invoice cards (Option A) ── */
.inv-mobile-cards { display: none; }
.inv-desktop-table { display: table; }

@media (max-width: 768px) {
  .inv-page { padding: 12px 10px 20px !important; gap: 14px !important; }

  /* Switch KPI grid → compact summary strip */
  .inv-page > .bk-kpi-grid { display: none !important; }
  .inv-page > .inv-mobile-summary { display: grid !important; grid-template-columns: 1fr 1fr !important; gap: 10px !important; }
  .inv-mobile-summary .inv-stat-count { display: none !important; }

  /* Switch table ↔ cards */
  .inv-desktop-table { display: none !important; }
  .inv-mobile-cards { display: flex; flex-direction: column; gap: 0; background: #f8fafc; }
  .inv-mobile-card { background: #fff; border-bottom: 1px solid #e5e7eb; padding: 12px 14px; cursor: pointer; transition: background .12s; }
  .inv-mobile-card:active { background: #f8f9fc; }
  .inv-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .inv-mc-docno { font-size: 12px; font-weight: 700; color: #2563eb; }
  .inv-mc-mid { font-size: 13.5px; font-weight: 600; color: #1a1d23; margin-bottom: 4px; }
  .inv-mc-meta { display: flex; justify-content: space-between; font-size: 12px; color: #868e96; margin-bottom: 4px; }
  .inv-mc-amount { font-weight: 700; color: #1a1d23; }
  .inv-mc-balance { font-size: 11.5px; color: #868e96; margin-bottom: 8px; }
  .inv-mc-footer { display: flex; gap: 6px; margin-top: 8px; }
  .inv-mc-btn { flex: 1; padding: 6px 10px; border-radius: 7px; font-size: 12px; font-weight: 600; cursor: pointer; background: #f1f5f9; border: 1px solid #e2e8f0; color: #374151; }
  .inv-mc-pay { background: #eff6ff; border-color: #bfdbfe; color: #2563eb; }
  .inv-mc-danger { background: #fff1f2; border-color: #fecaca; color: #dc2626; }
  .inv-mc--skeleton { pointer-events: none; }
  .inv-mc-shimmer { border-radius: 6px; background: linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size: 200% 100%; animation: mc-shimmer 1.4s infinite; }
  @keyframes mc-shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
  .inv-mc-empty { text-align: center; padding: 32px 16px; color: #868e96; font-size: 13px; }

  .sales-toolbar { flex-wrap: wrap; }
  .sales-actions { flex-wrap: wrap; }
  .sales-pills { flex-wrap: wrap; }
}

@media (max-width: 480px) {
  .inv-page > .inv-mobile-summary { grid-template-columns: 1fr !important; }
  .inv-view-cta .ab-label{display:none;}
}

/* ── Invoice Add/Edit drawer on mobile: the sidebar becomes an overlay
   (no layout width of its own) below 768px, so the "sit beside the
   sidebar" offset below must not apply here — otherwise the drawer gets
   squeezed into a narrow sliver and its content overlaps/cuts off. ── */


/* ── e-Invoice status dot (list row) ── */
.ei-status-dot { display:inline-block; width:7px; height:7px; border-radius:50%; margin-left:6px; vertical-align:middle; flex-shrink:0; }
.ei-dot-green  { background:#16a34a; }
.ei-dot-orange { background:#f59e0b; }
.ei-dot-grey   { background:#9ca3af; }

/* ── e-Invoice tab styles ── */
.ei-inline-badge { display:inline-flex; align-items:center; padding:3px 10px; border-radius:10px; font-size:12px; font-weight:600; }
.badge-green  { background:#dcfce7; color:#16a34a; }
.badge-orange { background:#fff7ed; color:#ea580c; }
.badge-grey   { background:#f3f4f6; color:#6b7280; }
.ei-action-btn { display:inline-flex; align-items:center; gap:5px; border-radius:8px; padding:8px 14px; font-size:13px; font-weight:600; cursor:pointer; border:none; }
.ei-action-btn.primary  { background:#2563eb; color:#fff; }
.ei-action-btn.primary:hover  { background:#1d4ed8; }
.ei-action-btn.primary:disabled { opacity:.6; cursor:not-allowed; }
.ei-action-btn.outline  { background:#fff; border:1.5px solid #2563eb; color:#2563eb; }
.ei-action-btn.outline:hover  { background:#eff6ff; }
.ei-action-btn.danger   { background:#fff; border:1.5px solid #dc2626; color:#dc2626; }
.ei-action-btn.danger:hover   { background:#fef2f2; }
.ei-action-btn.danger:disabled { opacity:.6; cursor:not-allowed; }
.ei-input { width:100%; border:1px solid #e5e7eb; border-radius:7px; padding:8px 10px; font:inherit; font-size:13px; outline:none; color:#111827; background:#fff; box-sizing:border-box; }
.ei-input:focus { border-color:#2563eb; box-shadow:0 0 0 3px rgba(37,99,235,.08); }
@keyframes spin { to { transform:rotate(360deg); } }

/* ── Readonly branding card in invoice drawer ── */
.inv-brand-readonly { display: flex; flex-direction: column; gap: 12px; }
.inv-brand-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.inv-brand-lbl { font-size: 11px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: .5px; min-width: 90px; flex-shrink: 0; }
.inv-brand-tmpl-btns { display: flex; gap: 6px; flex-wrap: wrap; }
.inv-brand-tmpl-chip {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 500;
  background: #f3f4f6; color: #6b7280; border: 1.5px solid #e5e7eb;
  user-select: none;
}
.inv-brand-tmpl-chip.active {
  background: #eff6ff; color: #2563eb; border-color: #93c5fd;
}
.inv-brand-color-preview { display: flex; align-items: center; gap: 8px; }
.inv-brand-color-swatch { width: 20px; height: 20px; border-radius: 4px; border: 1px solid rgba(0,0,0,.1); flex-shrink: 0; }
.inv-brand-color-hex { font-size: 12px; font-weight: 600; color: #374151; }
.inv-brand-logo-preview { display: flex; align-items: center; }
.inv-brand-logo-thumb { height: 36px; max-width: 120px; object-fit: contain; border: 1px solid #e5e7eb; border-radius: 4px; padding: 2px; background: #fff; }
.inv-brand-logo-none { font-size: 12px; color: #9ca3af; font-style: italic; }
.inv-brand-settings-hint { font-size: 11.5px; color: #9ca3af; display: flex; align-items: center; gap: 5px; margin-top: 4px; }
.inv-brand-settings-link { color: #2563eb; text-decoration: none; font-weight: 500; }
.inv-brand-settings-link:hover { text-decoration: underline; }
.inv-new-drawer{width:1020px !important;right:-1020px!important;}

/* ── Invoice Add/Edit drawer: sit beside the sidebar, not over it ── */
.inv-addedit-bg { left: var(--bv-sidebar-w, 220px) !important; }
.bv-app-sidebar-collapsed .inv-addedit-bg { left: var(--bv-sidebar-w-narrow, 56px) !important; }
.inv-addedit-bg .inv-addedit-panel { width: 100% !important; max-width: 100% !important; }

/* Mobile override — placed last so it wins the cascade tie-break against
   the unconditional desktop rules above (same specificity, later wins). */
@media (max-width: 768px) {
  .inv-addedit-bg,
  .bv-app-sidebar-collapsed .inv-addedit-bg { left: 0 !important; }
  .inv-new-drawer, .inv-drawer-wide { width: 100vw !important; max-width: 100vw !important; right: 0 !important; }
  .inv-split { width: 100vw !important; }
  .inv-content-row { flex-direction: column; }

  /* Line-item table -> stacked cards. Each cell gets its label from the
     data-label attribute on the <td> itself (set in the template), so a
     label can never end up paired with the wrong field regardless of
     column order or hidden/conditional columns. */
  .po-items-table { table-layout: auto; }
  .po-items-table thead { display: none; }
  .po-items-table, .po-items-table tbody, .po-items-table tr, .po-items-table td { display: block; width: auto; }
  .po-items-row {
    border: 1px solid #e5e7eb; border-radius: 12px; margin-bottom: 12px;
    padding: 12px 14px 4px; background: #fff; position: relative;
  }
  .po-items-row .td-num { position: absolute; top: 12px; left: 14px; padding: 0; }
  .po-items-row .td-rm { position: absolute; top: 8px; right: 8px; padding: 0; }
  .po-items-row .td-item { padding: 0 44px 10px 0; margin-top: 2px; }
  .po-items-row td[data-label] {
    padding: 8px 0; border-top: 1px solid #f0f2f8;
  }
  .po-items-row td[data-label]::before {
    content: attr(data-label);
    display: block; font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .04em; color: #9ca3af; margin-bottom: 4px;
  }
  .po-items-row .td-subtotal { text-align: left; border-top: 1px solid #e5e7eb; margin-top: 4px; }
}
</style>