<template>
<div class="list-page">
  <!-- Toolbar -->
  <div class="sales-toolbar">
    <div class="sales-search">
      <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
      <input v-model="search" placeholder="Search GRNs, suppliers…" class="sales-search-input"/>
    </div>
    <div class="sales-pills">
      <button v-for="t in TABS" :key="t.k" class="sales-pill" :class="{active:tab===t.k}" @click="tab=t.k">
        {{t.l}}
        <span v-if="t.k!=='all'" class="sales-pill-count">{{tabCounts[t.k]}}</span>
      </button>
    </div>
    <div style="margin-left:auto;display:flex;gap:6px">
      <button class="sales-btn-ghost" @click="load" title="Refresh"><span v-html="icon('refresh',13)"></span></button>
      <button class="sales-btn-primary" :disabled="!$canCreate('bills')" :title="!$canCreate('bills') ? 'Read-only access' : ''" @click="openNew"><span v-html="icon('plus',13)"></span> New GRN</button>
    </div>
  </div>

  <!-- KPI Cards -->
  <div class="bk-kpi-grid bk-kpi-grid-4">
    <div class="bk-kpi-card bk-kpi-accent clickable" @click="tab='all'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#dbeafe"><span v-html="icon('file',18)" style="color:#2563eb"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Total GRNs</div>
          <div class="bk-kpi-value">{{ list.length }}</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card clickable" @click="tab='0'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#f1f5f9"><span v-html="icon('edit',18)" style="color:#6b7280"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Draft</div>
          <div class="bk-kpi-value bk-kpi-amber">{{ counts.draft }}</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card clickable" @click="tab='1'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#dcfce7"><span v-html="icon('check',18)" style="color:#16a34a"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Received</div>
          <div class="bk-kpi-value bk-kpi-green">{{ counts.received }}</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card clickable" @click="tab='2'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#f1f5f9"><span v-html="icon('cancel',18)" style="color:#6b7280"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Cancelled</div>
          <div class="bk-kpi-value" :class="counts.cancelled>0?'bk-kpi-red':''">{{ counts.cancelled }}</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Bulk action bar -->
  <BulkActionBar :count="selectedRows.size" @clear="selectedRows=new Set()">
    <button :disabled="!$canDelete('bills')" :title="!$canDelete('bills') ? 'Not permitted' : ''" @click="bulkCancel">Cancel Submitted</button>
    <button class="bab-danger" :disabled="!$canDelete('bills')" :title="!$canDelete('bills') ? 'Not permitted' : ''" @click="bulkDelete">Delete Drafts</button>
  </BulkActionBar>

  <!-- Table -->
  <div class="inv-table-wrap">
    <table class="inv-table pr-desktop-table">
      <thead>
        <tr>
          <th style="width:32px" class="th-check"><input type="checkbox" @change="toggleAll" :checked="allChecked"/></th>
          <th @click="sortBy('name')" class="sortable">GRN # <span v-html="sortArrow('name')"></span></th>
          <th @click="sortBy('supplier_name')" class="sortable">Supplier <span v-html="sortArrow('supplier_name')"></span></th>
          <th @click="sortBy('posting_date')" class="sortable">Date <span v-html="sortArrow('posting_date')"></span></th>
          <th @click="sortBy('purchase_order')" class="sortable">Purchase Order <span v-html="sortArrow('purchase_order')"></span></th>
          <th @click="sortBy('total_qty')" class="sortable ta-r">Items <span v-html="sortArrow('total_qty')"></span></th>
          <th>Status</th>
          <th style="width:120px;text-align:center">Actions</th>
        </tr>
      </thead>
      <tbody>
        <template v-if="loading">
          <tr v-for="n in 5" :key="n"><td colspan="8" style="padding:14px"><div class="shimmer" style="height:12px"></div></td></tr>
        </template>
        <tr v-else-if="!sorted.length">
          <td colspan="8" class="bk-empty-state">
            <div class="bk-empty-inner">
              <template v-if="search||tab!=='all'">
                <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.3"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                <p class="bk-empty-title">No results match your filters</p>
              </template>
              <template v-else>
                <div class="bk-empty-illus"><svg width="80" height="96" viewBox="0 0 80 96" fill="none"><rect x="10" y="8" width="60" height="80" rx="6" fill="#e2e8f0"/><rect x="14" y="12" width="52" height="72" rx="4" fill="#fff"/><rect x="22" y="26" width="36" height="3" rx="2" fill="#e2e8f0"/><rect x="22" y="34" width="28" height="3" rx="2" fill="#e2e8f0"/><rect x="22" y="42" width="32" height="3" rx="2" fill="#e2e8f0"/><rect x="50" y="64" width="18" height="20" rx="3" fill="#16a34a" opacity=".7"/><rect x="36" y="70" width="12" height="14" rx="3" fill="#2563eb" opacity=".6"/></svg></div>
                <p class="bk-empty-title">No purchase receipts yet</p>
                <p class="bk-empty-sub">Create a GRN to record stock received from a supplier.</p>
                <button class="bk-empty-btn" :disabled="!$canCreate('bills')" :title="!$canCreate('bills') ? 'Read-only access' : ''" @click="openNew"><span v-html="icon('plus',13)"></span> New GRN</button>
              </template>
            </div>
          </td>
        </tr>
        <tr v-else v-for="r in paged" :key="r.name" class="inv-row" :class="{selected:selectedRows.has(r.name)}">
          <td class="td-check"><input type="checkbox" :disabled="r.source!=='real'" :checked="selectedRows.has(r.name)" @change="toggleRow(r.name)"/></td>
          <td @click="openView(r)"><DocLink doctype="Purchase Receipt" :name="r.name" /></td>
          <td class="fw-600" @click="openView(r)">{{r.supplier_name||r.supplier||'—'}}</td>
          <td class="c-muted mono-sm" @click="openView(r)">{{r.posting_date||'—'}}</td>
          <td class="c-muted mono-sm" @click="openView(r)">{{r.purchase_order||'—'}}</td>
          <td class="ta-r c-muted mono-sm" @click="openView(r)">{{r.total_qty||'—'}}</td>
          <td @click="openView(r)"><span class="inv-status-badge" :class="statusClass(r)">{{statusLabel(r)}}</span></td>
          <td @click.stop>
            <div class="pr-actions-row">
              <button class="inv-act-btn" @click.stop="openView(r)" title="View"><span v-html="icon('eye',12)"></span></button>
              <button v-if="canEdit(r)" class="inv-act-btn" @click.stop="openEdit(r)" title="Edit"><span v-html="icon('edit',12)"></span></button>
              <button v-if="r.source==='real' && r.docstatus===1" class="inv-act-btn pr-act-cancel" @click.stop="confirmTarget={row:r,mode:'cancel'}" title="Cancel"><span v-html="icon('x',12)"></span></button>
              <button v-if="r.source==='real' && r.docstatus===0" class="inv-act-btn pr-act-del" @click.stop="confirmTarget={row:r,mode:'delete'}" title="Delete"><span v-html="icon('trash',12)"></span></button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Mobile cards (shown at ≤768px, hidden on desktop) -->
    <div class="pr-mobile-cards">
      <template v-if="loading">
        <div v-for="n in 5" :key="n" class="pr-mobile-card pr-mc--skeleton">
          <div class="pr-mc-shimmer" style="height:13px;width:55%;margin-bottom:8px"></div>
          <div class="pr-mc-shimmer" style="height:11px;width:40%;margin-bottom:6px"></div>
          <div class="pr-mc-shimmer" style="height:11px;width:65%"></div>
        </div>
      </template>
      <div v-else-if="!sorted.length" class="pr-mc-empty">
        <div style="font-size:32px;margin-bottom:8px">📦</div>
        <div>{{search||tab!=='all' ? 'No results match your filters' : 'No purchase receipts yet'}}</div>
      </div>
      <template v-else>
        <div v-for="r in paged" :key="r.name" class="pr-mobile-card" @click="openView(r)">
          <div class="pr-mc-top">
            <span class="pr-mc-docno">{{r.name}}</span>
            <span class="inv-status-badge" :class="statusClass(r)">{{statusLabel(r)}}</span>
          </div>
          <div class="pr-mc-mid">{{r.supplier_name||r.supplier||'—'}}</div>
          <div class="pr-mc-meta">
            <span>{{r.posting_date||'—'}}</span>
            <span class="pr-mc-po">{{r.purchase_order||'—'}}</span>
          </div>
          <div class="pr-mc-meta">
            <span>Items: {{r.total_qty||'—'}}</span>
          </div>
          <div class="pr-mc-footer">
            <button class="pr-mc-btn" @click.stop="openView(r)">View</button>
            <button v-if="canEdit(r)" class="pr-mc-btn" @click.stop="openEdit(r)">Edit</button>
            <button v-if="r.source==='real' && r.docstatus===1" class="pr-mc-btn pr-mc-warn" @click.stop="confirmTarget={row:r,mode:'cancel'}">Cancel</button>
            <button v-if="r.source==='real' && r.docstatus===0" class="pr-mc-btn pr-mc-danger" @click.stop="confirmTarget={row:r,mode:'delete'}">Delete</button>
          </div>
        </div>
      </template>
    </div>
  </div>

  <div v-if="!loading && sorted.length">
    <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="sorted.length" />
  </div>

  <!-- ===== Drawers ===== -->
  <Teleport to="body">

    <!-- VIEW DRAWER -->
    <div v-if="viewOpen" class="inv-drawer-bg" @click.self="viewOpen=false">
      <div class="inv-drawer-panel inv-view-page pr-view-drawer">
        <template v-if="viewDoc">

          <!-- Header -->
          <div class="inv-view-header">
            <div>
              <div class="inv-view-number">{{ viewDoc.name }}</div>
              <div class="inv-view-subtitle">Purchase Receipt (GRN) · {{ viewDoc.posting_date }}</div>
            </div>
            <div style="display:flex;align-items:center;gap:8px">
              <span class="inv-hdr-badge" :class="statusClass(viewDoc)">{{ statusLabel(viewDoc) }}</span>
              <button class="inv-dclose" @click="viewOpen=false"><span v-html="icon('x',16)"></span></button>
            </div>
          </div>

          <!-- Action bar -->
          <div class="inv-action-bar">
            <button v-if="canEdit(viewDoc) && $canEdit('bills')" class="inv-ab-btn" @click="openEdit(viewDoc); viewOpen=false">
              <span v-html="icon('edit',13)"></span> Edit
            </button>
            <button v-if="viewDoc.docstatus===0" class="inv-ab-btn inv-ab-primary" @click="submitGRN" :disabled="submitting || !$canEdit('bills')" :title="!$canEdit('bills') ? 'Read-only access' : ''">
              <span v-html="icon('send',13)"></span> {{ submitting ? 'Submitting…' : 'Submit GRN' }}
            </button>
            <button v-if="viewDoc.docstatus===1 && viewDoc.source==='real'" class="inv-ab-btn" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''" @click="goToLandedCost(viewDoc)">
              <span v-html="icon('purchase',13)"></span> Create Landed Cost Voucher
            </button>
            <button v-if="viewDoc.docstatus===1 && viewDoc.source==='real'" class="inv-ab-btn pr-act-cancel" :disabled="!$canDelete('bills')" :title="!$canDelete('bills') ? 'Not permitted' : ''" @click="confirmTarget={row:viewDoc,mode:'cancel'}">
              <span v-html="icon('x',13)"></span> Cancel
            </button>
            <button v-if="viewDoc.docstatus===0 && viewDoc.source==='real'" class="inv-ab-btn pr-act-del" :disabled="!$canDelete('bills')" :title="!$canDelete('bills') ? 'Not permitted' : ''" @click="confirmTarget={row:viewDoc,mode:'delete'}">
              <span v-html="icon('trash',13)"></span> Delete
            </button>
          </div>

          <!-- Body -->
          <div class="inv-dbody">

            <!-- Supplier & receipt details -->
            <div class="pr-view-card">
              <div class="pr-view-card-hdr">Supplier & Receipt Details</div>
              <div class="pr-info-grid">
                <div class="pr-info-item">
                  <div class="pr-info-lbl">Supplier</div>
                  <div class="pr-info-val pr-info-link">
                    <DocLink doctype="Supplier" :name="viewDoc.supplier" :mono-style="false">{{ viewDoc.supplier_name||viewDoc.supplier||'—' }}</DocLink>
                  </div>
                </div>
                <div class="pr-info-item">
                  <div class="pr-info-lbl">Date</div>
                  <div class="pr-info-val">{{ viewDoc.posting_date||'—' }}</div>
                </div>
                <div class="pr-info-item">
                  <div class="pr-info-lbl">Receiving Warehouse</div>
                  <div class="pr-info-val" :class="viewDoc.set_warehouse?'':'pr-info-empty'">{{ viewDoc.set_warehouse||'—' }}</div>
                </div>
                <div class="pr-info-item">
                  <div class="pr-info-lbl">Total Qty</div>
                  <div class="pr-info-val" style="font-weight:600">{{ (viewDoc.items||[]).reduce((s,i)=>s+flt(i.qty),0)||'—' }}</div>
                </div>
                <div v-if="viewDoc.purchase_order" class="pr-info-item pr-info-full">
                  <div class="pr-info-lbl">Purchase Order</div>
                  <div class="pr-info-val pr-info-link"><DocLink doctype="Purchase Order" :name="viewDoc.purchase_order" /></div>
                </div>
                <div v-if="viewDoc.remarks" class="pr-info-item pr-info-full">
                  <div class="pr-info-lbl">Remarks</div>
                  <div class="pr-info-val" style="color:#6b7280">{{ viewDoc.remarks }}</div>
                </div>
              </div>
            </div>

            <!-- Items -->
            <div class="pr-view-card">
              <div class="pr-view-card-hdr">
                Items Received
                <span class="pr-item-count">{{ (viewDoc.items||[]).length }} line{{ (viewDoc.items||[]).length!==1?'s':'' }}</span>
              </div>
              <table class="inv-table pr-items-tbl">
                <thead>
                  <tr>
                    <th style="width:32px">#</th>
                    <th>Item</th>
                    <th class="ta-r" style="width:64px">Qty</th>
                    <th class="ta-r" style="width:76px">Accepted</th>
                    <th class="ta-r" style="width:76px">Rejected</th>
                    <th style="width:56px">UOM</th>
                    <th style="width:120px">Batch No</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(it,i) in viewDoc.items||[]" :key="it.name||it.item_code" class="inv-row">
                    <td class="pr-row-num">{{ i+1 }}</td>
                    <td style="font-weight:500;color:#111827">{{ it.item_name||it.item_code }}</td>
                    <td class="ta-r mono">{{ it.qty }}</td>
                    <td class="ta-r mono" style="color:#2F9E44">{{ it.accepted_qty||it.qty }}</td>
                    <td class="ta-r mono" style="color:#C92A2A">{{ it.rejected_qty||0 }}</td>
                    <td class="c-muted">{{ it.uom||'Nos' }}</td>
                    <td class="mono" style="font-size:11.5px;color:#2563eb">{{ it.batch_no||'—' }}</td>
                  </tr>
                  <tr v-if="!(viewDoc.items||[]).length">
                    <td colspan="7" style="text-align:center;padding:24px;color:#9ca3af;font-size:13px">No items</td>
                  </tr>
                </tbody>
              </table>
            </div>

          </div>

          <!-- Footer -->
          <div class="inv-dfooter">
            <span class="inv-hdr-badge" :class="statusClass(viewDoc)" style="margin-right:auto">{{ statusLabel(viewDoc) }}</span>
            <button class="form-btn form-btn-outline" @click="viewOpen=false">Close</button>
            <button v-if="canEdit(viewDoc) && $canEdit('bills')" class="form-btn form-btn-outline" @click="openEdit(viewDoc); viewOpen=false">
              <span v-html="icon('edit',13)"></span> Edit
            </button>
            <button v-if="viewDoc.docstatus===0" class="form-btn form-btn-primary" @click="submitGRN" :disabled="submitting || !$canEdit('bills')" :title="!$canEdit('bills') ? 'Read-only access' : ''">
              {{ submitting ? 'Submitting…' : 'Submit GRN' }}
            </button>
          </div>

        </template>
      </div>
    </div>

    <!-- CREATE / EDIT DRAWER -->
    <div v-if="formOpen" class="inv-drawer-bg" @click.self="formOpen=false">
      <div class="inv-drawer-panel" :class="{'is-add':!editingName}">

        <!-- Header -->
        <div class="inv-dh">
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
            <div class="inv-dh-title">{{ editingName ? 'Edit Purchase Receipt (GRN)' : 'New Purchase Receipt (GRN)' }}</div>
            <span v-if="!editingName" class="add-status-badge">Draft</span>
            <span v-if="editingName" class="inv-dh-sub" style="margin-left:4px">{{ editingName }}</span>
          </div>
          <button class="inv-dclose" @click="formOpen=false"><span v-html="icon('x',16)"></span></button>
        </div>

        <!-- Body -->
        <div class="inv-content-row">
        <div class="inv-dbody">

          <!-- Supplier & Date Card -->
          <div class="add-card">
            <div class="add-card-header" @click="collapsed.details=!collapsed.details">
              <div class="add-card-title">
                <span class="add-card-title-icon"><span v-html="icon('truck',16)"></span></span>
                Supplier & Date
              </div>
              <span class="add-card-chevron" :class="{collapsed:collapsed.details}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
              </span>
            </div>
            <div class="add-card-body" :class="{collapsed:collapsed.details}">
              <div class="inv-fg inv-fg2">
                <div style="grid-column:1/-1">
                  <label class="inv-lbl">Supplier <span class="inv-req">*</span></label>
                  <SearchableSelect v-model="form.supplier" :options="vendorOptions" placeholder="Search supplier…" @search="fetchVendors" @select="onSupSelect" />
                </div>
                <div>
                  <label class="inv-lbl">Date <span class="inv-req">*</span></label>
                  <input class="inv-fi" type="date" v-model="form.posting_date"/>
                </div>
                <div>
                  <label class="inv-lbl">Purchase Order (optional)</label>
                  <SearchableSelect v-model="form.purchase_order" :options="poOptions" placeholder="Select PO (filtered by supplier)…" @search="fetchPOs" @open="fetchPOs('')" @select="onPOSelect" />
                </div>
              </div>
            </div>
          </div>

          <!-- Receiving Details Card -->
          <div class="add-card">
            <div class="add-card-header" @click="collapsed.receiving=!collapsed.receiving">
              <div class="add-card-title">
                <span class="add-card-title-icon"><span v-html="icon('warehouse',16)"></span></span>
                Receiving Details
              </div>
              <span class="add-card-chevron" :class="{collapsed:collapsed.receiving}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
              </span>
            </div>
            <div class="add-card-body" :class="{collapsed:collapsed.receiving}">
              <div class="inv-fg inv-fg2">
                <div style="grid-column:1/-1">
                  <label class="inv-lbl">Warehouse</label>
                  <SearchableSelect v-model="form.set_warehouse" :options="warehouses" placeholder="Select warehouse where goods will be received…"
                    :createable="true" :staticCreate="true" createLabel="+ Create Warehouse" createDoctype="Warehouse" @search="fetchWarehouses" @open="fetchWarehouses('')" @create="fetchWarehouses('')" />
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
                Items Received <span class="inv-req">*</span>
                <span style="font-size:11.5px;color:#6b7280;font-weight:400;letter-spacing:0;text-transform:none">
                  &nbsp;· {{ form.items.length }} line{{ form.items.length!==1?'s':'' }}
                </span>
              </div>
              <div style="display:flex;align-items:center;gap:8px" @click.stop>
                <button class="add-lines-add-btn" :disabled="!(editingName ? $canEdit('bills') : $canCreate('bills'))" @click="addItem">
                  <span v-html="icon('plus',13)"></span> Add Item
                </button>
                <span class="add-card-chevron" :class="{collapsed:collapsed.items}" @click="collapsed.items=!collapsed.items">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
                </span>
              </div>
            </div>
            <div class="add-card-body" :class="{collapsed:collapsed.items}" style="padding:16px 16px 8px">
              <div class="po-item-cards">
                <div v-for="(it,i) in form.items" :key="i" class="po-item-card">
                  <!-- Card header -->
                  <div class="po-item-card-header" @click="it.collapsedUI=!it.collapsedUI">
                    <span class="po-item-card-num">#{{ i+1 }}</span>
                    <span class="po-item-card-title">{{ it.item_name || it.item_code || 'Line Item' }}</span>
                    <div class="po-item-card-subtotal">
                      <span class="po-item-card-subtotal-label">QTY</span>
                      <span class="po-item-card-amount">{{ it.qty || '—' }}</span>
                    </div>
                    <span class="po-item-card-chevron" :class="{collapsed:it.collapsedUI}">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
                    </span>
                    <button @click.stop="removeItem(i)" class="po-item-card-rm"><span v-html="icon('x',16)"></span></button>
                  </div>
                  <!-- Card body -->
                  <div class="po-item-card-body" v-show="!it.collapsedUI">
                    <div class="po-item-col po-item-col--left">
                      <div class="po-item-field">
                        <label>Item <span class="inv-req">*</span></label>
                        <SearchableSelect v-model="it.item_code" :options="itemOptions" placeholder="Search item…" @search="fetchItems" @select="opt => onItemSelect(it, opt)" />
                      </div>
                      <div v-if="it.has_batch_no" class="po-item-field" style="margin-top:14px">
                        <label>Batch No <span class="inv-req">*</span></label>
                        <SearchableSelect v-model="it.batch_no" :options="it.batchOptions" placeholder="Select existing or type to create new"
                          createable @search="q => fetchBatches(it, q)" @select="opt => onBatchSelect(it, opt)" @create="val => onBatchCreate(it, val)" />
                        <div class="po-item-num-row" style="margin-top:10px">
                          <div class="po-item-field">
                            <label>Mfg. Date</label>
                            <input class="inv-fi" type="date" v-model="it.manufacturing_date"/>
                          </div>
                          <div class="po-item-field">
                            <label>Expiry Date</label>
                            <input class="inv-fi" type="date" v-model="it.expiry_date"/>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div class="po-item-col po-item-col--right">
                      <div class="po-item-num-row">
                        <div class="po-item-field">
                          <label>Qty <span class="inv-req">*</span></label>
                          <input class="inv-fi" type="number" v-model.number="it.qty" placeholder="1" min="0.01" step="0.01"/>
                        </div>
                        <div class="po-item-field">
                          <label>Accepted Qty</label>
                          <input class="inv-fi" type="number" v-model.number="it.accepted_qty" placeholder="1" min="0" :max="it.qty" step="0.01"/>
                        </div>
                      </div>
                      <div class="po-item-field" style="margin-top:14px">
                        <label>UOM</label>
                        <input class="inv-fi" v-model="it.uom" placeholder="Nos"/>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div v-if="!form.items.length" class="pr-items-empty" style="padding:20px 0 8px">No items yet — click Add Item</div>

              <button class="inv-add-line-btn" style="margin-top:12px" :disabled="!(editingName ? $canEdit('bills') : $canCreate('bills'))" @click="addItem">
                <span v-html="icon('plus',12)"></span> Add Item
              </button>
            </div>
          </div>

        </div><!-- /inv-dbody -->
        </div><!-- /inv-content-row -->

        <!-- Footer -->
        <div class="inv-dfooter">
          <div class="add-footer-status">{{ editingName ? 'Editing: ' + editingName : 'New GRN — unsaved changes' }}</div>
          <div class="add-footer-actions">
            <button class="add-btn-cancel" @click="formOpen=false" :disabled="saving">Cancel</button>
            <button class="add-btn-draft" @click="saveGRN(false)" :disabled="saving || !(editingName ? $canEdit('bills') : $canCreate('bills'))" :title="!(editingName ? $canEdit('bills') : $canCreate('bills')) ? 'Read-only access' : ''">
              <span v-html="icon('save',13)"></span> {{ saving?'Saving…':(editingName?'Save Changes':'Save Draft') }}
            </button>
            <button class="add-btn-more" @click="saveGRN(true)" :disabled="saving || !(editingName ? $canEdit('bills') : $canCreate('bills'))" :title="!(editingName ? $canEdit('bills') : $canCreate('bills')) ? 'Read-only access' : ''">
              <span v-html="icon('check',13)"></span> {{ saving?'Saving…':'Save & Submit' }}
            </button>
          </div>
        </div>

      </div>
    </div>

    <!-- CONFIRM DIALOG (delete draft / cancel submitted) -->
    <div v-if="confirmTarget" class="inv-drawer-bg" style="z-index:60" @click.self="confirmTarget=null"></div>
    <div v-if="confirmTarget" class="pr-confirm" style="z-index:61">
      <div class="pr-confirm-icon" :class="confirmTarget.mode==='delete'?'danger':'warn'">
        <span v-html="icon(confirmTarget.mode==='delete'?'trash':'x', 20)"></span>
      </div>
      <div class="pr-confirm-title">{{ confirmTarget.mode==='delete' ? 'Delete draft GRN?' : 'Cancel GRN?' }}</div>
      <div class="pr-confirm-sub">
        <template v-if="confirmTarget.mode==='delete'">
          <strong>{{ confirmTarget.row.name }}</strong> will be permanently deleted. This cannot be undone.
        </template>
        <template v-else>
          <strong>{{ confirmTarget.row.name }}</strong> will be cancelled — this reverses the stock receipt and PO received quantities.
        </template>
      </div>
      <div class="pr-confirm-actions">
        <button class="b-btn b-btn-ghost" @click="confirmTarget=null" :disabled="deleting||cancelling">Keep it</button>
        <button class="b-btn" :class="confirmTarget.mode==='delete'?'pr-btn-danger':'pr-btn-warn'"
          @click="confirmAction" :disabled="deleting||cancelling||!$canDelete('bills')" :title="!$canDelete('bills') ? 'Not permitted' : ''">
          {{ (deleting||cancelling) ? (confirmTarget.mode==='delete'?'Deleting…':'Cancelling…') : (confirmTarget.mode==='delete'?'Yes, Delete':'Yes, Cancel') }}
        </button>
      </div>
    </div>

  </Teleport>
