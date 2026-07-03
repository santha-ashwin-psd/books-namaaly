from __future__ import annotations
"""
GST & TDS Compliance API — whitelisted endpoints.

Covers:
  - pay_gst: Journal Entry for GST payment (DR Output GST / CR Bank)
  - create_tds_entry: Journal Entry for TDS deduction on vendor payment
  - save_irn: Persist e-Invoice IRN to Sales Invoice notes field
"""
import frappe
from frappe import _
from frappe.utils import flt, today
from zoho_books_clone.accounts.doctype.general_ledger_entry.general_ledger_entry import (
    make_gl_entries,
)
from zoho_books_clone.db.validators import validate_fiscal_year


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _find_account(company: str, account_type: str, name_like: str = None) -> str | None:
    filters = {"account_type": account_type, "company": company, "is_group": 0}
    if name_like:
        filters["account_name"] = ["like", f"%{name_like}%"]
    return frappe.db.get_value("Account", filters, "name")


@frappe.whitelist(allow_guest=False)
def get_gst_accounts(company: str | None = None) -> dict:
    """Resolve the company's Output (sales) and Input (purchase) GST accounts so
    the SPA can post correctly-split CGST/SGST/IGST tax lines. Falls back across
    the common naming conventions ('Output CGST' / 'CGST Payable', etc.)."""
    from zoho_books_clone.api.session import _get_company
    if not company:
        company = _get_company(frappe.session.user)

    def find(*names):
        for n in names:
            acc = _find_account(company, "Tax", n)
            if acc:
                return acc
        return ""

    return {
        "output_cgst": find("Output CGST", "CGST Payable"),
        "output_sgst": find("Output SGST", "SGST Payable"),
        "output_igst": find("Output IGST", "IGST Payable"),
        "input_cgst":  find("Input CGST", "CGST Input"),
        "input_sgst":  find("Input SGST", "SGST Input"),
        "input_igst":  find("Input IGST", "IGST Input"),
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False, methods=["POST"])
def pay_gst(
    company: str,
    cgst_amount: str = "0",
    sgst_amount: str = "0",
    igst_amount: str = "0",
    bank_account: str = None,
    challan_ref: str = "",
    period: str = "",
) -> dict:
    """
    Create GL entries for GST payment to the government.

    GL Impact:
      DR Output CGST Payable  (reduce liability)
      DR Output SGST Payable  (reduce liability)
      DR Output IGST Payable  (reduce liability)
      CR Bank GL Account      (cash outflow)
    """
    # Authorization: posts GL (money out) — require accounts-module write access
    # and reject a company that isn't the caller's own.
    from zoho_books_clone.utils.access import require_module, assert_company
    assert_company(company)
    require_module("accounts", write=True)

    cgst  = flt(cgst_amount)
    sgst  = flt(sgst_amount)
    igst  = flt(igst_amount)
    total = cgst + sgst + igst

    if total <= 0:
        frappe.throw(_("Total GST payment amount must be positive."))

    # posting_date is always today() for GST payments — validate it falls in an
    # open, unlocked fiscal year before building any GL entries.
    posting_date = today()
    validate_fiscal_year(posting_date, company)

    # Resolve bank GL
    bank_gl = None
    if bank_account:
        bank_gl = frappe.db.get_value("Bank Account", bank_account, "gl_account")
    if not bank_gl:
        bank_gl = _find_account(company, "Bank") or _find_account(company, "Cash")
    if not bank_gl:
        frappe.throw(_("No bank/cash GL account found for company {0}.").format(company))

    # Resolve Output GST liability accounts
    cgst_acct = _find_account(company, "Tax", "Output CGST") or _find_account(company, "Tax", "CGST")
    sgst_acct = _find_account(company, "Tax", "Output SGST") or _find_account(company, "Tax", "SGST")
    igst_acct = _find_account(company, "Tax", "Output IGST") or _find_account(company, "Tax", "IGST")

    remark = "GST payment" + (f" — {period}" if period else "") + (f" — Challan: {challan_ref}" if challan_ref else "")

    gl_map = []
    if cgst > 0 and cgst_acct:
        gl_map.append({"account": cgst_acct, "debit": cgst, "credit": 0, "remarks": remark})
    if sgst > 0 and sgst_acct:
        gl_map.append({"account": sgst_acct, "debit": sgst, "credit": 0, "remarks": remark})
    if igst > 0 and igst_acct:
        gl_map.append({"account": igst_acct, "debit": igst, "credit": 0, "remarks": remark})

    if not gl_map:
        frappe.throw(_(
            "No Output GST accounts found. Please configure CGST / SGST / IGST "
            "accounts (account_type = Tax) in the Chart of Accounts."
        ))

    gl_map.append({"account": bank_gl, "debit": 0, "credit": total, "remarks": remark})

    voucher_no   = challan_ref or ("GST-PAY-" + today())
    for e in gl_map:
        e.update({
            "posting_date": posting_date,
            "voucher_type": "Journal Entry",
            "voucher_no": voucher_no,
            "company": company,
        })

    make_gl_entries(gl_map)
    frappe.db.commit()

    return {
        "total": total,
        "cgst": cgst,
        "sgst": sgst,
        "igst": igst,
        "bank_gl": bank_gl,
        "challan_ref": challan_ref,
        "voucher_no": voucher_no,
    }


