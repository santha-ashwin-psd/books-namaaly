<template>
<div style="padding:24px;background:#f0f2f5;min-height:100vh;">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;">
    <div>
      <div style="font-size:20px;font-weight:700;color:#1a1a2e;">Packing Slips</div>
      <div style="font-size:13px;color:#6b7280;margin-top:3px;">Packing records for Packing BOM Work Orders</div>
    </div>
    <button class="ps-btn-primary" @click="router.push('/manufacturing/packing-slip/new')">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
      New Packing Slip
    </button>
  </div>

  <!-- Status filter + search -->
  <div style="display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap;">
    <div style="display:flex;background:#fff;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;">
      <button v-for="t in statusTabs" :key="t.value" @click="activeStatus=t.value;loadList()"
        :style="activeStatus===t.value ? 'background:#2563eb;color:#fff;' : 'background:#fff;color:#374151;'"
        style="padding:7px 14px;border:none;cursor:pointer;font-size:12.5px;font-weight:600;white-space:nowrap;">
        {{ t.label }}
      </button>
    </div>
    <input v-model="search" @input="onSearch" placeholder="Search by name, work order…" style="padding:7px 12px;border:1px solid #e5e7eb;border-radius:8px;font-size:13px;outline:none;min-width:220px;" />
    <select v-model="sortField" @change="loadList()" style="padding:7px 12px;border:1px solid #e5e7eb;border-radius:8px;font-size:13px;outline:none;">
      <option value="modified">Sort: Last Modified</option>
      <option value="name">Sort: Name</option>
      <option value="packing_date">Sort: Packing Date</option>
    </select>
  </div>

  <!-- Bulk actions -->
  <div v-if="selected.length" style="display:flex;align-items:center;gap:10px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:10px 14px;margin-bottom:12px;">
    <span style="font-size:13px;font-weight:600;color:#1e40af;">{{ selected.length }} selected</span>
    <button @click="bulkDelete" style="padding:5px 12px;background:#fee2e2;color:#dc2626;border:1px solid #fecaca;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600;">Delete</button>
    <button @click="selected=[]" style="padding:5px 12px;background:#fff;border:1px solid #e5e7eb;border-radius:6px;cursor:pointer;font-size:12px;">Clear</button>
  </div>

  <!-- Table -->
  <div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.06);">
    <table style="width:100%;border-collapse:collapse;font-size:13px;">
      <thead>
        <tr style="background:#f9fafb;border-bottom:1px solid #e5e7eb;">
          <th style="width:36px;padding:10px 12px;"><input type="checkbox" @change="toggleAll($event)" :checked="selected.length===rows.length&&rows.length>0" /></th>
          <th style="text-align:left;padding:10px 12px;color:#6b7280;font-weight:600;font-size:12px;">Packing Slip</th>
          <th style="text-align:left;padding:10px 12px;color:#6b7280;font-weight:600;font-size:12px;">Work Order</th>
          <th style="text-align:left;padding:10px 12px;color:#6b7280;font-weight:600;font-size:12px;">Item Being Packed</th>
          <th style="text-align:right;padding:10px 12px;color:#6b7280;font-weight:600;font-size:12px;">Qty to Pack</th>
          <th style="text-align:left;padding:10px 12px;color:#6b7280;font-weight:600;font-size:12px;">Packing Date</th>
          <th style="text-align:left;padding:10px 12px;color:#6b7280;font-weight:600;font-size:12px;">Status</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading"><td colspan="7" style="text-align:center;padding:32px;color:#9ca3af;">Loading…</td></tr>
        <tr v-else-if="!rows.length"><td colspan="7" style="text-align:center;padding:32px;color:#9ca3af;">No Packing Slips found.</td></tr>
        <tr v-for="r in rows" :key="r.name" @click.self="go(r.name)" style="border-bottom:1px solid #f3f4f6;cursor:pointer;" class="ps-row">
          <td style="padding:10px 12px;" @click.stop><input type="checkbox" :value="r.name" v-model="selected" /></td>
          <td style="padding:10px 12px;" @click="go(r.name)"><span class="ps-link">{{ r.name }}</span></td>
          <td style="padding:10px 12px;" @click="go(r.name)">{{ r.work_order || '—' }}</td>
          <td style="padding:10px 12px;" @click="go(r.name)">{{ r.production_item || '—' }}</td>
          <td style="padding:10px 12px;text-align:right;" @click="go(r.name)">{{ fmt(r.qty_to_pack) }}</td>
          <td style="padding:10px 12px;" @click="go(r.name)">{{ fmtDate(r.packing_date) }}</td>
          <td style="padding:10px 12px;" @click="go(r.name)">
            <span :style="statusStyle(r.status)" style="padding:3px 8px;border-radius:12px;font-size:11px;font-weight:600;">{{ r.status }}</span>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Pagination -->
    <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 16px;border-top:1px solid #f3f4f6;background:#fafafa;">
      <span style="font-size:12px;color:#9ca3af;">{{ rows.length }} of {{ total }} records</span>
      <div style="display:flex;gap:8px;">
        <button @click="prevPage" :disabled="page===0" style="padding:5px 12px;border:1px solid #e5e7eb;border-radius:6px;cursor:pointer;font-size:12px;background:#fff;" :style="page===0?'opacity:.4':''">Prev</button>
        <button @click="nextPage" :disabled="(page+1)*pageSize>=total" style="padding:5px 12px;border:1px solid #e5e7eb;border-radius:6px;cursor:pointer;font-size:12px;background:#fff;" :style="(page+1)*pageSize>=total?'opacity:.4':''">Next</button>
      </div>
    </div>
  </div>
