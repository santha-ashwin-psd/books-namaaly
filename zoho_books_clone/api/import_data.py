import csv
import io
import re
import frappe
from frappe import _
from frappe.utils import flt, cint, nowdate


def _parse_date(value):
    """
    Normalise a date string to YYYY-MM-DD (the only format accepted by
    MariaDB / Frappe).  Handles the most common user-supplied formats:

        DD-MM-YYYY  →  2026-06-01
        DD/MM/YYYY  →  2026-06-01
        MM/DD/YYYY  →  2026-01-06   (US format, only tried when day > 12 fails)
        YYYY-MM-DD  →  returned as-is
        YYYY/MM/DD  →  2026-06-01

    Returns nowdate() when the value is empty/None, and raises
    frappe.ValidationError for values that cannot be parsed.
    """
    if not value:
        return nowdate()

    value = value.strip()
    if not value:
        return nowdate()

    # Already in the correct format
    if re.match(r'^\d{4}-\d{2}-\d{2}$', value):
        return value

    # YYYY/MM/DD
    m = re.match(r'^(\d{4})[/](\d{1,2})[/](\d{1,2})$', value)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    # DD-MM-YYYY  or  DD/MM/YYYY
    m = re.match(r'^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$', value)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        # If day > 12 it can only be DD-MM-YYYY
        if day > 12 or month <= 12:
            return f"{year}-{month:02d}-{day:02d}"

    frappe.throw(
        _(
            "Date value '{0}' is not in a recognised format. "
            "Please use YYYY-MM-DD (e.g. 2026-06-01)."
        ).format(value)
    )


CUSTOMER_FIELDS = [
    "customer_name", "customer_type", "email_id", "mobile_no",
    "phone", "tax_id", "city", "state", "country", "payment_terms",
]

ITEM_FIELDS = [
    "item_code", "item_name", "item_group", "item_type",
    "stock_uom", "standard_rate", "standard_buying_rate", "tax_code", "gst_rate", "hsn_code",
    "description", "is_sales_item", "is_purchase_item",
]

VENDOR_FIELDS = [
    "supplier_name", "supplier_type", "email_id", "mobile_no",
    "phone", "tax_id", "city", "state", "country", "payment_terms",
]

INVOICE_FIELDS = [
    "customer", "posting_date", "due_date", "item_code", "qty",
    "rate", "tax_type", "tax_rate", "currency", "remarks",
]

QUOTATION_FIELDS = [
    "customer", "valid_till", "item_code", "qty",
    "rate", "tax_type", "tax_rate", "currency", "remarks",
]

SALES_ORDER_FIELDS = [
    "customer", "delivery_date", "item_code", "qty",
    "rate", "tax_type", "tax_rate", "currency", "remarks",
]

BILL_FIELDS = [
    "supplier", "bill_no", "bill_date", "posting_date", "due_date",
    "item_code", "qty", "rate", "tax_type", "tax_rate", "currency", "remarks",
]

EXPENSE_FIELDS = [
    "posting_date", "expense_type", "description", "amount",
    "gst_rate", "expense_account", "paid_through",
    "vendor", "reference_no", "notes",
]

PURCHASE_ORDER_FIELDS = [
    "supplier", "transaction_date", "expected_delivery_date",
    "item_code", "qty", "rate", "tax_type", "tax_rate", "currency", "remarks",
]


