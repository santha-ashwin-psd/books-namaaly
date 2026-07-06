// Vue router for the new bundle. Only routes the Vue bundle owns are listed
// here; everything else is handled by the legacy SPA via the cutover loader
// in books.html. New phases append routes to this table and to
// window.BOOKS_VUE_ROUTES.

import { createRouter, createWebHistory } from "vue-router";
import PhaseAHome           from "./pages/PhaseAHome.vue";
import Dashboard            from "./pages/Dashboard.vue";
import Customers            from "./pages/Customers.vue";
import CustomerProfile      from "./pages/CustomerProfile.vue";
import Vendors              from "./pages/Vendors.vue";
import InventoryItems       from "./pages/InventoryItems.vue";
import InventoryItemView    from "./pages/InventoryItemView.vue";
import InventoryItemGroups  from "./pages/InventoryItemGroups.vue";
import InventoryWarehouses  from "./pages/InventoryWarehouses.vue";
import InventoryBatches     from "./pages/InventoryBatches.vue";
import InventoryVariants    from "./pages/InventoryVariants.vue";
import InventorySettings    from "./pages/InventorySettings.vue";
import OpeningStockBatchEntry from "./pages/OpeningStockBatchEntry.vue";
import SettingsProfile       from "./pages/SettingsProfile.vue";
import SettingsCompany       from "./pages/SettingsCompany.vue";
import SettingsNumberSeries  from "./pages/SettingsNumberSeries.vue";
import SettingsPaymentTerms  from "./pages/SettingsPaymentTerms.vue";
import SettingsUsers         from "./pages/SettingsUsers.vue";
import SettingsEmail         from "./pages/SettingsEmail.vue";
import SettingsEmailTemplates from "./pages/SettingsEmailTemplates.vue";
import SettingsRoles         from "./pages/SettingsRoles.vue";
import SettingsAuditLog      from "./pages/SettingsAuditLog.vue";
import SettingsOrganization  from "./pages/SettingsOrganization.vue";
import SettingsSecurity      from "./pages/SettingsSecurity.vue";
import SettingsIntegrations  from "./pages/SettingsIntegrations.vue";
import SettingsSSO           from "./pages/SettingsSSO.vue";
// import SettingsCurrencyExchange from "./pages/SettingsCurrencyExchange.vue"; // INR-only: hidden
import ChartOfAccounts        from "./pages/ChartOfAccounts.vue";
import JournalEntries         from "./pages/JournalEntries.vue";
import OpeningBalances        from "./pages/OpeningBalances.vue";
import CostCenters            from "./pages/CostCenters.vue";
import FiscalYears            from "./pages/FiscalYears.vue";
import Invoices               from "./pages/Invoices.vue";
import Quotes                 from "./pages/Quotes.vue";
import SalesOrders            from "./pages/SalesOrders.vue";
import CreditNotes            from "./pages/CreditNotes.vue";
import Bills                  from "./pages/Bills.vue";
import PurchaseOrders         from "./pages/PurchaseOrders.vue";
import Expenses               from "./pages/Expenses.vue";
import Payments               from "./pages/Payments.vue";
import DebitNotes             from "./pages/DebitNotes.vue";
import Recurring              from "./pages/Recurring.vue";
import EwayBills              from "./pages/EwayBills.vue";
import BankAccounts           from "./pages/BankAccounts.vue";
import BankTransactions       from "./pages/BankTransactions.vue";
import BankReconciliation     from "./pages/BankReconciliation.vue";
import BankTransfers          from "./pages/BankTransfers.vue";
import BankCheques            from "./pages/BankCheques.vue";
import BankCash               from "./pages/BankCash.vue";
import StockEntries           from "./pages/StockEntries.vue";
import InventoryAdjustments    from "./pages/InventoryAdjustments.vue";
import StockLedger            from "./pages/StockLedger.vue";
import StockValuation         from "./pages/StockValuation.vue";
import ReorderAlerts          from "./pages/ReorderAlerts.vue";
import GSTReturn1             from "./pages/GSTReturn1.vue";
import GSTReturn3B            from "./pages/GSTReturn3B.vue";
import EInvoice               from "./pages/EInvoice.vue";
import TDS                    from "./pages/TDS.vue";
import TaxTemplates           from "./pages/TaxTemplates.vue";
import Reports                from "./pages/Reports.vue";
import PriceLists             from "./pages/PriceLists.vue";
import RecurringBills         from "./pages/RecurringBills.vue";
import BulkImport             from "./pages/BulkImport.vue";
import DeliveryChallans       from "./pages/DeliveryChallans.vue";
import ProformaInvoices       from "./pages/ProformaInvoices.vue";
import PurchaseReceipts       from "./pages/PurchaseReceipts.vue";
import QualityInspections     from "./pages/QualityInspections.vue";
import QCTemplates            from "./pages/QCTemplates.vue";

