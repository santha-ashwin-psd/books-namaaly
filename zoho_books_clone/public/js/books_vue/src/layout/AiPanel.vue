<template>
  <Teleport to="body">
    <div v-if="open" class="bv-ai-panel" :class="{ 'bv-ai-panel--pro': proMode }">

      <div class="bv-ai-header" :class="{ 'bv-ai-header--pro': proMode }">
        <span class="bv-ai-header-title">
          <IconSvg name="sparkle" :size="15" />
          Books AI
          <span v-if="proMode" class="bv-ai-pro-badge">PRO</span>
        </span>
        <div style="display:flex;align-items:center;gap:6px">
          <button class="bv-ai-pro-toggle" :class="{ active: proMode }"
            @click="togglePro" :title="proMode ? 'Disable Pro Mode' : 'Enable Pro Mode — full app control'">
            ⚡ {{ proMode ? 'Pro On' : 'Pro' }}
          </button>
          <button class="bv-ai-clear-btn" @click="clearChat" title="Clear conversation">🗑</button>
          <button class="bv-ai-close" @click="$emit('close')">✕</button>
        </div>
      </div>

      <!-- Pro Mode Banner -->
      <div v-if="proMode" class="bv-ai-pro-banner">
        ⚡ Pro Mode — AI can create customers, suppliers, items, quotations, record payments, cancel invoices, and update prices.
      </div>

      <!-- Pending Goal Banner -->
      <div v-if="pendingGoal" class="bv-ai-goal-banner">
        📋 Invoice for <strong>{{ pendingGoal.customer }}</strong> — completing purchase first, then resuming
      </div>

      <!-- Proactive Alerts -->
      <div v-if="alerts.length && showAlerts" class="bv-ai-alerts">
        <div class="bv-ai-alerts-title">
          <span>🔔 Alerts</span>
          <button class="bv-ai-alerts-dismiss" @click="dismissAlerts">Dismiss</button>
        </div>
        <div v-for="(a, i) in alerts" :key="i"
          class="bv-ai-alert-item" :class="`bv-ai-alert-${a.type}`"
          @click="a.action && handleAlertClick(a)" :style="a.action ? 'cursor:pointer' : ''">
          {{ a.icon }} {{ a.text }}
          <span v-if="a.action" class="bv-ai-alert-arrow">→</span>
        </div>
      </div>

      <div ref="logEl" class="bv-ai-log">
        <div v-for="(m, i) in messages" :key="i" :class="`bv-ai-msg bv-ai-msg-${m.role}`">
          <div class="bv-ai-msg-text" v-html="renderText(m.content)"></div>

          <!-- Customer suggestion chips -->
          <div v-if="isCustomerPrompt(m, i) && topCustomers.length" class="bv-ai-cust-chips">
            <span class="bv-ai-cust-chips-label">Quick select:</span>
            <button v-for="c in topCustomers" :key="c.name"
              class="bv-ai-cust-chip"
              @click="onCustomerChipClick(c)">
              {{ c.customer_name || c.name }}
            </button>
          </div>

          <!-- Item suggestion chips -->
          <div v-if="isItemPrompt(m, i) && topItems.length" class="bv-ai-item-chips">
            <span class="bv-ai-item-chips-label">Top sold items:</span>
            <button v-for="it in topItems" :key="it.item_code || it.name"
              class="bv-ai-item-chip"
              @click="onItemChipClick(it)">
              {{ it.item_name || it.item_code || it.name }}
            </button>
          </div>

          <!-- Warehouse stock chips OR no-stock action panel -->
          <template v-if="isWarehousePrompt(m, i)">
            <div v-if="warehouseStock.length" class="bv-ai-wh-chips">
              <span class="bv-ai-wh-chips-label">In stock:</span>
              <button v-for="wh in warehouseStock" :key="wh.warehouse"
                class="bv-ai-wh-chip"
                @click="onWarehouseChipClick(wh)">
                {{ wh.warehouse }}
                <span class="bv-ai-wh-qty">{{ wh.actual_qty }} units</span>
              </button>
            </div>
            <div v-else-if="lastSelectedItem" class="bv-ai-nostock-panel">
              <div class="bv-ai-nostock-title">⚠️ No warehouse has stock for <strong>{{ lastSelectedItem }}</strong></div>
              <div class="bv-ai-nostock-sub">To create this invoice you'll need to receive stock first.</div>
              <div class="bv-ai-nostock-actions">
                <button class="bv-ai-nostock-btn bv-ai-nostock-btn--primary" @click="onOrderFromSupplier">
                  🛒 Order from supplier
                </button>
                <button class="bv-ai-nostock-btn bv-ai-nostock-btn--secondary" @click="onAddStockManually">
                  📦 Add stock manually
                </button>
                <button class="bv-ai-nostock-btn bv-ai-nostock-btn--ghost" @click="sendQuick('continue without checking stock')">
                  ⏭ Continue anyway
                </button>
              </div>
            </div>
          </template>

          <!-- Supplier chips -->
          <div v-if="isSupplierPrompt(m, i) && topSuppliers.length" class="bv-ai-sup-chips">
            <span class="bv-ai-sup-chips-label">Recent suppliers:</span>
            <button v-for="s in topSuppliers" :key="s.name"
              class="bv-ai-sup-chip"
              @click="sendQuick(s.supplier_name || s.name)">
              {{ s.supplier_name || s.name }}
            </button>
          </div>

          <!-- Payment mode chips -->
          <div v-if="isPaymentModePrompt(m, i)" class="bv-ai-pay-chips">
            <span class="bv-ai-pay-chips-label">Select mode:</span>
            <button v-for="mode in PAYMENT_MODES" :key="mode"
              class="bv-ai-pay-chip"
              @click="sendQuick(mode)">
              {{ mode }}
            </button>
          </div>

          <!-- Unpaid invoice chips -->
          <div v-if="isInvoiceSelectPrompt(m, i) && unpaidInvoices.length" class="bv-ai-inv-chips">
            <span class="bv-ai-inv-chips-label">Outstanding invoices:</span>
            <button v-for="inv in unpaidInvoices" :key="inv.name"
              class="bv-ai-inv-chip"
              @click="sendQuick(inv.name)">
              <span class="bv-ai-inv-name">{{ inv.name }}</span>
              <span class="bv-ai-inv-meta">{{ inv.customer }} · OMR {{ Number(inv.outstanding_amount || 0).toLocaleString() }}</span>
            </button>
          </div>

          <!-- Yes / No chips -->
          <div v-if="isYesNoPrompt(m, i)" class="bv-ai-yn-chips">
            <button class="bv-ai-yn-chip bv-ai-yn-chip--yes" @click="sendQuick('Yes, proceed')">✓ Yes, proceed</button>
            <button class="bv-ai-yn-chip bv-ai-yn-chip--no"  @click="sendQuick('No, skip')">✕ No, skip</button>
          </div>

          <!-- Price list chips -->
          <div v-if="isPriceListPrompt(m, i) && aiPriceLists.length" class="bv-ai-pl-chips">
            <span class="bv-ai-pl-chips-label">Price lists:</span>
            <button v-for="pl in aiPriceLists" :key="pl.name"
              class="bv-ai-pl-chip"
              @click="sendQuick(pl.name)">
              {{ pl.name }}
              <span v-if="pl.currency" class="bv-ai-pl-currency">{{ pl.currency }}</span>
            </button>
          </div>

          <!-- Invoice creation confirm card -->
          <div v-if="m.confirm" class="bv-ai-confirm-card">
            <div class="bv-ai-confirm-header">📄 Invoice Preview</div>
            <div class="bv-ai-confirm-row">
              <span class="bv-ai-confirm-label">Customer</span>
              <span>{{ m.confirm.customer || '—' }}</span>
            </div>
            <div v-for="(item, j) in (m.confirm.items || [])" :key="j" class="bv-ai-confirm-row">
              <span class="bv-ai-confirm-label">{{ item.item_name }}</span>
              <span>× {{ item.qty }} @ OMR {{ Number(item.rate || 0).toLocaleString() }}</span>
            </div>
            <div class="bv-ai-confirm-total" v-if="confirmTotal(m.confirm)">
              Total: OMR {{ confirmTotal(m.confirm).toLocaleString() }}
            </div>
            <div v-if="!m.confirmed" class="bv-ai-confirm-actions">
              <button class="bv-ai-confirm-yes" @click="doConfirmCreate(m)">✓ Confirm</button>
              <button class="bv-ai-confirm-no" @click="doCancelCreate(m)">✕ Cancel</button>
            </div>
            <div v-else class="bv-ai-confirm-done">{{ m.confirmed }}</div>
          </div>

          <!-- Pro Mode confirm cards -->
          <div v-if="m.proAction" class="bv-ai-confirm-card"
            :class="m.proAction === 'cancel_invoice' ? 'bv-ai-confirm-card--danger' : 'bv-ai-confirm-card--pro'">

            <!-- Create Customer -->
            <template v-if="m.proAction === 'create_customer'">
              <div class="bv-ai-confirm-header">👤 New Customer</div>
              <div class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">Name</span><span>{{ m.proData.customer_name }}</span></div>
              <div v-if="m.proData.email" class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">Email</span><span>{{ m.proData.email }}</span></div>
              <div v-if="m.proData.mobile_no" class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">Phone</span><span>{{ m.proData.mobile_no }}</span></div>
            </template>

            <!-- Create Supplier -->
            <template v-else-if="m.proAction === 'create_supplier'">
              <div class="bv-ai-confirm-header">🏭 New Supplier</div>
              <div class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">Name</span><span>{{ m.proData.supplier_name }}</span></div>
              <div v-if="m.proData.email" class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">Email</span><span>{{ m.proData.email }}</span></div>
              <div v-if="m.proData.mobile_no" class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">Phone</span><span>{{ m.proData.mobile_no }}</span></div>
            </template>

            <!-- Create Item -->
            <template v-else-if="m.proAction === 'create_item'">
              <div class="bv-ai-confirm-header">📦 New Item</div>
              <div class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">Name</span><span>{{ m.proData.item_name }}</span></div>
              <div class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">Type</span><span>{{ m.proData.item_type || 'Product' }}</span></div>
              <div v-if="m.proData.item_group" class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">Group</span><span>{{ m.proData.item_group }}</span></div>
              <div class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">Rate</span><span>OMR {{ Number(m.proData.rate || 0).toLocaleString() }}</span></div>
              <div class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">UOM</span><span>{{ m.proData.uom || 'Nos' }}</span></div>
            </template>

            <!-- Create Quotation -->
            <template v-else-if="m.proAction === 'create_quotation'">
              <div class="bv-ai-confirm-header">📋 Quotation Preview</div>
              <div class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">Customer</span><span>{{ m.proData.customer }}</span></div>
              <div v-for="(item, j) in (m.proData.items || [])" :key="j" class="bv-ai-confirm-row">
                <span class="bv-ai-confirm-label">{{ item.item_name }}</span>
                <span>× {{ item.qty }} @ OMR {{ Number(item.rate || 0).toLocaleString() }}</span>
              </div>
              <div class="bv-ai-confirm-total" v-if="confirmTotal(m.proData)">
                Total: OMR {{ confirmTotal(m.proData).toLocaleString() }}
              </div>
            </template>

            <!-- Record Payment -->
            <template v-else-if="m.proAction === 'create_payment'">
              <div class="bv-ai-confirm-header">💵 Payment Preview</div>
              <div class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">Invoice</span><span>{{ m.proData.invoice }}</span></div>
              <div class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">Customer</span><span>{{ m.proData.customer }}</span></div>
              <div class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">Amount</span><span style="font-weight:700;color:#2F9E44">OMR {{ Number(m.proData.amount || 0).toLocaleString() }}</span></div>
              <div class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">Mode</span><span>{{ m.proData.mode || 'Cash' }}</span></div>
            </template>

            <!-- Cancel Invoice -->
            <template v-else-if="m.proAction === 'cancel_invoice'">
              <div class="bv-ai-confirm-header">🚫 Cancel Invoice</div>
              <div class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">Invoice</span><span>{{ m.proData.invoice }}</span></div>
              <div class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">Customer</span><span>{{ m.proData.customer }}</span></div>
              <div class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">Amount</span><span>OMR {{ Number(m.proData.amount || 0).toLocaleString() }}</span></div>
              <div style="font-size:11px;color:#b91c1c;margin-top:6px">⚠️ This action cannot be easily undone.</div>
            </template>

            <!-- Update Item Price -->
            <template v-else-if="m.proAction === 'update_item_price'">
              <div class="bv-ai-confirm-header">💲 Price Update</div>
              <div class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">Item</span><span>{{ m.proData.item_name }}</span></div>
              <div class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">Old Rate</span><span style="text-decoration:line-through;color:#94a3b8">OMR {{ Number(m.proData.old_rate || 0).toLocaleString() }}</span></div>
              <div class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">New Rate</span><span style="font-weight:700;color:#2F9E44">OMR {{ Number(m.proData.new_rate || 0).toLocaleString() }}</span></div>
            </template>

            <!-- Purchase Order (no-stock flow) -->
            <template v-else-if="m.proAction === 'create_purchase_order'">
              <div class="bv-ai-confirm-header">🛒 Purchase Order</div>
              <div class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">Item</span><span>{{ m.proData.item_code }}</span></div>
              <div class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">Supplier</span><span>{{ m.proData.supplier }}</span></div>
              <div class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">Qty</span><span>{{ m.proData.qty }}</span></div>
              <div v-if="m.proData.rate" class="bv-ai-confirm-row"><span class="bv-ai-confirm-label">Rate</span><span>OMR {{ Number(m.proData.rate || 0).toLocaleString() }}</span></div>
              <div style="font-size:11px;color:#15803d;margin-top:6px">✓ Stock will be received immediately after confirmation.</div>
            </template>

            <div v-if="!m.proConfirmed" class="bv-ai-confirm-actions">
              <button class="bv-ai-confirm-yes" :class="m.proAction === 'cancel_invoice' ? 'bv-ai-confirm-yes--danger' : ''"
                @click="doProAction(m)">✓ Confirm</button>
              <button class="bv-ai-confirm-no" @click="doCancelPro(m)">✕ Cancel</button>
            </div>
            <div v-else class="bv-ai-confirm-done">{{ m.proConfirmed }}</div>
          </div>

          <div v-if="m.action && !PRO_CONFIRM_ACTIONS.has(m.action) && m.action !== 'create_invoice_confirm'" class="bv-ai-action-chip">
            ✓ {{ actionLabel(m.action) }}
          </div>
        </div>

        <div v-if="busy" class="bv-ai-msg bv-ai-msg-assistant bv-ai-thinking">
          <span></span><span></span><span></span>
        </div>
      </div>

      <!-- Quick chips — standard + pro -->
      <div v-if="messages.length <= 1 && !busy" class="bv-ai-chips">
        <button class="bv-ai-chip" @click="sendQuick('Create invoice')">📄 New invoice</button>
        <button class="bv-ai-chip" @click="sendQuick('Show overdue invoices')">⚠️ Overdue</button>
        <button class="bv-ai-chip" @click="sendQuick('Revenue this month')">📈 Revenue</button>
        <button class="bv-ai-chip" @click="sendQuick('Business summary')">📊 Summary</button>
        <button class="bv-ai-chip" @click="sendQuick('Profit estimate this month')">💰 Profit</button>
        <template v-if="proMode">
          <button class="bv-ai-chip bv-ai-chip--pro" @click="sendQuick('Create a new customer')">👤 New customer</button>
          <button class="bv-ai-chip bv-ai-chip--pro" @click="sendQuick('Record a payment for an invoice')">💵 Record payment</button>
          <button class="bv-ai-chip bv-ai-chip--pro" @click="sendQuick('Create a quotation')">📋 New quote</button>
          <button class="bv-ai-chip bv-ai-chip--pro" @click="sendQuick('Update item price')">💲 Update price</button>
        </template>
        <button class="bv-ai-chip" @click="sendQuick('help')">❓ Help</button>
      </div>

      <form class="bv-ai-input" @submit.prevent="send">
        <input ref="inputEl" v-model="draft" :disabled="busy"
          :placeholder="proMode ? 'Create, update, or query anything…' : 'Ask about invoices, revenue, stock levels…'"
          @keydown.enter.prevent="send"/>
        <button type="submit" :disabled="busy || !draft.trim()" class="bv-ai-send"
          :class="{ 'bv-ai-send--pro': proMode }">→</button>
      </form>

    </div>
  </Teleport>
