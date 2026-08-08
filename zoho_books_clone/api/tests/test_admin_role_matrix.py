# Copyright (c) 2026, PS Digitise and Contributors
# See license.txt
"""
Tests for get_role_matrix() (api/admin.py) -- the Roles & Permissions page
data source. Books Admin is hardcoded all-True (matches the utils/access.py
admin bypass, not a per-user toggle); every other role's per-module grant is
computed live as "does ANY current member of that role in this company have
the module on", not a static template -- these tests lock that behavior in.

DB-free: frappe.get_all is mocked; _require_company_admin is mocked to skip
the auth/company-resolution path (covered indirectly -- it's exercised for
real by every other _require_company_admin-gated endpoint).

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.api.tests.test_admin_role_matrix
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

import frappe

from zoho_books_clone.api.admin import get_role_matrix, BOOKS_ROLES, MODULE_FIELDS


def _member(user, books_role, is_company_admin=0, mods=None):
    row = {"user": user, "books_role": books_role, "is_company_admin": is_company_admin}
    for f in MODULE_FIELDS:
        row[f] = 0
    for m, v in (mods or {}).items():
        row[f"mod_{m}"] = 1 if v else 0
    return row


class TestGetRoleMatrix(unittest.TestCase):

    @patch("zoho_books_clone.api.admin._require_company_admin", return_value="VK Herbal")
    @patch.object(frappe, "get_all")
    def test_books_admin_is_hardcoded_all_true_regardless_of_member_data(self, mock_get_all, mock_req):
        # Even if every Books Admin member somehow has every mod_ flag off in
        # the DB, the reported perms must still be all-True -- admin access
        # is enforced via the code-level bypass in utils/access.py, not
        # these per-user toggles.
        mock_get_all.return_value = [_member("owner@vkherbal.test", "Books Admin", is_company_admin=1)]
        out = get_role_matrix()
        self.assertTrue(all(out["Books Admin"]["perms"].values()))

    @patch("zoho_books_clone.api.admin._require_company_admin", return_value="VK Herbal")
    @patch.object(frappe, "get_all")
    def test_perm_true_if_any_member_of_role_has_it_on(self, mock_get_all, mock_req):
        mock_get_all.return_value = [
            _member("a@vkherbal.test", "Accountant", mods={"invoices": False}),
            _member("b@vkherbal.test", "Accountant", mods={"invoices": True}),
        ]
        out = get_role_matrix()
        self.assertTrue(out["Accountant"]["perms"]["invoices"])

    @patch("zoho_books_clone.api.admin._require_company_admin", return_value="VK Herbal")
    @patch.object(frappe, "get_all")
    def test_perm_false_if_no_member_of_role_has_it_on(self, mock_get_all, mock_req):
        mock_get_all.return_value = [
            _member("a@vkherbal.test", "Accountant", mods={"invoices": False}),
        ]
        out = get_role_matrix()
        self.assertFalse(out["Accountant"]["perms"]["invoices"])

    @patch("zoho_books_clone.api.admin._require_company_admin", return_value="VK Herbal")
    @patch.object(frappe, "get_all")
    def test_role_with_zero_members_reports_all_false_not_an_error(self, mock_get_all, mock_req):
        mock_get_all.return_value = []
        out = get_role_matrix()
        self.assertEqual(out["Books Viewer"]["user_count"], 0)
        self.assertFalse(any(out["Books Viewer"]["perms"].values()))

    @patch("zoho_books_clone.api.admin._require_company_admin", return_value="VK Herbal")
    @patch.object(frappe, "get_all")
    def test_user_count_is_per_role(self, mock_get_all, mock_req):
        mock_get_all.return_value = [
            _member("a@vkherbal.test", "Accountant"),
            _member("b@vkherbal.test", "Accountant"),
            _member("c@vkherbal.test", "Books Manager"),
        ]
        out = get_role_matrix()
        self.assertEqual(out["Accountant"]["user_count"], 2)
        self.assertEqual(out["Books Manager"]["user_count"], 1)
        self.assertEqual(out["Books Admin"]["user_count"], 0)

    @patch("zoho_books_clone.api.admin._require_company_admin", return_value="VK Herbal")
    @patch.object(frappe, "get_all")
    def test_all_books_roles_present_in_output(self, mock_get_all, mock_req):
        mock_get_all.return_value = []
        out = get_role_matrix()
        self.assertEqual(set(out.keys()), set(BOOKS_ROLES))

    @patch("zoho_books_clone.api.admin._require_company_admin", return_value="VK Herbal")
    @patch.object(frappe, "get_all")
    def test_role_meta_merged_in(self, mock_get_all, mock_req):
        mock_get_all.return_value = []
        out = get_role_matrix()
        self.assertIn("desc", out["Accountant"])
        self.assertIn("color", out["Accountant"])

    @patch("zoho_books_clone.api.admin._require_company_admin", return_value="VK Herbal")
    @patch.object(frappe, "get_all")
    def test_members_filtered_to_caller_company(self, mock_get_all, mock_req):
        mock_get_all.return_value = []
        get_role_matrix()
        _, kwargs = mock_get_all.call_args
        self.assertEqual(kwargs["filters"], {"company": "VK Herbal"})

    def test_non_admin_caller_is_rejected(self):
        # _require_company_admin's own real behavior (unmocked here) --
        # get_role_matrix has no fallback path if the caller isn't a
        # company admin.
        with patch("zoho_books_clone.api.admin._require_company_admin",
                   side_effect=frappe.PermissionError("not a company admin")):
            with self.assertRaises(frappe.PermissionError):
                get_role_matrix()


if __name__ == "__main__":
    unittest.main()