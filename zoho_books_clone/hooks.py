app_name        = "zoho_books_clone"
app_title       = "Books"
app_publisher   = "PS Digitise"
app_description = "A full-featured accounting application built on Frappe"
app_email       = "devteam@psdigitise.com"
app_license     = "MIT"
app_version     = "1.0.0"
app_icon        = "octicon octicon-book"
app_color       = "#2563EB"

fixtures = [
    {"dt": "Role", "filters": [["name", "in", [
        "Books Admin", "Accountant", "Books Manager", "Books Viewer"
    ]]]},
    "Custom Field",
    "Property Setter",
]

# Central validation layer (P2/Issue 10) — runs on every financial document
_CV = "zoho_books_clone.accounts.central_validator"
# Stock link layer (Audit-2 / Audit-3) — auto stock entries on invoice submit/cancel
_SL = "zoho_books_clone.inventory.stock_link"
# Multi-tenant data isolation — must be defined before doc_events, permission_query_conditions, and has_permission
_TN = "zoho_books_clone.utils.tenancy"
# Quality Control gate — soft-warn before stock moves (runs BEFORE _SL on submit)
_QC = "zoho_books_clone.quality.qc_engine"
# Quality Hold Manager — auto-quarantine on failed QC Inspection
_QH = "zoho_books_clone.quality.qc_hold_manager"
doc_events = {
    "Sales Invoice": {
        "validate":  f"{_CV}.on_validate",
        "before_submit": f"{_QC}.auto_create_qc_for_sales_invoice",
        "on_submit": [f"{_CV}.on_submit", f"{_QC}.check_qc_before_stock_link", f"{_SL}.on_sales_invoice_submit"],
        "on_cancel": [f"{_CV}.on_cancel", f"{_SL}.on_sales_invoice_cancel"], "before_delete": f"{_CV}.before_delete",
    },
    "Purchase Invoice": {
        "validate":  f"{_CV}.on_validate",
        "on_submit": [f"{_CV}.on_submit", f"{_QC}.check_qc_before_stock_link", f"{_SL}.on_purchase_invoice_submit"],
        "on_cancel": [f"{_CV}.on_cancel", f"{_SL}.on_purchase_invoice_cancel"], "before_delete": f"{_CV}.before_delete",
    },
    "Payment Entry":    {"validate": f"{_CV}.on_validate", "on_submit": f"{_CV}.on_submit", "on_cancel": f"{_CV}.on_cancel", "before_delete": f"{_CV}.before_delete"},
    "Journal Entry":    {"validate": f"{_CV}.on_validate", "on_submit": f"{_CV}.on_submit", "on_cancel": f"{_CV}.on_cancel", "before_delete": f"{_CV}.before_delete"},
    "Credit Note":      {"validate": f"{_CV}.on_validate", "on_submit": f"{_CV}.on_submit", "on_cancel": f"{_CV}.on_cancel", "before_delete": f"{_CV}.before_delete"},
    "Expense":          {"validate": f"{_CV}.on_validate", "on_submit": f"{_CV}.on_submit", "on_cancel": f"{_CV}.on_cancel", "before_delete": f"{_CV}.before_delete"},
    "Expense Claim":    {"validate": f"{_CV}.on_validate", "on_submit": f"{_CV}.on_submit", "on_cancel": f"{_CV}.on_cancel", "before_delete": f"{_CV}.before_delete"},
    # Goods documents own the physical stock movement (Delivery Note out / Purchase Receipt in)
    # Phase 2: validate hook added so central_validator period/lock checks run on these too.
    "Delivery Note":    {"validate": f"{_CV}.on_validate", "before_submit": f"{_QC}.auto_create_qc_for_delivery_note", "on_submit": [f"{_QC}.check_qc_before_stock_link", f"{_SL}.on_delivery_note_submit"],    "on_cancel": [f"{_CV}.on_cancel", f"{_SL}.on_delivery_note_cancel"], "before_delete": f"{_CV}.before_delete"},
    "Purchase Receipt": {"validate": f"{_CV}.on_validate", "before_submit": f"{_QC}.auto_create_qc_for_purchase_receipt", "on_submit": [f"{_QC}.check_qc_before_stock_link", f"{_SL}.on_purchase_receipt_submit"], "on_cancel": [f"{_CV}.on_cancel", f"{_SL}.on_purchase_receipt_cancel"], "before_delete": f"{_CV}.before_delete"},
    # Purchase Order — wired so fiscal/period lock checks run on save and submit.
    "Purchase Order":   {"validate": f"{_CV}.on_validate", "on_submit": f"{_CV}.on_submit", "on_cancel": f"{_CV}.on_cancel", "before_delete": f"{_CV}.before_delete"},
    # Phase 2: Stock Entry and Bank Transaction wired to central_validator for period/lock checks.
    # Stock Entry also gets QC gate for Manufacture type entries.
    "Stock Entry":      {"validate": f"{_CV}.on_validate", "before_submit": f"{_QC}.auto_create_qc_for_stock_entry", "on_submit": f"{_QC}.check_qc_before_stock_link", "on_cancel": f"{_CV}.on_cancel", "before_delete": f"{_CV}.before_delete"},
    "Bank Transaction": {"validate": f"{_CV}.on_validate", "on_cancel": f"{_CV}.on_cancel", "before_delete": f"{_CV}.before_delete"},
    # QC Inspection — auto-handle hold/quarantine on submit
    "QC Inspection":    {"on_submit": f"{_QH}.handle_qc_result", "on_cancel": f"{_QH}.handle_qc_cancel"},
    # QC Approval Request — rejection_reason requirement enforced via doc_events
    # too (belt-and-suspenders alongside the controller's own validate()).
    "QC Approval Request": {"validate": f"{_QH}.validate_approval_request"},
    # Phase 3: pre-sales and GST docs wired so Books lock date + fiscal-year
    # period lock are enforced on these document types too.
    "Sales Order":      {"validate": f"{_CV}.on_validate", "on_cancel": f"{_CV}.on_cancel", "before_delete": f"{_CV}.before_delete"},
    "Quotation":        {"validate": f"{_CV}.on_validate", "on_cancel": f"{_CV}.on_cancel", "before_delete": f"{_CV}.before_delete"},
    "TDS Entry":        {"validate": f"{_CV}.on_validate", "on_cancel": f"{_CV}.on_cancel", "before_delete": f"{_CV}.before_delete"},
    # Auto-stamp books_company on master records so they're company-isolated
    "Customer":  {"before_insert": f"{_TN}.auto_stamp_books_company"},
    "Supplier":  {"before_insert": f"{_TN}.auto_stamp_books_company"},
    "Item":      {"before_insert": f"{_TN}.auto_stamp_books_company"},
    "Contact":   {"before_insert": f"{_TN}.auto_stamp_books_company"},
    # Auto-stamp company on manufacturing transactional records
    "BOM":              {"before_insert": f"{_TN}.auto_stamp_company"},
    "Work Order":       {"before_insert": f"{_TN}.auto_stamp_company"},
    "Production Plan":  {"before_insert": f"{_TN}.auto_stamp_company"},
    "Material Request": {"before_insert": f"{_TN}.auto_stamp_company"},
    "Packing Slip":     {"before_insert": f"{_TN}.auto_stamp_company"},
    "Job Card":         {"before_insert": f"{_TN}.auto_stamp_company"},
}

