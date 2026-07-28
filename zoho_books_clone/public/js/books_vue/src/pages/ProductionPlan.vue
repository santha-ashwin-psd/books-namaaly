<template>
<div class="bomx-page">

  <!-- ══════════ FULL-WIDTH LIST VIEW ══════════ -->
  <div v-if="!selectedName" class="bomx-list-view">
    <div class="bomx-list-toolbar">
      <span class="bomx-panel-title">📅 All Production Plans <span class="bomx-count">({{ sorted.length }})</span></span>
      <button class="bomx-btn bomx-btn-mfg" @click="openAdd"><span v-html="icon('plus',13)"></span> New Production Plan</button>
    </div>

    <div class="bomx-pp-sumstrip">
      <div class="bomx-pp-sc">
        <div class="bomx-pp-sc-bar" style="background:var(--bx-mfg)"></div>
        <div class="bomx-pp-sc-val">{{ countTotal }}</div>
        <div class="bomx-pp-sc-lbl">Total</div>
      </div>
      <div class="bomx-pp-sc">
        <div class="bomx-pp-sc-bar" style="background:var(--bx-muted)"></div>
        <div class="bomx-pp-sc-val" style="color:var(--bx-muted)">{{ countDraft }}</div>
        <div class="bomx-pp-sc-lbl">Draft</div>
      </div>
      <div class="bomx-pp-sc">
        <div class="bomx-pp-sc-bar" style="background:var(--bx-blue)"></div>
        <div class="bomx-pp-sc-val" style="color:var(--bx-blue)">{{ countSubmitted }}</div>
        <div class="bomx-pp-sc-lbl">Submitted</div>
      </div>
      <div class="bomx-pp-sc">
        <div class="bomx-pp-sc-bar" style="background:var(--bx-green)"></div>
        <div class="bomx-pp-sc-val" style="color:var(--bx-green)">{{ countWOCreated }}</div>
        <div class="bomx-pp-sc-lbl">WOs Created</div>
      </div>
      <div class="bomx-pp-sc">
        <div class="bomx-pp-sc-bar" style="background:var(--bx-green)"></div>
        <div class="bomx-pp-sc-val" style="color:var(--bx-green)">{{ countCompleted }}</div>
        <div class="bomx-pp-sc-lbl">Completed</div>
      </div>
      <div class="bomx-pp-sc">
        <div class="bomx-pp-sc-bar" style="background:var(--bx-red)"></div>
        <div class="bomx-pp-sc-val" style="color:var(--bx-red)">{{ countCancelled }}</div>
        <div class="bomx-pp-sc-lbl">Cancelled</div>
      </div>
    </div>

    <div class="bomx-list-filters">
      <select class="bomx-fi bomx-status-filter" v-model="filterStatus">
        <option value="">All Status</option>
        <option v-for="s in statusOptions" :key="s" :value="s">{{ s }}</option>
      </select>
      <input class="bomx-fi bomx-search-full" v-model="search" type="text" placeholder="Search by Plan ID, company, status, or remarks…"/>
    </div>

    <div class="bomx-pp-rows">
      <template v-if="loading">
        <div v-for="n in 4" :key="n" class="bomx-pp-row"><div class="shimmer" style="height:58px;border-radius:8px"></div></div>
      </template>
      <div v-else-if="!sorted.length" class="bomx-list-empty">No Production Plans found</div>
      <div v-else v-for="row in sorted" :key="row.name" class="bomx-pp-row" @click="selectPlan(row.name)">
        <div class="bomx-pp-row-top">
          <div class="bomx-item-name">{{ row.name }}</div>
          <span class="bomx-badge" :class="statusClass(row)">{{ row.status }}</span>
        </div>
        <div class="bomx-pp-row-foot">
          <div class="bomx-pp-row-meta">
            <span class="mono">{{ fmtDate(row.posting_date) }}</span>
            <span v-if="row.company">• {{ row.company }}</span>
          </div>
          <button class="bomx-btn bomx-btn-sm bomx-btn-light" style="color:var(--bx-mfgB);border:1px solid var(--bx-mfg)" @click.stop="selectPlan(row.name)">
            Open <span v-html="icon('open',11)"></span>
          </button>
          <button v-if="row.docstatus === 0" class="bomx-btn-icon danger" @click.stop="deletePP(row.name, $event)" title="Delete">
            <span v-html="icon('trash',13)"></span>
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- ══════════ FULL-WIDTH DETAIL VIEW ══════════ -->
  <div v-else class="bomx-detail-panel">
        <div v-if="loading" class="bomx-empty-state"><div class="shimmer" style="height:200px;border-radius:10px"></div></div>

        <template v-else>
          <!-- Back -->
          <button class="bomx-back-btn" @click="goBackToList" :disabled="saving || submitting" title="Back to list">
            <span v-html="icon('chevronLeft',16)"></span>
          </button>

          <!-- Pipeline -->
          <div class="bomx-pp-pipeline" v-if="!isNew">
            <template v-for="(step, i) in pipelineSteps" :key="step.key">
              <div class="bomx-pp-pipe-step">
                <div class="bomx-pp-pipe-dot" :class="'st-' + pipelineStepState(step.key)">
                  <span v-if="pipelineStepState(step.key)==='done' && step.key!=='Cancelled'" v-html="icon('check',14)"></span>
                  <span v-else-if="step.key==='Cancelled'" v-html="icon('x',14)"></span>
                  <span v-else>{{ i + 1 }}</span>
                </div>
                <div class="bomx-pp-pipe-label" :class="'st-' + pipelineStepState(step.key)">{{ step.label }}</div>
              </div>
              <div v-if="i < pipelineSteps.length - 1" class="bomx-pp-pipe-line" :class="{ done: pipelineStepState(pipelineSteps[i+1].key) === 'done' }"></div>
            </template>
          </div>

          <!-- Header -->
          <div class="bomx-detail-hdr">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap">
              <div style="min-width:0">
                <div class="bomx-detail-title">{{ isNew ? 'New Production Plan' : pp.name }}</div>
                <div class="bomx-detail-meta">
                  <span v-if="!isNew">{{ fmtDate(pp.posting_date) }}</span>
                  <span v-if="!isNew">•</span>
                  <span class="bomx-badge" :class="statusClass(pp)" style="font-size:11px" v-if="!isNew">{{ pp.status }}</span>
                </div>
              </div>
              <div style="display:flex;gap:6px;flex-shrink:0;flex-wrap:wrap;justify-content:flex-end">
                <button class="bomx-btn bomx-btn-ghost-inv" @click="goBackToList" :disabled="saving || submitting">Back</button>
                <button v-if="!isNew && pp.docstatus===2" class="bomx-btn bomx-btn-light" @click="amendPP" :disabled="submitting">
                  {{ submitting ? 'Amending…' : 'Amend' }}
                </button>
                <button v-if="!isNew && pp.docstatus===1" class="bomx-btn" style="background:var(--bx-redS);color:var(--bx-red)" @click="cancelPP" :disabled="submitting">
                  {{ submitting ? 'Cancelling…' : 'Cancel Plan' }}
                </button>
                <button v-if="!isNew && pp.docstatus===0" class="bomx-btn" style="background:var(--bx-redS);color:var(--bx-red)" @click="deletePP(pp.name)">
                  Delete
                </button>
                <button v-if="!isNew && pp.docstatus===0" class="bomx-btn bomx-btn-light" @click="submitPP" :disabled="submitting || saving">
                  {{ submitting ? 'Submitting…' : 'Submit' }}
                </button>
                <button v-if="!readOnly" class="bomx-btn bomx-btn-light" @click="save" :disabled="saving || loading">
                  {{ saving ? 'Saving…' : (isNew ? 'Save Production Plan' : 'Save Changes') }}
                </button>
                <button v-if="!isNew && pp.docstatus===1" class="bomx-btn bomx-btn-light" @click="saveRemarks" :disabled="saving">
                  {{ saving ? 'Saving…' : 'Save Remarks' }}
                </button>
              </div>
            </div>
          </div>

          <div class="bomx-body">

            <!-- ── CARD: Plan Details ── -->
            <div class="bomx-card">
              <div class="bomx-card-hdr">
                <span class="bomx-card-hdr-title"><span v-html="icon('clipboard',14)"></span> Plan Details</span>
              </div>
              <div class="bomx-card-body">
                <div class="bomx-fg bomx-fg-2" style="margin-bottom:14px">
                  <div>
                    <label class="bomx-fl">Posting Date</label>
                    <input class="bomx-fi" type="date" v-model="pp.posting_date" :disabled="readOnly"/>
                  </div>
                  <div>
                    <label class="bomx-fl">Remarks</label>
                    <input class="bomx-fi" type="text" v-model="pp.remarks" :disabled="pp.docstatus === 2" placeholder="Notes on this plan…"/>
                  </div>
                </div>
                <template v-if="pp.amended_from">
                  <div class="bomx-field-hint" style="margin-bottom:14px">Amended from <span class="bomx-link" @click="router.push(`/manufacturing/production-plan/${pp.amended_from}`)">{{ pp.amended_from }}</span></div>
                </template>
                <div class="bomx-fg bomx-fg-4">
                  <div>
                    <label class="bomx-fl">Source Warehouse (Raw Materials) <span style="color:var(--bx-red)">*</span></label>
                    <div class="bomx-fi-w"><select class="bomx-fi" v-model="pp.default_source_warehouse" :disabled="readOnly">
                      <option value="">— Select —</option>
                      <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
                    </select></div>
                  </div>
                  <div>
                    <label class="bomx-fl">Work-in-Progress Warehouse</label>
                    <div class="bomx-fi-w"><select class="bomx-fi" v-model="pp.default_wip_warehouse" :disabled="readOnly">
                      <option value="">— Select —</option>
                      <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
                    </select></div>
                  </div>
                  <div>
                    <label class="bomx-fl">Finished Goods Warehouse <span style="color:var(--bx-red)">*</span></label>
                    <div class="bomx-fi-w"><select class="bomx-fi" v-model="pp.default_fg_warehouse" :disabled="readOnly">
                      <option value="">— Select —</option>
                      <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
                    </select></div>
                  </div>
                  <div>
                    <label class="bomx-fl">Scrap / By-Product Warehouse</label>
                    <div class="bomx-fi-w"><select class="bomx-fi" v-model="pp.default_scrap_warehouse" :disabled="readOnly">
                      <option value="">— Defaults to FG Warehouse —</option>
                      <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
                    </select></div>
                  </div>
                </div>
              </div>
            </div>

            <!-- ── CARD: Source — Sales Orders ── -->
            <div class="bomx-card">
              <div class="bomx-card-hdr">
                <span class="bomx-card-hdr-title"><span v-html="icon('fileText',14)"></span> Source — Sales Orders</span>
                <button v-if="!readOnly" class="bomx-btn bomx-btn-ghost bomx-btn-sm" @click="openSOPicker">
                  <span v-html="icon('plus',12)"></span> Add Sales Orders
                </button>
              </div>
              <div v-if="!pp.sales_orders || !pp.sales_orders.length" class="bomx-tree-empty" style="padding:28px">
                Click <b>Add Sales Orders</b> to pull demand from open Sales Orders, or add items manually below.
              </div>
              <template v-else>
                <div class="bomx-tbl-wrap">
                  <table class="bomx-so-tbl">
                    <thead>
                      <tr>
                        <th>SO Number</th>
                        <th>Customer</th>
                        <th>Status</th>
                        <th>Delivery Date</th>
                        <th class="right">Grand Total</th>
                        <th v-if="!readOnly" style="width:36px"></th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(so, idx) in pp.sales_orders" :key="idx">
                        <td class="mono" style="font-weight:600">
                          <span class="bomx-link" @click="router.push(`/sales/sales-order/${so.sales_order}`)">{{ so.sales_order }}</span>
                        </td>
                        <td>{{ so.customer || '—' }}</td>
                        <td><span class="bomx-badge" :class="soStatusClass(so.status)">{{ so.status || '—' }}</span></td>
                        <td class="mono">{{ fmtDate(so.delivery_date) }}</td>
                        <td class="right mono">{{ so.grand_total ? fmt(so.grand_total) : '—' }}</td>
                        <td v-if="!readOnly">
                          <button class="bomx-btn-icon danger" @click="removeSalesOrder(idx)" title="Remove">
                            <span v-html="icon('trash',13)"></span>
                          </button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-if="!readOnly" class="bomx-card-footer">
                  <span class="bomx-field-hint" style="margin:0">Pulls pending qty (qty − delivered) per item across the Sales Orders above.</span>
                  <button class="bomx-btn bomx-btn-sm bomx-btn-mfg" @click="pullItemsFromSalesOrders" :disabled="itemsLoading || !pp.sales_orders || !pp.sales_orders.length">
                    {{ itemsLoading ? 'Pulling…' : 'Pull / Refresh Items' }}
                  </button>
                </div>
              </template>
            </div>

            <!-- ── CARD: Items to Produce ── -->
            <div class="bomx-card">
              <div class="bomx-card-hdr">
                <span class="bomx-card-hdr-title"><span v-html="icon('settings',14)"></span> Items to Produce</span>
                <button v-if="!readOnly" class="bomx-btn bomx-btn-ghost bomx-btn-sm" @click="addPOItem">
                  <span v-html="icon('plus',12)"></span> Add Row
                </button>
              </div>
              <div v-if="!pp.po_items || !pp.po_items.length" class="bomx-tree-empty" style="padding:28px">No items yet. Pull from Sales Orders above, or add a row manually.</div>
              <template v-else>
                <div class="bomx-tbl-wrap">
                  <table class="bomx-item-tbl">
                    <thead>
                      <tr>
                        <th>Item</th>
                        <th>BOM</th>
                        <th class="right" style="width:70px">Planned Qty</th>
                        <th>UOM</th>
                        <th>FG Warehouse</th>
                        <th class="right">WO Created Qty</th>
                        <th v-if="!readOnly" style="width:36px"></th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(row, idx) in pp.po_items" :key="idx">
                        <td style="min-width:150px">
                          <select class="bomx-fi" v-model="row.item_code" @change="onPOItemChange(row)" :disabled="readOnly">
                            <option value="">— Select —</option>
                            <option v-for="i in stockItems" :key="i.name" :value="i.name">{{ i.item_name || i.name }}</option>
                          </select>
                        </td>
                        <td style="min-width:130px">
                          <select class="bomx-fi" v-model="row.bom_no" :disabled="readOnly || !row.item_code">
                            <option value="">{{ row.item_code ? '— Select Submitted BOM —' : '— Select an Item first —' }}</option>
                            <option v-for="b in bomsFor(row.item_code)" :key="b.name" :value="b.name">{{ b.name }}</option>
                          </select>
                        </td>
                        <td class="right" style="width:70px;min-width:70px;max-width:70px">
                          <input class="bomx-fi bomx-fi-mono" style="text-align:right" type="number" v-model="row.planned_qty" min="0.01" step="any" :disabled="readOnly"/>
                        </td>
                        <td class="mono" style="color:var(--bx-muted)">{{ row.stock_uom || '—' }}</td>
                        <td style="min-width:130px">
                          <select class="bomx-fi" v-model="row.warehouse" :disabled="readOnly">
                            <option value="">— Use Default —</option>
                            <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
                          </select>
                        </td>
                        <td class="right mono" style="color:var(--bx-muted)">{{ flt(row.work_order_created_qty) ? fmt(row.work_order_created_qty) : '—' }}</td>
                        <td v-if="!readOnly">
                          <button class="bomx-btn-icon danger" @click="pp.po_items.splice(idx,1)" title="Remove">
                            <span v-html="icon('trash',13)"></span>
                          </button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div class="bomx-card-footer">
                  <span>{{ pp.po_items.length }} item{{ pp.po_items.length===1?'':'s' }} planned</span>
                  <span class="mono">Total: {{ fmt(totalPlannedQty) }} planned<template v-if="totalPendingWOQty > 0.0001"> · {{ fmt(totalPendingWOQty) }} pending WO</template></span>
                </div>
              </template>
            </div>

            <!-- ── CARD: Material Requirement Summary ── -->
            <div class="bomx-card">
              <div class="bomx-card-hdr">
                <span class="bomx-card-hdr-title"><span v-html="icon('package',14)"></span> Material Requirement Summary</span>
                <div style="display:flex;gap:8px;flex-shrink:0">
                  <button v-if="!isNew && pp.docstatus===1 && hasShortfall" class="bomx-btn bomx-btn-ghost bomx-btn-sm" @click="createMaterialRequests" :disabled="actionLoading==='mr'">
                    {{ actionLoading === 'mr' ? 'Creating…' : 'Create Material Requests' }}
                  </button>
                  <button class="bomx-btn bomx-btn-mfg bomx-btn-sm" @click="calculateRawMaterials" :disabled="mrLoading || !pp.po_items || !pp.po_items.length">
                    {{ mrLoading ? 'Calculating…' : 'Calculate Requirement' }}
                  </button>
                </div>
              </div>
              <div class="bomx-card-body">
                <div v-if="!pp.mr_items || !pp.mr_items.length" class="bomx-tree-empty">Add items above and click "Calculate Requirement" to see raw material requirements.</div>
                <template v-else>
                  <div v-if="hasShortfall" class="bomx-infobox bomx-ib-amber" style="margin-bottom:14px">
                    <span v-html="icon('alertTriangle',14)"></span>
                    <span><b>{{ shortfallCount }} material{{ shortfallCount===1?'':'s' }} short</b> — est. ₹{{ fmt(totalShortfallCost) }} to procure. Raise Material Requests before starting production.</span>
                  </div>
                  <div class="bomx-pp-mat-grid">
                    <div v-for="(m, idx) in pp.mr_items" :key="idx" class="bomx-pp-mat-card">
                      <div class="bomx-pp-mat-name">{{ m.item_name || m.item_code }}</div>
                      <div class="bomx-pp-mat-code mono">{{ m.item_code }}</div>
                      <div class="bomx-pp-mat-row"><span>Required</span><span class="mono" style="font-weight:700">{{ fmt(m.required_qty) }} {{ m.uom }}</span></div>
                      <div class="bomx-pp-mat-row"><span>Available</span><span class="mono">{{ fmt(m.available_qty) }} {{ m.uom }}</span></div>
                      <div class="bomx-pp-mat-row">
                        <span>Shortfall</span>
                        <span class="mono" :class="flt(m.shortfall_qty) > 0 ? 'bomx-pp-stock-short' : 'bomx-pp-stock-ok'">
                          {{ flt(m.shortfall_qty) > 0 ? fmt(m.shortfall_qty) + ' ' + m.uom : 'Sufficient' }}
                        </span>
                      </div>
                      <div v-if="flt(m.shortfall_qty) > 0" class="bomx-pp-mat-row">
                        <span>Est. Cost</span>
                        <span class="mono">₹{{ fmt(m.estimated_cost) }}</span>
                      </div>
                    </div>
                  </div>
                </template>
              </div>
            </div>

            <!-- ── CARD: Work Orders ── -->
            <div class="bomx-card" v-if="isNew">
              <div class="bomx-card-body"><div class="bomx-tree-empty">Save and submit the Production Plan first to create Work Orders.</div></div>
            </div>
            <template v-else>
              <div class="bomx-card" v-if="pp.docstatus===1">
                <div class="bomx-card-hdr">
                  <span class="bomx-card-hdr-title"><span v-html="icon('settings',14)"></span> Create Work Orders</span>
                  <div style="display:flex;gap:8px;flex-shrink:0">
                    <button v-if="hasDraftWorkOrders" class="bomx-btn bomx-btn-ghost bomx-btn-sm" @click="bulkSubmitWorkOrders" :disabled="actionLoading==='bulk-submit'">
                      {{ actionLoading === 'bulk-submit' ? 'Submitting…' : 'Submit All Work Orders' }}
                    </button>
                    <button class="bomx-btn bomx-btn-mfg bomx-btn-sm" @click="createWorkOrders" :disabled="actionLoading || !pendingWOQty">
                      {{ actionLoading==='wo' ? 'Creating…' : 'Create Work Orders' }}
                    </button>
                  </div>
                </div>
                <div class="bomx-card-body" v-if="!pendingWOQty">
                  <div class="bomx-field-hint" style="margin:0">Every row already has a Work Order for its full Planned Qty.</div>
                </div>
              </div>

              <div class="bomx-card">
                <div class="bomx-card-hdr">
                  <span class="bomx-card-hdr-title" :style="workOrders.length ? 'color:var(--bx-green)' : ''">
                    <span v-html="icon('check',14)"></span> Work Orders Created
                  </span>
                  <button class="bomx-btn bomx-btn-ghost bomx-btn-sm" @click="loadWorkOrders" :disabled="woLoading">Refresh</button>
                </div>
                <div class="bomx-card-body">
                  <div v-if="!workOrders.length" class="bomx-tree-empty">No Work Orders created yet.</div>
                  <template v-else>
                    <div class="bomx-infobox bomx-ib-green" style="margin-bottom:12px">
                      <span v-html="icon('check',14)"></span>
                      <span><b>{{ workOrders.length }}</b> Work Order{{ workOrders.length===1?'':'s' }} created from this Production Plan. Click a chip to open it.</span>
                    </div>
                    <div class="bomx-pp-wo-chips">
                      <span v-for="w in workOrders" :key="w.name" class="bomx-pp-wo-chip" :class="'wo-' + woStatusClass(w)" @click="router.push(`/manufacturing/work-order/${w.name}`)" :title="(w.item_name || w.production_item) + ' — ' + w.status">
                        {{ w.name }}
                      </span>
                    </div>
                  </template>
                </div>
              </div>
            </template>

          </div>
        </template>
  </div>

  <!-- Sales Order picker modal -->
  <div v-if="showSOPickerModal" class="bomx-modal-overlay" @click.self="showSOPickerModal=false">
    <div class="bomx-modal" style="width:560px;max-width:94vw">
      <div class="bomx-modal-title">Add Sales Orders</div>
      <div class="bomx-modal-body">
        <div v-if="soPickerLoading" class="bomx-tree-empty">Loading open Sales Orders…</div>
        <div v-else-if="!soPickerList.length" class="bomx-tree-empty">No open Sales Orders with pending delivery found.</div>
        <div v-else class="bomx-rm-cards" style="max-height:360px;overflow-y:auto">
          <div v-for="o in soPickerList" :key="o.name" class="bomx-rm-card" style="cursor:pointer" @click="toggleSOPick(o.name)">
            <div class="bomx-rm-card-hdr">
              <input type="checkbox" :checked="soPickerSelected.includes(o.name)" @click.stop="toggleSOPick(o.name)"/>
              <span class="bomx-rm-card-title mono" style="font-weight:600">{{ o.name }}</span>
              <span style="font-size:12px;color:var(--bx-muted)">{{ o.status }}</span>
            </div>
            <div class="bomx-rm-card-body" style="grid-template-columns:1fr 1fr">
              <div class="bomx-rm-field"><label>Customer</label><div class="bomx-rm-static">{{ o.customer_name }}</div></div>
              <div class="bomx-rm-field"><label>Delivery Date</label><div class="bomx-rm-static">{{ fmtDate(o.delivery_date) }}</div></div>
            </div>
          </div>
        </div>
      </div>
      <div class="bomx-modal-actions">
        <button class="bomx-btn" style="background:#fff;border:1px solid var(--bx-border)" @click="showSOPickerModal=false">Cancel</button>
        <button class="bomx-btn bomx-btn-mfg" @click="confirmSOPicker" :disabled="!soPickerSelected.length">Add {{ soPickerSelected.length || '' }}</button>
      </div>
    </div>
  </div>

