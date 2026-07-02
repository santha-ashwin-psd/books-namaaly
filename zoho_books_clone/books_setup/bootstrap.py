"""
Per-company bootstrap — runs on signup to seed a fresh company with the data
required for the golden flow (Customer → Item → Sales Invoice → Payment) to
work without manual setup.

Idempotent: every step checks for existence before inserting.

Account naming convention: "{account_name} - {company}"
  (matches the DocType autoname rule: format:{account_name} - {company})
"""
import datetime

import frappe


COA = [
    # (account_name, account_type, parent_name, is_group)
    # Parent is the account_name (not the full doc name) — we build the full
    # name as "{parent} - {company}" at runtime.
    ("Assets",                "Asset",      None,                  1),
    ("Current Assets",        "Asset",      "Assets",              1),
    ("Cash",                  "Cash",       "Current Assets",      0),
    ("Bank Accounts",         "Bank",       "Current Assets",      1),
    ("Accounts Receivable",   "Receivable", "Current Assets",      0),
    ("Stock In Hand",         "Stock",      "Current Assets",      0),
    ("Input Tax Credits",     "Tax",        "Current Assets",      1),
    ("CGST Input",            "Tax",        "Input Tax Credits",   0),
    ("SGST Input",            "Tax",        "Input Tax Credits",   0),
    ("IGST Input",            "Tax",        "Input Tax Credits",   0),
    ("Liabilities",           "Liability",  None,                  1),
    ("Current Liabilities",   "Liability",  "Liabilities",         1),
    ("Accounts Payable",      "Payable",    "Current Liabilities", 0),
    ("CGST Payable",          "Tax",        "Current Liabilities", 0),
    ("SGST Payable",          "Tax",        "Current Liabilities", 0),
    ("IGST Payable",          "Tax",        "Current Liabilities", 0),
    ("Equity",                "Equity",     None,                  1),
    ("Retained Earnings",     "Equity",     "Equity",              0),
    ("Income",                "Income",     None,                  1),
    ("Sales Revenue",         "Income",     "Income",              0),
    ("Other Income",          "Income",     "Income",              0),
    ("Expenses",              "Expense",    None,                  1),
    ("Cost of Goods Sold",    "Cost of Goods Sold", "Expenses",    0),
    ("Stock Adjustment",      "Stock Adjustment",   "Expenses",    0),
    ("Operating Expenses",    "Expense",    "Expenses",            1),
    ("Salaries & Wages",      "Expense",    "Operating Expenses",  0),
    ("Rent",                  "Expense",    "Operating Expenses",  0),
    ("Office Supplies",       "Expense",    "Operating Expenses",  0),
]


# Default Indian GST tax templates, seeded once per company.
# (template_name, [ (tax_type, description, rate, account_name), ... ])
# account_name is resolved to the company's full account name at seed time.
TAX_TEMPLATES = [
    ("GST 18% (Intra-State)", [("CGST", "CGST @ 9%", 9, "CGST Payable"), ("SGST", "SGST @ 9%", 9, "SGST Payable")]),
    ("GST 12% (Intra-State)", [("CGST", "CGST @ 6%", 6, "CGST Payable"), ("SGST", "SGST @ 6%", 6, "SGST Payable")]),
    ("GST 5% (Intra-State)",  [("CGST", "CGST @ 2.5%", 2.5, "CGST Payable"), ("SGST", "SGST @ 2.5%", 2.5, "SGST Payable")]),
    ("GST 28% (Intra-State)", [("CGST", "CGST @ 14%", 14, "CGST Payable"), ("SGST", "SGST @ 14%", 14, "SGST Payable")]),
    ("IGST 18% (Inter-State)", [("IGST", "IGST @ 18%", 18, "IGST Payable")]),
    ("IGST 12% (Inter-State)", [("IGST", "IGST @ 12%", 12, "IGST Payable")]),
    ("IGST 5% (Inter-State)",  [("IGST", "IGST @ 5%", 5, "IGST Payable")]),
    ("IGST 28% (Inter-State)", [("IGST", "IGST @ 28%", 28, "IGST Payable")]),
    ("GST Exempt", []),
    ("Input GST 18% (Intra-State)", [("CGST", "CGST ITC @ 9%", 9, "CGST Input"), ("SGST", "SGST ITC @ 9%", 9, "SGST Input")]),
    ("Input IGST 18% (Inter-State)", [("IGST", "IGST ITC @ 18%", 18, "IGST Input")]),
]

# Template names known to be app defaults — used by the back-fill patch to
# distinguish seeded defaults from user-created templates (which are left alone).
DEFAULT_TAX_TEMPLATE_NAMES = frozenset(name for name, _ in TAX_TEMPLATES)


def _acc_name(account_name: str, company: str) -> str:
    """Return the full document name for an account."""
    return f"{account_name} - {company}"


