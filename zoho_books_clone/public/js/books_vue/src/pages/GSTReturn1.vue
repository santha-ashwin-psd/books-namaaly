<template>
  <div class="g1-page">

    <!-- ── Toolbar ── -->
    <div class="g1-toolbar">
      <div>
        <div class="g1-title">GSTR-1</div>
        <div class="g1-sub">Outward Supply Return — B2B, B2C, CDNR &amp; HSN</div>
      </div>
      <div class="g1-controls">
        <select v-model="period" class="g1-select" @change="load">
          <option v-for="p in periods" :key="p.v" :value="p.v">{{ p.l }}</option>
        </select>
        <button class="g1-btn-ghost" @click="load" :disabled="loading">
          <span v-html="icon('refresh',13)" :style="loading?'animation:spin 1s linear infinite;display:inline-flex':''"></span>
        </button>
        <button v-if="data" class="g1-btn-ghost" @click="exportCSV"><span v-html="icon('download',13)"></span> CSV</button>
        <button class="g1-btn-primary" @click="load" :disabled="loading">{{ loading ? 'Computing…' : 'Compute' }}</button>
      </div>
    </div>

    <!-- ── Deadline banner ── -->
    <div class="g1-deadline" :class="dueSoon?'due-warn':'due-ok'">
      <span v-html="icon('calendar',12)"></span>
      GSTR-1 for <strong>{{ periodLabel }}</strong> — due <strong>{{ dueDate }}</strong>
      <span v-if="dueSoon" style="font-weight:600"> · deadline approaching</span>
    </div>

    <!-- ── Summary strip ── -->
    <div class="g1-sum-strip">
      <div class="g1-sum-card">
        <div class="g1-sum-lbl">B2B Invoices</div>
        <div class="g1-sum-val">{{ data ? data.b2b.length : '—' }}</div>
      </div>
      <div class="g1-sum-card">
        <div class="g1-sum-lbl">B2C Invoices</div>
        <div class="g1-sum-val">{{ data ? data.b2c.length : '—' }}</div>
      </div>
      <div class="g1-sum-card">
        <div class="g1-sum-lbl">Credit Notes (CDNR)</div>
        <div class="g1-sum-val">{{ data ? data.cdnr.length : '—' }}</div>
      </div>
      <div class="g1-sum-card">
        <div class="g1-sum-lbl">Total Tax Collected</div>
        <div class="g1-sum-val" style="color:#16a34a">{{ data ? fmtCur(data.totals.total_tax) : '—' }}</div>
      </div>
    </div>

    <!-- ── HSN warning ── -->
    <div v-if="data && noHsnCount > 0" class="g1-warn">
      <span v-html="icon('alert',13)" style="flex-shrink:0"></span>
      <strong>{{ noHsnCount }} invoice(s)</strong>&nbsp;have items without HSN/SAC codes — add codes before filing.
    </div>

    <!-- ── Section tabs + Table ── -->
    <div v-if="data || loading" class="g1-card">

      <!-- Tab bar + search -->
      <div class="g1-card-top">
        <div class="g1-tabs">
          <button class="g1-tab" :class="{active:section==='b2b'}" @click="section='b2b';search=''">
            B2B <span class="g1-tab-ct">{{ data ? data.b2b.length : 0 }}</span>
          </button>
          <button class="g1-tab" :class="{active:section==='b2c'}" @click="section='b2c';search=''">
            B2C <span class="g1-tab-ct">{{ data ? data.b2c.length : 0 }}</span>
          </button>
          <button class="g1-tab" :class="{active:section==='cdnr'}" @click="section='cdnr';search=''">
            CDNR <span class="g1-tab-ct">{{ data ? data.cdnr.length : 0 }}</span>
          </button>
          <button class="g1-tab" :class="{active:section==='cdnur'}" @click="section='cdnur';search=''">
            CDNUR <span class="g1-tab-ct">{{ data ? data.cdnur.length : 0 }}</span>
          </button>
          <button class="g1-tab" :class="{active:section==='hsn'}" @click="section='hsn';search=''">
            HSN Summary <span class="g1-tab-ct">{{ data ? data.hsn_summary.length : 0 }}</span>
          </button>
        </div>
        <div class="g1-search-wrap">
          <span v-html="icon('search',12)" style="color:#9ca3af;flex-shrink:0"></span>
          <input v-model="search" class="g1-search" :placeholder="searchPlaceholder" />
        </div>
      </div>

      <!-- B2B table -->
      <div v-if="section==='b2b'" class="g1-table-wrap">
        <table class="g1-table">
          <thead><tr>
            <th @click="sortBy('name')" class="sortable">Invoice # <span v-html="sortArrow('name')"></span></th>
            <th @click="sortBy('posting_date')" class="sortable">Date <span v-html="sortArrow('posting_date')"></span></th>
            <th>Customer</th>
            <th>GSTIN</th>
            <th>Place of Supply</th>
            <th class="ta-r">Taxable</th>
            <th class="ta-r">IGST</th>
            <th class="ta-r">CGST</th>
            <th class="ta-r">SGST</th>
            <th class="ta-r">Invoice Value</th>
          </tr></thead>
          <tbody>
            <template v-if="loading">
              <tr v-for="n in 6" :key="n"><td colspan="10"><div class="g1-shimmer"></div></td></tr>
            </template>
            <template v-else>
              <tr v-for="inv in paginatedRows" :key="inv.name" class="g1-row">
                <td data-label="Invoice #"><span class="g1-code">{{ inv.name }}</span></td>
                <td data-label="Date" class="mono muted">{{ fmtDate(inv.posting_date) }}</td>
                <td data-label="Customer" class="fw5">{{ inv.customer_name || inv.customer }}</td>
                <td data-label="GSTIN" class="mono muted sm">{{ inv.customer_gstin || '—' }}</td>
                <td data-label="Place of Supply" class="muted">{{ inv.place_of_supply || '—' }}</td>
                <td data-label="Taxable" class="ta-r mono">{{ fmtCur(inv.net_total) }}</td>
                <td data-label="IGST" class="ta-r mono muted">{{ fmtCur(taxByType(inv,'IGST')) }}</td>
                <td data-label="CGST" class="ta-r mono muted">{{ fmtCur(taxByType(inv,'CGST')) }}</td>
                <td data-label="SGST" class="ta-r mono muted">{{ fmtCur(taxByType(inv,'SGST')) }}</td>
                <td data-label="Invoice Value" class="ta-r mono fw6">{{ fmtCur(inv.grand_total) }}</td>
              </tr>
              <tr v-if="!filteredRows.length"><td colspan="10" class="g1-empty">No B2B invoices — customers need a GSTIN on their record</td></tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- B2C table -->
      <div v-else-if="section==='b2c'" class="g1-table-wrap">
        <table class="g1-table">
          <thead><tr>
            <th @click="sortBy('name')" class="sortable">Invoice # <span v-html="sortArrow('name')"></span></th>
            <th @click="sortBy('posting_date')" class="sortable">Date <span v-html="sortArrow('posting_date')"></span></th>
            <th>Customer</th>
            <th>Place of Supply</th>
            <th class="ta-r">Taxable</th>
            <th class="ta-r">Tax</th>
            <th class="ta-r">Invoice Value</th>
          </tr></thead>
          <tbody>
            <template v-if="loading">
              <tr v-for="n in 6" :key="n"><td colspan="7"><div class="g1-shimmer"></div></td></tr>
            </template>
            <template v-else>
              <tr v-for="inv in paginatedRows" :key="inv.name" class="g1-row">
                <td data-label="Invoice #"><span class="g1-code">{{ inv.name }}</span></td>
                <td data-label="Date" class="mono muted">{{ fmtDate(inv.posting_date) }}</td>
                <td data-label="Customer" class="fw5">{{ inv.customer_name || inv.customer }}</td>
                <td data-label="Place of Supply" class="muted">{{ inv.place_of_supply || '—' }}</td>
                <td data-label="Taxable" class="ta-r mono">{{ fmtCur(inv.net_total) }}</td>
                <td data-label="Tax" class="ta-r mono fw6">{{ fmtCur(inv.total_tax) }}</td>
                <td data-label="Invoice Value" class="ta-r mono fw6">{{ fmtCur(inv.grand_total) }}</td>
              </tr>
              <tr v-if="!filteredRows.length"><td colspan="7" class="g1-empty">No B2C invoices for this period</td></tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- CDNR table -->
      <div v-else-if="section==='cdnr'" class="g1-table-wrap">
        <table class="g1-table">
          <thead><tr>
            <th @click="sortBy('name')" class="sortable">Note # <span v-html="sortArrow('name')"></span></th>
            <th @click="sortBy('posting_date')" class="sortable">Date <span v-html="sortArrow('posting_date')"></span></th>
            <th>Customer</th>
            <th>GSTIN</th>
            <th>Against Invoice</th>
            <th class="ta-r">Taxable</th>
            <th class="ta-r">Tax</th>
            <th class="ta-r">Note Value</th>
          </tr></thead>
          <tbody>
            <template v-if="loading">
              <tr v-for="n in 4" :key="n"><td colspan="8"><div class="g1-shimmer"></div></td></tr>
            </template>
            <template v-else>
              <tr v-for="inv in paginatedRows" :key="inv.name" class="g1-row">
                <td data-label="Date" class="mono muted">{{ fmtDate(inv.posting_date) }}</td>
                <td data-label="Customer" class="fw5">{{ inv.customer_name || inv.customer }}</td>
                <td data-label="GSTIN" class="mono muted sm">{{ inv.customer_gstin || '—' }}</td>
                <td data-label="Against Invoice" class="mono muted">{{ inv.return_against || '—' }}</td>
                <td data-label="Taxable" class="ta-r mono">{{ fmtCur(inv.net_total) }}</td>
                <td data-label="Tax" class="ta-r mono fw6">{{ fmtCur(inv.total_tax) }}</td>
                <td data-label="Note Value" class="ta-r mono fw6 cdnr-code">{{ fmtCur(inv.grand_total) }}</td>
              </tr>
              <tr v-if="!filteredRows.length"><td colspan="8" class="g1-empty">No credit notes for this period</td></tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- HSN table -->
      <div v-else-if="section==='cdnur'" class="g1-table-wrap">
        <table class="g1-table">
          <thead><tr>
            <th @click="sortBy('name')" class="sortable">Note # <span v-html="sortArrow('name')"></span></th>
            <th @click="sortBy('posting_date')" class="sortable">Date <span v-html="sortArrow('posting_date')"></span></th>
            <th>Customer</th>
            <th>Against Invoice</th>
            <th class="ta-r">Taxable</th>
            <th class="ta-r">Tax</th>
            <th class="ta-r">Note Value</th>
          </tr></thead>
          <tbody>
            <template v-if="loading">
              <tr v-for="n in 4" :key="n"><td colspan="7"><div class="g1-shimmer"></div></td></tr>
            </template>
            <template v-else>
              <tr v-for="inv in paginatedRows" :key="inv.name" class="g1-row">
                <td data-label="Note #"><span class="g1-code cdnr-code">{{ inv.name }}</span></td>
                <td data-label="Date" class="mono muted">{{ fmtDate(inv.posting_date) }}</td>
                <td data-label="Customer" class="fw5">{{ inv.customer_name || inv.customer }}</td>
                <td data-label="Against Invoice" class="mono muted">{{ inv.return_against || '—' }}</td>
                <td data-label="Taxable" class="ta-r mono">{{ fmtCur(inv.net_total) }}</td>
                <td data-label="Tax" class="ta-r mono fw6">{{ fmtCur(inv.total_tax) }}</td>
                <td data-label="Note Value" class="ta-r mono fw6 cdnr-code">{{ fmtCur(inv.grand_total) }}</td>
              </tr>
              <tr v-if="!filteredRows.length"><td colspan="7" class="g1-empty">No credit notes against unregistered customers for this period</td></tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- HSN table -->
      <div v-else-if="section==='hsn'" class="g1-table-wrap">
        <table class="g1-table">
          <thead><tr>
            <th>HSN / SAC Code</th>
            <th class="ta-r">No. of Invoices</th>
            <th class="ta-r">Taxable Value</th>
          </tr></thead>
          <tbody>
            <template v-if="loading">
              <tr v-for="n in 4" :key="n"><td colspan="3"><div class="g1-shimmer"></div></td></tr>
            </template>
            <template v-else>
              <tr v-for="h in paginatedRows" :key="h.hsn_code" class="g1-row">
                <td data-label="HSN / SAC Code">
                  <span class="g1-code" :class="h.hsn_code==='Not Set'?'warn-code':''">{{ h.hsn_code }}</span>
                  <span v-if="h.hsn_code==='Not Set'" class="g1-warn-tag">Add HSN to items</span>
                </td>
                <td data-label="No. of Invoices" class="ta-r mono">{{ h.invoice_count }}</td>
                <td data-label="Taxable Value" class="ta-r mono fw6">{{ fmtCur(h.taxable_value) }}</td>
              </tr>
              <tr v-if="!filteredRows.length"><td colspan="3" class="g1-empty">No HSN data — add HSN/SAC codes to your items</td></tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- Load More -->
      <div v-if="!loading && hasMore" class="g1-load-more-wrap">
        <button class="g1-btn-ghost g1-load-more-btn" @click="loadMore">
          Load More ({{ filteredRows.length - visibleCount }} remaining)
        </button>
      </div>

    </div>
    <div v-else class="g1-placeholder">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" stroke-width="1.3"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
      <div class="g1-ph-title">Select a period and click Compute</div>
      <div class="g1-ph-sub">GSTR-1 data will appear here</div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { apiGET, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";
import { flt, fmtDate } from "../utils/format.js";

const { toast } = useToast();
const loading  = ref(false);
const data     = ref(null);
const section  = ref("b2b");
const search   = ref("");
const sortKey  = ref("posting_date");
const sortDir  = ref(-1);

const now = new Date();
function makePeriods() {
  const ps = [];
  for (let i = 0; i < 12; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const v = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}`;
    const l = d.toLocaleString("en-IN", { month:"long", year:"numeric" });
    ps.push({ v, l });
  }
  return ps;
}
const periods = makePeriods();
const period  = ref(periods[0].v);

const periodLabel = computed(() => periods.find(p => p.v === period.value)?.l || period.value);
const dueDate = computed(() => {
  const [yr, mo] = period.value.split("-");
  return new Date(+yr, +mo, 11).toLocaleDateString("en-IN", { day:"2-digit", month:"short", year:"numeric" });
});
const dueSoon = computed(() => {
  const [yr, mo] = period.value.split("-");
  const diff = (new Date(+yr, +mo, 11) - now) / 864e5;
  return diff >= 0 && diff <= 7;
});

const noHsnCount = computed(() => {
  if (!data.value) return 0;
  return (data.value.hsn_summary||[]).filter(h=>h.hsn_code==="Not Set").reduce((s,h)=>s+h.invoice_count,0);
});

const searchPlaceholder = computed(() => {
  if (section.value === "hsn")   return "Search HSN code…";
  if (section.value === "cdnr")  return "Search note # or GSTIN…";
  if (section.value === "cdnur") return "Search note #…";
  return "Search invoice # or customer…";
});

const activeRows = computed(() => {
  if (!data.value) return [];
  if (section.value === "b2b")   return data.value.b2b;
  if (section.value === "b2c")   return data.value.b2c;
  if (section.value === "cdnr")  return data.value.cdnr;
  if (section.value === "cdnur") return data.value.cdnur;
  if (section.value === "hsn")   return data.value.hsn_summary;
  return [];
});

const filteredRows = computed(() => {
  let rows = activeRows.value;
  const q = search.value.toLowerCase().trim();
  if (q) {
    rows = rows.filter(r =>
      (r.name||"").toLowerCase().includes(q) ||
      (r.customer_name||"").toLowerCase().includes(q) ||
      (r.customer_gstin||"").toLowerCase().includes(q) ||
      (r.hsn_code||"").toLowerCase().includes(q)
    );
  }
  if (section.value !== "hsn" && sortKey.value) {
    const k = sortKey.value, d = sortDir.value;
    rows = [...rows].sort((a,b) => {
      const av = a[k]||"", bv = b[k]||"";
      return av < bv ? -d : av > bv ? d : 0;
    });
  }
  return rows;
});

const PAGE_SIZE = 10;
const visibleCount = ref(PAGE_SIZE);
const paginatedRows = computed(() => filteredRows.value.slice(0, visibleCount.value));
const hasMore = computed(() => visibleCount.value < filteredRows.value.length);
function loadMore() { visibleCount.value += PAGE_SIZE; }

watch([section, search, period], () => { visibleCount.value = PAGE_SIZE; });

function sortBy(k) {
  if (sortKey.value === k) sortDir.value *= -1;
  else { sortKey.value = k; sortDir.value = -1; }
}
function sortArrow(k) {
  if (sortKey.value !== k) return `<span style="color:#d1d5db">⇅</span>`;
  return sortDir.value === 1 ? "↑" : "↓";
}

function taxByType(inv, type) {
  if (!inv.taxes?.length) return 0;
  const t = inv.taxes.find(r=>(r.tax_type||"").toUpperCase()===type||(r.description||"").toUpperCase().includes(type));
  return flt(t?.tax_amount);
}

async function load() {
  loading.value = true; data.value = null;
  try {
    const co = await resolveCompany();
    const [yr, mo] = period.value.split("-");
    const from = `${yr}-${mo}-01`;
    const to   = `${yr}-${mo}-${String(new Date(+yr,+mo,0).getDate()).padStart(2,"0")}`;
    data.value = await apiGET("zoho_books_clone.db.queries.get_gstr1_data", { company:co, from_date:from, to_date:to });
  } catch (e) { toast.error(e.message||"Failed to load GSTR-1"); }
  finally { loading.value = false; }
}

function exportCSV() {
  if (!data.value) return;
  const rows = [
    ["Section","Invoice #","Date","Customer","GSTIN","Place of Supply","Taxable","Tax","Invoice Value"],
    ...data.value.b2b.map(i=>["B2B",i.name,i.posting_date,i.customer_name||i.customer,i.customer_gstin||"",i.place_of_supply||"",flt(i.net_total),flt(i.total_tax),flt(i.grand_total)]),
    ...data.value.b2c.map(i=>["B2C",i.name,i.posting_date,i.customer_name||i.customer,"",i.place_of_supply||"",flt(i.net_total),flt(i.total_tax),flt(i.grand_total)]),
    ...data.value.cdnr.map(i=>["CDNR",i.name,i.posting_date,i.customer_name||i.customer,i.customer_gstin||"",i.place_of_supply||"",flt(i.net_total),flt(i.total_tax),flt(i.grand_total)]),
    ...data.value.cdnur.map(i=>["CDNUR",i.name,i.posting_date,i.customer_name||i.customer,"",i.place_of_supply||"",flt(i.net_total),flt(i.total_tax),flt(i.grand_total)]),
    [],[" HSN Code","Invoice Count","Taxable Value"],
    ...data.value.hsn_summary.map(h=>[h.hsn_code,h.invoice_count,flt(h.taxable_value)]),
  ];
  const csv = rows.map(r=>r.map(v=>`"${String(v).replace(/"/g,'""')}"`).join(",")).join("\n");
  const a = document.createElement("a");
  a.href = "data:text/csv;charset=utf-8,"+encodeURIComponent(csv);
  a.download = `GSTR-1_${period.value}.csv`; a.click();
}

