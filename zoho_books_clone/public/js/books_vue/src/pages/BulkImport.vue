<template>
<div class="bi-page">

  <!-- Header -->
  <div class="bi-head">
    <div>
      <div class="bi-title">Bulk Import</div>
      <div class="bi-subtitle">Import your business data quickly and accurately using a CSV file.</div>
    </div>
    <button class="sales-btn-ghost bi-download-btn" @click="downloadSample">
      <span v-html="icon('download',14)" style="vertical-align:-2px;margin-right:6px"></span> Download Sample CSV
    </button>
  </div>

  <!-- Category toggle + type cards -->
  <div class="bi-category-section">
    <div class="bi-category-tabs">
      <button v-for="cat in CATEGORIES" :key="cat.key"
        class="bi-cat-tab" :class="{ active: category === cat.key }"
        @click="switchCategory(cat.key)">
        <span v-html="icon(cat.icon, 13)" style="vertical-align:-2px;margin-right:5px"></span>
        {{cat.label}}
      </button>
    </div>

    <div class="bi-type-row">
      <button v-for="t in filteredTypes" :key="t.key"
        class="bi-type-card" :class="{ active: dtype===t.key }"
        @click="switchType(t.key)">
        <div class="bi-type-icon-wrap" :style="{ background: t.iconBg || '#eaf1ff' }">
          <span class="bi-type-icon" :style="{ color: t.iconColor || '#1a6ef7' }" v-html="icon(t.icon, 20)"></span>
        </div>
        <span class="bi-type-label">{{t.label}}</span>
        <span class="bi-type-req">{{requiredCountFor(t)}} required field{{requiredCountFor(t)===1?'':'s'}}</span>
        <span v-if="dtype===t.key" class="bi-type-check" v-html="icon('check',11)"></span>
      </button>
    </div>
  </div>

  <!-- Stepper -->
  <div class="bi-stepper">
    <template v-for="(s, i) in STEPS" :key="s.n">
      <div class="bi-step" :class="stepClass(s.n)" @click="jumpTo(s.n)">
        <div class="bi-step-dot">
          <span v-if="step > s.n" v-html="icon('check',12)"></span>
          <span v-else>{{s.n}}</span>
        </div>
        <div class="bi-step-info">
          <div class="bi-step-label">{{s.label}}</div>
          <div class="bi-step-sub">{{s.sub}}</div>
        </div>
      </div>
      <div v-if="i < STEPS.length-1" class="bi-step-line" :class="{ filled: step > s.n, flowing: importing && step===4 && s.n===4 }"></div>
    </template>
  </div>

  <!-- ░░░ STEP 1 — UPLOAD ░░░ -->
  <div v-if="step===1" class="bi-card">
    <div class="bi-card-head">Upload your CSV</div>

    <div class="bi-upload-grid">
      <div class="bi-dropzone-wrap">
        <div
          class="bi-dropzone"
          :class="{dragging, 'has-file': !!fileName}"
          @dragover.prevent="dragging=true"
          @dragleave="dragging=false"
          @drop.prevent="onDrop"
          @click="!fileName && $refs.fileInput.click()"
        >
          <input ref="fileInput" type="file" accept=".csv" style="display:none" @change="onFileChange"/>

          <template v-if="!fileName">
            <div class="bi-dz-icon-stack">
              <svg width="52" height="60" viewBox="0 0 52 60" fill="none">
                <rect x="2" y="2" width="40" height="52" rx="4" fill="#eaf1ff" stroke="#bfdbfe" stroke-width="1.5"/>
                <rect x="10" y="2" width="40" height="52" rx="4" fill="white" stroke="#bfdbfe" stroke-width="1.5"/>
                <text x="30" y="32" text-anchor="middle" font-size="9" font-weight="700" fill="#1a6ef7" font-family="sans-serif">CSV</text>
              </svg>
              <div class="bi-dz-upload-badge">
                <span v-html="icon('upload', 12)"></span>
              </div>
            </div>
            <div class="bi-dz-title">Drag and drop your CSV file here</div>
            <div class="bi-dz-browse">or click to browse</div>
            <div class="bi-dz-sub">.csv files only (UTF-8 encoded)</div>
          </template>

          <template v-else>
            <span class="bi-dz-icon ok" v-html="icon('file-text',30)"></span>
            <div class="bi-dz-title">{{fileName}}</div>
            <div class="bi-dz-sub">{{formatBytes(fileSize)}} · {{parsedRows.length}} row{{parsedRows.length!==1?'s':''}} · {{headers.length}} column{{headers.length!==1?'s':''}}</div>
            <button class="b-btn b-btn-ghost bi-dz-remove" @click.stop="clearFile">
              <span v-html="icon('x',12)"></span> Remove
            </button>
          </template>
        </div>

        <div class="bi-secure-note">
          <span class="bi-secure-icon" v-html="icon('shield',13)"></span>
          <div>
            <div class="bi-secure-title">Your data is secure and private</div>
            <div class="bi-secure-sub">We never store your files.</div>
          </div>
        </div>
      </div>

      <div class="bi-req-panel">
        <div class="bi-req-panel-title">Importing <b>{{currentType.label}}</b></div>
        <div class="bi-req-list-label">This import will understand the following columns:</div>
        <div v-if="currentType.note" class="bi-req-note">{{currentType.note}}</div>
        <div class="bi-req-chip-row">
          <span v-for="f in currentFields" :key="f.key"
            class="bi-field-chip" :class="f.required ? 'bi-field-chip--required' : ''">
            <span class="bi-chip-dot">•</span> {{f.label}}<template v-if="f.required">*</template>
          </span>
        </div>
        <div class="bi-req-hint"><span style="color:#C92A2A;font-weight:600">*</span> Required — rows missing this are skipped</div>
      </div>
    </div>

    <div v-if="parseError" class="bi-error-banner">
      <span v-html="icon('alert-circle',14)"></span> {{parseError}}
    </div>

    <div class="bi-step-actions">
      <span class="bi-step-actions-hint" v-if="parsing">Reading file…</span>
      <button class="b-btn b-btn-primary" :disabled="!parsedRows.length || parsing" @click="goToMapping">
        Continue to Map Columns <span v-html="icon('arrow-right',13)" style="vertical-align:-2px;margin-left:4px"></span>
      </button>
    </div>
  </div>

  <!-- ░░░ STEP 2 — MAP COLUMNS ░░░ -->
  <div v-if="step===2" class="bi-card">
    <div class="bi-card-head-row">
      <div class="bi-card-head">Map your columns</div>
      <div style="display:flex;gap:8px">
        <button class="b-btn b-btn-ghost" @click="autoMapColumns" style="font-size:12px">
          <span v-html="icon('refresh',12)"></span> Auto-map again
        </button>
        <button class="b-btn b-btn-ghost" @click="resetMapping" style="font-size:12px">Clear all</button>
      </div>
    </div>
    <div class="bi-map-sub">Tell us which CSV column feeds which field. We've guessed where we could — check the rest.</div>

    <div class="bi-map-grid">
      <div class="bi-map-table-wrap">
        <table class="b-table bi-map-table">
          <thead>
            <tr><th>CSV Column</th><th>Sample Value</th><th>Maps To</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="h in headers" :key="h">
              <td class="bi-map-col">{{h}}</td>
              <td class="bi-map-sample">{{sampleValue(h) || '—'}}</td>
              <td>
                <select class="nim-input bi-map-select" :value="mapping[h]||''" @change="setMapping(h, $event.target.value)">
                  <option value="">Don't import this column</option>
                  <optgroup label="Required fields">
                    <option v-for="f in requiredFieldsList" :key="f.key" :value="f.key" :disabled="isUsedElsewhere(h,f.key)">{{f.label}}</option>
                  </optgroup>
                  <optgroup label="Optional fields">
                    <option v-for="f in optionalFieldsList" :key="f.key" :value="f.key" :disabled="isUsedElsewhere(h,f.key)">{{f.label}}</option>
                  </optgroup>
                </select>
              </td>
              <td style="text-align:center;width:30px">
                <span v-if="mapping[h]" style="color:#2F9E44" v-html="icon('check',14)"></span>
                <span v-else style="color:#CED4DA" v-html="icon('circle',14)"></span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="bi-req-panel">
        <div class="bi-req-panel-title">Required field coverage</div>
        <div class="bi-coverage-list">
          <div v-for="f in requiredFieldsList" :key="f.key" class="bi-coverage-row">
            <span v-if="targetToHeader[f.key]" style="color:#2F9E44" v-html="icon('check',14)"></span>
            <span v-else style="color:#C92A2A" v-html="icon('x-circle',14)"></span>
            <span class="bi-coverage-field">{{f.label}}</span>
            <span class="bi-coverage-source">{{targetToHeader[f.key] || 'Not mapped'}}</span>
          </div>
        </div>
        <div v-if="!allRequiredMapped" class="bi-warn-banner">
          <span v-html="icon('alert-circle',13)"></span>
          Rows missing a required field will be skipped on import.
        </div>
        <div v-else class="bi-ok-banner">
          <span v-html="icon('check',13)"></span> All required fields are mapped.
        </div>
      </div>
    </div>

    <div class="bi-step-actions">
      <button class="b-btn b-btn-ghost" @click="step=1">← Back</button>
      <button class="b-btn b-btn-primary" @click="goToValidate">
        Preview &amp; Validate <span v-html="icon('arrow-right',13)" style="vertical-align:-2px"></span>
      </button>
    </div>
  </div>

  <!-- ░░░ STEP 3 — VALIDATE & PREVIEW ░░░ -->
  <div v-if="step===3" class="bi-card" style="padding:0;overflow:hidden">
    <div class="bi-card-head-row" style="padding:16px 20px 0">
      <div class="bi-card-head">Validate &amp; preview</div>
      <button class="b-btn b-btn-ghost" @click="downloadFlaggedRows" v-if="counts.skip+counts.fail>0" style="font-size:12px">
        <span v-html="icon('download',12)"></span> Download flagged rows
      </button>
    </div>

    <div class="bi-summary-row">
      <button class="bi-summary-chip" :class="{active: statusFilter==='all'}" @click="setStatusFilter('all')">
        <b>{{counts.total}}</b> Total
      </button>
      <button class="bi-summary-chip green" :class="{active: statusFilter==='ready'}" @click="setStatusFilter('ready')">
        <b>{{counts.ready}}</b> Ready
      </button>
      <button class="bi-summary-chip blue" :class="{active: statusFilter==='notice'}" @click="setStatusFilter('notice')" v-if="counts.notice>0">
        <b>{{counts.notice}}</b> Notices
      </button>
      <button class="bi-summary-chip amber" :class="{active: statusFilter==='skip'}" @click="setStatusFilter('skip')" v-if="counts.skip>0">
        <b>{{counts.skip}}</b> Will skip
      </button>
      <button class="bi-summary-chip red" :class="{active: statusFilter==='fail'}" @click="setStatusFilter('fail')" v-if="counts.fail>0">
        <b>{{counts.fail}}</b> Will fail
      </button>

      <div class="bi-search" style="margin-left:auto">
        <span v-html="icon('search',13)"></span>
        <input v-model="searchQuery" placeholder="Search rows…" @input="page=1"/>
      </div>
    </div>

    <div class="bi-table-wrap">
      <table class="b-table bi-validate-table">
        <thead>
          <tr>
            <th style="width:34px"><input type="checkbox" :checked="allVisibleIncluded" @change="toggleAllVisible($event.target.checked)"/></th>
            <th style="width:40px">#</th>
            <th style="width:28px"></th>
            <th v-for="f in displayFields" :key="f.key">{{f.label}}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in paged" :key="row.idx" :class="'bi-row-'+row.status">
            <td><input type="checkbox" :checked="included[row.idx]" @change="toggleIncluded(row.idx, $event.target.checked)"/></td>
            <td class="c-muted">{{row.rowNumber}}</td>
            <td>
              <span :title="row.issues.map(i=>i.message).join('; ')">
                <span v-if="row.status==='ready'" style="color:#2F9E44" v-html="icon('check',13)"></span>
                <span v-else-if="row.status==='notice'" style="color:#1971C2" v-html="icon('info',13)"></span>
                <span v-else-if="row.status==='skip'" style="color:#E67700" v-html="icon('alert-circle',13)"></span>
                <span v-else style="color:#C92A2A" v-html="icon('x-circle',13)"></span>
              </span>
            </td>
            <td v-for="f in displayFields" :key="f.key" class="bi-cell" @click="startEdit(row.idx, f.key)">
              <input v-if="editing && editing.idx===row.idx && editing.field===f.key"
                v-model="row.data[f.key]" class="bi-cell-input" autofocus
                @blur="editing=null" @keyup.enter="editing=null" @keyup.esc="editing=null"/>
              <span v-else :class="{'bi-cell-empty': !row.data[f.key]}">{{row.data[f.key] || '—'}}</span>
            </td>
          </tr>
          <tr v-if="!paged.length">
            <td :colspan="displayFields.length+3" class="b-empty">No rows match this filter.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="bi-pager">
      <Pagination v-model:page="page" v-model:page-size="pageSize" :total-items="totalItems" />
    </div>

    <div class="bi-footer-bar">
      <button class="b-btn b-btn-ghost" @click="step=2">← Back to Mapping</button>
      <div class="bi-footer-right">
        <span class="c-muted" style="font-size:12.5px">{{includedCount}} of {{counts.total}} rows selected</span>
        <button class="b-btn b-btn-primary" :disabled="!includedCount || !$canCreate('admin')" :title="!$canCreate('admin') ? 'Read-only access' : ''" @click="runImport">
          <span v-html="icon('upload',13)" style="vertical-align:-2px"></span> Import {{includedCount}} Record{{includedCount!==1?'s':''}}
        </button>
      </div>
    </div>
  </div>

  <!-- ░░░ STEP 4 — IMPORTING ░░░ -->
  <div v-if="step===4" class="bi-card bi-importing">
    <div class="bi-spinner"></div>
    <div class="bi-importing-title">Importing your {{currentType.label.toLowerCase()}}…</div>
    <div class="bi-importing-sub">Batch {{importProgress.batchIndex}} of {{importProgress.batchCount}} — {{importProgress.done}} / {{importProgress.total}} rows processed</div>
    <div class="bi-progress-track">
      <div class="bi-progress-fill" :style="{width: importPct+'%'}"></div>
    </div>
    <div class="c-muted" style="font-size:12px">Don't close this tab while the import is running.</div>
  </div>

  <!-- ░░░ STEP 5 — RESULTS ░░░ -->
  <div v-if="step===5" class="bi-card">
    <div class="bi-card-head">Import complete</div>
    <div class="bi-results-grid">
      <div class="bi-result-tile green">
        <div class="bi-result-num">{{result.created}}</div>
        <div class="bi-result-label">Created</div>
      </div>
      <div class="bi-result-tile amber">
        <div class="bi-result-num">{{result.skipped}}</div>
        <div class="bi-result-label">Skipped</div>
      </div>
      <div class="bi-result-tile red">
        <div class="bi-result-num">{{result.errors.length}}</div>
        <div class="bi-result-label">Errors</div>
      </div>
    </div>

    <div v-if="result.errors.length" class="bi-error-section">
      <div class="bi-card-head-row">
        <div style="font-size:12.5px;font-weight:700;color:#C92A2A">Errors ({{result.errors.length}})</div>
        <button class="b-btn b-btn-ghost" @click="downloadErrorReport" style="font-size:12px">
          <span v-html="icon('download',12)"></span> Download error report
        </button>
      </div>
      <div class="bi-error-list">
        <div v-for="(e,i) in result.errors" :key="i" class="bi-error-item">
          <span class="bi-error-row">Row {{e.row}}</span>
          <span class="bi-error-msg">{{e.error}}</span>
        </div>
      </div>
    </div>

    <div class="bi-step-actions">
      <button class="b-btn b-btn-ghost" @click="resetImport">Import Another File</button>
      <button v-if="result.created>0 && currentType.route" class="b-btn b-btn-primary" @click="goToList">
        View {{currentType.label}} →
      </button>
    </div>
  </div>

