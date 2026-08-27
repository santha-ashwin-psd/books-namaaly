<template>
  <div class="db-page">
    <!-- Header -->
    <div class="db-header">
      <div>
        <div class="db-greeting">{{ greeting }}, {{ firstName }}</div>
        <div class="db-company">{{ session.company }}</div>
      </div>
      <div class="db-header-right">
        <span class="db-date">{{ todayFmt }}</span>
      </div>
    </div>

    <!-- KPI Cards -->
    <div class="db-kpi-grid">
      <div class="db-kpi-card" @click="nav('/invoices')">
        <div class="db-kpi-icon" style="background:#eff6ff;color:#2563eb" v-html="icon('file-text',20)"></div>
        <div class="db-kpi-body">
          <div class="db-kpi-lbl">Total Receivables</div>
          <div class="db-kpi-val" :class="kpiLoading?'db-kpi-loading':''">{{ kpiLoading ? '—' : fmtCur(kpi.receivables) }}</div>
          <div class="db-kpi-sub">{{ kpi.invoiceCount }} open invoices</div>
        </div>
      </div>
      <div class="db-kpi-card" @click="nav('/purchases')">
        <div class="db-kpi-icon" style="background:#fef3c7;color:#d97706" v-html="icon('shopping-cart',20)"></div>
        <div class="db-kpi-body">
          <div class="db-kpi-lbl">Total Payables</div>
          <div class="db-kpi-val" :class="kpiLoading?'db-kpi-loading':''">{{ kpiLoading ? '—' : fmtCur(kpi.payables) }}</div>
          <div class="db-kpi-sub">{{ kpi.billCount }} unpaid bills</div>
        </div>
      </div>
      <div class="db-kpi-card" @click="nav('/payments-received')">
        <div class="db-kpi-icon" style="background:#dcfce7;color:#16a34a" v-html="icon('trending-up',20)"></div>
        <div class="db-kpi-body">
          <div class="db-kpi-lbl">Income This Month</div>
          <div class="db-kpi-val" :class="kpiLoading?'db-kpi-loading':''">{{ kpiLoading ? '—' : fmtCur(kpi.income) }}</div>
          <div class="db-kpi-sub">{{ kpi.paidCount }} payments received</div>
        </div>
      </div>
      <div class="db-kpi-card" @click="nav('/payments')">
        <div class="db-kpi-icon" style="background:#fee2e2;color:#dc2626" v-html="icon('trending-down',20)"></div>
        <div class="db-kpi-body">
          <div class="db-kpi-lbl">Expenses This Month</div>
          <div class="db-kpi-val" :class="kpiLoading?'db-kpi-loading':''">{{ kpiLoading ? '—' : fmtCur(kpi.expenses) }}</div>
          <div class="db-kpi-sub">{{ kpi.expenseCount }} transactions</div>
        </div>
      </div>
    </div>

    <div class="db-two-col">
      <!-- Recent Invoices -->
      <div class="db-panel">
        <div class="db-panel-header">
          <span class="db-panel-title">Recent Invoices</span>
          <button class="db-link-btn" @click="nav('/invoices')">View all →</button>
        </div>
        <template v-if="invoiceLoading">
          <div v-for="n in 5" :key="n" class="db-shimmer" style="margin:10px 16px"></div>
        </template>
        <table v-else class="db-mini-table">
          <thead><tr><th>Invoice</th><th>Customer</th><th class="ta-r">Amount</th><th>Status</th></tr></thead>
          <tbody>
            <tr v-for="inv in recentInvoices" :key="inv.name" class="db-mini-row">
              <td><span class="db-doc-link">{{ inv.name }}</span></td>
              <td class="text-muted" style="max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ inv.customer_name||inv.customer }}</td>
              <td class="ta-r mono-sm">{{ fmtCur(inv.grand_total) }}</td>
              <td><span class="db-badge" :class="invStatusClass(inv)">{{ inv.status }}</span></td>
            </tr>
            <tr v-if="!recentInvoices.length"><td colspan="4" class="db-empty">No invoices yet</td></tr>
          </tbody>
        </table>
      </div>

      <!-- Overdue & Alerts -->
      <div class="db-panel">
        <div class="db-panel-header">
          <span class="db-panel-title">Alerts</span>
        </div>

        <div class="db-alert-section">
          <div class="db-alert-hdr">Overdue Invoices</div>
          <template v-if="alertLoading">
            <div v-for="n in 3" :key="n" class="db-shimmer" style="margin:8px 16px"></div>
          </template>
          <template v-else>
            <div v-for="inv in overdueInvoices.slice(0,4)" :key="inv.name" class="db-alert-row" @click="nav('/invoices')">
              <div>
                <div class="db-alert-doc">{{ inv.name }}</div>
                <div class="db-alert-party">{{ inv.customer_name||inv.customer }}</div>
              </div>
              <div class="ta-r">
                <div class="mono-sm red">{{ fmtCur(inv.outstanding_amount) }}</div>
                <div class="db-alert-age">{{ daysPast(inv.due_date) }}d overdue</div>
              </div>
            </div>
            <div v-if="!overdueInvoices.length" class="db-alert-none"><span v-html="icon('check-circle',14)" style="color:#16a34a"></span> No overdue invoices</div>
          </template>
        </div>

        <div class="db-alert-section">
          <div class="db-alert-hdr">Reorder Alerts</div>
          <template v-if="alertLoading">
            <div class="db-shimmer" style="margin:8px 16px"></div>
          </template>
          <template v-else>
            <div v-if="reorderCount>0" class="db-alert-row" style="cursor:pointer" @click="nav('/inventory/reorder-alerts')">
              <div><div class="db-alert-doc">{{ reorderCount }} item{{ reorderCount>1?'s':'' }} below reorder level</div><div class="db-alert-party">Click to view</div></div>
              <span class="db-badge badge-orange">Action needed</span>
            </div>
            <div v-else class="db-alert-none"><span v-html="icon('check-circle',14)" style="color:#16a34a"></span> Stock levels are OK</div>
          </template>
        </div>
      </div>
    </div>

    <!-- Quick Access -->
    <div class="db-quick-section">
      <div class="db-panel-title" style="margin-bottom:12px">Quick Actions</div>
      <div class="db-quick-grid">
        <button class="db-quick-btn" @click="nav('/invoices')"><span v-html="icon('file-plus',16)"></span> New Invoice</button>
        <button class="db-quick-btn" @click="nav('/purchases')"><span v-html="icon('file-minus',16)"></span> New Bill</button>
        <button class="db-quick-btn" @click="nav('/payments-received')"><span v-html="icon('dollar-sign',16)"></span> Record Payment</button>
        <button class="db-quick-btn" @click="nav('/quotes')"><span v-html="icon('send',16)"></span> New Quote</button>
        <button class="db-quick-btn" @click="nav('/expenses')"><span v-html="icon('credit-card',16)"></span> Log Expense</button>
        <button class="db-quick-btn" @click="nav('/reports')"><span v-html="icon('bar-chart-2',16)"></span> Run Reports</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { session } from "../api/session.js";