</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useOpenFromQuery } from "../composables/useOpenFromQuery.js";
import { apiList, apiGet, apiGET, apiSave, apiSubmit, apiDelete, apiCancel, resolveCompany } from "../api/client.js";
import SearchableSelect from "../components/SearchableSelect.vue";
import DocLink from "../components/DocLink.vue";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";
import { flt } from "../utils/format.js";
import Pagination from "../components/Pagination.vue";
import BulkActionBar from "../components/BulkActionBar.vue";
import { usePagination } from "../composables/usePagination.js";

const { toast } = useToast();
const router = useRouter();
const route  = useRoute();

function goToLandedCost(doc) {
  router.push({ path: "/purchasing/landed-cost-vouchers/new", query: { purchase_receipt: doc.name } });
}

const TABS = [{k:"all",l:"All"},{k:"0",l:"Draft"},{k:"1",l:"Received"},{k:"2",l:"Cancelled"}];
const list      = ref([]);
const loading   = ref(false);
const search    = ref("");
const tab       = ref("all");
const viewOpen  = ref(false);
const viewDoc   = ref(null);
const formOpen  = ref(false);
const saving    = ref(false);
const submitting = ref(false);
const deleting  = ref(false);
const cancelling = ref(false);
const editingName = ref("");
const confirmTarget = ref(null); // { row, mode: "delete"|"cancel" }
const selectedRows = ref(new Set());
const sortKey = ref("posting_date");
const sortDir = ref(-1);
const vendorOptions = ref([]);
const itemOptions   = ref([]);
const poOptions     = ref([]);
const warehouses    = ref([]);
const collapsed = reactive({ details: false, receiving: false, items: false });

