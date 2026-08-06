import frappe
from frappe import _
from frappe.model.document import Document


class Warehouse(Document):
    def validate(self):
        if not self.warehouse_name:
            frappe.throw(_("Warehouse Name is required"))
        self.warehouse_name = self.warehouse_name.strip()
        self._validate_racks()

    def _validate_racks(self):
        """
        Rack numbers are label-only and only need to be unique *within* this
        warehouse (the same rack name/number is fine in a different warehouse,
        since each Warehouse Rack row belongs to its own parent).

        Also blocks removing/renaming a rack that's still referenced by a Bin
        in this warehouse, so Bin.rack_no never points at a rack that no
        longer exists in the warehouse's rack list.
        """
        seen = set()
        current_rack_nos = set()
        for row in self.get("racks") or []:
            rack_no = (row.rack_no or "").strip()
            if not rack_no:
                frappe.throw(_("Row #{0}: Rack No is required").format(row.idx))
            row.rack_no = rack_no
            key = rack_no.lower()
            if key in seen:
                frappe.throw(
                    _("Rack '{0}' is duplicated in this warehouse. Rack numbers must be unique within a warehouse.").format(rack_no)
                )
            seen.add(key)
            current_rack_nos.add(rack_no)

        if not self.is_new():
            in_use = frappe.get_all(
                "Bin",
                filters={"warehouse": self.name, "rack_no": ["not in", [""]]},
                fields=["rack_no"],
                pluck="rack_no",
            )
            removed = {r for r in in_use if r and r not in current_rack_nos}
            if removed:
                frappe.throw(
                    _("Cannot remove rack(s) {0} — they are still assigned to items in stock in this warehouse. Clear the rack assignment on those items first.").format(
                        ", ".join(sorted(removed))
                    )
                )

    def before_save(self):
        # Ensure a Bin record exists for any items already associated with this warehouse
        pass

    def on_trash(self):
        # Prevent deletion if stock exists
        if frappe.db.exists("Bin", {"warehouse": self.name, "actual_qty": [">", 0]}):
            frappe.throw(
                _("Cannot delete Warehouse '{0}' — it has stock. Clear all stock first.").format(self.name)
            )

    @frappe.whitelist()
    def get_stock_summary(self):
        """Return all Bins for this warehouse with current stock."""
        return frappe.get_all(
            "Bin",
            filters={"warehouse": self.name, "actual_qty": [">", 0]},
            fields=["item_code", "actual_qty", "valuation_rate", "stock_value"],
            order_by="item_code asc",
        )