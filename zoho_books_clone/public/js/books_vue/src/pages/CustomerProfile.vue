<template>
  <div class="cp-page">
    <!-- Back link + breadcrumb -->
    <div class="cp-bread">
      <router-link to="/customers" class="cp-back">
        <span v-html="icon('arrow-right',13)" style="transform:rotate(180deg)"></span>
        All Customers
      </router-link>
      <span class="cp-bread-sep">/</span>
      <span class="cp-bread-cur">{{ customer.customer_name || $route.params.name }}</span>
    </div>

    <!-- Header card -->
    <div class="cp-header">
      <div class="cp-header-left">
        <div class="cp-avatar">{{ initials }}</div>
        <div>
          <div class="cp-name">{{ customer.customer_name || $route.params.name }}</div>
          <div class="cp-meta">
            <span v-if="customer.customer_type" class="cp-chip">{{ customer.customer_type }}</span>
            <span v-if="customer.customer_group" class="cp-chip cp-chip-muted">{{ customer.customer_group }}</span>
            <span v-if="customer.territory" class="cp-chip cp-chip-muted">{{ customer.territory }}</span>
            <span v-if="customer.disabled" class="cp-chip cp-chip-danger">Disabled</span>
          </div>
        </div>
      </div>
      <div style="display:flex;gap:8px">
        <button class="cp-btn-ghost" @click="emailCustomer" :disabled="!customer.email_id">
          <span v-html="icon('mail',13)"></span> Email
        </button>
        <button class="cp-btn-ghost" @click="downloadStatement">
          <span v-html="icon('download',13)"></span> Statement
        </button>
        <button class="cp-btn-primary" @click="newInvoice">
          <span v-html="icon('plus',13)"></span> New Invoice
        </button>
      </div>
    </div>

    <!-- Stat cards -->
    <div class="cp-stats">
      <div class="cp-stat-card" :class="{warn: summary.outstanding>0}">
        <div class="cp-stat-lbl">Outstanding</div>
        <div class="cp-stat-val" :class="summary.outstanding>0?'red':'green'">{{ fmtCur(summary.outstanding) }}</div>
        <div class="cp-stat-sub">{{ summary.open_invoice_count }} open invoice{{ summary.open_invoice_count!==1?'s':'' }}</div>
      </div>
      <div class="cp-stat-card">
        <div class="cp-stat-lbl">Credit Note Balance</div>
        <div class="cp-stat-val" :class="summary.cn_credit>0?'green':''">{{ fmtCur(summary.cn_credit) }}</div>
        <div class="cp-stat-sub">{{ summary.open_cn_count }} open CN{{ summary.open_cn_count!==1?'s':'' }}</div>
      </div>
      <div class="cp-stat-card">
        <div class="cp-stat-lbl">Lifetime Billed</div>
        <div class="cp-stat-val">{{ fmtCur(lifetime) }}</div>
        <div class="cp-stat-sub">{{ counts.invoices }} invoice{{ counts.invoices!==1?'s':'' }}</div>
      </div>
      <div class="cp-stat-card">
        <div class="cp-stat-lbl">Last Activity</div>
        <div class="cp-stat-val cp-stat-val-sm">{{ fmtDate(summary.last_txn_date) || '—' }}</div>
        <div class="cp-stat-sub">{{ daysAgo(summary.last_txn_date) }}</div>
      </div>
    </div>

    <!-- Contact + Address strip -->
    <div class="cp-contact-card">
      <div class="cp-contact-section">
        <div class="cp-section-title">Contact</div>
        <div class="cp-contact-row">
          <div class="cp-kv"><span class="cp-k">Email</span>
            <a v-if="customer.email_id" :href="`mailto:${customer.email_id}`" class="cp-link">{{ customer.email_id }}</a>
            <span v-else>—</span>
          </div>
          <div class="cp-kv"><span class="cp-k">Mobile</span>
            <a v-if="customer.mobile_no" :href="`tel:${customer.mobile_no}`" class="cp-link">{{ customer.mobile_no }}</a>
            <span v-else>—</span>
          </div>
          <div class="cp-kv"><span class="cp-k">Phone</span>
            <a v-if="customer.phone" :href="`tel:${customer.phone}`" class="cp-link">{{ customer.phone }}</a>
            <span v-else>—</span>
          </div>
          <div class="cp-kv"><span class="cp-k">GSTIN</span><span class="mono">{{ customer.tax_id || '—' }}</span></div>
        </div>
      </div>
      <div class="cp-contact-section">
        <div class="cp-section-title">Addresses</div>
        <AddressManager
          v-if="customer.name"
          :partyDoctype="'Customer'"
          :partyName="customer.name"
          @addressSaved="onAddressChange"
          @addressDeleted="onAddressChange"
        />
        <div v-else style="color:#9ca3af;font-style:italic;font-size:12.5px">No address on file</div>
      </div>
      <div class="cp-contact-section">
        <div class="cp-section-title">Accounts</div>
        <div class="cp-contact-row">
          <div class="cp-kv"><span class="cp-k">Payment Terms</span><span>{{ customer.payment_terms || '—' }}</span></div>
          <div class="cp-kv"><span class="cp-k">Credit Limit</span><span class="mono">{{ customer.credit_limit ? fmtCur(customer.credit_limit) : '—' }}</span></div>
          <div class="cp-kv"><span class="cp-k">Receivable A/c</span><span class="mono-sm">{{ customer.default_receivable_account || '—' }}</span></div>
        </div>
      </div>
    </div>

    <!-- Opening Balance -->
    <div v-if="obInfo.has_opening_je" class="cp-ob-card">
      <div>
        <div class="cp-section-title" style="border:none;padding:0">Opening Balance</div>
        <div class="cp-ob-amt" :class="{green: obInfo.outstanding<=0}">
          {{ fmtCur(obInfo.outstanding) }}
          <span v-if="obInfo.outstanding<=0" class="cp-chip" style="margin-left:6px">Paid</span>
        </div>
      </div>
      <button v-if="obInfo.outstanding>0" class="cp-btn-primary" @click="openPayModal">
        <span v-html="icon('plus',13)"></span> Pay
      </button>
    </div>

    <!-- Tabs -->
    <div class="cp-tabs">
      <button v-for="t in tabs" :key="t.k" class="cp-tab" :class="{active:tab===t.k}" @click="tab=t.k">
        {{ t.l }}<span v-if="t.count" class="cp-tab-count">{{ t.count }}</span>
      </button>
    </div>

    <!-- Pay Opening Balance modal -->
    <div v-if="showPayModal" class="cp-modal-overlay" @click.self="showPayModal=false">
      <div class="cp-modal">
        <div class="cp-modal-title">Pay Opening Balance</div>
        <label class="cp-modal-field">
          <span>Amount</span>
          <input type="number" v-model.number="payForm.amount" :max="obInfo.outstanding" min="0.01" step="0.01" />
        </label>
        <label class="cp-modal-field">
          <span>Pay Into</span>
          <select v-model="payForm.bank_cash_account">
            <option v-for="a in obInfo.bank_cash_accounts" :key="a.name" :value="a.name">{{ a.name }}</option>
          </select>
        </label>
        <label class="cp-modal-field">
          <span>Date</span>
          <input type="date" v-model="payForm.payment_date" />
        </label>
        <div class="cp-modal-actions">
          <button class="cp-btn-ghost" @click="showPayModal=false">Cancel</button>
          <button class="cp-btn-primary" :disabled="payLoading" @click="submitPayment">
            {{ payLoading ? "Recording…" : "Record Payment" }}
          </button>
        </div>
      </div>
    </div>

    <!-- Tab content -->
    <div class="cp-tab-body">
      <div v-if="tabLoading" class="cp-empty">Loading…</div>

      <!-- Overview / mixed activity -->
      <div v-else-if="tab==='overview'">
        <table class="cp-table">
          <thead><tr><th>Type</th><th>Document</th><th>Date</th><th class="ta-r">Amount</th><th class="ta-r">Outstanding</th><th>Status</th></tr></thead>
          <tbody>
            <tr v-for="t in transactions" :key="t.type+t.name">
              <td><span class="cp-type-pill" :class="typeClass(t.type)">{{ t.type }}</span></td>
              <td><DocLink :doctype="docTypeFor(t.type)" :name="t.name" /></td>
              <td class="text-muted">{{ fmtDate(t.date) }}</td>
              <td class="ta-r mono-sm" :class="t.amount<0?'red':''">{{ fmtCur(t.amount) }}</td>
              <td class="ta-r mono-sm">{{ t.outstanding ? fmtCur(t.outstanding) : '—' }}</td>
              <td><span class="cp-status">{{ t.status || (t.docstatus===2?'Cancelled':t.docstatus===0?'Draft':'Submitted') }}</span></td>
            </tr>
            <tr v-if="!transactions.length"><td colspan="6" class="cp-empty">No activity yet</td></tr>
          </tbody>
        </table>
      </div>

      <!-- Document-type tabs use the same table but filtered -->
      <div v-else>
        <table class="cp-table">
          <thead><tr>
            <th>Document #</th><th>Date</th><th class="ta-r">Amount</th>
            <th v-if="tab==='Invoice'" class="ta-r">Outstanding</th>
            <th>Status</th>
          </tr></thead>
          <tbody>
            <tr v-for="t in tabRows" :key="t.name">
              <td><DocLink :doctype="docTypeFor(t.type)" :name="t.name" /></td>
              <td class="text-muted">{{ fmtDate(t.date) }}</td>
              <td class="ta-r mono-sm" :class="t.amount<0?'red':''">{{ fmtCur(Math.abs(t.amount)) }}</td>
              <td v-if="tab==='Invoice'" class="ta-r mono-sm">{{ t.outstanding ? fmtCur(t.outstanding) : '—' }}</td>
              <td><span class="cp-status">{{ t.status || (t.docstatus===2?'Cancelled':t.docstatus===0?'Draft':'Submitted') }}</span></td>
            </tr>
            <tr v-if="!tabRows.length"><td :colspan="tab==='Invoice'?5:4" class="cp-empty">No {{ tab.toLowerCase() }}s yet</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiGet, apiGET, apiList, apiSave, apiSubmit } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";
