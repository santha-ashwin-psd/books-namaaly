<template>
  <div class="sl-page">
    <div class="sl-filterbar">
      <div class="sl-fld sl-fld-item">
        <label class="sl-fld-lbl">Item</label>
        <SearchableSelect v-model="filters.item" :options="items" placeholder="All items" @search="fetchItems" />
      </div>
      <div class="sl-fld sl-fld-wh">
        <label class="sl-fld-lbl">Warehouse</label>
        <SearchableSelect v-model="filters.warehouse" :options="warehouses" placeholder="All warehouses" @search="fetchWarehouses" />
      </div>
      <div class="sl-fld sl-fld-date">
        <label class="sl-fld-lbl">From</label>
        <input v-model="filters.from_date" type="date" class="sl-input" />
      </div>
      <div class="sl-fld sl-fld-date">
        <label class="sl-fld-lbl">To</label>
        <input v-model="filters.to_date" type="date" class="sl-input" />
      </div>
      <button class="sl-btn-primary" @click="load"><span v-html="icon('refresh',13)"></span> Run</button>
      <button class="sl-btn-ghost" @click="exportCSV" :disabled="!list.length"><span v-html="icon('download',13)"></span> Export</button>
    </div>

    <SummaryStrip v-if="!loading && list.length" :cards="[
      { label:'Inward Qty', tone:'success', value: fmtQty(summaryIn), valueClass:'green' },
      { label:'Outward Qty', tone:'danger', value: fmtQty(summaryOut), valueClass:'red' },
      { label:'Net Qty', tone:'accent', value: fmtQty(summaryIn-summaryOut), valueClass:(summaryIn-summaryOut)>=0?'green':'red' },
      { label:'Stock Value', tone:'info', value: fmtCur(stockValue), valueClass:'blue' },
    ]" />

    <div v-if="loaded && list.length" class="sl-toolbar">
      <div class="sl-filter-pills">
        <button v-for="d in dirTabs" :key="d.key" class="sl-fpill" :class="{active:dirFilter===d.key}" @click="dirFilter=d.key">
          {{ d.label }} <span class="sl-fpill-count">{{ d.count }}</span>
        </button>
      </div>
      <div class="sl-toolbar-right">
        <span class="sl-result">{{ sorted.length }} of {{ list.length }}</span>
        <div class="sl-search-wrap">
          <span v-html="icon('search',13)" style="color:#94a3b8;flex-shrink:0"></span>
          <input v-model="search" placeholder="Search item / voucher / warehouse…" class="sl-search-input" />
        </div>
      </div>
    </div>

    <div class="sl-card">
      <table class="sl-table sl-desktop-table">
        <thead><tr>
          <th @click="sort('posting_date')" class="sortable">Date <span v-html="sortArrow('posting_date')"></span></th>
          <th @click="sort('item_code')" class="sortable">Item <span v-html="sortArrow('item_code')"></span></th>
          <th @click="sort('warehouse')" class="sortable">Warehouse <span v-html="sortArrow('warehouse')"></span></th>
          <th>Voucher Type</th><th>Voucher #</th>
          <th @click="sort('actual_qty')" class="sortable ta-r">Qty In/Out <span v-html="sortArrow('actual_qty')"></span></th>
          <th @click="sort('qty_after_transaction')" class="sortable ta-r">Balance Qty <span v-html="sortArrow('qty_after_transaction')"></span></th>
          <th class="ta-r">Value</th>
        </tr></thead>
        <tbody>
          <template v-if="loading"><tr v-for="n in 10" :key="n"><td colspan="8"><div class="sl-shimmer"></div></td></tr></template>
          <template v-else>
            <tr v-for="e in sorted" :key="e.name" class="sl-row" @click="openView(e)">
              <td class="mono-sm text-muted">{{ fmtDate(e.posting_date) }}</td>
              <td class="font-medium">{{ e.item_code }}</td>
              <td class="text-muted">{{ e.warehouse }}</td>
              <td class="text-muted" style="font-size:12px">{{ e.voucher_type }}</td>
              <td><span class="sl-voucher">{{ e.voucher_no }}</span></td>
              <td class="ta-r mono-sm" :class="flt(e.actual_qty)>0?'green':'red'">{{ flt(e.actual_qty)>0?'+':'' }}{{ fmtQty(e.actual_qty) }}</td>
              <td class="ta-r mono-sm">{{ fmtQty(e.qty_after_transaction) }}</td>
              <td class="ta-r mono-sm">{{ fmtCur(e.stock_value_difference) }}</td>
            </tr>
            <tr v-if="!sorted.length"><td colspan="8" class="sl-empty">{{ loaded?(list.length?'No entries match this filter':'No ledger entries found'):'Run to view stock ledger' }}</td></tr>
          </template>
        </tbody>
      </table>

      <!-- Mobile cards (shown at ≤768px) -->
      <div class="sl-mobile-cards">
        <template v-if="loading">
          <div v-for="n in 6" :key="n" class="sl-mobile-card sl-mc--skeleton">
            <div class="sl-mc-shimmer" style="height:13px;width:55%;margin-bottom:8px"></div>
            <div class="sl-mc-shimmer" style="height:11px;width:40%;margin-bottom:6px"></div>
            <div class="sl-mc-shimmer" style="height:11px;width:65%"></div>
          </div>
        </template>
        <div v-else-if="!sorted.length" class="sl-mc-empty">
          <div style="font-size:32px;margin-bottom:8px">📒</div>
          <div>{{ loaded?(list.length?'No entries match':'No ledger entries'):'Run filters to view ledger' }}</div>
        </div>
        <template v-else>
          <div v-for="e in sorted" :key="e.name" class="sl-mobile-card" @click="openView(e)">
            <div class="sl-mc-top">
              <span class="sl-mc-date">{{ fmtDate(e.posting_date) }}</span>
              <span :class="flt(e.actual_qty)>0?'sl-mc-pos':'sl-mc-neg'">
                {{ flt(e.actual_qty)>0?'+':'' }}{{ fmtQty(e.actual_qty) }}
              </span>
            </div>
            <div class="sl-mc-mid">{{ e.item_code }}</div>
            <div class="sl-mc-meta">
              <span>{{ e.voucher_type }} · {{ e.voucher_no }}</span>
              <span>Bal: {{ fmtQty(e.qty_after_transaction) }}</span>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- Detail drawer -->
    <div v-if="viewOpen" class="sl-overlay" @click.self="viewOpen=false"></div>
    <div class="sl-drawer" :class="{open:viewOpen}">
      <template v-if="viewDoc">
        <div class="sl-dheader">
          <button class="sl-dclose" @click="viewOpen=false"><span v-html="icon('x',16)"></span></button>
          <div class="sl-dh-top">
            <div class="sl-dh-ico"><span v-html="icon('ledger',20)"></span></div>
            <div>
              <div class="sl-dh-title">{{ viewDoc.item_code }}</div>
              <div class="sl-dh-sub">{{ viewDoc.warehouse }} · {{ fmtDate(viewDoc.posting_date) }}<template v-if="viewDoc.posting_time"> {{ viewDoc.posting_time }}</template></div>
            </div>
            <span class="sl-badge" :class="flt(viewDoc.actual_qty)>=0?'badge-green':'badge-red'">{{ flt(viewDoc.actual_qty)>=0?'Inward':'Outward' }}</span>
          </div>
          <div class="sl-dh-amount">
            <div class="sl-dh-amt-lbl">Quantity {{ flt(viewDoc.actual_qty)>=0?'In':'Out' }}</div>
            <div class="sl-dh-amt-val" :class="flt(viewDoc.actual_qty)>=0?'green':'red'">{{ flt(viewDoc.actual_qty)>0?'+':'' }}{{ fmtQty(viewDoc.actual_qty) }}</div>
          </div>
        </div>
        <div class="sl-dbody">
          <div class="sl-section-hdr"><span v-html="icon('info',13)"></span> Movement</div>
          <div class="sl-meta-grid">
            <div><div class="sl-meta-lbl">Balance After</div><div >{{ fmtQty(viewDoc.qty_after_transaction) }}</div></div>
            <div><div class="sl-meta-lbl">Valuation Rate</div><div >{{ fmtCur(viewDoc.valuation_rate) }}</div></div>
            <div><div class="sl-meta-lbl">Value Change</div><div  :class="flt(viewDoc.stock_value_difference)>=0?'green':'red'">{{ fmtCur(viewDoc.stock_value_difference) }}</div></div>
            <div><div class="sl-meta-lbl">Posting Date</div><div >{{ fmtDate(viewDoc.posting_date) }}<template v-if="viewDoc.posting_time"> {{ viewDoc.posting_time }}</template></div></div>
          </div>
          <div class="sl-section-hdr"><span v-html="icon('file',13)"></span> Source Voucher</div>
          <div class="sl-meta-grid">
            <div><div class="sl-meta-lbl">Type</div><div>{{ viewDoc.voucher_type||'—' }}</div></div>
            <div><div class="sl-meta-lbl">Number</div><div  style="color:#2563eb">{{ viewDoc.voucher_no||'—' }}</div></div>
          </div>
          <button v-if="viewDoc.voucher_type==='Stock Entry'" class="sl-link-btn" @click="goVoucher(viewDoc)">
            <span v-html="icon('ext',14)"></span> Open Stock Entry
          </button>
        </div>
        <div class="sl-dfooter"><button class="sl-btn-ghost" @click="viewOpen=false">Close</button></div>
      </template>
    </div>
  </div>
