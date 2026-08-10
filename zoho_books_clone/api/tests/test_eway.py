# Copyright (c) 2026, PS Digitise and Contributors
# See license.txt
"""
Tests for api/eway.py -- local-only E-Way Bill lifecycle endpoints (mock
NIC number, no real portal integration).

Covers: _validity_days (200km/day rule, including the round-up-to-next-day
boundary), _ui_status (Cancelled > Expired > Generated precedence), the
generate_eway_bill flow (docstatus guard, double-generation block, ODC vs
regular validity calc), cancel_eway_bill (idempotent on already-cancelled),
update_vehicle, extend_validity (single-extension rule, past-date base
clamp), and get_eway_json's NIC payload shape.

DB-free: frappe.db.* / frappe.get_doc are mocked; require_module is mocked
to isolate business logic from authorization (covered in
utils/tests/test_access.py).

Run with:
    bench run-tests --app zoho_books_clone --module zoho_books_clone.api.tests.test_eway
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import frappe

from zoho_books_clone.api import eway


class TestValidityDays(unittest.TestCase):

    def test_zero_distance_defaults_to_one_day(self):
        self.assertEqual(eway._validity_days(0), 1)

    def test_exactly_200km_is_one_day(self):
        self.assertEqual(eway._validity_days(200), 1)

    def test_201km_rounds_up_to_two_days(self):
        self.assertEqual(eway._validity_days(201), 2)

    def test_400km_is_two_days(self):
        self.assertEqual(eway._validity_days(400), 2)

    def test_negative_distance_clamped_to_zero_gives_one_day(self):
        self.assertEqual(eway._validity_days(-50), 1)


class TestUiStatus(unittest.TestCase):

    def test_cancelled_takes_precedence_over_everything(self):
        doc = frappe._dict(status="Cancelled", valid_upto="2020-01-01")
        self.assertEqual(eway._ui_status(doc), "Cancelled")

    def test_past_valid_upto_is_expired_even_if_status_says_generated(self):
        doc = frappe._dict(status="Generated", valid_upto="2020-01-01")
        self.assertEqual(eway._ui_status(doc), "Expired")

    def test_future_valid_upto_generated_stays_generated(self):
        doc = frappe._dict(status="Generated", valid_upto="2099-01-01")
        self.assertEqual(eway._ui_status(doc), "Generated")

    def test_no_valid_upto_falls_back_to_raw_status(self):
        doc = frappe._dict(status="Draft", valid_upto=None)
        self.assertEqual(eway._ui_status(doc), "Draft")

    def test_blank_status_defaults_to_draft(self):
        doc = frappe._dict(status=None, valid_upto=None)
        self.assertEqual(eway._ui_status(doc), "Draft")


class TestMockEwbNumber(unittest.TestCase):

    def test_produces_12_digit_numeric_string(self):
        num = eway._mock_ewb_number()
        self.assertEqual(len(num), 12)
        self.assertTrue(num.isdigit())


class TestGenerateEwayBill(unittest.TestCase):

    def _base_invoice(self, docstatus=1):
        return frappe._dict(
            name="SINV-0001", posting_date="2026-08-01", customer="CUST-1",
            customer_name="Acme Herbal Traders", grand_total=1180, company="VK Herbal",
            docstatus=docstatus,
        )

    @patch("zoho_books_clone.utils.access.require_module")
    def test_requires_invoice_transporter_and_vehicle(self, mock_req):
        with self.assertRaises(frappe.ValidationError):
            eway.generate_eway_bill(invoice_no="", transporter="", vehicle_no="")

    @patch.object(frappe.db, "exists", return_value=False)
    @patch("zoho_books_clone.utils.access.require_module")
    def test_throws_when_invoice_does_not_exist(self, mock_req, mock_exists):
        with self.assertRaises(frappe.ValidationError):
            eway.generate_eway_bill(invoice_no="SINV-GHOST", transporter="XYZ Logistics",
                                     vehicle_no="KA01AB1234")

    @patch.object(frappe.db, "get_value", return_value=0)  # draft invoice
    @patch.object(frappe.db, "exists", return_value=True)
    @patch("zoho_books_clone.utils.access.require_module")
    def test_throws_when_invoice_not_submitted(self, mock_req, mock_exists, mock_get_value):
        with self.assertRaises(frappe.ValidationError):
            eway.generate_eway_bill(invoice_no="SINV-DRAFT", transporter="XYZ Logistics",
                                     vehicle_no="KA01AB1234")

    def test_throws_when_active_ewb_already_exists(self):
        with patch("zoho_books_clone.utils.access.require_module"), \
             patch.object(frappe.db, "exists") as mock_exists, \
             patch.object(frappe.db, "get_value", return_value=1):
            # First exists() call = invoice exists; second = active EWB check
            mock_exists.side_effect = [True, "EWB-2026-00001"]
            with self.assertRaises(frappe.ValidationError):
                eway.generate_eway_bill(invoice_no="SINV-0001", transporter="XYZ Logistics",
                                         vehicle_no="KA01AB1234")

    @patch.object(frappe.db, "commit")
    @patch.object(frappe.db, "set_value")
    @patch.object(frappe.db, "get_value")
    @patch.object(frappe.db, "exists")
    @patch("zoho_books_clone.utils.access.require_module")
    def test_regular_cargo_uses_200km_rule(self, mock_req, mock_exists, mock_get_value,
                                            mock_set_value, mock_commit):
        mock_exists.side_effect = [True, None]  # invoice exists, no active EWB
        mock_get_value.return_value = 1  # docstatus submitted
        inv = self._base_invoice()
        ewb_doc = MagicMock()
        ewb_doc.name = "EWB-2026-00001"
        ewb_doc.ewb_no = "260801123456"
        ewb_doc.valid_upto = "2026-08-02"
        with patch.object(frappe, "get_doc") as mock_get_doc:
            mock_get_doc.side_effect = [inv, ewb_doc]
            result = eway.generate_eway_bill(
                invoice_no="SINV-0001", transporter="XYZ Logistics",
                vehicle_no="ka 01 ab 1234", distance_km=250, vehicle_type="Regular",
            )
        self.assertEqual(result["days"], 2)  # 250km -> ceil(250/200) = 2
        ewb_doc.insert.assert_called_once_with(ignore_permissions=False)

    @patch.object(frappe.db, "commit")
    @patch.object(frappe.db, "set_value")
    @patch.object(frappe.db, "get_value")
    @patch.object(frappe.db, "exists")
    @patch("zoho_books_clone.utils.access.require_module")
    def test_odc_uses_20km_rule_not_200km(self, mock_req, mock_exists, mock_get_value, mock_set_value, mock_commit):
        mock_exists.side_effect = [True, None]
        mock_get_value.return_value = 1
        inv = self._base_invoice()
        ewb_doc = MagicMock()
        ewb_doc.name = "EWB-2026-00002"
        ewb_doc.ewb_no = "260801654321"
        ewb_doc.valid_upto = "2026-08-04"
        with patch.object(frappe, "get_doc") as mock_get_doc:
            mock_get_doc.side_effect = [inv, ewb_doc]
            result = eway.generate_eway_bill(
                invoice_no="SINV-0001", transporter="XYZ Logistics",
                vehicle_no="KA01AB1234", distance_km=45, vehicle_type="Over Dimensional Cargo",
            )
        # 45km ODC: ceil(45/20) = 3 days, NOT ceil(45/200)=1
        self.assertEqual(result["days"], 3)

    @patch.object(frappe.db, "commit")
    @patch.object(frappe.db, "set_value", side_effect=Exception("column missing"))
    @patch.object(frappe.db, "get_value")
    @patch.object(frappe.db, "exists")
    @patch("zoho_books_clone.utils.access.require_module")
    def test_invoice_stamp_failure_does_not_block_ewb_creation(
        self, mock_req, mock_exists, mock_get_value, mock_set_value, mock_commit,
    ):
        # Best-effort stamp of ewaybill no. back onto the invoice -- wrapped
        # in try/except in the source, must not blow up the whole call.
        mock_exists.side_effect = [True, None]
        mock_get_value.return_value = 1
        inv = self._base_invoice()
        ewb_doc = MagicMock()
        ewb_doc.name = "EWB-2026-00003"
        ewb_doc.ewb_no = "260801000001"
        ewb_doc.valid_upto = "2026-08-02"
        with patch.object(frappe, "get_doc") as mock_get_doc:
            mock_get_doc.side_effect = [inv, ewb_doc]
            result = eway.generate_eway_bill(
                invoice_no="SINV-0001", transporter="XYZ Logistics", vehicle_no="KA01AB1234",
            )
        self.assertTrue(result["ok"])

    @patch.object(frappe.db, "commit")
    @patch.object(frappe.db, "set_value")
    @patch.object(frappe.db, "get_value")
    @patch.object(frappe.db, "exists")
    @patch("zoho_books_clone.utils.access.require_module")
    def test_vehicle_number_is_normalized(self, mock_req, mock_exists, mock_get_value,
                                           mock_set_value, mock_commit):
        mock_exists.side_effect = [True, None]
        mock_get_value.return_value = 1
        inv = self._base_invoice()
        ewb_doc = MagicMock()
        ewb_doc.name = "EWB-2026-00004"
        ewb_doc.ewb_no = "260801000002"
        ewb_doc.valid_upto = "2026-08-02"

        captured = {}
        def _get_doc_side_effect(*args, **kwargs):
            if args and isinstance(args[0], dict):
                captured.update(args[0])
                return ewb_doc
            return inv
        with patch.object(frappe, "get_doc", side_effect=_get_doc_side_effect):
            eway.generate_eway_bill(invoice_no="SINV-0001", transporter="XYZ Logistics",
                                     vehicle_no="ka 01 ab 1234")
        self.assertEqual(captured["vehicle_no"], "KA01AB1234")


class TestCancelEwayBill(unittest.TestCase):

    @patch.object(frappe.db, "commit")
    @patch.object(frappe.db, "set_value")
    @patch.object(frappe, "get_doc")
    @patch.object(frappe.db, "exists", return_value=True)
    @patch("zoho_books_clone.utils.access.require_module")
    def test_cancels_generated_ewb(self, mock_req, mock_exists, mock_get_doc, mock_set_value, mock_commit):
        doc = frappe._dict(name="EWB-0001", status="Generated", invoice_no="SINV-0001")
        doc.save = MagicMock()
        mock_get_doc.return_value = doc
        result = eway.cancel_eway_bill("EWB-0001", reason="Order returned")
        self.assertTrue(result["ok"])
        self.assertEqual(doc.status, "Cancelled")
        self.assertEqual(doc.cancellation_reason, "Order returned")
        doc.save.assert_called_once_with(ignore_permissions=False)

    @patch.object(frappe, "get_doc")
    @patch.object(frappe.db, "exists", return_value=True)
    @patch("zoho_books_clone.utils.access.require_module")
    def test_already_cancelled_is_idempotent_noop(self, mock_req, mock_exists, mock_get_doc):
        doc = frappe._dict(name="EWB-0001", status="Cancelled")
        doc.save = MagicMock()  # must not be reached -- early return
        mock_get_doc.return_value = doc
        result = eway.cancel_eway_bill("EWB-0001")
        self.assertTrue(result["ok"])
        doc.save.assert_not_called()

    @patch("zoho_books_clone.utils.access.require_module")
    def test_throws_for_unknown_ewb(self, mock_req):
        with patch.object(frappe.db, "exists", return_value=False):
            with self.assertRaises(frappe.ValidationError):
                eway.cancel_eway_bill("EWB-GHOST")


class TestUpdateVehicle(unittest.TestCase):

    @patch.object(frappe.db, "commit")
    @patch.object(frappe, "get_doc")
    @patch.object(frappe.db, "exists", return_value=True)
    @patch("zoho_books_clone.utils.access.require_module")
    def test_updates_and_normalizes_vehicle_number(self, mock_req, mock_exists, mock_get_doc, mock_commit):
        doc = frappe._dict(name="EWB-0001", status="Generated", vehicle_no="OLD123", transporter="Old Transporter")
        doc.save = MagicMock()
        mock_get_doc.return_value = doc
        result = eway.update_vehicle("EWB-0001", "ka 05 cd 9999", transporter="New Transporter")
        self.assertEqual(doc.vehicle_no, "KA05CD9999")
        self.assertEqual(doc.transporter, "New Transporter")
        self.assertEqual(result["vehicle_no"], "KA05CD9999")

    @patch.object(frappe, "get_doc")
    @patch.object(frappe.db, "exists", return_value=True)
    @patch("zoho_books_clone.utils.access.require_module")
    def test_cannot_update_non_generated_ewb(self, mock_req, mock_exists, mock_get_doc):
        doc = frappe._dict(name="EWB-0001", status="Cancelled", vehicle_no="OLD123")
        mock_get_doc.return_value = doc
        with self.assertRaises(frappe.ValidationError):
            eway.update_vehicle("EWB-0001", "KA05CD9999")


class TestExtendValidity(unittest.TestCase):

    @patch.object(frappe.db, "commit")
    @patch.object(frappe, "get_doc")
    @patch.object(frappe.db, "exists", return_value=True)
    @patch("zoho_books_clone.utils.access.require_module")
    def test_extends_from_future_valid_upto(self, mock_req, mock_exists, mock_get_doc, mock_commit):
        doc = frappe._dict(name="EWB-0001", status="Generated", valid_upto="2099-01-01", extended=0)
        doc.save = MagicMock()
        mock_get_doc.return_value = doc
        eway.extend_validity("EWB-0001", extra_days=3)
        self.assertEqual(str(doc.valid_upto), "2099-01-04")
        self.assertEqual(doc.extended, 1)

    @patch.object(frappe, "get_doc")
    @patch.object(frappe.db, "exists", return_value=True)
    @patch("zoho_books_clone.utils.access.require_module")
    def test_cannot_extend_twice(self, mock_req, mock_exists, mock_get_doc):
        doc = frappe._dict(name="EWB-0001", status="Generated", valid_upto="2099-01-01", extended=1)
        mock_get_doc.return_value = doc
        with self.assertRaises(frappe.ValidationError):
            eway.extend_validity("EWB-0001")

    @patch.object(frappe, "get_doc")
    @patch.object(frappe.db, "exists", return_value=True)
    @patch("zoho_books_clone.utils.access.require_module")
    def test_cannot_extend_non_generated_ewb(self, mock_req, mock_exists, mock_get_doc):
        doc = frappe._dict(name="EWB-0001", status="Expired", valid_upto="2020-01-01", extended=0)
        mock_get_doc.return_value = doc
        with self.assertRaises(frappe.ValidationError):
            eway.extend_validity("EWB-0001")


class TestGetEwayJson(unittest.TestCase):

    @patch.object(frappe.db, "get_value", return_value="VK Herbal Formulations Pvt Ltd")
    @patch.object(frappe, "get_doc")
    def test_payload_shape_and_item_mapping(self, mock_get_doc, mock_get_value):
        ewb = frappe._dict(
            name="EWB-0001", ewb_no="260801123456", invoice_no="SINV-0001",
            invoice_date="2026-08-01", from_gstin="27AAAAA0000A1Z1", to_gstin="29BBBBB0000B1Z2",
            supply_type="Outward", transaction_type="Regular", grand_total=1180,
            transporter="XYZ Logistics", vehicle_no="KA01AB1234", vehicle_type="Regular",
            valid_upto="2026-08-02", company="VK Herbal", customer_name="Acme Herbal Traders",
            customer="CUST-1",
        )
        item_row = frappe._dict(item_name="Ashwagandha Tablets", item_code="ITEM-1",
                                 description="", qty=10, uom="Box", amount=5000)
        item_row.get = lambda k, default=None: getattr(item_row, k, default)
        inv = frappe._dict(items=[item_row])

        def _get_doc_side_effect(doctype, name=None):
            if doctype == "E Way Bill":
                return ewb
            return inv
        mock_get_doc.side_effect = _get_doc_side_effect

        result = eway.get_eway_json("EWB-0001")
        import json
        payload = json.loads(result["content"])
        self.assertEqual(payload["docNo"], "SINV-0001")
        self.assertEqual(payload["supplyType"], "O")
        self.assertEqual(payload["ewbNo"], "260801123456")
        self.assertEqual(len(payload["itemList"]), 1)
        self.assertEqual(payload["itemList"][0]["productName"], "Ashwagandha Tablets")
        self.assertEqual(result["filename"], "EWB-260801123456.json")

    @patch.object(frappe.db, "get_value", return_value="")
    @patch.object(frappe, "get_doc")
    def test_missing_invoice_gives_empty_item_list_not_an_error(self, mock_get_doc, mock_get_value):
        ewb = frappe._dict(
            name="EWB-0002", ewb_no="260801000009", invoice_no="SINV-GONE",
            invoice_date=None, from_gstin=None, to_gstin=None, supply_type="Outward",
            transaction_type="Regular", grand_total=0, transporter="", vehicle_no="",
            vehicle_type="Regular", valid_upto=None, company="VK Herbal",
            customer_name="", customer="",
        )
        def _get_doc_side_effect(doctype, name=None):
            if doctype == "E Way Bill":
                return ewb
            raise frappe.DoesNotExistError
        mock_get_doc.side_effect = _get_doc_side_effect

        result = eway.get_eway_json("EWB-0002")
        import json
        payload = json.loads(result["content"])
        self.assertEqual(payload["itemList"], [])
        self.assertEqual(payload["fromGstin"], "URP")  # blank GSTIN falls back to "URP"


if __name__ == "__main__":
    unittest.main()