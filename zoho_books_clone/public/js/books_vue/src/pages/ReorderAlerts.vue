<template>
  <div class="rm-page">

    <!-- ── Header ─────────────────────────────────────────────────────── -->
    <div class="rm-header">
      <div class="rm-header-left">
        <div class="rm-title">Reorder Management</div>
        <div class="rm-subtitle">Monitor stock levels and configure automatic purchase orders</div>
      </div>
      <button class="rm-btn-ghost" @click="load" :disabled="loading">
        <span v-html="icon('refresh', 14)"></span> Refresh
      </button>
    </div>

    <!-- ── Stats ──────────────────────────────────────────────────────── -->
    <div class="rm-stats" v-if="!loading">
      <div class="rm-stat" :class="{ 'rm-stat--alert': criticalItems.length }">
        <div class="rm-stat-val" :class="criticalItems.length ? 'clr-red' : 'clr-ok'">{{ criticalItems.length }}</div>
        <div class="rm-stat-lbl">Critical (0 stock)</div>
      </div>
      <div class="rm-stat" :class="{ 'rm-stat--warn': lowItems.length }">
        <div class="rm-stat-val" :class="lowItems.length ? 'clr-orange' : 'clr-ok'">{{ lowItems.length }}</div>
        <div class="rm-stat-lbl">Low Stock</div>
      </div>
      <div class="rm-stat">
        <div class="rm-stat-val clr-blue">{{ autoPOItems.length }}</div>
        <div class="rm-stat-lbl">Auto-PO Enabled</div>
      </div>
      <div class="rm-stat">
        <div class="rm-stat-val">{{ allItems.length }}</div>
        <div class="rm-stat-lbl">Total Monitored</div>
      </div>
    </div>

    <!-- ── Body: list + detail ────────────────────────────────────────── -->
    <div class="rm-body" :class="{ 'rm-body--detail-open': selected }">

      <!-- LEFT: item list -->
      <div class="rm-list-panel">

        <!-- filter tabs -->
        <div class="rm-filter-tabs">
          <button v-for="t in TABS" :key="t.k"
            class="rm-ftab" :class="{ 'rm-ftab--active': filterTab === t.k }"
            @click="filterTab = t.k">
            {{ t.l }}
            <span class="rm-ftab-badge" v-if="t.count > 0"
              :class="t.k === 'critical' ? 'badge-red' : t.k === 'below' ? 'badge-orange' : 'badge-blue'">
              {{ t.count }}
            </span>
          </button>
        </div>

        <!-- search -->
        <div class="rm-list-search">
          <span v-html="icon('search', 13)" style="color:#9ca3af;flex-shrink:0"></span>
          <input v-model="search" placeholder="Search items…" class="rm-search-input" />
        </div>

        <!-- skeleton -->
        <div v-if="loading" class="rm-list-items">
          <div v-for="n in 6" :key="n" class="rm-item-row rm-item-row--sk">
            <div class="rm-sk-line" style="width:55%;height:13px;margin-bottom:6px"></div>
            <div class="rm-sk-line" style="width:35%;height:11px"></div>
          </div>
        </div>

        <!-- list -->
        <div v-else class="rm-list-items">
          <div v-if="!filteredItems.length" class="rm-list-empty">
            <div style="font-size:28px;margin-bottom:6px">✅</div>
            <div>No items match this filter</div>
          </div>
          <div v-for="item in filteredItems" :key="item.item_code"
            class="rm-item-row"
            :class="{
              'rm-item-row--selected': selected?.item_code === item.item_code,
              'rm-item-row--critical': flt(item.actual_qty) <= 0,
              'rm-item-row--low':      flt(item.actual_qty) > 0 && item.below_reorder,
            }"
            @click="selectItem(item)">
            <div class="rm-item-top">
              <span class="rm-item-name">{{ item.item_name || item.item_code }}</span>
              <span class="rm-badge"
                :class="flt(item.actual_qty) <= 0 ? 'badge-red' : item.below_reorder ? 'badge-orange' : 'badge-green'">
                {{ flt(item.actual_qty) <= 0 ? 'Critical' : item.below_reorder ? 'Low Stock' : 'OK' }}
              </span>
            </div>
            <div class="rm-item-meta">
              <span class="rm-item-code">{{ item.item_code }}</span>
              <span class="rm-item-stock">
                <span :class="flt(item.actual_qty) <= 0 ? 'clr-red' : item.below_reorder ? 'clr-orange' : ''">
                  {{ fmtQty(item.actual_qty) }}
                </span>
                <span style="color:#d1d5db"> / </span>
                <span style="color:#6b7280">{{ fmtQty(item.reorder_level) }}</span>
              </span>
            </div>
            <div v-if="item.auto_po_enabled" class="rm-item-auto-badge">
              <span v-html="icon('zap', 10)"></span> Auto-PO
            </div>
          </div>
        </div>
      </div>

      <!-- RIGHT: config panel -->
      <div class="rm-detail-panel" :class="{ 'rm-detail-panel--visible': selected }">

        <!-- mobile back -->
        <button class="rm-mobile-back" @click="selected = null">
          <span v-html="icon('arrow-left', 14)"></span> Back to list
        </button>

        <!-- empty state -->
        <div v-if="!selected" class="rm-detail-empty">
          <div class="rm-detail-empty-icon">📦</div>
          <div class="rm-detail-empty-title">Select an item</div>
          <div class="rm-detail-empty-sub">Choose an item from the list to view and configure its reorder settings</div>
        </div>

        <!-- detail content -->
        <template v-else>

          <!-- item header card -->
          <div class="rm-item-header-card">
            <div class="rm-ih-top">
              <div>
                <div class="rm-ih-name">{{ selected.item_name || selected.item_code }}</div>
                <div class="rm-ih-code">{{ selected.item_code }}</div>
              </div>
              <span class="rm-badge rm-badge--lg"
                :class="flt(cfg.actual_qty) <= 0 ? 'badge-red' : cfg.below_reorder ? 'badge-orange' : 'badge-green'">
                {{ flt(cfg.actual_qty) <= 0 ? 'Critical' : cfg.below_reorder ? 'Low Stock' : 'OK' }}
              </span>
            </div>
            <div class="rm-ih-metrics">
              <div class="rm-metric">
                <div class="rm-metric-val" :class="flt(cfg.actual_qty) <= 0 ? 'clr-red' : cfg.below_reorder ? 'clr-orange' : 'clr-ok'">
                  {{ fmtQty(cfg.actual_qty) }}
                </div>
                <div class="rm-metric-lbl">Current Stock</div>
              </div>
              <div class="rm-metric-div"></div>
              <div class="rm-metric">
                <div class="rm-metric-val">{{ fmtQty(cfg.reorder_level) }}</div>
                <div class="rm-metric-lbl">Reorder Level</div>
              </div>
              <div class="rm-metric-div"></div>
              <div class="rm-metric">
                <div class="rm-metric-val" :class="cfg.shortage_qty > 0 ? 'clr-red' : ''">
                  {{ fmtQty(cfg.shortage_qty) }}
                </div>
                <div class="rm-metric-lbl">Shortage</div>
              </div>
            </div>
            <!-- stock bar -->
            <div class="rm-stock-bar-wrap">
              <div class="rm-stock-bar">
                <div class="rm-stock-fill"
                  :class="flt(cfg.actual_qty) <= 0 ? 'fill-red' : cfg.below_reorder ? 'fill-orange' : 'fill-green'"
                  :style="{ width: stockPct + '%' }">
                </div>
                <div class="rm-stock-marker" :style="{ left: reorderPct + '%' }" title="Reorder Level"></div>
              </div>
              <div class="rm-stock-bar-labels">
                <span style="font-size:10px;color:#6b7280">0</span>
                <span style="font-size:10px;color:#6b7280">Reorder level: {{ fmtQty(cfg.reorder_level) }}</span>
              </div>
            </div>
          </div>

          <!-- Auto-PO toggle card -->
          <div class="rm-card">
            <div class="rm-auto-po-row">
              <div class="rm-auto-po-info">
                <div class="rm-auto-po-title">
                  <span v-html="icon('zap', 15)" :style="{ color: cfg.auto_po_enabled ? '#2563eb' : '#9ca3af' }"></span>
                  Auto Purchase Order
                </div>
                <div class="rm-auto-po-desc">
                  {{ cfg.auto_po_enabled
                    ? 'A draft PO is automatically created when stock drops below the reorder level.'
                    : 'Only a notification is sent when stock drops below the reorder level.' }}
                </div>
              </div>
              <button class="rm-toggle" :class="{ 'rm-toggle--on': cfg.auto_po_enabled }"
                :disabled="!$canEdit('inventory')" :title="!$canEdit('inventory') ? 'Read-only access' : ''"
                @click="onToggleAutoPO">
                <div class="rm-toggle-knob"></div>
              </button>
            </div>
            <div v-if="cfg.auto_po_enabled && !cfg.reorder_supplier" class="rm-auto-po-warn">
              <span v-html="icon('alert-triangle', 13)"></span>
              Set a supplier below so auto-PO knows who to order from.
            </div>
          </div>

          <!-- Reorder config card -->
          <div class="rm-card">
            <div class="rm-card-title">Reorder Configuration</div>
            <div class="rm-cfg-grid">
              <!-- Supplier -->
              <div class="rm-cfg-field rm-cfg-full">
                <label class="rm-label">Supplier</label>
                <select class="rm-input" v-model="cfg.reorder_supplier">
                  <option value="">— Select Supplier —</option>
                  <option v-for="s in suppliers" :key="s.name" :value="s.name">{{ s.supplier_name || s.name }}</option>
                </select>
                <div class="rm-field-hint">Who supplies this item for restocking</div>
              </div>
              <!-- Warehouse -->
              <div class="rm-cfg-field rm-cfg-full">
                <label class="rm-label">Receive into Warehouse</label>
                <select class="rm-input" v-model="cfg.reorder_warehouse_override">
                  <option value="">{{ selected.default_warehouse ? `Default (${selected.default_warehouse})` : '— Select Warehouse —' }}</option>
                  <option v-for="w in warehouses" :key="w.name" :value="w.name">{{ w.warehouse_name || w.name }}</option>
                </select>
                <div class="rm-field-hint">Where goods will be received (leave blank to use item's default warehouse)</div>
              </div>
              <!-- Reorder Level -->
              <div class="rm-cfg-field">
                <label class="rm-label">Reorder Level</label>
                <input class="rm-input" type="number" min="0" v-model.number="cfg.reorder_level" placeholder="e.g. 10" />
                <div class="rm-field-hint">Alert triggers when stock falls below this</div>
              </div>
              <!-- Order Qty -->
              <div class="rm-cfg-field">
                <label class="rm-label">Order Quantity</label>
                <input class="rm-input" type="number" min="0" v-model.number="cfg.reorder_qty" placeholder="e.g. 100" />
                <div class="rm-field-hint">Units to order per reorder</div>
              </div>
              <!-- Notes -->
              <div class="rm-cfg-field rm-cfg-full">
                <label class="rm-label">Notes / Terms</label>
                <textarea class="rm-input rm-textarea" v-model="cfg.reorder_notes"
                  placeholder="e.g. always request quality certificate, 30-day credit terms…" rows="3"></textarea>
                <div class="rm-field-hint">Attached to auto-generated purchase orders</div>
              </div>
            </div>

            <!-- action buttons -->
            <div class="rm-cfg-actions">
              <button class="rm-btn-primary" @click="saveConfig" :disabled="saving || !$canEdit('inventory')">
                <span v-if="saving" class="rm-spinner"></span>
                {{ saving ? 'Saving…' : 'Save Config' }}
              </button>
              <button class="rm-btn-secondary" @click="createPONow" :disabled="creatingPO || !$canCreate('bills')" :title="!$canCreate('bills') ? 'Read-only access' : ''">
                <span v-html="icon('plus', 14)"></span>
                {{ creatingPO ? 'Creating…' : 'Create PO Now' }}
              </button>
            </div>
          </div>

        </template>
      </div>
    </div>

    <!-- ── Confirmation Modal ──────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="showConfirmModal" class="rm-modal-overlay" @click.self="showConfirmModal = false">
        <div class="rm-modal">
          <div class="rm-modal-icon">🤖</div>
          <div class="rm-modal-title">Enable Auto Purchase Orders?</div>
          <div class="rm-modal-body">
            <p>You're enabling <b>automatic PO creation</b> for:</p>
            <div class="rm-modal-item-chip">{{ selected?.item_name || selected?.item_code }}</div>
            <p>Whenever stock drops below <b>{{ fmtQty(cfg.reorder_level) }} {{ selected?.stock_uom || 'units' }}</b>, the system will <b>automatically create a draft Purchase Order</b> using:</p>
            <ul class="rm-modal-list">
              <li><b>Supplier:</b> {{ cfg.reorder_supplier || '(not set — set one to avoid blank POs)' }}</li>
              <li><b>Warehouse:</b> {{ cfg.reorder_warehouse_override || selected?.default_warehouse || '(not set)' }}</li>
              <li><b>Order Qty:</b> {{ fmtQty(cfg.reorder_qty) }} {{ selected?.stock_uom || 'units' }}</li>
            </ul>
            <div class="rm-modal-note">
              The PO will be in <b>Draft</b> status — you must submit it manually to place the order.
            </div>
          </div>
          <div class="rm-modal-actions">
            <button class="rm-btn-ghost" @click="showConfirmModal = false">Cancel</button>
            <button class="rm-btn-primary" :disabled="!$canEdit('inventory')" @click="confirmEnableAutoPO">Yes, Enable Auto-PO</button>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { apiGET, apiPOST, apiList, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";
import { flt } from "../utils/format.js";

const { toast } = useToast();

// ── State ──────────────────────────────────────────────────────────────────
const allItems   = ref([]);
const loading    = ref(false);
const selected   = ref(null);   // selected item (read-only reference)
const cfg        = reactive({   // editable config form for selected item
  reorder_supplier: "", reorder_warehouse_override: "",
  reorder_qty: 0, reorder_level: 0, reorder_notes: "",
  auto_po_enabled: 0, actual_qty: 0, below_reorder: false, shortage_qty: 0,
});
const saving         = ref(false);
const creatingPO     = ref(false);
const showConfirmModal = ref(false);
const search         = ref("");
const filterTab      = ref("all");
const suppliers      = ref([]);
const warehouses     = ref([]);

// ── Filter tabs ────────────────────────────────────────────────────────────
const criticalItems = computed(() => allItems.value.filter(i => flt(i.actual_qty) <= 0));
const lowItems      = computed(() => allItems.value.filter(i => flt(i.actual_qty) > 0 && i.below_reorder));
const autoPOItems   = computed(() => allItems.value.filter(i => i.auto_po_enabled));

const TABS = computed(() => [
  { k: "all",      l: "All Monitored",   count: allItems.value.length },
  { k: "below",    l: "Below Reorder",   count: criticalItems.value.length + lowItems.value.length },
  { k: "critical", l: "Critical",        count: criticalItems.value.length },
  { k: "auto",     l: "Auto-PO Active",  count: autoPOItems.value.length },
]);

const filteredItems = computed(() => {
  let base = allItems.value;
  if (filterTab.value === "below")    base = base.filter(i => i.below_reorder);
  if (filterTab.value === "critical") base = base.filter(i => flt(i.actual_qty) <= 0);
  if (filterTab.value === "auto")     base = base.filter(i => i.auto_po_enabled);
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    base = base.filter(i =>
      (i.item_code || "").toLowerCase().includes(q) ||
      (i.item_name || "").toLowerCase().includes(q)
    );
  }
  return base;
});

// ── Stock progress bar ─────────────────────────────────────────────────────
const stockPct = computed(() => {
  const max = Math.max(flt(cfg.actual_qty), flt(cfg.reorder_level) * 1.5, 1);
  return Math.min((flt(cfg.actual_qty) / max) * 100, 100);
});
const reorderPct = computed(() => {
  const max = Math.max(flt(cfg.actual_qty), flt(cfg.reorder_level) * 1.5, 1);
  return Math.min((flt(cfg.reorder_level) / max) * 100, 100);
});

// ── Load ───────────────────────────────────────────────────────────────────
async function load() {
  loading.value = true;
  selected.value = null;
  try {
    const [co, items, sup, wh] = await Promise.all([
      resolveCompany(),
      apiGET("zoho_books_clone.api.inventory.get_reorder_dashboard"),
      apiList("Supplier", { fields: ["name", "supplier_name"], limit: 500, order_by: "supplier_name asc" }),
      apiList("Warehouse", { fields: ["name", "warehouse_name"], filters: [["is_group", "=", 0], ["disabled", "=", 0]], limit: 500 }),
    ]);
    allItems.value  = items || [];
    suppliers.value = sup  || [];
    warehouses.value= wh   || [];
  } catch (e) {
    toast(e.message || "Failed to load reorder data", "error");
  } finally {
    loading.value = false;
  }
}

function selectItem(item) {
  selected.value = item;
  Object.assign(cfg, {
    reorder_supplier:           item.reorder_supplier           || "",
    reorder_warehouse_override: item.reorder_warehouse_override || "",
    reorder_qty:                flt(item.reorder_qty),
    reorder_level:              flt(item.reorder_level),
    reorder_notes:              item.reorder_notes              || "",
    auto_po_enabled:            item.auto_po_enabled            || 0,
    actual_qty:                 flt(item.actual_qty),
    below_reorder:              item.below_reorder,
    shortage_qty:               flt(item.shortage_qty),
  });
}

// ── Save config ─────────────────────────────────────────────────────────────
async function saveConfig() {
  if (!selected.value) return;
  saving.value = true;
  try {
    await apiPOST("zoho_books_clone.api.inventory.save_item_reorder_config", {
      item_code:          selected.value.item_code,
      supplier:           cfg.reorder_supplier,
      warehouse_override: cfg.reorder_warehouse_override,
      reorder_qty:        cfg.reorder_qty,
      reorder_level:      cfg.reorder_level,
      auto_po_enabled:    cfg.auto_po_enabled,
      notes:              cfg.reorder_notes,
    });
    // Also update reorder_level on the item (uses frappe.db.set_value via save_item_reorder_config extension)
    // Patch local list so stats update immediately
    const idx = allItems.value.findIndex(i => i.item_code === selected.value.item_code);
    if (idx >= 0) {
      const updated = {
        reorder_supplier:           cfg.reorder_supplier,
        reorder_warehouse_override: cfg.reorder_warehouse_override,
        reorder_qty:                cfg.reorder_qty,
        reorder_level:              cfg.reorder_level,
        reorder_notes:              cfg.reorder_notes,
        auto_po_enabled:            cfg.auto_po_enabled,
      };
      updated.below_reorder = allItems.value[idx].actual_qty < updated.reorder_level;
      updated.shortage_qty  = Math.max(updated.reorder_level - allItems.value[idx].actual_qty, 0);
      Object.assign(allItems.value[idx], updated);
      selected.value       = allItems.value[idx];
      cfg.below_reorder    = updated.below_reorder;
      cfg.shortage_qty     = updated.shortage_qty;
    }
    toast("Reorder config saved", "success");
  } catch (e) {
    toast(e.message || "Save failed", "error");
  } finally {
    saving.value = false;
  }
}

// ── Auto-PO toggle ──────────────────────────────────────────────────────────
function onToggleAutoPO() {
  if (!cfg.auto_po_enabled) {
    // Turning ON → show confirmation first
    showConfirmModal.value = true;
  } else {
    // Turning OFF → immediate, no confirm needed
    cfg.auto_po_enabled = 0;
  }
}

function confirmEnableAutoPO() {
  cfg.auto_po_enabled = 1;
  showConfirmModal.value = false;
}

// ── Create PO now ───────────────────────────────────────────────────────────
async function createPONow() {
  if (!selected.value) return;
  creatingPO.value = true;
  try {
    const res = await apiPOST("zoho_books_clone.api.inventory.create_po_from_reorder", {
      items: JSON.stringify([{
        item_code: selected.value.item_code,
        qty:       cfg.reorder_qty || selected.value.reorder_qty,
        warehouse: cfg.reorder_warehouse_override || selected.value.default_warehouse,
      }]),
      supplier: cfg.reorder_supplier,
    });
    toast(`Purchase Order ${res.name} created as draft`, "success");
  } catch (e) {
    toast(e.message || "Failed to create PO", "error");
  } finally {
    creatingPO.value = false;
  }
}

function fmtQty(v) {
  return Number(flt(v)).toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

onMounted(load);
</script>

<style scoped>
/* ── Page ── */
.rm-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 24px;
  min-height: 100%;
  background: #f0f2f5;
}

/* ── Header ── */
.rm-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.rm-title {
  font-size: 20px;
  font-weight: 800;
  color: #1a1d23;
  letter-spacing: -.3px;
}
.rm-subtitle {
  font-size: 13px;
  color: #6b7280;
  margin-top: 2px;
}

/* ── Stats ── */
.rm-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.rm-stat {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px 18px;
  transition: border-color .15s;
}
.rm-stat--alert { border-color: #fca5a5; background: #fff5f5; }
.rm-stat--warn  { border-color: #fcd34d; background: #fffbeb; }
.rm-stat-val { font-size: 22px; font-weight: 800; }
.rm-stat-lbl { font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: .05em; margin-top: 2px; }
.clr-red    { color: #dc2626; }
.clr-orange { color: #ea580c; }
.clr-blue   { color: #2563eb; }
.clr-ok     { color: #16a34a; }

/* ── Body split ── */
.rm-body {
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 16px;
  align-items: start;
}

/* ── LIST PANEL ── */
.rm-list-panel {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.rm-filter-tabs {
  display: flex;
  border-bottom: 1px solid #e5e7eb;
  overflow-x: auto;
  scrollbar-width: none;
}
.rm-filter-tabs::-webkit-scrollbar { display: none; }

.rm-ftab {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 10px 14px;
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  background: none;
  border: none;
  cursor: pointer;
  white-space: nowrap;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}
.rm-ftab:hover { color: #374151; }
.rm-ftab--active { color: #2563eb; border-bottom-color: #2563eb; }

.rm-ftab-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 1px 6px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 700;
}
.badge-red    { background: #fee2e2; color: #dc2626; }
.badge-orange { background: #fff7ed; color: #ea580c; }
.badge-green  { background: #dcfce7; color: #16a34a; }
.badge-blue   { background: #eff6ff; color: #2563eb; }

.rm-list-search {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-bottom: 1px solid #f3f4f6;
}
.rm-search-input {
  border: none;
  background: transparent;
  outline: none;
  font: inherit;
  font-size: 13px;
  color: #111827;
  width: 100%;
}

.rm-list-items {
  overflow-y: auto;
  max-height: calc(100vh - 320px);
  min-height: 200px;
}
.rm-list-empty {
  text-align: center;
  padding: 48px 16px;
  color: #9ca3af;
  font-size: 13px;
}

.rm-item-row {
  padding: 12px 16px;
  border-bottom: 1px solid #f3f4f6;
  cursor: pointer;
  transition: background .1s;
}
.rm-item-row:last-child { border-bottom: none; }
.rm-item-row:hover { background: #f9fafb; }
.rm-item-row--selected { background: #eff6ff !important; border-left: 3px solid #2563eb; }
.rm-item-row--critical { background: #fff5f5; }
.rm-item-row--low { background: #fffbeb; }

.rm-item-row--sk { pointer-events: none; background: #fff; }
.rm-sk-line {
  border-radius: 4px;
  background: linear-gradient(90deg, #f3f4f6 25%, #e5e7eb 50%, #f3f4f6 75%);
  background-size: 200% 100%;
  animation: rm-sh 1.4s infinite;
}
@keyframes rm-sh { 0%{background-position:200% 0} 100%{background-position:-200% 0} }

.rm-item-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}
.rm-item-name  { font-size: 13px; font-weight: 600; color: #1a1d23; }
.rm-item-meta  { display: flex; justify-content: space-between; align-items: center; }
.rm-item-code  { font-size: 11px; color: #9ca3af; }
.rm-item-stock { font-size: 12px; font-weight: 600; }
.rm-item-auto-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  margin-top: 5px;
  padding: 1px 7px;
  background: #eff6ff;
  color: #2563eb;
  border-radius: 8px;
  font-size: 10px;
  font-weight: 700;
}
.rm-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 700;
}
.rm-badge--lg { padding: 4px 12px; font-size: 12px; }

/* ── DETAIL PANEL ── */
.rm-detail-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.rm-mobile-back { display: none; }

.rm-detail-empty {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  text-align: center;
  padding: 64px 32px;
  color: #9ca3af;
}
.rm-detail-empty-icon  { font-size: 40px; margin-bottom: 12px; }
.rm-detail-empty-title { font-size: 15px; font-weight: 700; color: #374151; margin-bottom: 6px; }
.rm-detail-empty-sub   { font-size: 13px; color: #9ca3af; max-width: 260px; margin: 0 auto; }

/* ── Item header card ── */
.rm-item-header-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 20px 24px;
}
.rm-ih-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}
.rm-ih-name { font-size: 17px; font-weight: 800; color: #1a1d23; }
.rm-ih-code { font-size: 11px; color: #9ca3af; margin-top: 2px; }

.rm-ih-metrics {
  display: flex;
  align-items: center;
  gap: 0;
  margin-bottom: 16px;
  background: #f8fafc;
  border-radius: 10px;
  padding: 12px 0;
}
.rm-metric { flex: 1; text-align: center; }
.rm-metric-val { font-size: 20px; font-weight: 800; }
.rm-metric-lbl { font-size: 10.5px; color: #6b7280; text-transform: uppercase; letter-spacing: .04em; margin-top: 2px; }
.rm-metric-div { width: 1px; background: #e5e7eb; height: 40px; }

/* Stock bar */
.rm-stock-bar-wrap { }
.rm-stock-bar {
  position: relative;
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: visible;
}
.rm-stock-fill {
  height: 100%;
  border-radius: 4px;
  transition: width .4s ease;
}
.fill-red    { background: #dc2626; }
.fill-orange { background: #ea580c; }
.fill-green  { background: #16a34a; }
.rm-stock-marker {
  position: absolute;
  top: -4px;
  width: 2px;
  height: 16px;
  background: #374151;
  border-radius: 1px;
  transform: translateX(-50%);
}
.rm-stock-bar-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
}

/* ── Generic card ── */
.rm-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 20px 24px;
}
.rm-card-title {
  font-size: 13px;
  font-weight: 700;
  color: #1a1d23;
  margin-bottom: 16px;
}

/* ── Auto-PO toggle row ── */
.rm-auto-po-row {
  display: flex;
  align-items: center;
  gap: 16px;
  justify-content: space-between;
}
.rm-auto-po-info { flex: 1; }
.rm-auto-po-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 700;
  color: #1a1d23;
  margin-bottom: 4px;
}
.rm-auto-po-desc { font-size: 12px; color: #6b7280; line-height: 1.5; }
.rm-auto-po-warn {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
  padding: 8px 12px;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: 8px;
  font-size: 12px;
  color: #92400e;
}

.rm-toggle {
  flex-shrink: 0;
  width: 44px;
  height: 24px;
  border-radius: 12px;
  position: relative;
  background: #d1d5db;
  border: none;
  cursor: pointer;
  transition: background .2s;
}
.rm-toggle--on { background: #2563eb; }
.rm-toggle-knob {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #fff;
  position: absolute;
  top: 2px;
  left: 2px;
  transition: left .2s;
  box-shadow: 0 1px 3px rgba(0,0,0,.2);
}
.rm-toggle--on .rm-toggle-knob { left: 22px; }

/* ── Config form ── */
.rm-cfg-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 20px;
}
.rm-cfg-full { grid-column: 1 / -1; }
.rm-cfg-field { display: flex; flex-direction: column; gap: 4px; }

.rm-label { font-size: 12px; font-weight: 600; color: #374151; }
.rm-input {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px 12px;
  font: inherit;
  font-size: 13px;
  color: #1a1d23;
  background: #fff;
  outline: none;
  transition: border-color .15s;
  width: 100%;
  box-sizing: border-box;
}
.rm-input:focus { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,.08); }
.rm-textarea { resize: vertical; }
.rm-field-hint { font-size: 11px; color: #9ca3af; }

/* ── Action buttons ── */
.rm-cfg-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.rm-btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 9px 18px;
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background .15s;
}
.rm-btn-primary:hover:not(:disabled) { background: #1d4ed8; }
.rm-btn-primary:disabled { opacity: .5; cursor: not-allowed; }
.rm-btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #fff;
  color: #374151;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 9px 18px;
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background .15s, border-color .15s;
}
.rm-btn-secondary:hover:not(:disabled) { background: #f9fafb; border-color: #9ca3af; }
.rm-btn-secondary:disabled { opacity: .5; cursor: not-allowed; }
.rm-btn-ghost {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 8px 14px;
  font: inherit;
  font-size: 13px;
  color: #374151;
  cursor: pointer;
}
.rm-btn-ghost:hover { background: #f9fafb; }

.rm-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255,255,255,.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin .6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Confirmation Modal ── */
.rm-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 16px;
}
.rm-modal {
  background: #fff;
  border-radius: 16px;
  padding: 28px;
  max-width: 440px;
  width: 100%;
  box-shadow: 0 20px 60px rgba(0,0,0,.2);
  animation: modal-in .2s ease;
}
@keyframes modal-in { from { transform: scale(.95); opacity:0 } to { transform: scale(1); opacity:1 } }
.rm-modal-icon  { font-size: 32px; margin-bottom: 8px; }
.rm-modal-title { font-size: 17px; font-weight: 800; color: #1a1d23; margin-bottom: 14px; }
.rm-modal-body  { font-size: 13px; color: #374151; line-height: 1.6; }
.rm-modal-body p { margin: 0 0 10px; }
.rm-modal-item-chip {
  display: inline-block;
  padding: 4px 12px;
  background: #eff6ff;
  color: #2563eb;
  border-radius: 20px;
  font-weight: 700;
  font-size: 13px;
  margin-bottom: 12px;
}
.rm-modal-list {
  margin: 0 0 14px;
  padding-left: 18px;
}
.rm-modal-list li { margin-bottom: 4px; }
.rm-modal-note {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 12px;
  color: #166534;
}
.rm-modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 20px;
}

/* ── Responsive ── */
@media (max-width: 960px) {
  .rm-stats { grid-template-columns: repeat(2, 1fr); }
  .rm-body  { grid-template-columns: 1fr; }

  /* On mobile, detail panel slides over the list */
  .rm-detail-panel {
    display: none;
  }
  .rm-body--detail-open .rm-detail-panel {
    display: flex;
    position: fixed;
    inset: 0;
    background: #f0f2f5;
    z-index: 50;
    overflow-y: auto;
    padding: 16px;
    animation: slide-in .2s ease;
  }
  @keyframes slide-in { from { transform: translateX(100%) } to { transform: translateX(0) } }
  .rm-mobile-back {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: none;
    border: none;
    font: inherit;
    font-size: 13px;
    font-weight: 600;
    color: #2563eb;
    cursor: pointer;
    padding: 0;
    margin-bottom: 12px;
  }
  .rm-cfg-grid { grid-template-columns: 1fr; }
  .rm-cfg-full { grid-column: auto; }
}
@media (max-width: 600px) {
  .rm-page   { padding: 12px; gap: 12px; }
  .rm-stats  { grid-template-columns: 1fr 1fr; }
  .rm-title  { font-size: 17px; }
  .rm-cfg-actions { flex-direction: column; }
  .rm-btn-primary, .rm-btn-secondary { justify-content: center; }
}
</style>