const form = reactive({
  supplier: "", supplier_name: "", posting_date: new Date().toISOString().slice(0,10),
  purchase_order: "", set_warehouse: "", remarks: "", items: [],
});

const counts = computed(() => ({
  draft:     list.value.filter(r => r.docstatus === 0).length,
  received:  list.value.filter(r => r.docstatus === 1).length,
  cancelled: list.value.filter(r => r.docstatus === 2).length,
}));
const tabCounts = computed(() => ({ "0": counts.value.draft, "1": counts.value.received, "2": counts.value.cancelled }));

function statusLabel(r) {
  if (r.docstatus===2) return "Cancelled";
  if (r.docstatus===0) return "Draft";
  // docstatus===1: real submitted receipts read "Submitted"; legacy
  // PO-derived rows carry their own Partially/Fully Received label.
  if (r.status === "Partially Received" || r.status === "Fully Received") return r.status;
  return "Received";
}
function statusClass(r) {
  if (r.docstatus===2) return "b-badge-muted";
  if (r.docstatus===0) return "b-badge-orange";
  if (r.status === "Partially Received") return "b-badge-orange";
  return "b-badge-green";
}
function canEdit(r) {
  return !!r && r.source === "real" && r.docstatus === 0;
}

async function load() {
  loading.value = true;
  try {
    // No standalone Purchase Receipt doctype in this build. Synthesise the list
    // from Purchase Order lines with received_qty > 0.
    const rows = await apiGET("zoho_books_clone.api.docs.get_purchase_receipt_list", { limit: 100000 }) || [];
    const rawList = rows.map(r => ({
      // Real Purchase Receipts already have their own name from the backend —
      // don't overwrite it with the linked PO's name, or multiple GRNs against
      // the same PO collapse into one row / the wrong document gets opened.
      name: r.name || r.purchase_order,
      supplier: r.supplier,
      supplier_name: r.supplier_name,
      posting_date: r.posting_date || r.expected_delivery_date || r.transaction_date,
      purchase_order: r.purchase_order,
      total_qty: r.qty_received,
      qty_ordered: r.qty_ordered,
      qty_received: r.qty_received,
      qty_billed: r.qty_billed,
      pct_received: r.pct_received,
      status: r.receipt_status,
      docstatus: r.docstatus,
      grand_total: r.grand_total,
      source: r.source || "derived",
    }));
    list.value = rawList;
    // Resolve missing supplier_name — backend may omit it
    const missing = [...new Set(rawList.filter(r => !r.supplier_name && r.supplier).map(r => r.supplier))];
    if (missing.length) {
      const sups = await apiList("Supplier", { fields: ["name","supplier_name"], filters: [["name","in",missing]], limit: missing.length }).catch(()=>[]);
      const nameMap = Object.fromEntries(sups.map(s => [s.name, s.supplier_name || s.name]));
      list.value = rawList.map(r => r.supplier_name ? r : { ...r, supplier_name: nameMap[r.supplier] || r.supplier });
    }
  } catch (e) { console.warn("Purchase receipt load failed:", e.message); list.value = []; }
  finally { loading.value = false; }
}

