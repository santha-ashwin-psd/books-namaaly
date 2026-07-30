<template>
  <div class="bt-page">

    <!-- ── Toolbar ── -->
    <div class="bt-toolbar">
      <div class="bt-fld bt-fld-item">
        <label class="bt-fld-lbl">Item</label>
        <SearchableSelect v-model="filters.item" :options="itemOptions" placeholder="All items" @search="fetchItems" />
      </div>
      <div class="bt-fld bt-fld-wh">
        <label class="bt-fld-lbl">Warehouse</label>
        <SearchableSelect v-model="filters.warehouse" :options="warehouseOptions" placeholder="All warehouses" @search="fetchWarehouses" />
      </div>
      <div style="flex:1"></div>
      <button class="bt-btn-ghost" @click="load" :disabled="loading">
        <span v-html="icon('refresh', 13)"></span><span class="bt-btn-label"> Refresh</span>
      </button>
      <button class="bt-btn-ghost" @click="exportCSV" :disabled="!sorted.length">
        <span v-html="icon('download', 13)"></span><span class="bt-btn-label"> Export</span>
      </button>
      <button class="bt-btn-primary" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''" @click="openNew">
        <span v-html="icon('plus', 13)"></span><span class="bt-btn-label"> New Batch</span>
      </button>
    </div>

    <!-- ── Summary strip ── -->
    <SummaryStrip v-if="!loading && list.length" :cards="[
      { label: 'Total Batches', tone: 'accent', value: list.length },
      { label: 'Total Qty', tone: 'info', value: fmtQty(totalQty) },
      { label: 'Expiring Soon (30d)', tone: 'warn', value: expiringCount, valueClass: expiringCount ? 'orange' : '' },
      { label: 'Expired', tone: 'danger', value: expiredCount, valueClass: expiredCount ? 'red' : '' },
    ]" />

    <!-- ── Status pills + search ── -->
    <div v-if="loaded && list.length" class="bt-subbar">
      <div class="bt-filter-pills">
        <button v-for="s in statusTabs" :key="s.key" class="bt-fpill" :class="{ active: statusFilter === s.key }" @click="statusFilter = s.key">
          {{ s.label }} <span class="bt-fpill-count">{{ s.count }}</span>
        </button>
      </div>
      <div class="bt-subbar-right">
        <span class="bt-result">{{ sorted.length }} of {{ list.length }}</span>
        <div class="bt-search-wrap">
          <span v-html="icon('search', 13)" style="color:#94a3b8;flex-shrink:0"></span>
          <input v-model="search" placeholder="Search batch / item / warehouse / supplier…" class="bt-search-input" />
        </div>
      </div>
    </div>

    <!-- ── Table ── -->
    <div class="bt-card">
      <table class="bt-table bt-desktop-table">
        <thead><tr>
          <th @click="sort('batch_no')" class="sortable">Batch No <span v-html="sortArrow('batch_no')"></span></th>
          <th @click="sort('item')" class="sortable">Item <span v-html="sortArrow('item')"></span></th>
          <th>Warehouse</th>
          <th @click="sort('manufacturing_date')" class="sortable">Mfg Date <span v-html="sortArrow('manufacturing_date')"></span></th>
          <th @click="sort('expiry_date')" class="sortable">Expiry Date <span v-html="sortArrow('expiry_date')"></span></th>
          <th @click="sort('batch_qty')" class="sortable ta-r">Qty <span v-html="sortArrow('batch_qty')"></span></th>
          <th>Supplier</th>
          <th>Status</th>
          <th class="ta-r">Actions</th>
        </tr></thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 8" :key="n"><td colspan="9"><div class="b-shimmer" style="height:13px"></div></td></tr>
          </template>
          <template v-else>
            <tr v-for="b in paginated" :key="b.name" class="bt-row" @click="openEdit(b)">
              <td class="font-medium">{{ b.batch_no || b.name }}</td>
              <td class="text-muted">{{ b.item }}</td>
              <td class="text-muted">{{ b.warehouse || '—' }}</td>
              <td class="mono-sm text-muted">{{ fmtDate(b.manufacturing_date) }}</td>
              <td class="mono-sm" :class="expiryClass(b)">{{ fmtDate(b.expiry_date) }}</td>
              <td class="ta-r mono-sm">{{ fmtQty(b.batch_qty) }}</td>
              <td class="text-muted">{{ b.supplier_name || b.supplier || '—' }}</td>
              <td><span class="bt-badge" :class="'bt-badge--' + batchStatus(b)">{{ statusLabel(batchStatus(b)) }}</span></td>
              <td class="ta-r bt-actions" @click.stop>
                <button class="bt-icon-btn" title="Edit" @click="openEdit(b)"><span v-html="icon('edit', 13)"></span></button>
                <button class="bt-icon-btn" :title="b.disabled ? 'Enable' : 'Disable'" @click="toggleDisabled(b)">
                  <span v-html="icon(b.disabled ? 'play' : 'pause', 13)"></span>
                </button>
              </td>
            </tr>
            <tr v-if="!sorted.length"><td colspan="9" class="bt-empty">
              {{ loaded ? (list.length ? 'No batches match this filter' : 'No batches yet — create your first batch to start tracking') : 'Loading…' }}
            </td></tr>
          </template>
        </tbody>
      </table>

      <!-- Mobile cards -->
      <div class="bt-mobile-cards">
        <template v-if="loading">
          <div v-for="n in 5" :key="n" class="bt-mobile-card bt-mc--skeleton">
            <div class="bt-mc-shimmer" style="height:13px;width:55%;margin-bottom:8px"></div>
            <div class="bt-mc-shimmer" style="height:11px;width:40%;margin-bottom:6px"></div>
            <div class="bt-mc-shimmer" style="height:11px;width:65%"></div>
          </div>
        </template>
        <div v-else-if="!sorted.length" class="bt-mc-empty">
          <div style="font-size:32px;margin-bottom:8px">📦</div>
          <div>{{ list.length ? 'No batches match' : 'No batches yet' }}</div>
        </div>
        <template v-else>
          <div v-for="b in paginated" :key="b.name" class="bt-mobile-card" @click="openEdit(b)">
            <div class="bt-mc-top">
              <span class="bt-mc-batch">{{ b.batch_no || b.name }}</span>
              <span class="bt-badge" :class="'bt-badge--' + batchStatus(b)">{{ statusLabel(batchStatus(b)) }}</span>
            </div>
            <div class="bt-mc-mid">{{ b.item }}</div>
            <div class="bt-mc-meta">
              <span>{{ b.warehouse || '—' }}</span>
              <span>Qty: {{ fmtQty(b.batch_qty) }}</span>
            </div>
            <div class="bt-mc-meta">
              <span :class="expiryClass(b)">Exp: {{ fmtDate(b.expiry_date) }}</span>
              <span>{{ b.supplier_name || b.supplier || '—' }}</span>
            </div>
          </div>
        </template>
      </div>

      <!-- Pagination -->
      <div v-if="!loading && sorted.length" class="bt-pagination">
        <span class="bt-pg-info">{{ pageRangeLabel }}</span>
        <div class="bt-pg-controls">
          <select v-model.number="pageSize" class="bt-pg-size">
            <option :value="10">10 / page</option>
            <option :value="20">20 / page</option>
            <option :value="50">50 / page</option>
            <option :value="100">100 / page</option>
          </select>
          <button class="bt-pg-btn" :disabled="page===1" @click="goToPage(1)" title="First page">«</button>
          <button class="bt-pg-btn" :disabled="page===1" @click="goToPage(page-1)" title="Previous page">‹</button>
          <span class="bt-pg-current">Page {{ page }} of {{ totalPages }}</span>
          <button class="bt-pg-btn" :disabled="page===totalPages" @click="goToPage(page+1)" title="Next page">›</button>
          <button class="bt-pg-btn" :disabled="page===totalPages" @click="goToPage(totalPages)" title="Last page">»</button>
        </div>
      </div>
    </div>

    <!-- ── Create / Edit drawer ── -->
    <div v-if="drawerOpen" class="bt-overlay" @click.self="drawerOpen = false"></div>
    <div class="bt-drawer" :class="{ open: drawerOpen }">
      <div class="bt-dheader">
        <button class="bt-dclose" @click="drawerOpen = false"><span v-html="icon('x', 16)"></span></button>
        <div class="bt-dh-top">
          <div class="bt-dh-ico"><span v-html="icon('qr', 20)"></span></div>
          <div>
            <div class="bt-dh-title">{{ editingName ? 'Edit Batch' : 'New Batch' }}</div>
            <div class="bt-dh-sub">{{ editingName ? editingName : 'Track a new inventory batch' }}</div>
          </div>
        </div>
      </div>

      <div class="bt-dbody">
        <div class="bt-form-fld">
          <label class="bt-form-lbl">Batch No</label>
          <input v-model="form.batch_no" class="bt-input" :disabled="!!editingName" placeholder="Leave blank to auto-generate (Item Code-Year-Sequence)" />
        </div>

        <div class="bt-form-fld">
          <label class="bt-form-lbl">Item <span class="req">*</span></label>
          <SearchableSelect v-model="form.item" :options="formItemOptions" placeholder="Select item" :disabled="!!editingName" @search="fetchFormItems" />
        </div>

        <div class="bt-form-row">
          <div class="bt-form-fld">
            <label class="bt-form-lbl">Manufacturing Date</label>
            <input v-model="form.manufacturing_date" type="date" class="bt-input" />
          </div>
          <div class="bt-form-fld">
            <label class="bt-form-lbl">Expiry Date</label>
            <input v-model="form.expiry_date" type="date" class="bt-input" />
          </div>
        </div>

        <div class="bt-form-fld">
          <label class="bt-form-lbl">Warehouse <span class="req">*</span></label>
          <SearchableSelect v-model="form.warehouse" :options="warehouseOptions" placeholder="Select warehouse" :disabled="!!editingName" @search="fetchWarehouses" />
          <span v-if="editingName" class="bt-hint">Locked after creation — like Qty, it's kept in sync by stock entries (receipts/transfers), not edited directly.</span>
        </div>

        <div class="bt-form-fld">
          <label class="bt-form-lbl">Supplier</label>
          <SearchableSelect v-model="form.supplier" :options="supplierOptions" placeholder="Select supplier" @search="fetchSuppliers" />
        </div>

        <div v-if="!editingName" class="bt-form-fld">
          <label class="bt-form-lbl">Add Qty</label>
          <input v-model.number="form.add_qty" type="number" min="0" step="0.001" class="bt-input" placeholder="0" />
          <span class="bt-hint">Optional — posts an opening Material Receipt to this warehouse so stock stays in sync</span>
        </div>

        <div v-if="editingName" class="bt-form-fld">
          <label class="bt-form-lbl">Current Qty</label>
          <div class="bt-readonly-qty">{{ fmtQty(form.batch_qty) }} <span class="bt-hint">— managed automatically via stock entries</span></div>
        </div>

        <div v-if="editingName" class="bt-form-fld bt-form-check">
          <label class="bt-checkbox-lbl">
            <input type="checkbox" v-model="form.disabled" />
            Disabled
          </label>
        </div>
      </div>

      <div class="bt-dfooter">
        <div style="flex:1"></div>
        <button class="bt-btn-ghost" @click="drawerOpen = false">Cancel</button>
        <button class="bt-btn-primary" :disabled="saving || !(editingName ? $canEdit('inventory') : $canCreate('inventory'))" @click="save">
          {{ saving ? 'Saving…' : (editingName ? 'Save Changes' : 'Create Batch') }}
        </button>
      </div>
    </div>

  </div>
