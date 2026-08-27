<template>
<div class="cust-page">
  <div class="cust-toolbar">
    <div style="display:flex;align-items:center;gap:12px">
      <span style="font-size:18px;font-weight:700;color:#1a1a2e">Email Templates</span>
      <span style="background:#F3F0FF;color:#2563eb;padding:2px 10px;border-radius:20px;font-size:12px;font-weight:600">{{list.length}}</span>
    </div>
    <button class="nim-btn nim-btn-primary" :disabled="!$canCreate('admin')" :title="!$canCreate('admin') ? 'Read-only access' : ''" @click="openAdd"><span v-html="icon('plus',13)" style="vertical-align:-2px;margin-right:4px"/>New Template</button>
  </div>

  <div style="background:linear-gradient(135deg,#E7F5FF,#D0EBFF);border:1px solid #a5d8ff;border-radius:10px;padding:14px 18px;margin-bottom:16px;display:flex;gap:12px;align-items:center">
    <span style="font-size:20px">📧</span>
    <div style="font-size:12.5px;color:#1971C2">Templates are auto-applied when sending emails. Name them exactly after the document type (e.g. <b>Sales Invoice</b>) and use <b v-pre>{{variable}}</b> placeholders for dynamic data.</div>
  </div>

  <div style="margin-bottom:14px">
    <div style="position:relative;max-width:360px">
      <span style="position:absolute;left:10px;top:50%;transform:translateY(-50%);opacity:.5" v-html="icon('search',14)"></span>
      <input class="nim-input" v-model="search" placeholder="Search templates…" style="padding-left:32px"/>
    </div>
  </div>

  <div v-if="loading" style="padding:60px;text-align:center;color:#868e96">Loading templates…</div>

  <div v-else-if="!filtered.length" style="padding:60px;text-align:center;color:#868e96;background:#fff;border:1px dashed #e4e8f0;border-radius:12px">
    <div style="font-size:36px;margin-bottom:10px">📭</div>
    <div style="font-size:14px;font-weight:600;margin-bottom:4px">No templates yet</div>
    <div style="font-size:12.5px">Create your first email template to automate customer communications</div>
    <button class="nim-btn nim-btn-primary" :disabled="!$canCreate('admin')" :title="!$canCreate('admin') ? 'Read-only access' : ''" @click="openAdd" style="margin-top:16px">Create Template</button>
  </div>

  <div v-else class="et-grid">
    <div v-for="(t, idx) in filtered" :key="t.name" class="et-grid-card">
      <!-- Top row: icon + HTML badge -->
      <div class="et-grid-top">
        <div class="et-grid-icon" :style="iconStyle(idx)">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" :stroke="iconColor(idx)" stroke-width="1.6">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <polyline points="9 15 12 18 15 15"/>
            <line x1="12" y1="12" x2="12" y2="18"/>
          </svg>
        </div>
        <span class="et-grid-badge" :style="badgeStyle(idx)">HTML</span>
      </div>

      <!-- Name + subject -->
      <div class="et-grid-name">{{t.name}}</div>
      <div class="et-grid-subject">{{t.subject||'No subject'}}</div>

      <!-- Divider -->
      <div class="et-grid-divider"></div>

      <!-- Meta row -->
      <div class="et-grid-meta">
        <div>
          <div class="et-grid-meta-label">Last Updated</div>
          <div class="et-grid-meta-val">{{formatDate(t.modified)}}</div>
        </div>
      </div>

      <!-- Divider -->
      <div class="et-grid-divider"></div>

      <!-- Actions -->
      <div class="et-grid-actions">
        <button class="et-grid-btn" :disabled="!$canEdit('admin')" :title="!$canEdit('admin') ? 'Read-only access' : ''" @click="openEdit(t)">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          Edit
        </button>
        <button class="et-grid-btn et-grid-btn-del" :disabled="!$canDelete('admin')" :title="!$canDelete('admin') ? 'Not permitted' : ''" @click="delTarget=t.name;showDel=true">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
          Delete
        </button>
      </div>
    </div>
  </div>

  <!-- ── Right-side drawer ─────────────────────────────────────── -->
  <Teleport to="body">
    <transition name="et-fade">
      <div v-if="showDrawer" class="et-overlay" @click.self="showDrawer=false"></div>
    </transition>
    <transition name="et-slide">
      <div v-if="showDrawer" class="et-drawer">

        <!-- Header -->
        <div class="et-header">
          <div class="et-header-left">
            <div class="et-header-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
              </svg>
            </div>
            <div>
              <div class="et-header-title">{{drawerMode==='add'?'New Email Template':'Edit Template'}}</div>
              <div v-if="form.name" class="et-header-sub">{{form.name}}</div>
            </div>
          </div>
          <button class="et-close-btn" @click="showDrawer=false">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6 6 18M6 6l12 12"/></svg>
          </button>
        </div>

        <!-- Tab bar -->
        <div class="et-tabbar">
          <button class="et-tab" :class="{active: activeTab==='settings'}" @click="activeTab='settings'">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
            Template Settings
          </button>
          <button class="et-tab" :class="{active: activeTab==='body'}" @click="activeTab='body'">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
            Email Body
          </button>
          <button class="et-tab" :class="{active: activeTab==='preview'}" @click="activeTab='preview'">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
            Preview
          </button>
        </div>

        <!-- ── Tab: Template Settings ───────────────────────────── -->
        <div v-if="activeTab==='settings'" class="et-body">
          <div class="et-section-head">
            <div class="et-section-title">Template Settings</div>
            <div class="et-section-desc">Configure the basic details of your template.</div>
          </div>

          <!-- Template Name -->
          <div class="et-field">
            <label class="et-label">Template Name <span class="et-req">*</span></label>
            <input class="nim-input" v-model="form.name"
              :readonly="drawerMode==='edit'"
              placeholder="e.g. Sales Invoice"
              :style="drawerMode==='edit'?'background:#f8f9fc;color:#868e96;cursor:not-allowed':''"/>
            <div class="et-hint">Auto-applied when sending — click a doc type to use as name:</div>
            <div class="et-chips-row">
              <button v-for="n in DOC_TYPE_NAMES" :key="n"
                class="et-docchip"
                :class="{active: form.name===n, taken: drawerMode==='add' && list.some(t=>t.name===n)}"
                :disabled="drawerMode==='edit'"
                :title="drawerMode==='add' && list.some(t=>t.name===n) ? 'Template already exists — click Edit to modify it' : ''"
                @click="drawerMode==='add' && (form.name=n)">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                {{n}}
              </button>
            </div>
          </div>

          <!-- Subject -->
          <div class="et-field">
            <label class="et-label">Subject <span class="et-req">*</span></label>
            <input class="nim-input et-subject-input" v-model="form.subject" :placeholder="subjectPlaceholder"/>
            <div class="et-varbar">
              <span class="et-varlabel">Insert variables in subject:</span>
              <button v-for="v in BUILTIN_VARS" :key="v.key" class="et-varchip" @click="insertSubjectVar(v.key)" :title="v.desc">{{v.key}}</button>
            </div>
          </div>

          <!-- Email Body preview in settings tab -->
          <div class="et-field">
            <div class="et-body-row-head">
              <div>
                <label class="et-label">Email Body <span class="et-req">*</span></label>
                <span class="et-html-badge">HTML</span>
              </div>
              <div class="et-body-tab-btns">
                <button class="et-edit-html-btn" @click="activeTab='body'">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
                  Edit HTML
                </button>
                <button class="et-preview-btn" @click="activeTab='preview'">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                  Preview
                </button>
              </div>
            </div>
            <div class="et-varbar">
              <span class="et-varlabel">Insert variables:</span>
              <button v-for="v in BUILTIN_VARS" :key="v.key" class="et-varchip" @click="insertBodyVar(v.key)" :title="v.desc">{{v.key}}</button>
            </div>
            <!-- Line-numbered code area -->
            <div class="et-code-wrap">
              <div class="et-line-nums" aria-hidden="true">
                <span v-for="(_, i) in codeLines" :key="i">{{i+1}}</span>
              </div>
              <textarea
                ref="bodyTextarea"
                class="et-code-textarea"
                v-model="form.response"
                :placeholder="bodyPlaceholder"
                spellcheck="false"
                @input="syncLines"
                @scroll="syncScroll"
              ></textarea>
            </div>
          </div>
        </div>

        <!-- ── Tab: Email Body ─────────────────────────────────── -->
        <div v-if="activeTab==='body'" class="et-body">
          <div class="et-section-head">
            <div style="display:flex;align-items:center;gap:8px">
              <div class="et-section-title" style="margin:0">Email Body</div>
              <span class="et-html-badge">HTML</span>
            </div>
            <div class="et-section-desc">Write your email content using HTML. Use variables to personalize the email.</div>
          </div>
          <div class="et-varbar">
            <span class="et-varlabel">Insert variables:</span>
            <button v-for="v in BUILTIN_VARS" :key="v.key" class="et-varchip" @click="insertBodyVar(v.key)" :title="v.desc">{{v.key}}</button>
          </div>
          <div class="et-code-wrap et-code-wrap-body">
            <div class="et-line-nums" aria-hidden="true">
              <span v-for="(_, i) in codeLines" :key="i">{{i+1}}</span>
            </div>
            <textarea
              ref="bodyTextarea2"
              class="et-code-textarea"
              v-model="form.response"
              :placeholder="bodyPlaceholder"
              spellcheck="false"
              @input="syncLines"
            ></textarea>
          </div>
        </div>

        <!-- ── Tab: Preview ────────────────────────────────────── -->
        <div v-if="activeTab==='preview'" class="et-body">
          <div class="et-preview-chrome">
            <div class="et-preview-topbar">
              <div class="et-preview-icon">📧</div>
              <div>
                <div style="font-weight:600;font-size:13px;color:#1a1a2e">{{form.subject||'(no subject)'}}</div>
                <div style="font-size:11px;color:#868e96;margin-top:1px">Live preview · <span v-pre style="color:#f59e0b;">{{variable}}</span> placeholders highlighted</div>
              </div>
            </div>
            <div class="et-preview-body" v-html="previewHtml"></div>
          </div>
        </div>

        <!-- Footer -->
        <div class="et-footer">
          <button class="nim-btn nim-btn-ghost" @click="showDrawer=false">Cancel</button>
          <button class="nim-btn nim-btn-primary" @click="save" :disabled="saving || !(drawerMode==='add' ? $canCreate('admin') : $canEdit('admin'))" :title="!(drawerMode==='add' ? $canCreate('admin') : $canEdit('admin')) ? 'Read-only access' : ''" style="min-width:150px">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" style="vertical-align:-2px;margin-right:5px"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
            {{saving?'Saving…':'Save Template'}}
          </button>
        </div>

      </div>
    </transition>

    <!-- Delete confirm -->
    <div v-if="showDel" class="nim-overlay" @click.self="showDel=false">
      <div class="nim-dialog" style="width:400px">
        <div class="nim-header"><span style="font-weight:700;color:#fff">Delete Template?</span></div>
        <div class="nim-body"><p style="font-size:13.5px;color:#4a5568">Delete "<b>{{delTarget}}</b>"? This cannot be undone and any automation using this template will stop working.</p></div>
        <div class="nim-footer">
          <button class="nim-btn nim-btn-ghost" @click="showDel=false">Cancel</button>
          <button class="nim-btn" style="background:#c92a2a;color:#fff;border-color:#c92a2a" :disabled="!$canDelete('admin')" :title="!$canDelete('admin') ? 'Not permitted' : ''" @click="confirmDel">Delete</button>
        </div>
      </div>
    </div>
  </Teleport>
