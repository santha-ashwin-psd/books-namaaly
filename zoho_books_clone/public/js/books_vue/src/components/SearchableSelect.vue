<template>
  <div class="ss-wrap">
    <div
      ref="trigEl" class="ss-trigger"
      :class="{ open, 'ss-disabled': disabled, 'ss-compact': compact }"
      tabindex="0"
      @click="openDD"
      @keydown.enter.prevent="openDD"
      @keydown.space.prevent="openDD"
    >
      <span class="ss-display" :class="{ 'ss-ph': !modelValue && modelValue !== 0 }">
        {{ (modelValue || modelValue === 0) ? displayLabel : placeholder }}
      </span>
      <span v-if="normalized.length > 1" class="ss-caret">
        <IconSvg name="chevD" :size="11" />
      </span>
    </div>

    <Teleport to="body">
      <div v-if="open" class="ss-drop ss-drop-teleport" :style="dropStyle">
        <div class="ss-search-row">
          <input
            ref="inputEl" v-model="q"
            class="ss-search-input"
            placeholder="Type to search…"
            @keydown.escape="open = false"
            @keydown.enter.prevent="filtered.length ? pick(filtered[0]) : (showCreate && onClickCreate())"
          />
        </div>
        <div class="ss-opts">
          <div v-if="!filtered.length && !showCreate" class="ss-no-match">
            {{ normalized.length ? `No matches for "${q}"` : "No options available" }}
          </div>
          <div
            v-for="o in filtered" :key="o.value"
            class="ss-opt"
            :class="{ 'ss-opt-sel': String(o.value) === String(modelValue) }"
            @mousedown.prevent="pick(o)"
          >{{ o.label }}</div>
          <div
            v-if="showCreate"
            class="ss-opt ss-opt-create"
            @mousedown.prevent="onClickCreate"
          >
            <IconSvg v-if="!(props.staticCreate && !q.trim())" name="plus" :size="13" />
            <template v-if="props.staticCreate && !q.trim()">{{ props.createLabel || '+ Add New' }}</template>
            <template v-else>Create <strong style="margin-left:4px">"{{ q.trim() }}"</strong></template>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from "vue";
import IconSvg from "./IconSvg.vue";
import { useQuickCreate } from "../composables/useQuickCreate.js";

const props = defineProps({
  modelValue:    { default: "" },
  options:       { type: Array,   default: () => [] },
  valueKey:      { type: String,  default: "" },
  labelKey:      { type: String,  default: "" },
  placeholder:   { type: String,  default: "— Select —" },
  compact:       { type: Boolean, default: false },
  disabled:      { type: Boolean, default: false },
  createable:    { type: Boolean, default: false },
  staticCreate:  { type: Boolean, default: false },
  createDoctype: { type: String,  default: "" },
  createLabel:   { type: String,  default: "" },
});
const emit = defineEmits(["update:modelValue", "select", "create", "search"]);

// Field configs for built-in quick-create. Mirrors books.js:389-409.
const SS_CREATE_FIELDS = {
  Item: [
    { f: "item_name",     l: "Item Name",  req: true,  type: "text" },
    { f: "item_group",    l: "Item Group", req: false, type: "text" },
    { f: "standard_rate", l: "Rate (₹)",   req: false, type: "number" },
    { f: "stock_uom",     l: "UOM",        req: false, type: "text", placeholder: "Nos" },
  ],
  Customer: [
    { f: "customer_name",  l: "Customer Name", req: true,  type: "text" },
    { f: "customer_group", l: "Group",         req: false, type: "text", placeholder: "All Customer Groups" },
    { f: "mobile_no",      l: "Mobile",        req: false, type: "text" },
  ],
  Supplier: [
    { f: "supplier_name",  l: "Supplier Name", req: true,  type: "text" },
    { f: "supplier_group", l: "Group",         req: false, type: "text", placeholder: "All Supplier Groups" },
  ],
  Warehouse: [
    { f: "warehouse_name", l: "Warehouse Name", req: true,  type: "text" },
    { f: "warehouse_type", l: "Type",           req: false, type: "text", placeholder: "Stores" },
  ],
};

const q         = ref("");
const open      = ref(false);
const inputEl   = ref(null);
const trigEl    = ref(null);
const dropStyle = ref({});

// Records created via quick-create that the parent hasn't refetched yet.
// Lets displayLabel show the friendly name immediately instead of the raw ID.
const _localCreated = ref([]);