</div>
</template>

<script setup>
import { ref, reactive, computed } from "vue";
import { useRouter } from "vue-router";
import { apiPOST, apiGET } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { usePagination } from "../composables/usePagination.js";
import { icon } from "../utils/icons.js";
import { GSTIN_REGEX } from "../composables/useValidation.js";
import Pagination from "../components/Pagination.vue";

const { toast } = useToast();
const router = useRouter();

const BATCH_SIZE = 40;

const STEPS = [
  { n: 1, label: "Upload",       sub: "Upload your CSV file" },
  { n: 2, label: "Map Columns",  sub: "Match CSV columns to fields" },
  { n: 3, label: "Validate",     sub: "Review and fix issues" },
  { n: 4, label: "Import",       sub: "Import your data" },
  { n: 5, label: "Done",         sub: "Review summary" },
];

// ── Field definitions mirror api/import_data.py exactly (keys, required-ness,
//    and types) so client-side validation/mapping predicts server behaviour. ──
const TYPES = [
  { key: "Customer",        label: "Customers",      icon: "users",    iconBg: "#eaf1ff", iconColor: "#1a6ef7", route: "/customers", fields: [
    { key: "customer_name", label: "Customer Name", required: true,  type: "text" },
    { key: "customer_type", label: "Customer Type", required: false, type: "text" },
    { key: "email_id",      label: "Email",          required: false, type: "email" },
    { key: "mobile_no",     label: "Mobile",         required: false, type: "text" },
    { key: "phone",         label: "Phone",          required: false, type: "text" },
    { key: "tax_id",        label: "Tax ID / GSTIN", required: false, type: "gstin" },
    { key: "city",          label: "City",           required: false, type: "text" },
    { key: "state",         label: "State",          required: false, type: "text" },
    { key: "country",       label: "Country",        required: false, type: "text" },
    { key: "payment_terms", label: "Payment Terms",  required: false, type: "text" },
  ]},
  { key: "Supplier",        label: "Vendors",        icon: "vendors",  iconBg: "#E8F5E9", iconColor: "#2E7D32", route: "/vendors", fields: [
    { key: "supplier_name", label: "Vendor Name",    required: true,  type: "text" },
    { key: "supplier_type", label: "Vendor Type",    required: false, type: "text" },
    { key: "email_id",      label: "Email",          required: false, type: "email" },
    { key: "mobile_no",     label: "Mobile",         required: false, type: "text" },
    { key: "phone",         label: "Phone",          required: false, type: "text" },
    { key: "tax_id",        label: "Tax ID / GSTIN", required: false, type: "gstin" },
    { key: "city",          label: "City",           required: false, type: "text" },
    { key: "state",         label: "State",          required: false, type: "text" },
    { key: "country",       label: "Country",        required: false, type: "text" },
    { key: "payment_terms", label: "Payment Terms",  required: false, type: "text" },
  ]},
  { key: "Item",            label: "Items",          icon: "box",      iconBg: "#E8F5E9", iconColor: "#388E3C", route: "/inventory/items", fields: [
    { key: "item_name",         label: "Item Name",         required: true,  type: "text" },
    { key: "item_code",         label: "Item Code",         required: false, type: "text" },
    { key: "item_group",        label: "Item Group",        required: false, type: "text" },
    { key: "item_type",         label: "Item Type",         required: false, type: "text" },
    { key: "stock_uom",         label: "Stock UOM",         required: false, type: "text" },
    { key: "standard_rate",     label: "Selling Rate",      required: false, type: "number" },
    { key: "standard_buying_rate", label: "Buying Rate",    required: false, type: "number" },
    { key: "tax_code",          label: "Tax Template",      required: false, type: "text" },
    { key: "hsn_code",          label: "HSN Code",          required: false, type: "text" },
    { key: "description",      label: "Description",       required: false, type: "text" },
    { key: "is_sales_item",    label: "Is Sales Item",     required: false, type: "text" },
    { key: "is_purchase_item", label: "Is Purchase Item",  required: false, type: "text" },
  ]},
  { key: "Sales Invoice",   label: "Invoices",       icon: "fileplus", iconBg: "#FFF3E0", iconColor: "#E65100",
    route: "/invoices",
    note: "One row = one invoice with a single line item.", fields: [
    { key: "customer",     label: "Customer",     required: true,  type: "text" },
    { key: "posting_date", label: "Posting Date", required: false, type: "date" },
    { key: "due_date",     label: "Due Date",     required: false, type: "date" },
    { key: "item_code",    label: "Item Code",    required: true,  type: "text" },
    { key: "qty",          label: "Quantity",     required: false, type: "number" },
    { key: "rate",         label: "Rate",         required: false, type: "number" },
    { key: "tax_type",     label: "Tax Type",     required: false, type: "text" },
    { key: "tax_rate",     label: "Tax Rate %",   required: false, type: "number" },
    { key: "currency",     label: "Currency",     required: false, type: "text" },
    { key: "remarks",      label: "Remarks",      required: false, type: "text" },
  ]},
  { key: "Quotation",       label: "Quotes",         icon: "quote",    iconBg: "#FFF8E1", iconColor: "#F57F17", route: "/quotes",
    note: "One row = one quote with a single line item.", fields: [
    { key: "customer",          label: "Customer",         required: true,  type: "text" },
    { key: "transaction_date",  label: "Transaction Date", required: false, type: "date" },
    { key: "valid_till",        label: "Valid Till",       required: false, type: "date" },
    { key: "item_code",         label: "Item Code",        required: true,  type: "text" },
    { key: "qty",               label: "Quantity",         required: false, type: "number" },
    { key: "rate",              label: "Rate",             required: false, type: "number" },
    { key: "tax_type",          label: "Tax Type",         required: false, type: "text" },
    { key: "tax_rate",          label: "Tax Rate %",       required: false, type: "number" },
    { key: "currency",          label: "Currency",         required: false, type: "text" },
    { key: "remarks",           label: "Remarks",          required: false, type: "text" },
  ]},
  { key: "Sales Order",     label: "Sales Orders",   icon: "order",    iconBg: "#E0F7FA", iconColor: "#00838F", route: "/sales-orders",
    note: "One row = one order with a single line item.", fields: [
    { key: "customer",         label: "Customer",         required: true,  type: "text" },
    { key: "transaction_date", label: "Transaction Date", required: false, type: "date" },
    { key: "delivery_date",    label: "Delivery Date",    required: false, type: "date" },
    { key: "item_code",        label: "Item Code",        required: true,  type: "text" },
    { key: "qty",              label: "Quantity",         required: false, type: "number" },
    { key: "rate",             label: "Rate",             required: false, type: "number" },
    { key: "tax_type",         label: "Tax Type",         required: false, type: "text" },
    { key: "tax_rate",         label: "Tax Rate %",       required: false, type: "number" },
    { key: "currency",         label: "Currency",         required: false, type: "text" },
    { key: "remarks",          label: "Remarks",          required: false, type: "text" },
  ]},
  { key: "Purchase Invoice", label: "Bills",          icon: "purchase", iconBg: "#FFF3E0", iconColor: "#BF360C", route: "/bills",
    note: "One row = one bill with a single line item; vendor must already exist.", fields: [
    { key: "supplier",     label: "Vendor",       required: true,  type: "text" },
    { key: "bill_no",      label: "Bill No.",     required: false, type: "text" },
    { key: "bill_date",    label: "Bill Date",    required: false, type: "date" },
    { key: "posting_date", label: "Posting Date", required: false, type: "date" },
    { key: "due_date",     label: "Due Date",     required: false, type: "date" },
    { key: "item_code",    label: "Item Code",    required: true,  type: "text" },
    { key: "qty",          label: "Quantity",     required: false, type: "number" },
    { key: "rate",         label: "Rate",         required: false, type: "number" },
    { key: "tax_type",     label: "Tax Type",     required: false, type: "text" },
    { key: "tax_rate",     label: "Tax Rate %",   required: false, type: "number" },
    { key: "currency",     label: "Currency",     required: false, type: "text" },
    { key: "remarks",      label: "Remarks",      required: false, type: "text" },
  ]},
  { key: "Expense",         label: "Expenses",       icon: "expense",  iconBg: "#FFF8E1", iconColor: "#E65100", route: "/expenses",
    note: "Expense type, amount, account and payment source are all required.", fields: [
    { key: "posting_date",     label: "Posting Date",     required: false, type: "date" },
    { key: "expense_type",     label: "Expense Type",     required: true,  type: "text" },
    { key: "description",      label: "Description",      required: false, type: "text" },
    { key: "amount",           label: "Amount",           required: true,  type: "number" },
    { key: "gst_rate",         label: "GST Rate %",       required: false, type: "number" },
    { key: "expense_account",  label: "Expense Account",  required: true,  type: "text" },
    { key: "paid_through",     label: "Paid Through",     required: true,  type: "text" },
    { key: "vendor",           label: "Vendor",           required: false, type: "text" },
    { key: "reference_no",     label: "Reference No.",    required: false, type: "text" },
    { key: "notes",            label: "Notes",            required: false, type: "text" },
  ]},
  { key: "Purchase Order",  label: "Purchase Orders", icon: "truck",   iconBg: "#E8EAF6", iconColor: "#3949AB", route: "/purchase-orders",
    note: "One row = one PO with a single line item; vendor must already exist.", fields: [
    { key: "supplier",                 label: "Vendor",                required: true,  type: "text" },
    { key: "transaction_date",         label: "Transaction Date",      required: false, type: "date" },
    { key: "expected_delivery_date",   label: "Expected Delivery",     required: false, type: "date" },
    { key: "item_code",                label: "Item Code",             required: true,  type: "text" },
    { key: "qty",                      label: "Quantity",              required: false, type: "number" },
    { key: "rate",                     label: "Rate",                  required: false, type: "number" },
    { key: "tax_type",                 label: "Tax Type",              required: false, type: "text" },
    { key: "tax_rate",                 label: "Tax Rate %",            required: false, type: "number" },
    { key: "currency",                 label: "Currency",              required: false, type: "text" },
    { key: "remarks",                  label: "Remarks",               required: false, type: "text" },
  ]},
];

