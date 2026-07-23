<template>
  <aside class="bv-sidebar" :class="{ 'bv-sidebar-collapsed': collapsed }">

    <!-- Brand row -->
    <div class="bv-sidebar-brand">
      <span
        class="bv-sidebar-brand-mark"
        @click.stop="collapsed && $emit('toggle')"
        :style="collapsed ? 'cursor:pointer' : ''"
      >B</span>
      <span v-if="!collapsed" class="bv-sidebar-brand-text">Books</span>
      <!-- Desktop: collapse toggle -->
      <button class="bv-sidebar-collapse" @click.stop="$emit('toggle')" :title="collapsed ? 'Expand' : 'Collapse'">
        <IconSvg :name="collapsed ? 'chevR' : 'chevL'" :size="13" />
      </button>
      <!-- Mobile: close button -->
      <button class="bv-sidebar-close-mob" @click.stop="$emit('close-mobile')" aria-label="Close menu">
        <IconSvg name="x" :size="15" />
      </button>
    </div>

    <!-- Nav items -->
    <nav class="bv-sidebar-nav">
      <template v-for="group in navGroups" :key="group.section ?? '__root__'">

        <!-- Section header (only shown when sidebar is expanded) -->
        <div
          v-if="group.section && !collapsed"
          class="bv-sidebar-section"
          :class="{ 'bv-sidebar-section-active': isSectionActive(group) }"
          @click="toggleSection(group.section)"
        >
          <span>{{ group.section }}</span>
          <IconSvg
            :name="isSectionOpen(group.section) ? 'chevU' : 'chevD'"
            :size="10"
            class="bv-section-chev"
          />
        </div>

        <!-- Items — always show in collapsed mode (icons only), or when section is open -->
        <template v-if="collapsed || !group.section || isSectionOpen(group.section)">
          <a
            v-for="item in group.items"
            :key="item.path"
            :href="`#${item.path}`"
            class="bv-sidebar-item"
            :class="{ 'bv-sidebar-item-active': isActive(item.path) }"
            :ref="el => { if (el && isActive(item.path)) activeItemEl = el }"
            :title="collapsed ? item.label : ''"
            @click.prevent="goTo(item)"
          >
            <span class="bv-sidebar-icon"><IconSvg :name="item.icon" :size="15" /></span>
            <span v-if="!collapsed" class="bv-sidebar-label">{{ item.label }}</span>
          </a>
        </template>

      </template>
    </nav>

    <!-- User footer -->
    <div
      class="bv-sidebar-user"
      @click="goTo({ path: '/settings/profile' })"
      :title="collapsed ? (session.fullname || session.user) : ''"
    >
      <div class="bv-sidebar-avatar">{{ initials }}</div>
      <div v-if="!collapsed" class="bv-sidebar-user-info">
        <div class="bv-sidebar-user-name">{{ session.fullname || session.user }}</div>
        <div class="bv-sidebar-user-role">{{ role || 'Member' }}</div>
      </div>
    </div>

    <button class="bv-sidebar-logout" @click.stop="doLogout" :title="collapsed ? 'Sign out' : ''">
      <IconSvg name="logout" :size="14" />
      <span v-if="!collapsed">Sign out</span>
    </button>

  </aside>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import IconSvg from "../components/IconSvg.vue";
import { NAV } from "./nav.js";
import { usePermissions } from "../composables/usePermissions.js";
import { useConfirm } from "../composables/useConfirm.js";
import { session } from "../api/session.js";

const { confirm } = useConfirm();

defineProps({
  collapsed:  { type: Boolean, default: false },
  mobileOpen: { type: Boolean, default: false },
});
const emit = defineEmits(["toggle", "close-mobile"]);

const activeItemEl = ref(null);
const routeReady = ref(false);

const route  = useRoute();
const router = useRouter();
const { can, role } = usePermissions();

// ── Open section (accordion — only one open at a time) ───────────────
const SECTION_KEY = "books_sidebar_open_section";
const openSection = ref(null);