</div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet, apiSave, apiList, apiSubmit, apiCancel, apiAmend, apiCall, apiDelete, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { useConfirm } from "../composables/useConfirm.js";

const ENGINE = "zoho_books_clone.manufacturing.production_plan_engine.";

const route = useRoute();
const router = useRouter();
const { toast } = useToast();
const { confirm } = useConfirm();

// ── LIST STATE ──────────────────────────────────────────────
const loading = ref(false);
const list = ref([]);
const search = ref("");
const filterStatus = ref("");

const statusOptions = ["Draft", "Submitted", "Work Orders Created", "Completed", "Cancelled"];

const selectedName = computed(() => (route.params.name && route.params.name !== "new") ? route.params.name : (route.params.name === "new" ? "new" : null));

async function loadList() {
  try {
    const fields = ["name", "posting_date", "company", "status", "docstatus", "modified", "remarks"];
    const r = await apiList("Production Plan", { fields, limit: 1000, order: "modified desc" });
    list.value = r || [];
  } catch (e) {
    toast("Could not load Production Plans: " + e.message, "error");
  }
}

const sorted = computed(() => {
  let r = list.value;
  if (filterStatus.value) r = r.filter(i => i.status === filterStatus.value);
  const q = search.value.toLowerCase().trim();
  if (q) r = r.filter(i => [i.name, i.company, i.status, i.remarks].some(f => (f || "").toLowerCase().includes(q)));
  return r;
});

