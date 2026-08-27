<template>
  <Teleport to="body">
    <div v-if="state.open" class="mr-overlay" @click.self="onClose"></div>
    <div v-if="state.open" class="mr-drawer">
      <div class="mr-header">
        <div class="mr-header-left">
          <div class="mr-header-ico"><span v-html="icon('repeat',18)"></span></div>
          <div>
            <div class="mr-title">Make Recurring</div>
            <div class="mr-sub">{{ state.doctype }} · {{ state.name }}</div>
          </div>
        </div>
        <button class="mr-close" @click="onClose"><span v-html="icon('x',16)"></span></button>
      </div>

      <div class="mr-body">
        <!-- Context card showing the source doc -->
        <div v-if="state.partyLabel || state.amount" class="mr-context">
          <div class="mr-context-row">
            <span class="mr-context-lbl">{{ state.partyLabel ? 'Party' : 'Reference' }}</span>
            <span class="mr-context-val">{{ state.partyLabel || state.name }}</span>
          </div>
          <div v-if="state.amount" class="mr-context-row">
            <span class="mr-context-lbl">Template Amount</span>
            <span class="mr-context-val mono">{{ fmtCurrency(state.amount) }}</span>
          </div>
        </div>

        <!-- Section: Schedule -->
        <div class="mr-section">
          <div class="mr-section-hdr"><span v-html="icon('refresh',13)"></span><span>Schedule</span></div>
          <div class="mr-grid">
            <div class="mr-field">
              <label>Frequency <span class="req">*</span></label>
              <select v-model="form.frequency" class="mr-input">
                <option value="Daily">Daily</option>
                <option value="Weekly">Weekly</option>
                <option value="Monthly">Monthly</option>
                <option value="Quarterly">Quarterly</option>
                <option value="Half-yearly">Half-yearly</option>
                <option value="Yearly">Yearly</option>
              </select>
            </div>
            <div class="mr-field">
              <label>Submit on Creation</label>
              <select v-model="form.submit_on_creation" class="mr-input">
                <option :value="1">Yes — auto-submit</option>
                <option :value="0">No — save as draft</option>
              </select>
            </div>
            <div class="mr-field">
              <label>Start Date <span class="req">*</span></label>
              <input v-model="form.start_date" type="date" class="mr-input" />
            </div>
            <div class="mr-field">
              <label>End Date <span class="hint">(optional)</span></label>
              <input v-model="form.end_date" type="date" class="mr-input" :min="minEndDate" />
            </div>
            <div v-if="planHint" class="mr-plan" style="grid-column:1/-1">
              <span v-html="icon('info',13)"></span> {{ planHint }}
            </div>
          </div>
        </div>

        <!-- Section: Notification -->
        <div class="mr-section">
          <div class="mr-section-hdr">
            <span v-html="icon('mail',13)"></span><span>Notification</span>
            <label class="mr-toggle">
              <input type="checkbox" v-model="form._notify" />
              <span class="mr-toggle-slider"></span>
            </label>
          </div>
          <div v-if="!form._notify" class="mr-section-empty">
            Email notifications are off. Toggle to email someone every time a document is generated.
          </div>
          <div v-else class="mr-grid">
            <div class="mr-field" style="grid-column:1/-1">
              <label>Recipients <span class="hint">(comma separated)</span></label>
              <input v-model="form.recipients" type="text" class="mr-input"
                     placeholder="finance@company.com, owner@company.com" />
            </div>
            <div class="mr-field" style="grid-column:1/-1">
              <label>Email Subject</label>
              <input v-model="form.subject" type="text" class="mr-input"
                     placeholder="Your recurring invoice is ready" />
            </div>
            <div class="mr-field" style="grid-column:1/-1">
              <label>Email Message</label>
              <textarea v-model="form.message" class="mr-input" rows="3"
                        placeholder="Hello, please find your latest document attached…"></textarea>
            </div>
          </div>
        </div>
      </div>

      <div class="mr-footer">
        <button class="mr-btn-ghost" @click="onClose" :disabled="saving">Cancel</button>
        <button class="mr-btn-primary" @click="submit" :disabled="saving">
          <span v-html="icon('repeat',13)"></span>
          {{ saving ? "Creating…" : "Create Subscription" }}
        </button>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, watch } from "vue";
