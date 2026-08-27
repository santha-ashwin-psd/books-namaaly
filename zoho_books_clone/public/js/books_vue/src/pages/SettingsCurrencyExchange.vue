<template>
<div class="cust-page" style="padding:0">
  <div class="cust-toolbar" style="background:#1A237E;color:#fff;border-radius:0;padding:14px 24px;display:flex;align-items:center;justify-content:space-between;gap:12px">
    <div style="display:flex;align-items:center;gap:12px">
      <span style="font-size:22px">💱</span>
      <div>
        <div style="font-size:17px;font-weight:700;letter-spacing:.3px">Currency &amp; Exchange</div>
        <div style="font-size:12px;opacity:.75">Manage currencies, exchange rates &amp; forex P&amp;L</div>
      </div>
    </div>
    <div style="display:flex;gap:8px">
      <button class="nim-btn nim-btn-ghost" style="color:#fff;border-color:rgba(255,255,255,.35)" @click="refreshRates" :disabled="refreshing">
        <span v-if="refreshing">⟳</span><span v-else>↺</span> Refresh Rates
      </button>
      <button class="nim-btn nim-btn-primary" :disabled="!$canWrite('admin')" :title="!$canWrite('admin') ? 'Read-only access' : ''" style="background:#fff;color:#1A237E;border-color:#fff" @click="openAddCurrency">+ Add Currency</button>
    </div>
  </div>

  <div style="background:#fff;border-bottom:1px solid #e4e8f0;padding:0 24px;display:flex;gap:0">
    <button v-for="t in tabs" :key="t.id" @click="activeTab=t.id"
      :style="'padding:12px 20px;border:none;background:none;cursor:pointer;font-size:13px;font-weight:600;white-space:nowrap;transition:all .15s;color:'+(activeTab===t.id?'#1A237E':'#666')+';border-bottom:2px solid '+(activeTab===t.id?'#1A237E':'transparent')">
      {{t.label}}
    </button>
  </div>

  <div style="padding:24px;overflow-y:auto;height:calc(100vh - 130px)">

    <!-- CURRENCIES -->
    <div v-if="activeTab==='currencies'">
      <div class="sce-stat-grid" style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px">
        <div v-for="s in currencySummary" :key="s.label"
          :style="'background:'+s.bg+';border:1px solid '+s.border+';border-radius:12px;padding:16px 20px'">
          <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.6px;color:#666;margin-bottom:6px">{{s.label}}</div>
          <div :style="'font-size:22px;font-weight:800;color:'+s.color">{{s.value}}</div>
          <div style="font-size:11px;color:#999;margin-top:2px">{{s.sub}}</div>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px">
        <div v-for="c in filteredCurrencies" :key="c.code"
          style="background:#fff;border:1px solid #e4e8f0;border-radius:12px;padding:18px;cursor:pointer;transition:box-shadow .15s;position:relative;overflow:hidden">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:12px">
            <div style="display:flex;align-items:center;gap:10px">
              <div :style="'width:42px;height:42px;border-radius:10px;background:'+c.bg+';display:flex;align-items:center;justify-content:center;font-size:20px'">{{c.flag}}</div>
              <div>
                <div style="font-size:14px;font-weight:700;color:#1a1a2e">{{c.code}}</div>
                <div style="font-size:11px;color:#888">{{c.name}}</div>
              </div>
            </div>
            <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px">
              <span :style="'font-size:11px;font-weight:600;padding:2px 8px;border-radius:20px;background:'+(c.change>=0?'#EBFBEE':'#FFF5F5')+';color:'+(c.change>=0?'#2F9E44':'#C92A2A')">
                {{c.change>=0?'+':''}}{{c.change}}%
              </span>
              <span :style="'font-size:10px;padding:1px 6px;border-radius:10px;background:'+(c.active?'#E8EAF6':'#F1F3F5')+';color:'+(c.active?'#1A237E':'#868E96')">
                {{c.active?'Active':'Inactive'}}
              </span>
            </div>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin-bottom:12px">
            <div v-for="r in [{l:'Buy',k:'buy'},{l:'Mid',k:'mid'},{l:'Sell',k:'sell'}]" :key="r.k"
              style="background:#f8f9fa;border-radius:8px;padding:6px 8px;text-align:center">
              <div style="font-size:10px;color:#888;margin-bottom:2px">{{r.l}}</div>
              <div style="font-size:13px;font-weight:700;color:#1a1a2e">{{c[r.k].toFixed(4)}}</div>
            </div>
          </div>
          <div style="height:36px;display:flex;align-items:flex-end;gap:2px">
            <div v-for="(v,i) in c.spark" :key="i"
              :style="'flex:1;border-radius:2px 2px 0 0;background:'+(c.change>=0?'#2F9E44':'#C92A2A')+';opacity:'+(0.4+i*0.07)+';height:'+sparkH(v,c.spark)+'px'">
            </div>
          </div>
          <div style="display:flex;gap:8px;margin-top:12px;padding-top:12px;border-top:1px solid #f0f0f0">
            <button class="nim-btn nim-btn-ghost" style="flex:1;font-size:12px;padding:5px 10px" @click.stop="openEditCurrency(c)">✏️ Edit</button>
            <button class="nim-btn nim-btn-ghost" style="flex:1;font-size:12px;padding:5px 10px" @click.stop="openAddRate(c.code)">📊 Add Rate</button>
          </div>
        </div>

        <div @click="openAddCurrency"
          style="background:#F8F9FA;border:2px dashed #dee2e6;border-radius:12px;padding:18px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;cursor:pointer;min-height:180px;transition:all .15s">
          <div style="font-size:28px">💱</div>
          <div style="font-size:13px;font-weight:600;color:#495057">Add Currency</div>
        </div>
      </div>
    </div>

    <!-- HISTORY -->
    <div v-if="activeTab==='history'">
      <div style="background:#fff;border:1px solid #e4e8f0;border-radius:12px;overflow:hidden">
        <div style="padding:16px 20px;border-bottom:1px solid #e4e8f0;display:flex;align-items:center;gap:12px;flex-wrap:wrap">
          <select v-model="histFilter.currency" style="border:1px solid #dee2e6;border-radius:8px;padding:7px 12px;font-size:13px;background:#fff">
            <option value="">All Currencies</option>
            <option v-for="c in currencies" :key="c.code" :value="c.code">{{c.code}} — {{c.name}}</option>
          </select>
          <input type="date" v-model="histFilter.from" style="border:1px solid #dee2e6;border-radius:8px;padding:7px 12px;font-size:13px">
          <input type="date" v-model="histFilter.to" style="border:1px solid #dee2e6;border-radius:8px;padding:7px 12px;font-size:13px">
          <div style="margin-left:auto;display:flex;gap:8px">
            <button class="nim-btn nim-btn-ghost" style="font-size:12px" @click="exportHistoryCSV">⬇ Export CSV</button>
            <button class="nim-btn nim-btn-primary" :disabled="!$canWrite('admin')" :title="!$canWrite('admin') ? 'Read-only access' : ''" style="font-size:13px" @click="openAddRate('')">+ Add Rate</button>
          </div>
        </div>
        <table style="width:100%;border-collapse:collapse;font-size:13px">
          <thead>
            <tr style="background:#F8F9FA">
              <th v-for="h in ['Date','Currency','Buy Rate','Mid Rate','Sell Rate','Source','Change']" :key="h"
                style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#666;border-bottom:1px solid #e4e8f0">{{h}}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in filteredHistory" :key="r.id" style="border-bottom:1px solid #f5f5f5;transition:background .1s">
              <td style="padding:10px 14px;color:#555">{{r.date}}</td>
              <td style="padding:10px 14px"><span style="font-weight:700;color:#1A237E">{{r.currency}}</span></td>
              <td style="padding:10px 14px;font-weight:600;color:#1a1a2e">{{r.buy.toFixed(4)}}</td>
              <td style="padding:10px 14px;font-weight:600;color:#1a1a2e">{{r.mid.toFixed(4)}}</td>
              <td style="padding:10px 14px;font-weight:600;color:#1a1a2e">{{r.sell.toFixed(4)}}</td>
              <td style="padding:10px 14px;color:#888">{{r.source}}</td>
              <td style="padding:10px 14px">
                <span :style="'font-size:12px;font-weight:600;color:'+(r.chg>=0?'#2F9E44':'#C92A2A')">
                  {{r.chg>=0?'▲':'▼'}} {{Math.abs(r.chg).toFixed(2)}}%
                </span>
              </td>
            </tr>
            <tr v-if="!filteredHistory.length">
              <td colspan="7" style="padding:32px;text-align:center;color:#aaa;font-size:13px">No rate history found</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- CONVERTER -->
    <div v-if="activeTab==='converter'" style="max-width:700px;margin:0 auto">
      <div style="background:#fff;border:1px solid #e4e8f0;border-radius:16px;padding:28px;margin-bottom:20px">
        <div style="font-size:16px;font-weight:700;color:#1a1a2e;margin-bottom:20px">⇋ Currency Converter</div>
        <div style="display:grid;grid-template-columns:1fr auto 1fr;gap:12px;align-items:end;margin-bottom:20px">
          <div>
            <label style="font-size:12px;font-weight:600;color:#666;display:block;margin-bottom:6px">FROM</label>
            <select v-model="conv.from" @change="calcConv" style="width:100%;border:1px solid #dee2e6;border-radius:8px;padding:8px 12px;font-size:14px;font-weight:600;color:#1A237E;background:#E8EAF6;margin-bottom:6px">
              <option v-for="c in allConvCurrencies" :key="c.code" :value="c.code">{{c.code}} — {{c.name}}</option>
            </select>
            <input type="number" v-model.number="conv.amount" @input="calcConv" style="width:100%;border:1px solid #dee2e6;border-radius:8px;padding:10px 14px;font-size:18px;font-weight:700;color:#1a1a2e">
          </div>
          <button @click="swapConv" style="background:#1A237E;color:#fff;border:none;border-radius:50%;width:40px;height:40px;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;margin-bottom:6px">⇋</button>
          <div>
            <label style="font-size:12px;font-weight:600;color:#666;display:block;margin-bottom:6px">TO</label>
            <select v-model="conv.to" @change="calcConv" style="width:100%;border:1px solid #dee2e6;border-radius:8px;padding:8px 12px;font-size:14px;font-weight:600;color:#1a1a2e;margin-bottom:6px">
              <option v-for="c in allConvCurrencies" :key="c.code" :value="c.code">{{c.code}} — {{c.name}}</option>
            </select>
            <div style="border:2px solid #1A237E;border-radius:8px;padding:10px 14px;font-size:18px;font-weight:700;color:#1A237E;background:#F8F9FA;min-height:48px">
              {{conv.result.toFixed(4)}}
            </div>
          </div>
        </div>
        <div style="background:#E8EAF6;border-radius:8px;padding:12px 16px;font-size:13px;color:#3949AB;margin-bottom:18px;text-align:center">
          1 {{conv.from}} = <strong>{{convRate.toFixed(6)}}</strong> {{conv.to}} &nbsp;|&nbsp; 1 {{conv.to}} = <strong>{{(1/convRate).toFixed(6)}}</strong> {{conv.from}}
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button v-for="q in [100,500,1000,5000,10000,50000]" :key="q" @click="conv.amount=q;calcConv()"
            :style="'border:1px solid '+(conv.amount===q?'#1A237E':'#dee2e6')+';background:'+(conv.amount===q?'#E8EAF6':'#fff')+';color:'+(conv.amount===q?'#1A237E':'#555')+';border-radius:20px;padding:5px 14px;font-size:12px;font-weight:600;cursor:pointer'">
            {{q.toLocaleString()}}
          </button>
        </div>
      </div>
      <div style="background:#fff;border:1px solid #e4e8f0;border-radius:12px;padding:20px">
        <div style="font-size:14px;font-weight:700;color:#1a1a2e;margin-bottom:14px">Quick Reference — 1 {{conv.from}}</div>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px">
          <div v-for="c in quickRefCurrencies" :key="c.code"
            style="background:#F8F9FA;border-radius:8px;padding:10px 12px;text-align:center">
            <div style="font-size:11px;color:#888;margin-bottom:4px">{{c.code}}</div>
            <div style="font-size:15px;font-weight:700;color:#1A237E">{{quickRefValue(c).toFixed(4)}}</div>
            <div style="font-size:10px;color:#aaa">{{c.name}}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- P&L -->
    <div v-if="activeTab==='pnl'">
      <div class="sce-stat-grid" style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px">
        <div style="background:#EBFBEE;border:1px solid #b2f2bb;border-radius:12px;padding:18px 20px">
          <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.6px;color:#2F9E44;margin-bottom:6px">Realised Gain</div>
          <div style="font-size:24px;font-weight:800;color:#2F9E44">OMR {{pnlSummary.gain.toLocaleString('en-OM',{minimumFractionDigits:3})}}</div>
        </div>
        <div style="background:#FFF5F5;border:1px solid #ffc9c9;border-radius:12px;padding:18px 20px">
          <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.6px;color:#C92A2A;margin-bottom:6px">Realised Loss</div>
          <div style="font-size:24px;font-weight:800;color:#C92A2A">OMR {{pnlSummary.loss.toLocaleString('en-OM',{minimumFractionDigits:3})}}</div>
        </div>
        <div :style="'background:'+(pnlSummary.net>=0?'#E8EAF6':'#FFF5F5')+';border:1px solid '+(pnlSummary.net>=0?'#c5cae9':'#ffc9c9')+';border-radius:12px;padding:18px 20px'">
          <div :style="'font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.6px;color:'+(pnlSummary.net>=0?'#1A237E':'#C92A2A')+';margin-bottom:6px'">Net P&amp;L</div>
          <div :style="'font-size:24px;font-weight:800;color:'+(pnlSummary.net>=0?'#1A237E':'#C92A2A')">{{pnlSummary.net>=0?'+':''}}OMR {{Math.abs(pnlSummary.net).toLocaleString('en-OM',{minimumFractionDigits:3})}}</div>
        </div>
        <div style="background:#FFF8F0;border:1px solid #ffd8a8;border-radius:12px;padding:18px 20px">
          <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.6px;color:#E67700;margin-bottom:6px">Transactions</div>
          <div style="font-size:24px;font-weight:800;color:#E67700">{{pnlTransactions.length}}</div>
        </div>
      </div>
      <div style="background:#fff;border:1px solid #e4e8f0;border-radius:12px;overflow:hidden">
        <div style="padding:14px 20px;border-bottom:1px solid #e4e8f0;display:flex;align-items:center;gap:12px">
          <span style="font-size:14px;font-weight:700;color:#1a1a2e">Forex Gain / Loss Transactions</span>
          <button class="nim-btn nim-btn-ghost" style="margin-left:auto;font-size:12px" @click="exportPnlCSV">⬇ Export CSV</button>
        </div>
        <table style="width:100%;border-collapse:collapse;font-size:13px">
          <thead>
            <tr style="background:#F8F9FA">
              <th v-for="h in ['Date','Reference','Currency','Booked Rate','Market Rate','Amount (FC)','Gain / Loss']" :key="h"
                style="padding:10px 14px;text-align:left;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#666;border-bottom:1px solid #e4e8f0">{{h}}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in pnlTransactions" :key="r.id" style="border-bottom:1px solid #f5f5f5">
              <td style="padding:10px 14px;color:#555">{{r.date}}</td>
              <td style="padding:10px 14px;color:#1971C2;font-weight:600">{{r.ref}}</td>
              <td style="padding:10px 14px;font-weight:700;color:#1A237E">{{r.currency}}</td>
              <td style="padding:10px 14px">{{r.bookedRate.toFixed(4)}}</td>
              <td style="padding:10px 14px">{{r.marketRate.toFixed(4)}}</td>
              <td style="padding:10px 14px;font-weight:600">{{r.amountFC.toLocaleString()}}</td>
              <td style="padding:10px 14px">
                <span :style="'font-weight:700;color:'+(r.gainLoss>=0?'#2F9E44':'#C92A2A')">
                  {{r.gainLoss>=0?'+':''}}OMR {{Math.abs(r.gainLoss).toLocaleString('en-OM',{minimumFractionDigits:3})}}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

  </div>

  <Teleport to="body">
    <div v-if="showCurrDrawer" class="nim-overlay" @click.self="showCurrDrawer=false">
      <div class="nim-dialog" style="width:520px">
        <div class="nim-header">
          <span>{{drawerMode==='add'?'Add Currency':'Edit Currency'}}</span>
          <button class="nim-btn nim-btn-ghost" style="padding:4px 10px" @click="showCurrDrawer=false">✕</button>
        </div>
        <div class="nim-body" style="display:grid;gap:16px">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
            <div>
              <label class="nim-label">Currency Code *</label>
              <input v-model="currForm.code" class="nim-input" placeholder="e.g. USD" :disabled="drawerMode==='edit'">
            </div>
            <div>
              <label class="nim-label">Symbol *</label>
              <input v-model="currForm.symbol" class="nim-input" placeholder="e.g. $">
            </div>
          </div>
          <div>
            <label class="nim-label">Currency Name *</label>
            <input v-model="currForm.name" class="nim-input" placeholder="e.g. US Dollar">
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px">
            <div>
              <label class="nim-label">Buy Rate</label>
              <input v-model.number="currForm.buy" type="number" step="0.0001" class="nim-input">
            </div>
            <div>
              <label class="nim-label">Mid Rate</label>
              <input v-model.number="currForm.mid" type="number" step="0.0001" class="nim-input">
            </div>
            <div>
              <label class="nim-label">Sell Rate</label>
              <input v-model.number="currForm.sell" type="number" step="0.0001" class="nim-input">
            </div>
          </div>
          <div>
            <label class="nim-label">Flag / Emoji</label>
            <input v-model="currForm.flag" class="nim-input" placeholder="e.g. 🇺🇸">
          </div>
          <div style="display:flex;align-items:center;gap:10px">
            <input type="checkbox" v-model="currForm.active" id="curr-active" style="width:16px;height:16px">
            <label for="curr-active" style="font-size:13px;color:#444;cursor:pointer">Active</label>
          </div>
        </div>
        <div class="nim-footer">
          <button class="nim-btn nim-btn-ghost" @click="showCurrDrawer=false">Cancel</button>
          <button class="nim-btn nim-btn-primary" @click="saveCurrency" :disabled="saving">{{saving?'Saving…':'Save Currency'}}</button>
        </div>
      </div>
    </div>

    <div v-if="showRateDrawer" class="nim-overlay" @click.self="showRateDrawer=false">
      <div class="nim-dialog" style="width:480px">
        <div class="nim-header">
          <span>Add Exchange Rate</span>
          <button class="nim-btn nim-btn-ghost" style="padding:4px 10px" @click="showRateDrawer=false">✕</button>
        </div>
        <div class="nim-body" style="display:grid;gap:16px">
          <div>
            <label class="nim-label">Currency *</label>
            <select v-model="rateForm.currency" class="nim-input">
              <option value="">Select currency</option>
              <option v-for="c in currencies" :key="c.code" :value="c.code">{{c.code}} — {{c.name}}</option>
            </select>
          </div>
          <div>
            <label class="nim-label">Date *</label>
            <input type="date" v-model="rateForm.date" class="nim-input">
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px">
            <div>
              <label class="nim-label">Buy Rate</label>
              <input v-model.number="rateForm.buy" type="number" step="0.0001" class="nim-input">
            </div>
            <div>
              <label class="nim-label">Mid Rate</label>
              <input v-model.number="rateForm.mid" type="number" step="0.0001" class="nim-input">
            </div>
            <div>
              <label class="nim-label">Sell Rate</label>
              <input v-model.number="rateForm.sell" type="number" step="0.0001" class="nim-input">
            </div>
          </div>
          <div>
            <label class="nim-label">Source</label>
            <input v-model="rateForm.source" class="nim-input" placeholder="e.g. RBI, Manual, API">
          </div>
        </div>
        <div class="nim-footer">
          <button class="nim-btn nim-btn-ghost" @click="showRateDrawer=false">Cancel</button>
          <button class="nim-btn nim-btn-primary" @click="saveRate" :disabled="saving">{{saving?'Saving…':'Save Rate'}}</button>
        </div>
      </div>
    </div>
  </Teleport>