</template>

<script setup>
import { ref, nextTick, watch, onMounted } from "vue";
import IconSvg from "../components/IconSvg.vue";
import { apiPOST, apiList } from "../api/client.js";
import { useAiActions } from "../composables/useAiActions.js";

const props = defineProps({
  open:   { type: Boolean, default: false },
  alerts: { type: Array,   default: () => [] },
});
const emit = defineEmits(["close", "alerts-seen"]);

const STORAGE_KEY   = "books_ai_chat_v2";
const PRO_KEY       = "books_ai_pro_mode";
const PAYMENT_MODES = ["Cash", "Bank Transfer", "UPI", "Cheque"];
const GREETING      = "Hi! I'm your Books AI assistant.\n\nI can query revenue, outstanding invoices, payments, profit estimates, check stock levels, find low-stock items, show top customers & suppliers, guide you through creating invoices, and navigate the app.\n\nEnable **Pro Mode** (⚡ button above) to also create customers, suppliers, items, quotations, record payments, cancel invoices, and update prices.\n\nUse the quick actions below or just type naturally.";

// ── Pro confirm action set ────────────────────────────────────────────────────
const PRO_CONFIRM_ACTIONS = new Set([
  "create_customer_confirm", "create_supplier_confirm", "create_item_confirm",
  "create_quotation_confirm", "create_payment_confirm",
  "cancel_invoice_confirm", "update_item_price_confirm",
  "create_purchase_order_confirm",
]);

