<template>
<div class="list-page">

  <!-- Toolbar -->
  <div class="sales-toolbar">
    <div class="sales-search">
      <span v-html="icon('search',14)"></span>
      <input v-model="search" class="sales-search-input" placeholder="Search tax templates…" />
    </div>
    <div class="sales-pills">
      <button v-for="t in TYPE_PILLS" :key="t" class="sales-pill" :class="{active:typeFilter===t}" @click="typeFilter=t">
        {{ t }}<span v-if="t!=='All'" class="sales-pill-count">{{ typeCounts[t]||0 }}</span>
      </button>
    </div>
    <div class="sales-actions">
      <button class="sales-btn-ghost" @click="load" title="Refresh"><span v-html="icon('refresh',14)"></span></button>
      <button class="sales-btn-primary" @click="openNew" :disabled="!$canWrite('taxes')" :title="!$canWrite('taxes') ? 'Read-only access' : ''">
        <span v-html="icon('plus',13)"></span> New Template
      </button>
    </div>
  </div>

  <!-- Table -->
  <div class="inv-table-wrap">
    <table class="inv-table">
      <thead>
        <tr>
          <th>Template</th>
          <th>Type</th>
          <th>Rates</th>
          <th class="ta-r">Total Rate</th>
          <th>Default</th>
          <th>Status</th>
          <th style="width:90px"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading" v-for="n in 5" :key="'s'+n" class="shimmer-row"><td v-for="c in 7" :key="c"><div class="shimmer" style="width:80%"></div></td></tr>
        <template v-else>
          <tr v-for="t in filtered" :key="t.name" class="inv-row" @click="openEdit(t)">
            <td data-label="Template" class="td-id"><span class="inv-link">{{ t.template_name }}</span></td>
            <td data-label="Type">{{ t.tax_type || 'GST' }}</td>
            <td data-label="Rates" class="text-muted" style="font-size:12px">{{ t.rateLabel || '—' }}</td>
            <td data-label="Total Rate" class="ta-r">{{ t.totalRate != null ? t.totalRate + '%' : '—' }}</td>
            <td data-label="Default"><span v-if="t.is_default" class="inv-status-badge status-active">Default</span><span v-else class="text-muted">—</span></td>
            <td data-label="Status"><span class="inv-status-badge" :class="t.disabled ? 'status-inactive' : 'status-active'">{{ t.disabled ? 'Disabled' : 'Active' }}</span></td>
            <td data-label="" @click.stop>
              <button class="inv-act-btn" @click="openEdit(t)" :title="$canWrite('taxes') ? 'Edit' : 'View'"><span v-html="icon($canWrite('taxes')?'edit':'eye',14)"></span></button>
              <button class="inv-act-btn" v-if="$canWrite('taxes')" @click="confirmDel(t)" style="margin-left:6px;color:#dc2626" title="Delete"><span v-html="icon('trash',14)"></span></button>
            </td>
          </tr>
          <tr v-if="!filtered.length">
            <td colspan="7" class="bk-empty-state">
              <div class="bk-empty-inner">
                <div class="bk-empty-illus" style="font-size:34px">🧾</div>
                <p class="bk-empty-title">No tax templates</p>
                <p class="bk-empty-sub">Create a GST/VAT template to apply on invoices and bills.</p>
                <button class="bk-empty-btn" v-if="$canWrite('taxes')" @click="openNew"><span v-html="icon('plus',13)"></span> New Template</button>
              </div>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>

  <!-- Create / Edit drawer -->
  <Teleport to="body">
    <Transition name="tt-drawer">
    <div v-if="drawer" class="tt-bg" @click.self="closeDrawer">
      <div class="tt-drawer">
        <div class="tt-hdr">
          <div class="tt-hdr-left">
            <div class="tt-badge"><span v-html="icon('percent',18)"></span></div>
            <div>
              <div class="tt-title">{{ editing ? 'Edit Tax Template' : 'New Tax Template' }}</div>
              <div class="tt-sub">Applied to invoice & bill line items</div>
            </div>
          </div>
          <button class="tt-x" @click="closeDrawer"><span v-html="icon('x',16)"></span></button>
        </div>

        <div class="tt-body">
          <div class="tt-field" style="margin-bottom:16px">
            <label class="tt-label">Template Name <span class="tt-req">*</span></label>
            <input v-model="form.template_name" class="b-input" :placeholder="form.tax_type==='VAT' ? 'e.g. VAT 5%' : form.tax_type==='GST' ? 'e.g. GST 18%' : 'e.g. Cess 1%'" :disabled="!!editing" />
          </div>

          <div class="tt-field" style="margin-bottom:6px">
            <label class="tt-label">Tax Regime</label>
            <div class="tt-pills">
              <button v-for="t in ['GST','VAT','Custom']" :key="t" type="button" class="tt-pill" :class="{active:form.tax_type===t}" @click="setType(t)">{{ t }}</button>
            </div>
          </div>

          <!-- GST: single total rate, auto-split at invoice time -->
          <template v-if="form.tax_type==='GST'">
            <div class="tt-field" style="margin-top:16px">
              <label class="tt-label">Total GST Rate (%) <span class="tt-req">*</span></label>
              <input v-model.number="form.total_rate" type="number" min="0" step="0.5" class="b-input" placeholder="e.g. 18" />
            </div>
            <div class="tt-note">
              <span v-html="icon('info',14)"></span>
              <span>On invoices this auto-splits by <strong>Place of Supply</strong>: intra-state → <strong>CGST {{ half }}% + SGST {{ half }}%</strong>, inter-state → <strong>IGST {{ form.total_rate||0 }}%</strong>. GST accounts are resolved from your Chart of Accounts.</span>
            </div>
          </template>

          <!-- VAT: single flat rate -->
          <template v-else-if="form.tax_type==='VAT'">
            <div class="tt-field" style="margin-top:16px">
              <label class="tt-label">VAT Rate (%) <span class="tt-req">*</span></label>
              <input v-model.number="form.total_rate" type="number" min="0" step="0.5" class="b-input" placeholder="e.g. 5" />
            </div>
            <div class="tt-note">
              <span v-html="icon('info',14)"></span>
              <span>VAT is applied as a single flat rate on invoices &amp; bills (no place-of-supply split).</span>
            </div>
          </template>

          <!-- Custom: free rows -->
          <template v-else>
            <div class="tt-section">
              <span class="tt-section-title">Custom Rates</span>
              <button class="tt-add-row" @click="addRow"><span v-html="icon('plus',12)"></span> Add rate</button>
            </div>
            <div v-if="!form.taxes.length" class="tt-norows">No rates — this template applies 0%.</div>
            <div v-for="(r,i) in form.taxes" :key="i" class="tt-row">
              <input v-model.number="r.rate" type="number" min="0" step="0.5" class="b-input tt-row-rate" placeholder="Rate %" />
              <SearchableSelect v-model="r.account_head" :options="accounts" value-key="name" label-key="name" placeholder="Account head" class="tt-row-acct" />
              <input v-model="r.description" class="b-input tt-row-desc" placeholder="Description" />
              <button class="tt-row-del" @click="removeRow(i)" title="Remove"><span v-html="icon('trash',13)"></span></button>
            </div>
          </template>

          <div class="tt-grid2" style="margin-top:20px">
            <label class="tt-check"><input type="checkbox" :checked="form.is_default" @change="form.is_default = $event.target.checked ? 1 : 0" /> Set as default</label>
            <label class="tt-check"><input type="checkbox" :checked="form.disabled" @change="form.disabled = $event.target.checked ? 1 : 0" /> Disabled</label>
          </div>
        </div>

        <div class="tt-foot">
          <button class="b-btn b-btn-ghost" @click="closeDrawer">Cancel</button>
          <button class="tt-save" @click="save" :disabled="saving"><span v-html="icon('check',14)"></span> {{ saving ? 'Saving…' : editing ? 'Update' : 'Create' }}</button>
        </div>
      </div>
    </div>
    </Transition>
  </Teleport>
