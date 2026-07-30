# Copyright (c) 2026
# Recurring Subscription (Frappe "Auto Repeat") lifecycle + analytics endpoints.

import frappe
from frappe import _
from frappe.utils import flt, getdate, today


def _get_ar(name: str):
    if not name:
        frappe.throw(_("Subscription name is required"))
    if not frappe.db.exists("Auto Repeat", name):
        frappe.throw(_("Subscription {0} not found").format(name))
    return frappe.get_doc("Auto Repeat", name)


def _ui_status(doc) -> str:
    """Map Frappe statuses to UI-friendly states used by Recurring.vue."""
    if doc.disabled and doc.status != "Completed":
        return "Paused"
    if doc.status == "Completed":
        return "Completed"
    if doc.status == "Disabled":
        return "Paused"
    return "Active"


def _party_for(reference_doctype: str, reference_document: str):
    """Return (party_label, party_value, amount) tuple for a reference doc."""
    if not (reference_doctype and reference_document):
        return "", "", 0.0
    try:
        if reference_doctype == "Sales Invoice":
            row = frappe.db.get_value(
                "Sales Invoice", reference_document,
                ["customer", "customer_name", "grand_total"], as_dict=True
            )
            if row:
                return "Customer", row.customer_name or row.customer or "", flt(row.grand_total)
        elif reference_doctype == "Purchase Invoice":
            row = frappe.db.get_value(
                "Purchase Invoice", reference_document,
                ["supplier", "supplier_name", "grand_total"], as_dict=True
            )
            if row:
                return "Supplier", row.supplier_name or row.supplier or "", flt(row.grand_total)
        elif reference_doctype == "Quotation":
            row = frappe.db.get_value(
                "Quotation", reference_document,
                ["party_name", "customer_name", "grand_total"], as_dict=True
            )
            if row:
                return "Customer", row.customer_name or row.party_name or "", flt(row.grand_total)
    except Exception:
        pass
    return "", "", 0.0


# ------------------------------------------------------------------ list

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_subscriptions(status=None, reference_doctype=None, limit=200):
    """List recurring subscriptions enriched with party + amount."""
    filters = {}
    if reference_doctype:
        filters["reference_doctype"] = reference_doctype

    rows = frappe.get_all(
        "Auto Repeat",
        filters=filters,
        fields=[
            "name", "subscription_name", "reference_doctype", "reference_document",
            "frequency", "start_date", "end_date",
            "next_schedule_date", "status", "disabled",
            "notify_by_email", "submit_on_creation", "creation",
        ],
        order_by="next_schedule_date asc, creation desc",
        limit_page_length=int(limit or 200),
    )

    out = []
    today_str = today()
    for r in rows:
        ui_status = _ui_status(frappe._dict(r))
        if status and status != "all" and status != ui_status:
            continue
        party_label, party, amount = _party_for(r.reference_doctype, r.reference_document)
        runs_count = frappe.db.count(
            "Communication",
            {"reference_doctype": "Auto Repeat", "reference_name": r.name},
        ) if False else 0  # placeholder, real count comes from generated docs below
        # Real run count: documents whose `auto_repeat` field == this AR name
        try:
            runs_count = frappe.db.count(r.reference_doctype, {"auto_repeat": r.name})
        except Exception:
            runs_count = 0

        out.append({
            **r,
            "ui_status": ui_status,
            "party_label": party_label,
            "party": party,
            "amount": amount,
            "runs_count": runs_count,
            "is_due": bool(r.next_schedule_date and str(r.next_schedule_date) <= today_str and ui_status == "Active"),
        })

    return out


