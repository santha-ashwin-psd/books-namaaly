<template>
  <div class="bt-page">
    <div class="bt-actions">
      <div class="bt-search-wrap">
        <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
        <input v-model="search" placeholder="Search transactions…" class="bt-search-input" />
      </div>
      <div class="bt-pills">
        <button v-for="t in tabs" :key="t.key" class="bt-pill" :class="{active:activeTab===t.key}" @click="activeTab=t.key">{{ t.label }}</button>
      </div>
      <div style="display:flex;gap:8px;margin-left:auto;align-items:center">
        <select v-model="selectedAccount" class="bt-select" @change="load">
          <option value="">All Accounts</option>
          <option v-for="a in bankAccounts" :key="a.name" :value="a.name">{{ a.account_name||a.name }}</option>
        </select>
        <label class="bt-import-btn" :class="{disabled:!selectedAccount||importing}" :title="!selectedAccount?'Pick a Bank Account first':''">
          {{ importing ? 'Importing…' : '📥 Import CSV/Excel' }}
          <input type="file" accept=".csv,.xlsx,.xls,text/csv,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" style="display:none" :disabled="!selectedAccount||importing" @change="onFileSelected"/>
        </label>
        <button class="bt-btn-ghost" @click="showFormatGuide=true" title="What format should my file be in?">
          <span v-html="icon('info',14)"></span> Format Guide
        </button>
        <button class="bt-btn-ghost" @click="load"><span v-html="icon('refresh',14)"></span></button>
      </div>
    </div>

    <div v-if="selected.size" class="bt-bulkbar">
      <span>{{ selected.size }} selected</span>
      <button class="bt-btn-primary" :disabled="reconciling" @click="reconcileSelected">
        {{ reconciling ? 'Reconciling…' : 'Mark as Reconciled' }}
      </button>
      <button class="bt-btn-ghost" @click="selected.clear()">Clear</button>
    </div>

    <div v-if="importResult" class="bt-import-result" :class="importResult.ok?'ok':'err'">
      <span v-if="importResult.ok">✓ Imported {{ importResult.count }} transaction(s), auto-reconciled {{ importResult.autoReconciled || 0 }} by date+amount match. Skipped {{ importResult.skipped }}.</span>
      <span v-else>✗ {{ importResult.error }}</span>
      <button class="bt-import-close" @click="importResult=null">×</button>
    </div>

    <SummaryStrip v-if="!loading" :cards="[
      { label: 'Deposits', tone: 'success', value: fmtCur(summaryDeposit), valueClass: 'green' },
      { label: 'Withdrawals', tone: 'danger', value: fmtCur(summaryWithdrawal), valueClass: 'red' },
      { label: 'Unreconciled', tone: counts.unreconciled>0?'warn':'default', value: counts.unreconciled, valueClass: counts.unreconciled>0?'orange':'' },
      { label: 'Total', tone: 'default', value: filtered.length },
    ]" />

    <div class="bt-card">
      <table class="bt-table bt-desktop-table">
        <thead>
          <tr>
            <th class="bt-checkcol"><input type="checkbox" :checked="allSelected" @click.stop @change="toggleSelectAll" /></th>
            <th @click="sort('date')" class="sortable">Date <span v-html="sortArrow('date')"></span></th>
            <th @click="sort('bank_account')" class="sortable">Account <span v-html="sortArrow('bank_account')"></span></th>
            <th @click="sort('description')" class="sortable">Description <span v-html="sortArrow('description')"></span></th>
            <th @click="sort('reference_number')" class="sortable">Reference <span v-html="sortArrow('reference_number')"></span></th>
            <th>Status</th>
            <th @click="sort('deposit')" class="sortable ta-r">Deposit <span v-html="sortArrow('deposit')"></span></th>
            <th @click="sort('withdrawal')" class="sortable ta-r">Withdrawal <span v-html="sortArrow('withdrawal')"></span></th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 8" :key="n"><td colspan="8"><div class="bt-shimmer"></div></td></tr>
          </template>
          <template v-else>
            <tr v-for="t in paged" :key="t.name" class="bt-row" :class="{'bt-row--reconciled':t.status==='Reconciled'}" @click="openView(t)">
              <td class="bt-checkcol" @click.stop>
                <input type="checkbox" :checked="selected.has(t.name)" :disabled="t.status==='Reconciled'" @change="toggleSelect(t.name)" />
              </td>
              <td class="mono-sm">{{ fmtDate(t.date) }}</td>
              <td class="text-muted">{{ t.bank_account||'—' }}</td>
              <td class="bt-description">{{ t.description || '—' }}</td>
              <td class="mono-sm text-muted">{{ t.reference_number||'—' }}</td>
              <td><span class="bt-badge" :class="t.status==='Reconciled'?'badge-green':t.status==='Unreconciled'?'badge-orange':'badge-grey'">{{ t.status||'Unreconciled' }}</span></td>
              <td class="ta-r mono-sm green">{{ flt(t.deposit)>0 ? fmtCur(t.deposit) : '—' }}</td>
              <td class="ta-r mono-sm red">{{ flt(t.withdrawal)>0 ? fmtCur(t.withdrawal) : '—' }}</td>
            </tr>
            <tr v-if="!sorted.length"><td colspan="8" class="bt-empty">No transactions found</td></tr>
          </template>
        </tbody>
      </table>

      <!-- Mobile cards (shown at ≤768px) -->
      <div class="bt-mobile-cards">
        <template v-if="loading">
          <div v-for="n in 5" :key="n" class="bt-mobile-card bt-mc--skeleton">
            <div class="bt-mc-shimmer" style="height:13px;width:55%;margin-bottom:8px"></div>
            <div class="bt-mc-shimmer" style="height:11px;width:40%;margin-bottom:6px"></div>
            <div class="bt-mc-shimmer" style="height:11px;width:65%"></div>
          </div>
        </template>
        <div v-else-if="!sorted.length" class="bt-mc-empty">
          <div style="font-size:32px;margin-bottom:8px">🏦</div>
          <div>No transactions found</div>
        </div>
        <template v-else>
          <div v-for="t in paged" :key="t.name" class="bt-mobile-card" @click="openView(t)">
            <div class="bt-mc-top">
              <span style="display:flex;align-items:center;gap:8px">
                <input type="checkbox" :checked="selected.has(t.name)" :disabled="t.status==='Reconciled'" @click.stop @change="toggleSelect(t.name)" />
                <span class="bt-mc-date">{{ fmtDate(t.date) }}</span>
              </span>
              <span class="bt-badge" :class="t.status==='Reconciled'?'badge-green':t.status==='Unreconciled'?'badge-orange':'badge-grey'">{{ t.status||'Unreconciled' }}</span>
            </div>
            <div class="bt-mc-mid">{{ t.description || '—' }}</div>
            <div class="bt-mc-meta">
              <span>{{ t.bank_account || '—' }}</span>
              <span>
                <span v-if="flt(t.deposit)>0" class="bt-mc-dep">+{{ fmtCur(t.deposit) }}</span>
                <span v-else-if="flt(t.withdrawal)>0" class="bt-mc-wd">-{{ fmtCur(t.withdrawal) }}</span>
                <span v-else>—</span>
              </span>
            </div>
          </div>
        </template>
      </div>
    </div>

    <div v-if="!loading && sorted.length" style="padding:4px 0 0">
      <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="sorted.length" />
    </div>

    <!-- View -->
    <div v-if="viewOpen" class="bt-overlay" @click.self="viewOpen=false"></div>
    <div class="bt-drawer" :class="{open:viewOpen}">
      <template v-if="viewDoc">
        <div class="bt-dheader">
          <button class="bt-dclose" @click="viewOpen=false"><span v-html="icon('x',16)"></span></button>
          <div class="bt-dh-top">
            <div class="bt-dh-ico"><span v-html="icon('ledger',20)"></span></div>
            <div>
              <div class="bt-dh-title">Transaction Details</div>
              <div class="bt-dh-sub">{{ viewDoc.bank_account||'—' }} · {{ fmtDate(viewDoc.date) }}</div>
            </div>
            <span class="bt-badge" :class="viewDoc.status==='Reconciled'?'badge-green':'badge-orange'">{{ viewDoc.status||'Unreconciled' }}</span>
          </div>
          <div class="bt-dh-amount">
            <div class="bt-dh-amt-lbl">{{ flt(viewDoc.deposit)>0 ? 'Deposit' : 'Withdrawal' }}</div>
            <div class="bt-dh-amt-val" :class="flt(viewDoc.deposit)>0?'pos':'neg'">
              {{ flt(viewDoc.deposit)>0 ? fmtCur(viewDoc.deposit) : '-'+fmtCur(viewDoc.withdrawal) }}
            </div>
          </div>
        </div>
        <div class="bt-dbody">
          <div class="bt-section-hdr"><span v-html="icon('info',13)"></span> Details</div>
          <div class="bt-meta-grid">
            <div><div class="bt-meta-lbl">Date</div><div class="mono-sm">{{ fmtDate(viewDoc.date) }}</div></div>
            <div><div class="bt-meta-lbl">Bank Account</div><div>{{ viewDoc.bank_account||'—' }}</div></div>
            <div><div class="bt-meta-lbl">Deposit</div><div class="mono-sm green">{{ flt(viewDoc.deposit)>0?fmtCur(viewDoc.deposit):'—' }}</div></div>
            <div><div class="bt-meta-lbl">Withdrawal</div><div class="mono-sm red">{{ flt(viewDoc.withdrawal)>0?fmtCur(viewDoc.withdrawal):'—' }}</div></div>
            <div><div class="bt-meta-lbl">Reference</div><div class="mono-sm">{{ viewDoc.reference_number||'—' }}</div></div>
            <div><div class="bt-meta-lbl">Status</div><div><span class="bt-badge" :class="viewDoc.status==='Reconciled'?'badge-green':'badge-orange'">{{ viewDoc.status||'Unreconciled' }}</span></div></div>
          </div>
          <div class="bt-section-hdr"><span v-html="icon('file',13)"></span> Description</div>
          <div class="bt-desc">{{ viewDoc.description||'—' }}</div>
        </div>
        <div class="bt-dfooter">
          <button v-if="viewDoc.status!=='Reconciled'" class="bt-btn-primary" :disabled="reconciling" @click="reconcileOne(viewDoc)">
            {{ reconciling ? 'Reconciling…' : 'Mark as Reconciled' }}
          </button>
          <button class="bt-btn-ghost" @click="viewOpen=false">Close</button>
        </div>
      </template>
    </div>

    <!-- Import Format Guide modal -->
    <div v-if="showFormatGuide" class="bt-overlay" @click.self="showFormatGuide=false">
      <div class="bt-drawer bt-fmt-modal open">
        <div class="bt-dheader">
          <button class="bt-dclose" @click="showFormatGuide=false"><span v-html="icon('x',16)"></span></button>
          <div class="bt-dh-top">
            <div class="bt-dh-ico"><span v-html="icon('info',20)"></span></div>
            <div>
              <div class="bt-dh-title">Import File Format</div>
              <div class="bt-dh-sub">Accepted: .csv, .xlsx, .xls</div>
            </div>
          </div>
        </div>
        <div class="bt-dbody">
          <div class="bt-section-hdr"><span v-html="icon('file',13)"></span> Required / recognised columns</div>
          <table class="bt-fmt-table">
            <thead><tr><th>Column</th><th>Also accepted as</th><th>Required</th><th>Notes</th></tr></thead>
            <tbody>
              <tr><td class="mono-sm">Date</td><td class="text-muted">Transaction Date, Posting Date</td><td>Yes</td><td>YYYY-MM-DD, DD/MM/YYYY, or an Excel date cell</td></tr>
              <tr><td class="mono-sm">Description</td><td class="text-muted">Narration, Particulars</td><td>No</td><td>Free text, truncated to 140 chars</td></tr>
              <tr><td class="mono-sm">Debit</td><td class="text-muted">—</td><td>One of Debit/Credit, or Amount+Type</td><td>Money received into the bank (deposit)</td></tr>
              <tr><td class="mono-sm">Credit</td><td class="text-muted">—</td><td>One of Debit/Credit, or Amount+Type</td><td>Money paid out of the bank (withdrawal)</td></tr>
              <tr><td class="mono-sm">Amount + Type</td><td class="text-muted">Type / Dr/Cr column with D or C</td><td>Alternative to Debit/Credit</td><td>e.g. Amount=5000, Type=Credit</td></tr>
              <tr><td class="mono-sm">Reference</td><td class="text-muted">Reference Number, Ref No</td><td>No</td><td>Cheque/UTR/transaction ref, truncated to 80 chars</td></tr>
            </tbody>
          </table>
          <div class="bt-fmt-hint">
            Column names are matched case-insensitively and the exact header order doesn't matter — extra columns are ignored.
            Give either <strong>Debit</strong>/<strong>Credit</strong> columns, <em>or</em> an <strong>Amount</strong> column together with a <strong>Type</strong> (Debit/Credit or D/C).
          </div>

          <div class="bt-section-hdr" style="margin-top:18px"><span v-html="icon('eye',13)"></span> Example</div>
          <table class="bt-fmt-table">
            <thead><tr><th>Date</th><th>Description</th><th>Reference</th><th>Debit</th><th>Credit</th></tr></thead>
            <tbody>
              <tr><td class="mono-sm">2026-06-01</td><td>Customer payment received</td><td class="mono-sm">UTR12345</td><td class="mono-sm green">15000</td><td class="mono-sm"></td></tr>
              <tr><td class="mono-sm">2026-06-03</td><td>Office rent</td><td class="mono-sm">CHQ0091</td><td class="mono-sm"></td><td class="mono-sm red">8000</td></tr>
              <tr><td class="mono-sm">2026-06-05</td><td>Vendor payment</td><td class="mono-sm">NEFT7788</td><td class="mono-sm"></td><td class="mono-sm red">4200</td></tr>
            </tbody>
          </table>

          <div class="bt-fmt-hint" style="margin-top:14px">
            After import, each row is checked against existing Payment Entries for an exact <strong>date + amount</strong> match.
            An unambiguous match is auto-marked <strong>Reconciled</strong>; anything else stays Unreconciled for manual matching via "🔍 Suggest".
          </div>
        </div>
        <div class="bt-dfooter">
          <button class="bt-btn-ghost" @click="downloadSampleTemplate('csv')">
            <span v-html="icon('file',13)"></span> Download Sample CSV
          </button>
          <button class="bt-btn-ghost" @click="downloadSampleTemplate('xlsx')" :disabled="downloadingSample">
            <span v-html="icon('file',13)"></span> {{ downloadingSample ? 'Preparing…' : 'Download Sample Excel' }}
          </button>
          <button class="bt-btn-primary" @click="showFormatGuide=false">Got it</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { apiList, apiPOST, resolveCompany } from "../api/client.js";

