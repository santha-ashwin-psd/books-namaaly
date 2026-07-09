<template>
<div class="sc-page">
  <div class="sc-sticky">
    <div class="sc-header">
      <div style="display:flex;align-items:center;gap:12px;">
        <button class="iv-back" @click="router.push('/manufacturing/work-order')" style="background:none;border:none;cursor:pointer;color:#2563eb;display:flex;align-items:center;gap:4px;font-weight:600;font-size:13px;padding:0;">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
          Back
        </button>
        <span class="sc-title">{{ isNew ? 'New Work Order' : wo.name }}</span>
        <div v-if="!isNew" class="inv-status-badge"
             style="font-size:12px;padding:3px 8px;border-radius:12px;"
             :style="statusStyle">
          {{ wo.status }}
        </div>
      </div>
      <div style="display:flex;gap:10px;">
        <button class="nim-btn" style="background:#fff;border:1px solid #e5e7eb;padding:8px 16px;border-radius:8px;font-weight:600;cursor:pointer;" @click="router.push('/manufacturing/work-order')" :disabled="saving || submitting">Back</button>
        <button v-if="!isNew && wo.docstatus===2" class="sc-save-btn" @click="amendWO" :disabled="submitting">
          {{ submitting ? 'Amending...' : 'Amend' }}
        </button>
        <button v-if="!isNew && wo.docstatus===1 && flt(wo.produced_qty)===0" class="nim-btn" style="background:#fee2e2;color:#dc2626;border:1px solid #fecaca;padding:8px 16px;border-radius:8px;font-weight:600;cursor:pointer;" @click="cancelWO" :disabled="submitting">
          {{ submitting ? 'Cancelling...' : 'Cancel Work Order' }}
        </button>
        <button v-if="!isNew && wo.docstatus===0" class="sc-save-btn" @click="submitWO" :disabled="submitting || saving">
          {{ submitting ? 'Submitting...' : 'Submit' }}
        </button>
        <button v-if="!readOnly" class="sc-save-btn" @click="save" :disabled="saving || loading">
          <span v-if="saving" style="display:inline-block;width:12px;height:12px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .6s linear infinite;margin-right:6px;"></span>
          {{ isNew ? 'Save Work Order' : 'Save Changes' }}
        </button>
      </div>
    </div>
    <div class="sc-tabs">
      <button v-for="t in tabs" :key="t.id"
        class="sc-tab" :class="{ 'sc-tab--active': activeTab === t.id }"
        @click="activeTab = t.id">
        {{ t.label }}
      </button>
    </div>
  </div>

  <!-- Tab 1: Work Order -->
  <div v-if="activeTab === 'details'" class="sc-body sc-body--narrow">
    <div class="sc-col-main">
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
          </div>
          <div>
            <div class="sc-card-title">BOM &amp; Quantity</div>
            <div class="sc-card-subtitle">Pick a submitted BOM to manufacture against.</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-fg" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">BOM <span class="sc-required">*</span></label>
            <select class="nim-input" v-model="wo.bom" @change="onBomChange" :disabled="readOnly">
              <option value="">— Select Submitted BOM —</option>
              <option v-for="b in bomList" :key="b.name" :value="b.name">{{ b.name }} — {{ b.item_name || b.item }}</option>
            </select>
            <div class="sc-field-hint" v-if="wo.item_name">Manufactures: <strong>{{ wo.item_name }}</strong> ({{ wo.stock_uom }})</div>
          </div>
          <div class="nim-field">
            <label class="nim-label">Qty to Manufacture <span class="sc-required">*</span></label>
            <input type="number" class="nim-input" v-model="wo.qty" min="0.01" step="any" :disabled="readOnly" />
          </div>
        </div>
        <div class="sc-fg sc-fg--single" v-if="!readOnly && wo.bom">
          <button class="sc-upload-btn" style="justify-self:start" @click="loadFromBom" :disabled="breakdownLoading">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
            {{ breakdownLoading ? 'Loading…' : 'Load / Refresh Materials from BOM' }}
          </button>
          <div class="sc-field-hint">Rescales raw materials &amp; operations from the BOM at the current qty. Overwrites any manual edits below.</div>
        </div>
      </div>

      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon" style="background:#fee2e2;color:#dc2626;box-shadow:inset 0 0 0 1px rgba(220,38,38,.08), 0 2px 6px rgba(220,38,38,.12);">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="10" rx="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
          </div>
          <div>
            <div class="sc-card-title">Warehouses</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-fg" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Default Source Warehouse (Raw Materials)</label>
            <select class="nim-input" v-model="wo.source_warehouse" :disabled="readOnly">
              <option value="">— Select —</option>
              <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
            </select>
          </div>
          <div class="nim-field">
            <label class="nim-label">Work-in-Progress Warehouse</label>
            <select class="nim-input" v-model="wo.wip_warehouse" :disabled="readOnly">
              <option value="">— None (consume from Source directly) —</option>
              <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
            </select>
            <div class="sc-field-hint">Optional. If set, use Issue Materials to stage raw materials here first.</div>
          </div>
        </div>
        <div class="sc-fg">
          <div class="nim-field">
            <label class="nim-label">Finished Goods Warehouse <span class="sc-required">*</span></label>
            <select class="nim-input" v-model="wo.fg_warehouse" :disabled="readOnly">
              <option value="">— Select —</option>
              <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
            </select>
          </div>
          <div class="nim-field">
            <label class="nim-label">Scrap / By-Product Warehouse</label>
            <select class="nim-input" v-model="wo.scrap_warehouse" :disabled="readOnly">
              <option value="">— Defaults to Finished Goods Warehouse —</option>
              <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
            </select>
          </div>
        </div>
      </div>

      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
          </div>
          <div>
            <div class="sc-card-title">Schedule</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-fg">
          <div class="nim-field">
            <label class="nim-label">Planned Start Date</label>
            <input type="date" class="nim-input" v-model="wo.planned_start_date" :disabled="readOnly" />
          </div>
          <div class="nim-field">
            <label class="nim-label">Planned End Date</label>
            <input type="date" class="nim-input" v-model="wo.planned_end_date" :disabled="readOnly" />
          </div>
        </div>
      </div>

      <div class="sc-card" style="max-width:100%;overflow-x:auto;">
        <div class="sc-card-header" style="justify-content:space-between;">
          <div style="display:flex;align-items:center;gap:14px;">
            <div class="sc-card-icon sc-card-icon--blue">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>
            </div>
            <div><div class="sc-card-title">Raw Materials</div></div>
          </div>
          <button v-if="!readOnly" class="sc-upload-btn" @click="addMaterial">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
            Add Row
          </button>
        </div>
        <div class="sc-divider"></div>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead>
            <tr>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Item Code</th>
              <th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Required Qty</th>
              <th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Transferred</th>
              <th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Consumed</th>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Source Warehouse</th>
              <th v-if="!readOnly" style="width:40px;border-bottom:1px solid #e5e7eb;"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!wo.items || !wo.items.length">
              <td colspan="6" style="text-align:center;padding:24px;color:#9ca3af;">No raw materials yet. Select a BOM and click "Load / Refresh Materials from BOM".</td>
            </tr>
            <tr v-for="(rm, idx) in wo.items" :key="idx">
              <td style="padding:6px;">
                <select class="nim-input" style="padding:6px 10px;" v-model="rm.item_code" :disabled="readOnly">
                  <option value="">— Select —</option>
                  <option v-for="i in stockItems" :key="i.name" :value="i.name">{{ i.item_name || i.name }}</option>
                </select>
              </td>
              <td style="padding:6px;"><input type="number" class="nim-input" style="padding:6px 10px;text-align:right;" v-model="rm.required_qty" min="0" step="any" :disabled="readOnly"/></td>
              <td style="padding:6px;text-align:right;vertical-align:middle;color:#6b7280;">{{ fmt(rm.transferred_qty) }}</td>
              <td style="padding:6px;text-align:right;vertical-align:middle;color:#6b7280;">{{ fmt(rm.consumed_qty) }}</td>
              <td style="padding:6px;">
                <select class="nim-input" style="padding:6px 10px;" v-model="rm.source_warehouse" :disabled="readOnly">
                  <option value="">— Use Default —</option>
                  <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
                </select>
              </td>
              <td v-if="!readOnly" style="padding:6px;text-align:center;vertical-align:middle;">
                <button @click="removeMaterial(idx)" style="background:none;border:none;color:#dc2626;cursor:pointer;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="sc-card" style="max-width:100%;overflow-x:auto;">
        <div class="sc-card-header" style="justify-content:space-between;">
          <div style="display:flex;align-items:center;gap:14px;">
            <div class="sc-card-icon sc-card-icon--blue">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"></circle></svg>
            </div>
            <div><div class="sc-card-title">Operations</div></div>
          </div>
          <button v-if="!readOnly" class="sc-upload-btn" @click="addOp">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
            Add Operation
          </button>
        </div>
        <div class="sc-divider"></div>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead>
            <tr>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Operation</th>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Workstation</th>
              <th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Planned (Mins)</th>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Status</th>
              <th v-if="!readOnly" style="width:40px;border-bottom:1px solid #e5e7eb;"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!wo.operations || !wo.operations.length">
              <td colspan="5" style="text-align:center;padding:24px;color:#9ca3af;">No operations yet.</td>
            </tr>
            <tr v-for="(op, idx) in wo.operations" :key="idx">
              <td style="padding:6px;">
                <select class="nim-input" style="padding:6px 10px;" v-model="op.operation" :disabled="readOnly">
                  <option value="">— Select —</option>
                  <option v-for="o in operationsList" :key="o.name" :value="o.name">{{ o.name }}</option>
                </select>
              </td>
              <td style="padding:6px;">
                <select class="nim-input" style="padding:6px 10px;" v-model="op.workstation" :disabled="readOnly">
                  <option value="">— Select —</option>
                  <option v-for="w in workstationsList" :key="w.name" :value="w.name">{{ w.name }}</option>
                </select>
              </td>
              <td style="padding:6px;"><input type="number" class="nim-input" style="padding:6px 10px;text-align:right;" v-model="op.planned_time_in_mins" min="0" step="any" :disabled="readOnly" /></td>
              <td style="padding:6px;">
                <select class="nim-input" style="padding:6px 10px;" v-model="op.status">
                  <option>Pending</option><option>In Process</option><option>Completed</option>
                </select>
              </td>
              <td v-if="!readOnly" style="padding:6px;text-align:center;vertical-align:middle;">
                <button @click="removeOp(idx)" style="background:none;border:none;color:#dc2626;cursor:pointer;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Tab 2: Production -->
  <div v-if="activeTab === 'production'" class="sc-body sc-body--narrow">
    <div class="sc-col-main">
      <div v-if="isNew" class="sc-card"><div class="sc-card-subtitle">Save and submit the Work Order first to begin production.</div></div>
      <template v-else>
        <div class="sc-card">
          <div class="sc-card-header" style="justify-content:space-between;">
            <div>
              <div class="sc-card-title">Production Progress</div>
              <div class="sc-card-subtitle">{{ fmt(wo.produced_qty) }} of {{ fmt(wo.qty) }} {{ wo.stock_uom }} produced</div>
            </div>
            <div style="font-size:20px;font-weight:800;color:#1e3a8a;">{{ progressPct }}%</div>
          </div>
          <div style="height:8px;background:#e5e7eb;border-radius:6px;overflow:hidden;margin-top:12px;">
            <div :style="{width: progressPct+'%'}" style="height:100%;background:linear-gradient(135deg,#2f74f5,#1a6ef7);"></div>
          </div>
          <div style="display:flex;gap:24px;margin-top:16px;">
            <div><div style="font-size:11px;color:#6b7280;text-transform:uppercase;font-weight:600;">Remaining</div><div style="font-size:16px;font-weight:700;">{{ fmt(remainingQty) }}</div></div>
            <div><div style="font-size:11px;color:#dc2626;text-transform:uppercase;font-weight:600;">Process Loss</div><div style="font-size:16px;font-weight:700;color:#dc2626;">{{ fmt(wo.process_loss_qty) }}</div></div>
          </div>
        </div>

        <div class="sc-card" v-if="wo.docstatus===1">
          <div class="sc-card-header"><div class="sc-card-title">Actions</div></div>
          <div class="sc-divider"></div>
          <div style="display:flex;gap:12px;flex-wrap:wrap;">
            <button v-if="wo.wip_warehouse" class="sc-save-btn" @click="issueMaterials" :disabled="actionLoading || allTransferred">
              {{ actionLoading==='issue' ? 'Issuing…' : (allTransferred ? 'Materials Issued' : 'Issue Materials to WIP') }}
            </button>
            <button class="sc-save-btn" style="background:linear-gradient(135deg,#16a34a,#15803d);" @click="openCompleteModal" :disabled="remainingQty<=0">
              Complete Work Order
            </button>
          </div>
          <div class="sc-field-hint" v-if="remainingQty<=0">Fully produced — no further completions possible.</div>
        </div>

        <div class="sc-card">
          <div class="sc-card-header" style="justify-content:space-between;">
            <div class="sc-card-title">Linked Stock Entries</div>
            <button class="sc-upload-btn" @click="loadStockEntries" :disabled="seLoading">Refresh</button>
          </div>
          <div class="sc-divider"></div>
          <table style="width:100%;border-collapse:collapse;font-size:13px;" v-if="stockEntries.length">
            <thead><tr>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Entry</th>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Type</th>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Date</th>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Status</th>
            </tr></thead>
            <tbody>
              <tr v-for="se in stockEntries" :key="se.name" style="cursor:pointer;" @click="router.push('/inventory/stock-entries')">
                <td style="padding:8px;" class="inv-link">{{ se.name }}</td>
                <td style="padding:8px;">{{ se.stock_entry_type }}</td>
                <td style="padding:8px;">{{ fmtDate(se.posting_date) }}</td>
                <td style="padding:8px;">{{ se.docstatus===1 ? 'Submitted' : (se.docstatus===2 ? 'Cancelled' : 'Draft') }}</td>
              </tr>
            </tbody>
          </table>
          <div v-else style="text-align:center;padding:24px;color:#9ca3af;">No Stock Entries posted against this Work Order yet.</div>
        </div>
      </template>
    </div>
  </div>

  <!-- Tab 3: More Info -->
  <div v-if="activeTab === 'more'" class="sc-body sc-body--narrow">
    <div class="sc-col-main">
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
          </div>
          <div><div class="sc-card-title">More Information</div></div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-fg" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Company</label>
            <input type="text" class="nim-input" v-model="wo.company" :disabled="readOnly" />
          </div>
          <div class="nim-field">
            <label class="nim-label">Sales Order</label>
            <input type="text" class="nim-input" v-model="wo.sales_order" :disabled="readOnly" placeholder="Optional reference" />
          </div>
        </div>
        <div class="sc-fg sc-fg--single">
          <div class="nim-field">
            <label class="nim-label">Remarks</label>
            <textarea class="nim-input" v-model="wo.remarks" rows="3" :disabled="readOnly"></textarea>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Complete Work Order Modal -->
  <div v-if="showCompleteModal" class="iv-modal-overlay" @click.self="closeCompleteModal">
    <div class="iv-modal" style="width:560px;max-width:94vw;text-align:left;">
      <div class="iv-modal-title">Complete Work Order</div>
      <div class="iv-modal-body">
        <div class="sc-fg" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Qty Manufactured <span class="sc-required">*</span></label>
            <input type="number" class="nim-input" v-model="completeForm.qty_manufactured" min="0.01" :max="remainingQty" step="any" />
            <div class="sc-field-hint">Remaining planned qty: {{ fmt(remainingQty) }}</div>
          </div>
          <div class="nim-field">
            <label class="nim-label">Process Loss / Wastage Qty</label>
            <input type="number" class="nim-input" v-model="completeForm.process_loss_qty" min="0" step="any" />
          </div>
        </div>
        <template v-if="productionItemHasBatch">
          <div class="sc-fg" style="margin-bottom:14px">
            <div class="nim-field">
              <label class="nim-label">Batch No</label>
              <input type="text" class="nim-input" v-model="completeForm.batch_no" placeholder="Leave blank to auto-generate" />
            </div>
            <div class="nim-field">
              <label class="nim-label">Manufacturing Date</label>
              <input type="date" class="nim-input" v-model="completeForm.manufacturing_date" />
            </div>
          </div>
          <div class="sc-fg sc-fg--single" style="margin-bottom:14px">
            <div class="nim-field">
              <label class="nim-label">Expiry Date</label>
              <input type="date" class="nim-input" v-model="completeForm.expiry_date" />
              <div class="sc-field-hint">Leave blank to auto-calculate from the item's shelf life.</div>
            </div>
          </div>
        </template>

        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
          <label class="nim-label" style="margin:0;">Recoverable Scrap / By-Products</label>
          <button class="sc-upload-btn" style="padding:5px 10px;" @click="addCompleteScrap">+ Add</button>
        </div>
        <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:8px;" v-if="completeForm.scrap_items.length">
          <tbody>
            <tr v-for="(s, idx) in completeForm.scrap_items" :key="idx">
              <td style="padding:4px;">
                <select class="nim-input" style="padding:6px 8px;" v-model="s.item_code">
                  <option value="">— Select Item —</option>
                  <option v-for="i in stockItems" :key="i.name" :value="i.name">{{ i.item_name || i.name }}</option>
                </select>
              </td>
              <td style="padding:4px;width:110px;"><input type="number" class="nim-input" style="padding:6px 8px;text-align:right;" v-model="s.qty" min="0" step="any" /></td>
              <td style="padding:4px;width:32px;"><button @click="completeForm.scrap_items.splice(idx,1)" style="background:none;border:none;color:#dc2626;cursor:pointer;">✕</button></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="iv-modal-actions">
        <button class="nim-btn" style="background:#fff;border:1px solid #e5e7eb;padding:8px 16px;border-radius:8px;font-weight:600;cursor:pointer;" @click="closeCompleteModal" :disabled="actionLoading">Cancel</button>
        <button class="sc-save-btn" @click="submitComplete" :disabled="actionLoading">
          {{ actionLoading==='complete' ? 'Completing…' : 'Complete' }}
        </button>
      </div>
    </div>
  </div>

