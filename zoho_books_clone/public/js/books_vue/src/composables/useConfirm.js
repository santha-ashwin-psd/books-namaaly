// Promise-returning confirm dialog. Mounted by AppShell via <ConfirmHost />;
// callers do `if (await confirm({title, body})) ...`.

import { reactive } from "vue";

const state = reactive({
  open:        false,
  title:       "",
  body:        "",
  okLabel:     "Confirm",
  cancelLabel: "Cancel",
  okStyle:     "danger",     // "danger" | "primary"
  hideCancel:  false,        // true -> single-button "OK" alert dialog
  resolve:     null,
});

export function useConfirm() {
  function confirm({ title = "Are you sure?", body = "", okLabel = "Confirm", cancelLabel = "Cancel", okStyle = "danger", hideCancel = false } = {}) {
    return new Promise((resolve) => {
      state.title       = title;
      state.body        = body;
      state.okLabel     = okLabel;
      state.cancelLabel = cancelLabel;
      state.okStyle     = okStyle;
      state.hideCancel  = hideCancel;
      state.resolve     = resolve;
      state.open        = true;
    });
  }

  function _ok()     { state.open = false; state.resolve?.(true);  state.resolve = null; }
  function _cancel() { state.open = false; state.resolve?.(false); state.resolve = null; }

  return { state, confirm, _ok, _cancel };
}