<template>
  <div class="list-page">

    <!-- ── Toolbar ── -->
    <div class="sales-toolbar">
      <div class="sales-search">
        <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
        <input v-model="search" placeholder="Search bills, vendors, bill #…" class="sales-search-input" />
      </div>
      <div class="sales-pills">
        <button v-for="t in tabs" :key="t.key"
          class="sales-pill" :class="{active:activeTab===t.key, ['pill-'+t.key]: t.key!=='all'}"
          @click="activeTab=t.key">
          {{ t.label }}
          <span v-if="t.key!=='all'" class="sales-pill-count">{{ counts[t.key] }}</span>
        </button>
      </div>
      <div style="display:flex;gap:8px;margin-left:auto">
        <button class="sales-btn-ghost view-toggle-btn" @click="viewMode=viewMode==='table'?'grid':'table'" :title="viewMode==='table'?'Grid View':'List View'"><span v-html="icon(viewMode==='table'?'grid':'file',14)"></span></button>
        <button class="sales-btn-ghost" @click="load" title="Refresh"><span v-html="icon('refresh',14)"></span></button>
        <button class="sales-btn-ghost" @click="exportCSV" title="Export CSV"><span v-html="icon('download',14)"></span> CSV</button>
        <button class="sales-btn-primary" @click="openNew" :disabled="!$canWrite('bills')" :title="!$canWrite('bills') ? 'Read-only access' : ''">
          <span v-html="icon('plus',13)"></span> New Bill
        </button>
      </div>
    </div>

    <!-- ── KPI Cards ── -->
    <div class="bk-kpi-grid">
      <div class="bk-kpi-card bk-kpi-accent clickable" @click="activeTab='all'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#dbeafe"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.8"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Total Bills</div><div class="bk-kpi-value">{{ list.length }}</div><div class="bk-kpi-trend" :class="billTrends.total.up?'bk-trend-up':'bk-trend-down'">{{ billTrends.total.up?'↑':'↓' }} {{ billTrends.total.pct }}% vs last month</div></div></div></div>
      <div class="bk-kpi-card clickable" @click="activeTab='draft'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#f1f5f9"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#6b7280" stroke-width="1.8"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Draft</div><div class="bk-kpi-value bk-kpi-amber">{{ counts.draft }}</div><div class="bk-kpi-trend bk-trend-neutral">— drafts</div></div></div></div>
      <div class="bk-kpi-card bk-kpi-warn clickable" @click="activeTab='unpaid'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#fef3c7"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Unpaid</div><div class="bk-kpi-value bk-kpi-amber">{{ counts.unpaid }}</div><div class="bk-kpi-trend" :class="billTrends.unpaid.up?'bk-trend-up':'bk-trend-down'">{{ billTrends.unpaid.up?'↑':'↓' }} {{ billTrends.unpaid.pct }}% vs last month</div></div></div></div>
      <div class="bk-kpi-card bk-kpi-danger clickable" @click="activeTab='overdue'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#fee2e2"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="1.8"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Overdue</div><div class="bk-kpi-value bk-kpi-red">{{ counts.overdue }}</div><div class="bk-kpi-trend" :class="billTrends.overdue.up?'bk-trend-down':'bk-trend-up'">{{ billTrends.overdue.up?'↑':'↓' }} {{ billTrends.overdue.pct }}% vs last month</div></div></div></div>
      <div class="bk-kpi-card bk-kpi-success clickable" @click="activeTab='paid'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#dcfce7"><svg width="22" height="22" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="#16a34a" stroke-width="1.8"/><polyline points="7 12.5 10.5 16 17 9" stroke="#16a34a" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Paid</div><div class="bk-kpi-value bk-kpi-green">{{ counts.paid }}</div><div class="bk-kpi-trend" :class="billTrends.paid.up?'bk-trend-up':'bk-trend-down'">{{ billTrends.paid.up?'↑':'↓' }} {{ billTrends.paid.pct }}% vs last month</div></div></div></div>
    </div>
    <div class="bk-stat-grid">
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">This Month Bills</div><div class="bk-stat-value">{{ billThisMonth.count }}</div></div><div class="bk-stat-icon" style="background:#dbeafe;color:#2563eb"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg></div></div></div>
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">This Month Spend</div><div class="bk-stat-value" style="font-size:16px">{{ fmtCur(billThisMonth.spend) }}</div></div><div class="bk-stat-icon" style="background:#fee2e2;color:#dc2626"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12"/><path d="M6 8h12"/><path d="m6 13 8.5 8"/><path d="M6 13h3"/><path d="M9 13c6.667 0 6.667-10 0-10"/></svg></div></div></div>
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">Total Payable</div><div class="bk-stat-value bk-kpi-amber" style="font-size:16px">{{ fmtCur(summary.totalDue) }}</div></div><div class="bk-stat-icon" style="background:#fef3c7;color:#d97706"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg></div></div></div>
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">Avg Bill Value</div><div class="bk-stat-value" style="font-size:16px">{{ fmtCur(billAvg) }}</div></div><div class="bk-stat-icon" style="background:#e5e7eb;color:#6b7280"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg></div></div></div>
    </div>

    <!-- ── Bulk action bar ── -->
    <BulkActionBar :count="selected.size" @clear="selected=new Set()">
      <button @click="bulkEmail"><span v-html="icon('mail',13)"></span> Send Email</button>
      <button @click="bulkCancel">Cancel Submitted</button>
      <button class="bab-danger" @click="bulkDelete">Delete Drafts</button>
      <button @click="exportCSV"><span v-html="icon('download',13)"></span> Export CSV</button>
    </BulkActionBar>

    <!-- ── Table ── -->
    <div class="inv-table-wrap">
      <template v-if="viewMode==='table'">
      <table class="inv-table bil-desktop-table">
        <thead>
          <tr>
            <th style="width:32px"><input type="checkbox" @change="toggleAll" :checked="allChecked" /></th>
            <th @click="sortBy('name')" class="sortable">Bill # <span v-html="sortArrow('name')"></span></th>
            <th @click="sortBy('supplier_name')" class="sortable">Vendor <span v-html="sortArrow('supplier_name')"></span></th>
            <th @click="sortBy('posting_date')" class="sortable">Date <span v-html="sortArrow('posting_date')"></span></th>
            <th @click="sortBy('due_date')" class="sortable">Due Date <span v-html="sortArrow('due_date')"></span></th>
            <th>Status</th>
            <th @click="sortBy('grand_total')" class="sortable ta-r">Amount <span v-html="sortArrow('grand_total')"></span></th>
            <th @click="sortBy('outstanding_amount')" class="sortable ta-r">Balance <span v-html="sortArrow('outstanding_amount')"></span></th>
            <th style="width:120px;text-align:center">Actions</th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 7" :key="n"><td colspan="10"><div class="shimmer"></div></td></tr>
          </template>
          <template v-else>
            <tr v-for="b in paged" :key="b.name" class="inv-row" :class="{selected:selected.has(b.name)}">
              <td class="td-check"><input type="checkbox" :checked="selected.has(b.name)" @change="toggle(b.name)" /></td>
              <td class="td-id" @click="openView(b)"><span class="inv-link">{{ b.name }}</span></td>
              <td class="td-customer" @click="openView(b)">{{ b.supplier_name || b.supplier || '—' }}</td>
              <td class="td-date text-muted mono-sm" @click="openView(b)">{{ fmtDate(b.posting_date) }}</td>
              <td class="td-due mono-sm" :class="isOverdue(b)?'text-danger':'text-muted'" @click="openView(b)">{{ fmtDate(b.due_date)||'—' }}</td>
              <td class="td-status" @click="openView(b)"><span class="inv-status-badge" :class="statusCls(b)">{{ statusLabel(b) }}</span></td>
              <td class="td-amount ta-r mono-sm" @click="openView(b)">{{ fmtCur(b.grand_total) }}</td>
              <td class="td-balance ta-r mono-sm" @click="openView(b)" :class="{'text-danger':flt(b.outstanding_amount)>0,'text-success':flt(b.outstanding_amount)<=0&&b.docstatus===1}">{{ fmtCur(b.outstanding_amount) }}</td>
              <td class="td-actions bill-act-cell">
                <button class="inv-act-btn" @click="openView(b)" title="View"><span v-html="icon('eye',13)"></span></button>
                <button v-if="b.docstatus===0" class="inv-act-btn" @click="openEdit(b)" title="Edit"><span v-html="icon('edit',13)"></span></button>
                <button v-if="b.docstatus===1 && flt(b.outstanding_amount)>0" class="inv-act-btn inv-act-pay" @click="payBill(b)" title="Record Payment">₹</button>
                <button v-if="b.docstatus===0 || b.docstatus===2" class="inv-act-btn bill-act-del" @click="deleteBill(b)" title="Delete"><span v-html="icon('trash',13)"></span></button>
              </td>
            </tr>
            <tr v-if="!sorted.length"><td colspan="10" class="bk-empty-state"><div class="bk-empty-inner"><template v-if="search||filterVendor"><svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.3"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg><p class="bk-empty-title">No bills match your filters</p></template><template v-else><div class="bk-empty-illus"><svg width="80" height="96" viewBox="0 0 80 96" fill="none"><rect x="10" y="8" width="60" height="80" rx="6" fill="#e2e8f0"/><rect x="14" y="12" width="52" height="72" rx="4" fill="#fff"/><rect x="22" y="26" width="36" height="3" rx="2" fill="#e2e8f0"/><rect x="22" y="34" width="28" height="3" rx="2" fill="#e2e8f0"/><rect x="22" y="42" width="32" height="3" rx="2" fill="#e2e8f0"/><rect x="50" y="64" width="18" height="20" rx="3" fill="#f59e0b" opacity=".7"/><rect x="36" y="70" width="12" height="14" rx="3" fill="#2563eb" opacity=".6"/></svg></div><p class="bk-empty-title">No bills created yet</p><p class="bk-empty-sub">Add your first vendor bill to start tracking payables.</p><button class="bk-empty-btn" @click="openNew"><span v-html="icon('plus',13)"></span> New Bill</button></template></div></td></tr>
          </template>
        </tbody>
      </table>

      <!-- Mobile cards (shown at ≤768px, hidden on desktop) -->
      <div class="bil-mobile-cards">
        <template v-if="loading">
          <div v-for="n in 5" :key="n" class="bil-mobile-card bil-mc--skeleton">
            <div class="bil-mc-shimmer" style="height:13px;width:55%;margin-bottom:8px"></div>
            <div class="bil-mc-shimmer" style="height:11px;width:40%;margin-bottom:6px"></div>
            <div class="bil-mc-shimmer" style="height:11px;width:65%"></div>
          </div>
        </template>
        <div v-else-if="!sorted.length" class="bil-mc-empty">
          <div style="font-size:32px;margin-bottom:8px">🧾</div>
          <div>No bills found</div>
        </div>
        <template v-else>
          <div v-for="b in paged" :key="b.name" class="bil-mobile-card" @click="openView(b)">
            <div class="bil-mc-top">
              <span class="bil-mc-docno">{{ b.name }}</span>
              <span class="inv-status-badge" :class="statusCls(b)">{{ statusLabel(b) }}</span>
            </div>
            <div class="bil-mc-mid">{{ b.supplier_name || b.supplier || '—' }}</div>
            <div class="bil-mc-meta">
              <span>{{ fmtDate(b.posting_date) }}</span>
              <span class="bil-mc-amount">{{ fmtCur(b.grand_total) }}</span>
            </div>
            <div v-if="flt(b.outstanding_amount) > 0" class="bil-mc-balance">
              Due: {{ fmtDate(b.due_date) || '—' }} · Balance: <span :class="isOverdue(b)?'text-danger':''">{{ fmtCur(b.outstanding_amount) }}</span>
            </div>
            <div class="bil-mc-footer">
              <button class="bil-mc-btn" @click.stop="openView(b)">View</button>
              <button v-if="b.docstatus===0" class="bil-mc-btn" @click.stop="openEdit(b)">Edit</button>
              <button v-if="b.docstatus===1 && flt(b.outstanding_amount)>0" class="bil-mc-btn bil-mc-pay" @click.stop="payBill(b)">Pay</button>
              <button v-if="b.docstatus===0||b.docstatus===2" class="bil-mc-btn bil-mc-danger" @click.stop="deleteBill(b)">Delete</button>
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
            <div style="font-size:32px;margin-bottom:8px">🧾</div>
            <div>{{ search || filterVendor ? 'No bills match your filters' : 'No bills yet' }}</div>
            <button v-if="!search && !filterVendor" class="nim-btn nim-btn-primary" :disabled="!$canWrite('bills')" :title="!$canWrite('bills') ? 'Read-only access' : ''" style="margin-top:14px" @click="openNew"><span v-html="icon('plus',13)"></span> New Bill</button>
          </div>
          <template v-else>
            <div v-for="b in paged" :key="b.name"
              class="b-card b-card-body"
              style="cursor:pointer;padding:16px;display:flex;flex-direction:column;gap:8px"
              @click="openView(b)">
              <div style="display:flex;align-items:center;justify-content:space-between;gap:8px">
                <span style="font-size:12px;font-weight:700;color:#2563eb">{{ b.name }}</span>
                <span class="inv-status-badge" :class="statusCls(b)">{{ statusLabel(b) }}</span>
              </div>
              <div style="font-size:13.5px;font-weight:600;color:#1a1d23;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ b.supplier_name || b.supplier || '—' }}</div>
              <div style="display:flex;justify-content:space-between;font-size:12px;color:#6b7280">
                <span>{{ fmtDate(b.posting_date) }}</span>
                <span style="font-weight:700;color:#1a1d23">{{ fmtCur(b.grand_total) }}</span>
              </div>
              <div v-if="flt(b.outstanding_amount) > 0" style="font-size:11.5px;" :class="isOverdue(b)?'text-danger':'text-muted'">
                Balance: {{ fmtCur(b.outstanding_amount) }}
              </div>
              <div style="display:flex;gap:6px;border-top:1px solid #f3f4f6;padding-top:10px">
                <button class="inv-act-btn" @click.stop="openView(b)" title="View"><span v-html="icon('eye',13)"></span></button>
                <button v-if="b.docstatus===0" class="inv-act-btn" @click.stop="openEdit(b)" title="Edit"><span v-html="icon('edit',13)"></span></button>
                <button v-if="b.docstatus===1 && flt(b.outstanding_amount)>0" class="inv-act-btn inv-act-pay" @click.stop="payBill(b)" title="Record Payment">₹</button>
                <button v-if="b.docstatus===0||b.docstatus===2" class="inv-act-btn" style="color:#dc2626" @click.stop="deleteBill(b)" title="Delete"><span v-html="icon('trash',13)"></span></button>
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

    <!-- ── Create / Edit drawer ── -->
    <div v-if="drawerOpen" class="inv-drawer-bg" @click.self="drawerOpen=false"></div>
    <div class="inv-drawer-panel bill-edit-drawer" :class="{open:drawerOpen}">

      <!-- Header -->
      <div class="inv-dh">
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
          <div class="inv-dh-title">{{ editingName ? 'Edit Bill' : 'New Bill' }}</div>
          <span v-if="!editingName" class="add-status-badge">Draft</span>
        </div>
        <button class="inv-dclose" @click="drawerOpen=false"><span v-html="icon('x',16)"></span></button>
      </div>

      <div class="inv-dbody">

        <!-- ══ CARD 1: Bill Details ══ -->
        <div class="add-card">
          <div class="add-card-header" @click="billCollapsed.details=!billCollapsed.details">
            <div class="add-card-title">
              <span class="add-card-title-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></span>
              Bill Details
            </div>
            <span class="add-card-chevron" :class="{collapsed:billCollapsed.details}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
          </div>
          <div class="add-card-body" :class="{collapsed:billCollapsed.details}">
            <div>
              <label class="inv-lbl">Vendor <span class="inv-req">*</span></label>
              <SearchableSelect v-model="form.supplier" :options="vendors"
                placeholder="Select vendor…" :createable="true" createDoctype="Supplier"
                @search="fetchVendors" @select="onVendorSelect" />
            </div>
            <div class="add-details-grid" style="margin-top:14px">
              <div>
                <label class="inv-lbl">Bill Date <span class="inv-req">*</span></label>
                <input v-model="form.posting_date" type="date" class="inv-fi" />
              </div>
              <div>
                <label class="inv-lbl">Due Date</label>
                <input v-model="form.due_date" type="date" class="inv-fi" />
              </div>
              <div>
                <label class="inv-lbl">Vendor Bill #</label>
                <input v-model="form.bill_no" type="text" class="inv-fi" placeholder="Vendor's invoice number" maxlength="50" />
              </div>
              <div>
                <label class="inv-lbl">Vendor Bill Date</label>
                <input v-model="form.bill_date" type="date" class="inv-fi" />
              </div>
              <div>
                <label class="inv-lbl">Cost Center</label>
                <select v-model="form.cost_center" class="inv-fi">
                  <option value="">— Select —</option>
                  <option v-for="cc in costCenters" :key="cc" :value="cc">{{ cc }}</option>
                </select>
              </div>
            </div>

            <!-- Inventory toggle -->
            <div style="margin-top:14px">
              <div class="inv-inv-block" :class="form.update_stock ? 'inv-on' : 'inv-off'">
                <div class="inv-inv-toggle-row">
                  <div class="inv-inv-icon" v-html="icon('box', 16)"></div>
                  <div class="inv-inv-text">
                    <div class="inv-inv-title">Update Inventory on Submit</div>
                    <div class="inv-inv-sub">Stock increases in the selected warehouse when this bill is submitted</div>
                  </div>
                  <label class="inv-inv-switch">
                    <input type="checkbox" v-model="form.update_stock" :true-value="1" :false-value="0" />
                    <span class="inv-inv-slider"></span>
                  </label>
                </div>
                <div v-if="form.update_stock" class="inv-inv-wh-row">
                  <label class="inv-lbl" style="margin-bottom:6px">Receiving Warehouse <span style="color:#dc2626">*</span></label>
                  <SearchableSelect v-model="form.set_warehouse" :options="warehouses" placeholder="Select warehouse where stock will be received…" :createable="true" createDoctype="Warehouse" @search="fetchWarehouses" @create="fetchWarehouses('')" />
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ══ CARD 2: Billing Address ══ -->
        <div class="add-card">
          <div class="add-card-header" @click="billCollapsed.billing=!billCollapsed.billing">
            <div class="add-card-title">
              <span class="add-card-title-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg></span>
              Billing Address
            </div>
            <span class="add-card-chevron" :class="{collapsed:billCollapsed.billing}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
          </div>
          <div class="add-card-body" :class="{collapsed:billCollapsed.billing}">
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
                @create="openAddrModal"
              />
            </div>
            <div v-if="selectedBillingAddr" class="po-addr-card">
              <div class="po-addr-card-type">{{ selectedBillingAddr.address_type || 'Billing' }}</div>
              <div class="po-addr-card-text">{{ formatAddress(selectedBillingAddr) }}</div>
            </div>
          </div>
        </div>

        <!-- ══ CARD 3: Line Items ══ -->
        <div class="add-card">
          <div class="add-card-header" @click="billCollapsed.lines=!billCollapsed.lines">
            <div class="add-card-title">
              <span class="add-card-title-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
              </span>
              Line Items
              <span class="po-item-count">{{ lines.length }} item{{ lines.length !== 1 ? 's' : '' }}</span>
            </div>
            <span class="add-card-chevron" :class="{collapsed:billCollapsed.lines}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
          </div>
          <div class="add-card-body" :class="{collapsed:billCollapsed.lines}">
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
                        <option value="">&#8212; No Tax &#8212;</option>
                        <option v-for="t in taxTemplates" :key="t.name" :value="t.name">{{ t.template_name || t.name }}</option>
                      </select>
                    </div>
                    <div class="po-item-num-row">
                      <div class="po-item-field">
                        <label>Qty</label>
                        <input v-model.number="line.qty" type="number" min="0" step="0.001" class="inv-fi" :class="{'field-error': line.qty > 999999999}" @input="e => { if(Number(e.target.value) > 999999999){ line.qty = 999999999; e.target.value = 999999999; } calcLine(line); }" />
                        <div v-if="line.qty > 999999999" class="exp-field-hint exp-field-hint-err">⚠ Qty cannot exceed 999,999,999</div>
                      </div>
                      <div class="po-item-field">
                        <label>Rate (₹)</label>
                        <input v-model.number="line.rate" type="number" min="0" step="0.01" class="inv-fi" :class="{'field-error': line.rate > 999999999}" @input="e => { if(Number(e.target.value) > 999999999){ line.rate = 999999999; e.target.value = 999999999; } calcLine(line); }" />
                        <div v-if="line.rate > 999999999" class="exp-field-hint exp-field-hint-err">⚠ Rate cannot exceed 999,999,999</div>
                      </div>
                    </div>
                    <div class="po-item-hint">Pricing is calculated based on current inventory stock and regional tax policies.</div>
                  </div>
                </div>
                <div v-if="form.update_stock && line.has_batch_no" class="po-item-col" style="grid-column:1 / -1;display:grid;grid-template-columns:2fr 1fr;gap:6px;padding:0 0 12px" v-show="!line.collapsed">
                  <SearchableSelect v-model="line.batch_no" :options="line.batchOptions" placeholder="Batch No — select existing or type to create new"
                    createable @search="q => fetchBillLineBatches(line, q)" @select="opt => onBillLineBatchSelect(line, opt)" @create="val => onBillLineBatchCreate(line, val)" style="font-size:12px"/>
                  <span style="font-size:11px;color:#9ca3af;align-self:center">{{ line.batchOptions.length ? 'Batch-tracked — required' : 'No batches yet — type a new code' }}</span>
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
                <div v-if="form.tds_applicable && tdsAmount > 0" class="po-total-row" style="color:#d97706;font-size:12px">
                  <span>TDS u/s {{ form.tds_section }} ({{ form.tds_rate }}%)</span>
                  <span style="color:#d97706">− {{ fmtCur(tdsAmount) }}</span>
                </div>
                <div class="po-total-row grand"><span>Grand Total</span><span>{{ fmtCur(grandTotal - tdsAmount) }}</span></div>
              </div>
            </div>
          </div>
        </div>

        <!-- ══ CARD 4: Remarks ══ -->
        <div class="add-card">
          <div class="add-card-header" @click="billCollapsed.remarks=!billCollapsed.remarks">
            <div class="add-card-title">
              <span class="add-card-title-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></span>
              Remarks
            </div>
            <span class="add-card-chevron" :class="{collapsed:billCollapsed.remarks}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
          </div>
          <div class="add-card-body" :class="{collapsed:billCollapsed.remarks}">
            <label class="inv-lbl" style="display:flex;justify-content:space-between;align-items:center">
              <span>Internal Remarks <span style="color:#9ca3af;font-weight:400">(not printed)</span></span>
              <span :style="{color: form.remarks.length > 500 ? '#ef4444' : form.remarks.length > 450 ? '#f59e0b' : '#9ca3af', fontSize:'11px', fontWeight:'600'}">{{ form.remarks.length }}/500</span>
            </label>
            <textarea v-model="form.remarks" rows="3" class="inv-fi" placeholder="Internal notes for your team…" maxlength="500"></textarea>
            <div v-if="form.remarks.length >= 500" style="font-size:11px;color:#ef4444;margin-top:3px">Character limit reached</div>
          </div>
        </div>

      </div><!-- /inv-dbody -->

      <!-- Footer -->
      <div class="inv-dfooter">
        <div class="add-footer-status">{{ editingName ? 'Editing: ' + editingName : 'New bill — unsaved changes' }}</div>
        <div class="add-footer-actions">
          <button class="add-btn-cancel" @click="drawerOpen=false">Cancel</button>
          <button class="add-btn-draft" :disabled="drawerSaving" @click="saveBill(0)">
            <span v-html="icon('save',13)"></span> {{ drawerSaving ? 'Saving…' : 'Save Draft' }}
          </button>
          <button class="add-btn-more" :disabled="drawerSaving" @click="saveBill(1)">
            <span v-html="icon('check',13)"></span> {{ drawerSaving ? 'Saving…' : 'Submit' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ── View drawer ── -->
    <div v-if="viewOpen" class="inv-drawer-bg" @click.self="viewOpen=false"></div>
    <div class="inv-drawer-panel bill-view-drawer" :class="{open:viewOpen}">
      <template v-if="viewDoc">

        <!-- Top header: bill number + badge | Pay CTA -->
        <div class="inv-view-header bill-view-page-header">
          <div style="display: flex;justify-content: space-between;width: stretch;">
            <div class="inv-view-header-left">
              <div class="inv-view-title-row">
                <span class="inv-view-number">{{ viewDoc.name }}</span>
                <span class="inv-hdr-badge" :class="statusCls(viewDoc)">{{ statusLabel(viewDoc) }}</span>
              </div>
              <div class="inv-view-subtitle">
                {{ viewDoc.supplier_name || viewDoc.supplier }}
                <span v-if="viewDoc.due_date"> · Due {{ fmtDate(viewDoc.due_date) }}
                  <span v-if="isOverdue(viewDoc)" style="color:#dc2626">(overdue)</span>
                </span>
              </div>
            </div>
            <div class="bill-view-cta-wrap">
              <button v-if="flt(viewDoc.outstanding_amount)>0 && viewDoc.docstatus===1"
                      class="inv-view-cta"
                      @click="payBill(viewDoc)">
                <span v-html="icon('indianrupee',15)"></span> Record Payment
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
            <TimelineStepper :steps="timelineSteps" />
          </div>

          <!-- Action buttons bar -->
          <div class="inv-action-bar">
            <button v-if="viewDoc.docstatus===0" class="inv-ab-btn" @click="viewOpen=false;openEdit(viewDoc)">
              <span v-html="icon('edit',13)"></span> <span class="ab-label">Edit</span>
            </button>
            <button v-if="viewDoc.docstatus===0" class="inv-ab-btn" style="color:#16a34a;border-color:rgba(22,163,106,.3)" @click="submitBill(viewDoc)">
              <span v-html="icon('check',13)"></span> <span class="ab-label">Submit</span>
            </button>
            <div style="position:relative;display:inline-flex">
              <button class="inv-ab-btn inv-ab-dropdown" @click="showDownloadMenu=!showDownloadMenu">
                <span v-html="icon('download',13)"></span> <span class="ab-label">Download</span>
                <span class="inv-ab-caret">▾</span>
              </button>
              <div v-if="showDownloadMenu" class="inv-dl-menu">
                <div class="inv-dl-menu-header">Export Bill</div>
                <button @click="downloadBillPdf('pdf')" class="inv-dl-menu-item">
                  <span class="inv-dl-menu-icon" v-html="icon('download',14)"></span>
                  <span class="inv-dl-menu-text">
                    <span class="inv-dl-menu-label">Download PDF</span>
                    <span class="inv-dl-menu-sub">Save to your device</span>
                  </span>
                </button>
                <button @click="downloadBillPdf('print')" class="inv-dl-menu-item">
                  <span class="inv-dl-menu-icon" v-html="icon('printer',14)"></span>
                  <span class="inv-dl-menu-text">
                    <span class="inv-dl-menu-label">Open &amp; Print</span>
                    <span class="inv-dl-menu-sub">Preview in new tab</span>
                  </span>
                </button>
              </div>
            </div>
            <button v-if="viewDoc.docstatus===1" class="inv-ab-btn" @click="emailBill(viewDoc)">
              <span v-html="icon('mail',13)"></span> <span class="ab-label">Email</span>
            </button>
            <button v-if="viewDoc.docstatus===1 && flt(viewDoc.outstanding_amount) > 0" class="inv-ab-btn" @click="issueDebitNote(viewDoc)">
              <span v-html="icon('arrow-left',13)"></span> <span class="ab-label">Debit Note</span>
            </button>
            <button v-if="viewDoc.docstatus===1" class="inv-ab-btn" @click="makeRecurringBill(viewDoc)">
              <span v-html="icon('repeat',13)"></span> <span class="ab-label">Make Recurring</span>
            </button>
            <button v-if="viewDoc.docstatus===1" class="inv-ab-btn inv-ab-danger" @click="cancelBill(viewDoc)">
              Cancel
            </button>
            <button v-if="viewDoc.docstatus===0 || viewDoc.docstatus===2" class="inv-ab-btn inv-ab-danger" @click="deleteBill(viewDoc)">
              <span v-html="icon('trash',13)"></span> <span class="ab-label">Delete</span>
            </button>
          </div>

          <!-- Tabs -->
          <div class="inv-view-tabs">
            <button class="inv-vtab" :class="{active:viewTab==='details'}" @click="viewTab='details'">Details</button>
            <button class="inv-vtab" :class="{active:viewTab==='payments'}" @click="viewTab='payments'">
              Payments<span v-if="viewPayments.length || viewDebitApps.length" class="inv-vtab-count">{{ viewPayments.length + viewDebitApps.length }}</span>
            </button>
          </div>

          <!-- ── Details tab ── -->
          <template v-if="viewTab==='details'">
            <div class="inv-tab-body">

              <!-- Meta row -->
              <div class="inv-details-meta" style="grid-template-columns:repeat(3,1fr)">
                <div class="inv-details-meta-col">
                  <div class="inv-dmeta-icon-row">
                    <span class="inv-dmeta-icon" v-html="icon('user',13)"></span>
                    <span class="inv-dmeta-lbl">Vendor</span>
                  </div>
                  <div class="inv-dmeta-primary">{{ viewDoc.supplier_name||viewDoc.supplier }}</div>
                  <div v-if="viewDoc.bill_no" class="inv-dmeta-secondary">Vendor Bill # {{ viewDoc.bill_no }}</div>
                </div>
                <div class="inv-details-meta-col">
                  <div class="inv-dmeta-icon-row">
                    <span class="inv-dmeta-icon" v-html="icon('calendar',13)"></span>
                    <span class="inv-dmeta-lbl">Bill Date</span>
                  </div>
                  <div class="inv-dmeta-date-val">{{ fmtDate(viewDoc.posting_date) }}</div>
                </div>
                <div class="inv-details-meta-col col-balance">
                  <div class="inv-dmeta-icon-row">
                    <span class="inv-dmeta-icon" v-html="icon('indianrupee',13)"></span>
                    <span class="inv-dmeta-lbl">Balance Due</span>
                  </div>
                  <div class="inv-balance-val"
                       :class="{'is-paid': flt(viewDoc.outstanding_amount)===0, 'is-zero': flt(viewDoc.outstanding_amount)===0}">
                    {{ fmtCur(viewDoc.outstanding_amount) }}
                  </div>
                  <button v-if="flt(viewDoc.outstanding_amount)>0 && viewDoc.docstatus===1"
                          class="inv-rec-pay-btn"
                          @click="payBill(viewDoc)">
                    Record Payment
                  </button>
                </div>
              </div>

              <div v-if="viewLoading" style="padding:24px;text-align:center;color:#9ca3af">Loading details…</div>

              <template v-else>
                <!-- Line items cards -->
                <template v-if="viewItems.length">
                  <div class="inv-sec-lbl">Line Items <span class="po-item-count">{{ viewItems.length }} item{{ viewItems.length !== 1 ? 's' : '' }}</span></div>
                  <div class="vi-line-cards">
                    <div v-for="(it, idx) in viewItems" :key="idx" class="vi-line-card">
                      <div class="vi-line-card-header">
                        <span class="vi-line-num">#{{ idx + 1 }}</span>
                        <span class="vi-line-name">{{ it.item_name || it.item_code }}</span>
                        <span class="vi-line-amount">{{ fmtCur(it.amount) }}</span>
                      </div>
                      <div v-if="it.description" class="vi-line-desc">{{ it.description }}</div>
                      <div class="vi-line-meta">
                        <div class="vi-line-meta-item">
                          <span class="vi-meta-lbl">Qty</span>
                          <span class="vi-meta-val">{{ flt(it.qty) }}</span>
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

                  <!-- Totals -->
                  <div class="po-view-totals">
                    <div class="po-view-totals-inner">
                      <div class="po-view-total-row">
                        <span>Subtotal</span>
                        <span>{{ fmtCur(viewSubtotal) }}</span>
                      </div>
                      <template v-if="viewGstLines.length">
                        <div v-for="tl in viewGstLines" :key="tl.template" class="po-view-total-row po-view-tax-row">
                          <span class="po-view-tax-label">
                            <span class="po-view-tax-badge">TAX</span>
                            {{ tl.template }}
                            <span class="po-view-tax-rate">{{ tl.rate }}%</span>
                          </span>
                          <span>{{ fmtCur(tl.amount) }}</span>
                        </div>
                      </template>
                      <div v-else-if="!viewTdsLine" class="po-view-total-row po-view-tax-row">
                        <span class="po-view-tax-label">
                          <span class="po-view-tax-badge po-view-tax-badge--none">NO TAX</span>
                          No taxes applied
                        </span>
                        <span>{{ fmtCur(0) }}</span>
                      </div>
                      <div v-if="viewTdsLine" class="po-view-total-row" style="color:#d97706">
                        <span>{{ viewTdsLine.label }} <span style="opacity:.7">({{ viewTdsLine.rate }}%)</span></span>
                        <span>− {{ fmtCur(viewTdsLine.amount) }}</span>
                      </div>
                      <div class="po-view-total-row po-view-grand">
                        <span>Grand Total</span>
                        <span>{{ fmtCur(viewDoc.grand_total) }}</span>
                      </div>
                    </div>
                  </div>
                </template>
                <div v-else style="color:#9ca3af;font-size:13px;padding:8px 0">No item details available.</div>
                <!-- Cost Center badge -->
                <div v-if="viewDoc.cost_center" style="margin-top:10px;display:flex;align-items:center;gap:8px;font-size:12.5px">
                  <span style="color:#6b7280;font-weight:600">Cost Center:</span>
                  <span style="background:#f0fdf4;border:1px solid #bbf7d0;color:#15803d;border-radius:5px;padding:2px 10px;font-weight:600">{{ viewDoc.cost_center }}</span>
                </div>
                <div v-if="viewDoc.set_warehouse" style="margin-top:10px;display:flex;align-items:center;gap:8px;font-size:12.5px">
                  <span style="color:#6b7280;font-weight:600">Receiving Warehouse:</span>
                  <span style="background:#eff6ff;border:1px solid #bfdbfe;color:#1d4ed8;border-radius:5px;padding:2px 10px;font-weight:600;display:inline-flex;align-items:center;gap:5px"><span v-html="icon('warehouse',12)"></span>{{ viewDoc.set_warehouse }}</span>
                </div>
                <!-- Internal Remark -->
                <div v-if="viewDoc.remark" style="margin-top:12px">
                  <div class="inv-dmeta-icon-row" style="margin-bottom:6px">
                    <span class="inv-dmeta-icon" v-html="icon('edit',13)"></span>
                    <span class="inv-dmeta-lbl">Internal Remark</span>
                  </div>
                  <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 14px;font-size:12.5px;color:#374151;white-space:pre-wrap;word-break:break-word;line-height:1.6">{{ viewDoc.remark }}</div>
                </div>
                <!-- Billing Address -->
                <div v-if="viewDoc.billing_address_name || viewDoc.billing_address" style="margin-top:14px">
                  <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px">
                    <span v-html="icon('map-pin',12)" style="color:#6b7280"></span>
                    <span style="font-size:10.5px;font-weight:700;text-transform:uppercase;color:#6b7280;letter-spacing:0.5px">Billing Address</span>
                  </div>
                  <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px 14px">
                    <span style="display:inline-block;background:#dbeafe;color:#2563eb;font-size:10px;font-weight:700;text-transform:uppercase;padding:2px 8px;border-radius:20px;letter-spacing:0.4px;margin-bottom:8px">Billing</span>
                    <div style="font-size:13px;color:#374151;line-height:1.65;white-space:pre-line">{{ displayAddr(viewBillingAddr ? formatAddress(viewBillingAddr) : viewDoc.billing_address) }}</div>
                  </div>
                </div>
              </template>
            </div>
          </template>

          <!-- ── Payments tab ── -->
          <template v-if="viewTab==='payments'">
            <div class="inv-tab-body">
              <div v-if="viewLoading" style="text-align:center;padding:24px;color:#9ca3af;font-size:13px">Loading payments…</div>
              <template v-else>

                <!-- Cash / bank payments -->
                <div v-if="viewPayments.length" class="inv-items-wrap">
                  <div class="inv-pay-section-lbl">Payments Made</div>
                  <table class="inv-items-table inv-payments-tbl">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Mode</th>
                        <th>Reference</th>
                        <th class="th-r">Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="p in viewPayments" :key="p.name">
                        <td class="mono-sm">{{ fmtDate(p.payment_date) }}</td>
                        <td>{{ p.mode_of_payment || '—' }}</td>
                        <td class="mono-sm text-muted">{{ p.reference_no || '—' }}</td>
                        <td class="td-r" style="font-weight:600;color:#059669">{{ fmtCur(p.paid_amount) }}</td>
                      </tr>
                    </tbody>
                  </table>
                  <!-- Mobile cards -->
                  <div class="bil-pay-mobile-cards">
                    <div v-for="p in viewPayments" :key="p.name" class="bil-pay-mc">
                      <div class="bil-pay-mc-top">
                        <span class="bil-pay-mc-date">{{ fmtDate(p.payment_date) }}</span>
                        <span class="bil-pay-mc-amount">{{ fmtCur(p.paid_amount) }}</span>
                      </div>
                      <div class="bil-pay-mc-bottom">
                        <span class="bil-pay-mc-mode">{{ p.mode_of_payment || '—' }}</span>
                        <span class="bil-pay-mc-ref">{{ p.reference_no || '—' }}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Debit note applications -->
                <div v-if="viewDebitApps.length" class="inv-items-wrap" style="margin-top:12px">
                  <div class="inv-pay-section-lbl inv-pay-section-lbl-dn">Debit Notes</div>
                  <table class="inv-items-table inv-payments-tbl">
                    <thead>
                      <tr>
                        <th>Debit Note</th>
                        <th>Date</th>
                        <th>Type</th>
                        <th class="th-r">Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(a, i) in viewDebitApps" :key="i">
                        <td class="mono-sm" style="color:#7c3aed;font-weight:600">{{ a.debit_note }}</td>
                        <td class="mono-sm">{{ fmtDate(a.date) }}</td>
                        <td>
                          <span v-if="a.type==='direct'" class="bil-dn-badge bil-dn-badge-direct">Issued</span>
                          <span v-else class="bil-dn-badge bil-dn-badge-applied">Applied</span>
                        </td>
                        <td class="td-r" style="font-weight:600;color:#7c3aed">{{ fmtCur(a.amount) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div v-if="!viewPayments.length && !viewDebitApps.length" style="text-align:center;padding:40px 24px;color:#9ca3af;font-size:13px">
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" stroke-width="1.3" style="margin-bottom:10px"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>
                  <div>No payments recorded yet.</div>
                  <div v-if="flt(viewDoc.outstanding_amount)>0 && viewDoc.docstatus===1" style="margin-top:12px">
                    <button class="inv-view-cta" @click="payBill(viewDoc)" style="font-size:12px;padding:7px 14px">₹ Record Payment</button>
                  </div>
                </div>
              </template>
            </div>
          </template>

        </div><!-- /inv-view-body -->

      </template>
    </div>

    <!-- ── Add New Address Modal ── -->
    <div v-if="addrModal.open" class="inv-drawer-bg" @click.self="addrModal.open=false" style="z-index:60"></div>
    <div v-if="addrModal.open" class="po-apply-dialog">
      <div class="inv-dh" style="height:auto;padding:14px 18px">
        <div class="inv-dh-title">Add New Address</div>
        <button class="inv-dclose" @click="addrModal.open=false"><span v-html="icon('x',16)"></span></button>
      </div>
      <div class="inv-dbody" style="padding:16px 18px;display:flex;flex-direction:column;gap:12px">
        <div class="add-details-grid">
          <div>
            <label class="inv-lbl">Address Title <span class="inv-req">*</span></label>
            <input v-model="addrModal.address_title" type="text" class="inv-fi" placeholder="e.g. Head Office" />
          </div>
          <div>
            <label class="inv-lbl">Address Type</label>
            <select v-model="addrModal.address_type" class="inv-fi">
              <option>Billing</option><option>Shipping</option><option>Office</option>
              <option>Personal</option><option>Plant</option><option>Postal</option>
              <option>Shop</option><option>Subsidiary</option><option>Warehouse</option><option>Other</option>
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
        <div class="add-details-grid">
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
        <div class="add-details-grid">
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

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from "vue";
import { useRoute } from "vue-router";
import { apiList, apiSave, apiGet, apiGET, apiSubmit, apiDelete, apiPOST, resolveCompany, refreshCsrfToken } from "../api/client.js";
import { useOpenFromQuery } from "../composables/useOpenFromQuery.js";
import { computeTaxRows } from "../composables/useTaxCalc.js";
import { stateFromGstin } from "../composables/useCountryState.js";
import { COUNTRIES, statesFor } from "../composables/useCountryState.js";
import { useToast } from "../composables/useToast.js";
import { usePermissions } from "../composables/usePermissions.js";
import { useDocStatus } from "../composables/useDocStatus.js";
import { useEmailDialog } from "../composables/useEmailDialog.js";
import { usePaymentDialog } from "../composables/usePaymentDialog.js";
import { useConfirmCascade } from "../composables/useConfirmCascade.js";
import { useReturnNote } from "../composables/useReturnNote.js";
import { useMakeRecurring } from "../composables/useMakeRecurring.js";
import { useConfirm } from "../composables/useConfirm.js";
import { useLivePreview } from "../composables/useLivePreview.js";
import { icon } from "../utils/icons.js";
import { flt, fmtDate } from "../utils/format.js";
import SearchableSelect from "../components/SearchableSelect.vue";
import SummaryStrip from "../components/SummaryStrip.vue";
import Pagination from "../components/Pagination.vue";
import { usePagination } from "../composables/usePagination.js";
import BulkActionBar from "../components/BulkActionBar.vue";
import TimelineStepper from "../components/TimelineStepper.vue";

const TDS_RATES = { "194C": 1, "194J": 10, "194A": 10, "194H": 5, "194I": 10, "192": 0, "195": 20, "Other": 10 };

const { toast } = useToast();
const route = useRoute();
const { canWrite } = usePermissions();
const { confirm } = useConfirm();
const { printDoc, renderDocument, setCompany, refreshBranding } = useLivePreview();
async function printBILL(d) { try { await refreshBranding(); } catch {} printDoc({ ...d, items: viewItems.value, taxes: viewTaxes.value }, { title: "BILL", partyLabel: "Vendor", partyField: "supplier_name", companyName: d?.company || "" }); }

const showDownloadMenu = ref(false);

function downloadBillPdf(mode = 'pdf') {
  showDownloadMenu.value = false;
  const doc = { ...viewDoc.value, items: viewItems.value, taxes: viewTaxes.value };
  if (!doc?.name) return;
  const html = renderDocument(doc, {
    title: "BILL",
    partyLabel: "Vendor",
    partyField: "supplier_name",
    companyName: doc.company || window.__booksCompany || "",
  });
  if (mode === 'print') {
    const win = window.open('', '_blank', 'width=820,height=1060,scrollbars=yes');
    if (!win) { toast('Pop-up blocked \u2014 allow pop-ups to print', 'error'); return; }
    win.document.write(html); win.document.close();
    setTimeout(() => { try { win.focus(); win.print(); } catch {} }, 600);
  } else {
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
    const objectUrl = URL.createObjectURL(blob);
    const win = window.open(objectUrl, '_blank', 'width=820,height=1060,scrollbars=yes');
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
const { openPayment } = usePaymentDialog();
const { confirmCascade } = useConfirmCascade();
const { openReturnNote } = useReturnNote();

// Status helpers tuned for Purchase Invoice
const { statusLabel, statusCls, statusBg, isOverdue } = useDocStatus({
  dueDateField: "due_date",
  outstandingField: "outstanding_amount",
  fallbackDraftLabel: "Draft",
  fallbackSubmittedLabel: "Unpaid",
});

const activeTab = ref("all");
const tabs = [
  { key: "all",     label: "All" },
  { key: "draft",   label: "Draft" },
  { key: "unpaid",  label: "Unpaid" },
  { key: "overdue", label: "Overdue" },
  { key: "paid",    label: "Paid" },
];

const list = ref([]), loading = ref(false), search = ref(""), selected = ref(new Set());
const viewMode = ref("table"); // "table" | "grid"
const drawerOpen = ref(false), drawerSaving = ref(false), editingName = ref("");
const viewOpen = ref(false), viewDoc = ref(null), viewTab = ref("details");
const billCollapsed = reactive({ details: false, billing: true, lines: false, remarks: true });
const viewLoading = ref(false), viewItems = ref([]), viewPayments = ref([]), viewTaxes = ref([]), viewDebitApps = ref([]);
const vendors = ref([]), items = ref([]), lines = ref([]), taxAccountHead = ref(""), taxTemplates = ref([]);
const companyGstState = ref(""), supplierState = ref("");
const gstAccounts = ref({ input_cgst:"", input_sgst:"", input_igst:"" });
const sortCol = ref("posting_date"), sortDir = ref("desc");
const copyingLast = ref(false);

let _id = 1;
const blankLine = () => ({ id: _id++, item_code: "", description: "", qty: 1, rate: 0, amount: 0, tax_code: "", collapsed: false, has_batch_no: 0, batch_no: "", batchOptions: [] });
const form = reactive({ supplier: "", posting_date: todayStr(), due_date: "", bill_no: "", bill_date: "", remarks: "", currency: "INR", exchange_rate: 1, update_stock: 1, set_warehouse: "", billing_address: "", billing_address_name: "", cost_center: "", tds_applicable: false, tds_section: "", tds_rate: 0 });
const vendorAddresses = ref([]);
const addrModal = reactive({
  open: false, saving: false,
  address_title: "", address_type: "Billing", address_line1: "", address_line2: "",
  city: "", state: "", pincode: "", country: "India",
});

function formatAddress(a) {
  if (!a) return "";
  return [a.address_line1, a.address_line2, a.city, a.state, a.pincode, a.country].filter(Boolean).join("\n");
}
function displayAddr(text) {
  if (!text) return "";
  return text.includes("\n") ? text : text.split(", ").join("\n");
}
const selectedBillingAddr = computed(() =>
  vendorAddresses.value.find(a => a.name === form.billing_address_name) || null
);

async function fetchVendorAddresses(supplier) {
  if (!supplier) { vendorAddresses.value = []; return; }
  try {
    const lnks = await apiList("Dynamic Link", {
      fields: ["parent"], filters: [["link_doctype","=","Supplier"],["link_name","=",supplier],["parenttype","=","Address"]], limit: 50
    });
    if (!lnks?.length) { vendorAddresses.value = []; return; }
    const addrs = await Promise.all(lnks.map(l => apiGet("Address", l.parent).catch(() => null)));
    vendorAddresses.value = addrs.filter(Boolean).map(a => {
      const rawTitle = a.address_title || a.name || "";
      const escaped  = supplier.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const cleaned  = rawTitle.replace(new RegExp("^" + escaped + "[-\\s]*", "i"), "").trim() || rawTitle;
      const title    = cleaned || a.address_type || "Address";
      return { ...a, label: `${title}${a.city ? " — " + a.city : ""}${a.address_type ? " (" + a.address_type + ")" : ""}` };
    });
  } catch { vendorAddresses.value = []; }
}

function onBillingAddrSelect(opt) {
  form.billing_address = opt ? formatAddress(opt) : "";
}
function openAddrModal() {
  Object.assign(addrModal, { open: true, saving: false, address_title: "", address_type: "Billing", address_line1: "", address_line2: "", city: "", state: "", pincode: "", country: "India" });
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
      links: form.supplier ? [{ doctype: "Address", link_doctype: "Supplier", link_name: form.supplier }] : [],
    };
    const saved = await apiSave(doc);
    toast.success("Address saved");
    await fetchVendorAddresses(form.supplier);
    const newAddr = vendorAddresses.value.find(a => a.name === saved?.name) || vendorAddresses.value[vendorAddresses.value.length - 1];
    if (newAddr) { form.billing_address_name = newAddr.name; form.billing_address = formatAddress(newAddr); }
    addrModal.open = false;
  } catch (e) { toast.error(e.message || "Failed to save address"); }
  addrModal.saving = false;
}
const warehouses = ref([]);
async function fetchWarehouses(q=""){try{const co=await resolveCompany();const r=await apiList("Warehouse",{fields:["name","parent_warehouse"],filters:[["company","=",co],["is_group","=",0],...(q?[["name","like",`%${q}%`]]:[])],limit:30});warehouses.value=r.map(x=>({label:x.parent_warehouse?`${x.parent_warehouse} / ${x.name}`:x.name,value:x.name}));}catch{warehouses.value=[];}}
const costCenters = ref([]);
async function fetchCostCenters(){try{const co=await resolveCompany();const r=await apiGET("frappe.client.get_list",{doctype:"Cost Center",fields:JSON.stringify(["name"]),filters:JSON.stringify([["disabled","=",0],["company","=",co],["is_group","=",0]]),order_by:"name asc",limit_page_length:100})||[];costCenters.value=r.map(c=>c.name);}catch{costCenters.value=[];}}

function todayStr() { return new Date().toISOString().slice(0, 10); }
function fmtCur(v) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 2 }).format(Math.abs(flt(v)));
}

async function load() {
  loading.value = true;
  try {
    list.value = await apiList("Purchase Invoice", {
      fields: ["name", "supplier", "supplier_name", "posting_date", "due_date", "bill_no", "grand_total", "outstanding_amount", "docstatus", "status"],
      filters: [["is_return", "=", 0]],
      limit: 500,
      order: "posting_date desc, creation desc",
    });
  } catch (e) { toast.error(e.message || "Failed to load bills"); }
  finally { loading.value = false; }
}
async function loadTaxAccount() {
  try {
    const r = await apiList("Account", { fields: ["name"], filters: [["account_type", "=", "Tax"], ["is_group", "=", 0]], limit: 1 });
    if (r?.length) taxAccountHead.value = r[0].name;
  } catch {}
  try {
    const templates = await apiList("Tax Template", { fields: ["name", "template_name", "tax_type"], filters: [["disabled", "=", 0]], limit: 100, order: "template_name asc" });
    const withRates = await Promise.all((templates || []).map(async t => {
      try {
        const doc = await apiGet("Tax Template", t.name);
        // Keep the full component rows so computeTaxRows can post to each row's
        // own (input-GST) account head, chosen by supplier place of supply.
        const rows = (doc?.taxes || []);
        const rate = rows.reduce((s, r) => s + (Number(r.rate) || 0), 0);
        const account = rows?.[0]?.account_head || taxAccountHead.value;
        return { name: t.name, template_name: t.template_name, tax_type: t.tax_type || doc?.tax_type || "GST", rate: Number(rate), account, taxes: rows };
      } catch { return { name: t.name, template_name: t.template_name, tax_type: t.tax_type || "GST", rate: 0, account: taxAccountHead.value, taxes: [] }; }
    }));
    taxTemplates.value = withRates;
  } catch { taxTemplates.value = []; }
  // Company GST state + Input GST accounts for intra/inter split (ITC side).
  try {
    const co = await resolveCompany();
    const bc = await apiGet("Books Company", co);
    companyGstState.value = bc?.gst_state || bc?.state || "";
    gstAccounts.value = await apiGET("zoho_books_clone.api.gst.get_gst_accounts", { company: co }) || {};
  } catch {}
}

// Shared context for the purchase-side split (supplier state vs company state).
function billTaxCtx() {
  return {
    companyState: companyGstState.value,
    placeOfSupply: supplierState.value,
    gst: { cgst: gstAccounts.value.input_cgst, sgst: gstAccounts.value.input_sgst, igst: gstAccounts.value.input_igst },
    defaultAccount: taxAccountHead.value,
  };
}

const counts = computed(() => ({
  draft:   list.value.filter(b => b.docstatus === 0).length,
  unpaid:  list.value.filter(b => b.docstatus === 1 && flt(b.outstanding_amount) > 0 && !isOverdue(b)).length,
  overdue: list.value.filter(b => isOverdue(b)).length,
  paid:    list.value.filter(b => b.docstatus === 1 && flt(b.outstanding_amount) <= 0).length,
}));
const summary = computed(() => ({
  totalUnpaid:   list.value.filter(b => b.docstatus === 1 && flt(b.outstanding_amount) > 0 && !isOverdue(b)).reduce((s, b) => s + flt(b.outstanding_amount), 0),
  overdueCount:  counts.value.overdue,
  totalDue:      list.value.filter(b => b.docstatus === 1).reduce((s, b) => s + flt(b.outstanding_amount), 0),
}));
const _bYM  = () => { const d=new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; };
const _bLYM = () => { const d=new Date(); d.setMonth(d.getMonth()-1); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; };
const _bTrend = (a,b) => { if(!b&&!a) return {pct:0,up:true}; if(!b) return {pct:100,up:true}; const p=Math.round((a-b)/b*100); return {pct:Math.abs(p),up:p>=0}; };
const billThisMonth = computed(()=>{ const ym=_bYM(); const r=list.value.filter(b=>(b.posting_date||'').startsWith(ym)); return {count:r.length,spend:r.reduce((s,b)=>s+flt(b.grand_total),0)}; });
const billAvg = computed(()=>{ const p=list.value.filter(b=>b.grand_total>0); return p.length?p.reduce((s,b)=>s+flt(b.grand_total),0)/p.length:0; });
const billTrends = computed(()=>({
  total:  _bTrend(billThisMonth.value.count, list.value.filter(b=>(b.posting_date||'').startsWith(_bLYM())).length),
  unpaid: _bTrend(counts.value.unpaid, list.value.filter(b=>(b.posting_date||'').startsWith(_bLYM())&&b.docstatus===1&&flt(b.outstanding_amount)>0&&!isOverdue(b)).length),
  overdue:_bTrend(counts.value.overdue, list.value.filter(b=>(b.posting_date||'').startsWith(_bLYM())&&isOverdue(b)).length),
  paid:   _bTrend(counts.value.paid, list.value.filter(b=>(b.posting_date||'').startsWith(_bLYM())&&b.docstatus===1&&flt(b.outstanding_amount)<=0).length),
}));

const filtered = computed(() => {
  let r = list.value;
  if (activeTab.value === "draft")   r = r.filter(b => b.docstatus === 0);
  if (activeTab.value === "unpaid")  r = r.filter(b => b.docstatus === 1 && flt(b.outstanding_amount) > 0 && !isOverdue(b));
  if (activeTab.value === "overdue") r = r.filter(b => isOverdue(b));
  if (activeTab.value === "paid")    r = r.filter(b => b.docstatus === 1 && flt(b.outstanding_amount) <= 0);
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    r = r.filter(x => (x.name || "").toLowerCase().includes(q)
      || (x.supplier_name || x.supplier || "").toLowerCase().includes(q)
      || (x.bill_no || "").toLowerCase().includes(q));
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
const { page, pageSize, paged } = usePagination(sorted, { storageKey: "bills" });
function sortBy(col) {
  if (sortCol.value === col) sortDir.value = sortDir.value === "asc" ? "desc" : "asc";
  else { sortCol.value = col; sortDir.value = "asc"; }
}
function sortArrow(col) {
  if (sortCol.value !== col) return '<span style="color:#d1d5db">⇅</span>';
  return sortDir.value === "asc" ? "↑" : "↓";
}

const allChecked = computed(() => sorted.value.length > 0 && sorted.value.every(b => selected.value.has(b.name)));
function toggle(n) { const s = new Set(selected.value); s.has(n) ? s.delete(n) : s.add(n); selected.value = s; }
function toggleAll(e) { selected.value = e.target.checked ? new Set(sorted.value.map(b => b.name)) : new Set(); }

// ── Timeline ──────────────────────────────────────────────────────────────
const timelineSteps = computed(() => {
  const b = viewDoc.value;
  if (!b) return [];
  if (b.docstatus === 2) {
    return [
      { key: "draft", label: "Draft", done: true },
      { key: "submitted", label: "Submitted", done: true },
      { key: "cancelled", label: "Cancelled", danger: true, current: true },
    ];
  }
  const paid = b.docstatus === 1 && flt(b.outstanding_amount) <= 0;
  const overdue = isOverdue(b);
  return [
    { key: "draft",     label: "Draft", done: true },
    { key: "submitted", label: "Submitted", done: b.docstatus >= 1, current: b.docstatus === 1 && !paid },
    { key: "paid",      label: overdue ? "Overdue" : "Paid", done: paid, danger: overdue && !paid, current: paid },
  ];
});


function openNew() {
  editingName.value = "";
  Object.assign(form, { supplier: "", posting_date: todayStr(), due_date: "", bill_no: "", bill_date: "", remarks: "", currency: "INR", exchange_rate: 1, update_stock: 1, set_warehouse: "", billing_address: "", billing_address_name: "", cost_center: "", tds_applicable: false, tds_section: "", tds_rate: 0 });
  vendorAddresses.value = [];
  lines.value = [blankLine()];
  Object.assign(billCollapsed, { details: false, billing: true, lines: false, remarks: true });
  fetchVendors(""); fetchItems(""); fetchWarehouses("");
  drawerOpen.value = true;
}
async function openEdit(b) {
  editingName.value = b.name;
  Object.assign(form, { supplier: b.supplier || "", posting_date: b.posting_date || todayStr(), due_date: b.due_date || "", bill_no: b.bill_no || "", bill_date: b.bill_date || "", remarks: b.remark || "", currency: "INR", exchange_rate: 1, update_stock: 1, set_warehouse: "", billing_address: "", billing_address_name: "", cost_center: "", tds_applicable: false, tds_section: "", tds_rate: 0 });
  vendorAddresses.value = [];
  lines.value = [blankLine()];
  fetchVendors(""); fetchItems(""); fetchWarehouses("");
  drawerOpen.value = true;
  try {
    const doc = await apiGet("Purchase Invoice", b.name);
    if (doc?.items?.length) {
      lines.value = doc.items.map(i => ({
        id: _id++, item_code: i.item_code || "", description: i.description || "",
        qty: i.qty || 1, rate: i.rate || 0, amount: i.amount || 0,
        tax_code: i.tax_code || "", collapsed: false,
        has_batch_no: 0, batch_no: i.batch_no || "", batchOptions: [],
      }));
      // Resolve has_batch_no per item so the Batch No field shows for
      // batch-tracked items already on this draft bill.
      const codes = [...new Set(lines.value.map(l => l.item_code).filter(Boolean))];
      if (codes.length) {
        try {
          const itemRows = await apiList("Item", { fields: ["name", "has_batch_no"], filters: [["name", "in", codes]], limit: codes.length });
          const flagMap = Object.fromEntries(itemRows.map(r => [r.name, r.has_batch_no ? 1 : 0]));
          lines.value.forEach(l => { l.has_batch_no = flagMap[l.item_code] || 0; if (l.has_batch_no) fetchBillLineBatches(l, ""); });
        } catch {}
      }
    }
    if (doc?.currency) form.currency = doc.currency;
    if (doc?.conversion_rate) form.exchange_rate = doc.conversion_rate;
    // Restore TDS from negative tax line
    const _TDS_RE = /tds|194[a-z]?|with.?hold|195/i;
    const tdsTax = (doc.taxes || []).find(t =>
      _TDS_RE.test(t.description || "") || _TDS_RE.test(t.tax_type || "") || Number(t.rate) < 0
    );
    if (tdsTax) {
      form.tds_applicable = true;
      const secMatch = (tdsTax.description || tdsTax.tax_type || "").match(/194[A-Z]?|192|195/i);
      form.tds_section = secMatch ? secMatch[0].toUpperCase() : (form.tds_section || "");
      form.tds_rate = Math.abs(Number(tdsTax.rate) || 0) || (TDS_RATES[form.tds_section] ?? 10);
    }
    if (doc?.remark) form.remarks = doc.remark;
    if (doc?.update_stock !== undefined) form.update_stock = doc.update_stock ? 1 : 0;
    if (doc?.set_warehouse) form.set_warehouse = doc.set_warehouse;
    if (doc?.billing_address) form.billing_address = doc.billing_address;
    if (doc?.cost_center) form.cost_center = doc.cost_center;
    // Load vendor addresses and restore selected dropdown
    if (b.supplier) {
      await fetchVendorAddresses(b.supplier);
      if (doc?.billing_address_name) {
        form.billing_address_name = doc.billing_address_name;
        const a = vendorAddresses.value.find(x => x.name === doc.billing_address_name);
        if (a) form.billing_address = formatAddress(a);
      }
    }
  } catch {}
}
const viewAddressCache = ref({});
const viewBillingAddr = computed(() =>
  viewDoc.value?.billing_address_name ? (viewAddressCache.value[viewDoc.value.billing_address_name] || null) : null
);

async function openView(b) {
  viewDoc.value = b;
  viewOpen.value = true;
  viewTab.value = "details";
  viewLoading.value = true;
  viewItems.value = [];
  viewPayments.value = [];
  viewTaxes.value = [];
  viewDebitApps.value = [];
  try {
    const [doc, payments, debitApps] = await Promise.all([
      apiGet("Purchase Invoice", b.name),
      b.docstatus === 1 ? apiGET("zoho_books_clone.api.docs.get_bill_payments", { bill_name: b.name }) : Promise.resolve([]),
      b.docstatus === 1 ? apiGET("zoho_books_clone.api.docs.get_bill_debit_applications", { bill_name: b.name }).catch(() => []) : Promise.resolve([]),
    ]);
    viewItems.value = doc?.items || [];
    viewTaxes.value = doc?.taxes || [];
    viewPayments.value = (payments || []).filter(p => p.docstatus === 1);
    viewDebitApps.value = debitApps || [];
    if (doc) viewDoc.value = { ...viewDoc.value,
      outstanding_amount: doc.outstanding_amount ?? viewDoc.value.outstanding_amount,
      grand_total: doc.grand_total ?? viewDoc.value.grand_total,
      docstatus: doc.docstatus ?? viewDoc.value.docstatus,
      status: doc.status ?? viewDoc.value.status,
      due_date: doc.due_date || viewDoc.value.due_date,
      cost_center: doc.cost_center, set_warehouse: doc.set_warehouse, billing_address: doc.billing_address,
      billing_address_name: doc.billing_address_name, remark: doc.remark || "" };
    // Resolve billing address object for card display
    if (doc?.billing_address_name && !viewAddressCache.value[doc.billing_address_name]) {
      apiGet("Address", doc.billing_address_name).then(a => { if (a) viewAddressCache.value = { ...viewAddressCache.value, [doc.billing_address_name]: a }; }).catch(() => {});
    }
  } catch (e) { /* keep dialog open */ }
  viewLoading.value = false;
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
    const r = await apiList("Item", { fields: ["name", "item_name", "description", "standard_rate", "standard_buying_rate", "stock_uom", "tax_code"], filters: [...f, ["has_variants", "=", 0]], limit: 30, order: "item_name asc" });
    items.value = r.map(x => ({ ...x, label: x.item_name || x.name, value: x.name, rate: x.standard_buying_rate || x.standard_rate || 0, description: x.description || "", tax_code: x.tax_code || "" }));
  } catch { items.value = []; }
}
watch(() => form.supplier, async (name) => {
  if (!name) { form.tds_applicable = false; form.tds_section = ""; form.tds_rate = 0; supplierState.value = ""; return; }
  try {
    const doc = await apiGET("zoho_books_clone.api.docs.get_doc", { doctype: "Supplier", name });
    supplierState.value = doc?.state || stateFromGstin(doc?.tax_id) || "";
    if (doc?.tds_applicable) {
      form.tds_applicable = true;
      form.tds_section = doc.tds_section || "";
      form.tds_rate = TDS_RATES[doc.tds_section] ?? 10;
    } else {
      form.tds_applicable = false; form.tds_section = ""; form.tds_rate = 0;
    }
  } catch {}
});

async function onVendorSelect(_opt) {
  form.billing_address = ""; form.billing_address_name = "";
  vendorAddresses.value = [];
  if (!form.supplier) return;
  await fetchVendorAddresses(form.supplier);
  // Auto-select first billing-type address if available
  const first = vendorAddresses.value.find(a => (a.address_type||"").toLowerCase() === "billing") || vendorAddresses.value[0];
  if (first) { form.billing_address_name = first.name; form.billing_address = formatAddress(first); }
}
async function onItemSelect(line, opt) {
  line.item_code = opt?.value ?? opt;
  if (opt?.rate !== undefined) { line.rate = Number(opt.rate) || 0; }
  if (opt?.item_name) { line.item_name = opt.item_name; }
  if (opt?.tax_code !== undefined) { line.tax_code = opt.tax_code || ""; }
  if (opt?.description) { line.description = opt.description; }
  else if (opt?.value) {
    // description not in option cache — fetch from Item doc directly
    try {
      const doc = await apiGet("Item", opt.value);
      if (doc?.description) line.description = doc.description;
      if (doc?.item_name) line.item_name = doc.item_name;
      if (doc?.tax_code) line.tax_code = doc.tax_code;
    } catch {}
  }
  // Resolve has_batch_no so the Batch No field shows up for batch-tracked
  // items when Update Inventory on Submit is on — mirrors PurchaseReceipts.vue.
  line.batch_no = ""; line.batchOptions = [];
  if (line.item_code) {
    try {
      line.has_batch_no = (await apiList("Item", { fields: ["has_batch_no"], filters: [["name", "=", line.item_code]], limit: 1 }))[0]?.has_batch_no ? 1 : 0;
    } catch { line.has_batch_no = 0; }
    if (line.has_batch_no) fetchBillLineBatches(line, "");
  } else {
    line.has_batch_no = 0;
  }
  calcLine(line);
}

// ── Batch helpers (mirrors PurchaseReceipts.vue / PurchaseOrders.vue convert-to-bill) ──
async function fetchBillLineBatches(line, q = "") {
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
function onBillLineBatchSelect(line, opt) { line.batch_no = opt?.value ?? opt; }
function onBillLineBatchCreate(line, val) { line.batch_no = val; }
function addLine() { lines.value.push(blankLine()); }
function removeLine(id) { if (lines.value.length > 1) lines.value = lines.value.filter(l => l.id !== id); }
function calcLine(l) { l.amount = Math.round(flt(l.qty) * flt(l.rate) * 100) / 100; }
const subtotal = computed(() => lines.value.reduce((s, l) => s + flt(l.amount), 0));

// Group tax by template name → { name, rate, amount }
const taxLines = computed(() =>
  computeTaxRows(lines.value, taxTemplates.value, billTaxCtx())
    .map(r => ({ template: r.description, description: r.description, tax_type: r.tax_type, rate: r.rate, account_head: r.account_head, amount: r.amount }))
);
const taxAmount = computed(() => taxLines.value.reduce((s, t) => s + t.amount, 0));
const grandTotal = computed(() => subtotal.value + taxAmount.value);
const tdsAmount = computed(() => form.tds_applicable && form.tds_rate > 0 ? Math.round(subtotal.value * form.tds_rate / 100 * 100) / 100 : 0);

// View drawer tax summary
const viewSubtotal = computed(() => viewItems.value.reduce((s, i) => s + flt(i.amount), 0));
// Show the *actual saved* tax lines, split into positive taxes (GST) and the
// negative TDS deduction — so the summary reconciles with the Grand Total
// instead of recomputing from items (which misses TDS and reads "No taxes").
const viewGstLines = computed(() =>
  (viewTaxes.value || [])
    .filter(t => flt(t.rate) >= 0 && flt(t.tax_amount) >= 0)
    .map(t => ({ template: t.description || t.tax_type || t.account_head || "Tax", rate: flt(t.rate), amount: flt(t.tax_amount) }))
);
const viewTdsLine = computed(() => {
  const t = (viewTaxes.value || []).find(x => flt(x.rate) < 0 || flt(x.tax_amount) < 0);
  return t ? { label: t.description || "TDS", rate: Math.abs(flt(t.rate)), amount: Math.abs(flt(t.tax_amount)) } : null;
});

async function copyLastItems() {
  if (!form.supplier) return;
  copyingLast.value = true;
  try {
    const r = await apiGET("zoho_books_clone.api.docs.get_party_last_items", { party_type: "Supplier", party: form.supplier, limit: 20 });
    if (r?.items?.length) {
      lines.value = r.items.map(it => ({
        id: _id++, item_code: it.item_code || "", description: it.description || it.item_name || "",
        qty: flt(it.qty) || 1, rate: flt(it.rate) || 0,
        amount: Math.round(flt(it.qty || 1) * flt(it.rate || 0) * 100) / 100,
        has_batch_no: 0, batch_no: "", batchOptions: [],
      }));
      const codes = [...new Set(lines.value.map(l => l.item_code).filter(Boolean))];
      if (codes.length) {
        try {
          const itemRows = await apiList("Item", { fields: ["name", "has_batch_no"], filters: [["name", "in", codes]], limit: codes.length });
          const flagMap = Object.fromEntries(itemRows.map(r2 => [r2.name, r2.has_batch_no ? 1 : 0]));
          lines.value.forEach(l => { l.has_batch_no = flagMap[l.item_code] || 0; if (l.has_batch_no) fetchBillLineBatches(l, ""); });
        } catch {}
      }
      toast.success(`Copied ${r.items.length} item(s) from ${r.source || "last bill"}`);
    } else { toast.info("No previous items found for this vendor"); }
  } catch (e) { toast.error("Failed to copy items"); }
  copyingLast.value = false;
}

async function saveBill(submit) {
  if (!form.supplier) return toast.error("Vendor is required");
  if (!lines.value.some(l => l.item_code && flt(l.qty) > 0)) return toast.error("At least one item required");
  if (form.update_stock && !form.set_warehouse) return toast.error("Receiving Warehouse is required when Update Inventory is on");

  // Batch-tracked items must carry a Batch No when Update Inventory on Submit
  // is on — that's what actually creates the incoming Stock Entry, and
  // StockEntry.validate() rejects batch-tracked rows with no batch_no.
  const activeLines = lines.value.filter(l => l.item_code && flt(l.qty) > 0);
  if (form.update_stock) {
    for (const l of activeLines) {
      if (!l.has_batch_no) continue;
      if (!l.batch_no) { toast.error(`${l.item_name || l.item_code} is batch-tracked — Batch No is required`); return; }
      const existing = await apiList("Batch", { fields: ["name", "disabled", "item"], filters: [["name", "=", l.batch_no]], limit: 1 }).catch(() => []);
      if (existing.length && existing[0].disabled) { toast.error(`Batch "${l.batch_no}" is disabled and can't be used.`); return; }
      if (existing.length && existing[0].item && existing[0].item !== l.item_code) {
        toast.error(`Batch "${l.batch_no}" already exists for item "${existing[0].item}", not "${l.item_code}".`); return;
      }
    }
  }

  drawerSaving.value = true;
  try {
    const company = await resolveCompany();
    // Split CGST/SGST/IGST (input) by supplier vs company state.
    const taxes = computeTaxRows(lines.value.filter(l => l.item_code), taxTemplates.value, billTaxCtx())
      .map(r => ({ doctype: "Tax Line", charge_type: "On Net Total", account_head: r.account_head, description: r.description, rate: r.rate, tax_type: r.tax_type, tax_amount: r.amount }));
    if (form.tds_applicable && form.tds_rate > 0 && form.tds_section) {
      taxes.push({
        doctype: "Tax Line", charge_type: "On Net Total",
        account_head: taxAccountHead.value || "TDS Payable",
        description: `TDS u/s ${form.tds_section}`,
        rate: -form.tds_rate,
      });
    }
    const doc = {
      doctype: "Purchase Invoice", company,
      supplier: form.supplier, posting_date: form.posting_date,
      due_date: form.due_date || null, bill_no: form.bill_no || "",
      bill_date: form.bill_date || null, remark: form.remarks || "",
      update_stock: form.update_stock ? 1 : 0, set_warehouse: form.set_warehouse || "",
      billing_address: form.billing_address || "",
      billing_address_name: form.billing_address_name || "",
      cost_center: form.cost_center || "",
      currency: form.currency || "INR",
      conversion_rate: form.currency === "INR" ? 1 : (form.exchange_rate || 1),
      items: activeLines.map(l => ({
        doctype: "Purchase Invoice Item", item_code: l.item_code,
        description: l.description || l.item_code,
        qty: flt(l.qty) || 1, rate: flt(l.rate), amount: flt(l.amount),
        tax_code: l.tax_code || "",
        batch_no: (form.update_stock && l.has_batch_no) ? l.batch_no : "",
      })),
      taxes,
    };
    if (editingName.value) doc.name = editingName.value;

    // Pre-create Batch records for batch-tracked lines so the auto-generated
    // Stock Entry can resolve batch_no as a valid Link on submit — mirrors
    // PurchaseReceipts.vue.
    if (form.update_stock) {
      for (const l of activeLines) {
        if (!l.has_batch_no || !l.batch_no) continue;
        const exists = await apiList("Batch", { fields: ["name"], filters: [["name", "=", l.batch_no]], limit: 1 });
        if (!exists.length) {
          await apiSave({
            doctype: "Batch", batch_no: l.batch_no, item: l.item_code,
            warehouse: form.set_warehouse || null, batch_qty: 0,
          });
        }
      }
    }

    const saved = await apiSave(doc);
    if (submit && saved?.name) await apiSubmit("Purchase Invoice", saved.name);
    toast.success(`Bill ${saved?.name || ""} ${submit ? "submitted" : "saved"}`);
    drawerOpen.value = false;
    await load();
    // Sync viewDoc from fresh list data so outstanding_amount/grand_total update
    if (saved?.name) {
      const fresh = list.value.find(x => x.name === saved.name);
      if (fresh) {
        if (viewDoc.value?.name === saved.name) viewDoc.value = { ...viewDoc.value, ...fresh };
        if (viewOpen.value && viewDoc.value?.name === saved.name) await openView(fresh);
      }
    }
  } catch (e) { toast.error(e.message || "Failed to save bill"); }
  finally { drawerSaving.value = false; }
}

// ── Actions ───────────────────────────────────────────────────────────────
async function emailBill(b) {
  await openEmail({
    doctype: "Purchase Invoice", name: b.name,
    docLabel: `Bill ${b.name}`,
    getDefaultsEndpoint: "zoho_books_clone.api.docs.get_bill_email_defaults",
    sendEndpoint: "zoho_books_clone.api.docs.send_bill_email",
    paramKey: "bill_name",
    printConfig: { title: "BILL", partyLabel: "Vendor", partyField: "supplier_name" },
  });
}
async function payBill(b) {
  if (!canWrite("bills")) { toast("Read-only access", "error"); return; }
  const paid = await openPayment({
    direction: "pay", doctype: "Purchase Invoice", name: b.name,
    party: b.supplier, partyLabel: b.supplier_name || b.supplier,
    balance: flt(b.outstanding_amount),
    getDefaultsEndpoint: "zoho_books_clone.api.docs.get_bill_payment_defaults",
    sendEndpoint: "zoho_books_clone.api.docs.record_vendor_payment",
    paramKey: "bill_name",
  });
  if (paid) { await load(); if (viewDoc.value?.name === b.name) await openView(b); }
}
async function issueDebitNote(b) {
  // Pre-fill items from the bill
  let billItems = viewItems.value;
  if (!billItems.length) {
    try { const doc = await apiGet("Purchase Invoice", b.name); billItems = doc?.items || []; }
    catch { billItems = []; }
  }
  const result = await openReturnNote({
    kind: "debit", parentName: b.name, party: b.supplier,
    maxInvoiceAmt: flt(b.outstanding_amount),
    items: billItems.map(i => ({ item_code: i.item_code, item_name: i.item_name, description: i.description, qty: i.qty, rate: i.rate })),
    existingEndpoint: "zoho_books_clone.api.docs.get_debit_notes",
    createEndpoint: "zoho_books_clone.api.docs.create_debit_note",
    paramKey: "bill_name",
    partyKey: "vendor",
    parentKey: "against_bill",
  });
  if (result) { await load(); if (viewDoc.value?.name === b.name) await openView(b); }
}

async function makeRecurringBill(b) {
  const { openMakeRecurring } = useMakeRecurring();
  const subName = await openMakeRecurring({
    doctype: "Purchase Invoice",
    name: b.name,
    partyLabel: b.supplier_name || b.supplier || "",
    amount: b.grand_total || 0,
  });
  if (subName) toast(`Recurring subscription ${subName} created`);
}

async function submitBill(b) {
  if (!await confirm({ title: "Submit Bill", body: `Submit ${b.name}? This will post it to the ledger and it can no longer be edited.`, okLabel: "Submit Bill" })) return;
  try {
    const submitted = await apiSubmit("Purchase Invoice", b.name);
    toast.success("Bill submitted");
    await load();
    await openView({ name: b.name });
  } catch (e) { if (e.message !== "Submission cancelled by user") toast.error(e.message || "Submit failed"); }
}
async function cancelBill(b) {
  let payments = [];
  try { payments = await apiGET("zoho_books_clone.api.docs.get_bill_payments", { bill_name: b.name }) || []; } catch {}
  const submittedPays = payments.filter(p => p.docstatus === 1);
  if (submittedPays.length) {
    const ok = await confirmCascade({
      title: "Cancel Bill & Payments",
      message: `${b.name} has ${submittedPays.length} linked payment(s). Both must be cancelled together.`,
      actionLabel: "Cancel Both",
      links: submittedPays.map(p => ({ name: p.name, mode: p.mode_of_payment, date: p.payment_date, amount: p.paid_amount })),
    });
    if (!ok) return;
    try {
      await apiPOST("zoho_books_clone.api.docs.cancel_bill_with_payments", { bill_name: b.name });
      toast.success("Bill and payment(s) cancelled");
      await load(); if (viewDoc.value?.name === b.name) await openView(b);
    } catch (e) { toast.error(e.message || "Cancel failed"); }
  } else {
    if (!await confirm({ title: "Cancel Bill", body: `Cancel ${b.name}? This cannot be undone.`, okLabel: "Cancel Bill" })) return;
    try {
      await apiPOST("zoho_books_clone.api.docs.cancel_doc", { doctype: "Purchase Invoice", name: b.name });
      toast.success("Bill cancelled");
      await load(); if (viewDoc.value?.name === b.name) await openView(b);
    } catch (e) { toast.error(e.message || "Cancel failed"); }
  }
}
async function deleteBill(b) {
  if (!canWrite("bills")) { toast("Read-only access", "error"); return; }
  if (!await confirm({ title: "Delete Bill", body: `Permanently delete ${b.name}? This cannot be undone.`, okLabel: "Delete" })) return;
  try {
    await apiDelete("Purchase Invoice", b.name);
    toast.success("Bill deleted");
    viewOpen.value = false; await load();
  } catch (e) { toast.error(e.message || "Delete failed"); }
}

// ── Bulk actions ──────────────────────────────────────────────────────────
async function bulkDelete() {
  if (!canWrite("bills")) { toast("Read-only access", "error"); return; }
  const drafts = sorted.value.filter(b => selected.value.has(b.name) && b.docstatus === 0);
  if (!drafts.length) { toast.info("No draft bills selected"); return; }
  if (!await confirm({ title: "Delete Drafts", body: `Delete ${drafts.length} draft bill(s)?`, okLabel: "Delete" })) return;
  for (const b of drafts) { try { await apiDelete("Purchase Invoice", b.name); } catch {} }
  selected.value = new Set();
  toast.success(`Deleted ${drafts.length} draft bill(s)`);
  await load();
}
async function bulkCancel() {
  if (!canWrite("bills")) { toast("Read-only access", "error"); return; }
  const submitted = sorted.value.filter(b => selected.value.has(b.name) && b.docstatus === 1);
  if (!submitted.length) { toast.info("No submitted bills selected"); return; }
  let done = 0, failed = 0;
  for (const b of submitted) {
    try { await apiPOST("zoho_books_clone.api.docs.cancel_bill_with_payments", { bill_name: b.name }); done++; }
    catch (e) { failed++; }
  }
  selected.value = new Set();
  toast.success(`Cancelled ${done} bill(s)${failed ? `; ${failed} failed` : ""}`);
  await load();
}
async function bulkEmail() {
  if (!canWrite("bills")) { toast("Read-only access", "error"); return; }
  const subs = sorted.value.filter(b => selected.value.has(b.name) && b.docstatus === 1);
  if (!subs.length) { toast.info("No submitted bills selected"); return; }
  let sent = 0;
  for (const b of subs) {
    const ok = await openEmail({
      doctype: "Purchase Invoice", name: b.name, docLabel: `Bill ${b.name}`,
      getDefaultsEndpoint: "zoho_books_clone.api.docs.get_bill_email_defaults",
      sendEndpoint: "zoho_books_clone.api.docs.send_bill_email",
      paramKey: "bill_name",
      printConfig: { title: "BILL", partyLabel: "Vendor", partyField: "supplier_name" },
    });
    if (ok) sent++;
  }
  if (sent) toast.success(`Emailed ${sent} bill(s)`);
}

function exportCSV() {
  const rows = selected.value.size
    ? sorted.value.filter(b => selected.value.has(b.name))
    : sorted.value;
  if (!rows.length) return;
  const head = ["Bill #","Vendor","Vendor Bill #","Date","Due Date","Status","Amount","Balance"];
  const esc = v => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const lines = [head.map(esc).join(",")];
  for (const b of rows) {
    lines.push([b.name, b.supplier_name || b.supplier, b.bill_no || "", b.posting_date || "", b.due_date || "",
      statusLabel(b), Number(b.grand_total || 0).toFixed(2), Number(b.outstanding_amount || 0).toFixed(2)
    ].map(esc).join(","));
  }
  const blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `bills_${todayStr()}.csv`;
  a.click(); URL.revokeObjectURL(url);
  toast.success(`CSV exported — ${rows.length} bill(s)`);
}

onMounted(async () => {
  setCompany(window.__booksCompany || "");
  document.addEventListener('click', onDocClickForDownloadMenu);
  await load();
  loadTaxAccount(); fetchCostCenters();
  // Cross-document deep link: /purchases?open=PINV-...
  useOpenFromQuery({ route, openByName: (n) => openView(list.value.find(x => x.name === n) || { name: n }) });
});
onUnmounted(() => document.removeEventListener('click', onDocClickForDownloadMenu));
</script>

<style scoped>
@import '../styles/list.css';
@import '../styles/view.css';
@import '../styles/edit.css';
@import '../styles/add.css';

/* ── Download dropdown menu ── */
.inv-dl-menu {
  position: absolute;
  top: calc(100% + 6px);
  left:0;
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

/* ── Edit drawer ── */
.bill-edit-drawer { width: 720px;right: -720px;max-width: 96vw; transition: right .22s ease; position: fixed; top: 0; bottom: 0; max-width: 96vw; z-index: 8100; background: #fff; display: flex; flex-direction: column; }
.bill-edit-drawer.open { right: 0; }

/* ── View drawer ── */
.bill-view-drawer { width: 900px; right: -900px; transition: right .22s ease; position: fixed; top: 0; bottom: 0; background: #f5f6f8; display: flex; flex-direction: column; overflow-y: auto; }
.bill-view-drawer.open { right: 0; }

/* ── View page header ── */
.bill-view-page-header {
  padding: 16px 20px 10px;
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
}
.inv-view-header-left { flex: 1; min-width: 0; }
.inv-view-title-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 4px; }
.inv-view-number { font-size: 18px; font-weight: 800; color: #1a1a2e; }
.inv-view-subtitle { font-size: 13px; color: #6b7280; }
.inv-hdr-badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; letter-spacing: .04em; }

/* ── View CTA button ── */
.inv-view-cta { display: inline-flex; align-items: center; gap: 6px; background: #1a6ef7; color: #fff; border: none; border-radius: 7px; padding: 8px 16px; font-size: 13px; font-weight: 700; cursor: pointer; white-space: nowrap; }
.inv-view-cta:hover { background: #155fd4; }

/* ── inv-view-body wraps everything below header ── */
.inv-view-body { margin: 12px 16px 16px; background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; overflow: scroll; }

/* ── Status timeline wrapper ── */
.inv-tl-wrap { border-bottom: 1px solid #f0f2f5; }

/* ── Action button bar ── */
.inv-action-bar { display: flex; align-items: center; gap: 6px; padding: 12px 16px; flex-wrap: wrap; border-bottom: 1px solid #f0f2f5; background: #fafafa; }
.inv-ab-btn { display: inline-flex; align-items: center; gap: 5px; background: #fff; border: 1px solid #e5e7eb; border-radius: 6px; padding: 6px 12px; font-size: 12.5px; font-weight: 600; color: #374151; cursor: pointer; white-space: nowrap; font-family: inherit; }
.inv-ab-btn:hover { border-color: #94a3b8; background: #f8fafc; }
.inv-ab-danger { color: #dc2626; border-color: #fca5a5; }
.inv-ab-danger:hover { background: #fee2e2; border-color: #dc2626; }
.ab-label { display: inline; }

/* ── Tabs ── */
.inv-view-tabs { display: flex; gap: 2px; padding: 0 16px; border-bottom: 1px solid #e5e7eb; background: #fff; }
.inv-vtab { background: none; border: none; border-bottom: 2px solid transparent; padding: 10px 14px; font-size: 13px; font-weight: 600; color: #6b7280; cursor: pointer; font-family: inherit; }
.inv-vtab.active { color: #1a6ef7; border-bottom-color: #1a6ef7; }
.inv-vtab-count { background: #eff6ff; color: #1a6ef7; border-radius: 10px; padding: 1px 7px; font-size: 11px; margin-left: 4px; }

/* ── Tab body ── */
.inv-tab-body { padding: 16px; }

/* ── Details meta row ── */
.inv-details-meta { display: grid; gap: 0; border-bottom: 1px solid #f0f2f5; }
.inv-details-meta-col { padding: 16px; border-right: 1px solid #f0f2f5; }
.inv-details-meta-col:last-child { border-right: none; }
.inv-dmeta-icon-row { display: flex; align-items: center; gap: 5px; margin-bottom: 4px; }
.inv-dmeta-icon { color: #9ca3af; }
.inv-dmeta-lbl { font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: #9ca3af; }
.inv-dmeta-primary { font-size: 14px; font-weight: 700; color: #111827; margin-bottom: 2px; }
.inv-dmeta-secondary { font-size: 12px; color: #6b7280; }
.inv-dmeta-date-val { font-size: 14px; font-weight: 600; color: #111827; }
.inv-dmeta-date-val.is-overdue { color: #dc2626; }
.inv-balance-val { font-size: 20px; font-weight: 800; color: #dc2626; }
.inv-balance-val.is-zero, .inv-balance-val.is-paid { color: #16a34a; }
.inv-rec-pay-btn { margin-top: 8px; background: #1a6ef7; color: #fff; border: none; border-radius: 6px; padding: 5px 12px; font-size: 12px; font-weight: 600; cursor: pointer; font-family: inherit; }
.inv-rec-pay-btn:hover { background: #155fd4; }

/* ── Line items table ── */
.inv-items-wrap { margin-top: 16px; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; }
.inv-items-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.inv-items-table th { padding: 9px 12px; background: #f8fafc; border-bottom: 1px solid #e5e7eb; font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; color: #9ca3af; text-align: left; }
.inv-items-table td { padding: 10px 12px; border-bottom: 1px solid #f0f2f5; }
.inv-items-table tbody tr:last-child td { border-bottom: none; }
.th-r { text-align: right; }
.td-r { text-align: right; }
.inv-item-num { color: #9ca3af; font-size: 12px; text-align: center; }
.inv-item-name { font-weight: 600; color: #111827; }
.inv-item-desc { font-size: 11.5px; color: #6b7280; margin-top: 2px; }

/* ── Totals section (view) ── */
.inv-totals-section { border-top: 1px solid #e5e7eb; background: #f8fafc; padding: 12px 16px; display: flex; justify-content: flex-end; }
.inv-totals-inner { min-width: 240px; display: flex; flex-direction: column; gap: 5px; }
.inv-total-line { display: flex; justify-content: space-between; align-items: center; font-size: 13px; color: #374151; padding: 2px 0; }
.t-lbl { color: #6b7280; }
.t-amt { font-weight: 600; }
.inv-grand-total-line { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #e5e7eb; padding-top: 8px; margin-top: 4px; }
.inv-grand-lbl { font-size: 14px; font-weight: 700; color: #111827; }
.inv-grand-amt { font-size: 18px; font-weight: 800; color: #1a6ef7; }

/* ── Edit drawer: add-card styles ── */
.add-card { border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden; margin-bottom: 12px; background: #fff; }
.add-card-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; cursor: pointer; user-select: none; background: #f8fafc; }
.add-card-header:hover { background: #f1f4f8; }
.add-card-title { display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 700; color: #374151; }
.add-card-title-icon { width: 28px; height: 28px; border-radius: 7px; background: #dbeafe; color: #2563eb; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.add-card-chevron { color: #9ca3af; display: flex; transition: transform .2s; }
.add-card-chevron.collapsed { transform: rotate(-90deg); }
.add-card-body { padding: 16px; transition: all .18s ease; }
.add-card-body.collapsed { display: none; }
.add-details-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.add-line-num { display: inline-block; width: 20px; text-align: center; color: #9ca3af; font-size: 12px; }
.add-line-amount { text-align: right; font-size: 12.5px; font-weight: 600; padding: 4px 8px; color: #374151; }
.add-line-del { background: none; border: 1px solid rgba(220,38,38,.3); border-radius: 4px; padding: 3px 5px; cursor: pointer; color: #dc2626; display: inline-flex; align-items: center; }
.add-new-line-row { }
.add-new-line-btn { display: inline-flex; align-items: center; gap: 5px; background: none; border: none; color: #1a6ef7; font-size: 12.5px; font-weight: 600; cursor: pointer; padding: 4px 0; }
.add-new-line-btn:hover { text-decoration: underline; }
.add-lines-add-btn { display: inline-flex; align-items: center; gap: 4px; background: #eaf1ff; border: 1px solid rgba(26,110,247,.3); color: #1a6ef7; border-radius: 6px; padding: 4px 10px; font-size: 12px; font-weight: 600; cursor: pointer; }
.add-status-badge { display: inline-block; background: #f1f5f9; color: #475569; border-radius: 6px; padding: 2px 10px; font-size: 12px; font-weight: 600; }

/* ── Footer ── */
.add-footer-status { font-size: 12px; color: #9ca3af; }
.add-footer-actions { display: flex; gap: 8px; align-items: center; }
.add-btn-cancel { background: none; border: 1px solid #e5e7eb; border-radius: 7px; padding: 8px 14px; font-size: 13px; font-weight: 600; color: #6b7280; cursor: pointer; font-family: inherit; }
.add-btn-cancel:hover { border-color: #94a3b8; }

.add-btn-submit { display: inline-flex; align-items: center; gap: 5px; background: #1a6ef7; color: #fff; border: none; border-radius: 7px; padding: 8px 16px; font-size: 13px; font-weight: 700; cursor: pointer; font-family: inherit; }
.add-btn-submit:hover { background: #155fd4; }
.add-btn-submit:disabled { opacity: .5; cursor: not-allowed; }

/* ── Address dropdown + card ── */
.po-addr-select { appearance: none; padding-right: 28px; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%239ca3af' stroke-width='2.5'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E"); background-repeat: no-repeat; background-position: right 10px center; }
.po-addr-card { margin-top: 8px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; display: flex; flex-direction: column; gap: 5px; }
.po-addr-card-type { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: #2563eb; background: #dbeafe; display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 10px; align-self: flex-start; }
.po-addr-card-text { font-size: 12.5px; color: #374151; line-height: 1.65; }
/* ── Add New Address modal ── */
.po-apply-dialog { position: fixed; top: 50%; left: 50%; transform: translate(-50%,-50%); width: 520px; max-width: 96vw; background: #fff; border-radius: 12px; box-shadow: 0 12px 40px rgba(0,0,0,.2); z-index: 8100; display: flex; flex-direction: column; overflow: hidden; }

.bill-act-cell { display:flex; align-items:center; gap:6px; justify-content:flex-end; }

/* ── PO-style item cards (Bills edit drawer) ── */
.po-item-cards { display: flex; flex-direction: column; gap: 12px; }
.po-item-card { background: #fff; border: 1px solid #dde3f0; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(99,102,241,.07); }
.po-item-card-header { display: flex; align-items: center; gap: 10px; padding: 12px 16px; background: linear-gradient(135deg,#eef2ff 0%,#f5f7ff 100%); border-bottom: 1px solid #dde3f0; }
.po-item-card-num { font-size: 11px; font-weight: 800; color: #4f46e5; background: #e0e7ff; border-radius: 5px; padding: 3px 8px; letter-spacing:.02em; flex-shrink:0; }
.po-item-card-title { font-size: 15px; font-weight: 700; color: #1e40af; flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.po-item-card-subtotal { display: flex; flex-direction: column; align-items: flex-end; flex-shrink:0; }
.po-item-card-subtotal-label { font-size: 9.5px; font-weight: 700; color: #9ca3af; letter-spacing: .08em; }
.po-item-card-amount { font-size: 20px; font-weight: 800; color: #111827; font-variant-numeric: tabular-nums; line-height: 1.1; }
.po-item-card-chevron { display:flex; align-items:center; color:#9ca3af; transition:transform .2s; margin-left:4px; flex-shrink:0; }
.po-item-card-chevron.collapsed { transform:rotate(-90deg); }
.po-item-card-rm { background: none; border: none; cursor: pointer; color: #9ca3af; padding: 6px; border-radius: 6px; display: flex; align-items: center; margin-left: 8px; flex-shrink:0; }
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
.po-item-count { font-size: 11px; font-weight: 600; background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; border-radius: 12px; padding: 1px 8px; margin-left: 4px; }
.po-totals { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-top: 16px; }
.po-totals-right { display: flex; flex-direction: column; gap: 4px; min-width: 220px; }
.po-total-row { display: flex; justify-content: space-between; gap: 16px; font-size: 13px; color: #374151; padding: 3px 0; }
.po-total-row.grand { font-weight: 700; font-size: 14px; color: #111827; border-top: 1px solid #e5e7eb; padding-top: 6px; }
.exp-field-hint { font-size:11.5px; color:#9ca3af; margin-top:4px; text-align:right; }

/* ── Bill line item card body — single-column stacked layout ── */
.bill-item-body { display: flex; flex-direction: column; }
.bill-item-row { display: flex; gap: 12px; padding: 14px 16px 0; }
.bill-item-grow { flex: 1; min-width: 0; }
.bill-item-tax { flex: 0 0 160px; min-width: 0; }
.bill-item-num { flex: 1; min-width: 0; }
.bill-item-desc { padding: 14px 16px 16px; }

/* ── Tax badges (view drawer) ── */
.vi-tax-badge { font-size:9px; font-weight:800; letter-spacing:.06em; padding:2px 6px; border-radius:4px; background:#e0e7ff; color:#4f46e5; white-space:nowrap; }
.vi-notax-badge { font-size:9px; font-weight:800; letter-spacing:.06em; padding:2px 6px; border-radius:4px; background:#f3f4f6; color:#9ca3af; }

/* ── Line item cards (view drawer) ── */
.inv-sec-lbl { font-size:10.5px; font-weight:700; letter-spacing:.6px; text-transform:uppercase; color:#9ca3af; margin-bottom:8px; margin-top:4px; padding-top:16px; border-top:1px solid #f0f2f5; }
.inv-sec-lbl:first-child { border-top:none; padding-top:0; margin-top:0; }
.vi-line-cards { display:flex; flex-direction:column; gap:10px; }
.vi-line-card { background:#fff; border:1px solid #e2e8f0; border-radius:10px; overflow:hidden; }
.vi-line-card-header { display:flex; align-items:center; gap:10px; padding:11px 16px; background:linear-gradient(135deg,#f0f4ff 0%,#f8fafc 100%); border-bottom:1px solid #e8edf5; }
.vi-line-num { font-size:10.5px; font-weight:800; color:#4f46e5; background:#e0e7ff; border-radius:5px; padding:2px 7px; letter-spacing:.02em; flex-shrink:0; }
.vi-line-name { font-size:14px; font-weight:700; color:#1e293b; flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.vi-line-amount { font-size:16px; font-weight:800; color:#111827; font-variant-numeric:tabular-nums; flex-shrink:0; }
.vi-line-desc { padding:8px 16px; font-size:12px; color:#6b7280; line-height:1.55; border-bottom:1px solid #f0f2f5; background:#fafbfc; word-break:break-word; overflow-wrap:anywhere; }
.vi-line-meta { display:flex; align-items:center; gap:12px; padding:10px 16px; flex-wrap:wrap; }
.vi-line-meta-item { display:flex; flex-direction:column; gap:2px; }
.vi-meta-lbl { font-size:9.5px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:#9ca3af; }
.vi-meta-val { font-size:13px; font-weight:600; color:#1e293b; }
.vi-line-tax { margin-left:auto; flex-direction:row; align-items:center; gap:6px; }

/* ── Totals block (view drawer) ── */
.po-view-totals { margin-top:16px; border-top:1px solid #e5e7eb; padding-top:12px; display:flex; justify-content:flex-end; }
.po-view-totals-inner { min-width:240px; display:flex; flex-direction:column; gap:6px; }
.po-view-total-row { display:flex; justify-content:space-between; align-items:center; font-size:13px; color:#374151; }
.po-view-tax-row { color:#6b7280; }
.po-view-tax-label { display:flex; align-items:center; gap:6px; }
.po-view-tax-badge { font-size:9px; font-weight:800; letter-spacing:.06em; padding:2px 6px; border-radius:4px; background:#e0e7ff; color:#4f46e5; flex-shrink:0; }
.po-view-tax-badge--none { background:#f3f4f6; color:#9ca3af; }
.po-view-tax-rate { font-size:11px; color:#9ca3af; }
.po-view-grand { font-size:15px; font-weight:800; color:#111827; border-top:1px solid #e5e7eb; padding-top:8px; margin-top:4px; }
.po-view-grand span:last-child { color:#1a6ef7; }

/* ══════════════════════════════════════════════════
   RESPONSIVE MEDIA QUERIES
   ══════════════════════════════════════════════════ */

/* ── Small desktop (≤ 1024px) ── */
@media (max-width: 1024px) {
  .bill-edit-drawer { width: 660px; right: -660px; }
  .bill-view-drawer { width: 780px; right: -780px; }

  .bk-kpi-grid  { grid-template-columns: repeat(3, 1fr); }
  .bk-stat-grid { grid-template-columns: repeat(2, 1fr); }
}

/* ── Tablet (≤ 768px) ── */
@media (max-width: 768px) {
  /* Drawers go full-screen */
  .bill-edit-drawer { width: 100% !important; right: -100% !important; max-width: 100%; }
  .bill-view-drawer { width: 100% !important; right: -100% !important; max-width: 100%; }
  /* .open must override right: -100% !important */
  .bill-edit-drawer.open,
  .bill-view-drawer.open { right: 0 !important; }

  /* KPI / stat grids */
  .bk-kpi-grid  { grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .bk-stat-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }

  /* Toolbar: wrap search + pills + buttons */
  .sales-toolbar { flex-wrap: wrap; gap: 8px; }

  /* View page header: keep title + buttons on one row */
  .bill-view-page-header { padding: 12px 14px 8px; gap: 8px; flex-wrap: nowrap; align-items: center; }
  .inv-view-header-left { flex: 1 1 auto; min-width: 0; overflow: hidden; }
  .inv-view-number { font-size: 15px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
  .inv-view-title-row { flex-wrap: nowrap; gap: 6px; }
  .inv-hdr-badge { flex-shrink: 0; }
  .bill-view-cta-wrap { flex-shrink: 0; }

  /* Details meta: 2-col (overrides inline grid-template-columns:repeat(3,1fr)) */
  .inv-details-meta { grid-template-columns: repeat(2, 1fr) !important; }
  .inv-details-meta-col { border-right: none; border-bottom: 1px solid #f0f2f5; padding: 12px; }
  .inv-details-meta-col:last-child { border-bottom: none; }

  /* Action bar */
  .inv-action-bar { padding: 8px 12px; gap: 5px; }
  .inv-ab-btn { padding: 5px 10px; font-size: 12px; }

  /* Totals block: stack */
  .po-totals { flex-direction: column; gap: 12px; }
  .po-totals-right { min-width: unset; width: 100%; }

  /* Totals panel (view) */
  .po-view-totals { justify-content: stretch; }
  .po-view-totals-inner { min-width: unset; width: 100%; }

  /* Address modal */
  .po-apply-dialog { width: 96vw; }

  /* Main list table: hide Due Date and Balance columns on tablet */
  .inv-table th:nth-child(5),
  .inv-table td:nth-child(5),
  .inv-table th:nth-child(8),
  .inv-table td:nth-child(8) { display: none; }
}

/* ── Mobile (≤ 480px) ── */
@media (max-width: 480px) {
  /* KPI + stat grids: single column */
  .bk-kpi-grid  { grid-template-columns: 1fr; }
  .bk-stat-grid { grid-template-columns: 1fr; }
  .inv-view-cta{display:none;}
  /* Details meta: single column */
  .inv-details-meta { grid-template-columns: 1fr !important; }

  /* Item card body stacks to single column */
  .po-item-card-body { grid-template-columns: 1fr; }
  .po-item-col--left { border-right: none; border-bottom: 1px solid #f0f2f8; }

  /* Numeric row in item card */
  .po-item-num-row { grid-template-columns: 1fr; }

  /* Additional details grid */
  .add-details-grid { grid-template-columns: 1fr; }

  /* Edit drawer footer buttons */
  .add-footer-actions { flex-wrap: wrap; width: 100%; }
  .add-btn-cancel,
  .add-btn-draft,
  .add-btn-more,
  .add-btn-submit { flex: 1 1 auto; justify-content: center; text-align: center; }

  /* Main list table: hide Date + Balance + Actions (keep Bill#, Vendor, Status, Amount) */
  .inv-table th:nth-child(4),
  .inv-table td:nth-child(4),
  .inv-table th:nth-child(5),
  .inv-table td:nth-child(5),
  .inv-table th:nth-child(8),
  .inv-table td:nth-child(8),
  .inv-table th:nth-child(9),
  .inv-table td:nth-child(9) { display: none; }


  /* Action bar buttons smaller */
  .inv-action-bar { gap: 4px; padding: 6px 10px; }
  .inv-ab-btn     { padding: 5px 8px; font-size: 11.5px; }
  .ab-label       { display: none; }

  /* Tabs */
  .inv-vtab { padding: 9px 12px; font-size: 12.5px; }

  /* Address modal */
  .po-apply-dialog { width: 98vw; height: 450px; border-radius: 8px; }

}


/* ── Mobile card view (Option A) ── */
.bil-mobile-cards { display: none; }
.bil-desktop-table { display: table; }

@media (max-width: 768px) {
  .bil-desktop-table { display: none !important; }
  .bil-mobile-cards { display: flex; flex-direction: column; gap: 0; background: #f8fafc; }
  .bil-mobile-card { background: #fff; border-bottom: 1px solid #e5e7eb; padding: 12px 14px; cursor: pointer; transition: background .12s; }
  .bil-mobile-card:active { background: #f8f9fc; }
  .bil-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .bil-mc-docno { font-size: 12px; font-weight: 700; color: #2563eb; }
  .bil-mc-mid { font-size: 13.5px; font-weight: 600; color: #1a1d23; margin-bottom: 4px; }
  .bil-mc-meta { display: flex; justify-content: space-between; font-size: 12px; color: #868e96; margin-bottom: 4px; }
  .bil-mc-amount { font-weight: 700; color: #1a1d23; }
  .bil-mc-balance { font-size: 11.5px; color: #868e96; margin-bottom: 8px; }
  .bil-mc-footer { display: flex; gap: 6px; margin-top: 8px; }
  .bil-mc-btn { flex: 1; padding: 6px 10px; border-radius: 7px; font-size: 12px; font-weight: 600; cursor: pointer; background: #f1f5f9; border: 1px solid #e2e8f0; color: #374151; }
  .bil-mc-pay { background: #eff6ff; border-color: #bfdbfe; color: #2563eb; }
  .bil-mc-danger { background: #fff1f2; border-color: #fecaca; color: #dc2626; }
  .bil-mc--skeleton { pointer-events: none; }
  .bil-mc-shimmer { border-radius: 6px; background: linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size: 200% 100%; animation: bil-shimmer 1.4s infinite; }
  @keyframes bil-shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
  .bil-mc-empty { text-align: center; padding: 32px 16px; color: #868e96; font-size: 13px; }
}

/* ── Payments tab section labels ─────────────────────────────────── */
.inv-pay-section-lbl { font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: #6b7280; padding: 10px 12px 6px; }
.inv-pay-section-lbl-dn { color: #7c3aed; }

/* ── Debit note badges ────────────────────────────────────────────── */
.bil-dn-badge { display: inline-block; padding: 2px 9px; border-radius: 12px; font-size: 11px; font-weight: 700; letter-spacing: .03em; }
.bil-dn-badge-direct  { background: #f3e8ff; color: #7c3aed; }
.bil-dn-badge-applied { background: #ede9fe; color: #6d28d9; }

/* ── Payments table shared ────────────────────────────────────────── */
.inv-payments-tbl th { padding: 9px 12px; background: #f8fafc; border-bottom: 1px solid #e5e7eb; font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; color: #9ca3af; text-align: left; }
.inv-payments-tbl td { padding: 10px 12px; border-bottom: 1px solid #f0f2f5; font-size: 13px; }
.th-r { text-align: right !important; }
.td-r { text-align: right; }

/* ── Payments tab: mobile card view ──────────────────────────────── */
.bil-pay-mobile-cards { display: none; }

@media (max-width: 768px) {
  .bil-pay-desktop-table { display: none !important; }
  .bil-pay-mobile-cards { display: flex; flex-direction: column; gap: 8px; padding: 2px 0; }
  .bil-pay-mc {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 12px 14px;
  }
  .bil-pay-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
  .bil-pay-mc-date { font-size: 13px; font-weight: 600; color: #1a1d23; }
  .bil-pay-mc-amount { font-size: 14px; font-weight: 700; color: #059669; }
  .bil-pay-mc-bottom { display: flex; align-items: center; justify-content: space-between; }
  .bil-pay-mc-mode {
    font-size: 11.5px; font-weight: 600; color: #2563eb;
    background: #eff6ff; border: 1px solid #bfdbfe;
    border-radius: 5px; padding: 2px 8px;
  }
  .bil-pay-mc-ref { font-size: 11.5px; color: #868e96; }
}

/* ── View drawer header: keep buttons on one row ──────────────────── */
.bill-view-cta-wrap { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }

/* ── Mobile card layout (≤ 425px) ────────────────────────────────── */
@media (max-width: 425px) {
  /* Suppress "Date:" prefix that Invoices.vue global CSS injects on td:nth-child(2)
     Specificity: 0-4-1 in scoped context beats 0-2-2 + !important global rule */
  .inv-table tbody .inv-row .td-id::before {
    content: none !important;
    display: none !important;
    font-size: 0 !important;
  }

  /* Style overrides for named cells */
  .td-id { padding: 0 14px 4px !important; cursor: pointer !important; }
  .td-id .inv-link {
    font-size: 12px !important;
    font-weight: 600 !important;
    color: #1a6ef7 !important;
    text-decoration: underline !important;
    text-underline-offset: 2px !important;
  }
  .td-id .inv-link:hover { color: #155fd4 !important; }
  .td-customer { font-size: 15px !important; font-weight: 700 !important; color: #1a1a2e !important; }
  .td-amount   { font-size: 14px !important; letter-spacing: -0.02em !important; }
}

@media (max-width: 480px) {
  .view-toggle-btn { display: none !important; }
}
</style>