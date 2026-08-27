<template>
  <div class="list-page">

    <!-- ── Toolbar ── -->
    <div class="sales-toolbar">
      <div class="sales-search">
        <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
        <input v-model="search" placeholder="Search credit notes, customers…" class="sales-search-input" />
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
        <button class="sales-btn-ghost" @click="load" title="Refresh"><span v-html="icon('refresh',14)"></span></button>
        <button class="sales-btn-ghost" @click="exportCSV" title="Export CSV"><span v-html="icon('download',14)"></span> CSV</button>
        <button class="sales-btn-primary" @click="openNew" :disabled="!$canCreate('invoices')" :title="!$canCreate('invoices') ? 'Read-only access' : ''">
          <span v-html="icon('plus',13)"></span> New Credit Note
        </button>
      </div>
    </div>

    <!-- ── KPI Cards ── -->
    <div class="bk-kpi-grid bk-kpi-grid-4">
      <div class="bk-kpi-card bk-kpi-accent clickable" @click="activeTab='all'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#dbeafe"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.8"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Total Credit Notes</div><div class="bk-kpi-value">{{ list.length }}</div><div class="bk-kpi-trend" :class="cnTrends.total.up?'bk-trend-up':'bk-trend-down'">{{ cnTrends.total.up?'↑':'↓' }} {{ cnTrends.total.pct }}% vs last month</div></div></div></div>
      <div class="bk-kpi-card bk-kpi-success clickable" @click="activeTab='issued'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#dcfce7"><svg width="22" height="22" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="#16a34a" stroke-width="1.8"/><polyline points="7 12.5 10.5 16 17 9" stroke="#16a34a" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Issued</div><div class="bk-kpi-value bk-kpi-green">{{ counts.issued }}</div><div class="bk-kpi-trend" :class="cnTrends.issued.up?'bk-trend-up':'bk-trend-down'">{{ cnTrends.issued.up?'↑':'↓' }} {{ cnTrends.issued.pct }}% vs last month</div></div></div></div>
      <div class="bk-kpi-card"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#fee2e2"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="1.8"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Open Balance</div><div class="bk-kpi-value bk-kpi-red" style="font-size:18px">{{ fmtCur(summary.openBalance) }}</div><div class="bk-kpi-trend bk-trend-neutral">unapplied credit</div></div></div></div>
      <div class="bk-kpi-card"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#dcfce7"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12"/><path d="M6 8h12"/><path d="m6 13 8.5 8"/><path d="M6 13h3"/><path d="M9 13c6.667 0 6.667-10 0-10"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Total Credit Value</div><div class="bk-kpi-value bk-kpi-green" style="font-size:18px">{{ fmtCur(summary.totalValue) }}</div><div class="bk-kpi-trend" :class="cnTrends.value.up?'bk-trend-up':'bk-trend-down'">{{ cnTrends.value.up?'↑':'↓' }} {{ cnTrends.value.pct }}% vs last month</div></div></div></div>
    </div>
    <div class="bk-stat-grid">
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">This Month</div><div class="bk-stat-value">{{ cnThisMonth.count }}</div></div><div class="bk-stat-icon" style="background:#dbeafe;color:#2563eb"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg></div></div></div>
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">This Month Value</div><div class="bk-stat-value bk-kpi-green" style="font-size:16px">{{ fmtCur(cnThisMonth.value) }}</div></div><div class="bk-stat-icon" style="background:#dcfce7;color:#16a34a"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/></svg></div></div></div>
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">Draft</div><div class="bk-stat-value">{{ counts.draft }}</div></div><div class="bk-stat-icon" style="background:#f8fafc;color:#6b7280"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></div></div></div>
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">Avg Credit Value</div><div class="bk-stat-value" style="font-size:16px">{{ fmtCur(cnAvg) }}</div></div><div class="bk-stat-icon" style="background:#e5e7eb;color:#6b7280"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg></div></div></div>
    </div>

    <!-- ── Bulk action bar ── -->
    <BulkActionBar :count="selected.size" @clear="selected=new Set()">
      <button :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="bulkEmail"><span v-html="icon('mail',13)"></span> Send Email</button>
      <button class="bab-danger" :disabled="!$canDelete('invoices')" :title="!$canDelete('invoices') ? 'Not permitted' : ''" @click="bulkDelete">Delete Drafts</button>
      <button @click="exportCSV"><span v-html="icon('download',13)"></span> Export CSV</button>
    </BulkActionBar>

    <!-- ── Table ── -->
    <div class="inv-table-wrap">
      <table class="inv-table cn-desktop-table">
        <thead>
          <tr>
            <th style="width:32px"><input type="checkbox" @change="toggleAll" :checked="allChecked" /></th>
            <th @click="sortBy('name')" class="sortable">CREDIT NOTE # <span v-html="sortArrow('name')"></span></th>
            <th @click="sortBy('customer_name')" class="sortable">CUSTOMER <span v-html="sortArrow('customer_name')"></span></th>
            <th @click="sortBy('posting_date')" class="sortable">DATE <span v-html="sortArrow('posting_date')"></span></th>
            <th>AGAINST INVOICE</th>
            <th>STATUS</th>
            <th @click="sortBy('grand_total')" class="sortable ta-r">AMOUNT <span v-html="sortArrow('grand_total')"></span></th>
            <th class="ta-r">AVAILABLE</th>
            <th style="width:120px;text-align:center">ACTIONS</th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 6" :key="n"><td colspan="9"><div class="shimmer"></div></td></tr>
          </template>
          <template v-else>
            <tr v-for="c in paged" :key="c.name" class="inv-row" :class="{selected:selected.has(c.name)}">
              <td><input type="checkbox" :checked="selected.has(c.name)" @change="toggle(c.name)" /></td>
              <td @click="openView(c)"><DocLink doctype="Credit Note" :name="c.name" /></td>
              <td @click="openView(c)">{{ c.customer_name || c.customer || '—' }}</td>
              <td @click="openView(c)" class="text-muted mono-sm">{{ fmtDate(c.posting_date) }}</td>
              <td @click="openView(c)" class="text-muted mono-sm">{{ c.return_against||'—' }}</td>
              <td @click="openView(c)"><span class="inv-status-badge" :class="statusCls(c)">{{ statusLabel(c) }}</span></td>
              <td @click="openView(c)" class="ta-r mono-sm" style="color:#7f1d1d">{{ fmtCur(Math.abs(c.grand_total||0)) }}</td>
              <td @click="openView(c)" class="ta-r mono-sm">
                <span v-if="c.docstatus===1 && balanceFor(c.name)===null" class="text-muted" title="Couldn't load balance — refresh to retry">Unknown</span>
                <span v-else-if="c.docstatus===1" :class="balanceFor(c.name)>0?'text-danger':'text-success'">{{ fmtCur(balanceFor(c.name)) }}</span>
                <span v-else class="text-muted">—</span>
              </td>
              <td class="cn-act-cell">
                <button class="inv-act-btn" @click="openView(c)" title="View"><span v-html="icon('eye',13)"></span></button>
                <button v-if="c.docstatus===0" class="inv-act-btn" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : 'Edit'" @click="openEdit(c)"><span v-html="icon('edit',13)"></span></button>
                <button v-if="c.docstatus===1 && balanceFor(c.name)>0" class="inv-act-btn cn-act-apply" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : 'Apply to Invoice'" @click="applyCN(c)">↳</button>
                <button v-if="c.docstatus===1 && cnStatus(c)!=='applied'" class="inv-act-btn cn-act-cancel" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : 'Cancel Credit Note'" @click="cancelCN(c)"><span v-html="icon('x',12)"></span></button>
                <button v-if="c.docstatus===0 || c.docstatus===2" class="inv-act-btn cn-act-del" :disabled="!$canDelete('invoices')" :title="!$canDelete('invoices') ? 'Not permitted' : 'Delete'" @click="deleteCN(c)"><span v-html="icon('trash',13)"></span></button>
              </td>
            </tr>
            <tr v-if="!sorted.length"><td colspan="9" class="cn-empty">No credit notes match</td></tr>
          </template>
        </tbody>
      </table>

      <!-- Mobile cards (shown at ≤768px) -->
      <div class="cn-mobile-cards">
        <template v-if="loading">
          <div v-for="n in 5" :key="n" class="cn-mobile-card cn-mc--skeleton">
            <div class="cn-mc-shimmer" style="height:13px;width:55%;margin-bottom:8px"></div>
            <div class="cn-mc-shimmer" style="height:11px;width:40%;margin-bottom:6px"></div>
            <div class="cn-mc-shimmer" style="height:11px;width:65%"></div>
          </div>
        </template>
        <div v-else-if="!sorted.length" class="cn-mc-empty">
          <div style="font-size:32px;margin-bottom:8px">📝</div>
          <div>No credit notes found</div>
        </div>
        <template v-else>
          <div v-for="c in paged" :key="c.name" class="cn-mobile-card" @click="openView(c)">
            <div class="cn-mc-top">
              <span class="cn-mc-docno">{{ c.name }}</span>
              <span class="inv-status-badge" :class="statusCls(c)">{{ statusLabel(c) }}</span>
            </div>
            <div class="cn-mc-mid">{{ c.customer_name || c.customer || '—' }}</div>
            <div class="cn-mc-meta">
              <span>{{ fmtDate(c.posting_date) }}</span>
              <span class="cn-mc-amount">{{ fmtCur(Math.abs(c.grand_total || 0)) }}</span>
            </div>
            <div v-if="c.docstatus===1 && balanceFor(c.name)>0" class="cn-mc-balance">Balance: {{ fmtCur(balanceFor(c.name)) }}</div>
            <div class="cn-mc-footer">
              <button class="cn-mc-btn" @click.stop="openView(c)">View</button>
              <button v-if="c.docstatus===0" class="cn-mc-btn" @click.stop="openEdit(c)">Edit</button>
              <button v-if="c.docstatus===1&&balanceFor(c.name)>0" class="cn-mc-btn cn-mc-apply" @click.stop="applyCN(c)">Apply</button>
              <button v-if="c.docstatus===1 && cnStatus(c)!=='applied'" class="cn-mc-btn cn-mc-cancel" @click.stop="cancelCN(c)">Cancel</button>
              <button v-if="c.docstatus===0||c.docstatus===2" class="cn-mc-btn cn-mc-danger" @click.stop="deleteCN(c)">Delete</button>
            </div>
          </div>
        </template>
      </div>
    </div>

    <div v-if="!loading && sorted.length" style="padding:12px 0 4px">
      <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="sorted.length" />
    </div>

    <!-- ── Create / Edit Drawer ── -->
    <div v-if="drawerOpen" class="inv-drawer-bg" @click.self="drawerOpen=false"></div>
    <div class="cn-drawer" :class="{open:drawerOpen}">

      <!-- Header -->
      <div class="inv-dh">
        <div class="cn-dheader-left">
          <div class="cn-dheader-ico" :class="editingName?'edit':''">
            <span v-html="icon(editingName?'edit':'creditnote',18)"></span>
          </div>
          <div>
            <div class="inv-dh-title">{{ editingName ? 'Edit Credit Note' : 'New Credit Note' }}</div>
            <div class="inv-dh-sub">
              {{ editingName ? editingName : 'Issue a credit against a customer invoice' }}
            </div>
          </div>
        </div>
        <button class="inv-dclose" @click="drawerOpen=false"><span v-html="icon('x',16)"></span></button>
      </div>

      <div class="inv-dbody cn-dbody">

        <!-- ══ CARD 1: Customer & Date ══ -->
        <div class="add-card">
          <div class="add-card-header" @click="cnCollapsed.customer=!cnCollapsed.customer">
            <div class="add-card-title">
              <span class="add-card-title-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              </span>
              Customer &amp; Date
            </div>
            <span class="add-card-chevron" :class="{collapsed:cnCollapsed.customer}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
          </div>
          <div class="add-card-body" :class="{collapsed:cnCollapsed.customer}">
            <div class="inv-fg inv-fg2">
              <div class="cn-field" style="grid-column:1/-1">
                <label class="inv-lbl">Customer <span class="inv-req">*</span></label>
                <SearchableSelect v-model="form.customer" :options="customers" placeholder="Select customer…"
                  :createable="true" createDoctype="Customer"
                  @search="fetchCustomers" @select="onCustomerSelect" />
              </div>
              <div class="cn-field">
                <label class="inv-lbl">Date <span class="inv-req">*</span></label>
                <input v-model="form.posting_date" type="date" class="inv-fi" />
              </div>
              <div class="cn-field">
                <label class="inv-lbl">Against Invoice</label>
                <SearchableSelect v-model="form.return_against" :options="invoices"
                  placeholder="Select invoice (optional)…" @search="fetchInvoices" @select="onInvoiceSelect" />
              </div>

              <!-- Invoice summary shown after selecting Against Invoice -->
              <div v-if="form.return_against" class="cn-field" style="grid-column:1/-1">
                <div class="cn-inv-summary">
                  <div v-if="invoiceSummary.loading" class="cn-summary-loading">
                    <span class="cn-spinner"></span> Loading invoice details…
                  </div>
                  <template v-else-if="invoiceSummary.data">
                    <div class="cn-summary-header">
                      <span class="cn-summary-inv-name">{{ form.return_against }}</span>
                      <span class="cn-summary-badge"
                        :class="'cn-badge-' + (invoiceSummary.data.status || 'submitted').toLowerCase().replace(/\s+/g, '-')">
                        {{ invoiceSummary.data.status }}
                      </span>
                    </div>
                    <div class="cn-summary-grid">
                      <div class="cn-summary-cell">
                        <div class="cn-summary-label">Invoice Amount</div>
                        <div class="cn-summary-value">{{ fmtCur(invoiceSummary.data.grand_total) }}</div>
                      </div>
                      <div class="cn-summary-cell">
                        <div class="cn-summary-label">Paid</div>
                        <div class="cn-summary-value cn-val-paid">{{ fmtCur(invoiceSummary.data.total_paid) }}</div>
                      </div>
                      <div class="cn-summary-cell">
                        <div class="cn-summary-label">Previous Credits</div>
                        <div class="cn-summary-value cn-val-credit">{{ fmtCur(invoiceSummary.data.total_credits) }}</div>
                      </div>
                      <div class="cn-summary-cell cn-summary-cell-outstanding">
                        <div class="cn-summary-label">Outstanding</div>
                        <div class="cn-summary-value cn-val-outstanding">{{ fmtCur(invoiceSummary.data.outstanding) }}</div>
                      </div>
                    </div>
                  </template>
                </div>
              </div>

              <div class="cn-field">
                <label class="inv-lbl">Reason</label>
                <select v-model="form.reason" class="inv-fi">
                  <option>Price Adjustment</option>
                  <option>Goods Returned</option>
                  <option>Damaged Goods</option>
                  <option>Short Delivery</option>
                  <option>Duplicate Invoice</option>
                  <option>Incentive</option>
                  <option>Other</option>
                </select>
              </div>
              <div class="cn-field" v-if="form.reason === 'Incentive'">
  <label class="inv-lbl">
    Incentive Amount (OMR) <span class="inv-req">*</span>
  </label>

 <input
  v-model.number="form.incentive_amount"
  type="number"
  min="0"
  :max="incentiveMaxAmount"
  step="0.01"
  class="inv-fi"
  placeholder="Enter incentive amount"
  @input="validateIncentiveAmount"
