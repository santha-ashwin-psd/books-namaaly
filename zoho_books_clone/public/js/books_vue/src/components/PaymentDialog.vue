<template>
  <Teleport to="body">
    <div v-if="state.open" class="pmd-backdrop" @click.self="onCancel">
      <div class="pmd-dialog">
        <div class="pmd-header">
          <span class="pmd-title">
            {{ state.direction === "pay" ? "Pay Vendor" : "Record Payment" }} — {{ state.name }}
          </span>
          <button class="pmd-close" @click="onCancel" :disabled="saving">✕</button>
        </div>

        <div class="pmd-party">
          <div class="pmd-avatar">{{ (state.partyLabel || state.party || "?").charAt(0).toUpperCase() }}</div>
          <div class="pmd-party-info">
            <div class="pmd-party-name">{{ state.partyLabel || state.party }}</div>
            <div class="pmd-balance">
              Balance {{ state.direction === "pay" ? "Payable" : "Due" }}:
              <strong>{{ fmt(state.balance) }}</strong>
            </div>
          </div>
        </div>

        <div class="pmd-body">
          <div class="pmd-grid">
            <div class="pmd-field">
              <label class="pmd-lbl">Amount <span class="pmd-req">*</span></label>
              <input v-model.number="form.amount" type="number" min="0.01" step="0.01" class="pmd-input pmd-money" />
            </div>
            <div class="pmd-field">
              <label class="pmd-lbl">Payment Date <span class="pmd-req">*</span></label>
              <input v-model="form.date" type="date" class="pmd-input" />
            </div>
            <div class="pmd-field">
              <label class="pmd-lbl">Mode</label>
              <select v-model="form.mode" class="pmd-input">
                <option>Cash</option>
                <option>Cheque</option>
                <option>Bank Transfer</option>
                <option>UPI</option>
                <option>NEFT</option>
                <option>RTGS</option>
                <option>IMPS</option>
                <option>Credit Card</option>
                <option>Debit Card</option>
                <option>DD</option>
              </select>
            </div>
            <div class="pmd-field">
              <label class="pmd-lbl">Reference #</label>
              <input v-model="form.ref" class="pmd-input" placeholder="Cheque / Txn #" />
            </div>
            <div class="pmd-field pmd-full">
              <label class="pmd-lbl">
                {{ accountFieldLabel }}
                <span class="pmd-hint">({{ isCashMode ? "Cash-in-Hand ledger" : "Bank ledger" }})</span>
              </label>
              <select v-model="form.bank" class="pmd-input">
                <option value="">— Select —</option>
                <option v-for="a in filteredAccounts" :key="a.name" :value="a.name">{{ a.name }}</option>
              </select>
              <div v-if="!filteredAccounts.length" class="pmd-warn">
                No {{ isCashMode ? "Cash" : "Bank" }} account found for this company. Set one up under Accounts first.
              </div>
            </div>
            <div class="pmd-field">
              <label class="pmd-lbl">Bank Charges</label>
              <input v-model.number="form.charges" type="number" min="0" step="0.01" class="pmd-input pmd-money" />
            </div>
            <div class="pmd-field pmd-full">
              <label class="pmd-lbl">Notes</label>
              <textarea v-model="form.notes" class="pmd-input" rows="2"></textarea>
            </div>
          </div>

          <div class="pmd-summary">
            <div><span>Total Balance</span><strong>{{ fmt(state.balance) }}</strong></div>
            <div><span>{{ state.direction === "pay" ? "Paying" : "Receiving" }}</span><strong>{{ fmt(form.amount) }}</strong></div>
            <div class="pmd-after">
              <span>Balance After</span>
              <strong :style="`color:${(state.balance - form.amount) > 0 ? '#dc2626' : '#059669'}`">
                {{ fmt(Math.max(0, state.balance - form.amount)) }}
              </strong>
            </div>
          </div>
        </div>

        <div class="pmd-footer">
          <button class="pmd-btn pmd-btn-ghost" @click="onCancel" :disabled="saving">Cancel</button>
          <button
            class="pmd-btn pmd-btn-primary"
            :disabled="saving || !form.amount || form.amount <= 0 || !$canWrite('payments')"
            :title="!$canWrite('payments') ? 'Read-only access' : ''"
            @click="onSave"
          >
            {{ saving ? "Recording…" : (state.direction === "pay" ? "Record Payment" : "Receive Payment") }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { reactive, ref, watch, computed } from "vue";
import { apiGET, apiPOST } from "../api/client.js";
import { usePaymentDialog } from "../composables/usePaymentDialog.js";
import { useToast } from "../composables/useToast.js";

const { state, complete, cancel } = usePaymentDialog();
const { toast } = useToast();

const saving = ref(false);
// Full account objects: [{ name, account_type: "Cash" | "Bank" }, ...]
const allAccounts = ref([]);
const form = reactive({ amount: 0, date: "", mode: "Cash", ref: "", bank: "", charges: 0, notes: "" });

// Only "Cash" mode maps to the Cash-in-Hand ledger bucket; every other mode
// (Cheque, Bank Transfer, UPI, NEFT, RTGS, IMPS, Credit/Debit Card, DD) is a
// bank-clearing instrument and must map to a Bank ledger. This is the guard
// that stops a cash receipt from ever posting straight to Bank (or vice versa).
const isCashMode = computed(() => form.mode === "Cash");
const filteredAccounts = computed(() =>
  allAccounts.value.filter(a => a.account_type === (isCashMode.value ? "Cash" : "Bank"))
);
const accountFieldLabel = computed(() => {
  if (state.direction === "pay") return isCashMode.value ? "Paid From" : "Paid From";
  return isCashMode.value ? "Received Into" : "Deposit To";
});

// Whenever Mode switches (e.g. Cash -> UPI), re-point the selected account to
// the matching bucket so a stale Bank/Cash selection can't linger under the
// wrong mode.
watch(() => form.mode, () => {
  if (!filteredAccounts.value.some(a => a.name === form.bank)) {
    form.bank = filteredAccounts.value[0]?.name || "";
  }
});

watch(() => state.open, async (open) => {
  if (!open) return;
  Object.assign(form, {
    amount: state.balance || 0,
    date: new Date().toISOString().slice(0, 10),
    mode: "Cash", ref: "", bank: "", charges: 0, notes: "",
  });
  allAccounts.value = [];
  if (state.getDefaultsEndpoint) {
    try {
      const params = { [state.paramKey]: state.name };
      const d = await apiGET(state.getDefaultsEndpoint, params);
      if (d?.bank_accounts) {
        // Normalize: backend returns {name, account_type}; tolerate plain strings too.
        allAccounts.value = d.bank_accounts.map(a =>
          typeof a === "string" ? { name: a, account_type: "Bank" } : a
        );
      }
      if (d?.payment_modes && d.payment_modes[0]) form.mode = d.payment_modes[0];
      // Select the account matching the (possibly just-set) mode, not just index 0.
      const bucket = isCashMode.value ? "Cash" : "Bank";
      form.bank = allAccounts.value.find(a => a.account_type === bucket)?.name || "";
    } catch {}
  }
});

function fmt(v) {
  return "₹" + Number(v || 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

async function onSave() {
  if (!form.amount || form.amount <= 0) { toast("Amount must be > 0", "error"); return; }
  if (!form.bank) { toast(`Select a ${isCashMode.value ? "Cash" : "Bank"} account`, "error"); return; }
  // Belt-and-braces: never let a Cash-mode payment post to a Bank ledger, or
  // a Bank-mode payment post to Cash-in-Hand, even if the selection got out
  // of sync with the dropdown (e.g. stale prop update).
  const chosen = allAccounts.value.find(a => a.name === form.bank);
  const expectedType = isCashMode.value ? "Cash" : "Bank";
  if (chosen && chosen.account_type !== expectedType) {
    toast(`Mode is "${form.mode}" but the selected account is a ${chosen.account_type} account. Please pick a ${expectedType} account.`, "error");
    return;
  }
  saving.value = true;
  try {
    const payload = {
      [state.paramKey]: state.name,
      amount_received: form.amount,
      amount_paid: form.amount,
      payment_date: form.date,
      payment_mode: form.mode,
      deposit_to: form.bank || "",
      paid_from: form.bank || "",
      bank_charges: form.charges || 0,
      reference_no: form.ref || "",
      notes: form.notes || "",
      save_as_draft: 0,
    };
    const res = await apiPOST(state.sendEndpoint, payload);
    toast(state.direction === "pay" ? "Vendor payment recorded" : "Payment recorded", "success");
    complete(res?.payment_entry || res?.name || true);
  } catch (e) {
    toast("Failed: " + (e.message || ""), "error");
  }
  saving.value = false;
}

function onCancel() {
  if (saving.value) return;
  cancel();
}
</script>

<style scoped>
.pmd-backdrop {
  position: fixed; inset: 0; background: rgba(15,23,42,.5);
  z-index: 10000; display: flex; align-items: center; justify-content: center;
}
.pmd-dialog {
  background: #fff; border-radius: 12px; width: 540px; max-width: 96vw;
  max-height: 92vh; display: flex; flex-direction: column;
  box-shadow: 0 12px 40px rgba(0,0,0,.2);
  animation: pmd-in .2s cubic-bezier(.34,1.56,.64,1);
}
@keyframes pmd-in { from { opacity: 0; transform: scale(.96) translateY(8px); } to { opacity: 1; transform: none; } }
.pmd-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px; border-bottom: 1px solid #e5e7eb; flex-shrink: 0;
}
.pmd-title { font-size: 15px; font-weight: 700; color: #111827; }
.pmd-close { background: transparent; border: none; cursor: pointer; font-size: 16px; color: #6b7280; width: 28px; height: 28px; border-radius: 6px; }
.pmd-close:hover { background: #f3f4f6; }
.pmd-close:disabled { opacity: .4; cursor: not-allowed; }
.pmd-party {
  display: flex; align-items: center; gap: 12px; padding: 12px 18px;
  background: #f0f9ff; border-bottom: 1px solid #e0f2fe; flex-shrink: 0;
}
.pmd-avatar {
  width: 36px; height: 36px; border-radius: 50%;
  background: #0369a1; color: #fff; display: grid; place-items: center;
  font-weight: 700; font-size: 14px;
}
.pmd-party-name { font-size: 13.5px; font-weight: 700; color: #0c4a6e; }
.pmd-balance { font-size: 12px; color: #0c4a6e; margin-top: 2px; }
.pmd-balance strong { font-size:12px }
.pmd-body { padding: 14px 18px; flex: 1; overflow-y: auto; }
.pmd-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.pmd-field { display: flex; flex-direction: column; gap: 4px; }
.pmd-full { grid-column: 1 / -1; }
.pmd-lbl { font-size: 12px; font-weight: 600; color: #374151; }
.pmd-req { color: #ef4444; margin-left: 2px; }
.pmd-hint { font-weight: 500; color: #6b7280; font-size: 11px; margin-left: 2px; }
.pmd-warn { font-size: 11.5px; color: #b45309; background: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; padding: 6px 8px; margin-top: 4px; }
.pmd-input {
  width: 100%; box-sizing: border-box;
  border: 1px solid #e5e7eb; border-radius: 6px; padding: 7px 10px;
  font-size: 13px; outline: none; font-family: inherit; background: #fff;
}
.pmd-input:focus { border-color: #2563eb; box-shadow: 0 0 0 2px rgba(37,99,235,.08); }
.pmd-money {  font-weight: 600; }
.pmd-summary {
  margin-top: 12px; background: #f8fafc; border-radius: 8px; padding: 12px;
  display: flex; flex-direction: column; gap: 6px; font-size: 13px;
}
.pmd-summary > div { display: flex; justify-content: space-between; color: #374151; }
.pmd-summary strong { font-size:13px; }
.pmd-after { border-top: 1px solid #e5e7eb; padding-top: 6px; font-weight: 700; }
.pmd-footer {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 12px 18px; border-top: 1px solid #e5e7eb; flex-shrink: 0;
}
.pmd-btn { font: inherit; font-size: 13px; padding: 8px 16px; border-radius: 8px; border: 1px solid transparent; cursor: pointer; font-weight: 600; }
.pmd-btn:disabled { opacity: .5; cursor: not-allowed; }
.pmd-btn-ghost { background: #fff; border-color: #e5e7eb; color: #374151; }
.pmd-btn-ghost:hover:not(:disabled) { background: #f9fafb; }
.pmd-btn-primary { background: #2563eb; color: #fff; }
.pmd-btn-primary:hover:not(:disabled) { background: #1d4ed8; }
</style>