const filtered = computed(() => {
  let r = list.value;
  if (tab.value === "0")      r = r.filter(x => x.docstatus === 0);
  else if (tab.value === "1") r = r.filter(x => x.docstatus === 1);
  else if (tab.value === "2") r = r.filter(x => x.docstatus === 2);
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    r = r.filter(x => (x.name||"").toLowerCase().includes(q) || (x.supplier_name||"").toLowerCase().includes(q));
  }
  return r;
});

const sorted = computed(() => {
  const key = sortKey.value, dir = sortDir.value;
  return [...filtered.value].sort((a,b) => {
    let av = a[key], bv = b[key];
    if (key === "total_qty") { av = flt(av); bv = flt(bv); return dir * (av - bv); }
    av = (av||"").toString().toLowerCase(); bv = (bv||"").toString().toLowerCase();
    return dir * av.localeCompare(bv);
  });
});
const { page, pageSize, paged } = usePagination(sorted, { storageKey: "purchase-receipts" });

function sortBy(key) {
  if (sortKey.value === key) sortDir.value = -sortDir.value;
  else { sortKey.value = key; sortDir.value = key === "posting_date" ? -1 : 1; }
}
function sortArrow(key) {
  if (sortKey.value !== key) return "";
  return sortDir.value === 1 ? "↑" : "↓";
}

