<template>
<div class="b-page">
  <div style="background:#EEF2FF;border:1px solid rgba(59,91,219,.15);border-radius:8px;padding:12px 16px;font-size:13px;color:#2f4ec4;line-height:1.6">
    <strong>What is this?</strong> Enter account balances from your previous accounting system as of the date you start using Books. This is done <strong>once</strong>. After submission, balances are locked and posted as an Opening Journal Entry.
  </div>

  <!-- ── Desktop stepper (hidden on 375–425px) ── -->
  <div class="b-card ob-desktop-stepper" style="padding:14px 18px;display:flex;align-items:center">
    <template v-for="(s,i) in ['Set go-live date','Enter balances','Verify equation','Submit']" :key="i">
      <div style="display:flex;align-items:center">
        <div class="ob-step-dot" :class="i<curStep||submitted?'ob-dot-done':i===curStep&&!submitted?'ob-dot-active':'ob-dot-pending'">
          <span v-if="i<curStep||submitted" v-html="icon('check',12)"></span>
          <span v-else>{{i+1}}</span>
        </div>
        <span class="ob-step-lbl" :class="i<curStep||submitted?'ob-lbl-done':i===curStep&&!submitted?'ob-lbl-active':'ob-lbl-muted'">{{s}}</span>
      </div>
      <div v-if="i<3" class="ob-step-line" :class="i<curStep||submitted?'ob-line-done':''"></div>
    </template>
  </div>

  <!-- ── Mobile stepper: dots on top row, labels below (shown only at 375–425px) ── -->
  <div class="ob-mobile-stepper">
    <!-- Dots + connecting lines -->
    <div class="ob-ms-dots">
      <template v-for="(s,i) in ['Set go-live date','Enter balances','Verify equation','Submit']" :key="'d'+i">
        <div class="ob-ms-dot-wrap">
          <div class="ob-step-dot ob-ms-dot"
            :class="i<curStep||submitted?'ob-dot-done':i===curStep&&!submitted?'ob-dot-active':'ob-dot-pending'">
            <span v-if="i<curStep||submitted" v-html="icon('check',11)"></span>
            <span v-else>{{i+1}}</span>
          </div>
        </div>
        <div v-if="i<3" class="ob-ms-line"
          :class="i<curStep||submitted?'ob-line-done':''">
        </div>
      </template>
    </div>
    <!-- Labels below each dot -->
    <div class="ob-ms-labels">
      <span v-for="(s,i) in ['Set go-live date','Enter balances','Verify equation','Submit']" :key="'l'+i"
        class="ob-ms-lbl"
        :class="i<curStep||submitted?'ob-lbl-done':i===curStep&&!submitted?'ob-lbl-active':'ob-lbl-muted'">
        {{s}}
      </span>
    </div>
  </div>

  <div class="ob-go-live-bar" style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap">
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
      <label style="font-size:13px;font-weight:600;color:#868E96;white-space:nowrap">Go-live Date</label>
      <input type="date" v-model="goLiveDate" @change="saveDraft" :disabled="submitted || !$canCreate('accounts')" class="b-input"/>
      <span style="font-size:12px;color:#868E96">Balances as at the closing of this date from your previous system.</span>
    </div>
    <div style="display:flex;gap:8px;align-items:center">
      <span v-if="submitted" style="display:inline-flex;align-items:center;gap:6px;background:#EBFBEE;color:#2F9E44;border:1px solid rgba(47,158,68,.2);border-radius:8px;padding:6px 14px;font-size:13px;font-weight:600"><span v-html="icon('check',13)"></span>Submitted</span>
      <button v-if="hasBalances||submitted" class="b-btn b-btn-ghost" :disabled="!$canCreate('accounts')" :title="!$canCreate('accounts') ? 'Read-only access' : ''" @click="showResetModal=true">Reset</button>
      <button v-if="!submitted" class="b-btn" :class="Math.abs(eq.diff)<0.01&&hasBalances?'b-btn-primary':'b-btn-ghost'" :disabled="!hasBalances || !$canCreate('accounts')" :title="!$canCreate('accounts') ? 'Read-only access' : ''" @click="Math.abs(eq.diff)<0.01&&hasBalances?showSubmitModal=true:null">
        <span v-html="icon('check',13)"></span>
        {{Math.abs(eq.diff)<0.01&&hasBalances?'Submit Opening Balances':'Needs Balancing'}}
      </button>
    </div>
  </div>

  <div v-if="loading" class="b-card" style="padding:40px;text-align:center;color:#868E96">
    <div class="b-shimmer" style="max-width:300px;margin:0 auto;height:14px"></div>
  </div>

  <div v-else class="b-card ob-eq-card" style="padding:16px 20px">
    <div class="ob-eq-title" style="font-size:11px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;color:#868E96;margin-bottom:12px">Accounting Equation Check — Assets = Liabilities + Equity</div>
    <div class="ob-eq-strip" style="display:flex;align-items:center;flex-wrap:wrap;gap:0">
      <div class="ob-eq-cell" style="flex:1;padding:12px 16px;border-radius:8px;text-align:center;background:#E0F7FA">
        <div class="ob-eq-lbl" style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.4px;color:#0C8599;margin-bottom:4px">Assets</div>
        <div class="ob-eq-val" style="font-size:18px;font-weight:700;color:#0C8599">{{fmtINR(eq.assets)}}</div>
      </div>
      <div class="ob-eq-op" style="font-size:20px;font-weight:700;color:#868E96;padding:0 12px;align-self:center">=</div>
      <div class="ob-eq-cell" style="flex:1;padding:12px 16px;border-radius:8px;text-align:center;background:#FFE3E3">
        <div class="ob-eq-lbl" style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.4px;color:#C92A2A;margin-bottom:4px">Liabilities</div>
        <div class="ob-eq-val" style="font-size:18px;font-weight:700;color:#C92A2A">{{fmtINR(eq.liabilities)}}</div>
      </div>
      <div class="ob-eq-op" style="font-size:20px;font-weight:700;color:#868E96;padding:0 12px;align-self:center">+</div>
      <div class="ob-eq-cell" style="flex:1;padding:12px 16px;border-radius:8px;text-align:center;background:#F3F0FF">
        <div class="ob-eq-lbl" style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.4px;color:#2563eb;margin-bottom:4px">Equity</div>
        <div class="ob-eq-val" style="font-size:18px;font-weight:700;color:#2563eb">{{fmtINR(eq.equity)}}</div>
      </div>
    </div>
    <div class="ob-eq-diff" :class="!eq.assets&&!eq.liabilities&&!eq.equity?'ob-eq-zero':Math.abs(eq.diff)<0.01?'ob-eq-ok':'ob-eq-err'">
      <span v-if="!eq.assets&&!eq.liabilities&&!eq.equity">Enter balances to check the equation</span>
      <span v-else-if="Math.abs(eq.diff)<0.01">✓ Balanced — Assets = Liabilities + Equity = {{fmtINR(eq.assets)}}</span>
      <span v-else>✗ Out of balance by {{fmtINR(Math.abs(eq.diff))}} — {{eq.diff>0?"Assets exceed Liabilities+Equity":"Liabilities+Equity exceed Assets"}}</span>
    </div>
  </div>

  <template v-if="!loading">
    <template v-for="type in OB_TYPES" :key="type">
      <div v-if="secAccts(type).length" class="b-card" style="padding:0;overflow:hidden">
        <div class="ob-sec-header" style="display:flex;align-items:center;justify-content:space-between;padding:12px 16px;cursor:pointer;user-select:none" @click="toggleSec(type)">
          <div style="display:flex;align-items:center;gap:10px">
            <span style="font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px" :style="{background:OB_TYPE_META[type].bg,color:OB_TYPE_META[type].color}">{{OB_TYPE_META[type].label}}</span>
            <span style="font-size:13px;color:#868E96">{{secAccts(type).length}} accounts &nbsp;·&nbsp; {{secAccts(type).filter(a=>balances[a.name]>0).length}} filled</span>
          </div>
          <div style="display:flex;align-items:center;gap:12px">
            <span style="font-size:14px;font-weight:700" :style="{color:OB_TYPE_META[type].color}">{{fmtINR(secTotal(type))}}</span>
            <span style="font-size:11px;color:#868E96;transition:transform .2s;display:inline-block" :style="{transform:isSec(type)?'rotate(90deg)':'rotate(0deg)'}">&#9654;</span>
          </div>
        </div>
        <template v-if="isSec(type)">
          <div class="ob-col-header" style="display:grid;grid-template-columns:1fr 130px 130px;align-items:center;gap:10px;padding:8px 16px;background:#F8F9FC;border-top:1px solid #F1F3F5">
            <div style="font-size:10.5px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;color:#868E96">Account</div>
            <div style="font-size:10.5px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;color:#868E96;text-align:right">Balance (₹)</div>
            <div style="font-size:10.5px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;color:#868E96">Dr / Cr</div>
          </div>
          <div v-for="a in secAccts(type)" :key="a.name" class="ob-acct-row">
            <div>
              <div style="font-size:13px;color:#1A1D23">{{a.account_name}}</div>
              <div v-if="a.account_type" style="font-size:11px;color:#868E96">{{a.account_type}}</div>
            </div>
            <input type="number" min="0" step="0.01" class="ob-bal-input" :class="balances[a.name]>0?'ob-has-val':''"
              :value="balances[a.name]||''" placeholder="0.00" :disabled="submitted || !$canCreate('accounts')"
              @input="setB(a.name,$event.target.value)" @focus="$event.target.select()"/>
            <select class="ob-dr-cr-sel" :class="(drCrMap[a.name]||'Debit')==='Debit'?'ob-dr':'ob-cr'"
              :disabled="submitted || !$canCreate('accounts')" @change="setDC(a.name,$event.target.value)">
              <option value="Debit" :selected="(drCrMap[a.name]||'Debit')==='Debit'">Dr (Debit)</option>
              <option value="Credit" :selected="(drCrMap[a.name]||'Debit')==='Credit'">Cr (Credit)</option>
            </select>
          </div>
          <div class="ob-sec-footer" style="display:grid;grid-template-columns:1fr 130px 130px;gap:10px;padding:10px 16px;background:#F8F9FC;border-top:1px solid #E2E8F0">
            <div style="font-size:12px;font-weight:600;color:#868E96">Total {{OB_TYPE_META[type].label}}</div>
            <div style="font-size:13px;font-weight:700;text-align:right" :style="{color:OB_TYPE_META[type].color}">{{fmtINR(secTotal(type))}}</div>
            <div></div>
          </div>
        </template>
      </div>
    </template>
    <div v-if="!accounts.length" class="b-card" style="padding:40px;text-align:center;color:#868E96">
      <div style="font-size:36px;margin-bottom:12px">📄</div>
      <div style="font-weight:600;margin-bottom:8px;color:#1A1D23">No accounts found</div>
      <div style="font-size:13px;margin-bottom:16px">Set up your Chart of Accounts first, then come back to enter opening balances.</div>
      <router-link to="/accounting/chart-of-accounts" class="b-btn b-btn-primary">Go to Chart of Accounts</router-link>
    </div>
  </template>

  <Teleport to="body">
    <div v-if="showSubmitModal" style="position:fixed;inset:0;z-index:1000;background:rgba(0,0,0,.5);display:flex;align-items:center;justify-content:center;padding:20px" @click.self="showSubmitModal=false">
      <div style="background:#fff;border-radius:12px;padding:28px 32px;max-width:500px;width:100%">
        <div style="font-size:18px;font-weight:700;margin-bottom:8px">Submit Opening Balances?</div>
        <div style="font-size:13px;color:#868E96;margin-bottom:14px;line-height:1.6">This will create an <strong>Opening Entry</strong> journal in Frappe and lock all balances. You <strong>cannot edit</strong> opening balances after submission without cancelling the journal entry.</div>
        <div class="ob-eq-diff" :class="Math.abs(eq.diff)<0.01?'ob-eq-ok':'ob-eq-err'" style="margin-bottom:20px">
          <span v-if="Math.abs(eq.diff)<0.01">✓ Assets ({{fmtINR(eq.assets)}}) = Liabilities ({{fmtINR(eq.liabilities)}}) + Equity ({{fmtINR(eq.equity)}})</span>
          <span v-else>✗ Out of balance by {{fmtINR(Math.abs(eq.diff))}}. Please fix before submitting.</span>
        </div>
        <div style="display:flex;gap:10px;justify-content:flex-end">
          <button class="b-btn b-btn-ghost" @click="showSubmitModal=false">Go Back</button>
          <button class="b-btn" style="background:#2F9E44;color:#fff;border-color:#2F9E44" :disabled="Math.abs(eq.diff)>=0.01" @click="doSubmit">Yes, Submit</button>
        </div>
      </div>
    </div>

    <div v-if="showResetModal" style="position:fixed;inset:0;z-index:1000;background:rgba(0,0,0,.5);display:flex;align-items:center;justify-content:center;padding:20px" @click.self="showResetModal=false">
      <div style="background:#fff;border-radius:12px;padding:28px 32px;max-width:420px;width:100%">
        <div style="font-size:18px;font-weight:700;margin-bottom:8px">Reset All Balances?</div>
        <div style="font-size:13px;color:#868E96;margin-bottom:24px;line-height:1.6">This will clear all entered balances. You will need to re-enter them.</div>
        <div style="display:flex;gap:10px;justify-content:flex-end">
          <button class="b-btn b-btn-ghost" @click="showResetModal=false">Cancel</button>
          <button class="b-btn" style="background:#C92A2A;color:#fff;border-color:#C92A2A" @click="doReset">Yes, Reset</button>
        </div>
      </div>
    </div>
  </Teleport>
