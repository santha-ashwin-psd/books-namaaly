<template>
<div class="cust-page">
  <div class="cust-toolbar">
    <div style="display:flex;align-items:center;gap:12px">
      <span style="font-size:18px;font-weight:700;color:#1a1a2e">Number Series</span>
      <span style="background:#EBFBEE;color:#2F9E44;padding:2px 10px;border-radius:20px;font-size:12px;font-weight:600">{{series.length}} series</span>
    </div>
    <button class="nim-btn nim-btn-primary" :disabled="!$canCreate('admin')" :title="!$canCreate('admin') ? 'Read-only access' : ''" @click="openAdd"><span v-html="icon('plus',13)" style="vertical-align:-2px;margin-right:4px"/>Add Series</button>
  </div>

  <div style="background:linear-gradient(135deg,#EBFBEE,#D3F9D8);border:1px solid #8CE99A;border-radius:10px;padding:14px 18px;margin-bottom:16px;display:flex;gap:12px;align-items:center">
    <span style="font-size:20px">🔢</span>
    <div style="font-size:12.5px;color:#2F9E44">Number series control the auto-numbering of your documents. The next number is generated as <b>PREFIX + padded sequence</b>. For example: <b>INV-0001</b>, <b>INV-0002</b>, etc.</div>
  </div>

  <div v-if="loading" style="padding:60px;text-align:center;color:#868e96">Loading…</div>

  <div v-else class="cust-table-card sns-tbl-card" style="margin-top:0">
    <table class="sns-desktop-table" style="width:100%;border-collapse:collapse;font-size:13px">
      <thead><tr style="background:#f8f9fc;border-bottom:2px solid #e4e8f0">
        <th style="padding:10px 16px;text-align:left;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#6b7db3">Document Type</th>
        <th style="padding:10px 16px;text-align:left;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#6b7db3">Prefix</th>
        <th style="padding:10px 16px;text-align:left;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#6b7db3">Padding</th>
        <th style="padding:10px 16px;text-align:left;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#6b7db3">Current</th>
        <th style="padding:10px 16px;text-align:left;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#6b7db3">Next Preview</th>
        <th style="padding:10px 16px;text-align:right;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#6b7db3">Actions</th>
      </tr></thead>
      <tbody>
        <tr v-for="s in series" :key="s.prefix" style="border-bottom:1px solid #f0f2f7">
          <td style="padding:12px 16px">
            <span style="background:#F3F0FF;color:#2563eb;padding:2px 10px;border-radius:20px;font-size:12px;font-weight:600">{{s.doctype}}</span>
          </td>
          <td style="padding:12px 16px;font-weight:700;color:#1a1a2e;font-size:13.5px">{{s.prefix}}</td>
          <td style="padding:12px 16px;color:#4a5568;text-align:center">{{s.padding||4}}</td>
          <td style="padding:12px 16px;color:#4a5568;text-align:center">{{s.current||0}}</td>
          <td style="padding:12px 16px;color:#2F9E44;font-weight:600">{{preview(s)}}</td>
          <td style="padding:12px 16px;text-align:right">
            <button class="nim-btn nim-btn-ghost" :disabled="!$canEdit('admin')" :title="!$canEdit('admin') ? 'Read-only access' : ''" @click="resetSeries(s)" style="font-size:12px;color:#c92a2a">Reset to 1</button>
          </td>
        </tr>
        <tr v-if="!series.length"><td colspan="6" style="padding:40px;text-align:center;color:#868e96">No number series configured</td></tr>
      </tbody>
    </table>

    <!-- Mobile cards (shown at ≤768px) -->
    <div class="sns-mobile-cards">
      <div v-if="!series.length" class="sns-mc-empty">
        <div style="font-size:32px;margin-bottom:8px">🔢</div>
        <div>No number series configured</div>
      </div>
      <template v-else>
        <div v-for="s in series" :key="s.prefix" class="sns-mobile-card">
          <div class="sns-mc-top">
            <span class="sns-mc-prefix">{{ s.prefix }}</span>
            <span style="background:#EBFBEE;color:#2F9E44;padding:2px 8px;border-radius:20px;font-size:12px;font-weight:600">{{ preview(s) }}</span>
          </div>
          <div class="sns-mc-mid">{{ s.doctype }}</div>
          <div class="sns-mc-meta">
            <span>Current: {{ s.current||0 }} · Padding: {{ s.padding||4 }}</span>
            <button class="nim-btn nim-btn-ghost" :disabled="!$canEdit('admin')" @click.stop="resetSeries(s)" style="font-size:11.5px;color:#c92a2a;padding:3px 8px">Reset</button>
          </div>
        </div>
      </template>
    </div>
  </div>

  <Teleport to="body">
    <div v-if="showDrawer" class="nim-overlay" @click.self="showDrawer=false">
      <div class="nim-dialog" style="width:480px">
        <div class="nim-header">
          <span style="font-size:15px;font-weight:700">Add Number Series</span>
          <button class="nim-btn nim-btn-ghost" @click="showDrawer=false"><span v-html="icon('x',14)"/></button>
        </div>
        <div class="nim-body" style="display:grid;gap:14px">
          <div class="nim-field">
            <label class="nim-label">Document Type <span style="color:#c92a2a">*</span></label>
            <select class="nim-input" v-model="form.doctype">
              <option value="">-- Select --</option>
              <option v-for="d in DOCTYPE_OPTIONS" :key="d" :value="d">{{d}}</option>
            </select>
          </div>
          <div class="nim-field">
            <label class="nim-label">Prefix <span style="color:#c92a2a">*</span></label>
            <input class="nim-input" v-model="form.prefix" placeholder="e.g. INV-" />
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
            <div class="nim-field">
              <label class="nim-label">Start From</label>
              <input class="nim-input" type="number" v-model="form.current" min="0"/>
            </div>
            <div class="nim-field">
              <label class="nim-label">Padding (digits)</label>
              <input class="nim-input" type="number" v-model="form.padding" min="1" max="10"/>
            </div>
          </div>
          <div v-if="form.prefix" style="background:#f8f9fc;border-radius:8px;padding:12px;font-size:12.5px">
            Preview: <b style="color:#2F9E44">{{form.prefix}}{{String((form.current||0)+1).padStart(form.padding||4,'0')}}</b>
          </div>
        </div>
        <div class="nim-footer">
          <button class="nim-btn nim-btn-ghost" @click="showDrawer=false">Cancel</button>
          <button class="nim-btn nim-btn-primary" @click="save" :disabled="saving || !$canCreate('admin')" :title="!$canCreate('admin') ? 'Read-only access' : ''">{{saving?'Saving…':'Save'}}</button>
        </div>
      </div>
    </div>
  </Teleport>