function statusClass(row) {
  if (row.status === "Completed" || row.status === "Work Orders Created") return "badge-active";
  if (row.status === "Cancelled") return "badge-cancelled";
  if (row.status === "Draft") return "badge-obsolete";
  return "badge-inprocess";
}

const countTotal = computed(() => list.value.length);
const countDraft = computed(() => list.value.filter(i => i.status === "Draft").length);
const countSubmitted = computed(() => list.value.filter(i => i.status === "Submitted").length);
const countWOCreated = computed(() => list.value.filter(i => i.status === "Work Orders Created").length);
const countCompleted = computed(() => list.value.filter(i => i.status === "Completed").length);
const countCancelled = computed(() => list.value.filter(i => i.status === "Cancelled").length);

// Pipeline stages shown in the detail header, derived from pp.status.
// Cancelled plans get their own short track; everything else walks
// Draft → Submitted → Work Orders Created → Completed.
const PIPELINE_STEPS = [
  { key: "Draft", label: "Draft" },
  { key: "Submitted", label: "Submitted" },
  { key: "Work Orders Created", label: "WOs Created" },
  { key: "Completed", label: "Completed" },
];
const pipelineSteps = computed(() => {
  if (pp.value.status === "Cancelled") {
    return [
      { key: "Draft", label: "Draft" },
      { key: "Submitted", label: "Submitted" },
      { key: "Cancelled", label: "Cancelled" },
    ];
  }
  return PIPELINE_STEPS;
});
function pipelineStepState(stepKey) {
  const order = ["Draft", "Submitted", "Work Orders Created", "Completed"];
  const curIdx = order.indexOf(pp.value.status === "Cancelled" ? "Submitted" : pp.value.status);
  const stepIdx = order.indexOf(stepKey);
  if (stepKey === "Cancelled") return "cancelled";
  if (stepIdx <= curIdx) return "done";
  return "pending";
}
function woStatusClass(w) {
  if (w.status === "Completed") return "badge-active";
  if (w.status === "Cancelled") return "badge-cancelled";
  if (w.status === "Draft") return "badge-obsolete";
  if (w.status === "Stopped") return "badge-stopped";
  return "badge-inprocess";
}