</template>
<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { apiList, resolveCompany, apiLinkValues } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";
import { flt, fmtDate } from "../utils/format.js";
import SearchableSelect from "../components/SearchableSelect.vue";
import SummaryStrip from "../components/SummaryStrip.vue";
const { toast } = useToast();
const router = useRouter();
const list=ref([]),loading=ref(false),loaded=ref(false);
const items=ref([]),warehouses=ref([]);
const search=ref(""), dirFilter=ref("all");
const viewOpen=ref(false), viewDoc=ref(null);
const sortCol=ref("posting_date"),sortDir=ref("desc");
const now=new Date();
const firstOfMonth=new Date(now.getFullYear(),now.getMonth(),1).toISOString().slice(0,10);
const filters=reactive({item:"",warehouse:"",from_date:firstOfMonth,to_date:now.toISOString().slice(0,10)});
async function load(){loading.value=true;loaded.value=true;try{const co=await resolveCompany();const f=[["company","=",co]];if(filters.item)f.push(["item_code","=",filters.item]);if(filters.warehouse)f.push(["warehouse","=",filters.warehouse]);if(filters.from_date)f.push(["posting_date",">=",filters.from_date]);if(filters.to_date)f.push(["posting_date","<=",filters.to_date]);list.value=await apiList("Stock Ledger Entry",{fields:["name","posting_date","posting_time","item_code","warehouse","voucher_type","voucher_no","actual_qty","qty_after_transaction","stock_value_difference","valuation_rate"],filters:f,limit:100000,order:"posting_date asc"});}catch(e){toast.error(e.message||"Failed to load stock ledger");}finally{loading.value=false;}}
const filteredRows=computed(()=>{
  let r=list.value;
  if(dirFilter.value==="in")r=r.filter(e=>flt(e.actual_qty)>0);
  else if(dirFilter.value==="out")r=r.filter(e=>flt(e.actual_qty)<0);
  if(search.value.trim()){const q=search.value.toLowerCase();r=r.filter(e=>(e.item_code||"").toLowerCase().includes(q)||(e.voucher_no||"").toLowerCase().includes(q)||(e.warehouse||"").toLowerCase().includes(q)||(e.voucher_type||"").toLowerCase().includes(q));}
  return r;
});
const sorted=computed(()=>{const col=sortCol.value;return[...filteredRows.value].sort((a,b)=>{const av=a[col]??"",bv=b[col]??"";const c=typeof av==="number"?av-bv:String(av).localeCompare(String(bv));return sortDir.value==="asc"?c:-c;});});
function sort(col){if(sortCol.value===col)sortDir.value=sortDir.value==="asc"?"desc":"asc";else{sortCol.value=col;sortDir.value="asc";}}
function sortArrow(col){if(sortCol.value!==col)return'<span style="color:#d1d5db">⇅</span>';return sortDir.value==="asc"?"↑":"↓";}
const dirTabs=computed(()=>[
  {key:"all",label:"All",count:list.value.length},
  {key:"in",label:"Inward",count:list.value.filter(e=>flt(e.actual_qty)>0).length},
  {key:"out",label:"Outward",count:list.value.filter(e=>flt(e.actual_qty)<0).length},
]);
const summaryIn=computed(()=>filteredRows.value.filter(e=>flt(e.actual_qty)>0).reduce((s,e)=>s+flt(e.actual_qty),0));
const summaryOut=computed(()=>filteredRows.value.filter(e=>flt(e.actual_qty)<0).reduce((s,e)=>s+Math.abs(flt(e.actual_qty)),0));
const stockValue=computed(()=>filteredRows.value.reduce((s,e)=>s+flt(e.stock_value_difference),0));
function openView(e){viewDoc.value=e;viewOpen.value=true;}
function goVoucher(e){if(e.voucher_no)router.push({name:"stock-entries",query:{open:e.voucher_no}});}
function fmtCur(v){return new Intl.NumberFormat("en-IN",{style:"currency",currency:"INR",minimumFractionDigits:2}).format(flt(v));}
function fmtQty(v){return Number(flt(v)).toLocaleString("en-IN",{maximumFractionDigits:3});}
function exportCSV(){
  const rows=sorted.value;
  if(!rows.length)return;
  const esc=v=>{const s=v==null?"":String(v);return /[",\n]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s;};
  const lines=[["Date","Item","Warehouse","Voucher Type","Voucher #","Qty In/Out","Balance Qty","Value Change","Valuation Rate"].join(",")];
  for(const e of rows){
    lines.push([fmtDate(e.posting_date),e.item_code||"",e.warehouse||"",e.voucher_type||"",e.voucher_no||"",flt(e.actual_qty),flt(e.qty_after_transaction),flt(e.stock_value_difference),flt(e.valuation_rate)].map(esc).join(","));
  }
  const blob=new Blob(["﻿"+lines.join("\r\n")],{type:"text/csv;charset=utf-8;"});
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a");
  a.href=url;a.download=`stock_ledger_${filters.from_date}_to_${filters.to_date}.csv`;
  a.click();URL.revokeObjectURL(url);
  toast.success(`Exported ${rows.length} row(s)`);
}
async function fetchItems(q=""){try{const r=await apiLinkValues("Item",q);items.value=r.map(x=>({label:x.name,value:x.name}));}catch{items.value=[];}}
async function fetchWarehouses(q=""){try{const co=await resolveCompany();const r=await apiList("Warehouse",{fields:["name"],filters:[["company","=",co],["is_group","=",0],...(q?[["name","like",`%${q}%`]]:[])],limit:20});warehouses.value=r.map(x=>({label:x.name,value:x.name}));}catch{warehouses.value=[];}}
// Pre-load dropdown options so the pickers aren't empty on first open.
onMounted(()=>{fetchItems("");fetchWarehouses("");});
</script>
<style scoped>
.sl-page{display:flex;flex-direction:column;gap:16px;padding:24px;}
/* premium filter bar */
.sl-filterbar{display:flex;align-items:flex-end;gap:12px;flex-wrap:wrap;background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:14px 16px;}
.sl-fld{display:flex;flex-direction:column;gap:5px;}
.sl-fld-item{flex:1 1 220px;max-width:300px;}
.sl-fld-wh{flex:1 1 200px;max-width:260px;}
.sl-fld-date{width:160px;}
.sl-fld-lbl{font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#94a3b8;}
.sl-input{width:100%;box-sizing:border-box;border:1px solid #e2e8f0;border-radius:8px;padding:8px 11px;font:inherit;font-size:13px;outline:none;background:#fff;color:#0f172a;transition:border-color .15s,box-shadow .15s;}
.sl-input:focus{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.1);}
.sl-btn-primary{display:inline-flex;align-items:center;gap:6px;background:#2563eb;color:#fff;border:none;border-radius:8px;padding:9px 16px;font-size:13px;font-weight:600;cursor:pointer;}
.sl-btn-primary:hover{background:#1d4ed8;}
.sl-btn-ghost{display:inline-flex;align-items:center;gap:6px;background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:9px 14px;font-size:13px;font-weight:600;color:#334155;cursor:pointer;}
.sl-btn-ghost:hover:not(:disabled){background:#f8fafc;border-color:#cbd5e1;}.sl-btn-ghost:disabled{opacity:.5;cursor:not-allowed;}
.green{color:#16a34a!important;}.red{color:#dc2626!important;}
.sl-toolbar-right{display:flex;align-items:center;gap:12px;}
.sl-result{font-size:12px;color:#94a3b8;font-weight:600;white-space:nowrap;}
/* toolbar */
.sl-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;}
.sl-filter-pills{display:inline-flex;align-items:center;gap:3px;background:#eef2f7;border:1px solid #e2e8f0;border-radius:12px;padding:4px;}
.sl-fpill{display:inline-flex;align-items:center;gap:7px;padding:7px 14px;border-radius:9px;font-size:12.5px;font-weight:600;border:none;background:transparent;color:#64748b;cursor:pointer;font-family:inherit;transition:color .15s,background .15s,box-shadow .15s;}
.sl-fpill:hover:not(.active){color:#334155;}
.sl-fpill.active{background:#fff;color:#1d4ed8;box-shadow:0 1px 2px rgba(15,23,42,.08),0 0 0 1px rgba(37,99,235,.08);}
.sl-fpill-count{display:inline-flex;align-items:center;justify-content:center;min-width:19px;height:18px;padding:0 6px;border-radius:9px;background:rgba(100,116,139,.16);color:#64748b;font-size:10.5px;font-weight:700;line-height:1;}
.sl-fpill.active .sl-fpill-count{background:#dbeafe;color:#1d4ed8;}
.sl-search-wrap{display:flex;align-items:center;gap:8px;background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:7px 12px;min-width:260px;transition:border-color .15s,box-shadow .15s;}
.sl-search-wrap:focus-within{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.1);}
.sl-search-input{border:none;background:transparent;outline:none;font:inherit;font-size:13px;color:#0f172a;width:100%;}
.sl-card{background:#fff;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;}
.sl-table{width:100%;border-collapse:collapse;font-size:13px;}
.sl-table th{background:#f9fafb;border-bottom:1px solid #e5e7eb;padding:10px 12px;font-size:11.5px;font-weight:600;color:#374151;text-align:left;white-space:nowrap;text-transform:uppercase;}
.sl-table th.sortable{cursor:pointer;user-select:none;}.sl-table th.sortable:hover{color:#2563eb;}
.ta-r{text-align:right!important;}
.sl-row td{padding:9px 12px;border-bottom:1px solid #f3f4f6;cursor:pointer;}
.sl-row:last-child td{border-bottom:none;}.sl-row:hover td{background:#f9fafb;}
.sl-voucher{font-size:12px;color:#2563eb;}
.font-medium{font-weight:600;}.mono-sm{font-size:12.5px;}.text-muted{color:#6b7280;}
.sl-empty{text-align:center;color:#9ca3af;padding:48px!important;}
.sl-shimmer{height:13px;background:linear-gradient(90deg,#f3f4f6 25%,#e5e7eb 50%,#f3f4f6 75%);border-radius:4px;animation:shimmer 1.2s infinite;background-size:200% 100%;}
@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}

/* detail drawer */
.sl-overlay{position:fixed;inset:0;background:rgba(15,23,42,.28);z-index:40;}
.sl-drawer{position:fixed;top:0;right:-420px;bottom:0;width:420px;max-width:96vw;background:#fff;border-left:1px solid #e5e7eb;box-shadow:-8px 0 28px rgba(15,23,42,.12);z-index:50;display:flex;flex-direction:column;transition:right .24s ease;}
.sl-drawer.open{right:0;}
.sl-dheader{position:relative;flex-shrink:0;padding:20px;border-bottom:1px solid #e5e7eb;background:linear-gradient(135deg,#eff6ff 0%,#dbeafe 100%);}
.sl-dclose{position:absolute;top:12px;right:12px;background:transparent;border:none;cursor:pointer;color:#475569;display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border-radius:8px;}
.sl-dclose:hover{background:rgba(255,255,255,.6);color:#0f172a;}
.sl-dh-top{display:flex;align-items:center;gap:13px;padding-right:36px;}
.sl-dh-ico{width:42px;height:42px;background:#fff;border-radius:11px;display:flex;align-items:center;justify-content:center;color:#2563eb;flex-shrink:0;box-shadow:0 1px 3px rgba(15,23,42,.08);}
.sl-dh-title{font-size:15px;font-weight:700;color:#0f172a;}
.sl-dh-sub{font-size:12px;color:#475569;margin-top:1px;}
.sl-dh-top .sl-badge{margin-left:auto;}
.sl-badge{display:inline-flex;align-items:center;padding:2px 8px;border-radius:10px;font-size:11.5px;font-weight:600;}
.badge-green{background:#dcfce7;color:#16a34a;}.badge-red{background:#fee2e2;color:#dc2626;}
.sl-dh-amount{margin-top:16px;}
.sl-dh-amt-lbl{font-size:10.5px;color:#64748b;text-transform:uppercase;letter-spacing:.05em;font-weight:600;}
.sl-dh-amt-val{font-size:26px;font-weight:800;letter-spacing:-.01em;margin-top:2px;}
.sl-dbody{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:12px;}
.sl-section-hdr{display:flex;align-items:center;gap:8px;font-size:11.5px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:#0f172a;margin-top:4px;}
.sl-section-hdr span{color:#2563eb;display:inline-flex;}
.sl-meta-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
.sl-meta-lbl{font-size:10.5px;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;margin-bottom:2px;font-weight:600;}
.sl-link-btn{display:inline-flex;align-items:center;gap:6px;align-self:flex-start;background:#eff6ff;border:1px solid #bfdbfe;color:#1d4ed8;border-radius:8px;padding:8px 12px;font:inherit;font-size:12.5px;font-weight:600;cursor:pointer;margin-top:4px;}
.sl-link-btn:hover{background:#dbeafe;}
.sl-dfooter{display:flex;justify-content:flex-end;padding:14px 20px;border-top:1px solid #e5e7eb;flex-shrink:0;}

/* ── Mobile card defaults ── */
.sl-mobile-cards { display: none; }
.sl-desktop-table { display: table; }

@media (max-width: 768px) {
  .sl-drawer { width: 100% !important; right: -100% !important; max-width: 100%; }
  .sl-drawer.open { right: 0 !important; }
  .sl-search-wrap { min-width: 0; flex: 1 1 auto; }
  .sl-toolbar { flex-wrap: wrap; }
  .sl-desktop-table { display: none !important; }
  .sl-mobile-cards { display: flex; flex-direction: column; gap: 0; background: #f8fafc; }
  .sl-mobile-card { background: #fff; border-bottom: 1px solid #e5e7eb; padding: 12px 14px; cursor: pointer; transition: background .12s; }
  .sl-mobile-card:active { background: #f8f9fc; }
  .sl-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .sl-mc-date { font-size: 12px; font-weight: 700; color: #2563eb; }
  .sl-mc-pos { font-weight: 700; color: #16a34a; }
  .sl-mc-neg { font-weight: 700; color: #dc2626; }
  .sl-mc-mid { font-size: 13.5px; font-weight: 600; color: #1a1d23; margin-bottom: 4px; }
  .sl-mc-meta { display: flex; justify-content: space-between; font-size: 12px; color: #868e96; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; gap: 8px; }
  .sl-mc--skeleton { pointer-events: none; }
  .sl-mc-shimmer { border-radius: 6px; background: linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size: 200% 100%; animation: sl-mc-sh 1.4s infinite; }
  @keyframes sl-mc-sh { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
  .sl-mc-empty { text-align: center; padding: 32px 16px; color: #868e96; font-size: 13px; }
}
@media (max-width: 480px) {
  .sl-page { padding: 12px; gap: 12px; }
  .sl-filterbar { padding: 12px; gap: 8px; }
  .sl-fld-date { width: 100%; }
  .sl-meta-grid { grid-template-columns: 1fr !important; }
}
</style>