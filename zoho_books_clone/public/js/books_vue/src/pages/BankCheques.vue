<template>
  <div class="chq-page">
    <div class="chq-actions">
      <div class="chq-search-wrap"><span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span><input v-model="search" placeholder="Search cheques…" class="chq-search-input" /></div>
      <div style="display:flex;gap:8px;margin-left:auto"><button class="chq-btn-ghost" @click="load"><span v-html="icon('refresh',14)"></span></button></div>
    </div>

    <SummaryStrip v-if="!loading" :cards="[
      { label: 'Total', tone: 'default', value: list.length, sub: fmtCur(totalAmount) },
      { label: 'Issued', tone: 'accent', value: summary.issued.count, valueClass: 'blue', sub: fmtCur(summary.issued.total) },
      { label: 'Cleared', tone: 'success', value: summary.cleared.count, valueClass: 'green', sub: fmtCur(summary.cleared.total) },
      { label: 'Bounced', tone: summary.bounced.count>0?'danger':'default', value: summary.bounced.count, valueClass: summary.bounced.count>0?'red':'', sub: fmtCur(summary.bounced.total) },
    ]" />

    <!-- Filter toolbar -->
    <div v-if="!loading && list.length" class="chq-toolbar">
      <div class="chq-filter-pills">
        <button v-for="t in tabs" :key="t.key" class="chq-fpill" :class="{active:activeTab===t.key}" @click="activeTab=t.key">
          {{ t.label }} <span class="chq-fpill-count">{{ tabCount(t.key) }}</span>
        </button>
      </div>
      <div class="chq-toolbar-right">
        <span class="chq-result">{{ sorted.length }} of {{ list.length }}</span>
        <button class="chq-btn-ghost" @click="exportCSV" :disabled="!sorted.length"><span v-html="icon('download',14)"></span> Export</button>
      </div>
    </div>

    <!-- Selection bar -->
    <div v-if="selected.size>0" class="chq-selbar">
      <span class="chq-sel-count">{{ selected.size }} selected</span>
      <button class="chq-sel-export" @click="exportCSV"><span v-html="icon('download',13)"></span> Export selected</button>
      <button v-if="selectedIssued.length" class="chq-sel-ok" @click="bulkClear" :disabled="bulkBusy">
        <span v-html="icon('check',13)"></span> Mark {{ selectedIssued.length }} Cleared
      </button>
      <div style="flex:1"></div>
      <button class="chq-sel-clear" @click="selected=new Set()">Clear</button>
    </div>

    <div class="chq-card">
      <table class="chq-table chq-desktop-table">
        <thead><tr>
          <th style="width:32px"><input type="checkbox" :checked="allSelected" @change="toggleSelectAll" /></th>
          <th @click="sort('name')" class="sortable">Payment # <span v-html="sortArrow('name')"></span></th>
          <th @click="sort('party')" class="sortable">Party <span v-html="sortArrow('party')"></span></th>
          <th @click="sort('reference_no')" class="sortable">Cheque No <span v-html="sortArrow('reference_no')"></span></th>
          <th @click="sort('payment_date')" class="sortable">Date <span v-html="sortArrow('payment_date')"></span></th>
          <th>Type</th>
          <th>Status</th>
          <th @click="sort('paid_amount')" class="sortable ta-r">Amount <span v-html="sortArrow('paid_amount')"></span></th>
        </tr></thead>
        <tbody>
          <template v-if="loading"><tr v-for="n in 6" :key="n"><td colspan="8"><div class="chq-shimmer"></div></td></tr></template>
          <template v-else>
            <tr v-for="p in paged" :key="p.name" class="chq-row" @click="openView(p)">
              <td @click.stop><input type="checkbox" :checked="selected.has(p.name)" @change="toggleSelect(p.name)" /></td>
              <td><DocLink doctype="Payment Entry" :name="p.name" /></td>
              <td>{{ p.party_name||p.party||'—' }}</td>
              <td class="mono-sm text-muted">{{ p.reference_no||'—' }}</td>
              <td class="mono-sm text-muted">{{ fmtDate(p.payment_date) }}</td>
              <td><span class="chq-badge" :class="p.payment_type==='Receive'?'badge-green':'badge-red'">{{ p.payment_type==='Receive'?'Received':'Paid Out' }}</span></td>
              <td><span class="chq-badge" :class="statusBadge(p.cheque_status)">{{ p.cheque_status || 'Issued' }}</span></td>
              <td class="ta-r mono-sm">{{ fmtCur(p.paid_amount) }}</td>
            </tr>
            <tr v-if="!sorted.length"><td colspan="8" class="chq-empty">{{ list.length ? 'No cheques match this filter' : 'No cheque payments found' }}</td></tr>
          </template>
        </tbody>
      </table>

      <!-- Mobile cards (shown at ≤768px) -->
      <div class="chq-mobile-cards">
        <template v-if="loading">
          <div v-for="n in 5" :key="n" class="chq-mobile-card chq-mc--skeleton">
            <div class="chq-mc-shimmer" style="height:13px;width:55%;margin-bottom:8px"></div>
            <div class="chq-mc-shimmer" style="height:11px;width:40%;margin-bottom:6px"></div>
            <div class="chq-mc-shimmer" style="height:11px;width:65%"></div>
          </div>
        </template>
        <div v-else-if="!sorted.length" class="chq-mc-empty">
          <div style="font-size:32px;margin-bottom:8px">🧾</div>
          <div>{{ list.length ? 'No cheques match' : 'No cheque payments found' }}</div>
        </div>
        <template v-else>
          <div v-for="p in paged" :key="p.name" class="chq-mobile-card" @click="openView(p)">
            <div class="chq-mc-top">
              <span class="chq-mc-docno"><DocLink doctype="Payment Entry" :name="p.name" /></span>
              <span class="chq-badge" :class="statusBadge(p.cheque_status)">{{ p.cheque_status||'Issued' }}</span>
            </div>
            <div class="chq-mc-mid">{{ p.party_name || p.party || '—' }}</div>
            <div class="chq-mc-meta">
              <span>{{ fmtDate(p.payment_date) }}{{ p.reference_no ? ' · ' + p.reference_no : '' }}</span>
              <span class="chq-mc-amount">{{ fmtCur(p.paid_amount) }}</span>
            </div>
            <div class="chq-mc-type">
              <span class="chq-badge" :class="p.payment_type==='Receive'?'badge-green':'badge-red'">{{ p.payment_type==='Receive'?'Received':'Paid Out' }}</span>
            </div>
          </div>
        </template>
      </div>
    </div>

    <div v-if="!loading && sorted.length" style="padding:4px 0 0">
      <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="sorted.length" />
    </div>

    <!-- View drawer -->
    <div v-if="viewOpen" class="chq-overlay" @click.self="viewOpen=false"></div>
    <div class="chq-drawer" :class="{open:viewOpen}">
      <template v-if="viewDoc">
        <div class="chq-dheader">
          <button class="chq-dclose chq-dclose-abs" @click="viewOpen=false"><span v-html="icon('x',16)"></span></button>
          <div class="chq-dh-top">
            <div class="chq-dh-ico"><span v-html="icon('payment',20)"></span></div>
            <div>
              <div class="chq-dh-title">{{ viewDoc.name }}</div>
              <div class="chq-dh-sub">{{ viewDoc.party_name||viewDoc.party||'—' }} · {{ fmtDate(viewDoc.payment_date) }}</div>
            </div>
            <span class="chq-badge" :class="statusBadge(viewDoc.cheque_status)">{{ viewDoc.cheque_status || 'Issued' }}</span>
          </div>
          <div class="chq-dh-amount">
            <div class="chq-dh-amt-lbl">{{ viewDoc.payment_type==='Receive'?'Received':'Paid Out' }}</div>
            <div class="chq-dh-amt-val" :class="viewDoc.payment_type==='Receive'?'pos':'neg'">{{ fmtCur(viewDoc.paid_amount) }}</div>
          </div>
        </div>
        <div class="chq-dbody">
          <div class="chq-section-hdr"><span v-html="icon('info',13)"></span> Details</div>
          <div class="chq-meta-grid">
            <div><div class="chq-meta-lbl">Cheque No</div><div class="mono-sm">{{ viewDoc.reference_no||'—' }}</div></div>
            <div><div class="chq-meta-lbl">Cheque Date</div><div class="mono-sm">{{ fmtDate(viewDoc.reference_date)||'—' }}</div></div>
            <div><div class="chq-meta-lbl">Type</div><div>{{ viewDoc.payment_type==='Receive'?'Received':'Paid Out' }}</div></div>
            <div><div class="chq-meta-lbl">Mode</div><div>{{ viewDoc.mode_of_payment||'Cheque' }}</div></div>
            <div v-if="viewDoc.cheque_cleared_date"><div class="chq-meta-lbl">Cleared On</div><div class="mono-sm">{{ fmtDate(viewDoc.cheque_cleared_date) }}</div></div>
            <div v-if="viewDoc.cheque_bounce_reason" style="grid-column:1/-1"><div class="chq-meta-lbl">Bounce Reason</div><div style="color:#dc2626">{{ viewDoc.cheque_bounce_reason }}</div></div>
          </div>

          <div class="chq-section-hdr"><span v-html="icon('repeat',13)"></span> Lifecycle</div>
          <div class="chq-life-row">
            <button class="chq-life-btn" :class="{active:isStatus('Issued')}" @click="setStatus('Issued')" :disabled="busy">Issued</button>
            <button class="chq-life-btn life-cleared" :class="{active:isStatus('Cleared')}" @click="onClear" :disabled="busy">Cleared</button>
            <button class="chq-life-btn life-bounced" :class="{active:isStatus('Bounced')}" @click="onBounce" :disabled="busy">Bounced</button>
            <button class="chq-life-btn life-cancelled" :class="{active:isStatus('Cancelled')}" @click="setStatus('Cancelled')" :disabled="busy">Cancel</button>
          </div>
          <div v-if="showClearedDate" class="chq-life-input">
            <label class="chq-meta-lbl">Cleared Date</label>
            <input v-model="clearedDate" type="date" />
            <button class="chq-life-confirm" @click="confirmCleared" :disabled="busy">Confirm</button>
          </div>
          <div v-if="showBounceForm" class="chq-life-input">
            <label class="chq-meta-lbl">Bounce Reason</label>
            <input v-model="bounceReason" type="text" placeholder="Insufficient funds / Account closed / …"/>
            <button class="chq-life-confirm" @click="confirmBounce" :disabled="busy || !bounceReason.trim()">Confirm</button>
          </div>
        </div>
        <div class="chq-dfooter"><button class="chq-btn-ghost" @click="viewOpen=false">Close</button></div>
      </template>
    </div>
  </div>
