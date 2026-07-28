<template>
<div class="cc-page">

  <!-- KPI strip -->
  <SummaryStrip :cards="kpiCards" />

  <!-- Toolbar -->
  <div class="sales-toolbar">
    <div class="sales-search">
      <span v-html="icon('search',14)"></span>
      <input v-model="ccSearch" class="sales-search-input" placeholder="Search cost centers…" />
    </div>
    <div class="sales-pills">
      <button v-for="t in TYPE_PILLS" :key="t" class="sales-pill" :class="{active:typeFilter===t}" @click="typeFilter=t">
        {{ t }}
        <span v-if="t!=='All'" class="sales-pill-count">{{ typeCounts[t]||0 }}</span>
      </button>
    </div>
    <div class="sales-actions">
      <div class="cc-view-toggle">
        <button :class="{active:viewMode==='tree'}" @click="setView('tree')" title="Tree view"><span v-html="icon('stack',14)"></span></button>
        <button :class="{active:viewMode==='list'}" @click="setView('list')" title="List view"><span v-html="icon('file',14)"></span></button>
      </div>
      <button class="sales-btn-ghost" @click="load" title="Refresh"><span v-html="icon('refresh',14)"></span></button>
      <button class="sales-btn-ghost" @click="exportCSV" title="Export CSV"><span v-html="icon('download',14)"></span> CSV</button>
      <button class="sales-btn-primary" @click="openAdd()" :disabled="!$canWrite('accounts')" :title="!$canWrite('accounts') ? 'Read-only access' : ''"><span v-html="icon('plus',13)"></span> New</button>
    </div>
  </div>

  <!-- Body: main pane (tree|list) + shared detail pane -->
  <div class="cc-body">

    <div class="cc-main" :class="{'cc-main--hidden': selected}">

      <!-- ════════ TREE VIEW ════════ -->
      <div v-if="viewMode==='tree'" class="cc-tree-card">
        <div class="cc-main-hdr">
          <span class="cc-main-count">{{ loading ? 'Loading…' : allCC.length + ' cost centers' }}</span>
          <div class="cc-hdr-actions">
            <button class="cc-icon-btn" @click="expandAll(true)" title="Expand all"><span v-html="icon('chevD',13)"></span></button>
            <button class="cc-icon-btn" @click="expandAll(false)" title="Collapse all"><span v-html="icon('chevU',13)"></span></button>
          </div>
        </div>
        <div class="cc-tree">
          <div v-if="loading" class="cc-loading">Loading…</div>
          <template v-else>
            <div v-for="node in visibleNodes" :key="node.name" class="cc-tree-row"
              :class="{active:selected===node.name}" @click="selectCC(node.name)">
              <div v-if="node.hasChildren" class="cc-tree-toggle" @click.stop="toggleCC(node.name)">
                <span class="cc-caret" :style="{transform:node.isOpen?'rotate(90deg)':'rotate(0deg)'}">&#9654;</span>
              </div>
              <div v-else class="cc-tree-spacer"></div>
              <div class="cc-tree-icon" :style="{background:node.color+'22',color:node.color,marginLeft:(node.depth*18)+'px'}">
                {{ CC_TYPE_ICONS[node.type]||'🏢' }}
              </div>
              <div class="cc-tree-body">
                <div class="cc-tree-name" :class="{group:node.is_group}" :style="{color:selected===node.name?'#1a6ef7':'#1A1D23'}">
                  {{ node.name }}
                  <span v-if="isOver(node)" class="cc-over-flag" title="Over budget">⚠</span>
                </div>
                <div v-if="!node.is_group && node.budget" class="cc-tree-bar">
                  <div class="cc-bar"><div class="cc-bar-fill" :style="{width:utilWidth(node)+'%',background:utilColor(node)}"></div></div>
                  <span class="cc-tree-spent">{{ fmtSigned(spentOf(node)) }}</span>
                </div>
                <div v-else-if="node.code" class="cc-tree-code">{{ node.code }}</div>
              </div>
              <span v-if="node.status==='Inactive'" class="cc-off-badge">Off</span>
            </div>
            <div v-if="!visibleNodes.length" class="cc-empty-inline">No cost centers found</div>
          </template>
        </div>
      </div>

      <!-- ════════ LIST VIEW ════════ -->
      <div v-else class="cc-list">
        <div class="inv-table-wrap">
          <table class="inv-table">
            <thead>
              <tr>
                <th class="sortable" @click="sortBy('name')">Name <span v-if="sortCol==='name'" class="sort-arrow">{{ sortArrow }}</span></th>
                <th>Type</th>
                <th class="col-hide-tablet">Parent</th>
                <th class="ta-r sortable" @click="sortBy('budget')">Budget <span v-if="sortCol==='budget'" class="sort-arrow">{{ sortArrow }}</span></th>
                <th class="ta-r sortable" @click="sortBy('spent')">Spent <span v-if="sortCol==='spent'" class="sort-arrow">{{ sortArrow }}</span></th>
                <th class="col-hide-tablet">Utilisation</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading" v-for="n in 6" :key="'s'+n" class="shimmer-row">
                <td v-for="c in 7" :key="c"><div class="shimmer" style="width:80%"></div></td>
              </tr>
              <template v-else>
                <tr v-for="cc in paged" :key="cc.name" class="inv-row" :class="{selected:selected===cc.name}" @click="selectCC(cc.name)">
                  <td data-label="Name" class="td-id">
                    <span class="inv-link">{{ cc.name }}</span>
                    <span v-if="cc.code" class="cc-row-code"> · {{ cc.code }}</span>
                  </td>
                  <td data-label="Type">{{ cc.is_group ? 'Group' : cc.type }}</td>
                  <td data-label="Parent" class="col-hide-tablet text-muted">{{ cc.parent || '—' }}</td>
                  <td data-label="Budget" class="ta-r">{{ cc.budget ? fmtINR(cc.budget) : '—' }}</td>
                  <td data-label="Spent" class="ta-r">{{ fmtSigned(spentOf(cc)) }}</td>
                  <td data-label="Utilisation" class="col-hide-tablet">
                    <div v-if="!cc.is_group && cc.budget" class="cc-tree-bar">
                      <div class="cc-bar"><div class="cc-bar-fill" :style="{width:utilWidth(cc)+'%',background:utilColor(cc)}"></div></div>
                      <span class="cc-util-pct" :style="{color:utilColor(cc)}">{{ utilRaw(cc) }}%</span>
                    </div>
                    <span v-else class="text-muted">—</span>
                  </td>
                  <td data-label="Status">
                    <span class="inv-status-badge" :class="cc.status==='Active'?'status-active':'status-inactive'">{{ cc.status }}</span>
                  </td>
                </tr>
                <tr v-if="!paged.length">
                  <td colspan="7" class="bk-empty-state">
                    <div class="bk-empty-inner">
                      <div class="bk-empty-illus" style="font-size:34px">🏢</div>
                      <p class="bk-empty-title">No cost centers found</p>
                      <p class="bk-empty-sub">Try a different search or filter, or create a new cost center.</p>
                      <button class="bk-empty-btn" @click="openAdd()"><span v-html="icon('plus',13)"></span> New Cost Center</button>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
        <div v-if="!loading && listSorted.length" class="list-pagination">
          <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="totalItems" />
        </div>
      </div>
    </div>

    <!-- ════════ SHARED DETAIL PANE ════════ -->
    <div class="cc-detail" :class="{'cc-detail--visible': selected}">
      <div class="cc-mobile-back">
        <button @click="selected=null" class="cc-back-btn"><span class="cc-back-arrow">&#8592;</span> Back to list</button>
      </div>

      <div v-if="!selectedCC" class="cc-detail-empty">
        <div class="cc-detail-empty-icon">🏢</div>
        <div class="cc-detail-empty-title">Select a cost center</div>
        <div class="cc-detail-empty-sub">Pick a cost center to see its budget, spend, and the transactions behind it.</div>
        <button class="b-btn b-btn-primary" :disabled="!$canWrite('accounts')" :title="!$canWrite('accounts') ? 'Read-only access' : ''" @click="openAdd()"><span v-html="icon('plus',13)"></span> Add Cost Center</button>
      </div>

      <template v-else>
        <div class="cc-detail-hdr">
          <div class="cc-detail-title">
            <div class="cc-detail-icon" :style="{background:selectedCC.color+'22',color:selectedCC.color}">{{ CC_TYPE_ICONS[selectedCC.type]||'🏢' }}</div>
            <div class="cc-detail-titletext">
              <div class="cc-detail-name">{{ selectedCC.name }}</div>
              <div class="cc-detail-meta">{{ selectedCC.is_group?'Group':selectedCC.type }}{{ selectedCC.code?' · '+selectedCC.code:'' }}{{ selectedCC.parent?' · under '+selectedCC.parent:'' }}</div>
            </div>
          </div>
          <div class="cc-detail-actions">
            <button class="b-btn b-btn-ghost" @click="openEdit(selectedCC.name)"><span v-html="icon('edit',13)"></span> Edit</button>
            <button class="cc-del-btn" @click="confirmDel(selectedCC.name)" title="Delete"><span v-html="icon('trash',14)"></span></button>
          </div>
        </div>

        <div class="cc-tabs">
          <button class="cc-tab" :class="{active:detailTab==='overview'}" @click="detailTab='overview'">Overview</button>
          <button class="cc-tab" :class="{active:detailTab==='transactions'}" @click="detailTab='transactions'">Transactions</button>
        </div>

        <!-- OVERVIEW TAB -->
        <div v-if="detailTab==='overview'" class="cc-detail-scroll">
          <div v-if="selectedCC.desc" class="cc-desc">{{ selectedCC.desc }}</div>

          <template v-if="!selectedCC.is_group">
            <div class="cc-stat-grid">
              <div class="cc-stat-box">
                <div class="cc-stat-lbl">{{ selectedCC.budget_period||'Annual' }} Budget</div>
                <div class="cc-stat-val" style="color:#3B5BDB">{{ selectedCC.budget?fmtINR(selectedCC.budget):'—' }}</div>
              </div>
              <div class="cc-stat-box">
                <div class="cc-stat-lbl">Spent ({{ periodLabel }})</div>
                <div class="cc-stat-val" :style="{color:utilColor(selectedCC)}">{{ fmtSigned(spentOf(selectedCC)) }}</div>
              </div>
              <div class="cc-stat-box">
                <div class="cc-stat-lbl">{{ remaining>=0?'Remaining':'Over Budget' }}</div>
                <div class="cc-stat-val" :style="{color:remaining>=0?'#2F9E44':'#C92A2A'}">{{ fmtINR(Math.abs(remaining)) }}</div>
              </div>
            </div>
            <div v-if="selectedCC.budget" class="cc-util">
              <div class="cc-util-hdr">
                <span>Budget utilisation</span>
                <span class="cc-util-num" :style="{color:utilColor(selectedCC)}">{{ utilRaw(selectedCC) }}%</span>
              </div>
              <div class="cc-bar cc-bar-lg"><div class="cc-bar-fill" :style="{width:utilWidth(selectedCC)+'%',background:utilColor(selectedCC)}"></div></div>
            </div>

            <div class="b-card cc-settings-card">
              <div class="cc-settings-hdr">Budget settings</div>
              <div class="cc-budget-grid">
                <div><div class="cc-kv-lbl">Period</div><div class="cc-kv-val">{{ selectedCC.budget_period||'Annual' }}</div></div>
                <div><div class="cc-kv-lbl">Alert at</div><div class="cc-kv-val">{{ selectedCC.alert_pct||80 }}%</div></div>
                <div><div class="cc-kv-lbl">Action</div><div class="cc-kv-val">{{ selectedCC.budget_action||'Warn' }}</div></div>
              </div>
            </div>
          </template>

          <template v-else>
            <div class="cc-stat-grid">
              <div class="cc-stat-box"><div class="cc-stat-lbl">Child Centers</div><div class="cc-stat-val">{{ ccChildren.length }}</div></div>
              <div class="cc-stat-box"><div class="cc-stat-lbl">Total Budget</div><div class="cc-stat-val" style="color:#3B5BDB">{{ fmtINR(childTotalBudget) }}</div></div>
              <div class="cc-stat-box"><div class="cc-stat-lbl">Total Spent</div><div class="cc-stat-val">{{ fmtSigned(childTotalSpent) }}</div></div>
            </div>
            <div v-if="ccChildren.length">
              <div class="cc-section-cap">Sub-centers expense allocation</div>
              <div v-for="c in ccChildren" :key="c.name" class="cc-alloc-row">
                <span class="cc-alloc-name">{{ c.name }}</span>
                <div class="cc-bar"><div class="cc-bar-fill" :style="{width:allocWidth(c)+'%',background:c.color}"></div></div>
                <span class="cc-alloc-amt">{{ fmtSigned(spentOf(c)) }}</span>
              </div>
            </div>
            <div v-else class="cc-txn-empty"><div class="cc-txn-empty-icon">📁</div><div>No child cost centers yet</div></div>
          </template>
        </div>

        <!-- TRANSACTIONS TAB -->
        <div v-else class="cc-detail-scroll">
          <div v-if="txnsLoading" class="cc-loading">Loading transactions…</div>
          <template v-else>
            <div v-if="!txns.length" class="cc-txn-empty">
              <div class="cc-txn-empty-icon">🧾</div>
              <div>No transactions in this {{ (selectedCC.budget_period||'Annual').toLowerCase() }} period</div>
            </div>
            <template v-else>
              <table class="cc-txn-table">
                <thead><tr><th>Date</th><th>Voucher</th><th>Account</th><th class="ta-r">Amount</th></tr></thead>
                <tbody>
                  <tr v-for="(t,i) in txns" :key="i">
                    <td class="cc-txn-date">{{ fmtDate(t.posting_date) }}</td>
                    <td>
                      <DocLink :doctype="t.voucher_type" :name="t.voucher_no" />
                      <div class="cc-vtype">{{ t.voucher_type }}</div>
                    </td>
                    <td class="cc-txn-acct">{{ t.account }}</td>
                    <td class="ta-r" :style="{color:(t.debit-t.credit)>=0?'#C92A2A':'#2F9E44'}">{{ fmtSigned(t.debit-t.credit) }}</td>
                  </tr>
                </tbody>
                <tfoot>
                  <tr><td colspan="3" class="cc-txn-total-lbl">Total spend ({{ periodLabel }})</td><td class="ta-r cc-txn-total-val">{{ fmtSigned(txnsTotal) }}</td></tr>
                </tfoot>
              </table>
            </template>
          </template>
        </div>
      </template>
    </div>
  </div>

  <!-- ════════ CREATE / EDIT DRAWER ════════ -->
  <Teleport to="body">
    <Transition name="cc-drawer">
    <div v-if="showDrawer" class="cc-drawer-bg" @click.self="closeDrawer">
      <div class="cc-drawer">
        <div class="cc-drawer-hdr">
          <div class="cc-drawer-hdr-left">
            <div class="cc-drawer-badge"><span v-html="icon('costcenter',18)"></span></div>
            <div>
              <div class="cc-drawer-title">{{ editing?'Edit Cost Center':'New Cost Center' }}</div>
              <div class="cc-drawer-sub">Track expenses by department or project</div>
            </div>
          </div>
          <button class="cc-drawer-x" @click="closeDrawer"><span v-html="icon('x',16)"></span></button>
        </div>

        <div class="cc-drawer-body">
          <div class="cc-section-title">Details</div>
          <div class="cc-fields">
            <div class="cc-field">
              <label class="cc-label">Cost Center Name <span class="cc-req">*</span></label>
              <input v-model="fForm.name" class="b-input" placeholder="e.g. Engineering, Sales, Project Alpha" :disabled="!!editing" />
            </div>
            <div class="cc-grid2">
              <div class="cc-field">
                <label class="cc-label">Cost Center Code</label>
                <input v-model="fForm.code" class="b-input" placeholder="e.g. ENG, SLS" />
              </div>
              <div class="cc-field">
                <label class="cc-label">Parent Cost Center</label>
                <select v-model="fForm.parent" class="b-input">
                  <option value="">— Root level —</option>
                  <option v-for="c in parentOptions" :key="c.name" :value="c.name">{{ c.name }}</option>
                </select>
              </div>
            </div>
            <div class="cc-grid2">
              <div class="cc-field">
                <label class="cc-label">Type</label>
                <select v-model="fForm.type" class="b-input">
                  <option value="Department">Department</option>
                  <option value="Project">Project</option>
                  <option value="Product">Product Line</option>
                  <option value="Region">Region / Branch</option>
                  <option value="Group">Group (parent only)</option>
                </select>
              </div>
              <div class="cc-field">
                <label class="cc-label">Colour Tag</label>
                <div class="cc-swatches">
                  <button type="button" v-for="c in CC_COLORS" :key="c" class="cc-swatch" :class="{active:fForm.color===c}" :style="{'--sw':c,background:c}" @click="fForm.color=c">
                    <span v-if="fForm.color===c" v-html="icon('check',12)"></span>
                  </button>
                </div>
              </div>
            </div>
            <div class="cc-field">
              <label class="cc-label">Description</label>
              <textarea v-model="fForm.desc" class="b-input" rows="2" style="resize:vertical" placeholder="What this cost center tracks…"></textarea>
            </div>
          </div>

          <template v-if="!fForm.is_group">
            <div class="cc-section-title cc-section-divided">Budget</div>
            <div class="cc-grid2">
              <div class="cc-field">
                <label class="cc-label">Budget Amount (₹)</label>
                <input v-model="fForm.budget" class="b-input" type="number" min="0" step="1000" placeholder="0" />
              </div>
              <div class="cc-field">
                <label class="cc-label">Budget Period</label>
                <select v-model="fForm.budget_period" class="b-input">
                  <option value="Annual">Annual</option>
                  <option value="Quarterly">Quarterly</option>
                  <option value="Monthly">Monthly</option>
                </select>
              </div>
            </div>
            <div class="cc-grid2">
              <div class="cc-field">
                <label class="cc-label">Budget Alert At (%)</label>
                <input v-model="fForm.alert_pct" class="b-input" type="number" min="0" max="100" />
              </div>
              <div class="cc-field">
                <label class="cc-label">Budget Action</label>
                <select v-model="fForm.budget_action" class="b-input">
                  <option value="Warn">Warn only</option>
                  <option value="Stop">Stop and warn</option>
                  <option value="None">No action</option>
                </select>
              </div>
            </div>
          </template>

          <div class="cc-section-title cc-section-divided">Settings</div>
          <div class="cc-grid2">
            <div class="cc-field">
              <label class="cc-label">Is Group?</label>
              <div class="cc-seg">
                <button type="button" class="cc-seg-btn" :class="{active:fForm.is_group===1}" @click="fForm.is_group=1">Yes</button>
                <button type="button" class="cc-seg-btn" :class="{active:fForm.is_group===0}" @click="fForm.is_group=0">No</button>
              </div>
            </div>
            <div class="cc-field">
              <label class="cc-label">Status</label>
              <div class="cc-seg">
                <button type="button" class="cc-seg-btn" :class="{active:fForm.status==='Active'}" @click="fForm.status='Active'">Active</button>
                <button type="button" class="cc-seg-btn cc-seg-btn--off" :class="{active:fForm.status==='Inactive'}" @click="fForm.status='Inactive'">Inactive</button>
              </div>
            </div>
          </div>
        </div>

        <div class="cc-drawer-foot">
          <button class="b-btn b-btn-ghost" @click="closeDrawer">Cancel</button>
          <button class="cc-save-btn" @click="saveCC" :disabled="saving">
            <span v-html="icon('check',14)"></span> {{ saving?'Saving…':editing?'Update':'Create' }}
          </button>
        </div>
      </div>
    </div>
    </Transition>
  </Teleport>