</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { apiGET, apiSave } from "../api/client.js";
import { useToast } from "../composables/useToast.js";

const { toast } = useToast();

const activeTab = ref("currencies");
const tabs = [
  { id: "currencies", label: "🌐 Currencies" },
  { id: "history",    label: "📊 Rate History" },
  { id: "converter",  label: "⇋ Converter" },
  { id: "pnl",        label: "💵 Forex P&L" },
];

const refreshing      = ref(false);
const saving          = ref(false);
const showCurrDrawer  = ref(false);
const showRateDrawer  = ref(false);
const drawerMode      = ref("add");

const currForm   = reactive({ code: "", symbol: "", name: "", buy: 1, mid: 1, sell: 1, flag: "🏳️", active: true });
const rateForm   = reactive({ currency: "", date: "", buy: 1, mid: 1, sell: 1, source: "Manual" });
const histFilter = reactive({ currency: "", from: "", to: "" });

const currencies = ref([
  { code: "USD", name: "US Dollar",       symbol: "$",   flag: "🇺🇸", buy: 83.12, mid: 83.25, sell: 83.38, change: 0.18,  active: true,  bg: "#E8EAF6", spark: [82.1,82.4,82.8,83.0,83.1,82.9,83.0,83.2,83.3,83.25,83.1,83.25] },
  { code: "EUR", name: "Euro",            symbol: "€",   flag: "🇪🇺", buy: 89.45, mid: 89.62, sell: 89.79, change: -0.32, active: true,  bg: "#E8F5E9", spark: [90.1,89.9,90.0,89.7,89.5,89.6,89.4,89.5,89.7,89.62,89.5,89.62] },
  { code: "GBP", name: "British Pound",   symbol: "£",   flag: "🇬🇧", buy: 104.2, mid: 104.5, sell: 104.8, change: 0.55,  active: true,  bg: "#FFF3E0", spark: [103.2,103.5,103.8,104.0,104.1,104.3,104.2,104.4,104.6,104.5,104.3,104.5] },
  { code: "AED", name: "UAE Dirham",      symbol: "د.إ", flag: "🇦🇪", buy: 22.63, mid: 22.70, sell: 22.77, change: 0.09,  active: true,  bg: "#E8EAF6", spark: [22.5,22.55,22.6,22.65,22.7,22.68,22.7,22.72,22.71,22.70,22.69,22.70] },
  { code: "SGD", name: "Singapore Dollar",symbol: "S$",  flag: "🇸🇬", buy: 61.35, mid: 61.52, sell: 61.69, change: -0.14, active: true,  bg: "#F3E5F5", spark: [61.8,61.7,61.6,61.5,61.4,61.5,61.6,61.55,61.5,61.52,61.45,61.52] },
  { code: "JPY", name: "Japanese Yen",    symbol: "¥",   flag: "🇯🇵", buy: 0.548, mid: 0.552, sell: 0.556, change: 0.73,  active: true,  bg: "#FCE4EC", spark: [0.540,0.542,0.545,0.547,0.549,0.551,0.550,0.552,0.553,0.552,0.551,0.552] },
  { code: "CNY", name: "Chinese Yuan",    symbol: "¥",   flag: "🇨🇳", buy: 11.45, mid: 11.51, sell: 11.57, change: -0.21, active: false, bg: "#FFF8E1", spark: [11.6,11.58,11.55,11.52,11.5,11.51,11.53,11.52,11.51,11.51,11.50,11.51] },
]);

