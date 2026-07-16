<template>
  <div class="i-page">
    <div class="i-head">
      <div>
        <div class="i-title">Integrations</div>
        <div class="i-sub">What's wired up today, what's available out of the box, and what's still on the roadmap.</div>
      </div>
      <button class="i-cta" @click="load" :disabled="loading"><span v-html="icon('refresh',13)"></span> Refresh</button>
    </div>

    <SummaryStrip v-if="!loading" :cards="[
      { label: 'Active', tone:'success', value: byStatus('active'), valueClass:'green' },
      { label: 'Available', tone:'accent', value: byStatus('available'), valueClass:'blue' },
      { label: 'Not Configured', tone: byStatus('not_configured')>0?'warn':'default', value: byStatus('not_configured'), valueClass: byStatus('not_configured')>0?'orange':'' },
      { label: 'Coming Soon', tone:'default', value: byStatus('coming_soon') },
    ]" />

    <div v-if="loading" class="i-loading">Loading…</div>
    <div v-else class="i-grid">
      <div v-for="grp in groups" :key="grp.label" class="i-group">
        <div class="i-group-hdr">{{ grp.label }}</div>
        <div class="i-cards">
          <div v-for="x in grp.items" :key="x.key" class="i-card" :class="x.status">
            <div class="i-card-top">
              <div class="i-card-ico" :style="{background: x.bg, color: x.fg}"><span v-html="icon(x.ico, 18)"></span></div>
              <div class="i-card-meta">
                <div class="i-card-name">{{ x.name }}</div>
                <div class="i-card-desc">{{ x.desc }}</div>
              </div>
              <span class="i-pill" :class="x.status">{{ STATUS_LABEL[x.status] }}</span>
            </div>
            <div v-if="x.note" class="i-note">{{ x.note }}</div>
            <div v-if="x.action" class="i-actions">
              <button class="i-link" @click="x.action.go()"><span v-html="icon('ext',12)"></span> {{ x.action.label }}</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { apiGET, resolveCompany, apiGet, apiList } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";
import SummaryStrip from "../components/SummaryStrip.vue";

const { toast } = useToast();
const router = useRouter();
const loading = ref(true);
const smtpEnabled = ref(false);
const companyGstin = ref("");
const irnGenerated = ref(0);
const irnPending = ref(0);

const STATUS_LABEL = { active: "Active", available: "Available", not_configured: "Not Configured", coming_soon: "Coming Soon" };