</div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from "vue";
import { apiGET, apiPOST, apiList, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { useConfirm } from "../composables/useConfirm.js";
import { usePagination } from "../composables/usePagination.js";
import { fmtDate } from "../utils/format.js";
import { icon } from "../utils/icons.js";
import SummaryStrip from "../components/SummaryStrip.vue";
import Pagination from "../components/Pagination.vue";
import DocLink from "../components/DocLink.vue";

const { toast } = useToast();
const { confirm } = useConfirm();

const CC_COLORS = ["#3B5BDB","#0C8599","#2F9E44","#E67700","#C92A2A","#2563eb","#D4537E","#1098AD","#495057"];
const CC_TYPE_ICONS = { Department: "🏢", Project: "📄", Product: "📦", Region: "🌍", Group: "📁" };
const TYPE_PILLS = ["All","Department","Project","Product","Region","Group"];

// Real actual-spend per cost center, summed from posted GL entries (keyed by
// the cost center's document name). Loaded from the backend on mount.
const spend = ref({});

const loading    = ref(true);
const allCC      = ref([]);
const selected   = ref(null);
const editing    = ref(null);
const expandedCC = ref([]);
const ccSearch   = ref("");
const typeFilter = ref("All");
const showDrawer = ref(false);
const saving     = ref(false);
const detailTab  = ref("overview");

// View mode persisted across visits
const viewMode = ref((() => { try { return localStorage.getItem("books.cc.view") === "list" ? "list" : "tree"; } catch { return "tree"; } })());
function setView(v) { viewMode.value = v; try { localStorage.setItem("books.cc.view", v); } catch {} }

const fForm = reactive({ name: "", code: "", parent: "", type: "Department", color: CC_COLORS[0], budget: "", budget_period: "Annual", alert_pct: 80, budget_action: "Warn", is_group: 0, status: "Active", desc: "", modified: "" });

// ── formatting helpers ───────────────────────────────────────────────────────
function fmtINR(v) { const n = Number(v || 0); if (n === 0) return "₹0"; return "₹" + Math.abs(n).toLocaleString("en-IN", { minimumFractionDigits: 0 }); }
function fmtSigned(v) { const n = Number(v || 0); return (n < 0 ? "-" : "") + "₹" + Math.abs(n).toLocaleString("en-IN", { minimumFractionDigits: 0 }); }
function spentOf(cc) { return spend.value[cc.name] || 0; }
// Utilisation never goes below 0 — a net-income cost center (negative net
// spend) means nothing was consumed against budget, i.e. 0% utilised.
function utilRaw(cc) { return cc.budget ? Math.max(0, Math.round(spentOf(cc) / cc.budget * 100)) : 0; }
function utilWidth(cc) { return cc.budget ? Math.min(100, Math.round(spentOf(cc) / cc.budget * 100)) : 0; }
function utilColor(cc) { const p = utilRaw(cc); return p >= 100 ? "#C92A2A" : p >= (cc.alert_pct || 80) ? "#E67700" : "#2F9E44"; }
function isOver(cc) { return !cc.is_group && cc.budget > 0 && spentOf(cc) >= cc.budget; }

// ── data load ────────────────────────────────────────────────────────────────
async function load() {
  loading.value = true;
  try {
    const ccs = await apiList("Cost Center", {
      fields: ["name", "cost_center_name", "cost_center_number", "parent_cost_center", "is_group", "disabled", "description", "budget", "budget_period", "alert_pct", "budget_action", "cc_type", "color_tag", "modified"],
      order: "name asc", limit: 200,
    }) || [];
    allCC.value = ccs.map((c) => ({
      name: c.name, code: c.cost_center_number || "", parent: c.parent_cost_center || "",
      type: c.cc_type || "Department", color: c.color_tag || "#3B5BDB", budget: Number(c.budget) || 0,
      budget_period: c.budget_period || "Annual", alert_pct: c.alert_pct || 80,
      budget_action: c.budget_action || "Warn", is_group: c.is_group ? 1 : 0,
      status: c.disabled ? "Inactive" : "Active", desc: c.description || "", modified: c.modified || "",
    }));
    // Real actual spend per cost center, summed from posted GL entries.
    try {
      const company = await resolveCompany();
      const map = await apiGET("zoho_books_clone.api.books_data.get_cost_center_spend", { company });
      spend.value = map && typeof map === "object" ? map : {};
    } catch { spend.value = {}; }
  } catch { allCC.value = []; }
  allCC.value.filter((c) => c.is_group).forEach((c) => { if (!expandedCC.value.includes(c.name)) expandedCC.value.push(c.name); });
  loading.value = false;
}

// ── KPI strip ────────────────────────────────────────────────────────────────
const kpiCards = computed(() => {
  const active = allCC.value.filter((c) => c.status === "Active").length;
  const totalBudget = allCC.value.reduce((s, c) => s + (c.is_group ? 0 : Number(c.budget || 0)), 0);
  const totalSpent = allCC.value.reduce((s, c) => s + (c.is_group ? 0 : spentOf(c)), 0);
  const over = allCC.value.filter((c) => isOver(c)).length;
  return [
    { label: "Cost Centers", value: allCC.value.length, tone: "accent" },
    { label: "Active", value: active, tone: "success" },
    { label: "Total Budget", value: fmtINR(totalBudget), tone: "default" },
    { label: "Total Spent", value: fmtSigned(totalSpent), tone: "info" },
    { label: "Over Budget", value: over, tone: over ? "danger" : "default", valueClass: over ? "red" : "" },
  ];
});

// ── filters ──────────────────────────────────────────────────────────────────
const typeCounts = computed(() => {
  const m = {};
  allCC.value.forEach((c) => { m[c.type] = (m[c.type] || 0) + 1; });
  return m;
});

function matchesFilters(c) {
  if (typeFilter.value !== "All" && c.type !== typeFilter.value) return false;
  const q = ccSearch.value.trim().toLowerCase();
  if (q && !((c.name || "").toLowerCase().includes(q) || (c.code || "").toLowerCase().includes(q))) return false;
  return true;
}
const listFiltered = computed(() => allCC.value.filter(matchesFilters));

// Tree view:
//  • Text search → flat list of matches (a search ignores hierarchy).
//  • Type filter → keep the hierarchy but prune to subtrees that contain a
//    matching node, so ancestors (the parent group) stay at the top and
//    expand/collapse keeps working.
const visibleNodes = computed(() => {
  const q = ccSearch.value.trim().toLowerCase();
  if (q) {
    return allCC.value
      .filter((c) => (typeFilter.value === "All" || c.type === typeFilter.value)
        && ((c.name || "").toLowerCase().includes(q) || (c.code || "").toLowerCase().includes(q)))
      .map((c) => ({ ...c, depth: 0, hasChildren: allCC.value.some((x) => x.parent === c.name), isOpen: false }));
  }

  const typeOk = (c) => typeFilter.value === "All" || c.type === typeFilter.value;
  const subtreeOk = (name) => {
    const node = allCC.value.find((c) => c.name === name);
    if (node && typeOk(node)) return true;
    return allCC.value.some((c) => c.parent === name && subtreeOk(c.name));
  };

  const result = [];
  (function walk(parent, depth) {
    allCC.value.filter((c) => (c.parent || "") === (parent || "")).forEach((c) => {
      if (typeFilter.value !== "All" && !subtreeOk(c.name)) return;
      const hasChildren = allCC.value.some((x) => x.parent === c.name);
      const isOpen = expandedCC.value.includes(c.name);
      result.push({ ...c, depth, hasChildren, isOpen });
      if (isOpen && hasChildren) walk(c.name, depth + 1);
    });
  })("", 0);
  return result;
});

function toggleCC(name) { const i = expandedCC.value.indexOf(name); if (i >= 0) expandedCC.value.splice(i, 1); else expandedCC.value.push(name); }
function expandAll(open) { if (open) allCC.value.forEach((c) => { if (!expandedCC.value.includes(c.name)) expandedCC.value.push(c.name); }); else expandedCC.value = []; }

// ── list sort + pagination ───────────────────────────────────────────────────
const sortCol = ref("name");
const sortDir = ref("asc");
const sortArrow = computed(() => (sortDir.value === "asc" ? "▲" : "▼"));
function sortBy(col) { if (sortCol.value === col) sortDir.value = sortDir.value === "asc" ? "desc" : "asc"; else { sortCol.value = col; sortDir.value = "asc"; } }
const listSorted = computed(() => {
  const col = sortCol.value;
  return [...listFiltered.value].sort((a, b) => {
    let av, bv;
    if (col === "spent") { av = spentOf(a); bv = spentOf(b); }
    else if (col === "budget") { av = Number(a.budget || 0); bv = Number(b.budget || 0); }
    else { av = a[col] ?? ""; bv = b[col] ?? ""; }
    const c = typeof av === "number" ? av - bv : String(av).localeCompare(String(bv));
    return sortDir.value === "asc" ? c : -c;
  });
});
const { page, pageSize, paged, totalItems } = usePagination(listSorted, { storageKey: "costcenters" });

// ── selection + detail ───────────────────────────────────────────────────────
function selectCC(name) { selected.value = name; detailTab.value = "overview"; txns.value = []; }

const selectedCC = computed(() => allCC.value.find((c) => c.name === selected.value) || null);
const ccChildren = computed(() => (selectedCC.value ? allCC.value.filter((c) => c.parent === selectedCC.value.name) : []));
const childTotalBudget = computed(() => ccChildren.value.reduce((s, c) => s + Number(c.budget || 0), 0));
const childTotalSpent = computed(() => ccChildren.value.reduce((s, c) => s + spentOf(c), 0));
// Only positive net spend consumes budget — net income (negative spend) leaves
// the full budget remaining rather than inflating it past 100%.
const remaining = computed(() => (selectedCC.value ? selectedCC.value.budget - Math.max(0, spentOf(selectedCC.value)) : 0));
const periodLabel = computed(() => { const p = selectedCC.value?.budget_period || "Annual"; return p === "Monthly" ? "MTD" : p === "Quarterly" ? "QTD" : "YTD"; });
function allocWidth(c) { const max = Math.max(1, ...ccChildren.value.map((x) => spentOf(x))); return Math.round(spentOf(c) / max * 100); }

// ── transactions drill-down ──────────────────────────────────────────────────
const txns = ref([]);
const txnsLoading = ref(false);
const txnsTotal = computed(() => txns.value.reduce((s, t) => s + (Number(t.debit || 0) - Number(t.credit || 0)), 0));

async function loadTxns() {
  if (!selectedCC.value) { txns.value = []; return; }
  txnsLoading.value = true;
  try {
    const company = await resolveCompany();
    const rows = await apiGET("zoho_books_clone.api.books_data.get_cost_center_transactions", {
      cost_center: selectedCC.value.name, company, period: selectedCC.value.budget_period || "Annual", limit: 100,
    });
    txns.value = Array.isArray(rows) ? rows : [];
  } catch { txns.value = []; }
  txnsLoading.value = false;
}
watch(detailTab, (t) => { if (t === "transactions" && !txns.value.length) loadTxns(); });

// ── create / edit ────────────────────────────────────────────────────────────
const parentOptions = computed(() => allCC.value.filter((c) => c.name !== fForm.name));

function openAdd(parentName) {
  editing.value = null;
  Object.assign(fForm, { name: "", code: "", parent: parentName || "", type: "Department", color: CC_COLORS[0], budget: "", budget_period: "Annual", alert_pct: 80, budget_action: "Warn", is_group: 0, status: "Active", desc: "", modified: "" });
  showDrawer.value = true;
}
function openEdit(name) {
  const cc = allCC.value.find((c) => c.name === name);
  if (!cc) return;
  editing.value = name;
  // Only assign the fields we explicitly use — never spread the full cc object,
  // as it may contain Frappe system fields (creation, owner, etc.) that would
  // leak into the save payload and cause "Value cannot be changed" errors.
  Object.assign(fForm, {
    name: cc.name, code: cc.code || "", parent: cc.parent || "",
    type: cc.type || "Department", color: cc.color || CC_COLORS[0],
    budget: cc.budget || "", budget_period: cc.budget_period || "Annual",
    alert_pct: cc.alert_pct || 80, budget_action: cc.budget_action || "Warn",
    is_group: cc.is_group || 0, status: cc.status || "Active",
    desc: cc.desc || "", modified: cc.modified || "",
  });
  showDrawer.value = true;
}
function closeDrawer() { showDrawer.value = false; editing.value = null; }

async function saveCC() {
  if (!fForm.name.trim()) { toast("Cost Center Name is required", "error"); return; }
  if (!fForm.parent && !fForm.is_group) { toast("A root-level cost center (no parent) must be marked as a Group. Enable \"Is Group\" in the Settings section.", "error"); return; }
  saving.value = true;
  const data = { ...fForm, budget: Number(fForm.budget) || 0 };
  const company = await resolveCompany();
  if (!company) { toast("No company configured. Please set a default company in Books Settings.", "error"); saving.value = false; return; }
  try {
    if (editing.value) {
      // Use set_value instead of save — save does an internal get+merge which
      // can trip the "Value cannot be changed for Created On" guard when Frappe
      // compares the incoming payload against the stored doc. set_value only
      // updates the fields we explicitly pass, never touching system fields.
      await apiPOST("frappe.client.set_value", {
        doctype: "Cost Center",
        name: editing.value,
        fieldname: JSON.stringify({
          cost_center_number: data.code || "",
          parent_cost_center: data.parent || "",
          is_group: data.is_group,
          budget: data.budget,
          description: data.desc || "",
          cc_type: data.type,
          color_tag: data.color,
          budget_period: data.budget_period,
          alert_pct: Number(data.alert_pct) || 80,
          budget_action: data.budget_action,
          disabled: data.status === "Inactive" ? 1 : 0,
        }),
      });
    } else {
      await apiPOST("frappe.client.insert", {
        doc: JSON.stringify({
          doctype: "Cost Center",
          cost_center_name: data.name,
          cost_center_number: data.code || "",
          parent_cost_center: data.parent || "",
          is_group: data.is_group,
          company,
          budget: data.budget,
          description: data.desc || "",
          cc_type: data.type,
          color_tag: data.color,
          budget_period: data.budget_period,
          alert_pct: Number(data.alert_pct) || 80,
          budget_action: data.budget_action,
          disabled: data.status === "Inactive" ? 1 : 0,
        }),
      });
    }
    await load();
    toast(editing.value ? "Cost center updated" : "Cost center created");
    saving.value = false;
    closeDrawer();
  } catch (e) {
    toast("Error saving cost center: " + (e.message || e), "error");
    saving.value = false;
  }
}

// ── delete ───────────────────────────────────────────────────────────────────
async function confirmDel(name) {
  const ok = await confirm({
    title: "Delete Cost Center?",
    body: `"${name}" will be permanently removed. This cannot be undone.`,
    okLabel: "Yes, delete", cancelLabel: "Keep it", okStyle: "danger",
  });
  if (!ok) return;
  try {
    await apiPOST("frappe.client.delete", { doctype: "Cost Center", name });
    if (selected.value === name) selected.value = null;
    await load();
    toast("Deleted");
  } catch (e) { toast("Error: " + (e.message || e), "error"); }
}

// ── CSV export ───────────────────────────────────────────────────────────────
function exportCSV() {
  const rows = listSorted.value;
  if (!rows.length) { toast("Nothing to export", "error"); return; }
  const head = ["Name", "Type", "Parent", "Budget", "Spent", "Utilisation %", "Status"];
  const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const lines = [head.map(esc).join(",")];
  for (const c of rows) {
    lines.push([c.name, c.is_group ? "Group" : c.type, c.parent || "", Number(c.budget || 0).toFixed(2), Number(spentOf(c)).toFixed(2), utilRaw(c), c.status].map(esc).join(","));
  }
  const blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `cost_centers_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click(); URL.revokeObjectURL(url);
  toast(`CSV exported — ${rows.length} cost center(s)`);
}

onMounted(load);
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   Cost Centers — page shell
   ═══════════════════════════════════════════════════════════ */
.cc-page   { display:flex; flex-direction:column; height:calc(100vh - 56px); overflow:hidden; padding:16px; gap:12px; background:#f5f6f8; box-sizing:border-box; }
.cc-body   { display:flex; flex:1; gap:12px; overflow:hidden; min-height:0; }
.cc-main   { flex:1; min-width:0; display:flex; flex-direction:column; overflow:hidden; }

/* View toggle (segmented) */
.cc-view-toggle { display:inline-flex; border:1px solid #e8ecf0; border-radius:6px; overflow:hidden; }
.cc-view-toggle button { border:none; background:#fff; padding:6px 10px; cursor:pointer; color:#6b7280; display:inline-flex; align-items:center; }
.cc-view-toggle button.active { background:#eaf1ff; color:#1a6ef7; }
.cc-view-toggle button + button { border-left:1px solid #e8ecf0; }

/* ── Tree card ── */
.cc-tree-card { display:flex; flex-direction:column; flex:1; min-height:0; background:#fff; border:1px solid #e5e7eb; border-radius:10px; overflow:hidden; }
.cc-main-hdr  { padding:10px 14px; border-bottom:1px solid #eef0f3; display:flex; align-items:center; justify-content:space-between; background:#f9f9fb; flex-shrink:0; }
.cc-main-count { font-size:12px; font-weight:700; letter-spacing:.4px; text-transform:uppercase; color:#868E96; }
.cc-hdr-actions { display:flex; gap:6px; }
.cc-icon-btn  { border:1px solid #E2E8F0; border-radius:5px; padding:4px 7px; background:#fff; cursor:pointer; color:#868E96; display:inline-flex; align-items:center; }
.cc-icon-btn:hover { border-color:#374151; color:#374151; }
.cc-tree      { overflow-y:auto; flex:1; }
.cc-loading   { padding:20px; text-align:center; color:#868E96; font-size:13px; }
.cc-empty-inline { padding:24px; text-align:center; color:#868E96; font-size:13px; }

/* Tree rows */
.cc-tree-row    { display:flex; align-items:center; border-bottom:1px solid #F8F9FC; cursor:pointer; transition:background .12s; user-select:none; border-left:3px solid transparent; }
.cc-tree-row:hover  { background:#f8faff; }
.cc-tree-row.active { background:rgba(26,110,247,.07); border-left-color:#1a6ef7; }
.cc-tree-toggle { width:20px; height:38px; display:flex; align-items:center; justify-content:center; flex-shrink:0; color:#868E96; cursor:pointer; margin-left:4px; }
.cc-caret       { display:inline-block; transition:transform .15s; font-size:10px; }
.cc-tree-spacer { width:24px; flex-shrink:0; }
.cc-tree-icon   { width:22px; height:22px; border-radius:5px; display:flex; align-items:center; justify-content:center; font-size:11px; flex-shrink:0; margin-right:8px; }
.cc-tree-body   { flex:1; padding:7px 8px 7px 0; min-width:0; }
.cc-tree-name   { font-size:13px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; display:flex; align-items:center; gap:5px; }
.cc-tree-name.group { font-weight:600; }
.cc-over-flag   { color:#C92A2A; font-size:11px; }
.cc-tree-code   { font-size:10.5px; color:#868E96; margin-top:1px; }
.cc-tree-bar    { display:flex; align-items:center; gap:7px; margin-top:4px; }
.cc-tree-spent  { font-size:10.5px; color:#868E96; white-space:nowrap; flex-shrink:0; }
.cc-off-badge   { font-size:10.5px; font-weight:600; padding:1px 7px; border-radius:10px; background:#F1F3F5; color:#868E96; margin-right:8px; flex-shrink:0; }

/* Utilisation bars */
.cc-bar       { flex:1; background:#E8ECF0; border-radius:20px; height:6px; overflow:hidden; min-width:40px; }
.cc-bar-lg    { height:8px; }
.cc-bar-fill  { height:100%; border-radius:20px; transition:width .4s ease; }
.cc-util-pct  { font-size:11px; font-weight:600; flex-shrink:0; }

/* ── List view ── */
.cc-list      { display:flex; flex-direction:column; flex:1; min-height:0; }
.cc-list .inv-table-wrap { flex:1; overflow:auto; }
.cc-row-code  { color:#868E96; font-size:12px; }

/* ── Detail pane ── */
.cc-detail    { width:430px; flex-shrink:0; display:flex; flex-direction:column; background:#fff; border:1px solid #e5e7eb; border-radius:10px; overflow:hidden; }
.cc-detail-empty { display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; text-align:center; color:#868E96; padding:40px 24px; }
.cc-detail-empty-icon  { font-size:40px; margin-bottom:12px; }
.cc-detail-empty-title { font-size:15px; font-weight:600; color:#1A1D23; margin-bottom:6px; }
.cc-detail-empty-sub   { font-size:13px; margin-bottom:20px; max-width:260px; line-height:1.5; }

.cc-detail-hdr   { padding:14px 18px; border-bottom:1px solid #E2E8F0; display:flex; align-items:flex-start; justify-content:space-between; gap:10px; flex-shrink:0; }
.cc-detail-title { display:flex; align-items:center; gap:10px; min-width:0; }
.cc-detail-icon  { width:36px; height:36px; border-radius:9px; display:flex; align-items:center; justify-content:center; font-size:18px; flex-shrink:0; }
.cc-detail-titletext { min-width:0; }
.cc-detail-name  { font-size:15px; font-weight:700; color:#1A1D23; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.cc-detail-meta  { font-size:12px; color:#868E96; }
.cc-detail-actions { display:flex; gap:8px; flex-shrink:0; }
.cc-del-btn      { border:1px solid rgba(201,42,42,.3); border-radius:5px; cursor:pointer; padding:5px 7px; display:inline-flex; color:#C92A2A; background:none; }
.cc-del-btn:hover { background:#fee2e2; }

/* Tabs */
.cc-tabs   { display:flex; gap:4px; padding:0 18px; border-bottom:1px solid #E2E8F0; flex-shrink:0; }
.cc-tab    { border:none; background:none; padding:10px 4px; margin-right:14px; font-size:13px; font-weight:600; color:#868E96; cursor:pointer; border-bottom:2px solid transparent; margin-bottom:-1px; }
.cc-tab.active { color:#1a6ef7; border-bottom-color:#1a6ef7; }

.cc-detail-scroll { flex:1; overflow-y:auto; padding:18px; }
.cc-desc   { font-size:13px; color:#868E96; margin-bottom:16px; line-height:1.5; }

/* Stat grid */
.cc-stat-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-bottom:16px; }
.cc-stat-box  { background:#F8F9FC; border:1px solid #E2E8F0; border-radius:8px; padding:11px 12px; }
.cc-stat-lbl  { font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:.4px; color:#868E96; margin-bottom:4px; }
.cc-stat-val  { font-size:16px; font-weight:700; }

/* Utilisation */
.cc-util      { margin-bottom:18px; }
.cc-util-hdr  { display:flex; justify-content:space-between; font-size:12px; color:#868E96; margin-bottom:6px; }
.cc-util-num  { font-weight:700; }

/* Budget settings card */
.cc-settings-card { padding:0; overflow:hidden; }
.cc-settings-hdr  { padding:11px 16px; border-bottom:1px solid #E2E8F0; font-size:13px; font-weight:600; }
.cc-budget-grid   { padding:14px 16px; display:grid; grid-template-columns:1fr 1fr 1fr; gap:14px; font-size:13px; }
.cc-kv-lbl   { color:#868E96; font-size:11.5px; margin-bottom:3px; }
.cc-kv-val   { font-weight:500; }

/* Group allocation */
.cc-section-cap { font-size:11px; font-weight:700; letter-spacing:.5px; text-transform:uppercase; color:#868E96; margin-bottom:10px; }
.cc-alloc-row   { display:flex; align-items:center; gap:10px; margin-bottom:8px; }
.cc-alloc-name  { font-size:12.5px; width:120px; flex-shrink:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.cc-alloc-amt   { font-size:12px; color:#868E96; width:70px; text-align:right; flex-shrink:0; }

/* Transactions */
.cc-txn-empty   { display:flex; flex-direction:column; align-items:center; gap:8px; padding:40px 20px; color:#868E96; font-size:13px; text-align:center; }
.cc-txn-empty-icon { font-size:32px; }
.cc-txn-table   { width:100%; border-collapse:collapse; font-size:12.5px; }
.cc-txn-table th { text-align:left; padding:8px 8px; border-bottom:2px solid #e8ecf0; font-size:10.5px; font-weight:600; color:#6b7280; text-transform:uppercase; letter-spacing:.04em; }
.cc-txn-table td { padding:9px 8px; border-bottom:1px solid #f0f2f5; vertical-align:top; }
.cc-txn-date    { white-space:nowrap; color:#374151; }
.cc-txn-acct    { color:#374151; }
.cc-vlink       { color:#1a6ef7; font-weight:600; text-decoration:none; }
.cc-vlink:hover { text-decoration:underline; }
.cc-vtype       { font-size:10.5px; color:#9ca3af; margin-top:2px; }
.cc-txn-total-lbl { text-align:right; font-weight:700; padding-top:10px; }
.cc-txn-total-val { font-weight:700; padding-top:10px; }
.ta-r { text-align:right; }
.text-muted { color:#9ca3af; }

/* ═══════════════════════════════════════════════════════════
   Drawer (create / edit)
   ═══════════════════════════════════════════════════════════ */
.cc-drawer-bg  { position:fixed; inset:0; z-index:9000; background:rgba(15,23,42,.45); display:flex; justify-content:flex-end; backdrop-filter:blur(3px); }
.cc-drawer     { width:480px; max-width:95vw; height:100%; background:#fff; display:flex; flex-direction:column; box-shadow:-24px 0 70px rgba(15,23,42,.22); }

/* Header — light, modern, with a gradient icon badge (matches page card headers) */
.cc-drawer-hdr { background:linear-gradient(180deg,#f6f9ff,#fff); border-bottom:1px solid #eef0f3; padding:18px 22px; display:flex; align-items:center; justify-content:space-between; gap:12px; flex-shrink:0; }
.cc-drawer-hdr-left { display:flex; align-items:center; gap:12px; min-width:0; }
.cc-drawer-badge { width:40px; height:40px; border-radius:11px; flex-shrink:0; display:flex; align-items:center; justify-content:center; color:#fff;
  background:linear-gradient(135deg,#2f74f5,#1a6ef7); box-shadow:0 4px 12px rgba(26,110,247,.32), inset 0 1px 0 rgba(255,255,255,.2); }
.cc-drawer-title { color:#1A1D23; font-size:16px; font-weight:700; }
.cc-drawer-sub   { color:#868E96; font-size:12px; margin-top:2px; }
.cc-drawer-x   { background:#f1f5f9; border:none; cursor:pointer; width:32px; height:32px; border-radius:8px; color:#64748b; display:flex; align-items:center; justify-content:center; transition:background .15s,color .15s; flex-shrink:0; }
.cc-drawer-x:hover { background:#e2e8f0; color:#334155; }
.cc-drawer-body { flex:1; overflow-y:auto; padding:22px; }
.cc-drawer-foot { padding:16px 22px; border-top:1px solid #E2E8F0; display:flex; justify-content:flex-end; gap:10px; background:#F8F9FC; flex-shrink:0; }

.cc-section-title { display:flex; align-items:center; gap:7px; font-size:11px; font-weight:700; letter-spacing:.6px; text-transform:uppercase; color:#64748b; margin-bottom:12px; }
.cc-section-title::before { content:""; width:3px; height:12px; border-radius:2px; background:linear-gradient(180deg,#2f74f5,#1a6ef7); }
.cc-section-divided { margin-top:22px; padding-top:20px; border-top:1px solid #eef0f3; }
.cc-fields { display:grid; gap:14px; margin-bottom:14px; }
.cc-grid2  { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:12px; }
.cc-field  { min-width:0; }
.cc-label  { display:block; font-size:11.5px; font-weight:600; color:#475569; margin-bottom:5px; }
.cc-req    { color:#C92A2A; }

/* Modern inputs inside the drawer */
.cc-drawer-body .b-input {
  width:100%; box-sizing:border-box; border:1px solid #e2e8f0; border-radius:9px;
  padding:9px 11px; font-size:13px; color:#1A1D23; background:#fff;
  transition:border-color .15s, box-shadow .15s; font-family:inherit;
}
.cc-drawer-body .b-input:hover:not(:disabled) { border-color:#cbd5e1; }
.cc-drawer-body .b-input:focus { border-color:#1a6ef7; box-shadow:0 0 0 3px rgba(26,110,247,.13); outline:none; }
.cc-drawer-body .b-input:disabled { background:#f8fafc; color:#94a3b8; cursor:not-allowed; }

/* Colour swatches */
.cc-swatches { display:flex; gap:9px; flex-wrap:wrap; margin-top:6px; }
.cc-swatch  { width:26px; height:26px; border-radius:50%; cursor:pointer; transition:transform .12s, box-shadow .15s; flex-shrink:0;
  border:2px solid #fff; box-shadow:0 0 0 1px #e2e8f0; display:flex; align-items:center; justify-content:center; color:#fff; padding:0; }
.cc-swatch:hover { transform:scale(1.12); }
.cc-swatch.active { box-shadow:0 0 0 2px var(--sw); transform:scale(1.05); }

/* Segmented toggle (Is Group / Status) */
.cc-seg     { display:inline-flex; width:100%; background:#f1f5f9; border:1px solid #e2e8f0; border-radius:9px; padding:3px; gap:3px; margin-top:1px; }
.cc-seg-btn { flex:1; border:none; background:none; cursor:pointer; padding:7px 10px; border-radius:7px; font-size:12.5px; font-weight:600; color:#64748b; transition:background .15s, color .15s, box-shadow .15s; font-family:inherit; }
.cc-seg-btn:hover:not(.active) { color:#334155; }
.cc-seg-btn.active { background:#fff; color:#1a6ef7; box-shadow:0 1px 3px rgba(15,23,42,.12); }
.cc-seg-btn--off.active { color:#64748b; }

/* Footer primary button — gradient, matches page accent */
.cc-save-btn { display:inline-flex; align-items:center; justify-content:center; gap:6px; min-width:120px;
  border:none; border-radius:9px; padding:9px 18px; font-size:13px; font-weight:600; color:#fff; cursor:pointer;
  background:linear-gradient(135deg,#2f74f5,#1a6ef7); box-shadow:0 4px 12px rgba(26,110,247,.28), inset 0 1px 0 rgba(255,255,255,.18);
  transition:box-shadow .18s, transform .18s, filter .18s; }
.cc-save-btn:hover:not(:disabled) { filter:brightness(1.04); transform:translateY(-1px); box-shadow:0 6px 18px rgba(26,110,247,.36); }
.cc-save-btn:active:not(:disabled) { transform:translateY(0); }
.cc-save-btn:disabled { opacity:.6; cursor:not-allowed; }

/* Slide-in / fade transition */
.cc-drawer-enter-active, .cc-drawer-leave-active { transition:opacity .25s ease; }
.cc-drawer-enter-active .cc-drawer, .cc-drawer-leave-active .cc-drawer { transition:transform .3s cubic-bezier(.4,0,.2,1); }
.cc-drawer-enter-from, .cc-drawer-leave-to { opacity:0; }
.cc-drawer-enter-from .cc-drawer, .cc-drawer-leave-to .cc-drawer { transform:translateX(100%); }

/* Mobile back button — hidden on desktop */
.cc-mobile-back { display:none; }

/* ═══════════════════════════════════════════════════════════
   RESPONSIVE
   ═══════════════════════════════════════════════════════════ */
@media (max-width: 1023px) {
  .cc-detail { width:360px; }
}

@media (max-width: 767px) {
  .cc-page { height:auto; min-height:calc(100vh - 56px); overflow:auto; padding:12px; }
  .cc-body { flex-direction:column; overflow:visible; height:auto; }

  /* Main pane hidden when a center is selected (detail takes over) */
  .cc-main--hidden { display:none; }
  .cc-tree-card { max-height:none; }
  .cc-tree { max-height:50vh; }

  /* Detail: full width, only shown when a center is selected */
  .cc-detail { width:100%; display:none; }
  .cc-detail--visible { display:flex; }

  .cc-mobile-back { display:block; padding:12px 14px 0; }
  .cc-back-btn { display:inline-flex; align-items:center; gap:6px; background:#fff; border:1.5px solid #e5e7eb; border-radius:8px; padding:7px 14px; font-size:13px; font-weight:600; color:#374151; cursor:pointer; }
  .cc-back-btn:hover { background:#f9fafb; }
  .cc-back-arrow { font-size:16px; line-height:1; }

  .cc-stat-grid { grid-template-columns:1fr 1fr; gap:8px; }
  .cc-stat-box:nth-child(3) { grid-column:1 / -1; }

  /* Drawer full-screen */
  .cc-drawer { width:100%; max-width:100vw; }
  .cc-grid2  { grid-template-columns:1fr; }
}

@media (max-width: 479px) {
  .cc-page { padding:8px; background:#fff; }
  .cc-detail-scroll { padding:14px; }
  .cc-budget-grid { gap:10px; padding:12px 14px; }
  .cc-drawer-body { padding:16px 14px; }
  .cc-swatch { width:28px; height:28px; }
}
</style>