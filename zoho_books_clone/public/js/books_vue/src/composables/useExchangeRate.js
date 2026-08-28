import { ref } from "vue";

// OMR-only: exchange rate is always 1. Stub retained so existing imports don't break.
export function useExchangeRate() {
  const rateLoading = ref(false);
  const rateSource  = ref("identity");
  const rateDate    = ref("");

  async function fetchRate() { return 1; }
  function sourceLabel() { return ""; }

  return { fetchRate, rateLoading, rateSource, rateDate, sourceLabel };
}