import { useToast } from "./composables/useToast.js";
import { usePermissions } from "./composables/usePermissions.js";
import { session } from "./api/session.js";

const routes = [
  {
    path: "/",
    redirect: "/dashboard",
  },
  {
    path: "/dashboard",
    name: "dashboard",
    component: Dashboard,
    meta: { module: null },
  },
  {
    path: "/books",
    redirect: "/dashboard",
  },
  {
    path: "/home",
    name: "home",
    component: PhaseAHome,
    meta: { module: null },
  },
  {
    path: "/customers",
    name: "customers",
    component: Customers,
    meta: { module: "customers" },
  },
  {
    path: "/customers/:name",
    name: "customer-profile",
    component: CustomerProfile,
    meta: { module: "customers" },
  },
  {
    path: "/vendors",
    name: "vendors",
    component: Vendors,
    meta: { module: "customers" },  // Vendors share the customers module flag in Books Company Member
  },
  {
    path: "/inventory/items",
    name: "inventory-items",
    component: InventoryItems,
    meta: { module: "inventory" },
  },
  {
    path: "/inventory/items/:itemCode",
    name: "item-view",
    component: InventoryItemView,
    meta: { module: "inventory" },
  },
  {
    path: "/inventory/item-groups",
    name: "inventory-item-groups",
    component: InventoryItemGroups,
    meta: { module: "inventory" },
  },
  {
    path: "/inventory/warehouses",
    name: "inventory-warehouses",
    component: InventoryWarehouses,
    meta: { module: "inventory" },
  },
  {
    path: "/inventory/settings",
    name: "inventory-settings",
    component: InventorySettings,
    meta: { module: "inventory" },
  },
  {
    path: "/settings/profile",
    name: "settings-profile",
    component: SettingsProfile,
    meta: { module: null },  // every user can edit their own profile
  },
  {
    path: "/settings/company",
    name: "settings-company",
    component: SettingsCompany,
    meta: { module: "admin" },
  },
  {
    path: "/settings/number-series",
    name: "settings-number-series",
    component: SettingsNumberSeries,
    meta: { module: "admin" },
  },
  {
    path: "/settings/payment-terms",
    name: "settings-payment-terms",
    component: SettingsPaymentTerms,
    meta: { module: "admin" },
  },
  {
    path: "/settings/users",
    name: "settings-users",
    component: SettingsUsers,
    meta: { module: "admin" },
  },
  {
    path: "/settings/email",
    name: "settings-email",
    component: SettingsEmail,
    meta: { module: "admin" },
  },
  {
    path: "/settings/email-templates",
    name: "settings-email-templates",
    component: SettingsEmailTemplates,
    meta: { module: "admin" },
  },
  { path: "/settings/roles",             name: "settings-roles",        component: SettingsRoles,         meta: { module: "admin" } },
  { path: "/settings/audit-log",         name: "settings-audit-log",    component: SettingsAuditLog,      meta: { module: "admin" } },
  { path: "/settings/organization",      name: "settings-organization", component: SettingsOrganization,  meta: { module: "admin" } },
  { path: "/settings/security",          name: "settings-security",     component: SettingsSecurity,      meta: { module: null    } },
  { path: "/settings/sso",              name: "settings-sso",          component: SettingsSSO,            meta: { module: "admin" } },
  { path: "/settings/integrations",      name: "settings-integrations", component: SettingsIntegrations,  meta: { module: "admin" } },
  // { path: "/settings/currency-exchange", name: "settings-currency", component: SettingsCurrencyExchange, meta: { module: "admin" } }, // INR-only: hidden
  { path: "/accounting/chart-of-accounts", name: "chart-of-accounts", component: ChartOfAccounts,  meta: { module: "accounts" } },
  { path: "/accounting/journal-entries",   name: "journal-entries",   component: JournalEntries,   meta: { module: "accounts" } },
  { path: "/accounting/opening-balances",  name: "opening-balances",  component: OpeningBalances,  meta: { module: "accounts" } },
  { path: "/accounting/cost-centers",      name: "cost-centers",      component: CostCenters,      meta: { module: "accounts" } },
  { path: "/accounting/fiscal-years",      name: "fiscal-years",      component: FiscalYears,      meta: { module: "accounts" } },
  { path: "/invoices",          name: "invoices",         component: Invoices,       meta: { module: "invoices" } },
  { path: "/quotes",            name: "quotes",           component: Quotes,         meta: { module: "invoices" } },
  { path: "/sales-orders",      name: "sales-orders",     component: SalesOrders,    meta: { module: "invoices" } },
  { path: "/credit-notes",      name: "credit-notes",     component: CreditNotes,    meta: { module: "invoices" } },
  { path: "/purchases",         name: "purchases",        component: Bills,          meta: { module: "bills"    } },
  { path: "/purchase-orders",   name: "purchase-orders",  component: PurchaseOrders, meta: { module: "bills"    } },
  { path: "/expenses",          name: "expenses",         component: Expenses,       meta: { module: "bills"    } },
  { path: "/payments",          name: "payments",         component: Payments,       meta: { module: "payments" } },
  { path: "/payments-received", name: "payments-received",component: Payments,       meta: { module: "payments" } },
  { path: "/debit-notes",       name: "debit-notes",      component: DebitNotes,     meta: { module: "bills"    } },
  { path: "/recurring-bills",   name: "recurring-bills",  component: RecurringBills, meta: { module: "bills"    } },
  { path: "/recurring",         name: "recurring",        component: Recurring,      meta: { module: "invoices" } },
  { path: "/eway-bills",        name: "eway-bills",       component: EwayBills,      meta: { module: "invoices" } },
  { path: "/banking/accounts",       name: "banking-accounts",       component: BankAccounts,       meta: { module: "accounts" } },
  { path: "/banking/transactions",   name: "banking-transactions",   component: BankTransactions,   meta: { module: "accounts" } },
  { path: "/banking/reconciliation", name: "banking-reconciliation", component: BankReconciliation, meta: { module: "accounts" } },
  { path: "/banking/transfers",      name: "banking-transfers",      component: BankTransfers,      meta: { module: "accounts" } },
  { path: "/banking/cheques",        name: "banking-cheques",        component: BankCheques,        meta: { module: "accounts" } },
  { path: "/banking/cash",           name: "banking-cash",           component: BankCash,           meta: { module: "accounts" } },
  { path: "/inventory/stock-entries",  name: "stock-entries",   component: StockEntries,   meta: { module: "inventory" } },
  { path: "/inventory/opening-stock",  name: "opening-stock",   component: OpeningStockBatchEntry, meta: { module: "inventory" } },
  { path: "/inventory/adjustments",    name: "inventory-adjustments", component: InventoryAdjustments, meta: { module: "inventory" } },
  { path: "/inventory/stock-ledger",   name: "stock-ledger",    component: StockLedger,    meta: { module: "inventory" } },
  { path: "/inventory/valuation",      name: "stock-valuation", component: StockValuation, meta: { module: "inventory" } },
  { path: "/inventory/reorder-alerts", name: "reorder-alerts",  component: ReorderAlerts,  meta: { module: "inventory" } },
  { path: "/inventory/price-lists",    name: "price-lists",     component: PriceLists,     meta: { module: "inventory" } },
  { path: "/inventory/batches",        name: "inventory-batches", component: InventoryBatches, meta: { module: "inventory" } },
  {
    path: "/inventory/items/:template/variants",
    name: "inventory-variants",
    component: InventoryVariants,
    meta: { module: "inventory" },
  },
  { path: "/gst/gstr1",    name: "gstr1",    component: GSTReturn1,  meta: { module: "accounts" } },
  { path: "/gst/gstr3b",   name: "gstr3b",   component: GSTReturn3B, meta: { module: "accounts" } },
  { path: "/gst/einvoice", name: "einvoice", component: EInvoice,    meta: { module: "invoices" } },
  { path: "/gst/tds",      name: "tds",      component: TDS,         meta: { module: "accounts" } },
  { path: "/gst/tax-templates", name: "tax-templates", component: TaxTemplates, meta: { module: "taxes" } },
  { path: "/reports",      name: "reports",  component: Reports,     meta: { module: null       } },
  { path: "/bulk-import",        name: "bulk-import",       component: BulkImport,       meta: { module: "admin"    } },
  { path: "/delivery-challans",   name: "delivery-challans",   component: DeliveryChallans,   meta: { module: "invoices" } },
  { path: "/proforma-invoices",   name: "proforma-invoices",   component: ProformaInvoices,   meta: { module: "invoices" } },
  { path: "/purchase-receipts",   name: "purchase-receipts",   component: PurchaseReceipts,   meta: { module: "bills"    } },
  // Quality
  { path: "/quality/inspections", name: "quality-inspections", component: QualityInspections, meta: { module: "inventory" } },
  { path: "/quality/templates",   name: "quality-templates",   component: QCTemplates,         meta: { module: "inventory" } },
  // Future phases append entries here.
  {
    path: "/:pathMatch(.*)*",
    name: "not-found",
    component: PhaseAHome,
    meta: { module: null, fallback: true },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to) => {
  // Auth: bootstrapSession() either populated session.ready or redirected.
  if (!session.ready) return false;

  const { can } = usePermissions();
  if (to.meta?.module && !can(to.meta.module)) {
    useToast().error(`You don't have access to "${to.name || to.path}".`);
    return { path: "/dashboard" };
  }
  return true;
});

export default router;