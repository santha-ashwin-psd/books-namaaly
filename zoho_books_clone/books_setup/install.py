import frappe
from frappe import _
import os


def after_install():
    create_roles()
    seed_naming_series()
    seed_currencies()
    seed_uoms()
    seed_modes_of_payment()
    seed_payment_terms()
    create_default_accounts()
    seed_landed_cost_accounts()
    seed_tax_templates()
    seed_warehouses()
    seed_price_lists()
    seed_item_groups()
    seed_customer_custom_fields()
    seed_supplier_custom_fields()
    seed_invoice_custom_fields()
    seed_books_company_field()
    seed_qc_item_fields()
    seed_manufacturing_settings()
    frappe.db.commit()
    print("✅  Zoho Books Clone installed successfully!")


def after_migrate():
    seed_naming_series()
    seed_warehouses()
    seed_price_lists()
    seed_currencies()
    seed_uoms()
    if frappe.db.exists("DocType", "Books Payment Mode"):
        seed_modes_of_payment()
    if frappe.db.exists("DocType", "Payment Terms"):
        seed_payment_terms()
    if frappe.db.exists("DocType", "Account"):
        seed_landed_cost_accounts()
    seed_tax_templates()
    seed_item_groups()
    seed_customer_custom_fields()
    seed_supplier_custom_fields()
    seed_invoice_custom_fields()
    seed_books_company_field()
    seed_qc_item_fields()
    seed_manufacturing_settings()
    _normalize_company_names()
    frappe.db.commit()


# ─── Company Name Normalisation ──────────────────────────────────────────────
def _normalize_company_names():
    """
    Normalise all company name references across key tables to use the most
    common casing found in tabAccount.  Silently skips tables that don't exist.
    """
    rows = frappe.db.sql(
        """SELECT company, COUNT(*) AS cnt
           FROM `tabAccount`
           WHERE company IS NOT NULL AND company != ''
           GROUP BY company ORDER BY cnt DESC LIMIT 1""",
        as_dict=True,
    )
    if not rows:
        return

    canonical = rows[0]["company"]

    targets = [
        ("tabAccount",              "company"),
        ("tabSales Invoice",        "company"),
        ("tabPurchase Invoice",     "company"),
        ("tabPayment Entry",        "company"),
        ("tabJournal Entry",        "company"),
        ("tabStock Entry",          "company"),
        ("tabGeneral Ledger Entry", "company"),
        ("tabStock Ledger Entry",   "company"),
        ("tabWarehouse",            "company"),
        ("tabCost Center",          "company"),
    ]
    for table, field in targets:
        try:
            frappe.db.sql(
                f"UPDATE `{table}` SET `{field}` = %s "
                f"WHERE LOWER(`{field}`) = LOWER(%s) AND `{field}` != %s",
                (canonical, canonical, canonical),
            )
        except Exception:
            pass


# ─── Roles ───────────────────────────────────────────────────────────────────
def create_roles():
    for role in ["Books Admin", "Accountant", "Books Manager", "Books Viewer"]:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)


# ─── Naming Series ───────────────────────────────────────────────────────────
def seed_naming_series():
    series = {
        "Sales Invoice":    "INV-.YYYY.-.#####",
        "Purchase Invoice": "PINV-.YYYY.-.#####",
        "Payment Entry":    "PAY-.YYYY.-.#####",
        "Bank Transaction": "BTXN-.YYYY.-.#####",
        "Customer":         "CUST-.YYYY.-.#####",
        "Supplier":         "SUPP-.YYYY.-.#####",
        "QC Inspection":    "QCI-.YYYY.-.#####",
        "BOM":              "BOM-.YYYY.-.#####",
        "Work Order":       "WO-.YYYY.-.#####",
        "Production Plan":  "PP-.YYYY.-.#####",
        "Job Card":         "JC-.YYYY.-.#####",
        "Material Request": "MR-.YYYY.-.#####",
        "Packing Slip":    "PS-.YYYY.-.#####",
        "Landed Cost Voucher": "LCV-.YYYY.-.#####",
    }
    for doctype, prefix in series.items():
        key = f"{prefix}."
        try:
            frappe.db.sql(
                "INSERT IGNORE INTO `tabSeries` (name, current) VALUES (%s, 0)", key
            )
        except Exception:
            pass
    frappe.db.commit()


