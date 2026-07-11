<template>
<div class="mdx-page">

  <!-- Header -->
  <div class="mdx-hdr">
    <div>
      <div class="mdx-hdr-title">🏭 Manufacturing</div>
      <div class="mdx-hdr-sub">Where things stand across BOMs, Work Orders, and the shop floor right now.</div>
    </div>
    <button class="mdx-btn mdx-btn-light" @click="loadAll" :disabled="loading">
      <span v-if="loading" class="mdx-spinner"></span>
      <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
      {{ loading ? 'Refreshing…' : 'Refresh' }}
    </button>
  </div>

  <!-- KPI grid -->
  <div class="mdx-kpi-grid">
    <div v-for="k in kpiTiles" :key="k.key" class="mdx-kpi-card" :class="{ 'mdx-kpi-card--warn': k.warn && kpis[k.key] > 0 }" @click="k.go && k.go()">
      <div class="mdx-kpi-top">
        <span class="mdx-kpi-icon" :style="{ background: k.iconBg, color: k.iconColor }">{{ k.icon }}</span>
        <span class="mdx-kpi-label">{{ k.label }}</span>
      </div>
      <div class="mdx-kpi-value">
        <div v-if="loading" class="shimmer" style="width:48px;height:24px;border-radius:5px"></div>
        <template v-else>{{ kpis[k.key] ?? 0 }}</template>
      </div>
      <div class="mdx-kpi-foot">{{ k.foot }}</div>
    </div>
  </div>

  <div class="mdx-mid-grid">

    <!-- Attention Needed -->
    <div class="mdx-card">
      <div class="mdx-card-hdr">
        <span class="mdx-card-title">⚠️ Needs Attention</span>
      </div>
      <div v-if="loading" class="mdx-attn-list">
        <div v-for="n in 3" :key="n" class="shimmer" style="height:44px;border-radius:8px"></div>
      </div>
      <div v-else-if="!attentionItems.length" class="mdx-empty">
        <div class="mdx-empty-icon">✅</div>
        <div class="mdx-empty-title">All clear</div>
        <div class="mdx-empty-sub">No stopped Work Orders or failed inspections right now.</div>
      </div>
      <div v-else class="mdx-attn-list">
        <div v-for="a in attentionItems" :key="a.key" class="mdx-attn-row" @click="a.go()">
          <span class="mdx-attn-dot" :style="{ background: a.color }"></span>
          <div class="mdx-attn-body">
            <div class="mdx-attn-title">{{ a.title }}</div>
            <div class="mdx-attn-sub">{{ a.sub }}</div>
          </div>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="color:var(--bx-muted);flex-shrink:0"><polyline points="9 18 15 12 9 6"/></svg>
        </div>
      </div>
    </div>

    <!-- Recent Work Orders -->
    <div class="mdx-card" style="grid-column:span 2">
      <div class="mdx-card-hdr">
        <span class="mdx-card-title">Recent Work Orders</span>
        <button class="mdx-link-btn" @click="router.push('/manufacturing/work-order')">View all</button>
      </div>
      <div v-if="loading" class="mdx-attn-list">
        <div v-for="n in 5" :key="n" class="shimmer" style="height:38px;border-radius:8px"></div>
      </div>
      <div v-else-if="!recentWOs.length" class="mdx-empty">
        <div class="mdx-empty-icon">🏭</div>
        <div class="mdx-empty-title">No Work Orders yet</div>
        <div class="mdx-empty-sub">Create one from a submitted BOM to start production.</div>
        <button class="mdx-empty-btn" @click="router.push('/manufacturing/work-order/new')">+ New Work Order</button>
      </div>
      <table v-else class="mdx-table">
        <thead><tr><th>Work Order</th><th>Item</th><th>Progress</th><th>Status</th></tr></thead>
        <tbody>
          <tr v-for="wo in recentWOs" :key="wo.name" @click="router.push('/manufacturing/work-order/' + wo.name)">
            <td class="mono" style="font-weight:600">{{ wo.name }}</td>
            <td>{{ wo.item_name || wo.production_item }}</td>
            <td>
              <div class="mdx-prog-wrap">
                <div class="mdx-prog-bar"><div class="mdx-prog-fill" :style="{ width: progressPct(wo) + '%' }"></div></div>
                <span class="mdx-prog-txt">{{ fmtNum(wo.produced_qty) }}/{{ fmtNum(wo.qty) }}</span>
              </div>
            </td>
            <td><span class="mdx-badge" :class="statusClass(wo.status)">{{ wo.status }}</span></td>
          </tr>
        </tbody>
      </table>
    </div>

  </div>

  <!-- Quick Links -->
  <div class="mdx-card" style="margin-top:14px">
    <div class="mdx-card-hdr"><span class="mdx-card-title">Quick Links</span></div>
    <div class="mdx-links-grid">
      <button v-for="l in quickLinks" :key="l.path" class="mdx-link-tile" @click="router.push(l.path)">
        <span class="mdx-link-icon">{{ l.icon }}</span>
        <span class="mdx-link-label">{{ l.label }}</span>
      </button>
    </div>
  </div>

