<template>
  <div class="tds-page">
    <div class="tds-topbar">
      <div class="tds-topbar-row">
        <div>
          <div class="tds-title">TDS</div>
          <div class="tds-subtitle">Tax Deducted at Source — Purchase Invoice Deductions &amp; Manual Entries</div>
        </div>
        <div class="tds-controls">
          <select v-model="periodFilter" class="tds-select" @change="load">
            <option value="">All Periods</option>
            <option v-for="p in periods" :key="p.v" :value="p.v">{{ p.l }}</option>
          </select>
          <button class="tds-btn-ghost" @click="load" :disabled="loading"><span v-html="icon('refresh',14)"></span></button>
          <button v-if="list.length" class="tds-btn-ghost" @click="exportCSV"><span v-html="icon('download',13)"></span> CSV</button>
          <button class="tds-btn-primary" :disabled="!$canCreate('accounts')" :title="!$canCreate('accounts') ? 'Read-only access' : ''" @click="openNewEntry"><span v-html="icon('plus',13)"></span> New TDS Entry</button>
        </div>
      </div>
      <div class="tds-search-wrap">
        <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
        <input v-model="search" placeholder="Search by party or section…" class="tds-search-input" />
      </div>
    </div>

    <div v-if="!loading && noTdsNote" class="tds-note">
      <span v-html="icon('info',14)"></span>
      No TDS deductions found. TDS transactions appear here when a Purchase Invoice has a tax line with "TDS", "194C", "194J" etc. in the description, or when a manual TDS Entry is created.
    </div>

    <div class="tds-summary" v-if="!loading">
      <div class="tds-sum-card"><div class="tds-sum-lbl">Total Deductions</div><div class="tds-sum-val">{{ list.length }}</div></div>
      <div class="tds-sum-card"><div class="tds-sum-lbl">Total TDS Deducted</div><div class="tds-sum-val red">{{ fmtCur(totalTds) }}</div></div>
      <div class="tds-sum-card"><div class="tds-sum-lbl">Gross Payment</div><div class="tds-sum-val">{{ fmtCur(totalGross) }}</div></div>
      <div class="tds-sum-card"><div class="tds-sum-lbl">Net Payment</div><div class="tds-sum-val blue">{{ fmtCur(totalNet) }}</div></div>
    </div>

    <!-- Section-wise breakdown -->
    <div v-if="!loading && sectionBreakdown.length > 1" class="tds-sections">
      <div class="tds-sections-title">Section-wise Breakdown</div>
      <div class="tds-sections-grid">
        <div v-for="s in sectionBreakdown" :key="s.section" class="tds-sec-card">
          <div class="tds-sec-label"><span class="tds-sec-badge">{{ s.section }}</span></div>
          <div class="tds-sec-count">{{ s.count }} transaction{{ s.count > 1 ? 's' : '' }}</div>
          <div class="tds-sec-amount">{{ fmtCur(s.amount) }}</div>
        </div>
      </div>
    </div>

    <div class="tds-card">
      <table class="tds-table tds-desktop-table">
        <thead><tr>
          <th @click="sort('name')" class="sortable">Voucher / Ref <span v-html="sortArrow('name')"></span></th>
          <th @click="sort('posting_date')" class="sortable">Date <span v-html="sortArrow('posting_date')"></span></th>
          <th>Party</th>
          <th>TDS Section</th>
          <th class="ta-r">Gross Amount</th>
          <th class="ta-r">TDS Rate %</th>
          <th class="ta-r">TDS Amount</th>
          <th class="ta-r">Net Payment</th>
          <th>Source</th>
          <th>Status</th>
          <th>Action</th>
        </tr></thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 8" :key="n"><td colspan="11"><div class="tds-shimmer"></div></td></tr>
          </template>
          <template v-else>
            <tr v-for="e in paginatedSorted" :key="(e.entry_name || e.name) + (e.tds_section||'')" class="tds-row">
              <td><span class="tds-code">{{ e.name }}</span></td>
              <td class="mono-sm text-muted">{{ fmtDate(e.posting_date) }}</td>
              <td>{{ e.party || '—' }}</td>
              <td><span class="tds-section-badge">{{ e.tds_section || '—' }}</span></td>
              <td class="ta-r mono-sm">{{ fmtCur(e.gross_amount) }}</td>
              <td class="ta-r mono-sm text-muted">{{ e.rate ? `${e.rate}%` : '—' }}</td>
              <td class="ta-r mono-sm red">{{ fmtCur(e.tds_amount) }}</td>
              <td class="ta-r mono-sm">{{ fmtCur(e.net_payment) }}</td>
              <td><span class="tds-source-badge" :class="e.source==='entry' ? 'tds-source-manual' : 'tds-source-bill'">{{ e.source === 'entry' ? 'Manual' : 'Bill' }}</span></td>
              <td>
                <span v-if="e.source==='entry'" class="tds-status-badge" :class="'tds-status-' + (e.status||'pending').toLowerCase()">{{ e.status || 'Pending' }}</span>
                <span v-else class="text-muted" style="font-size:11.5px">From PI</span>
              </td>
              <td>
                <button v-if="e.source==='entry' && e.status !== 'Deposited' && e.status !== 'Filed'" class="tds-act-btn" :disabled="!$canEdit('accounts')" :title="!$canEdit('accounts') ? 'Read-only access' : ''" @click="openDeposit(e)">Mark Deposited</button>
              </td>
            </tr>
            <tr v-if="!sorted.length"><td colspan="11" class="tds-empty">No TDS transactions found</td></tr>
          </template>
        </tbody>
      </table>

      <!-- Mobile cards (shown at ≤768px) -->
      <div class="tds-mobile-cards">
        <template v-if="loading">
          <div v-for="n in 6" :key="n" class="tds-mobile-card tds-mc--skeleton">
            <div class="tds-mc-shimmer" style="height:13px;width:55%;margin-bottom:8px"></div>
            <div class="tds-mc-shimmer" style="height:11px;width:40%;margin-bottom:6px"></div>
            <div class="tds-mc-shimmer" style="height:11px;width:65%"></div>
          </div>
        </template>
        <div v-else-if="!sorted.length" class="tds-mc-empty">
          <div style="font-size:32px;margin-bottom:8px">📋</div>
          <div>No TDS transactions found</div>
        </div>
        <template v-else>
          <div v-for="e in paginatedSorted" :key="(e.entry_name||e.name)+(e.tds_section||'')" class="tds-mobile-card">
            <div class="tds-mc-top">
              <span class="tds-mc-docno">{{ e.name }}</span>
              <span class="tds-source-badge" :class="e.source==='entry'?'tds-source-manual':'tds-source-bill'">{{ e.source==='entry'?'Manual':'Bill' }}</span>
            </div>
            <div class="tds-mc-mid">{{ e.party || '—' }}</div>
            <div class="tds-mc-meta">
              <span>{{ fmtDate(e.posting_date) }}{{ e.tds_section ? ' · ' + e.tds_section : '' }}</span>
              <span class="tds-mc-tds red">{{ fmtCur(e.tds_amount) }}</span>
            </div>
            <div class="tds-mc-footer" v-if="e.source==='entry' && e.status !== 'Deposited' && e.status !== 'Filed'">
              <button class="tds-act-btn" :disabled="!$canEdit('accounts')" @click.stop="openDeposit(e)">Mark Deposited</button>
            </div>
          </div>
        </template>
      </div><!-- end tds-mobile-cards -->

      <!-- Load More -->
      <div v-if="!loading && tdsHasMore" class="tds-load-more-wrap">
        <button class="tds-btn-ghost tds-load-more-btn" @click="loadMore">
          Load More ({{ sorted.length - tdsVisibleCount }} remaining)
        </button>
      </div>
    </div>
    <Teleport to="body">
      <div v-if="showEntryDrawer" class="tds-drawer-bg" @click.self="showEntryDrawer=false"></div>
      <div class="tds-drawer-panel" :class="{open:showEntryDrawer}">
        <div class="tds-drawer-header">
          <div>
            <div class="tds-drawer-title">New TDS Entry</div>
            <div class="tds-drawer-sub">Record a TDS deduction manually</div>
          </div>
          <button class="tds-drawer-close" @click="showEntryDrawer=false" v-html="icon('x',15)"></button>
        </div>
        <div class="tds-drawer-body">
          <div class="tds-form-grid">
            <div class="tds-form-field">
              <label class="tds-lbl">Date <span class="tds-req">*</span></label>
              <input v-model="entryForm.date" type="date" class="tds-fi" />
            </div>
            <div class="tds-form-field">
              <label class="tds-lbl">TDS Section <span class="tds-req">*</span></label>
              <select v-model="entryForm.section" class="tds-fi" @change="onSectionChange">
                <option value="">Select Section</option>
                <option>194C</option><option>194J</option><option>194A</option>
                <option>194H</option><option>194I</option><option>192</option>
                <option>195</option><option>Other</option>
              </select>
            </div>
            <div class="tds-form-field">
              <label class="tds-lbl">Party (Vendor) <span class="tds-req">*</span></label>
              <select v-model="entryForm.party" class="tds-fi" @change="onSupplierChange">
                <option value="">Select Supplier</option>
                <option v-for="s in suppliers" :key="s.name" :value="s.name">{{ s.supplier_name || s.name }}</option>
              </select>
            </div>
            <div class="tds-form-field">
              <label class="tds-lbl">PAN Number</label>
              <input v-model="entryForm.pan" class="tds-fi" placeholder="ABCDE1234F" @input="entryForm.pan=entryForm.pan.toUpperCase()" />
            </div>
            <div class="tds-form-field" style="grid-column:span 2">
              <label class="tds-lbl">Nature of Payment</label>
              <input v-model="entryForm.nature_of_payment" class="tds-fi" placeholder="e.g. Professional Services, Rent" />
            </div>
            <div class="tds-form-field">
              <label class="tds-lbl">Gross Amount <span class="tds-req">*</span></label>
              <input v-model.number="entryForm.amount" type="number" min="0" step="0.01" class="tds-fi" @input="calcEntryTds" />
            </div>
            <div class="tds-form-field">
              <label class="tds-lbl">TDS Rate (%)</label>
              <input v-model.number="entryForm.rate" type="number" min="0" max="100" step="0.01" class="tds-fi" @input="calcEntryTds" />
            </div>
            <div class="tds-form-field">
              <label class="tds-lbl">Surcharge (%)</label>
              <input v-model.number="entryForm.surcharge" type="number" min="0" step="0.01" class="tds-fi" @input="calcEntryTds" />
            </div>
            <div class="tds-form-field">
              <label class="tds-lbl">Cess (%)</label>
              <input v-model.number="entryForm.cess" type="number" min="0" step="0.01" class="tds-fi" @input="calcEntryTds" />
            </div>
            <div class="tds-form-field" style="grid-column:span 2">
              <label class="tds-lbl">TDS Amount (auto-calculated)</label>
              <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;padding:8px 12px;font-size:14px;font-weight:700;color:#dc2626;">
                {{ fmtCur(entryForm.tds_total) }}
              </div>
            </div>
            <div class="tds-form-field" style="grid-column:span 2">
              <label class="tds-lbl">Expense Account <span style="color:#9ca3af;font-weight:400">(optional — posts GL on save)</span></label>
              <select v-model="entryForm.expense_account" class="tds-fi">
                <option value="">— No GL posting —</option>
                <option v-for="a in expenseAccounts" :key="a.name" :value="a.name">{{ a.account_name || a.name }}</option>
              </select>
            </div>
            <div class="tds-form-field" style="grid-column:span 2">
              <label class="tds-lbl">Remarks</label>
              <textarea v-model="entryForm.remarks" class="tds-fi" rows="2" placeholder="Internal notes…"></textarea>
            </div>
          </div>
        </div>
        <div class="tds-drawer-footer">
          <button class="tds-btn-ghost" @click="showEntryDrawer=false">Cancel</button>
          <button class="tds-btn-primary" :disabled="entrySaving || !$canCreate('accounts')" :title="!$canCreate('accounts') ? 'Read-only access' : ''" @click="saveTDSEntry">
            <span v-if="entrySaving" v-html="icon('refresh',13)" style="animation:spin 1s linear infinite"></span>
            {{ entrySaving ? 'Saving…' : 'Save TDS Entry' }}
          </button>
        </div>
      </div>
    </Teleport>

    <!-- ── Mark Deposited Modal ── -->
    <Teleport to="body">
      <div v-if="showDepositModal" class="tds-drawer-bg" @click.self="showDepositModal=false"></div>
      <div v-if="showDepositModal" class="tds-modal">
        <div class="tds-modal-header">
          <span style="font-size:14px;font-weight:700;color:#111827">Mark TDS as Deposited</span>
          <button class="tds-drawer-close" @click="showDepositModal=false" v-html="icon('x',14)"></button>
        </div>
        <div style="padding:16px 20px;display:flex;flex-direction:column;gap:12px">
          <div>
            <label class="tds-lbl">Challan Number</label>
            <input v-model="depositForm.challan_no" class="tds-fi" placeholder="Challan reference number" />
          </div>
          <div>
            <label class="tds-lbl">Challan Date</label>
            <input v-model="depositForm.challan_date" type="date" class="tds-fi" />
          </div>
        </div>
        <div style="padding:12px 20px;display:flex;justify-content:flex-end;gap:8px;border-top:1px solid #f3f4f6">
          <button class="tds-btn-ghost" @click="showDepositModal=false">Cancel</button>
          <button class="tds-btn-primary" :disabled="depositSaving || !$canEdit('accounts')" :title="!$canEdit('accounts') ? 'Read-only access' : ''" @click="saveDeposit">
            {{ depositSaving ? 'Saving…' : 'Mark Deposited' }}
          </button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from "vue";
