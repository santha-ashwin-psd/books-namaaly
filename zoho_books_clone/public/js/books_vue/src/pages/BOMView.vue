<template>
<div class="sc-page">
  <div class="sc-sticky">
    <div class="sc-header">
      <div style="display:flex;align-items:center;gap:12px;">
        <button class="iv-back" @click="router.push('/manufacturing/bom')" style="background:none;border:none;cursor:pointer;color:#2563eb;display:flex;align-items:center;gap:4px;font-weight:600;font-size:13px;padding:0;">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
          Back
        </button>
        <span class="sc-title">{{ isNew ? 'New Bill of Materials' : bom.name }}</span>
        <span v-if="!isNew && bom.bom_version" style="font-size:12px;color:#6b7280;font-weight:600;">v{{ bom.bom_version }}</span>
        <div v-if="!isNew" class="inv-status-badge"
             style="font-size:12px;padding:3px 8px;border-radius:12px;"
             :style="bom.docstatus===1 ? 'background:#dcfce7;color:#16a34a' : (bom.docstatus===2 ? 'background:#fee2e2;color:#dc2626' : 'background:#fef3c7;color:#b45309')">
          {{ docStatusLabel }}
        </div>
      </div>
      <div style="display:flex;gap:10px;">
        <button class="nim-btn" style="background:#fff;border:1px solid #e5e7eb;padding:8px 16px;border-radius:8px;font-weight:600;cursor:pointer;" @click="router.push('/manufacturing/bom')" :disabled="saving || submitting">Back</button>
        <button v-if="!isNew && bom.docstatus===2" class="sc-save-btn" @click="amendBom" :disabled="submitting">
          {{ submitting ? 'Amending...' : 'Amend (New Revision)' }}
        </button>
        <button v-if="!isNew && bom.docstatus===1" class="nim-btn" style="background:#fee2e2;color:#dc2626;border:1px solid #fecaca;padding:8px 16px;border-radius:8px;font-weight:600;cursor:pointer;" @click="cancelBom" :disabled="submitting">
          {{ submitting ? 'Cancelling...' : 'Cancel BOM' }}
        </button>
        <button v-if="!isNew && bom.docstatus===0" class="sc-save-btn" @click="submitBom" :disabled="submitting || saving">
          {{ submitting ? 'Submitting...' : 'Submit' }}
        </button>
        <button v-if="!readOnly" class="sc-save-btn" @click="save" :disabled="saving || loading">
          <span v-if="saving" style="display:inline-block;width:12px;height:12px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .6s linear infinite;margin-right:6px;"></span>
          {{ isNew ? 'Save BOM' : 'Save Changes' }}
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

  <!-- Tab 1: Production Item -->
  <div v-if="activeTab === 'production'" class="sc-body sc-body--narrow">
    <div class="sc-col-main">
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
          </div>
          <div>
            <div class="sc-card-title">Production Item</div>
            <div class="sc-card-subtitle">Select the finished product you are manufacturing.</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-fg sc-fg--single" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Production Item <span class="sc-required">*</span></label>
            <select class="nim-input" v-model="bom.item" :disabled="readOnly">
              <option value="">— Select Manufactured Item —</option>
              <option v-for="i in manufacturedItems" :key="i.name" :value="i.name">{{ i.item_name || i.name }}</option>
            </select>
          </div>
        </div>
        <div class="sc-fg" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Quantity <span class="sc-required">*</span></label>
            <input type="number" class="nim-input" v-model="bom.quantity" @change="onQtyChange" min="0.01" step="any" :disabled="readOnly" />
            <div class="sc-field-hint">How many units this BOM produces.</div>
          </div>
          <div class="nim-field">
            <label class="nim-label">Routing</label>
            <input type="text" class="nim-input sc-input--readonly" value="Coming Soon" disabled style="font-style:italic;" />
            <div class="sc-field-hint">Routing integration is coming soon.</div>
          </div>
        </div>
        <div class="sc-fg sc-fg--three" style="margin-top:16px;">
          <label class="sc-toggle-row" style="padding:8px;background:none;"><input type="checkbox" v-model="bom.is_active" :true-value="1" :false-value="0" style="margin-right:8px;"/> <span style="font-size:13px;font-weight:600;">Is Active</span></label>
          <label class="sc-toggle-row" style="padding:8px;background:none;"><input type="checkbox" v-model="bom.is_default" :true-value="1" :false-value="0" style="margin-right:8px;"/> <span style="font-size:13px;font-weight:600;">Is Default</span></label>
          <label class="sc-toggle-row" style="padding:8px;background:none;"><input type="checkbox" v-model="bom.allow_alternative_item" :true-value="1" :false-value="0" style="margin-right:8px;"/> <span style="font-size:13px;font-weight:600;">Allow Alt Item</span></label>
        </div>
      </div>

      <div class="sc-card" style="padding:0;overflow:hidden;">
        <div style="display:flex;background:#f8f9fc;border-bottom:1px solid #e8ecf2;">
          <div style="flex:1;padding:16px 20px;border-right:1px solid #e8ecf2;">
            <div style="font-size:11px;color:#6b7280;text-transform:uppercase;font-weight:600;margin-bottom:4px;">Raw Material Cost</div>
            <div style="font-size:18px;font-weight:700;color:#111827;">{{ fmt(rm_cost) }}</div>
          </div>
          <div style="flex:1;padding:16px 20px;border-right:1px solid #e8ecf2;">
            <div style="font-size:11px;color:#6b7280;text-transform:uppercase;font-weight:600;margin-bottom:4px;">Operation Cost</div>
            <div style="font-size:18px;font-weight:700;color:#111827;">{{ fmt(op_cost) }}</div>
          </div>
          <div style="flex:1;padding:16px 20px;border-right:1px solid #e8ecf2;">
            <div style="font-size:11px;color:#dc2626;text-transform:uppercase;font-weight:600;margin-bottom:4px;">Scrap Value</div>
            <div style="font-size:18px;font-weight:700;color:#dc2626;">-{{ fmt(scrap_value) }}</div>
          </div>
          <div style="flex:1;padding:16px 20px;background:#eff6ff;">
            <div style="font-size:11px;color:#1e40af;text-transform:uppercase;font-weight:700;margin-bottom:4px;">Total Mfg Cost</div>
            <div style="font-size:18px;font-weight:800;color:#1e3a8a;">{{ fmt(total_cost) }}</div>
          </div>
        </div>
      </div>

      <div class="sc-card" style="max-width:100%;overflow-x:auto;">
        <div class="sc-card-header" style="justify-content:space-between;">
          <div style="display:flex;align-items:center;gap:14px;">
            <div class="sc-card-icon sc-card-icon--blue">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>
            </div>
            <div>
              <div class="sc-card-title">Raw Materials</div>
            </div>
          </div>
          <button class="sc-upload-btn" @click="addMaterial">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
            Add Row
          </button>
        </div>
        <div class="sc-divider"></div>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead>
            <tr>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Item Code</th>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">UOM</th>
              <th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Qty</th>
              <th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Rate</th>
              <th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Amount</th>
              <th style="width:40px;border-bottom:1px solid #e5e7eb;"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!bom.items || !bom.items.length">
              <td colspan="6" style="text-align:center;padding:24px;color:#9ca3af;">No raw materials added.</td>
            </tr>
            <tr v-for="(rm, idx) in bom.items" :key="idx">
              <td style="padding:6px;"><select class="nim-input" style="padding:6px 10px;" v-model="rm.item_code" @change="onRmItemChange(rm)"><option value="">— Select —</option><option v-for="i in stockItems" :key="i.name" :value="i.name">{{ i.item_name || i.name }}</option></select></td>
              <td style="padding:6px;"><select class="nim-input" style="padding:6px 10px;" v-model="rm.uom"><option v-for="u in uomList" :key="u" :value="u">{{ u }}</option></select></td>
              <td style="padding:6px;"><input type="number" class="nim-input" style="padding:6px 10px;text-align:right;" v-model="rm.qty" min="0" step="any"/></td>
              <td style="padding:6px;"><input type="number" class="nim-input" style="padding:6px 10px;text-align:right;" v-model="rm.rate" min="0" step="any"/></td>
              <td style="padding:6px;text-align:right;font-weight:600;vertical-align:middle;">{{ fmt(rm.qty * rm.rate) }}</td>
              <td style="padding:6px;text-align:center;vertical-align:middle;">
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
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
            </div>
            <div>
              <div class="sc-card-title">Operations</div>
            </div>
          </div>
          <button class="sc-upload-btn" @click="addOp">
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
              <th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Time (Mins)</th>
              <th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Hour Rate</th>
              <th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Cost</th>
              <th style="width:40px;border-bottom:1px solid #e5e7eb;"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!bom.operations || !bom.operations.length">
              <td colspan="6" style="text-align:center;padding:24px;color:#9ca3af;">No operations added.</td>
            </tr>
            <tr v-for="(op, idx) in bom.operations" :key="idx">
              <td style="padding:6px;">
                <select class="nim-input" style="padding:6px 10px;width:100%;" v-model="op.operation">
                  <option value="">— Select —</option>
                  <option v-for="o in operationsList" :key="o.name" :value="o.name">{{ o.name }}</option>
                </select>
              </td>
              <td style="padding:6px;">
                <select class="nim-input" style="padding:6px 10px;width:100%;" v-model="op.workstation" @change="onWorkstationChange(op)">
                  <option value="">— Select —</option>
                  <option v-for="w in workstationsList" :key="w.name" :value="w.name">{{ w.name }}</option>
                </select>
              </td>
              <td style="padding:6px;"><input type="number" class="nim-input" style="padding:6px 10px;text-align:right;" v-model="op.time_in_mins" min="0" step="any" /></td>
              <td style="padding:6px;"><input type="number" class="nim-input" style="padding:6px 10px;text-align:right;" v-model="op.hour_rate" min="0" step="any" /></td>
              <td style="padding:6px;text-align:right;font-weight:600;vertical-align:middle;">{{ fmt((op.time_in_mins / 60) * op.hour_rate) }}</td>
              <td style="padding:6px;text-align:center;vertical-align:middle;">
                <button @click="removeOp(idx)" style="background:none;border:none;color:#dc2626;cursor:pointer;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Tab 2: Scrap & Process Loss -->
  <div v-if="activeTab === 'scrap'" class="sc-body sc-body--narrow">
    <div class="sc-col-main">
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon" style="background:#fee2e2;color:#dc2626;box-shadow:inset 0 0 0 1px rgba(220,38,38,.08), 0 2px 6px rgba(220,38,38,.12);">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
          </div>
          <div>
            <div class="sc-card-title">Scrap & Process Loss</div>
            <div class="sc-card-subtitle">Manage material loss and scrap value.</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-fg sc-fg--single">
          <div class="nim-field">
            <label class="nim-label">Process Loss (%)</label>
            <input type="number" class="nim-input" v-model="bom.process_loss" min="0" max="100" step="any" />
            <div class="sc-field-hint">Percentage of material permanently lost.</div>
          </div>
        </div>
      </div>
      <div class="sc-card" style="max-width:100%;overflow-x:auto;">
        <div class="sc-card-header" style="justify-content:space-between;">
          <div style="display:flex;align-items:center;gap:14px;">
            <div class="sc-card-title">Scrap Items</div>
          </div>
          <button class="sc-upload-btn" @click="addScrap">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
            Add Scrap
          </button>
        </div>
        <div class="sc-divider"></div>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead>
            <tr>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Scrap Item Code</th>
              <th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Qty</th>
              <th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Rate</th>
              <th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Amount</th>
              <th style="width:40px;border-bottom:1px solid #e5e7eb;"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!bom.scrap_items || !bom.scrap_items.length">
              <td colspan="5" style="text-align:center;padding:24px;color:#9ca3af;">No scrap items added.</td>
            </tr>
            <tr v-for="(sc, idx) in bom.scrap_items" :key="idx">
              <td style="padding:6px;"><select class="nim-input" style="padding:6px 10px;" v-model="sc.item_code"><option value="">— Select —</option><option v-for="i in stockItems" :key="i.name" :value="i.name">{{ i.item_name || i.name }}</option></select></td>
              <td style="padding:6px;"><input type="number" class="nim-input" style="padding:6px 10px;text-align:right;" v-model="sc.qty" min="0" step="any" /></td>
              <td style="padding:6px;"><input type="number" class="nim-input" style="padding:6px 10px;text-align:right;" v-model="sc.rate" min="0" step="any" /></td>
              <td style="padding:6px;text-align:right;font-weight:600;color:#dc2626;vertical-align:middle;">{{ fmt(sc.qty * sc.rate) }}</td>
              <td style="padding:6px;text-align:center;vertical-align:middle;">
                <button @click="removeScrap(idx)" style="background:none;border:none;color:#dc2626;cursor:pointer;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Tab 3: More Info -->
  <div v-if="activeTab === 'more'" class="sc-body sc-body--narrow">
    <div class="sc-col-main">
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
          </div>
          <div>
            <div class="sc-card-title">More Information</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-fg sc-fg--single" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Project</label>
            <input type="text" class="nim-input" v-model="bom.project" />
          </div>
        </div>
        <div class="sc-fg sc-fg--single" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Description</label>
            <textarea class="nim-input" v-model="bom.description" rows="3"></textarea>
          </div>
          <div class="nim-field">
            <label class="nim-label">Internal Notes</label>
            <textarea class="nim-input" v-model="bom.internal_notes" rows="3"></textarea>
          </div>
        </div>
        <div class="sc-fg sc-fg--single" style="margin-top:16px;">
          <label class="sc-toggle-row" style="padding:8px;background:none;"><input type="checkbox" v-model="bom.is_phantom_bom" :true-value="1" :false-value="0" style="margin-right:8px;"/> <span style="font-size:13px;font-weight:600;">Is Phantom BOM</span></label>
          <label class="sc-toggle-row" style="padding:8px;background:none;"><input type="checkbox" v-model="bom.set_rate_of_sub_assembly_from_bom" :true-value="1" :false-value="0" style="margin-right:8px;"/> <span style="font-size:13px;font-weight:600;">Set Rate of Sub-Assembly from BOM</span></label>
        </div>
      </div>
    </div>
  </div>

  <!-- Tab 4: Website -->
  <div v-if="activeTab === 'website'" class="sc-body sc-body--narrow">
    <div class="sc-col-main">
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
          </div>
          <div>
            <div class="sc-card-title">Website Settings</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-fg sc-fg--single">
          <label class="sc-toggle-row" style="padding:8px;background:none;"><input type="checkbox" v-model="bom.publish_bom" :true-value="1" :false-value="0" style="margin-right:8px;"/> <span style="font-size:13px;font-weight:600;">Publish BOM</span></label>
        </div>
      </div>
    </div>
  </div>