import { fmtDate } from "../utils/format.js";
import DocLink from "../components/DocLink.vue";
import AddressManager from "../components/AddressManager.vue";

const route = useRoute();
const router = useRouter();
const { toast } = useToast();

const customer = ref({});
const summary = ref({ outstanding: 0, cn_credit: 0, open_invoice_count: 0, open_cn_count: 0, last_txn_date: null });
const transactions = ref([]);
const tab = ref("overview");
const tabLoading = ref(false);
const obInfo = ref({ has_opening_je: false });
const showPayModal = ref(false);
const payLoading = ref(false);
const payForm = reactive({ amount: 0, bank_cash_account: "", payment_date: new Date().toISOString().slice(0, 10) });

const tabs = computed(() => [
  { k: "overview", l: "Overview" },
  { k: "Invoice", l: "Invoices", count: counts.value.invoices },
  { k: "Credit Note", l: "Credit Notes", count: counts.value.credit_notes },
  { k: "Payment", l: "Payments", count: counts.value.payments },
]);

const counts = computed(() => {
  const c = { invoices: 0, credit_notes: 0, payments: 0 };
  for (const t of transactions.value) {
    if (t.type === "Invoice") c.invoices++;
    else if (t.type === "Credit Note") c.credit_notes++;
    else if (t.type === "Payment") c.payments++;
  }
  return c;
});