const PRO_CONFIRM_TYPE_MAP = {
  create_customer_confirm:      "create_customer",
  create_supplier_confirm:      "create_supplier",
  create_item_confirm:          "create_item",
  create_quotation_confirm:     "create_quotation",
  create_payment_confirm:       "create_payment",
  cancel_invoice_confirm:       "cancel_invoice",
  update_item_price_confirm:    "update_item_price",
  create_purchase_order_confirm:"create_purchase_order",
};

// ── State ─────────────────────────────────────────────────────────────────────
const draft             = ref("");
const busy              = ref(false);
const proMode           = ref(false);
const messages          = ref([]);
const logEl             = ref(null);
const inputEl           = ref(null);
const showAlerts        = ref(true);

// Suggestion chip data
const topCustomers      = ref([]);
const topItems          = ref([]);
const warehouseStock    = ref([]);
const topSuppliers      = ref([]);
const unpaidInvoices    = ref([]);
const aiPriceLists      = ref([]);

// Goal tracking
const lastSelectedItem    = ref(null);
const lastInvoiceCustomer = ref(null);
const pendingGoal         = ref(null); // { type: "create_invoice", customer: String }

const { dispatch } = useAiActions();

// ── Direct-hash navigation ────────────────────────────────────────────────────
const HASH_NAV = {
  show_items:       "#/inventory/items",
  show_item_groups: "#/inventory/item-groups",
  show_warehouses:  "#/inventory/warehouses",
  show_inventory:   "#/inventory/items",
  show_suppliers:   "#/suppliers",
  show_customers:   "#/customers",
  show_dashboard:   "#/",
};