// Import format guide + sample templates
const showFormatGuide = ref(false);
const downloadingSample = ref(false);
const SAMPLE_ROWS = [
  { Date: "2026-06-01", Description: "Customer payment received", Reference: "UTR12345", Debit: 15000, Credit: "" },
  { Date: "2026-06-03", Description: "Office rent", Reference: "CHQ0091", Debit: "", Credit: 8000 },
  { Date: "2026-06-05", Description: "Vendor payment", Reference: "NEFT7788", Debit: "", Credit: 4200 },
];

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

function downloadSampleTemplate(kind) {
  const headers = ["Date", "Description", "Reference", "Debit", "Credit"];
  if (kind === "csv") {
    const lines = [headers.join(",")];
    for (const row of SAMPLE_ROWS) {
      lines.push(headers.map(h => row[h] ?? "").join(","));
    }
    const blob = new Blob(["\uFEFF" + lines.join("\r\n")], { type: "text/csv;charset=utf-8;" });
    downloadBlob(blob, "bank_statement_sample.csv");
    return;
  }
  // xlsx
  downloadingSample.value = true;
  loadXlsxLib().then(XLSX => {
    const ws = XLSX.utils.json_to_sheet(SAMPLE_ROWS, { header: headers });
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Statement");
    const out = XLSX.write(wb, { bookType: "xlsx", type: "array" });
    downloadBlob(new Blob([out], { type: "application/octet-stream" }), "bank_statement_sample.xlsx");
  }).catch(() => {
    importResult.value = { ok: false, error: "Could not prepare sample Excel file" };
  }).finally(() => {
    downloadingSample.value = false;
  });
}

