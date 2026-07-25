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

		# BOM is only truly required once the plan is being submitted --
		# rows can sit without one on a Draft while still being worked out.
		# Checking it here, upfront, means it fails at Submit with the full
		# list of offending rows instead of surfacing one row at a time,
		# later, as a hard throw the first time "Create Work Orders" is
		# clicked -- by which point any earlier rows in the loop have
		# already had live Work Orders created for them.
		if self.docstatus == 1:
			missing = [row.item_code for row in self.po_items if not row.bom_no]
			if missing:
				frappe.throw(_(
					"Cannot submit: the following row(s) have no BOM selected — {0}."
				).format(", ".join(missing)))

	def on_submit(self):
		self.db_set("status", "Submitted")

	def on_cancel(self):
		# Only submitted Work Orders were checked before -- Draft ones (which
		# create_work_orders() deliberately leaves in Draft for review) slipped
		# through and were left pointing at a now-cancelled Production Plan.
		linked = frappe.get_all(
			"Work Order",
			filters={"production_plan": self.name, "docstatus": ["in", [0, 1]]},
			fields=["name", "docstatus"],
			limit=1,
			order_by="docstatus desc",
		)
		if linked:
			if linked[0].docstatus == 1:
				frappe.throw(_(
					"Cannot cancel: submitted Work Orders already exist against this Production "
					"Plan ({0}). Cancel those first if this was created in error."
				).format(linked[0].name))
			frappe.throw(_(
				"Cannot cancel: Draft Work Order {0} still exists against this Production "
				"Plan. Delete or submit it first."
			).format(linked[0].name))
		self.db_set("status", "Cancelled")