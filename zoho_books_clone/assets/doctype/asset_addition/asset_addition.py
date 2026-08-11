# Copyright (c) 2026, PS Digitise and contributors
# For license information, please see license.txt

from frappe.model.document import Document

import frappe

from zoho_books_clone.assets.asset_addition_gl import (
	calculate_addition_totals,
	post_addition_gl,
	reverse_addition_gl,
	validate_addition_setup,
)


class AssetAddition(Document):

	def validate(self):
		if not self.company and self.original_asset:
			self.company = frappe.db.get_value("Asset", self.original_asset, "company")
		calculate_addition_totals(self)
		validate_addition_setup(self)

	def on_submit(self):
		post_addition_gl(self)

	def on_cancel(self):
		reverse_addition_gl(self)