const CATEGORIES = [
  { key: "contacts",  label: "Contacts",  icon: "users" },
  { key: "sales",     label: "Sales",     icon: "fileplus" },
  { key: "purchases", label: "Purchases", icon: "purchase" },
];

const CATEGORY_MAP = {
  contacts:  ["Customer", "Supplier"],
  sales:     ["Sales Invoice", "Quotation", "Sales Order"],
  purchases: ["Purchase Invoice", "Purchase Order", "Expense", "Item"],
};

const category = ref("contacts");

const filteredTypes = computed(() =>
  TYPES.filter(t => CATEGORY_MAP[category.value]?.includes(t.key))
);

function switchCategory(cat) {
  category.value = cat;
  // Auto-select first type in this category if current selection not in it
  if (!CATEGORY_MAP[cat].includes(dtype.value)) {
    switchType(CATEGORY_MAP[cat][0]);
  }
}

const dtype = ref("Customer");
const step  = ref(1);

// Step 1 — upload
const dragging   = ref(false);
const parsing    = ref(false);
const fileName   = ref("");
const fileSize   = ref(0);
const parsedRows = ref([]);   // raw rows keyed by original CSV header
const headers    = ref([]);   // raw CSV headers
const parseError = ref("");

// Step 2 — mapping
const mapping = reactive({}); // { [csvHeader]: targetFieldKey | "" }

