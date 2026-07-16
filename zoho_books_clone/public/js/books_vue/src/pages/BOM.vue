<template>
<div class="bomx-page">
  <div class="bomx-two-col">

    <!-- ══════════ LEFT: BOM LIST ══════════ -->
    <div class="bomx-list-panel">
      <div class="bomx-panel-hdr">
        <span class="bomx-panel-title">📋 All BOMs <span class="bomx-count">({{ sorted.length }})</span></span>
        <button class="bomx-btn bomx-btn-mfg bomx-btn-sm" @click="openAdd"><span v-html="icon('plus',12)"></span> New</button>
      </div>
      <select class="bomx-fi bomx-status-filter" v-model="filterStatus">
        <option value="">All Status</option>
        <option value="active">Active</option>
        <option value="draft">Draft</option>
        <option value="inactive">Inactive</option>
        <option value="obsolete">Obsolete</option>
      </select>
      <input class="bomx-search" v-model="search" type="text" placeholder="Search BOM by item name or number…"/>
      <div class="bomx-list">
        <template v-if="loading">
          <div v-for="n in 5" :key="n" class="bomx-item"><div class="shimmer" style="height:38px;border-radius:6px"></div></div>
        </template>
        <div v-else-if="!sorted.length" class="bomx-list-empty">No BOMs found</div>
        <div v-else v-for="row in sorted" :key="row.name"
             class="bomx-item" :class="{active: !isNew && bom.name && chainRoot(bom.name) === chainRoot(row.name)}"
             @click="selectBOM(row.name)">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px">
            <div class="bomx-item-name">{{ row.item_name || row.item }}</div>
            <span class="bomx-badge" :class="statusClass(row)">{{ statusLabel(row) }}</span>
          </div>
          <div class="bomx-item-meta">
            <span class="mono">{{ row.name }}</span>
            <span>•</span>
            <span v-if="row.bom_version">v{{ formatVersion(row.bom_version) }}</span>
            <template v-if="row._versionCount > 1">
              <span>•</span>
              <span>{{ row._versionCount }} versions</span>
            </template>
          </div>
          <div class="bomx-item-right">
            <span style="font-size:12px;color:var(--bx-muted)">BOM Cost:</span>
            <span class="mono" style="font-size:12.5px;font-weight:700;color:var(--bx-mfgB)">{{ INR(row.total_cost) }}</span>
            <span v-if="row.is_default" class="bomx-default-tag">Default</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ══════════ RIGHT: BOM DETAIL ══════════ -->
    <div class="bomx-detail-panel">

      <!-- Empty state -->
      <div v-if="!selectedName" class="bomx-empty-state">
        <div class="bomx-empty-icon">📄</div>
        <div class="bomx-empty-title">Select a BOM</div>
        <div class="bomx-empty-sub">Choose a Bill of Materials from the list to view components, costs, and versions.</div>
        <button class="bomx-btn bomx-btn-mfg" @click="openAdd"><span v-html="icon('plus',13)"></span> Create BOM</button>
      </div>

      <template v-else>
        <div v-if="detailLoading" class="bomx-empty-state"><div class="shimmer" style="height:200px;border-radius:10px"></div></div>

        <template v-else>
          <!-- Header -->
          <div class="bomx-detail-hdr">
            <div class="bomx-hdr-flex">
              <div class="bomx-hdr-info">
                <div class="bomx-detail-title">{{ isNew ? 'New Bill of Materials' : (itemNameFor(bom.item) || bom.item) }}</div>
                <div class="bomx-detail-meta">
                  <span class="mono" v-if="!isNew">{{ bom.name }}</span>
                  <span v-if="!isNew">•</span>
                  <span>Produces: {{ bom.quantity || 1 }} {{ producedUom }}</span>
                  <span>•</span>
                  <span class="bomx-badge" :class="statusClass(bom)" style="font-size:11px">{{ statusLabel(bom) }}</span>
                </div>
              </div>
              <div class="bomx-hdr-actions">
                <button class="bomx-btn bomx-btn-ghost-inv" @click="goBackToList">Back</button>
                <button v-if="!isNew && isLatestInChain && (bom.docstatus===1 || bom.docstatus===2)"
                        class="bomx-btn bomx-btn-light" @click="newVersion" :disabled="submitting">
                  {{ submitting ? 'Creating…' : '+ New Version' }}
                </button>
                <button v-if="!isNew && isLatestInChain && bom.docstatus===1"
                        class="bomx-btn bomx-btn-ghost-inv" style="color:var(--bx-red);border-color:rgba(255,255,255,.4);background-color:white;"
                        @click="cancelBom" :disabled="submitting || cancelling">
                  {{ cancelling ? 'Cancelling…' : 'Cancel BOM' }}
                </button>
                <button v-if="!isNew && bom.docstatus===0" class="bomx-btn bomx-btn-light" @click="submitBom" :disabled="submitting || saving">
                  {{ submitting ? 'Submitting…' : 'Submit' }}
                </button>
                <button v-if="!readOnly" class="bomx-btn bomx-btn-light" @click="save" :disabled="saving || loading">
                  {{ saving ? 'Saving…' : (isNew ? 'Save BOM' : 'Save Changes') }}
                </button>
              </div>
            </div>
            <div v-if="!isNew && bomVersions.length" class="bomx-version-chips">
              <button v-for="v in bomVersions" :key="v.name"
                      class="bomx-vchip" :class="{ active: v.name === bom.name }"
                      @click="v.name !== bom.name && selectBOM(v.name)"
                      :title="v.name + ' — ' + statusLabel(v)">
                v{{ formatVersion(v.bom_version) }}
                <span v-if="v.name === bom.name" class="bomx-vchip-tick">✓</span>
              </button>
            </div>
          </div>

          <!-- Header fields -->
          <div class="bomx-hdr-fields">
            <div>
              <div class="bomx-hf-label">Production Item</div>
              <select class="bomx-fi" v-model="bom.item" :disabled="readOnly" style="width:100%" :title="itemNameFor(bom.item) || bom.item">
                <option value="">— Select —</option>
                <option v-for="i in manufacturedItems" :key="i.name" :value="i.name">{{ i.item_name || i.name }}</option>
              </select>
            </div>
            <div>
              <div class="bomx-hf-label">Quantity</div>
              <input class="bomx-fi bomx-fi-mono" type="number" v-model="bom.quantity" @change="onQtyChange" min="0.01" step="any" :disabled="readOnly" style="width:100%"/>
            </div>
            <div>
              <div class="bomx-hf-label">Routing</div>
              <select class="bomx-fi" v-model="bom.routing" :disabled="readOnly" @change="onRoutingChange" style="width:100%">
                <option value="">— Select —</option>
                <option v-for="r in routingsList" :key="r.name" :value="r.name">{{ r.name }}</option>
              </select>
            </div>
            <div>
              <div class="bomx-hf-label">BOM Type</div>
              <select class="bomx-fi" v-model="bom.bom_type" :disabled="readOnly || !isNew" style="width:100%" title="BOM Type is set on creation and cannot be changed afterwards.">
                <option value="Manufacturing">Manufacturing</option>
                <option value="Sub-Assembly">Sub-Assembly</option>
                <option value="Packing">Packing</option>
              </select>
            </div>
          </div>
          <div v-if="bom.bom_type === 'Packing'" class="bomx-hdr-fields" style="border-top:1px dashed var(--bx-border)">
            <div>
              <div class="bomx-hf-label">Bulk Item</div>
              <select class="bomx-fi" v-model="bom.bulk_item" @change="onBulkItemChange" :disabled="readOnly" style="width:100%" :title="itemNameFor(bom.bulk_item) || bom.bulk_item">
                <option value="">— Select —</option>
                <option v-for="i in bulkItemOptions" :key="i.name" :value="i.name">{{ i.item_name || i.name }}</option>
              </select>
              <div class="bomx-field-hint">The loose/bulk output (from a Manufacturing BOM) that this Packing BOM packs into the Production Item.</div>
            </div>
            <div>
              <div class="bomx-hf-label">Bulk Qty Consumed per Packed Unit</div>
              <input class="bomx-fi bomx-fi-mono" type="number" v-model="bom.bulk_qty_per_unit" min="0" step="any" :disabled="readOnly" style="width:100%"/>
            </div>
            <div>
              <div class="bomx-hf-label">Bulk Item Rate (₹)</div>
              <input class="bomx-fi bomx-fi-mono" type="number" v-model="bom.bulk_rate" min="0" step="any" :disabled="readOnly" style="width:100%"/>
            </div>
          </div>
          <div class="bomx-toggle-row">
            <label class="bomx-toggle"><input type="checkbox" v-model="bom.is_active" :true-value="1" :false-value="0" :disabled="readOnly"/> Is Active</label>
            <label class="bomx-toggle"><input type="checkbox" v-model="bom.is_default" :true-value="1" :false-value="0" :disabled="readOnly"/> Is Default</label>
          </div>

          <!-- Tabs -->
          <div class="bomx-tabs">
            <button v-for="t in tabs" :key="t.id" class="bomx-tab" :class="{active: activeTab===t.id}" @click="activeTab=t.id">{{ t.label }}</button>
          </div>

          <div class="bomx-body">

            <!-- ── Components tab ── -->
            <div v-if="activeTab==='components'">
              <div v-if="readOnly" class="bomx-notice">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/></svg>
                This BOM is {{ bom.docstatus===2?'cancelled':'submitted' }}. {{ isLatestInChain ? 'Create a new version to make changes.' : 'This is an older version — open the latest version to make changes.' }}
              </div>

              <!-- Cost summary strip -->
              <div class="bomx-cost-summary">
                <div class="bomx-cost-title">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                  BOM Cost Summary
                </div>
                <div class="bomx-cost-grid">
                  <div class="bomx-cost-cell">
                    <div class="bomx-cost-lbl">Material</div>
                    <div class="bomx-cost-val">{{ INR(rm_cost) }}</div>
                  </div>
                  <div class="bomx-cost-cell">
                    <div class="bomx-cost-lbl">Operations</div>
                    <div class="bomx-cost-val">{{ INR(op_cost) }}</div>
                  </div>
                  <div class="bomx-cost-cell">
                    <div class="bomx-cost-lbl">Scrap Value</div>
                    <div class="bomx-cost-val" style="color:var(--bx-red)">-{{ INR(scrap_value) }}</div>
                  </div>
                  <div class="bomx-cost-cell bomx-cost-cell-total">
                    <div class="bomx-cost-lbl" style="color:var(--bx-mfgB)">Total Cost</div>
                    <div class="bomx-cost-val" style="color:var(--bx-mfgB);font-size:19px">{{ INR(total_cost) }}</div>
                  </div>
                </div>
              </div>

              <!-- Raw Materials (Manufacturing / Sub-Assembly BOMs) -->
              <template v-if="bom.bom_type !== 'Packing'">
              <div class="bomx-section-lbl" style="display:flex;align-items:center;gap:6px">
                Raw Materials <span class="bomx-count" v-if="bom.items && bom.items.length">({{ bom.items.length }})</span>
              </div>
              <div class="bomx-rm-cards">
                <div v-if="!bom.items || !bom.items.length" class="bomx-tree-empty">No raw materials added.</div>
                <div class="bomx-rm-card" v-for="(rm, idx) in bom.items" :key="'rm'+idx">
                  <div class="bomx-rm-card-hdr">
                    <span class="bomx-tree-icon">📦</span>
                    <select class="bomx-fi bomx-fi-inline bomx-rm-card-title" v-model="rm.item_code" @change="onRmItemChange(rm)" :disabled="readOnly" :title="itemNameFor(rm.item_code) || rm.item_code">
                      <option value="">— Select item —</option>
                      <option v-for="i in rawMaterialItems" :key="i.name" :value="i.name">{{ i.item_name || i.name }}</option>
                    </select>
                    <div class="bomx-rm-card-amt">
                      <span class="bomx-rm-card-amt-lbl">Amount</span>
                      <span class="bomx-tree-cost" style="color:var(--bx-blue)">{{ INR((rm.qty||0)*(rm.rate||0)) }}</span>
                    </div>
                    <button v-if="!readOnly" class="bomx-btn-icon danger bomx-rm-card-rm" @click="removeMaterial(idx)" title="Remove">
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                  </div>
                  <div class="bomx-rm-card-body">
                    <div class="bomx-rm-field">
                      <label>Qty</label>
                      <input class="bomx-fi bomx-fi-mono" type="number" v-model="rm.qty" min="0" step="any" :disabled="readOnly"/>
                    </div>
                    <div class="bomx-rm-field">
                      <label>UOM</label>
                      <select class="bomx-fi" v-model="rm.uom" :disabled="readOnly">
                        <option v-for="u in uomList" :key="u" :value="u">{{ u }}</option>
                      </select>
                    </div>
                    <div class="bomx-rm-field">
                      <label>Rate (₹)</label>
                      <input class="bomx-fi bomx-fi-mono" type="number" v-model="rm.rate" min="0" step="any" :disabled="readOnly"/>
                      <div v-if="rmLandedInfo(rm.item_code)?.has_landed_cost" class="bomx-landed-hint" :title="`Base ${INR(rmLandedInfo(rm.item_code).base_rate)} + landed ${INR(rmLandedInfo(rm.item_code).landed_rate)} = ${INR(rmLandedInfo(rm.item_code).valuation_rate)} at ${rmLandedInfo(rm.item_code).warehouse}`">
                        🚚 Warehouse rate incl. landed cost: {{ INR(rmLandedInfo(rm.item_code).valuation_rate) }}
                        <a v-if="!readOnly" href="javascript:void(0)" @click="useLandedRate(rm)">Use</a>
                      </div>
                    </div>
                    <div class="bomx-rm-field bomx-rm-field-wide">
                      <label>Sub-Assembly BOM</label>
                      <select class="bomx-fi" v-model="rm.sub_assembly_bom" :disabled="readOnly">
                        <option value="">— Select —</option>
                        <option v-for="b in bomsList.filter(b => b.item === rm.item_code)" :key="b.name" :value="b.name">{{ b.name }}</option>
                      </select>
                      <div class="bomx-field-hint" v-if="rm.item_code && !bomsList.some(b => b.item === rm.item_code)">No submitted BOM exists yet for this item — it can't be used as a sub-assembly until one is created.</div>
                      <div class="bomx-field-hint bomx-field-hint-danger" v-else-if="rm.sub_assembly_bom && wouldCreateCycle(rm.sub_assembly_bom)">
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="vertical-align:-1px"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                        Circular reference: this sub-assembly loops back to this BOM. Explosion will be truncated.
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div v-if="!readOnly" class="bomx-add-row" @click="addMaterial">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                Add Component
              </div>
              </template>

              <!-- Packing Materials (Packing BOMs only) -->
              <template v-else>
              <div class="bomx-section-lbl" style="display:flex;align-items:center;gap:6px">
                Packing Materials <span class="bomx-count" v-if="bom.packing_items && bom.packing_items.length">({{ bom.packing_items.length }})</span>
              </div>
              <div class="bomx-field-hint" style="margin-bottom:10px">Bottles, caps, labels, cartons etc. consumed per Quantity of the packed unit — the Bulk Item above is consumed separately.</div>
              <div class="bomx-rm-cards">
                <div v-if="!bom.packing_items || !bom.packing_items.length" class="bomx-tree-empty">No packing materials added.</div>
                <div class="bomx-rm-card" v-for="(pi, idx) in bom.packing_items" :key="'pi'+idx">
                  <div class="bomx-rm-card-hdr">
                    <span class="bomx-tree-icon">🏷️</span>
                    <select class="bomx-fi bomx-fi-inline bomx-rm-card-title" v-model="pi.item_code" @change="onPackingItemChange(pi)" :disabled="readOnly" :title="itemNameFor(pi.item_code) || pi.item_code">
                      <option value="">— Select item —</option>
                      <option v-for="i in packingMaterialItems" :key="i.name" :value="i.name">{{ i.item_name || i.name }}</option>
                    </select>
                    <div class="bomx-rm-card-amt">
                      <span class="bomx-rm-card-amt-lbl">Amount</span>
                      <span class="bomx-tree-cost" style="color:var(--bx-blue)">{{ INR((pi.qty||0)*(pi.rate||0)) }}</span>
                    </div>
                    <button v-if="!readOnly" class="bomx-btn-icon danger bomx-rm-card-rm" @click="removePackingMaterial(idx)" title="Remove">
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                  </div>
                  <div class="bomx-rm-card-body">
                    <div class="bomx-rm-field">
                      <label>Qty</label>
                      <input class="bomx-fi bomx-fi-mono" type="number" v-model="pi.qty" min="0" step="any" :disabled="readOnly"/>
                    </div>
                    <div class="bomx-rm-field">
                      <label>UOM</label>
                      <select class="bomx-fi" v-model="pi.uom" :disabled="readOnly">
                        <option v-for="u in uomList" :key="u" :value="u">{{ u }}</option>
                      </select>
                    </div>
                    <div class="bomx-rm-field">
                      <label>Rate (₹)</label>
                      <input class="bomx-fi bomx-fi-mono" type="number" v-model="pi.rate" min="0" step="any" :disabled="readOnly"/>
                    </div>
                  </div>
                </div>
              </div>
              <div v-if="!readOnly" class="bomx-add-row" @click="addPackingMaterial">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                Add Packing Material
              </div>
              </template>

              <!-- Operations (Manufacturing / Sub-Assembly BOMs only — Packing BOMs don't run operations) -->
              <template v-if="bom.bom_type !== 'Packing'">
              <div class="bomx-tree-col-hdr" style="margin-top:20px">
                <div style="flex:1;padding-left:4px">Operations</div>
                <div style="min-width:80px;text-align:right">Mins</div>
                <div style="min-width:90px;text-align:right">Hr Rate (₹)</div>
                <div style="min-width:90px;text-align:right">Cost (₹)</div>
                <div style="width:36px"></div>
              </div>
              <div class="bomx-tree">
                <div v-if="!bom.operations || !bom.operations.length" class="bomx-tree-empty">No operations added.</div>
                <div class="bomx-tree-row" v-for="(op, idx) in bom.operations" :key="'op'+idx">
                  <div class="bomx-tree-dot" style="background:var(--bx-violet)"></div>
                  <span class="bomx-tree-icon">⚙️</span>
                  <div class="bomx-tree-selects">
                    <select class="bomx-fi bomx-fi-inline" style="flex:1" v-model="op.operation" :disabled="readOnly">
                      <option value="">— Operation —</option>
                      <option v-for="o in operationsList" :key="o.name" :value="o.name">{{ o.name }}</option>
                    </select>
                    <select class="bomx-fi bomx-fi-inline" style="flex:1" v-model="op.workstation" @change="onWorkstationChange(op)" :disabled="readOnly">
                      <option value="">— Workstation —</option>
                      <option v-for="w in workstationsList" :key="w.name" :value="w.name">{{ w.name }}</option>
                    </select>
                  </div>
                  <input class="bomx-fi bomx-fi-mono bomx-tree-rate-inp" type="number" v-model="op.time_in_mins" min="0" step="any" :disabled="readOnly"/>
                  <input class="bomx-fi bomx-fi-mono bomx-tree-rate-inp" type="number" v-model="op.hour_rate" min="0" step="any" :disabled="readOnly"/>
                  <span class="bomx-tree-cost" style="color:var(--bx-violet)">{{ INR(((op.time_in_mins||0)/60)*(op.hour_rate||0)) }}</span>
                  <div class="bomx-tree-actions">
                    <button v-if="!readOnly" class="bomx-btn-icon danger" @click="removeOp(idx)" title="Remove">
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                  </div>
                </div>
              </div>
              <div v-if="!readOnly" class="bomx-add-row" @click="addOp">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                Add Operation
              </div>
              </template>
            </div>

            <!-- ── Cost Breakdown tab ── -->
            <div v-if="activeTab==='costs'">
              <div style="font-size:13px;font-weight:700;color:var(--bx-text);margin-bottom:14px">Full Cost Breakdown</div>
              <table class="bomx-cost-table">
                <thead><tr>
                  <th style="text-align:left">Component</th>
                  <th style="text-align:right">Qty</th>
                  <th style="text-align:right">UOM</th>
                  <th style="text-align:right">Rate</th>
                  <th style="text-align:right">Amount</th>
                </tr></thead>
                <tbody>
                  <tr v-if="!bom.items || !bom.items.length"><td colspan="5" style="text-align:center;color:var(--bx-muted);padding:20px">No materials</td></tr>
                  <tr v-for="(rm, idx) in bom.items" :key="idx">
                    <td>{{ itemNameFor(rm.item_code) || rm.item_code }} <span class="mono" style="font-size:11px;color:var(--bx-muted)">{{ rm.item_code }}</span></td>
                    <td style="text-align:right" class="mono">{{ rm.qty }}</td>
                    <td style="text-align:right" class="mono">{{ rm.uom }}</td>
                    <td style="text-align:right" class="mono">{{ INR(rm.rate) }}</td>
                    <td style="text-align:right;font-weight:700" class="mono">{{ INR((rm.qty||0)*(rm.rate||0)) }}</td>
                  </tr>
                </tbody>
                <tfoot><tr>
                  <td colspan="4" style="font-weight:700;color:var(--bx-mfgB)">Total Material Cost</td>
                  <td style="text-align:right;font-weight:700;color:var(--bx-mfgB)" class="mono">{{ INR(rm_cost) }}</td>
                </tr></tfoot>
              </table>

              <div style="margin-top:20px">
                <div class="bomx-section-lbl">Labour &amp; Overhead</div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
                  <div class="bomx-lo-cell">
                    <div style="font-size:13px;font-weight:600">Operation Cost</div>
                    <div class="mono" style="font-weight:700">{{ INR(op_cost) }}</div>
                  </div>
                  <div class="bomx-lo-cell">
                    <div style="font-size:13px;font-weight:600">Scrap Value</div>
                    <div class="mono" style="font-weight:700;color:var(--bx-red)">-{{ INR(scrap_value) }}</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- ── Scrap tab ── -->
            <div v-if="activeTab==='scrap'">
              <div class="bomx-field-block">
                <div class="bomx-hf-label">Process Loss (%)</div>
                <input class="bomx-fi bomx-fi-mono" type="number" v-model="bom.process_loss" min="0" max="100" step="any" :disabled="readOnly" style="width:160px"/>
                <div class="bomx-field-hint">Percentage of material permanently lost during production.</div>
              </div>

              <div class="bomx-section-lbl" style="display:flex;align-items:center;gap:6px;margin-top:16px">
                Scrap Items <span class="bomx-count" v-if="bom.scrap_items && bom.scrap_items.length">({{ bom.scrap_items.length }})</span>
              </div>
              <div class="bomx-rm-cards">
                <div v-if="!bom.scrap_items || !bom.scrap_items.length" class="bomx-tree-empty">No scrap items added.</div>
                <div class="bomx-rm-card" v-for="(sc, idx) in bom.scrap_items" :key="idx">
                  <div class="bomx-rm-card-hdr">
                    <span class="bomx-tree-icon">🗑️</span>
                    <select class="bomx-fi bomx-fi-inline bomx-rm-card-title" v-model="sc.item_code" :disabled="readOnly" :title="itemNameFor(sc.item_code) || sc.item_code">
                      <option value="">— Select item —</option>
                      <option v-for="i in stockItems" :key="i.name" :value="i.name">{{ i.item_name || i.name }}</option>
                    </select>
                    <div class="bomx-rm-card-amt">
                      <span class="bomx-rm-card-amt-lbl">Amount</span>
                      <span class="bomx-tree-cost" style="color:var(--bx-red)">{{ INR((sc.qty||0)*(sc.rate||0)) }}</span>
                    </div>
                    <button v-if="!readOnly" class="bomx-btn-icon danger bomx-rm-card-rm" @click="removeScrap(idx)" title="Remove">
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                  </div>
                  <div class="bomx-rm-card-body">
                    <div class="bomx-rm-field">
                      <label>Qty</label>
                      <input class="bomx-fi bomx-fi-mono" type="number" v-model="sc.qty" min="0" step="any" :disabled="readOnly"/>
                    </div>
                    <div class="bomx-rm-field">
                      <label>Rate (₹)</label>
                      <input class="bomx-fi bomx-fi-mono" type="number" v-model="sc.rate" min="0" step="any" :disabled="readOnly"/>
                    </div>
                  </div>
                </div>
              </div>
              <div v-if="!readOnly" class="bomx-add-row" @click="addScrap">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                Add Scrap Item
              </div>
            </div>

            <!-- ── More Info tab ── -->
            <div v-if="activeTab==='more'">
              <div class="bomx-field-block">
                <div class="bomx-hf-label">Project</div>
                <input class="bomx-fi" type="text" v-model="bom.project" :disabled="readOnly" style="width:100%"/>
              </div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px">
                <div>
                  <div class="bomx-hf-label">Description</div>
                  <textarea class="bomx-fi" v-model="bom.description" rows="3" :disabled="readOnly" style="width:100%;resize:vertical"></textarea>
                </div>
                <div>
                  <div class="bomx-hf-label">Internal Notes</div>
                  <textarea class="bomx-fi" v-model="bom.internal_notes" rows="3" :disabled="readOnly" style="width:100%;resize:vertical"></textarea>
                </div>
              </div>
              <div class="bomx-toggle-row" style="margin-top:16px">
                <label class="bomx-toggle"><input type="checkbox" v-model="bom.is_phantom_bom" :true-value="1" :false-value="0" :disabled="readOnly"/> Is Phantom BOM</label>
                <label class="bomx-toggle"><input type="checkbox" v-model="bom.set_rate_of_sub_assembly_from_bom" :true-value="1" :false-value="0" :disabled="readOnly"/> Set Rate of Sub-Assembly from BOM</label>
              </div>
              <div class="bomx-toggle-row" style="margin-top:8px">
                <label class="bomx-toggle"><input type="checkbox" v-model="bom.publish_bom" :true-value="1" :false-value="0" :disabled="readOnly"/> Publish to Website</label>
              </div>
            </div>

            <!-- ── BOM Tree tab ── -->
            <div v-if="activeTab==='tree'">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
                <div>
                  <div style="font-size:13px;font-weight:700">Multi-Level BOM Explosion</div>
                  <div style="font-size:12px;color:var(--bx-muted)">Recursively expands all sub-assembly BOMs (including phantom BOMs) into leaf raw materials.</div>
                </div>
                <button class="bomx-btn bomx-btn-mfg" @click="loadBomTree" :disabled="treeLoading || isNew || bom.docstatus !== 1">
                  {{ treeLoading ? 'Exploding…' : 'Explode BOM' }}
                </button>
              </div>
              <div v-if="isNew || bom.docstatus !== 1" style="color:var(--bx-muted);font-size:13px">Submit the BOM first, then click "Explode BOM" to see the full multi-level tree.</div>
              <div v-else-if="!treeNodes.length && !treeLoading" style="color:var(--bx-muted);font-size:13px">Click "Explode BOM" to build the explosion tree.</div>
              <table v-if="treeNodes.length" class="bomx-cost-table">
                <thead><tr>
                  <th style="text-align:left">Item</th><th style="text-align:right">Qty</th><th style="text-align:left">UOM</th>
                  <th style="text-align:right">Rate</th><th style="text-align:right">Amount</th><th style="text-align:left">Sub-Assembly BOM</th>
                </tr></thead>
                <tbody>
                  <tr v-for="(node, idx) in treeNodes" :key="idx">
                    <td :style="{paddingLeft: (12+node.level*20)+'px'}">
                      <span :style="node.has_sub_assembly ? 'font-weight:700;color:var(--bx-mfgB)' : ''">{{ node.item_code }}</span>
                      <span v-if="node.is_phantom" style="font-size:10px;padding:1px 6px;background:var(--bx-mfgS);color:var(--bx-mfgB);border-radius:8px;font-weight:700;margin-left:4px">PHANTOM</span>
                      <div style="font-size:11px;color:var(--bx-muted)">{{ node.item_name }}</div>
                    </td>
                    <td style="text-align:right" class="mono">{{ INR(node.qty) }}</td>
                    <td>{{ node.uom }}</td>
                    <td style="text-align:right" class="mono">{{ INR(node.rate) }}</td>
                    <td style="text-align:right;font-weight:700" class="mono">{{ INR(node.amount) }}</td>
                    <td><span v-if="node.sub_assembly_bom" class="bomx-link" @click="router.push(`/manufacturing/bom/${node.sub_assembly_bom}`)">{{ node.sub_assembly_bom }}</span><span v-else style="color:var(--bx-muted)">—</span></td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- ── Compare tab ── -->
            <div v-if="activeTab==='compare'">
              <div style="display:flex;gap:10px;align-items:center;margin-bottom:16px;flex-wrap:wrap">
                <select class="bomx-fi" style="min-width:220px" v-model="compareBom2">
                  <option value="">— Select BOM to compare —</option>
                  <option v-for="b in bomsList.filter(b => b.name !== bom.name)" :key="b.name" :value="b.name">{{ b.name }} ({{ b.item }})</option>
                </select>
                <button class="bomx-btn bomx-btn-mfg" @click="runCompare" :disabled="compareLoading || !compareBom2 || isNew">
                  {{ compareLoading ? 'Comparing…' : 'Compare' }}
                </button>
              </div>
              <template v-if="compareResult">
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px">
                  <div class="bomx-lo-cell">
                    <div class="bomx-hf-label">BOM A (this)</div>
                    <div style="font-weight:700">{{ compareResult.bom1.name }}</div>
                    <div style="font-size:12px;color:var(--bx-muted)">{{ compareResult.bom1.item }} · Qty {{ compareResult.bom1.qty }}</div>
                    <div class="mono" style="font-weight:700;color:var(--bx-mfgB)">{{ INR(compareResult.bom1.total_cost) }}</div>
                  </div>
                  <div class="bomx-lo-cell">
                    <div class="bomx-hf-label">BOM B (selected)</div>
                    <div style="font-weight:700">{{ compareResult.bom2.name }}</div>
                    <div style="font-size:12px;color:var(--bx-muted)">{{ compareResult.bom2.item }} · Qty {{ compareResult.bom2.qty }}</div>
                    <div class="mono" style="font-weight:700;color:var(--bx-mfgB)">{{ INR(compareResult.bom2.total_cost) }}</div>
                  </div>
                </div>
                <div class="bomx-section-lbl">Materials</div>
                <table class="bomx-cost-table">
                  <thead><tr><th style="text-align:left">Item</th><th style="text-align:right">A Qty</th><th style="text-align:right">A Rate</th><th style="text-align:right">B Qty</th><th style="text-align:right">B Rate</th><th style="text-align:center">Change</th></tr></thead>
                  <tbody>
                    <tr v-for="m in compareResult.materials" :key="m.item_code">
                      <td>{{ m.item_code }}<div style="font-size:11px;color:var(--bx-muted)">{{ m.item_name }}</div></td>
                      <td style="text-align:right">{{ m.bom1_qty != null ? INR(m.bom1_qty) : '—' }}</td>
                      <td style="text-align:right">{{ m.bom1_rate != null ? INR(m.bom1_rate) : '—' }}</td>
                      <td style="text-align:right">{{ m.bom2_qty != null ? INR(m.bom2_qty) : '—' }}</td>
                      <td style="text-align:right">{{ m.bom2_rate != null ? INR(m.bom2_rate) : '—' }}</td>
                      <td style="text-align:center"><span class="bomx-badge" :class="'badge-'+m.status">{{ m.status.toUpperCase() }}</span></td>
                    </tr>
                  </tbody>
                </table>
                <div class="bomx-section-lbl" style="margin-top:16px">Operations</div>
                <table class="bomx-cost-table">
                  <thead><tr><th style="text-align:left">Operation</th><th style="text-align:right">A Time</th><th style="text-align:right">A Rate</th><th style="text-align:right">B Time</th><th style="text-align:right">B Rate</th><th style="text-align:center">Change</th></tr></thead>
                  <tbody>
                    <tr v-for="o in compareResult.operations" :key="o.operation">
                      <td>{{ o.operation }}</td>
                      <td style="text-align:right">{{ o.bom1_time != null ? o.bom1_time : '—' }}</td>
                      <td style="text-align:right">{{ o.bom1_rate != null ? INR(o.bom1_rate) : '—' }}</td>
                      <td style="text-align:right">{{ o.bom2_time != null ? o.bom2_time : '—' }}</td>
                      <td style="text-align:right">{{ o.bom2_rate != null ? INR(o.bom2_rate) : '—' }}</td>
                      <td style="text-align:center"><span class="bomx-badge" :class="'badge-'+o.status">{{ o.status.toUpperCase() }}</span></td>
                    </tr>
                  </tbody>
                </table>
              </template>
            </div>

          </div>


          <!-- Footer -->
          <div class="bomx-footer">
            <button class="bomx-btn bomx-btn-ghost-inv" style="color:var(--bx-red);border-color:rgba(201,42,42,.3)" @click="deleteFromDetail" v-if="!isNew && bom.docstatus===0">Delete BOM</button>
            <div style="flex:1"></div>
            <button v-if="!readOnly" class="bomx-btn bomx-btn-mfg" @click="save" :disabled="saving || loading">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13"/><polyline points="7 3 7 8 15 8"/></svg>
              {{ saving ? 'Saving…' : (isNew ? 'Save BOM' : 'Save Changes') }}
            </button>
          </div>
        </template>
      </template>
    </div>

  </div>
</div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useToast } from "../composables/useToast.js";
import { useConfirm } from "../composables/useConfirm.js";
import { apiGet, apiList, apiSave, apiDelete, apiSubmit, apiCancel, apiAmend, apiCall } from "../api/client.js";