@frappe.whitelist()
def bulk_import(doctype, rows_json):
    """
    Import a list of dicts into the given doctype.
    Returns {"created": N, "skipped": N, "errors": [...]}
    """
    import json

    allowed = {
        "Customer", "Item", "Supplier",
        "Sales Invoice", "Quotation", "Sales Order",
        "Purchase Invoice", "Expense", "Purchase Order",
    }
    if doctype not in allowed:
        frappe.throw(_("Unsupported doctype for import: {}").format(doctype))

    # Custom role/module authorization — only members who may create this doctype
    # (right module flag, not read-only) can bulk import it.
    from zoho_books_clone.utils.access import assert_can
    assert_can(doctype, "create")

    rows = json.loads(rows_json)
    if not isinstance(rows, list):
        frappe.throw(_("rows_json must be a JSON array"))

    created = 0
    skipped = 0
    errors = []

    from zoho_books_clone.utils.tenancy import _default_books_company

    user = frappe.session.user
    # Always look up the user's own Books Company Member record first —
    # get_user_company() returns None for bypass roles (Administrator / System Manager)
    # even when they ARE a member of a specific company, causing the wrong
    # _default_books_company() fallback to be used instead.
    company = (
        frappe.db.get_value("Books Company Member", {"user": user}, "company")
        or _default_books_company()
        or ""
    )

    for i, row in enumerate(rows, start=1):
        try:
            doc = _build_doc(doctype, row, company)
            if not doc:
                skipped += 1
                continue
            frappe.get_doc(doc).insert(ignore_permissions=False)
            created += 1
        except Exception as e:
            errors.append({"row": i, "data": row, "error": str(e)})

    frappe.db.commit()
    return {"created": created, "skipped": skipped, "errors": errors}


