<template>
<div class="bomx-page">

  <!-- ══════════ SUMMARY STRIP ══════════ -->
  <div class="bomx-sum-strip">
    <div class="bomx-sum-card">
      <div class="bomx-sc-bar" style="background:var(--bx-mfg)"></div>
      <div class="bomx-sc-lbl">Total Work Orders</div>
      <div class="bomx-sc-val">{{ list.length }}</div>
      <div class="bomx-sc-sub">All statuses</div>
    </div>
    <div class="bomx-sum-card">
      <div class="bomx-sc-bar" style="background:var(--bx-blue)"></div>
      <div class="bomx-sc-lbl" style="color:var(--bx-blue)">In Process</div>
      <div class="bomx-sc-val" style="color:var(--bx-blue)">{{ countByStatus('In Process') }}</div>
      <div class="bomx-sc-sub">Currently running</div>
    </div>
    <div class="bomx-sum-card">
      <div class="bomx-sc-bar" style="background:#868E96"></div>
      <div class="bomx-sc-lbl">Draft</div>
      <div class="bomx-sc-val">{{ countByStatus('Draft') }}</div>
      <div class="bomx-sc-sub">Not yet submitted</div>
    </div>
    <div class="bomx-sum-card">
      <div class="bomx-sc-bar" style="background:var(--bx-green)"></div>
      <div class="bomx-sc-lbl" style="color:var(--bx-green)">Completed</div>
      <div class="bomx-sc-val" style="color:var(--bx-green)">{{ countByStatus('Completed') }}</div>
      <div class="bomx-sc-sub">Finished production</div>
    </div>
    <div class="bomx-sum-card">
      <div class="bomx-sc-bar" style="background:var(--bx-amber)"></div>
      <div class="bomx-sc-lbl" style="color:var(--bx-amber)">Stopped</div>
      <div class="bomx-sc-val" style="color:var(--bx-amber)">{{ countByStatus('Stopped') }}</div>
      <div class="bomx-sc-sub">Paused production</div>
    </div>
    <div class="bomx-sum-card">
      <div class="bomx-sc-bar" style="background:var(--bx-blue)"></div>
      <div class="bomx-sc-lbl" style="color:var(--bx-blue)">Submitted</div>
      <div class="bomx-sc-val" style="color:var(--bx-blue)">{{ countByStatus('Submitted') }}</div>
      <div class="bomx-sc-sub">Not yet started</div>
    </div>
    <div class="bomx-sum-card">
      <div class="bomx-sc-bar" style="background:var(--bx-red)"></div>
      <div class="bomx-sc-lbl" style="color:var(--bx-red)">Cancelled</div>
      <div class="bomx-sc-val" style="color:var(--bx-red)">{{ countByStatus('Cancelled') }}</div>
      <div class="bomx-sc-sub">Voided Work Orders</div>
    </div>
    <div class="bomx-sum-card">
      <div class="bomx-sc-bar" style="background:var(--bx-violet)"></div>
      <div class="bomx-sc-lbl" style="color:var(--bx-violet)">Total Qty Planned</div>
      <div class="bomx-sc-val" style="color:var(--bx-violet)">{{ fmtNum(totalQtyPlanned) }}</div>
      <div class="bomx-sc-sub">Across all Work Orders</div>
    </div>
  </div>

  <!-- ══════════ STATUS TABS ══════════ -->
  <div class="bomx-status-tabs">
    <button class="bomx-status-tab" :class="{active: filterStatus===''}" @click="filterStatus=''">All <span class="bomx-tab-count">{{ list.length }}</span></button>
    <button v-for="s in statusOptions" :key="s" class="bomx-status-tab" :class="{active: filterStatus===s}" @click="filterStatus=s">{{ s }} <span class="bomx-tab-count">{{ countByStatus(s) }}</span></button>
  </div>

  <!-- ══════════ TOOLBAR ══════════ -->
  <div class="bomx-toolbar">
    <div class="bomx-search-wrap">
      <span v-html="icon('search',14)"></span>
      <input v-model="search" type="text" placeholder="Search by WO number, item…"/>
    </div>
    <span class="bomx-toolbar-count">{{ sorted.length }} order{{ sorted.length===1?'':'s' }}</span>
    <div style="flex:1"></div>
    <button class="bomx-btn bomx-btn-mfg" @click="openAdd"><span v-html="icon('plus',13)"></span> New Work Order</button>
  </div>

  <!-- ══════════ WORK ORDER TABLE ══════════ -->
  <div class="bomx-table-wrap">
    <template v-if="loading">
      <div style="padding:16px">
        <div v-for="n in 6" :key="n" class="shimmer" style="height:34px;border-radius:6px;margin-bottom:8px"></div>
      </div>
    </template>
    <div v-else-if="!sorted.length" class="bomx-list-empty" style="padding:56px 20px">
      <div style="font-size:38px;margin-bottom:10px">🏗️</div>
      No Work Orders found.
      <div style="margin-top:14px"><button class="bomx-btn bomx-btn-mfg" @click="openAdd"><span v-html="icon('plus',13)"></span> Create Work Order</button></div>
    </div>
    <table v-else class="bomx-table">
      <thead>
        <tr>
          <th>WO Number</th>
          <th>Item</th>
          <th>BOM</th>
          <th style="text-align:right">Qty Ordered</th>
          <th style="text-align:right">Qty Produced</th>
          <th>Planned Start</th>
          <th>Planned End</th>
          <th>Status</th>
          <th>Progress</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in sorted" :key="row.name" class="bomx-wo-row" @click="selectWorkOrder(row.name)">
          <td class="mono" style="font-weight:700;color:var(--bx-mfgB)">{{ row.name }}</td>
          <td>
            <div style="font-weight:600">{{ row.item_name || row.production_item }}</div>
            <div style="font-size:11.5px;color:var(--bx-muted)">{{ row.production_item }}</div>
          </td>
          <td class="mono" style="font-size:12px;color:var(--bx-muted)">{{ row.bom || '—' }}</td>
          <td style="text-align:right;font-weight:700;white-space:nowrap">{{ fmtNum(row.qty) }} <span style="font-weight:400;color:var(--bx-muted);font-size:12px">{{ row.stock_uom }}</span></td>
          <td style="text-align:right;white-space:nowrap">{{ fmtNum(row.produced_qty) }} <span style="color:var(--bx-muted);font-size:12px">{{ row.stock_uom }}</span></td>
          <td style="font-size:12.5px;color:var(--bx-muted);white-space:nowrap">{{ fmtDate(row.planned_start_date) }}</td>
          <td style="white-space:nowrap">
            <span :style="isOverdue(row) ? 'color:var(--bx-red);font-weight:700' : 'color:var(--bx-muted)'" style="font-size:12.5px">{{ fmtDate(row.planned_end_date) }}<span v-if="isOverdue(row)"> ▲</span></span>
          </td>
          <td><span class="bomx-badge" :class="statusClass(row)">{{ row.status }}</span></td>
          <td>
            <div style="display:flex;align-items:center;gap:8px">
              <div class="bomx-prog-bar"><div class="bomx-prog-fill" :style="{width: progressPctnew(row)+'%', background: progressColor(row)}"></div></div>
              <span style="font-size:11.5px;font-weight:700;color:var(--bx-muted);white-space:nowrap">{{ progressPctnew(row) }}%</span>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- ══════════ DRAWER: WORK ORDER DETAIL ══════════ -->
  <div v-if="selectedName" class="bomx-overlay" @click.self="goBackToList">
    <div class="bomx-drawer">

        <div v-if="loading" class="bomx-empty-state"><div class="shimmer" style="height:200px;border-radius:10px"></div></div>

        <template v-else>
          <!-- Header -->
          <div class="bomx-detail-hdr">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap">
              <div style="min-width:0">
                <div class="bomx-detail-title">{{ isNew ? 'New Work Order' : (wo.item_name || wo.name) }}</div>
                <div class="bomx-detail-meta">
                  <span class="mono" v-if="!isNew">{{ wo.name }}</span>
                  <span v-if="!isNew">•</span>
                  <span class="bomx-badge" :class="statusClass(wo)" style="font-size:11px" v-if="!isNew">{{ wo.status }}</span>
                </div>
              </div>
              <div style="display:flex;gap:6px;flex-shrink:0;flex-wrap:wrap;justify-content:flex-end">
                <button class="bomx-btn bomx-btn-ghost-inv" @click="goBackToList" :disabled="saving || submitting">Back</button>
                <button v-if="!isNew && wo.docstatus===2 && !amendedInto" class="bomx-btn bomx-btn-light" @click="amendWO" :disabled="submitting">
                  {{ submitting ? 'Amending…' : 'Amend' }}
                </button>
                <button v-if="!isNew && wo.docstatus===2 && amendedInto" class="bomx-btn bomx-btn-light" @click="router.push('/manufacturing/work-order/' + amendedInto)">
                  View Amended {{ amendedInto }}
                </button>
                <button v-if="!isNew && wo.docstatus===1 && flt(wo.produced_qty)===0" class="bomx-btn" style="background:var(--bx-redS);color:var(--bx-red)" @click="cancelWO" :disabled="submitting">
                  {{ submitting ? 'Cancelling…' : 'Cancel Work Order' }}
                </button>
                <button v-if="!isNew && wo.docstatus===1 && bomType==='Packing' && wo.status!=='Completed' && wo.status!=='Cancelled'" class="bomx-btn" style="background:var(--bx-blueS);color:var(--bx-blue)" @click="createPackingSlip" :disabled="actionLoading==='ps'">
                  {{ actionLoading === 'ps' ? 'Creating…' : 'Create Packing Slip' }}
                </button>
                <button v-if="!isNew && wo.docstatus===1 && wo.status!=='Stopped' && wo.status!=='Completed'" class="bomx-btn" style="background:var(--bx-amberS);color:var(--bx-amber)" @click="stopWO" :disabled="submitting">
                  {{ submitting ? 'Stopping…' : 'Stop' }}
                </button>
                <button v-if="!isNew && wo.docstatus===1 && wo.status==='Stopped'" class="bomx-btn" style="background:var(--bx-greenS);color:var(--bx-green)" @click="resumeWO" :disabled="submitting">
                  {{ submitting ? 'Resuming…' : 'Resume' }}
                </button>
                <button v-if="!isNew && wo.docstatus===0" class="bomx-btn bomx-btn-light" @click="submitWO" :disabled="submitting || saving">
                  {{ submitting ? 'Submitting…' : 'Submit' }}
                </button>
                <button v-if="!readOnly || (wo.docstatus===1 && (warehousesEditable || operatingCostEditable))" class="bomx-btn bomx-btn-light" @click="save" :disabled="saving || loading">
                  {{ saving ? 'Saving…' : (isNew ? 'Save Work Order' : (readOnly ? 'Save Changes' : 'Save Changes')) }}
                </button>
              </div>
            </div>
          </div>

          <!-- Status Pipeline -->
          <div class="bomx-status-pipe" v-if="!isNew">
            <template v-for="(step, i) in pipelineSteps" :key="step.key">
              <div class="bomx-sp-wrap">
                <div class="bomx-sp-dot" :class="pipelineDotClass(step)">
                  <svg v-if="pipelineStepDone(step)" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
                  <span v-else>{{ i + 1 }}</span>
                </div>
                <div class="bomx-sp-label" :class="{'bomx-sp-label--active': pipelineStepActive(step)}">{{ step.label }}</div>
              </div>
              <div class="bomx-sp-line" v-if="i < pipelineSteps.length - 1" :class="{'bomx-sp-line--done': pipelineStepDone(step)}"></div>
            </template>
          </div>

          <!-- Tabs -->
          <div class="bomx-tabs">
            <button v-for="t in tabs" :key="t.id" class="bomx-tab" :class="{'bomx-tab--active': activeTab===t.id}" @click="activeTab=t.id">{{ t.label }}</button>
          </div>

          <div class="bomx-body">

            <!-- ── TAB: Work Order ── -->
            <template v-if="activeTab==='details'">
              <div class="bomx-section-lbl">Production Item &amp; BOM</div>
              <div class="bomx-hdr-fields bomx-hf-cols-2-1" style="padding:0;border:none;background:none;margin-bottom:8px">
                <div>
                  <div class="bomx-hf-label">Production Item</div>
                  <select class="bomx-fi" v-model="selectedProductionItem" @change="onProductionItemChange" :disabled="readOnly" style="width:100%">
                    <option value="">— Select Item —</option>
                    <option v-for="i in manufacturedItems" :key="i.name" :value="i.name">{{ i.item_name || i.name }}</option>
                  </select>
                  <div class="bomx-field-hint">Picking an item auto-suggests its BOM below — still overridable.</div>
                </div>
              </div>
              <div class="bomx-hdr-fields bomx-hf-cols-2-1" style="padding:0;border:none;background:none;margin-bottom:8px">
                <div>
                  <div class="bomx-hf-label">BOM <span style="color:var(--bx-red)">*</span></div>
                  <select class="bomx-fi" v-model="wo.bom" @change="onBomChange" :disabled="readOnly" style="width:100%">
                    <option value="">— Select Submitted BOM —</option>
                    <option v-for="b in filteredBomList" :key="b.name" :value="b.name">{{ b.name }} — {{ b.item_name || b.item }}</option>
                  </select>
                  <div class="bomx-field-hint" v-if="wo.item_name">Manufactures: <strong>{{ wo.item_name }}</strong> ({{ wo.stock_uom }})</div>
                  <div class="bomx-field-hint" style="color:var(--bx-amber);font-weight:600" v-if="warnBomNotDefault && wo.bom && selectedBomIsNotDefault">
                    ⚠ This isn't the default BOM for {{ wo.item_name || selectedProductionItem }}.
                  </div>
                </div>
                <div>
                  <div class="bomx-hf-label">Qty to Manufacture <span style="color:var(--bx-red)">*</span></div>
                  <input class="bomx-fi" type="number" v-model="wo.qty" min="0.01" step="any" :disabled="readOnly" style="width:100%"/>
                </div>
              </div>
              <div v-if="!readOnly && wo.bom" style="margin-bottom:20px">
                <button class="bomx-btn bomx-btn-light" style="color:var(--bx-mfgB);border:1px solid var(--bx-mfg)" @click="loadFromBom" :disabled="breakdownLoading">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
                  {{ breakdownLoading ? 'Loading…' : 'Load / Refresh Materials from BOM' }}
                </button>
                <div class="bomx-field-hint">Rescales raw materials &amp; operations from the BOM at the current qty. Overwrites any manual edits below.</div>
                <div v-if="materialsStale" class="bomx-field-hint" style="color:var(--bx-red);font-weight:600;margin-top:4px">
                  ⚠ Qty to Manufacture changed to {{ fmt(wo.qty) }} since materials were last loaded for {{ fmt(wo.items_loaded_for_qty) }}. Raw material quantities below are stale — click "Load / Refresh Materials from BOM" above before saving, or this Work Order will consume/cost the wrong amount of material when completed.
                </div>
              </div>

              <div class="bomx-section-lbl">Warehouses</div>
              <div class="bomx-hdr-fields bomx-hf-cols-1-1" style="padding:0;border:none;background:none;margin-bottom:20px">
                <div>
                  <div class="bomx-hf-label">Default Source Warehouse (Raw Materials) <span style="color:var(--bx-red)">*</span></div>
                  <select class="bomx-fi" v-model="wo.source_warehouse" :disabled="!warehousesEditable" style="width:100%">
                    <option value="">— Select —</option>
                    <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
                  </select>
                </div>
                <div>
                  <div class="bomx-hf-label">Work-in-Progress Warehouse</div>
                  <select class="bomx-fi" v-model="wo.wip_warehouse" :disabled="!warehousesEditable" style="width:100%">
                    <option value="">— None (consume from Source directly) —</option>
                    <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
                  </select>
                  <div class="bomx-field-hint">Optional. If set, use Issue Materials to stage raw materials here first.</div>
                </div>
                <div>
                  <div class="bomx-hf-label">Finished Goods Warehouse <span style="color:var(--bx-red)">*</span></div>
                  <select class="bomx-fi" v-model="wo.fg_warehouse" :disabled="readOnly" style="width:100%">
                    <option value="">— Select —</option>
                    <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
                  </select>
                </div>
                <div>
                  <div class="bomx-hf-label">Scrap / By-Product Warehouse</div>
                  <select class="bomx-fi" v-model="wo.scrap_warehouse" :disabled="readOnly" style="width:100%">
                    <option value="">— Defaults to Finished Goods Warehouse —</option>
                    <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
                  </select>
                </div>
              </div>

              <div class="bomx-section-lbl">Schedule</div>
              <div class="bomx-hdr-fields bomx-hf-cols-1-1" style="padding:0;border:none;background:none;margin-bottom:8px">
                <div>
                  <div class="bomx-hf-label">Planned Start Date</div>
                  <input class="bomx-fi" type="date" v-model="wo.planned_start_date" :disabled="readOnly" style="width:100%"/>
                </div>
                <div>
                  <div class="bomx-hf-label">Planned End Date</div>
                  <input class="bomx-fi" type="date" v-model="wo.planned_end_date" :disabled="readOnly" style="width:100%"/>
                </div>
              </div>
              <div v-if="totalPlannedOperationMinutes > 0" class="bomx-field-hint" style="margin-bottom:20px">
                Estimated {{ estimatedProductionDays.toFixed(1) }} working day(s) at {{ jobCardHoursPerDay }} hr/day
                (capacity planning window: {{ capacityPlanningForDays }} day(s)).
                <span v-if="capacityWindowExceeded" style="color:var(--bx-amber);font-weight:600">
                  ⚠ This exceeds the configured capacity planning window.
                </span>
                <button
                  v-if="!readOnly && wo.planned_start_date"
                  type="button"
                  class="bomx-btn bomx-btn-sm bomx-btn-light"
                  style="color:var(--bx-mfgB);border:1px solid var(--bx-mfg);margin-left:8px"
                  @click="suggestPlannedEndDate"
                >Suggest End Date</button>
              </div>

              <div class="bomx-section-lbl" style="display:flex;align-items:center;justify-content:space-between">
                <span>Raw Materials <span class="bomx-count" v-if="wo.items && wo.items.length">({{ wo.items.length }})</span></span>
                <div style="display:flex;gap:6px">
                  <button v-if="!isNew && wo.items && wo.items.length && (wo.docstatus===0 || (wo.docstatus===1 && wo.status!=='Completed'))" type="button" class="bomx-btn bomx-btn-sm bomx-btn-light" style="color:var(--bx-mfgB);border:1px solid var(--bx-mfg)" @click="printWorkOrder" title="Print Work Order">
                    <span v-html="icon('printer',12)"></span> Print
                  </button>
                  <button v-if="!readOnly" class="bomx-btn bomx-btn-sm bomx-btn-light" style="color:var(--bx-mfgB);border:1px solid var(--bx-mfg)" @click="addMaterial">+ Add Row</button>
                </div>
              </div>
              <div class="bomx-rm-cards">
                <div v-if="!wo.items || !wo.items.length" class="bomx-tree-empty">No raw materials yet. Select a BOM and click "Load / Refresh Materials from BOM".</div>
                <div class="bomx-rm-card" v-for="(rm, idx) in wo.items" :key="idx">
                  <div class="bomx-rm-card-hdr">
                    <span class="bomx-tree-icon">📦</span>
                    <span class="bomx-rm-card-title" style="font-weight:600">{{ rm.item_code || 'New Row' }}</span>
                    <span v-if="rm.is_substituted" class="bomx-badge" style="background:#eef2ff;color:#4338ca;font-size:10px" :title="'Substituted from ' + rm.original_item_code">Substituted</span>
                    <div style="flex:1"></div>
                    <button v-if="readOnly && wo.docstatus===1 && !flt(rm.consumed_qty) && rm.name" class="bomx-btn bomx-btn-sm bomx-btn-light" style="color:var(--bx-mfgB);border:1px solid var(--bx-mfg)" @click="openSubstitute(rm)" title="Substitute this material">Substitute</button>
                    <button v-if="!readOnly" class="bomx-btn-icon danger bomx-rm-card-rm" @click="removeMaterial(idx)" title="Remove">
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                  </div>
                  <div class="bomx-rm-card-body bomx-rm-card-body-3col">
                    <div class="bomx-rm-field bomx-rm-field-wide">
                      <label>Item Code</label>
                      <select class="bomx-fi" v-model="rm.item_code" :disabled="readOnly">
                        <option value="">— Select —</option>
                        <option v-for="i in rawMaterialItems" :key="i.name" :value="i.name">{{ i.item_name || i.name }}</option>
                      </select>
                    </div>
                    <div class="bomx-rm-field">
                      <label>Required Qty</label>
                      <input class="bomx-fi bomx-fi-mono" type="number" v-model="rm.required_qty" min="0" step="any" :disabled="readOnly"/>
                    </div>
                    <div class="bomx-rm-field">
                      <label>Source Warehouse</label>
                      <select class="bomx-fi" v-model="rm.source_warehouse" :disabled="!warehousesEditable">
                        <option value="">— Use Default —</option>
                        <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
                      </select>
                    </div>
                    <div class="bomx-rm-field">
                      <label>Transferred</label>
                      <div class="bomx-rm-static">{{ fmt(rm.transferred_qty) }}</div>
                    </div>
                    <div class="bomx-rm-field">
                      <label>Consumed</label>
                      <div class="bomx-rm-static">{{ fmt(rm.consumed_qty) }}</div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="bomx-section-lbl" style="display:flex;align-items:center;justify-content:space-between;margin-top:22px">
                <span>Operations <span class="bomx-count" v-if="wo.operations && wo.operations.length">({{ wo.operations.length }})</span></span>
                <button v-if="!readOnly" class="bomx-btn bomx-btn-sm bomx-btn-light" style="color:var(--bx-mfgB);border:1px solid var(--bx-mfg)" @click="addOp">+ Add Operation</button>
              </div>
              <div class="bomx-rm-cards">
                <div v-if="!wo.operations || !wo.operations.length" class="bomx-tree-empty">No operations yet.</div>
                <div class="bomx-rm-card" v-for="(op, idx) in wo.operations" :key="idx">
                  <div class="bomx-rm-card-hdr">
                    <span class="bomx-tree-icon">⚙️</span>
                    <span class="bomx-rm-card-title" style="font-weight:600">{{ op.operation || 'New Operation' }}</span>
                    <div style="flex:1"></div>
                    <template v-if="!isNew && op.operation">
                      <span v-for="jc in jobCardsFor(op)" :key="jc.name" class="bomx-badge"
                            style="cursor:pointer" :class="jc.status==='Completed' ? 'badge-active' : (jc.status==='Cancelled' ? 'badge-obsolete' : 'badge-wip')"
                            :title="jc.name" @click="router.push('/manufacturing/job-card/' + jc.name)">{{ jc.status || 'Open' }}</span>
                      <button v-if="!jobCardsFor(op).length" class="bomx-btn bomx-btn-sm bomx-btn-light" style="color:var(--bx-mfgB);border:1px solid var(--bx-mfg)" @click="createJobCardFor(op)">+ Job Card</button>
                    </template>
                    <button v-if="!readOnly" class="bomx-btn-icon danger bomx-rm-card-rm" @click="removeOp(idx)" title="Remove">
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                  </div>
                  <div class="bomx-rm-card-body" style="grid-template-columns:1fr 1fr">
                    <div class="bomx-rm-field">
                      <label>Operation</label>
                      <select class="bomx-fi" v-model="op.operation" :disabled="readOnly">
                        <option value="">— Select —</option>
                        <option v-for="o in operationsList" :key="o.name" :value="o.name">{{ o.name }}</option>
                      </select>
                    </div>
                    <div class="bomx-rm-field">
                      <label>Workstation</label>
                      <select class="bomx-fi" v-model="op.workstation" :disabled="readOnly">
                        <option value="">— Select —</option>
                        <option v-for="w in workstationsList" :key="w.name" :value="w.name">{{ w.name }}</option>
                      </select>
                    </div>
                    <div class="bomx-rm-field">
                      <label>Planned (Mins)</label>
                      <input class="bomx-fi bomx-fi-mono" type="number" v-model="op.planned_time_in_mins" min="0" step="any" :disabled="readOnly"/>
                    </div>
                    <div class="bomx-rm-field" v-if="!isNew">
                      <label>Actual (Mins)</label>
                      <input class="bomx-fi bomx-fi-mono" type="number" :value="fmt(op.actual_time_in_mins)" disabled
                        :style="flt(op.actual_time_in_mins) > flt(op.planned_time_in_mins) && flt(op.planned_time_in_mins) > 0 ? 'color:var(--bx-red);font-weight:600;' : ''"
                        title="Rolled up from Job Card time logs for this operation"/>
                    </div>
                    <div class="bomx-rm-field">
                      <label>Status</label>
                      <select class="bomx-fi" v-model="op.status" :disabled="readOnly">
                        <option>Pending</option><option>In Process</option><option>Completed</option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>

              <div class="bomx-section-lbl" style="margin-top:22px;display:flex;align-items:center;justify-content:space-between">
                <span>Operation Cost</span>
                <button
                  v-if="!isNew"
                  type="button"
                  class="bomx-btn bomx-btn-sm bomx-btn-light"
                  style="color:var(--bx-mfgB);border:1px solid var(--bx-mfg)"
                  @click="recalcOperatingCost(false)"
                  :disabled="recalcLoading"
                >{{ recalcLoading ? 'Recalculating…' : 'Recalculate' }}</button>
              </div>
              <div
                v-if="!isNew && !recalcLoading && flt(wo.planned_operating_cost) === 0 && wo.operations && wo.operations.length && totalPlannedOperationMinutes > 0"
                class="bomx-field-hint"
                style="color:var(--bx-amber);margin-bottom:8px"
              >
                ⚠ Planned Operating Cost is ₹0.00 despite planned time being set — the Operations table likely has no Hour Rate
                stored (captured as 0 when this was last loaded from the BOM). Click Recalculate to
                <button type="button" class="bomx-btn-link" style="border:none;background:none;color:var(--bx-mfgB);text-decoration:underline;cursor:pointer;padding:0;font:inherit" @click="recalcOperatingCost(true)">re-pull current Workstation hour rates</button>
                and resync.
              </div>
              <div class="bomx-hdr-fields bomx-hf-cols-1-1" style="padding:0;border:none;background:none;margin-bottom:8px">
                <div>
                  <div class="bomx-hf-label">Planned Operating Cost</div>
                  <div class="bomx-rm-static" >₹ {{ fmt(wo.planned_operating_cost) }}</div>
                </div>
                <div>
                  <div class="bomx-hf-label">Actual Operating Cost</div>
                  <div class="bomx-rm-static" >₹ {{ fmt(wo.actual_operating_cost) }}</div>
                </div>
                <div>
                  <div class="bomx-hf-label">Additional Operating Cost</div>
                  <input class="bomx-fi bomx-fi-mono" type="number" v-model="wo.additional_operating_cost" min="0" step="any" :disabled="!operatingCostEditable"/>
                </div>
                <div>
                  <div class="bomx-hf-label">Total Operating Cost</div>
                  <div class="bomx-rm-static" style="font-weight:700">₹ {{ fmt(totalOperatingCostPreview) }}</div>
                </div>
              </div>
            </template>

            <!-- ── TAB: Production ── -->
            <template v-if="activeTab==='production'">
              <div v-if="isNew" class="bomx-tree-empty">Save and submit the Work Order first to begin production.</div>
              <template v-else>
                <div class="bomx-prod-card">
                  <div style="display:flex;align-items:center;justify-content:space-between;gap:12px">
                    <div>
                      <div class="bomx-section-lbl" style="margin-bottom:2px">Production Progress</div>
                      <div style="font-size:12.5px;color:var(--bx-muted)">{{ fmt(wo.produced_qty) }} of {{ fmt(wo.qty) }} {{ wo.stock_uom }} produced</div>
                    </div>
                    <div style="font-size:20px;font-weight:800;color:var(--bx-mfgB)">{{ progressPct }}%</div>
                  </div>
                  <div style="height:8px;background:#e5e7eb;border-radius:6px;overflow:hidden;margin-top:12px">
                    <div :style="{width: progressPct+'%'}" style="height:100%;background:linear-gradient(135deg,var(--bx-mfgL),var(--bx-mfg))"></div>
                  </div>
                  <div style="display:flex;gap:24px;margin-top:16px">
                    <div><div style="font-size:11px;color:var(--bx-muted);text-transform:uppercase;font-weight:600">Remaining</div><div style="font-size:16px;font-weight:700">{{ fmt(remainingQty) }}</div></div>
                    <div><div style="font-size:11px;color:var(--bx-red);text-transform:uppercase;font-weight:600">Process Loss</div><div style="font-size:16px;font-weight:700;color:var(--bx-red)">{{ fmt(wo.process_loss_qty) }}</div></div>
                  </div>
                </div>

                <div class="bomx-prod-card" v-if="wo.docstatus===1">
                  <div class="bomx-section-lbl">Actions</div>
                  <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:8px">
                    <button v-if="wo.wip_warehouse" class="bomx-btn bomx-btn-mfg" @click="issueMaterials" :disabled="actionLoading || allTransferred || wo.status==='Stopped'">
                      {{ actionLoading==='issue' ? 'Issuing…' : (allTransferred ? 'Materials Issued' : 'Issue Materials to WIP') }}
                    </button>
                    <button v-if="bomType!=='Packing'" class="bomx-btn" style="background:var(--bx-green);color:#fff" @click="openCompleteModal" :disabled="!canCompleteMore || wo.status==='Stopped'">
                      Complete Work Order
                    </button>
                  </div>
                  <div class="bomx-field-hint" v-if="bomType==='Packing'" style="margin-top:8px">This Work Order uses a Packing BOM — complete it via a Packing Slip instead (see above).</div>
                  <div class="bomx-field-hint" v-else-if="wo.status==='Stopped'" style="color:var(--bx-amber);margin-top:8px">Work Order is stopped — resume it to continue production.</div>
                  <div class="bomx-field-hint" v-else-if="!canCompleteMore" style="margin-top:8px">Fully produced — no further completions possible.</div>
                </div>

                <div class="bomx-prod-card" v-if="bomType!=='Packing' && (sourcedPackingSlips.length || sourcedPsLoading)">
                  <div style="display:flex;align-items:center;justify-content:space-between">
                    <div class="bomx-section-lbl" style="margin-bottom:0">Packed Via</div>
                    <button class="bomx-btn bomx-btn-sm bomx-btn-light" style="color:var(--bx-mfgB);border:1px solid var(--bx-mfg)" @click="loadReconciliation" :disabled="reconLoading">
                      {{ reconLoading ? 'Checking…' : (reconciliation ? 'Refresh Reconciliation' : 'Check Reconciliation') }}
                    </button>
                  </div>
                  <div v-if="sourcedPsLoading" class="bomx-field-hint" style="margin-top:8px">Loading…</div>
                  <div v-else style="display:flex;flex-direction:column;gap:8px;margin-top:8px">
                    <div v-for="ps in sourcedPackingSlips" :key="ps.name" style="display:flex;align-items:center;justify-content:space-between;gap:8px">
                      <div>
                        <span class="bomx-link" @click="router.push(`/manufacturing/packing-slip/${ps.name}`)">{{ ps.name }}</span>
                        <span style="color:var(--bx-muted);font-size:12px;margin-left:8px">{{ fmt(ps.qty_to_pack) }} packed</span>
                      </div>
                      <span class="bomx-badge" :class="statusClass({status: ps.status})" style="font-size:11px">{{ ps.status }}</span>
                    </div>
                  </div>

                  <!-- Phase 6: Bulk → Packed reconciliation -->
                  <div v-if="reconciliation" style="margin-top:14px;padding-top:12px;border-top:1px dashed var(--bx-border)">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
                      <span class="bomx-badge" :style="reconStatusStyle(reconciliation.status)">{{ reconStatusLabel(reconciliation.status) }}</span>
                      <span style="color:var(--bx-muted);font-size:12px">{{ reconciliation.bulk_item_name }} in {{ reconciliation.fg_warehouse }}</span>
                    </div>
                    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">
                      <div class="bomx-recon-cell">
                        <div class="bomx-recon-lbl">Produced</div>
                        <div class="bomx-recon-val">{{ fmt(reconciliation.bulk_qty_produced) }}</div>
                      </div>
                      <div class="bomx-recon-cell">
                        <div class="bomx-recon-lbl">Consumed (posted)</div>
                        <div class="bomx-recon-val">{{ fmt(reconciliation.bulk_qty_consumed_posted) }}</div>
                      </div>
                      <div class="bomx-recon-cell">
                        <div class="bomx-recon-lbl">Reserved (unposted)</div>
                        <div class="bomx-recon-val">{{ fmt(reconciliation.bulk_qty_reserved_unposted) }}</div>
                      </div>
                      <div class="bomx-recon-cell">
                        <div class="bomx-recon-lbl">Remaining in Warehouse</div>
                        <div class="bomx-recon-val">{{ fmt(reconciliation.bulk_qty_remaining_in_warehouse) }}</div>
                      </div>
                    </div>
                    <div class="bomx-field-hint" style="margin-top:8px" v-if="reconciliation.status!=='reconciled'">
                      {{ fmt(Math.abs(reconciliation.bulk_qty_unaccounted)) }} units {{ reconciliation.status==='shortage' ? 'unaccounted for' : 'more in the warehouse than were ever produced' }} — check for stock movements against {{ reconciliation.bulk_item }} outside this Work Order's Packing Slip chain.
                    </div>
                  </div>
                </div>

                <div class="bomx-prod-card" v-if="qcInspections.length || qcLoading">
                  <div style="display:flex;align-items:center;justify-content:space-between">
                    <div class="bomx-section-lbl" style="margin-bottom:0">Quality Inspections</div>
                    <button class="bomx-btn bomx-btn-sm bomx-btn-light" style="color:var(--bx-mfgB);border:1px solid var(--bx-mfg)" @click="loadQcInspections" :disabled="qcLoading">Refresh</button>
                  </div>
                  <div v-if="qcSummary" style="display:flex;align-items:center;gap:10px;margin-top:10px">
                    <span
                      class="bomx-badge"
                      :style="qcSummary.overall==='Fail' ? 'background:var(--bx-redS);color:var(--bx-red)' : (qcSummary.overall==='Pending' ? 'background:var(--bx-amberS);color:var(--bx-amber)' : 'background:var(--bx-greenS);color:var(--bx-green)')">
                      {{ qcSummary.overall==='Fail' ? 'QC Failed' : (qcSummary.overall==='Pending' ? 'QC Pending' : 'QC Passed') }}
                    </span>
                    <span style="font-size:12px;color:var(--bx-muted)">
                      {{ qcSummary.pass }} passed · {{ qcSummary.pending }} pending · {{ qcSummary.fail }} failed
                    </span>
                  </div>
                  <div class="bomx-field-hint" v-if="qcSummary && qcSummary.overall!=='Pass'" style="color:var(--bx-amber);margin-top:8px">
                    {{ qcSummary.overall==='Fail' ? 'One or more produced batches failed inspection — review before dispatch.' : 'Finished-good inspection is still pending for this Work Order.' }}
                  </div>
                  <div class="bomx-rm-cards" style="margin-top:10px" v-if="qcInspections.length">
                    <div class="bomx-rm-card" v-for="qi in qcInspections" :key="qi.name" style="cursor:pointer" @click="router.push('/quality/inspections?open=' + qi.name)">
                      <div class="bomx-rm-card-hdr">
                        <span class="bomx-tree-icon">🔬</span>
                        <span class="bomx-rm-card-title mono" style="font-weight:600">{{ qi.name }}</span>
                        <span class="bomx-badge" :style="qi.status==='Fail' ? 'background:var(--bx-redS);color:var(--bx-red)' : (qi.status==='Pass' ? 'background:var(--bx-greenS);color:var(--bx-green)' : 'background:var(--bx-amberS);color:var(--bx-amber)')">{{ qi.docstatus===0 ? 'Pending' : qi.status }}</span>
                      </div>
                      <div class="bomx-rm-card-body" style="grid-template-columns:1fr 1fr">
                        <div class="bomx-rm-field"><label>Item</label><div class="bomx-rm-static">{{ qi.item_name || qi.item }}</div></div>
                        <div class="bomx-rm-field"><label>Date</label><div class="bomx-rm-static">{{ fmtDate(qi.inspection_date) }}</div></div>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="bomx-prod-card">
                  <div style="display:flex;align-items:center;justify-content:space-between">
                    <div class="bomx-section-lbl" style="margin-bottom:0">Job Cards</div>
                    <button class="bomx-btn bomx-btn-sm bomx-btn-light" style="color:var(--bx-mfgB);border:1px solid var(--bx-mfg)" @click="loadJobCards" :disabled="jcLoading">Refresh</button>
                  </div>
                  <div class="bomx-rm-cards" style="margin-top:10px" v-if="jobCards.length">
                    <div class="bomx-rm-card" v-for="jc in jobCards" :key="jc.name" style="cursor:pointer" @click="router.push('/manufacturing/job-card/' + jc.name)">
                      <div class="bomx-rm-card-hdr">
                        <span class="bomx-tree-icon">🗂️</span>
                        <span class="bomx-rm-card-title mono" style="font-weight:600">{{ jc.name }}</span>
                        <span class="bomx-badge" :class="jc.status==='Completed' ? 'badge-active' : (jc.status==='Cancelled' ? 'badge-obsolete' : 'badge-wip')">{{ jc.status || 'Open' }}</span>
                      </div>
                      <div class="bomx-rm-card-body" style="grid-template-columns:1fr 1fr">
                        <div class="bomx-rm-field"><label>Operation</label><div class="bomx-rm-static">{{ jc.operation }}</div></div>
                        <div class="bomx-rm-field"><label>Workstation</label><div class="bomx-rm-static">{{ jc.workstation || '—' }}</div></div>
                      </div>
                    </div>
                  </div>
                  <div v-else class="bomx-tree-empty">No Job Cards created for this Work Order yet.</div>
                </div>

                <div class="bomx-prod-card">
                  <div style="display:flex;align-items:center;justify-content:space-between">
                    <div class="bomx-section-lbl" style="margin-bottom:0">Linked Stock Entries</div>
                    <button class="bomx-btn bomx-btn-sm bomx-btn-light" style="color:var(--bx-mfgB);border:1px solid var(--bx-mfg)" @click="loadStockEntries" :disabled="seLoading">Refresh</button>
                  </div>
                  <div class="bomx-rm-cards" style="margin-top:10px" v-if="stockEntries.length">
                    <div class="bomx-rm-card" v-for="se in stockEntries" :key="se.name" style="cursor:pointer" @click="router.push('/inventory/stock-entries')">
                      <div class="bomx-rm-card-hdr">
                        <span class="bomx-tree-icon">📄</span>
                        <span class="bomx-rm-card-title mono" style="font-weight:600">{{ se.name }}</span>
                        <span class="bomx-badge" :class="se.docstatus===1?'badge-active':(se.docstatus===2?'badge-cancelled':'badge-obsolete')">{{ se.docstatus===1 ? 'Submitted' : (se.docstatus===2 ? 'Cancelled' : 'Draft') }}</span>
                      </div>
                      <div class="bomx-rm-card-body" style="grid-template-columns:1fr 1fr">
                        <div class="bomx-rm-field"><label>Type</label><div class="bomx-rm-static">{{ se.stock_entry_type }}</div></div>
                        <div class="bomx-rm-field"><label>Date</label><div class="bomx-rm-static">{{ fmtDate(se.posting_date) }}</div></div>
                      </div>
                    </div>
                  </div>
                  <div v-else class="bomx-tree-empty">No Stock Entries posted against this Work Order yet.</div>
                </div>
              </template>
            </template>

            <!-- ── TAB: More Information ── -->
            <template v-if="activeTab==='more'">
              <div class="bomx-section-lbl">More Information</div>

              <div class="bomx-cost-card">
                <div class="bomx-cost-card-hdr">
                  <span>Cost Breakdown</span>
                  <span class="bomx-cost-total-pill">₹ {{ fmt(totalWorkOrderCost) }}</span>
                </div>
                <div class="bomx-cost-card-body">
                  <div class="bomx-cost-item">
                    <div class="bomx-cost-item-lbl">
                      <span class="bomx-cost-dot" style="background:var(--bx-mfg)"></span>Raw Material Cost
                    </div>
                    <div class="bomx-cost-item-val">₹ {{ fmt(rawMaterialCost) }}</div>
                  </div>
                  <div class="bomx-cost-plus">+</div>
                  <div class="bomx-cost-item">
                    <div class="bomx-cost-item-lbl">
                      <span class="bomx-cost-dot" style="background:var(--bx-violet)"></span>Operation Cost
                    </div>
                    <div class="bomx-cost-item-val">₹ {{ fmt(totalOperatingCostPreview) }}</div>
                  </div>
                  <div class="bomx-cost-eq">=</div>
                  <div class="bomx-cost-item bomx-cost-item--total">
                    <div class="bomx-cost-item-lbl">Total Cost (Planned)</div>
                    <div class="bomx-cost-item-val bomx-cost-item-val--total">₹ {{ fmt(totalWorkOrderCost) }}</div>
                  </div>
                  <div class="bomx-cost-item bomx-cost-item--total" v-if="actualAbsorbedCost !== null" style="margin-top:6px">
                    <div class="bomx-cost-item-lbl" title="Actual cost posted into finished-good stock across every completion recorded so far, from the Manufacture Stock Entries (raw material + operating cost, net of scrap credit) -- not the BOM-load-time snapshot above.">Total Cost (Actual)</div>
                    <div class="bomx-cost-item-val bomx-cost-item-val--total">₹ {{ fmt(actualAbsorbedCost) }}</div>
                  </div>
                </div>
              </div>

              <div class="bomx-hdr-fields bomx-hf-cols-1" style="padding:0;border:none;background:none;margin-bottom:20px">
                <div>
                  <div class="bomx-hf-label">Sales Order</div>
                  <select class="bomx-fi" v-model="wo.sales_order" :disabled="readOnly" style="width:100%">
                    <option value="">— Select —</option>
                    <option v-for="s in salesOrdersList" :key="s.name" :value="s.name">{{ s.name }}</option>
                  </select>
                </div>
              </div>
              <div class="bomx-section-lbl">Remarks</div>
              <textarea class="bomx-fi" v-model="wo.remarks" rows="3" :disabled="readOnly" style="width:100%;min-height:90px;resize:vertical"></textarea>
            </template>

          </div>
        </template>
    </div>
  </div>

  <!-- Complete Work Order Modal -->
  <div v-if="showCompleteModal" class="bomx-modal-overlay" @click.self="closeCompleteModal">
    <div class="bomx-modal" style="width:560px;max-width:94vw">
      <div class="bomx-modal-title">Complete Work Order</div>
      <div class="bomx-modal-body">
        <div class="bomx-hdr-fields bomx-hf-cols-1-1" style="padding:0;border:none;background:none;margin-bottom:14px">
          <div>
            <div class="bomx-hf-label">Qty Manufactured <span style="color:var(--bx-red)">*</span></div>
            <input class="bomx-fi" type="number" v-model="completeForm.qty_manufactured" min="0.01" :max="maxCompletableQty" step="any" style="width:100%" :style="qtyManufacturedError ? 'border-color:var(--bx-red)' : ''"/>
            <div class="bomx-field-hint">Remaining planned qty: {{ fmt(remainingQty) }}<span v-if="overProductionAllowancePct>0"> · up to {{ fmt(maxCompletableQty) }} allowed with the {{ overProductionAllowancePct }}% over-production allowance</span></div>
            <div v-if="qtyManufacturedError" class="bomx-field-hint" style="color:var(--bx-red)">{{ qtyManufacturedError }}</div>
          </div>
          <div>
            <div class="bomx-hf-label">Process Loss / Wastage Qty</div>
            <input class="bomx-fi" type="number" v-model="completeForm.process_loss_qty" min="0" step="any" style="width:100%"/>
          </div>
        </div>
        <template v-if="productionItemHasBatch">
          <div class="bomx-hdr-fields bomx-hf-cols-1-1" style="padding:0;border:none;background:none;margin-bottom:14px">
            <div>
              <div class="bomx-hf-label">Batch No</div>
              <input class="bomx-fi" type="text" v-model="completeForm.batch_no" placeholder="Leave blank to auto-generate" style="width:100%"/>
            </div>
            <div>
              <div class="bomx-hf-label">Manufacturing Date</div>
              <input class="bomx-fi" type="date" v-model="completeForm.manufacturing_date" style="width:100%"/>
            </div>
          </div>
          <div style="margin-bottom:14px">
            <div class="bomx-hf-label">Expiry Date</div>
            <input class="bomx-fi" type="date" v-model="completeForm.expiry_date" style="width:100%"/>
            <div class="bomx-field-hint">Leave blank to auto-calculate from the item's shelf life.</div>
          </div>
        </template>

        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
          <span class="bomx-hf-label" style="margin:0">Recoverable Scrap / By-Products</span>
          <button class="bomx-btn bomx-btn-sm bomx-btn-light" style="color:var(--bx-mfgB);border:1px solid var(--bx-mfg)" @click="addCompleteScrap">+ Add</button>
        </div>
        <div class="bomx-rm-cards" style="margin-bottom:8px" v-if="completeForm.scrap_items.length">
          <div class="bomx-rm-card" v-for="(s, idx) in completeForm.scrap_items" :key="idx">
            <div class="bomx-rm-card-body bomx-rm-card-body-2-1-auto">
              <div class="bomx-rm-field">
                <label>Item</label>
                <select class="bomx-fi" v-model="s.item_code">
                  <option value="">— Select Item —</option>
                  <option v-for="i in stockItems" :key="i.name" :value="i.name">{{ i.item_name || i.name }}</option>
                </select>
              </div>
              <div class="bomx-rm-field">
                <label>Qty</label>
                <input class="bomx-fi bomx-fi-mono" type="number" v-model="s.qty" min="0" step="any"/>
              </div>
              <button class="bomx-btn-icon danger" @click="completeForm.scrap_items.splice(idx,1)" title="Remove">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
          </div>
        </div>
      </div>
      <div class="bomx-modal-actions">
        <button class="bomx-btn" style="background:#fff;border:1px solid var(--bx-border)" @click="closeCompleteModal" :disabled="actionLoading">Cancel</button>
        <button class="bomx-btn bomx-btn-mfg" @click="submitComplete" :disabled="actionLoading || !!qtyManufacturedError">
          {{ actionLoading==='complete' ? 'Completing…' : 'Complete' }}
        </button>
      </div>
    </div>
  </div>

  <!-- Substitute Material Modal -->
  <div v-if="showSubstituteModal" class="bomx-modal-overlay" @click.self="closeSubstituteModal">
    <div class="bomx-modal" style="width:520px;max-width:94vw">
      <div class="bomx-modal-title">Substitute Material</div>
      <div class="bomx-modal-body">
        <div style="margin-bottom:14px">
          <div class="bomx-hf-label">Original Item</div>
          <div class="bomx-rm-static">{{ substituteRow && substituteRow.item_code }}</div>
        </div>
        <div v-if="substituteLoading" class="bomx-tree-empty">Loading alternatives…</div>
        <div v-else-if="!substituteOptions.length" class="bomx-tree-empty">
          No Alternative Items are defined for this item. Add one under Manufacturing → Alternative Items first.
        </div>
        <template v-else>
          <div style="margin-bottom:14px">
            <div class="bomx-hf-label">Alternative Item <span style="color:var(--bx-red)">*</span></div>
            <select class="bomx-fi" v-model="substituteForm.alternative_item_code" style="width:100%">
              <option value="">— Select —</option>
              <option v-for="o in substituteOptions" :key="o.alternative_item_code" :value="o.alternative_item_code">
                {{ o.alternative_item_code }}{{ o.is_default ? ' (default)' : '' }} — factor {{ o.conversion_factor }}
              </option>
            </select>
            <div v-if="selectedOption && selectedOption.requires_approval" class="bomx-field-hint" style="color:var(--bx-amber);font-weight:600">
              This item requires approval — the substitution won't apply until a Books Admin / System Manager reviews it.
            </div>
          </div>
          <div style="margin-bottom:14px">
            <div class="bomx-hf-label">Reason <span style="color:var(--bx-red)">*</span></div>
            <textarea class="bomx-fi" rows="2" style="width:100%" v-model="substituteForm.reason" placeholder="Why this substitution is needed…"></textarea>
          </div>
        </template>
      </div>
      <div class="bomx-modal-actions">
        <button class="bomx-btn" style="background:#fff;border:1px solid var(--bx-border)" @click="closeSubstituteModal" :disabled="substituteSaving">Cancel</button>
        <button v-if="substituteOptions.length" class="bomx-btn bomx-btn-mfg" @click="submitSubstitute" :disabled="substituteSaving">
          {{ substituteSaving ? 'Submitting…' : 'Submit Substitution' }}
        </button>
      </div>
    </div>
  </div>

