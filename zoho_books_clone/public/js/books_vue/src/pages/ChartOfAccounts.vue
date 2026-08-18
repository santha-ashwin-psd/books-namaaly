<template>
<div class="coa-page" style="padding:10px;">

  <!-- <div class="coa-type-strip">
    <div v-for="s in typeStats" :key="s.type"
      class="coa-type-card"
      :class="{active: typeFilter===s.type}"
      :style="'border-left-color:'+s.meta.color+(typeFilter===s.type?';background:'+s.meta.bg:'')"
      @click="typeFilter = typeFilter===s.type?'':s.type">
      <div class="coa-type-lbl" :style="'color:'+s.meta.color">{{s.type}}</div>
      <div class="coa-type-val" :style="'color:'+s.meta.color">{{s.count}}</div>
      <div class="coa-type-sub">{{s.meta.dr?'Normally Dr':'Normally Cr'}} · {{s.total?fmtINR(s.total):'No opening'}}</div>
    </div>
  </div> -->

  <!-- Trial-balance / balancing card -->
  <!-- <div class="coa-balance-row">
    <div class="coa-balance-card" :class="trialBalance.balanced ? 'is-ok' : 'is-off'">
      <span class="coa-bal-title">Trial Balance</span>
      <span class="coa-bal-kv"><i>Dr</i><b>{{ fmtINR(trialBalance.dr) }}</b></span>
      <span class="coa-bal-sep">=</span>
      <span class="coa-bal-kv"><i>Cr</i><b>{{ fmtINR(trialBalance.cr) }}</b></span>
      <span v-if="balancesLoading" class="coa-bal-chip pending">Calculating…</span>
      <span v-else-if="trialBalance.balanced" class="coa-bal-chip ok"><span v-html="icon('check',11)"></span> Balanced</span>
      <span v-else class="coa-bal-chip off"><span v-html="icon('alert',11)"></span> Off by {{ fmtINR(Math.abs(trialBalance.diff)) }}</span>
    </div>
  </div> -->

  <div class="b-action-bar">
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
      <div class="b-search" style="border-radius:20px;padding:2px 12px">
        <span v-html="icon('search',13)"></span>
        <input v-model="searchQ" placeholder="Search account name or code..." style="border:none;outline:none;font-size:13px;background:transparent;width:220px"/>
      </div>
      <button class="b-btn b-btn-ghost" @click="load"><span v-html="icon('refresh',13)"></span> Refresh</button>
      <div class="coa-view-toggle">
        <button type="button" class="coa-view-btn" :class="{active: viewMode==='list'}" @click="viewMode='list'">List</button>
        <button type="button" class="coa-view-btn" :class="{active: viewMode==='tree'}" @click="viewMode='tree'">Tree</button>
      </div>
      <template v-if="viewMode==='tree'">
        <button class="b-btn b-btn-ghost" @click="expandAllGroups"><span v-html="icon('chevD',13)"></span> Expand All</button>
        <button class="b-btn b-btn-ghost" @click="collapseAllGroups"><span v-html="icon('chevR',13)"></span> Collapse All</button>
      </template>
    </div>
    <button class="b-btn b-btn-primary" @click="openAdd()" :disabled="!$canCreate('accounts')" :title="!$canCreate('accounts') ? 'Read-only access' : ''"><span v-html="icon('plus',13)"></span> Add Account</button>
  </div>

  <div class="b-card coa-split-card" style="padding:0;overflow:hidden">
    <!-- ── Desktop split view: account list (left) + detail panel (right) ── -->
    <div class="coa-split coa-desktop-table">
      <!-- Left: account list -->
      <div class="coa-split-list">
        <div class="coa-split-list-head">
          <span>Account Name</span><span>Type</span>
        </div>
        <div class="coa-split-list-body">
          <template v-if="loading">
            <div v-for="n in 8" :key="n" class="coa-split-row" style="padding:12px 14px">
              <div class="b-shimmer" style="height:12px"></div>
            </div>
          </template>
          <template v-else-if="flatTree.length===0">
            <div class="b-empty">No accounts found</div>
          </template>
          <template v-else>
            <div v-for="row in flatTree" :key="row.name"
              class="coa-split-row"
              :class="{active: selectedAccount && selectedAccount.name===row.name, 'coa-group-row': row.is_group}"
              :style="viewMode==='tree' ? ('padding-left:'+(14+row.depth*18)+'px') : ''"
              @click="selectAccount(row)">
              <button v-if="viewMode==='tree' && row.is_group"
                type="button" class="coa-toggle"
                :class="{open: isExpanded(row.name)}"
                @click.stop="toggleGroup(row.name)">
                <span v-html="icon('chevR',10)"></span>
              </button>
              <span v-else style="width:6px;flex-shrink:0;display:inline-block"></span>
              <div class="coa-split-row-main">
                <div class="coa-split-row-name" :class="{'fw-700':row.is_group}">{{row.account_name||row.name}}</div>
                <div class="coa-split-row-type">{{row.account_type || row.root_type}}<span v-if="row.is_group"> · Group</span></div>
              </div>
              <div v-if="!row.is_group" class="coa-split-row-bal" :class="(balances[row.name]||0) < 0 ? 'coa-cr' : 'coa-dr'">{{ fmtBal(balances[row.name]) }}</div>
            </div>
          </template>
        </div>
      </div>

      <!-- Right: detail panel -->
      <div class="coa-split-detail">
        <template v-if="!selectedAccount">
          <div class="coa-split-empty">
            <span v-html="icon('accts',34)"></span>
            <div>Select an account to view details</div>
          </div>
        </template>
        <template v-else>
          <div class="coa-detail-head">
            <div>
              <div class="coa-detail-type">{{selectedAccount.account_type || selectedAccount.root_type}}</div>
              <div class="coa-detail-name">{{selectedAccount.account_name || selectedAccount.name}}</div>
            </div>
            <div style="display:flex;gap:8px">
            <div class="coa-detail-balance coa-detail-balance-opening" v-if="!selectedAccount.is_group">
            <div class="coa-detail-balance-lbl">Opening Balance</div>
            <div class="coa-detail-balance-val" :class="getBalType(selectedAccount.opening, selectedAccount.bal_type) === 'Credit' ? 'coa-cr' : 'coa-dr'">
              {{ fmtBal(selectedAccount.opening) }}
              <span class="coa-detail-balance-tag">{{ getBalType(selectedAccount.opening, selectedAccount.bal_type) === 'Credit' ? '(Cr)' : '(Dr)' }}</span>
            </div>
          </div>
            <div class="coa-detail-balance" v-if="!selectedAccount.is_group">
            <div class="coa-detail-balance-lbl">Closing Balance</div>
            <div class="coa-detail-balance-val" :class="(balances[selectedAccount.name]||0) < 0 ? 'coa-cr' : 'coa-dr'">
              {{ fmtBal(balances[selectedAccount.name]) }}
              <span class="coa-detail-balance-tag">{{ (balances[selectedAccount.name]||0) < 0 ? '(Cr)' : '(Dr)' }}</span>
            </div>
            <div v-if="selectedAccount.notes" class="coa-detail-desc"><i>Description</i> : {{selectedAccount.notes}}</div>
          </div>
          <div class="coa-detail-balance" v-else>
            <div class="coa-detail-balance-lbl">Group Account</div>
            <div style="font-size:12.5px;color:#868e96;margin-top:4px">Group accounts don't carry ledger entries — they contain child accounts.</div>
          </div>
            <div style="align-content: center;">
              <button v-if="!selectedAccount.is_group && selectedAccount.source==='frappe'" class="b-icon-btn" @click="openLedger(selectedAccount)" title="View Full Ledger" style="color:#2563eb"><span v-html="icon('book',15)"></span></button>
              <button class="b-icon-btn" style="margin-left:2px" :disabled="!$canEdit('accounts')" :title="!$canEdit('accounts') ? 'Read-only access' : 'Edit'" @click="openEdit(selectedAccount.name)"><span v-html="icon('edit',15)"></span></button>
              <button v-if="canDeleteAccount(selectedAccount)" class="b-icon-btn danger"
  :disabled="!$canDelete('accounts')"
  :title="!$canDelete('accounts') ? 'Not permitted' : 'Delete'"
  @click="confirmDelete(selectedAccount.name)">
  <span v-html="icon('trash',15)"></span>
