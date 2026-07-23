// Generic payment recording dialog. Works for both customer-side (Invoice) and
// vendor-side (Bill) by passing a different sendEndpoint. Also supports a
// MULTI-INVOICE mode: pass `multi: true` + an `invoices` array to let the
// user apply one payment across several of a customer's open invoices.
//
// Single-invoice usage:
//   const { openPayment } = usePaymentDialog();
//   const paymentName = await openPayment({
//     direction: "receive",                // "receive" (from customer) or "pay" (to vendor)
//     doctype: "Sales Invoice",
//     name: "INV-001",
//     party: "Acme Corp",
//     partyLabel: "Acme Corp",
//     balance: 5000,
//     getDefaultsEndpoint: "zoho_books_clone.api.books_data.get_payment_defaults",
//     sendEndpoint: "zoho_books_clone.api.books_data.record_payment",
//     paramKey: "invoice_name",
//   });
//
// Multi-invoice usage:
//   const { openPayment } = usePaymentDialog();
//   const paymentName = await openPayment({
//     multi: true,
//     direction: "receive",
//     party: "CUST-0001",                  // customer id
//     partyLabel: "Acme Corp",
//     invoices: [{ name, due_date, outstanding_amount }, ...],  // pre-fetched, or omit and pass invoicesEndpoint
//     invoicesEndpoint: "zoho_books_clone.api.books_data.get_customer_outstanding_invoices",
//     getDefaultsEndpoint: "zoho_books_clone.api.books_data.get_payment_defaults",
//     sendEndpoint: "zoho_books_clone.api.books_data.record_payment_multi",
//   });

import { reactive } from "vue";

const defaults = {
  open: false,
  multi: false,
  direction: "receive",
  doctype: "",
  name: "",
  party: "",
  partyLabel: "",
  balance: 0,
  invoices: null,           // pre-fetched invoice list, multi mode only
  invoicesEndpoint: "",     // used to fetch invoices if `invoices` not passed
  getDefaultsEndpoint: "",
  sendEndpoint: "",
  paramKey: "name",
  resolve: null,
};

const state = reactive({ ...defaults });

export function usePaymentDialog() {
  function openPayment(opts) {
    return new Promise((resolve) => {
      Object.assign(state, { ...defaults, ...opts, open: true, resolve });
    });
  }
  function complete(paymentName) {
    state.open = false;
    const r = state.resolve; state.resolve = null;
    r?.(paymentName);
  }
  function cancel() {
    state.open = false;
    const r = state.resolve; state.resolve = null;
    r?.(null);
  }
  return { state, openPayment, complete, cancel };
}