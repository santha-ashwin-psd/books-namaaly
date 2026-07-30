<template>
  <div class="ba-page">
    <!-- ===================== ACTION BAR -->
    <div class="ba-actions">
      <div class="ba-search-wrap">
        <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
        <input v-model="search" placeholder="Search bank accounts…" class="ba-search-input" />
      </div>
      <div class="ba-primary-btn">
        <button class="ba-btn-ghost" @click="load"><span v-html="icon('refresh',14)"></span></button>
        <button class="ba-btn-primary" @click="openNew" :disabled="!$canCreate('banking')" :title="!$canCreate('banking') ? 'Read-only access' : ''"><span v-html="icon('plus',13)"></span> New Account</button>
      </div>
    </div>

    <!-- ===================== SUMMARY STRIP -->
    <SummaryStrip v-if="!loading && list.length" :cards="[
      { label: 'Total Accounts', tone: 'default', value: list.length },
      { label: 'Total Balance', tone: 'accent', value: fmtCur(totalBalance), valueClass: totalBalance>=0?'green':'red' },
      { label: 'Avg Reconciled', tone: avgReconciled>=80?'success':'warn', value: avgReconciled+'%', valueClass: avgReconciled>=80?'green':'orange' },
      { label: 'Transactions', tone: 'info', value: totalTxns, valueClass: 'blue' },
    ]" />

    <!-- ===================== FILTER BAR -->
    <div v-if="!loading && list.length" class="ba-filterbar">
      <div class="ba-filter-pills">
        <button v-for="t in typeTabs" :key="t.key" class="ba-fpill" :class="{active:typeFilter===t.key}" @click="typeFilter=t.key">
          {{ t.label }} <span class="ba-fpill-count">{{ t.count }}</span>
        </button>
      </div>
      <div class="ba-filter-meta">
        <span class="ba-filter-result">{{ filtered.length }} of {{ list.length }} {{ list.length===1?'account':'accounts' }}</span>
        <div class="ba-sort-wrap">
          <span v-html="icon('chart',13)" style="color:#94a3b8"></span>
          <select v-model="sortKey" class="ba-sort-select">
            <option value="name">Name (A–Z)</option>
            <option value="balance_desc">Balance (high → low)</option>
            <option value="balance_asc">Balance (low → high)</option>
            <option value="recon">Reconciled %</option>
            <option value="txns">Transactions</option>
          </select>
        </div>
      </div>
    </div>

    <!-- ===================== CARD GRID -->
    <div class="ba-grid" v-if="!loading && filtered.length">
      <div v-for="acc in filtered" :key="acc.name" class="ba-card" :class="{'is-default':acc.is_default,'menu-open':openMenuName===acc.name}" @click="openView(acc)">
        <div class="ba-card-top">
          <div class="ba-card-icon"><span v-html="icon('bank',20)"></span></div>
          <div class="ba-card-top-right">
            <span v-if="acc.is_default" class="ba-default-pill"><span v-html="icon('sparkle',11)"></span> Default</span>
            <button class="ba-kebab" @click.stop="toggleMenu(acc.name)" aria-label="Account actions">
              <span class="ba-kebab-dots"></span>
            </button>
          </div>
        </div>

        <div class="ba-card-name">{{ acc.account_name||acc.name }}</div>
        <div class="ba-card-bank text-muted">{{ acc.bank_name||'—' }}<span v-if="acc.account_type"> · {{ acc.account_type }}</span></div>
        <div class="ba-card-num mono-sm">{{ acc.account_number ? maskAcct(acc.account_number) : 'No account number' }}</div>

        <div class="ba-balance-block">
          <div class="ba-balance-lbl">Balance</div>
          <div class="ba-balance-val" :class="flt(acc.balance)>=0?'pos':'neg'">{{ fmtCur(acc.balance, acc.currency) }}</div>
        </div>

        <div class="ba-card-footer">
          <div class="ba-recon" :title="`${acc.reconcile_pct||0}% of ${acc.txn_count||0} transactions reconciled`">
            <div class="ba-recon-bar"><div class="ba-recon-fill" :style="{width:(acc.reconcile_pct||0)+'%'}" :class="reconClass(acc.reconcile_pct)"></div></div>
            <span class="ba-recon-lbl">{{ acc.reconcile_pct||0 }}% reconciled</span>
          </div>
          <span class="ba-txn-chip">{{ acc.txn_count||0 }} txns</span>
        </div>

        <!-- kebab dropdown -->
        <div v-if="openMenuName===acc.name" class="ba-menu" @click.stop>
          <button class="ba-menu-item" @click="openView(acc)"><span v-html="icon('eye',13)"></span> View</button>
          <button class="ba-menu-item" :disabled="!$canEdit('banking')" :title="!$canEdit('banking') ? 'Read-only access' : ''" @click="openEdit(acc)"><span v-html="icon('edit',13)"></span> Edit</button>
          <button v-if="!acc.is_default" class="ba-menu-item" :disabled="!$canEdit('banking')" :title="!$canEdit('banking') ? 'Read-only access' : ''" @click="setDefault(acc)"><span v-html="icon('sparkle',13)"></span> Set as Default</button>
          <div class="ba-menu-sep"></div>
          <button class="ba-menu-item danger" :disabled="!$canDelete('banking')" :title="!$canDelete('banking') ? 'Not permitted' : ''" @click="confirmDelete(acc)"><span v-html="icon('trash',13)"></span> Delete</button>
        </div>
      </div>
    </div>

    <!-- ===================== EMPTY STATE -->
    <div v-else-if="!loading" class="ba-empty-wrap">
      <div class="ba-empty-card">
        <span v-html="icon('bank',32)" style="color:#cbd5e1;display:block;margin:0 auto 12px"></span>
        <div style="font-weight:600;color:#374151;margin-bottom:4px">{{ hasFilters ? 'No matching accounts' : 'No bank accounts yet' }}</div>
        <div style="color:#9ca3af;font-size:12.5px;margin-bottom:16px">{{ hasFilters ? 'Try a different filter or search term' : 'Add your first bank account to get started' }}</div>
        <button v-if="hasFilters" class="ba-btn-ghost" @click="clearFilters">Clear filters</button>
        <button v-else class="ba-btn-primary" :disabled="!$canCreate('banking')" :title="!$canCreate('banking') ? 'Read-only access' : ''" @click="openNew"><span v-html="icon('plus',13)"></span> Add Account</button>
      </div>
    </div>

    <!-- ===================== SKELETON -->
    <div v-else class="ba-grid">
      <div v-for="n in 4" :key="n" class="ba-card-skeleton"><div class="ba-shimmer" style="height:140px"></div></div>
    </div>

    <!-- backdrop to dismiss kebab menu -->
    <div v-if="openMenuName" class="ba-menu-backdrop" @click="openMenuName=''"></div>

    <!-- ===================== CREATE / EDIT DRAWER -->
    <div v-if="drawerOpen" class="ba-overlay" @click.self="!drawerSaving && (drawerOpen=false)"></div>
    <div class="ba-drawer" :class="{open:drawerOpen}">
      <div class="ba-dheader" :class="editingName?'edit':''">
        <div class="ba-dheader-left">
          <div class="ba-dheader-ico" :class="editingName?'edit':''"><span v-html="icon('bank',20)"></span></div>
          <div>
            <div class="ba-dheader-title">{{ editingName?'Edit Bank Account':'New Bank Account' }}</div>
            <div class="ba-dheader-sub">{{ editingName ? editingName : 'Add an account and its ledger' }}</div>
          </div>
        </div>
        <button class="ba-dclose" @click="drawerOpen=false"><span v-html="icon('x',16)"></span></button>
      </div>

      <div class="ba-dbody">
        <!-- Account Details -->
        <div class="ba-section-hdr"><span v-html="icon('building',13)"></span> Account Details</div>
        <div class="ba-fields-grid">
          <div class="ba-field" style="grid-column:1/-1">
            <label class="ba-label">Account Name <span class="req">*</span></label>
            <input v-model="form.account_name" class="ba-input" placeholder="e.g. HDFC Current Account" />
          </div>
          <div class="ba-field">
            <label class="ba-label">Bank <span class="req">*</span></label>
            <input v-model="form.bank_name" class="ba-input" placeholder="e.g. HDFC Bank" />
          </div>
          <div class="ba-field">
            <label class="ba-label">Account Type</label>
            <select v-model="form.account_type" class="ba-select">
              <option value="Savings">Savings</option>
              <option value="Current">Current</option>
              <option value="Cash">Cash</option>
              <option value="Overdraft">Overdraft</option>
              <option value="Credit Card">Credit Card</option>
            </select>
          </div>
          <div class="ba-field" style="grid-column:1/-1">
            <label class="ba-label">Account Holder Name</label>
            <input v-model="form.account_holder_name" class="ba-input" placeholder="As printed on the account" />
          </div>
        </div>

        <!-- Bank Identifiers -->
        <div class="ba-section-hdr"><span v-html="icon('hash',13)"></span> Bank Identifiers</div>
        <div class="ba-fields-grid">
          <div class="ba-field">
            <label class="ba-label">Account Number</label>
            <input v-model="form.account_number" class="ba-input" placeholder="Account number" />
          </div>
          <div class="ba-field">
            <label class="ba-label">IFSC Code</label>
            <input v-model="form.ifsc_code" class="ba-input" placeholder="e.g. HDFC0001234" />
          </div>
          <div class="ba-field">
            <label class="ba-label">MICR Code</label>
            <input v-model="form.micr_code" class="ba-input" placeholder="9-digit MICR" />
          </div>
          <div class="ba-field">
            <label class="ba-label">Branch</label>
            <input v-model="form.branch" class="ba-input" placeholder="Branch name" />
          </div>
        </div>

        <!-- Accounting -->
        <div class="ba-section-hdr"><span v-html="icon('ledger',13)"></span> Accounting</div>
        <div class="ba-fields-grid">
          <div class="ba-field" style="grid-column:1/-1">
            <label class="ba-label">GL Account</label>
            <SearchableSelect v-model="form.gl_account" :options="glAccounts" placeholder="Link to chart of accounts…" />
            <div class="ba-hint">Leave blank — a ledger account will be created automatically.</div>
          </div>
          <div class="ba-field">
            <label class="ba-label">Opening Balance</label>
            <input v-model.number="form.opening_balance" type="number" step="0.01" class="ba-input" placeholder="0.00" :disabled="!!editingName" />
            <div v-if="editingName" class="ba-hint">Opening balance is locked after creation.</div>
          </div>
          <div class="ba-field" style="grid-column:1/-1">
            <label class="ba-check"><input type="checkbox" v-model="form.is_default" /> Set as default account</label>
          </div>
        </div>
      </div>

      <div class="ba-dfooter">
        <button class="ba-btn-ghost" @click="drawerOpen=false">Cancel</button>
        <button class="ba-btn-primary" :disabled="drawerSaving" @click="saveAccount">
          <span v-html="icon('save',13)"></span> {{ drawerSaving?'Saving…':'Save Account' }}
        </button>
      </div>
    </div>

    <!-- ===================== VIEW DRAWER -->
    <div v-if="viewOpen" class="ba-overlay" @click.self="viewOpen=false"></div>
    <div class="ba-drawer ba-view-drawer" :class="{open:viewOpen}">
      <template v-if="viewDoc">
        <div class="ba-view-head">
          <button class="ba-dclose ba-vclose" @click="viewOpen=false"><span v-html="icon('x',16)"></span></button>
          <div class="ba-view-top">
            <div class="ba-view-icon"><span v-html="icon('bank',24)"></span></div>
            <div>
              <div class="ba-view-name">{{ viewDoc.account_name||viewDoc.name }}</div>
              <div class="ba-view-sub">{{ viewDoc.bank_name||'—' }}<span v-if="viewDoc.account_type"> · {{ viewDoc.account_type }}</span></div>
            </div>
            <span v-if="viewDoc.is_default" class="ba-default-pill light"><span v-html="icon('sparkle',11)"></span> Default</span>
          </div>
          <div class="ba-view-balance">
            <div>
              <div class="ba-vb-lbl">Current Balance</div>
              <div class="ba-vb-val" :class="flt(viewDoc.balance)>=0?'pos':'neg'">{{ fmtCur(viewDoc.balance, viewDoc.currency) }}</div>
            </div>
            <div class="ba-vb-recon">
              <div class="ba-vb-lbl">Reconciled</div>
              <div class="ba-vb-pct">{{ viewDoc.reconcile_pct||0 }}%</div>
              <div class="ba-vb-txn">{{ viewDoc.txn_count||0 }} transactions</div>
            </div>
          </div>
        </div>

        <div class="ba-dbody">
          <div class="ba-section-hdr"><span v-html="icon('info',13)"></span> Details</div>
          <div class="ba-meta-grid">
            <div><div class="ba-meta-lbl">Account No</div><div class="mono-sm">{{ viewDoc.account_number||'—' }}</div></div>
            <div><div class="ba-meta-lbl">IFSC</div><div class="mono-sm">{{ viewDoc.ifsc_code||'—' }}</div></div>
            <div><div class="ba-meta-lbl">MICR</div><div class="mono-sm">{{ viewDoc.micr_code||'—' }}</div></div>
            <div><div class="ba-meta-lbl">Branch</div><div>{{ viewDoc.branch||'—' }}</div></div>
            <div><div class="ba-meta-lbl">Holder</div><div>{{ viewDoc.account_holder_name||'—' }}</div></div>
            <div><div class="ba-meta-lbl">Opening Balance</div><div class="mono-sm">{{ fmtCur(viewDoc.opening_balance, viewDoc.currency) }}</div></div>
            <div style="grid-column:1/-1"><div class="ba-meta-lbl">GL Account</div><div>{{ glAccountLabel(viewDoc.gl_account) }}</div></div>
          </div>

          <div class="ba-section-hdr"><span v-html="icon('grid',13)"></span> Quick Actions</div>
          <div class="ba-quick-grid">
            <button class="ba-quick" @click="goTransactions(viewDoc)"><span v-html="icon('ledger',16)"></span> Transactions</button>
            <button class="ba-quick" @click="goReconcile(viewDoc)"><span v-html="icon('balance',16)"></span> Reconcile</button>
            <button class="ba-quick" @click="goTransfer(viewDoc)"><span v-html="icon('repeat',16)"></span> Transfer</button>
          </div>
        </div>

        <div class="ba-dfooter">
          <button class="ba-btn-danger-ghost" :disabled="!$canDelete('banking')" :title="!$canDelete('banking') ? 'Not permitted' : ''" @click="confirmDelete(viewDoc)"><span v-html="icon('trash',13)"></span> Delete</button>
          <div style="margin-left:auto;display:flex;gap:8px">
            <button class="ba-btn-ghost" @click="viewOpen=false">Close</button>
            <button class="ba-btn-primary" :disabled="!$canEdit('banking')" :title="!$canEdit('banking') ? 'Read-only access' : ''" @click="openEdit(viewDoc)"><span v-html="icon('edit',13)"></span> Edit</button>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { apiGET, apiPOST, apiList, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { useConfirm } from "../composables/useConfirm.js";
import { useRouter } from "vue-router";
import { icon } from "../utils/icons.js";
import { flt } from "../utils/format.js";
import SearchableSelect from "../components/SearchableSelect.vue";
import SummaryStrip from "../components/SummaryStrip.vue";

const { toast } = useToast();
const { confirm } = useConfirm();
const router = useRouter();

const list = ref([]), loading = ref(false), search = ref("");
const typeFilter = ref("all"), sortKey = ref("name");
const drawerOpen = ref(false), drawerSaving = ref(false), editingName = ref("");
const viewOpen = ref(false), viewDoc = ref(null);
const glAccounts = ref([]);
const glAccountLabelCache = ref({});
function glAccountLabel(name){
  if(!name) return '—';
  const opt = glAccounts.value.find(o=>o.value===name);
  if(opt) return opt.label;
  if(glAccountLabelCache.value[name]) return glAccountLabelCache.value[name];
  apiList("Account", { fields:["name","account_name"], filters:[["name","=",name]], limit:1 })
    .then(rows => { glAccountLabelCache.value[name] = rows?.[0]?.account_name || name; })
    .catch(() => { glAccountLabelCache.value[name] = name; });
  return name;
}
const openMenuName = ref("");

const form = reactive({
  account_name: "", bank_name: "", account_type: "Current", account_holder_name: "",
  account_number: "", ifsc_code: "", micr_code: "", branch: "",
  gl_account: "", currency: "INR", opening_balance: 0, is_default: false,
});

async function load() {
  loading.value = true;
  try {
    const co = await resolveCompany();
    const r = await apiGET("zoho_books_clone.api.banking.get_bank_accounts_with_balances", { company: co });
    list.value = Array.isArray(r) ? r : (r?.message || []);
  } catch (e) {
    toast.error(e.message || "Failed to load bank accounts");
  } finally {
    loading.value = false;
  }
}

const typeTabs = computed(() => {
  const counts = {};
  for (const a of list.value) {
    const t = a.account_type || "Other";
    counts[t] = (counts[t] || 0) + 1;
  }
  const tabs = [{ key: "all", label: "All", count: list.value.length }];
  for (const t of Object.keys(counts).sort()) tabs.push({ key: t, label: t, count: counts[t] });
  return tabs;
});

const filtered = computed(() => {
  let r = list.value;
  if (typeFilter.value !== "all") {
    r = r.filter(a => (a.account_type || "Other") === typeFilter.value);
  }
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    r = r.filter(a =>
      (a.account_name || a.name || "").toLowerCase().includes(q) ||
      (a.bank_name || "").toLowerCase().includes(q));
  }
  const s = sortKey.value;
  return [...r].sort((a, b) => {
    if (s === "balance_desc") return flt(b.balance) - flt(a.balance);
    if (s === "balance_asc")  return flt(a.balance) - flt(b.balance);
    if (s === "recon")        return (b.reconcile_pct || 0) - (a.reconcile_pct || 0);
    if (s === "txns")         return (b.txn_count || 0) - (a.txn_count || 0);
    return (a.account_name || a.name || "").localeCompare(b.account_name || b.name || "");
  });
});