</div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet, apiSave, apiList, apiSubmit, apiCancel, apiAmend, apiCall, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";

const route = useRoute();
const router = useRouter();
const { toast } = useToast();

const isNew = computed(() => route.params.name === "new");
const loading = ref(true);
const saving = ref(false);
const submitting = ref(false);
const breakdownLoading = ref(false);
const actionLoading = ref(false);
const seLoading = ref(false);

const activeTab = ref("details");
const tabs = [
  { id: "details",    label: "Work Order" },
  { id: "production", label: "Production" },
  { id: "more",        label: "More Information" },
];

const wo = ref({
  doctype: "Work Order",
  bom: "",
  production_item: "",
  item_name: "",
  qty: 1,
  stock_uom: "",
  status: "Draft",
  produced_qty: 0,
  process_loss_qty: 0,
  source_warehouse: "",
  wip_warehouse: "",
  fg_warehouse: "",
  scrap_warehouse: "",
  planned_start_date: "",
  planned_end_date: "",
  items: [],
  operations: [],
  company: "",
  sales_order: "",
  remarks: "",
});

const bomList = ref([]);
const stockItems = ref([]);
const warehouseList = ref([]);
const stockEntries = ref([]);
const operationsList = ref([]);
const workstationsList = ref([]);

const EMPTY_MATERIAL = () => ({ item_code: "", required_qty: 1, transferred_qty: 0, consumed_qty: 0, source_warehouse: "" });
const EMPTY_OP = () => ({ operation: "", workstation: "", planned_time_in_mins: 0, actual_time_in_mins: 0, status: "Pending" });