/>
  <div class="cn-field-hint">
  Maximum:
  {{ fmtCur(incentiveMaxAmount) }}
</div>
</div>
              <div class="cn-field">
                <label class="inv-lbl">Cost Center</label>
                <select v-model="form.cost_center" class="inv-fi">
                  <option value="">— Select —</option>
                  <option v-for="cc in costCenters" :key="cc" :value="cc">{{ cc }}</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        
        <!-- ══ CARD 2: Items to Credit ══ -->
<template v-if="form.reason !== 'Incentive'">
<div class="add-card">
          <div class="add-card-header" @click="cnCollapsed.items=!cnCollapsed.items">
            <div class="add-card-title">
              <span class="add-card-title-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
              </span>
              Items to Credit
            </div>
            <div style="display:flex;align-items:center;gap:10px">
              <span class="cn-lines-badge">{{ lines.length }} line{{ lines.length!==1?'s':'' }}</span>
              <span class="add-card-chevron" :class="{collapsed:cnCollapsed.items}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
              </span>
            </div>
          </div>
          <div class="add-card-body" :class="{collapsed:cnCollapsed.items}" style="padding:0">
            <!-- Expandable item cards -->
            <div class="cn-item-cards">
              <div v-for="(line, idx) in lines" :key="line.id" class="cn-item-card">
                <!-- Card header -->
                <div class="cn-item-card-header" @click="line.collapsed = !line.collapsed">
                  <span class="cn-item-card-num">#{{ idx + 1 }}</span>
                  <span class="cn-item-card-title">{{ line.item_name || line.item_code || 'Line Item' }}</span>
                  <div class="cn-item-card-subtotal">
                    <span class="cn-item-subtotal-label">SUBTOTAL</span>
                    <span class="cn-item-amount">{{ fmtCur(line.amount) }}</span>
                  </div>
                  <span class="cn-item-chevron" :class="{collapsed: line.collapsed}">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
                  </span>
                  <button class="cn-item-rm" @click.stop="removeLine(line.id)">
                    <span v-html="icon('x', 12)"></span>
                  </button>
                </div>
                <!-- Card body -->
                <div class="cn-item-card-body" v-show="!line.collapsed">
                  <div class="cn-item-col cn-item-col--left">
                    <div class="cn-item-field">
                      <label>Item Name <span class="inv-req">*</span></label>
                      <SearchableSelect v-model="line.item_code" :options="items"
                        placeholder="Search item or service" :createable="true" createDoctype="Item"
                        @search="fetchItems" @update:modelValue="onItemChange(line)" />
                    </div>
                    <div class="cn-item-field" style="margin-top:12px">
                      <label>Description</label>
                      <textarea v-model="line.description" class="inv-fi cn-item-desc-ta" rows="3" maxlength="500" placeholder="Item description…"></textarea>
                      <div class="cn-field-hint">{{ (line.description||'').length }}/500</div>
                    </div>
                  </div>
                  <div class="cn-item-col cn-item-col--right">
                    <div class="cn-item-num-row">
                      <div class="cn-item-field">
                        <label>HSN/SAC</label>
                        <input v-model="line.hsn_code" class="inv-fi" placeholder="e.g. 998314" />
                      </div>
                      <div class="cn-item-field">
                        <label>UOM</label>
                        <select v-model="line.uom" class="inv-fi">
                          <option v-for="u in uomList" :key="u" :value="u">{{ u }}</option>
                        </select>
                      </div>
                    </div>
                    <div class="cn-item-num-row">
                      <div class="cn-item-field">
                        <label>Qty</label>
                        <input v-model.number="line.qty" type="number" min="0.001" step="0.001" class="inv-fi" @input="calcLine(line)" />
                      </div>
                      <div class="cn-item-field">
                        <label>Rate (OMR)</label>
                        <input v-model.number="line.rate" type="number" min="0" step="0.01" class="inv-fi" @input="calcLine(line)" />
                      </div>
                    </div>
                    <div class="cn-item-num-row" v-if="line.batch_no">
                      <div class="cn-item-field">
                        <label>Batch No</label>
                        <input :value="line.batch_no" class="inv-fi" disabled />
                      </div>
                      <div class="cn-item-field" v-if="line.batch_expiry_date">
                        <label>Batch Expiry</label>
                        <input :value="line.batch_expiry_date" class="inv-fi" disabled />
                      </div>
                    </div>
                    <div class="cn-item-num-row">
                      <div class="cn-item-field">
                        <label>Discount %</label>
                        <input v-model.number="line.discount_percentage" type="number" min="0" max="100" step="0.1" class="inv-fi" @input="calcLine(line)" />
                      </div>
                      <div class="cn-item-field">
                        <label>Tax Template</label>
                        <select v-model="line.tax_code" class="inv-fi">
                          <option value="">— No Tax —</option>
                          <option v-for="t in taxTemplates" :key="t.name" :value="t.name">{{ t.title || t.name }}</option>
                        </select>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div style="padding:10px 16px 4px">
              <button class="inv-add-line-btn" @click="addLine"><span v-html="icon('plus',12)"></span> Add Item</button>
            </div>
            <!-- Totals: subtotal + taxes from invoice + grand total -->
            <div class="cn-form-totals">
              <div v-if="cnTaxLines.length" class="cn-tax-note">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                Tax rates inherited from invoice {{ form.return_against }}
              </div>
              <div class="po-totals" style="justify-content:flex-end">
                <div class="po-totals-right" style="min-width:260px">
                  <div class="po-total-row">
                    <span>Subtotal</span>
                    <span>{{ fmtCur(subtotal) }}</span>
                  </div>
                  <template v-if="cnTaxLines.length">
                    <div v-for="tl in cnTaxLines" :key="tl.description" class="po-total-row cn-tax-row">
                      <span>{{ tl.description }} ({{ tl.rate }}%)</span>
                      <span>{{ fmtCur(tl.amount) }}</span>
                    </div>
                  </template>
                  <div v-else class="po-total-row cn-tax-row">
                    <span>Tax</span><span>{{ fmtCur(0) }}</span>
                  </div>
                  <div class="po-total-row">
                    <span>Total Credit</span>
                    <span>{{ fmtCur(cnGrandTotal) }}</span>
                  </div>
                </div>
              </div>
            </div> <!-- /cn-form-totals -->
          </div>
        </div>
        </template>

        <!-- ══ CARD 3: Notes ══ -->
        <div class="add-card">
          <div class="add-card-header" @click="cnCollapsed.notes=!cnCollapsed.notes">
            <div class="add-card-title">
              <span class="add-card-title-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
              </span>
              Notes
            </div>
            <span class="add-card-chevron" :class="{collapsed:cnCollapsed.notes}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
          </div>
          <div class="add-card-body" :class="{collapsed:cnCollapsed.notes}">
            <textarea v-model="form.notes" rows="3" class="inv-fi" placeholder="Internal note (optional)…" maxlength="500"></textarea>
            <div class="cn-field-hint">{{ (form.notes||'').length }}/500</div>
          </div>
        </div>

      </div>

      <div class="inv-dfooter">
        <button class="form-btn form-btn-outline" @click="drawerOpen=false" :disabled="drawerSaving">Cancel</button>
        <div>
        <button class="add-btn-draft" style="margin-right: 5px;" :disabled="drawerSaving" @click="saveCN(0)"><span v-html="icon('save',13)"></span> {{ drawerSaving?'Saving…':'Save Draft' }}</button>
        <button class="add-btn-more" :disabled="drawerSaving" @click="saveCN(1)"><span v-html="icon('check',13)"></span> {{ drawerSaving?'Saving…':'Submit' }}</button>
        </div>
      </div>
    </div>

    <!-- ── View Drawer ── -->
    <div v-if="viewOpen" class="inv-drawer-bg" @click.self="viewOpen=false"></div>
    <div class="cn-drawer cn-view-drawer" :class="{open:viewOpen}">
      <template v-if="viewDoc">
        <div class="inv-view-header cn-view-header-fixed">
          <div class="inv-view-head-cn">
            <div class="cn-view-head-left">
              <div class="inv-view-number">{{ viewDoc.name }}</div>
              <div class="inv-view-subtitle">
                <DocLink doctype="Customer" :name="viewDoc.customer" :mono-style="false">{{ viewDoc.customer_name||viewDoc.customer }}</DocLink>
              </div>
            </div>
            <button class="inv-dclose cn-vclose-fixed" @click="viewOpen=false"><span v-html="icon('x',16)"></span></button>
          </div>
        </div>

        <div class="cn-stepper-wrap"><TimelineStepper :steps="timelineSteps" /></div>

        <div class="inv-view-tabs">
          <button class="inv-vtab" :class="{active:viewTab==='details'}" @click="viewTab='details'">Details</button>
          <button class="inv-vtab" :class="{active:viewTab==='applied'}" @click="viewTab='applied'">
            Applied To<span v-if="viewApplications.length" class="inv-vtab-count">{{ viewApplications.length }}</span>
          </button>
          <button v-if="viewDoc.docstatus===1" class="inv-vtab" :class="{active:viewTab==='journal'}" @click="viewTab='journal'">Journal</button>
        </div>

        <div class="inv-dbody">
          <template v-if="viewTab==='journal'">
            <JournalTab
              voucher-type="Sales Invoice"
              :voucher-no="viewDoc.name"
              label="Credit Note"
              :currency="viewDoc.currency || 'INR'"
            />
          </template>
          <template v-if="viewTab==='details'">
            <div class="cn-meta-grid">
              <div><div class="cn-meta-lbl">Date</div><div class="mono-sm">{{ fmtDate(viewDoc.posting_date) }}</div></div>
              <div><div class="cn-meta-lbl">Against Invoice</div><div><DocLink doctype="Sales Invoice" :name="viewDoc.return_against" /></div></div>
              <div><div class="cn-meta-lbl">Reason</div><div class="mono-sm" style="color:#374151">{{ viewReason || '—' }}</div></div>
              <div><div class="cn-meta-lbl">Total Credit</div><div class="mono-sm" style="color:#7f1d1d;font-weight:600">{{ fmtCur(Math.abs(viewDoc.grand_total||0)) }}</div></div>
              <div><div class="cn-meta-lbl">Available Balance</div>
                <div class="mono-sm" :class="viewBalance>0?'text-danger':'text-success'">{{ fmtCur(viewBalance) }}</div>
              </div>
              <div v-if="viewDoc.cost_center"><div class="cn-meta-lbl">Cost Center</div>
                <div class="mono-sm" style="color:#059669">{{ viewDoc.cost_center }}</div>
              </div>
            </div>

            <div v-if="viewLoading" style="text-align:center;padding:24px;color:#6b7280;font-size:13px">Loading…</div>
            <template v-else-if="viewReason === 'Incentive'">
              <div class="inv-sec-lbl">Incentive</div>
              <div style="padding:16px;background:#f9fafb;border-radius:8px;color:#374151;font-size:13px">
                This is a goodwill incentive credit of {{ fmtCur(Math.abs(viewDoc.grand_total||0)) }} issued against
                <DocLink doctype="Sales Invoice" :name="viewDoc.return_against" /> — not tied to specific line items.
              </div>
            </template>
            <template v-else-if="viewItems.length">
              <div class="inv-sec-lbl">Line Items</div>
              <!-- Desktop table -->
              <div class="cn-view-items cn-view-items--desktop">
                <div class="cn-view-items-head"><span>Item</span><span>Batch No</span><span class="ta-r">Qty</span><span class="ta-r">Rate</span><span class="ta-r">Amount</span></div>
                <div v-for="it in viewItems" :key="it.name" class="cn-view-items-row">
                  <span>{{ it.item_name||it.item_code }}</span>
                  <span class="mono-sm text-muted">{{ it.batch_no || '—' }}</span>
                  <span class="ta-r mono-sm">{{ Math.abs(it.qty||0) }}</span>
                  <span class="ta-r mono-sm">{{ fmtCur(it.rate) }}</span>
                  <span class="ta-r mono-sm" style="font-weight:600">{{ fmtCur(Math.abs(it.amount||0)) }}</span>
                </div>
              </div>
              <!-- Mobile cards -->
              <div class="cn-view-items--mobile">
                <div v-for="(it, idx) in viewItems" :key="it.name" class="cn-vi-card">
                  <div class="cn-vi-card-header">
                    <span class="cn-vi-card-num">#{{ idx + 1 }}</span>
                    <span class="cn-vi-card-name">{{ it.item_name||it.item_code }}</span>
                    <span class="cn-vi-card-amount">{{ fmtCur(Math.abs(it.amount||0)) }}</span>
                  </div>
                  <div class="cn-vi-card-meta">
                    <div class="cn-vi-meta-item" v-if="it.batch_no">
                      <span class="cn-vi-meta-lbl">Batch No</span>
                      <span class="cn-vi-meta-val">{{ it.batch_no }}</span>
                    </div>
                    <div class="cn-vi-meta-item">
                      <span class="cn-vi-meta-lbl">Qty</span>
                      <span class="cn-vi-meta-val">{{ Math.abs(it.qty||0) }}</span>
                    </div>
                    <div class="cn-vi-meta-item">
                      <span class="cn-vi-meta-lbl">Rate</span>
                      <span class="cn-vi-meta-val">{{ fmtCur(it.rate) }}</span>
                    </div>
                    <div class="cn-vi-meta-item cn-vi-meta-item--amount">
                      <span class="cn-vi-meta-lbl">Amount</span>
                      <span class="cn-vi-meta-val cn-vi-meta-val--amount">{{ fmtCur(Math.abs(it.amount||0)) }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <!-- Totals: subtotal + taxes + grand total -->
              <div class="cn-view-totals">
                <div class="cn-vt-row">
                  <span class="cn-vt-lbl">Subtotal</span>
                  <span class="cn-vt-val">{{ fmtCur(viewSubtotal) }}</span>
                </div>
                <template v-if="viewTaxes.length">
                  <div v-for="(tx, i) in viewTaxes" :key="i" class="cn-vt-row cn-vt-tax">
                    <span class="cn-vt-lbl">{{ tx.description || tx.account_head }} ({{ tx.rate }}%)</span>
                    <span class="cn-vt-val">{{ fmtCur(Math.abs(tx.tax_amount || 0)) }}</span>
                  </div>
                </template>
                <div class="cn-vt-row ">
                  <span class="cn-vt-lbl">Total Credit</span>
                  <span class="cn-vt-val" style="color:#7f1d1d">{{ fmtCur(Math.abs(viewDoc.grand_total||0)) }}</span>
                </div>
              </div>
            </template>
          </template>

          <template v-if="viewTab==='applied'">
            <div v-if="viewLoading" style="text-align:center;padding:24px;color:#6b7280;font-size:13px">Loading…</div>
            <template v-else>
              <!-- Balance summary strip -->
              <div class="cn-applied-summary">
                <div class="cn-applied-summ-item">
                  <div class="cn-applied-summ-lbl">Total Credit</div>
                  <div class="cn-applied-summ-val" style="color:#7f1d1d">{{ fmtCur(Math.abs(viewDoc?.grand_total||0)) }}</div>
                </div>
                <div class="cn-applied-summ-sep">—</div>
                <div class="cn-applied-summ-item">
                  <div class="cn-applied-summ-lbl">Applied</div>
                  <div class="cn-applied-summ-val" style="color:#059669">{{ fmtCur(appliedTotal) }}</div>
                </div>
                <div class="cn-applied-summ-sep">=</div>
                <div class="cn-applied-summ-item">
                  <div class="cn-applied-summ-lbl">Available</div>
                  <div class="cn-applied-summ-val" :class="viewBalance>0?'text-danger':'text-success'">{{ fmtCur(viewBalance) }}</div>
                </div>
              </div>

              <!-- Invoice-wise groups -->
              <template v-if="groupedApplications.length">
                <div v-for="grp in groupedApplications" :key="grp.invoice" class="cn-inv-group">
                  <div class="cn-inv-group-header">
                    <div style="display:flex;align-items:center;gap:8px">
                      <DocLink doctype="Sales Invoice" :name="grp.invoice" />
                      <span class="cn-inv-grp-count">{{ grp.entries.length }} allocation{{ grp.entries.length!==1?'s':'' }}</span>
                    </div>
                    <span class="cn-inv-grp-total">{{ fmtCur(grp.total) }}</span>
                  </div>
                  <div class="cn-inv-entry-row cn-inv-entry-head">
                    <span>Date</span><span>Reference</span><span class="ta-r">Amount Applied</span>
                  </div>
                  <div v-for="a in grp.entries" :key="a.payment_entry" class="cn-inv-entry-row">
                    <span class="mono-sm text-muted">{{ fmtDate(a.date) }}</span>
                    <DocLink :doctype="a.ref_doctype||'Journal Entry'" :name="a.payment_entry" />
                    <span class="ta-r mono-sm" style="font-weight:600;color:#059669">{{ fmtCur(a.amount) }}</span>
                  </div>
                </div>
              </template>
              <div v-else style="text-align:center;padding:24px;color:#9ca3af;font-size:13px">
                No applications yet.
                <div v-if="viewBalance>0 && viewDoc.docstatus===1" style="margin-top:8px">
                  <button class="form-btn form-btn-primary" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="applyCN(viewDoc)" style="font-size:12px;padding:6px 12px">↳ Apply to Invoice</button>
                </div>
              </div>
            </template>
          </template>
        </div>

        <div class="cn-view-footer">
          <!-- Primary actions row — contextual, full-width prominence -->
          <div class="cn-vf-primary">
            <button v-if="viewDoc.docstatus===0" class="cn-vf-btn cn-vf-btn-submit" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="submitDraftCN(viewDoc)">
              <span v-html="icon('check',14)"></span> Submit
            </button>
            <button v-if="viewDoc.docstatus===1 && viewBalance>0" class="cn-vf-btn cn-vf-btn-apply" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="applyCN(viewDoc)">
              ↳ <div class="cn-view-action-btn">Apply to Invoice</div>
            </button>
            <button v-if="viewDoc.docstatus===1 && viewBalance>0" class="cn-vf-btn cn-vf-btn-auto" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="autoApplyCN(viewDoc)">
              ⚡<div class="cn-view-action-btn">Auto Apply</div>
            </button>
            <button v-if="viewDoc.docstatus===1 && viewBalance>0" class="cn-vf-btn cn-vf-btn-refund" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="refundCN(viewDoc)">
              ↩  <div class="cn-view-action-btn">Refund Credit</div>
            </button>
            <button v-if="viewDoc.docstatus===1 && viewBalance>0 && viewBalance<=500" class="cn-vf-btn cn-vf-btn-outline" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="writeOffCN(viewDoc)">
              ✎ <div class="cn-view-action-btn">Write Off</div>
            </button>
          </div>
          <!-- Secondary actions row — compact icon+label buttons -->
          <div class="cn-vf-secondary">
            <button class="cn-vf-sec-btn" @click="viewOpen=false">
              <span v-html="icon('x',13)"></span> <div class="cn-view-action-btn">Close</div>
            </button>
            <button v-if="viewDoc.docstatus===0" class="cn-vf-sec-btn" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="openEdit(viewDoc);viewOpen=false">
              <span v-html="icon('edit',13)"></span> <div class="cn-view-action-btn">Edit</div>
            </button>
            <button v-if="viewDoc.docstatus===1" class="cn-vf-sec-btn" @click="emailCN(viewDoc)">
              <span v-html="icon('mail',13)"></span> <div class="cn-view-action-btn">Email</div>
            </button>
            <button class="cn-vf-sec-btn" @click="printCN(viewDoc)">
              <span v-html="icon('printer',13)"></span> <div class="cn-view-action-btn">Print</div>
            </button>
            <button v-if="viewDoc.docstatus===1 && cnStatus(viewDoc)!=='applied'" class="cn-vf-sec-btn cn-vf-sec-danger" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="cancelCN(viewDoc)">
              <span v-html="icon('x-circle',13)"></span> <div class="cn-view-action-btn">Cancel</div>
            </button>
            <button v-if="viewDoc.docstatus===0 || viewDoc.docstatus===2" class="cn-vf-sec-btn cn-vf-sec-danger" :disabled="!$canDelete('invoices')" :title="!$canDelete('invoices') ? 'Not permitted' : ''" @click="deleteCN(viewDoc)">
              <span v-html="icon('trash',13)"></span> <div class="cn-view-action-btn">Delete</div>
            </button>
          </div>
        </div>
      </template>
    </div>

    <!-- ── Apply-to-Invoice modal ── -->
    <div v-if="applyModal.open" class="inv-drawer-bg" @click.self="applyModal.open=false" style="z-index:60"></div>
    <div v-if="applyModal.open" class="cn-apply-dialog">
      <div class="inv-dh" style="background:linear-gradient(135deg,#7f1d1d,#dc2626);height:auto;padding:14px 18px">
        <div class="inv-dh-title">Apply Credit Note — {{ applyModal.cnName }}</div>
        <button class="inv-dclose" @click="applyModal.open=false"><span v-html="icon('x',16)"></span></button>
      </div>
      <div class="inv-dbody">
        <!-- Credit balance pill -->
        <div class="cn-balance-pill">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          Credit Available: <strong>{{ fmtCur(applyModal.balance) }}</strong>
        </div>

        <!-- Invoice selector -->
        <div class="cn-field">
          <label class="inv-lbl">Target Invoice <span class="inv-req">*</span></label>
          <select v-model="applyModal.invoice" class="inv-fi" @change="onApplyInvoiceChange">
            <option value="">— Select invoice —</option>
            <option v-for="i in applyModal.openInvoices" :key="i.name" :value="i.name">
              {{ i.name === applyModal.originInv ? '★ ' : '' }}{{ i.name }} · {{ fmtCur(i.outstanding_amount) }} due{{ i.name === applyModal.originInv ? ' (original)' : '' }}
            </option>
          </select>
        </div>

        <!-- Invoice summary card (shown after selection) -->
        <div v-if="applyModal.invoice" class="cn-inv-summary">
          <div v-if="applyModal.summaryLoading" class="cn-summary-loading">
            <span class="cn-spinner"></span> Loading invoice details…
          </div>
          <template v-else-if="applyModal.summary">
            <div class="cn-summary-header">
              <span class="cn-summary-inv-name">{{ applyModal.invoice }}</span>
              <span class="cn-summary-badge" :class="'cn-badge-' + (applyModal.summary.status || 'Unpaid').toLowerCase().replace(' ','-')">
                {{ applyModal.summary.status }}
              </span>
            </div>
            <div class="cn-summary-grid">
              <div class="cn-summary-cell">
                <div class="cn-summary-label">Invoice Amount</div>
                <div class="cn-summary-value">{{ fmtCur(applyModal.summary.grand_total) }}</div>
              </div>
              <div class="cn-summary-cell">
                <div class="cn-summary-label">Paid</div>
                <div class="cn-summary-value cn-val-paid">{{ fmtCur(applyModal.summary.total_paid) }}</div>
              </div>
              <div class="cn-summary-cell">
                <div class="cn-summary-label">Previous Credits</div>
                <div class="cn-summary-value cn-val-credit">{{ fmtCur(applyModal.summary.total_credits) }}</div>
              </div>
              <div class="cn-summary-cell cn-summary-cell-outstanding">
                <div class="cn-summary-label">Outstanding</div>
                <div class="cn-summary-value cn-val-outstanding">{{ fmtCur(applyModal.summary.outstanding) }}</div>
              </div>
            </div>
          </template>
        </div>

        <!-- Amount to apply -->
        <div class="cn-field">
          <label class="inv-lbl">Amount to Apply <span class="inv-req">*</span></label>
          <input v-model.number="applyModal.amount" type="number" min="0.01" :max="applyModal.balance" step="0.01" class="inv-fi ta-r" />
        </div>
      </div>
      <div class="inv-dfooter">
        <button class="form-btn form-btn-outline" @click="applyModal.open=false" :disabled="applyModal.saving">Cancel</button>
        <button class="form-btn form-btn-primary" :disabled="applyModal.saving || !applyModal.invoice || applyModal.amount<=0" @click="submitApply">
          {{ applyModal.saving ? 'Applying…' : `Apply ${fmtCur(applyModal.amount)}` }}
        </button>
      </div>
    </div>

    <!-- ── Refund modal ── -->
    <div v-if="refundModal.open" class="inv-drawer-bg" @click.self="refundModal.open=false" style="z-index:60"></div>
    <div v-if="refundModal.open" class="cn-apply-dialog">
      <div class="inv-dh" style="background:linear-gradient(135deg,#78350f,#d97706);height:auto;padding:14px 18px">
        <div class="inv-dh-title">Refund Credit Note — {{ refundModal.cnName }}</div>
        <button class="inv-dclose" @click="refundModal.open=false"><span v-html="icon('x',16)"></span></button>
      </div>
      <div class="inv-dbody">
        <div style="font-size:12.5px;color:#374151">Available Balance: <strong>{{ fmtCur(refundModal.balance) }}</strong></div>
        <div class="inv-fg inv-fg2">
          <div class="cn-field">
            <label class="inv-lbl">Refund Amount <span class="inv-req">*</span></label>
            <input v-model.number="refundModal.amount" type="number" min="0.01" :max="refundModal.balance" step="0.01" class="inv-fi ta-r"/>
          </div>
          <div class="cn-field">
            <label class="inv-lbl">Mode</label>
            <select v-model="refundModal.mode" class="inv-fi">
              <option>Bank Transfer</option>
              <option>Cash</option>
              <option>Cheque</option>
              <option>UPI</option>
              <option>NEFT</option>
            </select>
          </div>
          <div class="cn-field" style="grid-column:1/-1">
            <label class="inv-lbl">Reference / Cheque #</label>
            <input v-model="refundModal.reference" class="inv-fi" placeholder="Optional reference" />
          </div>
        </div>
      </div>
      <div class="inv-dfooter">
        <button class="form-btn form-btn-outline" @click="refundModal.open=false" :disabled="refundModal.saving">Cancel</button>
        <button class="form-btn form-btn-outline" :disabled="refundModal.saving || refundModal.amount<=0" @click="submitRefund">
          {{ refundModal.saving ? 'Processing…' : `Refund ${fmtCur(refundModal.amount)}` }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { apiList, apiSave, apiGet, apiGET, apiPOST, apiSubmit, apiDelete, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { usePermissions } from "../composables/usePermissions.js";
import { useDocStatus } from "../composables/useDocStatus.js";
import { useRoute } from "vue-router";
import { useEmailDialog } from "../composables/useEmailDialog.js";
import { useOpenFromQuery } from "../composables/useOpenFromQuery.js";
import { usePagination } from "../composables/usePagination.js";
import DocLink from "../components/DocLink.vue";
import JournalTab from "../components/JournalTab.vue";
import Pagination from "../components/Pagination.vue";
import { useConfirm } from "../composables/useConfirm.js";
import { useLivePreview } from "../composables/useLivePreview.js";
import { icon } from "../utils/icons.js";
import { flt, fmtDate } from "../utils/format.js";
import { computeTaxRows } from "../composables/useTaxCalc.js";
import SearchableSelect from "../components/SearchableSelect.vue";
import SummaryStrip from "../components/SummaryStrip.vue";
import BulkActionBar from "../components/BulkActionBar.vue";
import TimelineStepper from "../components/TimelineStepper.vue";

const { toast } = useToast();
const { canCreate, canEdit, canDelete } = usePermissions();
const route = useRoute();
const { confirm } = useConfirm();
const { printDoc, refreshBranding } = useLivePreview();
async function printCN(d) { try { await refreshBranding(); } catch {} printDoc(d, { title: "CREDIT NOTE", partyLabel: "Customer", partyField: "customer_name", companyName: d?.company || "" }); }

const { openEmail } = useEmailDialog();
// Credit-note-specific status — based on docstatus + available balance
function cnStatus(c) {
  if (c.docstatus === 2) return "cancelled";
  if (c.docstatus === 0) return "draft";
  const bal = balanceFor(c.name);
  if (bal === null) return "unknown";
  const total = Math.abs(flt(c.grand_total || 0));
  if (bal <= 0.005)        return "applied";
  if (bal < total - 0.005) return "partial";
  return "issued";
}
function statusLabel(c) {
  return { draft: "Draft", issued: "Issued", partial: "Partially Applied", applied: "Applied", cancelled: "Cancelled", unknown: "Balance Unknown" }[cnStatus(c)] || "—";
}
function statusCls(c) {
  return { draft: "cn-st-draft", issued: "cn-st-issued", partial: "cn-st-partial", applied: "cn-st-applied", cancelled: "cn-st-cancelled", unknown: "cn-st-draft" }[cnStatus(c)] || "";
}

const activeTab = ref("all");
const tabs = [
  { key: "all",       label: "All" },
  { key: "draft",     label: "Draft" },
  { key: "issued",    label: "Issued" },
  { key: "partial",   label: "Partially Applied" },
  { key: "applied",   label: "Applied" },
  { key: "cancelled", label: "Cancelled" },
];

const list = ref([]), loading = ref(false), search = ref(""), selected = ref(new Set());
const drawerOpen = ref(false), drawerSaving = ref(false), editingName = ref("");
const viewOpen = ref(false), viewDoc = ref(null), viewTab = ref("details");
const cnCollapsed = reactive({ customer: false, items: false, notes: true });
const viewLoading = ref(false), viewItems = ref([]), viewApplications = ref([]), viewBalance = ref(0), viewReason = ref("");
const viewTaxes = computed(() => (viewDoc.value?.taxes || []).filter(t => flt(t.tax_amount) !== 0 || flt(t.rate) !== 0));
const viewSubtotal = computed(() => viewItems.value.reduce((s, i) => s + Math.abs(flt(i.amount)), 0));
const customers = ref([]), items = ref([]), invoices = ref([]), lines = ref([]);
const uomList = ref(["Nos", "Kg", "Ltr", "Hrs", "Pcs", "Box", "Mtr", "Set"]);
const sortCol = ref("posting_date"), sortDir = ref("desc");
const _balances = ref({});
// Returns null when the balance couldn't be fetched (e.g. transient network
// failure during load()) — distinct from a legitimate 0 (fully applied).
// Callers must not treat null as 0: doing so silently makes a CN whose
// balance we simply failed to fetch look "fully applied" in the list,
// hiding a real available balance from the user.
function balanceFor(name) {
  const v = _balances.value[name];
  return v == null ? null : flt(v);
}

let _id = 1;
const blankLine = () => ({ id: _id++, item_code: "", item_name: "", description: "", hsn_code: "", qty: 1, rate: 0, uom: "Nos", discount_percentage: 0, discount_amount: 0, amount: 0, tax_code: "", collapsed: false, batch_no: "", batch_expiry_date: "" });
const costCenters = ref([]);
const form = reactive({
  customer: "",
  posting_date: todayStr(),
  return_against: "",
  reason: "Price Adjustment",
  incentive_amount: 0,
  notes: "",
  cost_center: ""
});
const invoiceSummary = reactive({ data: null, loading: false });
const isIncentive = computed(() => form.reason === "Incentive");

const incentiveMaxAmount = computed(() => {
  const data = invoiceSummary.data || {};

  const grandTotal = flt(data.grand_total || 0);
  const previousCredits = flt(data.total_credits || 0);

  // Capped by the invoice's total value minus credit already issued against
  // it — NOT by outstanding_amount. A credit note (including an Incentive)
  // is a goodwill/adjustment credit independent of whether the invoice is
  // still owed money; a fully paid invoice must remain a valid target (see
  // fetchInvoices() below).
  return Math.max(0, grandTotal - previousCredits);
});
const incentiveAmount = computed(() =>
  Math.max(0, flt(form.incentive_amount || 0))
);

function validateIncentiveAmount() {
  let amount = flt(form.incentive_amount || 0);

  if (amount < 0) {
    amount = 0;
  }

  const max = incentiveMaxAmount.value;

  if (max > 0 && amount > max) {
    amount = max;
  }

  form.incentive_amount = Math.round(amount * 100) / 100;
}
const cnTaxes = ref([]);
// Whether the source invoice's tax breakup was inter-state (IGST) rather than
// intra-state (CGST+SGST) — detected once from the inherited tax rows, since
// the CN form itself doesn't collect a place of supply. Used to steer which
// component rows apply when taxes are recalculated per remaining line below.
const cnIsInterState = ref(false);
function detectInterState(rows) {
  return (rows || []).some(t => /igst/i.test(t.description || "") || /igst/i.test(t.tax_type || "") || /igst/i.test(t.account_head || ""));
}
const taxTemplates = ref([]);
const taxAccountHead = ref("");

const applyModal = reactive({ open: false, saving: false, cnName: "", balance: 0, invoice: "", originInv: "", amount: 0, openInvoices: [], summary: null, summaryLoading: false });
const refundModal = reactive({ open: false, saving: false, cnName: "", balance: 0, amount: 0, mode: "Bank Transfer", reference: "" });

function todayStr() { return new Date().toISOString().slice(0, 10); }
function fmtCur(v) { const n = Math.abs(flt(v)); try { return new Intl.NumberFormat("en-OM", { style: "currency", currency: "OMR" }).format(n); } catch { return "ر.ع. " + n.toLocaleString("en-OM", { minimumFractionDigits: 3, maximumFractionDigits: 3 }); } }

async function load() {
  loading.value = true;
  try {
    const co = await resolveCompany();
    list.value = await apiList("Sales Invoice", {
      fields: ["name", "customer", "customer_name", "posting_date", "grand_total", "return_against", "docstatus", "status"],
      filters: [["is_return", "=", 1], ["company", "=", co]],
      limit: 100000,
      order: "posting_date desc, creation desc",
    });
    // Frappe sometimes omits customer_name on return invoices — resolve missing ones
    const missingNames = [...new Set(list.value.filter(c => !c.customer_name && c.customer).map(c => c.customer))];
    if (missingNames.length) {
      const custRows = await apiList("Customer", {
        fields: ["name", "customer_name"],
        filters: [["name", "in", missingNames]],
        limit: missingNames.length,
      }).catch(() => []);
      const nameMap = Object.fromEntries(custRows.map(r => [r.name, r.customer_name || r.name]));
      list.value = list.value.map(c => c.customer_name ? c : { ...c, customer_name: nameMap[c.customer] || c.customer });
    }
    const submitted = list.value.filter(c => c.docstatus === 1);
    const balances = await Promise.all(submitted.map(c =>
      apiGET("zoho_books_clone.api.docs.get_credit_note_balance", { credit_note_name: c.name }).catch(() => null)
    ));
    const map = {};
    submitted.forEach((c, i) => { if (balances[i]) map[c.name] = balances[i].balance; });
    _balances.value = map;
  } catch (e) { toast.error(e.message || "Failed to load credit notes"); }
  finally { loading.value = false; }
}

const counts = computed(() => {
  let draft = 0, issued = 0, partial = 0, applied = 0, cancelled = 0;
  for (const c of list.value) {
    const s = cnStatus(c);
    if (s === "draft")      draft++;
    else if (s === "issued")    issued++;
    else if (s === "partial")   partial++;
    else if (s === "applied")   applied++;
    else if (s === "cancelled") cancelled++;
  }
  return { draft, issued, partial, applied, cancelled };
});
const summary = computed(() => ({
  totalValue:  list.value.filter(c => c.docstatus === 1).reduce((s, c) => s + Math.abs(flt(c.grand_total)), 0),
  openBalance: Object.values(_balances.value).reduce((s, v) => s + flt(v), 0),
}));
const _cnYM  = () => { const d=new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; };
const _cnLYM = () => { const d=new Date(); d.setMonth(d.getMonth()-1); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; };
const _cnTr  = (a,b) => { if(!b&&!a) return {pct:0,up:true}; if(!b) return {pct:100,up:true}; const p=Math.round((a-b)/b*100); return {pct:Math.abs(p),up:p>=0}; };
const cnThisMonth = computed(()=>{ const ym=_cnYM(); const r=list.value.filter(c=>(c.posting_date||'').startsWith(ym)); return {count:r.length,value:r.reduce((s,c)=>s+Math.abs(flt(c.grand_total)),0)}; });
const cnAvg = computed(()=>{ const p=list.value.filter(c=>c.grand_total); return p.length?p.reduce((s,c)=>s+Math.abs(flt(c.grand_total)),0)/p.length:0; });
const cnTrends = computed(()=>({
  total:  _cnTr(cnThisMonth.value.count, list.value.filter(c=>(c.posting_date||'').startsWith(_cnLYM())).length),
  issued: _cnTr(counts.value.issued, list.value.filter(c=>(c.posting_date||'').startsWith(_cnLYM())&&c.docstatus===1).length),
  value:  _cnTr(cnThisMonth.value.value, list.value.filter(c=>(c.posting_date||'').startsWith(_cnLYM())&&c.docstatus===1).reduce((s,c)=>s+Math.abs(flt(c.grand_total)),0)),
}));

const filtered = computed(() => {
  let r = list.value;
  const t = activeTab.value;
  if (t === "draft" || t === "issued" || t === "partial" || t === "applied" || t === "cancelled")
    r = r.filter(c => cnStatus(c) === t);
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    r = r.filter(x => (x.name || "").toLowerCase().includes(q)
      || (x.customer_name || x.customer || "").toLowerCase().includes(q)
      || (x.return_against || "").toLowerCase().includes(q));
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
function sortBy(col) { if (sortCol.value === col) sortDir.value = sortDir.value === "asc" ? "desc" : "asc"; else { sortCol.value = col; sortDir.value = "asc"; } }
function sortArrow(col) { if (sortCol.value !== col) return '<span style="color:#d1d5db">⇅</span>'; return sortDir.value === "asc" ? "↑" : "↓"; }

const { page, pageSize, paged } = usePagination(sorted, { storageKey: "credit-notes" });

const allChecked = computed(() => sorted.value.length > 0 && sorted.value.every(c => selected.value.has(c.name)));
function toggle(n) { const s = new Set(selected.value); s.has(n) ? s.delete(n) : s.add(n); selected.value = s; }
function toggleAll(e) { selected.value = e.target.checked ? new Set(sorted.value.map(c => c.name)) : new Set(); }

const subtotal = computed(() => lines.value.reduce((s, l) => s + flt(l.amount), 0));
// Only lines that will actually be saved (has an item + qty), each taxed by
// its OWN tax_code — fixes taxes over-applying when items are removed after
// inheriting from an invoice: previously every inherited tax rate was applied
// to the whole remaining subtotal regardless of which items it belonged to.

const cnActiveLines = computed(() =>
  lines.value.filter(l => l.item_code && flt(l.qty) > 0)
);

const cnTaxCtx = computed(() => ({
  companyState: "same",
  placeOfSupply: cnIsInterState.value ? "different" : "same",
  defaultAccount: taxAccountHead.value,
}));
const cnTaxRows  = computed(() => computeTaxRows(cnActiveLines.value, taxTemplates.value, cnTaxCtx.value));
const cnTaxLines = computed(() => cnTaxRows.value.map(t => ({ description: t.description, rate: t.rate, amount: t.amount, tax_type: t.account_head })));

const cnGrandTotal = computed(() => {
  if (isIncentive.value) {
    return Math.max(0, flt(form.incentive_amount || 0));
  }

  return subtotal.value +
    cnTaxLines.value.reduce((s, t) => s + t.amount, 0);
});

const appliedTotal = computed(() => viewApplications.value.reduce((s, a) => s + flt(a.amount), 0));
const groupedApplications = computed(() => {
  const groups = {};
  for (const a of viewApplications.value) {
    if (!groups[a.invoice]) groups[a.invoice] = { invoice: a.invoice, total: 0, entries: [] };
    groups[a.invoice].total += flt(a.amount);
    groups[a.invoice].entries.push(a);
  }
  return Object.values(groups);
});

const timelineSteps = computed(() => {
  const c = viewDoc.value;
  if (!c) return [];
  if (c.docstatus === 2) {
    return [
      { key: "draft",     label: "Draft",     done: true },
      { key: "issued",    label: "Issued",    done: true },
      { key: "cancelled", label: "Cancelled", danger: true, current: true },
    ];
  }
  const st = cnStatus(c);
  const isDraft   = st === "draft";
  const isIssued  = st === "issued";
  const isPartial = st === "partial";
  const isApplied = st === "applied";
  return [
    { key: "draft",   label: "Draft",            done: !isDraft,              current: isDraft },
    { key: "issued",  label: "Issued",            done: isPartial || isApplied, current: isIssued },
    { key: "partial", label: "Partially Applied", done: isApplied,             current: isPartial },
    { key: "applied", label: "Applied",           done: isApplied,             current: isApplied },
  ];
});

// ── Create / Edit ─────────────────────────────────────────────────────────
function openNew() {
  editingName.value = "";
  Object.assign(form, {
  customer: "",
  posting_date: todayStr(),
  return_against: "",
  reason: "Price Adjustment",
  incentive_amount: 0,
  notes: "",
  cost_center: ""
});
  invoiceSummary.data = null; invoiceSummary.loading = false;
  cnTaxes.value = [];
  cnIsInterState.value = false;
  lines.value = [blankLine()];
  Object.assign(cnCollapsed, { customer: false, items: false, notes: true });
  fetchCustomers(""); fetchItems(""); fetchInvoices(""); fetchTaxTemplates(); fetchCostCenters();
  drawerOpen.value = true;
}
async function openEdit(c) {
  editingName.value = c.name;
  cnTaxes.value = [];
  Object.assign(form, {
  customer: c.customer || "",
  posting_date: c.posting_date || todayStr(),
  return_against: c.return_against || "",
  reason: "Price Adjustment",
  incentive_amount: 0,
  notes: "",
  cost_center: ""
});
  lines.value = [blankLine()];
  Object.assign(cnCollapsed, { customer: false, items: false, notes: true });
  fetchCustomers(""); fetchItems(""); fetchInvoices(""); fetchTaxTemplates(); fetchCostCenters();
  drawerOpen.value = true;
  try {
    const doc = await apiGet("Sales Invoice", c.name);
    // Reason is stored as "reason — notes" in remarks; restore both.
    if (doc?.remarks) {
      const parts = doc.remarks.split(" — ");
      form.reason = parts[0].trim() || "Price Adjustment";
      form.notes = parts.slice(1).join(" — ").trim();
    }
    if (form.reason === "Incentive") {
      // The saved item is a synthetic placeholder (Frappe requires >=1 item
      // row), not a real line — don't load it into the editable items grid.
      form.incentive_amount = Math.abs(doc?.items?.[0]?.amount || 0);
      lines.value = [blankLine()];
    } else if (doc?.items?.length) {
      lines.value = doc.items.map(i => ({
        id: _id++, item_code: i.item_code || "", item_name: i.item_name || i.item_code || "",
        description: i.description || "", hsn_code: i.hsn_code || "",
        qty: Math.abs(i.qty || 0), rate: Math.abs(i.rate || 0),
        uom: i.uom || "Nos", discount_percentage: Math.abs(i.discount_percentage || 0),
        discount_amount: Math.abs(i.discount_amount || 0),
        amount: Math.abs(i.amount || 0), tax_code: i.tax_code || i.item_tax_template || "", collapsed: true,
        batch_no: i.batch_no || "", batch_expiry_date: i.batch_expiry_date || "",
      }));
    }
    // Restore taxes from the saved CN
    cnTaxes.value = (doc?.taxes || [])
      .map(t => ({ tax_type: t.account_head || "", description: t.description || "", rate: Number(t.rate || 0) }))
      .filter(t => t.tax_type);
    cnIsInterState.value = detectInterState(doc?.taxes || []);
    if (doc?.cost_center) form.cost_center = doc.cost_center;
  } catch {}
}
async function openView(c) {
  viewDoc.value = c;
  viewOpen.value = true;
  viewTab.value = "details";
  viewLoading.value = true;
  viewItems.value = [];
  viewApplications.value = [];
  viewBalance.value = 0;
  viewReason.value = "";
  try {
    const doc = await apiGet("Sales Invoice", c.name);
    viewItems.value = doc?.items || [];
    viewDoc.value = { ...viewDoc.value, ...doc };
    // Extract reason from remarks: stored as "reason — notes"
    if (doc?.remarks) {
      viewReason.value = doc.remarks.split(" — ")[0].trim();
    }
    if (c.docstatus === 1) {
      const [bal, apps] = await Promise.all([
        apiGET("zoho_books_clone.api.docs.get_credit_note_balance", { credit_note_name: c.name }).catch(() => null),
        apiGET("zoho_books_clone.api.docs.get_credit_note_applications", { credit_note_name: c.name }).catch(() => []),
      ]);
      if (bal) viewBalance.value = flt(bal.balance);
      viewApplications.value = apps || [];
    }
  } catch {}
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
async function fetchItems(q = "") {
  try {
    const f = [["disabled", "=", 0]];
    if (q) f.push(["item_name", "like", "%" + q + "%"]);
    const r = await apiList("Item", { fields: ["name", "item_name", "standard_rate", "stock_uom"], filters: [...f, ["has_variants", "=", 0], ["is_sales_item", "=", 1]], limit: 30, order: "item_name asc" });
    items.value = r.map(x => ({ ...x, label: x.item_name || x.name, value: x.name, rate: x.standard_rate || 0 }));
  } catch { items.value = []; }
}
async function fetchInvoices(q = "") {
  try {
    // Deliberately NOT filtered on outstanding_amount > 0: a Credit Note
    // undoes/adjusts the original sale (return, overcharge, price
    // correction), which is independent of whether the invoice is still
    // owed money — a fully paid invoice is just as valid a CN target as an
    // unpaid one. Filtering on outstanding_amount here would make it
    // structurally impossible to ever issue a CN against a paid invoice.
    const f = [["is_return", "=", 0], ["docstatus", "=", 1]];
    if (form.customer) f.push(["customer", "=", form.customer]);
    if (q) f.push(["name", "like", "%" + q + "%"]);
    const r = await apiList("Sales Invoice", { fields: ["name", "customer", "customer_name", "outstanding_amount", "grand_total"], filters: f, limit: 30 });
    invoices.value = r.map(x => {
      const due = flt(x.outstanding_amount);
      const label = due > 0
        ? `${x.name} · OMR ${Number(due).toLocaleString("en-OM",{minimumFractionDigits:3})} due${x.customer_name ? ` · ${x.customer_name}` : ""}`
        : `${x.name} · Paid${x.customer_name ? ` · ${x.customer_name}` : ""}`;
      return { ...x, label, value: x.name };
    });
  } catch { invoices.value = []; }
}
function onCustomerSelect(_opt) { form.return_against = ""; invoiceSummary.data = null; cnTaxes.value = []; cnIsInterState.value = false; fetchInvoices(""); }
async function onInvoiceSelect(opt) {
  const invName = opt?.value ?? opt;
  invoiceSummary.data = null;
  cnTaxes.value = [];
  if (!invName) return;
  invoiceSummary.loading = true;
  try {
    const [doc, summary] = await Promise.all([
      apiGet("Sales Invoice", invName),
      apiGET("zoho_books_clone.api.docs.get_invoice_apply_summary", { invoice_name: invName }).catch(() => null),
    ]);
    // Store taxes from the parent invoice so saveCN can pass them to the backend
    cnTaxes.value = (doc?.taxes || [])
      .map(t => ({ tax_type: t.account_head || "", description: t.description || "", rate: Number(t.rate || 0) }))
      .filter(t => t.tax_type);
    cnIsInterState.value = detectInterState(doc?.taxes || []);
    if (doc?.items?.length) {
      lines.value = doc.items.map(i => ({
        id: _id++, item_code: i.item_code || "", item_name: i.item_name || i.item_code || "",
        description: i.description || i.item_name || "", hsn_code: i.hsn_code || "",
        qty: Math.abs(i.qty || 1), rate: Math.abs(i.rate || 0),
        uom: i.uom || "Nos", discount_percentage: Math.abs(i.discount_percentage || 0),
        discount_amount: Math.abs(i.discount_amount || 0),
        amount: Math.round(Math.abs(i.qty || 1) * Math.abs(i.rate || 0) * 100) / 100,
        tax_code: i.tax_code || i.item_tax_template || "", collapsed: true,
        batch_no: i.batch_no || "", batch_expiry_date: i.batch_expiry_date || "",
      }));
      toast.success(`Loaded ${doc.items.length} item(s) from ${invName}`);
    }
    if (!form.customer && doc?.customer) form.customer = doc.customer;
    if (summary) invoiceSummary.data = summary;
  } catch {}
  finally { invoiceSummary.loading = false; }
}
async function onItemChange(line) {
  const it = items.value.find(i => i.name === line.item_code || i.value === line.item_code);
  if (it) {
    line.item_name = it.item_name || it.name || line.item_code;
    line.rate = flt(it.rate || it.standard_rate || 0);
    line.uom = it.stock_uom || "Nos";
    calcLine(line);
  }
  if (line.item_code) {
    try {
      const doc = await apiGet("Item", line.item_code);
      if (doc?.item_name) line.item_name = doc.item_name;
      if (doc?.description && !line.description) line.description = doc.description;
      if (doc?.hsn_code) line.hsn_code = doc.hsn_code;
      if (!flt(line.rate) && doc?.standard_rate) line.rate = flt(doc.standard_rate);
      if (doc?.stock_uom) line.uom = doc.stock_uom;
      if (doc?.tax_code) line.tax_code = doc.tax_code;
      calcLine(line);
    } catch {}
  }
}
function addLine() { lines.value.push(blankLine()); }
function removeLine(id) { if (lines.value.length > 1) lines.value = lines.value.filter(l => l.id !== id); }
function calcLine(l) {
  if (l.discount_percentage > 100) l.discount_percentage = 100;
  if (l.discount_percentage < 0) l.discount_percentage = 0;
  const base = Math.round(flt(l.qty) * flt(l.rate) * 100) / 100;
  const disc = Math.round(base * flt(l.discount_percentage) / 100 * 100) / 100;
  l.discount_amount = disc;
  l.amount = base - disc;
}
async function fetchTaxTemplates() {
  try {
    const co = await resolveCompany();
    const r = await apiList("Account", { fields: ["name"], filters: [["company","=",co],["account_type","=","Tax"],["is_group","=",0]], limit: 1 });
    taxAccountHead.value = r[0]?.name || "";
  } catch {}
  try {
    const templates = await apiList("Tax Template", {
      fields: ["name","template_name","tax_type"], filters: [["disabled","=",0], ["applies_to","in",["Sales","Both"]]], limit: 50
    });
    const withRows = await Promise.all((templates || []).map(async t => {
      try {
        const doc = await apiGet("Tax Template", t.name);
        return { name: t.name, title: t.template_name || t.name, tax_type: t.tax_type || doc?.tax_type || "GST", taxes: doc?.taxes || [] };
      } catch { return { name: t.name, title: t.template_name || t.name, tax_type: t.tax_type || "GST", taxes: [] }; }
    }));
    taxTemplates.value = withRows;
  } catch { taxTemplates.value = []; }
}
async function fetchCostCenters() {
  try {
    const co = await resolveCompany();
    const r = await apiGET("frappe.client.get_list", { doctype: "Cost Center", fields: JSON.stringify(["name"]), filters: JSON.stringify([["disabled","=",0],["company","=",co],["is_group","=",0]]), order_by: "name asc", limit_page_length: 100 }) || [];
    costCenters.value = r.map(c => c.name);
  } catch { costCenters.value = []; }
}
async function submitDraftCN(d) {
  if (!await confirm({ title: "Submit Credit Note", body: `Submit ${d.name}? GL entries will be posted and it cannot be edited.`, okLabel: "Submit" })) return;
  try {
    await apiSubmit("Sales Invoice", d.name);
    toast.success(`${d.name} submitted`);
    viewOpen.value = false;
    await load();
  } catch (e) { toast.error(e.message || "Submit failed"); }
}
async function autoApplyCN(c) {
  if (!canEdit("invoices")) { toast("Read-only access", "error"); return; }
  try {
    const [r, balData] = await Promise.all([
      apiList("Sales Invoice", {
        fields: ["name", "outstanding_amount", "posting_date"],
        filters: [["is_return","=",0],["docstatus","=",1],["customer","=",c.customer],["outstanding_amount",">",0]],
        limit: 50, order: "posting_date asc",
      }),
      apiGET("zoho_books_clone.api.docs.get_credit_note_balance", { credit_note_name: c.name }).catch(() => null),
    ]);
    if (!r.length) { toast.info("No open invoices for this customer"); return; }
    const balance = flt(balData?.balance ?? 0);
    if (balance <= 0) { toast.info("No available credit balance"); return; }
    const oldest = r[0];
    const applyAmt = Math.min(balance, flt(oldest.outstanding_amount));
    if (!await confirm({ title: "Auto-Apply Credit", body: `Apply ${fmtCur(applyAmt)} to ${oldest.name} (oldest open invoice)?`, okLabel: "Apply" })) return;
    await apiPOST("zoho_books_clone.api.docs.apply_credit_note_to_invoice", {
      credit_note: c.name, invoice: oldest.name, amount: applyAmt,
    });
    toast.success(`Applied ${fmtCur(applyAmt)} to ${oldest.name}`);
    await load();
    if (viewDoc.value?.name === c.name) await openView(viewDoc.value);
  } catch (e) { toast.error(e.message || "Auto-apply failed"); }
}
async function writeOffCN(c) {
  if (!canEdit("invoices")) { toast("Read-only access", "error"); return; }
  const balData = await apiGET("zoho_books_clone.api.docs.get_credit_note_balance", { credit_note_name: c.name }).catch(() => null);
  const balance = flt(balData?.balance ?? 0);
  if (balance <= 0) { toast.info("No balance to write off"); return; }
  if (!await confirm({ title: "Write Off Balance", body: `Write off the remaining balance of ${fmtCur(balance)} on ${c.name}? A Journal Entry will be created.`, okLabel: "Write Off" })) return;
  try {
    const r = await apiPOST("zoho_books_clone.api.docs.write_off_credit_note", { credit_note_name: c.name });
    toast.success(`Balance written off — ${r?.journal_entry || "JE created"}`);
    await load();
    if (viewDoc.value?.name === c.name) await openView(viewDoc.value);
  } catch (e) { toast.error(e.message || "Write-off failed"); }
}

async function saveCN(submit) {
  if (!form.customer) {
    return toast.error("Customer is required");
  }

  if (form.reason === "Incentive") {
  const amount = flt(form.incentive_amount || 0);
  const maxAmount = incentiveMaxAmount.value;

  if (!form.return_against) {
    return toast.error(
      "Please select an invoice before entering an incentive"
    );
  }

  if (maxAmount <= 0) {
    return toast.error(
      "The selected invoice has no outstanding amount available for an incentive"
    );
  }

 if (amount <= 0) {
    return toast.error("Incentive amount must be greater than 0");
}

if (amount > maxAmount + 0.01) {
  return toast.error(
    `Incentive amount cannot exceed the outstanding amount of ${fmtCur(maxAmount)}`
  );
}
  }

// Items are required for normal credit notes,
// but NOT for Incentive credit notes.
if (form.reason !== "Incentive") {
    if (!lines.value.some(l => l.item_code && flt(l.qty) > 0)) {
        return toast.error("At least one item is required");
    }
}
  
  drawerSaving.value = true;
  try {
    const itemsPayload = form.reason === "Incentive"
  ? []
  : lines.value
      .filter(l => l.item_code)
      .map(l => ({
        item_code: l.item_code,
        item_name: l.item_name || l.item_code,
        description: l.description,
        hsn_code: l.hsn_code || "",
        qty: flt(l.qty),
        rate: flt(l.rate),
        uom: l.uom || "Nos",
        discount_percentage: flt(l.discount_percentage),
        discount_amount: flt(l.discount_amount),
        amount: flt(l.amount),
        tax_code: l.tax_code || "",
        batch_no: l.batch_no || "",
        batch_expiry_date: l.batch_expiry_date || "",
      }));

    // IMPORTANT: build the tax payload from the CURRENT line items (each
    // taxed by its own tax_code), not the old cnTaxes snapshot inherited from
    // the source invoice — that snapshot was the source invoice's full
    // breakup and stayed the same size no matter how many items got removed
    // here, so it used to apply every original rate against whatever
    // subtotal remained.
    const recomputedTaxes = cnTaxRows.value.map(t => ({ tax_type: t.account_head, description: t.description, rate: t.rate }));
    const taxPayload = recomputedTaxes.length
      ? recomputedTaxes
      : (cnTaxes.value.length ? cnTaxes.value : cnTaxLines.value.map(tl => {
          const tmpl = taxTemplates.value.find(t => t.name === tl.description);
          const account = tmpl?.taxes?.[0]?.account_head || taxAccountHead.value;
          return { tax_type: account, description: tl.description, rate: tl.rate };
        }));
    const taxesJson = JSON.stringify(
  form.reason === "Incentive" ? [] : taxPayload
);
    if (!editingName.value && submit === 1) {
      // New + submit → backend API which wires GL accounts and CN- naming
      const r = await apiPOST("zoho_books_clone.api.docs.create_credit_note", {
        customer: form.customer,
        against_invoice: form.return_against || "",
        date: form.posting_date,
        reason: form.reason,
        notes: form.notes || "",
        cost_center: form.cost_center || "",
        incentive_amount: form.reason === "Incentive"
          ? flt(form.incentive_amount || 0)
          : 0,
        items: JSON.stringify(itemsPayload),
        taxes: taxesJson,
      });
      toast.success(`Credit Note ${r?.credit_note || ""} submitted`);
    } else {
      // Draft (new or edit) or edit+submit → save_credit_note_draft preserves CN- naming
      const r = await apiPOST("zoho_books_clone.api.docs.save_credit_note_draft", {
        name: editingName.value || "",
        customer: form.customer,
        against_invoice: form.return_against || "",
        date: form.posting_date,
        reason: form.reason,
        notes: form.notes || "",
        cost_center: form.cost_center || "",
        incentive_amount: form.reason === "Incentive"
          ? flt(form.incentive_amount || 0)
          : 0,
        items: JSON.stringify(itemsPayload),
        taxes: taxesJson,
      });
      if (submit) await apiSubmit("Sales Invoice", r?.name || editingName.value);
      toast.success(`Credit Note ${r?.name || ""} ${submit ? "submitted" : "saved as draft"}`);
    }
    drawerOpen.value = false;
    await load();
  } catch (e) { toast.error(e.message || "Failed to save credit note"); }
  finally { drawerSaving.value = false; }
}

// ── Actions ───────────────────────────────────────────────────────────────
async function emailCN(c) {
  await openEmail({
    doctype: "Sales Invoice", name: c.name, docLabel: `Credit Note ${c.name}`,
    getDefaultsEndpoint: "zoho_books_clone.api.docs.get_credit_note_email_defaults",
    sendEndpoint: "zoho_books_clone.api.docs.send_credit_note_email",
    paramKey: "credit_note_name",
    printConfig: { title: "CREDIT NOTE", partyLabel: "Customer", partyField: "customer_name" },
  });
}
async function applyCN(c) {
  if (!canEdit("invoices")) { toast("Read-only access", "error"); return; }
  try {
    // Fetch both invoices and fresh CN balance in parallel
    const [r, balData] = await Promise.all([
      apiList("Sales Invoice", {
        fields: ["name", "outstanding_amount", "grand_total", "posting_date"],
        filters: [["is_return", "=", 0], ["docstatus", "=", 1], ["customer", "=", c.customer], ["outstanding_amount", ">", 0]],
        limit: 50, order: "posting_date desc, creation desc",
      }),
      apiGET("zoho_books_clone.api.docs.get_credit_note_balance", { credit_note_name: c.name }).catch(() => null),
    ]);
    if (!r.length) { toast.info("No open invoices for this customer"); return; }
    const balance = flt(balData?.balance ?? 0);
    if (balance <= 0) { toast.info("No available credit balance on this credit note"); return; }

    // Sort: original invoice (return_against) always first, others by date
    const originInv = c.return_against || "";
    const sorted = [...r].sort((a, b) => {
      if (a.name === originInv) return -1;
      if (b.name === originInv) return 1;
      return 0;
    });

    Object.assign(applyModal, {
      open: true, saving: false, cnName: c.name, balance,
      invoice: "", originInv,
      amount: 0, openInvoices: sorted, summary: null, summaryLoading: false,
    });
  } catch (e) { toast.error(e.message || "Failed to load invoices"); }
}
async function onApplyInvoiceChange() {
  applyModal.summary = null;
  if (!applyModal.invoice) return;
  applyModal.summaryLoading = true;
  try {
    const s = await apiGET("zoho_books_clone.api.docs.get_invoice_apply_summary", { invoice_name: applyModal.invoice });
    applyModal.summary = s;
    // Auto-fill amount = min(credit balance, outstanding)
    applyModal.amount = Math.min(applyModal.balance, flt(s.outstanding));
  } catch (e) {
    toast.error(e.message || "Failed to load invoice details");
  } finally {
    applyModal.summaryLoading = false;
  }
}
async function submitApply() {
  if (!applyModal.invoice || applyModal.amount <= 0) return;
  applyModal.saving = true;
  try {
    const result = await apiPOST("zoho_books_clone.api.docs.apply_credit_note_to_invoice", {
      credit_note: applyModal.cnName,
      invoice: applyModal.invoice,
      amount: applyModal.amount,
    });
    const newOutstanding = result?.invoice_outstanding ?? null;
    const outstandingMsg = newOutstanding !== null
      ? ` · Invoice balance now ${fmtCur(newOutstanding)}`
      : "";
    toast.success(`Applied ${fmtCur(applyModal.amount)} to ${applyModal.invoice}${outstandingMsg}`);

    // Update the openInvoices list in-place so it's accurate if re-opened
    if (newOutstanding !== null) {
      applyModal.openInvoices = applyModal.openInvoices
        .map(i => i.name === applyModal.invoice
          ? { ...i, outstanding_amount: newOutstanding }
          : i
        )
        .filter(i => flt(i.outstanding_amount) > 0);
    }

    applyModal.open = false;
    await load();
    if (viewDoc.value?.name === applyModal.cnName) await openView(viewDoc.value);
  } catch (e) { toast.error(e.message || "Apply failed"); }
  applyModal.saving = false;
}
async function refundCN(c) {
  if (!canEdit("invoices")) { toast.error("Read-only access"); return; }
  const balData = await apiGET("zoho_books_clone.api.docs.get_credit_note_balance", { credit_note_name: c.name }).catch(() => null);
  const balance = flt(balData?.balance ?? 0);
  if (balance <= 0) { toast.info("No available balance to refund"); return; }
  Object.assign(refundModal, { open: true, saving: false, cnName: c.name, balance, amount: balance, mode: "Bank Transfer", reference: "" });
}
async function submitRefund() {
  if (refundModal.amount <= 0) return;
  refundModal.saving = true;
  try {
    await apiPOST("zoho_books_clone.api.docs.refund_credit_note", {
      credit_note_name: refundModal.cnName,
      amount: refundModal.amount,
      refund_mode: refundModal.mode,
      reference_no: refundModal.reference,
    });
    toast.success(`Refunded ${fmtCur(refundModal.amount)} from ${refundModal.cnName}`);
    refundModal.open = false;
    await load();
    if (viewDoc.value?.name === refundModal.cnName) await openView(viewDoc.value);
  } catch (e) { toast.error(e.message || "Refund failed"); }
  refundModal.saving = false;
}
async function cancelCN(c) {
  if (!canEdit("invoices")) { toast("Read-only access", "error"); return; }
  if (!await confirm({ title: "Cancel Credit Note", body: `Cancel ${c.name}? The against invoice's outstanding will be restored.`, okLabel: "Cancel CN" })) return;
  try {
    await apiPOST("zoho_books_clone.api.docs.cancel_credit_note", { name: c.name });
    toast.success("Credit Note cancelled — invoice outstanding restored");
    await load();
    if (viewDoc.value?.name === c.name) {
      const fresh = list.value.find(x => x.name === c.name);
      if (fresh) await openView(fresh); else viewOpen.value = false;
    }
  } catch (e) { toast.error(e.message || "Cancel failed"); }
}
async function deleteCN(c) {
  if (!canDelete("invoices")) { toast("Not permitted", "error"); return; }
  if (!await confirm({ title: "Delete Credit Note", body: `Permanently delete ${c.name}?`, okLabel: "Delete" })) return;
  try {
    await apiDelete("Sales Invoice", c.name);
    toast.success("Credit Note deleted");
    viewOpen.value = false; await load();
  } catch (e) { toast.error(e.message || "Delete failed"); }
}

// ── Bulk ──────────────────────────────────────────────────────────────────
async function bulkDelete() {
  if (!canDelete("invoices")) { toast("Not permitted", "error"); return; }
  const drafts = sorted.value.filter(c => selected.value.has(c.name) && c.docstatus === 0);
  if (!drafts.length) { toast.info("No draft credit notes selected"); return; }
  if (!await confirm({ title: "Delete Drafts", body: `Delete ${drafts.length} draft credit note(s)?`, okLabel: "Delete" })) return;
  for (const c of drafts) { try { await apiDelete("Sales Invoice", c.name); } catch {} }
  selected.value = new Set();
  toast.success(`Deleted ${drafts.length} draft(s)`);
  await load();
}
async function bulkEmail() {
  if (!canEdit("invoices")) { toast("Read-only access", "error"); return; }
  const subs = sorted.value.filter(c => selected.value.has(c.name) && c.docstatus === 1);
  if (!subs.length) { toast.info("No submitted credit notes selected"); return; }
  let sent = 0;
  for (const c of subs) {
    const ok = await openEmail({
      doctype: "Sales Invoice", name: c.name, docLabel: `Credit Note ${c.name}`,
      getDefaultsEndpoint: "zoho_books_clone.api.docs.get_credit_note_email_defaults",
      sendEndpoint: "zoho_books_clone.api.docs.send_credit_note_email",
      paramKey: "credit_note_name",
      printConfig: { title: "CREDIT NOTE", partyLabel: "Customer", partyField: "customer_name" },
    });
    if (ok) sent++;
  }
  if (sent) toast.success(`Emailed ${sent} credit note(s)`);
}

function exportCSV() {
  // Export selected rows if any are selected; otherwise export the full filtered view.
  const rows = selected.value.size
    ? sorted.value.filter(c => selected.value.has(c.name))
    : sorted.value;
  if (!rows.length) return;
  const head = ["Credit Note","Customer","Date","Against Invoice","Status","Amount","Available Balance"];
  const esc = v => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const out = [head.map(esc).join(",")];
  for (const c of rows) {
    out.push([c.name, c.customer_name || c.customer, c.posting_date, c.return_against || "",
      statusLabel(c), Math.abs(flt(c.grand_total)).toFixed(2), balanceFor(c.name) === null ? "Unknown" : balanceFor(c.name).toFixed(2)
    ].map(esc).join(","));
  }
  const blob = new Blob(["﻿" + out.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `credit_notes_${todayStr()}.csv`;
  a.click(); URL.revokeObjectURL(url);
  toast.success(`CSV exported — ${rows.length} note(s)`);
}

onMounted(async () => {
  await load();
  apiList("UOM", { fields: ["name"], order: "name asc", limit: 200 })
    .then(r => { if (r && r.length) uomList.value = r.map(u => u.name); })
    .catch(() => {});
  useOpenFromQuery({
    route,
    openByName: (n) => openView(list.value.find(x => x.name === n) || { name: n }),
  });
});
</script>

<style scoped>
/* ── Drawer slide-in transition ── */
.cn-drawer {
  position: fixed;
  top: 0; right: -620px; bottom: 0;
  width: 620px; max-width: 96vw;
  background: #fff;
  box-shadow: -12px 0 32px rgba(15,23,42,.12);
  z-index: 9001;
  display: flex; flex-direction: column;
  transition: right .24s cubic-bezier(.32,.72,0,1);
}
.cn-drawer.open { right: 0; }
.cn-view-drawer { width: 625px; right: -625px; }
.cn-view-drawer.open { right: 0; }
.inv-view-head-cn{
  display: flex;
    justify-content: space-between;
    width: -webkit-fill-available;
}
/* ── Body tray for add-cards ── */
.cn-dbody { background: #f0f4f8; padding: 14px; display: flex; flex-direction: column; gap: 0; }

/* add-card inside cn-dbody */
.cn-dbody .add-card {
  background: #fff;
  border: 1px solid #e3e8ef;
  border-radius: 10px;
  margin-bottom: 10px;
  box-shadow: 0 1px 3px rgba(15,23,42,.04);
}
.cn-dbody .add-card:last-child { margin-bottom: 0; }

.cn-dbody .add-card-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #e8ecf0;
  cursor: pointer; user-select: none;
  border-radius: 10px 10px 0 0;
}
.cn-dbody .add-card-title {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; font-weight: 700; color: #1a1a2e;
}
.cn-dbody .add-card-title-icon {
  width: 20px; height: 20px;
  display: flex; align-items: center; justify-content: center;
  color: #dc2626; flex-shrink: 0;
}
.cn-dbody .add-card-chevron {
  color: #9ca3af; transition: transform .2s; display: inline-flex;
}
.cn-dbody .add-card-chevron.collapsed { transform: rotate(-90deg); }
.cn-dbody .add-card-body { padding: 16px; }
.cn-dbody .add-card-body.collapsed { display: none; }

/* Line count badge in items card header */
.cn-lines-badge {
  font-size: 11.5px; font-weight: 600;
  color: #374151; background: #f3f4f6;
  border: 1px solid #e5e7eb;
  border-radius: 5px; padding: 2px 8px;
}
.cn-dheader-left { display: flex; align-items: flex-start; gap: 12px; }
.cn-dheader-ico {
  width: 38px; height: 38px; border-radius: 10px;
  background: #fff; border: 1px solid rgba(220,38,38,.22);
  display: inline-flex; align-items: center; justify-content: center;
  color: #dc2626; flex-shrink: 0;
}
.cn-dheader-ico.edit { color: #ca8a04; border-color: rgba(202,138,4,.25); }

/* ── Field helpers ── */
.cn-field { display: flex; flex-direction: column; gap: 4px; }

/* ── Items line table ── */
.cn-items-table {
  display: flex; flex-direction: column;
  border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden;
}
.cn-items-head {
  display: grid;
  grid-template-columns: 2fr 2fr 80px 100px 100px 32px;
  gap: 8px; background: #f9fafb; padding: 8px 12px;
  font-size: 11.5px; font-weight: 600; color: #374151;
}
.cn-items-row {
  display: grid;
  grid-template-columns: 2fr 2fr 80px 100px 100px 32px;
  gap: 8px; padding: 8px 12px;
  border-top: 1px solid #f3f4f6; align-items: center;
}
.cn-total-row { display: flex; justify-content: space-between; gap: 16px; font-size: 13px; color: #374151; padding: 8px 0; }
.cn-total-row.grand { font-weight: 700; font-size: 15px; color: #111827; border-top: 2px solid #e5e7eb; padding-top: 10px; }

/* ── Form totals (items card footer) ── */
.cn-form-totals {
  padding: 6px 16px 14px;
  border-top: 1px solid #f0f2f5;
  background: #fafbfc;
  border-bottom-left-radius: 8px;
  border-bottom-right-radius: 8px;
}
.cn-tax-note {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 11.5px; color: #6b7280;
  background: #f0f9ff; border: 1px solid #bae6fd;
  border-radius: 5px; padding: 4px 9px;
  margin-bottom: 8px;
}
.cn-tax-row { color: #6b7280 !important; font-size: 12.5px !important; }
.cn-grand-total-row {
  font-size: 15px !important; font-weight: 800 !important;
  color: #7f1d1d !important;
  border-top: 2px solid #fecaca !important;
  padding-top: 8px !important; margin-top: 4px !important;
}

/* ── View panel header ── */
.cn-view-header-fixed {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}
.cn-view-head-left { display: flex; flex-direction: column; gap: 2px; }
.cn-view-head-right { display: flex; flex-direction: column; align-items: flex-end; gap: 6px; flex-shrink: 0; }
.cn-view-amount { font-size: 22px; font-weight: 800; color: #1a1a2e; line-height: 1; }
.cn-vclose-fixed {
  flex-shrink: 0;
  margin-top: 2px;
}

/* ── View drawer footer ── */
.cn-view-footer {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid #e5e7eb;
  background: #f8fafc;
}
/* Primary row: stacks of action buttons */
.cn-vf-primary {
  display: flex;
  flex-wrap: nowrap;
  gap: 8px;
}
.cn-vf-btn {
  flex: 1;
  min-width: fit-content;
  padding: 9px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  white-space: nowrap;
}
.cn-vf-btn-submit  { background: #2563eb; color: #fff; }
.cn-vf-btn-apply   { background: #2563eb; color: #fff; }
.cn-vf-btn-auto    { background: #fff; color: #374151; border: 1px solid #d1d5db; }
.cn-vf-btn-refund  { background: #fff; color: #374151; border: 1px solid #d1d5db; }
.cn-vf-btn-outline { background: #fff; color: #374151; border: 1px solid #d1d5db; }
/* Secondary row: compact icon+label buttons */
.cn-vf-secondary {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.cn-vf-sec-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 11px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  background: #fff;
  border: 1px solid #e5e7eb;
  color: #374151;
  white-space: nowrap;
}
.cn-vf-sec-btn:hover { background: #f3f4f6; }
.cn-vf-sec-danger { color: #dc2626; border-color: #fecaca; }
.cn-vf-sec-danger:hover { background: #fff1f2; }

/* Mobile overrides for the view drawer */
@media (max-width: 768px) {
  /* ── Both add/edit drawer and view drawer go full-width ── */
  .cn-drawer {
    width: 100vw !important;
    right: -100vw !important;
    max-width: 100vw;
  }
  .cn-drawer.open { right: 0 !important; }
  .cn-view-drawer {
    width: 100vw !important;
    right: -100vw !important;
    max-width: 100vw;
  }
  .cn-view-drawer.open { right: 0 !important; }
  .cn-vf-btn { flex: unset; width: 100%; }
  .cn-vf-secondary { flex-wrap: wrap; gap: 6px; }
  .cn-vf-sec-btn { flex: 1; justify-content: center; }
  /* KPI grid on mobile */
  :deep(.bk-kpi-grid),
  :deep(.bk-kpi-grid-4) { display: none !important; }

  /* ── Invoice summary: 2×2 grid on mobile instead of 4-col ── */
  .cn-summary-grid {
    grid-template-columns: repeat(2, 1fr) !important;
  }
  /* restore missing right border after col-2 wrap */
  .cn-summary-cell:nth-child(2) { border-right: none; }
  .cn-summary-cell:nth-child(3) {
    border-right: 1px solid #e5e7eb;
    border-top: 1px solid #e5e7eb;
  }
  .cn-summary-cell:nth-child(4) {
    border-right: none;
    border-top: 1px solid #e5e7eb;
  }

  /* ── Footer buttons: stack to full-width on very narrow ── */
  .inv-dfooter {
    flex-wrap: wrap;
    gap: 8px;
  }
  .inv-dfooter > div {
    display: flex;
    gap: 8px;
    flex: 1;
  }
  .add-btn-draft,
  .add-btn-more {
    flex: 1;
  }
}

/* ── Meta/detail 2-col grid ── */
.cn-meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.cn-meta-lbl { font-size: 11px; color: #9ca3af; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 2px; }

/* ── View items table ── */
.cn-view-items { display: flex; flex-direction: column; border: 1px solid #e5e7eb; border-radius: 6px; overflow: hidden; }
.cn-view-items-head {
  display: grid; grid-template-columns: 2fr 110px 70px 90px 100px;
  gap: 8px; background: #f9fafb; padding: 8px 12px;
  font-size: 11px; font-weight: 700; color: #6b7280; text-transform: uppercase;
}
.cn-view-items-row {
  display: grid; grid-template-columns: 2fr 110px 70px 90px 100px;
  gap: 8px; padding: 8px 12px; border-top: 1px solid #f3f4f6;
  align-items: center; font-size: 12.5px;
}
/* Mobile line-item cards */
.cn-view-items--mobile { display: none; flex-direction: column; gap: 8px; }
.cn-vi-card {
  border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden; background: #fff;
}
.cn-vi-card-header {
  display: flex; align-items: center; gap: 8px;
  background: #fafafa; padding: 10px 12px; border-bottom: 1px solid #f0f0f0;
}
.cn-vi-card-num {
  font-size: 11px; font-weight: 800; color: #dc2626; min-width: 20px; flex-shrink: 0;
}
.cn-vi-card-name {
  flex: 1; font-size: 13px; font-weight: 600; color: #111827;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0;
}
.cn-vi-card-amount {
  font-size: 13.5px; font-weight: 700; color: #7f1d1d; flex-shrink: 0;
}
.cn-vi-card-meta {
  display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0;
}
.cn-vi-meta-item {
  display: flex; flex-direction: column; gap: 2px;
  padding: 8px 12px; border-right: 1px solid #f3f4f6;
}
.cn-vi-meta-item:last-child { border-right: none; }
.cn-vi-meta-item--amount { background: #fff8f8; }
.cn-vi-meta-lbl {
  font-size: 10px; font-weight: 700; color: #9ca3af;
  text-transform: uppercase; letter-spacing: .05em;
}
.cn-vi-meta-val { font-size: 12.5px; font-weight: 600; color: #374151; }
.cn-vi-meta-val--amount { color: #7f1d1d; font-weight: 700; }
@media (max-width: 768px) {
  .cn-view-items--desktop { display: none !important; }
  .cn-view-items--mobile { display: flex; }
}
.cn-view-totals {
  margin-top: 8px; border: 1px solid #e5e7eb; border-radius: 6px;
  overflow: hidden; font-size: 12.5px;
}
.cn-vt-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 7px 12px; border-bottom: 1px solid #f3f4f6;
}
.cn-vt-row:last-child { border-bottom: none; }
.cn-vt-lbl { color: #6b7280; }
.cn-vt-val { font-weight: 500; color: #111827; }
.cn-vt-tax { background: #fafafa; }
.cn-vt-tax .cn-vt-lbl { color: #4b5563; }
.cn-vt-grand {
  background: #fff7f7; border-top: 2px solid #fecaca !important;
}
.cn-vt-grand .cn-vt-lbl { font-weight: 700; color: #374151; }
.cn-vt-grand .cn-vt-val { font-weight: 700; font-size: 13px; }

/* ── Applications grid ── */
.cn-app-head {
  display: grid; grid-template-columns: 1fr 1fr 1fr 1fr;
  gap: 8px; background: #f9fafb; padding: 8px 12px;
  font-size: 11px; font-weight: 700; color: #6b7280; text-transform: uppercase;
  border-radius: 6px 6px 0 0; border: 1px solid #e5e7eb; border-bottom: none;
}
.cn-app-row {
  display: grid; grid-template-columns: 1fr 1fr 1fr 1fr;
  gap: 8px; padding: 8px 12px; border-top: 1px solid #f3f4f6;
  border-left: 1px solid #e5e7eb; border-right: 1px solid #e5e7eb;
  align-items: center; font-size: 12.5px;
}
.cn-app-row:last-child { border-bottom: 1px solid #e5e7eb; border-radius: 0 0 6px 6px; }

/* ── Row action button variants ── */
.cn-act-cell { display: flex; gap: 4px; justify-content: flex-end; cursor: default !important; }
.cn-act-apply { background: #fef2f2; border-color: #dc2626; color: #dc2626; }
.cn-act-apply:hover { background: #fee2e2; color: #b91c1c; }
.cn-act-del:hover { background: #fee2e2; color: #dc2626; border-color: #fca5a5; }
.cn-act-cancel { background: #fff7ed; border-color: #f97316; color: #ea580c; }
.cn-act-cancel:hover { background: #ffedd5; color: #c2410c; border-color: #fb923c; }

/* ── Credit-note status badges ── */
.cn-st-draft     { background: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1; }
.cn-st-issued    { background: #dbeafe; color: #1d4ed8; border: 1px solid #93c5fd; }
.cn-st-partial   { background: #fef3c7; color: #b45309; border: 1px solid #fcd34d; }
.cn-st-applied   { background: #dcfce7; color: #15803d; border: 1px solid #86efac; }
.cn-st-cancelled { background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }
.cn-empty { text-align: center; color: #9ca3af; padding: 48px !important; cursor: default !important; }

/* ── Apply/Refund dialog ── */
.cn-apply-dialog {
  position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
  width: 480px; max-width: 96vw; background: #fff;
  border-radius: 12px; box-shadow: 0 12px 40px rgba(0,0,0,.2);
  z-index: 9100; display: flex; flex-direction: column; overflow: hidden;
}

/* ── Timeline stepper wrapper ── */
.cn-stepper-wrap { background: #fff; border-bottom: 1px solid #e5e7eb; flex-shrink: 0; }

/* ── Applied-to balance summary strip ── */
.cn-applied-summary {
  display: flex; align-items: center; gap: 12px;
  background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 10px;
  padding: 12px 16px; margin-bottom: 16px;
}
.cn-applied-summ-item { display: flex; flex-direction: column; gap: 2px; flex: 1; text-align: center; }
.cn-applied-summ-lbl { font-size: 10.5px; font-weight: 700; color: #9ca3af; text-transform: uppercase; letter-spacing: .05em; }
.cn-applied-summ-val { font-size: 15px; font-weight: 700; color: #111827; }
.cn-applied-summ-sep { font-size: 16px; color: #d1d5db; font-weight: 400; flex-shrink: 0; }

/* ── Invoice-wise allocation groups ── */
.cn-inv-group {
  border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; margin-bottom: 12px;
}
.cn-inv-group-header {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  background: #f9fafb; padding: 10px 14px;
  border-bottom: 1px solid #e5e7eb;
}
.cn-inv-grp-count {
  font-size: 11px; font-weight: 600; color: #6b7280;
  background: #e5e7eb; border-radius: 10px; padding: 1px 7px;
}
.cn-inv-grp-total { font-size: 13px; font-weight: 700; color: #059669; }
.cn-inv-entry-row {
  display: grid; grid-template-columns: 1fr 1.5fr 1fr;
  gap: 8px; padding: 7px 14px; border-top: 1px solid #f3f4f6;
  align-items: center; font-size: 12.5px;
}
.cn-inv-entry-head {
  background: #fff; border-top: none; border-bottom: 1px solid #f3f4f6;
  font-size: 10.5px; font-weight: 700; color: #9ca3af; text-transform: uppercase; letter-spacing: .04em;
}

/* ── Credit-balance pill ── */
.cn-balance-pill {
  display: inline-flex; align-items: center; gap: 6px;
  background: #fef2f2; border: 1px solid #fecaca; color: #991b1b;
  font-size: 12.5px; font-weight: 600; border-radius: 20px;
  padding: 5px 12px; margin-bottom: 14px;
}

/* ── Invoice summary card ── */
.cn-inv-summary {
  border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden;
  margin-bottom: 14px; background: #fafafa;margin-top:14px;
}
.cn-summary-loading {
  display: flex; align-items: center; gap: 8px;
  padding: 14px 16px; font-size: 12.5px; color: #6b7280;
}
.cn-spinner {
  display: inline-block; width: 14px; height: 14px; flex-shrink: 0;
  border: 2px solid #e5e7eb; border-top-color: #6b7280;
  border-radius: 50%; animation: cn-spin 0.7s linear infinite;
}
@keyframes cn-spin { to { transform: rotate(360deg); } }
.cn-summary-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px 8px; border-bottom: 1px solid #e5e7eb;
  background: #f3f4f6;
}
.cn-summary-inv-name { font-size: 12.5px; font-weight: 700; color: #1a1a2e; }
.cn-summary-badge {
  font-size: 10.5px; font-weight: 700; padding: 2px 9px; border-radius: 10px;
  text-transform: uppercase; letter-spacing: .04em;
}
.cn-badge-unpaid    { background: #fef3c7; color: #92400e; }
.cn-badge-overdue   { background: #fee2e2; color: #991b1b; }
.cn-badge-partly-paid { background: #dbeafe; color: #1e40af; }
.cn-badge-paid      { background: #d1fae5; color: #065f46; }
.cn-badge-submitted { background: #e0f2fe; color: #0369a1; }

.cn-summary-grid {
  display: grid; grid-template-columns: repeat(4, 1fr);
  gap: 0;
}
.cn-summary-cell {
  display: flex; flex-direction: column; gap: 3px;
  padding: 10px 12px; border-right: 1px solid #e5e7eb;
}
.cn-summary-cell:last-child { border-right: none; }
.cn-summary-cell-outstanding { background: #fff8f0; }
.cn-summary-label {
  font-size: 10px; font-weight: 700; color: #9ca3af;
  text-transform: uppercase; letter-spacing: .05em;
}
.cn-summary-value { font-size: 13.5px; font-weight: 700; color: #111827; }
.cn-val-paid      { color: #059669; }
.cn-val-credit    { color: #2563eb; }
.cn-val-outstanding { color: #dc2626; }

/* ── Item Cards (expandable per-line) ── */
.cn-item-cards { padding: 12px 14px 4px; display: flex; flex-direction: column; gap: 10px; }
.cn-item-card {
  border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden;
  background: #fff;
}
.cn-item-card:focus-within { box-shadow: 0 0 0 2px rgba(220,38,38,.1); border-color: #fca5a5; }
.cn-item-card-header {
  display: flex; align-items: center; gap: 10px;
  padding: 11px 14px; cursor: pointer; user-select: none;
  background: #fafafa; border-bottom: 1px solid #e5e7eb;
  transition: background .12s;
}
.cn-item-card-header:hover { background: #f3f4f6; }
.cn-item-card-num {
  font-size: 11.5px; font-weight: 800; color: #dc2626; min-width: 22px; flex-shrink: 0;
}
.cn-item-card-title {
  flex: 1; font-size: 12.5px; font-weight: 600; color: #111827;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0;
}
.cn-item-card-subtotal { display: flex; flex-direction: column; align-items: flex-end; gap: 1px; flex-shrink: 0; }
.cn-item-subtotal-label {
  font-size: 9.5px; font-weight: 700; color: #9ca3af;
  text-transform: uppercase; letter-spacing: .06em;
}
.cn-item-amount { font-size: 13px; font-weight: 700; color: #7f1d1d; }
.cn-item-chevron { color: #9ca3af; display: inline-flex; flex-shrink: 0; transition: transform .18s; }
.cn-item-chevron.collapsed { transform: rotate(-90deg); }
.cn-item-rm {
  width: 24px; height: 24px; display: flex; align-items: center; justify-content: center;
  border: 1px solid #fee2e2; border-radius: 5px; background: #fef2f2; color: #dc2626;
  cursor: pointer; flex-shrink: 0; padding: 0; transition: background .12s;
}
.cn-item-rm:hover { background: #fee2e2; }
/* Card body: 2-col layout */
.cn-item-card-body { display: grid; grid-template-columns: 1.1fr 1fr; }
.cn-item-col { display: flex; flex-direction: column; padding: 14px; }
.cn-item-col--left { border-right: 1px solid #f0f2f5; }
.cn-item-col--right { display: flex; flex-direction: column; gap: 10px; }
.cn-item-field { display: flex; flex-direction: column; gap: 4px; }
.cn-item-field label { font-size: 11px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: .04em; }
.cn-item-num-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.cn-item-desc-ta { resize: vertical; min-height: 70px; font-size: 12.5px; }
.cn-field-hint { font-size: 10.5px; color: #9ca3af; text-align: right; }
.cn-mobile-cards { display: none; }
.cn-desktop-table { display: table; }

@media (max-width: 768px) {
  .cn-desktop-table { display: none !important; }
  .cn-mobile-cards { display: flex; flex-direction: column; gap: 0; background: #f8fafc; }
  .cn-mobile-card { background: #fff; border-bottom: 1px solid #e5e7eb; padding: 12px 14px; cursor: pointer; transition: background .12s; }
  .cn-mobile-card:active { background: #f8f9fc; }
  .cn-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .cn-mc-docno { font-size: 12px; font-weight: 700; color: #2563eb; }
  .cn-mc-mid { font-size: 13.5px; font-weight: 600; color: #1a1d23; margin-bottom: 4px; }
  .cn-mc-meta { display: flex; justify-content: space-between; font-size: 12px; color: #868e96; margin-bottom: 4px; }
  .cn-mc-amount { font-weight: 700; color: #7f1d1d; }
  .cn-mc-balance { font-size: 11.5px; color: #868e96; margin-bottom: 8px; }
  .cn-mc-footer { display: flex; gap: 6px; margin-top: 8px; }
  .cn-mc-btn { flex: 1; padding: 6px 10px; border-radius: 7px; font-size: 12px; font-weight: 600; cursor: pointer; background: #f1f5f9; border: 1px solid #e2e8f0; color: #374151; }
  .cn-mc-cancel { background: #fff7ed; border-color: #fde68a; color: #d97706; }
  .cn-mc-apply { background: #eff6ff; border-color: #bfdbfe; color: #2563eb; }
  .cn-mc-danger { background: #fff1f2; border-color: #fecaca; color: #dc2626; }
  .cn-mc--skeleton { pointer-events: none; }
  .cn-mc-shimmer { border-radius: 6px; background: linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size: 200% 100%; animation: cn-shimmer 1.4s infinite; }
  @keyframes cn-shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
  .cn-mc-empty { text-align: center; padding: 32px 16px; color: #868e96; font-size: 13px; }
  /* ── Add-drawer item card: single column on mobile ── */
  .cn-item-card-body { grid-template-columns: 1fr; }
  .cn-item-col--left { border-right: none; border-bottom: 1px solid #f0f2f5; padding-bottom: 10px; }
  .cn-item-col--right { padding-top: 10px; }
  .cn-item-card-header { flex-wrap: nowrap; gap: 6px; padding: 10px 12px; }
  .cn-item-card-num { min-width: 18px; font-size: 11px; }
  .cn-item-card-title { font-size: 12px; }
  .cn-item-subtotal-label { font-size: 9px; }
  .cn-item-amount { font-size: 12px; }
  .cn-item-desc-ta { min-height: 56px; }

  /* ── Add/edit drawer body: tighter padding ── */
  .cn-dbody { padding: 10px; }
  .cn-dbody .add-card-body { padding: 12px; }

  /* ── Customer & Date field grid: single column ── */
  .cn-dbody .inv-fg2 {
    grid-template-columns: 1fr !important;
  }
  .cn-dbody .inv-fg2 .cn-field[style*="grid-column"] {
    grid-column: 1 !important;
  }
}
@media (max-width: 480px) {
  .cn-view-action-btn{display:none;}
}
</style>