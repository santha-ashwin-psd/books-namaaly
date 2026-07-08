<template>
  <div class="ob-page">

    <!-- ── Summary strip ── -->
    <div class="ob-kpi-strip">
      <div class="ob-kpi">
        <div class="ob-kpi-ico" style="background:#eff6ff;color:#2563eb"><span v-html="icon('opening',16)"></span></div>
        <div><div class="ob-kpi-lbl">Opening Entries</div><div class="ob-kpi-val">{{ kpi.total }}</div></div>
      </div>
      <div class="ob-kpi">
        <div class="ob-kpi-ico" style="background:#f0fdf4;color:#16a34a"><span v-html="icon('box',16)"></span></div>
        <div><div class="ob-kpi-lbl">Items Set</div><div class="ob-kpi-val" style="color:#16a34a">{{ kpi.itemCount }}</div></div>
      </div>
      <div class="ob-kpi">
        <div class="ob-kpi-ico" style="background:#fffbeb;color:#d97706"><span v-html="icon('hash',16)"></span></div>
        <div><div class="ob-kpi-lbl">Batches Created</div><div class="ob-kpi-val" style="color:#d97706">{{ kpi.batchCount }}</div></div>
      </div>
      <div class="ob-kpi ob-kpi-value">
        <div class="ob-kpi-ico" style="background:#faf5ff;color:#7c3aed"><span v-html="icon('chart',16)"></span></div>
        <div><div class="ob-kpi-lbl">Opening Value</div><div class="ob-kpi-val" style="color:#7c3aed;font-size:13px">{{ fmtCur(kpi.value) }}</div></div>
      </div>
    </div>

    <!-- ── Action bar ── -->
    <div class="ob-actions">
      <div class="ob-search-wrap">
        <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
        <input v-model="search" placeholder="Search entry #, item, warehouse, batch…" class="ob-search-input" />
      </div>
      <div style="display:flex;gap:8px;">
        <button class="ob-btn-ghost" @click="load"><span v-html="icon('refresh',14)"></span></button>
        <button class="ob-btn-primary" @click="openNew"><span v-html="icon('plus',13)"></span> New Opening Stock Entry</button>
      </div>
    </div>

    <p class="ob-hint">
      Use this to set the starting stock-on-hand for each item/warehouse before go-live.
      Items flagged <em>Has Batch No</em> require a Batch No, manufacturing date, and
      expiry date per line — the batch record is created automatically when you save.
    </p>

    <!-- ── Table ── -->
    <div class="ob-card">
      <table class="ob-table ob-desktop-table">
        <thead><tr>
          <th>Entry #</th>
          <th>Date</th>
          <th>Warehouse(s)</th>
          <th class="ta-r">Items</th>
          <th class="ta-r">Batched Lines</th>
          <th class="ta-r">Value</th>
          <th>Status</th>
          <th style="width:44px"></th>
        </tr></thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 6" :key="n"><td colspan="8"><div class="ob-shimmer"></div></td></tr>
          </template>
          <template v-else>
            <tr v-for="e in paginated" :key="e.name" class="ob-row" @click="openView(e)">
              <td><span class="ob-num">{{ e.name }}</span></td>
              <td class="mono-sm text-muted">{{ fmtDate(e.posting_date) }}</td>
              <td><span class="ob-wh-tag" v-if="e.to_warehouse">{{ shortWH(e.to_warehouse) }}</span><span v-else class="text-muted">Multiple</span></td>
              <td class="ta-r">{{ e._itemCount ?? '—' }}</td>
              <td class="ta-r">{{ e._batchCount ?? '—' }}</td>
              <td class="ta-r" style="font-weight:600">{{ fmtCur(e.total_incoming_value) }}</td>
              <td><span class="ob-badge" :class="statusClass(e)">{{ statusLabel(e) }}</span></td>
              <td @click.stop style="display:flex;gap:4px">
                <button class="ob-act-btn" @click="openView(e)" title="View"><span v-html="icon('eye',13)"></span></button>
                <button v-if="e.docstatus===0" class="ob-act-btn" @click="openEdit(e)" title="Edit"><span v-html="icon('edit',13)"></span></button>
              </td>
            </tr>
            <tr v-if="!filtered.length">
              <td colspan="8" class="ob-empty">
                <div style="font-size:32px;margin-bottom:8px">🗃️</div>
                <div style="font-weight:600;margin-bottom:4px">No opening stock entries yet</div>
                <div style="font-size:13px;color:#9ca3af;margin-bottom:12px">Set starting balances and batches before go-live</div>
                <button class="ob-btn-primary" @click="openNew"><span v-html="icon('plus',13)"></span> New Opening Stock Entry</button>
              </td>
            </tr>
          </template>
        </tbody>
      </table>

      <!-- Mobile cards -->
      <div class="ob-mobile-cards">
        <template v-if="loading">
          <div v-for="n in 4" :key="n" class="ob-mobile-card ob-mc--skeleton">
            <div class="ob-mc-shimmer" style="height:13px;width:55%;margin-bottom:8px"></div>
            <div class="ob-mc-shimmer" style="height:11px;width:40%"></div>
          </div>
        </template>
        <div v-else-if="!filtered.length" class="ob-mc-empty">No opening stock entries yet</div>
        <template v-else>
          <div v-for="e in paginated" :key="e.name" class="ob-mobile-card" @click="openView(e)">
            <div class="ob-mc-top">
              <span class="ob-mc-docno">{{ e.name }}</span>
              <span style="display:flex;gap:6px;align-items:center">
                <span class="ob-badge" :class="statusClass(e)">{{ statusLabel(e) }}</span>
                <button v-if="e.docstatus===0" class="ob-act-btn" @click.stop="openEdit(e)" title="Edit"><span v-html="icon('edit',12)"></span></button>
              </span>
            </div>
            <div class="ob-mc-meta">
              <span>{{ fmtDate(e.posting_date) }}</span>
              <span style="font-weight:700">{{ fmtCur(e.total_incoming_value) }}</span>
            </div>
          </div>
        </template>
      </div>

      <!-- Pagination -->
      <div v-if="!loading && filtered.length" class="ob-pagination">
        <span class="ob-pg-info">{{ pageRangeLabel }}</span>
        <div class="ob-pg-controls">
          <select v-model.number="pageSize" class="ob-pg-size">
            <option :value="10">10 / page</option>
            <option :value="20">20 / page</option>
            <option :value="50">50 / page</option>
            <option :value="100">100 / page</option>
          </select>
          <button class="ob-pg-btn" :disabled="page===1" @click="goToPage(1)" title="First page">«</button>
          <button class="ob-pg-btn" :disabled="page===1" @click="goToPage(page-1)" title="Previous page">‹</button>
          <span class="ob-pg-current">Page {{ page }} of {{ totalPages }}</span>
          <button class="ob-pg-btn" :disabled="page===totalPages" @click="goToPage(page+1)" title="Next page">›</button>
          <button class="ob-pg-btn" :disabled="page===totalPages" @click="goToPage(totalPages)" title="Last page">»</button>
        </div>
      </div>
    </div>

    <!-- ── Create Drawer ── -->
    <div v-if="drawerOpen" class="ob-overlay" @click.self="drawerOpen=false"></div>
    <div class="ob-drawer" :class="{open:drawerOpen}">
      <div class="ob-dheader">
        <button class="ob-dclose ob-dclose-abs" @click="drawerOpen=false"><span v-html="icon('x',16)"></span></button>
        <div class="ob-dh-top">
          <div class="ob-dh-ico"><span v-html="icon('opening',20)" style="color:#fff"></span></div>
          <div>
            <div class="ob-dh-title" style="color:#fff">{{ editingName ? 'Edit Opening Stock Entry — ' + editingName : 'Opening Stock & Batch Entry' }}</div>
            <div class="ob-dh-sub" style="color:rgba(255,255,255,.75)">{{ editingName ? 'Editing draft entry' : 'Set starting balances and batch numbers' }}</div>
          </div>
        </div>
      </div>
      <div class="ob-dbody">
        <div class="ob-fields-grid">
          <div class="ob-field">
            <label class="ob-label">Posting Date <span class="req">*</span></label>
            <input v-model="form.posting_date" type="date" class="ob-input" />
          </div>
          <div class="ob-field">
            <label class="ob-label">Default Warehouse</label>
            <SearchableSelect v-model="form.to_warehouse" :options="warehouses" placeholder="Applies to lines left blank…" @search="fetchWarehouses" />
          </div>
          <div class="ob-field" style="grid-column:1/-1">
            <label class="ob-label">Remarks</label>
            <input v-model="form.remarks" class="ob-input" placeholder="e.g. Opening balance as of go-live date"/>
          </div>
        </div>

        <div class="ob-section-title" style="margin-top:4px">Items & Batches</div>

        <!-- Desktop line items -->
        <div class="ob-items-table ob-add-items-desktop">
          <div v-for="(line, idx) in lines" :key="line.id" class="ob-line-card">
            <div class="ob-line-row">
              <div class="ob-line-field" style="flex:2.2">
                <label class="ob-label">Item</label>
                <SearchableSelect v-model="line.item_code" :options="items" placeholder="Item…" @search="fetchItems" @select="opt=>onItemSelect(line,opt)" />
              </div>
              <div class="ob-line-field" style="flex:1.6">
                <label class="ob-label">Warehouse</label>
                <SearchableSelect v-model="line.t_warehouse" :options="warehouses" placeholder="Warehouse…" @search="fetchWarehouses" :compact="true"/>
              </div>
              <div class="ob-line-field" style="flex:.9">
                <label class="ob-label">Qty</label>
                <input v-model.number="line.qty" type="number" min="0" step="0.001" class="ob-input ta-r" />
              </div>
              <div class="ob-line-field" style="flex:1">
                <label class="ob-label">Rate (₹)</label>
                <input v-model.number="line.basic_rate" type="number" min="0" step="0.01" class="ob-input ta-r" />
              </div>
              <button @click="removeLine(line.id)" class="ob-rm-line" style="margin-top:20px" aria-label="Remove item"><span v-html="icon('x',12)"></span></button>
            </div>

            <div v-if="line.has_batch_no" class="ob-line-row ob-line-row-batch">
              <div class="ob-line-field" style="flex:1.6">
                <label class="ob-label">Batch No <span class="req">*</span></label>
                <SearchableSelect
                  v-model="line.batch_no"
                  :options="line.batchOptions"
                  placeholder="Select existing batch or type to create new"
                  createable
                  @search="q=>fetchBatches(line,q)"
                  @select="opt=>onBatchSelect(line,opt)"
                  @create="val=>onBatchCreate(line,val)"
                  :compact="true"
                />
              </div>
              <div class="ob-line-field" style="flex:1">
                <label class="ob-label">Mfg date</label>
                <input v-model="line.manufacturing_date" type="date" class="ob-input" />
              </div>
              <div class="ob-line-field" style="flex:1">
                <label class="ob-label">Expiry date</label>
                <input v-model="line.expiry_date" type="date" class="ob-input" />
              </div>
              <div class="ob-line-spacer"></div>
            </div>
          </div>

          <div class="ob-items-total" v-if="lines.length">
            <div class="ob-items-total-label">Total opening value</div>
            <div class="ob-items-total-val">{{ fmtCur(lineTotal) }}</div>
          </div>
          <button class="ob-add-line" @click="addLine"><span v-html="icon('plus',12)"></span> Add item</button>
        </div>

        <!-- Mobile cards -->
        <div class="ob-add-items-mobile">
          <div v-for="(line, idx) in lines" :key="line.id" class="ob-aic">
            <div class="ob-aic-header">
              <span class="ob-aic-num">Item {{ idx + 1 }}</span>
              <button @click="removeLine(line.id)" class="ob-rm-line ob-rm-line-sm"><span v-html="icon('x',12)"></span></button>
            </div>
            <div class="ob-aic-field">
              <label class="ob-label">Item</label>
              <SearchableSelect v-model="line.item_code" :options="items" placeholder="Item…" @search="fetchItems" @select="opt=>onItemSelect(line,opt)" />
            </div>
            <div class="ob-aic-field">
              <label class="ob-label">Warehouse</label>
              <SearchableSelect v-model="line.t_warehouse" :options="warehouses" placeholder="Warehouse…" @search="fetchWarehouses" />
            </div>
            <div style="display:flex;gap:8px">
              <div class="ob-aic-field" style="flex:1">
                <label class="ob-label">Qty</label>
                <input v-model.number="line.qty" type="number" min="0" step="0.001" class="ob-input ta-r" />
              </div>
              <div class="ob-aic-field" style="flex:1">
                <label class="ob-label">Rate (₹)</label>
                <input v-model.number="line.basic_rate" type="number" min="0" step="0.01" class="ob-input ta-r" />
              </div>
            </div>
            <template v-if="line.has_batch_no">
              <div class="ob-aic-field">
                <label class="ob-label">Batch No <span class="req">*</span></label>
                <SearchableSelect
                  v-model="line.batch_no"
                  :options="line.batchOptions"
                  placeholder="Select existing or type to create new"
                  createable
                  @search="q=>fetchBatches(line,q)"
                  @select="opt=>onBatchSelect(line,opt)"
                  @create="val=>onBatchCreate(line,val)"
                />
              </div>
              <div style="display:flex;gap:8px">
                <div class="ob-aic-field" style="flex:1">
                  <label class="ob-label">Mfg Date</label>
                  <input v-model="line.manufacturing_date" type="date" class="ob-input" />
                </div>
                <div class="ob-aic-field" style="flex:1">
                  <label class="ob-label">Expiry Date</label>
                  <input v-model="line.expiry_date" type="date" class="ob-input" />
                </div>
              </div>
            </template>
            <div class="ob-aic-amount">{{ fmtCur(flt(line.qty)*flt(line.basic_rate)) }}</div>
          </div>
        </div>
      </div>
      <div class="ob-dfooter">
        <button class="ob-btn-cancel" @click="drawerOpen=false">Cancel</button>
        <button class="ob-btn-save" :disabled="drawerSaving" @click="saveEntry(0)"><span v-html="icon('save',13)"></span> {{ drawerSaving?'Saving…':'Save Draft' }}</button>
        <button class="ob-btn-primary" :disabled="drawerSaving" @click="saveEntry(1)"><span v-html="icon('check',13)"></span> {{ drawerSaving?'Submitting…':'Submit' }}</button>
      </div>
    </div>

    <!-- ── View Panel ── -->
    <div v-if="viewOpen" class="ob-overlay" @click.self="viewOpen=false"></div>
    <div class="ob-drawer ob-view-drawer" :class="{open:viewOpen}">
      <template v-if="viewDoc">
        <div class="ob-dheader">
          <button class="ob-dclose ob-dclose-abs" @click="viewOpen=false"><span v-html="icon('x',16)"></span></button>
          <div class="ob-dh-top">
            <div class="ob-dh-ico" style="background:rgba(255,255,255,.2)"><span v-html="icon('opening',20)" style="color:#fff"></span></div>
            <div>
              <div class="ob-dh-title" style="color:#fff">{{ viewDoc.name }}</div>
              <div class="ob-dh-sub" style="color:rgba(255,255,255,.8)">Opening Stock · {{ fmtDate(viewDoc.posting_date) }}</div>
            </div>
            <span class="ob-badge" :class="statusClass(viewDoc)" style="margin-left:auto;flex-shrink:0">{{ statusLabel(viewDoc) }}</span>
          </div>
        </div>
        <div class="ob-dbody">
          <div class="ob-view-section" v-if="viewLoading">
            <div class="ob-view-sec-lbl">Items</div>
            <div v-for="n in 3" :key="n" class="ob-shimmer" style="height:36px;margin-bottom:6px;border-radius:6px"></div>
          </div>
          <div class="ob-view-section" v-else-if="(viewDoc.items||[]).length">
            <div class="ob-view-sec-lbl">Items ({{ viewDoc.items.length }})</div>
            <table class="ob-view-items-tbl">
              <thead><tr>
                <th>Item</th><th>Warehouse</th><th>Batch No</th><th class="ta-r">Qty</th><th class="ta-r">Rate</th><th class="ta-r">Amount</th>
              </tr></thead>
              <tbody>
                <tr v-for="it in viewDoc.items" :key="it.name||it.idx">
                  <td>
                    <div style="font-weight:600;font-size:12.5px">{{ it.item_code }}</div>
                    <div v-if="it.item_name && it.item_name!==it.item_code" style="font-size:11px;color:#9ca3af">{{ it.item_name }}</div>
                  </td>
                  <td class="text-muted" style="font-size:12px">{{ it.t_warehouse||viewDoc.to_warehouse||'—' }}</td>
                  <td class="text-muted" style="font-size:12px">{{ it.batch_no||'—' }}</td>
                  <td class="ta-r">{{ it.qty }}</td>
                  <td class="ta-r">{{ fmtCur(it.basic_rate) }}</td>
                  <td class="ta-r" style="font-weight:600">{{ fmtCur(flt(it.qty)*flt(it.basic_rate)) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="ob-view-section">
            <div class="ob-view-sec-lbl">Value Summary</div>
            <div class="ob-val-box">
              <div class="ob-val-lbl">Total Opening Value</div>
              <div class="ob-val-num">{{ fmtCur(viewDoc.total_incoming_value||0) }}</div>
            </div>
          </div>
          <div v-if="viewDoc.docstatus===0" style="display:flex;justify-content:flex-end;gap:8px">
            <button class="ob-btn-cancel" @click="openEdit(viewDoc); viewOpen=false"><span v-html="icon('edit',13)"></span> Edit</button>
            <button class="ob-btn-primary" @click="submitEntry(viewDoc.name)"><span v-html="icon('check',13)"></span> Submit</button>
          </div>
        </div>
      </template>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from "vue";
import { apiList, apiGet, apiPOST, apiSave, apiSubmit, resolveCompany, apiLinkValues } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";
import { flt, fmtDate } from "../utils/format.js";
import SearchableSelect from "../components/SearchableSelect.vue";

const { toast } = useToast();

const search       = ref("");
const list         = ref([]);
const loading      = ref(false);
const drawerOpen   = ref(false);
const drawerSaving = ref(false);
const editingName  = ref("");
const viewOpen     = ref(false);
const viewDoc      = ref(null);
const viewLoading  = ref(false);
const warehouses   = ref([]);
const items        = ref([]);
const lines        = ref([]);
let _id = 1;
const blankLine = () => ({
  id: _id++, item_code: "", item_name: "", qty: 1, basic_rate: 0,
  t_warehouse: "", batch_no: "", manufacturing_date: "", expiry_date: "",
  has_batch_no: 0, batchOptions: [],
});

const form = reactive({
  posting_date: new Date().toISOString().slice(0, 10),
  to_warehouse: "",
  remarks: "",
});

const lineTotal = computed(() => lines.value.reduce((s, l) => s + flt(l.qty) * flt(l.basic_rate), 0));

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase();
  if (!q) return list.value;
  return list.value.filter(e =>
    (e.name || "").toLowerCase().includes(q) ||
    (e.to_warehouse || "").toLowerCase().includes(q) ||
    (e.remarks || "").toLowerCase().includes(q)
  );
});

