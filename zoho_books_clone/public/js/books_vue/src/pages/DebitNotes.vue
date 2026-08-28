<template>
  <div class="list-page">

    <!-- ── Toolbar ── -->
    <div class="sales-toolbar">
      <div class="sales-search">
        <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
        <input v-model="search" placeholder="Search debit notes, vendors…" class="sales-search-input" />
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
        <button class="sales-btn-primary" @click="openNew" :disabled="!$canCreate('bills')" :title="!$canCreate('bills') ? 'Read-only access' : ''"><span v-html="icon('plus',13)"></span> New Debit Note</button>
      </div>
    </div>

    <!-- ── KPI Cards ── -->
    <div class="bk-kpi-grid bk-kpi-grid-4">
      <div class="bk-kpi-card bk-kpi-accent clickable" @click="activeTab='all'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#dbeafe"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.8"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Total Debit Notes</div><div class="bk-kpi-value">{{ list.length }}</div><div class="bk-kpi-trend" :class="dnTrends.total.up?'bk-trend-up':'bk-trend-down'">{{ dnTrends.total.up?'↑':'↓' }} {{ dnTrends.total.pct }}% vs last month</div></div></div></div>
      <div class="bk-kpi-card bk-kpi-success clickable" @click="activeTab='issued'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#dcfce7"><svg width="22" height="22" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="#16a34a" stroke-width="1.8"/><polyline points="7 12.5 10.5 16 17 9" stroke="#16a34a" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Issued</div><div class="bk-kpi-value bk-kpi-green">{{ counts.issued }}</div><div class="bk-kpi-trend" :class="dnTrends.issued.up?'bk-trend-up':'bk-trend-down'">{{ dnTrends.issued.up?'↑':'↓' }} {{ dnTrends.issued.pct }}% vs last month</div></div></div></div>
      <div class="bk-kpi-card"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#fef3c7"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="1.8"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Open Balance</div><div class="bk-kpi-value bk-kpi-amber" style="font-size:18px">{{ fmtCur(summary.openBalance) }}</div><div class="bk-kpi-trend bk-trend-neutral">unapplied debit</div></div></div></div>
      <div class="bk-kpi-card"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#dcfce7"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M16 8h-6a2 2 0 0 0 0 4h4a2 2 0 0 1 0 4H8"/><line x1="12" y1="18" x2="12" y2="21"/><line x1="12" y1="3" x2="12" y2="6"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Total Debit Value</div><div class="bk-kpi-value bk-kpi-green" style="font-size:18px">{{ fmtCur(summary.totalValue) }}</div><div class="bk-kpi-trend" :class="dnTrends.value.up?'bk-trend-up':'bk-trend-down'">{{ dnTrends.value.up?'↑':'↓' }} {{ dnTrends.value.pct }}% vs last month</div></div></div></div>
    </div>
    <div class="bk-stat-grid">
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">This Month</div><div class="bk-stat-value">{{ dnThisMonth.count }}</div></div><div class="bk-stat-icon" style="background:#dbeafe;color:#2563eb"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg></div></div></div>
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">This Month Value</div><div class="bk-stat-value bk-kpi-green" style="font-size:16px">{{ fmtCur(dnThisMonth.value) }}</div></div><div class="bk-stat-icon" style="background:#dcfce7;color:#16a34a"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/></svg></div></div></div>
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">Draft</div><div class="bk-stat-value">{{ counts.draft }}</div></div><div class="bk-stat-icon" style="background:#f8fafc;color:#6b7280"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></div></div></div>
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">Avg Debit Value</div><div class="bk-stat-value" style="font-size:16px">{{ fmtCur(dnAvg) }}</div></div><div class="bk-stat-icon" style="background:#e5e7eb;color:#6b7280"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg></div></div></div>
    </div>

    <!-- ── Bulk action bar ── -->
    <BulkActionBar :count="selected.size" @clear="selected=new Set()">
      <button @click="bulkEmail" :disabled="!$canEdit('bills')" :title="!$canEdit('bills') ? 'Read-only access' : ''"><span v-html="icon('mail',13)"></span> Send Email</button>
      <button class="bab-danger" @click="bulkDelete" :disabled="!$canDelete('bills')" :title="!$canDelete('bills') ? 'Not permitted' : ''">Delete Drafts</button>
      <button @click="exportCSV"><span v-html="icon('download',13)"></span> Export CSV</button>
    </BulkActionBar>

    <!-- ── Table ── -->
    <div class="inv-table-wrap">
      <table class="inv-table dn-desktop-table">
        <thead>
          <tr>
            <th style="width:32px"><input type="checkbox" @change="toggleAll" :checked="allChecked" /></th>
            <th @click="sortBy('name')" class="sortable">Debit Note # <span v-html="sortArrow('name')"></span></th>
            <th @click="sortBy('supplier_name')" class="sortable">Vendor <span v-html="sortArrow('supplier_name')"></span></th>
            <th @click="sortBy('posting_date')" class="sortable">Date <span v-html="sortArrow('posting_date')"></span></th>
            <th>Against Bill</th>
            <th>Status</th>
            <th @click="sortBy('grand_total')" class="sortable ta-r">Amount <span v-html="sortArrow('grand_total')"></span></th>
            <th class="ta-r">Available</th>
            <th style="width:120px;text-align:center">Actions</th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 6" :key="n"><td colspan="9"><div class="shimmer"></div></td></tr>
          </template>
          <template v-else>
            <tr v-for="d in paged" :key="d.name" class="inv-row" :class="{selected:selected.has(d.name)}">
              <td class="td-check"><input type="checkbox" :checked="selected.has(d.name)" @change="toggle(d.name)" /></td>
              <td class="td-id" @click="openView(d)"><DocLink doctype="Debit Note" :name="d.name" /></td>
              <td class="td-customer" @click="openView(d)">{{ d.supplier_name || d.supplier || '—' }}</td>
              <td class="td-date text-muted mono-sm" @click="openView(d)">{{ fmtDate(d.posting_date) }}</td>
              <td class="td-against text-muted mono-sm" @click="openView(d)">{{ d.return_against||'—' }}</td>
              <td class="td-status" @click="openView(d)"><span class="inv-status-badge" :class="statusCls(d)">{{ statusLabel(d) }}</span></td>
              <td class="td-amount ta-r mono-sm" @click="openView(d)" style="color:#7c2d12">{{ fmtCur(Math.abs(d.grand_total||0)) }}</td>
              <td class="td-balance ta-r mono-sm" @click="openView(d)">
                <span v-if="d.docstatus===1 && balanceFor(d.name)===null" class="text-muted" title="Couldn't load balance — refresh to retry">Unknown</span>
                <span v-else-if="d.docstatus===1" :class="balanceFor(d.name)>0?'text-danger':'text-success'">{{ fmtCur(balanceFor(d.name)) }}</span>
                <span v-else class="text-muted">—</span>
              </td>
              <td class="td-actions dn-act-cell">
                <button class="inv-act-btn" @click="openView(d)" title="View"><span v-html="icon('eye',13)"></span></button>
                <button v-if="d.docstatus===0" class="inv-act-btn" :disabled="!$canEdit('bills')" :title="!$canEdit('bills') ? 'Read-only access' : 'Edit'" @click="openEdit(d)"><span v-html="icon('edit',13)"></span></button>
                <button v-if="d.docstatus===1 && balanceFor(d.name)>0" class="inv-act-btn dn-act-apply" :disabled="!$canEdit('bills')" :title="!$canEdit('bills') ? 'Read-only access' : 'Apply to Bill'" @click="applyDN(d)">↳</button>
                <button v-if="d.docstatus===1" class="inv-act-btn dn-act-cancel" :disabled="!$canDelete('bills')" :title="!$canDelete('bills') ? 'Not permitted' : 'Cancel Debit Note'" @click="cancelDN(d)"><span v-html="icon('x',12)"></span></button>
                <button v-if="d.docstatus===0 || d.docstatus===2" class="inv-act-btn dn-act-del" :disabled="!$canDelete('bills')" :title="!$canDelete('bills') ? 'Not permitted' : 'Delete'" @click="deleteDN(d)"><span v-html="icon('trash',13)"></span></button>
              </td>
            </tr>
            <tr v-if="!sorted.length"><td colspan="9" class="dn-empty">No debit notes match</td></tr>
          </template>
        </tbody>
      </table>

      <!-- Mobile cards (shown at ≤768px) -->
      <div class="dn-mobile-cards">
        <template v-if="loading">
          <div v-for="n in 5" :key="n" class="dn-mobile-card dn-mc--skeleton">
            <div class="dn-mc-shimmer" style="height:13px;width:55%;margin-bottom:8px"></div>
            <div class="dn-mc-shimmer" style="height:11px;width:40%;margin-bottom:6px"></div>
            <div class="dn-mc-shimmer" style="height:11px;width:65%"></div>
          </div>
        </template>
        <div v-else-if="!sorted.length" class="dn-mc-empty">
          <div style="font-size:32px;margin-bottom:8px">📋</div>
          <div>No debit notes found</div>
        </div>
        <template v-else>
          <div v-for="d in paged" :key="d.name" class="dn-mobile-card" @click="openView(d)">
            <div class="dn-mc-top">
              <span class="dn-mc-docno">{{ d.name }}</span>
              <span class="inv-status-badge" :class="statusCls(d)">{{ statusLabel(d) }}</span>
            </div>
            <div class="dn-mc-mid">{{ d.supplier_name || d.supplier || '—' }}</div>
            <div class="dn-mc-meta">
              <span>{{ fmtDate(d.posting_date) }}</span>
              <span class="dn-mc-amount">{{ fmtCur(Math.abs(d.grand_total || 0)) }}</span>
            </div>
            <div v-if="d.docstatus===1 && balanceFor(d.name)>0" class="dn-mc-balance">Balance: {{ fmtCur(balanceFor(d.name)) }}</div>
            <div class="dn-mc-footer">
              <button class="dn-mc-btn" @click.stop="openView(d)">View</button>
              <button v-if="d.docstatus===0" class="dn-mc-btn" :disabled="!$canEdit('bills')" @click.stop="openEdit(d)">Edit</button>
              <button v-if="d.docstatus===1&&balanceFor(d.name)>0" class="dn-mc-btn dn-mc-apply" :disabled="!$canEdit('bills')" @click.stop="applyDN(d)">Apply</button>
              <button v-if="d.docstatus===0||d.docstatus===2" class="dn-mc-btn dn-mc-danger" :disabled="!$canDelete('bills')" @click.stop="deleteDN(d)">Delete</button>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- ── Pagination ── -->
    <div v-if="!loading && sorted.length" style="padding:12px 4px 4px">
      <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="sorted.length" />
    </div>

    <!-- ── Create/Edit Drawer ── -->
    <div v-if="drawerOpen" class="inv-drawer-bg" @click.self="drawerOpen=false"></div>
    <div class="dn-drawer" :class="{open:drawerOpen}">

      <!-- Header -->
      <div class="inv-dh">
        <div class="dn-dheader-left">
          <div class="dn-dheader-ico" :class="editingName?'edit':''">
            <span v-html="icon(editingName?'edit':'file',18)"></span>
          </div>
          <div>
            <div class="inv-dh-title">{{ editingName ? 'Edit Debit Note' : 'New Debit Note' }}</div>
            <div class="inv-dh-sub">{{ editingName ? editingName : 'Issue a debit against a vendor bill' }}</div>
          </div>
        </div>
        <button class="inv-dclose" @click="drawerOpen=false"><span v-html="icon('x',16)"></span></button>
      </div>

      <div class="inv-dbody dn-dbody">

        <!-- ══ CARD 1: Vendor & Date ══ -->
        <div class="add-card">
          <div class="add-card-header" @click="dnCollapsed.vendor=!dnCollapsed.vendor">
            <div class="add-card-title">
              <span class="add-card-title-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              </span>
              Vendor &amp; Date
            </div>
            <span class="add-card-chevron" :class="{collapsed:dnCollapsed.vendor}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
          </div>
          <div class="add-card-body" :class="{collapsed:dnCollapsed.vendor}">
            <div class="inv-fg inv-fg2">
              <div class="dn-field" style="grid-column:1/-1">
                <label class="inv-lbl">Vendor <span class="inv-req">*</span></label>
                <SearchableSelect v-model="form.supplier" :options="vendors" placeholder="Select vendor…"
                  :createable="true" createDoctype="Supplier"
                  @search="fetchVendors" @select="onVendorSelect" />
              </div>
              <div class="dn-field">
                <label class="inv-lbl">Date <span class="inv-req">*</span></label>
                <input v-model="form.posting_date" type="date" class="inv-fi" />
              </div>
              <div class="dn-field">
                <label class="inv-lbl">Against Bill</label>
                <SearchableSelect v-model="form.return_against" :options="bills"
                  placeholder="Select bill (optional)…" @search="fetchBills" @select="onBillSelect" />
              </div>

              <!-- Bill summary shown after selecting Against Bill -->
              <div v-if="form.return_against" class="dn-field" style="grid-column:1/-1">
                <div class="dn-inv-summary">
                  <div v-if="billSummary.loading" class="dn-summary-loading">
                    <span class="dn-spinner"></span> Loading bill details…
                  </div>
                  <template v-else-if="billSummary.data">
                    <div class="dn-summary-header">
                      <span class="dn-summary-inv-name">{{ form.return_against }}</span>
                      <span class="dn-summary-badge"
                        :class="'dn-badge-' + (billSummary.data.status || 'unpaid').toLowerCase().replace(/\s+/g, '-')">
                        {{ billSummary.data.status }}
                      </span>
                    </div>
                    <div class="dn-summary-grid">
                      <div class="dn-summary-cell">
                        <div class="dn-summary-label">Bill Amount</div>
                        <div class="dn-summary-value">{{ fmtCur(billSummary.data.grand_total) }}</div>
                      </div>
                      <div class="dn-summary-cell">
                        <div class="dn-summary-label">Paid</div>
                        <div class="dn-summary-value dn-val-paid">{{ fmtCur(billSummary.data.total_paid) }}</div>
                      </div>
                      <div class="dn-summary-cell dn-summary-cell-outstanding">
                        <div class="dn-summary-label">Outstanding</div>
                        <div class="dn-summary-value dn-val-outstanding">{{ fmtCur(billSummary.data.outstanding) }}</div>
                      </div>
                    </div>
                  </template>
                </div>
              </div>

              <div class="dn-field">
                <label class="inv-lbl">Reason</label>
                <select v-model="form.reason" class="inv-fi" @change="onReasonChange">
                  <option>Vendor Overcharge</option>
                  <option>Goods Returned</option>
                  <option>Damaged Goods</option>
                  <option>Short Delivery</option>
                  <option>Duplicate Invoice</option>
                  <option>Incentive</option>
                  <option>Other</option>
                </select>
              </div>
              <div class="dn-field">
                <label class="inv-lbl">Cost Center</label>
                <select v-model="form.cost_center" class="inv-fi">
                  <option value="">— Select —</option>
                  <option v-for="cc in costCenters" :key="cc" :value="cc">{{ cc }}</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        
        <!-- ══ CARD 2: Debit Items ══ -->
