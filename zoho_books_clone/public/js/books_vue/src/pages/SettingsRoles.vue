<template>
  <div class="r-page">
    <div class="r-head">
      <div>
        <div class="r-title">Roles &amp; Permissions</div>
        <div class="r-sub">Built-in roles ship with the app. Per-user module access is editable from Users.</div>
      </div>
      <button class="r-cta" @click="goUsers"><span v-html="icon('users',13)"></span> Manage Users</button>
    </div>

    <div v-if="loading" class="r-loading">Loading roles…</div>
    <div v-else class="r-grid">
      <div v-for="role in ROLES" :key="role.name" class="r-card">
        <div class="r-card-head">
          <div class="r-card-head-left">
            <span class="r-badge" :style="{background: role.bg, color: role.color}">{{ role.name }}</span>
            <span class="r-card-desc">{{ role.desc }}</span>
          </div>
          <span class="r-count" :class="userCount(role.name)===0?'zero':''">{{ userCount(role.name) }} {{ userCount(role.name)===1?'user':'users' }}</span>
        </div>

        <div class="r-modules">
          <div v-for="m in MODULES" :key="m.key" class="r-mod" :class="role.perms[m.key]?'on':''">
            <span v-html="icon(role.perms[m.key]?'check':'lock',11)"></span> {{ m.lbl }}
          </div>
        </div>

        <div v-if="usersIn(role.name).length" class="r-users">
          <div v-for="u in usersIn(role.name)" :key="u.email" class="r-user" :title="u.email + (u.enabled?'':' (disabled)')">
            <span class="r-avatar" :style="{opacity: u.enabled?1:.45}">{{ initials(u.full_name||u.email) }}</span>
            <div class="r-user-meta">
              <div class="r-user-name" :style="{opacity: u.enabled?1:.55}">{{ u.full_name || u.email }}<span v-if="u.is_company_admin" class="r-tag-admin">admin</span></div>
              <div class="r-user-sub">{{ u.email }}<span v-if="!u.enabled" class="r-tag-off">disabled</span></div>
            </div>
          </div>
        </div>
        <div v-else class="r-empty">No users in this role.</div>
      </div>
    </div>

    <div class="r-note">
      <span v-html="icon('info',13)"></span>
      Want a custom role with a different module mix? Use the Users page to set <strong>per-user module access</strong> on top of any built-in role — that covers most custom-role needs without needing a separate role definition.
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { apiGET } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";

const { toast } = useToast();
const router = useRouter();
const members = ref([]);
const loading = ref(true);

// Cosmetic display order only. Name/description/color/module-flags for each
// role now come from the backend (get_role_matrix) so this page can't drift
// from what utils/access.py and the Users page actually enforce.
const ROLE_ORDER = ["Books Admin", "Accountant", "Books Manager", "Books Viewer"];
const roleMatrix = ref({});

const MODULES = [
  { key: "invoices",  lbl: "Sales / Invoicing" },
  { key: "bills",     lbl: "Purchases / Bills" },
  { key: "payments",  lbl: "Payments" },
  { key: "banking",   lbl: "Banking" },
  { key: "inventory", lbl: "Inventory" },
  { key: "accounts",  lbl: "Accounting" },
  { key: "reports",   lbl: "Reports" },
  { key: "customers", lbl: "Customers & Suppliers" },
  { key: "taxes",     lbl: "Taxes & GST" },
  { key: "admin",     lbl: "Admin / Settings" },
];

const ROLES = computed(() =>
  ROLE_ORDER.map(name => {
    const r = roleMatrix.value[name] || {};
    return {
      name,
      desc: r.desc || "",
      color: r.color || "#868E96",
      bg: r.bg || "#F1F3F5",
      perms: r.perms || {},
    };
  })
);

async function load() {
  loading.value = true;
  try {
    const [membersRes, matrixRes] = await Promise.all([
      apiGET("zoho_books_clone.api.admin.get_company_members"),
      apiGET("zoho_books_clone.api.admin.get_role_matrix"),
    ]);
    members.value = Array.isArray(membersRes) ? membersRes : (membersRes?.message || []);
    roleMatrix.value = matrixRes?.message || matrixRes || {};
  } catch (e) { toast.error(e.message || "Failed to load roles"); }
  finally { loading.value = false; }
}