// CSV / Excel import
const importing = ref(false);
const importResult = ref(null);
let _xlsxLib = null;
async function loadXlsxLib() {
  if (_xlsxLib) return _xlsxLib;
  _xlsxLib = await import(/* @vite-ignore */ "https://cdn.jsdelivr.net/npm/xlsx@0.18.5/+esm");
  return _xlsxLib;
}

function isExcelFile(f) {
  const name = (f.name || "").toLowerCase();
  return name.endsWith(".xlsx") || name.endsWith(".xls") ||
    f.type === "application/vnd.ms-excel" ||
    f.type === "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
}

async function fileToCsvText(f) {
  if (!isExcelFile(f)) {
    return await f.text();
  }
  // Excel: parse first sheet client-side and convert to CSV so the backend
  // import endpoint (which understands CSV columns date/description/debit/credit)
  // can be reused unchanged.
  const XLSX = await loadXlsxLib();
  const buf = await f.arrayBuffer();
  const wb = XLSX.read(buf, { type: "array", cellDates: true });
  const sheetName = wb.SheetNames[0];
  const sheet = wb.Sheets[sheetName];
  // dateNF ensures date cells convert to ISO text instead of Excel serials.
  return XLSX.utils.sheet_to_csv(sheet, { dateNF: "yyyy-mm-dd" });
}