// ── Pagination ──────────────────────────────────────────────────────────
const page     = ref(1);
const pageSize = ref(20);
const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / pageSize.value)));
const paginated = computed(() => {
  const start = (page.value - 1) * pageSize.value;
  return filtered.value.slice(start, start + pageSize.value);
});
const pageRangeLabel = computed(() => {
  if (!filtered.value.length) return "0 of 0";
  const start = (page.value - 1) * pageSize.value + 1;
  const end = Math.min(filtered.value.length, page.value * pageSize.value);
  return `${start}–${end} of ${filtered.value.length}`;
});
function goToPage(p) {
  page.value = Math.min(Math.max(1, p), totalPages.value);
}
// Reset to page 1 whenever the search term changes, and clamp the current
// page if the underlying list shrinks below it (e.g. after a reload).
watch(search, () => { page.value = 1; });
watch(totalPages, (tp) => { if (page.value > tp) page.value = tp; });

const kpi = computed(() => {
  // Cancelled entries no longer represent real opening balances — exclude
  // them here the same way "value" already does, so the KPI strip can't show
  // e.g. "Batches Created: 6" next to "Opening Value: ₹0.00".
  const active = list.value.filter(e => e.docstatus !== 2);
  return {
    total:      list.value.length,
    itemCount:  active.reduce((s, e) => s + (e._itemCount || 0), 0),
    batchCount: active.reduce((s, e) => s + (e._batchCount || 0), 0),
    value:      list.value.filter(e => e.docstatus === 1).reduce((s, e) => s + flt(e.total_incoming_value), 0),
  };
});