// Step 3 — validate/preview
const editableRows  = ref([]);   // [{ [targetFieldKey]: value }] snapshot, editable
const included      = ref([]);   // parallel boolean array
const searchQuery   = ref("");
const statusFilter  = ref("all");
const editing       = ref(null); // { idx, field }

// Step 4 — import
const importing = ref(false);
const importProgress = reactive({ done: 0, total: 0, batchIndex: 0, batchCount: 0 });

// Step 5 — results
const result = ref({ created: 0, skipped: 0, errors: [] });

const currentType   = computed(() => TYPES.find(t => t.key === dtype.value));
const currentFields = computed(() => currentType.value.fields);
const requiredFieldsList = computed(() => currentFields.value.filter(f => f.required));
const optionalFieldsList = computed(() => currentFields.value.filter(f => !f.required));

function requiredCountFor(t) { return t.fields.filter(f => f.required).length; }

function stepClass(n) {
  if (step.value === n) return "active";
  if (step.value > n) return "done";
  return "";
}
function jumpTo(n) {
  // Only allow jumping backward to a step already passed.
  if (n < step.value && n >= 1) step.value = n;
}

// ───────────────────────────── Step switching / reset ─────────────────────
function switchType(k) {
  dtype.value = k;
  resetImport();
}

function resetImport() {
  step.value = 1;
  fileName.value = ""; fileSize.value = 0;
  parsedRows.value = []; headers.value = [];
  parseError.value = ""; parsing.value = false;
  Object.keys(mapping).forEach(k => delete mapping[k]);
  editableRows.value = []; included.value = [];
  searchQuery.value = ""; statusFilter.value = "all"; page.value = 1; editing.value = null;
  importing.value = false;
  importProgress.done = 0; importProgress.total = 0; importProgress.batchIndex = 0; importProgress.batchCount = 0;
  result.value = { created: 0, skipped: 0, errors: [] };
}