# ------------------------------------------------------------------ detail

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_subscription(name):
    doc = _get_ar(name)
    party_label, party, amount = _party_for(doc.reference_doctype, doc.reference_document)

    # Generated documents
    runs = []
    try:
        runs = frappe.get_all(
            doc.reference_doctype,
            filters={"auto_repeat": doc.name},
            fields=["name", "creation", "docstatus", "grand_total"],
            order_by="creation desc",
            limit_page_length=100,
        )
    except Exception:
        runs = []

    total_billed = sum(flt(r.get("grand_total")) for r in runs)

    # Upcoming schedule (next 5 runs)
    upcoming = []
    try:
        sched = doc.get_auto_repeat_schedule() or []
        upcoming = [
            {"date": str(s.get("next_scheduled_date")), "frequency": s.get("frequency")}
            for s in sched[:5]
        ]
    except Exception:
        upcoming = []

    return {
        "name": doc.name,
        "subscription_name": doc.subscription_name or "",
        "reference_doctype": doc.reference_doctype,
        "reference_document": doc.reference_document,
        "frequency": doc.frequency,
        "start_date": str(doc.start_date) if doc.start_date else None,
        "end_date": str(doc.end_date) if doc.end_date else None,
        "next_schedule_date": str(doc.next_schedule_date) if doc.next_schedule_date else None,
        "submit_on_creation": doc.submit_on_creation,
        "notify_by_email": doc.notify_by_email,
        "recipients": doc.recipients,
        "subject": doc.subject,
        "message": doc.message,
        "status": doc.status,
        "ui_status": _ui_status(doc),
        "disabled": doc.disabled,
        "creation": str(doc.creation),
        "party_label": party_label,
        "party": party,
        "template_amount": amount,
        "runs": runs,
        "runs_count": len(runs),
        "total_billed": total_billed,
        "upcoming": upcoming,
    }


# ------------------------------------------------------------------ lifecycle

@frappe.whitelist(allow_guest=False, methods=["POST"])
def pause_subscription(name):
    from zoho_books_clone.utils.access import require_write
    require_write()
    doc = _get_ar(name)
    if doc.disabled:
        return {"ok": True, "status": _ui_status(doc), "message": "Already paused"}
    doc.disabled = 1
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "status": _ui_status(doc), "message": f"{name} paused"}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def resume_subscription(name):
    from zoho_books_clone.utils.access import require_write
    require_write()
    doc = _get_ar(name)
    if not doc.disabled:
        return {"ok": True, "status": _ui_status(doc), "message": "Already active"}
    if doc.end_date and getdate(doc.end_date) < getdate(today()):
        frappe.throw(_("Cannot resume — end date is in the past. Extend end date first."))
    doc.disabled = 0
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "status": _ui_status(doc), "message": f"{name} resumed"}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def cancel_subscription(name):
    """Cancel = disable + freeze end_date in the past so it never resumes.

    Frappe's Auto Repeat.validate_dates() refuses end_date == today() or
    end_date == start_date, so we bypass validation with a direct db update
    after disabling via save().
    """
    from zoho_books_clone.utils.access import require_write
    require_write()
    from frappe.utils import add_days
    doc = _get_ar(name)
    doc.disabled = 1
    doc.save(ignore_permissions=True)
    # Stamp end_date directly to yesterday (or day before start, whichever is later)
    start = getdate(doc.start_date) if doc.start_date else getdate(today())
    yesterday = add_days(today(), -1)
    new_end = yesterday if getdate(yesterday) > start else add_days(start, -1)
    frappe.db.set_value("Auto Repeat", name, "end_date", new_end,
                        update_modified=False)
    frappe.db.commit()
    return {"ok": True, "status": "Completed", "message": f"{name} cancelled"}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def delete_subscription(name):
    from zoho_books_clone.utils.access import require_write
    require_write()
    _get_ar(name)
    frappe.delete_doc("Auto Repeat", name, ignore_permissions=False)
    frappe.db.commit()
    return {"ok": True, "message": f"{name} deleted"}