function selectPlan(name) {
  router.push(`/manufacturing/production-plan/${name}`);
}
function openAdd() {
  router.push("/manufacturing/production-plan/new");
}
function goBackToList() {
  router.push("/manufacturing/production-plan");
}

// ── DETAIL STATE ─────────────────────────────────────────────
const isNew = computed(() => route.params.name === "new");
const saving = ref(false);
const submitting = ref(false);
const itemsLoading = ref(false);
const mrLoading = ref(false);
const actionLoading = ref(false);
const woLoading = ref(false);

function emptyPP() {
  return {
    doctype: "Production Plan",
    posting_date: new Date().toISOString().slice(0, 10),
    status: "Draft",
    company: "",
    default_source_warehouse: "",
    default_wip_warehouse: "",
    default_fg_warehouse: "",
    default_scrap_warehouse: "",
    sales_orders: [],
    po_items: [],
    mr_items: [],
    remarks: "",
  };
}
const pp = ref(emptyPP());

const stockItems = ref([]);
const bomList = ref([]);
const warehouseList = ref([]);
const workOrders = ref([]);

const EMPTY_PO_ITEM = () => ({ item_code: "", item_name: "", bom_no: "", planned_qty: 1, stock_uom: "", warehouse: "", sales_order: "", work_order_created_qty: 0 });

// docstatus: 0 = Draft, 1 = Submitted, 2 = Cancelled. Once submitted, the
// plan (items/warehouses/sales orders) is locked — from here on, progress
// happens only through Create Work Orders on the Work Orders tab.
const readOnly = computed(() => !isNew.value && (pp.value.docstatus === 1 || pp.value.docstatus === 2));

onMounted(async () => {
  loading.value = true;
  try {
    const co = await resolveCompany();
    if (isNew.value) pp.value.company = co;

    // Independent of each other — Warehouse only needs `co`, already resolved
    // above. loadList() doesn't depend on this reference data either, so it's
    // folded in too, turning ~4 sequential round trips into 1.
    const [stk, boms, whs] = await Promise.all([
      apiList("Item", { fields: ["name", "item_name", "stock_uom"], filters: [["is_stock_item", "=", 1]], limit: 5000, order: "name asc" }),
      apiList("BOM", { fields: ["name", "item", "quantity", "is_default", "docstatus", "is_active"], filters: [["docstatus", "=", 1], ["is_active", "=", 1]], limit: 2000, order: "name asc" }),
      apiList("Warehouse", { fields: ["name"], filters: co ? [["company", "=", co], ["is_group", "=", 0]] : [["is_group", "=", 0]], limit: 1000, order: "name asc" }),
      loadList(),
    ]);
    stockItems.value = stk || [];
    bomList.value = boms || [];
    warehouseList.value = whs || [];

    if (route.params.name) {
      await loadPP();
    } else {
      // New plan — prefill default warehouses from Manufacturing Settings
      try {
        const ms = await apiCall(
          "zoho_books_clone.manufacturing.doctype.manufacturing_settings.manufacturing_settings.get_manufacturing_defaults"
        );
        if (ms) {
          if (!pp.value.default_source_warehouse && ms.default_source_warehouse)
            pp.value.default_source_warehouse = ms.default_source_warehouse;
          if (!pp.value.default_wip_warehouse && ms.default_wip_warehouse)
            pp.value.default_wip_warehouse = ms.default_wip_warehouse;
          if (!pp.value.default_fg_warehouse && ms.default_fg_warehouse)
            pp.value.default_fg_warehouse = ms.default_fg_warehouse;
          if (!pp.value.default_scrap_warehouse && ms.default_scrap_warehouse)
            pp.value.default_scrap_warehouse = ms.default_scrap_warehouse;
        }
      } catch (e) {
        // non-fatal — settings may not be configured yet
      }
    }
  } catch (e) {
    toast("Error loading data: " + e.message, "error");
  }
  loading.value = false;
});

