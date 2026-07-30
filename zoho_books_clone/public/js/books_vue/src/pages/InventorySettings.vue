<template>
<div class="list-page">

  <!-- ════════════════════════════════════════════
       TOOLBAR — tab strip + search + new button
       ════════════════════════════════════════════ -->
  <div class="sales-toolbar">
    <div class="is-tabs">
      <button
        v-for="t in TABS" :key="t.key"
        class="sales-pill" :class="{ active: tab === t.key }"
        @click="switchTab(t.key)"
      >
        <span v-html="icon(t.icon, 13)" style="vertical-align:-2px;margin-right:4px"></span>
        {{ t.label }}
        <span class="sales-pill-count">{{ rowsFor(t.key).length }}</span>
      </button>
    </div>

    <div class="sales-search">
      <span v-html="icon('search', 14)"></span>
      <input v-model="search" class="sales-search-input" :placeholder="'Search ' + activeTabDef.label.toLowerCase() + '…'" />
    </div>

    <div style="flex:1"></div>

    <div class="sales-actions">
      <button class="sales-btn-ghost" @click="load" :disabled="loading" title="Refresh">
        <span v-html="icon('refresh', 13)"></span>
      </button>
      <button class="sales-btn-primary" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''" @click="openAdd">
        <span v-html="icon('plus', 13)"></span> New {{ activeTabDef.singular }}
      </button>
    </div>
  </div>

  <div class="is-hint">
    <span v-html="icon('info', 14)" style="flex-shrink:0;margin-top:1px"></span>
    <span>{{ activeTabDef.hint }}</span>
  </div>

  <!-- ════════════════════════════════════════════
       LIST
       ════════════════════════════════════════════ -->
  <div v-if="loading" class="is-empty-card">Loading…</div>

  <div v-else-if="!filteredRows.length" class="is-empty-card">
    <div style="font-size:32px;margin-bottom:8px">{{ activeTabDef.emptyIcon }}</div>
    <div style="font-size:14px;font-weight:600;color:#374151;margin-bottom:4px">
      {{ search ? 'No matches found' : activeTabDef.emptyTitle }}
    </div>
    <div style="font-size:12.5px;color:#9ca3af">{{ activeTabDef.emptySub }}</div>
    <button v-if="!search" class="sales-btn-primary" style="margin-top:14px" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''" @click="openAdd">
      <span v-html="icon('plus', 13)"></span> New {{ activeTabDef.singular }}
    </button>
  </div>

  <div v-else class="is-grid">
    <div v-for="row in filteredRows" :key="row.name" class="is-card">
      <div class="is-card-top">
        <div class="is-card-icon" v-html="icon(activeTabDef.icon, 18)"></div>
        <div class="is-card-actions">
          <button class="is-card-btn" :disabled="!$canEdit('inventory')" :title="!$canEdit('inventory') ? 'Read-only access' : 'Edit'" @click="openEdit(row)">
            <span v-html="icon('edit', 12)"></span>
          </button>
          <button class="is-card-btn is-card-btn--danger" :disabled="!$canDelete('inventory')" :title="!$canDelete('inventory') ? 'Not permitted' : 'Delete'" @click="askDelete(row)">
            <span v-html="icon('trash', 12)"></span>
          </button>
        </div>
      </div>

      <div class="is-card-name">{{ row.name }}</div>

      <template v-if="tab === 'territory'">
        <div class="is-card-sub">
          <span v-if="row.parent_territory">
            <span v-html="icon('chevR', 10)" style="opacity:.5;vertical-align:-1px"></span>
            {{ row.parent_territory }}
          </span>
          <span v-else class="text-muted">Top level</span>
        </div>
        <div class="is-card-bottom">
          <span class="inv-status-badge" :class="row.is_group ? 'status-draft' : 'status-paid'">
            {{ row.is_group ? 'Group' : 'Leaf' }}
          </span>
        </div>
      </template>

      <template v-else>
        <div class="is-card-sub">{{ row.description || 'No description' }}</div>
        <div class="is-card-bottom">
          <span class="inv-status-badge" :class="isActive(row) ? 'status-paid' : 'status-draft'">
            {{ isActive(row) ? 'Active' : 'Inactive' }}
          </span>
        </div>
      </template>
    </div>
  </div>

  <!-- ════════════════════════════════════════════
       ADD / EDIT MODAL
       ════════════════════════════════════════════ -->
  <Modal :show="showModal" :title="(mode === 'add' ? 'New ' : 'Edit ') + activeTabDef.singular" width="480px" @close="showModal = false">
    <div class="is-form">

      <div class="is-field">
        <label class="is-label">{{ activeTabDef.nameLabel }} <span style="color:#dc2626">*</span></label>
        <input class="is-input" v-model="form.name" :placeholder="activeTabDef.namePlaceholder" />
      </div>

      <div v-if="tab !== 'territory'" class="is-field">
        <label class="is-label">Description</label>
        <textarea class="is-input" rows="2" v-model="form.description" placeholder="Optional notes"></textarea>
      </div>

      <div v-if="tab === 'territory'" class="is-field">
        <label class="is-label">Parent Territory</label>
        <select class="is-input" v-model="form.parent_territory">
          <option value="">— None (top level) —</option>
          <option v-for="t in territories.filter(t => t.name !== originalName)" :key="t.name" :value="t.name">{{ t.name }}</option>
        </select>
      </div>

      <div class="is-toggle-row">
        <label class="is-toggle-label">
          <span class="is-toggle-wrap">
            <input type="checkbox" class="is-toggle-input" v-model="form.activeFlag" />
            <span class="is-toggle-track"><span class="is-toggle-thumb"></span></span>
          </span>
          <span class="is-toggle-text">
            <span class="is-toggle-title">{{ tab === 'territory' ? 'Is Group' : 'Active' }}</span>
            <span class="is-toggle-sub">
              {{ tab === 'territory'
                ? 'A group can contain other territories beneath it.'
                : 'Inactive ' + activeTabDef.label.toLowerCase() + ' won&#8217;t appear in dropdowns for new records.' }}
            </span>
          </span>
        </label>
      </div>
    </div>

    <template #footer>
      <button class="nim-btn" @click="showModal = false">Cancel</button>
      <button class="nim-btn nim-btn-primary" @click="save" :disabled="saving || !(mode === 'edit' ? $canEdit('inventory') : $canCreate('inventory'))">
        {{ saving ? 'Saving…' : 'Save ' + activeTabDef.singular }}
      </button>
    </template>
  </Modal>

