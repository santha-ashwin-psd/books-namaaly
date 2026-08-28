<template>
  <Teleport to="body">
    <div v-if="state.open" class="qcd-backdrop" @mousedown.self="onCancel">
      <div class="qcd-panel">

        <div class="qcd-header">
          <div>
            <div class="qcd-title">Create New {{ LABELS[state.doctype] || state.doctype }}</div>
            <div class="qcd-subtitle">Fill in the details below — the record will be auto-selected after saving</div>
          </div>
          <button class="qcd-close" @click="onCancel" title="Close">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>

        <div class="qcd-body">

          <!-- ── Customer ─────────────────────────────────────────────── -->
          <template v-if="state.doctype === 'Customer'">
            <div class="qcd-section">Contact Details</div>
            <div class="qcd-grid">
              <div class="qcd-field qcd-full">
                <label class="qcd-lbl">Customer Name <span class="qcd-req">*</span></label>
                <input v-model="form.customer_name" class="qcd-input" placeholder="Full name or business name" autofocus />
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">Customer Type</label>
                <select v-model="form.customer_type" class="qcd-input">
                  <option value="Company">Company</option>
                  <option value="Individual">Individual</option>
                </select>
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">GST Treatment</label>
                <select v-model="form.gst_treatment" class="qcd-input">
                  <option value="Registered Business">Registered Business</option>
                  <option value="Unregistered Business">Unregistered Business</option>
                  <option value="Consumer">Consumer</option>
                  <option value="Overseas">Overseas</option>
                </select>
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">Email</label>
                <input v-model="form.email_id" type="email" class="qcd-input" placeholder="contact@example.com" />
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">Mobile</label>
                <input v-model="form.mobile_no" type="tel" class="qcd-input" placeholder="9876543210" />
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">Tax ID / GSTIN</label>
                <input v-model="form.tax_id" class="qcd-input" placeholder="27AAPFU0939F1ZV" @input="form.tax_id = form.tax_id.toUpperCase()" />
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">Country</label>
                <select v-model="form.country" class="qcd-input" @change="form.state = ''">
                  <option value="">— Select Country —</option>
                  <option v-for="c in COUNTRIES" :key="c" :value="c">{{ c }}</option>
                </select>
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">State</label>
                <select v-if="statesFor(form.country).length" v-model="form.state" class="qcd-input">
                  <option value="">— Select State —</option>
                  <option v-for="s in statesFor(form.country)" :key="s" :value="s">{{ s }}</option>
                </select>
                <input v-else v-model="form.state" class="qcd-input" placeholder="State" />
              </div>
              <div>
              <div class="qcd-field">
              <label class="qcd-lbl">Payment Terms</label>
              <select v-model="form.payment_terms" class="qcd-input" @change="applyPaymentTerms">
                <option value="">— Select Payment Terms —</option>
                <option v-for="t in PAYMENT_TERMS" :key="t" :value="t">{{ t }}</option>
              </select>
              </div>
            </div>
            </div>
          </template>

          <!-- ── Supplier / Vendor ───────────────────────────────────── -->
          <template v-else-if="state.doctype === 'Supplier'">
            <div class="qcd-section">Vendor Details</div>
            <div class="qcd-grid">
              <div class="qcd-field qcd-full">
                <label class="qcd-lbl">Supplier Name <span class="qcd-req">*</span></label>
                <input v-model="form.supplier_name" class="qcd-input" placeholder="Vendor / company name" autofocus />
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">Supplier Type</label>
                <select v-model="form.supplier_type" class="qcd-input">
                  <option value="Company">Company</option>
                  <option value="Individual">Individual</option>
                </select>
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">Email</label>
                <input v-model="form.email_id" type="email" class="qcd-input" placeholder="vendor@example.com" />
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">Mobile</label>
                <input v-model="form.mobile_no" type="tel" class="qcd-input" placeholder="9876543210" />
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">Tax ID / GSTIN</label>
                <input v-model="form.tax_id" class="qcd-input" placeholder="27AAPFU0939F1ZV" @input="form.tax_id = form.tax_id.toUpperCase()" />
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">Country</label>
                <select v-model="form.country" class="qcd-input" @change="form.state = ''">
                  <option value="">— Select Country —</option>
                  <option v-for="c in COUNTRIES" :key="c" :value="c">{{ c }}</option>
                </select>
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">State</label>
                <select v-if="statesFor(form.country).length" v-model="form.state" class="qcd-input">
                  <option value="">— Select State —</option>
                  <option v-for="s in statesFor(form.country)" :key="s" :value="s">{{ s }}</option>
                </select>
                <input v-else v-model="form.state" class="qcd-input" placeholder="State" />
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">Payment Terms</label>
                <input v-model="form.payment_terms" class="qcd-input" placeholder="e.g. Net 30" />
              </div>
            </div>
          </template>

          <!-- ── Item ────────────────────────────────────────────────── -->
          <template v-else-if="state.doctype === 'Item'">
            <div class="qcd-section">Item Details</div>
            <div class="qcd-grid">
              <div class="qcd-field qcd-full">
                <label class="qcd-lbl">Item Name <span class="qcd-req">*</span></label>
                <input v-model="form.item_name" class="qcd-input" placeholder="Product or service name" autofocus />
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">Item Code</label>
                <input v-model="form.item_code" class="qcd-input" placeholder="Auto from name if blank" />
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">Item Group</label>
                <input v-model="form.item_group" class="qcd-input" placeholder="All Item Groups" />
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">Item Type</label>
                <select v-model="form.item_type" class="qcd-input">
                  <option value="Product">Product</option>
                  <option value="Service">Service</option>
                </select>
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">Standard Rate (OMR)</label>
                <input v-model.number="form.standard_rate" type="number" min="0" step="0.01" class="qcd-input" placeholder="0.00" />
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">Unit of Measure</label>
                <select v-model="form.stock_uom" class="qcd-input">
                  <option value="">— Select UOM —</option>
                  <option v-for="u in uomList" :key="u" :value="u">{{u}}</option>
                </select>
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">HSN / SAC Code</label>
                <input v-model="form.hsn_code" class="qcd-input" placeholder="HSN or SAC code" />
              </div>
            </div>
          </template>

          <!-- ── Warehouse ────────────────────────────────────────────── -->
          <template v-else-if="state.doctype === 'Warehouse'">
            <div class="qcd-section">Warehouse Details</div>
            <div class="qcd-grid">
              <div class="qcd-field qcd-full">
                <label class="qcd-lbl">Warehouse Name <span class="qcd-req">*</span></label>
                <input v-model="form.warehouse_name" class="qcd-input" placeholder="e.g. Main Store, Finished Goods" autofocus />
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">Warehouse Type</label>
                <select v-model="form.warehouse_type" class="qcd-input">
                  <option value="">— Select Type —</option>
                  <option value="Stores">Stores</option>
                  <option value="Work In Progress">Work In Progress</option>
                  <option value="Finished Goods">Finished Goods</option>
                  <option value="Rejected">Rejected</option>
                  <option value="Scrap">Scrap</option>
                </select>
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">Parent Warehouse</label>
                <select v-model="form.parent_warehouse" class="qcd-input">
                  <option value="">— Top level —</option>
                  <option v-for="w in parentWarehouseList" :key="w" :value="w">{{ w }}</option>
                </select>
              </div>
              <div class="qcd-field qcd-full">
                <label class="qcd-lbl">Address (optional)</label>
                <input v-model="form.address_line_1" class="qcd-input" placeholder="Street / building" />
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">City</label>
                <input v-model="form.city" class="qcd-input" placeholder="City" />
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">PIN Code</label>
                <input v-model="form.pin" class="qcd-input" placeholder="6-digit PIN" maxlength="6" />
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">Country</label>
                <select v-model="form.country" class="qcd-input" @change="form.state = ''">
                  <option value="">— Select Country —</option>
                  <option v-for="c in COUNTRIES" :key="c" :value="c">{{ c }}</option>
                </select>
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">State</label>
                <select v-if="statesFor(form.country).length" v-model="form.state" class="qcd-input">
                  <option value="">— Select State —</option>
                  <option v-for="s in statesFor(form.country)" :key="s" :value="s">{{ s }}</option>
                </select>
                <input v-else v-model="form.state" class="qcd-input" placeholder="State" />
              </div>
            </div>
          </template>

          <!-- ── Account ────────────────────────────────────────────── -->
          <template v-else-if="state.doctype === 'Account'">
            <div class="qcd-section">Account Details</div>
            <div class="qcd-grid">
              <div class="qcd-field qcd-full">
                <label class="qcd-lbl">Account Name <span class="qcd-req">*</span></label>
                <input v-model="form.account_name" class="qcd-input" placeholder="e.g. Sales Revenue, Office Supplies" autofocus />
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">Account Type</label>
                <select v-model="form.account_type" class="qcd-input">
                  <option value="">— Select Type —</option>
                  <option value="Income Account">Income Account</option>
                  <option value="Expense Account">Expense Account</option>
                  <option value="Cost of Goods Sold">Cost of Goods Sold</option>
                  <option value="Fixed Asset">Fixed Asset</option>
                  <option value="Accumulated Depreciation">Accumulated Depreciation</option>
                  <option value="Depreciation">Depreciation</option>
                  <option value="Current Asset">Current Asset</option>
                  <option value="Current Liability">Current Liability</option>
                  <option value="Equity">Equity</option>
                  <option value="Cash">Cash</option>
                  <option value="Bank">Bank</option>
                  <option value="Receivable">Receivable</option>
                  <option value="Payable">Payable</option>
                  <option value="Tax">Tax</option>
                </select>
              </div>
              <div class="qcd-field">
                <label class="qcd-lbl">Parent Account <span class="qcd-req">*</span></label>
                <select v-model="form.parent_account" class="qcd-input">
                  <option value="">— Select Parent —</option>
                  <option v-for="a in parentAccountList" :key="a" :value="a">{{ a }}</option>
                </select>
              </div>
              <div class="qcd-field qcd-full">
                <label class="qcd-lbl">Account Number</label>
                <input v-model="form.account_number" class="qcd-input" placeholder="Optional account code" />
              </div>
            </div>
          </template>

          <!-- ── Fallback ─────────────────────────────────────────────── -->
          <template v-else>
            <div class="qcd-grid">
              <div class="qcd-field qcd-full">
                <label class="qcd-lbl">Name <span class="qcd-req">*</span></label>
                <input v-model="form.name" class="qcd-input" :placeholder="state.doctype + ' name'" autofocus />
              </div>
            </div>
          </template>

        </div>

        <div class="qcd-footer">
          <button class="qcd-btn-cancel" @click="onCancel">Cancel</button>
          <button class="add-btn-draft" :disabled="saving" @click="onSave">
            {{ saving ? 'Saving…' : 'Create & Select' }}
          </button>
        </div>

      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { reactive, ref, watch, onMounted } from "vue";