watch(() => route.params.name, async (name) => {
  if (!name) { pp.value = emptyPP(); return; }
  loading.value = true;
  try {
    await loadPP();
  } catch (e) {
    toast("Error loading Production Plan: " + e.message, "error");
  }
  loading.value = false;
});

async function loadPP() {
  if (isNew.value) {
    pp.value = emptyPP();
    return;
  }
  const data = await apiGet("Production Plan", route.params.name);
  pp.value = data;
  if (!pp.value.sales_orders) pp.value.sales_orders = [];
  if (!pp.value.po_items) pp.value.po_items = [];
  if (!pp.value.mr_items) pp.value.mr_items = [];
  if (pp.value.docstatus === 1) await loadWorkOrders();
}

function bomsFor(itemCode) {
  // Previously returned the full bomList (every BOM in the system) when no
  // item was picked yet, so the dropdown was pickable out of order and full
  // of irrelevant options. An item must be chosen first.
  if (!itemCode) return [];
  return bomList.value.filter(b => b.item === itemCode);
}

function onPOItemChange(row) {
  const item = stockItems.value.find(i => i.name === row.item_code);
  row.item_name = item ? item.item_name : "";
  row.stock_uom = item ? item.stock_uom : "";
  const candidates = bomsFor(row.item_code);
  // Only reassign BOM if the current one isn't valid for the newly-selected
  // item. Previously this always overwrote row.bom_no, so any BOM already
  // chosen (however it got there) was silently discarded on every item
  // change, even when it belonged to the new item.
  const stillValid = row.bom_no && candidates.some(b => b.name === row.bom_no);
  if (!stillValid) {
    const def = candidates.find(b => b.is_default) || candidates[0];
    row.bom_no = def ? def.name : "";
  }
}

function addPOItem() { pp.value.po_items.push(EMPTY_PO_ITEM()); }

// ── Sales Order picker ──────────────────────────────────────────────────
const showSOPickerModal = ref(false);
const soPickerList = ref([]);
const soPickerSelected = ref([]);
const soPickerLoading = ref(false);

async function openSOPicker() {
  showSOPickerModal.value = true;
  soPickerSelected.value = [];
  soPickerLoading.value = true;
  try {
    const result = await apiCall(ENGINE + "get_open_sales_orders", { company: pp.value.company });
    const existing = new Set((pp.value.sales_orders || []).map(r => r.sales_order));
    soPickerList.value = (result || []).filter(o => !existing.has(o.name));
  } catch (e) {
    toast(e.message, "error");
  }
  soPickerLoading.value = false;
}

function toggleSOPick(name) {
  const i = soPickerSelected.value.indexOf(name);
  if (i >= 0) soPickerSelected.value.splice(i, 1);
  else soPickerSelected.value.push(name);
}

function confirmSOPicker() {
  const chosen = soPickerList.value.filter(o => soPickerSelected.value.includes(o.name));
  chosen.forEach(o => {
    pp.value.sales_orders.push({
      sales_order: o.name,
      customer: o.customer_name,
      delivery_date: o.delivery_date,
      status: o.status,
      grand_total: o.grand_total,
    });
  });
  showSOPickerModal.value = false;
}

async function removeSalesOrder(idx) {
  // Removing a Sales Order used to just splice the row and leave whatever
  // had already been pulled from it sitting in Items to Manufacture --
  // demand for a SO no longer on the plan stayed on the plan regardless.
  // Re-pull from the remaining Sales Orders (if any) so SO-sourced rows
  // reflect exactly what's still selected; work_order_created_qty and any
  // BOM choice already made are preserved for items still present.
  pp.value.sales_orders.splice(idx, 1);
  const remaining = (pp.value.sales_orders || []).map(r => r.sales_order).filter(Boolean);
  if (remaining.length) {
    await pullItemsFromSalesOrders();
  } else {
    pp.value.po_items = (pp.value.po_items || []).filter(r => !r.sales_order);
    toast("Sales Order removed — its pulled item(s) were also removed since no Sales Orders remain");
  }
}

async function pullItemsFromSalesOrders() {
  const soNames = (pp.value.sales_orders || []).map(r => r.sales_order).filter(Boolean);
  if (!soNames.length) return toast("Add at least one Sales Order first", "error");
  itemsLoading.value = true;
  try {
    const items = await apiCall(ENGINE + "get_items_from_sales_orders", { sales_orders: soNames });
    // Keep manually-added rows (no sales_order tag); replace SO-sourced rows
    // with the freshly aggregated set so re-pulling reflects any delivery
    // that's happened since.
    const manual = (pp.value.po_items || []).filter(r => !r.sales_order);
    // Re-pulling rebuilds SO-sourced rows from scratch, which would otherwise
    // wipe work_order_created_qty (silently un-tracking WOs already created
    // for this item on an amended plan) and any BOM already picked for it.
    // Carry both forward by item_code before the old rows are discarded.
    const priorByItem = {};
    for (const r of (pp.value.po_items || [])) {
      if (r.sales_order && r.item_code) priorByItem[r.item_code] = r;
    }
    pp.value.po_items = [...manual, ...(items || []).map(i => {
      const prior = priorByItem[i.item_code];
      return {
        ...EMPTY_PO_ITEM(), ...i,
        work_order_created_qty: prior ? flt(prior.work_order_created_qty) : 0,
        bom_no: (prior && prior.bom_no) || i.bom_no,
      };
    })];
    toast(`Pulled ${(items || []).length} item(s) from ${soNames.length} Sales Order(s)`);
  } catch (e) {
    toast(e.message, "error");
  }
  itemsLoading.value = false;
}

// ── Raw Materials ────────────────────────────────────────────────────────
async function calculateRawMaterials() {
  if (!pp.value.po_items || !pp.value.po_items.length) return toast("Add items to manufacture first", "error");
  mrLoading.value = true;
  try {
    const rows = pp.value.po_items.map(r => ({ item_code: r.item_code, bom_no: r.bom_no, planned_qty: r.planned_qty }));
    const resp = await apiCall(ENGINE + "get_raw_materials", {
      po_items: rows,
      warehouse: pp.value.default_source_warehouse || undefined,
      production_plan: pp.value.name || undefined,
    });
    pp.value.mr_items = resp.items || [];
    const warnings = [];
    if (!resp.warehouse_checked) {
      warnings.push("no Default Source Warehouse set — every item is shown as full shortfall, not checked against stock");
    }
    if (resp.skipped && resp.skipped.length) {
      warnings.push(`${resp.skipped.length} item(s) skipped (no BOM selected): ${resp.skipped.join(", ")}`);
    }
    toast(warnings.length ? `Raw material requirement calculated — but ${warnings.join("; ")}` : "Raw material requirement calculated", warnings.length ? "error" : undefined);
  } catch (e) {
    toast(e.message, "error");
  }
  mrLoading.value = false;
}

