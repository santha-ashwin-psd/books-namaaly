<template>
  <div class="ew-page">
    <!-- ============================ TOOLBAR -->
    <div class="ew-actions">
      <div class="ew-search-wrap">
        <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
        <input v-model="search" placeholder="Search invoice, EWB no, customer, transporter…" class="ew-search-input" />
      </div>
      <div class="ew-pills">
        <button v-for="t in tabs" :key="t.v" class="ew-pill" :class="{active:tab===t.v}" @click="tab=t.v">
          {{ t.l }}<span v-if="t.count!=null" class="ew-pill-count">{{ t.count }}</span>
        </button>
      </div>
      <div class="ew-btn-group">
        <button class="ew-btn-ghost" @click="exportCSV" :disabled="!sortedRows.length">
          <span v-html="icon('download',14)"></span> CSV
        </button>
        <button class="ew-btn-ghost" @click="load" :disabled="loading">
          <span v-html="icon('refresh',14)"></span>
        </button>
        <button class="ew-btn-primary" :disabled="!$canCreate('invoices')" :title="!$canCreate('invoices') ? 'Read-only access' : ''" @click="openGenerateList">
          <span v-html="icon('plus',13)"></span> Generate E-Way Bill
        </button>
      </div>
    </div>

    <!-- ============================ SUMMARY -->
    <SummaryStrip v-if="!loading" :cards="[
      { label: 'Total Invoices', tone: 'accent', value: stats.total_invoices },
      { label: 'Generated', tone: 'success', value: stats.generated, valueClass: 'green' },
      { label: 'Pending', tone: stats.pending>0?'warn':'default', value: stats.pending, valueClass: stats.pending>0?'orange':'' },
      { label: 'Expiring / Expired', tone: (stats.expired>0||stats.expiring_soon>0)?'danger':'default', value: `${stats.expiring_soon} / ${stats.expired}`, valueClass: (stats.expired>0||stats.expiring_soon>0)?'red':'' },
    ]" />

    <!-- ============================ BULK ACTION BAR -->
    <div v-if="selected.size" class="inv-bulk-bar">
      <span class="inv-bulk-count">{{ selected.size }} selected</span>
      <button class="inv-bulk-btn" @click="bulkDownloadJson" :disabled="bulkBusy">
        <span v-html="icon('download',13)"></span> Download JSONs
      </button>
      <button class="inv-bulk-btn" @click="bulkExtend" :disabled="bulkBusy || !$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''">Extend Validity (+1d)</button>
      <button class="inv-bulk-btn inv-bulk-danger" @click="bulkCancelEwb" :disabled="bulkBusy || !$canDelete('invoices')" :title="!$canDelete('invoices') ? 'Not permitted' : ''">Cancel EWBs</button>
      <button class="inv-bulk-btn" @click="exportCSV" :disabled="bulkBusy">
        <span v-html="icon('download',13)"></span> Export CSV
      </button>
      <button class="inv-bulk-clear" @click="selected = new Set()">✕ Clear</button>
    </div>

    <!-- ============================ TABLE -->
    <div class="ew-card">
      <table class="ew-table ew-desktop-table">
        <thead>
          <tr>
            <th style="width:32px"><input type="checkbox" @change="toggleAll" :checked="allChecked" /></th>
            <th>EWB #</th>
            <th @click="sort('invoice_no')" class="sortable">INVOICE # <span v-html="sortArrow('invoice_no')"></span></th>
            <th @click="sort('invoice_date')" class="sortable">INV. DATE <span v-html="sortArrow('invoice_date')"></span></th>
            <th>CUSTOMER</th>
            <th>TRANSPORTER</th>
            <th>VEHICLE</th>
            <th>VALID UNTIL</th>
            <th class="ta-r">AMOUNT</th>
            <th>STATUS</th>
            <th style="width:110px;text-align:right">ACTIONS</th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 8" :key="n"><td colspan="11"><div class="ew-shimmer"></div></td></tr>
          </template>
          <template v-else>
            <tr v-for="r in paged" :key="r.name" class="ew-row" :class="{selected: selected.has(r.name)}" @click="openView(r)">
              <td @click.stop><input type="checkbox" :checked="selected.has(r.name)" @change="toggle(r.name)" /></td>
              <td><span class="ew-irn mono-sm">{{ r.ewb_no || '—' }}</span></td>
              <td @click.stop><DocLink doctype="Sales Invoice" :name="r.invoice_no" /></td>
              <td class="mono-sm text-muted">{{ fmtDate(r.invoice_date) }}</td>
              <td style="color:#374151;max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ r.customer_name || r.customer }}</td>
              <td class="text-muted">{{ r.transporter || '—' }}</td>
              <td class="mono-sm text-muted">{{ r.vehicle_no || '—' }}</td>
              <td class="mono-sm" :class="validClass(r)">{{ fmtDate(r.valid_upto) || '—' }}</td>
              <td class="ta-r mono-sm" style="color:#374151;">{{ fmtCur(r.grand_total) }}</td>
              <td><span class="ew-badge" :class="statusClass(r.ui_status)">{{ r.ui_status }}</span></td>
              <td @click.stop style="text-align:right">
                <div class="ew-actions-row">
                  <button class="ew-act-btn" @click="openView(r)" title="View"><span v-html="icon('eye',13)"></span></button>
                  <button v-if="r.ui_status==='Generated'" class="ew-act-btn" @click="quickDownload(r)" title="Download JSON"><span v-html="icon('download',13)"></span></button>
                  <button v-if="r.ui_status==='Generated'" class="ew-act-btn" :disabled="!$canDelete('invoices')" :title="!$canDelete('invoices') ? 'Not permitted' : 'Cancel EWB'" @click="actionOn(r,'cancel')"><span v-html="icon('x',13)"></span></button>
                  <button v-if="r.ui_status==='Cancelled' || r.ui_status==='Expired'" class="ew-act-btn ew-act-del" :disabled="!$canDelete('invoices')" :title="!$canDelete('invoices') ? 'Not permitted' : 'Delete'" @click.stop="deleteTarget={row:r}"><span v-html="icon('trash',13)"></span></button>
                </div>
              </td>
            </tr>
            <tr v-if="!sortedRows.length"><td colspan="11" class="ew-empty">
              <div class="ew-empty-wrap">
                <div class="ew-empty-icon" v-html="icon('warehouse',32)"></div>
                <div class="ew-empty-title">No E-Way Bills here</div>
                <div class="ew-empty-sub">Generate an E-Way Bill from a submitted sales invoice to start.</div>
                <button class="ew-btn-primary" style="margin-top:12px" @click="openGenerateList">
                  <span v-html="icon('plus',13)"></span> Generate E-Way Bill
                </button>
              </div>
            </td></tr>
          </template>
        </tbody>
      </table>

      <!-- Mobile cards (shown at ≤768px) -->
      <div class="ew-mobile-cards">
        <template v-if="loading">
          <div v-for="n in 6" :key="n" class="ew-mobile-card ew-mc--skeleton">
            <div class="ew-mc-shimmer" style="height:13px;width:55%;margin-bottom:8px"></div>
            <div class="ew-mc-shimmer" style="height:11px;width:40%;margin-bottom:6px"></div>
            <div class="ew-mc-shimmer" style="height:11px;width:65%"></div>
          </div>
        </template>
        <div v-else-if="!sortedRows.length" class="ew-mc-empty">
          <div style="font-size:32px;margin-bottom:8px">🚛</div>
          <div>No E-Way Bills here</div>
        </div>
        <template v-else>
          <div v-for="r in paged" :key="r.name" class="ew-mobile-card" @click="openView(r)">
            <div class="ew-mc-top">
              <span class="ew-mc-docno">{{ r.invoice_no }}</span>
              <span class="ew-badge" :class="statusClass(r.ui_status)">{{ r.ui_status }}</span>
            </div>
            <div class="ew-mc-mid">{{ r.customer_name || r.customer }}</div>
            <div class="ew-mc-meta">
              <span>{{ fmtDate(r.invoice_date) }}{{ r.ewb_no ? ' · EWB: ' + r.ewb_no : '' }}</span>
              <span class="ew-mc-amount">{{ fmtCur(r.grand_total) }}</span>
            </div>
            <div class="ew-mc-footer">
              <button v-if="r.ui_status==='Generated'" class="ew-act-btn" @click.stop="quickDownload(r)" title="Download"><span v-html="icon('download',13)"></span></button>
              <button v-if="r.ui_status==='Generated'" class="ew-act-btn" @click.stop="actionOn(r,'cancel')" title="Cancel"><span v-html="icon('x',13)"></span></button>
              <button v-if="r.ui_status==='Cancelled'||r.ui_status==='Expired'" class="ew-act-btn ew-act-del" @click.stop="deleteTarget={row:r}" title="Delete"><span v-html="icon('trash',13)"></span></button>
            </div>
          </div>
        </template>
      </div>
    </div>

    <div v-if="!loading && sortedRows.length">
      <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="sortedRows.length" />
    </div>

    <!-- ============================ GENERATE LIST DRAWER (pick invoice) -->
    <div v-if="genListOpen" class="ew-overlay" @click.self="genListOpen=false"></div>
    <div class="ew-drawer" :class="{open:genListOpen}">
      <div class="ew-dheader">
        <div class="ew-dheader-left">
          <div class="ew-dheader-ico"><span v-html="icon('plus',18)"></span></div>
          <div>
            <div class="ew-dheader-title">Pick an Invoice</div>
            <div class="ew-dheader-sub">Choose a submitted sales invoice to generate an E-Way Bill</div>
          </div>
        </div>
        <button class="ew-dclose" @click="genListOpen=false"><span v-html="icon('x',16)"></span></button>
      </div>
      <div class="ew-dbody">
        <input v-model="pendingSearch" class="ew-input" placeholder="Filter invoices…" style="margin-bottom:12px"/>
        <div v-if="!pendingFiltered.length" class="ew-tab-empty">No pending invoices. All submitted invoices already have an active EWB.</div>
        <div v-else class="ew-pending-list">
          <div v-for="p in pendingFiltered" :key="p.name" class="ew-pending-item" @click="startGenerate(p)">
            <div style="flex:1;min-width:0">
              <div class="ew-pending-inv mono-sm">{{ p.name }}</div>
              <div class="ew-pending-meta">{{ p.customer_name || p.customer }} · {{ fmtDate(p.posting_date) }}</div>
            </div>
            <div class="ew-pending-amount mono-sm">{{ fmtCur(p.grand_total) }}</div>
            <span v-html="icon('arrow-right',14)" style="color:#9ca3af"></span>
          </div>
        </div>
      </div>
    </div>

    <!-- ============================ GENERATE DRAWER -->
    <div v-if="genOpen" class="ew-overlay" @click.self="genOpen=false"></div>
    <div class="ew-drawer" :class="{open:genOpen}">
      <div class="ew-dheader">
        <div class="ew-dheader-left">
          <div class="ew-dheader-ico"><span v-html="icon('warehouse',18)"></span></div>
          <div>
            <div class="ew-dheader-title">Generate E-Way Bill</div>
            <div class="ew-dheader-sub">{{ genForm.invoice_no }} · {{ genForm.customer_name }}</div>
          </div>
        </div>
        <button class="ew-dclose" @click="genOpen=false"><span v-html="icon('x',16)"></span></button>
      </div>
      <div class="ew-dbody" style="gap:10px">
        <div class="ew-ctx-card">
          <div class="ew-ctx-ico"><span ><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line></svg></span></div>
          <div style="flex:1;min-width:0">
            <div class="ew-ctx-doctype">Sales Invoice</div>
            <div class="ew-ctx-name">{{ genForm.invoice_no }}</div>
          </div>
          <div class="ew-ctx-meta">
            <div class="ew-ctx-party">{{ genForm.customer_name }}</div>
            <div class="ew-ctx-amount mono">{{ fmtCur(genForm.grand_total) }}</div>
          </div>
        </div>

        <!-- Transporter -->
        <div class="ew-gen-card">
          <div class="ew-gen-card-header" @click="genCollapsed.transporter=!genCollapsed.transporter">
            <div class="ew-gen-card-title">
              <span class="ew-gen-card-title-icon"><span v-html="icon('warehouse',15)"></span></span>
              Transporter Details
            </div>
            <span class="ew-gen-card-chevron" :class="{collapsed:genCollapsed.transporter}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
          </div>
          <div class="ew-gen-card-body" :class="{collapsed:genCollapsed.transporter}">
            <div class="ew-grid">
              <div class="ew-field" style="grid-column:1/-1">
                <label class="ew-flbl">Transporter <span class="req">*</span></label>
                <input v-model="genForm.transporter" class="ew-input" placeholder="e.g. BlueDart Express, VRL Logistics" />
              </div>
              <div class="ew-field">
                <label class="ew-flbl">Vehicle Number <span class="req">*</span></label>
                <input v-model="genForm.vehicle_no" class="ew-input" placeholder="e.g. MH12AB1234"
                       @input="genForm.vehicle_no=genForm.vehicle_no.toUpperCase()" />
              </div>
              <div class="ew-field">
                <label class="ew-flbl">Vehicle Type</label>
                <select v-model="genForm.vehicle_type" class="ew-input">
                  <option value="Regular">Regular</option>
                  <option value="Over Dimensional Cargo">Over Dimensional Cargo</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        <!-- Movement -->
        <div class="ew-gen-card">
          <div class="ew-gen-card-header" @click="genCollapsed.movement=!genCollapsed.movement">
            <div class="ew-gen-card-title">
              <span class="ew-gen-card-title-icon"><span v-html="icon('refresh',15)"></span></span>
              Movement Details
            </div>
            <span class="ew-gen-card-chevron" :class="{collapsed:genCollapsed.movement}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
          </div>
          <div class="ew-gen-card-body" :class="{collapsed:genCollapsed.movement}">
            <div class="ew-grid">
              <div class="ew-field">
                <label class="ew-flbl">Distance (km) <span class="req">*</span></label>
                <input v-model.number="genForm.distance_km" type="number" min="0" step="1" class="ew-input" placeholder="e.g. 350" />
              </div>
              <div class="ew-field">
                <label class="ew-flbl">Supply Type</label>
                <select v-model="genForm.supply_type" class="ew-input">
                  <option value="Outward">Outward</option>
                  <option value="Inward">Inward</option>
                </select>
              </div>
              <div class="ew-field" style="grid-column:1/-1">
                <label class="ew-flbl">Transaction Type</label>
                <select v-model="genForm.transaction_type" class="ew-input">
                  <option value="Regular">Regular</option>
                  <option value="Bill To Ship To">Bill To Ship To</option>
                  <option value="Bill From Dispatch From">Bill From Dispatch From</option>
                  <option value="Combination">Combination</option>
                </select>
              </div>
              <div class="ew-plan-hint" style="grid-column:1/-1" v-if="genForm.distance_km>0">
                <span v-html="icon('info',13)"></span>
                <span>Validity: <b>{{ validityDays }} day{{ validityDays!==1?'s':'' }}</b> ({{ genForm.vehicle_type==='Over Dimensional Cargo'?'1 day per 20 km':'1 day per 200 km' }})</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="ew-dfooter">
        <button class="ew-btn-ghost" @click="genOpen=false" :disabled="generating">Cancel</button>
        <button class="ew-btn-primary" :disabled="generating || !canGenerate || !$canCreate('invoices')" :title="!$canCreate('invoices') ? 'Read-only access' : ''" @click="submitGenerate">
          <span v-html="icon('check',13)"></span>
          {{ generating?'Generating…':'Generate E-Way Bill' }}
        </button>
      </div>
    </div>

    <!-- ============================ VIEW DRAWER -->
    <div v-if="viewOpen" class="ew-overlay" @click.self="viewOpen=false"></div>
    <div class="ew-drawer ew-view-drawer" :class="{open:viewOpen}">
      <template v-if="viewDoc">
        <div class="ew-view-head" :class="viewDoc.ui_status==='Cancelled'?'cancelled':viewDoc.ui_status==='Expired'?'expired':''">
          <div class="ew-view-head-row">
            <div>
              <div class="ew-view-num">{{ viewDoc.ewb_no || viewDoc.name }}</div>
              <div class="ew-view-sub">
                Invoice <DocLink doctype="Sales Invoice" :name="viewDoc.invoice_no" :mono-style="false" /> · <DocLink doctype="Customer" :name="viewDoc.customer" :mono-style="false">{{ viewDoc.customer_name || viewDoc.customer }}</DocLink>
              </div>
            </div>
            <div style="display:flex;align-items:center;gap:8px">
              <span class="ew-badge ew-badge-lg" :class="statusClass(viewDoc.ui_status)">{{ viewDoc.ui_status }}</span>
              <button class="ew-dclose" @click="viewOpen=false"><span v-html="icon('x',16)"></span></button>
            </div>
          </div>
          <div class="ew-view-stats">
            <div><div class="vh-lbl">Amount</div><div class="vh-val mono">{{ fmtCur(viewDoc.grand_total) }}</div></div>
            <div><div class="vh-lbl">Valid Until</div><div class="vh-val mono" :class="validClass(viewDoc)">{{ fmtDate(viewDoc.valid_upto) || '—' }}</div></div>
            <div><div class="vh-lbl">Days Left</div><div class="vh-val" :class="(viewDoc.days_left??0)<=1?'red':''">{{ viewDoc.days_left==null?'—':viewDoc.days_left }}</div></div>
          </div>
        </div>

        <div class="ew-view-actbar">
          <button class="ew-va-btn" @click="downloadJson(viewDoc)" :disabled="!viewDoc.ewb_no || actionLoading">
            <span v-html="icon('download',13)"></span><div class="ew-va-btn-text"> Download JSON</div>
          </button>
          <button class="ew-va-btn" @click="printEwb(viewDoc)" :disabled="actionLoading">
            <span v-html="icon('mail',13)"></span> <div class="ew-va-btn-text">Print</div>
          </button>
          <button class="ew-va-btn" @click="openVehicleEdit(viewDoc)" :disabled="actionLoading || viewDoc.ui_status!=='Generated' || !$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''">
            <span v-html="icon('edit',13)"></span> <div class="ew-va-btn-text">Update Vehicle</div>
          </button>
          <button class="ew-va-btn" @click="openExtend(viewDoc)" :disabled="actionLoading || viewDoc.ui_status!=='Generated' || viewDoc.extended || !$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : (viewDoc.extended?'Already extended once — NIC permits only one extension':'')">
            <span v-html="icon('refresh',13)"></span> <div class="ew-va-btn-text">{{ viewDoc.extended?'Extended':'Extend' }}</div>
          </button>
          <button class="ew-va-btn ew-va-danger" @click="doCancel(viewDoc)" :disabled="actionLoading || viewDoc.ui_status==='Cancelled' || viewDoc.ui_status==='Expired' || !$canDelete('invoices')" :title="!$canDelete('invoices') ? 'Not permitted' : ''">
            <span v-html="icon('x',13)"></span> <div class="ew-va-btn-text">Cancel EWB</div>
          </button>
        </div>

        <div class="ew-dbody">
          <!-- Inline edit overlays -->
          <div v-if="vehicleEdit.open" class="ew-section">
            <div class="ew-section-hdr"><span v-html="icon('edit',13)"></span><span>Update Vehicle</span></div>
            <div class="ew-grid">
              <div class="ew-field">
                <label class="ew-flbl">Vehicle Number</label>
                <input v-model="vehicleEdit.vehicle" class="ew-input" @input="vehicleEdit.vehicle=vehicleEdit.vehicle.toUpperCase()" />
              </div>
              <div class="ew-field">
                <label class="ew-flbl">Transporter</label>
                <input v-model="vehicleEdit.transporter" class="ew-input" />
              </div>
              <div style="grid-column:1/-1;display:flex;gap:8px;justify-content:flex-end">
                <button class="ew-btn-ghost" @click="vehicleEdit.open=false">Cancel</button>
                <button class="ew-btn-primary" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="saveVehicle">Save</button>
              </div>
            </div>
          </div>

          <div v-if="extendEdit.open" class="ew-section">
            <div class="ew-section-hdr"><span v-html="icon('refresh',13)"></span><span>Extend Validity</span></div>
            <div class="ew-grid">
              <div class="ew-field">
                <label class="ew-flbl">Extra Days</label>
                <input v-model.number="extendEdit.days" type="number" min="1" max="30" class="ew-input" />
              </div>
              <div class="ew-plan-hint" style="grid-column:1/-1">
                <span v-html="icon('info',13)"></span>
                Per NIC rules an EWB can be extended once. The new validity becomes <b>{{ newValid }}</b>.
              </div>
              <div style="grid-column:1/-1;display:flex;gap:8px;justify-content:flex-end">
                <button class="ew-btn-ghost" @click="extendEdit.open=false">Cancel</button>
                <button class="ew-btn-primary" :disabled="!$canEdit('invoices')" :title="!$canEdit('invoices') ? 'Read-only access' : ''" @click="saveExtend">Extend</button>
              </div>
            </div>
          </div>

          <div class="ew-section">
            <div class="ew-section-hdr"><span v-html="icon('folder',13)"></span><span>Document Details</span></div>
            <div class="ew-kv-list">
              <div class="ew-kv-row">
                <span class="ew-kv-lbl">Invoice</span>
                <span class="ew-kv-val"><DocLink doctype="Sales Invoice" :name="viewDoc.invoice_no" /></span>
              </div>
              <div class="ew-kv-row">
                <span class="ew-kv-lbl">Invoice Date</span>
                <span class="ew-kv-val mono-sm">{{ fmtDate(viewDoc.invoice_date) }}</span>
              </div>
              <div class="ew-kv-row">
                <span class="ew-kv-lbl">Customer</span>
                <span class="ew-kv-val" style="font-weight:600;color:#111827">{{ viewDoc.customer_name || viewDoc.customer }}</span>
              </div>
              <div class="ew-kv-row">
                <span class="ew-kv-lbl">Amount</span>
                <span class="ew-kv-val mono-sm" style="font-weight:700;color:#0f172a">{{ fmtCur(viewDoc.grand_total) }}</span>
              </div>
              <div class="ew-kv-row">
                <span class="ew-kv-lbl">From GSTIN</span>
                <span class="ew-kv-val mono-sm">{{ viewDoc.from_gstin || 'Unregistered' }}</span>
              </div>
              <div class="ew-kv-row">
                <span class="ew-kv-lbl">To GSTIN</span>
                <span class="ew-kv-val mono-sm">{{ viewDoc.to_gstin || 'Unregistered' }}</span>
              </div>
              <div class="ew-kv-row" v-if="viewDoc.cancellation_reason">
                <span class="ew-kv-lbl">Cancellation Reason</span>
                <span class="ew-kv-val">{{ viewDoc.cancellation_reason }}</span>
              </div>
            </div>
          </div>

          <div class="ew-section">
            <div class="ew-section-hdr"><span v-html="icon('warehouse',13)"></span><span>Movement</span></div>
            <div class="ew-kv-list">
              <div class="ew-kv-row">
                <span class="ew-kv-lbl">Transporter</span>
                <span class="ew-kv-val" style="font-weight:600;color:#111827">{{ viewDoc.transporter || '—' }}</span>
              </div>
              <div class="ew-kv-row">
                <span class="ew-kv-lbl">Vehicle No</span>
                <span class="ew-kv-val mono-sm">{{ viewDoc.vehicle_no || '—' }}</span>
              </div>
              <div class="ew-kv-row">
                <span class="ew-kv-lbl">Vehicle Type</span>
                <span class="ew-kv-val">{{ viewDoc.vehicle_type || 'Regular' }}</span>
              </div>
              <div class="ew-kv-row">
                <span class="ew-kv-lbl">Supply Type</span>
                <span class="ew-kv-val">{{ viewDoc.supply_type || 'Outward' }}</span>
              </div>
              <div class="ew-kv-row">
                <span class="ew-kv-lbl">Transaction</span>
                <span class="ew-kv-val">{{ viewDoc.transaction_type || 'Regular' }}</span>
              </div>
              <div class="ew-kv-row">
                <span class="ew-kv-lbl">Generated On</span>
                <span class="ew-kv-val mono-sm">{{ fmtDate(viewDoc.creation) }}</span>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

  <!-- DELETE CONFIRM DIALOG -->
  <div v-if="deleteTarget" class="ew-overlay" style="z-index:60" @click.self="deleteTarget=null"></div>
  <div v-if="deleteTarget" class="ew-confirm" style="z-index:61">
    <div class="ew-confirm-icon danger">
      <span v-html="icon('trash', 20)"></span>
    </div>
    <div class="ew-confirm-title">Delete E-Way Bill?</div>
    <div class="ew-confirm-sub">
      E-Way Bill <strong>{{ deleteTarget.row.ewb_no || deleteTarget.row.name }}</strong> will be permanently deleted. This cannot be undone.
    </div>
    <div class="ew-confirm-actions">
      <button class="ew-btn-ghost" @click="deleteTarget=null" :disabled="deleting">Keep it</button>
      <button class="ew-btn-danger" @click="confirmDelete" :disabled="deleting">
        {{ deleting ? 'Deleting…' : 'Yes, Delete' }}
      </button>
    </div>
  </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { apiGET, apiPOST, apiDelete, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { useRoute } from "vue-router";
import { useConfirm } from "../composables/useConfirm.js";
import { useOpenFromQuery } from "../composables/useOpenFromQuery.js";
import { usePagination } from "../composables/usePagination.js";
import DocLink from "../components/DocLink.vue";
import Pagination from "../components/Pagination.vue";
import SummaryStrip from "../components/SummaryStrip.vue";
import { icon } from "../utils/icons.js";
import { flt, fmtDate } from "../utils/format.js";

const { toast } = useToast();
const route = useRoute();
const { confirm } = useConfirm();

const list = ref([]);
const loading     = ref(false);
const deleteTarget = ref(null);  // { row }
const deleting     = ref(false);
const search = ref("");
const tab = ref("all");
const stats = ref({ total_invoices: 0, total_value: 0, generated: 0, pending: 0, expired: 0, cancelled: 0, expiring_soon: 0 });
const sortCol = ref("invoice_date");
const sortDir = ref("desc");
const selected = ref(new Set());
const bulkBusy = ref(false);

const tabs = computed(() => [
  { v: "all", l: "All", count: list.value.length || null },
  { v: "Generated", l: "Generated", count: stats.value.generated },
  { v: "Expired", l: "Expired", count: stats.value.expired || null },
  { v: "Cancelled", l: "Cancelled", count: stats.value.cancelled || null },
]);

const filtered = computed(() => {
  let r = list.value;
  if (tab.value !== "all") r = r.filter((x) => x.ui_status === tab.value);
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    r = r.filter((x) =>
      (x.invoice_no || "").toLowerCase().includes(q) ||
      (x.ewb_no || "").toLowerCase().includes(q) ||
      (x.customer_name || "").toLowerCase().includes(q) ||
      (x.transporter || "").toLowerCase().includes(q)
    );
  }
  return r;
});

