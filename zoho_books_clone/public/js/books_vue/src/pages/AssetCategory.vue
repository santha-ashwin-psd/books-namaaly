<template>
  <div class="ac-page">

    <!-- TOOLBAR -->
    <div class="ac-toolbar">
      <div class="ac-toolbar-left">
        <div class="ac-search-wrap">
          <span v-html="icon('search')" class="ac-search-icon"></span>
          <input v-model="search" class="ac-search-input" placeholder="Search categories…" />
          <button v-if="search" class="ac-search-clear" @click="search = ''">
            <span v-html="icon('x', 12)"></span>
          </button>
        </div>
      </div>
      <button class="ac-new-btn" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''" @click="newCategory">
        <span v-html="icon('plus', 13)"></span>
        <span class="ac-btn-label">New Category</span>
      </button>
    </div>

    <!-- BODY -->
    <div class="ac-body">

      <!-- Sidebar list -->
      <aside class="ac-sidebar" :class="{ 'ac-mob-hidden': isMobile && panelMode !== 'none' }">
        <div class="ac-sidebar-header">
          <div class="ac-sidebar-title">
            Asset Categories
            <span class="ac-sidebar-count">{{ categories.length }}</span>
          </div>
          <div class="ac-sidebar-stats">
            {{ activeCount }} active &middot; {{ assetCount }} assets
          </div>
        </div>

        <div v-if="loading" class="ac-shimmer-wrap">
          <div v-for="i in 6" :key="i" class="ac-shimmer-row">
            <div class="b-shimmer" :style="{ width: (70 + i * 5) + '%', height: '14px', borderRadius: '4px' }"></div>
          </div>
        </div>

        <div v-else-if="!filteredList.length" class="ac-tree-empty">
          <div style="font-size:28px;margin-bottom:8px">🔍</div>
          <div style="font-size:13px;color:#94a3b8">No categories found</div>
        </div>

        <div v-else class="ac-tree-scroll">
          <div
            v-for="cat in filteredList" :key="cat.name"
            class="ac-tree-node"
            :class="{
              'ac-tree-node--active': selected === cat.name,
              'ac-tree-node--active-cat': selected === cat.name && cat.is_active,
              'ac-tree-node--inactive-cat': selected === cat.name && !cat.is_active,
            }"
            @click="selectCategory(cat)"
          >
            <span class="ac-node-icon">{{ cat.is_active ? '📂' : '📁' }}</span>
             <span class="ac-node-label">{{ cat.category_name || cat.name }}</span>
            <span v-if="assetCountFor(cat.name) > 0" class="ac-node-item-count">
              {{ assetCountFor(cat.name) }}
            </span>
            <span class="ac-node-status-pill" :class="cat.is_active ? 'ac-pill-active' : 'ac-pill-inactive'">
              {{ cat.is_active ? 'Active' : 'Inactive' }}
            </span>
          </div>
        </div>
      </aside>

      <!-- Detail panel -->
      <main class="ac-detail" :class="{ 'ac-mob-hidden': isMobile && panelMode === 'none' }">

        <!-- Mobile back nav -->
        <div v-if="isMobile && panelMode !== 'none'" class="ac-mob-back-bar">
          <button class="ac-mob-back-btn" @click="panelMode = 'none'">
            <span v-html="icon('chevL', 15)"></span> Categories
          </button>
          <div class="ac-mob-back-title">
             {{ panelMode === 'new' ? 'New Category' : (selectedCategory?.category_name || selectedCategory?.name || '') }}
          </div>
        </div>

        <!-- EMPTY STATE -->
        <div v-if="panelMode === 'none'" class="ac-empty-state">
          <div class="ac-empty-icon">📁</div>
          <div class="ac-empty-title">Select a category to view</div>
          <div class="ac-empty-sub">Click any asset category from the list to see its details</div>
          <button class="ac-action-btn ac-action-btn--primary" style="margin-top:18px"
            @click="newCategory">
            <span v-html="icon('plus', 13)"></span> New Category
          </button>
        </div>

        <!-- VIEW MODE -->
        <div v-else-if="panelMode === 'view'" class="ac-form-wrap">

          <!-- Header -->
          <div class="ac-view-header">
            <div class="ac-form-icon-wrap" :class="selectedCategory?.is_active ? 'ac-form-icon--active' : 'ac-form-icon--inactive'">
              <span style="font-size:26px">{{ selectedCategory?.is_active ? '📂' : '📁' }}</span>
            </div>
            <div class="ac-form-header-info">
               <div class="ac-form-header-title">{{ selectedCategory?.category_name || selectedCategory?.name }}</div>
              <div class="ac-form-header-sub">
                <span class="ac-view-badge" :class="selectedCategory?.is_active ? 'ac-badge-active' : 'ac-badge-inactive'">
                  {{ selectedCategory?.is_active ? 'Active' : 'Inactive' }}
                </span>
              </div>
            </div>
            <div class="ac-form-stats">
              <div class="ac-form-stat">
                <div class="ac-form-stat-val">{{ assetCountFor(selectedCategory?.name || '') }}</div>
                <div class="ac-form-stat-lbl">Assets</div>
              </div>
            </div>
          </div>

          <!-- Details card -->
          <div class="ac-view-card">
            <div class="ac-form-section">Details</div>
            <div class="ac-view-rows">
              <div class="ac-view-row">
                <div class="ac-view-lbl">Category Name</div>
                 <div class="ac-view-val">{{ selectedCategory?.category_name || selectedCategory?.name }}</div>
              </div>
              <div v-if="selectedCategory?.description" class="ac-view-row">
                <div class="ac-view-lbl">Description</div>
                <div class="ac-view-val">{{ selectedCategory.description }}</div>
              </div>
              <div class="ac-view-row">
                <div class="ac-view-lbl">Status</div>
                <div class="ac-view-val">
                  <span class="ac-type-pill" :class="selectedCategory?.is_active ? 'ac-type-pill--active' : 'ac-type-pill--inactive'">
                    {{ selectedCategory?.is_active ? 'Active' : 'Inactive' }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- View actions -->
          <div class="ac-form-actions">
            <button class="ac-action-btn ac-action-btn--primary" :disabled="!$canEdit('inventory')" :title="!$canEdit('inventory') ? 'Read-only access' : ''" @click="enterEditMode">
              <span v-html="icon('edit', 13)"></span> Edit Category
            </button>
            <button class="ac-action-btn ac-action-btn--danger" :disabled="!$canDelete('inventory')" :title="!$canDelete('inventory') ? 'Not permitted' : ''" @click="deleteCategory">
              <span v-html="icon('trash', 13)"></span> Delete
            </button>
          </div>

          <!-- Assets in category -->
          <div class="ac-items-section">
            <div class="ac-items-hdr">
              <div class="ac-form-section" style="margin-bottom:0">Assets in this Category</div>
              <span v-if="!assetsLoading" class="ac-items-count-pill">{{ categoryAssets.length }}</span>
            </div>

            <div v-if="assetsLoading" class="ac-items-shimmer-wrap">
              <div v-for="i in 3" :key="i" class="b-shimmer" style="height:76px;border-radius:10px"></div>
            </div>

            <div v-else-if="!categoryAssets.length" class="ac-items-empty">
              <div style="font-size:30px;margin-bottom:8px">📭</div>
              <div class="ac-items-empty-title">No assets in <strong>{{ selectedCategory?.name }}</strong></div>
              <div class="ac-items-empty-sub">
                Go to <strong>Assets</strong> and create an asset with this category
              </div>
            </div>

            <div v-else class="ac-items-grid">
              <div v-for="asset in categoryAssets" :key="asset.name"
                class="ac-item-card"
                :class="{ 'ac-item-card--disabled': !asset.is_active }">
                <div class="ac-item-card-top">
                  <span class="ac-item-card-icon">🏢</span>
                  <div class="ac-item-card-badges">
                    <span class="ac-asset-status-badge" :class="'ac-status--' + (asset.status || 'Draft').toLowerCase().replace(/\s+/g, '')">
                      {{ asset.status || 'Draft' }}
                    </span>
                  </div>
                </div>
                <div class="ac-item-card-name">{{ asset.asset_name }}</div>
                <div class="ac-item-card-code">{{ asset.asset_code || asset.name }}</div>
                <div class="ac-item-card-footer">
                  <span class="ac-item-card-dept">{{ asset.department || '—' }}</span>
                  <span class="ac-item-card-cost">OMR {{ flt(asset.purchase_cost, 2) }}</span>
                </div>
              </div>
            </div>
          </div>

        </div>

        <!-- EDIT / NEW MODE -->
        <div v-else class="ac-form-wrap">

          <!-- Header -->
          <div class="ac-form-header">
            <div class="ac-form-icon-wrap" :class="form.is_active ? 'ac-form-icon--active' : 'ac-form-icon--inactive'">
              <span style="font-size:26px">{{ form.is_active ? '📂' : '📁' }}</span>
            </div>
            <div class="ac-form-header-info">
              <div class="ac-form-header-title">
                 {{ panelMode === 'edit' ? (form.category_name || form.name) : 'New Asset Category' }}
              </div>
              <div class="ac-form-header-sub">
                <span class="ac-form-mode-badge" :class="panelMode === 'new' ? 'ac-form-mode-badge--new' : 'ac-form-mode-badge--edit'">
                  {{ panelMode === 'new' ? 'New' : 'Editing' }}
                </span>
              </div>
            </div>
            <div class="ac-form-stats">
              <div class="ac-form-stat">
                <div class="ac-form-stat-val">{{ assetCountFor(form.name) }}</div>
                <div class="ac-form-stat-lbl">Assets</div>
              </div>
            </div>
          </div>

          <!-- Form fields -->
          <div class="ac-form-card">
            <div class="ac-form-section">Category Details</div>
            <div class="ac-form-grid">
              <div class="ac-field">
                <label class="ac-label">Category Name <span style="color:#dc2626">*</span></label>
                 <input class="ac-input" v-model="form.category_name"
                   placeholder="e.g. Electronics"/>
              </div>
            </div>

            <div class="ac-field" style="margin-top:14px">
              <label class="ac-label">Description</label>
              <textarea class="ac-input" v-model="form.description" rows="3"
                placeholder="Brief description of this category…" style="resize:vertical"></textarea>
            </div>

            <div class="ac-is-active-row">
              <label class="ac-is-active-label">
                <div class="ac-toggle-wrap">
                  <input type="checkbox" class="ac-toggle-input"
                    :checked="!!form.is_active"
                    @change="form.is_active = $event.target.checked ? 1 : 0"/>
                  <span class="ac-toggle-track">
                    <span class="ac-toggle-thumb"></span>
                  </span>
                </div>
                <div class="ac-is-active-text">
                  <div class="ac-is-active-title">Active</div>
                  <div class="ac-is-active-sub">Inactive categories are hidden from asset entry forms</div>
                </div>
              </label>
            </div>
          </div>

          <!-- Accounting (per Company) card -->
          <div class="ac-form-card">
            <div class="ac-acct-hdr">
              <div>
                <div class="ac-form-section" style="margin-bottom:2px">Accounting</div>
                <div class="ac-acct-hdr-sub">
                  Fixed Asset / Accumulated Depreciation / Depreciation Expense accounts to use for this
                  category. Required before any asset in this category can be submitted.
                </div>
              </div>
              <button class="ac-action-btn" @click="addAccountRow" :disabled="form.accounts.length >= 1 || !(panelMode === 'edit' ? $canEdit('inventory') : $canCreate('inventory'))"
                :title="form.accounts.length >= 1 ? 'Only one set of accounts is needed — this category belongs to a single company' : ''">
                <span v-html="icon('plus', 12)"></span> Add Accounts
              </button>
            </div>

            <div v-if="!form.accounts.length" class="ac-acct-empty">
              No company accounts configured yet. Add one so assets in this category can be capitalized and depreciated.
            </div>

            <div v-for="(row, idx) in form.accounts" :key="idx" class="ac-acct-row">
              <div class="ac-acct-row-top">
                <div class="ac-field" style="flex:1">
                  <label class="ac-label">Company <span style="color:#dc2626">*</span></label>
                  <SearchableSelect
                    v-model="row.company"
                    :options="companyOptions"
                    placeholder="Select company"
                    @search="fetchCompanyOptions"
                  />
                </div>
                <button class="ac-acct-remove-btn" title="Remove" :disabled="!(panelMode === 'edit' ? $canEdit('inventory') : $canCreate('inventory'))" @click="removeAccountRow(idx)">
                  <span v-html="icon('trash', 13)"></span>
                </button>
              </div>
              <div class="ac-acct-row-grid">
                <div class="ac-field">
                  <label class="ac-label">Fixed Asset Account <span style="color:#dc2626">*</span></label>
                  <SearchableSelect
                    v-model="row.fixed_asset_account"
                    :options="row._opts.fixed"
                    placeholder="Fixed Asset account"
                    @search="(q) => fetchRowAccounts(row, 'fixed', 'Fixed Asset', q)"
                  />
                </div>
                <div class="ac-field">
                  <label class="ac-label">Accumulated Depreciation Account <span style="color:#dc2626">*</span></label>
                  <SearchableSelect
                    v-model="row.accumulated_depreciation_account"
                    :options="row._opts.accdep"
                    placeholder="Accumulated Depreciation account"
                    @search="(q) => fetchRowAccounts(row, 'accdep', 'Accumulated Depreciation', q)"
                  />
                </div>
                <div class="ac-field">
                  <label class="ac-label">Depreciation Expense Account <span style="color:#dc2626">*</span></label>
                  <SearchableSelect
                    v-model="row.depreciation_expense_account"
                    :options="row._opts.depexp"
                    placeholder="Depreciation Expense account"
                    @search="(q) => fetchRowAccounts(row, 'depexp', 'Depreciation', q)"
                  />
                </div>
                <div class="ac-field">
                  <label class="ac-label">CWIP Account <span style="color:#94a3b8;font-weight:500">(optional)</span></label>
                  <SearchableSelect
                    v-model="row.cwip_account"
                    :options="row._opts.cwip"
                    placeholder="Capital work in progress account"
                    @search="(q) => fetchRowAccounts(row, 'cwip', null, q)"
                  />
                </div>
                <div class="ac-field">
                  <label class="ac-label">GST Input Account <span style="color:#94a3b8;font-weight:500">(optional)</span></label>
                  <SearchableSelect
                    v-model="row.gst_input_account"
                    :options="row._opts.gst"
                    placeholder="Required only if assets in this category carry ITC-eligible tax"
                    @search="(q) => fetchRowAccounts(row, 'gst', 'Tax', q)"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- Form actions -->
          <div class="ac-form-actions">
            <button class="ac-action-btn ac-action-btn--primary" :disabled="saving || !(panelMode === 'edit' ? $canEdit('inventory') : $canCreate('inventory'))" @click="saveCategory">
              <span v-html="icon('check', 14)"></span>
              {{ saving ? 'Saving…' : (panelMode === 'edit' ? 'Update Category' : 'Create Category') }}
            </button>
            <button class="ac-action-btn" @click="cancelForm">
              Cancel
            </button>
          </div>

        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from "vue";
import { apiGet, apiList, apiSave, apiDelete, apiPOST, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { useConfirm } from "../composables/useConfirm.js";
import { icon } from "../utils/icons.js";
import { flt } from "../utils/format.js";
import SearchableSelect from "../components/SearchableSelect.vue";

const { toast }   = useToast();
const { confirm } = useConfirm();

const panelMode    = ref("none");
const originalName = ref("");
const categories   = ref([]);
const loading      = ref(true);
const saving       = ref(false);
const selected     = ref(null);
const selectedCategory = ref(null);
const search       = ref("");
const isMobile     = ref(window.innerWidth <= 480);
const allAssets    = ref([]);
const assetsLoading = ref(false);

const form = reactive({ name: "", category_name: "", description: "", is_active: 1, accounts: [] });
const companyOptions = ref([]);
// The category is now scoped to a single owning Books Company (books_company).
// The per-row "Company" picker in the Accounting section must never offer any
// other company — otherwise a category from Company A could be configured
// with GL accounts belonging to Company B, defeating the isolation above.
const myCompany = ref("");

function onResize() { isMobile.value = window.innerWidth <= 480; }

function blankAccountRow() {
  return {
    company: "",
    fixed_asset_account: "",
    accumulated_depreciation_account: "",
    depreciation_expense_account: "",
    cwip_account: "",
    gst_input_account: "",
    // UI-only, per-row dropdown option caches — stripped before save.
    _opts: { fixed: [], accdep: [], depexp: [], cwip: [], gst: [] },
  };
}

function addAccountRow() {
  form.accounts.push({ ...blankAccountRow(), company: myCompany.value || "" });
}

function removeAccountRow(idx) {
  form.accounts.splice(idx, 1);
}

async function fetchCompanyOptions(q = "") {
  // Restricted to the category's own company — the accounts sub-table must
  // never let this category be wired to another tenant's GL accounts.
  if (!myCompany.value) { companyOptions.value = []; return; }
  try {
    const rows = await apiList("Books Company", {
      fields: ["name", "company_name"],
      filters: [["name", "=", myCompany.value]],
      limit: 1,
    });
    companyOptions.value = (rows || []).map((x) => ({ label: x.company_name || x.name, value: x.name }));
  } catch {
    companyOptions.value = [{ label: myCompany.value, value: myCompany.value }];
  }
}

async function fetchRowAccounts(row, key, accountType, q = "") {
  try {
    const filters = [["is_group", "=", 0]];
    if (accountType) filters.push(["account_type", "=", accountType]);
    if (row.company) filters.push(["company", "=", row.company]);
    if (q) filters.push(["name", "like", `%${q}%`]);
    const rows = await apiList("Account", { fields: ["name", "account_name"], filters, limit: 30, order: "name asc" });
    row._opts[key] = (rows || []).map((r) => ({ label: r.account_name || r.name, value: r.name }));
  } catch {
    row._opts[key] = [];
  }
}

const CATEGORY_DEFAULTS = [
  { name: "ACS-001", category_name: "Electronics",        description: "Electronic devices and components", is_active: 1 },
  { name: "ACS-002", category_name: "Furniture",          description: "Office and warehouse furniture", is_active: 1 },
  { name: "ACS-003", category_name: "Vehicles",           description: "Company vehicles and transport", is_active: 1 },
  { name: "ACS-004", category_name: "Computer Equipment", description: "Laptops, desktops, servers", is_active: 1 },
  { name: "ACS-005", category_name: "Office Equipment",   description: "Printers, scanners, projectors", is_active: 1 },
];

async function load() {
  loading.value = true;
  try {
    const rows = await apiList("Asset Category", {
      fields: ["name", "category_name", "description", "is_active"],
      order: "name asc", limit: 200,
    });
    categories.value = rows || [];
  } catch { categories.value = CATEGORY_DEFAULTS; }
  loading.value = false;
}

async function loadAssets() {
  assetsLoading.value = true;
  try {
    allAssets.value = await apiList("Asset", {
      fields: ["name", "asset_name", "asset_code", "asset_category", "status", "purchase_cost", "department", "is_active"],
      order: "asset_name asc", limit: 500,
    });
  } catch { allAssets.value = []; }
  assetsLoading.value = false;
}

const assetsByCategory = computed(() => {
  const map = {};
  allAssets.value.forEach((asset) => {
    const g = asset.asset_category || "";
    if (!map[g]) map[g] = [];
    map[g].push(asset);
  });
  return map;
});

const categoryAssets = computed(() =>
  selected.value ? (assetsByCategory.value[selected.value] || []) : []
);

const filteredList = computed(() => {
  const q = search.value.toLowerCase().trim();
  if (!q) return categories.value;
  return categories.value
    .filter((c) => (c.name || "").toLowerCase().includes(q) || (c.description || "").toLowerCase().includes(q))
    .sort((a, b) => a.name.localeCompare(b.name));
});

const assetCountFor = (name) => (assetsByCategory.value[name] || []).length;

const activeCount = computed(() => categories.value.filter(c => c.is_active).length);
const assetCount = computed(() => allAssets.value.length);

function selectCategory(cat) {
  selected.value = cat.name;
  selectedCategory.value = cat;
  panelMode.value = "view";
}

async function enterEditMode() {
  if (!selectedCategory.value) return;
  originalName.value = selectedCategory.value.name;
  Object.assign(form, {
    name: selectedCategory.value.name,
    category_name: selectedCategory.value.category_name || "",
    description: selectedCategory.value.description || "",
    is_active: selectedCategory.value.is_active ? 1 : 0,
    accounts: [],
  });
  panelMode.value = "edit";
  // The sidebar list only carries summary fields — fetch the full doc to get
  // the per-company accounts child table.
  try {
    const full = await apiGet("Asset Category", selectedCategory.value.name);
    myCompany.value = full?.books_company || (await resolveCompany()) || "";
    form.accounts = (full?.accounts || []).map((r) => ({
      company: r.company || "",
      fixed_asset_account: r.fixed_asset_account || "",
      accumulated_depreciation_account: r.accumulated_depreciation_account || "",
      depreciation_expense_account: r.depreciation_expense_account || "",
      cwip_account: r.cwip_account || "",
      gst_input_account: r.gst_input_account || "",
      _opts: { fixed: [], accdep: [], depexp: [], cwip: [], gst: [] },
    }));
  } catch (e) {
    toast("Failed to load account setup: " + e.message, "error");
  }
}

async function newCategory() {
  selected.value = null;
  selectedCategory.value = null;
  Object.assign(form, { name: "", category_name: "", description: "", is_active: 1, accounts: [] });
  myCompany.value = (await resolveCompany()) || "";
  panelMode.value = "new";
}

function cancelForm() {
  if (panelMode.value === "edit") {
    panelMode.value = "view";
  } else {
    panelMode.value = selected.value ? "view" : "none";
  }
}

async function saveCategory() {
  if (!form.category_name.trim()) { toast("Category name is required", "error"); return; }

  for (const row of form.accounts) {
    if (!row.company || !row.fixed_asset_account || !row.accumulated_depreciation_account || !row.depreciation_expense_account) {
      toast("Each company row needs Company, Fixed Asset, Accumulated Depreciation and Depreciation Expense accounts", "error");
      return;
    }
  }
  const companiesSeen = new Set();
  for (const row of form.accounts) {
    if (companiesSeen.has(row.company)) {
      toast(`Company "${row.company}" is configured more than once`, "error");
      return;
    }
    companiesSeen.add(row.company);
  }

  saving.value = true;
  try {
    const catName = form.category_name.trim();
    const isEdit = panelMode.value === "edit";

    const payload = {
      doctype: "Asset Category",
      category_name: catName,
      description: form.description,
      is_active: form.is_active ? 1 : 0,
    };
    if (!isEdit) {
      const booksCompany = await resolveCompany();
      if (!booksCompany) { toast("No company configured.", "error"); saving.value = false; return; }
      payload.books_company = booksCompany;
    }
    Object.assign(payload, {
      accounts: form.accounts.map((r) => ({
        company: r.company,
        fixed_asset_account: r.fixed_asset_account,
        accumulated_depreciation_account: r.accumulated_depreciation_account,
        depreciation_expense_account: r.depreciation_expense_account,
        cwip_account: r.cwip_account || "",
        gst_input_account: r.gst_input_account || "",
      })),
    });
    if (isEdit) {
      payload.name = originalName.value;
    }

    await apiSave(payload);
    await load();

    if (isEdit) {
      const updated = categories.value.find((c) => c.name === originalName.value);
      if (updated) {
        selected.value = updated.name;
        selectedCategory.value = updated;
        originalName.value = updated.name;
      }
    } else {
      const created = categories.value.find((c) => c.category_name === catName);
      if (created) {
        selected.value = created.name;
        selectedCategory.value = created;
        originalName.value = created.name;
        Object.assign(form, { name: created.name, category_name: created.category_name || "" });
      }
    }
    toast(isEdit ? "Category updated" : "Category created");
    panelMode.value = isEdit ? "view" : "none";
  } catch (e) {
    console.error("saveCategory error:", e);
    const raw = e?.response || e?.data || e;
    const extra = raw && typeof raw === "object" ? ("\n" + JSON.stringify(raw, null, 2).slice(0, 400)) : "";
    const msg = typeof e?.message === "string" && e.message ? e.message
             : raw && typeof raw === "object" ? JSON.stringify(raw).slice(0, 200)
             : e?.message || String(e);
    toast("Save failed: " + msg + extra, "error");
  }
  finally { saving.value = false; }
}

async function deleteCategory() {
  if (!selectedCategory.value) return;
  const ok = await confirm({
    title: "Delete category?",
    body: `Delete "${selectedCategory.value.name}"? This cannot be undone.`,
    okLabel: "Delete",
  });
  if (!ok) return;
  try {
    await apiDelete("Asset Category", selectedCategory.value.name);
    await load();
    selected.value = null;
    selectedCategory.value = null;
    panelMode.value = "none";
    toast("Category deleted");
  } catch (e) { toast("Delete failed: " + e.message, "error"); }
}

onMounted(() => {
  load();
  loadAssets();
  fetchCompanyOptions();
  window.addEventListener("resize", onResize, { passive: true });
});
onUnmounted(() => window.removeEventListener("resize", onResize));
</script>

<style>
.ac-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px);
  background: #f1f4f8;
  overflow: hidden;
}

