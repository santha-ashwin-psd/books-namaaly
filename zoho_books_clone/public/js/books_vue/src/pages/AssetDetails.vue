<template>
  <Teleport to="body">
    <div class="inv-drawer-bg" @click.self="cancelGuarded">
      <div class="inv-drawer-panel is-add">

        <!-- Header -->
        <div class="inv-dh">
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
            <div class="inv-dh-title">{{ isNew ? 'New Asset' : 'Edit Asset' }}</div>
            <span v-if="isNew" class="add-status-badge">Draft</span>
          </div>
          <div style="display:flex;align-items:center;gap:8px">
            <button class="inv-dclose" @click="cancelGuarded" title="Close"><span v-html="icon('x',16)"></span></button>
          </div>
        </div>

        <!-- Body -->
        <div class="inv-dbody">

          <!-- General Information -->
          <div class="add-card">
            <div class="add-card-header" @click="collapsed.general = !collapsed.general">
              <div class="add-card-title">
                <span class="add-card-title-icon"><span v-html="icon('purchase',16)"></span></span>
                General Information
              </div>
              <span class="add-card-chevron" :class="{collapsed:collapsed.general}"><span v-html="icon('chevD',14)"></span></span>
            </div>
            <div class="add-card-body" :class="{collapsed:collapsed.general}">
              <div class="inv-fg inv-fg2">
                <div>
                  <label class="inv-lbl">Asset Name <span class="inv-req">*</span></label>
                  <input v-model="asset.asset_name" class="inv-fi" required autocomplete="off" placeholder="e.g. Dell Laptop XPS 15"/>
                </div>
                <div>
                  <label class="inv-lbl">Asset Category <span class="inv-req">*</span></label>
                  <select v-model="asset.asset_category" class="inv-fi" required :disabled="financialsLocked">
                    <option value="">Select category</option>
                    <option v-for="category in categories" :key="category.name" :value="category.name">{{ category.category_name || category.name }}</option>
                  </select>
                </div>
                <div>
                  <label class="inv-lbl">Status</label>
                  <div class="inv-fi" style="background:#f8fafc;color:#475569;display:flex;align-items:center;">
                    {{ asset.status || 'Draft' }}
                  </div>
                </div>
                <div>
                  <label class="inv-lbl">Company</label>
                  <SearchableSelect
                    v-model="asset.company"
                    :options="companies"
                    placeholder="Company name"
                    :disabled="financialsLocked"
                    @search="fetchCompanies"
                  />
                </div>
              </div>
              <p v-if="financialsLocked" class="asset-locked-hint">
                This asset is submitted — its capitalization entry has already posted to the ledger, so Category and Company are locked to keep the books consistent. Use Asset Value Adjustment, Asset Quantity Adjustment, or Asset Disposal for changes after submit.
              </p>
            </div>
          </div>

          <!-- Purchase Details -->
          <div class="add-card">
            <div class="add-card-header" @click="collapsed.purchase = !collapsed.purchase">
              <div class="add-card-title">
                <span class="add-card-title-icon"><span v-html="icon('rupee',16)"></span></span>
                Purchase Details
              </div>
              <span class="add-card-chevron" :class="{collapsed:collapsed.purchase}"><span v-html="icon('chevD',14)"></span></span>
            </div>
            <div class="add-card-body" :class="{collapsed:collapsed.purchase}">
              <div class="inv-fg inv-fg3 asset-fg4">
                <div>
                  <label class="inv-lbl">Purchase Date <span class="inv-req">*</span></label>
                  <input v-model="asset.purchase_date" type="date" class="inv-fi" :disabled="financialsLocked"/>
                </div>
                <div>
                  <label class="inv-lbl">Qty <span class="inv-req">*</span></label>
                  <input v-model.number="asset.qty" type="number" min="1" step="1" class="inv-fi" placeholder="1" :disabled="financialsLocked"/>
                </div>
                <div v-if="!asset.is_existing_asset">
                  <label class="inv-lbl">Taxable Value <span class="inv-req">*</span></label>
                  <input v-model.number="asset.taxable_value" type="number" step="0.01" min="0" class="inv-fi" placeholder="0.00" @input="recalcTotals" :disabled="financialsLocked"/>
                </div>
                <div v-else>
                  <label class="inv-lbl">Purchase Cost <span class="inv-req">*</span></label>
                  <input v-model.number="asset.purchase_cost" type="number" step="0.01" min="0" class="inv-fi" placeholder="0.00" :disabled="financialsLocked"/>
                </div>
                <div>
                  <label class="inv-lbl">Supplier</label>
                  <SearchableSelect
                    v-model="asset.supplier"
                    :options="suppliers"
                    placeholder="Vendor / supplier"
                    createable
                    create-doctype="Supplier"
                    :disabled="financialsLocked"
                    @search="fetchSuppliers"
                  />
                </div>
              </div>

              <!-- Tax Lines (not applicable to existing/opening assets -- backend skips tax bookkeeping for them) -->
              <div class="asset-tax-block" v-if="!asset.is_existing_asset">
                <div class="asset-tax-head">
                  <span class="inv-lbl" style="margin:0">Taxes</span>
                  <button type="button" class="asset-tax-add" @click="addTaxRow" :disabled="financialsLocked">
                    <span v-html="icon('plus',12)"></span> Add Tax
                  </button>
                </div>

                <div v-if="asset.taxes && asset.taxes.length" class="asset-tax-table">
                  <div class="asset-tax-row asset-tax-row-head">
                    <div>Tax Type</div>
                    <div>Rate (%)</div>
                    <div>ITC Eligible</div>
                    <div>Account Head</div>
                    <div class="ta-r">Amount</div>
                    <div></div>
                  </div>
                  <div v-for="(row, idx) in asset.taxes" :key="row._id" class="asset-tax-row">
                    <select v-model="row.tax_type" class="inv-fi" :disabled="financialsLocked">
                      <option value="">Select</option>
                      <option>CGST</option>
                      <option>SGST</option>
                      <option>IGST</option>
                      <option>VAT</option>
                      <option>Cess</option>
                      <option>Other</option>
                    </select>
                    <input v-model.number="row.rate" type="number" step="0.01" min="0" class="inv-fi" placeholder="0" @input="recalcTotals" :disabled="financialsLocked"/>
                    <label class="ad-switch" style="margin:auto">
                      <input type="checkbox" :checked="!!row.is_itc_eligible" :disabled="financialsLocked" @change="row.is_itc_eligible = $event.target.checked ? 1 : 0; recalcTotals()"/>
                      <span class="ad-switch-track"></span>
                    </label>
                    <SearchableSelect
                      v-model="row.account_head"
                      :options="taxAccountOptions"
                      placeholder="Default (category)"
                      :disabled="financialsLocked || !row.is_itc_eligible"
                      @search="fetchTaxAccounts"
                    />
                    <div class="ta-r mono-sm">{{ fmt(row.amount || 0) }}</div>
                    <button type="button" class="asset-tax-remove" @click="removeTaxRow(idx)" title="Remove" :disabled="financialsLocked">
                      <span v-html="icon('x',13)"></span>
                    </button>
                  </div>
                </div>
                <div v-else class="asset-tax-empty">No tax lines. Click "Add Tax" if GST or another tax applies to this purchase.</div>

                <div class="asset-tax-totals">
                  <div><span>Total Tax</span><span>{{ fmt(asset.total_tax || 0) }}</span></div>
                  <div><span>Purchase Cost (capitalized)</span><span>{{ fmt(asset.purchase_cost || 0) }}</span></div>
                  <div class="fw-700"><span>Grand Total</span><span>{{ fmt(asset.grand_total || 0) }}</span></div>
                </div>
                <div style="font-size:11px;color:#94a3b8;margin-top:6px">
                  ITC-eligible tax posts to the category's GST Input Account and is excluded from Purchase Cost. Non-eligible tax is folded into Purchase Cost and depreciated with the asset.
                </div>
              </div>
              <div v-else style="font-size:11px;color:#94a3b8;margin-top:14px">
                Existing asset: enter its current book value directly in Purchase Cost above. No capitalization tax entry is posted for opening assets.
              </div>

              <label class="add-toggle-row" style="margin-top:14px">
                <span>Existing Asset (already on the books)</span>
                <span class="ad-switch">
                  <input type="checkbox" :checked="!!asset.is_existing_asset" :disabled="financialsLocked" @change="asset.is_existing_asset=$event.target.checked?1:0"/>
                  <span class="ad-switch-track"></span>
                </span>
              </label>
              <div v-if="!asset.is_existing_asset" class="inv-fg" style="margin-top:14px">
                <div>
                  <label class="inv-lbl">Credit Account (Payable / Bank / Cash) <span class="inv-req">*</span></label>
                  <SearchableSelect
                    v-model="asset.credit_account"
                    :options="creditAccountOptions"
                    placeholder="Account credited on capitalization"
                    :disabled="financialsLocked"
                    @search="fetchCreditAccounts"
                  />
                  <div style="font-size:11px;color:#94a3b8;margin-top:4px">
                    Posted on submit: Dr Fixed Asset (from category) / Cr this account, for the Purchase Cost above.
                  </div>
                </div>
              </div>
              <p v-if="financialsLocked" class="asset-locked-hint">
                Purchase details are locked after submit — the capitalization entry for this Purchase Cost has already posted to the ledger.
              </p>
            </div>
          </div>

          <!-- Location & Assignment -->
          <div class="add-card">
            <div class="add-card-header" @click="collapsed.location = !collapsed.location">
              <div class="add-card-title">
                <span class="add-card-title-icon"><span v-html="icon('map-pin',16)"></span></span>
                Location &amp; Assignment
              </div>
              <span class="add-card-chevron" :class="{collapsed:collapsed.location}"><span v-html="icon('chevD',14)"></span></span>
            </div>
            <div class="add-card-body" :class="{collapsed:collapsed.location}">
              <div class="inv-fg inv-fg2">
                <div>
                  <label class="inv-lbl">Location</label>
                  <input v-model="asset.location" class="inv-fi" autocomplete="off" placeholder="e.g. Warehouse A"/>
                </div>
                <div>
                  <label class="inv-lbl">Department</label>
                  <select v-model="asset.department" class="inv-fi">
                    <option value="">Select department</option>
                    <option v-for="department in departments" :key="department.name" :value="department.name">{{ department.name }}</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          <!-- Depreciation -->
          <div class="add-card">
            <div class="add-card-header" @click="collapsed.depreciation = !collapsed.depreciation">
              <div class="add-card-title">
                <span class="add-card-title-icon"><span v-html="icon('trend',16)"></span></span>
                Depreciation
              </div>
              <span class="add-card-chevron" :class="{collapsed:collapsed.depreciation}"><span v-html="icon('chevD',14)"></span></span>
            </div>
            <div class="add-card-body" :class="{collapsed:collapsed.depreciation}">
              <div class="inv-fg inv-fg2">
                <div>
                  <label class="inv-lbl">Method</label>
                  <select v-model="asset.depreciation_method" class="inv-fi" :disabled="depreciationLocked">
                    <option value="">Select method</option>
                    <option>Straight Line</option>
                    <option>Written Down Value</option>
                  </select>
                </div>
                <div>
                  <label class="inv-lbl">Useful Life (Years)</label>
                  <input v-model.number="asset.useful_life" type="number" class="inv-fi" placeholder="e.g. 5" :disabled="depreciationLocked"/>
                </div>
                <div>
                  <label class="inv-lbl">Salvage Value</label>
                  <input v-model.number="asset.salvage_value" type="number" step="0.01" class="inv-fi" placeholder="0.00" :disabled="depreciationLocked"/>
                </div>
                <div>
                  <label class="inv-lbl">Current Value</label>
                  <div class="inv-fi" style="background:#f8fafc;color:#475569;display:flex;align-items:center;">
                    {{ fmt(asset.current_value || 0) }}
                  </div>
                </div>
              </div>
              <p v-if="depreciationLocked" class="asset-locked-hint">
                One or more depreciation periods have already posted. Method, Useful Life, and Salvage Value are locked here to avoid silently invalidating posted history — use a dedicated depreciation revision flow if the schedule genuinely needs to change.
              </p>
            </div>
          </div>

          <!-- Maintenance -->
          <div class="add-card">
            <div class="add-card-header" @click="collapsed.maintenance = !collapsed.maintenance">
              <div class="add-card-title">
                <span class="add-card-title-icon"><span v-html="icon('calendar',16)"></span></span>
                Maintenance
              </div>
              <span class="add-card-chevron" :class="{collapsed:collapsed.maintenance}"><span v-html="icon('chevD',14)"></span></span>
            </div>
            <div class="add-card-body" :class="{collapsed:collapsed.maintenance}">
              <div class="inv-fg inv-fg3">
                <div>
                  <label class="inv-lbl">Last Maintenance Date</label>
                  <input v-model="asset.last_maintenance_date" type="date" class="inv-fi"/>
                </div>
                <div>
                  <label class="inv-lbl">Next Maintenance Date</label>
                  <input v-model="asset.next_maintenance_date" type="date" class="inv-fi"/>
                </div>
                <div>
                  <label class="inv-lbl">Maintenance Frequency (Days)</label>
                  <input v-model.number="asset.maintenance_frequency_days" type="number" class="inv-fi" placeholder="e.g. 90"/>
                </div>
              </div>
            </div>
          </div>

          <!-- Additional Details -->
          <div class="add-card">
            <div class="add-card-header" @click="collapsed.additional = !collapsed.additional">
              <div class="add-card-title">
                <span class="add-card-title-icon"><span v-html="icon('file',16)"></span></span>
                Additional Details
              </div>
              <span class="add-card-chevron" :class="{collapsed:collapsed.additional}"><span v-html="icon('chevD',14)"></span></span>
            </div>
            <div class="add-card-body" :class="{collapsed:collapsed.additional}">
              <label class="inv-lbl">Description</label>
              <textarea v-model="asset.description" class="inv-fi" rows="3" placeholder="Brief description of this asset" style="margin-bottom:14px"></textarea>
              <label class="add-toggle-row">
                <span>Active</span>
                <span class="ad-switch">
                  <input type="checkbox" :checked="!!asset.is_active" @change="asset.is_active=$event.target.checked?1:0"/>
                  <span class="ad-switch-track"></span>
                </span>
              </label>
            </div>
          </div>

        </div>

        <!-- Footer -->
        <div class="inv-dfooter">
          <div class="add-footer-status">{{ isNew ? 'New asset — unsaved changes' : 'Editing: ' + (asset.name || '') }}</div>
          <div class="add-footer-actions">
            <button class="add-btn-cancel" @click="cancelGuarded">Cancel</button>
            <button class="add-btn-draft" :disabled="saving || !(isNew ? $canCreate('inventory') : $canEdit('inventory'))" @click="saveAsset('Draft')">
              <span v-html="icon('save',13)"></span> Save Draft
            </button>
            <button class="add-btn-more" :disabled="saving || !(isNew ? $canCreate('inventory') : $canEdit('inventory'))" @click="saveAsset('Submitted')">
              <span v-html="icon('check',13)"></span> {{ saving ? 'Saving…' : 'Save & Submit' }}
            </button>
          </div>
        </div>

      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { apiGet, apiList, apiSave, apiSubmit, apiLinkValues } from '@/api/client.js';