const route = useRoute();
const router = useRouter();
const { toast } = useToast();
const { confirm } = useConfirm();

// ── LIST STATE ──────────────────────────────────────────────
const loading = ref(false);
const list = ref([]);
const search = ref("");
const filterStatus = ref("");

const selectedName = computed(() => (route.params.name && route.params.name !== "new") ? route.params.name : (route.params.name === "new" ? "new" : null));

async function loadList() {
  loading.value = true;
  try {
    const fields = ["name", "item", "is_active", "is_default", "docstatus", "bom_version", "amended_from", "modified", "rm_cost", "op_cost", "scrap_value", "total_cost"];
    const r = await apiList("BOM", { fields, limit: 1000, order: "modified desc" });
    list.value = r || [];
    if (list.value.length) {
      const uniqueItemCodes = [...new Set(list.value.map(row => row.item).filter(Boolean))];
      if (uniqueItemCodes.length) {
        try {
          const items = await apiList("Item", { fields: ["name", "item_name"], filters: [["name", "in", uniqueItemCodes]], limit: uniqueItemCodes.length });
          const itemNames = {};
          if (items) items.forEach(i => itemNames[i.name] = i.item_name);
          list.value.forEach(row => row.item_name = itemNames[row.item] || row.item);
        } catch (e) { /* degrade gracefully */ }
      }
    }
  } catch (e) {
    toast("Could not load BOMs", "error");
  }
  loading.value = false;
}