</template>
<script setup>
import { ref, computed, onMounted } from "vue";
import { apiGET, apiPOST, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";
import { flt, fmtDate } from "../utils/format.js";
import SummaryStrip from "../components/SummaryStrip.vue";
import Pagination from "../components/Pagination.vue";
import { usePagination } from "../composables/usePagination.js";
import DocLink from "../components/DocLink.vue";
const { toast } = useToast();
const activeTab = ref("all");
const tabs = [
  { key: "all",       label: "All" },
  { key: "Issued",    label: "Issued" },
  { key: "Cleared",   label: "Cleared" },
  { key: "Bounced",   label: "Bounced" },
  { key: "Cancelled", label: "Cancelled" },
];
const list = ref([]), loading = ref(false), search = ref("");
const summary = ref({ issued:{count:0,total:0}, cleared:{count:0,total:0}, bounced:{count:0,total:0}, cancelled:{count:0,total:0} });
const viewOpen = ref(false), viewDoc = ref(null);
const sortCol = ref("payment_date"), sortDir = ref("desc");
const busy = ref(false), bulkBusy = ref(false);
const selected = ref(new Set());
const showClearedDate = ref(false), showBounceForm = ref(false);
const clearedDate = ref(""), bounceReason = ref("");

async function load() {
  loading.value = true;
  try {
    const [rows, s] = await Promise.all([
      apiGET("zoho_books_clone.api.docs.get_cheque_list"),
      apiGET("zoho_books_clone.api.docs.get_cheque_summary"),
    ]);
    list.value = rows || [];
    if (s) summary.value = s;
    selected.value = new Set();
  } catch (e) { toast.error(e.message || "Failed to load cheques"); }
  finally { loading.value = false; }
}

const filtered = computed(() => {
  let r = list.value;
  if (activeTab.value !== "all") {
    r = r.filter(p => (p.cheque_status || "Issued") === activeTab.value);
  }
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    r = r.filter(p => (p.party||"").toLowerCase().includes(q)
      || (p.reference_no||"").toLowerCase().includes(q)
      || (p.party_name||"").toLowerCase().includes(q));
  }
  return r;
});
const sorted = computed(() => {
  const col = sortCol.value;
  return [...filtered.value].sort((a, b) => {
    const av = a[col] ?? "", bv = b[col] ?? "";
    const c = typeof av === "number" ? av - bv : String(av).localeCompare(String(bv));
    return sortDir.value === "asc" ? c : -c;
  });
});
function sort(col) { if (sortCol.value===col) sortDir.value=sortDir.value==="asc"?"desc":"asc"; else { sortCol.value=col; sortDir.value="asc"; } }
function sortArrow(col) { if (sortCol.value!==col) return '<span style="color:#d1d5db">⇅</span>'; return sortDir.value==="asc"?"↑":"↓"; }

