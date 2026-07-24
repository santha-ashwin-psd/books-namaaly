<template>
<div>
  <!-- ── FLAT TABLE VIEW (default) ── -->
  <div v-if="!selectedCustomer" class="list-page">

    <div class="sales-toolbar">
      <div class="cust-toolbar-left">
        <div class="sales-pills">
          <button v-for="f in [{k:'all',l:'All'},{k:'active',l:'Active'},{k:'disabled',l:'Disabled'},{k:'dealer',l:'🏪 Dealers'},{k:'distributor',l:'🚚 Distributors'}]"
            :key="f.k" class="sales-pill" :class="{'active': activeFilter===f.k}"
            @click="activeFilter=f.k">
            {{f.l}}
            <span class="sales-pill-count" :class="activeFilter===f.k?'':'zb-pc-muted'">{{counts[f.k]}}</span>
          </button>
        </div>
      </div>
      <div class="cust-toolbar-right">
        <select v-if="customerGroups.length" class="sales-select" v-model="groupFilter" title="Filter by customer group">
          <option value="">All Groups</option>
          <option v-for="g in customerGroups" :key="g" :value="g">{{ g }}</option>
        </select>
        <select v-if="territories.length" class="sales-select" v-model="territoryFilter" title="Filter by territory">
          <option value="">All Territories</option>
          <option v-for="t in territories" :key="t" :value="t">{{ t }}</option>
        </select>
        <div class="sales-search">
          <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
          <input v-model="search" placeholder="Search customers…" class="sales-search-input" autocomplete="off"/>
        </div>
        <button class="sales-btn-ghost view-toggle-btn" @click="viewMode=viewMode==='table'?'grid':'table'" :title="viewMode==='table'?'Grid View':'List View'"><span v-html="icon(viewMode==='table'?'grid':'file',14)"></span></button>
        <button class="sales-btn-ghost" @click="triggerImport" title="Import customers from CSV"><span v-html="icon('upload',13)"></span> Import</button>
        <button class="sales-btn-ghost" @click="exportCSV" title="Export CSV"><span v-html="icon('download',13)"></span> Export</button>
        <button class="sales-btn-ghost" @click="load" title="Refresh"><span v-html="icon('refresh',13)"></span> Refresh</button>
        <button class="sales-btn-primary" :disabled="!$canWrite('customers')" :title="!$canWrite('customers') ? 'Read-only access' : ''" @click="openAdd"><span v-html="icon('plus',13)"></span> New Customer</button>
        <input ref="importInput" type="file" accept=".csv,text/csv" style="display:none" @change="importCSV" />
      </div>
    </div>

    <!-- ── KPI Cards ── -->
    <div class="bk-kpi-grid bk-kpi-grid-4" style="margin-bottom:18px">
      <div v-for="kpi in custKpiCards" :key="kpi.key" class="bk-kpi-card" :class="kpi.route?'clickable':''">
        <div class="bk-kpi-inner">
          <div class="bk-kpi-icon" :style="{ background: kpi.iconBg }"><span v-html="kpi.icon"></span></div>
          <div class="bk-kpi-body">
            <div class="bk-kpi-label">{{ kpi.label }}</div>
            <div class="bk-kpi-value" :class="kpi.valueClass">
              <template v-if="loading"><div class="b-shimmer" style="width:64px;height:22px;margin-top:2px;border-radius:4px"></div></template>
              <template v-else>{{ kpi.format === 'currency' ? fmt(kpi.value) : kpi.value }}</template>
            </div>
            <div class="bk-kpi-trend bk-trend-neutral">{{ kpi.sub || '—' }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Bulk action bar -->
    <div v-if="selectedRows.size" class="inv-bulk-bar" style="margin: 0 24px 12px">
      <span class="inv-bulk-count">{{ selectedRows.size }} selected</span>
      <button class="inv-bulk-btn" @click="bulkSetDisabled(false)" :disabled="bulkBusy">Enable</button>
      <button class="inv-bulk-btn inv-bulk-danger" @click="bulkSetDisabled(true)" :disabled="bulkBusy">Disable</button>
      <button class="inv-bulk-btn" @click="exportCSV" :disabled="bulkBusy">
        <span v-html="icon('download',13)"></span> Export CSV
      </button>
      <button class="inv-bulk-btn" @click="bulkEmail" :disabled="bulkBusy">
        <span v-html="icon('mail',13)"></span> Send Email
      </button>
      <button class="inv-bulk-clear" @click="clearSelection">✕ Clear</button>
    </div>

    <div class="inv-table-wrap">
      <!-- TABLE MODE -->
      <div v-if="viewMode==='table'" class="inv-table-wrap">
        <table class="inv-table cus-desktop-table">
          <thead>
            <tr>
              <th class="vt-th vt-th-check">
                <input type="checkbox" class="vt-checkbox"
                  :checked="filtered.length>0 && filtered.every(c=>selectedRows.has(c.name))"
                  @change="e=>e.target.checked ? selectedRows=new Set(filtered.map(c=>c.name)) : clearSelection()" />
              </th>
              <th class="vt-th">Customer Name</th>
              <th class="vt-th">Type</th>
              <th class="vt-th">Group / Territory</th>
              <th class="vt-th">GSTIN</th>
              <th class="vt-th vt-th-num">Outstanding</th>
              <th class="vt-th">Last Invoice</th>
              <th class="vt-th">Mobile</th>
              <th class="vt-th">Status</th>
              <th class="vt-th vt-th-actions">Actions</th>
            </tr>
          </thead>
          <tbody>
            <template v-if="loading">
              <tr v-for="n in 6" :key="n" class="vt-row-shimmer">
                <td colspan="10"><div class="shimmer" style="height:12px;border-radius:3px;width:65%"></div></td>
              </tr>
            </template>
            <tr v-else-if="!filtered.length">
              <td colspan="10" class="vt-empty">
                <div class="vt-empty-icon">
                  <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" stroke-width="1.3"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                </div>
                <div class="vt-empty-title">{{search ? 'No results found' : 'No customers yet'}}</div>
                <div class="vt-empty-sub">{{search ? 'Try adjusting your search or filter' : 'Add your first customer to get started'}}</div>
                <button v-if="!search" class="nim-btn nim-btn-primary" :disabled="!$canWrite('customers')" :title="!$canWrite('customers') ? 'Read-only access' : ''" style="margin-top:14px" @click="openAdd"><span v-html="icon('plus',13)"></span> New Customer</button>
              </td>
            </tr>
            <tr v-else v-for="c in filtered" :key="c.name"
              class="inv-row"
              :class="[c.disabled ? 'vt-row-disabled' : '', selectedRows.has(c.name) ? 'vt-row-selected' : '']"
              @click="selectCustomer(c)">
              <td class="vt-td vt-td-check" @click.stop>
                <input type="checkbox" class="vt-checkbox" :checked="selectedRows.has(c.name)" @change="toggleRow(c.name)" />
              </td>
              <td class="vt-td vt-td-customer">
                <div class="vt-vendor-cell">
                  <div class="vt-avatar" :class="c.disabled ? 'vt-avatar-disabled' : ''">{{custInitials(c.customer_name)}}</div>
                  <div>
                    <div class="vt-vendor-name inv-customer">{{c.customer_name}}</div>
                    <div class="vt-vendor-id">{{c.name}}</div>
                  </div>
                </div>
              </td>
              <td class="vt-td">
                <span class="vt-badge"
                  :style="CTYPE_META[c.customer_type] ? { background: CTYPE_META[c.customer_type].bg, color: CTYPE_META[c.customer_type].text, border: 'none' } : {}">
                  {{ CTYPE_META[c.customer_type]?.icon || '' }} {{c.customer_type||'—'}}
                </span>
              </td>
              <td class="vt-td vt-td-secondary">
                <div v-if="c.customer_group" style="font-size:12px;font-weight:600;color:#374151">{{ c.customer_group }}</div>
                <div v-if="c.territory" style="font-size:11px;color:#9ca3af;margin-top:2px">📍 {{ c.territory }}</div>
                <span v-if="!c.customer_group && !c.territory">—</span>
              </td>
              <td class="vt-td vt-td-mono">
                <span v-if="c.tax_id">{{c.tax_id}}</span>
                <span v-else class="vt-badge vt-badge-amber">Unregistered</span>
              </td>
              <td class="vt-td vt-td-num">
                <span :class="(c.outstanding||0)>0 ? 'vt-amount-due' : 'vt-amount-nil'">
                  {{ (c.outstanding||0)>0 ? fmt(c.outstanding) : '—' }}
                </span>
              </td>
              <td class="vt-td vt-td-secondary">
                <template v-if="lastInvoiceByCust[c.name]">
                  <div class="vt-lastinv-ref">{{ lastInvoiceByCust[c.name].name }}</div>
                  <div class="vt-lastinv-date">{{ fmtDate(lastInvoiceByCust[c.name].date) }} · {{ fmt(lastInvoiceByCust[c.name].amount) }}</div>
                </template>
                <span v-else>—</span>
              </td>
              <td class="vt-td vt-td-secondary">{{c.mobile_no||'—'}}</td>
              <td class="vt-td">
                <span class="inv-status-badge" :class="c.disabled ? 'vt-badge-red' : 'vt-badge-green'">
                  <span class="vt-badge-dot"></span>{{c.disabled ? 'Disabled' : 'Active'}}
                </span>
              </td>
              <td class="vt-td vt-td-actions" @click.stop>
                <div class="vt-actions">
                  <button class="inv-act-btn vt-act-edit" @click="openEdit(c.name)" title="Edit"><span v-html="icon('edit',13)"></span></button>
                  <button class="inv-act-btn vt-act-del" @click="confirmDelete(c)" title="Delete"><span v-html="icon('trash',13)"></span></button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Mobile cards (shown at ≤768px) -->
        <div class="cus-mobile-cards">
          <template v-if="loading">
            <div v-for="n in 5" :key="n" class="cus-mobile-card cus-mc--skeleton">
              <div class="cus-mc-shimmer" style="height:13px;width:55%;margin-bottom:8px"></div>
              <div class="cus-mc-shimmer" style="height:11px;width:40%"></div>
            </div>
          </template>
          <div v-else-if="!filtered.length" class="cus-mc-empty">
            <div style="font-size:32px;margin-bottom:8px">👤</div>
            <div>{{ search ? 'No results found' : 'No customers yet' }}</div>
          </div>
          <template v-else>
            <div v-for="c in filtered" :key="c.name" class="cus-mobile-card" @click="selectCustomer(c)">
              <div class="cus-mc-top">
                <div class="cus-mc-name">{{ c.customer_name }}</div>
                <span class="inv-status-badge" :class="c.disabled ? 'vt-badge-red' : 'vt-badge-green'">{{ c.disabled ? 'Disabled' : 'Active' }}</span>
              </div>
              <div class="cus-mc-meta">
                <span>{{ c.mobile_no || '—' }}</span>
              </div>
              <div class="cus-mc-meta">
                <span :style="(c.outstanding||0)>0 ? 'color:#dc2626;font-weight:600' : ''">
                  {{ (c.outstanding||0)>0 ? fmt(c.outstanding)+' due' : 'No balance' }}
                </span>
                <span>{{ lastInvoiceByCust[c.name] ? 'Last: '+lastInvoiceByCust[c.name].name : '—' }}</span>
              </div>
              <div class="cus-mc-footer">
                <button class="cus-mc-btn" @click.stop="openEdit(c.name)">Edit</button>
                <button class="cus-mc-btn cus-mc-danger" @click.stop="confirmDelete(c)">Delete</button>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- GRID MODE -->
      <div v-else style="display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px;padding:24px 24px 24px">
        <template v-if="loading">
          <div v-for="n in 8" :key="n" class="b-card" style="padding:16px">
            <div style="display:flex;gap:10px;margin-bottom:12px">
              <div class="b-shimmer" style="width:40px;height:40px;border-radius:50%;flex-shrink:0"></div>
              <div style="flex:1">
                <div class="b-shimmer" style="height:13px;width:70%;border-radius:4px;margin-bottom:7px"></div>
                <div class="b-shimmer" style="height:11px;width:45%;border-radius:4px"></div>
              </div>
            </div>
            <div class="b-shimmer" style="height:11px;width:55%;border-radius:4px"></div>
          </div>
        </template>
        <div v-else-if="!filtered.length" style="grid-column:1/-1;text-align:center;padding:40px 16px;color:#9ca3af;font-size:13px">
          <div style="font-size:32px;margin-bottom:8px">👤</div>
          <div>{{ search ? 'No results found' : 'No customers yet' }}</div>
          <button v-if="!search" class="nim-btn nim-btn-primary" :disabled="!$canWrite('customers')" :title="!$canWrite('customers') ? 'Read-only access' : ''" style="margin-top:14px" @click="openAdd"><span v-html="icon('plus',13)"></span> New Customer</button>
        </div>
        <template v-else>
          <div v-for="c in filtered" :key="c.name"
            class="b-card b-card-body"
            style="cursor:pointer;padding:16px;display:flex;flex-direction:column;gap:10px"
            @click="selectCustomer(c)">
            <div style="display:flex;align-items:flex-start;gap:10px">
              <div class="vt-avatar" :class="c.disabled ? 'vt-avatar-disabled' : ''" style="width:40px;height:40px;font-size:14px;flex-shrink:0">
                {{custInitials(c.customer_name)}}
              </div>
              <div style="flex:1;min-width:0">
                <div style="font-size:13.5px;font-weight:700;color:#1a1d23;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{c.customer_name}}</div>
                <div style="font-size:11.5px;color:#9ca3af">{{c.name}}</div>
              </div>
              <span class="inv-status-badge" :class="c.disabled ? 'vt-badge-red' : 'vt-badge-green'" style="flex-shrink:0">
                <span class="vt-badge-dot"></span>{{c.disabled ? 'Disabled' : 'Active'}}
              </span>
            </div>
            <div style="font-size:12px;color:#6b7280;display:flex;justify-content:flex-end;align-items:center">
              <span class="vt-badge" :class="c.customer_type==='Company' ? 'vt-badge-blue' : 'vt-badge-gray'">{{c.customer_type||'—'}}</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;border-top:1px solid #f3f4f6;padding-top:10px">
              <span style="font-size:12px;color:#6b7280">{{c.mobile_no||'—'}}</span>
              <div style="display:flex;gap:6px">
                <button class="inv-act-btn vt-act-edit" @click.stop="openEdit(c.name)" title="Edit"><span v-html="icon('edit',13)"></span></button>
                <button class="inv-act-btn vt-act-del" @click.stop="confirmDelete(c)" title="Delete"><span v-html="icon('trash',13)"></span></button>
              </div>
            </div>
          </div>
        </template>
      </div>

      <div v-if="!loading && filtered.length" class="vt-footer">
        <span>Showing <strong>{{filtered.length}}</strong> of <strong>{{list.length}}</strong> customers</span>
      </div>
    </div>
  </div>

  <!-- ── TWO-PANEL DETAIL VIEW (when customer selected) ── -->
  <div v-else class="zb-master-detail" style="height:calc(100vh - 56px)">
    <!-- Left panel: customer list -->
    <div class="zb-list-pane" style="width:320px;min-width:260px;border-right:1px solid #e4e8f0;display:flex;flex-direction:column;overflow:hidden">
      <div style="padding:16px 16px 10px;border-bottom:1px solid #f0f2f5;flex-shrink:0">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
          <span style="font-size:14px;font-weight:700;color:#111827">Customers</span>
          <button class="nim-btn nim-btn-primary" :disabled="!$canWrite('customers')" :title="!$canWrite('customers') ? 'Read-only access' : ''" style="padding:5px 10px;font-size:12px" @click="openAdd">
            <span v-html="icon('plus',12)"></span> New Customer
          </button>
        </div>
        <div class="sales-search" style="width:100%">
          <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
          <input v-model="search" placeholder="Search customers…" class="sales-search-input" autocomplete="off"/>
        </div>
        <div style="display:flex;gap:4px;margin-top:8px;flex-wrap:wrap">
          <button class="sales-pill" :class="{'active':activeFilter==='all'}" @click="activeFilter='all'" style="font-size:11.5px">All <span class="sales-pill-count" :class="activeFilter==='all'?'':'zb-pc-muted'">{{counts.all}}</span></button>
          <button class="sales-pill" :class="{'active':activeFilter==='active'}" @click="activeFilter='active'" style="font-size:11.5px">Active <span class="sales-pill-count" :class="activeFilter==='active'?'':'zb-pc-muted'">{{counts.active}}</span></button>
          <button class="sales-pill" :class="{'active':activeFilter==='disabled'}" @click="activeFilter='disabled'" style="font-size:11.5px">Disabled <span class="sales-pill-count" :class="activeFilter==='disabled'?'':'zb-pc-muted'">{{counts.disabled}}</span></button>
        </div>
      </div>
      <div style="flex:1;overflow-y:auto">
        <template v-if="loading">
          <div v-for="n in 6" :key="n" style="padding:14px 16px;border-bottom:1px solid #f0f2f5">
            <div class="b-shimmer" style="height:12px;border-radius:4px;width:70%;margin-bottom:6px"></div>
            <div class="b-shimmer" style="height:10px;border-radius:4px;width:40%"></div>
          </div>
        </template>
        <div v-else-if="!filtered.length" style="text-align:center;padding:40px 16px">
          <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" stroke-width="1.5" style="margin:0 auto 10px;display:block"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
          <div style="font-size:13px;font-weight:600;color:#374151;margin-bottom:4px">{{search?'No matches':'No customers yet'}}</div>
          <div style="font-size:12px;color:#9ca3af">{{search?'Try different keywords':'Add your first customer'}}</div>
          <button v-if="!search" class="nim-btn nim-btn-primary" :disabled="!$canWrite('customers')" :title="!$canWrite('customers') ? 'Read-only access' : ''" style="margin-top:12px;font-size:12px" @click="openAdd">New Customer</button>
        </div>
        <div v-else v-for="c in filtered" :key="c.name"
          @click="selectCustomer(c)"
          :style="{
            padding:'12px 16px',
            borderBottom:'1px solid #f0f2f5',
            cursor:'pointer',
            background: selectedCustomer && selectedCustomer.name===c.name ? '#FFF7ED' : 'transparent',
            borderLeft: selectedCustomer && selectedCustomer.name===c.name ? '3px solid #E67700' : '3px solid transparent',
            transition:'background 0.15s',
          }">
          <div style="display:flex;align-items:center;gap:10px">
            <div :style="{
              width:'34px',height:'34px',borderRadius:'50%',flexShrink:0,
              display:'flex',alignItems:'center',justifyContent:'center',
              fontWeight:700,fontSize:'12px',color:'#fff',
              background: c.disabled ? '#9CA3AF' : 'linear-gradient(135deg,#16a34a,#15803d)'
            }">{{custInitials(c.customer_name)}}</div>
            <div style="flex:1;min-width:0">
              <div style="font-size:13px;font-weight:700;color:#111827;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                {{c.customer_name}}
              </div>
              <div style="font-size:11.5px;color:#6B7280;margin-top:2px">
                <span :style="c.outstanding>0?'color:#E67700;font-weight:600':''">{{ fmt(c.outstanding || 0) }}</span> outstanding
                <span v-if="c.disabled" style="margin-left:6px;font-size:10px;font-weight:600;color:#6B7280;background:#F3F4F6;padding:1px 5px;border-radius:10px">Disabled</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-if="!loading && filtered.length" style="padding:8px 16px;border-top:1px solid #f0f2f5;font-size:11.5px;color:#9ca3af;display:flex;justify-content:space-between;flex-shrink:0">
        <span>{{filtered.length}} of {{list.length}} customers</span>
        <button @click="load" style="background:none;border:none;cursor:pointer;color:#6B7280;font-size:11.5px;display:flex;align-items:center;gap:3px"><span v-html="icon('refresh',11)"></span> Refresh</button>
      </div>
    </div>

    <!-- Right panel -->
    <div style="flex:1;overflow-y:auto;background:#F9FAFB">
      <div style="max-width:960px;margin:0 auto;padding:24px">

        <!-- Header -->
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
          <div style="display:flex;align-items:center;gap:12px">
            <div :style="{
              width:'46px',height:'46px',borderRadius:'50%',flexShrink:0,
              display:'flex',alignItems:'center',justifyContent:'center',
              fontWeight:700,fontSize:'16px',color:'#fff',
              background: selectedCustomer.disabled ? '#9CA3AF' : 'linear-gradient(135deg,#16a34a,#15803d)'
            }">{{custInitials(selectedCustomer.customer_name)}}</div>
            <div>
              <div style="font-size:19px;font-weight:700;color:#111827">{{selectedCustomer.customer_name}}</div>
              <div style="font-size:12px;color:#6B7280">{{selectedCustomer.name}}</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px">
            <button class="nim-btn" style="background:#fff;color:#374151;border:1px solid #E5E7EB;font-size:13px" @click="openEdit(selectedCustomer.name)">
              <span v-html="icon('edit',13)"></span> Edit
            </button>
            <button class="nim-btn" style="background:#fff;color:#374151;border:1px solid #E5E7EB;width:32px;height:32px;padding:0;display:grid;place-items:center" @click="closeCustomer" title="Close">
              <span v-html="icon('x',14)"></span>
            </button>
          </div>
        </div>

        <!-- Tabs -->
        <div style="display:flex;border-bottom:2px solid #E5E7EB;margin-bottom:22px;gap:0">
          <button @click="activeCustomerTab='overview'"
            :style="{padding:'8px 16px',fontSize:'13.5px',fontWeight:600,border:'none',background:'none',cursor:'pointer',
              color:activeCustomerTab==='overview'?'#16a34a':'#6B7280',
              borderBottom:activeCustomerTab==='overview'?'2px solid #16a34a':'2px solid transparent',marginBottom:'-2px'}">
            Overview
          </button>
          <button @click="activeCustomerTab='transactions'"
            :style="{padding:'8px 16px',fontSize:'13.5px',fontWeight:600,border:'none',background:'none',cursor:'pointer',display:'flex',
              color:activeCustomerTab==='transactions'?'#16a34a':'#6B7280',
              borderBottom:activeCustomerTab==='transactions'?'2px solid #16a34a':'2px solid transparent',marginBottom:'-2px'}">
            Transactions
            <span v-if="custTxnsActive.length" style="background:#16a34a;color:#fff;padding:1px 7px;border-radius:999px;font-size:11px;margin-left:4px">{{custTxnsActive.length}}</span>
          </button>
          <button @click="activeCustomerTab='statement'"
            :style="{padding:'8px 16px',fontSize:'13.5px',fontWeight:600,border:'none',background:'none',cursor:'pointer',
              color:activeCustomerTab==='statement'?'#16a34a':'#6B7280',
              borderBottom:activeCustomerTab==='statement'?'2px solid #16a34a':'2px solid transparent',marginBottom:'-2px'}">
            Statement
          </button>
        </div>
        <!-- Overview tab -->
        <div v-if="activeCustomerTab==='overview'" class="cus-overview-cols" style="display:flex;gap:20px;align-items:flex-start">

          <!-- Left column ~55% -->
          <div style="flex:0 0 55%;min-width:0;display:flex;flex-direction:column;gap:14px">

            <div style="background:#fff;border:1px solid #E5E7EB;border-radius:10px;padding:18px">
              <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;padding-bottom:14px;border-bottom:1px solid #F3F4F6">
                <div :style="{
                  width:'44px',height:'44px',borderRadius:'50%',flexShrink:0,
                  display:'flex',alignItems:'center',justifyContent:'center',
                  fontWeight:700,fontSize:'16px',color:'#fff',
                  background: selectedCustomer.disabled ? '#9CA3AF' : 'linear-gradient(135deg,#16a34a,#15803d)'
                }">{{custInitials(selectedCustomer.customer_name)}}</div>
                <div>
                  <div style="font-size:14px;font-weight:700;color:#111827">{{ selectedCustomer.salutation ? selectedCustomer.salutation + ' ' : '' }}{{selectedCustomer.customer_name}}</div>
                  <div v-if="selectedCustomer.email_id" style="font-size:12px;color:#6B7280;margin-top:2px">{{selectedCustomer.email_id}}</div>
                </div>
                <div style="margin-left:auto;display:none;">
                  <a href="#" style="font-size:12px;color:#16a34a;text-decoration:none">Invite to Portal</a>
                </div>
              </div>
              <div style="display:flex;flex-direction:column;gap:7px">
                <div v-if="selectedCustomer.mobile_no" style="display:flex;align-items:center;gap:8px;font-size:12.5px;color:#374151">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#9CA3AF" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12 19.79 19.79 0 0 1 1.63 3.18 2 2 0 0 1 3.6 1h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.6A16 16 0 0 0 15.4 16.1l.97-.97a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
                  <span>{{selectedCustomer.mobile_no}}</span>
                </div>
                <div v-else style="display:flex;align-items:center;gap:8px;font-size:12.5px;color:#9CA3AF">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#D1D5DB" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12 19.79 19.79 0 0 1 1.63 3.18 2 2 0 0 1 3.6 1h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.6A16 16 0 0 0 15.4 16.1l.97-.97a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
                  <span>No phone number</span>
                </div>
              </div>
            </div>

            <div style="background:#fff;border:1px solid #E5E7EB;border-radius:10px;overflow:hidden">
              <div style="padding:12px 16px;display:flex;justify-content:space-between;align-items:center;cursor:pointer;user-select:none" :style="!custSectionCollapsed.address?'border-bottom:1px solid #F3F4F6':''" @click="custSectionCollapsed.address=!custSectionCollapsed.address">
                <span style="font-size:11px;font-weight:700;color:#9CA3AF;letter-spacing:0.8px">ADDRESS</span>
                <svg :style="{transition:'transform 0.2s',transform:custSectionCollapsed.address?'rotate(-90deg)':'rotate(0deg)'}" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#9CA3AF" stroke-width="2.5" stroke-linecap="round"><polyline points="18 15 12 9 6 15"/></svg>
              </div>
              <div v-show="!custSectionCollapsed.address" style="padding:14px 16px">
                <AddressManager
                  v-if="selectedCustomer.name"
                  :partyDoctype="'Customer'"
                  :partyName="selectedCustomer.name"
                  :readonly="true"
                />
              </div>
            </div>

            

          </div>

          <!-- Right column ~45% -->
          <div style="flex:1;min-width:0;display:flex;flex-direction:column;gap:14px">

            <div style="background:#fff;border:1px solid #E5E7EB;border-radius:10px;padding:16px">
              <div style="font-size:11.5px;color:#6B7280;margin-bottom:4px">Payment due period</div>
              <div style="font-size:14px;font-weight:600;color:#111827">{{selectedCustomer.payment_terms||'Due on Receipt'}}</div>
            </div>

            <div style="background:#fff;border:1px solid #E5E7EB;border-radius:10px;overflow:hidden">
              <div style="padding:12px 16px;border-bottom:1px solid #F3F4F6">
                <span style="font-size:11px;font-weight:700;color:#9CA3AF;letter-spacing:0.8px">RECEIVABLES</span>
              </div>
              <table class="cus-recv-table" style="width:100%;border-collapse:collapse;table-layout:fixed">
                <thead>
                  <tr style="border-bottom:1px solid #F3F4F6">
                    <th style="width:28%;text-align:left;font-size:10.5px;font-weight:600;color:#9CA3AF;padding:8px 16px;white-space:normal;word-break:break-word;line-height:1.3">CURRENCY</th>
                    <th style="width:36%;text-align:right;font-size:10.5px;font-weight:600;color:#9CA3AF;padding:8px 12px;white-space:normal;word-break:break-word;line-height:1.3">OUTSTANDING RECEIVABLES</th>
                    <th style="width:36%;text-align:right;font-size:10.5px;font-weight:600;color:#9CA3AF;padding:8px 16px;white-space:normal;word-break:break-word;line-height:1.3">UNUSED CREDITS</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td style="font-size:13px;font-weight:600;color:#374151;padding:10px 16px;overflow:hidden;text-overflow:ellipsis">{{ selectedCustomer.default_currency || "INR" }}</td>
                    <td style="font-size:13px;font-weight:600;text-align:right;padding:10px 12px;overflow:hidden;text-overflow:ellipsis" :style="{color: selectedCustomer.outstanding>0?'#dc2626':'#111827'}">{{fmt(selectedCustomer.outstanding||0)}}</td>
                    <td style="font-size:13px;font-weight:600;color:#059669;text-align:right;padding:10px 16px;overflow:hidden;text-overflow:ellipsis">{{ fmt(selectedCustomer.unused_credits||0) }}</td>
                  </tr>
                </tbody>
              </table>
              <div style="padding:10px 16px ;display:none;">
                <a href="#" style="font-size:12.5px;color:#2563EB;text-decoration:none">Enter Opening Balance</a>
              </div>
            </div>

            <div v-if="obInfo.has_opening_je" style="background:#fff;border:1px solid #E5E7EB;border-radius:10px;padding:16px;display:flex;align-items:center;justify-content:space-between">
              <div>
                <div style="font-size:11px;font-weight:700;color:#9CA3AF;letter-spacing:0.8px">OPENING BALANCE</div>
                <div style="font-size:16px;font-weight:700;margin-top:4px" :style="{color: obInfo.outstanding>0?'#dc2626':'#16a34a'}">
                  {{ fmt(obInfo.outstanding) }}
                  <span v-if="obInfo.outstanding<=0" style="font-size:11px;font-weight:700;padding:1px 8px;border-radius:12px;background:#dcfce7;color:#16a34a;margin-left:6px">Paid</span>
                </div>
              </div>
              <button v-if="obInfo.outstanding>0" class="nim-btn nim-btn-primary" style="font-size:13px" @click="openPayModal">
                <span v-html="icon('plus',13)"></span> Pay
              </button>
            </div>
            <div style="background:#fff;border:1px solid #E5E7EB;border-radius:10px;overflow:hidden">
              <div style="padding:12px 16px;display:flex;justify-content:space-between;align-items:center;cursor:pointer;user-select:none" :style="!custSectionCollapsed.otherDetails?'border-bottom:1px solid #F3F4F6':''" @click="custSectionCollapsed.otherDetails=!custSectionCollapsed.otherDetails">
                <span style="font-size:11px;font-weight:700;color:#9CA3AF;letter-spacing:0.8px">OTHER DETAILS</span>
                <svg :style="{transition:'transform 0.2s',transform:custSectionCollapsed.otherDetails?'rotate(-90deg)':'rotate(0deg)'}" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#9CA3AF" stroke-width="2.5" stroke-linecap="round"><polyline points="18 15 12 9 6 15"/></svg>
              </div>
              <div v-show="!custSectionCollapsed.otherDetails" style="padding:14px 16px;display:flex;flex-direction:column;gap:10px">
                <div style="display:flex;justify-content:space-between;font-size:12.5px">
                  <span style="color:#6B7280">Default Currency</span>
                  <span style="font-weight:600;color:#111827">{{selectedCustomer.default_currency||'INR'}}</span>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:12.5px;align-items:center">
                  <span style="color:#6B7280">Portal Status</span>
                  <span style="font-size:11px;font-weight:700;padding:2px 8px;border-radius:20px;background:#F3F4F6;color:#6B7280">● Disabled</span>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:12.5px">
                  <span style="color:#6B7280">Customer Type</span>
                  <span style="font-weight:600;color:#111827">{{selectedCustomer.customer_type||'Company'}}</span>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:12.5px">
                  <span style="color:#6B7280">GSTIN / Tax ID</span>
                  <span v-if="selectedCustomer.tax_id" style="font-weight:600;color:#111827">{{selectedCustomer.tax_id}}</span>
                  <span v-else style="font-size:11px;font-weight:700;padding:1px 8px;border-radius:12px;background:#fff7ed;color:#b45309">Unregistered</span>
                </div>
                <div v-if="selectedCustomer.tds_applicable" style="display:flex;justify-content:space-between;font-size:12.5px">
                  <span style="color:#6B7280">TDS</span>
                  <span style="font-weight:600;color:#111827">Applicable{{ selectedCustomer.tds_section ? ' · '+selectedCustomer.tds_section : '' }}</span>
                </div>
              </div>
            </div>

            <div style="padding:4px 0">
              <button @click="confirmDelete(selectedCustomer)" style="background:none;border:none;cursor:pointer;color:#DC2626;font-size:12.5px;display:flex;align-items:center;gap:6px">
                <span v-html="icon('trash',13)"></span> Delete Customer
              </button>
            </div>

          </div>
        </div>

        <!-- Transactions tab -->
        <div v-else-if="activeCustomerTab==='transactions'">
          <!-- Skeleton loader -->
          <div v-if="custTxnsLoading" class="cus-txn-skeleton">
            <div v-for="n in 5" :key="n" class="cus-txn-sk-row">
              <div class="cus-sk-pill"></div>
              <div class="cus-sk-line cus-sk-line-md"></div>
              <div class="cus-sk-line cus-sk-line-sm"></div>
              <div class="cus-sk-line cus-sk-line-sm" style="margin-left:auto"></div>
            </div>
          </div>
          <div v-else-if="!custTxnsActive.length" style="background:#fff;border:1px solid #E5E7EB;border-radius:10px;padding:24px;text-align:center;color:#9CA3AF">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#D1D5DB" stroke-width="1.5" style="margin:0 auto 12px;display:block"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            <div style="font-size:14px;font-weight:600;color:#374151;margin-bottom:6px">No transactions yet</div>
            <div style="font-size:12.5px;color:#9CA3AF">Invoices and payments for {{selectedCustomer.customer_name}} will appear here.</div>
          </div>
          <div v-else class="cus-txn-wrap" style="background:#fff;border:1px solid #E5E7EB;border-radius:10px;overflow:scroll">
            <div class="cus-txn-desktop">
              <div style="display:grid;grid-template-columns:100px 160px 100px 130px 130px auto;gap:8px;background:#F9FAFB;padding:10px 14px;font-size:11px;font-weight:700;color:#6B7280;text-transform:uppercase;border-bottom:1px solid #E5E7EB;min-width:560px">
                <span>Type</span><span>Reference</span><span>Date</span><span style="text-align:right">Amount</span><span style="text-align:right">Outstanding</span>
              </div>
              <div v-for="t in custTxnsVisible" :key="t.type+'-'+t.name"
                style="display:grid;grid-template-columns:100px 160px 100px 130px 130px auto;gap:8px;padding:9px 14px;border-bottom:1px solid #F3F4F6;font-size:12.5px;align-items:center;min-width:560px">
                <span :style="{
                  fontSize:'10.5px',fontWeight:700,padding:'2px 8px',borderRadius:'10px',display:'inline-block',width:'fit-content',
                  background: t.type==='Invoice' ? '#DBEAFE' : t.type==='Payment' ? '#D1FAE5' : '#FEE2E2',
                  color: t.type==='Invoice' ? '#1E40AF' : t.type==='Payment' ? '#059669' : '#991B1B'
                }">{{t.type}}</span>
                <span style="color:#2563EB;font-weight:600">{{t.name}}</span>
                <span style="color:#6B7280">{{fmtDate(t.date)}}</span>
                <span style="text-align:right;font-weight:600" :style="{color: t.amount<0 ? '#059669' : '#374151'}">{{fmt(Math.abs(t.amount))}}</span>
                <span style="text-align:right;" :style="{color: t.outstanding>0 ? '#dc2626' : '#9CA3AF'}">{{t.outstanding>0?fmt(t.outstanding):''}}</span>
              </div>
            </div>

            <!-- Mobile card view -->
            <div class="cus-txn-mobile-cards">
              <div v-for="t in custTxnsVisible" :key="'mc-'+t.type+'-'+t.name" class="cus-txn-mc">
                <div class="cus-txn-mc-top">
                  <span class="cus-txn-mc-badge" :style="{
                    background: t.type==='Invoice' ? '#DBEAFE' : t.type==='Payment' ? '#D1FAE5' : '#FEE2E2',
                    color: t.type==='Invoice' ? '#1E40AF' : t.type==='Payment' ? '#059669' : '#991B1B'
                  }">{{t.type}}</span>
                  <span class="cus-txn-mc-amount" :style="{color: t.amount<0 ? '#059669' : '#374151'}">{{fmt(Math.abs(t.amount))}}</span>
                </div>
                <div class="cus-txn-mc-mid">
                  <span class="cus-txn-mc-ref">{{t.name}}</span>
                  <span class="cus-txn-mc-date">{{fmtDate(t.date)}}</span>
                </div>
                <div v-if="t.outstanding>0" class="cus-txn-mc-outstanding">
                  Outstanding: <strong>{{fmt(t.outstanding)}}</strong>
                </div>
              </div>
            </div>
          </div>

          <!-- Load More — transactions -->
          <div v-if="custTxnsHasMore" class="cus-load-more-wrap">
            <span class="cus-load-more-count">Showing {{custTxnsVisible.length}} of {{custTxnsActive.length}}</span>
            <button class="cus-load-more-btn" @click="txnPage++">Load more</button>
          </div>
          <div v-else-if="custTxnsActive.length" class="cus-load-more-wrap cus-load-more-end">
            All {{custTxnsActive.length}} transactions shown
          </div>
        </div>

        <!-- Statement tab -->
        <div v-else-if="activeCustomerTab==='statement'">
          <div style="background:#fff;border:1px solid #E5E7EB;border-radius:10px;padding:14px 18px;display:flex;align-items:center;gap:12px;margin-bottom:14px;flex-wrap:wrap">
            <button class="nim-btn" style="border:1px solid #E5E7EB" @click="stmtLoaded=false; loadStatement()" :disabled="stmtLoading">
              <span v-if="stmtLoading">Loading…</span><span v-else>↺ Refresh</span>
            </button>
            <div style="margin-left:auto;display:flex;gap:8px">
              <button v-if="stmt && stmt.email" class="nim-btn" style="border:1px solid #E5E7EB" @click="sendStatement" :disabled="sendingStmt">
                {{sendingStmt ? 'Sending…' : '📧 Send Statement'}}
              </button>
            </div>
          </div>
          <!-- Skeleton loader -->
          <div v-if="stmtLoading" class="cus-stmt-skeleton">
            <div class="cus-stmt-sk-kpis">
              <div v-for="n in 3" :key="n" class="cus-stmt-sk-kpi">
                <div class="cus-sk-line cus-sk-line-sm" style="margin-bottom:8px"></div>
                <div class="cus-sk-line cus-sk-line-lg"></div>
              </div>
            </div>
            <div class="cus-txn-skeleton" style="margin-top:0">
              <div v-for="n in 4" :key="n" class="cus-txn-sk-row">
                <div class="cus-sk-line cus-sk-line-md"></div>
                <div class="cus-sk-line cus-sk-line-sm"></div>
                <div class="cus-sk-line cus-sk-line-sm" style="margin-left:auto"></div>
              </div>
            </div>
          </div>
          <div v-else-if="!stmt" style="background:#fff;border:1px solid #E5E7EB;border-radius:10px;padding:40px;text-align:center;color:#9CA3AF">
            <div style="font-size:32px;margin-bottom:8px">📄</div>
            <div style="font-size:13.5px;font-weight:600;color:#374151;margin-bottom:4px">No statement loaded</div>
            <button class="nim-btn nim-btn-primary" @click="loadStatement">Load Statement</button>
          </div>
          <template v-else>
            <div class="cus-stmt-kpis" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:14px">
              <div style="background:#FFF5F5;border:1px solid #FFC9C9;border-radius:10px;padding:14px 16px">
                <div style="font-size:11px;color:#C92A2A;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">Total Outstanding</div>
                <div style="font-size:20px;font-weight:700;color:#C92A2A">₹{{fmtStmt(stmt.total_outstanding)}}</div>
              </div>
              <div style="background:#FFF9DB;border:1px solid #FFD43B;border-radius:10px;padding:14px 16px">
                <div style="font-size:11px;color:#E67700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">Overdue</div>
                <div style="font-size:20px;font-weight:700;color:#E67700">₹{{fmtStmt(stmt.overdue_amount)}}</div>
              </div>
              <div style="background:#F3F4F6;border:1px solid #E5E7EB;border-radius:10px;padding:14px 16px">
                <div style="font-size:11px;color:#6B7280;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">Open Invoices</div>
                <div style="font-size:20px;font-weight:700;color:#111827">{{stmt.invoices.length}}</div>
              </div>
            </div>
            <div v-if="!stmt.email" style="margin-bottom:12px;padding:10px 14px;background:#FFF9DB;border:1px solid #FFD43B;border-radius:8px;font-size:12.5px;color:#876800">
              ⚠️ No email on file — add an email to enable sending this statement.
            </div>
            <div class="cus-stmt-inv-wrap" style="background:#fff;border:1px solid #E5E7EB;border-radius:10px;overflow:hidden">
              <div v-if="!stmt.invoices.length" style="padding:24px;text-align:center;color:#9CA3AF;font-size:13px">No outstanding invoices</div>
              <template v-else>
                <div style="font-size:11px;font-weight:700;color:#9CA3AF;letter-spacing:0.8px;padding:12px 14px;background:#F9FAFB;border-bottom:1px solid #E5E7EB">OUTSTANDING INVOICES</div>
                <div class="cus-stmt-desktop">
                  <div v-for="inv in stmtInvsVisible" :key="inv.name"
                    style="display:grid;grid-template-columns:160px 100px 100px auto 80px;gap:8px;padding:8px 14px;border-bottom:1px solid #F3F4F6;font-size:12.5px;align-items:center;min-width:480px">
                    <span style="color:#2563EB;font-weight:600">{{inv.name}}</span>
                    <span style="color:#6B7280">{{inv.posting_date}}</span>
                    <span style="color:#6B7280">{{inv.due_date}}</span>
                    <span style="text-align:right;font-weight:600">₹{{fmtStmt(inv.outstanding_amount)}}</span>
                    <span :style="'padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;text-align:center;'+(inv.is_overdue?'background:#FFF5F5;color:#C92A2A':'background:#EBFBEE;color:#2F9E44')">
                      {{inv.is_overdue ? 'Overdue' : 'Due'}}
                    </span>
                  </div>
                </div>

                <!-- Mobile card view -->
                <div class="cus-stmt-mobile-cards">
                  <div v-for="inv in stmtInvsVisible" :key="'mc-'+inv.name" class="cus-stmt-mc">
                    <div class="cus-stmt-mc-top">
                      <span class="cus-stmt-mc-name">{{inv.name}}</span>
                      <span class="cus-stmt-mc-badge" :style="inv.is_overdue?'background:#FFF5F5;color:#C92A2A':'background:#EBFBEE;color:#2F9E44'">
                        {{inv.is_overdue ? 'Overdue' : 'Due'}}
                      </span>
                    </div>
                    <div class="cus-stmt-mc-mid">
                      <span>Posted {{inv.posting_date}}</span>
                      <span>Due {{inv.due_date}}</span>
                    </div>
                    <div class="cus-stmt-mc-amount">₹{{fmtStmt(inv.outstanding_amount)}}</div>
                  </div>
                </div>

                <!-- Load More — statement invoices -->
                <div v-if="stmtInvsHasMore" class="cus-load-more-wrap" style="border-top:1px solid #F3F4F6">
                  <span class="cus-load-more-count">Showing {{stmtInvsVisible.length}} of {{stmt.invoices.length}}</span>
                  <button class="cus-load-more-btn" @click="stmtPage++">Load more</button>
                </div>
                <div v-else-if="stmt.invoices.length > STMT_PAGE_SIZE" class="cus-load-more-wrap cus-load-more-end" style="border-top:1px solid #F3F4F6">
                  All {{stmt.invoices.length}} invoices shown
                </div>
              </template>
            </div>
          </template>
        </div>

      </div>
    </div>
  </div>

  <!-- Drawer -->
  <Teleport to="body">
    <div v-if="showPayModal" class="cus-pay-modal-overlay" @click.self="showPayModal=false">
      <div class="cus-pay-modal">
        <div style="font-size:16px;font-weight:700;color:#111827;margin-bottom:14px">Pay Opening Balance</div>
        <label style="display:flex;flex-direction:column;gap:4px;margin-bottom:12px;font-size:12.5px;color:#374151;font-weight:600">
          <span>Amount</span>
          <input type="number" v-model.number="payForm.amount" :max="obInfo.outstanding" min="0.01" step="0.01"
            style="border:1px solid #d1d5db;border-radius:8px;padding:8px 10px;font-size:13px;font-family:inherit"/>
        </label>
        <label style="display:flex;flex-direction:column;gap:4px;margin-bottom:12px;font-size:12.5px;color:#374151;font-weight:600">
          <span>Pay Into</span>
          <select v-model="payForm.bank_cash_account" style="border:1px solid #d1d5db;border-radius:8px;padding:8px 10px;font-size:13px;font-family:inherit">
            <option v-for="a in obInfo.bank_cash_accounts" :key="a.name" :value="a.name">{{ a.name }}</option>
          </select>
        </label>
        <label style="display:flex;flex-direction:column;gap:4px;margin-bottom:12px;font-size:12.5px;color:#374151;font-weight:600">
          <span>Date</span>
          <input type="date" v-model="payForm.payment_date"
            style="border:1px solid #d1d5db;border-radius:8px;padding:8px 10px;font-size:13px;font-family:inherit"/>
        </label>
        <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:16px">
          <button class="nim-btn" style="background:#fff;color:#374151;border:1px solid #E5E7EB" @click="showPayModal=false">Cancel</button>
          <button class="nim-btn nim-btn-primary" :disabled="payLoading" @click="submitPayment">
            {{ payLoading ? "Recording…" : "Record Payment" }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showDrawer" class="inv-drawer-bg" @click.self="showDrawer=false">
      <div class="inv-drawer-panel" :class="{open:showDrawer}" style="width:680px;max-width:98vw">

        <div class="inv-dh" style="background:linear-gradient(135deg,#16a34a,#15803d);padding:18px 24px">
          <div style="display:flex;align-items:center;gap:12px;flex:1;min-width:0">
            <div style="width:40px;height:40px;border-radius:10px;background:rgba(255,255,255,.18);display:flex;align-items:center;justify-content:center;flex-shrink:0">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            </div>
            <div style="min-width:0">
              <div class="inv-dh-title">{{drawerMode==='add'?'New Customer':'Edit Customer'}}</div>
              <div style="font-size:12px;color:rgba(255,255,255,.7);margin-top:1px">{{drawerMode==='edit'?form.name:'Fill in customer details'}}</div>
            </div>
          </div>
          <button style="background: rgba(255, 255, 255, .15);
    border: none;
    cursor: pointer;
    color: #fff;
    width: 30px;
    height: 30px;
    border-radius: 8px;
    display: grid;
    place-items: center;
    transition: .15s;" class="inv-dclose" @click="showDrawer=false" v-html="icon('x',14)"></button>
        </div>

        <div class="inv-view-tabs">
          <button v-for="t in [{k:'overview',l:'Overview'},{k:'address',l:'Address'},{k:'other',l:'Other Details'},{k:'bank',l:'Bank Details'},{k:'remarks',l:'Remarks'}]"
            :key="t.k" @click="drawerTab=t.k"
            class="inv-vtab" :class="{active: drawerTab===t.k}">
            {{t.l}}
          </button>
        </div>

        <div v-if="drawerLoading" style="flex:1;display:grid;place-items:center;color:#9ca3af;font-size:13px;padding:40px">
          Loading customer…
        </div>

        <div v-else class="inv-dbody" style="padding:24px;overflow-y:auto;flex:1">

          <!-- Overview Tab -->
          <template v-if="drawerTab==='overview'">

            <div style="margin-bottom:20px">
              <label class="inv-lbl" style="margin-bottom:8px;display:block">Customer Type</label>
              <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:8px">
                <button v-for="opt in CUSTOMER_TYPES" :key="opt" type="button"
                  @click="form.customer_type = opt"
                  :style="{
                    padding:'10px 8px', borderRadius:'10px', fontSize:'12px', fontWeight:'600',
                    cursor:'pointer', fontFamily:'inherit', transition:'all .15s', textAlign:'center',
                    border: '1.5px solid ' + (form.customer_type===opt ? CTYPE_META[opt].text : '#e2e8f0'),
                    background: form.customer_type===opt ? CTYPE_META[opt].bg : '#fff',
                    color: form.customer_type===opt ? CTYPE_META[opt].text : '#6b7280',
                    boxShadow: form.customer_type===opt ? '0 0 0 3px ' + CTYPE_META[opt].bg : 'none',
                  }">
                  <div style="font-size:18px;margin-bottom:4px">{{ CTYPE_META[opt].icon }}</div>
                  <div>{{ opt }}</div>
                </button>
              </div>
              <div v-if="form.customer_type && CTYPE_META[form.customer_type]"
                style="margin-top:8px;padding:7px 12px;border-radius:7px;font-size:12px;font-weight:500"
                :style="{background: CTYPE_META[form.customer_type].bg, color: CTYPE_META[form.customer_type].text}">
                {{ CTYPE_META[form.customer_type].icon }} {{ CTYPE_META[form.customer_type].desc }}
              </div>
            </div>

            <!-- Customer Group & Territory -->
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px">
              <div>
                <label class="inv-lbl" style="margin-bottom:6px;display:block">Customer Group</label>
                <select v-model="form.customer_group" class="inv-fi">
                  <option value="">— Select Group —</option>
                  <optgroup v-if="form.customer_type==='Distributor'" label="Distributor Groups">
                    <option v-for="g in customerGroups.filter(g=>g.toLowerCase().includes('distributor'))" :key="g" :value="g">{{ g }}</option>
                  </optgroup>
                  <optgroup v-if="form.customer_type==='Dealer'" label="Dealer Groups">
                    <option v-for="g in customerGroups.filter(g=>g.toLowerCase().includes('dealer'))" :key="g" :value="g">{{ g }}</option>
                  </optgroup>
                  <optgroup label="All Groups">
                    <option v-for="g in customerGroups" :key="g" :value="g">{{ g }}</option>
                  </optgroup>
                </select>
              </div>
              <div>
                <label class="inv-lbl" style="margin-bottom:6px;display:block">Territory</label>
                <select v-model="form.territory" class="inv-fi">
                  <option value="">— Select Territory —</option>
                  <option v-for="t in territories" :key="t" :value="t">{{ t }}</option>
                </select>
              </div>
            </div>

            <div style="margin-bottom:20px">
              <label class="inv-lbl" style="margin-bottom:8px;display:block">GST Treatment</label>
              <div style="display:flex;flex-wrap:wrap;gap:8px">
                <button v-for="opt in GST_TREATMENT_OPTIONS" :key="opt" @click="form.gst_treatment=opt" type="button"
                  :style="'padding:6px 14px;border-radius:20px;font-size:12.5px;font-weight:600;cursor:pointer;font-family:inherit;transition:all .15s;border:1.5px solid '+(form.gst_treatment===opt?GST_RULES[opt].badge.color:'#e2e8f0')+';background:'+(form.gst_treatment===opt?GST_RULES[opt].badge.bg:'#fff')+';color:'+(form.gst_treatment===opt?GST_RULES[opt].badge.color:'#6b7280')">
                  {{opt}}
                </button>
              </div>
              <div v-if="activeRule.hint" style="margin-top:8px;padding:8px 12px;background:#f8f9fc;border-left:3px solid;border-radius:0 6px 6px 0;font-size:12px;color:#6b7280;line-height:1.5"
                :style="{borderColor: activeRule.badge.color}">
                <span :style="{color:activeRule.badge.color,fontWeight:'600'}">{{activeRule.badge.label}}:</span> {{activeRule.hint}}
                <span v-if="activeRule.taxType"> · Tax: <strong>{{activeRule.taxType}}</strong></span>
              </div>
            </div>

            <div style="margin-bottom:16px">
              <label class="inv-lbl" style="margin-bottom:8px;display:block">Primary Contact</label>
              <div style="display:grid;grid-template-columns:140px 1fr 1fr;gap:10px">
                <select v-model="form.salutation" class="inv-fi" style="cursor:pointer">
                  <option value="">Salutation</option>
                  <option>Mr.</option><option>Ms.</option><option>Mrs.</option><option>Dr.</option><option>Prof.</option>
                </select>
                <div style="position:relative">
                  <input v-model="form.first_name" class="inv-fi" placeholder="First Name"
                    :style="formErrors.first_name?'border-color:#dc2626;background:#fff5f5':''"
                    @input="form.first_name=form.first_name.replace(/[^a-zA-Z\s.']/g,''); delete formErrors.first_name"
                    @blur="validateField('first_name')"/>
                  <div v-if="formErrors.first_name" style="position:absolute;left:0;top:100%;margin-top:3px;font-size:11.5px;color:#dc2626;white-space:nowrap">{{formErrors.first_name}}</div>
                </div>
                <div style="position:relative">
                  <input v-model="form.last_name" class="inv-fi" placeholder="Last Name"
                    :style="formErrors.last_name?'border-color:#dc2626;background:#fff5f5':''"
                    @input="form.last_name=form.last_name.replace(/[^a-zA-Z\s.']/g,''); delete formErrors.last_name"
                    @blur="validateField('last_name')"/>
                  <div v-if="formErrors.last_name" style="position:absolute;left:0;top:100%;margin-top:3px;font-size:11.5px;color:#dc2626;white-space:nowrap">{{formErrors.last_name}}</div>
                </div>
              </div>
            </div>

            <div style="margin-bottom:16px">
              <label class="inv-lbl">{{ form.customer_type==='Individual' ? 'Company / Org Name' : 'Company Name' }} <span v-if="form.customer_type!=='Individual'" class="nim-req">*</span></label>
              <input v-model="form.company_name" class="inv-fi" placeholder="Company name"
                :style="formErrors.company_name?'border-color:#dc2626;background:#fff5f5':''"
                @input="delete formErrors.company_name"
                @blur="validateField('company_name')"/>
              <div v-if="formErrors.company_name" style="margin-top:4px;font-size:12px;color:#dc2626;display:flex;align-items:center;gap:4px">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12" y2="16"/></svg>
                {{formErrors.company_name}}
              </div>
            </div>

            <div style="margin-bottom:16px">
              <label class="inv-lbl" style="display:flex;justify-content:space-between">
                <span>Display Name <span class="nim-req">*</span></span>
                <span :style="{fontSize:'11px',color:form.customer_name.length>90?'#dc2626':form.customer_name.length>0?'#9ca3af':'transparent'}">{{form.customer_name.length}}/100</span>
              </label>
              <input v-model="form.customer_name" class="inv-fi" maxlength="100"
                :style="formErrors.customer_name?'border-color:#dc2626;background:#fff5f5':''"
                placeholder="Name shown on invoices and orders"
                @input="form.customer_name=form.customer_name.replace(/[^a-zA-Z\s.'-]/g,''); delete formErrors.customer_name"
                @blur="validateField('customer_name')"/>
              <div v-if="formErrors.customer_name" style="margin-top:4px;font-size:12px;color:#dc2626;display:flex;align-items:center;gap:4px">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12" y2="16"/></svg>
                {{formErrors.customer_name}}
              </div>
            </div>

            <transition name="gst-field">
              <div v-if="activeRule.showGstin || activeRule.showPan"
                style="display:grid;gap:14px;margin-bottom:16px"
                :style="{gridTemplateColumns: (activeRule.showGstin && activeRule.showPan) ? '1fr 1fr' : '1fr'}">
                <div v-if="activeRule.showGstin">
                  <label class="inv-lbl">
                    GSTIN / Tax ID
                    <span v-if="activeRule.requireGstin" class="nim-req">*</span>
                    <span v-else style="font-size:11px;font-weight:400;color:#9ca3af;margin-left:4px">(optional)</span>
                  </label>
                  <input v-model="form.tax_id" class="inv-fi"
                    :style="formErrors.tax_id?'border-color:#dc2626;background:#fff5f5':''"
                    :placeholder="activeRule.gstinPlaceholder||'27AAPFU0939F1ZV'"
                    style="font-family:var(--mono);letter-spacing:.04em"
                    @input="form.tax_id=form.tax_id.toUpperCase();delete formErrors.tax_id"
                    @blur="validateField('tax_id')"/>
                  <div v-if="formErrors.tax_id" style="margin-top:4px;font-size:12px;color:#dc2626;display:flex;align-items:center;gap:4px">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12" y2="16"/></svg>
                    {{formErrors.tax_id}}
                  </div>
                  <div v-else-if="form.tax_id && !formErrors.tax_id && GSTIN_REGEX.test(form.tax_id)"
                    style="margin-top:4px;font-size:12px;color:#2f9e44;display:flex;align-items:center;gap:4px">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                    Valid GSTIN
                  </div>
                </div>
                <div v-if="activeRule.showPan">
                  <label class="inv-lbl">PAN Number <span style="font-size:11px;font-weight:400;color:#9ca3af">(optional)</span></label>
                  <input v-model="form.pan_no" class="inv-fi" placeholder="ABCDE1234F" maxlength="10"
                    style="font-family:var(--mono);letter-spacing:.04em"
                    :style="formErrors.pan_no?'border-color:#dc2626;background:#fff5f5':''"
                    @input="form.pan_no=form.pan_no.toUpperCase().replace(/[^A-Z0-9]/g,''); delete formErrors.pan_no"
                    @blur="validateField('pan_no')"/>
                  <div v-if="formErrors.pan_no" style="margin-top:4px;font-size:12px;color:#dc2626;display:flex;align-items:center;gap:4px">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12" y2="16"/></svg>
                    {{formErrors.pan_no}}
                  </div>
                  <div v-else-if="form.pan_no && PAN_REGEX.test(form.pan_no)" style="margin-top:4px;font-size:12px;color:#2f9e44;display:flex;align-items:center;gap:4px">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                    Valid PAN
                  </div>
                </div>
              </div>
            </transition>

            <div style="height:1px;background:#e8ecf0;margin-bottom:20px"></div>

            <div class="cus-form-grid2" style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:16px">
              <div>
                <label class="inv-lbl">Email Address</label>
                <input v-model="form.email_id" class="inv-fi" placeholder="name@company.com"
                  :style="formErrors.email_id?'border-color:#dc2626;background:#fff5f5':form.email_id&&EMAIL_REGEX.test(form.email_id)?'border-color:#2f9e44':''"
                  @input="delete formErrors.email_id"
                  @blur="validateField('email_id')"/>
                <div v-if="formErrors.email_id" style="margin-top:4px;font-size:12px;color:#dc2626;display:flex;align-items:center;gap:4px">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12" y2="16"/></svg>
                  {{formErrors.email_id}}
                </div>
                <div v-else-if="form.email_id&&EMAIL_REGEX.test(form.email_id)" style="margin-top:4px;font-size:12px;color:#2f9e44;display:flex;align-items:center;gap:4px">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                  Valid email
                </div>
              </div>
              <div>
                <label class="inv-lbl">Work Phone</label>
                <input v-model="form.phone" class="inv-fi" placeholder="022-12345678"
                  :style="formErrors.phone?'border-color:#dc2626;background:#fff5f5':''"
                  @input="form.phone=form.phone.replace(/[^\d+\-\s()]/g,''); delete formErrors.phone"
                  @blur="validateField('phone')"/>
                <div v-if="formErrors.phone" style="margin-top:4px;font-size:12px;color:#dc2626;display:flex;align-items:center;gap:4px">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12" y2="16"/></svg>
                  {{formErrors.phone}}
                </div>
              </div>
              <div>
                <label class="inv-lbl">Mobile</label>
                <div class="cus-mobile-row" style="display:flex;gap:0">
                  <select v-model="form.mobile_code" class="inv-fi cus-mobile-code" style="width:90px;border-right:none;border-radius:8px 0 0 8px;background:#f8f9fc;cursor:pointer;flex-shrink:0;padding:0 6px"
                    @change="delete formErrors.mobile_no; if(form.mobile_no) validateField('mobile_no')">
                    <option value="+91">🇮🇳 +91</option>
                    <option value="+1">🇺🇸 +1</option>
                    <option value="+44">🇬🇧 +44</option>
                    <option value="+61">🇦🇺 +61</option>
                    <option value="+971">🇦🇪 +971</option>
                    <option value="+65">🇸🇬 +65</option>
                    <option value="+49">🇩🇪 +49</option>
                    <option value="+33">🇫🇷 +33</option>
                    <option value="+60">🇲🇾 +60</option>
                    <option value="+94">🇱🇰 +94</option>
                    <option value="+966">🇸🇦 +966</option>
                    <option value="+92">🇵🇰 +92</option>
                    <option value="+880">🇧🇩 +880</option>
                    <option value="+977">🇳🇵 +977</option>
                    <option value="+27">🇿🇦 +27</option>
                    <option value="+55">🇧🇷 +55</option>
                    <option value="+86">🇨🇳 +86</option>
                    <option value="+81">🇯🇵 +81</option>
                  </select>
                  <input v-model="form.mobile_no" class="inv-fi" style="border-radius:0 8px 8px 0;flex:1" placeholder="98765 43210"
                    :style="formErrors.mobile_no?'border-color:#dc2626;background:#fff5f5':form.mobile_no&&!formErrors.mobile_no&&form.mobile_no.replace(/\D/g,'').length>6?'border-color:#2f9e44':''"
                    @input="form.mobile_no=form.mobile_no.replace(/\D/g,''); delete formErrors.mobile_no"
                    @blur="validateField('mobile_no')"/>
                </div>
                <div v-if="formErrors.mobile_no" style="margin-top:4px;font-size:12px;color:#dc2626;display:flex;align-items:center;gap:4px">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12" y2="16"/></svg>
                  {{formErrors.mobile_no}}
                </div>
                <div v-else-if="form.mobile_no&&!formErrors.mobile_no&&(form.mobile_code==='+91'?form.mobile_no.replace(/\D/g,'').length===10:form.mobile_no.replace(/\D/g,'').length>=7)" style="margin-top:4px;font-size:12px;color:#2f9e44;display:flex;align-items:center;gap:4px">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                  Valid mobile number
                </div>
              </div>
              <div>
                <label class="inv-lbl">Website</label>
                <input v-model="form.website" class="inv-fi" placeholder="https://company.com"
                  :style="formErrors.website?'border-color:#dc2626;background:#fff5f5':form.website&&URL_REGEX.test(form.website)?'border-color:#2f9e44':''"
                  @input="delete formErrors.website"
                  @blur="validateField('website')"/>
                <div v-if="formErrors.website" style="margin-top:4px;font-size:12px;color:#dc2626;display:flex;align-items:center;gap:4px">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12" y2="16"/></svg>
                  {{formErrors.website}}
                </div>
                <div v-else-if="form.website&&URL_REGEX.test(form.website)" style="margin-top:4px;font-size:12px;color:#2f9e44;display:flex;align-items:center;gap:4px">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                  Valid URL
                </div>
              </div>
            </div>

            <div style="height:1px;background:#e8ecf0;margin-bottom:20px"></div>

            <div class="inv-sec-lbl" style="margin-top:0">Billing Preferences</div>
            <div class="cus-form-grid3" style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin-bottom:20px">
              <div>
                <label class="inv-lbl">Payment Terms</label>
                <select v-model="form.payment_terms" class="inv-fi" style="cursor:pointer">
                  <option value="">— Select —</option>
                  <option>Net 7</option><option>Net 15</option><option>Net 30</option><option>Net 45</option><option>Net 60</option>
                  <option>Due on Receipt</option><option>End of Month</option>
                </select>
              </div>
              <div>
                <label class="inv-lbl">Credit Limit ({{ currencySymbol }})</label>
                <input v-model.number="form.credit_limit" type="number" min="0" class="inv-fi" placeholder="0 = unlimited"
                  :style="formErrors.credit_limit?'border-color:#dc2626;background:#fff5f5':''"
                  @input="delete formErrors.credit_limit"
                  @blur="validateField('credit_limit')"/>
                <div v-if="formErrors.credit_limit" style="margin-top:4px;font-size:12px;color:#dc2626;display:flex;align-items:center;gap:4px">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12" y2="16"/></svg>
                  {{formErrors.credit_limit}}
                </div>
              </div>
            </div>

            <div v-if="drawerMode==='edit'" style="padding:14px 16px;background:#fff5f5;border-radius:8px;border:1px solid #fecaca;display:flex;align-items:center;gap:10px;cursor:pointer" @click="form.disabled=form.disabled?0:1">
              <input type="checkbox" :checked="!!form.disabled" @click.stop="form.disabled=form.disabled?0:1" style="width:16px;height:16px;accent-color:#dc2626;cursor:pointer;flex-shrink:0"/>
              <div>
                <div style="font-size:13px;font-weight:600;color:#dc2626">Disable Customer</div>
                <div style="font-size:12px;color:#9ca3af;margin-top:1px">Disabled customers won't appear in invoice and order dropdowns</div>
              </div>
            </div>
          </template>

          <!-- Address Tab -->
          <template v-else-if="drawerTab==='address'">
            <AddressManager
              partyDoctype="Customer"
              :partyName="drawerMode==='edit' ? form.name : ''"
              v-model="pendingAddresses"
              @addressSaved="load"
              @addressDeleted="load"
            />
          </template>

          <!-- Other Details Tab -->
          <template v-else-if="drawerTab==='other'">
            <div class="inv-sec-lbl" style="margin-top:0">Tax &amp; Compliance</div>

            <div style="display:flex;align-items:center;gap:8px;margin-bottom:16px;padding:10px 14px;border-radius:8px;border:1px solid #e8ecf0;background:#fafbfd">
              <span style="font-size:12px;color:#6b7280;font-weight:500">Current GST Treatment:</span>
              <span :style="'padding:3px 10px;border-radius:12px;font-size:12px;font-weight:700;background:'+activeRule.badge.bg+';color:'+activeRule.badge.color">
                {{form.gst_treatment}}
              </span>
              <span style="font-size:12px;color:#9ca3af">·</span>
              <span style="font-size:12px;font-weight:600;color:#374151">Tax: {{activeRule.taxType}}</span>
              <button @click="drawerTab='overview'" style="margin-left:auto;font-size:12px;color:#3B5BDB;background:none;border:none;cursor:pointer;font-weight:600;font-family:inherit">Change →</button>
            </div>

            <div class="cus-form-grid2" style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:18px">
              <transition name="gst-field">
                <div v-if="activeRule.showPlaceOfSupply">
                  <label class="inv-lbl">
                    Place of Supply
                    <span v-if="activeRule.requirePlaceOfSupply" class="nim-req">*</span>
                  </label>
                  <select v-model="form.place_of_supply" class="inv-fi" style="cursor:pointer"
                    :style="formErrors.place_of_supply?'border-color:#dc2626;background:#fff5f5':''"
                    @change="delete formErrors.place_of_supply">
                    <option value="">— Select State —</option>
                    <option v-for="s in PLACE_OF_SUPPLY" :key="s" :value="s">{{s}}</option>
                  </select>
                  <div v-if="formErrors.place_of_supply" style="margin-top:4px;font-size:12px;color:#dc2626">{{formErrors.place_of_supply}}</div>
                </div>
              </transition>
              <div v-if="!activeRule.showPlaceOfSupply" style="padding:12px 14px;border-radius:8px;background:#f0f9ff;border:1px solid #bae6fd;font-size:12.5px;color:#0369a1;line-height:1.5;display:flex;align-items:flex-start;gap:8px">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0;margin-top:1px"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12" y2="16"/></svg>
                Place of Supply not applicable for <strong>{{form.gst_treatment}}</strong> customers.
              </div>
              <div>
                <label class="inv-lbl">Customer Source</label>
                <select v-model="form.source" class="inv-fi" style="cursor:pointer">
                  <option value="">— Select —</option>
                  <option>Cold Calling</option><option>Email</option><option>Existing Customer</option>
                  <option>Partner</option><option>Campaign</option><option>Website</option><option>Referral</option><option>Word of Mouth</option><option>Other</option>
                </select>
              </div>
            </div>