const ACTION_LABELS = {
  show_overdue:          "Filtered to overdue invoices",
  show_unpaid:           "Filtered to unpaid invoices",
  show_all_invoices:     "Showing all invoices",
  find_invoices:         "Filtered by customer",
  create_invoice:        "Opened new invoice",
  show_outstanding:      "Navigated to dashboard",
  show_bills:            "Navigated to bills",
  show_quotes:           "Navigated to quotes",
  show_customers:        "Navigated to customers",
  show_suppliers:        "Navigated to suppliers",
  show_dashboard:        "Navigated to dashboard",
  show_sales_orders:     "Navigated to sales orders",
  show_purchase_orders:  "Navigated to purchase orders",
  show_items:            "Navigated to items",
  show_item_groups:      "Navigated to item groups",
  show_warehouses:       "Navigated to warehouses",
  show_inventory:        "Navigated to inventory",
  navigate:              "Navigated",
};

function actionLabel(a) { return ACTION_LABELS[a] || a; }

// ── Suggestion chip — prompt detectors ───────────────────────────────────────
function _isLastMsg(m, i) {
  return i === messages.value.length - 1 && !m.confirm && !m.proAction;
}

function isCustomerPrompt(m, i) {
  if (!_isLastMsg(m, i)) return false;
  const lower = (m.content || "").toLowerCase();
  return (
    lower.includes("invoice for") ||
    lower.includes("quotation for") ||
    lower.includes("who is this") ||
    (lower.includes("customer") && (lower.includes("invoice") || lower.includes("which") || lower.includes("quotation")))
  );
}

