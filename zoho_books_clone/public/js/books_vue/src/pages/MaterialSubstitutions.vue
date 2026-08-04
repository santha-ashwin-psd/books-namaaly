<template>
  <div class="qcar-page">

    <div class="qcar-kpi-strip">
      <div class="qcar-kpi" :class="{active: filterStatus==='all'}" @click="filterStatus='all'">
        <div class="qcar-kpi-ico" style="background:#eff6ff;color:#2563eb">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 3H8a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2z"/><path d="M9 12l2 2 4-4"/></svg>
        </div>
        <div><div class="qcar-kpi-lbl">Total</div><div class="qcar-kpi-val">{{ stats.total }}</div></div>
      </div>
      <div class="qcar-kpi" :class="{active: filterStatus==='Pending'}" @click="filterStatus='Pending'">
        <div class="qcar-kpi-ico" style="background:#fffbeb;color:#d97706">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        </div>
        <div><div class="qcar-kpi-lbl">Pending Approval</div><div class="qcar-kpi-val" style="color:#d97706">{{ stats.pending }}</div></div>
      </div>
      <div class="qcar-kpi" :class="{active: filterStatus==='Approved'}" @click="filterStatus='Approved'">
        <div class="qcar-kpi-ico" style="background:#f0fdf4;color:#16a34a">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
        </div>
        <div><div class="qcar-kpi-lbl">Approved</div><div class="qcar-kpi-val" style="color:#16a34a">{{ stats.approved }}</div></div>
      </div>
      <div class="qcar-kpi" :class="{active: filterStatus==='Applied Immediately'}" @click="filterStatus='Applied Immediately'">
        <div class="qcar-kpi-ico" style="background:#eef2ff;color:#4338ca">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
        </div>
        <div><div class="qcar-kpi-lbl">Applied Immediately</div><div class="qcar-kpi-val" style="color:#4338ca">{{ stats.applied }}</div></div>
      </div>
      <div class="qcar-kpi" :class="{active: filterStatus==='Rejected'}" @click="filterStatus='Rejected'">
        <div class="qcar-kpi-ico" style="background:#fef2f2;color:#dc2626">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
        </div>
        <div><div class="qcar-kpi-lbl">Rejected</div><div class="qcar-kpi-val" style="color:#dc2626">{{ stats.rejected }}</div></div>
      </div>
    </div>

    <div class="qcar-toolbar">
      <div class="qcar-search-wrap">
        <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
        <input v-model="search" placeholder="Search work order, item…" class="qcar-search-input" />
      </div>
      <div style="display:flex;gap:8px;align-items:center">
        <button class="qcar-btn-ghost" @click="load"><span v-html="icon('refresh',14)"></span></button>
      </div>
    </div>

    <div class="qcar-card qcar-table-wrap">
      <table class="qcar-table">
        <thead><tr>
          <th>Log #</th>
          <th>Work Order</th>
          <th>Substitution</th>
          <th>Requested By</th>
          <th>Date</th>
          <th>Status</th>
          <th style="width:44px"></th>
        </tr></thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 6" :key="n"><td colspan="7"><div class="qcar-shimmer"></div></td></tr>
          </template>
          <template v-else>
            <tr v-for="r in filtered" :key="r.name" class="qcar-row" @click="openView(r)">
              <td><span class="qcar-num">{{ r.name }}</span></td>
              <td><DocLink doctype="Work Order" :name="r.work_order" /></td>
              <td>
                <div style="font-size:12.5px;font-weight:600">{{ r.original_item_code }} → {{ r.alternative_item_code }}</div>
                <div style="font-size:11px;color:#9ca3af">{{ r.requires_approval ? 'Requires approval' : 'No approval needed' }}</div>
              </td>
              <td style="font-size:12px;color:#6b7280">{{ shortUser(r.requested_by) }}</td>
              <td class="mono-sm text-muted">{{ fmtDate(r.request_date) }}</td>
              <td><span class="qcar-status-badge" :class="statusClass(r.approval_status)">{{ r.approval_status }}</span></td>
              <td @click.stop><button class="qcar-act-btn" @click="openView(r)"><span v-html="icon('eye',13)"></span></button></td>
            </tr>
            <tr v-if="!filtered.length">
              <td colspan="7" class="qcar-empty">
                <div style="font-size:32px;margin-bottom:8px">🔀</div>
                <div style="font-weight:600;margin-bottom:4px">No Material Substitutions found</div>
                <div style="font-size:13px;color:#9ca3af">Logs appear when a raw material is substituted on a Work Order</div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- Mobile card list (shown instead of the table below the qcar-cards-wrap breakpoint) -->
    <div class="qcar-cards-wrap">
      <template v-if="loading">
        <div v-for="n in 4" :key="n" class="qcar-card qcar-mcard"><div class="qcar-shimmer" style="height:70px"></div></div>
      </template>
      <template v-else>
        <div v-for="r in filtered" :key="r.name" class="qcar-card qcar-mcard" @click="openView(r)">
          <div class="qcar-mcard-top">
            <span class="qcar-num">{{ r.name }}</span>
            <span class="qcar-status-badge" :class="statusClass(r.approval_status)">{{ r.approval_status }}</span>
          </div>
          <div class="qcar-mcard-sub">{{ r.original_item_code }} → {{ r.alternative_item_code }}</div>
          <div class="qcar-mcard-hint">{{ r.requires_approval ? 'Requires approval' : 'No approval needed' }}</div>
          <div class="qcar-mcard-meta">
            <DocLink doctype="Work Order" :name="r.work_order" />
            <span>{{ shortUser(r.requested_by) }}</span>
            <span class="mono-sm text-muted">{{ fmtDate(r.request_date) }}</span>
          </div>
        </div>
        <div v-if="!filtered.length" class="qcar-card qcar-empty">
          <div style="font-size:32px;margin-bottom:8px">🔀</div>
          <div style="font-weight:600;margin-bottom:4px">No Material Substitutions found</div>
          <div style="font-size:13px;color:#9ca3af">Logs appear when a raw material is substituted on a Work Order</div>
        </div>
      </template>
    </div>

    <div v-if="viewOpen" class="qcar-overlay" @click.self="viewOpen=false"></div>
    <div class="qcar-drawer" :class="{open: viewOpen}">
      <template v-if="viewDoc">
        <div class="qcar-dheader">
          <button class="qcar-dclose" @click="viewOpen=false"><span v-html="icon('x',16)"></span></button>
          <div class="qcar-dh-top">
            <div class="qcar-dh-ico">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><path d="M16 3H8a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2z"/></svg>
            </div>
            <div>
              <div class="qcar-dh-title">{{ viewDoc.name }}</div>
              <div class="qcar-dh-sub">Material Substitution · {{ fmtDate(viewDoc.request_date) }}</div>
            </div>
            <span class="qcar-status-badge" :class="statusClass(viewDoc.approval_status)" style="margin-left:auto;flex-shrink:0">{{ viewDoc.approval_status }}</span>
          </div>
        </div>
        <div class="qcar-dbody">

          <div class="qcar-info-grid">
            <div><span class="qcar-info-lbl">Work Order</span><div class="qcar-info-val"><DocLink doctype="Work Order" :name="viewDoc.work_order" :mono-style="false" style="color:#2563eb" /></div></div>
            <div><span class="qcar-info-lbl">Row</span><div class="qcar-info-val">{{ viewDoc.work_order_item_row }}</div></div>
            <div><span class="qcar-info-lbl">Original Item</span><div class="qcar-info-val">{{ viewDoc.original_item_code }}</div></div>
            <div><span class="qcar-info-lbl">Alternative Item</span><div class="qcar-info-val" style="color:#2563eb">{{ viewDoc.alternative_item_code }}</div></div>
            <div><span class="qcar-info-lbl">Conversion Factor</span><div class="qcar-info-val">{{ viewDoc.conversion_factor }}</div></div>
            <div><span class="qcar-info-lbl">Qty</span><div class="qcar-info-val">{{ viewDoc.original_required_qty }} → {{ viewDoc.new_required_qty }}</div></div>
            <div><span class="qcar-info-lbl">Requested By</span><div class="qcar-info-val">{{ viewDoc.requested_by }}</div></div>
            <div><span class="qcar-info-lbl">Request Date</span><div class="qcar-info-val">{{ fmtDate(viewDoc.request_date) }}</div></div>
          </div>

          <div class="qcar-view-section">
            <div class="qcar-sec-lbl">Reason</div>
            <div class="qcar-remarks-box">{{ viewDoc.reason }}</div>
          </div>

          <div v-if="viewDoc.approval_status !== 'Pending'" class="qcar-view-section">
            <div class="qcar-sec-lbl">{{ viewDoc.approval_status === 'Rejected' ? 'Rejection' : 'Approval' }} Details</div>
            <div class="qcar-info-grid">
              <div><span class="qcar-info-lbl">By</span><div class="qcar-info-val">{{ viewDoc.approved_by || '—' }}</div></div>
              <div><span class="qcar-info-lbl">Date</span><div class="qcar-info-val">{{ fmtDate(viewDoc.approval_date) }}</div></div>
            </div>
            <div v-if="viewDoc.rejection_reason" style="margin-top:8px">
              <div class="qcar-sec-lbl" style="color:#dc2626">Rejection Reason</div>
              <div class="qcar-remarks-box" style="border-color:#fca5a5;background:#fef2f2">{{ viewDoc.rejection_reason }}</div>
            </div>
          </div>

          <div v-if="viewDoc.approval_status === 'Pending'" class="qcar-view-section">
            <div class="qcar-sec-lbl">Action</div>
            <div style="display:flex;flex-direction:column;gap:8px">
              <textarea v-model="actionRemarks" class="qcar-input" rows="2" placeholder="Remarks (optional for approve, required for reject)…"></textarea>
              <textarea v-if="showRejectReason" v-model="rejectReason" class="qcar-input" rows="2" placeholder="Rejection reason (required)…" style="border-color:#fca5a5"></textarea>
              <div style="display:flex;gap:8px;flex-wrap:wrap">
                <button class="qcar-btn-approve" :disabled="actionSaving || !$canEdit('inventory')" @click="doApprove">
                  <span v-html="icon('check',13)"></span>{{ actionSaving && actionMode==='approve' ? 'Approving…' : 'Approve' }}
                </button>
                <button class="qcar-btn-reject" :disabled="actionSaving || !$canEdit('inventory')" @click="doReject">
                  <span v-html="icon('x',13)"></span>{{ actionSaving && actionMode==='reject' ? 'Rejecting…' : 'Reject' }}
                </button>
              </div>
            </div>
          </div>

        </div>
        <div class="qcar-dfooter">
          <button class="qcar-btn-ghost" @click="viewOpen=false">Close</button>
        </div>
      </template>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { apiCall } from "../api/client.js";
