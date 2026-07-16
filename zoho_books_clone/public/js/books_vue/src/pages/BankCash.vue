<template>
  <div class="cash-page">
    <div class="cash-actions">
      <div class="cash-search-wrap"><span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span><input v-model="search" placeholder="Search cash transactions…" class="cash-search-input" /></div>
      <div style="display:flex;gap:8px;margin-left:auto">
        <button class="cash-btn-ghost" @click="load"><span v-html="icon('refresh',14)"></span></button>
        <button
          class="cash-btn-ghost"
          v-if="totalUndeposited>0"
          :disabled="!$canWrite('banking')"
          :title="!$canWrite('banking') ? 'Read-only access' : ''"
          @click="openDeposit"
        ><span v-html="icon('bank',14)"></span> Deposit <span class="cash-dep-count" style="margin-left:4px">{{ fmtCur(totalUndeposited) }}</span></button>
        <button class="cash-btn-primary" :disabled="!$canWrite('banking')" :title="!$canWrite('banking') ? 'Read-only access' : ''" @click="openNew"><span v-html="icon('plus',13)"></span> New Cash Entry</button>
      </div>
    </div>

    <SummaryStrip v-if="!loading" :cards="[
      { label: 'Cash In', tone: 'success', value: fmtCur(cashIn), valueClass: 'green' },
      { label: 'Cash Out', tone: 'danger', value: fmtCur(cashOut), valueClass: 'red' },
      { label: 'Net Cash', tone: 'accent', value: fmtCur(cashIn-cashOut), valueClass: (cashIn-cashOut)>=0?'green':'red' },
      { label: 'Entries', tone: 'default', value: list.length },
    ]" />

    <!-- Filter toolbar -->
    <div v-if="!loading && list.length" class="cash-toolbar">
      <div class="cash-filter-pills">
        <button v-for="t in tabs" :key="t.key" class="cash-fpill" :class="{active:activeTab===t.key}" @click="activeTab=t.key">
          {{ t.label }} <span class="cash-fpill-count">{{ tabCount(t.key) }}</span>
        </button>
      </div>
      <div class="cash-toolbar-right">
        <span class="cash-result">{{ sorted.length }} of {{ list.length }}</span>
        <button class="cash-btn-ghost" @click="exportCSV" :disabled="!sorted.length"><span v-html="icon('download',14)"></span> Export</button>
      </div>
    </div>

    <!-- Selection bar -->
    <div v-if="selected.size>0" class="cash-selbar">
      <span class="cash-sel-count">{{ selected.size }} selected</span>
      <button class="cash-sel-export" @click="exportCSV"><span v-html="icon('download',13)"></span> Export selected</button>
      <button class="cash-sel-danger" @click="bulkDelete" :disabled="bulkBusy"><span v-html="icon('trash',13)"></span> Delete {{ selected.size }}</button>
      <div style="flex:1"></div>
      <button class="cash-sel-clear" @click="selected=new Set()">Clear</button>
    </div>

    <div class="cash-card">
      <table class="cash-table cash-desktop-table">
        <thead><tr>
          <th style="width:32px"><input type="checkbox" :checked="allSelected" @change="toggleSelectAll" /></th>
          <th @click="sort('name')" class="sortable">Entry # <span v-html="sortArrow('name')"></span></th>
          <th @click="sort('party')" class="sortable">Party <span v-html="sortArrow('party')"></span></th>
          <th @click="sort('payment_date')" class="sortable">Date <span v-html="sortArrow('payment_date')"></span></th>
          <th>Type</th>
          <th @click="sort('paid_amount')" class="sortable ta-r">Amount <span v-html="sortArrow('paid_amount')"></span></th>
        </tr></thead>
        <tbody>
          <template v-if="loading"><tr v-for="n in 6" :key="n"><td colspan="6"><div class="cash-shimmer"></div></td></tr></template>
          <template v-else>
            <tr v-for="p in paged" :key="p.name" class="cash-row" @click="openView(p)">
              <td @click.stop><input type="checkbox" :checked="selected.has(p.name)" @change="toggleSelect(p.name)" /></td>
              <td><span class="cash-num">{{ p.name }}</span></td>
              <td>{{ p.party_name||p.party||'—' }}</td>
              <td class="mono-sm text-muted">{{ fmtDate(p.payment_date) }}</td>
              <td><span class="cash-badge" :class="p.payment_type==='Receive'?'badge-green':'badge-red'">{{ p.payment_type==='Receive'?'Cash In':'Cash Out' }}</span></td>
              <td class="ta-r mono-sm">{{ fmtCur(p.paid_amount) }}</td>
            </tr>
            <tr v-if="!sorted.length"><td colspan="6" class="cash-empty">{{ list.length ? 'No entries match this filter' : 'No cash entries found' }}</td></tr>
          </template>
        </tbody>
      </table>

      <!-- Mobile cards (shown at ≤768px) -->
      <div class="cash-mobile-cards">
        <template v-if="loading">
          <div v-for="n in 5" :key="n" class="cash-mobile-card cash-mc--skeleton">
            <div class="cash-mc-shimmer" style="height:13px;width:55%;margin-bottom:8px"></div>
            <div class="cash-mc-shimmer" style="height:11px;width:40%;margin-bottom:6px"></div>
            <div class="cash-mc-shimmer" style="height:11px;width:65%"></div>
          </div>
        </template>
        <div v-else-if="!sorted.length" class="cash-mc-empty">
          <div style="font-size:32px;margin-bottom:8px">💵</div>
          <div>{{ list.length ? 'No entries match' : 'No cash entries found' }}</div>
        </div>
        <template v-else>
          <div v-for="p in paged" :key="p.name" class="cash-mobile-card" @click="openView(p)">
            <div class="cash-mc-top">
              <span class="cash-mc-docno">{{ p.name }}</span>
              <span class="cash-badge" :class="p.payment_type==='Receive'?'badge-green':'badge-red'">{{ p.payment_type==='Receive'?'Cash In':'Cash Out' }}</span>
            </div>
            <div class="cash-mc-mid">{{ p.party_name || p.party || '—' }}</div>
            <div class="cash-mc-meta">
              <span>{{ fmtDate(p.payment_date) }}</span>
              <span class="cash-mc-amount" :class="p.payment_type==='Receive'?'cash-mc-pos':'cash-mc-neg'">{{ fmtCur(p.paid_amount) }}</span>
            </div>
          </div>
        </template>
      </div>
    </div>

    <div v-if="!loading && sorted.length" style="padding:4px 0 0">
      <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="sorted.length" />
    </div>

    <!-- New Entry Drawer -->
    <div v-if="drawerOpen" class="cash-overlay" @click.self="!drawerSaving && (drawerOpen=false)"></div>
    <div class="cash-drawer" :class="{open:drawerOpen}">
      <div class="cash-dheader">
        <button class="cash-dclose cash-dclose-abs" @click="drawerOpen=false"><span v-html="icon('x',16)"></span></button>
        <div class="cash-dh-top">
          <div class="cash-dh-ico"><span v-html="icon('cash',20)"></span></div>
          <div>
            <div class="cash-dh-title">New Cash Entry</div>
            <div class="cash-dh-sub">Record a cash receipt or payment</div>
          </div>
        </div>
      </div>
      <div class="cash-dbody">
        <div class="cash-fields-grid">
          <div class="cash-field" style="grid-column:1/-1">
            <label class="cash-label">Type <span class="req">*</span></label>
            <div class="cash-radio-group">
              <label class="cash-radio" :class="{checked:form.payment_type==='Receive'}" @click="form.payment_type='Receive'"><span class="cash-radio-dot" :class="{on:form.payment_type==='Receive'}"></span> Cash In (Received)</label>
              <label class="cash-radio" :class="{checked:form.payment_type==='Pay'}" @click="form.payment_type='Pay'"><span class="cash-radio-dot" :class="{on:form.payment_type==='Pay'}"></span> Cash Out (Paid)</label>
            </div>
          </div>
          <div class="cash-field"><label class="cash-label">Date <span class="req">*</span></label><input v-model="form.payment_date" type="date" class="cash-input" /></div>
          <div class="cash-field"><label class="cash-label">Amount <span class="req">*</span></label><input v-model.number="form.paid_amount" type="number" min="0" step="0.01" class="cash-input" /></div>
          <div class="cash-field" style="grid-column:1/-1">
            <label class="cash-label">{{ form.payment_type==='Receive'?'Customer':'Vendor/Employee' }} <span class="req">*</span></label>
            <SearchableSelect v-model="form.party" :options="partyOptions" :placeholder="form.payment_type==='Receive'?'Select customer…':'Select vendor/employee…'" @search="fetchParties" />
          </div>
          <div class="cash-field" style="grid-column:1/-1" v-if="form.payment_type==='Receive'">
            <label class="cash-label">Purpose <span class="req">*</span></label>
            <select v-model="form.custom_purpose" class="cash-input">
              <option value="">— Select purpose —</option>
              <option v-for="p in CASH_IN_PURPOSES" :key="p" :value="p">{{ p }}</option>
            </select>
          </div>
          <div class="cash-field" style="grid-column:1/-1" v-else>
            <label class="cash-label">Expense Category <span class="req">*</span></label>
            <SearchableSelect v-model="form.custom_expense_category" :options="expenseCategoryOptions" placeholder="Select expense category…" @search="fetchExpenseCategories" @open="fetchExpenseCategories('')" />
          </div>
          <div class="cash-field" style="grid-column:1/-1"><label class="cash-label">Remarks</label><textarea v-model="form.remarks" rows="2" class="cash-input" placeholder="Optional…"></textarea></div>
        </div>
      </div>
      <div class="cash-dfooter">
        <button class="cash-btn-ghost" @click="drawerOpen=false">Cancel</button>
        <button class="cash-btn-primary" :disabled="drawerSaving" @click="saveCash"><span v-html="icon('check',13)"></span> {{ drawerSaving?'Saving…':'Submit' }}</button>
      </div>
    </div>

    <!-- Deposit to Bank Drawer -->
    <div v-if="depositOpen" class="cash-overlay" @click.self="!depositSaving && (depositOpen=false)"></div>
    <div class="cash-drawer" :class="{open:depositOpen}">
      <div class="cash-dheader">
        <button class="cash-dclose cash-dclose-abs" @click="!depositSaving && (depositOpen=false)"><span v-html="icon('x',16)"></span></button>
        <div class="cash-dh-top">
          <div class="cash-dh-ico"><span v-html="icon('bank',20)"></span></div>
          <div>
            <div class="cash-dh-title">Deposit</div>
            <div class="cash-dh-sub">Move undeposited cash to a bank account or another cash account</div>
          </div>
        </div>
      </div>
      <div class="cash-dbody">
        <div v-if="depositLoading" class="cash-empty" style="padding:32px 0">Loading undeposited cash…</div>
        <template v-else>
          <div v-if="totalUndeposited<=0 && !depositForm.destination_account" class="cash-empty" style="padding:32px 0">
            No undeposited cash. Every cash receipt has already been deposited.
          </div>
          <template v-else>
            <div class="cash-field">
              <label class="cash-label">Deposit To <span class="req">*</span></label>
              <select v-model="depositForm.destination_account" class="cash-input" @change="onDestinationChange">
                <option value="">— Select account —</option>
                <optgroup label="Bank Account" v-if="bankDestinations.length">
                  <option v-for="b in bankDestinations" :key="b.name" :value="b.name">{{ b.name }}</option>
                </optgroup>
                <optgroup label="Cash Account" v-if="cashDestinations.length">
                  <option v-for="c in cashDestinations" :key="c.name" :value="c.name">{{ c.name }}</option>
                </optgroup>
              </select>
              <div v-if="!bankDestinations.length && !cashDestinations.length" class="pmd-warn" style="margin-top:4px">
                No Bank or other Cash account found — set one up under Accounts first.
              </div>
            </div>

            <div class="cash-dep-total" style="margin-bottom:4px">
              <span>Yet to deposit</span>
              <strong>{{ fmtCur(totalUndeposited) }}</strong>
            </div>

            <div class="cash-field">
              <label class="cash-label">Amount to Deposit <span class="req">*</span></label>
              <input v-model.number="depositForm.amount" type="number" min="0.01" :max="totalUndeposited" step="0.01" class="cash-input" />
              <div class="pmd-warn" v-if="depositForm.amount>totalUndeposited" style="margin-top:4px">
                Cannot deposit more than the undeposited balance ({{ fmtCur(totalUndeposited) }}).
              </div>
            </div>

            <div class="cash-field">
              <label class="cash-label">Deposit Date <span class="req">*</span></label>
              <input v-model="depositForm.date" type="date" class="cash-input" />
            </div>

            <div class="cash-field">
              <label class="cash-label">Notes</label>
              <textarea v-model="depositForm.notes" rows="2" class="cash-input" placeholder="Optional — deposit slip #, branch, etc."></textarea>
            </div>

            <div class="cash-dep-total">
              <span>Remaining after this deposit</span>
              <strong>{{ fmtCur(Math.max(totalUndeposited - (depositForm.amount||0), 0)) }}</strong>
            </div>
          </template>
        </template>
      </div>
      <div class="cash-dfooter">
        <button class="cash-btn-ghost" :disabled="depositSaving" @click="depositOpen=false">Cancel</button>
        <button
          class="cash-btn-primary"
          :disabled="depositSaving || !depositForm.amount || depositForm.amount<=0 || depositForm.amount>totalUndeposited || !depositForm.destination_account || !depositForm.date"
          @click="saveDeposit"
        >
          <span v-html="icon('check',13)"></span>
          {{ depositSaving ? "Depositing…" : `Deposit ${fmtCur(depositForm.amount||0)}` }}
        </button>
      </div>
    </div>

    <!-- View Drawer -->
    <div v-if="viewOpen" class="cash-overlay" @click.self="viewOpen=false"></div>
    <div class="cash-drawer cash-view-drawer" :class="{open:viewOpen}">
      <template v-if="viewDoc">
        <div class="cash-dheader">
          <button class="cash-dclose cash-dclose-abs" @click="viewOpen=false"><span v-html="icon('x',16)"></span></button>
          <div class="cash-dh-top">
            <div class="cash-dh-ico"><span v-html="icon('cash',20)"></span></div>
            <div>
              <div class="cash-dh-title">{{ viewDoc.name }}</div>
              <div class="cash-dh-sub">{{ viewDoc.party_name||viewDoc.party||'—' }} · {{ fmtDate(viewDoc.payment_date) }}</div>
            </div>
            <span class="cash-badge" :class="viewDoc.payment_type==='Receive'?'badge-green':'badge-red'">{{ viewDoc.payment_type==='Receive'?'Cash In':'Cash Out' }}</span>
          </div>
          <div class="cash-dh-amount">
            <div class="cash-dh-amt-lbl">{{ viewDoc.payment_type==='Receive'?'Received':'Paid Out' }}</div>
            <div class="cash-dh-amt-val" :class="viewDoc.payment_type==='Receive'?'pos':'neg'">{{ fmtCur(viewDoc.paid_amount) }}</div>
          </div>
        </div>
        <div class="cash-dbody">
          <div class="cash-section-hdr"><span v-html="icon('info',13)"></span> Details</div>
          <div class="cash-meta-grid">
            <div><div class="cash-meta-lbl">Date</div><div class="mono-sm">{{ fmtDate(viewDoc.payment_date) }}</div></div>
            <div><div class="cash-meta-lbl">{{ viewDoc.payment_type==='Receive'?'Customer':'Vendor/Employee' }}</div><div>{{ viewDoc.party_name||viewDoc.party||'—' }}</div></div>
            <div><div class="cash-meta-lbl">Type</div><div>{{ viewDoc.payment_type==='Receive'?'Cash In':'Cash Out' }}</div></div>
            <div><div class="cash-meta-lbl">Mode</div><div>Cash</div></div>
            <div v-if="viewDoc.payment_type==='Receive'"><div class="cash-meta-lbl">Purpose</div><div>{{ viewDoc.custom_purpose||'—' }}</div></div>
            <div v-else><div class="cash-meta-lbl">Expense Category</div><div>{{ viewDoc.custom_expense_category||'—' }}</div></div>
          </div>
          <template v-if="viewDoc.remarks">
            <div class="cash-section-hdr"><span v-html="icon('file',13)"></span> Remarks</div>
            <div class="cash-remark">{{ viewDoc.remarks }}</div>
          </template>
        </div>
        <div class="cash-dfooter">
          <button class="cash-btn-danger-ghost" @click="deleteEntry(viewDoc)" :disabled="actionBusy"><span v-html="icon('trash',13)"></span> Delete</button>
          <div style="margin-left:auto"><button class="cash-btn-ghost" @click="viewOpen=false">Close</button></div>
        </div>
      </template>
    </div>
  </div>