async function onFileSelected(e) {
  const f = e.target.files?.[0];
  if (!f) return;
  if (!selectedAccount.value) {
    importResult.value = { ok: false, error: "Pick a Bank Account first" };
    e.target.value = "";
    return;
  }
  importing.value = true;
  importResult.value = null;
  try {
    const csvText = await fileToCsvText(f);
    const r = await apiPOST("zoho_books_clone.api.docs.import_bank_statement_csv", {
      bank_account: selectedAccount.value,
      csv_data: csvText,
    });
    importResult.value = {
      ok: true,
      count: r?.count || 0,
      skipped: r?.skipped || 0,
      autoReconciled: r?.auto_reconciled || 0,
    };
    if (r?.auto_reconciled) {
      toast.success(`${r.auto_reconciled} transaction(s) auto-reconciled by date + amount match`);
    }
    await load();
  } catch (err) {
    importResult.value = { ok: false, error: err.message || "Import failed" };
  } finally {
    importing.value = false;
    e.target.value = ""; // reset input so the same file can be re-selected
  }
}
import { useToast } from "../composables/useToast.js";
import { useRoute } from "vue-router";
import { icon } from "../utils/icons.js";
import { flt, fmtDate } from "../utils/format.js";
import SummaryStrip from "../components/SummaryStrip.vue";
import Pagination from "../components/Pagination.vue";
import { usePagination } from "../composables/usePagination.js";