</div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { apiList } from "../api/client.js";
import { useToast } from "../composables/useToast.js";

const router = useRouter();
const { toast } = useToast();

const loading = ref(false);
const kpis = ref({});
const recentWOs = ref([]);
const stoppedWOs = ref([]);
const qcFails = ref([]);

const kpiTiles = [
  { key: "in_process",  label: "In Process",      icon: "⚙️", iconBg: "var(--bx-mfgS)", iconColor: "var(--bx-mfg)",  foot: "Work Orders running",
    go: () => router.push({ path: "/manufacturing/work-order", query: { status: "In Process" } }) },
  { key: "due_soon",    label: "Due This Week",   icon: "📅", iconBg: "#FFF3BF",        iconColor: "#E67700",        foot: "Planned end within 7 days",
    go: () => router.push("/manufacturing/work-order") },
  { key: "jc_running",  label: "Job Cards Live",  icon: "🗂️", iconBg: "#E7F5FF",        iconColor: "#1971C2",        foot: "Currently in progress",
    go: () => router.push({ path: "/manufacturing/job-card", query: { status: "Work In Progress" } }) },
  { key: "qc_pending",  label: "QC Pending",      icon: "🔬", iconBg: "#F3F0FF",        iconColor: "#7048E8",        foot: "Awaiting inspection",
    go: () => router.push("/quality/inspections") },
  { key: "mr_pending",  label: "Material Reqs",   icon: "📦", iconBg: "#EBFBEE",        iconColor: "#2F9E44",        foot: "Draft / Submitted",
    go: () => router.push("/manufacturing/material-request") },
  { key: "wo_stopped",  label: "Stopped",         icon: "🛑", iconBg: "#FFF5F5",        iconColor: "#C92A2A",        foot: "Work Orders halted", warn: true,
    go: () => router.push({ path: "/manufacturing/work-order", query: { status: "Stopped" } }) },
];

const quickLinks = [
  { path: "/manufacturing/bom",              icon: "📋", label: "Bill of Materials" },
  { path: "/manufacturing/work-order",       icon: "🏭", label: "Work Orders" },
  { path: "/manufacturing/job-card",         icon: "🗂️", label: "Job Cards" },
  { path: "/manufacturing/production-plan",  icon: "📊", label: "Production Plan" },
  { path: "/manufacturing/material-request", icon: "📦", label: "Material Requests" },
  { path: "/manufacturing/routing",          icon: "🔁", label: "Routing" },
  { path: "/manufacturing/workstation",      icon: "⚙️", label: "Workstations" },
  { path: "/manufacturing/packing-slip",     icon: "🏷️", label: "Packing Slips" },
  { path: "/manufacturing/reports",          icon: "📈", label: "Reports" },
  { path: "/manufacturing/settings",         icon: "🔧", label: "Settings" },
];

const attentionItems = ref([]);