@frappe.whitelist(allow_guest=False, methods=["POST"])
def create_tds_entry(
    company: str,
    party: str,
    expense_account: str,
    amount: str,
    tds_amount: str,
    tds_section: str = "",
    date: str = None,
    remarks: str = "",
) -> dict:
    """
    Create GL entries for TDS deduction on a vendor payment.

    GL Impact:
      DR Expense Account    (gross amount)
      CR TDS Payable        (TDS withheld for government)
      CR Accounts Payable   (net amount due to vendor)
    """
    # Authorization: posts GL — require accounts-module write access and reject a
    # company that isn't the caller's own.
    from zoho_books_clone.utils.access import require_module, assert_company
    assert_company(company)
    require_module("accounts", write=True)

    amount_f = flt(amount)
    tds_f    = flt(tds_amount)
    net      = round(amount_f - tds_f, 2)

    if amount_f <= 0:
        frappe.throw(_("Payment amount must be positive."))
    if tds_f < 0 or tds_f > amount_f:
        frappe.throw(_("TDS amount must be between 0 and the gross amount."))

    date = date or today()

    # Block GL posting into a closed or missing fiscal year.  date is resolved
    # above so the check always has a concrete value to test against.
    validate_fiscal_year(date, company)

    tds_payable = (
        _find_account(company, "Tax", "TDS Payable")
        or _find_account(company, "Payable", "TDS")
        or _find_account(company, "Tax")
    )
    ap_account = _find_account(company, "Payable")

    if not tds_payable:
        frappe.throw(_("No TDS Payable account found. Create an account named 'TDS Payable' under Liabilities."))
    if not ap_account:
        frappe.throw(_("No Accounts Payable account found for company {0}.").format(company))
    if not expense_account:
        frappe.throw(_("Expense account is required."))

    remark     = remarks or f"TDS on payment to {party} — Section {tds_section}"
    voucher_no = f"TDS-{(party or '')[:10].upper().replace(' ','-')}-{date}"

    gl_map = [
        {"account": expense_account, "debit": amount_f, "credit": 0,    "remarks": remark},
        {"account": tds_payable,     "debit": 0,        "credit": tds_f, "remarks": remark},
        {"account": ap_account,      "debit": 0,        "credit": net,   "remarks": remark},
    ]
    for e in gl_map:
        e.update({
            "posting_date": date,
            "voucher_type": "Journal Entry",
            "voucher_no": voucher_no,
            "company": company,
        })

    make_gl_entries(gl_map)
    frappe.db.commit()

    return {
        "voucher_no": voucher_no,
        "gross_amount": amount_f,
        "tds_amount": tds_f,
        "net_payable": net,
    }


