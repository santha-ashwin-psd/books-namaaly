<template>
  <div class="list-page">
    <div class="sales-toolbar">
      <div class="sales-search">
        <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
        <input v-model="search" placeholder="Search expenses…" class="sales-search-input" />
      </div>
      <div class="sales-pills">
        <button v-for="t in tabs" :key="t.key" class="sales-pill" :class="{active:activeTab===t.key, ['pill-'+t.key]: t.key!=='all'}" @click="activeTab=t.key">{{ t.label }}</button>
      </div>
      <div style="display:flex;gap:8px;margin-left:auto">
        <button class="sales-btn-ghost" @click="load"><span v-html="icon('refresh',14)"></span></button>
        <button class="sales-btn-primary" @click="openNew" :disabled="!$canWrite('bills')" :title="!$canWrite('bills') ? 'Read-only access' : ''"><span v-html="icon('plus',13)"></span> New Expense</button>
      </div>
    </div>

    <!-- ── KPI Cards ── -->
    <div class="bk-kpi-grid bk-kpi-grid-4">
      <div class="bk-kpi-card bk-kpi-accent clickable" @click="activeTab='all'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#dbeafe"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.8"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Total Records</div><div class="bk-kpi-value">{{ list.length }}</div><div class="bk-kpi-trend" :class="expTrends.total.up?'bk-trend-up':'bk-trend-down'">{{ expTrends.total.up?'↑':'↓' }} {{ expTrends.total.pct }}% vs last month</div></div></div></div>
      <div class="bk-kpi-card"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#dcfce7"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="1.8"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">This Month</div><div class="bk-kpi-value bk-kpi-green" style="font-size:18px">{{ fmtCur(monthTotal) }}</div><div class="bk-kpi-trend" :class="expTrends.month.up?'bk-trend-up':'bk-trend-down'">{{ expTrends.month.up?'↑':'↓' }} {{ expTrends.month.pct }}% vs last month</div></div></div></div>
      <div class="bk-kpi-card bk-kpi-info clickable" @click="activeTab='submitted'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#cffafe"><svg width="22" height="22" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="#0891b2" stroke-width="1.8"/><polyline points="7 12.5 10.5 16 17 9" stroke="#0891b2" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Submitted</div><div class="bk-kpi-value bk-kpi-blue">{{ list.filter(e=>e.docstatus===1).length }}</div><div class="bk-kpi-trend" :class="expTrends.submitted.up?'bk-trend-up':'bk-trend-down'">{{ expTrends.submitted.up?'↑':'↓' }} {{ expTrends.submitted.pct }}% vs last month</div></div></div></div>
      <div class="bk-kpi-card bk-kpi-warn clickable" @click="activeTab='draft'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#f1f5f9"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#6b7280" stroke-width="1.8"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Draft</div><div class="bk-kpi-value bk-kpi-amber">{{ counts.draft }}</div><div class="bk-kpi-trend" :class="expTrends.draft.up?'bk-trend-up':'bk-trend-down'">{{ expTrends.draft.up?'↑':'↓' }} {{ expTrends.draft.pct }}% vs last month</div></div></div></div>
    </div>
    <div class="bk-stat-grid">
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">This Month Count</div><div class="bk-stat-value">{{ expThisMonth.count }}</div></div><div class="bk-stat-icon" style="background:#dbeafe;color:#2563eb"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg></div></div></div>
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">Submitted</div><div class="bk-stat-value bk-kpi-green">{{ list.filter(e=>e.docstatus===1).length }}</div></div><div class="bk-stat-icon" style="background:#dcfce7;color:#16a34a"><svg width="18" height="18" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="#16a34a" stroke-width="1.8"/><polyline points="7 12.5 10.5 16 17 9" stroke="#16a34a" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></div></div></div>
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">Avg Expense</div><div class="bk-stat-value" style="font-size:16px">{{ fmtCur(expAvg) }}</div></div><div class="bk-stat-icon" style="background:#e5e7eb;color:#6b7280"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg></div></div></div>
          </div>

    <div class="inv-table-wrap">
      <table class="inv-table exp-desktop-table">
        <thead>
          <tr>
            <th style="width:32px"><input type="checkbox" @change="toggleAll" :checked="allChecked" /></th>
            <th @click="sort('name')" class="sortable">Expense # <span v-html="sortArrow('name')"></span></th>
            <th @click="sort('expense_type')" class="sortable">Category <span v-html="sortArrow('expense_type')"></span></th>
            <th @click="sort('posting_date')" class="sortable">Date <span v-html="sortArrow('posting_date')"></span></th>
            <th>Status</th>
            <th @click="sort('total_claimed_amount')" class="sortable ta-r">Amount <span v-html="sortArrow('total_claimed_amount')"></span></th>
            <th style="width:50px"></th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 8" :key="n"><td colspan="7"><div class="shimmer"></div></td></tr>
          </template>
          <template v-else>
            <tr v-for="e in paged" :key="e.name" class="inv-row" :class="{selected:selected.has(e.name)}">
              <td><input type="checkbox" :checked="selected.has(e.name)" @change="toggle(e.name)" /></td>
              <td @click="openView(e)"><span class="inv-link">{{ e.name }}</span></td>
              <td @click="openView(e)">{{ e.expense_type||'—' }}</td>
              <td @click="openView(e)">{{ fmtDate(e.posting_date) }}</td>
              <td @click="openView(e)"><span class="inv-status-badge" :class="statusClass(e)">{{ statusLabel(e) }}</span></td>
              <td @click="openView(e)" class="ta-r mono-sm">{{ fmtCur(e.total_claimed_amount||e.grand_total) }}</td>
              <td style="display:flex;gap:4px;justify-content:flex-end">
                <button class="inv-act-btn" @click="openView(e)"><span v-html="icon('eye',13)"></span></button>
                <button v-if="e.docstatus===0" class="inv-act-btn" @click="openEdit(e)"><span v-html="icon('edit',13)"></span></button>
              </td>
            </tr>
            <tr v-if="!sorted.length"><td colspan="7" class="exp-empty">No expenses found</td></tr>
          </template>
        </tbody>
      </table>

      <!-- Mobile cards (shown at ≤768px) -->
      <div class="exp-mobile-cards">
        <template v-if="loading">
          <div v-for="n in 5" :key="n" class="exp-mobile-card exp-mc--skeleton">
            <div class="exp-mc-shimmer" style="height:13px;width:55%;margin-bottom:8px"></div>
            <div class="exp-mc-shimmer" style="height:11px;width:40%;margin-bottom:6px"></div>
            <div class="exp-mc-shimmer" style="height:11px;width:65%"></div>
          </div>
        </template>
        <div v-else-if="!sorted.length" class="exp-mc-empty">
          <div style="font-size:32px;margin-bottom:8px">🧾</div>
          <div>No expenses found</div>
        </div>
        <template v-else>
          <div v-for="e in paged" :key="e.name" class="exp-mobile-card" @click="openView(e)">
            <div class="exp-mc-top">
              <span class="exp-mc-docno">{{ e.name }}</span>
              <span class="inv-status-badge" :class="statusClass(e)">{{ statusLabel(e) }}</span>
            </div>
            <div class="exp-mc-mid">{{ e.expense_type || '—' }}</div>
            <div class="exp-mc-meta">
              <span>{{ fmtDate(e.posting_date) }}</span>
              <span class="exp-mc-amount">{{ fmtCur(e.total_claimed_amount || e.grand_total) }}</span>
            </div>
            <div class="exp-mc-footer">
              <button class="exp-mc-btn" @click.stop="openView(e)">View</button>
              <button v-if="e.docstatus===0" class="exp-mc-btn" @click.stop="openEdit(e)">Edit</button>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- ── Pagination ── -->
    <div v-if="!loading && sorted.length" style="padding:12px 4px 4px">
      <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="sorted.length" />
    </div>

    <!-- Drawer -->
    <div v-if="drawerOpen" class="inv-drawer-bg" @click.self="drawerOpen=false"></div>
    <div class="inv-drawer-panel" :class="{open:drawerOpen}">

      <!-- Header -->
      <div class="inv-dh">
        <div class="exp-dh-left">
          <div class="exp-dh-icon"><span v-html="icon('indianrupee',16)"></span></div>
          <div>
            <div class="inv-dh-title">{{ editingName ? 'Edit Expense' : 'New Expense' }}</div>
            <div class="inv-dh-sub">{{ editingName ? editingName : 'Fill in the details below' }}</div>
          </div>
        </div>
        <button class="inv-dclose" @click="drawerOpen=false"><span v-html="icon('x',15)"></span></button>
      </div>

      <div class="inv-dbody" style="padding:16px;background:#f8fafc;display:flex;flex-direction:column;gap:10px;">

        <!-- Card: Basic Details -->
        <div class="add-card">
          <div class="add-card-header" @click="expCollapsed.basic=!expCollapsed.basic">
            <div class="add-card-title">
              <span class="add-card-title-icon"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></span>
              Basic Details
            </div>
            <span class="add-card-chevron" :class="{collapsed:expCollapsed.basic}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
          </div>
          <div class="add-card-body" :class="{collapsed:expCollapsed.basic}">
            <div class="inv-fg inv-fg2">
              <div>
                <label class="inv-lbl">Expense Date <span class="inv-req">*</span></label>
                <input v-model="form.posting_date" type="date" class="inv-fi" />
              </div>
              <div>
                <label class="inv-lbl">Category <span class="inv-req">*</span></label>
                <select v-model="form.expense_type" class="inv-fi">
                  <option value="">— Select —</option>
                  <option v-for="c in expenseCategories" :key="c" :value="c">{{ c }}</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        <!-- Card: Payment Details -->
        <div class="add-card">
          <div class="add-card-header" @click="expCollapsed.payment=!expCollapsed.payment">
            <div class="add-card-title">
              <span class="add-card-title-icon"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg></span>
              Payment Details
            </div>
            <span class="add-card-chevron" :class="{collapsed:expCollapsed.payment}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
          </div>
          <div class="add-card-body" :class="{collapsed:expCollapsed.payment}">
            <div class="inv-fg inv-fg2">
              <div>
                <label class="inv-lbl">Amount <span class="inv-req">*</span></label>
                <div class="exp-amount-wrap">
                  <span class="exp-amount-prefix">₹</span>
                  <input v-model.number="form.total_claimed_amount" type="number" min="0" max="999999999.99" step="0.01" class="inv-fi exp-amount-input" placeholder="0.00" />
                </div>
                <div v-if="form.total_claimed_amount > 999999999.99" class="exp-field-hint exp-field-hint-err">Amount cannot exceed ₹99,99,99,999.99</div>
              </div>
              <div>
                <label class="inv-lbl">Expense Account <span class="inv-req">*</span></label>
                <SearchableSelect v-model="form.expense_account" :options="expenseAccountOptions"
                  placeholder="Search expense account…"
                  @search="fetchExpenseAccounts" @open="fetchExpenseAccounts('')" />
              </div>
              <div style="grid-column:1/-1">
                <label class="inv-lbl">Paid Through <span class="inv-req">*</span></label>
                <SearchableSelect v-model="form.paid_through" :options="paidThroughOptions"
                  placeholder="Search bank / cash account…"
                  @search="fetchPaidThroughAccounts" @open="fetchPaidThroughAccounts('')" />
              </div>
              <div style="grid-column:1/-1">
                <label class="inv-lbl">Cost Center</label>
                <select v-model="form.cost_center" class="inv-fi">
                  <option value="">— Select —</option>
                  <option v-for="cc in costCenters" :key="cc" :value="cc">{{ cc }}</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        <!-- Card: Notes & Receipt -->
        <div class="add-card">
          <div class="add-card-header" @click="expCollapsed.notes=!expCollapsed.notes">
            <div class="add-card-title">
              <span class="add-card-title-icon"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></span>
              Notes &amp; Receipt
            </div>
            <span class="add-card-chevron" :class="{collapsed:expCollapsed.notes}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
          </div>
          <div class="add-card-body" :class="{collapsed:expCollapsed.notes}">
            <div style="margin-bottom:12px">
              <label class="inv-lbl">Description <span class="inv-req">*</span></label>
              <textarea v-model="form.remark" rows="3" maxlength="500" class="inv-fi exp-textarea" placeholder="What was this expense for?"></textarea>
              <div class="exp-field-hint" :class="{'exp-field-hint-err': form.remark.length >= 500}">{{ form.remark.length }}/500 characters</div>
            </div>
            <div>
              <label class="inv-lbl">Attach Receipt</label>
              <div v-if="receiptFile" class="exp-receipt-attached">
                <div class="exp-receipt-attached-icon"><span v-html="icon('check',13)"></span></div>
                <span class="exp-receipt-filename">{{receiptFile.name}}</span>
                <button @click="receiptFile=null" class="exp-receipt-remove" v-html="icon('x',12)"></button>
              </div>
              <label v-else class="exp-receipt-drop">
                <div class="exp-receipt-drop-icon"><span v-html="icon('fileplus',16)"></span></div>
                <div>
                  <div class="exp-receipt-drop-text">Click to attach receipt</div>
                  <div class="exp-receipt-drop-hint">Supports image or PDF</div>
                </div>
                <input type="file" accept="image/*,.pdf" style="display:none" @change="onReceiptChange"/>
              </label>
            </div>
          </div>
        </div>

      </div>

      <!-- Footer -->
      <div class="inv-dfooter">
        <button class="form-btn form-btn-outline" @click="drawerOpen=false">Cancel</button>
        <div style="display:flex;gap:8px">
          <button class="add-btn-draft" :disabled="drawerSaving" @click="saveExpense(0)">
            <span v-html="icon('save',13)"></span> {{ drawerSaving ? 'Saving…' : 'Save Draft' }}
          </button>
          <button class="add-btn-more" :disabled="drawerSaving" @click="saveExpense(1)">
            <span v-html="icon('check',13)"></span> {{ drawerSaving ? 'Saving…' : 'Submit' }}
          </button>
        </div>
      </div>
    </div>

    <!-- View Drawer -->
    <div v-if="viewOpen" class="inv-drawer-bg" @click.self="viewOpen=false"></div>
    <div class="inv-drawer-panel exp-view-drawer" :class="{open:viewOpen}">
      <template v-if="viewDoc">

        <!-- View Header -->
        <div class="exp-view-head">
          <div class="exp-view-head-left">
            <div class="exp-view-head-icon"><span v-html="icon('indianrupee',18)"></span></div>
            <div>
              <div class="exp-view-num">{{ viewDoc.name }}</div>
              <div class="exp-view-sub">{{ viewDoc.expense_type||'Expense' }}</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px">
            <span class="inv-status-badge exp-badge-lg" :class="statusClass(viewDoc)">{{ statusLabel(viewDoc) }}</span>
            <button class="inv-dclose" @click="viewOpen=false"><span v-html="icon('x',15)"></span></button>
          </div>
        </div>

        <!-- Amount hero strip -->
        <div class="exp-view-amount-strip">
          <div class="exp-view-amount-val">{{ fmtCur(viewDoc.total_claimed_amount||viewDoc.grand_total) }}</div>
          <div class="exp-view-amount-lbl">Total Amount</div>
        </div>

        <!-- View Body -->
        <div class="exp-vbody">

          <div class="ew-section">
            <div class="ew-section-hdr"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg><span>Expense Details</span></div>
            <div class="ew-kv-list">
              <div class="ew-kv-row">
                <span class="ew-kv-lbl">Date</span>
                <span class="ew-kv-val mono-sm">{{ fmtDate(viewDoc.posting_date) }}</span>
              </div>
              <div class="ew-kv-row">
                <span class="ew-kv-lbl">Category</span>
                <span class="ew-kv-val">{{ viewDoc.expense_type||'—' }}</span>
              </div>
            </div>
          </div>

          <div class="ew-section">
            <div class="ew-section-hdr"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg><span>Payment</span></div>
            <div class="ew-kv-list">
              <div class="ew-kv-row">
                <span class="ew-kv-lbl">Expense Account</span>
                <span class="ew-kv-val mono-sm">{{ viewDoc.expense_account||'—' }}</span>
              </div>
              <div class="ew-kv-row">
                <span class="ew-kv-lbl">Paid Through</span>
                <span class="ew-kv-val mono-sm">{{ viewDoc.paid_through||'—' }}</span>
              </div>
              <div v-if="viewDoc.cost_center" class="ew-kv-row">
                <span class="ew-kv-lbl">Cost Center</span>
                <span class="ew-kv-val">{{ viewDoc.cost_center }}</span>
              </div>
            </div>
          </div>

          <div v-if="viewDoc.remark||viewDoc.notes||viewDoc.description" class="ew-section">
            <div class="ew-section-hdr"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg><span>Notes</span></div>
            <p style="font-size:13px;color:#374151;line-height:1.6;margin:0;word-break:break-word;overflow-wrap:anywhere;white-space:pre-wrap">{{ viewDoc.remark||viewDoc.notes||viewDoc.description }}</p>
          </div>

          <div v-if="viewDoc.attach" class="ew-section">
            <div class="ew-section-hdr"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg><span>Receipt</span></div>
            <a :href="viewDoc.attach" target="_blank" class="exp-vattach-link">
              <div class="exp-vattach-icon"><span v-html="icon('paperclip',13)"></span></div>
              <span class="exp-vattach-name">{{ viewDoc.attach.split('/').pop() }}</span>
              <span v-html="icon('externallink',11)" style="flex-shrink:0;color:#93c5fd;margin-left:auto"></span>
            </a>
          </div>

        </div>

        <!-- View Footer -->
        <div class="inv-dfooter">
          <button class="form-btn form-btn-outline" @click="viewOpen=false">Close</button>
          <button v-if="viewDoc.docstatus===0" class="form-btn form-btn-primary" @click="openEdit(viewDoc);viewOpen=false">
            <span v-html="icon('edit',13)"></span> Edit
          </button>
          <button v-if="viewDoc.docstatus===1" class="form-btn form-btn-outline" :disabled="cancelling" @click="cancelExpense(viewDoc)">
            <span v-html="icon('x',13)"></span> {{ cancelling ? 'Cancelling…' : 'Cancel Expense' }}
          </button>
        </div>

      </template>
    </div>
  </div>

  <!-- Quick-Create popup (shared: triggered by SearchableSelect createable) -->
  <QuickCreateDrawer />
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { apiList, apiGet, apiGET, apiSave, apiSubmit, apiCancel, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { useConfirm } from "../composables/useConfirm.js";
import { icon } from "../utils/icons.js";
import { flt, fmtDate } from "../utils/format.js";
import SearchableSelect from "../components/SearchableSelect.vue";
import QuickCreateDrawer from "../components/QuickCreateDrawer.vue";
import Pagination from "../components/Pagination.vue";
import { usePagination } from "../composables/usePagination.js";

const { toast } = useToast();
const { confirm } = useConfirm();
const activeTab=ref("all");
const tabs=[{key:"all",label:"All"},{key:"draft",label:"Draft"},{key:"submitted",label:"Submitted"}];
const expenseCategories=["Travel","Food & Meals","Accommodation","Office Supplies","Utilities","Marketing","Software","Hardware","Training","Miscellaneous"];

const list=ref([]),loading=ref(false),search=ref(""),selected=ref(new Set());
const drawerOpen=ref(false),drawerSaving=ref(false),editingName=ref("");
const expCollapsed=reactive({basic:false,payment:false,notes:true});
const viewOpen=ref(false),viewDoc=ref(null);
const cancelling=ref(false);
const receiptFile=ref(null);
function onReceiptChange(e){const f=e.target.files[0];if(f)receiptFile.value=f;e.target.value="";}
const sortCol=ref("posting_date"),sortDir=ref("desc");
let _id=1;
const expenseAccountOptions  = ref([]);
const paidThroughOptions     = ref([]);

async function fetchExpenseAccounts(q = "") {
  try {
    const company = await resolveCompany();
    const filters = [["is_group","=",0],["disabled","=",0],["company","=",company],["account_type","=","Expense"]];
    if (q) filters.push(["name","like",`%${q}%`]);
    const rows = await apiList("Account", { fields:["name"], filters, limit:30, order:"name asc" });
    expenseAccountOptions.value = rows.map(r => ({ label: r.name, value: r.name }));
  } catch { expenseAccountOptions.value = []; }
}
async function fetchPaidThroughAccounts(q = "") {
  try {
    const company = await resolveCompany();
    const filters = [["is_group","=",0],["disabled","=",0],["company","=",company],["account_type","in",["Bank","Cash"]]];
    if (q) filters.push(["name","like",`%${q}%`]);
    const rows = await apiList("Account", { fields:["name","account_type"], filters, limit:30, order:"name asc" });
    paidThroughOptions.value = rows.map(r => ({ label: r.name, value: r.name }));
  } catch { paidThroughOptions.value = []; }
}
const form=reactive({posting_date:new Date().toISOString().slice(0,10),expense_type:"",total_claimed_amount:0,currency:"INR",remark:"",expense_account:"",paid_through:"",cost_center:""});
const costCenters=ref([]);
async function fetchCostCenters(){try{const co=await resolveCompany();const r=await apiGET("frappe.client.get_list",{doctype:"Cost Center",fields:JSON.stringify(["name"]),filters:JSON.stringify([["disabled","=",0],["company","=",co],["is_group","=",0]]),order_by:"name asc",limit_page_length:100})||[];costCenters.value=r.map(c=>c.name);}catch{costCenters.value=[];}}

async function load(){
  loading.value=true;
  try{
    const co=await resolveCompany();
    const raw=await apiList("Expense",{
      fields:["name","posting_date","expense_type","description","amount","tax_amount",
              "total_amount","status","docstatus","expense_account","paid_through","attach","notes"],
      filters:[["company","=",co]],
      limit:200,
      order: "posting_date desc, creation desc",
    });
    // Map to legacy shape so the rest of the template doesn't need to change.
    list.value=raw.map(e=>({
      ...e,
      total_claimed_amount: e.total_amount||e.amount||0,
    }));
  }catch(e){toast.error(e.message||"Failed to load expenses");}
  finally{loading.value=false;}
}

function statusLabel(e){if(e.docstatus===2)return"Cancelled";if(e.docstatus===0)return"Draft";return"Submitted";}
function statusClass(e){if(e.docstatus===2)return"badge-grey";if(e.docstatus===0)return"badge-orange";return"badge-blue";}
const now=new Date();
const monthStart=new Date(now.getFullYear(),now.getMonth(),1).toISOString().slice(0,10);
const monthTotal=computed(()=>list.value.filter(e=>e.posting_date>=monthStart).reduce((s,e)=>s+flt(e.total_claimed_amount||e.grand_total),0));
const unpaidTotal=computed(()=>list.value.filter(e=>e.docstatus===1).reduce((s,e)=>s+flt(e.total_claimed_amount||e.grand_total),0));
const counts=computed(()=>({draft:list.value.filter(e=>e.docstatus===0).length}));
const _exYM  = () => { const d=new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; };
const _exLYM = () => { const d=new Date(); d.setMonth(d.getMonth()-1); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; };
const _exTr  = (a,b) => { if(!b&&!a) return {pct:0,up:true}; if(!b) return {pct:100,up:true}; const p=Math.round((a-b)/b*100); return {pct:Math.abs(p),up:p>=0}; };
const expThisMonth = computed(()=>{ const ym=_exYM(); const r=list.value.filter(e=>(e.posting_date||'').startsWith(ym)); return {count:r.length,total:r.reduce((s,e)=>s+flt(e.total_claimed_amount||e.grand_total),0)}; });
const expAvg = computed(()=>{ const p=list.value.filter(e=>(e.total_claimed_amount||e.grand_total)>0); return p.length?p.reduce((s,e)=>s+flt(e.total_claimed_amount||e.grand_total),0)/p.length:0; });
const expTrends = computed(()=>({
  total:     _exTr(expThisMonth.value.count, list.value.filter(e=>(e.posting_date||'').startsWith(_exLYM())).length),
  month:     _exTr(expThisMonth.value.total, list.value.filter(e=>(e.posting_date||'').startsWith(_exLYM())).reduce((s,e)=>s+flt(e.total_claimed_amount||e.grand_total),0)),
  submitted: _exTr(list.value.filter(e=>e.docstatus===1).length, list.value.filter(e=>(e.posting_date||'').startsWith(_exLYM())&&e.docstatus===1).length),
  draft:     _exTr(list.value.filter(e=>e.docstatus===0).length, list.value.filter(e=>(e.posting_date||'').startsWith(_exLYM())&&e.docstatus===0).length),
}));
function fmtCur(v){return new Intl.NumberFormat("en-IN",{style:"currency",currency:"INR",minimumFractionDigits:2}).format(flt(v));}
const filtered=computed(()=>{let r=list.value;if(activeTab.value==="draft")r=r.filter(e=>e.docstatus===0);if(activeTab.value==="submitted")r=r.filter(e=>e.docstatus===1);if(search.value.trim()){const q=search.value.toLowerCase();r=r.filter(x=>(x.name||"").toLowerCase().includes(q)||(x.expense_type||"").toLowerCase().includes(q));}return r;});
const sorted=computed(()=>{const col=sortCol.value;return[...filtered.value].sort((a,b)=>{const av=a[col]??"",bv=b[col]??"";const c=typeof av==="number"?av-bv:String(av).localeCompare(String(bv));return sortDir.value==="asc"?c:-c;});});
const { page, pageSize, paged } = usePagination(sorted, { storageKey: "expenses" });
function sort(col){if(sortCol.value===col)sortDir.value=sortDir.value==="asc"?"desc":"asc";else{sortCol.value=col;sortDir.value="asc";}}
function sortArrow(col){if(sortCol.value!==col)return'<span style="color:#d1d5db">⇅</span>';return sortDir.value==="asc"?"↑":"↓";}
const allChecked=computed(()=>sorted.value.length>0&&sorted.value.every(e=>selected.value.has(e.name)));
function toggle(n){const s=new Set(selected.value);s.has(n)?s.delete(n):s.add(n);selected.value=s;}
function toggleAll(e){selected.value=e.target.checked?new Set(sorted.value.map(x=>x.name)):new Set();}
function openNew(){editingName.value="";receiptFile.value=null;Object.assign(form,{posting_date:new Date().toISOString().slice(0,10),expense_type:"",total_claimed_amount:0,currency:"INR",remark:"",expense_account:"",paid_through:"",cost_center:""});Object.assign(expCollapsed,{basic:false,payment:false,notes:true});drawerOpen.value=true;}
async function openEdit(e){
  editingName.value=e.name;
  receiptFile.value=null;
  // Reset to blanks first so a failed/partial fetch below can never leave
  // stale account/cost-center values from a previously edited expense.
  Object.assign(form,{posting_date:"",expense_type:"",total_claimed_amount:0,currency:"INR",remark:"",expense_account:"",paid_through:"",cost_center:""});
  try{
    const doc=await apiGet("Expense",e.name);
    Object.assign(form,{
      posting_date: doc.posting_date||"",
      expense_account: doc.expense_account||"",
      paid_through:    doc.paid_through||"",
      cost_center:     doc.cost_center||"",
      expense_type: doc.expense_type||"",
      // Prefer the base `amount` (what this field maps to on save) over the
      // tax-inclusive `total_amount` — loading the inclusive total here would
      // re-apply gst_rate on top of it on every subsequent edit.
      total_claimed_amount: flt(doc.amount ?? doc.total_amount),
      currency: "INR",
      remark: doc.description||doc.notes||"",
    });
    // Expense is FLAT (one row = one expense), so seed a single line for editing
  }catch{
    // Full doc fetch failed — fall back to what the list row gave us, but
    // never silently carry over account fields the list doesn't include;
    // tell the user so they can re-check before saving.
    Object.assign(form,{
      posting_date:e.posting_date||"",
      expense_type:e.expense_type||"",
      total_claimed_amount:flt(e.amount ?? e.total_amount ?? e.total_claimed_amount),
      currency:"INR",
      remark:e.description||"",
      expense_account:"",
      paid_through:"",
      cost_center:"",
    });
    toast.warning("Couldn't load full expense details — please re-select Expense Account and Paid Through before saving.");
  }
  drawerOpen.value=true;
}
async function openView(e) {
  viewDoc.value = e;
  viewOpen.value = true;
  // Fetch full doc to get expense_account, paid_through, attach, notes
  try {
    const full = await apiGet("Expense", e.name);
    if (full) viewDoc.value = { ...e, ...full };
  } catch {}
}

async function saveExpense(submit){
  if(!flt(form.total_claimed_amount)) return toast.error("Enter an amount");
  if(flt(form.total_claimed_amount) > 999999999.99) return toast.error("Amount cannot exceed ₹99,99,99,999.99");
  if(!form.expense_type)              return toast.error("Category is required");
  if(!form.expense_account)           return toast.error("Expense Account is required");
  if(!form.paid_through)              return toast.error("Paid Through is required");
  if(!form.remark)                    return toast.error("Description is required");
  if(form.remark.length > 500)        return toast.error("Description cannot exceed 500 characters");
  drawerSaving.value=true;
  try{
    const company=await resolveCompany();
    const amt=flt(form.total_claimed_amount);
    const doc={
      doctype:"Expense",
      company,
      posting_date:form.posting_date||new Date().toISOString().slice(0,10),
      expense_type:form.expense_type,
      description:form.remark,
      amount:amt,
      tax_amount:0,
      total_amount:amt,
      expense_account: form.expense_account,
      paid_through:    form.paid_through,
      cost_center:     form.cost_center||"",
      notes:form.remark||"",
    };
    if(editingName.value) doc.name=editingName.value;
    const saved=await apiSave(doc);
    // Upload attachment to Frappe and save the file URL in the `attach` field
    if(receiptFile.value && saved?.name){
      try{
        const url = await uploadAttachment(receiptFile.value, "Expense", saved.name);
        if(url){
          await apiSave({ doctype:"Expense", name:saved.name, attach: url });
        }
      }catch(uploadErr){
        // Non-fatal — expense saved, just warn about the attachment
        toast.warning("Expense saved but attachment upload failed: " + (uploadErr.message||""));
      }
    }
    if(submit && saved?.name) await apiSubmit("Expense",saved.name);
    toast.success(`Expense ${saved?.name} ${submit?"submitted":"saved"}`);
    drawerOpen.value=false;
    await load();
  }catch(e){toast.error(e.message||"Failed to save expense");}
  finally{drawerSaving.value=false;}
}

async function cancelExpense(doc){
  const ok = await confirm({
    title: "Cancel Expense",
    body: `Cancel ${doc.name}? This will reverse its GL entries. This cannot be undone.`,
    okLabel: "Cancel Expense",
    cancelLabel: "Go back",
    okStyle: "danger",
  });
  if(!ok) return;
  cancelling.value=true;
  try{
    await apiCancel("Expense", doc.name);
    toast.success(`${doc.name} cancelled`);
    viewOpen.value=false;
    await load();
  }catch(e){toast.error(e.message||"Failed to cancel expense");}
  finally{cancelling.value=false;}
}

async function uploadAttachment(file, doctype, docname) {
  const fd = new FormData();
  fd.append("file", file, file.name);
  fd.append("doctype", doctype);
  fd.append("docname", docname);
  fd.append("fieldname", "attach");
  fd.append("is_private", "0");
  const res = await fetch("/api/method/upload_file", {
    method: "POST",
    headers: { "X-Frappe-CSRF-Token": window.csrf_token || frappe?.csrf_token || "" },
    body: fd,
  });
  if(!res.ok) throw new Error(`Upload failed: ${res.status}`);
  const data = await res.json();
  return data?.message?.file_url || data?.file_url || null;
}
onMounted(() => { load(); fetchExpenseAccounts(""); fetchPaidThroughAccounts(""); fetchCostCenters(); });
</script>

<style scoped>
/* ── Drawer ── */
.inv-drawer-panel { position:fixed;top:0;right:-540px;bottom:0;width:540px;background:#fff;box-shadow:-12px 0 40px rgba(0,0,0,.12);z-index:8000;display:flex;flex-direction:column;transition:right .24s cubic-bezier(.4,0,.2,1); }
.inv-drawer-panel.open { right:0; }
.exp-view-drawer { width:460px;right:-460px; }
.exp-view-drawer.open { right:0; }

/* ── Add/Edit drawer header ── */
.exp-dh-left { display:flex;align-items:center;gap:12px; }
.exp-dh-icon { width:36px;height:36px;border-radius:10px;background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.25);display:flex;align-items:center;justify-content:center;color:#fff;flex-shrink:0; }

/* ── Collapsible cards (reuse add-card pattern) ── */
.add-card { background:#fff;border:1px solid #e3e8ef;border-radius:10px; }
.add-card-header { display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid #e8ecf0;cursor:pointer;user-select:none; }
.add-card-title { display:flex;align-items:center;gap:8px;font-size:13px;font-weight:700;color:#1a1a2e;letter-spacing:.01em; }
.add-card-title-icon { width:20px;height:20px;display:flex;align-items:center;justify-content:center;color:#1565c0;flex-shrink:0; }
.add-card-chevron { color:#9ca3af;transition:transform .2s;display:inline-flex; }
.add-card-chevron.collapsed { transform:rotate(-90deg); }
.add-card-body { padding:16px 18px; }
.add-card-body.collapsed { display:none; }

/* ── View drawer header ── */
.exp-view-head { display:flex;align-items:center;justify-content:space-between;padding:16px 20px;background:linear-gradient(135deg,#1e3a5f,#1a6ef7);flex-shrink:0;gap:12px; }
.exp-view-head-left { display:flex;align-items:center;gap:12px;min-width:0; }
.exp-view-head-icon { width:38px;height:38px;border-radius:10px;background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.25);display:flex;align-items:center;justify-content:center;color:#fff;flex-shrink:0; }
.exp-view-num { font-size:15px;font-weight:700;color:#fff;letter-spacing:-.01em; }
.exp-view-sub { font-size:12px;color:rgba(255,255,255,.75);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
.exp-badge-lg { padding:4px 12px!important;font-size:12.5px!important; }

/* ── Amount hero strip ── */
.exp-view-amount-strip { display:flex;flex-direction:column;align-items:center;padding:14px 20px;background:#f0f7ff;border-bottom:1px solid #dbeafe;flex-shrink:0; }
.exp-view-amount-val { font-size:22px;font-weight:800;color:#0f172a;letter-spacing:-.02em; }
.exp-view-amount-lbl { font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:.06em;margin-top:2px; }

/* ── View body uses ew-section / ew-kv-* pattern ── */
.exp-vbody { flex:1;overflow-y:auto;background:#f8fafc;display:flex;flex-direction:column;gap:10px;padding:12px; }
.ew-section { background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:12px;box-shadow:0 1px 2px rgba(15,23,42,.03); }
.ew-section-hdr { display:flex;align-items:center;gap:8px;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:#0f172a; }
.ew-section-hdr svg { color:#2563eb; }
.ew-kv-list { display:flex;flex-direction:column; }
.ew-kv-row { display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid #f0f2f5;gap:12px; }
.ew-kv-row:last-child { border-bottom:none; }
.ew-kv-lbl { font-size:12px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap;flex-shrink:0; }
.ew-kv-val { font-size:13px;color:#374151;text-align:right; }

/* ── Amount field with prefix ── */
.exp-amount-wrap { position:relative;display:flex;align-items:center; }
.exp-amount-prefix { position:absolute;left:11px;font-size:13px;font-weight:600;color:#6b7280;pointer-events:none; }
.exp-amount-input { padding-left:24px!important;font-weight:600;font-size:14px!important; }

/* ── Receipt Upload ── */
.exp-receipt-drop { display:flex;align-items:center;gap:12px;padding:14px 16px;border:2px dashed #bfdbfe;border-radius:10px;cursor:pointer;background:#f0f7ff;transition:border-color .15s,background .15s; }
.exp-receipt-drop:hover { border-color:#2563eb;background:#eff6ff; }
.exp-receipt-drop-icon { width:36px;height:36px;border-radius:8px;background:#dbeafe;display:flex;align-items:center;justify-content:center;color:#2563eb;flex-shrink:0; }
.exp-receipt-drop-text { font-size:13px;font-weight:600;color:#1d4ed8; }
.exp-receipt-drop-hint { font-size:11.5px;color:#93c5fd;margin-top:1px; }
.exp-receipt-attached { display:flex;align-items:center;gap:10px;padding:10px 14px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;font-size:12.5px; }
.exp-receipt-attached-icon { width:28px;height:28px;border-radius:50%;background:#dcfce7;display:flex;align-items:center;justify-content:center;color:#16a34a;flex-shrink:0; }
.exp-receipt-filename { flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#15803d;font-weight:500; }
.exp-receipt-remove { background:none;border:none;cursor:pointer;color:#dc2626;padding:2px;display:flex;align-items:center;border-radius:4px; }
.exp-receipt-remove:hover { background:#fef2f2; }

/* ── Receipt link in view ── */
.exp-vattach-link { display:inline-f  lex;align-items:center;gap:10px;margin-top:4px;padding:10px 14px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;text-decoration:none;max-width:100%;transition:background .15s; }
.exp-vattach-link:hover { background:#dbeafe; }
.exp-vattach-icon { width:30px;height:30px;border-radius:8px;background:#dbeafe;display:flex;align-items:center;justify-content:center;color:#2563eb;flex-shrink:0; }
.exp-vattach-name { font-size:12.5px;font-weight:600;color:#1d4ed8;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1; }

.exp-field-hint { font-size:11.5px;color:#9ca3af;margin-top:4px;text-align:right; }
.exp-field-hint-err { color:#dc2626;font-weight:600; }

/* ── Misc ── */
.exp-empty { text-align:center;color:#9ca3af;padding:48px!important;cursor:default!important; }
.exp-textarea { resize:vertical;min-height:80px;line-height:1.5; }
.inv-req { color:#dc2626; }
.ta-r { text-align:right!important; }
.text-muted { color:#6b7280; }
.mono-sm { font-size:13px; }
.badge-blue { background-color:#e0f2fe;color:#0369a1; }
.badge-green { background-color:#d1fae5;color:#065f46; }
.badge-orange { background-color:#fff7ed;color:#c2410c; }
.badge-grey { background-color:#f3f4f6;color:#374151; }

/* ── Mobile card view (Option A) ── */
.exp-mobile-cards { display: none; }
.exp-desktop-table { display: table; }

@media (max-width: 768px) {
  .exp-desktop-table { display: none !important; }
  .exp-mobile-cards { display: flex; flex-direction: column; gap: 0; background: #f8fafc; }
  .exp-mobile-card { background: #fff; border-bottom: 1px solid #e5e7eb; padding: 12px 14px; cursor: pointer; transition: background .12s; }
  .exp-mobile-card:active { background: #f8f9fc; }
  .exp-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .exp-mc-docno { font-size: 12px; font-weight: 700; color: #2563eb; }
  .exp-mc-mid { font-size: 13.5px; font-weight: 600; color: #1a1d23; margin-bottom: 4px; }
  .exp-mc-meta { display: flex; justify-content: space-between; font-size: 12px; color: #868e96; margin-bottom: 4px; }
  .exp-mc-amount { font-weight: 700; color: #1a1d23; }
  .exp-mc-sub { font-size: 11.5px; color: #868e96; margin-bottom: 8px; }
  .exp-mc-footer { display: flex; gap: 6px; margin-top: 8px; }
  .exp-mc-btn { flex: 1; padding: 6px 10px; border-radius: 7px; font-size: 12px; font-weight: 600; cursor: pointer; background: #f1f5f9; border: 1px solid #e2e8f0; color: #374151; }
  .exp-mc--skeleton { pointer-events: none; }
  .exp-mc-shimmer { border-radius: 6px; background: linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size: 200% 100%; animation: exp-shimmer 1.4s infinite; }
  @keyframes exp-shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
  .exp-mc-empty { text-align: center; padding: 32px 16px; color: #868e96; font-size: 13px; }
}
</style>