const tabRows = computed(() => transactions.value.filter(t => t.type === tab.value));

const lifetime = computed(() =>
  transactions.value.filter(t => t.type === "Invoice").reduce((s, t) => s + Math.abs(t.amount || 0), 0)
);

const initials = computed(() => {
  const name = customer.value.customer_name || route.params.name || "";
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map(p => p[0]).join("").toUpperCase() || "?";
});

function fmtCur(v) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 0 }).format(Number(v || 0));
}

function daysAgo(d) {
  if (!d) return "Never";
  const days = Math.floor((new Date() - new Date(d)) / 86400000);
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 30) return `${days} days ago`;
  if (days < 365) return `${Math.floor(days / 30)} months ago`;
  return `${Math.floor(days / 365)} years ago`;
}

function typeClass(type) {
  return type === "Invoice" ? "type-invoice" : type === "Credit Note" ? "type-cn" : "type-payment";
}

function docTypeFor(type) {
  return type === "Invoice" ? "Sales Invoice"
    : type === "Credit Note" ? "Sales Invoice"   // CNs are stored as Sales Invoice with is_return=1
    : type === "Payment" ? "Payment Entry" : "";
}

async function load() {
  tabLoading.value = true;
  try {
    const name = route.params.name;
    const [c, s, t, ob] = await Promise.all([
      apiGet("Customer", name).catch(() => ({})),
      apiGET("zoho_books_clone.api.docs.get_customer_summary", { customer: name }).catch(() => ({})),
      apiGET("zoho_books_clone.api.docs.get_customer_transactions", { customer: name, limit: 200 }).catch(() => []),
      apiGET("zoho_books_clone.accounts.opening_balance.get_opening_balance_payment_info",
        { party_type: "Customer", party: name }).catch(() => ({ has_opening_je: false })),
    ]);
    customer.value = c || {};
    summary.value = s || summary.value;
    transactions.value = Array.isArray(t) ? t : [];
    obInfo.value = ob || { has_opening_je: false };
  } catch (e) {
    toast.error(e.message || "Failed to load customer");
  } finally {
    tabLoading.value = false;
  }
}

