<template>
<div class="cust-page">
  <!-- ── Toolbar ────────────────────────────────────────────────────── -->
  <div class="cust-toolbar">
    <div style="display:flex;align-items:center;gap:12px">
      <span style="font-size:18px;font-weight:700;color:#1a1a2e">Tax Templates</span>
      <span style="background:#E3F9E5;color:#2F9E44;padding:2px 10px;border-radius:20px;font-size:12px;font-weight:600">
        {{ list.filter(t=>!t.disabled).length }} active
      </span>
    </div>
    <button class="nim-btn nim-btn-primary" :disabled="!$canCreate('taxes')" :title="!$canCreate('taxes') ? 'Read-only access' : ''" @click="openAdd">
      <span v-html="icon('plus',13)" style="vertical-align:-2px;margin-right:4px"/>New Template
    </button>
  </div>

  <!-- ── Info banner ───────────────────────────────────────────────── -->
  <div style="background:linear-gradient(135deg,#E3F9E5,#B2F2BB);border:1px solid #69DB7C;border-radius:10px;padding:14px 18px;margin-bottom:16px;display:flex;gap:12px;align-items:flex-start">
    <span style="font-size:20px">🧾</span>
    <div style="font-size:12.5px;color:#1A6B2F">
      Tax templates define CGST/SGST (intra-state) or IGST (inter-state) rates applied to invoices and bills.
      Assign a template to each item via <b>Inventory → Items → Default Tax Template</b>.
      The standard GST slabs (5%, 12%, 18%, 28%) are seeded automatically on setup.
    </div>
  </div>

  <!-- ── Filter bar ────────────────────────────────────────────────── -->
  <div style="display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap">
    <button
      v-for="f in FILTERS" :key="f.key"
      @click="activeFilter=f.key"
      :style="activeFilter===f.key
        ? 'background:#1971C2;color:#fff;border-color:#1971C2'
        : 'background:#fff;color:#495057;border-color:#dee2e6'"
      style="padding:5px 14px;border-radius:20px;border:1px solid;font-size:12.5px;font-weight:600;cursor:pointer"
    >{{ f.label }}</button>
    <input
      v-model="search" placeholder="Search…"
      style="margin-left:auto;padding:5px 12px;border:1px solid #dee2e6;border-radius:20px;font-size:13px;min-width:160px"
    />
  </div>

  <!-- ── Loading / empty ───────────────────────────────────────────── -->
  <div v-if="loading" style="padding:60px;text-align:center;color:#868e96">Loading…</div>

  <div v-else-if="!filtered.length" style="padding:60px;text-align:center;color:#868e96;background:#fff;border:1px dashed #e4e8f0;border-radius:12px">
    <div style="font-size:36px;margin-bottom:10px">🧾</div>
    <div style="font-size:14px;font-weight:600;margin-bottom:4px">No tax templates found</div>
    <div style="font-size:12.5px">Create GST templates for CGST+SGST (intra-state) or IGST (inter-state)</div>
    <button class="nim-btn nim-btn-primary" :disabled="!$canCreate('taxes')" :title="!$canCreate('taxes') ? 'Read-only access' : ''" @click="openAdd" style="margin-top:16px">Create Template</button>
  </div>

  <!-- ── Template cards ────────────────────────────────────────────── -->
  <div v-else style="display:grid;gap:10px">
    <div
      v-for="t in filtered" :key="t.name"
      style="background:#fff;border:1px solid #e4e8f0;border-radius:12px;padding:18px 20px"
      :style="t.disabled ? 'opacity:0.55' : ''"
    >
      <!-- Card header row -->
      <div style="display:flex;align-items:center;gap:14px">
        <div :style="'width:46px;height:46px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;background:'+typeMeta(t).bg">
          {{ typeMeta(t).emoji }}
        </div>
        <div style="flex:1;min-width:0">
          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
            <span style="font-size:13.5px;font-weight:700;color:#1a1a2e">{{ t.template_name }}</span>
            <span v-if="t.is_default" style="background:#FFF3BF;color:#E67700;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700">DEFAULT</span>
            <span v-if="t.disabled" style="background:#F8D7DA;color:#842029;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700">DISABLED</span>
          </div>
          <div style="font-size:12px;color:#868e96;margin-top:3px">
            {{ t.tax_type }}
            <template v-if="t.company"> · {{ t.company }}</template>
          </div>
          <!-- Tax row chips -->
          <div v-if="t.taxes && t.taxes.length" style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px">
            <span
              v-for="(row, idx) in t.taxes" :key="idx"
              :style="'background:'+taxChipColor(row.tax_type).bg+';color:'+taxChipColor(row.tax_type).c+';padding:3px 10px;border-radius:12px;font-size:11.5px;font-weight:600'"
            >{{ row.tax_type }} {{ row.rate }}%</span>
          </div>
        </div>
        <div style="display:flex;gap:8px;align-items:center;flex-shrink:0">
          <span :style="'background:'+typeMeta(t).bg+';color:'+typeMeta(t).c+';padding:3px 10px;border-radius:20px;font-size:11.5px;font-weight:600'">
            {{ totalRate(t) }}% total
          </span>
          <button class="nim-btn nim-btn-ghost" :disabled="!$canEdit('taxes')" @click="openEdit(t)" style="padding:5px 10px;font-size:12px">
            <span v-html="icon('edit',12)" style="vertical-align:-2px;margin-right:3px"/>Edit
          </button>
          <button
            class="nim-btn"
            :disabled="!$canDelete('taxes')"
            :title="!$canDelete('taxes') ? 'Not permitted' : ''"
            @click="delTarget=t.name;showDel=true"
            style="padding:5px 10px;font-size:12px;color:#c92a2a;border-color:#ffc9c9;background:#fff5f5"
          ><span v-html="icon('trash',12)" style="vertical-align:-2px"/></button>
        </div>
      </div>
    </div>
  </div>

  <!-- ════════════════════════════════════════════════════════════════ -->
  <!-- Add / Edit Drawer                                               -->
  <!-- ════════════════════════════════════════════════════════════════ -->
  <Teleport to="body">
    <div v-if="showDrawer" class="nim-overlay" @click.self="showDrawer=false">
      <div class="nim-dialog" style="width:580px;max-height:90vh;display:flex;flex-direction:column">
        <div class="nim-header">
          <span style="font-size:15px;font-weight:700">
            {{ drawerMode==='add' ? 'New Tax Template' : 'Edit Tax Template' }}
          </span>
          <button class="nim-btn nim-btn-ghost" @click="showDrawer=false">
            <span v-html="icon('x',14)"/>
          </button>
        </div>

        <div class="nim-body" style="flex:1;overflow-y:auto;display:grid;gap:14px">

          <!-- Template Name -->
          <div class="nim-field">
            <label class="nim-label">Template Name <span style="color:#c92a2a">*</span></label>
            <input class="nim-input" v-model="form.template_name"
              :readonly="drawerMode==='edit'"
              :style="drawerMode==='edit'?'background:#f8f9fc;color:#868e96':''"
              placeholder="e.g. GST 18% (Intra-State)"/>
          </div>

          <!-- Tax Type + Is Default row -->
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
            <div class="nim-field">
              <label class="nim-label">Tax Type</label>
              <select class="nim-input" v-model="form.tax_type">
                <option value="GST">GST</option>
                <option value="VAT">VAT</option>
                <option value="Custom">Custom</option>
              </select>
            </div>
            <div class="nim-field" style="display:flex;flex-direction:column;justify-content:flex-end">
              <label style="display:flex;align-items:center;gap:8px;cursor:pointer;font-size:13px;color:#495057;padding:10px 0 4px">
                <input type="checkbox" v-model="form.is_default" :true-value="1" :false-value="0"/>
                Set as Default Template
              </label>
              <label style="display:flex;align-items:center;gap:8px;cursor:pointer;font-size:13px;color:#495057">
                <input type="checkbox" v-model="form.disabled" :true-value="1" :false-value="0"/>
                Disabled
              </label>
            </div>
          </div>

          <!-- Company (optional) -->
          <div class="nim-field">
            <label class="nim-label">Company <span style="font-size:11px;color:#868e96">(leave blank for all companies)</span></label>
            <input class="nim-input" v-model="form.company" placeholder="Optional — restrict to one company"/>
          </div>

          <!-- ── Tax Rows ──────────────────────────────────────────── -->
          <div>
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
              <label class="nim-label" style="margin:0">Tax Rows</label>
              <div style="display:flex;gap:6px">
                <button class="nim-btn nim-btn-ghost" :disabled="!(drawerMode==='add' ? $canCreate('taxes') : $canEdit('taxes'))" @click="addRow('CGST')" style="padding:3px 10px;font-size:12px">+ CGST</button>
                <button class="nim-btn nim-btn-ghost" :disabled="!(drawerMode==='add' ? $canCreate('taxes') : $canEdit('taxes'))" @click="addRow('SGST')" style="padding:3px 10px;font-size:12px">+ SGST</button>
                <button class="nim-btn nim-btn-ghost" :disabled="!(drawerMode==='add' ? $canCreate('taxes') : $canEdit('taxes'))" @click="addRow('IGST')" style="padding:3px 10px;font-size:12px">+ IGST</button>
                <button class="nim-btn nim-btn-ghost" :disabled="!(drawerMode==='add' ? $canCreate('taxes') : $canEdit('taxes'))" @click="addRow('Cess')" style="padding:3px 10px;font-size:12px">+ Cess</button>
                <button class="nim-btn nim-btn-ghost" :disabled="!(drawerMode==='add' ? $canCreate('taxes') : $canEdit('taxes'))" @click="addRow('Other')" style="padding:3px 10px;font-size:12px">+ Other</button>
              </div>
            </div>

            <!-- Quick-fill buttons -->
            <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px">
              <span style="font-size:11.5px;color:#868e96;align-self:center">Quick fill:</span>
              <button v-for="q in QUICK_FILLS" :key="q.label"
                class="nim-btn nim-btn-ghost"
                :disabled="!(drawerMode==='add' ? $canCreate('taxes') : $canEdit('taxes'))"
                @click="applyQuickFill(q)"
                style="padding:2px 10px;font-size:11.5px;border-radius:20px"
              >{{ q.label }}</button>
            </div>

            <div v-if="!form.taxes.length" style="padding:16px;text-align:center;background:#f8f9fc;border:1px dashed #dee2e6;border-radius:8px;font-size:12.5px;color:#868e96">
              Use the buttons above to add tax rows (e.g. CGST + SGST for intra-state, IGST for inter-state)
            </div>

            <div v-else style="display:grid;gap:8px">
              <div
                v-for="(row, idx) in form.taxes" :key="idx"
                style="display:grid;grid-template-columns:110px 80px 1fr auto;gap:8px;align-items:center;background:#f8f9fc;border:1px solid #e4e8f0;border-radius:8px;padding:10px 12px"
              >
                <select class="nim-input" v-model="row.tax_type" style="padding:6px 8px;font-size:12.5px">
                  <option>CGST</option>
                  <option>SGST</option>
                  <option>IGST</option>
                  <option>Cess</option>
                  <option>Other</option>
                </select>
                <div style="position:relative">
                  <input class="nim-input" type="number" v-model.number="row.rate" min="0" max="100" step="0.25"
                    style="padding:6px 24px 6px 8px;font-size:12.5px"/>
                  <span style="position:absolute;right:8px;top:50%;transform:translateY(-50%);font-size:12px;color:#868e96">%</span>
                </div>
                <input class="nim-input" v-model="row.account_head" placeholder="Account Head (optional)"
                  style="padding:6px 8px;font-size:12px"/>
                <button @click="form.taxes.splice(idx,1)"
                  :disabled="!(drawerMode==='add' ? $canCreate('taxes') : $canEdit('taxes'))"
                  style="width:28px;height:28px;border-radius:6px;border:1px solid #ffc9c9;background:#fff5f5;color:#c92a2a;cursor:pointer;display:flex;align-items:center;justify-content:center"
                >
                  <span v-html="icon('x',11)"/>
                </button>
              </div>
            </div>

            <!-- Total preview -->
            <div v-if="form.taxes.length" style="margin-top:10px;background:#E3F9E5;border:1px solid #8CE99A;border-radius:8px;padding:10px 14px;font-size:12.5px;color:#2F9E44;display:flex;gap:16px;flex-wrap:wrap">
              <span><b>Total Rate:</b> {{ formTotalRate }}%</span>
              <span v-for="row in form.taxes" :key="row.tax_type+row.rate">
                {{ row.tax_type }}: {{ row.rate }}%
              </span>
            </div>
          </div>

        </div><!-- /nim-body -->

        <div class="nim-footer">
          <button class="nim-btn nim-btn-ghost" @click="showDrawer=false">Cancel</button>
          <button class="nim-btn nim-btn-primary" @click="save" :disabled="saving || !(drawerMode==='add' ? $canCreate('taxes') : $canEdit('taxes'))">
            {{ saving ? 'Saving…' : 'Save Template' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Delete confirm -->
    <div v-if="showDel" class="nim-overlay" @click.self="showDel=false">
      <div class="nim-dialog" style="width:400px">
        <div class="nim-header"><span style="font-weight:700">Delete Tax Template?</span></div>
        <div class="nim-body">
          <p style="font-size:13.5px;color:#4a5568">
            Delete "<b>{{ delTarget }}</b>"? Items and transactions referencing this template
            will not be affected, but it will no longer be available for new documents.
          </p>
        </div>
        <div class="nim-footer">
          <button class="nim-btn nim-btn-ghost" @click="showDel=false">Cancel</button>
          <button class="nim-btn" style="background:#c92a2a;color:#fff;border-color:#c92a2a" :disabled="!$canDelete('taxes')" @click="confirmDel">
            Delete
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { apiGET, apiPOST } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";

const { toast } = useToast();

// ── State ──────────────────────────────────────────────────────────────────
const list        = ref([]);
const loading     = ref(false);
const saving      = ref(false);
const showDrawer  = ref(false);
const drawerMode  = ref("add");
const showDel     = ref(false);
const delTarget   = ref(null);
const activeFilter = ref("all");
const search      = ref("");

const BLANK_FORM = () => ({
  template_name: "",
  tax_type: "GST",
  company: "",
  is_default: 0,
  disabled: 0,
  taxes: [],
});
const form = reactive(BLANK_FORM());

// ── Filters ─────────────────────────────────────────────────────────────────
const FILTERS = [
  { key: "all",    label: "All" },
  { key: "intra",  label: "Intra-State (CGST+SGST)" },
  { key: "inter",  label: "Inter-State (IGST)" },
  { key: "active", label: "Active" },
];

const filtered = computed(() => {
  let rows = list.value;
  if (activeFilter.value === "intra")  rows = rows.filter(t => t.taxes.some(r => r.tax_type === "CGST"));
  if (activeFilter.value === "inter")  rows = rows.filter(t => t.taxes.some(r => r.tax_type === "IGST") && !t.taxes.some(r => r.tax_type === "CGST"));
  if (activeFilter.value === "active") rows = rows.filter(t => !t.disabled);
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    rows = rows.filter(t => t.template_name.toLowerCase().includes(q) || (t.tax_type||"").toLowerCase().includes(q));
  }
  return rows;
});

// ── Quick fill presets ──────────────────────────────────────────────────────
const QUICK_FILLS = [
  { label: "GST 5% Intra",  rows: [{ tax_type:"CGST", rate:2.5, account_head:"CGST Payable", description:"" }, { tax_type:"SGST", rate:2.5, account_head:"SGST Payable", description:"" }] },
  { label: "GST 12% Intra", rows: [{ tax_type:"CGST", rate:6,   account_head:"CGST Payable", description:"" }, { tax_type:"SGST", rate:6,   account_head:"SGST Payable", description:"" }] },
  { label: "GST 18% Intra", rows: [{ tax_type:"CGST", rate:9,   account_head:"CGST Payable", description:"" }, { tax_type:"SGST", rate:9,   account_head:"SGST Payable", description:"" }] },
  { label: "GST 28% Intra", rows: [{ tax_type:"CGST", rate:14,  account_head:"CGST Payable", description:"" }, { tax_type:"SGST", rate:14,  account_head:"SGST Payable", description:"" }] },
  { label: "IGST 5%",       rows: [{ tax_type:"IGST", rate:5,   account_head:"IGST Payable", description:"" }] },
  { label: "IGST 12%",      rows: [{ tax_type:"IGST", rate:12,  account_head:"IGST Payable", description:"" }] },
  { label: "IGST 18%",      rows: [{ tax_type:"IGST", rate:18,  account_head:"IGST Payable", description:"" }] },
  { label: "IGST 28%",      rows: [{ tax_type:"IGST", rate:28,  account_head:"IGST Payable", description:"" }] },
];

function applyQuickFill(q) {
  form.taxes = q.rows.map(r => ({ ...r }));
}

// ── Helpers ─────────────────────────────────────────────────────────────────
function totalRate(t) {
  return (t.taxes || []).reduce((s, r) => s + parseFloat(r.rate || 0), 0);
}

const formTotalRate = computed(() =>
  form.taxes.reduce((s, r) => s + parseFloat(r.rate || 0), 0)
);

const TYPE_META = {
  GST:    { c: "#2F9E44", bg: "#E3F9E5", emoji: "🧾" },
  VAT:    { c: "#1971C2", bg: "#E7F5FF", emoji: "📋" },
  Custom: { c: "#6741D9", bg: "#F3F0FF", emoji: "⚙️" },
};
function typeMeta(t) { return TYPE_META[t.tax_type] || TYPE_META.GST; }

const TAX_CHIP = {
  CGST:  { c: "#1971C2", bg: "#E7F5FF" },
  SGST:  { c: "#2F9E44", bg: "#E3F9E5" },
  IGST:  { c: "#E67700", bg: "#FFF3BF" },
  Cess:  { c: "#6741D9", bg: "#F3F0FF" },
  Other: { c: "#495057", bg: "#F1F3F5" },
};
function taxChipColor(type) { return TAX_CHIP[type] || TAX_CHIP.Other; }

// ── Data ops ────────────────────────────────────────────────────────────────
async function load() {
  loading.value = true;
  try {
    list.value = await apiGET("zoho_books_clone.api.admin.get_tax_templates") || [];
  } catch (e) { toast("Could not load tax templates: " + e.message, "error"); }
  loading.value = false;
}

function openAdd() {
  drawerMode.value = "add";
  Object.assign(form, BLANK_FORM());
  showDrawer.value = true;
}

function openEdit(t) {
  drawerMode.value = "edit";
  Object.assign(form, {
    template_name: t.template_name,
    tax_type:      t.tax_type || "GST",
    company:       t.company || "",
    is_default:    t.is_default ? 1 : 0,
    disabled:      t.disabled  ? 1 : 0,
    taxes: (t.taxes || []).map(r => ({ ...r })),
  });
  showDrawer.value = true;
}

function addRow(type) {
  form.taxes.push({ tax_type: type, rate: 0, account_head: "", description: "" });
}

async function save() {
  if (!form.template_name.trim()) return toast("Template name is required", "error");
  saving.value = true;
  try {
    await apiPOST("zoho_books_clone.api.admin.save_tax_template", {
      template_name: form.template_name,
      tax_type:      form.tax_type,
      company:       form.company,
      is_default:    form.is_default,
      disabled:      form.disabled,
      taxes:         JSON.stringify(form.taxes),
    });
    toast(drawerMode.value === "add" ? "Tax template created" : "Tax template updated");
    showDrawer.value = false;
    load();
  } catch (e) { toast(e.message || "Save failed", "error"); }
  saving.value = false;
}

async function confirmDel() {
  try {
    await apiPOST("zoho_books_clone.api.admin.delete_tax_template", { name: delTarget.value });
    toast("Tax template deleted");
    showDel.value = false;
    load();
  } catch (e) { toast(e.message, "error"); }
}

onMounted(load);
</script>