// Amended revisions link back via `amended_from`. Walk that chain to find the
// original root document, which we use as the stable grouping key for a version set.
function chainRoot(name) {
  const byName = new Map(list.value.map(r => [r.name, r]));
  let cur = byName.get(name);
  const seen = new Set();
  while (cur && cur.amended_from && !seen.has(cur.name)) {
    seen.add(cur.name);
    if (!byName.has(cur.amended_from)) break;
    cur = byName.get(cur.amended_from);
  }
  return cur ? cur.name : name;
}

const sorted = computed(() => {
  let r = list.value;
  if (filterStatus.value === "active") r = r.filter(i => i.is_active && i.docstatus !== 2);
  if (filterStatus.value === "inactive") r = r.filter(i => !i.is_active && i.docstatus !== 2);
  if (filterStatus.value === "draft") r = r.filter(i => i.docstatus === 0);
  if (filterStatus.value === "obsolete") r = r.filter(i => i.docstatus === 2);
  const q = search.value.toLowerCase().trim();
  if (q) r = r.filter(i => [i.item_name, i.item, i.name].filter(Boolean).join(" ").toLowerCase().includes(q));

  // Group all revisions that share the same base document id into a single list row.
  const groups = new Map();
  for (const row of r) {
    const key = chainRoot(row.name);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  }
  return [...groups.values()].map(rows => {
    // Prefer a non-cancelled revision as the representative; fall back to the newest overall.
    const notCancelled = rows.filter(x => x.docstatus !== 2);
    const pool = notCancelled.length ? notCancelled : rows;
    const rep = pool.slice().sort((a, b) => (Number(b.bom_version) || 0) - (Number(a.bom_version) || 0))[0];
    return { ...rep, _versionCount: rows.length };
  }).sort((a, b) => new Date(b.modified) - new Date(a.modified));
});

