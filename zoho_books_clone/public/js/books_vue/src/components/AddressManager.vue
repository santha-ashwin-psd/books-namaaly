<template>
  <div class="am-wrap">
    <!-- ── Billing Addresses ─────────────────────────────── -->
    <div class="am-section">
      <div class="am-section-header">
        <span class="am-section-title">Billing Addresses</span>
        <button v-if="!readonly" class="am-btn-add" @click="openNew('Billing')">+ Add</button>
      </div>
      <div v-if="!byType('Billing').length" class="am-empty">No billing address on file</div>
      <div v-for="addr in byType('Billing')" :key="addr.name || addr._tempId" class="am-card">
        <div class="am-card-body">
          <div v-if="addr.address_line1">{{ addr.address_line1 }}</div>
          <div v-if="addr.address_line2">{{ addr.address_line2 }}</div>
          <div>{{ [addr.city, addr.state, addr.pincode].filter(Boolean).join(', ') }}</div>
          <div v-if="addr.country">{{ addr.country }}</div>
          <div v-if="addr.phone" style="color:#6b7280;margin-top:2px;font-size:12px">{{ addr.phone }}</div>
        </div>
        <div v-if="!readonly" class="am-card-actions">
          <button class="am-act-btn" @click="openEdit(addr)">Edit</button>
          <button class="am-act-btn am-act-del" @click="confirmDelete(addr)">Delete</button>
        </div>
      </div>
    </div>

    <!-- ── Shipping Addresses ────────────────────────────── -->
    <div class="am-section">
      <div class="am-section-header">
        <span class="am-section-title">Shipping Addresses</span>
        <button v-if="!readonly && !sameAsBilling" class="am-btn-add" @click="openNew('Shipping')">+ Add</button>
      </div>
      <label class="am-same-label">
        <input type="checkbox" v-model="sameAsBilling" class="am-same-check" />
        Use same address as billing
      </label>
      <template v-if="!sameAsBilling">
        <div v-if="!byType('Shipping').length" class="am-empty">No shipping address on file</div>
        <div v-for="addr in byType('Shipping')" :key="addr.name || addr._tempId" class="am-card">
          <div class="am-card-body">
            <div v-if="addr.address_line1">{{ addr.address_line1 }}</div>
            <div v-if="addr.address_line2">{{ addr.address_line2 }}</div>
            <div>{{ [addr.city, addr.state, addr.pincode].filter(Boolean).join(', ') }}</div>
            <div v-if="addr.country">{{ addr.country }}</div>
            <div v-if="addr.phone" style="color:#6b7280;margin-top:2px;font-size:12px">{{ addr.phone }}</div>
          </div>
          <div v-if="!readonly" class="am-card-actions">
            <button class="am-act-btn" @click="openEdit(addr)">Edit</button>
            <button class="am-act-btn am-act-del" @click="confirmDelete(addr)">Delete</button>
          </div>
        </div>
      </template>
      <div v-else class="am-same-notice">Shipping address matches billing address</div>
    </div>

    <!-- ── Add / Edit form ───────────────────────────────── -->
    <div v-if="showForm && !readonly" class="am-form">
      <div class="am-form-header">
        {{ editingAddr ? 'Edit' : 'Add' }} Address
        <button class="am-form-close" @click="closeForm">✕</button>
      </div>
      <div class="am-form-grid">
        <div class="am-form-field am-span2">
          <label class="am-lbl">Address Type</label>
          <select v-model="form.address_type" class="am-input">
            <option>Billing</option>
            <option>Shipping</option>
          </select>
        </div>
        <div class="am-form-field am-span2">
          <label class="am-lbl">Address Line 1 <span class="am-req">*</span></label>
          <input v-model="form.address_line1" class="am-input" placeholder="Street, building no." />
        </div>
        <div class="am-form-field am-span2">
          <label class="am-lbl">Address Line 2</label>
          <input v-model="form.address_line2" class="am-input" placeholder="Area, landmark" />
        </div>
        <div class="am-form-field">
          <label class="am-lbl">City</label>
          <input v-model="form.city" class="am-input" placeholder="City" />
        </div>
        <div class="am-form-field">
          <label class="am-lbl">Country</label>
          <select v-model="form.country" class="am-input" @change="form.state = ''">
            <option value="">— Select Country —</option>
            <option v-for="c in COUNTRIES" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>
        <div class="am-form-field">
          <label class="am-lbl">State</label>
          <select v-if="statesFor(form.country).length" v-model="form.state" class="am-input">
            <option value="">— Select State —</option>
            <option v-for="s in statesFor(form.country)" :key="s" :value="s">{{ s }}</option>
          </select>
          <input v-else v-model="form.state" class="am-input" placeholder="State" />
        </div>
        <div class="am-form-field">
          <label class="am-lbl">Pincode</label>
          <input v-model="form.pincode" class="am-input" placeholder="Pincode" />
        </div>
        <div class="am-form-field am-span2">
          <label class="am-lbl">Phone</label>
          <input v-model="form.phone" class="am-input" placeholder="Phone number" type="tel" />
        </div>
      </div>
      <div class="am-form-footer">
        <button class="am-btn-cancel" @click="closeForm">Cancel</button>
        <button class="am-btn-save" :disabled="saving" @click="save">
          {{ saving ? 'Saving…' : 'Save Address' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from "vue";
import { apiList, apiSave, apiDelete } from "../api/client.js";
import { COUNTRIES, statesFor } from "../composables/useCountryState.js";

const props = defineProps({
  partyDoctype: { type: String, required: true },
  partyName:    { type: String, default: "" },
  readonly:     { type: Boolean, default: false },
  modelValue:   { type: Array, default: () => [] }, // pending addresses for add mode
});
const emit = defineEmits(["addressSaved", "addressDeleted", "update:modelValue"]);

const isPending = computed(() => !props.partyName);

const addresses    = ref([]);
const showForm     = ref(false);
const editingAddr  = ref(null);
const saving       = ref(false);
const sameAsBilling = ref(false);
let _tempCounter = 0;

const form = reactive({
  address_type: "Billing",
  address_line1: "", address_line2: "",
  city: "", state: "", pincode: "", country: "Oman", phone: "",
});

const byType = (type) => addresses.value.filter(a => a.address_type === type);

// Sync modelValue → local addresses in pending mode
watch(() => props.modelValue, (v) => {
  if (isPending.value) addresses.value = [...(v || [])];
}, { immediate: true });

// When partyName becomes available (edit mode), load from Frappe
watch(() => props.partyName, (v) => { if (v) loadAddresses(); });

async function loadAddresses() {
  if (!props.partyName) return;
  try {
    const r = await apiList("Address", {
      fields: ["name","address_title","address_type","address_line1","address_line2",
               "city","state","pincode","country","phone"],
      filters: [
        ["Dynamic Link","link_name","=",props.partyName],
        ["Dynamic Link","link_doctype","=",props.partyDoctype],
      ],
      order: "`tabAddress`.address_type asc, `tabAddress`.modified desc",
      limit: 50,
    });
    addresses.value = Array.isArray(r) ? r : [];
  } catch {
    addresses.value = [];
  }
}

function openNew(type) {
  editingAddr.value = null;
  Object.assign(form, { address_type: type, address_line1: "", address_line2: "",
                        city: "", state: "", pincode: "", country: "Oman", phone: "" });
  showForm.value = true;
}

function openEdit(addr) {
  editingAddr.value = addr;
  Object.assign(form, {
    address_type:  addr.address_type || "Billing",
    address_line1: addr.address_line1 || "",
    address_line2: addr.address_line2 || "",
    city:          addr.city || "",
    state:         addr.state || "",
    pincode:       addr.pincode || "",
    country:       addr.country || "Oman",
    phone:         addr.phone || "",
  });
  showForm.value = true;
}

function closeForm() {
  showForm.value = false;
  editingAddr.value = null;
}

async function save() {
  if (!form.address_line1.trim()) return;

  // Pending mode — store locally, emit update
  if (isPending.value) {
    const addr = {
      _tempId: editingAddr.value?._tempId || ("_t" + (++_tempCounter)),
      address_type:  form.address_type,
      address_line1: form.address_line1.trim(),
      address_line2: form.address_line2.trim(),
      city:    form.city.trim(),
      state:   form.state.trim(),
      pincode: form.pincode.trim(),
      country: form.country.trim() || "Oman",
      phone:   form.phone.trim(),
    };
    const updated = editingAddr.value
      ? addresses.value.map(a => a._tempId === addr._tempId ? addr : a)
      : [...addresses.value, addr];
    addresses.value = updated;
    emit("update:modelValue", updated);
    closeForm();
    return;
  }

  // Frappe mode — save to Address doctype
  saving.value = true;
  try {
    const doc = {
      doctype: "Address",
      address_title: `${props.partyName} - ${form.address_type}`,
      address_type:  form.address_type,
      address_line1: form.address_line1.trim(),
      address_line2: form.address_line2.trim(),
      city:     form.city.trim(),
      state:    form.state.trim(),
      pincode:  form.pincode.trim(),
      country:  form.country.trim() || "Oman",
      phone:    form.phone.trim(),
      links: [{ link_doctype: props.partyDoctype, link_name: props.partyName }],
    };
    if (editingAddr.value) doc.name = editingAddr.value.name;
    await apiSave(doc);
    await loadAddresses();
    closeForm();
    emit("addressSaved");
  } catch (e) {
    console.error("Address save failed:", e);
  } finally {
    saving.value = false;
  }
}

async function confirmDelete(addr) {
  if (!confirm(`Delete this ${addr.address_type} address?`)) return;

  // Pending mode
  if (isPending.value) {
    const updated = addresses.value.filter(a => a._tempId !== addr._tempId);
    addresses.value = updated;
    emit("update:modelValue", updated);
    return;
  }

  // Frappe mode
  try {
    await apiDelete("Address", addr.name);
    await loadAddresses();
    emit("addressDeleted", addr.name);
  } catch (e) {
    console.error("Address delete failed:", e);
  }
}

onMounted(() => { if (!isPending.value) loadAddresses(); });
</script>

<style scoped>
.am-wrap { font-family: Plus Jakarta Sans, Lato, system-ui, sans-serif; font-size: 13px; }
.am-section { margin-bottom: 20px; }
.am-section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.am-section-title { font-size: 12px; font-weight: 700; color: #374151; text-transform: uppercase; letter-spacing: .04em; }
.am-btn-add { background: none; border: 1px solid #3B5BDB; color: #3B5BDB; border-radius: 6px; padding: 4px 10px; font-size: 12px; font-weight: 600; cursor: pointer; font-family: inherit; transition: background .12s; }
.am-btn-add:hover { background: #eff1ff; }
.am-same-label { display: flex; align-items: center; gap: 7px; font-size: 12.5px; color: #374151; cursor: pointer; margin-bottom: 8px; }
.am-same-check { accent-color: #3B5BDB; }
.am-same-notice { font-size: 12.5px; color: #9ca3af; font-style: italic; padding: 4px 0; }
.am-empty { font-size: 12.5px; color: #9ca3af; font-style: italic; padding: 4px 0; }
.am-card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; display: flex; align-items: flex-start; justify-content: space-between; background: #fafafa; }
.am-card-body { line-height: 1.6; color: #374151; font-size: 12.5px; }
.am-card-actions { display: flex; gap: 6px; margin-left: 12px; flex-shrink: 0; }
.am-act-btn { background: none; border: 1px solid #e5e7eb; color: #6b7280; border-radius: 5px; padding: 3px 10px; font-size: 11.5px; cursor: pointer; font-family: inherit; transition: all .12s; }
.am-act-btn:hover { border-color: #3B5BDB; color: #3B5BDB; background: #eff1ff; }
.am-act-del:hover { border-color: #dc2626; color: #dc2626; background: #fef2f2; }
/* ── Form ── */
.am-form { border: 1px solid #e5e7eb; border-radius: 10px; padding: 16px; margin-top: 12px; background: #fff; }
.am-form-header { display: flex; align-items: center; justify-content: space-between; font-size: 13px; font-weight: 700; color: #111827; margin-bottom: 14px; }
.am-form-close { background: none; border: none; cursor: pointer; font-size: 15px; color: #6b7280; line-height: 1; }
.am-form-close:hover { color: #111827; }
.am-form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px; }
.am-form-field { display: flex; flex-direction: column; gap: 4px; }
.am-span2 { grid-column: span 2; }
.am-lbl { font-size: 11.5px; font-weight: 600; color: #374151; }
.am-req { color: #dc2626; }
.am-input { width: 100%; box-sizing: border-box; border: 1px solid #d1d5db; border-radius: 6px; padding: 7px 10px; font-size: 13px; font-family: inherit; outline: none; color: #111827; transition: border-color .12s; }
.am-input:focus { border-color: #3B5BDB; box-shadow: 0 0 0 3px #3B5BDB1a; }
.am-form-footer { display: flex; justify-content: flex-end; gap: 8px; }
.am-btn-cancel { background: none; border: 1px solid #d1d5db; border-radius: 7px; padding: 7px 16px; font-size: 13px; font-weight: 500; cursor: pointer; color: #374151; font-family: inherit; }
.am-btn-save { background: #3B5BDB; border: none; border-radius: 7px; padding: 7px 18px; font-size: 13px; font-weight: 600; color: #fff; cursor: pointer; font-family: inherit; transition: background .12s; }
.am-btn-save:hover:not(:disabled) { background: #2f4ab8; }
.am-btn-save:disabled { opacity: .55; cursor: default; }

@media (max-width: 768px) {
  .am-form-grid { grid-template-columns: 1fr !important; }
  .am-span2 { grid-column: span 1 !important; }
  .am-form-footer { flex-direction: row; }
  .am-btn-cancel, .am-btn-save { flex: 1; text-align: center; }
}
</style>