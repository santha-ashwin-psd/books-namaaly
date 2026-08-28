<template>
  <div class="jt-wrap">
    <div class="jt-currency-note">
      Amount is displayed in your base currency <span class="jt-currency-badge">{{ currency }}</span>
    </div>
    <div class="jt-doctype-lbl">{{ label }}</div>

    <div v-if="loading" class="jt-loading">
      <div class="b-shimmer" style="height:14px;margin-bottom:8px" v-for="n in 3" :key="n"></div>
    </div>
    <div v-else-if="!rows.length" class="jt-empty">No journal entries found for this transaction.</div>
    <template v-else>
      <div class="jt-table">
        <div class="jt-row jt-head">
          <span>Account</span><span class="ta-r">Debit</span><span class="ta-r">Credit</span>
        </div>
        <div v-for="(r, i) in normalizedRows" :key="i" class="jt-row">
          <span class="jt-acct">{{ acctName(r.account) }}</span>
          <span class="ta-r">{{ r.debit ? fmt(r.debit) : '—' }}</span>
          <span class="ta-r">{{ r.credit ? fmt(r.credit) : '—' }}</span>
        </div>
        <div class="jt-row jt-total">
          <span>Total</span>
          <span class="ta-r">{{ fmt(normTotalDebit) }}</span>
          <span class="ta-r">{{ fmt(normTotalCredit) }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { apiGET } from "../api/client.js";

const props = defineProps({
  /** Frappe voucher_type, e.g. "Sales Invoice", "Purchase Invoice", "Expense", "Payment Entry" */
  voucherType: { type: String, required: true },
  /** Voucher document name/id, e.g. "INV-2026-00018" */
  voucherNo:   { type: String, required: true },
  /** Heading shown above the table, e.g. "Invoice", "Expense" */
  label:       { type: String, default: "" },
  currency:    { type: String, default: "OMR" },
});

const rows = ref([]);
const loading = ref(false);

// Return-style documents (e.g. Credit Notes implemented as Sales Invoice with
// is_return=1) post GL rows with a NEGATIVE amount left in the original
// debit/credit column instead of flipping it into the opposite column.
// A ledger should never show a negative debit or credit — normalize here so
// each row always shows a positive amount in the correct column, regardless
// of how the source document stored it.
function normalizeRow(r) {
  let debit = Number(r.debit || 0);
  let credit = Number(r.credit || 0);
  if (debit < 0) { credit += -debit; debit = 0; }
  if (credit < 0) { debit += -credit; credit = 0; }
  return { ...r, debit, credit };
}

const normalizedRows = computed(() => rows.value.map(normalizeRow));
const normTotalDebit  = computed(() => normalizedRows.value.reduce((s, r) => s + r.debit, 0));
const normTotalCredit = computed(() => normalizedRows.value.reduce((s, r) => s + r.credit, 0));

function fmt(v) {
  const n = Number(v || 0);
  return n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Frappe account names are stored as "Account Name - CompanyAbbr" (e.g. "Sales Revenue - PSD").
// Strip the trailing " - Abbr" for a cleaner display, same as Zoho's account column.
function acctName(name) {
  if (!name) return "";
  const idx = name.lastIndexOf(" - ");
  return idx > -1 ? name.slice(0, idx) : name;
}

async function load() {
  if (!props.voucherType || !props.voucherNo) { rows.value = []; return; }
  loading.value = true;
  try {
    const res = await apiGET("zoho_books_clone.api.books_data.get_voucher_journal", {
      voucher_type: props.voucherType,
      voucher_no: props.voucherNo,
    });
    rows.value = (res && res.rows) || [];
  } catch (e) {
    rows.value = [];
  } finally {
    loading.value = false;
  }
}

watch(() => [props.voucherType, props.voucherNo], load, { immediate: true });
</script>

<style scoped>
.jt-wrap { padding: 4px 2px 8px; }
.jt-currency-note { font-size: 12.5px; color: #6b7280; display: flex; align-items: center; gap: 8px; margin-bottom: 14px; }
.jt-currency-badge { background: #166534; color: #fff; font-size: 10.5px; font-weight: 700; padding: 2px 8px; border-radius: 4px; letter-spacing: 0.3px; }
.jt-doctype-lbl { font-size: 15px; font-weight: 700; color: #1a1a2e; margin-bottom: 10px; }
.jt-empty { font-size: 13px; color: #9ca3af; padding: 18px 0; }
.jt-table { border-top: 1px solid #e5e7eb; }
.jt-row { display: grid; grid-template-columns: 1fr 140px 140px; gap: 10px; padding: 9px 4px; font-size: 13px; }
.jt-row + .jt-row { border-top: 1px solid #f1f5f9; }
.jt-head { color: #94a3b8; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.4px; border-top: none; }
.jt-acct { color: #1a1a2e; font-weight: 500; }
.jt-total { font-weight: 700; color: #1a1a2e; border-top: 2px solid #1a1a2e !important; }
.ta-r { text-align: right; font-variant-numeric: tabular-nums; }
</style>