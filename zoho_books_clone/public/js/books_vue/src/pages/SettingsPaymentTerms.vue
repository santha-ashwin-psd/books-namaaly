<template>
<div class="cust-page">
  <div class="cust-toolbar">
    <div style="display:flex;align-items:center;gap:12px">
      <span style="font-size:18px;font-weight:700;color:#1a1a2e">Payment Terms</span>
      <span style="background:#FFF3BF;color:#E67700;padding:2px 10px;border-radius:20px;font-size:12px;font-weight:600">{{list.length}} terms</span>
    </div>
    <button class="nim-btn nim-btn-primary" :disabled="!$canWrite('admin')" :title="!$canWrite('admin') ? 'Read-only access' : ''" @click="openAdd"><span v-html="icon('plus',13)" style="vertical-align:-2px;margin-right:4px"/>New Term</button>
  </div>

  <div style="background:linear-gradient(135deg,#FFF9DB,#FFF3BF);border:1px solid #FFD43B;border-radius:10px;padding:14px 18px;margin-bottom:16px;display:flex;gap:12px;align-items:center">
    <span style="font-size:20px">💳</span>
    <div style="font-size:12.5px;color:#876800">Payment terms define <b>when</b> a payment is due. Once created here, they appear in the Payment Terms dropdown on Invoices and Purchase Bills and automatically set the due date.</div>
  </div>

  <div v-if="loading" style="padding:60px;text-align:center;color:#868e96">Loading…</div>

  <div v-else-if="!list.length" style="padding:60px;text-align:center;color:#868e96;background:#fff;border:1px dashed #e4e8f0;border-radius:12px">
    <div style="font-size:36px;margin-bottom:10px">💳</div>
    <div style="font-size:14px;font-weight:600;margin-bottom:4px">No payment terms yet</div>
    <div style="font-size:12.5px">Create payment terms like "Net 30", "Immediate" or "2/10 Net 30"</div>
    <button class="nim-btn nim-btn-primary" :disabled="!$canWrite('admin')" :title="!$canWrite('admin') ? 'Read-only access' : ''" @click="openAdd" style="margin-top:16px">Create Term</button>
  </div>

  <div v-else style="display:grid;gap:10px">
    <div v-for="t in list" :key="t.name" style="background:#fff;border:1px solid #e4e8f0;border-radius:12px;padding:18px 20px;display:flex;align-items:center;gap:14px">
      <div :style="'width:46px;height:46px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;background:'+termMeta(t).bg">💳</div>
      <div style="flex:1;min-width:0">
        <div style="font-size:13.5px;font-weight:700;color:#1a1a2e">{{t.name}}</div>
        <div style="font-size:12px;color:#868e96;margin-top:2px">{{summaryLabel(t)}}</div>
        <div v-if="t.description" style="font-size:11.5px;color:#adb5bd;margin-top:2px">{{t.description}}</div>
      </div>
      <div style="display:flex;align-items:center;gap:8px">
        <span :style="'background:'+termMeta(t).bg+';color:'+termMeta(t).c+';padding:3px 10px;border-radius:20px;font-size:11.5px;font-weight:600'">{{t.payment_days}} days</span>
        <button class="nim-btn nim-btn-ghost" @click="openEdit(t)" style="padding:5px 10px;font-size:12px"><span v-html="icon('edit',12)" style="vertical-align:-2px;margin-right:3px"/>Edit</button>
        <button class="nim-btn" @click="delTarget=t.name;showDel=true" style="padding:5px 10px;font-size:12px;color:#c92a2a;border-color:#ffc9c9;background:#fff5f5"><span v-html="icon('trash',12)" style="vertical-align:-2px"/></button>
      </div>
    </div>
  </div>

  <Teleport to="body">
    <div v-if="showDrawer" class="nim-overlay" @click.self="showDrawer=false">
      <div class="nim-dialog" style="width:520px">
        <div class="nim-header">
          <span style="font-size:15px;font-weight:700">{{drawerMode==='add'?'New Payment Term':'Edit Payment Term'}}</span>
          <button class="nim-btn nim-btn-ghost" @click="showDrawer=false"><span v-html="icon('x',14)"/></button>
        </div>
        <div class="nim-body" style="display:grid;gap:14px">
          <div class="nim-field">
            <label class="nim-label">Term Name <span style="color:#c92a2a">*</span></label>
            <input class="nim-input" v-model="form.name" :readonly="drawerMode==='edit'" placeholder="e.g. Net 30, Immediate, 2/10 Net 30" :style="drawerMode==='edit'?'background:#f8f9fc;color:#868e96':''"/>
          </div>
          <div class="nim-field">
            <label class="nim-label">Due Date Based On</label>
            <select class="nim-input" v-model="form.due_date_based_on">
              <option v-for="o in DUE_OPTIONS" :key="o" :value="o">{{o}}</option>
            </select>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
            <div class="nim-field">
              <label class="nim-label">Payment Days</label>
              <input class="nim-input" type="number" v-model="form.payment_days" min="0"/>
            </div>
            <div class="nim-field">
              <label class="nim-label">Discount Days (early pay)</label>
              <input class="nim-input" type="number" v-model="form.discount_days" min="0"/>
            </div>
          </div>
          <div class="nim-field">
            <label class="nim-label">Early Payment Discount %</label>
            <input class="nim-input" type="number" v-model="form.discount_percentage" min="0" max="100" step="0.01" placeholder="0"/>
            <div style="font-size:11px;color:#868e96;margin-top:3px">Leave 0 for no early-pay discount</div>
          </div>
          <div class="nim-field">
            <label class="nim-label">Description</label>
            <input class="nim-input" v-model="form.description" placeholder="e.g. Payment due 30 days from invoice date"/>
          </div>
          <div v-if="form.name" style="background:#f0f9f4;border:1px solid #8CE99A;border-radius:8px;padding:12px;font-size:12.5px;color:#2F9E44">
            <b>Preview:</b> {{summaryLabel(form)}}
          </div>
        </div>
        <div class="nim-footer">
          <button class="nim-btn nim-btn-ghost" @click="showDrawer=false">Cancel</button>
          <button class="nim-btn nim-btn-primary" @click="save" :disabled="saving">{{saving?'Saving…':'Save Term'}}</button>
        </div>
      </div>
    </div>

    <div v-if="showDel" class="nim-overlay" @click.self="showDel=false">
      <div class="nim-dialog" style="width:400px">
        <div class="nim-header"><span style="font-weight:700">Delete Payment Term?</span></div>
        <div class="nim-body"><p style="font-size:13.5px;color:#4a5568">Delete "<b>{{delTarget}}</b>"? Any invoices using this term will not be affected but the term will no longer be available in new documents.</p></div>
        <div class="nim-footer">
          <button class="nim-btn nim-btn-ghost" @click="showDel=false">Cancel</button>
          <button class="nim-btn" style="background:#c92a2a;color:#fff;border-color:#c92a2a" @click="confirmDel">Delete</button>
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