</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from "vue";
import { apiGET, apiPOST } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";

const { toast } = useToast();

const list         = ref([]);
const loading      = ref(false);
const saving       = ref(false);
const showDrawer    = ref(false);
const drawerMode    = ref("add");
const showDel       = ref(false);
const delTarget     = ref(null);
const search        = ref("");
const preview       = ref(false);
const activeTab     = ref("settings");
const bodyTextarea  = ref(null);
const bodyTextarea2 = ref(null);
const codeLines     = ref([""]);
const form          = reactive({ name: "", subject: "", response: "" });

const DOC_TYPE_NAMES = [
  "Sales Invoice", "Purchase Invoice", "Quotation",
  "Sales Order", "Purchase Order", "Credit Note", "Debit Note",
];

const BUILTIN_VARS = [
  { key: "{{customer_name}}", desc: "Customer / contact name" },
  { key: "{{invoice_no}}",    desc: "Invoice / document number" },
  { key: "{{amount}}",        desc: "Total amount" },
  { key: "{{due_date}}",      desc: "Due / delivery date" },
  { key: "{{company}}",       desc: "Your company name" },
];

const subjectPlaceholder = "e.g. Invoice {{invoice_no}} is due on {{due_date}}";
const bodyPlaceholder = `<p>Dear {{customer_name}},</p>
<p>Your invoice <b>{{invoice_no}}</b> of OMR {{amount}} is due on {{due_date}}.</p>
<p>Regards,<br>{{company}}</p>`;