</div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet, apiSave, apiList, apiSubmit, apiCancel, apiAmend, apiCall, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { useConfirm } from "../composables/useConfirm.js";

const route = useRoute();
const router = useRouter();
const { toast } = useToast();
const { confirm } = useConfirm();

// ── LIST STATE ──────────────────────────────────────────────
const loading = ref(false);
const list = ref([]);
const search = ref("");
const filterStatus = ref(typeof route.query.status === "string" ? route.query.status : "");

const statusOptions = ["Draft", "Submitted", "In Process", "Stopped", "Completed", "Cancelled"];

const selectedName = computed(() => (route.params.name && route.params.name !== "new") ? route.params.name : (route.params.name === "new" ? "new" : null));

async function loadList() {
  try {
    const fields = ["name", "production_item", "item_name", "bom", "qty", "stock_uom",
                     "produced_qty", "status", "docstatus", "modified",
                     "planned_start_date", "planned_end_date"];
    const r = await apiList("Work Order", { fields, limit: 1000, order: "modified desc" });
    list.value = r || [];
  } catch (e) {
    toast("Could not load Work Orders: " + e.message, "error");
  }
}

const filtered = computed(() => {
  let r = list.value;
  if (filterStatus.value) r = r.filter(i => i.status === filterStatus.value);
  const q = search.value.toLowerCase().trim();
  if (q) r = r.filter(i => ((i.item_name || "") + (i.production_item || "") + (i.bom || "") + i.name).toLowerCase().includes(q));
  return r;
});

