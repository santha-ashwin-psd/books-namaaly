<template>
<div class="list-page">

  <!-- ── Toolbar ── -->
  <div class="sales-toolbar">
    <div class="sales-search">
      <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
      <input v-model="search" placeholder="Search departments..." class="sales-search-input"/>
    </div>
    <div class="sales-pills">
      <button v-for="t in tabs" :key="t.key"
        class="sales-pill" :class="{active:filterTab===t.key, ['pill-'+t.key]: t.key!=='all'}"
        @click="filterTab=t.key">
        {{ t.label }}
        <span v-if="t.key!=='all'" class="sales-pill-count">{{ counts[t.key] }}</span>
      </button>
    </div>
    <div class="sales-actions">
      <button class="sales-btn-ghost" @click="load" title="Refresh" :disabled="loading"><span v-html="icon('refresh',14)"></span></button>
      <button class="sales-btn-ghost" @click="exportCSV" title="Export CSV" :disabled="!filtered.length"><span v-html="icon('download',14)"></span> CSV</button>
      <button class="sales-btn-primary" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''" @click="openNewDepartmentForm"><span v-html="icon('plus',13)"></span> New Department</button>
    </div>
  </div>

  <div class="bk-kpi-grid">
    <div class="bk-kpi-card bk-kpi-accent clickable" @click="filterTab='all'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#dbeafe"><span v-html="icon('file',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Total Departments</div>
          <div class="bk-kpi-value">{{ list.length }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">registered teams</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card bk-kpi-success clickable" @click="filterTab='documented'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#dcfce7"><span v-html="icon('check',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Documented</div>
          <div class="bk-kpi-value bk-kpi-green">{{ counts.documented || 0 }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">with description</div>
        </div>
      </div>
    </div>
    <div class="bk-kpi-card bk-kpi-warn clickable" @click="filterTab='needs-details'">
      <div class="bk-kpi-inner">
        <div class="bk-kpi-icon" style="background:#fef3c7"><span v-html="icon('edit',22)"></span></div>
        <div class="bk-kpi-body">
          <div class="bk-kpi-label">Needs Details</div>
          <div class="bk-kpi-value bk-kpi-amber">{{ counts['needs-details'] || 0 }}</div>
          <div class="bk-kpi-trend bk-trend-neutral">missing description</div>
        </div>
      </div>
    </div>
  </div>

  <div class="bk-stat-grid">
    <div class="bk-stat-card">
      <div class="bk-stat-content">
        <div>
          <div class="bk-stat-label">Departments</div>
          <div class="bk-stat-value">{{ list.length }}</div>
        </div>
        <div class="bk-stat-icon" style="background:#dbeafe;color:#2563eb"><span v-html="icon('users',18)"></span></div>
      </div>
    </div>
    <div class="bk-stat-card">
      <div class="bk-stat-content">
        <div>
          <div class="bk-stat-label">Documented</div>
          <div class="bk-stat-value bk-kpi-green">{{ counts.documented || 0 }}</div>
        </div>
        <div class="bk-stat-icon" style="background:#dcfce7;color:#16a34a"><span v-html="icon('check',18)"></span></div>
      </div>
    </div>
    <div class="bk-stat-card">
      <div class="bk-stat-content">
        <div>
          <div class="bk-stat-label">Needs Details</div>
          <div class="bk-stat-value bk-kpi-amber">{{ counts['needs-details'] || 0 }}</div>
        </div>
        <div class="bk-stat-icon" style="background:#fef3c7;color:#92400e"><span v-html="icon('edit',18)"></span></div>
      </div>
    </div>
    <div class="bk-stat-card">
      <div class="bk-stat-content">
        <div>
          <div class="bk-stat-label">Coverage</div>
          <div class="bk-stat-value">{{ coverage }}%</div>
        </div>
        <div class="bk-stat-icon" style="background:#ede9fe;color:#7c3aed"><span v-html="icon('percent',18)"></span></div>
      </div>
    </div>
  </div>

  <!-- ── Table view ── -->
  <div class="inv-table-wrap">
    <table class="inv-table departments-tbl">
      <thead><tr>
        <th class="sortable" @click="sortBy('department_name')">Department Name <span v-html="sortArrow('department_name')"></span></th>
        <th class="sortable" @click="sortBy('description')">Description <span v-html="sortArrow('description')"></span></th>
        <th class="sortable" @click="sortBy('status')">Status <span v-html="sortArrow('status')"></span></th>
        <th style="width:110px;text-align:center">Actions</th>
      </tr></thead>
      <tbody>
        <template v-if="loading"><tr v-for="n in 5" :key="n"><td colspan="4"><div class="shimmer"></div></td></tr></template>
        <tr v-else-if="!sorted.length"><td colspan="4" class="bk-empty-state"><div class="bk-empty-inner">
          <template v-if="search||filterTab!=='all'">
            <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.3"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <p class="bk-empty-title">No departments match your filters</p>
          </template>
          <template v-else>
            <p class="bk-empty-title">No departments yet</p>
            <p class="bk-empty-sub">Create your first department to get started.</p>
            <button class="bk-empty-btn" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''" @click="openNewDepartmentForm"><span v-html="icon('plus',13)"></span> New Department</button>
          </template>
        </div></td></tr>
        <tr v-else v-for="row in paged" :key="row.name" class="inv-row">
          <td @click="openEditDepartmentForm(row)" data-label="Department Name"><span class="inv-link">{{ row.department_name || row.name }}</span><div class="dept-code">{{ row.name }}</div></td>
          <td @click="openEditDepartmentForm(row)" data-label="Description"><span v-if="row.description" class="text-muted">{{ row.description }}</span><span v-else class="text-muted">—</span></td>
          <td @click="openEditDepartmentForm(row)" data-label="Status"><span class="inv-status-badge" :class="statusClass(row)">{{ row.description ? 'Documented' : 'Missing Details' }}</span></td>
          <td style="text-align:center;white-space:nowrap" @click.stop>
            <button class="inv-act-btn" @click="openEditDepartmentForm(row)" :disabled="!$canEdit('inventory')" title="Edit"><span v-html="icon('edit',13)"></span></button>
            <button class="inv-act-btn" style="color:#dc2626" @click="confirmDelete(row)" :disabled="!$canDelete('inventory')" title="Delete"><span v-html="icon('trash',13)"></span></button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- ── Pagination ── -->
  <div v-if="!loading && sorted.length" style="padding:12px 4px 4px">
    <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="sorted.length" />
  </div>

  <DepartmentForm
    v-if="showForm"
    :is-edit="isEdit"
    :department="selectedDepartment"
    @close="closeDepartmentForm"
    @save="saveDepartment"
  />

</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useToast } from "../composables/useToast.js";
import { useConfirm } from "../composables/useConfirm.js";
import { apiList, apiSave, apiDelete } from "../api/client.js";
import { icon } from "../utils/icons.js";
import Pagination from "../components/Pagination.vue";
import DepartmentForm from "./DepartmentForm.vue";

const { toast } = useToast();
const { confirm } = useConfirm();

const list = ref([]);
const loading = ref(false);
const search = ref("");
const filterTab = ref("all");
const page = ref(1);
const pageSize = ref(20);
const showForm = ref(false);
const isEdit = ref(false);
const selectedDepartment = ref(null);
const sortKey = ref("department_name");
const sortDir = ref(1);

const tabs = [
  { key: "all", label: "All" },
  { key: "documented", label: "Documented" },
  { key: "needs-details", label: "Needs Details" },
];

const counts = computed(() => {
  const c = {};
  for (const t of tabs) {
    if (t.key !== "all") {
      c[t.key] = list.value.filter(i =>
        t.key === "documented" ? !!(i.description || "").trim() : !(i.description || "").trim()
      ).length;
    }
  }
  return c;
});

const coverage = computed(() => {
  if (!list.value.length) return 0;
  return Math.round(((counts.value.documented || 0) / list.value.length) * 100);
});

const filtered = computed(() => {
  let result = list.value;
  if (filterTab.value === "documented") {
    result = result.filter(i => !!(i.description || "").trim());
  } else if (filterTab.value === "needs-details") {
    result = result.filter(i => !(i.description || "").trim());
  }
  if (search.value) {
    const s = search.value.toLowerCase();
    result = result.filter(i =>
      (i.department_name || i.name || "").toLowerCase().includes(s) ||
      (i.description || "").toLowerCase().includes(s)
    );
  }
  return result;
});

const sorted = computed(() => {
  const key = sortKey.value;
  const dir = sortDir.value;
  return [...filtered.value].sort((a, b) => {
    let av = a[key] ?? "";
    let bv = b[key] ?? "";
    if (key === "status") {
      av = a.description ? "Documented" : "Missing Details";
      bv = b.description ? "Documented" : "Missing Details";
    }
    if (typeof av === "number" || typeof bv === "number") return ((parseFloat(av) || 0) - (parseFloat(bv) || 0)) * dir;
    return String(av).localeCompare(String(bv), undefined, { numeric: true }) * dir;
  });
});

const paged = computed(() => {
  const start = (page.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return sorted.value.slice(start, end);
});

function sortBy(key) {
  if (sortKey.value === key) sortDir.value *= -1;
  else { sortKey.value = key; sortDir.value = 1; }
}

function sortArrow(key) {
  if (sortKey.value !== key) return "";
  return sortDir.value === 1 ? "&#9650;" : "&#9660;";
}

function statusClass(row) {
  return row.description ? "status-active" : "status-draft";
}

async function load() {
  loading.value = true;
  try {
    const rows = await apiList("Department", {
      fields: ["name", "department_name", "description"],
      order: "department_name asc",
      limit: 500,
    });
    list.value = rows || [];
  } catch (e) {
    toast.error("Failed to load departments: " + e.message);
    list.value = [];
  } finally {
    loading.value = false;
  }
}

function openNewDepartmentForm() {
  isEdit.value = false;
  selectedDepartment.value = null;
  showForm.value = true;
}

function openEditDepartmentForm(department) {
  isEdit.value = true;
  selectedDepartment.value = department;
  showForm.value = true;
}

function closeDepartmentForm() {
  showForm.value = false;
}

async function saveDepartment(formData) {
  try {
    const doc = {
      doctype: "Department",
      ...formData,
    };
    if (!isEdit.value || !doc.name) {
      delete doc.name;
    }
    await apiSave(doc);
    toast.success(isEdit.value ? "Department updated" : "Department created");
    showForm.value = false;
    await load();
  } catch (e) {
    toast.error("Failed to save department: " + e.message);
  }
}

async function confirmDelete(department) {
  const ok = await confirm({
    title: "Delete Department",
    body: `Are you sure you want to delete department ${department.department_name || department.name}?`,
    okLabel: "Delete",
    okStyle: "danger",
  });
  if (ok) await deleteDepartment(department.name);
}

async function deleteDepartment(name) {
  try {
    await apiDelete("Department", name);
    toast.success("Department deleted");
    await load();
  } catch (e) {
    toast.error("Failed to delete department: " + e.message);
  }
}

function exportCSV() {
  const headers = ["Department Name", "Description"];
  const rows = filtered.value.map(d => [d.department_name || d.name, d.description || ""]);
  const csv = [headers, ...rows].map(row => row.map(v => `"${String(v ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "departments.csv";
  a.click();
  URL.revokeObjectURL(url);
}

onMounted(load);
</script>

<style scoped>
.dept-code {
  margin-top: 3px;
  color: #9ca3af;
  font-size: 11px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.departments-tbl { min-width: 600px; }
@media (max-width: 768px) {
  .departments-tbl { min-width: 0; }
}
</style>