function isItemPrompt(m, i) {
  if (!_isLastMsg(m, i)) return false;
  const lower = (m.content || "").toLowerCase();
  return (
    (lower.includes("item") && (lower.includes("add") || lower.includes("like") || lower.includes("want") || lower.includes("invoice"))) ||
    lower.includes("what would you like") ||
    lower.includes("which item") ||
    lower.includes("product")
  );
}

function isWarehousePrompt(m, i) {
  if (!_isLastMsg(m, i)) return false;
  const lower = (m.content || "").toLowerCase();
  return lower.includes("warehouse") || lower.includes("stock location") || lower.includes("from which location");
}

function isSupplierPrompt(m, i) {
  if (!_isLastMsg(m, i)) return false;
  const lower = (m.content || "").toLowerCase();
  return lower.includes("supplier") && (lower.includes("which") || lower.includes("from") || lower.includes("order"));
}

function isPaymentModePrompt(m, i) {
  if (!_isLastMsg(m, i)) return false;
  const lower = (m.content || "").toLowerCase();
  return (lower.includes("mode") || lower.includes("method")) && lower.includes("pay");
}

function isInvoiceSelectPrompt(m, i) {
  if (!_isLastMsg(m, i)) return false;
  const lower = (m.content || "").toLowerCase();
  return (
    lower.includes("which invoice") ||
    lower.includes("outstanding invoice") ||
    (lower.includes("invoice") && lower.includes("payment for"))
  );
}