function fmtCur(v) { return new Intl.NumberFormat("en-IN",{style:"currency",currency:"INR",minimumFractionDigits:2}).format(flt(v)); }

onMounted(load);
</script>

<style scoped>
@keyframes spin    { to { transform: rotate(360deg); } }
@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }

.g1-page { display:flex; flex-direction:column; gap:14px; padding:24px; background:#f8fafc; min-height:100%; font-family:'Inter','Lato',system-ui,-apple-system,sans-serif; }

/* Toolbar */
.g1-toolbar { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px; background:#fff; border:1px solid #e5e7eb; border-radius:10px; padding:16px 20px; }
.g1-title { font-size:16px; font-weight:700; color:#111827; }
.g1-sub   { font-size:11.5px; color:#9ca3af; margin-top:2px; }
.g1-controls { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
.g1-select { border:1px solid #e2e8f0; border-radius:7px; padding:7px 11px; font:inherit; font-size:13px; outline:none; background:#fff; color:#111827; cursor:pointer; }
.g1-select:focus { border-color:#2563eb; }
.g1-btn-primary { display:inline-flex; align-items:center; gap:6px; background:#2563eb; color:#fff; border:none; border-radius:7px; padding:7px 14px; font-size:13px; font-weight:600; cursor:pointer; font-family:inherit; transition:background .15s; }
.g1-btn-primary:hover:not(:disabled) { background:#1d4ed8; }
.g1-btn-primary:disabled { opacity:.55; cursor:not-allowed; }
.g1-btn-ghost { display:inline-flex; align-items:center; gap:6px; background:#fff; border:1px solid #e5e7eb; border-radius:7px; padding:7px 11px; font-size:13px; font-weight:500; color:#374151; cursor:pointer; font-family:inherit; transition:all .15s; }
.g1-btn-ghost:hover:not(:disabled) { background:#f9fafb; }
.g1-btn-ghost:disabled { opacity:.45; cursor:not-allowed; }

/* Deadline */
.g1-deadline { display:flex; align-items:center; gap:8px; border-radius:8px; padding:9px 14px; font-size:12.5px; font-weight:500; }
.due-ok   { background:#f0fdf4; border:1px solid #bbf7d0; color:#15803d; }
.due-warn { background:#fffbeb; border:1px solid #fde68a; color:#b45309; }

/* Summary strip */
.g1-sum-strip { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }
.g1-sum-card  { background:#fff; border:1px solid #e5e7eb; border-radius:10px; padding:14px 16px; }
.g1-sum-lbl   { font-size:11px; color:#6b7280; text-transform:uppercase; letter-spacing:.05em; margin-bottom:4px; }
.g1-sum-val   { font-size:18px; font-weight:700; color:#111827; }

/* Warning */
.g1-warn { display:flex; align-items:center; gap:8px; background:#fff7ed; border:1px solid #fed7aa; border-radius:8px; padding:10px 14px; font-size:12.5px; color:#c2410c; font-weight:500; }

/* Card (tab+table container) */
.g1-card { background:#fff; border:1px solid #e5e7eb; border-radius:10px; overflow:hidden; }
.g1-card-top { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px; padding:12px 16px; border-bottom:1px solid #f1f5f9; }

/* Tabs */
.g1-tabs { display:flex; gap:2px; background:#f3f4f6; border-radius:7px; padding:3px; }
.g1-tab  { border:none; background:transparent; border-radius:5px; padding:5px 12px; font-size:12.5px; font-weight:600; color:#6b7280; cursor:pointer; font-family:inherit; transition:all .15s; white-space:nowrap; display:flex; align-items:center; gap:5px; }
.g1-tab.active { background:#fff; color:#2563eb; box-shadow:0 1px 3px rgba(0,0,0,.08); }
.g1-tab-ct { background:#e5e7eb; color:#6b7280; border-radius:10px; padding:0 6px; font-size:10.5px; font-weight:700; }
.g1-tab.active .g1-tab-ct { background:#dbeafe; color:#1d4ed8; }

/* Search */
.g1-search-wrap { display:flex; align-items:center; gap:6px; background:#f9fafb; border:1px solid #e5e7eb; border-radius:7px; padding:5px 10px; min-width:180px; transition:all .15s; }
.g1-search-wrap:focus-within { background:#fff; border-color:#2563eb; }
.g1-search { border:none; background:transparent; outline:none; font:inherit; font-size:12.5px; color:#111827; width:100%; }
.g1-search::placeholder { color:#9ca3af; }

/* Table */
.g1-table-wrap { overflow-x:auto; }
.g1-table { width:100%; border-collapse:collapse; font-size:12.5px; min-width:520px; }
.g1-table thead tr { background:#f8fafc; }
.g1-table th { border-bottom:1px solid #e5e7eb; padding:9px 14px; font-size:10.5px; font-weight:700; color:#9ca3af; text-align:left; white-space:nowrap; letter-spacing:.05em; text-transform:uppercase; }
.g1-table th.sortable { cursor:pointer; user-select:none; }
.g1-table th.sortable:hover { color:#2563eb; }
.ta-r  { text-align:right !important; }
.g1-row td { padding:10px 14px; border-bottom:1px solid #f8fafc; color:#374151; vertical-align:middle; }
.g1-row:last-child td { border-bottom:none; }
.g1-row:hover td { background:#f8fafc; }
.g1-code { font-size:12px; color:#2563eb; font-weight:700; }
.cdnr-code { color:#ea580c !important; }
.warn-code { color:#ea580c !important; }
.mono  { font-variant-numeric:tabular-nums; }
.fw5   { font-weight:500; }
.fw6   { font-weight:600; }
.muted { color:#9ca3af; }
.sm    { font-size:11.5px; }
.g1-warn-tag { font-size:10.5px; background:#fff7ed; color:#ea580c; border:1px solid #fed7aa; border-radius:4px; padding:1px 7px; margin-left:6px; font-weight:600; }
.g1-empty { text-align:center; color:#b0bac7; padding:40px !important; font-size:13px; font-style:italic; }
.g1-shimmer { height:13px; background:linear-gradient(90deg,#f1f5f9 25%,#e2e8f0 50%,#f1f5f9 75%); border-radius:4px; animation:shimmer 1.4s infinite; background-size:200% 100%; margin:10px 0; }

/* Load More */
.g1-load-more-wrap { display:flex; justify-content:center; padding:14px 16px; border-top:1px solid #f1f5f9; }
.g1-load-more-btn  { width:100%; max-width:320px; justify-content:center; font-weight:600; color:#2563eb; border-color:#bfdbfe; }
.g1-load-more-btn:hover { background:#eff6ff; border-color:#93c5fd; }

/* Placeholder */
.g1-placeholder { display:flex; flex-direction:column; align-items:center; gap:8px; padding:64px; background:#fff; border:1px solid #e5e7eb; border-radius:10px; }
.g1-ph-title { font-size:14px; font-weight:600; color:#374151; }
.g1-ph-sub   { font-size:12.5px; color:#9ca3af; }

/* Mobile table cards */
@media (max-width: 640px) {
  .g1-table-wrap {
    overflow-x: visible;
  }
  
  .g1-table {
    min-width: 0;
    border: none;
  }
  
  .g1-table thead {
    display: none;
  }
  
  .g1-table tbody {
    display: block;
  }
  
  .g1-table .g1-row {
    display: block;
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    margin-bottom: 12px;
    padding: 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }
  
  .g1-table .g1-row:hover td {
    background: transparent;
  }
  
  .g1-table .g1-row td {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 14px;
    border: none;
    border-bottom: 1px solid #f3f4f6;
    text-align: right;
  }
  
  .g1-table .g1-row td:last-child {
    border-bottom: none;
  }
  
  .g1-table .g1-row td:first-child {
    background: #f8fafc;
    font-weight: 600;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
  }
  
  .g1-table .g1-row td::before {
    content: attr(data-label);
    font-weight: 600;
    color: #6b7280;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    text-align: left;
    flex-shrink: 0;
  }
  
  .g1-table .g1-row td.ta-r {
    text-align: right;
  }
  
  /* Empty state on mobile */
  .g1-table .g1-empty {
    display: block;
    text-align: center;
    padding: 32px 20px !important;
  }
  
  /* Shimmer loader on mobile */
  .g1-table tbody tr:has(.g1-shimmer) {
    display: block;
    margin-bottom: 12px;
  }
  
  .g1-table tbody tr:has(.g1-shimmer) td {
    display: block;
    padding: 12px;
  }
  
  /* Specific adjustments for HSN warn tag */
  .g1-warn-tag {
    display: block;
    margin-top: 4px;
    margin-left: 0;
  }
  
  /* Card top adjustments */
  .g1-card-top {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  
  .g1-tabs {
    width: 100%;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
  
  .g1-search-wrap {
    width: 100%;
  }
}

@media (max-width: 768px) {
  .g1-sum-strip   { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 480px) {
  .g1-page    { padding: 12px; gap: 10px; }
  .g1-toolbar { padding: 12px 14px; }
  .g1-sum-strip { grid-template-columns: 1fr; }
  
  .g1-sum-card {
    padding: 12px 14px;
  }
  
  .g1-controls {
    width: 100%;
  }
  
  .g1-select, .g1-btn-primary, .g1-btn-ghost {
    width: 100%;
    justify-content: center;
  }
}
</style>