function clearFile() {
  fileName.value = ""; fileSize.value = 0;
  parsedRows.value = []; headers.value = [];
  parseError.value = "";
  Object.keys(mapping).forEach(k => delete mapping[k]);
}

// ───────────────────────────── Step 1: file handling ───────────────────────
function onDrop(e) {
  dragging.value = false;
  const file = e.dataTransfer.files[0];
  if (file) readFile(file);
}
function onFileChange(e) {
  const file = e.target.files[0];
  if (file) readFile(file);
  e.target.value = "";
}
function readFile(file) {
  if (!file.name.toLowerCase().endsWith(".csv")) {
    parseError.value = "Only .csv files are supported";
    return;
  }
  fileName.value = file.name;
  fileSize.value = file.size;
  parseError.value = "";
  parsing.value = true;
  const reader = new FileReader();
  reader.onload = (e) => { parseCSV(decodeCSVBuffer(e.target.result)); parsing.value = false; };
  reader.onerror = () => { parseError.value = "Could not read that file"; parsing.value = false; };
  reader.readAsArrayBuffer(file);
}

// Excel's "CSV (Comma delimited)" export (as opposed to "CSV UTF-8") writes
// smart punctuation — em dashes, curly quotes — in Windows-1252, not UTF-8.
// Forcing a UTF-8 decode on that file turns every such character into a
// U+FFFD replacement character (the "�" seen in place of an em dash after
// import). Detect this by attempting a strict UTF-8 decode first; if the
// byte sequence isn't valid UTF-8, it throws, and we fall back to
// Windows-1252 — which covers the vast majority of real-world Excel exports.
function decodeCSVBuffer(buffer) {
  const bytes = new Uint8Array(buffer);
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch (e) {
    return new TextDecoder("windows-1252").decode(bytes);
  }
}

function parseCSV(text) {
  if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1); // strip BOM (Excel exports)
  const lines = text.trim().split(/\r?\n/);
  if (lines.length < 2) {
    parseError.value = "CSV must have a header row and at least one data row";
    parsedRows.value = [];
    return;
  }
  const hdrs = lines[0].split(",").map(h => h.trim().replace(/^"|"$/g, ""));
  headers.value = hdrs;
  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    const vals = splitCSVLine(line);
    const row = {};
    hdrs.forEach((h, idx) => { row[h] = (vals[idx] || "").trim().replace(/^"|"$/g, ""); });
    rows.push(row);
  }
  if (!rows.length) {
    parseError.value = "No data rows found in CSV";
    parsedRows.value = [];
    return;
  }
  parsedRows.value = rows;
  parseError.value = "";
  autoMapColumns();
}

function splitCSVLine(line) {
  const result = [];
  let cur = "", inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') { inQuotes = !inQuotes; }
    else if (ch === "," && !inQuotes) { result.push(cur); cur = ""; }
    else { cur += ch; }
  }
  result.push(cur);
  return result;
}

function sampleValue(h) {
  const row = parsedRows.value.find(r => (r[h] || "").trim());
  return row ? row[h] : "";
}

function formatBytes(n) {
  if (!n) return "0 B";
  if (n < 1024) return n + " B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
  return (n / (1024 * 1024)).toFixed(1) + " MB";
}

async function downloadSample() {
  try {
    const csv = await apiGET("zoho_books_clone.api.import_data.get_sample_csv", { doctype: dtype.value });
    downloadBlob(csv, `sample_${dtype.value.toLowerCase().replace(/ /g,"_")}_import.csv`, "text/csv");
  } catch (e) { toast.error("Could not download sample: " + e.message); }
}

// ───────────────────────────── Step 2: column mapping ──────────────────────
function norm(s) { return (s || "").toLowerCase().replace(/[^a-z0-9]/g, ""); }

function autoMapColumns() {
  const used = new Set();
  for (const h of headers.value) {
    const nh = norm(h);
    let match = currentFields.value.find(f => !used.has(f.key) && (norm(f.key) === nh || norm(f.label) === nh));
    if (!match) {
      match = currentFields.value.find(f => !used.has(f.key) && nh && (nh.includes(norm(f.key)) || norm(f.key).includes(nh)));
    }
    mapping[h] = match ? match.key : "";
    if (match) used.add(match.key);
  }
}
function resetMapping() {
  headers.value.forEach(h => { mapping[h] = ""; });
}
function setMapping(header, target) {
  if (target) {
    for (const h of headers.value) {
      if (h !== header && mapping[h] === target) mapping[h] = "";
    }
  }
  mapping[header] = target;
}
function isUsedElsewhere(header, fieldKey) {
  return Object.entries(mapping).some(([h, t]) => h !== header && t === fieldKey);
}

const targetToHeader = computed(() => {
  const o = {};
  for (const h of headers.value) { if (mapping[h]) o[mapping[h]] = h; }
  return o;
});
const allRequiredMapped = computed(() => requiredFieldsList.value.every(f => !!targetToHeader.value[f.key]));

const mappedRows = computed(() => parsedRows.value.map(r => {
  const o = {};
  for (const h of headers.value) { const t = mapping[h]; if (t) o[t] = r[h]; }
  return o;
}));

function goToMapping() {
  if (!parsedRows.value.length) return;
  step.value = 2;
}

function goToValidate() {
  editableRows.value = mappedRows.value.map(r => ({ ...r }));
  included.value = editableRows.value.map(() => true);
  searchQuery.value = ""; statusFilter.value = "all"; page.value = 1;
  step.value = 3;
}

// ───────────────────────────── Step 3: validation ──────────────────────────
function isValidDateStr(v) {
  if (!v) return true;
  v = v.trim();
  if (!v) return true;
  if (/^\d{4}-\d{2}-\d{2}$/.test(v)) return true;
  if (/^\d{4}\/\d{1,2}\/\d{1,2}$/.test(v)) return true;
  const m = v.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$/);
  if (m) {
    const day = +m[1], month = +m[2];
    if (day > 12 || month <= 12) return true;
  }
  return false;
}
function isNumericStr(v) {
  if (v === null || v === undefined || String(v).trim() === "") return true;
  return !isNaN(parseFloat(String(v).replace(/,/g, "")));
}

