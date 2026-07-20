<template>
  <Teleport to="body">
    <div class="inv-drawer-bg" @click.self="close">
      <div class="inv-drawer-panel is-add">

        <!-- Header -->
        <div class="inv-dh">
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
            <div class="inv-dh-title">{{ isEdit ? 'Edit Maintenance Log' : 'New Maintenance Log' }}</div>
            <span v-if="!isEdit" class="add-status-badge">Draft</span>
          </div>
          <button class="inv-dclose" @click="close" title="Close"><span v-html="icon('x',16)"></span></button>
        </div>

        <!-- Body -->
        <div class="inv-dbody">

          <!-- Maintenance Details -->
          <div class="add-card">
            <div class="add-card-header" @click="collapsed.details = !collapsed.details">
              <div class="add-card-title">
                <span class="add-card-title-icon"><span v-html="icon('gear',16)"></span></span>
                Maintenance Details
              </div>
              <span class="add-card-chevron" :class="{collapsed:collapsed.details}"><span v-html="icon('chevD',14)"></span></span>
            </div>
            <div class="add-card-body" :class="{collapsed:collapsed.details}">
              <div class="inv-fg inv-fg2">
                <div>
                  <label class="inv-lbl">Asset <span class="inv-req">*</span></label>
                  <SearchableSelect
                    v-model="form.asset"
                    :options="assetOptions"
                    placeholder="Select asset"
                    createable
                    create-doctype="Asset"
                  />
                </div>
                <div>
                  <label class="inv-lbl">Maintenance Date <span class="inv-req">*</span></label>
                  <input type="date" v-model="form.maintenance_date" class="inv-fi" required/>
                </div>
                <div>
                  <label class="inv-lbl">Technician <span class="inv-req">*</span></label>
                  <input type="text" v-model="form.technician" class="inv-fi" required placeholder="Technician name"/>
                </div>
                <div>
                  <label class="inv-lbl">Cost <span class="inv-req">*</span></label>
                  <input type="number" step="0.01" v-model="form.cost" class="inv-fi" required placeholder="0.00"/>
                </div>
                <div>
                  <label class="inv-lbl">Status <span class="inv-req">*</span></label>
                  <select v-model="form.status" class="inv-fi" required>
                    <option v-for="s in statuses" :key="s" :value="s">{{ s }}</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          <!-- Work Done -->
          <div class="add-card">
            <div class="add-card-header" @click="collapsed.work = !collapsed.work">
              <div class="add-card-title">
                <span class="add-card-title-icon"><span v-html="icon('edit',16)"></span></span>
                Work Done
              </div>
              <span class="add-card-chevron" :class="{collapsed:collapsed.work}"><span v-html="icon('chevD',14)"></span></span>
            </div>
            <div class="add-card-body" :class="{collapsed:collapsed.work}">
              <div class="inv-fg">
                <div style="grid-column:1 / -1">
                  <label class="inv-lbl">Description</label>
                  <textarea v-model="form.work_done" rows="4" class="inv-fi" placeholder="Describe the work performed..."></textarea>
                </div>
              </div>
            </div>
          </div>

        </div>

        <!-- Footer -->
        <div class="inv-dfooter">
          <button type="button" class="nim-btn" style="border:1px solid #e5e7eb" @click="close">Cancel</button>
          <button type="button" class="nim-btn nim-btn-primary" :disabled="saving" @click="onSave">
            <span v-html="icon('save',13)"></span> {{ saving ? 'Saving…' : (isEdit ? 'Update Log' : 'Save Log') }}
          </button>
        </div>

      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { icon } from "../utils/icons.js";
import { apiList } from "../api/client.js";
import SearchableSelect from "../components/SearchableSelect.vue";

const props = defineProps({
  isEdit: Boolean,
  log: Object,
});

const emit = defineEmits(['close', 'save']);

const statuses = ["Completed", "Pending", "Cancelled"];
const assetOptions = ref([]);
const saving = ref(false);
const collapsed = reactive({ details: false, work: false });

const form = reactive({
  name: "",
  asset: "",
  maintenance_date: "",
  technician: "",
  cost: "",
  status: "Pending",
  work_done: "",
});

if (props.isEdit && props.log) {
  Object.assign(form, props.log);
  if (!form.status) form.status = "Pending";
}

async function loadAssets() {
  try {
    const rows = await apiList("Asset", {
      fields: ["name", "asset_name"],
      filters: [["docstatus", "<", 2]],
      limit: 500,
    });
    assetOptions.value = (rows || []).map(r => ({
      value: r.name,
      label: r.asset_name ? `${r.asset_name} (${r.name})` : r.name,
    }));
  } catch (e) {
    assetOptions.value = [];
  }
}

onMounted(loadAssets);

function close() {
  emit('close');
}

function onSave() {
  if (!form.asset || !form.maintenance_date || !form.technician || form.cost === "" || !form.status) {
    return;
  }
  saving.value = true;
  try {
    const payload = { ...form };
    if (!props.isEdit) delete payload.name;
    emit('save', payload);
  } finally {
    saving.value = false;
  }
}
</script>