const rateHistory = ref([
  { id: 1, date: "2024-04-25", currency: "USD", buy: 83.12, mid: 83.25, sell: 83.38, source: "RBI",    chg: 0.18 },
  { id: 2, date: "2024-04-25", currency: "EUR", buy: 89.45, mid: 89.62, sell: 89.79, source: "RBI",    chg: -0.32 },
  { id: 3, date: "2024-04-25", currency: "GBP", buy: 104.2, mid: 104.5, sell: 104.8, source: "Manual", chg: 0.55 },
  { id: 4, date: "2024-04-24", currency: "USD", buy: 82.97, mid: 83.10, sell: 83.23, source: "RBI",    chg: -0.18 },
  { id: 5, date: "2024-04-24", currency: "EUR", buy: 89.73, mid: 89.91, sell: 90.09, source: "RBI",    chg: 0.22 },
  { id: 6, date: "2024-04-23", currency: "USD", buy: 83.12, mid: 83.28, sell: 83.44, source: "API",    chg: 0.05 },
  { id: 7, date: "2024-04-23", currency: "AED", buy: 22.60, mid: 22.67, sell: 22.74, source: "Manual", chg: 0.09 },
  { id: 8, date: "2024-04-22", currency: "SGD", buy: 61.48, mid: 61.65, sell: 61.82, source: "RBI",    chg: -0.14 },
  { id: 9, date: "2024-04-22", currency: "GBP", buy: 103.8, mid: 104.1, sell: 104.4, source: "API",    chg: -0.38 },
  { id: 10,date: "2024-04-21", currency: "JPY", buy: 0.543, mid: 0.547, sell: 0.551, source: "RBI",    chg: 0.73 },
]);

