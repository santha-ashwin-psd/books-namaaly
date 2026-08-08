<template>
<div class="ig-page">

  <!-- TOOLBAR -->
  <div class="ig-toolbar">
    <div class="ig-toolbar-left">
      <div class="ig-search-wrap">
        <span v-html="icon('search')" class="ig-search-icon"></span>
        <input v-model="search" class="ig-search-input" placeholder="Search groups…" />
        <button v-if="search" class="ig-search-clear" @click="search = ''">
          <span v-html="icon('x', 12)"></span>
        </button>
      </div>
    </div>
    <button class="ig-new-btn" @click="newGroup('All Item Groups')" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''">
      <span v-html="icon('plus', 13)"></span>
      <span class="ig-btn-label">New Group</span>
    </button>
  </div>

  <!-- BODY -->
  <div class="ig-body">

    <!-- ── Sidebar tree ── -->
    <aside class="ig-sidebar" :class="{ 'ig-mob-hidden': isMobile && panelMode !== 'none' }">
      <div class="ig-sidebar-header">
        <div class="ig-sidebar-title">
          Item Groups
          <span class="ig-sidebar-count">{{ allGroups.length }}</span>
        </div>
        <div class="ig-sidebar-stats">
          {{ allGroups.filter(g => g.is_group).length }} groups &middot; {{ allItems.length }} items
        </div>
        <div class="ig-sidebar-controls">
          <button class="ig-ctrl-btn" @click="toggleExpandAll"
            :title="allExpanded ? 'Collapse All' : 'Expand All'">
            <span class="ig-ctrl-chev" :class="{ 'ig-ctrl-chev--open': allExpanded }" v-html="icon('chevR', 11)"></span>
            {{ allExpanded ? 'Collapse All' : 'Expand All' }}
          </button>
          <button class="ig-ctrl-btn" :class="{ 'ig-ctrl-btn--active': sortMode === 'count' }"
            @click="sortMode = sortMode === 'count' ? 'name' : 'count'"
            :title="sortMode === 'count' ? 'Sort A–Z' : 'Sort by item count'">
            <span v-html="icon('hash', 11)"></span>
            {{ sortMode === 'count' ? 'By Count' : 'A – Z' }}
          </button>
        </div>
      </div>

      <div v-if="loading" class="ig-shimmer-wrap">
        <div v-for="i in 6" :key="i" class="ig-shimmer-row">
          <div class="b-shimmer" :style="{ width: (70 + i * 5) + '%', height: '14px', borderRadius: '4px' }"></div>
        </div>
      </div>

      <div v-else-if="!filteredTree.length" class="ig-tree-empty">
        <div style="font-size:28px;margin-bottom:8px">🔍</div>
        <div style="font-size:13px;color:#94a3b8">No groups found</div>
      </div>

      <div v-else class="ig-tree-scroll">
        <div
          v-for="node in filteredTree" :key="node.name"
          class="ig-tree-node"
          :class="{
            'ig-tree-node--active': selected === node.name,
            'ig-tree-node--group':  node.is_group,
            'ig-tree-node--leaf':   !node.is_group,
          }"
          :style="{ paddingLeft: (search ? 14 : 10 + node.depth * 20) + 'px' }"
          @click="selectGroup(node)"
        >
          <button v-if="hasChildren(node.name) && !search"
            class="ig-expand-btn" @click.stop="toggleExpand(node.name)">
            <span class="ig-expand-chev"
              :class="{ 'ig-expand-chev--open': expanded.has(node.name) }"
              v-html="icon('chevR', 10)"></span>
          </button>
          <span v-else class="ig-expand-spacer"></span>

          <span class="ig-node-icon">
            {{ node.is_group
              ? (expanded.has(node.name) && !search ? '📂' : '📁')
              : '🏷️' }}
          </span>

          <span class="ig-node-label">{{ node.name }}</span>

          <span v-if="!node.is_group && itemCountFor(node.name) > 0" class="ig-node-item-count">
            {{ itemCountFor(node.name) }}
          </span>
          <span v-else-if="node.is_group && hasChildren(node.name)" class="ig-node-count">
            {{ childCount(node.name) }}
          </span>

          <button class="ig-add-child-btn" :title="!$canCreate('inventory') ? 'Read-only access' : 'Add child group'" :disabled="!$canCreate('inventory')" @click.stop="newGroup(node.name)">
            <span v-html="icon('plus', 11)"></span>
          </button>
        </div>
      </div>
    </aside>

    <!-- ── Detail panel ── -->
    <main class="ig-detail" :class="{ 'ig-mob-hidden': isMobile && panelMode === 'none' }">

      <!-- Mobile back nav -->
      <div v-if="isMobile && panelMode !== 'none'" class="ig-mob-back-bar">
        <button class="ig-mob-back-btn" @click="panelMode = 'none'">
          <span v-html="icon('chevL', 15)"></span> Groups
        </button>
        <div class="ig-mob-back-title">
          {{ panelMode === 'new' ? 'New Group' : selectedGroup?.name || '' }}
        </div>
      </div>

      <!-- ════ EMPTY STATE ════ -->
      <div v-if="panelMode === 'none'" class="ig-empty-state">
        <div class="ig-empty-icon">📁</div>
        <div class="ig-empty-title">Select a group to view</div>
        <div class="ig-empty-sub">Click any item group from the list to see its details</div>
        <button class="ig-action-btn ig-action-btn--primary" style="margin-top:18px"
          :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''"
          @click="newGroup('All Item Groups')">
          <span v-html="icon('plus', 13)"></span> New Group
        </button>
      </div>

      <!-- ════ VIEW MODE ════ -->
      <div v-else-if="panelMode === 'view'" class="ig-form-wrap">

        <!-- Header -->
        <div class="ig-view-header">
          <div class="ig-form-icon-wrap" :class="selectedGroup?.is_group ? 'ig-form-icon--group' : 'ig-form-icon--leaf'">
            <span style="font-size:26px">{{ selectedGroup?.is_group ? '📁' : '🏷️' }}</span>
          </div>
          <div class="ig-form-header-info">
            <div class="ig-form-header-title">{{ selectedGroup?.name }}</div>
            <div class="ig-form-header-sub">
              <span v-if="selectedGroup?.parent_item_group" class="ig-breadcrumb">
                <span v-html="icon('chevR', 10)" style="opacity:.5"></span>
                {{ selectedGroup.parent_item_group }}
              </span>
              <span class="ig-view-badge">
                {{ selectedGroup?.is_group ? 'Group' : 'Leaf Group' }}
              </span>
            </div>
          </div>
          <div class="ig-form-stats">
            <div class="ig-form-stat">
              <div class="ig-form-stat-val">{{ childCount(selectedGroup?.name || '') }}</div>
              <div class="ig-form-stat-lbl">Children</div>
            </div>
            <div class="ig-form-stat">
              <div class="ig-form-stat-val">{{ itemCountFor(selectedGroup?.name || '') }}</div>
              <div class="ig-form-stat-lbl">Items</div>
            </div>
          </div>
        </div>

        <!-- Details card (read-only) -->
        <div class="ig-view-card">
          <div class="ig-form-section">Details</div>
          <div class="ig-view-rows">
            <div class="ig-view-row">
              <div class="ig-view-lbl">Group Name</div>
              <div class="ig-view-val">{{ selectedGroup?.name }}</div>
            </div>
            <div class="ig-view-row">
              <div class="ig-view-lbl">Parent Group</div>
              <div class="ig-view-val">{{ selectedGroup?.parent_item_group || '— (Root)' }}</div>
            </div>
            <div v-if="selectedGroup?.description" class="ig-view-row">
              <div class="ig-view-lbl">Description</div>
              <div class="ig-view-val">{{ selectedGroup.description }}</div>
            </div>
            <div class="ig-view-row">
              <div class="ig-view-lbl">Type</div>
              <div class="ig-view-val">
                <span class="ig-type-pill" :class="selectedGroup?.is_group ? 'ig-type-pill--group' : 'ig-type-pill--leaf'">
                  {{ selectedGroup?.is_group ? '📁 Group (has children)' : '🏷️ Leaf (items belong here)' }}
                </span>
              </div>
            </div>
            <div v-if="!selectedGroup?.is_group" class="ig-view-row">
              <div class="ig-view-lbl">Partial Material Issue</div>
              <div class="ig-view-val">
                <span class="ig-type-pill" :style="selectedGroup?.allow_partial_issue ? 'background:var(--bx-amberS);color:var(--bx-amber)' : 'background:#EEF1F6;color:var(--bx-muted)'">
                  {{ selectedGroup?.allow_partial_issue ? '✅ Allowed — can issue short / zero to WIP' : '🔒 Not allowed — must be fully in stock to issue' }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- View actions -->
        <div class="ig-form-actions">
          <button class="ig-action-btn ig-action-btn--primary" :disabled="!$canEdit('inventory')" :title="!$canEdit('inventory') ? 'Read-only access' : ''" @click="enterEditMode">
            <span v-html="icon('edit', 13)"></span> Edit Group
          </button>
          <button class="ig-action-btn" :disabled="!$canCreate('inventory')" :title="!$canCreate('inventory') ? 'Read-only access' : ''" @click="newGroup(selectedGroup?.name || 'All Item Groups')">
            <span v-html="icon('plus', 13)"></span> New Child
          </button>
          <div style="flex:1"></div>
          <button class="ig-action-btn ig-action-btn--danger" :disabled="!$canDelete('inventory')" :title="!$canDelete('inventory') ? 'Not permitted' : ''" @click="deleteGroup">
            <span v-html="icon('trash', 13)"></span> Delete
          </button>
        </div>

        <!-- Items in group -->
        <div class="ig-items-section">
          <div class="ig-items-hdr">
            <div class="ig-form-section" style="margin-bottom:0">Items in this Group</div>
            <span v-if="!itemsLoading" class="ig-items-count-pill">{{ groupItems.length }}</span>
          </div>

          <!-- Parent groups can't directly hold items -->
          <div v-if="selectedGroup?.is_group" class="ig-items-group-notice">
            <span style="font-size:20px;flex-shrink:0">📁</span>
            <div>
              <strong>Parent group</strong> — items are assigned to child groups, not directly here.
              Select a child group on the left to see its items.
            </div>
          </div>

          <template v-else>

          <div v-if="itemsLoading" class="ig-items-shimmer-wrap">
            <div v-for="i in 3" :key="i" class="b-shimmer" style="height:76px;border-radius:10px"></div>
          </div>

          <div v-else-if="!groupItems.length" class="ig-items-empty">
            <div style="font-size:30px;margin-bottom:8px">📭</div>
            <div class="ig-items-empty-title">No items in <strong>{{ selectedGroup?.name }}</strong></div>
            <div class="ig-items-empty-sub">
              Go to <strong>Items</strong> → create or edit an item → set Item Group to <em>{{ selectedGroup?.name }}</em>
            </div>
          </div>

          <div v-else class="ig-items-grid">
            <div v-for="item in groupItems" :key="item.name"
              class="ig-item-card"
              :class="{ 'ig-item-card--disabled': item.disabled }">
              <div class="ig-item-card-top">
                <span class="ig-item-card-icon">{{ itemTypeIcon(item.item_type) }}</span>
                <div class="ig-item-card-badges">
                  <span class="ig-item-type-badge"
                    :class="'ig-type--' + (item.item_type || 'Product').toLowerCase().replace(/[\s]+/g, '')">
                    {{ item.item_type || 'Product' }}
                  </span>
                  <span v-if="item.disabled" class="ig-item-inactive-badge">Inactive</span>
                </div>
              </div>
              <div class="ig-item-card-name">{{ item.item_name }}</div>
              <div class="ig-item-card-code">{{ item.item_code }}</div>
              <div class="ig-item-card-footer">
                <span class="ig-item-card-uom">{{ item.stock_uom || 'Nos' }}</span>
                <span class="ig-item-card-rate">₹ {{ flt(item.standard_rate, 2) }}</span>
              </div>
            </div>
          </div>

          </template>
        </div>

      </div>

      <!-- ════ EDIT / NEW MODE ════ -->
      <div v-else class="ig-form-wrap">

        <!-- Header -->
        <div class="ig-form-header">
          <div class="ig-form-icon-wrap" :class="form.is_group ? 'ig-form-icon--group' : 'ig-form-icon--leaf'">
            <span style="font-size:26px">{{ form.is_group ? '📁' : '🏷️' }}</span>
          </div>
          <div class="ig-form-header-info">
            <div class="ig-form-header-title">
              {{ panelMode === 'edit' ? form.name : 'New Item Group' }}
            </div>
            <div class="ig-form-header-sub">
              <span v-if="panelMode === 'edit' && form.parent_item_group" class="ig-breadcrumb">
                <span v-html="icon('chevR', 10)" style="opacity:.5"></span>
                {{ form.parent_item_group }}
              </span>
              <span class="ig-form-mode-badge" :class="panelMode === 'new' ? 'ig-form-mode-badge--new' : 'ig-form-mode-badge--edit'">
                {{ panelMode === 'new' ? 'New' : 'Editing' }}
              </span>
            </div>
          </div>
          <div v-if="panelMode === 'edit'" class="ig-form-stats">
            <div class="ig-form-stat">
              <div class="ig-form-stat-val">{{ childCount(form.name) }}</div>
              <div class="ig-form-stat-lbl">Children</div>
            </div>
            <div class="ig-form-stat">
              <div class="ig-form-stat-val">{{ itemCountFor(form.name) }}</div>
              <div class="ig-form-stat-lbl">Items</div>
            </div>
          </div>
        </div>

        <!-- Form fields -->
        <div class="ig-form-card">
          <div class="ig-form-section">Group Details</div>
          <div class="ig-form-grid">
            <div class="ig-field">
              <label class="nim-label">Group Name <span style="color:#dc2626">*</span></label>
              <input class="nim-input" v-model="form.name"
                placeholder="e.g. Electronics"/>
            </div>
            <div class="ig-field">
              <label class="nim-label">Parent Group</label>
              <select class="nim-input" v-model="form.parent_item_group">
                <option value="">— Root (no parent) —</option>
                <option v-for="g in allGroups.filter(g => g.is_group && g.name !== form.name)" :key="g.name" :value="g.name">
                  {{ g.name }}
                </option>
              </select>
            </div>
          </div>

          <div class="ig-field" style="margin-top:14px">
            <label class="nim-label">Description</label>
            <textarea class="nim-input" v-model="form.description" rows="3"
              placeholder="Optional description…" style="resize:vertical"></textarea>
          </div>

          <div class="ig-is-group-row">
            <label class="ig-is-group-label">
              <div class="ig-toggle-wrap">
                <input type="checkbox" class="ig-toggle-input"
                  :checked="!!form.is_group"
                  @change="form.is_group = $event.target.checked ? 1 : 0"/>
                <span class="ig-toggle-track">
                  <span class="ig-toggle-thumb"></span>
                </span>
              </div>
              <div class="ig-is-group-text">
                <div class="ig-is-group-title">Is a Group</div>
                <div class="ig-is-group-sub">Group nodes can have child item groups</div>
              </div>
            </label>
          </div>

          <div v-if="!form.is_group" class="ig-is-group-row">
            <label class="ig-is-group-label">
              <div class="ig-toggle-wrap">
                <input type="checkbox" class="ig-toggle-input"
                  :checked="!!form.allow_partial_issue"
                  @change="form.allow_partial_issue = $event.target.checked ? 1 : 0"/>
                <span class="ig-toggle-track">
                  <span class="ig-toggle-thumb"></span>
                </span>
              </div>
              <div class="ig-is-group-text">
                <div class="ig-is-group-title">Allow Partial Material Issue</div>
                <div class="ig-is-group-sub">
                  Work Order → Issue Materials may issue less than required (even zero) for items in
                  this group when stock is short. Unchecked items must be fully in stock to be issued —
                  otherwise they're skipped and stay pending, without blocking other items.
                </div>
              </div>
            </label>
          </div>
        </div>

        <!-- Form actions -->
        <div class="ig-form-actions">
          <button class="ig-action-btn ig-action-btn--primary" :disabled="saving || !(panelMode === 'edit' ? $canEdit('inventory') : $canCreate('inventory'))" @click="saveGroup">
            <span v-html="icon('check', 14)"></span>
            {{ saving ? 'Saving…' : (panelMode === 'edit' ? 'Update Group' : 'Create Group') }}
          </button>
          <button class="ig-action-btn" @click="cancelForm">
            Cancel
          </button>
        </div>

      </div>
    </main>
  </div>
</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from "vue";
import { apiList, apiSave, apiDelete, apiPOST } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { useConfirm } from "../composables/useConfirm.js";
import { icon } from "../utils/icons.js";
import { flt } from "../utils/format.js";

const { toast }   = useToast();
const { confirm } = useConfirm();

// panelMode: 'none' | 'view' | 'edit' | 'new'
const panelMode    = ref("none");
const originalName = ref("");
const allGroups    = ref([]);
const loading      = ref(true);
const saving       = ref(false);
const selected     = ref(null);
const selectedGroup = ref(null);
const expanded     = ref(new Set(["All Item Groups"]));
const search       = ref("");
const sortMode     = ref("name");
const isMobile     = ref(window.innerWidth <= 480);

const allItems     = ref([]);
const itemsLoading = ref(false);

const form = reactive({ name: "", parent_item_group: "All Item Groups", is_group: 0, description: "", allow_partial_issue: 0 });

function onResize() { isMobile.value = window.innerWidth <= 480; }

const GROUP_DEFAULTS = [
  { name: "All Item Groups",  parent_item_group: "",                is_group: 1, description: "Root", allow_partial_issue: 0 },
  { name: "Products",         parent_item_group: "All Item Groups", is_group: 1, description: "", allow_partial_issue: 0 },
  { name: "Services",         parent_item_group: "All Item Groups", is_group: 1, description: "", allow_partial_issue: 0 },
  { name: "Raw Materials",    parent_item_group: "All Item Groups", is_group: 1, description: "", allow_partial_issue: 0 },
  { name: "Finished Goods",   parent_item_group: "All Item Groups", is_group: 1, description: "", allow_partial_issue: 0 },
];

async function load() {
  loading.value = true;
  try {
    const rows = await apiList("Item Group", {
      fields: ["name", "parent_item_group", "is_group", "description", "allow_partial_issue"],
      order: "name asc", limit: 200,
    });
    allGroups.value = rows || [];
  } catch { allGroups.value = GROUP_DEFAULTS; }
  loading.value = false;
}

async function loadItems() {
  itemsLoading.value = true;
  try {
    allItems.value = await apiList("Item", {
      fields: ["name", "item_code", "item_name", "item_group", "item_type",
               "stock_uom", "standard_rate", "disabled", "is_stock_item"],
      order: "item_name asc", limit: 100000,
    });
  } catch { allItems.value = []; }
  itemsLoading.value = false;
}

const itemsByGroup = computed(() => {
  const map = {};
  allItems.value.forEach((item) => {
    const g = item.item_group || "";
    if (!map[g]) map[g] = [];
    map[g].push(item);
  });
  return map;
});

const groupItems = computed(() =>
  selected.value ? (itemsByGroup.value[selected.value] || []) : []
);

const flatTree = computed(() => {
  const byParent = {};
  allGroups.value.forEach((g) => {
    const p = g.parent_item_group || "";
    if (!byParent[p]) byParent[p] = [];
    byParent[p].push(g);
  });

  function sortedChildren(children) {
    if (sortMode.value !== "count") return children;
    return [...children].sort((a, b) => {
      const aVal = a.is_group ? (byParent[a.name] || []).length : (itemsByGroup.value[a.name] || []).length;
      const bVal = b.is_group ? (byParent[b.name] || []).length : (itemsByGroup.value[b.name] || []).length;
      return bVal - aVal;
    });
  }

  const known = new Set(allGroups.value.map((g) => g.name));
  const roots = allGroups.value.filter((g) => !g.parent_item_group || !known.has(g.parent_item_group));
  const out = [];
  function walk(node, depth) {
    out.push({ ...node, depth });
    if (!expanded.value.has(node.name)) return;
    sortedChildren(byParent[node.name] || []).forEach((k) => walk(k, depth + 1));
  }
  sortedChildren(roots).forEach((r) => walk(r, 0));
  return out;
});

const allExpanded = computed(() => {
  const groupsWithChildren = allGroups.value.filter(g => g.is_group && hasChildren(g.name));
  return groupsWithChildren.length > 0 && groupsWithChildren.every(g => expanded.value.has(g.name));
});

const filteredTree = computed(() => {
  const q = search.value.toLowerCase().trim();
  if (!q) return flatTree.value;
  return allGroups.value
    .filter((g) => g.name.toLowerCase().includes(q) || (g.description || "").toLowerCase().includes(q))
    .map((g) => ({ ...g, depth: 0 }));
});

function hasChildren(name) { return allGroups.value.some((g) => g.parent_item_group === name); }
function childCount(name)  { return allGroups.value.filter((g) => g.parent_item_group === name).length; }
function itemCountFor(name) { return (itemsByGroup.value[name] || []).length; }

function itemTypeIcon(type) {
  return { Product: "📦", Service: "🛠️", "Raw Material": "⚙️", "Finished Good": "✅", "Scrap Item": "♻️" }[type] || "📦";
}

function toggleExpand(name) {
  const s = new Set(expanded.value);
  s.has(name) ? s.delete(name) : s.add(name);
  expanded.value = s;
}

function toggleExpandAll() {
  if (allExpanded.value) {
    expanded.value = new Set();
  } else {
    expanded.value = new Set(allGroups.value.filter(g => g.is_group).map(g => g.name));
  }
}

function expandToNode(name) {
  const s = new Set(expanded.value);
  let cur = allGroups.value.find(g => g.name === name);
  while (cur?.parent_item_group) {
    s.add(cur.parent_item_group);
    cur = allGroups.value.find(g => g.name === cur.parent_item_group);
  }
  expanded.value = s;
}

function selectGroup(g) {
  selected.value = g.name;
  selectedGroup.value = g;
  expandToNode(g.name);
  panelMode.value = "view";
}

function enterEditMode() {
  if (!selectedGroup.value) return;
  originalName.value = selectedGroup.value.name;
  Object.assign(form, {
    name: selectedGroup.value.name,
    parent_item_group: selectedGroup.value.parent_item_group || "",
    is_group: selectedGroup.value.is_group ? 1 : 0,
    description: selectedGroup.value.description || "",
    allow_partial_issue: selectedGroup.value.allow_partial_issue ? 1 : 0,
  });
  panelMode.value = "edit";
}

function newGroup(parentName) {
  selected.value = null;
  selectedGroup.value = null;
  Object.assign(form, { name: "", parent_item_group: parentName || "All Item Groups", is_group: 0, description: "", allow_partial_issue: 0 });
  panelMode.value = "new";
}

function cancelForm() {
  if (panelMode.value === "edit") {
    panelMode.value = "view";
  } else {
    panelMode.value = selected.value ? "view" : "none";
  }
}

async function saveGroup() {
  if (!form.name.trim()) { toast("Group name is required", "error"); return; }
  saving.value = true;
  try {
    const isEdit = panelMode.value === "edit";
    const nameChanged = isEdit && form.name.trim() !== originalName.value;

    // Rename doc first if name changed
    if (nameChanged) {
      await apiPOST("frappe.client.rename_doc", {
        doctype: "Item Group",
        old_name: originalName.value,
        new_name: form.name.trim(),
        merge: 0,
      });
    }

    await apiSave({
      doctype: "Item Group",
      name: form.name.trim(),
      parent_item_group: form.parent_item_group,
      is_group: form.is_group ? 1 : 0,
      description: form.description,
      allow_partial_issue: form.is_group ? 0 : (form.allow_partial_issue ? 1 : 0),
    });
    await load();
    await loadItems();
    selected.value = form.name.trim();
    const updated = allGroups.value.find((g) => g.name === form.name.trim());
    selectedGroup.value = updated || null;
    originalName.value = form.name.trim();
    if (form.parent_item_group) {
      const s = new Set(expanded.value);
      s.add(form.parent_item_group);
      expanded.value = s;
    }
    toast(isEdit ? "Group updated" : "Group created");
    panelMode.value = "view";
  } catch (e) { toast("Save failed: " + e.message, "error"); }
  finally { saving.value = false; }
}

function getDescendants(name) {
  const result = [];
  function collect(n) {
    allGroups.value
      .filter((g) => g.parent_item_group === n)
      .forEach((g) => { result.push(g); collect(g.name); });
  }
  collect(name);
  return result;
}

async function deleteGroup() {
  if (!selectedGroup.value) return;
  const descendants = getDescendants(selectedGroup.value.name);
  const childMsg = descendants.length
    ? ` and its ${descendants.length} child group(s)` : "";
  if (!(await confirm({
    title: "Delete group?",
    body: `Delete "${selectedGroup.value.name}"${childMsg}? This cannot be undone.`,
    okLabel: "Delete All",
  }))) return;
  try {
    for (const d of [...descendants].reverse()) {
      await apiDelete("Item Group", d.name);
    }
    await apiDelete("Item Group", selectedGroup.value.name);
    await load();
    selected.value = null;
    selectedGroup.value = null;
    panelMode.value = "none";
    toast(descendants.length
      ? `Deleted group and ${descendants.length} child(ren)`
      : "Group deleted");
  } catch (e) { toast("Delete failed: " + e.message, "error"); }
}

onMounted(() => {
  load();
  loadItems();
  window.addEventListener("resize", onResize, { passive: true });
});
onUnmounted(() => window.removeEventListener("resize", onResize));
</script>

<style>
/* ════════════════════════════════════════════════════════════════
   ITEM GROUPS PAGE
   ════════════════════════════════════════════════════════════════ */

.ig-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px);
  background: #f1f4f8;
  overflow: hidden;
}