</div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet, apiSave, apiList, apiSubmit, apiCancel, apiAmend } from "../api/client.js";
import { useToast } from "../composables/useToast.js";

const route = useRoute();
const router = useRouter();
const { toast } = useToast();

const isNew = computed(() => route.params.name === "new");
const loading = ref(true);
const saving = ref(false);

const activeTab = ref("production");
const tabs = [
  { id: "production", label: "Production Item" },
  { id: "scrap", label: "Scrap & Process Loss" },
  { id: "more", label: "More Information" },
  { id: "website", label: "Website" },
];

const bom = ref({
  doctype: "BOM",
  item: "",
  quantity: 1,
  is_active: 1,
  is_default: 1,
  allow_alternative_item: 0,
  set_rate_of_sub_assembly_from_bom: 0,
  is_phantom_bom: 0,
  process_loss: 0,
  publish_bom: 0,
  items: [],
  operations: [],
  scrap_items: [],
  rm_cost: 0,
  op_cost: 0,
  scrap_value: 0,
  total_cost: 0,
});

const manufacturedItems = ref([]);
const stockItems = ref([]);
const uomList = ref([]);
const operationsList = ref([]);
const workstationsList = ref([]);
const oldQty = ref(1);
const submitting = ref(false);

// docstatus: 0 = Draft, 1 = Submitted, 2 = Cancelled.
// A submitted or cancelled BOM shouldn't be freely edited — it should be
// amended into a new draft revision instead, so the recipe history stays intact.
const readOnly = computed(() => !isNew.value && (bom.value.docstatus === 1 || bom.value.docstatus === 2));
const docStatusLabel = computed(() => {
  if (isNew.value) return "";
  return { 0: "Draft", 1: "Submitted", 2: "Cancelled" }[bom.value.docstatus] || "Draft";
});

