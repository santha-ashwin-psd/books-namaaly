<template>
  <Teleport to="body">
    <div v-if="state.open" class="pmd-backdrop" @click.self="onCancel">
      <div class="pmd-dialog">
        <div class="pmd-header">
          <span class="pmd-title">
            {{ state.direction === "pay" ? "Pay Vendor" : "Record Payment" }}
            — {{ state.multi ? (state.partyLabel || state.party) : state.name }}
          </span>
          <button class="pmd-close" @click="onCancel" :disabled="saving">✕</button>
        </div>

        <div class="pmd-party">
          <div class="pmd-avatar">{{ (state.partyLabel || state.party || "?").charAt(0).toUpperCase() }}</div>
          <div class="pmd-party-info">
            <div class="pmd-party-name">{{ state.partyLabel || state.party }}</div>
            <div class="pmd-balance">
              {{ state.multi ? "Total Outstanding" : (state.direction === "pay" ? "Balance Payable" : "Balance Due") }}:
              <strong>{{ fmt(state.multi ? totalOutstanding : state.balance) }}</strong>
            </div>
          </div>
        </div>

        <div class="pmd-body">
          <div v-if="state.multi && loadingInvoices" class="pmd-loading">Loading outstanding {{ state.direction === "pay" ? "bills" : "invoices" }}…</div>
          <div v-else-if="state.multi && !invoices.length" class="pmd-empty">
            This {{ state.direction === "pay" ? "vendor" : "customer" }} has no outstanding {{ state.direction === "pay" ? "bills" : "invoices" }}.
          </div>

          <template v-else>
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
                  <option>Demand Draft</option>
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

            <!-- Multi-invoice picker -->
            <template v-if="state.multi">
              <div class="pmd-invoices-head">
                <span class="pmd-lbl">Apply to {{ state.direction === "pay" ? "Bills" : "Invoices" }}</span>
                <button class="pmd-link-btn" type="button" @click="autoAllocate" :disabled="!form.amount">
                  Auto-allocate (oldest due first)
                </button>
              </div>
              <div class="pmd-table">
                <div class="pmd-row pmd-row-head">
                  <div class="pmd-col pmd-col-check"></div>
                  <div class="pmd-col pmd-col-inv">{{ state.direction === "pay" ? "Bill" : "Invoice" }}</div>
                  <div class="pmd-col pmd-col-due">Due Date</div>
                  <div class="pmd-col pmd-col-amt">Outstanding</div>
                  <div class="pmd-col pmd-col-amt">Allocate</div>
                </div>
                <div v-for="row in invoices" :key="row.name" class="pmd-row">
                  <div class="pmd-col pmd-col-check">
                    <input type="checkbox" v-model="row.checked" @change="onCheckToggle(row)" />
                  </div>
                  <div class="pmd-col pmd-col-inv">{{ row.name }}</div>
                  <div class="pmd-col pmd-col-due">{{ fmtDate(row.due_date) }}</div>
                  <div class="pmd-col pmd-col-amt">{{ fmt(row.outstanding_amount) }}</div>
                  <div class="pmd-col pmd-col-amt">
                    <input
                      type="number" min="0" step="0.01" class="pmd-alloc-input"
                      :disabled="!row.checked"
                      v-model.number="row.allocated"
                      @input="clampAlloc(row)"
                    />
                  </div>
                </div>
              </div>
            </template>

            <div class="pmd-summary">
              <div v-if="!state.multi"><span>Total Balance</span><strong>{{ fmt(state.balance) }}</strong></div>
              <div><span>{{ state.direction === "pay" ? "Paying" : "Receiving" }}</span><strong>{{ fmt(form.amount) }}</strong></div>

              <template v-if="state.multi">
                <div><span>Total Allocated</span><strong :class="allocDiff !== 0 ? 'pmd-red' : ''">{{ fmt(totalAllocated) }}</strong></div>
                <div class="pmd-after" v-if="allocDiff !== 0">
                  <span>{{ allocDiff > 0 ? "Unallocated" : "Over-allocated" }}</span>
                  <strong class="pmd-red">{{ fmt(Math.abs(allocDiff)) }}</strong>
                </div>
              </template>
              <div class="pmd-after" v-else>
                <span>Balance After</span>
                <strong :style="`color:${(state.balance - form.amount) > 0 ? '#dc2626' : '#059669'}`">
                  {{ fmt(Math.max(0, state.balance - form.amount)) }}
                </strong>
              </div>
            </div>
            <div v-if="state.multi && allocDiff !== 0" class="pmd-warn">
              Total allocated must equal Amount before you can save. Use Auto-allocate or adjust the amounts above.
            </div>
          </template>
        </div>

        <div class="pmd-footer">
          <button class="pmd-btn pmd-btn-ghost" @click="onCancel" :disabled="saving">Cancel</button>
          <button
            class="pmd-btn pmd-btn-primary"
            :disabled="saving || !canSave || !$canWrite('payments')"
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
const loadingInvoices = ref(false);
const invoices = ref([]); // multi mode only: [{ name, due_date, outstanding_amount, checked, allocated }]
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
  if (state.direction === "pay") return "Paid From";
  return isCashMode.value ? "Received Into" : "Deposit To";
});