.ac-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 24px;
  background: #fff;
  border-bottom: 1px solid #e8edf5;
  flex-shrink: 0;
}
.ac-toolbar-left { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; }

.ac-search-wrap { position: relative; width: 260px; max-width: 100%; }
.ac-search-icon {
  position: absolute; left: 10px; top: 50%; transform: translateY(-50%);
  color: #94a3b8; pointer-events: none; width: 14px;
}
.ac-search-input {
  width: 100%; border: 1.5px solid #e2e8f0; border-radius: 9px;
  padding: 8px 32px 8px 32px; font-size: 13px; color: #1e293b;
  outline: none; background: #f8fafc; transition: border-color .15s, background .15s;
  box-sizing: border-box;
}
.ac-search-input:focus { border-color: #3b82f6; background: #fff; }
.ac-search-clear {
  position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
  background: #e2e8f0; border: none; border-radius: 50%; width: 18px; height: 18px;
  display: flex; align-items: center; justify-content: center; cursor: pointer; color: #64748b;
}

.ac-new-btn {
  display: inline-flex; align-items: center; gap: 7px; padding: 8px 18px;
  font-size: 13px; font-weight: 700;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: #fff; border: none; border-radius: 9px; cursor: pointer;
  box-shadow: 0 2px 8px rgba(37,99,235,.3);
  transition: opacity .15s, transform .1s; white-space: nowrap; flex-shrink: 0;
}
.ac-new-btn:hover { opacity: .9; transform: translateY(-1px); }
.ac-new-btn:active { transform: translateY(0); }

.ac-body { display: flex; flex: 1; overflow: hidden; }

.ac-sidebar {
  width: 300px; min-width: 300px; display: flex; flex-direction: column;
  background: #fff; border-right: 1px solid #e2e8f0;
  box-shadow: 2px 0 12px rgba(0,0,0,.04);
}
.ac-sidebar-header { padding: 16px 18px 12px; border-bottom: 1px solid #edf0f5; }
.ac-sidebar-title {
  font-size: 13.5px; font-weight: 800; color: #0f172a;
  display: flex; align-items: center; gap: 8px;
}
.ac-sidebar-count {
  font-size: 11px; font-weight: 700; background: #e2e8f0; color: #475569;
  padding: 2px 8px; border-radius: 20px;
}
.ac-sidebar-stats {
  font-size: 11.5px; color: #94a3b8; font-weight: 500; margin-top: 4px;
}
.ac-shimmer-wrap { padding: 14px 16px; display: flex; flex-direction: column; gap: 10px; }
.ac-shimmer-row  { display: flex; align-items: center; }
.ac-tree-empty   { padding: 40px 20px; text-align: center; }

.ac-tree-scroll { flex: 1; overflow-y: auto; padding: 6px 0; }

.ac-tree-node {
  display: flex; align-items: center; gap: 6px;
  padding-top: 7px; padding-bottom: 7px; padding-right: 10px;
  cursor: pointer; border-left: 3px solid transparent;
  transition: background .1s, border-color .1s; position: relative;
}
.ac-tree-node:hover { background: #f8fafc; }
.ac-tree-node--active { background: #eff6ff !important; border-left-color: #2563eb !important; }
.ac-tree-node--active-cat .ac-node-label { color: #2563eb; font-weight: 700; }
.ac-tree-node--inactive-cat .ac-node-label { color: #64748b; font-weight: 600; }

.ac-node-icon { font-size: 14px; flex-shrink: 0; }
.ac-node-label {
  flex: 1; min-width: 0; font-size: 13px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ac-node-item-count {
  font-size: 10px; font-weight: 700; background: #dcfce7; color: #15803d;
  padding: 1px 7px; border-radius: 10px; flex-shrink: 0;
}
.ac-node-status-pill {
  font-size: 10px; font-weight: 700; padding: 1px 7px; border-radius: 10px; flex-shrink: 0;
}
.ac-pill-active { background: #dcfce7; color: #15803d; }
.ac-pill-inactive { background: #f1f5f9; color: #64748b; }

.ac-detail {
  flex: 1; overflow-y: auto; background: #f1f4f8; display: flex; flex-direction: column;
}

.ac-empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  flex: 1; padding: 40px; text-align: center;
}
.ac-empty-icon  { font-size: 56px; margin-bottom: 14px; }
.ac-empty-title { font-size: 17px; font-weight: 700; color: #334155; margin-bottom: 6px; }
.ac-empty-sub   { font-size: 13.5px; color: #94a3b8; max-width: 260px; line-height: 1.5; }

.ac-form-wrap {
  padding: 24px 28px; display: flex; flex-direction: column;
  gap: 16px; max-width: 800px; width: 100%;
}

.ac-view-header {
  background: #fff; border-radius: 14px; padding: 20px 24px;
  display: flex; align-items: center; gap: 16px;
  border: 1px solid #e8edf5;
  box-shadow: 0 1px 4px rgba(0,0,0,.06), 0 4px 16px rgba(0,0,0,.04);
  flex-wrap: wrap;
}

.ac-form-header {
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  border-radius: 14px; padding: 20px 24px;
  display: flex; align-items: center; gap: 16px;
  box-shadow: 0 4px 16px rgba(0,0,0,.15);
  flex-wrap: wrap;
}
.ac-form-header .ac-form-header-title { color: #fff; }
.ac-form-header .ac-form-header-sub   { color: rgba(255,255,255,.7); }
.ac-form-header .ac-form-stat-val     { color: #93c5fd; }
.ac-form-header .ac-form-stat-lbl     { color: rgba(255,255,255,.5); }

.ac-form-icon-wrap {
  width: 56px; height: 56px; border-radius: 14px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.ac-form-icon--active { background: #eff6ff; }
.ac-form-icon--inactive { background: #fef3c7; }
.ac-form-header .ac-form-icon--active { background: rgba(219,234,254,.2); }
.ac-form-header .ac-form-icon--inactive { background: rgba(254,243,199,.2); }

.ac-form-header-info { flex: 1; min-width: 0; }
.ac-form-header-title {
  font-size: 20px; font-weight: 800; color: #0f172a;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-bottom: 5px;
}
.ac-form-header-sub { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

.ac-view-badge {
  font-size: 11px; font-weight: 700; padding: 2px 10px;
  border-radius: 20px;
}
.ac-badge-active { background: #dcfce7; color: #15803d; }
.ac-badge-inactive { background: #f1f5f9; color: #64748b; }

.ac-form-mode-badge {
  font-size: 11px; font-weight: 700; padding: 2px 10px; border-radius: 20px;
}
.ac-form-mode-badge--new  { background: #dcfce7; color: #15803d; }
.ac-form-mode-badge--edit { background: rgba(251,191,36,.25); color: #d97706; }

.ac-form-stats { display: flex; gap: 20px; flex-shrink: 0; }
.ac-form-stat  { text-align: center; }
.ac-form-stat-val {
  font-size: 22px; font-weight: 800; color: #2563eb; line-height: 1; margin-bottom: 3px;
}
.ac-form-stat-lbl {
  font-size: 10.5px; font-weight: 600; color: #94a3b8;
  text-transform: uppercase; letter-spacing: .04em;
}

.ac-view-card {
  background: #fff; border-radius: 14px; padding: 22px 24px;
  border: 1px solid #e8edf5; box-shadow: 0 1px 4px rgba(0,0,0,.05);
}
.ac-view-rows { display: flex; flex-direction: column; gap: 0; }
.ac-view-row {
  display: flex; align-items: flex-start; gap: 16px;
  padding: 12px 0; border-bottom: 1px solid #f1f5f9;
}
.ac-view-row:last-child { border-bottom: none; }
.ac-view-lbl {
  width: 130px; flex-shrink: 0; font-size: 12px; font-weight: 700;
  color: #94a3b8; text-transform: uppercase; letter-spacing: .04em; padding-top: 2px;
}
.ac-view-val { flex: 1; font-size: 13.5px; font-weight: 600; color: #1e293b; }

.ac-type-pill {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 12px; font-weight: 700; padding: 4px 12px; border-radius: 20px;
}
.ac-type-pill--active { background: #dcfce7; color: #15803d; }
.ac-type-pill--inactive { background: #fef3c7; color: #92400e; }

.ac-form-card {
  background: #fff; border-radius: 14px; padding: 22px 24px;
  border: 1px solid #e8edf5; box-shadow: 0 1px 4px rgba(0,0,0,.05);
}
.ac-form-section {
  font-size: 10.5px; font-weight: 800; color: #94a3b8;
  text-transform: uppercase; letter-spacing: .07em; margin-bottom: 16px;
}
.ac-form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.ac-field { display: flex; flex-direction: column; gap: 5px; }
.ac-label { font-size: 13px; font-weight: 600; color: #374151; }
.ac-input {
  width: 100%; border: 1.5px solid #e2e8f0; border-radius: 9px;
  padding: 9px 12px; font-size: 13px; color: #1e293b;
  outline: none; background: #f8fafc; transition: border-color .15s, background .15s;
  box-sizing: border-box;
}
.ac-input:focus { border-color: #3b82f6; background: #fff; }
.ac-input::placeholder { color: #94a3b8; }

.ac-is-active-row {
  margin-top: 18px; padding: 14px 16px; background: #f8fafc;
  border: 1px solid #e2e8f0; border-radius: 10px;
}
.ac-is-active-label { display: flex; align-items: center; gap: 14px; cursor: pointer; }
.ac-toggle-wrap { position: relative; flex-shrink: 0; }
.ac-toggle-input { position: absolute; opacity: 0; width: 0; height: 0; }
.ac-toggle-track {
  display: block; width: 40px; height: 22px; background: #e2e8f0;
  border-radius: 11px; position: relative; transition: background .2s;
}
.ac-toggle-input:checked + .ac-toggle-track { background: #2563eb; }
.ac-toggle-thumb {
  position: absolute; top: 3px; left: 3px; width: 16px; height: 16px;
  background: #fff; border-radius: 50%; box-shadow: 0 1px 4px rgba(0,0,0,.2);
  transition: transform .2s;
}
.ac-toggle-input:checked + .ac-toggle-track .ac-toggle-thumb { transform: translateX(18px); }
.ac-is-active-text { flex: 1; }
.ac-is-active-title { font-size: 13px; font-weight: 700; color: #374151; }
.ac-is-active-sub   { font-size: 11.5px; color: #94a3b8; margin-top: 2px; }

.ac-acct-hdr { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; margin-bottom: 16px; }
.ac-acct-hdr-sub { font-size: 11.5px; color: #94a3b8; line-height: 1.5; margin-top: 4px; max-width: 480px; }
.ac-acct-empty {
  padding: 18px 16px; text-align: center; font-size: 12.5px; color: #94a3b8;
  background: #f8fafc; border-radius: 10px; border: 1.5px dashed #e2e8f0;
}
.ac-acct-row {
  border: 1.5px solid #e8edf5; border-radius: 12px; padding: 14px 16px;
  margin-bottom: 12px; background: #fbfcfe;
}
.ac-acct-row:last-child { margin-bottom: 0; }
.ac-acct-row-top { display: flex; align-items: flex-end; gap: 10px; margin-bottom: 12px; }
.ac-acct-remove-btn {
  flex-shrink: 0; display: flex; align-items: center; justify-content: center;
  width: 34px; height: 34px; border-radius: 9px; border: 1.5px solid #fca5a5;
  background: #fff5f5; color: #dc2626; cursor: pointer; transition: background .12s;
}
.ac-acct-remove-btn:hover { background: #fee2e2; }
.ac-acct-row-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

@media (max-width: 640px) {
  .ac-acct-row-grid { grid-template-columns: 1fr; }
}

.ac-form-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.ac-action-btn {
  display: inline-flex; align-items: center; gap: 6px; padding: 9px 18px;
  font-size: 13px; font-weight: 600; border-radius: 9px; border: 1.5px solid #e2e8f0;
  background: #fff; color: #374151; cursor: pointer;
  transition: background .12s, box-shadow .12s, transform .1s; white-space: nowrap;
}
.ac-action-btn:hover { background: #f8fafc; box-shadow: 0 2px 6px rgba(0,0,0,.08); }
.ac-action-btn:active { transform: translateY(1px); }
.ac-action-btn:disabled { opacity: .55; cursor: not-allowed; }
.ac-action-btn--primary {
  background: linear-gradient(135deg, #3b82f6, #2563eb); color: #fff;
  border-color: transparent; box-shadow: 0 2px 8px rgba(37,99,235,.3);
}
.ac-action-btn--primary:hover { opacity: .9; background: linear-gradient(135deg, #3b82f6, #2563eb); }
.ac-action-btn--danger { color: #dc2626; border-color: #fca5a5; background: #fff5f5; }
.ac-action-btn--danger:hover { background: #fee2e2; }

.ac-mob-back-bar {
  display: flex; align-items: center; gap: 10px; padding: 10px 14px;
  background: #fff; border-bottom: 1px solid #e4e8f0;
  position: sticky; top: 0; z-index: 10; flex-shrink: 0;
}
.ac-mob-back-btn {
  display: flex; align-items: center; gap: 4px; font-size: 13px; font-weight: 600;
  color: #2563eb; background: none; border: none; cursor: pointer; padding: 4px 0; flex-shrink: 0;
}
.ac-mob-back-title {
  font-size: 13.5px; font-weight: 700; color: #1a1d23;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.ac-items-section {
  background: #fff; border-radius: 14px; padding: 22px 24px;
  border: 1px solid #e8edf5; box-shadow: 0 1px 4px rgba(0,0,0,.05);
  display: flex; flex-direction: column; gap: 14px;
}
.ac-items-hdr { display: flex; align-items: center; justify-content: space-between; }
.ac-items-count-pill {
  font-size: 11px; font-weight: 800; background: #dbeafe; color: #1d4ed8;
  padding: 3px 10px; border-radius: 20px;
}
.ac-items-shimmer-wrap { display: flex; flex-direction: column; gap: 10px; }

.ac-items-empty {
  padding: 24px 16px; text-align: center;
  background: #f8fafc; border-radius: 10px; border: 1.5px dashed #e2e8f0;
}
.ac-items-empty-title { font-size: 13.5px; font-weight: 600; color: #374151; margin-bottom: 6px; }
.ac-items-empty-sub   { font-size: 12px; color: #94a3b8; line-height: 1.5; }

.ac-items-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px;
}
.ac-item-card {
  background: #f8fafc; border: 1.5px solid #e8edf5; border-radius: 12px;
  padding: 14px; display: flex; flex-direction: column; gap: 6px;
  transition: box-shadow .15s, border-color .15s, transform .1s;
}
.ac-item-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.09); border-color: #c7d7f5; transform: translateY(-1px); }
.ac-item-card--disabled { opacity: .5; filter: grayscale(0.5); }

.ac-item-card-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.ac-item-card-icon { font-size: 20px; flex-shrink: 0; }
.ac-item-card-badges { display: flex; gap: 4px; align-items: center; flex-wrap: wrap; }
.ac-asset-status-badge {
  font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 8px; white-space: nowrap;
}
.ac-status--draft { background: #f1f5f9; color: #475569; }
.ac-status--submitted { background: #dcfce7; color: #15803d; }
.ac-status--partiallydepreciated { background: #fef3c7; color: #92400e; }
.ac-status--fullydepreciated { background: #f1f5f9; color: #475569; }
.ac-status--scrapped { background: #fee2e2; color: #b91c1c; }
.ac-status--sold { background: #dbeafe; color: #1d4ed8; }
.ac-status--inmaintenance { background: #fef9c3; color: #a16207; }
.ac-status--outoforder { background: #fecaca; color: #991b1b; }

.ac-item-card-name {
  font-size: 13px; font-weight: 700; color: #0f172a;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ac-item-card-code {
  font-size: 11px; color: #64748b;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ac-item-card-footer {
  display: flex; align-items: center; justify-content: space-between;
  margin-top: 4px; padding-top: 8px; border-top: 1px solid #e8edf5;
}
.ac-item-card-dept  { font-size: 11px; color: #94a3b8; font-weight: 600; }
.ac-item-card-cost { font-size: 13px; font-weight: 800; color: #2563eb; }

@media (max-width: 768px) {
  .ac-sidebar { width: 240px; min-width: 240px; }
  .ac-form-wrap { padding: 16px 18px; }
  .ac-view-header, .ac-form-header { padding: 16px 18px; }
  .ac-form-header-title { font-size: 17px; }
  .ac-form-icon-wrap { width: 46px; height: 46px; }
  .ac-view-card, .ac-form-card { padding: 16px 18px; }
  .ac-form-grid { grid-template-columns: 1fr; }
  .ac-search-wrap { width: 200px; }
  .ac-items-section { padding: 16px 18px; }
  .ac-items-grid { grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); }
}

@media (max-width: 480px) {
  .ac-toolbar { padding: 10px 14px; }
  .ac-search-wrap { width: 100%; flex: 1; }
  .ac-btn-label { display: none; }
  .ac-new-btn { padding: 8px 12px; }

  .ac-body { flex-direction: column; }

  .ac-sidebar {
    width: 100% !important; min-width: 0 !important;
    border-right: none !important; border-bottom: 1px solid #e2e8f0; flex: 1;
  }
  .ac-detail {
    position: absolute; inset: 0; top: 56px; z-index: 50; background: #f1f4f8;
  }
  .ac-mob-hidden { display: none !important; }

  .ac-form-wrap { padding: 14px 14px; }
  .ac-view-header, .ac-form-header { padding: 14px 16px; gap: 12px; }
  .ac-form-header-title { font-size: 15px; }
  .ac-form-icon-wrap { width: 42px; height: 42px; }
  .ac-form-stats { gap: 14px; }
  .ac-form-stat-val { font-size: 18px; }
  .ac-view-card, .ac-form-card { padding: 14px 16px; }
  .ac-view-lbl { width: 100px; }
  .ac-form-grid { grid-template-columns: 1fr; }
  .ac-form-actions { gap: 8px; }
  .ac-action-btn { padding: 8px 14px; font-size: 12.5px; }
  .ac-items-section { padding: 14px 16px; }
  .ac-items-grid { grid-template-columns: repeat(auto-fill, minmax(145px, 1fr)); }
}
</style>