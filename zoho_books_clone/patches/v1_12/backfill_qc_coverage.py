"""
Patch v1_12: back-fill QC Coverage from existing QC Inspections.

QC Coverage is a new, additive doctype (Phase 1 of the QC flow redesign --
see QC_Flow_Redesign.md) whose source_row is now the authoritative answer
to "does this row have coverage." Every QC Inspection created before this
release predates source_row, so this patch computes it for them and
inserts the matching QC Coverage row.

source_row = f"{child_doctype}:{child_row_name}" -- for an old QC
Inspection we don't have the child row name on file directly, so it's
recovered via best-effort matching against the CURRENT rows of the
referenced document: reference_type + reference_name narrows to one
transactional doc, then item (+ batch_no, when set) narrows to specific
rows on it. Only an unambiguous 1:1 match is back-filled; anything with
zero or multiple candidate rows is logged and skipped rather than guessed
-- a wrong guess here would silently misattribute coverage, which is
exactly the failure mode this redesign exists to eliminate. Skipped/
ambiguous inspections keep working exactly as they do today (the legacy
QC gate before this patch already tolerated a blank/wrong row link); they
just won't benefit from source_row-based coverage until a human re-links
them or a fresh inspection is created for that row going forward.

Only touches non-cancelled QC Inspections (docstatus != 2) -- a cancelled
one is not live coverage and get_or_create_coverage() would immediately
treat any QC Coverage row pointing at it as stale and delete it again.

Safe to re-run: skips any QC Inspection that already has a QC Coverage
row pointing at it, and QC Coverage.source_row is itself unique so a
duplicate insert attempt is a no-op (caught, not fatal).
"""
import frappe


def execute():
    if not frappe.db.exists("DocType", "QC Coverage"):
        return  # schema sync for this doctype hasn't landed yet
    if not frappe.db.exists("DocType", "QC Inspection"):
        return

    already_covered = set(
        frappe.db.get_all("QC Coverage", pluck="qc_inspection")
    )

    inspections = frappe.db.get_all(
        "QC Inspection",
        filters={"docstatus": ["!=", 2]},
        fields=["name", "reference_type", "reference_name", "item", "batch_no"],
    )

    backfilled = 0
    skipped_no_match = []
    skipped_ambiguous = []

    # Group by reference doc so each transactional document's item table is
    # only loaded once, not once per QC Inspection against it.
    by_reference = {}
    for qi in inspections:
        if qi.name in already_covered:
            continue
        key = (qi.reference_type, qi.reference_name)
        by_reference.setdefault(key, []).append(qi)

    for (ref_type, ref_name), qcis in by_reference.items():
        if not ref_type or not ref_name:
            skipped_no_match.extend(qi.name for qi in qcis)
            continue
        if not frappe.db.exists(ref_type, ref_name):
            skipped_no_match.extend(qi.name for qi in qcis)
            continue

        try:
            ref_doc = frappe.get_doc(ref_type, ref_name)
        except Exception:
            skipped_no_match.extend(qi.name for qi in qcis)
            continue

        rows = getattr(ref_doc, "items", []) or []

        for qi in qcis:
            candidates = [
                r for r in rows
                if (getattr(r, "item_code", None) or getattr(r, "item", None)) == qi.item
                and (not qi.batch_no or getattr(r, "batch_no", None) == qi.batch_no)
            ]
            if len(candidates) == 0:
                skipped_no_match.append(qi.name)
                continue
            if len(candidates) > 1:
                skipped_ambiguous.append(qi.name)
                continue

            row = candidates[0]
            source_row = f"{row.doctype}:{row.name}"

            if frappe.db.exists("QC Coverage", {"source_row": source_row}):
                # Another (better-matched) inspection already claimed this
                # row -- don't overwrite, just skip. Leaves the row's
                # existing coverage as-is.
                skipped_ambiguous.append(qi.name)
                continue

            try:
                cov = frappe.new_doc("QC Coverage")
                cov.source_row    = source_row
                cov.qc_inspection = qi.name
                cov.insert(ignore_permissions=True)
                backfilled += 1
            except Exception:
                skipped_no_match.append(qi.name)

    if backfilled:
        frappe.db.commit()

    print(f"✅  v1_12: QC Coverage back-filled for {backfilled} existing QC Inspection(s).")
    if skipped_no_match:
        print(
            f"⚠️  v1_12: {len(skipped_no_match)} QC Inspection(s) could not be matched to a "
            "current row on their reference document (deleted/edited rows) and were skipped: "
            + ", ".join(skipped_no_match[:20])
            + (" ..." if len(skipped_no_match) > 20 else "")
        )
    if skipped_ambiguous:
        print(
            f"⚠️  v1_12: {len(skipped_ambiguous)} QC Inspection(s) matched more than one "
            "candidate row (or lost a race to a better match) and were left un-backfilled "
            "rather than guessed: "
            + ", ".join(skipped_ambiguous[:20])
            + (" ..." if len(skipped_ambiguous) > 20 else "")
        )