function usersIn(roleName) { return members.value.filter(m => (m.books_role || "") === roleName); }
function userCount(roleName) { return usersIn(roleName).length; }
function initials(s) { const p = (s || "").trim().split(/\s+/); return ((p[0]?.[0] || "") + (p[1]?.[0] || "")).toUpperCase() || (s||"?")[0]?.toUpperCase(); }
function goUsers() { router.push({ name: "settings-users" }); }

onMounted(load);
</script>

<style scoped>
.r-page{display:flex;flex-direction:column;gap:18px;padding:24px;}
.r-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap;}
.r-title{font-size:18px;font-weight:700;color:#0f172a;}
.r-sub{font-size:12.5px;color:#64748b;margin-top:2px;max-width:680px;line-height:1.5;}
.r-cta{display:inline-flex;align-items:center;gap:6px;background:#2563eb;color:#fff;border:none;border-radius:8px;padding:9px 14px;font-size:13px;font-weight:600;cursor:pointer;}
.r-cta:hover{background:#1d4ed8;}
.r-loading{padding:40px;text-align:center;color:#94a3b8;}

.r-grid{display:grid;grid-template-columns:repeat(auto-fill, minmax(380px, 1fr));gap:14px;}
.r-card{background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:18px;display:flex;flex-direction:column;gap:14px;}
.r-card-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;}
.r-card-head-left{display:flex;flex-direction:column;gap:6px;}
.r-badge{display:inline-flex;align-items:center;padding:4px 11px;border-radius:20px;font-size:12px;font-weight:700;align-self:flex-start;}
.r-card-desc{font-size:12.5px;color:#475569;line-height:1.5;}
.r-count{display:inline-flex;align-items:center;background:#f1f5f9;color:#334155;border-radius:20px;padding:3px 10px;font-size:11.5px;font-weight:700;white-space:nowrap;}
.r-count.zero{background:#fef2f2;color:#dc2626;}

.r-modules{display:grid;grid-template-columns:repeat(2, 1fr);gap:6px;}
.r-mod{display:flex;align-items:center;gap:6px;padding:5px 9px;border-radius:7px;font-size:11.5px;font-weight:600;background:#f8fafc;color:#94a3b8;border:1px solid #eef2f7;}
.r-mod.on{background:#ecfdf5;color:#16a34a;border-color:#bbf7d0;}
.r-mod span{display:inline-flex;}

.r-users{display:flex;flex-direction:column;gap:6px;padding-top:12px;border-top:1px dashed #e5e7eb;}
.r-user{display:flex;align-items:center;gap:10px;}
.r-avatar{width:30px;height:30px;border-radius:50%;background:linear-gradient(135deg,#2563eb,#1d4ed8);color:#fff;font-size:11.5px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0;}
.r-user-meta{display:flex;flex-direction:column;min-width:0;}
.r-user-name{font-size:13px;font-weight:600;color:#0f172a;display:flex;align-items:center;gap:6px;}
.r-user-sub{font-size:11px;color:#94a3b8;display:flex;align-items:center;gap:6px;}
.r-tag-admin{background:#dbeafe;color:#1d4ed8;font-size:9px;font-weight:700;padding:1px 6px;border-radius:8px;text-transform:uppercase;}
.r-tag-off{background:#fee2e2;color:#dc2626;font-size:9px;font-weight:700;padding:1px 6px;border-radius:8px;text-transform:uppercase;}
.r-empty{font-size:12px;color:#94a3b8;padding:10px 12px;background:#f8fafc;border:1px dashed #e5e7eb;border-radius:8px;text-align:center;}

.r-note{display:flex;gap:10px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:12px 14px;font-size:12.5px;color:#1e3a8a;line-height:1.55;}
.r-note span{color:#2563eb;flex-shrink:0;margin-top:1px;display:inline-flex;}
</style>