const totalBalance  = computed(() => list.value.reduce((s, a) => s + flt(a.balance), 0));
const totalTxns     = computed(() => list.value.reduce((s, a) => s + (a.txn_count || 0), 0));
const avgReconciled = computed(() => {
  if (!list.value.length) return 0;
  return Math.round(list.value.reduce((s, a) => s + (a.reconcile_pct || 0), 0) / list.value.length);
});

const hasFilters = computed(() => typeFilter.value !== "all" || !!search.value.trim());
function clearFilters() { typeFilter.value = "all"; search.value = ""; }
function reconClass(pct) { return (pct || 0) >= 80 ? "high" : (pct || 0) >= 40 ? "mid" : "low"; }
function maskAcct(n) { if (!n || n.length < 4) return n; return "•".repeat(Math.max(0, n.length - 4)) + n.slice(-4); }
function fmtCur(v, cur) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: cur || "INR", minimumFractionDigits: 2 }).format(flt(v));
}

function toggleMenu(name) { openMenuName.value = openMenuName.value === name ? "" : name; }

function resetForm() {
  Object.assign(form, {
    account_name: "", bank_name: "", account_type: "Current", account_holder_name: "",
    account_number: "", ifsc_code: "", micr_code: "", branch: "",
    gl_account: "", currency: "INR", opening_balance: 0, is_default: false,
  });
}

