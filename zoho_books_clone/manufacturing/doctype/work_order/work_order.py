import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class WorkOrder(Document):
	def before_insert(self):
		"""When this doc is a fresh amendment (created via api.docs.amend_doc,
		which inserts with docstatus=0 but otherwise carries every field over
		verbatim from the cancelled original via frappe.copy_doc), reset every
		field that describes PROGRESS rather than PLAN back to a clean start.

		Several of these fields are already flagged no_copy=1 in the doctype
		JSON precisely because they shouldn't survive a copy -- but amend_doc
		is generic and doesn't special-case no_copy, so status/produced_qty/
		process_loss_qty/operating cost all came through unchanged. Without
		this, a brand-new revision that has had zero materials issued/
		consumed and zero production recorded against it showed status
		"Cancelled" (from the doc it was amended from) and its raw-material/
		operation rows still showed transferred/consumed qty and Completed
		operations left over from a Work Order that, under this name, never
		actually ran.
		"""
		if not self.amended_from:
			return
		self.status = "Draft"
		self.produced_qty = 0
		self.process_loss_qty = 0
		self.actual_operating_cost = 0
		self.total_operating_cost = 0
		for row in (self.items or []):
			row.transferred_qty = 0
			row.consumed_qty = 0
		for row in (self.operations or []):
			row.status = "Pending"
			row.actual_time_in_mins = 0

	def validate(self):
		if self.bom:
			bom_type = frappe.db.get_value("BOM", self.bom, "bom_type")
			if bom_type == "Sub-Assembly":
				frappe.throw(_(
					"{0} is a Sub-Assembly BOM and can't be used directly on a Work Order. "
					"Sub-Assembly BOMs are meant to be consumed inside a Manufacturing or "
					"Packing BOM -- their materials and operations are pulled in "
					"automatically wherever that BOM references them."
				).format(self.bom))

		if flt(self.qty) <= 0:
			frappe.throw(_("Qty to Manufacture must be greater than zero."))

		if not self.fg_warehouse:
			frappe.throw(_("Finished Goods Warehouse is required."))

		# A Source Warehouse to consume raw materials from is required at
		# Complete Work Order time -- either the Work Order's own Default
		# Source Warehouse, or a Source Warehouse on every individual raw
		# material row. Enforcing this here (rather than only at Complete
		# time) stops a Work Order from being saved/submitted in a state
		# that's guaranteed to fail production later with no way to add a
		# warehouse from the Complete Work Order screen.
		if not self.source_warehouse:
			missing_rows = [
				row.item_code for row in (self.items or []) if not row.source_warehouse
			]
			if missing_rows or not self.items:
				frappe.throw(_(
					"Default Source Warehouse is required, or a Source Warehouse must "
					"be set on every raw material row. Missing for: {0}"
				).format(", ".join(missing_rows) or _("all rows")))


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

		self._check_materials_current()
		self.calculate_operating_cost()

	def _check_materials_current(self):
		"""Guard against the Raw Material/Operations tables being stale for the
		current Qty to Manufacture -- e.g. materials were loaded from the BOM
		at qty 5, then Qty was edited to 10 in the form without clicking
		"Load / Refresh Materials from BOM" (or an API caller passed items
		once and later PATCHed qty without recomputing them).

		complete_work_order()'s raw-material consumption and operating-cost
		absorption are both proportional to `self.qty` (see
		manufacturing.work_order_engine.complete_work_order:
		consumption_ratio = (qty_manufactured + process_loss_qty) / self.qty).
		If the Raw Material rows' required_qty is still sized for a different
		qty than self.qty, that proportion is silently wrong -- a full
		completion consumes and costs the WRONG total of raw material against
		the ACTUAL qty produced, with no error anywhere to surface it. This
		check turns that into a loud, immediate one instead.

		items_loaded_for_qty is a snapshot written whenever materials are
		(re)loaded from the BOM -- either by the client calling
		get_bom_breakdown (see WorkOrder.vue::loadFromBom) or by
		set_items_and_operations_from_bom() above. It is intentionally NOT
		compared against the BOM itself row-by-row: legitimate manual edits
		(added/removed rows, hand-adjusted quantities, or a Material
		Substitution swapping an item_code) are a supported workflow and must
		not trip this check as long as they were made without changing qty
		afterward. A value of 0 means the Work Order predates this field (or
		was created before it was ever set) -- treated as "unknown basis" and
		skipped rather than blocking existing/legacy documents.
		"""
		if not self.items_loaded_for_qty:
			return
		tolerance = max(flt(self.qty) * 0.001, 0.0001)
		if abs(flt(self.qty) - flt(self.items_loaded_for_qty)) > tolerance:
			frappe.throw(_(
				"Raw Materials/Operations were loaded from BOM {0} for Qty to "
				"Manufacture {1}, but Qty to Manufacture is now {2}. Click "
				"'Load / Refresh Materials from BOM' to rescale them, or "
				"restore the original Qty. Saving with mismatched Qty would "
				"consume and cost raw materials for the wrong quantity when "
				"this Work Order is completed."
			).format(self.bom, self.items_loaded_for_qty, self.qty))

	def calculate_operating_cost(self):
		"""Recompute Planned/Actual/Total Operating Cost from the Operations
		child table.

		- planned_operating_cost = Σ (planned_time_in_mins / 60 * hour_rate)
		- actual_operating_cost  = Σ (actual_time_in_mins / 60 * hour_rate)
		- total_operating_cost   = Σ, PER ROW, of (actual cost if that row has
		  logged actual time, else its planned cost) + additional_operating_cost

		total_operating_cost is evaluated per row rather than as a single
		all-or-nothing switch across the whole table. A multi-operation
		routing (e.g. Mixing -> Filling -> Packaging) starts logging actual
		time on its first operation well before the later ones begin --
		switching the WHOLE total to "actual mode" the moment any one row
		gets a Job Card would make every not-yet-started row contribute ₹0
		instead of its planned cost, understating the true cost-to-date
		(and, via complete_work_order's operating_cost_this_run snapshot,
		understating FG valuation for any partial completion recorded while
		some operations are still pending).

		This is the single source of truth referenced from validate() (every
		normal save), from work_order_engine.recalculate_operating_cost()
		(the "Recalculate" button, used when hour rates were stale/zero at
		BOM-load time), and from Job Card's _sync_wo_operating_cost() (roll-up
		after time-log changes written via db_set outside validate()).
		"""
		planned = 0.0
		actual = 0.0
		total = 0.0

		for row in (self.operations or []):
			hour_rate = flt(row.hour_rate)
			row_planned_cost = flt(row.planned_time_in_mins) / 60.0 * hour_rate
			row_actual_time = flt(row.actual_time_in_mins)
			row_actual_cost = row_actual_time / 60.0 * hour_rate

			planned += row_planned_cost
			actual += row_actual_cost
			total += row_actual_cost if row_actual_time else row_planned_cost

		self.planned_operating_cost = planned
		self.actual_operating_cost = actual
		self.total_operating_cost = total + flt(self.additional_operating_cost)

	def set_items_and_operations_from_bom(self):
		"""Safety net used only when a Work Order reaches validate() with a BOM
		set but no Raw Material rows (e.g. created via the generic API without
		the client calling get_bom_breakdown first). Delegates to
		manufacturing.work_order_engine.get_bom_breakdown so Manufacturing
		and Packing BOMs -- including sub-assembly/phantom explosion and
		duplicate-row merging -- are all handled the same way here as in
		the normal client-driven flow. (Sub-Assembly BOMs are rejected
		earlier in validate() and never reach this point.) A Packing BOM
		has no rows in its own `items` table by design (its materials live
		in `packing_items` + the bulk item), so reading bom.items directly
		here would always come back empty and fail the "must have at least
		one Raw Material row" check below.
		"""
		from zoho_books_clone.manufacturing.work_order_engine import get_bom_breakdown

		bom = frappe.get_doc("BOM", self.bom)
		if bom.docstatus != 1:
			frappe.throw(_("Only a submitted BOM can be used on a Work Order."))

		breakdown = get_bom_breakdown(self.bom, self.qty)

		# Snapshot the BOM's expected process-loss % onto the Work Order, same
		# as WorkOrder.vue does client-side (wo.value.process_loss_percent =
		# flt(r.process_loss)) on the normal load-from-BOM flow. Without this,
		# a Work Order created via this API safety net keeps
		# process_loss_percent at its default of 0, so complete_work_order()'s
		# expected_loss_qty_this_run works out to 0 and ALL process loss on
		# that Work Order gets treated as abnormal (expensed to
		# manufacturing_variance_loss) instead of the normal-shrinkage share
		# being capitalized into FG cost as the BOM intends.
		self.process_loss_percent = flt(breakdown.get("process_loss"))

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

		self.items_loaded_for_qty = flt(self.qty)

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
				"for_quantity":      flt(op_row.sub_assembly_qty, 4) if op_row.sub_assembly_item else flt(self.qty),
				"status":            "Open",
				"wo_operation_name": op_row.name,
				"sub_assembly_bom":  op_row.sub_assembly_bom or "",
				"sub_assembly_item": op_row.sub_assembly_item or "",
			})
			jc.insert(ignore_permissions=True)

	def on_cancel(self):
		if flt(self.produced_qty) > 0:
			frappe.throw(_(
				"Cannot cancel a Work Order that already has finished-goods "
				"production recorded against it. Cancel/reverse the Manufacture "
				"Stock Entries first if this was posted in error."
			))
		# A Work Order can have had issue_materials() run -- a submitted
		# Material Transfer moving stock into the WIP warehouse -- with zero
		# production recorded yet. The produced_qty check above doesn't catch
		# that case, so without this a cancel would leave that Stock Entry
		# submitted and its stock stranded in WIP with no Work Order left to
		# consume it.
		linked_stock_entries = frappe.get_all(
			"Stock Entry", filters={"work_order": self.name, "docstatus": 1}, limit=1
		)
		if linked_stock_entries:
			frappe.throw(_(
				"Cannot cancel: Stock Entry {0} is still submitted against this Work "
				"Order (materials were issued and/or production was recorded). "
				"Cancel that Stock Entry first if this was posted in error."
			).format(linked_stock_entries[0].name))

		self.db_set("status", "Cancelled")
		# Job Cards aren't submittable documents, so they don't block cancel
		# the way a submitted Stock Entry does -- but leaving them Open/Work
		# In Progress after their parent Work Order is cancelled would orphan
		# them pointing at a dead parent. Completed Job Cards are left alone
		# as a historical record.
		frappe.db.sql(
			"""UPDATE `tabJob Card` SET status = 'Cancelled'
			   WHERE work_order = %s AND status NOT IN ('Completed', 'Cancelled')""",
			(self.name,),
		)

	def on_trash(self):
		"""Job Cards have no independent existence once their Work Order is
		gone -- they only ever record progress against this WO's own
		operations -- so deleting the Work Order deletes its Job Cards too,
		rather than leaving them behind pointing at a name that no longer
		exists. Frappe only reaches on_trash for a Draft (docstatus=0) or
		already-Cancelled (docstatus=2) Work Order (submitted docs must be
		cancelled first), so there's no risk of this firing on an in-progress
		WO with real production recorded against its cards.
		"""
		job_cards = frappe.get_all("Job Card", filters={"work_order": self.name}, pluck="name")
		for jc in job_cards:
			frappe.delete_doc("Job Card", jc, ignore_permissions=True, force=True)