import { apiGET, apiPOST, apiList, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";
import { flt, fmtDate } from "../utils/format.js";

const TDS_RATES = { "194C": 1, "194J": 10, "194A": 10, "194H": 5, "194I": 10, "192": 0, "195": 20, "Other": 10 };

const { toast } = useToast();
const list = ref([]);
const loading = ref(false);
const search = ref("");
const periodFilter = ref("");
const sortCol = ref("posting_date");
const sortDir = ref("desc");
const noTdsNote = ref(false);
const expenseAccounts = ref([]);
const suppliers = ref([]);

// Entry drawer
const showEntryDrawer = ref(false);
const entrySaving = ref(false);
const entryForm = reactive({
  date: new Date().toISOString().slice(0, 10),
  section: "", party: "", party_name: "", pan: "", nature_of_payment: "",
  amount: 0, rate: 0, surcharge: 0, cess: 0, tds_total: 0,
  expense_account: "", remarks: "",
});

// Deposit modal
const showDepositModal = ref(false);
const depositSaving = ref(false);
const depositTarget = ref(null);
const depositForm = reactive({ challan_no: "", challan_date: "" });

const now = new Date();
function makePeriods() {
  const ps = [];
  for (let i = 0; i < 12; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const v = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    const l = d.toLocaleString("en-IN", { month: "long", year: "numeric" });
    ps.push({ v, l });
  }
  return ps;
}
const periods = makePeriods();

async function load() {
  loading.value = true;
  noTdsNote.value = false;
  try {
    const co = await resolveCompany();
    const params = { company: co };
    if (periodFilter.value) {
      const [yr, mo] = periodFilter.value.split("-");
      params.from_date = `${yr}-${mo}-01`;
      params.to_date   = `${yr}-${mo}-${new Date(+yr, +mo, 0).getDate()}`;
    }

    const [piRows, entryRows] = await Promise.all([
      apiGET("zoho_books_clone.db.queries.get_tds_transactions", params).catch(() => []),
      apiGET("zoho_books_clone.api.gst.get_tds_entries", params).catch(() => []),
    ]);

    const piNormalized = (Array.isArray(piRows) ? piRows : []).map(e => ({
      name: e.name,
      posting_date: e.posting_date,
      party: e.supplier_name || e.supplier || "",
      tds_section: e.tds_section || e.tax_type || "",
      gross_amount: flt(e.gross_amount),
      rate: e.rate,
      tds_amount: flt(e.tds_amount),
      net_payment: flt(e.net_payment),
      source: "bill",
      status: "",
      entry_name: null,
    }));

    const entryNormalized = (Array.isArray(entryRows) ? entryRows : []).map(e => ({
      name: e.voucher_no || e.name,
      posting_date: e.date,
      party: e.party_name || e.party || "",
      tds_section: e.section || "",
      gross_amount: flt(e.amount),
      rate: e.amount > 0 ? Math.round(flt(e.tds_total) / flt(e.amount) * 100 * 100) / 100 : 0,
      tds_amount: flt(e.tds_total),
      net_payment: flt(e.amount) - flt(e.tds_total),
      source: "entry",
      status: e.status || "Pending",
      entry_name: e.name,
    }));

    // Merge: deduplicate by voucher_no (entries already linked from bills via GL)
    const piVouchers = new Set(piNormalized.map(r => r.name).filter(Boolean));
    const uniqueEntries = entryNormalized.filter(r => !r.name || !piVouchers.has(r.name));
    list.value = [...piNormalized, ...uniqueEntries];

    if (!list.value.length) noTdsNote.value = true;
  } catch (e) {
    toast.error(e.message || "Failed to load TDS data");
  } finally {
    loading.value = false;
  }
}

async function loadExpenseAccounts() {
  try {
    const rows = await apiList("Account", {
      fields: ["name", "account_name"],
      filters: [["is_group", "=", 0], ["account_type", "=", "Expense"]],
      limit: 100,
    });
    expenseAccounts.value = rows || [];
  } catch { expenseAccounts.value = []; }
}

async function loadSuppliers() {
  try {
    const rows = await apiList("Supplier", {
      fields: ["name", "supplier_name"],
      filters: [["disabled", "=", 0]],
      limit: 100000,
    });
    suppliers.value = rows || [];
  } catch { suppliers.value = []; }
}

const totalTds   = computed(() => list.value.reduce((s, e) => s + flt(e.tds_amount), 0));
const totalGross = computed(() => list.value.reduce((s, e) => s + flt(e.gross_amount), 0));
const totalNet   = computed(() => list.value.reduce((s, e) => s + flt(e.net_payment), 0));

const sectionBreakdown = computed(() => {
  const map = {};
  list.value.forEach(e => {
    const sec = e.tds_section || "Unknown";
    if (!map[sec]) map[sec] = { section: sec, count: 0, amount: 0 };
    map[sec].count++;
    map[sec].amount += flt(e.tds_amount);
  });
  return Object.values(map).sort((a, b) => b.amount - a.amount);
});

const filtered = computed(() => {
  if (!search.value.trim()) return list.value;
  const q = search.value.toLowerCase();
  return list.value.filter(e =>
    (e.party || "").toLowerCase().includes(q) ||
    (e.tds_section || "").toLowerCase().includes(q)
  );
});

const sorted = computed(() => {
  const col = sortCol.value;
  return [...filtered.value].sort((a, b) => {
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

const TDS_PAGE_SIZE = 10;
const tdsVisibleCount = ref(TDS_PAGE_SIZE);
const paginatedSorted = computed(() => sorted.value.slice(0, tdsVisibleCount.value));
const tdsHasMore = computed(() => tdsVisibleCount.value < sorted.value.length);
function loadMore() { tdsVisibleCount.value += TDS_PAGE_SIZE; }

watch([search, periodFilter], () => { tdsVisibleCount.value = TDS_PAGE_SIZE; });

function openNewEntry() {
  Object.assign(entryForm, {
    date: new Date().toISOString().slice(0, 10),
    section: "", party: "", party_name: "", pan: "", nature_of_payment: "",
    amount: 0, rate: 0, surcharge: 0, cess: 0, tds_total: 0,
    expense_account: "", remarks: "",
  });
  if (!suppliers.value.length) loadSuppliers();
  showEntryDrawer.value = true;
}

function onSupplierChange() {
  const s = suppliers.value.find(s => s.name === entryForm.party);
  entryForm.party_name = s ? (s.supplier_name || s.name) : entryForm.party;
}

function onSectionChange() {
  entryForm.rate = TDS_RATES[entryForm.section] ?? 0;
  calcEntryTds();
}

function calcEntryTds() {
  entryForm.tds_total = Math.round(
    flt(entryForm.amount) * (flt(entryForm.rate) + flt(entryForm.surcharge) + flt(entryForm.cess)) / 100 * 100
  ) / 100;
}

async function saveTDSEntry() {
  if (!entryForm.section) return toast.error("TDS Section is required");
  if (!entryForm.party.trim()) return toast.error("Party name is required");
  if (!entryForm.amount || entryForm.amount <= 0) return toast.error("Gross amount must be positive");

  entrySaving.value = true;
  try {
    const co = await resolveCompany();
    await apiPOST("zoho_books_clone.api.gst.save_tds_entry", {
      data: JSON.stringify({ ...entryForm, company: co }),
    });
    toast.success("TDS Entry saved successfully");
    showEntryDrawer.value = false;
    await load();
  } catch (e) {
    toast.error(e.message || "Failed to save TDS entry");
  } finally {
    entrySaving.value = false;
  }
}

function openDeposit(entry) {
  depositTarget.value = entry;
  Object.assign(depositForm, { challan_no: entry.challan_no || "", challan_date: new Date().toISOString().slice(0, 10) });
  showDepositModal.value = true;
}

async function saveDeposit() {
  if (!depositTarget.value?.entry_name) return;
  depositSaving.value = true;
  try {
    await apiPOST("zoho_books_clone.api.gst.update_tds_entry_status", {
      entry_name: depositTarget.value.entry_name,
      status: "Deposited",
      challan_no: depositForm.challan_no,
      challan_date: depositForm.challan_date,
    });
    toast.success("TDS Entry marked as Deposited");
    showDepositModal.value = false;
    depositTarget.value = null;
    await load();
  } catch (e) {
    toast.error(e.message || "Failed to update status");
  } finally {
    depositSaving.value = false;
  }
}

function exportCSV() {
  const rows = [
    ["Voucher / Ref", "Date", "Party", "TDS Section", "Gross Amount", "TDS Rate %", "TDS Amount", "Net Payment", "Source", "Status"],
    ...sorted.value.map(e => [
      e.name, e.posting_date, e.party || "",
      e.tds_section || "",
      flt(e.gross_amount), e.rate || "",
      flt(e.tds_amount), flt(e.net_payment),
      e.source === "entry" ? "Manual" : "Bill",
      e.status || "",
    ]),
  ];
  const csv = rows.map(r => r.map(v => `"${String(v ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
  const a = document.createElement("a");
  a.href = "data:text/csv;charset=utf-8," + encodeURIComponent(csv);
  a.download = `TDS_${periodFilter.value || "all"}.csv`;
  a.click();
}

function fmtCur(v) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "OMR", minimumFractionDigits: 2 }).format(flt(v));
}

onMounted(() => { load(); loadExpenseAccounts(); loadSuppliers(); });
</script>

<style scoped>
.tds-page{display:flex;flex-direction:column;gap:16px;padding:24px;}
.tds-topbar{display:flex;flex-direction:column;gap:10px;}
.tds-topbar-row{display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px;}
.tds-title{font-size:20px;font-weight:800;color:#111827;}.tds-subtitle{font-size:12px;color:#6b7280;}
.tds-controls{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
.tds-search-wrap{display:flex;align-items:center;gap:6px;background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:6px 10px;}
.tds-search-input{border:none;background:transparent;outline:none;font:inherit;color:#111827;width:100%;font-size:13px;}
.tds-select{border:1px solid #e5e7eb;border-radius:8px;padding:7px 10px;font:inherit;font-size:13px;outline:none;background:#fff;color:#111827;}
.tds-btn-ghost{display:inline-flex;align-items:center;gap:6px;background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:8px 12px;font-size:13px;color:#374151;cursor:pointer;font-family:inherit;}
.tds-btn-ghost:hover:not(:disabled){background:#f9fafb;}.tds-btn-ghost:disabled{opacity:.5;cursor:not-allowed;}
.tds-btn-primary{display:inline-flex;align-items:center;gap:6px;background:#2563eb;border:none;border-radius:8px;padding:8px 14px;font-size:13px;font-weight:600;color:#fff;cursor:pointer;font-family:inherit;}
.tds-btn-primary:hover:not(:disabled){background:#1d4ed8;}.tds-btn-primary:disabled{opacity:.55;cursor:default;}
.tds-note{display:flex;align-items:flex-start;gap:8px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:12px 16px;font-size:12.5px;color:#1e40af;line-height:1.55;}
.tds-summary{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;}
.tds-sum-card{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:14px 16px;}
.tds-sum-lbl{font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px;}
.tds-sum-val{font-size:18px;font-weight:700;color:#111827;}
.blue{color:#2563eb!important;}.red{color:#dc2626!important;}
.tds-sections{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:14px 16px;}
.tds-sections-title{font-size:12px;font-weight:700;color:#374151;text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px;}
.tds-sections-grid{display:flex;gap:10px;flex-wrap:wrap;}
.tds-sec-card{background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:10px 14px;min-width:140px;}
.tds-sec-label{margin-bottom:4px;}
.tds-sec-badge{background:#eff6ff;color:#2563eb;border-radius:10px;padding:2px 10px;font-size:11.5px;font-weight:700;}
.tds-sec-count{font-size:11.5px;color:#6b7280;margin-top:4px;}
.tds-sec-amount{font-size:14px;font-weight:700;color:#dc2626;margin-top:2px;}
.tds-card{background:#fff;border:1px solid #e5e7eb;border-radius:10px;overflow:scroll;}
.tds-table{width:100%;border-collapse:collapse;font-size:13px;}
.tds-table th{background:#f9fafb;border-bottom:1px solid #e5e7eb;padding:10px 12px;font-size:11.5px;font-weight:600;color:#374151;text-align:left;white-space:nowrap;text-transform:uppercase;}
.tds-table th.sortable{cursor:pointer;user-select:none;}.tds-table th.sortable:hover{color:#2563eb;}
.ta-r{text-align:right!important;}
.tds-row td{padding:10px 12px;border-bottom:1px solid #f3f4f6;}
.tds-row:last-child td{border-bottom:none;}.tds-row:hover td{background:#f9fafb;}
.tds-code{font-size:12.5px;color:#2563eb;font-weight:600;}
.tds-section-badge{background:#eff6ff;color:#2563eb;padding:2px 8px;border-radius:10px;font-size:11.5px;font-weight:600;text-wrap-mode: nowrap;}
.tds-source-badge{padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;}
.tds-source-manual{background:#fef3c7;color:#92400e;}
.tds-source-bill{background:#f0fdf4;color:#166534;}
.tds-status-badge{padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;}
.tds-status-pending{background:#fef3c7;color:#92400e;}
.tds-status-deposited{background:#f0fdf4;color:#166534;}
.tds-status-filed{background:#eff6ff;color:#1d4ed8;}
.tds-act-btn{background:#fff;border:1px solid #e5e7eb;border-radius:6px;padding:4px 10px;font-size:11.5px;cursor:pointer;color:#374151;font-family:inherit;}
.tds-act-btn:hover{border-color:#2563eb;color:#2563eb;background:#eff6ff;}
.mono-sm{font-size:12.5px;}.text-muted{color:#6b7280;}
.tds-empty{text-align:center;color:#9ca3af;padding:48px!important;}
.tds-shimmer{height:13px;background:linear-gradient(90deg,#f3f4f6 25%,#e5e7eb 50%,#f3f4f6 75%);border-radius:4px;animation:shimmer 1.2s infinite;background-size:200% 100%;}
@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}
@keyframes spin{to{transform:rotate(360deg)}}
/* Drawer */
.tds-drawer-bg{position:fixed;inset:0;background:rgba(0,0,0,.35);z-index:999;}
.tds-drawer-panel{position:fixed;right:0;top:0;bottom:0;width:min(540px,96vw);background:#fff;box-shadow:-4px 0 24px rgba(0,0,0,.12);z-index:1000;display:flex;flex-direction:column;transform:translateX(100%);transition:transform .25s cubic-bezier(.4,0,.2,1);}
.tds-drawer-panel.open{transform:translateX(0);}
.tds-drawer-header{background:linear-gradient(135deg,#1e40af,#2563eb);padding:18px 24px;display:flex;align-items:flex-start;justify-content:space-between;flex-shrink:0;}
.tds-drawer-title{font-size:16px;font-weight:700;color:#fff;}
.tds-drawer-sub{font-size:12px;color:rgba(255,255,255,.8);margin-top:2px;}
.tds-drawer-close{background:none;border:none;color:rgba(255,255,255,.8);cursor:pointer;font-size:18px;line-height:1;padding:0;}
.tds-drawer-close:hover{color:#fff;}
.tds-drawer-body{flex:1;overflow-y:auto;padding:20px 24px;}
.tds-drawer-footer{padding:14px 24px;border-top:1px solid #f3f4f6;display:flex;justify-content:flex-end;gap:8px;flex-shrink:0;}
.tds-form-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
.tds-form-field{display:flex;flex-direction:column;gap:4px;}
.tds-lbl{font-size:11.5px;font-weight:600;color:#374151;}
.tds-req{color:#dc2626;}
.tds-fi{border:1px solid #d1d5db;border-radius:6px;padding:7px 10px;font-size:13px;font-family:inherit;outline:none;color:#111827;width:100%;box-sizing:border-box;}
.tds-fi:focus{border-color:#2563eb;box-shadow:0 0 0 3px #2563eb1a;}
/* Modal */
.tds-modal{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#fff;border-radius:12px;box-shadow:0 20px 60px rgba(0,0,0,.18);z-index:1001;width:min(420px,90vw);overflow:hidden;}
.tds-modal-header{display:flex;align-items:center;justify-content:space-between;padding:14px 20px;border-bottom:1px solid #f3f4f6;}

/* ── Load More ── */
.tds-load-more-wrap { display:flex; justify-content:center; padding:14px 16px; border-top:1px solid #f3f4f6; }
.tds-load-more-btn  { width:100%; max-width:320px; justify-content:center; font-weight:600; color:#2563eb; border-color:#bfdbfe; }
.tds-load-more-btn:hover { background:#eff6ff; border-color:#93c5fd; }

/* ── Mobile card defaults ── */
.tds-mobile-cards { display: none; }
.tds-desktop-table { display: table; }

@media (max-width: 768px) {
  .tds-summary     { grid-template-columns: repeat(2, 1fr); }
  .tds-drawer-panel { width: 100% !important; }

  /* Controls row: period select stretches, New Entry fills remaining */
  .tds-topbar-row { flex-direction: column; align-items: stretch; gap: 8px; }
  .tds-controls { width: 100%; }
  .tds-select { flex: 1 1 auto; min-width: 0; }
  .tds-controls .tds-btn-primary { flex: 1 1 auto; justify-content: center; }

  .tds-desktop-table { display: none !important; }
  .tds-mobile-cards { display: flex; flex-direction: column; gap: 0; background: #f8fafc; }
  .tds-mobile-card { background: #fff; border-bottom: 1px solid #e5e7eb; padding: 12px 14px; transition: background .12s; }
  .tds-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .tds-mc-docno { font-size: 12px; font-weight: 700; color: #2563eb; }
  .tds-mc-mid { font-size: 13.5px; font-weight: 600; color: #1a1d23; margin-bottom: 4px; }
  .tds-mc-meta { display: flex; justify-content: space-between; font-size: 12px; color: #868e96; margin-bottom: 8px; }
  .tds-mc-tds { font-weight: 700; }
  .tds-mc-footer { display: flex; gap: 6px; }
  .tds-mc--skeleton { pointer-events: none; }
  .tds-mc-shimmer { border-radius: 6px; background: linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size: 200% 100%; animation: tds-mc-sh 1.4s infinite; }
  @keyframes tds-mc-sh { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
  .tds-mc-empty { text-align: center; padding: 32px 16px; color: #868e96; font-size: 13px; }
}
@media (max-width: 480px) {
  .tds-sections-grid{justify-content:space-evenly;}
  .tds-page    { padding: 12px; gap: 12px; }
  .tds-summary { grid-template-columns: 1fr 1fr; }
  .tds-form-grid { grid-template-columns: 1fr !important; }
}
</style>