function isYesNoPrompt(m, i) {
  if (!_isLastMsg(m, i)) return false;
  const lower = (m.content || "").toLowerCase();
  return (
    lower.includes("would you like") ||
    lower.includes("should i") ||
    lower.includes("do you want") ||
    lower.includes("shall i")
  );
}

function isPriceListPrompt(m, i) {
  if (!_isLastMsg(m, i)) return false;
  return (m.content || "").toLowerCase().includes("price list");
}

// ── Data loaders ──────────────────────────────────────────────────────────────
async function loadTopCustomers() {
  if (topCustomers.value.length) return;
  try {
    const res = await apiList("Customer", { fields: ["name","customer_name"], limit: 5, order_by: "modified desc" });
    topCustomers.value = res || [];
  } catch {}
}

async function loadTopItems() {
  if (topItems.value.length) return;
  try {
    const res = await apiPOST("zoho_books_clone.api.books_data.get_top_sold_items", { limit: 7 });
    topItems.value = Array.isArray(res) ? res : [];
  } catch {}
}

async function loadWarehousesForItem(itemCode) {
  warehouseStock.value = [];
  if (!itemCode) return;
  try {
    const res = await apiPOST("zoho_books_clone.api.books_data.get_item_warehouse_stock", { item_code: itemCode });
    warehouseStock.value = Array.isArray(res) ? res : [];
  } catch {}
}

async function loadTopSuppliers() {
  if (topSuppliers.value.length) return;
  try {
    const res = await apiList("Supplier", { fields: ["name","supplier_name"], limit: 5, order_by: "modified desc" });
    topSuppliers.value = res || [];
  } catch {}
}

async function loadUnpaidInvoices() {
  if (unpaidInvoices.value.length) return;
  try {
    const res = await apiList("Sales Invoice", {
      filters: [["outstanding_amount",">",0],["docstatus","=",1]],
      fields: ["name","customer","outstanding_amount"],
      limit: 5,
      order_by: "due_date asc",
    });
    unpaidInvoices.value = res || [];
  } catch {}
}

