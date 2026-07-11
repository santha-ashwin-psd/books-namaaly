<template>
<div class="mrx-page">
  <div class="mrx-panel">

    <!-- Header -->
    <div class="mrx-hdr">
      <div>
        <div class="mrx-hdr-title">📊 Manufacturing Reports</div>
        <div class="mrx-hdr-sub">{{ tabs.find(t => t.id === activeTab)?.desc }}</div>
      </div>
      <div style="display:flex;gap:8px;">
        <button v-if="result" class="mrx-btn mrx-btn-light" @click="exportCSV">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          Export CSV
        </button>
        <button class="mrx-btn mrx-btn-mfg" @click="runReport" :disabled="loading">
          <span v-if="loading" class="mrx-spinner"></span>
          <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
          {{ loading ? 'Running…' : 'Run Report' }}
        </button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="mrx-tabs">
      <button v-for="t in tabs" :key="t.id"
        class="mrx-tab" :class="{ active: activeTab === t.id }"
        @click="activeTab = t.id; result = null">
        <span class="mrx-tab-ic">{{ t.icon }}</span> {{ t.label }}
      </button>
    </div>

    <!-- Filters -->
    <div class="mrx-filters">
      <template v-if="activeTab !== 'bom-cost'">
        <div>
          <div class="mrx-hf-label">From Date</div>
          <input type="date" class="mrx-fi" v-model="filters.from_date" />
        </div>
        <div>
          <div class="mrx-hf-label">To Date</div>
          <input type="date" class="mrx-fi" v-model="filters.to_date" />
        </div>
      </template>

      <div v-if="activeTab === 'wo-status' || activeTab === 'performance'">
        <div class="mrx-hf-label">Status</div>
        <select class="mrx-fi" v-model="filters.status">
          <option value="All">All</option>
          <option v-if="activeTab === 'wo-status'" value="Submitted">Submitted</option>
          <option v-if="activeTab === 'wo-status'" value="In Process">In Process</option>
          <option value="Completed">Completed</option>
          <option v-if="activeTab === 'wo-status'" value="Stopped">Stopped</option>
        </select>
      </div>

      <div v-if="activeTab === 'bom-cost'">
        <div class="mrx-hf-label">BOM Type</div>
        <select class="mrx-fi" v-model="filters.bom_type">
          <option value="All">All</option>
          <option value="Manufacturing">Manufacturing</option>
          <option value="Packing">Packing</option>
          <option value="Sub-Assembly">Sub-Assembly</option>
        </select>
      </div>

      <div v-if="activeTab === 'bom-cost'">
        <div class="mrx-hf-label">Active Only</div>
        <select class="mrx-fi" v-model="filters.is_active">
          <option value="">All</option>
          <option value="1">Active</option>
          <option value="0">Inactive</option>
        </select>
      </div>
    </div>

    <!-- Body -->
    <div class="mrx-body">

      <!-- Loading -->
      <div v-if="loading" class="shimmer" style="height:220px;border-radius:10px"></div>

      <template v-else-if="result">
        <!-- KPI strip -->
        <div v-if="summary" class="mrx-kpi-grid" :style="`grid-template-columns:repeat(${summaryKpis.length},1fr)`">
          <div v-for="kpi in summaryKpis" :key="kpi.label" class="mrx-kpi-cell">
            <div class="mrx-kpi-lbl">{{ kpi.label }}</div>
            <div class="mrx-kpi-val" :style="kpi.color ? `color:${kpi.color}` : ''">{{ kpi.value }}</div>
          </div>
        </div>

        <!-- ── Work Order Status table ── -->
        <div v-if="activeTab === 'wo-status'" class="mrx-table-wrap">
          <div v-if="!result.rows.length" class="mrx-empty">No Work Orders found for the selected filters.</div>
          <table v-else class="mrx-table">
            <thead>
              <tr>
                <th>Work Order</th><th>Item</th><th>BOM</th>
                <th style="text-align:right;">Planned Qty</th>
                <th style="text-align:right;">Produced</th>
                <th style="text-align:right;">Completion</th>
                <th>Status</th><th>Created</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in result.rows" :key="r.name" class="mrx-row" @click="router.push(`/manufacturing/work-order/${r.name}`)">
                <td class="mrx-link">{{ r.name }}</td>
                <td>{{ r.item_name }}<div class="mrx-sub">{{ r.production_item }}</div></td>
                <td class="mrx-sub">{{ r.bom || '—' }}</td>
                <td style="text-align:right;">{{ fmt(r.qty) }}</td>
                <td style="text-align:right;">{{ fmt(r.produced_qty) }}</td>
                <td style="text-align:right;">
                  <div style="display:flex;align-items:center;gap:6px;justify-content:flex-end;">
                    <div class="mrx-bar"><div class="mrx-bar-fill" :style="`width:${r.completion_pct}%;background:${r.completion_pct>=100?'var(--bx-green)':'var(--bx-blue)'};`"></div></div>
                    <span>{{ r.completion_pct }}%</span>
                  </div>
                </td>
                <td><span class="mrx-badge" :class="statusClass(r.status)">{{ r.status }}</span></td>
                <td class="mrx-sub">{{ r.creation?.slice(0,10) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- ── Stock Requirement table ── -->
        <div v-if="activeTab === 'stock-req'" class="mrx-table-wrap">
          <div v-if="!result.rows.length" class="mrx-empty">No open Work Orders found — no material requirements.</div>
          <table v-else class="mrx-table">
            <thead>
              <tr>
                <th>Item</th>
                <th style="text-align:right;">Required Qty</th>
                <th style="text-align:right;">On-Hand</th>
                <th style="text-align:right;">Shortfall</th>
                <th>UOM</th><th>Source WH</th>
                <th style="text-align:right;">WOs</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in result.rows" :key="r.item_code" :style="r.shortfall_qty > 0 ? 'background:var(--bx-redS);' : ''">
                <td style="font-weight:600;">{{ r.item_code }}<div class="mrx-sub">{{ r.item_name }}</div></td>
                <td style="text-align:right;">{{ fmt(r.required_qty) }}</td>
                <td style="text-align:right;">{{ fmt(r.on_hand_qty) }}</td>
                <td style="text-align:right;" :style="r.shortfall_qty > 0 ? 'color:var(--bx-red);font-weight:700;' : 'color:var(--bx-green);'">
                  {{ r.shortfall_qty > 0 ? fmt(r.shortfall_qty) : '✓' }}
                </td>
                <td>{{ r.uom }}</td>
                <td class="mrx-sub">{{ r.source_warehouse || '—' }}</td>
                <td style="text-align:right;">{{ r.work_order_count }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- ── BOM Cost Analysis table ── -->
        <div v-if="activeTab === 'bom-cost'" class="mrx-table-wrap">
          <div v-if="!result.rows.length" class="mrx-empty">No submitted BOMs found for the selected filters.</div>
          <table v-else class="mrx-table">
            <thead>
              <tr>
                <th>BOM</th><th>Item</th><th>Type</th>
                <th style="text-align:right;">Qty</th>
                <th style="text-align:right;">RM Cost</th>
                <th style="text-align:right;">Op Cost</th>
                <th style="text-align:right;">Scrap Value</th>
                <th style="text-align:right;">Total Cost</th>
                <th style="text-align:center;">Active</th>
                <th style="text-align:center;">Default</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in result.rows" :key="r.name" class="mrx-row" @click="router.push(`/manufacturing/bom/${r.name}`)">
                <td class="mrx-link" style="font-size:12px;">{{ r.name }}</td>
                <td>{{ r.item_name }}<div class="mrx-sub">{{ r.item }}</div></td>
                <td><span class="mrx-badge badge-changed">{{ r.bom_type }}</span></td>
                <td style="text-align:right;">{{ fmt(r.quantity) }}</td>
                <td style="text-align:right;">{{ fmt(r.rm_cost) }}</td>
                <td style="text-align:right;">{{ fmt(r.op_cost) }}</td>
                <td style="text-align:right;color:var(--bx-red);">{{ fmt(r.scrap_value) }}</td>
                <td style="text-align:right;font-weight:700;color:var(--bx-mfgB);">{{ fmt(r.total_cost) }}</td>
                <td style="text-align:center;">{{ r.is_active ? '✓' : '' }}</td>
                <td style="text-align:center;">{{ r.is_default ? '★' : '' }}</td>
              </tr>
            </tbody>
            <tfoot>
              <tr class="mrx-tfoot">
                <td colspan="4">Totals</td>
                <td style="text-align:right;">{{ fmt(result.summary.total_rm) }}</td>
                <td style="text-align:right;">{{ fmt(result.summary.total_op) }}</td>
                <td></td>
                <td style="text-align:right;color:var(--bx-mfgB);">{{ fmt(result.summary.total_cost) }}</td>
                <td colspan="2"></td>
              </tr>
            </tfoot>
          </table>
        </div>

        <!-- ── Production Performance table ── -->
        <div v-if="activeTab === 'performance'" class="mrx-table-wrap">
          <div v-if="!result.rows.length" class="mrx-empty">No Work Orders found for the selected filters.</div>
          <table v-else class="mrx-table">
            <thead>
              <tr>
                <th>Work Order</th><th>Item</th>
                <th style="text-align:right;">Planned</th>
                <th style="text-align:right;">Produced</th>
                <th style="text-align:right;">Process Loss</th>
                <th style="text-align:right;">Yield %</th>
                <th style="text-align:right;">Efficiency %</th>
                <th>Status</th><th>Created</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in result.rows" :key="r.name" class="mrx-row" @click="router.push(`/manufacturing/work-order/${r.name}`)">
                <td class="mrx-link">{{ r.name }}</td>
                <td>{{ r.item_name }}<div class="mrx-sub">{{ r.production_item }}</div></td>
                <td style="text-align:right;">{{ fmt(r.qty) }}</td>
                <td style="text-align:right;">{{ fmt(r.produced_qty) }}</td>
                <td style="text-align:right;color:var(--bx-red);">{{ fmt(r.process_loss_qty) }}</td>
                <td style="text-align:right;" :style="r.yield_pct < 90 ? 'color:var(--bx-red);font-weight:700;' : 'color:var(--bx-green);font-weight:700;'">{{ r.yield_pct }}%</td>
                <td style="text-align:right;" :style="r.efficiency_pct < 90 ? 'color:var(--bx-mfg);font-weight:700;' : ''">{{ r.efficiency_pct }}%</td>
                <td><span class="mrx-badge" :class="statusClass(r.status)">{{ r.status }}</span></td>
                <td class="mrx-sub">{{ r.creation?.slice(0,10) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <!-- Empty state before first run -->
      <div v-else class="mrx-empty-state">
        <div class="mrx-empty-icon">📊</div>
        <div class="mrx-empty-title">No report generated yet</div>
        <div class="mrx-empty-sub">Set your filters above and click "Run Report" to view results.</div>
      </div>

    </div>
  </div>
</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { apiCall } from "../api/client.js";
import { useToast } from "../composables/useToast.js";

const router = useRouter();
const { toast } = useToast();

const activeTab = ref("wo-status");
const tabs = [
  { id: "wo-status",   label: "Work Order Status",       icon: "📋", desc: "Track progress and completion of all work orders." },
  { id: "stock-req",   label: "Stock Requirement",       icon: "📦", desc: "Material needs and shortfalls across open work orders." },
  { id: "bom-cost",    label: "BOM Cost Analysis",       icon: "💰", desc: "Cost breakdown of raw materials, operations, and scrap per BOM." },
  { id: "performance", label: "Production Performance",  icon: "⚙️", desc: "Yield, efficiency, and process loss across completed runs." },
];

const today = new Date().toISOString().slice(0, 10);
const firstOfMonth = today.slice(0, 8) + "01";
const filters = ref({
  from_date: firstOfMonth,
  to_date: today,
  status: "All",
  bom_type: "All",
  is_active: "",
});

const loading = ref(false);
const result = ref(null);

const API_MAP = {
  "wo-status":   "zoho_books_clone.manufacturing.reports.get_work_order_status_report",
  "stock-req":   "zoho_books_clone.manufacturing.reports.get_stock_requirement_report",
  "bom-cost":    "zoho_books_clone.manufacturing.reports.get_bom_cost_analysis",
  "performance": "zoho_books_clone.manufacturing.reports.get_production_performance_report",
};

async function runReport() {
  loading.value = true;
  result.value = null;
  try {
    const data = await apiCall(API_MAP[activeTab.value], { filters: filters.value });
    result.value = data;
  } catch (e) {
    toast("Report failed: " + e.message, "error");
  }
  loading.value = false;
}

const summary = computed(() => result.value?.summary || null);

const summaryKpis = computed(() => {
  if (!summary.value) return [];
  const s = summary.value;
  if (activeTab.value === "wo-status") return [
    { label: "Total", value: s.total },
    { label: "In Process", value: s.in_process, color: "var(--bx-blue)" },
    { label: "Completed", value: s.completed, color: "var(--bx-green)" },
    { label: "Stopped", value: s.stopped, color: "var(--bx-red)" },
  ];
  if (activeTab.value === "stock-req") return [
    { label: "Materials Needed", value: s.total_items },
    { label: "With Shortfall", value: s.shortfall_items, color: s.shortfall_items > 0 ? "var(--bx-red)" : "var(--bx-green)" },
    { label: "Sufficient", value: s.total_items - s.shortfall_items, color: "var(--bx-green)" },
  ];
  if (activeTab.value === "bom-cost") return [
    { label: "BOMs", value: s.total_boms },
    { label: "Total RM Cost", value: fmt(s.total_rm) },
    { label: "Total Op Cost", value: fmt(s.total_op) },
    { label: "Total Cost", value: fmt(s.total_cost), color: "var(--bx-mfgB)" },
  ];
  if (activeTab.value === "performance") return [
    { label: "Orders", value: s.total_orders },
    { label: "Planned", value: fmt(s.total_planned) },
    { label: "Produced", value: fmt(s.total_produced) },
    { label: "Avg Yield", value: s.avg_yield_pct + "%", color: s.avg_yield_pct >= 90 ? "var(--bx-green)" : "var(--bx-red)" },
    { label: "Avg Efficiency", value: s.avg_efficiency + "%", color: s.avg_efficiency >= 90 ? "var(--bx-green)" : "var(--bx-mfg)" },
  ];
  return [];
});

function fmt(val) {
  const n = parseFloat(val) || 0;
  return n.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function statusClass(status) {
  const map = {
    "Completed":  "badge-active",
    "In Process": "badge-changed",
    "Submitted":  "badge-draft",
    "Stopped":    "badge-removed",
    "Cancelled":  "badge-obsolete",
    "Draft":      "badge-obsolete",
  };
  return map[status] || "badge-obsolete";
}

function exportCSV() {
  if (!result.value?.rows?.length) return;
  const rows = result.value.rows;
  const keys = Object.keys(rows[0]);
  const lines = [
    keys.join(","),
    ...rows.map(r => keys.map(k => JSON.stringify(r[k] ?? "")).join(","))
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${activeTab.value}-report-${today}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

onMounted(() => runReport());
</script>

<style scoped>
.mrx-page {
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
.mrx-panel { background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; display:flex; flex-direction:column; min-height: calc(100vh - 32px); }

.mrx-hdr { padding:18px 22px; background:linear-gradient(135deg, var(--bx-mfgB), var(--bx-mfg)); display:flex; align-items:flex-start; justify-content:space-between; gap:12px; }
.mrx-hdr-title { font-size:18px; font-weight:700; color:#fff; margin-bottom:4px; }
.mrx-hdr-sub { font-size:12.5px; color:rgba(255,255,255,.75); }

.mrx-tabs { display:flex; border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); padding:0 22px; overflow-x:auto; }
.mrx-tab { display:flex; align-items:center; gap:6px; padding:10px 16px; font-size:13px; font-weight:600; cursor:pointer; border:none; background:none; color:var(--bx-muted); border-bottom:2px solid transparent; margin-bottom:-1px; white-space:nowrap; }
.mrx-tab-ic { font-size:13px; }
.mrx-tab.active { color:var(--bx-mfg); border-bottom-color:var(--bx-mfg); }

.mrx-filters { display:flex; gap:12px; flex-wrap:wrap; align-items:flex-end; padding:16px 22px; border-bottom:1px solid var(--bx-border); background:var(--bx-surf2); }
.mrx-hf-label { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); margin-bottom:4px; }

.mrx-body { padding:20px 22px; overflow-y:auto; flex:1; }

/* ── KPI strip ── */
.mrx-kpi-grid { display:grid; gap:10px; margin-bottom:18px; }
.mrx-kpi-cell { background:var(--bx-mfgS); border:1px solid rgba(180,83,9,.15); border-radius:var(--bx-rsm); padding:12px 14px; }
.mrx-kpi-lbl { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-mfg); margin-bottom:4px; }
.mrx-kpi-val { font-size:19px; font-weight:700; color:var(--bx-text); }
@media (max-width:900px) { .mrx-kpi-grid { grid-template-columns:1fr 1fr !important; } }

/* ── Table ── */
.mrx-table-wrap { overflow-x:auto; border:1px solid var(--bx-border); border-radius:var(--bx-rsm); }
.mrx-empty { text-align:center; padding:32px; color:var(--bx-muted); font-size:13px; }
.mrx-table { width:100%; border-collapse:collapse; font-size:13px; }
.mrx-table th { text-align:left; padding:8px 12px; border-bottom:1px solid var(--bx-border); color:var(--bx-muted); font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; background:var(--bx-surf2); white-space:nowrap; }
.mrx-table td { padding:9px 12px; border-bottom:1px solid #F1F3F5; vertical-align:middle; }
.mrx-row { cursor:pointer; transition:background .1s; }
.mrx-row:hover { background:#FAFBFF; }
.mrx-link { color:var(--bx-mfg); font-weight:600; }
.mrx-sub { font-size:11px; color:var(--bx-muted); }
.mrx-bar { width:60px; height:6px; background:#E5E7EB; border-radius:3px; overflow:hidden; }
.mrx-bar-fill { height:100%; border-radius:3px; }
.mrx-tfoot td { background:var(--bx-mfgS); font-weight:700; color:var(--bx-mfgB); }

/* ── Badges ── */
.mrx-badge { display:inline-flex; align-items:center; padding:2px 8px; border-radius:20px; font-size:11px; font-weight:600; white-space:nowrap; }
.badge-active { background:var(--bx-greenS); color:var(--bx-green); }
.badge-draft { background:var(--bx-amberS); color:var(--bx-amber); }
.badge-obsolete { background:#F1F3F5; color:var(--bx-muted); }
.badge-changed { background:var(--bx-blueS); color:var(--bx-blue); }
.badge-removed { background:var(--bx-redS); color:var(--bx-red); }

/* ── Empty state ── */
.mrx-empty-state { text-align:center; padding:60px 20px; color:var(--bx-muted); }
.mrx-empty-icon { font-size:48px; margin-bottom:14px; }
.mrx-empty-title { font-size:16px; font-weight:700; color:var(--bx-text); margin-bottom:6px; }
.mrx-empty-sub { font-size:13px; line-height:1.6; max-width:320px; margin:0 auto; }

/* ── Buttons / inputs ── */
.mrx-fi { border:1px solid #CDD5E0; border-radius:var(--bx-rsm); padding:7px 9px; font-size:13px; color:var(--bx-text); background:#fff; outline:none; min-width:140px; }
.mrx-fi:focus { border-color:var(--bx-mfg); box-shadow:0 0 0 3px rgba(180,83,9,.1); }
select.mrx-fi {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  padding-right: 30px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%239ca3af' stroke-width='2.5'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
}
.mrx-btn { display:inline-flex; align-items:center; gap:6px; padding:8px 16px; border-radius:var(--bx-rsm); font-size:13px; font-weight:600; cursor:pointer; border:1px solid transparent; line-height:1; white-space:nowrap; }
.mrx-btn:disabled { opacity:.6; cursor:not-allowed; }
.mrx-btn-mfg { background:var(--bx-mfg); color:#fff; }
.mrx-btn-mfg:hover:not(:disabled) { background:var(--bx-mfgB); }
.mrx-btn-light { background:#fff; color:var(--bx-mfgB); border:1px solid var(--bx-border); }
.mrx-btn-light:hover:not(:disabled) { background:var(--bx-surf2); }

.mrx-spinner { display:inline-block;width:11px;height:11px;border:2px solid rgba(255,255,255,.4);border-top-color:#fff;border-radius:50%;animation:spin .6s linear infinite; }
@keyframes spin { to { transform: rotate(360deg) } }

.shimmer { background:linear-gradient(90deg,#f1f3f5 25%,#e9ecef 37%,#f1f3f5 63%); background-size:400% 100%; animation:shimmer 1.4s ease infinite; }
@keyframes shimmer { 0%{background-position:100% 50%} 100%{background-position:0 50%} }
</style>