def _build_doc(doctype, row, company):
    if doctype == "Customer":
        name = (row.get("customer_name") or "").strip()
        if not name:
            return None
        return {
            "doctype": "Customer",
            "customer_name": name,
            "customer_type": row.get("customer_type") or "Individual",
            "email_id": row.get("email_id") or "",
            "mobile_no": row.get("mobile_no") or "",
            "phone": row.get("phone") or "",
            "tax_id": row.get("tax_id") or "",
            "city": row.get("city") or "",
            "state": row.get("state") or "",
            "country": row.get("country") or "India",
            "payment_terms": row.get("payment_terms") or "",
            "books_company": company,
        }

    if doctype == "Supplier":
        name = (row.get("supplier_name") or "").strip()
        if not name:
            return None
        return {
            "doctype": "Supplier",
            "supplier_name": name,
            "supplier_type": row.get("supplier_type") or "Individual",
            "email_id": row.get("email_id") or "",
            "mobile_no": row.get("mobile_no") or "",
            "phone": row.get("phone") or "",
            "tax_id": row.get("tax_id") or "",
            "city": row.get("city") or "",
            "state": row.get("state") or "",
            "country": row.get("country") or "India",
            "payment_terms": row.get("payment_terms") or "",
            "books_company": company,
        }

    if doctype == "Item":
        iname = (row.get("item_name") or "").strip()
        if not iname:
            return None
        return {
            "doctype": "Item",
            "item_name": iname,
            "item_code": (row.get("item_code") or iname).strip(),
            "item_group": _resolve_or_create_item_group(row.get("item_group")),
            "item_type": row.get("item_type") or "Service",
            "stock_uom": row.get("stock_uom") or "Nos",
            "standard_rate": flt(row.get("standard_rate") or 0),
            "standard_buying_rate": flt(row.get("standard_buying_rate") or 0),
            "tax_code": _resolve_tax_code(row.get("tax_code"), company),
            "gst_rate": flt(row.get("gst_rate") or 0),
            "hsn_code": row.get("hsn_code") or "",
            "description": row.get("description") or iname,
            "is_sales_item": cint(row.get("is_sales_item") if row.get("is_sales_item") is not None else 1),
            "is_purchase_item": cint(row.get("is_purchase_item") if row.get("is_purchase_item") is not None else 1),
            "books_company": company,
        }

    if doctype == "Sales Invoice":
        customer_input = (row.get("customer") or "").strip()
        item_code = (row.get("item_code") or "").strip()
        if not customer_input or not item_code:
            return None
        if not company:
            frappe.throw(_("Company could not be determined. Please ensure your user is linked to a Books Company, or set a default company in Books Settings."))
        customer_id, customer_name = _resolve_customer(customer_input, company)
        return {
            "doctype": "Sales Invoice",
            "company": company,
            "customer": customer_id,
            "customer_name": customer_name,
            "posting_date": _parse_date(row.get("posting_date")),
            "due_date": _parse_date(row.get("due_date")),
            "currency": row.get("currency") or "INR",
            "remarks": row.get("remarks") or "",
            "items": [
                {
                    "item_code": item_code,
                    "qty": flt(row.get("qty") or 1),
                    "rate": flt(row.get("rate") or 0),
                }
            ],
            "taxes": _build_tax_rows(flt(row.get("tax_rate") or 0), row.get("tax_type")),
        }

    if doctype == "Quotation":
        customer_input = (row.get("customer") or "").strip()
        item_code = (row.get("item_code") or "").strip()
        if not customer_input or not item_code:
            return None
        if not company:
            frappe.throw(_("Company could not be determined. Please ensure your user is linked to a Books Company, or set a default company in Books Settings."))
        customer_id, customer_name = _resolve_customer(customer_input, company)
        return {
            "doctype": "Quotation",
            "company": company,
            "quotation_to": "Customer",
            "party_name": customer_id,
            "customer_name": customer_name,
            "transaction_date": _parse_date(row.get("transaction_date")),
            "valid_till": _parse_date(row.get("valid_till")),
            "currency": row.get("currency") or "INR",
            "remarks": row.get("remarks") or "",
            "items": [
                {
                    "item_code": item_code,
                    "qty": flt(row.get("qty") or 1),
                    "rate": flt(row.get("rate") or 0),
                }
            ],
            "taxes": _build_tax_rows(flt(row.get("tax_rate") or 0), row.get("tax_type")),
        }

    if doctype == "Sales Order":
        customer_input = (row.get("customer") or "").strip()
        item_code = (row.get("item_code") or "").strip()
        if not customer_input or not item_code:
            return None
        if not company:
            frappe.throw(_("Company could not be determined. Please ensure your user is linked to a Books Company, or set a default company in Books Settings."))
        customer_id, customer_name = _resolve_customer(customer_input, company)
        return {
            "doctype": "Sales Order",
            "company": company,
            "customer": customer_id,
            "customer_name": customer_name,
            "delivery_date": _parse_date(row.get("delivery_date")),
            "transaction_date": _parse_date(row.get("transaction_date")),
            "currency": row.get("currency") or "INR",
            "remarks": row.get("remarks") or "",
            "items": [
                {
                    "item_code": item_code,
                    "qty": flt(row.get("qty") or 1),
                    "rate": flt(row.get("rate") or 0),
                    "delivery_date": _parse_date(row.get("delivery_date")),
                }
            ],
            "taxes": _build_tax_rows(flt(row.get("tax_rate") or 0), row.get("tax_type")),
        }

    if doctype == "Purchase Invoice":
        supplier_input = (row.get("supplier") or "").strip()
        item_code = (row.get("item_code") or "").strip()
        if not supplier_input or not item_code:
            return None
        if not company:
            frappe.throw(_("Company could not be determined. Please ensure your user is linked to a Books Company."))
        supplier_id, supplier_name = _resolve_supplier(supplier_input, company)
        return {
            "doctype": "Purchase Invoice",
            "company": company,
            "supplier": supplier_id,
            "supplier_name": supplier_name,
            "bill_no": row.get("bill_no") or "",
            "bill_date": _parse_date(row.get("bill_date")),
            "posting_date": _parse_date(row.get("posting_date")),
            "due_date": _parse_date(row.get("due_date")),
            "currency": row.get("currency") or "INR",
            "remark": row.get("remarks") or "",
            "items": [
                {
                    "item_code": item_code,
                    "qty": flt(row.get("qty") or 1),
                    "rate": flt(row.get("rate") or 0),
                }
            ],
            "taxes": _build_tax_rows(flt(row.get("tax_rate") or 0), row.get("tax_type")),
        }

    if doctype == "Expense":
        expense_type = (row.get("expense_type") or "").strip()
        amount = flt(row.get("amount") or 0)
        expense_account = (row.get("expense_account") or "").strip()
        paid_through = (row.get("paid_through") or "").strip()
        if not expense_type or not amount or not expense_account or not paid_through:
            return None
        if not company:
            frappe.throw(_("Company could not be determined. Please ensure your user is linked to a Books Company."))
        vendor_input = (row.get("vendor") or "").strip()
        vendor_id = ""
        if vendor_input:
            try:
                supplier_id, _ = _resolve_supplier(vendor_input, company)
                vendor_id = supplier_id
            except Exception:
                vendor_id = ""
        return {
            "doctype": "Expense",
            "company": company,
            "posting_date": _parse_date(row.get("posting_date")),
            "expense_type": expense_type,
            "description": row.get("description") or expense_type,
            "amount": amount,
            "gst_rate": flt(row.get("gst_rate") or 0),
            "expense_account": expense_account,
            "paid_through": paid_through,
            "vendor": vendor_id,
            "reference_no": row.get("reference_no") or "",
            "notes": row.get("notes") or "",
        }

    if doctype == "Purchase Order":
        supplier_input = (row.get("supplier") or "").strip()
        item_code = (row.get("item_code") or "").strip()
        if not supplier_input or not item_code:
            return None
        if not company:
            frappe.throw(_("Company could not be determined. Please ensure your user is linked to a Books Company."))
        supplier_id, supplier_name = _resolve_supplier(supplier_input, company)
        return {
            "doctype": "Purchase Order",
            "company": company,
            "supplier": supplier_id,
            "supplier_name": supplier_name,
            "transaction_date": _parse_date(row.get("transaction_date")),
            "expected_delivery_date": _parse_date(row.get("expected_delivery_date")),
            "currency": row.get("currency") or "INR",
            "remarks": row.get("remarks") or "",
            "items": [
                {
                    "item_code": item_code,
                    "qty": flt(row.get("qty") or 1),
                    "rate": flt(row.get("rate") or 0),
                    "expected_delivery_date": _parse_date(row.get("expected_delivery_date")),
                }
            ],
            "taxes": _build_tax_rows(flt(row.get("tax_rate") or 0), row.get("tax_type")),
        }

    return None