const pnlTransactions = ref([
  { id: 1, date: "2024-04-22", ref: "INV-0042", currency: "USD", bookedRate: 82.50, marketRate: 83.25, amountFC: 5000,  gainLoss: 3750.00 },
  { id: 2, date: "2024-04-20", ref: "INV-0039", currency: "EUR", bookedRate: 90.10, marketRate: 89.62, amountFC: 2000,  gainLoss: -960.00 },
  { id: 3, date: "2024-04-18", ref: "PAY-0017", currency: "GBP", bookedRate: 103.8, marketRate: 104.5, amountFC: 1500,  gainLoss: 1050.00 },
  { id: 4, date: "2024-04-15", ref: "INV-0035", currency: "AED", bookedRate: 22.55, marketRate: 22.70, amountFC: 10000, gainLoss: 1500.00 },
  { id: 5, date: "2024-04-12", ref: "PAY-0015", currency: "USD", bookedRate: 83.50, marketRate: 83.25, amountFC: 3000,  gainLoss: -750.00 },
  { id: 6, date: "2024-04-10", ref: "INV-0031", currency: "SGD", bookedRate: 61.80, marketRate: 61.52, amountFC: 800,   gainLoss: -224.00 },
]);

const filteredCurrencies = computed(() => currencies.value);

