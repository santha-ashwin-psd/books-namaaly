# Copyright (c) 2026, PS Digitise and Contributors
# See license.txt
"""
Tests for the custom role/module authorization layer
(utils/access.py) -- module_for(), _membership()'s bypass/no_member/admin/
readonly resolution and the levels_customized additive-vs-authoritative
merge logic, can_read/can_write/can_create/can_edit/can_delete,
_can_at_level's unmapped-doctype fallback, assert_can's action->threshold
routing, require_module, require_write, is_readonly, and assert_company.

This is the backbone of the Phase 0-6 permissions rollout referenced in the
module docstring -- these tests lock in that six-phase investment.

DB-free: frappe.db.get_value / frappe.get_roles are mocked; no real
Books Company Member rows are created.

Run with:
    bench run-tests --app zoho_books_clone \
        --module zoho_books_clone.utils.tests.test_access
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

import frappe

from zoho_books_clone.utils import access


def _member_row(books_role="Accountant", is_company_admin=0, levels_customized=0,
                 mods=None, levels=None):
    """Build a Books Company Member row as frappe.db.get_value(..., as_dict=True)
    would return it, with all mod_/lvl_ fields defaulted."""
    row = {"books_role": books_role, "is_company_admin": is_company_admin,
           "levels_customized": levels_customized}
    for m in access.MODULES:
        row[f"mod_{m}"] = 0
        row[f"lvl_{m}"] = "None"
    for m, v in (mods or {}).items():
        row[f"mod_{m}"] = 1 if v else 0
    for m, v in (levels or {}).items():
        row[f"lvl_{m}"] = v
    return frappe._dict(row)


class TestModuleFor(unittest.TestCase):

    def test_mapped_doctype(self):
        self.assertEqual(access.module_for("Sales Invoice"), "invoices")
        self.assertEqual(access.module_for("Purchase Order"), "bills")
        self.assertEqual(access.module_for("Stock Entry"), "inventory")

    def test_unmapped_doctype_returns_none(self):
        self.assertIsNone(access.module_for("Some Random Doctype"))

    def test_assets_mapped_to_inventory_module(self):
        # Deliberate per the module docstring -- matches Phase 4 frontend gating.
        self.assertEqual(access.module_for("Asset"), "inventory")
        self.assertEqual(access.module_for("Asset Disposal"), "inventory")


class TestMembershipBypass(unittest.TestCase):

    @patch.object(frappe, "get_roles", return_value=["System Manager"])
    def test_system_manager_is_full_bypass(self, mock_roles):
        m = access._membership("admin@vkherbal.test")
        self.assertTrue(m["bypass"])
        self.assertTrue(m["admin"])
        self.assertFalse(m["readonly"])
        self.assertTrue(all(m["mods"].values()))
        self.assertTrue(all(lvl == "Delete" for lvl in m["levels"].values()))

    @patch.object(frappe, "get_roles", return_value=[])
    def test_administrator_user_is_bypass_without_role_check(self, mock_roles):
        m = access._membership("Administrator")
        self.assertTrue(m["bypass"])


class TestMembershipNoRow(unittest.TestCase):

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value", return_value=None)
    def test_no_membership_row_is_locked_out(self, mock_get_value, mock_roles):
        m = access._membership("stranger@example.com")
        self.assertTrue(m["no_member"])
        self.assertTrue(m["readonly"])
        self.assertFalse(m["admin"])
        self.assertTrue(all(v is False for v in m["mods"].values()))
        self.assertTrue(all(lvl == "None" for lvl in m["levels"].values()))


class TestMembershipCompanyAdmin(unittest.TestCase):

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value")
    def test_company_admin_gets_every_module_and_delete_level(self, mock_get_value, mock_roles):
        mock_get_value.return_value = _member_row(books_role="Books Admin", is_company_admin=1)
        m = access._membership("owner@vkherbal.test")
        self.assertTrue(m["admin"])
        self.assertTrue(all(m["mods"].values()))
        self.assertTrue(all(lvl == "Delete" for lvl in m["levels"].values()))


class TestMembershipLegacyAdditiveLevels(unittest.TestCase):
    """levels_customized=False: lvl_<module> only merges UP, never down."""

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value")
    def test_accountant_with_mod_on_gets_edit_regardless_of_stale_lvl_field(self, mock_get_value, mock_roles):
        mock_get_value.return_value = _member_row(
            books_role="Accountant", levels_customized=0,
            mods={"invoices": True}, levels={"invoices": "None"},  # stale/default noise
        )
        m = access._membership("acct@vkherbal.test")
        self.assertEqual(m["levels"]["invoices"], "Edit")  # legacy wins, "None" ignored

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value")
    def test_viewer_with_mod_on_gets_view_only(self, mock_get_value, mock_roles):
        mock_get_value.return_value = _member_row(
            books_role="Books Viewer", levels_customized=0, mods={"invoices": True},
        )
        m = access._membership("viewer@vkherbal.test")
        self.assertEqual(m["levels"]["invoices"], "View")

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value")
    def test_lvl_field_higher_than_legacy_still_wins_additively(self, mock_get_value, mock_roles):
        # Not customized, but if lvl_<module> somehow holds something ABOVE
        # the legacy-derived level, the additive (max) merge keeps it --
        # only a *downgrade* is blocked pre-customization.
        mock_get_value.return_value = _member_row(
            books_role="Accountant", levels_customized=0,
            mods={"invoices": True}, levels={"invoices": "Delete"},
        )
        m = access._membership("acct@vkherbal.test")
        self.assertEqual(m["levels"]["invoices"], "Delete")

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value")
    def test_mod_off_and_not_customized_gives_none(self, mock_get_value, mock_roles):
        mock_get_value.return_value = _member_row(
            books_role="Accountant", levels_customized=0, mods={"invoices": False},
        )
        m = access._membership("acct@vkherbal.test")
        self.assertEqual(m["levels"]["invoices"], "None")


class TestMembershipCustomizedLevels(unittest.TestCase):
    """levels_customized=True: lvl_<module> is authoritative, can restrict below the checkbox."""

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value")
    def test_explicit_none_overrides_mod_checkbox_being_on(self, mock_get_value, mock_roles):
        mock_get_value.return_value = _member_row(
            books_role="Accountant", levels_customized=1,
            mods={"invoices": True}, levels={"invoices": "None"},
        )
        m = access._membership("acct@vkherbal.test")
        self.assertEqual(m["levels"]["invoices"], "None")  # trusted as-is, not upgraded

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value")
    def test_explicit_create_only_is_trusted(self, mock_get_value, mock_roles):
        mock_get_value.return_value = _member_row(
            books_role="Accountant", levels_customized=1,
            mods={"invoices": True}, levels={"invoices": "Create"},
        )
        m = access._membership("acct@vkherbal.test")
        self.assertEqual(m["levels"]["invoices"], "Create")


class TestCanReadWriteCreateEditDelete(unittest.TestCase):

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value")
    def test_create_level_allows_create_but_not_edit(self, mock_get_value, mock_roles):
        mock_get_value.return_value = _member_row(
            books_role="Accountant", levels_customized=1, levels={"invoices": "Create"},
        )
        self.assertTrue(access.can_read("Sales Invoice", user="u@vkherbal.test"))
        self.assertTrue(access.can_create("Sales Invoice", user="u@vkherbal.test"))
        self.assertFalse(access.can_edit("Sales Invoice", user="u@vkherbal.test"))
        self.assertFalse(access.can_delete("Sales Invoice", user="u@vkherbal.test"))

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value")
    def test_can_write_true_for_admin(self, mock_get_value, mock_roles):
        mock_get_value.return_value = _member_row(books_role="Books Admin", is_company_admin=1)
        self.assertTrue(access.can_write("Sales Invoice", user="owner@vkherbal.test"))

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value")
    def test_can_write_false_for_readonly(self, mock_get_value, mock_roles):
        mock_get_value.return_value = _member_row(books_role="Books Viewer", mods={"invoices": True})
        self.assertFalse(access.can_write("Sales Invoice", user="viewer@vkherbal.test"))

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value")
    def test_can_write_unmapped_doctype_allowed_for_non_readonly_member(self, mock_get_value, mock_roles):
        mock_get_value.return_value = _member_row(books_role="Accountant")
        self.assertTrue(access.can_write("Some Random Doctype", user="acct@vkherbal.test"))

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value", return_value=None)
    def test_can_write_false_for_no_member(self, mock_get_value, mock_roles):
        self.assertFalse(access.can_write("Sales Invoice", user="stranger@example.com"))


class TestCanAtLevelUnmappedDoctype(unittest.TestCase):

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value", return_value=None)
    def test_view_always_allowed_even_for_no_member(self, mock_get_value, mock_roles):
        self.assertTrue(access._can_at_level("Unmapped Doctype", "View", "stranger@example.com"))

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value", return_value=None)
    def test_edit_denied_for_no_member_on_unmapped_doctype(self, mock_get_value, mock_roles):
        self.assertFalse(access._can_at_level("Unmapped Doctype", "Edit", "stranger@example.com"))

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value")
    def test_edit_allowed_for_ordinary_member_on_unmapped_doctype(self, mock_get_value, mock_roles):
        mock_get_value.return_value = _member_row(books_role="Accountant")
        self.assertTrue(access._can_at_level("Unmapped Doctype", "Edit", "acct@vkherbal.test"))

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value")
    def test_edit_denied_for_readonly_member_on_unmapped_doctype(self, mock_get_value, mock_roles):
        mock_get_value.return_value = _member_row(books_role="Books Viewer")
        self.assertFalse(access._can_at_level("Unmapped Doctype", "Edit", "viewer@vkherbal.test"))


class TestAssertCan(unittest.TestCase):

    def test_guest_always_denied(self):
        with self.assertRaises(frappe.PermissionError):
            access.assert_can("Sales Invoice", "read", user="Guest")

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value")
    def test_delete_action_requires_delete_tier_not_edit(self, mock_get_value, mock_roles):
        # Edit-level member can submit/cancel (routine workflow) but NOT the
        # generic delete_doc endpoint -- that's the one real behavior change
        # this phase introduces.
        mock_get_value.return_value = _member_row(
            books_role="Accountant", levels_customized=1, levels={"invoices": "Edit"},
        )
        access.assert_can("Sales Invoice", "cancel", user="acct@vkherbal.test")  # should not raise
        with self.assertRaises(frappe.PermissionError):
            access.assert_can("Sales Invoice", "delete", user="acct@vkherbal.test")

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value")
    def test_delete_action_passes_with_delete_tier(self, mock_get_value, mock_roles):
        mock_get_value.return_value = _member_row(
            books_role="Accountant", levels_customized=1, levels={"invoices": "Delete"},
        )
        access.assert_can("Sales Invoice", "delete", user="acct@vkherbal.test")  # should not raise

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value")
    def test_submit_and_cancel_both_gate_at_edit_not_delete(self, mock_get_value, mock_roles):
        mock_get_value.return_value = _member_row(
            books_role="Accountant", levels_customized=1, levels={"invoices": "Edit"},
        )
        access.assert_can("Sales Invoice", "submit", user="acct@vkherbal.test")
        access.assert_can("Sales Invoice", "cancel", user="acct@vkherbal.test")


class TestRequireModule(unittest.TestCase):

    def test_guest_denied(self):
        with self.assertRaises(frappe.PermissionError):
            access.require_module("invoices", user="Guest")

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value")
    def test_write_denied_for_readonly(self, mock_get_value, mock_roles):
        mock_get_value.return_value = _member_row(books_role="Books Viewer", mods={"invoices": True})
        with self.assertRaises(frappe.PermissionError):
            access.require_module("invoices", write=True, user="viewer@vkherbal.test")

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value")
    def test_read_allowed_for_readonly_with_view_level(self, mock_get_value, mock_roles):
        mock_get_value.return_value = _member_row(books_role="Books Viewer", mods={"invoices": True})
        access.require_module("invoices", write=False, user="viewer@vkherbal.test")  # should not raise

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value")
    def test_explicit_none_level_blocks_even_read(self, mock_get_value, mock_roles):
        mock_get_value.return_value = _member_row(
            books_role="Accountant", levels_customized=1, levels={"invoices": "None"},
        )
        with self.assertRaises(frappe.PermissionError):
            access.require_module("invoices", write=False, user="acct@vkherbal.test")


class TestRequireWrite(unittest.TestCase):

    def test_guest_denied(self):
        with self.assertRaises(frappe.PermissionError):
            access.require_write(user="Guest")

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value")
    def test_readonly_denied(self, mock_get_value, mock_roles):
        mock_get_value.return_value = _member_row(books_role="Books Viewer")
        with self.assertRaises(frappe.PermissionError):
            access.require_write(user="viewer@vkherbal.test")

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value")
    def test_ordinary_member_allowed(self, mock_get_value, mock_roles):
        mock_get_value.return_value = _member_row(books_role="Accountant")
        access.require_write(user="acct@vkherbal.test")  # should not raise


class TestIsReadonly(unittest.TestCase):

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value")
    def test_true_for_viewer(self, mock_get_value, mock_roles):
        mock_get_value.return_value = _member_row(books_role="Books Viewer")
        self.assertTrue(access.is_readonly(user="viewer@vkherbal.test"))

    @patch.object(frappe, "get_roles", return_value=[])
    @patch.object(frappe.db, "get_value")
    def test_false_for_admin_even_with_viewer_role_field(self, mock_get_value, mock_roles):
        # is_company_admin overrides books_role -- an admin flagged with a
        # stale "Books Viewer" role string is still full-access.
        mock_get_value.return_value = _member_row(books_role="Books Viewer", is_company_admin=1)
        self.assertFalse(access.is_readonly(user="owner@vkherbal.test"))


class TestAssertCompany(unittest.TestCase):

    @patch("zoho_books_clone.utils.access._is_bypass", return_value=True)
    def test_bypass_user_skips_check(self, mock_bypass):
        access.assert_company("Any Company", user="admin@vkherbal.test")  # should not raise

    @patch("zoho_books_clone.utils.access._is_bypass", return_value=False)
    @patch("zoho_books_clone.utils.access.get_user_company", return_value="VK Herbal")
    def test_matching_company_passes(self, mock_get_company, mock_bypass):
        access.assert_company("VK Herbal", user="u@vkherbal.test")  # should not raise

    @patch("zoho_books_clone.utils.access._is_bypass", return_value=False)
    @patch("zoho_books_clone.utils.access.get_user_company", return_value="VK Herbal")
    def test_mismatched_company_throws(self, mock_get_company, mock_bypass):
        with self.assertRaises(frappe.PermissionError):
            access.assert_company("Someone Else's Co", user="u@vkherbal.test")

    @patch("zoho_books_clone.utils.access._is_bypass", return_value=False)
    @patch("zoho_books_clone.utils.access.get_user_company", return_value=None)
    def test_user_with_no_company_throws(self, mock_get_company, mock_bypass):
        with self.assertRaises(frappe.PermissionError):
            access.assert_company("VK Herbal", user="orphan@example.com")


if __name__ == "__main__":
    unittest.main()