def _resolve_tax_code(tax_code_input, company):
    """
    Resolve a 'tax_code' CSV value to a valid Tax Template docname.

    Tax Template's autoname was changed (patch v1_2) from a globally-unique
    `field:template_name` to `format:{template_name} - {company}`, so a CSV
    written against the old naming (e.g. "GST 5% (Intra-State)") no longer
    matches any docname directly and would otherwise fail Item's Link
    validation with a generic "Could not find Default Tax Template: ..."
    error on every row. Resolve it the same way the Tax Template list
    displays it — by template_name scoped to the company — before falling
    back to a direct name match.
    """
    value = (tax_code_input or "").strip()
    if not value:
        return ""

    # Already the exact per-company docname (or user typed it in full).
    if frappe.db.exists("Tax Template", value):
        return value

    # New naming scheme: "{template_name} - {company}", scoped to this company.
    by_company_name = frappe.db.get_value(
        "Tax Template", {"name": f"{value} - {company}"}, "name"
    )
    if by_company_name:
        return by_company_name

    # Fall back to the clean display name (template_name), scoped to company.
    by_template_name = frappe.db.get_value(
        "Tax Template", {"template_name": value, "company": company}, "name"
    )
    if by_template_name:
        return by_template_name

    frappe.throw(
        _(
            "Tax code '{0}' not found for this company. "
            "Please check the Tax Templates list or the spelling."
        ).format(value)
    )