function statusClass(e) {
  if (e.docstatus === 1) return "badge-green";
  if (e.docstatus === 2) return "badge-grey";
  return "badge-orange";
}
function statusLabel(e) {
  return e.docstatus === 1 ? "Submitted" : e.docstatus === 2 ? "Cancelled" : "Draft";
}
function shortWH(wh) {
  if (!wh) return "";
  const parts = wh.split(" - ");
  return parts[0].length > 18 ? parts[0].slice(0, 16) + "…" : parts[0];
}
function fmtCur(v) {
  return "₹" + flt(v).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

async function load() {
  loading.value = true;
  try {
    const co = await resolveCompany();
    const rows = await apiList("Stock Entry", {
      fields: ["name", "posting_date", "to_warehouse", "total_incoming_value", "docstatus", "remarks", "company"],
      filters: [["company", "=", co], ["stock_entry_type", "=", "Opening Stock"]],
      limit: 500, order: "posting_date desc, creation desc",
    });
    // Item/batch counts for every row in one grouped query instead of
    // firing a full apiGet() per row (that N+1 pattern is what made this
    // list slow to load once there were more than a handful of entries).
    try {
      const names = rows.map(r => r.name);
      const counts = names.length
        ? await apiPOST("zoho_books_clone.api.docs.get_stock_entry_line_counts", { names })
        : {};
      for (const e of rows) {
        const c = counts[e.name];
        e._itemCount = c ? c.item_count : 0;
        e._batchCount = c ? c.batch_count : 0;
      }
    } catch {
      for (const e of rows) { e._itemCount = null; e._batchCount = null; }
    }
    list.value = rows;
  } catch (e) {
    toast.error(e.message || "Failed to load opening stock entries");
  } finally {
    loading.value = false;
  }
}

async function openView(e) {
  viewDoc.value = { ...e, items: [] };
  viewOpen.value = true;
  viewLoading.value = true;
  try {
    const full = await apiGet("Stock Entry", e.name);
    if (full) viewDoc.value = full;
  } catch { /* keep list-row data */ }
  viewLoading.value = false;
}

async function submitEntry(name) {
  try {
    await apiSubmit("Stock Entry", name);
    toast.success("Opening Stock Entry submitted");
    viewOpen.value = false;
    await load();
  } catch (e) { toast.error(e.message || "Submit failed"); }
}

async function fetchWarehouses(q = "") {
  try {
    const co = await resolveCompany();
    const r = await apiList("Warehouse", {
      fields: ["name"],
      filters: [["company", "=", co], ["is_group", "=", 0], ...(q ? [["name", "like", `%${q}%`]] : [])],
      limit: 20,
    });
    warehouses.value = r.map(x => ({ label: x.name, value: x.name }));
  } catch { warehouses.value = []; }
}
async function fetchItems(q = "") {
  try {
    const r = await apiLinkValues("Item", q);
    items.value = r.map(x => ({ label: x.name, value: x.name }));
  } catch { items.value = []; }
}
async function fetchBatches(line, q = "") {
  if (!line.item_code) { line.batchOptions = []; return; }
  const forItem = line.item_code;
  try {
    const filters = [["item", "=", forItem], ["disabled", "=", 0]];
    if (q) filters.push(["name", "like", `%${q}%`]);
    const r = await apiList("Batch", {
      fields: ["name", "manufacturing_date", "expiry_date", "batch_qty"],
      filters, limit: 20,
    });
    // Item may have changed while this request was in flight — don't let a
    // stale response overwrite the options for whatever item is selected now.
    if (line.item_code !== forItem) return;
    line.batchOptions = r.map(b => ({
      value: b.name,
      label: (b.batch_qty !== undefined && b.batch_qty !== null) ? `${b.name} (Qty: ${b.batch_qty})` : b.name,
      manufacturing_date: b.manufacturing_date || "",
      expiry_date: b.expiry_date || "",
    }));
  } catch { if (line.item_code === forItem) line.batchOptions = []; }
}
function onBatchSelect(line, opt) {
  line.batch_no = opt?.value ?? opt;
  // Existing batch picked — mirror its dates exactly (including clearing them
  // if the batch has none) so the form never shows leftover dates from a
  // previously-typed "create new batch" attempt as if they belonged to this
  // batch.
  line.manufacturing_date = (opt && opt.manufacturing_date) || "";
  line.expiry_date = (opt && opt.expiry_date) || "";
}
function onBatchCreate(line, typed) {
  // User typed a Batch No that doesn't exist yet — treat as a new batch
  // entry; mfg/expiry stay editable below and the batch is created on save.
  line.batch_no = typed;
}
async function onItemSelect(line, opt) {
  line.item_code = opt?.value ?? opt;
  if (!line.item_code) return;
  try {
    const r = await apiList("Item", {
      fields: ["name", "item_name", "standard_buying_rate", "standard_rate", "has_batch_no"],
      filters: [["name", "=", line.item_code]], limit: 1,
    });
    const it = r && r[0];
    if (it) {
      line.item_name = it.item_name || line.item_code;
      line.has_batch_no = it.has_batch_no ? 1 : 0;
      if (!flt(line.basic_rate)) line.basic_rate = flt(it.standard_buying_rate) || flt(it.standard_rate) || 0;
      // Item changed — whatever batch/dates were on the line belonged to the
      // previous item and must not ride along, whether the new item is
      // batch-tracked or not.
      line.batch_no = "";
      line.manufacturing_date = "";
      line.expiry_date = "";
      line.batchOptions = [];
      if (line.has_batch_no) {
        await fetchBatches(line, "");
      }
    }
  } catch {}
}
function addLine() { lines.value.push(blankLine()); }
function removeLine(id) { if (lines.value.length > 1) lines.value = lines.value.filter(l => l.id !== id); }

function openNew() {
  editingName.value = "";
  Object.assign(form, {
    posting_date: new Date().toISOString().slice(0, 10),
    to_warehouse: "", remarks: "",
  });
  lines.value = [blankLine()];
  fetchWarehouses(""); fetchItems("");
  drawerOpen.value = true;
}

async function openEdit(e) {
  if (e.docstatus !== 0) return;
  editingName.value = e.name;
  Object.assign(form, {
    posting_date: e.posting_date || new Date().toISOString().slice(0, 10),
    to_warehouse: e.to_warehouse || "", remarks: e.remarks || "",
  });
  lines.value = [blankLine()];
  fetchWarehouses(""); fetchItems("");
  drawerOpen.value = true;
  try {
    const doc = await apiGet("Stock Entry", e.name);
    if (doc?.items?.length) {
      const built = await Promise.all(doc.items.map(async (it) => {
        const line = {
          id: _id++, item_code: it.item_code || "", item_name: it.item_name || it.item_code || "",
          qty: flt(it.qty) || 1, basic_rate: flt(it.basic_rate) || 0,
          t_warehouse: it.t_warehouse || "", batch_no: it.batch_no || "",
          manufacturing_date: "", expiry_date: "", has_batch_no: 0, batchOptions: [],
        };
        try {
          const r = await apiList("Item", { fields: ["name", "has_batch_no"], filters: [["name", "=", line.item_code]], limit: 1 });
          line.has_batch_no = r?.[0]?.has_batch_no ? 1 : 0;
        } catch {
          // Lookup failed (e.g. network blip) — don't default to "not
          // batch-tracked" here, since saveEntry() nulls batch_no for any
          // line where has_batch_no is falsy. The row already carries a
          // batch_no from the saved doc, which is strong evidence the item
          // is in fact batch-tracked, so preserve it rather than silently
          // stripping it on the next save.
          line.has_batch_no = line.batch_no ? 1 : 0;
        }
        if (line.has_batch_no && line.batch_no) {
          try {
            const b = await apiList("Batch", {
              fields: ["name", "manufacturing_date", "expiry_date", "batch_qty"],
              filters: [["name", "=", line.batch_no]], limit: 1,
            });
            const bd = b && b[0];
            if (bd) {
              line.manufacturing_date = bd.manufacturing_date || "";
              line.expiry_date = bd.expiry_date || "";
              line.batchOptions = [{
                value: bd.name,
                label: (bd.batch_qty !== undefined && bd.batch_qty !== null) ? `${bd.name} (Qty: ${bd.batch_qty})` : bd.name,
                manufacturing_date: bd.manufacturing_date || "", expiry_date: bd.expiry_date || "",
              }];
            }
          } catch {}
        }
        return line;
      }));
      lines.value = built.length ? built : [blankLine()];
    }
  } catch {
    toast.error("Failed to load entry for editing");
  }
}

async function saveEntry(submit) {
  const usable = lines.value.filter(l => l.item_code);
  if (!usable.length) return toast.error("At least one item is required");
  for (const [idx, l] of usable.entries()) {
    if (!(l.t_warehouse || form.to_warehouse))
      return toast.error(`Row ${idx + 1}: warehouse is required`);
    if (l.has_batch_no && !l.batch_no)
      return toast.error(`Row ${idx + 1}: ${l.item_code} is batch-tracked — Batch No is required`);
  }
  // Block disabled batches even if typed in manually (dropdown already
  // excludes them, but a typed-in exact match can bypass that). Also block a
  // typed batch_no that already exists for a *different* item — the pre-create
  // step below only checks whether the name exists, not who it belongs to, so
  // without this check a colliding name would silently reuse the wrong item's
  // batch and fail later at server-side submit, after we've already created
  // Batch records for the earlier rows (leaving them behind as orphans).
  const batchOwners = new Map(); // batch_no -> item_code, scoped to this save
  for (const [idx, l] of usable.entries()) {
    if (!l.has_batch_no || !l.batch_no) continue;
    if (batchOwners.has(l.batch_no) && batchOwners.get(l.batch_no) !== l.item_code) {
      return toast.error(`Row ${idx + 1}: Batch "${l.batch_no}" is already used for a different item in this entry.`);
    }
    batchOwners.set(l.batch_no, l.item_code);
    const existing = await apiList("Batch", { fields: ["name", "disabled", "item"], filters: [["name", "=", l.batch_no]], limit: 1 }).catch(() => []);
    if (existing.length && existing[0].disabled) {
      return toast.error(`Row ${idx + 1}: Batch "${l.batch_no}" is disabled and can't be used.`);
    }
    if (existing.length && existing[0].item && existing[0].item !== l.item_code) {
      return toast.error(`Row ${idx + 1}: Batch "${l.batch_no}" already exists for item "${existing[0].item}", not "${l.item_code}".`);
    }
  }

  drawerSaving.value = true;
  try {
    const company = await resolveCompany();

    // Pre-create Batch records for batch-tracked lines so the Stock Entry
    // submit can resolve them as valid Links.
    for (const l of usable) {
      if (!l.has_batch_no || !l.batch_no) continue;
      const exists = await apiList("Batch", { fields: ["name"], filters: [["name", "=", l.batch_no]], limit: 1 });
      if (!exists.length) {
        // batch_qty is intentionally left at 0 here. The Stock Entry's
        // on_submit -> _adjust_batch_qty is the single authoritative writer
        // for batch_qty (it runs for every batch-tracked movement type).
        // Seeding it here too would double-count: this entry's qty would be
        // added once at creation and again when the SLE posts on submit.
        await apiSave({
          doctype: "Batch",
          batch_no: l.batch_no,
          item: l.item_code,
          warehouse: l.t_warehouse || form.to_warehouse,
          manufacturing_date: l.manufacturing_date || null,
          expiry_date: l.expiry_date || null,
          batch_qty: 0,
        });
      }
    }

    const doc = {
      doctype: "Stock Entry", company,
      stock_entry_type: "Opening Stock",
      posting_date: form.posting_date,
      to_warehouse: form.to_warehouse || null,
      remarks: form.remarks || "",
      items: usable.map(l => ({
        doctype: "Stock Entry Detail",
        item_code: l.item_code,
        item_name: l.item_name || l.item_code,
        qty: flt(l.qty),
        basic_rate: flt(l.basic_rate),
        t_warehouse: l.t_warehouse || form.to_warehouse || null,
        batch_no: l.has_batch_no ? (l.batch_no || null) : null,
      })),
    };
    if (editingName.value) doc.name = editingName.value;
    const saved = await apiSave(doc);
    if (submit) await apiSubmit("Stock Entry", saved.name);
    toast.success(`Opening Stock Entry ${saved?.name || ""} ${submit ? "submitted" : "saved as draft"}`);
    drawerOpen.value = false;
    editingName.value = "";
    await load();
  } catch (e) {
    toast.error(e.message || "Failed to save opening stock entry");
  } finally { drawerSaving.value = false; }
}

onMounted(async () => {
  await load();
});
</script>

<style scoped>
.ob-page { display:flex; flex-direction:column; gap:14px; padding:18px; }
.ob-hint { font-size:12.5px; color:#6b7280; background:#f8fafc; border:1px solid #e5e7eb; border-radius:8px; padding:10px 14px; margin:0; }
.ob-kpi-strip { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; }
.ob-kpi { display:flex; align-items:center; gap:10px; background:#fff; border:1px solid #e5e7eb; border-radius:10px; padding:12px 14px; }
.ob-kpi-ico { width:34px; height:34px; border-radius:8px; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.ob-kpi-lbl { font-size:11px; color:#6b7280; }
.ob-kpi-val { font-size:18px; font-weight:700; color:#0f172a; }

.ob-actions { display:flex; gap:10px; flex-wrap:wrap; align-items:center; justify-content:space-between; }
.ob-search-wrap { display:flex; align-items:center; gap:8px; border:1px solid #e2e8f0; border-radius:8px; padding:7px 11px; background:#fff; min-width:260px; flex:1; max-width:420px; }
.ob-search-input { border:none; outline:none; font:inherit; font-size:13px; flex:1; background:transparent; }
.ob-btn-ghost { background:#fff; border:1px solid #e2e8f0; border-radius:8px; padding:8px 12px; cursor:pointer; color:#374151; display:inline-flex; align-items:center; gap:6px; font-size:13px; }
.ob-btn-ghost:hover { background:#f8fafc; }
.ob-btn-primary { background:#2563eb; color:#fff; border:none; border-radius:8px; padding:9px 14px; cursor:pointer; font-size:13px; font-weight:600; display:inline-flex; align-items:center; gap:6px; }
.ob-btn-primary:hover { background:#1d4ed8; }
.ob-btn-primary:disabled { opacity:.6; cursor:not-allowed; }
.ob-btn-cancel { background:#fff; border:1px solid #e2e8f0; border-radius:8px; padding:9px 14px; cursor:pointer; font-size:13px; color:#374151; }
.ob-btn-save { background:#fff; border:1px solid #2563eb; color:#2563eb; border-radius:8px; padding:9px 14px; cursor:pointer; font-size:13px; font-weight:600; display:inline-flex; align-items:center; gap:6px; }
.ob-btn-save:disabled { opacity:.6; cursor:not-allowed; }

.ob-card { background:#fff; border:1px solid #e5e7eb; border-radius:10px; overflow:hidden; }
.ob-table { width:100%; border-collapse:collapse; font-size:12.5px; }
.ob-table th { background:#f9fafb; padding:9px 12px; font-size:10.5px; font-weight:700; color:#374151; text-align:left; border-bottom:1px solid #e5e7eb; text-transform:uppercase; letter-spacing:.04em; }
.ob-table td { padding:10px 12px; border-bottom:1px solid #f3f4f6; color:#111827; }
.ob-row { cursor:pointer; } .ob-row:hover td { background:#f9fafb; }
.ob-num { font-weight:600; color:#2563eb; }
.ob-wh-tag { background:#eff6ff; color:#2563eb; padding:2px 8px; border-radius:6px; font-size:11.5px; font-weight:600; }
.ob-badge { display:inline-flex; padding:3px 9px; border-radius:20px; font-size:11px; font-weight:700; }
.badge-green { background:#dcfce7; color:#16a34a; } .badge-grey { background:#f3f4f6; color:#6b7280; } .badge-orange { background:#fff7ed; color:#ea580c; }
.ob-act-btn { background:transparent; border:1px solid #e5e7eb; border-radius:6px; width:26px; height:26px; display:inline-flex; align-items:center; justify-content:center; cursor:pointer; color:#6b7280; }
.ob-act-btn:hover { background:#eff6ff; color:#2563eb; border-color:#bfdbfe; }
.ob-empty { text-align:center; padding:36px 16px; color:#6b7280; }
.ob-shimmer { height:14px; border-radius:6px; background:linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size:200% 100%; animation:ob-sh 1.4s infinite; }
@keyframes ob-sh { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
.ta-r { text-align:right; } .text-muted { color:#9ca3af; } .mono-sm { font-size:12px; }

.ob-overlay { position:fixed; inset:0; background:rgba(15,23,42,.45); z-index:40; }
.ob-drawer { position:fixed; top:0; right:-720px; width:720px; max-width:94vw; height:100%; background:#fff; box-shadow:-8px 0 30px rgba(0,0,0,.15); z-index:41; display:flex; flex-direction:column; transition:right .25s ease; }
.ob-drawer.open { right:0; }
.ob-dheader { position:relative; padding:20px; background:linear-gradient(135deg,#1e3a8a,#2563eb); flex-shrink:0; }
.ob-dh-top { display:flex; align-items:center; gap:12px; }
.ob-dh-ico { width:40px; height:40px; border-radius:10px; background:rgba(255,255,255,.18); display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.ob-dh-title { font-size:16px; font-weight:700; }
.ob-dh-sub { font-size:12px; margin-top:2px; }
.ob-dclose-abs { position:absolute; top:14px; right:14px; background:rgba(255,255,255,.15); border:none; border-radius:6px; width:28px; height:28px; color:#fff; cursor:pointer; display:flex; align-items:center; justify-content:center; }
.ob-dbody { flex:1; overflow-y:auto; padding:20px; display:flex; flex-direction:column; gap:16px; }
.ob-dfooter { display:flex; align-items:center; justify-content:flex-end; gap:8px; padding:14px 20px; border-top:1px solid #e5e7eb; flex-shrink:0; background:#f9fafb; }

.ob-fields-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.ob-field { display:flex; flex-direction:column; gap:4px; }
.ob-label { font-size:12px; font-weight:600; color:#374151; } .req { color:#dc2626; }
.ob-input { border:1px solid #e2e8f0; border-radius:8px; padding:8px 11px; font:inherit; font-size:13px; outline:none; background:#fff; color:#0f172a; }
.ob-input:focus { border-color:#2563eb; box-shadow:0 0 0 3px rgba(37,99,235,.1); }
.ob-input:disabled { background:#f8fafc; color:#9ca3af; }
.ob-input-req { border-color:#fca5a5; background:#fff7f7; }
.ob-section-title { font-size:11.5px; font-weight:700; color:#374151; text-transform:uppercase; letter-spacing:.05em; padding-bottom:6px; border-bottom:1px solid #f3f4f6; }
.ob-items-table { display:flex; flex-direction:column; border:1px solid #e5e7eb; border-radius:8px; overflow:hidden; }
.ob-line-card { padding:12px; border-top:1px solid #f3f4f6; }
.ob-line-card:first-child { border-top:none; }
.ob-line-row { display:flex; gap:10px; align-items:flex-start; }
.ob-line-field { display:flex; flex-direction:column; gap:4px; min-width:0; }
.ob-line-row-batch { margin-top:10px; padding-top:10px; border-top:1px dashed #e5e7eb; }
.ob-line-spacer { width:28px; flex-shrink:0; }
.ob-items-total { display:flex; align-items:center; justify-content:flex-end; gap:10px; padding:10px 14px; border-top:2px solid #e5e7eb; background:#f8fafc; }
.ob-items-total-label { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:#6b7280; }
.ob-items-total-val { font-weight:700; color:#0f172a; font-size:14px; }
.ob-add-line { background:transparent; border:none; border-top:1px solid #f3f4f6; color:#2563eb; font-size:12.5px; font-weight:600; cursor:pointer; padding:10px 14px; display:flex; align-items:center; gap:6px; width:100%; }
.ob-add-line:hover { background:#eff6ff; }
.ob-rm-line { background:transparent; border:1px solid #e5e7eb; border-radius:4px; width:28px; height:36px; display:inline-flex; align-items:center; justify-content:center; cursor:pointer; color:#9ca3af; flex-shrink:0; }
.ob-rm-line:hover { background:#fee2e2; color:#dc2626; border-color:#fca5a5; }
.ob-rm-line-sm { width:22px; height:22px; }

.ob-view-section { display:flex; flex-direction:column; gap:8px; }
.ob-view-sec-lbl { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; color:#9ca3af; }
.ob-view-items-tbl { width:100%; border-collapse:collapse; font-size:12.5px; border:1px solid #e5e7eb; border-radius:8px; overflow:hidden; }
.ob-view-items-tbl th { background:#f9fafb; padding:8px 10px; font-size:10.5px; font-weight:700; color:#374151; text-align:left; border-bottom:1px solid #e5e7eb; text-transform:uppercase; letter-spacing:.04em; }
.ob-view-items-tbl td { padding:9px 10px; border-bottom:1px solid #f3f4f6; color:#111827; }
.ob-val-box { border:1px solid #e2e8f0; border-radius:8px; padding:12px 14px; background:#f8fafc; }
.ob-val-lbl { font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:#6b7280; margin-bottom:4px; }
.ob-val-num { font-weight:700; font-size:16px; color:#7c3aed; }

.ob-pagination { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:10px 14px; border-top:1px solid #e5e7eb; background:#f9fafb; flex-wrap:wrap; }
.ob-pg-info { font-size:12px; color:#6b7280; }
.ob-pg-controls { display:flex; align-items:center; gap:6px; }
.ob-pg-size { border:1px solid #e2e8f0; border-radius:6px; padding:5px 8px; font-size:12px; color:#374151; background:#fff; outline:none; }
.ob-pg-btn { background:#fff; border:1px solid #e2e8f0; border-radius:6px; width:28px; height:28px; display:inline-flex; align-items:center; justify-content:center; cursor:pointer; color:#374151; font-size:14px; }
.ob-pg-btn:hover:not(:disabled) { background:#eff6ff; color:#2563eb; border-color:#bfdbfe; }
.ob-pg-btn:disabled { opacity:.4; cursor:not-allowed; }
.ob-pg-current { font-size:12px; color:#374151; padding:0 4px; white-space:nowrap; }

.ob-mobile-cards { display:none; }
.ob-desktop-table { display:table; }
@media (max-width:768px) {
  .ob-kpi-strip { grid-template-columns:1fr 1fr; }
  .ob-kpi-value { grid-column:1/-1; }
  .ob-drawer, .ob-view-drawer { width:100% !important; max-width:100% !important; right:-100% !important; }
  .ob-drawer.open, .ob-view-drawer.open { right:0 !important; }
  .ob-desktop-table { display:none !important; }
  .ob-mobile-cards { display:flex; flex-direction:column; }
  .ob-mobile-card { background:#fff; border-bottom:1px solid #e5e7eb; padding:12px 14px; cursor:pointer; }
  .ob-mc-top { display:flex; align-items:center; justify-content:space-between; margin-bottom:6px; }
  .ob-mc-docno { font-size:12px; font-weight:700; color:#2563eb; }
  .ob-mc-meta { display:flex; justify-content:space-between; font-size:12px; color:#868e96; }
  .ob-mc-empty { text-align:center; padding:32px 16px; color:#868e96; font-size:13px; }
  .ob-add-items-desktop { display:none !important; }
  .ob-add-items-mobile { display:flex !important; flex-direction:column; }
}
.ob-add-items-mobile { display:none; flex-direction:column; gap:10px; }
.ob-aic { background:#fff; border:1px solid #e5e7eb; border-radius:10px; padding:12px 14px; display:flex; flex-direction:column; gap:10px; }
.ob-aic-header { display:flex; align-items:center; justify-content:space-between; }
.ob-aic-num { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:#6b7280; }
.ob-aic-field { display:flex; flex-direction:column; gap:4px; }
.ob-aic-amount { font-size:12px; color:#6b7280; text-align:right; border-top:1px solid #f3f4f6; padding-top:8px; }
@media (max-width:480px) {
  .ob-page { padding:12px; gap:10px; }
  .ob-fields-grid { grid-template-columns:1fr !important; }
  .ob-pagination { justify-content:center; }
  .ob-pg-info { width:100%; text-align:center; }
}
</style>