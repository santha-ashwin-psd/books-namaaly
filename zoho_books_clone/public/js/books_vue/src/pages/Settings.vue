<template>
  <div class="settings-page">
    <div class="tabs">
      <button :class="['tab', tab==='smtp'  && 'active']" @click="tab='smtp'">Email / SMTP</button>
      <button :class="['tab', tab==='users' && 'active']" @click="tab='users'">Users &amp; Permissions</button>
    </div>

    <!-- ─── SMTP TAB ──────────────────────────────────────────── -->
    <section v-if="tab==='smtp'" class="card">
      <h2>Outgoing Email (Company SMTP)</h2>
      <p class="hint">
        This SMTP is used for invoices, payment reminders, and customer email.
        Sign-up and password-reset OTPs are sent via the platform-level SMTP and don't use these settings.
      </p>

      <div v-if="smtpLoading" class="muted">Loading…</div>

      <form v-else class="form" @submit.prevent="saveSmtp">
        <label class="row">
          <input type="checkbox" v-model="smtp.smtp_enabled" :true-value="1" :false-value="0"/>
          <span>Enable Company SMTP</span>
        </label>

        <div class="grid">
          <div class="fld">
            <label>SMTP Server</label>
            <input v-model="smtp.smtp_server" placeholder="smtp.gmail.com" :disabled="!smtp.smtp_enabled"/>
          </div>
          <div class="fld">
            <label>Port</label>
            <input v-model.number="smtp.smtp_port" type="number" placeholder="587" :disabled="!smtp.smtp_enabled"/>
          </div>
          <div class="fld">
            <label>Username (login)</label>
            <input v-model="smtp.smtp_login" placeholder="you@company.com" :disabled="!smtp.smtp_enabled"/>
          </div>
          <div class="fld">
            <label>Password / App Password
              <span v-if="smtp.smtp_password_set && !smtp.smtp_password" class="muted">(stored — leave blank to keep)</span>
            </label>
            <input v-model="smtp.smtp_password" type="password" placeholder="••••••••" :disabled="!smtp.smtp_enabled"/>
          </div>
          <div class="fld">
            <label>From Email</label>
            <input v-model="smtp.smtp_from_email" placeholder="invoices@company.com" :disabled="!smtp.smtp_enabled"/>
          </div>
          <div class="fld">
            <label>From Name</label>
            <input v-model="smtp.smtp_from_name" :placeholder="smtp.company" :disabled="!smtp.smtp_enabled"/>
          </div>
          <label class="row">
            <input type="checkbox" v-model="smtp.smtp_use_tls" :true-value="1" :false-value="0" :disabled="!smtp.smtp_enabled"/>
            <span>Use TLS (port 587)</span>
          </label>
          <label class="row">
            <input type="checkbox" v-model="smtp.smtp_use_ssl" :true-value="1" :false-value="0" :disabled="!smtp.smtp_enabled"/>
            <span>Use SSL (port 465)</span>
          </label>
        </div>

        <div class="actions">
          <button type="submit" class="btn-primary" :disabled="saving">{{ saving ? "Saving…" : "Save SMTP Settings" }}</button>
          <button type="button" class="btn-ghost" @click="testSmtp" :disabled="testing">{{ testing ? "Sending…" : "Send Test Email" }}</button>
        </div>

        <div v-if="smtpMsg" :class="['msg', smtpMsgKind]">{{ smtpMsg }}</div>
      </form>
    </section>

    <!-- ─── USERS TAB ─────────────────────────────────────────── -->
    <section v-if="tab==='users'" class="card">
      <h2>Users &amp; Permissions</h2>
      <p class="hint">
        Invite teammates and choose what each one can access.
        Invited users receive an email with a temporary password — they should change it on first login.
      </p>

      <div class="user-actions">
        <button class="btn-primary" :disabled="!$canCreate('admin')" :title="!$canCreate('admin') ? 'Read-only access' : ''" @click="openInvite">+ Invite User</button>
      </div>

      <div v-if="usersLoading" class="muted">Loading…</div>

      <table v-else class="users-table">
        <thead>
          <tr>
            <th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Modules</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.email">
            <td>{{ u.full_name || "—" }}</td>
            <td class="mono">{{ u.email }}</td>
            <td>
              <select :value="u.books_role" @change="onRoleChange(u, $event.target.value)" :disabled="u.email===currentUser || !$canEdit('admin')">
                <option v-for="r in roles" :key="r" :value="r">{{ r }}</option>
              </select>
            </td>
            <td>
              <span v-if="u.is_company_admin" class="pill admin">Admin</span>
              <span v-else-if="u.enabled" class="pill ok">Active</span>
              <span v-else class="pill off">Disabled</span>
            </td>
            <td class="modules-cell">
              <button class="btn-link" @click="openPerms(u)" :disabled="u.is_company_admin || !$canEdit('admin')">
                {{ u.is_company_admin ? "All access" : (moduleSummary(u.modules) || "Edit access…") }}
              </button>
            </td>
            <td class="row-actions">
              <button v-if="u.email !== currentUser && !u.is_company_admin" class="btn-link danger" :disabled="!$canDelete('admin')" :title="!$canDelete('admin') ? 'Not permitted' : ''" @click="removeUser(u)">Remove</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="usersMsg" :class="['msg', usersMsgKind]">{{ usersMsg }}</div>
    </section>

    <!-- ─── INVITE MODAL ──────────────────────────────────────── -->
    <div v-if="showInvite" class="modal-backdrop" @click.self="showInvite=false">
      <div class="modal">
        <h3>Invite User</h3>
        <form @submit.prevent="submitInvite">
          <div class="grid">
            <div class="fld">
              <label>Email *</label>
              <input v-model="invite.email" type="email" required/>
            </div>
            <div class="fld">
              <label>First Name</label>
              <input v-model="invite.first_name"/>
            </div>
            <div class="fld">
              <label>Last Name</label>
              <input v-model="invite.last_name"/>
            </div>
            <div class="fld">
              <label>Role *</label>
              <select v-model="invite.role">
                <option v-for="r in roles" :key="r" :value="r">{{ r }}</option>
              </select>
            </div>
          </div>

          <div v-if="invite.role !== 'Books Admin'" class="modules-grid">
            <div class="modules-title">Module access</div>
            <label v-for="m in moduleList" :key="m.key" class="row">
              <input type="checkbox" v-model="invite.modules[m.key]"/>
              <span>{{ m.label }}</span>
            </label>
          </div>

          <div class="actions">
            <button type="button" class="btn-ghost" @click="showInvite=false">Cancel</button>
            <button type="submit" class="btn-primary" :disabled="inviting">{{ inviting ? "Inviting…" : "Send Invite" }}</button>
          </div>
          <div v-if="inviteErr" class="msg err">{{ inviteErr }}</div>
        </form>
      </div>
    </div>

    <!-- ─── PERMISSIONS MODAL ─────────────────────────────────── -->
    <div v-if="showPerms" class="modal-backdrop" @click.self="showPerms=false">
      <div class="modal">
        <h3>Module Access — {{ permsUser.full_name || permsUser.email }}</h3>
        <div class="modules-grid">
          <label v-for="m in moduleList" :key="m.key" class="row">
            <input type="checkbox" v-model="permsDraft[m.key]"/>
            <span>{{ m.label }}</span>
          </label>
        </div>
        <div class="actions">
          <button type="button" class="btn-ghost" @click="showPerms=false">Cancel</button>
          <button type="button" class="btn-primary" @click="savePerms" :disabled="savingPerms || !$canEdit('admin')">{{ savingPerms ? "Saving…" : "Save Access" }}</button>
        </div>
        <div v-if="permsErr" class="msg err">{{ permsErr }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from "vue";
import { useConfirm } from "../composables/useConfirm.js";
import { usePrompt } from "../composables/usePrompt.js";

const { confirm } = useConfirm();
const { prompt } = usePrompt();

const tab = ref("smtp");
const currentUser = computed(() => (window.frappe?.session?.user || ""));

// ────────────────────────────────────────────────────────────────
// Frappe API helper
// ────────────────────────────────────────────────────────────────
async function callApi(method, args = {}) {
  const csrf = window.frappe?.csrf_token || "";
  const res = await fetch(`/api/method/${method}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "X-Frappe-CSRF-Token": csrf,
    },
    credentials: "same-origin",
    body: new URLSearchParams(
      Object.fromEntries(
        Object.entries(args).map(([k, v]) => [k, typeof v === "object" ? JSON.stringify(v) : v]),
      ),
    ),
  });
  const data = await res.json();
  if (!res.ok) {
    const msg = (data && (data._server_messages || data.exception || data.message)) || `HTTP ${res.status}`;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data.message;
}

// ────────────────────────────────────────────────────────────────
// SMTP tab
// ────────────────────────────────────────────────────────────────
const smtp = reactive({
  smtp_enabled: 0, smtp_server: "", smtp_port: 587,
  smtp_use_tls: 1, smtp_use_ssl: 0,
  smtp_login: "", smtp_password: "",
  smtp_from_email: "", smtp_from_name: "",
  smtp_password_set: false, company: "",
});
const smtpLoading = ref(true);
const saving = ref(false);
const testing = ref(false);
const smtpMsg = ref("");
const smtpMsgKind = ref("ok");

async function loadSmtp() {
  smtpLoading.value = true;
  try {
    const data = await callApi("zoho_books_clone.api.admin.get_company_smtp");
    Object.assign(smtp, data, { smtp_password: "" });
  } catch (e) {
    smtpMsg.value = e.message;
    smtpMsgKind.value = "err";
  } finally {
    smtpLoading.value = false;
  }
}

async function saveSmtp() {
  saving.value = true;
  smtpMsg.value = "";
  try {
    const payload = { ...smtp };
    if (!payload.smtp_password) delete payload.smtp_password;
    delete payload.smtp_password_set; delete payload.company;
    await callApi("zoho_books_clone.api.admin.save_company_smtp", payload);
    smtpMsg.value = "SMTP settings saved.";
    smtpMsgKind.value = "ok";
    smtp.smtp_password = "";
    await loadSmtp();
  } catch (e) {
    smtpMsg.value = e.message;
    smtpMsgKind.value = "err";
  } finally {
    saving.value = false;
  }
}

async function testSmtp() {
  const to = await prompt({
    title: "Send Test Email",
    label: "Send test email to:",
    defaultValue: currentUser.value,
    placeholder: "name@example.com",
    okLabel: "Send",
    inputType: "email",
  });
  if (!to) return;
  testing.value = true;
  smtpMsg.value = "";
  try {
    const overrides = { ...smtp, use_overrides: smtp.smtp_password ? 1 : 0 };
    if (!overrides.smtp_password) delete overrides.use_overrides;
    delete overrides.smtp_password_set; delete overrides.company;
    await callApi("zoho_books_clone.api.admin.send_test_email", { to_email: to, ...overrides });
    smtpMsg.value = `Test email sent to ${to}.`;
    smtpMsgKind.value = "ok";
  } catch (e) {
    smtpMsg.value = e.message;
    smtpMsgKind.value = "err";
  } finally {
    testing.value = false;
  }
}

// ────────────────────────────────────────────────────────────────
// Users tab
// ────────────────────────────────────────────────────────────────
const moduleList = [
  { key: "invoices",  label: "Sales Invoices" },
  { key: "bills",     label: "Bills & Purchases" },
  { key: "payments",  label: "Payments" },
  { key: "banking",   label: "Banking" },
  { key: "inventory", label: "Inventory" },
  { key: "accounts",  label: "Chart of Accounts" },
  { key: "reports",   label: "Reports" },
  { key: "customers", label: "Customers & Suppliers" },
  { key: "taxes",     label: "Taxes & GST" },
  { key: "admin",     label: "Admin / Settings" },
];
const roles = ["Books Admin", "Books Manager", "Accountant", "Books Viewer"];

const users = ref([]);
const usersLoading = ref(true);
const usersMsg = ref("");
const usersMsgKind = ref("ok");

async function loadUsers() {
  usersLoading.value = true;
  try {
    users.value = await callApi("zoho_books_clone.api.admin.get_users_list") || [];
  } catch (e) {
    usersMsg.value = e.message;
    usersMsgKind.value = "err";
  } finally {
    usersLoading.value = false;
  }
}

function moduleSummary(modules) {
  const enabled = moduleList.filter(m => modules?.[m.key]).map(m => m.label);
  if (!enabled.length) return "No module access";
  if (enabled.length === moduleList.length) return "All modules";
  return enabled.length === 1 ? enabled[0] : `${enabled.length} modules`;
}

async function onRoleChange(u, newRole) {
  if (newRole === u.books_role) return;
  try {
    await callApi("zoho_books_clone.api.admin.update_user_role", { user: u.email, role: newRole });
    await loadUsers();
  } catch (e) {
    usersMsg.value = e.message;
    usersMsgKind.value = "err";
  }
}

async function removeUser(u) {
  if (!await confirm({
    title: "Remove User",
    body: `Remove <b>${u.email}</b> from your company? They will be disabled and cannot sign in.`,
    okLabel: "Remove",
  })) return;
  try {
    await callApi("zoho_books_clone.api.admin.remove_user_from_company", { user: u.email });
    await loadUsers();
  } catch (e) {
    usersMsg.value = e.message;
    usersMsgKind.value = "err";
  }
}

// Invite modal
const showInvite = ref(false);
const inviting = ref(false);
const inviteErr = ref("");
const invite = reactive({
  email: "", first_name: "", last_name: "",
  role: "Books Viewer",
  modules: defaultModules(),
});
function defaultModules() {
  return Object.fromEntries(moduleList.map(m => [m.key, ["invoices", "bills", "payments", "reports", "customers"].includes(m.key)]));
}
function openInvite() {
  invite.email = ""; invite.first_name = ""; invite.last_name = "";
  invite.role = "Books Viewer"; invite.modules = defaultModules();
  inviteErr.value = "";
  showInvite.value = true;
}
async function submitInvite() {
  if (!invite.email) { inviteErr.value = "Email is required"; return; }
  inviting.value = true; inviteErr.value = "";
  try {
    const moduleInts = Object.fromEntries(Object.entries(invite.modules).map(([k, v]) => [k, v ? 1 : 0]));
    await callApi("zoho_books_clone.api.admin.invite_user", {
      email: invite.email, first_name: invite.first_name, last_name: invite.last_name,
      role: invite.role, modules: moduleInts,
    });
    showInvite.value = false;
    usersMsg.value = `Invite sent to ${invite.email}.`;
    usersMsgKind.value = "ok";
    await loadUsers();
  } catch (e) {
    inviteErr.value = e.message;
  } finally {
    inviting.value = false;
  }
}

// Permissions modal
const showPerms = ref(false);
const savingPerms = ref(false);
const permsErr = ref("");
const permsUser = ref({});
const permsDraft = reactive({});
function openPerms(u) {
  permsUser.value = u;
  Object.assign(permsDraft, defaultModules());
  for (const k of Object.keys(permsDraft)) permsDraft[k] = !!u.modules?.[k];
  permsErr.value = "";
  showPerms.value = true;
}
async function savePerms() {
  savingPerms.value = true; permsErr.value = "";
  try {
    const moduleInts = Object.fromEntries(Object.entries(permsDraft).map(([k, v]) => [k, v ? 1 : 0]));
    await callApi("zoho_books_clone.api.admin.set_user_permissions", { user: permsUser.value.email, modules: moduleInts });
    showPerms.value = false;
    await loadUsers();
  } catch (e) {
    permsErr.value = e.message;
  } finally {
    savingPerms.value = false;
  }
}

// ── Init ────────────────────────────────────────────────────────
onMounted(() => {
  loadSmtp();
  loadUsers();
});
</script>

<style scoped>
.settings-page { padding: 24px 32px; max-width: 1100px; }
.tabs { display: flex; gap: 4px; border-bottom: 1px solid #E2E8F0; margin-bottom: 20px; }
.tab { background: transparent; border: none; padding: 10px 18px; cursor: pointer; font-size: 14px; color: #64748B; border-bottom: 2px solid transparent; }
.tab.active { color: #1A237E; border-bottom-color: #3949AB; font-weight: 600; }

.card { background: #fff; border-radius: 12px; padding: 28px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.card h2 { font-size: 18px; margin-bottom: 6px; color: #0D1117; }
.hint { color: #64748B; font-size: 13px; margin-bottom: 22px; line-height: 1.5; }

.form { display: flex; flex-direction: column; gap: 16px; }
.grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px 18px; }
.fld { display: flex; flex-direction: column; gap: 6px; }
.fld label { font-size: 12px; color: #64748B; font-weight: 500; }
.fld input, .fld select { border: 1px solid #E2E8F0; border-radius: 8px; padding: 9px 12px; font-size: 14px; outline: none; transition: border-color 0.15s; }
.fld input:focus, .fld select:focus { border-color: #3949AB; }
.fld input:disabled { background: #F8FAFC; color: #94A3B8; }
.row { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #475569; }
.muted { color: #94A3B8; font-size: 13px; }
.actions { display: flex; gap: 10px; margin-top: 8px; }
.btn-primary { background: #3949AB; color: #fff; border: none; border-radius: 8px; padding: 9px 18px; font-size: 14px; font-weight: 500; cursor: pointer; }
.btn-primary:hover { background: #1A237E; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-ghost { background: transparent; color: #3949AB; border: 1px solid #C7D2FE; border-radius: 8px; padding: 9px 18px; font-size: 14px; cursor: pointer; }
.btn-ghost:hover { background: #EEF2FF; }
.btn-link { background: none; border: none; color: #3949AB; cursor: pointer; padding: 0; font-size: 13px; text-decoration: underline; }
.btn-link.danger { color: #C92A2A; }
.btn-link:disabled { color: #94A3B8; cursor: default; text-decoration: none; }
.msg { padding: 10px 14px; border-radius: 8px; font-size: 13px; margin-top: 6px; }
.msg.ok { background: #DEF7EC; color: #03543F; }
.msg.err { background: #FEF3F2; color: #C92A2A; }

.user-actions { margin-bottom: 14px; }
.users-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.users-table th, .users-table td { text-align: left; padding: 12px 10px; border-bottom: 1px solid #F1F5F9; }
.users-table th { font-size: 12px; color: #64748B; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
.users-table .mono { font-size: 13px; color: #475569; }
.users-table select { padding: 5px 8px; font-size: 13px; border: 1px solid #E2E8F0; border-radius: 6px; }
.modules-cell { max-width: 200px; }
.row-actions { text-align: right; }
.pill { display: inline-block; padding: 3px 9px; border-radius: 999px; font-size: 11px; font-weight: 600; }
.pill.admin { background: #E0E7FF; color: #1A237E; }
.pill.ok    { background: #DCFCE7; color: #166534; }
.pill.off   { background: #F1F5F9; color: #64748B; }

.modal-backdrop { position: fixed; inset: 0; background: rgba(15,23,42,0.5); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: #fff; border-radius: 12px; padding: 28px; width: 520px; max-width: calc(100vw - 40px); box-shadow: 0 12px 40px rgba(0,0,0,0.2); }
.modal h3 { margin-bottom: 20px; font-size: 17px; color: #0D1117; }
.modules-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; padding: 12px; background: #F8FAFC; border-radius: 8px; margin: 16px 0; }
.modules-title { grid-column: 1 / -1; font-size: 12px; color: #64748B; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }

@media (max-width: 768px) {
  .settings-page { padding: 16px; }
  .card { overflow-x: auto; }
}
@media (max-width: 480px) {
  .settings-page { padding: 12px; }
  .grid { grid-template-columns: 1fr !important; }
  .users-table { min-width: 480px; }
}
</style>