function buildAttention() {
  const items = [];
  for (const wo of stoppedWOs.value) {
    items.push({
      key: "wo-" + wo.name,
      color: "var(--bx-red)",
      title: `${wo.name} is stopped`,
      sub: `${wo.item_name || wo.production_item} — resume it to continue production.`,
      go: () => router.push("/manufacturing/work-order/" + wo.name),
    });
  }
  for (const qi of qcFails.value) {
    items.push({
      key: "qc-" + qi.name,
      color: "var(--bx-amber)",
      title: `${qi.name} failed inspection`,
      sub: `${qi.item_name || qi.item} — review before dispatch.`,
      go: () => router.push("/quality/inspections?open=" + qi.name),
    });
  }
  attentionItems.value = items;
}

function progressPct(wo) {
  const qty = parseFloat(wo.qty) || 0;
  if (!qty) return 0;
  return Math.min(100, Math.round(((parseFloat(wo.produced_qty) || 0) / qty) * 100));
}
function fmtNum(n) {
  return (parseFloat(n) || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });
}
function statusClass(status) {
  const map = {
    "Completed":   "mdx-badge-green",
    "In Process":  "mdx-badge-blue",
    "Submitted":   "mdx-badge-amber",
    "Stopped":     "mdx-badge-red",
    "Cancelled":   "mdx-badge-grey",
    "Draft":       "mdx-badge-grey",
  };
  return map[status] || "mdx-badge-grey";
}

async function loadAll() {
  loading.value = true;
  try {
    const today = new Date();
    const weekOut = new Date(today.getTime() + 7 * 24 * 3600 * 1000);
    const todayStr = today.toISOString().slice(0, 10);
    const weekStr = weekOut.toISOString().slice(0, 10);

    const [inProcess, dueSoon, jcRunning, qcRows, mrPending, stopped, recent] = await Promise.all([
      apiList("Work Order", { fields: ["name"], filters: [["status", "=", "In Process"]], limit: 1000 }).catch(() => []),
      apiList("Work Order", { fields: ["name"], filters: [
        ["status", "not in", ["Completed", "Cancelled"]],
        ["planned_end_date", ">=", todayStr],
        ["planned_end_date", "<=", weekStr],
      ], limit: 1000 }).catch(() => []),
      apiList("Job Card", { fields: ["name"], filters: [["status", "=", "Work In Progress"]], limit: 1000 }).catch(() => []),
      apiList("QC Inspection", { fields: ["name", "status", "docstatus", "item", "item_name"], filters: [["docstatus", "!=", 2]], limit: 1000 }).catch(() => []),
      apiList("Material Request", { fields: ["name"], filters: [["status", "in", ["Draft", "Submitted"]]], limit: 1000 }).catch(() => []),
      apiList("Work Order", { fields: ["name", "item_name", "production_item"], filters: [["status", "=", "Stopped"]], limit: 100 }).catch(() => []),
      apiList("Work Order", { fields: ["name", "item_name", "production_item", "status", "qty", "produced_qty", "modified"], limit: 8, order: "modified desc" }).catch(() => []),
    ]);

    const pending = (qcRows || []).filter(q => q.status === "Pending" || q.docstatus === 0);
    const fails = (qcRows || []).filter(q => q.status === "Fail");

    kpis.value = {
      in_process: (inProcess || []).length,
      due_soon: (dueSoon || []).length,
      jc_running: (jcRunning || []).length,
      qc_pending: pending.length,
      mr_pending: (mrPending || []).length,
      wo_stopped: (stopped || []).length,
    };
    stoppedWOs.value = stopped || [];
    qcFails.value = fails;
    recentWOs.value = recent || [];
    buildAttention();
  } catch (e) {
    toast("Could not load dashboard data: " + e.message, "error");
  }
  loading.value = false;
}

onMounted(loadAll);
</script>