const { toast } = useToast();
const route = useRoute();
const activeTab=ref("all");
const tabs=[{key:"all",label:"All"},{key:"Unreconciled",label:"Unreconciled"},{key:"Reconciled",label:"Reconciled"}];
const list=ref([]),loading=ref(false),search=ref(""),selectedAccount=ref("");
const bankAccounts=ref([]),viewOpen=ref(false),viewDoc=ref(null);
const sortCol=ref("date"),sortDir=ref("desc");
const selected=ref(new Set());
const reconciling=ref(false);

async function load(){
  loading.value=true;
  try{
    const co=await resolveCompany();
    if(!bankAccounts.value.length){bankAccounts.value=await apiList("Bank Account",{fields:["name","account_name"],filters:[["company","=",co]],limit:50});}
    const whNames=bankAccounts.value.map(a=>a.name);
    if(!whNames.length&&!selectedAccount.value){list.value=[];loading.value=false;return;}
    const filters=whNames.length?[["bank_account","in",whNames]]:[];
    if(selectedAccount.value)filters.push(["bank_account","=",selectedAccount.value]);
    // Bank Transaction uses `debit`/`credit` columns (not deposit/withdrawal).
    // Pull both then alias for the legacy template.
    const raw=await apiList("Bank Transaction",{
      fields:["name","date","bank_account","description","reference_number","debit","credit","status","currency"],
      filters, limit:300, order: "date desc, creation desc"
    });
    list.value = raw.map(t => ({
      ...t,
      deposit:    flt(t.credit || 0),   // bank-statement convention: credit = money IN
      withdrawal: flt(t.debit  || 0),   // debit = money OUT
    }));
  }catch(e){toast.error(e.message||"Failed to load transactions");}
  finally{loading.value=false;}
}