</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { apiList, apiGet, apiSave, apiPOST, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { useConfirm } from "../composables/useConfirm.js";
import { icon } from "../utils/icons.js";
import SearchableSelect from "../components/SearchableSelect.vue";

const { toast } = useToast();
const { confirm } = useConfirm();

const TYPE_PILLS = ["All", "GST", "VAT", "Custom"];

const list      = ref([]);
const loading   = ref(true);
const search    = ref("");
const typeFilter = ref("All");
const accounts  = ref([]);
const drawer    = ref(false);
const editing   = ref(null);
const saving    = ref(false);

const form = reactive({ template_name: "", tax_type: "GST", total_rate: 0, is_default: 0, disabled: 0, taxes: [] });
const half = computed(() => Math.round((Number(form.total_rate) || 0) / 2 * 100) / 100);
function setType(t) { form.tax_type = t; if (t === "Custom" && !form.taxes.length) form.taxes = [blankRow()]; }

function rateSummary(taxes) {
  const rows = taxes || [];
  const total = rows.reduce((s, r) => s + (Number(r.rate) || 0), 0);
  const label = rows.map((r) => `${r.tax_type} ${Number(r.rate) || 0}%`).join(" + ");
  return { totalRate: Math.round(total * 100) / 100, rateLabel: label };
}

async function load() {
  loading.value = true;
  try {
    const rows = await apiList("Tax Template", {
      fields: ["name", "template_name", "tax_type", "is_default", "disabled"],
      order: "template_name asc", limit: 200,
    }) || [];
    // Lazy-load child rows to show a rate summary (mirrors Invoices.vue).
    list.value = await Promise.all(rows.map(async (r) => {
      try {
        const doc = await apiGet("Tax Template", r.name);
        return { ...r, ...rateSummary(doc?.taxes), _taxes: doc?.taxes || [] };
      } catch { return { ...r, totalRate: null, rateLabel: "", _taxes: [] }; }
    }));
  } catch (e) { toast(e.message || "Failed to load tax templates", "error"); list.value = []; }
  loading.value = false;
}

async function loadAccounts() {
  try {
    let r = await apiList("Account", { fields: ["name"], filters: [["account_type", "=", "Tax"], ["is_group", "=", 0]], limit: 200, order: "name asc" });
    if (!r || !r.length) r = await apiList("Account", { fields: ["name"], filters: [["is_group", "=", 0]], limit: 500, order: "name asc" });
    accounts.value = r || [];
  } catch { accounts.value = []; }
}

const typeCounts = computed(() => {
  const m = {};
  list.value.forEach((t) => { const k = t.tax_type || "GST"; m[k] = (m[k] || 0) + 1; });
  return m;
});

const filtered = computed(() => {
  let r = list.value;
  if (typeFilter.value !== "All") r = r.filter((t) => (t.tax_type || "GST") === typeFilter.value);
  const q = search.value.trim().toLowerCase();
  if (q) r = r.filter((t) => (t.template_name || "").toLowerCase().includes(q));
  return r;
});

function blankRow() { return { tax_type: "CGST", rate: 0, account_head: "", description: "" }; }
function addRow() { form.taxes.push(blankRow()); }
function removeRow(i) { form.taxes.splice(i, 1); }

function openNew() {
  editing.value = null;
  Object.assign(form, { template_name: "", tax_type: "GST", total_rate: 0, is_default: 0, disabled: 0, taxes: [] });
  drawer.value = true;
}
function openEdit(t) {
  editing.value = t.name;
  const rows = (t._taxes || []).map((r) => ({ tax_type: r.tax_type, rate: Number(r.rate) || 0, account_head: r.account_head || "", description: r.description || "" }));
  const type = t.tax_type || "GST";
  // GST/VAT store their total across component rows — collapse to a single rate.
  const total = rows.reduce((s, r) => s + (Number(r.rate) || 0), 0);
  Object.assign(form, {
    template_name: t.template_name, tax_type: type,
    total_rate: type === "Custom" ? 0 : Math.round(total * 100) / 100,
    is_default: t.is_default ? 1 : 0, disabled: t.disabled ? 1 : 0,
    taxes: type === "Custom" ? (rows.length ? rows : [blankRow()]) : [],
  });
  drawer.value = true;
}
function closeDrawer() { drawer.value = false; editing.value = null; }

async function save() {
  if (!form.template_name.trim()) { toast("Template name is required", "error"); return; }
  saving.value = true;
  try {
    const company = await resolveCompany();
    if (!company) { toast("No company configured.", "error"); saving.value = false; return; }
    // Build child rows per regime. GST stores its total as CGST+SGST (the
    // intra-state view); the invoice re-splits by Place of Supply. VAT stores a
    // single VAT row. Custom keeps the user's free rows.
    let taxes;
    if (form.tax_type === "GST") {
      const total = Number(form.total_rate) || 0;
      const h = Math.round(total / 2 * 100) / 100;
      taxes = total > 0
        ? [{ tax_type: "CGST", rate: h, description: `CGST @ ${h}%` },
           { tax_type: "SGST", rate: h, description: `SGST @ ${h}%` }]
        : [];
    } else if (form.tax_type === "VAT") {
      const total = Number(form.total_rate) || 0;
      taxes = total > 0 ? [{ tax_type: "VAT", rate: total, description: `VAT @ ${total}%` }] : [];
    } else {
      taxes = form.taxes
        .filter((r) => Number(r.rate))
        .map((r) => ({ tax_type: "Other", rate: Number(r.rate) || 0, account_head: r.account_head || "", description: r.description || `Other @ ${Number(r.rate) || 0}%` }));
    }
    const doc = {
      doctype: "Tax Template",
      template_name: form.template_name.trim(),
      company,
      tax_type: form.tax_type,
      is_default: form.is_default,
      disabled: form.disabled,
      taxes: taxes.map((r) => ({ doctype: "Tax Template Detail", ...r })),
    };
    if (editing.value) doc.name = editing.value;
    await apiSave(doc);
    toast(editing.value ? "Tax template updated" : "Tax template created");
    closeDrawer();
    await load();
  } catch (e) { toast("Error: " + (e.message || e), "error"); }
  saving.value = false;
}

async function confirmDel(t) {
  const ok = await confirm({ title: "Delete Tax Template?", body: `"${t.template_name}" will be permanently removed.`, okLabel: "Delete", cancelLabel: "Keep it", okStyle: "danger" });
  if (!ok) return;
  try { await apiPOST("frappe.client.delete", { doctype: "Tax Template", name: t.name }); toast("Deleted"); await load(); }
  catch (e) { toast("Error: " + (e.message || e), "error"); }
}

onMounted(() => { load(); loadAccounts(); });
</script>

<style scoped>
.td-id .inv-link { font-weight: 600; }

/* Drawer */
.tt-bg     { position:fixed; inset:0; z-index:9000; background:rgba(15,23,42,.45); display:flex; justify-content:flex-end; backdrop-filter:blur(3px); }
.tt-drawer { width:560px; max-width:96vw; height:100%; background:#fff; display:flex; flex-direction:column; box-shadow:-24px 0 70px rgba(15,23,42,.22); }
.tt-hdr    { background:linear-gradient(180deg,#f6f9ff,#fff); border-bottom:1px solid #eef0f3; padding:18px 22px; display:flex; align-items:center; justify-content:space-between; gap:12px; }
.tt-hdr-left { display:flex; align-items:center; gap:12px; }
.tt-badge  { width:40px; height:40px; border-radius:11px; display:flex; align-items:center; justify-content:center; color:#fff; background:linear-gradient(135deg,#2f74f5,#1a6ef7); box-shadow:0 4px 12px rgba(26,110,247,.32); }
.tt-title  { font-size:16px; font-weight:700; color:#1A1D23; }
.tt-sub    { font-size:12px; color:#868E96; margin-top:2px; }
.tt-x      { background:#f1f5f9; border:none; cursor:pointer; width:32px; height:32px; border-radius:8px; color:#64748b; display:flex; align-items:center; justify-content:center; }
.tt-x:hover { background:#e2e8f0; color:#334155; }
.tt-body   { flex:1; overflow-y:auto; padding:22px; }
.tt-foot   { padding:16px 22px; border-top:1px solid #E2E8F0; display:flex; justify-content:flex-end; gap:10px; background:#F8F9FC; }

.tt-grid2  { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.tt-field  { min-width:0; }
.tt-label  { display:block; font-size:11.5px; font-weight:600; color:#475569; margin-bottom:5px; }
.tt-req    { color:#C92A2A; }
.b-input   { width:100%; box-sizing:border-box; border:1px solid #e2e8f0; border-radius:9px; padding:9px 11px; font-size:13px; background:#fff; font-family:inherit; }
.b-input:focus { border-color:#1a6ef7; box-shadow:0 0 0 3px rgba(26,110,247,.13); outline:none; }
.b-input:disabled { background:#f8fafc; color:#94a3b8; }

.tt-section { display:flex; align-items:center; justify-content:space-between; margin:22px 0 10px; }
.tt-section-title { font-size:11px; font-weight:700; letter-spacing:.6px; text-transform:uppercase; color:#64748b; }
.tt-add-row { display:inline-flex; align-items:center; gap:5px; border:1px solid #e2e8f0; background:#fff; border-radius:7px; padding:5px 10px; font-size:12px; font-weight:600; color:#1a6ef7; cursor:pointer; }
.tt-add-row:hover { background:#eaf1ff; }
.tt-norows  { font-size:12.5px; color:#94a3b8; padding:8px 0; }
.tt-row     { display:grid; grid-template-columns:90px 1fr 1fr 30px; gap:8px; align-items:center; margin-bottom:8px; }
.tt-row-del { border:none; background:none; cursor:pointer; color:#dc2626; display:flex; align-items:center; justify-content:center; padding:4px; }
.tt-row .b-input { padding:7px 9px; }

.tt-pills   { display:flex; gap:8px; }
.tt-pill    { flex:1; border:1.5px solid #e2e8f0; background:#fff; border-radius:9px; padding:9px 0; font-size:13px; font-weight:600; color:#64748b; cursor:pointer; font-family:inherit; transition:all .15s; }
.tt-pill:hover { border-color:#cbd5e1; }
.tt-pill.active { border-color:#1a6ef7; background:#eaf1ff; color:#1a4fd0; }
.tt-note    { display:flex; gap:8px; margin-top:12px; padding:10px 12px; background:#f0f7ff; border:1px solid #d6e6ff; border-radius:9px; font-size:12px; color:#475569; line-height:1.5; }
.tt-note strong { color:#1a4fd0; }
.tt-note :deep(svg) { flex-shrink:0; color:#1a6ef7; margin-top:1px; }

.tt-check   { display:flex; align-items:center; gap:8px; font-size:13px; color:#374151; cursor:pointer; }
.tt-save    { display:inline-flex; align-items:center; gap:6px; min-width:120px; justify-content:center; border:none; border-radius:9px; padding:9px 18px; font-size:13px; font-weight:600; color:#fff; cursor:pointer; background:linear-gradient(135deg,#2f74f5,#1a6ef7); box-shadow:0 4px 12px rgba(26,110,247,.28); }
.tt-save:hover:not(:disabled) { filter:brightness(1.04); }
.tt-save:disabled { opacity:.6; cursor:not-allowed; }

.tt-drawer-enter-active, .tt-drawer-leave-active { transition:opacity .25s ease; }
.tt-drawer-enter-active .tt-drawer, .tt-drawer-leave-active .tt-drawer { transition:transform .3s cubic-bezier(.4,0,.2,1); }
.tt-drawer-enter-from, .tt-drawer-leave-to { opacity:0; }
.tt-drawer-enter-from .tt-drawer, .tt-drawer-leave-to .tt-drawer { transform:translateX(100%); }

@media (max-width: 600px) {
  .tt-drawer { width:100%; }
  .tt-row { grid-template-columns:1fr 1fr; }
  .tt-row-acct, .tt-row-desc { grid-column:1 / -1; }
}
</style>