const sorted = computed(() => [...filtered.value]);

function statusClass(row) {
  if (row.status === "Completed") return "badge-active";
  if (row.status === "Cancelled") return "badge-cancelled";
  if (row.status === "Draft") return "badge-obsolete";
  if (row.status === "Stopped") return "badge-stopped";
  return "badge-inprocess";
}

function fmtNum(n) {
  if (n === undefined || n === null) return "0";
  return Number(n).toLocaleString("en-IN", { maximumFractionDigits: 3 });
}
function fmtDate(d) {
  if (!d) return "—";
  const dt = new Date(d);
  if (isNaN(dt)) return "—";
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return `${dt.getDate()} ${months[dt.getMonth()]} ${dt.getFullYear()}`;
}
function isOverdue(row) {
  if (!row.planned_end_date) return false;
  if (["Completed", "Cancelled", "Stopped"].includes(row.status)) return false;
  return new Date(row.planned_end_date) < new Date(new Date().toDateString());
}
function progressPctnew(row) {
  const qty = Number(row.qty) || 0;
  if (!qty) return 0;
  return Math.min(100, Math.round((Number(row.produced_qty) || 0) / qty * 100));
}
function progressColor(row) {
  const pct = progressPctnew(row);
  if (row.status === "Completed" || pct >= 100) return "var(--bx-green)";
  if (row.status === "Stopped") return "var(--bx-amber)";
  return "var(--bx-mfg)";
}