def _resolve_or_create_item_group(name):
    """
    Item Group is a global (not per-company) taxonomy, autonamed by prompt —
    the value typed in the CSV *is* the docname directly, there's no
    separate title field. If the CSV references a group that doesn't exist
    yet, create it as a flat leaf group under "All Item Groups" instead of
    failing the whole row with a generic Link-validation error ("Could not
    find Item Group: ...") — the same class of failure the tax_code column
    used to hit before _resolve_tax_code was added.
    """
    name = (name or "").strip() or "All Item Groups"
    if frappe.db.exists("Item Group", name):
        return name

    # "All Item Groups" itself is seeded at install and should always exist.
    # If it's somehow missing, don't try to parent the new group under a
    # group that doesn't exist either — leave it parentless rather than
    # fail the whole row over a missing root node.
    parent = "All Item Groups" if frappe.db.exists("Item Group", "All Item Groups") else None

    try:
        frappe.get_doc({
            "doctype": "Item Group",
            "name": name,  # autoname: prompt — the typed name is the docname
            "parent_item_group": parent,
            "is_group": 0,
        }).insert(ignore_permissions=True)
    except frappe.DuplicateEntryError:
        # Race: an earlier row in this same import batch (or a concurrent
        # import) already created it — nothing more to do.
        pass
    return name


def _resolve_supplier(supplier_input, company):
    """
    Look up a Supplier record by supplier_name scoped to the user's company.
    Returns (supplier_id, supplier_name).
    Raises frappe.ValidationError when not found.
    """
    exact = frappe.db.get_value(
        "Supplier",
        {"name": supplier_input, "books_company": company},
        ["name", "supplier_name"],
        as_dict=True,
    )
    if exact:
        return exact["name"], exact["supplier_name"]

    by_name = frappe.db.get_value(
        "Supplier",
        {"supplier_name": supplier_input, "books_company": company},
        ["name", "supplier_name"],
        as_dict=True,
    )
    if by_name:
        return by_name["name"], by_name["supplier_name"]

    frappe.throw(
        _(
            "Vendor '{0}' not found. "
            "Please create this vendor first or check the spelling."
        ).format(supplier_input)
    )
    """
    Look up a Customer record by customer_name scoped to the user's company.

    - customer_input  : the value from the CSV 'customer' column (display name)
    - company         : the books_company value for the logged-in user

    Returns (customer_id, customer_name) where customer_id is Customer.name
    (the autonamed series key, e.g. CUST-2025-00001) used as the Link value,
    and customer_name is the display name to stamp on the document.

    Raises frappe.ValidationError with a clear message if no matching customer
    exists for that company, so the row is recorded as an error rather than
    silently creating a broken document.
    """
    # First try matching by the series name directly (e.g. CUST-2025-00001)
    # in case the CSV already contains the internal ID.
    exact = frappe.db.get_value(
        "Customer",
        {"name": customer_input, "books_company": company},
        ["name", "customer_name"],
        as_dict=True,
    )
    if exact:
        return exact["name"], exact["customer_name"]

    # Otherwise match by customer_name (display name) scoped to this company.
    by_name = frappe.db.get_value(
        "Customer",
        {"first_name": customer_input, "books_company": company},
        ["name", "customer_name"],
        as_dict=True,
    )
    if by_name:
        return by_name["name"], by_name["customer_name"]
    by_name = frappe.db.get_value(
        "Customer",
        {"customer_name": customer_input, "books_company": company},
        ["name", "customer_name"],
        as_dict=True,
    )
    if by_name:
        return by_name["name"], by_name["customer_name"]

    frappe.throw(
        _(
            "Customer '{0}' not found. "
            "Please create this customer first or check the spelling."
        ).format(customer_input, company)
    )


