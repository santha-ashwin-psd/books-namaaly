<template>
<div class="sc-page">
  <div class="sc-sticky">
    <div class="sc-header">
      <div style="display:flex;align-items:center;gap:12px;">
        <span class="sc-title">Manufacturing Settings</span>
        <span v-if="saved" style="font-size:12px;color:#16a34a;font-weight:600;animation:fadeIn .3s;">Saved</span>
      </div>
      <button class="sc-save-btn" @click="save" :disabled="saving || loading">
        <span v-if="saving" style="display:inline-block;width:12px;height:12px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .6s linear infinite;margin-right:6px;"></span>
        {{ saving ? 'Saving…' : 'Save Settings' }}
      </button>
    </div>
  </div>

  <div v-if="loading" style="padding:60px;text-align:center;color:#9ca3af;">Loading settings…</div>
  <div v-else class="sc-body sc-body--narrow">
    <div class="sc-col-main">

      <!-- Warehouse Defaults -->
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon sc-card-icon--blue">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>
          </div>
          <div>
            <div class="sc-card-title">Default Warehouses</div>
            <div class="sc-card-subtitle">Pre-filled on new Work Orders. Can be overridden per document.</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-fg">
          <div class="nim-field">
            <label class="nim-label">Default Source Warehouse</label>
            <select class="nim-input" v-model="s.default_source_warehouse">
              <option value="">— None —</option>
              <option v-for="w in warehouses" :key="w.name" :value="w.name">{{ w.name }}</option>
            </select>
            <div class="sc-field-hint">Raw materials are drawn from here by default.</div>
          </div>
          <div class="nim-field">
            <label class="nim-label">Default WIP Warehouse</label>
            <select class="nim-input" v-model="s.default_wip_warehouse">
              <option value="">— None —</option>
              <option v-for="w in warehouses" :key="w.name" :value="w.name">{{ w.name }}</option>
            </select>
            <div class="sc-field-hint">Set this to enable the "Issue Materials" transfer step.</div>
          </div>
        </div>
        <div class="sc-fg" style="margin-top:14px;">
          <div class="nim-field">
            <label class="nim-label">Default Finished Goods Warehouse</label>
            <select class="nim-input" v-model="s.default_fg_warehouse">
              <option value="">— None —</option>
              <option v-for="w in warehouses" :key="w.name" :value="w.name">{{ w.name }}</option>
            </select>
            <div class="sc-field-hint">Manufactured goods are received here by default.</div>
          </div>
          <div class="nim-field">
            <label class="nim-label">Default Scrap Warehouse</label>
            <select class="nim-input" v-model="s.default_scrap_warehouse">
              <option value="">— None —</option>
              <option v-for="w in warehouses" :key="w.name" :value="w.name">{{ w.name }}</option>
            </select>
            <div class="sc-field-hint">Recoverable scrap / by-products go here.</div>
          </div>
        </div>
      </div>

      <!-- Work Order Defaults -->
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>
          </div>
          <div>
            <div class="sc-card-title">Work Order Defaults</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-fg">
          <div class="nim-field">
            <label class="nim-label">Over-Production Allowance (%)</label>
            <input type="number" class="nim-input" v-model="s.over_production_allowance_pct" min="0" max="100" step="0.01" />
            <div class="sc-field-hint">% above the planned qty that can be produced without error. 0 = strict.</div>
          </div>
          <div class="nim-field">
            <label class="nim-label">Backflush Raw Materials Based On</label>
            <select class="nim-input" v-model="s.backflush_raw_materials_based_on">
              <option value="BOM">BOM</option>
              <option value="Material Transferred for Manufacture">Material Transferred for Manufacture</option>
            </select>
            <div class="sc-field-hint">How raw material consumption qty is calculated at completion.</div>
          </div>
        </div>
        <div class="sc-fg sc-fg--three" style="margin-top:16px;">
          <label class="sc-toggle-row" style="padding:8px;background:none;">
            <input type="checkbox" v-model="s.auto_create_job_cards" :true-value="1" :false-value="0" style="margin-right:8px;"/>
            <span style="font-size:13px;font-weight:600;">Auto-Create Job Cards on Submit</span>
          </label>
          <label class="sc-toggle-row" style="padding:8px;background:none;">
            <input type="checkbox" v-model="s.allow_negative_stock" :true-value="1" :false-value="0" style="margin-right:8px;"/>
            <span style="font-size:13px;font-weight:600;">Allow Negative Stock</span>
          </label>
        </div>
      </div>

      <!-- BOM Defaults -->
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
          </div>
          <div>
            <div class="sc-card-title">BOM Defaults</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-fg">
          <div class="nim-field">
            <label class="nim-label">Default BOM Type</label>
            <select class="nim-input" v-model="s.default_bom_type">
              <option value="Manufacturing">Manufacturing</option>
              <option value="Packing">Packing</option>
              <option value="Sub-Assembly">Sub-Assembly</option>
            </select>
          </div>
        </div>
        <div class="sc-fg sc-fg--three" style="margin-top:16px;">
          <label class="sc-toggle-row" style="padding:8px;background:none;">
            <input type="checkbox" v-model="s.set_rate_of_sub_assembly_item_based_on_bom" :true-value="1" :false-value="0" style="margin-right:8px;"/>
            <span style="font-size:13px;font-weight:600;">Set Sub-Assembly Rate from BOM</span>
          </label>
        </div>
      </div>

      <!-- Capacity Planning -->
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
          </div>
          <div>
            <div class="sc-card-title">Capacity Planning</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-fg">
          <div class="nim-field">
            <label class="nim-label">Job Card Hours per Day</label>
            <input type="number" class="nim-input" v-model="s.job_card_hours_per_day" min="1" max="24" step="0.5" />
            <div class="sc-field-hint">Working hours per day used for operation duration estimates.</div>
          </div>
          <div class="nim-field">
            <label class="nim-label">Capacity Planning Horizon (Days)</label>
            <input type="number" class="nim-input" v-model="s.capacity_planning_for_days" min="1" step="1" />
            <div class="sc-field-hint">How many days ahead to plan production.</div>
          </div>
        </div>
      </div>

      <!-- Notifications -->
      <div class="sc-card">
        <div class="sc-card-header">
          <div class="sc-card-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
          </div>
          <div>
            <div class="sc-card-title">Notifications &amp; Alerts</div>
          </div>
        </div>
        <div class="sc-divider"></div>
        <div class="sc-fg sc-fg--three" style="margin-top:8px;">
          <label class="sc-toggle-row" style="padding:8px;background:none;">
            <input type="checkbox" v-model="s.warn_if_bom_not_default" :true-value="1" :false-value="0" style="margin-right:8px;"/>
            <span style="font-size:13px;font-weight:600;">Warn If BOM Is Not Default</span>
          </label>
          <label class="sc-toggle-row" style="padding:8px;background:none;">
            <input type="checkbox" v-model="s.warn_on_missing_job_cards" :true-value="1" :false-value="0" style="margin-right:8px;"/>
            <span style="font-size:13px;font-weight:600;">Warn on Incomplete Job Cards</span>
          </label>
        </div>
      </div>

    </div>
  </div>
