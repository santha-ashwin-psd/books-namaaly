import frappe
from frappe import _
from frappe.model.document import Document


class Routing(Document):
    def validate(self):
        if not self.operations:
            frappe.throw(_("Routing must have at least one Operation row."))
        self._auto_set_sequence()

    def _auto_set_sequence(self):
        for idx, row in enumerate(self.operations, start=1):
            row.sequence_id = idx


@frappe.whitelist()
def get_routing_operations(routing):
    """Return the operations of a Routing as a list suitable for populating
    BOM Operation child rows. Called from BOMView.vue on routing change."""
    doc = frappe.get_doc("Routing", routing)
    rows = []
    for op in doc.operations:
        rows.append({
            "operation": op.operation,
            "workstation": op.workstation or "",
            "time_in_mins": op.time_in_mins or 0,
            "hour_rate": op.hour_rate or 0,
            "cost": 0,
        })
    return rows