function openNew() {
  openMenuName.value = "";
  editingName.value = "";
  resetForm();
  glAccounts.value = [];
  drawerOpen.value = true;
  fetchGLAccounts();
}

async function openEdit(a) {
  openMenuName.value = "";
  viewOpen.value = false;
  editingName.value = a.name;
  // Pull the full doc so branch/holder/micr/currency prefill correctly.
  const full = await fetchFull(a.name) || a;
  Object.assign(form, {
    account_name: full.account_name || "", bank_name: full.bank_name || "",
    account_type: full.account_type || "Current", account_holder_name: full.account_holder_name || "",
    account_number: full.account_number || "", ifsc_code: full.ifsc_code || "",
    micr_code: full.micr_code || "", branch: full.branch || "",
    gl_account: full.gl_account || "", currency: full.currency || "INR",
    opening_balance: flt(full.opening_balance), is_default: !!full.is_default,
  });
  glAccounts.value = [];
  drawerOpen.value = true;
  fetchGLAccounts();
}

async function openView(a) {
  openMenuName.value = "";
  viewDoc.value = a;            // show immediately with list data
  viewOpen.value = true;
  const full = await fetchFull(a.name);
  if (full) viewDoc.value = { ...a, ...full };
}

async function fetchFull(name) {
  try {
    const r = await apiGET("zoho_books_clone.api.banking.get_bank_account", { name });
    return r?.message || r || null;
  } catch { return null; }
}

