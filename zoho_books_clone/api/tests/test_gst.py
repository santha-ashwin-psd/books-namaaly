# Copyright (c) 2026, PS Digitise and Contributors
# See license.txt
"""
Tests for api/gst.py -- GST payment / TDS / e-Invoice IRN endpoints.

Covers: pay_gst (GL map construction, account resolution fallbacks, the
positive-total guard), create_tds_entry (net calc, TDS-in-range guard, GL
map), save_tds_entry (TDS Entry insert + conditional GL posting, swallowed
on failure), update_tds_entry_status, get_tds_entries filter building,
get_gst_accounts naming-convention fallback, and the IRN lifecycle
(generate/save/cancel/save_irn_manual) including generate_irn's
deterministic SHA-256 + financial-year derivation.

DB-free: frappe.db.* and make_gl_entries are mocked; authorization helpers
(require_module/assert_company) are mocked to isolate business logic --
utils/access.py's own behavior is covered in utils/tests/test_access.py.

Run with:
    bench run-tests --app zoho_books_clone --module zoho_books_clone.api.tests.test_gst
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import frappe

from zoho_books_clone.api import gst


def _no_auth():
    """Patch both authorization helpers as no-ops for a test."""
    return (
        patch("zoho_books_clone.utils.access.require_module"),
        patch("zoho_books_clone.utils.access.assert_company"),
    )


class TestPayGst(unittest.TestCase):

    @patch("zoho_books_clone.api.gst.make_gl_entries")
    @patch("zoho_books_clone.api.gst.validate_fiscal_year")
    @patch.object(frappe.db, "get_value")
    @patch("zoho_books_clone.utils.access.assert_company")
    @patch("zoho_books_clone.utils.access.require_module")
    def test_throws_when_total_not_positive(self, mock_req, mock_co, mock_get_value, mock_fy, mock_gl):
        with self.assertRaises(frappe.ValidationError):
            gst.pay_gst(company="VK Herbal", cgst_amount="0", sgst_amount="0", igst_amount="0")
        mock_gl.assert_not_called()

    @patch("zoho_books_clone.api.gst.make_gl_entries")
    @patch("zoho_books_clone.api.gst.validate_fiscal_year")
    @patch.object(frappe.db, "get_value")
    @patch("zoho_books_clone.utils.access.assert_company")
    @patch("zoho_books_clone.utils.access.require_module")
    def test_builds_one_gl_line_per_nonzero_tax_component_plus_bank(
        self, mock_req, mock_co, mock_get_value, mock_fy, mock_gl,
    ):
        # _find_account is called via frappe.db.get_value under the hood --
        # give it a distinct account name per call in the order pay_gst
        # resolves them: bank, cgst, sgst, igst.
        mock_get_value.side_effect = [
            "Bank - VK", "Output CGST - VK", "Output SGST - VK", "Output IGST - VK",
        ]
        result = gst.pay_gst(company="VK Herbal", cgst_amount="100", sgst_amount="100",
                              igst_amount="0", challan_ref="CHLN-1")
        gl_map = mock_gl.call_args.args[0]
        # 2 tax lines (cgst, sgst -- igst is zero, skipped) + 1 bank credit line
        self.assertEqual(len(gl_map), 3)
        accounts = {row["account"]: row for row in gl_map}
        self.assertEqual(accounts["Output CGST - VK"]["debit"], 100)
        self.assertEqual(accounts["Output SGST - VK"]["debit"], 100)
        self.assertEqual(accounts["Bank - VK"]["credit"], 200)
        self.assertEqual(result["total"], 200)

    @patch("zoho_books_clone.api.gst.make_gl_entries")
    @patch("zoho_books_clone.api.gst.validate_fiscal_year")
    @patch.object(frappe.db, "get_value", return_value=None)
    @patch("zoho_books_clone.utils.access.assert_company")
    @patch("zoho_books_clone.utils.access.require_module")
    def test_throws_when_no_bank_account_found(self, mock_req, mock_co, mock_get_value, mock_fy, mock_gl):
        with self.assertRaises(frappe.ValidationError):
            gst.pay_gst(company="VK Herbal", cgst_amount="100")

    @patch("zoho_books_clone.api.gst.make_gl_entries")
    @patch("zoho_books_clone.api.gst.validate_fiscal_year",
           side_effect=frappe.ValidationError("closed period"))
    @patch("zoho_books_clone.utils.access.assert_company")
    @patch("zoho_books_clone.utils.access.require_module")
    def test_closed_fiscal_year_blocks_payment(self, mock_req, mock_co, mock_fy, mock_gl):
        with self.assertRaises(frappe.ValidationError):
            gst.pay_gst(company="VK Herbal", cgst_amount="100")
        mock_gl.assert_not_called()

    @patch("zoho_books_clone.utils.access.require_module",
           side_effect=frappe.PermissionError("read-only"))
    def test_requires_accounts_write_access(self, mock_req):
        with self.assertRaises(frappe.PermissionError):
            gst.pay_gst(company="VK Herbal", cgst_amount="100")

    @patch("zoho_books_clone.utils.access.assert_company",
           side_effect=frappe.PermissionError("not your company"))
    def test_rejects_foreign_company(self, mock_co):
        with self.assertRaises(frappe.PermissionError):
            gst.pay_gst(company="Someone Else Co", cgst_amount="100")


class TestCreateTdsEntry(unittest.TestCase):

    @patch("zoho_books_clone.api.gst.make_gl_entries")
    @patch("zoho_books_clone.api.gst.validate_fiscal_year")
    @patch.object(frappe.db, "get_value")
    @patch("zoho_books_clone.utils.access.assert_company")
    @patch("zoho_books_clone.utils.access.require_module")
    def test_gl_map_debits_expense_credits_tds_and_payable(
        self, mock_req, mock_co, mock_get_value, mock_fy, mock_gl,
    ):
        mock_get_value.side_effect = ["TDS Payable - VK", "Creditors - VK"]
        result = gst.create_tds_entry(
            company="VK Herbal", party="SUPP-1", expense_account="Professional Fees - VK",
            amount="10000", tds_amount="1000", date="2026-08-01",
        )
        gl_map = mock_gl.call_args.args[0]
        rows = {r["account"]: r for r in gl_map}
        self.assertEqual(rows["Professional Fees - VK"]["debit"], 10000.0)
        self.assertEqual(rows["TDS Payable - VK"]["credit"], 1000.0)
        self.assertEqual(rows["Creditors - VK"]["credit"], 9000.0)
        self.assertEqual(result["net_payable"], 9000.0)

    @patch("zoho_books_clone.utils.access.assert_company")
    @patch("zoho_books_clone.utils.access.require_module")
    def test_throws_when_amount_not_positive(self, mock_req, mock_co):
        with self.assertRaises(frappe.ValidationError):
            gst.create_tds_entry(company="VK Herbal", party="SUPP-1",
                                  expense_account="Expense - VK", amount="0", tds_amount="0")

    @patch("zoho_books_clone.utils.access.assert_company")
    @patch("zoho_books_clone.utils.access.require_module")
    def test_throws_when_tds_exceeds_gross(self, mock_req, mock_co):
        with self.assertRaises(frappe.ValidationError):
            gst.create_tds_entry(company="VK Herbal", party="SUPP-1",
                                  expense_account="Expense - VK", amount="1000", tds_amount="1500")

    @patch("zoho_books_clone.api.gst.validate_fiscal_year")
    @patch.object(frappe.db, "get_value", return_value=None)
    @patch("zoho_books_clone.utils.access.assert_company")
    @patch("zoho_books_clone.utils.access.require_module")
    def test_throws_when_no_tds_payable_account(self, mock_req, mock_co, mock_get_value, mock_fy):
        with self.assertRaises(frappe.ValidationError):
            gst.create_tds_entry(company="VK Herbal", party="SUPP-1",
                                  expense_account="Expense - VK", amount="1000", tds_amount="100",
                                  date="2026-08-01")


class TestGetTdsEntries(unittest.TestCase):

    @patch.object(frappe, "get_list", return_value=[])
    def test_filters_built_from_optional_dates(self, mock_get_list):
        gst.get_tds_entries(company="VK Herbal", from_date="2026-08-01", to_date="2026-08-31")
        _, kwargs = mock_get_list.call_args
        self.assertIn(["company", "=", "VK Herbal"], kwargs["filters"])
        self.assertIn(["date", ">=", "2026-08-01"], kwargs["filters"])
        self.assertIn(["date", "<=", "2026-08-31"], kwargs["filters"])

    @patch.object(frappe, "get_list", return_value=[])
    def test_company_only_filter_when_dates_omitted(self, mock_get_list):
        gst.get_tds_entries(company="VK Herbal")
        _, kwargs = mock_get_list.call_args
        self.assertEqual(kwargs["filters"], [["company", "=", "VK Herbal"]])


class TestSaveTdsEntry(unittest.TestCase):

    @patch.object(frappe.db, "commit")
    @patch.object(frappe.db, "set_value")
    @patch("zoho_books_clone.api.gst.create_tds_entry")
    @patch.object(frappe, "get_doc")
    @patch("zoho_books_clone.utils.access.require_module")
    def test_posts_gl_when_expense_account_and_positive_amounts(
        self, mock_req, mock_get_doc, mock_create, mock_set_value, mock_commit,
    ):
        entry = MagicMock(name="TDS-0001")
        entry.name = "TDS-0001"
        mock_get_doc.return_value = entry
        mock_create.return_value = {"voucher_no": "TDS-SUPP1-2026-08-01"}
        import json
        result = gst.save_tds_entry(json.dumps({
            "company": "VK Herbal", "party": "SUPP-1", "amount": 10000, "rate": 10,
            "expense_account": "Professional Fees - VK",
        }))
        entry.insert.assert_called_once_with(ignore_permissions=True)
        mock_create.assert_called_once()
        self.assertEqual(result["voucher_no"], "TDS-SUPP1-2026-08-01")
        self.assertEqual(result["tds_total"], 1000.0)

    @patch.object(frappe, "get_doc")
    @patch("zoho_books_clone.utils.access.require_module")
    def test_no_gl_posting_without_expense_account(self, mock_req, mock_get_doc):
        entry = MagicMock()
        entry.name = "TDS-0002"
        mock_get_doc.return_value = entry
        import json
        with patch("zoho_books_clone.api.gst.create_tds_entry") as mock_create:
            result = gst.save_tds_entry(json.dumps({
                "company": "VK Herbal", "party": "SUPP-1", "amount": 10000, "rate": 10,
            }))
            mock_create.assert_not_called()
        self.assertEqual(result["voucher_no"], "")

    @patch.object(frappe, "get_doc")
    @patch("zoho_books_clone.api.gst.create_tds_entry", side_effect=Exception("account missing"))
    @patch("zoho_books_clone.utils.access.require_module")
    def test_gl_posting_failure_does_not_block_save(self, mock_req, mock_create, mock_get_doc):
        entry = MagicMock()
        entry.name = "TDS-0003"
        mock_get_doc.return_value = entry
        import json
        result = gst.save_tds_entry(json.dumps({
            "company": "VK Herbal", "party": "SUPP-1", "amount": 10000, "rate": 10,
            "expense_account": "Professional Fees - VK",
        }))
        entry.insert.assert_called_once()  # entry itself still saved
        self.assertEqual(result["voucher_no"], "")


class TestUpdateTdsEntryStatus(unittest.TestCase):

    @patch.object(frappe.db, "commit")
    @patch.object(frappe.db, "set_value")
    @patch("zoho_books_clone.utils.access.require_module")
    def test_sets_status_and_challan_details(self, mock_req, mock_set_value, mock_commit):
        gst.update_tds_entry_status("TDS-0001", "Deposited", "CHLN-99", "2026-08-15")
        mock_set_value.assert_called_once_with("TDS Entry", "TDS-0001", {
            "status": "Deposited", "challan_no": "CHLN-99", "challan_date": "2026-08-15",
        })


class TestGetGstAccounts(unittest.TestCase):

    @patch.object(frappe.db, "get_value")
    def test_falls_back_across_naming_conventions(self, mock_get_value):
        # First name tried for each ("Output CGST" etc) misses, second
        # ("CGST Payable" etc) hits.
        mock_get_value.side_effect = [
            None, "CGST Payable - VK",   # output_cgst
            None, "SGST Payable - VK",   # output_sgst
            None, "IGST Payable - VK",   # output_igst
            None, "CGST Input - VK",     # input_cgst
            None, "SGST Input - VK",     # input_sgst
            None, "IGST Input - VK",     # input_igst
        ]
        result = gst.get_gst_accounts(company="VK Herbal")
        self.assertEqual(result["output_cgst"], "CGST Payable - VK")
        self.assertEqual(result["input_igst"], "IGST Input - VK")

    @patch.object(frappe.db, "get_value", return_value=None)
    def test_missing_accounts_return_empty_string(self, mock_get_value):
        result = gst.get_gst_accounts(company="VK Herbal")
        self.assertEqual(result["output_cgst"], "")


class TestIrnLifecycle(unittest.TestCase):

    @patch.object(frappe.db, "commit")
    @patch.object(frappe.db, "set_value")
    @patch("zoho_books_clone.utils.access.require_module")
    def test_save_irn_stamps_fields(self, mock_req, mock_set_value, mock_commit):
        gst.save_irn("SINV-0001", "a" * 64, ack_no="ACK1", ack_date="2026-08-01")
        mock_set_value.assert_called_once()
        args = mock_set_value.call_args.args
        self.assertEqual(args[0], "Sales Invoice")
        self.assertEqual(args[1], "SINV-0001")
        self.assertEqual(args[2]["irn"], "a" * 64)
        self.assertEqual(args[2]["einvoice_status"], "Generated")

    @patch("zoho_books_clone.utils.access.require_module")
    def test_save_irn_requires_invoice_and_irn(self, mock_req):
        with self.assertRaises(frappe.ValidationError):
            gst.save_irn("", "")

    @patch.object(frappe.db, "commit")
    @patch.object(frappe.db, "set_value")
    @patch.object(frappe.db, "get_value", return_value="29ABCDE1234F1Z5")
    @patch.object(frappe, "get_doc")
    @patch("zoho_books_clone.utils.access.require_module")
    def test_generate_irn_produces_64_char_hex_deterministically(
        self, mock_req, mock_get_doc, mock_get_value, mock_set_value, mock_commit,
    ):
        inv = frappe._dict(docstatus=1, customer_gstin="27XXXXX0000X1Z1", irn=None,
                            einvoice_status=None, posting_date="2026-08-05",
                            company="VK Herbal")
        mock_get_doc.return_value = inv
        result1 = gst.generate_irn("SINV-0001")
        result2 = gst.generate_irn("SINV-0001")
        self.assertEqual(len(result1["irn"]), 64)
        int(result1["irn"], 16)  # valid hex
        self.assertEqual(result1["irn"], result2["irn"])  # deterministic for same inputs

    @patch("zoho_books_clone.utils.access.require_module")
    def test_generate_irn_requires_submitted_invoice(self, mock_req):
        with patch.object(frappe, "get_doc") as mock_get_doc:
            mock_get_doc.return_value = frappe._dict(docstatus=0, customer_gstin="X", irn=None,
                                                        einvoice_status=None)
            with self.assertRaises(frappe.ValidationError):
                gst.generate_irn("SINV-DRAFT")

    @patch("zoho_books_clone.utils.access.require_module")
    def test_generate_irn_requires_customer_gstin(self, mock_req):
        with patch.object(frappe, "get_doc") as mock_get_doc:
            mock_get_doc.return_value = frappe._dict(docstatus=1, customer_gstin=None,
                                                        irn=None, einvoice_status=None)
            with self.assertRaises(frappe.ValidationError):
                gst.generate_irn("SINV-0001")

    @patch("zoho_books_clone.utils.access.require_module")
    def test_generate_irn_blocks_regenerating_active_irn(self, mock_req):
        with patch.object(frappe, "get_doc") as mock_get_doc:
            mock_get_doc.return_value = frappe._dict(
                docstatus=1, customer_gstin="27XXXXX0000X1Z1",
                irn="a" * 64, einvoice_status="Generated",
            )
            with self.assertRaises(frappe.ValidationError):
                gst.generate_irn("SINV-0001")

    @patch.object(frappe.db, "commit")
    @patch.object(frappe.db, "set_value")
    @patch.object(frappe.db, "get_value", return_value=None)  # no company GSTIN configured
    @patch.object(frappe, "get_doc")
    @patch("zoho_books_clone.utils.access.require_module")
    def test_generate_irn_requires_company_gstin(self, mock_req, mock_get_doc, mock_get_value,
                                                    mock_set_value, mock_commit):
        mock_get_doc.return_value = frappe._dict(
            docstatus=1, customer_gstin="27XXXXX0000X1Z1", irn=None, einvoice_status=None,
        )
        with self.assertRaises(frappe.ValidationError):
            gst.generate_irn("SINV-0001")

    @patch.object(frappe.db, "commit")
    @patch.object(frappe.db, "set_value")
    @patch("zoho_books_clone.utils.access.require_module")
    def test_cancel_irn(self, mock_req, mock_set_value, mock_commit):
        with patch.object(frappe.db, "get_value", side_effect=["a" * 64, "Generated"]):
            gst.cancel_irn("SINV-0001")
        mock_set_value.assert_called_once_with("Sales Invoice", "SINV-0001",
                                                {"einvoice_status": "Cancelled"})

    @patch("zoho_books_clone.utils.access.require_module")
    def test_cancel_irn_requires_existing_irn(self, mock_req):
        with patch.object(frappe.db, "get_value", return_value=None):
            with self.assertRaises(frappe.ValidationError):
                gst.cancel_irn("SINV-0001")

    @patch("zoho_books_clone.utils.access.require_module")
    def test_cancel_irn_rejects_already_cancelled(self, mock_req):
        with patch.object(frappe.db, "get_value", side_effect=["a" * 64, "Cancelled"]):
            with self.assertRaises(frappe.ValidationError):
                gst.cancel_irn("SINV-0001")

    @patch.object(frappe.db, "commit")
    @patch.object(frappe.db, "set_value")
    @patch("zoho_books_clone.utils.access.require_module")
    def test_save_irn_manual_requires_64_char_irn(self, mock_req, mock_set_value, mock_commit):
        with self.assertRaises(frappe.ValidationError):
            gst.save_irn_manual("SINV-0001", "too-short", ack_no="ACK1")

    @patch("zoho_books_clone.utils.access.require_module")
    def test_save_irn_manual_requires_ack_no(self, mock_req):
        with self.assertRaises(frappe.ValidationError):
            gst.save_irn_manual("SINV-0001", "a" * 64, ack_no="")


if __name__ == "__main__":
    unittest.main()