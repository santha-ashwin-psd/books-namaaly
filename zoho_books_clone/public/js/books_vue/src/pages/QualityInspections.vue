<template>
  <div class="qc-page">

    <!-- ── Header KPI strip ── -->
    <div class="qc-kpi-strip">
      <div class="qc-kpi" :class="{active: filterStatus==='all'}" @click="filterStatus='all'">
        <div class="qc-kpi-ico" style="background:#eff6ff;color:#2563eb">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 12h6M9 16h4"/></svg>
        </div>
        <div><div class="qc-kpi-lbl">Total</div><div class="qc-kpi-val">{{ stats.total }}</div></div>
      </div>
      <div class="qc-kpi" :class="{active: filterStatus==='Pass'}" @click="filterStatus='Pass'">
        <div class="qc-kpi-ico" style="background:#f0fdf4;color:#16a34a">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
        </div>
        <div><div class="qc-kpi-lbl">Passed</div><div class="qc-kpi-val" style="color:#16a34a">{{ stats.passed }}</div></div>
      </div>
      <div class="qc-kpi" :class="{active: filterStatus==='Fail'}" @click="filterStatus='Fail'">
        <div class="qc-kpi-ico" style="background:#fef2f2;color:#dc2626">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
        </div>
        <div><div class="qc-kpi-lbl">Failed</div><div class="qc-kpi-val" style="color:#dc2626">{{ stats.failed }}</div></div>
      </div>
      <div class="qc-kpi" :class="{active: filterStatus==='Pending'}" @click="filterStatus='Pending'">
        <div class="qc-kpi-ico" style="background:#fffbeb;color:#d97706">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        </div>
        <div><div class="qc-kpi-lbl">Pending</div><div class="qc-kpi-val" style="color:#d97706">{{ stats.pending }}</div></div>
      </div>
      <div class="qc-kpi">
        <div class="qc-kpi-ico" style="background:#faf5ff;color:#7c3aed">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        </div>
        <div><div class="qc-kpi-lbl">Pass Rate</div><div class="qc-kpi-val" style="color:#7c3aed">{{ passRate }}%</div></div>
      </div>
    </div>

    <!-- ── Tabs ── -->
    <div class="qc-tab-row">
      <button v-for="t in typeTabs" :key="t.key" class="qc-tab" :class="{active: activeType===t.key}" @click="activeType=t.key">
        <span class="qc-tab-dot" :style="'background:'+t.color"></span>
        {{ t.label }}
        <span class="qc-tab-cnt">{{ t.cnt }}</span>
      </button>
      <div style="flex:1"></div>
      <!-- Action buttons -->
      <button class="qc-btn-ghost" @click="load"><span v-html="icon('refresh',14)"></span></button>
      <button class="qc-btn-ghost" @click="exportCSV" :disabled="!sorted.length"><span v-html="icon('download',14)"></span> Export</button>
      <button class="qc-btn-primary" @click="openNew"><span v-html="icon('plus',13)"></span> New Inspection</button>
    </div>

    <!-- ── Filter bar ── -->
    <div class="qc-filter-bar">
      <div class="qc-search-wrap">
        <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
        <input v-model="search" placeholder="Search inspection #, item, reference…" class="qc-search-input" />
      </div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <select v-model="filterRefType" class="qc-select">
          <option value="">All Doc Types</option>
          <option v-for="rt in refTypes" :key="rt" :value="rt">{{ rt }}</option>
        </select>
        <input type="date" v-model="dateFrom" class="qc-date"/>
        <span style="font-size:12px;color:#6b7280">to</span>
        <input type="date" v-model="dateTo" class="qc-date"/>
      </div>
    </div>

    <!-- ── Desktop Table ── -->
    <div class="qc-card qc-table-wrap">
      <table class="qc-table">
        <thead><tr>
          <th @click="sort('name')" class="sortable">Inspection # <span v-html="sortArrow('name')"></span></th>
          <th @click="sort('inspection_type')" class="sortable">Type <span v-html="sortArrow('inspection_type')"></span></th>
          <th>Reference</th>
          <th @click="sort('item')" class="sortable">Item <span v-html="sortArrow('item')"></span></th>
          <th @click="sort('inspection_date')" class="sortable">Date <span v-html="sortArrow('inspection_date')"></span></th>
          <th>Inspected By</th>
          <th class="ta-r">Readings</th>
          <th @click="sort('status')" class="sortable">Status <span v-html="sortArrow('status')"></span></th>
          <th style="width:44px"></th>
        </tr></thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 8" :key="n"><td colspan="9"><div class="qc-shimmer"></div></td></tr>
          </template>
          <template v-else>
            <tr v-for="r in paginated" :key="r.name" class="qc-row" @click="openView(r)">
              <td><span class="qc-num">{{ r.name }}</span></td>
              <td><span class="qc-type-badge" :style="typeStyle(r.inspection_type)">{{ r.inspection_type }}</span></td>
              <td>
                <div style="display:flex;flex-direction:column;gap:2px">
                  <span style="font-size:11px;color:#9ca3af">{{ r.reference_type }}</span>
                  <span style="font-size:12.5px;font-weight:600;color:#2563eb">{{ r.reference_name || '—' }}</span>
                </div>
              </td>
              <td>
                <div style="font-size:12.5px;font-weight:600">{{ r.item }}</div>
                <div v-if="r.item_name && r.item_name !== r.item" style="font-size:11px;color:#9ca3af">{{ r.item_name }}</div>
              </td>
              <td class="mono-sm text-muted">{{ fmtDate(r.inspection_date) }}</td>
              <td style="font-size:12px;color:#6b7280">{{ shortUser(r.inspected_by) }}</td>
              <td class="ta-r">
                <span v-if="r.total_readings">
                  <span style="color:#16a34a;font-weight:700">{{ r.accepted_readings }}</span>
                  <span style="color:#9ca3af">/</span>
                  <span style="color:#dc2626">{{ r.rejected_readings }}</span>
                  <span style="color:#9ca3af;font-size:11px"> of {{ r.total_readings }}</span>
                </span>
                <span v-else style="color:#9ca3af">—</span>
              </td>
              <td>
                <span class="qc-status-badge" :class="statusClass(r)">{{ r.status }}</span>
              </td>
              <td @click.stop style="white-space:nowrap">
                <button class="qc-act-btn" @click="openEdit(r)" title="Edit" style="margin-right:2px">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                </button>
                <button class="qc-act-btn" @click="openView(r)" title="View">
                  <span v-html="icon('eye',13)"></span>
                </button>
              </td>
            </tr>
            <tr v-if="!sorted.length">
              <td colspan="9" class="qc-empty">
                <div style="font-size:32px;margin-bottom:8px">🔬</div>
                <div style="font-weight:600;margin-bottom:4px">No QC Inspections found</div>
                <div style="font-size:13px;color:#9ca3af;margin-bottom:12px">Create an inspection from a Purchase Receipt, Invoice, or Delivery Note</div>
                <button class="qc-btn-primary" @click="openNew"><span v-html="icon('plus',13)"></span> New Inspection</button>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- ── Mobile Card List (≤425px) ── -->
    <div class="qc-mobile-list">
      <!-- shimmer -->
      <template v-if="loading">
        <div v-for="n in 5" :key="n" class="qc-mobile-shimmer"></div>
      </template>
      <!-- empty -->
      <div v-else-if="!sorted.length" class="qc-mobile-empty">
        <div style="font-size:30px;margin-bottom:8px">🔬</div>
        <div style="font-weight:600;margin-bottom:4px;font-size:14px">No QC Inspections found</div>
        <div style="font-size:12px;color:#9ca3af;margin-bottom:12px">Create an inspection from a Purchase Receipt, Invoice, or Delivery Note</div>
        <button class="qc-btn-primary" @click="openNew"><span v-html="icon('plus',13)"></span> New Inspection</button>
      </div>
      <!-- cards -->
      <div v-else v-for="r in paginated" :key="r.name" class="qc-mob-card" :style="'border-left-color:'+typeAccent(r.inspection_type)" @click="openView(r)">
        <!-- card top row -->
        <div class="qc-mob-top">
          <span class="qc-num" style="font-size:11px">{{ r.name }}</span>
          <span class="qc-status-badge" :class="statusClass(r)">{{ r.status }}</span>
        </div>
        <!-- type + date row -->
        <div class="qc-mob-row2">
          <span class="qc-type-badge" :style="typeStyle(r.inspection_type)">{{ r.inspection_type }}</span>
          <span class="qc-mob-date">{{ fmtDate(r.inspection_date) }}</span>
        </div>
        <!-- item -->
        <div class="qc-mob-item">
          <span class="qc-mob-lbl">Item</span>
          <span class="qc-mob-val">{{ r.item }}<span v-if="r.item_name && r.item_name !== r.item" class="qc-mob-sub"> · {{ r.item_name }}</span></span>
        </div>
        <!-- reference -->
        <div class="qc-mob-item">
          <span class="qc-mob-lbl">Reference</span>
          <span class="qc-mob-val" style="color:#2563eb">{{ r.reference_name || '—' }}<span class="qc-mob-sub"> ({{ r.reference_type }})</span></span>
        </div>
        <!-- readings + inspector -->
        <div class="qc-mob-footer">
          <span v-if="r.total_readings" class="qc-mob-readings">
            <span style="color:#16a34a;font-weight:700">{{ r.accepted_readings }}</span><span style="color:#9ca3af">/</span><span style="color:#dc2626">{{ r.rejected_readings }}</span>
            <span style="color:#9ca3af;font-size:10px"> of {{ r.total_readings }}</span>
          </span>
          <span v-else class="qc-mob-readings" style="color:#9ca3af">No readings</span>
          <span class="qc-mob-inspector">{{ shortUser(r.inspected_by) }}</span>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="sorted.length > pageSize" style="display:flex;justify-content:space-between;align-items:center;font-size:12px;color:#6b7280;padding:4px 2px">
      <span>Showing {{ paginated.length }} of {{ sorted.length }}</span>
      <div style="display:flex;gap:4px">
        <button class="qc-pg-btn" :disabled="page===1" @click="page--">‹</button>
        <span style="padding:4px 8px;font-weight:600">{{ page }} / {{ totalPages }}</span>
        <button class="qc-pg-btn" :disabled="page===totalPages" @click="page++">›</button>
      </div>
    </div>

    <!-- ── Create Drawer ── -->
    <div v-if="drawerOpen" class="qc-overlay" @click.self="drawerOpen=false"></div>
    <div class="qc-drawer" :class="{open:drawerOpen}">
      <div class="qc-dheader">
        <button class="qc-dclose" @click="drawerOpen=false"><span v-html="icon('x',16)"></span></button>
        <div class="qc-dh-top">
          <div class="qc-dh-ico"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 12h6M9 16h4"/></svg></div>
          <div>
            <div class="qc-dh-title">New QC Inspection</div>
            <div class="qc-dh-sub">Record quality check for an item</div>
          </div>
        </div>
      </div>
      <div class="qc-dbody">
        <div class="qc-fields-grid">
          <div class="qc-field">
            <label class="qc-label">Inspection Type <span class="req">*</span></label>
            <select v-model="form.inspection_type" class="qc-select-full">
              <option value="Incoming">Incoming — Purchasing goods</option>
              <option value="Outgoing">Outgoing — Dispatching goods</option>
              <option value="In Process">In Process — Manufacturing</option>
            </select>
          </div>
          <div class="qc-field">
            <label class="qc-label">Reference Doc Type <span class="req">*</span></label>
            <select v-model="form.reference_type" class="qc-select-full">
              <option value="">Select…</option>
              <option v-for="rt in refTypeOptions" :key="rt" :value="rt">{{ rt }}</option>
            </select>
            <span v-if="form.reference_type" style="font-size:11px;color:#6b7280;margin-top:2px">
              Documents from <strong>{{ form.reference_type }}</strong> will be listed
            </span>
          </div>
          <div class="qc-field">
            <label class="qc-label">Reference Document <span class="req">*</span></label>
            <SearchableSelect
              v-model="form.reference_name"
              :options="refDocs"
              :placeholder="form.reference_type ? (refDocsLoading ? 'Loading…' : 'Search ' + form.reference_type + '…') : 'Select a Doc Type first…'"
              :disabled="!form.reference_type"
              value-key="value"
              label-key="label"
            />
          </div>
          <div class="qc-field">
            <label class="qc-label">Item <span class="req">*</span></label>
            <SearchableSelect
              v-model="form.item"
              :options="items"
              :placeholder="!form.reference_name ? 'Select a Reference Document first…' : (itemsLoading ? 'Loading…' : 'Search item code…')"
              :disabled="!form.reference_name"
              value-key="value"
              label-key="label"
            />
          </div>
          <div class="qc-field">
            <label class="qc-label">Sample Size</label>
            <input v-model.number="form.sample_size" type="number" min="0" step="0.001" class="qc-input" />
          </div>
          <div class="qc-field">
            <label class="qc-label">Inspection Date <span class="req">*</span></label>
            <input v-model="form.inspection_date" type="date" class="qc-input" />
          </div>
          <div class="qc-field" style="grid-column:1/-1">
            <label class="qc-label">Remarks</label>
            <textarea v-model="form.remarks" rows="2" class="qc-input" placeholder="Optional observations…"></textarea>
          </div>
        </div>
      </div>
      <div class="qc-dfooter">
        <button class="qc-btn-ghost" @click="drawerOpen=false">Cancel</button>
        <button class="qc-btn-primary" :disabled="drawerSaving" @click="saveInspection">
          <span v-html="icon('plus',13)"></span>{{ drawerSaving ? 'Creating…' : 'Create Inspection' }}
        </button>
      </div>
    </div>

    <!-- ── View Drawer ── -->
    <div v-if="viewOpen" class="qc-overlay" @click.self="viewOpen=false"></div>
    <div class="qc-drawer qc-view-drawer" :class="{open:viewOpen}">
      <template v-if="viewDoc">
        <div class="qc-dheader" :style="'background:'+typeGrad(viewDoc.inspection_type)">
          <button class="qc-dclose" style="color:#fff;background:rgba(255,255,255,.15)" @click="viewOpen=false"><span v-html="icon('x',16)"></span></button>
          <div class="qc-dh-top">
            <div class="qc-dh-ico" style="background:rgba(255,255,255,.2)">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/></svg>
            </div>
            <div>
              <div class="qc-dh-title" style="color:#fff">{{ viewDoc.name }}</div>
              <div class="qc-dh-sub" style="color:rgba(255,255,255,.8)">{{ viewDoc.inspection_type }} · {{ fmtDate(viewDoc.inspection_date) }}</div>
            </div>
            <span class="qc-status-badge" :class="statusClass(viewDoc)" style="margin-left:auto;flex-shrink:0">{{ viewDoc.status }}</span>
          </div>
        </div>
        <div class="qc-dbody">

          <!-- Summary bar -->
          <div class="qc-summary-bar">
            <div class="qc-sumbar-item">
              <span class="qc-sumbar-lbl">Reference</span>
              <span class="qc-sumbar-val" style="color:#2563eb">{{ viewDoc.reference_type }} / {{ viewDoc.reference_name }}</span>
            </div>
            <div class="qc-sumbar-item" v-if="viewDoc.work_order">
              <span class="qc-sumbar-lbl">Work Order</span>
              <span class="qc-sumbar-val" style="color:#2563eb;cursor:pointer" @click="router.push('/manufacturing/work-order/' + viewDoc.work_order)">{{ viewDoc.work_order }}</span>
            </div>
            <div class="qc-sumbar-item">
              <span class="qc-sumbar-lbl">Item</span>
              <span class="qc-sumbar-val">{{ viewDoc.item }}</span>
            </div>
            <div class="qc-sumbar-item">
              <span class="qc-sumbar-lbl">Inspected By</span>
              <span class="qc-sumbar-val">{{ shortUser(viewDoc.inspected_by) }}</span>
            </div>
            <div class="qc-sumbar-item">
              <span class="qc-sumbar-lbl">Sample Size</span>
              <span class="qc-sumbar-val">{{ viewDoc.sample_size || '—' }}</span>
            </div>
          </div>

          <!-- Pass/Fail progress -->
          <div v-if="viewDoc.total_readings" class="qc-progress-section">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px">
              <span style="font-size:12px;font-weight:600;color:#374151">Reading Results</span>
              <span style="font-size:12px;color:#6b7280">{{ viewDoc.accepted_readings }}/{{ viewDoc.total_readings }} Accepted</span>
            </div>
            <div class="qc-progress-bar">
              <div class="qc-progress-fill" :style="'width:'+Math.round((viewDoc.accepted_readings/viewDoc.total_readings)*100)+'%;background:'+(viewDoc.status==='Pass'?'#16a34a':'#dc2626')"></div>
            </div>
          </div>

          <!-- Readings table -->
          <div class="qc-view-section" v-if="viewLoading">
            <div v-for="n in 4" :key="n" class="qc-shimmer" style="height:36px;margin-bottom:6px;border-radius:6px"></div>
          </div>
          <div class="qc-view-section" v-else-if="(viewDoc.readings||[]).length">
            <div class="qc-view-sec-lbl">Readings ({{ viewDoc.readings.length }})</div>
            <table class="qc-readings-tbl">
              <thead><tr>
                <th>Parameter</th>
                <th>Type</th>
                <th>Expected</th>
                <th>Reading Value</th>
                <th>Result</th>
              </tr></thead>
              <tbody>
                <tr v-for="rd in viewDoc.readings" :key="rd.name||rd.idx" :class="'qc-reading-row-'+rd.status?.toLowerCase()">
                  <td style="font-weight:600;font-size:12.5px">{{ rd.template_parameter }}</td>
                  <td><span class="qc-type-mini" :style="paramTypeStyle(rd.parameter_type)">{{ rd.parameter_type }}</span></td>
                  <td style="font-size:12px;color:#6b7280">
                    <template v-if="rd.parameter_type==='Numeric'">{{ rd.min_value }} – {{ rd.max_value }}</template>
                    <template v-else-if="rd.parameter_type==='Non-Numeric'">{{ rd.acceptance_criteria_value }}</template>
                    <template v-else>Formula</template>
                  </td>
                  <td>
                    <input v-if="viewDoc.docstatus===0" v-model="rd.reading_value" class="qc-rd-input" :placeholder="'Enter value…'" @change="markDirty" />
                    <span v-else style="font-size:12.5px;font-weight:600">{{ rd.reading_value || '—' }}</span>
                  </td>
                  <td>
                    <span class="qc-rd-badge" :class="'qc-rd-'+rd.status?.toLowerCase()">{{ rd.status || 'Pending' }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-if="viewDoc.docstatus===0 && isDirty" style="margin-top:8px;display:flex;justify-content:flex-end">
              <button class="qc-btn-save" :disabled="saving" @click="saveReadings">
                <span v-html="icon('save',13)"></span>{{ saving?'Saving…':'Save Readings' }}
              </button>
            </div>
          </div>
          <div v-else class="qc-view-section">
            <div class="qc-view-sec-lbl">Readings</div>
            <div style="padding:16px;text-align:center;color:#9ca3af;font-size:13px">No readings recorded yet</div>
          </div>

          <!-- Accept/Reject Qty split -->
          <div class="qc-view-section" v-if="viewDoc.inspected_qty">
            <div class="qc-view-sec-lbl">Accepted / Rejected Qty</div>
            <div v-if="viewDoc.docstatus===0" style="display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap">
              <div>
                <label style="font-size:11px;color:#6b7280;display:block;margin-bottom:2px">Inspected Qty</label>
                <div style="font-size:13px;font-weight:600;padding:6px 0">{{ viewDoc.inspected_qty }}</div>
              </div>
              <div>
                <label style="font-size:11px;color:#6b7280;display:block;margin-bottom:2px">Accepted Qty</label>
                <input type="number" min="0" step="0.001" class="qc-input" style="width:110px"
                       v-model.number="viewDoc.accepted_qty"
                       @change="onAcceptedQtyChange" />
              </div>
              <div>
                <label style="font-size:11px;color:#6b7280;display:block;margin-bottom:2px">Rejected Qty</label>
                <input type="number" min="0" step="0.001" class="qc-input" style="width:110px"
                       v-model.number="viewDoc.rejected_qty"
                       @change="onRejectedQtyChange" />
              </div>
              <div v-if="Number(viewDoc.accepted_qty||0)+Number(viewDoc.rejected_qty||0) !== Number(viewDoc.inspected_qty||0)"
                   style="font-size:11.5px;color:#dc2626">
                Must sum to {{ viewDoc.inspected_qty }}
              </div>
            </div>
            <div v-else style="display:flex;gap:16px;flex-wrap:wrap">
              <div><span class="qc-meta-lbl">Inspected</span><div style="font-size:12.5px;margin-top:2px">{{ viewDoc.inspected_qty }}</div></div>
              <div><span class="qc-meta-lbl">Accepted</span><div style="font-size:12.5px;margin-top:2px;color:#16a34a;font-weight:600">{{ viewDoc.accepted_qty || 0 }}</div></div>
              <div><span class="qc-meta-lbl">Rejected</span><div style="font-size:12.5px;margin-top:2px;color:#dc2626;font-weight:600">{{ viewDoc.rejected_qty || 0 }}</div></div>
            </div>
          </div>

          <!-- Remarks -->
          <div class="qc-view-section" v-if="viewDoc.remarks">
            <div class="qc-view-sec-lbl">Remarks</div>
            <div style="font-size:13px;color:#374151;background:#f8fafc;border-radius:6px;padding:10px 12px;border:1px solid #e2e8f0">{{ viewDoc.remarks }}</div>
          </div>

          <!-- Meta -->
          <div class="qc-view-section">
            <div style="display:flex;gap:16px;flex-wrap:wrap">
              <div v-if="viewDoc.inspected_by"><span class="qc-meta-lbl">Inspected By</span><div style="font-size:12.5px;margin-top:2px">{{ viewDoc.inspected_by }}</div></div>
              <div v-if="viewDoc.verified_by"><span class="qc-meta-lbl">Verified By</span><div style="font-size:12.5px;margin-top:2px">{{ viewDoc.verified_by }}</div></div>
              <div v-if="viewDoc.qc_inspection_template"><span class="qc-meta-lbl">Template</span><div style="font-size:12.5px;margin-top:2px">{{ viewDoc.qc_inspection_template }}</div></div>
              <div v-if="viewDoc.creation"><span class="qc-meta-lbl">Created</span><div style="font-size:12.5px;margin-top:2px">{{ fmtDate(viewDoc.creation?.slice(0,10)) }}</div></div>
            </div>
          </div>

        </div>
        <div class="qc-dfooter">
          <button class="qc-btn-ghost" @click="viewOpen=false">Close</button>
          <!-- Request Approval button: only for submitted inspections that failed QC -->
          <button
            v-if="viewDoc.docstatus === 1 && viewDoc.status === 'Fail'"
            class="qc-btn-approval"
            :disabled="approvalSending"
            @click="requestApproval(viewDoc.name)"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 12h6M9 16h4"/></svg>
            {{ approvalSending ? 'Requesting…' : 'Request Approval' }}
          </button>
          <!-- Certificate of Analysis: available for any submitted inspection -->
          <button
            v-if="viewDoc.docstatus === 1"
            class="qc-btn-ghost"
            :disabled="coaSending"
            @click="printCOA(viewDoc.name)"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9V2h12v7"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><path d="M6 14h12v8H6z"/></svg>
            {{ coaSending ? 'Generating…' : 'Print / Download COA' }}
          </button>
          <button v-if="viewDoc.docstatus===0" class="qc-btn-edit" @click="openEdit(viewDoc);viewOpen=false">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            Edit
          </button>
          <button v-if="viewDoc.docstatus===0" class="qc-btn-save" :disabled="saving" @click="saveReadings">
            <span v-html="icon('save',13)"></span>{{ saving?'Saving…':'Save' }}
          </button>
          <button v-if="viewDoc.docstatus===0 && (viewDoc.readings||[]).length" class="qc-btn-primary" :disabled="saving" @click="submitInspection(viewDoc.name)">
            <span v-html="icon('check',13)"></span>{{ saving?'Submitting…':'Submit' }}
          </button>
        </div>
      </template>
    </div>

    <!-- ── Edit Drawer ── -->
    <div v-if="editOpen" class="qc-overlay" @click.self="editOpen=false"></div>
    <div class="qc-drawer" :class="{open:editOpen}">
      <div class="qc-dheader" style="background:linear-gradient(135deg,#1e3a5f,#2563eb)">
        <button class="qc-dclose" @click="editOpen=false"><span v-html="icon('x',16)"></span></button>
        <div class="qc-dh-top">
          <div class="qc-dh-ico">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          </div>
          <div>
            <div class="qc-dh-title">Edit QC Inspection</div>
            <div class="qc-dh-sub">{{ editForm._name }}</div>
          </div>
        </div>
      </div>
      <div class="qc-dbody">
        <div class="qc-fields-grid">
          <div class="qc-field">
            <label class="qc-label">Inspection Type <span class="req">*</span></label>
            <select v-model="editForm.inspection_type" class="qc-select-full">
              <option value="Incoming">Incoming — Purchasing goods</option>
              <option value="Outgoing">Outgoing — Dispatching goods</option>
              <option value="In Process">In Process — Manufacturing</option>
            </select>
          </div>
          <div class="qc-field">
            <label class="qc-label">Reference Doc Type <span class="req">*</span></label>
            <select v-model="editForm.reference_type" class="qc-select-full">
              <option value="">Select…</option>
              <option v-for="rt in REF_TYPE_MAP[editForm.inspection_type] || refTypes" :key="rt" :value="rt">{{ rt }}</option>
            </select>
          </div>
          <div class="qc-field">
            <label class="qc-label">Reference Document <span class="req">*</span></label>
            <SearchableSelect
              v-model="editForm.reference_name"
              :options="editRefDocs"
              :placeholder="editForm.reference_type ? (editRefLoading ? 'Loading…' : 'Search ' + editForm.reference_type + '…') : 'Select a Doc Type first…'"
              :disabled="!editForm.reference_type"
              value-key="value"
              label-key="label"
            />
          </div>
          <div class="qc-field">
            <label class="qc-label">Item <span class="req">*</span></label>
            <SearchableSelect
              v-model="editForm.item"
              :options="items"
              :placeholder="!editForm.reference_name ? 'Select a Reference Document first…' : (itemsLoading ? 'Loading…' : 'Search item code…')"
              :disabled="!editForm.reference_name"
              value-key="value"
              label-key="label"
            />
          </div>
          <div class="qc-field">
            <label class="qc-label">Sample Size</label>
            <input v-model.number="editForm.sample_size" type="number" min="0" step="0.001" class="qc-input" />
          </div>
          <div class="qc-field">
            <label class="qc-label">Inspection Date <span class="req">*</span></label>
            <input v-model="editForm.inspection_date" type="date" class="qc-input" />
          </div>
          <div class="qc-field" style="grid-column:1/-1">
            <label class="qc-label">Remarks</label>
            <textarea v-model="editForm.remarks" rows="2" class="qc-input" placeholder="Optional observations…"></textarea>
          </div>
          <div class="qc-field" style="grid-column:1/-1">
            <label class="qc-label">QC Template</label>
            <div style="display:flex;gap:8px;align-items:center">
              <select v-model="editForm.qc_inspection_template" class="qc-select-full" style="flex:1">
                <option value="">— No template —</option>
                <option v-for="t in editTemplates" :key="t.name" :value="t.name">
                  {{ t.template_name }} ({{ t.parameter_count }} param{{ t.parameter_count===1?'':'s' }})
                </option>
              </select>
              <button
                type="button"
                class="qc-btn-ghost"
                :disabled="applyingTemplate || !editForm.qc_inspection_template"
                @click="applyTemplate"
              >
                {{ applyingTemplate ? 'Applying…' : 'Apply Template' }}
              </button>
            </div>
            <div style="font-size:11px;color:#9ca3af;margin-top:4px">
              Applying a template rebuilds the Readings table from its parameters. Any previously entered reading values will be cleared. Only available on Draft inspections.
            </div>
          </div>
        </div>
      </div>
      <div class="qc-dfooter">
        <button class="qc-btn-ghost" @click="editOpen=false">Cancel</button>
        <button class="qc-btn-primary" :disabled="editSaving" @click="updateInspection">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
          {{ editSaving ? 'Saving…' : 'Save Changes' }}
        </button>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiCall, apiList } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";
