from __future__ import annotations

import re
import frappe
from frappe import _
from frappe.model.document import Document

_GSTIN_RE = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')

# Maps the human-readable Select field value to the MM-DD string
# expected by bootstrap._seed_fiscal_year.
_MONTH_TO_START = {
    "January":   "01-01",
    "February":  "02-01",
    "March":     "03-01",
    "April":     "04-01",
    "May":       "05-01",
    "June":      "06-01",
    "July":      "07-01",
    "August":    "08-01",
    "September": "09-01",
    "October":   "10-01",
    "November":  "11-01",
    "December":  "12-01",
}


class BooksCompany(Document):
    def validate(self):
        self.company_name = (self.company_name or "").strip()
        if not self.company_name:
            frappe.throw(_("Company Name is required."))
        if self.gstin:
            self.gstin = self.gstin.strip().upper()
            if not _GSTIN_RE.match(self.gstin):
                frappe.throw(_("Invalid Company GSTIN: {0}. Expected format: 22AAAAA0000A1Z5").format(self.gstin))

        if not self.company_abbr:
            self.company_abbr = self._derive_abbr(self.company_name)

        if self.smtp_enabled:
            for f in ("smtp_server", "smtp_login", "smtp_password"):
                if not self.get(f):
                    frappe.throw(_("SMTP {0} is required when company SMTP is enabled.").format(f))
            if not self.smtp_from_email:
                self.smtp_from_email = self.smtp_login

        self._validate_inventory_accounts()

    def _validate_inventory_accounts(self):
        """
        Guard the perpetual-inventory default accounts: wrong type/company
        here would silently misroute every purchase/receipt/return GL entry
        for this company, with nothing downstream re-checking it.
        """
        checks = (
            ("default_inventory_account", ["Stock"]),
            ("stock_received_not_billed", ["Stock Received But Not Billed"]),
            ("default_cogs_account", ["Cost of Goods Sold", "Expense"]),
        )
        for field, expected_types in checks:
            account = self.get(field)
            if not account:
                continue
            acc = frappe.db.get_value("Account", account, ["account_type", "company"], as_dict=True)
            if not acc:
                continue
            if acc.company and acc.company != self.company_name:
                frappe.throw(_(
                    "{0}: account {1} belongs to company {2}, not {3}."
                ).format(self.meta.get_label(field), account, acc.company, self.company_name))
            if acc.account_type not in expected_types:
                frappe.throw(_(
                    "{0}: account {1} must be of type {2}, found {3}."
                ).format(self.meta.get_label(field), account, "/".join(expected_types), acc.account_type or "None"))

    def after_insert(self):
        """Seed Chart of Accounts + default Fiscal Year for this company.

        Runs automatically whenever a BooksCompany record is created — whether
        through the signup flow, the settings UI, or directly via the Frappe
        desk.  bootstrap_company_data is idempotent so duplicate calls are safe.
        """
        try:
            from zoho_books_clone.books_setup.bootstrap import bootstrap_company_data
            bootstrap_company_data(self.company_name, self._fy_start())
            self._set_inventory_account_defaults()
        except Exception as exc:
            # Log but never block the insert — a missing FY is recoverable;
            # a rolled-back company creation is not.
            frappe.log_error(
                f"BooksCompany.after_insert — could not seed fiscal year for "
                f"'{self.company_name}': {exc}",
                "Books Bootstrap",
            )

    def _set_inventory_account_defaults(self):
        """Point inventory account fields at the freshly seeded CoA leaves."""
        mapping = {
            "default_inventory_account": ("Stock In Hand", "Stock"),
            "stock_received_not_billed": (
                "Stock Received",
                "Stock Received But Not Billed",
            ),
            "default_cogs_account": ("Cost of Goods Sold", "Cost of Goods Sold"),
        }
        updates = {}
        for field, (acct_name, acct_type) in mapping.items():
            if self.get(field):
                continue
            acct = (
                frappe.db.get_value(
                    "Account",
                    {"account_name": acct_name, "company": self.company_name, "is_group": 0},
                    "name",
                )
                or frappe.db.get_value(
                    "Account",
                    {"account_type": acct_type, "company": self.company_name, "is_group": 0},
                    "name",
                )
            )
            if acct:
                updates[field] = acct
        if updates:
            self.db_set(updates, update_modified=False)

    def _fy_start(self) -> str:
        """Return the MM-DD fiscal year start string derived from fiscal_year_start_month."""
        month = (self.fiscal_year_start_month or "April").strip()
        return _MONTH_TO_START.get(month, "04-01")

    @staticmethod
    def _derive_abbr(name: str) -> str:
        parts = [p for p in name.replace("&", " ").split() if p]
        if not parts:
            return ""
        if len(parts) == 1:
            return parts[0][:3].upper()
        return "".join(p[0] for p in parts[:4]).upper()

    def get_smtp_config(self) -> dict | None:
        """Return decrypted SMTP config dict, or None if not enabled/complete."""
        if not self.smtp_enabled:
            return None
        try:
            password = self.get_password("smtp_password", raise_exception=False)
        except Exception:
            password = None
        if not (self.smtp_server and self.smtp_login and password):
            return None
        return {
            "server": self.smtp_server,
            "port": int(self.smtp_port or 587),
            "login": self.smtp_login,
            "password": password,
            "use_tls": bool(self.smtp_use_tls),
            "use_ssl": bool(self.smtp_use_ssl),
            "from_email": self.smtp_from_email or self.smtp_login,
            "from_name": self.smtp_from_name or self.company_name,
        }