import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class StockLedgerEntry(Document):
    """
    Immutable audit-trail record for every stock movement.
    Never edited after creation — cancel by setting is_cancelled=1.
    """

    def before_save(self):
        if self.is_new():
            return
        # Prevent edits after creation (except is_cancelled flag)
        old = self.get_doc_before_save()
        if old and not old.is_cancelled:
            allowed = {"is_cancelled", "modified", "modified_by"}
            changed = {k for k, v in self.as_dict().items() if str(v) != str(old.as_dict().get(k))}
            if changed - allowed:
                frappe.throw(_("Stock Ledger Entries are immutable. Cancel via Stock Entry."))

    def after_insert(self):
        self._update_bin()

    def _update_bin(self):
        """
        Create or update the Bin for this item+warehouse combination.

        Audit-6: Uses SELECT ... FOR UPDATE row-level locking so that concurrent
        SLE inserts for the same item+warehouse don't race and produce an incorrect
        Bin balance.  The lock is held for the duration of the current DB transaction
        and released automatically on commit/rollback.
        """
        bin_name = frappe.db.get_value("Bin", {"item_code": self.item_code, "warehouse": self.warehouse})

        if bin_name:
            # Acquire an exclusive row lock before reading current qty.
            # This serialises concurrent updates to the same Bin row.
            frappe.db.sql(
                "SELECT name FROM `tabBin` WHERE name = %s FOR UPDATE",
                (bin_name,),
            )
            bin_doc = frappe.get_doc("Bin", bin_name)
        else:
            # INSERT path — race-safe because the unique constraint on
            # (item_code, warehouse) will cause a duplicate-key error if two
            # threads try to create the same Bin simultaneously; the second
            # thread retries via get_value below.
            try:
                bin_doc = frappe.get_doc({
                    "doctype": "Bin",
                    "item_code": self.item_code,
                    "warehouse": self.warehouse,
                    "company": self.company,
                    "actual_qty": 0,
                    "reserved_qty": 0,
                    "ordered_qty": 0,
                    "stock_value": 0,
                    "valuation_rate": 0,
                })
                bin_doc.flags.ignore_links = True
                bin_doc.flags.ignore_mandatory = True
                bin_doc.insert(ignore_permissions=True)
                # Lock the newly inserted row immediately
                frappe.db.sql(
                    "SELECT name FROM `tabBin` WHERE name = %s FOR UPDATE",
                    (bin_doc.name,),
                )
            except Exception:
                # Another thread created the Bin between our get_value check and
                # our INSERT — fetch it and lock it instead.
                bin_name = frappe.db.get_value(
                    "Bin", {"item_code": self.item_code, "warehouse": self.warehouse}
                )
                frappe.db.sql(
                    "SELECT name FROM `tabBin` WHERE name = %s FOR UPDATE",
                    (bin_name,),
                )
                bin_doc = frappe.get_doc("Bin", bin_name)

        # Apply the delta (now holding the exclusive lock).
        #
        # Moving-average valuation math lives in
        # zoho_books_clone.inventory.utils.compute_bin_valuation — a pure,
        # unit-tested function — so this method and
        # zoho_books_clone.inventory.utils.update_bin never have to be
        # eyeballed against each other for drift. See that function's
        # docstring for the incoming/outgoing/value-only branch rules.
        from zoho_books_clone.inventory.utils import compute_bin_valuation

        old_qty   = flt(bin_doc.actual_qty)
        old_value = flt(bin_doc.stock_value)
        delta_qty = flt(self.actual_qty)

        new_qty, new_value, new_rate = compute_bin_valuation(
            old_qty=old_qty,
            old_value=old_value,
            delta_qty=delta_qty,
            incoming_rate=self.incoming_rate,
            valuation_rate=self.valuation_rate,
            stock_value_difference=self.stock_value_difference,
        )

        bin_doc.actual_qty = new_qty
        bin_doc.valuation_rate = new_rate if new_qty > 0 else flt(bin_doc.valuation_rate)
        bin_doc.stock_value = new_value
        bin_doc.projected_qty = flt(new_qty) + flt(bin_doc.ordered_qty) - flt(bin_doc.reserved_qty)
        # Rack assignment is label-only and only makes sense while there's
        # actually stock sitting in the rack. Once qty drops to zero (or
        # below, e.g. a corrective negative entry), clear it automatically
        # rather than leaving a stale rack label on an empty Bin.
        if new_qty <= 0 and bin_doc.get("rack_no"):
            bin_doc.rack_no = ""
        bin_doc.flags.ignore_links = True
        bin_doc.flags.ignore_mandatory = True
        bin_doc.save(ignore_permissions=True)

        # Reorder check runs against the freshly-saved Bin. This is the only
        # place it's wired up: it used to live in Stock Entry's _sync_bin(),
        # but that method is dead code — nothing calls it, since _update_bin()
        # here is the single authoritative Bin writer (see the comments in
        # Stock Entry._create_sle / _reverse_sle). As a result reorder alerts
        # and auto-PO creation never actually fired in practice. Best-effort:
        # a failure here must not roll back the stock movement itself.
        try:
            from zoho_books_clone.inventory.utils import check_reorder
            check_reorder(self.item_code, self.warehouse)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Reorder check failed")