function statusLabel(row) {
  if (row.docstatus === 2) return "Obsolete";
  if (row.docstatus === 0) return "Draft";
  return row.is_active ? "Active" : "Inactive";
}
function statusClass(row) {
  const l = statusLabel(row);
  return l === "Active" ? "badge-active" : (l === "Draft" ? "badge-draft" : "badge-obsolete");
}

function selectBOM(name) {
  router.push(`/manufacturing/bom/${name}`);
}
function openAdd() {
  router.push("/manufacturing/bom/new");
}
function goBackToList() {
  router.push("/manufacturing/bom");
}

async function isBomDeletable(row) {
  if (row.docstatus === 1) {
    toast(`${row.name} is submitted and cannot be deleted. Cancel it first.`, "error");
    return false;
  }
  try {
    const inUse = await apiList("Work Order", { fields: ["name"], filters: [["bom", "=", row.name], ["docstatus", "!=", 2]], limit: 1 });
    if (inUse && inUse.length) {
      toast(`${row.name} is used by Work Order ${inUse[0].name} and cannot be deleted.`, "error");
      return false;
    }
  } catch (e) {
    toast(`Could not verify whether ${row.name} is in use — try again.`, "error");
    return false;
  }
  return true;
}

async function deleteFromDetail() {
  const row = { name: bom.value.name, docstatus: bom.value.docstatus };
  if (!(await isBomDeletable(row))) return;
  if (await confirm({ title: "Delete BOM?", body: `Are you sure you want to delete ${row.name}?`, okLabel: "Delete", okStyle: "danger" })) {
    try {
      await apiDelete("BOM", row.name);
      toast("BOM deleted");
      goBackToList();
      loadList();
    } catch (e) {
      toast("Could not delete BOM: " + e.message, "error");
    }
  }
}