const filtered=computed(()=>{let r=list.value;if(activeTab.value!=="all")r=r.filter(t=>t.status===activeTab.value);if(search.value.trim()){const q=search.value.toLowerCase();r=r.filter(t=>(t.description||"").toLowerCase().includes(q)||(t.reference_number||"").toLowerCase().includes(q));}return r;});
const sorted=computed(()=>{const col=sortCol.value;return[...filtered.value].sort((a,b)=>{const av=a[col]??"",bv=b[col]??"";const c=typeof av==="number"?av-bv:String(av).localeCompare(String(bv));return sortDir.value==="asc"?c:-c;});});
function sort(col){if(sortCol.value===col)sortDir.value=sortDir.value==="asc"?"desc":"asc";else{sortCol.value=col;sortDir.value="asc";}}
function sortArrow(col){if(sortCol.value!==col)return'<span style="color:#d1d5db">⇅</span>';return sortDir.value==="asc"?"↑":"↓";}
const summaryDeposit=computed(()=>filtered.value.reduce((s,t)=>s+flt(t.deposit),0));
const summaryWithdrawal=computed(()=>filtered.value.reduce((s,t)=>s+flt(t.withdrawal),0));
const counts=computed(()=>({unreconciled:list.value.filter(t=>t.status!=="Reconciled").length}));
function fmtCur(v){return new Intl.NumberFormat("en-IN",{style:"currency",currency:"INR",minimumFractionDigits:2}).format(flt(v));}
function openView(t){viewDoc.value=t;viewOpen.value=true;}

const { page, pageSize, paged } = usePagination(sorted, { storageKey: "bank-transactions" });

const reconcilableNames=computed(()=>paged.value.filter(t=>t.status!=="Reconciled").map(t=>t.name));
const allSelected=computed(()=>reconcilableNames.value.length>0 && reconcilableNames.value.every(n=>selected.value.has(n)));
function toggleSelect(name){
  const s=new Set(selected.value);
  if(s.has(name))s.delete(name);else s.add(name);
  selected.value=s;
}
function toggleSelectAll(){
  if(allSelected.value){selected.value=new Set();}
  else{selected.value=new Set(reconcilableNames.value);}
}
async function reconcileOne(t){
  if(!t||t.status==="Reconciled")return;
  reconciling.value=true;
  try{
    await apiPOST("zoho_books_clone.api.banking.mark_transaction_reconciled",{bank_transaction:t.name});
    t.status="Reconciled";
    selected.value.delete(t.name);
    toast.success(`${t.name} marked as Reconciled`);
  }catch(e){toast.error(e.message||"Failed to reconcile transaction");}
  finally{reconciling.value=false;}
}
async function reconcileSelected(){
  const names=[...selected.value];
  if(!names.length)return;
  const acc=selectedAccount.value || list.value.find(t=>names.includes(t.name))?.bank_account;
  reconciling.value=true;
  try{
    await apiPOST("zoho_books_clone.api.banking.reconcile_transactions",{
      bank_account: acc,
      transaction_names: JSON.stringify(names),
    });
    list.value.forEach(t=>{if(names.includes(t.name))t.status="Reconciled";});
    selected.value=new Set();
    toast.success(`${names.length} transaction(s) marked as Reconciled`);
  }catch(e){toast.error(e.message||"Failed to reconcile transactions");}
  finally{reconciling.value=false;}
}
onMounted(()=>{if(route.query.account)selectedAccount.value=String(route.query.account);load();});
</script>