// ── SUMMARY STRIP (display-only, derived from existing list data) ──
function countByStatus(status) {
  return list.value.filter(r => r.status === status).length;
}
const totalQtyPlanned = computed(() => list.value.reduce((s, r) => s + (Number(r.qty) || 0), 0));

// ── STATUS PIPELINE (read-only visual, derived from wo.status) ──
const pipelineSteps = computed(() => {
  if (wo.value.status === "Cancelled") {
    return [
      { key: "draft", label: "Draft" },
      { key: "submitted", label: "Submitted" },
      { key: "cancelled", label: "Cancelled" },
    ];
  }
  if (wo.value.status === "Stopped") {
    return [
      { key: "draft", label: "Draft" },
      { key: "submitted", label: "Submitted" },
      { key: "inprocess", label: "In Process" },
      { key: "stopped", label: "Stopped" },
    ];
  }
  return [
    { key: "draft", label: "Draft" },
    { key: "submitted", label: "Submitted" },
    { key: "inprocess", label: "In Process" },
    { key: "completed", label: "Completed" },
  ];
});
const pipelineOrder = ["draft", "submitted", "inprocess", "completed", "stopped", "cancelled"];
function currentPipelineKey() {
  const s = wo.value.status;
  if (s === "In Process") return "inprocess";
  if (s === "Completed") return "completed";
  if (s === "Stopped") return "stopped";
  if (s === "Cancelled") return "cancelled";
  if (s === "Submitted") return "submitted";
  return "draft";
}
function pipelineStepDone(step) {
  const cur = currentPipelineKey();
  if (step.key === cur) return step.key === "completed" || step.key === "cancelled" || step.key === "stopped";
  return pipelineOrder.indexOf(step.key) < pipelineOrder.indexOf(cur) && !["stopped", "cancelled"].includes(step.key) ? true :
    (pipelineSteps.value.findIndex(s => s.key === step.key) < pipelineSteps.value.findIndex(s => s.key === cur));
}
function pipelineStepActive(step) {
  return step.key === currentPipelineKey();
}
function pipelineDotClass(step) {
  const active = pipelineStepActive(step);
  const done = pipelineStepDone(step);
  if (step.key === "cancelled" && active) return "bomx-sp-dot--cancelled";
  if (step.key === "stopped" && active) return "bomx-sp-dot--stopped";
  if (done || active) return "bomx-sp-dot--done";
  return "bomx-sp-dot--pending";
}

function selectWorkOrder(name) {
  router.push(`/manufacturing/work-order/${name}`);
}
function openAdd() {
  router.push("/manufacturing/work-order/new");
}
function goBackToList() {
  router.push("/manufacturing/work-order");
}

// ── DETAIL STATE ─────────────────────────────────────────────
const isNew = computed(() => route.params.name === "new");
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

function emptyWO() {
  return {
    doctype: "Work Order",
    bom: "",
    production_item: "",
    item_name: "",
    qty: 1,
    stock_uom: "",
    status: "Draft",
    produced_qty: 0,
    process_loss_qty: 0,
    process_loss_percent: 0,
    items_loaded_for_qty: 0,
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
    planned_operating_cost: 0,
    actual_operating_cost: 0,
    additional_operating_cost: 0,
    total_operating_cost: 0,
  };
}
const wo = ref(emptyWO());

const bomList = ref([]);
const selectedProductionItem = ref("");
const filteredBomList = computed(() => {
  if (!selectedProductionItem.value) return bomList.value;
  return bomList.value.filter(b => b.item === selectedProductionItem.value);
});
const stockItems = ref([]);
// Production Item picker: only items that are actually manufactured (Finished Good / WIP).
const manufacturedItems = computed(() =>
  stockItems.value.filter(i => i.item_type === "Finished Good" || i.item_type === "Work In Progress")
);
// Raw-material row picker: exclude Finished Goods (a finished good shouldn't be
// consumed as a raw material into a Manufacturing/Sub-Assembly Work Order) --
// mirrors BOM.vue's rawMaterialItems restriction on the BOM component picker.
// Packing BOMs are the deliberate exception: their bulk item and packing
// materials are frequently Finished Good/Product-type items themselves (e.g.
// a bulk-manufactured item being packed into retail units), so excluding
// Finished Goods there just made a validly-set row's <select> render blank
// (no matching <option> for the already-chosen item_code).
const rawMaterialItems = computed(() =>
  stockItems.value.filter(i => i.item_type !== "Finished Good" || bomType.value === "Packing")
);
const warehouseList = ref([]);
const stockEntries = ref([]);
const qcInspections = ref([]);
const qcLoading = ref(false);
const jobCards = ref([]);
const amendedInto = ref(null);
const jcLoading = ref(false);
const operationsList = ref([]);
const workstationsList = ref([]);
const companiesList = ref([]);
const salesOrdersList = ref([]);
const bomScrapItems = ref([]);
const bomProcessLoss = ref(0);
const bomType = ref("");
const sourcedPackingSlips = ref([]);
const sourcedPsLoading = ref(false);
const reconciliation = ref(null);
const reconLoading = ref(false);

