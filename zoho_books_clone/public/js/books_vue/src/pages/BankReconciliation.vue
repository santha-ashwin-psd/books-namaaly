<template>
  <div class="br-page">
    <div class="br-actions">
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
        <select v-model="form.bank_account" class="br-select" style="min-width:220px">
          <option value="">— Select Bank Account —</option>
          <option v-for="a in bankAccounts" :key="a.name" :value="a.name">{{ a.account_name||a.name }}</option>
        </select>
        <input v-model="form.from_date" type="date" class="br-input" />
        <input v-model="form.to_date" type="date" class="br-input" />
        <button class="br-btn-primary" @click="load" :disabled="!form.bank_account">
          <span v-html="icon('refresh',13)"></span> Run
        </button>
      </div>
    </div>

    <SummaryStrip v-if="!loading && ran" :cards="[
      { label: 'Bank Statement Amount', tone: 'accent', value: fmtCur(summary.statementBalance) },
      { label: 'ERP Book Balance', tone: 'default', value: fmtCur(summary.systemBalance) },
      { label: 'Variance', tone: Math.abs(summary.diff)<0.01?'success':'danger', value: fmtCur(summary.diff), valueClass: Math.abs(summary.diff)<0.01?'green':'red' },
      { label: 'Unmatched', tone: summary.unmatched>0?'warn':'default', value: summary.unmatched, valueClass: summary.unmatched>0?'orange':'' },
    ]" />

    <div v-if="ran && !loading" class="br-toolbar">
      <div class="br-filter-pills">
        <button v-for="s in statusTabs" :key="s.key" class="br-fpill" :class="{active:statusFilter===s.key}" @click="statusFilter=s.key">
          {{ s.label }} <span class="br-fpill-count">{{ s.count }}</span>
        </button>
      </div>
      <div class="br-toolbar-right">
        <div class="br-search-wrap">
          <span v-html="icon('search',13)" style="color:#94a3b8;flex-shrink:0"></span>
          <input v-model="search" placeholder="Search statement…" class="br-search-input" />
        </div>
        <button class="br-btn-ghost" @click="exportCSV" :disabled="!displayRows.length">
          <span v-html="icon('download',14)"></span> Export
        </button>
      </div>
    </div>

    <div v-if="ran && selected.size>0" class="br-reconcile-bar">
      <span class="br-rb-count">{{ selected.size }} selected</span>
      <button class="br-rb-export" @click="exportCSV"><span v-html="icon('download',13)"></span> Export selected</button>
      <div class="br-rb-spacer"></div>
      <template v-if="selectedUnreconciled.length">
        <label style="font-size:13px;color:#374151">Clearance Date</label>
        <input v-model="clearanceDate" type="date" class="br-input" style="width:150px" />
        <button class="br-btn-primary" :disabled="reconciling||!clearanceDate||!$canEdit('banking')" :title="!$canEdit('banking') ? 'Read-only access' : ''" @click="markReconciled">
          <span v-html="icon('check',13)"></span> {{ reconciling?'Saving…':`Mark ${selectedUnreconciled.length} Reconciled` }}
        </button>
      </template>
      <span v-else class="br-rb-note">All selected rows are already reconciled</span>
      <button class="br-rb-clear" @click="selected=new Set()">Clear</button>
    </div>

    <div v-if="ran" class="br-section-title">Bank Transactions (Statement)</div>
    <div v-if="ran" class="br-card">
      <table class="br-table br-table--desktop">
        <thead>
          <tr>
            <th style="width:32px"><input type="checkbox" :checked="allSelected" @change="toggleSelectAll" /></th>
            <th>Date</th><th>Description</th><th>Reference</th>
            <th class="ta-r">Deposit</th><th class="ta-r">Withdrawal</th><th>Status</th>
            <th style="width:130px">Match</th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 5" :key="n"><td colspan="8"><div class="br-shimmer"></div></td></tr>
          </template>
          <template v-else>
            <template v-for="t in pagedRows" :key="t.name">
              <tr class="br-row">
                <td @click.stop><input type="checkbox" :checked="selected.has(t.name)" @change="toggleSelect(t.name)" /></td>
                <td class="mono-sm">{{ fmtDate(t.date) }}</td>
                <td class="br-description">{{ t.description || '—' }}</td>
                <td class="mono-sm text-muted">{{ t.reference_number||'—' }}</td>
                <td class="ta-r mono-sm green">{{ flt(t.deposit)>0?fmtCur(t.deposit):'—' }}</td>
                <td class="ta-r mono-sm red">{{ flt(t.withdrawal)>0?fmtCur(t.withdrawal):'—' }}</td>
                <td><span class="br-badge" :class="t.status==='Reconciled'?'badge-green':'badge-orange'">{{ t.status||'Unreconciled' }}</span></td>
                <td>
                  <button v-if="t.status!=='Reconciled'"
                    class="br-match-btn"
                    @click.stop="suggestMatches(t)"
                    :disabled="matchingFor===t.name">
                    {{ matchingFor===t.name ? '…' : '🔍 Suggest' }}
                  </button>
                </td>
              </tr>
              <tr v-if="suggestions[t.name]" class="br-suggest-row">
                <td colspan="8" style="padding:0">
                  <div class="br-suggest-panel">
                    <div style="font-size:12px;font-weight:600;color:#1e40af;margin-bottom:8px">
                      🤖 {{ suggestions[t.name].matches.length }} candidate payment{{ suggestions[t.name].matches.length===1?'':'s' }} for ₹{{ fmtCur(suggestions[t.name].bt_amount) }} ({{ suggestions[t.name].bt_direction==='in'?'received':'paid out' }})
                    </div>
                    <div v-if="!suggestions[t.name].matches.length" style="font-size:12.5px;color:#6b7280;padding:8px">No Payment Entries matched on amount + date. You can mark this row Reconciled manually if you reviewed it.</div>
                    <div v-for="m in suggestions[t.name].matches" :key="m.name" class="br-suggest-card">
                      <div class="br-suggest-meta">
                        <span class="br-num" @click.stop><DocLink doctype="Payment Entry" :name="m.name" /></span>
                        <span class="br-score" :style="`background:${m.score>=80?'#dcfce7':m.score>=50?'#fef3c7':'#fee2e2'};color:${m.score>=80?'#16a34a':m.score>=50?'#d97706':'#dc2626'}`">{{ m.score.toFixed(0) }}% confidence</span>
                      </div>
                      <div class="br-suggest-info">
                        <span>{{ m.party_name || m.party }} · {{ fmtDate(m.payment_date) }} · {{ m.mode_of_payment||'—' }}</span>
                      </div>
                      <div class="br-suggest-amt">{{ fmtCur(m.paid_amount) }}</div>
                      <button class="br-match-confirm" @click="confirmMatch(t, m)" :disabled="matchingFor===m.name || !$canEdit('banking')" :title="!$canEdit('banking') ? 'Read-only access' : ''">
                        {{ matchingFor===m.name ? '…' : '✓ Match' }}
                      </button>
                    </div>
                    <button class="br-suggest-close" @click="suggestions[t.name]=null">close</button>
                  </div>
                </td>
              </tr>
            </template>
            <tr v-if="!displayRows.length"><td colspan="8" class="br-empty">{{ transactions.length ? 'No transactions match this filter' : 'No transactions in this period' }}</td></tr>
          </template>
        </tbody>
      </table>

      <!-- Mobile cards -->
      <div class="br-cards--mobile">
        <div v-if="loading">
          <div v-for="n in 4" :key="n" class="br-card-shimmer"></div>
        </div>
        <template v-else-if="pagedRows.length">
          <div v-for="t in pagedRows" :key="t.name" class="br-card">
            <div class="br-card-header">
              <input type="checkbox" :checked="selected.has(t.name)" @change="toggleSelect(t.name)" class="br-card-chk" />
              <span class="br-card-date mono-sm">{{ fmtDate(t.date) }}</span>
              <span class="br-badge" :class="t.status==='Reconciled'?'badge-green':'badge-orange'">{{ t.status||'Unreconciled' }}</span>
            </div>
            <td
  class="br-description"
  :title="t.description" >{{ t.description || '—' }}</td>
            <div v-if="t.reference_number" class="br-card-ref mono-sm">Ref: {{ t.reference_number }}</div>
            <div class="br-card-amounts">
              <div v-if="flt(t.deposit)>0" class="br-card-amt-item">
                <span class="br-card-amt-lbl">Deposit</span>
                <span class="br-card-amt-val green">{{ fmtCur(t.deposit) }}</span>
              </div>
              <div v-if="flt(t.withdrawal)>0" class="br-card-amt-item">
                <span class="br-card-amt-lbl">Withdrawal</span>
                <span class="br-card-amt-val red">{{ fmtCur(t.withdrawal) }}</span>
              </div>
            </div>
            <div v-if="t.status!=='Reconciled'" class="br-card-actions">
              <button class="br-match-btn" @click.stop="suggestMatches(t)" :disabled="matchingFor===t.name">
                {{ matchingFor===t.name ? '…' : '🔍 Suggest Match' }}
              </button>
            </div>
            <div v-if="suggestions[t.name]" class="br-suggest-panel" style="margin-top:10px">
              <div style="font-size:12px;font-weight:600;color:#1e40af;margin-bottom:8px">
                🤖 {{ suggestions[t.name].matches.length }} candidate payment{{ suggestions[t.name].matches.length===1?'':'s' }} for ₹{{ fmtCur(suggestions[t.name].bt_amount) }} ({{ suggestions[t.name].bt_direction==='in'?'received':'paid out' }})
              </div>
              <div v-if="!suggestions[t.name].matches.length" style="font-size:12.5px;color:#6b7280;padding:8px">No Payment Entries matched on amount + date. You can mark this row Reconciled manually if you reviewed it.</div>
              <div v-for="m in suggestions[t.name].matches" :key="m.name" class="br-suggest-card">
                <div class="br-suggest-meta">
                  <span class="br-num" @click.stop><DocLink doctype="Payment Entry" :name="m.name" /></span>
                  <span class="br-score" :style="`background:${m.score>=80?'#dcfce7':m.score>=50?'#fef3c7':'#fee2e2'};color:${m.score>=80?'#16a34a':m.score>=50?'#d97706':'#dc2626'}`">{{ m.score.toFixed(0) }}% confidence</span>
                </div>
                <div class="br-suggest-info"><span>{{ m.party_name || m.party }} · {{ fmtDate(m.payment_date) }} · {{ m.mode_of_payment||'—' }}</span></div>
                <div class="br-suggest-amt">{{ fmtCur(m.paid_amount) }}</div>
                <button class="br-match-confirm" @click="confirmMatch(t, m)" :disabled="matchingFor===m.name || !$canEdit('banking')" :title="!$canEdit('banking') ? 'Read-only access' : ''">
                  {{ matchingFor===m.name ? '…' : '✓ Match' }}
                </button>
              </div>
              <button class="br-suggest-close" @click="suggestions[t.name]=null">close</button>
            </div>
          </div>
        </template>
        <div v-else class="br-empty" style="padding:32px 16px;text-align:center">
          {{ transactions.length ? 'No transactions match this filter' : 'No transactions in this period' }}
        </div>
      </div>
    </div>

    <div v-if="ran && !loading && displayRows.length" style="padding:4px 0 0">
      <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="displayRows.length" />
    </div>

    <div v-if="!ran" class="br-placeholder">
      <span v-html="icon('balance',40)" style="color:#d1d5db;display:block;margin:0 auto 16px"></span>
      <div style="font-weight:600;color:#374151;margin-bottom:6px">Bank Reconciliation</div>
      <div style="color:#9ca3af;font-size:13px">Select a bank account and date range, then click Run to view the reconciliation statement.</div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { apiList, apiGET, apiPOST, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { useRoute } from "vue-router";
import { icon } from "../utils/icons.js";
import { flt, fmtDate } from "../utils/format.js";
import SummaryStrip from "../components/SummaryStrip.vue";
import Pagination from "../components/Pagination.vue";
import { usePagination } from "../composables/usePagination.js";
import DocLink from "../components/DocLink.vue";

const { toast } = useToast();
const route = useRoute();
const bankAccounts=ref([]),transactions=ref([]),loading=ref(false),ran=ref(false);
const systemBalance=ref(0);
const selected=ref(new Set());
const search=ref(""), statusFilter=ref("all");
const clearanceDate=ref(new Date().toISOString().slice(0,10));
const reconciling=ref(false);
const now=new Date();
const firstOfMonth=new Date(now.getFullYear(),now.getMonth(),1).toISOString().slice(0,10);
const form=reactive({bank_account:"",from_date:firstOfMonth,to_date:now.toISOString().slice(0,10)});

async function loadAccounts(){try{const co=await resolveCompany();bankAccounts.value=await apiList("Bank Account",{fields:["name","account_name","is_default"],filters:[["company","=",co]],order:"is_default desc, account_name asc",limit:50});}catch{}}
async function load(){
  if(!form.bank_account)return;
  loading.value=true;ran.value=true;systemBalance.value=0;
  selected.value=new Set();
  try{
    // Use the consolidated backend endpoint — handles the GL Entry → General
    // Ledger Entry rename + the Bank Transaction debit/credit column naming.
    const res = await apiGET("zoho_books_clone.api.docs.get_bank_reconciliation", {
      bank_account: form.bank_account,
      from_date:    form.from_date,
      to_date:      form.to_date,
    });
    // Backend returns rows with debit/credit; alias for legacy template.
    transactions.value = (res?.bank_transactions || []).map(t => ({
      ...t,
      deposit:    flt(t.credit  || 0),
      withdrawal: flt(t.debit || 0),
    }));
    systemBalance.value = flt(res?.gl_balance || 0);
  }catch(e){toast.error(e.message||"Failed to load");}finally{loading.value=false;}
}
const summary=computed(()=>{
  const dep=transactions.value.reduce((s,t)=>s+flt(t.deposit),0);
  const wd=transactions.value.reduce((s,t)=>s+flt(t.withdrawal),0);
  const stmtBal=dep-wd;
  const unmatched=transactions.value.filter(t=>t.status!=="Reconciled").length;
  return{statementBalance:stmtBal,systemBalance:systemBalance.value,diff:systemBalance.value-stmtBal,unmatched};
});
function fmtCur(v){return new Intl.NumberFormat("en-IN",{style:"currency",currency:"INR",minimumFractionDigits:2}).format(flt(v));}

const statusTabs=computed(()=>{
  const recon=transactions.value.filter(t=>t.status==="Reconciled").length;
  return[
    {key:"all",label:"All",count:transactions.value.length},
    {key:"Unreconciled",label:"Unreconciled",count:transactions.value.length-recon},
    {key:"Reconciled",label:"Reconciled",count:recon},
  ];
});
const displayRows=computed(()=>{
  let r=transactions.value;
  if(statusFilter.value==="Reconciled")r=r.filter(t=>t.status==="Reconciled");
  else if(statusFilter.value==="Unreconciled")r=r.filter(t=>t.status!=="Reconciled");
  if(search.value.trim()){const q=search.value.toLowerCase();r=r.filter(t=>(t.description||"").toLowerCase().includes(q)||(t.reference_number||"").toLowerCase().includes(q));}
  return r;
});
// Selection/export act on the full filtered set (all pages); only the table
// rendering itself is paginated via `pagedRows`.
const { page, pageSize, paged: pagedRows } = usePagination(displayRows, { storageKey: "bank-reconciliation" });
// Selected rows that are still unreconciled — the only ones "Mark Reconciled" acts on.
const selectedUnreconciled=computed(()=>displayRows.value.filter(t=>t.status!=="Reconciled"&&selected.value.has(t.name)));

function toggleSelect(name){const s=new Set(selected.value);if(s.has(name))s.delete(name);else s.add(name);selected.value=s;}
const allSelected=computed(()=>displayRows.value.length>0&&displayRows.value.every(t=>selected.value.has(t.name)));
function toggleSelectAll(){if(allSelected.value){selected.value=new Set();}else{selected.value=new Set(displayRows.value.map(t=>t.name));}}

function exportCSV(){
  // Export the selected rows when any are ticked, otherwise the whole visible statement.
  const rows=selected.value.size?displayRows.value.filter(t=>selected.value.has(t.name)):displayRows.value;
  if(!rows.length)return;
  const esc=v=>{const s=v==null?"":String(v);return /[",\n]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s;};
  const lines=[["Date","Description","Reference","Deposit","Withdrawal","Status"].join(",")];
  for(const t of rows){
    lines.push([fmtDate(t.date),t.description||"",t.reference_number||"",flt(t.deposit)||0,flt(t.withdrawal)||0,t.status||"Unreconciled"].map(esc).join(","));
  }
  const blob=new Blob(["﻿"+lines.join("\r\n")],{type:"text/csv;charset=utf-8;"});
  const url=URL.createObjectURL(blob);
  const acc=(bankAccounts.value.find(x=>x.name===form.bank_account)?.account_name)||form.bank_account||"reconciliation";
  const a=document.createElement("a");
  a.href=url;
  a.download=`reconciliation_${acc}_${form.from_date}_to_${form.to_date}.csv`.replace(/\s+/g,"_");
  a.click();
  URL.revokeObjectURL(url);
  toast.success(`Exported ${rows.length} row(s)`);
}
async function markReconciled(){
  const names=selectedUnreconciled.value.map(t=>t.name);
  if(!names.length||!clearanceDate.value)return;
  reconciling.value=true;
  let ok=0;
  try{
    for(const name of names){
      try{
        await apiPOST("zoho_books_clone.api.docs.reconcile_bank_transaction",{bank_transaction_name:name},{module:"banking",action:"edit"});
        ok++;
      }catch{}
    }
    toast.success(`${ok} transaction(s) marked as reconciled`);
    await load();
  }catch(e){toast.error(e.message||"Failed to reconcile transactions");}
  finally{reconciling.value=false;}
}
// ── Auto-match suggestions ───────────────────────────────────────────────
const suggestions = reactive({});   // { bt_name: { matches, bt_amount, bt_direction } | null }
const matchingFor = ref("");

async function suggestMatches(t) {
  if (suggestions[t.name]) { suggestions[t.name] = null; return; } // toggle close
  matchingFor.value = t.name;
  try {
    suggestions[t.name] = await apiGET("zoho_books_clone.api.docs.suggest_payment_matches",
      { bank_transaction_name: t.name });
  } catch (e) { toast.error(e.message || "Failed to suggest matches"); }
  matchingFor.value = "";
}

async function confirmMatch(t, m) {
  matchingFor.value = m.name;
  try {
    await apiPOST("zoho_books_clone.api.docs.reconcile_bank_transaction",
      { bank_transaction_name: t.name, payment_entry_name: m.name },
      { module: "banking", action: "edit" });
    toast.success(`${t.name} matched to ${m.name}`);
    suggestions[t.name] = null;
    await load();
  } catch (e) { toast.error(e.message || "Match failed"); }
  matchingFor.value = "";
}

onMounted(async()=>{
  await loadAccounts();
  // Pre-select: deep-link account → default account → first account.
  const fromQuery = route.query.account ? String(route.query.account) : "";
  const defaultAcc = bankAccounts.value.find(a=>a.is_default)?.name;
  form.bank_account = fromQuery || defaultAcc || bankAccounts.value[0]?.name || "";
  if(form.bank_account) await load();
});
</script>

<style scoped>
.br-page{display:flex;flex-direction:column;gap:16px;padding:24px;}
.br-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
.br-select{border:1px solid #e5e7eb;border-radius:8px;padding:7px 10px;font:inherit;font-size:13px;outline:none;background:#fff;color:#111827;cursor:pointer;}
.br-select:focus{border-color:#2563eb;}
.br-input{border:1px solid #e5e7eb;border-radius:8px;padding:7px 10px;font:inherit;font-size:13px;outline:none;background:#fff;color:#111827;}
.br-input:focus{border-color:#2563eb;}
.br-btn-primary{display:inline-flex;align-items:center;gap:6px;background:#2563eb;color:#fff;border:none;border-radius:8px;padding:8px 14px;font-size:13px;font-weight:600;cursor:pointer;}
.br-btn-primary:hover{background:#1d4ed8;}.br-btn-primary:disabled{opacity:.5;cursor:not-allowed;}
.green{color:#16a34a!important;}.red{color:#dc2626!important;}.orange{color:#ea580c!important;}
.br-section-title{font-size:12px;font-weight:700;color:#374151;text-transform:uppercase;letter-spacing:.05em;}
/* toolbar: status pills + search + export */
.br-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;}
.br-filter-pills{display:inline-flex;align-items:center;gap:3px;background:#eef2f7;border:1px solid #e2e8f0;border-radius:12px;padding:4px;}
.br-fpill{display:inline-flex;align-items:center;gap:7px;padding:7px 14px;border-radius:9px;font-size:12.5px;font-weight:600;border:none;background:transparent;color:#64748b;cursor:pointer;font-family:inherit;transition:color .15s,background .15s,box-shadow .15s;}
.br-fpill:hover:not(.active){color:#334155;}
.br-fpill.active{background:#fff;color:#1d4ed8;box-shadow:0 1px 2px rgba(15,23,42,.08),0 0 0 1px rgba(37,99,235,.08);}
.br-fpill-count{display:inline-flex;align-items:center;justify-content:center;min-width:19px;height:18px;padding:0 6px;border-radius:9px;background:rgba(100,116,139,.16);color:#64748b;font-size:10.5px;font-weight:700;line-height:1;}
.br-fpill.active .br-fpill-count{background:#dbeafe;color:#1d4ed8;}
.br-toolbar-right{display:flex;align-items:center;gap:10px;}
.br-search-wrap{display:flex;align-items:center;gap:8px;background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:7px 12px;min-width:220px;transition:border-color .15s,box-shadow .15s;}
.br-search-wrap:focus-within{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.1);}
.br-search-input{border:none;background:transparent;outline:none;font:inherit;font-size:13px;color:#0f172a;width:100%;}
.br-btn-ghost{display:inline-flex;align-items:center;gap:6px;background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:8px 14px;font-size:13px;font-weight:600;color:#334155;cursor:pointer;}
.br-btn-ghost:hover:not(:disabled){background:#f8fafc;border-color:#cbd5e1;}
.br-btn-ghost:disabled{opacity:.5;cursor:not-allowed;}
.br-card{background:#fff;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;}
.br-table{width:100%;border-collapse:collapse;font-size:13px;}
.br-table th{background:#f9fafb;border-bottom:1px solid #e5e7eb;padding:10px 12px;font-size:11.5px;font-weight:600;color:#374151;text-align:left;text-transform:uppercase;}
.ta-r{text-align:right!important;}
.br-row td{padding:10px 12px;border-bottom:1px solid #f3f4f6;vertical-align:middle;}
.br-row:last-child td{border-bottom:none;}.br-row:hover td{background:#f9fafb;}
.mono-sm{font-size:13px;}.text-muted{color:#6b7280;}
.br-badge{display:inline-flex;align-items:center;padding:2px 8px;border-radius:10px;font-size:11.5px;font-weight:600;}
.badge-green{background:#dcfce7;color:#16a34a;}.badge-orange{background:#fff7ed;color:#ea580c;}
.br-empty{text-align:center;color:#9ca3af;padding:32px!important;}
.br-shimmer{height:13px;background:linear-gradient(90deg,#f3f4f6 25%,#e5e7eb 50%,#f3f4f6 75%);border-radius:4px;animation:shimmer 1.2s infinite;background-size:200% 100%;}
@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}
.br-placeholder{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:80px 20px;text-align:center;}
.br-reconcile-bar{display:flex;align-items:center;gap:12px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:12px 16px;flex-wrap:wrap;}
.br-rb-count{font-size:13px;color:#1e3a8a;font-weight:700;}
.br-rb-spacer{flex:1;}
.br-rb-note{font-size:12.5px;color:#64748b;}
.br-rb-export{display:inline-flex;align-items:center;gap:6px;background:#fff;border:1px solid #bfdbfe;color:#1d4ed8;border-radius:8px;padding:7px 12px;font-size:12.5px;font-weight:600;cursor:pointer;font-family:inherit;}
.br-rb-export:hover{background:#dbeafe;}
.br-rb-clear{background:transparent;border:none;color:#64748b;font-size:12.5px;font-weight:600;cursor:pointer;font-family:inherit;}
.br-rb-clear:hover{color:#1d4ed8;text-decoration:underline;}
.br-match-btn{background:#eff6ff;border:1px solid #93c5fd;color:#1d4ed8;padding:4px 10px;border-radius:6px;font-size:11.5px;font-weight:600;cursor:pointer;font-family:inherit;}
.br-match-btn:hover:not(:disabled){background:#dbeafe;}
.br-match-btn:disabled{opacity:.5;cursor:not-allowed;}
.br-suggest-row{background:#f8fafc;}
.br-suggest-panel{position:relative;padding:14px 18px;background:#f0f9ff;border-left:3px solid #1a6ef7;}
.br-suggest-card{display:grid;grid-template-columns:1.5fr 2fr 100px 80px;gap:10px;align-items:center;padding:8px 10px;background:#fff;border:1px solid #e0e7ff;border-radius:6px;margin-bottom:6px;font-size:12.5px;}
.br-suggest-meta{display:flex;align-items:center;gap:8px;}
.br-num{color:#1d4ed8;font-weight:700;font-size:12px;}
.br-score{padding:2px 8px;border-radius:10px;font-size:10.5px;font-weight:700;}
.br-suggest-info{color:#6b7280;font-size:12px;}
.br-suggest-amt{text-align:right;font-weight:700;color:#111827;}
.br-match-confirm{background:#1a6ef7;color:#fff;border:none;padding:5px 10px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;}
.br-match-confirm:hover:not(:disabled){background:#1d4ed8;}
.br-match-confirm:disabled{opacity:.5;cursor:not-allowed;}
.br-suggest-close{position:absolute;top:8px;right:10px;background:transparent;border:none;color:#6b7280;font-size:11px;cursor:pointer;}
.br-suggest-close:hover{color:#1d4ed8;text-decoration:underline;}

/* ── Responsive ── */
/* Mobile card styles */
.br-cards--mobile { display: none; flex-direction: column; gap: 10px; }
.br-card-shimmer { height: 90px; background: linear-gradient(90deg,#f3f4f6 25%,#e9ebee 50%,#f3f4f6 75%); background-size: 200% 100%; border-radius: 10px; animation: br-shimmer 1.2s infinite; margin-bottom: 8px; }
.br-card { border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px 14px; background: #fff; display: flex; flex-direction: column; gap: 6px; }
.br-card-header { display: flex; align-items: center; gap: 8px; }
.br-card-chk { flex-shrink: 0; }
.br-card-date { flex: 1; font-size: 12px; color: #374151; font-weight: 600; }
.br-card-desc { font-size: 13px; color: #111827; font-weight: 500;word-break: break-word; }
.br-card-ref { font-size: 11.5px; color: #9ca3af; }
.br-card-amounts { display: flex; gap: 16px; margin-top: 2px; }
.br-card-amt-item { display: flex; flex-direction: column; gap: 2px; }
.br-card-amt-lbl { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; color: #9ca3af; }
.br-card-amt-val { font-size: 13.5px; font-weight: 700; }
.br-card-actions { margin-top: 4px; }
.br-card-actions .br-match-btn { width: 100%; justify-content: center; }
.br-table {
  width: 100%;
  table-layout: fixed;
}

.br-description {
  max-width: 400px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
@media (max-width: 768px) {
  .br-table--desktop { display: none !important; }
  .br-cards--mobile { display: flex; }
  .br-toolbar-right { flex-wrap: wrap; gap: 8px; }
  .br-search-wrap { min-width: 0; flex: 1 1 auto; }
}

@media (max-width: 480px) {
  .br-page { padding: 12px; gap: 12px; }
  .br-suggest-card { grid-template-columns: 1fr auto; }
  .br-suggest-info { grid-column: 1 / -1; }
}
</style>