async function loadAiPriceLists() {
  if (aiPriceLists.value.length) return;
  try {
    const res = await apiList("Price List", {
      filters: [["enabled","=",1]],
      fields: ["name","currency"],
      limit: 5,
    });
    aiPriceLists.value = res || [];
  } catch {}
}

// ── Chip click handlers ───────────────────────────────────────────────────────
function onCustomerChipClick(c) {
  const name = c.customer_name || c.name;
  lastInvoiceCustomer.value = name;
  sendQuick(name);
}

function onItemChipClick(item) {
  lastSelectedItem.value = item.item_code || item.name;
  warehouseStock.value = [];
  loadWarehousesForItem(lastSelectedItem.value);
  sendQuick(item.item_name || item.item_code || item.name);
}

function onWarehouseChipClick(wh) {
  sendQuick(wh.warehouse);
}

function onOrderFromSupplier() {
  pendingGoal.value = { type: "create_invoice", customer: lastInvoiceCustomer.value || "" };
  loadTopSuppliers();
  const item = lastSelectedItem.value || "the item";
  sendQuick(`I need to order "${item}" from a supplier to restock before creating the invoice`);
}

function onAddStockManually() {
  pendingGoal.value = { type: "create_invoice", customer: lastInvoiceCustomer.value || "" };
  const item = lastSelectedItem.value || "the item";
  sendQuick(`I want to add stock manually for "${item}" before creating the invoice`);
}

// ── Goal resumption ───────────────────────────────────────────────────────────
function resumePendingGoal() {
  const g = pendingGoal.value;
  if (!g) return;
  pendingGoal.value = null;
  const msg = g.customer
    ? `Stock is now available. Let's create the invoice for ${g.customer}`
    : "Stock is now available. Let's get back to creating that invoice";
  setTimeout(() => sendQuick(msg), 900);
}

// ── Render helpers ────────────────────────────────────────────────────────────
function renderText(text) {
  return (text || "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>");
}

function confirmTotal(d) {
  return (d.items || []).reduce((s, it) => s + (Number(it.rate || 0) * Number(it.qty || 1)), 0);
}

// ── Pro Mode toggle ───────────────────────────────────────────────────────────
function togglePro() {
  proMode.value = !proMode.value;
  try { localStorage.setItem(PRO_KEY, proMode.value ? "1" : "0"); } catch {}
}

// ── Session memory ────────────────────────────────────────────────────────────
function saveHistory() {
  try {
    const toSave = messages.value.slice(-50).map(m => ({
      role: m.role, content: m.content, action: m.action || null,
      confirm: m.confirm || null, confirmed: m.confirmed || null,
      proAction: m.proAction || null, proData: m.proData || null, proConfirmed: m.proConfirmed || null,
    }));
    localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
  } catch {}
}

function loadHistory() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return false;
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.length) { messages.value = parsed; return true; }
  } catch {}
  return false;
}

function clearChat() {
  messages.value = [];
  localStorage.removeItem(STORAGE_KEY);
  pendingGoal.value = null;
  lastSelectedItem.value = null;
  lastInvoiceCustomer.value = null;
  messages.value.push({ role: "assistant", content: GREETING });
  saveHistory();
}

// ── Streaming typewriter ──────────────────────────────────────────────────────
function streamText(idx, fullText) {
  let i = 0;
  const CHUNK = 5;
  const timer = setInterval(async () => {
    if (i >= fullText.length) {
      clearInterval(timer);
      messages.value[idx].content = fullText;
      saveHistory();
      await scroll();
      return;
    }
    messages.value[idx].content = fullText.slice(0, i + CHUNK);
    i += CHUNK;
    if (i % 30 === 0) await scroll();
  }, 18);
}

// ── Alert handlers ────────────────────────────────────────────────────────────
function dismissAlerts() { showAlerts.value = false; emit("alerts-seen"); }
function handleAlertClick(alert) {
  if (alert.action) handleAction(alert.action, {});
  dismissAlerts();
  emit("close");
}

// ── Invoice creation (existing wizard) ───────────────────────────────────────
async function doConfirmCreate(msg) {
  msg.confirmed = "✓ Creating invoice…";
  dispatch("create_invoice", msg.confirm);
  await nextTick();
  emit("close");
}
function doCancelCreate(msg) {
  msg.confirmed = "Cancelled.";
  messages.value.push({ role: "assistant", content: "No problem — invoice creation cancelled." });
  scroll();
}