<!-- 
            <div class="inv-sec-lbl">TDS / Withholding Tax</div>
            <div style="margin-bottom:18px">
              <div style="display:flex;align-items:center;gap:10px;padding:10px 14px;border-radius:8px;border:1px solid #e8ecf0;background:#fafbfd">
                <input type="checkbox" id="cust_tds_applicable" :checked="!!form.tds_applicable"
                  @change="form.tds_applicable = $event.target.checked ? 1 : 0"
                  style="width:16px;height:16px;accent-color:#16a34a;cursor:pointer;flex-shrink:0"/>
                <label for="cust_tds_applicable" style="font-size:13px;color:#374151;cursor:pointer;font-weight:500">
                  TDS Applicable — tax deducted at source on payments from this customer
                </label>
              </div>
              <div v-if="form.tds_applicable" class="cus-form-grid2" style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px">
                <div>
                  <label class="inv-lbl">Default TDS Section</label>
                  <select v-model="form.tds_section" class="inv-fi" style="cursor:pointer">
                    <option value="">Select Section</option>
                    <option>194C</option><option>194J</option><option>194A</option>
                    <option>194H</option><option>194I</option><option>192</option>
                    <option>195</option><option>Other</option>
                  </select>
                </div>
              </div>
            </div> -->

            <div class="inv-sec-lbl">Opening Balance</div>
            <div class="cus-form-grid2" style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:18px">
              <div>
                <label class="inv-lbl">Opening Balance (₹)</label>
                <input v-model.number="form.opening_balance" type="number" min="0" class="inv-fi" placeholder="0.00"
                  :style="formErrors.opening_balance?'border-color:#dc2626;background:#fff5f5':''"
                  @input="delete formErrors.opening_balance"
                  @blur="validateField('opening_balance')"/>
                <div v-if="formErrors.opening_balance" style="margin-top:4px;font-size:12px;color:#dc2626">{{formErrors.opening_balance}}</div>
              </div>
            </div>
          </template>

          <!-- Bank Tab -->
          <template v-else-if="drawerTab==='bank'">
            <div class="inv-sec-lbl" style="margin-top:0">Bank Account</div>
            <div class="cus-form-grid2 cus-bank-grid" style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
              <div class="cus-bank-full" style="grid-column:span 2">
                <label class="inv-lbl">Bank Name</label>
                <input v-model="form.bank_name" class="inv-fi" placeholder="HDFC Bank, SBI, ICICI…"/>
              </div>
              <div>
                <label class="inv-lbl">Account Number <span style="font-size:11px;font-weight:400;color:#9ca3af">(9–18 digits)</span></label>
                <input v-model="form.bank_account_no" class="inv-fi" placeholder="XXXXXXXXXXXXXXXX" maxlength="18" style="font-family:var(--mono)"
                  :style="formErrors.bank_account_no?'border-color:#dc2626;background:#fff5f5':form.bank_account_no&&!formErrors.bank_account_no&&/^\d{9,18}$/.test(form.bank_account_no)?'border-color:#2f9e44':''"
                  @input="form.bank_account_no=form.bank_account_no.replace(/\D/g,''); delete formErrors.bank_account_no"
                  @blur="validateField('bank_account_no')"/>
                <div v-if="formErrors.bank_account_no" style="margin-top:4px;font-size:12px;color:#dc2626">{{formErrors.bank_account_no}}</div>
                <div v-else-if="form.bank_account_no&&/^\d{9,18}$/.test(form.bank_account_no)" style="margin-top:4px;font-size:12px;color:#2f9e44">Valid account number</div>
              </div>
              <div>
                <label class="inv-lbl">IFSC Code <span style="font-size:11px;font-weight:400;color:#9ca3af">(AAAA0XXXXXX)</span></label>
                <input v-model="form.bank_ifsc" class="inv-fi" placeholder="HDFC0001234" maxlength="11" style="font-family:var(--mono)"
                  :style="formErrors.bank_ifsc?'border-color:#dc2626;background:#fff5f5':form.bank_ifsc&&IFSC_REGEX.test(form.bank_ifsc)?'border-color:#2f9e44':''"
                  @input="form.bank_ifsc=form.bank_ifsc.toUpperCase().replace(/[^A-Z0-9]/g,''); delete formErrors.bank_ifsc"
                  @blur="validateField('bank_ifsc')"/>
                <div v-if="formErrors.bank_ifsc" style="margin-top:4px;font-size:12px;color:#dc2626">{{formErrors.bank_ifsc}}</div>
                <div v-else-if="form.bank_ifsc&&IFSC_REGEX.test(form.bank_ifsc)" style="margin-top:4px;font-size:12px;color:#2f9e44">Valid IFSC</div>
              </div>
            </div>
          </template>

          <!-- Remarks Tab -->
          <template v-else-if="drawerTab==='remarks'">
            <div class="inv-sec-lbl" style="margin-top:0">Internal Notes</div>
            <textarea v-model="form.notes" class="inv-fi" rows="14" style="resize:vertical;line-height:1.6;min-height:280px" placeholder="Add any internal notes about this customer — payment behaviour, communication preferences, account history…"></textarea>
          </template>

        </div>

        <!-- Footer -->
        <div class="inv-dfooter" style="border-top:1px solid #e8ecf0;padding:14px 24px;background:#fafbfd">
          <button class="form-btn form-btn-outline" @click="showDrawer=false">Cancel</button>
          <button class="form-btn form-btn-primary" @click="saveCustomer" :disabled="saving" style="background:#16a34a;border-color:#16a34a;min-width:140px;position:relative">
            <span v-if="saving" v-html="icon('refresh',13)" style="animation:spin 1s linear infinite"></span>
            {{saving ? 'Saving…' : (drawerMode==='add' ? 'Create Customer' : 'Save Changes')}}
            <span v-if="Object.keys(formErrors).length && !saving"
              style="position:absolute;top:-6px;right:-6px;background:#dc2626;color:#fff;border-radius:10px;font-size:10px;font-weight:700;padding:1px 5px;min-width:16px;text-align:center;line-height:16px">
              {{Object.keys(formErrors).length}}
            </span>
          </button>
        </div>

      </div>
    </div>
  </Teleport>

  <!-- Delete Confirm Modal -->
  <Teleport to="body">
    <div v-if="showDelete" class="nim-overlay" @click.self="showDelete=false">
      <div class="nim-dialog" style="max-width:420px">
        <div class="nim-header" style="background:linear-gradient(135deg,#dc2626,#b91c1c)">
          <div class="nim-header-left">
            <div class="nim-header-icon" style="color:#fff;">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/></svg>
            </div>
            <div class="nim-header-title">Delete Customer?</div>
          </div>
          <button class="nim-close" @click="showDelete=false" v-html="icon('x',15)"></button>
        </div>
        <div class="nim-body" style="padding:20px 24px">
          <p style="font-size:14px;color:#374151;line-height:1.6">
            Are you sure you want to delete <strong>{{deleteTarget?.customer_name}}</strong>?
            This action cannot be undone.
          </p>
        </div>
        <div class="inv-dfooter">
          <button class="form-btn form-btn-outline" @click="showDelete=false">Cancel</button>
          <button @click="doDelete" :disabled="deleting"
            style="height:37px;padding:0 18px;border-radius:8px;font-size:13.5px;font-weight:600;cursor:pointer;font-family:inherit;border:none;background:#dc2626;color:#fff;display:inline-flex;align-items:center;gap:7px">
            <span v-if="deleting" v-html="icon('refresh',13)" style="animation:spin 1s linear infinite"></span>
            {{deleting ? 'Deleting…' : 'Yes, Delete'}}
          </button>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- CSV Import Preview / Summary Modal -->
  <Teleport to="body">
    <div v-if="importModal.open" class="nim-overlay" @click.self="!importModal.running && closeImport()">
      <div class="nim-dialog cus-import-dialog" style="max-width:620px;width:96vw">
        <div class="nim-header" style="background:linear-gradient(135deg,#16a34a,#15803d)">
          <div class="nim-header-left">
            <div class="nim-header-icon" style="color:#fff;"><span v-html="icon('upload',16)"></span></div>
            <div class="nim-header-title">{{ importModal.done ? 'Import Complete' : 'Review Import' }}</div>
          </div>
          <button class="nim-close" @click="closeImport" :disabled="importModal.running" v-html="icon('x',15)"></button>
        </div>

        <div class="nim-body" style="padding:18px 22px">

          <!-- ── Preview phase ── -->
          <template v-if="!importModal.done">
            <div class="cus-import-stats">
              <div class="cus-import-stat"><div class="cus-import-stat-val">{{ importCounts.total }}</div><div class="cus-import-stat-lbl">Rows</div></div>
              <div class="cus-import-stat cus-import-stat-new"><div class="cus-import-stat-val">{{ importCounts.create }}</div><div class="cus-import-stat-lbl">New</div></div>
              <div class="cus-import-stat cus-import-stat-upd"><div class="cus-import-stat-val">{{ importCounts.update }}</div><div class="cus-import-stat-lbl">Update</div></div>
            </div>
            <div class="cus-import-note">
              Rows matching an existing customer name will be <strong>updated</strong> (blank cells keep current values); the rest are <strong>created</strong>.
            </div>
            <div class="cus-import-table-wrap">
              <table class="cus-import-table">
                <thead>
                  <tr><th>Customer</th><th>Type</th><th>GSTIN</th><th style="text-align:right">Action</th></tr>
                </thead>
                <tbody>
                  <tr v-for="(row,i) in importPreviewRows" :key="i">
                    <td>
                      <div class="cus-import-name">{{ row.cname }}</div>
                      <div class="cus-import-sub">{{ row.email || row.mobile || '—' }}</div>
                    </td>
                    <td>{{ row.ctype }}</td>
                    <td class="cus-import-mono">{{ row.gstin || '—' }}</td>
                    <td style="text-align:right">
                      <span class="cus-import-badge" :class="row.action==='update' ? 'cus-import-badge-upd' : 'cus-import-badge-new'">
                        {{ row.action==='update' ? 'Update' : 'New' }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
              <div v-if="importModal.rows.length > importPreviewRows.length" class="cus-import-more">
                + {{ importModal.rows.length - importPreviewRows.length }} more row(s) not shown
              </div>
            </div>
          </template>

          <!-- ── Summary phase ── -->
          <template v-else>
            <div class="cus-import-stats">
              <div class="cus-import-stat cus-import-stat-new"><div class="cus-import-stat-val">{{ importModal.result.created }}</div><div class="cus-import-stat-lbl">Created</div></div>
              <div class="cus-import-stat cus-import-stat-upd"><div class="cus-import-stat-val">{{ importModal.result.updated }}</div><div class="cus-import-stat-lbl">Updated</div></div>
              <div class="cus-import-stat" :class="importModal.result.failed ? 'cus-import-stat-fail' : ''"><div class="cus-import-stat-val">{{ importModal.result.failed }}</div><div class="cus-import-stat-lbl">Failed</div></div>
            </div>
            <div class="cus-import-note" style="text-align:center">
              {{ importModal.result.failed
                  ? 'Some rows could not be saved — check that names/GSTINs are valid.'
                  : 'All rows imported successfully.' }}
            </div>
          </template>
        </div>

        <div class="inv-dfooter">
          <template v-if="!importModal.done">
            <button class="form-btn form-btn-outline" @click="closeImport" :disabled="importModal.running">Cancel</button>
            <button class="form-btn form-btn-primary" @click="runImport" :disabled="importModal.running || !importCounts.total"
              style="background:#16a34a;border-color:#16a34a;min-width:150px">
              <span v-if="importModal.running" v-html="icon('refresh',13)" style="animation:spin 1s linear infinite"></span>
              {{ importModal.running ? 'Importing…' : `Import ${importCounts.total} Row(s)` }}
            </button>
          </template>
          <template v-else>
            <button class="form-btn form-btn-primary" @click="closeImport" style="background:#16a34a;border-color:#16a34a;min-width:110px">Done</button>
          </template>
        </div>
      </div>
    </div>
  </Teleport>

</div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from "vue";
import { apiList, apiGET, apiSave, apiSubmit, apiDelete, apiPOST, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { usePermissions } from "../composables/usePermissions.js";
import AddressManager from "../components/AddressManager.vue";
import { fmt, fmtDate } from "../utils/format.js";
import { icon } from "../utils/icons.js";
import { COUNTRIES, statesFor } from "../composables/useCountryState.js";
import {
  EMAIL_REGEX, GSTIN_REGEX, PAN_REGEX, IFSC_REGEX, URL_REGEX,
  validateMobile, validatePhone, validatePincode, sanitizePincode, pincodePlaceholder, pincodeHint,
} from "../composables/useValidation.js";

const { toast } = useToast();
const { canWrite } = usePermissions();

// ── Static option lists, factored out of inline template arrays in legacy ──
// COUNTRIES and statesFor() imported from useCountryState.js
const PLACE_OF_SUPPLY = [
  "01-Jammu and Kashmir","02-Himachal Pradesh","03-Punjab","04-Chandigarh","05-Uttarakhand",
  "06-Haryana","07-Delhi","08-Rajasthan","09-Uttar Pradesh","10-Bihar","11-Sikkim","12-Arunachal Pradesh",
  "13-Nagaland","14-Manipur","15-Mizoram","16-Tripura","17-Meghalaya","18-Assam","19-West Bengal",
  "20-Jharkhand","21-Odisha","22-Chhattisgarh","23-Madhya Pradesh","24-Gujarat","25-Daman and Diu",
  "26-Dadra and Nagar Haveli","27-Maharashtra","28-Andhra Pradesh","29-Karnataka","30-Goa","31-Lakshadweep",
  "32-Kerala","33-Tamil Nadu","34-Puducherry","35-Andaman and Nicobar Islands","36-Telangana",
  "37-Andhra Pradesh (New)","38-Ladakh",
];

const CUSTOMER_TYPES = ["Company", "Individual", "Government", "Dealer", "Distributor"];

// Customer type metadata — colour + description
const CTYPE_META = {
  "Company":     { bg: "#dbeafe", text: "#1d4ed8", icon: "🏢", desc: "B2B registered company" },
  "Individual":  { bg: "#f1f5f9", text: "#475569", icon: "👤", desc: "Direct individual buyer" },
  "Government":  { bg: "#ede9fe", text: "#6d28d9", icon: "🏛️", desc: "Govt / PSU department" },
  "Dealer":      { bg: "#fef9c3", text: "#a16207", icon: "🏪", desc: "Authorised dealer / reseller" },
  "Distributor": { bg: "#dcfce7", text: "#15803d", icon: "🚚", desc: "Regional distributor / stockist" },
};

// Default customer groups seeded per type (fallback if API is unavailable)
const DEFAULT_CUSTOMER_GROUPS = {
  "Company":     ["Wholesale", "Institutional"],
  "Individual":  ["Retail", "Walk-in"],
  "Government":  ["Government"],
  "Dealer":      ["Dealer - Local", "Dealer - Regional", "Dealer - National"],
  "Distributor": ["Distributor - State", "Distributor - Zone", "Distributor - National"],
};

// All flat group list loaded from server
const customerGroups = ref([]);
const territories    = ref([]);

// ── State ──
const list = ref([]);
const lastInvoiceByCust = ref({});   // {customer: {name, date, amount}}
const loading = ref(true);
const search = ref("");
const selectedRows = ref(new Set());
const bulkBusy = ref(false);
const importInput = ref(null);
const importModal = reactive({
  open: false, running: false, done: false,
  rows: [], result: { created: 0, updated: 0, failed: 0 },
});

function toggleRow(name) {
  const s = new Set(selectedRows.value);
  s.has(name) ? s.delete(name) : s.add(name);
  selectedRows.value = s;
}
function clearSelection() { selectedRows.value = new Set(); }
const activeFilter = ref("all");
const viewMode     = ref("table"); // "table" | "grid"
const showDrawer = ref(false);
const drawerMode = ref("add");
const drawerLoading = ref(false);
const saving = ref(false);
const showDelete = ref(false);
const deleteTarget = ref(null);
const deleting = ref(false);
const drawerTab = ref("overview");
const formErrors = reactive({});
const shipSameAsBilling = ref(false);
const pendingAddresses = ref([]);

// ── GST Treatment rules ──
const GST_RULES = {
  "Registered Business": {
    badge: { label: "Registered", bg: "#EBFBEE", color: "#2F9E44" },
    showGstin: true, requireGstin: true,
    showPan: true, requirePan: false,
    showPlaceOfSupply: true, requirePlaceOfSupply: true,
    requireIndiaCountry: false,
    taxType: "GST",
    hint: "GSTIN is mandatory for Registered Businesses.",
    gstinPlaceholder: "27AAPFU0939F1ZV",
  },
  "Unregistered Business": {
    badge: { label: "Unregistered", bg: "#FFF3BF", color: "#E67700" },
    showGstin: false, requireGstin: false,
    showPan: true, requirePan: false,
    showPlaceOfSupply: true, requirePlaceOfSupply: true,
    requireIndiaCountry: false,
    taxType: "GST",
    hint: "No GSTIN required. Tax will be applied based on Place of Supply.",
  },
  "Overseas": {
    badge: { label: "Overseas", bg: "#E7F5FF", color: "#1971C2" },
    showGstin: false, requireGstin: false,
    showPan: false, requirePan: false,
    showPlaceOfSupply: false, requirePlaceOfSupply: false,
    requireIndiaCountry: false,
    taxType: "Zero Rated (Export/LUT)",
    hint: "Exports are zero-rated under GST. Raise invoices under LUT/Bond without charging IGST, or charge IGST and claim refund. No Indian GSTIN required.",
    countryNote: "Set country to the customer's country (outside India).",
  },
  "SEZ": {
    badge: { label: "SEZ", bg: "#F3F0FF", color: "#2563eb" },
    showGstin: true, requireGstin: true,
    showPan: true, requirePan: false,
    showPlaceOfSupply: true, requirePlaceOfSupply: true,
    requireIndiaCountry: false,
    taxType: "GST 0%",
    hint: "Supplies to SEZ are zero-rated. GSTIN is mandatory.",
    gstinPlaceholder: "SEZ unit GSTIN",
  },
  "Consumer": {
    badge: { label: "Consumer", bg: "#F8F9FA", color: "#495057" },
    showGstin: false, requireGstin: false,
    showPan: false, requirePan: false,
    showPlaceOfSupply: false, requirePlaceOfSupply: false,
    requireIndiaCountry: false,
    taxType: "GST",
    hint: "B2C customer. No GSTIN required.",
  },
};
const GST_TREATMENT_OPTIONS = Object.keys(GST_RULES);

const FIELD_TAB = {
  customer_name: "overview", first_name: "overview", last_name: "overview",
  company_name: "overview", email_id: "overview", mobile_no: "overview",
  phone: "overview", website: "overview", credit_limit: "overview",
  tax_id: "overview", pan_no: "overview",
  place_of_supply: "other", opening_balance: "other",
  pincode: "address", ship_pincode: "address",
  bank_account_no: "bank", bank_ifsc: "bank",
};

// ── Form state ──
const form = reactive({
  name: "",
  customer_name: "", customer_type: "Company", salutation: "",
  first_name: "", last_name: "", company_name: "",
  customer_group: "", territory: "",
  gst_treatment: "Registered Business",
  tax_id: "", default_currency: "INR", credit_limit: 0,
  email_id: "", mobile_code: "+91", mobile_no: "", phone: "", website: "",
  address_line1: "", address_line2: "",
  city: "", state: "", pincode: "", country: "India",
  ship_address_line1: "", ship_address_line2: "",
  ship_city: "", ship_state: "", ship_pincode: "", ship_country: "India",
  payment_terms: "", place_of_supply: "", source: "",
  pan_no: "", opening_balance: 0,
  tds_applicable: 0, tds_section: "",
  bank_name: "", bank_account_no: "", bank_ifsc: "",
  notes: "", disabled: 0,
});

const activeRule = computed(() => GST_RULES[form.gst_treatment] || GST_RULES["Registered Business"]);

const currencySymbol = "₹";

// Clear GSTIN/POS errors when treatment changes
watch(() => form.gst_treatment, () => {
  delete formErrors.tax_id;
  delete formErrors.place_of_supply;
  if (!activeRule.value.showGstin) form.tax_id = "";
  if (!activeRule.value.showPlaceOfSupply) form.place_of_supply = "";
});

function validateField(field) {
  delete formErrors[field];
  const rule = activeRule.value;
  const v = form[field];
  const s = typeof v === "string" ? v.trim() : v;

  if (field === "customer_name") {
    if (!s) formErrors.customer_name = "Display name is required";
    else if (s.length < 2) formErrors.customer_name = "Name must be at least 2 characters";
    else if (s.length > 100) formErrors.customer_name = "Name must not exceed 100 characters";
  }
  if (field === "first_name" && s && !/^[\p{L}\s.'\-]+$/u.test(s))
    formErrors.first_name = "First name must contain letters only";
  if (field === "last_name" && s && !/^[\p{L}\s.'\-]+$/u.test(s))
    formErrors.last_name = "Last name must contain letters only";
  if (field === "company_name" && form.customer_type !== "Individual" && !s)
    formErrors.company_name = "Company name is required for " + form.customer_type + " customers";
  if (field === "email_id" && s && !EMAIL_REGEX.test(s))
    formErrors.email_id = "Invalid email address";
  if (field === "mobile_no" && s) {
    const err = validateMobile(s.replace(/\D/g, ""), form.mobile_code);
    if (err) formErrors.mobile_no = err;
  }
  if (field === "phone" && s) {
    const err = validatePhone(s);
    if (err) formErrors.phone = err;
  }
  if (field === "website" && s && !URL_REGEX.test(s))
    formErrors.website = "Website must start with http:// or https://";
  if (field === "credit_limit" && v < 0)
    formErrors.credit_limit = "Credit limit cannot be negative";
  if (field === "tax_id") {
    if (rule.requireGstin && !s)
      formErrors.tax_id = "GSTIN is required for " + form.gst_treatment;
    else if (rule.showGstin && s && !GSTIN_REGEX.test(s))
      formErrors.tax_id = "Invalid GSTIN format (e.g. 27AAPFU0939F1ZV)";
  }
  if (field === "pan_no" && s && !PAN_REGEX.test(s))
    formErrors.pan_no = "Invalid PAN format (e.g. ABCDE1234F)";
  if (field === "place_of_supply" && rule.requirePlaceOfSupply && !v)
    formErrors.place_of_supply = "Place of Supply is required";
  if (field === "pincode" && s) {
    const err = validatePincode(s, form.country);
    if (err) formErrors.pincode = err;
  }
  if (field === "ship_pincode" && s) {
    const err = validatePincode(s, form.ship_country);
    if (err) formErrors.ship_pincode = err;
  }
  if (field === "opening_balance" && v < 0)
    formErrors.opening_balance = "Opening balance cannot be negative";
  if (field === "bank_account_no" && s && !/^\d{9,18}$/.test(s))
    formErrors.bank_account_no = "Account number must be 9–18 digits";
  if (field === "bank_ifsc" && s && !IFSC_REGEX.test(s))
    formErrors.bank_ifsc = "Invalid IFSC code (e.g. HDFC0001234)";
}

function validateCustomerForm() {
  Object.keys(formErrors).forEach((k) => delete formErrors[k]);
  const rule = activeRule.value;

  const cn = (form.customer_name || "").trim();
  if (!cn) formErrors.customer_name = "Display name is required";
  else if (cn.length < 2) formErrors.customer_name = "Name must be at least 2 characters";
  else if (cn.length > 100) formErrors.customer_name = "Name must not exceed 100 characters";
  if (form.customer_type !== "Individual" && !form.company_name.trim())
    formErrors.company_name = "Company name is required for " + form.customer_type + " customers";
  if (form.first_name && !/^[\p{L}\s.'\-]+$/u.test(form.first_name.trim()))
    formErrors.first_name = "First name must contain letters only";
  if (form.last_name && !/^[\p{L}\s.'\-]+$/u.test(form.last_name.trim()))
    formErrors.last_name = "Last name must contain letters only";
  if (form.email_id && !EMAIL_REGEX.test(form.email_id.trim()))
    formErrors.email_id = "Invalid email address";
  if (form.mobile_no) {
    const err = validateMobile(form.mobile_no.replace(/\D/g, ""), form.mobile_code);
    if (err) formErrors.mobile_no = err;
  }
  if (form.phone) {
    const err = validatePhone(form.phone);
    if (err) formErrors.phone = err;
  }
  if (form.website && !URL_REGEX.test(form.website.trim()))
    formErrors.website = "Website must start with http:// or https://";
  if (form.credit_limit < 0) formErrors.credit_limit = "Credit limit cannot be negative";
  if (rule.requireGstin && !form.tax_id.trim())
    formErrors.tax_id = "GSTIN is required for " + form.gst_treatment;
  else if (rule.showGstin && form.tax_id.trim() && !GSTIN_REGEX.test(form.tax_id.trim()))
    formErrors.tax_id = "Invalid GSTIN format (e.g. 27AAPFU0939F1ZV)";
  if (form.pan_no && !PAN_REGEX.test(form.pan_no.trim()))
    formErrors.pan_no = "Invalid PAN format (e.g. ABCDE1234F)";

  if (rule.requirePlaceOfSupply && !form.place_of_supply)
    formErrors.place_of_supply = "Place of Supply is required";
  if (form.opening_balance < 0) formErrors.opening_balance = "Opening balance cannot be negative";

  if (form.pincode) { const err = validatePincode(form.pincode, form.country); if (err) formErrors.pincode = err; }
  if (form.ship_pincode) { const err = validatePincode(form.ship_pincode, form.ship_country); if (err) formErrors.ship_pincode = err; }

  if (form.bank_account_no && !/^\d{9,18}$/.test(form.bank_account_no.replace(/\s/g, "")))
    formErrors.bank_account_no = "Account number must be 9–18 digits";
  if (form.bank_ifsc && !IFSC_REGEX.test(form.bank_ifsc.trim()))
    formErrors.bank_ifsc = "Invalid IFSC code (e.g. HDFC0001234)";

  return Object.keys(formErrors).length === 0;
}

const counts = computed(() => ({
  all:          list.value.length,
  active:       list.value.filter((c) => !c.disabled).length,
  disabled:     list.value.filter((c) =>  c.disabled).length,
  dealer:       list.value.filter((c) => c.customer_type === "Dealer").length,
  distributor:  list.value.filter((c) => c.customer_type === "Distributor").length,
}));

const totalOutstanding = computed(() =>
  list.value.reduce((s, c) => s + (c.outstanding || 0), 0)
);

const custKpiCards = computed(() => [
  {
    key: "total", label: "Total Customers", format: "number",
    value: counts.value.all, sub: "all customers",
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2" stroke-linecap="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
    iconBg: "#eff6ff", valueClass: "bk-kpi-blue",
  },
  {
    key: "active", label: "Active", format: "number",
    value: counts.value.active,
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2" stroke-linecap="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/><polyline points="16 11 18 13 22 9"/></svg>`,
    iconBg: "#f0fdf4", valueClass: "bk-kpi-green", sub: "enabled",
  },
  {
    key: "disabled", label: "Disabled", format: "number",
    value: counts.value.disabled, sub: "inactive",
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2" stroke-linecap="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/><line x1="18" y1="8" x2="23" y2="13"/><line x1="23" y1="8" x2="18" y2="13"/></svg>`,
    iconBg: "#fef2f2", valueClass: "bk-kpi-red",
  },
  {
    key: "outstanding", label: "Total Outstanding", format: "currency",
    value: totalOutstanding.value, sub: "receivable",
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12"/><path d="M6 8h12"/><path d="m6 13 8.5 8"/><path d="M6 13h3"/><path d="M9 13c6.667 0 6.667-10 0-10"/></svg>`,
    iconBg: "#fff7ed", valueClass: "bk-kpi-amber",
  },
]);

const groupFilter     = ref("");
const territoryFilter = ref("");

const filtered = computed(() => {
  let r = list.value;
  if (activeFilter.value === "active")      r = r.filter((c) => !c.disabled);
  if (activeFilter.value === "disabled")    r = r.filter((c) =>  c.disabled);
  if (activeFilter.value === "dealer")      r = r.filter((c) => c.customer_type === "Dealer");
  if (activeFilter.value === "distributor") r = r.filter((c) => c.customer_type === "Distributor");
  if (groupFilter.value)     r = r.filter((c) => c.customer_group === groupFilter.value);
  if (territoryFilter.value) r = r.filter((c) => c.territory === territoryFilter.value);
  const q = search.value.toLowerCase().trim();
  if (q) r = r.filter((c) =>
    (c.customer_name  || "").toLowerCase().includes(q) ||
    (c.name           || "").toLowerCase().includes(q) ||
    (c.email_id       || "").toLowerCase().includes(q) ||
    (c.mobile_no      || "").toLowerCase().includes(q) ||
    (c.tax_id         || "").toLowerCase().includes(q) ||
    (c.customer_group || "").toLowerCase().includes(q) ||
    (c.territory      || "").toLowerCase().includes(q)
  );
  return r;
});

async function load() {
  loading.value = true;
  try {
    const [rows, balances, credits, lastInvs] = await Promise.all([
      apiList("Customer", {
        fields: ["name","customer_name","customer_type","customer_group","territory","email_id","mobile_no",
          "tax_id","city","state","disabled","default_currency","credit_limit","salutation","gst_treatment"],
        order: "customer_name asc", limit: 300,
      }),
      apiGET("zoho_books_clone.api.books_data.get_customer_outstanding").catch(() => ({})),
      apiGET("zoho_books_clone.api.books_data.get_customer_unused_credits").catch(() => ({})),
      apiGET("zoho_books_clone.api.books_data.get_customer_last_invoice").catch(() => ({})),
    ]);
    lastInvoiceByCust.value = lastInvs || {};
    list.value = (rows || []).map(c => ({ ...c, outstanding: balances[c.name] || 0, unused_credits: credits[c.name] || 0 }));

    // Customer groups: "Customer Group" is not a registered doctype in this app,
    // so use the fixed Ayurvedic distributor/dealer channel list directly (no server call).
    customerGroups.value = [
      "Distributor - State", "Distributor - Zone", "Distributor - National",
      "Dealer - Local", "Dealer - Regional", "Dealer - National",
      "Wholesale", "Retail", "Institutional", "Government", "Walk-in", "Online",
    ];

    // Load territories
    try {
      const terrs = await apiList("Territory", { fields: ["name"], order: "name asc", limit: 200 }).catch(() => null);
      if (terrs && terrs.length) {
        territories.value = terrs.map(t => t.name);
      } else {
        territories.value = [
          "Tamil Nadu", "Kerala", "Karnataka", "Andhra Pradesh", "Telangana",
          "Maharashtra", "Gujarat", "Rajasthan", "Delhi", "Punjab", "All India",
        ];
      }
    } catch { territories.value = []; }
  } catch (e) {
    toast("Failed to load customers: " + (e.message || e), "error");
  } finally { loading.value = false; }
}

function resetForm() {
  drawerTab.value = "overview";
  shipSameAsBilling.value = false;
  pendingAddresses.value = [];
  Object.keys(formErrors).forEach((k) => delete formErrors[k]);
  Object.assign(form, {
    name: "", customer_name: "", customer_type: "Company", salutation: "",
    first_name: "", last_name: "", company_name: "",
    customer_group: "", territory: "",
    gst_treatment: "Registered Business",
    tax_id: "", default_currency: "INR", credit_limit: 0,
    email_id: "", mobile_code: "+91", mobile_no: "", phone: "", website: "",
    address_line1: "", address_line2: "", city: "", state: "", pincode: "", country: "India",
    ship_address_line1: "", ship_address_line2: "", ship_city: "", ship_state: "", ship_pincode: "", ship_country: "India",
    payment_terms: "", place_of_supply: "", source: "", pan_no: "", opening_balance: 0,
    tds_applicable: 0, tds_section: "",
    bank_name: "", bank_account_no: "", bank_ifsc: "", notes: "", disabled: 0,
  });
}

function openAdd() {
  resetForm();
  drawerMode.value = "add";
  showDrawer.value = true;
}

async function openEdit(name) {
  resetForm();
  drawerMode.value = "edit";
  drawerLoading.value = true;
  showDrawer.value = true;
  try {
    const doc = await apiGET("zoho_books_clone.api.docs.get_doc", { doctype: "Customer", name });
    const mno = doc.mobile_no || "";
    Object.assign(form, {
      name: doc.name,
      customer_name: doc.customer_name || "",
      customer_type: doc.customer_type || "Company",
      salutation: doc.salutation || "",
      first_name: doc.first_name || "",
      last_name: doc.last_name || "",
      company_name: doc.company_name || "",
      customer_group: doc.customer_group || "",
      territory: doc.territory || "",
      gst_treatment: doc.gst_treatment || "Registered Business",
      tax_id: doc.tax_id || "",
      default_currency: doc.default_currency || "INR",
      credit_limit: doc.credit_limit || 0,
      email_id: doc.email_id || "",
      mobile_code: mno.startsWith("+") && mno.includes(" ") ? mno.split(" ")[0] : "+91",
      mobile_no:   mno.startsWith("+") && mno.includes(" ") ? mno.substring(mno.indexOf(" ") + 1) : mno,
      phone: doc.phone || "",
      website: doc.website || "",
      address_line1: doc.address_line1 || "",
      address_line2: doc.address_line2 || "",
      city: doc.city || "",
      state: doc.state || "",
      pincode: doc.pincode || "",
      country: doc.country || "India",
      ship_address_line1: doc.ship_address_line1 || "",
      ship_address_line2: doc.ship_address_line2 || "",
      ship_city: doc.ship_city || "",
      ship_state: doc.ship_state || "",
      ship_pincode: doc.ship_pincode || "",
      ship_country: doc.ship_country || "India",
      payment_terms: doc.payment_terms || "",
      place_of_supply: doc.place_of_supply || "",
      source: doc.source || "",
      pan_no: doc.pan_no || "",
      opening_balance: doc.opening_balance || 0,
      tds_applicable: doc.tds_applicable || 0,
      tds_section: doc.tds_section || "",
      bank_name: doc.bank_name || "",
      bank_account_no: doc.bank_account_no || "",
      bank_ifsc: doc.bank_ifsc || "",
      notes: doc.notes || "",
      disabled: doc.disabled || 0,
    });
  } catch (e) {
    toast("Could not load customer: " + (e.message || e), "error");
    showDrawer.value = false;
  } finally { drawerLoading.value = false; }
}

function onShipSameChange() {
  if (shipSameAsBilling.value) {
    form.ship_address_line1 = form.address_line1;
    form.ship_address_line2 = form.address_line2;
    form.ship_city          = form.city;
    form.ship_state         = form.state;
    form.ship_pincode       = form.pincode;
    form.ship_country       = form.country;
  } else {
    form.ship_address_line1 = "";
    form.ship_address_line2 = "";
    form.ship_city          = "";
    form.ship_state         = "";
    form.ship_pincode       = "";
    form.ship_country       = "India";
  }
}

async function saveCustomer() {
  if (!validateCustomerForm()) {
    const firstErrField = Object.keys(formErrors)[0];
    if (firstErrField && FIELD_TAB[firstErrField]) drawerTab.value = FIELD_TAB[firstErrField];
    toast(Object.values(formErrors)[0], "error");
    return;
  }
  saving.value = true;
  try {
    const booksCompany = await resolveCompany();
    const doc = {
      doctype: "Customer",
      ...(drawerMode.value === "edit" ? { name: form.name } : { naming_series: "CUST-.YYYY.-.#####" }),
      books_company: booksCompany,
      customer_name: form.customer_name.trim(),
      customer_type: form.customer_type,
      customer_group: form.customer_group,
      territory: form.territory,
      salutation: form.salutation,
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      company_name: form.company_name.trim(),
      gst_treatment: form.gst_treatment,
      tax_id: form.tax_id.trim(),
      default_currency: form.default_currency,
      credit_limit: parseFloat(form.credit_limit) || 0,
      email_id: form.email_id.trim(),
      mobile_no: form.mobile_no.trim() ? (form.mobile_code + " " + form.mobile_no.trim()) : "",
      phone: form.phone.trim(),
      website: form.website.trim(),
      payment_terms: form.payment_terms,
      place_of_supply: form.place_of_supply,
      source: form.source,
      pan_no: form.pan_no.trim(),
      opening_balance: parseFloat(form.opening_balance) || 0,
      tds_applicable: form.tds_applicable ? 1 : 0,
      tds_section: form.tds_applicable ? form.tds_section : "",
      bank_name: form.bank_name.trim(),
      bank_account_no: form.bank_account_no.trim(),
      bank_ifsc: form.bank_ifsc.trim(),
      notes: form.notes.trim(),
      disabled: form.disabled ? 1 : 0,
    };
    let doc_to_save = doc;
    if (drawerMode.value === "edit") {
      const fresh = await apiGET("zoho_books_clone.api.docs.get_doc", { doctype: "Customer", name: form.name });
      doc_to_save = { ...fresh, ...doc };
    }
    const savedDoc = await apiSave(doc_to_save);
    const savedName = savedDoc?.name || form.name;

    // Flush pending addresses (add mode) → Address doctype
    if (drawerMode.value === "add" && savedName && pendingAddresses.value.length) {
      for (const addr of pendingAddresses.value) {
        try {
          await apiSave({
            doctype: "Address",
            address_title: `${savedName} - ${addr.address_type}`,
            address_type: addr.address_type,
            address_line1: addr.address_line1,
            address_line2: addr.address_line2 || "",
            city: addr.city || "", state: addr.state || "",
            pincode: addr.pincode || "", country: addr.country || "India",
            phone: addr.phone || "",
            links: [{ link_doctype: "Customer", link_name: savedName }],
          });
        } catch {}
      }
      // Sync first billing address fields onto the Customer doctype for the detail view
      const firstBilling = pendingAddresses.value.find(a => a.address_type === "Billing");
      if (firstBilling) {
        try {
          await apiSave({
            doctype: "Customer", name: savedName,
            address_line1: firstBilling.address_line1,
            address_line2: firstBilling.address_line2 || "",
            city: firstBilling.city || "", state: firstBilling.state || "",
            pincode: firstBilling.pincode || "", country: firstBilling.country || "India",
          });
        } catch {}
      }
    }

    toast(drawerMode.value === "edit" ? "Customer updated!" : "Customer created!");
    showDrawer.value = false;
    await load();
  } catch (e) {
    toast(e.message || "Could not save customer", "error");
  } finally { saving.value = false; }
}

function confirmDelete(c) {
  deleteTarget.value = c;
  showDelete.value = true;
}

async function doDelete() {
  if (!deleteTarget.value) return;
  deleting.value = true;
  try {
    const delName = deleteTarget.value.name;
    await apiPOST("zoho_books_clone.api.docs.safe_delete_party", {
      doctype: "Customer", name: delName,
    });
    toast("Customer deleted");
    showDelete.value = false;
    deleteTarget.value = null;
    if (selectedCustomer.value && selectedCustomer.value.name === delName) {
      selectedCustomer.value = null;
    }
    await load();
  } catch (e) {
    toast(e.message || "Could not delete customer", "error");
  } finally { deleting.value = false; }
}

// ── Master-detail view ──
const selectedCustomer = ref(null);
const activeCustomerTab = ref("overview");
const custTxns = ref([]);
const custTxnsLoading = ref(false);
const custTxnsLoaded  = ref(false);          // ← lazy flag
const txnPage = ref(1);                       // ← load-more page
const TXN_PAGE_SIZE = 10;
const custSectionCollapsed = reactive({ address: false, otherDetails: false });
const obInfo = ref({ has_opening_je: false });
const showPayModal = ref(false);
const payLoading = ref(false);
const payForm = reactive({ amount: 0, bank_cash_account: "", payment_date: new Date().toISOString().slice(0, 10) });

async function loadOpeningBalance() {
  if (!selectedCustomer.value) return;
  obInfo.value = await apiGET(
    "zoho_books_clone.accounts.opening_balance.get_opening_balance_payment_info",
    { party_type: "Customer", party: selectedCustomer.value.name }
  ).catch(() => ({ has_opening_je: false }));
}

function openPayModal() {
  payForm.amount = obInfo.value.outstanding;
  payForm.bank_cash_account = obInfo.value.bank_cash_accounts?.[0]?.name || "";
  payForm.payment_date = new Date().toISOString().slice(0, 10);
  showPayModal.value = true;
}

async function submitPayment() {
  const amount = Number(payForm.amount);
  if (!payForm.bank_cash_account) { toast("Choose an account to pay into", "error"); return; }
  if (!amount || amount <= 0) { toast("Enter a valid amount", "error"); return; }
  if (amount > obInfo.value.outstanding + 0.01) { toast("Amount exceeds outstanding opening balance", "error"); return; }

  payLoading.value = true;
  try {
    const doc = {
      doctype: "Payment Entry",
      payment_type: "Receive",
      party_type: "Customer",
      party: selectedCustomer.value.name,
      party_name: selectedCustomer.value.customer_name,
      company: obInfo.value.company,
      paid_from: obInfo.value.party_account,
      paid_to: payForm.bank_cash_account,
      paid_amount: amount,
      received_amount: amount,
      payment_date: payForm.payment_date,
      remarks: `Opening balance payment for ${selectedCustomer.value.customer_name || selectedCustomer.value.name}`,
      references: [{
        reference_doctype: "Journal Entry",
        reference_name: obInfo.value.journal_entry,
        allocated_amount: amount,
      }],
    };
    const saved = await apiSave(doc);
    await apiSubmit("Payment Entry", saved.name);
    toast("Payment recorded", "success");
    showPayModal.value = false;
    await loadOpeningBalance();

    // Refresh outstanding balances everywhere they're shown — the sidebar
    // list, the RECEIVABLES card, and (if open) the Transactions/Statement
    // tabs — otherwise they keep showing the pre-payment amount until a
    // full page reload.
    await load();
    const updated = list.value.find(c => c.name === selectedCustomer.value.name);
    if (updated) selectedCustomer.value = { ...selectedCustomer.value, outstanding: updated.outstanding };

    custTxnsLoaded.value = false;
    if (activeCustomerTab.value === "transactions") await loadTransactions();
    stmtLoaded.value = false;
    if (activeCustomerTab.value === "statement") await loadStatement();
  } catch (e) {
    toast(e.message || "Failed to record payment", "error");
  } finally {
    payLoading.value = false;
  }
}

async function loadTransactions() {
  if (!selectedCustomer.value || custTxnsLoaded.value) return;
  custTxnsLoading.value = true;
  try {
    const txns = await apiGET("zoho_books_clone.api.docs.get_customer_transactions", {
      customer: selectedCustomer.value.name, limit: 100,
    }).catch(() => []);
    custTxns.value = txns || [];
    custTxnsLoaded.value = true;
  } catch (e) { /* keep panel open */ }
  custTxnsLoading.value = false;
}

async function selectCustomer(c) {
  selectedCustomer.value = c;
  activeCustomerTab.value = "overview";
  stmt.value        = null;
  stmtLoaded.value  = false;
  stmtPage.value    = 1;
  custTxns.value    = [];
  custTxnsLoaded.value = false;
  txnPage.value     = 1;
  Object.assign(custSectionCollapsed, { address: false, otherDetails: false });
  obInfo.value = { has_opening_je: false };
  loadOpeningBalance();
  // Only load the full customer doc (lightweight) — tabs load on demand
  custTxnsLoading.value = true;
  try {
    const fullDoc = await apiGET("zoho_books_clone.api.docs.get_doc", {
      doctype: "Customer", name: c.name,
    }).catch(() => null);
    if (fullDoc) selectedCustomer.value = { ...c, ...fullDoc, outstanding: c.outstanding || 0, unused_credits: c.unused_credits || 0 };
  } catch (e) { /* keep panel open */ }
  custTxnsLoading.value = false;
}
function closeCustomer()   { selectedCustomer.value = null; showPayModal.value = false; }
function custInitials(name) {
  return (name || "?").split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2);
}

// ── Customer Statement ──
const stmt        = ref(null);
const stmtLoading = ref(false);
const stmtLoaded  = ref(false);             // ← lazy flag
const stmtPage    = ref(1);                 // ← load-more page
const STMT_PAGE_SIZE = 10;
const sendingStmt = ref(false);
const fmtStmt = (v) => Number(v||0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

// ── Load-more computed slices ──
const custTxnsActive    = computed(() => custTxns.value.filter((t) => t.docstatus !== 2 && t.status !== "Cancelled"));
const custTxnsVisible   = computed(() => custTxnsActive.value.slice(0, txnPage.value * TXN_PAGE_SIZE));
const custTxnsHasMore   = computed(() => custTxnsActive.value.length > txnPage.value * TXN_PAGE_SIZE);
const stmtInvsVisible   = computed(() => stmt.value ? stmt.value.invoices.slice(0, stmtPage.value * STMT_PAGE_SIZE) : []);
const stmtInvsHasMore   = computed(() => stmt.value ? stmt.value.invoices.length > stmtPage.value * STMT_PAGE_SIZE : false);


async function loadStatement() {
  if (!selectedCustomer.value || stmtLoaded.value) return;
  stmtLoading.value = true;
  try {
    const co = await resolveCompany();
    stmt.value = await apiGET("zoho_books_clone.db.queries.get_customer_statement", {
      customer: selectedCustomer.value.name, company: co,
    });
    stmtLoaded.value = true;
  } catch (e) { toast("Could not load statement: " + e.message, "error"); }
  stmtLoading.value = false;
}

async function sendStatement() {
  if (!selectedCustomer.value || !stmt.value) return;
  sendingStmt.value = true;
  try {
    const co = await resolveCompany();
    await apiPOST("zoho_books_clone.db.queries.send_customer_statement", {
      customer: selectedCustomer.value.name, company: co,
    });
    toast("Statement sent to " + stmt.value.email);
  } catch (e) { toast(e.message || "Failed to send statement", "error"); }
  sendingStmt.value = false;
}

watch(activeCustomerTab, (t) => {
  if (t === "transactions" && !custTxnsLoaded.value) loadTransactions();
  if (t === "statement"    && !stmtLoaded.value)     loadStatement();
});

// ── Bulk actions ────────────────────────────────────────────────────────────
async function bulkSetDisabled(disable) {
  if (!canWrite("customers")) { toast("Read-only access", "error"); return; }
  const names = [...selectedRows.value];
  if (!names.length) { toast("No customers selected", "info"); return; }
  bulkBusy.value = true;
  try {
    const { apiPOST } = await import("../api/client.js");
    await apiPOST("zoho_books_clone.api.docs.bulk_set_customer_disabled", {
      customer_names: JSON.stringify(names),
      disabled: disable ? 1 : 0,
    });
    toast(`${disable ? "Disabled" : "Enabled"} ${names.length} customer(s)`, "success");
    clearSelection();
    await load();
  } catch (e) { toast(e.message || "Bulk update failed", "error"); }
  finally { bulkBusy.value = false; }
}

function exportCSV() {
  const rows = selectedRows.value.size
    ? filtered.value.filter(c => selectedRows.value.has(c.name))
    : filtered.value;
  if (!rows.length) { toast("Nothing to export", "info"); return; }
  const headers = ["Customer","Name","Type","GSTIN","Email","Mobile","City","State","Status"];
  const data = rows.map(c => [
    c.name, c.customer_name || "", c.customer_type || "",
    c.tax_id || "", c.email_id || "", c.mobile_no || "",
    c.city || "", c.state || "",
    c.disabled ? "Disabled" : "Active",
  ]);
  const esc = v => { const s = v == null ? "" : String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  const csv = "﻿" + [headers, ...data].map(r => r.map(esc).join(",")).join("\r\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `customers-${new Date().toISOString().slice(0,10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
  toast(`${rows.length} row(s) exported`, "success");
}

// ── CSV Import ───────────────────────────────────────────────────────────────
function triggerImport() { importInput.value && importInput.value.click(); }

// Minimal RFC-4180-ish CSV row parser (handles quoted fields with commas)
function parseCsvLine(line) {
  const out = []; let cur = ""; let inQ = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQ) {
      if (ch === '"' && line[i + 1] === '"') { cur += '"'; i++; }
      else if (ch === '"') inQ = false;
      else cur += ch;
    } else {
      if (ch === '"') inQ = true;
      else if (ch === ",") { out.push(cur); cur = ""; }
      else cur += ch;
    }
  }
  out.push(cur);
  return out.map(s => s.trim());
}

// Map existing display names (lowercased) → Customer id, for upsert matching
function buildExistingNameMap() {
  const m = {};
  for (const c of list.value) {
    const key = (c.customer_name || "").trim().toLowerCase();
    if (key && !(key in m)) m[key] = c.name;
  }
  return m;
}

// Phase 1: parse the CSV, classify each row as new/update, open the preview dialog
async function importCSV(e) {
  const file = e.target.files && e.target.files[0];
  if (importInput.value) importInput.value.value = ""; // allow re-selecting same file
  if (!file) return;
  try {
    const text = await file.text();
    const lines = text.replace(/^﻿/, "").split(/\r?\n/).filter(l => l.trim().length);
    if (lines.length < 2) { toast("CSV has no data rows", "error"); return; }
    const header = parseCsvLine(lines[0]).map(h => h.toLowerCase());
    const idx = (...names) => { for (const n of names) { const i = header.indexOf(n); if (i !== -1) return i; } return -1; };
    const col = {
      name:    idx("name", "customer", "customer name", "display name"),
      type:    idx("type", "customer type"),
      gstin:   idx("gstin", "gstin / tax id", "tax id", "tax_id"),
      email:   idx("email", "email address", "email_id"),
      mobile:  idx("mobile", "mobile no", "phone"),
      city:    idx("city"),
      state:   idx("state"),
    };
    if (col.name === -1) { toast('CSV must have a "Name" or "Customer Name" column', "error"); return; }

    const existing = buildExistingNameMap();
    const rows = [];
    for (let r = 1; r < lines.length; r++) {
      const cells = parseCsvLine(lines[r]);
      const cname = (cells[col.name] || "").trim();
      if (!cname) continue;
      const rawType = col.type !== -1 ? (cells[col.type] || "").trim() : "";
      const ctype = CUSTOMER_TYPES.includes(rawType) ? rawType : "Company";
      const existingName = existing[cname.toLowerCase()] || "";
      rows.push({
        cname, ctype,
        gstin:  col.gstin  !== -1 ? (cells[col.gstin]  || "").trim().toUpperCase() : "",
        email:  col.email  !== -1 ? (cells[col.email]  || "").trim() : "",
        mobile: col.mobile !== -1 ? (cells[col.mobile] || "").trim() : "",
        city:   col.city   !== -1 ? (cells[col.city]   || "").trim() : "",
        state:  col.state  !== -1 ? (cells[col.state]  || "").trim() : "",
        action: existingName ? "update" : "new",
        existingName,
      });
    }
    if (!rows.length) { toast("No valid rows found in CSV", "error"); return; }
    importModal.rows = rows;
    importModal.done = false;
    importModal.running = false;
    importModal.result = { created: 0, updated: 0, failed: 0 };
    importModal.open = true;
  } catch (err) {
    toast(err.message || "Could not read CSV file", "error");
  }
}

const importCounts = computed(() => ({
  total:  importModal.rows.length,
  create: importModal.rows.filter(r => r.action === "new").length,
  update: importModal.rows.filter(r => r.action === "update").length,
}));
const importPreviewRows = computed(() => importModal.rows.slice(0, 200));

function closeImport() {
  if (importModal.running) return;
  importModal.open = false;
  importModal.rows = [];
}

// Build the save payload. On update, blank cells are omitted so existing data is kept.
function buildImportPayload(row, isUpdate) {
  const p = { customer_name: row.cname, customer_type: row.ctype };
  if (row.ctype !== "Individual") p.company_name = row.cname;
  const setIf = (k, v) => { if (!isUpdate || (v !== "" && v != null)) p[k] = v; };
  setIf("tax_id", row.gstin);
  setIf("email_id", row.email);
  setIf("mobile_no", row.mobile);
  setIf("city", row.city);
  setIf("state", row.state);
  if (!isUpdate) {
    p.default_currency = "INR";
    p.gst_treatment = row.gstin ? "Registered Business" : "Unregistered Business";
  } else if (row.gstin) {
    p.gst_treatment = "Registered Business";
  }
  return p;
}

// Phase 2: execute the upsert, then show the summary
async function runImport() {
  if (!importModal.rows.length || importModal.running) return;
  importModal.running = true;
  let created = 0, updated = 0, failed = 0;
  try {
    const booksCompany = await resolveCompany();
    for (const row of importModal.rows) {
      try {
        if (row.action === "update" && row.existingName) {
          const fresh = await apiGET("zoho_books_clone.api.docs.get_doc", { doctype: "Customer", name: row.existingName });
          await apiSave({ ...fresh, ...buildImportPayload(row, true), doctype: "Customer", name: row.existingName });
          updated++;
        } else {
          await apiSave({ doctype: "Customer", naming_series: "CUST-.YYYY.-.#####", books_company: booksCompany, ...buildImportPayload(row, false) });
          created++;
        }
      } catch { failed++; }
    }
  } finally {
    importModal.result = { created, updated, failed };
    importModal.running = false;
    importModal.done = true;
    await load();
  }
}

function bulkEmail() {
  if (!canWrite("customers")) { toast("Read-only access", "error"); return; }
  const rows = [...selectedRows.value]
    .map(n => list.value.find(c => c.name === n))
    .filter(c => c && c.email_id);
  if (!rows.length) { toast("No selected customers have an email address", "info"); return; }
  const emails = rows.map(c => c.email_id).join(",");
  // Compose a mailto: with all selected recipients
  window.location.href = `mailto:?bcc=${encodeURIComponent(emails)}`;
  toast(`Composing email to ${rows.length} customer(s)`, "info");
}

onMounted(load);
</script>

<style scoped>
.cus-pay-modal-overlay{position:fixed;inset:0;background:rgba(15,23,42,.45);display:flex;align-items:center;justify-content:center;z-index:100;}
.cus-pay-modal{background:#fff;border-radius:12px;padding:22px;width:340px;box-shadow:0 10px 30px rgba(0,0,0,.15);}
/* ── Drawer slide-in animation ──────────────────────────── */
.inv-drawer-panel {
  width: 680px;
  max-width: 98vw;
  transform: translateX(100%);
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.inv-drawer-panel.open {
  transform: translateX(0);
}

/* ── Customer avatar circle ─────────────────────────────── */
.vt-vendor-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}
.vt-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  flex-shrink: 0;
  background: linear-gradient(135deg, #16a34a, #15803d);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.03em;
}
.vt-avatar-disabled { background: #d1d5db; }
.vt-vendor-name {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
  line-height: 1.3;
}
.vt-vendor-id {
  font-size: 11.5px;
  color: #9ca3af;
  margin-top: 1px;
}

/* ── Customer-specific column helpers ───────────────────── */
.vt-th {
  padding: 10px 14px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
  white-space: nowrap;
  user-select: none;
}
.vt-th-actions { text-align: center; width: 88px; }
.vt-td {
  padding: 11px 14px;
  vertical-align: middle;
  color: #374151;
  white-space: nowrap;
}
.vt-td-mono      {font-size: 12px; color: #374151; }
.vt-td-secondary { color: #6b7280; font-size: 12.5px; }
.vt-td-actions   { text-align: center; width: 88px; }
.vt-checkbox { width: 15px; height: 15px; accent-color: #16a34a; cursor: pointer; border-radius: 3px; }
.vt-row-shimmer td { padding: 13px 14px; }
.vt-row-disabled   { opacity: 0.55; }
.vt-row-selected   { background: #f0fdf4 !important; }
.vt-actions {
  display: flex;
  gap: 3px;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.12s;
}
.inv-row:hover .vt-actions { opacity: 1; }
.vt-act-edit:hover { background: #eff6ff; color: #2563eb; border-color: #bfdbfe; }
.vt-act-del:hover  { background: #fef2f2; color: #dc2626; border-color: #fecaca; }
.vt-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 9px;
  border-radius: 20px;
  font-size: 11.5px;
  font-weight: 500;
  white-space: nowrap;
  line-height: 1.6;
}
.vt-badge-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.vt-badge-green             { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
.vt-badge-green .vt-badge-dot { background: #22c55e; }
.vt-badge-red               { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
.vt-badge-red   .vt-badge-dot { background: #ef4444; }
.vt-badge-blue  { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
.vt-badge-gray  { background: #f9fafb; color: #6b7280; border: 1px solid #e5e7eb; }
.vt-badge-amber { background: #fff7ed; color: #b45309; border: 1px solid #fed7aa; }

/* ── Outstanding / Last Invoice columns ── */
.vt-th-num { text-align: right; }
.vt-td-num { text-align: right; white-space: nowrap; }
.vt-amount-due { color: #dc2626; font-weight: 700; font-size: 13px; }
.vt-amount-nil { color: #9ca3af; }
.vt-lastinv-ref  { font-size: 12px; font-weight: 600; color: #2563eb; }
.vt-lastinv-date { font-size: 11px; color: #9ca3af; margin-top: 1px; }

/* ── CSV Import dialog ── */
.cus-import-stats { display: flex; gap: 10px; margin-bottom: 14px; }
.cus-import-stat {
  flex: 1; text-align: center; padding: 12px 8px; border-radius: 10px;
  background: #f8fafc; border: 1px solid #e5e7eb;
}
.cus-import-stat-val { font-size: 22px; font-weight: 800; color: #111827; line-height: 1; }
.cus-import-stat-lbl { font-size: 11px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: .04em; margin-top: 5px; }
.cus-import-stat-new  { background: #f0fdf4; border-color: #bbf7d0; }
.cus-import-stat-new  .cus-import-stat-val { color: #15803d; }
.cus-import-stat-upd  { background: #eff6ff; border-color: #bfdbfe; }
.cus-import-stat-upd  .cus-import-stat-val { color: #1d4ed8; }
.cus-import-stat-fail { background: #fef2f2; border-color: #fecaca; }
.cus-import-stat-fail .cus-import-stat-val { color: #b91c1c; }
.cus-import-note {
  font-size: 12px; color: #6b7280; line-height: 1.5;
  background: #fafbfd; border: 1px solid #eef1f5; border-radius: 8px;
  padding: 9px 12px; margin-bottom: 12px;
}
.cus-import-table-wrap { max-height: 320px; overflow-y: auto; border: 1px solid #e5e7eb; border-radius: 8px; }
.cus-import-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.cus-import-table th {
  position: sticky; top: 0; background: #f9fafb; z-index: 1;
  text-align: left; font-size: 10.5px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .04em; color: #9ca3af; padding: 8px 12px; border-bottom: 1px solid #e5e7eb;
}
.cus-import-table td { padding: 8px 12px; border-bottom: 1px solid #f3f4f6; vertical-align: middle; }
.cus-import-name { font-weight: 600; color: #111827; }
.cus-import-sub  { font-size: 11px; color: #9ca3af; margin-top: 1px; }
.cus-import-mono { font-family: var(--mono); font-size: 11.5px; color: #374151; }
.cus-import-badge { font-size: 10.5px; font-weight: 700; padding: 2px 9px; border-radius: 12px; }
.cus-import-badge-new { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
.cus-import-badge-upd { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
.cus-import-more { padding: 8px 12px; font-size: 11.5px; color: #9ca3af; text-align: center; background: #fafbfd; }
.vt-empty { padding: 52px 24px; text-align: center; }
.vt-empty-icon {
  margin: 0 auto 14px; width: 56px; height: 56px; border-radius: 14px;
  background: #f9fafb; border: 1px solid #e5e7eb;
  display: flex; align-items: center; justify-content: center;
}
.vt-empty-title { font-size: 14px; font-weight: 600; color: #374151; margin-bottom: 5px; }
.vt-empty-sub   { font-size: 13px; color: #9ca3af; }
.vt-footer { padding: 9px 16px; border-top: 1px solid #f3f4f6; font-size: 12px; color: #9ca3af; background: #fafafa; }
.vt-footer strong { color: #6b7280; font-weight: 600; }

/* ── Mobile number field: prevent inv-fi width:100% from overriding select ── */
.cus-mobile-row { display: flex; gap: 0; }
.cus-mobile-code.inv-fi { width: 90px !important; flex-shrink: 0 !important; min-width: 0 !important; box-sizing: border-box; }
.cus-mobile-row .inv-fi:not(.cus-mobile-code) { flex: 1 !important; width: 0 !important; min-width: 0 !important; }

/* ── Load More ── */
.cus-load-more-wrap {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  margin-top: 8px;
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: 10px;
}
.cus-load-more-end {
  justify-content: center;
  font-size: 12px;
  color: #9CA3AF;
  font-style: italic;
}
.cus-load-more-count {
  font-size: 12px;
  color: #6B7280;
}
.cus-load-more-btn {
  font-size: 12.5px;
  font-weight: 600;
  color: #2563EB;
  background: #EFF6FF;
  border: 1px solid #BFDBFE;
  border-radius: 7px;
  padding: 5px 14px;
  cursor: pointer;
  font-family: inherit;
  transition: background .12s;
}
.cus-load-more-btn:hover { background: #DBEAFE; }

/* ── Skeleton shimmer ── */
@keyframes cus-shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
.cus-sk-base {
  background: linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%);
  background-size: 200% 100%;
  animation: cus-shimmer 1.4s infinite;
  border-radius: 6px;
}
.cus-sk-pill  { width: 64px; height: 22px; flex-shrink: 0; border-radius: 10px; }
.cus-sk-line  { height: 13px; border-radius: 4px; }
.cus-sk-line-sm  { width: 80px; }
.cus-sk-line-md  { width: 140px; }
.cus-sk-line-lg  { width: 100px; height: 22px; border-radius: 5px; }
.cus-sk-pill, .cus-sk-line {
  background: linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%);
  background-size: 200% 100%;
  animation: cus-shimmer 1.4s infinite;
}
.cus-txn-skeleton {
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: 10px;
  overflow: hidden;
}
.cus-txn-sk-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 13px 16px;
  border-bottom: 1px solid #F3F4F6;
}
.cus-txn-sk-row:last-child { border-bottom: none; }
.cus-stmt-sk-kpis {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 14px;
}
.cus-stmt-sk-kpi {
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: 10px;
  padding: 14px 16px;
}

/* ── Mobile card view (Option A) ── */
.cus-mobile-cards { display: none; }
.cus-desktop-table { display: table; }

/* Mobile card views: hidden by default, shown only ≤768px */
.cus-txn-mobile-cards { display: none; }
.cus-stmt-mobile-cards { display: none; }

@media (max-width: 768px) {
  .cus-desktop-table { display: none !important; }
  .cus-mobile-cards { display: flex; flex-direction: column; gap: 0; background: #f8fafc; }
  .cus-mobile-card { background: #fff; border-bottom: 1px solid #e5e7eb; padding: 12px 14px; cursor: pointer; transition: background .12s; }
  .cus-mobile-card:active { background: #f8f9fc; }
  .cus-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
  .cus-mc-name { font-size: 14px; font-weight: 700; color: #1a1d23; }
  .cus-mc-meta { display: flex; justify-content: space-between; font-size: 12px; color: #868e96; margin-bottom: 8px; }
  .cus-mc-footer { display: flex; gap: 6px; }
  .cus-mc-btn { flex: 1; padding: 6px 10px; border-radius: 7px; font-size: 12px; font-weight: 600; cursor: pointer; background: #f1f5f9; border: 1px solid #e2e8f0; color: #374151; }
  .cus-mc-danger { background: #fff1f2; border-color: #fecaca; color: #dc2626; }
  .cus-mc--skeleton { pointer-events: none; }
  .cus-mc-shimmer { border-radius: 6px; background: linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size: 200% 100%; animation: cus-shimmer 1.4s infinite; }
  @keyframes cus-shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
  .cus-mc-empty { text-align: center; padding: 32px 16px; color: #868e96; font-size: 13px; }

  /* ── Detail panel: hide left pane, go full-width ── */
  .zb-master-detail { flex-direction: column !important; height: auto !important; min-height: calc(100vh - 56px); }
  .zb-list-pane { display: none !important; }

  /* ── Overview: stack two columns vertically ── */
  .cus-overview-cols { flex-direction: column !important; }
  .cus-overview-cols > div { flex: none !important; width: 100% !important; min-width: 0 !important; }

  /* ── Receivables table: compact + wrap headers ── */
  .cus-recv-table th {
    font-size: 9.5px !important;
    padding: 6px 8px !important;
    white-space: normal !important;
    word-break: break-word !important;
    line-height: 1.3 !important;
  }
  .cus-recv-table td { font-size: 12px !important; padding: 8px !important; }

  /* (mobile-card defaults declared above this media query, before the breakpoint) */
  /* ── Transactions tab: switch to card view ── */
  .cus-txn-wrap { overflow: visible !important; border: none !important; background: transparent !important; }
  .cus-txn-desktop { display: none !important; }

  /* ── Statement tab: 1-col KPI grid + card view for invoices ── */
  .cus-stmt-kpis { grid-template-columns: 1fr !important; gap: 8px !important; }
  .cus-stmt-sk-kpis { grid-template-columns: 1fr !important; gap: 8px !important; }
  .cus-stmt-inv-wrap { overflow: visible !important; }
  .cus-stmt-desktop { display: none !important; }

  /* ── New/Edit Customer form: stack multi-col grids to 1 col ── */
  /* Class-based (scoped — these work when the class is on this component's elements) */
  .cus-form-grid2 { grid-template-columns: 1fr !important; }
  .cus-form-grid3 { grid-template-columns: 1fr !important; }
  /* Inline-style grids directly in this template (attr selector beats inline without !important) */
  [style*="grid-template-columns:1fr 1fr"],
  [style*="grid-template-columns: 1fr 1fr"],
  [style*="grid-template-columns:1fr 1fr 1fr"],
  [style*="grid-template-columns: 1fr 1fr 1fr"] {
    grid-template-columns: 1fr !important;
  }

  :deep(.inv-add-drawer),
  :deep(.cus-add-drawer) {
    width: 100vw !important;
    right: -100vw !important;
    max-width: 100vw !important;
  }
  :deep(.inv-add-drawer.open),
  :deep(.cus-add-drawer.open) { right: 0 !important; }

  /* ── Tab bar: scrollable, no wrapping ── */
  :deep(.inv-view-tabs) {
    overflow-x: auto !important;
    flex-wrap: nowrap !important;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    padding-bottom: 0;
  }
  :deep(.inv-view-tabs)::-webkit-scrollbar { display: none; }
  :deep(.inv-vtab) {
    flex-shrink: 0 !important;
    white-space: nowrap !important;
    font-size: 12.5px !important;
    padding: 8px 12px !important;
  }

  /* ── Bank Details grid: force single column (overrides inline style) ── */
  .cus-bank-grid {
    grid-template-columns: 1fr !important;
  }
  .cus-bank-full {
    grid-column: span 1 !important;
  }

  /* ── Drawer footer: sticky, proper row layout ── */
  :deep(.inv-dfooter) {
    display: flex !important;
    flex-direction: row !important;
    gap: 8px !important;
    padding: 12px 14px !important;
    position: sticky;
    bottom: 0;
    background: #fafbfd;
    border-top: 1px solid #e8ecf0;
    z-index: 10;
  }
  :deep(.inv-dfooter) .form-btn {
    flex: 1 !important;
    min-width: 0 !important;
    font-size: 13px !important;
    padding: 10px 8px !important;
    text-align: center !important;
    justify-content: center !important;
  }
  :deep(.inv-dfooter) .form-btn-primary {
    flex: 2 !important;
  }

  /* ── Transactions: mobile cards ── */
  .cus-txn-mobile-cards { display: flex; flex-direction: column; gap: 8px; }
  .cus-txn-mc { background: #fff; border: 1px solid #E5E7EB; border-radius: 10px; padding: 12px 14px; }
  .cus-txn-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
  .cus-txn-mc-badge { font-size: 10.5px; font-weight: 700; padding: 2px 8px; border-radius: 10px; }
  .cus-txn-mc-amount { font-size: 14px; font-weight: 700; }
  .cus-txn-mc-mid { display: flex; align-items: center; justify-content: space-between; }
  .cus-txn-mc-ref { font-size: 13px; font-weight: 600; color: #2563EB; }
  .cus-txn-mc-date { font-size: 12px; color: #6B7280; }
  .cus-txn-mc-outstanding { margin-top: 8px; padding-top: 8px; border-top: 1px solid #F3F4F6; font-size: 12px; color: #dc2626; }

  /* ── Statement: mobile cards ── */
  .cus-stmt-mobile-cards { display: flex; flex-direction: column; gap: 8px; padding: 8px; }
  .cus-stmt-mc { background: #fff; border: 1px solid #E5E7EB; border-radius: 10px; padding: 12px 14px; }
  .cus-stmt-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
  .cus-stmt-mc-name { font-size: 13.5px; font-weight: 600; color: #2563EB; }
  .cus-stmt-mc-badge { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 10px; }
  .cus-stmt-mc-mid { display: flex; align-items: center; justify-content: space-between; font-size: 12px; color: #6B7280; margin-bottom: 6px; }
  .cus-stmt-mc-amount { font-size: 15px; font-weight: 700; color: #111827; text-align: right; }
}

@media (max-width: 480px) {
  .view-toggle-btn { display: none !important; }
}
</style>