onMounted(async () => {
  loading.value = true;
  try {
    // Fetch Items for the Production Item dropdown (removing strict is_manufactured filter for easier onboarding)
    const mfg = await apiList("Item", { fields: ["name", "item_name"], limit: 1000, order: "name asc" });
    manufacturedItems.value = mfg || [];

    const stk = await apiList("Item", { fields: ["name", "item_name", "standard_rate", "stock_uom"], filters: [["is_stock_item", "=", 1]], limit: 5000, order: "name asc" });
    stockItems.value = stk || [];
    
    const uoms = await apiList("UOM", { fields: ["name"], order: "name asc", limit: 200 });
    uomList.value = (uoms || []).map((r) => r.name);

    const ops = await apiList("Operation", { fields: ["name"], limit: 1000, order: "name asc" });
    operationsList.value = ops || [];

    const wks = await apiList("Workstation", { fields: ["name", "hour_rate"], limit: 1000, order: "name asc" });
    workstationsList.value = wks || [];

    await loadBom();
  } catch (e) {
    toast("Error loading data: " + e.message, "error");
    router.push("/manufacturing/bom");
  }
  loading.value = false;
});

async function loadBom() {
  if (!isNew.value) {
    const data = await apiGet("BOM", route.params.name);
    bom.value = data;
    oldQty.value = data.quantity || 1;
    if (!bom.value.items) bom.value.items = [];
    if (!bom.value.operations) bom.value.operations = [];
    if (!bom.value.scrap_items) bom.value.scrap_items = [];
  }
}