function openPayModal() {
  payForm.amount = obInfo.value.outstanding;
  payForm.bank_cash_account = obInfo.value.bank_cash_accounts?.[0]?.name || "";
  payForm.payment_date = new Date().toISOString().slice(0, 10);
  showPayModal.value = true;
}

async function submitPayment() {
  const amount = Number(payForm.amount);
  if (!payForm.bank_cash_account) { toast.error("Choose an account to pay into"); return; }
  if (!amount || amount <= 0) { toast.error("Enter a valid amount"); return; }
  if (amount > obInfo.value.outstanding + 0.01) { toast.error("Amount exceeds outstanding opening balance"); return; }

  payLoading.value = true;
  try {
    const doc = {
      doctype: "Payment Entry",
      payment_type: "Receive",
      party_type: "Customer",
      party: route.params.name,
      party_name: customer.value.customer_name,
      company: obInfo.value.company,
      paid_from: obInfo.value.party_account,
      paid_to: payForm.bank_cash_account,
      paid_amount: amount,
      received_amount: amount,
      payment_date: payForm.payment_date,
      remarks: `Opening balance payment for ${customer.value.customer_name || route.params.name}`,
      references: [{
        reference_doctype: "Journal Entry",
        reference_name: obInfo.value.journal_entry,
        allocated_amount: amount,
      }],
    };
    const saved = await apiSave(doc);
    await apiSubmit("Payment Entry", saved.name);
    toast.success("Payment recorded");
    showPayModal.value = false;
    await load();
  } catch (e) {
    toast.error(e.message || "Failed to record payment");
  } finally {
    payLoading.value = false;
  }
}

function onAddressChange() {
  // Re-fetch customer to get latest; addresses managed by AddressManager itself
}

onMounted(load);
watch(() => route.params.name, load);

function emailCustomer() {
  if (customer.value.email_id) window.location.href = `mailto:${customer.value.email_id}`;
}