import { apiSave, apiList, resolveCompany } from "../api/client.js";
import { useQuickCreate } from "../composables/useQuickCreate.js";
import { useToast } from "../composables/useToast.js";
import { COUNTRIES, statesFor } from "../composables/useCountryState.js";

const { state, complete, cancel } = useQuickCreate();
const { toast } = useToast();

const saving  = ref(false);
const form    = reactive({});
const uomList = ref([]);
const parentWarehouseList = ref([]);
const parentAccountList   = ref([]);
const PAYMENT_TERMS = ["Due on Receipt","Net 7","Net 15","Net 30","Net 45","Net 60","Net 90"];
const LABELS = { Customer: "Customer", Supplier: "Vendor / Supplier", Item: "Item", Warehouse: "Warehouse", Account: "Account" };

onMounted(async () => {
  try {
    const r = await apiList("UOM", { fields: ["name"], order: "name asc", limit: 200 });
    uomList.value = (r || []).map(x => x.name);
  } catch { uomList.value = ["Nos","Kg","Ltr","Mtr","Box","Pcs","Set","Dozen"]; }
  try {
    const r = await apiList("Warehouse", { fields: ["name"], filters: [["is_group","=",1],["disabled","=",0]], order: "name asc", limit: 100 });
    parentWarehouseList.value = (r || []).map(x => x.name);
  } catch { parentWarehouseList.value = []; }
  try {
    const r = await apiList("Account", { fields: ["name"], filters: [["is_group","=",1]], order: "name asc", limit: 300 });
    parentAccountList.value = (r || []).map(x => x.name);
  } catch { parentAccountList.value = []; }
});

