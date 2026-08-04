<template>
<div class="b-page jen-page">

  <div class="jen-info-banner">
    <span v-html="icon('info',15)" style="flex-shrink:0"></span>
    <span>Journal entries record any financial transaction not covered by Sales/Purchase. Total <strong>Debits must equal Credits</strong> in every entry.</span>
  </div>

  <div class="jen-sum-strip">
    <div class="jen-sum-card">
      <div class="jen-sum-lbl">Total Entries</div>
      <div class="jen-sum-val">{{summary.total}}</div>
    </div>
    <div class="jen-sum-card">
      <div class="jen-sum-lbl" style="color:#3b5bdb">This Month</div>
      <div class="jen-sum-val" style="color:#3b5bdb">{{summary.month}}</div>
    </div>
    <div class="jen-sum-card">
      <div class="jen-sum-lbl" style="color:#2f9e44">Total Debits</div>
      <div class="jen-sum-val" style="color:#2f9e44">{{summary.totalDr>=1000?'₹'+(summary.totalDr/1000).toFixed(1)+'K':fmtINR(summary.totalDr)||'₹0'}}</div>
    </div>
    <div class="jen-sum-card">
      <div class="jen-sum-lbl" style="color:#c92a2a">Drafts</div>
      <div class="jen-sum-val" style="color:#c92a2a">{{summary.drafts}}</div>
    </div>
  </div>

  <!-- ── Desktop action bar (hidden on 375–425px) ── -->
  <div class="b-action-bar jen-desktop-bar" style="margin-bottom:14px;flex-wrap:wrap;gap:10px">
    <div style="display:flex;gap:6px;flex-wrap:wrap">
      <button class="jen-pill" :class="{active:currentFilter==='all'}" @click="currentFilter='all'">All</button>
      <button class="jen-pill" :class="{active:currentFilter==='Draft'}" @click="currentFilter='Draft'">
        Draft <span class="jen-pc" style="background:#f1f3f5;color:#868e96">{{counts.Draft}}</span>
      </button>
      <button class="jen-pill" :class="{active:currentFilter==='Submitted'}" @click="currentFilter='Submitted'">
        Submitted <span class="jen-pc" style="background:#ebfbee;color:#2f9e44">{{counts.Submitted}}</span>
      </button>
      <button class="jen-pill" :class="{active:currentFilter==='Cancelled'}" @click="currentFilter='Cancelled'">
        Cancelled <span class="jen-pc" style="background:#ffe3e3;color:#c92a2a">{{counts.Cancelled}}</span>
      </button>
    </div>
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
      <div style="display:flex;align-items:center;gap:6px;font-size:12.5px;color:#868e96">
        <span>From</span>
        <input type="date" v-model="dateFrom" class="jen-date-input"/>
        <span>To</span>
        <input type="date" v-model="dateTo" class="jen-date-input"/>
      </div>
      <div class="b-search" style="border-radius:20px;padding:6px 12px">
        <span v-html="icon('search',13)"></span>
        <input v-model="searchQ" placeholder="Search JE, narration..." style="border:none;outline:none;font-size:13px;background:transparent;width:180px"/>
      </div>
      <button class="b-btn b-btn-ghost" @click="load"><span v-html="icon('refresh',13)"></span> Refresh</button>
      <button class="b-btn b-btn-primary" @click="openAdd" :disabled="!$canCreate('accounts')" :title="!$canCreate('accounts') ? 'Read-only access' : ''"><span v-html="icon('plus',13)"></span> New Entry</button>
    </div>
  </div>

  <!-- ── Mobile action bar (shown only on 375–425.98px) ── -->
  <div class="jen-mobile-bar">

    <!-- Filter pills: wrap naturally across rows -->
    <div class="jen-mob-pills">
      <button class="jen-mob-pill" :class="{active:currentFilter==='all'}" @click="currentFilter='all'">All</button>
      <button class="jen-mob-pill" :class="{active:currentFilter==='Draft'}" @click="currentFilter='Draft'">
        Draft <span class="jen-mob-pc jen-mob-pc--draft">{{counts.Draft}}</span>
      </button>
      <button class="jen-mob-pill" :class="{active:currentFilter==='Submitted'}" @click="currentFilter='Submitted'">
        Submitted <span class="jen-mob-pc jen-mob-pc--submitted">{{counts.Submitted}}</span>
      </button>
      <button class="jen-mob-pill" :class="{active:currentFilter==='Cancelled'}" @click="currentFilter='Cancelled'">
        Cancelled <span class="jen-mob-pc jen-mob-pc--cancelled">{{counts.Cancelled}}</span>
      </button>
    </div>

    <!-- Date range card -->
    <div class="jen-mob-date-card">
      <div class="jen-mob-date-lbl">DATE RANGE</div>
      <div class="jen-mob-date-row">
        <div class="jen-mob-date-field">
          <label class="jen-mob-date-field-lbl">From</label>
          <input type="date" v-model="dateFrom" class="jen-mob-date-input"/>
        </div>
        <div class="jen-mob-date-field">
          <label class="jen-mob-date-field-lbl">To</label>
          <input type="date" v-model="dateTo" class="jen-mob-date-input"/>
        </div>
      </div>
    </div>

    <!-- Action buttons -->
    <div class="jen-mob-btns">
      <button class="jen-mob-btn jen-mob-btn--ghost" @click="load">
        <span v-html="icon('refresh',15)"></span>
        Refresh
      </button>
      <button class="jen-mob-btn jen-mob-btn--primary" @click="openAdd" :disabled="!$canCreate('accounts')" :title="!$canCreate('accounts') ? 'Read-only access' : ''">
        <span v-html="icon('plus',15)"></span>
        New Entry
      </button>
    </div>

  </div>

  <div class="b-card" style="padding:0;overflow:hidden">
    <!-- ── Desktop table (hidden on 375–425px via media query) ── -->
    <table class="b-table jen-desktop-table">
      <thead>
        <tr>
          <th>Entry #</th><th>Date</th><th>Type</th><th>Narration</th>
          <th class="ta-r">Total Debit</th><th class="ta-r">Total Credit</th>
          <th>Status</th>
          <th style="text-align:center;width:100px">Actions</th>
        </tr>
      </thead>
      <tbody>
        <template v-if="loading">
          <tr v-for="n in 6" :key="n"><td colspan="9" style="padding:12px 14px"><div class="b-shimmer" style="height:12px"></div></td></tr>
        </template>
        <template v-else-if="filteredRows.length===0">
          <tr><td colspan="9" class="b-empty">
            <div style="font-size:32px;margin-bottom:8px">📄</div>
            <div style="font-weight:600;margin-bottom:4px">{{searchQ?'No entries match':'No journal entries yet'}}</div>
            <div style="font-size:13px;color:#868e96;margin-bottom:12px">{{searchQ?'Try a different search':'Record adjustments, depreciation, accruals and more'}}</div>
            <button v-if="!searchQ" class="b-btn b-btn-primary" :disabled="!$canCreate('accounts')" :title="!$canCreate('accounts') ? 'Read-only access' : ''" @click="openAdd"><span v-html="icon('plus',13)"></span> New Entry</button>
          </td></tr>
        </template>
        <template v-else>
          <tr v-for="e in filteredRows" :key="e.name" class="clickable" @click="openView(e.name)">
            <td @click.stop><DocLink doctype="Journal Entry" :name="e.name" /></td>
            <td style="font-size:12.5px;color:#868e96">{{fmtDateLocal(e.date)}}</td>
            <td><span class="b-badge" :class="JE_TYPE_COLOR[e.type]||'je-type-info'">{{e.type||'Journal Entry'}}</span></td>
            <td style="font-size:13px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{e.narration||'—'}}</td>
            <td class="ta-r" style="font-weight:600;color:#c92a2a">{{fmtINR(e.total_debit)}}</td>
            <td class="ta-r" style="font-weight:600;color:#2f9e44">{{fmtINR(e.total_credit)}}</td>
            <td><span class="b-badge" :class="JE_STATUS_COLOR[e.status]||'je-s-draft'">{{e.status}}</span></td>
            <td style="text-align:center">
              <div style="display:flex;gap:4px;justify-content:center">
                <button class="b-icon-btn" @click.stop="openView(e.name)" title="View"><span v-html="icon('eye',14)"></span></button>
                <button v-if="e.status==='Draft'" class="b-icon-btn" :disabled="!$canEdit('accounts')" :title="!$canEdit('accounts') ? 'Read-only access' : 'Edit'" @click.stop="openEdit(e.name)"><span v-html="icon('edit',14)"></span></button>
                <button v-if="e.status==='Draft'" class="b-icon-btn danger" :disabled="!$canDelete('accounts')" :title="!$canDelete('accounts') ? 'Not permitted' : 'Delete'" @click.stop="confirmAction(e.name,'delete')"><span v-html="icon('trash',14)"></span></button>
                <button v-if="e.status==='Submitted'" class="b-icon-btn danger" :disabled="!$canEdit('accounts')" :title="!$canEdit('accounts') ? 'Read-only access' : 'Cancel'" @click.stop="confirmAction(e.name,'cancel')"><span v-html="icon('cancel',14)"></span></button>
              </div>
            </td>
          </tr>
        </template>
      </tbody>
    </table>

    <!-- ── Mobile card list (shown only on 375–425.98px via media query) ── -->
    <div class="jen-mobile-cards">

      <!-- Loading skeleton -->
      <template v-if="loading">
        <div v-for="n in 5" :key="'sk-'+n" class="jen-mobile-card jen-mobile-card--skeleton">
          <div class="jen-mc-shimmer jen-mc-shimmer--title"></div>
          <div class="jen-mc-shimmer jen-mc-shimmer--line"></div>
          <div class="jen-mc-shimmer jen-mc-shimmer--line"></div>
        </div>
      </template>

      <!-- Empty state -->
      <div v-else-if="filteredRows.length===0" class="jen-mc-empty">
        <div class="jen-mc-empty-icon">📄</div>
        <div class="jen-mc-empty-title">{{searchQ?'No entries match':'No journal entries yet'}}</div>
        <div class="jen-mc-empty-sub">{{searchQ?'Try a different search':'Record adjustments, depreciation, accruals and more'}}</div>
        <button v-if="!searchQ" class="b-btn b-btn-primary" :disabled="!$canCreate('accounts')" :title="!$canCreate('accounts') ? 'Read-only access' : ''" style="margin-top:10px" @click="openAdd">
          <span v-html="icon('plus',13)"></span> New Entry
        </button>
      </div>

      <!-- Journal entry cards -->
      <template v-else>
        <div v-for="e in filteredRows" :key="'mc-'+e.name"
          class="jen-mobile-card"
          :class="'jen-mc-status--'+(e.status||'Draft').toLowerCase()"
          @click="openView(e.name)">

          <!-- Card header: entry # + status badge -->
          <div class="jen-mc-header">
            <div class="jen-mc-entry-no" @click.stop><DocLink doctype="Journal Entry" :name="e.name" :mono-style="false" /></div>
            <span class="b-badge jen-mc-status-badge" :class="JE_STATUS_COLOR[e.status]||'je-s-draft'">{{e.status}}</span>
          </div>

          <!-- Card meta: date + type badge -->
          <div class="jen-mc-meta">
            <span class="jen-mc-date">📅 {{fmtDateLocal(e.date)}}</span>
            <span class="b-badge jen-mc-type-badge" :class="JE_TYPE_COLOR[e.type]||'je-type-info'">
              {{e.type||'Journal Entry'}}
            </span>
          </div>

          <!-- Narration -->
          <div class="jen-mc-narration">{{e.narration||'—'}}</div>

          <!-- Debit / Credit amounts -->
          <div class="jen-mc-amounts">
            <div class="jen-mc-amount-box jen-mc-amount-box--dr">
              <div class="jen-mc-amount-lbl">Total Debit</div>
              <div class="jen-mc-amount-val jen-mc-amount-val--dr">{{fmtINR(e.total_debit)}}</div>
            </div>
            <div class="jen-mc-amount-divider"></div>
            <div class="jen-mc-amount-box jen-mc-amount-box--cr">
              <div class="jen-mc-amount-lbl">Total Credit</div>
              <div class="jen-mc-amount-val jen-mc-amount-val--cr">{{fmtINR(e.total_credit)}}</div>
            </div>
          </div>

          <!-- Card footer: action buttons -->
          <div class="jen-mc-footer" @click.stop>
            <button class="jen-mc-action-btn"
              @click.stop="openView(e.name)"
              title="View">
              <span v-html="icon('eye',13)"></span>
              <span class="jen-mc-action-lbl">View</span>
            </button>
            <button v-if="e.status==='Draft'"
              class="jen-mc-action-btn"
              :disabled="!$canEdit('accounts')"
              @click.stop="openEdit(e.name)"
              title="Edit">
              <span v-html="icon('edit',13)"></span>
              <span class="jen-mc-action-lbl">Edit</span>
            </button>
            <button v-if="e.status==='Draft'"
              class="jen-mc-action-btn jen-mc-action-btn--danger"
              :disabled="!$canDelete('accounts')"
              @click.stop="confirmAction(e.name,'delete')"
              title="Delete">
              <span v-html="icon('trash',13)"></span>
              <span class="jen-mc-action-lbl">Delete</span>
            </button>
            <button v-if="e.status==='Submitted'"
              class="jen-mc-action-btn jen-mc-action-btn--danger"
              :disabled="!$canEdit('accounts')"
              @click.stop="confirmAction(e.name,'cancel')"
              title="Cancel">
              <span v-html="icon('cancel',13)"></span>
              <span class="jen-mc-action-lbl">Cancel</span>
            </button>
          </div>
        </div>
      </template>
    </div>
  </div>
  <div style="text-align:right;font-size:12px;color:#868e96;padding:6px 4px">Showing {{filteredRows.length}} of {{allEntries.length}} entries</div>

  <Teleport to="body">
    <div v-if="drawerOpen" class="coa-drawer-bg" @click.self="drawerOpen=false">
      <div class="jen-drawer-panel">
        <div class="coa-dh">
          <div><div class="coa-dh-title">{{editingName?'Edit Journal Entry':'New Journal Entry'}}</div>
          <div class="coa-dh-sub">Debits must equal Credits</div></div>
          <button class="coa-dclose" @click="drawerOpen=false"><span v-html="icon('x',16)"></span></button>
        </div>
        <div class="coa-dbody">

          <span class="coa-sec-lbl" style="margin-top:0;border-top:none;padding-top:0">Entry Details</span>
          <div class="coa-fg jen-fg4">
            <div>
              <label class="coa-lbl">Date <span style="color:#c92a2a">*</span></label>
              <input v-model="form.date" type="date" class="coa-fi"/>
            </div>
            <div>
              <label class="coa-lbl">Entry Type</label>
              <select v-model="form.type" class="coa-fi">
                <option value="Journal Entry">Journal Entry</option>
                <option value="Depreciation">Depreciation</option>
                <option value="Accrual">Accrual Entry</option>
                <option value="Prepaid">Prepaid Expense</option>
                <option value="Provision">Provision Entry</option>
                <option value="Contra">Contra Entry</option>
                <option value="Rectification">Rectification Entry</option>
                <option value="Opening Entry">Opening Entry</option>
              </select>
            </div>
            <div>
              <label class="coa-lbl">Cheque / Ref No.</label>
              <input v-model="form.ref" class="coa-fi" placeholder="Optional reference"/>
            </div>
            <div>
              <label class="coa-lbl">Cheque Date</label>
              <input v-model="form.cheque_date" type="date" class="coa-fi"/>
            </div>
          </div>
          <div style="margin-bottom:16px">
            <label class="coa-lbl">Narration <span style="color:#c92a2a">*</span></label>
            <textarea v-model="form.narration" class="coa-fi" rows="2" style="resize:vertical" placeholder="Describe this journal entry — e.g. Depreciation for March 2026..."></textarea>
          </div>

          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
            <span style="font-size:11px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;color:#868e96">Lines</span>
            <div style="display:flex;gap:8px">
              <button @click="addLine('Debit')" class="jen-add-line-btn" style="border-color:rgba(201,42,42,.3);color:#c92a2a">
                <span v-html="icon('plus',12)"></span> Debit Row
              </button>
              <button @click="addLine('Credit')" class="jen-add-line-btn" style="border-color:rgba(47,158,68,.3);color:#2f9e44">
                <span v-html="icon('plus',12)"></span> Credit Row
              </button>
            </div>
          </div>

          <div class="jen-balance-bar" :class="lines.length&&(totalDr>0||totalCr>0)?(balanced?'jen-bal-ok':'jen-bal-err'):'jen-bal-zero'">
            <div style="display:flex;align-items:center;gap:8px">
              <span v-html="icon(balanced&&(totalDr>0)?'check':'info',14)"></span>
              <span>{{!lines.length||(totalDr===0&&totalCr===0)?'Add debit and credit lines':balanced?'Balanced — ready to post':'Difference: ₹'+Math.abs(totalDr-totalCr).toLocaleString('en-IN',{minimumFractionDigits:2})}}</span>
            </div>
            <div style="font-weight:700">
              <span v-if="totalDr>0||totalCr>0">Dr: ₹{{totalDr.toLocaleString('en-IN',{minimumFractionDigits:2})}} / Cr: ₹{{totalCr.toLocaleString('en-IN',{minimumFractionDigits:2})}}</span>
            </div>
          </div>

          <!-- Desktop lines table (hidden on mobile) -->
          <div class="jen-lines-desktop-wrapper" style="border:1px solid #e8ecf0;border-radius:8px;overflow:hidden;margin-bottom:16px;overflow-x:auto">
            <table class="jen-lines-tbl" style="min-width:680px">
              <thead>
                <tr>
                  <th style="width:28%">Account <span style="color:#c92a2a">*</span></th>
                  <th style="width:20%">Cost Center</th>
                  <th style="width:13%;text-align:right">Debit (Dr)</th>
                  <th style="width:13%;text-align:right">Credit (Cr)</th>
                  <th style="width:7%">Type</th>
                  <th style="width:4%"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="line in lines" :key="line.id">
                  <td>
                    <SearchableSelect :modelValue="line.account" @update:modelValue="v => onAccountChange(line, v)" :options="accounts" placeholder="— Select Account —" :compact="true" class="ss-cell-wrap"/>
                  </td>
                  <td>
                    <select v-model="line.cost_center" class="jen-ci">
                      <option value="">—</option>
                      <option v-for="cc in costCenters" :key="cc" :value="cc">{{cc}}</option>
                    </select>
                  </td>
                  <td><input v-model="line.dr" type="number" min="0" step="0.01" class="jen-ci" style="text-align:right" placeholder="0.00" @input="line.cr=''"/></td>
                  <td><input v-model="line.cr" type="number" min="0" step="0.01" class="jen-ci" style="text-align:right" placeholder="0.00" @input="line.dr=''"/></td>
                  <td style="font-size:11px;color:#868e96;padding:0 6px">{{flt(line.dr)>0?'Dr':flt(line.cr)>0?'Cr':'—'}}</td>
                  <td style="padding:4px 6px">
                    <button @click="removeLine(line.id)" class="b-icon-btn danger" style="padding:3px 5px"><span v-html="icon('x',12)"></span></button>
                  </td>
                </tr>
                <tr v-if="!lines.length">
                  <td colspan="6" style="text-align:center;padding:20px;color:#868e96;font-size:13px">No lines — click Debit Row or Credit Row to add</td>
                </tr>
                <tr class="jen-total-row">
                  <td colspan="2" style="padding:8px 10px;font-size:12px;font-weight:700;color:#868e96;text-transform:uppercase;letter-spacing:.04em">Totals</td>
                  <td style="text-align:right;padding:8px 10px;font-weight:700;color:#c92a2a">₹{{totalDr.toLocaleString('en-IN',{minimumFractionDigits:2})}}</td>
                  <td style="text-align:right;padding:8px 10px;font-weight:700;color:#2f9e44">₹{{totalCr.toLocaleString('en-IN',{minimumFractionDigits:2})}}</td>
                  <td colspan="2"></td>
                </tr>
              </tbody>
            </table>
          </div><!-- end .jen-lines-desktop-wrapper -->

          <!-- Mobile line cards (shown only at 375–425px) -->
          <div class="jen-lines-mobile-cards">

            <!-- Empty state -->
            <div v-if="!lines.length" class="jen-lmc-empty">
              No lines — click ‘+ Debit Row’ or ‘+ Credit Row’ above
            </div>

            <!-- One card per line -->
            <div v-for="line in lines" :key="'lmc-'+line.id"
              class="jen-lmc-card"
              :class="flt(line.dr)>0?'jen-lmc--dr':flt(line.cr)>0?'jen-lmc--cr':'jen-lmc--empty'">

              <!-- Card header: type chip + delete button -->
              <div class="jen-lmc-header">
                <span class="jen-lmc-type-chip"
                  :class="flt(line.dr)>0?'jen-lmc-chip--dr':flt(line.cr)>0?'jen-lmc-chip--cr':'jen-lmc-chip--none'">
                  {{flt(line.dr)>0?'Debit (Dr)':flt(line.cr)>0?'Credit (Cr)':'New Line'}}
                </span>
                <button @click="removeLine(line.id)" class="jen-lmc-del-btn" title="Remove line">
                  <span v-html="icon('x',12)"></span>
                </button>
              </div>

              <!-- Account select -->
              <div class="jen-lmc-field">
                <label class="jen-lmc-lbl">Account <span style="color:#c92a2a">*</span></label>
                <SearchableSelect :modelValue="line.account" @update:modelValue="v => onAccountChange(line, v)" :options="accounts" placeholder="— Select Account —" :compact="true" class="ss-cell-wrap jen-lmc-ss"/>
              </div>

              <!-- Cost center -->
              <div class="jen-lmc-field">
                <label class="jen-lmc-lbl">Cost Center</label>
                <select v-model="line.cost_center" class="jen-lmc-input">
                  <option value="">—</option>
                  <option v-for="cc in costCenters" :key="cc" :value="cc">{{cc}}</option>
                </select>
              </div>

              <!-- Dr / Cr inputs in a 2-col strip -->
              <div class="jen-lmc-amounts">
                <div class="jen-lmc-amount-cell jen-lmc-amount-cell--dr">
                  <label class="jen-lmc-amount-lbl">Debit (Dr)</label>
                  <input v-model="line.dr" type="number" min="0" step="0.01"
                    class="jen-lmc-amount-input jen-lmc-amount-input--dr"
                    placeholder="0.00" @input="line.cr=''"/>
                </div>
                <div class="jen-lmc-amount-cell jen-lmc-amount-cell--cr">
                  <label class="jen-lmc-amount-lbl">Credit (Cr)</label>
                  <input v-model="line.cr" type="number" min="0" step="0.01"
                    class="jen-lmc-amount-input jen-lmc-amount-input--cr"
                    placeholder="0.00" @input="line.dr=''"/>
                </div>
              </div>

            </div><!-- end jen-lmc-card -->

            <!-- Totals row -->
            <div v-if="lines.length" class="jen-lmc-totals">
              <span class="jen-lmc-totals-lbl">Totals</span>
              <div class="jen-lmc-totals-vals">
                <span class="jen-lmc-totals-dr">Dr: ₹{{totalDr.toLocaleString('en-IN',{minimumFractionDigits:2})}}</span>
                <span class="jen-lmc-totals-cr">Cr: ₹{{totalCr.toLocaleString('en-IN',{minimumFractionDigits:2})}}</span>
              </div>
            </div>

          </div><!-- end .jen-lines-mobile-cards -->

          <div class="coa-fg coa-fg2">
            <div>
              <label class="coa-lbl">Cost Center (global)</label>
              <select v-model="form.cost_center" class="coa-fi">
                <option value="">— All Centers —</option>
                <option v-for="cc in costCenters" :key="cc" :value="cc">{{cc}}</option>
              </select>
            </div>
            <div>
              <label class="coa-lbl">Status</label>
              <select v-model="form.status" class="coa-fi">
                <option value="Draft">Draft</option>
                <option value="Submitted">Submit (Post to Ledger)</option>
              </select>
            </div>
          </div>

        </div>
        <div class="coa-dfooter" style="justify-content:space-between">
          <div style="font-size:12px;color:#868e96">{{editingName?'Editing: '+editingName:'New entry'}}</div>
          <div style="display:flex;gap:10px">
            <button class="b-btn b-btn-ghost" @click="drawerOpen=false">Cancel</button>
            <button class="b-btn b-btn-ghost" @click="saveEntry('Draft')" :disabled="drawerSaving" style="border-color:#3b5bdb;color:#3b5bdb">Save Draft</button>
            <button class="b-btn b-btn-primary" @click="saveEntry('Submitted')" :disabled="drawerSaving||!balanced" style="min-width:140px">
              <span v-html="icon('check',13)"></span> Post to Ledger
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="viewOpen && viewEntry" class="coa-drawer-bg" @click.self="viewOpen=false">
      <div class="jen-drawer-panel">
        <div class="coa-dh" :style="'background:'+(viewEntry.status==='Submitted'?'linear-gradient(135deg,#1a4731,#2f9e44)':viewEntry.status==='Cancelled'?'linear-gradient(135deg,#6b1212,#c92a2a)':'linear-gradient(135deg,#1e3a5f,#2563eb)')">
          <div>
            <div class="coa-dh-title">{{viewEntry.name}}</div>
            <div class="coa-dh-sub">{{viewEntry.type}} · {{fmtDateLocal(viewEntry.date)}}</div>
          </div>
          <button class="coa-dclose" @click="viewOpen=false"><span v-html="icon('x',16)"></span></button>
        </div>
        <div class="coa-dbody">
          <!-- Meta row -->
          <div class="card-row-jen">
            <div class="jen-view-meta-card">
              <div class="jen-view-meta-lbl">Status</div>
              <span class="b-badge" :class="JE_STATUS_COLOR[viewEntry.status]||'je-s-draft'" style="margin-top:2px;">{{viewEntry.status}}</span>
            </div>
            <div class="jen-view-meta-card">
              <div class="jen-view-meta-lbl">Date</div>
              <div class="jen-view-meta-val">{{fmtDateLocal(viewEntry.date)}}<template v-if="viewEntry.posting_time"> {{viewEntry.posting_time}}</template></div>
            </div>
            <div class="jen-view-meta-card">
              <div class="jen-view-meta-lbl">Type</div>
              <span class="b-badge" :class="JE_TYPE_COLOR[viewEntry.type]||'je-type-info'" style="margin-top:2px">{{viewEntry.type||'Journal Entry'}}</span>
            </div>
          </div>

          <!-- Narration -->
          <div style="background:#f8f9fc;border:1px solid #e8ecf0;border-radius:8px;padding:12px 14px;margin-bottom:18px">
            <div class="jen-view-meta-lbl" style="margin-bottom:6px">Narration</div>
            <div style="font-size:13.5px;line-height:1.55;color:#1a1d23">{{viewEntry.narration||'—'}}</div>
          </div>

          <!-- Totals -->
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px">
            <div style="background:#fff4f4;border:1px solid #ffcdd2;border-radius:8px;padding:12px 16px;text-align:center">
              <div style="font-size:10.5px;color:#c92a2a;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px">Total Debit (Dr)</div>
              <div style="font-size:20px;font-weight:700;color:#c92a2a;">{{fmtINR(viewEntry.total_debit)}}</div>
            </div>
            <div style="background:#f0fff4;border:1px solid #b2f2bb;border-radius:8px;padding:12px 16px;text-align:center">
              <div style="font-size:10.5px;color:#2f9e44;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px">Total Credit (Cr)</div>
              <div style="font-size:20px;font-weight:700;color:#2f9e44;">{{fmtINR(viewEntry.total_credit)}}</div>
            </div>
          </div>

          <!-- Lines -->
          <div style="font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#868e96;margin-bottom:8px">Account Lines</div>
          <div v-if="viewLoading" style="border:1px solid #e2e8f0;border-radius:8px;padding:24px;text-align:center;color:#868e96;font-size:13px">
            <div class="b-shimmer" style="height:12px;margin-bottom:8px"></div>
            <div class="b-shimmer" style="height:12px;margin-bottom:8px"></div>
            <div class="b-shimmer" style="height:12px"></div>
          </div>
          <div v-else-if="(viewEntry.lines||[]).length">
            <!-- Desktop lines table -->
            <div class="jen-view-lines-desktop" style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden">
              <div style="display:grid;grid-template-columns:1fr 130px 130px;padding:9px 14px;background:#f8f9fc;border-bottom:1px solid #e2e8f0;font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:#6b7db3">
                <div>Account</div><div style="text-align:right">Debit (Dr)</div><div style="text-align:right">Credit (Cr)</div>
              </div>
              <div v-for="(l,i) in viewEntry.lines" :key="i"
                :style="'display:grid;grid-template-columns:1fr 130px 130px;padding:10px 14px;font-size:13px;border-bottom:1px solid #f1f3f5;background:'+(i%2===1?'#fafafa':'#fff')">
                <div style="font-weight:500;color:#1a1d23">
                  {{l.account}}
                </div>
                <div style="text-align:right;font-weight:600;color:#c92a2a">{{flt(l.dr)>0?fmtINR(l.dr):'—'}}</div>
                <div style="text-align:right;font-weight:600;color:#2f9e44">{{flt(l.cr)>0?fmtINR(l.cr):'—'}}</div>
              </div>
            </div>
            <!-- Mobile line cards -->
            <div class="jen-view-lines-mobile">
              <div v-for="(l,i) in viewEntry.lines" :key="'vlmc-'+i"
                class="jen-vlmc-card"
                :class="flt(l.dr)>0 ? 'jen-vlmc--dr' : flt(l.cr)>0 ? 'jen-vlmc--cr' : 'jen-vlmc--none'">
                <!-- type chip -->
                <div class="jen-vlmc-header">
                  <span class="jen-vlmc-chip"
                    :class="flt(l.dr)>0 ? 'jen-vlmc-chip--dr' : flt(l.cr)>0 ? 'jen-vlmc-chip--cr' : 'jen-vlmc-chip--none'">
                    {{ flt(l.dr)>0 ? 'DEBIT' : flt(l.cr)>0 ? 'CREDIT' : 'NONE' }}
                  </span>
                  <span class="jen-vlmc-idx">#{{i+1}}</span>
                </div>
                <!-- account name -->
                <div class="jen-vlmc-account">
                  {{l.account}}
                </div>
                <!-- dr / cr amounts -->
                <div class="jen-vlmc-amounts">
                  <div class="jen-vlmc-amt jen-vlmc-amt--dr">
                    <div class="jen-vlmc-amt-lbl">Debit (Dr)</div>
                    <div class="jen-vlmc-amt-val jen-vlmc-amt-val--dr">{{flt(l.dr)>0?fmtINR(l.dr):'—'}}</div>
                  </div>
                  <div class="jen-vlmc-divider"></div>
                  <div class="jen-vlmc-amt jen-vlmc-amt--cr">
                    <div class="jen-vlmc-amt-lbl">Credit (Cr)</div>
                    <div class="jen-vlmc-amt-val jen-vlmc-amt-val--cr">{{flt(l.cr)>0?fmtINR(l.cr):'—'}}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div v-else style="border:1px dashed #e2e8f0;border-radius:8px;padding:24px;text-align:center;color:#adb5bd;font-size:13px">
            <div style="font-size:24px;margin-bottom:6px">📋</div>
            No account lines found for this entry.
          </div>
        </div>
        <div class="coa-dfooter" style="justify-content:space-between">
          <div style="font-size:12px;color:#868e96"></div>
          <div style="display:flex;gap:10px">
            <button v-if="viewEntry.status==='Draft'" class="b-btn b-btn-ghost" :disabled="!$canEdit('accounts')" :title="!$canEdit('accounts') ? 'Read-only access' : ''" @click="viewOpen=false;openEdit(viewEntry.name)"><span v-html="icon('edit',13)"></span> Edit</button>
            <button v-if="viewEntry.status==='Submitted'" class="b-btn b-btn-ghost" style="border-color:rgba(201,42,42,.4);color:#c92a2a" :disabled="!$canEdit('accounts')" :title="!$canEdit('accounts') ? 'Read-only access' : ''" @click="viewOpen=false;confirmAction(viewEntry.name,'cancel')"><span v-html="icon('cancel',13)"></span> Cancel</button>
            <button class="b-btn b-btn-ghost" @click="viewOpen=false">Close</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showConf" class="coa-drawer-bg" @click.self="showConf=false" style="justify-content:center;align-items:center">
      <div style="background:#fff;border-radius:12px;padding:28px 32px;max-width:440px;width:100%;border:1px solid #e2e8f0;margin:10px">
        <div style="font-size:17px;font-weight:700;margin-bottom:8px">{{confType==='delete'?'Delete Entry?':'Cancel Entry?'}}</div>
        <div style="font-size:14px;color:#868e96;margin-bottom:24px;line-height:1.5">
          {{confType==='delete'?'This journal entry will be permanently removed.':'This will mark the entry as Cancelled. It cannot be edited after cancellation.'}}
          <br><strong>{{confTarget}}</strong>
        </div>
        <div style="display:flex;gap:10px;justify-content:flex-end">
          <button @click="showConf=false" class="b-btn b-btn-ghost">Keep It</button>
          <button @click="doAction" class="b-btn" style="background:#c92a2a;color:#fff;border-color:#c92a2a">{{confType==='delete'?'Yes, Delete':'Yes, Cancel'}}</button>
        </div>
      </div>
    </div>
  </Teleport>