import { fmtDate } from "../utils/format.js";
import SearchableSelect from "../components/SearchableSelect.vue";

const { toast } = useToast();
const route = useRoute();
const router = useRouter();

// ── State ─────────────────────────────────────────────────────────────────────
const list        = ref([]);
const loading     = ref(false);
const drawerOpen  = ref(false);
const drawerSaving = ref(false);
const editOpen    = ref(false);
const editSaving  = ref(false);
const editTemplates     = ref([]);
const editTemplateLoading = ref(false);
const applyingTemplate  = ref(false);
const viewOpen    = ref(false);
const viewDoc     = ref(null);
const viewLoading = ref(false);
const approvalSending = ref(false);
const coaSending  = ref(false);
const saving      = ref(false);
const isDirty     = ref(false);
const search      = ref("");
const filterStatus = ref("all");
const filterRefType = ref("");
const activeType  = ref("all");
const dateFrom    = ref("");
const dateTo      = ref("");
const page        = ref(1);
const pageSize    = 40;
const sortCol     = ref("inspection_date");
const sortDir     = ref("desc");

// Edit form
const editForm = reactive({
  _name:          "",
  inspection_type: "Incoming",
  reference_type:  "",
  reference_name:  "",
  item:            "",
  sample_size:     1,
  inspection_date: "",
  remarks:         "",
  qc_inspection_template: "",
});
const editRefDocs  = ref([]);
const editRefLoading = ref(false);
// Guards the reference_type watcher below from clearing reference_name while
// openEdit() is hydrating the form from an existing record (see openEdit()).
const suppressEditRefWatch = ref(false);