watch(() => state.open, (open) => {
  if (!open) return;
  for (const k in form) delete form[k];

  if (state.doctype === "Customer") {
    Object.assign(form, {
      customer_name: state.prefill, customer_type: "Company",
      gst_treatment: "Registered Business",
      email_id: "", mobile_no: "", tax_id: "", country: "Oman", state: "", payment_terms: "",
    });
  } else if (state.doctype === "Supplier") {
    Object.assign(form, {
      supplier_name: state.prefill, supplier_type: "Company",
      email_id: "", mobile_no: "", tax_id: "", country: "Oman", state: "", payment_terms: "",
    });
  } else if (state.doctype === "Item") {
    Object.assign(form, {
      item_name: state.prefill, item_code: "",
      item_group: "All Item Groups", item_type: "Product",
      standard_rate: 0, stock_uom: "Nos", hsn_code: "",
    });
  } else if (state.doctype === "Warehouse") {
    Object.assign(form, {
      warehouse_name: state.prefill, warehouse_type: "Stores",
      parent_warehouse: "", address_line_1: "", city: "", state: "", pin: "", country: "Oman",
    });
  } else if (state.doctype === "Account") {
    Object.assign(form, {
      account_name: state.prefill, account_type: "", parent_account: "", account_number: "",
    });
  } else {
    form.name = state.prefill;
  }
});

