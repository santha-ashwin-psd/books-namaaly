<template>
<div class="list-page">
  <!-- Toolbar -->
  <div class="sales-toolbar">
    <div class="sales-search" style="min-width:220px">
      <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
      <input v-model="search" placeholder="Search challans, customers…" class="sales-search-input"/>
    </div>
    <div class="sales-pills">
      <button v-for="t in TABS" :key="t.k" class="sales-pill" :class="{active:tab===t.k}" @click="tab=t.k">
        {{t.l}}
        <span v-if="t.k!=='all'" class="sales-pill-count">{{tabCounts[t.k]}}</span>
      </button>
    </div>
    <div style="margin-left:auto;display:flex;gap:6px">
      <button class="sales-btn-ghost" @click="exportCSV" title="Export CSV"><span v-html="icon('download',13)"></span> CSV</button>
      <button class="sales-btn-ghost" @click="load" title="Refresh"><span v-html="icon('refresh',13)"></span></button>
      <button class="sales-btn-primary" :disabled="!$canWrite('invoices')" :title="!$canWrite('invoices') ? 'Read-only access' : ''" @click="openNew"><span v-html="icon('plus',13)"></span> New Challan</button>
    </div>
  </div>

  <!-- ── KPI Cards ── -->
  <div class="bk-kpi-grid bk-kpi-grid-4">
    <div class="bk-kpi-card bk-kpi-accent clickable" @click="activeTab='all'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#dbeafe"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.8"><rect x="1" y="3" width="15" height="13" rx="1"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Total Challans</div><div class="bk-kpi-value">{{ list.length }}</div><div class="bk-kpi-trend" :class="dcTrends.total.up?'bk-trend-up':'bk-trend-down'">{{ dcTrends.total.up?'↑':'↓' }} {{ dcTrends.total.pct }}% vs last month</div></div></div></div>
    <div class="bk-kpi-card clickable" @click="activeTab='draft'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#f1f5f9"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#6b7280" stroke-width="1.8"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Draft</div><div class="bk-kpi-value bk-kpi-amber">{{ counts.draft }}</div><div class="bk-kpi-trend bk-trend-neutral">pending</div></div></div></div>
    <div class="bk-kpi-card bk-kpi-info clickable" @click="activeTab='toDeliver'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#dbeafe"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.8"><rect x="1" y="3" width="15" height="13" rx="1"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">To Deliver</div><div class="bk-kpi-value bk-kpi-blue">{{ counts.toDeliver }}</div><div class="bk-kpi-trend" :class="dcTrends.deliver.up?'bk-trend-up':'bk-trend-down'">{{ dcTrends.deliver.up?'↑':'↓' }} {{ dcTrends.deliver.pct }}% vs last month</div></div></div></div>
    <div class="bk-kpi-card bk-kpi-success clickable" @click="activeTab='delivered'"><div class="bk-kpi-inner"><div class="bk-kpi-icon" style="background:#dcfce7"><svg width="22" height="22" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="#16a34a" stroke-width="1.8"/><polyline points="7 12.5 10.5 16 17 9" stroke="#16a34a" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></div><div class="bk-kpi-body"><div class="bk-kpi-label">Delivered</div><div class="bk-kpi-value bk-kpi-green">{{ counts.delivered }}</div><div class="bk-kpi-trend" :class="dcTrends.delivered.up?'bk-trend-up':'bk-trend-down'">{{ dcTrends.delivered.up?'↑':'↓' }} {{ dcTrends.delivered.pct }}% vs last month</div></div></div></div>
  </div>
  <!-- ── Mobile KPI Summary Strip (≤480px) ── -->
  <div class="dc-mob-summary">
    <div class="dc-mob-kpi dc-mob-kpi-green">
      <div class="dc-mob-kpi-label">THIS MONTH CHALLANS</div>
      <div class="dc-mob-kpi-val">{{ dcThisMonth }}</div>
    </div>
    <div class="dc-mob-kpi dc-mob-kpi-amber">
      <div class="dc-mob-kpi-label">TO DELIVER</div>
      <div class="dc-mob-kpi-val">{{ counts.toDeliver }}</div>
    </div>
    <div class="dc-mob-kpi dc-mob-kpi-blue">
      <div class="dc-mob-kpi-label">DELIVERED</div>
      <div class="dc-mob-kpi-val">{{ counts.delivered }}</div>
    </div>
  </div>

  <!-- ── Mobile Card List (≤480px) ── -->
  <div class="dc-mob-list">
    <div v-if="loading" class="dc-mob-loading">
      <div v-for="n in 4" :key="n" class="dc-mob-card dc-mob-shimmer">
        <div class="shimmer" style="height:14px;width:55%;border-radius:6px;margin-bottom:8px"></div>
        <div class="shimmer" style="height:11px;width:38%;border-radius:6px;margin-bottom:6px"></div>
        <div class="shimmer" style="height:11px;width:48%;border-radius:6px"></div>
      </div>
    </div>
    <div v-else-if="!sorted.length" class="dc-mob-empty">No challans match your filters</div>
    <template v-else>
      <div v-for="r in paged" :key="r.name" class="dc-mob-card" @click="openView(r)">
        <!-- Card body: left info + right status -->
        <div class="dc-mob-card-body">
          <div class="dc-mob-card-left">
            <div class="dc-mob-challan-no">{{ r.name }}</div>
            <div class="dc-mob-customer">{{ r.customer_name || r.customer || '—' }}</div>
            <div class="dc-mob-date">Date: {{ r.posting_date || '—' }}</div>
          </div>
          <div class="dc-mob-card-divider"></div>
          <div class="dc-mob-card-right">
            <div class="dc-mob-qty">{{ r.total_qty ? r.total_qty + ' qty' : '—' }}</div>
            <span class="inv-status-badge" :class="statusClass(r)">{{ statusLabel(r) }}</span>
          </div>
        </div>
        <!-- Action icons row -->
        <div class="dc-mob-actions" @click.stop>
          <button class="dc-mob-act" @click.stop="openView(r)" title="View">
            <span v-html="icon('eye', 15)"></span>
          </button>
          <button v-if="canEdit(r)" class="dc-mob-act" @click.stop="openEdit(r)" title="Edit">
            <span v-html="icon('edit', 15)"></span>
          </button>
          <button v-if="r._source==='dn' && r.docstatus===0" class="dc-mob-act" @click.stop="submitOne(r)" title="Submit">
            <span v-html="icon('check', 15)"></span>
          </button>
          <button v-if="r._source==='dn' && r.docstatus===1 && r.status!=='Cancelled' && r.status!=='Delivered' && r.status!=='Fully Delivered'" class="dc-mob-act dc-mob-act-cancel" @click.stop="deleteTarget={row:r,mode:'cancel'}" title="Cancel">
            <span v-html="icon('x', 15)"></span>
          </button>
          <button v-if="r._source==='dn' && (r.docstatus===0 || r.docstatus===2 || r.status==='Cancelled')" class="dc-mob-act dc-mob-act-del" @click.stop="deleteTarget={row:r,mode:'delete'}" title="Delete">
            <span v-html="icon('trash', 15)"></span>
          </button>
        </div>
      </div>
    </template>
  </div>



  <!-- Table -->
  <!-- Bulk action bar -->
  <div v-if="selected.size" class="inv-bulk-bar">
    <span class="inv-bulk-count">{{ selected.size }} selected</span>
    <button class="inv-bulk-btn" @click="bulkSubmit" :disabled="bulkBusy">Submit Drafts</button>
    <button class="inv-bulk-btn inv-bulk-danger" @click="bulkCancel" :disabled="bulkBusy">Cancel Submitted</button>
    <button class="inv-bulk-btn inv-bulk-danger" @click="bulkDelete" :disabled="bulkBusy">Delete Drafts</button>
    <button class="inv-bulk-btn" @click="exportCSV" :disabled="bulkBusy">
      <span v-html="icon('download',13)"></span> Export CSV
    </button>
    <button class="inv-bulk-clear" @click="selected = new Set()">✕ Clear</button>
  </div>

  <div class="inv-table-wrap">
    <table class="inv-table">
      <thead>
        <tr>
          <th style="width:32px"><input type="checkbox" @change="toggleAll" :checked="allChecked" /></th>
          <th @click="sort('name')" class="sortable">Challan / SO # <span v-html="sa('name')"></span></th>
          <th @click="sort('customer_name')" class="sortable">Customer <span v-html="sa('customer_name')"></span></th>
          <th @click="sort('posting_date')" class="sortable">Date <span v-html="sa('posting_date')"></span></th>
          <th>Sales Order</th>
          <th>Status</th>
          <th class="ta-r">Qty</th>
          <th style="width:140px;text-align:center">Actions</th>
        </tr>
      </thead>
      <tbody>
        <template v-if="loading">
          <tr v-for="n in 6" :key="n"><td colspan="8" style="padding:14px"><div class="shimmer" style="height:12px"></div></td></tr>
        </template>
        <tr v-else-if="!sorted.length">
          <td colspan="8" class="b-empty">{{search?'No challans match your search':'No delivery challans yet'}}</td>
        </tr>
        <tr v-else v-for="r in paged" :key="r.name" class="inv-row" :class="{selected: selected.has(r.name)}" @click="openView(r)">
          <td @click.stop><input v-if="r._source==='dn'" type="checkbox" :checked="selected.has(r.name)" @change="toggle(r.name)" /></td>
          <td><span class="inv-link">{{r.name}}</span></td>
          <td class="fw-600">{{r.customer_name||r.customer||'—'}}</td>
          <td class="c-muted" style="font-size:13px">{{r.posting_date||'—'}}</td>
          <td class="c-muted mono" style="font-size:13px">{{r.sales_order||r.name||'—'}}</td>
          <td><span class="inv-status-badge" :class="statusClass(r)">{{statusLabel(r)}}</span></td>
          <td class="ta-r c-muted" style="font-size:13px">{{r.total_qty||'—'}}</td>
          <td @click.stop>
            <div class="dc-actions-row">
              <button class="inv-act-btn" @click.stop="openView(r)" title="View"><span v-html="icon('eye',12)"></span></button>
              <button v-if="canEdit(r)" class="inv-act-btn" @click.stop="openEdit(r)" title="Edit"><span v-html="icon('edit',12)"></span></button>
              <button v-if="r._source==='dn' && r.docstatus===0" class="inv-act-btn" @click.stop="submitOne(r)" title="Submit"><span v-html="icon('check',12)"></span></button>
              <button v-if="r._source==='dn' && r.docstatus===1 && r.status!=='Cancelled' && r.status!=='Delivered' && r.status!=='Fully Delivered'" class="inv-act-btn dc-act-cancel" @click.stop="deleteTarget={row:r,mode:'cancel'}" title="Cancel"><span v-html="icon('x',12)"></span></button>
              <button v-if="r._source==='dn' && (r.docstatus===0 || r.docstatus===2 || r.status==='Cancelled')" class="inv-act-btn dc-act-del" @click.stop="deleteTarget={row:r,mode:'delete'}" title="Delete"><span v-html="icon('trash',12)"></span></button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <div v-if="!loading && sorted.length">
    <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="sorted.length" />
  </div>

  <!-- ===== Drawers ===== -->
  <Teleport to="body">

    <!-- VIEW DRAWER -->
    <div v-if="viewOpen" class="inv-drawer-bg" @click.self="viewOpen=false">
      <div class="inv-drawer-panel inv-view-page dc-view-drawer">
        <template v-if="viewDoc">

          <!-- Header -->
          <div class="inv-view-header dc-view-head">
            <div class="dc-vhead-content">
              <div class="dc-vhead-title-row">
                <div class="inv-view-number">{{ viewDoc.name }}</div>
                <span class="inv-hdr-badge" :class="statusClass(viewDoc)">{{ statusLabel(viewDoc) }}</span>
              </div>
              <div class="inv-view-subtitle">Delivery Challan · {{ viewDoc.posting_date }}</div>
            </div>
            <button class="inv-dclose dc-vhead-close" @click="viewOpen=false"><span v-html="icon('x',16)"></span></button>
          </div>

          <!-- Action bar -->
          <div class="inv-action-bar">
            <button v-if="canEdit(viewDoc)" class="inv-ab-btn" @click="openEdit(viewDoc);viewOpen=false">
              <span v-html="icon('edit',13)"></span> Edit
            </button>
            <button v-if="viewDoc.docstatus===0" class="inv-ab-btn inv-ab-primary" @click="submitChallan" :disabled="submitting">
              <span v-html="icon('send',13)"></span> {{ submitting ? 'Submitting…' : 'Submit Challan' }}
            </button>
            <button v-if="viewDoc._source==='dn' && viewDoc.docstatus===1 && viewDoc.status!=='Cancelled' && viewDoc.status!=='Delivered' && viewDoc.status!=='Fully Delivered'"
              class="inv-ab-btn dc-act-cancel" @click="deleteTarget={row:viewDoc,mode:'cancel'}">
              <span v-html="icon('x',13)"></span> Cancel
            </button>
            <button v-if="viewDoc._source==='dn' && (viewDoc.docstatus===0 || viewDoc.docstatus===2 || viewDoc.status==='Cancelled')"
              class="inv-ab-btn dc-act-del" @click="deleteTarget={row:viewDoc,mode:'delete'}">
              <span v-html="icon('trash',13)"></span> Delete
            </button>
          </div>

          <!-- Body -->
          <div class="inv-dbody">

            <!-- Customer & logistics -->
            <div class="dc-view-card">
              <div class="dc-view-card-hdr">Customer & Delivery Details</div>
              <div class="dc-info-grid">
                <div class="dc-info-item">
                  <div class="dc-info-lbl">Customer</div>
                  <div class="dc-info-val dc-info-link">
                    <DocLink doctype="Customer" :name="viewDoc.customer" :mono-style="false">{{ viewDoc.customer_name||viewDoc.customer||'—' }}</DocLink>
                  </div>
                </div>
                <div class="dc-info-item">
                  <div class="dc-info-lbl">Date</div>
                  <div class="dc-info-val">{{ viewDoc.posting_date||'—' }}</div>
                </div>
                <div class="dc-info-item">
                  <div class="dc-info-lbl">Dispatch Warehouse</div>
                  <div class="dc-info-val" :class="viewDoc.set_warehouse?'':'dc-info-empty'">{{ viewDoc.set_warehouse||'—' }}</div>
                </div>
                <div class="dc-info-item">
                  <div class="dc-info-lbl">Total Qty</div>
                  <div class="dc-info-val" style="font-weight:600">{{ (viewDoc.items||[]).reduce((s,i)=>s+flt(i.qty),0)||'—' }}</div>
                </div>
                <div class="dc-info-item">
                  <div class="dc-info-lbl">LR / Tracking #</div>
                  <div class="dc-info-val" :class="viewDoc.lr_no?'':'dc-info-empty'">{{ viewDoc.lr_no||'—' }}</div>
                </div>
                <div class="dc-info-item">
                  <div class="dc-info-lbl">Transporter</div>
                  <div class="dc-info-val" :class="viewDoc.transporter_name?'':'dc-info-empty'">{{ viewDoc.transporter_name||'—' }}</div>
                </div>
                <div v-if="viewDoc.sales_order" class="dc-info-item dc-info-full">
                  <div class="dc-info-lbl">Sales Order</div>
                  <div class="dc-info-val dc-info-link"><DocLink doctype="Sales Order" :name="viewDoc.sales_order" /></div>
                </div>
                <div v-if="viewDoc.billing_address||viewDoc.shipping_address" class="dc-info-item dc-info-full">
                  <div class="view-address-grid">
                    <div v-if="viewDoc.billing_address">
                      <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px">
                        <span v-html="icon('map-pin',12)" style="color:#6b7280"></span>
                        <span style="font-size:10.5px;font-weight:700;text-transform:uppercase;color:#6b7280;letter-spacing:0.5px">Billing Address</span>
                      </div>
                      <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px 14px">
                        <span style="display:inline-block;background:#dbeafe;color:#2563eb;font-size:10px;font-weight:700;text-transform:uppercase;padding:2px 8px;border-radius:20px;letter-spacing:0.4px;margin-bottom:8px">Billing</span>
                        <div style="font-size:13px;color:#374151;line-height:1.65;">{{ displayAddr(viewDoc.billing_address) }}</div>
                      </div>
                    </div>
                    <div v-if="viewDoc.shipping_address">
                      <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px">
                        <span v-html="icon('map-pin',12)" style="color:#6b7280"></span>
                        <span style="font-size:10.5px;font-weight:700;text-transform:uppercase;color:#6b7280;letter-spacing:0.5px">Delivery Address</span>
                      </div>
                      <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px 14px">
                        <span style="display:inline-block;background:#dbeafe;color:#2563eb;font-size:10px;font-weight:700;text-transform:uppercase;padding:2px 8px;border-radius:20px;letter-spacing:0.4px;margin-bottom:8px">Shipping</span>
                        <div style="font-size:13px;color:#374151;line-height:1.65;">{{ displayAddr(viewDoc.shipping_address) }}</div>
                      </div>
                    </div>
                  </div>
                </div>
                <div v-else class="dc-info-item dc-info-full">
                  <div class="dc-info-lbl">Delivery Address</div>
                  <div class="dc-info-val dc-info-empty">—</div>
                </div>
                <div v-if="viewDoc.remarks" class="dc-info-item dc-info-full">
                  <div class="dc-info-lbl">Remarks</div>
                  <div class="dc-info-val" style="color:#6b7280">{{ viewDoc.remarks }}</div>
                </div>
              </div>
            </div>

            <!-- Items -->
            <div class="dc-view-card">
              <div class="dc-view-card-hdr">
                Items
                <span class="dc-item-count">{{ (viewDoc.items||[]).length }} line{{ (viewDoc.items||[]).length!==1?'s':'' }}</span>
              </div>

              <!-- Desktop table (hidden on mobile) -->
              <table class="inv-table dc-items-tbl dc-items-tbl-desktop">
                <thead>
                  <tr>
                    <th style="width:32px">#</th>
                    <th>Item</th>
                    <th>Description</th>
                    <th class="ta-r" style="width:64px">Qty</th>
                    <th style="width:56px">UOM</th>
                    <th v-if="(viewDoc.items||[]).some(i=>i.warehouse)" style="width:110px">Warehouse</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(it,i) in viewDoc.items||[]" :key="it.name||it.item_code" class="inv-row">
                    <td class="dc-row-num">{{ i+1 }}</td>
                    <td>
                      <div style="font-weight:500;color:#111827">{{ it.item_name||it.item_code }}</div>
                      <div v-if="it.item_code&&it.item_name&&it.item_code!==it.item_name" style="font-size:11px;color:#9ca3af">{{ it.item_code }}</div>
                    </td>
                    <td style="color:#6b7280;font-size:12px">{{ it.description||'—' }}</td>
                    <td class="ta-r" style="font-weight:600;font-variant-numeric:tabular-nums">{{ it.qty }}</td>
                    <td style="color:#6b7280">{{ it.uom||'Nos' }}</td>
                    <td v-if="(viewDoc.items||[]).some(i=>i.warehouse)" style="color:#6b7280;font-size:12px">{{ it.warehouse||viewDoc.set_warehouse||'—' }}</td>
                  </tr>
                  <tr v-if="!(viewDoc.items||[]).length">
                    <td colspan="6" style="text-align:center;padding:24px;color:#9ca3af;font-size:13px">No items</td>
                  </tr>
                </tbody>
              </table>

              <!-- Mobile cards (shown only on mobile) -->
              <div class="dc-view-items-mob">
                <div v-if="!(viewDoc.items||[]).length" class="dc-view-items-empty">No items</div>
                <div v-for="(it,i) in viewDoc.items||[]" :key="it.name||it.item_code" class="dc-view-item-card">
                  <div class="dc-vic-num">#{{ i+1 }}</div>
                  <div class="dc-vic-body">
                    <div class="dc-vic-name">{{ it.item_name||it.item_code }}</div>
                    <div v-if="it.item_code&&it.item_name&&it.item_code!==it.item_name" class="dc-vic-code">{{ it.item_code }}</div>
                    <div v-if="it.description" class="dc-vic-desc">{{ it.description }}</div>
                    <div class="dc-vic-meta-row">
                      <div class="dc-vic-meta">
                        <span class="dc-vic-meta-lbl">Qty</span>
                        <span class="dc-vic-meta-val">{{ it.qty }}</span>
                      </div>
                      <div class="dc-vic-meta">
                        <span class="dc-vic-meta-lbl">UOM</span>
                        <span class="dc-vic-meta-val">{{ it.uom||'Nos' }}</span>
                      </div>
                      <div v-if="it.warehouse||viewDoc.set_warehouse" class="dc-vic-meta">
                        <span class="dc-vic-meta-lbl">Warehouse</span>
                        <span class="dc-vic-meta-val">{{ it.warehouse||viewDoc.set_warehouse }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

          </div>

          <!-- Footer -->
          <div class="inv-dfooter delivery-challan-footer">
            <span class="inv-hdr-badge" :class="statusClass(viewDoc)" style="margin-right:auto">{{ statusLabel(viewDoc) }}</span>
            <button class="form-btn form-btn-outline" @click="viewOpen=false">Close</button>
            <button v-if="canEdit(viewDoc)" class="form-btn form-btn-outline" @click="openEdit(viewDoc);viewOpen=false">
              <span v-html="icon('edit',13)"></span> Edit
            </button>
            <button v-if="viewDoc.docstatus===0" class="form-btn form-btn-primary" @click="submitChallan" :disabled="submitting">
              {{ submitting ? 'Submitting…' : 'Submit Challan' }}
            </button>
          </div>

        </template>
      </div>
    </div>

    <!-- CREATE / EDIT DRAWER -->
    <div v-if="formOpen" class="inv-drawer-bg" @click.self="!editingName ? null : formOpen=false">
      <div class="inv-drawer-panel" :class="{'is-add':!editingName}">

        <!-- Header -->
        <div class="inv-dh">
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
            <div class="inv-dh-title">{{ editingName ? 'Edit Challan' : 'New Delivery Challan' }}</div>
            <span v-if="!editingName" class="add-status-badge">Draft</span>
            <span v-if="editingName" class="inv-dh-sub" style="margin-left:4px">{{ editingName }}</span>
          </div>
          <div style="display:flex;align-items:center;gap:8px">
            <button class="inv-dclose" @click="formOpen=false"><span v-html="icon('x',16)"></span></button>
          </div>
        </div>

        <!-- Body -->
        <div class="inv-content-row">
        <div class="inv-dbody">

          <!-- Customer & Date Card -->
          <div class="add-card">
            <div class="add-card-header" @click="collapsed.details=!collapsed.details">
              <div class="add-card-title">
                <span class="add-card-title-icon"><span v-html="icon('user',16)"></span></span>
                Customer & Date
              </div>
              <span class="add-card-chevron" :class="{collapsed:collapsed.details}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
              </span>
            </div>
            <div class="add-card-body" :class="{collapsed:collapsed.details}">
              <div class="inv-fg inv-fg2">
                <div style="grid-column:1/-1">
                  <label class="inv-lbl">Customer <span class="inv-req">*</span></label>
                  <SearchableSelect
                    v-model="form.customer"
                    :options="customers"
                    placeholder="Select customer…"
                    :createable="true"
                    createDoctype="Customer"
                    @search="fetchCustomers"
                    @select="onCustomerSelect"
                  />
                </div>
                <div>
                  <label class="inv-lbl">Date <span class="inv-req">*</span></label>
                  <input class="inv-fi" type="date" v-model="form.posting_date"/>
                </div>
                <div>
                  <label class="inv-lbl">Sales Order (optional)</label>
                  <SearchableSelect
                    v-model="form.sales_order"
                    :options="salesOrders"
                    placeholder="Link to Sales Order…"
                    @search="fetchSalesOrders"
                    @select="onSOSelect"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- Transport Card -->
          <div class="add-card">
            <div class="add-card-header" @click="collapsed.transport=!collapsed.transport">
              <div class="add-card-title">
                <span class="add-card-title-icon"><span v-html="icon('warehouse',16)"></span></span>
                Transport
              </div>
              <span class="add-card-chevron" :class="{collapsed:collapsed.transport}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
              </span>
            </div>
            <div class="add-card-body" :class="{collapsed:collapsed.transport}">
              <div class="inv-fg inv-fg2">
                <div style="grid-column:1/-1">
                  <label class="inv-lbl">Dispatch Warehouse</label>
                  <SearchableSelect v-model="form.set_warehouse" :options="warehouses" placeholder="Ship stock from…" @search="fetchWarehouses" />
                </div>
                <div>
                  <label class="inv-lbl">LR / Tracking #</label>
                  <input class="inv-fi" v-model="form.lr_no" placeholder="e.g. LR12345"/>
                </div>
                <div>
                  <label class="inv-lbl">Transporter</label>
                  <input class="inv-fi" v-model="form.transporter_name" placeholder="e.g. BlueDart, VRL"/>
                </div>
                <!-- Billing Address -->
                <div>
                  <label class="inv-lbl">Billing Address</label>
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
                  <div v-if="selectedBillingAddr" class="po-addr-card">
                    <div class="po-addr-card-body">{{ formatAddress(selectedBillingAddr) }}</div>
                  </div>
                </div>
                <!-- Shipping / Delivery Address -->
                <div>
                  <label class="inv-lbl">Delivery / Shipping Address</label>
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
                  <div v-if="selectedShippingAddr" class="po-addr-card">
                    <div class="po-addr-card-body">{{ formatAddress(selectedShippingAddr) }}</div>
                  </div>
                </div>
                <div style="grid-column:1/-1">
                  <label class="inv-lbl">Remarks</label>
                  <textarea class="inv-fi" v-model="form.remarks" rows="2" maxlength="500" placeholder="Optional remarks" style="resize:vertical"></textarea>
                  <div class="exp-field-hint" :class="{'exp-field-hint-err': (form.remarks||'').length >= 500}">{{ (form.remarks||'').length }}/500 characters</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Items Card -->
          <div class="add-card">
            <div class="add-card-header" @click="collapsed.items=!collapsed.items">
              <div class="add-card-title">
                <span class="add-card-title-icon"><span v-html="icon('box',16)"></span></span>
                Items <span class="inv-req">*</span>
                <span style="font-size:11.5px;color:#6b7280;font-weight:400;letter-spacing:0;text-transform:none">
                  &nbsp;· {{ form.items.length }} line{{ form.items.length!==1?'s':'' }}
                </span>
              </div>
              <div style="display:flex;align-items:center;gap:8px" @click.stop>
                <button class="add-lines-add-btn" @click="addItem">
                  <span v-html="icon('plus',13)"></span> Add Item
                </button>
                <span class="add-card-chevron" :class="{collapsed:collapsed.items}" @click="collapsed.items=!collapsed.items">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
                </span>
              </div>
            </div>
            <div class="add-card-body" :class="{collapsed:collapsed.items}" style="padding:16px 16px 8px">
              <div class="po-item-cards">
                <div v-for="(it,i) in form.items" :key="it._id" class="po-item-card">
                  <!-- Card header: collapse toggle + item name + remove -->
                  <div class="po-item-card-header" @click="it.collapsed=!it.collapsed">
                    <span class="po-item-card-num">#{{ i+1 }}</span>
                    <span class="po-item-card-title">{{ it.item_code || 'Line Item' }}</span>
                    <div class="po-item-card-subtotal">
                      <span class="po-item-card-subtotal-label">QTY</span>
                      <span class="po-item-card-amount dc-qty-val">{{ it.qty || '—' }}</span>
                    </div>
                    <span class="po-item-card-chevron" :class="{collapsed:it.collapsed}">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
                    </span>
                    <button @click.stop="removeItem(i)" class="po-item-card-rm"><span v-html="icon('x',16)"></span></button>
                  </div>
                  <!-- Card body: fields -->
                  <div class="po-item-card-body dc-item-card-body" v-show="!it.collapsed">
                    <div class="po-item-col po-item-col--left">
                      <div class="po-item-field">
                        <label>Item <span class="inv-req">*</span></label>
                        <SearchableSelect
                          v-model="it.item_code"
                          :options="items"
                          placeholder="Search item…"
                          :createable="true"
                          createDoctype="Item"
                          @search="fetchItems"
                          @select="opt => onItemSelect(it, opt)"
                        />
                      </div>
                      <div class="po-item-field" style="margin-top:14px">
                        <label>Description</label>
                        <textarea v-model="it.description" class="inv-fi po-item-desc-ta" rows="4" maxlength="500" placeholder="Enter item description…"></textarea>
                        <div class="exp-field-hint" :class="{'exp-field-hint-err': (it.description||'').length >= 500}">{{ (it.description||'').length }}/500</div>
                      </div>
                    </div>
                    <div class="po-item-col po-item-col--right">
                      <div class="po-item-num-row">
                        <div class="po-item-field">
                          <label>Qty <span class="inv-req">*</span></label>
                          <input class="inv-fi" type="number" v-model.number="it.qty" placeholder="1" min="0.01" step="0.01"/>
                        </div>
                        <div class="po-item-field">
                          <label>UOM</label>
                          <input class="inv-fi" v-model="it.uom" placeholder="Nos"/>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div v-if="!form.items.length" class="dc-items-empty" style="padding:20px 0 8px">No items yet — click Add Item</div>

              <button class="inv-add-line-btn" style="margin-top:12px" @click="addItem">
                <span v-html="icon('plus',12)"></span> Add Item
              </button>
            </div>
          </div>

        </div><!-- /inv-dbody -->
        </div><!-- /inv-content-row -->

        <!-- Footer -->
        <div class="inv-dfooter">
          <div class="add-footer-status">{{ editingName ? 'Editing: ' + editingName : 'New challan — unsaved changes' }}</div>
          <div class="add-footer-actions">
            <button class="add-btn-cancel" @click="formOpen=false" :disabled="saving">Cancel</button>
            <button class="add-btn-draft" @click="saveChallan(0)" :disabled="saving">
              <span v-html="icon('save',13)"></span> {{ saving?'Saving…':'Save Draft' }}
            </button>
            <button class="add-btn-more" @click="saveChallan(1)" :disabled="saving">
              <span v-html="icon('check',13)"></span> {{ saving?'Saving…':'Submit' }}
            </button>
          </div>
        </div>

      </div>
    </div>


    <!-- ADD NEW ADDRESS MODAL -->
    <div v-if="addrModal.open" class="inv-drawer-bg" style="z-index:8050;background:rgba(15,23,42,.35)" @click.self="addrModal.open=false"></div>
    <div v-if="addrModal.open" class="po-apply-dialog" style="z-index:8100">
      <div class="inv-dh" style="border-bottom:1px solid #e5e7eb;padding:16px 20px">
        <div class="inv-dh-title" style="font-size:15px">Add New Address</div>
        <button class="inv-dclose" @click="addrModal.open=false"><span v-html="icon('x',16)"></span></button>
      </div>
      <div class="inv-dbody" style="padding:20px;overflow-y:auto;flex:1">
        <div class="inv-fg inv-fg2">
          <div style="grid-column:1/-1">
            <label class="inv-lbl">Address Title <span class="inv-req">*</span></label>
            <input class="inv-fi" v-model="addrModal.address_title" placeholder="e.g. Head Office, Warehouse"/>
          </div>
          <div style="grid-column:1/-1">
            <label class="inv-lbl">Address Line 1 <span class="inv-req">*</span></label>
            <input class="inv-fi" v-model="addrModal.address_line1" placeholder="Street / Building"/>
          </div>
          <div style="grid-column:1/-1">
            <label class="inv-lbl">Address Line 2</label>
            <input class="inv-fi" v-model="addrModal.address_line2" placeholder="Area / Landmark"/>
          </div>
          <div>
            <label class="inv-lbl">City</label>
            <input class="inv-fi" v-model="addrModal.city" placeholder="City"/>
          </div>
          <div>
            <label class="inv-lbl">Country</label>
            <select class="inv-fi" v-model="addrModal.country" @change="addrModal.state = ''">
              <option value="">— Select Country —</option>
              <option v-for="c in COUNTRIES" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>
          <div>
            <label class="inv-lbl">State</label>
            <select v-if="statesFor(addrModal.country).length" class="inv-fi" v-model="addrModal.state">
              <option value="">— Select State —</option>
              <option v-for="s in statesFor(addrModal.country)" :key="s" :value="s">{{ s }}</option>
            </select>
            <input v-else class="inv-fi" v-model="addrModal.state" placeholder="State"/>
          </div>
          <div>
            <label class="inv-lbl">PIN / Postal Code</label>
            <input class="inv-fi" v-model="addrModal.pincode" placeholder="PIN"/>
          </div>
          <div>
            <label class="inv-lbl">Address Type</label>
            <select class="inv-fi" v-model="addrModal.address_type">
              <option value="Shipping">Shipping</option>
              <option value="Billing">Billing</option>
              <option value="Office">Office</option>
              <option value="Other">Other</option>
            </select>
          </div>
        </div>
      </div>
      <div class="inv-dfooter" style="padding:14px 20px">
        <button class="form-btn form-btn-outline" @click="addrModal.open=false" :disabled="addrModal.saving">Cancel</button>
        <button class="form-btn form-btn-primary" @click="saveNewAddress" :disabled="addrModal.saving">
          {{ addrModal.saving ? 'Saving…' : 'Save Address' }}
        </button>
      </div>
    </div>

    <!-- DELETE / CANCEL CONFIRM DIALOG -->
    <div v-if="deleteTarget" class="inv-drawer-bg" style="z-index:60" @click.self="deleteTarget=null"></div>
    <div v-if="deleteTarget" class="dc-confirm" style="z-index:61">
      <div class="dc-confirm-icon" :class="deleteTarget.mode==='delete'?'danger':'warn'">
        <span v-html="icon(deleteTarget.mode==='delete'?'trash':'x', 20)"></span>
      </div>
      <div class="dc-confirm-title">
        {{ deleteTarget.mode === 'delete' ? 'Delete Challan?' : 'Cancel Challan?' }}
      </div>
      <div class="dc-confirm-sub">
        <template v-if="deleteTarget.mode==='delete'">
          <strong>{{ deleteTarget.row.name }}</strong> will be permanently deleted. This cannot be undone.
        </template>
        <template v-else>
          <strong>{{ deleteTarget.row.name }}</strong> will be cancelled and can no longer be edited.
        </template>
      </div>
      <div class="dc-confirm-actions">
        <button class="b-btn b-btn-ghost" @click="deleteTarget=null" :disabled="deleting">Keep it</button>
        <button class="b-btn" :class="deleteTarget.mode==='delete'?'dc-btn-danger':'dc-btn-warn'"
          @click="confirmDeleteAction" :disabled="deleting">
          {{ deleting ? (deleteTarget.mode==='delete'?'Deleting…':'Cancelling…') : (deleteTarget.mode==='delete'?'Yes, Delete':'Yes, Cancel') }}
        </button>
      </div>
    </div>

  </Teleport>
</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { apiList, apiGet, apiGET, apiPOST, apiSave, apiSubmit, apiDelete, apiCancel, resolveCompany } from "../api/client.js";
import { COUNTRIES, statesFor } from "../composables/useCountryState.js";
import { useRoute } from "vue-router";
import { useToast } from "../composables/useToast.js";
import { useOpenFromQuery } from "../composables/useOpenFromQuery.js";
import { usePagination } from "../composables/usePagination.js";
import DocLink from "../components/DocLink.vue";
import Pagination from "../components/Pagination.vue";
import SummaryStrip from "../components/SummaryStrip.vue";
import { icon } from "../utils/icons.js";
import { flt } from "../utils/format.js";
import SearchableSelect from "../components/SearchableSelect.vue";

const { toast } = useToast();
const route = useRoute();

const TABS = [
  { k: "all",       l: "All" },
  { k: "draft",     l: "Draft" },
  { k: "toDeliver", l: "To Deliver" },
  { k: "delivered", l: "Delivered" },
  { k: "cancelled", l: "Cancelled" },
];

// ── State ─────────────────────────────────────────────────────────────────────
const list        = ref([]);
const loading     = ref(false);
const search      = ref("");
const tab         = ref("all");
const sortCol     = ref("posting_date");
const sortDir     = ref("desc");
const selected    = ref(new Set());
const bulkBusy    = ref(false);

const viewOpen    = ref(false);
const viewDoc     = ref(null);
const submitting  = ref(false);
const deleteTarget = ref(null);  // { row, mode: "delete"|"cancel" }
const deleting     = ref(false);

const formOpen    = ref(false);
const editingName = ref("");
const saving      = ref(false);
const collapsed   = reactive({ details: false, transport: false, items: false });
const customerAddresses = ref([]);
const addrModal = reactive({
  open: false, forField: "shipping", saving: false,
  address_title: "", address_type: "Shipping",
  address_line1: "", address_line2: "", city: "", state: "", pincode: "", country: "India",
});

const selectedBillingAddr  = computed(() => customerAddresses.value.find(a => a.name === form.billing_address_name) || null);
const selectedShippingAddr = computed(() => customerAddresses.value.find(a => a.name === form.shipping_address_name) || null);

// Dropdown option lists
const customers  = ref([]);
const items      = ref([]);
const warehouses = ref([]);
const salesOrders = ref([]);

let _lineId = 1;
const blankItem = () => ({ _id: _lineId++, item_code: "", item_name: "", description: "", qty: 1, uom: "Nos", collapsed: false });

const form = reactive({
  customer: "",
  customer_name: "",
  posting_date: new Date().toISOString().slice(0, 10),
  sales_order: "",
  set_warehouse: "",
  lr_no: "",
  transporter_name: "",
  billing_address: "",
  billing_address_name: "",
  shipping_address: "",
  shipping_address_name: "",
  remarks: "",
  items: [],
});

// ── Counts ────────────────────────────────────────────────────────────────────
const isDelivered = (r) => r.status === "Delivered" || r.status === "Fully Delivered" || (r._source === "dn" && r.docstatus === 1);
const counts = computed(() => ({
  draft:     list.value.filter(r => r.docstatus === 0).length,
  toDeliver: list.value.filter(r => r.docstatus === 1 && !isDelivered(r)).length,
  delivered: list.value.filter(r => isDelivered(r)).length,
  cancelled: list.value.filter(r => r.docstatus === 2 || r.status === "Cancelled").length,
}));
const _dcYM  = () => { const d=new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; };
const _dcLYM = () => { const d=new Date(); d.setMonth(d.getMonth()-1); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; };
const _dcTr  = (a,b) => { if(!b&&!a) return {pct:0,up:true}; if(!b) return {pct:100,up:true}; const p=Math.round((a-b)/b*100); return {pct:Math.abs(p),up:p>=0}; };
const dcThisMonth = computed(()=>list.value.filter(r=>(r.posting_date||'').startsWith(_dcYM())).length);
const dcTrends = computed(()=>({
  total:     _dcTr(dcThisMonth.value, list.value.filter(r=>(r.posting_date||'').startsWith(_dcLYM())).length),
  deliver:   _dcTr(counts.value.toDeliver, list.value.filter(r=>(r.posting_date||'').startsWith(_dcLYM())&&r.docstatus===1&&!isDelivered(r)).length),
  delivered: _dcTr(counts.value.delivered, list.value.filter(r=>(r.posting_date||'').startsWith(_dcLYM())&&isDelivered(r)).length),
}));

const tabCounts = computed(() => ({
  draft:     counts.value.draft,
  toDeliver: counts.value.toDeliver,
  delivered: counts.value.delivered,
  cancelled: counts.value.cancelled,
}));

// ── Status helpers ────────────────────────────────────────────────────────────
function statusLabel(r) {
  if (r.docstatus === 2 || r.status === "Cancelled") return "Cancelled";
  if (r.status === "Delivered" || r.status === "Fully Delivered") return "Delivered";
  if (r.status === "Partially Delivered") return "Partial";
  // A real Delivery Note (_source==='dn') that is submitted IS the delivery —
  // its own status field is a lifecycle state ("Submitted"), not a delivery-
  // progress state, so treat submitted real DNs as Delivered rather than
  // falling through to the derived-SO "To Deliver" label.
  if (r._source === "dn" && r.docstatus === 1) return "Delivered";
  if (r.docstatus === 1) return "To Deliver";
  return "Draft";
}
function statusClass(r) {
  if (r.docstatus === 2 || r.status === "Cancelled") return "b-badge-muted";
  if (r.status === "Delivered" || r.status === "Fully Delivered") return "b-badge-green";
  if (r.status === "Partially Delivered") return "b-badge-yellow";
  if (r._source === "dn" && r.docstatus === 1) return "b-badge-green";
  if (r.docstatus === 1) return "b-badge-blue";
  return "b-badge-orange";
}
function dcHeadClass(r) {
  if (r.docstatus === 2 || r.status === "Cancelled") return "cancelled";
  if (r.status === "Delivered" || r.status === "Fully Delivered") return "delivered";
  if (r._source === "dn" && r.docstatus === 1) return "delivered";
  return "";
}
function canEdit(r) {
  return r.docstatus === 0;
}

// ── Load ──────────────────────────────────────────────────────────────────────
async function load() {
  loading.value = true;
  try {
    const company = await resolveCompany();

    // 1) Real Delivery Notes (submitted doctype)
    const dnRows = await apiList("Delivery Note", {
      fields: ["name", "customer", "customer_name", "posting_date", "delivery_date",
               "sales_order", "status", "total_qty", "lr_no", "transporter_name", "docstatus"],
      filters: [["company", "=", company]],
      limit: 500,
      order: "posting_date desc, creation desc",
    }).catch(() => []);

    // 2) Sales Orders that are Submitted and not yet fully delivered
    //    (docstatus=1 = Submitted in Frappe; status can be "To Deliver", "Partially Delivered", etc.)
    const soRows = await apiList("Sales Order", {
      fields: ["name", "customer", "customer_name", "transaction_date", "delivery_date",
               "status", "grand_total", "docstatus"],
      filters: [
        ["company", "=", company],
        ["status", "in", ["To Deliver", "Partially Delivered", "Submitted"]],
      ],
      limit: 500,
      order: "transaction_date desc, creation desc",
    }).catch(() => []);

    // Normalise DN rows
    const dnNormalised = dnRows.map(r => ({
      _source:       "dn",
      name:          r.name,
      customer:      r.customer,
      customer_name: r.customer_name,
      posting_date:  r.posting_date || r.delivery_date,
      sales_order:   r.sales_order || "",
      lr_no:         r.lr_no || "",
      transporter_name: r.transporter_name || "",
      status:        r.status || (r.docstatus === 1 ? "To Deliver" : "Draft"),
      docstatus:     r.docstatus,
      total_qty:     flt(r.total_qty),
    }));

    // Sales Orders — only include those that don't already have a matching DN
    const dnSONames = new Set(dnNormalised.map(r => r.sales_order).filter(Boolean));
    const soNormalised = soRows
      .filter(r => !dnSONames.has(r.name))
      .map(r => ({
        _source:       "so",
        name:          r.name,          // SO name shown as the "challan" reference
        customer:      r.customer,
        customer_name: r.customer_name,
        posting_date:  r.delivery_date || r.transaction_date,
        sales_order:   r.name,
        lr_no:         "",
        transporter_name: "",
        status:        r.status === "Partially Delivered" ? "Partially Delivered" : "To Deliver",
        docstatus:     1,
        total_qty:     null,
      }));

    list.value = [...dnNormalised, ...soNormalised];
  } catch (e) {
    console.warn("DC load failed:", e.message);
    list.value = [];
  } finally {
    loading.value = false;
  }
}

// ── Filtering / sorting ───────────────────────────────────────────────────────
const filtered = computed(() => {
  let r = list.value;
  if (tab.value === "draft")     r = r.filter(x => x.docstatus === 0);
  else if (tab.value === "toDeliver") r = r.filter(x => x.docstatus === 1 && !isDelivered(x));
  else if (tab.value === "delivered") r = r.filter(x => isDelivered(x));
  else if (tab.value === "cancelled") r = r.filter(x => x.docstatus === 2 || x.status === "Cancelled");
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    r = r.filter(x =>
      (x.name || "").toLowerCase().includes(q) ||
      (x.customer_name || x.customer || "").toLowerCase().includes(q) ||
      (x.sales_order || "").toLowerCase().includes(q)
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

const { page, pageSize, paged } = usePagination(sorted, { storageKey: "delivery-challans" });

function sort(col) {
  if (sortCol.value === col) sortDir.value = sortDir.value === "asc" ? "desc" : "asc";
  else { sortCol.value = col; sortDir.value = "asc"; }
}
function sa(col) {
  if (sortCol.value !== col) return '<span style="color:#d1d5db">⇅</span>';
  return sortDir.value === "asc" ? "↑" : "↓";
}

// ── View ──────────────────────────────────────────────────────────────────────
async function openView(r) {
  viewOpen.value = true;
  viewDoc.value = { ...r, items: [] };
  try {
    if (r._source === "dn") {
      // Real Delivery Note — fetch full doc
      const doc = await apiGet("Delivery Note", r.name);
      viewDoc.value = {
        ...r,
        items:                doc?.items || [],
        remarks:              doc?.remarks || r.remarks || "",
        set_warehouse:        doc?.set_warehouse || "",
        shipping_address:     doc?.shipping_address || doc?.customer_address || "",
        shipping_address_name:doc?.shipping_address_name || "",
        billing_address:      doc?.billing_address || "",
        billing_address_name: doc?.billing_address_name || "",
        contact_display:      doc?.contact_display || "",
        vehicle_no:           doc?.vehicle_no || "",
        lr_date:              doc?.lr_date || "",
      };
    } else {
      // Sales Order — fetch delivered lines
      const lines = await apiGET("zoho_books_clone.api.docs.get_delivery_challan_lines", { sales_order: r.name }).catch(() => []);
      viewDoc.value = { ...r, items: lines || [] };
    }
  } catch (e) {
    console.warn("DC view load failed:", e.message);
  }
}

async function submitChallan() {
  if (!viewDoc.value) return;
  submitting.value = true;
  try {
    await apiSubmit("Delivery Note", viewDoc.value.name);
    toast.success("Challan submitted");
    viewOpen.value = false;
    await load();
  } catch (e) { toast.error(e.message || "Submit failed"); }
  finally { submitting.value = false; }
}

// ── Selection + bulk actions ──────────────────────────────────────────────────
const allChecked = computed(() => {
  const dnRows = sorted.value.filter(r => r._source === "dn");
  return dnRows.length > 0 && dnRows.every(r => selected.value.has(r.name));
});
function toggle(name) {
  const s = new Set(selected.value);
  s.has(name) ? s.delete(name) : s.add(name);
  selected.value = s;
}
function toggleAll(e) {
  selected.value = e.target.checked
    ? new Set(sorted.value.filter(r => r._source === "dn").map(r => r.name))
    : new Set();
}
function selectedRows() {
  return sorted.value.filter(r => r._source === "dn" && selected.value.has(r.name));
}
async function submitOne(r) {
  try {
    await apiSubmit("Delivery Note", r.name);
    toast.success(`${r.name} submitted`);
    await load();
  } catch (e) { toast.error(e.message || "Submit failed"); }
}
async function bulkSubmit() {
  const rows = selectedRows().filter(r => r.docstatus === 0);
  if (!rows.length) { toast.error("No draft challans selected"); return; }
  bulkBusy.value = true;
  let ok = 0, fail = 0;
  for (const r of rows) {
    try { await apiSubmit("Delivery Note", r.name); ok++; } catch { fail++; }
  }
  bulkBusy.value = false;
  toast.success(`${ok} submitted${fail?`, ${fail} failed`:''}`);
  selected.value = new Set();
  await load();
}
async function bulkCancel() {
  const rows = selectedRows().filter(r => r.docstatus === 1 && r.status !== "Cancelled" && r.status !== "Delivered" && r.status !== "Fully Delivered");
  if (!rows.length) { toast.error("No submitted challans selected"); return; }
  bulkBusy.value = true;
  let ok = 0, fail = 0;
  for (const r of rows) {
    try { await apiCancel("Delivery Note", r.name); ok++; } catch { fail++; }
  }
  bulkBusy.value = false;
  toast.success(`${ok} cancelled${fail?`, ${fail} failed`:''}`);
  selected.value = new Set();
  await load();
}
async function bulkDelete() {
  const rows = selectedRows().filter(r => r.docstatus === 0 || r.docstatus === 2 || r.status === "Cancelled");
  if (!rows.length) { toast.error("Only drafts and cancelled rows can be deleted"); return; }
  bulkBusy.value = true;
  let ok = 0, fail = 0;
  for (const r of rows) {
    try { await apiDelete("Delivery Note", r.name); ok++; } catch { fail++; }
  }
  bulkBusy.value = false;
  toast.success(`${ok} deleted${fail?`, ${fail} failed`:''}`);
  selected.value = new Set();
  await load();
}
function exportCSV() {
  // Selection-aware: if rows are selected export those, else export filtered view.
  // Only "real" DN rows (not derived SO rows) are exported — derived rows
  // don't have transporter/LR data anyway.
  const source = selected.value.size
    ? sorted.value.filter(r => r._source === "dn" && selected.value.has(r.name))
    : sorted.value.filter(r => r._source === "dn");
  if (!source.length) { toast.error("Nothing to export"); return; }
  const headers = ["Challan #","Customer","Date","Sales Order","Status","Qty","LR / Tracking","Transporter"];
  const lines = source.map(r => [
    r.name, r.customer_name || r.customer || "", r.posting_date || "",
    r.sales_order || "", statusLabel(r), r.total_qty || "",
    r.lr_no || "", r.transporter_name || "",
  ]);
  const esc = v => { const s = v == null ? "" : String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  const csv = "﻿" + [headers, ...lines].map(r => r.map(esc).join(",")).join("\r\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `delivery-challans-${new Date().toISOString().slice(0,10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
  toast.success(`${source.length} row(s) exported`);
}

// ── Open New / Edit ───────────────────────────────────────────────────────────
function resetForm() {
  Object.assign(form, {
    customer: "",
    customer_name: "",
    posting_date: new Date().toISOString().slice(0, 10),
    sales_order: "",
    set_warehouse: "",
    lr_no: "",
    transporter_name: "",
    billing_address: "",
    billing_address_name: "",
    shipping_address: "",
    shipping_address_name: "",
    remarks: "",
    items: [blankItem()],
  });
  customerAddresses.value = [];
}

function openNew() {
  editingName.value = "";
  resetForm();
  fetchCustomers("");
  fetchItems("");
  fetchWarehouses("");
  fetchSalesOrders("");
  formOpen.value = true;
}

async function openEdit(r) {
  editingName.value = r.name;
  resetForm();
  fetchCustomers("");
  fetchItems("");
  fetchWarehouses("");
  fetchSalesOrders("");
  formOpen.value = true;

  // Pre-fill from existing doc
  Object.assign(form, {
    customer:              r.customer || "",
    customer_name:         r.customer_name || r.customer || "",
    posting_date:          r.posting_date || new Date().toISOString().slice(0, 10),
    sales_order:           r.sales_order || "",
    lr_no:                 r.lr_no || "",
    transporter_name:      r.transporter_name || "",
    billing_address:       r.billing_address || "",
    billing_address_name:  r.billing_address_name || "",
    shipping_address:      r.shipping_address || "",
    shipping_address_name: r.shipping_address_name || "",
    remarks:               r.remarks || "",
    items:                 [],
  });

  if (r._source === "dn") {
    try {
      const doc = await apiGet("Delivery Note", r.name);
      form.items = (doc?.items || []).map(it => ({
        _id:         _lineId++,
        item_code:   it.item_code || "",
        item_name:   it.item_name || "",
        description: it.description || "",
        qty:         flt(it.qty) || 1,
        uom:         it.uom || "Nos",
        collapsed:   false,
      }));
      if (doc?.remarks)               form.remarks = doc.remarks;
      if (doc?.set_warehouse)         form.set_warehouse = doc.set_warehouse;
      if (doc?.shipping_address)      form.shipping_address = doc.shipping_address;
      if (doc?.shipping_address_name) form.shipping_address_name = doc.shipping_address_name;
      if (doc?.billing_address)       form.billing_address = doc.billing_address;
      if (doc?.billing_address_name)  form.billing_address_name = doc.billing_address_name;
      if (doc?.lr_no)                 form.lr_no = doc.lr_no;
      if (doc?.transporter_name)      form.transporter_name = doc.transporter_name;
      // Fetch customer addresses after restoring link fields
      if (form.customer) {
        await fetchCustomerAddresses(form.customer);
      }
    } catch {}
  } else if (r._source === "so") {
    try {
      const lines = await apiGET("zoho_books_clone.api.docs.get_delivery_challan_lines", { sales_order: r.name }).catch(() => []);
      form.items = (lines || []).map(it => ({
        _id:         _lineId++,
        item_code:   it.item_code || "",
        item_name:   it.item_name || "",
        description: it.description || "",
        qty:         flt(it.delivered_qty || it.qty) || 1,
        uom:         it.uom || "Nos",
        collapsed:   false,
      }));
    } catch {}
  }
  if (!form.items.length) form.items = [blankItem()];
}

// ── Dropdown fetchers ─────────────────────────────────────────────────────────
async function fetchCustomers(q = "") {
  try {
    const f = [["disabled", "=", 0]];
    if (q) f.push(["customer_name", "like", "%" + q + "%"]);
    const r = await apiList("Customer", {
      fields: ["name", "customer_name"],
      filters: f, limit: 30, order: "customer_name asc",
    });
    customers.value = (r || []).map(x => ({ ...x, label: x.customer_name || x.name, value: x.name }));
  } catch { customers.value = []; }
}

async function fetchWarehouses(q = "") {
  try {
    const co = await resolveCompany();
    const r = await apiList("Warehouse", {
      fields: ["name", "parent_warehouse"],
      filters: [["company", "=", co], ["is_group", "=", 0], ...(q ? [["name", "like", `%${q}%`]] : [])],
      limit: 30,
    });
    warehouses.value = r.map(x => ({ label: x.parent_warehouse ? `${x.parent_warehouse} / ${x.name}` : x.name, value: x.name }));
  } catch { warehouses.value = []; }
}

async function fetchItems(q = "") {
  try {
    const f = [["disabled", "=", 0], ["has_variants", "=", 0]];
    if (q) f.push(["item_name", "like", "%" + q + "%"]);
    const r = await apiList("Item", {
      fields: ["name", "item_name", "stock_uom", "description"],
      filters: f, limit: 30, order: "item_name asc",
    });
    items.value = (r || []).map(x => ({
      ...x,
      label: x.item_name || x.name,
      value: x.name,
      uom: x.stock_uom || "Nos",
      description: x.description || "",
    }));
  } catch { items.value = []; }
}

async function fetchSalesOrders(q = "") {
  try {
    const company = await resolveCompany();
    const f = [
      ["company", "=", company],
      ["docstatus", "=", 1],
      // Only SOs that still have something left to deliver — excludes
      // Delivered / Invoiced / Closed / Cancelled / draft Sales Orders.
      ["status", "in", ["To Deliver", "Partially Delivered", "Submitted"]],
    ];
    if (form.customer) f.push(["customer", "=", form.customer]);
    if (q) f.push(["name", "like", "%" + q + "%"]);
    const r = await apiList("Sales Order", {
      fields: ["name", "customer", "customer_name", "delivery_date", "status"],
      filters: f, limit: 30, order: "transaction_date desc, creation desc",
    });
    salesOrders.value = (r || []).map(x => ({
      ...x,
      label: x.name + (x.customer_name ? " · " + x.customer_name : ""),
      value: x.name,
    }));
  } catch { salesOrders.value = []; }
}

// ── Customer select: fetch linked addresses + filter SO list ──────────────────
async function onCustomerSelect(opt) {
  const custName = opt?.value ?? opt;
  form.customer_name = opt?.label ?? opt?.customer_name ?? custName ?? "";
  form.sales_order = "";
  salesOrders.value = [];
  form.billing_address = ""; form.billing_address_name = "";
  form.shipping_address = ""; form.shipping_address_name = "";
  if (!custName) return;

  fetchSalesOrders("");
  await fetchCustomerAddresses(custName);
  // Auto-select first billing and shipping addresses
  const firstBilling  = customerAddresses.value.find(a => a.address_type === "Billing")  || customerAddresses.value[0];
  const firstShipping = customerAddresses.value.find(a => a.address_type === "Shipping") || null;
  if (firstBilling)  { form.billing_address_name  = firstBilling.name;  form.billing_address  = formatAddress(firstBilling); }
  if (firstShipping) { form.shipping_address_name = firstShipping.name; form.shipping_address = formatAddress(firstShipping); }
  else if (firstBilling) { form.shipping_address_name = firstBilling.name; form.shipping_address = formatAddress(firstBilling); }
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
  const addrType = field === "billing" ? "Billing" : "Shipping";
  Object.assign(addrModal, { open: true, saving: false, forField: field, address_type: addrType, address_title: "", address_line1: "", address_line2: "", city: "", state: "", pincode: "", country: "India" });
}

async function saveNewAddress() {
  if (!addrModal.address_title.trim()) { toast.error("Address Title is required"); return; }
  if (!addrModal.address_line1.trim()) { toast.error("Address Line 1 is required"); return; }
  addrModal.saving = true;
  try {
    const addrDoc = {
      doctype: "Address",
      address_title: addrModal.address_title,
      address_type:  addrModal.address_type || "Shipping",
      address_line1: addrModal.address_line1,
      address_line2: addrModal.address_line2 || "",
      city:          addrModal.city || "",
      state:         addrModal.state || "",
      pincode:       addrModal.pincode || "",
      country:       addrModal.country || "India",
      links: form.customer ? [{ doctype: "Address", link_doctype: "Customer", link_name: form.customer }] : [],
    };
    const saved = await apiSave(addrDoc);
    toast.success("Address saved");
    await fetchCustomerAddresses(form.customer);
    const newAddr = customerAddresses.value.find(a => a.name === saved?.name) || customerAddresses.value[customerAddresses.value.length - 1];
    if (newAddr) {
      if (addrModal.forField === "billing") { form.billing_address_name = newAddr.name; form.billing_address = formatAddress(newAddr); }
      else { form.shipping_address_name = newAddr.name; form.shipping_address = formatAddress(newAddr); }
    }
    addrModal.open = false;
  } catch (e) { toast.error(e.message || "Failed to save address"); }
  finally { addrModal.saving = false; }
}

// ── SO select: pull items from Sales Order ────────────────────────────────────
async function onSOSelect(opt) {
  const soName = opt?.value ?? opt;
  if (!soName) return;
  try {
    const so = await apiGet("Sales Order", soName);
    if (!form.customer && so?.customer) {
      form.customer = so.customer;
      form.customer_name = so.customer_name || so.customer;
      await onCustomerSelect({ value: so.customer, label: so.customer_name || so.customer });
    } else if (form.customer && !customerAddresses.value.length) {
      await fetchCustomerAddresses(form.customer);
    }
    // Copy addresses from Sales Order if available
    if (so?.billing_address_name) { form.billing_address_name = so.billing_address_name; form.billing_address = so.billing_address || ""; }
    if (so?.shipping_address_name) { form.shipping_address_name = so.shipping_address_name; form.shipping_address = so.shipping_address || ""; }
    if (so?.items?.length) {
      form.items = so.items.map(it => ({
        _id:         _lineId++,
        item_code:   it.item_code || "",
        item_name:   it.item_name || it.item_code || "",
        description: it.description || "",
        qty:         flt(Math.max(0, flt(it.qty) - flt(it.delivered_qty))) || flt(it.qty) || 1,
        uom:         it.uom || "Nos",
        collapsed:   false,
      })).filter(it => it.qty > 0);
      if (!form.items.length) form.items = [blankItem()];
      toast.success(`Loaded ${so.items.length} item(s) from ${soName}`);
    }
    if (so?.delivery_date) form.posting_date = so.delivery_date;
  } catch {}
}

// ── Item select: auto-fill UOM + description ──────────────────────────────────
function onItemSelect(line, opt) {
  const code = opt?.value ?? opt;
  line.item_code = code;
  const found = items.value.find(i => i.value === code || i.name === code);
  if (found) {
    if (found.uom)         line.uom = found.uom;
    if (found.description) line.description = found.description;
    line.item_name = found.label || found.item_name || code;
  }
}

function addItem() { form.items.push(blankItem()); }
function removeItem(i) { if (form.items.length > 1) form.items.splice(i, 1); }

// ── Save ──────────────────────────────────────────────────────────────────────
async function saveChallan(submit) {
  if (!form.customer) { toast.error("Customer is required"); return; }
  const validItems = form.items.filter(it => it.item_code && flt(it.qty) > 0);
  if (!validItems.length) { toast.error("At least one item with qty > 0 is required"); return; }
  if (form.items.some(it => (it.description||'').length > 500)) { toast.error("Item description cannot exceed 500 characters"); return; }
  if ((form.remarks||'').length > 500) { toast.error("Remarks cannot exceed 500 characters"); return; }

  saving.value = true;
  try {
    const company = await resolveCompany();
    const doc = {
      doctype:               "Delivery Note",
      company,
      customer:              form.customer,
      customer_name:         form.customer_name || form.customer,
      posting_date:          form.posting_date,
      sales_order:           form.sales_order || undefined,
      set_warehouse:         form.set_warehouse || "",
      lr_no:                 form.lr_no || "",
      transporter_name:      form.transporter_name || "",
      billing_address:       form.billing_address || "",
      billing_address_name:  form.billing_address_name || "",
      shipping_address:      form.shipping_address || "",
      shipping_address_name: form.shipping_address_name || "",
      remarks:               form.remarks || "",
      items: validItems.map(it => ({
        doctype:    "Delivery Note Item",
        item_code:  it.item_code,
        item_name:  it.item_name || it.item_code,
        description:it.description || "",
        qty:        flt(it.qty),
        uom:        it.uom || "Nos",
        stock_uom:  it.uom || "Nos",
        conversion_factor: 1,
        warehouse:  it.warehouse || form.set_warehouse || "",
      })),
    };
    if (editingName.value) doc.name = editingName.value;

    const saved = await apiSave(doc);
    if (submit && saved?.name) await apiSubmit("Delivery Note", saved.name);

    toast.success(`Challan ${saved?.name || ""} ${submit ? "submitted" : "saved"}`);
    formOpen.value = false;
    await load();
  } catch (e) { toast.error(e.message || "Failed to save"); }
  finally { saving.value = false; }
}

// ── Delete / Cancel ───────────────────────────────────────────────────────────
async function confirmDeleteAction() {
  if (!deleteTarget.value) return;
  const { row, mode } = deleteTarget.value;
  deleting.value = true;
  try {
    if (mode === "delete") {
      await apiDelete("Delivery Note", row.name);
      toast.success(`Challan ${row.name} deleted`);
    } else {
      await apiCancel("Delivery Note", row.name);
      toast.success(`Challan ${row.name} cancelled`);
    }
    deleteTarget.value = null;
    viewOpen.value = false;
    await load();
  } catch (e) {
    toast.error(e.message || (mode === "delete" ? "Delete failed" : "Cancel failed"));
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
</script>

<style scoped>
@import '../styles/list.css';
@import '../styles/view.css';
@import '../styles/edit.css';
@import '../styles/add.css';

/* ── Action bar primary button ── */
.inv-ab-primary { background:#2563eb;border-color:#2563eb;color:#fff; }
.inv-ab-primary:hover { background:#1d4ed8;border-color:#1d4ed8; }

/* ── View cards ── */
.dc-view-card { background:#fff;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;margin-bottom:14px; }
.dc-view-card-hdr { display:flex;align-items:center;justify-content:space-between;padding:10px 16px;background:#f8fafc;border-bottom:1px solid #e5e7eb;font-size:12px;font-weight:700;color:#374151;letter-spacing:.02em; }
.dc-item-count { font-size:11.5px;font-weight:500;color:#6b7280;letter-spacing:0; }

/* ── Info grid (Customer & Date card) ── */
.dc-info-grid { display:grid;grid-template-columns:1fr 1fr;gap:0; }
.dc-info-item { padding:10px 16px;border-bottom:1px solid #f1f5f9; }
.dc-info-item:nth-child(odd) { border-right:1px solid #f1f5f9; }
.dc-info-full { grid-column:1/-1; }
.dc-info-lbl { font-size:10.5px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px; }
.dc-info-val { font-size:13px;color:#111827;line-height:1.4; }
.dc-info-empty { color:#9ca3af !important; }
.dc-info-link a, .dc-info-link span { color:#2563eb;font-weight:500; }

/* ── Items table ── */
.dc-items-tbl { font-size:12.5px; }
.dc-row-num { color:#9ca3af;font-size:11.5px;font-weight:600;text-align:center; }

/* ── Items column grid (edit drawer) ── */
.dc-items-head { display:grid;grid-template-columns:2fr 2fr 80px 80px 32px;gap:8px;background:#f9fafb;padding:6px 10px;border-radius:6px 6px 0 0;font-size:11.5px;font-weight:600;color:#374151;border:1px solid #e5e7eb;border-bottom:none; }
.dc-item-row { display:grid;grid-template-columns:2fr 2fr 80px 80px 32px;gap:8px;padding:6px 0;border-top:1px solid #f3f4f6;align-items:center; }
.dc-items-empty { font-size:12px;color:#868E96;text-align:center;padding:14px;background:#f9fafb;border:1px dashed #e5e7eb;border-radius:8px; }
/* ── Confirm dialog ── */
.dc-confirm { position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#fff;border-radius:16px;padding:28px 28px 22px;box-shadow:0 20px 60px rgba(15,23,42,.18);z-index:61;width:340px;max-width:92vw;display:flex;flex-direction:column;align-items:center;gap:10px;text-align:center; }
.dc-confirm-icon { width:52px;height:52px;border-radius:50%;display:flex;align-items:center;justify-content:center;margin-bottom:4px; }
.dc-confirm-icon.danger { background:#fee2e2;color:#dc2626; }
.dc-confirm-icon.warn { background:#fffbeb;color:#d97706; }
.dc-confirm-title { font-size:16px;font-weight:700;color:#111827; }
.dc-confirm-sub { font-size:13px;color:#6b7280;line-height:1.5; }
.dc-confirm-actions { display:flex;gap:8px;margin-top:6px;width:66%; }
.dc-confirm-actions .form-btn { flex:1;justify-content:center; }
.dc-btn-danger { background:#dc2626;border:1px solid #dc2626;color:#fff;border-radius:8px;padding:8px 14px;font-size:13px;font-weight:600;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:6px; }
.dc-btn-danger:hover { background:#b91c1c;border-color:#b91c1c; }
.dc-btn-danger:disabled,.dc-btn-warn:disabled { opacity:.5;cursor:not-allowed; }
.dc-btn-warn { background:#d97706;border:1px solid #d97706;color:#fff;border-radius:8px;padding:8px 14px;font-size:13px;font-weight:600;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:6px; }
.dc-btn-warn:hover { background:#b45309;border-color:#b45309; }

/* ── Action button hover states ── */
.dc-actions-row { display:flex;align-items:center;justify-content:center;gap:4px;flex-wrap:nowrap; }
.dc-act-del:hover { background:#fef2f2 !important;border-color:#fecaca !important;color:#dc2626 !important; }
.dc-act-cancel:hover { background:#fffbeb !important;border-color:#fde68a !important;color:#d97706 !important; }

/* ── Misc ── */
.b-empty { text-align:center;color:#9ca3af;padding:24px!important; }
.ta-r { text-align:right; }
.fw-600 { font-weight:600; }
.c-muted { color:#6b7280; }
.mono { font-size:13px; }
.req { color:#dc2626; }
.sortable { cursor:pointer;user-select:none; }
.sortable:hover { color:#2563eb; }
.dc-view-drawer { width: 625px; right: -625px; }
/* ══════════════════════════════════════════════
   MOBILE — Items → Card layout (375px & 425px)
   Matches reference screenshot exactly.
   ══════════════════════════════════════════════ */
@media (max-width: 480px) {
  .delivery-challan-footer{
    display: none !important;
  }
  /* ── Hide the 5-column desktop header ── */
  .dc-items-head { display: none; }

  /* ── Each item row → a card ── */
  .dc-item-row {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    align-items: flex-start;
    background: #fff;
    border: 1.5px solid #e2e8f0;
    border-radius: 14px;
    margin: 0 10px 10px;
    padding: 14px;
    gap: 10px 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,.07);
    box-sizing: border-box;
    border-top: none;
    position: relative;
  }

  /* ── Row 1: ITEM — full width ── */
  .dc-item-row > div:nth-child(1) {
    width: 100%;
    order: 1;
    min-width: 0;
  }
  .dc-item-row > div:nth-child(1)::before {
    content: 'ITEM';
    display: block;
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: .07em;
    color: #9ca3af;
    margin-bottom: 5px;
  }

  /* ── Row 2: DESCRIPTION (wide) + DELETE button (narrow) side by side ── */
  .dc-item-row > div:nth-child(2) {
    width: calc(100% - 48px); /* leave 40px + 8px gap for delete */
    order: 2;
    min-width: 0;
  }
  .dc-item-row > div:nth-child(2)::before {
    content: 'DESCRIPTION';
    display: block;
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: .07em;
    color: #9ca3af;
    margin-bottom: 5px;
  }

  /* Delete button: sits next to description INPUT (aligned to bottom) */
  .dc-item-row > div:nth-child(5) {
    width: 40px;
    order: 2;
    display: flex;
    align-items: center;
    justify-content: center;
    align-self: flex-end;   /* ← pushes to bottom of row = next to the input */
    flex-shrink: 0;
    position: static;
  }
  .dc-item-row > div:nth-child(5) .add-line-del {
    opacity: 1 !important;
    background: #fee2e2 !important;
    border: 1.5px solid #fecaca !important;
    border-radius: 8px !important;
    padding: 8px !important;
    color: #dc2626 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
    width: 36px !important;
    height: 36px !important;
    transition: background .15s !important;
  }

  /* ── Row 3: QTY (50%) + UOM (50%) side by side ── */
  .dc-item-row > div:nth-child(3) {
    width: calc(50% - 4px);
    order: 3;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }
  .dc-item-row > div:nth-child(3)::before {
    content: 'QTY';
    display: block;
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: .07em;
    color: #9ca3af;
    margin-bottom: 5px;
  }

  .dc-item-row > div:nth-child(4) {
    width: calc(50% - 4px);
    order: 3;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }
  .dc-item-row > div:nth-child(4)::before {
    content: 'UOM';
    display: block;
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: .07em;
    color: #9ca3af;
    margin-bottom: 5px;
  }

  /* ── All inputs & selects: full width ── */
  .dc-item-row .inv-fi {
    width: 100% !important;
    min-width: 0 !important;
    box-sizing: border-box !important;
    font-size: 13.5px !important;
    padding: 9px 11px !important;
    border-radius: 8px !important;
  }
  .dc-item-row .inv-fi.ta-r { text-align: left !important; }

  /* ── Add new line button ── */
  .add-new-line-row { padding: 8px 10px 10px; border-top: 1px solid #f0f3f7; }
  .add-new-line-btn {
    width: 100%;
    justify-content: center;
    padding: 11px;
    border: 1.5px dashed #d1d5db;
    border-radius: 10px;
    font-size: 13.5px;
    font-weight: 600;
    color: #2563eb;
    background: #f8fafc;
    gap: 6px;
  }

  /* ── VIEW drawer items table → cards ── */
  .dc-items-tbl thead { display: none; }
  .dc-items-tbl,
  .dc-items-tbl tbody { display: block; width: 100%; }

  .dc-items-tbl tbody tr {
    display: grid;
    grid-template-columns: 24px 1fr auto;
    grid-template-rows: auto auto;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    margin-bottom: 8px;
    padding: 10px 12px;
    gap: 3px 10px;
  }
  .dc-items-tbl tbody tr td:nth-child(1) {
    grid-column: 1; grid-row: 1 / 3;
    display: flex; align-items: center;
    padding: 0; border: none;
    font-size: 12px; color: #9ca3af; font-weight: 700;
  }
  .dc-items-tbl tbody tr td:nth-child(2) {
    grid-column: 2; grid-row: 1;
    padding: 0; border: none;
  }
  .dc-items-tbl tbody tr td:nth-child(3) {
    grid-column: 2 / 4; grid-row: 2;
    padding: 0; border: none;
    font-size: 12px; color: #6b7280;
  }
  .dc-items-tbl tbody tr td:nth-child(4) {
    grid-column: 3; grid-row: 1;
    padding: 0; border: none;
    text-align: right;
    font-size: 14px; font-weight: 700; color: #111827;
  }
  .dc-items-tbl tbody tr td:nth-child(5),
  .dc-items-tbl tbody tr td:nth-child(6) { display: none; }
}

/* ═══════════════════════════════════════════════════
   MOBILE CARD LAYOUT — matches Invoices page exactly
   Visible only at ≤ 480px
   ═══════════════════════════════════════════════════ */

/* Hide mobile elements on desktop — must use !important to beat global CSS */
.dc-mob-summary,
.dc-mob-list { display: none !important; }

@media (max-width: 480px) {

  /* ── KPI summary strip ── */
  .dc-mob-summary {
    display: flex !important;
    flex-direction: column;
    gap: 8px;
    padding: 12px 12px 0;
  }
  .dc-mob-kpi {
    border-radius: 10px;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .dc-mob-kpi-green  { background: #f0fdf4; }
  .dc-mob-kpi-amber  { background: #fffbeb; }
  .dc-mob-kpi-blue   { background: #eff6ff; }
  .dc-mob-kpi-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .07em;
    text-transform: uppercase;
    color: #6b7280;
  }
  .dc-mob-kpi-val {
    font-size: 26px;
    font-weight: 800;
    color: #111827;
    line-height: 1.1;
  }

  /* ── Card list wrapper ── */
  .dc-mob-list {
    display: block !important;
    padding: 10px 12px 80px;
  }

  /* ── Single card ── */
  .dc-mob-card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    margin-bottom: 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,.06);
    cursor: pointer;
    overflow: hidden;
    transition: box-shadow .15s;
  }
  .dc-mob-card:active { box-shadow: 0 2px 8px rgba(0,0,0,.1); }

  /* ── Card body: left | divider | right ── */
  .dc-mob-card-body {
    display: flex;
    align-items: stretch;
    padding: 14px 16px 10px;
    gap: 0;
  }
  .dc-mob-card-left {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .dc-mob-challan-no {
    font-size: 14px;
    font-weight: 700;
    color: #111827;
  }
  .dc-mob-customer {
    font-size: 13px;
    font-weight: 500;
    color: #374151;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .dc-mob-date {
    font-size: 12px;
    color: #6b7280;
    margin-top: 2px;
  }

  /* Vertical divider */
  .dc-mob-card-divider {
    width: 1px;
    background: #e5e7eb;
    margin: 0 14px;
    flex-shrink: 0;
  }

  /* Right side: qty + status badge */
  .dc-mob-card-right {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    justify-content: center;
    gap: 6px;
    min-width: 80px;
    flex-shrink: 0;
  }
  .dc-mob-qty {
    font-size: 14px;
    font-weight: 700;
    color: #111827;
  }

  /* ── Action icons row ── */
  .dc-mob-actions {
    display: flex;
    align-items: center;
    gap: 2px;
    padding: 6px 14px 10px;
    border-top: 1px solid #f3f4f6;
    margin-top: 4px;
  }
  .dc-mob-act {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border: none;
    background: transparent;
    border-radius: 8px;
    color: #6b7280;
    transition: background .13s, color .13s;
  }
  .dc-mob-act:hover,
  .dc-mob-act:active { background: #f1f5f9; color: #111827; }
  .dc-mob-act-del { color: #dc2626 !important; }
  .dc-mob-act-del:hover { background: #fee2e2 !important; }

  /* ── Shimmer / empty states ── */
  .dc-mob-shimmer {
    padding: 16px;
    pointer-events: none;
  }
  .dc-mob-empty {
    text-align: center;
    padding: 40px 20px;
    color: #9ca3af;
    font-size: 13px;
  }

  /* Hide the desktop table and stat grid on mobile */
  .inv-table-wrap,
  .bk-stat-grid {
    display: none !important;
  }
  /* bk-kpi-grid is a global class — needs :deep() to pierce scoped styles */
  :deep(.bk-kpi-grid),
  :deep(.bk-kpi-grid-4) {
    display: none !important;
  }
}

@media (max-width: 425px) {
  .dc-mob-summary { padding: 10px 10px 0; }
  .dc-mob-kpi { padding: 12px 14px; }
  .dc-mob-kpi-val { font-size: 24px; }
  .dc-mob-list { padding: 8px 10px 80px; }
  .dc-mob-card-body { padding: 12px 14px 8px; }
}

@media (max-width: 375px) {
  .dc-mob-summary { padding: 8px 8px 0; gap: 6px; }
  .dc-mob-kpi { padding: 11px 12px; }
  .dc-mob-kpi-val { font-size: 22px; }
  .dc-mob-list { padding: 7px 8px 80px; }
  .dc-mob-card-body { padding: 11px 12px 8px; }
  .dc-mob-challan-no { font-size: 13px; }
  .dc-mob-customer { font-size: 12.5px; }
  .dc-mob-date { font-size: 11.5px; }
}

/* ── View drawer header layout ── */
.dc-view-head { position: relative; }
.dc-vhead-content { flex: 1; min-width: 0; }
.dc-vhead-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 3px;
}
.dc-vhead-close {
  position: absolute;
  top: 12px;
  right: 12px;
  flex-shrink: 0;
}

/* ── Mobile cancel button in card actions ── */
.dc-mob-act-cancel { color: #d97706 !important; }
.dc-mob-act-cancel:hover { background: #fef3c7 !important; }

/* ── Item card: qty display in header ── */
.dc-qty-val {
  font-size: 16px !important;
}

/* ── Item card body: 60/40 split (description left, qty+uom right) ── */
.dc-item-card-body {
  grid-template-columns: 3fr 2fr !important;
}

/* ── Mobile view-drawer item cards ── */
.dc-view-items-mob { display: none; }

@media (max-width: 480px) {
  /* Hide desktop table in view drawer items section */
  .dc-items-tbl-desktop { display: none !important; }

  /* Show mobile item cards */
  .dc-view-items-mob {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 4px 0 2px;
  }
  .dc-view-items-empty {
    text-align: center;
    color: #9ca3af;
    font-size: 13px;
    padding: 20px 0;
  }
  .dc-view-item-card {
    display: flex;
    gap: 10px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 12px 14px;
  }
  .dc-vic-num {
    font-size: 11px;
    font-weight: 700;
    color: #9ca3af;
    min-width: 22px;
    padding-top: 2px;
    flex-shrink: 0;
  }
  .dc-vic-body {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .dc-vic-name {
    font-size: 14px;
    font-weight: 600;
    color: #111827;
    line-height: 1.3;
  }
  .dc-vic-code {
    font-size: 11px;
    color: #9ca3af;
  }
  .dc-vic-desc {
    font-size: 12.5px;
    color: #6b7280;
    line-height: 1.5;
    margin-top: 2px;
    word-break: break-word;
  }
  .dc-vic-meta-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    margin-top: 6px;
    padding-top: 8px;
    border-top: 1px solid #e5e7eb;
  }
  .dc-vic-meta {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .dc-vic-meta-lbl {
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: .06em;
    text-transform: uppercase;
    color: #9ca3af;
  }
  .dc-vic-meta-val {
    font-size: 13px;
    font-weight: 600;
    color: #111827;
  }
}
</style>