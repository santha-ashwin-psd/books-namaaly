# Copyright (c) 2026, PS Digitise and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from zoho_books_clone.utils.tenancy import get_user_company, _is_bypass, _default_books_company


class AssetCategory(Document):

	def validate(self):
		# Company isolation: every category must belong to a Books Company so
		# it stays scoped to that tenant (mirrors Customer/Supplier/Item/Contact
		# and Expense Category). before_insert already stamps this for new
		# records; this is a safety net for API/import paths that bypass it,
		# and re-validates on every save.
		if not self.books_company:
			company = get_user_company(frappe.session.user) or _default_books_company()
			if company:
				self.books_company = company
			elif not _is_bypass(frappe.session.user):
				frappe.throw(_("Your user is not linked to any Books Company. Contact your administrator."))

		if self.books_company:
			duplicate = frappe.db.exists("Asset Category", {
				"category_name": self.category_name,
				"books_company": self.books_company,
				"name": ["!=", self.name],
			})
			if duplicate:
				frappe.throw(_("Asset Category {0} already exists for {1}").format(
					frappe.bold(self.category_name), frappe.bold(self.books_company)))