<style scoped>
.bt-page{display:flex;flex-direction:column;gap:16px;padding:24px;}
.bt-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
.bt-search-wrap{display:flex;align-items:center;gap:8px;background:#ffffff;border-radius:8px;padding:6px 12px;min-width:220px;}
.bt-search-input{border:none;background:transparent;outline:none;font:inherit;color:#111827;width:100%;font-size:13px;}
.bt-pills{display:flex;gap:6px;}
.bt-pill{padding:6px 14px;border-radius:20px;font-size:12.5px;font-weight:600;border:1px solid #e5e7eb;background:#fff;color:#6b7280;cursor:pointer;font-family:inherit;}
.bt-pill.active{background:#eff6ff;border-color:#2563eb;color:#2563eb;}
.bt-select{border:1px solid #e5e7eb;border-radius:8px;padding:7px 10px;font:inherit;font-size:13px;outline:none;background:#fff;color:#111827;cursor:pointer;}
.bt-btn-ghost{display:inline-flex;align-items:center;gap:6px;background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;padding:8px 12px;font-size:13px;color:#374151;cursor:pointer;}
.bt-btn-ghost:hover{background:#f9fafb;}
.bt-btn-primary{display:inline-flex;align-items:center;gap:6px;background:#2563eb;border:1px solid #2563eb;color:#fff;border-radius:8px;padding:8px 14px;font-size:13px;font-weight:600;cursor:pointer;}
.bt-btn-primary:hover:not(:disabled){background:#1d4ed8;}
.bt-btn-primary:disabled{opacity:.6;cursor:not-allowed;}
.bt-bulkbar{display:flex;align-items:center;gap:10px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:8px 14px;font-size:13px;color:#1d4ed8;font-weight:600;}
.bt-checkcol{width:34px;text-align:center;}
.bt-row--reconciled{opacity:.7;}
.bt-import-btn{display:inline-flex;align-items:center;gap:6px;background:#eff6ff;border:1px solid #93c5fd;color:#1d4ed8;border-radius:8px;padding:7px 14px;font-size:13px;font-weight:600;cursor:pointer;}
.bt-import-btn:hover:not(.disabled){background:#dbeafe;}
.bt-import-btn.disabled{opacity:.5;cursor:not-allowed;}
.bt-import-result{display:flex;align-items:center;justify-content:space-between;padding:10px 14px;border-radius:8px;font-size:12.5px;font-weight:600;margin-top:-4px;}
.bt-import-result.ok{background:#dcfce7;color:#16a34a;border:1px solid #86efac;}
.bt-import-result.err{background:#fee2e2;color:#dc2626;border:1px solid #fca5a5;}
.bt-import-close{background:transparent;border:none;color:inherit;cursor:pointer;font-size:18px;line-height:1;padding:0 4px;}
.bt-import-close:hover{opacity:.7;}
.green{color:#16a34a!important;}.red{color:#dc2626!important;}.orange{color:#ea580c!important;}
.bt-card{background:#fff;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;}
.bt-table{width:100%;border-collapse:collapse;font-size:13px;}
.bt-table th{background:#f9fafb;border-bottom:1px solid #e5e7eb;padding:10px 12px;font-size:11.5px;font-weight:600;color:#374151;text-align:left;white-space:nowrap;text-transform:uppercase;}
.bt-table th.sortable{cursor:pointer;user-select:none;}.bt-table th.sortable:hover{color:#2563eb;}
.ta-r{text-align:right!important;}
.bt-row td{padding:10px 12px;border-bottom:1px solid #f3f4f6;vertical-align:middle;cursor:pointer;}
.bt-row:last-child td{border-bottom:none;}.bt-row:hover td{background:#f9fafb;}
.mono-sm{font-size:13px;}.text-muted{color:#6b7280;}
.bt-badge{display:inline-flex;align-items:center;padding:2px 8px;border-radius:10px;font-size:11.5px;font-weight:600;}
.badge-green{background:#dcfce7;color:#16a34a;}.badge-orange{background:#fff7ed;color:#ea580c;}.badge-grey{background:#f3f4f6;color:#6b7280;}
.bt-empty{text-align:center;color:#9ca3af;padding:48px!important;cursor:default!important;}
.bt-shimmer{height:13px;background:linear-gradient(90deg,#f3f4f6 25%,#e5e7eb 50%,#f3f4f6 75%);border-radius:4px;animation:shimmer 1.2s infinite;background-size:200% 100%;}
@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}
.bt-overlay{position:fixed;inset:0;background:rgba(15,23,42,.28);z-index:40;}
.bt-drawer{position:fixed;top:0;right:-440px;bottom:0;width:440px;max-width:96vw;background:#fff;border-left:1px solid #e5e7eb;box-shadow:-8px 0 28px rgba(15,23,42,.12);z-index:50;display:flex;flex-direction:column;transition:right .24s ease;}
.bt-drawer.open{right:0;}
.bt-dheader{position:relative;flex-shrink:0;padding:20px;border-bottom:1px solid #e5e7eb;background:linear-gradient(135deg,#eff6ff 0%,#dbeafe 100%);}
.bt-dclose{position:absolute;top:12px;right:12px;background:transparent;border:none;cursor:pointer;color:#475569;display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border-radius:8px;}
.bt-dclose:hover{background:rgba(255,255,255,.6);color:#0f172a;}
.bt-dh-top{display:flex;align-items:center;gap:13px;padding-right:36px;}
.bt-dh-ico{width:42px;height:42px;background:#fff;border-radius:11px;display:flex;align-items:center;justify-content:center;color:#2563eb;flex-shrink:0;box-shadow:0 1px 3px rgba(15,23,42,.08);}
.bt-dh-title{font-size:15px;font-weight:700;color:#0f172a;}
.bt-dh-sub{font-size:12px;color:#475569;margin-top:1px;}
.bt-dh-top .bt-badge{margin-left:auto;}
.bt-dh-amount{margin-top:16px;}
.bt-dh-amt-lbl{font-size:10.5px;color:#64748b;text-transform:uppercase;letter-spacing:.05em;font-weight:600;}
.bt-dh-amt-val{font-size:26px;font-weight:800;letter-spacing:-.01em;margin-top:2px;}
.bt-dh-amt-val.pos{color:#16a34a;}.bt-dh-amt-val.neg{color:#dc2626;}
.bt-dbody{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:12px;}
.bt-section-hdr{display:flex;align-items:center;gap:8px;font-size:11.5px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:#0f172a;margin-top:4px;}
.bt-section-hdr span{color:#2563eb;display:inline-flex;}
.bt-meta-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
.bt-meta-lbl{font-size:10.5px;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;margin-bottom:2px;font-weight:600;}
.bt-desc{font-size:13px;color:#334155;line-height:1.5;background:#f8fafc;border:1px solid #eef2f7;border-radius:10px;padding:12px 14px;word-break: break-word;}
.bt-dfooter{display:flex;align-items:center;justify-content:flex-end;gap:8px;padding:14px 20px;border-top:1px solid #e5e7eb;flex-shrink:0;}

/* ── Mobile card defaults ── */
.bt-mobile-cards { display: none; }
.bt-desktop-table { display: table; }
.bt-description {
  max-width: 350px; /* adjust as needed */
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* ── Responsive ── */
@media (max-width: 768px) {
  .bt-drawer { width: 100% !important; right: -100% !important; max-width: 100%; }
  .bt-drawer.open { right: 0 !important; }
  .bt-desktop-table { display: none !important; }
  .bt-mobile-cards { display: flex; flex-direction: column; gap: 0; background: #f8fafc; }
  .bt-mobile-card { background: #fff; border-bottom: 1px solid #e5e7eb; padding: 12px 14px; cursor: pointer; transition: background .12s; }
  .bt-mobile-card:active { background: #f8f9fc; }
  .bt-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .bt-mc-date { font-size: 12px; font-weight: 700; color: #2563eb; }
  .bt-mc-mid { font-size: 13.5px; font-weight: 600; color: #1a1d23; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .bt-mc-meta { display: flex; justify-content: space-between; font-size: 12px; color: #868e96; }
  .bt-mc-dep { color: #16a34a; font-weight: 700; }
  .bt-mc-wd  { color: #dc2626; font-weight: 700; }
  .bt-mc--skeleton { pointer-events: none; }
  .bt-mc-shimmer { border-radius: 6px; background: linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size: 200% 100%; animation: bt-mc-sh 1.4s infinite; }
  @keyframes bt-mc-sh { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
  .bt-mc-empty { text-align: center; padding: 32px 16px; color: #868e96; font-size: 13px; }
}

@media (max-width: 480px) {
  .bt-page { padding: 12px; gap: 12px; }
  .bt-search-wrap { min-width: 0; flex: 1 1 auto; }
  .bt-pills { flex-wrap: wrap; gap: 4px; }
  .bt-meta-grid { grid-template-columns: 1fr !important; }
  .bt-dh-amt-val { font-size: 20px; }
}

/* Import format-guide modal (wider than the standard side drawer) */
.bt-fmt-modal { width: 640px; right: -680px; }
.bt-fmt-modal.open { right: 0; }
.bt-fmt-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.bt-fmt-table th { background: #f9fafb; border-bottom: 1px solid #e5e7eb; padding: 8px 10px; font-size: 11px; font-weight: 700; color: #374151; text-align: left; text-transform: uppercase; }
.bt-fmt-table td { padding: 7px 10px; border-bottom: 1px solid #f3f4f6; vertical-align: top; }
.bt-fmt-table tr:last-child td { border-bottom: none; }
.bt-fmt-hint { font-size: 12.5px; color: #475569; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px; line-height: 1.55; }
.bt-dfooter .bt-btn-ghost[disabled] { opacity: .5; cursor: not-allowed; }
@media (max-width: 720px) {
  .bt-fmt-modal { width: 96vw; right: -100vw; }
}
</style>