</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { apiList, apiGet, apiSave, apiDelete, apiSubmit, apiPOST, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";
import { flt } from "../utils/format.js";
import SearchableSelect from "../components/SearchableSelect.vue";
import DocLink from "../components/DocLink.vue";
import { useRoute } from "vue-router";
import { useOpenFromQuery } from "../composables/useOpenFromQuery.js";
import { usePermissions } from "../composables/usePermissions.js";

const { toast } = useToast();
const { canCreate, canEdit, canDelete } = usePermissions();

const JE_TYPE_COLOR   = { "Journal Entry": "je-type-info", Depreciation: "je-type-muted", Accrual: "je-type-info", Prepaid: "je-type-info", Provision: "je-type-muted", Contra: "je-type-muted", Rectification: "je-type-muted", "Opening Entry": "je-type-info" };
const JE_STATUS_COLOR = { Draft: "je-s-draft", Submitted: "je-s-submitted", Cancelled: "je-s-cancelled" };

const allEntries  = ref([]);
const accounts    = ref([]);
const accountTypeMap = ref({}); // { accountName: account_type }

function onAccountChange(line, value) {
  line.account = value;
}
const costCenters = ref([]);
const loading     = ref(true);
const currentFilter = ref("all");
const searchQ     = ref("");
const dateFrom    = ref("");
const dateTo      = ref("");

const drawerOpen   = ref(false);
const editingName  = ref(null);
const drawerSaving = ref(false);
const form = reactive({ date: "", type: "Journal Entry", ref: "", cheque_date: "", narration: "", cost_center: "", status: "Draft" });
const lines = ref([]);

const viewOpen    = ref(false);
const viewEntry   = ref(null);
const viewLoading = ref(false);
const showConf   = ref(false);
const confTarget = ref(null);
const confType   = ref("");

const todayStr = () => new Date().toISOString().slice(0, 10);
const thisMonth = (d) => { const n = new Date(); return (d || "").startsWith(n.getFullYear() + "-" + String(n.getMonth() + 1).padStart(2, "0")); };

function fmtINR(v) {
  if (!v && v !== 0) return "—";
  const n = Number(v);
  if (n === 0) return "—";
  return "₹" + Math.abs(n).toLocaleString("en-IN", { minimumFractionDigits: 2 });
}
function fmtDateLocal(d) {
  if (!d) return "—";
  try { return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }); }
  catch { return d; }
}

