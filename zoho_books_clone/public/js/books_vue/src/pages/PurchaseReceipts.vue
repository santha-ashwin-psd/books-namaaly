<template>
<div class="b-page">
  <div class="b-action-bar">
    <div style="display:flex;align-items:center;gap:6px;background:#fff;border:1px solid #E2E8F0;border-radius:20px;padding:5px 14px;flex:1;max-width:280px">
      <span v-html="icon('search',13)" style="color:#868E96;flex-shrink:0"></span>
      <input v-model="search" placeholder="Search receipts…" style="border:none;outline:none;font-size:13px;width:100%;background:transparent;font-family:inherit"/>
    </div>
    <div style="display:flex;gap:6px">
      <button v-for="t in TABS" :key="t.k" class="b-pill" :class="{active:tab===t.k}" @click="tab=t.k">{{t.l}}</button>
    </div>
    <div style="margin-left:auto;display:flex;gap:6px">
      <button class="b-btn b-btn-ghost" @click="load"><span v-html="icon('refresh',13)"></span></button>
      <button class="b-btn b-btn-primary" :disabled="!$canWrite('bills')" :title="!$canWrite('bills') ? 'Read-only access' : ''" @click="openNew"><span v-html="icon('plus',13)"></span> New GRN</button>
    </div>
  </div>

  <SummaryStrip v-if="!loading" :cards="[
    { label: 'Total',     tone: 'accent',                                       value: list.length },
    { label: 'Draft',     tone: counts.draft>0 ? 'warn' : 'default',            value: counts.draft,     valueClass: counts.draft>0 ? 'orange' : '' },
    { label: 'Received',  tone: 'success',                                      value: counts.received,  valueClass: 'green' },
    { label: 'Cancelled', tone: counts.cancelled>0 ? 'danger' : 'default',      value: counts.cancelled, valueClass: counts.cancelled>0 ? 'red' : '' },
  ]" />

  <div class="b-card" style="padding:0;overflow:hidden">
    <table class="b-table">
      <thead>
        <tr>
          <th>GRN #</th>
          <th>Supplier</th>
          <th>Date</th>
          <th>Purchase Order</th>
          <th class="ta-r">Items</th>
          <th>Status</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <template v-if="loading">
          <tr v-for="n in 5" :key="n"><td colspan="7" style="padding:14px"><div class="b-shimmer" style="height:12px"></div></td></tr>
        </template>
        <tr v-else-if="!sorted.length">
          <td colspan="7" class="b-empty">{{search ? 'No results' : 'No purchase receipts yet'}}</td>
        </tr>
        <tr v-else v-for="r in paged" :key="r.name" class="clickable" @click="openView(r)">
          <td><span class="mono" style="font-size:12px;color:#3B5BDB">{{r.name}}</span></td>
          <td class="fw-600">{{r.supplier_name||r.supplier||'—'}}</td>
          <td class="c-muted" style="font-size:12.5px">{{r.posting_date||'—'}}</td>
          <td class="c-muted mono" style="font-size:12px">{{r.purchase_order||'—'}}</td>
          <td class="ta-r c-muted" style="font-size:12.5px">{{r.total_qty||'—'}}</td>
          <td>
            <span class="b-badge" :class="statusClass(r)">{{statusLabel(r)}}</span>
          </td>
          <td style="text-align:center">
            <button class="b-btn b-btn-ghost" style="padding:4px 8px;font-size:11.5px" @click.stop="openView(r)"><span v-html="icon('eye',12)"></span></button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- ── Pagination ── -->
  <div v-if="!loading && sorted.length" style="padding:12px 4px 4px">
    <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="sorted.length" />
  </div>

  <Teleport to="body">
    <!-- View drawer -->
    <div v-if="viewOpen" style="position:fixed;inset:0;background:rgba(0,0,0,.2);z-index:40" @click.self="viewOpen=false"></div>
    <div :style="'position:fixed;top:0;right:0;bottom:0;width:520px;background:#fff;border-left:1px solid #e5e7eb;z-index:50;display:flex;flex-direction:column;transition:transform .22s;transform:'+(viewOpen?'translateX(0)':'translateX(100%)')">
      <template v-if="viewDoc">
        <div style="display:flex;align-items:center;justify-content:space-between;padding:0 20px;height:60px;border-bottom:1px solid #e5e7eb;flex-shrink:0;background:#EDF2FF">
          <div>
            <div style="font-size:15px;font-weight:700;">{{viewDoc.name}}</div>
            <div style="font-size:12px;color:#6b7280;margin-top:1px">GRN · {{viewDoc.posting_date}}</div>
          </div>
          <div style="display:flex;align-items:center;gap:8px">
            <span class="b-badge" :class="statusClass(viewDoc)">{{statusLabel(viewDoc)}}</span>
            <button @click="viewOpen=false" style="background:none;border:none;cursor:pointer;padding:4px" v-html="icon('x',16)"></button>
          </div>
        </div>
        <div style="flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:16px">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
            <div><div style="font-size:11px;color:#9ca3af;text-transform:uppercase;margin-bottom:3px">Supplier</div><div style="font-weight:600">{{viewDoc.supplier_name||viewDoc.supplier}}</div></div>
            <div><div style="font-size:11px;color:#9ca3af;text-transform:uppercase;margin-bottom:3px">Date</div><div>{{viewDoc.posting_date}}</div></div>
            <div><div style="font-size:11px;color:#9ca3af;text-transform:uppercase;margin-bottom:3px">Purchase Order</div><div class="mono" style="font-size:12.5px">{{viewDoc.purchase_order||'—'}}</div></div>
            <div><div style="font-size:11px;color:#9ca3af;text-transform:uppercase;margin-bottom:3px">Warehouse</div><div style="font-size:12.5px">{{viewDoc.set_warehouse||'—'}}</div></div>
            <div style="grid-column:1/-1"><div style="font-size:11px;color:#9ca3af;text-transform:uppercase;margin-bottom:3px">Remarks</div><div style="font-size:12.5px">{{viewDoc.remarks||'—'}}</div></div>
          </div>
          <div v-if="(viewDoc.items||[]).length">
            <div style="font-size:12px;font-weight:700;color:#374151;margin-bottom:8px;text-transform:uppercase;letter-spacing:.04em">Items Received</div>
            <table class="b-table" style="font-size:12px">
              <thead><tr><th>Item</th><th class="ta-r">Qty</th><th class="ta-r">Accepted</th><th class="ta-r">Rejected</th><th>UOM</th></tr></thead>
              <tbody>
                <tr v-for="it in viewDoc.items" :key="it.name||it.item_code">
                  <td>{{it.item_name||it.item_code}}</td>
                  <td class="ta-r mono">{{it.qty}}</td>
                  <td class="ta-r mono" style="color:#2F9E44">{{it.accepted_qty||it.qty}}</td>
                  <td class="ta-r mono" style="color:#C92A2A">{{it.rejected_qty||0}}</td>
                  <td class="c-muted">{{it.uom||'Nos'}}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div style="padding:14px 20px;border-top:1px solid #e5e7eb;display:flex;gap:8px;justify-content:flex-end">
          <button class="b-btn b-btn-ghost" @click="viewOpen=false">Close</button>
          <button v-if="viewDoc.docstatus===0" class="b-btn b-btn-primary" @click="submitGRN" :disabled="submitting">
            {{submitting ? 'Submitting…' : 'Submit GRN'}}
          </button>
        </div>
      </template>
    </div>

    <!-- New GRN drawer -->
    <div v-if="newOpen" style="position:fixed;inset:0;background:rgba(0,0,0,.2);z-index:40" @click.self="newOpen=false"></div>
    <div :style="'position:fixed;top:0;right:0;bottom:0;width:560px;background:#fff;border-left:1px solid #e5e7eb;z-index:50;display:flex;flex-direction:column;transition:transform .22s;transform:'+(newOpen?'translateX(0)':'translateX(100%)')">
      <div style="display:flex;align-items:center;justify-content:space-between;padding:0 20px;height:60px;border-bottom:1px solid #e5e7eb;flex-shrink:0">
        <span style="font-size:15px;font-weight:700">New Purchase Receipt (GRN)</span>
        <button @click="newOpen=false" style="background:none;border:none;cursor:pointer;padding:4px" v-html="icon('x',16)"></button>
      </div>
      <div style="flex:1;overflow-y:auto;padding:20px;display:grid;gap:14px;align-content:start">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
          <div class="nim-field" style="grid-column:1/-1">
            <label class="nim-label">Supplier <span style="color:#c92a2a">*</span></label>
            <SearchableSelect v-model="form.supplier" :options="vendorOptions"
              placeholder="Search supplier…" @search="fetchVendors" @select="onSupSelect" />
          </div>
          <div class="nim-field">
            <label class="nim-label">Date <span style="color:#c92a2a">*</span></label>
            <input class="nim-input" type="date" v-model="form.posting_date"/>
          </div>
          <div class="nim-field">
            <label class="nim-label">Purchase Order #</label>
            <SearchableSelect v-model="form.purchase_order" :options="poOptions"
              placeholder="Select PO (filtered by supplier)…"
              @search="fetchPOs" @open="fetchPOs('')" />
          </div>
          <div class="nim-field" style="grid-column:1/-1">
            <label class="nim-label">Warehouse</label>
            <input class="nim-input" v-model="form.set_warehouse" placeholder="e.g. Stores - ABC"/>
          </div>
          <div class="nim-field" style="grid-column:1/-1">
            <label class="nim-label">Remarks</label>
            <input class="nim-input" v-model="form.remarks" placeholder="Optional remarks"/>
          </div>
        </div>

        <!-- Items -->
        <div>
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
            <label class="nim-label" style="margin:0">Items Received <span style="color:#c92a2a">*</span></label>
            <button class="b-btn b-btn-ghost" style="padding:4px 10px;font-size:12px" @click="addItem">
              <span v-html="icon('plus',11)" style="vertical-align:-1px;margin-right:3px"></span> Add Item
            </button>
          </div>
          <div v-for="(it,i) in form.items" :key="i" style="display:grid;grid-template-columns:2fr 70px 70px 60px 28px;gap:6px;margin-bottom:8px;align-items:center">
            <SearchableSelect v-model="it.item_code" :options="itemOptions" placeholder="Search item…" @search="fetchItems" @select="opt => onItemSelect(it, opt)" style="font-size:12px"/>
            <input class="nim-input" type="number" v-model="it.qty" placeholder="Qty" min="0.01" style="font-size:12px"/>
            <input class="nim-input" type="number" v-model="it.accepted_qty" placeholder="Accept" min="0" style="font-size:12px"/>
            <input class="nim-input" v-model="it.uom" placeholder="UOM" style="font-size:12px"/>
            <button @click="removeItem(i)" style="background:none;border:none;cursor:pointer;color:#C92A2A;padding:2px" v-html="icon('trash',12)"></button>
          </div>
          <div v-if="!form.items.length" style="font-size:12px;color:#868E96;text-align:center;padding:10px;background:#F8F9FA;border-radius:6px">
            No items yet — click Add Item
          </div>
        </div>
      </div>
      <div style="padding:14px 20px;border-top:1px solid #e5e7eb;display:flex;gap:8px;justify-content:flex-end">
        <button class="b-btn b-btn-ghost" @click="newOpen=false">Cancel</button>
        <button class="b-btn b-btn-primary" @click="saveGRN" :disabled="saving">{{saving?'Saving…':'Save GRN'}}</button>
      </div>
    </div>
  </Teleport>