@frappe.whitelist(allow_guest=False, methods=["POST"])
def run_subscription_now(name):
    """Force-generate the next document immediately, ignoring schedule."""
    from zoho_books_clone.utils.access import require_write
    require_write()
    doc = _get_ar(name)
    if doc.disabled:
        frappe.throw(_("Cannot run a paused subscription. Resume first."))

    # Pre-flight: confirm today falls in an open, unlocked fiscal year for the
    # reference document's company.  make_new_document() clones the source doc
    # with today's date — if the period is locked or missing the generated doc
    # would fail on save/submit anyway, but catching it here gives a clean
    # error before any document is created.
    try:
        company = frappe.db.get_value(
            doc.reference_doctype, doc.reference_document, "company"
        ) or ""
        if company:
            from zoho_books_clone.db.validators import validate_fiscal_year
            validate_fiscal_year(today(), company)
    except frappe.ValidationError:
        raise
    except Exception:
        pass  # company field absent on this doctype — skip the pre-flight

    try:
        new_doc = doc.make_new_document()
        if doc.notify_by_email and doc.recipients:
            try:
                doc.send_notification(new_doc)
            except Exception:
                pass
        frappe.db.commit()
        return {"ok": True, "generated": new_doc.name, "doctype": new_doc.doctype}
    except Exception as e:
        frappe.log_error(f"run_subscription_now failed for {name}: {e}")
        frappe.throw(_("Failed to generate document: {0}").format(str(e)))


@frappe.whitelist(allow_guest=False, methods=["POST"])
def update_subscription(name, frequency=None, end_date=None, notify_by_email=None,
                       submit_on_creation=None, recipients=None, subject=None, message=None,
                       subscription_name=None):
    from zoho_books_clone.utils.access import require_write
    require_write()
    doc = _get_ar(name)
    if subscription_name is not None:
        doc.subscription_name = subscription_name
    if frequency is not None:
        doc.frequency = frequency
    if end_date is not None:
        # Empty string means "clear the end date" (open-ended subscription)
        doc.end_date = end_date if end_date else None
    if notify_by_email is not None:
        doc.notify_by_email = int(bool(int(notify_by_email))) if str(notify_by_email).isdigit() else int(bool(notify_by_email))
    if submit_on_creation is not None:
        doc.submit_on_creation = int(bool(int(submit_on_creation))) if str(submit_on_creation).isdigit() else int(bool(submit_on_creation))
    if recipients is not None:
        doc.recipients = recipients
    if subject is not None:
        doc.subject = subject
    if message is not None:
        doc.message = message
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "name": doc.name, "status": _ui_status(doc)}


# ------------------------------------------------------------------ bulk

@frappe.whitelist(allow_guest=False, methods=["POST"])
def bulk_action(names, action):
    """action ∈ {pause, resume, cancel, delete}. names = list[str] or JSON."""
    from zoho_books_clone.utils.access import require_write
    require_write()
    if isinstance(names, str):
        import json
        try:
            names = json.loads(names)
        except Exception:
            names = [n.strip() for n in names.split(",") if n.strip()]

    fn = {
        "pause": pause_subscription,
        "resume": resume_subscription,
        "cancel": cancel_subscription,
        "delete": delete_subscription,
    }.get(action)
    if not fn:
        frappe.throw(_("Unknown action {0}").format(action))

    ok, failed = [], []
    for n in (names or []):
        try:
            fn(n)
            ok.append(n)
        except Exception as e:
            failed.append({"name": n, "error": str(e)})
    return {"ok": ok, "failed": failed}


# ------------------------------------------------------------------ analytics

@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def get_subscription_stats():
    """Aggregate counters for the Recurring page summary strip."""
    all_rows = frappe.get_all(
        "Auto Repeat",
        fields=["name", "status", "disabled", "next_schedule_date", "end_date"],
        limit_page_length=2000,
    )
    today_str = today()
    active = paused = cancelled = completed = due_today = overdue = 0
    for r in all_rows:
        s = _ui_status(frappe._dict(r))
        if s == "Active":
            active += 1
            if r.next_schedule_date and str(r.next_schedule_date) == today_str:
                due_today += 1
            elif r.next_schedule_date and str(r.next_schedule_date) < today_str:
                overdue += 1
        elif s == "Paused":
            paused += 1
        elif s == "Completed":
            completed += 1
    return {
        "total": len(all_rows),
        "active": active,
        "paused": paused,
        "cancelled": cancelled,
        "completed": completed,
        "due_today": due_today,
        "overdue": overdue,
    }