const totalOutstanding = computed(() =>
  invoices.value.reduce((s, r) => s + (Number(r.outstanding_amount) || 0), 0)
);
const totalAllocated = computed(() =>
  invoices.value.filter(r => r.checked).reduce((s, r) => s + (Number(r.allocated) || 0), 0)
);
const allocDiff = computed(() => round2((form.amount || 0) - totalAllocated.value));

const canSave = computed(() => {
  if (!form.amount || form.amount <= 0) return false;
  if (state.multi) return invoices.value.length > 0 && allocDiff.value === 0;
  return true;
});

function round2(n) { return Math.round((n + Number.EPSILON) * 100) / 100; }
function fmtDate(d) {
  if (!d) return "—";
  try { return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }); }
  catch { return d; }
}

// Whenever Mode switches (e.g. Cash -> UPI), re-point the selected account to
// the matching bucket so a stale Bank/Cash selection can't linger under the
// wrong mode.
watch(() => form.mode, () => {
  if (!filteredAccounts.value.some(a => a.name === form.bank)) {
    form.bank = filteredAccounts.value[0]?.name || "";
  }
});

function onCheckToggle(row) {
  if (!row.checked) {
    row.allocated = 0;
    form.amount = round2(totalAllocated.value);
    return;
  }
  // When freshly checked, default the allocation to whatever cash is left,
  // capped at this invoice's outstanding.
  const remaining = round2((form.amount || 0) - totalAllocated.value);
  row.allocated = Math.max(0, Math.min(row.outstanding_amount, remaining || row.outstanding_amount));
  form.amount = round2(totalAllocated.value);
}

function clampAlloc(row) {
  if (row.allocated < 0) row.allocated = 0;
  if (row.allocated > row.outstanding_amount) row.allocated = row.outstanding_amount;
  // A manual edit to one invoice's allocation is the user making a deliberate
  // partial payment against it — follow that intent by re-syncing the total
  // Amount to match, rather than blocking save on a stale mismatch.
  form.amount = round2(totalAllocated.value);
}

function autoAllocate() {
  // Invoices are sorted oldest-due-first by the backend, so a straight FIFO
  // walk gives the standard "pay oldest bills first" allocation.
  let remaining = round2(form.amount || 0);
  for (const row of invoices.value) {
    if (remaining <= 0) {
      row.checked = false;
      row.allocated = 0;
      continue;
    }
    const take = Math.min(row.outstanding_amount, remaining);
    row.checked = true;
    row.allocated = round2(take);
    remaining = round2(remaining - take);
  }
}