</div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { apiCall } from "../api/client.js";
import { useToast } from "../composables/useToast.js";

const { toast } = useToast();

const loading = ref(true);
const saving = ref(false);
const saved = ref(false);
const warehouses = ref([]);

const s = ref({
  default_source_warehouse: "",
  default_wip_warehouse: "",
  default_fg_warehouse: "",
  default_scrap_warehouse: "",
  auto_create_job_cards: 1,
  over_production_allowance_pct: 0,
  allow_negative_stock: 0,
  backflush_raw_materials_based_on: "BOM",
  default_bom_type: "Manufacturing",
  set_rate_of_sub_assembly_item_based_on_bom: 0,
  job_card_hours_per_day: 8,
  capacity_planning_for_days: 30,
  warn_if_bom_not_default: 1,
  warn_on_missing_job_cards: 1,
});

onMounted(async () => {
  loading.value = true;
  try {
    // Load warehouses for dropdowns
    const whs = await apiCall("frappe.client.get_list", {
      doctype: "Warehouse",
      fields: ["name"],
      filters: [["is_group", "=", 0], ["disabled", "=", 0]],
      limit: 500,
      order_by: "name asc",
    });
    warehouses.value = whs || [];

    // Load current settings
    const data = await apiCall(
      "zoho_books_clone.manufacturing.doctype.manufacturing_settings.manufacturing_settings.get_manufacturing_defaults"
    );
    if (data) {
      Object.assign(s.value, data);
    }
  } catch (e) {
    toast("Error loading settings: " + e.message, "error");
  }
  loading.value = false;
});

async function save() {
  const pct = parseFloat(s.value.over_production_allowance_pct) || 0;
  if (pct < 0 || pct > 100) {
    return toast("Over-Production Allowance must be between 0 and 100%", "error");
  }
  const hrs = parseFloat(s.value.job_card_hours_per_day) || 0;
  if (hrs <= 0) {
    return toast("Job Card Hours per Day must be greater than 0", "error");
  }

  saving.value = true;
  saved.value = false;
  try {
    await apiCall("frappe.client.set_value", {
      doctype: "Manufacturing Settings",
      name: "Manufacturing Settings",
      fieldname: {
        default_source_warehouse: s.value.default_source_warehouse || "",
        default_wip_warehouse: s.value.default_wip_warehouse || "",
        default_fg_warehouse: s.value.default_fg_warehouse || "",
        default_scrap_warehouse: s.value.default_scrap_warehouse || "",
        auto_create_job_cards: s.value.auto_create_job_cards,
        over_production_allowance_pct: pct,
        allow_negative_stock: s.value.allow_negative_stock,
        backflush_raw_materials_based_on: s.value.backflush_raw_materials_based_on,
        default_bom_type: s.value.default_bom_type,
        set_rate_of_sub_assembly_item_based_on_bom: s.value.set_rate_of_sub_assembly_item_based_on_bom,
        job_card_hours_per_day: hrs,
        capacity_planning_for_days: parseInt(s.value.capacity_planning_for_days) || 30,
        warn_if_bom_not_default: s.value.warn_if_bom_not_default,
        warn_on_missing_job_cards: s.value.warn_on_missing_job_cards,
      },
    });
    saved.value = true;
    toast("Manufacturing Settings saved");
    setTimeout(() => { saved.value = false; }, 3000);
  } catch (e) {
    toast("Failed to save: " + e.message, "error");
  }
  saving.value = false;
}
</script>