</button>
            </div>
            </div>
          </div>

          <div v-if="$canEdit('accounts')" class="coa-detail-edit"><span v-html="icon('edit',12)"></span> <a @click="openEdit(selectedAccount.name)">Edit</a></div>

          

          <template v-if="!selectedAccount.is_group && selectedAccount.source==='frappe'">
            <div class="coa-detail-txn-head" style="flex-wrap:wrap;gap:8px">
              <span>Recent Transactions</span>
              <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">
                <input type="date" v-model="coaFilterFrom" :max="coaFilterTo || undefined" />
                <span style="font-size:12px;color:#9ca3af">to</span>
                <input type="date" v-model="coaFilterTo" :min="coaFilterFrom || undefined" />
                <button class="b-btn b-btn-ghost" style="padding:5px 10px;font-size:12px" @click="applyCoaDateFilter(selectedAccount)">Apply</button>
                <button v-if="coaFilterFrom || coaFilterTo" class="b-btn b-btn-ghost" style="padding:5px 10px;font-size:12px" @click="clearCoaDateFilter(selectedAccount)">Clear</button>
              </div>
            </div>
            <div class="coa-detail-txns">
              <div v-if="inlineLedger[selectedAccount.name] && inlineLedger[selectedAccount.name].loading" style="padding:22px;text-align:center;color:#9ca3af;font-size:12.5px">Loading transactions…</div>
              <div v-else-if="!inlineLedger[selectedAccount.name] || !inlineLedger[selectedAccount.name].rows.length" style="padding:22px;text-align:center;color:#9ca3af;font-size:12.5px">No transactions yet.</div>
              <template v-else>
                <div class="coa-txn-tbl-head">
                  <span>Date</span><span>Transaction Details</span><span>Type</span><span class="ta-r">Debit</span><span class="ta-r">Credit</span><span class="ta-r">Balance</span>
                </div>
                <div v-for="r in inlineLedger[selectedAccount.name].rows.slice(0, inlineLedger[selectedAccount.name].visible)"
                  :key="(r.voucher_no||'')+'-'+r.posting_date+'-'+r.balance" class="coa-txn-row">
                  <span class="coa-txn-date">{{ r.posting_date }}</span>
                  <span class="coa-txn-detail" v-if="r.party_name || r.party" :title="r.party_name || r.party">{{ r.party_name || r.party }}</span>
                  <span class="coa-txn-detail" v-else :title="r.voucher_no"><DocLink :doctype="r.voucher_type" :name="r.voucher_no" :mono-style="false" /></span>
                  <span class="coa-txn-type">{{ r.voucher_type }}</span>
                  <span class="ta-r coa-txn-dr">{{ getRowDr(r) > 0 ? "₹"+getRowDr(r).toLocaleString("en-IN",{minimumFractionDigits:2}) : '' }}</span>
                  <span class="ta-r coa-txn-cr">{{ getRowCr(r) > 0 ? "₹"+getRowCr(r).toLocaleString("en-IN",{minimumFractionDigits:2}) : '' }}</span>
                  <span class="ta-r coa-txn-bal" :style="{color: r.balance > 0 ? '#16a34a' : r.balance < 0 ? '#dc2626' : '#374151'}">₹{{ Number(r.balance).toLocaleString("en-IN",{minimumFractionDigits:2}) }}</span>
                </div>
                <div class="coa-detail-loadmore">
                  <span>Showing {{ Math.min(inlineLedger[selectedAccount.name].visible, inlineLedger[selectedAccount.name].rows.length) }} of {{ inlineLedger[selectedAccount.name].rows.length }}</span>
                  <button v-if="inlineLedger[selectedAccount.name].visible < inlineLedger[selectedAccount.name].rows.length" class="b-btn b-btn-ghost" style="padding:5px 14px;font-size:12px" @click="loadMoreInline(selectedAccount.name)">Load More</button>
                </div>
              </template>
            </div>
          </template>
        </template>
      </div>
    </div>

    <!-- ── Mobile card list (shown only on 375–425px screens via media query) ── -->
    <div class="coa-mobile-cards">
      <!-- Loading skeleton -->
      <template v-if="loading">
        <div v-for="n in 5" :key="'sk-'+n" class="coa-mobile-card coa-mobile-card--skeleton">
          <div class="coa-mc-shimmer coa-mc-shimmer--title"></div>
          <div class="coa-mc-shimmer coa-mc-shimmer--line"></div>
          <div class="coa-mc-shimmer coa-mc-shimmer--line"></div>
        </div>
      </template>

      <!-- Empty state -->
      <div v-else-if="flatTree.length===0" class="coa-mc-empty">
        <div class="coa-mc-empty-icon">📂</div>
        <div class="coa-mc-empty-text">No accounts found</div>
      </div>

      <!-- Account cards -->
      <template v-else>
        <div v-for="row in flatTree" :key="'mc-'+row.name"
          class="coa-mobile-card"
          :class="[row.is_group ? 'coa-mobile-card--group' : 'coa-mobile-card--leaf']"
          :style="'--mc-accent:'+(TYPE_META_COA[row.root_type]||TYPE_META_COA.Asset).color+';--mc-bg:'+(TYPE_META_COA[row.root_type]||TYPE_META_COA.Asset).bg+(viewMode==='tree' ? (';margin-left:'+(row.depth*12)+'px') : '')"
          @click="handleRowClick(row)">

          <!-- Card header: name + badges -->
          <div class="coa-mc-header" style="padding-left:8px">
            <div class="coa-mc-name-row">
              <button v-if="!row.is_group && row.source==='frappe'"
                class="coa-toggle coa-mc-toggle"
                :class="{open: !!inlineLedger[row.name]}"
                @click.stop="toggleInlineLedger(row)">
                <span v-html="icon('chevR',10)"></span>
              </button>
              <button v-else-if="row.is_group && viewMode==='tree'"
                class="coa-toggle coa-mc-toggle"
                :class="{open: isExpanded(row.name)}"
                @click.stop="toggleGroup(row.name)">
                <span v-html="icon('chevR',10)"></span>
              </button>
              <span class="coa-dot coa-mc-dot"
                :style="'background:'+(TYPE_META_COA[row.root_type]||TYPE_META_COA.Asset).color"></span>
              <span class="coa-mc-acct-name" :class="{'coa-mc-acct-name--bold': row.is_group}">
                {{row.account_name || row.name}}
              </span>
            </div>
            <div class="coa-mc-badges">
              <span class="b-badge coa-mc-type-badge"
                :style="'background:'+(TYPE_META_COA[row.root_type]||TYPE_META_COA.Asset).bg+';color:'+(TYPE_META_COA[row.root_type]||TYPE_META_COA.Asset).color">
                {{row.root_type}}
              </span>
              <span v-if="row.is_group" class="coa-group-chip coa-mc-group-chip"
                :style="'background:'+(TYPE_META_COA[row.root_type]||TYPE_META_COA.Asset).bg+';color:'+(TYPE_META_COA[row.root_type]||TYPE_META_COA.Asset).color">
                Group
              </span>
              <span v-if="row.account_type" class="coa-acct-type coa-mc-acct-type-chip">
                {{row.account_type}}
              </span>
            </div>
          </div>

          <!-- Card body: data rows -->
          <div class="coa-mc-body">
            <div class="coa-mc-row">
              <span class="coa-mc-label">Account No.</span>
              <span class="coa-mc-value coa-mc-value--code">{{row.code || '—'}}</span>
            </div>
            <div class="coa-mc-row">
              <span class="coa-mc-label">Opening</span>
              <div class="coa-split-row-bal"
                :class="row.opening ? (getBalType(row.opening, row.bal_type) === 'Credit' ? 'coa-cr' : 'coa-dr') : 'c-muted'">
                {{ fmtBal(row.opening) }}
              </div>
            </div>
            <div class="coa-mc-row">
              <span class="coa-mc-label">Current Balance</span>
              <span class="coa-mc-value"
                :class="getBalType(balances[row.name], 'Debit') === 'Credit' ? 'coa-cr' : 'coa-dr'">
                <template v-if="row.is_group">—</template>
                <template v-else-if="balancesLoading && balances[row.name] === undefined">
                  <span style="color:#9ca3af;font-size:10px">…</span>
                </template>
                <template v-else>{{ fmtBal(balances[row.name]) }}</template>
              </span>
            </div>
          </div>

          <!-- Inline ledger (mobile) -->
          <div v-if="inlineLedger[row.name]" class="coa-inline-ledger" @click.stop>
            <div v-if="inlineLedger[row.name].loading" style="padding:14px;text-align:center;color:#9ca3af;font-size:12px">Loading ledger entries…</div>
            <div v-else-if="!inlineLedger[row.name].rows.length" style="padding:14px;text-align:center;color:#9ca3af;font-size:12px">No ledger entries for this account.</div>
            <template v-else>
              <div v-for="r in inlineLedger[row.name].rows.slice(0, inlineLedger[row.name].visible)" :key="(r.voucher_no||'')+'-'+r.posting_date+'-'+r.balance"
                style="padding:8px 12px;border-top:1px solid #f3f4f6;font-size:12px">
                <div style="display:flex;justify-content:space-between"><b style="color:#2563eb" @click.stop><DocLink :doctype="r.voucher_type" :name="r.voucher_no" :mono-style="false" /></b><span style="color:#6b7280">{{r.posting_date}}</span></div>
                <div style="display:flex;justify-content:space-between;margin-top:2px;color:#6b7280">
                  <span>{{r.voucher_type}} · {{r.party_name||r.party||'—'}}</span>
                  <span :style="{color: r.balance > 0 ? '#16a34a' : r.balance < 0 ? '#dc2626' : '#374151', fontWeight:700}">₹{{ Number(r.balance).toLocaleString("en-IN",{minimumFractionDigits:2}) }}</span>
                </div>
              </div>
              <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:#f8fafc;border-top:1px solid #e5e7eb">
                <span style="font-size:11px;color:#868e96">{{ Math.min(inlineLedger[row.name].visible, inlineLedger[row.name].rows.length) }} of {{ inlineLedger[row.name].rows.length }}</span>
                <button v-if="inlineLedger[row.name].visible < inlineLedger[row.name].rows.length" class="b-btn b-btn-ghost" style="padding:4px 10px;font-size:11.5px" @click.stop="loadMoreInline(row.name)">Load More</button>
              </div>
            </template>
          </div>

          <!-- Card footer: actions -->
          <div class="coa-mc-footer" @click.stop>
            <button v-if="!row.is_group && row.source==='frappe'"
              class="b-icon-btn coa-mc-action-btn"
              @click.stop="openLedger(row)"
              title="View Ledger"
              style="color:#2563eb">
              <span v-html="icon('book',13)"></span>
              <span class="coa-mc-action-lbl">Ledger</span>
            </button>
            <button class="b-icon-btn coa-mc-action-btn"
              :disabled="!$canEdit('accounts')"
              @click.stop="openEdit(row.name)"
              title="Edit">
              <span v-html="icon('edit',13)"></span>
              <span class="coa-mc-action-lbl">Edit</span>
            </button>
            <button v-if="row.source!=='frappe'"
              class="b-icon-btn danger coa-mc-action-btn"
              :disabled="!$canDelete('accounts')"
              @click.stop="confirmDelete(row.name)"
              title="Delete">
              <span v-html="icon('trash',13)"></span>
              <span class="coa-mc-action-lbl">Delete</span>
            </button>
          </div>
        </div>
      </template>
    </div>
  </div>
  <div style="text-align:right;font-size:12px;color:#868e96;padding:6px 4px">{{flatTree.length}} account(s)</div>

  <Teleport to="body">
    <div v-if="drawerOpen" class="coa-drawer-bg" @click.self="drawerOpen=false">
      <div class="coa-drawer-panel">
        <div class="coa-dh">
          <div><div class="coa-dh-title">{{editingName?'Edit Account':'Add Account'}}</div>
          <div class="coa-dh-sub">{{editingName?'Update account details':'Create a new account in the chart'}}</div></div>
          <button class="coa-dclose" @click="drawerOpen=false"><span v-html="icon('x',16)"></span></button>
        </div>
        <div class="coa-dbody">
          <div class="coa-info-box">
            <span v-html="icon('info',14)"></span>
            <span>Group accounts can have child accounts. Ledger accounts record actual transactions.</span>
          </div>

          <span class="coa-sec-lbl">Account Details</span>
          <div class="coa-fg coa-fg2">
            <div style="grid-column:1/3">
              <label class="coa-lbl">Account Name <span style="color:#c92a2a">*</span></label>
              <input v-model="form.name" class="coa-fi" placeholder="e.g. Cash in Hand, Sales Revenue"/>
            </div>
            <div>
              <label class="coa-lbl">Account Number</label>
              <input v-model="form.code" class="coa-fi" placeholder="e.g. 1001, 4001"/>
            </div>
            <div>
              <label class="coa-lbl">Root Type <span style="color:#c92a2a">*</span></label>
              <select v-model="form.root_type" class="coa-fi" @change="form.account_type=''">
                <option value="">— Select —</option>
                <option value="Asset">Asset</option>
                <option value="Liability">Liability</option>
                <option value="Equity">Equity</option>
                <option value="Income">Income</option>
                <option value="Expense">Expense</option>
              </select>
            </div>
            <div>
              <label class="coa-lbl">Account Type</label>
              <select v-model="form.account_type" class="coa-fi">
                <option value="">— General —</option>
                <option v-for="t in accountTypeOptions" :key="t" :value="t">{{t}}</option>
              </select>
            </div>
            <div>
              <label class="coa-lbl">Parent Account</label>
              <SearchableSelect v-model="form.parent" :options="parentOptions" value-key="name" label-key="account_name" placeholder="— Root level —"/>
            </div>
          </div>

          <div class="coa-fg coa-fg2" style="margin-top:0">
            <div>
              <label class="coa-lbl">Is Group Account?</label>
              <div style="display:flex;align-items:center;gap:14px;margin-top:8px">
                <label style="display:flex;align-items:center;gap:6px;cursor:pointer;font-size:13px">
                  <input type="radio" v-model="form.is_group" :value="1" style="accent-color:#3b5bdb"/> Yes
                </label>
                <label style="display:flex;align-items:center;gap:6px;cursor:pointer;font-size:13px">
                  <input type="radio" v-model="form.is_group" :value="0" style="accent-color:#3b5bdb"/> No
                </label>
              </div>
            </div>
            <div>
              <label class="coa-lbl">Balance Sheet Item?</label>
              <select v-model="form.bs_item" class="coa-fi">
                <option :value="1">Yes (Balance Sheet)</option>
                <option :value="0">No (P&amp;L)</option>
              </select>
            </div>
          </div>

          <span class="coa-sec-lbl">Opening Balance</span>
          <div class="coa-fg coa-fg2">
            <div>
              <label class="coa-lbl">Opening Balance (₹)</label>
              <input v-model="form.opening" type="number" min="0" step="0.01" class="coa-fi" placeholder="0.00" />
            </div>
            <div>
              <label class="coa-lbl">Balance Type</label>
              <select v-model="form.bal_type" class="coa-fi">
                <option value="Debit">Debit (Dr)</option>
                <option value="Credit">Credit (Cr)</option>
              </select>
            </div>
          </div>

          <div>
            <label class="coa-lbl">Description / Notes</label>
            <textarea v-model="form.notes" class="coa-fi" rows="2" style="resize:vertical" placeholder="Optional description..."></textarea>
          </div>
        </div>
        <div class="coa-dfooter">
          <button class="b-btn b-btn-ghost" @click="drawerOpen=false">Cancel</button>
          <button class="b-btn b-btn-primary" @click="saveAccount" :disabled="drawerSaving" style="min-width:130px">
            {{drawerSaving?'Saving…':'Save Account'}}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showDel" class="coa-drawer-bg" @click.self="showDel=false" style="justify-content:center;align-items:center">
      <div style="background:#fff;border-radius:12px;padding:28px 32px;max-width:420px;width:100%;border:1px solid #e2e8f0">
        <div style="font-size:17px;font-weight:700;margin-bottom:8px">Delete Account?</div>
        <div style="font-size:14px;color:#868e96;margin-bottom:24px;line-height:1.5">
          <strong>{{deleteTarget}}</strong> and all its child accounts will be permanently removed from local data.
        </div>
        <div style="display:flex;gap:10px;justify-content:flex-end">
          <button @click="showDel=false" class="b-btn b-btn-ghost">Keep It</button>
          <button @click="doDelete" class="b-btn" style="background:#c92a2a;color:#fff;border-color:#c92a2a">Yes, Delete</button>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- ── Ledger drill-down drawer ── -->
  <Teleport to="body">
    <div v-if="ledgerDrawer.open" class="coa-drawer-bg" @click.self="closeLedger">
      <div class="coa-drawer-panel ldg-panel" style="width:min(960px,98vw)">
        <div class="coa-dh" style="background:linear-gradient(135deg,#1e3a5f,#1a6ef7);color:#fff;padding:18px 24px">
          <div>
            <div class="coa-dh-title" style="color:#fff">📒 Ledger — {{ ledgerDrawer.account_label }}</div>
            <div class="coa-dh-sub" style="color:rgba(255,255,255,.8)">General Ledger entries with running balance</div>
          </div>
          <button class="coa-dclose" style="color:#fff;background:rgba(255,255,255,.18)" @click="closeLedger"><span v-html="icon('x',16)"></span></button>
        </div>
        <div class="ldg-toolbar" style="padding:12px 24px;background:#f8fafc;display:flex;align-items:center;gap:10px;border-bottom:1px solid #e5e7eb;flex-wrap:wrap">
          <span style="font-size:11.5px;font-weight:600;color:#6b7280">FROM</span>
          <input v-model="ledgerDrawer.from_date" type="date" class="coa-fi" style="width:150px"/>
          <span style="font-size:11.5px;font-weight:600;color:#6b7280">TO</span>
          <input v-model="ledgerDrawer.to_date" type="date" class="coa-fi" style="width:150px"/>
          <button class="b-btn b-btn-primary" style="padding:6px 14px" @click="fetchLedger">Refresh</button>
          <button class="b-btn" style="margin-left:auto;padding:6px 14px;border:1px solid #e5e7eb;background:#fff" @click="exportLedgerCSV" :disabled="!ledgerDrawer.rows.length">📥 Export CSV</button>
        </div>
        <div style="flex:1;overflow-y:auto;padding:16px 24px">
          <div v-if="ledgerDrawer.loading" style="text-align:center;padding:32px;color:#9ca3af">Loading ledger…</div>
          <div v-else-if="!ledgerDrawer.rows.length" style="text-align:center;padding:32px;color:#9ca3af">No transactions in this period.</div>
          <template v-else>
            <!-- Desktop ledger table -->
            <table v-if="!isMobile" class="b-table ldg-desktop-table" style="width:100%;border-collapse:collapse;font-size:12.5px">
              <thead>
                <tr style="background:#f9fafb">
                  <th style="text-align:left;padding:8px 10px;font-size:11px;color:#6b7280;text-transform:uppercase;font-weight:700">Date</th>
                  <th style="text-align:left;padding:8px 10px;font-size:11px;color:#6b7280;text-transform:uppercase;font-weight:700">Voucher</th>
                  <th style="text-align:left;padding:8px 10px;font-size:11px;color:#6b7280;text-transform:uppercase;font-weight:700">Type</th>
                  <th style="text-align:left;padding:8px 10px;font-size:11px;color:#6b7280;text-transform:uppercase;font-weight:700">Party</th>
                  <th style="text-align:right;padding:8px 10px;font-size:11px;color:#6b7280;text-transform:uppercase;font-weight:700">Debit</th>
                  <th style="text-align:right;padding:8px 10px;font-size:11px;color:#6b7280;text-transform:uppercase;font-weight:700">Credit</th>
                  <th style="text-align:right;padding:8px 10px;font-size:11px;color:#6b7280;text-transform:uppercase;font-weight:700">Balance</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in ledgerDrawer.rows" :key="(r.name||r.voucher_no)+'-'+r.posting_date"
                  style="border-top:1px solid #f3f4f6">
                  <td style="padding:8px 10px;color:#6b7280">{{ r.posting_date }}</td>
                  <td style="padding:8px 10px;color:#2563eb;font-weight:600"><DocLink :doctype="r.voucher_type" :name="r.voucher_no" /></td>
                  <td style="padding:8px 10px;color:#6b7280">{{ r.voucher_type }}</td>
                  <td style="padding:8px 10px;color:#374151" :title="r.party || ''">{{ r.party_name || r.party || '—' }}</td>
                  <td style="padding:8px 10px;text-align:right;color:#16a34a">{{ getRowDr(r) > 0 ? "₹"+getRowDr(r).toLocaleString("en-IN",{minimumFractionDigits:2}) : '—' }}</td>
                  <td style="padding:8px 10px;text-align:right;color:#dc2626">{{ getRowCr(r) > 0 ? "₹"+getRowCr(r).toLocaleString("en-IN",{minimumFractionDigits:2}) : '—' }}</td>
                  <td style="padding:8px 10px;text-align:right;font-weight:700" :style="{color: r.balance > 0 ? '#16a34a' : r.balance < 0 ? '#dc2626' : '#374151'}">
                    ₹{{ Number(r.balance).toLocaleString("en-IN",{minimumFractionDigits:2}) }}
                  </td>
                </tr>
              </tbody>
              <tfoot v-if="ledgerDrawer.rows.length">
                <tr style="background:#f9fafb;border-top:2px solid #e5e7eb">
                  <td colspan="4" style="padding:10px;font-weight:700;color:#374151">Closing Balance</td>
                  <td colspan="2"></td>
                  <td style="padding:10px;text-align:right;font-weight:800;font-size:14px" :style="{color: ledgerDrawer.rows[ledgerDrawer.rows.length-1].balance > 0 ? '#16a34a' : '#dc2626'}">
                    ₹{{ Number(ledgerDrawer.rows[ledgerDrawer.rows.length-1].balance).toLocaleString("en-IN",{minimumFractionDigits:2}) }}
                  </td>
                </tr>
              </tfoot>
            </table>

            <!-- Mobile ledger cards -->
            <div v-if="isMobile" class="ldg-mobile-cards">
              <div v-for="r in ledgerDrawer.rows" :key="'lmc-'+(r.name||r.voucher_no)+'-'+r.posting_date"
                class="ldg-entry-card"
                :class="r.balance > 0 ? 'ldg-card--dr' : r.balance < 0 ? 'ldg-card--cr' : 'ldg-card--zero'">
                <!-- Row 1: Date + Voucher type -->
                <div class="ldg-card-top">
                  <span class="ldg-card-date">{{ r.posting_date }}</span>
                  <span class="ldg-card-vtype">{{ r.voucher_type }}</span>
                </div>
                <!-- Row 2: Voucher no + Party -->
                <div class="ldg-card-mid">
                  <span class="ldg-card-voucher" @click.stop><DocLink :doctype="r.voucher_type" :name="r.voucher_no" :mono-style="false" /></span>
                  <span class="ldg-card-party">{{ r.party_name || r.party || '—' }}</span>
                </div>
                <!-- Row 3: Debit | Credit | Balance strip -->
                <div class="ldg-card-strip">
                  <div class="ldg-strip-cell">
                    <span class="ldg-strip-lbl">Debit</span>
                    <span class="ldg-strip-val ldg-strip-dr">{{ getRowDr(r) > 0 ? "₹"+getRowDr(r).toLocaleString("en-IN",{minimumFractionDigits:2}) : '—' }}</span>
                  </div>
                  <div class="ldg-strip-cell ldg-strip-cell--mid">
                    <span class="ldg-strip-lbl">Credit</span>
                    <span class="ldg-strip-val ldg-strip-cr">{{ getRowCr(r) > 0 ? "₹"+getRowCr(r).toLocaleString("en-IN",{minimumFractionDigits:2}) : '—' }}</span>
                  </div>
                  <div class="ldg-strip-cell">
                    <span class="ldg-strip-lbl">Balance</span>
                    <span class="ldg-strip-val" :style="{color: r.balance > 0 ? '#16a34a' : r.balance < 0 ? '#dc2626' : '#374151'}">
                      ₹{{ Number(r.balance).toLocaleString("en-IN",{minimumFractionDigits:2}) }}
                    </span>
                  </div>
                </div>
              </div>
              <!-- Closing balance card -->
              <div v-if="ledgerDrawer.rows.length" class="ldg-closing-card">
                <span class="ldg-closing-lbl">Closing Balance</span>
                <span class="ldg-closing-val"
                  :style="{color: ledgerDrawer.rows[ledgerDrawer.rows.length-1].balance > 0 ? '#16a34a' : '#dc2626'}">
                  ₹{{ Number(ledgerDrawer.rows[ledgerDrawer.rows.length-1].balance).toLocaleString("en-IN",{minimumFractionDigits:2}) }}
                </span>
              </div>
            </div><!-- end .ldg-mobile-cards -->
          </template>
        </div>
      </div>
    </div>
  </Teleport>