watch(() => state.open, async (open) => {
  if (!open) return;
  Object.assign(form, {
    amount: state.multi ? 0 : (state.balance || 0),
    date: new Date().toISOString().slice(0, 10),
    mode: "Cash", ref: "", bank: "", charges: 0, notes: "",
  });
  allAccounts.value = [];
  invoices.value = [];

  if (state.multi) {
    loadingInvoices.value = true;
    try {
      // Invoices handed in directly (e.g. from a multiselect on the list page)
      // came from a deliberate user selection, so pre-check them and allocate
      // their full outstanding amount. Invoices fetched via `invoicesEndpoint`
      // (e.g. a customer's whole open-invoice list) start unchecked since
      // that's a browse list, not a selection.
      const preselected = Array.isArray(state.invoices) && state.invoices.length > 0;
      const list = state.invoices || (state.invoicesEndpoint
        ? (await apiGET(state.invoicesEndpoint, { customer: state.party })).invoices || []
        : []);
      invoices.value = list.map(r => ({
        ...r,
        checked: preselected,
        allocated: preselected ? round2(Number(r.outstanding_amount) || 0) : 0,
      }));
      if (preselected) {
        form.amount = round2(invoices.value.reduce((s, r) => s + (Number(r.outstanding_amount) || 0), 0));
      }
    } catch (e) {
      toast("Failed to load invoices: " + (e.message || ""), "error");
    }
    loadingInvoices.value = false;
  }

  if (state.getDefaultsEndpoint) {
    try {
      const params = state.multi
        ? { [state.paramKey || "invoice_name"]: invoices.value[0]?.name }
        : { [state.paramKey]: state.name };
      const d = await apiGET(state.getDefaultsEndpoint, params);
      if (d?.bank_accounts) {
        // Normalize: backend returns {name, account_type}; tolerate plain strings too.
        allAccounts.value = d.bank_accounts.map(a =>
          typeof a === "string" ? { name: a, account_type: "Bank" } : a
        );
      }
      // NOTE: intentionally NOT overriding form.mode with d.payment_modes[0] here.
      // That list is alphabetically ordered by the backend ("Bank Transfer" sorts
      // before "Cash"), so doing so silently flipped the correct "Cash" default
      // set above to "Bank Transfer" on every open — mis-booking cash receipts
      // to a Bank account and making them vanish from the Bank & Cash undeposited
      // total. The mode dropdown's options are hardcoded in the template anyway,
      // so this list isn't needed to drive the selection.
      // Select the account matching the current mode, not just index 0.
      const bucket = isCashMode.value ? "Cash" : "Bank";
      form.bank = allAccounts.value.find(a => a.account_type === bucket)?.name || "";
    } catch (e) {
      toast("Failed to load payment accounts: " + (e.message || ""), "error");
    }
  }
});

function fmt(v) {
  return "OMR " + Number(v || 0).toLocaleString("en-OM", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
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

  if (state.multi && allocDiff.value !== 0) {
    toast("Total allocated must equal amount received", "error");
    return;
  }

  saving.value = true;
  try {
    let payload;
    if (state.multi) {
      const allocations = invoices.value
        .filter(r => r.checked && r.allocated > 0)
        .map(r => ({ invoice: r.name, allocated_amount: r.allocated }));
      if (!allocations.length) { toast("Select at least one invoice", "error"); saving.value = false; return; }
      const common = {
        payment_date: form.date,
        payment_mode: form.mode,
        reference_no: form.ref || "",
        notes: form.notes || "",
        allocations: JSON.stringify(allocations),
        bank_charges: form.charges || 0,
        save_as_draft: 0,
      };
      payload = state.direction === "pay"
        ? { ...common, supplier: state.party, amount_paid: form.amount, paid_from: form.bank || "" }
        : { ...common, customer: state.party, amount_received: form.amount, deposit_to: form.bank || "" };
    } else {
      payload = {
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
    }
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
.pmd-loading, .pmd-empty { padding: 24px 0; text-align: center; color: #6b7280; font-size: 13px; }
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
.pmd-invoices-head { display: flex; align-items: center; justify-content: space-between; margin: 10px 0 6px; }
.pmd-link-btn {
  background: none; border: none; color: #2563eb; font-size: 12px; font-weight: 600;
  cursor: pointer; padding: 0;
}
.pmd-link-btn:disabled { color: #9ca3af; cursor: not-allowed; }
.pmd-table { border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; }
.pmd-row { display: grid; grid-template-columns: 26px 1.4fr 1fr 1fr 1fr; align-items: center; gap: 6px; padding: 7px 8px; border-top: 1px solid #f1f5f9; }
.pmd-row:first-child { border-top: none; }
.pmd-row-head { background: #f8fafc; font-size: 10.5px; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: .02em; }
.pmd-col-amt { text-align: right; }
.pmd-col-inv { font-weight: 600; color: #111827; font-size: 12px; }
.pmd-col-due { font-size: 12px; color: #6b7280; }
.pmd-alloc-input {
  width: 100%; box-sizing: border-box; text-align: right;
  border: 1px solid #e5e7eb; border-radius: 6px; padding: 5px 6px; font-size: 12px;
}
.pmd-alloc-input:disabled { background: #f9fafb; color: #9ca3af; }
.pmd-summary {
  margin-top: 12px; background: #f8fafc; border-radius: 8px; padding: 12px;
  display: flex; flex-direction: column; gap: 6px; font-size: 13px;
}
.pmd-summary > div { display: flex; justify-content: space-between; color: #374151; }
.pmd-summary strong { font-size:13px; }
.pmd-after { border-top: 1px solid #e5e7eb; padding-top: 6px; font-weight: 700; }
.pmd-red { color: #dc2626; }
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