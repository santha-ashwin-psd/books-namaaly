<template>
  <div class="sso-page">
    <div class="sso-head">
      <div>
        <div class="sso-title">Single Sign-On</div>
        <div class="sso-sub">Allow your team to log in with Google or Microsoft. Users who sign in via SSO are automatically provisioned if they match a team member's email.</div>
      </div>
    </div>

    <div v-if="loading" class="sso-loading">Loading…</div>
    <div v-else class="sso-grid">

      <!-- Google -->
      <div class="sso-card" :class="google.enabled ? 'card-on' : ''">
        <div class="sso-card-header">
          <div class="sso-logo google-logo">
            <svg width="22" height="22" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.18 1.48-4.97 2.31-8.16 2.31-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/><path fill="none" d="M0 0h48v48H0z"/></svg>
          </div>
          <div class="sso-card-meta">
            <div class="sso-card-name">Google Sign-In</div>
            <div class="sso-card-desc">Let users log in with their Google / Google Workspace account</div>
          </div>
          <span class="sso-pill" :class="google.enabled ? 'pill-on' : 'pill-off'">{{ google.enabled ? 'Active' : 'Inactive' }}</span>
        </div>

        <div class="sso-form">
          <div class="sso-field">
            <label class="sso-lbl">Client ID <span class="req">*</span></label>
            <input v-model="google.client_id" class="sso-input" placeholder="xxxx.apps.googleusercontent.com" autocomplete="off" />
          </div>
          <div class="sso-field">
            <label class="sso-lbl">Client Secret <span class="req">*</span></label>
            <input v-model="google.client_secret" class="sso-input" type="password" :placeholder="google.has_secret ? '••••••••••••• (saved)' : 'Enter client secret'" autocomplete="off" />
          </div>
          <div class="sso-hint">
            <span v-html="icon('ext', 11)"></span>
            Get these from <strong>Google Cloud Console → APIs &amp; Services → Credentials</strong>. Set redirect URI to:
            <code class="sso-code">{{ origin }}/api/method/frappe.integrations.oauth2_logins.login_via_google</code>
          </div>
        </div>

        <div class="sso-actions">
          <button v-if="google.enabled" class="sso-btn-ghost" @click="disable('Google')" :disabled="google.saving || !$canEdit('admin')">Disable</button>
          <button class="sso-btn-primary" @click="save('Google')" :disabled="google.saving || !google.client_id || !$canEdit('admin')">
            {{ google.saving ? 'Saving…' : google.enabled ? 'Update' : 'Enable Google Sign-In' }}
          </button>
        </div>
      </div>

      <!-- Microsoft / Office 365 -->
      <div class="sso-card" :class="ms.enabled ? 'card-on' : ''">
        <div class="sso-card-header">
          <div class="sso-logo ms-logo">
            <svg width="22" height="22" viewBox="0 0 21 21"><rect x="1" y="1" width="9" height="9" fill="#f25022"/><rect x="11" y="1" width="9" height="9" fill="#7fba00"/><rect x="1" y="11" width="9" height="9" fill="#00a4ef"/><rect x="11" y="11" width="9" height="9" fill="#ffb900"/></svg>
          </div>
          <div class="sso-card-meta">
            <div class="sso-card-name">Microsoft / Azure AD</div>
            <div class="sso-card-desc">Let users log in with their Microsoft 365 or Azure AD account</div>
          </div>
          <span class="sso-pill" :class="ms.enabled ? 'pill-on' : 'pill-off'">{{ ms.enabled ? 'Active' : 'Inactive' }}</span>
        </div>

        <div class="sso-form">
          <div class="sso-field">
            <label class="sso-lbl">Application (Client) ID <span class="req">*</span></label>
            <input v-model="ms.client_id" class="sso-input" placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" autocomplete="off" />
          </div>
          <div class="sso-field">
            <label class="sso-lbl">Client Secret <span class="req">*</span></label>
            <input v-model="ms.client_secret" class="sso-input" type="password" :placeholder="ms.has_secret ? '••••••••••••• (saved)' : 'Enter client secret'" autocomplete="off" />
          </div>
          <div class="sso-hint">
            <span v-html="icon('ext', 11)"></span>
            Get these from <strong>Azure Portal → App registrations</strong>. Set redirect URI to:
            <code class="sso-code">{{ origin }}/api/method/frappe.integrations.oauth2_logins.login_via_office365</code>
          </div>
        </div>

        <div class="sso-actions">
          <button v-if="ms.enabled" class="sso-btn-ghost" @click="disable('Office 365')" :disabled="ms.saving || !$canEdit('admin')">Disable</button>
          <button class="sso-btn-primary" @click="save('Office 365')" :disabled="ms.saving || !ms.client_id || !$canEdit('admin')">
            {{ ms.saving ? 'Saving…' : ms.enabled ? 'Update' : 'Enable Microsoft Sign-In' }}
          </button>
        </div>
      </div>

    </div>

    <!-- How it works -->
    <div class="sso-info-card">
      <div class="sso-info-title"><span v-html="icon('info', 14)"></span> How SSO works with Books</div>
      <ol class="sso-info-list">
        <li>Configure credentials above and click Enable.</li>
        <li>Your team members visit the Books login page — a <strong>"Sign in with Google"</strong> or <strong>"Sign in with Microsoft"</strong> button appears automatically.</li>
        <li>On first sign-in, Frappe checks if the email matches an existing user. If yes, they're logged in. If not, a new user is created (if sign-ups are enabled in System Settings).</li>
        <li>After SSO login, the user lands on the Books dashboard as normal.</li>
      </ol>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { apiGET, apiPOST } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";