function onCancel() {
  if (saving.value) return;
  cancel();
}

async function onSave() {
  if (state.doctype === "Customer" && !form.customer_name?.trim()) {
    toast("Customer Name is required", "error"); return;
  }
  if (state.doctype === "Supplier" && !form.supplier_name?.trim()) {
    toast("Supplier Name is required", "error"); return;
  }
  if (state.doctype === "Item" && !form.item_name?.trim()) {
    toast("Item Name is required", "error"); return;
  }
  if (state.doctype === "Warehouse" && !form.warehouse_name?.trim()) {
    toast("Warehouse Name is required", "error"); return;
  }
  if (state.doctype === "Account") {
    if (!form.account_name?.trim()) { toast("Account Name is required", "error"); return; }
    if (!form.parent_account?.trim()) { toast("Parent Account is required", "error"); return; }
  }
  if (!state.doctype && !form.name?.trim()) {
    toast("Name is required", "error"); return;
  }

  saving.value = true;
  try {
    const company = await resolveCompany();
    const payload = { doctype: state.doctype };
    for (const [k, v] of Object.entries(form)) {
      if (v !== "" && v !== null && v !== undefined) payload[k] = v;
    }
    if (company) {
      if (["Customer", "Supplier", "Item"].includes(state.doctype)) payload.books_company = company;
      if (["Warehouse", "Account"].includes(state.doctype)) payload.company = company;
    }

    const saved = await apiSave(payload);
    const savedName = saved?.name || saved;
    const label =
      state.doctype === "Customer"  ? (form.customer_name  || savedName) :
      state.doctype === "Supplier"  ? (form.supplier_name  || savedName) :
      state.doctype === "Item"      ? (form.item_name      || savedName) :
      state.doctype === "Warehouse" ? (form.warehouse_name || savedName) :
      state.doctype === "Account"   ? (form.account_name   || savedName) :
      savedName;

    toast(`${LABELS[state.doctype] || state.doctype} "${label}" created`, "success");
    complete({ name: savedName, label });
  } catch (e) {
    toast("Failed to create: " + (e?.message || String(e)), "error");
  } finally {
    saving.value = false;
  }
}
</script>

