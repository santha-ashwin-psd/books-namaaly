import frappe
from frappe.model.document import Document


class QCInspectionTemplate(Document):
    def validate(self):
        self._validate_parameters()

    def _validate_parameters(self):
        for row in (self.parameters or []):
            if row.parameter_type == "Numeric":
                if row.min_value is not None and row.max_value is not None:
                    if float(row.min_value or 0) > float(row.max_value or 0):
                        frappe.throw(
                            f"Parameter '{row.parameter}': Min value cannot be greater than Max value."
                        )
            elif row.parameter_type == "Non-Numeric":
                if not (row.acceptance_criteria_value or "").strip():
                    frappe.throw(
                        f"Parameter '{row.parameter}': Acceptance Criteria Value is required for Non-Numeric parameters."
                    )