import { useToast } from '@/composables/useToast.js';
import { useConfirm } from '@/composables/useConfirm.js';
import { icon } from '@/utils/icons.js';
import SearchableSelect from '@/components/SearchableSelect.vue';

const route = useRoute();
const router = useRouter();
const toast = useToast();
const { confirm } = useConfirm();

let _taxRowId = 1;
const blankAsset = () => ({
  doctype: 'Asset',
  asset_name: '',
  asset_category: '',
  status: 'Draft',
  company: window.__booksCompany || '',
  purchase_date: todayLocal(),
  qty: 1,
  taxable_value: 0,
  total_tax: 0,
  purchase_cost: 0,
  grand_total: 0,
  taxes: [],
  supplier: '',
  is_existing_asset: 0,
  credit_account: '',
  location: '',
  department: '',
  depreciation_method: 'Straight Line',
  useful_life: '',
  salvage_value: 0,
  current_value: 0,
  last_maintenance_date: '',
  next_maintenance_date: '',
  maintenance_frequency_days: '',
  description: '',
  is_active: 1,
});

const asset = ref(blankAsset());
const categories = ref([]);
const departments = ref([]);
const suppliers = ref([]);
const companies = ref([]);
const creditAccountOptions = ref([]);
const taxAccountOptions = ref([]);
const loading = ref(true);
const saving = ref(false);
let initialSnapshot = '';
const isDirty = computed(() => JSON.stringify(asset.value) !== initialSnapshot);