const refTypes = ["Purchase Invoice", "Sales Invoice", "Stock Entry"];

// ── Dropdown data ──────────────────────────────────────────────────
const refDocs       = ref([]);   // Reference Document options
const refDocsLoading = ref(false);
const items         = ref([]);   // Item options
const itemsLoading  = ref(false);

const form = reactive({
  inspection_type: "Incoming",
  reference_type: "",
  reference_name: "",
  item: "",
  sample_size: 1,
  inspection_date: new Date().toISOString().slice(0, 10),
  remarks: "",
});

// ── Reference Doc Type options driven by Inspection Type ───────────────────────
const REF_TYPE_MAP = {
  "Incoming":   ["Purchase Invoice", "Sales Invoice"],
  "Outgoing":   ["Sales Invoice", "Purchase Invoice"],
  "In Process": ["Stock Entry", "Purchase Invoice", "Sales Invoice"],
};

const refTypeOptions = computed(() => {
  return REF_TYPE_MAP[form.inspection_type] || ["Purchase Invoice", "Sales Invoice", "Stock Entry"];
});

// Reset ref type + docs when inspection_type changes
watch(() => form.inspection_type, () => {
  form.reference_type  = "";
  form.reference_name  = "";
  refDocs.value        = [];
}, { immediate: true });

