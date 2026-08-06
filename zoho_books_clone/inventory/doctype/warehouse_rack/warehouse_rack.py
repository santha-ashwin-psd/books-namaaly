from frappe.model.document import Document


class WarehouseRack(Document):
    """
    Child row on Warehouse — a label-only rack name/number.
    Uniqueness (within the parent Warehouse) and in-use-on-delete checks
    are enforced by the parent Warehouse.validate() / rack removal check,
    since child table rows don't get their own validate() call in list-save
    flows the way standalone docs do.
    """
    pass