const currencySummary = computed(() => {
  const active = currencies.value.filter((c) => c.active).length;
  const avgChg = currencies.value.reduce((s, c) => s + c.change, 0) / (currencies.value.length || 1);
  return [
    { label: "Total Currencies", value: currencies.value.length, sub: "configured", color: "#1A237E", bg: "#E8EAF6", border: "#c5cae9" },
    { label: "Active",            value: active,                  sub: "in use",      color: "#2F9E44", bg: "#EBFBEE", border: "#b2f2bb" },
    { label: "Avg. Daily Change", value: (avgChg >= 0 ? "+" : "") + avgChg.toFixed(2) + "%", sub: "vs yesterday", color: avgChg >= 0 ? "#2F9E44" : "#C92A2A", bg: avgChg >= 0 ? "#EBFBEE" : "#FFF5F5", border: avgChg >= 0 ? "#b2f2bb" : "#ffc9c9" },
    { label: "Base Currency",     value: "INR",                   sub: "Indian Rupee",color: "#E67700", bg: "#FFF8F0", border: "#ffd8a8" },
  ];
});

const filteredHistory = computed(() =>
  rateHistory.value.filter((r) => {
    if (histFilter.currency && r.currency !== histFilter.currency) return false;
    if (histFilter.from && r.date < histFilter.from) return false;
    if (histFilter.to && r.date > histFilter.to) return false;
    return true;
  })
);