</template>
<script setup>
import { ref, reactive, computed, onMounted, watch } from "vue";
import { apiList, apiSave, apiSubmit, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";
import { flt, fmtDate, today } from "../utils/format.js";
import SearchableSelect from "../components/SearchableSelect.vue";
import SummaryStrip from "../components/SummaryStrip.vue";

const { toast } = useToast();

const list = ref([]), loading = ref(false), loaded = ref(false);
const search = ref(""), statusFilter = ref("all");
const sortCol = ref("expiry_date"), sortDir = ref("asc");

const itemOptions = ref([]), warehouseOptions = ref([]);
const formItemOptions = ref([]), supplierOptions = ref([]);

const filters = reactive({ item: "", warehouse: "" });

const drawerOpen = ref(false), editingName = ref(null), saving = ref(false);
const emptyForm = () => ({
  batch_no: "", item: "", warehouse: "", manufacturing_date: "",
  expiry_date: "", supplier: "", disabled: false, batch_qty: 0, add_qty: 0,
});
const form = reactive(emptyForm());

async function load() {
  loading.value = true; loaded.value = true;
  try {
    const rows = await apiList("Batch", {
      fields: ["name", "batch_no", "item", "warehouse", "manufacturing_date", "expiry_date", "batch_qty", "supplier", "disabled"],
      filters: [],
      limit: 100000,
      order: "expiry_date asc",
    });
    list.value = rows;
    // Batch doctype only stores the Supplier link (id) — resolve display names.
    const missing = [...new Set(rows.filter(b => b.supplier).map(b => b.supplier))];
    if (missing.length) {
      const sups = await apiList("Supplier", { fields: ["name", "supplier_name"], filters: [["name", "in", missing]], limit: missing.length }).catch(() => []);
      const nameMap = Object.fromEntries(sups.map(s => [s.name, s.supplier_name || s.name]));
      list.value = rows.map(b => b.supplier ? { ...b, supplier_name: nameMap[b.supplier] || b.supplier } : b);
    }
  } catch (e) {
    toast.error(e.message || "Failed to load batches");
  } finally {
    loading.value = false;
  }
}

function daysUntil(dateStr) {
  if (!dateStr) return null;
  const d = new Date(dateStr); d.setHours(0, 0, 0, 0);
  const now = new Date(); now.setHours(0, 0, 0, 0);
  return Math.round((d - now) / 86400000);
}
function batchStatus(b) {
  if (b.disabled) return "disabled";
  const days = daysUntil(b.expiry_date);
  if (days === null) return "active";
  if (days < 0) return "expired";
  if (days <= 30) return "expiring";
  return "active";
}
function statusLabel(s) {
  return { active: "Active", expiring: "Expiring Soon", expired: "Expired", disabled: "Disabled" }[s] || s;
}
function expiryClass(b) {
  const s = batchStatus(b);
  if (s === "expired") return "red";
  if (s === "expiring") return "orange";
  return "";
}

const filteredRows = computed(() => {
  let r = list.value;
  if (filters.item) r = r.filter(b => b.item === filters.item);
  if (filters.warehouse) r = r.filter(b => b.warehouse === filters.warehouse);
  if (statusFilter.value !== "all") r = r.filter(b => batchStatus(b) === statusFilter.value);
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    r = r.filter(b =>
      (b.batch_no || b.name || "").toLowerCase().includes(q) ||
      (b.item || "").toLowerCase().includes(q) ||
      (b.warehouse || "").toLowerCase().includes(q) ||
      (b.supplier || "").toLowerCase().includes(q) ||
      (b.supplier_name || "").toLowerCase().includes(q)
    );
  }
  return r;
});