const selectableRows = computed(() => paged.value.filter(r => r.source === "real"));
const allChecked = computed(() => selectableRows.value.length > 0 && selectableRows.value.every(r => selectedRows.value.has(r.name)));
function toggleRow(name) {
  const s = new Set(selectedRows.value);
  if (s.has(name)) s.delete(name); else s.add(name);
  selectedRows.value = s;
}
function toggleAll() {
  if (allChecked.value) { selectedRows.value = new Set(); return; }
  selectedRows.value = new Set(selectableRows.value.map(r => r.name));
}
async function bulkCancel() {
  const targets = [...selectedRows.value].map(n => list.value.find(r => r.name === n)).filter(r => r && r.source==="real" && r.docstatus===1);
  if (!targets.length) { toast.info("No submitted GRNs selected"); return; }
  for (const r of targets) {
    try { await apiCancel("Purchase Receipt", r.name); } catch (e) { toast.error(`${r.name}: ${e.message||"Cancel failed"}`); }
  }
  toast.success(`Cancelled ${targets.length} GRN(s)`);
  selectedRows.value = new Set();
  await load();
}
async function bulkDelete() {
  const targets = [...selectedRows.value].map(n => list.value.find(r => r.name === n)).filter(r => r && r.source==="real" && r.docstatus===0);
  if (!targets.length) { toast.info("No draft GRNs selected"); return; }
  for (const r of targets) {
    try { await apiDelete("Purchase Receipt", r.name); } catch (e) { toast.error(`${r.name}: ${e.message||"Delete failed"}`); }
  }
  toast.success(`Deleted ${targets.length} draft GRN(s)`);
  selectedRows.value = new Set();
  await load();
}

async function openView(r) {
  viewOpen.value = true;
  try {
    if (r.source === "real") {
      // Real Purchase Receipt document — show its own item rows directly.
      const doc = await apiGet("Purchase Receipt", r.name);
      viewDoc.value = { ...r, ...doc, items: doc?.items || [] };
    } else {
      // Legacy row derived from Purchase Order lines with no PR document.
      const lines = await apiGET("zoho_books_clone.api.docs.get_purchase_receipt_lines", { purchase_order: r.purchase_order || r.name }) || [];
      viewDoc.value = { ...r, items: lines };
    }
  } catch (e) {
    console.warn("PR lines load failed:", e.message);
    viewDoc.value = r;
  }
}

