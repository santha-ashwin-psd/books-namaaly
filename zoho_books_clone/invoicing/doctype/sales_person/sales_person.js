frappe.ui.form.on("Sales Person", {
  setup(frm) {
    frm.set_query("reports_to", () => ({
      filters: { name: ["!=", frm.doc.name] }
    }));
  },

  refresh(frm) {
    if (!frm.is_new()) {
      frm.add_custom_button(__("View Invoices"), () =>
        frappe.set_route("List", "Sales Invoice", { sales_person: frm.doc.name })
      );
      frm.add_custom_button(__("New Invoice"), () => {
        frappe.new_doc("Sales Invoice", { sales_person: frm.doc.name });
      });
    }
  },

  sales_person_name(frm) {
    // Auto-suggest naming series won't collide
  },
});