const sorted = computed(() => {
  const col = sortCol.value;
  return [...filteredRows.value].sort((a, b) => {
    const av = a[col] ?? "", bv = b[col] ?? "";
    const c = typeof av === "number" ? av - bv : String(av).localeCompare(String(bv));
    return sortDir.value === "asc" ? c : -c;
  });
});
function sort(col) {
  if (sortCol.value === col) sortDir.value = sortDir.value === "asc" ? "desc" : "asc";
  else { sortCol.value = col; sortDir.value = "asc"; }
}
function sortArrow(col) {
  if (sortCol.value !== col) return '<span style="color:#d1d5db">⇅</span>';
  return sortDir.value === "asc" ? "↑" : "↓";
}

// ── Pagination ──────────────────────────────────────────────────────────
const page     = ref(1);
const pageSize = ref(20);
const totalPages = computed(() => Math.max(1, Math.ceil(sorted.value.length / pageSize.value)));
const paginated = computed(() => {
  const start = (page.value - 1) * pageSize.value;
  return sorted.value.slice(start, start + pageSize.value);
});
const pageRangeLabel = computed(() => {
  if (!sorted.value.length) return "0 of 0";
  const start = (page.value - 1) * pageSize.value + 1;
  const end = Math.min(sorted.value.length, page.value * pageSize.value);
  return `${start}–${end} of ${sorted.value.length}`;
});
function goToPage(p) {
  page.value = Math.min(Math.max(1, p), totalPages.value);
}
// Any change that reshuffles/refilters the result set should land back on page 1.
watch([search, statusFilter, () => filters.item, () => filters.warehouse, sortCol, sortDir], () => { page.value = 1; });
watch(totalPages, (tp) => { if (page.value > tp) page.value = tp; });

