<template>
  <div class="se-page">

    <!-- ── Summary strip ── -->
    <div class="se-kpi-strip">
      <div class="se-kpi" @click="activeTab='all'" :class="{active:activeTab==='all'}">
        <div class="se-kpi-ico" style="background:#eff6ff;color:#2563eb"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg></div>
        <div><div class="se-kpi-lbl">Total Entries</div><div class="se-kpi-val">{{ kpi.total }}</div></div>
      </div>
      <div class="se-kpi" @click="activeTab='Material Receipt'" :class="{active:activeTab==='Material Receipt'}">
        <div class="se-kpi-ico" style="background:#f0fdf4;color:#16a34a"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12l7 7 7-7"/></svg></div>
        <div><div class="se-kpi-lbl">Receipts (In)</div><div class="se-kpi-val" style="color:#16a34a">{{ kpi.receipts }}</div></div>
      </div>
      <div class="se-kpi" @click="activeTab='Material Issue'" :class="{active:activeTab==='Material Issue'}">
        <div class="se-kpi-ico" style="background:#fff7ed;color:#ea580c"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 19V5M5 12l7-7 7 7"/></svg></div>
        <div><div class="se-kpi-lbl">Issues (Out)</div><div class="se-kpi-val" style="color:#ea580c">{{ kpi.issues }}</div></div>
      </div>
      <div class="se-kpi" @click="activeTab='Material Transfer'" :class="{active:activeTab==='Material Transfer'}">
        <div class="se-kpi-ico" style="background:#f0f9ff;color:#0284c7"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M15 7l5 5-5 5"/></svg></div>
        <div><div class="se-kpi-lbl">Transfers</div><div class="se-kpi-val" style="color:#0284c7">{{ kpi.transfers }}</div></div>
      </div>
      <div class="se-kpi se-kpi-value">
        <div class="se-kpi-ico" style="background:#faf5ff;color:#7c3aed"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a10 10 0 1 0 0 20A10 10 0 0 0 12 2z"/><path d="M12 6v6l4 2"/></svg></div>
        <div><div class="se-kpi-lbl">Net Value In</div><div class="se-kpi-val" style="color:#7c3aed;font-size:13px">{{ fmtCur(kpi.valueIn) }}</div></div>
      </div>
    </div>

    <!-- ── Action bar ── -->
    <div class="se-actions">
      <div class="se-search-wrap">
        <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
        <input v-model="search" placeholder="Search entry #, item, remarks…" class="se-search-input" />
      </div>
      <div class="se-filter-row">
        <div style="display:flex;gap:6px;align-items:center;font-size:12px;color:#6b7280">
          <span>Source:</span>
          <select v-model="sourceFilter" class="se-filter-select">
            <option value="all">All</option>
            <option value="purchase">From Purchase</option>
            <option value="sale">From Sale</option>
            <option value="adjustment">Stock Adjustment</option>
            <option value="manual">Manual</option>
          </select>
        </div>
        <div style="display:flex;gap:6px;align-items:center;font-size:12px;color:#6b7280">
          <span>From</span>
          <input type="date" v-model="dateFrom" class="se-date-input"/>
          <span>To</span>
          <input type="date" v-model="dateTo" class="se-date-input"/>
        </div>
      </div>
      <div style="display:flex;gap:8px;">
        <button class="se-btn-ghost" @click="load"><span v-html="icon('refresh',14)"></span></button>
        <button class="se-btn-ghost" @click="exportCSV" :disabled="!sorted.length"><span v-html="icon('download',14)"></span> Export</button>
        <button class="se-btn-primary" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''" @click="openNew"><span v-html="icon('plus',13)"></span> New Entry</button>
      </div>
    </div>

    <!-- ── Type pills ── -->
    <div style="display:flex;gap:6px;flex-wrap:wrap">
      <button v-for="t in tabs" :key="t.key" class="se-pill" :class="{active:activeTab===t.key}" @click="activeTab=t.key">
        <span class="se-pill-dot" :style="'background:'+t.color"></span>
        {{ t.label }}
        <span class="se-pill-cnt">{{ t.cnt }}</span>
      </button>
    </div>

    <!-- ── Table ── -->
    <div class="se-card">
      <table class="se-table se-desktop-table">
        <thead><tr>
          <th @click="sort('name')" class="sortable">Entry # <span v-html="sortArrow('name')"></span></th>
          <th @click="sort('stock_entry_type')" class="sortable">Type <span v-html="sortArrow('stock_entry_type')"></span></th>
          <th @click="sort('posting_date')" class="sortable">Date <span v-html="sortArrow('posting_date')"></span></th>
          <th>Source</th>
          <th>Warehouse Flow</th>
          <th class="ta-r">Items</th>
          <th @click="sort('value_difference')" class="sortable ta-r">Value <span v-html="sortArrow('value_difference')"></span></th>
          <th>Status</th>
          <th style="width:44px"></th>
        </tr></thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 8" :key="n"><td colspan="9"><div class="se-shimmer"></div></td></tr>
          </template>
          <template v-else>
            <tr v-for="e in paginated" :key="e.name" class="se-row" @click="openView(e)">
              <td><span class="se-num">{{ e.name }}</span></td>
              <td><span class="se-type-badge" :style="typeStyle(e.stock_entry_type)">{{ e.stock_entry_type||'—' }}</span></td>
              <td class="mono-sm text-muted">{{ fmtDate(e.posting_date) }}</td>
              <td>
                <div class="se-source-cell">
                  <span class="se-source-dot" :style="'background:'+sourceInfo(e).color"></span>
                  <span style="font-size:12px;font-weight:600;color:#374151">{{ sourceInfo(e).label }}</span>
                  <DocLink v-if="e.work_order" doctype="Work Order" :name="e.work_order" class="se-source-ref" />
                  <DocLink v-else-if="e.reference_name" :doctype="e.reference_doctype" :name="e.reference_name" class="se-source-ref" />
                </div>
              </td>
              <td>
                <div class="se-wh-flow">
                  <span class="se-wh-tag" v-if="e.from_warehouse">{{ shortWH(e.from_warehouse) }}</span>
                  <span v-if="e.from_warehouse && e.to_warehouse" style="color:#9ca3af;font-size:11px">→</span>
                  <span class="se-wh-tag se-wh-tag-to" v-if="e.to_warehouse">{{ shortWH(e.to_warehouse) }}</span>
                  <span v-if="!e.from_warehouse && !e.to_warehouse" class="text-muted" style="font-size:12px">—</span>
                </div>
              </td>
              <td class="ta-r"><span class="se-item-cnt">{{ e._itemCount||'—' }}</span></td>
              <td class="ta-r">
                <span :style="'font-size:12.5px;font-weight:600;color:'+(flt(e.value_difference)>=0?'#16a34a':'#dc2626')">
                  {{ flt(e.value_difference)>=0?'+':'' }}{{ fmtCur(e.value_difference) }}
                </span>
              </td>
              <td><span class="se-badge" :class="statusClass(e)">{{ statusLabel(e) }}</span></td>
              <td @click.stop style="display:flex;gap:4px">
                <button class="se-act-btn" @click="openView(e)" title="View"><span v-html="icon('eye',13)"></span></button>
                <button v-if="e.docstatus===0 && $canEdit('inventory')" class="se-act-btn" @click="openEdit(e)" title="Edit"><span v-html="icon('edit',13)"></span></button>
                <button v-if="e.docstatus===1 && $canEdit('inventory')" class="se-act-btn" :disabled="actionBusy" @click="editSubmittedEntry(e)" title="Edit (cancels &amp; re-posts corrected GL)"><span v-html="icon('edit',13)"></span></button>
                <button v-if="e.docstatus===1 && $canEdit('inventory')" class="se-act-btn" :disabled="actionBusy" @click="cancelSubmittedEntry(e)" title="Cancel entry"><span v-html="icon('x',13)"></span></button>
                <button v-if="e.docstatus===2 && $canDelete('inventory')" class="se-act-btn" :disabled="actionBusy" @click="deleteEntry(e)" title="Delete cancelled entry"><span v-html="icon('trash',13)"></span></button>
              </td>
            </tr>
            <tr v-if="!sorted.length">
              <td colspan="9" class="se-empty">
                <div style="font-size:32px;margin-bottom:8px">📦</div>
                <div style="font-weight:600;margin-bottom:4px">No stock entries found</div>
                <div style="font-size:13px;color:#9ca3af;margin-bottom:12px">Try changing the filter or date range</div>
                <button class="se-btn-primary" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''" @click="openNew"><span v-html="icon('plus',13)"></span> New Entry</button>
              </td>
            </tr>
          </template>
        </tbody>
      </table>

      <!-- Mobile cards (shown at ≤768px) -->
      <div class="se-mobile-cards">
        <template v-if="loading">
          <div v-for="n in 6" :key="n" class="se-mobile-card se-mc--skeleton">
            <div class="se-mc-shimmer" style="height:13px;width:55%;margin-bottom:8px"></div>
            <div class="se-mc-shimmer" style="height:11px;width:40%;margin-bottom:6px"></div>
            <div class="se-mc-shimmer" style="height:11px;width:65%"></div>
          </div>
        </template>
        <div v-else-if="!sorted.length" class="se-mc-empty">
          <div style="font-size:32px;margin-bottom:8px">📦</div>
          <div>No stock entries found</div>
        </div>
        <template v-else>
          <div v-for="e in paginated" :key="e.name" class="se-mobile-card" @click="openView(e)">
            <div class="se-mc-top">
              <span class="se-mc-docno">{{ e.name }}</span>
              <span style="display:flex;gap:6px;align-items:center">
                <span class="se-badge" :class="statusClass(e)">{{ statusLabel(e) }}</span>
                <button v-if="e.docstatus===0 && $canEdit('inventory')" class="se-act-btn" @click.stop="openEdit(e)" title="Edit"><span v-html="icon('edit',12)"></span></button>
                <button v-if="e.docstatus===1 && $canEdit('inventory')" class="se-act-btn" :disabled="actionBusy" @click.stop="editSubmittedEntry(e)" title="Edit (cancels &amp; re-posts corrected GL)"><span v-html="icon('edit',12)"></span></button>
                <button v-if="e.docstatus===1 && $canEdit('inventory')" class="se-act-btn" :disabled="actionBusy" @click.stop="cancelSubmittedEntry(e)" title="Cancel entry"><span v-html="icon('x',12)"></span></button>
                <button v-if="e.docstatus===2 && $canDelete('inventory')" class="se-act-btn" :disabled="actionBusy" @click.stop="deleteEntry(e)" title="Delete cancelled entry"><span v-html="icon('trash',12)"></span></button>
              </span>
            </div>
            <div class="se-mc-mid">
              <span class="se-type-badge" :style="typeStyle(e.stock_entry_type)">{{ e.stock_entry_type||'—' }}</span>
            </div>
            <div class="se-mc-meta">
              <span>{{ fmtDate(e.posting_date) }}</span>
              <span :style="'font-weight:700;color:'+(flt(e.value_difference)>=0?'#16a34a':'#dc2626')">
                {{ flt(e.value_difference)>=0?'+':'' }}{{ fmtCur(e.value_difference) }}
              </span>
            </div>
          </div>
        </template>
      </div>
    </div>
    <div v-if="sorted.length > pageSize" style="display:flex;justify-content:space-between;align-items:center;font-size:12px;color:#6b7280;padding:4px 2px">
      <span>Showing {{ paginated.length }} of {{ sorted.length }}</span>
      <div style="display:flex;gap:4px">
        <button class="se-pg-btn" :disabled="page===1" @click="page--">‹</button>
        <span style="padding:4px 8px;font-weight:600">{{ page }} / {{ totalPages }}</span>
        <button class="se-pg-btn" :disabled="page===totalPages" @click="page++">›</button>
      </div>
    </div>

    <!-- ── Create Drawer ── -->
    <div v-if="drawerOpen" class="se-overlay" @click.self="drawerOpen=false"></div>
    <div class="se-drawer" :class="{open:drawerOpen}">
      <div class="se-dheader" :style="'background:'+typeGradient(form.stock_entry_type)">
        <button class="se-dclose se-dclose-abs" @click="drawerOpen=false"><span v-html="icon('x',16)"></span></button>
        <div class="se-dh-top">
          <div class="se-dh-ico"><span v-html="icon('stack',20)" style="color:#fff"></span></div>
          <div>
            <div class="se-dh-title" style="color:#fff">{{ editingName ? 'Edit Stock Entry — ' + editingName : 'New Stock Entry' }}</div>
            <div class="se-dh-sub" style="color:rgba(255,255,255,.75)">{{ editingName ? 'Editing draft entry' : 'Record a stock movement' }}</div>
          </div>

        </div>
      </div>
      <div class="se-dbody">
        <div class="se-fields-grid">
          <div class="se-field" style="grid-column:1/-1">
            <label class="se-label">Entry Type <span class="req">*</span></label>
            <select v-model="form.stock_entry_type" class="se-select">
              <option value="Material Receipt">Material Receipt — Stock coming IN</option>
              <option value="Material Issue">Material Issue — Stock going OUT</option>
              <option value="Material Transfer">Material Transfer — Move between warehouses</option>
            </select>
          </div>
          <div class="se-field">
            <label class="se-label">Date <span class="req">*</span></label>
            <input v-model="form.posting_date" type="date" class="se-input" />
          </div>
          <div class="se-field">
            <label class="se-label">Adjustment Reason</label>
            <input v-model="form.adjustment_reason" class="se-input" placeholder="e.g. Annual count, damage…"/>
          </div>
          <div class="se-field" v-if="showFromWh">
            <label class="se-label">From Warehouse <span v-if="fromWhRequired" class="req">*</span></label>
            <SearchableSelect v-model="form.from_warehouse" :options="warehouses" placeholder="Source warehouse…" @search="fetchWarehouses" />
          </div>
          <div class="se-field" v-if="showToWh">
            <label class="se-label">To Warehouse <span v-if="toWhRequired" class="req">*</span></label>
            <SearchableSelect v-model="form.to_warehouse" :options="warehouses" placeholder="Destination warehouse…" @search="fetchWarehouses" />
          </div>
        </div>

        <div class="se-section-title" style="margin-top:4px">Items</div>

        <!-- Desktop table -->
        <div class="se-items-table se-add-items-desktop">
          <div class="se-items-head">
            <div>Item</div>
            <div class="ta-r">Qty</div>
            <div class="ta-r">Rate (OMR)</div>
            <div></div>
          </div>
          <div v-for="line in lines" :key="line.id" class="se-items-line">
            <div class="se-items-row">
              <div>
  <SearchableSelect
    v-model="line.item_code"
    :options="items"
    placeholder="Item…"
    @search="fetchItems"
    @select="opt=>onItemSelect(line,opt)"
  />
  <div
    v-if="line.item_code"
    style="font-size:11px;color:#6b7280;margin-top:4px;margin-left:2px;"
  >
    UOM: {{ line.stock_uom || 'Nos' }}
  </div>