// docstatus: 0 = Draft, 1 = Submitted, 2 = Cancelled. Once submitted, the
// plan (materials/operations/warehouses) is locked — progress from here on
// happens only through Issue Materials / Complete Work Order.
const readOnly = computed(() => !isNew.value && (wo.value.docstatus === 1 || wo.value.docstatus === 2));

const statusStyle = computed(() => {
  const s = wo.value.status;
  if (s === "Completed") return "background:#dcfce7;color:#16a34a";
  if (s === "Cancelled") return "background:#fee2e2;color:#dc2626";
  if (s === "Draft") return "background:#fef3c7;color:#b45309";
  return "background:#dbeafe;color:#1e40af";
});

onMounted(async () => {
  loading.value = true;
  try {
    const co = await resolveCompany();
    if (isNew.value) wo.value.company = co;

    const boms = await apiList("BOM", { fields: ["name", "item", "quantity", "docstatus"], filters: [["docstatus", "=", 1]], limit: 1000, order: "name asc" });
    const stk = await apiList("Item", { fields: ["name", "item_name", "standard_rate", "stock_uom", "has_batch_no", "shelf_life_in_days"], filters: [["is_stock_item", "=", 1]], limit: 5000, order: "name asc" });
    stockItems.value = stk || [];
    const itemNameOf = {};
    stockItems.value.forEach(i => itemNameOf[i.name] = i.item_name);
    bomList.value = (boms || []).map(b => ({ ...b, item_name: itemNameOf[b.item] || b.item }));

    const whs = await apiList("Warehouse", { fields: ["name"], filters: co ? [["company", "=", co], ["is_group", "=", 0]] : [["is_group", "=", 0]], limit: 1000, order: "name asc" });
    warehouseList.value = whs || [];

    const ops = await apiList("Operation", { fields: ["name"], limit: 1000, order: "name asc" });
    operationsList.value = ops || [];

    const wks = await apiList("Workstation", { fields: ["name", "hour_rate"], limit: 1000, order: "name asc" });
    workstationsList.value = wks || [];

    await loadWO();
  } catch (e) {
    toast("Error loading data: " + e.message, "error");
    router.push("/manufacturing/work-order");
  }
  loading.value = false;
});

