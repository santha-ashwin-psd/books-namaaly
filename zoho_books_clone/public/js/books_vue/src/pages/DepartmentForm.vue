<template>
  <div class="modal-overlay">
    <div class="modal-card">
      <div class="modal-header">
        <h3 class="modal-title">{{ isEdit ? 'Edit Department' : 'New Department' }}</h3>
        <button class="modal-close" @click="$emit('close')">×</button>
      </div>
      <div class="modal-body">
        <form @submit.prevent="onSave">
          <div class="form-group">
            <label for="department_name">Department Name <span class="nim-req">*</span></label>
            <input type="text" id="department_name" v-model="form.department_name" required>
          </div>
          <div class="form-group">
            <label for="description">Description</label>
            <textarea id="description" v-model="form.description" rows="3" placeholder="Brief description of this department"></textarea>
          </div>
          <div class="form-actions">
            <button type="button" class="btn-secondary" @click="$emit('close')">Cancel</button>
            <button type="submit" class="btn-primary" :disabled="saving || !(isEdit ? $canEdit('inventory') : $canCreate('inventory'))">{{ saving ? 'Saving…' : 'Save' }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, defineProps, defineEmits } from 'vue';

const props = defineProps({
  isEdit: Boolean,
  department: Object,
});

const emit = defineEmits(['close', 'save']);

const form = ref({
  department_name: '',
  description: '',
});

if (props.isEdit && props.department) {
  form.value = { ...props.department };
}

const saving = ref(false);

async function onSave() {
  saving.value = true;
  try {
    emit('save', { ...form.value });
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}
.modal-card {
  background: white;
  border-radius: 10px;
  width: 500px;
  max-width: 98%;
}
.modal-header {
  padding: 16px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.modal-title {
  font-size: 17px;
  font-weight: 700;
}
.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #6b7280;
}
.modal-body {
  padding: 16px;
}
form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.form-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.form-group label {
  font-size: 12.5px;
  font-weight: 600;
  color: #374151;
}
.form-group input,
.form-group textarea,
.form-group select {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.form-group input:focus,
.form-group textarea:focus,
.form-group select:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37,99,235,0.08);
}
.form-group textarea {
  resize: vertical;
  min-height: 68px;
}
.nim-req {
  color: #dc2626;
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px solid #e5e7eb;
  margin-top: 4px;
}
.btn-secondary {
  padding: 8px 16px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}
.btn-secondary:hover { background: #f9fafb; }
.btn-primary {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  background: #2563eb;
  color: white;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
}
.btn-primary:hover { background: #1d4ed8; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
</style>