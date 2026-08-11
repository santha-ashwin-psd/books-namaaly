# Copyright (c) 2026, PS Digitise and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from zoho_books_clone.assets.asset_quantity_adjustment_gl import (
	post_quantity_adjustment_gl,
	reverse_quantity_adjustment_gl,
	validate_quantity_adjustment_setup,
)


class AssetQuantityAdjustment(Document):

	def validate(self):
		if not self.company and self.asset:
			self.company = frappe.db.get_value("Asset", self.asset, "company")
		validate_quantity_adjustment_setup(self)

	def on_submit(self):
		post_quantity_adjustment_gl(self)

	def on_cancel(self):
		reverse_quantity_adjustment_gl(self)