async function loadWO() {
  if (!isNew.value) {
    const data = await apiGet("Work Order", route.params.name);
    wo.value = data;
    if (!wo.value.items) wo.value.items = [];
    if (!wo.value.operations) wo.value.operations = [];
    if (wo.value.docstatus === 1) await loadStockEntries();
  }
}

watch(() => route.params.name, () => {
  loadWO().catch((e) => toast("Error loading Work Order: " + e.message, "error"));
});

async function onBomChange() {
  if (!wo.value.bom) return;
  await loadFromBom();
}

async function loadFromBom() {
  if (!wo.value.bom || !wo.value.qty) return;
  breakdownLoading.value = true;
  try {
    const r = await apiCall("zoho_books_clone.manufacturing.work_order_engine.get_bom_breakdown", {
      bom: wo.value.bom, qty: wo.value.qty,
    });
    wo.value.production_item = r.production_item;
    wo.value.item_name = r.item_name;
    wo.value.stock_uom = r.stock_uom;
    wo.value.items = (r.items || []).map(i => ({ ...EMPTY_MATERIAL(), ...i, source_warehouse: "" }));
    wo.value.operations = (r.operations || []).map(o => ({ ...EMPTY_OP(), ...o }));
  } catch (e) {
    toast(e.message, "error");
  }
  breakdownLoading.value = false;
}