// ── DETAIL STATE ─────────────────────────────────────────────
const isNew = computed(() => route.params.name === "new");
const detailLoading = ref(false);
const saving = ref(false);
const submitting = ref(false);
const cancelling = ref(false);

const activeTab = ref("components");
const tabs = [
  { id: "components", label: "Components" },
  { id: "costs",       label: "Cost Breakdown" },
  { id: "scrap",       label: "Scrap & Process Loss" },
  { id: "more",        label: "More Information" },
  { id: "tree",        label: "BOM Tree" },
  { id: "compare",     label: "Compare" },
];

function emptyBom() {
  return {
    doctype: "BOM", item: "", quantity: 1, routing: "",
    bom_type: mfgDefaultBomType.value || "Manufacturing",
    is_active: 1, is_default: 1, allow_alternative_item: 0,
    set_rate_of_sub_assembly_from_bom: mfgDefaultSubAssemblyRate.value ? 1 : 0, is_phantom_bom: 0,
    process_loss: 0, publish_bom: 0,
    items: [], operations: [], scrap_items: [],
    packing_items: [], bulk_item: "", bulk_qty_per_unit: 0, bulk_rate: 0,
    rm_cost: 0, op_cost: 0, scrap_value: 0, total_cost: 0,
  };
}
const mfgDefaultBomType = ref("Manufacturing");
const mfgDefaultSubAssemblyRate = ref(false);
const bom = ref(emptyBom());

const stockItems = ref([]);
// Production Item picker: only items that are actually manufactured (Finished Good / WIP).
const manufacturedItems = computed(() =>
  stockItems.value.filter(i => i.item_type === "Finished Good" || i.item_type === "Work In Progress")
);
// Raw-material row picker: exclude Finished Goods (a finished good shouldn't be consumed as a raw material).
const rawMaterialItems = computed(() =>
  stockItems.value.filter(i => i.item_type !== "Finished Good")
);
// Packing Materials row picker (Packing BOMs only): bottles, caps, labels,
// cartons etc. — restricted to the Packing Material item type so a raw
// material or finished good can't be picked into a packing line by mistake.
const packingMaterialItems = computed(() =>
  stockItems.value.filter(i => i.item_type === "Packing Material")
);
// Bulk Item picker (Packing BOMs only): the loose/bulk output being packed —
// same pool as the Production Item picker (Finished Good / WIP), since a
// Packing BOM's bulk source is whatever a Manufacturing BOM produced.
const bulkItemOptions = computed(() => manufacturedItems.value);
const uomList = ref([]);
const operationsList = ref([]);
const workstationsList = ref([]);
const routingsList = ref([]);
const bomsList = ref([]);
const oldQty = ref(1);
// Graph of parent BOM name -> [sub_assembly_bom names it references], used to detect
// circular sub-assembly chains before they're built (the backend depth-limits and
// dedupes silently during explosion, but gives no warning at edit time).
const subAssemblyEdges = ref({});

const treeNodes = ref([]);
const treeLoading = ref(false);
const compareBom2 = ref("");
const compareResult = ref(null);
const compareLoading = ref(false);

const readOnly = computed(() => !isNew.value && (bom.value.docstatus === 1 || bom.value.docstatus === 2));
const producedUom = computed(() => (stockItems.value.find(i => i.name === bom.value.item) || {}).stock_uom || "Nos");

function itemNameFor(code) {
  const i = stockItems.value.find(x => x.name === code) || manufacturedItems.value.find(x => x.name === code);
  return i ? i.item_name : null;
}

// All revisions sharing the same base document id as the open BOM, newest version first.
const bomVersions = computed(() => {
  if (!bom.value.name) return [];
  const base = chainRoot(bom.value.name);
  return list.value
    .filter(r => chainRoot(r.name) === base)
    .slice()
    .sort((a, b) => (Number(b.bom_version) || 0) - (Number(a.bom_version) || 0));
});
// Only the newest revision in a version chain may be cancelled/amended into a further version;
// older, superseded revisions are read-only history.
const isLatestInChain = computed(() => {
  if (!bomVersions.value.length) return true;
  return bomVersions.value[0].name === bom.value.name;
});
function formatVersion(v) {
  if (v == null || v === "") return "1.0";
  const n = Number(v);
  return Number.isFinite(n) ? n.toFixed(1) : String(v);
}

onMounted(async () => {
  loading.value = true;
  try {
    const stk = await apiList("Item", { fields: ["name", "item_name", "standard_rate", "stock_uom", "item_type", "default_warehouse"], filters: [["is_stock_item", "=", 1]], limit: 5000, order: "name asc" });
    stockItems.value = stk || [];
    refreshRmLandedCosts();
    const uoms = await apiList("UOM", { fields: ["name"], order: "name asc", limit: 200 });
    uomList.value = (uoms || []).map(r => r.name);
    const ops = await apiList("Operation", { fields: ["name"], limit: 1000, order: "name asc" });
    operationsList.value = ops || [];
    const wks = await apiList("Workstation", { fields: ["name", "hour_rate"], filters: [["is_active", "=", 1]], limit: 1000, order: "name asc" });
    workstationsList.value = wks || [];
    const rtg = await apiList("Routing", { fields: ["name"], filters: [["is_active", "=", 1]], limit: 1000, order: "name asc" });
    routingsList.value = rtg || [];
    const bl = await apiList("BOM", { fields: ["name", "item", "bom_type"], filters: [["docstatus", "=", 1]], limit: 2000, order: "name desc" });
    bomsList.value = bl || [];
    const saRows = await apiList("BOM Item", { fields: ["parent", "sub_assembly_bom"], filters: [["sub_assembly_bom", "!=", ""]], limit: 5000 });
    const edges = {};
    (saRows || []).forEach(r => {
      if (!r.sub_assembly_bom) return;
      (edges[r.parent] || (edges[r.parent] = [])).push(r.sub_assembly_bom);
    });
    subAssemblyEdges.value = edges;
    try {
      const mfgDefaults = await apiCall(
        "zoho_books_clone.manufacturing.doctype.manufacturing_settings.manufacturing_settings.get_manufacturing_defaults"
      );
      if (mfgDefaults && mfgDefaults.default_bom_type) mfgDefaultBomType.value = mfgDefaults.default_bom_type;
      if (mfgDefaults) mfgDefaultSubAssemblyRate.value = !!mfgDefaults.set_rate_of_sub_assembly_item_based_on_bom;
    } catch (e) { /* non-critical — keep the "Manufacturing" fallback */ }
  } catch (e) {
    toast("Error loading manufacturing data: " + e.message, "error");
  }
  await loadList();
  if (route.params.name) await loadBom();
  loading.value = false;
});

watch(() => route.params.name, async (name) => {
  if (!name) { bom.value = emptyBom(); return; }
  await loadBom();
});

async function loadBom() {
  if (isNew.value) {
    bom.value = emptyBom();
    activeTab.value = "components";
    return;
  }
  detailLoading.value = true;
  try {
    const data = await apiGet("BOM", route.params.name);
    bom.value = data;
    oldQty.value = data.quantity || 1;
    if (!bom.value.items) bom.value.items = [];
    if (!bom.value.operations) bom.value.operations = [];
    if (!bom.value.scrap_items) bom.value.scrap_items = [];
    activeTab.value = "components";
    refreshRmLandedCosts();
  } catch (e) {
    toast("Error loading BOM: " + e.message, "error");
    goBackToList();
  }
  detailLoading.value = false;
}