function validateRow(data, fields) {
  const issues = [];
  let missing = false, badDate = false, badNumber = false, badGstin = false;
  for (const f of fields) {
    const val = (data[f.key] ?? "").toString().trim();
    if (f.required && !val) {
      missing = true;
      issues.push({ field: f.key, kind: "missing", message: `${f.label} is required` });
    }
    if (f.type === "date" && val && !isValidDateStr(val)) {
      badDate = true;
      issues.push({ field: f.key, kind: "date", message: `${f.label} "${val}" isn't a recognised date format` });
    }
    if (f.type === "number" && val && !isNumericStr(val)) {
      badNumber = true;
      issues.push({ field: f.key, kind: "number", message: `${f.label} "${val}" isn't numeric — will be treated as 0` });
    }
    if (f.type === "gstin" && val && !GSTIN_REGEX.test(val.toUpperCase())) {
      badGstin = true;
      issues.push({ field: f.key, kind: "gstin", message: `${f.label} "${val}" isn't a valid GSTIN (e.g. 27AAPFU0939F1ZV)` });
    }
  }
  let status = "ready";
  if (badDate) status = "fail";
  else if (missing) status = "skip";
  else if (badNumber || badGstin) status = "notice";
  return { issues, status };
}

const validatedRows = computed(() => editableRows.value.map((data, idx) => {
  const { issues, status } = validateRow(data, currentFields.value);
  return { idx, rowNumber: idx + 1, data, issues, status };
}));

const counts = computed(() => {
  const c = { total: validatedRows.value.length, ready: 0, notice: 0, skip: 0, fail: 0 };
  for (const r of validatedRows.value) c[r.status]++;
  return c;
});

const displayFields = computed(() => currentFields.value.filter(f => targetToHeader.value[f.key]));

const filteredRows = computed(() => {
  let rows = validatedRows.value;
  if (statusFilter.value !== "all") rows = rows.filter(r => r.status === statusFilter.value);
  const q = searchQuery.value.trim().toLowerCase();
  if (q) rows = rows.filter(r => Object.values(r.data).some(v => String(v || "").toLowerCase().includes(q)));
  return rows;
});

// Shared client-side pagination (same component used across list pages)
const { page, pageSize, paged, totalItems } = usePagination(filteredRows, { storageKey: "bulkimport" });

function setStatusFilter(f) { statusFilter.value = f; page.value = 1; }

const includedCount = computed(() => included.value.filter(Boolean).length);
const allVisibleIncluded = computed(() => paged.value.length > 0 && paged.value.every(r => included.value[r.idx]));
function toggleIncluded(idx, val) { included.value[idx] = val; }
function toggleAllVisible(val) { paged.value.forEach(r => { included.value[r.idx] = val; }); }

function startEdit(idx, field) { editing.value = { idx, field }; }

// ───────────────────────────── Step 4: chunked import ──────────────────────
async function runImport() {
  const includedIdx = editableRows.value.map((_, i) => i).filter(i => included.value[i]);
  if (!includedIdx.length) return;

  importing.value = true;
  step.value = 4;

  const batches = [];
  for (let i = 0; i < includedIdx.length; i += BATCH_SIZE) batches.push(includedIdx.slice(i, i + BATCH_SIZE));

  importProgress.done = 0;
  importProgress.total = includedIdx.length;
  importProgress.batchIndex = 0;
  importProgress.batchCount = batches.length;

  const merged = { created: 0, skipped: 0, errors: [] };

  for (const batch of batches) {
    importProgress.batchIndex++;
    const rows = batch.map(i => editableRows.value[i]);
    try {
      const res = await apiPOST("zoho_books_clone.api.import_data.bulk_import", {
        doctype: dtype.value,
        rows_json: JSON.stringify(rows),
      });
      merged.created += res.created || 0;
      merged.skipped += res.skipped || 0;
      (res.errors || []).forEach(e => {
        const originalIdx = batch[(e.row || 1) - 1];
        merged.errors.push({ row: originalIdx != null ? originalIdx + 1 : e.row, data: e.data, error: e.error });
      });
    } catch (e) {
      merged.errors.push({ row: "—", data: {}, error: e.message || "This batch failed to import" });
    }
    importProgress.done += batch.length;
  }

  result.value = merged;
  importing.value = false;
  step.value = 5;
}

const importPct = computed(() => importProgress.total ? Math.round((importProgress.done / importProgress.total) * 100) : 0);