function addMaterial() { wo.value.items.push(EMPTY_MATERIAL()); }
function removeMaterial(idx) { wo.value.items.splice(idx, 1); }
function addOp() { wo.value.operations.push(EMPTY_OP()); }
function removeOp(idx) { wo.value.operations.splice(idx, 1); }

async function save() {
  if (!wo.value.bom) return toast("Please select a BOM", "error");
  if (!wo.value.qty || wo.value.qty <= 0) return toast("Qty to Manufacture must be greater than 0", "error");
  if (!wo.value.fg_warehouse) return toast("Finished Goods Warehouse is required", "error");
  if (!wo.value.items || !wo.value.items.length) return toast("Load raw materials from the BOM first", "error");

  saving.value = true;
  try {
    const doc = await apiSave(wo.value);
    toast(isNew.value ? "Work Order created" : "Work Order updated");
    if (isNew.value) {
      router.replace(`/manufacturing/work-order/${doc.name}`);
    } else {
      wo.value = doc;
    }
  } catch (e) {
    toast(e.message, "error");
  }
  saving.value = false;
}

async function submitWO() {
  if (!wo.value.name) return;
  submitting.value = true;
  try {
    const doc = await apiSubmit("Work Order", wo.value.name);
    wo.value = doc;
    toast("Work Order submitted");
  } catch (e) {
    toast(e.message, "error");
  }
  submitting.value = false;
}

