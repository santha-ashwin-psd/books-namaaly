<template>
<div class="cust-page">
  <div class="cust-toolbar">
    <span style="font-size:18px;font-weight:700;color:#1a1a2e">Email Settings (SMTP)</span>
    <span v-if="form.company" style="background:#F3F0FF;color:#2563eb;padding:2px 10px;border-radius:20px;font-size:12px;font-weight:600;margin-left:10px">{{form.company}}</span>
  </div>

  <div style="background:#f0f4ff;border:1px solid #c5d0fa;border-radius:10px;padding:14px 18px;margin-bottom:18px;font-size:13px;color:#3b4a7a;display:flex;gap:12px;align-items:flex-start">
    <span style="font-size:18px;margin-top:-1px">✉️</span>
    <div><strong>How email works in Books:</strong> By default, invoices, payment reminders, and customer email are sent from the built-in platform account (<em>Books by PS Digitise</em>). Turn on <strong>Enable Company SMTP</strong> below to send that business email from your own address instead. Sign-in &amp; password-reset OTPs always use the platform account and are never affected by these settings.</div>
  </div>

  <div v-if="loading" style="padding:40px;text-align:center;color:#868E96">Loading…</div>

  <div v-else style="max-width:760px;display:grid;gap:16px">
    <div style="background:#fff;border:1px solid #e4e8f0;border-radius:12px;padding:24px">
      <label style="display:flex;align-items:flex-start;gap:10px;cursor:pointer;margin-bottom:18px">
        <input type="checkbox" :checked="form.smtp_enabled" @change="form.smtp_enabled = $event.target.checked ? 1 : 0" style="width:16px;height:16px;cursor:pointer;margin-top:2px"/>
        <span>
          <span style="font-size:14px;font-weight:600;color:#1a1a2e;display:block">Enable Company SMTP</span>
          <span style="font-size:12px;color:#868e96">{{ form.smtp_enabled ? 'On — invoices & business email are sent from your SMTP server below.' : 'Off — business email is sent from the platform account (Books by PS Digitise).' }}</span>
        </span>
      </label>

      <div class="se-form-grid" style="display:grid;grid-template-columns:1fr 1fr;gap:14px 18px">
        <div>
          <div style="font-size:11.5px;color:#6b7db3;font-weight:600;margin-bottom:6px">SMTP Server</div>
          <input class="nim-input" v-model="form.smtp_server" placeholder="smtp.gmail.com" :disabled="!form.smtp_enabled"/>
        </div>
        <div>
          <div style="font-size:11.5px;color:#6b7db3;font-weight:600;margin-bottom:6px">Port</div>
          <input class="nim-input" type="number" v-model.number="form.smtp_port" placeholder="587" :disabled="!form.smtp_enabled"/>
        </div>
        <div>
          <div style="font-size:11.5px;color:#6b7db3;font-weight:600;margin-bottom:6px">Username (login)</div>
          <input class="nim-input" v-model="form.smtp_login" placeholder="you@company.com" :disabled="!form.smtp_enabled"/>
        </div>
        <div>
          <div style="font-size:11.5px;color:#6b7db3;font-weight:600;margin-bottom:6px">
            Password / App Password
            <span v-if="form.smtp_password_set && !form.smtp_password" style="color:#868e96;font-weight:500;font-size:11px">— stored, leave blank to keep</span>
          </div>
          <input class="nim-input" type="password" v-model="form.smtp_password" placeholder="••••••••" :disabled="!form.smtp_enabled"/>
        </div>
        <div>
          <div style="font-size:11.5px;color:#6b7db3;font-weight:600;margin-bottom:6px">From Email</div>
          <input class="nim-input" v-model="form.smtp_from_email" placeholder="invoices@company.com" :disabled="!form.smtp_enabled"/>
        </div>
        <div>
          <div style="font-size:11.5px;color:#6b7db3;font-weight:600;margin-bottom:6px">From Name</div>
          <input class="nim-input" v-model="form.smtp_from_name" :placeholder="form.company" :disabled="!form.smtp_enabled"/>
        </div>
        <label style="display:flex;align-items:center;gap:8px;font-size:13px;color:#3b4a7a;cursor:pointer">
          <input type="radio" name="smtp-enc" :checked="form.smtp_use_tls && !form.smtp_use_ssl" @change="setEncryption('tls')" :disabled="!form.smtp_enabled"/>
          Use TLS (port 587)
        </label>
        <label style="display:flex;align-items:center;gap:8px;font-size:13px;color:#3b4a7a;cursor:pointer">
          <input type="radio" name="smtp-enc" :checked="form.smtp_use_ssl && !form.smtp_use_tls" @change="setEncryption('ssl')" :disabled="!form.smtp_enabled"/>
          Use SSL (port 465)
        </label>
      </div>

      <div style="display:flex;gap:10px;margin-top:20px">
        <button class="nim-btn nim-btn-primary" @click="save" :disabled="saving || !$canEdit('admin')">{{saving?'Saving…':'Save SMTP Settings'}}</button>
      </div>
    </div>

    <div style="background:#fff;border:1px solid #e4e8f0;border-radius:12px;padding:24px">
      <div style="font-size:14px;font-weight:700;color:#1a1a2e;margin-bottom:4px">Send Test Email</div>
      <div style="font-size:12px;color:#868e96;margin-bottom:12px">Tip: if you've typed a new password above, the test will use that without saving — verify before persisting.</div>
      <div style="display:flex;gap:10px">
        <input class="nim-input" v-model="testEmail" placeholder="recipient@example.com" style="flex:1"/>
        <button class="nim-btn nim-btn-primary" @click="sendTest" :disabled="testing">{{testing?'Sending…':'Send Test'}}</button>
      </div>
    </div>
  </div>