// Amending pushes to a new /manufacturing/bom/:name — Vue Router reuses this
// component instance for same-route param changes, so onMounted won't refire.
// Refetch explicitly whenever the route's :name param changes.
watch(() => route.params.name, () => {
  loadBom().catch((e) => toast("Error loading BOM: " + e.message, "error"));
});


function onQtyChange() {
  const newQty = parseFloat(bom.value.quantity) || 0;
  if (newQty <= 0) {
    bom.value.quantity = 1;
    return;
  }
  const ratio = newQty / oldQty.value;
  
  if (bom.value.items) {
    bom.value.items.forEach(rm => {
      rm.qty = (rm.qty || 0) * ratio;
    });
  }
  if (bom.value.scrap_items) {
    bom.value.scrap_items.forEach(sc => {
      sc.qty = (sc.qty || 0) * ratio;
    });
  }
  
  oldQty.value = newQty;
}

function onRmItemChange(rm) {
  if (!rm.item_code) return;
  const item = stockItems.value.find(i => i.name === rm.item_code);
  if (item) {
    rm.rate = item.standard_rate || 0;
    rm.uom = item.stock_uom || "Nos";
    rm.item_name = item.item_name;
  }
}

function onWorkstationChange(op) {
  if (!op.workstation) return;
  const w = workstationsList.value.find(x => x.name === op.workstation);
  if (w) {
    op.hour_rate = w.hour_rate || 0;
  }
}