def _build_tax_rows(tax_rate, tax_type=None):
    """
    Return Tax Line child rows if tax_rate > 0, else empty list.
    tax_type must be one of: CGST, SGST, IGST, VAT, Cess, Other.
    Defaults to IGST when not supplied.
    account_head is intentionally omitted — it is optional on Tax Line
    and was causing "Could not find Account Head" errors on import.
    """
    if not tax_rate:
        return []
    valid_types = {"CGST", "SGST", "IGST", "VAT", "Cess", "Other"}
    ttype = (tax_type or "IGST").strip()
    if ttype not in valid_types:
        ttype = "IGST"
    return [
        {
            "tax_type": ttype,
            "description": f"GST @ {tax_rate}%",
            "rate": tax_rate,
        }
    ]


@frappe.whitelist()
def get_sample_csv(doctype):
    """Return a CSV string with headers + sample row for the given doctype."""
    config = {
        "Customer": {
            "headers": ["customer_name","customer_type","email_id","mobile_no","phone","tax_id","city","state","country","payment_terms"],
            "sample":  [["Acme Corp","Company","acme@example.com","9876543210","","27AAACR5055K1Z5","Mumbai","Maharashtra","India","Net 30"]],
        },
        "Supplier": {
            "headers": ["supplier_name","supplier_type","email_id","mobile_no","phone","tax_id","city","state","country","payment_terms"],
            "sample":  [["Global Supplies","Company","supplier@example.com","9876543210","","27AAACR5055K1Z5","Delhi","Delhi","India",""]],
        },
        "Item": {
            "headers": ["item_code","item_name","item_group","item_type","stock_uom","standard_rate","standard_buying_rate","tax_code","hsn_code","description","is_sales_item","is_purchase_item"],
            "sample":  [["ITEM-001","Widget A","All Item Groups","Product","Nos","100","60","GST 18%","8471","Standard Widget","1","1"]],
        },
        "Sales Invoice": {
            "headers": ["customer","posting_date","due_date","item_code","qty","rate","tax_type","tax_rate","currency","remarks"],
            "sample":  [["Acme Corp","2025-01-15","2025-02-14","ITEM-001","2","500","IGST","18","INR","Bulk import invoice"]],
        },
        "Quotation": {
            "headers": ["customer","valid_till","item_code","qty","rate","tax_type","tax_rate","currency","remarks","transaction_date"],
            "sample":  [["Acme Corp","2025-02-28","ITEM-001","5","450","IGST","18","INR","Quote for Q1","2025-01-15"]],
        },
        "Sales Order": {
            "headers": ["customer","delivery_date","item_code","qty","rate","tax_type","tax_rate","currency","remarks","transaction_date"],
            "sample":  [["Acme Corp","2025-01-30","ITEM-001","10","480","IGST","18","INR","Bulk order Jan","2025-01-15"]],
        },
        "Purchase Invoice": {
            "headers": ["supplier","bill_no","bill_date","posting_date","due_date","item_code","qty","rate","tax_type","tax_rate","currency","remarks"],
            "sample":  [["Global Supplies","BILL-001","2025-01-15","2025-01-15","2025-02-14","ITEM-001","3","400","IGST","18","INR","Purchase bill Jan"]],
        },
        "Expense": {
            "headers": ["posting_date","expense_type","description","amount","gst_rate","expense_account","paid_through","vendor","reference_no","notes"],
            "sample":  [["2025-01-15","Travel","Taxi fare to client site","1500","0","Travelling Expenses - TC","Cash - TC","","","Q1 travel"]],
        },
        "Purchase Order": {
            "headers": ["supplier","transaction_date","expected_delivery_date","item_code","qty","rate","tax_type","tax_rate","currency","remarks"],
            "sample":  [["Global Supplies","2025-01-10","2025-01-30","ITEM-001","20","380","IGST","18","INR","PO for Q1 stock"]],
        },
    }

    if doctype not in config:
        frappe.throw(_("Unsupported doctype: {}").format(doctype))

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(config[doctype]["headers"])
    for row in config[doctype]["sample"]:
        w.writerow(row)
    return buf.getvalue()