const filtered = computed(() => {
  const q = search.value.toLowerCase();
  return list.value.filter(t =>
    !q || (t.name||"").toLowerCase().includes(q) || (t.subject||"").toLowerCase().includes(q)
  );
});

// Live preview: render HTML and highlight {{var}} placeholders
const previewHtml = computed(() => {
  let h = form.response || "<p style='color:#868e96;font-style:italic'>Nothing to preview yet.</p>";
  h = h.replace(
    /\{\{(\w+)\}\}/g,
    `<span style="display:inline-block;background:#fff3bf;color:#8b6914;padding:1px 6px;border-radius:4px;font-size:12px;font-weight:600;">{{$1}}</span>`
  );
  return h;
});

async function load() {
  loading.value = true;
  try { list.value = await apiGET("zoho_books_clone.api.admin.get_email_templates") || []; }
  catch (e) { toast("Could not load templates: " + e.message, "error"); }
  loading.value = false;
}

function openAdd() {
  drawerMode.value = "add";
  Object.assign(form, { name: "", subject: "", response: "" });
  preview.value = false;
  activeTab.value = "settings";
  codeLines.value = [""];
  showDrawer.value = true;
}

async function openEdit(t) {
  drawerMode.value = "edit";
  preview.value = false;
  activeTab.value = "settings";
  try {
    const d = await apiGET("zoho_books_clone.api.admin.get_email_template", { name: t.name });
    Object.assign(form, { name: d.name, subject: d.subject || "", response: d.response || "" });
  } catch {
    Object.assign(form, { name: t.name, subject: t.subject || "", response: "" });
  }
  codeLines.value = (form.response || "").split("\n");
  showDrawer.value = true;
}

