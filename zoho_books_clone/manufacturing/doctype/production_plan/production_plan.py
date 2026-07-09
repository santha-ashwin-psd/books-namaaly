import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate


class ProductionPlan(Document):
	def validate(self):
		if not self.posting_date:
			self.posting_date = nowdate()

		if not self.po_items:
			frappe.throw(_(
				"Add at least one item to manufacture — pull demand from Sales Orders "
				"or add a row manually — before saving."
			))

		for row in self.po_items:
			if flt(row.planned_qty) <= 0:
				frappe.throw(_("Row for {0}: Planned Qty must be greater than zero.").format(row.item_code))

	def on_submit(self):
		self.db_set("status", "Submitted")

	def on_cancel(self):
		linked = frappe.get_all(
			"Work Order",
			filters={"production_plan": self.name, "docstatus": 1},
			limit=1,
		)
		if linked:
			frappe.throw(_(
				"Cannot cancel: submitted Work Orders already exist against this Production "
				"Plan ({0}). Cancel those first if this was created in error."
			).format(linked[0].name))
		self.db_set("status", "Cancelled")