const EMPTY_MATERIAL = () => ({ item_code: "", required_qty: 1, transferred_qty: 0, consumed_qty: 0, source_warehouse: "" });
const EMPTY_OP = () => ({ operation: "", workstation: "", planned_time_in_mins: 0, actual_time_in_mins: 0, status: "Pending" });

// docstatus: 0 = Draft, 1 = Submitted, 2 = Cancelled. Once submitted, the
// plan (materials/operations/warehouses) is locked — progress from here on
// happens only through Issue Materials / Complete Work Order.
const readOnly = computed(() => !isNew.value && (wo.value.docstatus === 1 || wo.value.docstatus === 2));
// Source/WIP warehouse (and per-row source warehouse) can still be corrected
// after submit -- e.g. if the Work Order was submitted without one -- as
// long as the Work Order isn't cancelled and no production has actually
// been recorded against it yet. Once qty has been manufactured, changing
// the source warehouse would be misleading against stock already consumed.
const warehousesEditable = computed(() => wo.value.docstatus !== 2 && flt(wo.value.produced_qty) <= 0);

// Additional Operating Cost is deliberately allow_on_submit=1 on the
// backend (see work_order.json) -- overhead/utilities/etc. not captured by
// Job Card time logs genuinely needs adding while a Work Order is in
// progress (docstatus===1), not just while still a Draft. Only a
// cancelled Work Order (docstatus===2) should block it.
const operatingCostEditable = computed(() => wo.value.docstatus !== 2 && wo.value.status !== "Completed");


onMounted(async () => {
  loading.value = true;
  try {
    const co = await resolveCompany();
    if (isNew.value) wo.value.company = co;

    // Independent of each other — Warehouse only needs `co`, already resolved
    // above. loadList() and fetchManufacturingDefaults() don't depend on any
    // of this reference data either, so they're folded in too. Firing all of
    // this together turns ~9 sequential round trips into 1.
    const [boms, stk, whs, ops, wks, cos, sos] = await Promise.all([
      apiList("BOM", { fields: ["name", "item", "quantity", "docstatus", "bom_version", "is_default", "bom_type"], filters: [["docstatus", "=", 1]], limit: 1000, order: "name asc" }),
      apiList("Item", { fields: ["name", "item_name", "standard_rate", "stock_uom", "has_batch_no", "shelf_life_in_days", "item_type"], filters: [["is_stock_item", "=", 1]], limit: 5000, order: "name asc" }),
      apiList("Warehouse", { fields: ["name"], filters: co ? [["company", "=", co], ["is_group", "=", 0]] : [["is_group", "=", 0]], limit: 1000, order: "name asc" }),
      apiList("Operation", { fields: ["name"], limit: 1000, order: "name asc" }),
      apiList("Workstation", { fields: ["name", "hour_rate"], limit: 1000, order: "name asc" }),
      apiList("Company", { fields: ["name"], limit: 200, order: "name asc" }).catch(() => []),
      apiList("Sales Order", { fields: ["name"], filters: [["docstatus", "=", 1]], limit: 2000, order: "name desc" }).catch(() => []),
      loadList(),
      fetchManufacturingDefaults(),
    ]);

    stockItems.value = stk || [];
    const itemNameOf = {};
    stockItems.value.forEach(i => itemNameOf[i.name] = i.item_name);
    bomList.value = (boms || []).map(b => ({ ...b, item_name: itemNameOf[b.item] || b.item }));

    // The BOM select's options only come from submitted (docstatus=1) BOMs --
    // deliberately, so a new/edited Work Order can't be pointed at a Draft or
    // Cancelled one. But an EXISTING Work Order can be linked to a BOM that
    // was submitted at the time and has since been cancelled elsewhere; that
    // BOM name is missing from bomList, so the <select> (bound to wo.bom by
    // value) has no matching <option> and silently renders blank even though
    // wo.bom itself still holds the correct name. Fetch and inject it here so
    // the field actually displays what the Work Order is linked to.
    if (!isNew.value && wo.value.bom && !bomList.value.some(b => b.name === wo.value.bom)) {
      try {
        const missingBom = await apiGet("BOM", wo.value.bom);
        if (missingBom) {
          bomList.value.push({
            name: missingBom.name,
            item: missingBom.item,
            quantity: missingBom.quantity,
            docstatus: missingBom.docstatus,
            bom_version: missingBom.bom_version,
            is_default: missingBom.is_default,
            bom_type: missingBom.bom_type,
            item_name: itemNameOf[missingBom.item] || missingBom.item,
          });
        }
      } catch (e) { /* non-fatal — field just stays as the raw name if this fails */ }
    }

    warehouseList.value = whs || [];
    operationsList.value = ops || [];
    workstationsList.value = wks || [];
    companiesList.value = cos || [];
    salesOrdersList.value = sos || [];

    if (route.params.name && !isNew.value) {
      await loadWO();
    } else {
      applyWarehouseDefaults();
    }
  } catch (e) {
    toast("Error loading data: " + e.message, "error");
  }
  loading.value = false;
});

// New Work Order — prefill default warehouses from Manufacturing Settings
// (previously these only appeared after a BOM was selected)
let manufacturingDefaults = null;
const warnBomNotDefault = ref(true);
const warnOnMissingJobCards = ref(true);
const jobCardHoursPerDay = ref(8);
const capacityPlanningForDays = ref(30);
async function fetchManufacturingDefaults() {
  try {
    manufacturingDefaults = await apiCall(
      "zoho_books_clone.manufacturing.doctype.manufacturing_settings.manufacturing_settings.get_manufacturing_defaults"
    );
    if (manufacturingDefaults) {
      overProductionAllowancePct.value = flt(manufacturingDefaults.over_production_allowance_pct);
      warnBomNotDefault.value = !!manufacturingDefaults.warn_if_bom_not_default;
      warnOnMissingJobCards.value = !!manufacturingDefaults.warn_on_missing_job_cards;
      jobCardHoursPerDay.value = flt(manufacturingDefaults.job_card_hours_per_day) || 8;
      capacityPlanningForDays.value = flt(manufacturingDefaults.capacity_planning_for_days) || 30;
    }
  } catch (e) {
    // non-fatal — settings may not be configured yet
  }
}

// Total planned operation time across all rows, in minutes
const totalPlannedOperationMinutes = computed(() =>
  (wo.value.operations || []).reduce((sum, op) => sum + (flt(op.planned_time_in_mins) || 0), 0)
);

// Client-side preview of Total Operating Cost so the field updates instantly
// as Additional Operating Cost is edited, ahead of the authoritative
// server-side recalculation in Work Order.calculate_operating_cost() on save.
// Mirrors the backend's PER-ROW logic (see work_order.py::calculate_operating_cost):
// each operation row contributes its actual cost if it has logged actual time,
// else its planned cost. Switching the WHOLE total to "actual" the moment any
// one row gets a Job Card would make every not-yet-started row contribute ₹0
// instead of its planned cost, understating the true cost-to-date.
const totalOperatingCostPreview = computed(() => {
  const rowsTotal = (wo.value.operations || []).reduce((sum, op) => {
    const hourRate = flt(op.hour_rate);
    const actualTime = flt(op.actual_time_in_mins);
    const plannedCost = (flt(op.planned_time_in_mins) / 60) * hourRate;
    const actualCost = (actualTime / 60) * hourRate;
    return sum + (actualTime ? actualCost : plannedCost);
  }, 0);
  const additional = flt(wo.value.additional_operating_cost);
  return rowsTotal + additional;
});

// Raw Material Cost: sum of each Work Order Item row's amount
// (required_qty × rate), same basis Stock Entry uses to value consumption.
const rawMaterialCost = computed(() =>
  (wo.value.items || []).reduce((sum, row) => sum + (flt(row.amount) || 0), 0)
);

// Total Cost shown in the More Information > Cost Breakdown panel: raw
// material cost plus the same Operating Cost figure shown on the Work
// Order tab (planned/actual + additional), mirroring how
// complete_work_order() actually values the finished good.
const totalWorkOrderCost = computed(() => rawMaterialCost.value + totalOperatingCostPreview.value);

// Actual absorbed cost: unlike totalWorkOrderCost/rawMaterialCost above
// (which only ever reflect the BOM-load-time planned snapshot), this pulls
// the real cost that was actually posted into FG stock across every
// completion recorded so far -- so the panel can show "Planned" and
// "Actual" side by side once the Work Order has at least one completion.
const actualAbsorbedCost = ref(null);
async function loadActualAbsorbedCost() {
  if (isNew.value || !wo.value.name || !flt(wo.value.produced_qty)) {
    actualAbsorbedCost.value = null;
    return;
  }
  try {
    const r = await apiCall("zoho_books_clone.manufacturing.work_order_engine.get_actual_absorbed_cost", {
      work_order: wo.value.name,
    });
    actualAbsorbedCost.value = flt(r.actual_cost);
  } catch (e) {
    actualAbsorbedCost.value = null;
  }
}

const recalcLoading = ref(false);
async function recalcOperatingCost(refreshHourRates) {
  if (!wo.value.name || recalcLoading.value) return;
  recalcLoading.value = true;
  try {
    const r = await apiCall(
      "zoho_books_clone.manufacturing.work_order_engine.recalculate_operating_cost",
      { work_order: wo.value.name, refresh_hour_rates: !!refreshHourRates }
    );
    wo.value.planned_operating_cost = r.planned_operating_cost;
    wo.value.actual_operating_cost = r.actual_operating_cost;
    wo.value.total_operating_cost = r.total_operating_cost;
    if (refreshHourRates) {
      // Hour rates on the Operations rows were re-pulled server-side too —
      // reload so the in-memory rows (and any future save) reflect them.
      const fresh = await apiGet("Work Order", wo.value.name);
      wo.value.operations = fresh.operations || wo.value.operations;
    }
    toast("Operating cost recalculated.", "success");
  } catch (e) {
    toast(e.message, "error");
  }
  recalcLoading.value = false;
}

// Estimated number of working days needed to run all operations,
// based on Manufacturing Settings > Job Card Hours Per Day
const estimatedProductionDays = computed(() => {
  const hoursPerDay = jobCardHoursPerDay.value || 8;
  const totalHours = totalPlannedOperationMinutes.value / 60;
  return hoursPerDay > 0 ? totalHours / hoursPerDay : 0;
});

// Whether the estimated duration exceeds the configured capacity planning window
const capacityWindowExceeded = computed(() =>
  estimatedProductionDays.value > (capacityPlanningForDays.value || 0)
);

// Suggests a Planned End Date from Planned Start Date + estimated production days,
// respecting Job Card Hours Per Day. Does not overwrite a date the user already set.
function suggestPlannedEndDate() {
  if (!wo.value.planned_start_date || !totalPlannedOperationMinutes.value) return;
  const days = Math.max(1, Math.ceil(estimatedProductionDays.value));
  const start = new Date(wo.value.planned_start_date);
  if (isNaN(start)) return;
  start.setDate(start.getDate() + days);
  wo.value.planned_end_date = start.toISOString().slice(0, 10);
}

const selectedBomIsNotDefault = computed(() => {
  if (!wo.value.bom) return false;
  const b = bomList.value.find(x => x.name === wo.value.bom);
  return !!b && !b.is_default;
});

function applyWarehouseDefaults() {
  const ms = manufacturingDefaults;
  if (!ms) return;
  if (!wo.value.source_warehouse && ms.default_source_warehouse)
    wo.value.source_warehouse = ms.default_source_warehouse;
  if (!wo.value.wip_warehouse && ms.default_wip_warehouse)
    wo.value.wip_warehouse = ms.default_wip_warehouse;
  if (!wo.value.fg_warehouse && ms.default_fg_warehouse)
    wo.value.fg_warehouse = ms.default_fg_warehouse;
  if (!wo.value.scrap_warehouse && ms.default_scrap_warehouse)
    wo.value.scrap_warehouse = ms.default_scrap_warehouse;
}

watch(() => route.params.name, async (name) => {
  activeTab.value = "details";
  if (!name) { wo.value = emptyWO(); selectedProductionItem.value = ""; return; }
  loading.value = true;
  try {
    await loadWO();
  } catch (e) {
    toast("Error loading Work Order: " + e.message, "error");
  }
  loading.value = false;
});