<style scoped>
.mdx-page {
  --bx-bg:#F3F4F6; --bx-surface:#FFFFFF; --bx-surf2:#F8F9FC; --bx-border:#E2E8F0;
  --bx-text:#1A1D23; --bx-muted:#868E96;
  --bx-green:#2F9E44; --bx-greenS:#EBFBEE;
  --bx-red:#C92A2A; --bx-redS:#FFF5F5;
  --bx-amber:#E67700; --bx-amberS:#FFF3BF;
  --bx-blue:#1971C2; --bx-blueS:#E7F5FF;
  --bx-mfg:#1a6ef7; --bx-mfgL:#2f74f5; --bx-mfgS:#EAF1FF; --bx-mfgB:#1e3a5f;
  --bx-radius:10px; --bx-rsm:6px;
  padding: 16px;
}

.mdx-hdr { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; margin-bottom:16px; }
.mdx-hdr-title { font-size:20px; font-weight:800; color:var(--bx-text); }
.mdx-hdr-sub { font-size:13px; color:var(--bx-muted); margin-top:2px; }

.mdx-btn { display:inline-flex; align-items:center; gap:6px; padding:8px 16px; border-radius:var(--bx-rsm); font-size:13px; font-weight:600; cursor:pointer; border:1px solid var(--bx-border); line-height:1; white-space:nowrap; }
.mdx-btn:disabled { opacity:.6; cursor:not-allowed; }
.mdx-btn-light { background:#fff; color:var(--bx-mfgB); }
.mdx-btn-light:hover:not(:disabled) { background:var(--bx-mfgS); border-color:var(--bx-mfg); }
.mdx-spinner { display:inline-block;width:11px;height:11px;border:2px solid rgba(26,110,247,.25);border-top-color:var(--bx-mfg);border-radius:50%;animation:mdx-spin .6s linear infinite; }
@keyframes mdx-spin { to { transform: rotate(360deg) } }

/* KPI grid */
.mdx-kpi-grid { display:grid; grid-template-columns:repeat(6,1fr); gap:12px; margin-bottom:14px; }
@media (max-width:1100px) { .mdx-kpi-grid { grid-template-columns:repeat(3,1fr); } }
@media (max-width:640px)  { .mdx-kpi-grid { grid-template-columns:repeat(2,1fr); } }

.mdx-kpi-card { background:#fff; border:1px solid var(--bx-border); border-radius:var(--bx-radius); padding:14px 16px; cursor:pointer; transition:box-shadow .12s, border-color .12s; }
.mdx-kpi-card:hover { border-color:var(--bx-mfg); box-shadow:0 2px 8px rgba(26,110,247,.08); }
.mdx-kpi-card--warn { border-color:rgba(201,42,42,.25); }
.mdx-kpi-top { display:flex; align-items:center; gap:8px; margin-bottom:8px; }
.mdx-kpi-icon { width:26px; height:26px; border-radius:7px; display:flex; align-items:center; justify-content:center; font-size:13px; flex-shrink:0; }
.mdx-kpi-label { font-size:11.5px; font-weight:700; color:var(--bx-muted); text-transform:uppercase; letter-spacing:.03em; }
.mdx-kpi-value { font-size:24px; font-weight:800; color:var(--bx-text); line-height:1; }
.mdx-kpi-foot { font-size:11px; color:var(--bx-muted); margin-top:6px; }

/* Middle grid */
.mdx-mid-grid { display:grid; grid-template-columns:1fr 2fr; gap:14px; }
@media (max-width:1000px) { .mdx-mid-grid { grid-template-columns:1fr; } .mdx-mid-grid > div { grid-column:auto !important; } }

.mdx-card { background:#fff; border:1px solid var(--bx-border); border-radius:var(--bx-radius); padding:16px 18px; }
.mdx-card-hdr { display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; }
.mdx-card-title { font-size:14px; font-weight:700; color:var(--bx-text); }
.mdx-link-btn { background:none; border:none; cursor:pointer; font-size:12.5px; font-weight:600; color:var(--bx-mfg); font-family:inherit; padding:0; }
.mdx-link-btn:hover { text-decoration:underline; }

/* Attention list */
.mdx-attn-list { display:flex; flex-direction:column; gap:8px; }
.mdx-attn-row { display:flex; align-items:center; gap:10px; padding:9px 10px; border-radius:var(--bx-rsm); cursor:pointer; border:1px solid var(--bx-border); }
.mdx-attn-row:hover { background:var(--bx-surf2); }
.mdx-attn-dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
.mdx-attn-body { flex:1; min-width:0; }
.mdx-attn-title { font-size:13px; font-weight:600; color:var(--bx-text); }
.mdx-attn-sub { font-size:11.5px; color:var(--bx-muted); margin-top:1px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }

/* Empty state */
.mdx-empty { display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; padding:28px 10px; }
.mdx-empty-icon { font-size:30px; margin-bottom:8px; }
.mdx-empty-title { font-size:13.5px; font-weight:700; color:var(--bx-text); }
.mdx-empty-sub { font-size:12px; color:var(--bx-muted); margin-top:4px; max-width:220px; line-height:1.5; }
.mdx-empty-btn { margin-top:12px; background:var(--bx-mfg); color:#fff; border:none; border-radius:var(--bx-rsm); padding:7px 14px; font-size:12.5px; font-weight:600; cursor:pointer; }
.mdx-empty-btn:hover { background:var(--bx-mfgB); }

/* Table */
.mdx-table { width:100%; border-collapse:collapse; font-size:13px; }
.mdx-table th { text-align:left; font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); padding:0 10px 8px; }
.mdx-table td { padding:9px 10px; border-top:1px solid #F1F3F5; color:var(--bx-text); }
.mdx-table tbody tr { cursor:pointer; }
.mdx-table tbody tr:hover td { background:var(--bx-surf2); }
.mono { font-family: ui-monospace, monospace; }

.mdx-prog-wrap { display:flex; align-items:center; gap:8px; }
.mdx-prog-bar { width:80px; height:6px; background:#E9ECEF; border-radius:20px; overflow:hidden; }
.mdx-prog-fill { height:100%; background:linear-gradient(135deg,var(--bx-mfgL),var(--bx-mfg)); border-radius:20px; }
.mdx-prog-txt { font-size:11.5px; color:var(--bx-muted); white-space:nowrap; }

.mdx-badge { display:inline-flex; align-items:center; padding:2px 8px; border-radius:20px; font-size:11px; font-weight:600; white-space:nowrap; }
.mdx-badge-green { background:var(--bx-greenS); color:var(--bx-green); }
.mdx-badge-blue  { background:var(--bx-blueS);  color:var(--bx-blue); }
.mdx-badge-amber { background:var(--bx-amberS); color:var(--bx-amber); }
.mdx-badge-red   { background:var(--bx-redS);   color:var(--bx-red); }
.mdx-badge-grey  { background:#F1F3F5; color:var(--bx-muted); }

/* Quick links */
.mdx-links-grid { display:grid; grid-template-columns:repeat(5,1fr); gap:10px; }
@media (max-width:900px) { .mdx-links-grid { grid-template-columns:repeat(3,1fr); } }
@media (max-width:520px) { .mdx-links-grid { grid-template-columns:repeat(2,1fr); } }
.mdx-link-tile { display:flex; flex-direction:column; align-items:center; gap:6px; padding:14px 8px; border:1px solid var(--bx-border); border-radius:var(--bx-radius); background:var(--bx-surf2); cursor:pointer; font-family:inherit; }
.mdx-link-tile:hover { border-color:var(--bx-mfg); background:var(--bx-mfgS); }
.mdx-link-icon { font-size:20px; }
.mdx-link-label { font-size:12px; font-weight:600; color:var(--bx-text); text-align:center; }

.shimmer { background:linear-gradient(90deg,#f1f3f5 25%,#e9ecef 37%,#f1f3f5 63%); background-size:400% 100%; animation:mdx-shimmer 1.4s ease infinite; }
@keyframes mdx-shimmer { 0%{background-position:100% 50%} 100%{background-position:0 50%} }
</style>