// Fetch reference docs whenever reference_type changes
watch(() => form.reference_type, (newType) => {
  form.reference_name = "";
  if (newType) fetchRefDocs("");
  else refDocs.value = [];
});

// Fetch items scoped to the chosen reference document whenever it changes
watch(() => form.reference_name, (newName) => {
  form.item = "";
  fetchItems(form.reference_type, newName);
});

// ── Type config ────────────────────────────────────────────────────────────────
const TYPE_META = {
  "Incoming":   { color: "#0891b2", grad: "linear-gradient(135deg,#0c4a6e,#0891b2)" },
  "Outgoing":   { color: "#ea580c", grad: "linear-gradient(135deg,#7c2d12,#ea580c)" },
  "In Process": { color: "#7c3aed", grad: "linear-gradient(135deg,#3b0764,#7c3aed)" },
};

function typeStyle(t) {
  const m = TYPE_META[t] || { color: "#6b7280" };
  return `background:${m.color}18;color:${m.color};border:1px solid ${m.color}33`;
}
function typeGrad(t) {
  return (TYPE_META[t] || { grad: "linear-gradient(135deg,#374151,#6b7280)" }).grad;
}
function typeAccent(t) {
  return (TYPE_META[t] || { color: "#6b7280" }).color;
}
function paramTypeStyle(pt) {
  if (pt === "Numeric")     return "background:#eff6ff;color:#2563eb";
  if (pt === "Non-Numeric") return "background:#f0fdf4;color:#16a34a";
  return "background:#faf5ff;color:#7c3aed";
}
function statusClass(r) {
  const s = r.status || "";
  if (s === "Pass")    return "qc-status-pass";
  if (s === "Fail")    return "qc-status-fail";
  return "qc-status-pending";
}
function shortUser(u) {
  if (!u) return "—";
  return u.split("@")[0].replace(/\./g, " ").replace(/\b\w/g, c => c.toUpperCase()).slice(0, 18);
}

