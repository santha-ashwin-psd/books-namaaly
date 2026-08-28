<template>
  <div class="ei-page">

    <!-- ── Top Bar ── -->
    <div class="ei-topbar">
      <div>
        <div class="ei-title">e-Invoice</div>
        <div class="ei-sub">IRN generation &amp; management for B2B invoices</div>
      </div>
      <div class="ei-controls">
        <div class="ei-search-wrap">
          <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
          <input v-model="search" placeholder="Search invoice or customer…" class="ei-search-input" />
        </div>
        <div class="ei-tab-pills">
          <button v-for="t in tabs" :key="t.v" class="ei-pill" :class="{active:tab===t.v}" @click="tab=t.v">{{ t.l }}</button>
        </div>
        <input v-model="fromDate" type="date" class="ei-date-in" @change="load" />
        <span style="font-size:11px;color:#9ca3af">to</span>
        <input v-model="toDate" type="date" class="ei-date-in" @change="load" />
        <button class="ei-btn-ghost" @click="load" :disabled="loading"><span v-html="icon('refresh',14)"></span></button>
        <button v-if="irnPending.length" class="ei-btn-outline" @click="generateAllPending" :disabled="bulkGenerating || !$canCreate('accounts')" :title="!$canCreate('accounts') ? 'Read-only access' : ''">
          <span v-if="bulkGenerating" v-html="icon('refresh',13)" style="animation:spin 1s linear infinite;display:inline-flex"></span>
          {{ bulkGenerating ? `Generating ${bulkProgress}/${irnPending.length}…` : `Generate All Pending (${irnPending.length})` }}
        </button>
        <button v-if="sorted.length" class="ei-btn-ghost" @click="exportCSV"><span v-html="icon('download',13)"></span> CSV</button>
      </div>
    </div>

    <!-- ── Summary Strip ── -->
    <div class="ei-sum-strip">
      <div class="ei-sum-card">
        <div class="ei-sum-lbl">Total B2B Invoices</div>
        <div class="ei-sum-val">{{ list.length }}</div>
      </div>
      <div class="ei-sum-card">
        <div class="ei-sum-lbl">IRN Generated</div>
        <div class="ei-sum-val" style="color:#16a34a">{{ irnGenerated.length }}</div>
      </div>
      <div class="ei-sum-card">
        <div class="ei-sum-lbl">Pending IRN</div>
        <div class="ei-sum-val" style="color:#d97706">{{ irnPending.length }}</div>
      </div>
      <div class="ei-sum-card">
        <div class="ei-sum-lbl">Cancelled</div>
        <div class="ei-sum-val" style="color:#dc2626">{{ irnCancelled.length }}</div>
      </div>
    </div>

    <!-- No GSTIN notice -->
    <div v-if="!loading && noGstinWarning" class="ei-notice">
      <span v-html="icon('info',14)"></span>
      No B2B invoices found for this period. e-Invoice applies only when the customer has a GSTIN — set Tax ID on the Customer record.
    </div>

    <!-- ── Table ── -->
    <div class="ei-card">
      <table class="ei-table ei-desktop-table">
        <thead><tr>
          <th @click="sort('name')" class="sortable">Invoice # <span v-html="sortArrow('name')"></span></th>
          <th @click="sort('posting_date')" class="sortable">Date <span v-html="sortArrow('posting_date')"></span></th>
          <th>Customer</th>
          <th>GSTIN</th>
          <th class="ta-r">Invoice Value</th>
          <th>IRN</th>
          <th>Status</th>
        </tr></thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 8" :key="n"><td colspan="7"><div class="ei-shimmer"></div></td></tr>
          </template>
          <template v-else>
            <tr v-for="inv in paginatedSorted" :key="inv.name" class="ei-row" @click="openView(inv)">
              <td><span class="ei-code">{{ inv.name }}</span></td>
              <td class="mono text-muted">{{ fmtDate(inv.posting_date) }}</td>
              <td class="fw500">{{ inv.customer_name || inv.customer }}</td>
              <td class="mono text-muted" style="font-size:11.5px">{{ inv.customer_gstin || '—' }}</td>
              <td class="ta-r mono fw600">{{ fmtCur(inv.grand_total) }}</td>
              <td>
                <span v-if="inv.irn && inv.einvoice_status !== 'Cancelled'" class="ei-irn-chip" :title="inv.irn">{{ inv.irn.slice(0,14) }}…</span>
                <span v-else-if="inv.einvoice_status === 'Cancelled'" class="text-muted" style="font-size:11.5px">Cancelled</span>
                <span v-else class="text-muted" style="font-size:11.5px">—</span>
              </td>
              <td><span class="ei-badge" :class="statusClass(inv)">{{ statusLabel(inv) }}</span></td>
            </tr>
            <tr v-if="!sorted.length">
              <td colspan="7" class="ei-empty">
                <div class="ei-empty-wrap">
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" stroke-width="1.3"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>
                  <div>No e-invoices match this filter</div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>

      <!-- Mobile cards (shown at ≤768px) -->
      <div class="ei-mobile-cards">
        <template v-if="loading">
          <div v-for="n in 6" :key="n" class="ei-mobile-card ei-mc--skeleton">
            <div class="ei-mc-shimmer" style="height:13px;width:55%;margin-bottom:8px"></div>
            <div class="ei-mc-shimmer" style="height:11px;width:40%;margin-bottom:6px"></div>
            <div class="ei-mc-shimmer" style="height:11px;width:65%"></div>
          </div>
        </template>
        <div v-else-if="!sorted.length" class="ei-mc-empty">
          <div style="font-size:32px;margin-bottom:8px">🧾</div>
          <div>No e-invoices match this filter</div>
        </div>
        <template v-else>
          <div v-for="inv in paginatedSorted" :key="inv.name" class="ei-mobile-card" @click="openView(inv)">
            <div class="ei-mc-top">
              <span class="ei-mc-docno">{{ inv.name }}</span>
              <span class="ei-badge" :class="statusClass(inv)">{{ statusLabel(inv) }}</span>
            </div>
            <div class="ei-mc-mid">{{ inv.customer_name || inv.customer }}</div>
            <div class="ei-mc-meta">
              <span>{{ fmtDate(inv.posting_date) }}</span>
              <span class="ei-mc-amount">{{ fmtCur(inv.grand_total) }}</span>
            </div>
          </div>
        </template>
      </div>

      <!-- Load More -->
      <div v-if="!loading && hasMore" class="ei-load-more-wrap">
        <button class="ei-btn-ghost ei-load-more-btn" @click="loadMore">
          Load More ({{ sorted.length - visibleCount }} remaining)
        </button>
      </div>
    </div>

    <!-- ── View Drawer ── -->
    <Teleport to="body">
      <div v-if="viewing" class="ei-overlay" @click.self="closeView"></div>
      <div class="ei-panel" :class="{open: !!viewing}">
        <template v-if="viewing">

          <!-- Gradient header -->
          <div class="ei-panel-hdr" :style="headerGrad(viewing)">
            <div style="flex:1;min-width:0">
              <div class="ei-panel-num">{{ viewing.name }}</div>
              <div class="ei-panel-cust">{{ viewing.customer_name || viewing.customer }}</div>
              <div style="margin-top:8px"><span class="ei-badge" :class="statusClass(viewing)" style="font-size:12px;padding:3px 10px">{{ statusLabel(viewing) }}</span></div>
            </div>
            <button class="ei-close-btn" @click="closeView"><span v-html="icon('x',16)"></span></button>
          </div>

          <!-- Meta 3-col -->
          <div class="ei-meta-row">
            <div class="ei-meta-card">
              <div class="ei-meta-lbl">Date</div>
              <div class="ei-meta-val">{{ fmtDate(viewing.posting_date) }}</div>
            </div>
            <div class="ei-meta-card">
              <div class="ei-meta-lbl">Invoice Value</div>
              <div class="ei-meta-val" style="color:#2563eb">{{ fmtCur(viewing.grand_total) }}</div>
            </div>
            <div class="ei-meta-card">
              <div class="ei-meta-lbl">Status</div>
              <div class="ei-meta-val">{{ statusLabel(viewing) }}</div>
            </div>
          </div>

          <!-- GSTIN block -->
          <div class="ei-gstin-blk">
            <div v-if="!companyGstin" class="ei-company-gstin-warn">
              <span style="flex-shrink:0;font-size:15px">⚠️</span>
              <div>
                <div style="font-weight:700;margin-bottom:1px">Company GSTIN not configured</div>
                <div>Set your company's GSTIN under <strong>Books Company → GSTIN</strong> to enable IRN generation.</div>
              </div>
            </div>
            <div class="ei-gstin-row">
              <span class="ei-gstin-lbl">Customer GSTIN</span>
              <span v-if="viewing.customer_gstin" class="ei-gstin-val">{{ viewing.customer_gstin }}</span>
              <span v-else style="color:#ef4444;font-size:12px;font-weight:600">Not set — add Tax ID on Customer</span>
            </div>
            <div v-if="companyGstin" class="ei-gstin-row" style="border-bottom:none">
              <span class="ei-gstin-lbl">Company GSTIN</span>
              <span class="ei-gstin-val">{{ companyGstin }}</span>
            </div>
          </div>

          <!-- Body -->
          <div class="ei-panel-body">

            <!-- No GSTIN warning -->
            <div v-if="!viewing.customer_gstin" class="ei-warn-blk">
              <span v-html="icon('info',14)" style="flex-shrink:0;margin-top:1px"></span>
              Add Tax ID (GSTIN) on the Customer record to enable IRN generation for this invoice.
            </div>

            <!-- IRN details -->
            <template v-if="viewing.irn">
              <div class="ei-sec-hdr">IRN Details</div>
              <div class="ei-irn-blk">
                <div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:10px">
                  <div class="ei-irn-text">{{ viewing.irn }}</div>
                  <button class="ei-copy-btn" @click="copyIRN" :title="copied?'Copied!':'Copy IRN'">
                    <span v-html="icon(copied?'check':'copy',13)"></span>
                  </button>
                </div>
                <div class="ei-ack-row">
                  <div>
                    <div class="ei-meta-lbl">Ack No.</div>
                    <div class="ei-ack-val">{{ viewing.ack_no || '—' }}</div>
                  </div>
                  <div>
                    <div class="ei-meta-lbl">Ack Date</div>
                    <div class="ei-ack-val">{{ fmtDate(viewing.ack_date) || '—' }}</div>
                  </div>
                </div>
              </div>

              <!-- QR Code -->
              <div v-if="viewing.einvoice_status !== 'Cancelled'" class="ei-qr-wrap">
                <div class="ei-qr-label">QR Code</div>
                <div class="ei-qr-box">
                  <IrnQrCode :irn="viewing.irn" :size="qrSize" class="ei-qr-img" />
                </div>
              </div>
            </template>

            <!-- Pending placeholder -->
            <div v-else-if="!viewing.irn && viewing.customer_gstin" class="ei-pending-ph">
              <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" stroke-width="1.3"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>
              <div style="font-size:13px;font-weight:600;color:#374151">No IRN generated yet</div>
              <div style="font-size:12px;color:#9ca3af;margin-top:2px">Click "Generate IRN" below to create one</div>
            </div>

            <!-- Manual form -->
            <div v-if="showManualForm" class="ei-manual-card">
              <div class="ei-sec-hdr" style="margin-top:0;margin-bottom:10px">Enter IRN Manually</div>
              <label class="ei-lbl">IRN (64-char hex) <span style="color:#ef4444">*</span></label>
              <input v-model="manualForm.irn" class="ei-fi" placeholder="64-character hex string from NIC portal" maxlength="64" />
              <label class="ei-lbl" style="margin-top:10px">Ack No. <span style="color:#ef4444">*</span></label>
              <input v-model="manualForm.ack_no" class="ei-fi" placeholder="Acknowledgement number" />
              <label class="ei-lbl" style="margin-top:10px">Ack Date</label>
              <input v-model="manualForm.ack_date" type="date" class="ei-fi" />
              <div style="display:flex;gap:8px;margin-top:14px">
                <button class="ei-btn-ghost" style="flex:1" @click="showManualForm=false">Cancel</button>
                <button class="ei-btn-primary" style="flex:1" :disabled="manualSaving || !$canCreate('accounts')" :title="!$canCreate('accounts') ? 'Read-only access' : ''" @click="saveManualIRN">
                  {{ manualSaving ? 'Saving…' : 'Save IRN' }}
                </button>
              </div>
            </div>

          </div>

          <!-- Footer -->
          <div class="ei-panel-footer">
            <button class="ei-btn-ghost" @click="closeView">Close</button>
            <template v-if="viewing.einvoice_status !== 'Cancelled'">
              <button v-if="!viewing.irn && viewing.customer_gstin && !showManualForm"
                class="ei-btn-outline"
                :disabled="!companyGstin || !$canCreate('accounts')"
                :title="!companyGstin ? 'Company GSTIN not configured. Set it under Books Company → GSTIN.' : (!$canCreate('accounts') ? 'Read-only access' : '')"
                @click="showManualForm=true">Enter Manually</button>
              <button v-if="!viewing.irn && viewing.customer_gstin"
                class="ei-btn-primary"
                :disabled="generating || !companyGstin || !$canCreate('accounts')"
                :title="!companyGstin ? 'Company GSTIN not configured. Set it under Books Company → GSTIN.' : (!$canCreate('accounts') ? 'Read-only access' : '')"
                @click="doGenerateIRN(viewing)">
                <span v-if="generating" v-html="icon('refresh',13)" style="animation:spin 1s linear infinite;display:inline-flex"></span>
                {{ generating ? 'Generating…' : 'Generate IRN' }}
              </button>
              <button v-if="viewing.irn" class="ei-btn-danger" :disabled="cancelling || !$canDelete('accounts')" :title="!$canDelete('accounts') ? 'Not permitted' : ''" @click="doCancelIRN(viewing)">
                {{ cancelling ? 'Cancelling…' : 'Cancel IRN' }}
              </button>
            </template>
          </div>

        </template>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { apiList, apiPOST, resolveCompany, apiGET } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";