import { useMakeRecurring } from "../composables/useMakeRecurring.js";
import { useToast } from "../composables/useToast.js";
import { apiPOST } from "../api/client.js";
import { icon } from "../utils/icons.js";

const { state, complete, cancel } = useMakeRecurring();
const { toast } = useToast();

const saving = ref(false);
const form = reactive({
  frequency: "Monthly",
  start_date: new Date().toISOString().slice(0, 10),
  end_date: "",
  submit_on_creation: 1,
  _notify: false,
  recipients: "",
  subject: "",
  message: "",
});

const minEndDate = computed(() => {
  if (!form.start_date) return "";
  const d = new Date(form.start_date);
  d.setDate(d.getDate() + 1);
  return d.toISOString().slice(0, 10);
});

const planHint = computed(() => {
  if (!form.start_date) return "";
  if (!form.end_date) return "Open-ended subscription — runs until paused or cancelled.";
  const start = new Date(form.start_date);
  const end = new Date(form.end_date);
  if (end < start) return "End date is before start date.";
  const months = (end.getFullYear() - start.getFullYear()) * 12 + (end.getMonth() - start.getMonth());
  const map = {
    Daily: Math.max(1, Math.round((end - start) / 86400000)),
    Weekly: Math.max(1, Math.round((end - start) / (7 * 86400000))),
    Monthly: months + 1,
    Quarterly: Math.floor(months / 3) + 1,
    "Half-yearly": Math.floor(months / 6) + 1,
    Yearly: end.getFullYear() - start.getFullYear() + 1,
  };
  const n = map[form.frequency] || 0;
  return `Will generate approximately ${n} document${n !== 1 ? "s" : ""}.`;
});

// Reset form when dialog opens
watch(() => state.open, (v) => {
  if (v) {
    Object.assign(form, {
      frequency: "Monthly",
      start_date: new Date().toISOString().slice(0, 10),
      end_date: "",
      submit_on_creation: 1,
      _notify: false,
      recipients: "",
      subject: "",
      message: "",
    });
    saving.value = false;
  }
});

function fmtCurrency(v) {
  if (v == null || v === "") return "—";
  const n = Number(v) || 0;
  return "OMR " + n.toLocaleString("en-OM", { maximumFractionDigits: 3 });
}

function onClose() {
  if (saving.value) return;
  cancel();
}