# ─── Currencies ──────────────────────────────────────────────────────────────
def seed_currencies():
    currencies = [
        ("INR", "₹", "Paise",  100, "#,##,###.##"),
        ("USD", "$", "Cents",  100, "#,###.##"),
        ("EUR", "€", "Cents",  100, "#,###.##"),
        ("GBP", "£", "Pence",  100, "#,###.##"),
        ("AED", "د.إ","Fils",  100, "#,###.##"),
        ("SGD", "S$","Cents",  100, "#,###.##"),
    ]
    for code, symbol, fraction, units, fmt in currencies:
        if not frappe.db.exists("Currency", code):
            frappe.get_doc({
                "doctype":        "Currency",
                "currency_name":  code,
                "currency_symbol":symbol,
                "fraction":       fraction,
                "fraction_units": units,
                "number_format":  fmt,
                "enabled":        1,
            }).insert(ignore_permissions=True)


# ─── Units of Measure ────────────────────────────────────────────────────────
def seed_uoms():
    uoms = [
        ("Nos",     "Numbers / Units"),
        ("Kg",      "Kilogram"),
        ("Gram",    "Gram"),
        ("Liter",   "Liter"),
        ("Meter",   "Meter"),
        ("Hour",    "Hour"),
        ("Day",     "Day"),
        ("Month",   "Month"),
        ("Box",     "Box"),
        ("Pair",    "Pair"),
        ("Dozen",   "Dozen"),
        ("Quintal", "Quintal (100 Kg)"),
        ("Tonne",   "Metric Tonne"),
        ("Sq Meter","Square Meter"),
        ("Sq Foot", "Square Foot"),
    ]
    for name, desc in uoms:
        if not frappe.db.exists("UOM", name):
            frappe.get_doc({
                "doctype": "UOM",
                "uom_name": name,
                "description": desc,
                "enabled": 1,
            }).insert(ignore_permissions=True)


# ─── Modes of Payment ────────────────────────────────────────────────────────
def seed_modes_of_payment():
    modes = [
        ("Cash",          "Cash"),
        ("Bank Transfer", "Bank"),
        ("NEFT",          "Bank"),
        ("RTGS",          "Bank"),
        ("UPI",           "Bank"),
        ("Cheque",        "Bank"),
        ("Credit Card",   "Bank"),
        ("Debit Card",    "Bank"),
        ("Demand Draft",  "Bank"),
    ]
    for name, mtype in modes:
        if not frappe.db.exists("Books Payment Mode", name):
            frappe.get_doc({
                "doctype":        "Books Payment Mode",
                "mode_of_payment": name,
                "type":           mtype,
                "enabled":        1,
            }).insert(ignore_permissions=True)


# ─── Payment Terms ───────────────────────────────────────────────────────────
def seed_payment_terms():
    terms = [
        ("Net 30",        30, "Day(s) after invoice date"),
        ("Net 15",        15, "Day(s) after invoice date"),
        ("Net 7",          7, "Day(s) after invoice date"),
        ("Due on Receipt", 0, "Day(s) after invoice date"),
        ("Net 60",        60, "Day(s) after invoice date"),
        ("Net 90",        90, "Day(s) after invoice date"),
        ("End of Month",   0, "Day(s) after the end of the invoice month"),
    ]
    for name, days, basis in terms:
        if not frappe.db.exists("Payment Terms", name):
            frappe.get_doc({
                "doctype":           "Payment Terms",
                "payment_terms_name": name,
                "credit_days":       days,
                "due_date_based_on": basis,
            }).insert(ignore_permissions=True)