scheduler_events = {
    "daily": [
        "zoho_books_clone.utils.scheduler.send_payment_reminders",
        "zoho_books_clone.banking.utils.auto_match_bank_transactions",
        "zoho_books_clone.utils.scheduler.send_reorder_alerts",
    ],
    "monthly": [
        "zoho_books_clone.utils.scheduler.generate_monthly_reports",
    ],
}

global_search_doctypes = {
    "Accounts":  [
        {"doctype": "Account"},
        {"doctype": "Cost Center"},
    ],
    "Invoicing": [
        {"doctype": "Sales Invoice"},
        {"doctype": "Purchase Invoice"},
        {"doctype": "Customer"},
        {"doctype": "Supplier"},
        {"doctype": "Item"},
    ],
    "Payments": [
        {"doctype": "Payment Entry"},
    ],
    "Expenses": [
        {"doctype": "Expense"},
        {"doctype": "Expense Claim"},
    ],
    "Inventory": [
        {"doctype": "Warehouse"},
        {"doctype": "Stock Entry"},
        {"doctype": "Item Price"},
        {"doctype": "Price List"},
    ],
    "Quality": [
        {"doctype": "QC Inspection"},
        {"doctype": "QC Inspection Template"},
        {"doctype": "QC Approval Request"},
    ],
    "Books Setup": [
        {"doctype": "Currency"},
        {"doctype": "Currency Exchange"},
        {"doctype": "UOM"},
        {"doctype": "Books Payment Mode"},
        {"doctype": "Payment Terms"},
    ],
    "Manufacturing": [
        {"doctype": "BOM"},
        {"doctype": "Work Order"},
        {"doctype": "Production Plan"},
        {"doctype": "Job Card"},
        {"doctype": "Material Request"},
        {"doctype": "Packing Slip"},
        {"doctype": "Alternative Item"},
        {"doctype": "Material Substitution Log"},
        {"doctype": "Operation"},
        {"doctype": "Workstation"},
        {"doctype": "Routing"},
    ],
}