async function fetchGLAccounts(q = "") {
  try {
    const co = await resolveCompany();
    const r = await apiList("Account", {
      fields: ["name", "account_name"],
      filters: [["account_type", "in", ["Bank", "Cash"]], ["company", "=", co], ["is_group", "=", 0],
        ...(q ? [["name", "like", `%${q}%`]] : [])],
      limit: 20,
    });
    glAccounts.value = r.map(x => ({ label: x.account_name || x.name, value: x.name }));
  } catch { glAccounts.value = []; }
}

async function saveAccount() {
  if (!form.account_name.trim()) return toast.error("Account name is required");
  if (!form.bank_name.trim()) return toast.error("Bank name is required");
  drawerSaving.value = true;
  try {
    const co = await resolveCompany();
    const payload = {
      account_name: form.account_name, bank_name: form.bank_name,
      account_type: form.account_type, account_holder_name: form.account_holder_name || "",
      account_number: form.account_number || "", ifsc_code: form.ifsc_code || "",
      micr_code: form.micr_code || "", branch: form.branch || "",
      gl_account: form.gl_account || "", currency: form.currency || "INR",
      is_default: form.is_default ? 1 : 0, company: co,
      opening_balance: flt(form.opening_balance),
    };
    if (editingName.value) payload.existing_name = editingName.value;
    const saved = await apiPOST("zoho_books_clone.api.banking.save_bank_account", payload,
      { module: "banking", action: editingName.value ? "edit" : "create" });
    const nm = saved?.message?.name || saved?.name || form.account_name;
    toast.success(`Bank account ${nm} saved`);
    drawerOpen.value = false;
    await load();
  } catch (e) {
    toast.error(e.message || "Failed to save bank account");
  } finally {
    drawerSaving.value = false;
  }
}

