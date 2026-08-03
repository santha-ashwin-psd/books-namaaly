<template>
  <Modal
    :show="state.open"
    :title="state.title"
    width="420px"
    @close="_cancel"
  >
    <div v-if="state.body" class="bv-confirm-body" v-html="state.body"></div>
    <template #footer>
      <button v-if="!state.hideCancel" class="nim-btn" @click="_cancel">{{ state.cancelLabel }}</button>
      <button
        class="nim-btn"
        :class="state.okStyle === 'danger' ? 'nim-btn-danger' : 'nim-btn-primary'"
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
</style>