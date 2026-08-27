<template>
  <Teleport to="body">
    <div v-if="state.open" class="ccd-backdrop" @click.self="_cancel">
      <div class="ccd-dialog">
        <div class="ccd-header">
          <span class="ccd-title">{{ state.title }}</span>
          <button class="ccd-close" @click="_cancel" :disabled="state.loading">✕</button>
        </div>
        <div class="ccd-body">
          <p v-if="state.message" class="ccd-msg">{{ state.message }}</p>
          <div v-if="state.links.length" class="ccd-links">
            <div class="ccd-links-head">
              <span>Linked</span><span>Mode / Type</span><span>Date</span><span style="text-align:right">Amount</span>
            </div>
            <div v-for="p in state.links" :key="p.name" class="ccd-links-row">
              <span >{{ p.name }}</span>
              <span>{{ p.mode || p.type || "—" }}</span>
              <span style="color:#6b7280">{{ p.date || "—" }}</span>
              <span style="text-align:right;font-weight:700;color:#059669">{{ fmt(p.amount) }}</span>
            </div>
          </div>
          <p v-if="state.links.length" class="ccd-warn">
            The {{ state.links.length }} record(s) above will also be cancelled. This cannot be undone.
          </p>
        </div>
        <div class="ccd-footer">
          <button class="ccd-btn ccd-btn-ghost" @click="_cancel" :disabled="state.loading">Keep</button>
          <button
            class="ccd-btn"
            :class="state.actionStyle === 'danger' ? 'ccd-btn-danger' : 'ccd-btn-primary'"
            :disabled="state.loading"
            @click="_ok"
          >
            {{ state.loading ? "Working…" : state.actionLabel }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { useConfirmCascade } from "../composables/useConfirmCascade.js";
const { state, _ok, _cancel } = useConfirmCascade();

function fmt(v) {
  if (v == null) return "—";
  return "OMR " + Number(v).toLocaleString("en-OM", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
}
</script>

<style scoped>
.ccd-backdrop {
  position: fixed; inset: 0; background: rgba(15,23,42,.5);
  z-index: 10000; display: flex; align-items: center; justify-content: center;
}
.ccd-dialog {
  background: #fff; border-radius: 12px; width: 480px; max-width: 96vw;
  box-shadow: 0 12px 40px rgba(0,0,0,.2);
  animation: ccd-in .2s cubic-bezier(.34,1.56,.64,1);
}
@keyframes ccd-in { from { opacity: 0; transform: scale(.96) translateY(8px); } to { opacity: 1; transform: none; } }
.ccd-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px; border-bottom: 1px solid #e5e7eb;
}
.ccd-title { font-size: 15px; font-weight: 700; color: #111827; }
.ccd-close {
  background: transparent; border: none; cursor: pointer; font-size: 16px; color: #6b7280;
  width: 28px; height: 28px; border-radius: 6px;
}
.ccd-close:hover { background: #f3f4f6; color: #111827; }
.ccd-close:disabled { opacity: .4; cursor: not-allowed; }
.ccd-body { padding: 16px 18px; display: flex; flex-direction: column; gap: 12px; }
.ccd-msg { font-size: 13px; color: #374151; margin: 0; line-height: 1.5; }
.ccd-links {
  border: 1px solid #fca5a5; border-radius: 8px; overflow: hidden;
}
.ccd-links-head {
  background: #fef2f2; padding: 8px 12px; font-size: 11px;
  font-weight: 700; text-transform: uppercase; letter-spacing: .04em;
  color: #b91c1c; display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 8px;
}
.ccd-links-row {
  padding: 8px 12px; font-size: 12.5px; display: grid;
  grid-template-columns: 1fr 1fr 1fr 1fr; gap: 8px;
  border-top: 1px solid #fee2e2; align-items: center;
}
.ccd-warn { font-size: 12px; color: #b91c1c; margin: 0; }
.ccd-footer {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 12px 18px; border-top: 1px solid #e5e7eb;
}
.ccd-btn {
  font: inherit; font-size: 13px; padding: 8px 16px; border-radius: 8px;
  border: 1px solid transparent; cursor: pointer; font-weight: 600;
}
.ccd-btn:disabled { opacity: .5; cursor: not-allowed; }
.ccd-btn-ghost { background: #fff; border-color: #e5e7eb; color: #374151; }
.ccd-btn-ghost:hover:not(:disabled) { background: #f9fafb; }
.ccd-btn-danger { background: #dc2626; color: #fff; border-color: #dc2626; }
.ccd-btn-danger:hover:not(:disabled) { background: #b91c1c; }
.ccd-btn-primary { background: #2563eb; color: #fff; border-color: #2563eb; }
.ccd-btn-primary:hover:not(:disabled) { background: #1d4ed8; }
</style>