async function submitGRN() {
  if (!viewDoc.value) return;
  if (viewDoc.value.source !== "real") {
    // Legacy rows are just a computed view of Purchase Order lines and have
    // no Purchase Receipt document behind them to submit.
    toast.info("This is a legacy record derived from Purchase Order lines — there's no receipt document to submit. Use New GRN to create one.");
    return;
  }
  submitting.value = true;
  try {
    await apiSubmit("Purchase Receipt", viewDoc.value.name);
    toast.success("GRN submitted");
    viewOpen.value = false;
    await load();
  } catch (e) { toast.error(e.message || "Submit failed"); }
  finally { submitting.value = false; }
}

async function confirmAction() {
  if (!confirmTarget.value) return;
  const { row, mode } = confirmTarget.value;
  if (row.source !== "real") { confirmTarget.value = null; return; } // safety: only real docs are actionable
  if (mode === "delete") {
    if (row.docstatus !== 0) { confirmTarget.value = null; return; }
    deleting.value = true;
    try {
      await apiDelete("Purchase Receipt", row.name);
      toast.success(`Draft GRN ${row.name} deleted`);
      confirmTarget.value = null;
      viewOpen.value = false;
      await load();
    } catch (e) { toast.error(e.message || "Delete failed"); }
    finally { deleting.value = false; }
  } else {
    if (row.docstatus !== 1) { confirmTarget.value = null; return; }
    cancelling.value = true;
    try {
      await apiCancel("Purchase Receipt", row.name);
      toast.success(`GRN ${row.name} cancelled`);
      confirmTarget.value = null;
      viewOpen.value = false;
      await load();
    } catch (e) { toast.error(e.message || "Cancel failed"); }
    finally { cancelling.value = false; }
  }
}

function resetForm() {
  Object.assign(form, {
    supplier: "", supplier_name: "", posting_date: new Date().toISOString().slice(0,10),
    purchase_order: "", set_warehouse: "", remarks: "", items: [],
  });
}

function openNew() {
  editingName.value = "";
  resetForm();
  fetchVendors("");
  fetchItems("");
  fetchPOs("");
  fetchWarehouses("");
  addItem();
  formOpen.value = true;
}

async function openEdit(r) {
  if (!canEdit(r)) return;
  editingName.value = r.name;
  resetForm();
  fetchVendors("");
  fetchItems("");
  fetchPOs("");
  fetchWarehouses("");
  formOpen.value = true;
  try {
    const doc = await apiGet("Purchase Receipt", r.name);
    if (!doc) return;
    Object.assign(form, {
      supplier:       doc.supplier || "",
      supplier_name:  doc.supplier_name || "",
      posting_date:   doc.posting_date || new Date().toISOString().slice(0,10),
      purchase_order: doc.purchase_order || "",
      set_warehouse:  doc.set_warehouse || "",
      remarks:        doc.remarks || "",
      items: [],
    });
    if (doc.purchase_order) fetchPOs("");
    const items = doc.items || [];
    const codes = [...new Set(items.map(it => it.item_code).filter(Boolean))];
    let flagMap = {};
    if (codes.length) {
      try {
        const itemRows = await apiList("Item", { fields: ["name", "has_batch_no"], filters: [["name", "in", codes]], limit: codes.length });
        flagMap = Object.fromEntries(itemRows.map(x => [x.name, x.has_batch_no ? 1 : 0]));
      } catch {}
    }
    form.items = items.map(it => ({
      po_item:            it.po_item || null,
      item_code:          it.item_code || "",
      item_name:          it.item_name || it.item_code || "",
      qty:                it.qty ?? 1,
      accepted_qty:       it.accepted_qty ?? it.qty ?? 1,
      uom:                it.uom || "Nos",
      has_batch_no:       flagMap[it.item_code] || 0,
      batch_no:           it.batch_no || "",
      manufacturing_date: it.manufacturing_date || "",
      expiry_date:        it.expiry_date || "",
      batchOptions:       [],
      collapsedUI:        false,
    }));
    form.items.forEach(l => { if (l.has_batch_no) fetchBatches(l, ""); });
    if (!form.items.length) addItem();
  } catch (e) {
    toast.error(e.message || "Failed to load GRN for editing");
    formOpen.value = false;
  }
}

function addItem() {
  form.items.push({
    item_code:"", item_name:"", qty:1, accepted_qty:1, uom:"Nos", po_item: null,
    has_batch_no: 0, batch_no: "", manufacturing_date: "", expiry_date: "", batchOptions: [], collapsedUI: false,
  });
}
function removeItem(i) { form.items.splice(i, 1); }

async function fetchVendors(q = "") {
  try {
    const filters = [["disabled", "=", 0]];
    if (q) filters.push(["supplier_name", "like", `%${q}%`]);
    const rows = await apiList("Supplier", { fields: ["name", "supplier_name"], filters, limit: 30, order: "supplier_name asc" });
    vendorOptions.value = rows.map(r => ({ label: r.supplier_name || r.name, value: r.name }));
  } catch { vendorOptions.value = []; }
}
function onSupSelect(opt) {
  form.supplier      = opt?.value ?? opt;
  form.supplier_name = opt?.label ?? opt?.value ?? "";
  // Reset PO and reload PO list for the new supplier
  form.purchase_order = "";
  poOptions.value = [];
  fetchPOs("");
}
async function fetchWarehouses(q = "") {
  try {
    const co = await resolveCompany();
    const rows = await apiList("Warehouse", { filters: [["company","=",co],["disabled","=",0],["is_group","=",0]], fields: ["name","parent_warehouse"], limit: 50 });
    warehouses.value = (rows || [])
      .filter(r => !q || r.name.toLowerCase().includes(q.toLowerCase()) || (r.parent_warehouse||"").toLowerCase().includes(q.toLowerCase()))
      .map(r => ({ label: r.parent_warehouse ? `${r.parent_warehouse} / ${r.name}` : r.name, value: r.name }));
  } catch { warehouses.value = []; }
}
async function fetchPOs(q = "") {
  try {
    const company = await resolveCompany();
    const filters = [
      ["company", "=", company],
      ["docstatus", "=", 1],
      // Only POs that still have something left to receive — excludes
      // Received / Billed / Closed / Cancelled / draft Purchase Orders.
      ["status", "in", ["To Receive", "Partially Received", "Submitted"]],
    ];
    if (form.supplier) filters.push(["supplier", "=", form.supplier]);
    if (q) filters.push(["name", "like", `%${q}%`]);
    const rows = await apiList("Purchase Order", {
      fields: ["name", "supplier", "transaction_date", "grand_total"],
      filters, limit: 30, order: "transaction_date desc, creation desc",
    });
    poOptions.value = rows.map(r => ({
      label: `${r.name}  (${r.transaction_date || ""})`,
      value: r.name,
    }));
  } catch { poOptions.value = []; }
}