# ------------------------------------------------------------------ make-from

@frappe.whitelist(allow_guest=False, methods=["POST"])
def make_recurring_from_doc(reference_doctype, reference_document, frequency,
                            start_date, end_date=None, submit_on_creation=1,
                            notify_by_email="", recipients="", subject="", message="",
                            subscription_name=""):
    """Create an Auto Repeat attached to an existing document.
    Used by 'Make Recurring' button on Invoice/PO/etc. drawers."""
    from zoho_books_clone.utils.access import require_write
    require_write()
    if not frappe.db.exists(reference_doctype, reference_document):
        frappe.throw(_("Reference document does not exist"))

    # Frappe's Auto Repeat controller requires the source doc to be Submitted (docstatus=1).
    # Catching this here gives a clean user-facing message instead of an OperationalError.
    docstatus = frappe.db.get_value(reference_doctype, reference_document, "docstatus")
    if docstatus != 1:
        status_label = {0: "Draft", 2: "Cancelled"}.get(docstatus, f"status {docstatus}")
        frappe.throw(
            _(
                "Cannot create a recurring subscription for a {0} document. "
                "Please submit {1} first, then create the subscription."
            ).format(status_label, reference_document)
        )

    existing = frappe.db.exists("Auto Repeat", {
        "reference_doctype": reference_doctype,
        "reference_document": reference_document,
        "disabled": 0,
    })
    if existing:
        frappe.throw(_("An active subscription already exists for this document: {0}").format(existing))

    # Pre-flight: ensure the reference doctype has the `auto_repeat` column that
    # Frappe's Auto Repeat validator (update_auto_repeat_id) will SELECT.
    # This column is added by bench migrate / frappe.reload_doctype; if it's absent
    # the insert explodes with OperationalError: (1054, "Unknown column 'auto_repeat'").
    table = f"tab{reference_doctype}"
    col_exists = frappe.db.sql(
        f"SELECT 1 FROM information_schema.COLUMNS "
        f"WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = 'auto_repeat'",
        (table,),
    )
    if not col_exists:
        # Attempt to add the column automatically, then re-validate.
        try:
            frappe.db.sql(f"ALTER TABLE `{table}` ADD COLUMN `auto_repeat` VARCHAR(140) DEFAULT NULL")
            frappe.db.commit()
        except Exception as col_err:
            frappe.log_error(f"make_recurring_from_doc: could not add auto_repeat column to {table}: {col_err}")
            frappe.throw(
                _(
                    "The '{0}' doctype is missing the 'auto_repeat' database column required by "
                    "Frappe's recurring engine. Please run 'bench migrate' on your site and try again."
                ).format(reference_doctype)
            )

    doc = frappe.get_doc({
        "doctype": "Auto Repeat",
        "subscription_name": subscription_name or "",
        "reference_doctype": reference_doctype,
        "reference_document": reference_document,
        "frequency": frequency,
        "start_date": start_date,
        "end_date": end_date or None,
        "submit_on_creation": int(submit_on_creation or 0),
        "notify_by_email": 1 if (recipients or notify_by_email) else 0,
        "recipients": recipients or notify_by_email or "",
        "subject": subject or "",
        "message": message or "",
    })
    try:
        doc.insert(ignore_permissions=False)
    except Exception as e:
        err_str = str(e)
        if "Unknown column 'auto_repeat'" in err_str:
            frappe.throw(
                _(
                    "Database schema is out of date — the 'auto_repeat' column is missing. "
                    "Please run 'bench migrate' on your site and try again."
                )
            )
        raise
    frappe.db.commit()
    return {"ok": True, "name": doc.name}