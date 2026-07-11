import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class WorkOrder(Document):
	def validate(self):
		if flt(self.qty) <= 0:
			frappe.throw(_("Qty to Manufacture must be greater than zero."))

		if not self.fg_warehouse:
			frappe.throw(_("Finished Goods Warehouse is required."))

		# Safety net: if the Raw Materials table is still empty (e.g. the doc
		# was created via API without calling get_bom_breakdown first), pull
		# it from the BOM now rather than letting an empty Work Order through.
		# The normal path is the Work Order form calling
		# manufacturing.work_order_engine.get_bom_breakdown to populate/refresh
		# these tables client-side so the person can review/edit before saving.
		if self.bom and not self.items:
			self.set_items_and_operations_from_bom()

		if not self.items:
			frappe.throw(_("Work Order must have at least one Raw Material row."))

		if flt(self.produced_qty) > flt(self.qty):
			frappe.throw(_("Produced Qty cannot exceed Qty to Manufacture."))

	def set_items_and_operations_from_bom(self):
		"""Safety net used only when a Work Order reaches validate() with a BOM
		set but no Raw Material rows (e.g. created via the generic API without
		the client calling get_bom_breakdown first). Delegates to
		manufacturing.work_order_engine.get_bom_breakdown so Manufacturing,
		Sub-Assembly, and Packing BOMs — including sub-assembly/phantom
		explosion and duplicate-row merging — are all handled the same way
		here as in the normal client-driven flow. A Packing BOM has no rows
		in its own `items` table by design (its materials live in
		`packing_items` + the bulk item), so reading bom.items directly here
		would always come back empty and fail the "must have at least one Raw
		Material row" check below.
		"""
		from zoho_books_clone.manufacturing.work_order_engine import get_bom_breakdown

		bom = frappe.get_doc("BOM", self.bom)
		if bom.docstatus != 1:
			frappe.throw(_("Only a submitted BOM can be used on a Work Order."))

		breakdown = get_bom_breakdown(self.bom, self.qty)

		self.set("items", [])
		for row in breakdown["items"]:
			self.append("items", {
				"item_code": row["item_code"],
				"item_name": row["item_name"],
				"required_qty": row["required_qty"],
				"uom": row["uom"],
				"rate": row["rate"],
				"amount": row["amount"],
				"source_warehouse": row.get("source_warehouse") or self.source_warehouse,
			})

		self.set("operations", [])
		for row in breakdown["operations"]:
			self.append("operations", {
				"operation": row["operation"],
				"workstation": row["workstation"],
				"planned_time_in_mins": row["planned_time_in_mins"],
				"hour_rate": row["hour_rate"],
				"cost": row["cost"],
			})

	def on_submit(self):
		self.db_set("status", "Submitted")
		self._create_job_cards()

	def _get_mfg_settings(self):
		try:
			return frappe.get_single("Manufacturing Settings")
		except Exception:
			return frappe._dict({"auto_create_job_cards": 1})

	def _create_job_cards(self):
		"""Auto-create Job Cards for every operation on the Work Order when the
		Manufacturing Settings 'Auto-Create Job Cards' option is enabled."""
		ms = self._get_mfg_settings()
		if not ms.get("auto_create_job_cards", 1):
			return

		for op_row in (self.operations or []):
			if not op_row.operation:
				continue
			jc = frappe.get_doc({
				"doctype":           "Job Card",
				"work_order":        self.name,
				"operation":         op_row.operation,
				"workstation":       op_row.workstation or "",
				"for_quantity":      flt(self.qty),
				"status":            "Open",
				"wo_operation_name": op_row.name,
			})
			jc.insert(ignore_permissions=True)

	def on_cancel(self):
		if flt(self.produced_qty) > 0:
			frappe.throw(_(
				"Cannot cancel a Work Order that already has finished-goods "
				"production recorded against it. Cancel/reverse the Manufacture "
				"Stock Entries first if this was posted in error."
			))
		self.db_set("status", "Cancelled")