async function loadWO() {
  // Reset every Work-Order-scoped list up front. Without this, switching to a
  // Work Order that skips the docstatus===1 branch below (e.g. a Draft) left
  // the PREVIOUS Work Order's Job Cards / Stock Entries / Packing Slips /
  // QC Inspections sitting in these refs, since nothing ever cleared them --
  // the Production tab kept showing the last-loaded WO's data until the user
  // manually clicked Refresh. Reconciliation is included too: it's only
  // fetched on-demand via the "Check Reconciliation" button, so without this
  // reset it stays on screen from whichever WO it was last checked on.
  jobCards.value = [];
  stockEntries.value = [];
  sourcedPackingSlips.value = [];
  qcInspections.value = [];
  reconciliation.value = null;
  amendedInto.value = null;

  if (isNew.value) {
    wo.value = emptyWO();
    selectedProductionItem.value = "";
    await fetchManufacturingDefaults();
    applyWarehouseDefaults();
    return;
  }
  const data = await apiGet("Work Order", route.params.name);
  wo.value = data;
  selectedProductionItem.value = data.production_item || "";
  if (!wo.value.items) wo.value.items = [];
  if (!wo.value.operations) wo.value.operations = [];
  const linkedBom = bomList.value.find(b => b.name === wo.value.bom);
  bomType.value = linkedBom ? (linkedBom.bom_type || "Manufacturing") : "";
  if (wo.value.docstatus === 1) {
    await loadStockEntries(); await loadJobCards();
    loadSourcedPackingSlips();
    loadActualAbsorbedCost();
  }
  if (wo.value.docstatus === 2) {
    try {
      const existing = await apiList("Work Order", {
        fields: ["name"],
        filters: [["amended_from", "=", wo.value.name]],
        limit: 1,
      }) || [];
      amendedInto.value = existing[0]?.name || null;
    } catch (e) { amendedInto.value = null; }
  }

  // If the linked BOM is no longer active (it was amended into a newer version,
  // or cancelled), auto-switch a still-editable draft to the latest active
  // version for the same production item so Submit doesn't fail.
  if (!readOnly.value && wo.value.bom) {
    const stillActive = bomList.value.some(b => b.name === wo.value.bom);
    if (!stillActive) {
      let itemCode = wo.value.production_item;
      if (!itemCode) {
        try {
          const staleBom = await apiGet("BOM", wo.value.bom);
          itemCode = staleBom ? staleBom.item : null;
        } catch (e) { /* stale BOM may itself be inaccessible — fall through */ }
      }
      const candidates = bomList.value.filter(b => b.item === itemCode);
      candidates.sort((a, b) => (Number(b.bom_version) || 0) - (Number(a.bom_version) || 0));
      const replacement = candidates.find(c => c.is_default) || candidates[0] || null;
      if (replacement) {
        wo.value.bom = replacement.name;
        toast(`Linked BOM was superseded — switched to the latest version, ${replacement.name}`, "error");
      } else {
        wo.value.bom = "";
        toast("The linked BOM is no longer active. Please select a valid BOM.", "error");
      }
    }
  }
}

async function onProductionItemChange() {
  // Changing the Production Item invalidates whatever BOM/materials/
  // operations were loaded for the previous item.
  wo.value.bom = "";
  wo.value.production_item = selectedProductionItem.value;
  wo.value.item_name = "";
  wo.value.stock_uom = "";
  wo.value.items = [];
  wo.value.operations = [];
  bomScrapItems.value = [];
  bomProcessLoss.value = 0;
  bomType.value = "";

  if (!selectedProductionItem.value) return;

  try {
    const r = await apiCall("zoho_books_clone.manufacturing.work_order_engine.get_default_bom_for_item", {
      item_code: selectedProductionItem.value,
    });
    if (r && r.bom) {
      wo.value.bom = r.bom;
      await loadFromBom();
    }
  } catch (e) {
    // Non-fatal — user can still pick a BOM manually from the dropdown.
  }
}

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
    selectedProductionItem.value = r.production_item || "";
    wo.value.item_name = r.item_name;
    wo.value.stock_uom = r.stock_uom;
    wo.value.items = (r.items || []).map(i => ({
      ...EMPTY_MATERIAL(),
      ...i,
      // use per-row source_warehouse from BOM Item if set, else fall back to
      // the default source warehouse coming from Manufacturing Settings
      source_warehouse: i.source_warehouse || r.default_source_warehouse || "",
    }));
    wo.value.operations = (r.operations || []).map(o => ({ ...EMPTY_OP(), ...o }));
    bomScrapItems.value = r.scrap_items || [];
    bomProcessLoss.value = flt(r.process_loss);
    // Persist onto the Work Order doc itself (not just the client-side ref)
    // so complete_work_order() on the server has this BOM's expected loss %
    // available to split actual process loss into normal vs abnormal later.
    wo.value.process_loss_percent = flt(r.process_loss);
    bomType.value = r.bom_type || "Manufacturing";

    // Pre-fill Work Order warehouse fields from Manufacturing Settings if empty
    if (!wo.value.source_warehouse && r.default_source_warehouse)
      wo.value.source_warehouse = r.default_source_warehouse;
    if (!wo.value.wip_warehouse && r.default_wip_warehouse)
      wo.value.wip_warehouse = r.default_wip_warehouse;
    if (!wo.value.fg_warehouse && r.default_fg_warehouse)
      wo.value.fg_warehouse = r.default_fg_warehouse;
    if (!wo.value.scrap_warehouse && r.default_scrap_warehouse)
      wo.value.scrap_warehouse = r.default_scrap_warehouse;

    // Snapshot the qty these tables were just synced to, so a later edit to
    // Qty to Manufacture without clicking this button again can be detected
    // (see materialsStale below and Work Order's own server-side check).
    wo.value.items_loaded_for_qty = flt(wo.value.qty);
  } catch (e) {
    toast(e.message, "error");
  }
  breakdownLoading.value = false;
}

// True once Qty to Manufacture has drifted away from the qty the Raw
// Material/Operations tables were last loaded/refreshed for -- e.g. the
// person bumped Qty up after already loading materials, without clicking
// "Load / Refresh Materials from BOM" again. Required Qty on every raw
// material row is still sized for the OLD qty in that state, so saving as-is
// would silently under/over-consume raw materials and mis-value the
// finished good once this Work Order is completed. Ignores brand-new/empty
// Work Orders (nothing loaded yet) and legacy docs saved before this field
// existed (items_loaded_for_qty of 0/falsy -- basis unknown, not our call to
// flag).
const materialsStale = computed(() => {
  if (!wo.value.items_loaded_for_qty || !wo.value.items || !wo.value.items.length) return false;
  const tolerance = Math.max(flt(wo.value.qty) * 0.001, 0.0001);
  return Math.abs(flt(wo.value.qty) - flt(wo.value.items_loaded_for_qty)) > tolerance;
});

function addMaterial() { wo.value.items.push(EMPTY_MATERIAL()); }
function removeMaterial(idx) { wo.value.items.splice(idx, 1); }
function addOp() { wo.value.operations.push(EMPTY_OP()); }
function removeOp(idx) { wo.value.operations.splice(idx, 1); }

// A Work Order needs a Source Warehouse to consume raw materials from at
// Complete time -- either a Default Source Warehouse on the Work Order
// itself, or every individual raw material row overriding its own. If
// neither is set, Complete Work Order fails later with no way to fix it
// from that screen, so we catch it here at save/submit time instead.
function hasSourceWarehouse() {
  if (wo.value.source_warehouse) return true;
  const rows = wo.value.items || [];
  return rows.length > 0 && rows.every(r => !!r.source_warehouse);
}

async function save() {
  if (!wo.value.bom) return toast("Please select a BOM", "error");
  if (!wo.value.qty || wo.value.qty <= 0) return toast("Qty to Manufacture must be greater than 0", "error");
  if (!wo.value.fg_warehouse) return toast("Finished Goods Warehouse is required", "error");
  if (!wo.value.items || !wo.value.items.length) return toast("Load raw materials from the BOM first", "error");
  if (!hasSourceWarehouse()) return toast("Default Source Warehouse is required (or set a Source Warehouse on every raw material row)", "error");
  if (materialsStale.value) return toast("Qty to Manufacture changed since materials were loaded — click 'Load / Refresh Materials from BOM' first", "error");


  saving.value = true;
  try {
    const doc = await apiSave(wo.value);
    toast(isNew.value ? "Work Order created" : "Work Order updated");
    if (isNew.value) {
      router.replace(`/manufacturing/work-order/${doc.name}`);
    } else {
      wo.value = doc;
    }
    loadList();
  } catch (e) {
    toast(e.message, "error");
  }
  saving.value = false;
}

async function submitWO() {
  if (!wo.value.name) return;
  if (!wo.value.bom) return toast("Please select a BOM", "error");
  if (!wo.value.qty || wo.value.qty <= 0) return toast("Qty to Manufacture must be greater than 0", "error");
  if (!wo.value.fg_warehouse) return toast("Finished Goods Warehouse is required", "error");
  if (!wo.value.items || !wo.value.items.length) return toast("Load raw materials from the BOM first", "error");
  if (!hasSourceWarehouse()) return toast("Default Source Warehouse is required (or set a Source Warehouse on every raw material row)", "error");
  if (materialsStale.value) return toast("Qty to Manufacture changed since materials were loaded — click 'Load / Refresh Materials from BOM' first", "error");

  submitting.value = true;

  try {
    // Persist any unsaved edits (e.g. an auto-corrected BOM reference) before
    // submitting — apiSubmit acts on the doc as currently stored in the DB.
    const saved = await apiSave(wo.value);
    wo.value = saved;
    const doc = await apiSubmit("Work Order", wo.value.name);
    wo.value = doc;
    toast("Work Order submitted");
    loadList();
  } catch (e) {
    toast(e.message, "error");
  }
  submitting.value = false;
}

async function cancelWO() {
  if (!wo.value.name) return;
  if (!(await confirm({
    title: "Cancel Work Order",
    body: `Cancel Work Order ${wo.value.name}? This cannot be undone.`,
    okLabel: "Cancel Work Order",
    okStyle: "danger",
  }))) return;
  submitting.value = true;
  try {
    const doc = await apiCancel("Work Order", wo.value.name);
    wo.value = doc;
    toast("Work Order cancelled");
    loadList();
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
    loadList();
  } catch (e) {
    toast(e.message, "error");
  }
  submitting.value = false;
}

async function stopWO() {
  if (!wo.value.name) return;
  submitting.value = true;
  try {
    await apiCall("zoho_books_clone.manufacturing.work_order_engine.stop_work_order", { work_order: wo.value.name });
    // Backend also bulk-updates every Operation row's status and bumps
    // `modified` -- re-fetch the full doc rather than patching just the
    // status field locally, so the client's `modified` timestamp stays in
    // sync (otherwise the next apiSave() sends a stale timestamp and hits
    // a "Document has been modified" error).
    wo.value = await apiGet("Work Order", wo.value.name);
    toast("Work Order stopped");
    loadList();
  } catch (e) {
    toast(e.message, "error");
  }
  submitting.value = false;
}

async function resumeWO() {
  if (!wo.value.name) return;
  submitting.value = true;
  try {
    await apiCall("zoho_books_clone.manufacturing.work_order_engine.resume_work_order", { work_order: wo.value.name });
    // Same reasoning as stopWO() -- re-fetch the full doc instead of
    // patching a single field, so `modified` doesn't go stale.
    wo.value = await apiGet("Work Order", wo.value.name);
    toast("Work Order resumed");
    loadList();
  } catch (e) {
    toast(e.message, "error");
  }
  submitting.value = false;
}

const remainingQty = computed(() => flt(wo.value.qty) - flt(wo.value.produced_qty));
// Manufacturing Settings' Over-Production Allowance % lets complete_work_order
// (server-side) accept qty_manufactured beyond the planned qty. The Complete
// modal used to hard-cap at remainingQty regardless of this setting, which
// made the allowance completely unreachable from the UI — every over-planned
// completion would be blocked client-side before the request even left the
// browser, no matter how the admin had configured it.
const overProductionAllowancePct = ref(0);
const maxCompletableQty = computed(() => {
  const planned = flt(wo.value.qty);
  const allowance = planned * (flt(overProductionAllowancePct.value) / 100);
  return Math.max(0, planned + allowance - flt(wo.value.produced_qty));
});
// Whether there's still any completable qty left, INCLUDING what the
// over-production allowance opens up once produced_qty reaches the planned
// qty. remainingQty alone hits 0 exactly at 100% produced and would lock
// the button out even when the allowance still permits more.
const canCompleteMore = computed(() => maxCompletableQty.value > 0.0001);
// Live inline validation for the Complete modal's Qty Manufactured field --
// HTML's `max` attribute doesn't actually block typed/pasted values above
// it, so this backs it up with a message the person sees immediately,
// while the hard check in submitComplete() (and the server) stays the
// real source of truth.
const qtyManufacturedError = computed(() => {
  const qty = flt(completeForm.value.qty_manufactured);
  if (qty > maxCompletableQty.value + 0.0001) {
    return `Cannot exceed ${fmt(maxCompletableQty.value)}${overProductionAllowancePct.value > 0 ? ` (planned qty + ${overProductionAllowancePct.value}% over-production allowance)` : ""}`;
  }
  return "";
});
const progressPct = computed(() => progressPctnew(wo.value));
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

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function itemLabel(code) {
  const i = stockItems.value.find(x => x.name === code);
  return (i && i.item_name) || code || "";
}

