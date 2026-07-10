import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class BOM(Document):
    def validate(self):
        self.bom_type = self.bom_type or "Manufacturing"

        if self.bom_type == "Packing":
            self.validate_packing_bom()
        elif self.bom_type == "Sub-Assembly":
            self.validate_sub_assembly_bom()
        else:
            self.validate_manufacturing_bom()

        self._calc_costs()

        # Carry the version number forward on amendment so it reads 2, 3, 4...
        # instead of resetting to 1 (amended_from is only set on the copy Frappe
        # creates when you amend a cancelled BOM).
        if self.amended_from and not self.is_new():
            pass  # version already set by set_version_on_amend at insert time

    def validate_manufacturing_bom(self):
        if not self.items or len(self.items) == 0:
            frappe.throw(_("BOM must have at least one Raw Material row before it can be saved."))

    def validate_sub_assembly_bom(self):
        """Sub-Assembly BOMs follow the same rules as Manufacturing BOMs — they
        just produce an intermediate item consumed by a parent BOM."""
        if not self.items or len(self.items) == 0:
            frappe.throw(_("Sub-Assembly BOM must have at least one Raw Material row."))
        # Guard against self-referencing sub-assembly rows
        for row in self.items:
            if row.sub_assembly_bom == self.name:
                frappe.throw(_("Row for {0}: Sub-Assembly BOM cannot reference itself.").format(row.item_code))

    def validate_packing_bom(self):
        if not self.bulk_item:
            frappe.throw(_("Packing BOM requires a Bulk Item to consume from."))
        if not self.bulk_qty_per_unit or self.bulk_qty_per_unit <= 0:
            frappe.throw(_("Packing BOM requires a positive Bulk Qty Consumed per Packed Unit."))
        if self.bulk_item == self.item:
            frappe.throw(_("Bulk Item cannot be the same as the Production Item being packed."))
        if not self.packing_items or len(self.packing_items) == 0:
            frappe.throw(_("Packing BOM must have at least one Packing Material row before it can be saved."))
        # Packing BOMs don't consume raw materials or run operations directly —
        # those belong to the Manufacturing BOM that produced the bulk item.
        if self.items:
            frappe.throw(_("Packing BOM should not have Raw Materials rows. Use the Packing Materials table instead."))
        if self.operations:
            frappe.throw(_("Packing BOM should not have Operations. Operations belong to the Manufacturing BOM."))

    def _calc_costs(self):
        """Recompute all cost roll-up fields from child rows.
        Called on every save so the stored values are always in sync with the
        actual rows — no stale figures even if rows were edited via API."""

        # Raw material / packing material cost
        source_items = self.packing_items if self.bom_type == "Packing" else (self.items or [])
        rm = 0.0
        for r in source_items:
            r.amount = flt(r.qty) * flt(r.rate)
            rm += r.amount

        # Operation cost  (time_in_mins / 60 * hour_rate)
        op = 0.0
        for r in (self.operations or []):
            r.cost = flt(r.time_in_mins) / 60.0 * flt(r.hour_rate)
            op += r.cost

        # Scrap / by-product value
        scrap = 0.0
        for r in (self.scrap_items or []):
            r.amount = flt(r.qty) * flt(r.rate)
            scrap += r.amount

        self.rm_cost = rm
        self.op_cost = op
        self.scrap_value = scrap
        self.total_cost = rm + op - scrap

    def before_insert(self):
        # Stamp the user's company for multi-tenant isolation if not yet set.
        if not self.company:
            from zoho_books_clone.utils.tenancy import get_user_company, _is_bypass
            company = get_user_company(frappe.session.user)
            if not company and _is_bypass(frappe.session.user):
                company = (
                    frappe.db.get_single_value("Books Settings", "default_company")
                    or frappe.db.get_value("Company", {}, "name")
                )
            if company:
                self.company = company

        if self.amended_from:
            prev_version = frappe.db.get_value("BOM", self.amended_from, "bom_version") or 1
            self.bom_version = int(prev_version) + 1
            # A new revision starts as the active one; the row it amends should
            # not keep competing as "default" once superseded.
            self.is_active = 1

    def on_submit(self):
        # Only one submitted, active BOM should be flagged default per item —
        # supersede any earlier default BOM for the same production item.
        if self.is_default:
            frappe.db.sql(
                """UPDATE `tabBOM` SET is_default = 0
                   WHERE item = %s AND bom_type = %s AND name != %s AND docstatus = 1""",
                (self.item, self.bom_type, self.name),
            )
        # The BOM this one amends is no longer the active revision.
        if self.amended_from:
            frappe.db.set_value("BOM", self.amended_from, "is_active", 0)

    def on_cancel(self):
        self.is_active = 0
        self.db_set("is_active", 0)