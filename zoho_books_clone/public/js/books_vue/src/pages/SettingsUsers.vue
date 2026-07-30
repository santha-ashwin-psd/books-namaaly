<template>
<div class="cust-page" @click="closeAllMenus">

  <div class="cust-toolbar">
    <div style="display:flex;align-items:center;gap:12px">
      <span class="su-title">Team Members</span>
      <span class="su-count-badge">{{ users.length }} members</span>
    </div>
    <button v-if="!accessDenied" class="nim-btn nim-btn-primary su-add-btn" :disabled="!$canCreate('admin')" :title="!$canCreate('admin') ? 'Read-only access' : ''" @click="openInvite">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
      Add Member
    </button>
  </div>

  <div v-if="!accessDenied" class="su-info-banner">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
    <div><strong>Company-scoped access:</strong> Members you add here will only see data belonging to your company. Each member gets their own email &amp; password. New user sign-ups always create a separate, isolated company.</div>
  </div>

  <div v-if="accessDenied" class="su-denied">
    <div style="font-size:22px;margin-bottom:8px">🔒</div>
    <strong>Access Denied</strong><br/>
    <span style="color:#4a5568;font-size:13px">Only company admins can manage team members.</span>
  </div>

  <div v-else class="su-cards-section">
    <div v-if="loading" class="su-loading">Loading members…</div>
    <div v-else class="su-cards-grid">
      <!-- Member cards -->
      <div v-for="u in users" :key="u.name" class="su-member-card" @click.self="closeAllMenus">
        <!-- Card header: avatar + owner badge + menu -->
        <div class="su-card-header">
          <div v-if="u.is_owner" class="su-owner-tag">OWNER 👑</div>
          <div v-else style="height:22px"></div>
          <button v-if="!u.is_owner" class="su-menu-btn" @click.stop="toggleMenu(u.name)">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/></svg>
          </button>
          <!-- Dropdown menu -->
          <div v-if="openMenu === u.name" class="su-dropdown" @click.stop>
            <button class="su-dd-item" :disabled="!$canEdit('admin')" :title="!$canEdit('admin') ? 'Read-only access' : ''" @click="editUser=u;editRole=u.books_role;openMenu=null">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              Change Role
            </button>
            <button v-if="!u.is_company_admin" class="su-dd-item" :disabled="!$canEdit('admin')" :title="!$canEdit('admin') ? 'Read-only access' : ''" @click="openPerms(u);openMenu=null">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
              Module Access
            </button>
            <button class="su-dd-item su-dd-item--warn" :disabled="!$canEdit('admin')" :title="!$canEdit('admin') ? 'Read-only access' : ''" @click="toggleActive(u);openMenu=null">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>
              {{ u.enabled ? 'Deactivate' : 'Activate' }}
            </button>
            <div class="su-dd-divider"></div>
            <button class="su-dd-item su-dd-item--danger" :disabled="!$canDelete('admin')" :title="!$canDelete('admin') ? 'Not permitted' : ''" @click="showRemoveConfirm=u;openMenu=null">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
              Remove
            </button>
          </div>
        </div>

        <!-- Avatar -->
        <div class="su-card-avatar-wrap">
          <div v-if="u.user_image" class="su-card-avatar su-card-avatar--img">
            <img :src="u.user_image" style="width:100%;height:100%;object-fit:cover;border-radius:50%"/>
          </div>
          <div v-else class="su-card-avatar">{{ userInitials(u.full_name||u.name) }}</div>
        </div>

        <!-- Name & email -->
        <div class="su-card-name">{{ u.full_name||u.name }}</div>
        <div class="su-card-email">{{ u.name }}</div>

        <div class="su-card-divider"></div>

        <!-- Meta rows -->
        <div class="su-card-meta-row">
          <span class="su-card-meta-label">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 3H8L2 7h20l-6-4z"/></svg>
            Role
          </span>
          <span class="su-role-pill" :style="{ background: ROLE_BG[displayRole(u)]||'#F8F9FA', color: ROLE_COLORS[displayRole(u)]||'#868E96' }">
            {{ displayRole(u)||'—' }}
          </span>
        </div>
        <div class="su-card-meta-row">
          <span class="su-card-meta-label">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            Status
          </span>
          <span class="su-status-pill" :class="u.enabled ? 'su-status--active' : 'su-status--inactive'">
            ● {{ u.enabled ? 'Active' : 'Inactive' }}
          </span>
        </div>
        <div class="su-card-meta-row">
          <span class="su-card-meta-label">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
            Last Login
          </span>
          <span class="su-card-meta-value">{{ u.last_login ? fmtDate(u.last_login) : 'Never' }}</span>
        </div>

        <!-- Joined -->
        <div class="su-card-joined">Joined on {{ u.creation ? fmtDate(u.creation) : '—' }}</div>
      </div>

      <!-- Add New Member card -->
      <div class="su-add-card" @click="$canCreate('admin') && openInvite()">
        <div class="su-add-card-icon">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.8"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="16" y1="11" x2="22" y2="11"/></svg>
        </div>
        <div class="su-add-card-title">Add New Member</div>
        <div class="su-add-card-sub">Invite a new team member to your company</div>
        <button class="su-add-card-btn" :disabled="!$canCreate('admin')" :title="!$canCreate('admin') ? 'Read-only access' : ''" @click.stop="openInvite">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Add Member
        </button>
      </div>
    </div>
  </div>

  <Teleport to="body">
    <!-- Invite drawer -->
    <div v-if="showInvite" class="nim-overlay" @click.self="showInvite=false">
      <div class="nim-dialog" style="width:560px">
        <div class="nim-header">
          <div>
            <span style="font-weight:700;color:#fff;font-size:15px">Add Team Member</span>
            <div style="font-size:11.5px;color:#868e96;margin-top:2px">Step {{stepIndex}} of {{totalSteps}} — {{step===1?'Assign a Role':(step===2?'Module Access':'Set Credentials')}}</div>
          </div>
          <button class="nim-close" @click="showInvite=false">✕</button>
        </div>
        <div style="display:flex;gap:0;padding:0 24px;margin-bottom:-1px">
          <div v-for="s in stepsForRole" :key="s" :style="'flex:1;height:3px;border-radius:2px;margin:0 2px;background:'+(step>=s?'#2563eb':'#e4e8f0')"></div>
        </div>
        <div v-if="step===1" class="nim-body" style="display:grid;gap:12px">
          <div style="font-size:13px;color:#4a5568">Select the role this member will have in your company:</div>
          <div v-for="r in ROLES" :key="r" @click="selectRole(r)" :style="'padding:14px 16px;border-radius:10px;cursor:pointer;display:flex;align-items:center;gap:14px;transition:all .15s;'+(inviteForm.role===r?'border:2px solid #2563eb;background:#f5f0ff':'border:2px solid #e4e8f0;background:#fff')">
            <div :style="'width:10px;height:10px;border-radius:50%;flex-shrink:0;background:'+ROLE_COLORS[r]"></div>
            <div style="flex:1"><div style="font-weight:700;font-size:13px;color:#1a1a2e">{{r}}</div><div style="font-size:12px;color:#868e96;margin-top:2px">{{ROLE_DESC[r]}}</div></div>
            <div v-if="inviteForm.role===r" style="color:#2563eb;font-size:16px">✓</div>
          </div>
          <div v-if="inviteError" style="background:#fff5f5;border:1px solid #ffd0d0;border-radius:8px;padding:10px 14px;color:#C92A2A;font-size:12.5px">{{inviteError}}</div>
        </div>
        <div v-if="step===2" class="nim-body" style="display:grid;gap:14px">
          <div style="background:#f5f0ff;border-radius:8px;padding:10px 14px;display:flex;align-items:center;gap:10px">
            <span :style="'background:'+ROLE_COLORS[inviteForm.role]+';color:#fff;padding:2px 10px;border-radius:20px;font-size:12px;font-weight:700'">{{inviteForm.role}}</span>
            <span style="font-size:12.5px;color:#3b4a7a">Selected — <a href="#" @click.prevent="step=1" style="color:#2563eb;text-decoration:none">Change</a></span>
          </div>
          <div style="font-size:13px;color:#4a5568">{{ inviteForm.role==='Custom' ? 'Pick exactly which modules this member can access.' : 'Choose which modules this member can access.' }}</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;background:#f8f9fc;border-radius:8px;padding:14px">
            <label v-for="m in MODULES" :key="m.key" style="display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:6px;cursor:pointer;font-size:13px;color:#3b4a7a">
              <input type="checkbox" :checked="inviteForm.modules[m.key]" @change="inviteForm.modules[m.key] = $event.target.checked" style="width:14px;height:14px;cursor:pointer"/>
              <span>{{m.label}}</span>
            </label>
          </div>
        </div>
        <div v-if="step===3" class="nim-body" style="display:grid;gap:14px">
          <div style="background:#f5f0ff;border-radius:8px;padding:10px 14px;display:flex;align-items:center;gap:10px">
            <span :style="'background:'+ROLE_COLORS[inviteForm.role]+';color:#fff;padding:2px 10px;border-radius:20px;font-size:12px;font-weight:700'">{{inviteForm.role}}</span>
            <span style="font-size:12.5px;color:#3b4a7a">Selected — <a href="#" @click.prevent="step=1" style="color:#2563eb;text-decoration:none">Change</a></span>
          </div>
          <div class="nim-field"><label class="nim-label">Email Address *</label><input class="nim-input" v-model="inviteForm.email" type="email" placeholder="member@company.com"/></div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
            <div class="nim-field"><label class="nim-label">First Name *</label><input class="nim-input" v-model="inviteForm.first_name" placeholder="First"/></div>
            <div class="nim-field"><label class="nim-label">Last Name</label><input class="nim-input" v-model="inviteForm.last_name" placeholder="Last"/></div>
          </div>
          <div style="background:#f0f9ff;border:1px solid #c5d9fa;border-radius:8px;padding:12px 14px;font-size:12.5px;color:#1971C2;line-height:1.5">
            <strong>📧 Invite by email</strong> — Books will email <em>{{inviteForm.email||'this user'}}</em> a temporary password and a sign-in link.
          </div>
          <div v-if="inviteError" style="background:#fff5f5;border:1px solid #ffd0d0;border-radius:8px;padding:10px 14px;color:#C92A2A;font-size:12.5px">{{inviteError}}</div>
        </div>
        <div class="nim-footer">
          <button class="nim-btn" @click="step===1?showInvite=false:prevStep()">{{step===1?'Cancel':'Back'}}</button>
          <button v-if="step!==3" class="nim-btn nim-btn-primary" @click="nextStep">{{nextLabel}}</button>
          <button v-else class="nim-btn nim-btn-primary" @click="sendInvite" :disabled="saving || !$canCreate('admin')" :title="!$canCreate('admin') ? 'Read-only access' : ''">{{saving?'Sending…':'Send Invite'}}</button>
        </div>
      </div>
    </div>

    <!-- Module Access dialog -->
    <div v-if="permsUser" class="nim-overlay" :key="permsUser.name + '-' + permsRenderKey" @click.self="permsUser=null">
      <div class="nim-dialog" style="width:640px">
        <div class="nim-header"><span style="font-weight:700;color: #fff;">Module Access — {{permsUser.full_name||permsUser.name}}</span><button class="nim-close" @click="permsUser=null">✕</button></div>
        <div class="nim-body" style="display:grid;gap:20px">
          <div>
            <div style="font-size:13px;color:#4a5568;margin-bottom:10px">Toggle which modules this member can access. Unchecking sets the level below to None; checking defaults it to View.</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;background:#f8f9fc;border-radius:8px;padding:14px">
              <label v-for="m in MODULES" :key="m.key" style="display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:6px;cursor:pointer;font-size:13px;color:#3b4a7a">
                <input type="checkbox" :checked="permsDraft[m.key]" @change="onModuleToggle(m.key, $event.target.checked)" style="width:14px;height:14px;cursor:pointer"/>
                <span>{{m.label}}</span>
              </label>
            </div>
          </div>
          <div>
            <div style="font-weight:700;font-size:13.5px;color:#1a1a2e;margin-bottom:2px">Permission Levels</div>
            <div style="font-size:12.5px;color:#868e96;margin-bottom:10px">Granular per-module access (None / View / Create / Edit / Delete). Stays in sync with the checkboxes above — the two never disagree.</div>
            <div v-if="MODULES.some(m => permsDraft[m.key])" style="display:grid;grid-template-columns:1fr 1fr;gap:12px 16px">
              <div v-for="m in MODULES" v-show="permsDraft[m.key]" :key="m.key">
                <label style="display:block;font-size:12.5px;color:#4a5568;margin-bottom:4px">{{m.label}}</label>
                <select :value="levelsDraft[m.key]" @change="onLevelChange(m.key, $event.target.value)" style="width:100%;padding:7px 10px;border-radius:6px;border:1px solid #e4e8f0;background:#f8f9fc;font-size:13px;color:#1a1a2e;cursor:pointer">
                  <option v-for="lvl in LEVELS" :key="lvl" :value="lvl">{{lvl}}</option>
                </select>
              </div>
            </div>
            <div v-else style="font-size:12.5px;color:#9ca3af;padding:10px 0">No modules checked yet — check a module above to set its access level.</div>
          </div>
        </div>
        <div class="nim-footer">
          <button class="nim-btn" @click="permsUser=null">Cancel</button>
          <button class="nim-btn nim-btn-primary" @click="savePerms" :disabled="permsSaving || !$canEdit('admin')" :title="!$canEdit('admin') ? 'Read-only access' : ''">{{permsSaving?'Saving…':'Save Access'}}</button>
        </div>
      </div>
    </div>

    <!-- Change Role dialog -->
    <div v-if="editUser" class="nim-overlay" @click.self="editUser=null">
      <div class="nim-dialog" style="width:420px">
        <div class="nim-header"><span style="font-weight:700;color:#fff;">Change Role — {{editUser.full_name||editUser.name}}</span><button class="nim-close" @click="editUser=null">✕</button></div>
        <div class="nim-body" style="display:grid;gap:10px">
          <div v-for="r in CHANGEABLE_ROLES" :key="r" @click="editRole=r" :style="'padding:12px 14px;border-radius:8px;cursor:pointer;display:flex;align-items:center;gap:12px;transition:all .15s;'+(editRole===r?'border:2px solid #2563eb;background:#f5f0ff':'border:2px solid #e4e8f0;background:#fff')">
            <div :style="'width:8px;height:8px;border-radius:50%;background:'+ROLE_COLORS[r]"></div>
            <div style="flex:1"><div style="font-weight:600;font-size:13px">{{r}}</div><div style="font-size:11.5px;color:#868e96">{{ROLE_DESC[r]}}</div></div>
            <div v-if="editRole===r" style="color:#2563eb">✓</div>
          </div>
        </div>
        <div class="nim-footer"><button class="nim-btn" @click="editUser=null">Cancel</button><button class="nim-btn nim-btn-primary" @click="changeRole" :disabled="!$canEdit('admin')" :title="!$canEdit('admin') ? 'Read-only access' : ''">Save Role</button></div>
      </div>
    </div>

    <!-- Remove confirm -->
    <div v-if="showRemoveConfirm" class="nim-overlay" @click.self="showRemoveConfirm=null">
      <div class="nim-dialog" style="width:400px">
        <div class="nim-header"><span style="font-weight:700;color:#C92A2A">Remove Member</span><button class="nim-close" @click="showRemoveConfirm=null">✕</button></div>
        <div class="nim-body"><p style="color:#4a5568;font-size:13.5px;line-height:1.6">Are you sure you want to remove <strong>{{showRemoveConfirm.full_name||showRemoveConfirm.name}}</strong>? Their account will be deactivated and they will lose access to company data.</p></div>
        <div class="nim-footer"><button class="nim-btn" @click="showRemoveConfirm=null">Cancel</button><button class="nim-btn" style="background:#C92A2A;color:#fff;border-color:#C92A2A" @click="confirmRemove(showRemoveConfirm)" :disabled="!$canDelete('admin')" :title="!$canDelete('admin') ? 'Not permitted' : ''">Remove Member</button></div>
      </div>
    </div>
  </Teleport>