async function cancelWO() {
  if (!wo.value.name) return;
  if (!confirm("Cancel this Work Order?")) return;
  submitting.value = true;
  try {
    const doc = await apiCancel("Work Order", wo.value.name);
    wo.value = doc;
    toast("Work Order cancelled");
  } catch (e) {
    toast(e.message, "error");
  }
  submitting.value = false;
}

async function amendWO() {
  if (!wo.value.name) return;
  submitting.value = true;
  try {
    const doc = await apiAmend("Work Order", wo.value.name);
    toast(`New revision ${doc.name} created`);
    router.push(`/manufacturing/work-order/${doc.name}`);
  } catch (e) {
    toast(e.message, "error");
  }
  submitting.value = false;
}

const remainingQty = computed(() => flt(wo.value.qty) - flt(wo.value.produced_qty));
const progressPct = computed(() => {
  const q = flt(wo.value.qty);
  if (!q) return 0;
  return Math.min(100, Math.round((flt(wo.value.produced_qty) / q) * 100));
});
const allTransferred = computed(() => (wo.value.items || []).every(r => flt(r.transferred_qty) >= flt(r.required_qty) - 0.0001));

const productionItemHasBatch = computed(() => {
  const item = stockItems.value.find(i => i.name === wo.value.production_item);
  return !!(item && item.has_batch_no);
});

async function issueMaterials() {
  actionLoading.value = "issue";
  try {
    const seName = await apiCall("zoho_books_clone.manufacturing.work_order_engine.issue_materials", { work_order: wo.value.name });
    toast(`Materials issued via ${seName}`);
    await loadWO();
  } catch (e) {
    toast(e.message, "error");
  }
  actionLoading.value = false;
}