import { flt, fmtDate } from "../utils/format.js";
import IrnQrCode from "../components/IrnQrCode.vue";

const { toast } = useToast();
const list         = ref([]);
const loading      = ref(false);
const search       = ref("");
const tab          = ref("all");
const sortCol      = ref("posting_date");
const sortDir      = ref("desc");
const viewing      = ref(null);
const noGstinWarning = ref(false);
const companyGstin   = ref("");
const copied       = ref(false);

const now = new Date();
const fromDate = ref(`${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,"0")}-01`);
const toDate   = ref(new Date(now.getFullYear(), now.getMonth()+1, 0).toISOString().slice(0,10));

const generating     = ref(false);
const cancelling     = ref(false);
const bulkGenerating = ref(false);
const bulkProgress   = ref(0);
const showManualForm = ref(false);
const manualSaving   = ref(false);
const manualForm     = ref({ irn: "", ack_no: "", ack_date: "" });

const qrSize = computed(() => window.innerWidth <= 480 ? Math.min(window.innerWidth - 80, 220) : 200);

const PAGE_SIZE = 10;
const visibleCount = ref(PAGE_SIZE);
const paginatedSorted = computed(() => sorted.value.slice(0, visibleCount.value));
const hasMore = computed(() => visibleCount.value < sorted.value.length);
function loadMore() { visibleCount.value += PAGE_SIZE; }