// ── PO select: pull remaining-to-receive lines from the Purchase Order ───────
async function onPOSelect(opt) {
  const poName = opt?.value ?? opt;
  form.purchase_order = poName;
  if (!poName) return;
  try {
    const res = await apiGET("zoho_books_clone.api.docs.get_purchase_order_fulfillment", { purchase_order: poName });
    const lines = (res?.lines || []).filter(it => flt(it.remaining_to_receive) > 0);
    if (lines.length) {
      form.items = lines.map(it => ({
        po_item:      it.name,
        item_code:    it.item_code,
        item_name:    it.item_name || it.item_code,
        qty:          flt(it.remaining_to_receive) || flt(it.qty) || 1,
        accepted_qty: flt(it.remaining_to_receive) || flt(it.qty) || 1,
        uom:          it.uom || "Nos",
        has_batch_no: 0, batch_no: "", manufacturing_date: "", expiry_date: "", batchOptions: [], collapsedUI: false,
      }));
      // Resolve has_batch_no per item so the Batch No field shows up for
      // batch-tracked items pulled in from the Purchase Order.
      const codes = [...new Set(form.items.map(l => l.item_code).filter(Boolean))];
      if (codes.length) {
        try {
          const itemRows = await apiList("Item", { fields: ["name", "has_batch_no"], filters: [["name", "in", codes]], limit: codes.length });
          const flagMap = Object.fromEntries(itemRows.map(r => [r.name, r.has_batch_no ? 1 : 0]));
          form.items.forEach(l => { l.has_batch_no = flagMap[l.item_code] || 0; if (l.has_batch_no) fetchBatches(l, ""); });
        } catch {}
      }
      toast.success(`Loaded ${lines.length} item(s) from ${poName}`);
    } else {
      toast.info(`${poName} has nothing left to receive`);
    }
  } catch {}
}
async function fetchItems(q = "") {
  try {
    const filters = [["disabled", "=", 0], ["has_variants", "=", 0], ["is_purchase_item", "=", 1]];
    if (q) filters.push(["item_name", "like", `%${q}%`]);
    const rows = await apiList("Item", { fields: ["name", "item_name", "description", "stock_uom", "standard_rate", "standard_buying_rate", "has_batch_no"], filters, limit: 30, order: "item_name asc" });
    itemOptions.value = rows.map(r => ({ label: r.item_name || r.name, value: r.name, description: r.description || "", uom: r.stock_uom || "Nos", rate: r.standard_buying_rate || r.standard_rate || 0, has_batch_no: r.has_batch_no ? 1 : 0 }));
  } catch { itemOptions.value = []; }
}
function onItemSelect(line, opt) {
  line.item_code    = opt?.value ?? opt;
  line.item_name    = opt?.label  || opt?.value || "";
  line.uom          = opt?.uom   || line.uom || "Nos";
  line.po_item      = null; // manually changing the item breaks the PO-line link
  line.has_batch_no = opt?.has_batch_no ? 1 : 0;
  line.batch_no     = "";
  line.manufacturing_date = "";
  line.expiry_date  = "";
  line.batchOptions = [];
  if (line.has_batch_no) fetchBatches(line, "");
}

// ── Batch helpers (mirrors OpeningStockBatchEntry.vue) ────────────────────────
async function fetchBatches(line, q = "") {
  if (!line.item_code) { line.batchOptions = []; return; }
  const itemCode = line.item_code;
  try {
    const filters = [["item", "=", itemCode], ["disabled", "=", 0]];
    if (q) filters.push(["name", "like", `%${q}%`]);
    const rows = await apiList("Batch", { fields: ["name", "manufacturing_date", "expiry_date", "batch_qty"], filters, limit: 20 });
    if (line.item_code !== itemCode) return; // item changed while awaiting
    line.batchOptions = rows.map(b => ({
      value: b.name,
      label: (b.batch_qty !== undefined && b.batch_qty !== null) ? `${b.name} (Qty: ${b.batch_qty})` : b.name,
      manufacturing_date: b.manufacturing_date || "",
      expiry_date: b.expiry_date || "",
    }));
  } catch { if (line.item_code === itemCode) line.batchOptions = []; }
}
function onBatchSelect(line, opt) {
  line.batch_no = opt?.value ?? opt;
  line.manufacturing_date = (opt && opt.manufacturing_date) || "";
  line.expiry_date = (opt && opt.expiry_date) || "";
}
function onBatchCreate(line, val) { line.batch_no = val; }

async function saveGRN(submit) {
  if (!form.supplier.trim()) { toast.error("Supplier is required"); return; }
  const usable = form.items.filter(it => it.item_code.trim());
  if (!usable.length) { toast.error("Add at least one item"); return; }

  for (const [idx, it] of usable.entries()) {
    const rowQty = parseFloat(it.qty) || 0;
    const rowAccepted = parseFloat(it.accepted_qty);
    if (!isNaN(rowAccepted) && (rowAccepted < 0 || rowAccepted > rowQty)) {
      toast.error(`Row ${idx + 1}: Accepted Qty can't be negative or exceed Received Qty (${rowQty}).`);
      return;
    }
  }

  // Batch-tracked items must carry a Batch No before we let this go to the
  // backend — otherwise the auto-generated Stock Entry (Material Receipt)
  // fails its own "Batch No is required" check on submit.
  for (const [idx, it] of usable.entries()) {
    if (it.has_batch_no && !it.batch_no) {
      toast.error(`Row ${idx + 1}: ${it.item_name || it.item_code} is batch-tracked — Batch No is required`);
      return;
    }
  }
  const batchOwners = new Map();
  for (const [idx, it] of usable.entries()) {
    if (!it.has_batch_no || !it.batch_no) continue;
    if (batchOwners.has(it.batch_no) && batchOwners.get(it.batch_no) !== it.item_code) {
      toast.error(`Row ${idx + 1}: Batch "${it.batch_no}" is already used for a different item in this GRN.`);
      return;
    }
    batchOwners.set(it.batch_no, it.item_code);
    const existing = await apiList("Batch", { fields: ["name", "disabled", "item"], filters: [["name", "=", it.batch_no]], limit: 1 }).catch(() => []);
    if (existing.length && existing[0].disabled) {
      toast.error(`Row ${idx + 1}: Batch "${it.batch_no}" is disabled and can't be used.`);
      return;
    }
    if (existing.length && existing[0].item && existing[0].item !== it.item_code) {
      toast.error(`Row ${idx + 1}: Batch "${it.batch_no}" already exists for item "${existing[0].item}", not "${it.item_code}".`);
      return;
    }
  }

  saving.value = true;
  try {
    const company = await resolveCompany();

    // Pre-create Batch records for batch-tracked lines so the auto-generated
    // Stock Entry can resolve batch_no as a valid Link on submit.
    for (const it of usable) {
      if (!it.has_batch_no || !it.batch_no) continue;
      const exists = await apiList("Batch", { fields: ["name"], filters: [["name", "=", it.batch_no]], limit: 1 });
      if (!exists.length) {
        await apiSave({
          doctype: "Batch",
          batch_no: it.batch_no,
          item: it.item_code,
          warehouse: form.set_warehouse || null,
          manufacturing_date: it.manufacturing_date || null,
          expiry_date: it.expiry_date || null,
          batch_qty: 0,
        });
      }
    }

    const doc = {
      doctype: "Purchase Receipt",
      supplier: form.supplier,
      posting_date: form.posting_date,
      company,
      purchase_order: form.purchase_order || null,
      set_warehouse: form.set_warehouse || null,
      remarks: form.remarks || "",
      items: usable.map(it => {
        const rowQty = parseFloat(it.qty) || 1;
        const rawAccepted = parseFloat(it.accepted_qty);
        const rowAccepted = Math.min(Math.max(isNaN(rawAccepted) ? rowQty : rawAccepted, 0), rowQty);
        return {
        doctype: "Purchase Receipt Item",
        item_code: it.item_code,
        item_name: it.item_name || it.item_code,
        qty: rowQty,
        accepted_qty: rowAccepted,
        rejected_qty: rowQty - rowAccepted,
        uom: it.uom || "Nos",
        stock_uom: it.uom || "Nos",
        conversion_factor: 1,
        received_qty: rowQty,
        rate: 0,
        po_item: it.po_item || undefined,
        batch_no: it.has_batch_no ? (it.batch_no || null) : null,
        manufacturing_date: it.has_batch_no ? (it.manufacturing_date || null) : null,
        expiry_date: it.has_batch_no ? (it.expiry_date || null) : null,
      };}),
    };
    if (editingName.value) doc.name = editingName.value;

    const saved = await apiSave(doc);
    if (submit && saved?.name) await apiSubmit("Purchase Receipt", saved.name);
    toast.success(`GRN ${saved?.name || ""} ${submit ? "submitted" : "saved"}`);
    formOpen.value = false;
    await load();
  } catch (e) { toast.error(e.message || "Failed to save GRN"); }
  finally { saving.value = false; }
}

