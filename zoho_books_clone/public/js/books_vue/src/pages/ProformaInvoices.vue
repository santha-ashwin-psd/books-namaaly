<template>
<div class="b-page">
  <!-- Toolbar -->
  <div class="b-action-bar">
    <div style="display:flex;align-items:center;gap:6px;background:#fff;border:1px solid #E2E8F0;border-radius:20px;padding:5px 14px;flex:1;max-width:280px">
      <span v-html="icon('search',13)" style="color:#868E96;flex-shrink:0"></span>
      <input v-model="search" placeholder="Search proforma invoices…" style="border:none;outline:none;font-size:13px;width:100%;background:transparent;font-family:inherit"/>
    </div>
    <div style="display:flex;gap:6px;margin-left:auto">
      <button class="b-btn b-btn-ghost" @click="load"><span v-html="icon('refresh',13)"></span></button>
      <button class="b-btn b-btn-primary" :disabled="!$canWrite('invoices')" :title="!$canWrite('invoices') ? 'Read-only access' : ''" @click="openNew"><span v-html="icon('plus',13)"></span> New Proforma</button>
    </div>
  </div>

  <!-- Summary strip -->
  <SummaryStrip v-if="!loading" :cards="[
    { label: 'Total Proformas', tone: 'accent', value: list.length },
    { label: 'In Filter', tone: 'info', value: filtered.length, valueClass: 'blue' },
    { label: 'Pipeline Value', tone: 'warn', value: '₹' + fmtAmt(list.reduce((s,p) => s + (Number(p.grand_total)||0), 0)) },
  ]" />

  <!-- Table -->
  <div class="b-card" style="padding:0;overflow:hidden">
    <table class="b-table">
      <thead>
        <tr>
          <th>Proforma #</th>
          <th>Customer</th>
          <th>Date</th>
          <th class="ta-r">Amount</th>
          <th>Status</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <template v-if="loading">
          <tr v-for="n in 5" :key="n"><td colspan="6" style="padding:14px"><div class="b-shimmer" style="height:12px"></div></td></tr>
        </template>
        <tr v-else-if="!filtered.length">
          <td colspan="6" class="b-empty">{{ search ? 'No proforma invoices match your search' : 'No proforma invoices yet' }}</td>
        </tr>
        <tr v-else v-for="p in paged" :key="p.name" class="clickable" @click="openView(p)">
          <td><span class="mono" style="font-size:12px;color:#3B5BDB">{{p.name}}</span></td>
          <td class="fw-600">{{p.customer_name||p.customer||'—'}}</td>
          <td class="c-muted" style="font-size:12.5px">{{p.posting_date||'—'}}</td>
          <td class="ta-r mono" style="font-weight:600;color:#2F9E44">₹{{fmtAmt(p.grand_total)}}</td>
          <td><span class="b-badge b-badge-orange">Draft / Proforma</span></td>
          <td style="text-align:center">
            <button @click.stop="confirmDel(p)" style="background:none;border:none;cursor:pointer;color:#C92A2A;padding:4px" v-html="icon('trash',13)"></button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <div v-if="!loading && filtered.length" style="margin-top:12px">
    <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="filtered.length" />
  </div>

  <!-- View / Convert drawer -->
  <Teleport to="body">
    <div v-if="viewOpen" class="pf-overlay" @click.self="viewOpen=false"></div>
    <div class="pf-drawer pf-view-drawer" :class="{open:viewOpen}">
      <template v-if="viewDoc">
        <div class="pf-view-head">
          <div class="pf-view-head-row">
            <div>
              <div class="pf-view-num">{{ viewDoc.name }}</div>
              <div class="pf-view-sub">Proforma Invoice · {{ viewDoc.posting_date }}</div>
            </div>
            <button class="pf-dclose" @click="viewOpen=false"><span v-html="icon('x',16)"></span></button>
          </div>
          <div class="pf-view-amount">₹{{ fmtAmt(viewDoc.grand_total) }}</div>
        </div>

        <div class="pf-dbody">
          <div class="pf-section">
            <div class="pf-section-hdr"><span v-html="icon('user',13)"></span><span>Customer & Date</span></div>
            <div class="pf-meta-grid">
              <div><div class="pf-meta-lbl">Customer</div><div style="font-weight:600">{{ viewDoc.customer_name||viewDoc.customer }}</div></div>
              <div><div class="pf-meta-lbl">Date</div><div>{{ viewDoc.posting_date }}</div></div>
              <div><div class="pf-meta-lbl">Valid Until</div><div>{{ viewDoc.due_date||'—' }}</div></div>
              <div><div class="pf-meta-lbl">Grand Total</div><div class="mono" style="color:#16a34a;font-weight:700">₹{{ fmtAmt(viewDoc.grand_total) }}</div></div>
              <div style="grid-column:1/-1" v-if="viewDoc.remarks"><div class="pf-meta-lbl">Remarks</div><div>{{ viewDoc.remarks }}</div></div>
            </div>
          </div>

          <div class="pf-section" v-if="(viewDoc.items||[]).length">
            <div class="pf-section-hdr">
              <span v-html="icon('box',13)"></span><span>Items</span>
              <span style="margin-left:auto;font-size:11.5px;color:#6b7280;text-transform:none;letter-spacing:0">{{ (viewDoc.items||[]).length }} line{{ (viewDoc.items||[]).length!==1?'s':'' }}</span>
            </div>
            <table class="b-table" style="font-size:12.5px">
              <thead><tr><th>Item</th><th class="ta-r">Qty</th><th class="ta-r">Rate</th><th class="ta-r">Amount</th></tr></thead>
              <tbody>
                <tr v-for="it in viewDoc.items" :key="it.name||it.item_code">
                  <td>{{ it.item_name||it.item_code }}</td>
                  <td class="ta-r">{{ it.qty }}</td>
                  <td class="ta-r mono">₹{{ fmtAmt(it.rate) }}</td>
                  <td class="ta-r mono fw-700">₹{{ fmtAmt(it.amount) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="pf-dfooter">
          <button class="b-btn b-btn-ghost" @click="viewOpen=false">Close</button>
          <button class="b-btn pf-btn-amber" @click="printProforma">
            <span v-html="icon('print',13)"></span> Print
          </button>
          <button class="b-btn b-btn-primary" @click="convertToInvoice" :disabled="converting">
            {{ converting ? 'Converting…' : '→ Convert to Invoice' }}
          </button>
        </div>
      </template>
    </div>

    <!-- New Proforma drawer -->
    <div v-if="newOpen" class="pf-overlay" @click.self="newOpen=false"></div>
    <div class="pf-drawer" :class="{open:newOpen}">
      <div class="pf-dheader">
        <div class="pf-dheader-left">
          <div class="pf-dheader-ico"><span v-html="icon('invoices',18)"></span></div>
          <div>
            <div class="pf-dheader-title">New Proforma Invoice</div>
            <div class="pf-dheader-sub">A draft quote-style invoice for advance billing</div>
          </div>
        </div>
        <button class="pf-dclose" @click="newOpen=false"><span v-html="icon('x',16)"></span></button>
      </div>

      <div class="pf-dbody">
        <!-- Customer & Date -->
        <div class="pf-section">
          <div class="pf-section-hdr"><span v-html="icon('user',13)"></span><span>Customer & Date</span></div>
          <div class="pf-grid">
            <div class="pf-field" style="grid-column:1/-1">
              <label class="pf-flbl">Customer <span class="req">*</span></label>
              <SearchableSelect
                v-model="form.customer"
                :options="customers"
                placeholder="Select customer…"
                :createable="true"
                createDoctype="Customer"
                @search="fetchCustomers"
              />
            </div>
            <div class="pf-field">
              <label class="pf-flbl">Date <span class="req">*</span></label>
              <input class="pf-input" type="date" v-model="form.posting_date"/>
            </div>
            <div class="pf-field">
              <label class="pf-flbl">Valid Until</label>
              <input class="pf-input" type="date" v-model="form.due_date"/>
            </div>
            <div class="pf-field" style="grid-column:1/-1">
              <label class="pf-flbl">Remarks</label>
              <input class="pf-input" v-model="form.remarks" placeholder="e.g. Proforma Invoice for advance payment"/>
            </div>
          </div>
        </div>

        <!-- Items -->
        <div class="pf-section">
          <div class="pf-section-hdr">
            <span v-html="icon('box',13)"></span><span>Items <span class="req">*</span></span>
            <button class="b-btn b-btn-ghost" style="margin-left:auto;padding:4px 10px;font-size:12px" @click="addItem">
              <span v-html="icon('plus',11)" style="vertical-align:-1px;margin-right:3px"></span> Add Item
            </button>
          </div>
          <div v-for="(it,i) in form.items" :key="i" class="pf-item-row">
            <SearchableSelect
              v-model="it.item_code"
              :options="items"
              placeholder="Select item…"
              :createable="true"
              createDoctype="Item"
              @search="fetchItems"
              @select="opt => onItemSelect(it, opt)"
            />
            <input class="pf-input ta-r" type="number" v-model.number="it.qty" placeholder="Qty" min="0.01" @input="calcAmount(it)"/>
            <input class="pf-input ta-r" type="number" v-model.number="it.rate" placeholder="Rate" min="0" @input="calcAmount(it)"/>
            <button class="pf-rm" @click="removeItem(i)"><span v-html="icon('trash',12)"></span></button>
          </div>
          <div v-if="!form.items.length" class="pf-items-empty">No items yet — click Add Item</div>
          <div class="pf-total"><span>Total</span><span class="mono">₹{{ fmtAmt(itemTotal) }}</span></div>
        </div>
      </div>

      <div class="pf-dfooter">
        <button class="b-btn b-btn-ghost" @click="newOpen=false" :disabled="saving">Cancel</button>
        <button class="b-btn b-btn-primary" @click="saveProforma" :disabled="saving">{{ saving?'Saving…':'Save Proforma' }}</button>
      </div>
    </div>

    <!-- Delete confirm -->
    <div v-if="showDel" style="position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:1000;display:flex;align-items:center;justify-content:center" @click.self="showDel=false">
      <div class="b-card b-card-body" style="max-width:400px;width:90%">
        <div style="font-size:15px;font-weight:700;margin-bottom:8px;color:#C92A2A">Delete Proforma?</div>
        <div style="font-size:13px;color:#374151;margin-bottom:20px">Delete <strong>{{delTarget?.name}}</strong>? This cannot be undone.</div>
        <div style="display:flex;gap:8px;justify-content:flex-end">
          <button class="b-btn b-btn-ghost" @click="showDel=false">Cancel</button>
          <button class="b-btn" style="background:#C92A2A;color:#fff;border-color:#C92A2A" @click="doDelete">Delete</button>
        </div>
      </div>
    </div>
  </Teleport>
</div>
</template>

<script setup>
import { ref, reactive, computed } from "vue";
import { useRouter, useRoute } from "vue-router";
import { apiList, apiGet, apiGET, apiSave, apiDelete, apiSubmit, resolveCompany } from "../api/client.js";
import SearchableSelect from "../components/SearchableSelect.vue";
import { useToast } from "../composables/useToast.js";
import { useOpenFromQuery } from "../composables/useOpenFromQuery.js";
import { usePagination } from "../composables/usePagination.js";
import DocLink from "../components/DocLink.vue";
import Pagination from "../components/Pagination.vue";
import SummaryStrip from "../components/SummaryStrip.vue";
import { icon } from "../utils/icons.js";

const { toast } = useToast();
const router = useRouter();
const route = useRoute();

const list      = ref([]);
const loading   = ref(false);
const search    = ref("");
const viewOpen  = ref(false);
const viewDoc   = ref(null);
const newOpen   = ref(false);
const saving    = ref(false);
const converting = ref(false);
const showDel   = ref(false);
const delTarget = ref(null);
const custSugg  = ref([]);   // kept for compat, unused after SearchableSelect migration
const customers = ref([]);
const items     = ref([]);

const form = reactive({
  customer: "", posting_date: new Date().toISOString().slice(0,10),
  due_date: "", remarks: "Proforma Invoice", items: [],
});

const fmtAmt = (v) => Number(v||0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const itemTotal = computed(() => form.items.reduce((s,it) => s + (parseFloat(it.amount)||0), 0));

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase();
  if (!q) return list.value;
  return list.value.filter(p =>
    (p.name||"").toLowerCase().includes(q) ||
    (p.customer_name||"").toLowerCase().includes(q)
  );
});

const { page, pageSize, paged } = usePagination(filtered, { storageKey: "proforma" });

async function load() {
  loading.value = true;
  try {
    // Proforma invoices = draft Sales Invoices whose `notes` field contains 'Proforma'.
    // (The schema renamed the legacy `remarks` column to `notes`.)
    list.value = await apiList("Sales Invoice", {
      fields: ["name","customer","customer_name","posting_date","grand_total","notes","docstatus"],
      filters: [["docstatus","=",0],["notes","like","%Proforma%"]],
      limit: 200,
    });
    // Compat alias so existing template that reads `remarks` still works.
    list.value = list.value.map(r => ({ ...r, remarks: r.notes }));
  } catch (e) {
    console.warn("Proforma load failed:", e.message);
    list.value = [];
  } finally { loading.value = false; }
}

async function openView(p) {
  viewOpen.value = true;
  try { viewDoc.value = await apiGET("Sales Invoice", p.name); }
  catch { viewDoc.value = p; }
}

function printProforma() {
  if (!viewDoc.value) return;
  window.open(`/printview?doctype=Sales%20Invoice&name=${viewDoc.value.name}&format=Standard&no_letterhead=0`, "_blank");
}

async function convertToInvoice() {
  if (!viewDoc.value) return;
  converting.value = true;
  try {
    await apiSubmit("Sales Invoice", viewDoc.value.name);
    toast.success(`Invoice ${viewDoc.value.name} finalized`);
    viewOpen.value = false;
    router.push("/invoices");
  } catch (e) { toast.error(e.message || "Conversion failed"); }
  finally { converting.value = false; }
}

function openNew() {
  Object.assign(form, { customer:"", posting_date: new Date().toISOString().slice(0,10), due_date:"", remarks:"Proforma Invoice", items:[] });
  custSugg.value = [];
  fetchCustomers("");
  fetchItems("");
  addItem();
  newOpen.value = true;
}

function addItem() { form.items.push({ item_code:"", qty:1, rate:0, amount:0 }); }
function removeItem(i) { form.items.splice(i, 1); }
function calcAmount(it) { it.amount = (parseFloat(it.qty)||0) * (parseFloat(it.rate)||0); }
// ── Dropdown fetchers ─────────────────────────────────────────────────────────
async function fetchCustomers(q = "") {
  try {
    const f = [["disabled", "=", 0]];
    if (q) f.push(["customer_name", "like", "%" + q + "%"]);
    const r = await apiList("Customer", { fields: ["name", "customer_name"], filters: f, limit: 30, order: "customer_name asc" });
    customers.value = (r || []).map(x => ({ ...x, label: x.customer_name || x.name, value: x.name }));
  } catch { customers.value = []; }
}

async function fetchItems(q = "") {
  try {
    const f = [["disabled", "=", 0]];
    if (q) f.push(["item_name", "like", "%" + q + "%"]);
    const r = await apiList("Item", { fields: ["name", "item_name", "standard_rate", "stock_uom", "description"], filters: [...f, ["has_variants", "=", 0]], limit: 30, order: "item_name asc" });
    items.value = (r || []).map(x => ({
      ...x,
      label: x.item_name || x.name,
      value: x.name,
      rate: x.standard_rate || 0,
      uom: x.stock_uom || "Nos",
      description: x.description || "",
    }));
  } catch { items.value = []; }
}

function onItemSelect(it, opt) {
  const code = opt?.value ?? opt;
  it.item_code = code;
  const found = items.value.find(i => i.value === code || i.name === code);
  if (found) {
    it.rate      = found.rate ?? 0;
    it.item_name = found.label || found.item_name || code;
    it.description = found.description || "";
    calcAmount(it);
  }
}

// ── Kept for backward compat (no longer wired to template) ───────────────────
function onCustInput() {}
function pickCust(s) { form.customer = s.name; custSugg.value = []; }
async function onItemChange(it) {
  if (!it.item_code) return;
  try {
    const doc = await apiGet("Item", it.item_code);
    if (doc?.standard_rate) { it.rate = doc.standard_rate; calcAmount(it); }
  } catch {}
}

async function saveProforma() {
  if (!form.customer.trim()) { toast.error("Customer is required"); return; }
  if (!form.items.length || !form.items[0].item_code) { toast.error("Add at least one item"); return; }
  saving.value = true;
  try {
    const company = await resolveCompany();
    const doc = {
      doctype: "Sales Invoice",
      customer: form.customer,
      posting_date: form.posting_date,
      due_date: form.due_date || form.posting_date,
      company,
      notes: form.remarks || "Proforma Invoice",
      items: form.items.filter(it => it.item_code?.trim()).map(it => ({
        doctype: "Sales Invoice Item",
        item_code: it.item_code,
        item_name: it.item_name || it.item_code,
        description: it.description || it.item_name || it.item_code,
        qty: parseFloat(it.qty) || 1,
        rate: parseFloat(it.rate) || 0,
        amount: parseFloat(it.amount) || 0,
      })),
    };
    const saved = await apiSave(doc);
    toast.success(`Proforma ${saved.name} saved`);
    newOpen.value = false;
    await load();
  } catch (e) { toast.error(e.message || "Failed to save"); }
  finally { saving.value = false; }
}

function confirmDel(p) { delTarget.value = p; showDel.value = true; }
async function doDelete() {
  try {
    await apiDelete("Sales Invoice", delTarget.value.name);
    toast.success("Deleted");
    showDel.value = false;
    await load();
  } catch (e) { toast.error(e.message || "Delete failed"); }
}

import { onMounted } from "vue";
onMounted(async () => {
  await load();
  useOpenFromQuery({
    route,
    openByName: (n) => openView(list.value.find(x => x.name === n) || { name: n }),
  });
});
</script>

<style scoped>
.pf-overlay{position:fixed;inset:0;background:rgba(15,23,42,.28);backdrop-filter:blur(2px);z-index:40;}
.pf-drawer{position:fixed;top:0;right:-580px;bottom:0;width:580px;max-width:96vw;background:#fff;border-left:1px solid #e5e7eb;box-shadow:-12px 0 32px rgba(15,23,42,.12);z-index:50;display:flex;flex-direction:column;transition:right .24s cubic-bezier(.32,.72,0,1);}
.pf-drawer.open{right:0;}
.pf-view-drawer{width:560px;right:-560px;}.pf-view-drawer.open{right:0;}

.pf-dheader{display:flex;align-items:flex-start;justify-content:space-between;padding:18px 20px;border-bottom:1px solid #e5e7eb;flex-shrink:0;background:linear-gradient(135deg,#fff9db 0%,#ffe066 100%);}
.pf-dheader-left{display:flex;align-items:flex-start;gap:12px;}
.pf-dheader-ico{width:38px;height:38px;border-radius:10px;background:#fff;border:1px solid rgba(202,138,4,.25);display:inline-flex;align-items:center;justify-content:center;color:#ca8a04;box-shadow:0 1px 3px rgba(15,23,42,.06);flex-shrink:0;}
.pf-dheader-title{font-size:15px;font-weight:700;color:#111827;letter-spacing:-0.01em;}
.pf-dheader-sub{font-size:12px;color:#876800;margin-top:3px;font-weight:500;}
.pf-dclose{background:rgba(255,255,255,.65);border:none;cursor:pointer;color:#475569;display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border-radius:8px;transition:background .15s;}
.pf-dclose:hover{background:#fff;color:#111827;}

.pf-view-head{padding:18px 20px;border-bottom:1px solid #e5e7eb;background:linear-gradient(135deg,#fff9db 0%,#ffe066 100%);flex-shrink:0;}
.pf-view-head-row{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;}
.pf-view-num{font-size:18px;font-weight:700;color:#111827;}
.pf-view-sub{font-size:12.5px;color:#876800;margin-top:2px;}
.pf-view-amount{font-size:24px;font-weight:800;color:#16a34a;margin-top:10px;}

.pf-dbody{flex:1;overflow-y:auto;padding:18px 20px;display:flex;flex-direction:column;gap:14px;background:#f8fafc;}
.pf-section{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:12px;box-shadow:0 1px 2px rgba(15,23,42,.03);}
.pf-section-hdr{display:flex;align-items:center;gap:8px;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:#0f172a;}
.pf-section-hdr svg{color:#ca8a04;}

.pf-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
.pf-field{display:flex;flex-direction:column;gap:4px;}
.pf-flbl{font-size:12px;font-weight:600;color:#374151;}
.pf-input{border:1px solid #e2e8f0;border-radius:8px;padding:8px 12px;font:inherit;font-size:13px;outline:none;background:#fff;color:#0f172a;transition:border-color .15s,box-shadow .15s;width:100%;box-sizing:border-box;}
.pf-input:hover:not(:disabled){border-color:#cbd5e1;}
.pf-input:focus{border-color:#ca8a04;box-shadow:0 0 0 3px rgba(202,138,4,.15);}
.req{color:#dc2626;}

.pf-suggest{position:absolute;top:calc(100% + 4px);left:0;right:0;background:#fff;border:1px solid #e5e7eb;border-radius:8px;box-shadow:0 8px 24px rgba(15,23,42,.10);z-index:100;max-height:200px;overflow-y:auto;}
.pf-suggest-item{padding:8px 12px;cursor:pointer;font-size:13px;border-bottom:1px solid #f3f4f6;}
.pf-suggest-item:hover{background:#fff9db;}
.pf-suggest-item:last-child{border-bottom:none;}

.pf-item-row{display:grid;grid-template-columns:2fr 80px 100px 32px;gap:8px;align-items:center;}
.pf-rm{background:#fef2f2;border:1px solid #fecaca;border-radius:6px;cursor:pointer;color:#dc2626;height:32px;display:inline-flex;align-items:center;justify-content:center;}
.pf-rm:hover{background:#fee2e2;}
.pf-items-empty{font-size:12px;color:#868E96;text-align:center;padding:14px;background:#f9fafb;border:1px dashed #e5e7eb;border-radius:8px;}
.pf-total{display:flex;justify-content:space-between;align-items:center;padding:10px 14px;background:linear-gradient(135deg,#fff9db,#fff);border:1px solid #ffe066;border-radius:8px;font-size:14px;font-weight:700;color:#0f172a;}

.pf-meta-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
.pf-meta-lbl{font-size:11px;color:#9ca3af;text-transform:uppercase;letter-spacing:.04em;margin-bottom:3px;font-weight:600;}

.pf-dfooter{display:flex;align-items:center;justify-content:flex-end;gap:8px;padding:14px 20px;border-top:1px solid #e5e7eb;background:#fff;flex-shrink:0;}
.pf-btn-amber{background:#fff9db;color:#a16207;border:1px solid #ffd43b;}
.pf-btn-amber:hover{background:#fff3bf;}
</style>