// Reset pagination when filters change
watch([search, tab, fromDate, toDate], () => { visibleCount.value = PAGE_SIZE; });

const tabs = [
  { v:"all",       l:"All" },
  { v:"generated", l:"IRN Generated" },
  { v:"pending",   l:"Pending" },
  { v:"cancelled", l:"Cancelled" },
];

async function load() {
  loading.value = true;
  noGstinWarning.value = false;
  try {
    const co = await resolveCompany();
    try {
      const cd = await apiGET("zoho_books_clone.api.docs.get_doc", { doctype:"Books Company", name:co });
      companyGstin.value = cd?.gstin || "";
    } catch { companyGstin.value = ""; }

    const filters = [
      ["company","=",co],["docstatus","=",1],["is_return","=",0],["customer_gstin","!=",""],
    ];
    if (fromDate.value) filters.push(["posting_date",">=",fromDate.value]);
    if (toDate.value)   filters.push(["posting_date","<=",toDate.value]);

    const rows = await apiList("Sales Invoice", {
      fields:["name","posting_date","customer","customer_name","customer_gstin",
              "grand_total","irn","einvoice_status","ack_no","ack_date"],
      filters, limit:500, order: "posting_date desc, creation desc",
    });
    list.value = (rows||[]).filter(i=>i.customer_gstin);
    if (!list.value.length) noGstinWarning.value = true;
  } catch (e) { toast.error(e.message||"Failed to load"); }
  finally { loading.value = false; }
}

