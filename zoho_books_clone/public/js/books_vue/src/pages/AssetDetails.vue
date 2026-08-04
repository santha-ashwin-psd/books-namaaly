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
                  <select v-model="asset.asset_category" class="inv-fi" required>
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
                    @search="fetchCompanies"
                  />
                </div>
              </div>
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
              <div class="inv-fg inv-fg3">
                <div>
                  <label class="inv-lbl">Purchase Date</label>
                  <input v-model="asset.purchase_date" type="date" class="inv-fi"/>
                </div>
                <div>
                  <label class="inv-lbl">Purchase Cost</label>
                  <input v-model.number="asset.purchase_cost" type="number" step="0.01" class="inv-fi" placeholder="0.00"/>
                </div>
                <div>
                  <label class="inv-lbl">Supplier</label>
                  <SearchableSelect
                    v-model="asset.supplier"
                    :options="suppliers"
                    placeholder="Vendor / supplier"
                    createable
                    create-doctype="Supplier"
                    @search="fetchSuppliers"
                  />
                </div>
              </div>
              <label class="add-toggle-row" style="margin-top:14px">
                <span>Existing Asset (already on the books)</span>
                <span class="ad-switch">
                  <input type="checkbox" :checked="!!asset.is_existing_asset" @change="asset.is_existing_asset=$event.target.checked?1:0"/>
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
                    @search="fetchCreditAccounts"
                  />
                  <div style="font-size:11px;color:#94a3b8;margin-top:4px">
                    Posted on submit: Dr Fixed Asset (from category) / Cr this account, for the Purchase Cost above.
                  </div>
                </div>
              </div>
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
                  <select v-model="asset.depreciation_method" class="inv-fi">
                    <option value="">Select method</option>
                    <option>Straight Line</option>
                    <option>Written Down Value</option>
                  </select>
                </div>
                <div>
                  <label class="inv-lbl">Useful Life (Years)</label>
                  <input v-model.number="asset.useful_life" type="number" class="inv-fi" placeholder="e.g. 5"/>
                </div>
                <div>
                  <label class="inv-lbl">Salvage Value</label>
                  <input v-model.number="asset.salvage_value" type="number" step="0.01" class="inv-fi" placeholder="0.00"/>
                </div>
                <div>
                  <label class="inv-lbl">Current Value</label>
                  <input v-model.number="asset.current_value" type="number" step="0.01" class="inv-fi" placeholder="0.00"/>
                </div>
              </div>
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

const blankAsset = () => ({
  doctype: 'Asset',
  asset_name: '',
  asset_category: '',
  status: 'Draft',
  company: window.__booksCompany || '',
  purchase_date: '',
  purchase_cost: 0,
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
  if (targetStatus === 'Submitted' && !asset.value.is_existing_asset && !asset.value.credit_account) {
    toast.error('Credit Account is required to submit a non-existing asset (used for the capitalization entry).');
    return;
  }
  saving.value = true;
  try {
    const doc = { ...asset.value, doctype: 'Asset' };
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
</style>