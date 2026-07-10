<template>
<div class="msx-page">
  <div class="msx-panel">

    <!-- Header -->
    <div class="msx-hdr">
      <div>
        <div class="msx-hdr-title">⚙️ Manufacturing Settings</div>
        <div class="msx-hdr-sub">Defaults and controls applied across BOMs, Work Orders, and Job Cards.</div>
      </div>
      <div style="display:flex;align-items:center;gap:10px;">
        <span v-if="saved" class="msx-saved">✓ Saved</span>
        <button class="msx-btn msx-btn-light" @click="save" :disabled="saving || loading">
          <span v-if="saving" class="msx-spinner"></span>
          <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13"/><polyline points="7 3 7 8 15 8"/></svg>
          {{ saving ? 'Saving…' : 'Save Settings' }}
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="msx-body">
      <div class="shimmer" style="height:120px;border-radius:10px;margin-bottom:16px"></div>
      <div class="shimmer" style="height:120px;border-radius:10px;margin-bottom:16px"></div>
      <div class="shimmer" style="height:120px;border-radius:10px"></div>
    </div>

    <!-- Body -->
    <div v-else class="msx-body">

      <!-- Warehouse Defaults -->
      <div class="msx-sect">
        <div class="msx-sect-hdr">
          <div class="msx-sect-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>
          </div>
          <div>
            <div class="msx-sect-title">Default Warehouses</div>
            <div class="msx-sect-sub">Pre-filled on new Work Orders. Can be overridden per document.</div>
          </div>
        </div>
        <div class="msx-fg">
          <div>
            <div class="msx-hf-label">Default Source Warehouse</div>
            <select class="msx-fi" v-model="s.default_source_warehouse" style="width:100%">
              <option value="">— None —</option>
              <option v-for="w in warehouses" :key="w.name" :value="w.name">{{ w.name }}</option>
            </select>
            <div class="msx-hint">Raw materials are drawn from here by default.</div>
          </div>
          <div>
            <div class="msx-hf-label">Default WIP Warehouse</div>
            <select class="msx-fi" v-model="s.default_wip_warehouse" style="width:100%">
              <option value="">— None —</option>
              <option v-for="w in warehouses" :key="w.name" :value="w.name">{{ w.name }}</option>
            </select>
            <div class="msx-hint">Set this to enable the "Issue Materials" transfer step.</div>
          </div>
          <div>
            <div class="msx-hf-label">Default Finished Goods Warehouse</div>
            <select class="msx-fi" v-model="s.default_fg_warehouse" style="width:100%">
              <option value="">— None —</option>
              <option v-for="w in warehouses" :key="w.name" :value="w.name">{{ w.name }}</option>
            </select>
            <div class="msx-hint">Manufactured goods are received here by default.</div>
          </div>
          <div>
            <div class="msx-hf-label">Default Scrap Warehouse</div>
            <select class="msx-fi" v-model="s.default_scrap_warehouse" style="width:100%">
              <option value="">— None —</option>
              <option v-for="w in warehouses" :key="w.name" :value="w.name">{{ w.name }}</option>
            </select>
            <div class="msx-hint">Recoverable scrap / by-products go here.</div>
          </div>
        </div>
      </div>

      <!-- Work Order Defaults -->
      <div class="msx-sect">
        <div class="msx-sect-hdr">
          <div class="msx-sect-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>
          </div>
          <div><div class="msx-sect-title">Work Order Defaults</div></div>
        </div>
        <div class="msx-fg">
          <div>
            <div class="msx-hf-label">Over-Production Allowance (%)</div>
            <input type="number" class="msx-fi msx-fi-mono" v-model="s.over_production_allowance_pct" min="0" max="100" step="0.01" style="width:100%"/>
            <div class="msx-hint">% above the planned qty that can be produced without error. 0 = strict.</div>
          </div>
          <div>
            <div class="msx-hf-label">Backflush Raw Materials Based On</div>
            <select class="msx-fi" v-model="s.backflush_raw_materials_based_on" style="width:100%">
              <option value="BOM">BOM</option>
              <option value="Material Transferred for Manufacture">Material Transferred for Manufacture</option>
            </select>
            <div class="msx-hint">How raw material consumption qty is calculated at completion.</div>
          </div>
        </div>
        <div class="msx-toggle-row">
          <label class="msx-toggle"><input type="checkbox" v-model="s.auto_create_job_cards" :true-value="1" :false-value="0"/> Auto-Create Job Cards on Submit</label>
          <label class="msx-toggle"><input type="checkbox" v-model="s.allow_negative_stock" :true-value="1" :false-value="0"/> Allow Negative Stock</label>
        </div>
      </div>

      <!-- BOM Defaults -->
      <div class="msx-sect">
        <div class="msx-sect-hdr">
          <div class="msx-sect-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
          </div>
          <div><div class="msx-sect-title">BOM Defaults</div></div>
        </div>
        <div class="msx-fg">
          <div>
            <div class="msx-hf-label">Default BOM Type</div>
            <select class="msx-fi" v-model="s.default_bom_type" style="width:100%">
              <option value="Manufacturing">Manufacturing</option>
              <option value="Packing">Packing</option>
              <option value="Sub-Assembly">Sub-Assembly</option>
            </select>
          </div>
        </div>
        <div class="msx-toggle-row">
          <label class="msx-toggle"><input type="checkbox" v-model="s.set_rate_of_sub_assembly_item_based_on_bom" :true-value="1" :false-value="0"/> Set Sub-Assembly Rate from BOM</label>
        </div>
      </div>

      <!-- Capacity Planning -->
      <div class="msx-sect">
        <div class="msx-sect-hdr">
          <div class="msx-sect-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
          </div>
          <div><div class="msx-sect-title">Capacity Planning</div></div>
        </div>
        <div class="msx-fg">
          <div>
            <div class="msx-hf-label">Job Card Hours per Day</div>
            <input type="number" class="msx-fi msx-fi-mono" v-model="s.job_card_hours_per_day" min="1" max="24" step="0.5" style="width:100%"/>
            <div class="msx-hint">Working hours per day used for operation duration estimates.</div>
          </div>
          <div>
            <div class="msx-hf-label">Capacity Planning Horizon (Days)</div>
            <input type="number" class="msx-fi msx-fi-mono" v-model="s.capacity_planning_for_days" min="1" step="1" style="width:100%"/>
            <div class="msx-hint">How many days ahead to plan production.</div>
          </div>
        </div>
      </div>

      <!-- Notifications -->
      <div class="msx-sect">
        <div class="msx-sect-hdr">
          <div class="msx-sect-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
          </div>
          <div><div class="msx-sect-title">Notifications &amp; Alerts</div></div>
        </div>
        <div class="msx-toggle-row" style="padding-top:0;">
          <label class="msx-toggle"><input type="checkbox" v-model="s.warn_if_bom_not_default" :true-value="1" :false-value="0"/> Warn If BOM Is Not Default</label>
          <label class="msx-toggle"><input type="checkbox" v-model="s.warn_on_missing_job_cards" :true-value="1" :false-value="0"/> Warn on Incomplete Job Cards</label>
        </div>
      </div>

    </div>

    <!-- Footer -->
    <div v-if="!loading" class="msx-footer">
      <span v-if="saved" class="msx-saved">✓ Settings saved</span>
      <div style="flex:1"></div>
      <button class="msx-btn msx-btn-mfg" @click="save" :disabled="saving || loading">
        <span v-if="saving" class="msx-spinner"></span>
        {{ saving ? 'Saving…' : 'Save Settings' }}
      </button>
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