@frappe.whitelist(allow_guest=False)
def get_tds_entries(
    company: str,
    from_date: str = None,
    to_date: str = None,
) -> list:
    """Return TDS Entry records saved to Frappe DB (not from PI tax lines)."""
    filters = [["company", "=", company]]
    if from_date:
        filters.append(["date", ">=", from_date])
    if to_date:
        filters.append(["date", "<=", to_date])
    return frappe.get_list(
        "TDS Entry",
        filters=filters,
        fields=["name", "date", "section", "party", "party_name", "pan", "amount",
                "tds_total", "status", "voucher_no", "challan_no", "challan_date"],
        order_by="date desc",
        limit=500,
    )


@frappe.whitelist(allow_guest=False, methods=["POST"])
def save_tds_entry(data: str) -> dict:
    """
    Save a TDS Entry document to Frappe DB.
    If expense_account is provided, also posts GL entries via create_tds_entry().
    """
    from zoho_books_clone.utils.access import require_module
    require_module("accounts", write=True)
    import json
    d = json.loads(data) if isinstance(data, str) else data

    amount    = flt(d.get("amount", 0))
    rate      = flt(d.get("rate", 0))
    surcharge = flt(d.get("surcharge", 0))
    cess      = flt(d.get("cess", 0))
    tds_total = flt(d.get("tds_total")) or round(amount * (rate + surcharge + cess) / 100, 2)

    # Resolve supplier display name
    party_id = d.get("party", "")
    party_name = d.get("party_name", "")
    if not party_name and party_id:
        try:
            party_name = frappe.db.get_value("Supplier", party_id, "supplier_name") or party_id
        except Exception:
            party_name = party_id

    entry = frappe.get_doc({
        "doctype":           "TDS Entry",
        "company":           d.get("company"),
        "date":              d.get("date") or today(),
        "section":           d.get("section", ""),
        "party":             party_id,
        "party_name":        party_name,
        "pan":               d.get("pan", ""),
        "nature_of_payment": d.get("nature_of_payment", ""),
        "amount":            amount,
        "rate":              rate,
        "surcharge":         surcharge,
        "cess":              cess,
        "tds_total":         tds_total,
        "expense_account":   d.get("expense_account", ""),
        "remarks":           d.get("remarks", ""),
    })
    entry.insert(ignore_permissions=True)

    # Post GL entries if expense_account is provided
    voucher_no = ""
    if d.get("expense_account") and amount > 0 and tds_total > 0:
        try:
            gl_result = create_tds_entry(
                company=d.get("company"),
                party=d.get("party", ""),
                expense_account=d.get("expense_account"),
                amount=str(amount),
                tds_amount=str(tds_total),
                tds_section=d.get("section", ""),
                date=d.get("date") or today(),
                remarks=d.get("remarks", ""),
            )
            voucher_no = gl_result.get("voucher_no", "")
            frappe.db.set_value("TDS Entry", entry.name, "voucher_no", voucher_no)
            frappe.db.commit()
        except Exception:
            pass

    return {"name": entry.name, "voucher_no": voucher_no, "tds_total": tds_total}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def update_tds_entry_status(
    entry_name: str,
    status: str,
    challan_no: str = "",
    challan_date: str = "",
) -> dict:
    """Mark a TDS Entry as Deposited or Filed and store challan details."""
    from zoho_books_clone.utils.access import require_module
    require_module("accounts", write=True)
    frappe.db.set_value("TDS Entry", entry_name, {
        "status": status,
        "challan_no": challan_no,
        "challan_date": challan_date,
    })
    frappe.db.commit()
    return {"name": entry_name, "status": status}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def save_irn(
    invoice_name: str,
    irn: str,
    ack_no: str = "",
    ack_date: str = "",
) -> dict:
    """Persist e-Invoice IRN directly to the Sales Invoice irn/ack fields."""
    from zoho_books_clone.utils.access import require_module
    require_module("invoices", write=True)
    if not invoice_name or not irn:
        frappe.throw(_("Invoice name and IRN are required."))

    frappe.db.set_value("Sales Invoice", invoice_name, {
        "irn":             irn,
        "ack_no":          ack_no or "",
        "ack_date":        ack_date or today(),
        "einvoice_status": "Generated",
    })
    frappe.db.commit()
    return {"invoice_name": invoice_name, "irn": irn, "saved": True}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def generate_irn(invoice_name: str) -> dict:
    """
    Generate an offline IRN (SHA-256 of company_gstin|fin_year|INV|invoice_name).
    Suitable for sandbox / demo use. Format matches the 64-char hex the NIC portal produces.
    """
    from zoho_books_clone.utils.access import require_module
    require_module("invoices", write=True)
    import hashlib
    import random
    from datetime import datetime as _dt

    if not invoice_name:
        frappe.throw(_("Invoice name is required."))

    doc = frappe.get_doc("Sales Invoice", invoice_name)

    if doc.docstatus != 1:
        frappe.throw(_("IRN can only be generated for submitted invoices."))
    if not doc.customer_gstin:
        frappe.throw(_("Customer GSTIN is required to generate IRN. Add Tax ID on the Customer record."))
    if doc.irn and doc.einvoice_status == "Generated":
        frappe.throw(_("IRN already generated for this invoice. Cancel the existing IRN first."))

    company_gstin = frappe.db.get_value("Books Company", doc.company, "gstin") or ""
    if not company_gstin:
        frappe.throw(_("Company GSTIN not configured. Set it under Books Company → GSTIN."))

    # Financial year in YYYY-YY format derived from posting_date
    p = doc.posting_date or today()
    yr = int(str(p)[:4])
    mo = int(str(p)[5:7])
    fin_year = f"{yr}{str(yr + 1)[-2:]}" if mo >= 4 else f"{yr - 1}{str(yr)[-2:]}"

    payload  = f"{company_gstin}|{fin_year}|INV|{invoice_name}"
    irn      = hashlib.sha256(payload.encode()).hexdigest()
    ack_date = today()
    ack_no   = _dt.now().strftime("%Y%m%d%H%M%S") + str(random.randint(1000, 9999))

    frappe.db.set_value("Sales Invoice", invoice_name, {
        "irn":             irn,
        "ack_no":          ack_no,
        "ack_date":        ack_date,
        "einvoice_status": "Generated",
    })
    frappe.db.commit()

    return {"irn": irn, "ack_no": ack_no, "ack_date": ack_date, "einvoice_status": "Generated"}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def cancel_irn(invoice_name: str) -> dict:
    """Mark an e-Invoice IRN as Cancelled (does not delete the IRN, preserves audit trail)."""
    from zoho_books_clone.utils.access import require_module
    require_module("invoices", write=True)
    if not invoice_name:
        frappe.throw(_("Invoice name is required."))

    irn = frappe.db.get_value("Sales Invoice", invoice_name, "irn")
    if not irn:
        frappe.throw(_("No IRN found for invoice {0}.").format(invoice_name))

    status = frappe.db.get_value("Sales Invoice", invoice_name, "einvoice_status")
    if status == "Cancelled":
        frappe.throw(_("IRN is already cancelled."))

    frappe.db.set_value("Sales Invoice", invoice_name, {"einvoice_status": "Cancelled"})
    frappe.db.commit()
    return {"invoice_name": invoice_name, "einvoice_status": "Cancelled"}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def save_irn_manual(
    invoice_name: str,
    irn: str,
    ack_no: str = "",
    ack_date: str = "",
) -> dict:
    """Save a manually entered IRN (obtained directly from the NIC/IRP portal)."""
    from zoho_books_clone.utils.access import require_module
    require_module("invoices", write=True)
    if not invoice_name or not irn:
        frappe.throw(_("Invoice name and IRN are required."))
    if len(irn) != 64:
        frappe.throw(_("IRN must be exactly 64 characters (hex). Got {0}.").format(len(irn)))
    if not ack_no:
        frappe.throw(_("Acknowledgement number is required."))

    frappe.db.set_value("Sales Invoice", invoice_name, {
        "irn":             irn,
        "ack_no":          ack_no,
        "ack_date":        ack_date or today(),
        "einvoice_status": "Generated",
    })
    frappe.db.commit()
    return {"invoice_name": invoice_name, "irn": irn, "ack_no": ack_no,
            "ack_date": ack_date or today(), "einvoice_status": "Generated"}