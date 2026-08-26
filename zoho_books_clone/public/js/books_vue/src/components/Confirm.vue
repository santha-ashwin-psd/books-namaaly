<template>
  <Modal
    :show="state.open"
    :width="state.width"
    @close="_cancel"
  >
    <template v-if="state.icon" #header>
      <div class="bv-confirm-header">
        <span class="bv-confirm-icon" :class="`bv-confirm-icon-${state.icon}`">!</span>
        <h3>{{ state.title }}</h3>
      </div>
      <button class="nim-dialog-close" @click="_cancel">✕</button>
    </template>
    <template v-else #header>
      <h3>{{ state.title }}</h3>
      <button class="nim-dialog-close" @click="_cancel">✕</button>
    </template>

    <div v-if="state.body" class="bv-confirm-body" v-html="state.body"></div>

    <div v-if="state.items && state.items.length" class="bv-confirm-cards">
      <div v-for="(item, idx) in state.items" :key="idx" class="bv-confirm-card">
        <div class="bv-confirm-card-top">
          <span class="bv-confirm-card-title">{{ item.title }}</span>
          <span
            v-if="item.badge"
            class="bv-confirm-badge"
            :class="`bv-confirm-badge-${item.badge.tone || 'default'}`"
          >{{ item.badge.label }}</span>
        </div>
        <div v-if="item.fields && item.fields.length" class="bv-confirm-card-fields">
          <div v-for="(f, fi) in item.fields" :key="fi" class="bv-confirm-field">
            <div class="bv-confirm-field-label">{{ f.label }}</div>
            <div class="bv-confirm-field-value" :class="f.tone ? `bv-confirm-field-value-${f.tone}` : ''">{{ f.value }}</div>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <button v-if="!state.hideCancel" class="nim-btn" @click="_cancel">{{ state.cancelLabel }}</button>
      <button
        class="nim-btn"
        :class="state.okStyle === 'danger' ? 'nim-btn-danger' : (state.icon ? 'nim-btn-dark' : 'nim-btn-primary')"
        @click="_ok"
      >{{ state.okLabel }}</button>
    </template>
  </Modal>
</template>

<script setup>
import Modal from "./Modal.vue";
import { useConfirm } from "../composables/useConfirm.js";
const { state, _ok, _cancel } = useConfirm();
</script>

<style>
.bv-confirm-body { font-size: 13px; color: #374151; line-height: 1.5; padding: 4px 0; }
.bv-confirm-body p { margin: 0 0 10px; }
.bv-confirm-body p:last-child { margin-bottom: 0; }
.bv-confirm-list {
  margin: 2px 0 12px;
  padding: 8px 10px 8px 26px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  list-style: disc;
}
.bv-confirm-list li {
  margin: 4px 0;
  word-break: break-word;
}

/* ── Header with a colored icon badge (used for alert-style dialogs) ── */
.bv-confirm-header { display: flex; align-items: center; gap: 10px; }
.bv-confirm-header h3 { font-size: 15px; font-weight: 700; color: #111827; margin: 0; }
.bv-confirm-icon {
  flex-shrink: 0;
  width: 26px; height: 26px;
  border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 800; color: #fff;
  font-style: normal;
}
.bv-confirm-icon-warning { background: #dc2626; }

/* ── Structured item cards (e.g. per-item stock shortfall) ── */
.bv-confirm-cards { display: flex; flex-direction: column; gap: 10px; margin: 4px 0 8px; }
.bv-confirm-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px 14px;
  background: #fff;
}
.bv-confirm-card-top { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.bv-confirm-card-title { font-size: 13.5px; font-weight: 700; color: #111827; word-break: break-word; }
.bv-confirm-badge {
  flex-shrink: 0;
  font-size: 11px; font-weight: 700;
  padding: 2px 9px;
  border-radius: 999px;
  text-transform: capitalize;
}
.bv-confirm-badge-danger { background: #fee2e2; color: #dc2626; }
.bv-confirm-badge-default { background: #f3f4f6; color: #374151; }
.bv-confirm-card-fields { display: flex; gap: 28px; margin-top: 10px; }
.bv-confirm-field-label {
  font-size: 10.5px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase;
  color: #9ca3af; margin-bottom: 3px;
}
.bv-confirm-field-value { font-size: 14px; font-weight: 700; color: #111827; }
.bv-confirm-field-value-danger { color: #dc2626; }

.nim-btn-dark { background: #111827; border-color: #111827; color: #fff; }
.nim-btn-dark:hover:not(:disabled) { background: #1f2937; border-color: #1f2937; color: #fff; }
</style>