</div>
              <div><input v-model.number="line.qty" type="number" min="0" step="0.001" class="se-input ta-r" /></div>
              <div><input v-model.number="line.basic_rate" type="number" min="0" step="0.01" class="se-input ta-r" /></div>
              <div><button @click="removeLine(line.id)" class="se-rm-line"><span v-html="icon('x',12)"></span></button></div>
            </div>
            <div v-if="line.has_batch_no" class="se-batch-row">
              <div class="se-batch-field" style="flex:1.6">
                <label class="se-label">Batch No <span v-if="batchRequired(line)" class="req">*</span></label>
                <SearchableSelect
                  v-model="line.batch_no"
                  :options="line.batchOptions"
                  :placeholder="batchPlaceholder(line)"
                  createable
                  @search="q=>fetchBatches(line,q)"
                  @select="opt=>onBatchSelect(line,opt)"
                  @create="val=>onBatchCreate(line,val)"
                  :compact="true"
                />
              </div>
              <div class="se-batch-field" style="flex:1">
                <label class="se-label">Mfg date</label>
                <input v-model="line.manufacturing_date" type="date" class="se-input" />
              </div>
              <div class="se-batch-field" style="flex:1">
                <label class="se-label">Expiry date</label>
                <input v-model="line.expiry_date" type="date" class="se-input" />
              </div>
            </div>
          </div>
          <div class="se-items-total" v-if="lines.length">
            <div style="grid-column:1/3;text-align:right;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#6b7280">Total</div>
            <div class="ta-r" style="font-weight:700;color:#0f172a">{{ fmtCur(lineTotal) }}</div>
            <div></div>
          </div>
          <button class="se-add-line" @click="addLine"><span v-html="icon('plus',12)"></span> Add Item</button>
        </div>

        <!-- Mobile cards -->
        <div class="se-add-items-mobile">
          <div v-for="(line, idx) in lines" :key="line.id" class="se-aic">
            <div class="se-aic-header">
              <span class="se-aic-num">Item {{ idx + 1 }}</span>
              <button @click="removeLine(line.id)" class="se-rm-line"><span v-html="icon('x',12)"></span></button>
            </div>
            <div class="se-aic-field">
              <label class="se-label">Item</label>
              <SearchableSelect
  v-model="line.item_code"
  :options="items"
  placeholder="Item…"
  @search="fetchItems"
  @select="opt=>onItemSelect(line,opt)"
/>
<div
  v-if="line.item_code"
  style="font-size:11px;color:#6b7280;margin-top:4px;margin-left:2px;"
>
  UOM: {{ line.stock_uom || 'Nos' }}