const conv = reactive({ from: "USD", to: "INR", amount: 1, result: 83.25 });

const convRate = computed(() => {
  if (conv.from === "INR") {
    const tgt = currencies.value.find((c) => c.code === conv.to);
    return tgt ? 1 / tgt.mid : 1;
  }
  if (conv.to === "INR") {
    const src = currencies.value.find((c) => c.code === conv.from);
    return src ? src.mid : 1;
  }
  const src = currencies.value.find((c) => c.code === conv.from);
  const tgt = currencies.value.find((c) => c.code === conv.to);
  const srcMid = src ? src.mid : 1;
  const tgtMid = tgt ? tgt.mid : 1;
  return srcMid / tgtMid;
});

const allConvCurrencies = computed(() => [
  { code: "INR", name: "Indian Rupee" },
  ...currencies.value.map((c) => ({ code: c.code, name: c.name })),
]);

const quickRefCurrencies = computed(() =>
  currencies.value.filter((c) => c.code !== conv.from).slice(0, 8)
);

function quickRefValue(c) {
  if (conv.from === "INR") return c.mid ? 1 / c.mid : 0;
  if (c.code === "INR") {
    const src = currencies.value.find((x) => x.code === conv.from);
    return src ? src.mid : 1;
  }
  const src = currencies.value.find((x) => x.code === conv.from);
  return src && c.mid ? src.mid / c.mid : 1;
}