</template>
<script setup>
import { ref, reactive, computed, onMounted, watch } from "vue";
import { apiList, apiSave, apiSubmit, apiCancel, apiDelete, resolveCompany, apiGET, apiPOST } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { useConfirm } from "../composables/useConfirm.js";
import { icon } from "../utils/icons.js";
import { flt, fmtDate } from "../utils/format.js";
import SummaryStrip from "../components/SummaryStrip.vue";
import SearchableSelect from "../components/SearchableSelect.vue";
import Pagination from "../components/Pagination.vue";
import { usePagination } from "../composables/usePagination.js";
const { toast } = useToast();
const { confirm } = useConfirm();
const cashAccount=ref(""),cashAccounts=ref([]),receivableAccount=ref(""),payableAccount=ref(""),companyCurrency=ref("INR");
async function loadAccounts(){try{const co=await resolveCompany();const[cashAccs,recvAcc,payAcc,comp]=await Promise.all([apiList("Account",{fields:["name"],filters:[["company","=",co],["account_type","=","Cash"],["is_group","=",0]]}),apiList("Account",{fields:["name"],filters:[["company","=",co],["account_type","=","Receivable"],["is_group","=",0]],limit:1}),apiList("Account",{fields:["name"],filters:[["company","=",co],["account_type","=","Payable"],["is_group","=",0]],limit:1}),apiList("Books Company",{fields:["currency"],filters:[["name","=",co]],limit:1})]);cashAccounts.value=cashAccs.map(a=>a.name);cashAccount.value=cashAccounts.value[0]||"";receivableAccount.value=recvAcc[0]?.name||"";payableAccount.value=payAcc[0]?.name||"";companyCurrency.value=comp[0]?.currency||"INR";}catch(e){console.error("Failed to load accounts",e);}}
const activeTab=ref("all");
const tabs=[{key:"all",label:"All"},{key:"Receive",label:"Cash In"},{key:"Pay",label:"Cash Out"}];
const list=ref([]),loading=ref(false),search=ref("");
const drawerOpen=ref(false),drawerSaving=ref(false),actionBusy=ref(false),bulkBusy=ref(false);
const viewOpen=ref(false),viewDoc=ref(null);
const depositOpen=ref(false),depositLoading=ref(false),depositSaving=ref(false);
const depositDestinations=ref([]); // [{name, account_type}]
const totalUndeposited=ref(0);
const depositForm=reactive({amount:0,destination_account:"",date:new Date().toISOString().slice(0,10),notes:""});
const bankDestinations=computed(()=>depositDestinations.value.filter(d=>d.account_type==="Bank"));
const cashDestinations=computed(()=>depositDestinations.value.filter(d=>d.account_type==="Cash"));
const selected=ref(new Set());
const partyOptions=ref([]);
const expenseCategoryOptions=ref([]);
const CASH_IN_PURPOSES=["Sales Receipt","Customer Advance","Loan Received","Capital Introduced","Other Income","Refund Received","Other"];
async function fetchExpenseCategories(q=""){
  try{
    const company=await resolveCompany();
    const filters=[["is_group","=",0],["disabled","=",0],["company","=",company],["account_type","=","Expense"]];
    if(q)filters.push(["name","like",`%${q}%`]);
    const rows=await apiList("Account",{fields:["name"],filters,limit:30,order:"name asc"});
    expenseCategoryOptions.value=rows.map(r=>({label:r.name,value:r.name}));
  }catch{expenseCategoryOptions.value=[];}
}
const sortCol=ref("payment_date"),sortDir=ref("desc");
const form=reactive({payment_type:"Receive",payment_date:new Date().toISOString().slice(0,10),paid_amount:0,party:"",custom_purpose:"",custom_expense_category:"",remarks:""});
async function load(){
  loading.value=true;
  try{
    const co=await resolveCompany();
    // Resolve Cash accounts inline (not via mode_of_payment label) so this
    // list always matches the same source of truth as get_undeposited_cash:
    // the actual GL account money is sitting in, not a free-text mode field
    // that can drift out of sync with where the entry really posted.
    const cashAccs = cashAccounts.value.length ? cashAccounts.value
      : (await apiList("Account",{fields:["name"],filters:[["company","=",co],["account_type","=","Cash"],["is_group","=",0]]})).map(a=>a.name);
    if(!cashAccs.length){ list.value=[]; selected.value=new Set(); return; }
    const [cashIn, cashOutPE, cashOut] = await Promise.all([
      // Cash In: real Payment Entries (Dr Cash / Cr Accounts Receivable).
      apiList("Payment Entry",{fields:["name","party","party_name","payment_type","payment_date","paid_amount","remarks","custom_purpose","custom_expense_category","docstatus","custom_deposited_to_bank"],filters:[["company","=",co],["paid_to","in",cashAccs],["payment_type","=","Receive"],["docstatus","=",1]],limit:200,order:"payment_date desc, creation desc"}),
      // Cash Out: real Payment Entries (Dr Payable / Cr Cash) — bill payments made in cash.
      apiList("Payment Entry",{fields:["name","party","party_name","payment_type","payment_date","paid_amount","remarks","custom_purpose","custom_expense_category","docstatus"],filters:[["company","=",co],["paid_from","in",cashAccs],["payment_type","=","Pay"],["docstatus","=",1]],limit:200,order:"payment_date desc, creation desc"}),
      // Cash Out: Journal Entries (Dr Expense / Cr Cash-in-Hand) tagged by this page — cash expenses with no vendor bill.
      apiList("Journal Entry",{fields:["name","posting_date","total_debit","remark","custom_expense_category","custom_party","custom_party_name","docstatus"],filters:[["company","=",co],["custom_cash_out_entry","=",1],["docstatus","=",1]],limit:200,order:"posting_date desc, creation desc"}),
    ]);
    const normalizedOut = cashOut.map(j=>({
      name:j.name, _dt:"Journal Entry",
      party:j.custom_party||"", party_name:j.custom_party_name||j.custom_party||"",
      payment_type:"Pay", payment_date:j.posting_date, paid_amount:j.total_debit,
      remarks:j.remark||"", custom_purpose:"", custom_expense_category:j.custom_expense_category||"",
      docstatus:j.docstatus,
    }));
    const normalizedOutPE = cashOutPE.map(p=>({...p,_dt:"Payment Entry"}));
    const normalizedIn = cashIn.map(p=>({...p,_dt:"Payment Entry"}));
    list.value=[...normalizedIn,...normalizedOutPE,...normalizedOut];
    selected.value=new Set();
  }catch(e){toast.error(e.message||"Failed to load cash entries");}
  finally{loading.value=false;}
}
const filtered=computed(()=>{let r=list.value;if(activeTab.value!=="all")r=r.filter(p=>p.payment_type===activeTab.value);if(search.value.trim()){const q=search.value.toLowerCase();r=r.filter(p=>(p.party_name||p.party||"").toLowerCase().includes(q)||(p.name||"").toLowerCase().includes(q)||(p.remarks||"").toLowerCase().includes(q));}return r;});
const sorted=computed(()=>{const col=sortCol.value;return[...filtered.value].sort((a,b)=>{const av=a[col]??"",bv=b[col]??"";const c=typeof av==="number"?av-bv:String(av).localeCompare(String(bv));return sortDir.value==="asc"?c:-c;});});
// Selection/export act on the full filtered+sorted set (all pages); only the
// table rendering itself is paginated via `paged`.
const { page, pageSize, paged } = usePagination(sorted, { storageKey: "bank-cash" });
function sort(col){if(sortCol.value===col)sortDir.value=sortDir.value==="asc"?"desc":"asc";else{sortCol.value=col;sortDir.value="asc";}}
function sortArrow(col){if(sortCol.value!==col)return'<span style="color:#d1d5db">⇅</span>';return sortDir.value==="asc"?"↑":"↓";}
const cashIn=computed(()=>list.value.filter(p=>p.payment_type==="Receive").reduce((s,p)=>s+flt(p.paid_amount),0));
const cashOut=computed(()=>list.value.filter(p=>p.payment_type==="Pay").reduce((s,p)=>s+flt(p.paid_amount),0));
function tabCount(key){if(key==="all")return list.value.length;return list.value.filter(p=>p.payment_type===key).length;}
function fmtCur(v){return new Intl.NumberFormat("en-IN",{style:"currency",currency:"INR",minimumFractionDigits:2}).format(flt(v));}