// ── Work Orders ──────────────────────────────────────────────────────────
const pendingWOQty = computed(() => (pp.value.po_items || []).some(r => flt(r.planned_qty) - flt(r.work_order_created_qty) > 0.0001));
const hasShortfall = computed(() => (pp.value.mr_items || []).some(r => flt(r.shortfall_qty) > 0.0001));
const shortfallCount = computed(() => (pp.value.mr_items || []).filter(r => flt(r.shortfall_qty) > 0.0001).length);
const totalShortfallCost = computed(() => (pp.value.mr_items || []).reduce((s, r) => s + (flt(r.shortfall_qty) > 0.0001 ? flt(r.estimated_cost) : 0), 0));
const hasDraftWorkOrders = computed(() => workOrders.value.some(w => w.status === "Draft"));
const totalPlannedQty = computed(() => (pp.value.po_items || []).reduce((s, r) => s + flt(r.planned_qty), 0));
const totalPendingWOQty = computed(() => (pp.value.po_items || []).reduce((s, r) => s + Math.max(0, flt(r.planned_qty) - flt(r.work_order_created_qty)), 0));

function soStatusClass(status) {
  if (!status) return "badge-obsolete";
  const s = status.toLowerCase();
  if (s.includes("cancel")) return "badge-cancelled";
  if (s.includes("draft")) return "badge-obsolete";
  if (s.includes("complet") || s.includes("deliver")) return "badge-active";
  return "badge-inprocess";
}

async function loadWorkOrders() {
  woLoading.value = true;
  try {
    workOrders.value = await apiList("Work Order", {
      fields: ["name", "production_item", "item_name", "qty", "status"],
      filters: [["production_plan", "=", pp.value.name]],
      limit: 200, order: "creation desc",
    }) || [];
  } catch (e) { /* non-fatal */ }
  woLoading.value = false;
}

async function createWorkOrders() {
  actionLoading.value = "wo";
  try {
    const created = await apiCall(ENGINE + "create_work_orders", { production_plan: pp.value.name });
    toast(`Created ${created.length} Work Order(s)`);
    await loadPP();
  } catch (e) {
    toast(e.message, "error");
  }
  actionLoading.value = false;
}

async function bulkSubmitWorkOrders() {
  if (!confirm("Submit all Draft Work Orders linked to this Production Plan? They will be locked for editing.")) return;
  actionLoading.value = "bulk-submit";
  try {
    const result = await apiCall(ENGINE + "bulk_submit_work_orders", { production_plan: pp.value.name });
    const sub = (result.submitted || []).length;
    const err = (result.errors || []).length;
    if (err > 0) {
      toast(`Submitted ${sub}, but ${err} Work Order(s) failed — check each individually.`, "error");
    } else {
      toast(`${sub} Work Order(s) submitted successfully`);
    }
    await loadWorkOrders();
    await loadPP();
  } catch (e) {
    toast(e.message, "error");
  }
  actionLoading.value = false;
}

async function createMaterialRequests() {
  actionLoading.value = "mr";
  try {
    const names = await apiCall(ENGINE + "create_material_requests", { production_plan: pp.value.name });
    toast(`Material Request ${names[0]} created for shortfall items`);
  } catch (e) {
    toast(e.message, "error");
  }
  actionLoading.value = false;
}

// ── Save / Submit / Cancel / Amend ───────────────────────────────────────
async function deletePP(name, event) {
  if (event) event.stopPropagation();
  const ok = await confirm({
    title: "Delete Production Plan",
    body: `Are you sure you want to delete ${name}? This cannot be undone.`,
    okLabel: "Delete",
    okStyle: "danger",
  });
  if (!ok) return;
  try {
    await apiDelete("Production Plan", name);
    toast(`${name} deleted`);
    if (selectedName.value === name) goBackToList();
    await loadList();
  } catch (e) {
    toast(e.message, "error");
  }
}

async function saveRemarks() {
  // Every other field on a submitted plan is rightly locked (po_items/mr_items
  // drive Work Orders and Material Requests already created against them), but
  // remarks is just a note and shouldn't have gone read-only along with them.
  // save_doc already lets submitted-doc updates through, so this only needed
  // a UI entry point since the main Save button disappears once readOnly.
  saving.value = true;
  try {
    const doc = await apiSave(pp.value);
    pp.value = doc;
    toast("Remarks saved");
  } catch (e) {
    toast(e.message, "error");
  }
  saving.value = false;
}

async function save() {
  if (!pp.value.po_items || !pp.value.po_items.length) return toast("Add at least one item to manufacture", "error");
  if (!pp.value.default_fg_warehouse) return toast("Default Finished Goods Warehouse is required", "error");
  for (const r of pp.value.po_items) {
    if (!flt(r.planned_qty) || flt(r.planned_qty) <= 0) return toast(`Row for ${r.item_code || '(blank)'}: Planned Qty must be greater than 0`, "error");
  }

  saving.value = true;
  try {
    const doc = await apiSave(pp.value);
    toast(isNew.value ? "Production Plan created" : "Production Plan updated");
    if (isNew.value) {
      router.replace(`/manufacturing/production-plan/${doc.name}`);
    } else {
      pp.value = doc;
    }
    loadList();
  } catch (e) {
    toast(e.message, "error");
  }
  saving.value = false;
}

async function submitPP() {
  if (!pp.value.name) return;
  submitting.value = true;
  try {
    const doc = await apiSubmit("Production Plan", pp.value.name);
    pp.value = doc;
    toast("Production Plan submitted");
    loadList();
  } catch (e) {
    toast(e.message, "error");
  }
  submitting.value = false;
}

async function cancelPP() {
  if (!pp.value.name) return;
  if (!confirm("Cancel this Production Plan?")) return;
  submitting.value = true;
  try {
    const doc = await apiCancel("Production Plan", pp.value.name);
    pp.value = doc;
    toast("Production Plan cancelled");
    loadList();
  } catch (e) {
    toast(e.message, "error");
  }
  submitting.value = false;
}

async function amendPP() {
  if (!pp.value.name) return;
  submitting.value = true;
  try {
    const doc = await apiAmend("Production Plan", pp.value.name);
    toast(`New revision ${doc.name} created`);
    router.push(`/manufacturing/production-plan/${doc.name}`);
    loadList();
  } catch (e) {
    toast(e.message, "error");
  }
  submitting.value = false;
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

// ── UTIL ─────────────────────────────────────────────────────
const ICONS = {
  plus:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>',
  x:     '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>',
  open:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="7" y1="17" x2="17" y2="7"></line><polyline points="7 7 17 7 17 17"></polyline></svg>',
  chevronLeft: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>',
  clipboard: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"></path><rect x="9" y="3" width="6" height="4" rx="1"></rect><line x1="9" y1="12" x2="15" y2="12"></line><line x1="9" y1="16" x2="13" y2="16"></line></svg>',
  fileText: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>',
  settings: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"></path></svg>',
  package: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path></svg>',
  alertTriangle: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
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
.bomx-list-view { display:flex; flex-direction:column; gap:14px; }

/* ── List toolbar ── */
.bomx-list-toolbar { display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap; }
.bomx-panel-title { font-size:16px; font-weight:700; color:var(--bx-text); }
.bomx-count { font-size:13px; font-weight:400; color:var(--bx-muted); }

/* ── Filters row ── */
.bomx-list-filters { display:flex; gap:10px; flex-wrap:wrap; }
.bomx-status-filter { width:200px; }
.bomx-search-full { flex:1; min-width:220px; }
.bomx-list-empty { text-align:center; padding:40px; color:var(--bx-muted); font-size:13px; background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); }
.bomx-item-name { font-size:14.5px; font-weight:700; color:var(--bx-text); }

/* ── Summary strip (list view) ── */
.bomx-pp-sumstrip { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; }
.bomx-pp-sc { position:relative; background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); padding:12px 14px 12px 18px; text-align:left; overflow:hidden; }
.bomx-pp-sc-bar { position:absolute; top:0; left:0; width:3px; height:100%; }
.bomx-pp-sc-val { font-size:20px; font-weight:700; font-family:var(--bx-mono); color:var(--bx-text); }
.bomx-pp-sc-lbl { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.03em; color:var(--bx-muted); margin-top:2px; }

