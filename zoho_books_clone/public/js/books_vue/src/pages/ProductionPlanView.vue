<template>
<div class="sc-page">
  <div class="sc-sticky">
    <div class="sc-header">
      <div style="display:flex;align-items:center;gap:12px;">
        <button class="iv-back" @click="router.push('/manufacturing/production-plan')" style="background:none;border:none;cursor:pointer;color:#2563eb;display:flex;align-items:center;gap:4px;font-weight:600;font-size:13px;padding:0;">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
          Back
        </button>
        <span class="sc-title">{{ isNew ? 'New Production Plan' : pp.name }}</span>
        <div v-if="!isNew" class="inv-status-badge" style="font-size:12px;padding:3px 8px;border-radius:12px;" :style="statusStyle">
          {{ pp.status }}
        </div>
      </div>
      <div style="display:flex;gap:10px;">
        <button class="nim-btn" style="background:#fff;border:1px solid #e5e7eb;padding:8px 16px;border-radius:8px;font-weight:600;cursor:pointer;" @click="router.push('/manufacturing/production-plan')" :disabled="saving || submitting">Back</button>
        <button v-if="!isNew && pp.docstatus===2" class="sc-save-btn" @click="amendPP" :disabled="submitting">
          {{ submitting ? 'Amending...' : 'Amend' }}
        </button>
        <button v-if="!isNew && pp.docstatus===1" class="nim-btn" style="background:#fee2e2;color:#dc2626;border:1px solid #fecaca;padding:8px 16px;border-radius:8px;font-weight:600;cursor:pointer;" @click="cancelPP" :disabled="submitting">
          {{ submitting ? 'Cancelling...' : 'Cancel Plan' }}
        </button>
        <button v-if="!isNew && pp.docstatus===0" class="sc-save-btn" @click="submitPP" :disabled="submitting || saving">
          {{ submitting ? 'Submitting...' : 'Submit' }}
        </button>
        <button v-if="!readOnly" class="sc-save-btn" @click="save" :disabled="saving || loading">
          <span v-if="saving" style="display:inline-block;width:12px;height:12px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .6s linear infinite;margin-right:6px;"></span>
          {{ isNew ? 'Save Production Plan' : 'Save Changes' }}
        </button>
      </div>
    </div>
    <div class="sc-tabs">
      <button v-for="t in tabs" :key="t.id" class="sc-tab" :class="{ 'sc-tab--active': activeTab === t.id }" @click="activeTab = t.id">
        {{ t.label }}
      </button>
    </div>
  </div>

  <!-- Tab 1: Plan (demand + items) -->
  <div v-if="activeTab === 'plan'" class="sc-body sc-body--narrow">
    <div class="sc-col-main">

      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
          </div>
          <div>
            <div class="sc-card-title">Plan Details</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-fg">
          <div class="nim-field">
            <label class="nim-label">Posting Date</label>
            <input type="date" class="nim-input" v-model="pp.posting_date" :disabled="readOnly" />
          </div>
        </div>
      </div>

      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon" style="background:#fee2e2;color:#dc2626;box-shadow:inset 0 0 0 1px rgba(220,38,38,.08), 0 2px 6px rgba(220,38,38,.12);">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="10" rx="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
          </div>
          <div><div class="sc-card-title">Default Warehouses</div></div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-fg" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Default Source Warehouse (Raw Materials)</label>
            <select class="nim-input" v-model="pp.default_source_warehouse" :disabled="readOnly">
              <option value="">— Select —</option>
              <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
            </select>
            <div class="sc-field-hint">Also the warehouse checked for availability on the Raw Materials tab.</div>
          </div>
          <div class="nim-field">
            <label class="nim-label">Default Work-in-Progress Warehouse</label>
            <select class="nim-input" v-model="pp.default_wip_warehouse" :disabled="readOnly">
              <option value="">— None —</option>
              <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
            </select>
          </div>
        </div>
        <div class="sc-fg">
          <div class="nim-field">
            <label class="nim-label">Default Finished Goods Warehouse <span class="sc-required">*</span></label>
            <select class="nim-input" v-model="pp.default_fg_warehouse" :disabled="readOnly">
              <option value="">— Select —</option>
              <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
            </select>
          </div>
          <div class="nim-field">
            <label class="nim-label">Default Scrap / By-Product Warehouse</label>
            <select class="nim-input" v-model="pp.default_scrap_warehouse" :disabled="readOnly">
              <option value="">— Defaults to Finished Goods Warehouse —</option>
              <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
            </select>
          </div>
        </div>
      </div>

      <div class="sc-card" style="max-width:100%;overflow-x:auto;">
        <div class="sc-card-header" style="justify-content:space-between;">
          <div style="display:flex;align-items:center;gap:14px;">
            <div class="sc-card-icon sc-card-icon--blue">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 12l2 2 4-4"></path><circle cx="12" cy="12" r="10"></circle></svg>
            </div>
            <div>
              <div class="sc-card-title">Demand from Sales Orders</div>
              <div class="sc-card-subtitle">Optional — pull pending qty from open Sales Orders as a starting point.</div>
            </div>
          </div>
          <div style="display:flex;gap:8px;" v-if="!readOnly">
            <button class="sc-upload-btn" @click="openSOPicker">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
              Add Sales Orders
            </button>
            <button class="sc-upload-btn" @click="pullItemsFromSalesOrders" :disabled="itemsLoading || !pp.sales_orders.length">
              {{ itemsLoading ? 'Pulling…' : 'Pull / Refresh Items' }}
            </button>
          </div>
        </div>
        <div class="sc-divider"></div>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead>
            <tr>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Sales Order</th>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Customer</th>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Delivery Date</th>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">SO Status</th>
              <th v-if="!readOnly" style="width:40px;border-bottom:1px solid #e5e7eb;"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!pp.sales_orders || !pp.sales_orders.length">
              <td colspan="5" style="text-align:center;padding:24px;color:#9ca3af;">No Sales Orders added yet.</td>
            </tr>
            <tr v-for="(so, idx) in pp.sales_orders" :key="idx">
              <td style="padding:8px;"><span class="inv-link">{{ so.sales_order }}</span></td>
              <td style="padding:8px;">{{ so.customer }}</td>
              <td style="padding:8px;">{{ fmtDate(so.delivery_date) }}</td>
              <td style="padding:8px;">{{ so.status }}</td>
              <td v-if="!readOnly" style="padding:8px;text-align:center;">
                <button @click="pp.sales_orders.splice(idx,1)" style="background:none;border:none;color:#dc2626;cursor:pointer;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="sc-card" style="max-width:100%;overflow-x:auto;">
        <div class="sc-card-header" style="justify-content:space-between;">
          <div style="display:flex;align-items:center;gap:14px;">
            <div class="sc-card-icon sc-card-icon--blue">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>
            </div>
            <div><div class="sc-card-title">Items to Manufacture</div></div>
          </div>
          <button v-if="!readOnly" class="sc-upload-btn" @click="addPOItem">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
            Add Row
          </button>
        </div>
        <div class="sc-divider"></div>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead>
            <tr>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Item to Manufacture</th>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">BOM</th>
              <th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Planned Qty</th>
              <th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">WO Created</th>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">FG Warehouse</th>
              <th v-if="!readOnly" style="width:40px;border-bottom:1px solid #e5e7eb;"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!pp.po_items || !pp.po_items.length">
              <td colspan="6" style="text-align:center;padding:24px;color:#9ca3af;">No items yet. Pull from Sales Orders above, or add a row manually.</td>
            </tr>
            <tr v-for="(row, idx) in pp.po_items" :key="idx">
              <td style="padding:6px;">
                <select class="nim-input" style="padding:6px 10px;" v-model="row.item_code" @change="onPOItemChange(row)" :disabled="readOnly">
                  <option value="">— Select —</option>
                  <option v-for="i in stockItems" :key="i.name" :value="i.name">{{ i.item_name || i.name }}</option>
                </select>
              </td>
              <td style="padding:6px;">
                <select class="nim-input" style="padding:6px 10px;" v-model="row.bom_no" :disabled="readOnly">
                  <option value="">— Select Submitted BOM —</option>
                  <option v-for="b in bomsFor(row.item_code)" :key="b.name" :value="b.name">{{ b.name }}</option>
                </select>
              </td>
              <td style="padding:6px;"><input type="number" class="nim-input" style="padding:6px 10px;text-align:right;" v-model="row.planned_qty" min="0.01" step="any" :disabled="readOnly"/></td>
              <td style="padding:6px;text-align:right;vertical-align:middle;color:#6b7280;">{{ fmt(row.work_order_created_qty) }}</td>
              <td style="padding:6px;">
                <select class="nim-input" style="padding:6px 10px;" v-model="row.warehouse" :disabled="readOnly">
                  <option value="">— Use Default —</option>
                  <option v-for="w in warehouseList" :key="w.name" :value="w.name">{{ w.name }}</option>
                </select>
              </td>
              <td v-if="!readOnly" style="padding:6px;text-align:center;vertical-align:middle;">
                <button @click="pp.po_items.splice(idx,1)" style="background:none;border:none;color:#dc2626;cursor:pointer;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

    </div>
  </div>

  <!-- Tab 2: Raw Materials -->
  <div v-if="activeTab === 'materials'" class="sc-body sc-body--narrow">
    <div class="sc-col-main">
      <div class="sc-card">
        <div class="sc-card-header" style="justify-content:space-between;">
          <div>
            <div class="sc-card-title">Raw Material Requirement</div>
            <div class="sc-card-subtitle">Explodes the BOM for every Item to Manufacture and compares against on-hand stock in the Default Source Warehouse.</div>
          </div>
          <div style="display:flex;gap:8px;">
            <button v-if="!isNew && pp.docstatus===1 && hasShortfall" class="sc-upload-btn" @click="createMaterialRequests" :disabled="actionLoading==='mr'">
              {{ actionLoading === 'mr' ? 'Creating…' : 'Create Material Requests' }}
            </button>
            <button class="sc-save-btn" @click="calculateRawMaterials" :disabled="mrLoading || !pp.po_items.length">
              {{ mrLoading ? 'Calculating…' : 'Calculate Requirement' }}
            </button>
          </div>
        </div>
      </div>

      <div class="sc-card" style="max-width:100%;overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead>
            <tr>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Raw Material</th>
              <th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Required Qty</th>
              <th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Available Qty</th>
              <th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Shortfall</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!pp.mr_items || !pp.mr_items.length">
              <td colspan="4" style="text-align:center;padding:24px;color:#9ca3af;">No requirement calculated yet. Click "Calculate Requirement" above.</td>
            </tr>
            <tr v-for="(m, idx) in pp.mr_items" :key="idx" :style="flt(m.shortfall_qty) > 0 ? 'background:#fef2f2;' : ''">
              <td style="padding:8px;">{{ m.item_name || m.item_code }}</td>
              <td style="padding:8px;text-align:right;">{{ fmt(m.required_qty) }} {{ m.uom }}</td>
              <td style="padding:8px;text-align:right;">{{ fmt(m.available_qty) }}</td>
              <td style="padding:8px;text-align:right;font-weight:700;" :style="flt(m.shortfall_qty) > 0 ? 'color:#dc2626;' : 'color:#16a34a;'">
                {{ flt(m.shortfall_qty) > 0 ? fmt(m.shortfall_qty) : '—' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Tab 3: Work Orders -->
  <div v-if="activeTab === 'work-orders'" class="sc-body sc-body--narrow">
    <div class="sc-col-main">
      <div v-if="isNew" class="sc-card"><div class="sc-card-subtitle">Save and submit the Production Plan first to create Work Orders.</div></div>
      <template v-else>
        <div class="sc-card" v-if="pp.docstatus===1">
          <div class="sc-card-header" style="justify-content:space-between;">
            <div>
              <div class="sc-card-title">Create Work Orders</div>
              <div class="sc-card-subtitle">Generates one Draft Work Order per row for whatever Planned Qty doesn't already have one. Review and submit each Work Order from there.</div>
            </div>
            <div style="display:flex;gap:8px;">
              <button v-if="hasDraftWorkOrders" class="sc-upload-btn" @click="bulkSubmitWorkOrders" :disabled="actionLoading==='bulk-submit'">
                {{ actionLoading === 'bulk-submit' ? 'Submitting…' : 'Submit All Work Orders' }}
              </button>
              <button class="sc-save-btn" @click="createWorkOrders" :disabled="actionLoading || !pendingWOQty">
                {{ actionLoading==='wo' ? 'Creating…' : 'Create Work Orders' }}
              </button>
            </div>
          </div>
          <div class="sc-field-hint" v-if="!pendingWOQty">Every row already has a Work Order for its full Planned Qty.</div>
        </div>

        <div class="sc-card" style="max-width:100%;overflow-x:auto;">
          <div class="sc-card-header" style="justify-content:space-between;">
            <div class="sc-card-title">Linked Work Orders</div>
            <button class="sc-upload-btn" @click="loadWorkOrders" :disabled="woLoading">Refresh</button>
          </div>
          <div class="sc-divider"></div>
          <table style="width:100%;border-collapse:collapse;font-size:13px;" v-if="workOrders.length">
            <thead><tr>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Work Order</th>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Item</th>
              <th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Qty</th>
              <th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-weight:600;font-size:12px;">Status</th>
            </tr></thead>
            <tbody>
              <tr v-for="w in workOrders" :key="w.name" class="inv-row" style="cursor:pointer;" @click="router.push(`/manufacturing/work-order/${w.name}`)">
                <td style="padding:8px;"><span class="inv-link">{{ w.name }}</span></td>
                <td style="padding:8px;">{{ w.item_name || w.production_item }}</td>
                <td style="padding:8px;text-align:right;">{{ fmt(w.qty) }}</td>
                <td style="padding:8px;">{{ w.status }}</td>
              </tr>
            </tbody>
          </table>
          <div v-else style="text-align:center;padding:24px;color:#9ca3af;">No Work Orders created yet.</div>
        </div>
      </template>
    </div>
  </div>

  <!-- Tab 4: More Information -->
  <div v-if="activeTab === 'more'" class="sc-body sc-body--narrow">
    <div class="sc-col-main">
      <div class="sc-card">
        <div class="sc-card-header"><div class="sc-card-title">More Information</div></div>
        <div class="sc-divider"></div>
        <div class="sc-fg sc-fg--single" style="margin-bottom:14px">
          <div class="nim-field">
            <label class="nim-label">Remarks</label>
            <textarea class="nim-input" rows="3" v-model="pp.remarks" :disabled="readOnly"></textarea>
          </div>
        </div>
        <div class="sc-fg" v-if="pp.amended_from">
          <div class="nim-field">
            <label class="nim-label">Amended From</label>
            <span class="inv-link" style="cursor:pointer;" @click="router.push(`/manufacturing/production-plan/${pp.amended_from}`)">{{ pp.amended_from }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Sales Order picker modal -->
  <div v-if="showSOPickerModal" class="iv-modal-overlay" @click.self="showSOPickerModal=false">
    <div class="iv-modal" style="width:560px;">
      <div class="iv-modal-title">Add Sales Orders</div>
      <div class="iv-modal-body">
        <div v-if="soPickerLoading" style="text-align:center;padding:20px;color:#9ca3af;">Loading open Sales Orders…</div>
        <div v-else-if="!soPickerList.length" style="text-align:center;padding:20px;color:#9ca3af;">No open Sales Orders with pending delivery found.</div>
        <table v-else style="width:100%;border-collapse:collapse;font-size:13px;max-height:360px;overflow-y:auto;">
          <tbody>
            <tr v-for="o in soPickerList" :key="o.name" style="cursor:pointer;" @click="toggleSOPick(o.name)">
              <td style="padding:6px 4px;width:24px;"><input type="checkbox" :checked="soPickerSelected.includes(o.name)" @click.stop="toggleSOPick(o.name)"/></td>
              <td style="padding:6px 4px;font-weight:600;">{{ o.name }}</td>
              <td style="padding:6px 4px;color:#6b7280;">{{ o.customer_name }}</td>
              <td style="padding:6px 4px;color:#6b7280;">{{ fmtDate(o.delivery_date) }}</td>
              <td style="padding:6px 4px;color:#6b7280;">{{ o.status }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="iv-modal-actions">
        <button class="nim-btn" style="background:#fff;border:1px solid #e5e7eb;padding:8px 16px;border-radius:8px;font-weight:600;cursor:pointer;" @click="showSOPickerModal=false">Cancel</button>
        <button class="sc-save-btn" @click="confirmSOPicker" :disabled="!soPickerSelected.length">Add {{ soPickerSelected.length || '' }}</button>
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

const ENGINE = "zoho_books_clone.manufacturing.production_plan_engine.";

const route = useRoute();
const router = useRouter();
const { toast } = useToast();

const isNew = computed(() => route.params.name === "new");
const loading = ref(true);
const saving = ref(false);
const submitting = ref(false);
const itemsLoading = ref(false);
const mrLoading = ref(false);
const actionLoading = ref(false);
const woLoading = ref(false);

const activeTab = ref("plan");
const tabs = [
  { id: "plan",         label: "Plan" },
  { id: "materials",    label: "Raw Materials" },
  { id: "work-orders",  label: "Work Orders" },
  { id: "more",          label: "More Information" },
];

const pp = ref({
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
});

const stockItems = ref([]);
const bomList = ref([]);
const warehouseList = ref([]);
const workOrders = ref([]);

const EMPTY_PO_ITEM = () => ({ item_code: "", item_name: "", bom_no: "", planned_qty: 1, stock_uom: "", warehouse: "", sales_order: "", work_order_created_qty: 0 });

// docstatus: 0 = Draft, 1 = Submitted, 2 = Cancelled. Once submitted, the
// plan (items/warehouses/sales orders) is locked — from here on, progress
// happens only through Create Work Orders on the Work Orders tab.
const readOnly = computed(() => !isNew.value && (pp.value.docstatus === 1 || pp.value.docstatus === 2));

const statusStyle = computed(() => {
  const s = pp.value.status;
  if (s === "Completed" || s === "Work Orders Created") return "background:#dcfce7;color:#16a34a";
  if (s === "Cancelled") return "background:#fee2e2;color:#dc2626";
  if (s === "Draft") return "background:#fef3c7;color:#b45309";
  return "background:#dbeafe;color:#1e40af";
});

onMounted(async () => {
  loading.value = true;
  try {
    const co = await resolveCompany();
    if (isNew.value) pp.value.company = co;

    const stk = await apiList("Item", { fields: ["name", "item_name", "stock_uom"], filters: [["is_stock_item", "=", 1]], limit: 5000, order: "name asc" });
    stockItems.value = stk || [];

    const boms = await apiList("BOM", { fields: ["name", "item", "quantity", "is_default", "docstatus"], filters: [["docstatus", "=", 1]], limit: 2000, order: "name asc" });
    bomList.value = boms || [];

    const whs = await apiList("Warehouse", { fields: ["name"], filters: co ? [["company", "=", co], ["is_group", "=", 0]] : [["is_group", "=", 0]], limit: 1000, order: "name asc" });
    warehouseList.value = whs || [];

    await loadPP();
  } catch (e) {
    toast("Error loading data: " + e.message, "error");
    router.push("/manufacturing/production-plan");
  }
  loading.value = false;
});

async function loadPP() {
  if (!isNew.value) {
    const data = await apiGet("Production Plan", route.params.name);
    pp.value = data;
    if (!pp.value.sales_orders) pp.value.sales_orders = [];
    if (!pp.value.po_items) pp.value.po_items = [];
    if (!pp.value.mr_items) pp.value.mr_items = [];
    if (pp.value.docstatus === 1) await loadWorkOrders();
  }
}

watch(() => route.params.name, () => {
  loadPP().catch((e) => toast("Error loading Production Plan: " + e.message, "error"));
});

function bomsFor(itemCode) {
  if (!itemCode) return bomList.value;
  return bomList.value.filter(b => b.item === itemCode);
}

function onPOItemChange(row) {
  const item = stockItems.value.find(i => i.name === row.item_code);
  row.item_name = item ? item.item_name : "";
  row.stock_uom = item ? item.stock_uom : "";
  const candidates = bomsFor(row.item_code);
  const def = candidates.find(b => b.is_default) || candidates[0];
  row.bom_no = def ? def.name : "";
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
    pp.value.po_items = [...manual, ...(items || []).map(i => ({ ...EMPTY_PO_ITEM(), ...i }))];
    toast(`Pulled ${(items || []).length} item(s) from ${soNames.length} Sales Order(s)`);
  } catch (e) {
    toast(e.message, "error");
  }
  itemsLoading.value = false;
}

// ── Raw Materials ────────────────────────────────────────────────────────
async function calculateRawMaterials() {
  if (!pp.value.po_items.length) return toast("Add items to manufacture first", "error");
  mrLoading.value = true;
  try {
    const rows = pp.value.po_items.map(r => ({ item_code: r.item_code, bom_no: r.bom_no, planned_qty: r.planned_qty }));
    pp.value.mr_items = await apiCall(ENGINE + "get_raw_materials", { po_items: rows, warehouse: pp.value.default_source_warehouse || undefined });
    toast("Raw material requirement calculated");
  } catch (e) {
    toast(e.message, "error");
  }
  mrLoading.value = false;
}

// ── Work Orders ──────────────────────────────────────────────────────────
const pendingWOQty = computed(() => (pp.value.po_items || []).some(r => flt(r.planned_qty) - flt(r.work_order_created_qty) > 0.0001));
const hasShortfall = computed(() => (pp.value.mr_items || []).some(r => flt(r.shortfall_qty) > 0.0001));
const hasDraftWorkOrders = computed(() => workOrders.value.some(w => w.status === "Draft"));

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