</div>
            </div>
            <div class="se-aic-row2">
              <div class="se-aic-field">
                <label class="se-label">Qty</label>
                <input v-model.number="line.qty" type="number" min="0" step="0.001" class="se-input ta-r" />
              </div>
              <div class="se-aic-field">
                <label class="se-label">Rate (OMR)</label>
                <input v-model.number="line.basic_rate" type="number" min="0" step="0.01" class="se-input ta-r" />
              </div>
            </div>
            <template v-if="line.has_batch_no">
              <div class="se-aic-field">
                <label class="se-label">Batch No <span v-if="batchRequired(line)" class="req">*</span></label>
                <SearchableSelect
                  v-model="line.batch_no"
                  :options="line.batchOptions"
                  :placeholder="batchPlaceholder(line)"
                  createable
                  @search="q=>fetchBatches(line,q)"
                  @select="opt=>onBatchSelect(line,opt)"
                  @create="val=>onBatchCreate(line,val)"
                />
              </div>
              <div class="se-aic-row2">
                <div class="se-aic-field" style="flex:1">
                  <label class="se-label">Mfg Date</label>
                  <input v-model="line.manufacturing_date" type="date" class="se-input" />
                </div>
                <div class="se-aic-field" style="flex:1">
                  <label class="se-label">Expiry Date</label>
                  <input v-model="line.expiry_date" type="date" class="se-input" />
                </div>
              </div>
            </template>
            <div class="se-aic-amount">Amount: <strong>{{ fmtCur(flt(line.qty) * flt(line.basic_rate)) }}</strong></div>
          </div>
          <div v-if="lines.length" class="se-aic-total">
            <span>Total</span><strong>{{ fmtCur(lineTotal) }}</strong>
          </div>
          <button class="se-add-line" @click="addLine"><span v-html="icon('plus',12)"></span> Add Item</button>
        </div>
        <div class="se-field">
          <label class="se-label">Remarks</label>
          <textarea v-model="form.remarks" rows="2" class="se-input" placeholder="Optional notes about this movement…"></textarea>
        </div>
      </div>
      <div class="se-dfooter">
        <button class="se-btn-ghost" @click="drawerOpen=false">Cancel</button>
        <button class="se-btn-save" :disabled="drawerSaving" @click="saveEntry(0)"><span v-html="icon('save',13)"></span> {{ drawerSaving?'Saving…':'Save Draft' }}</button>
        <button class="se-btn-primary" :disabled="drawerSaving" @click="saveEntry(1)"><span v-html="icon('check',13)"></span> {{ drawerSaving?'Submitting…':'Submit' }}</button>
      </div>
    </div>

    <!-- ── View Panel ── -->
    <div v-if="viewOpen" class="se-overlay" @click.self="viewOpen=false"></div>
    <div class="se-drawer se-view-drawer" :class="{open:viewOpen}">
      <template v-if="viewDoc">
        <div class="se-dheader" :style="'background:'+typeGradient(viewDoc.stock_entry_type)">
          <button class="se-dclose se-dclose-abs" @click="viewOpen=false"><span v-html="icon('x',16)"></span></button>
          <div class="se-dh-top">
            <div class="se-dh-ico" style="background:rgba(255,255,255,.2)"><span v-html="icon('stack',20)" style="color:#fff"></span></div>
            <div>
              <div class="se-dh-title" style="color:#fff">{{ viewDoc.name }}</div>
              <div class="se-dh-sub" style="color:rgba(255,255,255,.8)">{{ viewDoc.stock_entry_type }} · {{ fmtDate(viewDoc.posting_date) }}<template v-if="viewDoc.posting_time"> {{ viewDoc.posting_time }}</template></div>
            </div>
            <span class="se-badge" :class="statusClass(viewDoc)" style="margin-left:auto;flex-shrink:0">{{ statusLabel(viewDoc) }}</span>
          </div>
        </div>

        <div class="se-dbody">

          <!-- Source card -->
          <div class="se-source-card" :style="'border-color:'+sourceInfo(viewDoc).color+';background:'+sourceInfo(viewDoc).bg">
            <div style="font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#6b7280;margin-bottom:6px">Origin / Source</div>
            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
              <span class="se-source-label" :style="'background:'+sourceInfo(viewDoc).color+'22;color:'+sourceInfo(viewDoc).color">{{ sourceInfo(viewDoc).label }}</span>
              <template v-if="viewDoc.work_order">
                <span style="font-size:12px;color:#6b7280">Work Order:</span>
                <DocLink doctype="Work Order" :name="viewDoc.work_order" :mono-style="false" style="font-size:13px;font-weight:700;color:#2563eb;" />
              </template>
              <template v-else-if="viewDoc.reference_doctype && viewDoc.reference_name">
                <span style="font-size:12px;color:#6b7280">{{ viewDoc.reference_doctype }}:</span>
                <DocLink :doctype="viewDoc.reference_doctype" :name="viewDoc.reference_name" :mono-style="false" style="font-size:13px;font-weight:700;color:#2563eb;" />
              </template>
              <template v-else-if="viewDoc.adjustment_reason">
                <span style="font-size:13px;color:#374151">{{ viewDoc.adjustment_reason }}</span>
              </template>
              <template v-else>
                <span style="font-size:12.5px;color:#9ca3af">Created manually</span>
              </template>
            </div>
          </div>

          <!-- Warehouse flow -->
          <div class="se-view-section">
            <div class="se-view-sec-lbl">Warehouse Movement</div>
            <div class="se-wh-flow-big">
              <div class="se-wh-box" :class="viewDoc.from_warehouse?'':'se-wh-box-empty'">
                <div style="font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:#9ca3af;margin-bottom:3px">From</div>
                <div style="font-weight:600;color:#0f172a;font-size:13px">{{ viewDoc.from_warehouse||'—' }}</div>
              </div>
              <div class="se-wh-arrow">
                <svg width="32" height="16" viewBox="0 0 32 16"><path d="M0 8h28M24 4l6 4-6 4" stroke="#94a3b8" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>
              </div>
              <div class="se-wh-box" :class="viewDoc.to_warehouse?'':'se-wh-box-empty'">
                <div style="font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:#9ca3af;margin-bottom:3px">To</div>
                <div style="font-weight:600;color:#0f172a;font-size:13px">{{ viewDoc.to_warehouse||'—' }}</div>
              </div>
            </div>
          </div>

          <!-- Items table -->
          <div class="se-view-section" v-if="viewLoading">
            <div class="se-view-sec-lbl">Items</div>
            <div v-for="n in 3" :key="n" class="se-shimmer" style="height:36px;margin-bottom:6px;border-radius:6px"></div>
          </div>
          <div class="se-view-section" v-else-if="(viewDoc.items||[]).length">
            <div class="se-view-sec-lbl">Items ({{ viewDoc.items.length }})</div>

            <!-- Desktop table -->
            <table class="se-view-items-tbl se-view-items-desktop">
              <thead>
                <tr>
                  <th>Item</th>
                  <th>Batch</th>
                  <th>From WH</th>
                  <th>To WH</th>
                  <th class="ta-r">Qty</th>
                  <th class="ta-r">Rate</th>
                  <th class="ta-r">Amount</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="it in viewDoc.items" :key="it.name||it.idx">
                  <td>
                    <div style="font-weight:600;font-size:12.5px">{{ it.item_code }}</div>
                    <div v-if="it.item_name && it.item_name!==it.item_code" style="font-size:11px;color:#9ca3af">{{ it.item_name }}</div>
                  </td>
                  <td class="text-muted" style="font-size:12px">{{ it.batch_no||'—' }}</td>
                  <td class="text-muted" style="font-size:12px">{{ it.s_warehouse||viewDoc.from_warehouse||'—' }}</td>
                  <td class="text-muted" style="font-size:12px">{{ it.t_warehouse||viewDoc.to_warehouse||'—' }}</td>
                  <td class="ta-r">{{ it.qty }} <span style="color:#9ca3af;font-size:10px">{{ it.uom||'' }}</span></td>
                  <td class="ta-r">{{ fmtCur(it.basic_rate) }}</td>
                  <td class="ta-r" style="font-weight:600">{{ fmtCur(flt(it.qty)*flt(it.basic_rate)) }}</td>
                </tr>
              </tbody>
            </table>

            <!-- Mobile item cards -->
            <div class="se-view-items-mobile">
              <div v-for="it in viewDoc.items" :key="it.name||it.idx" class="se-vic">
                <div class="se-vic-top">
                  <div>
                    <div class="se-vic-name">{{ it.item_code }}</div>
                    <div v-if="it.item_name && it.item_name!==it.item_code" class="se-vic-sub">{{ it.item_name }}</div>
                  </div>
                  <div class="se-vic-amount">{{ fmtCur(flt(it.qty)*flt(it.basic_rate)) }}</div>
                </div>
                <div class="se-vic-grid">
                  <div class="se-vic-cell" v-if="it.batch_no">
                    <span class="se-vic-lbl">Batch</span>
                    <span class="se-vic-val">{{ it.batch_no }}</span>
                  </div>
                  <div class="se-vic-cell">
                    <span class="se-vic-lbl">Qty</span>
                    <span class="se-vic-val">{{ it.qty }} <span style="color:#9ca3af;font-size:10px">{{ it.uom||'' }}</span></span>
                  </div>
                  <div class="se-vic-cell">
                    <span class="se-vic-lbl">Rate</span>
                    <span class="se-vic-val">{{ fmtCur(it.basic_rate) }}</span>
                  </div>
                  <div class="se-vic-cell">
                    <span class="se-vic-lbl">From WH</span>
                    <span class="se-vic-val">{{ it.s_warehouse||viewDoc.from_warehouse||'—' }}</span>
                  </div>
                  <div class="se-vic-cell">
                    <span class="se-vic-lbl">To WH</span>
                    <span class="se-vic-val">{{ it.t_warehouse||viewDoc.to_warehouse||'—' }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Value summary -->
          <div class="se-view-section">
            <div class="se-view-sec-lbl">Value Summary</div>
            <div class="se-val-strip">
              <div class="se-val-box se-val-in">
                <div class="se-val-lbl">Incoming Value</div>
                <div class="se-val-num">{{ fmtCur(viewDoc.total_incoming_value||0) }}</div>
              </div>
              <div class="se-val-box se-val-out">
                <div class="se-val-lbl">Outgoing Value</div>
                <div class="se-val-num">{{ fmtCur(viewDoc.total_outgoing_value||0) }}</div>
              </div>
              <div class="se-val-box se-val-diff">
                <div class="se-val-lbl">Net Difference</div>
                <div class="se-val-num" :style="'color:'+(flt(viewDoc.value_difference)>=0?'#16a34a':'#dc2626')">
                  {{ flt(viewDoc.value_difference)>=0?'+':'' }}{{ fmtCur(viewDoc.value_difference||0) }}
                </div>
              </div>
            </div>
          </div>

          <!-- Remarks -->
          <div class="se-view-section" v-if="viewDoc.remarks">
            <div class="se-view-sec-lbl">Remarks</div>
            <div style="font-size:13px;color:#374151;line-height:1.5;background:#f8fafc;border-radius:6px;padding:10px 12px;border:1px solid #e2e8f0">{{ viewDoc.remarks }}</div>
          </div>

          <!-- Journal (debit/credit ledger) -->
          <div class="se-view-section">
            <div class="se-view-sec-lbl">Journal</div>
            <template v-if="viewDoc.docstatus===1">
              <JournalTab
                voucher-type="Stock Entry"
                :voucher-no="viewDoc.name"
                label="Stock Entry"
                :currency="viewDoc.currency || 'INR'"
              />
            </template>
            <div v-else style="color:#9ca3af;font-size:13px;padding:8px 0">Journal entries are posted once the stock entry is submitted.</div>
          </div>

          <!-- Timestamps -->
          <div class="se-view-section">
            <div style="display:flex;gap:16px;flex-wrap:wrap">
              <div v-if="viewDoc.company"><span class="se-meta-lbl">Company</span><div style="font-size:12.5px;margin-top:2px">{{ viewDoc.company }}</div></div>
              <div v-if="viewDoc.owner"><span class="se-meta-lbl">Created by</span><div style="font-size:12.5px;margin-top:2px">{{ viewDoc.owner }}</div></div>
              <div v-if="viewDoc.creation"><span class="se-meta-lbl">Created</span><div style="font-size:12.5px;margin-top:2px;">{{ fmtDate(viewDoc.creation?.slice(0,10)) }}</div></div>
            </div>
          </div>

        </div>
        <div class="se-dfooter">
          <button class="se-btn-ghost" @click="viewOpen=false">Close</button>
          <button v-if="viewDoc.docstatus===0 && $canEdit('inventory')" class="se-btn-ghost" @click="openEdit(viewDoc); viewOpen=false">
            <span v-html="icon('edit',13)"></span> Edit
          </button>
          <button v-if="viewDoc.docstatus===0" class="se-btn-primary" @click="submitEntry(viewDoc.name)">
            <span v-html="icon('check',13)"></span> Submit
          </button>
          <button v-if="viewDoc.docstatus===1 && $canEdit('inventory')" class="se-btn-ghost" :disabled="actionBusy" @click="editSubmittedEntry(viewDoc)" title="Cancels this entry and reverses its GL/stock ledger, then opens a corrected draft">
            <span v-html="icon('edit',13)"></span> Edit
          </button>
          <button v-if="viewDoc.docstatus===1 && $canEdit('inventory')" class="se-btn-ghost" :disabled="actionBusy" @click="cancelSubmittedEntry(viewDoc)">
            <span v-html="icon('x',13)"></span> Cancel Entry
          </button>
          <button v-if="viewDoc.docstatus===2 && $canDelete('inventory')" class="se-btn-ghost" :disabled="actionBusy" @click="deleteEntry(viewDoc)" title="Delete cancelled entry">
            <span v-html="icon('trash',13)"></span> Delete
          </button>
        </div>
      </template>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { apiList, apiGet, apiGET, apiSave, apiSubmit, apiCancel, apiDelete, resolveCompany, apiLinkValues } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { useConfirm } from "../composables/useConfirm.js";
import { icon } from "../utils/icons.js";
import { flt, fmtDate } from "../utils/format.js";
import SearchableSelect from "../components/SearchableSelect.vue";
import JournalTab from "../components/JournalTab.vue";
import DocLink from "../components/DocLink.vue";

const { toast } = useToast();
const { confirm } = useConfirm();
const route = useRoute();
const actionBusy = ref(false);

const activeTab  = ref("all");
const sourceFilter = ref("all");
const dateFrom   = ref("");
const dateTo     = ref("");
const search     = ref("");
const page       = ref(1);
const pageSize   = 30;

const list        = ref([]);
const loading     = ref(false);
const drawerOpen  = ref(false);
const drawerSaving = ref(false);
const editingName = ref("");
const viewOpen    = ref(false);
const viewDoc     = ref(null);
const viewLoading = ref(false);
const warehouses  = ref([]);
const items       = ref([]);
const lines       = ref([]);
const sortCol     = ref("posting_date");
const sortDir     = ref("desc");
let _id = 1;
const blankLine = () => ({
  id: _id++, item_code: "", qty: 1, basic_rate: 0, s_warehouse: "", t_warehouse: "",
  has_batch_no: 0, stock_uom: "", batch_no: "", manufacturing_date: "", expiry_date: "", batchOptions: [],
});

const form = reactive({
  stock_entry_type: "Material Receipt",
  posting_date: new Date().toISOString().slice(0, 10),
  from_warehouse: "", to_warehouse: "",
  adjustment_reason: "", remarks: "",
});

const TYPE_META = {
  "Material Receipt":  { color: "#16a34a", grad: "linear-gradient(135deg,#064e3b,#16a34a)" },
  "Material Issue":    { color: "#ea580c", grad: "linear-gradient(135deg,#7c2d12,#ea580c)" },
  "Material Transfer": { color: "#0284c7", grad: "linear-gradient(135deg,#0c4a6e,#0284c7)" },
  "Manufacture":       { color: "#7c3aed", grad: "linear-gradient(135deg,#3b0764,#7c3aed)" },
  "Repack":            { color: "#d97706", grad: "linear-gradient(135deg,#78350f,#d97706)" },
};

// Mirrors SE_TYPE_DIRECTION in stock_entry.py. Used to know which entry
// types have a source-warehouse leg — the backend auto-assigns batch_no
// FIFO/LIFO for those when left blank, so the UI doesn't need to force a
// value. Types without an "s" leg (Material Receipt, Repack) bring stock
// in fresh, so a Batch No must be supplied (new or existing) up front.
const TYPE_DIRECTION = {
  "Material Receipt":  { s: false, t: true },
  "Material Issue":    { s: true,  t: false },
  "Material Transfer": { s: true,  t: true },
  "Manufacture":       { s: true,  t: true },
  "Repack":            { s: false, t: false },
};
function batchRequired(line) {
  // Batch No is mandatory whenever the backend won't auto-assign one for
  // this line: incoming-only rows (no source leg), and Manufacture/Transfer
  // rows where the user hasn't given a source warehouse for this specific
  // line (so there's nothing for FIFO auto-assignment to draw from).
  const dir = TYPE_DIRECTION[form.stock_entry_type] || {};
  if (!dir.s) return true;
  return !(line.s_warehouse || form.from_warehouse);
}
function batchPlaceholder(line) {
  return batchRequired(line) ? "Select existing batch or type to create new" : "Leave blank to auto-assign (FIFO)";
}

// Warehouse fields shown per entry type: a Receipt has no source, an Issue has
// no destination; a Transfer/Manufacture uses both.
const showFromWh     = computed(() => form.stock_entry_type !== "Material Receipt");
const showToWh       = computed(() => form.stock_entry_type !== "Material Issue");
const fromWhRequired = computed(() => ["Material Issue", "Material Transfer", "Manufacture"].includes(form.stock_entry_type));
const toWhRequired   = computed(() => ["Material Receipt", "Material Transfer", "Manufacture"].includes(form.stock_entry_type));

const tabs = computed(() => [
  { key: "all",               label: "All",       color: "#6b7280", cnt: list.value.length },
  { key: "Material Receipt",  label: "Receipts",  color: "#16a34a", cnt: list.value.filter(e => e.stock_entry_type === "Material Receipt").length },
  { key: "Material Issue",    label: "Issues",    color: "#ea580c", cnt: list.value.filter(e => e.stock_entry_type === "Material Issue").length },
  { key: "Material Transfer", label: "Transfers", color: "#0284c7", cnt: list.value.filter(e => e.stock_entry_type === "Material Transfer").length },
]);

const kpi = computed(() => ({
  total:     list.value.length,
  receipts:  list.value.filter(e => e.stock_entry_type === "Material Receipt").length,
  issues:    list.value.filter(e => e.stock_entry_type === "Material Issue").length,
  transfers: list.value.filter(e => e.stock_entry_type === "Material Transfer").length,
  valueIn:   list.value.filter(e => e.docstatus === 1).reduce((s, e) => s + flt(e.total_incoming_value), 0),
}));

const lineTotal = computed(() => lines.value.reduce((s, l) => s + flt(l.qty) * flt(l.basic_rate), 0));

function typeStyle(t) {
  const m = TYPE_META[t] || { color: "#6b7280" };
  return `background:${m.color}18;color:${m.color};border:1px solid ${m.color}33`;
}
function typeGradient(t) {
  return (TYPE_META[t] || { grad: "linear-gradient(135deg,#374151,#6b7280)" }).grad;
}
function statusClass(e) {
  if (e.docstatus === 1) return "badge-green";
  if (e.docstatus === 2) return "badge-grey";
  return "badge-orange";
}
function statusLabel(e) {
  return e.docstatus === 1 ? "Submitted" : e.docstatus === 2 ? "Cancelled" : "Draft";
}
function shortWH(wh) {
  if (!wh) return "";
  const parts = wh.split(" - ");
  return parts[0].length > 18 ? parts[0].slice(0, 16) + "…" : parts[0];
}
function sourceInfo(e) {
  const rd = (e.reference_doctype || "").toLowerCase();
  if (rd.includes("purchase invoice") || rd.includes("purchase receipt"))
    return { label: "Purchase", color: "#0891b2", bg: "#f0f9ff" };
  if (rd.includes("sales invoice") || rd.includes("delivery"))
    return { label: "Sale", color: "#dc2626", bg: "#fff7f7" };
  if (rd.includes("purchase order"))
    return { label: "Purchase Order", color: "#7c3aed", bg: "#faf5ff" };
  if (e.adjustment_reason || e.stock_entry_type === "Repack")
    return { label: "Adjustment", color: "#7c3aed", bg: "#faf5ff" };
  if (e.stock_entry_type === "Manufacture")
    return { label: "Manufacturing", color: "#d97706", bg: "#fffbeb" };
  if (e.stock_entry_type === "Material Transfer")
    return { label: "Transfer", color: "#0284c7", bg: "#f0f9ff" };
  const rem = (e.remarks || "").toLowerCase();
  if (rem.includes("purchase invoice")) return { label: "Purchase", color: "#0891b2", bg: "#f0f9ff" };
  if (rem.includes("sales invoice"))    return { label: "Sale",     color: "#dc2626", bg: "#fff7f7" };
  if (rem.includes("adjustment"))       return { label: "Adjustment", color: "#7c3aed", bg: "#faf5ff" };
  return { label: "Manual", color: "#6b7280", bg: "#f9fafb" };
}

const filtered = computed(() => {
  let r = list.value;
  if (activeTab.value !== "all") r = r.filter(e => e.stock_entry_type === activeTab.value);
  if (sourceFilter.value !== "all") {
    r = r.filter(e => {
      const si = sourceInfo(e).label.toLowerCase();
      if (sourceFilter.value === "purchase")   return si === "purchase" || si === "purchase order";
      if (sourceFilter.value === "sale")       return si === "sale";
      if (sourceFilter.value === "adjustment") return si === "adjustment";
      if (sourceFilter.value === "manual")     return si === "manual";
      return true;
    });
  }
  if (dateFrom.value) r = r.filter(e => e.posting_date >= dateFrom.value);
  if (dateTo.value)   r = r.filter(e => e.posting_date <= dateTo.value);
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    r = r.filter(e =>
      (e.name || "").toLowerCase().includes(q) ||
      (e.stock_entry_type || "").toLowerCase().includes(q) ||
      (e.from_warehouse || "").toLowerCase().includes(q) ||
      (e.to_warehouse || "").toLowerCase().includes(q) ||
      (e.remarks || "").toLowerCase().includes(q) ||
      (e.reference_name || "").toLowerCase().includes(q) ||
      (e.work_order || "").toLowerCase().includes(q)
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
function fmtCur(v) {
  const n = flt(v);
  try {
    return new Intl.NumberFormat("en-OM", { style: "currency", currency: "OMR" }).format(n);
  } catch {
    return "ر.ع. " + n.toLocaleString("en-OM", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
  }
}

async function load() {
  loading.value = true;
  try {
    const co = await resolveCompany();
    const rows = await apiList("Stock Entry", {
      fields: ["name", "stock_entry_type", "posting_date", "from_warehouse", "to_warehouse",
               "value_difference", "total_incoming_value", "total_outgoing_value",
               "docstatus", "remarks", "reference_doctype", "reference_name", "work_order",
               "adjustment_reason", "company", "owner", "creation"],
      filters: [["company", "=", co]],
      limit: 100000, order: "posting_date desc, creation desc",
    });
    // Attach item count from a separate list call (names only)
    list.value = rows;
  } catch (e) {
    toast.error(e.message || "Failed to load stock entries");
  } finally {
    loading.value = false;
  }
}

async function openView(e) {
  viewDoc.value = { ...e, items: [] };
  viewOpen.value = true;
  viewLoading.value = true;
  try {
    const full = await apiGet("Stock Entry", e.name);
    if (full) viewDoc.value = full;
  } catch { /* keep list-row data */ }
  viewLoading.value = false;
}

async function submitEntry(name) {
  try {
    await apiSubmit("Stock Entry", name);
    toast.success("Stock Entry submitted");
    viewOpen.value = false;
    await load();
  } catch (e) { toast.error(e.message || "Submit failed"); }
}

async function fetchWarehouses(q = "") {
  try {
    const co = await resolveCompany();
    const r = await apiList("Warehouse", {
      fields: ["name"],
      filters: [["company", "=", co], ["is_group", "=", 0], ...(q ? [["name", "like", `%${q}%`]] : [])],
      limit: 20,
    });
    warehouses.value = r.map(x => ({ label: x.name, value: x.name }));
  } catch { warehouses.value = []; }
}
async function fetchItems(q = "") {
  try {
    const r = await apiLinkValues("Item", q);
    items.value = r.map(x => ({ label: x.name, value: x.name }));
  } catch { items.value = []; }
}
async function fetchBatches(line, q = "") {
  if (!line.item_code) { line.batchOptions = []; return; }
  const forItem = line.item_code;
  try {
    // NOTE: Batch.batch_qty is only an incrementally-adjusted cache and can
    // drift/double-count (e.g. same batch present in multiple warehouses).
    // Use the live SLE-aggregated qty, same as Bills/Invoices/PurchaseOrders,
    // instead of querying the raw Batch doctype.
    const r = await apiGET("zoho_books_clone.api.inventory.get_batches_for_item", { item_code: forItem, search: q || "" }) || [];
    // Item may have changed while this request was in flight — don't let a
    // stale response overwrite the options for whatever item is selected now.
    if (line.item_code !== forItem) return;
    line.batchOptions = r.map(b => ({
      value: b.batch_no,
      label: (b.qty !== undefined && b.qty !== null) ? `${b.batch_no} (Qty: ${b.qty})` : b.batch_no,
      manufacturing_date: b.manufacturing_date || "",
      expiry_date: b.expiry_date || "",
    }));
  } catch { if (line.item_code === forItem) line.batchOptions = []; }
}
function onBatchSelect(line, opt) {
  line.batch_no = opt?.value ?? opt;
  // Existing batch picked — mirror its dates exactly (including clearing them
  // if the batch has none) so the form never shows leftover dates from a
  // previously-typed "create new batch" attempt as if they belonged to this
  // batch.
  line.manufacturing_date = (opt && opt.manufacturing_date) || "";
  line.expiry_date = (opt && opt.expiry_date) || "";
}
function onBatchCreate(line, typed) {
  // User typed a Batch No that doesn't exist yet — treat as a new batch
  // entry; mfg/expiry stay editable below and the batch is created on save.
  line.batch_no = typed;
}
async function onItemSelect(line, opt) {
  line.item_code = opt?.value ?? opt;
  if (!line.item_code) return;
  try {
    const r = await apiList("Item", { fields: ["name", "standard_buying_rate", "standard_rate", "has_batch_no", "stock_uom"], filters: [["name", "=", line.item_code]], limit: 1 });
    const it = r && r[0];
    if (it) {
  if (!flt(line.basic_rate)) line.basic_rate = flt(it.standard_buying_rate) || flt(it.standard_rate) || 0;
  line.has_batch_no = it.has_batch_no ? 1 : 0;
  line.stock_uom = it.stock_uom || "";
      // Item changed — whatever batch/dates were on the line belonged to the
      // previous item and must not ride along, whether the new item is
      // batch-tracked or not.
      line.batch_no = "";
      line.manufacturing_date = "";
      line.expiry_date = "";
      line.batchOptions = [];
      if (line.has_batch_no) {
        await fetchBatches(line, "");
      }
    }
  } catch {}
}
function addLine() { lines.value.push(blankLine()); }
function removeLine(id) { if (lines.value.length > 1) lines.value = lines.value.filter(l => l.id !== id); }

function openNew() {
  editingName.value = "";
  Object.assign(form, {
    stock_entry_type: "Material Receipt",
    posting_date: new Date().toISOString().slice(0, 10),
    from_warehouse: "", to_warehouse: "", adjustment_reason: "", remarks: "",
  });
  lines.value = [blankLine()];
  fetchWarehouses(""); fetchItems("");
  drawerOpen.value = true;
}

async function openEdit(e, { force = false } = {}) {
  if (e.docstatus !== 0 && !force) return;
  editingName.value = e.name;
  Object.assign(form, {
    stock_entry_type: e.stock_entry_type || "Material Receipt",
    posting_date: e.posting_date || new Date().toISOString().slice(0, 10),
    from_warehouse: e.from_warehouse || "", to_warehouse: e.to_warehouse || "",
    adjustment_reason: e.adjustment_reason || "", remarks: e.remarks || "",
  });
  lines.value = [blankLine()];
  fetchWarehouses(""); fetchItems("");
  drawerOpen.value = true;
  try {
    const doc = await apiGet("Stock Entry", e.name);
    if (doc?.items?.length) {
      const built = await Promise.all(doc.items.map(async (it) => {
        const line = {
          id: _id++, item_code: it.item_code || "", qty: flt(it.qty) || 1, basic_rate: flt(it.basic_rate) || 0,
          s_warehouse: it.s_warehouse || "", t_warehouse: it.t_warehouse || "",
          has_batch_no: 0, batch_no: it.batch_no || "", manufacturing_date: "", expiry_date: "", batchOptions: [],
        };
        try {
          const r = await apiList("Item", { fields: ["name", "has_batch_no", "stock_uom"], filters: [["name", "=", line.item_code]], limit: 1 });
          line.has_batch_no = r?.[0]?.has_batch_no ? 1 : 0;
line.stock_uom = r?.[0]?.stock_uom || "";
        } catch {}
        if (line.has_batch_no && line.batch_no) {
          try {
            const b = await apiList("Batch", {
              fields: ["name", "manufacturing_date", "expiry_date"],
              filters: [["name", "=", line.batch_no]], limit: 1,
            });
            const bd = b && b[0];
            if (bd) {
              line.manufacturing_date = bd.manufacturing_date || "";
              line.expiry_date = bd.expiry_date || "";
              // Just this one batch is already selected on the saved doc — no
              // need for a (possibly stale/global) qty label here.
              line.batchOptions = [{
                value: bd.name,
                label: bd.name,
                manufacturing_date: bd.manufacturing_date || "", expiry_date: bd.expiry_date || "",
              }];
            }
          } catch {}
        }
        return line;
      }));
      lines.value = built.length ? built : [blankLine()];
    }
  } catch {
    toast.error("Failed to load entry for editing");
  }
}

// A submitted Stock Entry already has stock ledger + GL entries posted against
// it — mutating those fields in place would leave the GL out of sync with the
// stock ledger (or need a hand-written reversal), and would destroy the audit
// trail of what was actually posted. So cancelling here calls Stock Entry's
// own on_cancel, which reverses the SLE and GL entries exactly (including
// batch qty adjustments), leaving the books consistent.
async function cancelSubmittedEntry(e) {
  const ok = await confirm({
    title: "Cancel this stock entry?",
    body: `Cancelling ${e.name} reverses its stock movement and ledger entries. This can't be undone.`,
    okLabel: "Cancel Entry", okStyle: "danger",
  });
  if (!ok) return;
  actionBusy.value = true;
  try {
    await apiCancel("Stock Entry", e.name);
    toast.success(`${e.name} cancelled`);
    viewOpen.value = false;
    await load();
  } catch (err) {
    toast.error(err.message || "Failed to cancel entry");
  } finally { actionBusy.value = false; }
}

// A cancelled Stock Entry's stock/GL impact was already fully reversed at
// cancel-time (on_cancel() flips the original rows to is_cancelled=1 and
// posts mirror rows) — the entry itself is just leftover audit trail at
// that point. Deleting it is safe: Stock Entry.on_trash() hard-deletes
// those already-inert ledger rows too, which is what actually lets a
// wrongly-entered Item pass its own "any Stock Ledger Entry left?" check
// afterward. A submitted (docstatus 1) entry can't be deleted this way —
// only cancel/edit apply until it's cancelled first.
async function deleteEntry(e) {
  const ok = await confirm({
    title: "Delete this stock entry?",
    body: `Permanently delete cancelled entry ${e.name}? This also removes its (already-reversed) ledger history. This can't be undone.`,
    okLabel: "Delete", okStyle: "danger",
  });
  if (!ok) return;
  actionBusy.value = true;
  try {
    await apiDelete("Stock Entry", e.name);
    toast.success(`${e.name} deleted`);
    viewOpen.value = false;
    await load();
  } catch (err) {
    toast.error(err.message || "Failed to delete entry");
  } finally { actionBusy.value = false; }
}

// "Edit" on a submitted entry is really "cancel + re-post": cancel reverses
// the wrong stock/GL impact exactly (via on_cancel), then a corrected draft
// is opened pre-filled with the same details so it can be fixed and
// resubmitted. Both the cancelled original and the new entry remain visible
// in the list for audit purposes — nothing is silently overwritten.
async function editSubmittedEntry(e) {
  const ok = await confirm({
    title: "Edit this stock entry?",
    body: `This cancels ${e.name} — reversing its stock and ledger entries — then opens a corrected entry with the same details. Both entries stay in the list for audit purposes.`,
    okLabel: "Cancel & Correct", okStyle: "danger",
  });
  if (!ok) return;
  actionBusy.value = true;
  try {
    await apiCancel("Stock Entry", e.name);
    viewOpen.value = false;
    await openEdit(e, { force: true }); // pre-fills form + lines from the (now cancelled) doc
    editingName.value = "";     // clear so Save creates a fresh draft, not an overwrite
  } catch (err) {
    toast.error(err.message || "Failed to cancel entry for editing");
  } finally { actionBusy.value = false; }
}

// Sum the requested qty per item, then verify the source warehouse holds enough.
// Returns an error string if short, or "" when everything is available.
async function checkAvailability(sourceWh) {
  const need = {};
  for (const l of lines.value) {
    if (!l.item_code) continue;
    need[l.item_code] = (need[l.item_code] || 0) + flt(l.qty);
  }
  for (const [item, qty] of Object.entries(need)) {
    if (qty <= 0) continue;
    try {
      const d = await apiGET("zoho_books_clone.api.inventory.get_item_stock_detail", { item_code: item, warehouse: sourceWh });
      const avail = flt(d?.warehouses?.[0]?.actual_qty);
      if (qty > avail) return `Not enough stock of "${item}" in ${sourceWh} — need ${qty}, available ${avail}.`;
    } catch { /* balance lookup failed — don't block the save */ }
  }
  return "";
}

async function saveEntry(submit) {
  const usable = lines.value.filter(l => l.item_code);
  if (!usable.length) return toast.error("At least one item is required");
  const type = form.stock_entry_type;
  if (fromWhRequired.value && !form.from_warehouse) return toast.error("From Warehouse is required");
  if (toWhRequired.value && !form.to_warehouse) return toast.error("To Warehouse is required");
  if (type === "Material Transfer" && form.from_warehouse && form.from_warehouse === form.to_warehouse)
    return toast.error("Source and destination warehouses must be different");
  for (const [idx, l] of usable.entries()) {
    if (l.has_batch_no && batchRequired(l) && !l.batch_no)
      return toast.error(`Row ${idx + 1}: ${l.item_code} is batch-tracked — Batch No is required`);
  }
  // Block disabled batches even if typed in manually (dropdown already
  // excludes them, but a typed-in exact match can bypass that). Also block a
  // typed batch_no that already exists for a *different* item — the pre-create
  // step below only checks whether the name exists, not who it belongs to, so
  // without this check a colliding name would silently reuse the wrong item's
  // batch and fail later at server-side submit, after we've already created
  // Batch records for the earlier rows (leaving them behind as orphans).
  const batchOwners = new Map(); // batch_no -> item_code, scoped to this save
  for (const [idx, l] of usable.entries()) {
    if (!l.has_batch_no || !l.batch_no) continue;
    if (batchOwners.has(l.batch_no) && batchOwners.get(l.batch_no) !== l.item_code) {
      return toast.error(`Row ${idx + 1}: Batch "${l.batch_no}" is already used for a different item in this entry.`);
    }
    batchOwners.set(l.batch_no, l.item_code);
    const existing = await apiList("Batch", { fields: ["name", "disabled", "item"], filters: [["name", "=", l.batch_no]], limit: 1 }).catch(() => []);
    if (existing.length && existing[0].disabled) {
      return toast.error(`Row ${idx + 1}: Batch "${l.batch_no}" is disabled and can't be used.`);
    }
    if (existing.length && existing[0].item && existing[0].item !== l.item_code) {
      return toast.error(`Row ${idx + 1}: Batch "${l.batch_no}" already exists for item "${existing[0].item}", not "${l.item_code}".`);
    }
  }
  // Verify stock exists before actually posting an outgoing/transfer movement.
  if (submit && (type === "Material Issue" || type === "Material Transfer") && form.from_warehouse) {
    const err = await checkAvailability(form.from_warehouse);
    if (err) return toast.error(err);
  }
  drawerSaving.value = true;
  try {
    const company = await resolveCompany();

    // Pre-create Batch records for any batch-tracked line carrying a Batch No
    // that doesn't exist yet, so the Stock Entry submit can resolve it as a
    // valid Link. Existing batches (e.g. typed in for an outgoing line) are
    // left untouched. batch_qty is intentionally left at 0 — Stock Entry's
    // on_submit -> _adjust_batch_qty is the single authoritative writer.
    for (const l of usable) {
      if (!l.has_batch_no || !l.batch_no) continue;
      const exists = await apiList("Batch", { fields: ["name"], filters: [["name", "=", l.batch_no]], limit: 1 });
      if (!exists.length) {
        await apiSave({
          doctype: "Batch",
          batch_no: l.batch_no,
          item: l.item_code,
          warehouse: l.t_warehouse || form.to_warehouse || l.s_warehouse || form.from_warehouse,
          manufacturing_date: l.manufacturing_date || null,
          expiry_date: l.expiry_date || null,
          batch_qty: 0,
        });
      }
    }

    const doc = {
      doctype: "Stock Entry", company,
      stock_entry_type: form.stock_entry_type,
      posting_date: form.posting_date,
      from_warehouse: form.from_warehouse || null,
      to_warehouse: form.to_warehouse || null,
      adjustment_reason: form.adjustment_reason || "",
      remarks: form.remarks || "",
      items: usable.map(l => ({
        doctype: "Stock Entry Detail",
        item_code: l.item_code,
        qty: flt(l.qty),
        basic_rate: flt(l.basic_rate),
        s_warehouse: l.s_warehouse || form.from_warehouse || null,
        t_warehouse: l.t_warehouse || form.to_warehouse || null,
        batch_no: l.has_batch_no ? (l.batch_no || null) : null,
      })),
    };
    if (editingName.value) doc.name = editingName.value;
    const saved = await apiSave(doc);
    if (submit) await apiSubmit("Stock Entry", saved.name);
    toast.success(`Stock Entry ${saved?.name || ""} ${submit ? "submitted" : "saved as draft"}`);
    drawerOpen.value = false;
    editingName.value = "";
    await load();
  } catch (e) {
    toast.error(e.message || "Failed to save stock entry");
  } finally { drawerSaving.value = false; }
}

function exportCSV() {
  const rows = sorted.value;
  if (!rows.length) return;
  const esc = v => { const s = v == null ? "" : String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  const hdr = ["Entry #", "Type", "Date", "Source", "Reference", "From WH", "To WH", "Status", "Incoming", "Outgoing", "Net Diff"];
  const lines2 = [hdr.join(",")];
  for (const e of rows) {
    lines2.push([
      e.name, e.stock_entry_type || "", fmtDate(e.posting_date),
      sourceInfo(e).label, e.reference_name || "",
      e.from_warehouse || "", e.to_warehouse || "",
      statusLabel(e),
      flt(e.total_incoming_value), flt(e.total_outgoing_value), flt(e.value_difference),
    ].map(esc).join(","));
  }
  const blob = new Blob(["﻿" + lines2.join("\r\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `stock_entries_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click(); URL.revokeObjectURL(url);
  toast.success(`Exported ${rows.length} row(s)`);
}

onMounted(async () => {
  await load();
  if (route.query.open) openView({ name: String(route.query.open) });
});
</script>

<style scoped>
.se-page { display:flex; flex-direction:column; gap:14px; padding:24px; }

/* KPI strip */
.se-kpi-strip { display:grid; grid-template-columns:repeat(5,1fr); gap:10px; }
.se-kpi { background:#fff; border:1px solid #e5e7eb; border-radius:10px; padding:12px 14px; display:flex; align-items:center; gap:12px; cursor:pointer; transition:border-color .15s,box-shadow .15s; }
.se-kpi:hover,.se-kpi.active { border-color:#2563eb; box-shadow:0 0 0 2px rgba(37,99,235,.1); }
.se-kpi-ico { width:36px; height:36px; border-radius:9px; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.se-kpi-lbl { font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.05em; color:#9ca3af; }
.se-kpi-val { font-size:20px; font-weight:700; color:#0f172a; line-height:1.2; }

/* Actions */
.se-actions { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.se-search-wrap { display:flex; align-items:center; gap:8px; background:#fff; border:1px solid #e5e7eb; border-radius:8px; padding:6px 12px; min-width:240px; }
.se-search-input { border:none; background:transparent; outline:none; font:inherit; color:#111827; width:100%; font-size:13px; }
.se-filter-row { display:flex; align-items:center; gap:14px; flex-wrap:wrap; }
.se-filter-select { border:1px solid #e5e7eb; border-radius:6px; padding:4px 8px; font:inherit; font-size:12px; color:#374151; background:#fff; outline:none; cursor:pointer; }
.se-date-input { border:1px solid #e5e7eb; border-radius:6px; padding:4px 8px; font-size:12px; outline:none; background:#fff; }

/* Pills */
.se-pill { padding:5px 12px; border-radius:20px; font-size:12.5px; font-weight:600; border:1px solid #e5e7eb; background:#fff; color:#6b7280; cursor:pointer; font-family:inherit; display:inline-flex; align-items:center; gap:6px; }
.se-pill.active { background:#eff6ff; border-color:#2563eb; color:#2563eb; }
.se-pill-dot { width:7px; height:7px; border-radius:50%; display:inline-block; flex-shrink:0; }
.se-pill-cnt { background:#f3f4f6; color:#6b7280; font-size:10.5px; padding:1px 6px; border-radius:10px; font-weight:700; }

/* Buttons */
.se-btn-primary { display:inline-flex; align-items:center; gap:6px; background:#2563eb; color:#fff; border:none; border-radius:8px; padding:8px 14px; font-size:13px; font-weight:600; cursor:pointer; }
.se-btn-primary:hover { background:#1d4ed8; } .se-btn-primary:disabled { opacity:.5; cursor:not-allowed; }
.se-btn-ghost { display:inline-flex; align-items:center; gap:6px; background:#fff; border:1px solid #e5e7eb; border-radius:8px; padding:8px 12px; font-size:13px; color:#374151; cursor:pointer; }
.se-btn-ghost:hover { background:#f9fafb; }
.se-btn-save { display:inline-flex; align-items:center; gap:6px; background:#f0fdf4; border:1px solid #16a34a; color:#16a34a; border-radius:8px; padding:8px 14px; font-size:13px; font-weight:600; cursor:pointer; }
.se-btn-save:hover { background:#dcfce7; } .se-btn-save:disabled { opacity:.5; cursor:not-allowed; }

/* Table */
.se-card { background:#fff; border:1px solid #e5e7eb; border-radius:10px; overflow:hidden; }
.se-table { width:100%; border-collapse:collapse; font-size:13px; }
.se-table th { background:#f9fafb; border-bottom:1px solid #e5e7eb; padding:10px 12px; font-size:11px; font-weight:700; color:#374151; text-align:left; white-space:nowrap; text-transform:uppercase; letter-spacing:.04em; }
.se-table th.sortable { cursor:pointer; user-select:none; } .se-table th.sortable:hover { color:#2563eb; }
.ta-r { text-align:right!important; }
.se-row td { padding:10px 12px; border-bottom:1px solid #f3f4f6; vertical-align:middle; cursor:pointer; }
.se-row:last-child td { border-bottom:none; } .se-row:hover td { background:#f9fafb; }
.se-num { font-size:12.5px; color:#2563eb; font-weight:700; }
.se-type-badge { display:inline-flex; padding:3px 8px; border-radius:20px; font-size:11.5px; font-weight:700; white-space: nowrap;}
.se-badge { display:inline-flex; align-items:center; padding:2px 8px; border-radius:10px; font-size:11.5px; font-weight:600; }
.badge-green { background:#dcfce7; color:#16a34a; } .badge-orange { background:#fff7ed; color:#ea580c; } .badge-grey { background:#f3f4f6; color:#6b7280; }
.se-source-cell { display:flex; align-items:center; gap:5px; }
.se-source-dot { width:7px; height:7px; border-radius:50%; flex-shrink:0; }
.se-source-ref { font-size:11px; color:#6b7280; background:#f3f4f6; padding:1px 5px; border-radius:4px; max-width:100px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.se-wh-flow { display:flex; align-items:center; gap:4px; flex-wrap:nowrap; }
.se-wh-tag { font-size:11px; font-weight:600; background:#eff6ff; color:#1d4ed8; padding:2px 7px; border-radius:6px; white-space:nowrap; max-width:100px; overflow:hidden; text-overflow:ellipsis; }
.se-wh-tag-to { background:#f0fdf4; color:#15803d; }
.se-item-cnt { font-size:12px; font-weight:700; color:#6b7280; background:#f3f4f6; padding:1px 7px; border-radius:8px; }
.se-act-btn { background:transparent; border:1px solid #e5e7eb; border-radius:6px; width:28px; height:28px; display:inline-flex; align-items:center; justify-content:center; cursor:pointer; color:#6b7280; }
.se-act-btn:hover { background:#eff6ff; color:#2563eb; border-color:#bfdbfe; }
.mono-sm { font-size:12.5px; } .text-muted { color:#6b7280; }
.se-empty { text-align:center; color:#9ca3af; padding:48px!important; cursor:default!important; }
.se-shimmer { height:13px; background:linear-gradient(90deg,#f3f4f6 25%,#e5e7eb 50%,#f3f4f6 75%); border-radius:4px; animation:shimmer 1.2s infinite; background-size:200% 100%; }
@keyframes shimmer { 0%{background-position:200% 0}100%{background-position:-200% 0} }
.se-pg-btn { background:#fff; border:1px solid #e5e7eb; border-radius:6px; padding:3px 10px; cursor:pointer; font-size:14px; color:#374151; }
.se-pg-btn:disabled { opacity:.4; cursor:not-allowed; }

/* Drawer */
.se-overlay { position:fixed; inset:0; background:rgba(15,23,42,.28); z-index:40; }
.se-drawer { position:fixed; top:0; right:-520px; bottom:0; width:520px; max-width:96vw; background:#fff; border-left:1px solid #e5e7eb; box-shadow:-8px 0 28px rgba(15,23,42,.12); z-index:50; display:flex; flex-direction:column; transition:right .24s ease; }
.se-drawer.open { right:0; }
.se-view-drawer { width:580px; right:-580px; } .se-view-drawer.open { right:0; }
.se-dheader { position:relative; flex-shrink:0; padding:20px; border-bottom:1px solid #e5e7eb; }
.se-dh-top { display:flex; align-items:center; gap:13px; padding-right:36px; }
.se-dh-ico { width:42px; height:42px; border-radius:11px; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.se-dh-title { font-size:15px; font-weight:700; } .se-dh-sub { font-size:12px; margin-top:1px; }
.se-dclose { background:transparent; border:none; cursor:pointer; display:inline-flex; align-items:center; justify-content:center; width:32px; height:32px; border-radius:8px; color:rgba(255,255,255,.8); }
.se-dclose:hover { background:rgba(255,255,255,.2); color:#fff; }
.se-dclose-abs { position:absolute; top:12px; right:12px; background: rgba(255, 255, 255, .15);
    border: none;
    cursor: pointer;
    color: #fff;
    width: 30px;
    height: 30px;
    border-radius: 8px;
    display: grid;
    place-items: center;
    transition: .15s;}
.se-dbody { flex:1; overflow-y:auto; padding:20px; display:flex; flex-direction:column; gap:16px; }
.se-dfooter { display:flex; align-items:center; justify-content:flex-end; gap:8px; padding:14px 20px; border-top:1px solid #e5e7eb; flex-shrink:0; background:#f9fafb; }

/* Create form */
.se-fields-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.se-field { display:flex; flex-direction:column; gap:4px; }
.se-label { font-size:12px; font-weight:600; color:#374151; } .req { color:#dc2626; }
.se-input { width:100%; box-sizing:border-box; border:1px solid #e2e8f0; border-radius:8px; padding:8px 11px; font:inherit; font-size:13px; outline:none; background:#fff; color:#0f172a; transition:border-color .15s; }
.se-input:focus { border-color:#2563eb; box-shadow:0 0 0 3px rgba(37,99,235,.1); }
textarea.se-input { resize:vertical; }
.se-select { border:1px solid #e2e8f0; border-radius:8px; padding:8px 11px; font:inherit; font-size:13px; outline:none; background:#fff; color:#0f172a; cursor:pointer; }
.se-select:focus { border-color:#2563eb; box-shadow:0 0 0 3px rgba(37,99,235,.1); }
.se-section-title { font-size:11.5px; font-weight:700; color:#374151; text-transform:uppercase; letter-spacing:.05em; padding-bottom:6px; border-bottom:1px solid #f3f4f6; }
.se-items-table { display:flex; flex-direction:column; border:1px solid #e5e7eb; border-radius:8px; max-width:100%;}
.se-items-head { display:grid; grid-template-columns:2.5fr 90px 110px 28px; gap:6px; background:#f9fafb; padding:8px 10px; font-size:11px; font-weight:700; color:#374151; text-transform:uppercase; letter-spacing:.03em; }
.se-items-row { display:grid; grid-template-columns:2.5fr 90px 110px 28px; gap:6px; padding:8px 10px; border-top:1px solid #f3f4f6; align-items:center; }
.se-items-total { display:grid; grid-template-columns:2.5fr 90px 110px 28px; gap:6px; padding:8px 10px; border-top:2px solid #e5e7eb; background:#f8fafc; }
.se-items-row > div, .se-items-head > div { min-width:0; }
.se-items-row input.se-input { min-width:0; padding-left:6px; padding-right:6px; }
.se-add-line { background:transparent; border:none; color:#2563eb; font-size:12.5px; font-weight:600; cursor:pointer; padding:8px 10px; display:inline-flex; align-items:center; gap:6px; }
.se-add-line:hover { background:#eff6ff; }
.se-rm-line { background:transparent; border:1px solid #e5e7eb; border-radius:4px; width:22px; height:22px; display:inline-flex; align-items:center; justify-content:center; cursor:pointer; color:#9ca3af; flex-shrink:0; }
.se-rm-line:hover { background:#fee2e2; color:#dc2626; border-color:#fca5a5; }
.se-items-line { border-top:1px solid #f3f4f6; }
.se-items-line:first-child { border-top:none; }
.se-items-line .se-items-row { border-top:none; }
.se-batch-row { display:flex; flex-wrap:wrap; gap:8px; padding:0 10px 10px; background:#fafbfc; }
.se-batch-field { display:flex; flex-direction:column; gap:3px; flex:1 1 120px; min-width:120px; max-width:100%; }
.se-batch-field input.se-input[type="date"] { min-width:0; padding-left:8px; padding-right:4px; }
.se-input-req { border-color:#fca5a5 !important; background:#fff7f7; }

/* View panel */
.se-source-card { border:1.5px solid #e5e7eb; border-radius:10px; padding:12px 14px; }
.se-source-label { display:inline-flex; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:700; }
.se-view-section { display:flex; flex-direction:column; gap:8px; }
.se-view-sec-lbl { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; color:#9ca3af; }
.se-wh-flow-big { display:flex; align-items:center; gap:12px; background:#f8fafc; border:1px solid #e5e7eb; border-radius:10px; padding:14px 16px; }
.se-wh-box { flex:1; }
.se-wh-box-empty div:last-child { color:#9ca3af; font-style:italic; }
.se-wh-arrow { flex-shrink:0; display:flex; align-items:center; }
.se-val-strip { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }
.se-val-box { border-radius:8px; padding:10px 12px; border:1px solid; text-align:center; }
.se-val-in  { background:#f0fdf4; border-color:#bbf7d0; }
.se-val-out { background:#fff7ed; border-color:#fed7aa; }
.se-val-diff { background:#f8fafc; border-color:#e2e8f0; }
.se-val-lbl { font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:#6b7280; margin-bottom:4px; }
.se-val-num { font-weight:700; font-size:14px; }
.se-val-in .se-val-num  { color:#16a34a; }
.se-val-out .se-val-num { color:#ea580c; }
.se-meta-lbl { font-size:10.5px; color:#9ca3af; text-transform:uppercase; letter-spacing:.05em; display:block; }
.se-view-items-tbl { width:100%; border-collapse:collapse; font-size:12.5px; border:1px solid #e5e7eb; border-radius:8px; overflow:hidden; }
.se-view-items-tbl th { background:#f9fafb; padding:8px 10px; font-size:10.5px; font-weight:700; color:#374151; text-align:left; border-bottom:1px solid #e5e7eb; text-transform:uppercase; letter-spacing:.04em; }
.se-view-items-tbl td { padding:9px 10px; border-bottom:1px solid #f3f4f6; color:#111827; }
.se-view-items-tbl tr:last-child td { border-bottom:none; }
.se-view-items-tbl tr:hover td { background:#f9fafb; }

/* ── Mobile card defaults ── */
.se-mobile-cards { display: none; }
.se-desktop-table { display: table; }

@media (max-width: 768px) {
  .se-kpi-strip { grid-template-columns: 1fr 1fr; }
  .se-kpi-value { grid-column: 1 / -1; }
  .se-drawer      { width: 100% !important; max-width: 100% !important; right: -100% !important; }
  .se-view-drawer { width: 100% !important; max-width: 100% !important; right: -100% !important; }
  .se-drawer.open,
  .se-view-drawer.open { right: 0 !important; }
  .se-search-wrap { min-width: 0; flex: 1 1 auto; }
  .se-filter-row  { width: 100%; }
  .se-desktop-table { display: none !important; }
  .se-mobile-cards { display: flex; flex-direction: column; gap: 0; background: #f8fafc; }
  .se-mobile-card { background: #fff; border-bottom: 1px solid #e5e7eb; padding: 12px 14px; cursor: pointer; transition: background .12s; }
  .se-mobile-card:active { background: #f8f9fc; }
  .se-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
  .se-mc-docno { font-size: 12px; font-weight: 700; color: #2563eb; }
  .se-mc-mid { margin-bottom: 6px; }
  .se-mc-meta { display: flex; justify-content: space-between; font-size: 12px; color: #868e96; }
  .se-mc--skeleton { pointer-events: none; }
  .se-mc-shimmer { border-radius: 6px; background: linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size: 200% 100%; animation: se-mc-sh 1.4s infinite; }
  @keyframes se-mc-sh { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
  .se-mc-empty { text-align: center; padding: 32px 16px; color: #868e96; font-size: 13px; }
  /* View drawer items: hide table, show cards */
  .se-view-items-desktop { display: none !important; }
  .se-view-items-mobile  { display: flex !important; flex-direction: column; }
}
/* Add-drawer items: switch to cards earlier (900px) since the table needs more
   room than the drawer has well before the page-level 768px breakpoint */
@media (max-width: 900px) {
  .se-add-items-desktop  { display: none !important; }
  .se-add-items-mobile   { display: flex !important; flex-direction: column; }
}
@media (max-width: 480px) {
  .se-page { padding: 12px; gap: 10px; }
  .se-fields-grid { grid-template-columns: 1fr !important; }
  .se-val-strip   { grid-template-columns: 1fr !important; }
}
/* ── Add-drawer item cards (mobile) ── */
.se-add-items-mobile { display: none; flex-direction: column; gap: 10px; }
.se-aic { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px 14px; display: flex; flex-direction: column; gap: 10px; }
.se-aic-header { display: flex; align-items: center; justify-content: space-between; }
.se-aic-num { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: #6b7280; }
.se-aic-field { display: flex; flex-direction: column; gap: 4px; }
.se-aic-row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.se-aic-amount { font-size: 12px; color: #6b7280; text-align: right; border-top: 1px solid #f3f4f6; padding-top: 8px; }
.se-aic-total { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 13px; color: #374151; }
.se-aic-total strong { font-size: 14px; color: #0f172a; }

/* ── View-drawer item cards (mobile) ── */
.se-view-items-mobile { display: none; flex-direction: column; gap: 8px; }
.se-vic { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px 14px; }
.se-vic-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
.se-vic-name { font-size: 13px; font-weight: 700; color: #0f172a; }
.se-vic-sub { font-size: 11px; color: #9ca3af; margin-top: 2px; }
.se-vic-amount { font-size: 14px; font-weight: 700; color: #0f172a; flex-shrink: 0; margin-left: 8px; }
.se-vic-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.se-vic-cell { display: flex; flex-direction: column; gap: 2px; }
.se-vic-lbl { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: #9ca3af; }
.se-vic-val { font-size: 12px; font-weight: 600; color: #374151; }

</style>