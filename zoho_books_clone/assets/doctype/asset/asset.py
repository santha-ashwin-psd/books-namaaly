import frappe
from frappe.model.document import Document
from frappe.utils import add_years

class Asset(Document):

    def validate(self):
        self.generate_depreciation_schedule()

    def generate_depreciation_schedule(self):
        # NOTE (ported from legacy Assets module): `depreciation_method` offers
        # "Straight Line" / "Written Down Value" as a Select option, but this
        # function always computes straight-line depreciation regardless of
        # which one is chosen. WDV is effectively a no-op field right now.
        # Flagging rather than silently adding WDV math — that's new behavior,
        # not a straight port, and should be a deliberate follow-up phase.

        # Clear old schedule
        self.depreciation_schedule = []

        if (
            not self.purchase_cost
            or not self.useful_life
            or self.useful_life <= 0
        ):
            return

        purchase_cost = self.purchase_cost
        salvage_value = self.salvage_value or 0
        useful_life = self.useful_life

        yearly_depreciation = (
            purchase_cost - salvage_value
        ) / useful_life

        opening = purchase_cost

        for year in range(1, useful_life + 1):

            closing = opening - yearly_depreciation

            if closing < salvage_value:
                closing = salvage_value

            self.append("depreciation_schedule", {

                "year": year,

                "depreciation_date": add_years(
                    self.purchase_date,
                    year
                ),

                "opening_value": opening,

                "depreciation_amount": yearly_depreciation,

                "closing_value": closing,

                "status": "Pending"

            })

            opening = closing

        self.current_value = purchase_cost