const collapsed = reactive({
  general: false,
  purchase: false,
  location: false,
  depreciation: false,
  maintenance: false,
  additional: false,
});

const isNew = computed(() => route.params.id === 'new');
// Once an asset is submitted, its capitalization GL entry has already been
// posted (post_asset_capitalization in asset_gl.py runs once, at submit).
// The backend's save_doc() sets ignore_validate_update_after_submit for every
// doctype, so nothing stops these fields from being edited and saved after
// submit — but Asset.calculate_totals() re-derives purchase_cost/grand_total
// on every save, and NOTHING re-posts the GL to match. Editing these after
// submit would silently desync the Asset's book value from the ledger. Lock
// them here; only operational metadata (location, maintenance, description,
// depreciation policy going forward) stays editable post-submit.
const financialsLocked = computed(() => !isNew.value && asset.value.docstatus === 1);

// generate_depreciation_schedule() on the backend refuses to regenerate once
// any row has status "Completed" (a posted depreciation entry) -- edits to
// method/useful_life/salvage_value at that point are silently a no-op. Match
// that here so the UI doesn't imply the change will take effect.
const depreciationLocked = computed(() =>
  (asset.value.depreciation_schedule || []).some(row => row.status === 'Completed')
);

async function loadLookups() {
  const [categoryRows, departmentRows] = await Promise.all([
    apiList('Asset Category', { fields: ['name', 'category_name'], order: 'name asc', limit: 500 }),
    apiList('Department', { fields: ['name'], order: 'name asc', limit: 500 }),
  ]);
  categories.value = categoryRows || [];
  departments.value = departmentRows || [];
}