async function loadStockEntries() {
  seLoading.value = true;
  try {
    stockEntries.value = await apiList("Stock Entry", {
      fields: ["name", "stock_entry_type", "posting_date", "docstatus"],
      filters: [["work_order", "=", wo.value.name]],
      limit: 100, order: "creation desc",
    }) || [];
  } catch (e) { /* non-fatal */ }
  seLoading.value = false;
}

// ── Complete Work Order modal ──────────────────────────────────────────
const showCompleteModal = ref(false);
const completeForm = ref({
  qty_manufactured: 0,
  process_loss_qty: 0,
  batch_no: "",
  manufacturing_date: "",
  expiry_date: "",
  scrap_items: [],
});

function openCompleteModal() {
  completeForm.value = {
    qty_manufactured: remainingQty.value > 0 ? remainingQty.value : 0,
    process_loss_qty: 0,
    batch_no: "",
    manufacturing_date: new Date().toISOString().slice(0, 10),
    expiry_date: "",
    scrap_items: [],
  };
  showCompleteModal.value = true;
}
function closeCompleteModal() { showCompleteModal.value = false; }
function addCompleteScrap() { completeForm.value.scrap_items.push({ item_code: "", qty: 1 }); }

async function submitComplete() {
  const qty = flt(completeForm.value.qty_manufactured);
  if (qty <= 0) return toast("Qty Manufactured must be greater than zero", "error");
  if (qty > remainingQty.value + 0.0001) return toast(`Qty Manufactured cannot exceed the remaining ${fmt(remainingQty.value)}`, "error");

  actionLoading.value = "complete";
  try {
    const scrapItems = completeForm.value.scrap_items.filter(s => s.item_code && flt(s.qty) > 0);
    await apiCall("zoho_books_clone.manufacturing.work_order_engine.complete_work_order", {
      work_order: wo.value.name,
      qty_manufactured: qty,
      process_loss_qty: flt(completeForm.value.process_loss_qty),
      scrap_items: scrapItems,
      batch_no: completeForm.value.batch_no || undefined,
      manufacturing_date: completeForm.value.manufacturing_date || undefined,
      expiry_date: completeForm.value.expiry_date || undefined,
    });
    toast("Work Order completion recorded");
    showCompleteModal.value = false;
    await loadWO();
  } catch (e) {
    toast(e.message, "error");
  }
  actionLoading.value = false;
}

