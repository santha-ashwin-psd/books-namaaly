<template>
  <router-link v-if="to" :to="to" target="_blank" class="doc-link" :class="{ mono: monoStyle }" @click.stop>
    <slot>{{ name }}</slot>
  </router-link>
  <span v-else class="doc-link-disabled" :class="{ mono: monoStyle }">
    <slot>{{ name }}</slot>
  </span>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  /** Frappe doctype name, e.g. "Sales Invoice" */
  doctype: { type: String, required: true },
  /** Record name, e.g. "INV-2026-00072" */
  name:    { type: String, default: "" },
  /** Style toggle — true → monospace blue (default); false → inherit parent style */
  monoStyle: { type: Boolean, default: true },
});

/**
 * Central mapping of Frappe doctypes → SPA routes. Anywhere a clickable ID
 * appears in a drawer, this is the one source of truth for where it goes.
 * Returns null for doctypes we don't have a list page for — the link is
 * rendered as plain text in that case.
 */
/**
 * Doctype routing convention:
 *   - "list:/path"     → opens the list page with ?open=NAME (auto-opens drawer)
 *   - "path:/path"     → opens a dedicated profile page using :name path param
 */
const DOCTYPE_ROUTE = {
  "Sales Invoice":     "list:/invoices",
  "Purchase Invoice":  "list:/purchases",
  "Quotation":         "list:/quotes",
  "Sales Order":       "list:/sales-orders",
  "Purchase Order":    "list:/purchase-orders",
  "Payment Entry":     "list:/payments-received",
  "Bank Transaction":  "list:/banking/transactions",
  "Credit Note":       "list:/credit-notes",
  "Debit Note":        "list:/debit-notes",
  "Delivery Note":     "list:/delivery-challans",
  "Purchase Receipt":  "list:/purchase-receipts",
  "Auto Repeat":       "list:/recurring",
  "E Way Bill":        "list:/eway-bills",
  "Customer":          "path:/customers",
  "Supplier":          "list:/vendors",
  "Item":              "list:/inventory/items",
  "Journal Entry":     "list:/accounting/journal-entries",
  "Expense":           "list:/expenses",
  "Landed Cost Voucher": "path:/purchasing/landed-cost-vouchers",
  "Stock Entry":       "list:/inventory/stock-entries",
  "BOM":               "path:/manufacturing/bom",
  "Work Order":        "path:/manufacturing/work-order",
  "Job Card":          "path:/manufacturing/job-card",
  "Packing Slip":      "path:/manufacturing/packing-slip",
  "Production Plan":   "path:/manufacturing/production-plan",
  "Material Request":  "path:/manufacturing/material-request",
  "Routing":           "path:/manufacturing/routing",
  "Workstation":       "path:/manufacturing/workstation",
};

const to = computed(() => {
  const spec = DOCTYPE_ROUTE[props.doctype];
  if (!spec || !props.name) return null;
  const [kind, base] = spec.split(":");
  if (kind === "path") {
    // Profile pages: /customers/CUST-2026-00004
    return { path: `${base}/${encodeURIComponent(props.name)}` };
  }
  // List pages: /invoices?open=INV-2026-00072
  return { path: base, query: { open: props.name } };
});
</script>

<style scoped>
.doc-link {
  color: #2563eb;
  font-weight: 600;
  text-decoration: none;
  border-bottom: 1px dashed transparent;
  cursor: pointer;
  transition: color .15s, border-color .15s;
}
.doc-link:hover { color: #1d4ed8; border-bottom-color: #2563eb; }
.doc-link.mono {font-size: 13px; }

.doc-link-disabled {
  color: #0f172a;
  font-weight: 600;
}
.doc-link-disabled.mono {  font-size: 13px; }
</style>