<template>
  <div class="sv-page">
    <div class="sv-filterbar">
      <div class="sv-fld sv-fld-wh">
        <label class="sv-fld-lbl">Warehouse</label>
        <SearchableSelect v-model="filters.warehouse" :options="warehouses" placeholder="All warehouses" @search="fetchWarehouses" />
      </div>
      <div class="sv-fld sv-fld-grp">
        <label class="sv-fld-lbl">Item Group</label>
        <SearchableSelect v-model="filters.item_group" :options="itemGroups" placeholder="All item groups" @search="fetchItemGroups" />
      </div>
      <button class="sv-btn-primary" @click="load"><span v-html="icon('refresh',13)"></span> Refresh</button>
      <button class="sv-btn-ghost" @click="exportCSV" :disabled="!list.length"><span v-html="icon('download',13)"></span> Export</button>
      <span class="sv-asof">As of today</span>
    </div>

    <SummaryStrip v-if="!loading && list.length" :cards="[
      { label:'Total Items', tone:'default', value: list.length },
      { label:'Total Stock Value', tone:'accent', value: fmtCur(totalValue), valueClass:'blue' },
      { label:'Zero Stock Items', tone: zeroStock>0?'warn':'default', value: zeroStock, valueClass: zeroStock>0?'orange':'' },
      { label:'Total Qty', tone:'info', value: fmtQty(totalQty) },
    ]" />

    <div v-if="!loading && list.length" class="sv-toolbar">
      <span class="sv-result">{{ sorted.length }} item{{ sorted.length===1?'':'s' }}</span>
      <div class="sv-search-wrap">
        <span v-html="icon('search',13)" style="color:#94a3b8;flex-shrink:0"></span>
        <input v-model="search" placeholder="Search item / group…" class="sv-search-input" />
      </div>
    </div>

    <div class="sv-card">
      <table class="sv-table sv-desktop-table">
        <thead><tr>
          <th @click="sort('item_code')" class="sortable">Item <span v-html="sortArrow('item_code')"></span></th>
          <th @click="sort('item_name')" class="sortable">Item Name <span v-html="sortArrow('item_name')"></span></th>
          <th @click="sort('item_group')" class="sortable">Group <span v-html="sortArrow('item_group')"></span></th>
          <th>UOM</th>
          <th @click="sort('actual_qty')" class="sortable ta-r">Qty <span v-html="sortArrow('actual_qty')"></span></th>
          <th @click="sort('valuation_rate')" class="sortable ta-r">Rate <span v-html="sortArrow('valuation_rate')"></span></th>
          <th class="ta-r" style="width:70px">Landed?</th>
          <th @click="sort('stock_value')" class="sortable ta-r">Stock Value <span v-html="sortArrow('stock_value')"></span></th>
          <th style="width:80px"></th>
        </tr></thead>
        <tbody>
          <template v-if="loading"><tr v-for="n in 10" :key="n"><td colspan="9"><div class="sv-shimmer"></div></td></tr></template>
          <template v-else>
            <tr v-for="i in sorted" :key="i.item_code+i.warehouse" class="sv-row">
              <td><span class="sv-code">{{ i.item_code }}</span></td>
              <td>{{ i.item_name||i.item_code }}</td>
              <td class="text-muted">{{ i.item_group||'—' }}</td>
              <td class="text-muted">{{ i.stock_uom||'—' }}</td>
              <td class="ta-r mono-sm" :class="flt(i.actual_qty)<=0?'red':''">{{ fmtQty(i.actual_qty) }}</td>
              <td class="ta-r mono-sm" :title="rateTooltip(i)">{{ fmtCur(i.valuation_rate) }}</td>
              <td class="ta-r">
                <span v-if="landedInfo(i).has_landed_cost" class="sv-landed-badge" :title="rateTooltip(i)">🚚 {{ fmtCur(landedInfo(i).landed_rate) }}</span>
                <span v-else class="text-muted">—</span>
              </td>
              <td class="ta-r mono-sm font-medium">{{ fmtCur(i.stock_value) }}</td>
              <td class="ta-r"><button class="sv-adjust-btn" @click="goAdjust(i)">Adjust</button></td>
            </tr>
            <tr v-if="!sorted.length"><td colspan="9" class="sv-empty">{{ list.length ? 'No items match your search' : 'No stock data found' }}</td></tr>
          </template>
        </tbody>
      </table>

      <!-- Mobile cards (shown at ≤768px) -->
      <div class="sv-mobile-cards">
        <template v-if="loading">
          <div v-for="n in 6" :key="n" class="sv-mobile-card sv-mc--skeleton">
            <div class="sv-mc-shimmer" style="height:13px;width:55%;margin-bottom:8px"></div>
            <div class="sv-mc-shimmer" style="height:11px;width:40%;margin-bottom:6px"></div>
            <div class="sv-mc-shimmer" style="height:11px;width:65%"></div>
          </div>
        </template>
        <div v-else-if="!sorted.length" class="sv-mc-empty">
          <div style="font-size:32px;margin-bottom:8px">📦</div>
          <div>{{ list.length ? 'No items match' : 'No stock data found' }}</div>
        </div>
        <template v-else>
          <div v-for="i in sorted" :key="i.item_code+i.warehouse" class="sv-mobile-card">
            <div class="sv-mc-top">
              <span class="sv-mc-code">{{ i.item_code }}</span>
              <span class="sv-mc-value">{{ fmtCur(i.stock_value) }}</span>
            </div>
            <div class="sv-mc-mid">{{ i.item_name||i.item_code }}</div>
            <div class="sv-mc-meta">
              <span :class="flt(i.actual_qty)<=0?'sv-mc-neg':''">{{ fmtQty(i.actual_qty) }} {{ i.stock_uom||'' }}</span>
              <span v-if="landedInfo(i).has_landed_cost" class="sv-landed-badge" :title="rateTooltip(i)">🚚 landed</span>
              <button class="sv-adjust-btn" @click.stop="goAdjust(i)">Adjust</button>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { apiList, apiGET, apiCall, resolveCompany, apiLinkValues } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";
