"""
Renumber documents that use a Frappe naming series (e.g. INV-2026-00009 -> INV-2026-00001)
so that existing records become sequential starting at 1, with no gaps, and the
Series counter is reset so the NEXT new document continues correctly after the last one.

HOW TO RUN
----------
Copy this file into your bench apps folder (or anywhere bench can import it) and run:

    bench --site your-site-name console

Then inside the console:

    from renumber_naming_series import renumber
    renumber("Sales Invoice", prefix="INV-2026-", padding=5)

Or run directly as a script:

    bench --site your-site-name execute renumber_naming_series.renumber \
        --kwargs "{'doctype':'Sales Invoice','prefix':'INV-2026-','padding':5}"

WHAT IT DOES
------------
1. Fetches all docs of the given doctype whose `name` starts with `prefix`,
   ordered by creation (oldest first) - so the oldest record becomes 00001,
   next becomes 00002, and so on, with zero gaps.
2. Uses frappe.rename_doc() for each one, which also fixes up every Link/Dynamic
   Link field pointing to that document across the whole site (child tables,
   references, GL Entries, etc.) - not just a raw SQL update.
3. Updates the `tabSeries` counter row for that prefix so the *next* auto-generated
   name continues correctly from the last renumbered record (avoids collisions).

IMPORTANT NOTES
----------------
- BACK UP YOUR DATABASE before running this (bench --site your-site backup).
- Run this when no one else is using the system / during low traffic, since
  renaming documents can briefly lock rows.
- If two docs would end up mapped to names that already exist and aren't part
  of the batch, rename_doc will raise - the script uses a temporary "__tmp__"
  prefix pass first to avoid collisions between old and new numbers.
- `padding` must match the ##### count in your naming series (5 hashes = 5 here).
- Works for any doctype using a simple prefix + zero-padded running number series
  (Sales Invoice, Purchase Invoice, Quotation, Sales Order, Credit Note, etc.)
"""

import frappe


def renumber(doctype: str, prefix: str, padding: int = 5, start: int = 1, dry_run: bool = False):
	"""
	Renumber all documents of `doctype` whose name starts with `prefix` to be
	sequential, starting at `start`, ordered by creation date.

	Example:
	    renumber("Sales Invoice", prefix="INV-2026-", padding=5)
	    -> INV-2026-00009, INV-2026-00010 (oldest->newest) become
	       INV-2026-00001, INV-2026-00002 ...
	"""

	docs = frappe.get_all(
		doctype,
		filters={"name": ["like", f"{prefix}%"]},
		fields=["name", "creation"],
		order_by="creation asc",
	)

	if not docs:
		frappe.msgprint(f"No records found for {doctype} with prefix '{prefix}'")
		return []

	print(f"Found {len(docs)} records for {doctype} with prefix '{prefix}'")

	# Build old -> new name map
	rename_map = []
	counter = start
	for d in docs:
		new_name = f"{prefix}{str(counter).zfill(padding)}"
		rename_map.append((d.name, new_name))
		counter += 1

	# Show the plan
	for old, new in rename_map:
		marker = "  (no change)" if old == new else ""
		print(f"  {old}  ->  {new}{marker}")

	if dry_run:
		print("Dry run only - no changes made.")
		return rename_map

	# PASS 1: move everything to a temporary namespace to avoid name collisions
	# between old numbers and new numbers (e.g. old 00009 might need to become
	# new 00003 while something else is currently 00003).
	tmp_map = []
	for old, new in rename_map:
		if old == new:
			continue
		tmp_name = f"__tmp__{old}"
		frappe.rename_doc(doctype, old, tmp_name, force=True)
		tmp_map.append((tmp_name, new))
	frappe.db.commit()

	# PASS 2: move from temp names to the final new names
	for tmp_name, new in tmp_map:
		frappe.rename_doc(doctype, tmp_name, new, force=True)
	frappe.db.commit()

	# Reset the Series counter so the NEXT new document continues correctly.
	# Frappe's Series doctype stores the current counter keyed by the prefix.
	last_number = counter - 1
	series_key = prefix
	frappe.db.sql(
		"insert into tabSeries (name, current) values (%s, %s) "
		"on duplicate key update current=%s",
		(series_key, last_number, last_number),
	)
	frappe.db.commit()

	print(f"Done. {doctype} renumbered from {prefix}{str(start).zfill(padding)} "
		  f"to {prefix}{str(last_number).zfill(padding)}. "
		  f"Series counter '{series_key}' set to {last_number}, "
		  f"so next new record will be {prefix}{str(last_number + 1).zfill(padding)}.")

	return rename_map


if __name__ == "__main__":
	import sys
	# Allows: bench execute renumber_naming_series.renumber --kwargs "{...}"
	print(__doc__)


# ---------------------------------------------------------------------------
# BATCH CONFIG - all Sales and Purchase module doctypes with their series.
# Year (2026) is hardcoded into the prefix here since that's what your naming
# series currently resolves to (INV-.YYYY.-.#####  ->  INV-2026-). Update the
# year below once a new financial year rolls over and old records need it.
# ---------------------------------------------------------------------------
SALES_PURCHASE_SERIES = [
	# (doctype,            prefix,          padding)
	("Quotation",          "QT-2026-",      5),
	("Sales Order",        "SO-2026-",      5),
	("Delivery Note",      "DN-2026-",      5),
	("Sales Invoice",      "INV-2026-",     5),
	("Purchase Order",     "PO-2026-",      5),
	("Purchase Receipt",   "PR-2026-",      5),
	("Purchase Invoice",   "PINV-2026-",    5),
	("Payment Entry",      "PAY-2026-",     5),
]


def renumber_all(configs=None, dry_run=False):
	"""
	Run renumber() across every doctype in SALES_PURCHASE_SERIES (or a custom
	list of (doctype, prefix, padding) tuples passed via `configs`).

	Example:
	    from zoho_books_clone.renumber_naming_series import renumber_all
	    renumber_all(dry_run=True)   # preview everything first
	    renumber_all()               # actually run it for all doctypes
	"""
	configs = configs or SALES_PURCHASE_SERIES
	results = {}
	for doctype, prefix, padding in configs:
		print(f"\n{'='*60}\n{doctype}  (prefix={prefix})\n{'='*60}")
		try:
			results[doctype] = renumber(doctype, prefix=prefix, padding=padding, dry_run=dry_run)
		except Exception as e:
			print(f"  !! FAILED for {doctype}: {e}")
			results[doctype] = None
	return results