function addMaterial() {
  bom.value.items.push({ item_code: "", uom: "Nos", qty: 1, rate: 0 });
}
function removeMaterial(idx) {
  bom.value.items.splice(idx, 1);
}

function addOp() {
  bom.value.operations.push({ operation: "", workstation: "", time_in_mins: 60, hour_rate: 0 });
}
function removeOp(idx) {
  bom.value.operations.splice(idx, 1);
}

function addScrap() {
  bom.value.scrap_items.push({ item_code: "", qty: 1, rate: 0 });
}
function removeScrap(idx) {
  bom.value.scrap_items.splice(idx, 1);
}

const rm_cost = computed(() => {
  return (bom.value.items || []).reduce((sum, rm) => sum + (parseFloat(rm.qty) || 0) * (parseFloat(rm.rate) || 0), 0);
});

const op_cost = computed(() => {
  return (bom.value.operations || []).reduce((sum, op) => sum + ((parseFloat(op.time_in_mins) || 0) / 60) * (parseFloat(op.hour_rate) || 0), 0);
});

const scrap_value = computed(() => {
  return (bom.value.scrap_items || []).reduce((sum, sc) => sum + (parseFloat(sc.qty) || 0) * (parseFloat(sc.rate) || 0), 0);
});

const total_cost = computed(() => {
  return rm_cost.value + op_cost.value - scrap_value.value;
});