const { toast } = useToast();
const loading = ref(true);
const origin = window.location.origin;

const google = reactive({ enabled: false, client_id: "", client_secret: "", has_secret: false, saving: false });
const ms     = reactive({ enabled: false, client_id: "", client_secret: "", has_secret: false, saving: false });

async function load() {
  loading.value = true;
  try {
    const data = await apiGET("zoho_books_clone.api.admin.get_sso_providers");
    const g = data?.Google || data?.message?.Google || {};
    const m = data?.["Office 365"] || data?.message?.["Office 365"] || {};
    Object.assign(google, { enabled: !!g.enabled, client_id: g.client_id || "", has_secret: !!g.has_secret, client_secret: "" });
    Object.assign(ms,     { enabled: !!m.enabled, client_id: m.client_id || "", has_secret: !!m.has_secret, client_secret: "" });
  } catch (e) {
    toast.error(e.message || "Failed to load SSO settings");
  } finally {
    loading.value = false;
  }
}

async function save(provider) {
  const state = provider === "Google" ? google : ms;
  if (!state.client_id) return toast.error("Client ID is required");
  if (!state.has_secret && !state.client_secret) return toast.error("Client Secret is required");
  state.saving = true;
  try {
    await apiPOST("zoho_books_clone.api.admin.save_sso_provider", {
      provider,
      client_id: state.client_id,
      client_secret: state.client_secret || "",
      enabled: 1,
    });
    toast.success(`${provider} SSO enabled`);
    await load();
  } catch (e) {
    toast.error(e.message || "Failed to save");
  } finally {
    state.saving = false;
  }
}

async function disable(provider) {
  const state = provider === "Google" ? google : ms;
  state.saving = true;
  try {
    await apiPOST("zoho_books_clone.api.admin.disable_sso_provider", { provider });
    toast.success(`${provider} SSO disabled`);
    await load();
  } catch (e) {
    toast.error(e.message || "Failed to disable");
  } finally {
    state.saving = false;
  }
}

onMounted(load);
</script>