const summary = computed(() => {
  const month = allEntries.value.filter((e) => thisMonth(e.date));
  const drafts = allEntries.value.filter((e) => e.status === "Draft");
  const totalDr = allEntries.value.filter((e) => e.status === "Submitted").reduce((s, e) => s + Number(e.total_debit || 0), 0);
  return { total: allEntries.value.length, month: month.length, totalDr, drafts: drafts.length };
});

const counts = computed(() => ({
  Draft:     allEntries.value.filter((e) => e.status === "Draft").length,
  Submitted: allEntries.value.filter((e) => e.status === "Submitted").length,
  Cancelled: allEntries.value.filter((e) => e.status === "Cancelled").length,
}));

const filteredRows = computed(() => {
  const q = searchQ.value.toLowerCase();
  let r = currentFilter.value === "all" ? allEntries.value : allEntries.value.filter((e) => e.status === currentFilter.value);
  if (dateFrom.value) r = r.filter((e) => e.date && e.date >= dateFrom.value);
  if (dateTo.value)   r = r.filter((e) => e.date && e.date <= dateTo.value);
  if (q) r = r.filter((e) => (e.name + e.narration + (e.type || "")).toLowerCase().includes(q));
  return r;
});

const totalDr   = computed(() => lines.value.reduce((s, l) => s + flt(l.dr), 0));
const totalCr   = computed(() => lines.value.reduce((s, l) => s + flt(l.cr), 0));
const balanced  = computed(() => Math.abs(totalDr.value - totalCr.value) < 0.01);

