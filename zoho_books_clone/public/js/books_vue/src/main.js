import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import { bootstrapSession } from "./api/session.js";
import { usePermissions } from "./composables/usePermissions.js";
import "./shell.css";
import "./legacy-extras.css";
import "./styles/list.css";
import "./styles/view.css";
import "./styles/edit.css";
import "./styles/add.css";

// Bootstrap the session before mounting so usePermissions() and the API
// client see populated state synchronously after the await.
// bootstrapSession() returns false when it redirects to /login — in that
// case we must NOT mount the app, otherwise the router briefly renders the
// dashboard before the page navigation completes (the back-and-forth flash).
bootstrapSession().then((ok) => {
  if (ok === false) return;   // redirecting to login — do not mount
  const app = createApp(App);
  // Global template helpers for role/module gating (backend enforces the same).
  // Usage in any template: :disabled="!$canWrite('invoices')"
  // Phase 4: granular per-action helpers on top of the legacy blanket ones —
  // :disabled="!$canCreate('banking')" / "!$canEdit('banking')" / "!$canDelete('banking')".
  const { canWrite, can, canCreate, canEdit, canDelete } = usePermissions();
  app.config.globalProperties.$canWrite  = canWrite;
  app.config.globalProperties.$can       = can;
  app.config.globalProperties.$canCreate = canCreate;
  app.config.globalProperties.$canEdit   = canEdit;
  app.config.globalProperties.$canDelete = canDelete;
  app.use(router);
  app.mount("#books-app");
});