// ── selection ──
function toggleSelect(name){const s=new Set(selected.value);if(s.has(name))s.delete(name);else s.add(name);selected.value=s;}
const allSelected=computed(()=>sorted.value.length>0&&sorted.value.every(p=>selected.value.has(p.name)));
function toggleSelectAll(){if(allSelected.value){selected.value=new Set();}else{selected.value=new Set(sorted.value.map(p=>p.name));}}

function exportCSV(){
  const rows=selected.value.size?sorted.value.filter(p=>selected.value.has(p.name)):sorted.value;
  if(!rows.length)return;
  const esc=v=>{const s=v==null?"":String(v);return /[",\n]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s;};
  const lines=[["Entry #","Party","Date","Type","Amount","Purpose/Expense Category","Remarks"].join(",")];
  for(const p of rows){
    lines.push([p.name,p.party||"",fmtDate(p.payment_date),p.payment_type==="Receive"?"Cash In":"Cash Out",flt(p.paid_amount)||0,p.payment_type==="Receive"?(p.custom_purpose||""):(p.custom_expense_category||""),p.remarks||""].map(esc).join(","));
  }
  const blob=new Blob(["﻿"+lines.join("\r\n")],{type:"text/csv;charset=utf-8;"});
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a");
  a.href=url;a.download=`cash_entries_${new Date().toISOString().slice(0,10)}.csv`;
  a.click();URL.revokeObjectURL(url);
  toast.success(`Exported ${rows.length} row(s)`);
}

async function bulkDelete(){
  const rows=sorted.value.filter(p=>selected.value.has(p.name));
  if(!rows.length)return;
  const ok=await confirm({title:`Delete ${rows.length} cash entr${rows.length>1?'ies':'y'}?`,body:"This cancels and deletes the selected entries, reversing their ledger impact. This cannot be undone.",okLabel:"Delete",okStyle:"danger"});
  if(!ok)return;
  bulkBusy.value=true;let done=0;
  try{for(const p of rows){const dt=p._dt||"Payment Entry";try{await apiCancel(dt,p.name);}catch{}try{await apiDelete(dt,p.name);done++;}catch{}}toast.success(`Deleted ${done} entr${done>1?'ies':'y'}`);await load();}
  finally{bulkBusy.value=false;}
}

async function fetchParties(q=""){
  const dt=form.payment_type==="Receive"?"Customer":"Supplier";
  const nameField=dt==="Customer"?"customer_name":"supplier_name";
  try{
    const filters=[["disabled","=",0]];
    if(q)filters.push([nameField,"like","%"+q+"%"]);
    const rows=await apiList(dt,{fields:["name",nameField],filters,limit:30,order:nameField+" asc"});
    partyOptions.value = rows.map(r => ({
      label: r[nameField] || r.name,
      value: r.name,
      party_name: r[nameField] || r.name
    }));
  }catch{partyOptions.value=[];}
}
// Switching Cash In/Out changes the party master — reset selection + reload list.
watch(()=>form.payment_type,()=>{form.party="";form.custom_purpose="";form.custom_expense_category="";if(drawerOpen.value){fetchParties("");if(form.payment_type==="Pay")fetchExpenseCategories("");}});

function openNew(){Object.assign(form,{payment_type:"Receive",payment_date:new Date().toISOString().slice(0,10),paid_amount:0,party:"",custom_purpose:"",custom_expense_category:"",remarks:""});partyOptions.value=[];expenseCategoryOptions.value=[];fetchParties("");drawerOpen.value=true;}
function openView(p){viewDoc.value=p;viewOpen.value=true;}

async function saveCash(){
  if(!flt(form.paid_amount))return toast.error("Amount is required");
  if(!form.party.trim())return toast.error(form.payment_type==="Receive"?"Customer is required":"Vendor/Employee is required");
  if(form.payment_type==="Receive"&&!form.custom_purpose)return toast.error("Purpose is required");
  if(form.payment_type==="Pay"&&!form.custom_expense_category)return toast.error("Expense Category is required");
  if(!cashAccount.value)return toast.error("Cash account not configured — check chart of accounts");
  drawerSaving.value=true;
  try{
    const company=await resolveCompany();const isCashIn=form.payment_type==="Receive";
    const selectedParty = partyOptions.value.find(
      o => o.value === form.party
    );
    const partyName = selectedParty?.party_name || form.party;

    if(isCashIn){
      // Dr Cash-in-Hand / Cr Accounts Receivable (customer pays cash).
      const doc={doctype:"Payment Entry",company,payment_type:"Receive",party_type:"Customer",party:form.party,party_name: partyName,mode_of_payment:"Cash",paid_from:receivableAccount.value||cashAccount.value,paid_to:cashAccount.value,paid_from_account_currency:companyCurrency.value,paid_to_account_currency:companyCurrency.value,source_exchange_rate:1,target_exchange_rate:1,paid_amount:flt(form.paid_amount),received_amount:flt(form.paid_amount),payment_date:form.payment_date,custom_purpose:form.custom_purpose,custom_expense_category:"",remarks:form.remarks||""};
      const saved=await apiSave(doc);await apiSubmit("Payment Entry",saved.name);
      toast.success(`Cash entry ${saved?.name||""} created`);
    }else{
      // Direct cash expense (no vendor bill being settled) — must be a Journal
      // Entry: Dr [selected Expense account] / Cr Cash-in-Hand. A Payment
      // Entry can't be used here because its "Pay" leg is hard-locked to a
      // Payable account, which would silently misbook this as settling a
      // vendor bill that doesn't exist and never touch the expense ledger.
      const amt=flt(form.paid_amount);
      const doc={
        doctype:"Journal Entry", company, posting_date:form.payment_date,
        voucher_type:"Journal Entry", naming_series:"JV-.YYYY.-",
        remark: form.remarks || `Cash expense — ${partyName}`,
        custom_cash_out_entry:1, custom_expense_category:form.custom_expense_category,
        custom_party:form.party, custom_party_name:partyName,
        accounts:[
          {doctype:"Journal Entry Account", account:form.custom_expense_category, party_type:"Supplier", party:form.party, debit:amt, credit:0},
          {doctype:"Journal Entry Account", account:cashAccount.value, debit:0, credit:amt},
        ],
      };
      const saved=await apiSave(doc);await apiSubmit("Journal Entry",saved.name);
      toast.success(`Cash entry ${saved?.name||""} created`);
    }
    drawerOpen.value=false;await load();
  }catch(e){toast.error(e.message||"Failed to save");}finally{drawerSaving.value=false;}
}

async function deleteEntry(p){
  const ok=await confirm({title:"Delete cash entry?",body:`This cancels and deletes ${p.name}, reversing its ledger impact.`,okLabel:"Delete",okStyle:"danger"});
  if(!ok)return;
  actionBusy.value=true;
  const dt=p._dt||"Payment Entry";
  try{try{await apiCancel(dt,p.name);}catch{}await apiDelete(dt,p.name);toast.success(`${p.name} deleted`);viewOpen.value=false;await load();}
  catch(e){toast.error(e.message||"Failed to delete");}finally{actionBusy.value=false;}
}

async function refreshUndepositedCount(){
  try{
    const co=await resolveCompany();
    const d=await apiGET("zoho_books_clone.api.books_data.get_undeposited_cash",{company:co});
    totalUndeposited.value=flt(d?.total_undeposited||0);
  }catch{totalUndeposited.value=0;}
}

async function loadDepositPool(excludeAccount){
  const co=await resolveCompany();
  const params={company:co};
  if(excludeAccount)params.exclude_account=excludeAccount;
  const d=await apiGET("zoho_books_clone.api.books_data.get_undeposited_cash",params);
  totalUndeposited.value=flt(d?.total_undeposited||0);
  depositDestinations.value=d?.destination_accounts||[];
  return d;
}

async function openDeposit(){
  depositOpen.value=true;depositLoading.value=true;
  Object.assign(depositForm,{amount:0,destination_account:"",date:new Date().toISOString().slice(0,10),notes:""});
  viewOpen.value=false;
  try{
    await loadDepositPool();
    // Default to depositing the full pooled balance — user can edit down for a partial deposit.
    depositForm.amount=totalUndeposited.value;
  }catch(e){toast.error(e.message||"Failed to load undeposited cash");totalUndeposited.value=0;}
  finally{depositLoading.value=false;}
}

async function onDestinationChange(){
  // If the destination is itself a Cash account (e.g. Petty Cash), the pool
  // must exclude that account's own balance — money can't move from an
  // account into itself. Re-fetch the pool total accordingly.
  const dest=depositDestinations.value.find(d=>d.name===depositForm.destination_account);
  const excludeAccount = dest && dest.account_type==="Cash" ? dest.name : null;
  depositLoading.value=true;
  try{
    const prevAmount=depositForm.amount;
    const prevWasFull = prevAmount>=totalUndeposited.value; // was the user depositing "everything"?
    const keepDestination=depositForm.destination_account;
    await loadDepositPool(excludeAccount);
    if(keepDestination && !depositDestinations.value.some(d=>d.name===keepDestination)){
      const original=dest||{name:keepDestination,account_type:"Cash"};
      depositDestinations.value=[...depositDestinations.value,original];
    }
    depositForm.amount = prevWasFull ? totalUndeposited.value : Math.min(prevAmount, totalUndeposited.value);
  }catch(e){toast.error(e.message||"Failed to refresh balance");}
  finally{depositLoading.value=false;}
}

async function saveDeposit(){
  if(!depositForm.amount||depositForm.amount<=0)return toast.error("Enter an amount to deposit");
  if(depositForm.amount>totalUndeposited.value)return toast.error("Amount exceeds the undeposited balance");
  if(!depositForm.destination_account)return toast.error("Select where to deposit the cash");
  if(!depositForm.date)return toast.error("Deposit date is required");
  depositSaving.value=true;
  try{
    const co=await resolveCompany();
    const res=await apiPOST("zoho_books_clone.api.books_data.deposit_cash_to_bank",{
      amount:depositForm.amount,
      destination_account:depositForm.destination_account,
      deposit_date:depositForm.date,
      notes:depositForm.notes||"",
      company:co,
    });
    toast.success(`Deposited ${fmtCur(res?.amount||depositForm.amount)} to ${depositForm.destination_account} via ${res?.journal_entry||"Journal Entry"}`);
    depositOpen.value=false;
    await Promise.all([load(),refreshUndepositedCount()]);
  }catch(e){toast.error(e.message||"Deposit failed");}
  finally{depositSaving.value=false;}
}

onMounted(()=>{load();loadAccounts();refreshUndepositedCount();});
</script>
<style scoped>
.cash-page{display:flex;flex-direction:column;gap:16px;padding:24px;}
.cash-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
.cash-search-wrap{display:flex;align-items:center;gap:8px;background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:6px 12px;min-width:240px;}
.cash-search-input{border:none;background:transparent;outline:none;font:inherit;color:#111827;width:100%;font-size:13px;}
.cash-btn-primary{display:inline-flex;align-items:center;gap:6px;background:#2563eb;color:#fff;border:none;border-radius:8px;padding:8px 14px;font-size:13px;font-weight:600;cursor:pointer;}
.cash-btn-primary:hover{background:#1d4ed8;}.cash-btn-primary:disabled{opacity:.5;cursor:not-allowed;}
.cash-dep-badge{display:inline-flex;align-items:center;justify-content:center;min-width:18px;height:18px;padding:0 5px;border-radius:9px;background:#fef3c7;color:#b45309;font-size:10.5px;font-weight:700;margin-left:2px;}
.cash-dep-count{margin-left:auto;font-size:11px;font-weight:600;color:#64748b;text-transform:none;letter-spacing:0;}
.cash-dep-list{display:flex;flex-direction:column;border:1px solid #e5e7eb;border-radius:8px;}
.cash-dep-row{display:flex;align-items:center;gap:10px;padding:10px 12px;border-bottom:1px solid #f3f4f6;font-size:12.5px;cursor:pointer;transition:background .12s;}
.cash-dep-row:last-child{border-bottom:none;}.cash-dep-row:hover{background:#f9fafb;}
.cash-dep-row.selected{background:#eff6ff;}
.cash-dep-row.selected:hover{background:#e0f0ff;}
.cash-dep-row input[type=checkbox]{flex-shrink:0;width:15px;height:15px;accent-color:#2563eb;cursor:pointer;}
.cash-dep-row--hdr{position:sticky;top:0;z-index:1;background:#f9fafb;font-weight:600;color:#475569;cursor:default;}
.cash-dep-row--hdr:hover{background:#f9fafb;}
.cash-dep-col-main{flex:1;display:flex;flex-direction:column;gap:1px;min-width:0;}
.cash-dep-sub{font-size:11px;color:#94a3b8;}
.cash-dep-col-amt{flex-shrink:0;width:88px;text-align:right;font-weight:600;color:#0f172a;}
.cash-dep-total{display:flex;justify-content:space-between;align-items:center;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:10px 14px;font-size:13px;color:#166534;transition:background .15s,border-color .15s,color .15s;}
.cash-dep-total strong{font-size:15px;}
.cash-dep-total--empty{background:#f8fafc;border-color:#e5e7eb;color:#94a3b8;}
.cash-dep-total--empty strong{color:#94a3b8;}
.pmd-warn{font-size:11.5px;color:#b45309;background:#fffbeb;border:1px solid #fde68a;border-radius:6px;padding:6px 8px;}
.cash-btn-ghost{display:inline-flex;align-items:center;gap:6px;background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:8px 14px;font-size:13px;font-weight:600;color:#334155;cursor:pointer;}
.cash-btn-ghost:hover:not(:disabled){background:#f8fafc;border-color:#cbd5e1;}.cash-btn-ghost:disabled{opacity:.5;cursor:not-allowed;}
.cash-btn-danger-ghost{display:inline-flex;align-items:center;gap:6px;background:#fff;border:1px solid #fecaca;border-radius:8px;padding:8px 12px;font-size:13px;color:#dc2626;cursor:pointer;}
.cash-btn-danger-ghost:hover:not(:disabled){background:#fef2f2;}.cash-btn-danger-ghost:disabled{opacity:.5;cursor:not-allowed;}

/* toolbar */
.cash-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;}
.cash-filter-pills{display:inline-flex;align-items:center;gap:3px;background:#eef2f7;border:1px solid #e2e8f0;border-radius:12px;padding:4px;}
.cash-fpill{display:inline-flex;align-items:center;gap:7px;padding:7px 14px;border-radius:9px;font-size:12.5px;font-weight:600;border:none;background:transparent;color:#64748b;cursor:pointer;font-family:inherit;transition:color .15s,background .15s,box-shadow .15s;}
.cash-fpill:hover:not(.active){color:#334155;}
.cash-fpill.active{background:#fff;color:#1d4ed8;box-shadow:0 1px 2px rgba(15,23,42,.08),0 0 0 1px rgba(37,99,235,.08);}
.cash-fpill-count{display:inline-flex;align-items:center;justify-content:center;min-width:19px;height:18px;padding:0 6px;border-radius:9px;background:rgba(100,116,139,.16);color:#64748b;font-size:10.5px;font-weight:700;line-height:1;}
.cash-fpill.active .cash-fpill-count{background:#dbeafe;color:#1d4ed8;}
.cash-toolbar-right{display:flex;align-items:center;gap:12px;}
.cash-result{font-size:12px;color:#94a3b8;font-weight:600;white-space:nowrap;}

/* selection bar */
.cash-selbar{display:flex;align-items:center;gap:12px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:10px 14px;flex-wrap:wrap;}
.cash-sel-count{font-size:13px;color:#1e3a8a;font-weight:700;}
.cash-sel-export{display:inline-flex;align-items:center;gap:6px;background:#fff;border:1px solid #bfdbfe;color:#1d4ed8;border-radius:8px;padding:7px 12px;font-size:12.5px;font-weight:600;cursor:pointer;font-family:inherit;}
.cash-sel-export:hover{background:#dbeafe;}
.cash-sel-danger{display:inline-flex;align-items:center;gap:6px;background:#fff;border:1px solid #fecaca;color:#dc2626;border-radius:8px;padding:7px 12px;font-size:12.5px;font-weight:600;cursor:pointer;font-family:inherit;}
.cash-sel-danger:hover:not(:disabled){background:#fef2f2;}.cash-sel-danger:disabled{opacity:.5;cursor:not-allowed;}
.cash-sel-clear{background:transparent;border:none;color:#64748b;font-size:12.5px;font-weight:600;cursor:pointer;font-family:inherit;}
.cash-sel-clear:hover{color:#1d4ed8;text-decoration:underline;}

.cash-card{background:#fff;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;}
.cash-table{width:100%;border-collapse:collapse;font-size:13px;}
.cash-table th{background:#f9fafb;border-bottom:1px solid #e5e7eb;padding:10px 12px;font-size:11.5px;font-weight:600;color:#374151;text-align:left;white-space:nowrap;text-transform:uppercase;}
.cash-table th.sortable{cursor:pointer;user-select:none;}.cash-table th.sortable:hover{color:#2563eb;}
.ta-r{text-align:right!important;}
.cash-row td{padding:10px 12px;border-bottom:1px solid #f3f4f6;cursor:pointer;}
.cash-row:last-child td{border-bottom:none;}.cash-row:hover td{background:#f9fafb;}
.cash-num{font-size:13px;color:#2563eb;font-weight:600;}
.mono-sm{font-size:13px;}.text-muted{color:#6b7280;}
.cash-badge{display:inline-flex;align-items:center;padding:2px 8px;border-radius:10px;font-size:11.5px;font-weight:600;}
.badge-green{background:#dcfce7;color:#16a34a;}.badge-red{background:#fee2e2;color:#dc2626;}.badge-amber{background:#fef3c7;color:#b45309;}
.cash-empty{text-align:center;color:#9ca3af;padding:48px!important;cursor:default!important;}
.cash-shimmer{height:13px;background:linear-gradient(90deg,#f3f4f6 25%,#e5e7eb 50%,#f3f4f6 75%);border-radius:4px;animation:shimmer 1.2s infinite;background-size:200% 100%;}
@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}

/* drawer */
.cash-overlay{position:fixed;inset:0;background:rgba(15,23,42,.28);z-index:40;}
.cash-drawer{position:fixed;top:0;right:-440px;bottom:0;width:440px;max-width:96vw;background:#fff;border-left:1px solid #e5e7eb;box-shadow:-8px 0 28px rgba(15,23,42,.12);z-index:50;display:flex;flex-direction:column;transition:right .24s ease;}
.cash-drawer.open{right:0;}
.cash-view-drawer{width:400px;right:-400px;}.cash-view-drawer.open{right:0;}
.cash-dheader{position:relative;flex-shrink:0;padding:20px;border-bottom:1px solid #e5e7eb;background:linear-gradient(135deg,#eff6ff 0%,#dbeafe 100%);}
.cash-dclose{background:transparent;border:none;cursor:pointer;color:#475569;display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border-radius:8px;}
.cash-dclose:hover{background:rgba(255,255,255,.6);color:#0f172a;}
.cash-dclose-abs{position:absolute;top:12px;right:12px;}
.cash-dh-top{display:flex;align-items:center;gap:13px;padding-right:36px;}
.cash-dh-ico{width:42px;height:42px;background:#fff;border-radius:11px;display:flex;align-items:center;justify-content:center;color:#2563eb;flex-shrink:0;box-shadow:0 1px 3px rgba(15,23,42,.08);}
.cash-dh-title{font-size:15px;font-weight:700;color:#0f172a;}
.cash-dh-sub{font-size:12px;color:#475569;margin-top:1px;}
.cash-dh-top .cash-badge{margin-left:auto;text-wrap-mode: nowrap;}
.cash-dh-amount{margin-top:16px;}
.cash-dh-amt-lbl{font-size:10.5px;color:#64748b;text-transform:uppercase;letter-spacing:.05em;font-weight:600;}
.cash-dh-amt-val{font-size:26px;font-weight:800;letter-spacing:-.01em;margin-top:2px;}
.cash-dh-amt-val.pos{color:#16a34a;}.cash-dh-amt-val.neg{color:#dc2626;}
.cash-dbody{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:12px;}
.cash-section-hdr{display:flex;align-items:center;gap:8px;font-size:11.5px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:#0f172a;margin-top:4px;}
.cash-section-hdr span{color:#2563eb;display:inline-flex;}
.cash-fields-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
.cash-field{display:flex;flex-direction:column;gap:4px;}
.cash-label{font-size:12px;font-weight:600;color:#334155;}.req{color:#dc2626;}
.cash-input{border:1px solid #e2e8f0;border-radius:8px;padding:8px 11px;font:inherit;font-size:13px;outline:none;background:#fff;color:#0f172a;transition:border-color .15s,box-shadow .15s;}
.cash-input:focus{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.1);}
textarea.cash-input{resize:vertical;}
.cash-radio-group{display:flex;gap:10px;}
.cash-radio{display:flex;align-items:center;gap:8px;padding:8px 14px;border:1px solid #e2e8f0;border-radius:8px;cursor:pointer;font-size:13px;color:#374151;user-select:none;}
.cash-radio.checked{border-color:#2563eb;background:#eff6ff;color:#2563eb;}
.cash-radio-dot{width:14px;height:14px;border-radius:50%;border:2px solid #d1d5db;display:inline-block;flex-shrink:0;}
.cash-radio-dot.on{border-color:#2563eb;background:#2563eb;box-shadow:inset 0 0 0 3px #fff;}
.cash-meta-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
.cash-meta-lbl{font-size:10.5px;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;margin-bottom:2px;font-weight:600;}
.cash-remark{font-size:13px;color:#334155;line-height:1.5;background:#f8fafc;border:1px solid #eef2f7;border-radius:10px;padding:12px 14px;}
.cash-dfooter{display:flex;align-items:center;gap:8px;padding:14px 20px;border-top:1px solid #e5e7eb;flex-shrink:0;}

/* ── Mobile card defaults ── */
.cash-mobile-cards { display: none; }
.cash-desktop-table { display: table; }

/* ── Responsive ── */
@media (max-width: 768px) {
  .cash-drawer      { width: 100% !important; right: -100% !important; max-width: 100%; }
  .cash-view-drawer { width: 100% !important; right: -100% !important; max-width: 100%; }
  .cash-drawer.open,
  .cash-view-drawer.open { right: 0 !important; }
  .cash-desktop-table { display: none !important; }
  .cash-mobile-cards { display: flex; flex-direction: column; gap: 0; background: #f8fafc; }
  .cash-mobile-card { background: #fff; border-bottom: 1px solid #e5e7eb; padding: 12px 14px; cursor: pointer; transition: background .12s; }
  .cash-mobile-card:active { background: #f8f9fc; }
  .cash-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .cash-mc-docno { font-size: 12px; font-weight: 700; color: #2563eb; }
  .cash-mc-mid { font-size: 13.5px; font-weight: 600; color: #1a1d23; margin-bottom: 4px; }
  .cash-mc-meta { display: flex; justify-content: space-between; font-size: 12px; color: #868e96; }
  .cash-mc-amount { font-weight: 700; }
  .cash-mc-pos { color: #16a34a; }
  .cash-mc-neg { color: #dc2626; }
  .cash-mc--skeleton { pointer-events: none; }
  .cash-mc-shimmer { border-radius: 6px; background: linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size: 200% 100%; animation: cash-mc-sh 1.4s infinite; }
  @keyframes cash-mc-sh { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
  .cash-mc-empty { text-align: center; padding: 32px 16px; color: #868e96; font-size: 13px; }
  .cash-badge { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 10px; font-size: 11.5px; font-weight: 600; }
}

@media (max-width: 480px) {
  .cash-page { padding: 12px; gap: 12px; }
  .cash-search-wrap { min-width: 0; flex: 1 1 auto; }
  .cash-fields-grid { grid-template-columns: 1fr !important; }
  .cash-radio-group { flex-direction: column; }
  .cash-meta-grid   { grid-template-columns: 1fr !important; }
  .cash-dh-amt-val  { font-size: 20px; }
}
</style>