/* ── Toolbar ── */
.ig-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 24px;
  background: #fff;
  border-bottom: 1px solid #e8edf5;
  flex-shrink: 0;
}
.ig-toolbar-left { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; }

.ig-search-wrap { position: relative; width: 260px; max-width: 100%; }
.ig-search-icon {
  position: absolute; left: 10px; top: 50%; transform: translateY(-50%);
  color: #94a3b8; pointer-events: none; width: 14px;
}
.ig-search-input {
  width: 100%; border: 1.5px solid #e2e8f0; border-radius: 9px;
  padding: 8px 32px 8px 32px; font-size: 13px; color: #1e293b;
  outline: none; background: #f8fafc; transition: border-color .15s, background .15s;
  box-sizing: border-box;
}
.ig-search-input:focus { border-color: #3b82f6; background: #fff; }
.ig-search-clear {
  position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
  background: #e2e8f0; border: none; border-radius: 50%; width: 18px; height: 18px;
  display: flex; align-items: center; justify-content: center; cursor: pointer; color: #64748b;
}

.ig-new-btn {
  display: inline-flex; align-items: center; gap: 7px; padding: 8px 18px;
  font-size: 13px; font-weight: 700;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: #fff; border: none; border-radius: 9px; cursor: pointer;
  box-shadow: 0 2px 8px rgba(37,99,235,.3);
  transition: opacity .15s, transform .1s; white-space: nowrap; flex-shrink: 0;
}
.ig-new-btn:hover { opacity: .9; transform: translateY(-1px); }
.ig-new-btn:active { transform: translateY(0); }

/* ── Body ── */
.ig-body { display: flex; flex: 1; overflow: hidden; }

/* ── Sidebar ── */
.ig-sidebar {
  width: 300px; min-width: 300px; display: flex; flex-direction: column;
  background: #fff; border-right: 1px solid #e2e8f0;
  box-shadow: 2px 0 12px rgba(0,0,0,.04);
}
.ig-sidebar-header { padding: 16px 18px 12px; border-bottom: 1px solid #edf0f5; }
.ig-sidebar-title {
  font-size: 13.5px; font-weight: 800; color: #0f172a;
  display: flex; align-items: center; gap: 8px;
}
.ig-sidebar-count {
  font-size: 11px; font-weight: 700; background: #e2e8f0; color: #475569;
  padding: 2px 8px; border-radius: 20px;
}
.ig-sidebar-stats {
  font-size: 11.5px; color: #94a3b8; font-weight: 500; margin-top: 4px;
}
.ig-sidebar-controls {
  display: flex; align-items: center; gap: 6px; margin-top: 10px;
}
.ig-ctrl-btn {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 11.5px; font-weight: 600; color: #475569;
  background: #f1f5f9; border: 1.5px solid #e2e8f0; border-radius: 7px;
  padding: 4px 10px; cursor: pointer; transition: background .12s, border-color .12s, color .12s;
  white-space: nowrap;
}
.ig-ctrl-btn:hover { background: #e2e8f0; color: #1e293b; }
.ig-ctrl-btn--active { background: #eff6ff; border-color: #93c5fd; color: #2563eb; }
.ig-ctrl-chev { display: flex; align-items: center; transition: transform .18s ease; }
.ig-ctrl-chev--open { transform: rotate(90deg); }

.ig-shimmer-wrap { padding: 14px 16px; display: flex; flex-direction: column; gap: 10px; }
.ig-shimmer-row  { display: flex; align-items: center; }
.ig-tree-empty   { padding: 40px 20px; text-align: center; }

/* ── Tree ── */
.ig-tree-scroll { flex: 1; overflow-y: auto; padding: 6px 0; }

.ig-tree-node {
  display: flex; align-items: center; gap: 6px;
  padding-top: 7px; padding-bottom: 7px; padding-right: 10px;
  cursor: pointer; border-left: 3px solid transparent;
  transition: background .1s, border-color .1s; position: relative;
}
.ig-tree-node:hover { background: #f8fafc; }
.ig-tree-node:hover .ig-add-child-btn { opacity: 1; }
.ig-tree-node--active { background: #eff6ff !important; border-left-color: #2563eb !important; }
.ig-tree-node--active .ig-node-label { color: #2563eb; font-weight: 700; }
.ig-tree-node--group > .ig-node-label { font-weight: 700; color: #0f172a; }
.ig-tree-node--leaf  > .ig-node-label { font-weight: 500; color: #374151; }

.ig-expand-btn {
  width: 20px; height: 20px; display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; background: none; border: none; cursor: pointer; border-radius: 4px;
  color: #94a3b8; transition: background .1s; padding: 0;
}
.ig-expand-btn:hover { background: #e2e8f0; color: #475569; }
.ig-expand-chev { display: flex; align-items: center; transition: transform .18s ease; }
.ig-expand-chev--open { transform: rotate(90deg); }
.ig-expand-spacer { width: 20px; flex-shrink: 0; }
.ig-node-icon { font-size: 14px; flex-shrink: 0; }
.ig-node-label {
  flex: 1; min-width: 0; font-size: 13px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ig-node-count {
  font-size: 10px; font-weight: 700; background: #f1f5f9; color: #64748b;
  padding: 1px 7px; border-radius: 10px; flex-shrink: 0;
}
.ig-node-item-count {
  font-size: 10px; font-weight: 700; background: #dcfce7; color: #15803d;
  padding: 1px 7px; border-radius: 10px; flex-shrink: 0;
}
.ig-add-child-btn {
  width: 20px; height: 20px; display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; background: #eff6ff; border: 1px solid #93c5fd; border-radius: 5px;
  cursor: pointer; color: #2563eb; opacity: 0; transition: opacity .12s, background .1s; padding: 0;
}
.ig-add-child-btn:hover { background: #dbeafe; }

/* ── Detail panel ── */
.ig-detail {
  flex: 1; overflow-y: auto; background: #f1f4f8; display: flex; flex-direction: column;
}

/* ── Empty state ── */
.ig-empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  flex: 1; padding: 40px; text-align: center;
}
.ig-empty-icon  { font-size: 56px; margin-bottom: 14px; }
.ig-empty-title { font-size: 17px; font-weight: 700; color: #334155; margin-bottom: 6px; }
.ig-empty-sub   { font-size: 13.5px; color: #94a3b8; max-width: 260px; line-height: 1.5; }

/* ── Form / view wrap ── */
.ig-form-wrap {
  padding: 24px 28px; display: flex; flex-direction: column;
  gap: 16px; max-width: 800px; width: 100%;
}

/* ── View header (read-only) ── */
.ig-view-header {
  background: #fff; border-radius: 14px; padding: 20px 24px;
  display: flex; align-items: center; gap: 16px;
  border: 1px solid #e8edf5;
  box-shadow: 0 1px 4px rgba(0,0,0,.06), 0 4px 16px rgba(0,0,0,.04);
  flex-wrap: wrap;
}

/* ── Form header (edit/new) ── */
.ig-form-header {
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  border-radius: 14px; padding: 20px 24px;
  display: flex; align-items: center; gap: 16px;
  box-shadow: 0 4px 16px rgba(0,0,0,.15);
  flex-wrap: wrap;
}
.ig-form-header .ig-form-header-title { color: #fff; }
.ig-form-header .ig-form-header-sub   { color: rgba(255,255,255,.7); }
.ig-form-header .ig-breadcrumb        { color: rgba(255,255,255,.6); }
.ig-form-header .ig-form-stat-val     { color: #93c5fd; }
.ig-form-header .ig-form-stat-lbl     { color: rgba(255,255,255,.5); }

.ig-form-icon-wrap {
  width: 56px; height: 56px; border-radius: 14px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.ig-form-icon--group { background: #eff6ff; }
.ig-form-icon--leaf  { background: #f0fdf4; }
.ig-form-header .ig-form-icon--group { background: rgba(219,234,254,.2); }
.ig-form-header .ig-form-icon--leaf  { background: rgba(220,252,231,.2); }

.ig-form-header-info { flex: 1; min-width: 0; }
.ig-form-header-title {
  font-size: 20px; font-weight: 800; color: #0f172a;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-bottom: 5px;
}
.ig-form-header-sub { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

.ig-breadcrumb { display: flex; align-items: center; gap: 4px; font-size: 12px; color: #64748b; }

/* Badges */
.ig-view-badge {
  font-size: 11px; font-weight: 700; padding: 2px 10px;
  border-radius: 20px; background: #e2e8f0; color: #475569;
}
.ig-form-mode-badge {
  font-size: 11px; font-weight: 700; padding: 2px 10px; border-radius: 20px;
}
.ig-form-mode-badge--new  { background: #dcfce7; color: #15803d; }
.ig-form-mode-badge--edit { background: rgba(251,191,36,.25); color: #d97706; }

.ig-form-stats { display: flex; gap: 20px; flex-shrink: 0; }
.ig-form-stat  { text-align: center; }
.ig-form-stat-val {
  font-size: 22px; font-weight: 800; color: #2563eb; line-height: 1; margin-bottom: 3px;
}
.ig-form-stat-lbl {
  font-size: 10.5px; font-weight: 600; color: #94a3b8;
  text-transform: uppercase; letter-spacing: .04em;
}

/* ── View card (read-only details) ── */
.ig-view-card {
  background: #fff; border-radius: 14px; padding: 22px 24px;
  border: 1px solid #e8edf5; box-shadow: 0 1px 4px rgba(0,0,0,.05);
}
.ig-view-rows { display: flex; flex-direction: column; gap: 0; }
.ig-view-row {
  display: flex; align-items: flex-start; gap: 16px;
  padding: 12px 0; border-bottom: 1px solid #f1f5f9;
}
.ig-view-row:last-child { border-bottom: none; }
.ig-view-lbl {
  width: 130px; flex-shrink: 0; font-size: 12px; font-weight: 700;
  color: #94a3b8; text-transform: uppercase; letter-spacing: .04em; padding-top: 2px;
}
.ig-view-val { flex: 1; font-size: 13.5px; font-weight: 600; color: #1e293b; }

.ig-type-pill {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 12px; font-weight: 700; padding: 4px 12px; border-radius: 20px;
}
.ig-type-pill--group { background: #eff6ff; color: #2563eb; }
.ig-type-pill--leaf  { background: #f0fdf4; color: #15803d; }

/* ── Form card ── */
.ig-form-card {
  background: #fff; border-radius: 14px; padding: 22px 24px;
  border: 1px solid #e8edf5; box-shadow: 0 1px 4px rgba(0,0,0,.05);
}
.ig-form-section {
  font-size: 10.5px; font-weight: 800; color: #94a3b8;
  text-transform: uppercase; letter-spacing: .07em; margin-bottom: 16px;
}
.ig-form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.ig-field { display: flex; flex-direction: column; gap: 5px; }

/* ── Toggle ── */
.ig-is-group-row {
  margin-top: 18px; padding: 14px 16px; background: #f8fafc;
  border: 1px solid #e2e8f0; border-radius: 10px;
}
.ig-is-group-label { display: flex; align-items: center; gap: 14px; cursor: pointer; }
.ig-toggle-wrap { position: relative; flex-shrink: 0; }
.ig-toggle-input { position: absolute; opacity: 0; width: 0; height: 0; }
.ig-toggle-track {
  display: block; width: 40px; height: 22px; background: #e2e8f0;
  border-radius: 11px; position: relative; transition: background .2s;
}
.ig-toggle-input:checked + .ig-toggle-track { background: #2563eb; }
.ig-toggle-thumb {
  position: absolute; top: 3px; left: 3px; width: 16px; height: 16px;
  background: #fff; border-radius: 50%; box-shadow: 0 1px 4px rgba(0,0,0,.2);
  transition: transform .2s;
}
.ig-toggle-input:checked + .ig-toggle-track .ig-toggle-thumb { transform: translateX(18px); }
.ig-is-group-text { flex: 1; }
.ig-is-group-title { font-size: 13px; font-weight: 700; color: #374151; }
.ig-is-group-sub   { font-size: 11.5px; color: #94a3b8; margin-top: 2px; }

/* ── Actions ── */
.ig-form-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.ig-action-btn {
  display: inline-flex; align-items: center; gap: 6px; padding: 9px 18px;
  font-size: 13px; font-weight: 600; border-radius: 9px; border: 1.5px solid #e2e8f0;
  background: #fff; color: #374151; cursor: pointer;
  transition: background .12s, box-shadow .12s, transform .1s; white-space: nowrap;
}
.ig-action-btn:hover { background: #f8fafc; box-shadow: 0 2px 6px rgba(0,0,0,.08); }
.ig-action-btn:active { transform: translateY(1px); }
.ig-action-btn:disabled { opacity: .55; cursor: not-allowed; }
.ig-action-btn--primary {
  background: linear-gradient(135deg, #3b82f6, #2563eb); color: #fff;
  border-color: transparent; box-shadow: 0 2px 8px rgba(37,99,235,.3);
}
.ig-action-btn--primary:hover { opacity: .9; background: linear-gradient(135deg, #3b82f6, #2563eb); }
.ig-action-btn--danger { color: #dc2626; border-color: #fca5a5; background: #fff5f5; }
.ig-action-btn--danger:hover { background: #fee2e2; }

/* ── Mobile back bar ── */
.ig-mob-back-bar {
  display: flex; align-items: center; gap: 10px; padding: 10px 14px;
  background: #fff; border-bottom: 1px solid #e4e8f0;
  position: sticky; top: 0; z-index: 10; flex-shrink: 0;
}
.ig-mob-back-btn {
  display: flex; align-items: center; gap: 4px; font-size: 13px; font-weight: 600;
  color: #2563eb; background: none; border: none; cursor: pointer; padding: 4px 0; flex-shrink: 0;
}
.ig-mob-back-title {
  font-size: 13.5px; font-weight: 700; color: #1a1d23;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* ══════════════════════════════════════
   ITEMS IN GROUP SECTION
   ══════════════════════════════════════ */
.ig-items-section {
  background: #fff; border-radius: 14px; padding: 22px 24px;
  border: 1px solid #e8edf5; box-shadow: 0 1px 4px rgba(0,0,0,.05);
  display: flex; flex-direction: column; gap: 14px;
}
.ig-items-hdr { display: flex; align-items: center; justify-content: space-between; }
.ig-items-count-pill {
  font-size: 11px; font-weight: 800; background: #dbeafe; color: #1d4ed8;
  padding: 3px 10px; border-radius: 20px;
}
.ig-items-shimmer-wrap { display: flex; flex-direction: column; gap: 10px; }

.ig-items-group-notice {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  background: #fffbeb;
  border: 1.5px solid #fde68a;
  border-radius: 10px;
  font-size: 13px;
  color: #92400e;
  line-height: 1.5;
}
.ig-items-empty {
  padding: 24px 16px; text-align: center;
  background: #f8fafc; border-radius: 10px; border: 1.5px dashed #e2e8f0;
}
.ig-items-empty-title { font-size: 13.5px; font-weight: 600; color: #374151; margin-bottom: 6px; }
.ig-items-empty-sub   { font-size: 12px; color: #94a3b8; line-height: 1.5; }

.ig-items-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px;
}
.ig-item-card {
  background: #f8fafc; border: 1.5px solid #e8edf5; border-radius: 12px;
  padding: 14px; display: flex; flex-direction: column; gap: 6px;
  transition: box-shadow .15s, border-color .15s, transform .1s;
}
.ig-item-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.09); border-color: #c7d7f5; transform: translateY(-1px); }
.ig-item-card--disabled { opacity: .5; filter: grayscale(0.5); }

.ig-item-card-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.ig-item-card-icon { font-size: 20px; flex-shrink: 0; }
.ig-item-card-badges { display: flex; gap: 4px; align-items: center; flex-wrap: wrap; }
.ig-item-type-badge {
  font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 8px; white-space: nowrap;
}
.ig-type--product      { background: #dbeafe; color: #1d4ed8; }
.ig-type--service      { background: #f3e8ff; color: #7c3aed; }
.ig-type--rawmaterial  { background: #fef3c7; color: #92400e; }
.ig-type--finishedgood { background: #dcfce7; color: #15803d; }
.ig-type--scrapitem    { background: #fef3c7; color: #b45309; }
.ig-item-inactive-badge {
  font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 8px;
  background: #fee2e2; color: #b91c1c;
}
.ig-item-card-name {
  font-size: 13px; font-weight: 700; color: #0f172a;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ig-item-card-code {
  font-size: 11px; color: #64748b;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ig-item-card-footer {
  display: flex; align-items: center; justify-content: space-between;
  margin-top: 4px; padding-top: 8px; border-top: 1px solid #e8edf5;
}
.ig-item-card-uom  { font-size: 11px; color: #94a3b8; font-weight: 600; }
.ig-item-card-rate { font-size: 13px; font-weight: 800; color: #2563eb; }

/* ══════════════════════════════════════
   TABLET (481 – 768 px)
   ══════════════════════════════════════ */
@media (max-width: 768px) {
  .ig-sidebar { width: 240px; min-width: 240px; }
  .ig-form-wrap { padding: 16px 18px; }
  .ig-view-header, .ig-form-header { padding: 16px 18px; }
  .ig-form-header-title { font-size: 17px; }
  .ig-form-icon-wrap { width: 46px; height: 46px; }
  .ig-view-card, .ig-form-card { padding: 16px 18px; }
  .ig-form-grid { grid-template-columns: 1fr; }
  .ig-search-wrap { width: 200px; }
  .ig-items-section { padding: 16px 18px; }
  .ig-items-grid { grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); }
}

/* ══════════════════════════════════════
   MOBILE (≤ 480 px)
   ══════════════════════════════════════ */
@media (max-width: 480px) {
  .ig-toolbar { padding: 10px 14px; }
  .ig-search-wrap { width: 100%; flex: 1; }
  .ig-btn-label { display: none; }
  .ig-new-btn { padding: 8px 12px; }

  .ig-body { flex-direction: column; }

  .ig-sidebar {
    width: 100% !important; min-width: 0 !important;
    border-right: none !important; border-bottom: 1px solid #e2e8f0; flex: 1;
  }
  .ig-detail {
    position: absolute; inset: 0; top: 56px; z-index: 50; background: #f1f4f8;
  }
  .ig-mob-hidden { display: none !important; }

  .ig-form-wrap { padding: 14px 14px; }
  .ig-view-header, .ig-form-header { padding: 14px 16px; gap: 12px; }
  .ig-form-header-title { font-size: 15px; }
  .ig-form-icon-wrap { width: 42px; height: 42px; }
  .ig-form-stats { gap: 14px; }
  .ig-form-stat-val { font-size: 18px; }
  .ig-view-card, .ig-form-card { padding: 14px 16px; }
  .ig-view-lbl { width: 100px; }
  .ig-form-grid { grid-template-columns: 1fr; }
  .ig-form-actions { gap: 8px; }
  .ig-action-btn { padding: 8px 14px; font-size: 12.5px; }
  .ig-items-section { padding: 14px 16px; }
  .ig-items-grid { grid-template-columns: repeat(auto-fill, minmax(145px, 1fr)); }
}
</style>