async function submit() {
  if (!form.start_date) return toast.error("Start date is required");
  if (form.end_date && form.end_date <= form.start_date) {
    return toast.error("End date must be after start date");
  }
  saving.value = true;
  try {
    const res = await apiPOST("zoho_books_clone.api.recurring.make_recurring_from_doc", {
      reference_doctype: state.doctype,
      reference_document: state.name,
      frequency: form.frequency,
      start_date: form.start_date,
      end_date: form.end_date || null,
      submit_on_creation: form.submit_on_creation,
      recipients: form._notify ? form.recipients : "",
      subject: form._notify ? form.subject : "",
      message: form._notify ? form.message : "",
    });
    const subName = res?.message?.name || res?.name;
    toast.success(`Recurring subscription ${subName || ""} created`);
    complete(subName);
  } catch (e) {
    toast.error(e.message || "Failed to create subscription");
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
/* MakeRecurringDialog sits on top of every page drawer (Invoices is 8000, Banking ~9999) */
.mr-overlay{position:fixed;inset:0;background:rgba(15,23,42,.42);backdrop-filter:blur(3px);z-index:11000;}
.mr-drawer{position:fixed;top:0;right:0;bottom:0;width:560px;max-width:96vw;background:#fff;border-left:1px solid #e5e7eb;box-shadow:-16px 0 40px rgba(15,23,42,.18);z-index:11010;display:flex;flex-direction:column;animation:slideIn .24s cubic-bezier(.32,.72,0,1);}
@keyframes slideIn{from{transform:translateX(100%)}to{transform:translateX(0)}}

/* Header — gradient + icon badge, matching every other premium drawer */
.mr-header{display:flex;align-items:flex-start;justify-content:space-between;padding:18px 20px;border-bottom:1px solid #e5e7eb;background:linear-gradient(135deg,#eff6ff 0%,#dbeafe 100%);flex-shrink:0;}
.mr-header-left{display:flex;align-items:flex-start;gap:12px;}
.mr-header-ico{width:38px;height:38px;border-radius:10px;background:#fff;border:1px solid rgba(37,99,235,.18);display:inline-flex;align-items:center;justify-content:center;color:#2563eb;box-shadow:0 1px 3px rgba(15,23,42,.06);flex-shrink:0;}
.mr-title{font-size:15px;font-weight:700;color:#111827;letter-spacing:-0.01em;}
.mr-sub{font-size:12px;color:#475569;margin-top:3px;font-weight:500;}
.mr-close{background:rgba(255,255,255,.6);border:none;cursor:pointer;color:#475569;width:32px;height:32px;border-radius:8px;display:inline-flex;align-items:center;justify-content:center;transition:background .15s;}
.mr-close:hover{background:#fff;color:#111827;}

/* Body — slate background + sectioned white cards */
.mr-body{flex:1;overflow-y:auto;padding:18px 20px;display:flex;flex-direction:column;gap:14px;background:#f8fafc;}

/* Context strip showing the source doc */
.mr-context{display:flex;flex-direction:column;gap:8px;background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:12px 14px;box-shadow:0 1px 2px rgba(15,23,42,.04);}
.mr-context-row{display:flex;justify-content:space-between;align-items:center;font-size:13px;gap:12px;}
.mr-context-row + .mr-context-row{border-top:1px dashed #f1f5f9;padding-top:8px;}
.mr-context-lbl{color:#6b7280;font-weight:600;text-transform:uppercase;font-size:10.5px;letter-spacing:.05em;flex-shrink:0;}
.mr-context-val{color:#0f172a;font-weight:700;text-align:right;}

/* Section cards */
.mr-section{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:12px;box-shadow:0 1px 2px rgba(15,23,42,.03);}
.mr-section-hdr{display:flex;align-items:center;gap:8px;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:#0f172a;}
.mr-section-hdr svg{color:#2563eb;}
.mr-section-empty{font-size:12.5px;color:#6b7280;font-style:italic;line-height:1.5;}

/* iOS-style toggle (sits at the right of the section header) */
.mr-toggle{position:relative;margin-left:auto;width:34px;height:18px;display:inline-block;cursor:pointer;}
.mr-toggle input{opacity:0;width:0;height:0;}
.mr-toggle-slider{position:absolute;inset:0;background:#cbd5e1;border-radius:18px;transition:background .18s;}
.mr-toggle-slider::before{content:"";position:absolute;width:14px;height:14px;left:2px;top:2px;background:#fff;border-radius:50%;transition:transform .18s;box-shadow:0 1px 3px rgba(0,0,0,.15);}
.mr-toggle input:checked + .mr-toggle-slider{background:#2563eb;}
.mr-toggle input:checked + .mr-toggle-slider::before{transform:translateX(16px);}

.mr-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
.mr-field{display:flex;flex-direction:column;gap:4px;}
.mr-field label{font-size:12px;font-weight:600;color:#374151;}
.req{color:#dc2626;}
.hint{font-weight:400;color:#9ca3af;font-size:11px;}
.mr-input{border:1px solid #e2e8f0;border-radius:8px;padding:8px 12px;font:inherit;font-size:13px;outline:none;background:#fff;color:#0f172a;transition:border-color .15s,box-shadow .15s;}
.mr-input:hover:not(:disabled){border-color:#cbd5e1;}
.mr-input:focus{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.12);}
.mr-plan{background:#eff6ff;border:1px solid #bfdbfe;color:#1d4ed8;padding:8px 12px;border-radius:8px;font-size:12px;display:flex;align-items:center;gap:8px;}

.mr-footer{display:flex;align-items:center;justify-content:flex-end;gap:8px;padding:14px 20px;border-top:1px solid #e5e7eb;background:#fff;flex-shrink:0;}
.mr-btn-ghost{display:inline-flex;align-items:center;gap:6px;background:transparent;border:1px solid #e5e7eb;border-radius:8px;padding:8px 14px;font-size:13px;color:#374151;cursor:pointer;font-family:inherit;}
.mr-btn-ghost:hover:not(:disabled){background:#f9fafb;}
.mr-btn-ghost:disabled{opacity:.5;cursor:not-allowed;}
.mr-btn-primary{display:inline-flex;align-items:center;gap:6px;background:#2563eb;color:#fff;border:none;border-radius:8px;padding:8px 14px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;}
.mr-btn-primary:hover:not(:disabled){background:#1d4ed8;}
.mr-btn-primary:disabled{opacity:.5;cursor:not-allowed;}
</style>
