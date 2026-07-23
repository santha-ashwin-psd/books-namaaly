<template>
<div class="list-page">

  <!-- Toolbar -->
  <div class="sales-toolbar">
    <div class="sales-search">
      <span v-html="icon('search',14)"></span>
      <input v-model="search" class="sales-search-input" placeholder="Search expense categories…" />
    </div>
    <div class="sales-pills">
      <button v-for="s in STATUS_PILLS" :key="s" class="sales-pill" :class="{active:statusFilter===s}" @click="statusFilter=s">
        {{ s }}<span v-if="s!=='All'" class="sales-pill-count">{{ statusCounts[s]||0 }}</span>
      </button>
    </div>
    <div class="sales-actions">
      <button class="sales-btn-ghost" @click="load" title="Refresh"><span v-html="icon('refresh',14)"></span></button>
      <button class="sales-btn-primary" @click="openNew" :disabled="!$canWrite('bills')" :title="!$canWrite('bills') ? 'Read-only access' : ''">
        <span v-html="icon('plus',13)"></span> New Category
      </button>
    </div>
  </div>

  <!-- Table -->
  <div class="inv-table-wrap">
    <table class="inv-table">
      <thead>
        <tr>
          <th>Category</th>
          <th>Description</th>
          <th>Status</th>
          <th style="width:90px"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading" v-for="n in 5" :key="'s'+n" class="shimmer-row"><td v-for="c in 4" :key="c"><div class="shimmer" style="width:80%"></div></td></tr>
        <template v-else>
          <tr v-for="c in filtered" :key="c.name" class="inv-row" @click="openEdit(c)">
            <td data-label="Category" class="td-id"><span class="inv-link">{{ c.category_name }}</span></td>
            <td data-label="Description" class="text-muted eco-desc" style="font-size:12px" :title="c.description || ''">{{ c.description || '—' }}</td>
            <td data-label="Status"><span class="inv-status-badge" :class="c.disabled ? 'status-inactive' : 'status-active'">{{ c.disabled ? 'Disabled' : 'Active' }}</span></td>
            <td data-label="" @click.stop>
              <button class="inv-act-btn" @click="openEdit(c)" :title="$canWrite('bills') ? 'Edit' : 'View'"><span v-html="icon($canWrite('bills')?'edit':'eye',14)"></span></button>
              <button class="inv-act-btn" v-if="$canWrite('bills')" @click="confirmDel(c)" style="margin-left:6px;color:#dc2626" title="Delete"><span v-html="icon('trash',14)"></span></button>
            </td>
          </tr>
          <tr v-if="!filtered.length">
            <td colspan="4" class="bk-empty-state">
              <div class="bk-empty-inner">
                <div class="bk-empty-illus" style="font-size:34px">🗂️</div>
                <p class="bk-empty-title">No expense categories</p>
                <p class="bk-empty-sub">Create a category to classify expenses and expense claims.</p>
                <button class="bk-empty-btn" v-if="$canWrite('bills')" @click="openNew"><span v-html="icon('plus',13)"></span> New Category</button>
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
            <div class="tt-badge"><span v-html="icon('folder',18)"></span></div>
            <div>
              <div class="tt-title">{{ editing ? 'Edit Expense Category' : 'New Expense Category' }}</div>
              <div class="tt-sub">Used to classify Expenses &amp; Expense Claims</div>
            </div>
          </div>
          <button class="tt-x" @click="closeDrawer"><span v-html="icon('x',16)"></span></button>
        </div>

        <div class="tt-body">
          <div class="tt-field" style="margin-bottom:16px">
            <label class="tt-label">Category Name <span class="tt-req">*</span></label>
            <input v-model="form.category_name" class="b-input" placeholder="e.g. Travel" :disabled="!!editing" />
          </div>

          <div class="tt-field" style="margin-bottom:16px">
            <label class="tt-label">Description</label>
            <textarea v-model="form.description" class="b-input" rows="3" placeholder="Optional notes about this category"></textarea>
          </div>

          <label class="tt-check"><input type="checkbox" :checked="form.disabled" @change="form.disabled = $event.target.checked ? 1 : 0" /> Disabled</label>
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
import { apiList, apiSave, apiPOST, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { useConfirm } from "../composables/useConfirm.js";
import { icon } from "../utils/icons.js";

const { toast } = useToast();
const { confirm } = useConfirm();

const STATUS_PILLS = ["All", "Active", "Disabled"];

const list        = ref([]);
const loading     = ref(true);
const search      = ref("");
const statusFilter = ref("All");
const drawer      = ref(false);
const editing     = ref(null);
const saving      = ref(false);

const form = reactive({ category_name: "", description: "", disabled: 0 });

async function load() {
  loading.value = true;
  try {
    list.value = await apiList("Expense Category", {
      fields: ["name", "category_name", "description", "disabled"],
      order: "category_name asc", limit: 200,
    }) || [];
  } catch (e) { toast(e.message || "Failed to load expense categories", "error"); list.value = []; }
  loading.value = false;
}

const statusCounts = computed(() => {
  const m = { Active: 0, Disabled: 0 };
  list.value.forEach((c) => { m[c.disabled ? "Disabled" : "Active"]++; });
  return m;
});

const filtered = computed(() => {
  let r = list.value;
  if (statusFilter.value !== "All") {
    r = r.filter((c) => (c.disabled ? "Disabled" : "Active") === statusFilter.value);
  }
  const q = search.value.trim().toLowerCase();
  if (q) r = r.filter((c) => (c.category_name || "").toLowerCase().includes(q));
  return r;
});

function openNew() {
  editing.value = null;
  Object.assign(form, { category_name: "", description: "", disabled: 0 });
  drawer.value = true;
}
function openEdit(c) {
  editing.value = c.name;
  Object.assign(form, {
    category_name: c.category_name,
    description: c.description || "",
    disabled: c.disabled ? 1 : 0,
  });
  drawer.value = true;
}
function closeDrawer() { drawer.value = false; editing.value = null; }

async function save() {
  if (!form.category_name.trim()) { toast("Category name is required", "error"); return; }
  saving.value = true;
  try {
    const company = await resolveCompany();
    if (!company) { toast("No company configured.", "error"); saving.value = false; return; }
    const doc = {
      doctype: "Expense Category",
      category_name: form.category_name.trim(),
      company,
      description: form.description || "",
      disabled: form.disabled,
    };
    if (editing.value) doc.name = editing.value;
    await apiSave(doc);
    toast(editing.value ? "Expense category updated" : "Expense category created");
    closeDrawer();
    await load();
  } catch (e) { toast("Error: " + (e.message || e), "error"); }
  saving.value = false;
}

async function confirmDel(c) {
  const ok = await confirm({ title: "Delete Expense Category?", body: `"${c.category_name}" will be permanently removed.`, okLabel: "Delete", cancelLabel: "Keep it", okStyle: "danger" });
  if (!ok) return;
  try { await apiPOST("frappe.client.delete", { doctype: "Expense Category", name: c.name }); toast("Deleted"); await load(); }
  catch (e) { toast("Error: " + (e.message || e), "error"); }
}

onMounted(() => { load(); });
</script>

<style scoped>
.td-id .inv-link { font-weight: 600; }

/* Prevent a long, unbroken description from blowing out the table layout —
   clip it with an ellipsis and show the full text on hover via [title]. */
.inv-table th:nth-child(2), .inv-table td.eco-desc {
  max-width: 320px;
}
.eco-desc {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Drawer */
.tt-bg     { position:fixed; inset:0; z-index:9000; background:rgba(15,23,42,.45); display:flex; justify-content:flex-end; backdrop-filter:blur(3px); }
.tt-drawer { width:480px; max-width:96vw; height:100%; background:#fff; display:flex; flex-direction:column; box-shadow:-24px 0 70px rgba(15,23,42,.22); }
.tt-hdr    { background:linear-gradient(180deg,#f6f9ff,#fff); border-bottom:1px solid #eef0f3; padding:18px 22px; display:flex; align-items:center; justify-content:space-between; gap:12px; }
.tt-hdr-left { display:flex; align-items:center; gap:12px; }
.tt-badge  { width:40px; height:40px; border-radius:11px; display:flex; align-items:center; justify-content:center; color:#fff; background:linear-gradient(135deg,#2f74f5,#1a6ef7); box-shadow:0 4px 12px rgba(26,110,247,.32); }
.tt-title  { font-size:16px; font-weight:700; color:#1A1D23; }
.tt-sub    { font-size:12px; color:#868E96; margin-top:2px; }
.tt-x      { background:#f1f5f9; border:none; cursor:pointer; width:32px; height:32px; border-radius:8px; color:#64748b; display:flex; align-items:center; justify-content:center; }
.tt-x:hover { background:#e2e8f0; color:#334155; }
.tt-body   { flex:1; overflow-y:auto; padding:22px; }
.tt-foot   { padding:16px 22px; border-top:1px solid #E2E8F0; display:flex; justify-content:flex-end; gap:10px; background:#F8F9FC; }

.tt-field  { min-width:0; }
.tt-label  { display:block; font-size:11.5px; font-weight:600; color:#475569; margin-bottom:5px; }
.tt-req    { color:#C92A2A; }
.b-input   { width:100%; box-sizing:border-box; border:1px solid #e2e8f0; border-radius:9px; padding:9px 11px; font-size:13px; background:#fff; font-family:inherit; }
.b-input:focus { border-color:#1a6ef7; box-shadow:0 0 0 3px rgba(26,110,247,.13); outline:none; }
.b-input:disabled { background:#f8fafc; color:#94a3b8; }
textarea.b-input { resize:vertical; }

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
}

/* list.css defines a strict Invoice-specific mobile grid at ≤425px (named
   areas: id/amount/customer/date/badge/actions) that applies globally to any
   .inv-table. Our cells don't carry those specific classes, so the Category
   name and Description were falling outside the grid instead of stacking
   normally. Override back to a simple stacked card for this page only. */
@media (max-width: 425px) {
  .inv-table tbody .inv-row {
    display: block !important;
    padding: 4px 0 !important;
  }
  .inv-table tbody .inv-row::after { display: none !important; }
  .inv-table td {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    padding: 7px 14px !important;
    border: none !important;
    border-bottom: 1px solid #f0f2f5 !important;
    font-size: 13px !important;
  }
  .inv-table td[data-label]::before {
    display: block !important;
    content: attr(data-label);
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .04em; color: #9ca3af; flex-shrink: 0; margin-right: 8px;
  }
  .td-id { padding: 7px 14px !important; }
  .td-id .inv-link { font-weight: 600 !important; font-size: 14.5px !important; color:#1a1a2e !important; }
  .eco-desc { max-width: 60%; }
  .inv-table td:last-child {
    display: flex !important;
    justify-content: flex-end !important;
    gap: 6px !important;
    border-bottom: none !important;
    padding: 8px 14px !important;
  }
}
</style>