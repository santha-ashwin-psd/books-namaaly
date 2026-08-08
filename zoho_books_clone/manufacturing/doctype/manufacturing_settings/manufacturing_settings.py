import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class ManufacturingSettings(Document):
    def validate(self):
        if flt(self.over_production_allowance_pct) < 0:
            frappe.throw(_("Over-Production Allowance cannot be negative."))
        if flt(self.over_production_allowance_pct) > 100:
            frappe.throw(_("Over-Production Allowance cannot exceed 100%."))
        if flt(self.job_card_hours_per_day) <= 0:
            frappe.throw(_("Job Card Hours per Day must be greater than zero."))
        if (self.capacity_planning_for_days or 0) < 0:
            frappe.throw(_("Capacity Planning Horizon cannot be negative."))


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_manufacturing_defaults():
    """Return the current Manufacturing Settings as a plain dict. Safe to call
    before the DocType is migrated — returns hardcoded defaults in that case."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    defaults = {
        "default_source_warehouse": "",
        "default_wip_warehouse": "",
        "default_fg_warehouse": "",
        "default_scrap_warehouse": "",
        "auto_create_job_cards": 1,
        "over_production_allowance_pct": 0,
        "default_close_on_loss_reconciliation": 0,
        "allow_negative_stock": 0,
        "backflush_raw_materials_based_on": "BOM",
        "default_bom_type": "Manufacturing",
        "set_rate_of_sub_assembly_item_based_on_bom": 0,
        "job_card_hours_per_day": 8,
        "capacity_planning_for_days": 30,
        "warn_if_bom_not_default": 1,
        "warn_on_missing_job_cards": 1,
        "enable_scrap_reuse": 1,
    }

    try:
        ms = frappe.get_single("Manufacturing Settings")
        for key in defaults:
            val = ms.get(key)
            if val is not None:
                defaults[key] = val
    except Exception:
        pass

    return defaults