function printWorkOrder() {
  const rows = wo.value.items || [];
  const rowsHtml = rows.length
    ? rows.map(rm => `
        <tr>
          <td>${esc(rm.item_code)}</td>
          <td>${esc(itemLabel(rm.item_code))}</td>
          <td style="text-align:right">${esc(fmt(rm.required_qty))}</td>
          <td>${esc(rm.source_warehouse || wo.value.source_warehouse || "—")}</td>
        </tr>`).join("")
    : `<tr><td colspan="4" style="text-align:center;color:#868E96">No raw materials</td></tr>`;

  const html = `
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8"/>
        <title>Work Order ${esc(wo.value.name)}</title>
        <style>
          * { box-sizing:border-box; margin:0; padding:0; }
          body { font-family: Arial, Helvetica, sans-serif; color:#1A1D23; background:#e5e7eb; min-height:100vh; }
          .toolbar { position:sticky; top:0; z-index:10; background:#fff; padding:10px 18px; border-bottom:1px solid #e5e7eb; display:flex; align-items:center; gap:10px; box-shadow:0 1px 4px rgba(0,0,0,.06); }
          .tb-lbl { font-size:11.5px; font-weight:700; color:#374151; letter-spacing:.04em; }
          .print-btn { margin-left:auto; background:#1a6ef7; color:#fff; border:none; padding:7px 16px; border-radius:7px; font-weight:700; cursor:pointer; font:inherit; font-size:12.5px; display:flex; align-items:center; gap:6px; }
          .print-btn:hover { background:#1558d0; }
          .doc-wrap { max-width:820px; margin:20px auto; background:#fff; box-shadow:0 4px 24px rgba(0,0,0,.1); border-radius:8px; overflow:hidden; }
          .sheet { padding:28px 30px; }
          h1 { font-size:18px; margin:0 0 4px; }
          .sub { color:#868E96; font-size:12px; margin-bottom:20px; padding-bottom:14px; border-bottom:1px solid #E2E8F0; }
          .meta { display:grid; grid-template-columns: 1fr 1fr; gap:10px 24px; margin-bottom:22px; font-size:13px; }
          .meta div { border:1px solid #E2E8F0; border-radius:6px; padding:8px 10px; }
          .meta div span { color:#868E96; display:block; font-size:10.5px; text-transform:uppercase; letter-spacing:.04em; margin-bottom:2px; }
          table { width:100%; border-collapse:collapse; font-size:13px; border:1px solid #E2E8F0; border-radius:6px; overflow:hidden; }
          th, td { border:1px solid #E2E8F0; padding:8px 10px; text-align:left; }
          th { background:#F8F9FC; font-size:11px; text-transform:uppercase; letter-spacing:.03em; color:#868E96; }
          h2 { font-size:13px; text-transform:uppercase; letter-spacing:.03em; color:#868E96; margin:0 0 8px; }
          @media print { .toolbar { display:none!important; } body { background:#fff; } .doc-wrap { box-shadow:none; margin:0; max-width:none; border-radius:0; } }
        </style>
      </head>
      <body>
        <div class="toolbar">
          <span class="tb-lbl">PRINT PREVIEW</span>
          <button class="print-btn" onclick="window.print()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
            Print
          </button>
        </div>
        <div class="doc-wrap"><div class="sheet">
          <h1>Work Order — ${esc(wo.value.name)}</h1>
          <div class="sub">Printed ${esc(new Date().toLocaleString())}</div>
          <div class="meta">
            <div><span>Production Item</span>${esc(wo.value.item_name || wo.value.production_item)}</div>
            <div><span>BOM</span>${esc(wo.value.bom)}</div>
            <div><span>Qty to Manufacture</span>${esc(fmt(wo.value.qty))} ${esc(wo.value.stock_uom)}</div>
            <div><span>Default Source Warehouse</span>${esc(wo.value.source_warehouse || "—")}</div>
          </div>
          <h2>Raw Materials</h2>
          <table>
            <thead>
              <tr><th>Item Code</th><th>Item Name</th><th style="text-align:right">Required Qty</th><th>Warehouse</th></tr>
            </thead>
            <tbody>${rowsHtml}</tbody>
          </table>
        </div></div>
      </body>
    </html>`;

  const win = window.open("", "_blank");
  if (!win) { toast("Please allow pop-ups to print", "error"); return; }
  win.document.open();
  win.document.write(html);
  win.document.close();
  win.focus();
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
  await loadQcInspections();
}

// QC Inspections for finished-good items get auto-created (In Process type)
// against the Manufacture Stock Entry when this Work Order is completed —
// see zoho_books_clone.quality.qc_engine.auto_create_qc_for_stock_entry.
// They're stamped with a `work_order` field for traceability; surface them
// here so a Pending/Fail QC on the produced batch is never silently missed.
async function loadQcInspections() {
  qcLoading.value = true;
  try {
    qcInspections.value = await apiList("QC Inspection", {
      fields: ["name", "status", "item", "item_name", "inspection_date", "reference_name", "docstatus"],
      filters: [["work_order", "=", wo.value.name]],
      limit: 50, order: "creation desc",
    }) || [];
  } catch (e) { qcInspections.value = []; }
  qcLoading.value = false;
}

// Packing Slips that traced their bulk item back to this Work Order (see
// packing_engine.py's source_work_order field) -- the inverse of "Sourced
// From" shown on the Packing Slip itself.
async function loadSourcedPackingSlips() {
  sourcedPsLoading.value = true;
  try {
    sourcedPackingSlips.value = await apiCall(
      "zoho_books_clone.manufacturing.packing_engine.get_packing_slips_sourced_from_work_order",
      { work_order: wo.value.name }
    ) || [];
  } catch (e) { sourcedPackingSlips.value = []; }
  sourcedPsLoading.value = false;
}

// Phase 6: on-demand reconciliation of this (bulk-producing) Work Order's
// output against every Packing Slip that drew on it, plus what's still
// sitting in the warehouse. Loaded on click rather than on mount -- it's a
// diagnostic view, not something every page load needs to pay for.
async function loadReconciliation() {
  reconLoading.value = true;
  try {
    reconciliation.value = await apiCall(
      "zoho_books_clone.manufacturing.packing_engine.get_bulk_packing_reconciliation",
      { work_order: wo.value.name }
    ) || null;
  } catch (e) {
    reconciliation.value = null;
    toast.error(e?.message || "Could not load reconciliation.");
  }
  reconLoading.value = false;
}

function reconStatusLabel(status) {
  if (status === "reconciled") return "Reconciled";
  if (status === "shortage") return "Shortage";
  if (status === "overpack") return "Overpack";
  return status;
}

function reconStatusStyle(status) {
  if (status === "reconciled") return "background:var(--bx-greenS);color:var(--bx-green)";
  if (status === "shortage") return "background:var(--bx-redS);color:var(--bx-red)";
  return "background:var(--bx-amberS);color:var(--bx-amber)"; // overpack
}

// Job Cards aren't a child table on Work Order — they're separate documents that
// reference this Work Order by name. Surface them here (with a shortcut to create
// one per operation) rather than making users navigate to a separate page and
// re-pick the same Work Order + Operation from scratch.
async function loadJobCards() {
  jcLoading.value = true;
  try {
    jobCards.value = await apiList("Job Card", {
      fields: ["name", "operation", "wo_operation_name", "workstation", "status", "for_quantity", "total_time_in_mins"],
      filters: [["work_order", "=", wo.value.name]],
      limit: 100, order: "creation desc",
    }) || [];
  } catch (e) { jobCards.value = []; }
  jcLoading.value = false;
}

function jobCardsFor(op) {
  return (jobCards.value || []).filter(jc => jc.wo_operation_name === op.name);
}
function createJobCardFor(op) {
  router.push({
    path: "/manufacturing/job-card/new",
    query: {
      work_order: wo.value.name,
      operation: op.operation,
      wo_operation_name: op.name,
      workstation: op.workstation || "",
      for_quantity: wo.value.qty || 1,
    },
  });
}

const qcSummary = computed(() => {
  const list = qcInspections.value || [];
  if (!list.length) return null;
  const fail = list.filter(q => q.status === "Fail").length;
  const pending = list.filter(q => q.status === "Pending" || q.docstatus === 0).length;
  const pass = list.filter(q => q.status === "Pass" && q.docstatus === 1).length;
  let overall = "Pass";
  if (fail > 0) overall = "Fail";
  else if (pending > 0) overall = "Pending";
  return { fail, pending, pass, overall, total: list.length };
});

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

// Derive the BOM-proportional process loss & scrap-item quantities for a
// given Qty Manufactured. Shared by openCompleteModal (initial prefill) and
// the qty_manufactured watcher below (keeps them in sync on edits).
function deriveScrapAndLoss(qtyMfg) {
  const ratio = qtyMfg / flt(wo.value.qty || 1);
  const derivedLoss = bomProcessLoss.value > 0
    ? parseFloat((qtyMfg * bomProcessLoss.value / 100).toFixed(4))
    : 0;
  const preScrap = bomScrapItems.value.length
    ? bomScrapItems.value.map(s => ({ item_code: s.item_code, qty: parseFloat((flt(s.qty) * ratio).toFixed(4)) }))
    : [];
  return { derivedLoss, preScrap };
}

function openCompleteModal() {
  // Prefer the plain remaining qty (the common case); once that's used up,
  // fall back to whatever the over-production allowance still permits so
  // the field isn't prefilled with 0 while completion is still possible.
  const qtyMfg = remainingQty.value > 0 ? remainingQty.value : maxCompletableQty.value;
  const { derivedLoss, preScrap } = deriveScrapAndLoss(qtyMfg);
  completeForm.value = {
    qty_manufactured: qtyMfg,
    process_loss_qty: derivedLoss,
    batch_no: "",
    manufacturing_date: new Date().toISOString().slice(0, 10),
    expiry_date: "",
    scrap_items: preScrap,
  };
  showCompleteModal.value = true;
}
function closeCompleteModal() { showCompleteModal.value = false; }
function addCompleteScrap() { completeForm.value.scrap_items.push({ item_code: "", qty: 1 }); }

// Keep the BOM-derived process loss & scrap-item quantities in sync with
// Qty Manufactured whenever the person edits it in the modal. Without this,
// a partial completion (qty edited down from the prefilled full remaining
// qty) would silently submit scrap/process-loss figures sized for the
// original, larger qty.
watch(() => completeForm.value.qty_manufactured, (newQty) => {
  if (!showCompleteModal.value) return;
  const qtyMfg = flt(newQty);
  const { derivedLoss, preScrap } = deriveScrapAndLoss(qtyMfg);
  completeForm.value.process_loss_qty = derivedLoss;

  // Only rescale rows that still match a BOM-derived scrap item (by
  // item_code) so manually added/edited scrap rows aren't clobbered.
  const bomCodes = new Set(bomScrapItems.value.map(s => s.item_code));
  completeForm.value.scrap_items = completeForm.value.scrap_items.map(row => {
    if (!bomCodes.has(row.item_code)) return row;
    const match = preScrap.find(p => p.item_code === row.item_code);
    return match ? { ...row, qty: match.qty } : row;
  });
});

async function submitComplete() {
  const qty = flt(completeForm.value.qty_manufactured);
  if (qty <= 0) return toast("Qty Manufactured must be greater than zero", "error");
  if (qty > maxCompletableQty.value + 0.0001) return toast(`Qty Manufactured cannot exceed ${fmt(maxCompletableQty.value)}${overProductionAllowancePct.value>0 ? ` (planned qty + ${overProductionAllowancePct.value}% over-production allowance)` : ""}`, "error");

  // Warn on Incomplete Job Cards (Manufacturing Settings): if this completion
  // would finish the Work Order but one or more Job Cards are still open,
  // give the user a chance to back out and close them first — otherwise
  // they're silently force-completed by the backend once the WO is done.
  const willFinish = (wo.value.produced_qty || 0) + qty >= flt(wo.value.qty) - 0.0001;
  if (warnOnMissingJobCards.value && willFinish) {
    const incomplete = (jobCards.value || []).filter(jc => jc.status !== "Completed" && jc.status !== "Cancelled");
    if (incomplete.length) {
      const names = incomplete.map(jc => jc.name).join(", ");
      if (!(await confirm({
        title: "Incomplete Job Cards",
        body: `This completion will finish the Work Order, but ${incomplete.length} Job Card(s) are still open (${names}). They'll be force-marked Completed. Continue anyway?`,
        okLabel: "Complete Anyway",
        okStyle: "danger",
      }))) return;
    }
  }

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
    loadList();
  } catch (e) {
    toast(e.message, "error");
  }
  actionLoading.value = false;
}

async function createPackingSlip() {
  actionLoading.value = "ps";
  try {
    const psName = await apiCall("zoho_books_clone.manufacturing.packing_engine.create_packing_slip", {
      work_order: wo.value.name,
      qty_to_pack: flt(wo.value.qty) - flt(wo.value.produced_qty),
    });
    toast(`Packing Slip ${psName} created`);
    router.push(`/manufacturing/packing-slip/${psName}`);
  } catch (e) {
    toast(e.message, "error");
  }
  actionLoading.value = false;
}

// ── Substitute Material modal ──────────────────────────────────────────
const showSubstituteModal = ref(false);
const substituteRow = ref(null);
const substituteOptions = ref([]);
const substituteLoading = ref(false);
const substituteSaving = ref(false);
const substituteForm = ref({ alternative_item_code: "", reason: "" });

const selectedOption = computed(() =>
  substituteOptions.value.find(o => o.alternative_item_code === substituteForm.value.alternative_item_code) || null
);

async function openSubstitute(rm) {
  substituteRow.value = rm;
  substituteForm.value = { alternative_item_code: "", reason: "" };
  substituteOptions.value = [];
  showSubstituteModal.value = true;
  substituteLoading.value = true;
  try {
    const res = await apiCall("zoho_books_clone.api.material_substitution.get_substitution_options", {
      work_order: wo.value.name,
      work_order_item_row: rm.name,
    });
    const data = res?.message || res || {};
    substituteOptions.value = data.options || [];
  } catch (e) {
    toast(e.message || "Could not load alternative items", "error");
  }
  substituteLoading.value = false;
}
function closeSubstituteModal() { showSubstituteModal.value = false; }

async function submitSubstitute() {
  if (!substituteForm.value.alternative_item_code) return toast("Select an alternative item", "error");
  if (!substituteForm.value.reason.trim()) return toast("A reason is required", "error");
  substituteSaving.value = true;
  try {
    const res = await apiCall("zoho_books_clone.api.material_substitution.request_material_substitution", {
      work_order: wo.value.name,
      work_order_item_row: substituteRow.value.name,
      alternative_item_code: substituteForm.value.alternative_item_code,
      reason: substituteForm.value.reason,
    });
    const data = res?.message || res || {};
    toast(data.message || "Substitution submitted");
    showSubstituteModal.value = false;
    await loadWO();
  } catch (e) {
    toast(e.message || "Substitution failed", "error");
  }
  substituteSaving.value = false;
}