const integrations = computed(() => [
  { group: "Email & Notifications", key: "smtp", name: "Company SMTP", desc: "Send invoices, reminders, and customer emails from your domain.",
    ico: "mail", bg: "#eff6ff", fg: "#2563eb",
    status: smtpEnabled.value ? "active" : "not_configured",
    note: smtpEnabled.value ? null : "Configure server, login, and from-address to start sending email.",
    action: { label: "Open Email & SMTP", go: () => router.push({ name: "settings-email" }) } },

  { group: "Banking", key: "bank-match", name: "Bank Auto-Match", desc: "Daily scheduler matches Bank Transactions to Payment Entries by amount + date + reference.",
    ico: "bank", bg: "#ecfdf5", fg: "#16a34a", status: "active",
    note: "Runs via scheduled hook (banking.utils.auto_match_bank_transactions, daily)." },
  { group: "Banking", key: "bank-recon", name: "Bank Reconciliation", desc: "Match unreconciled bank transactions against your ledger with one click.",
    ico: "balance", bg: "#eff6ff", fg: "#2563eb", status: "active",
    action: { label: "Open Reconciliation", go: () => router.push({ name: "banking-reconciliation" }) } },

  { group: "GST & E-Invoicing", key: "gstr1", name: "GSTR-1 Filing", desc: "Auto-prepared GSTR-1 returns from your Sales Invoices.",
    ico: "gstfile", bg: "#fff7ed", fg: "#ea580c", status: "active",
    action: { label: "Open GSTR-1", go: () => router.push({ name: "gstr-1" }).catch(()=>{}) } },
  { group: "GST & E-Invoicing", key: "gstr3b", name: "GSTR-3B Summary", desc: "Monthly GSTR-3B preview from your invoice + bill tax lines.",
    ico: "gstfile", bg: "#fff7ed", fg: "#ea580c", status: "active",
    action: { label: "Open GSTR-3B", go: () => router.push({ name: "gstr-3b" }).catch(()=>{}) } },
  { group: "GST & E-Invoicing", key: "einvoice", name: "E-Invoice (IRP)", desc: "Generate IRN + QR codes for B2B invoices. Attach to PDF, cancel within 24 hrs.",
    ico: "qr", bg: "#fef2f2", fg: "#dc2626",
    status: companyGstin.value ? (irnGenerated.value > 0 ? "active" : "available") : "not_configured",
    note: companyGstin.value
      ? `GSTIN: ${companyGstin.value} · ${irnGenerated.value} IRN generated${irnPending.value > 0 ? ` · ${irnPending.value} pending` : ''}`
      : "Set your company GSTIN (Settings → Company) to activate e-Invoice generation.",
    action: { label: "Open e-Invoice", go: () => router.push({ name: "einvoice" }).catch(() => {}) } },
  { group: "GST & E-Invoicing", key: "eway", name: "E-Way Bills", desc: "EWB generation for shipments.",
    ico: "truck", bg: "#eff6ff", fg: "#2563eb", status: "active",
    action: { label: "Open E-Way Bills", go: () => router.push({ name: "eway-bills" }).catch(()=>{}) } },

  { group: "Inventory & Stock", key: "stock-link", name: "Stock ↔ Documents Link", desc: "Delivery Notes deduct stock at FIFO cost; Purchase Receipts add stock. Invoices opt-in via 'Update Inventory'.",
    ico: "stack", bg: "#ecfdf5", fg: "#16a34a", status: "active",
    note: "Wired via doc_events in hooks.py — goods documents own the physical stock movement." },
  { group: "Inventory & Stock", key: "reorder", name: "Reorder Alerts", desc: "Daily scan flags items at or below their reorder level.",
    ico: "alert", bg: "#fef2f2", fg: "#dc2626", status: "active",
    action: { label: "Open Reorder Alerts", go: () => router.push({ name: "reorder-alerts" }).catch(()=>{}) } },

  { group: "Accounting", key: "period-lock", name: "Books Lock Date", desc: "Server-side guard blocks postings dated on or before the lock date.",
    ico: "lock", bg: "#fff7ed", fg: "#ea580c", status: "active",
    action: { label: "Set on Fiscal Years", go: () => router.push({ name: "fiscal-years" }).catch(()=>{}) } },
  { group: "Accounting", key: "fiscal-close", name: "Fiscal Year Close", desc: "Posts closing JE to Retained Earnings and locks the year.",
    ico: "balance", bg: "#eff6ff", fg: "#2563eb", status: "active" },
  { group: "Accounting", key: "recurring", name: "Recurring Documents (Auto Repeat)", desc: "Schedule invoices, bills, JEs to auto-generate on a cadence.",
    ico: "recurring", bg: "#f5f3ff", fg: "#7c3aed", status: "active",
    action: { label: "Open Recurring Bills", go: () => router.push({ name: "recurring-bills" }).catch(()=>{}) } },

  { group: "Single Sign-On", key: "sso-google", name: "Google Sign-In", desc: "Let users log in with their Google or Google Workspace account.",
    ico: "user", bg: "#fefce8", fg: "#a16207", status: "available",
    action: { label: "Configure", go: () => router.push({ name: "settings-sso" }) } },
  { group: "Single Sign-On", key: "sso-ms", name: "Microsoft / Azure AD", desc: "Enterprise SSO via Microsoft 365 or Azure Active Directory.",
    ico: "shield", bg: "#eff6ff", fg: "#2563eb", status: "available",
    action: { label: "Configure", go: () => router.push({ name: "settings-sso" }) } },

  { group: "On the Roadmap", key: "slack", name: "Slack Notifications", desc: "Push invoice/payment events to Slack channels.",
    ico: "send", bg: "#f5f3ff", fg: "#7c3aed", status: "coming_soon" },
  { group: "On the Roadmap", key: "webhooks", name: "Outbound Webhooks", desc: "POST real-time events to any HTTP endpoint.",
    ico: "webhook", bg: "#ecfeff", fg: "#0891b2", status: "coming_soon" },
  { group: "On the Roadmap", key: "portal", name: "Customer Portal", desc: "Customers log in to view invoices and pay online.",
    ico: "users", bg: "#fef2f2", fg: "#dc2626", status: "coming_soon" },
]);