async function fetchSuppliers(q = '') {
  try {
    const filters = [["disabled", "=", 0]];
    if (q) filters.push(["supplier_name", "like", `%${q}%`]);
    const rows = await apiList("Supplier", { fields: ["name", "supplier_name"], filters, limit: 30, order: "supplier_name asc" });
    suppliers.value = rows.map(r => ({ label: r.supplier_name || r.name, value: r.name }));
  } catch {
    suppliers.value = [];
  }
}

async function fetchCompanies(q = '') {
  try {
    const r = await apiList('Books Company', {
      fields: ['name', 'company_name'],
      filters: q ? [['company_name', 'like', `%${q}%`]] : [],
      limit: 100,
    });
    companies.value = (r || []).map(x => ({ label: x.company_name || x.name, value: x.name }));
  } catch {
    companies.value = [];
  }
  const co = window.__booksCompany || '';
  if (co && !companies.value.some(o => o.value === co)) {
    companies.value.unshift({ label: co, value: co });
  }
}

function fmt(n) {
  return (Number(n) || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function todayLocal() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function addTaxRow() {
  if (!Array.isArray(asset.value.taxes)) asset.value.taxes = [];
  asset.value.taxes.push({ _id: _taxRowId++, tax_type: '', rate: 0, is_itc_eligible: 0, amount: 0, account_head: '', description: '' });
}

function removeTaxRow(idx) {
  asset.value.taxes.splice(idx, 1);
  recalcTotals();
}

// Mirrors Asset.calculate_totals() on the backend so the totals shown here
// match what gets saved. The server recalculates authoritatively on save —
// this is a live preview only, not the source of truth.
function recalcTotals() {
  const taxableValue = Number(asset.value.taxable_value) || 0;
  let eligibleTax = 0;
  let nonEligibleTax = 0;
  for (const row of asset.value.taxes || []) {
    row.amount = Math.round(taxableValue * (Number(row.rate) || 0) / 100 * 100) / 100;
    if (row.is_itc_eligible) eligibleTax += row.amount;
    else nonEligibleTax += row.amount;
  }
  asset.value.total_tax = Math.round((eligibleTax + nonEligibleTax) * 100) / 100;
  asset.value.purchase_cost = Math.round((taxableValue + nonEligibleTax) * 100) / 100;
  asset.value.grand_total = Math.round((taxableValue + asset.value.total_tax) * 100) / 100;
}

async function fetchTaxAccounts(q = '') {
  try {
    const filters = [["is_group", "=", 0], ["disabled", "=", 0], ["account_type", "=", "Tax"]];
    if (asset.value.company) filters.push(["company", "=", asset.value.company]);
    if (q) filters.push(["name", "like", `%${q}%`]);
    const rows = await apiList("Account", { fields: ["name", "account_name"], filters, limit: 30, order: "name asc" });
    taxAccountOptions.value = rows.map(r => ({ label: r.account_name || r.name, value: r.name }));
  } catch {
    taxAccountOptions.value = [];
  }
}

async function fetchCreditAccounts(q = '') {
  try {
    const filters = [["is_group", "=", 0], ["disabled", "=", 0], ["account_type", "in", ["Payable", "Bank", "Cash"]]];
    if (asset.value.company) filters.push(["company", "=", asset.value.company]);
    if (q) filters.push(["name", "like", `%${q}%`]);
    const rows = await apiList("Account", { fields: ["name", "account_name"], filters, limit: 30, order: "name asc" });
    creditAccountOptions.value = rows.map(r => ({ label: r.account_name || r.name, value: r.name }));
  } catch {
    creditAccountOptions.value = [];
  }
}

async function loadAsset() {
  loading.value = true;
  try {
    await loadLookups();
    if (isNew.value) {
      asset.value = blankAsset();
    } else {
      const doc = await apiGet('Asset', route.params.id);
      asset.value = { ...blankAsset(), ...doc };
      asset.value.taxes = (asset.value.taxes || []).map(r => ({ ...r, _id: r._id || _taxRowId++ }));
    }
    initialSnapshot = JSON.stringify(asset.value);
  } catch (e) {
    toast.error('Failed to load asset: ' + e.message);
  } finally {
    loading.value = false;
  }
}

async function saveAsset(targetStatus) {
  if (saving.value) return;
  if (!(asset.value.asset_name || '').trim()) {
    toast.error('Asset Name is required.');
    collapsed.general = false;
    return;
  }
  if (!asset.value.asset_category) {
    toast.error('Asset Category is required.');
    collapsed.general = false;
    return;
  }
  if (!asset.value.company) {
    toast.error('Company is required.');
    collapsed.general = false;
    return;
  }
  if (targetStatus === 'Submitted' && !asset.value.is_existing_asset && !asset.value.credit_account) {
    toast.error('Credit Account is required to submit a non-existing asset (used for the capitalization entry).');
    collapsed.purchase = false;
    return;
  }
  if (!asset.value.qty || asset.value.qty < 1) {
    toast.error('Qty must be at least 1.');
    collapsed.purchase = false;
    return;
  }
  if (asset.value.is_existing_asset) {
    if (!asset.value.purchase_cost || asset.value.purchase_cost <= 0) {
      toast.error('Purchase Cost must be greater than 0 for an existing asset.');
      collapsed.purchase = false;
      return;
    }
  } else if (!asset.value.taxable_value || asset.value.taxable_value <= 0) {
    toast.error('Taxable Value must be greater than 0.');
    collapsed.purchase = false;
    return;
  }
  if (!asset.value.purchase_date) {
    toast.error('Purchase Date is required.');
    collapsed.purchase = false;
    return;
  }
  saving.value = true;
  try {
    const doc = { ...asset.value, doctype: 'Asset' };
    // _id is a client-only key for Vue's :key — strip before sending to the backend
    if (Array.isArray(doc.taxes)) doc.taxes = doc.taxes.map(({ _id, ...r }) => r);
    if (targetStatus === 'Submitted') {
      doc.status = 'Submitted';
    } else if (asset.value.docstatus !== 1) {
      // Still unsubmitted — safe to (re)label it Draft. If it's already
      // submitted (docstatus 1), a "Save Draft" click here is just a minor
      // field edit on an existing record — leave its real status alone
      // rather than relabeling a Submitted asset back to "Draft" text.
      doc.status = 'Draft';
    }
    if (isNew.value) delete doc.name;
    // Ensure the asset is scoped to the current company for tenancy isolation.
    if (!doc.company) doc.company = window.__booksCompany || '';
    const saved = await apiSave(doc);
    const savedName = saved?.name || doc.name;
    // Keep the in-memory doc in sync with what the server actually persisted
    // (name, modified, docstatus, etc.) -- router.push below doesn't remount
    // this component when it's already on the same route, so without this
    // asset.value would keep the pre-save `modified` and the next save would
    // be rejected as a false conflict.
    if (saved) asset.value = { ...asset.value, ...saved };

    if (targetStatus === 'Submitted' && saved?.docstatus !== 1) {
      try {
        const submitted = await apiSubmit('Asset', savedName);
        if (submitted) asset.value = { ...asset.value, ...submitted };
      } catch (subErr) {
        toast.error('Saved as draft — submit failed: ' + (subErr.message || subErr));
        initialSnapshot = JSON.stringify(asset.value);
        router.push({ name: 'asset-details', params: { id: savedName } });
        return;
      }
    }

    toast.success(isNew.value ? 'Asset created' : 'Asset updated');
    initialSnapshot = JSON.stringify(asset.value);
    router.push({ name: 'asset-details', params: { id: savedName } });
  } catch (e) {
    toast.error('Failed to save asset: ' + e.message);
  } finally {
    saving.value = false;
  }
}

function cancel() {
  router.push({ name: 'assets-assets' });
}

async function cancelGuarded() {
  if (isDirty.value) {
    const ok = await confirm({
      title: 'Discard unsaved changes?',
      body: 'You have unsaved changes. Closing now will discard them.',
      okLabel: 'Discard',
      okStyle: 'danger',
    });
    if (!ok) return;
  }
  cancel();
}

onMounted(() => {
  fetchCompanies();
  fetchSuppliers();
  fetchTaxAccounts();
  loadAsset();
});
</script>

<style scoped>
.add-toggle-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  cursor: default;
}
.ad-switch {
  position: relative;
  display: inline-block;
  width: 42px;
  height: 24px;
  flex-shrink: 0;
}
.ad-switch input { opacity: 0; width: 0; height: 0; }
.ad-switch-track {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background: #d1d5db;
  border-radius: 24px;
  transition: .2s;
}
.ad-switch-track:before {
  content: "";
  position: absolute;
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background: #fff;
  border-radius: 50%;
  transition: .2s;
}
.ad-switch input:checked + .ad-switch-track { background: #2563eb; }
.ad-switch input:checked + .ad-switch-track:before { transform: translateX(18px); }
.asset-fg4 { grid-template-columns: 1fr 1fr 1fr 1fr; }
@media (max-width: 700px) {
  .asset-fg4 { grid-template-columns: 1fr; }
}
.asset-locked-hint {
  margin-top: 12px; font-size: 12px; color: #92400e; background: #fffbeb;
  border: 1px solid #fde68a; border-radius: 6px; padding: 8px 12px;
}
.asset-tax-block { margin-top: 14px; padding-top: 14px; border-top: 1px dashed #e2e8f0; }
.asset-tax-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.asset-tax-add {
  display: flex; align-items: center; gap: 4px;
  font-size: 12px; font-weight: 600; color: #2563eb;
  background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px;
  padding: 5px 10px; cursor: pointer;
}
.asset-tax-add:hover { background: #dbeafe; }
.asset-tax-table { display: flex; flex-direction: column; gap: 6px; margin-bottom: 10px; }
.asset-tax-row {
  display: grid;
  grid-template-columns: 1.1fr 0.8fr 0.9fr 1.4fr 0.9fr 28px;
  gap: 8px;
  align-items: center;
}
.asset-tax-row-head {
  font-size: 10px; font-weight: 700; letter-spacing: .03em; text-transform: uppercase;
  color: #94a3b8; padding: 0 2px;
}
.asset-tax-remove {
  display: flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; border-radius: 6px;
  background: #fef2f2; border: 1px solid #fecaca; color: #dc2626; cursor: pointer;
}
.asset-tax-remove:hover { background: #fee2e2; }
.asset-tax-empty { font-size: 12px; color: #94a3b8; padding: 10px 0; }
.asset-tax-totals {
  display: flex; flex-direction: column; gap: 4px;
  border-top: 1px solid #e2e8f0; padding-top: 10px; font-size: 12.5px; color: #475569;
}
.asset-tax-totals > div { display: flex; justify-content: space-between; }
.asset-tax-totals .fw-700 { font-weight: 700; color: #1e293b; font-size: 13.5px; }
@media (max-width: 700px) {
  .asset-tax-row { grid-template-columns: 1fr 1fr; grid-auto-rows: auto; }
  .asset-tax-row-head { display: none; }
}
</style>