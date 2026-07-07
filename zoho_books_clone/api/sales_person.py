"""
Sales Person API.

Mirrors the Customer / Vendor contact endpoints in api/books_data.py and the
generic doc CRUD in api/docs.py (get_doc / get_list / save_doc / delete_doc
already work for "Sales Person" once it's registered in
utils/access.DOCTYPE_MODULE — no extra CRUD wrapper needed here).

This module only adds the bits that are specific to Sales Person:
  - dashboard/list summary + KPI counts
  - bulk enable/disable
  - performance (invoices, revenue, commission) per sales person
  - top sales persons by revenue

All endpoints are company-scoped through Sales Invoice.company, same as the
Customer analytics in books_data.py.
"""
import frappe
from frappe import _
from frappe.utils import flt

from zoho_books_clone.api.session import _get_company
from zoho_books_clone.utils.access import require_module, can_read


@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_sales_persons_summary():
    """Counts + KPI tiles for the Sales Person list page (mirrors Customers.vue counts)."""
    if not can_read("Sales Person"):
        return {"all": 0, "active": 0, "disabled": 0, "total_commission_rate_avg": 0}

    rows = frappe.get_all(
        "Sales Person",
        fields=["name", "status", "disabled", "commission_rate"],
    )
    total = len(rows)
    disabled = sum(1 for r in rows if r.disabled)
    active = sum(1 for r in rows if not r.disabled and (r.status or "Active") == "Active")
    avg_commission = (
        sum(flt(r.commission_rate) for r in rows) / total if total else 0
    )
    return {
        "all": total,
        "active": active,
        "disabled": disabled,
        "avg_commission_rate": round(avg_commission, 2),
    }


@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_sales_person_outstanding():
    """Return {sales_person: outstanding_amount} across their open invoices.

    Requires a `sales_person` Link field on Sales Invoice (add via
    save_doc / DB migration) — returns {} gracefully until that field exists.
    """
    if not frappe.get_meta("Sales Invoice").has_field("sales_person"):
        return {}
    company = _get_company(frappe.session.user)
    rows = frappe.db.sql(
        """
        SELECT sales_person, COALESCE(SUM(outstanding_amount), 0) AS outstanding
        FROM `tabSales Invoice`
        WHERE docstatus=1 AND outstanding_amount>0 AND company=%s AND sales_person IS NOT NULL
        GROUP BY sales_person
        """,
        company,
        as_dict=True,
    )
    return {r.sales_person: float(r.outstanding or 0) for r in rows}


@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_sales_person_performance(sales_person):
    """Invoice count, total revenue and commission earned for one Sales Person.

    Commission earned = sum(grand_total) * commission_rate / 100, using the
    Sales Person's own default commission_rate.
    """
    if not can_read("Sales Person") or not can_read("Sales Invoice"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    doc = frappe.get_doc("Sales Person", sales_person)

    if not frappe.get_meta("Sales Invoice").has_field("sales_person"):
        return {
            "invoice_count": 0, "total_revenue": 0.0,
            "outstanding": 0.0, "commission_earned": 0.0,
            "note": "Add a 'sales_person' Link field to Sales Invoice to enable performance tracking.",
        }

    company = _get_company(frappe.session.user)
    row = frappe.db.sql(
        """
        SELECT COUNT(*) AS cnt,
               COALESCE(SUM(grand_total), 0) AS revenue,
               COALESCE(SUM(outstanding_amount), 0) AS outstanding
        FROM `tabSales Invoice`
        WHERE docstatus=1 AND sales_person=%s AND company=%s
        """,
        (sales_person, company),
        as_dict=True,
    )[0]

    revenue = flt(row.revenue)
    commission = round(revenue * flt(doc.commission_rate) / 100, 2)

    return {
        "invoice_count": int(row.cnt or 0),
        "total_revenue": revenue,
        "outstanding": flt(row.outstanding),
        "commission_earned": commission,
    }


@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_top_sales_persons(limit=5):
    """Top N sales persons by revenue (submitted Sales Invoices)."""
    if not frappe.get_meta("Sales Invoice").has_field("sales_person"):
        return []
    company = _get_company(frappe.session.user)
    limit = int(limit or 5)
    rows = frappe.db.sql(
        """
        SELECT sales_person, SUM(grand_total) AS total, COUNT(*) AS cnt
        FROM `tabSales Invoice`
        WHERE docstatus=1 AND company=%s AND sales_person IS NOT NULL
        GROUP BY sales_person
        ORDER BY total DESC
        LIMIT %s
        """,
        (company, limit),
        as_dict=True,
    )
    return [
        {"sales_person": r.sales_person, "revenue": float(r.total or 0), "invoice_count": int(r.cnt or 0)}
        for r in rows
    ]


@frappe.whitelist(allow_guest=False, methods=["POST"])
def bulk_set_sales_person_disabled(sales_person_names, disabled=1):
    """Bulk enable/disable Sales Persons (mirrors bulk_set_customer_disabled in docs.py)."""
    require_module("customers", write=True)

    import json
    if isinstance(sales_person_names, str):
        sales_person_names = json.loads(sales_person_names)
    disabled = int(disabled)

    done = 0
    for sp in (sales_person_names or []):
        try:
            frappe.db.set_value("Sales Person", sp, "disabled", disabled, update_modified=True)
            done += 1
        except Exception:
            pass
    frappe.db.commit()
    return {"updated": done, "disabled": disabled}


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def safe_delete_sales_person(name):
    """Delete a Sales Person only when it has no linked Sales Invoices.

    Mirrors safe_delete_party (Customer/Supplier) in api/docs.py, since
    Sales Person isn't a "party" doctype in Frappe's own sense.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    require_module("customers", write=True)

    blocking = []
    if frappe.get_meta("Sales Invoice").has_field("sales_person"):
        cnt = frappe.db.count("Sales Invoice", {"sales_person": name})
        if cnt:
            blocking.append(f"{cnt} Sales Invoice{'s' if cnt > 1 else ''}")

    if blocking:
        frappe.throw(
            _("Cannot delete {0} — it has existing transactions ({1}). Disable it instead.")
            .format(name, ", ".join(blocking))
        )

    # A Sales Person reporting to this one would be left dangling — clear the link.
    frappe.db.set_value("Sales Person", {"reports_to": name}, "reports_to", "")

    frappe.delete_doc("Sales Person", name, ignore_permissions=True, force=True)
    frappe.db.commit()
    return {"message": "deleted"}