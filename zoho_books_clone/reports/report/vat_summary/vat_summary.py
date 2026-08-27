import frappe
from zoho_books_clone.db.queries import get_vat_summary


def execute(filters=None):
    filters = filters or {}
    summary = get_vat_summary(filters["company"], filters["from_date"], filters["to_date"])

    columns = [
        {"label": "Line",           "fieldname": "line",           "fieldtype": "Data",     "width": 220},
        {"label": "Invoice Count",  "fieldname": "invoice_count",  "fieldtype": "Int",      "width": 130},
        {"label": "Amount",         "fieldname": "amount",         "fieldtype": "Currency", "width": 150},
    ]

    data = [
        {
            "line": "Output VAT (on Sales)",
            "invoice_count": summary["output_invoice_count"],
            "amount": summary["output_vat"],
        },
        {
            "line": "Input VAT (on Purchases)",
            "invoice_count": summary["input_invoice_count"],
            "amount": -summary["input_vat"],
        },
        {
            "line": "Net VAT Payable" if summary["net_vat_payable"] >= 0 else "Net VAT Refundable",
            "invoice_count": None,
            "amount": summary["net_vat_payable"],
        },
    ]

    return columns, data