import DocLink from "../components/DocLink.vue";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";
import { fmtDate } from "../utils/format.js";

const { toast } = useToast();

const list        = ref([]);
const loading     = ref(false);
const viewOpen    = ref(false);
const viewDoc     = ref(null);
const search      = ref("");
const filterStatus = ref("all");
const actionRemarks = ref("");
const rejectReason  = ref("");
const showRejectReason = ref(false);
const actionSaving  = ref(false);
const actionMode    = ref("");

function statusClass(s) {
  if (s === "Approved") return "qcar-status-approved";
  if (s === "Rejected") return "qcar-status-rejected";
  if (s === "Applied Immediately") return "qcar-status-approved";
  return "qcar-status-pending";
}
function shortUser(u) {
  if (!u) return "—";
  return u.split("@")[0].replace(/\./g, " ").replace(/\b\w/g, c => c.toUpperCase()).slice(0, 18);
}

const stats = computed(() => ({
  total:    list.value.length,
  pending:  list.value.filter(r => r.approval_status === "Pending").length,
  approved: list.value.filter(r => r.approval_status === "Approved").length,
  applied:  list.value.filter(r => r.approval_status === "Applied Immediately").length,
  rejected: list.value.filter(r => r.approval_status === "Rejected").length,
}));

const filtered = computed(() => {
  let r = list.value;
  if (filterStatus.value !== "all") r = r.filter(x => x.approval_status === filterStatus.value);
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    r = r.filter(x =>
      (x.name || "").toLowerCase().includes(q) ||
      (x.work_order || "").toLowerCase().includes(q) ||
      (x.original_item_code || "").toLowerCase().includes(q) ||
      (x.alternative_item_code || "").toLowerCase().includes(q)
    );
  }
  return r;
});

