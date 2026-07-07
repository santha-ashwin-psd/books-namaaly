"""
QC Pass Rate by Supplier — Script Report
=========================================
Reuses aggregation logic from get_qc_dashboard_stats (api/qc.py) extended
with supplier join via Purchase Receipt / Purchase Invoice reference.

Columns:
  Supplier | Supplier Name | Total Inspections | Passed | Failed | Pending | Pass Rate %
"""
from __future__ import annotations

import frappe
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data    = get_data(filters)
    chart   = get_chart(data)
    return columns, data, None, chart


def get_columns():
    return [
        {"label": "Supplier",           "fieldname": "supplier",    "fieldtype": "Link",    "options": "Supplier", "width": 160},
        {"label": "Supplier Name",      "fieldname": "supplier_name","fieldtype": "Data",   "width": 200},
        {"label": "Total Inspections",  "fieldname": "total",       "fieldtype": "Int",     "width": 120},
        {"label": "Passed",             "fieldname": "passed",      "fieldtype": "Int",     "width": 80},
        {"label": "Failed",             "fieldname": "failed",      "fieldtype": "Int",     "width": 80},
        {"label": "Pending",            "fieldname": "pending",     "fieldtype": "Int",     "width": 80},
        {"label": "Pass Rate %",        "fieldname": "pass_rate",   "fieldtype": "Float",   "width": 100,
         "precision": 1},
    ]


def get_data(filters: dict) -> list:
    """
    Join QC Inspection → Purchase Receipt/Purchase Invoice → Supplier.
    Reuses the same submitted-docstatus=1 filter convention from
    get_qc_dashboard_stats, adding date range and optional supplier filter.
    """
    date_cond = (
        "AND qi.inspection_date BETWEEN %(from_date)s AND %(to_date)s"
        if filters.get("from_date") and filters.get("to_date")
        else ""
    )
    supplier_cond = "AND pr.supplier = %(supplier)s" if filters.get("supplier") else ""
    type_cond     = "AND qi.inspection_type = %(inspection_type)s" if filters.get("inspection_type") else ""

    # Purchase Receipt path
    pr_sql = f"""
        SELECT
            pr.supplier                           AS supplier,
            pr.supplier_name                      AS supplier_name,
            COUNT(*)                              AS total,
            SUM(CASE WHEN qi.status='Pass' THEN 1 ELSE 0 END)    AS passed,
            SUM(CASE WHEN qi.status='Fail' THEN 1 ELSE 0 END)    AS failed,
            SUM(CASE WHEN qi.docstatus=0     THEN 1 ELSE 0 END)  AS pending
        FROM `tabQC Inspection` qi
        INNER JOIN `tabPurchase Receipt` pr
            ON pr.name = qi.reference_name
            AND qi.reference_type = 'Purchase Receipt'
        WHERE qi.docstatus IN (0,1)
        {date_cond}
        {supplier_cond}
        {type_cond}
        GROUP BY pr.supplier, pr.supplier_name
    """

    # Purchase Invoice path (alternate incoming reference)
    pi_sql = f"""
        SELECT
            pi.supplier                           AS supplier,
            pi.supplier_name                      AS supplier_name,
            COUNT(*)                              AS total,
            SUM(CASE WHEN qi.status='Pass' THEN 1 ELSE 0 END)    AS passed,
            SUM(CASE WHEN qi.status='Fail' THEN 1 ELSE 0 END)    AS failed,
            SUM(CASE WHEN qi.docstatus=0     THEN 1 ELSE 0 END)  AS pending
        FROM `tabQC Inspection` qi
        INNER JOIN `tabPurchase Invoice` pi
            ON pi.name = qi.reference_name
            AND qi.reference_type = 'Purchase Invoice'
        WHERE qi.docstatus IN (0,1)
        {date_cond}
        {supplier_cond}
        {type_cond}
        GROUP BY pi.supplier, pi.supplier_name
    """

    pr_rows = frappe.db.sql(pr_sql, filters, as_dict=True)
    pi_rows = frappe.db.sql(pi_sql, filters, as_dict=True)

    # Merge: aggregate both sources per supplier
    merged: dict[str, dict] = {}
    for row in pr_rows + pi_rows:
        sup = row["supplier"]
        if sup not in merged:
            merged[sup] = {
                "supplier":      sup,
                "supplier_name": row["supplier_name"] or sup,
                "total":   0, "passed": 0, "failed": 0, "pending": 0,
            }
        merged[sup]["total"]   += row["total"]   or 0
        merged[sup]["passed"]  += row["passed"]  or 0
        merged[sup]["failed"]  += row["failed"]  or 0
        merged[sup]["pending"] += row["pending"] or 0

    result = []
    for rec in sorted(merged.values(), key=lambda r: r["total"], reverse=True):
        t = rec["total"]
        rec["pass_rate"] = round(flt(rec["passed"]) / t * 100, 1) if t else 0.0
        result.append(rec)

    return result


def get_chart(data: list) -> dict | None:
    if not data:
        return None
    labels    = [r["supplier_name"] or r["supplier"] for r in data[:15]]
    pass_vals = [r["passed"]  for r in data[:15]]
    fail_vals = [r["failed"]  for r in data[:15]]
    return {
        "data": {
            "labels":   labels,
            "datasets": [
                {"name": "Passed", "values": pass_vals, "chartType": "bar"},
                {"name": "Failed", "values": fail_vals, "chartType": "bar"},
            ],
        },
        "type":      "bar",
        "barOptions": {"stacked": True},
        "colors":    ["#16a34a", "#dc2626"],
        "title":     "QC Pass / Fail by Supplier",
    }