async function save() {
  if (!form.name.trim())    return toast("Template name is required", "error");
  if (!form.subject.trim()) return toast("Subject is required", "error");
  if (drawerMode.value === "add") {
    const exists = list.value.some(t => t.name === form.name.trim());
    if (exists) return toast(`A template named "${form.name}" already exists. Edit it instead.`, "error");
  }
  saving.value = true;
  try {
    await apiPOST("zoho_books_clone.api.admin.save_email_template", {
      name: form.name, subject: form.subject, response: form.response, use_html: 1,
    });
    toast(drawerMode.value === "add" ? "Template created" : "Template updated");
    showDrawer.value = false;
    load();
  } catch (e) { toast(e.message, "error"); }
  saving.value = false;
}

async function confirmDel() {
  try {
    await apiPOST("zoho_books_clone.api.admin.delete_email_template", { name: delTarget.value });
    toast("Template deleted"); showDel.value = false; load();
  } catch (e) { toast(e.message, "error"); }
}

// Insert variable at cursor in subject field
function insertSubjectVar(v) {
  const el = document.querySelector(".et-subject-input");
  if (!el) { form.subject += v; return; }
  const s = el.selectionStart ?? form.subject.length;
  const e2 = el.selectionEnd ?? form.subject.length;
  form.subject = form.subject.slice(0, s) + v + form.subject.slice(e2);
  nextTick(() => { el.focus(); el.setSelectionRange(s + v.length, s + v.length); });
}

// Insert variable at cursor in body textarea
function insertBodyVar(v) {
  const el = bodyTextarea.value;
  if (!el) { form.response += v; return; }
  const s = el.selectionStart ?? form.response.length;
  const e2 = el.selectionEnd ?? form.response.length;
  form.response = form.response.slice(0, s) + v + form.response.slice(e2);
  nextTick(() => { el.focus(); el.setSelectionRange(s + v.length, s + v.length); });
}