async function load() {
  loading.value = true;
  try {
    const res = await apiCall("zoho_books_clone.api.material_substitution.list_material_substitution_logs", {
      approval_status: "all", page_len: 200, page: 0,
    });
    list.value = res?.message?.logs || res?.logs || [];
  } catch (e) {
    toast.error(e.message || "Failed to load Material Substitution Logs");
  } finally {
    loading.value = false;
  }
}

function openView(r) {
  viewDoc.value = { ...r };
  viewOpen.value = true;
  actionRemarks.value = "";
  rejectReason.value = "";
  showRejectReason.value = false;
  actionMode.value = "";
}

async function doApprove() {
  if (!viewDoc.value) return;
  actionSaving.value = true;
  actionMode.value = "approve";
  try {
    await apiCall("zoho_books_clone.api.material_substitution.approve_material_substitution", {
      log_name: viewDoc.value.name,
      remarks: actionRemarks.value,
    });
    toast.success(`${viewDoc.value.name} approved`);
    viewOpen.value = false;
    await load();
  } catch (e) {
    toast.error(e.message || "Approval failed");
  } finally {
    actionSaving.value = false;
  }
}

async function doReject() {
  if (!viewDoc.value) return;
  if (!showRejectReason.value) {
    showRejectReason.value = true;
    return;
  }
  if (!rejectReason.value.trim()) {
    return toast.error("Rejection reason is required.");
  }
  actionSaving.value = true;
  actionMode.value = "reject";
  try {
    await apiCall("zoho_books_clone.api.material_substitution.reject_material_substitution", {
      log_name: viewDoc.value.name,
      rejection_reason: rejectReason.value,
    });
    toast.success(`${viewDoc.value.name} rejected`);
    viewOpen.value = false;
    await load();
  } catch (e) {
    toast.error(e.message || "Rejection failed");
  } finally {
    actionSaving.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.qcar-page { display:flex; flex-direction:column; gap:14px; padding:24px; min-width:0; }
.qcar-kpi-strip { display:grid; grid-template-columns:repeat(5,1fr); gap:10px; }
.qcar-kpi { background:#fff; border:1px solid #e5e7eb; border-radius:10px; padding:12px 14px; display:flex; align-items:center; gap:12px; cursor:pointer; transition:border-color .15s,box-shadow .15s; }
.qcar-kpi:hover,.qcar-kpi.active { border-color:#2563eb; box-shadow:0 0 0 2px rgba(37,99,235,.1); }
.qcar-kpi-ico { width:36px; height:36px; border-radius:9px; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.qcar-kpi-lbl { font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.05em; color:#9ca3af; }
.qcar-kpi-val { font-size:20px; font-weight:700; color:#0f172a; line-height:1.2; }

.qcar-toolbar { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.qcar-search-wrap { display:flex; align-items:center; gap:8px; background:#fff; border:1px solid #e5e7eb; border-radius:8px; padding:6px 12px; min-width:0; flex:1; }
.qcar-search-input { border:none; background:transparent; outline:none; font:inherit; color:#111827; width:100%; font-size:13px; }
.qcar-btn-ghost { display:inline-flex; align-items:center; gap:6px; background:#fff; border:1px solid #e5e7eb; border-radius:8px; padding:8px 12px; font-size:13px; color:#374151; cursor:pointer; font-family:inherit; }
.qcar-btn-ghost:hover { background:#f9fafb; }

.qcar-card { background:#fff; border:1px solid #e5e7eb; border-radius:10px; overflow:hidden; overflow-x:auto; }
.qcar-table { width:100%; border-collapse:collapse; font-size:13px; }
.qcar-table th { background:#f9fafb; padding:10px 12px; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:#6b7280; text-align:left; border-bottom:1px solid #e5e7eb; white-space:nowrap; }
.qcar-table td { padding:10px 12px; border-bottom:1px solid #f3f4f6; vertical-align:middle; }
.qcar-row { cursor:pointer; transition:background .12s; }
.qcar-row:hover { background:#f8fafc; }
.qcar-num {  font-size:12px; font-weight:700; color:#2563eb; background:#eff6ff; padding:2px 6px; border-radius:4px; }
.qcar-act-btn { background:none; border:1px solid #e5e7eb; border-radius:6px; padding:4px 6px; cursor:pointer; color:#6b7280; }
.qcar-act-btn:hover { background:#f3f4f6; }
.qcar-empty { text-align:center; padding:40px 0; color:#6b7280; }
.qcar-shimmer { height:32px; background:linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size:200%; animation:shimmer 1.4s infinite; border-radius:4px; }
@keyframes shimmer { 0%{background-position:200%} 100%{background-position:-200%} }
.mono-sm {  font-size:12px; }
.text-muted { color:#9ca3af; }

/* ── Mobile card list (hidden on desktop; swaps in for the table on small screens) ── */
.qcar-cards-wrap { display:none; flex-direction:column; gap:10px; }
.qcar-mcard { padding:12px 14px; cursor:pointer; transition:background .12s; overflow:visible; }
.qcar-mcard:hover { background:#f8fafc; }
.qcar-mcard-top { display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:6px; }
.qcar-mcard-sub { font-size:13px; font-weight:600; color:#111827; margin-bottom:2px; }
.qcar-mcard-hint { font-size:11px; color:#9ca3af; margin-bottom:8px; }
.qcar-mcard-meta { display:flex; align-items:center; gap:8px; flex-wrap:wrap; font-size:12px; color:#6b7280; padding-top:8px; border-top:1px solid #f3f4f6; }
@media (max-width:680px) {
  .qcar-table-wrap { display:none; }
  .qcar-cards-wrap { display:flex; }
}

.qcar-status-badge { font-size:11px; font-weight:700; padding:3px 9px; border-radius:20px; }
.qcar-status-approved { background:#dcfce7; color:#15803d; }
.qcar-status-rejected { background:#fee2e2; color:#dc2626; }
.qcar-status-pending  { background:#fef3c7; color:#b45309; }

.qcar-overlay { position:fixed; inset:0; background:rgba(0,0,0,.35); z-index:998; }
.qcar-drawer { position:fixed; right:0; top:0; bottom:0; width:560px; background:#fff; z-index:999; display:flex; flex-direction:column; transform:translateX(100%); transition:transform .25s cubic-bezier(.4,0,.2,1); box-shadow:-4px 0 24px rgba(0,0,0,.12); }
.qcar-drawer.open { transform:translateX(0); }
.qcar-dheader { padding:20px 20px 16px; background:linear-gradient(135deg,#1e3a5f,#2563eb); position:relative; flex-shrink:0; }
.qcar-dh-top { display:flex; align-items:center; gap:12px; }
.qcar-dh-ico { width:40px; height:40px; border-radius:10px; background:rgba(255,255,255,.2); display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.qcar-dh-title { font-size:16px; font-weight:700; color:#fff; }
.qcar-dh-sub { font-size:12px; color:rgba(255,255,255,.75); margin-top:2px; }
.qcar-dclose { position:absolute; top:14px; right:14px; background:rgba(255,255,255,.15); border:none; border-radius:8px; padding:6px; cursor:pointer; color:#fff; display:flex; align-items:center; }
.qcar-dclose:hover { background:rgba(255,255,255,.25); }
.qcar-dbody { flex:1; overflow-y:auto; padding:18px 20px; display:flex; flex-direction:column; gap:14px; }
.qcar-dfooter { padding:14px 20px; border-top:1px solid #e5e7eb; display:flex; gap:8px; justify-content:flex-end; flex-shrink:0; }

.qcar-info-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; background:#f8fafc; border-radius:8px; padding:12px 14px; border:1px solid #e5e7eb; }
.qcar-info-lbl { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:#9ca3af; }
.qcar-info-val { font-size:13px; font-weight:600; color:#0f172a; margin-top:2px; }

.qcar-view-section { display:flex; flex-direction:column; gap:6px; }
.qcar-sec-lbl { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:#9ca3af; }
.qcar-remarks-box { font-size:13px; color:#374151; background:#f8fafc; border-radius:6px; padding:10px 12px; border:1px solid #e2e8f0; }
.qcar-input { border:1px solid #e5e7eb; border-radius:8px; padding:8px 10px; font:inherit; font-size:13px; outline:none; color:#111827; resize:vertical; transition:border-color .15s; }
.qcar-input:focus { border-color:#2563eb; box-shadow:0 0 0 3px rgba(37,99,235,.08); }

.qcar-btn-approve { display:inline-flex; align-items:center; gap:6px; background:#f0fdf4; border:1px solid #16a34a; color:#16a34a; border-radius:8px; padding:8px 14px; font-size:13px; font-weight:600; cursor:pointer; font-family:inherit; }
.qcar-btn-approve:hover { background:#dcfce7; } .qcar-btn-approve:disabled { opacity:.5; cursor:not-allowed; }
.qcar-btn-reject  { display:inline-flex; align-items:center; gap:6px; background:#fef2f2; border:1px solid #dc2626; color:#dc2626; border-radius:8px; padding:8px 14px; font-size:13px; font-weight:600; cursor:pointer; font-family:inherit; }
.qcar-btn-reject:hover { background:#fee2e2; } .qcar-btn-reject:disabled { opacity:.5; cursor:not-allowed; }

@media (max-width: 480px) {
  .qcar-page { padding:10px 8px; gap:10px; }
  .qcar-kpi-strip { grid-template-columns:repeat(2,1fr); }
  .qcar-drawer { width:100%; }
  .qcar-dheader { padding:16px 16px 14px; }
  .qcar-dh-top { flex-wrap:wrap; }
  .qcar-dh-title { font-size:15px; word-break:break-word; }
  .qcar-dbody { padding:14px 16px; gap:12px; }
  .qcar-info-grid { grid-template-columns:1fr; gap:12px; padding:12px; }
  .qcar-dfooter { padding:12px 16px; flex-direction:column-reverse; }
  .qcar-dfooter .qcar-btn-ghost { width:100%; justify-content:center; }
  .qcar-btn-approve, .qcar-btn-reject { flex:1; justify-content:center; }
}
</style>