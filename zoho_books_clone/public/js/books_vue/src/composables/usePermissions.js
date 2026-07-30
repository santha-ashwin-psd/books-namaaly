// Permission gating. Reads from the reactive session populated by
// bootstrapSession() at boot time; no extra round trip needed.

import { computed } from "vue";
import { session } from "../api/session.js";

// Mirrors utils/access.py LEVELS — each level implies everything below it.
const LEVELS = ["None", "View", "Create", "Edit", "Delete"];
function _levelAtLeast(level, threshold) {
  return LEVELS.indexOf(level) >= LEVELS.indexOf(threshold);
}

export function usePermissions() {
  const flags      = computed(() => session.permissions || {});
  const role       = computed(() => session.permissions?.books_role || "");
  const isAdmin    = computed(() => !!session.permissions?.is_company_admin);
  // Read-only everywhere (mirrors the backend). Prefer the server-provided
  // read_only flag; fall back to the role name for older sessions.
  const isReadonly = computed(() =>
    session.permissions?.read_only === true ||
    session.permissions?.books_role === "Books Viewer");

  function can(module) {
    if (!module) return true;       // routes without a module gate (e.g. dashboard) pass through.
    if (isAdmin.value) return true; // admins get everything; backend mirrors this.
    // Was: raw mod_<module> boolean flag only, which ignores levels entirely --
    // so an explicit lvl_<module>="None" (Permission Levels dropdown) never
    // blocked page navigation/sidebar visibility even after levels_customized
    // made it authoritative for canCreate/canEdit/canDelete. session.permissions
    // .levels[module] is resolved server-side by utils/access.py._membership(),
    // which for untouched members mirrors the same true/false the boolean flag
    // gave (additive merge), and for customized members honors an explicit
    // "None". So this is a strict correctness fix, not a behavior change for
    // any member who hasn't used the granular dropdown.
    return (session.permissions?.levels?.[module] || "None") !== "None";
  }

  // Whether the user may create/edit/delete in `module`. Admins → yes; read-only
  // roles → no; everyone else needs the module flag. Backend enforces the same,
  // so this is for UX (disable/grey out) only.
  function canWrite(module) {
    if (isAdmin.value) return true;
    if (isReadonly.value) return false;
    return can(module);
  }

  // ── Granular (Phase 3) ──────────────────────────────────────────────────
  // Reads session.permissions.levels[module], populated by
  // get_books_session() from utils/access.py's _membership() — the same
  // engine the backend's assert_can()/can_create()/can_edit()/can_delete()
  // use. These are UX hints only (disable/hide a button); the backend is
  // still the real enforcement point for every one of these actions.
  //
  // Naming note for integrators: some pages (e.g. PurchaseOrders.vue,
  // DeliveryChallans.vue) already define their own local canEdit(row)/
  // canDelete(row) functions that check a *document's* state (docstatus
  // etc.), not the user's *module* permission. If a page needs both, alias
  // one on import: `const { canEdit: canEditModule } = usePermissions()`.
  function levelOf(module) {
    if (isAdmin.value) return "Delete";
    return session.permissions?.levels?.[module] || "None";
  }
  function canCreate(module) {
    if (isAdmin.value) return true;
    return _levelAtLeast(levelOf(module), "Create");
  }
  function canEdit(module) {
    if (isAdmin.value) return true;
    return _levelAtLeast(levelOf(module), "Edit");
  }
  function canDelete(module) {
    if (isAdmin.value) return true;
    return _levelAtLeast(levelOf(module), "Delete");
  }

  return {
    flags, role, isAdmin, isReadonly, can, canWrite,
    levelOf, canCreate, canEdit, canDelete,
  };
}