const sortedRows = computed(() => {
  const col = sortCol.value;
  return [...filtered.value].sort((a, b) => {
    const av = a[col] ?? "";
    const bv = b[col] ?? "";
    const c = typeof av === "number" ? av - bv : String(av).localeCompare(String(bv));
    return sortDir.value === "asc" ? c : -c;
  });
});

const { page, pageSize, paged } = usePagination(sortedRows, { storageKey: "eway-bills" });

function sort(col) {
  if (sortCol.value === col) sortDir.value = sortDir.value === "asc" ? "desc" : "asc";
  else { sortCol.value = col; sortDir.value = "asc"; }
}
function sortArrow(col) {
  if (sortCol.value !== col) return '<span style="color:#d1d5db">⇅</span>';
  return sortDir.value === "asc" ? "↑" : "↓";
}

function fmtCur(v) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 0 }).format(flt(v));
}
function statusClass(s) {
  if (s === "Cancelled") return "badge-grey";
  if (s === "Expired") return "badge-red";
  if (s === "Generated") return "badge-green";
  return "badge-orange";
}
function validClass(r) {
  if (!r.valid_upto) return "";
  if (r.ui_status === "Expired") return "red";
  const dl = r.days_left;
  if (dl != null && dl <= 1) return "red";
  return "";
}