async function downloadStatement() {
  try {
    const data = await apiGET("zoho_books_clone.api.docs.get_customer_statement",
      { customer: route.params.name });
    if (!data || !data.rows?.length) { toast.error("No statement rows in this period"); return; }
    const headers = ["Date","Document","Type","Debit","Credit","Balance"];
    const rows = data.rows.map(r => [r.date, r.name, r.type, r.debit, r.credit, r.balance]);
    const esc = v => { const s = v == null ? "" : String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
    const csv = "﻿" + [headers, ...rows].map(r => r.map(esc).join(",")).join("\r\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `statement-${route.params.name}-${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    toast.error(e.message || "Statement download failed");
  }
}

function newInvoice() {
  router.push({ path: "/invoices", query: { new: 1, customer: route.params.name } });
}
</script>

<style scoped>
.cp-page{padding:24px;display:flex;flex-direction:column;gap:16px;background:#f8fafc;min-height:100vh;}
.cp-bread{display:flex;align-items:center;gap:8px;font-size:12.5px;color:#6b7280;}
.cp-back{color:#2563eb;text-decoration:none;display:inline-flex;align-items:center;gap:4px;font-weight:600;}
.cp-back:hover{color:#1d4ed8;text-decoration:underline;}
.cp-bread-sep{color:#cbd5e1;}
.cp-bread-cur{color:#0f172a;font-weight:600;}

.cp-header{display:flex;align-items:center;justify-content:space-between;gap:20px;background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:20px 24px;box-shadow:0 1px 2px rgba(15,23,42,.04);}
.cp-header-left{display:flex;align-items:center;gap:16px;}
.cp-avatar{width:56px;height:56px;border-radius:50%;background:linear-gradient(135deg,#3b82f6,#1d4ed8);color:#fff;display:inline-flex;align-items:center;justify-content:center;font-size:20px;font-weight:700;flex-shrink:0;}
.cp-name{font-size:20px;font-weight:700;color:#0f172a;letter-spacing:-0.01em;}
.cp-meta{display:flex;gap:6px;margin-top:6px;flex-wrap:wrap;}
.cp-chip{background:#eff6ff;color:#1d4ed8;padding:3px 10px;border-radius:20px;font-size:11.5px;font-weight:600;}
.cp-chip-muted{background:#f3f4f6;color:#475569;}
.cp-chip-danger{background:#fee2e2;color:#dc2626;}
.cp-btn-ghost{display:inline-flex;align-items:center;gap:6px;background:#fff;border:1px solid #e5e7eb;color:#374151;border-radius:8px;padding:8px 14px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;}
.cp-btn-ghost:hover:not(:disabled){background:#f9fafb;border-color:#cbd5e1;}
.cp-btn-ghost:disabled{opacity:.5;cursor:not-allowed;}
.cp-btn-primary{display:inline-flex;align-items:center;gap:6px;background:#2563eb;color:#fff;border:none;border-radius:8px;padding:8px 14px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;}
.cp-btn-primary:hover{background:#1d4ed8;}

.cp-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;}
.cp-stat-card{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:16px 18px;box-shadow:0 1px 2px rgba(15,23,42,.03);}
.cp-stat-card.warn{background:linear-gradient(135deg,#fef2f2,#fff);border-color:#fecaca;}
.cp-stat-lbl{font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;font-weight:600;}
.cp-stat-val{font-size:22px;font-weight:700;color:#111827;margin-top:6px;}
.cp-stat-val-sm{font-size:14px;font-family:inherit;}
.cp-stat-sub{font-size:11.5px;color:#9ca3af;margin-top:4px;}
.green{color:#16a34a!important;}.red{color:#dc2626!important;}

.cp-contact-card{display:grid;grid-template-columns:1.4fr 1fr 1.4fr;gap:24px;background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:18px 22px;box-shadow:0 1px 2px rgba(15,23,42,.03);}
.cp-contact-section{display:flex;flex-direction:column;gap:10px;}
.cp-section-title{font-size:11px;font-weight:700;color:#0f172a;text-transform:uppercase;letter-spacing:.05em;padding-bottom:6px;border-bottom:1px solid #f3f4f6;}
.cp-contact-row{display:flex;flex-direction:column;gap:8px;}
.cp-kv{display:flex;justify-content:space-between;align-items:center;font-size:12.5px;gap:8px;}
.cp-k{color:#6b7280;font-weight:500;}
.cp-link{color:#2563eb;text-decoration:none;font-weight:500;}
.cp-link:hover{text-decoration:underline;}
.cp-address{font-size:12.5px;color:#374151;line-height:1.6;}

.cp-ob-card{display:flex;align-items:center;justify-content:space-between;background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:16px 22px;box-shadow:0 1px 2px rgba(15,23,42,.03);}
.cp-ob-amt{font-size:20px;font-weight:700;color:#0f172a;margin-top:4px;}

.cp-modal-overlay{position:fixed;inset:0;background:rgba(15,23,42,.45);display:flex;align-items:center;justify-content:center;z-index:100;}
.cp-modal{background:#fff;border-radius:12px;padding:22px;width:340px;box-shadow:0 10px 30px rgba(0,0,0,.15);}
.cp-modal-title{font-size:16px;font-weight:700;color:#0f172a;margin-bottom:14px;}
.cp-modal-field{display:flex;flex-direction:column;gap:4px;margin-bottom:12px;font-size:12.5px;color:#374151;font-weight:600;}
.cp-modal-field input,.cp-modal-field select{border:1px solid #d1d5db;border-radius:8px;padding:8px 10px;font-size:13px;font-family:inherit;}
.cp-modal-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:16px;}

.cp-tabs{display:flex;gap:0;background:#fff;border:1px solid #e5e7eb;border-radius:10px 10px 0 0;padding:0 12px;flex-shrink:0;}
.cp-tab{background:transparent;border:none;padding:12px 18px;font-size:13px;font-weight:600;color:#6b7280;cursor:pointer;border-bottom:2px solid transparent;display:inline-flex;align-items:center;gap:6px;font-family:inherit;}
.cp-tab.active{color:#2563eb;border-bottom-color:#2563eb;}
.cp-tab-count{background:#e5e7eb;color:#374151;padding:1px 8px;border-radius:10px;font-size:11px;font-weight:700;}
.cp-tab.active .cp-tab-count{background:#dbeafe;color:#1d4ed8;}

.cp-tab-body{background:#fff;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 10px 10px;padding:0;}
.cp-table{width:100%;border-collapse:collapse;font-size:13px;}
.cp-table th{background:#f9fafb;border-bottom:1px solid #e5e7eb;padding:10px 14px;font-size:11.5px;font-weight:600;color:#374151;text-align:left;white-space:nowrap;}
.cp-table td{padding:11px 14px;border-bottom:1px solid #f3f4f6;vertical-align:middle;}
.cp-table tr:last-child td{border-bottom:none;}
.ta-r{text-align:right!important;}
.mono-sm{font-size:12.5px;}.text-muted{color:#6b7280;}
.cp-type-pill{display:inline-flex;padding:2px 10px;border-radius:10px;font-size:11px;font-weight:700;}
.type-invoice{background:#dbeafe;color:#1d4ed8;}
.type-cn{background:#fef2f2;color:#dc2626;}
.type-payment{background:#dcfce7;color:#16a34a;}
.cp-status{font-size:11.5px;color:#374151;font-weight:500;}
.cp-empty{text-align:center;padding:48px;color:#9ca3af;font-size:13px;}

@media (max-width: 768px) {
  .cp-page { padding: 12px !important; gap: 12px !important; }

  /* Header: wrap buttons below name */
  .cp-header { flex-direction: column; align-items: flex-start; gap: 12px; padding: 14px 16px; }
  .cp-header > div:last-child { width: 100%; display: flex; flex-wrap: wrap; gap: 8px; }
  .cp-header > div:last-child > button { flex: 1; justify-content: center; }

  /* Stats: 2-col grid */
  .cp-stats { grid-template-columns: 1fr 1fr !important; gap: 8px !important; }
  .cp-stat-val { font-size: 17px; }

  /* Contact card: single column stack */
  .cp-contact-card { grid-template-columns: 1fr !important; gap: 0 !important; padding: 0 !important; }
  .cp-contact-section { padding: 14px 16px; border-bottom: 1px solid #f3f4f6; }
  .cp-contact-section:last-child { border-bottom: none; }

  /* Tabs: allow horizontal scroll if many tabs */
  .cp-tabs { overflow-x: auto; -webkit-overflow-scrolling: touch; }
  .cp-tab { white-space: nowrap; padding: 10px 14px; font-size: 12.5px; }

  /* Table: horizontal scroll */
  .cp-tab-body { overflow-x: auto; }
  .cp-table { min-width: 480px; }
}

@media (max-width: 480px) {
  /* Stats: 1-col on very small phones */
  .cp-stats { grid-template-columns: 1fr !important; }
}
</style>