app_include_css = ["/assets/zoho_books_clone/css/books.css"]
app_include_js  = ["/assets/zoho_books_clone/js/books.js"]

after_install = "zoho_books_clone.books_setup.install.after_install"
after_migrate = "zoho_books_clone.books_setup.install.after_migrate"


# ─── Multi-tenant data isolation ─────────────────────────────────────────────
# Every transactional doctype with a `company` field is filtered to the user's
# company at query time AND validated at save time (via central_validator).
# System Manager / Administrator bypass these filters.
# (_TN is defined near the top of this file, alongside _CV and _SL)

permission_query_conditions = {
    "Sales Invoice":     f"{_TN}.qc_sales_invoice",
    "Purchase Invoice":  f"{_TN}.qc_purchase_invoice",
    "Payment Entry":     f"{_TN}.qc_payment_entry",
    "Journal Entry":     f"{_TN}.qc_journal_entry",
    "Credit Note":       f"{_TN}.qc_credit_note",
    "Sales Order":       f"{_TN}.qc_sales_order",
    "Purchase Order":    f"{_TN}.qc_purchase_order",
    "Quotation":         f"{_TN}.qc_quotation",
    "Account":           f"{_TN}.qc_account",
    "Cost Center":       f"{_TN}.qc_cost_center",
    "Warehouse":         f"{_TN}.qc_warehouse",
    "Stock Entry":       f"{_TN}.qc_stock_entry",
    "Bank Account":      f"{_TN}.qc_bank_account",
    "Bank Transaction":  f"{_TN}.qc_bank_transaction",
    "Expense":           f"{_TN}.qc_expense",
    "Expense Claim":     f"{_TN}.qc_expense_claim",
    # Master types — scoped by books_company custom field
    "Customer":          f"{_TN}.qc_customer",
    "Supplier":          f"{_TN}.qc_supplier",
    "Item":              f"{_TN}.qc_item",
    "Contact":           f"{_TN}.qc_contact",
    # Manufacturing — scoped by the `company` field
    "BOM":               f"{_TN}.qc_bom",
    "Work Order":        f"{_TN}.qc_work_order",
    "Production Plan":   f"{_TN}.qc_production_plan",
    "Job Card":          f"{_TN}.qc_job_card",
    "Material Request":  f"{_TN}.qc_material_request",
    "Packing Slip":      f"{_TN}.qc_packing_slip",
}

has_permission = {
    "Sales Invoice":     f"{_TN}.hp_sales_invoice",
    "Purchase Invoice":  f"{_TN}.hp_purchase_invoice",
    "Payment Entry":     f"{_TN}.hp_payment_entry",
    "Journal Entry":     f"{_TN}.hp_journal_entry",
    "Credit Note":       f"{_TN}.hp_credit_note",
    "Sales Order":       f"{_TN}.hp_sales_order",
    "Purchase Order":    f"{_TN}.hp_purchase_order",
    "Quotation":         f"{_TN}.hp_quotation",
    "Account":           f"{_TN}.hp_account",
    "Cost Center":       f"{_TN}.hp_cost_center",
    "Warehouse":         f"{_TN}.hp_warehouse",
    "Stock Entry":       f"{_TN}.hp_stock_entry",
    "Bank Account":      f"{_TN}.hp_bank_account",
    "Bank Transaction":  f"{_TN}.hp_bank_transaction",
    "Expense":           f"{_TN}.hp_expense",
    "Expense Claim":     f"{_TN}.hp_expense_claim",
    # Master types — scoped by books_company custom field
    "Customer":          f"{_TN}.hp_customer",
    "Supplier":          f"{_TN}.hp_supplier",
    "Item":              f"{_TN}.hp_item",
    "Contact":           f"{_TN}.hp_contact",
    # Manufacturing — scoped by the `company` field
    "BOM":               f"{_TN}.hp_bom",
    "Work Order":        f"{_TN}.hp_work_order",
    "Production Plan":   f"{_TN}.hp_production_plan",
    "Job Card":          f"{_TN}.hp_job_card",
    "Material Request":  f"{_TN}.hp_material_request",
    "Packing Slip":      f"{_TN}.hp_packing_slip",
}