const groups = computed(() => {
  const order = ["Email & Notifications", "Single Sign-On", "Banking", "GST & E-Invoicing", "Inventory & Stock", "Accounting", "On the Roadmap"];
  const map = {};
  for (const x of integrations.value) (map[x.group] ||= []).push(x);
  return order.filter(l => map[l]).map(l => ({ label: l, items: map[l] }));
});

function byStatus(s) { return integrations.value.filter(x => x.status === s).length; }

async function load() {
  loading.value = true;
  try {
    const co = await resolveCompany();
    const [smtp, company] = await Promise.all([
      apiGET("zoho_books_clone.api.admin.get_company_smtp").catch(() => null),
      apiGet("Books Company", co).catch(() => null),
    ]);
    const v = smtp?.smtp_enabled ?? smtp?.message?.smtp_enabled;
    smtpEnabled.value = !!(v && Number(v));
    companyGstin.value = company?.gstin || "";

    if (companyGstin.value) {
      const [withIrn, submitted] = await Promise.all([
        apiList("Sales Invoice", { fields: ["name"], filters: [["company","=",co],["irn","!=",""],["docstatus","=",1]], limit: 100000 }).catch(() => []),
        apiList("Sales Invoice", { fields: ["name"], filters: [["company","=",co],["docstatus","=",1],["customer_gstin","!=",""]], limit: 100000 }).catch(() => []),
      ]);
      irnGenerated.value = withIrn.length;
      irnPending.value = Math.max(0, submitted.length - withIrn.length);
    }
  } catch (e) { toast.error(e.message || "Failed to load integrations"); }
  finally { loading.value = false; }
}

onMounted(load);
</script>

<style scoped>
.i-page{display:flex;flex-direction:column;gap:18px;padding:24px;}
.i-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap;}
.i-title{font-size:18px;font-weight:700;color:#0f172a;}
.i-sub{font-size:12.5px;color:#64748b;margin-top:2px;max-width:680px;line-height:1.5;}
.i-cta{display:inline-flex;align-items:center;gap:6px;background:#fff;border:1px solid #e2e8f0;color:#334155;border-radius:8px;padding:8px 13px;font-size:13px;font-weight:600;cursor:pointer;}
.i-cta:hover:not(:disabled){background:#f8fafc;border-color:#cbd5e1;}.i-cta:disabled{opacity:.5;cursor:not-allowed;}
.i-loading{padding:40px;text-align:center;color:#94a3b8;}

.i-grid{display:flex;flex-direction:column;gap:16px;}
.i-group-hdr{font-size:11px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;}
.i-cards{display:grid;grid-template-columns:repeat(auto-fill, minmax(340px, 1fr));gap:12px;}
.i-card{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:14px;display:flex;flex-direction:column;gap:8px;transition:border-color .15s,box-shadow .15s;}
.i-card.active{border-color:#bbf7d0;}
.i-card.not_configured{border-color:#fde68a;}
.i-card-top{display:flex;align-items:flex-start;gap:11px;}
.i-card-ico{width:38px;height:38px;border-radius:10px;display:flex;align-items:center;justify-content:center;flex-shrink:0;}
.i-card-meta{flex:1;min-width:0;}
.i-card-name{font-size:13.5px;font-weight:700;color:#0f172a;}
.i-card-desc{font-size:12px;color:#64748b;margin-top:2px;line-height:1.45;}
.i-pill{align-self:flex-start;display:inline-flex;align-items:center;border-radius:20px;padding:2px 9px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap;}
.i-pill.active{background:#dcfce7;color:#16a34a;}
.i-pill.available{background:#dbeafe;color:#1d4ed8;}
.i-pill.not_configured{background:#fef3c7;color:#a16207;}
.i-pill.coming_soon{background:#f1f5f9;color:#64748b;}
.i-note{font-size:11.5px;color:#94a3b8;line-height:1.5;padding:6px 0 0;border-top:1px dashed #eef2f7;}
.i-actions{display:flex;gap:6px;}
.i-link{display:inline-flex;align-items:center;gap:5px;background:#eff6ff;border:1px solid #bfdbfe;color:#1d4ed8;border-radius:7px;padding:5px 10px;font:inherit;font-size:11.5px;font-weight:600;cursor:pointer;}
.i-link:hover{background:#dbeafe;}
</style>