const CARD_PALETTES = [
  { bg: "#F0EEFF", stroke: "#7C3AED", badgeBg: "#EDE9FE", badgeColor: "#5B21B6" },
  { bg: "#ECFDF5", stroke: "#059669", badgeBg: "#D1FAE5", badgeColor: "#065F46" },
  { bg: "#EFF6FF", stroke: "#2563EB", badgeBg: "#DBEAFE", badgeColor: "#1D4ED8" },
  { bg: "#FFF7ED", stroke: "#D97706", badgeBg: "#FEF3C7", badgeColor: "#92400E" },
  { bg: "#FFF0F3", stroke: "#E11D48", badgeBg: "#FFE4E6", badgeColor: "#9F1239" },
  { bg: "#F0F9FF", stroke: "#0284C7", badgeBg: "#E0F2FE", badgeColor: "#075985" },
];
function iconStyle(idx) {
  const p = CARD_PALETTES[idx % CARD_PALETTES.length];
  return { background: p.bg };
}
function iconColor(idx) {
  return CARD_PALETTES[idx % CARD_PALETTES.length].stroke;
}
function badgeStyle(idx) {
  const p = CARD_PALETTES[idx % CARD_PALETTES.length];
  return { background: p.badgeBg, color: p.badgeColor };
}
function formatDate(val) {
  if (!val) return "—";
  // Frappe returns "2025-05-15 10:23:45.000000" — replace space with T for Safari/Firefox compat
  const d = new Date(val.toString().replace(" ", "T"));
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function syncLines() {
  codeLines.value = (form.response || "").split("\n");
}

function syncScroll(e) {
  const nums = e.target.previousElementSibling;
  if (nums) nums.scrollTop = e.target.scrollTop;
}

onMounted(load);
</script>

<style scoped>
/* ── Overlay & drawer ───────────────────────────────────────────── */
.et-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.38);
  z-index: 1000;
}
.et-drawer {
  position: fixed; top: 0; right: 0; bottom: 0;
  width: 700px; max-width: 100vw;
  background: #fff;
  display: flex; flex-direction: column;
  box-shadow: -8px 0 40px rgba(0,0,0,.18);
  z-index: 1001;
}
/* Overlay fades in/out */
.et-fade-enter-active, .et-fade-leave-active { transition: opacity .25s ease; }
.et-fade-enter-from, .et-fade-leave-to { opacity: 0; }
/* Drawer slides in/out */
.et-slide-enter-active, .et-slide-leave-active { transition: transform .28s cubic-bezier(.4,0,.2,1); }
.et-slide-enter-from, .et-slide-leave-to { transform: translateX(100%); }