</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { apiGET, apiPOST } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { fmtDate } from "../utils/format.js";
import { icon } from "../utils/icons.js";

const { toast } = useToast();

const MODULES = [
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

const LEVELS = ["None", "View", "Create", "Edit", "Delete"];

const ROLES = ["Books Admin", "Accountant", "Books Manager", "Books Viewer", "Custom"];
const CHANGEABLE_ROLES = ["Books Admin", "Accountant", "Books Manager", "Books Viewer"];

const ROLE_COLORS = {
  "Books Admin":   "#2563eb",
  "Accountant":    "#1971C2",
  "Books Manager": "#2F9E44",
  "Books Viewer":  "#868E96",
  "Custom":        "#E67700",
};
const ROLE_BG = {
  "Books Admin":   "#F3F0FF",
  "Accountant":    "#E7F5FF",
  "Books Manager": "#EBFBEE",
  "Books Viewer":  "#F8F9FA",
  "Custom":        "#FFF3BF",
};
const ROLE_DESC = {
  "Books Admin":   "Full access — manage users, settings, all data",
  "Accountant":    "Create & edit invoices, bills, payments, reports",
  "Books Manager": "Create & edit transactions; no admin functions",
  "Books Viewer":  "Read-only access to all records",
  "Custom":        "Pick exact module access — nothing granted by default",
};

const DEFAULT_MODULES_BY_ROLE = {
  "Books Admin":   Object.fromEntries(MODULES.map((m) => [m.key, true])),
  "Books Manager": { invoices: true, bills: true, payments: true, banking: true, inventory: true, accounts: true, reports: true, customers: true, taxes: false, admin: false },
  "Accountant":    { invoices: true, bills: true, payments: true, banking: true, inventory: false, accounts: true, reports: true, customers: true, taxes: true, admin: false },
  "Books Viewer":  { invoices: true, bills: true, payments: true, banking: false, inventory: false, accounts: false, reports: true, customers: true, taxes: false, admin: false },
  "Custom":        Object.fromEntries(MODULES.map((m) => [m.key, false])),
};
function defaultModulesFor(role) { return { ...(DEFAULT_MODULES_BY_ROLE[role] || {}) }; }

const users    = ref([]);
const loading  = ref(false);
const saving   = ref(false);
const accessDenied = ref(false);
const showInvite = ref(false);
const step     = ref(1);
const editUser = ref(null);
const editRole = ref("");
const showRemoveConfirm = ref(null);

const inviteForm = reactive({
  email: "", first_name: "", last_name: "",
  role: "Books Viewer", password: "", confirm_password: "",
  modules: defaultModulesFor("Books Viewer"),
});
const inviteError = ref("");

const permsUser  = ref(null);
const permsDraft = reactive(defaultModulesFor("Books Viewer"));
const levelsDraft = reactive(Object.fromEntries(MODULES.map((m) => [m.key, "None"])));
const permsSaving = ref(false);
const permsRenderKey = ref(0);
const openMenu = ref(null);

function toggleMenu(name) { openMenu.value = openMenu.value === name ? null : name; }
function closeAllMenus() { openMenu.value = null; }

const stepsForRole = computed(() => inviteForm.role === "Books Admin" ? [1, 3] : [1, 2, 3]);
const totalSteps   = computed(() => stepsForRole.value.length);
const stepIndex    = computed(() => stepsForRole.value.indexOf(step.value) + 1);
const nextLabel    = computed(() => {
  if (step.value === 1) return inviteForm.role === "Books Admin" ? "Next: Set Credentials →" : "Next: Module Access →";
  return "Next: Set Credentials →";
});

function displayRole(u) {
  if (u.books_role !== "Books Viewer") return u.books_role;
  if (!u.modules) return u.books_role;
  const def = DEFAULT_MODULES_BY_ROLE["Books Viewer"];
  for (const m of MODULES) if (!!u.modules[m.key] !== !!def[m.key]) return "Custom";
  return u.books_role;
}

async function load() {
  loading.value = true;
  accessDenied.value = false;
  try {
    users.value = await apiGET("zoho_books_clone.api.admin.get_company_members") || [];
  } catch (e) {
    const msg = e.message || String(e);
    if (msg.includes("permission") || msg.includes("admin") || msg.includes("linked")) {
      accessDenied.value = true;
    } else {
      toast("Could not load members: " + msg, "error");
    }
  }
  loading.value = false;
}

function openInvite() {
  Object.assign(inviteForm, {
    email: "", first_name: "", last_name: "",
    role: "Books Viewer", password: "", confirm_password: "",
    modules: defaultModulesFor("Books Viewer"),
  });
  inviteError.value = "";
  step.value = 1;
  showInvite.value = true;
}

function selectRole(role) {
  inviteForm.role = role;
  inviteForm.modules = defaultModulesFor(role);
}

function nextStep() {
  inviteError.value = "";
  if (step.value === 1) {
    if (!inviteForm.role) { inviteError.value = "Please select a role."; return; }
    step.value = inviteForm.role === "Books Admin" ? 3 : 2;
    return;
  }
  if (step.value === 2) { step.value = 3; return; }
}

function prevStep() {
  if (step.value === 3) { step.value = inviteForm.role === "Books Admin" ? 1 : 2; return; }
  if (step.value === 2) { step.value = 1; return; }
}

async function sendInvite() {
  inviteError.value = "";
  if (!inviteForm.email || !inviteForm.first_name) { inviteError.value = "Email and first name are required."; return; }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(inviteForm.email)) { inviteError.value = "Please enter a valid email address."; return; }
  saving.value = true;
  try {
    const modulePayload = Object.fromEntries(MODULES.map((m) => [m.key, inviteForm.modules[m.key] ? 1 : 0]));
    const serverRole = inviteForm.role === "Custom" ? "Books Viewer" : inviteForm.role;
    await apiPOST("zoho_books_clone.api.admin.invite_member", {
      email: inviteForm.email, first_name: inviteForm.first_name,
      last_name: inviteForm.last_name, role: serverRole,
      password: inviteForm.password || "",
      modules: modulePayload,
    });
    toast("Invite sent — " + inviteForm.email + " will receive an email with sign-in details.");
    showInvite.value = false;
    load();
  } catch (e) { inviteError.value = e.message || "Failed to add member."; }
  saving.value = false;
}