const statusTabs = computed(() => [
  { key: "all", label: "All", count: filteredRowsForCount.value.length },
  { key: "active", label: "Active", count: list.value.filter(b => batchStatus(b) === "active").length },
  { key: "expiring", label: "Expiring Soon", count: list.value.filter(b => batchStatus(b) === "expiring").length },
  { key: "expired", label: "Expired", count: list.value.filter(b => batchStatus(b) === "expired").length },
  { key: "disabled", label: "Disabled", count: list.value.filter(b => batchStatus(b) === "disabled").length },
]);
// Base counts ignore the status filter itself so tab counts stay stable while switching tabs.
const filteredRowsForCount = computed(() => {
  let r = list.value;
  if (filters.item) r = r.filter(b => b.item === filters.item);
  if (filters.warehouse) r = r.filter(b => b.warehouse === filters.warehouse);
  return r;
});

const totalQty = computed(() => filteredRowsForCount.value.reduce((s, b) => s + flt(b.batch_qty), 0));
const expiringCount = computed(() => list.value.filter(b => batchStatus(b) === "expiring").length);
const expiredCount = computed(() => list.value.filter(b => batchStatus(b) === "expired").length);

function fmtQty(v) { return Number(flt(v)).toLocaleString("en-IN", { maximumFractionDigits: 3 }); }

