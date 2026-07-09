import frappe
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

	def set_expiry_date_from_shelf_life(self):
		"""Auto-calculate expiry_date from manufacturing_date + Item.shelf_life_in_days
		when expiry_date is left blank. Never overrides a manually entered expiry_date."""
		if self.expiry_date or not self.manufacturing_date or not self.item:
			return

		shelf_life_in_days = frappe.db.get_value("Item", self.item, "shelf_life_in_days")
		if shelf_life_in_days:
			self.expiry_date = add_days(getdate(self.manufacturing_date), shelf_life_in_days)