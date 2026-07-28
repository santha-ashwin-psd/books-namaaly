from __future__ import annotations
"""
Asset Movement — Phase 4, part 1 of the asset-management build-out.

Pure logistics doctype: records where an asset has been and where it's
going (location / department / custodian), independent of the GL. No
accounting entries are posted here -- that's Asset Repair (part 2) and
Disposal (Phase 5).

On submit, the asset's current `location` / `department` snapshot fields
are updated to the Movement's target values, so Asset.location always
reflects the most recent submitted movement without anyone having to
edit the Asset directly. On cancel, they're reverted to the Movement's
own source snapshot -- not re-derived from other movements -- mirroring
the same "reverse, don't recompute from scratch" posture asset_gl.py and
depreciation_posting.py already use for their own state flips.

History for a given asset is just the list of submitted Asset Movement
documents against it (filter by `asset`) -- no separate log/child table
duplicating that.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class AssetMovement(Document):

    def validate(self):
        self._fetch_asset_snapshot()
        self._validate_purpose_requirements()

    def on_submit(self):
        self._apply_to_asset()

    def on_cancel(self):
        self._revert_asset()

    # ── internals ───────────────────────────────────────────────────────

    def _fetch_asset_snapshot(self) -> None:
        """Stamp company from the Asset, and default the source_* fields
        from the Asset's current location/department when left blank --
        so the person only has to fill in where the asset is *going*."""
        if not self.asset:
            return

        asset = frappe.db.get_value(
            "Asset",
            self.asset,
            ["company", "location", "department"],
            as_dict=True,
        )
        if not asset:
            frappe.throw(_("Asset {0} not found.").format(self.asset))

        # The Asset's own company is authoritative here (not the session
        # user's default company via auto_stamp_company) -- a movement must
        # stay scoped to whichever company actually owns the asset.
        self.company = asset.company

        if not self.source_location:
            self.source_location = asset.location
        if not self.source_department:
            self.source_department = asset.department

    def _validate_purpose_requirements(self) -> None:
        if self.purpose == "Transfer":
            if not (self.target_location or self.target_department or self.target_custodian):
                frappe.throw(
                    _("Transfer requires at least one of Target Location, Target Department or Target Custodian.")
                )
        elif self.purpose == "Issue":
            if not (self.source_location or self.source_department or self.source_custodian):
                frappe.throw(
                    _("Issue requires at least one of Source Location, Source Department or Source Custodian.")
                )
            if self.target_location or self.target_department:
                frappe.throw(
                    _("Issue moves the asset out of company locations -- Target Location/Department should be left blank. Use Target Custodian only.")
                )
        elif self.purpose == "Receipt":
            if not (self.target_location or self.target_department):
                frappe.throw(
                    _("Receipt requires Target Location and/or Target Department (the asset is returning to a company location).")
                )

        no_op = (
            self.source_location == self.target_location
            and self.source_department == self.target_department
            and self.source_custodian == self.target_custodian
        )
        if self.purpose == "Transfer" and no_op:
            frappe.throw(_("Source and Target are identical -- nothing to move."))

    def _apply_to_asset(self) -> None:
        updates = {}
        if self.target_location:
            updates["location"] = self.target_location
        if self.target_department:
            updates["department"] = self.target_department

        if updates:
            asset = frappe.get_doc("Asset", self.asset)
            for fieldname, value in updates.items():
                asset.db_set(fieldname, value, update_modified=False)

    def _revert_asset(self) -> None:
        """Revert to this movement's own source snapshot. If another
        movement happened after this one and is later cancelled out of
        order, the person should re-check Asset.location manually --
        this deliberately doesn't try to replay movement history."""
        asset = frappe.get_doc("Asset", self.asset)
        asset.db_set("location", self.source_location or "", update_modified=False)
        if self.source_department:
            asset.db_set("department", self.source_department, update_modified=False)