function flt(n) { const v = parseFloat(n); return isNaN(v) ? 0 : v; }
function fmt(n) {
  if (isNaN(n) || n == null) return "0.00";
  return Number(n).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function fmtDate(d) {
  if (!d) return "";
  const obj = new Date(d);
  if (isNaN(obj)) return d;
  return obj.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}
</script>

<style scoped>
@keyframes spin { to { transform: rotate(360deg) } }

.sc-page { background: #f0f2f5; padding-bottom: 32px; min-height: 100vh; }
.sc-sticky { position: sticky; top: 0; z-index: 20; background: #f0f2f5; }
.sc-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 18px 24px 0; }
.sc-title { font-size: 20px; font-weight: 700; color: #1a1a2e; letter-spacing: -0.3px; }
.sc-save-btn {
  display: flex; align-items: center; gap: 7px; font-size: 13.5px; font-weight: 600;
  padding: 9px 20px; border-radius: 9px;
  background: linear-gradient(135deg, #2f74f5 0%, #1a6ef7 100%);
  border: none; color: #fff; cursor: pointer;
  box-shadow: 0 4px 12px rgba(26,110,247,.28), inset 0 1px 0 rgba(255,255,255,.18);
  transition: box-shadow .18s ease, transform .18s ease, filter .18s ease;
}
.sc-save-btn:hover:not(:disabled) { filter: brightness(1.04); box-shadow: 0 6px 18px rgba(26,110,247,.36), inset 0 1px 0 rgba(255,255,255,.2); transform: translateY(-1px); }
.sc-save-btn:active:not(:disabled) { transform: translateY(0); box-shadow: 0 2px 8px rgba(26,110,247,.3); }
.sc-save-btn:disabled { opacity: .6; cursor: not-allowed; }

.sc-tabs { display: flex; border-bottom: 2px solid #e4e8f0; padding: 0 24px; margin-top: 14px; overflow-x: auto; scrollbar-width: none; }
.sc-tabs::-webkit-scrollbar { display: none; }
.sc-tab {
  padding: 10px 18px; border: none; background: none; cursor: pointer; font-size: 13px; font-weight: 600;
  color: #868e96; white-space: nowrap; border-bottom: 2px solid transparent; border-radius: 8px 8px 0 0;
  margin-bottom: -2px; transition: color .15s, background .15s;
}
.sc-tab:hover { color: #374151; background: rgba(37,99,235,.05); }
.sc-tab--active { color: #2563eb; border-bottom-color: #2563eb; background: linear-gradient(180deg, rgba(37,99,235,.06), rgba(37,99,235,0)); }

.sc-body { padding: 24px; display: grid; gap: 20px; align-content: start; }
.sc-body--narrow { max-width: 900px; margin: 0 auto; }
.sc-col-main { display: grid; gap: 20px; align-content: start; }

.sc-card {
  background: #fff; border: 1px solid #e8ecf2; border-radius: 14px; padding: 22px 24px;
  box-shadow: 0 1px 2px rgba(16,24,40,.04), 0 1px 3px rgba(16,24,40,.03);
  transition: box-shadow .2s ease, transform .2s ease, border-color .2s ease;
}
.sc-card:hover { box-shadow: 0 6px 20px rgba(16,24,40,.07), 0 2px 6px rgba(16,24,40,.04); border-color: #dbe3ee; transform: translateY(-1px); }
.sc-card-header { display: flex; align-items: center; gap: 14px; }
.sc-card-icon {
  width: 40px; height: 40px; border-radius: 11px;
  background: linear-gradient(135deg, #eaf1ff 0%, #dbe7ff 100%);
  color: #2563eb; display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; box-shadow: inset 0 0 0 1px rgba(37,99,235,.08), 0 2px 6px rgba(37,99,235,.12);
}
.sc-card-icon--blue { background: linear-gradient(135deg, #eaf1ff 0%, #dbe7ff 100%); color: #2563eb; }
.sc-card-title { font-size: 14px; font-weight: 700; color: #111827; }
.sc-card-subtitle { font-size: 12px; color: #9ca3af; margin-top: 2px; }
.sc-divider { height: 1px; background: #f3f4f6; margin: 18px 0; }
.sc-required { color: #dc2626; }

.sc-fg { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.sc-fg--single { grid-template-columns: 1fr; }
.sc-fg--three  { grid-template-columns: 1fr 1fr 1fr; }

.sc-field-hint { display: flex; align-items: center; gap: 5px; margin-top: 5px; font-size: 12px; color: #6b7280; }

.sc-upload-btn {
  display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px;
  border: 1.5px solid #2563eb; border-radius: 8px; background: #fff;
  color: #2563eb; font-size: 12.5px; font-weight: 600; cursor: pointer; transition: background .15s; white-space: nowrap;
}
.sc-upload-btn:hover { background: #eff6ff; }
.sc-upload-btn:disabled { opacity: .6; cursor: not-allowed; }

.nim-field { display: flex; flex-direction: column; gap: 6px; }
.nim-label { font-size: 13px; font-weight: 600; color: #374151; }
.nim-input {
  border: 1px solid #d1d5db; border-radius: 8px; padding: 10px 14px;
  font-size: 14px; color: #111827; outline: none; transition: border-color .15s, box-shadow .15s;
  background: #fff;
}
.nim-input:focus { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,.1); }
.nim-input:disabled { background: #f8fafc; color: #6b7280; cursor: default; }

.iv-modal-overlay { position: fixed; inset: 0; background: rgba(17,24,39,.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.iv-modal { background: #fff; border-radius: 12px; padding: 22px; width: 420px; max-width: 92vw; box-shadow: 0 20px 50px rgba(0,0,0,.25); }
.iv-modal-title { font-size: 16px; font-weight: 700; color: #111827; margin-bottom: 8px; }
.iv-modal-body { font-size: 13.5px; color: #4B5563; line-height: 1.5; margin-bottom: 20px; }
.iv-modal-actions { display: flex; justify-content: flex-end; gap: 10px; }

@media (max-width: 600px) {
  .sc-fg, .sc-fg--three { grid-template-columns: 1fr; }
  .sc-tabs { mask-image: linear-gradient(to right, transparent 0, black 16px, black calc(100% - 16px), transparent 100%); -webkit-mask-image: linear-gradient(to right, transparent 0, black 16px, black calc(100% - 16px), transparent 100%); }
}
</style>