async function load() {
  loading.value = true;
  try {
    let frappeEntries = [];
    try {
      frappeEntries = await apiList("Journal Entry", {
        fields: ["name", "posting_date", "voucher_type", "remark", "total_debit", "total_credit", "docstatus"],
        order: "posting_date desc, creation desc", limit: 300,
      });
    } catch {}
    if (frappeEntries && frappeEntries.length) {
      allEntries.value = frappeEntries.map((e) => ({
        name: e.name, date: e.posting_date, type: e.voucher_type || "Journal Entry",
        narration: e.remark || "",
        total_debit: e.total_debit || 0, total_credit: e.total_credit || 0,
        status: e.docstatus === 1 ? "Submitted" : e.docstatus === 2 ? "Cancelled" : "Draft",
        lines: [], source: "frappe",
      }));
    } else {
      allEntries.value = [];
    }
    try {
      const accts = await apiList("Account", { fields: ["name", "account_name", "account_type"], filters: [["is_group", "=", 0], ["disabled", "=", 0]], limit: 100000 });
      // Receivable / Payable / Stock are control accounts whose balances must
      // stay tied to a Customer/Supplier/Item via Invoices, Bills, and Stock
      // Entries — posting to them directly from a Journal Entry would silently
      // break those sub-ledgers, so they're excluded here.
      const RESTRICTED_TYPES = ["Receivable", "Payable", "Stock"];
      const usable = accts.filter((a) => !RESTRICTED_TYPES.includes(a.account_type));
      accounts.value = usable.map((a) => a.name || a.account_name);
      accountTypeMap.value = Object.fromEntries(usable.map((a) => [a.name || a.account_name, a.account_type]));
    } catch { accounts.value = []; }
    try {
      const cc = await apiList("Cost Center", { fields: ["name"], filters: [["is_group", "=", 0]], limit: 100 });
      costCenters.value = cc.map((c) => c.name);
    } catch {}
  } finally { loading.value = false; }
}