function onQtyChange() {
  const newQty = parseFloat(bom.value.quantity) || 0;
  if (newQty <= 0) { bom.value.quantity = 1; oldQty.value = 1; return; }
  const ratio = newQty / oldQty.value;
  (bom.value.items || []).forEach(rm => { rm.qty = (rm.qty || 0) * ratio; });
  (bom.value.scrap_items || []).forEach(sc => { sc.qty = (sc.qty || 0) * ratio; });
  // Packing BOMs keep their materials in packing_items (items is required to
  // stay empty for that bom_type — see BOM.validate_packing_bom) — without
  // rescaling this table too, changing Quantity on a Packing BOM silently
  // leaves every packing material's qty at its old, now-wrong value.
  (bom.value.packing_items || []).forEach(pi => { pi.qty = (pi.qty || 0) * ratio; });
  // Operation time must scale with quantity too — otherwise op_cost stays pinned
  // to the old quantity's time. Mirrors get_bom_breakdown() on the backend, which
  // scales planned_time_in_mins by the same qty ratio when previewing a Work Order.
  (bom.value.operations || []).forEach(op => { op.time_in_mins = (op.time_in_mins || 0) * ratio; });
  oldQty.value = newQty;
}

// Would picking `candidateBom` as a Sub-Assembly BOM on this row eventually loop
// back to the BOM currently being edited? Walks the known sub-assembly graph
// (built from submitted BOMs) forward from the candidate looking for our own name.
function wouldCreateCycle(candidateBom) {
  if (!candidateBom || !bom.value.name) return false;
  const target = bom.value.name;
  if (candidateBom === target) return true;
  const seen = new Set();
  const stack = [candidateBom];
  while (stack.length) {
    const cur = stack.pop();
    if (seen.has(cur)) continue;
    seen.add(cur);
    for (const next of (subAssemblyEdges.value[cur] || [])) {
      if (next === target) return true;
      if (!seen.has(next)) stack.push(next);
    }
  }
  return false;
}

function onRmItemChange(rm) {
  if (!rm.item_code) return;
  const item = stockItems.value.find(i => i.name === rm.item_code);
  if (item) { rm.rate = item.standard_rate || 0; rm.uom = item.stock_uom || "Nos"; rm.item_name = item.item_name; }
  refreshRmLandedCosts();
}

// Landed-cost visibility (Phase 8): rm.rate is a manually-entered/standard
// rate used for BOM cost estimation, which can drift from the live Bin
// valuation rate once a Landed Cost Voucher has capitalized freight/customs
// into that item+warehouse. This surfaces the current warehouse rate
// (base + landed split) as a hint next to Rate, read-only, so the client can
// see the true landed cost impact without this editable BOM figure silently
// changing underneath them.
const rmLanded = ref({}); // item_code -> { valuation_rate, base_rate, landed_rate, has_landed_cost, warehouse }
let rmLandedTimer = null;
function refreshRmLandedCosts() {
  clearTimeout(rmLandedTimer);
  rmLandedTimer = setTimeout(async () => {
    const rows = bom.value.bom_type === "Packing" ? bom.value.packing_items : bom.value.items;
    const pairs = [];
    for (const rm of (rows || [])) {
      if (!rm.item_code) continue;
      const item = stockItems.value.find(i => i.name === rm.item_code);
      const warehouse = item?.default_warehouse;
      if (warehouse) pairs.push({ item_code: rm.item_code, warehouse });
    }
    if (!pairs.length) return;
    try {
      const r = await apiCall(
        "zoho_books_clone.inventory.landed_cost_engine.get_landed_cost_breakdown",
        { pairs: JSON.stringify(pairs) }
      );
      const byItem = {};
      for (const p of pairs) {
        const info = (r || {})[`${p.item_code}::${p.warehouse}`];
        if (info) byItem[p.item_code] = { ...info, warehouse: p.warehouse };
      }
      rmLanded.value = byItem;
    } catch (e) { /* non-fatal — BOM rate stays user-editable regardless */ }
  }, 300);
}
function rmLandedInfo(itemCode) {
  return rmLanded.value[itemCode] || null;
}
function useLandedRate(rm) {
  const info = rmLandedInfo(rm.item_code);
  if (info) rm.rate = info.valuation_rate;
}
function onBulkItemChange() {
  if (!bom.value.bulk_item) return;
  const item = stockItems.value.find(i => i.name === bom.value.bulk_item);
  if (item && !bom.value.bulk_rate) bom.value.bulk_rate = item.standard_rate || 0;
}
function onWorkstationChange(op) {
  if (!op.workstation) return;
  const w = workstationsList.value.find(x => x.name === op.workstation);
  if (w) op.hour_rate = w.hour_rate || 0;
}
async function onRoutingChange() {
  if (!bom.value.routing) return;
  if ((bom.value.operations || []).length) {
    const ok = await confirm({
      title: "Replace Operations?",
      body: "Loading this Routing will replace the current Operations rows. Any manual edits will be lost. Continue?",
      okLabel: "Replace",
      okStyle: "danger",
    });
    if (!ok) return;
  }
  try {
    const rows = await apiCall("zoho_books_clone.manufacturing.doctype.routing.routing.get_routing_operations", { routing: bom.value.routing });
    if (rows && rows.length) {
      bom.value.operations = rows;
      toast(`${rows.length} operation(s) loaded from Routing "${bom.value.routing}"`);
    }
  } catch (e) {
    toast("Could not load Routing operations: " + (e.message || e), "error");
  }
}

function addMaterial() { bom.value.items.push({ item_code: "", uom: "Nos", qty: 1, rate: 0 }); }
function removeMaterial(idx) { bom.value.items.splice(idx, 1); }
function onPackingItemChange(pi) {
  if (!pi.item_code) return;
  const item = stockItems.value.find(i => i.name === pi.item_code);
  if (item) { pi.rate = item.standard_rate || 0; pi.uom = item.stock_uom || "Nos"; pi.item_name = item.item_name; }
}
function addPackingMaterial() { bom.value.packing_items.push({ item_code: "", uom: "Nos", qty: 1, rate: 0 }); }
function removePackingMaterial(idx) { bom.value.packing_items.splice(idx, 1); }
function addOp() { bom.value.operations.push({ operation: "", workstation: "", time_in_mins: 60, hour_rate: 0 }); }
function removeOp(idx) { bom.value.operations.splice(idx, 1); }
function addScrap() { bom.value.scrap_items.push({ item_code: "", qty: 1, rate: 0 }); }
function removeScrap(idx) { bom.value.scrap_items.splice(idx, 1); }

const rm_cost = computed(() => {
  const sourceItems = bom.value.bom_type === "Packing" ? bom.value.packing_items : bom.value.items;
  let total = (sourceItems || []).reduce((s, rm) => s + (parseFloat(rm.qty) || 0) * (parseFloat(rm.rate) || 0), 0);
  if (bom.value.bom_type === "Packing" && bom.value.bulk_item && parseFloat(bom.value.bulk_qty_per_unit) > 0) {
    total += (parseFloat(bom.value.bulk_qty_per_unit) || 0) * (parseFloat(bom.value.quantity) || 1) * (parseFloat(bom.value.bulk_rate) || 0);
  }
  return total;
});
const op_cost = computed(() => (bom.value.operations || []).reduce((s, op) => s + ((parseFloat(op.time_in_mins) || 0) / 60) * (parseFloat(op.hour_rate) || 0), 0));
const scrap_value = computed(() => (bom.value.scrap_items || []).reduce((s, sc) => s + (parseFloat(sc.qty) || 0) * (parseFloat(sc.rate) || 0), 0));
const total_cost = computed(() => rm_cost.value + op_cost.value - scrap_value.value);

async function save() {
  if (!bom.value.item) return toast("Please select a Production Item", "error");
  if (!bom.value.quantity || bom.value.quantity <= 0) return toast("Quantity must be greater than 0", "error");
  const pl = parseFloat(bom.value.process_loss) || 0;
  if (pl < 0 || pl > 100) return toast("Process Loss must be between 0 and 100%", "error");
  let totalScrapQty = 0;
  (bom.value.scrap_items || []).forEach(sc => totalScrapQty += (parseFloat(sc.qty) || 0));
  if (totalScrapQty > bom.value.quantity) return toast("Total Scrap quantity cannot exceed Production Quantity", "error");

  if (bom.value.bom_type === "Packing") {
    if (!bom.value.bulk_item) return toast("Packing BOM requires a Bulk Item to consume from", "error");
    if (!bom.value.bulk_qty_per_unit || bom.value.bulk_qty_per_unit <= 0) return toast("Bulk Qty Consumed per Packed Unit must be greater than 0", "error");
    if (bom.value.bulk_item === bom.value.item) return toast("Bulk Item cannot be the same as the Production Item being packed", "error");
    if (!bom.value.packing_items || !bom.value.packing_items.length) return toast("Add at least one Packing Material row", "error");
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
    loadList();
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
    loadList();
  } catch (e) { toast(e.message, "error"); }
  submitting.value = false;
}

async function newVersion() {
  if (!bom.value.name) return;
  if (!(await confirm({
    title: "Create new version?",
    body: bom.value.docstatus === 1
      ? "This will cancel the current active revision and open a new draft version for editing."
      : "This will open a new draft version for editing.",
    okLabel: "New Version",
  }))) return;
  submitting.value = true;
  try {
    let target = bom.value;
    if (bom.value.docstatus === 1) {
      target = await apiCancel("BOM", bom.value.name);
    }
    const doc = await apiAmend("BOM", target.name);
    toast(`New revision ${doc.name} created — v${doc.bom_version}`);
    router.push(`/manufacturing/bom/${doc.name}`);
    loadList();
  } catch (e) { toast(e.message, "error"); }
  submitting.value = false;
}

