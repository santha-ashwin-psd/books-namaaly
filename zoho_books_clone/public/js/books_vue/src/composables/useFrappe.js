// composables/useFrappe.js
// Thin wrapper around the app's own apiGET/apiList for use in Vue components.
// NOTE: frappe.call is NOT available in this standalone Vue bundle — use client.js instead.

import { ref } from "vue";
import { apiGET, apiList } from "../api/client.js";

/**
 * Call a whitelisted Python method.
 * Returns { data, loading, error, execute }.
 */
export function useFrappeCall(method, args = {}) {
  const data    = ref(null);
  const loading = ref(false);
  const error   = ref(null);

  async function execute(overrideArgs = {}) {
    loading.value = true;
    error.value   = null;
    try {
      const res = await apiGET(method, { ...args, ...overrideArgs });
      data.value = res;
    } catch (e) {
      error.value = e;
      console.error(`[useFrappeCall] ${method}`, e);
    } finally {
      loading.value = false;
    }
    return data.value;
  }

  return { data, loading, error, execute };
}

/**
 * Fetch a list of documents.
 */
export function useFrappeList(doctype, opts = {}) {
  const list    = ref([]);
  const loading = ref(false);
  const error   = ref(null);

  async function fetch(overrideOpts = {}) {
    loading.value = true;
    error.value   = null;
    try {
      list.value = await apiList(doctype, { ...opts, ...overrideOpts });
    } catch (e) {
      error.value = e;
    } finally {
      loading.value = false;
    }
    return list.value;
  }

  return { list, loading, error, fetch };
}

/** Format a number as OMR currency */
export function formatCurrency(val, currency = "OMR") {
  if (val == null) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(val);
}

/** Format ISO date to readable string */
export function formatDate(val) {
  if (!val) return "—";
  return new Date(val).toLocaleDateString("en-IN", {
    day: "2-digit", month: "short", year: "numeric",
  });
}