</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { apiList, apiGET, apiSave, apiSubmit, resolveCompany } from "../api/client.js";
import SearchableSelect from "../components/SearchableSelect.vue";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";
import SummaryStrip from "../components/SummaryStrip.vue";
import Pagination from "../components/Pagination.vue";
import { usePagination } from "../composables/usePagination.js";

const { toast } = useToast();

const TABS = [{k:"all",l:"All"},{k:"0",l:"Draft"},{k:"1",l:"Submitted"},{k:"2",l:"Cancelled"}];
const list      = ref([]);
const loading   = ref(false);
const search    = ref("");
const tab       = ref("all");
const viewOpen  = ref(false);
const viewDoc   = ref(null);
const newOpen   = ref(false);
const saving    = ref(false);
const submitting = ref(false);
const supSugg   = ref([]);
let supTimer    = null;
const vendorOptions = ref([]);
const itemOptions   = ref([]);
const poOptions     = ref([]);

const form = reactive({
  supplier: "", posting_date: new Date().toISOString().slice(0,10),
  purchase_order: "", set_warehouse: "", remarks: "", items: [],
});

const counts = computed(() => ({
  draft:     list.value.filter(r => r.docstatus === 0).length,
  received:  list.value.filter(r => r.docstatus === 1).length,
  cancelled: list.value.filter(r => r.docstatus === 2).length,
}));