def bootstrap_company_data(company: str, fy_start: str = "04-01") -> None:
    """Seed a fresh company with the minimum data needed for invoicing."""
    if not company:
        return
    _seed_coa(company)
    _seed_fiscal_year(company, fy_start)
    _seed_tax_templates(company)


def _seed_tax_templates(company: str) -> None:
    """Create the default GST tax templates for `company` if absent.

    Idempotent: the document name is "{template_name} - {company}" (autoname
    format:{template_name} - {company}), so we skip any that already exist.
    Never deletes — only fills in missing defaults.
    """
    if not company or not frappe.db.exists("DocType", "Tax Template"):
        return

    def _acct(name):
        # Resolve a tax account_name to this company's full account name.
        return frappe.db.get_value(
            "Account", {"account_name": name, "company": company, "is_group": 0}, "name"
        ) or _acc_name(name, company)

    for template_name, rows in TAX_TEMPLATES:
        doc_name = f"{template_name} - {company}"
        if frappe.db.exists("Tax Template", doc_name):
            continue
        try:
            frappe.get_doc({
                "doctype": "Tax Template",
                "template_name": template_name,
                "company": company,
                "tax_type": "GST",
                "taxes": [
                    {"tax_type": t[0], "description": t[1], "rate": t[2], "account_head": _acct(t[3])}
                    for t in rows
                ],
            }).insert(ignore_permissions=True)
        except Exception as exc:
            frappe.log_error(
                title="Books Bootstrap",
                message=f"Bootstrap Tax Template — {company}/{template_name}: {exc}",
            )


def _seed_coa(company: str) -> None:
    """Create the default Chart of Accounts for this company if absent.

    The full document name for each account is "{account_name} - {company}".
    We check by that full name first so the idempotency guard works even when
    the account was created in a previous call.
    """
    for name, atype, parent, is_group in COA:
        full_name = _acc_name(name, company)

        # Idempotency: skip if already present (check by PK, which is the full name)
        if frappe.db.exists("Account", full_name):
            continue

        parent_full = _acc_name(parent, company) if parent else ""

        try:
            doc = frappe.get_doc({
                "doctype":        "Account",
                "account_name":   name,
                "account_type":   atype,
                "parent_account": parent_full,
                "is_group":       is_group,
                "company":        company,
                "currency":       "INR",
            })
            doc.insert(ignore_permissions=True)
        except Exception as exc:
            frappe.log_error(
                title="Books Bootstrap",
                message=f"Bootstrap COA — {company}/{name}: {exc}",
            )


def _seed_fiscal_year(company: str, fy_start: str = "04-01") -> None:
    """Create a Fiscal Year for `company` covering today, if absent.

    Fiscal Year autoname is ``field:year``, so the ``year`` field value becomes
    the document PK.  We suffix it with the company name — "{year_label} - {company}"
    — to keep each company's FY unique in a multi-tenant database.  The
    ``company`` field is also explicitly stamped so the FY is correctly scoped
    by the filtering in FiscalYears.vue and central_validator.
    """
    try:
        today = datetime.date.today()
        month, day = (int(x) for x in (fy_start or "04-01").split("-"))

        start = datetime.date(today.year, month, day)
        if today < start:
            start = datetime.date(today.year - 1, month, day)
        end = datetime.date(start.year + 1, month, day) - datetime.timedelta(days=1)

        if start.year == end.year:
            year_label = str(start.year)
        else:
            year_label = f"{start.year}-{str(end.year)[-2:]}"

        # Full document name: "{year_label} - {company}"
        # Must be unique per company because autoname = field:year.
        doc_name = f"{year_label} - {company}"

        # Idempotency: skip if this exact FY doc already exists, OR if any FY
        # for this company already covers the same date range.
        if frappe.db.exists("Fiscal Year", doc_name):
            return

        existing = frappe.db.sql("""
            SELECT name FROM `tabFiscal Year`
            WHERE company = %s
              AND year_start_date <= %s
              AND year_end_date   >= %s
            LIMIT 1
        """, (company, end.strftime("%Y-%m-%d"), start.strftime("%Y-%m-%d")), as_dict=True)

        if existing:
            return

        fy = frappe.new_doc("Fiscal Year")
        fy.year            = doc_name          # PK via autoname=field:year
        fy.year_start_date = start.strftime("%Y-%m-%d")
        fy.year_end_date   = end.strftime("%Y-%m-%d")
        fy.company         = company           # explicit company stamp
        # flags.ignore_validate skips the overlap check in FiscalYear.validate()
        # which would otherwise trigger because fy.name is not yet persisted
        fy.flags.ignore_validate = True
        fy.insert(ignore_permissions=True)

    except Exception as exc:
        frappe.log_error(
            title="Books Bootstrap",
            message=f"Bootstrap FY — {company}: {exc}",
        )