</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { apiList, apiSave, apiDelete, apiPOST } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { useConfirm } from "../composables/useConfirm.js";
import { icon } from "../utils/icons.js";
import Modal from "../components/Modal.vue";

const { toast }   = useToast();
const { confirm } = useConfirm();

const TABS = [
  {
    key: "uom", label: "Units of Measure", singular: "UOM", icon: "hash",
    doctype: "UOM", nameField: "uom_name", activeField: "enabled", activeMeaning: "enabled",
    nameLabel: "UOM Name", namePlaceholder: "e.g. Nos, Kg, Litre, Box",
    hint: "Units of Measure define how items are counted or sold (Nos, Kg, Litre…). They appear in the Default UOM dropdown on every item.",
    emptyIcon: "📏", emptyTitle: "No units of measure yet", emptySub: "Create units like Nos, Kg, Litre or Box",
  },
  {
    key: "brand", label: "Brands", singular: "Brand", icon: "building",
    doctype: "Brand", nameField: "brand_name", activeField: "disabled", activeMeaning: "disabled_inverted",
    nameLabel: "Brand Name", namePlaceholder: "e.g. Himalaya, Patanjali",
    hint: "Brands let you group items by manufacturer or label. They appear on the Item master and can be used to filter and report by brand.",
    emptyIcon: "🏷️", emptyTitle: "No brands yet", emptySub: "Create brands to tag and filter items by manufacturer",
  },
  {
    key: "territory", label: "Territories", singular: "Territory", icon: "org",
    doctype: "Territory", nameField: "territory_name", activeField: "is_group", activeMeaning: "is_group",
    nameLabel: "Territory Name", namePlaceholder: "e.g. South India, Tamil Nadu, Export",
    hint: "Territories define sales regions. They appear in the Territory dropdown on Customers and can be nested under a parent territory.",
    emptyIcon: "🗺️", emptyTitle: "No territories yet", emptySub: "Create territories like North Zone, South Zone or Export",
  },
];

