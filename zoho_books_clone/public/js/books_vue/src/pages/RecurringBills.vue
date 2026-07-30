<template>
  <div class="rec-page">
    <!-- ============================================================ TOOLBAR -->
    <div class="rec-actions">
      <div class="rec-list-actions">
        <div class="rec-search-wrap">
          <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
          <input v-model="search" placeholder="Search recurring bills…" class="rec-search-input" />
        </div>
        <div class="rec-pills">
          <button v-for="t in tabs" :key="t.key" class="rec-pill" :class="{active:activeTab===t.key, ['pill-'+t.key]: t.key!=='all'}" @click="activeTab=t.key">
            {{ t.label }}
          </button>
        </div>
      </div>
      <div style="display:flex;gap:8px;">
        <button class="rec-btn-ghost" @click="load" :disabled="loading">
          <span v-html="icon('refresh',14)"></span>
        </button>
        <button class="rec-btn-primary" :disabled="!$canCreate('bills')" :title="!$canCreate('bills') ? 'Read-only access' : ''" @click="openNew">
          <span v-html="icon('plus',13)"></span> New Recurring Bill
        </button>
      </div>
    </div>

    <!-- ── KPI Cards ── -->
    <div class="bk-kpi-grid bk-kpi-grid-4">
      <div class="bk-kpi-card"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#dbeafe"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.8"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Total Schedules</div><div class="bk-kpi-value">{{ list.length }}</div><div class="bk-kpi-trend bk-trend-neutral">all recurring bills</div></div></div></div>
      <div class="bk-kpi-card bk-kpi-success clickable" @click="activeTab='Active'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#dcfce7"><svg width="22" height="22" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="#16a34a" stroke-width="1.8"/><polyline points="7 12.5 10.5 16 17 9" stroke="#16a34a" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Active</div><div class="bk-kpi-value bk-kpi-green">{{ counts.active }}</div><div class="bk-kpi-trend bk-trend-neutral">running</div></div></div></div>
      <div class="bk-kpi-card bk-kpi-warn clickable" @click="activeTab='Paused'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#fef3c7"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><line x1="10" y1="15" x2="10" y2="9"/><line x1="14" y1="15" x2="14" y2="9"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Paused</div><div class="bk-kpi-value bk-kpi-amber">{{ counts.paused }}</div><div class="bk-kpi-trend bk-trend-neutral">on hold</div></div></div></div>
      <div class="bk-kpi-card bk-kpi-danger clickable" @click="activeTab='Cancelled'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#fee2e2"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Cancelled</div><div class="bk-kpi-value bk-kpi-red">{{ counts.cancelled }}</div><div class="bk-kpi-trend bk-trend-neutral">stopped</div></div></div></div>
    </div>
    <div class="bk-stat-grid">
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">Active Rate</div><div class="bk-stat-value bk-kpi-green">{{ list.length ? Math.round(counts.active/list.length*100) : 0 }}%</div></div><div class="bk-stat-icon" style="background:#dcfce7;color:#16a34a"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/></svg></div></div></div>
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">Weekly Bills</div><div class="bk-stat-value">{{ list.filter(r=>r.frequency==='Weekly').length }}</div></div><div class="bk-stat-icon" style="background:#dbeafe;color:#2563eb"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg></div></div></div>
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">Monthly Bills</div><div class="bk-stat-value">{{ list.filter(r=>r.frequency==='Monthly').length }}</div></div><div class="bk-stat-icon" style="background:#dbeafe;color:#2563eb"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg></div></div></div>
      <div class="bk-stat-card"><div class="bk-stat-content"><div><div class="bk-stat-label">Annual Bills</div><div class="bk-stat-value">{{ list.filter(r=>r.frequency==='Yearly').length }}</div></div><div class="bk-stat-icon" style="background:#e5e7eb;color:#6b7280"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg></div></div></div>
    </div>

    <!-- ============================================================ TABLE -->
    <div class="rec-card">
      <table class="rec-table">
        <thead>
          <tr>
            <th style="width:32px"><input type="checkbox" :checked="allSelected" @change="toggleAll" /></th>
            <th @click="sort('name')" class="sortable">Subscription # <span v-html="sortArrow('name')"></span></th>
            <th @click="sort('party')" class="sortable">Vendor <span v-html="sortArrow('party')"></span></th>
            <th @click="sort('reference_document')" class="sortable">Reference Bill <span v-html="sortArrow('reference_document')"></span></th>
            <th @click="sort('frequency')" class="sortable">Frequency <span v-html="sortArrow('frequency')"></span></th>
            <th @click="sort('next_schedule_date')" class="sortable">Next Billing Date <span v-html="sortArrow('next_schedule_date')"></span></th>
            <th>Status</th>
            <th style="width:120px;text-align:right">Actions</th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 6" :key="n"><td colspan="9"><div class="rec-shimmer"></div></td></tr>
          </template>
          <template v-else>
            <tr v-for="r in paged" :key="r.name" class="rec-row" :class="{selected:selected.includes(r.name)}" @click="openView(r)">
              <td @click.stop><input type="checkbox" :checked="selected.includes(r.name)" @change="toggleOne(r.name)" /></td>
              <td>
                <router-link :to="{ path: '/recurring-bills', query: { open: r.name } }" class="rec-num" @click.stop="openView(r)">{{ r.name }}</router-link>
                <div v-if="r.subscription_name" style="font-size:11.5px;color:#6b7280;margin-top:2px;font-weight:500">{{ r.subscription_name }}</div>
              </td>
              <td>
                <span v-if="r.party" style="font-size:13px;color:#111827;font-weight:500">{{ r.party }}</span>
                <span v-else class="text-muted">—</span>
              </td>
              <td><DocLink v-if="r.reference_document" doctype="Purchase Invoice" :name="r.reference_document" @click.stop /><span v-else class="rec-ref">—</span></td>
              <td>{{ r.frequency||'—' }}</td>
              <td class="mono-sm" :class="isDue(r)?'text-accent':''">{{ fmtDate(r.next_schedule_date)||'—' }}</td>
              <td><span class="rec-badge" :class="statusClass(r.ui_status||r.status)">{{ r.ui_status||r.status||'Active' }}</span></td>
              <td @click.stop style="text-align:right">
                <button class="rec-act-btn" @click="openView(r)" title="View"><span v-html="icon('eye',13)"></span></button>
                <button v-if="(r.ui_status||r.status||'Active')==='Active'" class="rec-act-btn" :disabled="!$canEdit('bills')" :title="!$canEdit('bills') ? 'Read-only access' : 'Pause'" @click="quickAction(r,'pause')"><span v-html="icon('pause',13)"></span></button>
                <button v-else-if="(r.ui_status||r.status||'Active')==='Paused'" class="rec-act-btn" :disabled="!$canEdit('bills')" :title="!$canEdit('bills') ? 'Read-only access' : 'Resume'" @click="quickAction(r,'resume')"><span v-html="icon('play',13)"></span></button>
                <button class="rec-act-btn rec-act-danger" :disabled="!$canDelete('bills')" :title="!$canDelete('bills') ? 'Not permitted' : 'Delete'" @click="quickAction(r,'delete')"><span v-html="icon('trash',13)"></span></button>
              </td>
            </tr>
            <tr v-if="!sorted.length">
              <td colspan="9" class="rec-empty">
                <div class="rec-empty-wrap">
                  <div class="rec-empty-icon" v-html="icon('repeat',32)"></div>
                  <div class="rec-empty-title">No recurring bills found</div>
                  <div class="rec-empty-sub">Create a recurring bill to auto-generate purchase orders on a schedule.</div>
                  <button class="rec-btn-primary" :disabled="!$canCreate('bills')" :title="!$canCreate('bills') ? 'Read-only access' : ''" @click="openNew" style="margin-top:12px">
                    <span v-html="icon('plus',13)"></span> Create your first recurring bill
                  </button>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- ── Pagination ── -->
    <div v-if="!loading && sorted.length" style="padding:12px 4px 4px">
      <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="sorted.length" />
    </div>

    <!-- ============================================================ CREATE DRAWER -->
    <div v-if="drawerOpen" class="rec-overlay" @click.self="drawerOpen=false"></div>
    <div class="rec-drawer" :class="{open:drawerOpen}">
      <div class="rec-dheader" :class="editMode?'edit':''">
        <div class="rec-dheader-left">
          <div class="rec-dheader-ico" :class="editMode?'edit':''">
            <span v-html="icon(editMode?'edit':'repeat',18)"></span>
          </div>
          <div>
            <div class="rec-dheader-title">{{ editMode ? 'Edit Recurring Bill' : 'New Recurring Bill' }}</div>
            <div class="rec-dheader-sub">{{ editMode ? form._name : 'Automatically generate vendor bills on a schedule' }}</div>
          </div>
        </div>
        <button class="rec-dclose" @click="onOverlayClose"><span v-html="icon('x',16)"></span></button>
      </div>

      <div class="rec-dbody">

        <!-- Subscription Info Card (edit mode) -->
        <div v-if="editMode" class="rb-info-card">
          <div class="rb-info-row">
            <div class="rb-info-item">
              <div class="rb-info-lbl">Reference #</div>
              <div class="rb-info-val rb-info-name">{{ form._name }}</div>
            </div>
            <div class="rb-info-item">
              <div class="rb-info-lbl">Status</div>
              <span class="rec-badge" :class="statusClass(form._status)">{{ form._status || 'Active' }}</span>
            </div>
          </div>
          <div class="rb-info-row">
            <div class="rb-info-item">
              <div class="rb-info-lbl">Vendor</div>
              <div class="rb-info-val">{{ form.vendor_name || form.vendor || '—' }}</div>
            </div>
            <div class="rb-info-item">
              <div class="rb-info-lbl">Next Billing Date</div>
              <div class="rb-info-val" :class="form.next_billing_date && form.next_billing_date <= new Date().toISOString().slice(0,10) ? 'text-accent' : ''">
                {{ fmtDate(form.next_billing_date) || '—' }}
              </div>
            </div>
          </div>
        </div>

        <!-- Section: Reference -->
        <div class="rec-section">
          <div class="rec-section-hdr">
            <span v-html="icon('folder',13)"></span>
            <span>Reference Document</span>
          </div>
          <div class="rec-fields-grid">
            <div class="rec-field" style="grid-column:1/-1">
              <label class="rec-label">Subscription Name <span class="rec-hint">(optional)</span></label>
              <input v-model="form.subscription_name" type="text" class="rec-input" placeholder="e.g. Office Rent, AWS Monthly…" maxlength="140" />
              <div class="rec-field-help">A friendly label to identify this recurring bill.</div>
            </div>
            <div class="rec-field" style="grid-column:1/-1">
              <label class="rec-label">Reference Bill <span class="req">*</span></label>
              <SearchableSelect v-model="form.reference_document" :options="refDocs" placeholder="Search a saved bill…" @search="fetchRefDocs" :disabled="editMode" />
              <div class="rec-field-help" v-if="!form.reference_document">
                Pick an existing bill to use as the template for this recurring schedule.
              </div>
            </div>
            <!-- Vendor (read-only, auto-filled from selected bill) -->
            <div v-if="form.vendor_name || form.vendor" class="rec-field" style="grid-column:1/-1">
              <label class="rec-label">Vendor</label>
              <div class="rb-readonly-field">
                <span v-html="icon('user',13)" style="color:#6b7280;flex-shrink:0"></span>
                <span>{{ form.vendor_name || form.vendor }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Section: Schedule -->
        <div class="rec-section">
          <div class="rec-section-hdr">
            <span v-html="icon('refresh',13)"></span>
            <span>Schedule</span>
          </div>
          <div class="rec-fields-grid">
            <div class="rec-field">
              <label class="rec-label">Frequency <span class="req">*</span></label>
              <select v-model="form.frequency" class="rec-select">
                <option value="Daily">Daily</option>
                <option value="Weekly">Weekly</option>
                <option value="Monthly">Monthly</option>
                <option value="Quarterly">Quarterly</option>
                <option value="Half-Yearly">Half-Yearly</option>
                <option value="Yearly">Yearly</option>
              </select>
            </div>
            <div class="rec-field">
              <label class="rec-label">Submit on Creation</label>
              <select v-model="form.submit_on_creation" class="rec-select">
                <option :value="1">Yes — auto-submit</option>
                <option :value="0">No — save as draft</option>
              </select>
            </div>
            <div class="rec-field">
              <label class="rec-label">Start Date <span class="req">*</span></label>
              <input v-model="form.start_date" type="date" class="rec-input" :disabled="editMode" />
            </div>
            <div class="rec-field">
              <label class="rec-label">End Date <span class="rec-hint">(optional)</span></label>
              <input v-model="form.end_date" type="date" class="rec-input" :min="form.start_date" />
            </div>
          </div>
        </div>

        <!-- Section: Notification -->
        <div class="rec-section">
          <div class="rec-section-hdr">
            <span v-html="icon('mail',13)"></span>
            <span>Notification</span>
            <label class="rec-toggle">
              <input type="checkbox" v-model="form._notify" />
              <span class="rec-toggle-slider"></span>
            </label>
          </div>
          <div v-if="!form._notify" class="rec-section-empty">
            Email notifications are off. Toggle to email someone every time a document is generated.
          </div>
          <div v-else class="rec-fields-grid">
            <div class="rec-field" style="grid-column:1/-1">
              <label class="rec-label">Recipients <span class="rec-hint">(comma separated)</span></label>
              <input v-model="form.recipients" type="text" class="rec-input" :class="{'field-error': recipientError}" placeholder="finance@company.com, owner@company.com" @blur="validateRecipients" @input="recipientError=''" />
              <div v-if="form.recipients.trim()" style="display:flex;flex-wrap:wrap;gap:4px;margin-top:6px">
                <span v-for="em in form.recipients.split(',').map(s=>s.trim()).filter(Boolean)" :key="em"
                  :style="{
                    display:'inline-flex', alignItems:'center', gap:'4px',
                    padding:'2px 8px', borderRadius:'999px', fontSize:'12px', fontWeight:'500',
                    background: /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em) ? '#dcfce7' : '#fee2e2',
                    color:    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em) ? '#15803d' : '#b91c1c',
                    border:  '1px solid ' + (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em) ? '#86efac' : '#fca5a5')
                  }">
                  <svg v-if="/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em)" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
                  <svg v-else width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                  {{ em }}
                </span>
              </div>
              <div v-if="recipientError" class="exp-field-hint exp-field-hint-err" style="margin-top:4px">⚠ Fix invalid email addresses above before saving</div>
            </div>
            <div class="rec-field" style="grid-column:1/-1">
              <label class="rec-label">Email Subject</label>
              <input v-model="form.subject" type="text" class="rec-input" :class="{'field-error': form.subject.length > 100}" maxlength="100" placeholder="Your recurring bill is ready" />
              <div class="exp-field-hint" :class="{'exp-field-hint-err': form.subject.length >= 100}" style="margin-top:4px;text-align:right">{{ form.subject.length }}/100</div>
            </div>
            <div class="rec-field" style="grid-column:1/-1">
              <label class="rec-label">Email Message</label>
              <textarea v-model="form.message" class="rec-input" rows="3" placeholder="Hello, please find your latest purchase order attached…"></textarea>
            </div>
          </div>
        </div>
      </div>

      <div class="rec-dfooter">
        <button class="rec-btn-ghost" @click="onOverlayClose" :disabled="drawerSaving">Cancel</button>
        <button class="rec-btn-primary" :disabled="drawerSaving || !(editMode ? $canEdit('bills') : $canCreate('bills'))" :title="!(editMode ? $canEdit('bills') : $canCreate('bills')) ? 'Read-only access' : ''" @click="saveRec">
          <span v-html="icon('check',13)"></span>
          {{ drawerSaving ? 'Saving…' : (editMode ? 'Save Changes' : 'Create Recurring Bill') }}
        </button>
      </div>
    </div>

    <!-- ============================================================ VIEW DRAWER -->
    <div v-if="viewOpen" class="rec-overlay" @click.self="viewOpen=false"></div>
    <div class="rec-drawer rec-view-drawer" :class="{open:viewOpen}">
      <template v-if="viewDoc">
        <div class="rec-view-head" :class="viewDoc.status==='Paused'?'paused':viewDoc.status==='Cancelled'?'completed':''">
          <div class="rec-view-head-row">
            <div>
              <div class="rec-view-num">{{ viewDoc.subscription_name || viewDoc.name }}</div>
              <div class="rec-view-sub">
                <span v-if="viewDoc.subscription_name" style="color:#9ca3af;font-size:11.5px">{{ viewDoc.name }} · </span>
                {{ viewDoc.party || viewDoc.vendor_name || 'Recurring Bill' }}
                <span v-if="viewDoc.frequency"> · {{ viewDoc.frequency }}</span>
              </div>
            </div>
            <div style="display:flex;align-items:center;gap:8px">
              <span class="rec-badge rec-badge-lg" :class="statusClass(viewDoc.ui_status||viewDoc.status)">{{ viewDoc.ui_status||viewDoc.status||'Active' }}</span>
              <button class="rec-dclose" @click="viewOpen=false"><span v-html="icon('x',16)"></span></button>
            </div>
          </div>
          <div class="rec-view-stats">
            <div>
              <div class="vh-lbl">Vendor</div>
              <div class="vh-val">{{ viewDoc.party || viewDoc.vendor_name || '—' }}</div>
            </div>
            <div>
              <div class="vh-lbl">Next Billing Date</div>
              <div class="vh-val" :class="isDue(viewDoc)?'text-accent':''">{{ fmtDate(viewDoc.next_schedule_date)||'—' }}</div>
            </div>
            <div>
              <div class="vh-lbl">Status</div>
              <div class="vh-val"><span class="rec-badge" :class="statusClass(viewDoc.ui_status||viewDoc.status)">{{ viewDoc.ui_status||viewDoc.status||'Active' }}</span></div>
            </div>
          </div>
        </div>

        <!-- action bar -->
        <div class="rec-view-actbar">
          <button class="rec-va-btn" @click="openEdit(viewDoc)" :disabled="(viewDoc.ui_status||viewDoc.status)==='Cancelled' || !$canEdit('bills')" :title="!$canEdit('bills') ? 'Read-only access' : ''"><span v-html="icon('edit',13)"></span> <div class="rec-va-btn-text">Edit</div></button>
          <button class="rec-va-btn" @click="runNow(viewDoc)" :disabled="(viewDoc.ui_status||viewDoc.status||'Active')!=='Active' || actionLoading || !$canEdit('bills')" :title="!$canEdit('bills') ? 'Read-only access' : ''"><span v-html="icon('play',13)"></span> <div class="rec-va-btn-text">Run Now</div></button>
          <button v-if="(viewDoc.ui_status||viewDoc.status||'Active')==='Active'" class="rec-va-btn" @click="actionOn(viewDoc,'pause')" :disabled="actionLoading || !$canEdit('bills')" :title="!$canEdit('bills') ? 'Read-only access' : ''"><span v-html="icon('pause',13)"></span> <div class="rec-va-btn-text">Pause</div></button>
          <button v-else-if="(viewDoc.ui_status||viewDoc.status)==='Paused'" class="rec-va-btn" @click="actionOn(viewDoc,'resume')" :disabled="actionLoading || !$canEdit('bills')" :title="!$canEdit('bills') ? 'Read-only access' : ''"><span v-html="icon('play',13)"></span> <div class="rec-va-btn-text">Resume</div></button>
          <button class="rec-va-btn rec-va-warn" @click="actionOn(viewDoc,'cancel')" :disabled="actionLoading || (viewDoc.ui_status||viewDoc.status)==='Cancelled' || !$canDelete('bills')" :title="!$canDelete('bills') ? 'Not permitted' : ''"><span v-html="icon('x',13)"></span> <div class="rec-va-btn-text">Cancel</div></button>
          <button class="rec-va-btn rec-va-danger" @click="actionOn(viewDoc,'delete')" :disabled="actionLoading || !$canDelete('bills')" :title="!$canDelete('bills') ? 'Not permitted' : ''"><span v-html="icon('trash',13)"></span> <div class="rec-va-btn-text">Delete</div></button>
        </div>

        <!-- timeline -->
        <div class="rec-timeline">
          <div class="rec-tl-step" :class="{done:true}">
            <div class="rec-tl-dot"></div>
            <div class="rec-tl-lbl">Created<br/><span class="rec-tl-sub">{{ fmtDate(viewDoc.creation) }}</span></div>
          </div>
          <div class="rec-tl-line" :class="{done:(viewDoc.ui_status||viewDoc.status)!=='Paused'}"></div>
          <div class="rec-tl-step" :class="{done:(viewDoc.ui_status||viewDoc.status||'Active')==='Active' || viewDoc.runs_count>0, current:(viewDoc.ui_status||viewDoc.status||'Active')==='Active'}">
            <div class="rec-tl-dot"></div>
            <div class="rec-tl-lbl">{{ (viewDoc.ui_status||viewDoc.status)==='Paused'?'Paused':'Active' }}<br/><span class="rec-tl-sub">{{ fmtDate(viewDoc.start_date) }}</span></div>
          </div>
          <div class="rec-tl-line" :class="{done:viewDoc.runs_count>0}"></div>
          <div class="rec-tl-step" :class="{done:viewDoc.runs_count>0}">
            <div class="rec-tl-dot"></div>
            <div class="rec-tl-lbl">Last Run<br/><span class="rec-tl-sub">{{ viewDoc.runs&&viewDoc.runs.length?fmtDate(viewDoc.runs[0].creation):'—' }}</span></div>
          </div>
          <div class="rec-tl-line" :class="{done:(viewDoc.ui_status||viewDoc.status)==='Cancelled'}"></div>
          <div class="rec-tl-step" :class="{done:(viewDoc.ui_status||viewDoc.status)==='Cancelled' || (viewDoc.ui_status||viewDoc.status)==='Completed'}">
            <div class="rec-tl-dot"></div>
            <div class="rec-tl-lbl">{{ viewDoc.end_date?'Ends':'Open-ended' }}<br/><span class="rec-tl-sub">{{ fmtDate(viewDoc.end_date)||'No end' }}</span></div>
          </div>
        </div>

        <!-- tabs -->
        <div class="rec-view-tabs">
          <button v-for="t in viewTabs" :key="t.key" class="rec-vt-btn" :class="{active:viewTab===t.key}" @click="viewTab=t.key">
            {{ t.label }}<span v-if="t.count!=null" class="rec-vt-count">{{ t.count }}</span>
          </button>
        </div>

        <div class="rec-dbody">
          <!-- Details tab -->
          <div v-if="viewTab==='details'">
            <div class="rec-section">
              <div class="rec-section-hdr"><span v-html="icon('folder',13)"></span><span>Details</span></div>
              <div class="rec-meta-grid">
                <div><div class="rec-meta-lbl">Reference #</div><div class="mono-sm" style="font-weight:600">{{ viewDoc.name }}</div></div>
                <div><div class="rec-meta-lbl">Status</div><span class="rec-badge" :class="statusClass(viewDoc.ui_status||viewDoc.status)">{{ viewDoc.ui_status||viewDoc.status||'Active' }}</span></div>
                <div style="grid-column:1/-1" v-if="viewDoc.subscription_name"><div class="rec-meta-lbl">Subscription Name</div><div style="font-size:14px;font-weight:700;color:#1d4ed8">{{ viewDoc.subscription_name }}</div></div>
                <div><div class="rec-meta-lbl">Vendor</div><div style="font-weight:500;color:#111827">{{ viewDoc.party || viewDoc.vendor_name || '—' }}</div></div>
                <div><div class="rec-meta-lbl">Next Billing Date</div><div class="mono-sm" :class="isDue(viewDoc)?'text-accent':''">{{ fmtDate(viewDoc.next_schedule_date)||'—' }}</div></div>
                <div><div class="rec-meta-lbl">Reference Bill</div><div class="mono-sm">{{ viewDoc.reference_document||'—' }}</div></div>
                <div><div class="rec-meta-lbl">Frequency</div><div>{{ viewDoc.frequency }}</div></div>
                <div><div class="rec-meta-lbl">Start Date</div><div class="mono-sm">{{ fmtDate(viewDoc.start_date) }}</div></div>
                <div><div class="rec-meta-lbl">End Date</div><div class="mono-sm">{{ fmtDate(viewDoc.end_date)||'No end' }}</div></div>
                <div><div class="rec-meta-lbl">Submit on Creation</div><div>{{ viewDoc.submit_on_creation?'Yes':'No (Draft)' }}</div></div>
              </div>
            </div>
            <div v-if="viewDoc.recipients" class="rec-section" style="margin-top:12px">
              <div class="rec-section-hdr"><span v-html="icon('mail',13)"></span><span>Notification</span></div>
              <div style="display:flex;flex-direction:column;gap:10px;margin-top:8px">
                <div>
                  <div class="rec-meta-lbl">Recipients</div>
                  <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:4px">
                    <span v-for="em in viewDoc.recipients.split(',').map(s=>s.trim()).filter(Boolean)" :key="em"
                      style="display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:500;background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe">{{ em }}</span>
                  </div>
                </div>
                <div v-if="viewDoc.subject">
                  <div class="rec-meta-lbl">Subject</div>
                  <div style="font-size:13px;font-weight:500;color:#111827;margin-top:2px;white-space: pre-wrap;word-break: break-word;">{{ viewDoc.subject }}</div>
                </div>
                <div v-if="viewDoc.message">
                  <div class="rec-meta-lbl">Message</div>
                  <div style="font-size:13px;color:#374151;line-height:1.6;white-space:pre-wrap;word-break:break-word;overflow-wrap:anywhere;background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;padding:10px 12px;margin-top:4px;max-height:120px;overflow-y:auto">{{ viewDoc.message }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Generated tab -->
          <div v-else-if="viewTab==='generated'">
            <div v-if="!viewDoc.runs||!viewDoc.runs.length" class="rec-tab-empty">No documents generated yet.</div>
            <template v-else>
              <!-- Desktop table -->
              <table class="rec-table rec-table-inner rec-gen-table-desktop">
                <thead><tr><th>Document</th><th>Created</th><th>Status</th></tr></thead>
                <tbody>
                  <tr v-for="d in viewDoc.runs" :key="d.name">
                    <td><DocLink doctype="Purchase Invoice" :name="d.name" /></td>
                    <td class="text-muted mono-sm">{{ fmtDate(d.creation) }}</td>
                    <td><span class="rec-badge" :class="d.docstatus===1?'badge-green':d.docstatus===2?'badge-red':'badge-grey'">{{ d.docstatus===1?'Submitted':d.docstatus===2?'Cancelled':'Draft' }}</span></td>
                  </tr>
                </tbody>
              </table>
              <!-- Mobile cards -->
              <div class="rec-gen-cards-mobile">
                <div v-for="d in viewDoc.runs" :key="d.name" class="rec-gen-card">
                  <div class="rec-gen-card-top">
                    <span class="rec-num">{{ d.name }}</span>
                    <span class="rec-badge" :class="d.docstatus===1?'badge-green':d.docstatus===2?'badge-red':'badge-grey'">{{ d.docstatus===1?'Submitted':d.docstatus===2?'Cancelled':'Draft' }}</span>
                  </div>
                  <div class="rec-gen-card-bot">
                    <span class="rec-gen-card-date">{{ fmtDate(d.creation) }}</span>
                  </div>
                </div>
              </div>
            </template>
          </div>

          <!-- Upcoming tab -->
          <div v-else-if="viewTab==='upcoming'">
            <div v-if="!viewDoc.upcoming||!viewDoc.upcoming.length" class="rec-tab-empty">No upcoming runs scheduled.</div>
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
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from "vue";
import { apiList, apiSave, apiLinkValues, apiGET, apiPOST } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { useConfirm } from "../composables/useConfirm.js";
import { icon } from "../utils/icons.js";
import { fmtDate } from "../utils/format.js";
import SearchableSelect from "../components/SearchableSelect.vue";
import SummaryStrip from "../components/SummaryStrip.vue";
import Pagination from "../components/Pagination.vue";
import { usePagination } from "../composables/usePagination.js";
import DocLink from "../components/DocLink.vue";
import { useRoute } from "vue-router";
import { useOpenFromQuery } from "../composables/useOpenFromQuery.js";

const { toast } = useToast();
const { confirm } = useConfirm();
const activeTab = ref("all");
const tabs = [
  { key: "all", label: "All" },
  { key: "Active", label: "Active" },
  { key: "Paused", label: "Paused" },
  { key: "Cancelled", label: "Cancelled" },
];
const list = ref([]), loading = ref(false), search = ref("");
const selected = ref([]);
const drawerOpen = ref(false), drawerSaving = ref(false), editMode = ref(false);
const recipientError = ref("");
const viewOpen = ref(false), viewDoc = ref(null), viewTab = ref("details");
const actionLoading = ref(false);
const refDocs = ref([]);
const sortCol = ref("next_schedule_date"), sortDir = ref("asc");
const form = reactive({
  _name: "",
  subscription_name: "",
  vendor: "",
  vendor_name: "",
  next_billing_date: "",
  _status: "",
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

async function load() {
  loading.value = true;
  try {
    const rows = await apiGET("zoho_books_clone.api.recurring.get_subscriptions", {
      reference_doctype: "Purchase Invoice", limit: 200,
    });
    list.value = Array.isArray(rows) ? rows : (rows?.message ?? []);
  } catch (e) {
    console.warn("Auto Repeat load failed:", e.message);
    list.value = [];
  } finally { loading.value = false; }
}

const today = new Date().toISOString().slice(0, 10);
function isDue(r) { return r.next_schedule_date && r.next_schedule_date <= today && (r.status||"Active") === "Active"; }
function statusClass(s) { if (s==="Cancelled") return "badge-grey"; if (s==="Paused") return "badge-orange"; return "badge-green"; }

const counts = computed(() => ({
  active:    list.value.filter(r => (r.ui_status||r.status||"Active") === "Active").length,
  paused:    list.value.filter(r => (r.ui_status||r.status) === "Paused").length,
  cancelled: list.value.filter(r => (r.ui_status||r.status) === "Cancelled").length,
}));

const filtered = computed(() => {
  let r = list.value;
  if (activeTab.value !== "all") r = r.filter(x => (x.ui_status||x.status||"Active") === activeTab.value);
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    r = r.filter(x =>
      (x.name||"").toLowerCase().includes(q) ||
      (x.subscription_name||"").toLowerCase().includes(q) ||
      (x.party||"").toLowerCase().includes(q) ||
      (x.reference_document||"").toLowerCase().includes(q)
    );
  }
  return r;
});

const sorted = computed(() => {
  const col = sortCol.value;
  return [...filtered.value].sort((a, b) => {
    const c = String(a[col]??"").localeCompare(String(b[col]??""));
    return sortDir.value === "asc" ? c : -c;
  });
});
const { page, pageSize, paged } = usePagination(sorted, { storageKey: "recurring-bills" });

function sort(col) { if (sortCol.value===col) sortDir.value=sortDir.value==="asc"?"desc":"asc"; else { sortCol.value=col; sortDir.value="asc"; } }
function sortArrow(col) { if (sortCol.value!==col) return '<span style="color:#d1d5db">⇅</span>'; return sortDir.value==="asc"?"↑":"↓"; }

const viewTabs = computed(() => [
  { key: "details", label: "Details" },
  { key: "generated", label: "Generated", count: viewDoc.value?.runs_count ?? 0 },
  { key: "upcoming", label: "Upcoming", count: viewDoc.value?.upcoming?.length ?? 0 },
]);
const allSelected = computed(() => sorted.value.length > 0 && sorted.value.every(r => selected.value.includes(r.name)));
function toggleAll() { selected.value = allSelected.value ? [] : sorted.value.map(r => r.name); }
function toggleOne(n) { selected.value = selected.value.includes(n) ? selected.value.filter(x => x !== n) : [...selected.value, n]; }

function openNew() {
  editMode.value = false;
  Object.assign(form, {
    _name: "", subscription_name: "", vendor: "", vendor_name: "",
    next_billing_date: "", _status: "",
    reference_document: "", frequency: "Monthly",
    start_date: new Date().toISOString().slice(0, 10),
    end_date: "", submit_on_creation: 1, _notify: false,
    recipients: "", subject: "", message: "",
  });
  refDocs.value = [];
  drawerOpen.value = true;
  fetchRefDocs();
}
async function openView(r) {
  if (!r?.name) return;
  viewOpen.value = true;
  viewTab.value = "details";
  viewDoc.value = { ...r, runs: r.runs || [], upcoming: r.upcoming || [], runs_count: r.runs_count || 0 };
  try {
    const detail = await apiGET("zoho_books_clone.api.recurring.get_subscription", { name: r.name });
    const d = (detail && typeof detail === "object") ? detail : {};
    viewDoc.value = {
      ...viewDoc.value, ...d,
      runs: Array.isArray(d.runs) ? d.runs : (viewDoc.value.runs || []),
      upcoming: Array.isArray(d.upcoming) ? d.upcoming : (viewDoc.value.upcoming || []),
      runs_count: d.runs_count != null ? d.runs_count : (Array.isArray(d.runs) ? d.runs.length : (viewDoc.value.runs_count || 0)),
    };
  } catch (e) { toast.error(e.message || "Failed to load detail"); }
}

async function openEdit(doc) {
  if (!doc?.name) return;
  editMode.value = true;
  viewOpen.value = false;
  // Populate from what we have immediately so drawer opens fast
  Object.assign(form, {
    _name: doc.name,
    subscription_name: doc.subscription_name || "",
    vendor: doc.vendor || doc.party || "",
    vendor_name: doc.vendor_name || doc.party || "",
    next_billing_date: doc.next_schedule_date || "",
    _status: doc.ui_status || doc.status || "Active",
    reference_document: doc.reference_document || "",
    frequency: doc.frequency || "Monthly",
    start_date: doc.start_date || "",
    end_date: doc.end_date || "",
    submit_on_creation: doc.submit_on_creation ? 1 : 0,
    _notify: !!(doc.recipients),
    recipients: doc.recipients || "",
    subject: doc.subject || "",
    message: doc.message || "",
  });
  refDocs.value = doc.reference_document ? [{ label: doc.reference_document, value: doc.reference_document }] : [];
  drawerOpen.value = true;
  // Fetch full detail to fill recipients/subject/message/submit_on_creation
  try {
    const detail = await apiGET("zoho_books_clone.api.recurring.get_subscription", { name: doc.name });
    const d = (detail && typeof detail === "object") ? detail : {};
    Object.assign(form, {
      subscription_name: d.subscription_name || form.subscription_name,
      vendor: d.vendor || d.party || form.vendor,
      vendor_name: d.vendor_name || d.party || form.vendor_name,
      next_billing_date: d.next_schedule_date || form.next_billing_date,
      _status: d.ui_status || d.status || form._status,
      frequency: d.frequency || form.frequency,
      end_date: d.end_date || "",
      submit_on_creation: d.submit_on_creation ? 1 : 0,
      _notify: !!(d.recipients || d.notify_by_email),
      recipients: d.recipients || "",
      subject: d.subject || "",
      message: d.message || "",
    });
  } catch { /* keep optimistic values */ }
}

function onOverlayClose() {
  if (drawerSaving.value) return;
  drawerOpen.value = false;
}

async function quickAction(r, action) {
  const messages = {
    pause:  { title: `Pause ${r.name}?`,  body: "It will stop generating documents until resumed.", okLabel: "Pause" },
    resume: { title: `Resume ${r.name}?`, body: "It will start generating documents on schedule.", okLabel: "Resume" },
    cancel: { title: `Cancel ${r.name}?`, body: "Subscription will be ended permanently.", okLabel: "Cancel Sub" },
    delete: { title: `Delete ${r.name}?`, body: "This cannot be undone.", okLabel: "Delete" },
  };
  if (!(await confirm(messages[action]))) return;
  await runLifecycle(r.name, action);
}

async function actionOn(doc, action) {
  if (!doc?.name) return;
  await quickAction(doc, action);
  if (action === "delete") { viewOpen.value = false; }
  else if (viewOpen.value) { await openView({ name: doc.name }); }
}

async function runLifecycle(name, action) {
  actionLoading.value = true;
  try {
    const res = await apiPOST(`zoho_books_clone.api.recurring.${action}_subscription`, { name });
    toast.success(res?.message?.message || res?.message || `${name} ${action}d`);
    await load();
  } catch (e) { toast.error(e.message || `Failed to ${action}`); }
  finally { actionLoading.value = false; }
}

async function runNow(doc) {
  if (!doc?.name) return;
  if (!(await confirm({ title: `Run ${doc.name} now?`, body: "A new document will be generated immediately, ignoring the schedule.", okLabel: "Run Now" }))) return;
  actionLoading.value = true;
  try {
    const res = await apiPOST("zoho_books_clone.api.recurring.run_subscription_now", { name: doc.name });
    const gen = res?.message?.generated || res?.generated;
    toast.success(gen ? `Generated ${gen}` : "Document generated");
    await load();
    await openView({ name: doc.name });
  } catch (e) { toast.error(e.message || "Failed to run subscription"); }
  finally { actionLoading.value = false; }
}

async function fetchRefDocs(q = "") {
  try {
    const r = await apiLinkValues("Purchase Invoice", q, [["docstatus","in",[0,1]],["is_return","=",0]]);
    refDocs.value = r.map(x => ({ label: x.name, value: x.name }));
  } catch { refDocs.value = []; }
}

watch(() => form.reference_document, async (v) => {
  if (!v) { form.vendor = ""; form.vendor_name = ""; return; }
  try {
    const r = await apiGET("frappe.client.get_value", {
      doctype: "Purchase Invoice",
      filters: JSON.stringify({ name: v }),
      fieldname: JSON.stringify(["supplier", "supplier_name"]),
    });
    const row = r?.message || {};
    form.vendor = row.supplier || "";
    form.vendor_name = row.supplier_name || row.supplier || "";
  } catch { form.vendor = ""; form.vendor_name = ""; }
});

function validateRecipients() {
  if (!form._notify || !form.recipients.trim()) { recipientError.value = ""; return true; }
  const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const bad = form.recipients.split(",").map(s => s.trim()).filter(s => s && !emailRe.test(s));
  if (bad.length) { recipientError.value = `Invalid email${bad.length > 1 ? "s" : ""}: ${bad.join(", ")}`; return false; }
  recipientError.value = ""; return true;
}

async function saveRec() {
  if (!form.reference_document) return toast.error("Reference bill is required");
  if (!form.start_date) return toast.error("Start date is required");
  if (form.end_date && form.end_date < form.start_date) return toast.error("End date must be after start date");
  if (!validateRecipients()) return;
  drawerSaving.value = true;
  try {
    if (editMode.value) {
      await apiPOST("zoho_books_clone.api.recurring.update_subscription", {
        name: form._name,
        subscription_name: form.subscription_name,
        frequency: form.frequency,
        end_date: form.end_date || "",
        submit_on_creation: form.submit_on_creation,
        notify_by_email: form._notify ? 1 : 0,
        recipients: form.recipients,
        subject: form.subject,
        message: form.message,
      });
      toast.success(`${form._name} updated`);
    } else {
      const saved = await apiPOST("zoho_books_clone.api.recurring.make_recurring_from_doc", {
        reference_doctype:  "Purchase Invoice",
        reference_document: form.reference_document,
        subscription_name:  form.subscription_name,
        frequency:          form.frequency,
        start_date:         form.start_date,
        end_date:           form.end_date || "",
        submit_on_creation: form.submit_on_creation,
        notify_by_email:    form._notify ? "1" : "",
        recipients:         form._notify ? (form.recipients || "") : "",
        subject:            form._notify ? (form.subject || "") : "",
        message:            form._notify ? (form.message || "") : "",
      });
      toast.success(`Recurring bill ${saved?.name || ""} created`);
    }
    drawerOpen.value = false;
    if (editMode.value && form._name) await openView({ name: form._name });
    await load();
  } catch (e) { toast.error(e.message || "Failed to save recurring bill"); }
  finally { drawerSaving.value = false; }
}

const route = useRoute();
onMounted(async () => {
  await load();
  useOpenFromQuery({
    route,
    openByName: (n) => openView(list.value?.find(r => r.name === n) || { name: n }),
  });
});
</script>

<style scoped>
/* ── Page & Toolbar ── */
.rec-page{display:flex;flex-direction:column;gap:16px;padding:24px;}
.rec-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
.rec-search-wrap{display:flex;align-items:center;gap:8px;background:#ffffff;border-radius:8px;padding:6px 12px;min-width:220px;border:1px solid #e5e7eb;}
.rec-search-input{border:none;background:transparent;outline:none;font:inherit;color:#111827;width:100%;font-size:13px;}
.rec-pills{display:flex;gap:6px;}
.rec-pill{padding:6px 14px;border-radius:20px;font-size:12.5px;font-weight:600;border:1px solid #e5e7eb;background:#fff;color:#6b7280;cursor:pointer;font-family:inherit;}
.rec-pill.active{background:#eff6ff;border-color:#2563eb;color:#2563eb;}
.rec-btn-primary{display:inline-flex;align-items:center;gap:6px;background:#2563eb;color:#fff;border:none;border-radius:8px;padding:8px 14px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;}
.rec-btn-primary:hover{background:#1d4ed8;}
.rec-btn-primary:disabled{opacity:.5;cursor:not-allowed;}
.rec-btn-ghost{display:inline-flex;align-items:center;gap:6px;background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;padding:8px 12px;font-size:13px;color:#374151;cursor:pointer;font-family:inherit;}
.rec-btn-ghost:hover{background:#f9fafb;}
.rec-btn-ghost:disabled{opacity:.5;cursor:not-allowed;}

/* ── Table ── */
.green{color:#16a34a!important;}.orange{color:#ea580c!important;}.red{color:#dc2626!important;}
.rec-card{background:#fff;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;}
.rec-table{width:100%;border-collapse:collapse;font-size:13px;}
.rec-table th{background:#f9fafb;border-bottom:1px solid #e5e7eb;padding:10px 12px;font-size:11.5px;font-weight:600;color:#374151;text-align:left;white-space:nowrap;text-transform:uppercase;}
.rec-table th.sortable{cursor:pointer;user-select:none;}.rec-table th.sortable:hover{color:#2563eb;}
.rec-row td{padding:10px 12px;border-bottom:1px solid #f3f4f6;vertical-align:middle;cursor:pointer;}
.rec-row:last-child td{border-bottom:none;}.rec-row:hover td{background:#f9fafb;}
.rec-num{font-size:13px;color:#2563eb;font-weight:600;}
.rec-ref{font-size:13px;color:#374151;}
.mono-sm{font-size:13px;}.text-muted{color:#6b7280;}.text-accent{color:#2563eb;font-weight:600;}
.rec-badge{display:inline-flex;align-items:center;padding:2px 8px;border-radius:10px;font-size:11.5px;font-weight:600;width: fit-content;}
.rec-badge-lg{padding:4px 10px;font-size:12.5px;}
.badge-green{background:#dcfce7;color:#16a34a;}.badge-orange{background:#fef3c7;color:#ea580c;}.badge-grey{background:#e5e7eb;color:#6b7280;}
.rec-act-btn{background:transparent;border:1px solid #e5e7eb;border-radius:6px;width:26px;height:26px;display:inline-flex;align-items:center;justify-content:center;cursor:pointer;color:#6b7280;}
.rec-act-btn:hover{background:#e5e7eb;color:#2563eb;}
.rec-empty{text-align:center;color:#9ca3af;padding:48px!important;cursor:default!important;}
.rec-empty-wrap{display:flex;flex-direction:column;align-items:center;gap:6px;color:#9ca3af;}
.rec-empty-icon{color:#cbd5e1;margin-bottom:6px;}
.rec-empty-title{font-size:15px;font-weight:600;color:#374151;}
.rec-empty-sub{font-size:12.5px;max-width:380px;text-align:center;}
.rec-shimmer{height:13px;background:linear-gradient(90deg,#f3f4f6 25%,#e5e7eb 50%,#f3f4f6 75%);border-radius:4px;animation:shimmer 1.2s infinite;background-size:200% 100%;}
@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}

/* ── Overlay & Drawer ── */
.rec-overlay{position:fixed;inset:0;background:rgba(15,23,42,.28);z-index:40;}
.rec-drawer{position:fixed;top:0;right:-560px;bottom:0;width:560px;background:#fff;border-left:1px solid #e5e7eb;box-shadow:-12px 0 32px rgba(15,23,42,.12);z-index:50;display:flex;flex-direction:column;transition:right .24s cubic-bezier(.32,.72,0,1);}
.rec-drawer.open{right:0;}
.rec-view-drawer{width:625px;right:-625px;}.rec-view-drawer.open{right:0;}

/* ── Drawer Header ── */
.rec-dheader{display:flex;align-items:flex-start;justify-content:space-between;padding:18px 20px;border-bottom:1px solid #e5e7eb;flex-shrink:0;background:linear-gradient(135deg,#eff6ff 0%,#dbeafe 100%);}
.rec-dheader-left{display:flex;align-items:flex-start;gap:12px;}
.rec-dheader-ico{width:38px;height:38px;border-radius:10px;background:#fff;border:1px solid rgba(37,99,235,.18);display:inline-flex;align-items:center;justify-content:center;color:#2563eb;box-shadow:0 1px 3px rgba(15,23,42,.06);flex-shrink:0;}
.rec-dheader-title{font-size:15px;font-weight:700;color:#111827;letter-spacing:-0.01em;}
.rec-dheader-sub{font-size:12px;color:#475569;margin-top:3px;font-weight:500;}
.rec-dclose{background:rgba(255,255,255,.6);border:none;cursor:pointer;color:#475569;display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border-radius:8px;transition:background .15s;}
.rec-dclose:hover{background:#fff;color:#111827;}

/* ── Drawer Body ── */
.rec-dbody{flex:1;overflow-y:auto;padding:18px 20px;display:flex;flex-direction:column;gap:18px;background:#f8fafc;}

/* ── Sections ── */
.rec-section{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:12px;box-shadow:0 1px 2px rgba(15,23,42,.03);}
.rec-section-hdr{display:flex;align-items:center;gap:8px;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:#0f172a;}
.rec-section-hdr svg{color:#2563eb;}
.rec-section-empty{font-size:12.5px;color:#6b7280;font-style:italic;line-height:1.5;}
.rec-field-help{font-size:11.5px;color:#9ca3af;margin-top:4px;}

/* ── Toggle ── */
.rec-toggle{position:relative;margin-left:auto;width:34px;height:18px;display:inline-block;cursor:pointer;}
.rec-toggle input{opacity:0;width:0;height:0;}
.rec-toggle-slider{position:absolute;inset:0;background:#cbd5e1;border-radius:18px;transition:background .18s;}
.rec-toggle-slider::before{content:"";position:absolute;width:14px;height:14px;left:2px;top:2px;background:#fff;border-radius:50%;transition:transform .18s;box-shadow:0 1px 3px rgba(0,0,0,.15);}
.rec-toggle input:checked + .rec-toggle-slider{background:#2563eb;}
.rec-toggle input:checked + .rec-toggle-slider::before{transform:translateX(16px);}

/* ── Fields ── */
.rec-fields-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
.rec-field{display:flex;flex-direction:column;gap:4px;}
.rec-label{font-size:12px;font-weight:600;color:#374151;}
.rec-hint{font-weight:400;color:#9ca3af;font-size:11px;}
.req{color:#dc2626;}
.rec-input,.rec-select{border:1px solid #e2e8f0;border-radius:8px;padding:8px 12px;font:inherit;font-size:13px;outline:none;background:#fff;color:#0f172a;transition:border-color .15s, box-shadow .15s;}
.rec-input:hover:not(:disabled),.rec-select:hover:not(:disabled){border-color:#cbd5e1;}
.rec-input:focus,.rec-select:focus{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.12);}
.rec-input:disabled,.rec-select:disabled{background:#f1f5f9;color:#94a3b8;cursor:not-allowed;border-color:#e2e8f0;}
textarea.rec-input{resize:vertical;min-height:72px;}

/* ── Drawer Footer ── */
.rec-dfooter{display:flex;align-items:center;justify-content:flex-end;gap:8px;padding:14px 20px;border-top:1px solid #e5e7eb;flex-shrink:0;background:#fff;}

/* ── Selected row ── */
.rec-row.selected td{background:#eff6ff;}
.rec-act-danger:hover{color:#dc2626;background:#fef2f2;border-color:#fecaca;}

/* ── Edit mode drawer header ── */
.rec-dheader.edit{background:linear-gradient(135deg,#fef3c7 0%,#fde68a 100%);}
.rec-dheader-ico.edit{color:#ca8a04;border-color:rgba(202,138,4,.25);}

/* ── View action bar ── */
.rec-view-actbar{display:flex;flex-wrap:wrap;gap:6px;padding:10px 20px;border-bottom:1px solid #e5e7eb;background:#fff;flex-shrink:0;}
.rec-va-btn{display:inline-flex;align-items:center;gap:5px;border:1px solid #e5e7eb;background:#fff;color:#374151;border-radius:7px;padding:6px 11px;font-size:12.5px;font-weight:600;cursor:pointer;font-family:inherit;}
.rec-va-btn:hover:not(:disabled){background:#f9fafb;border-color:#cbd5e1;}
.rec-va-btn:disabled{opacity:.45;cursor:not-allowed;}
.rec-va-warn{color:#ea580c;border-color:#fed7aa;}.rec-va-warn:hover:not(:disabled){background:#fff7ed;}
.rec-va-danger{color:#dc2626;border-color:#fecaca;}.rec-va-danger:hover:not(:disabled){background:#fef2f2;}

/* ── Timeline ── */
.rec-timeline{display:flex;align-items:center;padding:14px 20px;background:#fff;border-bottom:1px solid #e5e7eb;gap:0;flex-shrink:0;}
.rec-tl-step{display:flex;flex-direction:column;align-items:center;flex-shrink:0;min-width:80px;}
.rec-tl-dot{width:12px;height:12px;border-radius:50%;background:#e5e7eb;border:2px solid #fff;box-shadow:0 0 0 2px #e5e7eb;}
.rec-tl-step.done .rec-tl-dot{background:#16a34a;box-shadow:0 0 0 2px #16a34a;}
.rec-tl-step.current .rec-tl-dot{background:#2563eb;box-shadow:0 0 0 3px #bfdbfe;}
.rec-tl-lbl{font-size:11px;color:#6b7280;text-align:center;margin-top:6px;font-weight:600;line-height:1.3;}
.rec-tl-sub{font-weight:400;color:#9ca3af;font-size:10.5px;}
.rec-tl-line{flex:1;height:2px;background:#e5e7eb;min-width:20px;}
.rec-tl-line.done{background:#16a34a;}
.rec-tl-line.danger{background:#dc2626;}

/* ── View tabs ── */
.rec-view-tabs{display:flex;border-bottom:1px solid #e5e7eb;padding:0 12px;background:#fff;flex-shrink:0;}
.rec-vt-btn{background:transparent;border:none;padding:10px 14px;font-size:13px;font-weight:600;color:#6b7280;cursor:pointer;border-bottom:2px solid transparent;display:inline-flex;align-items:center;gap:6px;font-family:inherit;}
.rec-vt-btn.active{color:#2563eb;border-bottom-color:#2563eb;}
.rec-vt-count{background:#e5e7eb;color:#374151;padding:1px 7px;border-radius:10px;font-size:11px;font-weight:700;}
.rec-vt-btn.active .rec-vt-count{background:#dbeafe;color:#1d4ed8;}

/* ── Generated / Upcoming tabs ── */
.badge-red{background:#fee2e2;color:#dc2626;}
.rec-table-inner{font-size:12.5px;}
.rec-table-inner th{background:#fafafa;}
.rec-tab-empty{padding:24px;text-align:center;color:#9ca3af;font-size:13px;}
.rec-upcoming-list{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:8px;}
.rec-upcoming-list li{background:#f9fafb;border:1px solid #f3f4f6;border-radius:8px;padding:10px 14px;display:flex;align-items:center;gap:12px;font-size:13px;}
.rec-upcoming-idx{background:#dbeafe;color:#1d4ed8;font-weight:700;padding:2px 8px;border-radius:8px;font-size:11.5px;}

/* ── View Drawer Header ── */
.rec-view-head{padding:20px;border-bottom:1px solid #e5e7eb;flex-shrink:0;background:linear-gradient(135deg,#eff6ff 0%,#dbeafe 100%);}
.rec-view-head.paused{background:linear-gradient(135deg,#fff7ed 0%,#fed7aa 100%);}
.rec-view-head.completed{background:linear-gradient(135deg,#f3f4f6 0%,#e5e7eb 100%);}
.rec-view-head-row{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;}
.rec-view-num{font-size:18px;font-weight:700;color:#111827;}
.rec-view-sub{font-size:12.5px;color:#475569;margin-top:2px;}
.rec-view-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:16px;}
.rec-view-stats > div{background:rgba(255,255,255,.55);border-radius:8px;padding:8px 10px;}
.vh-lbl{font-size:10.5px;color:#475569;text-transform:uppercase;letter-spacing:.05em;font-weight:600;}
.vh-val{font-size:15px;font-weight:700;color:#0f172a;margin-top:2px;}
.rec-meta-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
.rec-meta-lbl{font-size:11px;color:#9ca3af;text-transform:uppercase;letter-spacing:.05em;margin-bottom:2px;font-weight:600;}

/* ── Subscription info card (edit form) ── */
.rb-info-card{background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;padding:14px 16px;margin-bottom:4px;display:flex;flex-direction:column;gap:10px;}
.rb-info-row{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
.rb-info-item{display:flex;flex-direction:column;gap:3px;}
.rb-info-lbl{font-size:11px;font-weight:700;color:#0369a1;text-transform:uppercase;letter-spacing:.04em;}
.rb-info-val{font-size:13px;color:#0f172a;font-weight:500;}
.rb-info-name{font-weight:700;color:#1d4ed8;font-size:14px;}
/* ── Vendor readonly field ── */
.rb-readonly-field{display:flex;align-items:center;gap:8px;background:#f9fafb;border:1px solid #e5e7eb;border-radius:7px;padding:8px 12px;font-size:13px;color:#374151;font-weight:500;}
.rec-list-actions{display:contents;}
/* ═══════════════════════════════════════════════════
   RESPONSIVE MEDIA QUERIES
   ═══════════════════════════════════════════════════ */

/* ── Tablet (≤ 768px) ── */
@media (max-width: 768px) {
  /* Drawers: full-screen */
  .rec-drawer      { width: 100% !important; right: -100% !important; max-width: 100%; }
  .rec-view-drawer { width: 100% !important; right: -100% !important; }
  /* .open must override right: -100% !important */
  .rec-drawer.open,
  .rec-view-drawer.open { right: 0 !important; }

  .rec-page    { padding: 12px; gap: 12px; }
  .rec-actions { flex-wrap: wrap; gap: 8px; }

  /* KPI / stat grids */
  .bk-kpi-grid  { grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .bk-stat-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }

  /* Table: hide Reference Bill + Frequency */
  .rec-table th:nth-child(4), .rec-table td:nth-child(4),
  .rec-table th:nth-child(5), .rec-table td:nth-child(5) { display: none; }

  /* View drawer header: allow wrap, single-row action group */
  .rec-view-head-row { flex-wrap: wrap; gap: 8px; }
  .rec-view-stats    { display:flex; }
}

/* ── Mobile (≤ 480px) ── */
@media (max-width: 480px) {
  .rec-page { padding: 8px; gap: 8px; }

  /* KPI grids: single column */
  .bk-kpi-grid  { grid-template-columns: 1fr; }
  .bk-stat-grid { grid-template-columns: 1fr; }

  /* Table: also hide Next Billing Date */
  .rec-table th:nth-child(6), .rec-table td:nth-child(6) { display: none; }

  /* View stats: single column */
  .rec-view-stats { grid-template-columns: 1fr; }
  .rec-meta-grid  { grid-template-columns: 1fr !important; }

  /* Form fields: single column */
  .rec-fields-grid { grid-template-columns: 1fr !important; }

  /* Inner generated table: scrollable */
  .rec-dbody .rec-card { overflow-x: auto !important; -webkit-overflow-scrolling: touch; }

  /* Action bar */
  .rec-view-actbar { gap: 5px; padding: 8px 12px; }
  .rec-va-btn      { padding: 5px 9px; font-size: 12px; }
}

/* ── Timeline: dots-only at ≤ 540px ── */
@media (max-width: 540px) {
  .rec-va-btn-text{display:none;}
  .rec-list-actions{display:block; width :stretch;}
  .rec-pills{justify-content: space-evenly;}
  .rec-search-wrap{ margin-bottom:5px;}
  .rec-timeline { display:none;padding: 10px 12px; gap: 0; }
  .rec-tl-lbl   { display: none !important; }
  .rec-tl-step  { min-width: 0; }
  .rec-tl-dot   { width: 14px; height: 14px; }
  .rec-tl-line  { min-width: 14px; }
}

/* ── Mobile card layout (≤ 425px) ── */
@media (max-width: 425px) {
  /* Strip the white box from the card container — cards become individual rows */
  .rec-card { background: transparent; border: none; border-radius: 0; box-shadow: none; overflow: visible; }

  /* Hide table header entirely */
  .rec-table thead { display: none !important; }

  /* Each row is a card */
  .rec-table tbody { display: flex !important; flex-direction: column; gap: 10px; }
  .rec-row {
    display: grid !important;
    grid-template-columns: 1fr auto !important;
    grid-template-rows: auto auto auto !important;
    gap: 4px 8px !important;
    background: #fff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px !important;
    padding: 14px !important;
    margin-bottom: 0 !important;
  }
  .rec-row:hover td { background: transparent !important; }

  /* All tds: block in grid */
  .rec-row td { display: block !important; padding: 0 !important; border: none !important; background: transparent !important; }

  /* Hide: checkbox, Reference Bill, Frequency, Next Billing Date */
  .rec-row td:nth-child(1),
  .rec-row td:nth-child(4),
  .rec-row td:nth-child(5),
  .rec-row td:nth-child(6) { display: none !important; }

  /* td 2: Subscription # — row 1 col 1 */
  .rec-row td:nth-child(2) { grid-row: 1; grid-column: 1; }
  .rec-num { font-size: 13px !important; font-weight: 700 !important; color: #2563eb !important; }

  /* td 3: Vendor — row 2 col 1 */
  .rec-row td:nth-child(3) { grid-row: 2; grid-column: 1; font-size: 15px !important; font-weight: 700 !important; color: #1a1a2e !important; }

  /* td 7: Status — row 3 col 1 */
  .rec-row td:nth-child(7) { grid-row: 3; grid-column: 1; }

  /* td 8: Actions — spans all rows on right */
  .rec-row td:nth-child(8) {
    grid-row: 1 / 4 !important;
    grid-column: 2 !important;
    display: flex !important;
    flex-direction: column;
    align-items: flex-end;
    gap: 8px;
    text-align: right;
    justify-content: flex-start;
  }
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
    padding-top: 6px;
    border-top: 1px solid #f3f4f6;
  }
  .rec-gen-card-date {
    font-size: 12px;
    color: #6b7280;
  }
}
</style>