function statusLabel(r) {
  if (r.docstatus===2) return "Cancelled";
  if (r.docstatus===1) return "Received";
  return "Draft";
}
function statusClass(r) {
  if (r.docstatus===2) return "b-badge-muted";
  if (r.docstatus===1) return "b-badge-green";
  return "b-badge-orange";
}

async function load() {
  loading.value = true;
  try {
    // No standalone Purchase Receipt doctype in this build. Synthesise the list
    // from Purchase Order lines with received_qty > 0.
    const rows = await apiGET("zoho_books_clone.api.docs.get_purchase_receipt_list", { limit: 500 }) || [];
    const rawList = rows.map(r => ({
      name: r.purchase_order,
      supplier: r.supplier,
      supplier_name: r.supplier_name,
      posting_date: r.expected_delivery_date || r.transaction_date,
      purchase_order: r.purchase_order,
      total_qty: r.qty_received,
      qty_ordered: r.qty_ordered,
      qty_received: r.qty_received,
      qty_billed: r.qty_billed,
      pct_received: r.pct_received,
      status: r.receipt_status,
      docstatus: r.status === "Cancelled" ? 2 : 1,
      grand_total: r.grand_total,
    }));
    list.value = rawList;
    // Resolve missing supplier_name — backend may omit it
    const missing = [...new Set(rawList.filter(r => !r.supplier_name && r.supplier).map(r => r.supplier))];
    if (missing.length) {
      const sups = await apiList("Supplier", { fields: ["name","supplier_name"], filters: [["name","in",missing]], limit: missing.length }).catch(()=>[]);
      const nameMap = Object.fromEntries(sups.map(s => [s.name, s.supplier_name || s.name]));
      list.value = rawList.map(r => r.supplier_name ? r : { ...r, supplier_name: nameMap[r.supplier] || r.supplier });
    }
  } catch (e) { console.warn("Purchase receipt load failed:", e.message); list.value = []; }
  finally { loading.value = false; }
}