// ── Pro Mode confirm/cancel ───────────────────────────────────────────────────
async function doProAction(msg) {
  msg.proConfirmed = "⏳ Processing…";
  try {
    const res = await apiPOST("zoho_books_clone.api.books_data.ai_execute_pro_action", {
      action: msg.proAction,
      data:   JSON.stringify(msg.proData || {}),
    });
    const reply = res?.reply || "Done.";
    msg.proConfirmed = reply;
    const newMsg = { role: "assistant", content: reply, action: res?.action || null };
    messages.value.push(newMsg);
    if (res?.action) handleAction(res.action, res);
    saveHistory();
    await scroll();
    // Resume pending goal after purchase order completion
    if (msg.proAction === "create_purchase_order" && pendingGoal.value) {
      resumePendingGoal();
    }
  } catch (e) {
    msg.proConfirmed = "Failed: " + (e?.message || "unknown error");
    saveHistory();
  }
}

function doCancelPro(msg) {
  msg.proConfirmed = "Cancelled.";
  messages.value.push({ role: "assistant", content: "Action cancelled." });
  saveHistory();
  scroll();
}

// ── Action routing ────────────────────────────────────────────────────────────
function handleAction(action, payload) {
  if (!action) return;
  if (HASH_NAV[action]) { window.location.hash = HASH_NAV[action]; emit("close"); return; }
  dispatch(action, payload);
}

// ── Main send ─────────────────────────────────────────────────────────────────
async function send() {
  const content = draft.value.trim();
  if (!content || busy.value) return;
  draft.value = "";
  messages.value.push({ role: "user", content });
  saveHistory();
  busy.value = true;
  await scroll();
  try {
    const res = await apiPOST("zoho_books_clone.api.books_data.ai_chat", {
      pro_mode: proMode.value ? 1 : 0,
      messages: JSON.stringify(
        messages.value
          .filter(m => m.role === "user" || m.role === "assistant")
          .map(m => ({ role: m.role, content: m.content }))
          .slice(-14)
      ),
    });

    const reply  = res?.reply || res?.message || (typeof res === "string" ? res : "…");
    const action = res?.action || null;
    const msgObj = { role: "assistant", content: "", action };

    if (action === "create_invoice_confirm") {
      msgObj.confirm = { customer: res.customer, items: res.items };
    } else if (PRO_CONFIRM_ACTIONS.has(action)) {
      msgObj.proAction = PRO_CONFIRM_TYPE_MAP[action];
      msgObj.proData   = { ...res };
    } else if (action) {
      handleAction(action, res);
    }

    messages.value.push(msgObj);
    streamText(messages.value.length - 1, reply);

  } catch (e) {
    messages.value.push({ role: "assistant", content: "Sorry — " + (e?.message || "something went wrong.") });
    saveHistory();
  } finally {
    busy.value = false;
    await scroll();
  }
}

function sendQuick(text) { draft.value = text; send(); }

async function scroll() {
  await nextTick();
  if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight;
}

// ── Lazy-load unpaid invoices when that prompt appears ────────────────────────
watch(messages, () => {
  const last = messages.value[messages.value.length - 1];
  if (!last || last.role !== "assistant") return;
  if (isInvoiceSelectPrompt(last, messages.value.length - 1)) loadUnpaidInvoices();
  if (isSupplierPrompt(last, messages.value.length - 1)) loadTopSuppliers();
  if (isPriceListPrompt(last, messages.value.length - 1)) loadAiPriceLists();
}, { deep: false });

onMounted(() => {
  try { proMode.value = localStorage.getItem(PRO_KEY) === "1"; } catch {}
  if (!loadHistory()) {
    messages.value.push({ role: "assistant", content: GREETING });
    saveHistory();
  }
  loadTopCustomers();
  loadTopItems();
  // Suppliers and price lists loaded lazily on first relevant prompt
});

watch(() => props.open, (v) => {
  if (v) { showAlerts.value = true; nextTick(() => { inputEl.value?.focus(); scroll(); }); }
});
</script>