const tab     = ref("uom");
const search  = ref("");
const loading = ref(false);
const saving  = ref(false);

const uoms       = ref([]);
const brands     = ref([]);
const territories = ref([]);

const showModal   = ref(false);
const mode        = ref("add");      // 'add' | 'edit'
const originalName = ref("");
const form = reactive({
  name: "", description: "", parent_territory: "", activeFlag: true,
});

const activeTabDef = computed(() => TABS.find(t => t.key === tab.value));

function rowsFor(key) {
  if (key === "uom") return uoms.value;
  if (key === "brand") return brands.value;
  return territories.value;
}

const filteredRows = computed(() => {
  const rows = rowsFor(tab.value);
  const q = search.value.trim().toLowerCase();
  if (!q) return rows;
  return rows.filter(r =>
    (r.name || "").toLowerCase().includes(q) ||
    (r.description || "").toLowerCase().includes(q) ||
    (r.parent_territory || "").toLowerCase().includes(q)
  );
});

function isActive(row) {
  const def = activeTabDef.value;
  if (def.activeMeaning === "enabled")          return !!row.enabled;
  if (def.activeMeaning === "disabled_inverted") return !row.disabled;
  if (def.activeMeaning === "is_group")          return !!row.is_group;
  return true;
}

function switchTab(key) {
  tab.value = key;
  search.value = "";
}

async function load() {
  loading.value = true;
  try {
    const [u, b, t] = await Promise.all([
      apiList("UOM",      { fields: ["name", "uom_name", "description", "enabled"],            order: "uom_name asc",      limit: 500 }),
      apiList("Brand",    { fields: ["name", "brand_name", "description", "disabled"],          order: "brand_name asc",   limit: 500 }),
      apiList("Territory",{ fields: ["name", "territory_name", "parent_territory", "is_group"], order: "territory_name asc", limit: 500 }),
    ]);
    uoms.value = u || [];
    brands.value = b || [];
    territories.value = t || [];
  } catch (e) {
    toast("Could not load inventory settings: " + e.message, "error");
  }
  loading.value = false;
}

function openAdd() {
  mode.value = "add";
  originalName.value = "";
  Object.assign(form, { name: "", description: "", parent_territory: "", activeFlag: tab.value !== "territory" });
  showModal.value = true;
}

function openEdit(row) {
  mode.value = "edit";
  originalName.value = row.name;
  Object.assign(form, {
    name: row.name,
    description: row.description || "",
    parent_territory: row.parent_territory || "",
    activeFlag: isActive(row),
  });
  showModal.value = true;
}

async function save() {
  const def = activeTabDef.value;
  const newName = form.name.trim();
  if (!newName) { toast(def.nameLabel + " is required", "error"); return; }

  saving.value = true;
  try {
    const isEdit = mode.value === "edit";
    const nameChanged = isEdit && newName !== originalName.value;

    if (nameChanged) {
      await apiPOST("frappe.client.rename_doc", {
        doctype: def.doctype,
        old_name: originalName.value,
        new_name: newName,
        merge: 0,
      });
    }

    const doc = { doctype: def.doctype, name: newName, [def.nameField]: newName };

    if (tab.value === "territory") {
      doc.parent_territory = form.parent_territory || "";
      doc.is_group = form.activeFlag ? 1 : 0;
    } else {
      doc.description = form.description || "";
      if (def.activeMeaning === "enabled")          doc.enabled  = form.activeFlag ? 1 : 0;
      if (def.activeMeaning === "disabled_inverted") doc.disabled = form.activeFlag ? 0 : 1;
    }

    await apiSave(doc);
    toast(def.singular + (isEdit ? " updated" : " created"));
    showModal.value = false;
    load();
  } catch (e) {
    toast(e.message, "error");
  }
  saving.value = false;
}