<!-- ══ CARD 2: Debit Items ══ -->
<div v-if="!isIncentive" class="add-card">
  <div class="add-card-header" @click="dnCollapsed.items=!dnCollapsed.items">
    <div class="add-card-title">
      <span class="add-card-title-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" stroke-width="2">
          <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4z"/>
        </svg>
      </span>
      Debit Items
    </div>

    <div style="display:flex;align-items:center;gap:10px">
      <span class="dn-lines-badge">
        {{ lines.length }} line{{ lines.length !== 1 ? 's' : '' }}
      </span>

      <span class="add-card-chevron" :class="{collapsed:dnCollapsed.items}">
        <svg width="14" height="14" viewBox="0 0 24 24"
          fill="none" stroke="currentColor" stroke-width="2.5">
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </span>
    </div>
  </div>

  <div
    class="add-card-body"
    :class="{collapsed:dnCollapsed.items}"
    style="padding:0"
  >

    <!-- Item cards -->
    <div class="dn-item-cards">

      <div
        v-for="(line, idx) in lines"
        :key="line.id"
        class="dn-item-card"
      >

        <div
          class="dn-item-card-header"
          @click="line.collapsed = !line.collapsed"
        >
          <span class="dn-item-card-num">#{{ idx + 1 }}</span>

          <span class="dn-item-card-title">
            {{ line.item_name || line.item_code || 'Line Item' }}
          </span>

          <div class="dn-item-card-subtotal">
            <span class="dn-item-subtotal-label">SUBTOTAL</span>
            <span class="dn-item-amount">
              {{ fmtCur(line.amount) }}
            </span>
          </div>

          <span
            class="dn-item-chevron"
            :class="{collapsed: line.collapsed}"
          >
            <svg width="14" height="14" viewBox="0 0 24 24"
              fill="none" stroke="currentColor" stroke-width="2.5">
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </span>

          <button
            class="dn-item-rm"
            @click.stop="removeLine(line.id)"
          >
            <span v-html="icon('x', 12)"></span>
          </button>
        </div>

        <div
          class="dn-item-card-body"
          v-show="!line.collapsed"
        >
          <div class="dn-item-col dn-item-col--left">

            <div class="dn-item-field">
              <label>
                Item Name <span class="inv-req">*</span>
              </label>

              <SearchableSelect
                v-model="line.item_code"
                :options="items"
                placeholder="Search item or service"
                :createable="true"
                createDoctype="Item"
                @search="fetchItems"
                @update:modelValue="onItemChange(line)"
              />
            </div>

            <div
              class="dn-item-field"
              style="margin-top:12px"
            >
              <label>Description</label>

              <textarea
                v-model="line.description"
                class="inv-fi dn-item-desc-ta"
                rows="3"
                maxlength="500"
                placeholder="Item description…"
              ></textarea>

              <div class="dn-field-hint">
                {{ (line.description || '').length }}/500
              </div>
            </div>

          </div>

          <div class="dn-item-col dn-item-col--right">

            <div class="dn-item-num-row">

              <div class="dn-item-field">
                <label>HSN/SAC</label>
                <input
                  v-model="line.hsn_code"
                  class="inv-fi"
                  placeholder="e.g. 998314"
                />
              </div>

              <div class="dn-item-field">
                <label>UOM</label>
                <select v-model="line.uom" class="inv-fi">
                  <option
                    v-for="u in uomList"
                    :key="u"
                    :value="u"
                  >
                    {{ u }}
                  </option>
                </select>
              </div>

            </div>

            <div class="dn-item-num-row">

              <div class="dn-item-field">
                <label>Qty</label>
                <input
                  v-model.number="line.qty"
                  type="number"
                  min="0.001"
                  step="0.001"
                  class="inv-fi"
                  @input="calcLine(line)"
                />
              </div>

              <div class="dn-item-field">
                <label>Rate (OMR)</label>
                <input
                  v-model.number="line.rate"
                  type="number"
                  min="0"
                  step="0.01"
                  class="inv-fi"
                  @input="calcLine(line)"
                />
              </div>

            </div>

            <div
              class="dn-item-num-row"
              v-if="line.batch_no"
            >
              <div class="dn-item-field">
                <label>Batch No</label>
                <input
                  :value="line.batch_no"
                  class="inv-fi"
                  disabled
                />
              </div>

              <div
                class="dn-item-field"
                v-if="line.batch_expiry_date"
              >
                <label>Batch Expiry</label>
                <input
                  :value="line.batch_expiry_date"
                  class="inv-fi"
                  disabled
                />
              </div>
            </div>

            <div class="dn-item-num-row">

              <div class="dn-item-field">
                <label>Discount %</label>
                <input
                  v-model.number="line.discount_percentage"
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  class="inv-fi"
                  @input="calcLine(line)"
                />
              </div>

              <div class="dn-item-field">
                <label>Tax Template</label>

                <select
                  v-model="line.tax_code"
                  class="inv-fi"
                >
                  <option value="">— No Tax —</option>

                  <option
                    v-for="t in taxTemplates"
                    :key="t.name"
                    :value="t.name"
                  >
                    {{ t.title || t.name }}
                  </option>
                </select>
              </div>

            </div>

          </div>
        </div>

      </div>
    </div>

    <!-- Add Item -->
    <div style="padding:10px 16px 4px">
      <button
        class="inv-add-line-btn"
        @click="addLine"
      >
        <span v-html="icon('plus',12)"></span>
        Add Item
      </button>
    </div>

    <!-- Normal Debit Note totals -->
    <div class="dn-form-totals">

      <div v-if="dnTaxLines.length" class="dn-tax-note">
        <svg width="12" height="12" viewBox="0 0 24 24"
          fill="none" stroke="currentColor" stroke-width="2.5">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>

        Tax is recalculated live from each item's own Tax Template —
        change an item's template above to update it
      </div>

      <div class="po-totals" style="justify-content:flex-end">
        <div class="po-totals-right" style="min-width:260px">

          <div class="po-total-row">
            <span>Subtotal</span>
            <span>{{ fmtCur(subtotal) }}</span>
          </div>

          <template v-if="dnTaxLines.length">

            <div
              v-for="tl in dnTaxLines"
              :key="tl.description"
              class="po-total-row dn-tax-row"
            >
              <span>
                {{ tl.description }} ({{ tl.rate }}%)
              </span>

              <span>
                {{ fmtCur(tl.amount) }}
              </span>
            </div>

          </template>

          <div
            v-else
            class="po-total-row dn-tax-row"
          >
            <span>Tax</span>
            <span>{{ fmtCur(0) }}</span>
          </div>

        </div>
      </div>

      <div class="po-totals" style="justify-content:flex-end">
        <div class="po-totals-right" style="min-width:260px">

          <div class="po-total-row dn-grand-total-row">
            <span>Total Debit</span>
            <span>{{ fmtCur(displayDebitTotal) }}</span>
          </div>

        </div>
      </div>

    </div>
  </div>
</div>

<!-- ══ INCENTIVE ONLY ══ -->
<div v-if="isIncentive" class="add-card">

  <div class="add-card-header">
    <div class="add-card-title">
      Incentive
    </div>
  </div>

  <div class="add-card-body">

    <div class="dn-field">

      <label class="inv-lbl">
        Incentive Amount
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

      <div class="dn-field-hint">
        Maximum: {{ fmtCur(incentiveMaxAmount) }}
      </div>

      <div
        v-if="incentiveAmount > incentiveMaxAmount"
        style="font-size:12px;color:#dc2626;margin-top:4px"
      >
        Incentive amount cannot exceed the bill amount.
      </div>

      <div
        v-if="incentiveAmount < 0"
        style="font-size:12px;color:#dc2626;margin-top:4px"
      >
        Incentive amount cannot be negative.
      </div>

    </div>

    <!-- Incentive Total -->
    <div
      class="po-totals"
      style="justify-content:flex-end;margin-top:10px"
    >
      <div
        class="po-totals-right"
        style="min-width:260px"
      >

        <div class="po-total-row dn-grand-total-row">
          <span>Total Debit</span>
          <span>{{ fmtCur(displayDebitTotal) }}</span>
        </div>

      </div>
    </div>

  </div>