async function cancelBom() {
  if (!bom.value.name) return;
  if (!(await confirm({
    title: "Cancel BOM?",
    body: `This will discontinue ${bom.value.name} without creating a replacement version. It will no longer be usable in new Work Orders or Sub-Assembly links. This cannot be undone from here.`,
    okLabel: "Cancel BOM",
    okStyle: "danger",
  }))) return;
  cancelling.value = true;
  try {
    const doc = await apiCancel("BOM", bom.value.name);
    bom.value = doc;
    toast("BOM cancelled");
    loadList();
  } catch (e) { toast(e.message, "error"); }
  cancelling.value = false;
}

async function loadBomTree() {
  if (!bom.value.name || bom.value.docstatus !== 1) return;
  treeLoading.value = true;
  treeNodes.value = [];
  try {
    const nodes = await apiCall("zoho_books_clone.manufacturing.bom_engine.get_bom_tree", { bom: bom.value.name, qty: bom.value.quantity || 1 });
    treeNodes.value = nodes || [];
    if (!treeNodes.value.length) toast("No materials found in BOM", "error");
  } catch (e) { toast("Failed to build BOM tree: " + e.message, "error"); }
  treeLoading.value = false;
}

async function runCompare() {
  if (!bom.value.name || !compareBom2.value) return;
  compareLoading.value = true;
  compareResult.value = null;
  try {
    compareResult.value = await apiCall("zoho_books_clone.manufacturing.bom_engine.compare_boms", { bom1: bom.value.name, bom2: compareBom2.value });
  } catch (e) { toast("Comparison failed: " + e.message, "error"); }
  compareLoading.value = false;
}