</div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { apiList, apiDelete } from "../api/client.js";
import { useToast } from "../composables/useToast.js";

const router = useRouter();
const { toast } = useToast();

const rows = ref([]);
const total = ref(0);
const loading = ref(false);
const search = ref("");
const activeStatus = ref("all");
const sortField = ref("modified");
const selected = ref([]);
const page = ref(0);
const pageSize = 20;
let searchTimer = null;

const statusTabs = [
  { value: "all",         label: "All" },
  { value: "Draft",       label: "Draft" },
  { value: "In Progress", label: "In Progress" },
  { value: "Packed",      label: "Packed" },
  { value: "Cancelled",   label: "Cancelled" },
];

async function loadList() {
  loading.value = true;
  try {
    const filters = [];
    if (activeStatus.value !== "all") filters.push(["status", "=", activeStatus.value]);
    if (search.value) filters.push(["name", "like", `%${search.value}%`]);
    const data = await apiList("Packing Slip", {
      fields: ["name", "work_order", "production_item", "qty_to_pack", "packing_date", "status"],
      filters,
      limit: pageSize,
      start: page.value * pageSize,
      order: sortField.value + " desc",
    }) || [];
    rows.value = data;
    total.value = data.length < pageSize ? page.value * pageSize + data.length : (page.value + 1) * pageSize + 1;
  } catch (e) {
    toast(e.message, "error");
  }
  loading.value = false;
}

function onSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { page.value = 0; loadList(); }, 350);
}

function prevPage() { if (page.value > 0) { page.value--; loadList(); } }
function nextPage() { if ((page.value + 1) * pageSize < total.value) { page.value++; loadList(); } }
function toggleAll(e) { selected.value = e.target.checked ? rows.value.map(r => r.name) : []; }

async function bulkDelete() {
  if (!confirm(`Delete ${selected.value.length} Packing Slip(s)?`)) return;
  for (const name of selected.value) {
    try { await apiDelete("Packing Slip", name); } catch (e) { toast(e.message, "error"); }
  }
  selected.value = [];
  toast("Deleted");
  loadList();
}

function go(name) { router.push(`/manufacturing/packing-slip/${name}`); }

function statusStyle(s) {
  if (s === "Packed") return "background:#dcfce7;color:#16a34a;";
  if (s === "In Progress") return "background:#dbeafe;color:#1e40af;";
  if (s === "Cancelled") return "background:#fee2e2;color:#dc2626;";
  return "background:#fef3c7;color:#b45309;";
}

function fmt(n) { const v = parseFloat(n); return isNaN(v) ? "0.00" : v.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
function fmtDate(d) {
  if (!d) return "—";
  const o = new Date(d);
  return isNaN(o) ? d : o.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

onMounted(loadList);
</script>

<style scoped>
.ps-btn-primary { display:inline-flex;align-items:center;gap:7px;font-size:13.5px;font-weight:600;padding:9px 20px;border-radius:9px;background:linear-gradient(135deg,#2f74f5,#1a6ef7);border:none;color:#fff;cursor:pointer; }
.ps-btn-primary:hover { filter:brightness(1.05); }
.ps-row:hover { background:#f9fafb; }
.ps-link { color:#2563eb;font-weight:600; }
.ps-link:hover { text-decoration:underline; }
</style>