function statusLabel(inv) {
  if (inv.einvoice_status === "Cancelled") return "Cancelled";
  if (inv.irn) return "IRN Generated";
  return "Pending IRN";
}
function statusClass(inv) {
  if (inv.einvoice_status === "Cancelled") return "badge-grey";
  if (inv.irn) return "badge-green";
  return "badge-orange";
}
function headerGrad(inv) {
  if (inv.einvoice_status === "Cancelled") return "background:linear-gradient(135deg,#6b7280,#4b5563)";
  if (inv.irn) return "background:linear-gradient(135deg,#16a34a,#15803d)";
  return "background:linear-gradient(135deg,#d97706,#b45309)";
}

const irnGenerated = computed(() => list.value.filter(i=>i.irn && i.einvoice_status!=="Cancelled"));
const irnPending   = computed(() => list.value.filter(i=>!i.irn));
const irnCancelled = computed(() => list.value.filter(i=>i.einvoice_status==="Cancelled"));

const filtered = computed(() => {
  let r = list.value;
  if (tab.value==="generated") r = irnGenerated.value;
  else if (tab.value==="pending")   r = irnPending.value;
  else if (tab.value==="cancelled") r = irnCancelled.value;
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    r = r.filter(i=>(i.name||"").toLowerCase().includes(q)||(i.customer_name||"").toLowerCase().includes(q));
  }
  return r;
});

const sorted = computed(() => {
  const col = sortCol.value;
  return [...filtered.value].sort((a,b) => {
    const c = String(a[col]??"").localeCompare(String(b[col]??""));
    return sortDir.value==="asc"?c:-c;
  });
});
function sort(col) { if(sortCol.value===col) sortDir.value=sortDir.value==="asc"?"desc":"asc"; else{sortCol.value=col;sortDir.value="asc";} }
function sortArrow(col) { if(sortCol.value!==col) return '<span style="color:#d1d5db">⇅</span>'; return sortDir.value==="asc"?"↑":"↓"; }