function openNew() {
  editingName.value = null;
  Object.assign(form, emptyForm());
  drawerOpen.value = true;
}
function openEdit(b) {
  editingName.value = b.name;
  Object.assign(form, {
    batch_no: b.batch_no || b.name || "",
    item: b.item || "",
    warehouse: b.warehouse || "",
    manufacturing_date: b.manufacturing_date || "",
    expiry_date: b.expiry_date || "",
    supplier: b.supplier || "",
    disabled: !!b.disabled,
    batch_qty: flt(b.batch_qty),
  });
  drawerOpen.value = true;
}

async function save() {
  if (!form.item) { toast.error("Item is required"); return; }
  if (!form.warehouse) { toast.error("Warehouse is required — stock can't be tracked without one"); return; }
  const addQty = !editingName.value ? flt(form.add_qty) : 0;
  saving.value = true;
  try {
    const doc = {
      doctype: "Batch",
      batch_no: form.batch_no.trim() || null,
      item: form.item,
      warehouse: form.warehouse || null,
      manufacturing_date: form.manufacturing_date || null,
      expiry_date: form.expiry_date || null,
      supplier: form.supplier || null,
      disabled: form.disabled ? 1 : 0,
    };
    if (editingName.value) doc.name = editingName.value;
    const saved = await apiSave(doc);

    // batch_qty is only ever authoritatively written by Stock Entry's
    // on_submit -> _adjust_batch_qty. If an opening qty was given, post a
    // Material Receipt into the chosen warehouse instead of setting
    // batch_qty directly, so the stock ledger/Bin stay in sync.
    if (addQty > 0) {
      const company = await resolveCompany();
      const se = await apiSave({
        doctype: "Stock Entry",
        company,
        stock_entry_type: "Material Receipt",
        posting_date: today(),
        to_warehouse: form.warehouse,
        remarks: `Opening qty for batch ${saved?.name || form.batch_no.trim()}`,
        items: [{
          doctype: "Stock Entry Detail",
          item_code: form.item,
          qty: addQty,
          t_warehouse: form.warehouse,
          batch_no: saved?.name || form.batch_no.trim(),
        }],
      });
      await apiSubmit("Stock Entry", se.name);
    }

    toast.success(editingName.value ? "Batch updated" : `Batch created${addQty > 0 ? ` with ${fmtQty(addQty)} opening qty` : ""}`);
    drawerOpen.value = false;
    await load();
  } catch (e) {
    toast.error(e.message || "Failed to save batch");
  } finally {
    saving.value = false;
  }
}

async function toggleDisabled(b) {
  try {
    await apiSave({ doctype: "Batch", name: b.name, disabled: b.disabled ? 0 : 1 });
    b.disabled = b.disabled ? 0 : 1;
    toast.success(b.disabled ? "Batch disabled" : "Batch enabled");
  } catch (e) {
    toast.error(e.message || "Failed to update batch");
  }
}