</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { apiGET, apiPOST, apiSave, apiSubmit, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";
import { usePermissions } from "../composables/usePermissions.js";

const { toast } = useToast();
const { canCreate } = usePermissions();

const OB_TYPE_META = {
  Asset:     { color: "#0C8599", bg: "#E0F7FA", label: "Assets",      balType: "Debit"  },
  Liability: { color: "#C92A2A", bg: "#FFE3E3", label: "Liabilities", balType: "Credit" },
  Equity:    { color: "#2563eb", bg: "#F3F0FF", label: "Equity",      balType: "Credit" },
  Income:    { color: "#2F9E44", bg: "#EBFBEE", label: "Income",      balType: "Credit" },
  Expense:   { color: "#E67700", bg: "#FFF3BF", label: "Expenses",    balType: "Debit"  },
};
const OB_TYPES = ["Asset", "Liability", "Equity", "Income", "Expense"];

const loading    = ref(true);
const accounts   = ref([]);
const balances   = reactive({});
const drCrMap    = reactive({});
const goLiveDate = ref(new Date().toISOString().slice(0, 10));
const submitted  = ref(false);
const openSecs   = ref(["Asset", "Liability", "Equity", "Income", "Expense"]);
const showSubmitModal = ref(false);
const showResetModal  = ref(false);

function r2(v) { return Math.round(Number(v || 0) * 100) / 100; }
function fmtINR(v) {
  const n = Number(v || 0);
  if (n === 0) return "₹0";
  return "₹" + Math.abs(n).toLocaleString("en-IN", { minimumFractionDigits: 2 });
}
function guessRT(t, name) {
  t = (t || "").toLowerCase();
  name = (name || "").toLowerCase();
  if (t === "income" || t.includes("income")) return "Income";
  if (t === "expense" || t.includes("expense") || t === "cost of goods sold" || t === "depreciation") return "Expense";
  if (t === "payable" || t === "liability" || t === "credit card") return "Liability";
  if (t === "equity" || t.includes("retained")) return "Equity";
  // Tax accounts: "Input" / "ITC" / "Credit" → Asset (receivable); "Payable" / "Output" → Liability
  if (t === "tax") {
    if (name.includes("payable") || name.includes("output")) return "Liability";
    return "Asset";
  }
  // Receivable, Cash, Bank, Stock, Stock Adjustment → Asset
  if (t === "receivable" || t === "cash" || t === "bank" || t === "stock" || t === "stock adjustment") return "Asset";
  return "Asset";
}

async function load() {
  loading.value = true;
  try {
    const company = await resolveCompany();
    const res = await apiGET("zoho_books_clone.api.books_data.get_chart_of_accounts", { company });
    let raw = Array.isArray(res) ? res : [];
    if (company) {
      const nameSet = new Set(raw.map((a) => a.account_name || a.name));
      raw = raw.filter((a) => {
        const nm = a.account_name || a.name;
        return nm.endsWith(" - " + company) || !nameSet.has(nm + " - " + company);
      });
    }
    accounts.value = raw.filter((a) => !a.is_group).map((a) => ({
      name: a.name, account_name: a.account_name || a.name,
      root_type: a.root_type || guessRT(a.account_type, a.account_name || a.name),
      account_type: a.account_type || "",
    }));
    // Always recompute drCrMap from root_type — don't let stale localStorage values
    // override the correct Debit/Credit assignment (e.g. Tax Payable accounts).
    accounts.value.forEach((a) => {
      drCrMap[a.name] = OB_TYPE_META[a.root_type]?.balType || "Debit";
    });
    // Now restore any user overrides from localStorage (after the correct defaults are set)
    try {
      const s = JSON.parse(localStorage.getItem("books_ob") || "{}");
      if (s.b) Object.assign(balances, s.b);
      if (s.date) goLiveDate.value = s.date;
      submitted.value = localStorage.getItem("books_ob_status") === "submitted";
      // Only restore drCrMap overrides for accounts that exist
      if (s.d) {
        accounts.value.forEach((a) => {
          if (s.d[a.name] !== undefined) drCrMap[a.name] = s.d[a.name];
        });
      }
    } catch {}
    if (accounts.value.length) toast("Loaded " + accounts.value.length + " accounts", "info");
    else toast("No accounts found — set up Chart of Accounts first", "info");
  } catch (e) { toast("Could not load accounts: " + e.message, "error"); }
  finally { loading.value = false; }
}

function saveDraft() {
  try { localStorage.setItem("books_ob", JSON.stringify({ b: { ...balances }, d: { ...drCrMap }, date: goLiveDate.value })); } catch {}
}

const eq = computed(() => {
  let a = 0, l = 0, e = 0;
  accounts.value.forEach((ac) => {
    const v = r2(Number(balances[ac.name] || 0));
    if (!v) return;
    const dc = drCrMap[ac.name] || OB_TYPE_META[ac.root_type]?.balType || "Debit";
    const s = (dc === "Debit" ? 1 : -1) * v;
    if (ac.root_type === "Asset") a += s;
    else if (ac.root_type === "Liability") l -= s;
    else if (ac.root_type === "Equity") e -= s;
  });
  return { assets: r2(a), liabilities: r2(l), equity: r2(e), diff: r2(a - (l + e)) };
});

const curStep = computed(() => {
  if (submitted.value) return 4;
  const { diff } = eq.value;
  const hasB = Object.keys(balances).some((k) => Number(balances[k]) > 0);
  const bal = hasB && Math.abs(diff) < 0.01;
  return bal ? 3 : hasB ? 2 : goLiveDate.value ? 1 : 0;
});

const hasBalances = computed(() => Object.keys(balances).some((k) => Number(balances[k]) > 0));

function setB(name, val) {
  const n = parseFloat(val) || 0;
  if (n > 0) balances[name] = n; else delete balances[name];
  saveDraft();
}
function setDC(name, val) { drCrMap[name] = val; saveDraft(); }
function toggleSec(t) { const i = openSecs.value.indexOf(t); if (i >= 0) openSecs.value.splice(i, 1); else openSecs.value.push(t); }
function isSec(t) { return openSecs.value.includes(t); }
function secAccts(t) { return accounts.value.filter((a) => a.root_type === t); }
function secTotal(t) { return r2(secAccts(t).reduce((s, a) => s + r2(Number(balances[a.name] || 0)), 0)); }

async function doSubmit() {
  if (!canCreate("accounts")) { toast("Read-only access", "error"); showSubmitModal.value = false; return; }
  showSubmitModal.value = false;
  const date = goLiveDate.value || new Date().toISOString().slice(0, 10);
  const lines = [];
  accounts.value.forEach((a) => {
    const v = r2(Number(balances[a.name] || 0));
    if (!v) return;
    const dc = drCrMap[a.name] || "Debit";
    lines.push({
      doctype: "Journal Entry Account",
      account: a.name,
      debit:  dc === "Debit"  ? v : 0,
      credit: dc === "Credit" ? v : 0,
    });
  });
  try {
    const company = await resolveCompany();
    const doc = {
      doctype: "Journal Entry",
      naming_series: "JV-.YYYY.-",
      company,
      voucher_type: "Opening Entry",
      posting_date: date,
      remark: "Opening Balances as at " + date,
      accounts: lines,
    };
    const saved = await apiSave(doc);
    await apiSubmit("Journal Entry", saved.name);
    toast("Opening entry posted: " + saved.name, "success");
    // Only mark as submitted once the opening Journal Entry actually posted.
    submitted.value = true;
    localStorage.setItem("books_ob_status", "submitted");
    saveDraft();
  } catch (e) {
    toast("Failed to post opening entry — " + (e.message || "please try again"), "error");
  }
}

function doReset() {
  if (!canCreate("accounts")) { toast("Read-only access", "error"); showResetModal.value = false; return; }
  Object.keys(balances).forEach((k) => delete balances[k]);
  submitted.value = false;
  localStorage.removeItem("books_ob_status");
  accounts.value.forEach((a) => {
    drCrMap[a.name] = OB_TYPE_META[a.root_type]?.balType || "Debit";
  });
  showResetModal.value = false;
  saveDraft();
  toast("Opening balances reset");
}

onMounted(load);
</script>

<style scoped>
/* ─────────────────────────────────────────────────────────
   Opening Balances — base styles
   ───────────────────────────────────────────────────────── */
.ob-step-dot {
  width: 24px; height: 24px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; flex-shrink: 0;
}
.ob-dot-done    { background: #2F9E44; color: #fff; }
.ob-dot-active  { background: #3B5BDB; color: #fff; }
.ob-dot-pending { background: #E2E8F0; color: #868E96; }

.ob-step-lbl {
  font-size: 13px; margin-left: 8px; white-space: nowrap;
}
.ob-lbl-done   { color: #2F9E44; font-weight: 600; }
.ob-lbl-active { color: #3B5BDB; font-weight: 600; }
.ob-lbl-muted  { color: #868E96; font-weight: 500; }

.ob-step-line {
  flex: 1; height: 2px; background: #E2E8F0; margin: 0 12px; border-radius: 1px;
}
.ob-line-done { background: #2F9E44; }

.ob-eq-diff {
  margin-top: 14px; padding: 10px 14px; border-radius: 8px;
  font-size: 13px; font-weight: 600; text-align: center;
}
.ob-eq-zero { background: #F8F9FC; color: #868E96; }
.ob-eq-ok   { background: #EBFBEE; color: #2F9E44; }
.ob-eq-err  { background: #FFE3E3; color: #C92A2A; }

.ob-acct-row {
  display: grid; grid-template-columns: 1fr 130px 130px;
  align-items: center; gap: 10px;
  padding: 8px 16px; border-top: 1px solid #F1F3F5;
}

.ob-bal-input {
  width: 100%; border: 1px solid #E2E8F0; border-radius: 6px;
  padding: 6px 10px; font-size: 13px;
  text-align: right; outline: none;
}
.ob-bal-input:focus { border-color: #3B5BDB; box-shadow: 0 0 0 3px rgba(59,91,219,.08); }
.ob-has-val { background: #F0FDF4; border-color: #86EFAC; }

.ob-dr-cr-sel {
  width: 100%; border: 1px solid #E2E8F0; border-radius: 6px;
  padding: 6px 10px; font-size: 12.5px; font-weight: 600;
  background: #fff; cursor: pointer; outline: none;
}
.ob-dr { color: #C92A2A; }
.ob-cr { color: #2F9E44; }

/* ── Default: mobile stepper hidden ── */
.ob-mobile-stepper { display: none; }

/* ── Default: desktop stepper visible ── */
.ob-desktop-stepper { display: flex; }

/* ═══════════════════════════════════════════════════════════
   TABLET  –  481 px … 768 px
   ═══════════════════════════════════════════════════════════ */
@media (min-width: 481px) and (max-width: 768px) {

  /* Stepper: tighter spacing */
  .ob-step-lbl { font-size: 11.5px !important; }
  .ob-step-line { margin: 0 6px !important; }

  /* Go-live bar: wrap tightly */
  .ob-go-live-bar {
    flex-direction: column !important;
    align-items: flex-start !important;
    gap: 10px !important;
  }

  .ob-go-live-bar > div:last-child {
    width: 100%;
    display: flex;
    gap: 8px;
  }

  .ob-go-live-bar > div:last-child button { flex: 1; justify-content: center; }

  /* Eq strip: 3-col stays but tighter */
  .ob-eq-title { font-size: 10px !important; }

  .ob-eq-strip > div[style*="flex:1"] {
    padding: 10px 12px !important;
  }

  /* Account column header: tighter widths */
  .ob-col-header {
    grid-template-columns: 1fr 110px 100px !important;
    padding: 6px 14px !important;
    gap: 6px !important;
  }

  /* Account rows: tighter columns */
  .ob-acct-row {
    grid-template-columns: 1fr 110px 100px !important;
    padding: 8px 14px !important;
    gap: 6px !important;
  }

  .ob-bal-input { padding: 5px 8px !important; font-size: 12.5px !important; }
  .ob-dr-cr-sel { padding: 5px 6px !important; font-size: 11.5px !important; }

  /* Section footer: match tighter widths */
  .ob-sec-footer {
    grid-template-columns: 1fr 110px 100px !important;
    padding: 8px 14px !important;
    gap: 6px !important;
  }

} /* end @media tablet 481–768px */

/* ═══════════════════════════════════════════════════════════
   MOBILE  –  ≤ 480 px
   ═══════════════════════════════════════════════════════════ */
@media (max-width: 480px) {

  /* ── Stepper: swap to mobile dots layout ── */
  .ob-desktop-stepper { display: none !important; }

  .ob-mobile-stepper {
    display: block;
    background: #fff;
    border: 1px solid #e8ecf0;
    border-radius: 10px;
    padding: 14px 12px 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }

  .ob-ms-dots {
    display: flex;
    align-items: center;
    width: 100%;
    margin-bottom: 10px;
  }

  .ob-ms-dot-wrap {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .ob-ms-dot { width: 26px; height: 26px; font-size: 11px; }

  .ob-ms-line {
    flex: 1; height: 2px;
    background: #E2E8F0; border-radius: 1px; margin: 0 4px;
  }
  .ob-ms-line.ob-line-done { background: #2F9E44; }

  .ob-ms-labels {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
  }

  .ob-ms-lbl {
    font-size: 9.5px; font-weight: 600; line-height: 1.3;
    text-align: center; padding: 0 2px;
    word-break: break-word; hyphens: auto;
  }
  .ob-ms-lbl.ob-lbl-done   { color: #2F9E44; }
  .ob-ms-lbl.ob-lbl-active { color: #3B5BDB; }
  .ob-ms-lbl.ob-lbl-muted  { color: #868E96; }

  /* ── Go-live bar: stack vertically ── */
  .ob-go-live-bar {
    flex-direction: column !important;
    align-items: flex-start !important;
    gap: 10px !important;
  }

  .ob-go-live-bar > div:first-child {
    flex-direction: column !important;
    align-items: flex-start !important;
    gap: 6px !important;
    width: 100%;
  }

  .ob-go-live-bar > div:first-child input[type="date"] {
    width: 100%; box-sizing: border-box;
  }

  .ob-go-live-bar > div:first-child span { font-size: 11px !important; }

  .ob-go-live-bar > div:last-child {
    width: 100%; display: flex; gap: 8px;
  }

  .ob-go-live-bar > div:last-child button,
  .ob-go-live-bar > div:last-child a {
    flex: 1; justify-content: center; text-align: center;
  }

  /* ── Equation card: clip overflow and reduce side padding ── */
  .ob-eq-card {
    padding: 12px 10px !important;
    overflow: hidden !important;
  }

  /* ── Equation check: compact horizontal row ── */
  .ob-eq-title {
    font-size: 8.5px !important;
    letter-spacing: 0.2px !important;
    margin-bottom: 8px !important;
  }

  .ob-eq-strip {
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    gap: 0 !important;
    align-items: stretch !important;
    width: 100% !important;
  }

  .ob-eq-cell {
    min-width: 0;
    flex: 1;
    padding: 6px 4px !important;
    text-align: center;
  }

  .ob-eq-lbl {
    font-size: 8px !important;
    letter-spacing: 0.1px !important;
    margin-bottom: 2px !important;
  }

  .ob-eq-val {
    font-size: 13px !important;
  }

  .ob-eq-op {
    padding: 0 3px !important;
    font-size: 12px !important;
    flex-shrink: 0;
  }

  .ob-eq-diff {
    font-size: 10.5px !important;
    padding: 7px 8px !important;
    line-height: 1.5;
  }

  /* ── Section header ── */
  .ob-sec-header { padding: 10px 12px !important; gap: 6px !important; }

  /* ── Column header: hidden on mobile (labels shown in cards) ── */
  .ob-col-header { display: none !important; }

  /* ── Account rows: 2-row card (name | balance + Dr/Cr) ── */
  .ob-acct-row {
    display: grid !important;
    grid-template-columns: 1fr 1fr !important;
    grid-template-rows: auto auto !important;
    gap: 6px 8px !important;
    padding: 10px 12px !important;
    border-top: 1px solid #f1f3f5;
  }

  .ob-acct-row > div:first-child {
    grid-column: 1 / -1;
    grid-row: 1;
  }

  .ob-acct-row > input.ob-bal-input {
    grid-column: 1;
    grid-row: 2;
    width: 100%;
    font-size: 13px !important;
    padding: 8px 10px !important;
  }

  .ob-acct-row > select.ob-dr-cr-sel {
    grid-column: 2;
    grid-row: 2;
    width: 100%;
    font-size: 11.5px !important;
    padding: 8px 6px !important;
  }

  /* ── Section footer ── */
  .ob-sec-footer {
    grid-template-columns: 1fr auto !important;
    padding: 8px 12px !important;
    gap: 6px !important;
  }

  .ob-sec-footer > div:last-child { display: none !important; }

  /* ── Modals: full width ── */
  div[style*="max-width:500px"],
  div[style*="max-width:420px"] {
    padding: 20px 18px !important;
    border-radius: 10px !important;
  }

} /* end @media mobile ≤480px */
</style>

