<template>
  <div class="list-page">

    <div class="sales-toolbar">
      <div class="sales-search">
        <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
        <input v-model="search" placeholder="Search payments…" class="sales-search-input" />
      </div>
      <div class="sales-pills">
        <button v-for="t in tabs" :key="t.key" class="sales-pill" :class="{active:activeTab===t.key, ['pill-'+t.key]: t.key!=='all'}" @click="activeTab=t.key">{{ t.label }}</button>
      </div>
      <div class="pmt-btn-group">
        <button class="sales-btn-ghost" @click="load" title="Refresh"><span v-html="icon('refresh',14)"></span></button>
        <button class="sales-btn-primary" @click="openNew" :disabled="!$canWrite('payments')" :title="!$canWrite('payments') ? 'Read-only access' : ''"><span ><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="9" y1="13" x2="15" y2="13"></line><line x1="9" y1="17" x2="13" y2="17"></line></svg></span> {{ defaultTab === 'Receive' ? 'New Received Payment' : 'New Payment Made' }}</button>
      </div>
    </div>

    <!-- ── KPI Cards ── -->
    <div class="bk-kpi-grid bk-kpi-grid-4">
      <div class="bk-kpi-card bk-kpi-accent clickable" @click="activeTab='all'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#dbeafe"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.8"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Total Payments</div><div class="bk-kpi-value">{{ list.length }}</div><div class="bk-kpi-trend" :class="pmtTrends.total.up?'bk-trend-up':'bk-trend-down'">{{ pmtTrends.total.up?'↑':'↓' }} {{ pmtTrends.total.pct }}% vs last month</div></div></div></div>
      <div class="bk-kpi-card bk-kpi-success clickable" @click="activeTab='Receive'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#dcfce7"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="1.8"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Total Received</div><div class="bk-kpi-value bk-kpi-green" style="font-size:20px">{{ fmtCur(summaryReceived) }}</div><div class="bk-kpi-trend" :class="pmtTrends.received.up?'bk-trend-up':'bk-trend-down'">{{ pmtTrends.received.up?'↑':'↓' }} {{ pmtTrends.received.pct }}% vs last month</div></div></div></div>
      <div class="bk-kpi-card bk-kpi-danger clickable" @click="activeTab='Pay'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#fee2e2"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="1.8"><polyline points="1 6 10.5 15.5 15.5 10.5 23 18"/><polyline points="17 18 23 18 23 12"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Total Paid Out</div><div class="bk-kpi-value bk-kpi-red" style="font-size:20px">{{ fmtCur(summaryPaid) }}</div><div class="bk-kpi-trend" :class="pmtTrends.paid.up?'bk-trend-down':'bk-trend-up'">{{ pmtTrends.paid.up?'↑':'↓' }} {{ pmtTrends.paid.pct }}% vs last month</div></div></div></div>
      <div class="bk-kpi-card"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#f3f4f6"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12"/><path d="M6 8h12"/><path d="m6 13 8.5 8"/><path d="M6 13h3"/><path d="M9 13c6.667 0 6.667-10 0-10"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Net Flow</div><div class="bk-kpi-value" :class="(summaryReceived-summaryPaid)>=0?'bk-kpi-green':'bk-kpi-red'" style="font-size:20px">{{ fmtCur(summaryReceived - summaryPaid) }}</div><div class="bk-kpi-trend bk-trend-neutral">this period</div></div></div></div>
    </div>
    <div class="bk-stat-grid">
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">This Month</div><div class="bk-stat-value">{{ pmtThisMonth.count }}</div></div><div class="bk-stat-icon" style="background:#dbeafe;color:#2563eb"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg></div></div></div>
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">Received This Month</div><div class="bk-stat-value bk-kpi-green" style="font-size:16px">{{ fmtCur(pmtThisMonth.received) }}</div></div><div class="bk-stat-icon" style="background:#dcfce7;color:#16a34a"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg></div></div></div>
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">Paid Out This Month</div><div class="bk-stat-value bk-kpi-red" style="font-size:16px">{{ fmtCur(pmtThisMonth.paid) }}</div></div><div class="bk-stat-icon" style="background:#fee2e2;color:#dc2626"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/></svg></div></div></div>
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">Avg Payment</div><div class="bk-stat-value" style="font-size:16px">{{ fmtCur(pmtAvg) }}</div></div><div class="bk-stat-icon" style="background:#e5e7eb;color:#6b7280"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg></div></div></div>
    </div>

    <!-- Bulk action bar -->
    <div v-if="selected.size" class="inv-bulk-bar">
      <span class="inv-bulk-count">{{ selected.size }} selected</span>
      <button class="inv-bulk-btn" @click="bulkCancel" :disabled="bulkBusy">Cancel Submitted</button>
      <button class="inv-bulk-btn inv-bulk-danger" @click="bulkDelete" :disabled="bulkBusy">Delete Drafts</button>
      <button class="inv-bulk-btn" @click="bulkExport" :disabled="bulkBusy">
        <span v-html="icon('download',13)"></span> Export CSV
      </button>
      <button class="inv-bulk-clear" @click="selected = new Set()">✕ Clear</button>
    </div>

    <div class="inv-table-wrap">
      <table class="inv-table pay-desktop-table">
        <thead><tr>
          <th style="width:32px"><input type="checkbox" @change="toggleAll" :checked="allChecked" /></th>
          <th @click="sort('name')" class="sortable">PAYMENT # <span v-html="sortArrow('name')"></span></th>
          <th @click="sort('party')" class="sortable">PARTY <span v-html="sortArrow('party')"></span></th>
          <th @click="sort('mode_of_payment')" class="sortable">MODE <span v-html="sortArrow('mode_of_payment')"></span></th>
          <th @click="sort('reference_no')" class="sortable">REFERENCE <span v-html="sortArrow('reference_no')"></span></th>
          <th @click="sort('payment_date')" class="sortable">DATE <span v-html="sortArrow('payment_date')"></span></th>
          <th>TYPE</th>
          <th @click="sort('paid_amount')" class="sortable ta-r">AMOUNT <span v-html="sortArrow('paid_amount')"></span></th>
          <th style="width:60px">ACTIONS</th>
        </tr></thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 8" :key="n"><td colspan="9"><div class="shimmer"></div></td></tr>
          </template>
          <template v-else>
            <tr v-for="p in paged" :key="p.name" class="inv-row" :class="{selected:selected.has(p.name)}">
              <td><input type="checkbox" :checked="selected.has(p.name)" @change="toggle(p.name)" /></td>
              <td @click="openView(p)"><span class="inv-link">{{ p.name }}</span></td>
              <td @click="openView(p)">{{ p.party_name||p.party||'—' }}</td>
              <td @click="openView(p)" class="text-muted">{{ p.mode_of_payment||'—' }}</td>
              <td @click="openView(p)" class="text-muted mono-sm" style="overflow: hidden;max-width: 10px">{{ p.reference_no||'—' }}</td>
              <td @click="openView(p)" class="text-muted mono-sm">{{ fmtDate(p.payment_date) }}</td>
              <td @click="openView(p)">
                <span class="inv-status-badge" :class="p.payment_type==='Receive'?'badge-green':'badge-red'">
                  {{ p.payment_type==='Receive'?'Received':'Paid Out' }}
                </span>
              </td>
              <td @click="openView(p)" class="ta-r mono-sm" :class="p.payment_type==='Receive'?'green':'red'">{{ fmtCur(p.paid_amount) }}</td>
              <td class="pmt-act-cell">
                <button class="inv-act-btn" @click="openView(p)" title="View"><span v-html="icon('eye',13)"></span></button>
                <button v-if="p.docstatus===0" class="inv-act-btn" @click="openEdit(p)" title="Edit"><span v-html="icon('edit',13)"></span></button>
                <button v-if="p.docstatus===1" class="inv-act-btn" style="border-color:#fee2e2;color:#dc2626" @click="cancelPmt(p)" title="Cancel">✕</button>
                <button v-if="p.docstatus===0 || p.docstatus===2" class="inv-act-btn" style="border-color:#fee2e2;color:#dc2626" @click="deletePmt(p)" title="Delete"><span v-html="icon('trash',13)"></span></button>
              </td>
            </tr>
            <tr v-if="!sorted.length"><td colspan="9" class="bk-empty-state"><div class="bk-empty-inner"><template v-if="search"><svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.3"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg><p class="bk-empty-title">No payments match</p></template><template v-else><div class="bk-empty-illus"><svg width="80" height="80" viewBox="0 0 80 80" fill="none"><rect x="8" y="22" width="64" height="40" rx="8" fill="#e2e8f0"/><rect x="12" y="26" width="56" height="32" rx="6" fill="#fff"/><rect x="12" y="38" width="56" height="6" fill="#cbd5e1"/><circle cx="22" cy="50" r="5" fill="#f0fdf4" stroke="#16a34a" stroke-width="1.5"/><polyline points="19.5 50 21.5 52 24.5 48" stroke="#16a34a" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></div><p class="bk-empty-title">No payments recorded yet</p><p class="bk-empty-sub">Record your first payment to track cash flow.</p><button class="bk-empty-btn" @click="openNew()"><span v-html="icon('plus',13)"></span> Record Payment</button></template></div></td></tr>
          </template>
        </tbody>
      </table>

      <!-- Mobile cards (shown at ≤768px) -->
      <div class="pay-mobile-cards">
        <template v-if="loading">
          <div v-for="n in 5" :key="n" class="pay-mobile-card pay-mc--skeleton">
            <div class="pay-mc-shimmer" style="height:13px;width:55%;margin-bottom:8px"></div>
            <div class="pay-mc-shimmer" style="height:11px;width:40%;margin-bottom:6px"></div>
            <div class="pay-mc-shimmer" style="height:11px;width:65%"></div>
          </div>
        </template>
        <div v-else-if="!sorted.length" class="pay-mc-empty">
          <div style="font-size:32px;margin-bottom:8px">💳</div>
          <div>No payments found</div>
        </div>
        <template v-else>
          <div v-for="p in paged" :key="p.name" class="pay-mobile-card" @click="openView(p)">
            <div class="pay-mc-top">
              <span class="pay-mc-docno">{{ p.name }}</span>
              <span class="inv-status-badge" :class="p.payment_type==='Receive'?'badge-green':'badge-red'">{{ p.payment_type==='Receive'?'Received':'Paid Out' }}</span>
            </div>
            <div class="pay-mc-mid">{{ p.party_name || p.party || '—' }}</div>
            <div class="pay-mc-meta">
              <span>{{ fmtDate(p.payment_date) }}</span>
              <span class="pay-mc-amount" :class="p.payment_type==='Receive'?'pay-mc-green':'pay-mc-red'">{{ fmtCur(p.paid_amount) }}</span>
            </div>
            <div v-if="p.mode_of_payment" class="pay-mc-sub">{{ p.mode_of_payment }}</div>
            <div class="pay-mc-footer">
              <button class="pay-mc-btn" @click.stop="openView(p)">View</button>
              <button v-if="p.docstatus===0" class="pay-mc-btn" @click.stop="openEdit(p)">Edit</button>
              <button v-if="p.docstatus===1" class="pay-mc-btn pay-mc-danger" @click.stop="cancelPmt(p)">Cancel</button>
              <button v-if="p.docstatus===0||p.docstatus===2" class="pay-mc-btn pay-mc-danger" @click.stop="deletePmt(p)">Delete</button>
            </div>
          </div>
        </template>
      </div>
    </div>

    <div v-if="!loading && sorted.length">
      <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="sorted.length" />
    </div>

    <!-- Create / Edit drawer -->
    <div v-if="drawerOpen" class="inv-drawer-bg" @click.self="drawerOpen=false"></div>
    <div class="inv-drawer-panel pmt-edit-drawer" :class="{open:drawerOpen}">

      <!-- Header -->
      <div class="pmt-dheader" :class="form.payment_type==='Pay'?'pay':'recv'">
        <div class="pmt-dheader-left">
          <div class="pmt-dheader-ico" :class="form.payment_type==='Pay'?'pay':'recv'">
            <span v-if="form.payment_type==='Pay'" v-html="icon('expense',18)"></span>
            <span v-else><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="13" y2="17"/></svg></span>
          </div>
          <div>
            <div class="pmt-dheader-title">{{ editingName?'Edit Payment':'New Payment' }}</div>
            <div class="pmt-dheader-sub">
              {{ editingName ? editingName : (form.payment_type==='Pay'?'Record an outgoing payment to a vendor':'Record a payment received from a customer') }}
            </div>
          </div>
        </div>
        <button class="inv-dclose pmt-dclose-light" @click="drawerOpen=false"><span v-html="icon('x',16)"></span></button>
      </div>

      <div class="inv-dbody pmt-dbody">

        <!-- ══ CARD 1: Payment Type ══ -->
        <div class="add-card">
          <div class="add-card-header" @click="pmtCollapsed.type=!pmtCollapsed.type">
            <div class="add-card-title">
              <span class="add-card-title-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              </span>
              Payment Type
            </div>
            <span class="add-card-chevron" :class="{collapsed:pmtCollapsed.type}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
          </div>
          <div class="add-card-body" :class="{collapsed:pmtCollapsed.type}">
            <div class="pmt-radio-group">
              <label class="pmt-radio" :class="{checked:form.payment_type==='Receive'}" @click="setPaymentType('Receive')">
                <span class="pmt-radio-dot" :class="{on:form.payment_type==='Receive'}"></span>
                <div>
                  <div class="pmt-radio-title">Received</div>
                  <div class="pmt-radio-sub">from a customer</div>
                </div>
              </label>
              <label class="pmt-radio" :class="{checked:form.payment_type==='Pay'}" @click="setPaymentType('Pay')">
                <span class="pmt-radio-dot" :class="{on:form.payment_type==='Pay'}"></span>
                <div>
                  <div class="pmt-radio-title">Paid Out</div>
                  <div class="pmt-radio-sub">to a vendor</div>
                </div>
              </label>
            </div>
          </div>
        </div>

        <!-- ══ CARD 2: Party & Amount ══ -->
        <div class="add-card">
          <div class="add-card-header" @click="pmtCollapsed.party=!pmtCollapsed.party">
            <div class="add-card-title">
              <span class="add-card-title-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              </span>
              {{ form.payment_type==='Receive'?'Customer & Amount':'Vendor & Amount' }}
            </div>
            <span class="add-card-chevron" :class="{collapsed:pmtCollapsed.party}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
          </div>
          <div class="add-card-body" :class="{collapsed:pmtCollapsed.party}">
            <div class="inv-fg inv-fg2">
              <div style="grid-column:1/-1">
                <label class="inv-lbl">{{ form.payment_type==='Receive'?'Customer':'Vendor' }} <span class="inv-req">*</span></label>
                <SearchableSelect v-model="form.party" :options="partyOptions"
                  :placeholder="form.payment_type==='Receive'?'Select customer…':'Select vendor…'"
                  @search="fetchParties" @select="onPartySelect" />
              </div>
              <div>
                <label class="inv-lbl">Amount <span class="inv-req">*</span></label>
                <input v-model.number="form.paid_amount" type="number" min="0" max="999999999" step="0.01" class="inv-fi" :class="{'field-error': form.paid_amount > 999999999}" placeholder="0.00" @input="syncUnallocated" />
                <div v-if="form.paid_amount > 999999999" class="exp-field-hint exp-field-hint-err">Amount cannot exceed 9 digits</div>
              </div>
              <div v-if="vendorTdsInfo?.applicable && tdsDeduction > 0" style="grid-column:1/-1">
                <div style="background:#fef3c7;border:1px solid #fde68a;border-radius:8px;padding:10px 14px;font-size:12.5px;display:flex;align-items:center;gap:8px">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                  <span style="color:#92400e">
                    <strong>TDS u/s {{ vendorTdsInfo.section }}</strong> already deducted at billing (est. ₹{{ tdsDeduction.toFixed(2) }}) —
                    Outstanding amount shown is the <strong>net payable to vendor</strong>. Pay exactly the outstanding amount.
                  </span>
                </div>
              </div>
              <div v-if="vendorTdsInfo?.applicable && !tdsDeduction" style="grid-column:1/-1">
                <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:8px 12px;font-size:12px;color:#1d4ed8">
                  TDS applicable u/s {{ vendorTdsInfo.section }} — select bills above to see the deduction amount
                </div>
              </div>
              <div>
                <label class="inv-lbl">Mode of Payment</label>
                <select v-model="form.mode_of_payment" class="inv-fi">
                  <option value="">— Select —</option>
                  <option v-for="m in paymentModes" :key="m" :value="m">{{ m }}</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        <!-- ══ CARD 3: Reference & Dates ══ -->
        <div class="add-card">
          <div class="add-card-header" @click="pmtCollapsed.ref=!pmtCollapsed.ref">
            <div class="add-card-title">
              <span class="add-card-title-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="9" x2="20" y2="9"/><line x1="4" y1="15" x2="20" y2="15"/><line x1="10" y1="3" x2="8" y2="21"/><line x1="16" y1="3" x2="14" y2="21"/></svg>
              </span>
              Reference &amp; Dates
            </div>
            <span class="add-card-chevron" :class="{collapsed:pmtCollapsed.ref}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
          </div>
          <div class="add-card-body" :class="{collapsed:pmtCollapsed.ref}">
            <div class="inv-fg inv-fg2">
              <div>
                <label class="inv-lbl">Payment Date <span class="inv-req">*</span></label>
                <input v-model="form.payment_date" type="date" class="inv-fi" />
              </div>
              <div>
                <label class="inv-lbl">Reference Date</label>
                <input v-model="form.reference_date" type="date" class="inv-fi" />
              </div>
              <div style="grid-column:1/-1">
                <label class="inv-lbl" style="display:flex;justify-content:space-between;align-items:center">
                  <span>Reference / Cheque No</span>
                  <span :style="{color: (form.reference_no||'').length > 140 ? '#ef4444' : (form.reference_no||'').length > 120 ? '#f59e0b' : '#9ca3af', fontSize:'11px', fontWeight:'600'}">
                    {{ (form.reference_no||"").length }}/140
                  </span>
                </label>
                <input v-model="form.reference_no" type="text" class="inv-fi" placeholder="e.g. CHQ-001, NEFT-78902" maxlength="140" />
              </div>
            </div>
          </div>
        </div>

        <!-- ══ CARD 4: Accounts ══ -->
        <div class="add-card">
          <div class="add-card-header" @click="pmtCollapsed.accounts=!pmtCollapsed.accounts">
            <div class="add-card-title">
              <span class="add-card-title-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
              </span>
              Accounts
            </div>
            <span class="add-card-chevron" :class="{collapsed:pmtCollapsed.accounts}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
          </div>
          <div class="add-card-body" :class="{collapsed:pmtCollapsed.accounts}">
            <div class="inv-fg inv-fg2">
              <div>
                <label class="inv-lbl">Paid From <span style="font-weight:400;color:#9ca3af;font-size:10.5px">({{ form.payment_type==='Receive'?'Receivable':'Bank / Cash' }})</span></label>
                <SearchableSelect v-model="form.paid_from" :options="paidFromAccounts" placeholder="Select account…" @search="fetchPaidFromAccounts" @open="fetchPaidFromAccounts('')" />
              </div>
              <div>
                <label class="inv-lbl">Paid To <span style="font-weight:400;color:#9ca3af;font-size:10.5px">({{ form.payment_type==='Receive'?'Bank / Cash':'Payable' }})</span></label>
                <SearchableSelect v-model="form.paid_to" :options="paidToAccounts" placeholder="Select account…" @search="fetchPaidToAccounts" @open="fetchPaidToAccounts('')" />
              </div>
            </div>
          </div>
        </div>

        <!-- ══ CARD 5: Outstanding Invoices / Allocation ══ -->
        <div class="add-card">
          <div class="add-card-header" @click="pmtCollapsed.alloc=!pmtCollapsed.alloc">
            <div class="add-card-title">
              <span class="add-card-title-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
              </span>
              Outstanding {{ form.payment_type==='Receive'?'Invoices':'Bills' }}
            </div>
            <div style="display:flex;align-items:center;gap:10px">
              <span v-if="form.party" class="pmt-unalloc-badge" :class="unallocated<-0.01?'red':unallocated>0.01?'orange':''">
                Unallocated: {{ fmtCur(unallocated) }}
              </span>
              <span class="add-card-chevron" :class="{collapsed:pmtCollapsed.alloc}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
              </span>
            </div>
          </div>
          <div class="add-card-body" :class="{collapsed:pmtCollapsed.alloc}" style="padding:0">
            <div v-if="!form.party" class="pmt-inv-empty" style="margin:16px">Select a party to load outstanding invoices</div>
            <div v-else-if="invLoading" class="pmt-inv-empty" style="margin:16px"><span style="color:#9ca3af">Loading invoices…</span></div>
            <div v-else-if="!outstandingInvoices.length" class="pmt-inv-empty" style="margin:16px">No outstanding {{ form.payment_type==='Receive'?'invoices':'bills' }} for this party</div>
            <div v-else class="pmt-inv-table" style="border:none;border-radius:0">
              <div class="pmt-inv-head">
                <div></div><div>Document</div><div>Date</div>
                <div class="ta-r">Outstanding</div><div class="ta-r">Allocate</div>
              </div>
              <div v-for="ref in invoiceRefs" :key="ref.reference_name" class="pmt-inv-row">
                <div><input type="checkbox" v-model="ref.checked" @change="onRefCheck(ref)" /></div>
                <div><span class="pmt-inv-name">{{ ref.reference_name }}</span></div>
                <div class="mono-sm text-muted">{{ fmtDate(ref.due_date) }}</div>
                <div class="ta-r mono-sm">{{ fmtCur(ref.outstanding_amount) }}</div>
                <div>
                  <input v-if="ref.checked" v-model.number="ref.allocated_amount" type="number" min="0" :max="ref.outstanding_amount" step="0.01" class="pmt-alloc-input" @input="syncUnallocated" />
                  <span v-else class="mono-sm text-muted">—</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ══ CARD 6: Notes ══ -->
        <div class="add-card">
          <div class="add-card-header" @click="pmtCollapsed.notes=!pmtCollapsed.notes">
            <div class="add-card-title">
              <span class="add-card-title-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
              </span>
              Notes
            </div>
            <span class="add-card-chevron" :class="{collapsed:pmtCollapsed.notes}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
          </div>
          <div class="add-card-body" :class="{collapsed:pmtCollapsed.notes}">
            <textarea v-model="form.remarks" rows="3" maxlength="500" class="inv-fi" placeholder="Optional notes about this payment…"></textarea>
            <div style="text-align:right;font-size:12px;color:#94a3b8;margin-top:4px;">{{ (form.remarks || '').length }}/500</div>
          </div>
        </div>

      </div>

      <div class="inv-dfooter">
        <button class="form-btn form-btn-outline" @click="drawerOpen=false" :disabled="drawerSaving">Cancel</button>
        <div>
        <button class="add-btn-draft" style="margin-right:5px" :disabled="drawerSaving" @click="savePayment(0)">
          <span v-html="icon('save',13)"></span> {{ drawerSaving?'Saving…':'Save Draft' }}
        </button>
        <button class="add-btn-more" :disabled="drawerSaving" @click="savePayment(1)">
          <span v-html="icon('check',13)"></span> {{ drawerSaving?'Saving…':'Submit' }}
        </button>
        </div>
      </div>
    </div>

    <!-- View drawer -->
    <div v-if="viewOpen" class="inv-drawer-bg" @click.self="viewOpen=false"></div>
    <div class="inv-drawer-panel pmt-view-drawer" :class="{open:viewOpen}">
      <template v-if="viewPmt">

        <!-- ── Header card: Payment # + amount + status ── -->
        <div class="pmt-vd-body">
          <div class="pmt-vd-hero-card">
            <div class="pmt-vd-hero-left">
              <div class="pmt-vd-hero-num">{{ viewPmt.name }}</div>
              <div class="pmt-vd-hero-party">
                <DocLink :doctype="viewPmt.party_type || (viewPmt.payment_type==='Receive'?'Customer':'Supplier')" :name="viewPmt.party" :mono-style="false">
                  {{ viewPmt.party_name || viewPmt.party || '—' }}
                </DocLink>
              </div>
            </div>
            <div class="pmt-vd-hero-right">
              <div class="pmt-vd-hero-amount">{{ fmtCur(viewPmt.paid_amount) }}</div>
              <span class="pmt-vd-status-badge" :class="viewPmt.payment_type==='Receive'?'pmt-vd-badge-green':'pmt-vd-badge-red'">
                <span class="pmt-vd-badge-dot"></span>
                {{ viewPmt.payment_type==='Receive'?'RECEIVED':'PAID OUT' }}
              </span>
            </div>
            <button class="pmt-vd-close" @click="viewOpen=false"><span v-html="icon('x',15)"></span></button>
          </div>

          <!-- ── Payment Details card ── -->
          <div class="pmt-vd-card">
            <div class="pmt-vd-card-title">PAYMENT DETAILS</div>
            <div class="pmt-vd-meta-grid">
              <div>
                <div class="pmt-vd-lbl">PAYMENT DATE</div>
                <div class="pmt-vd-val">{{ fmtDate(viewPmt.payment_date) }}</div>
              </div>
              <div>
                <div class="pmt-vd-lbl">MODE</div>
                <div class="pmt-vd-val">{{ viewPmt.mode_of_payment||'—' }}</div>
              </div>
              <div>
                <div class="pmt-vd-lbl">REFERENCE NO</div>
                <div class="pmt-vd-val mono-sm">{{ viewPmt.reference_no||'—' }}</div>
              </div>
              <div>
                <div class="pmt-vd-lbl">REFERENCE DATE</div>
                <div class="pmt-vd-val mono-sm">{{ fmtDate(viewPmt.reference_date) }}</div>
              </div>
              <div>
                <div class="pmt-vd-lbl">PAID FROM</div>
                <div class="pmt-vd-val">{{ paymentAccountLabel(viewPmt.paid_from) }}</div>
              </div>
              <div>
                <div class="pmt-vd-lbl">PAID TO</div>
                <div class="pmt-vd-val">{{ paymentAccountLabel(viewPmt.paid_to) }}</div>
              </div>
            </div>
          </div>

          <!-- ── Linked Documents card ── -->
          <div class="pmt-vd-card" v-if="viewPmt.references&&viewPmt.references.length">
            <div class="pmt-vd-card-title">LINKED DOCUMENTS</div>
            <table class="pmt-vd-link-table">
              <thead>
                <tr>
                  <th style="text-align: left;">DOCUMENT</th>
                  <th class="ta-r">OUTSTANDING</th>
                  <th class="ta-r">ALLOCATED</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in viewPmt.references" :key="r.reference_name">
                  <td>
                    <DocLink :doctype="r.reference_doctype || (viewPmt.payment_type==='Receive'?'Sales Invoice':'Purchase Invoice')" :name="r.reference_name" />
                  </td>
                  <td class="ta-r mono-sm">{{ fmtCur(r.outstanding_amount) }}</td>
                  <td class="ta-r mono-sm pmt-vd-alloc-green">{{ fmtCur(r.allocated_amount) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- ── Remarks card ── -->
          <div class="pmt-vd-card" v-if="viewPmt.remarks">
            <div class="pmt-vd-card-title">REMARKS</div>
            <div class="pmt-vd-remarks">{{ viewPmt.remarks }}</div>
          </div>

          <!-- ── Journal (debit/credit ledger) card ── -->
          <div class="pmt-vd-card">
            <div class="pmt-vd-card-title">JOURNAL</div>
            <template v-if="viewPmt.docstatus===1">
              <JournalTab
                voucher-type="Payment Entry"
                :voucher-no="viewPmt.name"
                label="Payment"
                :currency="viewPmt.paid_from_account_currency || viewPmt.currency || 'INR'"
              />
            </template>
            <div v-else style="color:#9ca3af;font-size:13px;padding:8px 0">Journal entries are posted once the payment is submitted.</div>
          </div>
        </div>

        <!-- ── Footer ── -->
        <div class="inv-dfooter">
          <button class="pmt-vd-btn-close" @click="viewOpen=false">Close</button>
          <div style="display:flex;gap:8px">
            <button v-if="viewPmt.docstatus===0" class="form-btn form-btn-success" @click="openEdit(viewPmt);viewOpen=false">
              <span v-html="icon('edit',13)"></span> Edit
            </button>
            <button v-if="viewPmt.docstatus===1" class="pmt-vd-btn-cancel" @click="cancelPmt(viewPmt)">
              Cancel Payment
            </button>
            <button v-if="viewPmt.docstatus===0 || viewPmt.docstatus===2" class="pmt-vd-btn-cancel" @click="deletePmt(viewPmt)">
              <span v-html="icon('trash',13)"></span> Delete
            </button>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import { apiList, apiGet, apiGET, apiSave, apiSubmit, apiPOST, apiDelete, resolveCompany, apiLinkValues } from "../api/client.js";
import { useConfirm } from "../composables/useConfirm.js";
import { useOpenFromQuery } from "../composables/useOpenFromQuery.js";
import { usePagination } from "../composables/usePagination.js";
import DocLink from "../components/DocLink.vue";
import Pagination from "../components/Pagination.vue";
import SummaryStrip from "../components/SummaryStrip.vue";
import JournalTab from "../components/JournalTab.vue";
const { confirm } = useConfirm();

async function cancelPmt(p) {
  if (!canWrite("payments")) { toast("Read-only access", "error"); return; }
  if (!await confirm({ title: "Cancel Payment", body: `Cancel ${p.name}? Linked invoices/bills will reflect the reversal.`, okLabel: "Cancel Payment" })) return;
  try {
    await apiPOST("zoho_books_clone.api.docs.cancel_payment_entry_safe",
      { payment_entry_name: p.name });
    toast.success(`Payment ${p.name} cancelled`);
    viewOpen.value = false;
    await load();
  } catch (e) { toast.error(e.message || "Cancel failed"); }
}
async function deletePmt(p) {
  if (!canWrite("payments")) { toast("Read-only access", "error"); return; }
  if (!await confirm({ title: "Delete Payment", body: `Permanently delete ${p.name}? This cannot be undone.`, okLabel: "Delete" })) return;
  try {
    await apiDelete("Payment Entry", p.name);
    toast.success(`Payment ${p.name} deleted`);
    viewOpen.value = false;
    await load();
  } catch (e) { toast.error(e.message || "Delete failed"); }
}

// ─── Bulk actions ──────────────────────────────────────────────────────
const bulkBusy = ref(false);
function selectedRows() {
  return sorted.value.filter(p => selected.value.has(p.name));
}
async function bulkCancel() {
  if (!canWrite("payments")) { toast("Read-only access", "error"); return; }
  const rows = selectedRows().filter(p => p.docstatus === 1);
  if (!rows.length) { toast.info?.("No submitted payments selected") || toast.error("No submitted payments selected"); return; }
  if (!await confirm({ title: `Cancel ${rows.length} payment(s)?`, body: "Linked invoices/bills will reflect the reversal.", okLabel: "Cancel All", okStyle: "danger" })) return;
  bulkBusy.value = true;
  let ok = 0, fail = 0;
  for (const p of rows) {
    try { await apiPOST("zoho_books_clone.api.docs.cancel_payment_entry_safe", { payment_entry_name: p.name }); ok++; }
    catch { fail++; }
  }
  bulkBusy.value = false;
  toast.success(`${ok} cancelled${fail?`, ${fail} failed`:''}`);
  selected.value = new Set();
  await load();
}
async function bulkDelete() {
  if (!canWrite("payments")) { toast("Read-only access", "error"); return; }
  const rows = selectedRows().filter(p => p.docstatus === 0 || p.docstatus === 2);
  if (!rows.length) { toast.error("No draft/cancelled payments selected"); return; }
  if (!await confirm({ title: `Delete ${rows.length} payment(s)?`, body: "Only drafts and cancelled records can be deleted. This cannot be undone.", okLabel: "Delete All", okStyle: "danger" })) return;
  bulkBusy.value = true;
  let ok = 0, fail = 0;
  for (const p of rows) {
    try { await apiDelete("Payment Entry", p.name); ok++; }
    catch { fail++; }
  }
  bulkBusy.value = false;
  toast.success(`${ok} deleted${fail?`, ${fail} failed`:''}`);
  selected.value = new Set();
  await load();
}
function bulkExport() {
  const rows = selectedRows();
  if (!rows.length) return;
  const headers = ["Payment #","Party","Mode","Reference","Reference Date","Payment Date","Type","Amount","Status"];
  const lines = rows.map(p => [
    p.name, p.party_name || p.party || "", p.mode_of_payment || "",
    p.reference_no || "", p.reference_date || "", p.payment_date || "",
    p.payment_type === "Receive" ? "Received" : "Paid Out",
    p.paid_amount,
    p.docstatus === 1 ? "Submitted" : p.docstatus === 2 ? "Cancelled" : "Draft",
  ]);
  const esc = (v) => { const s = v == null ? "" : String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  const csv = "﻿" + [headers, ...lines].map(r => r.map(esc).join(",")).join("\r\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `payments-${new Date().toISOString().slice(0,10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
  toast.success(`${rows.length} row(s) exported`);
}
import { useToast } from "../composables/useToast.js";
import { usePermissions } from "../composables/usePermissions.js";
import { icon } from "../utils/icons.js";
import { flt, fmtDate } from "../utils/format.js";
import SearchableSelect from "../components/SearchableSelect.vue";

const { toast } = useToast();
const { canWrite } = usePermissions();
const route = useRoute();
const defaultTab = computed(() => route.path === "/payments-received" ? "Receive" : "Pay");
const activeTab = ref(defaultTab.value);
const tabs = [{key:"all",label:"All"},{key:"Receive",label:"Received"},{key:"Pay",label:"Paid Out"}];

const list = ref([]), loading = ref(false), search = ref(""), selected = ref(new Set());
const drawerOpen = ref(false), drawerSaving = ref(false), editingName = ref("");
// Plain (non-reactive) guard — checked/set synchronously the instant savePayment()
// is called, before any await. drawerSaving alone isn't enough: it's a reactive
// ref, so the button's :disabled attribute only updates on Vue's next render —
// two clicks that land within that window can both slip past it and each
// insert their own Payment Entry. This flag closes that race immediately.
let _savingInFlight = false;
const viewOpen = ref(false), viewPmt = ref(null);
const pmtCollapsed = reactive({ type: false, party: false, ref: false, accounts: true, alloc: false, notes: true });
const partyOptions = ref([]), paidFromAccounts = ref([]), paidToAccounts = ref([]);
const paymentAccountLabelCache = ref({});
function paymentAccountLabel(name){
  if(!name) return '—';
  const opt = paidFromAccounts.value.find(o=>o.value===name) || paidToAccounts.value.find(o=>o.value===name);
  if(opt) return opt.label;
  if(paymentAccountLabelCache.value[name]) return paymentAccountLabelCache.value[name];
  apiList("Account", { fields:["name","account_name"], filters:[["name","=",name]], limit:1 })
    .then(rows => { paymentAccountLabelCache.value[name] = rows?.[0]?.account_name || name; })
    .catch(() => { paymentAccountLabelCache.value[name] = name; });
  return name;
}
const paymentModes = ref(["Cash","Bank Transfer","Cheque","Credit Card","UPI","NEFT","RTGS"]);
const sortCol = ref("payment_date"), sortDir = ref("desc");

// Invoice linking state
const outstandingInvoices = ref([]);
const invoiceRefs = ref([]);
const invLoading = ref(false);

// TDS deduction tracking
const vendorTdsInfo = ref(null); // { applicable, section, rate } from Supplier doc

const blankForm = () => ({
  doctype: "Payment Entry",
  payment_type: defaultTab.value === "Receive" ? "Receive" : "Pay",
  party_type: defaultTab.value === "Receive" ? "Customer" : "Supplier",
  party: "", mode_of_payment: "", paid_amount: "",
  payment_date: new Date().toISOString().slice(0,10),
  reference_no: "", reference_date: "", paid_from: "", paid_to: "", remarks: "",
});
const form = reactive(blankForm());

const unallocated = computed(() => {
  const alloc = invoiceRefs.value.filter(r => r.checked).reduce((s, r) => s + flt(r.allocated_amount), 0);
  return flt(form.paid_amount) - alloc;
});

// outstanding_amount on each bill is already NET of TDS (TDS was deducted at bill creation).
// tdsDeduction is purely informational — DO NOT subtract it again from paid_amount.
const tdsDeduction = computed(() => {
  if (!vendorTdsInfo.value?.applicable || !vendorTdsInfo.value.rate) return 0;
  // Estimate: outstanding already has TDS removed, so gross ≈ outstanding / (1 - rate/100)
  const net = invoiceRefs.value.filter(r => r.checked).reduce((s, r) => s + flt(r.outstanding_amount), 0);
  if (!net) return 0;
  const rate = vendorTdsInfo.value.rate;
  const gross = Math.round(net / (1 - rate / 100) * 100) / 100;
  return Math.round((gross - net) * 100) / 100;
});

// When bills are checked/unchecked: set paid_amount AND allocated_amount together.
// onRefCheck runs before the watch (Vue timing), so it can't safely read paid_amount yet.
// All allocation logic lives here so values are consistent when savePayment reads them.
watch(() => invoiceRefs.value.map(r => r.checked), () => {
  const checkedRefs = invoiceRefs.value.filter(r => r.checked);
  const net = checkedRefs.reduce((s, r) => s + flt(r.outstanding_amount), 0);
  if (net > 0) {
    form.paid_amount = net;
    let remaining = net;
    for (const ref of checkedRefs) {
      const alloc = Math.min(flt(ref.outstanding_amount), remaining);
      ref.allocated_amount = alloc;
      remaining = Math.max(0, remaining - alloc);
    }
  }
  // Clear any unchecked refs
  invoiceRefs.value.filter(r => !r.checked).forEach(r => { r.allocated_amount = 0; });
}, { deep: true });

async function load() {
  loading.value = true;
  try {
    list.value = await apiList("Payment Entry", {
      fields: ["name","party","party_name","party_type","paid_amount","payment_type","payment_date",
               "mode_of_payment","reference_no","reference_date","paid_from","paid_to","remarks","docstatus"],
      limit: 200, order: "payment_date desc, creation desc",
    });
  } catch (e) { toast.error(e.message || "Failed to load payments"); }
  finally { loading.value = false; }
}

const filtered = computed(() => {
  let r = list.value;
  if (activeTab.value !== "all") r = r.filter(p => p.payment_type === activeTab.value);
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    r = r.filter(p => (p.name||"").toLowerCase().includes(q) || (p.party_name||p.party||"").toLowerCase().includes(q) || (p.reference_no||"").toLowerCase().includes(q));
  }
  return r;
});
const sorted = computed(() => {
  const col = sortCol.value;
  return [...filtered.value].sort((a, b) => {
    const av = a[col] ?? "", bv = b[col] ?? "";
    const cmp = typeof av === "number" ? av - bv : String(av).localeCompare(String(bv));
    return sortDir.value === "asc" ? cmp : -cmp;
  });
});
function sort(col) { if (sortCol.value===col) sortDir.value=sortDir.value==="asc"?"desc":"asc"; else{sortCol.value=col;sortDir.value="asc";} }
function sortArrow(col) { if (sortCol.value!==col) return '<span style="color:#d1d5db">⇅</span>'; return sortDir.value==="asc"?"↑":"↓"; }

const { page, pageSize, paged } = usePagination(sorted, { storageKey: "payments" });

const summaryReceived = computed(() => list.value.filter(p=>p.payment_type==="Receive").reduce((s,p)=>s+flt(p.paid_amount),0));
const summaryPaid = computed(() => list.value.filter(p=>p.payment_type==="Pay").reduce((s,p)=>s+flt(p.paid_amount),0));
const _pYM  = () => { const d=new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; };
const _pLYM = () => { const d=new Date(); d.setMonth(d.getMonth()-1); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; };
const _pTrend=(a,b)=>{ if(!b&&!a) return {pct:0,up:true}; if(!b) return {pct:100,up:true}; const p=Math.round((a-b)/b*100); return {pct:Math.abs(p),up:p>=0}; };
const pmtThisMonth = computed(()=>{ const ym=_pYM(); const r=list.value.filter(p=>(p.payment_date||'').startsWith(ym)); return {count:r.length,received:r.filter(p=>p.payment_type==="Receive").reduce((s,p)=>s+flt(p.paid_amount),0),paid:r.filter(p=>p.payment_type==="Pay").reduce((s,p)=>s+flt(p.paid_amount),0)}; });
const pmtAvg = computed(()=>{ const p=list.value.filter(x=>x.paid_amount>0); return p.length?p.reduce((s,x)=>s+flt(x.paid_amount),0)/p.length:0; });
const pmtTrends = computed(()=>({
  total:    _pTrend(pmtThisMonth.value.count, list.value.filter(p=>(p.payment_date||'').startsWith(_pLYM())).length),
  received: _pTrend(pmtThisMonth.value.received, list.value.filter(p=>(p.payment_date||'').startsWith(_pLYM())&&p.payment_type==="Receive").reduce((s,p)=>s+flt(p.paid_amount),0)),
  paid:     _pTrend(pmtThisMonth.value.paid, list.value.filter(p=>(p.payment_date||'').startsWith(_pLYM())&&p.payment_type==="Pay").reduce((s,p)=>s+flt(p.paid_amount),0)),
}));
function fmtCur(v) { return new Intl.NumberFormat("en-IN",{style:"currency",currency:"INR",minimumFractionDigits:2}).format(flt(v)); }

const allChecked = computed(() => sorted.value.length > 0 && sorted.value.every(p => selected.value.has(p.name)));
function toggle(name) { const s = new Set(selected.value); s.has(name)?s.delete(name):s.add(name); selected.value=s; }
function toggleAll(e) { selected.value = e.target.checked ? new Set(sorted.value.map(p=>p.name)) : new Set(); }

function openNew() {
  editingName.value = "";
  Object.assign(form, blankForm());
  // Always respect the route context: /payments-received => Receive (Sales), /payments => Pay (Purchase)
  form.payment_type = defaultTab.value;
  form.party_type = form.payment_type === "Receive" ? "Customer" : "Supplier";
  outstandingInvoices.value = [];
  invoiceRefs.value = [];
  Object.assign(pmtCollapsed, { type: false, party: false, ref: false, accounts: true, alloc: false, notes: true });
  fetchParties(""); fetchPaidFromAccounts(""); fetchPaidToAccounts("");
  drawerOpen.value = true;
}

async function openEdit(p) {
  editingName.value = p.name;
  Object.assign(form, {
    doctype: "Payment Entry", name: p.name, payment_type: p.payment_type,
    party_type: p.party_type, party: p.party||"", mode_of_payment: p.mode_of_payment||"",
    paid_amount: flt(p.paid_amount), payment_date: p.payment_date||new Date().toISOString().slice(0,10),
    reference_no: p.reference_no||"", reference_date: p.reference_date||"",
    paid_from: p.paid_from||"", paid_to: p.paid_to||"", remarks: p.remarks||"",
  });
  outstandingInvoices.value = []; invoiceRefs.value = [];
  Object.assign(pmtCollapsed, { type: false, party: false, ref: false, accounts: true, alloc: false, notes: true });
  fetchParties(""); fetchPaidFromAccounts(""); fetchPaidToAccounts("");
  drawerOpen.value = true;
  if (p.party) await fetchOutstandingInvoices(p.party, p.payment_type);
}

async function openView(p) {
  viewPmt.value = p;
  viewOpen.value = true;
  // Fetch full doc to get references child table
  try {
    const doc = await apiGet("Payment Entry", p.name);
    viewPmt.value = { ...p, references: doc.references || [] };
  } catch {}
}

function setPaymentType(type) {
  form.payment_type = type;
  form.party_type = type === "Receive" ? "Customer" : "Supplier";
  form.party = ""; form.paid_from = ""; form.paid_to = "";
  outstandingInvoices.value = []; invoiceRefs.value = [];
  fetchParties("");
  fetchPaidFromAccounts(""); fetchPaidToAccounts("");
}

async function fetchParties(q = "") {
  const dt = form.payment_type === "Receive" ? "Customer" : "Supplier";
  const nameField = dt === "Customer" ? "customer_name" : "supplier_name";
  try {
    const filters = [["disabled", "=", 0]];
    if (q) filters.push([nameField, "like", "%" + q + "%"]);
    const rows = await apiList(dt, { fields: ["name", nameField], filters, limit: 30, order: nameField + " asc" });
    partyOptions.value = rows.map(r => ({ label: r[nameField] || r.name, value: r.name }));
  } catch { partyOptions.value = []; }
}

async function onPartySelect(opt) {
  // SearchableSelect's @select emits the full {label, value} option object;
  // v-model="form.party" already updates form.party via update:modelValue.
  // Outstanding-invoice loading is handled by the watch() below, so this
  // handler is now a no-op kept for backwards compatibility.
  const party = (opt && typeof opt === "object") ? opt.value : opt;
  if (party && typeof party === "string" && party !== form.party) form.party = party;
}

// Reload outstanding invoices/bills whenever the party OR payment type changes,
// regardless of which UI control mutated them.
watch(() => [form.party, form.payment_type], async ([p, t], [oldP, oldT]) => {
  if (!p) {
    outstandingInvoices.value = [];
    invoiceRefs.value = [];
    vendorTdsInfo.value = null;
    return;
  }
  if (p === oldP && t === oldT) return;
  await fetchOutstandingInvoices(p, t);
  // Fetch TDS info for vendor payments only
  if (t === "Pay") {
    try {
      const doc = await apiGET("zoho_books_clone.api.docs.get_doc", { doctype: "Supplier", name: p });
      vendorTdsInfo.value = doc?.tds_applicable
        ? { applicable: true, section: doc.tds_section || "", rate: Number(doc.tds_section ? { "194C":1,"194J":10,"194A":10,"194H":5,"194I":10,"192":0,"195":20 }[doc.tds_section] ?? 10 : 0) }
        : null;
    } catch { vendorTdsInfo.value = null; }
  } else {
    vendorTdsInfo.value = null;
  }
});

async function fetchOutstandingInvoices(party, pmtType) {
  if (!party) return;
  invLoading.value = true;
  try {
    const dt = pmtType === "Receive" ? "Sales Invoice" : "Purchase Invoice";
    const partyField = pmtType === "Receive" ? "customer" : "supplier";
    const co = await resolveCompany();
    const rows = await apiList(dt, {
      fields: ["name", "posting_date", "due_date", "grand_total", "outstanding_amount"],
      filters: [["company","=",co],[partyField,"=",party],["docstatus","=",1],["outstanding_amount",">",0]],
      limit: 50, order: "posting_date asc",
    });
    outstandingInvoices.value = rows;
    invoiceRefs.value = rows.map(r => ({
      reference_doctype: dt,
      reference_name: r.name,
      outstanding_amount: flt(r.outstanding_amount),
      due_date: r.due_date || r.posting_date,
      allocated_amount: 0,
      checked: false,
    }));
  } catch { outstandingInvoices.value = []; invoiceRefs.value = []; }
  finally { invLoading.value = false; }
}

function onRefCheck(_ref) {
  // Allocation is fully managed by the watcher above — nothing to do here.
}

function syncUnallocated() {} // triggers computed

async function fetchPaidFromAccounts(q = "") {
  try {
    const company = await resolveCompany();
    // Receive: party pays us → Paid From is their Receivable account
    // Pay: we pay vendor → Paid From is our Bank/Cash account
    const types = form.payment_type === "Receive" ? ["Receivable"] : ["Bank","Cash"];
    const rows = await apiList("Account", {
      fields: ["name","account_name","account_type"],
      filters: [["is_group","=",0],["company","=",company],["account_type","in",types],...(q?[["name","like",`%${q}%`]]:[])],
      limit: 30,
    });
    paidFromAccounts.value = rows.map(r=>({label:r.account_name||r.name,value:r.name}));
  } catch { paidFromAccounts.value = []; }
}

async function fetchPaidToAccounts(q = "") {
  try {
    const company = await resolveCompany();
    // Receive: customer pays us → Paid To is our Bank/Cash account
    // Pay: we pay vendor → Paid To is their Payable account
    const types = form.payment_type === "Receive" ? ["Bank","Cash"] : ["Payable"];
    const rows = await apiList("Account", {
      fields: ["name","account_name","account_type"],
      filters: [["is_group","=",0],["company","=",company],["account_type","in",types],...(q?[["name","like",`%${q}%`]]:[])],
      limit: 30,
    });
    paidToAccounts.value = rows.map(r=>({label:r.account_name||r.name,value:r.name}));
  } catch { paidToAccounts.value = []; }
}

async function savePayment(submit) {
  if (_savingInFlight) return; // synchronous guard — blocks a second click before Vue can disable the button
  if (!form.party) return toast.error("Party is required");
  if (!form.paid_amount || flt(form.paid_amount) <= 0) return toast.error("Amount must be greater than 0");
  if (flt(form.paid_amount) > 999999999) return toast.error("Amount cannot exceed 9 digits (max ₹999,999,999)");
  if (!form.payment_date) return toast.error("Payment date is required");
  _savingInFlight = true;
  drawerSaving.value = true;
  try {
    const company = await resolveCompany();
    const checkedRefs = invoiceRefs.value.filter(r => r.checked && flt(r.allocated_amount) > 0);
    const references = checkedRefs.map(r => ({
      doctype: "Payment Entry Reference",
      reference_doctype: r.reference_doctype,
      reference_name: r.reference_name,
      outstanding_amount: flt(r.outstanding_amount),
      allocated_amount: flt(r.allocated_amount),
    }));
    // Resolve party_name from the selected option so Frappe stores it on the record
    const selectedPartyOpt = partyOptions.value.find(o => o.value === form.party);
    const partyName = selectedPartyOpt?.label || form.party;
    const doc = {
      doctype: "Payment Entry", company,
      payment_type: form.payment_type, party_type: form.party_type, party: form.party, party_name: partyName,
      mode_of_payment: form.mode_of_payment || "Cash",
      paid_amount: flt(form.paid_amount), received_amount: flt(form.paid_amount),
      payment_date: form.payment_date,
      reference_no: form.reference_no || "", reference_date: form.reference_date || null,
      paid_from: form.paid_from || "", paid_to: form.paid_to || "",
      remarks: form.remarks || "",
      references,
    };
    if (editingName.value) doc.name = editingName.value;
    const saved = await apiSave(doc);
    // Critical: remember the name we just created/updated. Without this, any
    // further save call in this drawer session (accidental double-click, or
    // Save Draft followed by Submit) would insert a brand-new Payment Entry
    // instead of updating the one that already exists.
    editingName.value = saved.name;
    if (submit) await apiSubmit("Payment Entry", saved.name);
    toast.success(`Payment ${saved?.name||""} ${submit?"submitted":"saved"}`);
    drawerOpen.value = false;
    await load();
  } catch (e) { toast.error(e.message || "Failed to save payment"); }
  finally { drawerSaving.value = false; _savingInFlight = false; }
}

onMounted(async () => {
  await load();
  useOpenFromQuery({
    route,
    openByName: (n) => openView(list.value.find(x => x.name === n) || { name: n }),
  });
});
</script>

<style scoped>
.space-top { margin-top: 16px; }
.section-card{ background: #fff; padding: 10px; border-radius: 15px; box-shadow: 0 1px 2px #0f172a08; }
/* ── Edit drawer width override ── */
.pmt-edit-drawer { width: 580px; right: -580px; transition: right .24s cubic-bezier(.32,.72,0,1); position: fixed; top: 0; bottom: 0; }
.pmt-edit-drawer.open { right: 0; }

/* ── View drawer width override ── */
.pmt-view-drawer { width: 625px; right: -625px; transition: right .24s cubic-bezier(.32,.72,0,1); position: fixed; top: 0; bottom: 0; }
.pmt-view-drawer.open { right: 0; }

/* ── Payment-specific drawer header (light bg, not gradient) ── */
.pmt-dheader { display:flex; align-items:flex-start; justify-content:space-between; padding:18px 20px; border-bottom:1px solid #e5e7eb; flex-shrink:0; background:linear-gradient(135deg,#eff6ff 0%,#dbeafe 100%); }
.pmt-dheader.recv { background:linear-gradient(135deg,#f0fdf4 0%,#bbf7d0 100%); }
.pmt-dheader.pay  { background:linear-gradient(135deg,#fff1f2 0%,#fecaca 100%); }
.pmt-dheader-left { display:flex; align-items:flex-start; gap:12px; }
.pmt-dheader-ico  { width:38px; height:38px; border-radius:10px; background:#fff; border:1px solid rgba(37,99,235,.18); display:inline-flex; align-items:center; justify-content:center; color:#2563eb; box-shadow:0 1px 3px rgba(15,23,42,.06); flex-shrink:0; }
.pmt-dheader-ico.recv { color:#16a34a; border-color:rgba(22,163,74,.22); }
.pmt-dheader-ico.pay  { color:#dc2626; border-color:rgba(220,38,38,.25); }
.pmt-dheader-title { font-size:15px; font-weight:700; color:#111827; letter-spacing:-0.01em; }
.pmt-dheader-sub   { font-size:12px; color:#475569; margin-top:3px; font-weight:500; }
/* Close button override for light header */
.pmt-dclose-light  { background:rgba(0,0,0,.06); color:#475569; }
.pmt-dclose-light:hover { background:rgba(0,0,0,.12); color:#111827; }

/* ── Body: section card style ── */
.pmt-dbody { background:#f0f4f8; padding: 14px; display:flex; flex-direction:column; gap:0; }

/* add-card inside pmt-dbody: white cards with spacing */
.pmt-dbody .add-card {
  background: #fff;
  border: 1px solid #e3e8ef;
  border-radius: 10px;
  margin-bottom: 10px;
  box-shadow: 0 1px 3px rgba(15,23,42,.04);
}
.pmt-dbody .add-card:last-child { margin-bottom: 0; }

.pmt-dbody .add-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #e8ecf0;
  cursor: pointer;
  user-select: none;
  border-radius: 10px 10px 0 0;
}
.pmt-dbody .add-card-header:has(+ .add-card-body.collapsed) { border-bottom: none; border-radius: 10px; }
.pmt-dbody .add-card-body.collapsed + * { display: none; }

.pmt-dbody .add-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
  color: #1a1a2e;
}
.pmt-dbody .add-card-title-icon {
  width: 20px; height: 20px;
  display: flex; align-items: center; justify-content: center;
  color: #1565c0; flex-shrink: 0;
}
.pmt-dbody .add-card-chevron {
  color: #9ca3af;
  transition: transform .2s;
  display: inline-flex;
}
.pmt-dbody .add-card-chevron.collapsed { transform: rotate(-90deg); }
.pmt-dbody .add-card-body { padding: 16px; }
.pmt-dbody .add-card-body.collapsed { display: none; }

/* Unallocated badge inside card header */
.pmt-unalloc-badge {
  font-size: 11.5px;
  font-weight: 700;
  color: #16a34a;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 5px;
  padding: 2px 8px;
}
.pmt-unalloc-badge.orange { color: #ea580c; background: #fff7ed; border-color: #fed7aa; }
.pmt-unalloc-badge.red    { color: #dc2626; background: #fff1f2; border-color: #fecaca; }
.pmt-section-hdr-bar { display:flex; align-items:center; gap:8px; font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:#0f172a; }
.pmt-section-hdr-bar .pmt-unalloc { margin-left:auto; text-transform:none; font-size:11.5px; font-weight:700; color:#16a34a; }
.pmt-section-hdr-bar .pmt-unalloc.red { color:#dc2626; }
.pmt-section-hdr-bar .pmt-unalloc.orange { color:#ea580c; }

/* ── Radio group ── */
.pmt-radio-group { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
.pmt-radio { display:flex; align-items:center; gap:10px; padding:10px 14px; border:1px solid #e5e7eb; border-radius:10px; cursor:pointer; font-size:13px; color:#374151; user-select:none; transition:border-color .15s,background .15s,box-shadow .15s; }
.pmt-radio:hover { border-color:#cbd5e1; }
.pmt-radio.checked { border-color:#2563eb; background:#eff6ff; box-shadow:0 0 0 3px rgba(37,99,235,.10); }
.pmt-radio-dot { width:16px; height:16px; border-radius:50%; border:2px solid #d1d5db; display:inline-block; flex-shrink:0; transition:border-color .15s, background .15s; }
.pmt-radio-dot.on { border-color:#2563eb; background:#2563eb; box-shadow:inset 0 0 0 3px #fff; }
.pmt-radio-title { font-weight:600; color:#0f172a; font-size:13px; line-height:1.2; }
.pmt-radio.checked .pmt-radio-title { color:#1d4ed8; }
.pmt-radio-sub { font-size:11.5px; color:#6b7280; margin-top:2px; }

/* ── View head (coloured bg stays, no gradient override) ── */
.pmt-view-head { position:relative; display:flex; align-items:flex-start; justify-content:space-between; padding:20px; border-bottom:1px solid #e5e7eb; flex-shrink:0; }
.head-green { background:#f0fdf4; }
.head-red   { background:#fff1f2; }
.pmt-view-num-dark { color:#111827 !important; }
.pmt-view-party { font-size:13px; color:#6b7280; margin-top:2px; }
.pmt-view-amount { font-size:22px; font-weight:800; color:#111827; }

/* ── Meta grid ── */
.pmt-meta-grid { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
.pmt-meta-lbl { font-size:11px; color:#9ca3af; text-transform:uppercase; letter-spacing:.05em; margin-bottom:2px;    font-weight: 600; }

/* ── Invoice allocation table ── */
.pmt-section-hdr { display:flex; align-items:center; justify-content:space-between; font-size:12px; font-weight:700; color:#374151; text-transform:uppercase; letter-spacing:.05em; padding-bottom:6px; }
.pmt-unalloc { font-size:12px; font-weight:600; color:#6b7280; }
.pmt-inv-empty { font-size:12.5px; color:#9ca3af; padding:18px 0; text-align:center; background:#f9fafb; border:1px dashed #e5e7eb; border-radius:8px; }
.pmt-inv-table { border:1px solid #e5e7eb; border-radius:8px; overflow:hidden; font-size:12.5px; background:#fff; }
.pmt-inv-head { display:grid; grid-template-columns:24px 1fr 90px 90px 90px; gap:8px; background:#f9fafb; padding:8px 10px; font-size:11px; font-weight:600; color:#6b7280; text-transform:uppercase; letter-spacing:.04em; }
.pmt-inv-row { display:grid; grid-template-columns:24px 1fr 90px 90px 90px; gap:8px; padding:8px 10px; border-top:1px solid #f3f4f6; align-items:center; }
.pmt-inv-name {color:#2563eb; font-weight:600; }
.pmt-alloc-input { width:80px; border:1px solid #e2e8f0; border-radius:6px; padding:4px 8px; font:inherit; font-size:12px; text-align:right; outline:none; }
.pmt-alloc-input:focus { border-color:#2563eb; box-shadow:0 0 0 2px rgba(37,99,235,.10); }

/* ── Row action cell ── */
.pmt-act-cell { cursor:default !important; display:flex; gap:4px; justify-content:flex-end; }

/* ── Color helpers ── */
.green { color:#16a34a !important; }
.red   { color:#dc2626 !important; }
.orange{ color:#ea580c !important; }

/* ── Payment-specific badge colours (not in shared CSS) ── */
.badge-green { background:#dcfce7; color:#16a34a; }
.badge-red   { background:#fee2e2; color:#dc2626; }

/* ══════════════════════════════════════════════
   View Drawer – new clean card design
   ══════════════════════════════════════════════ */
.pmt-vd-body {
  flex: 1;
  overflow-y: auto;
  background: #f1f3f9;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* Hero card: Payment # / party / amount / status */
.pmt-vd-hero-card {
  position: relative;
  background: #fff;
  border-radius: 14px;
  padding: 20px 20px 18px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
}
.pmt-vd-hero-left { flex: 1; min-width: 0; }
.pmt-vd-hero-num {
  font-size: 20px;
  font-weight: 800;
  color: #111827;
  letter-spacing: -.3px;
}
.pmt-vd-hero-party {
  margin-top: 4px;
  font-size: 13.5px;
  color: #2563eb;
  font-weight: 500;
}
.pmt-vd-hero-right {
  text-align: right;
  flex-shrink: 0;
  margin-left: 12px;
}
.pmt-vd-hero-amount {
  font-size: 22px;
  font-weight: 800;
  color: #111827;
  letter-spacing: -.4px;
}
.pmt-vd-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-top: 5px;
  font-size: 11.5px;
  font-weight: 700;
  letter-spacing: .04em;
  border-radius: 20px;
  padding: 3px 10px 3px 8px;
}
.pmt-vd-badge-green { background: #dcfce7; color: #15803d; }
.pmt-vd-badge-red   { background: #fee2e2; color: #dc2626; }
.pmt-vd-badge-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}
.pmt-vd-close {
    position: absolute;
    top: -4px;
    right: 0px;
    width: 28px;
    height: 28px;
    border: none;
    background: #fff1f2;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    color: #dc2626;
    transition: background .15s;
}
.pmt-vd-close:hover { background: #e5e7eb; color: #111827; }

/* Generic info card */
.pmt-vd-card {
  background: #fff;
  border-radius: 14px;
  padding: 18px 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
}
.pmt-vd-card-title {
  font-size: 11px;
  font-weight: 700;
  color: #111827;
  letter-spacing: .07em;
  text-transform: uppercase;
  margin-bottom: 14px;
}

/* 2-column meta grid inside details card */
.pmt-vd-meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px 24px;
}
.pmt-vd-lbl {
  font-size: 10.5px;
  font-weight: 700;
  color: #9ca3af;
  text-transform: uppercase;
  letter-spacing: .06em;
  margin-bottom: 3px;
}
.pmt-vd-val {
  font-size: 14px;
  color: #111827;
  font-weight: 500;
  white-space: pre-wrap;
  word-break: break-word;
}

/* Linked documents table */
.pmt-vd-link-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.pmt-vd-link-table thead tr {
  border-bottom: 1.5px solid #f3f4f6;
}
.pmt-vd-link-table th {
  font-size: 11px;
  font-weight: 700;
  color: #9ca3af;
  letter-spacing: .06em;
  text-transform: uppercase;
  padding: 0 0 10px;
}
.pmt-vd-link-table td {
  padding: 14px 0;
  border-bottom: 1px solid #f3f4f6;
  color: #111827;
  font-weight: 500;
}
.pmt-vd-link-table tbody tr:last-child td { border-bottom: none; }
.pmt-vd-alloc-green { color: #16a34a !important; font-weight: 700; }

/* Remarks */
.pmt-vd-remarks {
    font-size: 13.5px;
    color: #374151;
    border-radius: 8px;
    height: 100px;
    background: #f2f2f2;
    word-wrap: break-word;
    padding: 10px;
    overflow: scroll;
}

/* Footer buttons */
.pmt-vd-btn-close {
  border: 1.5px solid #d1d5db;
  background: #fff;
  color: #374151;
  font-size: 13.5px;
  font-weight: 600;
  padding: 8px 22px;
  border-radius: 8px;
  cursor: pointer;
  transition: background .15s;
}
.pmt-vd-btn-close:hover { background: #f9fafb; }

.pmt-vd-btn-cancel {
  border: none;
  background: #fff1f2;
  color: #dc2626;
  font-size: 13.5px;
  font-weight: 700;
  padding: 8px 22px;
  border-radius: 8px;
  cursor: pointer;
  transition: background .15s;
}
.pmt-vd-btn-cancel:hover { background: #fee2e2; }

/* Toolbar button group */
.pmt-btn-group { display:flex; gap:8px; margin-left:auto; }

/* ── Mobile card view (Option A) ── */
.pay-mobile-cards { display: none; }
.pay-desktop-table { display: table; }

@media (max-width: 768px) {
  .pay-desktop-table { display: none !important; }
  .pay-mobile-cards { display: flex; flex-direction: column; gap: 0; background: #f8fafc; }
  .pay-mobile-card { background: #fff; border-bottom: 1px solid #e5e7eb; padding: 12px 14px; cursor: pointer; transition: background .12s; }
  .pay-mobile-card:active { background: #f8f9fc; }
  .pay-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .pay-mc-docno { font-size: 12px; font-weight: 700; color: #2563eb; }
  .pay-mc-mid { font-size: 13.5px; font-weight: 600; color: #1a1d23; margin-bottom: 4px; }
  .pay-mc-meta { display: flex; justify-content: space-between; font-size: 12px; color: #868e96; margin-bottom: 4px; }
  .pay-mc-amount { font-weight: 700; }
  .pay-mc-green { color: #16a34a; }
  .pay-mc-red { color: #dc2626; }
  .pay-mc-sub { font-size: 11.5px; color: #868e96; margin-bottom: 8px; }
  .pay-mc-footer { display: flex; gap: 6px; margin-top: 8px; }
  .pay-mc-btn { flex: 1; padding: 6px 10px; border-radius: 7px; font-size: 12px; font-weight: 600; cursor: pointer; background: #f1f5f9; border: 1px solid #e2e8f0; color: #374151; }
  .pay-mc-danger { background: #fff1f2; border-color: #fecaca; color: #dc2626; }
  .pay-mc--skeleton { pointer-events: none; }
  .pay-mc-shimmer { border-radius: 6px; background: linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size: 200% 100%; animation: pay-shimmer 1.4s infinite; }
  @keyframes pay-shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
  .pay-mc-empty { text-align: center; padding: 32px 16px; color: #868e96; font-size: 13px; }
}

@media(max-width:475px) {
  .list-page { padding:12px 10px 20px !important; gap:14px !important; }

  /* Toolbar */
  .sales-toolbar { flex-wrap:wrap !important; gap:8px !important; }
  .sales-search { flex:1 1 100% !important; min-width:0 !important; width:100% !important; box-sizing:border-box !important; }
  .sales-pills { flex-wrap:wrap !important; }
  .pmt-btn-group { margin-left:0 !important; flex-wrap:wrap !important; width:100% !important; }
  .pmt-btn-group .sales-btn-primary { flex:1 !important; justify-content:center !important; }

  /* Drawers full-width */
  .pmt-edit-drawer { width:100% !important; right:-100% !important; }
  .pmt-edit-drawer.open { right:0 !important; }
  .pmt-view-drawer { width:100% !important; right:-100% !important; }
  .pmt-view-drawer.open { right:0 !important; }

  /* View drawer internals */
  .pmt-vd-meta-grid { grid-template-columns:1fr !important; gap:14px !important; }
  .pmt-radio-group { grid-template-columns:1fr !important; }
}

/* ── Tablet (≤ 768px) ── */
@media (max-width: 768px) {
  /* Drawers full-screen */
  .pmt-edit-drawer { width: 100% !important; right: -100% !important; max-width: 100%; }
  .pmt-view-drawer { width: 100% !important; right: -100% !important; max-width: 100%; }
  .pmt-edit-drawer.open,
  .pmt-view-drawer.open { right: 0 !important; }

  /* Toolbar */
  .sales-toolbar { flex-wrap: wrap; gap: 8px; }
  .pmt-btn-group { margin-left: 0; flex-wrap: wrap; width: 100%; }
  .pmt-btn-group .sales-btn-primary { flex: 1; justify-content: center; }

  /* KPI / stat grids */
  .bk-kpi-grid  { grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .bk-stat-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }

  /* Table: hide Mode + Reference columns */
  .inv-table th:nth-child(4), .inv-table td:nth-child(4),
  .inv-table th:nth-child(5), .inv-table td:nth-child(5) { display: none; }
}

/* ── Mobile (≤ 480px) ── */
@media (max-width: 480px) {
  .bk-kpi-grid  { grid-template-columns: 1fr; }
  .bk-stat-grid { grid-template-columns: 1fr; }

  /* View drawer internals */
  .pmt-meta-grid    { grid-template-columns: 1fr !important; }
  .pmt-vd-meta-grid { grid-template-columns: 1fr !important; }
  .pmt-radio-group  { grid-template-columns: 1fr !important; }

  /* Linked docs table: scrollable */
  .pmt-inv-table { overflow-x: auto !important; -webkit-overflow-scrolling: touch; }
  .pmt-vd-link-table { min-width: 280px; font-size: 12px !important; }

  /* View head: stack amount below name */
  .pmt-view-head { flex-wrap: wrap; gap: 10px; }
  .pmt-vd-hero-card { flex-wrap: wrap; gap: 10px; }
  .pmt-vd-hero-right { margin-left: 0; text-align: left; }
}
</style>