<style scoped>
.msx-page {
  --bx-bg:#F3F4F6; --bx-surface:#FFFFFF; --bx-surf2:#F8F9FC; --bx-border:#E2E8F0;
  --bx-text:#1A1D23; --bx-muted:#868E96;
  --bx-green:#2F9E44; --bx-greenS:#EBFBEE;
  --bx-red:#C92A2A; --bx-redS:#FFF5F5;
  --bx-amber:#E67700; --bx-amberS:#FFF3BF;
  --bx-blue:#1971C2; --bx-blueS:#E7F5FF;
  --bx-mfg:#B45309; --bx-mfgL:#D97706; --bx-mfgS:#FFFBEB; --bx-mfgB:#92400E;
  --bx-radius:10px; --bx-rsm:6px;
  padding: 16px;
}
.msx-panel { max-width:880px; margin:0 auto; background:var(--bx-surface); border:1px solid var(--bx-border); border-radius:var(--bx-radius); overflow:hidden; display:flex; flex-direction:column; }

.msx-hdr { padding:18px 22px; background:linear-gradient(135deg, var(--bx-mfgB), var(--bx-mfg)); display:flex; align-items:flex-start; justify-content:space-between; gap:12px; }
.msx-hdr-title { font-size:18px; font-weight:700; color:#fff; margin-bottom:4px; }
.msx-hdr-sub { font-size:12.5px; color:rgba(255,255,255,.75); }
.msx-saved { font-size:12.5px; font-weight:600; color:#fff; background:rgba(255,255,255,.18); padding:4px 10px; border-radius:20px; animation:fadeIn .3s; }

.msx-body { padding:20px 22px; display:flex; flex-direction:column; gap:16px; }

/* ── Section cards ── */
.msx-sect { background:var(--bx-surf2); border:1px solid var(--bx-border); border-radius:var(--bx-radius); padding:16px 18px; }
.msx-sect-hdr { display:flex; align-items:flex-start; gap:10px; margin-bottom:14px; }
.msx-sect-icon { width:32px; height:32px; border-radius:8px; background:var(--bx-mfgS); color:var(--bx-mfg); display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.msx-sect-title { font-size:14px; font-weight:700; color:var(--bx-text); }
.msx-sect-sub { font-size:12px; color:var(--bx-muted); margin-top:2px; }

.msx-fg { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
@media (max-width:640px) { .msx-fg { grid-template-columns:1fr; } }
.msx-hf-label { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--bx-muted); margin-bottom:4px; }
.msx-hint { font-size:12px; color:var(--bx-muted); margin-top:5px; line-height:1.5; }

.msx-toggle-row { display:flex; gap:20px; flex-wrap:wrap; padding-top:14px; margin-top:14px; border-top:1px solid var(--bx-border); }
.msx-toggle { display:flex; align-items:center; gap:6px; font-size:12.5px; font-weight:600; color:var(--bx-text); cursor:pointer; }

.msx-footer { padding:12px 22px; border-top:1px solid var(--bx-border); background:var(--bx-surf2); display:flex; align-items:center; gap:8px; }

/* ── Buttons / inputs ── */
.msx-fi { border:1px solid #CDD5E0; border-radius:var(--bx-rsm); padding:7px 9px; font-size:13px; color:var(--bx-text); background:#fff; outline:none; }
.msx-fi:focus { border-color:var(--bx-mfg); box-shadow:0 0 0 3px rgba(180,83,9,.1); }
.msx-fi-mono { font-family:"DM Mono",monospace; }
select.msx-fi {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  padding-right: 30px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%239ca3af' stroke-width='2.5'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
}
.msx-btn { display:inline-flex; align-items:center; gap:6px; padding:8px 18px; border-radius:var(--bx-rsm); font-size:13px; font-weight:600; cursor:pointer; border:1px solid transparent; line-height:1; white-space:nowrap; }
.msx-btn:disabled { opacity:.6; cursor:not-allowed; }
.msx-btn-mfg { background:var(--bx-mfg); color:#fff; }
.msx-btn-mfg:hover:not(:disabled) { background:var(--bx-mfgB); }
.msx-btn-light { background:rgba(255,255,255,.92); color:var(--bx-mfgB); border:1px solid rgba(255,255,255,.3); }
.msx-btn-light:hover:not(:disabled) { background:#fff; }

.msx-spinner { display:inline-block;width:11px;height:11px;border:2px solid rgba(255,255,255,.35);border-top-color:currentColor;border-radius:50%;animation:spin .6s linear infinite; }
@keyframes spin { to { transform: rotate(360deg) } }
@keyframes fadeIn { from{opacity:0} to{opacity:1} }

.shimmer { background:linear-gradient(90deg,#f1f3f5 25%,#e9ecef 37%,#f1f3f5 63%); background-size:400% 100%; animation:shimmer 1.4s ease infinite; }
@keyframes shimmer { 0%{background-position:100% 50%} 100%{background-position:0 50%} }
</style>