</div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { apiGET, apiPOST } from "../api/client.js";
import { useToast } from "../composables/useToast.js";

const { toast } = useToast();

const form = reactive({
  company: "",
  smtp_enabled: 0,
  smtp_server: "",
  smtp_port: 587,
  smtp_use_tls: 1,
  smtp_use_ssl: 0,
  smtp_login: "",
  smtp_password: "",
  smtp_password_set: false,
  smtp_from_email: "",
  smtp_from_name: "",
});
const loading   = ref(true);
const saving    = ref(false);
const testing   = ref(false);
const testEmail = ref("");

async function load() {
  loading.value = true;
  try {
    const d = await apiGET("zoho_books_clone.api.admin.get_company_smtp");
    Object.assign(form, d || {}, { smtp_password: "" });
  } catch (e) { toast(e.message || "Could not load SMTP settings", "error"); }
  loading.value = false;
}

// TLS and SSL are mutually exclusive — selecting one clears the other and
// snaps the port to its conventional default (only when it's still the other's).
function setEncryption(kind) {
  if (kind === "tls") {
    form.smtp_use_tls = 1; form.smtp_use_ssl = 0;
    if (Number(form.smtp_port) === 465) form.smtp_port = 587;
  } else {
    form.smtp_use_ssl = 1; form.smtp_use_tls = 0;
    if (Number(form.smtp_port) === 587) form.smtp_port = 465;
  }
}

function validate() {
  if (!form.smtp_enabled) return true; // nothing to validate when disabled
  if (!String(form.smtp_server).trim()) { toast("SMTP Server is required", "error"); return false; }
  if (!Number(form.smtp_port))          { toast("A valid Port is required", "error"); return false; }
  if (!String(form.smtp_login).trim())  { toast("Username (login) is required", "error"); return false; }
  if (!form.smtp_password && !form.smtp_password_set) { toast("Password is required", "error"); return false; }
  if (!form.smtp_use_tls && !form.smtp_use_ssl) { toast("Choose an encryption method — TLS or SSL", "error"); return false; }
  return true;
}

async function save() {
  if (!validate()) return;
  saving.value = true;
  try {
    const payload = { ...form };
    if (!payload.smtp_password) delete payload.smtp_password;
    delete payload.smtp_password_set; delete payload.company;
    await apiPOST("zoho_books_clone.api.admin.save_company_smtp", payload);
    toast("SMTP settings saved");
    form.smtp_password = "";
    await load();
  } catch (e) { toast(e.message || "Could not save", "error"); }
  saving.value = false;
}

async function sendTest() {
  if (!testEmail.value) return toast("Enter a recipient email", "error");
  testing.value = true;
  try {
    const payload = { to_email: testEmail.value };
    if (form.smtp_password) {
      Object.assign(payload, {
        use_overrides: 1,
        smtp_server: form.smtp_server, smtp_port: form.smtp_port,
        smtp_use_tls: form.smtp_use_tls, smtp_use_ssl: form.smtp_use_ssl,
        smtp_login: form.smtp_login, smtp_password: form.smtp_password,
        smtp_from_email: form.smtp_from_email, smtp_from_name: form.smtp_from_name,
      });
    }
    await apiPOST("zoho_books_clone.api.admin.send_test_email", payload);
    toast("Test email sent to " + testEmail.value);
  } catch (e) { toast(e.message || "Test failed", "error"); }
  testing.value = false;
}

onMounted(load);
</script>

<style>
@media (max-width: 480px) {
  .se-form-grid { grid-template-columns: 1fr !important; }
  .cust-page { padding: 12px !important; }
}
</style>