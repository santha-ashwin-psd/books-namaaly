<template>
  <div class="iv-page">

    <!-- ── Top bar ─────────────────────────────────────────────────── -->
    <div class="iv-topbar">
      <button class="iv-back" @click="$router.push('/inventory/items')">
        <span v-html="icon('arrow-left', 14)"></span> Items
      </button>
      <div class="iv-topbar-actions">
        <button class="iv-btn-ghost" @click="load"><span v-html="icon('refresh', 13)"></span></button>
        <button class="iv-btn-primary" @click="openEdit" :disabled="!$canEdit('inventory')" :title="!$canEdit('inventory') ? 'Read-only access' : ''">
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
            <div class="iv-kv"><span class="iv-k">Sales Tax Template</span><span class="iv-v">{{ item.tax_code || '—' }}</span></div>
            <div class="iv-kv"><span class="iv-k">Purchase Tax Template</span><span class="iv-v">{{ item.default_purchase_tax_template || '—' }}</span></div>
            <div class="iv-kv"><span class="iv-k">Income Account</span><span class="iv-v">{{ item.income_account || '—' }}</span></div>
            <div class="iv-kv"><span class="iv-k">Expense Account</span><span class="iv-v">{{ expenseAccountName || item.expense_account || '—' }}</span></div>
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
              <th class="ta-r">Rate (OMR)</th>
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

      <!-- ── Purchased / Sold To (Vendor / Customer) ───────────────── -->
      <div class="iv-card">
        <div class="iv-card-title">
          Purchase &amp; Sales History
          <span class="iv-total-chip" style="background:#eff6ff;color:#2563eb">
            Bought: {{ fmtQty(partyTxns.total_purchased_qty) }}
          </span>
          <span class="iv-total-chip" style="background:#f0fdf4;color:#16a34a">
            Sold: {{ fmtQty(partyTxns.total_sold_qty) }}
          </span>
        </div>
        <div v-if="!partyTxns.rows?.length" class="iv-no-stock">
          No purchase or sales transactions for this item yet
        </div>
        <template v-else>
          <!-- Desktop/tablet: table -->
          <div class="iv-ledger-wrap iv-ledger-table-view">
            <table class="iv-wh-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Type</th>
                  <th>Vendor / Customer</th>
                  <th>Voucher</th>
                  <th class="ta-r">Qty</th>
                  <th class="ta-r">Rate</th>
                  <th class="ta-r">Amount</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in partyTxns.rows" :key="row.type + row.voucher_no">
                  <td class="clr-muted" style="white-space:nowrap">{{ row.posting_date }}</td>
                  <td>
                    <span class="iv-ledger-type-badge" :class="row.type === 'Purchase' ? 'badge-out' : 'badge-in'">
                      {{ row.type === 'Purchase' ? 'Bought from' : 'Sold to' }}
                    </span>
                  </td>
                  <td class="fw-600">{{ row.party_name || row.party }}</td>
                  <td class="iv-mono" style="font-size:11.5px"><DocLink :doctype="row.type === 'Purchase' ? 'Purchase Invoice' : 'Sales Invoice'" :name="row.voucher_no" /></td>
                  <td class="ta-r fw-600" :class="row.type === 'Purchase' ? 'clr-red' : 'clr-green'">
                    {{ fmtQty(row.qty) }} {{ row.uom }}
                  </td>
                  <td class="ta-r clr-muted">{{ fmt(row.rate) }}</td>
                  <td class="ta-r clr-muted">{{ fmt(row.amount) }}</td>
                  <td class="clr-muted" style="font-size:12px">{{ row.status }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <!-- Mobile: cards -->
          <div class="iv-ledger-cards-view">
            <div v-for="row in partyTxns.rows" :key="row.type + row.voucher_no" class="iv-ledger-card">
              <div class="iv-lc-top">
                <span class="iv-ledger-type-badge" :class="row.type === 'Purchase' ? 'badge-out' : 'badge-in'">
                  {{ row.type === 'Purchase' ? 'Bought from' : 'Sold to' }}
                </span>
                <span class="iv-lc-qty" :class="row.type === 'Purchase' ? 'clr-red' : 'clr-green'">
                  {{ fmtQty(row.qty) }} {{ row.uom }}
                </span>
              </div>
              <div class="fw-600">{{ row.party_name || row.party }}</div>
              <div class="iv-lc-voucher iv-mono"><DocLink :doctype="row.type === 'Purchase' ? 'Purchase Invoice' : 'Sales Invoice'" :name="row.voucher_no" :mono-style="false" /></div>
              <div class="iv-lc-meta">
                <span>{{ row.posting_date }}</span>
                <span class="iv-sep">·</span>
                <span class="clr-muted">{{ row.status }}</span>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- ── Stock Ledger ───────────────────────────────────────── -->
      <div class="iv-card">
        <div class="iv-card-title">
          Stock Ledger
          <span class="iv-total-chip" style="background:#f0fdf4;color:#16a34a">Last 30 entries</span>
          <label v-if="cancelledCount" class="iv-show-cancelled">
            <input type="checkbox" v-model="showCancelled" />
            Show cancelled ({{ cancelledCount }})
          </label>
        </div>
        <div v-if="!item.is_stock_item" class="iv-no-stock">Service item — no stock ledger</div>
        <div v-else-if="!ledger.length" class="iv-no-stock">No stock movements yet</div>
        <div v-else-if="!visibleLedger.length" class="iv-no-stock">No active stock movements — check "Show cancelled" above</div>
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
                  <th v-if="showCancelled"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in visibleLedger" :key="row.name" :class="{ 'iv-row-cancelled': isCancelled(row) }">
                  <td class="clr-muted" style="white-space:nowrap">{{ row.posting_date }}</td>
                  <td>
                    <span class="iv-ledger-type-badge" :class="row.actual_qty > 0 ? 'badge-in' : 'badge-out'">
                      {{ row.voucher_type || '—' }}
                    </span>
                    <span v-if="isCancelled(row)" class="iv-ledger-type-badge badge-cancelled" > Cancelled </span>
                  </td>
                  <td class="iv-mono" style="font-size:11.5px"><DocLink :doctype="row.voucher_type" :name="row.voucher_no" /></td>
                  <td class="clr-muted" style="font-size:12px">{{ row.warehouse }}</td>
                  <td class="ta-r fw-600" :class="row.actual_qty > 0 ? 'clr-green' : 'clr-red'">
                    {{ row.actual_qty > 0 ? '+' : '' }}{{ fmtQty(row.actual_qty) }}
                  </td>
                  <td class="ta-r clr-muted">{{ fmtQty(row.qty_after_transaction) }}</td>
                  <td class="ta-r clr-muted">{{ fmt(row.incoming_rate || row.valuation_rate) }}</td>
                  <td v-if="showCancelled" class="ta-r">
                   <button v-if="isCancelled(row)" class="iv-btn-ghost iv-btn-danger" :disabled="!$canEdit('inventory') || deletingName === row.name"
                      :title="!$canEdit('inventory') ? 'Read-only access' : 'Delete this cancelled entry'"
                      @click="deleteLedgerEntry(row)">
                      <span v-html="icon('trash', 12)"></span>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <!-- Mobile: cards -->
          <div class="iv-ledger-cards-view">
           <div
    v-for="row in visibleLedger"
    :key="row.name"
    class="iv-ledger-card"
    :class="{ 'iv-row-cancelled': isCancelled(row) }"
>
              <div class="iv-lc-top">
                <span class="iv-ledger-type-badge" :class="row.actual_qty > 0 ? 'badge-in' : 'badge-out'">
                  {{ row.voucher_type || '—' }}
                </span>
                <span
    v-if="isCancelled(row)"
    class="iv-ledger-type-badge badge-cancelled"
>
    Cancelled
</span>
                <span class="iv-lc-qty" :class="row.actual_qty > 0 ? 'clr-green' : 'clr-red'">
                  {{ row.actual_qty > 0 ? '+' : '' }}{{ fmtQty(row.actual_qty) }}
                </span>
              </div>
              <div class="iv-lc-voucher iv-mono"><DocLink :doctype="row.voucher_type" :name="row.voucher_no" :mono-style="false" /></div>
              <div class="iv-lc-meta">
                <span>{{ row.posting_date }}</span>
                <span class="iv-sep">·</span>
                <span class="clr-muted">Balance: {{ fmtQty(row.qty_after_transaction) }}</span>
                <span class="iv-sep">·</span>
                <span class="clr-muted">{{ row.warehouse }}</span>
              </div>
              <button v-if="isCancelled(row)" class="iv-btn-ghost iv-btn-danger" style="align-self:flex-start;margin-top:4px"
                :disabled="!$canEdit('inventory') || deletingName === row.name"
                @click="deleteLedgerEntry(row)">
                <span v-html="icon('trash', 12)"></span> Delete
              </button>
            </div>
          </div>
        </template>
      </div>

    </template>

    <ItemEditDrawer ref="itemDrawer" @saved="load" />

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { apiGET, apiPOST, apiList } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { useConfirm } from "../composables/useConfirm.js";
import { fmt, flt } from "../utils/format.js";
import { icon } from "../utils/icons.js";
import ItemEditDrawer from "../components/ItemEditDrawer.vue";
import DocLink from "../components/DocLink.vue";

const { toast }   = useToast();
const { confirm } = useConfirm();
const route     = useRoute();
const itemCode  = computed(() => route.params.itemCode);
const itemDrawer = ref(null);

// ── Data ───────────────────────────────────────────────────────────────────
const item        = ref(null);
const stockDetail = ref({ warehouses: [], total_qty: 0, total_value: 0 });
const ledger        = ref([]);
const showCancelled = ref(false);           // toggle: also show cancelled SLEs in the ledger
const deletingName  = ref("");              // name of the row currently being deleted (button spinner)
const priceLists  = ref([]);
const partyTxns   = ref({ rows: [], total_purchased_qty: 0, total_sold_qty: 0 });
const loading     = ref(true);
const expenseAccountName = ref("");

const isCancelled = (row) => Number(row.is_cancelled) === 1;

const visibleLedger = computed(() => {
    if (showCancelled.value) {
        return ledger.value;
    }

    return ledger.value.filter(row => !isCancelled(row));
});

const cancelledCount = computed(() => {
    return ledger.value.filter(row => isCancelled(row)).length;
});

// ── Load ───────────────────────────────────────────────────────────────────
async function load() {
  loading.value = true;
  item.value    = null;
  try {
    const [full, stock, sled, pl, ptx] = await Promise.all([
      apiGET("zoho_books_clone.api.docs.get_doc", { doctype: "Item", name: itemCode.value }),
      apiGET("zoho_books_clone.api.inventory.get_item_stock_detail", { item_code: itemCode.value }),
      apiGET("zoho_books_clone.api.inventory.get_stock_ledger_entries", { item_code: itemCode.value, limit: 30, include_cancelled: 1 }),
      apiGET("zoho_books_clone.api.inventory.get_item_price_list", { item_code: itemCode.value }).catch(() => []),
      apiGET("zoho_books_clone.api.inventory.get_item_party_transactions", { item_code: itemCode.value, limit: 50 })
        .catch(() => ({ rows: [], total_purchased_qty: 0, total_sold_qty: 0 })),
    ]);
    item.value        = full;
    stockDetail.value = stock || { warehouses: [], total_qty: 0, total_value: 0 };
    ledger.value      = sled  || [];
    priceLists.value  = pl    || [];
    partyTxns.value   = ptx   || { rows: [], total_purchased_qty: 0, total_sold_qty: 0 };
    expenseAccountName.value = "";
    if (item.value?.expense_account) {
      try {
        const rows = await apiList("Account", { fields: ["name", "account_name"], filters: [["name", "=", item.value.expense_account]], limit: 1 });
        expenseAccountName.value = rows?.[0]?.account_name || item.value.expense_account;
      } catch { expenseAccountName.value = item.value.expense_account; }
    }
  } catch (e) {
    toast(e.message || "Failed to load item", "error");
  } finally {
    loading.value = false;
  }
}

// ── Open edit ──────────────────────────────────────────────────────────────
// Uses the shared ItemEditDrawer component (the same Add/Edit drawer as the
// Items list page) instead of a separate, page-local drawer implementation.
function openEdit() {
  if (!item.value) return;
  itemDrawer.value?.openEdit(item.value);
}

// ── Delete a cancelled stock ledger entry ────────────────────────────────────
async function deleteLedgerEntry(row) {
  const ok = await confirm({
    title: "Delete Cancelled Entry",
    body: `Permanently delete this cancelled stock ledger entry (${row.voucher_type} ${row.voucher_no})? This cannot be undone.`,
    okLabel: "Delete",
    okStyle: "danger",
  });
  if (!ok) return;
  deletingName.value = row.name;
  try {
    await apiPOST(
      "zoho_books_clone.api.inventory.delete_cancelled_stock_ledger_entry",
      { name: row.name },
      { module: "inventory", action: "delete" }
    );
    ledger.value = ledger.value.filter(r => r.name !== row.name);
    toast("Cancelled entry deleted", "success");
  } catch (e) {
    toast(e.message || "Failed to delete entry", "error");
  } finally {
    deletingName.value = "";
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
.badge-cancelled { background: #f3f4f6; color: #6b7280; margin-left: 5px; }

.iv-show-cancelled {
  display: inline-flex; align-items: center; gap: 5px;
  margin-left: 12px; font-size: 12px; font-weight: 500; color: #6b7280;
  cursor: pointer; text-transform: none; letter-spacing: 0;
}
.iv-show-cancelled input { cursor: pointer; }

.iv-row-cancelled td, .iv-row-cancelled.iv-ledger-card { opacity: .55; }

.iv-btn-danger { padding: 5px 8px; color: #dc2626; border-color: #fecaca; }
.iv-btn-danger:hover:not(:disabled) { background: #fef2f2; }
.iv-btn-danger:disabled { opacity: .4; cursor: not-allowed; }

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

  /* Price list: hide Valid From / To on mobile */
  .iv-pl-table td:nth-child(4),
  .iv-pl-table td:nth-child(5),
  .iv-pl-table th:nth-child(4),
  .iv-pl-table th:nth-child(5) { display: none; }
}
</style>