</div>

        <!-- ══ CARD 3: Notes ══ -->
        <div class="add-card">
          <div class="add-card-header" @click="dnCollapsed.notes=!dnCollapsed.notes">
            <div class="add-card-title">
              <span class="add-card-title-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
              </span>
              Notes
            </div>
            <span class="add-card-chevron" :class="{collapsed:dnCollapsed.notes}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
          </div>
          <div class="add-card-body" :class="{collapsed:dnCollapsed.notes}">
            <textarea v-model="form.notes" rows="3" class="inv-fi" placeholder="Internal note (optional)…" maxlength="500"></textarea>
            <div class="dn-field-hint">{{ (form.notes||'').length }}/500</div>
          </div>
        </div>

      </div>

      <div class="inv-dfooter">
        <button class="form-btn form-btn-outline" @click="drawerOpen=false" :disabled="drawerSaving">Cancel</button>
        <div>
          <button class="add-btn-draft" style="margin-right:5px" :disabled="drawerSaving || !(editingName ? $canEdit('bills') : $canCreate('bills'))" :title="!(editingName ? $canEdit('bills') : $canCreate('bills')) ? 'Read-only access' : ''" @click="saveDN(0)"><span v-html="icon('save',13)"></span> {{ drawerSaving?'Saving…':'Save Draft' }}</button>
          <button class="add-btn-more" :disabled="drawerSaving || !(editingName ? $canEdit('bills') : $canCreate('bills'))" :title="!(editingName ? $canEdit('bills') : $canCreate('bills')) ? 'Read-only access' : ''" @click="saveDN(1)"><span v-html="icon('check',13)"></span> {{ drawerSaving?'Saving…':'Submit' }}</button>
        </div>
      </div>
    </div>

    <!-- ── View Drawer ── -->
    <div v-if="viewOpen" class="inv-drawer-bg" @click.self="viewOpen=false"></div>
    <div class="dn-drawer dn-view-drawer" :class="{open:viewOpen}">
      <template v-if="viewDoc">
        <div class="inv-view-header dn-view-header">
          <div class="dn-view-head-body">
            <div class="dn-view-head-left">
              <div class="inv-view-number">{{ viewDoc.name }}</div>
              <div class="inv-view-subtitle">{{ viewDoc.supplier_name||viewDoc.supplier }}</div>
            </div>
            <div class="dn-view-head-right">
              <span class="inv-hdr-badge" :class="statusCls(viewDoc)">{{ statusLabel(viewDoc) }}</span>
              <div class="dn-view-amount">{{ fmtCur(Math.abs(viewDoc.grand_total||0)) }}</div>
            </div>
          </div>
          <button class="dn-vclose" @click="viewOpen=false"><span v-html="icon('x',15)"></span></button>
        </div>

        <div class="dn-stepper-wrap"><TimelineStepper :steps="timelineSteps" /></div>

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
              voucher-type="Purchase Invoice"
              :voucher-no="viewDoc.name"
              label="Debit Note"
              :currency="viewDoc.currency || 'OMR'"
            />
          </template>
          <template v-if="viewTab==='details'">
            <div class="dn-meta-grid">
              <div><div class="dn-meta-lbl">Date</div><div class="mono-sm">{{ fmtDate(viewDoc.posting_date) }}<template v-if="viewDoc.posting_time"> {{ viewDoc.posting_time }}</template></div></div>
              <div><div class="dn-meta-lbl">Return Against</div>
                <DocLink v-if="viewDoc.return_against" doctype="Purchase Invoice" :name="viewDoc.return_against" />
                <span v-else class="mono-sm text-muted">—</span>
              </div>
              <div><div class="dn-meta-lbl">Total Debit</div><div class="mono-sm" style="color:#7c2d12;font-weight:600">{{ fmtCur(Math.abs(viewDoc.grand_total||0)) }}</div></div>
              <div><div class="dn-meta-lbl">Available Balance</div>
                <div class="mono-sm" :class="viewBalance>0?'text-danger':'text-success'">{{ fmtCur(viewBalance) }}</div>
              </div>
              <div v-if="viewReason"><div class="dn-meta-lbl">Reason</div>
                <div class="mono-sm" style="color:#374151">{{ viewReason }}</div>
              </div>
              <div v-if="viewDoc.cost_center"><div class="dn-meta-lbl">Cost Center</div>
                <div class="mono-sm" style="color:#059669">{{ viewDoc.cost_center }}</div>
              </div>
              <div v-if="viewDoc.remarks"><div class="dn-meta-lbl">Notes</div>
                <div class="mono-sm" style="color:#6b7280;font-style:italic">{{ viewDoc.remarks }}</div>
              </div>
            </div>

            <div v-if="viewLoading" style="text-align:center;padding:24px;color:#6b7280;font-size:13px">Loading…</div>
            <template v-else-if="viewReason === 'Incentive'">
              <div class="inv-sec-lbl">Incentive</div>
              <div style="padding:16px;background:#f9fafb;border-radius:8px;color:#374151;font-size:13px">
                This is a goodwill incentive debit of {{ fmtCur(Math.abs(viewDoc.grand_total||0)) }} issued against
                <DocLink doctype="Purchase Invoice" :name="viewDoc.return_against" /> — not tied to specific line items.
              </div>
            </template>
            <template v-else-if="viewItems.length">
              <div class="inv-sec-lbl">Line Items</div>
              <!-- Desktop table -->
              <div class="dn-view-items dn-view-items--desktop">
                <div class="dn-view-items-head"><span>Item</span><span>HSN/SAC</span><span>Batch No</span><span>UOM</span><span class="ta-r">Qty</span><span class="ta-r">Rate</span><span class="ta-r">Amount</span></div>
                <div v-for="it in viewItems" :key="it.name" class="dn-view-items-row">
                  <span>{{ it.item_name||it.item_code }}</span>
                  <span class="mono-sm text-muted">{{ it.hsn_code||'—' }}</span>
                  <span class="mono-sm text-muted">{{ it.batch_no||'—' }}</span>
                  <span class="mono-sm text-muted">{{ it.uom||'—' }}</span>
                  <span class="ta-r mono-sm">{{ Math.abs(it.qty||0) }}</span>
                  <span class="ta-r mono-sm">{{ fmtCur(it.rate) }}</span>
                  <span class="ta-r mono-sm" style="font-weight:600">{{ fmtCur(Math.abs(it.amount||0)) }}</span>
                </div>
              </div>
              <!-- Mobile cards -->
              <div class="dn-view-items--mobile">
                <div v-for="(it, idx) in viewItems" :key="it.name" class="dn-vi-card">
                  <div class="dn-vi-card-header">
                    <span class="dn-vi-card-num">#{{ idx + 1 }}</span>
                    <span class="dn-vi-card-name">{{ it.item_name||it.item_code }}</span>
                    <span class="dn-vi-card-amount">{{ fmtCur(Math.abs(it.amount||0)) }}</span>
                  </div>
                  <div v-if="it.batch_no" class="dn-vi-batch-line">Batch: <strong>{{ it.batch_no }}</strong></div>
                  <div class="dn-vi-card-meta">
                    <div class="dn-vi-meta-item">
                      <span class="dn-vi-meta-lbl">Qty</span>
                      <span class="dn-vi-meta-val">{{ Math.abs(it.qty||0) }}</span>
                    </div>
                    <div class="dn-vi-meta-item">
                      <span class="dn-vi-meta-lbl">Rate</span>
                      <span class="dn-vi-meta-val">{{ fmtCur(it.rate) }}</span>
                    </div>
                    <div class="dn-vi-meta-item dn-vi-meta-item--amount">
                      <span class="dn-vi-meta-lbl">Amount</span>
                      <span class="dn-vi-meta-val dn-vi-meta-val--amount">{{ fmtCur(Math.abs(it.amount||0)) }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <!-- Tax + Grand total block -->
              <div class="dn-view-totals" v-if="viewDoc.taxes?.length">
                <div v-for="(tx, i) in (viewDoc.taxes||[]).filter(t=>flt(t.tax_amount)||flt(t.rate))" :key="i" class="dn-vt-row dn-vt-tax">
                  <span class="dn-vt-lbl">{{ tx.description||tx.account_head }} ({{ tx.rate }}%)</span>
                  <span class="dn-vt-val">{{ fmtCur(Math.abs(tx.tax_amount||0)) }}</span>
                </div>
                <div class="dn-vt-row dn-vt-grand">
                  <span class="dn-vt-lbl">Grand Total</span>
                  <span class="dn-vt-val" style="color:#7c2d12">{{ fmtCur(Math.abs(viewDoc.grand_total||0)) }}</span>
                </div>
              </div>
            </template>
          </template>

          <template v-if="viewTab==='applied'">
            <div v-if="viewLoading" style="text-align:center;padding:24px;color:#6b7280;font-size:13px">Loading…</div>
            <template v-else>
              <!-- Balance strip -->
              <div class="dn-balance-strip">
                <div class="dn-bs-cell">
                  <div class="dn-bs-lbl">Total Debit</div>
                  <div class="dn-bs-val">{{ fmtCur(Math.abs(viewDoc.grand_total||0)) }}</div>
                </div>
                <div class="dn-bs-sep">−</div>
                <div class="dn-bs-cell">
                  <div class="dn-bs-lbl">Applied</div>
                  <div class="dn-bs-val">{{ fmtCur(appliedTotal) }}</div>
                </div>
                <div class="dn-bs-sep">=</div>
                <div class="dn-bs-cell dn-bs-cell--avail">
                  <div class="dn-bs-lbl">Available</div>
                  <div class="dn-bs-val dn-bs-val--avail">{{ fmtCur(viewBalance) }}</div>
                </div>
              </div>

              <div v-if="groupedApplications.length">
                <div v-for="grp in groupedApplications" :key="grp.bill" class="dn-app-group">
                  <div class="dn-app-group-header">
                    <DocLink doctype="Purchase Invoice" :name="grp.bill" />
                    <span class="dn-app-group-total">{{ fmtCur(grp.total) }}</span>
                  </div>
                  <div v-for="a in grp.entries" :key="a.payment_entry" class="dn-app-group-row">
                    <span class="mono-sm text-muted" style="font-size:11px">{{ fmtDate(a.date) }}</span>
                    <DocLink :doctype="a.ref_doctype||'Journal Entry'" :name="a.payment_entry" />
                    <span class="ta-r mono-sm" style="font-weight:600;color:#059669">{{ fmtCur(a.amount) }}</span>
                  </div>
                </div>
              </div>
              <div v-else style="text-align:center;padding:24px;color:#9ca3af;font-size:13px">
                No applications yet.
                <div v-if="viewBalance>0 && viewDoc.docstatus===1" style="margin-top:8px">
                  <button class="add-btn-draft" :disabled="!$canEdit('bills')" :title="!$canEdit('bills') ? 'Read-only access' : ''" @click="applyDN(viewDoc)" style="font-size:12px;padding:6px 12px">↳ Apply to Bill</button>
                </div>
              </div>
            </template>
          </template>
        </div>

        <div class="dn-view-footer">
          <!-- Primary actions row -->
          <div class="dn-vf-primary">
            <button v-if="viewDoc.docstatus===0" class="dn-vf-btn dn-vf-btn-submit" :disabled="!$canEdit('bills')" :title="!$canEdit('bills') ? 'Read-only access' : ''" @click="submitDraftDN(viewDoc)">
              <span v-html="icon('check',14)"></span> Submit
            </button>
            <button v-if="viewDoc.docstatus===1 && viewBalance>0" class="dn-vf-btn dn-vf-btn-apply" :disabled="!$canEdit('bills')" :title="!$canEdit('bills') ? 'Read-only access' : ''" @click="applyDN(viewDoc)">
              ↳ <div class="dn-view-action-btn">Apply to Bill</div>
            </button>
            <button v-if="viewDoc.docstatus===1 && viewBalance>0" class="dn-vf-btn dn-vf-btn-auto" :disabled="!$canEdit('bills')" :title="!$canEdit('bills') ? 'Read-only access' : ''" @click="autoApplyDN(viewDoc)">
              ⚡<div class="dn-view-action-btn">Auto Apply</div>
            </button>
            <button v-if="viewDoc.docstatus===1 && viewBalance>0" class="dn-vf-btn dn-vf-btn-refund" :disabled="!$canEdit('bills')" :title="!$canEdit('bills') ? 'Read-only access' : ''" @click="refundDN(viewDoc)">
              ↩ <div class="dn-view-action-btn">Refund Debit</div>
            </button>
            <button v-if="viewDoc.docstatus===1 && viewBalance>0 && viewBalance<=500" class="dn-vf-btn dn-vf-btn-outline" :disabled="!$canEdit('bills')" :title="!$canEdit('bills') ? 'Read-only access' : ''" @click="writeOffDN(viewDoc)">
              ✎ <div class="dn-view-action-btn">Write Off</div>
            </button>
          </div>
          <!-- Secondary actions row -->
          <div class="dn-vf-secondary">
            <button class="dn-vf-sec-btn" @click="viewOpen=false">
              <span v-html="icon('x',13)"></span> <div class="dn-view-action-btn">Close</div>
            </button>
            <button v-if="viewDoc.docstatus===0" class="dn-vf-sec-btn" :disabled="!$canEdit('bills')" :title="!$canEdit('bills') ? 'Read-only access' : ''" @click="openEdit(viewDoc);viewOpen=false">
              <span v-html="icon('edit',13)"></span> <div class="dn-view-action-btn">Edit</div>
            </button>
            <button v-if="viewDoc.docstatus===1" class="dn-vf-sec-btn" :disabled="!$canEdit('bills')" :title="!$canEdit('bills') ? 'Read-only access' : ''" @click="emailDN(viewDoc)">
              <span v-html="icon('mail',13)"></span> <div class="dn-view-action-btn">Email</div>
            </button>
            <button class="dn-vf-sec-btn" @click="printDN(viewDoc)">
              <span v-html="icon('printer',13)"></span> <div class="dn-view-action-btn">Print</div>
            </button>
            <button v-if="viewDoc.docstatus===1" class="dn-vf-sec-btn dn-vf-sec-danger" :disabled="!$canDelete('bills')" :title="!$canDelete('bills') ? 'Not permitted' : ''" @click="cancelDN(viewDoc)">
              <span v-html="icon('x-circle',13)"></span> <div class="dn-view-action-btn">Cancel</div>
            </button>
            <button v-if="viewDoc.docstatus===0 || viewDoc.docstatus===2" class="dn-vf-sec-btn dn-vf-sec-danger" :disabled="!$canDelete('bills')" :title="!$canDelete('bills') ? 'Not permitted' : ''" @click="deleteDN(viewDoc)">
              <span v-html="icon('trash',13)"></span> <div class="dn-view-action-btn">Delete</div>
            </button>
          </div>
        </div>
      </template>
    </div>

    <!-- ── Apply-to-Bill modal ── -->
    <div v-if="applyModal.open" class="inv-drawer-bg" @click.self="applyModal.open=false" style="z-index:60"></div>
    <div v-if="applyModal.open" class="dn-apply-dialog">
      <div class="inv-dh" style="background:linear-gradient(135deg,#7c2d12,#ea580c);height:auto;padding:14px 18px">
        <div class="inv-dh-title">Apply Debit Note — {{ applyModal.dnName }}</div>
        <button class="inv-dclose" @click="applyModal.open=false"><span v-html="icon('x',16)"></span></button>
      </div>
      <div class="inv-dbody">
        <!-- Debit balance pill -->
        <div class="dn-balance-pill">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          Debit Available: <strong>{{ fmtCur(applyModal.balance) }}</strong>
        </div>

        <!-- Bill selector -->
        <div class="dn-field">
          <label class="inv-lbl">Target Bill <span class="inv-req">*</span></label>
          <select v-model="applyModal.bill" class="inv-fi" @change="onApplyBillChange">
            <option value="">— Select bill —</option>
            <option v-for="b in applyModal.openBills" :key="b.name" :value="b.name">
              {{ b.name === applyModal.originBill ? '★ ' : '' }}{{ b.name }} · {{ fmtCur(b.outstanding_amount) }} due{{ b.name === applyModal.originBill ? ' (original)' : '' }}
            </option>
          </select>
        </div>

        <!-- Bill summary card (shown after selection) -->
        <div v-if="applyModal.bill" class="dn-inv-summary">
          <div v-if="applyModal.summaryLoading" class="dn-summary-loading">
            <span class="dn-spinner"></span> Loading bill details…
          </div>
          <template v-else-if="applyModal.summary">
            <div class="dn-summary-header">
              <span class="dn-summary-inv-name">{{ applyModal.bill }}</span>
              <span class="dn-summary-badge" :class="'dn-badge-' + (applyModal.summary.status || 'Unpaid').toLowerCase().replace(' ','-')">
                {{ applyModal.summary.status }}
              </span>
            </div>
            <div class="dn-summary-grid">
              <div class="dn-summary-cell">
                <div class="dn-summary-label">Bill Amount</div>
                <div class="dn-summary-value">{{ fmtCur(applyModal.summary.grand_total) }}</div>
              </div>
              <div class="dn-summary-cell">
                <div class="dn-summary-label">Paid</div>
                <div class="dn-summary-value dn-val-paid">{{ fmtCur(applyModal.summary.total_paid) }}</div>
              </div>
              <div class="dn-summary-cell dn-summary-cell-outstanding">
                <div class="dn-summary-label">Outstanding</div>
                <div class="dn-summary-value dn-val-outstanding">{{ fmtCur(applyModal.summary.outstanding) }}</div>
              </div>
            </div>
          </template>
        </div>

        <!-- Amount to apply -->
        <div class="dn-field">
          <label class="inv-lbl">Amount to Apply <span class="inv-req">*</span></label>
          <input v-model.number="applyModal.amount" type="number" min="0.01" :max="applyModal.balance" step="0.01" class="inv-fi ta-r" />
        </div>
      </div>
      <div class="inv-dfooter">
        <button class="form-btn form-btn-outline" @click="applyModal.open=false" :disabled="applyModal.saving">Cancel</button>
        <button class="form-btn form-btn-primary" :disabled="applyModal.saving || !applyModal.bill || applyModal.amount<=0 || !$canEdit('bills')" :title="!$canEdit('bills') ? 'Read-only access' : ''" @click="submitApply">
          {{ applyModal.saving ? 'Applying…' : `Apply ${fmtCur(applyModal.amount)}` }}
        </button>
      </div>
    </div>

    <!-- ── Refund Debit Note modal ── -->
    <div v-if="refundModal.open" class="inv-drawer-bg" @click.self="refundModal.open=false" style="z-index:60"></div>
    <div v-if="refundModal.open" class="dn-apply-dialog">
      <div class="inv-dh" style="background:linear-gradient(135deg,#78350f,#d97706);height:auto;padding:14px 18px">
        <div class="inv-dh-title">Refund Debit Note — {{ refundModal.dnName }}</div>
        <button class="inv-dclose" @click="refundModal.open=false"><span v-html="icon('x',16)"></span></button>
      </div>
      <div class="inv-dbody">
        <div style="font-size:12.5px;color:#374151;margin-bottom:14px">Available Balance: <strong>{{ fmtCur(refundModal.balance) }}</strong></div>
        <div class="inv-fg inv-fg2">
          <div class="dn-field">
            <label class="inv-lbl">Refund Amount <span class="inv-req">*</span></label>
            <input v-model.number="refundModal.amount" type="number" min="0.01" :max="refundModal.balance" step="0.01" class="inv-fi ta-r" />
          </div>
          <div class="dn-field">
            <label class="inv-lbl">Mode</label>
            <select v-model="refundModal.mode" class="inv-fi">
              <option>Bank Transfer</option>
              <option>Cash</option>
              <option>Cheque</option>
              <option>UPI</option>
              <option>NEFT</option>
            </select>
          </div>
          <div class="dn-field" style="grid-column:1/-1">
            <label class="inv-lbl">Reference / Cheque #</label>
            <input v-model="refundModal.reference" class="inv-fi" placeholder="Optional reference" />
          </div>
        </div>
      </div>
      <div class="inv-dfooter">
        <button class="form-btn form-btn-outline" @click="refundModal.open=false" :disabled="refundModal.saving">Cancel</button>
        <button class="form-btn form-btn-outline" :disabled="refundModal.saving || refundModal.amount<=0 || !$canEdit('bills')" :title="!$canEdit('bills') ? 'Read-only access' : ''" @click="submitRefundDN">
          {{ refundModal.saving ? 'Processing…' : `Refund ${fmtCur(refundModal.amount)}` }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from "vue";
import { useRoute } from "vue-router";
import { useOpenFromQuery } from "../composables/useOpenFromQuery.js";
import { apiList, apiSave, apiGet, apiGET, apiPOST, apiSubmit, apiDelete, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { usePermissions } from "../composables/usePermissions.js";
import { useDocStatus } from "../composables/useDocStatus.js";
import { useEmailDialog } from "../composables/useEmailDialog.js";
import { useConfirm } from "../composables/useConfirm.js";
import { useLivePreview } from "../composables/useLivePreview.js";
import { icon } from "../utils/icons.js";
import { flt, fmtDate } from "../utils/format.js";
import { computeTaxRows } from "../composables/useTaxCalc.js";
import SearchableSelect from "../components/SearchableSelect.vue";
import SummaryStrip from "../components/SummaryStrip.vue";
import Pagination from "../components/Pagination.vue";
import { usePagination } from "../composables/usePagination.js";
import BulkActionBar from "../components/BulkActionBar.vue";
import TimelineStepper from "../components/TimelineStepper.vue";
import DocLink from "../components/DocLink.vue";
import JournalTab from "../components/JournalTab.vue";

const { toast } = useToast();
const { canEdit, canDelete } = usePermissions();
const { confirm } = useConfirm();
const { printDoc, refreshBranding } = useLivePreview();
async function printDN(d) { try { await refreshBranding(); } catch {} printDoc(d, { title: "DEBIT NOTE", partyLabel: "Vendor", partyField: "supplier_name", companyName: d?.company || "" }); }

const { openEmail } = useEmailDialog();
function dnStatus(d) {
  if (d.docstatus === 2) return "cancelled";
  if (d.docstatus === 0) return "draft";
  const bal = balanceFor(d.name);
  if (bal === null) return "unknown";
  const total = Math.abs(flt(d.grand_total || 0));
  if (bal <= 0.005)        return "applied";
  if (bal < total - 0.005) return "partial";
  return "issued";
}
function statusLabel(d) {
  return { draft: "Draft", issued: "Issued", partial: "Partially Applied", applied: "Applied", cancelled: "Cancelled", unknown: "Balance Unknown" }[dnStatus(d)] || "—";
}
function statusCls(d) {
  return { draft: "dn-st-draft", issued: "dn-st-issued", partial: "dn-st-partial", applied: "dn-st-applied", cancelled: "dn-st-cancelled", unknown: "dn-st-draft" }[dnStatus(d)] || "";
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
const viewLoading = ref(false), viewItems = ref([]), viewApplications = ref([]), viewBalance = ref(0), viewReason = ref("");
const vendors = ref([]), items = ref([]), bills = ref([]), lines = ref([]);
const uomList = ref(["Nos", "Kg", "Ltr", "Hrs", "Pcs", "Box", "Mtr", "Set"]);
const sortCol = ref("posting_date"), sortDir = ref("desc");

// Balance cache by DN name
const _balances = ref({});
// Returns null when the balance couldn't be fetched (e.g. transient network
// failure during load()) — distinct from a legitimate 0 (fully applied).
// Callers must not treat null as 0: doing so silently makes a DN whose
// balance we simply failed to fetch look "fully applied" in the list,
// hiding a real available balance from the user.
function balanceFor(name) {
  const v = _balances.value[name];
  return v == null ? null : flt(v);
}

let _id = 1;
const blankLine = () => ({ id: _id++, item_code: "", item_name: "", description: "", hsn_code: "", uom: "Nos", qty: 1, rate: 0, discount_percentage: 0, discount_amount: 0, amount: 0, tax_code: "", collapsed: false, batch_no: "", batch_expiry_date: "" });
const costCenters = ref([]);
async function fetchCostCenters() {
  try {
    const co = await resolveCompany();
    const r = await apiGET("frappe.client.get_list", { doctype: "Cost Center", fields: JSON.stringify(["name"]), filters: JSON.stringify([["disabled","=",0],["company","=",co],["is_group","=",0]]), order_by: "name asc", limit_page_length: 100 }) || [];
    costCenters.value = r.map(c => c.name);
  } catch { costCenters.value = []; }
}
const form = reactive({
  supplier: "",
  posting_date: todayStr(),
  return_against: "",
  reason: "Vendor Overcharge",
  incentive_amount: 0,
  notes: "",
  cost_center: ""
});
const dnCollapsed = reactive({ vendor: false, items: false, notes: true });
const billSummary = reactive({ data: null, loading: false });

const dnTaxes = ref([]);
// Whether the source bill's tax breakup was inter-state (IGST) rather than
// intra-state (CGST+SGST) — detected once from the inherited tax rows, since
// the DN form itself doesn't collect a place of supply. Used to steer which
// component rows apply when taxes are recalculated per remaining line below.
const dnIsInterState = ref(false);
function detectInterState(rows) {
  return (rows || []).some(t => /igst/i.test(t.description || "") || /igst/i.test(t.tax_type || "") || /igst/i.test(t.account_head || ""));
}
const taxTemplates = ref([]);
const taxAccountHead = ref("");
const applyModal = reactive({ open: false, saving: false, dnName: "", balance: 0, bill: "", originBill: "", amount: 0, openBills: [], summary: null, summaryLoading: false });
// Refund modal
const refundModal = reactive({ open: false, saving: false, dnName: "", balance: 0, amount: 0, mode: "Bank Transfer", reference: "" });

function todayStr() { return new Date().toISOString().slice(0, 10); }
function fmtCur(v) { const n = Math.abs(flt(v)); try { return new Intl.NumberFormat("en-OM", { style: "currency", currency: "OMR" }).format(n); } catch { return "ر.ع. " + n.toLocaleString("en-OM", { minimumFractionDigits: 3, maximumFractionDigits: 3 }); } }

async function load() {
  loading.value = true;
  try {
    const co = await resolveCompany();
    const rows = await apiList("Purchase Invoice", {
      fields: ["name", "supplier", "supplier_name", "posting_date", "grand_total", "return_against", "docstatus", "status"],
      filters: [["is_return", "=", 1], ["company", "=", co]],
      limit: 100000,
      order: "posting_date desc, creation desc",
    });
    // Resolve supplier_name for any rows where it's missing
    const missing = [...new Set(rows.filter(d => !d.supplier_name && d.supplier).map(d => d.supplier))];
    if (missing.length) {
      try {
        const suppliers = await apiList("Supplier", {
          fields: ["name", "supplier_name"],
          filters: [["name", "in", missing]],
          limit: missing.length,
        });
        const nameMap = {};
        suppliers.forEach(s => { nameMap[s.name] = s.supplier_name || s.name; });
        rows.forEach(d => { if (!d.supplier_name && d.supplier) d.supplier_name = nameMap[d.supplier] || d.supplier; });
      } catch { /* fallback to supplier id */ }
    }
    list.value = rows;
    // Fetch balances for submitted DNs (parallel)
    const submitted = list.value.filter(d => d.docstatus === 1);
    const balances = await Promise.all(submitted.map(d =>
      apiGET("zoho_books_clone.api.docs.get_debit_note_balance", { debit_note_name: d.name }).catch(() => null)
    ));
    const map = {};
    submitted.forEach((d, i) => { if (balances[i]) map[d.name] = balances[i].balance; });
    _balances.value = map;
  } catch (e) { toast.error(e.message || "Failed to load debit notes"); }
  finally { loading.value = false; }
}

const counts = computed(() => {
  let draft = 0, issued = 0, partial = 0, applied = 0, cancelled = 0;
  for (const d of list.value) {
    const s = dnStatus(d);
    if (s === "draft")      draft++;
    else if (s === "issued")    issued++;
    else if (s === "partial")   partial++;
    else if (s === "applied")   applied++;
    else if (s === "cancelled") cancelled++;
  }
  return { draft, issued, partial, applied, cancelled };
});
const summary = computed(() => ({
  totalValue:  list.value.filter(d => d.docstatus === 1).reduce((s, d) => s + Math.abs(flt(d.grand_total)), 0),
  openBalance: Object.values(_balances.value).reduce((s, v) => s + flt(v), 0),
}));
const _dnYM  = () => { const d=new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; };
const _dnLYM = () => { const d=new Date(); d.setMonth(d.getMonth()-1); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; };
const _dnTr  = (a,b) => { if(!b&&!a) return {pct:0,up:true}; if(!b) return {pct:100,up:true}; const p=Math.round((a-b)/b*100); return {pct:Math.abs(p),up:p>=0}; };
const dnThisMonth = computed(()=>{ const ym=_dnYM(); const r=list.value.filter(d=>(d.posting_date||'').startsWith(ym)); return {count:r.length,value:r.reduce((s,d)=>s+Math.abs(flt(d.grand_total)),0)}; });
const dnAvg = computed(()=>{ const p=list.value.filter(d=>d.grand_total); return p.length?p.reduce((s,d)=>s+Math.abs(flt(d.grand_total)),0)/p.length:0; });
const dnTrends = computed(()=>({
  total:  _dnTr(dnThisMonth.value.count, list.value.filter(d=>(d.posting_date||'').startsWith(_dnLYM())).length),
  issued: _dnTr(counts.value.issued, list.value.filter(d=>(d.posting_date||'').startsWith(_dnLYM())&&d.docstatus===1).length),
  value:  _dnTr(dnThisMonth.value.value, list.value.filter(d=>(d.posting_date||'').startsWith(_dnLYM())&&d.docstatus===1).reduce((s,d)=>s+Math.abs(flt(d.grand_total)),0)),
}));

const filtered = computed(() => {
  let r = list.value;
  const t = activeTab.value;
  if (t === "draft" || t === "issued" || t === "partial" || t === "applied" || t === "cancelled")
    r = r.filter(d => dnStatus(d) === t);
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    r = r.filter(x => (x.name || "").toLowerCase().includes(q)
      || (x.supplier_name || x.supplier || "").toLowerCase().includes(q)
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
const { page, pageSize, paged } = usePagination(sorted, { storageKey: "debit-notes" });
function sortBy(col) { if (sortCol.value === col) sortDir.value = sortDir.value === "asc" ? "desc" : "asc"; else { sortCol.value = col; sortDir.value = "asc"; } }
function sortArrow(col) { if (sortCol.value !== col) return '<span style="color:#d1d5db">⇅</span>'; return sortDir.value === "asc" ? "↑" : "↓"; }

const allChecked = computed(() => sorted.value.length > 0 && sorted.value.every(d => selected.value.has(d.name)));
function toggle(n) { const s = new Set(selected.value); s.has(n) ? s.delete(n) : s.add(n); selected.value = s; }
function toggleAll(e) { selected.value = e.target.checked ? new Set(sorted.value.map(d => d.name)) : new Set(); }

const subtotal    = computed(() => lines.value.reduce((s, l) => s + flt(l.amount), 0));
// Only lines that will actually be saved (has an item + qty), each taxed by
// its OWN tax_code — this is what fixes taxes over-applying when items are
// removed: previously every inherited tax rate was applied to the whole
// remaining subtotal regardless of which items it actually belonged to.
const dnActiveLines = computed(() => lines.value.filter(l => l.item_code && flt(l.qty) > 0));
const dnTaxCtx = computed(() => ({
  companyState: "same",
  placeOfSupply: dnIsInterState.value ? "different" : "same",
  defaultAccount: taxAccountHead.value,
}));
const dnTaxRows   = computed(() => computeTaxRows(dnActiveLines.value, taxTemplates.value, dnTaxCtx.value));
const dnTaxLines  = computed(() => dnTaxRows.value.map(t => ({ description: t.description, rate: t.rate, amount: t.amount, tax_type: t.account_head })));
const dnGrandTotal = computed(() => subtotal.value + dnTaxLines.value.reduce((s, t) => s + t.amount, 0));
const isIncentive = computed(() => form.reason === "Incentive");

const incentiveMaxAmount = computed(() =>
  // Capped by the bill's total value, NOT outstanding_amount — an incentive
  // debit note is a goodwill/adjustment debit independent of whether the
  // bill is still owed money; a fully paid bill remains a valid target.
  Math.max(0, flt(billSummary.data?.grand_total || 0))
);

const incentiveAmount = computed(() =>
  Math.max(0, flt(form.incentive_amount || 0))
);

const displayDebitTotal = computed(() =>
  isIncentive.value ? incentiveAmount.value : dnGrandTotal.value
);

const timelineSteps = computed(() => {
  const d = viewDoc.value;
  if (!d) return [];
  if (d.docstatus === 2) {
    return [
      { key: "draft",     label: "Draft",     done: true },
      { key: "issued",    label: "Issued",    done: true },
      { key: "cancelled", label: "Cancelled", danger: true, current: true },
    ];
  }
  const st = dnStatus(d);
  const isDraft   = st === "draft";
  const isIssued  = st === "issued";
  const isPartial = st === "partial";
  const isApplied = st === "applied";
  return [
    { key: "draft",   label: "Draft",            done: !isDraft,               current: isDraft },
    { key: "issued",  label: "Issued",            done: isPartial || isApplied, current: isIssued },
    { key: "partial", label: "Partially Applied", done: isApplied,              current: isPartial },
    { key: "applied", label: "Applied",           done: isApplied,              current: isApplied },
  ];
});

const appliedTotal = computed(() => viewApplications.value.reduce((s, a) => s + flt(a.amount), 0));
const groupedApplications = computed(() => {
  const groups = {};
  for (const a of viewApplications.value) {
    const key = a.bill || "—";
    if (!groups[key]) groups[key] = { bill: key, total: 0, entries: [] };
    groups[key].total += flt(a.amount);
    groups[key].entries.push(a);
  }
  return Object.values(groups);
});

// ── Create / Edit ─────────────────────────────────────────────────────────
function openNew() {
  editingName.value = "";
 Object.assign(form, {
  supplier: "",
  posting_date: todayStr(),
  return_against: "",
  reason: "Vendor Overcharge",
  incentive_amount: 0,
  notes: "",
  cost_center: ""
});
  billSummary.data = null; billSummary.loading = false;
  dnTaxes.value = [];
  dnIsInterState.value = false;
  lines.value = [blankLine()];
  Object.assign(dnCollapsed, { vendor: false, items: false, notes: true });
  fetchVendors(""); fetchItems(""); fetchBills(""); fetchTaxTemplates(); fetchCostCenters();
  drawerOpen.value = true;
}
async function openEdit(d) {
  editingName.value = d.name;
  dnTaxes.value = [];
  Object.assign(form, { supplier: d.supplier || "", posting_date: d.posting_date || todayStr(), return_against: d.return_against || "", reason: "Vendor Overcharge", incentive_amount: 0, notes: "", cost_center: "" });
  billSummary.data = null; billSummary.loading = false;
  lines.value = [blankLine()];
  Object.assign(dnCollapsed, { vendor: false, items: false, notes: true });
  fetchVendors(""); fetchItems(""); fetchBills(""); fetchTaxTemplates(); fetchCostCenters();
  drawerOpen.value = true;
  try {
    const doc = await apiGet("Purchase Invoice", d.name);
    // Reason lives in its own field on Purchase Invoice; notes in `remark`.
    if (doc?.debit_note_reason) form.reason = doc.debit_note_reason;
    if (doc?.remark) form.notes = doc.remark;
    if (form.reason === "Incentive") {
      // The saved item is a synthetic placeholder (Purchase Invoice
      // requires >=1 item row), not a real line — don't load it into the
      // editable items grid.
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
    dnTaxes.value = (doc?.taxes || [])
      .map(t => ({ tax_type: t.account_head || "", description: t.description || "", rate: Number(t.rate || 0) }))
      .filter(t => t.tax_type);
    dnIsInterState.value = detectInterState(doc?.taxes || []);
    if (doc?.cost_center) form.cost_center = doc.cost_center;
    // Load the bill summary (amount/paid/outstanding) for the bill already
    // saved on this document — needed for the incentive max-amount cap and
    // the save-time "valid bill" check, since onBillSelect only fires on
    // user interaction with the dropdown, not this programmatic set above.
    if (form.return_against) fetchBillSummary(form.return_against);
  } catch {}
}
async function openView(d) {
  viewDoc.value = d;
  viewOpen.value = true;
  viewTab.value = "details";
  viewLoading.value = true;
  viewItems.value = [];
  viewApplications.value = [];
  viewBalance.value = 0;
  viewReason.value = "";
  try {
    const doc = await apiGet("Purchase Invoice", d.name);
    viewItems.value = doc?.items || [];
    if (doc) viewDoc.value = { ...viewDoc.value, ...doc };
    if (doc?.debit_note_reason) viewReason.value = doc.debit_note_reason;
    if (d.docstatus === 1) {
      const [bal, apps] = await Promise.all([
        apiGET("zoho_books_clone.api.docs.get_debit_note_balance", { debit_note_name: d.name }).catch(() => null),
        apiGET("zoho_books_clone.api.docs.get_debit_note_applications", { debit_note_name: d.name }).catch(() => []),
      ]);
      if (bal) viewBalance.value = flt(bal.balance);
      viewApplications.value = apps || [];
    }
  } catch {}
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
    const r = await apiList("Item", { fields: ["name", "item_name", "standard_rate", "standard_buying_rate", "stock_uom"], filters: [...f, ["has_variants", "=", 0], ["is_purchase_item", "=", 1]], limit: 30, order: "item_name asc" });
    items.value = r.map(x => ({ ...x, label: x.item_name || x.name, value: x.name, rate: x.standard_buying_rate || x.standard_rate || 0 }));
  } catch { items.value = []; }
}
async function fetchBills(q = "") {
  try {
    const f = [["is_return", "=", 0], ["docstatus", "=", 1]];
    if (form.supplier) f.push(["supplier", "=", form.supplier]);
    if (q) f.push(["name", "like", "%" + q + "%"]);
    const r = await apiList("Purchase Invoice", { fields: ["name", "supplier", "supplier_name", "grand_total", "outstanding_amount", "status"], filters: f, limit: 50 });
    bills.value = r.map(x => {
      const due = Number(x.outstanding_amount || 0);
      const total = Number(x.grand_total || 0);
      const dueStr = due > 0 ? ` · OMR ${due.toLocaleString("en-OM",{minimumFractionDigits:3})} due` : " · Paid";
      return { ...x, label: `${x.name}${dueStr}${x.supplier_name ? ` · ${x.supplier_name}` : ""}`, value: x.name };
    });
  } catch { bills.value = []; }
}
function onVendorSelect(opt) {
  if (opt?.value) form.supplier = opt.value;
  form.return_against = "";
  billSummary.data = null;
  dnTaxes.value = [];
  fetchBills("");
}
// Populates billSummary.data (bill amount/paid/outstanding/status) for a
// given bill name. Shared by onBillSelect (user picks a bill from the
// dropdown) and openEdit (bill is already set on the loaded document) —
// previously only onBillSelect populated it, so editing an existing
// Incentive debit note left billSummary.data null even though a bill was
// already selected, which broke both the "Maximum" display and the
// "select a valid bill" save-time validation.
async function fetchBillSummary(billName) {
  billSummary.data = null;
  if (!billName) return null;
  billSummary.loading = true;
  try {
    const doc = await apiGet("Purchase Invoice", billName);
    const paid = Math.abs(flt(doc?.grand_total || 0)) - Math.abs(flt(doc?.outstanding_amount || 0));
    billSummary.data = {
      grand_total: Math.abs(flt(doc?.grand_total || 0)),
      total_paid: Math.max(0, paid),
      outstanding: Math.abs(flt(doc?.outstanding_amount || 0)),
      status: doc?.status || "Unpaid",
    };
    return doc;
  } catch { return null; }
  finally { billSummary.loading = false; }
}
async function onBillSelect(opt) {
  const billName = opt?.value ?? opt;
  dnTaxes.value = [];
  if (!billName) { billSummary.data = null; return; }
  const doc = await fetchBillSummary(billName);
  if (!doc) return;
  dnTaxes.value = (doc.taxes || [])
    .map(t => ({ tax_type: t.account_head || "", description: t.description || "", rate: Number(t.rate || 0) }))
    .filter(t => t.tax_type);
  dnIsInterState.value = detectInterState(doc.taxes || []);
  if (doc.items?.length) {
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
    toast.success(`Loaded ${doc.items.length} item(s) from ${billName}`);
  }
  if (!form.supplier && doc.supplier) form.supplier = doc.supplier;
}
async function onItemChange(line) {
  const it = items.value.find(i => i.name === line.item_code || i.value === line.item_code);
  if (it) { line.item_name = it.item_name || it.name || line.item_code; line.rate = flt(it.rate || it.standard_rate || 0); line.uom = it.stock_uom || "Nos"; calcLine(line); }
  if (line.item_code) {
    try {
      const doc = await apiGet("Item", line.item_code);
      if (doc?.item_name) line.item_name = doc.item_name;
      if (doc?.description && !line.description) line.description = doc.description;
      if (doc?.hsn_code) line.hsn_code = doc.hsn_code;
      if (!flt(line.rate) && doc?.standard_rate) line.rate = flt(doc.standard_rate);
      if (doc?.stock_uom) line.uom = doc.stock_uom;
      if (doc?.default_purchase_tax_template) line.tax_code = doc.default_purchase_tax_template;
      calcLine(line);
    } catch {}
  }
}
function onReasonChange() {
  if (form.reason === "Incentive") {
    // Incentive debit notes do not require item lines
    lines.value = [];
  } else if (!lines.value.length) {
    // Normal debit notes require at least one item line
    lines.value = [blankLine()];
  }
}

function addLine() {
  lines.value.push(blankLine());
}

function removeLine(id) {
  if (lines.value.length > 1) {
    lines.value = lines.value.filter(l => l.id !== id);
  }
}
function calcLine(l) {
  if (l.discount_percentage > 100) l.discount_percentage = 100;
  if (l.discount_percentage < 0) l.discount_percentage = 0;
  const base = Math.round(flt(l.qty) * flt(l.rate) * 100) / 100;
  const disc = Math.round(base * flt(l.discount_percentage) / 100 * 100) / 100;
  l.discount_amount = disc;
  l.amount = base - disc;
}
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
async function fetchTaxTemplates() {
  try {
    const co = await resolveCompany();
    const r = await apiList("Account", { fields: ["name"], filters: [["company","=",co],["account_type","=","Tax"],["is_group","=",0]], limit: 1 });
    taxAccountHead.value = r?.[0]?.name || "";
  } catch {}
  try {
    const templates = await apiList("Tax Template", { fields: ["name","template_name","tax_type"], filters: [["disabled","=",0], ["applies_to","in",["Purchase","Both"]]], limit: 50 });
    const withRows = await Promise.all((templates || []).map(async t => {
      try {
        const doc = await apiGet("Tax Template", t.name);
        return { name: t.name, title: t.template_name || t.name, tax_type: t.tax_type || doc?.tax_type || "GST", taxes: doc?.taxes || [] };
      } catch { return { name: t.name, title: t.template_name || t.name, tax_type: t.tax_type || "GST", taxes: [] }; }
    }));
    taxTemplates.value = withRows;
  } catch { taxTemplates.value = []; }
}

async function saveDN(submit) {
  if (!form.supplier) return toast.error("Vendor is required");

  const activeLines = lines.value.filter(
    l => l.item_code && flt(l.qty) > 0
  );

  // Normal debit notes require at least one item.
  // Incentive debit notes are item-less and use incentive_amount instead.
  if (form.reason !== "Incentive" && !activeLines.length) {
    return toast.error("At least one item with quantity > 0 is required");
  }

  if (form.reason === "Incentive") {
  const amount = flt(form.incentive_amount || 0);
  const billAmount = flt(billSummary.data?.grand_total || 0);

  if (amount < 0) {
    return toast.error("Incentive amount cannot be negative");
  }

  if (!billAmount) {
    return toast.error("Please select a valid bill before entering an incentive");
  }

  if (amount > billAmount + 0.01) {
    return toast.error(
      `Incentive amount cannot exceed the bill amount of ${fmtCur(billAmount)}`
    );
  }
}
  drawerSaving.value = true;
  try {
    const itemsPayload = form.reason === "Incentive"
  ? []
  : activeLines.map(l => ({
      item_code: l.item_code,
      item_name: l.item_name || l.item_code,
      description: l.description || l.item_name || l.item_code,
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
    // taxed by its own tax_code), not the old dnTaxes snapshot inherited from
    // the source bill — that snapshot was the source bill's full breakup and
    // stayed the same size no matter how many items got removed here, so it
    // used to apply every original rate against whatever subtotal remained.
    const recomputedTaxes = dnTaxRows.value.map(t => ({ tax_type: t.account_head, description: t.description, rate: t.rate }));
    const taxPayload = form.reason === "Incentive"
  ? []
  : (
      recomputedTaxes.length
        ? recomputedTaxes
        : (
            dnTaxes.value.length
              ? dnTaxes.value
              : dnTaxLines.value.map(tl => ({
                  tax_type: taxAccountHead.value,
                  description: tl.description,
                  rate: tl.rate
                }))
          )
    );
    if (!editingName.value) {
      const r = await apiPOST("zoho_books_clone.api.docs.create_debit_note", {
        vendor: form.supplier,
        against_bill: form.return_against || "",
        date: form.posting_date,
        reason: form.reason,
        notes: form.notes || "",
        cost_center: form.cost_center || "",
        incentive_amount: form.reason === "Incentive"
          ? flt(form.incentive_amount || 0)
          : 0,
        items: JSON.stringify(itemsPayload),
        taxes: JSON.stringify(taxPayload),
        draft_only: submit ? 0 : 1,
        
      });
      toast.success(`Debit Note ${r?.debit_note || ""} ${submit ? "submitted" : "saved as draft"}`);
    } else {
      const company = await resolveCompany();
      let editItems;
      if (form.reason === "Incentive") {
        // Incentive debit notes are item-less in the UI. Purchase Invoice
        // requires >=1 item row, so reuse the first item from the source
        // bill as a placeholder and replace its value with the incentive.
        const sourceItem = (await apiList("Purchase Invoice Item", {
          filters: [["parent", "=", form.return_against]],
          fields: ["item_code", "item_name", "uom"],
          limit: 1,
        }).catch(() => []))[0];
        const amount = flt(form.incentive_amount || 0);
        editItems = [{
          doctype: "Purchase Invoice Item",
          item_code: sourceItem?.item_code || lines.value[0]?.item_code || "",
          item_name: sourceItem?.item_name || lines.value[0]?.item_name || "",
          description: "Incentive",
          hsn_code: "", uom: sourceItem?.uom || "Nos",
          qty: -1, rate: amount,
          discount_percentage: 0,
          amount: -amount,
          batch_no: null, batch_expiry_date: null,
        }];
      } else {
        editItems = activeLines.map(l => ({
          doctype: "Purchase Invoice Item",
          item_code: l.item_code, item_name: l.item_name || l.item_code,
          description: l.description || l.item_code,
          hsn_code: l.hsn_code || "", uom: l.uom || "Nos",
          qty: -Math.abs(flt(l.qty)), rate: flt(l.rate),
          discount_percentage: flt(l.discount_percentage),
          amount: -Math.abs(flt(l.amount)),
          batch_no: l.batch_no || null, batch_expiry_date: l.batch_expiry_date || null,
        }));
      }
      const doc = {
        doctype: "Purchase Invoice", name: editingName.value,
        company, supplier: form.supplier,
        posting_date: form.posting_date,
        is_return: 1, return_against: form.return_against || null,
        cost_center: form.cost_center || "",
        debit_note_reason: form.reason,
        remark: form.notes || "",
        update_stock: form.reason === "Goods Returned" ? 1 : 0,
        items: editItems,
        taxes: form.reason === "Incentive" ? [] : taxPayload.map(t => ({
          doctype: "Tax Line",
          charge_type: "On Net Total",
          account_head: t.tax_type,
          description: t.description || t.tax_type,
          rate: Number(t.rate || 0),
        })),
      };
      const saved = await apiSave(doc);
      if (submit) await apiSubmit("Purchase Invoice", saved.name);
      toast.success(`Debit Note ${saved?.name || ""} ${submit ? "submitted" : "saved"}`);
    }
    drawerOpen.value = false;
    await load();
  } catch (e) { toast.error(e.message || "Failed to save debit note"); }
  finally { drawerSaving.value = false; }
}

// ── Actions ───────────────────────────────────────────────────────────────
async function emailDN(d) {
  // Reuse bill email defaults — supplier-side, same shape
  await openEmail({
    doctype: "Debit Note", name: d.name, docLabel: `Debit Note ${d.name}`,
    getDefaultsEndpoint: "zoho_books_clone.api.docs.get_debit_note_email_defaults",
    sendEndpoint: "zoho_books_clone.api.docs.send_debit_note_email",
    paramKey: "debit_note_name",
    printConfig: { title: "DEBIT NOTE", partyLabel: "Vendor", partyField: "supplier_name" },
  });
}
async function applyDN(d) {
  if (!canEdit("bills")) { toast("Read-only access", "error"); return; }
  try {
    const [r, balData] = await Promise.all([
      apiList("Purchase Invoice", {
        fields: ["name", "outstanding_amount", "grand_total", "posting_date"],
        filters: [["is_return", "=", 0], ["docstatus", "=", 1], ["supplier", "=", d.supplier], ["outstanding_amount", ">", 0]],
        limit: 50, order: "posting_date asc",
      }),
      apiGET("zoho_books_clone.api.docs.get_debit_note_balance", { debit_note_name: d.name }).catch(() => null),
    ]);
    if (!r.length) { toast.info("No open bills for this vendor"); return; }
    // NOTE: no fallback to balanceFor()/grand_total here — if the balance
    // API call fails, we must not silently assume the note's full
    // grand_total is available. A note that's already been fully or
    // partially applied would then show as having its whole original
    // amount free again, letting the user over-apply it.
    if (balData == null) { toast.error("Failed to load debit note balance"); return; }
    const balance = flt(balData.balance ?? 0);
    if (balance <= 0) { toast.info("No available debit balance"); return; }
    const originBill = d.return_against || "";
    const sorted = [...r].sort((a, b) => {
      if (a.name === originBill) return -1;
      if (b.name === originBill) return 1;
      return 0;
    });
    Object.assign(applyModal, {
      open: true, saving: false, dnName: d.name, balance, originBill,
      bill: "", amount: 0, openBills: sorted, summary: null, summaryLoading: false,
    });
  } catch (e) { toast.error(e.message || "Failed to load bills"); }
}
async function onApplyBillChange() {
  applyModal.summary = null;
  if (!applyModal.bill) return;
  applyModal.summaryLoading = true;
  try {
    const doc = await apiGet("Purchase Invoice", applyModal.bill);
    const paid = Math.abs(flt(doc?.grand_total || 0)) - Math.abs(flt(doc?.outstanding_amount || 0));
    applyModal.summary = {
      grand_total: Math.abs(flt(doc?.grand_total || 0)),
      total_paid: paid,
      outstanding: Math.abs(flt(doc?.outstanding_amount || 0)),
      status: doc?.status || "Unpaid",
    };
    applyModal.amount = Math.min(applyModal.balance, applyModal.summary.outstanding);
  } catch { toast.error("Failed to load bill details"); }
  finally { applyModal.summaryLoading = false; }
}
async function submitApply() {
  if (!applyModal.bill || applyModal.amount <= 0) return;
  applyModal.saving = true;
  try {
    await apiPOST("zoho_books_clone.api.docs.apply_debit_note_to_bill", {
      debit_note: applyModal.dnName,
      bill: applyModal.bill,
      amount: applyModal.amount,
    });
    toast.success(`Applied ${fmtCur(applyModal.amount)} to ${applyModal.bill}`);
    applyModal.open = false;
    await load();
    if (viewDoc.value?.name === applyModal.dnName) await openView(viewDoc.value);
  } catch (e) { toast.error(e.message || "Apply failed"); }
  applyModal.saving = false;
}
async function submitDraftDN(d) {
  if (!await confirm({ title: "Submit Debit Note", body: `Submit ${d.name}? GL entries will be posted and the note cannot be edited.`, okLabel: "Submit" })) return;
  try {
    await apiSubmit("Purchase Invoice", d.name);
    toast.success(`${d.name} submitted`);
    viewOpen.value = false;
    await load();
  } catch (e) { toast.error(e.message || "Submit failed"); }
}
async function cancelDN(d) {
  if (!canDelete("bills")) { toast("Not permitted", "error"); return; }
  if (!await confirm({ title: "Cancel Debit Note", body: `Cancel ${d.name}? Any Journal-Entry applications will be cancelled and the bill's outstanding restored.`, okLabel: "Cancel DN" })) return;
  try {
    await apiPOST("zoho_books_clone.api.docs.cancel_debit_note", { name: d.name });
    toast.success("Debit Note cancelled — bill outstanding restored");
    await load(); if (viewDoc.value?.name === d.name) await openView(d);
  } catch (e) { toast.error(e.message || "Cancel failed"); }
}
async function autoApplyDN(d) {
  if (!canEdit("bills")) { toast("Read-only access", "error"); return; }
  try {
    const [r, balData] = await Promise.all([
      apiList("Purchase Invoice", {
        fields: ["name", "outstanding_amount", "posting_date"],
        filters: [["is_return","=",0],["docstatus","=",1],["supplier","=",d.supplier],["outstanding_amount",">",0]],
        limit: 50, order: "posting_date asc",
      }),
      apiGET("zoho_books_clone.api.docs.get_debit_note_balance", { debit_note_name: d.name }).catch(() => null),
    ]);
    if (!r.length) { toast.info("No open bills for this vendor"); return; }
    const balance = flt(balData?.balance ?? 0);
    if (balance <= 0) { toast.info("No available debit balance"); return; }
    const oldest = r[0];
    const applyAmt = Math.min(balance, flt(oldest.outstanding_amount));
    if (!await confirm({ title: "Auto-Apply Debit", body: `Apply ${fmtCur(applyAmt)} to ${oldest.name} (oldest open bill)?`, okLabel: "Apply" })) return;
    await apiPOST("zoho_books_clone.api.docs.apply_debit_note_to_bill", {
      debit_note: d.name, bill: oldest.name, amount: applyAmt,
    });
    toast.success(`Applied ${fmtCur(applyAmt)} to ${oldest.name}`);
    await load();
    if (viewDoc.value?.name === d.name) await openView(viewDoc.value);
  } catch (e) { toast.error(e.message || "Auto-apply failed"); }
}
async function writeOffDN(d) {
  if (!canEdit("bills")) { toast("Read-only access", "error"); return; }
  const balData = await apiGET("zoho_books_clone.api.docs.get_debit_note_balance", { debit_note_name: d.name }).catch(() => null);
  const balance = flt(balData?.balance ?? 0);
  if (balance <= 0) { toast.info("No balance to write off"); return; }
  if (!await confirm({ title: "Write Off Balance", body: `Write off the remaining balance of ${fmtCur(balance)} on ${d.name}? A Journal Entry will be created.`, okLabel: "Write Off" })) return;
  try {
    const r = await apiPOST("zoho_books_clone.api.docs.write_off_debit_note", { debit_note_name: d.name });
    toast.success(`Balance written off — ${r?.journal_entry || "JE created"}`);
    await load();
    if (viewDoc.value?.name === d.name) await openView(viewDoc.value);
  } catch (e) { toast.error(e.message || "Write-off failed"); }
}
async function refundDN(d) {
  if (!canEdit("bills")) { toast("Read-only access", "error"); return; }
  const balData = await apiGET("zoho_books_clone.api.docs.get_debit_note_balance", { debit_note_name: d.name }).catch(() => null);
  const balance = flt(balData?.balance ?? 0);
  if (balance <= 0) { toast.info("No available balance to refund"); return; }
  Object.assign(refundModal, { open: true, saving: false, dnName: d.name, balance, amount: balance, mode: "Bank Transfer", reference: "" });
}
async function submitRefundDN() {
  if (refundModal.amount <= 0) return;
  refundModal.saving = true;
  try {
    await apiPOST("zoho_books_clone.api.docs.refund_debit_note", {
      debit_note_name: refundModal.dnName,
      amount: refundModal.amount,
      refund_mode: refundModal.mode,
      reference_no: refundModal.reference,
    });
    toast.success(`Refunded ${fmtCur(refundModal.amount)} from ${refundModal.dnName}`);
    refundModal.open = false;
    await load();
    if (viewDoc.value?.name === refundModal.dnName) await openView(viewDoc.value);
  } catch (e) { toast.error(e.message || "Refund failed"); }
  refundModal.saving = false;
}
async function deleteDN(d) {
  if (!canDelete("bills")) { toast("Not permitted", "error"); return; }
  if (!await confirm({ title: "Delete Debit Note", body: `Permanently delete ${d.name}? This cannot be undone.`, okLabel: "Delete" })) return;
  try {
    await apiDelete("Purchase Invoice", d.name);
    toast.success("Debit Note deleted");
    viewOpen.value = false; await load();
  } catch (e) { toast.error(e.message || "Delete failed"); }
}

// ── Bulk ──────────────────────────────────────────────────────────────────
async function bulkDelete() {
  if (!canDelete("bills")) { toast("Not permitted", "error"); return; }
  const drafts = sorted.value.filter(d => selected.value.has(d.name) && d.docstatus === 0);
  if (!drafts.length) { toast.info("No draft debit notes selected"); return; }
  if (!await confirm({ title: "Delete Drafts", body: `Delete ${drafts.length} draft debit note(s)?`, okLabel: "Delete" })) return;
  for (const d of drafts) { try { await apiDelete("Purchase Invoice", d.name); } catch {} }
  selected.value = new Set();
  toast.success(`Deleted ${drafts.length} draft(s)`);
  await load();
}
async function bulkEmail() {
  if (!canEdit("bills")) { toast("Read-only access", "error"); return; }
  const subs = sorted.value.filter(d => selected.value.has(d.name) && d.docstatus === 1);
  if (!subs.length) { toast.info("No submitted debit notes selected"); return; }
  let sent = 0;
  for (const d of subs) {
    const ok = await openEmail({
      doctype: "Purchase Invoice", name: d.name, docLabel: `Debit Note ${d.name}`,
      getDefaultsEndpoint: "zoho_books_clone.api.docs.get_bill_email_defaults",
      sendEndpoint: "zoho_books_clone.api.docs.send_bill_email",
      paramKey: "bill_name",
      printConfig: { title: "DEBIT NOTE", partyLabel: "Vendor", partyField: "supplier_name" },
    });
    if (ok) sent++;
  }
  if (sent) toast.success(`Emailed ${sent} debit note(s)`);
}

function exportCSV() {
  const rows = selected.value.size
    ? sorted.value.filter(d => selected.value.has(d.name))
    : sorted.value;
  if (!rows.length) return;
  const head = ["Debit Note","Vendor","Date","Against Bill","Status","Amount","Available Balance"];
  const esc = v => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const out = [head.map(esc).join(",")];
  for (const d of rows) {
    out.push([d.name, d.supplier_name || d.supplier, d.posting_date, d.return_against || "",
      statusLabel(d), Math.abs(flt(d.grand_total)).toFixed(2), balanceFor(d.name) === null ? "Unknown" : balanceFor(d.name).toFixed(2)
    ].map(esc).join(","));
  }
  const blob = new Blob(["﻿" + out.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `debit_notes_${todayStr()}.csv`;
  a.click(); URL.revokeObjectURL(url);
  toast.success(`CSV exported — ${rows.length} note(s)`);
}

const route = useRoute();
onMounted(async () => {
  await load();
  apiList("UOM", { fields: ["name"], order: "name asc", limit: 200 })
    .then(r => { if (r && r.length) uomList.value = r.map(u => u.name); })
    .catch(() => {});
  useOpenFromQuery({ route, openByName: (n) => openView(list.value.find(x => x.name === n) || { name: n }) });
});
</script>

<style scoped>
/* ── Drawer slide-in transition ── */
.dn-drawer {
  position: fixed;
  top: 0; right: -625px; bottom: 0;
  width: 625px; max-width: 96vw;
  background: #fff;
  box-shadow: -8px 0 24px rgba(0,0,0,.08);
  z-index: 9001;
  display: flex; flex-direction: column;
  transition: right .22s ease;
}
.dn-drawer.open { right: 0; }
.dn-view-drawer { width: 625px; right: -625px; }
.dn-view-drawer.open { right: 0; }

/* ── Drawer add/edit body ── */
.dn-dbody .add-card-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #e8ecf0;
  cursor: pointer; user-select: none;
  border-radius: 10px 10px 0 0;
}
.dn-dbody .add-card-title {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; font-weight: 700; color: #1a1a2e;
}
.dn-dbody .add-card-title-icon {
  width: 20px; height: 20px;
  display: flex; align-items: center; justify-content: center;
  color: #ea580c; flex-shrink: 0;
}
.dn-dbody .add-card-chevron {
  color: #9ca3af; transition: transform .2s; display: inline-flex;
}
.dn-dbody .add-card-chevron.collapsed { transform: rotate(-90deg); }
.dn-dbody .add-card-body { padding: 16px; }
.dn-dbody .add-card-body.collapsed { display: none; }

/* Line count badge in items card header */
.dn-lines-badge {
  font-size: 11.5px; font-weight: 600;
  color: #374151; background: #f3f4f6;
  border: 1px solid #e5e7eb;
  border-radius: 5px; padding: 2px 8px;
}

/* ── Drawer header icon ── */
.dn-dheader-left { display: flex; align-items: flex-start; gap: 12px; }
.dn-dheader-ico {
  width: 38px; height: 38px; border-radius: 10px;
  background: #fff; border: 1px solid rgba(234,88,12,.22);
  display: inline-flex; align-items: center; justify-content: center;
  color: #ea580c; flex-shrink: 0;
}
.dn-dheader-ico.edit { color: #ca8a04; border-color: rgba(202,138,4,.25); }

/* ── Field helpers ── */
.dn-field { display: flex; flex-direction: column; gap: 4px; }

/* ── Item cards (add/edit drawer) ── */
.dn-item-cards { display: flex; flex-direction: column; gap: 8px; padding: 8px 14px 0; }
.dn-item-card {
  border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden;
  background: #fff; transition: box-shadow .15s;
}
.dn-item-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,.06); }
.dn-item-card-header {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 12px; background: #f9fafb; border-bottom: 1px solid #f0f0f0;
  cursor: pointer; user-select: none;
}
.dn-item-card-num  { font-size: 10.5px; font-weight: 800; color: #c2410c; min-width: 22px; }
.dn-item-card-title { flex: 1; font-size: 13px; font-weight: 600; color: #111827; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.dn-item-card-subtotal { display: flex; flex-direction: column; align-items: flex-end; gap: 0; flex-shrink: 0; }
.dn-item-subtotal-label { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: #9ca3af; }
.dn-item-amount { font-size: 13px; font-weight: 700; color: #7c2d12; }
.dn-item-rm { border: none; background: none; color: #d1d5db; font-size: 18px; font-weight: 700; cursor: pointer; padding: 0 2px; line-height: 1; flex-shrink: 0; transition: color .12s; }
.dn-item-rm:hover { color: #dc2626; }
.dn-item-card-body {
  display: grid; grid-template-columns: 1fr 1fr; gap: 14px;
  padding: 14px 16px;
}
.dn-item-col { display: flex; flex-direction: column; gap: 10px; }
.dn-item-field { display: flex; flex-direction: column; gap: 4px; }
.dn-item-field label { font-size: 11px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: .04em; }
.dn-item-num-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }

/* ── Form totals ── */
.dn-form-totals {
  border-top: 1px solid #e5e7eb; margin: 4px 14px 0;
  padding: 10px 0;
}
.dn-tax-note { font-size: 12px; color: #6b7280; padding: 2px 0; }
.dn-tax-row { color: #6b7280; font-size: 12.5px; }
.dn-grand-total-row { font-size: 15px; font-weight: 700; color: #7c2d12; border-top: 2px solid #e5e7eb; padding-top: 10px; margin-top: 4px; }
.dn-field-hint { font-size: 11px; color: #9ca3af; margin-top: 2px; }

/* ── Totals (legacy compat) ── */
.dn-total-row { display: flex; justify-content: space-between; gap: 16px; font-size: 13px; color: #374151; padding: 8px 0; }
.dn-total-row.grand { font-weight: 700; font-size: 15px; color: #111827; border-top: 2px solid #e5e7eb; padding-top: 10px; }

/* ── View panel header ── */
.dn-view-header {
  align-items: center !important;
  background: #fff;
  border-bottom: 1px solid #e8ecf0;
  padding: 18px 20px !important;
}
.dn-view-head-body { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex: 1; min-width: 0; }
.dn-view-head-left { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.dn-view-head-right { display: flex; flex-direction: column; align-items: flex-end; gap: 5px; flex-shrink: 0; }
.dn-view-amount { font-size: 20px; font-weight: 800; color: #1a1a2e; line-height: 1; }
.dn-vclose {
  display: inline-flex; align-items: center; justify-content: center;
  width: 32px; height: 32px; flex-shrink: 0; margin-left: 14px;
  background: #fff; border: 1.5px solid #e5e7eb; border-radius: 8px;
  color: #6b7280; cursor: pointer;
  transition: background .12s, border-color .12s, color .12s;
}
.dn-vclose:hover { background: #f8fafc; border-color: #cbd5e1; color: #374151; }

/* ── Meta/detail 2-col grid ── */
.dn-meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.dn-meta-lbl { font-size: 11px; color: #9ca3af; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 2px; }

/* ── View items table ── */
.dn-view-items { display: flex; flex-direction: column; border: 1px solid #e5e7eb; border-radius: 6px; overflow: hidden; }
.dn-view-items-head {
  display: grid; grid-template-columns: 2fr 70px 100px 55px 60px 80px 90px;
  gap: 8px; background: #f9fafb; padding: 8px 12px;
  font-size: 11px; font-weight: 700; color: #6b7280; text-transform: uppercase;
}
.dn-view-items-row {
  display: grid; grid-template-columns: 2fr 70px 100px 55px 60px 80px 90px;
  gap: 8px; padding: 8px 12px; border-top: 1px solid #f3f4f6;
  align-items: center; font-size: 12.5px;
}
.dn-view-totals { margin-top: 8px; border: 1px solid #e5e7eb; border-radius: 6px; overflow: hidden; font-size: 12.5px; }
.dn-vt-row { display: flex; justify-content: space-between; align-items: center; padding: 7px 12px; border-bottom: 1px solid #f3f4f6; }
.dn-vt-row:last-child { border-bottom: none; }
.dn-vt-lbl { color: #6b7280; }
.dn-vt-val { font-weight: 500; color: #111827; }
.dn-vt-tax { background: #fafafa; }
.dn-vt-grand { background: #fff7f0; border-top: 2px solid #fed7aa !important; }
.dn-vt-grand .dn-vt-lbl { font-weight: 700; color: #374151; }
.dn-vt-grand .dn-vt-val { font-weight: 700; font-size: 13px; }

/* ── Applications grid ── */
.dn-app-head {
  display: grid; grid-template-columns: 1fr 1fr 1fr 1fr;
  gap: 8px; background: #f9fafb; padding: 8px 12px;
  font-size: 11px; font-weight: 700; color: #6b7280; text-transform: uppercase;
  border-radius: 6px 6px 0 0; border: 1px solid #e5e7eb; border-bottom: none;
}
.dn-app-row {
  display: grid; grid-template-columns: 1fr 1fr 1fr 1fr;
  gap: 8px; padding: 8px 12px; border-top: 1px solid #f3f4f6;
  border-left: 1px solid #e5e7eb; border-right: 1px solid #e5e7eb;
  align-items: center; font-size: 12.5px;
}
.dn-app-row:last-child { border-bottom: 1px solid #e5e7eb; border-radius: 0 0 6px 6px; }

/* ── Row action button variants ── */
.dn-act-cell { display: flex; gap: 4px; justify-content: flex-end; cursor: default !important; }
.dn-act-apply { background: #fff7ed; border-color: #ea580c; color: #ea580c; }
.dn-act-apply:hover { background: #ffedd5; color: #c2410c; }
.dn-act-del:hover { background: #fee2e2; color: #dc2626; border-color: #fca5a5; }
.dn-empty { text-align: center; color: #9ca3af; padding: 48px !important; cursor: default !important; }

/* ── Apply-to-Bill dialog ── */
.dn-apply-dialog {
  position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
  width: 480px; max-width: 96vw; background: #fff;
  border-radius: 12px; box-shadow: 0 12px 40px rgba(0,0,0,.2);
  z-index: 9100; display: flex; flex-direction: column; overflow: hidden;
}

/* ── Timeline stepper wrapper ── */
.dn-stepper-wrap { background: #fff; border-bottom: 1px solid #e5e7eb; flex-shrink: 0; }

/* ── Bill selection card ── */
.dn-bill-ph {
  display: flex; align-items: center; gap: 8px;
  color: #9ca3af; font-size: 13px; font-style: italic;
  padding: 10px 4px;
}
.dn-no-bills-note {
  margin-top: 8px; font-size: 12px; color: #9ca3af; font-style: italic;
}
.dn-bill-loaded-badge {
  font-size: 11px; font-weight: 700;
  background: #fff7ed; color: #ea580c;
  border: 1px solid #fed7aa;
  border-radius: 5px; padding: 2px 8px;
}

/* ── Bill preview card ── */
.dn-bill-preview {
  background: #fff8f5;
  border: 1px solid #fed7aa;
  border-radius: 8px;
  padding: 14px 16px;
}
.dn-bill-preview-hdr {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 12px;
}
.dn-bill-num {
  font-size: 14px; font-weight: 800; color: #7c2d12; letter-spacing: -0.2px;
}
.dn-bill-meta {
  font-size: 12px; color: #92400e; margin-top: 2px;
}
.dn-change-bill-btn {
  border: 1px solid #fed7aa; background: #fff;
  color: #ea580c; border-radius: 6px;
  padding: 4px 10px; font-size: 12px; font-weight: 600;
  cursor: pointer; white-space: nowrap; font-family: inherit;
  transition: all .15s; flex-shrink: 0;
}
.dn-change-bill-btn:hover { background: #fff7ed; border-color: #ea580c; }
.dn-bill-preview-divider { height: 1px; background: #fed7aa; margin: 12px 0; }
.dn-bill-amounts {
  display: flex; align-items: center; gap: 0; flex-wrap: wrap;
}
.dn-bill-amount-item {
  display: flex; flex-direction: column; gap: 2px; flex: 1;
}
.dn-bill-amount-sep {
  color: #fbbf24; font-size: 16px; padding: 0 8px; align-self: center;
}
.dn-bill-amount-lbl {
  font-size: 10.5px; color: #92400e; text-transform: uppercase; letter-spacing: .05em; font-weight: 600;
}
.dn-bill-amount-val {
  font-size: 14px; font-weight: 700; color: #7c2d12;
}
.dn-bill-amount-val.outstanding { color: #dc2626; }

/* ── Items placeholder (no bill) ── */
.dn-items-ph {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  color: #9ca3af; font-size: 13px; font-style: italic;
  padding: 28px 16px;
}

/* ── Bill-driven items table (7 cols, legacy) ── */
.dn-items-head-bill {
  grid-template-columns: 2fr 2fr 70px 80px 90px 100px 32px !important;
}
.dn-items-row-bill {
  grid-template-columns: 2fr 2fr 70px 80px 90px 100px 32px !important;
}
.dn-item-name-cell { display: flex; align-items: center; padding: 4px 0; }
.dn-item-name { font-size: 13px; font-weight: 500; color: #374151; }
.dn-orig-qty {
  padding: 8px 0; font-size: 12px;
  color: #9ca3af; font-variant-numeric: tabular-nums;
}
.dn-rate-cell {
  padding: 8px 0; color: #6b7280;
}


/* ── Responsive ── */
@media (max-width: 768px) {
  .dn-drawer     { width: 100% !important; right: -100% !important; max-width: 100%; }
  .dn-view-drawer { width: 100% !important; right: -100% !important; max-width: 100%; }
  .dn-drawer.open,
  .dn-view-drawer.open { right: 0 !important; }

  /* toolbar */
  .dn-toolbar { flex-wrap: wrap; gap: 8px; }
  .dn-btn-group { margin-left: 0; flex-wrap: wrap; }

  /* KPI grids */
  .bk-kpi-grid  { grid-template-columns: repeat(2, 1fr) !important; gap: 10px; }
  .bk-stat-grid { grid-template-columns: repeat(2, 1fr) !important; gap: 10px; }

  /* hide Against Bill + Available columns */
  .inv-table th:nth-child(5), .inv-table td:nth-child(5),
  .inv-table th:nth-child(8), .inv-table td:nth-child(8) { display: none; }

  /* view drawer head */
  .dn-view-head-body { flex-wrap: wrap; gap: 8px; }

  /* Line item card: stack left + right columns vertically */
  .dn-item-card-body { grid-template-columns: 1fr; gap: 10px; padding: 12px 14px; }
  /* Keep 2-col grid for num fields — fits fine at full drawer width */
  .dn-item-num-row { grid-template-columns: 1fr 1fr; gap: 8px; }
}

@media (max-width: 480px) {
  .bk-kpi-grid  { grid-template-columns: 1fr !important; }
  .bk-stat-grid { grid-template-columns: 1fr !important; }

  /* meta grid 1-col */
  .dn-meta-grid { grid-template-columns: 1fr !important; }

  /* inner line-items table scrollable */
  .dn-view-items { overflow-x: auto !important; -webkit-overflow-scrolling: touch; }
  .dn-view-items-head,
  .dn-view-items-row { min-width: 380px; font-size: 11.5px !important; }

  /* applied-to table scrollable */
  .dn-app-head,
  .dn-app-row { min-width: 320px; font-size: 11.5px !important; }

  .dn-app-table { overflow-x: auto !important; -webkit-overflow-scrolling: touch; }
}

@media (max-width: 425px) {
  /* suppress the global "Date:" prefix injected by Invoices.vue */
  .inv-table tbody .inv-row .td-id::before {
    content: none !important; display: none !important; font-size: 0 !important;
  }

  /* card-layout style overrides */
  .td-id { padding: 0 14px 4px !important; cursor: pointer !important; }
  .td-id .inv-link { font-size: 12px !important; font-weight: 600 !important; color: #1a6ef7 !important; text-decoration: underline !important; }
  .td-customer { font-size: 15px !important; font-weight: 700 !important; color: #1a1a2e !important; }
  .td-amount   { font-size: 14px !important; letter-spacing: -0.02em !important; }
}

/* ── Mobile card view (Option A) ── */
.dn-mobile-cards { display: none; }
.dn-desktop-table { display: table; }

@media (max-width: 768px) {
  .dn-desktop-table { display: none !important; }
  .dn-mobile-cards { display: flex; flex-direction: column; gap: 0; background: #f8fafc; }
  .dn-mobile-card { background: #fff; border-bottom: 1px solid #e5e7eb; padding: 12px 14px; cursor: pointer; transition: background .12s; }
  .dn-mobile-card:active { background: #f8f9fc; }
  .dn-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .dn-mc-docno { font-size: 12px; font-weight: 700; color: #2563eb; }
  .dn-mc-mid { font-size: 13.5px; font-weight: 600; color: #1a1d23; margin-bottom: 4px; }
  .dn-mc-meta { display: flex; justify-content: space-between; font-size: 12px; color: #868e96; margin-bottom: 4px; }
  .dn-mc-amount { font-weight: 700; color: #7c2d12; }
  .dn-mc-balance { font-size: 11.5px; color: #868e96; margin-bottom: 8px; }
  .dn-mc-footer { display: flex; gap: 6px; margin-top: 8px; }
  .dn-mc-btn { flex: 1; padding: 6px 10px; border-radius: 7px; font-size: 12px; font-weight: 600; cursor: pointer; background: #f1f5f9; border: 1px solid #e2e8f0; color: #374151; }
  .dn-mc-apply { background: #eff6ff; border-color: #bfdbfe; color: #2563eb; }
  .dn-mc-danger { background: #fff1f2; border-color: #fecaca; color: #dc2626; }
  .dn-mc--skeleton { pointer-events: none; }
  .dn-mc-shimmer { border-radius: 6px; background: linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size: 200% 100%; animation: dn-shimmer 1.4s infinite; }
  @keyframes dn-shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
  .dn-mc-empty { text-align: center; padding: 32px 16px; color: #868e96; font-size: 13px; }
}

/* ── Status badges ── */
.dn-st-draft    { background:#f3f4f6; color:#6b7280; border:1px solid #e5e7eb; }
.dn-st-issued   { background:#eff6ff; color:#2563eb; border:1px solid #bfdbfe; }
.dn-st-partial  { background:#fff7ed; color:#c2410c; border:1px solid #fed7aa; }
.dn-st-applied  { background:#f0fdf4; color:#15803d; border:1px solid #bbf7d0; }
.dn-st-cancelled{ background:#fef2f2; color:#dc2626; border:1px solid #fecaca; }

/* ── 2-row view footer ── */
.dn-view-footer { border-top: 1px solid #e5e7eb; background: #fafafa; }
.dn-vf-primary {
  display: flex; flex-wrap: wrap; gap: 8px;
  padding: 12px 16px 8px; border-bottom: 1px solid #f0f0f0;
}
.dn-vf-btn {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 8px 14px; border-radius: 8px; font-size: 12.5px; font-weight: 600;
  cursor: pointer; border: none; transition: opacity .15s;
}
.dn-vf-btn:disabled { opacity: .5; cursor: not-allowed; }
.dn-vf-btn-submit { background: #2563eb; color: #fff; }
.dn-vf-btn-apply  { background: #7c2d12; color: #fff; }
.dn-vf-btn-auto   { background: #7c3aed; color: #fff; }
.dn-vf-btn-refund { background: #0f766e; color: #fff; }
.dn-vf-btn-outline{ background: #fff; color: #374151; border: 1px solid #d1d5db; }
.dn-view-action-btn { display: inline; }
.dn-vf-secondary {
  display: flex; flex-wrap: wrap; gap: 6px;
  padding: 8px 16px 12px;
}
.dn-vf-sec-btn {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 5px 10px; border-radius: 6px; font-size: 12px; font-weight: 500;
  cursor: pointer; border: 1px solid #e5e7eb; background: #fff; color: #6b7280;
  transition: background .12s;
}
.dn-vf-sec-btn:hover { background: #f3f4f6; }
.dn-vf-sec-danger { color: #dc2626 !important; border-color: #fecaca !important; }
.dn-vf-sec-danger:hover { background: #fff1f2 !important; }

/* ── Balance strip (Applied To tab) ── */
.dn-balance-strip {
  display: flex; align-items: center; gap: 0;
  background: linear-gradient(135deg,#7c2d12,#c2410c);
  border-radius: 10px; overflow: hidden; margin-bottom: 16px;
}
.dn-bs-cell {
  flex: 1; padding: 12px 16px; text-align: center;
}
.dn-bs-cell--avail { background: rgba(0,0,0,.15); }
.dn-bs-lbl { font-size: 10px; font-weight: 700; color: rgba(255,255,255,.7); text-transform: uppercase; letter-spacing: .05em; margin-bottom: 2px; }
.dn-bs-val { font-size: 14px; font-weight: 700; color: #fff; }
.dn-bs-val--avail { color: #fef08a; }
.dn-bs-sep { font-size: 16px; font-weight: 700; color: rgba(255,255,255,.5); padding: 0 4px; }

/* ── Grouped applications ── */
.dn-app-group { border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; margin-bottom: 10px; }
.dn-app-group-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 12px; background: #f9fafb; border-bottom: 1px solid #e5e7eb;
  font-size: 12.5px; font-weight: 600;
}
.dn-app-group-total { color: #059669; font-weight: 700; }
.dn-app-group-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 7px 12px; border-bottom: 1px solid #f3f4f6; font-size: 12px;
}
.dn-app-group-row:last-child { border-bottom: none; }

/* ── Mobile item cards ── */
.dn-view-items--mobile { display: none; flex-direction: column; gap: 8px; }
.dn-vi-card { border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden; background: #fff; }
.dn-vi-card-header {
  display: flex; align-items: center; gap: 8px;
  background: #fafafa; padding: 10px 12px; border-bottom: 1px solid #f0f0f0;
}
.dn-vi-card-num  { font-size: 11px; font-weight: 800; color: #c2410c; min-width: 20px; flex-shrink: 0; }
.dn-vi-card-name { flex: 1; font-size: 13px; font-weight: 600; color: #111827; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.dn-vi-card-amount { font-size: 13.5px; font-weight: 700; color: #7c2d12; flex-shrink: 0; }
.dn-vi-card-meta { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0; }
.dn-vi-batch-line { padding: 6px 12px; font-size: 12px; color: #6b7280; border-top: 1px solid #f3f4f6; }
.dn-vi-meta-item { display: flex; flex-direction: column; gap: 2px; padding: 8px 12px; border-right: 1px solid #f3f4f6; }
.dn-vi-meta-item:last-child { border-right: none; }
.dn-vi-meta-item--amount { background: #fff8f6; }
.dn-vi-meta-lbl { font-size: 10px; font-weight: 700; color: #9ca3af; text-transform: uppercase; letter-spacing: .05em; }
.dn-vi-meta-val { font-size: 12.5px; font-weight: 600; color: #374151; }
.dn-vi-meta-val--amount { color: #7c2d12; font-weight: 700; }
@media (max-width: 768px) {
  .dn-view-items--desktop { display: none !important; }
  .dn-view-items--mobile  { display: flex; }
}

/* ── Balance pill (Apply modal) ── */
.dn-balance-pill {
  display: flex; align-items: center; gap: 6px;
  background: #fff7ed; border: 1px solid #fed7aa; border-radius: 8px;
  padding: 8px 12px; font-size: 12.5px; color: #c2410c; font-weight: 500;
  margin-bottom: 14px;
}

/* ── Bill summary card (Apply modal) ── */
.dn-inv-summary { border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; margin-bottom: 12px; }
.dn-summary-loading { display: flex; align-items: center; gap: 8px; padding: 14px; font-size: 12.5px; color: #6b7280; }
.dn-spinner {
  width: 14px; height: 14px; border: 2px solid #e5e7eb; border-top-color: #c2410c;
  border-radius: 50%; animation: dn-spin .7s linear infinite; display: inline-block;
}
@keyframes dn-spin { to { transform: rotate(360deg); } }
.dn-summary-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; background: #fafafa; border-bottom: 1px solid #f0f0f0;
}
.dn-summary-inv-name { font-size: 12.5px; font-weight: 700; color: #111827; }
.dn-summary-badge {
  font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 20px;
  border: 1px solid currentColor;
}
.dn-badge-unpaid    { color: #dc2626; background: #fef2f2; }
.dn-badge-paid      { color: #15803d; background: #f0fdf4; }
.dn-badge-overdue   { color: #9a3412; background: #fff7ed; }
.dn-badge-partially-paid { color: #b45309; background: #fffbeb; }
.dn-summary-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; }
.dn-summary-cell { padding: 8px 12px; border-right: 1px solid #f3f4f6; }
.dn-summary-cell:last-child { border-right: none; }
.dn-summary-cell-outstanding { background: #fff7f5; }
.dn-summary-label { font-size: 10px; font-weight: 700; color: #9ca3af; text-transform: uppercase; letter-spacing: .04em; margin-bottom: 2px; }
.dn-summary-value { font-size: 13px; font-weight: 600; color: #374151; }
.dn-val-paid        { color: #15803d; }
.dn-val-outstanding { color: #c2410c; font-weight: 700; }

</style>