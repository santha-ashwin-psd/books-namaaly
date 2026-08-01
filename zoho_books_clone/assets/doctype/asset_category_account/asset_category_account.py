# Copyright (c) 2026, PS Digitise and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class AssetCategoryAccount(Document):

	def validate(self):
		# Guard against wiring one company's fixed-asset/depreciation/CWIP
		# accounts onto another company's category row (parent is a shared
		# master; only this child row is company-scoped).
		if not self.company:
			return

		account_fields = (
			"fixed_asset_account",
			"accumulated_depreciation_account",
			"depreciation_expense_account",
			"cwip_account",
		)
		for fieldname in account_fields:
			account = self.get(fieldname)
			if not account:
				continue
			account_company = frappe.db.get_value("Account", account, "company")
			if account_company and account_company != self.company:
				frappe.throw(_(
					"Row #{0}: {1} ({2}) belongs to company {3}, not {4}."
				).format(
					self.idx,
					frappe.get_meta(self.doctype).get_label(fieldname),
					frappe.bold(account),
					frappe.bold(account_company),
					frappe.bold(self.company),
				))