// ----- load
async function load() {
  loading.value = true;
  try {
    const co = await resolveCompany();
    const [rows, st] = await Promise.all([
      apiGET("zoho_books_clone.api.eway.get_eway_bills", { limit: 100000 }),
      apiGET("zoho_books_clone.api.eway.get_eway_stats", { company: co }),
    ]);
    const data = rows?.message ?? rows ?? [];
    list.value = (Array.isArray(data) ? data : []).map((r) => ({
      ...r,
      days_left: r.valid_upto ? Math.max(0, Math.ceil((new Date(r.valid_upto) - new Date()) / 86400000)) : null,
    }));
    stats.value = st?.message ?? st ?? stats.value;
  } catch (e) {
    toast.error(e.message || "Failed to load");
  } finally {
    loading.value = false;
  }
}
// ── Delete ────────────────────────────────────────────────────────────────────
async function confirmDelete() {
  if (!deleteTarget.value) return;
  const { row } = deleteTarget.value;
  deleting.value = true;
  try {
    await apiDelete("E Way Bill", row.name);
    toast.success(`E-Way Bill ${row.ewb_no || row.name} deleted`);
    deleteTarget.value = null;
    viewOpen.value = false;
    await load();
  } catch (e) {
    toast.error(e.message || "Delete failed");
  } finally {
    deleting.value = false;
  }
}