const list      = ref([]);
const loading   = ref(false);
const saving    = ref(false);
const showDrawer = ref(false);
const drawerMode = ref("add");
const showDel    = ref(false);
const delTarget  = ref(null);
const form = reactive({
  name: "", due_date_based_on: "Day(s) after invoice date",
  payment_days: 0, discount_days: 0, discount_percentage: 0, description: "",
});

const DUE_OPTIONS = [
  "Day(s) after invoice date",
  "Day(s) after end of invoice month",
  "Month(s) after end of invoice month",
];

const TYPE_COLOR = {
  "Day(s) after invoice date":            { c: "#1971C2", bg: "#E7F5FF" },
  "Day(s) after end of invoice month":    { c: "#E67700", bg: "#FFF3BF" },
  "Month(s) after end of invoice month":  { c: "#2F9E44", bg: "#EBFBEE" },
};

function termMeta(t) { return TYPE_COLOR[t.due_date_based_on] || { c: "#868E96", bg: "#F8F9FA" }; }

function summaryLabel(t) {
  const base =
    t.due_date_based_on === "Day(s) after invoice date"
      ? `${t.payment_days} days from invoice`
      : t.due_date_based_on === "Day(s) after end of invoice month"
      ? `${t.payment_days} days after month-end`
      : `${t.payment_days} months after month-end`;
  return base + (t.discount_percentage > 0 ? ` · ${t.discount_percentage}% discount if paid within ${t.discount_days}d` : "");
}

async function load() {
  loading.value = true;
  try {
    list.value = await apiGET("zoho_books_clone.api.admin.get_payment_terms") || [];
  } catch (e) { toast("Could not load payment terms: " + e.message, "error"); }
  loading.value = false;
}

function openAdd() {
  drawerMode.value = "add";
  Object.assign(form, {
    name: "", due_date_based_on: "Day(s) after invoice date",
    payment_days: 30, discount_days: 0, discount_percentage: 0, description: "",
  });
  showDrawer.value = true;
}

function openEdit(t) {
  drawerMode.value = "edit";
  Object.assign(form, {
    name: t.name,
    due_date_based_on: t.due_date_based_on,
    payment_days: t.payment_days || 0,
    discount_days: t.discount_days || 0,
    discount_percentage: t.discount_percentage || 0,
    description: t.description || "",
  });
  showDrawer.value = true;
}

async function save() {
  if (!form.name.trim()) return toast("Term name is required", "error");
  saving.value = true;
  try {
    await apiPOST("zoho_books_clone.api.admin.save_payment_term", {
      name: form.name,
      due_date_based_on: form.due_date_based_on,
      payment_days: form.payment_days,
      discount_days: form.discount_days,
      discount_percentage: form.discount_percentage,
      description: form.description,
    });
    toast(drawerMode.value === "add" ? "Payment term created" : "Payment term updated");
    showDrawer.value = false;
    load();
  } catch (e) { toast(e.message, "error"); }
  saving.value = false;
}

async function confirmDel() {
  try {
    await apiPOST("zoho_books_clone.api.admin.delete_payment_term", { name: delTarget.value });
    toast("Payment term deleted");
    showDel.value = false;
    load();
  } catch (e) { toast(e.message, "error"); }
}

onMounted(load);
</script>
