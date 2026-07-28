from __future__ import annotations
"""
Asset depreciation engine — Phase 3 of the asset-management accounting
build-out.

Replaces the old always-straight-line, always-annual, never-pro-rated
schedule generator that lived inline in Asset.generate_depreciation_schedule.
This module only *calculates* a schedule (list of dicts); it never touches
the database or the GL — see assets/depreciation_posting.py for that.

Design notes / deliberate scope limits (documented rather than silently
approximated):

  - Written Down Value (WDV) rate: derived from cost, salvage_value and
    useful_life via the standard reducing-balance formula
        rate = 1 - (salvage / cost) ** (1 / life_years)
    WDV mathematically never reaches exactly zero, so it requires a
    non-zero salvage to converge in a finite number of periods. If the
    person leaves Salvage Value at 0 (a very common case), we use a
    notional 1% of cost as the *rate basis only* -- it is never written
    back to the Asset or shown as the real salvage value, it only shapes
    how fast the WDV rate declines the book value. This mirrors how most
    small-business accounting tools handle a zero-salvage WDV asset.

  - Monthly frequency pro-rates only the FIRST period, by calendar days
    from Available for Use Date (falling back to Purchase Date) to the
    end of that calendar month. Every subsequent period is a full
    calendar month. This means the schedule's last period lands slightly
    *after* the nominal life_years anniversary when the first period was
    partial -- which is correct: an asset placed in service mid-month
    finishes depreciating slightly later than one placed in service on
    the 1st, because the partial first month contributed less than a
    full month's depreciation.

  - Annually frequency is anchored to Available for Use Date /
    Purchase Date itself (each period is exactly one year later), not to
    a fiscal-year boundary. No pro-ration is needed there since every
    period is, by construction, a full year long. Fiscal-year-aligned
    annual depreciation (where the first "year" might be a stub period
    ending at fiscal year end) is a further refinement left for later --
    flagging rather than silently guessing at a fiscal year convention
    this app doesn't otherwise attach to Asset.
"""

from frappe.utils import (
    add_days,
    add_months,
    add_years,
    flt,
    get_last_day,
    getdate,
)

_ZERO_SALVAGE_RATE_BASIS_PCT = 0.01  # 1% of cost, rate-calculation only


def build_schedule(asset) -> list[dict]:
    """Pure calculation: returns a list of row-dicts shaped for the
    Depreciation Schedule child table. Caller is responsible for clearing
    the old schedule and appending these (see Asset.generate_depreciation_schedule).
    Returns [] if the asset doesn't have enough info to depreciate yet.
    """
    cost = flt(asset.purchase_cost)
    salvage = flt(asset.salvage_value)
    life_years = int(asset.useful_life or 0)

    if cost <= 0 or life_years <= 0:
        return []

    start_date = getdate(asset.available_for_use_date or asset.purchase_date)
    if not start_date:
        return []

    if salvage < 0:
        salvage = 0.0
    if salvage > cost:
        # Nonsensical input -- don't project a schedule that "depreciates"
        # upward. Let Asset validation surface this instead of engine math.
        return []

    method = asset.depreciation_method or "Straight Line"
    frequency = asset.depreciation_posting_frequency or "Annually"

    if frequency == "Monthly":
        return _build_monthly(cost, salvage, life_years, start_date, method)
    return _build_annual(cost, salvage, life_years, start_date, method)


# ─── Rate helpers ──────────────────────────────────────────────────────────

def _wdv_annual_rate(cost: float, salvage: float, life_years: int) -> float:
    rate_basis_salvage = salvage if salvage > 0 else cost * _ZERO_SALVAGE_RATE_BASIS_PCT
    if cost <= 0 or life_years <= 0:
        return 0.0
    ratio = max(rate_basis_salvage / cost, 1e-6)  # guard against math domain error
    return 1 - ratio ** (1.0 / life_years)


def _wdv_monthly_rate(annual_rate: float) -> float:
    return 1 - (1 - annual_rate) ** (1.0 / 12)


def _true_up_final_row(rows: list[dict], salvage: float) -> None:
    """A pro-rated first period contributes less than a full period's
    depreciation, so summing exactly total_periods periods can leave a
    small residual above salvage_value at the end (the "missing" fraction
    of the first period). Rather than run extra low-value periods forever,
    true up the last generated row so the schedule always fully
    depreciates to salvage by its final row -- the standard "balloon the
    remainder into the last period" convention.
    """
    if not rows:
        return
    last = rows[-1]
    residual = flt(last["closing_value"]) - salvage
    if residual > 0.01:
        last["depreciation_amount"] = flt(last["depreciation_amount"]) + residual
        last["closing_value"] = salvage




def _build_annual(cost, salvage, life_years, start_date, method) -> list[dict]:
    rows = []
    opening = cost
    annual_rate = _wdv_annual_rate(cost, salvage, life_years) if method == "Written Down Value" else 0.0
    straight_line_annual = (cost - salvage) / life_years if method != "Written Down Value" else 0.0

    for period_no in range(1, life_years + 1):
        if opening <= salvage:
            break

        if method == "Written Down Value":
            dep = opening * annual_rate
        else:
            dep = straight_line_annual

        closing = opening - dep
        if closing < salvage:
            closing = salvage
        dep = opening - closing  # reconcile after any floor clamp

        rows.append({
            "year": period_no,
            "period_no": period_no,
            "depreciation_date": add_years(start_date, period_no),
            "opening_value": opening,
            "depreciation_amount": dep,
            "closing_value": closing,
            "status": "Pending",
            "is_pro_rata": 0,
        })
        opening = closing

    _true_up_final_row(rows, salvage)
    return rows


# ─── Monthly schedule (first period pro-rated by calendar days) ───────────

def _build_monthly(cost, salvage, life_years, start_date, method) -> list[dict]:
    total_periods = life_years * 12
    opening = cost

    annual_rate = _wdv_annual_rate(cost, salvage, life_years) if method == "Written Down Value" else 0.0
    monthly_rate = _wdv_monthly_rate(annual_rate) if method == "Written Down Value" else 0.0
    straight_line_monthly = (cost - salvage) / total_periods if method != "Written Down Value" else 0.0

    first_period_end = get_last_day(start_date)
    days_in_first_month = (first_period_end - getdate(f"{start_date.year}-{start_date.month:02d}-01")).days + 1
    days_active_first_month = (first_period_end - start_date).days + 1
    first_period_fraction = min(1.0, days_active_first_month / days_in_first_month) if days_in_first_month else 1.0

    rows = []
    period_end = first_period_end

    for period_no in range(1, total_periods + 1):
        if opening <= salvage:
            break

        is_first = period_no == 1
        fraction = first_period_fraction if is_first else 1.0

        if method == "Written Down Value":
            dep = opening * monthly_rate * fraction
        else:
            dep = straight_line_monthly * fraction

        closing = opening - dep
        if closing < salvage:
            closing = salvage
        dep = opening - closing

        rows.append({
            "year": ((period_no - 1) // 12) + 1,
            "period_no": period_no,
            "depreciation_date": period_end,
            "opening_value": opening,
            "depreciation_amount": dep,
            "closing_value": closing,
            "status": "Pending",
            "is_pro_rata": 1 if (is_first and fraction < 0.999) else 0,
        })
        opening = closing

        # Next period end = last day of the following calendar month.
        period_end = get_last_day(add_months(period_end, 1))

    _true_up_final_row(rows, salvage)
    return rows