onMounted(async () => {
  await load();
  useOpenFromQuery({
    route,
    openByName: (n) => openView(list.value.find(x => x.name === n) || { name: n }),
  });
});

// ----- generate list drawer
const genListOpen = ref(false);
const pendingList = ref([]);
const pendingSearch = ref("");
const pendingFiltered = computed(() => {
  if (!pendingSearch.value.trim()) return pendingList.value;
  const q = pendingSearch.value.toLowerCase();
  return pendingList.value.filter((p) =>
    (p.name || "").toLowerCase().includes(q) ||
    (p.customer_name || "").toLowerCase().includes(q)
  );
});

async function openGenerateList() {
  genListOpen.value = true;
  pendingSearch.value = "";
  try {
    const co = await resolveCompany();
    const r = await apiGET("zoho_books_clone.api.eway.get_pending_invoices", { company: co, limit: 200 });
    pendingList.value = r?.message ?? r ?? [];
  } catch (e) {
    toast.error(e.message || "Failed to load pending invoices");
  }
}

// ----- generate drawer
const genOpen = ref(false);
const generating = ref(false);
const genCollapsed = reactive({ transporter: false, movement: false });
const genForm = reactive({
  invoice_no: "", customer_name: "", grand_total: 0,
  transporter: "", vehicle_no: "", vehicle_type: "Regular",
  distance_km: 0, supply_type: "Outward", transaction_type: "Regular",
});