// ── UTIL ─────────────────────────────────────────────────────
function INR(n) {
  if (n == null || isNaN(n)) return "₹0.00";
  return "₹" + Number(n).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

const ICONS = {
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
};
function icon(name, size) {
  return (ICONS[name] || "").replace("<svg ", `<svg width="${size}" height="${size}" `);
}
</script>

<style scoped>
.bomx-page {
  --bx-bg:#F3F4F6; --bx-surface:#FFFFFF; --bx-surf2:#F8F9FC; --bx-border:#E2E8F0;
  --bx-text:#1A1D23; --bx-muted:#868E96;
  --bx-green:#2F9E44; --bx-greenS:#EBFBEE;
  --bx-red:#C92A2A; --bx-redS:#FFF5F5;
  --bx-amber:#E67700; --bx-amberS:#FFF3BF;
  --bx-blue:#1971C2; --bx-blueS:#E7F5FF;
  --bx-violet:#7048E8; --bx-violetS:#F3F0FF;
  --bx-mfg:#1a6ef7; --bx-mfgL:#2f74f5; --bx-mfgS:#EAF1FF; --bx-mfgB:#1e3a5f;
  --bx-radius:10px; --bx-rsm:6px;
  padding: 16px;
}
.bomx-two-col { display:grid; grid-template-columns: 340px 1fr; gap:16px; align-items:start; }
@media (max-width:1000px) { .bomx-two-col { grid-template-columns: 1fr; } }

/* ── List panel ── */
.bomx-list-panel { background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; display:flex; flex-direction:column; }
.bomx-panel-hdr { padding:12px 14px; border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); display:flex; align-items:center; justify-content:space-between; gap:8px; }
.bomx-panel-title { font-size:13px; font-weight:700; color:var(--bx-text); }
.bomx-count { font-size:12px; font-weight:400; color:var(--bx-muted); }
.bomx-status-filter { margin:8px 12px 0; width:calc(100% - 24px); font-size:12px; padding:6px 10px; }
.bomx-search { width:100%; border:none; outline:none; font-size:13px; padding:10px 14px; margin-top:8px; border-bottom:1px solid var(--bx-border); background:#fff; color:var(--bx-text); }
.bomx-search::placeholder { color:var(--bx-muted); }
.bomx-list { overflow-y:auto; max-height: calc(100vh - 230px); }
.bomx-list-empty { text-align:center; padding:32px; color:var(--bx-muted); font-size:13px; }
.bomx-item { padding:12px 14px; border-bottom:1px solid #F1F3F5; cursor:pointer; transition:background .12s; display:flex; flex-direction:column; gap:4px; }
.bomx-item:hover { background:#FAFBFF; }
.bomx-item.active { background:var(--bx-mfgS); border-left:3px solid var(--bx-mfg); }
.bomx-item-name { font-size:13.5px; font-weight:600; color:var(--bx-text); }
.bomx-item-meta { display:flex; align-items:center; gap:6px; font-size:12px; color:var(--bx-muted); }
.bomx-item-right { display:flex; align-items:center; gap:6px; margin-top:2px; }
.bomx-default-tag { font-size:10px; font-weight:700; background:#E8EAF6; color:#1A237E; padding:1px 6px; border-radius:10px; margin-left:2px; }

/* ── Badges ── */
.bomx-badge { display:inline-flex; align-items:center; padding:2px 8px; border-radius:20px; font-size:11px; font-weight:600; white-space:nowrap; }
.badge-active { background:var(--bx-greenS); color:var(--bx-green); }
.badge-draft { background:var(--bx-amberS); color:var(--bx-amber); }
.badge-obsolete { background:#F1F3F5; color:var(--bx-muted); }
.badge-added { background:var(--bx-greenS); color:var(--bx-green); }
.badge-removed { background:var(--bx-redS); color:var(--bx-red); }
.badge-changed { background:var(--bx-amberS); color:var(--bx-amber); }
.badge-unchanged { background:#F1F3F5; color:var(--bx-muted); }

/* ── Detail panel ── */
.bomx-detail-panel { background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; display:flex; flex-direction:column; min-height: calc(100vh - 100px); }
.bomx-empty-state { text-align:center; padding:60px 20px; color:var(--bx-muted); }
.bomx-empty-icon { font-size:48px; margin-bottom:14px; }
.bomx-empty-title { font-size:16px; font-weight:700; color:var(--bx-text); margin-bottom:6px; }
.bomx-empty-sub { font-size:13px; line-height:1.6; max-width:280px; margin:0 auto 20px; }

.bomx-detail-hdr { padding:18px 22px; background:linear-gradient(135deg, var(--bx-mfgB), var(--bx-mfg)); }
.bomx-detail-title { font-size:18px; font-weight:700; color:#fff; margin-bottom:4px; }
.bomx-detail-meta { font-size:12.5px; color:rgba(255,255,255,.75); display:flex; align-items:center; gap:8px; flex-wrap:wrap; }

.bomx-version-chips { display:flex; gap:8px; flex-wrap:wrap; margin-top:12px; }
.bomx-vchip {
  display:inline-flex; align-items:center; gap:5px;
  padding:5px 12px; border-radius:999px; font-size:12.5px; font-weight:600;
  background:rgba(255,255,255,.92); color:var(--bx-mfgB);
  border:1px solid rgba(255,255,255,.4); cursor:pointer; line-height:1.2;
}
.bomx-vchip:hover:not(.active) { background:#fff; }
.bomx-vchip.active {
  background:#fff; color:var(--bx-mfg);
  border-color:var(--bx-mfg); font-weight:700;
}
.bomx-vchip-tick { color:#2F9E44; font-weight:700; }

.bomx-hdr-fields { display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:12px; padding:16px 22px; border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); }
@media (max-width:760px) { .bomx-hdr-fields { grid-template-columns:1fr 1fr; } }
.bomx-hf-label { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); margin-bottom:4px; }
.bomx-toggle-row { display:flex; gap:20px; padding:10px 22px 14px; flex-wrap:wrap; background:var(--bx-surf2); border-bottom:1px solid var(--bx-border); }
.bomx-toggle { display:flex; align-items:center; gap:6px; font-size:12.5px; font-weight:600; color:var(--bx-text); }

.bomx-tabs { display:flex; border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); padding:0 22px; overflow-x:auto;overflow-y:hidden; }
.bomx-tab { padding:10px 16px; font-size:13px; font-weight:600; cursor:pointer; border:none; background:none; color:var(--bx-muted); border-bottom:2px solid transparent; margin-bottom:-1px; white-space:nowrap; }
.bomx-tab.active { color:var(--bx-mfg); border-bottom-color:var(--bx-mfg); }
.bomx-body { padding:20px 22px; overflow-y:auto; flex:1; }

.bomx-notice { background:var(--bx-amberS); border:1px solid rgba(230,119,0,.2); border-radius:8px; padding:10px 14px; margin-bottom:14px; font-size:13px; color:var(--bx-amber); display:flex; align-items:center; gap:8px; }

/* ── Cost summary ── */
.bomx-cost-summary { background:var(--bx-mfgS); border:1px solid rgba(180,83,9,.15); border-radius:var(--bx-radius); padding:16px 18px; margin-bottom:18px; }
.bomx-cost-title { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--bx-mfg); margin-bottom:12px; display:flex; align-items:center; gap:6px; }
.bomx-cost-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; }
.bomx-cost-cell { background:#fff; border:1px solid rgba(180,83,9,.12); border-radius:var(--bx-rsm); padding:10px 12px; }
.bomx-cost-cell-total { background:var(--bx-mfgS); border-color:rgba(180,83,9,.2); }
.bomx-cost-lbl { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-mfg); margin-bottom:3px; }
.bomx-cost-val { font-size:17px; font-weight:700; color:var(--bx-mfgB); }

/* ── Tree rows (materials / ops / scrap) ── */
.bomx-tree-col-hdr { display:flex; align-items:center; padding:7px 10px 7px 12px; font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--bx-muted); border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); margin-bottom:4px; gap:8px; }
.bomx-tree { display:flex; flex-direction:column; gap:2px; }
.bomx-tree-empty { text-align:center; padding:20px; color:var(--bx-muted); font-size:13px; }
.bomx-tree-row { display:flex; align-items:center; gap:8px; padding:8px 10px; border-radius:var(--bx-rsm); transition:background .1s; }
.bomx-tree-row:hover { background:#F5F6FF; }
.bomx-tree-dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
.bomx-tree-icon { font-size:14px; flex-shrink:0; }
.bomx-tree-cost {font-size:13px; font-weight:700; min-width:90px; text-align:right; }
.bomx-tree-actions { display:flex; gap:3px; }
.bomx-fi-inline { width:100%; }
.bomx-tree-qty-inp { width:60px; text-align:right; }
.bomx-tree-uom-inp { width:70px; }
.bomx-tree-rate-inp { width:80px; text-align:right; }
.bomx-tree-sa-inp { width:150px; font-size:12px; }
.bomx-add-row { display:flex; align-items:center; gap:8px; padding:8px 12px; color:var(--bx-mfg); cursor:pointer; font-size:13px; font-weight:600; border-radius:var(--bx-rsm); margin-top:4px; }
.bomx-add-row:hover { background:var(--bx-mfgS); }

/* ── Raw material cards ── */
.bomx-rm-cards { display:flex; flex-direction:column; gap:10px; }
.bomx-rm-card { background:#fff; border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; box-shadow:0 1px 3px rgba(16,24,40,.04); }
.bomx-rm-card-hdr { display:flex; align-items:center; gap:10px; padding:10px 14px; background:var(--bx-mfgS); border-bottom:1px solid var(--bx-border); }
.bomx-rm-card-title { flex:1; min-width:0; font-weight:600; }
.bomx-rm-card-amt { display:flex; flex-direction:column; align-items:flex-end; flex-shrink:0; gap:1px; }
.bomx-rm-card-amt-lbl { font-size:9.5px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; color:var(--bx-muted); }
.bomx-rm-card-rm { flex-shrink:0; }
.bomx-rm-card-body { display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:10px; padding:12px 14px; }
.bomx-rm-field { display:flex; flex-direction:column; gap:4px; min-width:0; }
.bomx-landed-hint { font-size:10.5px; color:var(--bx-amber); background:var(--bx-amberS); border-radius:5px; padding:3px 6px; display:flex; align-items:center; gap:6px; flex-wrap:wrap; cursor:help; }
.bomx-landed-hint a { color:var(--bx-mfg); font-weight:700; text-decoration:underline; cursor:pointer; }
.bomx-rm-field label { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); }
.bomx-rm-field .bomx-fi { width:100%; }
.bomx-rm-field-wide { grid-column:span 1; }
@media (max-width:640px) {
  .bomx-rm-card-body { grid-template-columns:1fr 1fr; }
  .bomx-rm-field-wide { grid-column:1 / -1; }
}

/* ── Cost breakdown table ── */
.bomx-cost-table { width:100%; border-collapse:collapse; font-size:13px; border:1px solid var(--bx-border); border-radius:var(--bx-rsm); overflow:hidden; }
.bomx-cost-table th { padding:8px 12px; text-align:left; font-size:10px; text-transform:uppercase; letter-spacing:.06em; color:var(--bx-muted); font-weight:700; background:var(--bx-surf2); }
.bomx-cost-table td { padding:8px 12px; border-top:1px solid #F1F3F5; }
.bomx-cost-table tfoot td { background:var(--bx-mfgS); font-weight:700; }

.bomx-section-lbl { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--bx-muted); margin-bottom:8px; }
.bomx-lo-cell { background:var(--bx-surf2); border:1px solid var(--bx-border); border-radius:var(--bx-rsm); padding:12px 16px; }
.bomx-field-block { margin-bottom:4px; }
.bomx-field-hint { font-size:12px; color:var(--bx-muted); margin-top:5px; }
.bomx-field-hint-danger { color:var(--bx-red); font-weight:600; display:flex; align-items:center; gap:4px; }
.bomx-link { color:var(--bx-mfg); font-weight:600; cursor:pointer; }
.bomx-link:hover { text-decoration:underline; }

.bomx-footer { padding:12px 22px; border-top:1px solid var(--bx-border); background:var(--bx-surf2); display:flex; justify-content:space-between; align-items:center; gap:8px; }

/* ── Buttons / inputs ── */
.bomx-fi { border:1px solid #CDD5E0; border-radius:var(--bx-rsm); padding:7px 9px; font-size:13px; color:var(--bx-text); background:#fff; outline:none; }
.bomx-fi:focus { border-color:var(--bx-mfg); box-shadow:0 0 0 3px rgba(180,83,9,.1); }
.bomx-fi:disabled { background:#F8F9FC; color:var(--bx-muted); }

select.bomx-fi {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  padding-right: 30px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%239ca3af' stroke-width='2.5'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
}
select.bomx-fi:disabled { background-image: none; padding-right: 9px; }
.bomx-btn { display:inline-flex; align-items:center; gap:6px; padding:8px 16px; border-radius:var(--bx-rsm); font-size:13px; font-weight:600; cursor:pointer; border:1px solid transparent; line-height:1; white-space:nowrap; }
.bomx-btn:disabled { opacity:.6; cursor:not-allowed; }
.bomx-btn-sm { padding:6px 10px; font-size:12px; }
.bomx-btn-mfg { background:var(--bx-mfg); color:#fff; }
.bomx-btn-mfg:hover:not(:disabled) { background:var(--bx-mfgB); }
.bomx-btn-light { background:rgba(255,255,255,.92); color:var(--bx-mfgB); }
.bomx-btn-light:hover:not(:disabled) { background:#fff; }
.bomx-btn-ghost-inv { background:rgba(255,255,255,.15); color:#fff; border-color:rgba(255,255,255,.3); }
.bomx-btn-ghost-inv:hover:not(:disabled) { background:rgba(255,255,255,.25); }
.bomx-btn-icon { background:none; border:1px solid var(--bx-border); border-radius:5px; cursor:pointer; padding:4px 6px; display:inline-flex; color:var(--bx-muted); }
.bomx-btn-icon:hover { border-color:var(--bx-mfg); color:var(--bx-mfg); background:var(--bx-mfgS); }
.bomx-btn-icon.danger { color:var(--bx-red); }
.bomx-btn-icon.danger:hover { background:var(--bx-redS); border-color:var(--bx-red); }

.shimmer { background:linear-gradient(90deg,#f1f3f5 25%,#e9ecef 37%,#f1f3f5 63%); background-size:400% 100%; animation:shimmer 1.4s ease infinite; }
@keyframes shimmer { 0%{background-position:100% 50%} 100%{background-position:0 50%} }

/* ── Header flex (was inline styles — now real classes so media queries can win) ── */
.bomx-hdr-flex { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; }
.bomx-hdr-info { min-width:0; }
.bomx-hdr-actions { display:flex; gap:6px; flex-shrink:0; flex-wrap:wrap; justify-content:flex-end; }
.bomx-tree-selects { flex:1; min-width:0; display:flex; gap:6px; }

/* ── Mobile responsive ── */
@media (max-width:768px) {
  .bomx-page { padding:10px; }
  .bomx-two-col { gap:12px; }
  .bomx-list { max-height:280px; }
  .bomx-detail-panel { min-height:auto; }

  .bomx-detail-hdr { padding:14px 16px; }
  .bomx-hdr-flex { flex-direction:column; align-items:stretch; }
  .bomx-hdr-actions { justify-content:flex-start; }
  .bomx-detail-title { font-size:16px; }

  .bomx-hdr-fields { grid-template-columns:1fr 1fr; padding:12px 16px; gap:10px; }
  .bomx-toggle-row { padding:10px 16px 12px; gap:12px; }
  .bomx-tabs { padding:0 16px; }
  .bomx-body { padding:14px 16px; }

  .bomx-cost-grid { grid-template-columns:1fr 1fr; }
  .bomx-rm-card-body { grid-template-columns:1fr 1fr; padding:10px 12px; }

  /* Operations / scrap tree rows: stop them overflowing horizontally */
  .bomx-tree-col-hdr { display:none; }
  .bomx-tree-row { flex-wrap:wrap; row-gap:6px; }
  .bomx-tree-selects { flex-basis:100%; order:1; }
  .bomx-tree-rate-inp, .bomx-tree-qty-inp { flex:1; width:auto; min-width:0; order:2; }
  .bomx-tree-cost { order:3; min-width:auto; margin-left:auto; }
  .bomx-tree-actions { order:4; }
  .bomx-tree-sa-inp { width:100%; }

  .bomx-cost-table { font-size:12px; display:block; overflow-x:auto; white-space:nowrap; }

  .bomx-footer { flex-direction:column; align-items:stretch; gap:10px; }
  .bomx-btn { padding:8px 12px; }
}

@media (max-width:420px) {
  .bomx-hdr-fields { grid-template-columns:1fr; }
  .bomx-cost-grid { grid-template-columns:1fr; }
  .bomx-rm-card-body { grid-template-columns:1fr; }
}
</style>