const normalized = computed(() => {
  const vk = props.valueKey, lk = props.labelKey;
  const base = (props.options || []).map((o) => {
    if (typeof o === "string") return { value: o, label: o };
    const v = vk ? o[vk] : (o.value !== undefined ? o.value : (o.name !== undefined ? o.name : String(o)));
    const l = lk ? o[lk] : (o.label !== undefined ? o.label : (o.name !== undefined ? o.name : String(o)));
    // Spread the original so extras like { rate, standard_rate, customer_name, ... }
    // pass through to @select handlers in the parent.
    return { ...o, value: v ?? "", label: l ?? v ?? "" };
  });
  // Merge in just-created records that aren't yet in props.options
  const existing = new Set(base.map(o => String(o.value)));
  for (const c of _localCreated.value) {
    if (!existing.has(String(c.value))) base.unshift(c);
  }
  return base;
});

const displayLabel = computed(() => {
  if (!props.modelValue && props.modelValue !== 0) return "";
  const found = normalized.value.find((o) => String(o.value) === String(props.modelValue));
  return found ? found.label : props.modelValue;
});

const filtered = computed(() => {
  const qv = q.value.toLowerCase().trim();
  if (!qv) return normalized.value.slice(0, 150);
  const pre = [], con = [];
  normalized.value.forEach((o) => {
    const l = String(o.label || "").toLowerCase();
    if (l.startsWith(qv)) pre.push(o);
    else if (l.includes(qv)) con.push(o);
  });
  return [...pre, ...con].slice(0, 100);
});

const showCreate = computed(() => {
  if (!props.createable) return false;
  const qv = q.value.trim();
  if (props.staticCreate && !qv) return true;
  if (!qv) return false;
  return !normalized.value.some((o) => String(o.label).toLowerCase() === qv.toLowerCase());
});


function calcDropStyle() {
  if (!trigEl.value) return;
  const r = trigEl.value.getBoundingClientRect();
  const spaceBelow = window.innerHeight - r.bottom;
  const goUp = spaceBelow < 260 && r.top > 260;
  dropStyle.value = {
    position: "fixed",
    left:  r.left  + "px",
    width: r.width + "px",
    zIndex: 99999,
    ...(goUp
      ? { bottom: (window.innerHeight - r.top + 4) + "px" }
      : { top:    (r.bottom + 4) + "px" }),
  };
}

let _searchDebounce = null;
watch(q, (val) => {
  clearTimeout(_searchDebounce);
  _searchDebounce = setTimeout(() => emit("search", val), 200);
});

function openDD() {
  if (props.disabled) return;
  calcDropStyle();
  open.value = true;
  q.value = "";
  emit("search", "");
  nextTick(() => inputEl.value && inputEl.value.focus());
}

function pick(opt) {
  emit("update:modelValue", opt.value);
  emit("select", opt);
  open.value = false;
  q.value = "";
}

async function onClickCreate() {
  const typed = q.value.trim();
  open.value = false;
  if (props.createDoctype) {
    const { openCreate } = useQuickCreate();
    const record = await openCreate(props.createDoctype, typed);
    if (record) {
      // Stash the friendly label so displayLabel renders the name even before
      // the parent's next options refetch.
      _localCreated.value.push({ value: record.name, label: record.label || record.name });
      pick({ value: record.name, label: record.label });
    }
  } else {
    emit("create", typed);
  }
}

function onDoc(e) {
  if (!open.value) return;
  const trig = trigEl.value;
  const drop = document.querySelector(".ss-drop-teleport");
  if (trig && !trig.contains(e.target) && drop && !drop.contains(e.target)) {
    open.value = false;
  }
}

function onScrollOrResize(e) {
  if (!open.value) return;
  // Ignore scrolls that originate inside the dropdown itself (e.g. scrolling
  // the options list or the search input) — only close on scroll of the
  // page/ancestor containers behind the teleported dropdown.
  const drop = document.querySelector(".ss-drop-teleport");
  if (drop && e.target && drop.contains(e.target)) return;
  open.value = false;
}

onMounted(() => {
  document.addEventListener("pointerdown", onDoc, true);
  // Close on any scroll (capture phase catches inner overflow containers too)
  document.addEventListener("scroll", onScrollOrResize, { capture: true, passive: true });
  window.addEventListener("resize", onScrollOrResize, { passive: true });
});
onUnmounted(() => {
  document.removeEventListener("pointerdown", onDoc, true);
  document.removeEventListener("scroll", onScrollOrResize, { capture: true });
  window.removeEventListener("resize", onScrollOrResize);
});
</script>