website_route_rules = [
    {"from_route": "/home", "to_route": "books"},
    {"from_route": "/dashboard", "to_route": "books"},
    {"from_route": "/customers", "to_route": "books"},
    {"from_route": "/customers/<path:path>", "to_route": "books"},
    {"from_route": "/vendors", "to_route": "books"},
    {"from_route": "/inventory/<path:path>", "to_route": "books"},
    {"from_route": "/settings/<path:path>", "to_route": "books"},
    {"from_route": "/accounting/<path:path>", "to_route": "books"},
    {"from_route": "/invoices", "to_route": "books"},
    {"from_route": "/invoices/<path:path>", "to_route": "books"},
    {"from_route": "/quotes", "to_route": "books"},
    {"from_route": "/quotes/<path:path>", "to_route": "books"},
    {"from_route": "/sales-orders", "to_route": "books"},
    {"from_route": "/sales-orders/<path:path>", "to_route": "books"},
    {"from_route": "/credit-notes", "to_route": "books"},
    {"from_route": "/credit-notes/<path:path>", "to_route": "books"},
    {"from_route": "/purchases", "to_route": "books"},
    {"from_route": "/purchase-orders", "to_route": "books"},
    {"from_route": "/purchase-orders/<path:path>", "to_route": "books"},
    {"from_route": "/expenses", "to_route": "books"},
    {"from_route": "/expenses/<path:path>", "to_route": "books"},
    {"from_route": "/payments", "to_route": "books"},
    {"from_route": "/payments/<path:path>", "to_route": "books"},
    {"from_route": "/payments-received", "to_route": "books"},
    {"from_route": "/debit-notes", "to_route": "books"},
    {"from_route": "/recurring-bills", "to_route": "books"},
    {"from_route": "/recurring", "to_route": "books"},
    {"from_route": "/eway-bills", "to_route": "books"},
    {"from_route": "/eway-bills/<path:path>", "to_route": "books"},
    {"from_route": "/banking/<path:path>", "to_route": "books"},
    {"from_route": "/gst/<path:path>", "to_route": "books"},
    {"from_route": "/reports", "to_route": "books"},
    {"from_route": "/reports/<path:path>", "to_route": "books"},
    {"from_route": "/bulk-import", "to_route": "books"},
    {"from_route": "/delivery-challans", "to_route": "books"},
    {"from_route": "/proforma-invoices", "to_route": "books"},
    {"from_route": "/purchase-receipts", "to_route": "books"},
    {"from_route": "/quality", "to_route": "books"},
    {"from_route": "/sales-persons", "to_route": "books"},
    {"from_route": "/quality/<path:path>", "to_route": "books"},
    {"from_route": "/manufacturing", "to_route": "books"},
    {"from_route": "/manufacturing/<path:path>", "to_route": "books"},
    # Catch-all: anything else that would otherwise 404 lands on the Books
    # dashboard instead of Frappe's default error page. Frappe's own core
    # paths (/app, /api, /assets, /files, etc.) are registered as their own,
    # more specific Werkzeug rules and are matched before this wildcard, so
    # they're unaffected — this only fires for genuinely unmatched routes.
    {"from_route": "/<path:app_path>", "to_route": "books"},
]

# Frappe's built-in account pages are not used by Books — bounce them to the
# app host (/books). Logged-in users land on the dashboard; guests are sent to
# /login by the www/books auth guard.
website_redirects = [
    {"source": "/me", "target": "/books"},
    {"source": r"/me/(.*)", "target": "/books"},
]