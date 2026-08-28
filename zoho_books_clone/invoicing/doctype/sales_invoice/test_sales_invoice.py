# Copyright (c) 2026, PS Digitise and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from zoho_books_clone.api.books_data import get_cost_center_spend


class TestSalesInvoice(FrappeTestCase):
    def setUp(self):
        # 1. Create a test company if it doesn't exist
        self.company_name = "Test Budget Company"
        if not frappe.db.exists("Books Company", self.company_name):
            self.company = frappe.get_doc({
                "doctype": "Books Company",
                "company_name": self.company_name,
                "currency": "OMR",
                "is_active": 1,
            }).insert(ignore_permissions=True)
        else:
            self.company = frappe.get_doc("Books Company", self.company_name)

        # Set user default for tenancy check
        frappe.defaults.set_user_default("company", self.company_name)

        # Bootstrap chart of accounts and fiscal year
        from zoho_books_clone.books_setup.bootstrap import bootstrap_company_data
        bootstrap_company_data(self.company_name)

        # 2. Create group cost center
        self.root_cc_name = "Root Test CC"
        if not frappe.db.exists("Cost Center", {"cost_center_name": self.root_cc_name, "company": self.company_name}):
            self.root_cc = frappe.get_doc({
                "doctype": "Cost Center",
                "cost_center_name": self.root_cc_name,
                "is_group": 1,
                "company": self.company_name,
            }).insert(ignore_permissions=True)
        else:
            self.root_cc = frappe.get_doc("Cost Center", {"cost_center_name": self.root_cc_name, "company": self.company_name})

        # 3. Create child cost center
        self.cc_name = "Department CC"
        if not frappe.db.exists("Cost Center", {"cost_center_name": self.cc_name, "company": self.company_name}):
            self.cc = frappe.get_doc({
                "doctype": "Cost Center",
                "cost_center_name": self.cc_name,
                "is_group": 0,
                "company": self.company_name,
                "parent_cost_center": self.root_cc.name,
                "budget": 10000.0,
            }).insert(ignore_permissions=True)
        else:
            self.cc = frappe.get_doc("Cost Center", {"cost_center_name": self.cc_name, "company": self.company_name})

        # 4. Create accounts using the bootstrap-configured accounts if possible
        self.ar_account = self.create_account("Accounts Receivable", "Receivable")
        self.income_account = self.create_account("Sales Revenue", "Income")
        self.expense_account = self.create_account("Cost of Goods Sold", "Expense")
        self.ap_account = self.create_account("Accounts Payable", "Payable")

        # 5. Create Customer, Supplier, Item
        if not frappe.db.exists("Customer", {"customer_name": "Test Customer"}):
            self.customer = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": "Test Customer",
            }).insert(ignore_permissions=True).name
        else:
            self.customer = frappe.db.get_value("Customer", {"customer_name": "Test Customer"}, "name")

        if not frappe.db.exists("Supplier", {"supplier_name": "Test Supplier"}):
            self.supplier = frappe.get_doc({
                "doctype": "Supplier",
                "supplier_name": "Test Supplier",
            }).insert(ignore_permissions=True).name
        else:
            self.supplier = frappe.db.get_value("Supplier", {"supplier_name": "Test Supplier"}, "name")

        if not frappe.db.exists("Item", "Test Item"):
            frappe.get_doc({
                "doctype": "Item",
                "item_code": "Test Item",
                "item_name": "Test Item",
                "rate": 100.0,
            }).insert(ignore_permissions=True)

    def create_account(self, name, account_type):
        fullname = f"{name} - {self.company_name}"
        if not frappe.db.exists("Account", fullname):
            doc = frappe.get_doc({
                "doctype": "Account",
                "account_name": name,
                "account_type": account_type,
                "company": self.company_name,
                "currency": "OMR",
            }).insert(ignore_permissions=True)
            return doc.name
        else:
            frappe.db.set_value("Account", fullname, "account_type", account_type)
        return fullname

    def test_net_budget_calculation(self):
        # Clean up any existing GL entries for this company to start fresh
        frappe.db.sql("DELETE FROM `tabGeneral Ledger Entry` WHERE company = %s", self.company_name)

        # Verify initial spend is 0
        initial_spend = get_cost_center_spend(self.company_name)
        self.assertEqual(initial_spend.get(self.cc.name, 0.0), 0.0)

        # 1. Create and submit a Sales Invoice
        si = frappe.get_doc({
            "doctype": "Sales Invoice",
            "customer": self.customer,
            "company": self.company_name,
            "posting_date": "2026-06-12",
            "due_date": "2026-07-12",
            "debit_to": self.ar_account,
            "income_account": self.income_account,
            "cost_center": self.cc.name,
            "items": [{
                "item_code": "Test Item",
                "qty": 1,
                "rate": 2500.0,
            }]
        }).insert(ignore_permissions=True)
        si.submit()

        # Net spend should be -2500 (credits from income offset spend)
        spend_after_invoice = get_cost_center_spend(self.company_name)
        self.assertEqual(spend_after_invoice.get(self.cc.name, 0.0), -2500.0)

        # 2. Create and submit a Purchase Invoice (Bill)
        pi = frappe.get_doc({
            "doctype": "Purchase Invoice",
            "supplier": self.supplier,
            "company": self.company_name,
            "posting_date": "2026-06-12",
            "due_date": "2026-07-12",
            "credit_to": self.ap_account,
            "expense_account": self.expense_account,
            "cost_center": self.cc.name,
            "items": [{
                "item_code": "Test Item",
                "qty": 1,
                "rate": 4000.0,
            }]
        }).insert(ignore_permissions=True)
        pi.submit()

        # Net spend should be 4000 (expense debit) - 2500 (revenue credit) = 1500
        spend_after_bill = get_cost_center_spend(self.company_name)
        self.assertEqual(spend_after_bill.get(self.cc.name, 0.0), 1500.0)

    def test_budget_enforcement(self):
        # Clean up any existing GL entries for this company to start fresh
        frappe.db.sql("DELETE FROM `tabGeneral Ledger Entry` WHERE company = %s", self.company_name)

        # Configure cost center budget and actions: budget = 10,000, action = Stop
        frappe.db.set_value("Cost Center", self.cc.name, {
            "budget": 10000.0,
            "budget_action": "Stop",
            "alert_pct": 80
        })

        # 1. Create a Purchase Invoice exceeding budget (12,000)
        pi = frappe.get_doc({
            "doctype": "Purchase Invoice",
            "supplier": self.supplier,
            "company": self.company_name,
            "posting_date": "2026-06-12",
            "due_date": "2026-07-12",
            "credit_to": self.ap_account,
            "expense_account": self.expense_account,
            "cost_center": self.cc.name,
            "items": [{
                "item_code": "Test Item",
                "qty": 1,
                "rate": 12000.0,
            }]
        }).insert(ignore_permissions=True)

        # Assert it raises ValidationError when exceeding budget on submit (action is Stop)
        self.assertRaises(frappe.ValidationError, pi.submit)

        # Reset docstatus back to 0 since the failed submit left docstatus=1 in the uncommitted DB transaction
        frappe.db.set_value("Purchase Invoice", pi.name, "docstatus", 0)
        frappe.clear_document_cache("Purchase Invoice", pi.name)

        # 2. Change budget action to "Warn" and verify it throws validation error initially
        frappe.db.set_value("Cost Center", self.cc.name, "budget_action", "Warn")
        frappe.clear_document_cache("Cost Center", self.cc.name)
        pi = frappe.get_doc("Purchase Invoice", pi.name)
        self.assertRaises(frappe.ValidationError, pi.submit)

        # Reset docstatus back to 0 again
        frappe.db.set_value("Purchase Invoice", pi.name, "docstatus", 0)
        frappe.clear_document_cache("Purchase Invoice", pi.name)

        # 3. Verify it allows submission with the ignore flag
        pi = frappe.get_doc("Purchase Invoice", pi.name)
        pi.flags.ignore_budget_warning = True
        pi.submit()
        
        self.assertEqual(pi.docstatus, 1)