/* ── Plan rows (full-width list view) ── */
.bomx-pp-rows { display:flex; flex-direction:column; gap:12px; }
.bomx-pp-row { background:var(--bx-surface); border:1.5px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; cursor:pointer; transition:all .15s; }
.bomx-pp-row:hover { border-color:var(--bx-mfgL); box-shadow:0 4px 16px rgba(26,110,247,.08); }
.bomx-pp-row-top { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; padding:14px 18px; border-bottom:1px solid var(--bx-border); }
.bomx-pp-row-foot { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:10px 18px; background:var(--bx-surf2); }
.bomx-pp-row-meta { display:flex; align-items:center; gap:6px; font-size:12.5px; color:var(--bx-muted); }

/* ── Pipeline stepper (detail header) ── */
.bomx-pp-pipeline { display:flex; align-items:center; gap:0; padding:14px 22px; background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); margin-bottom:16px; flex-wrap:wrap; }
.bomx-pp-pipe-step { display:flex; flex-direction:column; align-items:center; gap:4px; flex-shrink:0; }
.bomx-pp-pipe-dot { width:30px; height:30px; border-radius:50%; border:2px solid var(--bx-border); background:#fff; color:var(--bx-muted); display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:700; flex-shrink:0; }
.bomx-pp-pipe-dot.st-done { border-color:var(--bx-mfg); background:var(--bx-mfg); color:#fff; }
.bomx-pp-pipe-dot.st-cancelled { border-color:var(--bx-red); background:var(--bx-red); color:#fff; }
.bomx-pp-pipe-dot.st-pending { border-color:var(--bx-mfgL); color:var(--bx-mfgB); }
.bomx-pp-pipe-label { font-size:11px; font-weight:600; white-space:nowrap; color:var(--bx-muted); }
.bomx-pp-pipe-label.st-done { color:var(--bx-mfgB); }
.bomx-pp-pipe-label.st-cancelled { color:var(--bx-red); }
.bomx-pp-pipe-line { height:2px; width:44px; flex-shrink:0; margin-bottom:18px; background:var(--bx-border); }
.bomx-pp-pipe-line.done { background:var(--bx-mfg); }

/* ── Items to Manufacture table ── */
.bomx-tbl-wrap { overflow-x:auto; }
.bomx-item-tbl { width:100%; border-collapse:collapse; font-size:13px; table-layout:auto; }
.bomx-item-tbl th { text-align:left; padding:8px 8px; border-bottom:1px solid var(--bx-border); font-size:10px; letter-spacing:.05em; text-transform:uppercase; color:var(--bx-muted); font-weight:700; background:var(--bx-surf2); white-space:nowrap; }
.bomx-item-tbl th.right, .bomx-item-tbl td.right { text-align:right; }
.bomx-item-tbl td { padding:7px 8px; border-bottom:1px solid #F1F3F5; vertical-align:middle; }
.bomx-item-tbl td select.bomx-fi, .bomx-item-tbl td input.bomx-fi { width:100%; box-sizing:border-box; min-width:0; }
.bomx-item-tbl tr:last-child td { border-bottom:none; }
.bomx-item-tbl tr:hover td { background:#FAFBFF; }

/* ── Raw material grid ── */
.bomx-pp-mat-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:10px; }
.bomx-pp-mat-card { background:var(--bx-surf2); border:1px solid var(--bx-border); border-radius:var(--bx-rsm); padding:12px 14px; display:flex; flex-direction:column; gap:4px; }
.bomx-pp-mat-name { font-size:13px; font-weight:600; color:var(--bx-text); }
.bomx-pp-mat-code { font-size:11px; color:var(--bx-muted); }
.bomx-pp-mat-row { display:flex; justify-content:space-between; font-size:12px; color:var(--bx-muted); margin-top:2px; }
.bomx-pp-stock-ok { color:var(--bx-green); font-weight:700; }
.bomx-pp-stock-short { color:var(--bx-red); font-weight:700; }

/* ── Info box / WO chips ── */
.bomx-pp-infobox { border-radius:var(--bx-rsm); padding:10px 13px; font-size:13px; display:flex; gap:9px; align-items:flex-start; line-height:1.5; background:var(--bx-greenS); color:var(--bx-green); border:1px solid rgba(47,158,68,.2); margin-bottom:12px; }
.bomx-pp-wo-chips { display:flex; flex-wrap:wrap; gap:8px; }
.bomx-pp-wo-chip { display:inline-flex; align-items:center; gap:6px; border-radius:20px; padding:5px 12px; font-size:12.5px; font-weight:700; font-family:var(--bx-mono); cursor:pointer; border:1px solid transparent; transition:all .12s; }
.bomx-pp-wo-chip:hover { filter:brightness(0.97); }
.bomx-pp-wo-chip.wo-badge-active { background:var(--bx-greenS); color:var(--bx-green); border-color:rgba(47,158,68,.2); }
.bomx-pp-wo-chip.wo-badge-obsolete { background:#F1F3F5; color:var(--bx-muted); border-color:var(--bx-border); }
.bomx-pp-wo-chip.wo-badge-cancelled { background:var(--bx-redS); color:var(--bx-red); border-color:rgba(201,42,42,.2); }
.bomx-pp-wo-chip.wo-badge-stopped { background:var(--bx-amberS); color:var(--bx-amber); border-color:rgba(230,119,0,.2); }
.bomx-pp-wo-chip.wo-badge-inprocess { background:var(--bx-blueS); color:var(--bx-blue); border-color:rgba(25,113,194,.2); }

/* ── Badges ── */
.bomx-badge { display:inline-flex; align-items:center; padding:2px 8px; border-radius:20px; font-size:11px; font-weight:600; white-space:nowrap; }
.badge-active { background:var(--bx-greenS); color:var(--bx-green); }
.badge-obsolete { background:#F1F3F5; color:var(--bx-muted); }
.badge-cancelled { background:var(--bx-redS); color:var(--bx-red); }
.badge-stopped { background:var(--bx-amberS); color:var(--bx-amber); }
.badge-inprocess { background:var(--bx-blueS); color:var(--bx-blue); }

/* ── Back button (detail view) ── */
.bomx-back-btn { display:inline-flex; align-items:center; justify-content:center; width:38px; height:34px; margin:14px 0 0 14px; background:#fff; border:1px solid var(--bx-border); border-radius:10px; color:var(--bx-muted); cursor:pointer; box-shadow:0 1px 2px rgba(16,24,40,.05); transition:all .15s; }
.bomx-back-btn:hover:not(:disabled) { border-color:var(--bx-mfg); color:var(--bx-mfg); background:var(--bx-mfgS); }
.bomx-back-btn:disabled { opacity:.5; cursor:not-allowed; }

/* ── Detail panel ── */
.bomx-detail-panel { background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; display:flex; flex-direction:column; min-height: calc(100vh - 100px); }
.bomx-empty-state { text-align:center; padding:60px 20px; color:var(--bx-muted); }
.bomx-empty-icon { font-size:48px; margin-bottom:14px; }
.bomx-empty-title { font-size:16px; font-weight:700; color:var(--bx-text); margin-bottom:6px; }
.bomx-empty-sub { font-size:13px; line-height:1.6; max-width:280px; margin:0 auto 20px; }

.bomx-detail-hdr { padding:18px 22px; background:linear-gradient(135deg, var(--bx-mfgB), var(--bx-mfg)); }
.bomx-detail-title { font-size:18px; font-weight:700; color:#fff; margin-bottom:4px; }
.bomx-detail-meta { font-size:12.5px; color:rgba(255,255,255,.75); display:flex; align-items:center; gap:8px; flex-wrap:wrap; }


.bomx-hdr-fields { display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; padding:16px 22px; border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); }
.bomx-hf-cols-1-1 { grid-template-columns:1fr 1fr; }
.bomx-hf-cols-1 { grid-template-columns:1fr; }
.bomx-hf-label { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); margin-bottom:4px; }
.bomx-field-hint { font-size:12px; color:var(--bx-muted); margin-top:5px; }

.bomx-body { padding:20px 22px; overflow-y:auto; flex:1; display:flex; flex-direction:column; gap:16px; }
.bomx-pp-section-divider { height:1px; background:var(--bx-border); margin:24px -22px 24px; }
.bomx-section-lbl { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--bx-muted); margin-bottom:8px; }
.bomx-tree-empty { text-align:center; padding:20px; color:var(--bx-muted); font-size:13px; }
.bomx-link { color:var(--bx-mfg); font-weight:600; cursor:pointer; }
.bomx-link:hover { text-decoration:underline; }

.bomx-prod-card { background:var(--bx-surf2); border:1px solid var(--bx-border); border-radius:var(--bx-radius); padding:16px; margin-bottom:16px; }

/* ── Card sections (Plan Details / Sales Orders / Items / Material Req / Work Orders) ── */
.bomx-card { background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; }
.bomx-card-hdr { padding:13px 18px; border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap; }
.bomx-card-hdr-title { font-size:13px; font-weight:700; display:flex; align-items:center; gap:8px; color:var(--bx-text); }
.bomx-card-hdr-title svg { color:var(--bx-mfg); flex-shrink:0; }
.bomx-card-body { padding:18px; }
.bomx-card-footer { padding:10px 16px; background:var(--bx-surf2); border-top:1px solid var(--bx-border); font-size:12.5px; color:var(--bx-muted); display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; }

/* ── Form grid (used inside Plan Details) ── */
.bomx-fg { display:grid; gap:12px; }
.bomx-fg-2 { grid-template-columns:1fr 1fr; }
.bomx-fg-4 { grid-template-columns:1fr 1fr 1fr 1fr; }
.bomx-fl { display:block; font-size:11.5px; font-weight:600; color:#495057; margin-bottom:4px; }
.bomx-fi-w { position:relative; }
@media (max-width:900px) { .bomx-fg-4 { grid-template-columns:1fr 1fr; } }
@media (max-width:640px) { .bomx-fg-2, .bomx-fg-4 { grid-template-columns:1fr; } }

/* ── Sales Order table ── */
.bomx-so-tbl { width:100%; border-collapse:collapse; font-size:13px; }
.bomx-so-tbl th { text-align:left; padding:8px 12px; border-bottom:1px solid var(--bx-border); font-size:10px; letter-spacing:.05em; text-transform:uppercase; color:var(--bx-muted); font-weight:700; background:var(--bx-surf2); white-space:nowrap; }
.bomx-so-tbl th.right, .bomx-so-tbl td.right { text-align:right; }
.bomx-so-tbl td { padding:8px 12px; border-bottom:1px solid #F1F3F5; vertical-align:middle; }
.bomx-so-tbl tr:last-child td { border-bottom:none; }
.bomx-so-tbl tr:hover td { background:#FAFBFF; }

/* ── Info boxes (shortfall / success banners) ── */
.bomx-infobox { border-radius:var(--bx-rsm); padding:11px 14px; font-size:13px; display:flex; gap:10px; align-items:flex-start; line-height:1.5; }
.bomx-ib-amber { background:var(--bx-amberS); color:var(--bx-mfgB); border:1px solid rgba(230,119,0,.25); }
.bomx-ib-amber svg { color:var(--bx-amber); flex-shrink:0; margin-top:1px; }
.bomx-ib-green { background:var(--bx-greenS); color:var(--bx-green); border:1px solid rgba(47,158,68,.2); }

/* ── Child-row cards ── */
.bomx-rm-cards { display:flex; flex-direction:column; gap:10px; }
.bomx-rm-card { background:#fff; border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; box-shadow:0 1px 3px rgba(16,24,40,.04); }
.bomx-rm-card-hdr { display:flex; align-items:center; gap:10px; padding:10px 14px; background:var(--bx-mfgS); border-bottom:1px solid var(--bx-border); }
.bomx-rm-card-title { flex:1; min-width:0; font-weight:600; }
.bomx-rm-card-body { display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:10px; padding:12px 14px; }
.bomx-rm-field { display:flex; flex-direction:column; gap:4px; min-width:0; }
.bomx-rm-field label { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); }
.bomx-rm-field .bomx-fi { width:100%; }
.bomx-rm-static { font-size:13px; color:var(--bx-text); padding:7px 0; }
@media (max-width:640px) {
  .bomx-rm-card-body { grid-template-columns:1fr 1fr; }
}

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

/* ── Modal ── */
.bomx-modal-overlay { position:fixed; inset:0; background:rgba(17,24,39,.5); display:flex; align-items:center; justify-content:center; z-index:1000; }
.bomx-modal { background:#fff; border-radius:12px; padding:22px; max-width:94vw; box-shadow:0 20px 50px rgba(0,0,0,.25); }
.bomx-modal-title { font-size:16px; font-weight:700; color:var(--bx-text); margin-bottom:14px; }
.bomx-modal-body { font-size:13.5px; color:var(--bx-text); line-height:1.5; }
.bomx-modal-actions { display:flex; justify-content:flex-end; gap:10px; margin-top:18px; }

.shimmer { background:linear-gradient(90deg,#f1f3f5 25%,#e9ecef 37%,#f1f3f5 63%); background-size:400% 100%; animation:shimmer 1.4s ease infinite; }
@keyframes shimmer { 0%{background-position:100% 50%} 100%{background-position:0 50%} }

/* ── Mobile responsive ── */
@media (max-width:768px) {
  .bomx-page { padding:10px; overflow-x:hidden; }
  .bomx-list-view { gap:10px; }
  .bomx-detail-panel { min-height:auto; }
  .bomx-status-filter { width:100%; }

  .bomx-detail-hdr { padding:14px 16px; }
  .bomx-detail-title { font-size:16px; }

  .bomx-hdr-fields, .bomx-hf-cols-1-1 { grid-template-columns:1fr; padding:12px 16px; gap:10px; }
  .bomx-body { padding:14px 16px; }

  .bomx-rm-card-body { grid-template-columns:1fr 1fr; }
  .bomx-prod-card { padding:14px; }

  .bomx-pp-sumstrip { grid-template-columns:repeat(2,1fr); }
  .bomx-pp-pipeline { padding:12px 16px; }
  .bomx-pp-pipe-line { width:24px; }
}

@media (max-width:420px) {
  .bomx-rm-card-body { grid-template-columns:1fr; }
}
</style>