function openAdd() {
  editingName.value = null;
  lines.value = [
    { id: Date.now(),     account: "", cost_center: "", dr: "", cr: "", type: "Debit" },
    { id: Date.now() + 1, account: "", cost_center: "", dr: "", cr: "", type: "Credit" },
  ];
  Object.assign(form, { date: todayStr(), type: "Journal Entry", ref: "", cheque_date: "", narration: "", cost_center: "", status: "Draft" });
  drawerOpen.value = true;
}

function openEdit(name) {
  const e = allEntries.value.find((x) => x.name === name);
  if (!e || e.status !== "Draft") return;
  editingName.value = name;
  Object.assign(form, { date: e.date || todayStr(), type: e.type || "Journal Entry", ref: e.cheque_no || e.ref || "", cheque_date: e.cheque_date || "", narration: e.narration || "", cost_center: e.cost_center || "", status: e.status || "Draft" });
  lines.value = (e.lines && e.lines.length)
    ? e.lines.map((l, i) => ({ ...l, id: Date.now() + i }))
    : [
        { id: Date.now(),     account: "", cost_center: "", dr: "", cr: "", type: "Debit" },
        { id: Date.now() + 1, account: "", cost_center: "", dr: "", cr: "", type: "Credit" },
      ];
  drawerOpen.value = true;
}