function exportCSV() {
  const rows = sorted.value;
  if (!rows.length) return;
  const esc = v => { const s = v == null ? "" : String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  const lines = [["Batch No", "Item", "Warehouse", "Mfg Date", "Expiry Date", "Qty", "Supplier", "Status"].join(",")];
  for (const b of rows) {
    lines.push([b.batch_no || b.name, b.item || "", b.warehouse || "", fmtDate(b.manufacturing_date), fmtDate(b.expiry_date), flt(b.batch_qty), b.supplier_name || b.supplier || "", statusLabel(batchStatus(b))].map(esc).join(","));
  }
  const blob = new Blob(["\ufeff" + lines.join("\r\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `batches_${today()}.csv`;
  a.click(); URL.revokeObjectURL(url);
  toast.success(`Exported ${rows.length} row(s)`);
}

async function fetchItems(q = "") {
  try {
    const r = await apiList("Item", { fields: ["name", "item_name"], filters: q ? [["name", "like", `%${q}%`]] : [], limit: 20 });
    itemOptions.value = r.map(x => ({ label: x.item_name ? `${x.name} — ${x.item_name}` : x.name, value: x.name }));
  } catch { itemOptions.value = []; }
}
async function fetchFormItems(q = "") {
  try {
    const f = [["has_batch_no", "=", 1]];
    if (q) f.push(["name", "like", `%${q}%`]);
    const r = await apiList("Item", { fields: ["name", "item_name"], filters: f, limit: 20 });
    formItemOptions.value = r.map(x => ({ label: x.item_name ? `${x.name} — ${x.item_name}` : x.name, value: x.name }));
  } catch { formItemOptions.value = []; }
}
async function fetchWarehouses(q = "") {
  try {
    const r = await apiList("Warehouse", { fields: ["name"], filters: [["is_group", "=", 0], ...(q ? [["name", "like", `%${q}%`]] : [])], limit: 20 });
    warehouseOptions.value = r.map(x => ({ label: x.name, value: x.name }));
  } catch { warehouseOptions.value = []; }
}
async function fetchSuppliers(q = "") {
  try {
    // Supplier is autonamed off a naming series (e.g. "SUPP-2026-00001"), not
    // off supplier_name, so apiLinkValues (name-only) surfaced the raw ID as
    // the label. Fetch supplier_name explicitly and use it for the label —
    // same fix already applied to the batch list's supplier column (see load()).
    const f = q ? [["supplier_name", "like", `%${q}%`]] : [];
    const r = await apiList("Supplier", { fields: ["name", "supplier_name"], filters: f, limit: 20 });
    supplierOptions.value = r.map(x => ({ label: x.supplier_name || x.name, value: x.name }));
  } catch { supplierOptions.value = []; }
}

onMounted(() => {
  load();
  fetchItems("");
  fetchFormItems("");
  fetchWarehouses("");
  fetchSuppliers("");
});
</script>
<style scoped>
.bt-page { display: flex; flex-direction: column; gap: 16px; padding: 24px; }

.bt-toolbar { display: flex; align-items: flex-end; gap: 12px; flex-wrap: wrap; background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 14px 16px; }
.bt-fld { display: flex; flex-direction: column; gap: 5px; }
.bt-fld-item { flex: 1 1 220px; max-width: 300px; }
.bt-fld-wh { flex: 1 1 200px; max-width: 260px; }
.bt-fld-lbl { font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: #94a3b8; }

.bt-btn-primary { display: inline-flex; align-items: center; gap: 6px; background: #2563eb; color: #fff; border: none; border-radius: 8px; padding: 9px 16px; font-size: 13px; font-weight: 600; cursor: pointer; white-space: nowrap; }
.bt-btn-primary:hover:not(:disabled) { background: #1d4ed8; }
.bt-btn-primary:disabled { opacity: .5; cursor: not-allowed; }
.bt-btn-ghost { display: inline-flex; align-items: center; gap: 6px; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 9px 14px; font-size: 13px; font-weight: 600; color: #334155; cursor: pointer; white-space: nowrap; }
.bt-btn-ghost:hover:not(:disabled) { background: #f8fafc; border-color: #cbd5e1; }
.bt-btn-ghost:disabled { opacity: .5; cursor: not-allowed; }
.bt-btn-danger-ghost { display: inline-flex; align-items: center; gap: 6px; background: #fff; border: 1px solid #fecaca; color: #dc2626; border-radius: 8px; padding: 9px 14px; font-size: 13px; font-weight: 600; cursor: pointer; }
.bt-btn-danger-ghost:hover { background: #fef2f2; }

.orange { color: #d97706 !important; }
.red { color: #dc2626 !important; }
.green { color: #16a34a !important; }

.bt-subbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.bt-filter-pills { display: inline-flex; align-items: center; gap: 3px; background: #eef2f7; border: 1px solid #e2e8f0; border-radius: 12px; padding: 4px; flex-wrap: wrap; }
.bt-fpill { display: inline-flex; align-items: center; gap: 7px; padding: 7px 14px; border-radius: 9px; font-size: 12.5px; font-weight: 600; border: none; background: transparent; color: #64748b; cursor: pointer; font-family: inherit; }
.bt-fpill:hover:not(.active) { color: #334155; }
.bt-fpill.active { background: #fff; color: #1d4ed8; box-shadow: 0 1px 2px rgba(15,23,42,.08), 0 0 0 1px rgba(37,99,235,.08); }
.bt-fpill-count { display: inline-flex; align-items: center; justify-content: center; min-width: 19px; height: 18px; padding: 0 6px; border-radius: 9px; background: rgba(100,116,139,.16); color: #64748b; font-size: 10.5px; font-weight: 700; line-height: 1; }
.bt-fpill.active .bt-fpill-count { background: #dbeafe; color: #1d4ed8; }
.bt-subbar-right { display: flex; align-items: center; gap: 12px; }
.bt-result { font-size: 12px; color: #94a3b8; font-weight: 600; white-space: nowrap; }
.bt-search-wrap { display: flex; align-items: center; gap: 8px; background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 7px 12px; min-width: 260px; }
.bt-search-wrap:focus-within { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,.1); }
.bt-search-input { border: none; background: transparent; outline: none; font: inherit; font-size: 13px; color: #0f172a; width: 100%; }

.bt-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden; }
.bt-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.bt-table th { background: #f9fafb; border-bottom: 1px solid #e5e7eb; padding: 10px 12px; font-size: 11.5px; font-weight: 600; color: #374151; text-align: left; white-space: nowrap; text-transform: uppercase; }
.bt-table th.sortable { cursor: pointer; user-select: none; }
.bt-table th.sortable:hover { color: #2563eb; }
.ta-r { text-align: right !important; }
.bt-row td { padding: 9px 12px; border-bottom: 1px solid #f3f4f6; cursor: pointer; }
.bt-row:last-child td { border-bottom: none; }
.bt-row:hover td { background: #f9fafb; }
.font-medium { font-weight: 600; }
.mono-sm { font-size: 12.5px; }
.text-muted { color: #6b7280; }
.bt-empty { text-align: center; color: #9ca3af; padding: 48px !important; }

.bt-badge { display: inline-flex; align-items: center; padding: 2px 9px; border-radius: 10px; font-size: 11px; font-weight: 700; white-space: nowrap; }
.bt-badge--active { background: #dcfce7; color: #16a34a; }
.bt-badge--expiring { background: #fef3c7; color: #b45309; }
.bt-badge--expired { background: #fee2e2; color: #dc2626; }
.bt-badge--disabled { background: #f1f5f9; color: #64748b; }

.bt-actions { white-space: nowrap; }
.bt-icon-btn { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: 6px; border: none; background: transparent; color: #64748b; cursor: pointer; margin-left: 2px; }
.bt-icon-btn:hover { background: #eff6ff; color: #2563eb; }
.bt-icon-btn--danger:hover { background: #fef2f2; color: #dc2626; }

/* Drawer */
.bt-overlay { position: fixed; inset: 0; background: rgba(15,23,42,.28); z-index: 40; }
.bt-drawer { position: fixed; top: 0; right: -420px; bottom: 0; width: 420px; max-width: 96vw; background: #fff; border-left: 1px solid #e5e7eb; box-shadow: -8px 0 28px rgba(15,23,42,.12); z-index: 50; display: flex; flex-direction: column; transition: right .24s ease; }
.bt-drawer.open { right: 0; }
.bt-dheader { position: relative; flex-shrink: 0; padding: 20px; border-bottom: 1px solid #e5e7eb; background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); }
.bt-dclose { position: absolute; top: 12px; right: 12px; background: transparent; border: none; cursor: pointer; color: #475569; display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 8px; }
.bt-dclose:hover { background: rgba(255,255,255,.6); color: #0f172a; }
.bt-dh-top { display: flex; align-items: center; gap: 13px; padding-right: 36px; }
.bt-dh-ico { width: 42px; height: 42px; background: #fff; border-radius: 11px; display: flex; align-items: center; justify-content: center; color: #2563eb; flex-shrink: 0; box-shadow: 0 1px 3px rgba(15,23,42,.08); }
.bt-dh-title { font-size: 15px; font-weight: 700; color: #0f172a; }
.bt-dh-sub { font-size: 12px; color: #475569; margin-top: 1px; }
.bt-dbody { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 14px; }
.bt-form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.bt-form-fld { display: flex; flex-direction: column; gap: 5px; }
.bt-form-lbl { font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: #94a3b8; }
.req { color: #dc2626; }
.bt-input { width: 100%; box-sizing: border-box; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 11px; font: inherit; font-size: 13px; outline: none; background: #fff; color: #0f172a; }
.bt-input:focus { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,.1); }
.bt-input:disabled { background: #f8fafc; color: #94a3b8; cursor: not-allowed; }
.bt-readonly-qty { font-size: 14px; font-weight: 700; color: #0f172a; }
.bt-hint { font-size: 11px; font-weight: 500; color: #94a3b8; text-transform: none; letter-spacing: 0; }
.bt-form-check { flex-direction: row; align-items: center; }
.bt-checkbox-lbl { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 600; color: #334155; cursor: pointer; }
.bt-dfooter { display: flex; align-items: center; justify-content: flex-end; padding: 14px 20px; border-top: 1px solid #e5e7eb; flex-shrink: 0; gap: 8px; }

.bt-pagination { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 14px; border-top: 1px solid #e5e7eb; background: #f9fafb; flex-wrap: wrap; }
.bt-pg-info { font-size: 12px; color: #6b7280; }
.bt-pg-controls { display: flex; align-items: center; gap: 6px; }
.bt-pg-size { border: 1px solid #e2e8f0; border-radius: 6px; padding: 5px 8px; font-size: 12px; color: #374151; background: #fff; outline: none; }
.bt-pg-btn { background: #fff; border: 1px solid #e2e8f0; border-radius: 6px; width: 28px; height: 28px; display: inline-flex; align-items: center; justify-content: center; cursor: pointer; color: #374151; font-size: 14px; }
.bt-pg-btn:hover:not(:disabled) { background: #eff6ff; color: #2563eb; border-color: #bfdbfe; }
.bt-pg-btn:disabled { opacity: .4; cursor: not-allowed; }
.bt-pg-current { font-size: 12px; color: #374151; padding: 0 4px; white-space: nowrap; }

.bt-mobile-cards { display: none; }
.bt-desktop-table { display: table; }

@media (max-width: 768px) {
  .bt-drawer { width: 100% !important; right: -100% !important; max-width: 100%; }
  .bt-drawer.open { right: 0 !important; }
  .bt-search-wrap { min-width: 0; flex: 1 1 auto; }
  .bt-subbar { flex-wrap: wrap; }
  .bt-desktop-table { display: none !important; }
  .bt-mobile-cards { display: flex; flex-direction: column; gap: 0; background: #f8fafc; }
  .bt-mobile-card { background: #fff; border-bottom: 1px solid #e5e7eb; padding: 12px 14px; cursor: pointer; }
  .bt-mobile-card:active { background: #f8f9fc; }
  .bt-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; gap: 8px; }
  .bt-mc-batch { font-size: 12.5px; font-weight: 700; color: #2563eb; }
  .bt-mc-mid { font-size: 13.5px; font-weight: 600; color: #1a1d23; margin-bottom: 4px; }
  .bt-mc-meta { display: flex; justify-content: space-between; font-size: 12px; color: #868e96; gap: 8px; }
  .bt-mc--skeleton { pointer-events: none; }
  .bt-mc-shimmer { border-radius: 6px; background: linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size: 200% 100%; animation: bt-mc-sh 1.4s infinite; }
  @keyframes bt-mc-sh { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
  .bt-mc-empty { text-align: center; padding: 32px 16px; color: #868e96; font-size: 13px; }
}
@media (max-width: 480px) {
  .bt-page { padding: 12px; gap: 12px; }
  .bt-toolbar { padding: 12px; gap: 8px; }
  .bt-form-row { grid-template-columns: 1fr; }
  .bt-pagination { justify-content: center; }
  .bt-pg-info { width: 100%; text-align: center; }
}
</style>