<style scoped>
.sso-page { display:flex; flex-direction:column; gap:20px; padding:24px; }
.sso-head { display:flex; align-items:flex-start; justify-content:space-between; gap:16px; }
.sso-title { font-size:18px; font-weight:700; color:#0f172a; }
.sso-sub { font-size:12.5px; color:#64748b; margin-top:3px; max-width:680px; line-height:1.55; }
.sso-loading { padding:40px; text-align:center; color:#94a3b8; }

.sso-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(420px,1fr)); gap:16px; }
.sso-card { background:#fff; border:1.5px solid #e5e7eb; border-radius:14px; display:flex; flex-direction:column; gap:0; overflow:hidden; transition:border-color .2s; }
.sso-card.card-on { border-color:#86efac; }

.sso-card-header { display:flex; align-items:flex-start; gap:12px; padding:18px 18px 14px; border-bottom:1px solid #f1f5f9; }
.sso-logo { width:42px; height:42px; border-radius:10px; background:#f8fafc; display:flex; align-items:center; justify-content:center; flex-shrink:0; border:1px solid #e5e7eb; }
.sso-card-meta { flex:1; min-width:0; }
.sso-card-name { font-size:14px; font-weight:700; color:#0f172a; }
.sso-card-desc { font-size:12px; color:#64748b; margin-top:2px; line-height:1.4; }
.sso-pill { align-self:center; margin-left:auto; display:inline-flex; align-items:center; border-radius:20px; padding:3px 11px; font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; white-space:nowrap; }
.pill-on  { background:#dcfce7; color:#16a34a; }
.pill-off { background:#f1f5f9; color:#64748b; }

.sso-form { padding:16px 18px; display:flex; flex-direction:column; gap:12px; }
.sso-field { display:flex; flex-direction:column; gap:4px; }
.sso-lbl { font-size:11.5px; font-weight:600; color:#374151; }
.req { color:#dc2626; }
.sso-input { border:1px solid #e5e7eb; border-radius:7px; padding:8px 10px; font:inherit; font-size:13px; outline:none; color:#111827; background:#fff; }
.sso-input:focus { border-color:#2563eb; box-shadow:0 0 0 2px rgba(37,99,235,.08); }
.sso-hint { font-size:11.5px; color:#64748b; line-height:1.6; display:flex; flex-direction:column; gap:3px; }
.sso-code { font-size:10.5px; background:#f1f5f9; color:#0f172a; padding:2px 6px; border-radius:4px; word-break:break-all; display:block; margin-top:4px; }

.sso-actions { padding:14px 18px 18px; display:flex; justify-content:flex-end; gap:8px; border-top:1px solid #f1f5f9; }
.sso-btn-primary { display:inline-flex; align-items:center; gap:6px; background:#2563eb; color:#fff; border:none; border-radius:8px; padding:9px 16px; font:inherit; font-size:13px; font-weight:600; cursor:pointer; }
.sso-btn-primary:hover:not(:disabled) { background:#1d4ed8; }
.sso-btn-primary:disabled { opacity:.5; cursor:not-allowed; }
.sso-btn-ghost { display:inline-flex; align-items:center; gap:6px; background:#fff; border:1px solid #e5e7eb; color:#374151; border-radius:8px; padding:9px 16px; font:inherit; font-size:13px; font-weight:600; cursor:pointer; }
.sso-btn-ghost:hover:not(:disabled) { background:#f9fafb; }
.sso-btn-ghost:disabled { opacity:.5; cursor:not-allowed; }

.sso-info-card { background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:18px 20px; }
.sso-info-title { display:flex; align-items:center; gap:7px; font-size:13px; font-weight:700; color:#0f172a; margin-bottom:10px; }
.sso-info-list { margin:0; padding-left:18px; display:flex; flex-direction:column; gap:6px; }
.sso-info-list li { font-size:12.5px; color:#475569; line-height:1.55; }

@media (max-width: 768px) {
  .sso-head { flex-wrap: wrap; }
  .sso-grid { grid-template-columns: 1fr !important; }
}
@media (max-width: 480px) {
  .sso-page { padding: 12px; gap: 12px; }
}
</style>