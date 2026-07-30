<template>
  <div class="list-page">
    <!-- ============================================================ TOOLBAR -->
    <div class="sales-toolbar">
      <div class="sales-search">
        <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
        <input v-model="search" placeholder="Search subscriptions, reference, party…" class="sales-search-input" />
      </div>
      <div class="sales-pills">
        <button v-for="t in tabs" :key="t.key" class="sales-pill" :class="{active:activeTab===t.key, ['pill-'+t.key]: t.key!=='all'}" @click="activeTab=t.key">
          {{ t.label }}<span v-if="t.count!=null" class="sales-pill-count">{{ t.count }}</span>
        </button>
      </div>
      <div style="display:flex;gap:8px;">
        <button class="sales-btn-ghost" @click="exportCSV" :disabled="!sorted.length" title="Export to CSV">
          <span v-html="icon('download',14)"></span> CSV
        </button>
        <button class="sales-btn-ghost" @click="load" :disabled="loading">
          <span v-html="icon('refresh',14)"></span>
        </button>
        <button class="sales-btn-primary" :disabled="!$canCreate('invoices')" :title="!$canCreate('invoices') ? 'Read-only access' : ''" @click="openNew">
          <span v-html="icon('plus',13)"></span> New Subscription
        </button>
      </div>
    </div>

    <!-- ── KPI Cards ── -->
    <div class="bk-kpi-grid bk-kpi-grid-4">
      <div class="bk-kpi-card"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#dbeafe"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.8"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Total Schedules</div><div class="bk-kpi-value">{{ stats.total }}</div><div class="bk-kpi-trend bk-trend-neutral">all recurring</div></div></div></div>
      <div class="bk-kpi-card bk-kpi-success clickable" @click="activeTab='Active'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#dcfce7"><svg width="22" height="22" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="#16a34a" stroke-width="1.8"/><polyline points="7 12.5 10.5 16 17 9" stroke="#16a34a" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Active</div><div class="bk-kpi-value bk-kpi-green">{{ stats.active }}</div><div class="bk-kpi-trend bk-trend-neutral">running</div></div></div></div>
      <div class="bk-kpi-card bk-kpi-warn clickable" @click="activeTab='Paused'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#fef3c7"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><line x1="10" y1="15" x2="10" y2="9"/><line x1="14" y1="15" x2="14" y2="9"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Paused</div><div class="bk-kpi-value bk-kpi-amber">{{ stats.paused }}</div><div class="bk-kpi-trend bk-trend-neutral">on hold</div></div></div></div>
      <div class="bk-kpi-card"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#dbeafe"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Due Today</div><div class="bk-kpi-value bk-kpi-blue">{{ stats.due_today }}</div><div class="bk-kpi-trend bk-trend-neutral">to generate</div></div></div></div>
    </div>
    <div class="bk-stat-grid">
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">Completed</div><div class="bk-stat-value">{{ stats.completed }}</div></div><div class="bk-stat-icon" style="background:#dcfce7;color:#16a34a"><svg width="18" height="18" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="#16a34a" stroke-width="1.8"/><polyline points="7 12.5 10.5 16 17 9" stroke="#16a34a" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></div></div></div>
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">Overdue</div><div class="bk-stat-value bk-kpi-red">{{ stats.overdue }}</div></div><div class="bk-stat-icon" style="background:#fee2e2;color:#dc2626"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></div></div></div>
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">Active Rate</div><div class="bk-stat-value bk-kpi-green">{{ stats.total ? Math.round(stats.active/stats.total*100) : 0 }}%</div></div><div class="bk-stat-icon" style="background:#dcfce7;color:#16a34a"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/></svg></div></div></div>
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">Cancelled</div><div class="bk-stat-value">{{ stats.total - stats.active - stats.paused - stats.completed }}</div></div><div class="bk-stat-icon" style="background:#e5e7eb;color:#6b7280"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg></div></div></div>
    </div>

    <!-- ============================================================ BULK BAR -->
    <div v-if="selected.length" class="inv-bulk-bar">
      <span class="inv-bulk-count">{{ selected.length }} selected</span>
      <button class="inv-bulk-btn" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="bulkDo('pause')">Pause</button>
      <button class="inv-bulk-btn" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="bulkDo('resume')">Resume</button>
      <button class="inv-bulk-btn inv-bulk-danger" :disabled="!$canDelete('invoices')" :title="!$canDelete('invoices') ? 'Not permitted' : ''" @click="bulkDo('cancel')">Cancel</button>
      <button class="inv-bulk-btn inv-bulk-danger" :disabled="!$canDelete('invoices')" :title="!$canDelete('invoices') ? 'Not permitted' : ''" @click="bulkDo('delete')">Delete</button>
      <button class="inv-bulk-btn" @click="exportCSV"><span v-html="icon('download',13)"></span> Export CSV</button>
      <button class="inv-bulk-clear" @click="selected=[]">✕ Clear</button>
    </div>

    <!-- ============================================================ TABLE -->
    <div class="inv-table-wrap">
      <table class="inv-table">
        <thead>
          <tr>
            <th style="width:32px"><input type="checkbox" :checked="allSelected" @change="toggleAll" /></th>
            <th @click="sort('name')" class="sortable">SUBSCRIPTION # <span v-html="sortArrow('name')"></span></th>
            <th @click="sort('subscription_name')" class="sortable">NAME <span v-html="sortArrow('subscription_name')"></span></th>
            <th @click="sort('party')" class="sortable">CUSTOMER <span v-html="sortArrow('party')"></span></th>
            <th @click="sort('reference_doctype')" class="sortable">TYPE <span v-html="sortArrow('reference_doctype')"></span></th>
            <th @click="sort('reference_document')" class="sortable">REFERENCE <span v-html="sortArrow('reference_document')"></span></th>
            <th @click="sort('frequency')" class="sortable">FREQUENCY <span v-html="sortArrow('frequency')"></span></th>
            <th @click="sort('next_schedule_date')" class="sortable">NEXT RUN <span v-html="sortArrow('next_schedule_date')"></span></th>
            <th>STATUS</th>
            <th style="width:120px;text-align:right">ACTIONS</th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 6" :key="n"><td colspan="9"><div class="shimmer"></div></td></tr>
          </template>
          <template v-else>
            <tr v-for="r in paged" :key="r.name" class="inv-row" :class="{selected:selected.includes(r.name)}" @click="openView(r)">
              <td @click.stop>
                <input type="checkbox" :checked="selected.includes(r.name)" @change="toggleOne(r.name)" />
              </td>
              <td><DocLink doctype="Auto Repeat" :name="r.name" /></td>
              <td>
                <span v-if="r.subscription_name" style="font-size:13px;color:#111827;font-weight:500">{{ r.subscription_name }}</span>
                <span v-else class="text-muted">—</span>
              </td>
              <td>
                <span v-if="r.party" class="rec-party-cell">{{ r.party }}</span>
                <span v-else class="text-muted">—</span>
              </td>
              <td class="text-muted">{{ r.reference_doctype||'—' }}</td>
              <td @click.stop><DocLink :doctype="r.reference_doctype" :name="r.reference_document" /></td>
              <td>{{ freqLabel(r.frequency) }}</td>
              <td class="mono-sm" :class="r.is_due?'text-accent':''">
                {{ fmtDate(r.next_schedule_date)||'—' }}
                <span v-if="r.is_due" class="rec-due-dot" title="Due"></span>
              </td>
              <td><span class="inv-status-badge" :class="statusClass(r.ui_status)">{{ r.ui_status }}</span></td>
              <td @click.stop style="text-align:right">
                <button class="inv-act-btn" @click="openView(r)" title="View"><span v-html="icon('eye',13)"></span></button>
                <button v-if="r.ui_status==='Active'" class="inv-act-btn" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : 'Pause'" @click="quickAction(r,'pause')"><span v-html="icon('pause',13)"></span></button>
                <button v-else-if="r.ui_status==='Paused'" class="inv-act-btn" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : 'Resume'" @click="quickAction(r,'resume')"><span v-html="icon('play',13)"></span></button>
                <button v-if="r.ui_status!=='Cancelled'&&r.ui_status!=='Completed'" class="inv-act-btn rec-act-danger" :disabled="!$canDelete('invoices')" :title="!$canDelete('invoices') ? 'Not permitted' : 'Delete'" @click="quickAction(r,'delete')"><span v-html="icon('trash',13)"></span></button>
              </td>
            </tr>
            <tr v-if="!sorted.length"><td colspan="10" class="rec-empty">
              <div class="rec-empty-wrap">
                <div class="rec-empty-icon" v-html="icon('repeat',32)"></div>
                <div class="rec-empty-title">No subscriptions yet</div>
                <div class="rec-empty-sub">Create a recurring subscription to auto-generate invoices, bills, or journals on a schedule.</div>
                <button class="sales-btn-primary" :disabled="!$canCreate('invoices')" :title="!$canCreate('invoices') ? 'Read-only access' : ''" @click="openNew" style="margin-top:12px"><span v-html="icon('plus',13)"></span> Create your first subscription</button>
              </div>
            </td></tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- ============================================================ MOBILE CARD LIST -->
    <div class="rec-mobile-list">
      <template v-if="loading">
        <div v-for="n in 5" :key="n" class="rec-mob-card">
          <div class="shimmer" style="height:80px;border-radius:8px"></div>
        </div>
      </template>
      <template v-else>
        <div v-if="!sorted.length" class="rec-empty-wrap">
          <div class="rec-empty-icon" v-html="icon('repeat',32)"></div>
          <div class="rec-empty-title">No subscriptions yet</div>
          <div class="rec-empty-sub">Create a recurring subscription to auto-generate invoices, bills, or journals on a schedule.</div>
          <button class="sales-btn-primary" :disabled="!$canCreate('invoices')" :title="!$canCreate('invoices') ? 'Read-only access' : ''" @click="openNew" style="margin-top:12px"><span v-html="icon('plus',13)"></span> Create your first subscription</button>
        </div>
        <div v-for="r in paged" :key="r.name" class="rec-mob-card" @click="openView(r)">
          <div class="rec-mob-card-top">
            <div class="rec-mob-card-info">
              <span class="inv-link rec-mob-name">{{ r.name }}</span>
              <span v-if="r.subscription_name" class="rec-mob-sub-name">{{ r.subscription_name }}</span>
            </div>
            <span class="inv-status-badge" :class="statusClass(r.ui_status)">{{ r.ui_status }}</span>
          </div>
          <div class="rec-mob-card-mid">
            <span v-if="r.party" class="rec-mob-party">{{ r.party }}</span>
            <span v-else class="text-muted">—</span>
            <span class="rec-mob-freq">{{ freqLabel(r.frequency) }}</span>
          </div>
          <div class="rec-mob-card-ref" v-if="r.reference_document">
            <span class="rec-mob-ref-label">{{ r.reference_doctype }}</span>
            <DocLink :doctype="r.reference_doctype" :name="r.reference_document" @click.stop />
          </div>
          <div class="rec-mob-card-bot">
            <span class="rec-mob-next" :class="r.is_due ? 'text-accent' : ''">
              <span v-html="icon('calendar',12)"></span>
              Next: {{ fmtDate(r.next_schedule_date) || '—' }}
              <span v-if="r.is_due" class="rec-due-dot"></span>
            </span>
            <div class="rec-mob-actions" @click.stop>
              <button class="inv-act-btn" @click="openView(r)" title="View"><span v-html="icon('eye',13)"></span></button>
              <button v-if="r.ui_status==='Active'" class="inv-act-btn" @click="quickAction(r,'pause')" title="Pause"><span v-html="icon('pause',13)"></span></button>
              <button v-else-if="r.ui_status==='Paused'" class="inv-act-btn" @click="quickAction(r,'resume')" title="Resume"><span v-html="icon('play',13)"></span></button>
              <button v-if="r.ui_status!=='Cancelled'&&r.ui_status!=='Completed'" class="inv-act-btn rec-act-danger" @click="quickAction(r,'delete')" title="Delete"><span v-html="icon('trash',13)"></span></button>
            </div>
          </div>
        </div>
      </template>
    </div>

    <div v-if="!loading && sorted.length">
      <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="sorted.length" />
    </div>

    <!-- ============================================================ CREATE / EDIT DRAWER -->
    <Teleport to="body">
      <div v-if="drawerOpen" class="inv-drawer-bg" @click.self="!editMode ? null : onOverlayClose">
        <div class="inv-drawer-panel" :class="{'is-add':!editMode}">

          <!-- Header -->
          <div class="inv-dh">
            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
              <div class="inv-dh-title">{{ editMode ? 'Edit Subscription' : 'New Recurring Subscription' }}</div>
              <span v-if="!editMode" class="add-status-badge">Draft</span>
              <span v-if="editMode" class="inv-dh-sub" style="margin-left:4px">{{ form._name }}</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px">
              <button class="inv-dclose" @click="onOverlayClose"><span v-html="icon('x',16)"></span></button>
            </div>
          </div>

          <!-- Body -->
          <div class="inv-content-row">
          <div class="inv-dbody">

            <!-- Subscription Info Card (edit mode) -->
            <div v-if="editMode" class="rb-info-card">
              <div class="rb-info-row">
                <div class="rb-info-item">
                  <div class="rb-info-lbl">Subscription Name</div>
                  <div class="rb-info-val rb-info-name">{{ form._name }}</div>
                </div>
                <div class="rb-info-item">
                  <div class="rb-info-lbl">Status</div>
                  <span class="inv-status-badge" :class="recStatusClass(form._editStatus)">{{ form._editStatus || 'Active' }}</span>
                </div>
              </div>
              <div class="rb-info-row">
                <div class="rb-info-item">
                  <div class="rb-info-lbl">Customer</div>
                  <div class="rb-info-val">{{ form.customer_name || form.customer || '—' }}</div>
                </div>
                <div class="rb-info-item">
                  <div class="rb-info-lbl">Next Billing Date</div>
                  <div class="rb-info-val" :class="form._nextBillingDate && form._nextBillingDate <= new Date().toISOString().slice(0,10) ? 'text-accent' : ''">
                    {{ fmtDate(form._nextBillingDate) || '—' }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Intro/context card when a reference is selected (create mode) -->
            <div v-if="!editMode && form.reference_document && referenceMeta.party" class="rec-ctx-card">
              <div class="rec-ctx-ico"><span v-html="icon('folder',16)"></span></div>
              <div style="flex:1;min-width:0">
                <div class="rec-ctx-doctype">{{ form.reference_doctype }}</div>
                <div class="rec-ctx-name">{{ form.reference_document }}</div>
              </div>
              <div class="rec-ctx-meta">
                <div class="rec-ctx-party">{{ referenceMeta.party }}</div>
                <div class="rec-ctx-amount mono-sm">{{ fmtCurrency(referenceMeta.amount) }}</div>
              </div>
            </div>

            <!-- Section: Reference -->
            <div class="add-card">
              <div class="add-card-header" @click="collapsed.reference=!collapsed.reference">
                <div class="add-card-title">
                  <span class="add-card-title-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></span>
                  Reference Document
                </div>
                <span class="add-card-chevron" :class="{collapsed:collapsed.reference}">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
                </span>
              </div>
              <div class="add-card-body" :class="{collapsed:collapsed.reference}">
                <div class="inv-fg inv-fg2">
                  <div style="grid-column:1/-1">
                    <label class="inv-lbl">Subscription Name</label>
                    <input v-model="form.subscription_name" type="text" class="inv-fi" placeholder="e.g. Monthly SaaS — Acme Corp" maxlength="140" />
                    <div class="rec-field-help">A friendly label to identify this subscription in the list.</div>
                  </div>
                  <div style="grid-column:1/-1">
                    <label class="inv-lbl">Customer <span class="inv-req">*</span></label>
                    <SearchableSelect
                      v-model="form.customer"
                      :options="customers"
                      :disabled="editMode"
                      placeholder="Select a customer…"
                      @update:modelValue="onCustomerChange"
                    />
                    <div class="rec-field-help" v-if="!form.customer">Select a customer to filter documents below.</div>
                  </div>
                  <div style="grid-column:1/-1">
                    <label class="inv-lbl">Document Type <span class="inv-req">*</span></label>
                    <select v-model="form.reference_doctype" class="inv-fi" :disabled="editMode" @change="onTypeChange">
                      <option value="Sales Invoice">Sales Invoice</option>
                    </select>
                  </div>
                  <div style="grid-column:1/-1">
                    <label class="inv-lbl">Source Document <span class="inv-req">*</span></label>
                    <SearchableSelect
                      v-model="form.reference_document"
                      :options="refDocs"
                      :disabled="editMode || !form.customer"
                      placeholder="Select a customer first…"
                      @search="fetchRefDocs"
                    />
                    <div class="rec-field-help" v-if="form.customer && !form.reference_document">
                      Pick an existing {{ form.reference_doctype.toLowerCase() }} for <strong>{{ customers.find(c=>c.value===form.customer)?.label || form.customer }}</strong>.
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Section: Schedule -->
            <div class="add-card">
              <div class="add-card-header" @click="collapsed.schedule=!collapsed.schedule">
                <div class="add-card-title">
                  <span class="add-card-title-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg></span>
                  Schedule
                </div>
                <span class="add-card-chevron" :class="{collapsed:collapsed.schedule}">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
                </span>
              </div>
              <div class="add-card-body" :class="{collapsed:collapsed.schedule}">
                <div class="inv-fg inv-fg2">
                  <div>
                    <label class="inv-lbl">Frequency <span class="inv-req">*</span></label>
                    <select v-model="form.frequency" class="inv-fi">
                      <option value="Daily">Daily</option>
                      <option value="Weekly">Weekly</option>
                      <option value="Monthly">Monthly</option>
                      <option value="Quarterly">Quarterly</option>
                      <option value="Half-yearly">Half-yearly</option>
                      <option value="Yearly">Yearly</option>
                    </select>
                  </div>
                  <div>
                    <label class="inv-lbl">Submit on Creation</label>
                    <select v-model="form.submit_on_creation" class="inv-fi">
                      <option :value="1">Yes — auto-submit</option>
                      <option :value="0">No — save as draft</option>
                    </select>
                  </div>
                  <div>
                    <label class="inv-lbl">Start Date <span class="inv-req">*</span></label>
                    <input v-model="form.start_date" type="date" class="inv-fi" :disabled="editMode" />
                  </div>
                  <div>
                    <label class="inv-lbl">End Date <span class="rec-hint">(optional)</span></label>
                    <input v-model="form.end_date" type="date" class="inv-fi" :min="form.start_date" />
                  </div>
                  <div v-if="planHint" class="rec-plan-hint" style="grid-column:1/-1">
                    <span v-html="icon('info',13)"></span>
                    <span>{{ planHint }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Section: Notification -->
            <div class="add-card">
              <div class="add-card-header" @click="collapsed.notification=!collapsed.notification">
                <div class="add-card-title">
                  <span class="add-card-title-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg></span>
                  Notification
                </div>
                <div style="display:flex;align-items:center;gap:10px" @click.stop>
                  <label class="rec-toggle">
                    <input type="checkbox" v-model="form._notify" />
                    <span class="rec-toggle-slider"></span>
                  </label>
                  <span class="add-card-chevron" :class="{collapsed:collapsed.notification}" @click="collapsed.notification=!collapsed.notification">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
                  </span>
                </div>
              </div>
              <div class="add-card-body" :class="{collapsed:collapsed.notification}">
                <div v-if="!form._notify" class="rec-section-empty">
                  Email notifications are off. Toggle to email someone every time a document is generated.
                </div>
                <div v-else class="inv-fg inv-fg2">
                  <div style="grid-column:1/-1">
                    <label class="inv-lbl">Recipients <span class="rec-hint">(comma separated)</span></label>
                    <input v-model="form.recipients" type="text" class="inv-fi" placeholder="finance@company.com, owner@company.com" />
                  </div>
                  <div style="grid-column:1/-1">
                    <label class="inv-lbl">Email Subject</label>
                    <input v-model="form.subject" type="text" class="inv-fi" placeholder="Your recurring invoice is ready" />
                  </div>
                  <div style="grid-column:1/-1">
                    <label class="inv-lbl">Email Message</label>
                    <textarea v-model="form.message" class="inv-fi" rows="3" placeholder="Hello, please find your latest document attached…"></textarea>
                  </div>
                </div>
              </div>
            </div>

          </div><!-- /inv-dbody -->
          </div><!-- /inv-content-row -->

          <!-- Footer -->
          <div class="inv-dfooter">
            <div class="add-footer-status">{{ editMode ? 'Editing: ' + form._name : 'New subscription — unsaved changes' }}</div>
            <div class="add-footer-actions">
              <button class="add-btn-cancel" @click="onOverlayClose" :disabled="drawerSaving">Cancel</button>
              <button class="add-btn-more" :disabled="drawerSaving || !(editMode ? $canEdit('invoices') : $canCreate('invoices'))" :title="!(editMode ? $canEdit('invoices') : $canCreate('invoices')) ? 'Read-only access' : ''" @click="saveRec">
                <span v-html="icon('check',13)"></span>
                {{ drawerSaving ? 'Saving…' : (editMode ? 'Save Changes' : 'Create Subscription') }}
              </button>
            </div>
          </div>

        </div>
      </div>
    </Teleport>

    <!-- ============================================================ VIEW DRAWER -->
    <Teleport to="body">
      <div v-if="viewOpen" class="inv-drawer-bg" @click.self="viewOpen=false">
        <div class="inv-drawer-panel inv-view-page rec-view-drawer">
      <template v-if="viewDoc">
        <!-- header -->
        <div class="inv-view-header rec-view-head" :class="viewDoc.ui_status==='Paused'?'paused':viewDoc.ui_status==='Completed'?'completed':''">
          <div class="rec-vhead-content">
            <div class="rec-vhead-title-row">
              <div class="inv-view-number">{{ viewDoc.name }}</div>
              <span class="inv-hdr-badge rec-badge-lg" :class="statusClass(viewDoc.ui_status)">{{ viewDoc.ui_status }}</span>
            </div>
            <div class="inv-view-subtitle">
              {{ viewDoc.reference_doctype }} · {{ freqLabel(viewDoc.frequency) }}
              <span v-if="viewDoc.party"> · {{ viewDoc.party }}</span>
            </div>
          </div>
          <button class="inv-dclose rec-vhead-close" @click="viewOpen=false"><span v-html="icon('x',16)"></span></button>
        </div>
        <!-- subscription stats strip -->
        <div class="rec-view-stats-strip">
          <div><div class="vh-lbl">Total Billed</div><div class="vh-val">{{ fmtCurrency(viewDoc.total_billed) }}</div></div>
          <div><div class="vh-lbl">Generated</div><div class="vh-val">{{ viewDoc.runs_count }}</div></div>
          <div><div class="vh-lbl">Next Run</div><div class="vh-val" :class="isDue(viewDoc)?'text-accent':''">{{ fmtDate(viewDoc.next_schedule_date)||'—' }}</div></div>
        </div>

        <!-- action bar -->
        <div class="rec-view-actbar">
          <button class="rec-va-btn" :disabled="viewDoc.ui_status==='Completed'||viewDoc.ui_status==='Cancelled'||!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="openEdit(viewDoc)"><span v-html="icon('edit',13)"></span><div class="rec-va-btn-text"> Edit</div></button>
          <button class="rec-va-btn" :disabled="viewDoc.ui_status!=='Active' || actionLoading || !$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="runNow(viewDoc)"><span v-html="icon('play',13)"></span><div class="rec-va-btn-text"> Run Now</div></button>
          <button v-if="viewDoc.ui_status==='Active'" class="rec-va-btn" :disabled="actionLoading || !$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="actionOn(viewDoc,'pause')"><span v-html="icon('pause',13)"></span><div class="rec-va-btn-text"> Pause</div></button>
          <button v-else-if="viewDoc.ui_status==='Paused'" class="rec-va-btn" :disabled="actionLoading || !$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="actionOn(viewDoc,'resume')"><span v-html="icon('play',13)"></span><div class="rec-va-btn-text"> Resume</div></button>
          <button class="rec-va-btn rec-va-warn" :disabled="actionLoading||viewDoc.ui_status==='Completed'||viewDoc.ui_status==='Cancelled'||!$canDelete('invoices')" :title="!$canDelete('invoices') ? 'Not permitted' : ''" @click="actionOn(viewDoc,'cancel')"><span v-html="icon('x',13)"></span><div class="rec-va-btn-text"> Cancel</div></button>
          <button class="rec-va-btn rec-va-danger" :disabled="actionLoading || !$canDelete('invoices')" :title="!$canDelete('invoices') ? 'Not permitted' : ''" @click="actionOn(viewDoc,'delete')"><span v-html="icon('trash',13)"></span><div class="rec-va-btn-text"> Delete</div></button>
        </div>

        <!-- timeline -->
        <div class="rec-timeline">
          <div class="rec-tl-step" :class="{done:true}">
            <div class="rec-tl-dot"></div>
            <div class="rec-tl-lbl">Created<br/><span class="rec-tl-sub">{{ fmtDate(viewDoc.creation) }}</span></div>
          </div>
          <div class="rec-tl-line" :class="{done:viewDoc.ui_status!=='Paused'}"></div>
          <div class="rec-tl-step" :class="{done:viewDoc.ui_status==='Active' || viewDoc.runs_count>0, current:viewDoc.ui_status==='Active'}">
            <div class="rec-tl-dot"></div>
            <div class="rec-tl-lbl">{{ viewDoc.ui_status==='Paused'?'Paused':'Active' }}<br/><span class="rec-tl-sub">{{ fmtDate(viewDoc.start_date) }}</span></div>
          </div>
          <div class="rec-tl-line" :class="{done:viewDoc.runs_count>0}"></div>
          <div class="rec-tl-step" :class="{done:viewDoc.runs_count>0}">
            <div class="rec-tl-dot"></div>
            <div class="rec-tl-lbl">Last Run<br/><span class="rec-tl-sub">{{ viewDoc.runs.length?fmtDate(viewDoc.runs[0].creation):'—' }}</span></div>
          </div>
          <div class="rec-tl-line" :class="{done:viewDoc.ui_status==='Completed', danger:viewDoc.ui_status==='Paused'}"></div>
          <div class="rec-tl-step" :class="{done:viewDoc.ui_status==='Completed'}">
            <div class="rec-tl-dot"></div>
            <div class="rec-tl-lbl">{{ viewDoc.end_date?'Ends':'Open-ended' }}<br/><span class="rec-tl-sub">{{ fmtDate(viewDoc.end_date)||'No end' }}</span></div>
          </div>
        </div>

        <!-- tabs -->
        <div class="inv-view-tabs">
          <button v-for="t in viewTabs" :key="t.key" class="inv-vtab" :class="{active:viewTab===t.key}" @click="viewTab=t.key">
            {{ t.label }}<span v-if="t.count!=null" class="inv-vtab-count">{{ t.count }}</span>
          </button>
        </div>

        <div class="inv-dbody">
          <!-- Details tab -->
          <div v-if="viewTab==='details'">
            <div class="rec-meta-grid">
              <div><div class="rec-meta-lbl">Subscription Name</div><div class="rec-meta-value">{{ viewDoc.subscription_name || '—' }}</div></div>
              <div><div class="rec-meta-lbl">Reference</div><div><DocLink :doctype="viewDoc.reference_doctype" :name="viewDoc.reference_document" /></div></div>
              <div><div class="rec-meta-lbl">{{ viewDoc.party_label||'Party' }}</div><div class="rec-meta-value">{{ viewDoc.party||'—' }}</div></div>
              <div><div class="rec-meta-lbl">Frequency</div><div class="rec-meta-value">{{ freqLabel(viewDoc.frequency) }}</div></div>
              <div><div class="rec-meta-lbl">Template Amount</div><div class="rec-meta-value">{{ fmtCurrency(viewDoc.template_amount) }}</div></div>
              <div><div class="rec-meta-lbl">Start Date</div><div class="rec-meta-value">{{ fmtDate(viewDoc.start_date) }}</div></div>
              <div><div class="rec-meta-lbl">End Date</div><div class="rec-meta-value">{{ fmtDate(viewDoc.end_date)||'Open-ended' }}</div></div>
              <div><div class="rec-meta-lbl">Submit on Creation</div><div class="rec-meta-value">{{ viewDoc.submit_on_creation?'Yes':'No (Draft)' }}</div></div>
              <div><div class="rec-meta-lbl">Notify by Email</div><div class="rec-meta-value">{{ viewDoc.notify_by_email?'Yes':'No' }}</div></div>
              <div v-if="viewDoc.notify_by_email" style="grid-column:1/-1">
                <div class="rec-meta-lbl">Recipients</div>
                <div class="rec-meta-value" style="word-break:break-all">{{ viewDoc.recipients||'—' }}</div>
              </div>
              <div v-if="viewDoc.subject" style="grid-column:1/-1">
                <div class="rec-meta-lbl">Email Subject</div>
                <div class="rec-meta-value">{{ viewDoc.subject }}</div>
              </div>
            </div>
          </div>

          <!-- Generated tab -->
          <div v-else-if="viewTab==='generated'">
            <div v-if="!viewDoc.runs.length" class="rec-tab-empty">No documents generated yet.</div>
            <template v-else>
              <!-- Desktop table -->
              <table class="inv-table rec-table-inner rec-gen-table-desktop">
                <thead>
                  <tr><th>Document</th><th>Created</th><th style="text-align:right">Amount</th><th>Status</th></tr>
                </thead>
                <tbody>
                  <tr v-for="d in viewDoc.runs" :key="d.name" class="inv-row">
                    <td><DocLink :doctype="viewDoc.reference_doctype" :name="d.name" /></td>
                    <td class="text-muted mono-sm">{{ fmtDate(d.creation) }}</td>
                    <td style="text-align:right" class="mono-sm">{{ fmtCurrency(d.grand_total) }}</td>
                    <td>
                      <span class="inv-status-badge" :class="d.docstatus===1?'badge-green':d.docstatus===2?'badge-red':'badge-grey'">
                        {{ d.docstatus===1?'Submitted':d.docstatus===2?'Cancelled':'Draft' }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
              <!-- Mobile cards -->
              <div class="rec-gen-cards-mobile">
                <div v-for="d in viewDoc.runs" :key="d.name" class="rec-gen-card">
                  <div class="rec-gen-card-top">
                    <DocLink :doctype="viewDoc.reference_doctype" :name="d.name" />
                    <span class="inv-status-badge" :class="d.docstatus===1?'badge-green':d.docstatus===2?'badge-red':'badge-grey'">
                      {{ d.docstatus===1?'Submitted':d.docstatus===2?'Cancelled':'Draft' }}
                    </span>
                  </div>
                  <div class="rec-gen-card-bot">
                    <span class="rec-gen-card-date">{{ fmtDate(d.creation) }}</span>
                    <span class="rec-gen-card-amount">{{ fmtCurrency(d.grand_total) }}</span>
                  </div>
                </div>
              </div>
            </template>
          </div>

          <!-- Upcoming tab -->
          <div v-else-if="viewTab==='upcoming'">
            <div v-if="!viewDoc.upcoming.length" class="rec-tab-empty">No upcoming runs scheduled. End date may have passed or subscription is paused.</div>
            <ol v-else class="rec-upcoming-list">
              <li v-for="(u,i) in viewDoc.upcoming" :key="i">
                <span class="rec-upcoming-idx">#{{ i+1 }}</span>
                <span class="mono-sm">{{ fmtDate(u.date) }}</span>
                <span class="text-muted">— {{ u.frequency }}</span>
              </li>
            </ol>
          </div>
        </div>
      </template>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from "vue";
import { apiSave, apiGET, apiPOST, apiList, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { useRoute } from "vue-router";
import { useConfirm } from "../composables/useConfirm.js";
import { useOpenFromQuery } from "../composables/useOpenFromQuery.js";
import { usePagination } from "../composables/usePagination.js";
import DocLink from "../components/DocLink.vue";
import Pagination from "../components/Pagination.vue";
import SummaryStrip from "../components/SummaryStrip.vue";
import { icon } from "../utils/icons.js";
import { fmtDate } from "../utils/format.js";
import SearchableSelect from "../components/SearchableSelect.vue";

const { toast } = useToast();
const route = useRoute();
const { confirm } = useConfirm();

// state
const list = ref([]);
const loading = ref(false);
const search = ref("");
const activeTab = ref("all");
const stats = ref({ total: 0, active: 0, paused: 0, due_today: 0, overdue: 0, completed: 0 });
const sortCol = ref("next_schedule_date");
const sortDir = ref("asc");
const selected = ref([]);
const actionLoading = ref(false);

// create/edit drawer
const drawerOpen = ref(false);
const drawerSaving = ref(false);
const editMode = ref(false);
const refDocs = ref([]);
const customers = ref([]);
const collapsed = reactive({ reference: false, schedule: false, notification: false });
const referenceMeta = reactive({ party_label: "", party: "", amount: 0 });
const form = reactive({
  _name: "",
  customer: "",
  customer_name: "",
  _editStatus: "",
  _nextBillingDate: "",
  subscription_name: "",
  reference_doctype: "Sales Invoice",
  reference_document: "",
  frequency: "Monthly",
  start_date: new Date().toISOString().slice(0, 10),
  end_date: "",
  submit_on_creation: 1,
  _notify: false,
  recipients: "",
  subject: "",
  message: "",
});

// view drawer
const viewOpen = ref(false);
const viewDoc = ref(null);
const viewTab = ref("details");

// ----- derived
const tabs = computed(() => [
  { key: "all", label: "All", count: stats.value.total },
  { key: "Active", label: "Active", count: stats.value.active },
  { key: "Paused", label: "Paused", count: stats.value.paused },
  { key: "Completed", label: "Completed", count: stats.value.completed || null },
]);

const viewTabs = computed(() => [
  { key: "details", label: "Details" },
  { key: "generated", label: "Generated", count: viewDoc.value?.runs_count ?? 0 },
  { key: "upcoming", label: "Upcoming", count: viewDoc.value?.upcoming?.length ?? 0 },
]);

const filtered = computed(() => {
  let r = list.value;
  if (activeTab.value !== "all") r = r.filter((x) => x.ui_status === activeTab.value);
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    r = r.filter((x) =>
      (x.name || "").toLowerCase().includes(q) ||
      (x.reference_document || "").toLowerCase().includes(q) ||
      (x.party || "").toLowerCase().includes(q)
    );
  }
  return r;
});

const sorted = computed(() => {
  const col = sortCol.value;
  return [...filtered.value].sort((a, b) => {
    const av = a[col] ?? "";
    const bv = b[col] ?? "";
    const c = String(av).localeCompare(String(bv));
    return sortDir.value === "asc" ? c : -c;
  });
});

const { page, pageSize, paged } = usePagination(sorted, { storageKey: "recurring" });

const allSelected = computed(() => sorted.value.length > 0 && sorted.value.every((r) => selected.value.includes(r.name)));

const planHint = computed(() => {
  if (!form.start_date || !form.end_date) return form.start_date ? "Open-ended subscription — runs until paused or cancelled." : "";
  const start = new Date(form.start_date);
  const end = new Date(form.end_date);
  if (end < start) return "End date is before start date.";
  const months = (end.getFullYear() - start.getFullYear()) * 12 + (end.getMonth() - start.getMonth());
  const map = { Daily: Math.max(1, Math.round((end - start) / 86400000)), Weekly: Math.max(1, Math.round((end - start) / (7 * 86400000))), Monthly: months + 1, Quarterly: Math.floor(months / 3) + 1, "Half-yearly": Math.floor(months / 6) + 1, Yearly: end.getFullYear() - start.getFullYear() + 1 };
  const n = map[form.frequency] || 0;
  return `Will generate approximately ${n} document${n !== 1 ? "s" : ""}.`;
});

// ----- helpers
function freqLabel(f) { return f || "—"; }
function statusClass(s) {
  if (s === "Cancelled" || s === "Completed") return "badge-grey";
  if (s === "Paused") return "badge-orange";
  return "badge-green";
}
function recStatusClass(s) {
  if (s === "Cancelled" || s === "Completed") return "badge-grey";
  if (s === "Paused") return "badge-orange";
  return "badge-green";
}
function isDue(r) {
  const t = new Date().toISOString().slice(0, 10);
  return r.next_schedule_date && r.next_schedule_date <= t && r.ui_status === "Active";
}
function fmtCurrency(v) {
  if (v == null || v === "") return "—";
  const n = Number(v) || 0;
  return "₹" + n.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function sort(col) {
  if (sortCol.value === col) sortDir.value = sortDir.value === "asc" ? "desc" : "asc";
  else { sortCol.value = col; sortDir.value = "asc"; }
}
function sortArrow(col) {
  if (sortCol.value !== col) return '<span style="color:#d1d5db">⇅</span>';
  return sortDir.value === "asc" ? "↑" : "↓";
}

function toggleAll() { selected.value = allSelected.value ? [] : sorted.value.map((r) => r.name); }
function toggleOne(n) { selected.value = selected.value.includes(n) ? selected.value.filter((x) => x !== n) : [...selected.value, n]; }

// ----- load
async function load() {
  loading.value = true;
  try {
    const [rows, st] = await Promise.all([
      apiGET("zoho_books_clone.api.recurring.get_subscriptions", { limit: 200 }),
      apiGET("zoho_books_clone.api.recurring.get_subscription_stats", {}),
    ]);
    const allRows = Array.isArray(rows) ? rows : (rows?.message ?? []);

    const filteredRows = allRows.filter(
      (r) => r.reference_doctype === "Sales Invoice"
    );

    list.value = filteredRows;

    stats.value = {
      total: filteredRows.length,
      active: filteredRows.filter(r => r.ui_status === "Active").length,
      paused: filteredRows.filter(r => r.ui_status === "Paused").length,
      completed: filteredRows.filter(r => r.ui_status === "Completed").length,
      due_today: filteredRows.filter(r => r.is_due).length,
      overdue: filteredRows.filter(
        r =>
          r.ui_status === "Active" &&
          r.next_schedule_date &&
          r.next_schedule_date < new Date().toISOString().slice(0, 10) &&
          !r.is_due
      ).length,
    };
  } catch (e) {
    console.warn("Failed to load subscriptions", e);
    list.value = [];
    toast.error(e.message || "Failed to load subscriptions");
  } finally {
    loading.value = false;
  }
}
onMounted(async () => {
  await load();
  useOpenFromQuery({
    route,
    openByName: (n) => openView(list.value.find(x => x.name === n) || { name: n }),
  });
});

// ----- view drawer
async function openView(r) {
  if (!r?.name) return;
  viewOpen.value = true;
  viewTab.value = "details";
  // optimistic shallow view first
  viewDoc.value = { ...r, runs: r.runs || [], upcoming: r.upcoming || [], total_billed: r.total_billed || 0, runs_count: r.runs_count || 0 };
  try {
    const detail = await apiGET("zoho_books_clone.api.recurring.get_subscription", { name: r.name });
    // apiGET already unwraps `.message`, so `detail` is the dict directly.
    const d = (detail && typeof detail === "object") ? detail : {};
    // Merge: keep optimistic fields and overlay detail-only fields. Detail's
    // `runs` always wins (it's the authoritative source), even if empty.
    viewDoc.value = {
      ...viewDoc.value,
      ...d,
      runs: Array.isArray(d.runs) ? d.runs : (viewDoc.value.runs || []),
      upcoming: Array.isArray(d.upcoming) ? d.upcoming : (viewDoc.value.upcoming || []),
      runs_count: (d.runs_count != null) ? d.runs_count
                  : (Array.isArray(d.runs) ? d.runs.length : (viewDoc.value.runs_count || 0)),
      total_billed: (d.total_billed != null) ? d.total_billed : (viewDoc.value.total_billed || 0),
    };
  } catch (e) {
    toast.error(e.message || "Failed to load subscription detail");
  }
}

// ----- actions
async function quickAction(r, action) {
  const messages = {
    pause: { title: `Pause ${r.name}?`, body: "It will stop generating documents until resumed.", okLabel: "Pause", okStyle: "primary" },
    resume: { title: `Resume ${r.name}?`, body: "It will start generating documents on schedule.", okLabel: "Resume", okStyle: "primary" },
    cancel: { title: `Cancel ${r.name}?`, body: "Subscription will be ended permanently.", okLabel: "Cancel Sub", okStyle: "danger" },
    delete: { title: `Delete ${r.name}?`, body: "This cannot be undone.", okLabel: "Delete", okStyle: "danger" },
  };
  const m = messages[action];
  if (!(await confirm(m))) return;
  await runLifecycle(r.name, action);
}

async function actionOn(doc, action) {
  if (!doc?.name) return;
  const docName = doc.name;
  await quickAction(doc, action);
  if (action === "delete") {
    viewOpen.value = false;
  } else if (viewOpen.value && docName) {
    await openView({ name: docName });
  }
}

async function runLifecycle(name, action) {
  actionLoading.value = true;
  try {
    const method = `zoho_books_clone.api.recurring.${action}_subscription`;
    const res = await apiPOST(method, { name });
    toast.success(res?.message?.message || res?.message || `${name} ${action}d`);
    await load();
  } catch (e) {
    toast.error(e.message || `Failed to ${action}`);
  } finally {
    actionLoading.value = false;
  }
}

async function runNow(doc) {
  if (!doc?.name) return;
  const docName = doc.name;
  if (!(await confirm({ title: `Run ${docName} now?`, body: "A new document will be generated immediately, ignoring the schedule.", okLabel: "Run Now", okStyle: "primary" }))) return;
  actionLoading.value = true;
  try {
    const res = await apiPOST("zoho_books_clone.api.recurring.run_subscription_now", { name: docName });
    const gen = res?.message?.generated || res?.generated;
    toast.success(gen ? `Generated ${gen}` : "Document generated");
    await load();
    await openView({ name: docName });
  } catch (e) {
    toast.error(e.message || "Failed to run subscription");
  } finally {
    actionLoading.value = false;
  }
}

async function bulkDo(action) {
  if (!selected.value.length) return;
  if (!(await confirm({ title: `${action.charAt(0).toUpperCase()+action.slice(1)} ${selected.value.length} subscription(s)?`, body: "This applies to all selected rows.", okLabel: action.charAt(0).toUpperCase()+action.slice(1), okStyle: action === "delete" || action === "cancel" ? "danger" : "primary" }))) return;
  actionLoading.value = true;
  try {
    const res = await apiPOST("zoho_books_clone.api.recurring.bulk_action", { names: selected.value, action });
    const ok = res?.message?.ok || res?.ok || [];
    const failed = res?.message?.failed || res?.failed || [];
    toast.success(`${ok.length} updated${failed.length ? `, ${failed.length} failed` : ""}`);
    selected.value = [];
    await load();
  } catch (e) {
    toast.error(e.message || "Bulk action failed");
  } finally {
    actionLoading.value = false;
  }
}

// ----- create / edit
function openNew() {
  editMode.value = false;
  Object.assign(form, {
    _name: "", customer: "", customer_name: "", _editStatus: "", _nextBillingDate: "",
    subscription_name: "",
    reference_doctype: "Sales Invoice", reference_document: "",
    frequency: "Monthly", start_date: new Date().toISOString().slice(0, 10),
    end_date: "", submit_on_creation: 1, _notify: false,
    recipients: "", subject: "", message: "",
  });
  Object.assign(referenceMeta, { party_label: "", party: "", amount: 0 });
  drawerOpen.value = true;
  fetchCustomers();
  fetchRefDocs("");
}

function openEdit(doc) {
  if (!doc?.name) return;
  editMode.value = true;
  viewOpen.value = false;
  Object.assign(form, {
    _name: doc.name,
    customer: doc.customer || doc.party || "",
    customer_name: doc.customer_name || doc.party || "",
    _editStatus: doc.ui_status || doc.status || "Active",
    _nextBillingDate: doc.next_schedule_date || "",
    subscription_name: doc.subscription_name || "",
    reference_doctype: doc.reference_doctype,
    reference_document: doc.reference_document,
    frequency: doc.frequency,
    start_date: doc.start_date || "",
    end_date: doc.end_date || "",
    submit_on_creation: doc.submit_on_creation ? 1 : 0,
    _notify: !!doc.notify_by_email,
    recipients: doc.recipients || "",
    subject: doc.subject || "",
    message: doc.message || "",
  });
  refDocs.value = doc.reference_document ? [{ label: doc.reference_document, value: doc.reference_document }] : [];
  Object.assign(referenceMeta, { party_label: doc.party_label || "", party: doc.party || "", amount: doc.template_amount || 0 });
  fetchCustomers();
  drawerOpen.value = true;
}

function onOverlayClose() {
  if (drawerSaving.value) return;
  drawerOpen.value = false;
}

function onTypeChange() {
  form.reference_document = "";
  refDocs.value = [];
  Object.assign(referenceMeta, { party_label: "", party: "", amount: 0 });
  fetchRefDocs("");
}

function onCustomerChange() {
  form.reference_document = "";
  refDocs.value = [];
  Object.assign(referenceMeta, { party_label: "", party: "", amount: 0 });
  fetchRefDocs("");
}

async function fetchCustomers() {
  try {
    const r = await apiList("Customer", { fields: ["name", "customer_name"], filters: [["disabled", "=", 0]], limit: 500, order: "customer_name asc" }) || [];
    customers.value = r.map(x => ({ value: x.name, label: x.customer_name || x.name }));
  } catch { customers.value = []; }
}

async function fetchRefDocs(q = "") {
  const doctype = form.reference_doctype || "Sales Invoice";
  try {
    // Sales Invoices: only submitted (docstatus=1) — must be posted to ledger.
    const filters = [["docstatus", "=", 1]];
    if (form.customer) filters.push(["customer", "=", form.customer]);
    if (q) filters.push(["name", "like", `%${q}%`]);

    const r = await apiGET("frappe.client.get_list", {
      doctype,
      filters: JSON.stringify(filters),
      fields: JSON.stringify(["name", "customer_name"]),
      limit: 50,
      order_by: "name asc",
    });
    const rows = Array.isArray(r) ? r : (r?.message ?? []);
    refDocs.value = rows.map((x) => ({ label: x.customer_name ? `${x.name} — ${x.customer_name}` : x.name, value: x.name }));
  } catch {
    refDocs.value = [];
  }
}

// Watch the chosen reference document to fetch its party + amount
watch(() => form.reference_document, async (v) => {
  if (!v || !form.reference_doctype) {
    Object.assign(referenceMeta, { party_label: "", party: "", amount: 0 });
    return;
  }
  try {
    const fieldsByType = {
      "Sales Invoice": ["customer_name", "grand_total"],
    };
    const fields = fieldsByType[form.reference_doctype];
    if (!fields) return;
    const r = await apiGET("frappe.client.get_value", {
      doctype: form.reference_doctype,
      filters: JSON.stringify({ name: v }),
      fieldname: JSON.stringify(fields),
    });
    const row = r?.message || {};
    Object.assign(referenceMeta, {
      party_label: form.reference_doctype === "Sales Invoice" ? "Customer" : "Party",
      party: row[fields[0]] || "",
      amount: Number(row[fields[1]]) || 0,
    });
  } catch {
    /* silent */
  }
});

async function saveRec() {
  if (!form.customer) return toast.error("Customer is required");
  if (!form.reference_document) return toast.error("Reference document is required");
  if (!form.start_date) return toast.error("Start date is required");
  if (form.end_date && form.end_date < form.start_date) return toast.error("End date must be after start date");

  drawerSaving.value = true;
  try {
    if (editMode.value) {
      await apiPOST("zoho_books_clone.api.recurring.update_subscription", {
        name: form._name,
        subscription_name: form.subscription_name,
        frequency: form.frequency,
        end_date: form.end_date || "",
        notify_by_email: form._notify ? 1 : 0,
        submit_on_creation: form.submit_on_creation,
        recipients: form.recipients,
        subject: form.subject,
        message: form.message,
      });
      toast.success(`${form._name} updated`);
    } else {
      const saved = await apiPOST("zoho_books_clone.api.recurring.make_recurring_from_doc", {
        reference_doctype:  form.reference_doctype,
        reference_document: form.reference_document,
        subscription_name:  form.subscription_name,
        frequency:          form.frequency,
        start_date:         form.start_date,
        end_date:           form.end_date || "",
        submit_on_creation: form.submit_on_creation,
        notify_by_email:    form._notify ? "1" : "",
        recipients:         form.recipients || "",
        subject:            form.subject || "",
        message:            form.message || "",
      });
      toast.success(`Subscription ${saved?.name || ""} created`);
    }
    drawerOpen.value = false;
    // After an edit, reopen the view drawer with refreshed data
    if (editMode.value && form._name) await openView({ name: form._name });
    else if (viewOpen.value && viewDoc.value?.name) await openView({ name: viewDoc.value.name });
    await load();
  } catch (e) {
    toast.error(e.message || "Failed to save");
  } finally {
    drawerSaving.value = false;
  }
}

// ----- export
function exportCSV() {
  // If any rows are selected, export only those; otherwise export the filtered view.
  const source = selected.value.length
    ? sorted.value.filter((r) => selected.value.includes(r.name))
    : sorted.value;
  if (!source.length) return;
  const headers = ["Subscription #", "Type", "Reference", "Party", "Amount", "Frequency", "Start Date", "End Date", "Next Run", "Status", "Runs"];
  const rows = source.map((r) => [
    r.name, r.reference_doctype, r.reference_document, r.party, r.amount, r.frequency,
    r.start_date, r.end_date, r.next_schedule_date, r.ui_status, r.runs_count,
  ]);
  const esc = (v) => {
    const s = v == null ? "" : String(v);
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  const csv = "﻿" + [headers, ...rows].map((r) => r.map(esc).join(",")).join("\r\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `recurring-subscriptions-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
</script>

<style scoped>
/* ── Subscription-specific: view header states ── */
.rec-view-head { background:linear-gradient(135deg,#eff6ff 0%,#dbeafe 100%); }
.rec-view-head.paused { background:linear-gradient(135deg,#fff7ed 0%,#fed7aa 100%); }
.rec-view-head.completed { background:linear-gradient(135deg,#f3f4f6 0%,#e5e7eb 100%); }

/* ── Subscription stats strip under the header ── */
.rec-view-stats-strip { display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding:12px 20px;background:#fff;border-bottom:1px solid #e5e7eb;flex-shrink:0; }
.rec-view-stats-strip > div { background:#f8fafc;border-radius:8px;padding:8px 10px; }
.vh-lbl { font-size:10.5px;color:#475569;text-transform:uppercase;letter-spacing:.05em;font-weight:600; }
.vh-val { font-size:15px;font-weight:700;color:#0f172a;margin-top:2px; }

/* ── Frequency / subscription badge ── */
.rec-badge-lg { padding:4px 12px;font-size:12.5px; }

/* ── Action bar in view ── */
.rec-view-actbar { display:flex;flex-wrap:wrap;gap:6px;padding:10px 20px;border-bottom:1px solid #e5e7eb;background:#fff;flex-shrink:0; }
.rec-va-btn { display:inline-flex;align-items:center;gap:5px;border:1px solid #e5e7eb;background:#fff;color:#374151;border-radius:7px;padding:6px 11px;font-size:12.5px;font-weight:600;cursor:pointer; }
.rec-va-btn:hover { background:#f9fafb;border-color:#cbd5e1; }
.rec-va-btn:disabled { opacity:.45;cursor:not-allowed; }
.rec-va-warn { color:#ea580c;border-color:#fed7aa; }
.rec-va-warn:hover:not(:disabled) { background:#fff7ed; }
.rec-va-danger { color:#dc2626;border-color:#fecaca; }
.rec-va-danger:hover:not(:disabled) { background:#fef2f2; }

/* ── Timeline ── */
.rec-timeline { display:flex;align-items:center;padding:14px 20px;background:#fff;border-bottom:1px solid #e5e7eb;gap:0;flex-shrink:0; }
.rec-tl-step { display:flex;flex-direction:column;align-items:center;flex-shrink:0;min-width:80px; }
.rec-tl-dot { width:12px;height:12px;border-radius:50%;background:#e5e7eb;border:2px solid #fff;box-shadow:0 0 0 2px #e5e7eb; }
.rec-tl-step.done .rec-tl-dot { background:#16a34a;box-shadow:0 0 0 2px #16a34a; }
.rec-tl-step.current .rec-tl-dot { background:#2563eb;box-shadow:0 0 0 3px #bfdbfe; }
.rec-tl-lbl { font-size:11px;color:#6b7280;text-align:center;margin-top:6px;font-weight:600;line-height:1.3; }
.rec-tl-sub { font-weight:400;color:#9ca3af;font-size:10.5px; }
.rec-tl-line { flex:1;height:2px;background:#e5e7eb;min-width:20px; }
.rec-tl-line.done { background:#16a34a; }
.rec-tl-line.danger { background:#dc2626; }

/* ── Section wrappers in drawer body ── */
.rec-section { background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:12px;box-shadow:0 1px 2px rgba(15,23,42,.03);margin-bottom: 20px; }
.rec-section-empty { font-size:12.5px;color:#6b7280;font-style:italic;line-height:1.5; }
.rec-field-help { font-size:11.5px;color:#9ca3af;margin-top:4px; }

/* ── Toggle ── */
.rec-toggle { position:relative;width:34px;height:18px;display:inline-block;cursor:pointer; }
.rec-toggle input { opacity:0;width:0;height:0; }
.rec-toggle-slider { position:absolute;inset:0;background:#cbd5e1;border-radius:18px;transition:background .18s; }
.rec-toggle-slider::before { content:"";position:absolute;width:14px;height:14px;left:2px;top:2px;background:#fff;border-radius:50%;transition:transform .18s;box-shadow:0 1px 3px rgba(0,0,0,.15); }
.rec-toggle input:checked + .rec-toggle-slider { background:#2563eb; }
.rec-toggle input:checked + .rec-toggle-slider::before { transform:translateX(16px); }

/* ── Reference context card ── */
.rec-ctx-card { display:flex;align-items:center;gap:12px;background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:12px 14px;box-shadow:0 1px 2px rgba(15,23,42,.04); }
.rec-ctx-ico { width:36px;height:36px;border-radius:8px;background:#dbeafe;color:#2563eb;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0; }
.rec-ctx-doctype { font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.04em;font-weight:600; }
.rec-ctx-name { font-size:13px;color:#0f172a;font-weight:600;margin-top:1px; }
.rec-ctx-meta { text-align:right;display:flex;flex-direction:column;gap:2px;flex-shrink:0; }
.rec-ctx-party { font-size:12px;color:#475569;font-weight:600;max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap; }

/* ── Schedule hint ── */
.rec-plan-hint { background:#eff6ff;border:1px solid #bfdbfe;color:#1d4ed8;padding:8px 12px;border-radius:8px;font-size:12px;display:flex;align-items:center;gap:8px; }

/* ── Meta grid in details tab ── */
.rec-meta-grid { display:grid;grid-template-columns:1fr 1fr;gap:14px; }
.rec-meta-lbl { font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;margin-bottom:2px;font-weight:600; }

/* ── Generated / Upcoming tabs ── */
.rec-table-inner { font-size:12.5px; }
.rec-table-inner th { background:#fafafa; }
.rec-tab-empty { padding:24px;text-align:center;color:#9ca3af;font-size:13px; }
.rec-upcoming-list { list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:8px; }
.rec-upcoming-list li { background:#f9fafb;border:1px solid #f3f4f6;border-radius:8px;padding:10px 14px;display:flex;align-items:center;gap:12px;font-size:13px; }
.rec-upcoming-idx { background:#dbeafe;color:#1d4ed8;font-weight:700;padding:2px 8px;border-radius:8px;font-size:11.5px;}

/* ── Misc ── */
.rec-party-cell { font-size:13px;color:#111827;font-weight:500; }
.rec-due-dot { display:inline-block;width:6px;height:6px;background:#2563eb;border-radius:50%;margin-left:6px;vertical-align:middle; }
/* ── Subscription info card (edit form) ── */
.rb-info-card{background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;padding:14px 16px;margin-bottom:4px;display:flex;flex-direction:column;gap:10px;}
.rb-info-row{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
.rb-info-item{display:flex;flex-direction:column;gap:3px;}
.rb-info-lbl{font-size:11px;font-weight:700;color:#0369a1;text-transform:uppercase;letter-spacing:.04em;}
.rb-info-val{font-size:13px;color:#0f172a;font-weight:500;}
.rb-info-name{font-weight:700;color:#1d4ed8;font-size:14px;}
.rec-act-danger:hover { color:#dc2626;background:#fef2f2; }
.rec-empty { text-align:center;padding:0!important;cursor:default!important; }
.rec-empty-wrap { padding:48px 20px;display:flex;flex-direction:column;align-items:center;gap:6px;color:#6b7280; }
.rec-empty-icon { color:#cbd5e1;margin-bottom:6px; }
.rec-empty-title { font-size:15px;font-weight:600;color:#374151; }
.rec-empty-sub { font-size:12.5px;max-width:380px;text-align:center; }
.rec-hint { font-weight:400;color:#9ca3af;font-size:11px; }
.text-muted { color:#374151; }
.text-accent { color:#2563eb;font-weight:600; }
.mono-sm {font-size:13px; }
.req { color:#dc2626; }
.badge-green { background:#dcfce7;color:#16a34a;width: fit-content; }
.badge-orange { background:#fef3c7;color:#ea580c;width: fit-content; }
.badge-grey { background:#e5e7eb;color:#6b7280;width: fit-content; }
.badge-red { background:#fee2e2;color:#dc2626;width: fit-content; }
.rec-view-drawer { width: 625px; right: -625px; }

/* ── View header layout ── */
.rec-view-head { position: relative; }
.rec-vhead-content { flex: 1; min-width: 0; }
.rec-vhead-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 3px;
}
.rec-vhead-close {
  position: absolute;
  top: 12px;
  right: 12px;
  flex-shrink: 0;
}

@media (max-width: 480px) {
  .rec-timeline { display:none; }
  .rec-va-btn-text { display: none; }
}

/* ── Mobile card list ── */
.rec-mobile-list { display: none; }

@media (max-width: 768px) {
  /* Hide desktop table, show cards */
  .inv-table-wrap { display: none; }
  .rec-mobile-list { display: flex; flex-direction: column; gap: 10px; padding: 0 12px 12px; }

  /* Toolbar adjustments */
  .sales-toolbar { flex-wrap: wrap; gap: 8px; padding: 10px 12px; }
  .sales-pills { order: 3; width: 100%; overflow-x: auto; flex-wrap: nowrap; padding-bottom: 2px; }
  .sales-search { order: 1; flex: 1; min-width: 0; }
  .sales-toolbar > div:last-child { order: 2; margin-left: 0 !important; }

  /* KPI grids */
  .bk-kpi-grid-4 { grid-template-columns: 1fr 1fr; gap: 8px; }
  .bk-stat-grid { grid-template-columns: 1fr 1fr; gap: 8px; }

  /* Card styles */
  .rec-mob-card {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    box-shadow: 0 1px 3px rgba(15,23,42,.06);
    cursor: pointer;
    transition: box-shadow .15s, border-color .15s;
  }
  .rec-mob-card:active { box-shadow: 0 2px 8px rgba(15,23,42,.1); border-color: #bfdbfe; }

  .rec-mob-card-top {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 8px;
  }
  .rec-mob-card-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .rec-mob-name { font-size: 13px; font-weight: 700; color: #2563eb; }
  .rec-mob-sub-name { font-size: 13px; color: #111827; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  .rec-mob-card-mid {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  .rec-mob-party { font-size: 13px; color: #374151; font-weight: 500; }
  .rec-mob-freq {
    font-size: 11.5px;
    font-weight: 600;
    color: #6b7280;
    background: #f3f4f6;
    border-radius: 6px;
    padding: 2px 8px;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .rec-mob-card-ref {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
  }
  .rec-mob-ref-label {
    color: #9ca3af;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .03em;
    flex-shrink: 0;
  }

  .rec-mob-card-bot {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-top: 6px;
    border-top: 1px solid #f3f4f6;
    gap: 8px;
  }
  .rec-mob-next {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    color: #6b7280;
  }
  .rec-mob-actions { display: flex; align-items: center; gap: 4px; }
}
.rec-meta-value {
  font-size: 13px;
  color: #111827;
  font-weight: 500;
}

/* ── Generated tab: desktop table / mobile cards ── */
.rec-gen-table-desktop { display: table; }
.rec-gen-cards-mobile  { display: none; }

@media (max-width: 768px) {
  .rec-gen-table-desktop { display: none !important; }
  .rec-gen-cards-mobile  {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 4px 0;
  }
  .rec-gen-card {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 10px 14px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    box-shadow: 0 1px 3px rgba(15,23,42,.05);
  }
  .rec-gen-card-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  .rec-gen-card-bot {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding-top: 6px;
    border-top: 1px solid #f3f4f6;
  }
  .rec-gen-card-date {
    font-size: 12px;
    color: #6b7280;
  }
  .rec-gen-card-amount {
    font-size: 13px;
    font-weight: 700;
    color: #0f172a;
  }
}
</style>