<style>
.qcd-backdrop {
  position: fixed; inset: 0;
  background: rgba(15, 23, 42, 0.50);
  z-index: 10000;
  display: flex;
  justify-content: flex-end;
  align-items: stretch;
}
.qcd-panel {
  width: 540px; max-width: 96vw;
  background: #fff;
  display: flex; flex-direction: column;
  box-shadow: -20px 0 60px rgba(0,0,0,.18);
  overflow: hidden;
  animation: qcd-slide-in .22s ease;
}
@keyframes qcd-slide-in {
  from { transform: translateX(100%); }
  to   { transform: translateX(0); }
}
.qcd-header {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 12px;
  padding: 18px 24px; flex-shrink: 0;
  background: linear-gradient(135deg, #1e3a5f 0%, #1a6ef7 100%);
}
.qcd-title    { color: #fff; font-size: 16px; font-weight: 700; }
.qcd-subtitle { color: rgba(255,255,255,.7); font-size: 12px; margin-top: 3px; }
.qcd-close {
  background: rgba(255,255,255,.15); border: none; cursor: pointer;
  width: 30px; height: 30px; border-radius: 8px; color: #fff;
  display: grid; place-items: center; flex-shrink: 0; transition: background .15s;
}
.qcd-close:hover { background: rgba(255,255,255,.28); }
.qcd-body {
  flex: 1; overflow-y: auto; padding: 20px 24px;
  display: flex; flex-direction: column; gap: 16px;
}
.qcd-section {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .06em; color: #6b7280;
  padding-bottom: 6px; border-bottom: 1px solid #f3f4f6;
}
.qcd-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.qcd-field { display: flex; flex-direction: column; gap: 4px; }
.qcd-full  { grid-column: 1 / -1; }
.qcd-lbl   { font-size: 12px; font-weight: 600; color: #374151; }
.qcd-req   { color: #ef4444; margin-left: 2px; }
.qcd-input {
  width: 100%; box-sizing: border-box;
  border: 1px solid #e5e7eb; border-radius: 6px;
  padding: 7px 10px; font-size: 13px; font-family: inherit;
  outline: none; background: #fff; color: #111827;
}
.qcd-input:focus { border-color: #2563eb; box-shadow: 0 0 0 2px rgba(37,99,235,.08); }
.qcd-footer {
  display: flex; align-items: center; justify-content: flex-end; gap: 8px;
  padding: 14px 24px; border-top: 1px solid #e5e7eb; flex-shrink: 0;
}
.qcd-btn-cancel {
  background: transparent; border: 1px solid #e5e7eb; border-radius: 8px;
  padding: 8px 16px; font: inherit; font-size: 13px; color: #374151; cursor: pointer;
}
.qcd-btn-cancel:hover { background: #f9fafb; }
.qcd-btn-save {
  background: #2563eb; color: #fff; border: none; border-radius: 8px;
  padding: 8px 20px; font: inherit; font-size: 13px; font-weight: 600; cursor: pointer;
}
.qcd-btn-save:hover:not(:disabled) { background: #1d4ed8; }
.qcd-btn-save:disabled { opacity: .5; cursor: not-allowed; }
@media (max-width: 600px) {
  .qcd-grid { grid-template-columns: 1fr; }
  .qcd-full  { grid-column: auto; }
}
</style>