function flt(n) { const v = parseFloat(n); return isNaN(v) ? 0 : v; }
function fmt(n) {
  if (isNaN(n) || n == null) return "0.00";
  return Number(n).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
// ── UTIL ─────────────────────────────────────────────────────
const ICONS = {
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
  printer: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 6 2 18 2 18 9"></polyline><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path><rect x="6" y="14" width="12" height="8"></rect></svg>',
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
  x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>',
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

/* ── Status tabs (list view) ── */
.bomx-status-tabs { display:flex; border-bottom:2px solid var(--bx-border); margin-bottom:14px; gap:2px; overflow-x:auto; }
.bomx-status-tab { padding:9px 16px; font-size:13px; font-weight:600; cursor:pointer; border:none; background:none; color:var(--bx-muted); border-bottom:2px solid transparent; margin-bottom:-2px; transition:all .15s; white-space:nowrap; display:flex; align-items:center; gap:6px; }
.bomx-status-tab.active { color:var(--bx-mfg); border-bottom-color:var(--bx-mfg); }
.bomx-status-tab:hover:not(.active) { color:var(--bx-text); }
.bomx-tab-count { font-size:11px; background:var(--bx-bg); border:1px solid var(--bx-border); border-radius:20px; padding:1px 7px; font-weight:600; }
.bomx-status-tab.active .bomx-tab-count { background:var(--bx-mfgS); border-color:rgba(180,83,9,.2); color:var(--bx-mfg); }

/* ── Toolbar (list view) ── */
.bomx-toolbar { display:flex; align-items:center; gap:10px; flex-wrap:wrap; background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); padding:12px 14px; margin-bottom:16px; }
.bomx-search-wrap { display:flex; align-items:center; gap:7px; background:var(--bx-surf2); border:1px solid var(--bx-border); border-radius:20px; padding:6px 14px; min-width:220px; color:var(--bx-muted); }
.bomx-search-wrap input { border:none; outline:none; font-size:13px; background:transparent; color:var(--bx-text); width:100%; }
.bomx-search-wrap input::placeholder { color:var(--bx-muted); }
.bomx-toolbar-count { font-size:12.5px; color:var(--bx-muted); white-space:nowrap; }

/* ── Work Order table ── */
.bomx-table-wrap { background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow-x:auto; margin-bottom:20px; }
.bomx-table { width:100%; border-collapse:collapse; font-size:13px; }
.bomx-table th { text-align:left; padding:9px 14px; border-bottom:1px solid var(--bx-border); font-size:10px; letter-spacing:.06em; text-transform:uppercase; color:var(--bx-muted); font-weight:700; background:var(--bx-surf2); white-space:nowrap; }
.bomx-table td { padding:11px 14px; border-bottom:1px solid #F1F3F5; vertical-align:middle; }
.bomx-table tr:last-child td { border-bottom:none; }
.bomx-wo-row { cursor:pointer; transition:background .1s; }
.bomx-wo-row:hover td { background:#FAFBFF; }
.bomx-prog-bar { height:5px; background:#E2E8F0; border-radius:3px; overflow:hidden; width:76px; flex-shrink:0; }
.bomx-prog-fill { height:100%; border-radius:3px; transition:width .3s; }

/* ── Overlay + slide-in drawer (Work Order detail) ── */
.bomx-overlay { position:fixed; inset:0; background:rgba(17,24,39,.5); display:flex; justify-content:flex-end; z-index:1000; }
.bomx-drawer { width:820px; max-width:97vw; height:100%; background:#fff; box-shadow:-8px 0 30px rgba(0,0,0,.15); display:flex; flex-direction:column; animation: bx-slide-in .18s ease-out; overflow:hidden; }
@keyframes bx-slide-in { from { transform:translateX(100%); } to { transform:translateX(0); } }
.bomx-drawer .bomx-body { flex:1; overflow-y:auto; }

/* ── Summary strip ── */
.bomx-sum-strip { display:grid; grid-template-columns:repeat(6,1fr); gap:10px; margin-bottom:16px; }
.bomx-sum-card { background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); padding:12px 14px; position:relative; overflow:hidden; }
.bomx-sc-bar { position:absolute; top:0; left:0; width:3px; height:100%; }
.bomx-sc-lbl { font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); margin-bottom:3px; }
.bomx-sc-val { font-size:20px; font-weight:700; font-family:var(--bx-mono, monospace); }
.bomx-sc-sub { font-size:10.5px; color:var(--bx-muted); margin-top:1px; }
@media (max-width:1300px) { .bomx-sum-strip { grid-template-columns:repeat(3,1fr); } }
@media (max-width:640px) { .bomx-sum-strip { grid-template-columns:repeat(2,1fr); } }

/* ── Status pipeline ── */
.bomx-status-pipe { display:flex; align-items:flex-start; gap:0; margin:16px 22px 0; padding:14px 18px; background:var(--bx-surf2); border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow-x:auto; }
.bomx-sp-wrap { display:flex; flex-direction:column; align-items:center; gap:0; flex-shrink:0; }
.bomx-sp-dot { width:26px; height:26px; border-radius:50%; border:2px solid; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:700; flex-shrink:0; transition:all .2s; }
.bomx-sp-dot--pending { border-color:var(--bx-border); color:var(--bx-muted); background:#fff; }
.bomx-sp-dot--done { border-color:var(--bx-mfg); color:#fff; background:var(--bx-mfg); }
.bomx-sp-dot--stopped { border-color:var(--bx-amber); color:#fff; background:var(--bx-amber); }
.bomx-sp-dot--cancelled { border-color:var(--bx-red); color:#fff; background:var(--bx-red); }
.bomx-sp-label { font-size:11px; font-weight:600; margin-top:5px; text-align:center; white-space:nowrap; color:var(--bx-muted); }
.bomx-sp-label--active { color:var(--bx-mfgB); }
.bomx-sp-line { width:40px; height:2px; flex-shrink:0; background:var(--bx-border); margin:12px 6px 0; }
.bomx-sp-line--done { background:var(--bx-mfg); }


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

/* ── Badges ── */
.bomx-badge { display:inline-flex; align-items:center; padding:2px 8px; border-radius:20px; font-size:11px; font-weight:600; white-space:nowrap; }
.badge-active { background:var(--bx-greenS); color:var(--bx-green); }
.badge-obsolete { background:#F1F3F5; color:var(--bx-muted); }
.badge-cancelled { background:var(--bx-redS); color:var(--bx-red); }
.badge-stopped { background:var(--bx-amberS); color:var(--bx-amber); }
.badge-inprocess { background:var(--bx-blueS); color:var(--bx-blue); }

/* ── Detail panel ── */
.bomx-detail-panel { background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; display:flex; flex-direction:column; min-height: calc(100vh - 100px); }
.bomx-empty-state { text-align:center; padding:60px 20px; color:var(--bx-muted); }
.bomx-empty-icon { font-size:48px; margin-bottom:14px; }
.bomx-empty-title { font-size:16px; font-weight:700; color:var(--bx-text); margin-bottom:6px; }
.bomx-empty-sub { font-size:13px; line-height:1.6; max-width:280px; margin:0 auto 20px; }

.bomx-detail-hdr { padding:18px 22px; background:linear-gradient(135deg, var(--bx-mfgB), var(--bx-mfg)); }
.bomx-detail-title { font-size:18px; font-weight:700; color:#fff; margin-bottom:4px; }
.bomx-detail-meta { font-size:12.5px; color:rgba(255,255,255,.75); display:flex; align-items:center; gap:8px; flex-wrap:wrap; }

/* ── Tabs ── */
.bomx-tabs { display:flex; gap:2px; padding:0 22px; background:var(--bx-surf2); border-bottom:1px solid var(--bx-border); overflow-x:auto; scrollbar-width:none; }
.bomx-tabs::-webkit-scrollbar { display:none; }
.bomx-tab { padding:10px 14px; border:none; background:none; cursor:pointer; font-size:12.5px; font-weight:600; color:var(--bx-muted); white-space:nowrap; border-bottom:2px solid transparent; margin-bottom:-1px; transition:color .15s; }
.bomx-tab:hover { color:var(--bx-mfgB); }
.bomx-tab--active { color:var(--bx-mfgB); border-bottom-color:var(--bx-mfg); }

.bomx-hdr-fields { display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; padding:16px 22px; border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); }
.bomx-hf-cols-2-1 { grid-template-columns:2fr 1fr; }
.bomx-hf-cols-1-1 { grid-template-columns:1fr 1fr; }
.bomx-hf-cols-1 { grid-template-columns:1fr; }
.bomx-rm-card-body-2-1-auto { grid-template-columns:2fr 1fr auto; align-items:end; }
@media (max-width:640px) {
  .bomx-hf-cols-2-1, .bomx-hf-cols-1-1 { grid-template-columns:1fr; }
  .bomx-rm-card-body-2-1-auto { grid-template-columns:1fr; align-items:stretch; }
}
.bomx-hf-label { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); margin-bottom:4px; }
.bomx-field-hint { font-size:12px; color:var(--bx-muted); margin-top:5px; }
.bomx-toggle-row { display:flex; gap:20px; padding:10px 22px 14px; flex-wrap:wrap; background:var(--bx-surf2); border-bottom:1px solid var(--bx-border); }
.bomx-toggle { display:flex; align-items:center; gap:6px; font-size:12.5px; font-weight:600; color:var(--bx-text); }

.bomx-body { padding:20px 22px; overflow-y:auto; flex:1; }
.bomx-section-lbl { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--bx-muted); margin-bottom:8px; }
.bomx-link { color:var(--bx-mfg); font-weight:600; cursor:pointer; font-size:13px; }
.bomx-link:hover { text-decoration:underline; }
.bomx-tree-empty { text-align:center; padding:20px; color:var(--bx-muted); font-size:13px; }
.bomx-tree-icon { font-size:14px; flex-shrink:0; }
.bomx-add-row { display:flex; align-items:center; gap:8px; padding:8px 12px; color:var(--bx-mfg); cursor:pointer; font-size:13px; font-weight:600; border-radius:var(--bx-rsm); margin-top:4px; }
.bomx-add-row:hover { background:var(--bx-mfgS); }

.bomx-prod-card { background:var(--bx-surf2); border:1px solid var(--bx-border); border-radius:var(--bx-radius); padding:16px; margin-bottom:16px; }
.bomx-recon-cell { background:var(--bx-surf); border:1px solid var(--bx-border); border-radius:8px; padding:8px 10px; }
.bomx-recon-lbl { font-size:11px; color:var(--bx-muted); text-transform:uppercase; letter-spacing:.02em; }
.bomx-recon-val { font-size:15px; font-weight:600; margin-top:2px; }

/* ── Child-row cards ── */
.bomx-rm-cards { display:flex; flex-direction:column; gap:10px; }
.bomx-rm-card { background:#fff; border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; box-shadow:0 1px 3px rgba(16,24,40,.04); }
.bomx-rm-card-hdr { display:flex; align-items:center; gap:10px; padding:10px 14px; background:var(--bx-mfgS); border-bottom:1px solid var(--bx-border); }
.bomx-rm-card-title { flex:1; min-width:0; font-weight:600; }
.bomx-rm-card-rm { flex-shrink:0; }
.bomx-rm-card-body { display:grid; grid-template-columns:1fr 1fr; gap:10px; padding:12px 14px; }
.bomx-rm-card-body-3col { grid-template-columns:2fr 1fr 1fr; }
@media (max-width:768px) {
  .bomx-rm-card-body-3col { grid-template-columns:1fr 1fr; }
  .bomx-rm-card-body-3col .bomx-rm-field-wide { grid-column:1 / -1; }
}
@media (max-width:420px) {
  .bomx-rm-card-body-3col { grid-template-columns:1fr; }
  .bomx-rm-card-body-3col .bomx-rm-field-wide { grid-column:auto; }
}
.bomx-rm-field { display:flex; flex-direction:column; gap:4px; min-width:0; }
.bomx-rm-field label { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); }
.bomx-rm-field .bomx-fi { width:100%; }
.bomx-rm-static { font-size:13px; color:var(--bx-text); padding:7px 0; }

.bomx-cost-card {
  border:1px solid var(--bx-border,#e5e9f0);
  border-radius:var(--bx-rlg,14px);
  background:linear-gradient(135deg, var(--bx-mfgS), #fff 60%);
  overflow:hidden;
  margin-bottom:24px;
}
.bomx-cost-card-hdr {
  display:flex; align-items:center; justify-content:space-between;
  padding:12px 18px;
  background:linear-gradient(135deg, var(--bx-mfgB), var(--bx-mfg));
  color:#fff;
}
.bomx-cost-card-hdr span:first-child { font-size:12.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; }
.bomx-cost-total-pill {
 font-size:13.5px; font-weight:700;
  background:rgba(255,255,255,.18); padding:4px 12px; border-radius:999px;
}
.bomx-cost-card-body {
  display:flex; align-items:center; gap:14px;
  padding:20px 18px; flex-wrap:wrap;
}
.bomx-cost-item { flex:1 1 140px; min-width:140px; }
.bomx-cost-item-lbl {
  display:flex; align-items:center; gap:7px;
  font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em;
  color:var(--bx-muted); margin-bottom:6px;
}
.bomx-cost-dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
.bomx-cost-item-val { font-size:17px; font-weight:600; color:var(--bx-text); }
.bomx-cost-item--total {
  background:#fff; border:1px solid var(--bx-mfg); border-radius:var(--bx-rmd,10px);
  padding:10px 14px; flex:1 1 160px; min-width:160px;
}
.bomx-cost-item-val--total { font-size:19px; font-weight:800; color:var(--bx-mfgB); }
.bomx-cost-plus, .bomx-cost-eq {
  font-size:20px; font-weight:700; color:var(--bx-muted); flex:0 0 auto; padding-bottom:2px;
}
@media (max-width:560px) {
  .bomx-cost-card-body { flex-direction:column; align-items:stretch; }
  .bomx-cost-plus, .bomx-cost-eq { display:none; }
}

@media (max-width:640px) {
  .bomx-rm-card-body { grid-template-columns:1fr; }
}

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

/* ── Modal ── */
.bomx-modal-overlay { position:fixed; inset:0; background:rgba(17,24,39,.5); display:flex; align-items:center; justify-content:center; z-index:1000; }
.bomx-modal { background:#fff; border-radius:12px; padding:22px; max-width:94vw; box-shadow:0 20px 50px rgba(0,0,0,.25); }
.bomx-modal-title { font-size:16px; font-weight:700; color:var(--bx-text); margin-bottom:14px; }
.bomx-modal-body { font-size:13.5px; color:var(--bx-text); line-height:1.5; }
.bomx-modal-actions { display:flex; justify-content:flex-end; gap:10px; margin-top:18px; }

.shimmer { background:linear-gradient(90deg,#f1f3f5 25%,#e9ecef 37%,#f1f3f5 63%); background-size:400% 100%; animation:shimmer 1.4s ease infinite; }
@keyframes shimmer { 0%{background-position:100% 50%} 100%{background-position:0 50%} }
</style>