async function openView(name) {
  const stub = allEntries.value.find((x) => x.name === name) || { name, lines: [], status: "Draft" };
  viewEntry.value = stub;
  viewOpen.value = true;
  viewLoading.value = true;
  try {
    const doc = await apiGet("Journal Entry", name);
    if (doc) {
      viewEntry.value = {
        name: doc.name,
        date: doc.posting_date,
        posting_time: doc.posting_time || "",
        type: doc.voucher_type || "Journal Entry",
        narration: doc.remark || "",
        total_debit: doc.total_debit || 0,
        total_credit: doc.total_credit || 0,
        status: doc.docstatus === 1 ? "Submitted" : doc.docstatus === 2 ? "Cancelled" : "Draft",
        source: "frappe",
        lines: (doc.accounts || []).map((a) => ({
          account: a.account, dr: a.debit || 0, cr: a.credit || 0,
        })),
      };
    }
  } catch {}
  viewLoading.value = false;
}

function addLine(type) {
  lines.value.push({ id: Date.now(), account: "", cost_center: "", dr: type === "Debit" ? "0" : "", cr: type === "Credit" ? "0" : "", type });
}

function removeLine(id) {
  if (lines.value.length <= 1) return;
  lines.value = lines.value.filter((l) => l.id !== id);
}

async function saveEntry(status) {
  if (!(editingName.value ? canEdit("accounts") : canCreate("accounts"))) { toast("Read-only access", "error"); return; }
  if (!form.date)             { toast("Date is required", "error"); return; }
  if (!form.narration.trim()) { toast("Narration is required", "error"); return; }
  const hasLines = lines.value.some((l) => l.account && (flt(l.dr) > 0 || flt(l.cr) > 0));
  if (!hasLines)  { toast("Add at least one line with an account and amount", "error"); return; }
  if (!balanced.value) { toast("Total debits must equal total credits", "error"); return; }
  drawerSaving.value = true;
  try {
    const company = await resolveCompany();
    const payload = {
      posting_date: form.date,
      voucher_type: form.type,
      remark: form.narration,
      cost_center: form.cost_center || null,
      cheque_no: form.ref || null,
      cheque_date: form.cheque_date || null,
      accounts: lines.value.filter((l) => l.account).map((l) => ({
        doctype: "Journal Entry Account",
        account: l.account,
        cost_center: l.cost_center || form.cost_center || null,
        debit: flt(l.dr),
        credit: flt(l.cr),
      })),
    };
    const frappeDoc = { doctype: "Journal Entry", naming_series: "JV-.YYYY.-", company, ...payload };
    if (editingName.value) frappeDoc.name = editingName.value;
    const saved = await apiSave(frappeDoc);
    if (status === "Submitted" && saved?.name) {
      await apiSubmit("Journal Entry", saved.name);
    }
    await load();
    toast(editingName.value ? "Journal entry updated" : "Journal entry created", "success");
    drawerOpen.value = false;
  } catch (e) {
    toast(e.message || "Save failed", "error");
  } finally { drawerSaving.value = false; }
}

function confirmAction(name, type) {
  confTarget.value = name;
  confType.value = type;
  showConf.value = true;
}

async function doAction() {
  const name = confTarget.value;
  if (confType.value === "delete" && !canDelete("accounts")) { toast("Not permitted", "error"); showConf.value = false; return; }
  if (confType.value === "cancel" && !canEdit("accounts")) { toast("Read-only access", "error"); showConf.value = false; return; }
  try {
    if (confType.value === "delete") {
      await apiDelete("Journal Entry", name, { module: "accounts", action: "delete" });
      allEntries.value = allEntries.value.filter((e) => e.name !== name);
      toast("Entry deleted", "success");
    } else if (confType.value === "cancel") {
      await apiPOST("frappe.client.cancel", { doctype: "Journal Entry", name }, { module: "accounts", action: "cancel" });
      const idx = allEntries.value.findIndex((e) => e.name === name);
      if (idx >= 0) allEntries.value[idx] = { ...allEntries.value[idx], status: "Cancelled" };
      toast("Entry cancelled", "success");
    }
  } catch (e) { toast("Action failed: " + e.message, "error"); }
  showConf.value = false;
  confTarget.value = null;
}

const route = useRoute();
onMounted(async () => {
  await load();
  useOpenFromQuery({ route, openByName: (n) => openView(n) });
});
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════════════
   JEN MOBILE CARD VIEW  –  375 px … 425.98 px
   Default: mobile cards hidden, desktop table shown.
   Media query: flip visibility.
   ═══════════════════════════════════════════════════════════════════ */

/* ── Default: mobile card container hidden ── */
.jen-mobile-cards {
  display: none;
}

/* ── Default: desktop table visible ── */
.jen-desktop-table {
  display: table;
}

/* ── Default: mobile action bar hidden ── */
.jen-mobile-bar {
  display: none;
}

/* ── Default: desktop action bar visible ── */
.jen-desktop-bar {
  display: flex;
}

/* ── Default: view drawer mobile line cards hidden ── */
.jen-view-lines-mobile {
  display: none;
}

