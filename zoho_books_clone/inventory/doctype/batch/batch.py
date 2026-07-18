import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import add_days, getdate, nowdate


class Batch(Document):
	def autoname(self):
		"""Batch No format: {ITEM-CODE}-{YYYY}-{####}, e.g. ASHW-2026-0001.
		Sequence resets per item+year (own counter key), matching how a plant
		would restart batch numbering each year for each product.
		If the user has already typed a Batch No (manual override, used by the
		"type to create new batch" flows on transaction pages), that is honored
		as-is and nothing is auto-generated."""
		if self.batch_no and self.batch_no.strip():
			self.name = self.batch_no.strip()
			return

		item_code = self.item or "BATCH"
		year = getdate(self.manufacturing_date or nowdate()).year
		key = f"{item_code}-{year}-.####"
		self.name = self.batch_no = make_autoname(key, doctype="Batch", doc=self)

	def validate(self):
		self.set_expiry_date_from_shelf_life()
		self._apply_source_batch_lineage()

	def set_expiry_date_from_shelf_life(self):
		"""Auto-calculate expiry_date from manufacturing_date + Item.shelf_life_in_days
		when expiry_date is left blank. Never overrides a manually entered expiry_date."""
		if self.expiry_date or not self.manufacturing_date or not self.item:
			return

		shelf_life_in_days = frappe.db.get_value("Item", self.item, "shelf_life_in_days")
		if shelf_life_in_days:
			self.expiry_date = add_days(getdate(self.manufacturing_date), shelf_life_in_days)

	def _apply_source_batch_lineage(self):
		"""Phase 4 (bulk -> packed batch/expiry lineage): when source_batch_no
		is set (e.g. a Packing Slip's finished-good batch, filled from a bulk
		Work Order's batch), this batch's shelf life is bounded by that source
		batch -- packaging never extends the life of what's inside it:

		  1. Block manufacturing/packing a new batch from a source batch that
		     has already expired.
		  2. Cap this batch's expiry_date to the source batch's expiry_date if
		     it would otherwise be later (whether that later date came from an
		     explicit entry above or from set_expiry_date_from_shelf_life()'s
		     own Item-shelf-life calculation) -- the tighter of the two always
		     wins.

		source_batch_no is only meaningful at creation (no_copy, and callers
		treat it as immutable), so this only ever tightens expiry_date, never
		loosens it.
		"""
		if not self.source_batch_no:
			return

		source = frappe.db.get_value(
			"Batch", self.source_batch_no, ["expiry_date", "batch_no"], as_dict=True
		)
		if not source:
			return

		if not source.expiry_date:
			return

		mfg_date = getdate(self.manufacturing_date or nowdate())
		if mfg_date > getdate(source.expiry_date):
			frappe.throw(_(
				"Source Batch {0} expired on {1}, before this batch's "
				"Manufacturing Date ({2}). Cannot produce or pack from an "
				"already-expired batch."
			).format(self.source_batch_no, source.expiry_date, mfg_date))

		if not self.expiry_date or getdate(self.expiry_date) > getdate(source.expiry_date):
			self.expiry_date = source.expiry_date