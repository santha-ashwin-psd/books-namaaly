# Copyright (c) 2026, PS Digitise and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ExpenseCategory(Document):

	def validate(self):
		if not self.company:
			frappe.throw(_("Company is required for Expense Category"))
		duplicate = frappe.db.exists("Expense Category", {
			"category_name": self.category_name,
			"company": self.company,
			"name": ["!=", self.name],
		})
		if duplicate:
			frappe.throw(_("Expense Category {0} already exists for {1}").format(
				frappe.bold(self.category_name), frappe.bold(self.company)))