const filtered = computed(() => {
  let r = list.value;
  if (tab.value === "1")      r = r.filter(x => x.status === "Fully Received");
  else if (tab.value === "0") r = r.filter(x => x.status === "Partially Received");
  else if (tab.value === "2") r = r.filter(x => x.docstatus === 2);
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    r = r.filter(x => (x.name||"").toLowerCase().includes(q) || (x.supplier_name||"").toLowerCase().includes(q));
  }
  return r;
});

const sorted = computed(() => [...filtered.value].sort((a,b) =>
  (b.posting_date||"").localeCompare(a.posting_date||"")
));
const { page, pageSize, paged } = usePagination(sorted, { storageKey: "purchase-receipts" });

async function openView(r) {
  viewOpen.value = true;
  try {
    const lines = await apiGET("zoho_books_clone.api.docs.get_purchase_receipt_lines", { purchase_order: r.name }) || [];
    viewDoc.value = { ...r, items: lines };
  } catch (e) {
    console.warn("PR lines load failed:", e.message);
    viewDoc.value = r;
  }
}

async function submitGRN() {
  // No standalone Purchase Receipt doctype in this build; receipts are tracked
  // as `received_qty` on the Purchase Order lines. Point the user there.
  if (!viewDoc.value) return;
  toast.info("Receipt status is managed on the Purchase Order — open " + viewDoc.value.name + " in Purchase Orders to mark additional qty received.");
  return;
  // eslint-disable-next-line no-unreachable
  submitting.value = true;
  try {
    await apiSubmit("Purchase Receipt", viewDoc.value.name);
    toast.success("GRN submitted");
    viewOpen.value = false;
    await load();
  } catch (e) { toast.error(e.message || "Submit failed"); }
  finally { submitting.value = false; }
}