const validityDays = computed(() => {
  const d = Number(genForm.distance_km) || 0;
  if (d <= 0) return 1;
  if (genForm.vehicle_type === "Over Dimensional Cargo") return Math.max(1, Math.ceil(d / 20));
  return Math.max(1, Math.ceil(d / 200));
});

const canGenerate = computed(() =>
  genForm.transporter.trim() && genForm.vehicle_no.trim() && genForm.distance_km > 0
);

function startGenerate(p) {
  Object.assign(genForm, {
    invoice_no: p.name, customer_name: p.customer_name || p.customer, grand_total: p.grand_total,
    transporter: "", vehicle_no: "", vehicle_type: "Regular",
    distance_km: 0, supply_type: "Outward", transaction_type: "Regular",
  });
  Object.assign(genCollapsed, { transporter: false, movement: false });
  genListOpen.value = false;
  genOpen.value = true;
}

async function submitGenerate() {
  if (!canGenerate.value) return toast.error("Transporter, vehicle and distance are required");
  generating.value = true;
  try {
    const res = await apiPOST("zoho_books_clone.api.eway.generate_eway_bill", {
      invoice_no: genForm.invoice_no,
      transporter: genForm.transporter,
      vehicle_no: genForm.vehicle_no,
      distance_km: genForm.distance_km,
      supply_type: genForm.supply_type,
      transaction_type: genForm.transaction_type,
      vehicle_type: genForm.vehicle_type,
    });
    const ewb = res?.message?.ewb_no || res?.ewb_no;
    toast.success(`E-Way Bill ${ewb || ""} generated`);
    genOpen.value = false;
    await load();
  } catch (e) {
    toast.error(e.message || "Failed to generate");
  } finally {
    generating.value = false;
  }
}

// ----- view drawer
const viewOpen = ref(false);
const viewDoc = ref(null);
const actionLoading = ref(false);

async function openView(r) {
  if (!r?.name) return;
  viewOpen.value = true;
  viewDoc.value = { ...r };
  try {
    const d = await apiGET("zoho_books_clone.api.eway.get_eway_bill", { name: r.name });
    const data = d?.message ?? d ?? {};
    if (data.name) viewDoc.value = data;
  } catch (e) {
    toast.error(e.message || "Failed to load EWB detail");
  }
}

// ----- view actions
const vehicleEdit = reactive({ open: false, vehicle: "", transporter: "" });
const extendEdit = reactive({ open: false, days: 1 });

const newValid = computed(() => {
  const base = viewDoc.value?.valid_upto ? new Date(viewDoc.value.valid_upto) : new Date();
  if (base < new Date()) base.setTime(new Date().getTime());
  base.setDate(base.getDate() + (Number(extendEdit.days) || 1));
  return fmtDate(base.toISOString().slice(0, 10));
});

function openVehicleEdit(doc) {
  vehicleEdit.open = true;
  extendEdit.open = false;
  vehicleEdit.vehicle = doc.vehicle_no || "";
  vehicleEdit.transporter = doc.transporter || "";
}
function openExtend(doc) {
  extendEdit.open = true;
  vehicleEdit.open = false;
  extendEdit.days = 1;
}

async function saveVehicle() {
  if (!vehicleEdit.vehicle.trim()) return toast.error("Vehicle number required");
  actionLoading.value = true;
  try {
    await apiPOST("zoho_books_clone.api.eway.update_vehicle", {
      name: viewDoc.value.name,
      vehicle_no: vehicleEdit.vehicle,
      transporter: vehicleEdit.transporter,
    });
    toast.success("Vehicle updated");
    vehicleEdit.open = false;
    await openView({ name: viewDoc.value.name });
    await load();
  } catch (e) { toast.error(e.message || "Update failed"); }
  finally { actionLoading.value = false; }
}

async function saveExtend() {
  const days = Number(extendEdit.days) || 0;
  if (days < 1 || days > 30) return toast.error("Extra days must be between 1 and 30");
  actionLoading.value = true;
  try {
    const r = await apiPOST("zoho_books_clone.api.eway.extend_validity", {
      name: viewDoc.value.name,
      extra_days: extendEdit.days,
    });
    toast.success(`Validity extended to ${r?.message?.valid_upto || r?.valid_upto}`);
    extendEdit.open = false;
    await openView({ name: viewDoc.value.name });
    await load();
  } catch (e) { toast.error(e.message || "Extend failed"); }
  finally { actionLoading.value = false; }
}

async function doCancel(doc) {
  if (!(await confirm({ title: `Cancel ${doc.ewb_no || doc.name}?`, body: "The EWB will be marked Cancelled and the invoice's EWB number cleared.", okLabel: "Cancel EWB", okStyle: "danger" }))) return;
  actionLoading.value = true;
  try {
    await apiPOST("zoho_books_clone.api.eway.cancel_eway_bill", { name: doc.name });
    toast.success("Cancelled");
    await openView({ name: doc.name });
    await load();
  } catch (e) { toast.error(e.message || "Cancel failed"); }
  finally { actionLoading.value = false; }
}

