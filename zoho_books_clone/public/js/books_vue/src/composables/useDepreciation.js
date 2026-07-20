import { flt, fmtDate } from "../utils/format.js";

// Depreciation schedule projection.
//
// Mirrors the backend logic in assets/doctype/asset/asset.py
// (Asset.generate_depreciation_schedule) for the Straight Line method, and
// additionally supports the Written Down Value (declining balance) method that
// the Asset.depreciation_method select offers. Everything is computed purely
// from the asset's own fields so the projection works even when the saved
// child-table rows are empty or out of date.

function addYears(dateStr, years) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return "";
  d.setFullYear(d.getFullYear() + years);
  return d.toISOString().slice(0, 10);
}

// Years fully elapsed between the purchase date and today (floored).
export function yearsElapsed(purchaseDate) {
  if (!purchaseDate) return 0;
  const start = new Date(purchaseDate);
  if (isNaN(start.getTime())) return 0;
  const now = new Date();
  let yrs = now.getFullYear() - start.getFullYear();
  const m = now.getMonth() - start.getMonth();
  if (m < 0 || (m === 0 && now.getDate() < start.getDate())) yrs -= 1;
  return yrs;
}

export function computeSchedule(asset) {
  const cost = flt(asset.purchase_cost);
  const salvage = flt(asset.salvage_value);
  const life = parseInt(asset.useful_life) || 0;
  const method = asset.depreciation_method || "Straight Line";

  if (!cost || !life) return [];

  const rows = [];
  let opening = cost;
  let accumulated = 0;

  if (method === "Written Down Value" && salvage > 0 && salvage < cost) {
    const rate = 1 - Math.pow(salvage / cost, 1 / life);
    for (let year = 1; year <= life; year++) {
      let dep = opening * rate;
      let closing = opening - dep;
      if (closing < salvage) {
        closing = salvage;
        dep = opening - salvage;
      }
      accumulated += dep;
      rows.push({
        year,
        depreciation_date: addYears(asset.purchase_date, year),
        opening_value: round(opening),
        depreciation_amount: round(dep),
        accumulated_value: round(accumulated),
        closing_value: round(closing),
        status: "Pending",
      });
      opening = closing;
    }
  } else {
    // Straight Line (default + backend behaviour)
    const dep = (cost - salvage) / life;
    for (let year = 1; year <= life; year++) {
      let closing = opening - dep;
      if (closing < salvage) closing = salvage;
      accumulated += dep;
      rows.push({
        year,
        depreciation_date: addYears(asset.purchase_date, year),
        opening_value: round(opening),
        depreciation_amount: round(dep),
        accumulated_value: round(accumulated),
        closing_value: round(closing),
        status: "Pending",
      });
      opening = closing;
    }
  }

  return rows;
}

function round(v) {
  return Math.round((v + Number.EPSILON) * 100) / 100;
}

// Aggregate figures for KPI cards, including the position "as of today".
export function scheduleSummary(asset, rows) {
  const cost = flt(asset.purchase_cost);
  const salvage = flt(asset.salvage_value);
  const life = parseInt(asset.useful_life) || 0;
  if (!cost || !life) {
    return { cost: 0, salvage: 0, annual: 0, totalDep: 0, toDate: 0, bookValue: cost, life: 0 };
  }

  const totalDep = rows.reduce((s, r) => s + flt(r.depreciation_amount), 0);
  const annual =
    asset.depreciation_method === "Written Down Value"
      ? rows[0]?.depreciation_amount || 0
      : (cost - salvage) / life;

  const elapsed = Math.min(Math.max(yearsElapsed(asset.purchase_date), 0), life);
  const toDate =
    asset.depreciation_method === "Written Down Value"
      ? rows.slice(0, elapsed).reduce((s, r) => s + flt(r.depreciation_amount), 0)
      : annual * elapsed;

  return {
    cost,
    salvage,
    annual,
    totalDep,
    toDate: round(toDate),
    bookValue: round(cost - toDate),
    life,
  };
}

export { fmtDate };