function calcConv() { conv.result = conv.amount * convRate.value; }

function swapConv() {
  const tmp = conv.from; conv.from = conv.to; conv.to = tmp;
  calcConv();
}

const pnlSummary = computed(() => {
  let gain = 0, loss = 0;
  pnlTransactions.value.forEach((r) => {
    if (r.gainLoss > 0) gain += r.gainLoss;
    else loss += Math.abs(r.gainLoss);
  });
  return { gain, loss, net: gain - loss };
});

function sparkH(v, arr) {
  const mn = Math.min(...arr), mx = Math.max(...arr);
  if (mx === mn) return 20;
  return Math.max(4, Math.round(((v - mn) / (mx - mn)) * 32));
}

function openAddCurrency() {
  drawerMode.value = "add";
  Object.assign(currForm, { code: "", symbol: "", name: "", buy: 1, mid: 1, sell: 1, flag: "🏳️", active: true });
  showCurrDrawer.value = true;
}

function openEditCurrency(c) {
  drawerMode.value = "edit";
  Object.assign(currForm, { code: c.code, symbol: c.symbol, name: c.name, buy: c.buy, mid: c.mid, sell: c.sell, flag: c.flag, active: c.active });
  showCurrDrawer.value = true;
}

function openAddRate(code) {
  Object.assign(rateForm, { currency: code || "", date: "", buy: 1, mid: 1, sell: 1, source: "Manual" });
  showRateDrawer.value = true;
  activeTab.value = "history";
}

async function saveCurrency() {
  if (!currForm.code || !currForm.name) { toast("Currency code and name are required", "error"); return; }
  saving.value = true;
  try {
    if (drawerMode.value === "add") {
      currencies.value.push({
        code: currForm.code.toUpperCase(), name: currForm.name, symbol: currForm.symbol,
        flag: currForm.flag, buy: currForm.buy, mid: currForm.mid, sell: currForm.sell,
        change: 0, active: currForm.active, bg: "#E8EAF6", spark: [currForm.mid],
      });
    } else {
      const c = currencies.value.find((x) => x.code === currForm.code);
      if (c) Object.assign(c, { name: currForm.name, symbol: currForm.symbol, flag: currForm.flag, buy: currForm.buy, mid: currForm.mid, sell: currForm.sell, active: currForm.active });
    }
    try {
      await apiSave({ doctype: "Currency Exchange", from_currency: currForm.code, to_currency: "INR", exchange_rate: currForm.mid });
    } catch {}
    toast("Currency saved", "success");
    showCurrDrawer.value = false;
  } finally { saving.value = false; }
}