import { apiList, resolveCompany } from "../api/client.js";
import { icon } from "../utils/icons.js";
import { flt } from "../utils/format.js";

const router = useRouter();
function nav(path) { router.push(path); }

const now = new Date();
const todayFmt = now.toLocaleDateString("en-IN", { weekday: "long", year: "numeric", month: "long", day: "numeric" });
const hour = now.getHours();
const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
const firstName = computed(() => {
  const name = session.fullname || session.user || "";
  return name.split(" ")[0] || name;
});

const firstOfMonth = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
const todayStr = now.toISOString().slice(0, 10);

// KPIs
const kpiLoading = ref(true);
const kpi = ref({ receivables: 0, payables: 0, income: 0, expenses: 0, invoiceCount: 0, billCount: 0, paidCount: 0, expenseCount: 0 });

// Recent invoices
const invoiceLoading = ref(true);
const recentInvoices = ref([]);

// Alerts
const alertLoading = ref(true);
const overdueInvoices = ref([]);
const reorderCount = ref(0);

async function loadAll() {
  try {
    const co = await resolveCompany();

    // Load KPI data, recent invoices, and overdue in parallel
    const [invoices, bills, paymentsIn, paymentsOut, warehouses] = await Promise.all([
      apiList("Sales Invoice", {
        fields: ["name", "customer", "customer_name", "grand_total", "outstanding_amount", "status", "posting_date", "due_date"],
        filters: [["company", "=", co], ["docstatus", "=", 1], ["outstanding_amount", ">", 0]],
        limit: 100, order: "posting_date desc, creation desc"
      }),
      apiList("Purchase Invoice", {
        fields: ["name", "supplier", "grand_total", "outstanding_amount", "status", "posting_date"],
        filters: [["company", "=", co], ["docstatus", "=", 1], ["outstanding_amount", ">", 0]],
        limit: 100
      }),
      apiList("Payment Entry", {
        fields: ["name", "paid_amount", "payment_date"],
        filters: [["company", "=", co], ["payment_type", "=", "Receive"], ["payment_date", ">=", firstOfMonth], ["payment_date", "<=", todayStr]],
        limit: 200
      }),
      apiList("Payment Entry", {
        fields: ["name", "paid_amount", "payment_date"],
        filters: [["company", "=", co], ["payment_type", "=", "Pay"], ["payment_date", ">=", firstOfMonth], ["payment_date", "<=", todayStr]],
        limit: 200
      }),
      apiList("Warehouse", { fields: ["name"], filters: [["company", "=", co], ["is_group", "=", 0]], limit: 200 }),
    ]);
    const whNames = warehouses.map(w => w.name);
    const bins = whNames.length ? await apiList("Bin", {
      fields: ["item_code", "actual_qty", "reorder_level"],
      filters: [["warehouse", "in", whNames], ["reorder_level", ">", 0]],
      limit: 500
    }) : [];

    kpi.value = {
      receivables: invoices.reduce((s, i) => s + flt(i.outstanding_amount), 0),
      payables: bills.reduce((s, b) => s + flt(b.outstanding_amount), 0),
      income: paymentsIn.reduce((s, p) => s + flt(p.paid_amount), 0),
      expenses: paymentsOut.reduce((s, p) => s + flt(p.paid_amount), 0),
      invoiceCount: invoices.length,
      billCount: bills.length,
      paidCount: paymentsIn.length,
      expenseCount: paymentsOut.length,
    };
    kpiLoading.value = false;

    recentInvoices.value = invoices.slice(0, 7);
    invoiceLoading.value = false;

    overdueInvoices.value = invoices.filter(i => i.due_date && new Date(i.due_date) < now && flt(i.outstanding_amount) > 0);
    reorderCount.value = bins.filter(b => flt(b.actual_qty) <= flt(b.reorder_level)).length;
    alertLoading.value = false;

  } catch (e) {
    kpiLoading.value = false;
    invoiceLoading.value = false;
    alertLoading.value = false;
  }
}