/* ── Default: edit drawer mobile line cards hidden (desktop shows table) ── */
.jen-lines-mobile-cards {
  display: none;
}
.card-row-jen {
  display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:18px
}
/* ── Activate card layout only on 375 px – 425.98 px ── */
@media (min-width: 375px) and (max-width: 425.98px) {
.card-row-jen{
  display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-bottom:18px
}
  /* Hide desktop action bar, show mobile action bar */
  .jen-desktop-bar {
    display: none !important;
  }

  .jen-mobile-bar {
    display: flex;
    flex-direction: column;
    gap: 14px;
    margin-bottom: 14px;
  }

  /* ── Filter pills ── */
  .jen-mob-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
  }

  .jen-mob-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 7px 16px;
    border-radius: 50px;
    border: 1.5px solid #e5e7eb;
    background: #ffffff;
    font-size: 13.5px;
    font-weight: 500;
    color: #374151;
    cursor: pointer;
    transition: all 0.15s ease;
    white-space: nowrap;
  }

  .jen-mob-pill.active {
    background: #3b5bdb;
    border-color: #3b5bdb;
    color: #ffffff;
    font-weight: 600;
  }

  .jen-mob-pill:not(.active):hover {
    border-color: #3b5bdb;
    color: #3b5bdb;
  }

  /* Count badge inside pill */
  .jen-mob-pc {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 18px;
    height: 18px;
    border-radius: 9px;
    font-size: 10.5px;
    font-weight: 700;
    padding: 0 5px;
  }

  .jen-mob-pc--draft     { background: #f1f3f5; color: #868e96; }
  .jen-mob-pc--submitted { background: #ebfbee; color: #2f9e44; }
  .jen-mob-pc--cancelled { background: #ffe3e3; color: #c92a2a; }

  /* Active pill → invert badge colours */
  .jen-mob-pill.active .jen-mob-pc--draft     { background: rgba(255,255,255,0.25); color: #fff; }
  .jen-mob-pill.active .jen-mob-pc--submitted { background: rgba(255,255,255,0.25); color: #fff; }
  .jen-mob-pill.active .jen-mob-pc--cancelled { background: rgba(255,255,255,0.25); color: #fff; }

  /* ── DATE RANGE card ── */
  .jen-mob-date-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 14px 14px 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }

  .jen-mob-date-lbl {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.7px;
    text-transform: uppercase;
    color: #6b7280;
    margin-bottom: 10px;
  }

  .jen-mob-date-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  .jen-mob-date-field {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .jen-mob-date-field-lbl {
    font-size: 11.5px;
    font-weight: 500;
    color: #6b7280;
  }

  .jen-mob-date-input {
    width: 100%;
    border: 1.5px solid #e5e7eb;
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 13px;
    color: #374151;
    background: #fff;
    box-sizing: border-box;
    outline: none;
    transition: border-color 0.15s;
  }

  .jen-mob-date-input:focus {
    border-color: #3b5bdb;
  }

  /* ── Action buttons ── */
  .jen-mob-btns {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }

  .jen-mob-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    padding: 12px 16px;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
    border: none;
  }

  .jen-mob-btn--ghost {
    background: #ffffff;
    border: 1.5px solid #e5e7eb;
    color: #374151;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  }

  .jen-mob-btn--ghost:hover {
    background: #f9fafb;
    border-color: #d1d5db;
  }

  .jen-mob-btn--primary {
    background: #3b5bdb;
    color: #ffffff;
    box-shadow: 0 2px 8px rgba(59,91,219,0.35);
  }

  .jen-mob-btn--primary:hover {
    background: #2f4dc4;
    box-shadow: 0 3px 10px rgba(59,91,219,0.45);
  }

  /* Hide desktop table */
  .jen-desktop-table {
    display: none !important;
  }

  /* Show card list */
  .jen-mobile-cards {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px 10px;
    background: #f8fafc;
  }

  /* ── Individual journal entry card ── */
  .jen-mobile-card {
    background: #ffffff;
    border-radius: 12px;
    border: 1px solid #e5e7eb;
    border-left: 4px solid #3b5bdb;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
    overflow: hidden;
    cursor: pointer;
    transition: box-shadow 0.18s ease, transform 0.12s ease;
  }

  .jen-mobile-card:active {
    transform: scale(0.985);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
  }

  /* Status-based left border colours */
  .jen-mc-status--draft     { border-left-color: #3b5bdb; }
  .jen-mc-status--submitted { border-left-color: #2f9e44; }
  .jen-mc-status--cancelled { border-left-color: #c92a2a; }

  /* ── Card header: Entry # + Status badge ── */
  .jen-mc-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 11px 12px 6px;
    border-bottom: 1px solid #f3f4f6;
    gap: 8px;
  }

  .jen-mc-entry-no {
    font-size: 13px;
    font-weight: 700;
    color: #2563eb;
    letter-spacing: 0.2px;
    word-break: break-all;
  }

  .jen-mc-status-badge {
    font-size: 10px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 20px;
    white-space: nowrap;
    flex-shrink: 0;
  }

  /* ── Card meta: date + type badge ── */
  .jen-mc-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 6px 12px;
    flex-wrap: wrap;
  }

  .jen-mc-date {
    font-size: 11.5px;
    color: #6b7280;
    white-space: nowrap;
  }

  .jen-mc-type-badge {
    font-size: 10px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 20px;
    white-space: nowrap;
    flex-shrink: 0;
  }

  /* ── Narration ── */
  .jen-mc-narration {
    font-size: 12.5px;
    color: #374151;
    padding: 0 12px 8px;
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* ── Debit / Credit amount boxes ── */
  .jen-mc-amounts {
    display: flex;
    align-items: stretch;
    border-top: 1px solid #f3f4f6;
    border-bottom: 1px solid #f3f4f6;
  }

  .jen-mc-amount-box {
    flex: 1;
    padding: 8px 12px;
    text-align: center;
  }

  .jen-mc-amount-box--dr { background: #fff9f9; }
  .jen-mc-amount-box--cr { background: #f0fff4; }

  .jen-mc-amount-divider {
    width: 1px;
    background: #e5e7eb;
    flex-shrink: 0;
  }

  .jen-mc-amount-lbl {
    font-size: 9.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    color: #9ca3af;
    margin-bottom: 3px;
  }

  .jen-mc-amount-val {
    font-size: 13.5px;
    font-weight: 700;
  }

  .jen-mc-amount-val--dr { color: #c92a2a; }
  .jen-mc-amount-val--cr { color: #2f9e44; }

  /* ── Card footer: action buttons ── */
  .jen-mc-footer {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 7px 10px 8px;
    background: #fafafa;
  }

  .jen-mc-action-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 5px 10px;
    border-radius: 8px;
    font-size: 11.5px;
    font-weight: 500;
    background: #f3f4f6;
    border: 1px solid #e5e7eb;
    color: #374151;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s;
    flex-shrink: 0;
  }

  .jen-mc-action-btn:hover {
    background: #e5e7eb;
    border-color: #d1d5db;
  }

  .jen-mc-action-btn--danger {
    color: #dc2626;
    background: #fff1f2;
    border-color: #fecaca;
  }

  .jen-mc-action-btn--danger:hover {
    background: #fee2e2;
    border-color: #fca5a5;
  }

  .jen-mc-action-lbl {
    font-size: 11px;
  }

  /* ── Skeleton shimmer cards ── */
  .jen-mobile-card--skeleton {
    pointer-events: none;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    border-left-color: #e5e7eb;
    background: #ffffff;
  }

  .jen-mc-shimmer {
    border-radius: 6px;
    background: linear-gradient(90deg, #f3f4f6 25%, #e9ecef 50%, #f3f4f6 75%);
    background-size: 200% 100%;
    animation: jen-shimmer 1.4s infinite;
  }

  .jen-mc-shimmer--title {
    height: 14px;
    width: 60%;
  }

  .jen-mc-shimmer--line {
    height: 11px;
    width: 40%;
  }

  @keyframes jen-shimmer {
    0%   { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }

  /* ── Empty state ── */
  .jen-mc-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 36px 16px;
    text-align: center;
    color: #9ca3af;
  }

  .jen-mc-empty-icon {
    font-size: 36px;
    margin-bottom: 10px;
  }

  .jen-mc-empty-title {
    font-size: 14px;
    font-weight: 600;
    color: #374151;
    margin-bottom: 4px;
  }

  .jen-mc-empty-sub {
    font-size: 12px;
    color: #9ca3af;
    line-height: 1.5;
  }

  /* ───────────────────────────────────────────────────────────
     EDIT DRAWER – Lines table → cards (375–425.98px)
     ─────────────────────────────────────────────────────────── */

  /* Edit/New entry drawer: full screen on mobile */
  .jen-drawer-panel {
    width: 100% !important;
    max-width: 100vw !important;
    border-radius: 0 !important;
  }

  /* Balance bar: wrap Dr/Cr summary below the status text */
  .jen-balance-bar {
    flex-direction: column !important;
    align-items: flex-start !important;
    gap: 6px !important;
    padding: 10px 12px !important;
  }

  /* Entry details grid: 2-col → 1-col */
  .jen-fg4 {
    grid-template-columns: 1fr 1fr !important;
  }

  /* Desktop lines table: hide on mobile */
  .jen-lines-desktop-wrapper {
    display: none !important;
  }

  /* Mobile line cards container: hidden by default, shown here */
  .jen-lines-mobile-cards {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 16px;
  }

  /* Empty state */
  .jen-lmc-empty {
    text-align: center;
    padding: 18px;
    font-size: 12.5px;
    color: #9ca3af;
    border: 1px dashed #e5e7eb;
    border-radius: 10px;
  }

  /* Individual line card */
  .jen-lmc-card {
    border: 1px solid #e5e7eb;
    border-left: 3px solid #e5e7eb;
    border-radius: 10px;
    background: #fff;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  }

  /* Left border by type */
  .jen-lmc--dr    { border-left-color: #c92a2a; }
  .jen-lmc--cr    { border-left-color: #2f9e44; }
  .jen-lmc--empty { border-left-color: #d1d5db; }

  /* Card header: type chip + delete btn */
  .jen-lmc-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 10px 6px;
    border-bottom: 1px solid #f3f4f6;
    background: #fafafa;
  }

  .jen-lmc-type-chip {
    font-size: 10.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    padding: 2px 10px;
    border-radius: 20px;
    border: 1px solid;
  }
  .jen-lmc-chip--dr   { color: #c92a2a; background: #fff5f5; border-color: rgba(201,42,42,.2); }
  .jen-lmc-chip--cr   { color: #2f9e44; background: #f0fff4; border-color: rgba(47,158,68,.2); }
  .jen-lmc-chip--none { color: #868e96; background: #f8f9fa; border-color: #e5e7eb; }

  .jen-lmc-del-btn {
    background: #fff1f2;
    border: 1px solid #fecaca;
    border-radius: 6px;
    color: #dc2626;
    cursor: pointer;
    padding: 4px 7px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.15s;
    flex-shrink: 0;
  }
  .jen-lmc-del-btn:hover { background: #fee2e2; }

  /* Card body fields */
  .jen-lmc-field {
    padding: 7px 10px 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .jen-lmc-lbl {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    color: #9ca3af;
  }

  .jen-lmc-input {
    width: 100%;
    box-sizing: border-box;
    border: 1.5px solid #e5e7eb;
    border-radius: 7px;
    padding: 7px 10px;
    font-size: 13px;
    color: #374151;
    background: #fff;
    outline: none;
    transition: border-color 0.15s;
    font-family: inherit;
  }
  .jen-lmc-input:focus { border-color: #3b5bdb; }

  /* SearchableSelect inside a card */
  .jen-lmc-ss { width: 100%; }

  /* Dr / Cr 2-col strip */
  .jen-lmc-amounts {
    display: grid;
    grid-template-columns: 1fr 1fr;
    border-top: 1px solid #f3f4f6;
    margin-top: 8px;
  }

  .jen-lmc-amount-cell {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 8px 10px 10px;
  }

  .jen-lmc-amount-cell--dr { border-right: 1px solid #f3f4f6; background: #fff9f9; }
  .jen-lmc-amount-cell--cr { background: #f0fff4; }

  .jen-lmc-amount-lbl {
    font-size: 9.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    color: #9ca3af;
  }

  .jen-lmc-amount-input {
    width: 100%;
    box-sizing: border-box;
    border: 1.5px solid #e5e7eb;
    border-radius: 7px;
    padding: 6px 8px;
    font-size: 13px;
    font-weight: 600;
    text-align: right;
    background: #fff;
    outline: none;
    transition: border-color 0.15s;
    font-family: inherit;
  }
  .jen-lmc-amount-input--dr:focus { border-color: #c92a2a; }
  .jen-lmc-amount-input--cr:focus { border-color: #2f9e44; }

  /* Totals row */
  .jen-lmc-totals {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #f8f9fc;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 9px 12px;
    margin-top: 2px;
  }
  .jen-lmc-totals-lbl {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    color: #6b7280;
  }
  .jen-lmc-totals-vals {
    display: flex;
    gap: 12px;
  }
  .jen-lmc-totals-dr {
    font-size: 13px;
    font-weight: 700;
    color: #c92a2a;
  }
  .jen-lmc-totals-cr {
    font-size: 13px;
    font-weight: 700;
    color: #2f9e44;
  }

  /* Edit drawer footer: stack buttons on mobile */
  .coa-dfooter {
    flex-direction: column !important;
    gap: 8px !important;
    padding: 12px 14px !important;
    align-items: stretch !important;
  }

  /* ── View drawer: account lines ── */

  /* Hide desktop grid table */
  .jen-view-lines-desktop { display: none !important; }

  /* Show mobile cards */
  .jen-view-lines-mobile {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  /* Individual line card */
  .jen-vlmc-card {
    border: 1px solid #e5e7eb;
    border-left: 3px solid #e5e7eb;
    border-radius: 10px;
    background: #fff;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  }
  .jen-vlmc--dr   { border-left-color: #c92a2a; }
  .jen-vlmc--cr   { border-left-color: #2f9e44; }
  .jen-vlmc--none { border-left-color: #d1d5db; }

  /* Card header: chip + index */
  .jen-vlmc-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 7px 10px 6px;
    background: #fafafa;
    border-bottom: 1px solid #f3f4f6;
  }

  .jen-vlmc-chip {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 2px 9px;
    border-radius: 20px;
    border: 1px solid;
  }
  .jen-vlmc-chip--dr   { color: #c92a2a; background: #fff5f5; border-color: rgba(201,42,42,.2); }
  .jen-vlmc-chip--cr   { color: #2f9e44; background: #f0fff4; border-color: rgba(47,158,68,.2); }
  .jen-vlmc-chip--none { color: #868e96; background: #f8f9fa; border-color: #e5e7eb; }

  .jen-vlmc-idx {
    font-size: 10.5px;
    font-weight: 600;
    color: #9ca3af;
  }

  /* Account name */
  .jen-vlmc-account {
    padding: 8px 10px 6px;
    font-size: 13px;
    font-weight: 600;
    color: #1a1d23;
    line-height: 1.4;
  }
  .jen-vlmc-party {
    font-size: 11px;
    font-weight: 400;
    color: #868e96;
    margin-left: 4px;
  }

  /* Dr / Cr amounts row */
  .jen-vlmc-amounts {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    border-top: 1px solid #f3f4f6;
  }
  .jen-vlmc-divider {
    width: 1px;
    background: #f3f4f6;
    margin: 0;
  }

  .jen-vlmc-amt {
    display: flex;
    flex-direction: column;
    gap: 3px;
    padding: 8px 10px 10px;
  }
  .jen-vlmc-amt--dr { background: #fff9f9; }
  .jen-vlmc-amt--cr { background: #f0fff4; }

  .jen-vlmc-amt-lbl {
    font-size: 9.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    color: #9ca3af;
  }
  .jen-vlmc-amt-val {
    font-size: 14px;
    font-weight: 700;
  }
  .jen-vlmc-amt-val--dr { color: #c92a2a; }
  .jen-vlmc-amt-val--cr { color: #2f9e44; }

} /* end @media 375px–425.98px */
</style>