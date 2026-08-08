from __future__ import annotations

import frappe
from frappe.model.document import Document


class QCCoverage(Document):
    """
    Deliberately thin. All creation/lookup/cleanup logic lives in
    quality.qc_engine.get_or_create_coverage() — this doctype is just the
    DB-enforced uniqueness primitive (source_row is `unique: 1` in the
    JSON), not a place for business logic. Do not add validate()/on_update()
    side effects here without re-reading qc_engine.get_or_create_coverage's
    duplicate-key handling first, since inserts of this doctype are expected
    to fail on purpose under concurrency and that failure is caught deliberately.
    """
    pass