async function save() {
  if (!bom.value.item) {
    return toast("Please select a Production Item", "error");
  }
  if (!bom.value.quantity || bom.value.quantity <= 0) {
    return toast("Quantity must be greater than 0", "error");
  }
  
  const pl = parseFloat(bom.value.process_loss) || 0;
  if (pl < 0 || pl > 100) {
    return toast("Process Loss must be between 0 and 100%", "error");
  }
  
  let totalScrapQty = 0;
  bom.value.scrap_items.forEach(sc => totalScrapQty += (parseFloat(sc.qty) || 0));
  if (totalScrapQty > bom.value.quantity) {
    return toast("Total Scrap quantity cannot exceed Production Quantity", "error");
  }

  saving.value = true;
  try {
    bom.value.rm_cost = rm_cost.value;
    bom.value.op_cost = op_cost.value;
    bom.value.scrap_value = scrap_value.value;
    bom.value.total_cost = total_cost.value;

    const doc = await apiSave(bom.value);
    toast(isNew.value ? "BOM created successfully" : "BOM updated");
    if (isNew.value) {
      router.replace(`/manufacturing/bom/${doc.name}`);
    } else {
      bom.value = doc;
      oldQty.value = doc.quantity || 1;
    }
  } catch (e) {
    toast(e.message, "error");
  }
  saving.value = false;
}

async function submitBom() {
  if (!bom.value.name) return;
  submitting.value = true;
  try {
    const doc = await apiSubmit("BOM", bom.value.name);
    bom.value = doc;
    toast("BOM submitted — it's now the active revision");
  } catch (e) {
    toast(e.message, "error");
  }
  submitting.value = false;
}

async function cancelBom() {
  if (!bom.value.name) return;
  if (!confirm("Cancel this BOM? You can amend it into a new draft revision afterwards.")) return;
  submitting.value = true;
  try {
    const doc = await apiCancel("BOM", bom.value.name);
    bom.value = doc;
    toast("BOM cancelled");
  } catch (e) {
    toast(e.message, "error");
  }
  submitting.value = false;
}

async function amendBom() {
  if (!bom.value.name) return;
  submitting.value = true;
  try {
    const doc = await apiAmend("BOM", bom.value.name);
    toast(`New revision ${doc.name} created — v${doc.bom_version}`);
    router.push(`/manufacturing/bom/${doc.name}`);
  } catch (e) {
    toast(e.message, "error");
  }
  submitting.value = false;
}