</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from "vue";
import { apiGET, apiPOST, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";
import { flt } from "../utils/format.js";
import SearchableSelect from "../components/SearchableSelect.vue";
import DocLink from "../components/DocLink.vue";
import { usePermissions } from "../composables/usePermissions.js";

const { toast } = useToast();
const { canCreate, canEdit, canDelete } = usePermissions();

const TYPE_META_COA = {
  Asset:     { color: "#0C8599", bg: "#E0F7FA", dr: true  },
  Liability: { color: "#C92A2A", bg: "#FFE3E3", dr: false },
  Equity:    { color: "#2563eb", bg: "#F3F0FF", dr: false },
  Income:    { color: "#2F9E44", bg: "#EBFBEE", dr: false },
  Expense:   { color: "#E67700", bg: "#FFF3BF", dr: true  },
};
const ACCOUNT_TYPES_COA = {
  Asset:     ["Asset","Bank","Cash","Receivable","Tax"],
  Liability: ["Liability","Payable","Tax"],
  Equity:    ["Equity"],
  Income:    ["Income"],
  Expense:   ["Expense"],
};
const STANDARD_COA_DATA = [
  {name:"Current Assets",code:"1000",root_type:"Asset",account_type:"",is_group:1,parent:"",opening:0,bal_type:"Debit"},
  {name:"Cash in Hand",code:"1001",root_type:"Asset",account_type:"Cash",is_group:0,parent:"Current Assets",opening:50000,bal_type:"Debit"},
  {name:"Bank Accounts",code:"1010",root_type:"Asset",account_type:"Bank",is_group:1,parent:"Current Assets",opening:0,bal_type:"Debit"},
  {name:"HDFC Current Account",code:"1011",root_type:"Asset",account_type:"Bank",is_group:0,parent:"Bank Accounts",opening:500000,bal_type:"Debit"},
  {name:"Accounts Receivable",code:"1100",root_type:"Asset",account_type:"Receivable",is_group:0,parent:"Current Assets",opening:0,bal_type:"Debit"},
  {name:"Fixed Assets",code:"1500",root_type:"Asset",account_type:"",is_group:1,parent:"",opening:0,bal_type:"Debit"},
  {name:"Current Liabilities",code:"2000",root_type:"Liability",account_type:"",is_group:1,parent:"",opening:0,bal_type:"Credit"},
  {name:"Accounts Payable",code:"2100",root_type:"Liability",account_type:"Payable",is_group:0,parent:"Current Liabilities",opening:0,bal_type:"Credit"},
  {name:"Share Capital",code:"3000",root_type:"Equity",account_type:"Equity",is_group:0,parent:"",opening:1000000,bal_type:"Credit"},
  {name:"Retained Earnings",code:"3100",root_type:"Equity",account_type:"Retained Earnings",is_group:0,parent:"",opening:0,bal_type:"Credit"},
  {name:"Revenue",code:"4000",root_type:"Income",account_type:"",is_group:1,parent:"",opening:0,bal_type:"Credit"},
  {name:"Sales Revenue",code:"4001",root_type:"Income",account_type:"Income Account",is_group:0,parent:"Revenue",opening:0,bal_type:"Credit"},
  {name:"Operating Expenses",code:"5100",root_type:"Expense",account_type:"",is_group:1,parent:"",opening:0,bal_type:"Debit"},
  {name:"Salaries & Wages",code:"5101",root_type:"Expense",account_type:"Expense Account",is_group:0,parent:"Operating Expenses",opening:0,bal_type:"Debit"},
];

const allAccounts    = ref([]);
const loading        = ref(true);
const typeFilter     = ref("");
const searchQ        = ref("");
const viewMode       = ref("list"); // "list" | "tree"
const expandedGroups = ref(new Set());

function toggleGroup(name) {
  const s = new Set(expandedGroups.value);
  if (s.has(name)) s.delete(name); else s.add(name);
  expandedGroups.value = s;
}
function isExpanded(name) {
  return expandedGroups.value.has(name);
}
function expandAllGroups() {
  expandedGroups.value = new Set(allAccounts.value.filter(a => a.is_group).map(a => a.name));
}
function collapseAllGroups() {
  expandedGroups.value = new Set();
}
const drawerOpen     = ref(false);
const editingName    = ref(null);
const drawerSaving   = ref(false);
const showDel        = ref(false);
const deleteTarget   = ref(null);

const form = reactive({
  name: "", code: "", root_type: "", account_type: "", parent: "",
  is_group: 0, bs_item: 1, opening: "", bal_type: "Debit", notes: "",
});

const typeStats = computed(() =>
  ["Asset","Liability","Equity","Income","Expense"].map((t) => {
    const accts = allAccounts.value.filter((a) => a.root_type === t && !a.is_group);
    const tot = accts.reduce((s, a) => s + Number(a.opening || 0), 0);
    return { type: t, count: accts.length, total: tot, meta: TYPE_META_COA[t] };
  })
);

const accountTypeOptions = computed(() => ACCOUNT_TYPES_COA[form.root_type] || []);
const parentOptions      = computed(() => allAccounts.value.filter((a) => a.is_group));

// List view (no tree nesting, groups hidden): sorted by root type, then code/name.
// Tree view: groups are shown as expandable parent rows with children nested underneath.
const ROOT_TYPE_ORDER = { Asset: 0, Liability: 1, Equity: 2, Income: 3, Expense: 4 };

function sortAccts(list) {
  return list.slice().sort((a, b) => {
    const ro = (ROOT_TYPE_ORDER[a.root_type] ?? 9) - (ROOT_TYPE_ORDER[b.root_type] ?? 9);
    if (ro !== 0) return ro;
    if (!!a.is_group !== !!b.is_group) return a.is_group ? -1 : 1;
    const ca = (a.code || "").toString(), cb = (b.code || "").toString();
    if (ca && cb && ca !== cb) return ca.localeCompare(cb, undefined, { numeric: true });
    return (a.account_name || a.name).localeCompare(b.account_name || b.name);
  });
}

const flatTree = computed(() => {
  const q = searchQ.value.toLowerCase().trim();
  const tf = typeFilter.value;
  const matches = (a) => {
    if (tf && a.root_type !== tf) return false;
    if (!q) return true;
    const nm = (a.account_name || a.name).toLowerCase();
    const cd = (a.code || "").toLowerCase();
    return nm.includes(q) || cd.includes(q);
  };

  if (viewMode.value === "list") {
    // List view: leaf accounts only, no group accounts shown.
    const rows = allAccounts.value.filter((a) => !a.is_group && matches(a));
    return sortAccts(rows).map((a) => ({ ...a, depth: 0 }));
  }

  // Tree view: build a real hierarchy from parent/child relationships.
  const byParent = new Map();
  allAccounts.value.forEach((a) => {
    const p = a.parent || "";
    if (!byParent.has(p)) byParent.set(p, []);
    byParent.get(p).push(a);
  });

  // When searching/filtering, auto-expand ancestors of matches so results are visible.
  const searching = !!(q || tf);
  let visibleNames = null;
  if (searching) {
    visibleNames = new Set();
    const byName = new Map(allAccounts.value.map((a) => [a.name, a]));
    allAccounts.value.forEach((a) => {
      if (matches(a)) {
        let cur = a;
        while (cur) {
          visibleNames.add(cur.name);
          cur = cur.parent ? byName.get(cur.parent) : null;
        }
      }
    });
  }

  const out = [];
  function walk(parentName, depth) {
    const kids = sortAccts(byParent.get(parentName) || []);
    for (const a of kids) {
      if (visibleNames && !visibleNames.has(a.name)) continue;
      out.push({ ...a, depth });
      const hasKids = (byParent.get(a.name) || []).length > 0;
      if (a.is_group && hasKids && (searching || isExpanded(a.name))) {
        walk(a.name, depth + 1);
      }
    }
  }
  walk("", 0);
  return out;
});

function fmtINR(v) {
  if (!v && v !== 0) return "—";
  const n = Number(v);
  if (n === 0) return "—";
  return "₹" + Math.abs(n).toLocaleString("en-IN", { minimumFractionDigits: 2 });
}

async function load() {
  loading.value = true;
  try {
    let frappeAccts = [];
    try {
      const company = await resolveCompany();
      const res = await apiGET("zoho_books_clone.api.books_data.get_chart_of_accounts", { company });
      frappeAccts = Array.isArray(res) ? res : [];
      if (company) {
        const nameSet = new Set(frappeAccts.map((a) => a.account_name || a.name));
        frappeAccts = frappeAccts.filter((a) => {
          const nm = a.account_name || a.name;
          return nm.endsWith(" - " + company) || !nameSet.has(nm + " - " + company);
        });
      }
    } catch {}

    if (frappeAccts && frappeAccts.length) {
      const guessRootType = (a) => {
        if (a.root_type) return a.root_type;
        const t = (a.account_type || "").toLowerCase().trim();
        if (t === "income" || t === "other income" || t.includes("income account")) return "Income";
        if (t === "expense" || t === "other expense" || t.includes("expense account") || t === "cost of goods sold" || t === "depreciation") return "Expense";
        if (t === "payable" || t === "liability" || t === "other liability" || t === "credit card" || t === "current liability") return "Liability";
        if (t === "equity" || t === "retained earnings") return "Equity";
        return "Asset";
      };
      // Most reliable signal: the account's ROOT ancestor group. This DB's
      // Account table has no root_type column, so we derive the type by walking
      // up parent_account to the root and mapping its name. Falls back to the
      // account_type guess above only when the root isn't a recognised group
      // (fixes e.g. "Stock Adjustment" under Expenses being mislabelled Asset).
      const byName = new Map(frappeAccts.map((x) => [x.name, x]));
      const ROOT_NAME_MAP = {
        assets: "Asset", asset: "Asset",
        liabilities: "Liability", liability: "Liability",
        equity: "Equity",
        income: "Income", revenue: "Income",
        expenses: "Expense", expense: "Expense",
      };
      const rootType = (a) => {
        let cur = a, guard = 0;
        while (cur && cur.parent_account && guard++ < 50) {
          const p = byName.get(cur.parent_account);
          if (!p) break;
          cur = p;
        }
        return ROOT_NAME_MAP[(cur.account_name || cur.name || "").toLowerCase().trim()] || guessRootType(a);
      };
      allAccounts.value = frappeAccts.map((a) => ({
        name: a.name,
        account_name: a.account_name || a.name,
        code: a.account_number || "",
        root_type: rootType(a),
        account_type: a.account_type || "",
        is_group: a.is_group ? 1 : 0,
        parent: a.parent_account || "",
        opening: Number(a.opening_balance || 0),
        bal_type: a.balance_must_be || "Debit",
        source: "frappe",
      }));
      try { localStorage.removeItem("books_coa"); } catch {}
    } else {
      const saved = (() => { try { const s = localStorage.getItem("books_coa"); return s ? JSON.parse(s) : null; } catch { return null; } })();
      if (saved && saved.length) {
        allAccounts.value = saved;
      } else {
        allAccounts.value = STANDARD_COA_DATA.map((a) => ({ ...a, account_name: a.name, source: "local" }));
        try { localStorage.setItem("books_coa", JSON.stringify(allAccounts.value)); } catch {}
      }
    }
  } finally {
    loading.value = false;
  }
}

function openAdd(parentName) {
  editingName.value = null;
  Object.assign(form, { name: "", code: "", root_type: "", account_type: "", parent: parentName || "", is_group: 0, bs_item: 1, opening: "", bal_type: "Debit", notes: "" });
  drawerOpen.value = true;
}

function openEdit(acctName) {
  const a = allAccounts.value.find((x) => x.name === acctName);
  if (!a) return;
  editingName.value = acctName;
  Object.assign(form, {
    name: a.account_name || a.name,
    code: a.code || "",
    root_type: a.root_type || "",
    account_type: a.account_type || "",
    parent: a.parent || "",
    is_group: a.is_group ? 1 : 0,
    bs_item: ["Asset", "Liability", "Equity"].includes(a.root_type) ? 1 : 0,
    opening: a.opening || "",
    bal_type: a.bal_type || "Debit",
    notes: a.notes || "",
  });
  drawerOpen.value = true;
}

async function saveAccount() {
  if (!(editingName.value ? canEdit("accounts") : canCreate("accounts"))) { toast("Read-only access", "error"); return; }
  if (!form.name.trim())  { toast("Account name is required", "error"); return; }
  if (!form.root_type)    { toast("Root Type is required", "error");    return; }
  drawerSaving.value = true;
  let savedName = editingName.value || "";
  try {
    const payload = {
      account_name: form.name.trim(),
      account_number: form.code.trim(),
      root_type: form.root_type,
      account_type: form.account_type,
      parent_account: form.parent || "",
      is_group: form.is_group ? 1 : 0,
      opening_balance: flt(form.opening),
      balance_must_be: form.bal_type,
    };
    if (editingName.value) {
      try {
        await apiPOST("zoho_books_clone.api.books_data.save_account", { op: "update", name: editingName.value, ...payload });
      } catch (e) { toast(e.message || "Frappe update failed", "error"); }
      const idx = allAccounts.value.findIndex((x) => x.name === editingName.value);
      if (idx >= 0) {
        allAccounts.value[idx] = { ...allAccounts.value[idx], account_name: form.name.trim(), code: form.code.trim(), root_type: form.root_type, account_type: form.account_type, parent: form.parent, is_group: form.is_group ? 1 : 0, opening: flt(form.opening), bal_type: form.bal_type, notes: form.notes };
      }
      toast("Account updated", "success");
    } else {
      let newName = form.name.trim();
      try {
        const res = await apiPOST("zoho_books_clone.api.books_data.save_account", { op: "create", ...payload });
        if (res && res.name) newName = res.name;
      } catch (e) { toast(e.message || "Frappe create failed", "error"); }
      allAccounts.value.push({ name: newName, account_name: form.name.trim(), code: form.code.trim(), root_type: form.root_type, account_type: form.account_type, parent: form.parent, is_group: form.is_group ? 1 : 0, opening: flt(form.opening), bal_type: form.bal_type, notes: form.notes, source: "frappe" });
      toast("Account created", "success");
      savedName = newName;
    }
    drawerOpen.value = false;
    await load();
    // `load()` rebuilds `allAccounts` as a fresh array of new objects, so the
    // detail panel's `selectedAccount` (still pointing at the pre-save object)
    // would otherwise keep showing the old values — e.g. Balance Type staying
    // "Debit" in the UI even though the save succeeded. Re-point it at the
    // freshly-loaded record for whichever account was just edited/created.
    if (savedName) {
      const fresh = allAccounts.value.find((x) => x.name === savedName);
      if (fresh) selectedAccount.value = fresh;
    }
  } catch (e) {
    toast(e.message || "Save failed", "error");
  } finally {
    drawerSaving.value = false;
  }
}
function canDeleteAccount(account) {
  if (!account) return false;
  if (account.is_group) return false;
  if (!canDelete("accounts")) return false;

  // Local accounts have no Frappe ledger
  if (account.source !== "frappe") return true;

  // Don't show Delete until ledger check is completed
  const ledger = inlineLedger[account.name];

  if (!ledger || ledger.loading) return false;

  // Delete is allowed only when there are no transactions
  return ledger.rows.length === 0;
}

function confirmDelete(name) {
  if (!canDelete("accounts")) { toast("Not permitted", "error"); return; }
  deleteTarget.value = name; showDel.value = true;
}

async function doDelete() {
  if (!canDelete("accounts")) {
    toast("Not permitted", "error");
    showDel.value = false;
    return;
  }

  const name = deleteTarget.value;

  if (!name) {
    showDel.value = false;
    return;
  }

  try {
    await apiPOST(
      "zoho_books_clone.api.books_data.save_account",
      {
        op: "delete",
        name: name
      }
    );

    // Only update the UI after the backend confirms deletion
    allAccounts.value = allAccounts.value.filter(
      (a) => a.name !== name && a.parent !== name
    );

    if (selectedAccount.value?.name === name) {
      selectedAccount.value = null;
    }

    showDel.value = false;
    deleteTarget.value = null;

    toast("Account deleted", "success");

    await load();

  } catch (e) {
    // Backend rejected the deletion.
    // Keep the account in the UI.
    toast(e.message || "Delete failed", "error");
  }
}

// ── Live account balances (from GL) ───────────────────────────────────────
const balances = ref({});  // { account_name: number } — signed: >0 Dr, <0 Cr
const balancesLoading = ref(false);

// Trial balance: sum of leaf-account debit vs credit balances. In a balanced
// ledger the two totals are equal (difference ≈ 0).
const trialBalance = computed(() => {
  let dr = 0, cr = 0;
  for (const v of Object.values(balances.value)) {
    const n = Number(v) || 0;
    if (n > 0) dr += n; else if (n < 0) cr += -n;
  }
  const diff = Math.round((dr - cr) * 100) / 100;
  return { dr, cr, diff, balanced: Math.abs(diff) < 0.01 };
});
function fmtBal(v) {
  const n = Number(v || 0);
  if (Math.abs(n) < 0.005) return "—";
  return "₹" + Math.abs(n).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function getBalType(val, defaultType) {
  const n = Number(val || 0);
  if (n < 0) return defaultType === 'Credit' ? 'Debit' : 'Credit';
  return defaultType || 'Debit';
}
function getRowDr(r) {
  const dr = Number(r.debit || 0), cr = Number(r.credit || 0);
  return dr > 0 ? dr : (cr < 0 ? -cr : 0);
}
function getRowCr(r) {
  const dr = Number(r.debit || 0), cr = Number(r.credit || 0);
  return cr > 0 ? cr : (dr < 0 ? -dr : 0);
}
async function loadBalances() {
  const ledger = allAccounts.value.filter(a => !a.is_group && a.source === "frappe");
  if (!ledger.length) return;
  balancesLoading.value = true;
  // Was previously one get_account_balance() call per leaf account, sent in
  // chunks of 10 -- for a real chart of accounts (100+ leaf accounts) that's
  // 10+ sequential round trips just to paint balances, which is what made
  // this page feel heavy. get_account_balances_bulk() (already used by
  // Expenses.vue) returns every balance in one query.
  try {
    const map = await apiGET("zoho_books_clone.db.queries.get_account_balances_bulk", {
      accounts: ledger.map(a => a.name),
    }) || {};
    balances.value = map;
  } catch {
    balances.value = {};
  }
  balancesLoading.value = false;
}

// ── GL drill-down drawer ──────────────────────────────────────────────────
const ledgerDrawer = reactive({
  open: false, loading: false, account: "", account_label: "",
  from_date: "", to_date: "", rows: [],
});
function todayStr() { return new Date().toISOString().slice(0, 10); }
function monthsAgo(n) { const d = new Date(); d.setMonth(d.getMonth() - n); return d.toISOString().slice(0, 10); }

async function openLedger(acct) {
  Object.assign(ledgerDrawer, {
    open: true, loading: true,
    account: acct.name, account_label: acct.account_name || acct.name,
    from_date: monthsAgo(3), to_date: todayStr(), rows: [],
  });
  await fetchLedger();
}
async function fetchLedger() {
  ledgerDrawer.loading = true;
  try {
    const company = await resolveCompany();
    const rows = await apiGET("zoho_books_clone.db.queries.get_gl_entries", {
      company,
      account: ledgerDrawer.account,
      from_date: ledgerDrawer.from_date || "2000-01-01",
      to_date: ledgerDrawer.to_date || "2099-12-31",
    }) || [];
    // Compute running balance
    let bal = 0;
    rows.forEach(r => {
      bal += Number(r.debit || 0) - Number(r.credit || 0);
      r.balance = bal;
    });
    ledgerDrawer.rows = rows;
  } catch (e) {
    toast(e?.message || "Failed to load ledger", "error");
  }
  ledgerDrawer.loading = false;
}
function closeLedger() { ledgerDrawer.open = false; }

const PAGE_SIZE = 10;
const inlineLedger = reactive({}); // { [accountName]: { loading, rows, visible } }
const selectedAccount = ref(null);

// Date range filter for the "Recent Transactions" panel (right-side detail view)
const coaFilterFrom = ref("");
const coaFilterTo = ref("");

async function fetchInlineLedger(row, opts = {}) {
  const { force = false, fromDate = "2000-01-01", toDate = "2099-12-31" } = opts;
  if (inlineLedger[row.name] && !force) return;
  inlineLedger[row.name] = { loading: true, rows: [], visible: PAGE_SIZE };
  try {
    const company = await resolveCompany();
    const rows = await apiGET("zoho_books_clone.db.queries.get_gl_entries", {
      company,
      account: row.name,
      from_date: fromDate,
      to_date: toDate,
    }) || [];
    let bal = 0;
    rows.forEach((r) => { bal += Number(r.debit || 0) - Number(r.credit || 0); r.balance = bal; });
    rows.reverse(); // most recent first
    if (inlineLedger[row.name]) { inlineLedger[row.name].rows = rows; inlineLedger[row.name].loading = false; }
  } catch (e) {
    toast(e?.message || "Failed to load ledger entries", "error");
    if (inlineLedger[row.name]) inlineLedger[row.name].loading = false;
  }
}

function selectAccount(row) {
  selectedAccount.value = row;
  // Reset the date filter when switching accounts
  coaFilterFrom.value = "";
  coaFilterTo.value = "";
  if (!row.is_group && row.source === "frappe") fetchInlineLedger(row, { force: true });
}

function applyCoaDateFilter(row) {
  if (!row) return;
  fetchInlineLedger(row, {
    force: true,
    fromDate: coaFilterFrom.value || "2000-01-01",
    toDate: coaFilterTo.value || "2099-12-31",
  });
}

function clearCoaDateFilter(row) {
  coaFilterFrom.value = "";
  coaFilterTo.value = "";
  if (row) fetchInlineLedger(row, { force: true });
}

function handleRowClick(row) {
  if (row.is_group && viewMode.value === "tree") { toggleGroup(row.name); return; }
  if (!row.is_group && row.source === "frappe") toggleInlineLedger(row);
  else openEdit(row.name);
}

async function toggleInlineLedger(row) {
  if (inlineLedger[row.name]) { delete inlineLedger[row.name]; return; }
  await fetchInlineLedger(row);
}

function loadMoreInline(name) {
  if (inlineLedger[name]) inlineLedger[name].visible += PAGE_SIZE;
}

function exportLedgerCSV() {
  if (!ledgerDrawer.rows.length) return;
  const head = ["Date","Voucher","Type","Party","Debit","Credit","Balance","Remarks"];
  const esc = v => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const out = [head.map(esc).join(",")];
  for (const r of ledgerDrawer.rows) {
    out.push([r.posting_date, r.voucher_no, r.voucher_type, r.party_name || r.party || "",
      Number(r.debit || 0).toFixed(2), Number(r.credit || 0).toFixed(2),
      Number(r.balance || 0).toFixed(2), r.remarks || ""].map(esc).join(","));
  }
  const blob = new Blob(["﻿" + out.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `ledger_${ledgerDrawer.account_label.replace(/[^a-z0-9]/gi, "_")}_${todayStr()}.csv`;
  a.click(); URL.revokeObjectURL(url);
  toast("Ledger CSV exported", "success");
}

const isMobile = ref(window.innerWidth <= 425);
function onResize() { isMobile.value = window.innerWidth <= 425; }

onMounted(async () => {
  await load();
  loadBalances();
  window.addEventListener("resize", onResize, { passive: true });
});
onUnmounted(() => window.removeEventListener("resize", onResize));
</script>

<style scoped>
/* ── Inline ledger (list-view row expansion) ── */
.coa-row-expanded { background: #f8fafc; }
.coa-inline-ledger-row td { border-top: none !important; }
.coa-inline-ledger {
  border-top: 1px solid #e5e7eb;
  border-bottom: 2px solid #e5e7eb;
  background: #fafbfc;
}
.coa-mc-header .coa-mc-toggle,
.coa-toggle { cursor: pointer; }

/* ── View toggle (List / Tree) ── */
.coa-view-toggle {
  display: inline-flex; border: 1px solid #e2e8f0; border-radius: 20px; overflow: hidden;
}
.coa-view-btn {
  border: none; background: #fff; padding: 6px 14px; font-size: 12.5px; font-weight: 600;
  color: #64748b; cursor: pointer; transition: background .15s, color .15s;
}
.coa-view-btn + .coa-view-btn { border-left: 1px solid #e2e8f0; }
.coa-view-btn.active { background: #3b5bdb; color: #fff; }

/* Expand/collapse chevron used for group rows in tree view */
.coa-split-row > .coa-toggle {
  display: inline-flex; align-items: center; justify-content: center;
  width: 18px; height: 18px; flex-shrink: 0; border: none; background: transparent;
  color: #64748b; padding: 0; transition: transform .15s;
}
.coa-split-row > .coa-toggle.open { transform: rotate(90deg); }

/* ── Split view: account list + detail panel (Zoho-style) ── */
.coa-split { min-height: 520px; max-height: 74vh; }
.coa-split-list {
  width: 320px; flex-shrink: 0; border-right: 1px solid #e5e7eb;
  display: flex; flex-direction: column; overflow: hidden;
}
.coa-split-list-head {
  display: flex; justify-content: space-between; padding: 10px 14px;
  font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .4px;
  color: #6b7280; background: #f9fafb; border-bottom: 1px solid #e5e7eb; flex-shrink: 0;
}
.coa-split-list-body { overflow-y: auto; flex: 1; }
.coa-split-row {
  display: flex; align-items: center; gap: 8px; padding: 10px 14px;
  cursor: pointer; border-bottom: 1px solid #f3f4f6;
}
.coa-split-row:hover { background: #f8fafc; }
.coa-split-row.active { background: #eff6ff; border-left: 3px solid #2563eb; padding-left: 11px; }
.coa-lock-ic { font-size: 11px; opacity: .55; flex-shrink: 0; }
.coa-split-row-main { min-width: 0; flex: 1; }
.coa-split-row-name {
  font-size: 13px; font-weight: 600; color: #232336; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap;
}
.coa-split-row-type { font-size: 11.5px; color: #9ca3af; margin-top: 1px; }
.coa-split-row-bal { font-size: 12px; font-weight: 700; flex-shrink: 0; white-space: nowrap; margin-left: 6px; }
.coa-split-detail { flex: 1; overflow-y: auto; min-width: 0; }
.coa-split-empty {
  height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 10px; color: #9ca3af; font-size: 13px;
}
.coa-split-empty svg { opacity: .35; }
.coa-detail-head { display: flex; justify-content: space-between; align-items: flex-start;padding:10px 20px }
.coa-detail-type { font-size: 12px; color: #868e96; }
.coa-detail-name { font-size: 21px; font-weight: 800; color: #1a1a2e; margin-top: 2px; }
.coa-detail-edit {
  display: flex; align-items: center; gap: 6px;padding: 5px 26px;
  border-bottom: 1px solid #f0f1f3; font-size: 12.5px; color: #2563eb; cursor: pointer;
}
.coa-detail-edit a { color: inherit; cursor: pointer; }
.coa-detail-balance {
  background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 10px;
  padding: 6px 8px;width:max-content;
}
.coa-detail-balance-lbl { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .4px; color: #6b7280; }
.coa-detail-balance-val { font-size: 16px; font-weight: 800; margin-top: 6px; }
.coa-detail-balance-tag { font-size: 15px; font-weight: 600; margin-left: 4px; }
.coa-detail-desc { font-size: 12.5px; color: #6b7280; margin-top: 10px; font-style: italic; line-height: 1.5; }
.coa-detail-txn-head {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 15px; font-weight: 700; color: #1a1a2e; margin: 18px 0 8px;padding: 0px 20px;
}
.coa-detail-txn-head input[type="date"] {
  border: 1px solid #e2e8f0; border-radius: 7px; padding: 5px 8px; font-size: 12px;
  font-family: inherit; color: #374151; background: #fff;
}
.coa-detail-txn-head input[type="date"]:focus {
  outline: none; border-color: #1a6ef7; box-shadow: 0 0 0 3px rgba(26,110,247,.13);
}
.coa-detail-txns { border: 1px solid #e5e7eb;overflow: hidden; }
.coa-txn-tbl-head, .coa-txn-row {
  display: grid; grid-template-columns: 100px 1.6fr 110px 100px 100px 110px; gap: 8px; align-items: center;
}
.coa-txn-tbl-head {
  padding: 8px 14px; background: #f9fafb; font-size: 10.5px; font-weight: 700;
  text-transform: uppercase; letter-spacing: .4px; color: #6b7280; border-bottom: 1px solid #e5e7eb;
}
.coa-txn-row { padding: 10px 14px; font-size: 12.5px; border-bottom: 1px solid #f3f4f6; }
.coa-txn-row:last-child { border-bottom: none; }
.coa-txn-date { color: #6b7280; }
.coa-txn-detail { color: #1a1a2e; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.coa-txn-type { color: #6b7280; }
.coa-txn-dr { color: #16a34a; font-weight: 600; }
.coa-txn-cr { color: #dc2626; font-weight: 600; }
.coa-txn-bal { font-weight: 700; }
.coa-detail-loadmore {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 14px; background: #f9fafb; font-size: 11.5px; color: #868e96;
}
@media (max-width: 900px) {
  .coa-split-list { width: 240px; }
  .coa-txn-tbl-head, .coa-txn-row { grid-template-columns: 80px 1.4fr 90px 80px 80px 90px; font-size: 11.5px; }
}

/* ═══════════════════════════════════════════════════════════════════
   COA MOBILE CARD VIEW  –  375 px … 425 px
   By default (all widths): mobile cards hidden, desktop table shown.
   Inside the media query: flip visibility.
   ═══════════════════════════════════════════════════════════════════ */

/* ── Default: mobile card container hidden everywhere ── */
.coa-mobile-cards {
  display: none;
}

/* ── Default: desktop split view visible everywhere ── */
.coa-desktop-table {
  display: flex;
}

/* ── Activate card layout only on 375 px – 425 px ── */
@media (min-width: 375px) and (max-width: 425.98px) {

  /* Hide desktop table */
  .coa-desktop-table {
    display: none !important;
  }

  /* Show card list */
  .coa-mobile-cards {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px 10px;
    background: #f8fafc;
  }

  /* ── Individual account card ── */
  .coa-mobile-card {
    background: #ffffff;
    border-radius: 10px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    overflow: hidden;
    cursor: pointer;
    transition: box-shadow 0.15s, border-color 0.15s;
  }

  .coa-mobile-card:active {
    box-shadow: 0 1px 2px rgba(0,0,0,0.08);
    border-color: #cbd5e1;
  }

  /* Group cards: subtle top accent bar */
  .coa-mobile-card--group {
    border-top: 3px solid var(--mc-accent, #0C8599);
  }

  /* ── Card header ── */
  .coa-mc-header {
    padding: 11px 12px 8px;
    border-bottom: 1px solid #f3f4f6;
  }

  .coa-mc-name-row {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: nowrap;
    margin-bottom: 6px;
  }

  .coa-mc-toggle {
    flex-shrink: 0;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    background: #f1f5f9;
    border: 1px solid #e2e8f0;
    cursor: pointer;
    padding: 0;
    transition: background 0.15s;
  }

  .coa-mc-toggle.open {
    background: var(--mc-bg, #E0F7FA);
    border-color: var(--mc-accent, #0C8599);
    transform: rotate(90deg);
  }

  .coa-mc-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
    display: inline-block;
  }

  .coa-mc-acct-name {
    font-size: 13.5px;
    color: #1a202c;
    line-height: 1.3;
    word-break: break-word;
  }

  .coa-mc-acct-name--bold {
    font-weight: 700;
  }

  /* ── Badge row under the name ── */
  .coa-mc-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    align-items: center;
    margin-top: 2px;
  }

  .coa-mc-type-badge {
    font-size: 10px;
    font-weight: 600;
    padding: 2px 7px;
    border-radius: 20px;
    letter-spacing: 0.3px;
  }

  .coa-mc-group-chip {
    font-size: 10px;
    font-weight: 600;
    padding: 2px 7px;
    border-radius: 20px;
  }

  .coa-mc-acct-type-chip {
    font-size: 10px;
    color: #6b7280;
    background: #f3f4f6;
    padding: 2px 6px;
    border-radius: 20px;
  }

  /* ── Card body: labeled data rows ── */
  .coa-mc-body {
    padding: 8px 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .coa-mc-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    min-height: 22px;
  }

  .coa-mc-label {
    font-size: 11px;
    color: #9ca3af;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .coa-mc-value {
    font-size: 12.5px;
    font-weight: 600;
    color: #374151;
    text-align: right;
    word-break: break-all;
  }

  .coa-mc-value--code {
    font-size: 12px;
    color: #6b7280;
    font-weight: 500;
  }

  /* ── Card footer: action buttons ── */
  .coa-mc-footer {
    display: flex;
    align-items: center;
    gap: 2px;
    padding: 7px 10px 8px;
    border-top: 1px solid #f3f4f6;
    background: #fafafa;
  }

  .coa-mc-action-btn {
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

  .coa-mc-action-btn:hover {
    background: #e5e7eb;
    border-color: #d1d5db;
  }

  .coa-mc-action-btn.danger {
    color: #dc2626;
    background: #fff1f2;
    border-color: #fecaca;
  }

  .coa-mc-action-btn.danger:hover {
    background: #fee2e2;
    border-color: #fca5a5;
  }

  .coa-mc-action-lbl {
    font-size: 11px;
  }

  /* ── Skeleton shimmer cards ── */
  .coa-mobile-card--skeleton {
    pointer-events: none;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    border-left-color: #e5e7eb;
    background: #ffffff;
  }

  .coa-mc-shimmer {
    border-radius: 6px;
    background: linear-gradient(90deg, #f3f4f6 25%, #e9ecef 50%, #f3f4f6 75%);
    background-size: 200% 100%;
    animation: coa-shimmer 1.4s infinite;
  }

  .coa-mc-shimmer--title {
    height: 14px;
    width: 65%;
  }

  .coa-mc-shimmer--line {
    height: 11px;
    width: 45%;
  }

  @keyframes coa-shimmer {
    0%   { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }

  /* ── Empty state ── */
  .coa-mc-empty {
    text-align: center;
    padding: 36px 16px;
    color: #9ca3af;
  }

  .coa-mc-empty-icon {
    font-size: 36px;
    margin-bottom: 10px;
  }

  .coa-mc-empty-text {
    font-size: 13px;
    font-weight: 500;
  }

  /* ── Utility overrides inside mobile view ── */
  .coa-mobile-cards .coa-dr { color: #16a34a; }
  .coa-mobile-cards .coa-cr { color: #dc2626; }
  .coa-mobile-cards .c-muted { color: #9ca3af; font-weight: 400; }

  /* ───────────────────────────────────────────────────────────
     LEDGER DRAWER – Mobile responsive (375–425px)
     ─────────────────────────────────────────────────────────── */

  /* Ledger drawer: full screen on mobile, must fill viewport height */
  .ldg-panel {
    width: 100% !important;
    max-width: 100vw !important;
    height: 100vh !important;
    border-radius: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    overflow: hidden !important;
  }

  /* Compact 2-col toolbar: FROM/date | TO/date on row1, Refresh | Export on row2 */
  .ldg-toolbar {
    display: grid !important;
    grid-template-columns: auto 1fr auto 1fr !important;
    grid-template-rows: auto auto !important;
    align-items: center !important;
    gap: 6px 8px !important;
    padding: 10px 12px !important;
    flex-wrap: unset !important;
    flex-shrink: 0;
  }

  .ldg-toolbar > span { font-size: 10.5px !important; white-space: nowrap; }

  .ldg-toolbar input[type="date"] {
    width: 100% !important;
    min-width: 0;
    box-sizing: border-box;
    font-size: 12px !important;
    padding: 5px 6px !important;
  }

  /* Refresh and Export buttons span full width on row 2 */
  .ldg-toolbar .b-btn-primary {
    grid-column: 1 / 3 !important;
    margin: 0 !important;
    padding: 7px 10px !important;
    font-size: 12.5px !important;
  }

  .ldg-toolbar .b-btn:not(.b-btn-primary) {
    grid-column: 3 / 5 !important;
    margin-left: 0 !important;
    padding: 7px 10px !important;
    font-size: 12px !important;
    text-align: center;
  }

  /* Scrollable content area */
  .ldg-panel > div[style*="flex:1"] {
    flex: 1 !important;
    overflow-y: auto !important;
    -webkit-overflow-scrolling: touch;
    padding: 12px !important;
  }

  /* Hide desktop ledger table on mobile */
  .ldg-desktop-table {
    display: none !important;
  }

  /* Mobile ledger cards: hidden by default, shown in this breakpoint */
  .ldg-mobile-cards {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 4px 0;
  }

  /* Individual transaction card */
  .ldg-entry-card {
    background: #fff;
    border-radius: 10px;
    border: 1px solid #e5e7eb;
    border-left: 3px solid #e5e7eb;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    overflow: hidden;
  }

  /* Left border by balance direction */
  .ldg-card--dr  { border-left-color: #16a34a; }
  .ldg-card--cr  { border-left-color: #dc2626; }
  .ldg-card--zero{ border-left-color: #d1d5db; }

  /* Row 1: date + voucher type */
  .ldg-card-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px 4px;
    gap: 8px;
  }
  .ldg-card-date {
    font-size: 11.5px;
    color: #6b7280;
    font-weight: 500;
    flex-shrink: 0;
  }
  .ldg-card-vtype {
    font-size: 10.5px;
    font-weight: 600;
    color: #374151;
    background: #f3f4f6;
    border-radius: 20px;
    padding: 1px 8px;
    flex-shrink: 0;
  }

  /* Row 2: voucher no + party */
  .ldg-card-mid {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 2px 12px 8px;
    gap: 8px;
  }
  .ldg-card-voucher {
    font-size: 12.5px;
    font-weight: 700;
    color: #2563eb;
    word-break: break-all;
  }
  .ldg-card-party {
    font-size: 11.5px;
    color: #374151;
    text-align: right;
    flex-shrink: 0;
    max-width: 50%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* Row 3: 3-col Debit | Credit | Balance strip */
  .ldg-card-strip {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    border-top: 1px solid #f3f4f6;
    background: #fafafa;
  }
  .ldg-strip-cell {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 6px 4px;
    gap: 2px;
  }
  .ldg-strip-cell--mid {
    border-left: 1px solid #f3f4f6;
    border-right: 1px solid #f3f4f6;
  }
  .ldg-strip-lbl {
    font-size: 9.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    color: #9ca3af;
  }
  .ldg-strip-val {
    font-size: 12px;
    font-weight: 700;
    color: #374151;
  }
  .ldg-strip-dr { color: #16a34a; }
  .ldg-strip-cr { color: #dc2626; }

  /* Closing balance card */
  .ldg-closing-card {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #f9fafb;
    border: 1.5px solid #e5e7eb;
    border-radius: 10px;
    padding: 10px 14px;
    margin-top: 2px;
  }
  .ldg-closing-lbl {
    font-size: 12px;
    font-weight: 700;
    color: #374151;
  }
  .ldg-closing-val {
    font-size: 15px;
    font-weight: 800;
  }

} /* end @media 375px–425px */
/* ── Trial-balance / balancing card ── */
.coa-balance-row { display:flex; justify-content:flex-end; margin:12px 0 14px; }
.coa-balance-card {
  display:inline-flex; align-items:center; gap:14px;
  background:#fff; border:1px solid #E2E8F0; border-left:3px solid #94a3b8;
  border-radius:10px; padding:9px 16px; font-size:13px;
  box-shadow:0 1px 2px rgba(16,24,40,.04);
}
.coa-balance-card.is-ok  { border-left-color:#16a34a; }
.coa-balance-card.is-off { border-left-color:#dc2626; }
.coa-bal-title { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.5px; color:#64748b; }
.coa-bal-kv { display:inline-flex; align-items:center; gap:6px; }
.coa-bal-kv i { font-style:normal; font-size:11px; font-weight:700; color:#94a3b8; }
.coa-bal-kv b { font-weight:700; color:#1a1a2e; font-variant-numeric:tabular-nums; }
.coa-bal-sep { color:#cbd5e1; font-weight:700; }
.coa-bal-chip { display:inline-flex; align-items:center; gap:5px; padding:3px 10px; border-radius:20px; font-size:11.5px; font-weight:700; }
.coa-bal-chip.ok      { background:#dcfce7; color:#15803d; }
.coa-bal-chip.off     { background:#fee2e2; color:#b91c1c; }
.coa-bal-chip.pending { background:#f1f5f9; color:#64748b; }
@media (max-width: 600px) {
  .coa-balance-row  { justify-content:stretch; }
  .coa-balance-card { width:100%; flex-wrap:wrap; gap:10px; }
  .coa-bal-sep      { display:none; }
}
</style>