// Checkbox and level dropdown are two views of one value now -- keep them
// in lockstep so they can never silently diverge (that divergence was the
// root cause of "level set to None but user still had access").
function onModuleToggle(key, checked) {
  permsDraft[key] = checked;
  if (!checked) {
    levelsDraft[key] = "None";
  } else if (levelsDraft[key] === "None") {
    levelsDraft[key] = "View";
  }
}
function onLevelChange(key, value) {
  levelsDraft[key] = value;
  permsDraft[key] = value !== "None";
}

function openPerms(u) {
  if (u.is_company_admin) { toast("Admins always have full module access.", "info"); return; }
  permsUser.value = u;
  const current = u.modules || defaultModulesFor(u.books_role);
  for (const m of MODULES) permsDraft[m.key] = !!current[m.key];
  const currentLevels = u.levels || {};
  for (const m of MODULES) levelsDraft[m.key] = currentLevels[m.key] || "None";
}

async function savePerms() {
  if (!permsUser.value) return;
  permsSaving.value = true;
  try {
    const modulePayload = Object.fromEntries(MODULES.map((m) => [m.key, permsDraft[m.key] ? 1 : 0]));
    const levelPayload = Object.fromEntries(MODULES.map((m) => [m.key, levelsDraft[m.key]]));
    const savedUser = permsUser.value.email || permsUser.value.name;
    await apiPOST("zoho_books_clone.api.admin.set_user_permissions", {
      user: savedUser,
      modules: modulePayload,
      levels: levelPayload,
    });
    toast("Module access updated");
    await load();
    // Keep the dialog open and re-sync its draft state from the freshly
    // loaded user record, instead of closing it -- avoids the "looks wrong
    // until you reopen" gap between save and re-render.
    const refreshed = users.value.find((u) => u.name === savedUser);
    if (refreshed) {
      openPerms(refreshed);
      permsRenderKey.value++;
    }
  } catch (e) { toast(e.message || "Failed to update access", "error"); }
  permsSaving.value = false;
}

