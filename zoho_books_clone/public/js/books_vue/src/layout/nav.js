// Sidebar nav table. Single source of truth for both:
//   1. The sidebar (which items to render, gated by `module`),
//   2. The router (route.meta.module is hydrated from this list during phase rollout).
//
// `module` is a Books Company Member flag key (without the `mod_` prefix), or
// null for routes that have no permission gate (dashboard).
//
// New phases append entries here. The cutover decision (Vue vs legacy) is in
// books.html via window.BOOKS_VUE_ROUTES — items not in that list still appear
// in the sidebar but trigger a real navigation when clicked.

export const NAV = [
  { path: "/dashboard",                     label: "Dashboard",        icon: "grid",       module: null         },

  { section: "Sales" },
  { path: "/quotes",                        label: "Quotes",       icon: "quote",      module: "invoices"   },
  { path: "/sales-orders",                  label: "Sales Orders",     icon: "order",      module: "invoices"   },
  { path: "/invoices",                      label: "Invoices",         icon: "file",       module: "invoices"   },
  { path: "/recurring",                     label: "Recurring",        icon: "recurring",  module: "invoices"   },
  { path: "/delivery-challans",             label: "Delivery Challans",icon: "truck",      module: "invoices"   },
  { path: "/payments-received",             label: "Payments Received",icon: "rupee",      module: "payments"   },
  { path: "/credit-notes",                  label: "Credit Notes",     icon: "creditnote", module: "invoices"   },
  // { path: "/proforma-invoices",             label: "Proforma Invoices",icon: "file",       module: "invoices"   },
  { path: "/eway-bills",                    label: "E-Way Bills",      icon: "truck",      module: "invoices"   },

  { section: "Purchases" },
  { path: "/expenses",                      label: "Expenses",         icon: "expense",    module: "bills"      },
  { path: "/purchase-orders",               label: "Purchase Orders",  icon: "purchase",   module: "bills"      },
  { path: "/purchases",                     label: "Bills",            icon: "fileplus",   module: "bills"      },
  { path: "/recurring-bills",               label: "Recurring Bills",  icon: "recurring",  module: "bills"      },
  { path: "/purchase-receipts",             label: "Purchase Receipts",icon: "purchase",   module: "bills"      },
  { path: "/payments",                      label: "Payments Made",    icon: "payment",    module: "payments"   },
  { path: "/debit-notes",                   label: "Debit Notes",      icon: "creditnote", module: "bills"      },

  { section: "Contacts" },
  { path: "/customers",                     label: "Customers",        icon: "users",      module: "customers"  },
  { path: "/vendors",                       label: "Vendors",          icon: "vendors",    module: "customers"  },
  { path: "/sales-persons",                 label: "Sales Persons",    icon: "badge",      module: "customers"  },

  { section: "Banking" },
  { path: "/banking/accounts",              label: "Bank Accounts",    icon: "bank",       module: "banking"    },
  { path: "/banking/transactions",          label: "Transactions",     icon: "ledger",     module: "banking"    },
  { path: "/banking/reconciliation",        label: "Reconciliation",   icon: "balance",    module: "banking"    },
  { path: "/banking/transfers",             label: "Transfers",        icon: "share",      module: "banking"    },
  { path: "/banking/cheques",               label: "Cheques",          icon: "file",       module: "banking"    },
  { path: "/banking/cash",                  label: "Cash",             icon: "cash",       module: "banking"    },

  { section: "Accounting" },
  { path: "/accounting/chart-of-accounts",  label: "Chart of Accounts",icon: "coa",        module: "accounts"   },
  { path: "/accounting/journal-entries",    label: "Journal Entries",  icon: "journal",    module: "accounts"   },
  { path: "/accounting/opening-balances",   label: "Opening Balances", icon: "opening",    module: "accounts"   },
  { path: "/accounting/cost-centers",       label: "Cost Centers",     icon: "costcenter", module: "accounts"   },
  { path: "/accounting/fiscal-years",       label: "Fiscal Years",     icon: "fiscal",     module: "accounts"   },

  { section: "Inventory" },
  { path: "/inventory/items",               label: "Items",            icon: "box",        module: "inventory"  },
  { path: "/inventory/item-groups",         label: "Item Groups",      icon: "folder",     module: "inventory"  },
  { path: "/inventory/warehouses",          label: "Warehouses",       icon: "warehouse",  module: "inventory"  },
  { path: "/inventory/opening-stock",       label: "Opening Stock",    icon: "opening",    module: "inventory"  },
  { path: "/inventory/stock-entries",       label: "Stock Entries",    icon: "stack",      module: "inventory"  },
  { path: "/inventory/adjustments",         label: "Stock Adjustments", icon: "repeat",    module: "inventory"  },
  { path: "/inventory/stock-ledger",        label: "Stock Ledger",     icon: "ledger",     module: "inventory"  },
  { path: "/inventory/valuation",           label: "Valuation",        icon: "chart",      module: "inventory"  },
  { path: "/inventory/reorder-alerts",      label: "Reorder Alerts",   icon: "alert",      module: "inventory"  },
  { path: "/inventory/price-lists",         label: "Price Lists",      icon: "rupee",      module: "inventory"  },
  { path: "/inventory/batches",             label: "Batch Tracking",   icon: "qr",         module: "inventory"  },
  { path: "/inventory/settings",            label: "Settings",         icon: "gear",       module: "inventory"  },

  // { section: "Quality" },
  // { path: "/quality/inspections",           label: "Inspections",      icon: "shield",     module: "inventory"  },
  // { path: "/quality/templates",             label: "QC Templates",     icon: "file",       module: "inventory"  },
  // { path: "/quality/approvals",             label: "QC Approvals",     icon: "check",      module: "inventory"  },

  { section: "Manufacturing" },
  { path: "/manufacturing/bom",               label: "Bill of Materials", icon: "box",        module: "inventory" },
  { path: "/manufacturing/operation",         label: "Operations",       icon: "stack",      module: "inventory" },
  { path: "/manufacturing/workstation",       label: "Workstations",     icon: "gear",       module: "inventory" },
  { path: "/manufacturing/workstation-type",  label: "Workstation Types",icon: "badge",      module: "inventory" },
  { path: "/manufacturing/routing",           label: "Routing",          icon: "recurring",  module: "inventory" },
  { path: "/manufacturing/work-order",        label: "Work Orders",      icon: "order",      module: "inventory" },
  { path: "/manufacturing/job-card",          label: "Job Cards",        icon: "stack",      module: "inventory" },
  { path: "/manufacturing/production-plan",   label: "Production Plan",  icon: "chart",      module: "inventory" },
  { path: "/manufacturing/material-request",  label: "Material Requests", icon: "purchase",   module: "inventory" },
  { path: "/manufacturing/packing-slip",      label: "Packing Slips",     icon: "box",        module: "inventory" },
  { path: "/manufacturing/alternative-item", label: "Alternative Items",   icon: "stack", module: "inventory" },
  { path: "/manufacturing/reports",          label: "Mfg Reports",         icon: "chart",      module: "inventory" },
  { path: "/manufacturing/settings",         label: "Mfg Settings",        icon: "gear",       module: "inventory" },

  { section: "GST/Taxes" },
  { path: "/gst/tax-templates",             label: "Tax Templates",    icon: "percent",    module: "taxes"      },
  { path: "/gst/gstr1",                     label: "GSTR-1",           icon: "gstfile",    module: "accounts"   },
  { path: "/gst/gstr3b",                    label: "GSTR-3B",          icon: "gstfile",    module: "accounts"   },
  { path: "/gst/einvoice",                  label: "e-Invoice",        icon: "qr",         module: "accounts"   },
  { path: "/gst/tds",                       label: "TDS",              icon: "percent",    module: "accounts"   },

  { section: "Reports" },
  { path: "/reports",                       label: "All Reports",      icon: "chart",      module: "reports"    },

  { path: "/bulk-import",                   label: "Bulk Import",      icon: "fileplus",   module: "admin"      },

  { section: "Settings" },
  { path: "/settings/users",                label: "Users",            icon: "users",      module: "admin"      },
  { path: "/settings/profile",              label: "My Profile",       icon: "user",       module: null         },
  { path: "/settings/company",              label: "Company",          icon: "building",   module: "admin"      },
  { path: "/settings/email",                label: "Email & SMTP",     icon: "mail",       module: "admin"      },
  { path: "/settings/email-templates",      label: "Email Templates",  icon: "mail",       module: "admin"      },
  // { path: "/settings/number-series",        label: "Number Series",    icon: "hash",       module: "admin"      },
  // { path: "/settings/payment-terms",        label: "Payment Terms",    icon: "calendar",   module: "admin"      },
  // { path: "/settings/currency-exchange", label: "Currency", icon: "currency", module: "admin" }, // INR-only: hidden
  { path: "/settings/roles",                label: "Roles",            icon: "shield",     module: "admin"      },
  // { path: "/settings/organization",         label: "Organization",     icon: "org",        module: "admin"      },
  // { path: "/settings/security",             label: "Security",         icon: "lock",       module: null         },
  { path: "/settings/sso",                  label: "Single Sign-On",   icon: "shield",     module: "admin"      },
  // { path: "/settings/audit-log",            label: "Audit Log",        icon: "audit",      module: "admin"      },
  { path: "/settings/integrations",         label: "Integrations",     icon: "webhook",    module: "admin"      },
];

// Returns a label for the topbar given a route path. Falls back to "Books".
const TITLES = Object.fromEntries(
  NAV.filter((n) => n.path).map((n) => [n.path, n.label])
);
export function titleFor(path) {
  if (TITLES[path]) return TITLES[path];
  // Match nearest prefix for nested/dynamic routes (e.g. /invoices/INV-001).
  const hit = Object.keys(TITLES)
    .filter((p) => path.startsWith(p) && p !== "/")
    .sort((a, b) => b.length - a.length)[0];
  return TITLES[hit] || "Books";
}

// All routes are Vue-owned — the legacy bundle is retired.
export function isVueOwned(_path) {
  return true;
}