async function setDefault(a) {
  openMenuName.value = "";
  try {
    const full = await fetchFull(a.name) || a;
    await apiPOST("zoho_books_clone.api.banking.save_bank_account", {
      existing_name: a.name,
      account_name: full.account_name || a.account_name, bank_name: full.bank_name || "",
      account_type: full.account_type || "Current", account_holder_name: full.account_holder_name || "",
      account_number: full.account_number || "", ifsc_code: full.ifsc_code || "",
      micr_code: full.micr_code || "", branch: full.branch || "",
      gl_account: full.gl_account || "", currency: full.currency || "INR",
      is_default: 1, company: full.company || (await resolveCompany()),
      opening_balance: flt(full.opening_balance),
    }, { module: "banking", action: "edit" });
    toast.success(`${a.account_name || a.name} set as default`);
    await load();
  } catch (e) {
    toast.error(e.message || "Failed to set default");
  }
}

async function confirmDelete(a) {
  openMenuName.value = "";
  const ok = await confirm({
    title: "Delete bank account?",
    body: `This permanently deletes "${a.account_name || a.name}" and all ${a.txn_count || 0} linked transactions and their ledger entries. This cannot be undone.`,
    okLabel: "Delete Account",
    okStyle: "danger",
  });
  if (!ok) return;
  try {
    await apiPOST("zoho_books_clone.api.banking.delete_bank_account", { name: a.name },
      { module: "banking", action: "delete" });
    toast.success(`${a.account_name || a.name} deleted`);
    viewOpen.value = false;
    await load();
  } catch (e) {
    toast.error(e.message || "Failed to delete account");
  }
}

