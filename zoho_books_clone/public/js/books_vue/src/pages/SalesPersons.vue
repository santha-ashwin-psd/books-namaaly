<template>
<div>
  <!-- ── FLAT TABLE VIEW ── -->
  <div v-if="!selectedSP" class="list-page">
    <div class="sales-toolbar">
      <div class="cust-toolbar-left">
        <div class="sales-pills">
          <button v-for="f in [{k:'all',l:'All'},{k:'active',l:'Active'},{k:'disabled',l:'Disabled'}]"
            :key="f.k" class="sales-pill" :class="{'active': activeFilter===f.k}"
            @click="activeFilter=f.k">
            {{f.l}}
            <span class="sales-pill-count" :class="activeFilter===f.k?'':'zb-pc-muted'">{{counts[f.k]}}</span>
          </button>
        </div>
      </div>
      <div class="cust-toolbar-right">
        <div class="sales-search">
          <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
          <input v-model="search" placeholder="Search sales persons…" class="sales-search-input" autocomplete="off"/>
        </div>
        <button class="sales-btn-ghost" @click="load" title="Refresh"><span v-html="icon('refresh',13)"></span> Refresh</button>
        <button class="sales-btn-primary" :disabled="!$canWrite('customers')" :title="!$canWrite('customers') ? 'Read-only access' : ''" @click="openAdd"><span v-html="icon('plus',13)"></span> New Sales Person</button>
      </div>
    </div>

    <!-- KPI Cards -->
    <div class="bk-kpi-grid bk-kpi-grid-4" style="margin-bottom:18px">
      <div v-for="kpi in kpiCards" :key="kpi.key" class="bk-kpi-card">
        <div class="bk-kpi-inner">
          <div class="bk-kpi-icon" :style="{ background: kpi.iconBg }"><span v-html="kpi.icon"></span></div>
          <div class="bk-kpi-body">
            <div class="bk-kpi-label">{{ kpi.label }}</div>
            <div class="bk-kpi-value" :class="kpi.valueClass">
              <template v-if="loading"><div class="b-shimmer" style="width:64px;height:22px;margin-top:2px;border-radius:4px"></div></template>
              <template v-else>{{ kpi.format === 'currency' ? fmtCur(kpi.value) : kpi.value }}</template>
            </div>
            <div class="bk-kpi-trend bk-trend-neutral">{{ kpi.sub || '—' }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Bulk action bar -->
    <div v-if="selectedRows.size" class="inv-bulk-bar" style="margin: 0 24px 12px">
      <span class="inv-bulk-count">{{ selectedRows.size }} selected</span>
      <button class="inv-bulk-btn" @click="bulkSetDisabled(false)" :disabled="bulkBusy">Enable</button>
      <button class="inv-bulk-btn inv-bulk-danger" @click="bulkSetDisabled(true)" :disabled="bulkBusy">Disable</button>
      <button class="inv-bulk-clear" @click="selectedRows=new Set()">✕ Clear</button>
    </div>

    <div class="inv-table-wrap">
      <table class="inv-table">
        <thead>
          <tr>
            <th class="vt-th vt-th-check">
              <input type="checkbox" class="vt-checkbox" :checked="filtered.length>0 && filtered.every(v=>selectedRows.has(v.name))" @change="e=>e.target.checked ? selectedRows=new Set(filtered.map(v=>v.name)) : selectedRows=new Set()" />
            </th>
            <th class="vt-th">Sales Person</th>
            <th class="vt-th">Designation</th>
            <th class="vt-th">Reports To</th>
            <th class="vt-th vt-th-num">Commission</th>
            <th class="vt-th">Mobile</th>
            <th class="vt-th">Status</th>
            <th class="vt-th vt-th-actions">Actions</th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 6" :key="n" class="vt-row-shimmer">
              <td colspan="8"><div class="shimmer" style="height:12px;border-radius:3px;width:65%"></div></td>
            </tr>
          </template>
          <tr v-else-if="!filtered.length">
            <td colspan="8" class="vt-empty">
              <div class="vt-empty-icon">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" stroke-width="1.3"><rect x="4" y="4" width="16" height="16" rx="3"/><circle cx="12" cy="10" r="2.5"/><path d="M7 18c0-2.5 2.2-4 5-4s5 1.5 5 4"/></svg>
              </div>
              <div class="vt-empty-title">{{search ? 'No results found' : 'No sales persons yet'}}</div>
              <div class="vt-empty-sub">{{search ? 'Try adjusting your search' : 'Add your first sales person to get started'}}</div>
              <button v-if="!search" class="nim-btn nim-btn-primary" :disabled="!$canWrite('customers')" style="margin-top:14px" @click="openAdd"><span v-html="icon('plus',13)"></span> New Sales Person</button>
            </td>
          </tr>
          <tr v-else v-for="s in filtered" :key="s.name" class="inv-row"
            :class="[s.disabled ? 'vt-row-disabled' : '', selectedRows.has(s.name) ? 'vt-row-selected' : '']"
            @click="selectSP(s)">
            <td class="vt-td vt-td-check" @click.stop>
              <input type="checkbox" class="vt-checkbox" :checked="selectedRows.has(s.name)" @change="toggleRow(s.name)" />
            </td>
            <td class="vt-td vt-td-vendor">
              <div class="vt-vendor-cell">
                <div class="vt-avatar" :class="s.disabled ? 'vt-avatar-disabled' : ''">{{initials(s.sales_person_name)}}</div>
                <div>
                  <div class="vt-vendor-name inv-customer">{{s.sales_person_name||s.name}}</div>
                  <div class="vt-vendor-id">{{s.name}}</div>
                </div>
              </div>
            </td>
            <td class="vt-td vt-td-secondary">{{s.designation||'—'}}</td>
            <td class="vt-td vt-td-secondary">{{s.reports_to||'—'}}</td>
            <td class="vt-td vt-td-num">{{ s.commission_rate ? s.commission_rate+'%' : '—' }}</td>
            <td class="vt-td vt-td-secondary">{{s.mobile_no||'—'}}</td>
            <td class="vt-td">
              <span class="vt-badge" :class="s.disabled ? 'vt-badge-gray' : 'vt-badge-green'">
                {{ s.disabled ? 'Disabled' : (s.status||'Active') }}
              </span>
            </td>
            <td class="vt-td vt-td-actions" @click.stop>
              <button class="vt-icon-btn" title="Edit" @click="openEdit(s)" v-html="icon('edit',14)"></button>
              <button class="vt-icon-btn" title="Delete" @click="removeSP(s)" v-html="icon('trash',14)"></button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- ── DETAIL VIEW ── -->
  <div v-else class="list-page">
    <div class="sales-toolbar">
      <button class="sales-btn-ghost" @click="selectedSP=null"><span v-html="icon('arrow-left',13)"></span> Back</button>
      <div class="cust-toolbar-right">
        <button class="sales-btn-ghost" @click="openEdit(selectedSP)"><span v-html="icon('edit',13)"></span> Edit</button>
      </div>
    </div>

    <div style="padding:20px 24px">
      <div style="display:flex;align-items:center;gap:14px;margin-bottom:18px">
        <div class="vt-avatar" style="width:48px;height:48px;font-size:16px">{{initials(selectedSP.sales_person_name)}}</div>
        <div>
          <div style="font-size:18px;font-weight:700;color:#111827">{{selectedSP.sales_person_name}}</div>
          <div style="font-size:12.5px;color:#6b7280">{{selectedSP.name}} · {{selectedSP.designation||'—'}}</div>
        </div>
      </div>

      <div class="bk-kpi-grid bk-kpi-grid-4" style="margin-bottom:18px">
        <div class="bk-kpi-card">
          <div class="bk-kpi-body">
            <div class="bk-kpi-label">Invoices</div>
            <div class="bk-kpi-value">{{ perfLoading ? '…' : (performance.invoice_count||0) }}</div>
          </div>
        </div>
        <div class="bk-kpi-card">
          <div class="bk-kpi-body">
            <div class="bk-kpi-label">Revenue</div>
            <div class="bk-kpi-value">{{ perfLoading ? '…' : fmtCur(performance.total_revenue||0) }}</div>
          </div>
        </div>
        <div class="bk-kpi-card">
          <div class="bk-kpi-body">
            <div class="bk-kpi-label">Outstanding</div>
            <div class="bk-kpi-value">{{ perfLoading ? '…' : fmtCur(performance.outstanding||0) }}</div>
          </div>
        </div>
        <div class="bk-kpi-card">
          <div class="bk-kpi-body">
            <div class="bk-kpi-label">Commission Earned</div>
            <div class="bk-kpi-value">{{ perfLoading ? '…' : fmtCur(performance.commission_earned||0) }}</div>
          </div>
        </div>
      </div>
      <div v-if="performance.note" style="font-size:12px;color:#9ca3af;margin-bottom:18px">{{ performance.note }}</div>

      <div class="inv-sec-lbl">Contact</div>
      <div class="inv-fg inv-fg2" style="margin-bottom:20px">
        <div><span style="color:#6b7280;font-size:12.5px">Email</span><div>{{selectedSP.email_id||'—'}}</div></div>
        <div><span style="color:#6b7280;font-size:12.5px">Mobile</span><div>{{selectedSP.mobile_no||'—'}}</div></div>
        <div><span style="color:#6b7280;font-size:12.5px">Phone</span><div>{{selectedSP.phone||'—'}}</div></div>
        <div><span style="color:#6b7280;font-size:12.5px">Department</span><div>{{selectedSP.department||'—'}}</div></div>
      </div>
    </div>
  </div>

  <!-- Drawer -->
  <Teleport to="body">
    <div v-if="showDrawer" class="inv-drawer-bg" @click.self="showDrawer=false">
      <div class="inv-drawer-panel" :class="{open:showDrawer}" style="width:620px;max-width:98vw">
        <div class="inv-dh" style="background:linear-gradient(135deg,#7C3AED,#5B21B6);padding:18px 24px">
          <div class="cust-drawer-header-left">
            <div class="cust-drawer-icon" style="color:#fff" v-html="icon('badge',16)"></div>
            <div>
              <div class="inv-dh-title">{{drawerMode==='add'?'New Sales Person':'Edit Sales Person'}}</div>
              <div class="cust-drawer-sub">{{drawerMode==='edit'?form.name:'Fill in sales person details'}}</div>
            </div>
          </div>
          <button style="background:rgba(255,255,255,.15);border:none;cursor:pointer;color:#fff;width:30px;height:30px;border-radius:8px;display:grid;place-items:center" @click="showDrawer=false" v-html="icon('x',15)"></button>
        </div>

        <div v-if="drawerLoading" style="flex:1;display:grid;place-items:center;color:#9ca3af;font-size:13px;padding:40px">Loading…</div>

        <div v-else class="inv-dbody" style="padding:24px;overflow-y:auto;flex:1">
          <div class="inv-sec-lbl" style="margin-top:0">Basic Information</div>
          <div class="inv-fg inv-fg2">
            <div class="inv-field" style="grid-column:span 2">
              <label class="inv-lbl">Sales Person Name <span class="nim-req">*</span></label>
              <input v-model="form.sales_person_name" class="inv-fi"
                :style="formErrors.sales_person_name?'border-color:#dc2626;background:#fff5f5':''"
                placeholder="Full name"
                @input="delete formErrors.sales_person_name"
                @blur="validateField('sales_person_name')"/>
              <div v-if="formErrors.sales_person_name" style="margin-top:4px;font-size:12px;color:#dc2626">{{formErrors.sales_person_name}}</div>
            </div>
            <div class="inv-field">
              <label class="inv-lbl">Employee ID</label>
              <input v-model="form.employee_id" class="inv-fi" placeholder="EMP-001"/>
            </div>
            <div class="inv-field">
              <label class="inv-lbl">Status</label>
              <select v-model="form.status" class="inv-fi">
                <option>Active</option>
                <option>Inactive</option>
              </select>
            </div>
            <div class="inv-field">
              <label class="inv-lbl">Department</label>
              <input v-model="form.department" class="inv-fi" placeholder="Sales"/>
            </div>
            <div class="inv-field">
              <label class="inv-lbl">Designation</label>
              <input v-model="form.designation" class="inv-fi" placeholder="Sales Executive"/>
            </div>
            <div class="inv-field">
              <label class="inv-lbl">Reports To</label>
              <select v-model="form.reports_to" class="inv-fi">
                <option value="">None</option>
                <option v-for="sp in allSalesPersons.filter(p=>p.name!==form.name)" :key="sp.name" :value="sp.name">{{ sp.sales_person_name }}</option>
              </select>
            </div>
            <div class="inv-field">
              <label class="inv-lbl">Commission Rate (%)</label>
              <input v-model.number="form.commission_rate" type="number" min="0" max="100" step="0.1" class="inv-fi"
                :style="formErrors.commission_rate?'border-color:#dc2626;background:#fff5f5':''"
                @blur="validateField('commission_rate')"/>
              <div v-if="formErrors.commission_rate" style="margin-top:4px;font-size:12px;color:#dc2626">{{formErrors.commission_rate}}</div>
            </div>
          </div>

          <div class="inv-sec-lbl">Contact</div>
          <div class="inv-fg inv-fg2">
            <div class="inv-field">
              <label class="inv-lbl">Email</label>
              <input v-model="form.email_id" type="email" class="inv-fi"
                :style="formErrors.email_id?'border-color:#dc2626;background:#fff5f5':''"
                placeholder="name@company.com"
                @input="delete formErrors.email_id"
                @blur="validateField('email_id')"/>
              <div v-if="formErrors.email_id" style="margin-top:4px;font-size:12px;color:#dc2626">{{formErrors.email_id}}</div>
            </div>
            <div class="inv-field">
              <label class="inv-lbl">Mobile</label>
              <input v-model="form.mobile_no" class="inv-fi" placeholder="98765 43210"/>
            </div>
            <div class="inv-field">
              <label class="inv-lbl">Phone</label>
              <input v-model="form.phone" class="inv-fi"/>
            </div>
          </div>

          <div class="inv-sec-lbl">Address</div>
          <div class="inv-fg inv-fg2">
            <div class="inv-field" style="grid-column:span 2">
              <label class="inv-lbl">Address Line 1</label>
              <input v-model="form.address_line1" class="inv-fi"/>
            </div>
            <div class="inv-field" style="grid-column:span 2">
              <label class="inv-lbl">Address Line 2</label>
              <input v-model="form.address_line2" class="inv-fi"/>
            </div>
            <div class="inv-field"><label class="inv-lbl">City</label><input v-model="form.city" class="inv-fi"/></div>
            <div class="inv-field"><label class="inv-lbl">State</label><input v-model="form.state" class="inv-fi"/></div>
            <div class="inv-field"><label class="inv-lbl">Pincode</label><input v-model="form.pincode" class="inv-fi"/></div>
            <div class="inv-field"><label class="inv-lbl">Country</label><input v-model="form.country" class="inv-fi"/></div>
          </div>

          <div style="margin-top:16px;display:flex;align-items:center;gap:8px">
            <input type="checkbox" v-model="form.disabled" id="sp-disabled"/>
            <label for="sp-disabled" style="font-size:13px;color:#374151">Disabled</label>
          </div>
        </div>

        <div class="inv-dfooter" style="display:flex;gap:10px;padding:16px 24px;border-top:1px solid #e8ecf0">
          <button class="form-btn" @click="showDrawer=false">Cancel</button>
          <button class="form-btn form-btn-primary" :disabled="saving" @click="saveSP">{{saving?'Saving…':'Save'}}</button>
        </div>
      </div>
    </div>
  </Teleport>
</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { icon } from "../utils/icons.js";
import { apiList, apiGet, apiSave, apiPOST, apiDelete } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { useConfirm } from "../composables/useConfirm.js";

const { toast } = useToast();
const { confirm } = useConfirm();

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const loading   = ref(true);
const rows      = ref([]);
const search    = ref("");
const activeFilter = ref("all");
const selectedRows = ref(new Set());
const selectedSP   = ref(null);
const bulkBusy      = ref(false);

const performance  = ref({});
const perfLoading   = ref(false);

const showDrawer   = ref(false);
const drawerMode    = ref("add");
const drawerLoading = ref(false);
const saving         = ref(false);
const formErrors     = reactive({});
const allSalesPersons = ref([]);

const FIELDS = [
  "name", "sales_person_name", "employee_id", "status", "department", "designation",
  "reports_to", "email_id", "mobile_no", "phone", "commission_rate",
  "address_line1", "address_line2", "city", "state", "pincode", "country", "disabled",
];

function blankForm() {
  return {
    name: null, sales_person_name: "", employee_id: "", status: "Active",
    department: "", designation: "", reports_to: "", email_id: "", mobile_no: "",
    phone: "", commission_rate: 0, address_line1: "", address_line2: "",
    city: "", state: "", pincode: "", country: "India", disabled: 0,
  };
}
const form = reactive(blankForm());

async function load() {
  loading.value = true;
  try {
    rows.value = await apiList("Sales Person", { fields: FIELDS, order: "modified desc", limit: 500 });
    allSalesPersons.value = rows.value;
  } catch (e) {
    toast.error(e.message || "Failed to load sales persons");
  } finally {
    loading.value = false;
  }
}

const filtered = computed(() => {
  let list = rows.value;
  if (activeFilter.value === "active")   list = list.filter(s => !s.disabled);
  if (activeFilter.value === "disabled") list = list.filter(s => s.disabled);
  if (search.value.trim()) {
    const q = search.value.trim().toLowerCase();
    list = list.filter(s =>
      (s.sales_person_name || "").toLowerCase().includes(q) ||
      (s.name || "").toLowerCase().includes(q) ||
      (s.email_id || "").toLowerCase().includes(q) ||
      (s.mobile_no || "").includes(q));
  }
  return list;
});

const counts = computed(() => ({
  all: rows.value.length,
  active: rows.value.filter(s => !s.disabled).length,
  disabled: rows.value.filter(s => s.disabled).length,
}));

const kpiCards = computed(() => [
  { key: "total", label: "Total Sales Persons", value: counts.value.all, iconBg: "#EEF2FF", icon: icon("badge", 18) },
  { key: "active", label: "Active", value: counts.value.active, iconBg: "#F0FDF4", icon: icon("check", 18) },
  { key: "disabled", label: "Disabled", value: counts.value.disabled, iconBg: "#FEF2F2", icon: icon("x", 18) },
  {
    key: "avg_commission", label: "Avg. Commission", format: "pct",
    value: rows.value.length
      ? (rows.value.reduce((a, s) => a + (Number(s.commission_rate) || 0), 0) / rows.value.length).toFixed(1) + "%"
      : "0%",
    iconBg: "#FFFBEB", icon: icon("rupee", 18),
  },
]);

function toggleRow(name) {
  const s = new Set(selectedRows.value);
  s.has(name) ? s.delete(name) : s.add(name);
  selectedRows.value = s;
}

function initials(name) {
  if (!name) return "?";
  return name.split(" ").filter(Boolean).slice(0, 2).map(w => w[0].toUpperCase()).join("");
}

function fmtCur(v) {
  return "₹" + Number(v || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

async function selectSP(s) {
  selectedSP.value = s;
  performance.value = {};
  perfLoading.value = true;
  try {
    performance.value = await apiPOST("zoho_books_clone.api.sales_person.get_sales_person_performance", { sales_person: s.name })
      .catch(() => apiGET_fallback(s.name));
  } catch (e) {
    // non-fatal — performance tile just stays empty
  } finally {
    perfLoading.value = false;
  }
}
// get_sales_person_performance is a GET endpoint; apiPOST works too since apiPOST/apiGET both
// hit frappe.call under the hood, but keep a safe fallback just in case.
async function apiGET_fallback() { return {}; }

function openAdd() {
  Object.assign(form, blankForm());
  Object.keys(formErrors).forEach(k => delete formErrors[k]);
  drawerMode.value = "add";
  drawerLoading.value = false;
  showDrawer.value = true;
}

async function openEdit(s) {
  drawerMode.value = "edit";
  showDrawer.value = true;
  drawerLoading.value = true;
  Object.keys(formErrors).forEach(k => delete formErrors[k]);
  try {
    const doc = await apiGet("Sales Person", s.name);
    Object.assign(form, blankForm(), doc);
  } catch (e) {
    toast.error(e.message || "Failed to load sales person");
    showDrawer.value = false;
  } finally {
    drawerLoading.value = false;
  }
}

function validateField(field) {
  if (field === "sales_person_name") {
    if (!form.sales_person_name?.trim()) formErrors.sales_person_name = "Name is required";
    else delete formErrors.sales_person_name;
  }
  if (field === "email_id") {
    if (form.email_id && !EMAIL_REGEX.test(form.email_id)) formErrors.email_id = "Enter a valid email";
    else delete formErrors.email_id;
  }
  if (field === "commission_rate") {
    const v = Number(form.commission_rate);
    if (v < 0 || v > 100) formErrors.commission_rate = "Must be between 0 and 100";
    else delete formErrors.commission_rate;
  }
}

async function saveSP() {
  validateField("sales_person_name");
  validateField("email_id");
  validateField("commission_rate");
  if (Object.keys(formErrors).length) {
    toast.error("Please fix the highlighted fields");
    return;
  }
  saving.value = true;
  try {
    const doc = { ...form, doctype: "Sales Person" };
    await apiSave(doc);
    toast.success(drawerMode.value === "add" ? "Sales person created" : "Sales person updated");
    showDrawer.value = false;
    await load();
  } catch (e) {
    toast.error(e.message || "Failed to save sales person");
  } finally {
    saving.value = false;
  }
}

async function removeSP(s) {
  const ok = await confirm({
    title: "Delete Sales Person?",
    body: `This will permanently delete ${s.sales_person_name || s.name}. This cannot be undone.`,
    okLabel: "Delete", okStyle: "danger",
  });
  if (!ok) return;
  try {
    await apiPOST("zoho_books_clone.api.sales_person.safe_delete_sales_person", { name: s.name });
    toast.success("Sales person deleted");
    await load();
  } catch (e) {
    toast.error(e.message || "Failed to delete — it may have linked invoices. Disable it instead.");
  }
}

async function bulkSetDisabled(disabled) {
  bulkBusy.value = true;
  try {
    await apiPOST("zoho_books_clone.api.sales_person.bulk_set_sales_person_disabled", {
      sales_person_names: JSON.stringify([...selectedRows.value]),
      disabled: disabled ? 1 : 0,
    });
    toast.success(disabled ? "Disabled selected sales persons" : "Enabled selected sales persons");
    selectedRows.value = new Set();
    await load();
  } catch (e) {
    toast.error(e.message || "Bulk update failed");
  } finally {
    bulkBusy.value = false;
  }
}

onMounted(load);
</script>