// ── Computed ───────────────────────────────────────────────────────────────────
const stats = computed(() => ({
  total:   list.value.length,
  passed:  list.value.filter(r => r.status === "Pass").length,
  failed:  list.value.filter(r => r.status === "Fail").length,
  pending: list.value.filter(r => r.status === "Pending" || r.docstatus === 0).length,
}));

const passRate = computed(() => {
  const t = stats.value.total;
  return t > 0 ? Math.round((stats.value.passed / t) * 100) : 0;
});

const typeTabs = computed(() => [
  { key: "all",        label: "All",        color: "#6b7280", cnt: list.value.length },
  { key: "Incoming",   label: "Incoming",   color: "#0891b2", cnt: list.value.filter(r => r.inspection_type === "Incoming").length },
  { key: "Outgoing",   label: "Outgoing",   color: "#ea580c", cnt: list.value.filter(r => r.inspection_type === "Outgoing").length },
  { key: "In Process", label: "In Process", color: "#7c3aed", cnt: list.value.filter(r => r.inspection_type === "In Process").length },
]);

const filtered = computed(() => {
  let r = list.value;
  if (activeType.value !== "all")       r = r.filter(x => x.inspection_type === activeType.value);
  if (filterStatus.value !== "all")     r = r.filter(x => x.status === filterStatus.value);
  if (filterRefType.value)              r = r.filter(x => x.reference_type === filterRefType.value);
  if (dateFrom.value)                   r = r.filter(x => x.inspection_date >= dateFrom.value);
  if (dateTo.value)                     r = r.filter(x => x.inspection_date <= dateTo.value);
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    r = r.filter(x =>
      (x.name || "").toLowerCase().includes(q) ||
      (x.item || "").toLowerCase().includes(q) ||
      (x.item_name || "").toLowerCase().includes(q) ||
      (x.reference_name || "").toLowerCase().includes(q)
    );
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

const totalPages = computed(() => Math.max(1, Math.ceil(sorted.value.length / pageSize)));
const paginated  = computed(() => {
  const s = (page.value - 1) * pageSize;
  return sorted.value.slice(s, s + pageSize);
});

function sort(col) {
  if (sortCol.value === col) sortDir.value = sortDir.value === "asc" ? "desc" : "asc";
  else { sortCol.value = col; sortDir.value = "asc"; }
}
function sortArrow(col) {
  if (sortCol.value !== col) return '<span style="color:#d1d5db">⇅</span>';
  return sortDir.value === "asc" ? "↑" : "↓";
}

// ── API helpers ────────────────────────────────────────────────────────────────
async function load() {
  loading.value = true;
  try {
    const res = await apiCall("zoho_books_clone.api.qc.list_inspections", {
      page_len: 200, page: 0,
    });
    list.value = res?.message?.inspections || res?.inspections || [];
  } catch (e) {
    toast.error(e.message || "Failed to load QC Inspections");
  } finally {
    loading.value = false;
  }

  // Deep-link support: /quality/inspections?open=QCI-0001 (used by the
  // Work Order QC panel to jump straight to a specific inspection).
  const openName = route.query.open;
  if (openName) {
    const row = list.value.find(r => r.name === openName);
    if (row) openView(row);
    else openView({ name: openName });
  }
}

async function openView(r) {
  viewDoc.value = { ...r };
  viewOpen.value = true;
  isDirty.value = false;
  viewLoading.value = true;
  try {
    const res = await apiCall("zoho_books_clone.api.qc.get_inspection_detail", { inspection_name: r.name });
    if (res?.message) viewDoc.value = res.message;
    else if (res) viewDoc.value = res;
  } catch { /* keep list row */ }
  viewLoading.value = false;
}

function markDirty() { isDirty.value = true; }

function onAcceptedQtyChange() {
  if (!viewDoc.value?.inspected_qty) return;
  const inspected = Number(viewDoc.value.inspected_qty) || 0;
  const accepted = Math.max(0, Math.min(inspected, Number(viewDoc.value.accepted_qty) || 0));
  viewDoc.value.accepted_qty = accepted;
  viewDoc.value.rejected_qty = +(inspected - accepted).toFixed(3);
  markDirty();
}

function onRejectedQtyChange() {
  if (!viewDoc.value?.inspected_qty) return;
  const inspected = Number(viewDoc.value.inspected_qty) || 0;
  const rejected = Math.max(0, Math.min(inspected, Number(viewDoc.value.rejected_qty) || 0));
  viewDoc.value.rejected_qty = rejected;
  viewDoc.value.accepted_qty = +(inspected - rejected).toFixed(3);
  markDirty();
}

async function saveReadings() {
  if (!viewDoc.value) return;
  saving.value = true;
  try {
    const readings = (viewDoc.value.readings || []).map((rd, i) => ({
      idx: rd.idx || (i + 1),
      reading_value: rd.reading_value || "",
      remarks: rd.remarks || "",
    }));
    const res = await apiCall("zoho_books_clone.api.qc.save_qc_readings", {
      inspection_name: viewDoc.value.name,
      readings_json: JSON.stringify(readings),
      accepted_qty: viewDoc.value.inspected_qty ? viewDoc.value.accepted_qty : undefined,
      rejected_qty: viewDoc.value.inspected_qty ? viewDoc.value.rejected_qty : undefined,
    });
    const data = res?.message || res;
    if (data) {
      viewDoc.value.status = data.status;
      viewDoc.value.accepted_readings = data.accepted;
      viewDoc.value.rejected_readings = data.rejected;
      viewDoc.value.total_readings = data.total;
      if (data.readings) viewDoc.value.readings = data.readings;
      if (data.accepted_qty !== undefined) viewDoc.value.accepted_qty = data.accepted_qty;
      if (data.rejected_qty !== undefined) viewDoc.value.rejected_qty = data.rejected_qty;
    }
    isDirty.value = false;
    toast.success("Readings saved");
    await load();
  } catch (e) {
    toast.error(e.message || "Failed to save readings");
  } finally { saving.value = false; }
}

async function submitInspection(name) {
  saving.value = true;
  try {
    const res = await apiCall("zoho_books_clone.api.qc.submit_qc_inspection", { inspection_name: name });
    const data = res?.message || res;
    if (viewDoc.value) {
      viewDoc.value.docstatus = 1;
      viewDoc.value.status = data?.status || viewDoc.value.status;
    }
    toast.success(`QC Inspection ${name} submitted — ${data?.status || ""}`);
    viewOpen.value = false;
    await load();
  } catch (e) {
    toast.error(e.message || "Submit failed");
  } finally { saving.value = false; }
}

async function requestApproval(inspectionName) {
  if (!inspectionName) return;
  approvalSending.value = true;
  try {
    await apiCall("zoho_books_clone.api.qc_approval.create_qc_approval_request", {
      inspection_name: inspectionName,
      reason: "",
    });
    toast.success(`Approval request created for ${inspectionName} — check Pending Approvals`);
    viewOpen.value = false;
  } catch (e) {
    toast.error(e.message || "Failed to create approval request");
  } finally {
    approvalSending.value = false;
  }
}

async function printCOA(inspectionName) {
  if (!inspectionName) return;
  coaSending.value = true;
  try {
    const res = await apiCall("zoho_books_clone.api.qc.generate_coa", {
      inspection_name: inspectionName,
    });
    const data = res?.message || res || {};
    if (!data.html) throw new Error("Certificate of Analysis returned no content");
    // Open in a new tab so the browser's own print/save-as-PDF affordances are available.
    const win = window.open("", "_blank");
    if (!win) {
      toast.error("Pop-up blocked — please allow pop-ups to view the Certificate of Analysis.");
      return;
    }
    win.document.open();
    win.document.write(data.html);
    win.document.close();
  } catch (e) {
    toast.error(e.message || "Failed to generate Certificate of Analysis");
  } finally {
    coaSending.value = false;
  }
}

function openNew() {
  Object.assign(form, {
    inspection_type: "Incoming",
    reference_type: "",
    reference_name: "",
    item: "",
    sample_size: 1,
    inspection_date: new Date().toISOString().slice(0, 10),
    remarks: "",
  });
  refDocs.value = [];
  items.value   = [];
  drawerOpen.value = true;
}

// ── Edit Inspection ────────────────────────────────────────────────────────────
async function fetchEditRefDocs(q = "") {
  if (!editForm.reference_type) { editRefDocs.value = []; return; }
  editRefLoading.value = true;
  try {
    const LABEL_FIELD = {
      "Purchase Invoice": "supplier",
      "Sales Invoice":    "customer",
      "Stock Entry":      "stock_entry_type",
    };
    const labelField = LABEL_FIELD[editForm.reference_type] || null;
    const fields = labelField ? ["name", labelField] : ["name"];
    const rows = await apiList(editForm.reference_type, {
      fields,
      filters: [["docstatus", "!=", 2], ...(q ? [["name", "like", `%${q}%`]] : [])],
      limit: 50,
      order: "modified desc",
    });
    editRefDocs.value = rows.map(r => ({
      value: r.name,
      label: labelField && r[labelField] ? `${r.name}  —  ${r[labelField]}` : r.name,
    }));
  } catch { editRefDocs.value = []; }
  finally { editRefLoading.value = false; }
}

watch(() => editForm.reference_type, (newType) => {
  if (suppressEditRefWatch.value) return;
  editForm.reference_name = "";
  if (newType) fetchEditRefDocs("");
  else editRefDocs.value = [];
});

watch(() => editForm.reference_name, (newName) => {
  if (suppressEditRefWatch.value) return;
  editForm.item = "";
  fetchItems(editForm.reference_type, newName);
});

function openEdit(r) {
  suppressEditRefWatch.value = true;
  Object.assign(editForm, {
    _name:           r.name || "",
    inspection_type: r.inspection_type || "Incoming",
    reference_type:  r.reference_type  || "",
    reference_name:  r.reference_name  || "",
    item:            r.item            || "",
    sample_size:     r.sample_size     || 1,
    inspection_date: r.inspection_date || new Date().toISOString().slice(0, 10),
    remarks:         r.remarks         || "",
    qc_inspection_template: r.qc_inspection_template || "",
  });
  // Let the reference_type watcher run (and skip clearing) before re-enabling it
  // for genuine user-driven Reference Doc Type changes.
  nextTick(() => { suppressEditRefWatch.value = false; });
  // Load current ref docs and items for dropdowns
  fetchItems(r.reference_type, r.reference_name);
  if (r.reference_type) fetchEditRefDocs("");
  fetchEditTemplates();
  editOpen.value = true;
}

// Load all available templates so the user can manually (re-)attach one to
// a Draft inspection whose readings never got populated (see
// applyTemplate()). Intentionally unfiltered -- a matching template may not
// have existed for this item/inspection_type at creation time, but the user
// may still want to pick a close match manually.
async function fetchEditTemplates() {
  editTemplateLoading.value = true;
  try {
    const res = await apiCall("zoho_books_clone.api.qc.get_templates", {});
    editTemplates.value = res?.message || res || [];
  } catch { editTemplates.value = []; }
  finally { editTemplateLoading.value = false; }
}

// (Re-)attach the selected template to this Draft inspection and rebuild its
// Readings table from the template's parameters. This is the fix for
// inspections created before a matching template existed -- template
// resolution otherwise only ever runs once, at creation time.
async function applyTemplate() {
  if (!editForm.qc_inspection_template) return;
  applyingTemplate.value = true;
  try {
    const res = await apiCall("zoho_books_clone.api.qc.apply_qc_template", {
      inspection_name: editForm._name,
      template_name: editForm.qc_inspection_template,
    });
    const data = res?.message || res;
    const count = data?.doc?.readings?.length || 0;
    toast.success(`Template applied — ${count} reading${count === 1 ? "" : "s"} generated`);
    editOpen.value = false;
    await load();
    if (data?.doc) openView(data.doc);
  } catch (e) {
    toast.error(e.message || "Failed to apply template");
  } finally { applyingTemplate.value = false; }
}

async function updateInspection() {
  const refName  = (editForm.reference_name || "").trim();
  const itemCode = (editForm.item || "").trim();
  if (!editForm.reference_type) return toast.error("Please select a Reference Doc Type.");
  if (!refName)                 return toast.error("Reference Document is required.");
  if (!itemCode)                return toast.error("Item is required.");

  editSaving.value = true;
  try {
    await apiCall("zoho_books_clone.api.qc.update_qc_inspection", {
      inspection_name:  editForm._name,
      inspection_type:  editForm.inspection_type,
      reference_type:   editForm.reference_type,
      reference_name:   refName,
      item_code:        itemCode,
      sample_size:      editForm.sample_size || 1,
      inspection_date:  editForm.inspection_date,
      remarks:          editForm.remarks || "",
    });
    toast.success(`Inspection ${editForm._name} updated`);
    editOpen.value = false;
    await load();
  } catch (e) {
    toast.error(e.message || "Failed to update inspection");
  } finally { editSaving.value = false; }
}

async function saveInspection() {
  // Sanitize inputs — trim whitespace and stray special characters
  const refName  = (form.reference_name || "").trim().replace(/[`'"]/g, "");
  const itemCode = (form.item || "").trim().replace(/[`'"]/g, "");

  if (!form.reference_type) {
    return toast.error("Please select a Reference Doc Type.");
  }
  if (!refName) {
    return toast.error("Reference Document name is required (e.g. PREC-2026-00001).");
  }
  if (!itemCode) {
    return toast.error("Item code is required.");
  }

  drawerSaving.value = true;
  try {
    const res = await apiCall("zoho_books_clone.api.qc.create_qc_inspection", {
      reference_type: form.reference_type,
      reference_name: refName,
      item_code: itemCode,
      inspection_type: form.inspection_type,
    });
    const data = res?.message || res;
    if (data?.created === false) {
      // Inspection already exists — open it
      toast.success(`Inspection ${data.inspection_name} already exists — opening it.`);
      drawerOpen.value = false;
      await load();
      openView({ name: data.inspection_name });
    } else if (data?.inspection_name) {
      toast.success(`QC Inspection ${data.inspection_name} created`);
      drawerOpen.value = false;
      await load();
      // Auto-open the new inspection
      openView({ name: data.inspection_name, ...data.doc });
    }
  } catch (e) {
    toast.error(e.message || "Failed to create inspection");
  } finally { drawerSaving.value = false; }
}

// ── Dropdown fetchers ──────────────────────────────────────────────────
// Fetch documents of the chosen Reference DocType (Purchase Invoice, etc.)
async function fetchRefDocs(q = "") {
  if (!form.reference_type) { refDocs.value = []; return; }
  refDocsLoading.value = true;
  try {
    // Doctype-specific field mapping for a meaningful label
    const LABEL_FIELD = {
      "Purchase Invoice": "supplier",
      "Sales Invoice":    "customer",
      "Stock Entry":      "stock_entry_type",
    };
    const labelField = LABEL_FIELD[form.reference_type] || null;
    const fields = labelField ? ["name", labelField] : ["name"];
    const qFilter = q ? [["name", "like", `%${q}%`]] : [];
    const rows = await apiList(form.reference_type, {
      fields,
      filters: [["docstatus", "!=", 2], ...qFilter],
      limit: 50,
      order: "modified desc",
    });
    refDocs.value = rows.map(r => ({
      value: r.name,
      label: labelField && r[labelField]
        ? `${r.name}  —  ${r[labelField]}`
        : r.name,
    }));
  } catch { refDocs.value = []; }
  finally { refDocsLoading.value = false; }
}

// Fetch Items — scoped to the selected Reference Document. The Item
// dropdown must only ever offer items that actually appear on that
// document (see get_reference_doc_items), not every Item in the system.
async function fetchItems(referenceType, referenceName) {
  if (!referenceType || !referenceName) { items.value = []; return; }
  itemsLoading.value = true;
  try {
    const rows = await apiCall("zoho_books_clone.api.qc.get_reference_doc_items", {
      reference_type: referenceType,
      reference_name: referenceName,
    });
    items.value = (rows || []).map(r => ({
      value: r.item_code,
      label: r.item_name && r.item_name !== r.item_code ? `${r.item_code} — ${r.item_name}` : r.item_code,
    }));
  } catch { items.value = []; }
  finally { itemsLoading.value = false; }
}

function exportCSV() {
  if (!sorted.value.length) return;
  const esc = v => { const s = v == null ? "" : String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  const hdr = ["Inspection #", "Type", "Reference Type", "Reference", "Item", "Date", "Status", "Accepted", "Rejected", "Total", "Inspected By"];
  const lines = [hdr.join(",")];
  for (const r of sorted.value) {
    lines.push([
      r.name, r.inspection_type, r.reference_type, r.reference_name || "",
      r.item, r.inspection_date, r.status,
      r.accepted_readings || 0, r.rejected_readings || 0, r.total_readings || 0, r.inspected_by || "",
    ].map(esc).join(","));
  }
  const blob = new Blob(["\uFEFF" + lines.join("\r\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `qc_inspections_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click(); URL.revokeObjectURL(url);
  toast.success(`Exported ${sorted.value.length} row(s)`);
}

onMounted(load);
</script>

<style scoped>
.qc-page { display:flex; flex-direction:column; gap:14px; padding:24px; min-width:0; }

/* KPI strip */
.qc-kpi-strip { display:grid; grid-template-columns:repeat(5,1fr); gap:10px; min-width:0; }
.qc-kpi { background:#fff; border:1px solid #e5e7eb; border-radius:10px; padding:12px 14px; display:flex; align-items:center; gap:12px; cursor:pointer; transition:border-color .15s,box-shadow .15s; }
.qc-kpi:hover,.qc-kpi.active { border-color:#2563eb; box-shadow:0 0 0 2px rgba(37,99,235,.1); }
.qc-kpi-ico { width:36px; height:36px; border-radius:9px; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.qc-kpi-lbl { font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.05em; color:#9ca3af; }
.qc-kpi-val { font-size:20px; font-weight:700; color:#0f172a; line-height:1.2; }

/* Tabs */
.qc-tab-row { display:flex; align-items:center; gap:6px; flex-wrap:wrap; }
.qc-tab { padding:5px 12px; border-radius:20px; font-size:12.5px; font-weight:600; border:1px solid #e5e7eb; background:#fff; color:#6b7280; cursor:pointer; font-family:inherit; display:inline-flex; align-items:center; gap:6px; }
.qc-tab.active { background:#eff6ff; border-color:#2563eb; color:#2563eb; }
.qc-tab-dot { width:7px; height:7px; border-radius:50%; flex-shrink:0; }
.qc-tab-cnt { background:#f3f4f6; color:#6b7280; font-size:10.5px; padding:1px 6px; border-radius:10px; font-weight:700; }

/* Filter bar */
.qc-filter-bar { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.qc-search-wrap { display:flex; align-items:center; gap:8px; background:#fff; border:1px solid #e5e7eb; border-radius:8px; padding:6px 12px; min-width:0; flex:1; width:100%; }
.qc-search-input { border:none; background:transparent; outline:none; font:inherit; color:#111827; width:100%; font-size:13px; }
.qc-select { border:1px solid #e5e7eb; border-radius:6px; padding:4px 8px; font:inherit; font-size:12px; color:#374151; background:#fff; outline:none; cursor:pointer; }
.qc-date { border:1px solid #e5e7eb; border-radius:6px; padding:4px 8px; font-size:12px; outline:none; background:#fff; }

/* Buttons */
.qc-btn-primary { display:inline-flex; align-items:center; gap:6px; background:#2563eb; color:#fff; border:none; border-radius:8px; padding:8px 14px; font-size:13px; font-weight:600; cursor:pointer; font-family:inherit; transition:background .15s; }
.qc-btn-primary:hover { background:#1d4ed8; } .qc-btn-primary:disabled { opacity:.5; cursor:not-allowed; }
.qc-btn-ghost { display:inline-flex; align-items:center; gap:6px; background:#fff; border:1px solid #e5e7eb; border-radius:8px; padding:8px 12px; font-size:13px; color:#374151; cursor:pointer; font-family:inherit; }
.qc-btn-ghost:hover { background:#f9fafb; }
.qc-btn-save { display:inline-flex; align-items:center; gap:6px; background:#f0fdf4; border:1px solid #16a34a; color:#16a34a; border-radius:8px; padding:8px 14px; font-size:13px; font-weight:600; cursor:pointer; font-family:inherit; }
.qc-btn-save:hover { background:#dcfce7; } .qc-btn-save:disabled { opacity:.5; cursor:not-allowed; }
.qc-btn-edit { display:inline-flex; align-items:center; gap:6px; background:#fffbeb; border:1px solid #f59e0b; color:#b45309; border-radius:8px; padding:8px 14px; font-size:13px; font-weight:600; cursor:pointer; font-family:inherit; }
.qc-btn-edit:hover { background:#fef3c7; }
.qc-btn-approval { display:inline-flex; align-items:center; gap:6px; background:#faf5ff; border:1px solid #7c3aed; color:#7c3aed; border-radius:8px; padding:8px 14px; font-size:13px; font-weight:600; cursor:pointer; font-family:inherit; }
.qc-btn-approval:hover { background:#ede9fe; } .qc-btn-approval:disabled { opacity:.5; cursor:not-allowed; }

/* Table */
.qc-card { background:#fff; border:1px solid #e5e7eb; border-radius:10px; overflow:hidden; overflow-x:auto; }
.qc-table { width:100%; border-collapse:collapse; font-size:13px; }
.qc-table th { background:#f9fafb; padding:10px 12px; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:#6b7280; text-align:left; border-bottom:1px solid #e5e7eb; white-space:nowrap; }
.qc-table td { padding:10px 12px; border-bottom:1px solid #f3f4f6; vertical-align:middle; }
.qc-row { cursor:pointer; transition:background .12s; }
.qc-row:hover { background:#f8fafc; }
.qc-num {  font-size:12px; font-weight:700; color:#2563eb; background:#eff6ff; padding:2px 6px; border-radius:4px; }
.qc-type-badge { font-size:11px; font-weight:700; padding:3px 8px; border-radius:20px; }
.qc-type-mini { font-size:10px; font-weight:600; padding:2px 6px; border-radius:10px; }
.sortable { cursor:pointer; }
.ta-r { text-align:right; }
.text-muted { color:#9ca3af; }
.mono-sm { font-size:12px; }
.qc-act-btn { background:none; border:1px solid #e5e7eb; border-radius:6px; padding:4px 6px; cursor:pointer; color:#6b7280; }
.qc-act-btn:hover { background:#f3f4f6; }
.qc-empty { text-align:center; padding:40px 0; color:#6b7280; }
.qc-shimmer { height:32px; background:linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size:200%; animation:shimmer 1.4s infinite; border-radius:4px; }
@keyframes shimmer { 0%{background-position:200%} 100%{background-position:-200%} }

/* Status badges */
.qc-status-badge { font-size:11px; font-weight:700; padding:3px 9px; border-radius:20px; }
.qc-status-pass    { background:#dcfce7; color:#15803d; }
.qc-status-fail    { background:#fee2e2; color:#dc2626; }
.qc-status-pending { background:#fef3c7; color:#b45309; }

/* Pagination */
.qc-pg-btn { background:#fff; border:1px solid #e5e7eb; border-radius:6px; padding:4px 8px; cursor:pointer; font-size:13px; }
.qc-pg-btn:disabled { opacity:.4; cursor:not-allowed; }

/* Drawer */
.qc-overlay { position:fixed; inset:0; background:rgba(0,0,0,.35); z-index:998; }
.qc-drawer { position:fixed; right:0; top:0; bottom:0; width:540px; background:#fff; z-index:999; display:flex; flex-direction:column; transform:translateX(100%); transition:transform .25s cubic-bezier(.4,0,.2,1); box-shadow:-4px 0 24px rgba(0,0,0,.12); }
.qc-drawer.open { transform:translateX(0); }
.qc-view-drawer { width:620px; }
.qc-dheader { padding:20px 20px 16px; background:linear-gradient(135deg,#1e3a5f,#2563eb); position:relative; flex-shrink:0; }
.qc-dh-top { display:flex; align-items:center; gap:12px; }
.qc-dh-ico { width:40px; height:40px; border-radius:10px; background:rgba(255,255,255,.2); display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.qc-dh-title { font-size:16px; font-weight:700; color:#fff; }
.qc-dh-sub { font-size:12px; color:rgba(255,255,255,.75); margin-top:2px; }
.qc-dclose { position:absolute; top:14px; right:14px; background:rgba(255,255,255,.15); border:none; border-radius:8px; padding:6px; cursor:pointer; color:#fff; display:flex; align-items:center; }
.qc-dclose:hover { background:rgba(255,255,255,.25); }
.qc-dbody { flex:1; overflow-y:auto; padding:18px 20px; display:flex; flex-direction:column; gap:14px; }
.qc-dfooter { padding:14px 20px; border-top:1px solid #e5e7eb; display:flex; gap:8px; justify-content:flex-end; flex-shrink:0; }

/* Create form */
.qc-fields-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.qc-field { display:flex; flex-direction:column; gap:4px; }
.qc-label { font-size:12px; font-weight:600; color:#374151; }
.req { color:#ef4444; }
.qc-input { border:1px solid #e5e7eb; border-radius:8px; padding:8px 10px; font:inherit; font-size:13px; outline:none; color:#111827; transition:border-color .15s; }
.qc-input:focus { border-color:#2563eb; box-shadow:0 0 0 3px rgba(37,99,235,.08); }
.qc-select-full { border:1px solid #e5e7eb; border-radius:8px; padding:8px 10px; font:inherit; font-size:13px; outline:none; color:#111827; background:#fff; width:100%; }
.qc-select-full:focus { border-color:#2563eb; }

/* View sections */
.qc-summary-bar { display:grid; grid-template-columns:repeat(2,1fr); gap:10px; background:#f8fafc; border-radius:8px; padding:12px 14px; border:1px solid #e5e7eb; }
.qc-sumbar-item { display:flex; flex-direction:column; gap:2px; }
.qc-sumbar-lbl { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:#9ca3af; }
.qc-sumbar-val { font-size:13px; font-weight:600; color:#0f172a; }

.qc-progress-section { display:flex; flex-direction:column; gap:6px; }
.qc-progress-bar { height:8px; background:#f3f4f6; border-radius:4px; overflow:hidden; }
.qc-progress-fill { height:100%; border-radius:4px; transition:width .4s; }

.qc-view-section { display:flex; flex-direction:column; gap:6px; }
.qc-view-sec-lbl { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:#9ca3af; }
.qc-meta-lbl { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:#9ca3af; }

/* Readings table */
.qc-readings-tbl { width:100%; border-collapse:collapse; font-size:12.5px; }
.qc-readings-tbl th { background:#f9fafb; padding:8px 10px; font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:#6b7280; text-align:left; border-bottom:1px solid #e5e7eb; }
.qc-readings-tbl td { padding:8px 10px; border-bottom:1px solid #f3f4f6; vertical-align:middle; }
.qc-reading-row-accepted { background:#f0fdf4; }
.qc-reading-row-rejected { background:#fef2f2; }
.qc-rd-input { border:1px solid #e5e7eb; border-radius:6px; padding:4px 8px; font:inherit; font-size:12.5px; outline:none; width:100%; }
.qc-rd-input:focus { border-color:#2563eb; }
.qc-rd-badge { font-size:10.5px; font-weight:700; padding:2px 8px; border-radius:12px; }
.qc-rd-accepted { background:#dcfce7; color:#15803d; }
.qc-rd-rejected  { background:#fee2e2; color:#dc2626; }
.qc-rd-pending   { background:#fef3c7; color:#b45309; }

/* ── Mobile card list: hidden by default, shown ≤425px ── */
.qc-mobile-list { display:none; }

/* ── Responsive: 480px — covers 425px + 375px mobile ── */
@media (max-width: 480px) {
  .qc-page { padding:10px 8px; gap:10px; }

  /* hide desktop table, show card list */
  .qc-table-wrap { display:none; }
  .qc-mobile-list { display:flex; flex-direction:column; gap:10px; }

  /* shimmer cards */
  .qc-mobile-shimmer { height:110px; border-radius:12px; background:linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size:200%; animation:shimmer 1.4s infinite; }

  /* empty state */
  .qc-mobile-empty { text-align:center; padding:40px 16px; background:#fff; border:1px solid #e5e7eb; border-radius:12px; color:#6b7280; }

  /* individual card */
  .qc-mob-card { background:#fff; border:1px solid #e5e7eb; border-radius:12px; border-left:4px solid #6b7280; padding:12px 14px; display:flex; flex-direction:column; gap:8px; cursor:pointer; transition:box-shadow .15s,transform .12s; active:none; }
  .qc-mob-card:active { box-shadow:0 4px 16px rgba(0,0,0,.08); transform:scale(.99); }

  /* top row: number + status */
  .qc-mob-top { display:flex; align-items:center; justify-content:space-between; }

  /* type + date */
  .qc-mob-row2 { display:flex; align-items:center; gap:8px; }
  .qc-mob-date { font-size:11.5px; color:#9ca3af;  margin-left:auto; }

  /* label-value rows */
  .qc-mob-item { display:flex; align-items:baseline; gap:6px; font-size:12.5px; }
  .qc-mob-lbl { font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:#9ca3af; flex-shrink:0; min-width:56px; }
  .qc-mob-val { font-weight:600; color:#0f172a; line-height:1.3; word-break:break-word; }
  .qc-mob-sub { font-weight:400; color:#9ca3af; font-size:11px; }

  /* footer: readings + inspector */
  .qc-mob-footer { display:flex; align-items:center; justify-content:space-between; padding-top:4px; border-top:1px solid #f3f4f6; margin-top:2px; }
  .qc-mob-readings { font-size:12px; font-weight:600; display:flex; align-items:center; gap:3px; }
  .qc-mob-inspector { font-size:11.5px; color:#6b7280; }

  /* KPI: 2×2 + last full width */
  .qc-kpi-strip { grid-template-columns:1fr 1fr; gap:8px; }
  .qc-kpi-strip > .qc-kpi:last-child { grid-column: 1 / -1; }
  .qc-kpi { padding:10px 12px; gap:10px; }
  .qc-kpi-ico { width:30px; height:30px; border-radius:7px; flex-shrink:0; }
  .qc-kpi-lbl { font-size:10px; }
  .qc-kpi-val { font-size:17px; }

  /* Tab row */
  .qc-tab-row { gap:4px; row-gap:6px; }
  .qc-tab { padding:4px 9px; font-size:11.5px; gap:4px; }
  .qc-tab-cnt { font-size:10px; padding:1px 5px; }
  .qc-btn-ghost { padding:7px 10px; font-size:12px; }
  .qc-btn-primary { padding:8px 12px; font-size:12.5px; width:100%; justify-content:center; }

  /* Filter bar */
  .qc-filter-bar { flex-direction:column; align-items:stretch; gap:8px; }
  .qc-search-wrap { min-width:0; width:100%; }
  .qc-search-input { font-size:12.5px; }
  .qc-select { width:100%; font-size:12px; padding:6px 8px; }
  .qc-filter-bar > div { display:flex; flex-wrap:wrap; gap:6px; align-items:center; width:100%; }
  .qc-filter-bar > div .qc-select { flex:1; min-width:0; }
  .qc-date { flex:1; min-width:0; font-size:11.5px; padding:5px 6px; }

  /* Drawer */
  .qc-drawer,.qc-view-drawer { width:100%; }
  .qc-dheader { padding:16px 14px 12px; }
  .qc-dh-title { font-size:14px; }
  .qc-dh-sub { font-size:11px; }
  .qc-dbody { padding:14px; gap:12px; }
  .qc-dfooter { padding:12px 14px; }
  .qc-fields-grid { grid-template-columns:1fr; gap:10px; }
  .qc-summary-bar { grid-template-columns:1fr 1fr; }
}

/* ── Responsive: 375px ── */
@media (max-width: 375px) {
  .qc-page { padding:8px 6px; gap:8px; }

  /* cards stay, just tighter */
  .qc-mob-card { padding:10px 12px; gap:6px; border-radius:10px; }
  .qc-mob-lbl { min-width:50px; }
  .qc-mob-val { font-size:12px; }
  .qc-mob-date { font-size:11px; }
  .qc-mob-readings { font-size:11.5px; }
  .qc-mobile-shimmer { height:100px; }

  /* KPI */
  .qc-kpi { padding:8px 10px; gap:8px; }
  .qc-kpi-ico { width:28px; height:28px; border-radius:6px; }
  .qc-kpi-lbl { font-size:9.5px; letter-spacing:0; }
  .qc-kpi-val { font-size:15px; }

  /* Tabs */
  .qc-tab { padding:3px 7px; font-size:11px; }
  .qc-tab-cnt { padding:0 4px; font-size:9.5px; }
  .qc-btn-ghost { padding:6px 8px; font-size:11.5px; }
  .qc-btn-primary { font-size:12px; padding:7px 10px; }

  /* Filter */
  .qc-search-input { font-size:12px; }
  .qc-select { font-size:11.5px; }
  .qc-date { font-size:11px; padding:4px 5px; }

  /* Drawer */
  .qc-dheader { padding:12px 12px 10px; }
  .qc-dh-title { font-size:13px; }
  .qc-dbody { padding:12px; }
  .qc-dfooter { padding:10px 12px; }
  .qc-summary-bar { grid-template-columns:1fr; }
}
</style>