function goTransactions(a) { router.push({ name: "banking-transactions", query: { account: a.name } }); }
function goReconcile(a)    { router.push({ name: "banking-reconciliation", query: { account: a.name } }); }
function goTransfer(a)     { router.push({ name: "banking-transfers", query: { from: a.name } }); }

onMounted(load);
</script>

<style scoped>
.ba-page{display:flex;flex-direction:column;gap:16px;padding:24px;}
.ba-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
.ba-search-wrap{display:flex;align-items:center;gap:8px;background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:6px 12px;min-width:240px;}
.ba-search-input{border:none;background:transparent;outline:none;font:inherit;color:#111827;width:100%;font-size:13px;}
.ba-btn-primary{display:inline-flex;align-items:center;gap:6px;background:#2563eb;color:#fff;border:none;border-radius:8px;padding:8px 14px;font-size:13px;font-weight:600;cursor:pointer;transition:background .15s;}
.ba-btn-primary:hover{background:#1d4ed8;}.ba-btn-primary:disabled{opacity:.5;cursor:not-allowed;}
.ba-btn-ghost{display:inline-flex;align-items:center;gap:6px;background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:8px 12px;font-size:13px;color:#374151;cursor:pointer;}
.ba-btn-ghost:hover{background:#f9fafb;}
.ba-btn-danger-ghost{display:inline-flex;align-items:center;gap:6px;background:#fff;border:1px solid #fecaca;border-radius:8px;padding:8px 12px;font-size:13px;color:#dc2626;cursor:pointer;}
.ba-btn-danger-ghost:hover{background:#fef2f2;}

/* ── Filter bar (modern segmented control) ─────────────── */
.ba-filterbar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;}
.ba-filter-pills{display:inline-flex;align-items:center;gap:3px;background:#eef2f7;border:1px solid #e2e8f0;border-radius:12px;padding:4px;}
.ba-fpill{display:inline-flex;align-items:center;gap:7px;padding:7px 14px;border-radius:9px;font-size:12.5px;font-weight:600;border:none;background:transparent;color:#64748b;cursor:pointer;font-family:inherit;transition:color .15s,background .15s,box-shadow .15s;}
.ba-fpill:hover:not(.active){color:#334155;}
.ba-fpill.active{background:#fff;color:#1d4ed8;box-shadow:0 1px 2px rgba(15,23,42,.08),0 0 0 1px rgba(37,99,235,.08);}
.ba-fpill-count{display:inline-flex;align-items:center;justify-content:center;min-width:19px;height:18px;padding:0 6px;border-radius:9px;background:rgba(100,116,139,.16);color:#64748b;font-size:10.5px;font-weight:700;line-height:1;}
.ba-fpill.active .ba-fpill-count{background:#dbeafe;color:#1d4ed8;}
.ba-filter-meta{display:flex;align-items:center;gap:14px;}
.ba-filter-result{font-size:12px;color:#94a3b8;font-weight:600;white-space:nowrap;}
.ba-sort-wrap{display:inline-flex;align-items:center;gap:7px;background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:6px 12px;transition:border-color .15s,box-shadow .15s;}
.ba-sort-wrap:focus-within{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.1);}
.ba-sort-select{border:none;background:transparent;font:inherit;font-size:12.5px;font-weight:600;color:#334155;outline:none;cursor:pointer;padding-right:2px;}

/* ── Cards ─────────────────────────────────────────────── */
.ba-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(228px,1fr));gap:14px;}
.ba-card{position:relative;background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:14px;cursor:pointer;transition:box-shadow .15s,border-color .15s,transform .15s;}
.ba-card:hover{box-shadow:0 6px 20px rgba(15,23,42,.08);border-color:#bfdbfe;transform:translateY(-1px);}
.ba-card.is-default{border-color:#bfdbfe;background:linear-gradient(160deg,#f5f9ff 0%,#fff 55%);}
/* While its menu is open, lift the card above siblings so the dropdown is fully
   clickable, and freeze the hover transform so the menu doesn't drift. */
.ba-card.menu-open{z-index:40;transform:none;box-shadow:0 8px 28px rgba(15,23,42,.12);border-color:#bfdbfe;}
.ba-card-top{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:10px;}
.ba-card-icon{width:34px;height:34px;background:#eff6ff;border-radius:9px;display:flex;align-items:center;justify-content:center;color:#2563eb;}
.ba-card-icon :deep(svg){width:16px;height:16px;}
.ba-card-top-right{display:flex;align-items:center;gap:5px;}
.ba-default-pill{display:inline-flex;align-items:center;gap:4px;background:#dbeafe;color:#1d4ed8;border-radius:20px;padding:2px 8px;font-size:9.5px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;}
.ba-default-pill.light{background:rgba(255,255,255,.85);color:#1d4ed8;}
.ba-kebab{width:26px;height:26px;border:1px solid transparent;border-radius:7px;background:transparent;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;}
.ba-kebab:hover{background:#f1f5f9;border-color:#e5e7eb;}
.ba-kebab-dots,.ba-kebab-dots::before,.ba-kebab-dots::after{width:3px;height:3px;border-radius:50%;background:#64748b;display:block;}
.ba-kebab-dots{position:relative;}
.ba-kebab-dots::before,.ba-kebab-dots::after{content:"";position:absolute;left:0;}
.ba-kebab-dots::before{top:-5px;}.ba-kebab-dots::after{top:5px;}
.ba-card-name{font-size:13.5px;font-weight:700;color:#0f172a;margin-bottom:1px;line-height:1.25;}
.ba-card-bank{font-size:11.5px;margin-bottom:5px;}
.ba-card-num{font-size:12px;color:#475569;letter-spacing:.06em;margin-bottom:10px;}
.ba-balance-block{padding:9px 0;border-top:1px dashed #e5e7eb;}
.ba-balance-lbl{font-size:9.5px;color:#94a3b8;text-transform:uppercase;letter-spacing:.06em;font-weight:600;margin-bottom:1px;}
.ba-balance-val{font-size:18px;font-weight:800;letter-spacing:-.01em;}
.ba-balance-val.pos{color:#0f172a;}.ba-balance-val.neg{color:#dc2626;}
.ba-card-footer{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:6px;padding-top:9px;border-top:1px solid #f1f5f9;}
.ba-recon{display:flex;flex-direction:column;gap:4px;flex:1;min-width:0;}
.ba-recon-bar{height:5px;border-radius:4px;background:#eef2f7;overflow:hidden;}
.ba-recon-fill{height:100%;border-radius:4px;transition:width .3s;}
.ba-recon-fill.high{background:#16a34a;}.ba-recon-fill.mid{background:#f59e0b;}.ba-recon-fill.low{background:#cbd5e1;}
.ba-recon-lbl{font-size:9.5px;color:#94a3b8;font-weight:600;}
.ba-txn-chip{flex-shrink:0;background:#f1f5f9;color:#475569;border-radius:20px;padding:2px 9px;font-size:10px;font-weight:600;}

/* kebab dropdown */
.ba-menu{position:absolute;top:52px;right:14px;z-index:60;cursor:default;background:#fff;border:1px solid #e5e7eb;border-radius:10px;box-shadow:0 12px 32px rgba(15,23,42,.14);padding:6px;min-width:168px;}
.ba-menu-item{display:flex;align-items:center;gap:9px;width:100%;background:transparent;border:none;border-radius:7px;padding:8px 10px;font:inherit;font-size:13px;color:#334155;cursor:pointer;text-align:left;}
.ba-menu-item:hover{background:#f1f5f9;}
.ba-menu-item:disabled{opacity:.45;cursor:not-allowed;}.ba-menu-item:disabled:hover{background:transparent;}
.ba-menu-item.danger{color:#dc2626;}.ba-menu-item.danger:hover{background:#fef2f2;}
.ba-menu-sep{height:1px;background:#f1f5f9;margin:4px 0;}
.ba-menu-backdrop{position:fixed;inset:0;z-index:20;}

/* skeleton + empty */
.ba-card-skeleton{background:#fff;border:1px solid #e5e7eb;border-radius:14px;overflow:hidden;}
.ba-empty-wrap{display:flex;justify-content:center;padding:48px 0;}
.ba-empty-card{background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:36px;text-align:center;min-width:320px;}
.ba-shimmer{background:linear-gradient(90deg,#f3f4f6 25%,#e5e7eb 50%,#f3f4f6 75%);animation:shimmer 1.2s infinite;background-size:200% 100%;}
@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}
.text-muted{color:#64748b;}.mono-sm{font-family:var(--font);}

/* ── Drawers ───────────────────────────────────────────── */
.ba-overlay{position:fixed;inset:0;background:rgba(15,23,42,.28);z-index:40;}
.ba-drawer{position:fixed;top:0;right:-520px;bottom:0;width:520px;max-width:96vw;background:#fff;border-left:1px solid #e5e7eb;box-shadow:-8px 0 28px rgba(15,23,42,.12);z-index:50;display:flex;flex-direction:column;transition:right .24s ease;}
.ba-drawer.open{right:0;}
.ba-view-drawer{width:440px;right:-440px;}.ba-view-drawer.open{right:0;}

.ba-dheader{display:flex;align-items:flex-start;justify-content:space-between;padding:18px 20px;border-bottom:1px solid #e5e7eb;flex-shrink:0;background:linear-gradient(135deg,#eff6ff 0%,#dbeafe 100%);}
.ba-dheader.edit{background:linear-gradient(135deg,#fef3c7 0%,#fde68a 100%);}
.ba-dheader-left{display:flex;align-items:flex-start;gap:12px;}
.ba-dheader-ico{width:38px;height:38px;border-radius:10px;background:#fff;border:1px solid rgba(37,99,235,.18);display:inline-flex;align-items:center;justify-content:center;color:#2563eb;box-shadow:0 1px 3px rgba(15,23,42,.06);flex-shrink:0;}
.ba-dheader-ico.edit{color:#ca8a04;border-color:rgba(202,138,4,.25);}
.ba-dheader-title{font-size:15px;font-weight:700;color:#0f172a;}
.ba-dheader-sub{font-size:12px;color:#475569;margin-top:1px;}
.ba-dclose{background:transparent;border:none;cursor:pointer;color:#475569;display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border-radius:8px;}
.ba-dclose:hover{background:rgba(255,255,255,.6);color:#0f172a;}

.ba-dbody{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:12px;}
.ba-section-hdr{display:flex;align-items:center;gap:8px;font-size:11.5px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:#0f172a;margin-top:6px;}
.ba-section-hdr span{color:#2563eb;display:inline-flex;}
.ba-fields-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
.ba-field{display:flex;flex-direction:column;gap:4px;}
.ba-label{font-size:12px;font-weight:600;color:#334155;}.req{color:#dc2626;}
.ba-hint{font-size:11px;color:#94a3b8;}
.ba-input,.ba-select{border:1px solid #e2e8f0;border-radius:8px;padding:8px 11px;font:inherit;font-size:13px;outline:none;background:#fff;color:#0f172a;transition:border-color .15s,box-shadow .15s;}
.ba-input:focus,.ba-select:focus{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.1);}
.ba-input:disabled{background:#f8fafc;color:#94a3b8;cursor:not-allowed;}
.ba-select{cursor:pointer;}
.ba-check{display:flex;align-items:center;gap:8px;font-size:13px;color:#334155;cursor:pointer;}
.ba-check input{width:15px;height:15px;accent-color:#2563eb;}
.ba-dfooter{display:flex;align-items:center;gap:8px;padding:14px 20px;border-top:1px solid #e5e7eb;flex-shrink:0;}

/* view drawer head */
.ba-view-head{position:relative;flex-shrink:0;padding:20px;border-bottom:1px solid #e5e7eb;background:linear-gradient(135deg,#eff6ff 0%,#dbeafe 100%);}
.ba-vclose{position:absolute;top:12px;right:12px;}
.ba-view-top{display:flex;align-items:center;gap:13px;padding-right:36px;}
.ba-view-icon{width:46px;height:46px;background:#fff;border-radius:12px;display:flex;align-items:center;justify-content:center;color:#2563eb;flex-shrink:0;box-shadow:0 1px 3px rgba(15,23,42,.08);}
.ba-view-name{font-size:16px;font-weight:700;color:#0f172a;}
.ba-view-sub{font-size:12.5px;color:#475569;margin-top:1px;}
.ba-view-balance{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;margin-top:16px;}
.ba-vb-lbl{font-size:10.5px;color:#64748b;text-transform:uppercase;letter-spacing:.05em;font-weight:600;}
.ba-vb-val{font-size:26px;font-weight:800;letter-spacing:-.01em;margin-top:2px;}
.ba-vb-val.pos{color:#0f172a;}.ba-vb-val.neg{color:#dc2626;}
.ba-vb-recon{text-align:right;}
.ba-vb-pct{font-size:18px;font-weight:800;color:#16a34a;}
.ba-vb-txn{font-size:11px;color:#64748b;margin-top:1px;}

.ba-meta-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
.ba-meta-lbl{font-size:10.5px;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;margin-bottom:2px;font-weight:600;}
.ba-quick-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;}
.ba-quick{display:flex;flex-direction:column;align-items:center;gap:7px;padding:14px 8px;background:#fff;border:1px solid #e2e8f0;border-radius:10px;font:inherit;font-size:12px;font-weight:600;color:#334155;cursor:pointer;transition:border-color .15s,background .15s,color .15s;}
.ba-quick:hover{border-color:#2563eb;background:#eff6ff;color:#1d4ed8;}
.ba-quick span{color:#2563eb;}
.ba-primary-btn{display:flex;gap:8px;margin-left:auto;}
/* ── Responsive ── */
@media (max-width: 768px) {
  .ba-drawer      { width: 100% !important; right: -100% !important; max-width: 100%; }
  .ba-view-drawer { width: 100% !important; right: -100% !important; max-width: 100%; }
  .ba-drawer.open,
  .ba-view-drawer.open { right: 0 !important; }
}

@media (max-width: 480px) {
  .ba-page { padding: 12px; gap: 12px; }
  .ba-search-wrap { min-width: 0; flex: 1 1 auto; }
  .ba-fields-grid { grid-template-columns: 1fr !important; }
  .ba-meta-grid   { grid-template-columns: 1fr !important; }
  .ba-quick-grid  { grid-template-columns: repeat(2, 1fr) !important; }
  .ba-view-balance { flex-wrap: wrap; gap: 10px; }
  .ba-vb-val { font-size: 20px; }
  .ba-vb-recon { text-align: left; }
  .ba-filter-meta { flex-wrap: wrap; gap: 8px; }
  .ba-primary-btn{display:flex;gap:8px;margin:0}
}
</style>