function getActiveSection() {
  return navGroups.value.find(g => g.section && g.items.some(i => isActive(i.path)))?.section ?? null;
}

onMounted(() => {
  router.isReady().then(() => {
    routeReady.value = true;

    // Open the section that contains the active route; fall back to saved
    const active = getActiveSection();
    if (active) {
      openSection.value = active;
    } else {
      try {
        const saved = localStorage.getItem(SECTION_KEY);
        openSection.value = saved || null;
      } catch {}
    }

    nextTick(() => {
      if (activeItemEl.value) {
        activeItemEl.value.scrollIntoView({ block: "nearest", behavior: "smooth" });
        activeItemEl.value.focus({ preventScroll: true });
      }
    });
  });
});

function toggleSection(section) {
  // If the section being closed is the active one, keep it open
  if (openSection.value === section) {
    const isActive_ = navGroups.value.find(g => g.section === section)?.items.some(i => isActive(i.path));
    if (isActive_) return; // don't allow closing active section
    openSection.value = null;
  } else {
    openSection.value = section;
  }
  try { localStorage.setItem(SECTION_KEY, openSection.value || ""); } catch {}
}

function isSectionOpen(section) {
  return openSection.value === section;
}

function isSectionActive(group) {
  return group.items.some(item => isActive(item.path));
}

// ── Initials ──────────────────────────────────────────────────────────
const initials = computed(() => {
  const n = (session.fullname || session.user || "?").trim();
  const parts = n.split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] || "") + (parts[1]?.[0] || "")).toUpperCase() || "?";
});

// ── Logout ────────────────────────────────────────────────────────────
async function doLogout() {
  const ok = await confirm({
    title: "Sign out?",
    body: "Are you sure you want to sign out of your account?",
    okLabel: "Sign Out",
    cancelLabel: "Cancel",
    okStyle: "danger",
  });
  if (!ok) return;
  try {
    const csrf = window.frappe?.csrf_token ||
      document.cookie.match(/csrf_token=([^;]+)/)?.[1] || "";
    await fetch("/api/method/logout", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Frappe-CSRF-Token": csrf,
      },
      body: csrf ? "csrf_token=" + encodeURIComponent(csrf) : "",
    });
  } catch {}
  window.location.replace("/login");
}

// ── Visible nav grouped by section ───────────────────────────────────
const navGroups = computed(() => {
  const groups = [];
  let current = null;
  for (const item of NAV) {
    if (item.section) {
      if (current) groups.push(current);
      current = { section: item.section, items: [] };
      continue;
    }
    if (!can(item.module)) continue;
    if (!current) current = { section: null, items: [] };
    current.items.push(item);
  }
  if (current && current.items.length) groups.push(current);
  return groups.filter(g => g.items.length);
});

// ── Routing ───────────────────────────────────────────────────────────
function isActive(path) {
  if (!routeReady.value) return false;
  if (path === "/") return route.path === "/";
  if (route.path === path) return true;
  if (!route.path.startsWith(path + "/")) return false;
  // Prefix match (e.g. an unlisted detail route like /invoices/INV-0001
  // under the "/invoices" nav item). Only stay active here if no OTHER
  // nav item is a more specific match for the current route — otherwise
  // a parent path like "/expenses" would light up alongside its own
  // sibling item "/expenses/categories".
  const betterMatch = NAV.some((i) => {
    if (!i.path || i.path === path || i.path.length <= path.length) return false;
    return route.path === i.path || route.path.startsWith(i.path + "/");
  });
  return !betterMatch;
}

function goTo(item) {
  router.push(item.path);
  emit("close-mobile");   // close mobile sidebar on any navigation
}

// When navigating to a new route, open that route's section automatically
watch(() => route.path, () => {
  if (!routeReady.value) return;
  const active = getActiveSection();
  if (active && active !== openSection.value) {
    openSection.value = active;
    try { localStorage.setItem(SECTION_KEY, active); } catch {}
  }
});
</script>