async function askDelete(row) {
  const def = activeTabDef.value;
  const ok = await confirm({
    title: "Delete " + def.singular + "?",
    body: `Delete "${row.name}"? This can&#8217;t be undone. If it&#8217;s used on existing records, deletion will be blocked.`,
    okLabel: "Delete",
    okStyle: "danger",
  });
  if (!ok) return;
  try {
    await apiDelete(def.doctype, row.name);
    toast(def.singular + " deleted");
    load();
  } catch (e) {
    toast(e.message, "error");
  }
}

onMounted(load);
</script>

<style scoped>
.is-tabs { display: flex; gap: 8px; flex-wrap: wrap; }

.is-hint {
  display: flex; gap: 10px; align-items: flex-start;
  background: #eff6ff; border: 1px solid #bfdbfe; color: #1e40af;
  border-radius: 10px; padding: 10px 14px; font-size: 12.5px; line-height: 1.5;
}

.is-empty-card {
  background: #fff; border: 1.5px dashed #e2e8f0; border-radius: 12px;
  padding: 48px 20px; text-align: center;
}

/* ── Card grid (replaces table list) ── */
.is-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}
.is-card {
  background: #fff; border: 1px solid #e5e7eb; border-radius: 12px;
  padding: 14px 16px; display: flex; flex-direction: column; gap: 8px;
  transition: box-shadow .15s, border-color .15s, transform .1s;
}
.is-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.08); border-color: #c7d7f5; transform: translateY(-1px); }
.is-card-top { display: flex; align-items: center; justify-content: space-between; }
.is-card-icon {
  width: 34px; height: 34px; border-radius: 9px; background: #eff6ff; color: #1a6ef7;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.is-card-actions { display: flex; gap: 6px; }
.is-card-btn {
  width: 26px; height: 26px; border-radius: 6px; border: 1px solid #e8ecf0; background: #fff;
  color: #6b7280; cursor: pointer; display: flex; align-items: center; justify-content: center;
}
.is-card-btn:hover { background: #f9fafb; border-color: #374151; color: #374151; }
.is-card-btn--danger:hover { background: #fee2e2; border-color: #fca5a5; color: #dc2626; }
.is-card-name {
  font-size: 14px; font-weight: 700; color: #1a1a2e;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.is-card-sub {
  font-size: 12px; color: #9ca3af; line-height: 1.4;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.is-card-bottom { margin-top: 2px; }

.is-form { display: flex; flex-direction: column; gap: 14px; }
.is-field { display: flex; flex-direction: column; gap: 5px; }
.is-label { font-size: 12px; font-weight: 600; color: #374151; }
.is-input {
  border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 11px;
  font-size: 13px; outline: none; color: #1a1a2e; font-family: inherit; resize: vertical;
}
.is-input:focus { border-color: #1a6ef7; }

.is-toggle-row {
  margin-top: 4px; padding: 12px 14px; background: #f8fafc;
  border: 1px solid #e2e8f0; border-radius: 10px;
}
.is-toggle-label { display: flex; align-items: center; gap: 12px; cursor: pointer; }
.is-toggle-wrap { position: relative; flex-shrink: 0; }
.is-toggle-input { position: absolute; opacity: 0; width: 0; height: 0; }
.is-toggle-track {
  display: block; width: 38px; height: 21px; background: #e2e8f0;
  border-radius: 11px; position: relative; transition: background .2s;
}
.is-toggle-input:checked + .is-toggle-track { background: #1a6ef7; }
.is-toggle-thumb {
  position: absolute; top: 2.5px; left: 2.5px; width: 16px; height: 16px;
  background: #fff; border-radius: 50%; box-shadow: 0 1px 4px rgba(0,0,0,.2);
  transition: transform .2s;
}
.is-toggle-input:checked + .is-toggle-track .is-toggle-thumb { transform: translateX(17px); }
.is-toggle-text { flex: 1; }
.is-toggle-title { font-size: 12.5px; font-weight: 700; color: #374151; }
.is-toggle-sub   { display: block; font-size: 11px; color: #94a3b8; margin-top: 2px; line-height: 1.4; }

@media (max-width: 480px) {
  .is-grid { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
  .is-card { padding: 12px; }
}
</style>