onMounted(async () => {
  await load();
  fetchVendors(""); fetchItems(""); fetchPOs("");
  useOpenFromQuery({ route, openByName: (n) => openView(list.value.find(r => r.name === n) || { name: n }) });
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
.pr-view-card { background:#fff;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;margin-bottom:14px; }
.pr-view-card-hdr { display:flex;align-items:center;justify-content:space-between;padding:10px 16px;background:#f8fafc;border-bottom:1px solid #e5e7eb;font-size:12px;font-weight:700;color:#374151;letter-spacing:.02em; }
.pr-item-count { font-size:11.5px;font-weight:500;color:#6b7280;letter-spacing:0; }

/* ── Info grid ── */
.pr-info-grid { display:grid;grid-template-columns:1fr 1fr;gap:0; }
.pr-info-item { padding:10px 16px;border-bottom:1px solid #f1f5f9; }
.pr-info-item:nth-child(odd) { border-right:1px solid #f1f5f9; }
.pr-info-full { grid-column:1/-1; }
.pr-info-lbl { font-size:10.5px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px; }
.pr-info-val { font-size:13px;color:#111827;line-height:1.4; }
.pr-info-empty { color:#9ca3af !important; }
.pr-info-link a, .pr-info-link span { color:#2563eb;font-weight:500; }

/* ── Items table ── */
.pr-items-tbl { font-size:12.5px; }
.pr-row-num { color:#9ca3af;font-size:11.5px;font-weight:600;text-align:center; }
.pr-items-empty { font-size:12px;color:#868E96;text-align:center;padding:14px;background:#f9fafb;border:1px dashed #e5e7eb;border-radius:8px; }

/* ── Confirm dialog ── */
.pr-confirm { position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#fff;border-radius:16px;padding:28px 28px 22px;box-shadow:0 20px 60px rgba(15,23,42,.18);z-index:61;width:340px;max-width:92vw;display:flex;flex-direction:column;align-items:center;gap:10px;text-align:center; }
.pr-confirm-icon { width:52px;height:52px;border-radius:50%;display:flex;align-items:center;justify-content:center;margin-bottom:4px; }
.pr-confirm-icon.danger { background:#fee2e2;color:#dc2626; }
.pr-confirm-icon.warn { background:#fffbeb;color:#d97706; }
.pr-confirm-title { font-size:16px;font-weight:700;color:#111827; }
.pr-confirm-sub { font-size:13px;color:#6b7280;line-height:1.5; }
.pr-confirm-actions { display:flex;gap:8px;margin-top:6px;width:66%; }
.pr-confirm-actions .form-btn { flex:1;justify-content:center; }
.pr-btn-danger { background:#dc2626;border:1px solid #dc2626;color:#fff;border-radius:8px;padding:8px 14px;font-size:13px;font-weight:600;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:6px; }
.pr-btn-danger:hover { background:#b91c1c;border-color:#b91c1c; }
.pr-btn-warn { background:#d97706;border:1px solid #d97706;color:#fff;border-radius:8px;padding:8px 14px;font-size:13px;font-weight:600;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:6px; }
.pr-btn-warn:hover { background:#b45309;border-color:#b45309; }
.pr-btn-danger:disabled,.pr-btn-warn:disabled { opacity:.5;cursor:not-allowed; }

/* ── Action button hover states ── */
.pr-actions-row { display:flex;align-items:center;justify-content:center;gap:4px;flex-wrap:nowrap; }
.pr-act-del:hover { background:#fef2f2 !important;border-color:#fecaca !important;color:#dc2626 !important; }
.pr-act-cancel:hover { background:#fffbeb !important;border-color:#fde68a !important;color:#d97706 !important; }

/* ── Misc ── */
.b-empty { text-align:center;color:#9ca3af;padding:24px!important; }
.ta-r { text-align:right; }
.fw-600 { font-weight:600; }
.c-muted { color:#6b7280; }
.mono { font-size:13px; }
.pr-view-drawer { width: 600px; right: -600px; }

/* ── Mobile cards (hidden on desktop, base display:none must precede @media) ── */
.pr-mobile-cards { display: none; }
.pr-mc-shimmer { background: linear-gradient(90deg,#f1f5f9 25%,#e5e7eb 37%,#f1f5f9 63%); background-size:400% 100%; animation: pr-shimmer 1.4s ease infinite; border-radius:4px; }
@keyframes pr-shimmer { 0% { background-position:100% 50%; } 100% { background-position:0 50%; } }
.pr-mc-empty { text-align:center;color:#9ca3af;padding:32px 16px;font-size:13px; }

@media (max-width: 768px) {
  .pr-desktop-table { display: none; }
  .pr-mobile-cards { display: flex; flex-direction: column; gap: 0; background: #f8fafc; }
  .pr-mobile-card { background: #fff; border-bottom: 1px solid #e5e7eb; padding: 12px 14px; cursor: pointer; transition: background .12s; }
  .pr-mobile-card:active { background: #f8f9fc; }
  .pr-mc-top { display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:4px; }
  .pr-mc-docno { font-weight:700;font-size:13.5px;color:#1a6ef7; }
  .pr-mc-mid { font-weight:600;font-size:13px;color:#111827;margin-bottom:4px; }

  .pr-mc-footer { display:flex;gap:6px;margin-top:8px;flex-wrap:wrap; }
  .pr-mc-btn { background:#fff;border:1px solid #e2e8f0;color:#374151;font-size:12px;font-weight:600;padding:5px 10px;border-radius:6px;cursor:pointer; }
  .pr-mc-btn.pr-mc-warn { border-color:#fde68a;color:#d97706; }
  .pr-mc-btn.pr-mc-danger { border-color:#fecaca;color:#dc2626; }
}
</style>