async function downloadJson(doc) {
  try {
    const r = await apiGET("zoho_books_clone.api.eway.get_eway_json", { name: doc.name });
    const data = r?.message ?? r;
    const blob = new Blob([data.content], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = data.filename;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    toast.error(e.message || "Download failed");
  }
}

async function quickDownload(r) { await downloadJson(r); }

// ── Selection + bulk actions ──────────────────────────────────────────────────
const allChecked = computed(() => sortedRows.value.length > 0 && sortedRows.value.every(r => selected.value.has(r.name)));
function toggle(name) {
  const s = new Set(selected.value);
  s.has(name) ? s.delete(name) : s.add(name);
  selected.value = s;
}
function toggleAll(e) {
  selected.value = e.target.checked
    ? new Set(sortedRows.value.filter(r => r.ui_status === "Generated").map(r => r.name))
    : new Set();
}
function _selectedRows() {
  return sortedRows.value.filter(r => selected.value.has(r.name));
}

async function bulkDownloadJson() {
  const rows = _selectedRows().filter(r => r.ui_status === "Generated");
  if (!rows.length) { toast.error("No Generated EWBs selected"); return; }
  bulkBusy.value = true;
  let ok = 0, fail = 0;
  for (const r of rows) {
    try { await downloadJson(r); ok++; } catch { fail++; }
  }
  bulkBusy.value = false;
  toast.success(`${ok} JSON file(s) downloaded${fail?`, ${fail} failed`:''}`);
}

async function bulkCancelEwb() {
  const rows = _selectedRows().filter(r => r.ui_status === "Generated");
  if (!rows.length) { toast.error("No Generated EWBs selected"); return; }
  if (!(await confirm({ title: `Cancel ${rows.length} E-Way Bill(s)?`, body: "Each EWB will be marked Cancelled and the linked invoice's EWB number cleared.", okLabel: "Cancel All", okStyle: "danger" }))) return;
  bulkBusy.value = true;
  let ok = 0, fail = 0;
  for (const r of rows) {
    try {
      await apiPOST("zoho_books_clone.api.eway.cancel_eway_bill", { name: r.name });
      ok++;
    } catch { fail++; }
  }
  bulkBusy.value = false;
  toast.success(`${ok} cancelled${fail?`, ${fail} failed`:''}`);
  selected.value = new Set();
  await load();
}

async function bulkExtend() {
  const rows = _selectedRows().filter(r => r.ui_status === "Generated" && !r.extended);
  if (!rows.length) { toast.error("No eligible EWBs selected (already extended or not Generated)"); return; }
  if (!(await confirm({ title: `Extend ${rows.length} E-Way Bill(s)?`, body: "Each EWB will be extended by 1 day. This action cannot be undone.", okLabel: "Extend All", okStyle: "primary" }))) return;
  bulkBusy.value = true;
  let ok = 0, fail = 0;
  for (const r of rows) {
    try {
      await apiPOST("zoho_books_clone.api.eway.extend_validity", { name: r.name, extra_days: 1 });
      ok++;
    } catch { fail++; }
  }
  bulkBusy.value = false;
  toast.success(`${ok} extended by 1 day${fail?`, ${fail} failed`:''}`);
  selected.value = new Set();
  await load();
}


function printEwb(doc) {
  const w = window.open("", "_blank", "width=720,height=900");
  if (!w) return toast.error("Pop-up blocked — allow pop-ups to print");
  w.document.write(`<html><head><title>EWB ${doc.ewb_no}</title>
    <style>body{font-family:system-ui,sans-serif;padding:32px;color:#111}
    h1{margin:0 0 4px;font-size:18px}h2{font-size:13px;margin:18px 0 6px;color:#475569;text-transform:uppercase}
    table{width:100%;border-collapse:collapse;font-size:12px}
    td{padding:6px 10px;border-bottom:1px solid #eee}td:first-child{color:#64748b;width:35%}
    .num{font-size:14px;font-weight:700}</style></head><body>
    <h1>E-Way Bill</h1><div class="num">${doc.ewb_no || doc.name}</div>
    <h2>Document</h2><table>
      <tr><td>Invoice</td><td>${doc.invoice_no}</td></tr>
      <tr><td>Invoice Date</td><td>${fmtDate(doc.invoice_date)}</td></tr>
      <tr><td>Customer</td><td>${doc.customer_name || doc.customer || ""}</td></tr>
      <tr><td>Amount</td><td>${fmtCur(doc.grand_total)}</td></tr>
      <tr><td>From GSTIN</td><td>${doc.from_gstin || "—"}</td></tr>
      <tr><td>To GSTIN</td><td>${doc.to_gstin || "—"}</td></tr>
    </table>
    <h2>Transport</h2><table>
      <tr><td>Transporter</td><td>${doc.transporter || "—"}</td></tr>
      <tr><td>Vehicle</td><td>${doc.vehicle_no || "—"}</td></tr>
      <tr><td>Vehicle Type</td><td>${doc.vehicle_type || "Regular"}</td></tr>
      <tr><td>Supply Type</td><td>${doc.supply_type || "Outward"}</td></tr>
      <tr><td>Transaction Type</td><td>${doc.transaction_type || "Regular"}</td></tr>
      <tr><td>Valid Until</td><td>${fmtDate(doc.valid_upto) || "—"}</td></tr>
    </table>
    <script>window.print()<\/script></body></html>`);
  w.document.close();
}

// ----- export (respects selection — same convention as other sales pages)
function exportCSV() {
  const source = selected.value.size
    ? sortedRows.value.filter(r => selected.value.has(r.name))
    : sortedRows.value;
  if (!source.length) return;
  const headers = ["EWB #", "Invoice", "Inv Date", "Customer", "Transporter", "Vehicle", "Valid Until", "Amount", "Status"];
  const rows = source.map((r) => [
    r.ewb_no, r.invoice_no, r.invoice_date, r.customer_name || r.customer,
    r.transporter, r.vehicle_no, r.valid_upto, r.grand_total, r.ui_status,
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
  a.download = `eway-bills-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
</script>

<style scoped>
.ew-page{display:flex;flex-direction:column;gap:16px;padding:24px;}
.ew-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
.ew-search-wrap{display:flex;align-items:center;gap:8px;background:#ffffff;border-radius:8px;padding:6px 12px;min-width:260px;}
.ew-search-input{border:none;background:transparent;outline:none;font:inherit;color:#111827;width:100%;font-size:13px;}
.ew-pills{display:flex;gap:6px;}
.ew-pill{padding:6px 14px;border-radius:20px;font-size:12.5px;font-weight:600;border:1px solid #e5e7eb;background:#fff;color:#6b7280;cursor:pointer;font-family:inherit;display:inline-flex;align-items:center;gap:6px;}
.ew-pill.active{background:#eff6ff;border-color:#2563eb;color:#2563eb;}
.ew-pill-count{background:#e5e7eb;color:#374151;padding:1px 7px;border-radius:10px;font-size:11px;font-weight:700;}
.ew-pill.active .ew-pill-count{background:#dbeafe;color:#1d4ed8;}
.ew-btn-primary{display:inline-flex;align-items:center;gap:6px;background:#2563eb;color:#fff;border:none;border-radius:8px;padding:8px 14px;font-size:13px;font-weight:600;cursor:pointer;}
.ew-btn-primary:hover{background:#1d4ed8;}.ew-btn-primary:disabled{opacity:.5;cursor:not-allowed;}
.ew-btn-ghost{display:inline-flex;align-items:center;gap:6px;background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;padding:8px 12px;font-size:13px;color:#374151;cursor:pointer;}
.ew-btn-ghost:hover{background:#f9fafb;}.ew-btn-ghost:disabled{opacity:.5;cursor:not-allowed;}

.ew-summary{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;}
.ew-sum-card{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:14px 16px;}
.ew-sum-card.accent{background:linear-gradient(135deg,#eff6ff,#fff);border-color:#bfdbfe;}
.ew-sum-card.warn{background:linear-gradient(135deg,#fffbeb,#fff);border-color:#fde68a;}
.ew-sum-card.danger{background:linear-gradient(135deg,#fef2f2,#fff);border-color:#fecaca;}
.ew-sum-lbl{font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px;font-weight:600;}
.ew-sum-val{font-size:20px;font-weight:700;color:#111827;}
.green{color:#16a34a!important;}.orange{color:#ea580c!important;}.red{color:#dc2626!important;}.blue{color:#2563eb!important;}

.ew-card{background:#fff;border:1px solid #e5e7eb;border-radius:10px;overflow:scroll;}
.ew-table{width:100%;border-collapse:collapse;font-size:13px;}
.ew-table th{background:#f9fafb;border-bottom:1px solid #e5e7eb;padding:10px 12px;font-size:11.5px;font-weight:600;color:#374151;text-align:left;white-space:nowrap;}
.ew-table th.sortable{cursor:pointer;user-select:none;}.ew-table th.sortable:hover{color:#2563eb;}
.ta-r{text-align:right!important;}
.ew-row td{padding:10px 12px;border-bottom:1px solid #f3f4f6;cursor:pointer;vertical-align:middle;}
.ew-row:last-child td{border-bottom:none;}.ew-row:hover td{background:#f9fafb;}
.ew-code{font-size:13px;color:#2563eb;font-weight:600;}
.ew-irn{background:#dbeafe;padding:2px 8px;border-radius:6px;color:#1d4ed8;font-size:11.5px;font-weight:600;}
.mono-sm{font-size:13px;}.text-muted{color:#374151;}
.ew-badge{display:inline-flex;align-items:center;padding:2px 8px;border-radius:10px;font-size:11.5px;font-weight:600;}
.ew-badge-lg{padding:4px 12px;font-size:12.5px;}
.badge-green{background:#dcfce7;color:#16a34a;}
.badge-orange{background:#fff7ed;color:#ea580c;}
.badge-grey{background:#f3f4f6;color:#6b7280;}
.badge-red{background:#fef2f2;color:#dc2626;}
.ew-act-btn{background:transparent;border:1px solid #e5e7eb;border-radius:6px;width:26px;height:26px;display:inline-flex;align-items:center;justify-content:center;cursor:pointer;color:#6b7280;margin-left:4px;}
.ew-act-btn:hover{background:#f3f4f6;color:#2563eb;}
.ew-actions-row{display:inline-flex;align-items:center;gap:4px;justify-content:flex-end;}
.ew-act-del:hover{background:#fef2f2 !important;border-color:#fecaca !important;color:#dc2626 !important;}
.ew-confirm{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#fff;border-radius:16px;padding:28px 28px 22px;box-shadow:0 20px 60px rgba(15,23,42,.18);z-index:61;width:340px;max-width:92vw;display:flex;flex-direction:column;align-items:center;gap:10px;text-align:center;}
.ew-confirm-icon{width:52px;height:52px;border-radius:50%;display:flex;align-items:center;justify-content:center;margin-bottom:4px;}
.ew-confirm-icon.danger{background:#fef2f2;color:#dc2626;}
.ew-confirm-title{font-size:16px;font-weight:700;color:#111827;}
.ew-confirm-sub{font-size:13px;color:#6b7280;line-height:1.5;}
.ew-confirm-actions{display:flex;gap:8px;margin-top:6px;width:100%;}
.ew-confirm-actions .ew-btn-ghost{flex:1;}
.ew-btn-danger{flex:1;background:#dc2626;border:1px solid #dc2626;color:#fff;border-radius:8px;padding:8px 14px;font-size:13px;font-weight:600;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:6px;}
.ew-btn-danger:hover{background:#b91c1c;}
.ew-btn-danger:disabled{opacity:.5;cursor:not-allowed;}
.ew-empty{text-align:center;padding:0!important;cursor:default!important;}
.ew-empty-wrap{padding:48px 20px;display:flex;flex-direction:column;align-items:center;gap:6px;color:#6b7280;}
.ew-empty-icon{color:#cbd5e1;margin-bottom:6px;}
.ew-empty-title{font-size:15px;font-weight:600;color:#374151;}
.ew-empty-sub{font-size:12.5px;max-width:380px;text-align:center;}
.ew-shimmer{height:13px;background:linear-gradient(90deg,#f3f4f6 25%,#e5e7eb 50%,#f3f4f6 75%);border-radius:4px;animation:shimmer 1.2s infinite;background-size:200% 100%;}
@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}

/* Drawers */
.ew-overlay{position:fixed;inset:0;background:rgba(15,23,42,.32);backdrop-filter:blur(2px);z-index:40;}
.ew-drawer{position:fixed;top:0;right:-560px;bottom:0;width:560px;background:#fff;border-left:1px solid #e5e7eb;box-shadow:-12px 0 32px rgba(15,23,42,.12);z-index:50;display:flex;flex-direction:column;transition:right .24s cubic-bezier(.32,.72,0,1);}
.ew-drawer.open{right:0;}
.ew-view-drawer{width:530px;right:-530px;}.ew-view-drawer.open{right:0;}

.ew-dheader{display:flex;align-items:flex-start;justify-content:space-between;padding:18px 20px;border-bottom:1px solid #e5e7eb;flex-shrink:0;background:linear-gradient(135deg,#eff6ff 0%,#dbeafe 100%);}
.ew-dheader-left{display:flex;align-items:flex-start;gap:12px;}
.ew-dheader-ico{width:38px;height:38px;border-radius:10px;background:#fff;border:1px solid rgba(37,99,235,.18);display:inline-flex;align-items:center;justify-content:center;color:#2563eb;box-shadow:0 1px 3px rgba(15,23,42,.06);flex-shrink:0;}
.ew-dheader-title{font-size:15px;font-weight:700;color:#111827;letter-spacing:-0.01em;}
.ew-dheader-sub{font-size:12px;color:#475569;margin-top:3px;font-weight:500;}
.ew-dclose{background:rgba(255,255,255,.6);border:none;cursor:pointer;color:#475569;width:32px;height:32px;border-radius:8px;display:inline-flex;align-items:center;justify-content:center;transition:background .15s;}
.ew-dclose:hover{background:#fff;color:#111827;}

.ew-dbody{flex:1;overflow-y:auto;padding:18px 20px;display:flex;flex-direction:column;gap:18px;background:#f8fafc;}
.ew-ctx-card{display:flex;align-items:center;gap:12px;background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:12px 14px;box-shadow:0 1px 2px rgba(15,23,42,.04);}
.ew-ctx-ico{width:36px;height:36px;border-radius:8px;background:#eff6ff;color:#2563eb;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;}
.ew-ctx-doctype{font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.04em;font-weight:600;}
.ew-ctx-name{font-size:13px;color:#0f172a;font-weight:600;margin-top:1px;}
.ew-ctx-meta{text-align:right;display:flex;flex-direction:column;gap:2px;flex-shrink:0;}
.ew-ctx-party{font-size:12px;color:#475569;font-weight:600;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.ew-ctx-amount{font-size:14px;font-weight:700;color:#0f172a;}
.mono{font-size:13px;}

.ew-section{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:12px;box-shadow:0 1px 2px rgba(15,23,42,.03);}
.ew-section-hdr{display:flex;align-items:center;gap:8px;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:#0f172a;}
.ew-section-hdr svg{color:#2563eb;}
.ew-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
.ew-field{display:flex;flex-direction:column;gap:4px;}
.ew-flbl{font-size:12px;font-weight:600;color:#374151;}
.req{color:#dc2626;}
.ew-input{border:1px solid #e2e8f0;border-radius:8px;padding:8px 12px;font:inherit;font-size:13px;outline:none;background:#fff;color:#0f172a;transition:border-color .15s, box-shadow .15s;}
.ew-input:hover:not(:disabled){border-color:#cbd5e1;}
.ew-input:focus{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.12);}
.ew-plan-hint{background:#eff6ff;border:1px solid #bfdbfe;color:#1d4ed8;padding:8px 12px;border-radius:8px;font-size:12px;display:flex;align-items:center;gap:8px;}
.ew-dfooter{display:flex;align-items:center;justify-content:flex-end;gap:8px;padding:14px 20px;border-top:1px solid #e5e7eb;background:#fff;flex-shrink:0;}

/* Pending invoice picker */
.ew-pending-list{display:flex;flex-direction:column;gap:6px;}
.ew-pending-item{display:flex;align-items:center;gap:12px;padding:10px 14px;background:#fff;border:1px solid #e5e7eb;border-radius:8px;cursor:pointer;transition:border-color .15s, box-shadow .15s;}
.ew-pending-item:hover{border-color:#2563eb;box-shadow:0 1px 4px rgba(37,99,235,.10);}
.ew-pending-inv{font-weight:700;color:#2563eb;}
.ew-pending-meta{font-size:11.5px;color:#6b7280;margin-top:2px;}
.ew-pending-amount{font-size:14px;font-weight:700;color:#0f172a;}
.ew-tab-empty{padding:24px;text-align:center;color:#9ca3af;font-size:13px;}

/* View drawer header */
.ew-view-head{padding:20px;border-bottom:1px solid #e5e7eb;flex-shrink:0;background:linear-gradient(135deg,#eff6ff 0%,#dbeafe 100%);}
.ew-view-head.cancelled{background:linear-gradient(135deg,#f3f4f6 0%,#e5e7eb 100%);}
.ew-view-head.expired{background:linear-gradient(135deg,#fef2f2 0%,#fecaca 100%);}
.ew-view-head-row{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;}
.ew-view-num{font-size:18px;font-weight:700;color:#111827;}
.ew-view-sub{font-size:12.5px;color:#475569;margin-top:2px;}
.ew-view-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:16px;}
.ew-view-stats > div{background:rgba(255,255,255,.55);border-radius:8px;padding:8px 10px;}
.vh-lbl{font-size:10.5px;color:#475569;text-transform:uppercase;letter-spacing:.05em;font-weight:600;}
.vh-val{font-size:15px;font-weight:700;color:#0f172a;margin-top:2px;}

.ew-view-actbar{display:flex;flex-wrap:wrap;gap:6px;padding:10px 20px;border-bottom:1px solid #e5e7eb;background:#fff;flex-shrink:0;}
.ew-va-btn{display:inline-flex;align-items:center;gap:5px;border:1px solid #e5e7eb;background:#fff;color:#374151;border-radius:7px;padding:6px 11px;font-size:12.5px;font-weight:600;cursor:pointer;}
.ew-va-btn:hover:not(:disabled){background:#f9fafb;border-color:#cbd5e1;}
.ew-va-btn:disabled{opacity:.45;cursor:not-allowed;}
.ew-va-danger{color:#dc2626;border-color:#fecaca;}.ew-va-danger:hover:not(:disabled){background:#fef2f2;}

/* Collapsible generate drawer cards */
.ew-gen-card{background:#fff;border:1px solid #e3e8ef;border-radius:10px;}
.ew-gen-card-header{display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid #e8ecf0;cursor:pointer;user-select:none;}
.ew-gen-card-header:hover{background:#f8fafc;}
.ew-gen-card-title{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:700;color:#1a1a2e;letter-spacing:.01em;}
.ew-gen-card-title-icon{width:20px;height:20px;display:flex;align-items:center;justify-content:center;color:#2563eb;flex-shrink:0;}
.ew-gen-card-chevron{color:#9ca3af;transition:transform .2s;display:inline-flex;}
.ew-gen-card-chevron.collapsed{transform:rotate(-90deg);}
.ew-gen-card-body{padding:16px;}
.ew-gen-card-body.collapsed{display:none;}
/* Key-value row layout for view sections */
.ew-kv-list{display:flex;flex-direction:column;}
.ew-kv-row{display:flex;align-items:center;justify-content:space-between;padding:3px 0;gap:12px;}
.ew-kv-row:last-child{border-bottom:none;}
.ew-kv-lbl{font-size:12px;font-weight:600;color:#111827;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap;flex-shrink:0;}
.ew-kv-val{font-size:13px;color:#374151;text-align:right;}

/* Toolbar button group */
.ew-btn-group{display:flex;gap:8px;margin-left:auto;}

/* ── Mobile card defaults ── */
.ew-mobile-cards { display: none; }
.ew-desktop-table { display: table; }

@media (max-width: 768px) {
  .ew-drawer { width: 100% !important; right: -100% !important; }
  .ew-drawer.open { right: 0 !important; }
  .ew-view-drawer { width: 100% !important; right: -100% !important; }
  .ew-view-drawer.open { right: 0 !important; }
  .ew-desktop-table { display: none !important; }
  .ew-mobile-cards { display: flex; flex-direction: column; gap: 0; background: #f8fafc; }
  .ew-mobile-card { background: #fff; border-bottom: 1px solid #e5e7eb; padding: 12px 14px; cursor: pointer; transition: background .12s; }
  .ew-mobile-card:active { background: #f8f9fc; }
  .ew-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .ew-mc-docno { font-size: 12px; font-weight: 700; color: #2563eb; }
  .ew-mc-mid { font-size: 13.5px; font-weight: 600; color: #1a1d23; margin-bottom: 4px; }
  .ew-mc-meta { display: flex; justify-content: space-between; font-size: 12px; color: #868e96; margin-bottom: 8px; }
  .ew-mc-amount { font-weight: 700; color: #1a1d23; }
  .ew-mc-footer { display: flex; gap: 6px; }
  .ew-mc--skeleton { pointer-events: none; }
  .ew-mc-shimmer { border-radius: 6px; background: linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size: 200% 100%; animation: ew-mc-sh 1.4s infinite; }
  @keyframes ew-mc-sh { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
  .ew-mc-empty { text-align: center; padding: 32px 16px; color: #868e96; font-size: 13px; }
}

@media(max-width:475px) {
  .ew-view-actbar { display: flex; justify-content: space-evenly; }
  .ew-va-btn-text { display: none; }
  .ew-page { padding: 12px 10px 20px !important; gap: 14px !important; box-sizing: border-box !important; background: #fff !important; }
  .ew-view-stats { display: flex; }
  .ew-actions { flex-wrap: wrap !important; gap: 8px !important; margin-bottom: 0 !important; background: #f7f8fa !important; padding: 10px 12px !important; }
  .ew-search-wrap { flex: 1 1 100% !important; min-width: 0 !important; width: 100% !important; box-sizing: border-box !important; border: 1px solid #e2e8f0; }
  .ew-pills { flex-wrap: wrap !important; }
  .ew-btn-group { margin-left: 0 !important; flex-wrap: wrap !important; width: 100% !important; }
  .ew-btn-group .ew-btn-primary { flex: 1 !important; justify-content: center !important; }
}
</style>