/* ── Header ─────────────────────────────────────────────────────── */
.et-header {
  padding: 18px 22px;
  display: flex; align-items: center; justify-content: space-between;
  flex-shrink: 0;
  background: #fff;
  border-bottom: 1px solid #edf0f7;
}
.et-header-left {
  display: flex; align-items: center; gap: 12px;
}
.et-header-icon {
  width: 44px; height: 44px; border-radius: 12px;
  background: #F3F0FF;
  display: flex; align-items: center; justify-content: center;
  color: #5c3dc7; flex-shrink: 0;
}
.et-header-title {
  font-size: 17px; font-weight: 700; color: #1a1a2e;
}
.et-header-sub {
  font-size: 12px; color: #868e96; margin-top: 2px;
}
.et-close-btn {
  background: #f4f6fb; border: 1px solid #e4e8f0; cursor: pointer;
  color: #6b7280; width: 34px; height: 34px; border-radius: 8px;
  display: grid; place-items: center; transition: all .15s;
  flex-shrink: 0;
}
.et-close-btn:hover { background: #e4e8f0; color: #1a1a2e; }

/* ── Tab bar ─────────────────────────────────────────────────────── */
.et-tabbar {
  display: flex;
  border-bottom: 1px solid #e4e8f0;
  background: #fff;
  flex-shrink: 0;
  padding: 0 22px;
}
.et-tab {
  display: flex; align-items: center; gap: 6px;
  padding: 13px 18px;
  font-size: 13px; font-weight: 500; color: #6b7280;
  background: transparent; border: none; border-bottom: 2px solid transparent;
  cursor: pointer; transition: all .15s; white-space: nowrap;
  margin-bottom: -1px;
}
.et-tab:hover { color: #2563eb; }
.et-tab.active {
  color: #2563eb; font-weight: 600;
  border-bottom-color: #2563eb;
}
.et-tab svg { flex-shrink: 0; }

/* ── Scrollable body ────────────────────────────────────────────── */
.et-body {
  flex: 1; overflow-y: auto;
  padding: 22px; display: flex; flex-direction: column; gap: 20px;
  background: #f9fafc;
}

/* ── Section heading ────────────────────────────────────────────── */
.et-section-head {
  display: flex; flex-direction: column; gap: 3px;
}
.et-section-title {
  font-size: 15px; font-weight: 700; color: #1a1a2e;
}
.et-section-desc {
  font-size: 12.5px; color: #9ca3af;
}

/* ── White card sections ────────────────────────────────────────── */
.et-field {
  display: flex; flex-direction: column; gap: 8px;
  background: #fff;
  border: 1px solid #e4e8f0;
  border-radius: 12px;
  padding: 18px;
}
.et-label { font-size: 12.5px; font-weight: 600; color: #374151; }
.et-req { color: #c92a2a; }
.et-hint { font-size: 11.5px; color: #9ca3af; }

/* ── Doc-type chip buttons ──────────────────────────────────────── */
.et-chips-row {
  display: flex; flex-wrap: wrap; gap: 6px; margin-top: 2px;
}
.et-docchip {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 4px 12px; border-radius: 20px;
  font-size: 11.5px; font-weight: 600;
  background: #f4f6fb; color: #374151;
  border: 1.5px solid #e4e8f0;
  cursor: pointer; transition: all .15s; user-select: none;
}
.et-docchip:not(:disabled):hover { background: #ede9fe; color: #5c3dc7; border-color: #c4b5fd; }
.et-docchip.active { background: #ede9fe; color: #2563eb; border-color: #2563eb; }
.et-docchip.taken { background: #fff5f5; color: #c92a2a; border-color: #ffc9c9; }
.et-docchip:disabled { cursor: not-allowed; opacity: .6; }

/* ── Variable bar ───────────────────────────────────────────────── */
.et-varbar {
  display: flex; align-items: center; flex-wrap: wrap; gap: 6px;
  padding: 8px 12px;
  background: #f8f9fc; border: 1px solid #e8ecf5; border-radius: 8px;
}
.et-varlabel { font-size: 11px; color: #9ca3af; white-space: nowrap; margin-right: 2px; }
.et-varchip {
  padding: 3px 9px; border-radius: 8px;
  font-size: 11px; font-weight: 600;
  background: #f0eeff; color: #5c3dc7;
  border: 1px solid #d4c4ff; cursor: pointer;
  transition: background .1s; white-space: nowrap;
}
.et-varchip:hover { background: #e2d4ff; }

/* ── HTML badge ─────────────────────────────────────────────────── */
.et-html-badge {
  background: #E7F5FF; color: #1971C2;
  padding: 2px 9px; border-radius: 10px;
  font-size: 10.5px; font-weight: 700; letter-spacing: .3px;
  text-transform: uppercase; margin-left: 6px;
}

/* ── Body row header (in settings tab) ─────────────────────────── */
.et-body-row-head {
  display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;
}
.et-body-tab-btns {
  display: flex; gap: 6px;
}
.et-edit-html-btn {
  display: flex; align-items: center; gap: 5px;
  padding: 6px 14px; border-radius: 7px;
  font-size: 12px; font-weight: 600; color: #fff;
  background: #2563eb; border: none; cursor: pointer;
  transition: background .15s;
}
.et-edit-html-btn:hover { background: #1d4ed8; }
.et-preview-btn {
  display: flex; align-items: center; gap: 5px;
  padding: 6px 14px; border-radius: 7px;
  font-size: 12px; font-weight: 600; color: #374151;
  background: #fff; border: 1.5px solid #e4e8f0; cursor: pointer;
  transition: all .15s;
}
.et-preview-btn:hover { border-color: #c4b5fd; color: #5c3dc7; }

/* ── Line-numbered code editor ──────────────────────────────────── */
.et-code-wrap {
  display: flex;
  border: 1.5px solid #e4e8f0;
  border-radius: 8px;
  overflow: auto;
  background: #fff;
  font-size: 13px;
  min-height: 140px;
  resize: vertical;
}
.et-code-wrap-body {
  min-height: 420px;
  resize: vertical;
}
.et-line-nums {
  display: flex; flex-direction: column;
  padding: 14px 0;
  min-width: 38px;
  background: #f8f9fc; border-right: 1px solid #e8ecf5;
  overflow: hidden;
  user-select: none;
  flex-shrink: 0;
}
.et-line-nums span {
  display: block;
  line-height: 1.7;
  padding: 0 10px;
  font-size: 12px; color: #c0c8d8;
  text-align: right;
}
.et-code-textarea {
  flex: 1;
  padding: 14px 14px;
  border: none; outline: none;
  font-size: 13px;
  line-height: 1.7;
  color: #1a1a2e;
  background: #fff;
  resize: none;
  min-height: 120px;
  height: 100%;
  box-sizing: border-box;
}
.et-code-wrap-body .et-code-textarea {
  min-height: 0;
  height: 100%;
}
.et-code-textarea::placeholder { color: #bcc3d0; }

/* ── Preview ────────────────────────────────────────────────────── */
.et-preview-chrome {
  border: 1.5px solid #e4e8f0;
  border-radius: 12px;
  background: #fff;
  flex: 1;
  display: flex; flex-direction: column;
}
.et-preview-topbar {
  display: flex; align-items: center; gap: 10px;
  padding: 14px 18px;
  background: #f8f9fc; border-bottom: 1px solid #f0f2f7;
}
.et-preview-body {
  padding: 24px 28px;
  font-size: 14px; line-height: 1.8; color: #374151;
  flex: 1;
}
.et-preview-body :deep(p) { margin: 0 0 10px; }
.et-preview-body :deep(h1),
.et-preview-body :deep(h2),
.et-preview-body :deep(h3) { margin: 12px 0 6px; font-weight: 700; }
.et-preview-body :deep(table) { border-collapse: collapse; width: 100%; }
.et-preview-body :deep(td),
.et-preview-body :deep(th) { padding: 6px 12px; border: 1px solid #e4e8f0; }
.et-preview-body :deep(a) { color: #2563eb; }
.et-preview-body :deep(hr) { border: none; border-top: 1px solid #e4e8f0; margin: 12px 0; }

/* ── Footer ─────────────────────────────────────────────────────── */
.et-footer {
  display: flex; justify-content: flex-end; align-items: center; gap: 10px;
  padding: 14px 22px;
  background: #fff; border-top: 1px solid #e4e8f0;
  flex-shrink: 0;
}

@media (max-width: 720px) {
  .et-drawer { width: 100vw; }
}

/* ── Template list grid ─────────────────────────────────────────── */
.et-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.et-grid-card {
  background: #fff;
  border: 1px solid #e8ecf5;
  border-radius: 16px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: box-shadow .18s, border-color .18s;
}
.et-grid-card:hover {
  box-shadow: 0 4px 20px rgba(0,0,0,.07);
  border-color: #d0d7e8;
}
.et-grid-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}
.et-grid-icon {
  width: 52px; height: 52px; border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.et-grid-badge {
  padding: 3px 10px; border-radius: 10px;
  font-size: 11px; font-weight: 700; letter-spacing: .3px;
  text-transform: uppercase;
}
.et-grid-name {
  font-size: 15px; font-weight: 700; color: #1a1a2e;
  margin-top: 4px;
}
.et-grid-subject {
  font-size: 12.5px; color: #6b7280;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.et-grid-divider {
  height: 1px; background: #f0f2f7; margin: 0 -2px;
}
.et-grid-meta {
  display: flex; gap: 8px;
}
.et-grid-meta-label {
  font-size: 11px; font-weight: 600; color: #9ca3af;
  text-transform: uppercase; letter-spacing: .4px; margin-bottom: 3px;
}
.et-grid-meta-val {
  font-size: 12.5px; font-weight: 500; color: #374151;
}
.et-grid-actions {
  display: flex; gap: 8px;
}
.et-grid-btn {
  flex: 1;
  display: flex; align-items: center; justify-content: center; gap: 6px;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 12.5px; font-weight: 600; color: #374151;
  background: #fff; border: 1.5px solid #e4e8f0;
  cursor: pointer; transition: all .15s;
}
.et-grid-btn:hover { background: #f4f6fb; border-color: #d0d7e8; }
.et-grid-btn-del { color: #c92a2a; }
.et-grid-btn-del:hover { background: #fff5f5; border-color: #ffc9c9; color: #c92a2a; }
</style>