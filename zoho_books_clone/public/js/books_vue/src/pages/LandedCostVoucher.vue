<template>
<div class="list-page">

  <!-- ── Toolbar ── -->
  <div class="sales-toolbar">
    <div class="sales-search">
      <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
      <input v-model="search" placeholder="Search by voucher no, PR or PI…" class="sales-search-input"/>
    </div>
    <div class="sales-pills">
      <button v-for="f in FILTERS" :key="f.key" class="sales-pill" :class="{ active: filterStatus===f.key }" @click="filterStatus=f.key">
        {{ f.label }}<span v-if="f.key" class="sales-pill-count">{{ counts[f.key] }}</span>
      </button>
    </div>
    <div class="sales-actions">
      <button class="sales-btn-ghost" @click="loadList" title="Refresh" :disabled="loading"><span v-html="icon('refresh',14)"></span></button>
      <button class="sales-btn-primary" :disabled="!$canCreate('bills')" :title="!$canCreate('bills') ? 'Read-only access' : ''" @click="openAdd">
        <span v-html="icon('plus',13)"></span> New Voucher
      </button>
    </div>
  </div>

  <!-- ── Table ── -->
  <div class="inv-table-wrap">
    <table class="inv-table inv-desktop-table">
      <thead><tr>
        <th>DATE</th>
        <th>VOUCHER#</th>
        <th>SOURCE DOC</th>
        <th>DISTRIBUTION</th>
        <th class="ta-r">CHARGES</th>
        <th>STATUS</th>
        <th style="width:120px;text-align:center">ACTIONS</th>
      </tr></thead>
      <tbody>
        <template v-if="loading">
          <tr v-for="n in 6" :key="n" class="shimmer-row">
            <td><div class="shimmer" style="width:80px"></div></td>
            <td><div class="shimmer" style="width:110px"></div></td>
            <td><div class="shimmer" style="width:120px"></div></td>
            <td><div class="shimmer" style="width:90px"></div></td>
            <td><div class="shimmer" style="width:80px;margin-left:auto"></div></td>
            <td><div class="shimmer" style="width:70px"></div></td>
            <td></td>
          </tr>
        </template>
        <template v-else>
          <tr v-for="row in paged" :key="row.name" class="inv-row">
            <td @click="openView(row)" class="text-muted mono-sm">{{ row.posting_date }}</td>
            <td @click="openView(row)"><DocLink doctype="Landed Cost Voucher" :name="row.name" /></td>
            <td @click="openView(row)" class="mono-sm">
              <DocLink v-if="row.purchase_receipt" doctype="Purchase Receipt" :name="row.purchase_receipt" @click.stop />
              <DocLink v-else-if="row.purchase_invoice" doctype="Purchase Invoice" :name="row.purchase_invoice" @click.stop />
              <span v-else>—</span>
            </td>
            <td @click="openView(row)">{{ row.distribution_method || '—' }}</td>
            <td @click="openView(row)" class="ta-r mono-sm">{{ INR(row.total_charges) }}</td>
            <td @click="openView(row)">
              <span class="inv-status-badge" :class="statusClass(row)">{{ statusLabel(row) }}</span>
            </td>
            <td style="text-align:center" @click.stop>
              <div style="display:flex;gap:4px;justify-content:center">
                <button class="inv-act-btn" @click="openView(row)" title="View"><span v-html="icon('eye',13)"></span></button>
                <button v-if="row.docstatus===0" class="inv-act-btn" @click="openView(row)" title="Edit"><span v-html="icon('edit',13)"></span></button>
                <button v-if="row.docstatus===2" class="inv-act-btn" @click="openView(row)" title="Amend"><span v-html="icon('refresh',13)"></span></button>
              </div>
            </td>
          </tr>
          <tr v-if="!sorted.length">
            <td colspan="7" class="bk-empty-state">
              <div class="bk-empty-inner">
                <template v-if="search||filterStatus">
                  <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.3"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                  <p class="bk-empty-title">No vouchers match your filters</p>
                </template>
                <template v-else>
                  <div style="font-size:32px;margin-bottom:8px">📦</div>
                  <p class="bk-empty-title">No Landed Cost Vouchers created yet</p>
                  <p class="bk-empty-sub">Capitalize freight and transport charges into stock value.</p>
                  <button class="bk-empty-btn" :disabled="!$canCreate('bills')" :title="!$canCreate('bills') ? 'Read-only access' : ''" @click="openAdd"><span v-html="icon('plus',13)"></span> New Voucher</button>
                </template>
              </div>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
  <div v-if="!loading && sorted.length" style="padding:12px 0px 4px">
    <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="sorted.length"/>
  </div>

  <!-- ══ Drawer ══ -->
  <Teleport to="body">
    <div v-if="drawerOpen" class="inv-drawer-bg" @click.self="closeDrawer">
      <div class="inv-drawer-panel inv-drawer-wide lcv-drawer">

        <div class="inv-dh">
          <div>
            <div class="inv-dh-title">{{ isNew ? 'New Landed Cost Voucher' : lcv.name }}</div>
            <div class="inv-dh-sub" v-if="!isNew">{{ lcv.posting_date }}<template v-if="lcv.posting_time"> {{ lcv.posting_time }}</template> • {{ lcv.purchase_receipt || lcv.purchase_invoice || 'No source' }}</div>
          </div>
          <div style="display:flex;align-items:center;gap:10px">
            <span v-if="!isNew" class="inv-status-badge" :class="statusClass(lcv)">{{ statusLabel(lcv) }}</span>
            <button class="inv-dclose" @click="closeDrawer"><span v-html="icon('x',16)"></span></button>
          </div>
        </div>

        <div class="inv-dbody">
          <template v-if="detailLoading">
            <div class="shimmer" style="height:200px;border-radius:10px"></div>
          </template>
          <template v-else>

            <div v-if="lcv.docstatus===1" class="lcv-notice">
              <span v-html="icon('check',14)"></span>
              Submitted — {{ INR(lcv.total_capitalized_amount) }} of {{ INR(lcv.total_charges) }} in charges has been capitalized into stock value.
              <span v-if="flt(lcv.total_capitalized_amount) < flt(lcv.total_charges)">
                The remainder stays booked as a period expense (some received stock was already issued before this voucher was submitted).
              </span>
            </div>

            <!-- Source document -->
            <div class="inv-sec-lbl">Source Document</div>
            <div class="lcv-grid" style="margin-bottom:16px">
              <div>
                <label class="inv-lbl">Posting Date</label>
                <input class="inv-fi" type="date" v-model="lcv.posting_date" :disabled="readOnly"/>
              </div>
              <div>
                <label class="inv-lbl">Distribution Method</label>
                <select class="inv-fi" v-model="lcv.distribution_method" :disabled="readOnly" @change="refreshPreview">
                  <option value="By Value">By Value</option>
                  <option value="By Qty">By Qty</option>
                </select>
              </div>
              <div>
                <label class="inv-lbl">Purchase Receipt</label>
                <SearchableSelect
                  v-model="lcv.purchase_receipt"
                  :options="prOptions"
                  placeholder="— Select Purchase Receipt —"
                  :disabled="readOnly || !!lcv.purchase_invoice"
                  @update:modelValue="onPickPR"
                  @search="searchPR"
                />
              </div>
              <div>
                <label class="inv-lbl">Purchase Invoice</label>
                <SearchableSelect
                  v-model="lcv.purchase_invoice"
                  :options="piOptions"
                  placeholder="— Select Purchase Invoice —"
                  :disabled="readOnly || !!lcv.purchase_receipt"
                  @update:modelValue="onPickPI"
                  @search="searchPI"
                />
              </div>
            </div>
            <div v-if="!readOnly" style="margin-bottom:20px">
              <button class="sales-btn-ghost" @click="pullItemsFromSource" :disabled="pulling || (!lcv.purchase_receipt && !lcv.purchase_invoice)">
                {{ pulling ? 'Pulling…' : '⇩ Pull Items from Source' }}
              </button>
              <span v-if="!lcv.items.length && (lcv.purchase_receipt || lcv.purchase_invoice)" style="margin-left:10px;font-size:12.5px;color:#9ca3af">
                Pull items to build the allocation, then add charges below.
              </span>
            </div>

            <!-- Charges -->
            <div class="inv-sec-lbl">Charges</div>
            <div class="inv-table-wrap" style="margin-bottom:8px" v-if="lcv.charges.length">
              <table class="inv-table" style="font-size:13px">
                <thead>
                  <tr>
                    <th style="width:220px">Expense Account</th>
                    <th class="ta-r" style="width:120px">Amount</th>
                    <th>Description (optional)</th>
                    <th style="width:200px">Paid Through</th>
                    <th style="width:150px">Expense Type</th>
                    <th v-if="readOnly" style="width:110px">Expense</th>
                    <th v-if="!readOnly" style="width:36px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(c, idx) in lcv.charges" :key="idx">
                    <td>
                      <SearchableSelect
                        v-model="c.account"
                        :options="accountOptions"
                        placeholder="— Select expense account —"
                        :disabled="readOnly"
                        compact
                      />
                    </td>
                    <td class="ta-r">
                      <input class="inv-fi mono-sm" type="number" min="0" step="any" v-model.number="c.amount"
                             :disabled="readOnly" @change="refreshPreview" style="width:110px;text-align:right"/>
                    </td>
                    <td>
                      <input class="inv-fi" v-model="c.description" :disabled="readOnly" placeholder="e.g. Inward Freight — KPN Logistics"/>
                    </td>
                    <td>
                      <SearchableSelect
                        v-model="c.paid_through"
                        :options="payThroughOptions"
                        placeholder="— Cash/Bank —"
                        :disabled="readOnly || !!(c.reference_doctype && c.reference_name)"
                        compact
                      />
                    </td>
                    <td>
                      <SearchableSelect
                        v-model="c.expense_type"
                        :options="expenseTypeOptions"
                        placeholder="— Category —"
                        :disabled="readOnly"
                        compact
                      />
                    </td>
                    <td v-if="readOnly">
                      <a v-if="c.reference_doctype === 'Expense' && c.reference_name"
                         href="#" class="mono-sm" style="color:#3B5BDB;font-weight:600"
                         @click.prevent="viewLinkedExpense(c.reference_name)">
                        {{ c.reference_name }}
                      </a>
                      <span v-else class="c-muted" style="font-size:11.5px">
                        {{ c.reference_doctype ? c.reference_doctype + " " + c.reference_name : "—" }}
                      </span>
                    </td>
                    <td v-if="!readOnly" style="text-align:center">
                      <button class="inv-act-btn" style="color:#dc2626" :disabled="!(isNew ? $canCreate('bills') : $canEdit('bills'))" @click="removeCharge(idx)"><span v-html="icon('trash',13)"></span></button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="lcv-empty-box">No charges added yet.</div>
            <div v-if="!readOnly" class="lcv-add-row" :class="{disabled: !(isNew ? $canCreate('bills') : $canEdit('bills'))}" @click="(isNew ? $canCreate('bills') : $canEdit('bills')) && addCharge()">
              <span v-html="icon('plus',13)"></span> Add Charge
            </div>
            <div v-if="!readOnly && lcv.charges.length" style="font-size:11.5px;color:#94a3b8;margin:-4px 0 8px 2px">
              Paid Through is required unless this charge is already booked on another document (Bill/Journal Entry) — on submit, a new Expense entry is auto-created for it and then reclassified into stock value.
            </div>

            <!-- Item allocation preview -->
            <div class="inv-sec-lbl">Item Allocation {{ previewLoading ? '(recalculating…)' : '' }}</div>
            <div class="inv-table-wrap" v-if="lcv.items.length">
              <table class="inv-table" style="font-size:12.5px">
                <thead>
                  <tr>
                    <th>Item</th>
                    <th>Warehouse</th>
                    <th class="ta-r">Qty</th>
                    <th class="ta-r">Purchase Amt</th>
                    <th class="ta-r">Old Rate</th>
                    <th class="ta-r">Allocated</th>
                    <th class="ta-r">New Rate</th>
                    <th v-if="lcv.docstatus===1" class="ta-r">Capitalized</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, idx) in lcv.items" :key="idx">
                    <td>{{ row.item_name || row.item_code }}<div class="mono-sm" style="font-size:11px;color:#9ca3af">{{ row.item_code }}</div></td>
                    <td>{{ row.warehouse }}</td>
                    <td class="ta-r mono-sm">{{ row.received_qty }}</td>
                    <td class="ta-r mono-sm">{{ INR(row.purchase_amount) }}</td>
                    <td class="ta-r mono-sm">{{ INR(row.valuation_rate) }}</td>
                    <td class="ta-r mono-sm" style="font-weight:700;color:#1e3a5f">{{ INR(row.allocated_amount) }}</td>
                    <td class="ta-r mono-sm" style="font-weight:700;color:#059669">{{ INR(row.new_valuation_rate) }}</td>
                    <td v-if="lcv.docstatus===1" class="ta-r mono-sm">{{ INR(row.capitalized_amount) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="lcv-empty-box">Pull items from a source document to see the allocation.</div>

            <!-- Totals -->
            <div class="lcv-grid" style="margin-top:20px">
              <div>
                <div class="inv-lbl">Total Purchase Amount</div>
                <div class="mono-sm" style="font-size:14px;font-weight:700">{{ INR(lcv.total_purchase_amount) }}</div>
              </div>
              <div>
                <div class="inv-lbl">Total Charges</div>
                <div class="mono-sm" style="font-size:14px;font-weight:700;color:#1e3a5f">{{ INR(lcv.total_charges) }}</div>
              </div>
              <div v-if="lcv.docstatus===1">
                <div class="inv-lbl">Total Capitalized</div>
                <div class="mono-sm" style="font-size:14px;font-weight:700;color:#059669">{{ INR(lcv.total_capitalized_amount) }}</div>
              </div>
            </div>

            <div style="margin-top:18px">
              <label class="inv-lbl">Remarks</label>
              <textarea class="inv-fi" v-model="lcv.remarks" :disabled="readOnly" rows="2"></textarea>
            </div>

            <template v-if="!isNew && lcv.docstatus===1">
              <div class="inv-sec-lbl" style="margin-top:18px">Journal</div>
              <JournalTab
                voucher-type="Landed Cost Voucher"
                :voucher-no="lcv.name"
                label="Landed Cost Voucher"
                :currency="lcv.currency || 'INR'"
              />
            </template>

          </template>
        </div>

        <div class="inv-dfooter">
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <button v-if="!isNew && lcv.docstatus===2" class="sales-btn-ghost" :disabled="amending || !$canCreate('bills')" :title="!$canCreate('bills') ? 'Read-only access' : ''" @click="amendLcv">
              {{ amending ? 'Amending…' : 'Amend' }}
            </button>
            <button v-if="!isNew && lcv.docstatus===1" class="sales-btn-ghost" style="color:#dc2626" :disabled="cancelling || !$canDelete('bills')" :title="!$canDelete('bills') ? 'Not permitted' : ''" @click="cancelLcv">
              {{ cancelling ? 'Cancelling…' : 'Cancel Voucher' }}
            </button>
            <button v-if="!isNew && lcv.docstatus===0" class="sales-btn-primary" :disabled="submitting || saving || !$canEdit('bills')" :title="!$canEdit('bills') ? 'Read-only access' : ''" @click="submitLcv">
              {{ submitting ? 'Submitting…' : 'Submit' }}
            </button>
          </div>
          <div style="display:flex;gap:8px">
            <button class="add-btn-cancel" @click="closeDrawer">Close</button>
            <button v-if="readOnly===false" class="add-btn-draft" :disabled="saving || previewLoading || !(isNew ? $canCreate('bills') : $canEdit('bills'))" :title="!(isNew ? $canCreate('bills') : $canEdit('bills')) ? 'Read-only access' : ''" @click="save">
              {{ saving ? 'Saving…' : (isNew ? 'Save' : 'Save Changes') }}
            </button>
          </div>
        </div>

      </div>
    </div>
  </Teleport>

</div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import DocLink from "../components/DocLink.vue";
import { apiGet, apiSave, apiList, apiSubmit, apiCancel, apiAmend, apiCall, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import Pagination from "../components/Pagination.vue";
import SearchableSelect from "../components/SearchableSelect.vue";
import JournalTab from "../components/JournalTab.vue";

const ENGINE = "zoho_books_clone.inventory.landed_cost_engine.";

const route = useRoute();
const router = useRouter();
const { toast } = useToast();

function flt(n) { const x = Number(n); return isNaN(x) ? 0 : x; }

// Local (not UTC) YYYY-MM-DD — new Date().toISOString() is always UTC and
// can show "yesterday" for users west of UTC late in the day.
function todayLocal() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

// ── LIST STATE ──────────────────────────────────────────────
const loading = ref(false);
const list = ref([]);
const search = ref("");
const filterStatus = ref("");
const page = ref(1);
const pageSize = ref(20);

const FILTERS = [
  { key: "", label: "All" },
  { key: "draft", label: "Draft" },
  { key: "submitted", label: "Submitted" },
  { key: "cancelled", label: "Cancelled" },
];

const counts = computed(() => ({
  draft: list.value.filter(i => i.docstatus === 0).length,
  submitted: list.value.filter(i => i.docstatus === 1).length,
  cancelled: list.value.filter(i => i.docstatus === 2).length,
}));

async function loadList() {
  loading.value = true;
  try {
    const fields = ["name", "posting_date", "purchase_receipt", "purchase_invoice", "distribution_method", "total_charges", "total_capitalized_amount", "docstatus", "modified"];
    const r = await apiList("Landed Cost Voucher", { fields, limit: 100000, order: "modified desc" });
    list.value = r || [];
  } catch (e) {
    toast("Could not load Landed Cost Vouchers: " + e.message, "error");
  }
  loading.value = false;
}

const sorted = computed(() => {
  let r = list.value;
  if (filterStatus.value === "draft") r = r.filter(i => i.docstatus === 0);
  else if (filterStatus.value === "submitted") r = r.filter(i => i.docstatus === 1);
  else if (filterStatus.value === "cancelled") r = r.filter(i => i.docstatus === 2);
  const q = search.value.toLowerCase().trim();
  if (q) r = r.filter(i =>
    (i.name || "").toLowerCase().includes(q) ||
    (i.purchase_receipt || "").toLowerCase().includes(q) ||
    (i.purchase_invoice || "").toLowerCase().includes(q)
  );
  return r;
});

const paged = computed(() => {
  const start = (page.value - 1) * pageSize.value;
  return sorted.value.slice(start, start + pageSize.value);
});
watch([search, filterStatus], () => { page.value = 1; });

function statusLabel(row) {
  if (row.docstatus === 1) return "Submitted";
  if (row.docstatus === 2) return "Cancelled";
  return "Draft";
}
function statusClass(row) {
  if (row.docstatus === 1) return "status-submitted";
  if (row.docstatus === 2) return "status-cancelled";
  return "status-draft";
}

// ── DRAWER STATE ─────────────────────────────────────────────
const drawerOpen = ref(false);
const currentName = ref(null);
const isNew = computed(() => currentName.value === null);
const detailLoading = ref(false);
const saving = ref(false);
const submitting = ref(false);
const cancelling = ref(false);
const amending = ref(false);
const pulling = ref(false);
const previewLoading = ref(false);

const readOnly = computed(() => !isNew.value && lcv.value.docstatus !== 0);

function emptyLCV() {
  return {
    doctype: "Landed Cost Voucher",
    posting_date: todayLocal(),
    distribution_method: "By Value",
    purchase_receipt: "",
    purchase_invoice: "",
    items: [],
    charges: [],
    total_purchase_amount: 0,
    total_charges: 0,
    total_capitalized_amount: 0,
    remarks: "",
    docstatus: 0,
  };
}
const lcv = ref(emptyLCV());
const accounts = ref([]);
const accountOptions = computed(() =>
  accounts.value.map(a => ({ value: a.name, label: a.account_name || a.name }))
);
const payThroughAccounts = ref([]);
const payThroughOptions = computed(() =>
  payThroughAccounts.value.map(a => ({ value: a.name, label: a.account_name || a.name }))
);
// expense_type is a Link to Expense Category (per-company autoname
// "{category_name} - {company}") — fetch real doc names/labels rather than
// hardcoding option text, same pattern as Expenses.vue's fetchExpenseCategories().
const expenseCategories = ref([]);
const expenseTypeOptions = computed(() =>
  expenseCategories.value.map(c => ({ value: c.name, label: c.category_name || c.name }))
);
async function loadExpenseCategories() {
  try {
    const co = await resolveCompany();
    expenseCategories.value = await apiList("Expense Category", {
      fields: ["name", "category_name"],
      filters: [["disabled", "=", 0], ["company", "=", co]],
      order_by: "category_name asc",
      limit: 200,
    });
  } catch (e) { expenseCategories.value = []; }
}

async function loadAccounts() {
  try {
    accounts.value = await apiList("Account", {
      fields: ["name", "account_name", "account_type"],
      filters: [["is_group", "=", 0], ["disabled", "=", 0], ["account_type", "=", "Expense"]],
      limit: 100000,
    });
  } catch (e) { /* non-fatal */ }
}

async function loadPayThroughAccounts() {
  try {
    payThroughAccounts.value = await apiList("Account", {
      fields: ["name", "account_name", "account_type"],
      filters: [["is_group", "=", 0], ["disabled", "=", 0], ["account_type", "in", ["Cash", "Bank"]]],
      limit: 100000,
    });
  } catch (e) { /* non-fatal */ }
}

function openAdd() {
  currentName.value = null;
  lcv.value = emptyLCV();
  drawerOpen.value = true;
  if (route.name !== "landed-cost-vouchers") router.replace("/purchasing/landed-cost-vouchers");
}
function openView(row) {
  currentName.value = row.name;
  drawerOpen.value = true;
  loadDetail(row.name);
  if (route.name !== "landed-cost-vouchers") router.replace("/purchasing/landed-cost-vouchers");
}
function closeDrawer() {
  drawerOpen.value = false;
}

// Deep-link support: /purchasing/landed-cost-vouchers/new?purchase_receipt=XXX (used by Purchase Receipts)
// and /purchasing/landed-cost-vouchers/:name open the drawer directly, then normalize the URL back to the list.
// Extracted into a function (not just onMounted) because Vue Router reuses this
// component instance when navigating between /purchasing/landed-cost-vouchers/:name
// URLs — onMounted alone would miss those in-place navigations.
async function _handleRouteParam() {
  const paramName = route.params.name;
  if (paramName === "new") {
    currentName.value = null;
    lcv.value = emptyLCV();
    const preset = route.query.purchase_receipt || route.query.purchase_invoice;
    // Only one of PR/PI is ever valid at a time — if a URL somehow carries
    // both query params, prefer Purchase Receipt and ignore the other so we
    // never end up with both fields populated at once (which would desync
    // the :disabled bindings on the two SearchableSelect fields).
    if (route.query.purchase_receipt) {
      lcv.value.purchase_receipt = route.query.purchase_receipt;
    } else if (route.query.purchase_invoice) {
      lcv.value.purchase_invoice = route.query.purchase_invoice;
    }
    drawerOpen.value = true;
    if (preset) await pullItemsFromSource();
    router.replace("/purchasing/landed-cost-vouchers");
  } else if (paramName) {
    currentName.value = paramName;
    drawerOpen.value = true;
    loadDetail(paramName);
    router.replace("/purchasing/landed-cost-vouchers");
  }
}

onMounted(_handleRouteParam);
watch(() => route.params.name, (n, old) => { if (n && n !== old) _handleRouteParam(); });

async function loadDetail(name) {
  detailLoading.value = true;
  try {
    const doc = await apiGet("Landed Cost Voucher", name);
    doc.items = doc.items || [];
    doc.charges = doc.charges || [];
    lcv.value = doc;
  } catch (e) {
    toast("Could not load " + name + ": " + e.message, "error");
  }
  detailLoading.value = false;
}

onMounted(() => { loadList(); loadAccounts(); loadPayThroughAccounts(); loadPRList(); loadPIList(); loadExpenseCategories(); });

// ── Charges ──────────────────────────────────────────────────
function addCharge() {
  lcv.value.charges.push({ description: "", account: "", amount: 0, paid_through: "", expense_type: "" });
}
function viewLinkedExpense(expenseName) {
  router.push({ path: "/expenses", query: { view: expenseName } });
}
function removeCharge(idx) {
  lcv.value.charges.splice(idx, 1);
  refreshPreview();
}

// ── Pull items + live allocation preview ────────────────────
async function pullItemsFromSource() {
  const sourceDoctype = lcv.value.purchase_receipt ? "Purchase Receipt" : (lcv.value.purchase_invoice ? "Purchase Invoice" : null);
  const sourceName = lcv.value.purchase_receipt || lcv.value.purchase_invoice;
  if (!sourceDoctype || !sourceName) {
    toast("Set a Purchase Receipt or Purchase Invoice first.", "error");
    return;
  }
  pulling.value = true;
  try {
    const r = await apiCall(ENGINE + "get_landed_cost_preview", {
      source_doctype: sourceDoctype,
      source_name: sourceName,
      charges: JSON.stringify(lcv.value.charges.map(c => ({ amount: c.amount }))),
      distribution_method: lcv.value.distribution_method,
    });
    lcv.value.items = r.items || [];
    lcv.value.total_purchase_amount = r.total_purchase_amount || 0;
    lcv.value.total_charges = r.total_charges || 0;
    if (!lcv.value.charges.length) toast("Items pulled. Add charges below to allocate.", "success");
  } catch (e) {
    toast("Could not pull items: " + e.message, "error");
  }
  pulling.value = false;
}

let previewTimer = null;
function refreshPreview() {
  if (!lcv.value.items.length) return;
  clearTimeout(previewTimer);
  previewTimer = setTimeout(async () => {
    const sourceDoctype = lcv.value.purchase_receipt ? "Purchase Receipt" : (lcv.value.purchase_invoice ? "Purchase Invoice" : null);
    const sourceName = lcv.value.purchase_receipt || lcv.value.purchase_invoice;
    if (!sourceDoctype || !sourceName) return;
    previewLoading.value = true;
    try {
      const r = await apiCall(ENGINE + "get_landed_cost_preview", {
        source_doctype: sourceDoctype,
        source_name: sourceName,
        charges: JSON.stringify(lcv.value.charges.map(c => ({ amount: c.amount }))),
        distribution_method: lcv.value.distribution_method,
      });
      // Merge allocation results back onto existing rows (preserves warehouse/batch already pulled).
      // Matched POSITIONALLY, not by item_code+warehouse — two rows can share
      // the same item+warehouse (different batches), and a key-based match
      // would collide, silently duplicating one row's allocation onto both.
      // Both this call and the original pull iterate the same source
      // document's item rows in the same order, so position is a safe match.
      const previewItems = r.items || [];
      if (previewItems.length === lcv.value.items.length) {
        lcv.value.items.forEach((row, i) => {
          row.allocated_amount = previewItems[i].allocated_amount;
          row.new_valuation_rate = previewItems[i].new_valuation_rate;
        });
      }
      lcv.value.total_charges = r.total_charges || 0;
    } catch (e) {
      // Silent — preview is best-effort; save-time validation will catch real errors.
    }
    previewLoading.value = false;
  }, 400);
}
watch(() => lcv.value.charges.map(c => c.amount).join(","), refreshPreview);
watch(() => lcv.value.distribution_method, refreshPreview);

// ── Source document lists (Purchase Receipt / Purchase Invoice) ─────
// Powers the SearchableSelect fields above — shows a live, typeable list
// of submitted docs, matching standard Link-field UX, instead of a bare
// text input with a separate "pick" button.
const prList = ref([]);
const piList = ref([]);

function docLabel(o) {
  const bits = [o.name];
  if (o.supplier) bits.push(o.supplier);
  if (o.posting_date) bits.push(o.posting_date);
  return bits.join(" • ");
}
const prOptions = computed(() => prList.value.map(o => ({ value: o.name, label: docLabel(o) })));
const piOptions = computed(() => piList.value.map(o => ({ value: o.name, label: docLabel(o) })));

async function loadPRList(q = "") {
  try {
    const filters = [["docstatus", "=", 1]];
    if (q) filters.push(["name", "like", "%" + q + "%"]);
    prList.value = await apiList("Purchase Receipt", {
      fields: ["name", "supplier", "posting_date"],
      filters, limit: 50, order: "posting_date desc",
    });
  } catch (e) { /* non-fatal */ }
}
async function loadPIList(q = "") {
  try {
    const filters = [["docstatus", "=", 1]];
    if (q) filters.push(["name", "like", "%" + q + "%"]);
    piList.value = await apiList("Purchase Invoice", {
      fields: ["name", "supplier", "posting_date"],
      filters, limit: 50, order: "posting_date desc",
    });
  } catch (e) { /* non-fatal */ }
}
let prSearchTimer = null;
function searchPR(q) {
  clearTimeout(prSearchTimer);
  prSearchTimer = setTimeout(() => loadPRList(q), 250);
}
let piSearchTimer = null;
function searchPI(q) {
  clearTimeout(piSearchTimer);
  piSearchTimer = setTimeout(() => loadPIList(q), 250);
}

function clearPulledData() {
  lcv.value.items = [];
  lcv.value.charges = [];
  lcv.value.total_purchase_amount = 0;
  lcv.value.total_charges = 0;
}
async function onPickPR(name) {
  if (name) {
    lcv.value.purchase_invoice = "";
    await pullItemsFromSource();
  } else {
    clearPulledData();
  }
}
async function onPickPI(name) {
  if (name) {
    lcv.value.purchase_receipt = "";
    await pullItemsFromSource();
  } else {
    clearPulledData();
  }
}

// ── Save / Submit / Cancel / Amend ──────────────────────────
async function save() {
  if (!lcv.value.purchase_receipt && !lcv.value.purchase_invoice) {
    toast("Set a Purchase Receipt or Purchase Invoice.", "error"); return;
  }
  if (!lcv.value.items.length) {
    toast("Pull items from the source document first.", "error"); return;
  }
  if (!lcv.value.charges.length) {
    toast("Add at least one charge.", "error"); return;
  }
  const badRow = lcv.value.charges.find(c => !(c.reference_doctype && c.reference_name) && !c.paid_through);
  if (badRow) {
    toast("Every charge needs a Paid Through account (or must already be linked to a Bill/Journal Entry).", "error");
    return;
  }
  saving.value = true;
  try {
    const saved = await apiSave(lcv.value);
    lcv.value = saved;
    currentName.value = saved.name;
    toast("Saved.", "success");
    loadList();
  } catch (e) {
    toast("Save failed: " + e.message, "error");
  }
  saving.value = false;
}

async function submitLcv() {
  submitting.value = true;
  try {
    await apiSubmit("Landed Cost Voucher", lcv.value.name);
    toast("Submitted — charges capitalized into stock value.", "success");
    await loadDetail(lcv.value.name);
    loadList();
  } catch (e) {
    toast("Submit failed: " + e.message, "error");
  }
  submitting.value = false;
}

async function cancelLcv() {
  if (!confirm(`Cancel ${lcv.value.name}? This reverses the stock valuation and GL entries.`)) return;
  cancelling.value = true;
  try {
    await apiCancel("Landed Cost Voucher", lcv.value.name);
    toast("Cancelled.", "success");
    await loadDetail(lcv.value.name);
    loadList();
  } catch (e) {
    toast("Cancel failed: " + e.message, "error");
  }
  cancelling.value = false;
}

async function amendLcv() {
  amending.value = true;
  try {
    const amended = await apiAmend("Landed Cost Voucher", lcv.value.name);
    toast("Amendment created.", "success");
    currentName.value = amended.name;
    await loadDetail(amended.name);
    loadList();
  } catch (e) {
    toast("Amend failed: " + e.message, "error");
  }
  amending.value = false;
}

// ── UTIL ─────────────────────────────────────────────────────
function INR(n) {
  if (n == null || isNaN(n)) return "OMR 0.00";
  return "OMR " + Number(n).toLocaleString("en-OM", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
}

const ICONS = {
  plus:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>',
  search:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><path d="m21 21-4.35-4.35"></path></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>',
  eye:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>',
  edit:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>',
  refresh:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>',
  x:     '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>',
};
function icon(name, size) {
  return (ICONS[name] || "").replace("<svg ", `<svg width="${size}" height="${size}" `);
}
</script>

<style scoped>
.lcv-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:14px; }
.lcv-notice { background:#fff3bf; border:1px solid rgba(230,119,0,.2); border-radius:8px; padding:10px 14px; margin-bottom:18px; font-size:13px; color:#e67700; display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
.lcv-empty-box { color:#9ca3af; text-align:center; padding:14px; font-size:13px; border:1px dashed #e2e8f0; border-radius:8px; margin-bottom:8px; }
.lcv-add-row { display:flex; align-items:center; gap:8px; padding:8px 12px; color:#1a6ef7; cursor:pointer; font-size:13px; font-weight:600; border-radius:6px; margin-top:4px; width:fit-content; }
.lcv-add-row:hover { background:#eaf1ff; }
.lcv-drawer .inv-sec-lbl { font-size:10.5px; font-weight:700; letter-spacing:.6px; text-transform:uppercase; color:#9ca3af; margin-bottom:12px; margin-top:4px; padding-top:16px; border-top:1px solid #f0f2f5; }
.lcv-drawer .inv-sec-lbl:first-child { border-top:none; padding-top:0; margin-top:0; }
.lcv-drawer .inv-lbl { display:block; font-size:11.5px; font-weight:600; color:#495057; margin-bottom:5px; }
.lcv-drawer .inv-fi { width:100%; border:1px solid #e2e8f0; border-radius:6px; padding:7px 10px; font-size:13px; font-family:inherit; outline:none; box-sizing:border-box; background:#fff; }
.lcv-drawer .inv-fi:disabled { background:#f8f9fc; color:#9ca3af; }
.lcv-drawer .inv-fi:focus { border-color:#1a6ef7; box-shadow:0 0 0 3px rgba(26,110,247,.1); }
.bomx-modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,.4); display:flex; align-items:center; justify-content:center; z-index:9000; }
.bomx-modal { background:#fff; border-radius:10px; padding:18px; width:100%; }
.bomx-modal-hdr { font-weight:700; font-size:15px; margin-bottom:12px; }
.bomx-modal-footer { display:flex; justify-content:flex-end; gap:8px; margin-top:12px; }
.bomx-rm-card { border:1px solid #e2e8f0; border-radius:6px; margin-bottom:6px; }
.bomx-rm-card:hover { background:#f8f9fc; }
</style>