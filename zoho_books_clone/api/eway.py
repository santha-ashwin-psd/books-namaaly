# Copyright (c) 2026
# E-Way Bill lifecycle endpoints.
#
# This is a local-only implementation: we don't talk to the NIC portal,
# we generate a deterministic 12-digit mock EWB number and produce a JSON
# payload that conforms to the NIC schema so it can be uploaded manually.

import json
import random
import frappe
from frappe import _
from frappe.utils import getdate, today, add_days, flt, now_datetime


# ----- helpers -----------------------------------------------------------

def _get_ewb(name: str):
    if not name:
        frappe.throw(_("E-Way Bill name is required"))
    if not frappe.db.exists("E Way Bill", name):
        frappe.throw(_("E-Way Bill {0} not found").format(name))
    return frappe.get_doc("E Way Bill", name)


def _validity_days(distance_km: float) -> int:
    """NIC rule: 1 day per 200 km for regular cargo, 1 day per 20 km for ODC."""
    d = max(0, float(distance_km or 0))
    if d <= 0:
        return 1
    return max(1, int((d + 199) // 200))


def _mock_ewb_number() -> str:
    """12-digit mock EWB number — first 6 from timestamp, last 6 random."""
    now = now_datetime()
    prefix = f"{now.year % 100:02d}{now.month:02d}{now.day:02d}"
    suffix = f"{random.randint(0, 999999):06d}"
    return prefix + suffix


def _ui_status(doc) -> str:
    if doc.status == "Cancelled":
        return "Cancelled"
    if doc.valid_upto and getdate(doc.valid_upto) < getdate(today()):
        return "Expired"
    if doc.status == "Generated":
        return "Generated"
    return doc.status or "Draft"


def _invoice_party_gstin(inv) -> tuple[str, str]:
    """Return (from_gstin, to_gstin) for a Sales Invoice."""
    company_gstin = ""
    customer_gstin = ""
    try:
        company_gstin = frappe.db.get_value("Books Company", inv.company, "gstin") or ""
    except Exception:
        pass
    try:
        customer_gstin = frappe.db.get_value("Customer", inv.customer, "gstin") or ""
    except Exception:
        pass
    return company_gstin, customer_gstin


# ----- list / stats ------------------------------------------------------

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_eway_bills(status=None, limit=500):
    """List E-Way Bills enriched with effective status (Expired vs Generated)."""
    rows = frappe.get_all(
        "E Way Bill",
        fields=[
            "name", "ewb_no", "invoice_no", "invoice_date", "customer", "customer_name",
            "transporter", "vehicle_no", "vehicle_type", "supply_type", "transaction_type",
            "from_gstin", "to_gstin", "grand_total", "valid_upto", "status", "creation",
            "extended", "cancellation_reason",
        ],
        order_by="creation desc",
        limit_page_length=int(limit or 500),
    )
    out = []
    for r in rows:
        ui = _ui_status(frappe._dict(r))
        if status and status != "all" and status != ui:
            continue
        out.append({**r, "ui_status": ui})
    return out


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_eway_stats(company=None):
    """Counters for the page header summary strip."""
    co = company or frappe.db.get_default("company") or ""
    si_filters = {"docstatus": 1, "is_return": 0}
    if co:
        si_filters["company"] = co
    si_count = frappe.db.count("Sales Invoice", si_filters)
    si_total = frappe.db.sql(
        f"""SELECT IFNULL(SUM(grand_total),0) FROM `tabSales Invoice`
            WHERE docstatus=1 AND is_return=0 {('AND company=%s' if co else '')}""",
        (co,) if co else (),
    )[0][0]

    rows = frappe.get_all(
        "E Way Bill",
        fields=["name", "status", "valid_upto"],
        limit_page_length=5000,
    )
    today_d = getdate(today())
    gen = expired = cancelled = expiring_soon = 0
    for r in rows:
        ui = _ui_status(frappe._dict(r))
        if ui == "Cancelled":
            cancelled += 1
        elif ui == "Expired":
            expired += 1
        elif ui == "Generated":
            gen += 1
            if r.valid_upto and (getdate(r.valid_upto) - today_d).days <= 1:
                expiring_soon += 1

    pending = max(0, si_count - gen - expired - cancelled)
    return {
        "total_invoices": si_count,
        "total_value": flt(si_total),
        "generated": gen,
        "pending": pending,
        "expired": expired,
        "cancelled": cancelled,
        "expiring_soon": expiring_soon,
    }


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_pending_invoices(company=None, limit=200):
    """Sales invoices that don't yet have an E-Way Bill (or whose EWB is cancelled/expired)."""
    co = company or frappe.db.get_default("company") or ""
    cond = "WHERE si.docstatus=1 AND si.is_return=0"
    params = []
    if co:
        cond += " AND si.company=%s"
        params.append(co)

    rows = frappe.db.sql(f"""
        SELECT si.name, si.posting_date, si.customer, si.customer_name,
               si.grand_total, si.company
        FROM `tabSales Invoice` si
        LEFT JOIN `tabE Way Bill` ewb
            ON ewb.invoice_no = si.name AND ewb.status = 'Generated'
        {cond} AND ewb.name IS NULL
        ORDER BY si.posting_date DESC
        LIMIT {int(limit)}
    """, tuple(params), as_dict=True)
    return rows


# ----- detail ------------------------------------------------------------

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_eway_bill(name):
    doc = _get_ewb(name)
    today_d = getdate(today())
    days_left = None
    if doc.valid_upto:
        days_left = (getdate(doc.valid_upto) - today_d).days

    return {
        "name": doc.name,
        "ewb_no": doc.ewb_no,
        "invoice_no": doc.invoice_no,
        "invoice_date": str(doc.invoice_date) if doc.invoice_date else None,
        "customer": doc.customer,
        "customer_name": doc.customer_name,
        "grand_total": flt(doc.grand_total),
        "transporter": doc.transporter,
        "vehicle_no": doc.vehicle_no,
        "vehicle_type": doc.vehicle_type,
        "supply_type": doc.supply_type,
        "transaction_type": doc.transaction_type,
        "from_gstin": doc.from_gstin,
        "to_gstin": doc.to_gstin,
        "status": doc.status,
        "ui_status": _ui_status(doc),
        "valid_upto": str(doc.valid_upto) if doc.valid_upto else None,
        "days_left": days_left,
        "company": doc.company,
        "creation": str(doc.creation),
        "extended": bool(doc.extended),
        "cancellation_reason": doc.cancellation_reason,
    }


# ----- lifecycle ---------------------------------------------------------

@frappe.whitelist(allow_guest=False, methods=["POST"])
def generate_eway_bill(invoice_no, transporter, vehicle_no, distance_km=0,
                      supply_type="Outward", transaction_type="Regular",
                      vehicle_type="Regular"):
    """Generate an E-Way Bill for a Sales Invoice.

    Creates an `E Way Bill` record with a mock 12-digit number and a validity
    period computed from distance_km (1 day per 200 km, or 1 day per 20 km for ODC).
    """
    from zoho_books_clone.utils.access import require_module
    require_module("taxes", write=True)
    if not (invoice_no and transporter and vehicle_no):
        frappe.throw(_("Invoice, transporter and vehicle number are required"))
    if not frappe.db.exists("Sales Invoice", invoice_no):
        frappe.throw(_("Invoice {0} does not exist").format(invoice_no))

    inv_docstatus = frappe.db.get_value("Sales Invoice", invoice_no, "docstatus")
    if inv_docstatus != 1:
        frappe.throw(_("Cannot generate an E-Way Bill against an invoice that isn't submitted"))

    # Block double-generation against the same invoice
    existing = frappe.db.exists("E Way Bill",
                                {"invoice_no": invoice_no, "status": "Generated"})
    if existing:
        frappe.throw(_("An active E-Way Bill already exists for {0}: {1}")
                     .format(invoice_no, existing))

    inv = frappe.get_doc("Sales Invoice", invoice_no)
    from_g, to_g = _invoice_party_gstin(inv)

    # validity calc — ODC = 1 day / 20 km
    if vehicle_type == "Over Dimensional Cargo":
        days = max(1, int((float(distance_km or 0) + 19) // 20))
    else:
        days = _validity_days(distance_km)

    ewb = frappe.get_doc({
        "doctype": "E Way Bill",
        "naming_series": "EWB-.YYYY.-.#####",
        "invoice_no": invoice_no,
        "invoice_date": inv.posting_date,
        "customer": inv.customer,
        "customer_name": inv.customer_name,
        "grand_total": flt(inv.grand_total),
        "transporter": transporter,
        "vehicle_no": vehicle_no.upper().replace(" ", ""),
        "vehicle_type": vehicle_type,
        "supply_type": supply_type,
        "transaction_type": transaction_type,
        "from_gstin": from_g,
        "to_gstin": to_g,
        "ewb_no": _mock_ewb_number(),
        "valid_upto": add_days(today(), days),
        "status": "Generated",
        "company": inv.company,
    })
    ewb.insert(ignore_permissions=False)

    # Stamp the EWB number back onto the invoice
    try:
        frappe.db.set_value("Sales Invoice", invoice_no, "ewaybill",
                            ewb.ewb_no, update_modified=False)
    except Exception:
        pass

    frappe.db.commit()
    return {
        "ok": True,
        "name": ewb.name,
        "ewb_no": ewb.ewb_no,
        "valid_upto": str(ewb.valid_upto),
        "days": days,
    }


@frappe.whitelist(allow_guest=False, methods=["POST"])
def cancel_eway_bill(name, reason=""):
    from zoho_books_clone.utils.access import require_module
    require_module("taxes", write=True)
    doc = _get_ewb(name)
    if doc.status == "Cancelled":
        return {"ok": True, "message": "Already cancelled"}
    doc.status = "Cancelled"
    if reason:
        doc.cancellation_reason = reason
    doc.save(ignore_permissions=False)
    if doc.invoice_no:
        try:
            frappe.db.set_value("Sales Invoice", doc.invoice_no, "ewaybill",
                                None, update_modified=False)
        except Exception:
            pass
    frappe.db.commit()
    return {"ok": True, "message": f"{name} cancelled"}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def update_vehicle(name, vehicle_no, transporter=None):
    from zoho_books_clone.utils.access import require_module
    require_module("taxes", write=True)
    doc = _get_ewb(name)
    if doc.status != "Generated":
        frappe.throw(_("Cannot update — E-Way Bill is {0}").format(doc.status))
    doc.vehicle_no = (vehicle_no or "").upper().replace(" ", "")
    if transporter is not None:
        doc.transporter = transporter
    doc.save(ignore_permissions=False)
    frappe.db.commit()
    return {"ok": True, "vehicle_no": doc.vehicle_no, "transporter": doc.transporter}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def extend_validity(name, extra_days=1):
    """Extend the EWB validity by N days (NIC permits one extension per EWB)."""
    from zoho_books_clone.utils.access import require_module
    require_module("taxes", write=True)
    doc = _get_ewb(name)
    if doc.status != "Generated":
        frappe.throw(_("Cannot extend — E-Way Bill is {0}").format(doc.status))
    if doc.extended:
        frappe.throw(_("E-Way Bill {0} has already been extended once — NIC rules "
                       "permit only a single extension per EWB").format(name))
    n = max(1, int(extra_days or 1))
    base = getdate(doc.valid_upto) if doc.valid_upto else getdate(today())
    if base < getdate(today()):
        base = getdate(today())
    doc.valid_upto = add_days(base, n)
    doc.extended = 1
    doc.save(ignore_permissions=False)
    frappe.db.commit()
    return {"ok": True, "valid_upto": str(doc.valid_upto)}


# ----- NIC JSON export ---------------------------------------------------

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_eway_json(name):
    """Return an NIC-schema JSON payload that can be uploaded to the portal."""
    doc = _get_ewb(name)
    try:
        inv = frappe.get_doc("Sales Invoice", doc.invoice_no) if doc.invoice_no else None
    except Exception:
        inv = None

    items = []
    if inv:
        for r in (inv.items or []):
            items.append({
                "productName": r.item_name or r.item_code,
                "productDesc": r.description or r.item_name or "",
                "hsnCode": r.get("hsn_code") or "",
                "quantity": flt(r.qty),
                "qtyUnit": r.uom or "NOS",
                "taxableAmount": flt(r.amount),
            })

    payload = {
        "supplyType": "O" if (doc.supply_type or "Outward") == "Outward" else "I",
        "subSupplyType": "1",  # Supply
        "docType": "INV",
        "docNo": doc.invoice_no or "",
        "docDate": str(doc.invoice_date) if doc.invoice_date else "",
        "fromGstin": doc.from_gstin or "URP",
        "fromTrdName": frappe.db.get_value("Books Company", doc.company, "company_name") or doc.company or "",
        "toGstin": doc.to_gstin or "URP",
        "toTrdName": doc.customer_name or doc.customer or "",
        "transactionType": {"Regular": 1, "Bill To Ship To": 2,
                            "Bill From Dispatch From": 3, "Combination": 4}.get(doc.transaction_type or "Regular", 1),
        "totalValue": flt(doc.grand_total),
        "transporterId": doc.transporter or "",
        "transporterName": doc.transporter or "",
        "vehicleNo": doc.vehicle_no or "",
        "vehicleType": "O" if doc.vehicle_type == "Over Dimensional Cargo" else "R",
        "ewbNo": doc.ewb_no,
        "validUpto": str(doc.valid_upto) if doc.valid_upto else "",
        "itemList": items,
    }
    return {"filename": f"EWB-{doc.ewb_no or doc.name}.json",
            "content": json.dumps(payload, indent=2)}