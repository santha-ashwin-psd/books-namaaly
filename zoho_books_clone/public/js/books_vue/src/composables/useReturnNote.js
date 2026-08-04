// Generic Credit Note / Debit Note creation dialog.
// Pre-fills items from the parent invoice/bill, editable qty per line.
//
// Usage:
//   const { openReturnNote } = useReturnNote();
//   const result = await openReturnNote({
//     kind: "credit",                       // "credit" or "debit"
//     parentName: "INV-001",                // invoice/bill name
//     party: "Acme Corp",                   // customer/supplier
//     items: [{ item_code, item_name, qty, rate, description }, ...],
//     invoiceTotal: 1000,                    // parent invoice/bill's grand_total
//                                             // (NOT outstanding_amount — the CN/DN
//                                             // cap is against remaining claimable
//                                             // value, independent of payment status)
//     existingEndpoint: "zoho_books_clone.api.docs.get_credit_notes",
//     createEndpoint: "zoho_books_clone.api.docs.create_credit_note",
//     paramKey: "invoice_name",             // request param key for fetching existing notes
//     partyKey: "customer",                 // request param key for the party
//     parentKey: "against_invoice",         // request param key for parent doc
//   });
//   if (result) { /* result = { noteName: "CN-XXX" } */ }

import { reactive } from "vue";

const state = reactive({
  open: false,
  kind: "credit",
  parentName: "",
  party: "",
  items: [],
  taxes: [],
  invoiceTotal: 0,
  existingEndpoint: "",
  createEndpoint: "",
  paramKey: "name",
  partyKey: "customer",
  parentKey: "against_invoice",
  resolve: null,
});

export function useReturnNote() {
  function openReturnNote(opts) {
    return new Promise((resolve) => {
      Object.assign(state, {
        open: true,
        kind: "credit",
        parentName: "",
        party: "",
        items: [],
        taxes: [],
        invoiceTotal: 0,
        existingEndpoint: "",
        createEndpoint: "",
        paramKey: "name",
        partyKey: "customer",
        parentKey: "against_invoice",
        ...opts,
        resolve,
      });
    });
  }
  function complete(result) {
    state.open = false;
    const r = state.resolve; state.resolve = null;
    r?.(result);
  }
  function cancel() {
    state.open = false;
    const r = state.resolve; state.resolve = null;
    r?.(null);
  }
  return { state, openReturnNote, complete, cancel };
}