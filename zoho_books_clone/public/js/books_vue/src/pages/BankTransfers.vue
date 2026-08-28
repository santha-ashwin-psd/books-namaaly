<template>
  <div class="btr-page">
    <div class="btr-actions">
      <div class="btr-search-wrap">
        <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
        <input v-model="search" placeholder="Search transfers…" class="btr-search-input" />
      </div>
      <div style="display:flex;gap:8px;margin-left:auto">
        <button class="btr-btn-ghost" @click="load"><span v-html="icon('refresh',14)"></span></button>
        <button class="btr-btn-primary" :disabled="!$canCreate('banking')" :title="!$canCreate('banking') ? 'Read-only access' : ''" @click="openNew"><span v-html="icon('plus',13)"></span> New Transfer</button>
      </div>
    </div>

    <SummaryStrip v-if="!loading" :cards="[
      { label: 'Total Transfers', tone: 'default', value: list.length },
      { label: 'Total Amount', tone: 'accent', value: fmtCur(totalAmount), valueClass: 'green' },
      { label: 'This Month', tone: 'info', value: fmtCur(monthAmount), valueClass: 'blue' },
      { label: 'Unreconciled', tone: unreconciledCount>0?'warn':'default', value: unreconciledCount, valueClass: unreconciledCount>0?'orange':'' },
    ]" />

    <!-- Filter toolbar -->
    <div v-if="!loading && list.length" class="btr-toolbar">
      <div class="btr-filter-pills">
        <button v-for="s in statusTabs" :key="s.key" class="btr-fpill" :class="{active:statusFilter===s.key}" @click="statusFilter=s.key">
          {{ s.label }} <span class="btr-fpill-count">{{ s.count }}</span>
        </button>
      </div>
      <div class="btr-toolbar-right">
        <span class="btr-result">{{ displayRows.length }} of {{ list.length }}</span>
        <button class="btr-btn-ghost" @click="exportCSV" :disabled="!displayRows.length">
          <span v-html="icon('download',14)"></span> Export
        </button>
      </div>
    </div>

    <!-- Selection bar -->
    <div v-if="selected.size>0" class="btr-selbar">
      <span class="btr-sel-count">{{ selected.size }} selected</span>
      <button class="btr-sel-export" @click="exportCSV"><span v-html="icon('download',13)"></span> Export selected</button>
      <button class="btr-sel-danger" @click="bulkDelete" :disabled="bulkBusy || !$canDelete('banking')" :title="!$canDelete('banking') ? 'Not permitted' : ''">
        <span v-html="icon('trash',13)"></span> Delete {{ selected.size }}
      </button>
      <div style="flex:1"></div>
      <button class="btr-sel-clear" @click="selected=new Set()">Clear</button>
    </div>

    <div class="btr-card">
      <table class="btr-table btr-desktop-table">
        <thead>
          <tr>
            <th style="width:32px"><input type="checkbox" :checked="allSelected" @change="toggleSelectAll" /></th>
            <th @click="sort('date')" class="sortable">Date <span v-html="sortArrow('date')"></span></th>
            <th>Reference</th>
            <th>From Account</th><th>To Account</th>
            <th>Status</th>
            <th @click="sort('amount')" class="sortable ta-r">Amount <span v-html="sortArrow('amount')"></span></th>
            <th style="width:50px"></th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 6" :key="n"><td colspan="8"><div class="btr-shimmer"></div></td></tr>
          </template>
          <template v-else>
            <tr v-for="t in pagedRows" :key="t.from_transaction" class="btr-row" @click="openView(t)">
              <td @click.stop><input type="checkbox" :checked="selected.has(t.from_transaction)" @change="toggleSelect(t.from_transaction)" /></td>
              <td class="mono-sm text-muted">{{ fmtDate(t.date) }}</td>
              <td><span class="btr-num">{{ t.reference || t.from_transaction }}</span></td>
              <td class="text-muted">{{ t.from_account||'—' }}</td>
              <td class="text-muted">{{ t.to_account||'—' }}</td>
              <td><span class="btr-badge" :class="t.status==='Reconciled'?'badge-green':'badge-orange'">{{ t.status||'Unreconciled' }}</span></td>
              <td class="ta-r mono-sm">{{ fmtCur(t.amount) }}</td>
              <td @click.stop><button class="btr-act-btn" @click="openView(t)"><span v-html="icon('eye',13)"></span></button></td>
            </tr>
            <tr v-if="!displayRows.length"><td colspan="8" class="btr-empty">{{ list.length ? 'No transfers match this filter' : 'No transfers found' }}</td></tr>
          </template>
        </tbody>
      </table>

      <!-- Mobile cards (shown at ≤768px) -->
      <div class="btr-mobile-cards">
        <template v-if="loading">
          <div v-for="n in 5" :key="n" class="btr-mobile-card btr-mc--skeleton">
            <div class="btr-mc-shimmer" style="height:13px;width:55%;margin-bottom:8px"></div>
            <div class="btr-mc-shimmer" style="height:11px;width:40%;margin-bottom:6px"></div>
            <div class="btr-mc-shimmer" style="height:11px;width:65%"></div>
          </div>
        </template>
        <div v-else-if="!displayRows.length" class="btr-mc-empty">
          <div style="font-size:32px;margin-bottom:8px">↔️</div>
          <div>{{ list.length ? 'No transfers match' : 'No transfers found' }}</div>
        </div>
        <template v-else>
          <div v-for="t in pagedRows" :key="t.from_transaction" class="btr-mobile-card" @click="openView(t)">
            <div class="btr-mc-top">
              <span class="btr-mc-docno">{{ t.reference || t.from_transaction }}</span>
              <span class="btr-badge" :class="t.status==='Reconciled'?'badge-green':'badge-orange'">{{ t.status||'Unreconciled' }}</span>
            </div>
            <div class="btr-mc-mid">{{ t.from_account||'—' }} → {{ t.to_account||'—' }}</div>
            <div class="btr-mc-meta">
              <span>{{ fmtDate(t.date) }}</span>
              <span class="btr-mc-amount">{{ fmtCur(t.amount) }}</span>
            </div>
          </div>
        </template>
      </div>
    </div>

    <div v-if="!loading && displayRows.length" style="padding:4px 0 0">
      <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="displayRows.length" />
    </div>

    <!-- Create Drawer -->
    <div v-if="drawerOpen" class="btr-overlay" @click.self="!drawerSaving && (drawerOpen=false)"></div>
    <div class="btr-drawer" :class="{open:drawerOpen}">
      <div class="btr-dheader">
        <button class="btr-dclose btr-dclose-abs" @click="drawerOpen=false"><span v-html="icon('x',16)"></span></button>
        <div class="btr-dh-top">
          <div class="btr-dh-ico"><span v-html="icon('repeat',20)"></span></div>
          <div>
            <div class="btr-dh-title">New Bank Transfer</div>
            <div class="btr-dh-sub">Move funds between bank accounts</div>
          </div>
        </div>
      </div>
      <div class="btr-dbody">
        <div class="btr-section-hdr"><span v-html="icon('calendar',13)"></span> Transfer</div>
        <div class="btr-fields-grid">
          <div class="btr-field">
            <label class="btr-label">Transfer Date <span class="req">*</span></label>
            <input v-model="form.posting_date" type="date" class="btr-input" />
          </div>
          <div class="btr-field">
            <label class="btr-label">Amount <span class="req">*</span></label>
            <input v-model.number="form.amount" type="number" min="0" step="0.01" class="btr-input" placeholder="0.00" />
          </div>
          <div class="btr-field" style="grid-column:1/-1">
            <label class="btr-label">From Account <span class="req">*</span></label>
            <SearchableSelect v-model="form.from_account" :options="accounts" placeholder="Source bank account…" @search="fetchAccounts" />
          </div>
          <div class="btr-field" style="grid-column:1/-1">
            <label class="btr-label">To Account <span class="req">*</span></label>
            <SearchableSelect v-model="form.to_account" :options="accounts" placeholder="Destination bank account…" @search="fetchAccounts" />
          </div>
          <div class="btr-field" style="grid-column:1/-1">
            <label class="btr-label">Purpose / Transfer Type</label>
            <select v-model="form.purpose" class="btr-input">
              <option value="">— Select purpose —</option>
              <option v-for="p in TRANSFER_PURPOSES" :key="p" :value="p">{{ p }}</option>
            </select>
          </div>
          <div class="btr-field" style="grid-column:1/-1">
            <label class="btr-label">Remarks</label>
            <textarea v-model="form.remark" rows="2" class="btr-input" placeholder="Optional…"></textarea>
          </div>
        </div>
        <div class="btr-hint">Posts two reconciled bank transactions and a balanced ledger entry.</div>
      </div>
      <div class="btr-dfooter">
        <button class="btr-btn-ghost" @click="drawerOpen=false">Cancel</button>
        <button class="btr-btn-primary" :disabled="drawerSaving" @click="saveTransfer"><span v-html="icon('check',13)"></span> {{ drawerSaving?'Posting…':'Post Transfer' }}</button>
      </div>
    </div>

    <!-- View -->
    <div v-if="viewOpen" class="btr-overlay" @click.self="viewOpen=false"></div>
    <div class="btr-drawer btr-view-drawer" :class="{open:viewOpen}">
      <template v-if="viewDoc">
        <div class="btr-dheader">
          <button class="btr-dclose btr-dclose-abs" @click="viewOpen=false"><span v-html="icon('x',16)"></span></button>
          <div class="btr-dh-top">
            <div class="btr-dh-ico"><span v-html="icon('repeat',20)"></span></div>
            <div>
              <div class="btr-dh-title">{{ viewDoc.reference || viewDoc.from_transaction }}</div>
              <div class="btr-dh-sub">{{ fmtDate(viewDoc.date) }}</div>
            </div>
            <span class="btr-badge" :class="viewDoc.status==='Reconciled'?'badge-green':'badge-orange'">{{ viewDoc.status||'Unreconciled' }}</span>
          </div>
          <div class="btr-dh-amount">
            <div class="btr-dh-amt-lbl">Amount</div>
            <div class="btr-dh-amt-val">{{ fmtCur(viewDoc.amount) }}</div>
          </div>
        </div>
        <div class="btr-dbody">
          <div class="btr-section-hdr"><span v-html="icon('info',13)"></span> Details</div>
          <div class="btr-flow">
            <div class="btr-flow-acc">
              <div class="btr-flow-lbl">From</div>
              <div class="btr-flow-name">{{ viewDoc.from_account||'—' }}</div>
            </div>
            <span class="btr-flow-arrow" v-html="icon('arrow-right',18)"></span>
            <div class="btr-flow-acc">
              <div class="btr-flow-lbl">To</div>
              <div class="btr-flow-name">{{ viewDoc.to_account||'—' }}</div>
            </div>
          </div>
          <div class="btr-meta-grid">
            <div><div class="btr-meta-lbl">Date</div><div class="mono-sm">{{ fmtDate(viewDoc.date) }}</div></div>
            <div><div class="btr-meta-lbl">Status</div><div><span class="btr-badge" :class="viewDoc.status==='Reconciled'?'badge-green':'badge-orange'">{{ viewDoc.status||'Unreconciled' }}</span></div></div>
            <div><div class="btr-meta-lbl">Out Txn</div><div class="mono-sm">{{ viewDoc.from_transaction||'—' }}</div></div>
            <div><div class="btr-meta-lbl">In Txn</div><div class="mono-sm">{{ viewDoc.to_transaction||'—' }}</div></div>
            <div v-if="viewDoc.purpose" style="grid-column:1/-1"><div class="btr-meta-lbl">Purpose / Transfer Type</div><div>{{ viewDoc.purpose }}</div></div>
            <div v-if="viewDoc.description" style="grid-column:1/-1"><div class="btr-meta-lbl">Notes / Remarks</div><div style="word-break: break-word;">{{ viewDoc.description }}</div></div>
          </div>

          <div class="btr-section-hdr"><span v-html="icon('journal',13)"></span> Journal</div>
          <JournalTab
            voucher-type="Bank Transaction"
            :voucher-no="viewDoc.from_transaction"
            label="Bank Transfer"
            :currency="viewDoc.currency || 'OMR'"
          />
        </div>
        <div class="btr-dfooter">
          <button class="btr-btn-danger-ghost" @click="deleteTransfer(viewDoc)" :disabled="actionBusy || !$canDelete('banking')" :title="!$canDelete('banking') ? 'Not permitted' : ''"><span v-html="icon('trash',13)"></span> Delete</button>
          <div style="margin-left:auto"><button class="btr-btn-ghost" @click="viewOpen=false">Close</button></div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { apiList, apiGET, apiPOST, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { useConfirm } from "../composables/useConfirm.js";
import { useRoute } from "vue-router";
import { icon } from "../utils/icons.js";
import { flt, fmtDate } from "../utils/format.js";
import SearchableSelect from "../components/SearchableSelect.vue";
import SummaryStrip from "../components/SummaryStrip.vue";
import Pagination from "../components/Pagination.vue";
import JournalTab from "../components/JournalTab.vue";
import { usePagination } from "../composables/usePagination.js";

const { toast } = useToast();
const { confirm } = useConfirm();
const route = useRoute();
const list=ref([]),loading=ref(false),search=ref(""),statusFilter=ref("all");
const drawerOpen=ref(false),drawerSaving=ref(false),actionBusy=ref(false),bulkBusy=ref(false);
const viewOpen=ref(false),viewDoc=ref(null);
const accounts=ref([]);
const selected=ref(new Set());
const sortCol=ref("date"),sortDir=ref("desc");
const TRANSFER_PURPOSES = ["Fund Transfer","Salary Account Funding","Branch Transfer","Cash Withdrawal"];
const form=reactive({posting_date:new Date().toISOString().slice(0,10),amount:0,from_account:"",to_account:"",purpose:"",remark:""});
const now=new Date();
const monthStart=new Date(now.getFullYear(),now.getMonth(),1).toISOString().slice(0,10);

async function load(){
  loading.value=true;
  try{
    const co=await resolveCompany();
    const r=await apiGET("zoho_books_clone.api.banking.get_bank_transfers",{company:co});
    list.value=Array.isArray(r)?r:(r?.message||[]);
    selected.value=new Set();
  }catch(e){toast.error(e.message||"Failed to load transfers");}finally{loading.value=false;}
}

const filtered=computed(()=>{
  let r=list.value;
  if(statusFilter.value!=="all")r=r.filter(t=>(t.status||"Unreconciled")===statusFilter.value);
  if(search.value.trim()){const q=search.value.toLowerCase();r=r.filter(t=>(t.reference||"").toLowerCase().includes(q)||(t.from_transaction||"").toLowerCase().includes(q)||(t.from_account||"").toLowerCase().includes(q)||(t.to_account||"").toLowerCase().includes(q));}
  return r;
});
const displayRows=computed(()=>{const col=sortCol.value;return[...filtered.value].sort((a,b)=>{const av=a[col]??"",bv=b[col]??"";const c=typeof av==="number"?av-bv:String(av).localeCompare(String(bv));return sortDir.value==="asc"?c:-c;});});
function sort(col){if(sortCol.value===col)sortDir.value=sortDir.value==="asc"?"desc":"asc";else{sortCol.value=col;sortDir.value="asc";}}
function sortArrow(col){if(sortCol.value!==col)return'<span style="color:#d1d5db">⇅</span>';return sortDir.value==="asc"?"↑":"↓";}
// Selection/export act on the full filtered+sorted set (all pages); only the
// table rendering itself is paginated via `pagedRows`.
const { page, pageSize, paged: pagedRows } = usePagination(displayRows, { storageKey: "bank-transfers" });

const statusTabs=computed(()=>[
  {key:"all",label:"All",count:list.value.length},
  {key:"Reconciled",label:"Reconciled",count:list.value.filter(t=>t.status==="Reconciled").length},
  {key:"Unreconciled",label:"Unreconciled",count:list.value.filter(t=>t.status!=="Reconciled").length},
]);
const totalAmount=computed(()=>list.value.reduce((s,t)=>s+flt(t.amount),0));
const monthAmount=computed(()=>list.value.filter(t=>String(t.date)>=monthStart).reduce((s,t)=>s+flt(t.amount),0));
const unreconciledCount=computed(()=>list.value.filter(t=>t.status!=="Reconciled").length);
function fmtCur(v){const n=flt(v);try{return new Intl.NumberFormat("en-OM",{style:"currency",currency:"OMR"}).format(n);}catch{return "ر.ع. "+n.toLocaleString("en-OM",{minimumFractionDigits:3,maximumFractionDigits:3});}}

// ── selection (keyed by outgoing transaction) ──
function toggleSelect(id){const s=new Set(selected.value);if(s.has(id))s.delete(id);else s.add(id);selected.value=s;}
const allSelected=computed(()=>displayRows.value.length>0&&displayRows.value.every(t=>selected.value.has(t.from_transaction)));
function toggleSelectAll(){if(allSelected.value){selected.value=new Set();}else{selected.value=new Set(displayRows.value.map(t=>t.from_transaction));}}

function exportCSV(){
  const rows=selected.value.size?displayRows.value.filter(t=>selected.value.has(t.from_transaction)):displayRows.value;
  if(!rows.length)return;
  const esc=v=>{const s=v==null?"":String(v);return /[",\n]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s;};
  const lines=[["Reference","Date","From Account","To Account","Amount","Status"].join(",")];
  for(const t of rows){
    lines.push([t.reference||t.from_transaction,fmtDate(t.date),t.from_account||"",t.to_account||"",flt(t.amount)||0,t.status||"Unreconciled"].map(esc).join(","));
  }
  const blob=new Blob(["﻿"+lines.join("\r\n")],{type:"text/csv;charset=utf-8;"});
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a");
  a.href=url;a.download=`bank_transfers_${new Date().toISOString().slice(0,10)}.csv`;
  a.click();URL.revokeObjectURL(url);
  toast.success(`Exported ${rows.length} row(s)`);
}

async function bulkDelete(){
  const rows=displayRows.value.filter(t=>selected.value.has(t.from_transaction));
  if(!rows.length)return;
  const ok=await confirm({title:`Delete ${rows.length} transfer(s)?`,body:"This reverses the ledger entries and removes both bank transaction legs. This cannot be undone.",okLabel:"Delete",okStyle:"danger"});
  if(!ok)return;
  bulkBusy.value=true;let done=0;
  try{
    for(const t of rows){
      try{await apiPOST("zoho_books_clone.api.banking.delete_bank_transfer",{reference:t.reference||"",from_transaction:t.from_transaction||""},{module:"banking",action:"delete"});done++;}catch{}
    }
    toast.success(`Deleted ${done} transfer(s)`);await load();
  }finally{bulkBusy.value=false;}
}

function openNew(){Object.assign(form,{posting_date:new Date().toISOString().slice(0,10),amount:0,from_account:"",to_account:"",purpose:"",remark:""});accounts.value=[];fetchAccounts("");drawerOpen.value=true;}
function openView(t){viewDoc.value=t;viewOpen.value=true;}
async function fetchAccounts(q=""){try{const co=await resolveCompany();const r=await apiList("Bank Account",{fields:["name","account_name"],filters:[["company","=",co],...(q?[["account_name","like",`%${q}%`]]:[])],limit:50});accounts.value=r.map(x=>({label:x.account_name||x.name,value:x.name}));}catch{accounts.value=[];}}

async function saveTransfer(){
  if(!form.from_account||!form.to_account)return toast.error("Both accounts are required");
  if(form.from_account===form.to_account)return toast.error("From and To accounts must be different");
  if(!flt(form.amount))return toast.error("Amount is required");
  drawerSaving.value=true;
  try{
    const res=await apiPOST("zoho_books_clone.api.banking.post_bank_transfer",{from_account:form.from_account,to_account:form.to_account,amount:flt(form.amount),date:form.posting_date,purpose:form.purpose||"",description:form.remark||""},{module:"banking",action:"create"});
    const amt=res?.message?.amount??res?.amount??form.amount;
    toast.success(`Transfer of ${fmtCur(amt)} posted`);
    drawerOpen.value=false;await load();
  }catch(e){toast.error(e.message||"Failed to post transfer");}finally{drawerSaving.value=false;}
}

async function deleteTransfer(t){
  const ok=await confirm({title:"Delete this transfer?",body:`This reverses the ledger entries and removes both legs of ${t.reference||t.from_transaction}.`,okLabel:"Delete",okStyle:"danger"});
  if(!ok)return;
  actionBusy.value=true;
  try{await apiPOST("zoho_books_clone.api.banking.delete_bank_transfer",{reference:t.reference||"",from_transaction:t.from_transaction||""},{module:"banking",action:"delete"});toast.success("Transfer deleted");viewOpen.value=false;await load();}
  catch(e){toast.error(e.message||"Failed to delete");}finally{actionBusy.value=false;}
}

onMounted(async()=>{await load();if(route.query.from){openNew();form.from_account=String(route.query.from);}});
</script>

<style scoped>
.btr-page{display:flex;flex-direction:column;gap:16px;padding:24px;}
.btr-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
.btr-search-wrap{display:flex;align-items:center;gap:8px;background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:6px 12px;min-width:240px;}
.btr-search-input{border:none;background:transparent;outline:none;font:inherit;color:#111827;width:100%;font-size:13px;}
.btr-btn-primary{display:inline-flex;align-items:center;gap:6px;background:#2563eb;color:#fff;border:none;border-radius:8px;padding:8px 14px;font-size:13px;font-weight:600;cursor:pointer;}
.btr-btn-primary:hover{background:#1d4ed8;}.btr-btn-primary:disabled{opacity:.5;cursor:not-allowed;}
.btr-btn-ghost{display:inline-flex;align-items:center;gap:6px;background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:8px 14px;font-size:13px;font-weight:600;color:#334155;cursor:pointer;}
.btr-btn-ghost:hover:not(:disabled){background:#f8fafc;border-color:#cbd5e1;}.btr-btn-ghost:disabled{opacity:.5;cursor:not-allowed;}
.btr-btn-danger-ghost{display:inline-flex;align-items:center;gap:6px;background:#fff;border:1px solid #fecaca;border-radius:8px;padding:8px 12px;font-size:13px;color:#dc2626;cursor:pointer;}
.btr-btn-danger-ghost:hover:not(:disabled){background:#fef2f2;}.btr-btn-danger-ghost:disabled{opacity:.5;cursor:not-allowed;}

/* toolbar */
.btr-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;}
.btr-filter-pills{display:inline-flex;align-items:center;gap:3px;background:#eef2f7;border:1px solid #e2e8f0;border-radius:12px;padding:4px;}
.btr-fpill{display:inline-flex;align-items:center;gap:7px;padding:7px 14px;border-radius:9px;font-size:12.5px;font-weight:600;border:none;background:transparent;color:#64748b;cursor:pointer;font-family:inherit;transition:color .15s,background .15s,box-shadow .15s;}
.btr-fpill:hover:not(.active){color:#334155;}
.btr-fpill.active{background:#fff;color:#1d4ed8;box-shadow:0 1px 2px rgba(15,23,42,.08),0 0 0 1px rgba(37,99,235,.08);}
.btr-fpill-count{display:inline-flex;align-items:center;justify-content:center;min-width:19px;height:18px;padding:0 6px;border-radius:9px;background:rgba(100,116,139,.16);color:#64748b;font-size:10.5px;font-weight:700;line-height:1;}
.btr-fpill.active .btr-fpill-count{background:#dbeafe;color:#1d4ed8;}
.btr-toolbar-right{display:flex;align-items:center;gap:12px;}
.btr-result{font-size:12px;color:#94a3b8;font-weight:600;white-space:nowrap;}

/* selection bar */
.btr-selbar{display:flex;align-items:center;gap:12px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:10px 14px;flex-wrap:wrap;}
.btr-sel-count{font-size:13px;color:#1e3a8a;font-weight:700;}
.btr-sel-export{display:inline-flex;align-items:center;gap:6px;background:#fff;border:1px solid #bfdbfe;color:#1d4ed8;border-radius:8px;padding:7px 12px;font-size:12.5px;font-weight:600;cursor:pointer;font-family:inherit;}
.btr-sel-export:hover{background:#dbeafe;}
.btr-sel-danger{display:inline-flex;align-items:center;gap:6px;background:#fff;border:1px solid #fecaca;color:#dc2626;border-radius:8px;padding:7px 12px;font-size:12.5px;font-weight:600;cursor:pointer;font-family:inherit;}
.btr-sel-danger:hover:not(:disabled){background:#fef2f2;}.btr-sel-danger:disabled{opacity:.5;cursor:not-allowed;}
.btr-sel-clear{background:transparent;border:none;color:#64748b;font-size:12.5px;font-weight:600;cursor:pointer;font-family:inherit;}
.btr-sel-clear:hover{color:#1d4ed8;text-decoration:underline;}

.btr-card{background:#fff;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;}
.btr-table{width:100%;border-collapse:collapse;font-size:13px;}
.btr-table th{background:#f9fafb;border-bottom:1px solid #e5e7eb;padding:10px 12px;font-size:11.5px;font-weight:600;color:#374151;text-align:left;white-space:nowrap;text-transform:uppercase;}
.btr-table th.sortable{cursor:pointer;user-select:none;}.btr-table th.sortable:hover{color:#2563eb;}
.ta-r{text-align:right!important;}
.btr-row td{padding:10px 12px;border-bottom:1px solid #f3f4f6;vertical-align:middle;cursor:pointer;}
.btr-row:last-child td{border-bottom:none;}.btr-row:hover td{background:#f9fafb;}
.btr-num{font-size:13px;color:#2563eb;font-weight:600;}
.mono-sm{font-size:13px;}.text-muted{color:#6b7280;}
.btr-badge{display:inline-flex;align-items:center;padding:2px 8px;border-radius:10px;font-size:11.5px;font-weight:600;}
.badge-green{background:#dcfce7;color:#16a34a;}.badge-orange{background:#fff7ed;color:#ea580c;}.badge-grey{background:#f3f4f6;color:#6b7280;}
.btr-act-btn{background:transparent;border:1px solid #e5e7eb;border-radius:6px;width:26px;height:26px;display:inline-flex;align-items:center;justify-content:center;cursor:pointer;color:#6b7280;}
.btr-act-btn:hover{background:#f3f4f6;color:#2563eb;}
.btr-empty{text-align:center;color:#9ca3af;padding:48px!important;cursor:default!important;}
.btr-shimmer{height:13px;background:linear-gradient(90deg,#f3f4f6 25%,#e5e7eb 50%,#f3f4f6 75%);border-radius:4px;animation:shimmer 1.2s infinite;background-size:200% 100%;}
@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}

/* drawers */
.btr-overlay{position:fixed;inset:0;background:rgba(15,23,42,.28);z-index:40;}
.btr-drawer{position:fixed;top:0;right:-480px;bottom:0;width:480px;max-width:96vw;background:#fff;border-left:1px solid #e5e7eb;box-shadow:-8px 0 28px rgba(15,23,42,.12);z-index:50;display:flex;flex-direction:column;transition:right .24s ease;}
.btr-drawer.open{right:0;}
.btr-view-drawer{width:420px;right:-420px;}.btr-view-drawer.open{right:0;}
.btr-dheader{position:relative;flex-shrink:0;padding:20px;border-bottom:1px solid #e5e7eb;background:linear-gradient(135deg,#eff6ff 0%,#dbeafe 100%);}
.btr-dclose{background:transparent;border:none;cursor:pointer;color:#475569;display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border-radius:8px;}
.btr-dclose:hover{background:rgba(255,255,255,.6);color:#0f172a;}
.btr-dclose-abs{position:absolute;top:12px;right:12px;}
.btr-dh-top{display:flex;align-items:center;gap:13px;padding-right:36px;}
.btr-dh-ico{width:42px;height:42px;background:#fff;border-radius:11px;display:flex;align-items:center;justify-content:center;color:#2563eb;flex-shrink:0;box-shadow:0 1px 3px rgba(15,23,42,.08);}
.btr-dh-title{font-size:15px;font-weight:700;color:#0f172a;}
.btr-dh-sub{font-size:12px;color:#475569;margin-top:1px;}
.btr-dh-top .btr-badge{margin-left:auto;}
.btr-dh-amount{margin-top:16px;}
.btr-dh-amt-lbl{font-size:10.5px;color:#64748b;text-transform:uppercase;letter-spacing:.05em;font-weight:600;}
.btr-dh-amt-val{font-size:26px;font-weight:800;letter-spacing:-.01em;margin-top:2px;color:#0f172a;}
.btr-dbody{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:12px;}
.btr-section-hdr{display:flex;align-items:center;gap:8px;font-size:11.5px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:#0f172a;margin-top:4px;}
.btr-section-hdr span{color:#2563eb;display:inline-flex;}
.btr-flow{display:flex;align-items:center;gap:12px;background:#f8fafc;border:1px solid #eef2f7;border-radius:10px;padding:14px;}
.btr-flow-acc{flex:1;min-width:0;}
.btr-flow-lbl{font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;font-weight:600;margin-bottom:2px;}
.btr-flow-name{font-size:13px;color:#0f172a;font-weight:600;word-break:break-word;}
.btr-flow-arrow{color:#2563eb;flex-shrink:0;display:inline-flex;}
.btr-fields-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
.btr-field{display:flex;flex-direction:column;gap:4px;}
.btr-label{font-size:12px;font-weight:600;color:#334155;}.req{color:#dc2626;}
.btr-hint{font-size:11.5px;color:#94a3b8;margin-top:10px;}
.btr-input{border:1px solid #e2e8f0;border-radius:8px;padding:8px 11px;font:inherit;font-size:13px;outline:none;background:#fff;color:#0f172a;transition:border-color .15s,box-shadow .15s;}
.btr-input:focus{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.1);}
textarea.btr-input{resize:vertical;}
.btr-meta-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
.btr-meta-lbl{font-size:10.5px;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;margin-bottom:2px;font-weight:600;}
.btr-dfooter{display:flex;align-items:center;gap:8px;padding:14px 20px;border-top:1px solid #e5e7eb;flex-shrink:0;}

/* ── Mobile card defaults ── */
.btr-mobile-cards { display: none; }
.btr-desktop-table { display: table; }

/* ── Responsive ── */
@media (max-width: 768px) {
  .btr-drawer      { width: 100% !important; right: -100% !important; max-width: 100%; }
  .btr-view-drawer { width: 100% !important; right: -100% !important; max-width: 100%; }
  .btr-drawer.open,
  .btr-view-drawer.open { right: 0 !important; }
  .btr-desktop-table { display: none !important; }
  .btr-mobile-cards { display: flex; flex-direction: column; gap: 0; background: #f8fafc; }
  .btr-mobile-card { background: #fff; border-bottom: 1px solid #e5e7eb; padding: 12px 14px; cursor: pointer; transition: background .12s; }
  .btr-mobile-card:active { background: #f8f9fc; }
  .btr-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .btr-mc-docno { font-size: 12px; font-weight: 700; color: #2563eb; }
  .btr-mc-mid { font-size: 13.5px; font-weight: 600; color: #1a1d23; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .btr-mc-meta { display: flex; justify-content: space-between; font-size: 12px; color: #868e96; }
  .btr-mc-amount { font-weight: 700; color: #1a1d23; }
  .btr-mc--skeleton { pointer-events: none; }
  .btr-mc-shimmer { border-radius: 6px; background: linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size: 200% 100%; animation: btr-mc-sh 1.4s infinite; }
  @keyframes btr-mc-sh { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
  .btr-mc-empty { text-align: center; padding: 32px 16px; color: #868e96; font-size: 13px; }
}

@media (max-width: 480px) {
  .btr-page { padding: 12px; gap: 12px; }
  .btr-search-wrap { min-width: 0; flex: 1 1 auto; }
  .btr-fields-grid { grid-template-columns: 1fr !important; }
  .btr-meta-grid   { grid-template-columns: 1fr !important; }
  .btr-dh-amt-val  { font-size: 20px; }
}
</style>