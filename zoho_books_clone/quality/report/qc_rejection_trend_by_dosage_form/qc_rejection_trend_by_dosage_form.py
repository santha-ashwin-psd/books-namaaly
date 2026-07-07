"""
QC Rejection Trend by Dosage Form — Script Report
==================================================
Groups QC Inspection failures by item dosage_form (custom field on Item).
Reuses the status/docstatus convention from get_qc_dashboard_stats.

Modes (group_by filter):
  "Dosage Form"           — one row per dosage form, all time in range
  "Month"                 — one row per month, across all dosage forms
  "Dosage Form + Month"   — matrix: one row per dosage_form + month

Columns vary by mode but always include: total, failed, pass_rate.
"""
from __future__ import annotations

import frappe
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}
    group_by = filters.get("group_by") or "Dosage Form"
    columns  = get_columns(group_by)
    data     = get_data(filters, group_by)
    chart    = get_chart(data, group_by)
    return columns, data, None, chart


# ─── Columns ──────────────────────────────────────────────────────────────────

def get_columns(group_by: str) -> list:
    base = [
        {"label": "Total Inspections", "fieldname": "total",   "fieldtype": "Int",   "width": 120},
        {"label": "Failed",            "fieldname": "failed",  "fieldtype": "Int",   "width": 90},
        {"label": "Passed",            "fieldname": "passed",  "fieldtype": "Int",   "width": 90},
        {"label": "Pass Rate %",       "fieldname": "pass_rate","fieldtype": "Float", "width": 100, "precision": 1},
        {"label": "Rejection Rate %",  "fieldname": "reject_rate","fieldtype": "Float","width": 110, "precision": 1},
    ]
    if group_by == "Dosage Form":
        return [
            {"label": "Dosage Form", "fieldname": "dosage_form", "fieldtype": "Data", "width": 180},
        ] + base
    elif group_by == "Month":
        return [
            {"label": "Month", "fieldname": "month_label", "fieldtype": "Data", "width": 120},
        ] + base
    else:  # Dosage Form + Month
        return [
            {"label": "Dosage Form", "fieldname": "dosage_form",  "fieldtype": "Data", "width": 160},
            {"label": "Month",       "fieldname": "month_label",  "fieldtype": "Data", "width": 100},
        ] + base


# ─── Data ─────────────────────────────────────────────────────────────────────

def get_data(filters: dict, group_by: str) -> list:
    """
    Reuses the status field convention from get_qc_dashboard_stats:
      - submitted (docstatus=1) inspections are the source of truth for Pass/Fail
      - draft (docstatus=0) are counted as pending / total but not pass/fail

    dosage_form is a custom field on Item (confirmed in install.py and _resolve_template).
    """
    date_cond  = ""
    if filters.get("from_date") and filters.get("to_date"):
        date_cond = "AND qi.inspection_date BETWEEN %(from_date)s AND %(to_date)s"

    df_cond = ""
    if filters.get("dosage_form"):
        df_cond = "AND it.dosage_form = %(dosage_form)s"

    if group_by == "Dosage Form":
        sql = f"""
            SELECT
                COALESCE(it.dosage_form, '(No Dosage Form)') AS dosage_form,
                COUNT(*)                                      AS total,
                SUM(CASE WHEN qi.status='Pass' THEN 1 ELSE 0 END) AS passed,
                SUM(CASE WHEN qi.status='Fail' THEN 1 ELSE 0 END) AS failed
            FROM `tabQC Inspection` qi
            LEFT JOIN `tabItem` it ON it.name = qi.item
            WHERE qi.docstatus = 1
            {date_cond}
            {df_cond}
            GROUP BY COALESCE(it.dosage_form, '(No Dosage Form)')
            ORDER BY failed DESC
        """
        rows = frappe.db.sql(sql, filters, as_dict=True)
        return _enrich(rows, key="dosage_form")

    elif group_by == "Month":
        sql = f"""
            SELECT
                DATE_FORMAT(qi.inspection_date, '%%Y-%%m') AS month_key,
                COUNT(*)                                    AS total,
                SUM(CASE WHEN qi.status='Pass' THEN 1 ELSE 0 END) AS passed,
                SUM(CASE WHEN qi.status='Fail' THEN 1 ELSE 0 END) AS failed
            FROM `tabQC Inspection` qi
            LEFT JOIN `tabItem` it ON it.name = qi.item
            WHERE qi.docstatus = 1
            {date_cond}
            {df_cond}
            GROUP BY DATE_FORMAT(qi.inspection_date, '%%Y-%%m')
            ORDER BY month_key ASC
        """
        rows = frappe.db.sql(sql, filters, as_dict=True)
        for r in rows:
            r["month_label"] = _fmt_month(r.get("month_key", ""))
        return _enrich(rows, key="month_label")

    else:  # Dosage Form + Month
        sql = f"""
            SELECT
                COALESCE(it.dosage_form, '(No Dosage Form)')   AS dosage_form,
                DATE_FORMAT(qi.inspection_date, '%%Y-%%m')     AS month_key,
                COUNT(*)                                        AS total,
                SUM(CASE WHEN qi.status='Pass' THEN 1 ELSE 0 END) AS passed,
                SUM(CASE WHEN qi.status='Fail' THEN 1 ELSE 0 END) AS failed
            FROM `tabQC Inspection` qi
            LEFT JOIN `tabItem` it ON it.name = qi.item
            WHERE qi.docstatus = 1
            {date_cond}
            {df_cond}
            GROUP BY COALESCE(it.dosage_form, '(No Dosage Form)'), DATE_FORMAT(qi.inspection_date, '%%Y-%%m')
            ORDER BY dosage_form ASC, month_key ASC
        """
        rows = frappe.db.sql(sql, filters, as_dict=True)
        for r in rows:
            r["month_label"] = _fmt_month(r.get("month_key", ""))
        return _enrich(rows, key="dosage_form")


def _enrich(rows: list, key: str) -> list:
    """Add pass_rate and reject_rate to each row."""
    result = []
    for r in rows:
        t = r.get("total") or 0
        f = r.get("failed") or 0
        p = r.get("passed") or 0
        r["pass_rate"]   = round(flt(p) / t * 100, 1) if t else 0.0
        r["reject_rate"] = round(flt(f) / t * 100, 1) if t else 0.0
        result.append(r)
    return result


def _fmt_month(month_key: str) -> str:
    """Convert '2026-07' → 'Jul 2026'."""
    try:
        from datetime import datetime
        return datetime.strptime(month_key, "%Y-%m").strftime("%b %Y")
    except Exception:
        return month_key


# ─── Chart ────────────────────────────────────────────────────────────────────

def get_chart(data: list, group_by: str) -> dict | None:
    if not data:
        return None

    if group_by == "Dosage Form":
        labels = [r.get("dosage_form", "") for r in data[:15]]
    elif group_by == "Month":
        labels = [r.get("month_label", "") for r in data[:15]]
    else:
        # For combined, show dosage_form + month as label
        labels = [f"{r.get('dosage_form','')} / {r.get('month_label','')}" for r in data[:15]]

    fail_vals   = [r["failed"]      for r in data[:15]]
    reject_vals = [r["reject_rate"] for r in data[:15]]

    return {
        "data": {
            "labels":   labels,
            "datasets": [
                {"name": "Failed Count",    "values": fail_vals,   "chartType": "bar"},
                {"name": "Rejection Rate %","values": reject_vals, "chartType": "line"},
            ],
        },
        "type":   "axis-mixed",
        "colors": ["#dc2626", "#f59e0b"],
        "title":  "QC Rejection Trend by Dosage Form",
    }
