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
        <button class="sales-btn-primary" :disabled="!$canCreate('customers')" :title="!$canCreate('customers') ? 'Read-only access' : ''" @click="openAdd"><span v-html="icon('plus',13)"></span> New Sales Person</button>
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
            <div class="bk-kpi-trend bk-trend-neutral">{{ kpi.sub|| '' }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Bulk action bar -->
    <div v-if="selectedRows.size" class="inv-bulk-bar" style="margin: 0 24px 12px">
      <span class="inv-bulk-count">{{ selectedRows.size }} selected</span>
      <button class="inv-bulk-btn" @click="bulkSetDisabled(false)" :disabled="bulkBusy || !$canEdit('customers')" :title="!$canEdit('customers') ? 'Read-only access' : ''">Enable</button>
      <button class="inv-bulk-btn inv-bulk-danger" @click="bulkSetDisabled(true)" :disabled="bulkBusy || !$canEdit('customers')" :title="!$canEdit('customers') ? 'Read-only access' : ''">Disable</button>
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
              <button v-if="!search" class="nim-btn nim-btn-primary" :disabled="!$canCreate('customers')" :title="!$canCreate('customers') ? 'Read-only access' : ''" style="margin-top:14px" @click="openAdd"><span v-html="icon('plus',13)"></span> New Sales Person</button>
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
            <td class="vt-td vt-td-secondary">{{reportsToName(s.reports_to)}}</td>
            <td class="vt-td vt-td-num">{{ s.commission_rate ? s.commission_rate+'%' : '—' }}</td>
            <td class="vt-td vt-td-secondary">{{s.mobile_no||'—'}}</td>
            <td class="vt-td">
              <span class="vt-badge" :class="s.disabled ? 'vt-badge-gray' : 'vt-badge-green'">
                <span class="vt-badge-dot"></span>{{ s.disabled ? 'Disabled' : (s.status||'Active') }}
              </span>
            </td>
            <td class="vt-td vt-td-actions" @click.stop>
              <div class="vt-actions">
                <button class="inv-act-btn vt-act-edit" :disabled="!$canEdit('customers')" :title="!$canEdit('customers') ? 'Read-only access' : 'Edit'" @click="openEdit(s)"><span v-html="icon('edit',13)"></span></button>
                <button class="inv-act-btn vt-act-del" :disabled="!$canDelete('customers')" :title="!$canDelete('customers') ? 'Not permitted' : 'Delete'" @click="removeSP(s)"><span v-html="icon('trash',13)"></span></button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- ── DETAIL VIEW ── -->
  <div v-else class="sp-page">
    <!-- Breadcrumb -->
    <div class="sp-bread">
      <a class="sp-back" @click="selectedSP=null">
        <span v-html="icon('arrow-left',13)"></span> All Sales Persons
      </a>
      <span class="sp-bread-sep">/</span>
      <span class="sp-bread-cur">{{selectedSP.sales_person_name||selectedSP.name}}</span>
    </div>

    <!-- Header card -->
    <div class="sp-header">
      <div class="sp-header-left">
        <div class="sp-avatar" :class="{disabled: selectedSP.disabled}">{{initials(selectedSP.sales_person_name)}}</div>
        <div>
          <div class="sp-name">{{selectedSP.sales_person_name}}</div>
          <div class="sp-meta">
            <span class="sp-chip sp-chip-muted">{{selectedSP.name}}</span>
            <span v-if="selectedSP.designation" class="sp-chip">{{selectedSP.designation}}</span>
            <span v-if="selectedSP.department" class="sp-chip sp-chip-muted">{{selectedSP.department}}</span>
            <span v-if="selectedSP.disabled" class="sp-chip sp-chip-danger">Disabled</span>
            <span v-else class="sp-chip sp-chip-green">Active</span>
          </div>
        </div>
      </div>
      <div style="display:flex;gap:8px">
        <button class="sp-btn-ghost" :disabled="!selectedSP.email_id" @click="selectedSP.email_id && (location.href='mailto:'+selectedSP.email_id)">
          <span v-html="icon('mail',13)"></span> Email
        </button>
        <button class="sp-btn-primary" :disabled="!$canEdit('customers')" :title="!$canEdit('customers') ? 'Read-only access' : ''" @click="openEdit(selectedSP)">
          <span v-html="icon('edit',13)"></span> Edit
        </button>
      </div>
    </div>

    <!-- KPI stat cards -->
    <div class="bk-kpi-grid bk-kpi-grid-4" style="margin-bottom:16px">
      <div class="bk-kpi-card">
        <div class="bk-kpi-inner">
          <div class="bk-kpi-icon" style="background:#EEF2FF" v-html="icon('file',18)"></div>
          <div class="bk-kpi-body">
            <div class="bk-kpi-label">Invoices</div>
            <div class="bk-kpi-value">{{ perfLoading ? '…' : (performance.invoice_count||0) }}</div>
            <div class="bk-kpi-trend bk-trend-neutral">Total raised</div>
          </div>
        </div>
      </div>
      <div class="bk-kpi-card">
        <div class="bk-kpi-inner">
          <div class="bk-kpi-icon" style="background:#F0FDF4" v-html="icon('trend',18)"></div>
          <div class="bk-kpi-body">
            <div class="bk-kpi-label">Revenue</div>
            <div class="bk-kpi-value">{{ perfLoading ? '…' : fmtCur(performance.total_revenue||0) }}</div>
            <div class="bk-kpi-trend bk-trend-neutral">Lifetime billed</div>
          </div>
        </div>
      </div>
      <div class="bk-kpi-card">
        <div class="bk-kpi-inner">
          <div class="bk-kpi-icon" style="background:#FEF2F2" v-html="icon('alert',18)"></div>
          <div class="bk-kpi-body">
            <div class="bk-kpi-label">Outstanding</div>
            <div class="bk-kpi-value" :class="performance.outstanding>0?'bk-kpi-red':''">{{ perfLoading ? '…' : fmtCur(performance.outstanding||0) }}</div>
            <div class="bk-kpi-trend bk-trend-neutral">Unpaid balance</div>
          </div>
        </div>
      </div>
      <div class="bk-kpi-card">
        <div class="bk-kpi-inner">
          <div class="bk-kpi-icon" style="background:#FFFBEB" v-html="icon('rupee',18)"></div>
          <div class="bk-kpi-body">
            <div class="bk-kpi-label">Commission Earned</div>
            <div class="bk-kpi-value">{{ perfLoading ? '…' : fmtCur(performance.commission_earned||0) }}</div>
            <div class="bk-kpi-trend bk-trend-neutral">{{ selectedSP.commission_rate ? selectedSP.commission_rate+'% rate' : '—' }}</div>
          </div>
        </div>
      </div>
    </div>
    <div v-if="performance.note" class="sp-note">{{ performance.note }}</div>

    <!-- Contact + Job details card -->
    <div class="sp-info-card">
      <div class="sp-info-section">
        <div class="sp-section-title">Contact</div>
        <div class="sp-kv"><span class="sp-k">Email</span>
          <a v-if="selectedSP.email_id" :href="`mailto:${selectedSP.email_id}`" class="sp-link">{{selectedSP.email_id}}</a>
          <span v-else class="sp-v-empty">—</span>
        </div>
        <div class="sp-kv"><span class="sp-k">Mobile</span>
          <a v-if="selectedSP.mobile_no" :href="`tel:${selectedSP.mobile_no}`" class="sp-link">{{selectedSP.mobile_no}}</a>
          <span v-else class="sp-v-empty">—</span>
        </div>
        <div class="sp-kv"><span class="sp-k">Phone</span>
          <a v-if="selectedSP.phone" :href="`tel:${selectedSP.phone}`" class="sp-link">{{selectedSP.phone}}</a>
          <span v-else class="sp-v-empty">—</span>
        </div>
      </div>
      <div class="sp-info-section">
        <div class="sp-section-title">Job Details</div>
        <div class="sp-kv"><span class="sp-k">Employee ID</span><span>{{selectedSP.employee_id||'—'}}</span></div>
        <div class="sp-kv"><span class="sp-k">Department</span><span>{{selectedSP.department||'—'}}</span></div>
        <div class="sp-kv"><span class="sp-k">Reports To</span><span>{{reportsToName(selectedSP.reports_to)}}</span></div>
      </div>
      <div class="sp-info-section">
        <div class="sp-section-title">Address</div>
        <div v-if="selectedSP.address_line1 || selectedSP.city" class="sp-address">
          <div v-if="selectedSP.address_line1">{{selectedSP.address_line1}}</div>
          <div v-if="selectedSP.address_line2">{{selectedSP.address_line2}}</div>
          <div>{{[selectedSP.city, selectedSP.state, selectedSP.pincode].filter(Boolean).join(', ')}}</div>
          <div v-if="selectedSP.country">{{selectedSP.country}}</div>
        </div>
        <div v-else class="sp-v-empty" style="font-style:italic">No address on file</div>
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
              <label class="inv-lbl">Employee ID <span class="nim-req">*</span></label>
              <input v-model="form.employee_id" class="inv-fi" placeholder="EMP-001"
                :style="formErrors.employee_id?'border-color:#dc2626;background:#fff5f5':''"
                @input="delete formErrors.employee_id"
                @blur="validateField('employee_id')"/>
              <div v-if="formErrors.employee_id" style="margin-top:4px;font-size:12px;color:#dc2626">{{formErrors.employee_id}}</div>
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
                <option value="">No Manager (Top Level)</option>
                <option v-for="sp in allSalesPersons.filter(p=>p.name!==form.name)" :key="sp.name" :value="sp.name">{{ sp.sales_person_name }}</option>
              </select>
              <div v-if="!allSalesPersons.filter(p=>p.name!==form.name).length" style="margin-top:4px;font-size:11.5px;color:#9ca3af">
                No other sales persons yet — add more to build a reporting hierarchy.
              </div>
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
              <label class="inv-lbl">Mobile <span class="nim-req">*</span></label>
              <input v-model="form.mobile_no" class="inv-fi" placeholder="98765 43210"
                :style="formErrors.mobile_no?'border-color:#dc2626;background:#fff5f5':''"
                @input="delete formErrors.mobile_no"
                @blur="validateField('mobile_no')"/>
              <div v-if="formErrors.mobile_no" style="margin-top:4px;font-size:12px;color:#dc2626">{{formErrors.mobile_no}}</div>
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
          <button class="form-btn form-btn-primary" :disabled="saving || !(drawerMode==='edit' ? $canEdit('customers') : $canCreate('customers'))" :title="!(drawerMode==='edit' ? $canEdit('customers') : $canCreate('customers')) ? 'Read-only access' : ''" @click="saveSP">{{saving?'Saving…':'Save'}}</button>
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

function reportsToName(id) {
  if (!id) return "—";
  const sp = allSalesPersons.value.find(p => p.name === id) || rows.value.find(p => p.name === id);
  return sp ? sp.sales_person_name : id;
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
  if (field === "employee_id") {
    if (!form.employee_id?.trim()) formErrors.employee_id = "Employee ID is required";
    else delete formErrors.employee_id;
  }
  if (field === "mobile_no") {
    const digits = (form.mobile_no || "").replace(/\D/g, "");
    if (!digits) formErrors.mobile_no = "Mobile number is required";
    else if (digits.length < 10) formErrors.mobile_no = "Enter a valid mobile number";
    else delete formErrors.mobile_no;
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
  validateField("employee_id");
  validateField("mobile_no");
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

<style scoped>
/* ── Drawer slide-in animation ──────────────────────────── */
.inv-drawer-panel {
  transform: translateX(100%);
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.inv-drawer-panel.open {
  transform: translateX(0);
}
.cust-drawer-header-left { display: flex; align-items: center; gap: 12px; }
.cust-drawer-icon {
  width: 36px; height: 36px; border-radius: 10px;
  background: rgba(255,255,255,.15);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.cust-drawer-sub { color: rgba(255,255,255,.75); font-size: 12px; margin-top: 2px; }

/* ── Sales person avatar circle (purple gradient) ───────── */
.vt-vendor-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}
.vt-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  flex-shrink: 0;
  background: linear-gradient(135deg, #7C3AED, #5B21B6);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.03em;
}
.vt-avatar-disabled { background: #d1d5db; }
.vt-vendor-name {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
  line-height: 1.3;
}
.vt-vendor-id {
  font-size: 11.5px;
  color: #9ca3af;
  margin-top: 1px;
}

/* ── Table columns ───────────────────────────────────────── */
.vt-th {
  padding: 10px 14px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
  white-space: nowrap;
  user-select: none;
}
.vt-th-check   { width: 36px; padding-left: 16px; }
.vt-th-num     { text-align: right; }
.vt-th-actions { text-align: center; width: 88px; }
.vt-td {
  padding: 11px 14px;
  vertical-align: middle;
  color: #374151;
  white-space: nowrap;
}
.vt-td-check      { padding-left: 16px; width: 36px; }
.vt-td-num        { text-align: right; }
.vt-td-secondary  { color: #6b7280; font-size: 12.5px; }
.vt-td-actions    { text-align: center; width: 88px; }
.vt-checkbox { width: 15px; height: 15px; accent-color: #7C3AED; cursor: pointer; border-radius: 3px; }
.vt-row-shimmer td { padding: 13px 14px; }
.vt-row-disabled   { opacity: 0.55; }
.vt-row-selected   { background: #f5f3ff !important; }

.vt-actions {
  display: flex;
  gap: 3px;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.12s;
}
.inv-row:hover .vt-actions { opacity: 1; }
.vt-act-edit:hover { background: #eff6ff; color: #2563eb; border-color: #bfdbfe; }
.vt-act-del:hover  { background: #fef2f2; color: #dc2626; border-color: #fecaca; }

/* ── Status badges ───────────────────────────────────────── */
.vt-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 9px;
  border-radius: 20px;
  font-size: 11.5px;
  font-weight: 500;
  white-space: nowrap;
  line-height: 1.6;
}
.vt-badge-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.vt-badge-green               { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
.vt-badge-green .vt-badge-dot { background: #22c55e; }
.vt-badge-gray                { background: #f9fafb; color: #6b7280; border: 1px solid #e5e7eb; }
.vt-badge-gray  .vt-badge-dot { background: #9ca3af; }

/* ── Empty state ─────────────────────────────────────────── */
.vt-empty { padding: 52px 24px; text-align: center; }
.vt-empty-icon {
  margin: 0 auto 14px; width: 56px; height: 56px; border-radius: 14px;
  background: #f9fafb; border: 1px solid #e5e7eb;
  display: flex; align-items: center; justify-content: center;
}
.vt-empty-title { font-size: 14px; font-weight: 600; color: #374151; margin-bottom: 5px; }
.vt-empty-sub   { font-size: 13px; color: #9ca3af; }

/* ── Table row hover ─────────────────────────────────────── */
.inv-row {
  border-bottom: 1px solid #f3f4f6;
  cursor: pointer;
  transition: background 0.12s;
}
.inv-row:hover { background: #faf9ff; }

/* ── Detail-view field grid helper ───────────────────────── */
.inv-field { display: flex; flex-direction: column; gap: 5px; }

/* ── Detail / profile view ───────────────────────────────── */
.sp-page { padding: 24px; display: flex; flex-direction: column; gap: 16px; }
.sp-bread { display: flex; align-items: center; gap: 8px; font-size: 12.5px; color: #6b7280; }
.sp-back { color: #7C3AED; text-decoration: none; display: inline-flex; align-items: center; gap: 4px; font-weight: 600; cursor: pointer; }
.sp-back:hover { color: #5B21B6; text-decoration: underline; }
.sp-bread-sep { color: #cbd5e1; }
.sp-bread-cur { color: #0f172a; font-weight: 600; }

.sp-header {
  display: flex; align-items: center; justify-content: space-between; gap: 20px;
  background: #fff; border: 1px solid #e5e7eb; border-radius: 12px;
  padding: 20px 24px; box-shadow: 0 1px 2px rgba(15,23,42,.04);
}
.sp-header-left { display: flex; align-items: center; gap: 16px; }
.sp-avatar {
  width: 56px; height: 56px; border-radius: 50%;
  background: linear-gradient(135deg, #7C3AED, #5B21B6);
  color: #fff; display: inline-flex; align-items: center; justify-content: center;
  font-size: 20px; font-weight: 700; flex-shrink: 0;
}
.sp-avatar.disabled { background: #9ca3af; }
.sp-name { font-size: 20px; font-weight: 700; color: #0f172a; letter-spacing: -0.01em; }
.sp-meta { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
.sp-chip { background: #f5f3ff; color: #6d28d9; padding: 3px 10px; border-radius: 20px; font-size: 11.5px; font-weight: 600; }
.sp-chip-muted { background: #f3f4f6; color: #475569; }
.sp-chip-danger { background: #fee2e2; color: #dc2626; }
.sp-chip-green { background: #f0fdf4; color: #15803d; }

.sp-btn-ghost {
  display: inline-flex; align-items: center; gap: 6px; background: #fff;
  border: 1px solid #e5e7eb; color: #374151; border-radius: 8px;
  padding: 8px 14px; font-size: 13px; font-weight: 600; cursor: pointer; font-family: inherit;
}
.sp-btn-ghost:hover:not(:disabled) { background: #f9fafb; border-color: #cbd5e1; }
.sp-btn-ghost:disabled { opacity: .5; cursor: not-allowed; }
.sp-btn-primary {
  display: inline-flex; align-items: center; gap: 6px;
  background: #7C3AED; color: #fff; border: none; border-radius: 8px;
  padding: 8px 14px; font-size: 13px; font-weight: 600; cursor: pointer; font-family: inherit;
}
.sp-btn-primary:hover { background: #5B21B6; }

.sp-note { font-size: 12px; color: #9ca3af; }

.sp-info-card {
  display: grid; grid-template-columns: 1.2fr 1fr 1.2fr; gap: 24px;
  background: #fff; border: 1px solid #e5e7eb; border-radius: 12px;
  padding: 18px 22px; box-shadow: 0 1px 2px rgba(15,23,42,.03);
}
.sp-info-section { display: flex; flex-direction: column; gap: 10px; }
.sp-section-title {
  font-size: 11px; font-weight: 700; color: #0f172a; text-transform: uppercase;
  letter-spacing: .05em; padding-bottom: 6px; border-bottom: 1px solid #f3f4f6;
}
.sp-kv { display: flex; justify-content: space-between; align-items: center; font-size: 12.5px; gap: 8px; }
.sp-k { color: #6b7280; font-weight: 500; flex-shrink: 0; }
.sp-v-empty { color: #9ca3af; }
.sp-link { color: #7C3AED; text-decoration: none; font-weight: 500; }
.sp-link:hover { text-decoration: underline; }
.sp-address { font-size: 12.5px; color: #374151; line-height: 1.6; }

@media (max-width: 768px) {
  .sp-page { padding: 12px !important; gap: 12px !important; }
  .sp-header { flex-direction: column; align-items: flex-start; gap: 12px; padding: 14px 16px; }
  .sp-header > div:last-child { width: 100%; display: flex; flex-wrap: wrap; gap: 8px; }
  .sp-header > div:last-child > button { flex: 1; justify-content: center; }
  .sp-info-card { grid-template-columns: 1fr !important; gap: 0 !important; padding: 0 !important; }
  .sp-info-section { padding: 14px 16px; border-bottom: 1px solid #f3f4f6; }
  .sp-info-section:last-child { border-bottom: none; }
}

/* ── Responsive: hide Designation / Reports To on small screens ── */
@media (max-width: 768px) {
  .vt-th:nth-child(3), .vt-th:nth-child(4),
  .vt-td:nth-child(3), .vt-td:nth-child(4) { display: none; }
}
</style>