// ───────────────────────────── CSV export helpers ──────────────────────────
function toCSVField(v) {
  v = (v === undefined || v === null) ? "" : String(v);
  if (/[",\n]/.test(v)) v = '"' + v.replace(/"/g, '""') + '"';
  return v;
}
function downloadCSV(filename, headerArr, rowsArr) {
  const lines = [headerArr.map(toCSVField).join(",")];
  rowsArr.forEach(r => lines.push(r.map(toCSVField).join(",")));
  downloadBlob(lines.join("\n"), filename, "text/csv");
}
function downloadBlob(content, filename, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

function downloadFlaggedRows() {
  const flagged = validatedRows.value.filter(r => r.status === "skip" || r.status === "fail");
  const headerArr = ["Row", "Issues", ...currentFields.value.map(f => f.label)];
  const rowsArr = flagged.map(r => [r.rowNumber, r.issues.map(i => i.message).join("; "), ...currentFields.value.map(f => r.data[f.key] || "")]);
  downloadCSV(`flagged_${dtype.value.toLowerCase().replace(/ /g, "_")}.csv`, headerArr, rowsArr);
}

function downloadErrorReport() {
  const headerArr = ["Row", "Error", ...currentFields.value.map(f => f.label)];
  const rowsArr = result.value.errors.map(e => [e.row, e.error, ...currentFields.value.map(f => (e.data && e.data[f.key]) || "")]);
  downloadCSV(`import_errors_${dtype.value.toLowerCase().replace(/ /g, "_")}.csv`, headerArr, rowsArr);
}

function goToList() {
  if (currentType.value?.route) router.push(currentType.value.route);
}
</script>


<style scoped>
.bi-page { display: flex; flex-direction: column; gap: 14px; padding: 24px; }

/* ── Header ── */
.bi-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; padding-bottom: 2px; }
.bi-title { font-size: 20px; font-weight: 800; color: #111827; letter-spacing: -0.3px; }
.bi-subtitle { font-size: 13px; color: #6B7280; margin-top: 3px; }

/* Layout only — visual styling comes from the shared .sales-btn-ghost */
.bi-download-btn { white-space: nowrap; flex-shrink: 0; }

/* ── Category tabs + type cards wrapper ── */
.bi-category-section {
  background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; overflow: hidden;
}
.bi-category-tabs {
  display: flex; border-bottom: 1px solid #E5E7EB; padding: 0 16px;
}
.bi-cat-tab {
  padding: 11px 18px; font-size: 13px; font-weight: 600; color: #6B7280;
  border: none; background: transparent; cursor: pointer;
  border-bottom: 2px solid transparent; margin-bottom: -1px;
  transition: color .12s, border-color .12s; display: inline-flex; align-items: center;
}
.bi-cat-tab:hover { color: #374151; }
.bi-cat-tab.active { color: #1a6ef7; border-bottom-color: #1a6ef7; }

/* ── Type selector cards ── */
.bi-type-row {
  display: flex; gap: 0; padding: 12px;
  overflow-x: auto;
}
.bi-type-card {
  flex: 1 1 0; min-width: 120px; max-width: 220px; position: relative;
  display: flex; flex-direction: column; align-items: flex-start; gap: 4px;
  padding: 12px 13px; border-radius: 10px;
  border: 1.5px solid transparent; background: #F9FAFB; cursor: pointer;
  margin: 0 4px;
  transition: border-color .12s, background .12s, box-shadow .12s;
}
.bi-type-card:hover { border-color: #bfdbfe; background: #fff; box-shadow: 0 1px 6px rgba(26,110,247,.07); }
.bi-type-card.active { border-color: #1a6ef7; background: #fff; box-shadow: 0 0 0 3px rgba(26,110,247,.09); }
.bi-type-icon-wrap {
  width: 36px; height: 36px; border-radius: 9px;
  display: flex; align-items: center; justify-content: center; margin-bottom: 5px;
}
.bi-type-icon { display: flex; align-items: center; }
.bi-type-label { font-size: 13px; font-weight: 700; color: #111827; }
.bi-type-req { font-size: 11px; color: #9CA3AF; }
.bi-type-card.active .bi-type-req { color: #1a6ef7; }
.bi-type-check {
  position: absolute; top: 8px; right: 8px;
  width: 17px; height: 17px; border-radius: 50%;
  background: #1a6ef7; color: #fff;
  display: flex; align-items: center; justify-content: center;
}

/* ── Stepper ── */
.bi-stepper {
  display: flex; align-items: center;
  padding: 14px 20px; background: #fff; border: 1px solid #E5E7EB; border-radius: 14px;
}
.bi-step { display: flex; align-items: center; gap: 9px; cursor: default; flex: 0 0 auto; }
.bi-step.done { cursor: pointer; }
.bi-step-dot {
  width: 28px; height: 28px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; background: #fff; color: #9CA3AF;
  border: 2px solid #D1D5DB; transition: all .15s;
}
.bi-step.active .bi-step-dot { background: #1a6ef7; border-color: #1a6ef7; color: #fff; box-shadow: 0 0 0 3px rgba(26,110,247,.15); }
.bi-step.done .bi-step-dot { background: #ECFDF5; border-color: #6EE7B7; color: #059669; }
.bi-step-info { display: flex; flex-direction: column; gap: 1px; }
.bi-step-label { font-size: 12px; font-weight: 600; color: #9CA3AF; white-space: nowrap; }
.bi-step.active .bi-step-label { color: #1a6ef7; }
.bi-step.done .bi-step-label { color: #059669; }
.bi-step-sub { font-size: 11px; color: #D1D5DB; white-space: nowrap; }
.bi-step.active .bi-step-sub { color: #93C5FD; }
.bi-step-line { flex: 1 1 auto; height: 2px; background: #E5E7EB; margin: 0 10px; min-width: 20px; position: relative; overflow: hidden; }
.bi-step-line.filled { background: #6EE7B7; }
.bi-step-line.flowing::after {
  content: ""; position: absolute; inset: 0;
  background: repeating-linear-gradient(90deg, #1a6ef7 0 8px, transparent 8px 16px);
  animation: bi-flow 0.6s linear infinite;
}
@keyframes bi-flow { from { transform: translateX(-16px); } to { transform: translateX(0); } }

/* ── Cards ── */
.bi-card { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; padding: 22px; }
.bi-card-head { font-size: 14px; font-weight: 700; color: #111827; margin-bottom: 6px; }
.bi-card-head-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 4px; }

/* ── Step 1: Upload ── */
.bi-upload-grid { display: grid; grid-template-columns: 1.2fr 1fr; gap: 20px; margin-top: 16px; }
.bi-dropzone-wrap { display: flex; flex-direction: column; gap: 12px; }
.bi-dropzone {
  border: 2px dashed #bfdbfe; border-radius: 14px; padding: 44px 24px;
  text-align: center; cursor: pointer;
  transition: background .15s, border-color .15s; background: #f8faff;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 4px; min-height: 230px;
}
.bi-dropzone:hover, .bi-dropzone.dragging { background: #eaf1ff; border-color: #1a6ef7; }
.bi-dropzone.has-file { cursor: default; border-style: solid; border-color: #6EE7B7; background: #F0FDF9; }
.bi-dz-icon-stack { position: relative; width: 60px; height: 66px; margin-bottom: 12px; }
.bi-dz-upload-badge {
  position: absolute; bottom: 0; right: -4px;
  width: 22px; height: 22px; border-radius: 50%;
  background: #1a6ef7; color: #fff; display: flex; align-items: center; justify-content: center;
  border: 2px solid #f8faff;
}
.bi-dz-title { font-size: 14px; font-weight: 700; color: #374151; }
.bi-dz-browse { font-size: 13px; color: #1a6ef7; font-weight: 500; margin-top: 3px; }
.bi-dz-sub { font-size: 12px; color: #9CA3AF; margin-top: 8px; }
.bi-dz-icon { color: #059669; margin-bottom: 4px; }
.bi-dz-icon.ok { color: #059669; }
.bi-dz-remove { margin-top: 10px; font-size: 11.5px; padding: 4px 10px; }
.bi-secure-note {
  display: flex; align-items: flex-start; gap: 8px;
  background: #eaf1ff; border-radius: 8px; padding: 9px 12px;
}
.bi-secure-icon { color: #1a6ef7; margin-top: 1px; flex-shrink: 0; }
.bi-secure-title { font-size: 12px; font-weight: 600; color: #1a6ef7; }
.bi-secure-sub { font-size: 11px; color: #6B7280; }
.bi-req-panel { padding: 18px; border: 1px solid #E5E7EB; border-radius: 12px; background: #FAFAFA; display: flex; flex-direction: column; }
.bi-req-panel-title { font-size: 14px; font-weight: 700; color: #111827; margin-bottom: 4px; }
.bi-req-list-label { font-size: 12px; color: #6B7280; margin-bottom: 12px; }
.bi-req-note { font-size: 11.5px; color: #9CA3AF; margin-bottom: 10px; }
.bi-req-chip-row { display: flex; flex-wrap: wrap; gap: 7px; }
.bi-field-chip {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 500;
  border: 1px solid #E5E7EB; background: #fff; color: #374151;
}
.bi-field-chip--required { background: #FEF2F2; border-color: #FECACA; color: #B91C1C; }
.bi-chip-dot { font-size: 10px; }
.bi-req-hint { font-size: 11.5px; color: #9CA3AF; margin-top: 14px; }
.bi-error-banner {
  margin-top: 14px; background: #FEF2F2; border: 1px solid #FECACA; color: #B91C1C;
  border-radius: 8px; padding: 8px 12px; font-size: 12.5px; display: flex; align-items: center; gap: 8px;
}
.bi-step-actions { margin-top: 20px; display: flex; justify-content: flex-end; align-items: center; gap: 10px; }
.bi-step-actions-hint { font-size: 12px; color: #9CA3AF; margin-right: auto; }

/* ── Step 2 ── */
.bi-map-sub { font-size: 12px; color: #9CA3AF; margin-bottom: 14px; }
.bi-map-grid { display: grid; grid-template-columns: 1.6fr 1fr; gap: 16px; align-items: start; }
.bi-map-table-wrap { border: 1px solid #E5E7EB; border-radius: 10px; overflow: hidden; max-height: 420px; overflow-y: auto; }
.bi-map-col { font-weight: 600; font-size: 12.5px; color: #111827; }
.bi-map-sample { font-size: 11.5px; color: #9CA3AF; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bi-map-select { font-size: 12px; padding: 5px 8px; width: 100%; }
.bi-coverage-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
.bi-coverage-row { display: flex; align-items: center; gap: 7px; font-size: 12px; }
.bi-coverage-field { font-weight: 600; color: #111827; }
.bi-coverage-source { color: #9CA3AF; margin-left: auto; font-size: 11.5px; }
.bi-warn-banner, .bi-ok-banner { border-radius: 8px; padding: 8px 10px; font-size: 11.5px; display: flex; align-items: center; gap: 6px; }
.bi-warn-banner { background: #FFFBEB; color: #D97706; border: 1px solid #FDE68A; }
.bi-ok-banner { background: #ECFDF5; color: #059669; border: 1px solid #6EE7B7; }

/* ── Step 3 ── */
.bi-summary-row { display: flex; gap: 8px; align-items: center; padding: 12px 20px; border-bottom: 1px solid #F3F4F6; flex-wrap: wrap; }
.bi-summary-chip { border: 1px solid #E5E7EB; background: #fff; border-radius: 18px; padding: 5px 12px; font-size: 12px; color: #374151; cursor: pointer; display: flex; gap: 5px; align-items: center; }
.bi-summary-chip.active { background: #1a6ef7; color: #fff; border-color: #1a6ef7; }
.bi-summary-chip.green.active { background: #059669; border-color: #059669; }
.bi-summary-chip.blue.active { background: #1D4ED8; border-color: #1D4ED8; }
.bi-summary-chip.amber.active { background: #D97706; border-color: #D97706; }
.bi-summary-chip.red.active { background: #DC2626; border-color: #DC2626; }
.bi-search { display: inline-flex; align-items: center; gap: 6px; background: #fff; border: 1px solid #E5E7EB; border-radius: 8px; padding: 5px 10px; color: #9CA3AF; }
.bi-search input { border: none; outline: none; background: transparent; font: inherit; width: 160px; }
.bi-table-wrap { overflow-x: auto; max-height: 420px; overflow-y: auto; }
.bi-validate-table th { white-space: nowrap; }
.bi-row-skip { background: #FFFBEB; }
.bi-row-fail { background: #FEF2F2; }
.bi-cell { font-size: 12px; white-space: nowrap; cursor: text; }
.bi-cell:hover { background: #f8faff; }
.bi-cell-empty { color: #D1D5DB; }
.bi-cell-input { font: inherit; font-size: 12px; border: 1px solid #1a6ef7; border-radius: 4px; padding: 2px 5px; width: 100%; min-width: 80px; }
.bi-pager { display: flex; align-items: center; justify-content: space-between; padding: 10px 20px; border-top: 1px solid #F3F4F6; }
.bi-footer-bar { display: flex; align-items: center; justify-content: space-between; padding: 14px 20px; border-top: 1px solid #F3F4F6; }
.bi-footer-right { display: flex; align-items: center; gap: 12px; }

/* ── Step 4 ── */
.bi-importing { display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 60px 20px; text-align: center; }
.bi-spinner { width: 38px; height: 38px; border-radius: 50%; border: 3px solid #E5E7EB; border-top-color: #1a6ef7; animation: bi-spin 0.8s linear infinite; }
@keyframes bi-spin { to { transform: rotate(360deg); } }
.bi-importing-title { font-size: 14px; font-weight: 700; color: #111827; }
.bi-importing-sub { font-size: 12.5px; color: #9CA3AF; }
.bi-progress-track { width: 100%; max-width: 360px; height: 8px; border-radius: 6px; background: #F3F4F6; overflow: hidden; margin: 6px 0; }
.bi-progress-fill { height: 100%; background: linear-gradient(90deg, #1a6ef7, #1a6ef7); transition: width .25s ease; }

/* ── Step 5 ── */
.bi-results-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 12px; margin: 16px 0 20px; }
.bi-result-tile { border-radius: 12px; padding: 18px; text-align: center; border: 1px solid; }
.bi-result-tile.green { background: #ECFDF5; border-color: #6EE7B7; }
.bi-result-tile.amber { background: #FFFBEB; border-color: #FCD34D; }
.bi-result-tile.red   { background: #FEF2F2; border-color: #FECACA; }
.bi-result-num { font-size: 30px; font-weight: 800; }
.bi-result-tile.green .bi-result-num { color: #059669; }
.bi-result-tile.amber .bi-result-num { color: #D97706; }
.bi-result-tile.red   .bi-result-num { color: #DC2626; }
.bi-result-label { font-size: 12px; font-weight: 600; margin-top: 4px; }
.bi-result-tile.green .bi-result-label { color: #059669; }
.bi-result-tile.amber .bi-result-label { color: #D97706; }
.bi-result-tile.red   .bi-result-label { color: #DC2626; }
.bi-error-section { margin-bottom: 16px; }
.bi-error-list { max-height: 220px; overflow-y: auto; border: 1px solid #FECACA; border-radius: 8px; margin-top: 8px; }
.bi-error-item { padding: 8px 12px; font-size: 12px; border-bottom: 1px solid #FEF2F2; display: flex; gap: 10px; }
.bi-error-item:last-child { border-bottom: none; }
.bi-error-row { font-weight: 600; color: #9CA3AF; flex-shrink: 0; }
.bi-error-msg { color: #DC2626; }

/* Blue focus rings, matching the rest of the app */
.bi-map-select:focus, .bi-search:focus-within, .bi-cell-input:focus {
  border-color: #1a6ef7; outline: none;
}

/* ── Responsive ladder (mirrors styles/list.css breakpoints) ── */
@media (max-width: 1023px) {
  .bi-page { padding: 16px; }
  .bi-upload-grid, .bi-map-grid { grid-template-columns: 1fr; }
}
@media (max-width: 767px) {
  .bi-page { padding: 12px; gap: 12px; }
  .bi-head { flex-direction: column; align-items: stretch; }
  .bi-stepper { overflow-x: auto; }
  .bi-step-sub { display: none; }
  .bi-step-label { font-size: 11px; }
  .bi-results-grid { grid-template-columns: 1fr; }
  .bi-type-card { min-width: 130px; }
  .bi-card { padding: 18px; }
}
@media (max-width: 599px) {
  .bi-page { padding: 10px; }
  .bi-summary-row { gap: 6px; }
  .bi-search { margin-left: 0 !important; width: 100%; }
  .bi-search input { width: 100%; }
  .bi-footer-bar, .bi-step-actions { flex-direction: column; align-items: stretch; gap: 10px; }
  .bi-footer-right { flex-direction: column; align-items: stretch; gap: 8px; }
  .bi-footer-right .b-btn, .bi-step-actions .b-btn { width: 100%; justify-content: center; }
  .bi-step-actions-hint { margin-right: 0; text-align: center; }
  .bi-card { padding: 16px; }
}
@media (max-width: 479px) {
  .bi-page { padding: 8px; }
  .bi-step-dot { width: 24px; height: 24px; font-size: 11px; }
  .bi-step-label { font-size: 10px; }
  .bi-step-line { min-width: 14px; margin: 0 6px; }
  .bi-type-card { min-width: 120px; }
  .bi-cell { font-size: 11.5px; }
}
</style>