async function saveRate() {
  if (!rateForm.currency || !rateForm.date) { toast("Currency and date are required", "error"); return; }
  saving.value = true;
  try {
    const prevEntry = rateHistory.value.find((r) => r.currency === rateForm.currency);
    const prevMid = prevEntry ? prevEntry.mid : rateForm.mid;
    const chg = prevMid ? ((rateForm.mid - prevMid) / prevMid) * 100 : 0;
    rateHistory.value.unshift({
      id: Date.now(), date: rateForm.date, currency: rateForm.currency,
      buy: rateForm.buy, mid: rateForm.mid, sell: rateForm.sell,
      source: rateForm.source, chg: parseFloat(chg.toFixed(2)),
    });
    const c = currencies.value.find((x) => x.code === rateForm.currency);
    if (c) { c.buy = rateForm.buy; c.mid = rateForm.mid; c.sell = rateForm.sell; c.change = parseFloat(chg.toFixed(2)); }
    try {
      await apiSave({ doctype: "Currency Exchange", from_currency: rateForm.currency, to_currency: "INR", exchange_rate: rateForm.mid, date: rateForm.date });
    } catch {}
    toast("Rate added", "success");
    showRateDrawer.value = false;
  } finally { saving.value = false; }
}

async function refreshRates() {
  refreshing.value = true;
  try {
    const res = await apiGET("zoho_books_clone.api.books_data.refresh_all_exchange_rates", {});
    if (res && typeof res === "object") {
      Object.entries(res).forEach(([code, r]) => {
        const c = currencies.value.find((x) => x.code === code);
        if (c && r?.rate) { c.mid = r.rate; c.buy = r.rate; c.sell = r.rate; }
      });
      // refresh rate history too
      const { apiList } = await import("../api/client.js");
      const rows = await apiList("Currency Exchange", { fields: ["from_currency","exchange_rate","date"], limit: 200, order: "date desc" });
      rateHistory.value = rows.slice(0, 50).map((r, i) => ({ id: i+1, date: r.date, currency: r.from_currency, buy: r.exchange_rate, mid: r.exchange_rate, sell: r.exchange_rate, source: "Live", chg: 0 }));
    }
    toast("Rates refreshed from live feed", "success");
  } catch { toast("Could not fetch live rates — showing cached data", "warning"); }
  finally { refreshing.value = false; }
}

function exportHistoryCSV() {
  const headers = ["Date", "Currency", "Buy", "Mid", "Sell", "Source", "Change%"];
  const rows = filteredHistory.value.map((r) => [r.date, r.currency, r.buy, r.mid, r.sell, r.source, r.chg]);
  const csv = [headers, ...rows].map((r) => r.join(",")).join("\n");
  const a = document.createElement("a");
  a.href = "data:text/csv," + encodeURIComponent(csv);
  a.download = "rate_history.csv";
  a.click();
}

function exportPnlCSV() {
  const headers = ["Date", "Reference", "Currency", "BookedRate", "MarketRate", "AmountFC", "GainLoss"];
  const rows = pnlTransactions.value.map((r) => [r.date, r.ref, r.currency, r.bookedRate, r.marketRate, r.amountFC, r.gainLoss]);
  const csv = [headers, ...rows].map((r) => r.join(",")).join("\n");
  const a = document.createElement("a");
  a.href = "data:text/csv," + encodeURIComponent(csv);
  a.download = "forex_pnl.csv";
  a.click();
}

onMounted(async () => {
  calcConv();
  // Load real rates from Frappe silently; merge into the default currency list
  try {
    const { apiList } = await import("../api/client.js");
    const rows = await apiList("Currency Exchange", { fields: ["from_currency","exchange_rate","date"], limit: 200, order: "date desc" });
    const seen = {};
    rows.forEach(r => { if (!seen[r.from_currency]) seen[r.from_currency] = r; });
    currencies.value.forEach(c => {
      const r = seen[c.code];
      if (r) c.mid = r.exchange_rate;
    });
    // populate rate history from real records
    rateHistory.value = rows.slice(0, 50).map((r, i) => ({ id: i+1, date: r.date, currency: r.from_currency, buy: r.exchange_rate, mid: r.exchange_rate, sell: r.exchange_rate, source: "Frappe", chg: 0 }));
  } catch {}
});
</script>

<style>
@media (max-width: 768px) {
  .sce-stat-grid { grid-template-columns: repeat(2, 1fr) !important; }
}
@media (max-width: 480px) {
  .sce-stat-grid { grid-template-columns: 1fr 1fr !important; }
  .cust-page { padding: 12px !important; }
}
</style>
