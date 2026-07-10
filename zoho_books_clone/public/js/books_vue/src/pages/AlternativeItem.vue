<template>
<div class="sc-page">
  <div class="sc-sticky">
    <div class="sc-header">
      <div style="display:flex;align-items:center;gap:12px;">
        <span class="sc-title">Alternative Items</span>
        <span style="background:#f3f4f6;color:#6b7280;border-radius:12px;padding:3px 10px;font-size:13px;font-weight:600;">{{ total }}</span>
      </div>
      <button class="sc-save-btn" @click="router.push('/manufacturing/alternative-item/new')">+ New</button>
    </div>
  </div>

  <div class="sc-body">
    <div class="sc-list-card">
      <div style="padding:16px 20px;border-bottom:1px solid #e8ecf2;display:flex;gap:10px;">
        <input class="nim-input" style="max-width:280px;" placeholder="Search item code…" v-model="search" @input="loadList" />
      </div>

      <div v-if="loading" style="padding:40px;text-align:center;color:#9ca3af;">Loading…</div>
      <div v-else-if="!rows.length" style="padding:40px;text-align:center;color:#9ca3af;">No alternative items found.</div>
      <table v-else style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead>
          <tr style="background:#f9fafb;">
            <th style="text-align:left;padding:10px 16px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-size:12px;font-weight:600;">Original Item</th>
            <th style="text-align:left;padding:10px 16px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-size:12px;font-weight:600;">Alternative Item</th>
            <th style="text-align:right;padding:10px 16px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-size:12px;font-weight:600;">Conv. Factor</th>
            <th style="text-align:left;padding:10px 16px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-size:12px;font-weight:600;">UOM</th>
            <th style="text-align:center;padding:10px 16px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-size:12px;font-weight:600;">Default</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.name"
            class="sc-list-row"
            @click="router.push(`/manufacturing/alternative-item/${r.name}`)">
            <td style="padding:10px 16px;font-weight:600;color:#2563eb;">{{ r.item_code }}</td>
            <td style="padding:10px 16px;">{{ r.alternative_item_code }}</td>
            <td style="padding:10px 16px;text-align:right;">{{ r.conversion_factor }}</td>
            <td style="padding:10px 16px;">{{ r.uom || '—' }}</td>
            <td style="padding:10px 16px;text-align:center;">
              <span v-if="r.is_default" style="font-size:11px;padding:2px 8px;border-radius:10px;background:#dcfce7;color:#16a34a;font-weight:700;">Yes</span>
              <span v-else style="color:#d1d5db;">—</span>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="rows.length && total > rows.length" style="padding:12px 20px;text-align:center;">
        <button class="nim-btn" @click="loadMore" :disabled="loading">Load More</button>
      </div>
    </div>
  </div>
</div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { apiList } from "../api/client.js";
import { useToast } from "../composables/useToast.js";

const router = useRouter();
const { toast } = useToast();

const rows = ref([]);
const total = ref(0);
const loading = ref(true);
const search = ref("");
const page = ref(0);
const PAGE_SIZE = 50;

async function loadList(reset = true) {
  if (reset) page.value = 0;
  loading.value = true;
  try {
    const filters = search.value
      ? [["item_code", "like", `%${search.value}%`]]
      : [];
    const data = await apiList("Alternative Item", {
      fields: ["name", "item_code", "alternative_item_code", "conversion_factor", "uom", "is_default"],
      filters,
      limit: PAGE_SIZE,
      start: page.value * PAGE_SIZE,
      order: "item_code asc",
    });
    if (reset) {
      rows.value = data || [];
    } else {
      rows.value.push(...(data || []));
    }
    total.value = rows.value.length;
  } catch (e) {
    toast("Error loading alternatives: " + e.message, "error");
  }
  loading.value = false;
}

async function loadMore() {
  page.value++;
  await loadList(false);
}

onMounted(() => loadList());
</script>