// Selection/export act on the full filtered+sorted set (all pages); only the
// table rendering itself is paginated via `paged`.
const { page, pageSize, paged } = usePagination(sorted, { storageKey: "bank-cheques" });

const totalAmount = computed(() => list.value.reduce((s, p) => s + flt(p.paid_amount), 0));
function tabCount(key) {
  if (key === "all") return list.value.length;
  return list.value.filter(p => (p.cheque_status || "Issued") === key).length;
}
function fmtCur(v) { return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 2 }).format(flt(v)); }

// ── selection ──
function toggleSelect(name){const s=new Set(selected.value);if(s.has(name))s.delete(name);else s.add(name);selected.value=s;}
const allSelected=computed(()=>sorted.value.length>0&&sorted.value.every(p=>selected.value.has(p.name)));
function toggleSelectAll(){if(allSelected.value){selected.value=new Set();}else{selected.value=new Set(sorted.value.map(p=>p.name));}}
const selectedIssued=computed(()=>sorted.value.filter(p=>(p.cheque_status||"Issued")==="Issued"&&selected.value.has(p.name)));

function exportCSV(){
  const rows=selected.value.size?sorted.value.filter(p=>selected.value.has(p.name)):sorted.value;
  if(!rows.length)return;
  const esc=v=>{const s=v==null?"":String(v);return /[",\n]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s;};
  const lines=[["Payment #","Party","Cheque No","Date","Type","Status","Amount"].join(",")];
  for(const p of rows){
    lines.push([p.name,p.party_name||p.party||"",p.reference_no||"",fmtDate(p.payment_date),p.payment_type==="Receive"?"Received":"Paid Out",p.cheque_status||"Issued",flt(p.paid_amount)||0].map(esc).join(","));
  }
  const blob=new Blob(["﻿"+lines.join("\r\n")],{type:"text/csv;charset=utf-8;"});
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a");
  a.href=url;a.download=`cheques_${new Date().toISOString().slice(0,10)}.csv`;
  a.click();URL.revokeObjectURL(url);
  toast.success(`Exported ${rows.length} row(s)`);
}

async function bulkClear(){
  const rows=selectedIssued.value;
  if(!rows.length)return;
  bulkBusy.value=true;let done=0;
  const today=new Date().toISOString().slice(0,10);
  try{
    for(const p of rows){
      try{await apiPOST("zoho_books_clone.api.docs.update_cheque_status",{payment_entry_name:p.name,new_status:"Cleared",cleared_date:today});done++;}catch{}
    }
    toast.success(`${done} cheque(s) marked Cleared`);await load();
  }finally{bulkBusy.value=false;}
}

function openView(p) {
  viewDoc.value = p;
  viewOpen.value = true;
  showClearedDate.value = false;
  showBounceForm.value = false;
  clearedDate.value = new Date().toISOString().slice(0, 10);
  bounceReason.value = "";
}
function isStatus(s) { return (viewDoc.value?.cheque_status || "Issued") === s; }
function statusBadge(s) {
  const map = { Issued:"badge-blue", Cleared:"badge-green", Bounced:"badge-red", Cancelled:"badge-grey" };
  return map[s || "Issued"];
}

async function setStatus(newStatus, extra = {}) {
  if (!viewDoc.value) return;
  busy.value = true;
  try {
    const res = await apiPOST("zoho_books_clone.api.docs.update_cheque_status", {
      payment_entry_name: viewDoc.value.name,
      new_status: newStatus,
      ...extra,
    });
    viewDoc.value.cheque_status = res.cheque_status;
    viewDoc.value.cheque_cleared_date = res.cheque_cleared_date || null;
    viewDoc.value.cheque_bounce_reason = res.cheque_bounce_reason || null;
    showClearedDate.value = false;
    showBounceForm.value = false;
    toast.success(`Cheque marked ${newStatus}`);
    await load();
  } catch (e) { toast.error(e.message || "Status update failed"); }
  busy.value = false;
}
function onClear()  { showClearedDate.value = !showClearedDate.value; showBounceForm.value = false; }
function onBounce() { showBounceForm.value  = !showBounceForm.value;  showClearedDate.value = false; }
function confirmCleared() { setStatus("Cleared", { cleared_date: clearedDate.value }); }
function confirmBounce()  { setStatus("Bounced", { bounce_reason: bounceReason.value.trim() }); }

onMounted(load);
</script>
<style scoped>
.chq-page{display:flex;flex-direction:column;gap:16px;padding:24px;}
.chq-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
.chq-search-wrap{display:flex;align-items:center;gap:8px;background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:6px 12px;min-width:240px;}
.chq-search-input{border:none;background:transparent;outline:none;font:inherit;color:#111827;width:100%;font-size:13px;}
.chq-btn-ghost{display:inline-flex;align-items:center;gap:6px;background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:8px 14px;font-size:13px;font-weight:600;color:#334155;cursor:pointer;}
.chq-btn-ghost:hover:not(:disabled){background:#f8fafc;border-color:#cbd5e1;}.chq-btn-ghost:disabled{opacity:.5;cursor:not-allowed;}

/* toolbar */
.chq-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;}
.chq-filter-pills{display:inline-flex;align-items:center;gap:3px;background:#eef2f7;border:1px solid #e2e8f0;border-radius:12px;padding:4px;}
.chq-fpill{display:inline-flex;align-items:center;gap:7px;padding:7px 14px;border-radius:9px;font-size:12.5px;font-weight:600;border:none;background:transparent;color:#64748b;cursor:pointer;font-family:inherit;transition:color .15s,background .15s,box-shadow .15s;}
.chq-fpill:hover:not(.active){color:#334155;}
.chq-fpill.active{background:#fff;color:#1d4ed8;box-shadow:0 1px 2px rgba(15,23,42,.08),0 0 0 1px rgba(37,99,235,.08);}
.chq-fpill-count{display:inline-flex;align-items:center;justify-content:center;min-width:19px;height:18px;padding:0 6px;border-radius:9px;background:rgba(100,116,139,.16);color:#64748b;font-size:10.5px;font-weight:700;line-height:1;}
.chq-fpill.active .chq-fpill-count{background:#dbeafe;color:#1d4ed8;}
.chq-toolbar-right{display:flex;align-items:center;gap:12px;}
.chq-result{font-size:12px;color:#94a3b8;font-weight:600;white-space:nowrap;}

/* selection bar */
.chq-selbar{display:flex;align-items:center;gap:12px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:10px 14px;flex-wrap:wrap;}
.chq-sel-count{font-size:13px;color:#1e3a8a;font-weight:700;}
.chq-sel-export{display:inline-flex;align-items:center;gap:6px;background:#fff;border:1px solid #bfdbfe;color:#1d4ed8;border-radius:8px;padding:7px 12px;font-size:12.5px;font-weight:600;cursor:pointer;font-family:inherit;}
.chq-sel-export:hover{background:#dbeafe;}
.chq-sel-ok{display:inline-flex;align-items:center;gap:6px;background:#f0fdf4;border:1px solid #86efac;color:#16a34a;border-radius:8px;padding:7px 12px;font-size:12.5px;font-weight:600;cursor:pointer;font-family:inherit;}
.chq-sel-ok:hover:not(:disabled){background:#dcfce7;}.chq-sel-ok:disabled{opacity:.5;cursor:not-allowed;}
.chq-sel-clear{background:transparent;border:none;color:#64748b;font-size:12.5px;font-weight:600;cursor:pointer;font-family:inherit;}
.chq-sel-clear:hover{color:#1d4ed8;text-decoration:underline;}

.chq-card{background:#fff;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;}
.chq-table{width:100%;border-collapse:collapse;font-size:13px;}
.chq-table th{background:#f9fafb;border-bottom:1px solid #e5e7eb;padding:10px 12px;font-size:11.5px;font-weight:600;color:#374151;text-align:left;white-space:nowrap;text-transform:uppercase;}
.chq-table th.sortable{cursor:pointer;user-select:none;}.chq-table th.sortable:hover{color:#2563eb;}
.ta-r{text-align:right!important;}
.chq-row td{padding:10px 12px;border-bottom:1px solid #f3f4f6;cursor:pointer;}
.chq-row:last-child td{border-bottom:none;}.chq-row:hover td{background:#f9fafb;}
.chq-num{font-size:12.5px;color:#2563eb;font-weight:600;}
.mono-sm{font-size:13px;}.text-muted{color:#6b7280;}
.chq-badge{display:inline-flex;align-items:center;padding:2px 8px;border-radius:10px;font-size:11.5px;font-weight:600;}
.badge-green{background:#dcfce7;color:#16a34a;}.badge-red{background:#fee2e2;color:#dc2626;}
.badge-blue{background:#dbeafe;color:#1d4ed8;}.badge-grey{background:#f3f4f6;color:#6b7280;}
.chq-empty{text-align:center;color:#9ca3af;padding:48px!important;cursor:default!important;}
.chq-shimmer{height:13px;background:linear-gradient(90deg,#f3f4f6 25%,#e5e7eb 50%,#f3f4f6 75%);border-radius:4px;animation:shimmer 1.2s infinite;background-size:200% 100%;}
@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}

/* drawer */
.chq-overlay{position:fixed;inset:0;background:rgba(15,23,42,.28);z-index:40;}
.chq-drawer{position:fixed;top:0;right:-420px;bottom:0;width:420px;max-width:96vw;background:#fff;border-left:1px solid #e5e7eb;box-shadow:-8px 0 28px rgba(15,23,42,.12);z-index:50;display:flex;flex-direction:column;transition:right .24s ease;}
.chq-drawer.open{right:0;}
.chq-dheader{position:relative;flex-shrink:0;padding:20px;border-bottom:1px solid #e5e7eb;background:linear-gradient(135deg,#eff6ff 0%,#dbeafe 100%);}
.chq-dclose{background:transparent;border:none;cursor:pointer;color:#475569;display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border-radius:8px;}
.chq-dclose:hover{background:rgba(255,255,255,.6);color:#0f172a;}
.chq-dclose-abs{position:absolute;top:12px;right:12px;}
.chq-dh-top{display:flex;align-items:center;gap:13px;padding-right:36px;}
.chq-dh-ico{width:42px;height:42px;background:#fff;border-radius:11px;display:flex;align-items:center;justify-content:center;color:#2563eb;flex-shrink:0;box-shadow:0 1px 3px rgba(15,23,42,.08);}
.chq-dh-title{font-size:15px;font-weight:700;color:#0f172a;}
.chq-dh-sub{font-size:12px;color:#475569;margin-top:1px;}
.chq-dh-top .chq-badge{margin-left:auto;}
.chq-dh-amount{margin-top:16px;}
.chq-dh-amt-lbl{font-size:10.5px;color:#64748b;text-transform:uppercase;letter-spacing:.05em;font-weight:600;}
.chq-dh-amt-val{font-size:26px;font-weight:800;letter-spacing:-.01em;margin-top:2px;}
.chq-dh-amt-val.pos{color:#16a34a;}.chq-dh-amt-val.neg{color:#dc2626;}
.chq-dbody{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:12px;}
.chq-section-hdr{display:flex;align-items:center;gap:8px;font-size:11.5px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:#0f172a;margin-top:4px;}
.chq-section-hdr span{color:#2563eb;display:inline-flex;}
.chq-meta-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
.chq-meta-lbl{font-size:10.5px;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;margin-bottom:2px;font-weight:600;}
.chq-life-row{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;}
.chq-life-btn{padding:8px 10px;border:1px solid #e5e7eb;border-radius:8px;background:#fff;color:#6b7280;font:inherit;font-size:12px;font-weight:600;cursor:pointer;text-align:center;}
.chq-life-btn:hover:not(:disabled){background:#f9fafb;}
.chq-life-btn:disabled{opacity:.5;cursor:not-allowed;}
.chq-life-btn.active{border-color:#2563eb;background:#eff6ff;color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.08);}
.chq-life-btn.life-cleared.active{border-color:#16a34a;background:#dcfce7;color:#16a34a;}
.chq-life-btn.life-bounced.active{border-color:#dc2626;background:#fee2e2;color:#dc2626;}
.chq-life-btn.life-cancelled.active{border-color:#6b7280;background:#f3f4f6;}
.chq-life-input{display:flex;align-items:center;gap:8px;margin-top:8px;padding:10px;background:#f8fafc;border:1px solid #e5e7eb;border-radius:8px;}
.chq-life-input input[type=date],.chq-life-input input[type=text]{flex:1;border:1px solid #e2e8f0;border-radius:6px;padding:6px 10px;font:inherit;font-size:13px;outline:none;background:#fff;}
.chq-life-input input:focus{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.1);}
.chq-life-confirm{background:#2563eb;color:#fff;border:none;padding:6px 12px;border-radius:6px;font:inherit;font-size:12px;font-weight:600;cursor:pointer;}
.chq-life-confirm:hover:not(:disabled){background:#1d4ed8;}
.chq-life-confirm:disabled{opacity:.5;cursor:not-allowed;}
.chq-dfooter{display:flex;justify-content:flex-end;padding:14px 20px;border-top:1px solid #e5e7eb;flex-shrink:0;}

/* ── Mobile card defaults ── */
.chq-mobile-cards { display: none; }
.chq-desktop-table { display: table; }

/* ── Responsive ── */
@media (max-width: 768px) {
  .chq-drawer { width: 100% !important; right: -100% !important; max-width: 100%; }
  .chq-drawer.open { right: 0 !important; }
  .chq-desktop-table { display: none !important; }
  .chq-mobile-cards { display: flex; flex-direction: column; gap: 0; background: #f8fafc; }
  .chq-mobile-card { background: #fff; border-bottom: 1px solid #e5e7eb; padding: 12px 14px; cursor: pointer; transition: background .12s; }
  .chq-mobile-card:active { background: #f8f9fc; }
  .chq-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .chq-mc-docno { font-size: 12px; font-weight: 700; color: #2563eb; }
  .chq-mc-mid { font-size: 13.5px; font-weight: 600; color: #1a1d23; margin-bottom: 4px; }
  .chq-mc-meta { display: flex; justify-content: space-between; font-size: 12px; color: #868e96; margin-bottom: 6px; }
  .chq-mc-amount { font-weight: 700; color: #1a1d23; }
  .chq-mc-type { display: flex; gap: 6px; }
  .chq-mc--skeleton { pointer-events: none; }
  .chq-mc-shimmer { border-radius: 6px; background: linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size: 200% 100%; animation: chq-mc-sh 1.4s infinite; }
  @keyframes chq-mc-sh { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
  .chq-mc-empty { text-align: center; padding: 32px 16px; color: #868e96; font-size: 13px; }
  .chq-badge { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 10px; font-size: 11.5px; font-weight: 600; }
}

@media (max-width: 480px) {
  .chq-page { padding: 12px; gap: 12px; }
  .chq-search-wrap { min-width: 0; flex: 1 1 auto; }
  .chq-meta-grid { grid-template-columns: 1fr !important; }
  .chq-dh-amt-val { font-size: 20px; }
  .chq-life-input { flex-wrap: wrap; }
  .chq-filter-pills{display: contents;}
  .chq-life-input input { min-width: 0; flex: 1 1 100%; }
}
</style>