import { flt } from "../utils/format.js";
import SearchableSelect from "../components/SearchableSelect.vue";
import SummaryStrip from "../components/SummaryStrip.vue";
const { toast } = useToast();
const router = useRouter();
const list=ref([]),loading=ref(false),search=ref("");
const landedByBin=ref({});
function goAdjust(i){ router.push({ name:"inventory-adjustments", query:{ item:i.item_code, warehouse:i.warehouse } }); }
function landedInfo(i){
  return landedByBin.value[`${i.item_code}::${i.warehouse}`] || { has_landed_cost:false, base_rate:i.valuation_rate, landed_rate:0, valuation_rate:i.valuation_rate };
}
function rateTooltip(i){
  const li=landedInfo(i);
  if(!li.has_landed_cost) return "No landed costs capitalized into this rate.";
  return `Base rate ${fmtCur(li.base_rate)} + landed cost ${fmtCur(li.landed_rate)} = ${fmtCur(li.valuation_rate)} per unit`;
}
async function loadLandedBreakdown(rows){
  const pairs=rows.filter(r=>r.item_code&&r.warehouse).map(r=>({item_code:r.item_code,warehouse:r.warehouse}));
  if(!pairs.length){landedByBin.value={};return;}
  try{
    const r=await apiCall("zoho_books_clone.inventory.landed_cost_engine.get_landed_cost_breakdown",{pairs:JSON.stringify(pairs)});
    landedByBin.value=r||{};
  }catch(e){ landedByBin.value={}; } // non-fatal — base rate still shows fine without the breakdown
}
const warehouses=ref([]),itemGroups=ref([]);
const sortCol=ref("stock_value"),sortDir=ref("desc");
const filters=reactive({warehouse:"",item_group:""});
async function load(){
  loading.value=true;
  try{
    // get_stock_summary returns item_name + item_group and honours the
    // item-group filter (raw Bin has neither field). Only include filter keys
    // when set — passing undefined would serialize to the string "undefined".
    const params={show_zero_stock:1};
    if(filters.warehouse)params.warehouse=filters.warehouse;
    if(filters.item_group)params.item_group=filters.item_group;
    const r=await apiGET("zoho_books_clone.api.inventory.get_stock_summary",params);
    const rows=Array.isArray(r)?r:(r?.message||[]);
    list.value=rows.map(x=>({...x,stock_uom:x.uom||x.stock_uom||""}));
    loadLandedBreakdown(list.value);
  }catch(e){toast.error(e.message||"Failed to load valuation");}finally{loading.value=false;}
}
const filteredRows=computed(()=>{
  if(!search.value.trim())return list.value;
  const q=search.value.toLowerCase();
  return list.value.filter(i=>(i.item_code||"").toLowerCase().includes(q)||(i.item_name||"").toLowerCase().includes(q)||(i.item_group||"").toLowerCase().includes(q));
});
const sorted=computed(()=>{const col=sortCol.value;return[...filteredRows.value].sort((a,b)=>{const av=a[col]??"",bv=b[col]??"";const c=typeof av==="number"?av-bv:String(av).localeCompare(String(bv));return sortDir.value==="asc"?c:-c;});});
function sort(col){if(sortCol.value===col)sortDir.value=sortDir.value==="asc"?"desc":"asc";else{sortCol.value=col;sortDir.value="asc";}}
function sortArrow(col){if(sortCol.value!==col)return'<span style="color:#d1d5db">⇅</span>';return sortDir.value==="asc"?"↑":"↓";}
const totalValue=computed(()=>list.value.reduce((s,i)=>s+flt(i.stock_value),0));
const totalQty=computed(()=>list.value.reduce((s,i)=>s+flt(i.actual_qty),0));
const zeroStock=computed(()=>list.value.filter(i=>flt(i.actual_qty)<=0).length);
function fmtCur(v){return new Intl.NumberFormat("en-IN",{style:"currency",currency:"INR",minimumFractionDigits:2}).format(flt(v));}
function fmtQty(v){return Number(flt(v)).toLocaleString("en-IN",{maximumFractionDigits:3});}
function exportCSV(){
  const rows=sorted.value;
  if(!rows.length)return;
  const esc=v=>{const s=v==null?"":String(v);return /[",\n]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s;};
  const lines=[["Item","Item Name","Group","Warehouse","UOM","Qty","Rate","Base Rate","Landed Rate","Stock Value"].join(",")];
  for(const i of rows){
    const li=landedInfo(i);
    lines.push([i.item_code||"",i.item_name||"",i.item_group||"",i.warehouse||"",i.stock_uom||"",flt(i.actual_qty),flt(i.valuation_rate),flt(li.base_rate),flt(li.landed_rate),flt(i.stock_value)].map(esc).join(","));
  }
  const blob=new Blob(["﻿"+lines.join("\r\n")],{type:"text/csv;charset=utf-8;"});
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a");
  a.href=url;a.download=`stock_valuation_${new Date().toISOString().slice(0,10)}.csv`;
  a.click();URL.revokeObjectURL(url);
  toast.success(`Exported ${rows.length} row(s)`);
}
async function fetchWarehouses(q=""){try{const co=await resolveCompany();const r=await apiList("Warehouse",{fields:["name"],filters:[["company","=",co],["is_group","=",0],...(q?[["name","like",`%${q}%`]]:[])],limit:20});warehouses.value=r.map(x=>({label:x.name,value:x.name}));}catch{warehouses.value=[];}}
async function fetchItemGroups(q=""){try{const r=await apiLinkValues("Item Group",q);itemGroups.value=r.map(x=>({label:x.name,value:x.name}));}catch{itemGroups.value=[];}}
onMounted(()=>{load();fetchWarehouses("");fetchItemGroups("");});
</script>
<style scoped>
.sv-page{display:flex;flex-direction:column;gap:16px;padding:24px;}
/* premium filter bar */
.sv-filterbar{display:flex;align-items:flex-end;gap:12px;flex-wrap:wrap;background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:14px 16px;}
.sv-fld{display:flex;flex-direction:column;gap:5px;}
.sv-fld-wh{flex:1 1 220px;max-width:300px;}
.sv-fld-grp{flex:1 1 200px;max-width:260px;}
.sv-fld-lbl{font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#94a3b8;}
.sv-asof{margin-left:auto;align-self:center;color:#94a3b8;font-size:12px;font-weight:600;}
.sv-btn-primary{display:inline-flex;align-items:center;gap:6px;background:#2563eb;color:#fff;border:none;border-radius:8px;padding:9px 16px;font-size:13px;font-weight:600;cursor:pointer;}
.sv-btn-primary:hover{background:#1d4ed8;}
.sv-btn-ghost{display:inline-flex;align-items:center;gap:6px;background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:9px 14px;font-size:13px;font-weight:600;color:#334155;cursor:pointer;}
.sv-btn-ghost:hover:not(:disabled){background:#f8fafc;border-color:#cbd5e1;}.sv-btn-ghost:disabled{opacity:.5;cursor:not-allowed;}
.blue{color:#2563eb!important;}.orange{color:#ea580c!important;}.red{color:#dc2626!important;}
/* toolbar */
.sv-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;}
.sv-result{font-size:12px;color:#94a3b8;font-weight:600;white-space:nowrap;}
.sv-search-wrap{display:flex;align-items:center;gap:8px;background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:7px 12px;min-width:240px;transition:border-color .15s,box-shadow .15s;}
.sv-search-wrap:focus-within{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.1);}
.sv-search-input{border:none;background:transparent;outline:none;font:inherit;font-size:13px;color:#0f172a;width:100%;}
.sv-card{background:#fff;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;}
.sv-table{width:100%;border-collapse:collapse;font-size:13px;}
.sv-table th{background:#f9fafb;border-bottom:1px solid #e5e7eb;padding:10px 12px;font-size:11.5px;font-weight:600;color:#374151;text-align:left;white-space:nowrap;text-transform:uppercase;}
.sv-table th.sortable{cursor:pointer;user-select:none;}.sv-table th.sortable:hover{color:#2563eb;}
.ta-r{text-align:right!important;}
.sv-row td{padding:9px 12px;border-bottom:1px solid #f3f4f6;}
.sv-row:last-child td{border-bottom:none;}.sv-row:hover td{background:#f9fafb;}
.sv-code{font-size:12.5px;color:#2563eb;font-weight:600;}
.sv-adjust-btn{background:#eff6ff;border:1px solid #bfdbfe;color:#1d4ed8;border-radius:7px;padding:4px 10px;font:inherit;font-size:11.5px;font-weight:600;cursor:pointer;}
.sv-adjust-btn:hover{background:#dbeafe;}
.sv-landed-badge{display:inline-flex;align-items:center;gap:3px;background:#fff3bf;color:#e67700;border-radius:6px;padding:2px 7px;font-size:11px;font-weight:700;cursor:help;white-space:nowrap;}
.mono-sm{font-size:13px;}.font-medium{font-weight:600;}.text-muted{color:#6b7280;}
.sv-empty{text-align:center;color:#9ca3af;padding:48px!important;}
.sv-shimmer{height:13px;background:linear-gradient(90deg,#f3f4f6 25%,#e5e7eb 50%,#f3f4f6 75%);border-radius:4px;animation:shimmer 1.2s infinite;background-size:200% 100%;}
@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}

/* ── Mobile card defaults ── */
.sv-mobile-cards { display: none; }
.sv-desktop-table { display: table; }

@media (max-width: 768px) {
  .sv-search-wrap { min-width: 0; flex: 1 1 auto; }
  .sv-filterbar { padding: 12px; gap: 8px; }
  .sv-desktop-table { display: none !important; }
  .sv-mobile-cards { display: flex; flex-direction: column; gap: 0; background: #f8fafc; }
  .sv-mobile-card { background: #fff; border-bottom: 1px solid #e5e7eb; padding: 12px 14px; transition: background .12s; }
  .sv-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .sv-mc-code { font-size: 12px; font-weight: 700; color: #2563eb; }
  .sv-mc-value { font-size: 13px; font-weight: 700; color: #1a1d23; }
  .sv-mc-mid { font-size: 13.5px; font-weight: 600; color: #1a1d23; margin-bottom: 6px; }
  .sv-mc-meta { display: flex; align-items: center; justify-content: space-between; font-size: 12px; color: #868e96; }
  .sv-mc-neg { color: #dc2626; font-weight: 700; }
  .sv-mc--skeleton { pointer-events: none; }
  .sv-mc-shimmer { border-radius: 6px; background: linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size: 200% 100%; animation: sv-mc-sh 1.4s infinite; }
  @keyframes sv-mc-sh { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
  .sv-mc-empty { text-align: center; padding: 32px 16px; color: #868e96; font-size: 13px; }
}
@media (max-width: 480px) {
  .sv-page { padding: 12px; gap: 12px; }
  .sv-asof { display: none; }
}
</style>