function openView(inv) {
  viewing.value = {...inv};
  showManualForm.value = false;
  manualForm.value = { irn:"", ack_no:"", ack_date:new Date().toISOString().slice(0,10) };
}
function closeView() { viewing.value = null; }

function patchViewing(fields) {
  if (viewing.value) viewing.value = {...viewing.value, ...fields};
  const idx = list.value.findIndex(i=>i.name===viewing.value?.name);
  if (idx>=0) list.value[idx] = {...list.value[idx], ...fields};
}

async function doGenerateIRN(inv) {
  generating.value = true;
  try {
    const res = await apiPOST("zoho_books_clone.api.gst.generate_irn", { invoice_name:inv.name });
    patchViewing(res);
    toast.success("IRN generated successfully");
  } catch (e) { toast.error(e.message||"Failed to generate IRN"); }
  finally { generating.value = false; }
}

async function doCancelIRN(inv) {
  cancelling.value = true;
  try {
    await apiPOST("zoho_books_clone.api.gst.cancel_irn", { invoice_name:inv.name });
    patchViewing({ einvoice_status:"Cancelled" });
    toast.success("IRN cancelled");
  } catch (e) { toast.error(e.message||"Failed to cancel IRN"); }
  finally { cancelling.value = false; }
}

async function saveManualIRN() {
  if (!manualForm.value.irn || manualForm.value.irn.length!==64) return toast.error("IRN must be exactly 64 characters");
  if (!manualForm.value.ack_no) return toast.error("Ack No. is required");
  manualSaving.value = true;
  try {
    const res = await apiPOST("zoho_books_clone.api.gst.save_irn_manual", {
      invoice_name:viewing.value.name, irn:manualForm.value.irn,
      ack_no:manualForm.value.ack_no, ack_date:manualForm.value.ack_date,
    });
    patchViewing(res);
    showManualForm.value = false;
    toast.success("IRN saved");
  } catch (e) { toast.error(e.message||"Failed to save IRN"); }
  finally { manualSaving.value = false; }
}

async function generateAllPending() {
  bulkGenerating.value = true; bulkProgress.value = 0;
  const pending = irnPending.value.filter(i=>i.customer_gstin);
  for (const inv of pending) {
    try {
      const res = await apiPOST("zoho_books_clone.api.gst.generate_irn", { invoice_name:inv.name });
      const idx = list.value.findIndex(i=>i.name===inv.name);
      if (idx>=0) list.value[idx] = {...list.value[idx], ...res};
    } catch {}
    bulkProgress.value++;
  }
  bulkGenerating.value = false;
  toast.success(`Generated IRN for ${pending.length} invoice(s)`);
}

async function copyIRN() {
  if (!viewing.value?.irn) return;
  try { await navigator.clipboard.writeText(viewing.value.irn); copied.value=true; setTimeout(()=>{copied.value=false;},1800); }
  catch { toast.error("Copy failed"); }
}

function exportCSV() {
  const rows=[["Invoice #","Date","Customer","GSTIN","Invoice Value","IRN","Status","Ack No.","Ack Date"],
    ...sorted.value.map(i=>[i.name,i.posting_date,i.customer_name||i.customer,i.customer_gstin||"",flt(i.grand_total),i.irn||"",statusLabel(i),i.ack_no||"",i.ack_date||""])];
  const csv=rows.map(r=>r.map(v=>`"${String(v??"").replace(/"/g,'""')}"`).join(",")).join("\n");
  const a=document.createElement("a");a.href="data:text/csv;charset=utf-8,"+encodeURIComponent(csv);
  a.download=`eInvoice_${fromDate.value}_to_${toDate.value}.csv`;a.click();
}

function fmtCur(v) { return new Intl.NumberFormat("en-IN",{style:"currency",currency:"OMR",minimumFractionDigits:2}).format(flt(v)); }

onMounted(load);
</script>

<style scoped>
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }

/* ── Layout ── */
.ei-page { display:flex; flex-direction:column; gap:18px; padding:24px; background:#f8fafc; min-height:100%; }

/* ── Top Bar ── */
.ei-topbar { display:flex; align-items:flex-start; justify-content:space-between; flex-wrap:wrap; gap:12px; background:#fff; border:1px solid #e5e7eb; border-radius:12px; padding:18px 22px; box-shadow:0 1px 3px rgba(0,0,0,.04); }
.ei-title { font-size:17px; font-weight:700; color:#0f172a; letter-spacing:-0.3px; }
.ei-sub { font-size:11.5px; color:#94a3b8; margin-top:2px; }
.ei-controls { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
.ei-search-wrap { display:flex; align-items:center; gap:8px; background:#f8fafc; border:1px solid #e5e7eb; border-radius:8px; padding:6px 12px; min-width:200px; transition:border-color .15s; }
.ei-search-wrap:focus-within { border-color:#6366f1; background:#fff; }
.ei-search-input { border:none; background:transparent; outline:none; font:inherit; color:#111827; width:100%; font-size:13px; }
.ei-tab-pills { display:flex; gap:2px; background:#f3f4f6; border-radius:8px; padding:3px; }
.ei-pill { border:none; background:transparent; border-radius:6px; padding:5px 12px; font-size:12px; font-weight:600; color:#6b7280; cursor:pointer; font-family:inherit; transition:all .15s; white-space:nowrap; }
.ei-pill.active { background:#fff; color:#4f46e5; box-shadow:0 1px 3px rgba(0,0,0,.08); }
.ei-date-in { border:1px solid #e5e7eb; border-radius:7px; padding:6px 10px; font:inherit; font-size:12.5px; outline:none; color:#374151; background:#fff; transition:border-color .15s; }
.ei-date-in:focus { border-color:#6366f1; }

/* ── Buttons ── */
.ei-btn-primary { display:inline-flex; align-items:center; gap:6px; background:#4f46e5; color:#fff; border:none; border-radius:8px; padding:8px 14px; font-size:13px; font-weight:600; cursor:pointer; font-family:inherit; transition:background .15s; }
.ei-btn-primary:hover { background:#4338ca; }
.ei-btn-primary:disabled { opacity:.6; cursor:not-allowed; }
.ei-btn-ghost { display:inline-flex; align-items:center; gap:6px; background:#fff; border:1px solid #e5e7eb; border-radius:8px; padding:8px 12px; font-size:13px; color:#374151; cursor:pointer; font-family:inherit; font-weight:500; transition:all .15s; }
.ei-btn-ghost:hover:not(:disabled) { background:#f8fafc; border-color:#cbd5e1; }
.ei-btn-ghost:disabled { opacity:.5; cursor:not-allowed; }
.ei-btn-outline { display:inline-flex; align-items:center; gap:6px; background:#fff; border:1.5px solid #4f46e5; border-radius:8px; padding:7px 13px; font-size:13px; color:#4f46e5; font-weight:600; cursor:pointer; font-family:inherit; transition:all .15s; }
.ei-btn-outline:hover:not(:disabled) { background:#eef2ff; }
.ei-btn-outline:disabled { opacity:.5; cursor:not-allowed; }
.ei-btn-danger { display:inline-flex; align-items:center; gap:6px; background:#fff; border:1.5px solid #dc2626; border-radius:8px; padding:7px 13px; font-size:13px; color:#dc2626; font-weight:600; cursor:pointer; font-family:inherit; transition:all .15s; }
.ei-btn-danger:hover:not(:disabled) { background:#fef2f2; }
.ei-btn-danger:disabled { opacity:.6; cursor:not-allowed; }

/* ── Summary Strip ── */
.ei-sum-strip { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }
.ei-sum-card { background:#fff; border:1px solid #e5e7eb; border-radius:10px; padding:14px 16px; }
.ei-sum-lbl { font-size:11px; color:#6b7280; text-transform:uppercase; letter-spacing:.05em; margin-bottom:4px; }
.ei-sum-val { font-size:18px; font-weight:700; color:#111827; }

/* ── Notice ── */
.ei-notice { background:#fffbeb; border:1px solid #fde68a; border-radius:10px; padding:12px 16px; font-size:12.5px; color:#92400e; display:flex; align-items:center; gap:8px; font-weight:500; }

/* ── Table Card ── */
.ei-card { background:#fff; border:1px solid #e5e7eb; border-radius:12px; overflow:hidden; box-shadow:0 1px 3px rgba(0,0,0,.04); }
.ei-table { width:100%; border-collapse:collapse; font-size:13px; }
.ei-table thead tr { background:#f8fafc; }
.ei-table th { border-bottom:1px solid #e5e7eb; padding:10px 14px; font-size:10.5px; font-weight:700; color:#94a3b8; text-align:left; white-space:nowrap; text-transform:uppercase; letter-spacing:.05em; }
.ei-table th.sortable { cursor:pointer; user-select:none; }
.ei-table th.sortable:hover { color:#4f46e5; }
.ta-r { text-align:right !important; }
.ei-row td { padding:11px 14px; border-bottom:1px solid #f3f4f6; vertical-align:middle; cursor:pointer; }
.ei-row:last-child td { border-bottom:none; }
.ei-row:hover td { background:#f8fafc; }
.ei-code { font-size:12.5px; color:#4f46e5; font-weight:700; }
.ei-irn-chip { font-size:11px; background:#f0fdf4; color:#15803d; border:1px solid #bbf7d0; padding:2px 8px; border-radius:6px; font-weight:600; }
.mono { font-size:13px; font-variant-numeric:tabular-nums; }
.fw500 { font-weight:500; }
.fw600 { font-weight:600; }
.text-muted { color:#94a3b8; }
.ei-badge { display:inline-flex; align-items:center; padding:3px 9px; border-radius:10px; font-size:11.5px; font-weight:600; }
.badge-green  { background:#dcfce7; color:#16a34a; }
.badge-orange { background:#fff7ed; color:#ea580c; }
.badge-grey   { background:#f3f4f6; color:#6b7280; }
.ei-empty { text-align:center; padding:48px !important; cursor:default !important; }
.ei-empty-wrap { display:flex; flex-direction:column; align-items:center; gap:8px; color:#9ca3af; font-size:13px; }
.ei-shimmer { height:14px; background:linear-gradient(90deg,#f1f5f9 25%,#e2e8f0 50%,#f1f5f9 75%); border-radius:4px; animation:shimmer 1.4s infinite; background-size:200% 100%; }

/* ── Panel/Drawer ── */
.ei-overlay { position:fixed; inset:0; background:rgba(15,23,42,.35); backdrop-filter:blur(2px); z-index:1000; }
.ei-panel { position:fixed; top:0; right:-520px; width:500px; height:100vh; background:#fff; z-index:1001; display:flex; flex-direction:column; box-shadow:-8px 0 32px rgba(15,23,42,.12); transition:right .24s cubic-bezier(.32,.72,0,1); }
.ei-panel.open { right:0; }
.ei-panel-hdr { display:flex; align-items:flex-start; justify-content:space-between; padding:16px 20px 14px; flex-shrink:0; }
.ei-panel-num { font-size:17px; font-weight:800; color:#fff; letter-spacing:-0.3px; }
.ei-panel-cust { font-size:12.5px; color:rgba(255,255,255,.8); margin-top:3px; }
.ei-close-btn { background:rgba(255,255,255,.18); border:none; border-radius:8px; width:32px; height:32px; display:flex; align-items:center; justify-content:center; cursor:pointer; color:#fff; flex-shrink:0; transition:background .15s; }
.ei-close-btn:hover { background:rgba(255,255,255,.3); }

/* Meta row */
.ei-meta-row { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; padding:10px 20px 0; flex-shrink:0; }
.ei-meta-card { background:#f8f9fc; border:1px solid #e8ecf0; border-radius:8px; padding:10px 12px; }
.ei-meta-lbl { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:#94a3b8; }
.ei-meta-val { font-size:13px; font-weight:600; color:#0f172a; margin-top:3px; }

/* GSTIN block */
.ei-gstin-blk { padding:8px 20px 0; flex-shrink:0; }
.ei-gstin-row { display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px solid #f3f4f6; }
.ei-gstin-lbl { font-size:12px; color:#6b7280; }
.ei-gstin-val { font-size:12px; color:#374151; font-weight:600; font-variant-numeric:tabular-nums; }
.ei-company-gstin-warn { display:flex; align-items:flex-start; gap:10px; background:#fef2f2; border:1px solid #fecaca; border-radius:8px; padding:10px 12px; font-size:12px; color:#991b1b; line-height:1.5; margin-bottom:8px; }

/* Panel body */
.ei-panel-body { flex:1; overflow-y:auto; padding:10px 20px; display:flex; flex-direction:column; gap:0; background:#f8fafc; }
.ei-panel-footer { padding:14px 20px; border-top:1px solid #e5e7eb; display:flex; gap:8px; justify-content:flex-end; flex-shrink:0; background:#fff; }

/* IRN block */
.ei-sec-hdr { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; color:#6b7280; margin-top:10px; margin-bottom:6px; }
.ei-irn-blk { background:#eef2ff; border:1px solid #c7d2fe; border-radius:8px; padding:12px 14px; }
.ei-irn-text { font-size:11px; color:#3730a3; word-break:break-all; line-height:1.7; flex:1; font-variant-numeric:tabular-nums; }
.ei-copy-btn { background:none; border:1px solid #c7d2fe; border-radius:6px; padding:4px 7px; cursor:pointer; color:#4f46e5; flex-shrink:0; display:flex; align-items:center; }
.ei-copy-btn:hover { background:#e0e7ff; }
.ei-ack-row { display:grid; grid-template-columns:1fr 1fr; gap:8px; border-top:1px solid #c7d2fe; padding-top:10px; margin-top:0; }
.ei-ack-val { font-size:12px; font-weight:600; color:#1e1b4b; margin-top:3px; word-break:break-all; }

/* QR */
.ei-qr-wrap { display:flex; align-items:center; gap:12px; margin-top:10px; background:#fff; border:1px solid #e5e7eb; border-radius:10px; padding:12px 14px; box-shadow:0 1px 4px rgba(0,0,0,.06); width:100%; box-sizing:border-box; }
.ei-qr-label { font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; color:#6b7280; flex-shrink:0; writing-mode:vertical-rl; text-orientation:mixed; transform:rotate(180deg); }
.ei-qr-box { flex:1; display:flex; align-items:center; justify-content:center; }
.ei-qr-img { display:block; width:100%; height:auto; max-width:200px; }

/* Pending placeholder */
.ei-pending-ph { display:flex; flex-direction:column; align-items:center; gap:8px; padding:32px 0; color:#9ca3af; text-align:center; }

/* Warn block */
.ei-warn-blk { background:#fffbeb; border:1px solid #fde68a; border-radius:8px; padding:12px 14px; font-size:12.5px; color:#92400e; display:flex; align-items:flex-start; gap:8px; line-height:1.5; margin-top:8px; }

/* Manual form */
.ei-manual-card { background:#fff; border:1px solid #e5e7eb; border-radius:10px; padding:16px; margin-top:16px; }
.ei-lbl { font-size:11.5px; font-weight:600; color:#374151; display:block; margin-bottom:4px; }
.ei-fi { width:100%; border:1px solid #e5e7eb; border-radius:7px; padding:8px 10px; font:inherit; font-size:13px; outline:none; color:#111827; background:#fff; box-sizing:border-box; transition:border-color .15s; }
.ei-fi:focus { border-color:#4f46e5; box-shadow:0 0 0 3px rgba(79,70,229,.1); }

/* ── Load More ── */
.ei-load-more-wrap { display:flex; justify-content:center; padding:14px 16px; border-top:1px solid #f3f4f6; }
.ei-load-more-btn  { width:100%; max-width:320px; justify-content:center; font-weight:600; color:#4f46e5; border-color:#c7d2fe; }
.ei-load-more-btn:hover { background:#eef2ff; border-color:#a5b4fc; }

/* ── Mobile card defaults ── */
.ei-mobile-cards { display: none; }
.ei-desktop-table { display: table; }

@media (max-width: 768px) {
  .ei-panel { width: 100% !important; right: -100% !important; }
  .ei-panel.open { right: 0 !important; }
  .ei-sum-strip { grid-template-columns: repeat(2, 1fr); }
  .ei-search-wrap { min-width: 0; flex: 1 1 auto; }
  .ei-desktop-table { display: none !important; }
  .ei-mobile-cards { display: flex; flex-direction: column; gap: 0; background: #f8fafc; }
  .ei-mobile-card { background: #fff; border-bottom: 1px solid #e5e7eb; padding: 12px 14px; cursor: pointer; transition: background .12s; }
  .ei-mobile-card:active { background: #f8f9fc; }
  .ei-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .ei-mc-docno { font-size: 12px; font-weight: 700; color: #4f46e5; }
  .ei-mc-mid { font-size: 13.5px; font-weight: 600; color: #1a1d23; margin-bottom: 4px; }
  .ei-mc-meta { display: flex; justify-content: space-between; font-size: 12px; color: #868e96; }
  .ei-mc-amount { font-weight: 700; color: #1a1d23; }
  .ei-mc--skeleton { pointer-events: none; }
  .ei-mc-shimmer { border-radius: 6px; background: linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size: 200% 100%; animation: ei-mc-sh 1.4s infinite; }
  @keyframes ei-mc-sh { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
  .ei-mc-empty { text-align: center; padding: 32px 16px; color: #868e96; font-size: 13px; }

  /* Drawer / Panel mobile fixes */
  .ei-panel-body { padding: 10px 14px; }
  .ei-gstin-blk  { padding: 6px 14px 0; }
  .ei-meta-row   { padding: 8px 14px 0; gap: 6px; }
  .ei-panel-hdr  { padding: 14px 14px 12px; }
  .ei-panel-footer { padding: 10px 14px; gap: 8px; }
  .ei-panel-footer .ei-btn-ghost,
  .ei-panel-footer .ei-btn-primary,
  .ei-panel-footer .ei-btn-danger,
  .ei-panel-footer .ei-btn-outline { flex: 1; justify-content: center; }

  /* QR on mobile — stack vertically */
  .ei-qr-wrap { flex-direction: column; align-items: center; padding: 12px; }
  .ei-qr-label { writing-mode: horizontal-tb; transform: none; }
  .ei-qr-box { flex: unset; }
  .ei-qr-img { max-width: min(240px, 70vw); }

  /* GSTIN values may be long — allow wrapping */
  .ei-gstin-row { flex-wrap: wrap; gap: 4px; }
  .ei-gstin-val { font-size: 11.5px; word-break: break-all; text-align: right; }
}
@media (max-width: 480px) {
  .ei-page   { padding: 12px; gap: 12px; }
  .ei-topbar { padding: 12px 14px; }
  .ei-meta-row { grid-template-columns: 1fr 1fr !important; }
  .ei-qr-img { max-width: min(200px, 65vw); }
  .ei-panel-body{overflow:visible}
  .ei-panel{
    overflow:scroll
  }
}
</style>