function openNew() {
  Object.assign(form, { supplier:"", posting_date: new Date().toISOString().slice(0,10), purchase_order:"", set_warehouse:"", remarks:"", items:[] });
  supSugg.value = [];
  addItem();
  newOpen.value = true;
}

function addItem() { form.items.push({ item_code:"", qty:1, accepted_qty:1, uom:"Nos" }); }
function removeItem(i) { form.items.splice(i, 1); }

async function fetchVendors(q = "") {
  try {
    const filters = [["disabled", "=", 0]];
    if (q) filters.push(["supplier_name", "like", `%${q}%`]);
    const rows = await apiList("Supplier", { fields: ["name", "supplier_name"], filters, limit: 30, order: "supplier_name asc" });
    vendorOptions.value = rows.map(r => ({ label: r.supplier_name || r.name, value: r.name }));
  } catch { vendorOptions.value = []; }
}
function onSupSelect(opt) {
  form.supplier      = opt?.value ?? opt;
  form.supplier_name = opt?.label ?? opt?.value ?? "";
  // Reset PO and reload PO list for the new supplier
  form.purchase_order = "";
  poOptions.value = [];
  fetchPOs("");
}
async function fetchPOs(q = "") {
  try {
    const filters = [["docstatus", "=", "[To Receive,Billed]"]]; // submitted POs only
    if (form.supplier) filters.push(["supplier", "=", form.supplier]);
    if (q) filters.push(["name", "like", `%${q}%`]);
    const rows = await apiList("Purchase Order", {
      fields: ["name", "supplier", "transaction_date", "grand_total"],
      filters, limit: 30, order: "transaction_date desc, creation desc",
    });
    poOptions.value = rows.map(r => ({
      label: `${r.name}  (${r.transaction_date || ""})`,
      value: r.name,
    }));
  } catch { poOptions.value = []; }
}
async function fetchItems(q = "") {
  try {
    const filters = [["disabled", "=", 0], ["has_variants", "=", 0]];
    if (q) filters.push(["item_name", "like", `%${q}%`]);
    const rows = await apiList("Item", { fields: ["name", "item_name", "description", "stock_uom", "standard_rate", "standard_buying_rate"], filters, limit: 30, order: "item_name asc" });
    itemOptions.value = rows.map(r => ({ label: r.item_name || r.name, value: r.name, description: r.description || "", uom: r.stock_uom || "Nos", rate: r.standard_buying_rate || r.standard_rate || 0 }));
  } catch { itemOptions.value = []; }
}
function onItemSelect(line, opt) {
  line.item_code    = opt?.value ?? opt;
  line.item_name    = opt?.label  || opt?.value || "";
  line.description  = opt?.description || "";
  line.uom          = opt?.uom   || line.uom || "Nos";
}

async function saveGRN() {
  if (!form.supplier.trim()) { toast.error("Supplier is required"); return; }
  if (!form.items.length || !form.items[0].item_code) { toast.error("Add at least one item"); return; }
  saving.value = true;
  try {
    const company = await resolveCompany();
    const doc = {
      doctype: "Purchase Receipt",
      supplier: form.supplier,
      posting_date: form.posting_date,
      company,
      purchase_order: form.purchase_order || null,
      set_warehouse: form.set_warehouse || null,
      remarks: form.remarks || "",
      items: form.items.filter(it => it.item_code.trim()).map(it => ({
        doctype: "Purchase Receipt Item",
        item_code: it.item_code,
        item_name: it.item_name || it.item_code,
        qty: parseFloat(it.qty) || 1,
        accepted_qty: parseFloat(it.accepted_qty) || parseFloat(it.qty) || 1,
        rejected_qty: 0,
        uom: it.uom || "Nos",
        stock_uom: it.uom || "Nos",
        conversion_factor: 1,
        received_qty: parseFloat(it.qty) || 1,
        rate: 0,
      })),
    };
    const saved = await apiSave(doc);
    toast.success(`GRN ${saved.name} saved`);
    newOpen.value = false;
    await load();
  } catch (e) { toast.error(e.message || "Failed to save GRN"); }
  finally { saving.value = false; }
}

onMounted(() => { load(); fetchVendors(""); fetchItems(""); fetchPOs(""); });
</script>