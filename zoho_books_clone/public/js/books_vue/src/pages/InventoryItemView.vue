<template>
  <div class="iv-page">

    <!-- ── Top bar ─────────────────────────────────────────────────── -->
    <div class="iv-topbar">
      <button class="iv-back" @click="$router.push('/inventory/items')">
        <span v-html="icon('arrow-left', 14)"></span> Items
      </button>
      <div class="iv-topbar-actions">
        <button class="iv-btn-ghost" @click="load"><span v-html="icon('refresh', 13)"></span></button>
        <button class="iv-btn-primary" @click="openEdit">
          <span v-html="icon('edit', 13)"></span> Edit Item
        </button>
      </div>
    </div>

    <!-- skeleton -->
    <template v-if="loading">
      <div class="iv-sk-header"></div>
      <div class="iv-stats-row">
        <div v-for="n in 4" :key="n" class="iv-stat-card iv-sk-card"></div>
      </div>
      <div class="iv-two-col">
        <div class="iv-card iv-sk-card" style="height:240px"></div>
        <div class="iv-card iv-sk-card" style="height:240px"></div>
      </div>
    </template>

    <template v-else-if="!item">
      <div class="iv-not-found">
        <div style="font-size:36px;margin-bottom:12px">📦</div>
        <div style="font-size:16px;font-weight:700;color:#1a1d23;margin-bottom:6px">Item not found</div>
        <div style="color:#6b7280;font-size:13px">{{ itemCode }}</div>
        <button class="iv-btn-primary" style="margin-top:16px" @click="$router.push('/inventory/items')">Back to Items</button>
      </div>
    </template>

    <template v-else>

      <!-- ── Item header ─────────────────────────────────────────── -->
      <div class="iv-header">
        <div class="iv-header-left">
          <div class="iv-item-name">{{ item.item_name }}</div>
          <div class="iv-item-meta">
            <span class="iv-mono">{{ item.item_code }}</span>
            <span class="iv-sep">·</span>
            <span v-if="item.item_group" class="iv-group-badge">{{ item.item_group }}</span>
            <span class="iv-sep">·</span>
            <span class="iv-type-badge">{{ item.item_type || 'Product' }}</span>
            <span class="iv-sep">·</span>
            <span class="iv-uom">{{ item.stock_uom || 'Nos' }}</span>
          </div>
        </div>
        <span class="iv-status-badge" :class="item.disabled ? 'iv-status-inactive' : 'iv-status-active'">
          {{ item.disabled ? 'Inactive' : 'Active' }}
        </span>
      </div>

      <!-- ── Stats row ───────────────────────────────────────────── -->
      <div class="iv-stats-row">
        <div class="iv-stat-card">
          <div class="iv-stat-label">Selling Rate</div>
          <div class="iv-stat-val iv-stat-green">{{ fmt(item.standard_rate) }}</div>
        </div>
        <div class="iv-stat-card">
          <div class="iv-stat-label">Buying Rate</div>
          <div class="iv-stat-val">{{ fmt(item.standard_buying_rate) }}</div>
        </div>
        <div class="iv-stat-card">
          <div class="iv-stat-label">Total Stock</div>
          <div class="iv-stat-val iv-stat-blue">
            {{ fmtQty(stockDetail.total_qty) }}
            <span style="font-size:12px;font-weight:500;color:#6b7280">{{ item.stock_uom }}</span>
          </div>
        </div>
        <div class="iv-stat-card">
          <div class="iv-stat-label">Stock Value</div>
          <div class="iv-stat-val">{{ fmt(stockDetail.total_value) }}</div>
        </div>
      </div>

      <!-- ── Two-column section ──────────────────────────────────── -->
      <div class="iv-two-col">

        <!-- Details card -->
        <div class="iv-card">
          <div class="iv-card-title">Item Details</div>
          <div class="iv-kv-list">
            <div class="iv-kv"><span class="iv-k">Item Code</span><span class="iv-v iv-mono">{{ item.item_code }}</span></div>
            <div class="iv-kv"><span class="iv-k">Item Name</span><span class="iv-v">{{ item.item_name }}</span></div>
            <div class="iv-kv"><span class="iv-k">Group</span><span class="iv-v">{{ item.item_group || '—' }}</span></div>
            <div class="iv-kv"><span class="iv-k">Type</span><span class="iv-v">{{ item.item_type || 'Product' }}</span></div>
            <div class="iv-kv"><span class="iv-k">Unit of Measure</span><span class="iv-v">{{ item.stock_uom || 'Nos' }}</span></div>
            <div class="iv-kv"><span class="iv-k">HSN / SAC Code</span><span class="iv-v iv-mono">{{ item.hsn_code || '—' }}</span></div>
            <div class="iv-kv"><span class="iv-k">Tax Template</span><span class="iv-v">{{ item.tax_code || '—' }}</span></div>
            <div class="iv-kv"><span class="iv-k">Income Account</span><span class="iv-v">{{ item.income_account || '—' }}</span></div>
            <div class="iv-kv"><span class="iv-k">Expense Account</span><span class="iv-v">{{ item.expense_account || '—' }}</span></div>
            <div class="iv-kv"><span class="iv-k">Valuation Method</span><span class="iv-v">{{ item.valuation_method || 'FIFO' }}</span></div>
            <div class="iv-kv"><span class="iv-k">Track Stock</span><span class="iv-v">{{ item.is_stock_item ? 'Yes' : 'No' }}</span></div>
          </div>
          <div v-if="item.description" class="iv-description">
            <div class="iv-k" style="margin-bottom:6px">Description</div>
            <div class="iv-desc-body" v-html="item.description"></div>
          </div>
        </div>

        <!-- Stock by warehouse card -->
        <div class="iv-card">
          <div class="iv-card-title">
            Stock by Warehouse
            <span class="iv-total-chip">Total: {{ fmtQty(stockDetail.total_qty) }} {{ item.stock_uom }}</span>
          </div>
          <div v-if="!item.is_stock_item" class="iv-no-stock">
            <span v-html="icon('info', 14)" style="color:#6b7280"></span>
            Service item — no stock tracked
          </div>
          <div v-else-if="!stockDetail.warehouses?.length" class="iv-no-stock">
            No warehouse records yet. Add stock via Inventory → Warehouses → Adjust.
          </div>
          <table v-else class="iv-wh-table">
            <thead>
              <tr>
                <th>Warehouse</th>
                <th class="ta-r">On Hand</th>
                <th class="ta-r">Reserved</th>
                <th class="ta-r">Ordered</th>
                <th class="ta-r">Value</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="wh in stockDetail.warehouses" :key="wh.warehouse"
                :class="{ 'wh-row-zero': wh.actual_qty <= 0 }">
                <td class="iv-wh-name">{{ wh.warehouse }}</td>
                <td class="ta-r fw-600" :class="wh.actual_qty <= 0 ? 'clr-red' : 'clr-green'">
                  {{ fmtQty(wh.actual_qty) }}
                </td>
                <td class="ta-r clr-muted">{{ fmtQty(wh.reserved_qty) }}</td>
                <td class="ta-r" style="color:#7c3aed">{{ fmtQty(wh.ordered_qty) }}</td>
                <td class="ta-r">{{ fmt(wh.stock_value) }}</td>
              </tr>
            </tbody>
          </table>

          <!-- Reorder settings inside stock card -->
          <div v-if="item.is_stock_item" class="iv-reorder-strip">
            <div class="iv-reorder-row">
              <div class="iv-reorder-item">
                <span class="iv-k">Reorder Level</span>
                <span class="iv-reorder-val" :class="stockDetail.total_qty <= item.reorder_level ? 'clr-red' : ''">
                  {{ fmtQty(item.reorder_level) }} {{ item.stock_uom }}
                </span>
              </div>
              <div class="iv-reorder-item">
                <span class="iv-k">Order Qty</span>
                <span class="iv-reorder-val">{{ fmtQty(item.reorder_qty) }} {{ item.stock_uom }}</span>
              </div>
              <div class="iv-reorder-item">
                <span class="iv-k">Auto-PO</span>
                <span class="iv-auto-po-chip" :class="item.auto_po_enabled ? 'chip-on' : 'chip-off'">
                  {{ item.auto_po_enabled ? '⚡ ON' : 'OFF' }}
                </span>
              </div>
            </div>
            <div v-if="item.reorder_supplier" class="iv-reorder-row" style="margin-top:6px">
              <div class="iv-reorder-item">
                <span class="iv-k">Reorder Supplier</span>
                <span class="iv-reorder-val">{{ item.reorder_supplier }}</span>
              </div>
              <div class="iv-reorder-item" v-if="item.reorder_warehouse_override">
                <span class="iv-k">Reorder Warehouse</span>
                <span class="iv-reorder-val">{{ item.reorder_warehouse_override }}</span>
              </div>
            </div>
            <div v-if="stockDetail.total_qty <= item.reorder_level && item.reorder_level > 0" class="iv-reorder-alert">
              <span v-html="icon('alert-triangle', 12)"></span>
              Stock is at or below reorder level — restock needed
            </div>
          </div>
        </div>
      </div>

      <!-- ── Price Lists ────────────────────────────────────────── -->
      <div class="iv-card" v-if="priceLists.length">
        <div class="iv-card-title">Price Lists</div>
        <table class="iv-wh-table iv-pl-table">
          <thead>
            <tr>
              <th>Price List</th>
              <th class="ta-r">Rate (₹)</th>
              <th>UOM</th>
              <th>Valid From</th>
              <th>Valid To</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="pl in priceLists" :key="pl.name">
              <td class="fw-600">{{ pl.price_list }}</td>
              <td class="ta-r fw-600 clr-green">{{ fmt(pl.price_list_rate) }}</td>
              <td class="clr-muted">{{ pl.uom || item.stock_uom }}</td>
              <td class="clr-muted">{{ pl.valid_from || '—' }}</td>
              <td class="clr-muted">{{ pl.valid_upto || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- ── Stock Ledger ───────────────────────────────────────── -->
      <div class="iv-card">
        <div class="iv-card-title">
          Stock Ledger
          <span class="iv-total-chip" style="background:#f0fdf4;color:#16a34a">Last 30 entries</span>
        </div>
        <div v-if="!item.is_stock_item" class="iv-no-stock">Service item — no stock ledger</div>
        <div v-else-if="!ledger.length" class="iv-no-stock">No stock movements yet</div>
        <template v-else>
          <!-- Desktop/tablet: table -->
          <div class="iv-ledger-wrap iv-ledger-table-view">
            <table class="iv-wh-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Type</th>
                  <th>Voucher</th>
                  <th>Warehouse</th>
                  <th class="ta-r">Qty</th>
                  <th class="ta-r">Balance</th>
                  <th class="ta-r">Rate</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in ledger" :key="row.name">
                  <td class="clr-muted" style="white-space:nowrap">{{ row.posting_date }}</td>
                  <td>
                    <span class="iv-ledger-type-badge" :class="row.actual_qty > 0 ? 'badge-in' : 'badge-out'">
                      {{ row.voucher_type || '—' }}
                    </span>
                  </td>
                  <td class="iv-mono" style="font-size:11.5px;color:#2563eb">{{ row.voucher_no }}</td>
                  <td class="clr-muted" style="font-size:12px">{{ row.warehouse }}</td>
                  <td class="ta-r fw-600" :class="row.actual_qty > 0 ? 'clr-green' : 'clr-red'">
                    {{ row.actual_qty > 0 ? '+' : '' }}{{ fmtQty(row.actual_qty) }}
                  </td>
                  <td class="ta-r clr-muted">{{ fmtQty(row.qty_after_transaction) }}</td>
                  <td class="ta-r clr-muted">{{ fmt(row.incoming_rate || row.valuation_rate) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <!-- Mobile: cards -->
          <div class="iv-ledger-cards-view">
            <div v-for="row in ledger" :key="row.name" class="iv-ledger-card">
              <div class="iv-lc-top">
                <span class="iv-ledger-type-badge" :class="row.actual_qty > 0 ? 'badge-in' : 'badge-out'">
                  {{ row.voucher_type || '—' }}
                </span>
                <span class="iv-lc-qty" :class="row.actual_qty > 0 ? 'clr-green' : 'clr-red'">
                  {{ row.actual_qty > 0 ? '+' : '' }}{{ fmtQty(row.actual_qty) }}
                </span>
              </div>
              <div class="iv-lc-voucher iv-mono">{{ row.voucher_no }}</div>
              <div class="iv-lc-meta">
                <span>{{ row.posting_date }}</span>
                <span class="iv-sep">·</span>
                <span class="clr-muted">Balance: {{ fmtQty(row.qty_after_transaction) }}</span>
                <span class="iv-sep">·</span>
                <span class="clr-muted">{{ row.warehouse }}</span>
              </div>
            </div>
          </div>
        </template>
      </div>

    </template>

    <!-- ── Edit Drawer ────────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="showDrawer" class="iv-drawer-overlay" @click.self="showDrawer=false">
        <div class="iv-drawer">
          <div class="iv-drawer-header">
            <div>
              <div class="iv-drawer-title">Edit Item</div>
              <div class="iv-drawer-sub">{{ item?.item_code }}</div>
            </div>
            <button class="iv-drawer-close" @click="showDrawer=false" v-html="icon('x', 16)"></button>
          </div>

          <!-- Tabs -->
          <div class="iv-drawer-tabs">
            <button v-for="t in DRAWER_TABS" :key="t.k"
              class="iv-dtab" :class="{ 'iv-dtab--active': drawerTab === t.k }"
              @click="drawerTab = t.k">{{ t.l }}
            </button>
          </div>

          <!-- Form -->
          <div class="iv-drawer-body">
            <!-- Basic -->
            <template v-if="drawerTab === 'basic'">
              <div class="iv-fg2">
                <div class="iv-field"><label class="nim-label">Item Name <span class="req">*</span></label><input class="nim-input" v-model="form.item_name"/></div>
                <div class="iv-field"><label class="nim-label">Item Code <span class="req">*</span></label><input class="nim-input" v-model="form.item_code"/></div>
              </div>
              <div class="iv-field">
                <label class="nim-label">Item Group</label>
                <select class="nim-input" v-model="form.item_group">
                  <option value="">— Select Group —</option>
                  <option v-for="g in itemGroups" :key="g" :value="g">{{ g }}</option>
                </select>
              </div>
              <div class="iv-field">
                <label class="nim-label">Item Type</label>
                <div class="iv-type-row">
                  <button v-for="t in ITEM_TYPES" :key="t" type="button"
                    class="iv-type-btn" :class="{ 'iv-type-btn--on': form.item_type === t }"
                    @click="form.item_type = t">
                    {{ ITEM_TYPE_ICONS[t] }} {{ t }}
                  </button>
                </div>
              </div>
              <div class="iv-fg2">
                <div class="iv-field">
                  <label class="nim-label">UOM <span class="req">*</span></label>
                  <select class="nim-input" v-model="form.stock_uom">
                    <option v-for="u in UOM_LIST" :key="u" :value="u">{{ u }}</option>
                  </select>
                </div>
                <div class="iv-field"><label class="nim-label">HSN / SAC Code</label><input class="nim-input" v-model="form.hsn_code"/></div>
              </div>
              <div class="iv-field"><label class="nim-label">Description</label><textarea class="nim-input" v-model="form.description" rows="3" style="resize:vertical"></textarea></div>
              <label class="iv-check-row">
                <input type="checkbox" :checked="!!form.disabled" @change="form.disabled=$event.target.checked?1:0"/>
                <span>Mark as Inactive</span>
              </label>
            </template>

            <!-- Pricing -->
            <template v-else-if="drawerTab === 'pricing'">
              <div class="iv-fg2">
                <div class="iv-field"><label class="nim-label">Selling Rate (₹)</label><input type="number" class="nim-input" v-model.number="form.standard_rate" min="0"/></div>
                <div class="iv-field"><label class="nim-label">Buying Rate (₹)</label><input type="number" class="nim-input" v-model.number="form.standard_buying_rate" min="0"/></div>
              </div>
              <div class="iv-field"><label class="nim-label">MRP (₹)</label><input type="number" class="nim-input" v-model.number="form.mrp" min="0"/>
                <div class="text-muted" style="font-size:11.5px;margin-top:5px">If left blank, Selling Rate is used as the MRP on invoices.</div>
              </div>
              <div class="iv-field"><label class="nim-label">Tax Template <span style="color:#dc2626">*</span></label>
                <select class="nim-input" v-model="form.tax_code">
                  <option value="">— Select —</option>
                  <option v-for="t in taxTemplates" :key="t.name" :value="t.name">{{ t.label }}</option>
                </select>
                <div class="text-muted" style="font-size:11.5px;margin-top:5px">Tax on transactions is determined by the selected Tax Template.</div>
              </div>
              <div class="iv-field"><label class="nim-label">Income Account <span style="color:#dc2626">*</span></label>
                <select class="nim-input" v-model="form.income_account">
                  <option value="">— Select —</option>
                  <option v-for="a in incomeAccounts" :key="a" :value="a">{{ a }}</option>
                </select>
              </div>
              <div class="iv-field"><label class="nim-label">Expense Account <span style="color:#dc2626">*</span></label>
                <select class="nim-input" v-model="form.expense_account">
                  <option value="">— Select —</option>
                  <option v-for="a in expenseAccounts" :key="a" :value="a">{{ a }}</option>
                </select>
              </div>
            </template>

            <!-- Inventory -->
            <template v-else>
              <label class="iv-check-row" style="margin-bottom:14px">
                <input type="checkbox" :checked="!!form.is_stock_item" @change="form.is_stock_item=$event.target.checked?1:0"/>
                <span>Track Inventory (stock item)</span>
              </label>
              <div class="iv-fg2">
                <div class="iv-field">
                  <label class="nim-label">Valuation Method</label>
                  <select class="nim-input" v-model="form.valuation_method">
                    <option v-for="m in ['FIFO','Moving Average','LIFO']" :key="m" :value="m">{{ m }}</option>
                  </select>
                </div>
                <div class="iv-field">
                  <label class="nim-label">Default Warehouse <span v-if="form.is_stock_item" class="req">*</span></label>
                  <select class="nim-input" v-model="form.default_warehouse">
                    <option value="">— Select —</option>
                    <option v-for="w in warehouses" :key="w.name" :value="w.name">{{ w.label }}</option>
                  </select>
                </div>
              </div>
              <div class="iv-fg2">
                <div class="iv-field"><label class="nim-label">Reorder Level</label><input type="number" class="nim-input" v-model.number="form.reorder_level" min="0"/></div>
                <div class="iv-field"><label class="nim-label">Reorder Qty</label><input type="number" class="nim-input" v-model.number="form.reorder_qty" min="0"/></div>
              </div>
            </template>
          </div>

          <div class="iv-drawer-footer">
            <button class="iv-btn-ghost" @click="showDrawer=false">Cancel</button>
            <button class="iv-btn-primary" :disabled="saving" @click="saveItem">
              <span v-if="saving" class="iv-spinner"></span>
              {{ saving ? 'Saving…' : 'Update Item' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { apiGET, apiPOST, apiList, apiSave, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { fmt, flt } from "../utils/format.js";
import { icon } from "../utils/icons.js";

const { toast } = useToast();
const route     = useRoute();
const itemCode  = computed(() => route.params.itemCode);

// ── Data ───────────────────────────────────────────────────────────────────
const item        = ref(null);
const stockDetail = ref({ warehouses: [], total_qty: 0, total_value: 0 });
const ledger      = ref([]);
const priceLists  = ref([]);
const loading     = ref(true);

// Edit drawer
const showDrawer  = ref(false);
const drawerTab   = ref("basic");
const saving      = ref(false);
const itemGroups  = ref([]);
const warehouses  = ref([]);
const taxTemplates = ref([]);
const incomeAccounts  = ref([]);
const expenseAccounts = ref([]);

const form = reactive({
  name: "", item_code: "", item_name: "", item_group: "", item_type: "Product",
  stock_uom: "Nos", hsn_code: "", description: "", disabled: 0,
  standard_rate: 0, standard_buying_rate: 0, mrp: 0, tax_code: "",
  income_account: "", expense_account: "",
  is_stock_item: 1, valuation_method: "FIFO", default_warehouse: "",
  reorder_level: 0, reorder_qty: 0,
});

const DRAWER_TABS    = [{ k:"basic", l:"Basic Info" }, { k:"pricing", l:"Pricing & Tax" }, { k:"inventory", l:"Inventory" }];
const ITEM_TYPES     = ["Product", "Service", "Raw Material", "Finished Good"];
const ITEM_TYPE_ICONS = { Product:"📦", Service:"🛠️", "Raw Material":"⚙️", "Finished Good":"✅" };
const UOM_LIST       = ["Nos", "Kg", "Ltr", "Mtr", "Box", "Pcs", "Set", "Dozen", "Pair", "Roll"];

// ── Load ───────────────────────────────────────────────────────────────────
async function load() {
  loading.value = true;
  item.value    = null;
  try {
    const [full, stock, sled, pl] = await Promise.all([
      apiGET("zoho_books_clone.api.docs.get_doc", { doctype: "Item", name: itemCode.value }),
      apiGET("zoho_books_clone.api.inventory.get_item_stock_detail", { item_code: itemCode.value }),
      apiGET("zoho_books_clone.api.inventory.get_stock_ledger_entries", { item_code: itemCode.value, limit: 30 }),
      apiGET("zoho_books_clone.api.inventory.get_item_price_list", { item_code: itemCode.value }).catch(() => []),
    ]);
    item.value        = full;
    stockDetail.value = stock || { warehouses: [], total_qty: 0, total_value: 0 };
    ledger.value      = sled  || [];
    priceLists.value  = pl    || [];
  } catch (e) {
    toast(e.message || "Failed to load item", "error");
  } finally {
    loading.value = false;
  }
}

// ── Open edit ──────────────────────────────────────────────────────────────
async function openEdit() {
  if (!item.value) return;
  drawerTab.value = "basic";
  Object.assign(form, {
    name: item.value.name,
    item_code: item.value.item_code || "",
    item_name: item.value.item_name || "",
    item_group: item.value.item_group || "",
    item_type: item.value.item_type || "Product",
    stock_uom: item.value.stock_uom || "Nos",
    hsn_code: item.value.hsn_code || "",
    description: item.value.description || "",
    disabled: item.value.disabled ? 1 : 0,
    standard_rate: flt(item.value.standard_rate),
    standard_buying_rate: flt(item.value.standard_buying_rate),
    mrp: flt(item.value.mrp),
    tax_code: item.value.tax_code || "",
    income_account: item.value.income_account || "",
    expense_account: item.value.expense_account || "",
    is_stock_item: item.value.is_stock_item ? 1 : 0,
    valuation_method: item.value.valuation_method || "FIFO",
    default_warehouse: item.value.default_warehouse || "",
    reorder_level: flt(item.value.reorder_level),
    reorder_qty: flt(item.value.reorder_qty),
  });

  // Load dropdowns in background
  loadDrawerOptions();
  showDrawer.value = true;
}

async function loadDrawerOptions() {
  try {
    const [grps, whs, tt, company] = await Promise.all([
      apiList("Item Group", { fields: ["name", "is_group"], limit: 200 }),
      apiList("Warehouse", { fields: ["name","warehouse_name"], filters:[["disabled","=",0]], limit: 200 }),
      apiList("Tax Template", { fields: ["name","template_name"], filters:[["disabled","=",0]], limit: 100 }),
      resolveCompany(),
    ]);
    itemGroups.value = (grps || []).filter(g => !g.is_group).map(g => g.name);
    warehouses.value = (whs || []).map(w => ({ name: w.name, label: w.warehouse_name || w.name }));
    taxTemplates.value = (tt || []).map(t => ({ name: t.name, label: t.template_name || t.name }));
    // Income- and expense-class leaf accounts (no root_type column on this
    // app's Account doctype — filter by account_type directly).
    const base = [["is_group","=",0],["company","=",company]];
    const inc = await apiList("Account", { fields:["name"], filters:[...base,["account_type","=","Income"]], limit:500 });
    const exp = await apiList("Account", { fields:["name"], filters:[...base,["account_type","in",["Expense","Cost of Goods Sold"]]], limit:500 });
    incomeAccounts.value  = (inc || []).map(a => a.name);
    expenseAccounts.value = (exp || []).map(a => a.name);
  } catch {}
}

// ── Save ───────────────────────────────────────────────────────────────────
async function saveItem() {
  const checks = [
    [!form.item_name.trim(),                          "Item name is required",       "basic"],
    [!form.stock_uom,                                 "Default UOM is required",     "basic"],
    [!form.tax_code,                                  "Tax Template is required",    "pricing"],
    [!form.income_account,                            "Income account is required",  "pricing"],
    [!form.expense_account,                           "Expense account is required", "pricing"],
    [!!form.is_stock_item && !form.default_warehouse, "Default Warehouse is required when Track Inventory is on", "inventory"],
  ];
  for (const [bad, msg, tab] of checks) {
    if (bad) { drawerTab.value = tab; toast(msg, "error"); return; }
  }
  saving.value = true;
  try {
    const doc = {
      doctype: "Item", name: form.name,
      item_name: form.item_name, item_code: form.item_code,
      item_group: form.item_group || "Products", item_type: form.item_type,
      stock_uom: form.stock_uom, hsn_code: form.hsn_code,
      description: form.description, disabled: form.disabled,
      standard_rate: flt(form.standard_rate), standard_buying_rate: flt(form.standard_buying_rate),
      mrp: flt(form.mrp),
      tax_code: form.tax_code,
      income_account: form.income_account, expense_account: form.expense_account,
      is_stock_item: form.is_stock_item, valuation_method: form.valuation_method,
      default_warehouse: form.default_warehouse,
      reorder_level: flt(form.reorder_level), reorder_qty: flt(form.reorder_qty),
    };
    await apiSave(doc);
    toast("Item updated");
    showDrawer.value = false;
    await load();
  } catch (e) {
    toast(e.message || "Save failed", "error");
  } finally {
    saving.value = false;
  }
}

function fmtQty(v) {
  return Number(flt(v)).toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

onMounted(load);
</script>

<style scoped>
.iv-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px 24px 32px;
  background: #f0f2f5;
  min-height: 100%;
}

/* ── Top bar ── */
.iv-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.iv-topbar-actions { display: flex; gap: 8px; align-items: center; }
.iv-back {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: none;
  border: none;
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  color: #2563eb;
  cursor: pointer;
  padding: 0;
}
.iv-back:hover { text-decoration: underline; }

/* ── Not found ── */
.iv-not-found {
  text-align: center;
  padding: 80px 20px;
  color: #6b7280;
  font-size: 13px;
}

/* ── Header ── */
.iv-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 20px 24px;
}
.iv-item-name  { font-size: 22px; font-weight: 800; color: #1a1d23; letter-spacing: -.3px; }
.iv-item-meta  { display: flex; align-items: center; gap: 6px; margin-top: 6px; flex-wrap: wrap; }
.iv-mono       { font-size: 12px; color: #6b7280; }
.iv-sep        { color: #d1d5db; }
.iv-group-badge { display: inline-flex; padding: 2px 8px; background: #eff6ff; color: #2563eb; border-radius: 10px; font-size: 11.5px; font-weight: 600; }
.iv-type-badge  { display: inline-flex; padding: 2px 8px; background: #f3f4f6; color: #374151; border-radius: 10px; font-size: 11.5px; font-weight: 600; }
.iv-uom         { font-size: 12px; color: #6b7280; }
.iv-status-badge { display: inline-flex; padding: 5px 14px; border-radius: 20px; font-size: 12px; font-weight: 700; flex-shrink: 0; }
.iv-status-active   { background: #dcfce7; color: #16a34a; }
.iv-status-inactive { background: #fee2e2; color: #dc2626; }

/* ── Stats ── */
.iv-stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.iv-stat-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px 18px;
}
.iv-stat-label { font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 6px; }
.iv-stat-val   { font-size: 20px; font-weight: 800; color: #1a1d23; }
.iv-stat-green { color: #16a34a; }
.iv-stat-blue  { color: #2563eb; }

/* skeleton */
.iv-sk-header { height: 88px; background: #fff; border-radius: 12px; border: 1px solid #e5e7eb; animation: sk .8s infinite alternate; }
.iv-sk-card   { animation: sk .8s infinite alternate; }
@keyframes sk { from { opacity:.6 } to { opacity:.3 } }

/* ── Two-col ── */
.iv-two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

/* ── Card ── */
.iv-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 20px 24px;
}
.iv-card-title {
  font-size: 13px;
  font-weight: 700;
  color: #1a1d23;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.iv-total-chip {
  margin-left: auto;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  background: #eff6ff;
  color: #2563eb;
  border-radius: 10px;
}

/* ── KV list ── */
.iv-kv-list { display: flex; flex-direction: column; gap: 0; }
.iv-kv {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
  padding: 7px 0;
  border-bottom: 1px solid #f3f4f6;
  font-size: 13px;
}
.iv-kv:last-child { border-bottom: none; }
.iv-k { color: #6b7280; font-size: 12px; flex-shrink: 0; }
.iv-v { font-weight: 600; color: #1a1d23; text-align: right; }
.iv-description { margin-top: 14px; padding-top: 14px; border-top: 1px solid #f3f4f6; }
.iv-desc-body { font-size: 13px; color: #374151; line-height: 1.6; }

/* ── Warehouse table ── */
.iv-wh-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.iv-wh-table th { background: #f9fafb; border-bottom: 1px solid #e5e7eb; padding: 8px 10px; font-size: 11px; font-weight: 600; color: #374151; text-align: left; text-transform: uppercase; letter-spacing: .04em; }
.iv-wh-table td { padding: 9px 10px; border-bottom: 1px solid #f3f4f6; }
.iv-wh-table tr:last-child td { border-bottom: none; }
.iv-wh-table tr:hover td { background: #fafafa; }
.wh-row-zero td { background: #fff5f5; }
.iv-wh-name { font-weight: 500; color: #374151; font-size: 12.5px; }
.ta-r { text-align: right !important; }
.fw-600 { font-weight: 600; }
.clr-green { color: #16a34a; }
.clr-red   { color: #dc2626; }
.clr-muted { color: #6b7280; }

.iv-no-stock {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 20px;
  font-size: 13px;
  color: #6b7280;
  background: #f9fafb;
  border-radius: 8px;
}

/* ── Reorder strip inside stock card ── */
.iv-reorder-strip {
  margin-top: 14px;
  padding: 12px 14px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}
.iv-reorder-row { display: flex; gap: 24px; flex-wrap: wrap; }
.iv-reorder-item { display: flex; flex-direction: column; gap: 2px; }
.iv-reorder-val  { font-size: 13px; font-weight: 600; color: #1a1d23; }
.iv-auto-po-chip {
  display: inline-flex;
  padding: 1px 8px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 700;
}
.chip-on  { background: #eff6ff; color: #2563eb; }
.chip-off { background: #f3f4f6; color: #6b7280; }
.iv-reorder-alert {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: #dc2626;
  font-weight: 600;
}

/* ── Ledger ── */
.iv-ledger-wrap { overflow-x: auto; }
.iv-ledger-type-badge {
  display: inline-flex;
  padding: 2px 7px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}
.badge-in  { background: #dcfce7; color: #16a34a; }
.badge-out { background: #fee2e2; color: #dc2626; }

/* Ledger card view (mobile only — hidden by default) */
.iv-ledger-cards-view { display: none; }
.iv-ledger-card {
  padding: 11px 12px;
  border: 1px solid #f0f0f0;
  border-radius: 10px;
  background: #fafafa;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.iv-lc-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.iv-lc-qty  { font-size: 15px; font-weight: 700; }
.iv-lc-voucher { font-size: 11.5px; color: #2563eb; margin-top: 1px; }
.iv-lc-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  font-size: 11px;
  color: #6b7280;
  align-items: center;
}

/* ── Buttons ── */
.iv-btn-primary {
  display: inline-flex; align-items: center; gap: 5px;
  background: #2563eb; color: #fff; border: none;
  border-radius: 8px; padding: 8px 16px;
  font: inherit; font-size: 13px; font-weight: 600; cursor: pointer;
}
.iv-btn-primary:hover { background: #1d4ed8; }
.iv-btn-ghost {
  display: inline-flex; align-items: center; gap: 5px;
  background: #fff; color: #374151; border: 1px solid #e5e7eb;
  border-radius: 8px; padding: 7px 12px;
  font: inherit; font-size: 13px; cursor: pointer;
}
.iv-btn-ghost:hover { background: #f9fafb; }

/* ── Edit Drawer ── */
.iv-drawer-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.45); z-index: 900;
  display: flex; justify-content: flex-end;
}
.iv-drawer {
  width: 100%; max-width: 520px; height: 100%;
  background: #fff; display: flex; flex-direction: column;
  box-shadow: -4px 0 24px rgba(0,0,0,.15);
  animation: slideInR .2s ease;
}
@keyframes slideInR { from { transform: translateX(100%) } to { transform: translateX(0) } }
.iv-drawer-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 22px; border-bottom: 1px solid #e5e7eb;
  background: linear-gradient(135deg,#1a1d23,#2d3748);
}
.iv-drawer-title { font-size: 15px; font-weight: 700; color: #fff; }
.iv-drawer-sub   { font-size: 12px; color: rgba(255,255,255,.55); margin-top: 2px; }
.iv-drawer-close {
  background: rgba(255,255,255,.12); border: none; cursor: pointer;
  color: #fff; width: 30px; height: 30px; border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
}
.iv-drawer-tabs {
  display: flex; gap: 0; padding: 10px 16px 0;
  border-bottom: 1px solid #e5e7eb; overflow-x: auto; scrollbar-width: none;
}
.iv-drawer-tabs::-webkit-scrollbar { display: none; }
.iv-dtab {
  padding: 8px 14px; border: none; background: none; cursor: pointer;
  font: inherit; font-size: 12.5px; font-weight: 600; color: #6b7280;
  white-space: nowrap; border-bottom: 2px solid transparent; margin-bottom: -1px;
}
.iv-dtab:hover { color: #374151; }
.iv-dtab--active { color: #2563eb; border-bottom-color: #2563eb; }
.iv-drawer-body  { flex: 1; overflow-y: auto; padding: 20px 22px; display: flex; flex-direction: column; gap: 12px; }
.iv-drawer-footer {
  padding: 14px 22px; border-top: 1px solid #e5e7eb;
  display: flex; justify-content: flex-end; gap: 8px; background: #fafafa;
}

/* Drawer form helpers */
.iv-fg2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.iv-field { display: flex; flex-direction: column; gap: 4px; }
.req { color: #dc2626; }
.iv-type-row { display: flex; flex-wrap: wrap; gap: 6px; }
.iv-type-btn {
  padding: 5px 12px; border-radius: 16px; font: inherit; font-size: 12px;
  font-weight: 600; cursor: pointer; border: 1.5px solid #e5e7eb;
  background: #fff; color: #374151; transition: all .1s;
}
.iv-type-btn--on { background: #1a1d23; color: #fff; border-color: #1a1d23; }
.iv-check-row {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; font-weight: 600; color: #374151; cursor: pointer;
}
.iv-spinner {
  display: inline-block; width: 12px; height: 12px;
  border: 2px solid rgba(255,255,255,.3); border-top-color: #fff;
  border-radius: 50%; animation: spin .6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg) } }

/* ── Responsive ── */

/* Tablet (≤ 900px) */
@media (max-width: 900px) {
  .iv-page        { padding: 14px 16px 28px; gap: 14px; }
  .iv-stats-row   { grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .iv-two-col     { grid-template-columns: 1fr; }
  .iv-stat-val    { font-size: 17px; }
  .iv-item-name   { font-size: 19px; }

  /* Tables scroll horizontally on tablet */
  .iv-wh-table,
  .iv-ledger-wrap { overflow-x: auto; display: block; }

  /* Drawer full-width on tablet */
  .iv-drawer { max-width: 100%; }
}

/* Mobile (≤ 600px) */
@media (max-width: 600px) {
  .iv-page        { padding: 10px 12px 24px; gap: 12px; }

  /* Top bar stacks if needed */
  .iv-topbar      { flex-wrap: wrap; gap: 8px; }
  .iv-back        { font-size: 12px; }

  /* Header card stacks name + badge */
  .iv-header      { flex-direction: column; align-items: flex-start; gap: 8px; padding: 14px 16px; }
  .iv-item-name   { font-size: 17px; }
  .iv-item-meta   { font-size: 11px; gap: 4px; }
  .iv-group-badge,
  .iv-type-badge  { font-size: 10.5px; padding: 1px 6px; }

  /* Stats: 2-col, smaller */
  .iv-stats-row   { grid-template-columns: 1fr 1fr; gap: 8px; }
  .iv-stat-card   { padding: 12px 14px; }
  .iv-stat-label  { font-size: 10px; }
  .iv-stat-val    { font-size: 15px; }

  /* Cards */
  .iv-card        { padding: 14px 16px; border-radius: 10px; }
  .iv-card-title  { font-size: 12.5px; margin-bottom: 12px; }
  .iv-total-chip  { display: none; } /* reclaim space on mobile */

  /* KV list: stack label above value */
  .iv-kv          { flex-direction: column; gap: 2px; align-items: flex-start; padding: 8px 0; }
  .iv-k           { font-size: 10.5px; }
  .iv-v           { font-size: 13px; text-align: left; word-break: break-word; }

  /* Warehouse table: horizontally scrollable */
  .iv-wh-table    { font-size: 12px; }
  .iv-wh-table th,
  .iv-wh-table td { padding: 7px 8px; }

  /* Reorder strip */
  .iv-reorder-row { gap: 14px; }
  .iv-reorder-val { font-size: 12px; }

  /* Ledger — swap table for cards on mobile */
  .iv-ledger-table-view { display: none; }
  .iv-ledger-cards-view { display: flex; flex-direction: column; gap: 8px; }

  /* Drawer — full screen on mobile */
  .iv-drawer-overlay { align-items: flex-end; }
  .iv-drawer      { max-width: 100%; height: 92dvh; border-radius: 16px 16px 0 0; animation: slideInUp .22s ease; }
  @keyframes slideInUp { from { transform: translateY(100%) } to { transform: translateY(0) } }
  .iv-drawer-header { padding: 14px 16px; border-radius: 16px 16px 0 0; }
  .iv-drawer-body { padding: 14px 16px; }
  .iv-drawer-footer { padding: 12px 16px; }
  .iv-fg2         { grid-template-columns: 1fr; }
  .iv-type-row    { gap: 5px; }
  .iv-type-btn    { font-size: 11.5px; padding: 4px 10px; }

  /* Price list: hide Valid From / To on mobile */
  .iv-pl-table td:nth-child(4),
  .iv-pl-table td:nth-child(5),
  .iv-pl-table th:nth-child(4),
  .iv-pl-table th:nth-child(5) { display: none; }
}
</style>