function invStatusClass(inv) {
  const s = inv.status;
  if (s === "Overdue") return "badge-red";
  if (s === "Unpaid") return "badge-orange";
  if (s === "Paid") return "badge-green";
  if (s === "Partially Paid") return "badge-blue";
  return "badge-grey";
}

function daysPast(dateStr) {
  if (!dateStr) return 0;
  return Math.floor((now - new Date(dateStr)) / 86400000);
}

function fmtCur(v) {
  const n = flt(v);
  try {
    return new Intl.NumberFormat("en-OM", { style: "currency", currency: "OMR" }).format(n);
  } catch {
    return "ر.ع. " + n.toLocaleString("en-OM", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
  }
}

onMounted(loadAll);
</script>

<style scoped>
.db-page { display: flex; flex-direction: column; gap: 20px; padding: 24px; }

/* Header */
.db-header { display: flex; align-items: flex-start; justify-content: space-between; }
.db-greeting { font-size: 22px; font-weight: 800; color: #111827; }
.db-company { font-size: 13px; color: #6b7280; margin-top: 2px; }
.db-date { font-size: 12.5px; color: #9ca3af; }
.db-header-right { text-align: right; }

/* KPI cards */
.db-kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
@media (max-width: 900px) { .db-kpi-grid { grid-template-columns: repeat(2, 1fr); } }
.db-kpi-card {
  background: #fff; border: 1px solid #e5e7eb; border-radius: 12px;
  padding: 16px; display: flex; gap: 14px; align-items: flex-start;
  cursor: pointer; transition: box-shadow .15s;
}
.db-kpi-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,.08); }
.db-kpi-icon { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.db-kpi-lbl { font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 4px; }
.db-kpi-val { font-size: 19px; font-weight: 700; color: #111827; }
.db-kpi-val.db-kpi-loading { color: #d1d5db; }
.db-kpi-sub { font-size: 11.5px; color: #9ca3af; margin-top: 3px; }

/* Two-col layout */
.db-two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 860px) { .db-two-col { grid-template-columns: 1fr; } }

/* Panels */
.db-panel { background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden; }
.db-panel-header { display: flex; align-items: center; justify-content: space-between; padding: 14px 16px; border-bottom: 1px solid #e5e7eb; }
.db-panel-title { font-size: 13.5px; font-weight: 700; color: #111827; }
.db-link-btn { background: none; border: none; color: #2563eb; font-size: 12.5px; cursor: pointer; font-weight: 600; }
.db-link-btn:hover { text-decoration: underline; }

/* Mini table */
.db-mini-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.db-mini-table th { background: #f9fafb; padding: 8px 12px; font-size: 11px; font-weight: 600; color: #6b7280; text-align: left; border-bottom: 1px solid #e5e7eb; }
.db-mini-row td { padding: 9px 12px; border-bottom: 1px solid #f3f4f6; }
.db-mini-row:last-child td { border-bottom: none; }
.db-mini-row:hover td { background: #f9fafb; }
.db-doc-link { font-size: 12px; color: #2563eb; font-weight: 600; }
.ta-r { text-align: right !important; }
.mono-sm { font-size: 12px; }
.text-muted { color: #6b7280; }
.db-empty { text-align: center; color: #9ca3af; padding: 28px !important; font-size: 12.5px; }

/* Badges */
.db-badge { display: inline-flex; padding: 2px 7px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.badge-green  { background: #dcfce7; color: #16a34a; }
.badge-red    { background: #fee2e2; color: #dc2626; }
.badge-orange { background: #fff7ed; color: #ea580c; }
.badge-blue   { background: #eff6ff; color: #2563eb; }
.badge-grey   { background: #f3f4f6; color: #6b7280; }
.red { color: #dc2626 !important; }

/* Alert section */
.db-alert-section { border-bottom: 1px solid #f3f4f6; padding-bottom: 4px; }
.db-alert-section:last-child { border-bottom: none; }
.db-alert-hdr { padding: 10px 16px 6px; font-size: 11px; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: .05em; }
.db-alert-row { display: flex; align-items: center; justify-content: space-between; padding: 9px 16px; border-bottom: 1px solid #f3f4f6; cursor: pointer; }
.db-alert-row:hover { background: #f9fafb; }
.db-alert-row:last-child { border-bottom: none; }
.db-alert-doc { font-size: 12.5px; font-weight: 600; color: #111827; }
.db-alert-party { font-size: 11.5px; color: #6b7280; margin-top: 1px; }
.db-alert-age { font-size: 11px; color: #9ca3af; }
.db-alert-none { display: flex; align-items: center; gap: 6px; padding: 12px 16px; font-size: 12.5px; color: #6b7280; }

/* Quick actions */
.db-quick-section { background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px 20px; }
.db-quick-grid { display: flex; flex-wrap: wrap; gap: 10px; }
.db-quick-btn {
  display: inline-flex; align-items: center; gap: 7px;
  background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px;
  padding: 9px 16px; font-size: 13px; font-weight: 600; color: #374151; cursor: pointer;
  transition: all .12s;
}
.db-quick-btn:hover { background: #eff6ff; border-color: #bfdbfe; color: #2563eb; }

/* Shimmer */
.db-shimmer { height: 13px; background: linear-gradient(90deg,#f3f4f6 25%,#e5e7eb 50%,#f3f4f6 75%); border-radius: 4px; animation: shimmer 1.2s infinite; background-size: 200% 100%; margin-bottom: 6px; }
@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
</style>