async function changeRole() {
  try {
    await apiPOST("zoho_books_clone.api.admin.update_user_role", { user: editUser.value.name, role: editRole.value });
    toast("Role updated"); editUser.value = null; load();
  } catch (e) { toast(e.message, "error"); }
}

async function toggleActive(u) {
  try {
    await apiPOST("zoho_books_clone.api.admin.toggle_user_active", { user: u.name, enabled: u.enabled ? 0 : 1 });
    toast(u.enabled ? "Member deactivated" : "Member activated"); load();
  } catch (e) { toast(e.message, "error"); }
}

async function confirmRemove(u) {
  try {
    await apiPOST("zoho_books_clone.api.admin.remove_member", { user_email: u.name });
    toast("Member removed"); showRemoveConfirm.value = null; load();
  } catch (e) { toast(e.message, "error"); }
}

function userInitials(name) {
  return (name || "?").split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2);
}

onMounted(load);
</script>

<style scoped>
/* ── Toolbar ────────────────────────────────────────────────────────── */
.su-title { font-size: 18px; font-weight: 700; color: #1a1a2e; }
.su-count-badge {
  background: #F3F0FF; color: #2563eb;
  padding: 2px 10px; border-radius: 20px;
  font-size: 12px; font-weight: 600;
}
.su-add-btn {
  display: flex; align-items: center; gap: 6px;
  font-size: 13.5px; font-weight: 600;
  padding: 9px 18px; border-radius: 8px;
}

/* ── Info banner ────────────────────────────────────────────────────── */
.su-info-banner {
  background: #f0f4ff;
  border: 1px solid #c5d0fa;
  border-radius: 10px;
  padding: 14px 18px;
  margin-bottom: 18px;
  font-size: 13px;
  color: #3b4a7a;
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

/* ── Access denied ──────────────────────────────────────────────────── */
.su-denied {
  background: #fff5f5; border: 1px solid #ffd0d0;
  border-radius: 10px; padding: 24px;
  text-align: center; color: #C92A2A;
  font-size: 13.5px; margin-top: 0;
}

/* ── Cards section ──────────────────────────────────────────────────── */
.su-cards-section { margin-top: 4px; }
.su-loading { padding: 40px; text-align: center; color: #868E96; }

.su-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

/* ── Member card ────────────────────────────────────────────────────── */
.su-member-card {
  background: #fff;
  border: 1px solid #e8ecf2;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,.05);
  position: relative;
  transition: box-shadow .15s;
}
.su-member-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,.08); }

.su-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
  position: relative;
}
.su-owner-tag {
  background: #f0f4ff;
  color: #2563eb;
  font-size: 10.5px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 20px;
  letter-spacing: .4px;
}
.su-menu-btn {
  background: none; border: none; cursor: pointer;
  color: #9ca3af; padding: 4px; border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  transition: background .12s;
}
.su-menu-btn:hover { background: #f3f4f6; color: #374151; }

/* Dropdown */
.su-dropdown {
  position: absolute;
  top: 28px; right: 0;
  background: #fff;
  border: 1px solid #e4e8f0;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0,0,0,.12);
  padding: 6px;
  min-width: 160px;
  z-index: 100;
}
.su-dd-item {
  display: flex; align-items: center; gap: 8px;
  width: 100%; padding: 8px 10px;
  font-size: 13px; font-weight: 500;
  color: #374151; background: none; border: none;
  border-radius: 7px; cursor: pointer; text-align: left;
  transition: background .1s;
}
.su-dd-item:hover { background: #f8f9fc; }
.su-dd-item--warn { color: #b45309; }
.su-dd-item--warn:hover { background: #fffbeb; }
.su-dd-item--danger { color: #C92A2A; }
.su-dd-item--danger:hover { background: #fff5f5; }
.su-dd-divider { border: none; border-top: 1px solid #f0f2f7; margin: 4px 0; }

/* Avatar */
.su-card-avatar-wrap { display: flex; justify-content: center; margin-bottom: 14px; }
.su-card-avatar {
  width: 64px; height: 64px; border-radius: 50%;
  background: linear-gradient(135deg, #2563eb, #5e3dc7);
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 20px; font-weight: 700;
  overflow: hidden; flex-shrink: 0;
}
.su-card-avatar--img { background: none; }

.su-card-name {
  font-size: 15px; font-weight: 700; color: #111827;
  text-align: center; margin-bottom: 3px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.su-card-email {
  font-size: 12.5px; color: #6b7280;
  text-align: center; margin-bottom: 14px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.su-card-divider {
  border: none; border-top: 1px solid #f0f2f7; margin-bottom: 14px;
}

/* Meta rows */
.su-card-meta-row {
  display: flex; align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.su-card-meta-label {
  display: flex; align-items: center; gap: 6px;
  font-size: 12.5px; color: #9ca3af;
}
.su-card-meta-value { font-size: 13px; font-weight: 600; color: #111827; }
.su-card-joined {
  font-size: 11.5px; color: #9ca3af;
  margin-top: 10px; padding-top: 12px;
  border-top: 1px solid #f0f2f7;
}

/* ── Pills ──────────────────────────────────────────────────────────── */
.su-role-pill {
  display: inline-block;
  padding: 3px 10px; border-radius: 20px;
  font-size: 11.5px; font-weight: 600;
  white-space: nowrap;
}
.su-status-pill {
  display: inline-block;
  padding: 3px 10px; border-radius: 20px;
  font-size: 11.5px; font-weight: 600;
  white-space: nowrap;
}
.su-status--active   { background: #ebfbee; color: #2f9e44; }
.su-status--inactive { background: #f8f9fa; color: #868e96; }

/* ── Add New Member card ────────────────────────────────────────────── */
.su-add-card {
  background: #fff;
  border: 2px dashed #c5d0fa;
  border-radius: 16px;
  padding: 20px;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 8px; cursor: pointer;
  transition: border-color .15s, background .15s;
  min-height: 260px;
}
.su-add-card:hover { border-color: #2563eb; background: #f8f9ff; }
.su-add-card-icon {
  width: 60px; height: 60px; border-radius: 14px;
  background: #eef2ff;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 6px;
}
.su-add-card-title {
  font-size: 15px; font-weight: 700; color: #111827;
}
.su-add-card-sub {
  font-size: 12.5px; color: #6b7280;
  text-align: center; max-width: 180px;
}
.su-add-card-btn {
  margin-top: 8px;
  display: flex; align-items: center; gap: 6px;
  padding: 8px 18px; border-radius: 8px;
  border: 1.5px solid #2563eb; background: #fff;
  color: #2563eb; font-size: 13px; font-weight: 600;
  cursor: pointer; transition: background .12s;
}
.su-add-card-btn:hover { background: #eef2ff; }

/* ── Responsive ─────────────────────────────────────────────────────── */
@media (max-width: 768px) {
  .su-cards-grid { grid-template-columns: 1fr; gap: 14px; }
}
@media (max-width: 480px) {
  .cust-page { padding: 12px !important; }
}
</style>