function fmt(n) {
  if (isNaN(n) || n == null) return "0.00";
  return Number(n).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
</script>

<style scoped>
@keyframes spin { to { transform: rotate(360deg) } }

/* ── Page ──────────────────────────────────────────────────────────── */
.sc-page {
  background: #f0f2f5;
  padding-bottom: 32px;
  min-height: 100vh;
}

/* ── Sticky ────────────────────────────────────────────────────────── */
.sc-sticky {
  position: sticky;
  top: 0;
  z-index: 20;
  background: #f0f2f5;
}
.sc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 24px 0;
}
.sc-title {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a2e;
  letter-spacing: -0.3px;
}
.sc-save-btn {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 13.5px;
  font-weight: 600;
  padding: 9px 20px;
  border-radius: 9px;
  background: linear-gradient(135deg, #2f74f5 0%, #1a6ef7 100%);
  border: none;
  color: #fff;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(26,110,247,.28), inset 0 1px 0 rgba(255,255,255,.18);
  transition: box-shadow .18s ease, transform .18s ease, filter .18s ease;
}
.sc-save-btn:hover:not(:disabled) {
  filter: brightness(1.04);
  box-shadow: 0 6px 18px rgba(26,110,247,.36), inset 0 1px 0 rgba(255,255,255,.2);
  transform: translateY(-1px);
}
.sc-save-btn:active:not(:disabled) { transform: translateY(0); box-shadow: 0 2px 8px rgba(26,110,247,.3); }

/* ── Tabs ──────────────────────────────────────────────────────────── */
.sc-tabs {
  display: flex;
  border-bottom: 2px solid #e4e8f0;
  padding: 0 24px;
  margin-top: 14px;
  overflow-x: auto;
  scrollbar-width: none;
}
.sc-tabs::-webkit-scrollbar { display: none; }
.sc-tab {
  padding: 10px 18px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: #868e96;
  white-space: nowrap;
  border-bottom: 2px solid transparent;
  border-radius: 8px 8px 0 0;
  margin-bottom: -2px;
  transition: color .15s, background .15s;
}
.sc-tab:hover { color: #374151; background: rgba(37,99,235,.05); }
.sc-tab--active { color: #2563eb; border-bottom-color: #2563eb; background: linear-gradient(180deg, rgba(37,99,235,.06), rgba(37,99,235,0)); }

/* ── Body layouts ──────────────────────────────────────────────────── */
.sc-body {
  padding: 24px;
  display: grid;
  gap: 20px;
  align-content: start;
}
.sc-body--narrow { max-width: 900px; margin: 0 auto; }
.sc-col-main { display: grid; gap: 20px; align-content: start; }

/* ── Cards ─────────────────────────────────────────────────────────── */
.sc-card {
  background: #fff;
  border: 1px solid #e8ecf2;
  border-radius: 14px;
  padding: 22px 24px;
  box-shadow: 0 1px 2px rgba(16,24,40,.04), 0 1px 3px rgba(16,24,40,.03);
  transition: box-shadow .2s ease, transform .2s ease, border-color .2s ease;
}
.sc-card:hover {
  box-shadow: 0 6px 20px rgba(16,24,40,.07), 0 2px 6px rgba(16,24,40,.04);
  border-color: #dbe3ee;
  transform: translateY(-1px);
}
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

/* ── Form grid ─────────────────────────────────────────────────────── */
.sc-fg { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.sc-fg--single { grid-template-columns: 1fr; }
.sc-fg--three  { grid-template-columns: 1fr 1fr 1fr; }

.sc-input--readonly { background: #f8fafc; color: #475569; cursor: default; }
.sc-input--readonly:focus { border-color: #e4e8f0; box-shadow: none; }
.sc-field-hint {
  display: flex; align-items: center; gap: 5px; margin-top: 5px; font-size: 12px; color: #6b7280;
}

.sc-upload-btn {
  display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px;
  border: 1.5px solid #2563eb; border-radius: 8px; background: #fff;
  color: #2563eb; font-size: 12.5px; font-weight: 600; cursor: pointer; transition: background .15s; white-space: nowrap;
}
.sc-upload-btn:hover { background: #eff6ff; }

/* Global nim styles used inside this component for form fields */
.nim-field { display: flex; flex-direction: column; gap: 6px; }
.nim-label { font-size: 13px; font-weight: 600; color: #374151; }
.nim-input {
  border: 1px solid #d1d5db; border-radius: 8px; padding: 10px 14px;
  font-size: 14px; color: #111827; outline: none; transition: border-color .15s, box-shadow .15s;
  background: #fff;
}
.nim-input:focus { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,.1); }

@media (max-width: 600px) {
  .sc-fg, .sc-fg--three { grid-template-columns: 1fr; }
  .sc-tabs { mask-image: linear-gradient(to right, transparent 0, black 16px, black calc(100% - 16px), transparent 100%); -webkit-mask-image: linear-gradient(to right, transparent 0, black 16px, black calc(100% - 16px), transparent 100%); }
}
</style>