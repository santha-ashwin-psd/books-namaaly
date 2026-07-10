<template>
<div class="sc-page">
  <div class="sc-sticky">
    <div class="sc-header">
      <span class="sc-title">Manufacturing Reports</span>
    </div>
    <div class="sc-tabs">
      <button v-for="t in tabs" :key="t.id"
        class="sc-tab" :class="{ 'sc-tab--active': activeTab === t.id }"
        @click="activeTab = t.id; result = null">
        {{ t.label }}
      </button>
    </div>
  </div>

  <div class="sc-body sc-body--narrow">
    <div class="sc-col-main">

      <!-- Filter card -->
      <div class="sc-card">
        <div class="sc-fg" style="align-items:flex-end;gap:10px;flex-wrap:wrap;">
          <!-- Date range (not shown for BOM Cost Analysis) -->
          <template v-if="activeTab !== 'bom-cost'">
            <div class="nim-field" style="min-width:140px;">
              <label class="nim-label">From Date</label>
              <input type="date" class="nim-input" v-model="filters.from_date" />
            </div>
            <div class="nim-field" style="min-width:140px;">
              <label class="nim-label">To Date</label>
              <input type="date" class="nim-input" v-model="filters.to_date" />
            </div>
          </template>

          <!-- Status filter -->
          <div class="nim-field" v-if="activeTab === 'wo-status' || activeTab === 'performance'">
            <label class="nim-label">Status</label>
            <select class="nim-input" v-model="filters.status">
              <option value="All">All</option>
              <option v-if="activeTab === 'wo-status'" value="Submitted">Submitted</option>
              <option v-if="activeTab === 'wo-status'" value="In Process">In Process</option>
              <option value="Completed">Completed</option>
              <option v-if="activeTab === 'wo-status'" value="Stopped">Stopped</option>
            </select>
          </div>

          <!-- BOM Type filter -->
          <div class="nim-field" v-if="activeTab === 'bom-cost'">
            <label class="nim-label">BOM Type</label>
            <select class="nim-input" v-model="filters.bom_type">
              <option value="All">All</option>
              <option value="Manufacturing">Manufacturing</option>
              <option value="Packing">Packing</option>
              <option value="Sub-Assembly">Sub-Assembly</option>
            </select>
          </div>

          <!-- Active filter -->
          <div class="nim-field" v-if="activeTab === 'bom-cost'">
            <label class="nim-label">Active Only</label>
            <select class="nim-input" v-model="filters.is_active">
              <option value="">All</option>
              <option value="1">Active</option>
              <option value="0">Inactive</option>
            </select>
          </div>

          <div style="display:flex;gap:8px;margin-bottom:1px;">
            <button class="sc-save-btn" @click="runReport" :disabled="loading">
              <span v-if="loading" style="display:inline-block;width:11px;height:11px;border:2px solid rgba(255,255,255,.4);border-top-color:#fff;border-radius:50%;animation:spin .6s linear infinite;margin-right:6px;"></span>
              {{ loading ? 'Running…' : 'Run Report' }}
            </button>
            <button v-if="result" class="nim-btn" style="background:#f0fdf4;color:#16a34a;border:1px solid #bbf7d0;padding:8px 14px;border-radius:8px;font-weight:600;cursor:pointer;" @click="exportCSV">
              Export CSV
            </button>
          </div>
        </div>
      </div>

      <!-- Summary KPI strip -->
      <div v-if="result && summary" class="sc-card" style="padding:0;overflow:hidden;">
        <div style="display:flex;background:#f8f9fc;border-bottom:1px solid #e8ecf2;">
          <div v-for="kpi in summaryKpis" :key="kpi.label"
            style="flex:1;padding:14px 20px;border-right:1px solid #e8ecf2;">
            <div style="font-size:11px;color:#6b7280;font-weight:600;text-transform:uppercase;margin-bottom:4px;">{{ kpi.label }}</div>
            <div style="font-size:18px;font-weight:700;" :style="kpi.color ? `color:${kpi.color}` : ''">{{ kpi.value }}</div>
          </div>
        </div>
      </div>

      <!-- ── Work Order Status table ── -->
      <div v-if="activeTab === 'wo-status' && result" class="sc-card" style="overflow-x:auto;">
        <div v-if="!result.rows.length" style="padding:24px;text-align:center;color:#9ca3af;">No Work Orders found for the selected filters.</div>
        <table v-else style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead>
            <tr style="background:#f9fafb;">
              <th class="rth">Work Order</th>
              <th class="rth">Item</th>
              <th class="rth">BOM</th>
              <th class="rth" style="text-align:right;">Planned Qty</th>
              <th class="rth" style="text-align:right;">Produced</th>
              <th class="rth" style="text-align:right;">Completion</th>
              <th class="rth">Status</th>
              <th class="rth">Created</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in result.rows" :key="r.name" class="sc-list-row" @click="router.push(`/manufacturing/work-order/${r.name}`)">
              <td class="rtd" style="color:#2563eb;font-weight:600;">{{ r.name }}</td>
              <td class="rtd">{{ r.item_name }}<div style="font-size:11px;color:#9ca3af;">{{ r.production_item }}</div></td>
              <td class="rtd" style="font-size:12px;color:#6b7280;">{{ r.bom || '—' }}</td>
              <td class="rtd" style="text-align:right;">{{ fmt(r.qty) }}</td>
              <td class="rtd" style="text-align:right;">{{ fmt(r.produced_qty) }}</td>
              <td class="rtd" style="text-align:right;">
                <div style="display:flex;align-items:center;gap:6px;justify-content:flex-end;">
                  <div style="width:60px;height:6px;background:#e5e7eb;border-radius:3px;overflow:hidden;">
                    <div :style="`width:${r.completion_pct}%;height:100%;background:${r.completion_pct>=100?'#16a34a':'#2563eb'};border-radius:3px;`"></div>
                  </div>
                  <span>{{ r.completion_pct }}%</span>
                </div>
              </td>
              <td class="rtd"><span :style="statusBadge(r.status)">{{ r.status }}</span></td>
              <td class="rtd" style="font-size:12px;color:#6b7280;">{{ r.creation?.slice(0,10) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- ── Stock Requirement table ── -->
      <div v-if="activeTab === 'stock-req' && result" class="sc-card" style="overflow-x:auto;">
        <div v-if="!result.rows.length" style="padding:24px;text-align:center;color:#9ca3af;">No open Work Orders found — no material requirements.</div>
        <table v-else style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead>
            <tr style="background:#f9fafb;">
              <th class="rth">Item</th>
              <th class="rth" style="text-align:right;">Required Qty</th>
              <th class="rth" style="text-align:right;">On-Hand</th>
              <th class="rth" style="text-align:right;">Shortfall</th>
              <th class="rth">UOM</th>
              <th class="rth">Source WH</th>
              <th class="rth" style="text-align:right;">WOs</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in result.rows" :key="r.item_code"
              :style="r.shortfall_qty > 0 ? 'background:#fef2f2;' : ''"
              style="border-bottom:1px solid #f3f4f6;">
              <td class="rtd" style="font-weight:600;">{{ r.item_code }}<div style="font-size:11px;color:#9ca3af;">{{ r.item_name }}</div></td>
              <td class="rtd" style="text-align:right;">{{ fmt(r.required_qty) }}</td>
              <td class="rtd" style="text-align:right;">{{ fmt(r.on_hand_qty) }}</td>
              <td class="rtd" style="text-align:right;" :style="r.shortfall_qty > 0 ? 'color:#dc2626;font-weight:700;' : 'color:#16a34a;'">
                {{ r.shortfall_qty > 0 ? fmt(r.shortfall_qty) : '✓' }}
              </td>
              <td class="rtd">{{ r.uom }}</td>
              <td class="rtd" style="font-size:12px;color:#6b7280;">{{ r.source_warehouse || '—' }}</td>
              <td class="rtd" style="text-align:right;">{{ r.work_order_count }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- ── BOM Cost Analysis table ── -->
      <div v-if="activeTab === 'bom-cost' && result" class="sc-card" style="overflow-x:auto;">
        <div v-if="!result.rows.length" style="padding:24px;text-align:center;color:#9ca3af;">No submitted BOMs found for the selected filters.</div>
        <table v-else style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead>
            <tr style="background:#f9fafb;">
              <th class="rth">BOM</th>
              <th class="rth">Item</th>
              <th class="rth">Type</th>
              <th class="rth" style="text-align:right;">Qty</th>
              <th class="rth" style="text-align:right;">RM Cost</th>
              <th class="rth" style="text-align:right;">Op Cost</th>
              <th class="rth" style="text-align:right;">Scrap Value</th>
              <th class="rth" style="text-align:right;">Total Cost</th>
              <th class="rth" style="text-align:center;">Active</th>
              <th class="rth" style="text-align:center;">Default</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in result.rows" :key="r.name" class="sc-list-row" @click="router.push(`/manufacturing/bom/${r.name}`)">
              <td class="rtd" style="color:#2563eb;font-weight:600;font-size:12px;">{{ r.name }}</td>
              <td class="rtd">{{ r.item_name }}<div style="font-size:11px;color:#9ca3af;">{{ r.item }}</div></td>
              <td class="rtd"><span style="font-size:11px;padding:2px 8px;border-radius:10px;background:#dbeafe;color:#1e40af;font-weight:600;">{{ r.bom_type }}</span></td>
              <td class="rtd" style="text-align:right;">{{ fmt(r.quantity) }}</td>
              <td class="rtd" style="text-align:right;">{{ fmt(r.rm_cost) }}</td>
              <td class="rtd" style="text-align:right;">{{ fmt(r.op_cost) }}</td>
              <td class="rtd" style="text-align:right;color:#dc2626;">{{ fmt(r.scrap_value) }}</td>
              <td class="rtd" style="text-align:right;font-weight:700;color:#1e3a8a;">{{ fmt(r.total_cost) }}</td>
              <td class="rtd" style="text-align:center;">{{ r.is_active ? '✓' : '' }}</td>
              <td class="rtd" style="text-align:center;">{{ r.is_default ? '★' : '' }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr style="background:#eff6ff;font-weight:700;">
              <td class="rtd" colspan="4" style="color:#1e40af;">Totals</td>
              <td class="rtd" style="text-align:right;color:#1e40af;">{{ fmt(result.summary.total_rm) }}</td>
              <td class="rtd" style="text-align:right;color:#1e40af;">{{ fmt(result.summary.total_op) }}</td>
              <td class="rtd"></td>
              <td class="rtd" style="text-align:right;color:#1e3a8a;">{{ fmt(result.summary.total_cost) }}</td>
              <td class="rtd" colspan="2"></td>
            </tr>
          </tfoot>
        </table>
      </div>

      <!-- ── Production Performance table ── -->
      <div v-if="activeTab === 'performance' && result" class="sc-card" style="overflow-x:auto;">
        <div v-if="!result.rows.length" style="padding:24px;text-align:center;color:#9ca3af;">No Work Orders found for the selected filters.</div>
        <table v-else style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead>
            <tr style="background:#f9fafb;">
              <th class="rth">Work Order</th>
              <th class="rth">Item</th>
              <th class="rth" style="text-align:right;">Planned</th>
              <th class="rth" style="text-align:right;">Produced</th>
              <th class="rth" style="text-align:right;">Process Loss</th>
              <th class="rth" style="text-align:right;">Yield %</th>
              <th class="rth" style="text-align:right;">Efficiency %</th>
              <th class="rth">Status</th>
              <th class="rth">Created</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in result.rows" :key="r.name" class="sc-list-row" @click="router.push(`/manufacturing/work-order/${r.name}`)">
              <td class="rtd" style="color:#2563eb;font-weight:600;">{{ r.name }}</td>
              <td class="rtd">{{ r.item_name }}<div style="font-size:11px;color:#9ca3af;">{{ r.production_item }}</div></td>
              <td class="rtd" style="text-align:right;">{{ fmt(r.qty) }}</td>
              <td class="rtd" style="text-align:right;">{{ fmt(r.produced_qty) }}</td>
              <td class="rtd" style="text-align:right;color:#dc2626;">{{ fmt(r.process_loss_qty) }}</td>
              <td class="rtd" style="text-align:right;" :style="r.yield_pct < 90 ? 'color:#dc2626;font-weight:700;' : 'color:#16a34a;font-weight:700;'">{{ r.yield_pct }}%</td>
              <td class="rtd" style="text-align:right;" :style="r.efficiency_pct < 90 ? 'color:#b45309;font-weight:700;' : ''">{{ r.efficiency_pct }}%</td>
              <td class="rtd"><span :style="statusBadge(r.status)">{{ r.status }}</span></td>
              <td class="rtd" style="font-size:12px;color:#6b7280;">{{ r.creation?.slice(0,10) }}</td>
            </tr>
          </tbody>
        </table>
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
  { id: "wo-status",   label: "Work Order Status" },
  { id: "stock-req",   label: "Stock Requirement" },
  { id: "bom-cost",    label: "BOM Cost Analysis" },
  { id: "performance", label: "Production Performance" },
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
    { label: "In Process", value: s.in_process, color: "#2563eb" },
    { label: "Completed", value: s.completed, color: "#16a34a" },
    { label: "Stopped", value: s.stopped, color: "#dc2626" },
  ];
  if (activeTab.value === "stock-req") return [
    { label: "Materials Needed", value: s.total_items },
    { label: "With Shortfall", value: s.shortfall_items, color: s.shortfall_items > 0 ? "#dc2626" : "#16a34a" },
    { label: "Sufficient", value: s.total_items - s.shortfall_items, color: "#16a34a" },
  ];
  if (activeTab.value === "bom-cost") return [
    { label: "BOMs", value: s.total_boms },
    { label: "Total RM Cost", value: fmt(s.total_rm) },
    { label: "Total Op Cost", value: fmt(s.total_op) },
    { label: "Total Cost", value: fmt(s.total_cost), color: "#1e40af" },
  ];
  if (activeTab.value === "performance") return [
    { label: "Orders", value: s.total_orders },
    { label: "Planned", value: fmt(s.total_planned) },
    { label: "Produced", value: fmt(s.total_produced) },
    { label: "Avg Yield", value: s.avg_yield_pct + "%", color: s.avg_yield_pct >= 90 ? "#16a34a" : "#dc2626" },
    { label: "Avg Efficiency", value: s.avg_efficiency + "%", color: s.avg_efficiency >= 90 ? "#16a34a" : "#b45309" },
  ];
  return [];
});

function fmt(val) {
  const n = parseFloat(val) || 0;
  return n.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function statusBadge(status) {
  const map = {
    "Completed":  "background:#dcfce7;color:#16a34a;",
    "In Process": "background:#dbeafe;color:#1e40af;",
    "Submitted":  "background:#fef3c7;color:#92400e;",
    "Stopped":    "background:#fee2e2;color:#dc2626;",
    "Cancelled":  "background:#f3f4f6;color:#6b7280;",
    "Draft":      "background:#f3f4f6;color:#6b7280;",
  };
  const base = "font-size:11px;padding:2px 8px;border-radius:10px;font-weight:700;";
  return base + (map[status] || "background:#f3f4f6;color:#6b7280;");
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
.rth {
  text-align: left;
  padding: 8px 12px;
  border-bottom: 1px solid #e5e7eb;
  color: #6b7280;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}
.rtd {
  padding: 10px 12px;
  border-bottom: 1px solid #f3f4f6;
  vertical-align: middle;
}
</style>