</div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { apiGET, apiPOST } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";

const { toast } = useToast();

const loading = ref(false);
const saving  = ref(false);
const series  = ref([]);
const showDrawer = ref(false);
const form = reactive({ prefix: "", current: 0, padding: 4, doctype: "" });

const DOCTYPE_OPTIONS = [
  "Sales Invoice", "Purchase Invoice", "Sales Order", "Purchase Order",
  "Quotation", "Payment Entry", "Journal Entry", "Stock Entry",
  "Expense Claim", "Delivery Note", "Purchase Receipt",
];

async function load() {
  loading.value = true;
  try {
    const raw = await apiGET("zoho_books_clone.api.admin.get_number_series") || [];
    series.value = raw;
  } catch {
    series.value = [
      { prefix: "INV-", current: 1, padding: 4, doctype: "Sales Invoice" },
      { prefix: "PUR-", current: 1, padding: 4, doctype: "Purchase Invoice" },
      { prefix: "SO-",  current: 1, padding: 4, doctype: "Sales Order" },
      { prefix: "PO-",  current: 1, padding: 4, doctype: "Purchase Order" },
      { prefix: "QTN-", current: 1, padding: 4, doctype: "Quotation" },
      { prefix: "PAY-", current: 1, padding: 4, doctype: "Payment Entry" },
      { prefix: "JE-",  current: 1, padding: 4, doctype: "Journal Entry" },
    ];
  }
  loading.value = false;
}

function preview(s) {
  const num = String((s.current || 1) + 1).padStart(s.padding || 4, "0");
  return (s.prefix || "") + num;
}

function openAdd() {
  Object.assign(form, { prefix: "", current: 0, padding: 4, doctype: "" });
  showDrawer.value = true;
}

async function save() {
  if (!form.prefix.trim()) return toast("Prefix is required", "error");
  if (!form.doctype)       return toast("Document type is required", "error");
  saving.value = true;
  try {
    await apiPOST("zoho_books_clone.api.admin.save_number_series", { ...form });
    toast("Number series saved");
    showDrawer.value = false;
    load();
  } catch (e) { toast(e.message, "error"); }
  saving.value = false;
}

async function resetSeries(s) {
  try {
    await apiPOST("zoho_books_clone.api.admin.reset_number_series", { prefix: s.prefix, doctype: s.doctype });
    toast("Series reset to 1");
    load();
  } catch (e) { toast(e.message, "error"); }
}

onMounted(load);
</script>

<style>
.sns-mobile-cards { display: none; }
.sns-desktop-table { display: table; }

@media (max-width: 768px) {
  .sns-desktop-table { display: none !important; }
  .sns-mobile-cards { display: flex; flex-direction: column; gap: 0; background: #f8fafc; }
  .sns-mobile-card { background: #fff; border-bottom: 1px solid #e5e7eb; padding: 12px 14px; }
  .sns-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .sns-mc-prefix { font-size: 14px; font-weight: 800; color: #1a1a2e; }
  .sns-mc-mid { font-size: 12px; color: #6b7280; margin-bottom: 6px; }
  .sns-mc-meta { display: flex; align-items: center; justify-content: space-between; font-size: 12px; color: #868e96; }
  .sns-mc-empty { text-align: center; padding: 32px 16px; color: #868e96; font-size: 13px; }
}
@media (max-width: 480px) {
  .cust-page { padding: 12px !important; }
}
</style>