# ─── Chart of Accounts ───────────────────────────────────────────────────────
def create_default_accounts():
    # Prefer Books Settings — our authoritative source — then fall back to Global Defaults
    company = frappe.db.get_single_value("Books Settings", "default_company")
    if not company:
        try:
            company = frappe.db.get_single_value("Global Defaults", "default_company")
        except Exception:
            company = None
    if not company:
        return

    coa = [
        ("Assets",                "Asset",     None,                 1),
        ("Current Assets",        "Asset",     "Assets",             1),
        ("Cash in Hand",          "Cash",      "Current Assets",     1),
        ("Petty Cash",            "Cash",      "Cash in Hand",       0),
        ("Bank Accounts",         "Bank",      "Current Assets",     1),
        ("Accounts Receivable",   "Receivable","Current Assets",     0),
        ("Fixed Assets",          "Asset",     "Assets",             1),
        ("Fixed Assets - Cost",       "Fixed Asset",              "Fixed Assets", 0),
        ("Accumulated Depreciation",  "Accumulated Depreciation", "Fixed Assets", 0),
        ("Capital Work in Progress",  "Asset",                    "Fixed Assets", 0),
        ("Liabilities",           "Liability", None,                 1),
        ("Current Liabilities",   "Liability", "Liabilities",        1),
        ("Accounts Payable",      "Payable",   "Current Liabilities",0),
        ("Stock Received", "Stock Received But Not Billed", "Current Liabilities", 0),
        ("GST Payable",           "Tax",       "Current Liabilities",0),
        ("CGST Payable",          "Tax",       "Current Liabilities",0),
        ("SGST Payable",          "Tax",       "Current Liabilities",0),
        ("IGST Payable",          "Tax",       "Current Liabilities",0),
        ("Input Tax Credits",     "Tax",       "Current Assets",     1),
        ("CGST Input",            "Tax",       "Input Tax Credits",  0),
        ("SGST Input",            "Tax",       "Input Tax Credits",  0),
        ("IGST Input",            "Tax",       "Input Tax Credits",  0),
        ("Equity",                "Equity",    None,                 1),
        ("Retained Earnings",     "Equity",    "Equity",             0),
        ("Income",                "Income",    None,                 1),
        ("Sales Revenue",         "Income",    "Income",             0),
        ("Other Income",          "Income",    "Income",             0),
        ("Expenses",              "Expense",   None,                 1),
        ("Cost of Goods Sold",    "Cost of Goods Sold", "Expenses",    0),
        ("Stock In Hand",         "Stock",     "Current Assets",     0),
        ("Stock Adjustment",      "Stock Adjustment", "Expenses",    0),
        ("Operating Expenses",    "Expense",   "Expenses",           1),
        ("Salaries & Wages",      "Expense",   "Operating Expenses", 0),
        ("Rent",                  "Expense",   "Operating Expenses", 0),
        ("Office Supplies",       "Expense",   "Operating Expenses", 0),
        ("Depreciation Expense",  "Depreciation", "Operating Expenses", 0),
    ]

    def _acc(name):
        """Return the full scoped account name."""
        return f"{name} - {company}"

    for name, atype, parent, is_group in coa:
        full_name = _acc(name)
        if frappe.db.exists("Account", full_name):
            continue
        try:
            frappe.get_doc({
                "doctype":        "Account",
                "account_name":   name,
                "account_type":   atype,
                "parent_account": _acc(parent) if parent else "",
                "is_group":       is_group,
                "company":        company,
                "currency":       "INR",
            }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(str(e), f"Account seed: {name}")


# ─── Landed Cost Voucher accounts ────────────────────────────────────────────
def seed_landed_cost_accounts():
    """Three expense accounts a Landed Cost Voucher charge row can point at.
    LCV reclassifies out of these into Stock In Hand on submit (Phase 4) —
    seeding them here is just data, no code needed on the accounting side."""
    company = frappe.db.get_single_value("Books Settings", "default_company")
    if not company:
        try:
            company = frappe.db.get_single_value("Global Defaults", "default_company")
        except Exception:
            company = None
    if not company:
        return

    def _acc(name):
        return f"{name} - {company}"

    parent = _acc("Operating Expenses")
    if not frappe.db.exists("Account", parent):
        # Base chart of accounts hasn't been seeded yet (or uses a different
        # structure) — skip rather than guess a parent.
        return

    landed_cost_accounts = [
        "Freight & Parcel Charges - Inward",
        "Local Transport Charges - Inward",
        "Freight & Courier Charges - Outward",
    ]
    for name in landed_cost_accounts:
        full_name = _acc(name)
        if frappe.db.exists("Account", full_name):
            continue
        try:
            frappe.get_doc({
                "doctype":        "Account",
                "account_name":   name,
                "account_type":   "Expense",
                "parent_account": parent,
                "is_group":       0,
                "company":        company,
                "currency":       "INR",
            }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(str(e), f"Landed cost account seed: {name}")


# ─── Tax Templates (GST) ─────────────────────────────────────────────────────
def seed_tax_templates():
    """
    Create the standard Indian GST tax templates for EVERY company, so users
    have ready-to-use tax configurations out of the box.

    Per-company seeding lives in books_setup.bootstrap._seed_tax_templates
    (the single source of truth, also used on company creation and by the
    back-fill patch). Idempotent and non-destructive.
    """
    if not frappe.db.exists("DocType", "Tax Template"):
        return
    from zoho_books_clone.books_setup.bootstrap import _seed_tax_templates
    for company in _all_company_names():
        _seed_tax_templates(company)


def _all_company_names():
    """Collect every known company from Books Settings / Global defaults,
    per-user company defaults, and any company already stamped on Accounts."""
    companies = set()
    for doctype in ("Books Settings", "Global Defaults"):
        try:
            c = frappe.db.get_single_value(doctype, "default_company")
            if c:
                companies.add(c)
        except Exception:
            pass
    try:
        for (c,) in frappe.db.sql(
            "SELECT DISTINCT defvalue FROM `tabDefaultValue` WHERE defkey='company' AND defvalue IS NOT NULL AND defvalue != ''"
        ):
            if c:
                companies.add(c)
    except Exception:
        pass
    try:
        for (c,) in frappe.db.sql(
            "SELECT DISTINCT company FROM `tabAccount` WHERE company IS NOT NULL AND company != ''"
        ):
            if c:
                companies.add(c)
    except Exception:
        pass
    try:
        for row in frappe.get_all("Books Company", fields=["name"], ignore_permissions=True):
            companies.add(row["name"])
    except Exception:
        pass
    return companies


# ─── Cost Centers ────────────────────────────────────────────────────────────
def seed_cost_centers():
    # Prefer Books Settings — our authoritative source — then fall back to Global Defaults
    company = frappe.db.get_single_value("Books Settings", "default_company")
    if not company:
        try:
            company = frappe.db.get_single_value("Global Defaults", "default_company")
        except Exception:
            company = None
    if not company:
        return
    if not frappe.db.exists("Cost Center", {"cost_center_name": "Main", "company": company}):
        try:
            frappe.get_doc({
                "doctype":          "Cost Center",
                "cost_center_name": "Main",
                "is_group":         0,
                "company":          company,
            }).insert(ignore_permissions=True)
        except Exception:
            pass


# ─── Print Formats ───────────────────────────────────────────────────────────
@frappe.whitelist(allow_guest=False, methods=["POST"])
def seed_print_formats():
    """
    Create or update the 'Tax Invoice' Print Format in the Frappe database.
    Reads the HTML from the app's templates/print_formats/sales_invoice.html file.
    """
    try:
        # Resolve path to the HTML template relative to this file
        app_path = frappe.get_app_path("zoho_books_clone")
        html_path = os.path.join(app_path, "templates", "print_formats", "sales_invoice.html")

        if not os.path.exists(html_path):
            frappe.log_error(f"Print format HTML not found at {html_path}", "seed_print_formats")
            return

        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        format_name = "Tax Invoice"

        if frappe.db.exists("Print Format", format_name):
            # Update existing
            pf = frappe.get_doc("Print Format", format_name)
            pf.html = html_content
            pf.print_format_type = "Jinja"
            pf.save(ignore_permissions=True)
        else:
            # Create new
            frappe.get_doc({
                "doctype":           "Print Format",
                "name":              format_name,
                "doc_type":          "Sales Invoice",
                "module":            "Invoicing",
                "print_format_type": "Jinja",
                "html":              html_content,
                "standard":          "No",
                "disabled":          0,
            }).insert(ignore_permissions=True)

        frappe.db.commit()
        print(f"✅  Print Format '{format_name}' seeded successfully.")

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "seed_print_formats failed")
        print(f"⚠️  Could not seed print format: {e}")



# ─── Inventory Defaults ───────────────────────────────────────────────────────

def seed_warehouses():
    """Create default warehouse hierarchy for ALL companies that lack leaf warehouses."""
    if not frappe.db.exists("DocType", "Warehouse"):
        return

    # Collect all known companies from multiple sources
    companies = set()

    # 1. Global / Books default
    for doctype in ("Books Settings", "Global Defaults"):
        try:
            c = frappe.db.get_single_value(doctype, "default_company")
            if c:
                companies.add(c)
        except Exception:
            pass

    # 2. Per-user company defaults (covers every registered user's company)
    try:
        rows = frappe.db.sql(
            "SELECT DISTINCT defvalue FROM `tabDefaultValue` WHERE defkey='company' AND defvalue IS NOT NULL AND defvalue != ''",
            as_dict=False,
        )
        for (c,) in rows:
            if c:
                companies.add(c)
    except Exception:
        pass

    # 3. Companies that already have warehouses (any type)
    try:
        rows = frappe.db.sql(
            "SELECT DISTINCT company FROM `tabWarehouse` WHERE company IS NOT NULL AND company != ''",
            as_dict=False,
        )
        for (c,) in rows:
            if c:
                companies.add(c)
    except Exception:
        pass

    warehouse_templates = [
        # (warehouse_name, warehouse_type, is_group, parent_name)
        ("All Warehouses",  "Stores",        1, None),
        ("Stores",          "Stores",        0, "All Warehouses"),
        ("Transit",         "Transit",       0, "All Warehouses"),
        ("Manufacturing",   "Manufacturing", 0, "All Warehouses"),
        ("Scrap",           "Virtual",       0, "All Warehouses"),
    ]

    for company in companies:
        # Check if this company already has leaf (non-group) warehouses
        existing_leaf = frappe.db.sql(
            "SELECT COUNT(*) FROM `tabWarehouse` WHERE company=%s AND is_group=0 AND disabled=0",
            company,
        )[0][0]
        if existing_leaf:
            continue  # already has warehouses, skip

        # Suffix pattern used for named warehouses: "Stores-{company}"
        suffix = f"-{company}"

        for wh_name, wh_type, is_group, parent_name in warehouse_templates:
            full_name = wh_name + suffix
            if frappe.db.exists("Warehouse", full_name):
                continue
            try:
                parent_full = (parent_name + suffix) if parent_name else ""
                frappe.get_doc({
                    "doctype":         "Warehouse",
                    "warehouse_name":  wh_name,
                    "warehouse_type":  wh_type,
                    "parent_warehouse": parent_full,
                    "company":         company,
                    "is_group":        is_group,
                    "disabled":        0,
                }).insert(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(str(e), f"Warehouse seed: {wh_name} for {company}")


def seed_price_lists():
    """Create default Selling and Buying price lists."""
    price_lists = [
        ("Standard Selling", "INR", 1, 0),
        ("Standard Buying",  "INR", 0, 1),
        ("Export Selling",   "USD", 1, 0),
    ]

    for name, currency, selling, buying in price_lists:
        if frappe.db.exists("DocType", "Price List") and not frappe.db.exists("Price List", name):
            try:
                frappe.get_doc({
                    "doctype": "Price List",
                    "price_list_name": name,
                    "currency": currency,
                    "selling": selling,
                    "buying": buying,
                    "enabled": 1,
                }).insert(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(str(e), f"Price List seed: {name}")


# ─── Item Groups ──────────────────────────────────────────────────────────────
def seed_item_groups():
    """Create default Item Group hierarchy if none exist."""
    if not frappe.db.exists("DocType", "Item Group"):
        return

    groups = [
        # (name, parent, is_group)
        ("All Item Groups", "",               1),
        ("Products",        "All Item Groups", 0),
        ("Services",        "All Item Groups", 0),
        ("Raw Materials",   "All Item Groups", 0),
        ("Finished Goods",  "All Item Groups", 0),
    ]

    for name, parent, is_group in groups:
        if not frappe.db.exists("Item Group", name):
            try:
                frappe.get_doc({
                    "doctype":           "Item Group",
                    "name":              name,
                    "parent_item_group": parent,
                    "is_group":          is_group,
                }).insert(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(str(e), f"Item Group seed: {name}")


# ─── Customer Custom Fields ───────────────────────────────────────────────────
def seed_customer_custom_fields():
    """
    Add all extra fields that the Books SPA's Customer form uses but that
    are NOT part of Frappe's stock Customer doctype.
    Uses Frappe's Custom Field mechanism so they survive bench migrate.
    Also runs ALTER TABLE directly so the columns exist immediately without
    needing a full bench migrate cycle.
    """
    FIELDS = [
        # fieldname, label, fieldtype, insert_after, options/default
        ("salutation",          "Salutation",            "Select",   "customer_type",
         "\nMr.\nMs.\nMrs.\nDr.\nProf."),
        ("first_name",          "First Name",            "Data",     "salutation",      ""),
        ("last_name",           "Last Name",             "Data",     "first_name",      ""),
        ("company_name",        "Company Name",          "Data",     "last_name",       ""),
        ("gst_treatment",       "GST Treatment",         "Select",   "tax_id",
         "Registered Business\nUnregistered Business\nOverseas\nSEZ\nConsumer"),
        ("pan_no",              "PAN Number",            "Data",     "gst_treatment",   ""),
        ("place_of_supply",     "Place of Supply",       "Data",     "pan_no",          ""),
        ("source",              "Source",                "Data",     "place_of_supply", ""),
        ("opening_balance",     "Opening Balance",       "Currency", "source",          ""),
        # Shipping address
        ("ship_address_line1",  "Ship Address Line 1",   "Data",     "country",         ""),
        ("ship_address_line2",  "Ship Address Line 2",   "Data",     "ship_address_line1", ""),
        ("ship_city",           "Ship City",             "Data",     "ship_address_line2", ""),
        ("ship_state",          "Ship State",            "Data",     "ship_city",       ""),
        ("ship_pincode",        "Ship Pincode",          "Data",     "ship_state",      ""),
        ("ship_country",        "Ship Country",          "Data",     "ship_pincode",    ""),
        # Bank details
        ("bank_name",           "Bank Name",             "Data",     "ship_country",    ""),
        ("bank_account_no",     "Bank Account No",       "Data",     "bank_name",       ""),
        ("bank_ifsc",           "Bank IFSC Code",        "Data",     "bank_account_no", ""),
        # Notes / remarks
        ("notes",               "Notes",                 "Small Text","bank_ifsc",      ""),
    ]

    DB_TYPE_MAP = {
        "Data":       "varchar(140) DEFAULT NULL",
        "Select":     "varchar(140) DEFAULT NULL",
        "Currency":   "decimal(21,9) DEFAULT NULL",
        "Small Text": "text DEFAULT NULL",
    }

    db_name = frappe.conf.db_name
    # Existing columns in tabCustomer
    existing_cols = set(
        r[0] for r in frappe.db.sql(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'tabCustomer'",
            db_name
        )
    )

    for fieldname, label, fieldtype, insert_after, options_or_default in FIELDS:
        cf_name = f"Customer-{fieldname}"

        # 1. Create / update the Custom Field record
        if frappe.db.exists("Custom Field", cf_name):
            pass  # already there — skip
        else:
            try:
                cf = frappe.get_doc({
                    "doctype":      "Custom Field",
                    "name":         cf_name,
                    "dt":           "Customer",
                    "fieldname":    fieldname,
                    "label":        label,
                    "fieldtype":    fieldtype,
                    "insert_after": insert_after,
                    "options":      options_or_default if fieldtype in ("Select",) else "",
                    "default":      options_or_default if fieldtype not in ("Select",) else "",
                    "in_list_view": 0,
                    "in_standard_filter": 0,
                })
                cf.insert(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(str(e), f"Custom Field seed: {cf_name}")

        # 2. Add the physical DB column if missing (so data persists immediately)
        if fieldname not in existing_cols:
            col_def = DB_TYPE_MAP.get(fieldtype, "varchar(140) DEFAULT NULL")
            try:
                frappe.db.sql(
                    f"ALTER TABLE `tabCustomer` ADD COLUMN `{fieldname}` {col_def}"
                )
                existing_cols.add(fieldname)
            except Exception as e:
                # Column might already exist with a different approach — ignore
                frappe.log_error(str(e), f"ALTER TABLE Customer add {fieldname}")

    frappe.db.commit()


def seed_supplier_custom_fields():
    """
    Add shipping address custom fields to Supplier (mirrors the Customer ship_* fields).
    """
    FIELDS = [
        ("ship_address_line1", "Ship Address Line 1", "Data",     "country",            ""),
        ("ship_address_line2", "Ship Address Line 2", "Data",     "ship_address_line1",  ""),
        ("ship_city",          "Ship City",           "Data",     "ship_address_line2",  ""),
        ("ship_state",         "Ship State",          "Data",     "ship_city",           ""),
        ("ship_pincode",       "Ship Pincode",        "Data",     "ship_state",          ""),
        ("ship_country",       "Ship Country",        "Data",     "ship_pincode",        ""),
        ("opening_balance",    "Opening Balance",     "Currency", "ship_country",        ""),
    ]

    DB_TYPE_MAP = {"Data": "varchar(140) DEFAULT NULL", "Currency": "decimal(21,9) DEFAULT NULL"}
    db_name = frappe.conf.db_name
    existing_cols = set(
        r[0] for r in frappe.db.sql(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'tabSupplier'",
            db_name
        )
    )

    for fieldname, label, fieldtype, insert_after, _ in FIELDS:
        cf_name = f"Supplier-{fieldname}"
        if not frappe.db.exists("Custom Field", cf_name):
            try:
                frappe.get_doc({
                    "doctype": "Custom Field", "name": cf_name,
                    "dt": "Supplier", "fieldname": fieldname,
                    "label": label, "fieldtype": fieldtype,
                    "insert_after": insert_after,
                    "in_list_view": 0, "in_standard_filter": 0,
                }).insert(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(str(e), f"Custom Field seed: {cf_name}")

        if fieldname not in existing_cols:
            col_def = DB_TYPE_MAP.get(fieldtype, "varchar(140) DEFAULT NULL")
            try:
                frappe.db.sql(f"ALTER TABLE `tabSupplier` ADD COLUMN `{fieldname}` {col_def}")
                existing_cols.add(fieldname)
            except Exception as e:
                frappe.log_error(str(e), f"ALTER TABLE Supplier add {fieldname}")

    frappe.db.commit()


def seed_invoice_custom_fields():
    """
    Add shipping_address (Small Text) to Sales Invoice so the Invoice form
    can store a separate shipping address alongside the existing billing_address.
    """
    FIELDS = [
        # doctype, table, fieldname, label, fieldtype, insert_after
        ("Sales Invoice", "tabSales Invoice", "shipping_address",
         "Shipping Address", "Small Text", "billing_address"),
    ]

    DB_TYPE_MAP = {"Small Text": "text DEFAULT NULL"}
    db_name = frappe.conf.db_name

    for doctype, table, fieldname, label, fieldtype, insert_after in FIELDS:
        cf_name = f"{doctype}-{fieldname}"
        if not frappe.db.exists("Custom Field", cf_name):
            try:
                frappe.get_doc({
                    "doctype": "Custom Field", "name": cf_name,
                    "dt": doctype, "fieldname": fieldname,
                    "label": label, "fieldtype": fieldtype,
                    "insert_after": insert_after,
                    "in_list_view": 0, "in_standard_filter": 0,
                }).insert(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(str(e), f"Custom Field seed: {cf_name}")

        existing_cols = set(
            r[0] for r in frappe.db.sql(
                "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
                (db_name, table)
            )
        )
        if fieldname not in existing_cols:
            col_def = DB_TYPE_MAP.get(fieldtype, "text DEFAULT NULL")
            try:
                frappe.db.sql(f"ALTER TABLE `{table}` ADD COLUMN `{fieldname}` {col_def}")
            except Exception as e:
                frappe.log_error(str(e), f"ALTER TABLE {table} add {fieldname}")

    frappe.db.commit()


# ─── books_company isolation field ───────────────────────────────────────────
def seed_books_company_field():
    """
    Add the `books_company` custom field to Customer, Supplier, Item, and Contact.
    This field is used for company-level data isolation so all members of the same
    company share these records while different companies stay isolated.
    """
    TARGETS = [
        ("Customer",  "tabCustomer"),
        ("Supplier",  "tabSupplier"),
        ("Item",      "tabItem"),
        ("Contact",   "tabContact"),
    ]
    db_name = frappe.conf.db_name

    for doctype, table in TARGETS:
        cf_name = f"{doctype}-books_company"

        # Custom Field record
        if not frappe.db.exists("Custom Field", cf_name):
            try:
                frappe.get_doc({
                    "doctype":      "Custom Field",
                    "name":         cf_name,
                    "dt":           doctype,
                    "fieldname":    "books_company",
                    "label":        "Books Company",
                    "fieldtype":    "Link",
                    "options":      "Books Company",
                    "insert_after": "amended_from" if doctype != "Contact" else "last_name",
                    "hidden":       1,
                    "no_copy":      1,
                    "in_list_view": 0,
                    "in_standard_filter": 0,
                }).insert(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(str(e), f"Custom Field seed: {cf_name}")

        # Physical column
        existing = set(
            r[0] for r in frappe.db.sql(
                "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = 'books_company'",
                (db_name, table),
            )
        )
        if "books_company" not in existing:
            try:
                frappe.db.sql(
                    f"ALTER TABLE `{table}` ADD COLUMN `books_company` varchar(140) DEFAULT NULL"
                )
                frappe.db.sql(
                    f"ALTER TABLE `{table}` ADD INDEX `idx_{table.replace('tab','')}_books_company` (`books_company`)"
                )
            except Exception as e:
                frappe.log_error(str(e), f"ALTER TABLE {table} add books_company")

    frappe.db.commit()


# ─── Manufacturing Settings ──────────────────────────────────────────────────
def seed_manufacturing_settings():
    """Ensure the Manufacturing Settings singleton exists and has safe defaults.
    Idempotent — only writes fields that are not yet set."""
    if not frappe.db.exists("DocType", "Manufacturing Settings"):
        return
    try:
        ms = frappe.get_single("Manufacturing Settings")
        changed = False
        defaults = {
            "auto_create_job_cards": 1,
            "over_production_allowance_pct": 0,
            "allow_negative_stock": 0,
            "backflush_raw_materials_based_on": "BOM",
            "default_bom_type": "Manufacturing",
            "set_rate_of_sub_assembly_item_based_on_bom": 0,
            "job_card_hours_per_day": 8,
            "capacity_planning_for_days": 30,
            "warn_if_bom_not_default": 1,
            "warn_on_missing_job_cards": 1,
        }
        for field, val in defaults.items():
            current = ms.get(field)
            if current is None or current == "":
                frappe.db.set_value("Manufacturing Settings", "Manufacturing Settings", field, val)
                changed = True
        if changed:
            frappe.db.commit()
    except Exception as e:
        frappe.log_error(str(e), "seed_manufacturing_settings")


# ─── QC Item Custom Fields ───────────────────────────────────────────────
def seed_qc_item_fields():
    """
    Add QC-related custom fields to the Item doctype:
      - Section break: Quality Control
      - inspection_required_before_purchase  (Check)
      - inspection_required_before_delivery  (Check)
      - inspection_required_before_manufacture (Check)
      - default_qc_inspection_template       (Link -> QC Inspection Template)

    Idempotent: checks existence before inserting.
    Also seeds the Books Settings qc_warn_on_missing_inspection flag.
    """
    qc_fields = [
        {
            "fieldname": "section_qc",
            "fieldtype": "Section Break",
            "label":     "Quality Control",
            "insert_after": "section_inventory",
        },
        {
            "fieldname": "inspection_required_before_purchase",
            "fieldtype": "Check",
            "label":     "Inspection Required Before Purchase",
            "description": "QC Inspection required when receiving this item (Purchase Receipt / Purchase Invoice)",
            "insert_after": "section_qc",
        },
        {
            "fieldname": "inspection_required_before_delivery",
            "fieldtype": "Check",
            "label":     "Inspection Required Before Delivery",
            "description": "QC Inspection required before dispatching this item (Sales Invoice / Delivery Note)",
            "insert_after": "inspection_required_before_purchase",
        },
        {
            "fieldname": "inspection_required_before_manufacture",
            "fieldtype": "Check",
            "label":     "Inspection Required Before Manufacture",
            "description": "QC Inspection required for Manufacture-type Stock Entries",
            "insert_after": "inspection_required_before_delivery",
        },
        {
            "fieldname": "default_qc_inspection_template",
            "fieldtype": "Link",
            "label":     "Default QC Inspection Template",
            "options":   "QC Inspection Template",
            "description": "Auto-populated into new QC Inspections for this item",
            "insert_after": "inspection_required_before_manufacture",
        },
    ]

    for fld in qc_fields:
        cf_name = f"Item-{fld['fieldname']}"
        if frappe.db.exists("Custom Field", cf_name):
            continue
        try:
            doc = frappe.get_doc({
                "doctype":      "Custom Field",
                "name":         cf_name,
                "dt":           "Item",
                "fieldname":    fld["fieldname"],
                "label":        fld["label"],
                "fieldtype":    fld["fieldtype"],
                "options":      fld.get("options", ""),
                "insert_after": fld.get("insert_after", ""),
                "description":  fld.get("description", ""),
                "hidden":       0,
                "in_list_view": 0,
            })
            doc.insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(str(e), f"QC Custom Field seed: {cf_name}")

    # Physical columns on tabItem for the check fields
    db_name = frappe.conf.get("db_name")
    check_columns = [
        "inspection_required_before_purchase",
        "inspection_required_before_delivery",
        "inspection_required_before_manufacture",
        "default_qc_inspection_template",
    ]
    existing_cols = set(
        r[0] for r in frappe.db.sql(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'tabItem'",
            (db_name,),
        )
    )
    for col in check_columns:
        if col not in existing_cols:
            try:
                col_type = "tinyint(1) DEFAULT 0" if "inspection_required" in col or col == "inspection_required_before_manufacture" else "varchar(140) DEFAULT NULL"
                frappe.db.sql(f"ALTER TABLE `tabItem` ADD COLUMN `{col}` {col_type}")
            except Exception as e:
                frappe.log_error(str(e), f"ALTER TABLE tabItem add {col}")

    # Seed Books Settings QC master switch if the doctype exists
    try:
        if frappe.db.exists("DocType", "Books Settings"):
            # Add qc_warn_on_missing_inspection custom field to Books Settings if missing
            cf_name_bs = "Books Settings-qc_warn_on_missing_inspection"
            if not frappe.db.exists("Custom Field", cf_name_bs):
                frappe.get_doc({
                    "doctype":      "Custom Field",
                    "name":         cf_name_bs,
                    "dt":           "Books Settings",
                    "fieldname":    "qc_warn_on_missing_inspection",
                    "label":        "Warn When QC Inspection is Missing or Failed",
                    "fieldtype":    "Check",
                    "default":      "1",
                    "description":  "If enabled, submitting a document without a passed QC Inspection shows a warning dialog.",
                    "insert_after": "auto_reconcile",
                }).insert(ignore_permissions=True)
            # Set default value on the singleton
            try:
                bs = frappe.get_doc("Books Settings", "Books Settings")
                if bs.get("qc_warn_on_missing_inspection") is None:
                    frappe.db.set_value("Books Settings", "Books Settings",
                                        "qc_warn_on_missing_inspection", 1)
            except Exception:
                pass
    except Exception as e:
        frappe.log_error(str(e), "QC Books Settings seed")

    frappe.db.commit()