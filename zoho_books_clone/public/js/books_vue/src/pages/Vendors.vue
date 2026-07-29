<template>
<div>

  <!-- ── FLAT TABLE VIEW (default, nothing selected) ── -->
  <div v-if="!selectedVendor" class="list-page">
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
        <select v-if="supplierGroups.length" class="sales-select" v-model="groupFilterV" title="Filter by supplier group">
          <option value="">All Groups</option>
          <option v-for="g in supplierGroups" :key="g" :value="g">{{ g }}</option>
        </select>
        <div class="sales-search">
          <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
          <input v-model="search" placeholder="Search vendors…" class="sales-search-input" autocomplete="off"/>
        </div>
        <button class="sales-btn-ghost view-toggle-btn" @click="viewMode=viewMode==='table'?'grid':'table'" :title="viewMode==='table'?'Grid View':'List View'"><span v-html="icon(viewMode==='table'?'grid':'file',14)"></span></button>
        <button class="sales-btn-ghost" @click="triggerImport" title="Import vendors from CSV"><span v-html="icon('upload',13)"></span> Import</button>
        <button class="sales-btn-ghost" @click="exportCSV" title="Export CSV"><span v-html="icon('download',13)"></span> Export</button>
        <button class="sales-btn-ghost" @click="load" title="Refresh"><span v-html="icon('refresh',13)"></span> Refresh</button>
        <button class="sales-btn-primary" :disabled="!$canWrite('customers')" :title="!$canWrite('customers') ? 'Read-only access' : ''" @click="openAdd"><span v-html="icon('plus',13)"></span> New Vendor</button>
        <input ref="importInput" type="file" accept=".csv,text/csv" style="display:none" @change="importCSV" />
      </div>
    </div>

    <!-- ── KPI Cards ── -->
    <div class="bk-kpi-grid bk-kpi-grid-4" style="margin-bottom:18px">
      <div v-for="kpi in vendorKpiCards" :key="kpi.key" class="bk-kpi-card">
        <div class="bk-kpi-inner">
          <div class="bk-kpi-icon" :style="{ background: kpi.iconBg }"><span v-html="kpi.icon"></span></div>
          <div class="bk-kpi-body">
            <div class="bk-kpi-label">{{ kpi.label }}</div>
            <div class="bk-kpi-value" :class="kpi.valueClass">
              <template v-if="loading"><div class="b-shimmer" style="width:64px;height:22px;margin-top:2px;border-radius:4px"></div></template>
              <template v-else>{{ kpi.format === 'currency' ? fmtCur(kpi.value) : kpi.value }}</template>
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
      <button class="inv-bulk-btn" @click="triggerImport" :disabled="bulkBusy">
        <span v-html="icon('upload',13)"></span> Import CSV
      </button>
      <button class="inv-bulk-clear" @click="clearSelection">✕ Clear</button>
    </div>

    <div class="inv-table-wrap">
      <!-- TABLE MODE -->
      <div v-if="viewMode==='table'" class="inv-table-wrap">
        <table class="inv-table ven-desktop-table">
          <thead>
            <tr>
              <th class="vt-th vt-th-check">
                <input type="checkbox" class="vt-checkbox" :checked="filtered.length>0 && filtered.every(v=>selectedRows.has(v.name))" @change="e=>e.target.checked ? selectedRows=new Set(filtered.map(v=>v.name)) : clearSelection()" />
              </th>
              <th class="vt-th">Vendor Name</th>
              <th class="vt-th">Type</th>
              <th class="vt-th">Group</th>
              <th class="vt-th">GSTIN</th>
              <th class="vt-th vt-th-num">Outstanding</th>
              <th class="vt-th">Last Bill</th>
              <th class="vt-th">Mobile</th>
              <th class="vt-th">Status</th>
              <th class="vt-th vt-th-actions">Actions</th>
            </tr>
          </thead>
          <tbody>
            <template v-if="loading">
              <tr v-for="n in 6" :key="n" class="vt-row-shimmer">
                <td colspan="11"><div class="shimmer" style="height:12px;border-radius:3px;width:65%"></div></td>
              </tr>
            </template>
            <tr v-else-if="!filtered.length">
              <td colspan="11" class="vt-empty">
                <div class="vt-empty-icon">
                  <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" stroke-width="1.3"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                </div>
                <div class="vt-empty-title">{{search ? 'No results found' : 'No vendors yet'}}</div>
                <div class="vt-empty-sub">{{search ? 'Try adjusting your search or filter' : 'Add your first vendor to get started'}}</div>
                <button v-if="!search" class="nim-btn nim-btn-primary" :disabled="!$canWrite('customers')" :title="!$canWrite('customers') ? 'Read-only access' : ''" style="margin-top:14px" @click="openAdd"><span v-html="icon('plus',13)"></span> New Vendor</button>
              </td>
            </tr>
            <tr v-else v-for="v in filtered" :key="v.name"
              class="inv-row"
              :class="[v.disabled ? 'vt-row-disabled' : '', selectedRows.has(v.name) ? 'vt-row-selected' : '']"
              @click="selectVendor(v)">
              <td class="vt-td vt-td-check" @click.stop>
                <input type="checkbox" class="vt-checkbox" :checked="selectedRows.has(v.name)" @change="toggleRow(v.name)" />
              </td>
              <td class="vt-td vt-td-vendor">
                <div class="vt-vendor-cell">
                  <div class="vt-avatar" :class="v.disabled ? 'vt-avatar-disabled' : ''">{{vendorInitials(v.supplier_name)}}</div>
                  <div>
                    <div class="vt-vendor-name inv-customer">{{v.supplier_name||v.name}}</div>
                    <div class="vt-vendor-id">{{v.name}}</div>
                  </div>
                </div>
              </td>
              <td class="vt-td">
                <span class="vt-badge"
                  :style="STYPE_META[v.supplier_type] ? { background: STYPE_META[v.supplier_type].bg, color: STYPE_META[v.supplier_type].text, border: 'none' } : {}">
                  {{ STYPE_META[v.supplier_type]?.icon || '' }} {{v.supplier_type||'—'}}
                </span>
              </td>
              <td class="vt-td vt-td-secondary">
                <div v-if="v.supplier_group" style="font-size:12px;font-weight:600;color:#374151">{{ v.supplier_group }}</div>
                <span v-else>—</span>
              </td>
              <td class="vt-td vt-td-mono">
                <span v-if="v.tax_id">{{v.tax_id}}</span>
                <span v-else class="vt-badge vt-badge-amber">Unregistered</span>
              </td>
              <td class="vt-td vt-td-num">
                <span :class="(balancesByVendor[v.name]||0)>0 ? 'vt-amount-due' : 'vt-amount-nil'">
                  {{ (balancesByVendor[v.name]||0)>0 ? fmtCur(balancesByVendor[v.name]) : '—' }}
                </span>
              </td>
              <td class="vt-td vt-td-secondary">
                <template v-if="lastBillByVendor[v.name]">
                  <div class="vt-lastinv-ref" @click.stop><DocLink doctype="Purchase Invoice" :name="lastBillByVendor[v.name].name" /></div>
                  <div class="vt-lastinv-date">{{ fmtDate(lastBillByVendor[v.name].date) }} · {{ fmtCur(lastBillByVendor[v.name].amount) }}</div>
                </template>
                <span v-else>—</span>
              </td>
              <td class="vt-td vt-td-secondary">{{v.mobile_no||'—'}}</td>
              <td class="vt-td">
                <span class="inv-status-badge" :class="v.disabled ? 'vt-badge-red' : 'vt-badge-green'">
                  <span class="vt-badge-dot"></span>{{v.disabled ? 'Disabled' : 'Active'}}
                </span>
              </td>
              <td class="vt-td vt-td-actions" @click.stop>
                <div class="vt-actions">
                  <button class="inv-act-btn vt-act-edit" @click="openEdit(v.name)" title="Edit"><span v-html="icon('edit',13)"></span></button>
                  <button class="inv-act-btn vt-act-del" @click="confirmDelete(v)" title="Delete"><span v-html="icon('trash',13)"></span></button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Mobile cards (shown at ≤768px) -->
        <div class="ven-mobile-cards">
          <template v-if="loading">
            <div v-for="n in 5" :key="n" class="ven-mobile-card ven-mc--skeleton">
              <div class="ven-mc-shimmer" style="height:13px;width:55%;margin-bottom:8px"></div>
              <div class="ven-mc-shimmer" style="height:11px;width:40%"></div>
            </div>
          </template>
          <div v-else-if="!filtered.length" class="ven-mc-empty">
            <div style="font-size:32px;margin-bottom:8px">🏢</div>
            <div>{{ search ? 'No results found' : 'No vendors yet' }}</div>
          </div>
          <template v-else>
            <div v-for="v in filtered" :key="v.name" class="ven-mobile-card" @click="selectVendor(v)">
              <div class="ven-mc-top">
                <div class="ven-mc-name">{{ v.supplier_name || v.name }}</div>
                <span class="inv-status-badge" :class="v.disabled ? 'vt-badge-red' : 'vt-badge-green'">{{ v.disabled ? 'Disabled' : 'Active' }}</span>
              </div>
              <div class="ven-mc-meta">
                <span>{{ v.mobile_no || '—' }}</span>
              </div>
              <div class="ven-mc-meta">
                <span :style="(balancesByVendor[v.name]||0)>0 ? 'color:#E67700;font-weight:600' : ''">
                  {{ (balancesByVendor[v.name]||0)>0 ? fmtCur(balancesByVendor[v.name])+' payable' : 'No balance' }}
                </span>
                <span>{{ v.tax_id || 'Unregistered' }}</span>
              </div>
              <div class="ven-mc-footer">
                <button class="ven-mc-btn" @click.stop="openEdit(v.name)">Edit</button>
                <button class="ven-mc-btn ven-mc-danger" @click.stop="confirmDelete(v)">Delete</button>
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
          <div style="font-size:32px;margin-bottom:8px">🏢</div>
          <div>{{ search ? 'No results found' : 'No vendors yet' }}</div>
          <button v-if="!search" class="nim-btn nim-btn-primary" :disabled="!$canWrite('customers')" :title="!$canWrite('customers') ? 'Read-only access' : ''" style="margin-top:14px" @click="openAdd"><span v-html="icon('plus',13)"></span> New Vendor</button>
        </div>
        <template v-else>
          <div v-for="v in filtered" :key="v.name"
            class="b-card b-card-body"
            style="cursor:pointer;padding:16px;display:flex;flex-direction:column;gap:10px"
            @click="selectVendor(v)">
            <div style="display:flex;align-items:flex-start;gap:10px">
              <div class="vt-avatar" :class="v.disabled ? 'vt-avatar-disabled' : ''" style="width:40px;height:40px;font-size:14px;flex-shrink:0">
                {{vendorInitials(v.supplier_name)}}
              </div>
              <div style="flex:1;min-width:0">
                <div style="font-size:13.5px;font-weight:700;color:#1a1d23;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{v.supplier_name||v.name}}</div>
                <div style="font-size:11.5px;color:#9ca3af">{{v.name}}</div>
              </div>
              <span class="inv-status-badge" :class="v.disabled ? 'vt-badge-red' : 'vt-badge-green'" style="flex-shrink:0">
                <span class="vt-badge-dot"></span>{{v.disabled ? 'Disabled' : 'Active'}}
              </span>
            </div>
            <div style="font-size:12px;color:#6b7280;display:flex;justify-content:flex-end;align-items:center">
              <span class="vt-badge"
                :style="STYPE_META[v.supplier_type] ? { background: STYPE_META[v.supplier_type].bg, color: STYPE_META[v.supplier_type].text, border: 'none' } : {}">
                {{ STYPE_META[v.supplier_type]?.icon || '' }} {{v.supplier_type||'—'}}
              </span>
            </div>
            <div v-if="v.supplier_group" style="font-size:11.5px;color:#374151;font-weight:600">{{ v.supplier_group }}</div>
            <div style="font-size:11.5px;color:#9ca3af">
              <span>{{ lastBillByVendor[v.name] ? 'Last: '+lastBillByVendor[v.name].name : '—' }}</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;border-top:1px solid #f3f4f6;padding-top:10px">
              <span style="font-size:12px;color:#6b7280">{{v.mobile_no||'—'}}</span>
              <div style="display:flex;gap:6px">
                <button class="inv-act-btn vt-act-edit" @click.stop="openEdit(v.name)" title="Edit"><span v-html="icon('edit',13)"></span></button>
                <button class="inv-act-btn vt-act-del" @click.stop="confirmDelete(v)" title="Delete"><span v-html="icon('trash',13)"></span></button>
              </div>
            </div>
          </div>
        </template>
      </div>

      <div v-if="!loading && filtered.length" class="vt-footer">
        <span>Showing <strong>{{filtered.length}}</strong> of <strong>{{list.length}}</strong> vendors</span>
      </div>
    </div>
  </div>

  <!-- ── TWO-PANEL DETAIL VIEW (when vendor selected) ── -->
  <div v-else class="zb-master-detail" style="height:calc(100vh - 56px)">

    <!-- LEFT PANEL -->
    <div class="zb-list-pane" style="width:320px;min-width:260px;border-right:1px solid #e4e8f0;display:flex;flex-direction:column;overflow:hidden">

      <div style="padding:16px 16px 10px;border-bottom:1px solid #f0f2f5;flex-shrink:0">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
          <span style="font-size:14px;font-weight:700;color:#111827">Vendors</span>
          <button class="nim-btn nim-btn-primary" :disabled="!$canWrite('customers')" :title="!$canWrite('customers') ? 'Read-only access' : ''" style="padding:5px 10px;font-size:12px" @click="openAdd">
            <span v-html="icon('plus',12)"></span> New Vendor
          </button>
        </div>
        <div class="sales-search" style="width:100%">
          <span v-html="icon('search',13)" style="color:#9ca3af;flex-shrink:0"></span>
          <input v-model="search" placeholder="Search vendors…" class="sales-search-input" autocomplete="off"/>
        </div>
        <div style="display:flex;gap:4px;margin-top:8px;flex-wrap:wrap">
          <button v-for="f in [{k:'all',l:'All'},{k:'active',l:'Active'},{k:'disabled',l:'Disabled'},{k:'dealer',l:'🏪 Dealers'},{k:'distributor',l:'🚚 Distributors'}]"
            :key="f.k" class="sales-pill" :class="{'active': activeFilter===f.k}"
            @click="activeFilter=f.k" style="font-size:11.5px">
            {{f.l}}
            <span class="sales-pill-count" :class="activeFilter===f.k?'':'zb-pc-muted'">{{counts[f.k]}}</span>
          </button>
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
          <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" stroke-width="1.5" style="margin:0 auto 10px;display:block"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          <div style="font-size:13px;font-weight:600;color:#374151;margin-bottom:4px">{{search?'No matches':'No vendors yet'}}</div>
          <div style="font-size:12px;color:#9ca3af">{{search?'Try different keywords':'Add your first vendor'}}</div>
          <button v-if="!search" class="nim-btn nim-btn-primary" :disabled="!$canWrite('customers')" :title="!$canWrite('customers') ? 'Read-only access' : ''" style="margin-top:12px;font-size:12px" @click="openAdd">New Vendor</button>
        </div>
        <div v-else v-for="v in filtered" :key="v.name"
          @click="selectVendor(v)"
          :style="{
            padding:'12px 16px',
            borderBottom:'1px solid #f0f2f5',
            cursor:'pointer',
            background: selectedVendor && selectedVendor.name===v.name ? '#FFF7ED' : 'transparent',
            borderLeft: selectedVendor && selectedVendor.name===v.name ? '3px solid #E67700' : '3px solid transparent',
            transition:'background 0.15s',
          }">
          <div style="display:flex;align-items:center;gap:10px">
            <div :style="{
              width:'34px',height:'34px',borderRadius:'50%',flexShrink:0,
              display:'flex',alignItems:'center',justifyContent:'center',
              fontWeight:700,fontSize:'12px',color:'#fff',
              background: v.disabled ? '#9CA3AF' : 'linear-gradient(135deg,#E67700,#C96200)'
            }">{{vendorInitials(v.supplier_name)}}</div>
            <div style="flex:1;min-width:0">
              <div style="font-size:13px;font-weight:700;color:#111827;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                {{v.supplier_name||v.name}}
              </div>
              <div style="font-size:11.5px;color:#6B7280;margin-top:2px">
                <span :style="balancesByVendor[v.name]>0?'color:#E67700;font-weight:600':''">{{ fmtCur(balancesByVendor[v.name] || 0) }}</span> outstanding
                <span v-if="v.disabled" style="margin-left:6px;font-size:10px;font-weight:600;color:#6B7280;background:#F3F4F6;padding:1px 5px;border-radius:10px">Disabled</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="!loading && filtered.length" style="padding:8px 16px;border-top:1px solid #f0f2f5;font-size:11.5px;color:#9ca3af;display:flex;justify-content:space-between;flex-shrink:0">
        <span>{{filtered.length}} of {{list.length}} vendors</span>
        <button @click="load" style="background:none;border:none;cursor:pointer;color:#6B7280;font-size:11.5px;display:flex;align-items:center;gap:3px"><span v-html="icon('refresh',11)"></span> Refresh</button>
      </div>
    </div>

    <!-- RIGHT PANEL -->
    <div style="flex:1;overflow-y:auto;background:#F9FAFB">

      <div style="max-width:960px;margin:0 auto;padding:24px">

        <!-- Header -->
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
          <div style="display:flex;align-items:center;gap:12px">
            <div :style="{
              width:'46px',height:'46px',borderRadius:'50%',flexShrink:0,
              display:'flex',alignItems:'center',justifyContent:'center',
              fontWeight:700,fontSize:'16px',color:'#fff',
              background: selectedVendor.disabled ? '#9CA3AF' : 'linear-gradient(135deg,#E67700,#C96200)'
            }">{{vendorInitials(selectedVendor.supplier_name)}}</div>
            <div>
              <div style="font-size:19px;font-weight:700;color:#111827">{{selectedVendor.supplier_name}}</div>
              <div style="font-size:12px;color:#6B7280">{{selectedVendor.name}}</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px">
            <button class="nim-btn" style="background:#fff;color:#374151;border:1px solid #E5E7EB;font-size:13px" @click="openEdit(selectedVendor.name)">
              <span v-html="icon('edit',13)"></span> Edit
            </button>
            <!-- <button class="nim-btn nim-btn-primary" :disabled="!$canWrite('customers')" :title="!$canWrite('customers') ? 'Read-only access' : ''" style="font-size:13px;background:#E67700;border-color:#E67700" @click="openAdd">
              <span v-html="icon('plus',13)"></span> New Transaction
            </button> -->
            <button class="nim-btn" style="background:#fff;color:#374151;border:1px solid #E5E7EB;width:32px;height:32px;padding:0;display:grid;place-items:center" @click="closeVendor" title="Close">
              <span v-html="icon('x',14)"></span>
            </button>
          </div>
        </div>

        <!-- Tabs -->
        <div style="display:flex;border-bottom:2px solid #E5E7EB;margin-bottom:22px;gap:0">
          <button @click="activeVendorTab='overview'"
            :style="{padding:'8px 16px',fontSize:'13.5px',fontWeight:600,border:'none',background:'none',cursor:'pointer',
              color:activeVendorTab==='overview'?'#E67700':'#6B7280',
              borderBottom:activeVendorTab==='overview'?'2px solid #E67700':'2px solid transparent',marginBottom:'-2px'}">
            Overview
          </button>
          <button @click="activeVendorTab='transactions'"
            :style="{padding:'8px 16px',fontSize:'13.5px',fontWeight:600,border:'none',background:'none',cursor:'pointer',display:'flex',
              color:activeVendorTab==='transactions'?'#E67700':'#6B7280',
              borderBottom:activeVendorTab==='transactions'?'2px solid #E67700':'2px solid transparent',marginBottom:'-2px'}">
            Transactions
            <span v-if="vendorTxnsActive.length" style="background:#E67700;color:#fff;padding:1px 7px;border-radius:999px;font-size:11px;margin-left:4px">{{vendorTxnsActive.length}}</span>
          </button>
          <button @click="activeVendorTab='statement'; loadStatement()"
            :style="{padding:'8px 16px',fontSize:'13.5px',fontWeight:600,border:'none',background:'none',cursor:'pointer',
              color:activeVendorTab==='statement'?'#E67700':'#6B7280',
              borderBottom:activeVendorTab==='statement'?'2px solid #E67700':'2px solid transparent',marginBottom:'-2px'}">
            Statement
          </button>
        </div>

        <!-- Overview tab -->
        <div v-if="activeVendorTab==='overview'" class="ven-overview-cols" style="display:flex;gap:20px;align-items:flex-start">

          <!-- Left column ~55% -->
          <div style="flex:0 0 55%;min-width:0;display:flex;flex-direction:column;gap:14px">

            <div style="background:#fff;border:1px solid #E5E7EB;border-radius:10px;padding:18px">
              <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;padding-bottom:14px;border-bottom:1px solid #F3F4F6">
                <div :style="{
                  width:'44px',height:'44px',borderRadius:'50%',flexShrink:0,
                  display:'flex',alignItems:'center',justifyContent:'center',
                  fontWeight:700,fontSize:'16px',color:'#fff',
                  background: selectedVendor.disabled ? '#9CA3AF' : 'linear-gradient(135deg,#E67700,#C96200)'
                }">{{vendorInitials(selectedVendor.supplier_name)}}</div>
                <div>
                  <div style="font-size:14px;font-weight:700;color:#111827">{{selectedVendor.supplier_name}}</div>
                  <div v-if="selectedVendor.email_id" style="font-size:12px;color:#6B7280;margin-top:2px">{{selectedVendor.email_id}}</div>
                </div>
                <div style="margin-left:auto;display:none">
                  <a href="#" style="font-size:12px;color:#E67700;text-decoration:none">Invite to Portal</a>
                </div>
              </div>
              <div style="display:flex;flex-direction:column;gap:7px">
                <div v-if="selectedVendor.mobile_no" style="display:flex;align-items:center;gap:8px;font-size:12.5px;color:#374151">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#9CA3AF" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12 19.79 19.79 0 0 1 1.63 3.18 2 2 0 0 1 3.6 1h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.6A16 16 0 0 0 15.4 16.1l.97-.97a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
                  <span>{{selectedVendor.mobile_no}}</span>
                </div>
                <div v-else style="display:flex;align-items:center;gap:8px;font-size:12.5px;color:#9CA3AF">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#D1D5DB" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12 19.79 19.79 0 0 1 1.63 3.18 2 2 0 0 1 3.6 1h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.6A16 16 0 0 0 15.4 16.1l.97-.97a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
                  <span>No phone number</span>
                </div>
              </div>
            </div>

            <div style="background:#fff;border:1px solid #E5E7EB;border-radius:10px;overflow:hidden">
              <div style="padding:12px 16px;display:flex;justify-content:space-between;align-items:center;cursor:pointer;user-select:none" :style="!collapsed.address?'border-bottom:1px solid #F3F4F6':''" @click="collapsed.address=!collapsed.address">
                <span style="font-size:11px;font-weight:700;color:#9CA3AF;letter-spacing:0.8px">ADDRESS</span>
                <svg :style="{transition:'transform 0.2s',transform:collapsed.address?'rotate(-90deg)':'rotate(0deg)'}" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#9CA3AF" stroke-width="2.5" stroke-linecap="round"><polyline points="18 15 12 9 6 15"/></svg>
              </div>
              <div v-show="!collapsed.address" style="padding:14px 16px">
                <AddressManager
                  v-if="selectedVendor.name"
                  :partyDoctype="'Supplier'"
                  :partyName="selectedVendor.name"
                  :readonly="true"
                />
              </div>
            </div>

            

          </div>

          <!-- Right column ~45% -->
          <div style="flex:1;min-width:0;display:flex;flex-direction:column;gap:14px">

            <div style="background:#fff;border:1px solid #E5E7EB;border-radius:10px;padding:16px">
              <div style="font-size:11.5px;color:#6B7280;margin-bottom:4px">Payment due period</div>
              <div style="font-size:14px;font-weight:600;color:#111827">{{selectedVendor.payment_terms||'Due on Receipt'}}</div>
            </div>

            <div style="background:#fff;border:1px solid #E5E7EB;border-radius:10px;overflow:hidden">
              <div style="padding:12px 16px;border-bottom:1px solid #F3F4F6">
                <span style="font-size:11px;font-weight:700;color:#9CA3AF;letter-spacing:0.8px">PAYABLES</span>
              </div>
              <table class="ven-recv-table" style="width:100%;border-collapse:collapse">
                <thead>
                  <tr style="border-bottom:1px solid #F3F4F6">
                    <th style="text-align:left;font-size:10.5px;font-weight:600;color:#9CA3AF;padding:8px 16px">CURRENCY</th>
                    <th style="text-align:right;font-size:10.5px;font-weight:600;color:#9CA3AF;padding:8px 12px">OUTSTANDING PAYABLES</th>
                    <th style="text-align:right;font-size:10.5px;font-weight:600;color:#9CA3AF;padding:8px 16px">UNUSED CREDITS</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td style="font-size:13px;font-weight:600;color:#374151;padding:10px 16px">{{ selectedVendor.default_currency || "INR" }}</td>
                    <td style="font-size:13px;font-weight:600;color:#E67700;text-align:right;padding:10px 12px;">{{ fmtCur(vendorSummary.outstanding || 0) }}</td>
                    <td style="font-size:13px;font-weight:600;color:#059669;text-align:right;padding:10px 16px;">{{ fmtCur(vendorSummary.dn_credit || 0) }}</td>
                  </tr>
                </tbody>
              </table>
              <div style="padding:10px 16px;display:none;">
                <a href="#" style="font-size:12.5px;color:#2563EB;text-decoration:none">Enter Opening Balance</a>
              </div>
            </div>

            <div v-if="obInfo.has_opening_je" style="background:#fff;border:1px solid #E5E7EB;border-radius:10px;padding:16px;display:flex;align-items:center;justify-content:space-between">
              <div>
                <div style="font-size:11px;font-weight:700;color:#9CA3AF;letter-spacing:0.8px">OPENING BALANCE</div>
                <div style="font-size:16px;font-weight:700;margin-top:4px" :style="{color: obInfo.outstanding>0?'#E67700':'#16a34a'}">
                  {{ fmtCur(obInfo.outstanding) }}
                  <span v-if="obInfo.outstanding<=0" style="font-size:11px;font-weight:700;padding:1px 8px;border-radius:12px;background:#dcfce7;color:#16a34a;margin-left:6px">Paid</span>
                </div>
              </div>
              <button v-if="obInfo.outstanding>0" class="nim-btn nim-btn-primary" style="font-size:13px" @click="openPayModal">
                <span v-html="icon('plus',13)"></span> Pay
              </button>
            </div>

            <div style="background:#fff;border:1px solid #E5E7EB;border-radius:10px;overflow:hidden">
              <div style="padding:12px 16px;display:flex;justify-content:space-between;align-items:center;cursor:pointer;user-select:none" :style="!collapsed.otherDetails?'border-bottom:1px solid #F3F4F6':''" @click="collapsed.otherDetails=!collapsed.otherDetails">
                <span style="font-size:11px;font-weight:700;color:#9CA3AF;letter-spacing:0.8px">OTHER DETAILS</span>
                <svg :style="{transition:'transform 0.2s',transform:collapsed.otherDetails?'rotate(-90deg)':'rotate(0deg)'}" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#9CA3AF" stroke-width="2.5" stroke-linecap="round"><polyline points="18 15 12 9 6 15"/></svg>
              </div>
              <div v-show="!collapsed.otherDetails" style="padding:14px 16px;display:flex;flex-direction:column;gap:10px">
                <div style="display:flex;justify-content:space-between;font-size:12.5px">
                  <span style="color:#6B7280">Default Currency</span>
                  <span style="font-weight:600;color:#111827">{{selectedVendor.default_currency||'INR'}}</span>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:12.5px;align-items:center">
                  <span style="color:#6B7280">Portal Status</span>
                  <span style="font-size:11px;font-weight:700;padding:2px 8px;border-radius:20px;background:#F3F4F6;color:#6B7280">● Disabled</span>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:12.5px">
                  <span style="color:#6B7280">Vendor Type</span>
                  <span style="font-weight:600;color:#111827">{{selectedVendor.supplier_type||'Company'}}</span>
                </div>
                <div v-if="selectedVendor.tax_id" style="display:flex;justify-content:space-between;font-size:12.5px">
                  <span style="color:#6B7280">GSTIN / Tax ID</span>
                  <span style="font-weight:600;color:#111827;">{{selectedVendor.tax_id}}</span>
                </div>
              </div>
            </div>
            <div style="padding:4px 0">
              <button @click="confirmDelete(selectedVendor)" style="background:none;border:none;cursor:pointer;color:#DC2626;font-size:12.5px;display:flex;align-items:center;gap:6px">
                <span v-html="icon('trash',13)"></span> Delete Vendor
              </button>
            </div>
          </div>
        </div>

        <!-- Transactions tab -->
        <div v-else-if="activeVendorTab==='transactions'">
          <div v-if="detailLoading" style="background:#fff;border:1px solid #E5E7EB;border-radius:10px;padding:24px;text-align:center;color:#9CA3AF">Loading transactions…</div>
          <div v-else-if="!vendorTxnsActive.length" style="background:#fff;border:1px solid #E5E7EB;border-radius:10px;padding:24px;text-align:center;color:#9CA3AF">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#D1D5DB" stroke-width="1.5" style="margin:0 auto 12px;display:block"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            <div style="font-size:14px;font-weight:600;color:#374151;margin-bottom:6px">No transactions yet</div>
            <div style="font-size:12.5px;color:#9CA3AF">Bills and payments for {{selectedVendor.supplier_name}} will appear here.</div>
          </div>
          <div v-else class="ven-txn-wrap" style="background:#fff;border:1px solid #E5E7EB;border-radius:10px;overflow:hidden">
            <!-- Desktop table -->
            <div class="ven-txn-desktop">
              <div style="display:grid;grid-template-columns:90px 150px 95px 110px 110px 100px 120px;gap:8px;background:#F9FAFB;padding:10px 14px;font-size:11px;font-weight:700;color:#6B7280;text-transform:uppercase;border-bottom:1px solid #E5E7EB;min-width:660px">
                <span>Type</span><span>Reference</span><span>Date</span><span style="text-align:right">Amount</span><span style="text-align:right">Outstanding</span><span style="text-align:center">Status</span><span style="text-align:right">Balance</span>
              </div>
              <div v-for="t in vendorTxnsVisible" :key="t.type+'-'+t.name"
                style="display:grid;grid-template-columns:90px 150px 95px 110px 110px 100px 120px;gap:8px;padding:9px 14px;border-bottom:1px solid #F3F4F6;font-size:12.5px;align-items:center;min-width:660px">
                <span :style="{
                  fontSize:'10.5px',fontWeight:700,padding:'2px 8px',borderRadius:'10px',display:'inline-block',width:'fit-content',
                  background: t.type==='Bill' ? '#FEF3C7' : t.type==='Payment' ? '#D1FAE5' : '#FEE2E2',
                  color: t.type==='Bill' ? '#92400E' : t.type==='Payment' ? '#059669' : '#991B1B'
                }">{{t.type}}</span>
                <span @click.stop style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap"><DocLink :doctype="vendDocTypeFor(t.type)" :name="t.name" /></span>
                <span style="color:#6B7280">{{fmtDate(t.date)}}</span>
                <span style="text-align:right;font-weight:600" :style="{color: t.amount<0 ? '#059669' : '#374151'}">{{fmtCur(Math.abs(t.amount))}}</span>
                <span style="text-align:right;" :style="{color: t.outstanding>0 ? '#E67700' : '#9CA3AF'}">{{t.outstanding>0?fmtCur(t.outstanding):'—'}}</span>
                <span style="text-align:center"><span :style="'font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px;white-space:nowrap;'+txnStatusStyle(t)">{{txnStatusLabel(t)}}</span></span>
                <span style="text-align:right;font-weight:700;color:#111827">{{fmtCur(t.balance)}}</span>
              </div>
            </div>

            <!-- Mobile card view -->
            <div class="ven-txn-mobile-cards">
              <div v-for="t in vendorTxnsVisible" :key="'mc-'+t.type+'-'+t.name" class="ven-txn-mc">
                <div class="ven-txn-mc-top">
                  <span class="ven-txn-mc-badge" :style="{
                    background: t.type==='Bill' ? '#FEF3C7' : t.type==='Payment' ? '#D1FAE5' : '#FEE2E2',
                    color: t.type==='Bill' ? '#92400E' : t.type==='Payment' ? '#059669' : '#991B1B'
                  }">{{t.type}}</span>
                  <span class="ven-txn-mc-amount" :style="{color: t.amount<0 ? '#059669' : '#374151'}">{{fmtCur(Math.abs(t.amount))}}</span>
                </div>
                <div class="ven-txn-mc-mid">
                  <span class="ven-txn-mc-ref" @click.stop><DocLink :doctype="vendDocTypeFor(t.type)" :name="t.name" /></span>
                  <span class="ven-txn-mc-date">{{fmtDate(t.date)}}</span>
                </div>
                <div class="ven-txn-mc-mid" style="margin-top:4px">
                  <span :style="'font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px;'+txnStatusStyle(t)">{{txnStatusLabel(t)}}</span>
                  <span style="font-size:12px;color:#6B7280">Balance: <strong style="color:#111827">{{fmtCur(t.balance)}}</strong></span>
                </div>
                <div v-if="t.outstanding>0" class="ven-txn-mc-outstanding">
                  Outstanding: <strong>{{fmtCur(t.outstanding)}}</strong>
                </div>
              </div>
            </div>
          </div>

          <!-- Load More — transactions -->
          <div v-if="vendorTxnsHasMore" class="ven-load-more-wrap">
            <span class="ven-load-more-count">Showing {{vendorTxnsVisible.length}} of {{vendorTxnsActive.length}}</span>
            <button class="ven-load-more-btn" @click="txnPage++">Load more</button>
          </div>
          <div v-else-if="vendorTxnsActive.length > TXN_PAGE_SIZE" class="ven-load-more-wrap ven-load-more-end">
            All {{vendorTxnsActive.length}} transactions shown
          </div>
        </div>

        <!-- Statement tab -->
        <div v-else-if="activeVendorTab==='statement'">
          <div style="background:#fff;border:1px solid #E5E7EB;border-radius:10px;padding:14px 18px;display:flex;align-items:center;gap:12px;margin-bottom:14px;flex-wrap:wrap">
            <span style="font-size:12px;font-weight:600;color:#6B7280">FROM</span>
            <input v-model="stmtRange.from" type="date" class="inv-fi" style="width:160px"/>
            <span style="font-size:12px;font-weight:600;color:#6B7280">TO</span>
            <input v-model="stmtRange.to" type="date" class="inv-fi" style="width:160px"/>
            <button class="nim-btn" style="border:1px solid #E5E7EB" @click="loadStatement">Refresh</button>
            <div style="margin-left:auto;display:flex;gap:8px">
              <!-- <button v-if="vendorStatement.rows?.length" class="nim-btn" style="border:1px solid #E5E7EB" @click="downloadVendorStatementPdf" :disabled="downloadingVendorStmtPdf">
                {{downloadingVendorStmtPdf ? 'Generating…' : '⬇ Download PDF'}}
              </button> -->
              <button class="nim-btn" style="border:1px solid #E5E7EB" @click="emailVendorStatement">📧 Email Statement</button>
            </div>
          </div>
          <div v-if="detailLoading" style="background:#fff;border:1px solid #E5E7EB;border-radius:10px;padding:24px;text-align:center;color:#9CA3AF">Loading statement…</div>
          <div v-else style="background:#fff;border:1px solid #E5E7EB;border-radius:10px;overflow:hidden">
            <!-- Desktop table -->
            <div class="ven-stmt-desktop" style="overflow-x:auto">
              <table style="width:100%;border-collapse:collapse;font-size:12.5px">
                <thead>
                  <tr style="background:#F9FAFB">
                    <th style="text-align:left;padding:10px 14px;font-size:11px;font-weight:700;color:#6B7280;text-transform:uppercase;border-bottom:1px solid #E5E7EB;white-space:nowrap">Date</th>
                    <th style="text-align:left;padding:10px 14px;font-size:11px;font-weight:700;color:#6B7280;text-transform:uppercase;border-bottom:1px solid #E5E7EB">Reference</th>
                    <th style="text-align:left;padding:10px 14px;font-size:11px;font-weight:700;color:#6B7280;text-transform:uppercase;border-bottom:1px solid #E5E7EB;white-space:nowrap">Type</th>
                    <th style="text-align:right;padding:10px 14px;font-size:11px;font-weight:700;color:#6B7280;text-transform:uppercase;border-bottom:1px solid #E5E7EB;white-space:nowrap">Debit</th>
                    <th style="text-align:right;padding:10px 14px;font-size:11px;font-weight:700;color:#6B7280;text-transform:uppercase;border-bottom:1px solid #E5E7EB;white-space:nowrap">Credit</th>
                    <th style="text-align:right;padding:10px 14px;font-size:11px;font-weight:700;color:#6B7280;text-transform:uppercase;border-bottom:1px solid #E5E7EB;white-space:nowrap">Balance</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="!vendorStatement.rows?.length">
                    <td colspan="6" style="padding:24px;text-align:center;color:#9CA3AF;font-size:13px">No statement rows for this period.</td>
                  </tr>
                  <tr v-for="(r,i) in stmtRowsVisible" :key="r.ref+'-'+i" style="border-bottom:1px solid #F3F4F6">
                    <td style="padding:8px 14px;color:#6B7280;white-space:nowrap">{{fmtDate(r.date)}}</td>
                    <td style="padding:8px 14px" @click.stop><DocLink :doctype="vendDocTypeFor(r.type)" :name="r.ref" /></td>
                    <td style="padding:8px 14px;font-size:11px;color:#6B7280;white-space:nowrap">{{r.type}}</td>
                    <td style="padding:8px 14px;text-align:right;color:#059669;white-space:nowrap">{{r.debit>0?fmtCur(r.debit):'—'}}</td>
                    <td style="padding:8px 14px;text-align:right;color:#E67700;white-space:nowrap">{{r.credit>0?fmtCur(r.credit):'—'}}</td>
                    <td style="padding:8px 14px;text-align:right;font-weight:700;color:#111827;white-space:nowrap">{{fmtCur(r.balance)}}</td>
                  </tr>
                </tbody>
                <tfoot v-if="vendorStatement.rows?.length">
                  <tr style="background:#F9FAFB;font-weight:700">
                    <td colspan="5" style="padding:10px 14px">Closing Balance</td>
                    <td style="padding:10px 14px;text-align:right;white-space:nowrap">{{fmtCur(vendorStatement.totals?.closing_balance || 0)}}</td>
                  </tr>
                </tfoot>
              </table>
            </div>

            <!-- Mobile card view -->
            <div class="ven-stmt-mobile-cards">
              <div v-if="!vendorStatement.rows?.length" style="padding:24px;text-align:center;color:#9CA3AF;font-size:13px">No statement rows for this period.</div>
              <div v-for="(r,i) in stmtRowsVisible" :key="'smc-'+r.ref+'-'+i" class="ven-stmt-mc">
                <div class="ven-stmt-mc-top">
                  <span class="ven-stmt-mc-ref" @click.stop><DocLink :doctype="vendDocTypeFor(r.type)" :name="r.ref" /></span>
                  <span class="ven-stmt-mc-type">{{r.type}}</span>
                </div>
                <div class="ven-stmt-mc-date">{{fmtDate(r.date)}}</div>
                <div class="ven-stmt-mc-amounts">
                  <div v-if="r.debit>0" class="ven-stmt-mc-debit">
                    <span class="ven-stmt-mc-lbl">Debit</span>
                    <span>{{fmtCur(r.debit)}}</span>
                  </div>
                  <div v-if="r.credit>0" class="ven-stmt-mc-credit">
                    <span class="ven-stmt-mc-lbl">Credit</span>
                    <span>{{fmtCur(r.credit)}}</span>
                  </div>
                  <div class="ven-stmt-mc-balance">
                    <span class="ven-stmt-mc-lbl">Balance</span>
                    <span>{{fmtCur(r.balance)}}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Load More — statement rows -->
            <div v-if="stmtRowsHasMore" class="ven-load-more-wrap" style="border-top:1px solid #F3F4F6">
              <span class="ven-load-more-count">Showing {{stmtRowsVisible.length}} of {{vendorStatement.rows.length}}</span>
              <button class="ven-load-more-btn" @click="stmtPage++">Load more</button>
            </div>
            <div v-else-if="vendorStatement.rows?.length > STMT_PAGE_SIZE" class="ven-load-more-wrap ven-load-more-end" style="border-top:1px solid #F3F4F6">
              All {{vendorStatement.rows.length}} rows shown
            </div>

            <!-- Totals footer -->
            <div v-if="vendorStatement.rows?.length" style="background:#F9FAFB;padding:12px 14px;border-top:2px solid #E5E7EB;display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:14px;font-size:12.5px">
              <div><span style="color:#6B7280">Billed:</span> <strong style="color:#E67700">{{fmtCur(vendorStatement.totals?.billed || 0)}}</strong></div>
              <div><span style="color:#6B7280">Paid:</span> <strong style="color:#059669">{{fmtCur(vendorStatement.totals?.paid || 0)}}</strong></div>
              <div><span style="color:#6B7280">Debit Notes:</span> <strong style="color:#059669">{{fmtCur(vendorStatement.totals?.debit_notes || 0)}}</strong></div>
              <div><span style="color:#6B7280">Closing Balance:</span> <strong style="color:#111827">{{fmtCur(vendorStatement.totals?.closing_balance || 0)}}</strong></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Drawer -->
  <Teleport to="body">
    <div v-if="showPayModal" class="ven-pay-modal-overlay" @click.self="showPayModal=false">
      <div class="ven-pay-modal">
        <div style="font-size:16px;font-weight:700;color:#111827;margin-bottom:14px">Pay Opening Balance</div>
        <label style="display:flex;flex-direction:column;gap:4px;margin-bottom:12px;font-size:12.5px;color:#374151;font-weight:600">
          <span>Amount</span>
          <input type="number" v-model.number="payForm.amount" :max="obInfo.outstanding" min="0.01" step="0.01"
            style="border:1px solid #d1d5db;border-radius:8px;padding:8px 10px;font-size:13px;font-family:inherit"/>
        </label>
        <label style="display:flex;flex-direction:column;gap:4px;margin-bottom:12px;font-size:12.5px;color:#374151;font-weight:600">
          <span>Pay From</span>
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
  </Teleport>

  <Teleport to="body">
    <div v-if="showDrawer" class="inv-drawer-bg" @click.self="showDrawer=false">
      <div class="inv-drawer-panel" :class="{open:showDrawer}" style="width:680px;max-width:98vw">

        <div class="inv-dh" style="background:linear-gradient(135deg,#E67700,#C96200);padding:18px 24px">
          <div class="cust-drawer-header-left">
            <div class="cust-drawer-icon" style="color:#fff">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            </div>
            <div>
              <div class="inv-dh-title">{{drawerMode==='add'?'New Vendor':'Edit Vendor'}}</div>
              <div class="cust-drawer-sub">{{drawerMode==='edit'?form.name:'Fill in vendor details'}}</div>
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
    transition: .15s;" class="inv-dclose" @click="showDrawer=false" v-html="icon('x',15)"></button>
        </div>

        <div class="inv-view-tabs">
          <button v-for="t in [{k:'overview',l:'Overview'},{k:'address',l:'Address'},{k:'other',l:'Other Details'}]"
            :key="t.k" @click="drawerTab=t.k"
            class="inv-vtab" :class="{active: drawerTab===t.k}">
            {{t.l}}
          </button>
        </div>

        <div v-if="drawerLoading" style="flex:1;display:grid;place-items:center;color:#9ca3af;font-size:13px;padding:40px">
          <div>Loading vendor…</div>
        </div>

        <div v-else class="inv-dbody" style="padding:24px;overflow-y:auto;flex:1">

          <!-- Overview Tab -->
          <template v-if="drawerTab==='overview'">

          <div style="margin-bottom:20px">
            <label class="inv-lbl" style="margin-bottom:8px;display:block">Vendor Type</label>
            <div style="display:flex;flex-wrap:wrap;gap:8px">
              <button v-for="opt in SUPPLIER_TYPES" :key="opt" type="button"
                @click="form.supplier_type=opt"
                :style="'padding:6px 16px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;transition:all .15s;border:1.5px solid '+(form.supplier_type===opt?'#E67700':'#e2e8f0')+';background:'+(form.supplier_type===opt?'#fff7ed':'#fff')+';color:'+(form.supplier_type===opt?'#C96200':'#6b7280')">
                {{STYPE_META[opt]?.icon}} {{opt}}
              </button>
            </div>
            <div v-if="form.supplier_type && STYPE_META[form.supplier_type]?.desc"
              style="margin-top:8px;font-size:12px;padding:6px 10px;border-radius:6px;display:inline-block"
              :style="{background: STYPE_META[form.supplier_type].bg, color: STYPE_META[form.supplier_type].text}">
              {{ STYPE_META[form.supplier_type].icon }} {{ STYPE_META[form.supplier_type].desc }}
            </div>
          </div>

          <div style="margin-bottom:20px" v-if="form.supplier_type==='Dealer' || form.supplier_type==='Distributor'">
            <label class="inv-lbl" style="margin-bottom:8px;display:block">
              {{ form.supplier_type }} Group
            </label>
            <select v-model="form.supplier_group" class="inv-fi">
              <option value="">Select group</option>
              <optgroup v-if="form.supplier_type==='Distributor'" label="Distributor Groups">
                <option v-for="g in supplierGroups.filter(g=>g.toLowerCase().includes('distributor'))" :key="g" :value="g">{{ g }}</option>
              </optgroup>
              <optgroup v-if="form.supplier_type==='Dealer'" label="Dealer Groups">
                <option v-for="g in supplierGroups.filter(g=>g.toLowerCase().includes('dealer'))" :key="g" :value="g">{{ g }}</option>
              </optgroup>
            </select>
          </div>

          <div class="inv-sec-lbl" style="margin-top:0">Basic Information</div>
          <div class="inv-fg inv-fg2">
            <div class="inv-field" style="grid-column:span 2">
              <label class="inv-lbl">Vendor Name <span class="nim-req">*</span></label>
              <input v-model="form.supplier_name" class="inv-fi"
                :style="formErrors.supplier_name?'border-color:#dc2626;background:#fff5f5':''"
                placeholder="Company or individual name"
                @input="form.supplier_name=form.supplier_name.replace(/[^a-zA-Z\s.'&-]/g,''); delete formErrors.supplier_name"
                @blur="validateField('supplier_name')"/>
              <div v-if="formErrors.supplier_name" style="margin-top:4px;font-size:12px;color:#dc2626;display:flex;align-items:center;gap:4px">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12" y2="16"/></svg>
                {{formErrors.supplier_name}}
              </div>
            </div>
            <div class="inv-field">
              <label class="inv-lbl">GSTIN / Tax ID</label>
              <input v-model="form.tax_id" class="inv-fi"
                :style="formErrors.tax_id?'border-color:#dc2626;background:#fff5f5':form.tax_id&&!formErrors.tax_id&&form.country==='India'&&GSTIN_REGEX.test(form.tax_id)?'border-color:#2f9e44':''"
                placeholder="27AAPFU0939F1ZV"
                @input="form.tax_id=form.tax_id.toUpperCase(); delete formErrors.tax_id"
                @blur="validateField('tax_id')"/>
              <div v-if="formErrors.tax_id" style="margin-top:4px;font-size:12px;color:#dc2626;display:flex;align-items:center;gap:4px">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12" y2="16"/></svg>
                {{formErrors.tax_id}}
              </div>
              <div v-else-if="form.tax_id&&form.country==='India'&&GSTIN_REGEX.test(form.tax_id)" style="margin-top:4px;font-size:12px;color:#2f9e44;display:flex;align-items:center;gap:4px">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                Valid GSTIN
              </div>
            </div>
            <div class="inv-field">
              <label class="inv-lbl">Payment Terms</label>
              <select v-model="form.payment_terms" class="inv-fi">
                <option value="">Select</option>
                <option>Net 30</option><option>Net 15</option><option>Net 7</option>
                <option>Due on Receipt</option><option>End of Month</option>
              </select>
            </div>
          </div>

          <div class="inv-sec-lbl">Contact</div>
          <div class="inv-fg inv-fg2">
            <div class="inv-field">
              <label class="inv-lbl">Email</label>
              <input v-model="form.email_id" type="email" class="inv-fi"
                :style="formErrors.email_id?'border-color:#dc2626;background:#fff5f5':form.email_id&&EMAIL_REGEX.test(form.email_id)?'border-color:#2f9e44':''"
                placeholder="email@vendor.com"
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
            <div class="inv-field">
              <label class="inv-lbl">Mobile</label>
              <div style="display:flex;min-width:0">
                <select v-model="form.mobile_code" style="width:85px;flex-shrink:0;flex-grow:0;border:1px solid #d1d5db;border-right:none;border-top-right-radius:0;border-bottom-right-radius:0;border-top-left-radius:6px;border-bottom-left-radius:6px;text-align:center;background:#f9fafb;padding:0 5px;font-size:13px;height:38px;outline:none"
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
                <input v-model="form.mobile_no"
                  :style="`border:1px solid #d1d5db;border-top-left-radius:0;border-bottom-left-radius:0;border-top-right-radius:6px;border-bottom-right-radius:6px;flex:1 1 0%;width:0;min-width:0;padding:0 10px;font-size:13px;height:38px;outline:none;background:#fff;${formErrors.mobile_no?'border-color:#dc2626;background:#fff5f5':form.mobile_no&&!formErrors.mobile_no?'border-color:#2f9e44':''}`"
                  placeholder="Mobile number"
                  @input="form.mobile_no=form.mobile_no.replace(/\D/g,''); delete formErrors.mobile_no"
                  @blur="validateField('mobile_no')"/>
              </div>
              <div v-if="formErrors.mobile_no" style="margin-top:4px;font-size:12px;color:#dc2626;display:flex;align-items:center;gap:4px">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12" y2="16"/></svg>
                {{formErrors.mobile_no}}
              </div>
            </div>
            <div class="inv-field">
              <label class="inv-lbl">Phone</label>
              <input v-model="form.phone" class="inv-fi" placeholder="Landline"
                :style="formErrors.phone?'border-color:#dc2626;background:#fff5f5':''"
                @input="form.phone=form.phone.replace(/[^\d+\-\s()]/g,''); delete formErrors.phone"
                @blur="validateField('phone')"/>
              <div v-if="formErrors.phone" style="margin-top:4px;font-size:12px;color:#dc2626;display:flex;align-items:center;gap:4px">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12" y2="16"/></svg>
                {{formErrors.phone}}
              </div>
            </div>
            <div class="inv-field">
              <label class="inv-lbl">Website</label>
              <input v-model="form.website" class="inv-fi" placeholder="https://"
                :style="formErrors.website?'border-color:#dc2626;background:#fff5f5':form.website&&URL_REGEX.test(form.website)?'border-color:#2f9e44':''"
                @input="delete formErrors.website"
                @blur="validateField('website')"/>
              <div v-if="formErrors.website" style="margin-top:4px;font-size:12px;color:#dc2626;display:flex;align-items:center;gap:4px">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12" y2="16"/></svg>
                {{formErrors.website}}
              </div>
            </div>
          </div>

          <div v-if="drawerMode==='edit'" class="cust-disable-box" @click="form.disabled=form.disabled?0:1" style="margin-top:4px">
            <input type="checkbox" :checked="!!form.disabled" @click.stop="form.disabled=form.disabled?0:1" style="width:16px;height:16px;accent-color:#dc2626;cursor:pointer"/>
            <label style="font-size:13px;color:#dc2626;cursor:pointer">Disable this vendor (won't appear in bill dropdowns)</label>
          </div>

          </template>

          <!-- Address Tab -->
          <template v-else-if="drawerTab==='address'">
            <AddressManager
              partyDoctype="Supplier"
              :partyName="drawerMode==='edit' ? form.name : ''"
              v-model="pendingAddresses"
              @addressSaved="load"
              @addressDeleted="load"
            />
          </template>

          <!-- Other Details Tab -->
          <template v-else-if="drawerTab==='other'">
          <div class="inv-sec-lbl" style="margin-top:0">TDS / Withholding Tax</div>
          <div class="inv-fg inv-fg2">
            <div class="inv-field" style="grid-column:span 2;display:flex;align-items:center;gap:10px">
              <input type="checkbox" id="tds_applicable" :checked="!!form.tds_applicable"
                @change="form.tds_applicable = $event.target.checked ? 1 : 0"
                style="width:16px;height:16px;accent-color:#E67700;cursor:pointer;flex-shrink:0"/>
              <label for="tds_applicable" style="font-size:13px;color:#374151;cursor:pointer;font-weight:500">
                TDS Applicable — deduct tax at source on payments to this vendor
              </label>
            </div>
            <template v-if="form.tds_applicable">
              <div class="inv-field">
                <label class="inv-lbl">Default TDS Section</label>
                <select v-model="form.tds_section" class="inv-fi">
                  <option value="">Select Section</option>
                  <option>194C</option>
                  <option>194J</option>
                  <option>194A</option>
                  <option>194H</option>
                  <option>194I</option>
                  <option>192</option>
                  <option>195</option>
                  <option>Other</option>
                </select>
              </div>
              <div class="inv-field">
                <label class="inv-lbl">PAN Number</label>
                <input v-model="form.pan" class="inv-fi" placeholder="ABCDE1234F" maxlength="10"
                  style="font-family:var(--mono);letter-spacing:.04em"
                  :style="form.pan&&!PAN_REGEX.test(form.pan)?'border-color:#dc2626;background:#fff5f5':form.pan&&PAN_REGEX.test(form.pan)?'border-color:#2f9e44':''"
                  @input="form.pan = form.pan.toUpperCase().replace(/[^A-Z0-9]/g,'')"/>
                <div v-if="form.pan&&PAN_REGEX.test(form.pan)" style="margin-top:4px;font-size:12px;color:#2f9e44;display:flex;align-items:center;gap:4px">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                  Valid PAN
                </div>
              </div>
            </template>
          </div>

          <div class="inv-sec-lbl">Account Settings</div>
          <div class="cus-form-grid2" style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
            <div>
              <label class="inv-lbl">Default Payable Account</label>
              <select v-model="form.default_payable_account" class="inv-fi" style="cursor:pointer">
                <option value="">Select</option>
                <option v-for="a in accounts" :key="a.name" :value="a.name">{{a.name}}</option>
              </select>
            </div>
            <div>
              <label class="inv-lbl">Default Currency</label>
              <select v-model="form.default_currency" class="inv-fi" style="cursor:pointer">
                <option>INR</option><option>USD</option><option>EUR</option><option>GBP</option><option>AED</option><option>SGD</option>
              </select>
            </div>
          </div>

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

        </div>

        <div class="inv-dfooter" style="border-top:1px solid #e8ecf0;padding:14px 24px;background:#fafbfd">
          <button class="form-btn form-btn-outline" @click="showDrawer=false">Cancel</button>
          <button class="form-btn form-btn-primary" @click="saveVendor" :disabled="saving" style="background:#E67700;border-color:#E67700;min-width:140px;position:relative">
            <span v-if="saving" v-html="icon('refresh',13)" style="animation:spin 1s linear infinite"></span>
            {{saving ? 'Saving…' : (drawerMode==='add' ? 'Create Vendor' : 'Save Changes')}}
            <span v-if="Object.keys(formErrors).length && !saving"
              style="position:absolute;top:-6px;right:-6px;background:#dc2626;color:#fff;border-radius:10px;font-size:10px;font-weight:700;padding:1px 5px;min-width:16px;text-align:center;line-height:16px">
              {{Object.keys(formErrors).length}}
            </span>
          </button>
        </div>

      </div>
    </div>
  </Teleport>

  <!-- Delete Confirm -->
  <Teleport to="body">
    <div v-if="showDelete" class="nim-overlay" @click.self="showDelete=false">
      <div class="nim-dialog" style="max-width:420px">
        <div class="nim-header" style="background:linear-gradient(135deg,#dc2626,#b91c1c)">
          <div class="nim-header-left">
            <div class="nim-header-icon" style="color:#fff;">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/></svg>
            </div>
            <div class="nim-header-title">Delete Vendor?</div>
          </div>
          <button class="nim-close" @click="showDelete=false" v-html="icon('x',15)"></button>
        </div>
        <div class="nim-body" style="padding:20px 24px">
          <p style="font-size:14px;color:#374151;line-height:1.6">
            Are you sure you want to delete <strong>{{deleteTarget?.supplier_name}}</strong>?
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
        <div class="nim-header" style="background:linear-gradient(135deg,#2563eb,#1d4ed8)">
          <div class="nim-header-left">
            <div class="nim-header-icon" style="color:#fff;"><span v-html="icon('upload',16)"></span></div>
            <div class="nim-header-title">{{ importModal.done ? 'Import Complete' : 'Review Import' }}</div>
          </div>
          <button class="nim-close" @click="closeImport" :disabled="importModal.running" v-html="icon('x',15)"></button>
        </div>

        <div class="nim-body" style="padding:18px 22px">
          <!-- Preview phase -->
          <template v-if="!importModal.done">
            <div class="cus-import-stats">
              <div class="cus-import-stat"><div class="cus-import-stat-val">{{ importCounts.total }}</div><div class="cus-import-stat-lbl">Rows</div></div>
              <div class="cus-import-stat cus-import-stat-new"><div class="cus-import-stat-val">{{ importCounts.create }}</div><div class="cus-import-stat-lbl">New</div></div>
              <div class="cus-import-stat cus-import-stat-upd"><div class="cus-import-stat-val">{{ importCounts.update }}</div><div class="cus-import-stat-lbl">Update</div></div>
            </div>
            <div class="cus-import-note">
              Rows matching an existing vendor name will be <strong>updated</strong> (blank cells keep current values); the rest are <strong>created</strong>.
            </div>
            <div class="cus-import-table-wrap">
              <table class="cus-import-table">
                <thead>
                  <tr><th>Vendor</th><th>Type</th><th>GSTIN</th><th style="text-align:right">Action</th></tr>
                </thead>
                <tbody>
                  <tr v-for="(row,i) in importPreviewRows" :key="i">
                    <td>
                      <div class="cus-import-name">{{ row.vname }}</div>
                      <div class="cus-import-sub">{{ row.email || row.mobile || '\u2014' }}</div>
                    </td>
                    <td>{{ row.vtype }}</td>
                    <td class="cus-import-mono">{{ row.gstin || '\u2014' }}</td>
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

          <!-- Summary phase -->
          <template v-else>
            <div class="cus-import-stats">
              <div class="cus-import-stat cus-import-stat-new"><div class="cus-import-stat-val">{{ importModal.result.created }}</div><div class="cus-import-stat-lbl">Created</div></div>
              <div class="cus-import-stat cus-import-stat-upd"><div class="cus-import-stat-val">{{ importModal.result.updated }}</div><div class="cus-import-stat-lbl">Updated</div></div>
              <div class="cus-import-stat" :class="importModal.result.failed ? 'cus-import-stat-fail' : ''"><div class="cus-import-stat-val">{{ importModal.result.failed }}</div><div class="cus-import-stat-lbl">Failed</div></div>
            </div>
            <div class="cus-import-note" style="text-align:center">
              {{ importModal.result.failed
                  ? 'Some rows could not be saved \u2014 check that names/GSTINs are valid.'
                  : 'All rows imported successfully.' }}
            </div>
          </template>
        </div>

        <div class="inv-dfooter">
          <template v-if="!importModal.done">
            <button class="form-btn form-btn-outline" @click="closeImport" :disabled="importModal.running">Cancel</button>
            <button class="form-btn form-btn-primary" @click="runImport" :disabled="importModal.running || !importCounts.total"
              style="background:#2563eb;border-color:#2563eb;min-width:150px">
              <span v-if="importModal.running" v-html="icon('refresh',13)" style="animation:spin 1s linear infinite"></span>
              {{ importModal.running ? 'Importing\u2026' : `Import ${importCounts.total} Row(s)` }}
            </button>
          </template>
          <template v-else>
            <button class="form-btn form-btn-primary" @click="closeImport" style="background:#2563eb;border-color:#2563eb;min-width:110px">Done</button>
          </template>
        </div>
      </div>
    </div>
  </Teleport>

</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { apiList, apiGET, apiSave, apiSubmit, apiDelete, apiPOST, resolveCompany } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { usePermissions } from "../composables/usePermissions.js";
import { usePrompt } from "../composables/usePrompt.js";
import { useOpenFromQuery } from "../composables/useOpenFromQuery.js";
import AddressManager from "../components/AddressManager.vue";
import DocLink from "../components/DocLink.vue";
import { fmt, fmtDate } from "../utils/format.js";
import { icon } from "../utils/icons.js";
import { COUNTRIES, statesFor } from "../composables/useCountryState.js";
import {
  EMAIL_REGEX, GSTIN_REGEX, URL_REGEX, PAN_REGEX,
  validateMobile, validatePhone, validatePincode, sanitizePincode, pincodePlaceholder, pincodeHint,
} from "../composables/useValidation.js";


const { toast } = useToast();
const { canWrite } = usePermissions();
const { prompt } = usePrompt();

const list          = ref([]);
const loading       = ref(true);
const search        = ref("");
const activeFilter  = ref("all");
const viewMode      = ref("table"); // "table" | "grid"
const showDrawer    = ref(false);
const drawerMode    = ref("add");
const drawerTab     = ref("overview");
const drawerLoading = ref(false);
const saving        = ref(false);
const showDelete    = ref(false);
const deleteTarget  = ref(null);
const deleting      = ref(false);
const accounts      = ref([]);
const pendingAddresses = ref([]);

const collapsed = reactive({ address: false, otherDetails: false });

const SUPPLIER_TYPES = ["Company", "Individual", "Dealer", "Distributor"];

// Supplier type metadata
const STYPE_META = {
  "Company":     { bg: "#dbeafe", text: "#1d4ed8", icon: "🏢" },
  "Individual":  { bg: "#f1f5f9", text: "#475569", icon: "👤" },
  "Dealer":      { bg: "#fef9c3", text: "#a16207", icon: "🏪", desc: "Authorised dealer / reseller supplying stock" },
  "Distributor": { bg: "#dcfce7", text: "#15803d", icon: "🚚", desc: "Regional distributor / stockist supplying stock" },
};

// Supplier groups seeded for Ayurvedic raw material sourcing, plus
// distributor/dealer groups (Phase 2: Supplier & customer master setup
// with distributor/dealer groups)
const supplierGroups = ref([]);
const supplierGroupOptions = [
  "Raw Material Supplier", "Herb Supplier", "Mineral Supplier",
  "Packing Material Supplier", "Service Provider",
  "Equipment Supplier", "Contract Manufacturer", "Transporter",
];
const DEFAULT_SUPPLIER_GROUPS = {
  "Dealer":      ["Dealer - Local", "Dealer - Regional", "Dealer - National"],
  "Distributor": ["Distributor - State", "Distributor - Zone", "Distributor - National"],
};

const groupFilterV    = ref("");

const form = reactive({
  name: "",
  supplier_name: "", supplier_type: "Company",
  supplier_group: "",
  tax_id: "", default_currency: "INR", payment_terms: "",
  email_id: "", mobile_code: "+91", mobile_no: "", phone: "", website: "",
  address_line1: "", address_line2: "",
  city: "", state: "", pincode: "", country: "India",
  ship_address_line1: "", ship_address_line2: "",
  ship_city: "", ship_state: "", ship_pincode: "", ship_country: "India",
  default_payable_account: "", disabled: 0,
  tds_applicable: 0, tds_section: "", pan: "", opening_balance: 0,
});

const formErrors = reactive({});
const shipSameAsBilling = ref(false);

const counts = computed(() => ({
  all:         list.value.length,
  active:      list.value.filter((v) => !v.disabled).length,
  disabled:    list.value.filter((v) =>  v.disabled).length,
  dealer:      list.value.filter((v) => v.supplier_type === "Dealer").length,
  distributor: list.value.filter((v) => v.supplier_type === "Distributor").length,
}));

const filtered = computed(() => {
  let r = list.value;
  if (activeFilter.value === "active")      r = r.filter((v) => !v.disabled);
  if (activeFilter.value === "disabled")    r = r.filter((v) =>  v.disabled);
  if (activeFilter.value === "dealer")      r = r.filter((v) => v.supplier_type === "Dealer");
  if (activeFilter.value === "distributor") r = r.filter((v) => v.supplier_type === "Distributor");
  if (groupFilterV.value) r = r.filter((v) => v.supplier_group === groupFilterV.value);
  const q = search.value.toLowerCase().trim();
  if (q) r = r.filter((v) =>
    (v.supplier_name  || "").toLowerCase().includes(q) ||
    (v.name           || "").toLowerCase().includes(q) ||
    (v.email_id       || "").toLowerCase().includes(q) ||
    (v.mobile_no      || "").toLowerCase().includes(q) ||
    (v.tax_id         || "").toLowerCase().includes(q) ||
    (v.supplier_group || "").toLowerCase().includes(q)
  );
  return r;
});

async function load() {
  loading.value = true;
  try {
    const [rows, lastBills] = await Promise.all([
      apiList("Supplier", {
        fields: ["name","supplier_name","supplier_type","supplier_group","email_id","mobile_no",
          "tax_id","city","state","disabled","default_currency"],
        order: "supplier_name asc", limit: 300,
      }),
      apiGET("zoho_books_clone.api.books_data.get_vendor_last_bill").catch(() => ({})),
    ]);
    list.value = rows || [];
    lastBillByVendor.value = lastBills || {};

    // Supplier groups: "Supplier Group" is not a registered doctype in this app,
    // so combine the fixed sourcing-category list with dealer/distributor groups directly (no server call).
    const dealerDistGroups = [...DEFAULT_SUPPLIER_GROUPS.Dealer, ...DEFAULT_SUPPLIER_GROUPS.Distributor];
    supplierGroups.value = [...new Set([...supplierGroupOptions, ...dealerDistGroups])];

  } catch (e) {
    toast("Failed to load vendors: " + (e.message || e), "error");
  } finally { loading.value = false; }
}

async function loadAccounts() {
  try {
    const rows = await apiList("Account", {
      fields: ["name"],
      filters: [["account_type", "=", "Payable"], ["is_group", "=", 0]],
      limit: 50,
    });
    accounts.value = rows || [];
  } catch { accounts.value = []; }
}

function resetForm() {
  shipSameAsBilling.value = false;
  pendingAddresses.value = [];
  Object.assign(form, {
    name: "", supplier_name: "", supplier_type: "Company",
    supplier_group: "",
    tax_id: "", default_currency: "INR", payment_terms: "",
    email_id: "", mobile_code: "+91", mobile_no: "", phone: "", website: "",
    address_line1: "", address_line2: "",
    city: "", state: "", pincode: "", country: "India",
    ship_address_line1: "", ship_address_line2: "",
    ship_city: "", ship_state: "", ship_pincode: "", ship_country: "India",
    default_payable_account: "", disabled: 0,
    tds_applicable: 0, tds_section: "", pan: "", opening_balance: 0,
  });
  Object.keys(formErrors).forEach(k => delete formErrors[k]);
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

function openAdd() {
  resetForm();
  drawerMode.value = "add";
  drawerTab.value = "overview";
  showDrawer.value = true;
}

async function openEdit(name) {
  resetForm();
  drawerMode.value = "edit";
  drawerTab.value = "overview";
  drawerLoading.value = true;
  showDrawer.value = true;
  try {
    const doc = await apiGET("zoho_books_clone.api.docs.get_doc", { doctype: "Supplier", name });
    const mno = doc.mobile_no || "";
    Object.assign(form, {
      name: doc.name,
      supplier_name: doc.supplier_name || "",
      supplier_type: doc.supplier_type || "Company",
      supplier_group: doc.supplier_group || "",
      tax_id: doc.tax_id || "",
      default_currency: doc.default_currency || "INR",
      payment_terms: doc.payment_terms || "",
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
      default_payable_account: doc.default_payable_account || "",
      disabled: doc.disabled || 0,
      tds_applicable: doc.tds_applicable || 0,
      tds_section: doc.tds_section || "",
      pan: doc.pan || "",
      opening_balance: doc.opening_balance || 0,
    });
  } catch (e) {
    toast("Could not load vendor: " + (e.message || e), "error");
    showDrawer.value = false;
  } finally { drawerLoading.value = false; }
}

function validateField(field) {
  delete formErrors[field];
  const v = form[field];
  const s = typeof v === "string" ? v.trim() : v;

  if (field === "supplier_name") {
    if (!s) formErrors.supplier_name = "Vendor name is required";
    else if (s.length < 2) formErrors.supplier_name = "Name must be at least 2 characters";
    else if (s.length > 140) formErrors.supplier_name = "Name must not exceed 140 characters";
  }
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
  if (field === "tax_id" && s && form.country === "India" && !GSTIN_REGEX.test(s))
    formErrors.tax_id = "Invalid GSTIN format (e.g. 27AAPFU0939F1ZV)";
  if (field === "pincode" && s) {
    const err = validatePincode(s, form.country);
    if (err) formErrors.pincode = err;
  }
  if (field === "opening_balance" && v < 0)
    formErrors.opening_balance = "Opening balance cannot be negative";
}

function validateVendorForm() {
  Object.keys(formErrors).forEach((k) => delete formErrors[k]);
  if (!form.supplier_name.trim()) formErrors.supplier_name = "Vendor name is required";
  else if (form.supplier_name.trim().length < 2) formErrors.supplier_name = "Name must be at least 2 characters";
  if (form.email_id && !EMAIL_REGEX.test(form.email_id.trim())) formErrors.email_id = "Invalid email address";
  if (form.mobile_no) {
    const err = validateMobile(form.mobile_no.replace(/\D/g, ""), form.mobile_code);
    if (err) formErrors.mobile_no = err;
  }
  if (form.phone) { const err = validatePhone(form.phone); if (err) formErrors.phone = err; }
  if (form.website && !URL_REGEX.test(form.website.trim())) formErrors.website = "Website must start with http:// or https://";
  if (form.tax_id && form.country === "India" && !GSTIN_REGEX.test(form.tax_id.trim()))
    formErrors.tax_id = "Invalid GSTIN format (e.g. 27AAPFU0939F1ZV)";
  if (form.pincode) { const err = validatePincode(form.pincode, form.country); if (err) formErrors.pincode = err; }
  if (form.opening_balance < 0) formErrors.opening_balance = "Opening balance cannot be negative";
  return Object.keys(formErrors).length === 0;
}

async function saveVendor() {
  if (!validateVendorForm()) {
    const firstErr = Object.values(formErrors)[0];
    drawerTab.value = "overview";
    toast(firstErr || "Please fix the errors before saving", "error");
    return;
  }
  saving.value = true;
  try {
    const booksCompany = await resolveCompany();
    const doc = {
      doctype: "Supplier",
      ...(drawerMode.value === "edit" ? { name: form.name } : { naming_series: "SUPP-.YYYY.-.#####" }),
      books_company: booksCompany,
      supplier_name: form.supplier_name.trim(),
      supplier_type: form.supplier_type,
      supplier_group: form.supplier_group,
      tax_id: form.tax_id.trim(),
      default_currency: form.default_currency,
      payment_terms: form.payment_terms,
      email_id: form.email_id.trim(),
      mobile_no: form.mobile_no.trim() ? (form.mobile_code + " " + form.mobile_no.trim()) : "",
      phone: form.phone.trim(),
      website: form.website.trim(),
      address_line1: form.address_line1.trim(),
      address_line2: form.address_line2.trim(),
      city: form.city.trim(),
      state: form.state.trim(),
      pincode: form.pincode.trim(),
      country: form.country.trim() || "India",
      ship_address_line1: form.ship_address_line1.trim(),
      ship_address_line2: form.ship_address_line2.trim(),
      ship_city: form.ship_city.trim(),
      ship_state: form.ship_state.trim(),
      ship_pincode: form.ship_pincode.trim(),
      ship_country: form.ship_country.trim() || "India",
      default_payable_account: form.default_payable_account,
      disabled: form.disabled ? 1 : 0,
      tds_applicable: form.tds_applicable ? 1 : 0,
      tds_section: form.tds_section,
      pan: form.pan.trim(),
      opening_balance: parseFloat(form.opening_balance) || 0,
    };
    let doc_to_save = doc;
    if (drawerMode.value === "edit") {
      const fresh = await apiGET("zoho_books_clone.api.docs.get_doc", { doctype: "Supplier", name: form.name });
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
            links: [{ link_doctype: "Supplier", link_name: savedName }],
          });
        } catch {}
      }
      // Sync first billing address onto Supplier doctype for detail view display
      const firstBilling = pendingAddresses.value.find(a => a.address_type === "Billing");
      if (firstBilling) {
        try {
          await apiSave({
            doctype: "Supplier", name: savedName,
            address_line1: firstBilling.address_line1,
            address_line2: firstBilling.address_line2 || "",
            city: firstBilling.city || "", state: firstBilling.state || "",
            pincode: firstBilling.pincode || "", country: firstBilling.country || "India",
          });
        } catch {}
      }
    }

    toast(drawerMode.value === "edit" ? "Vendor updated!" : "Vendor created!");
    showDrawer.value = false;
    await load();
  } catch (e) {
    toast(e.message || "Could not save vendor", "error");
  } finally { saving.value = false; }
}

function confirmDelete(v) {
  deleteTarget.value = v;
  showDelete.value = true;
}

async function doDelete() {
  if (!deleteTarget.value) return;
  deleting.value = true;
  try {
    const delName = deleteTarget.value.name;
    await apiPOST("zoho_books_clone.api.docs.safe_delete_party", {
      doctype: "Supplier", name: delName,
    });
    toast("Vendor deleted");
    showDelete.value = false;
    deleteTarget.value = null;
    if (selectedVendor.value && selectedVendor.value.name === delName) {
      selectedVendor.value = null;
    }
    await load();
    loadAllBalances();
  } catch (e) {
    toast(e.message || "Could not delete vendor", "error");
  } finally { deleting.value = false; }
}

const selectedVendor  = ref(null);
const activeVendorTab = ref("overview");

// ── Live vendor data wired to backend ──────────────────────────────────────
const vendorSummary      = ref({});       // {outstanding, dn_credit, open_bill_count, ...}
const obInfo         = ref({ has_opening_je: false });
const showPayModal   = ref(false);
const payLoading     = ref(false);
const payForm        = reactive({ amount: 0, bank_cash_account: "", payment_date: new Date().toISOString().slice(0, 10) });
const vendorTxns         = ref([]);       // chronological transactions
const vendorStatement    = ref({ rows: [], totals: {} });
const balancesByVendor   = ref({});       // {vendor_name: outstanding} — for the list view
const lastBillByVendor   = ref({});       // {vendor_name: {name, date, amount}} — for the list view
const detailLoading      = ref(false);
const stmtRange          = reactive({ from: "", to: "" });

// ── Load-more pagination ───────────────────────────────────────────────────
const TXN_PAGE_SIZE  = 10;
const STMT_PAGE_SIZE = 10;
const txnPage        = ref(1);
const stmtPage       = ref(1);
// Transactions enriched with a running payable balance (oldest → newest).
// vendorTxns is newest-first; we walk it in reverse to accumulate, then expose
// the balance after each transaction keyed back onto the newest-first list.
const vendorTxnsActive = computed(() => vendorTxns.value.filter((t) => t.docstatus !== 2 && t.status !== "Cancelled"));
const vendorTxnsWithBalance = computed(() => {
  const asc = [...vendorTxnsActive.value].reverse();   // oldest first
  let running = 0;
  const balById = new Map();
  for (const t of asc) {
    running += Number(t.amount || 0);            // Bill +, Payment/Debit Note −
    balById.set(t.type + "-" + t.name, running);
  }
  return vendorTxnsActive.value.map(t => ({ ...t, balance: balById.get(t.type + "-" + t.name) || 0 }));
});
const vendorTxnsVisible  = computed(() => vendorTxnsWithBalance.value.slice(0, txnPage.value  * TXN_PAGE_SIZE));
const vendorTxnsHasMore  = computed(() => vendorTxnsActive.value.length > txnPage.value  * TXN_PAGE_SIZE);

// Human-friendly status label for a transaction row
function txnStatusLabel(t) {
  if (t.docstatus === 2) return "Cancelled";
  if (t.docstatus === 0) return "Draft";
  return t.status || "Submitted";
}
function txnStatusStyle(t) {
  const label = txnStatusLabel(t);
  if (label === "Cancelled") return "background:#F3F4F6;color:#6B7280";
  if (label === "Draft")     return "background:#FEF9C3;color:#854D0E";
  if (label === "Paid")      return "background:#D1FAE5;color:#059669";
  if (label === "Overdue")   return "background:#FEE2E2;color:#991B1B";
  if (label === "Partly Paid") return "background:#FEF3C7;color:#92400E";
  return "background:#DBEAFE;color:#1E40AF";
}
const stmtRowsVisible    = computed(() => (vendorStatement.value.rows || []).slice(0, stmtPage.value * STMT_PAGE_SIZE));
const stmtRowsHasMore    = computed(() => (vendorStatement.value.rows || []).length > stmtPage.value * STMT_PAGE_SIZE);

// Bulk selection (for the flat table)
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

async function selectVendor(v) {
  selectedVendor.value = v;
  activeVendorTab.value = "overview";
  detailLoading.value = true;
  vendorSummary.value = {};
  vendorTxns.value = [];
  vendorStatement.value = { rows: [], totals: {} };
  txnPage.value = 1;
  stmtPage.value = 1;
  obInfo.value = { has_opening_je: false };
  try {
    const [sum, txns, fullDoc] = await Promise.all([
      apiGET("zoho_books_clone.api.docs.get_vendor_summary", { vendor: v.name }).catch(() => ({})),
      apiGET("zoho_books_clone.api.docs.get_vendor_transactions", { vendor: v.name, limit: 100 }).catch(() => []),
      apiGET("zoho_books_clone.api.docs.get_doc", { doctype: "Supplier", name: v.name }).catch(() => null),
    ]);
    vendorSummary.value = sum || {};
    vendorTxns.value = txns || [];
    if (fullDoc) selectedVendor.value = { ...v, ...fullDoc };
  } catch (e) { /* keep panel open */ }
  detailLoading.value = false;
  loadOpeningBalance();
}
function closeVendor() { selectedVendor.value = null; }
function vendDocTypeFor(type) {
  return type === "Bill" ? "Purchase Invoice"
    : type === "Debit Note" ? "Debit Note"
    : type === "Payment" ? "Payment Entry" : "";
}

async function loadOpeningBalance() {
  if (!selectedVendor.value) return;
  obInfo.value = await apiGET(
    "zoho_books_clone.accounts.opening_balance.get_opening_balance_payment_info",
    { party_type: "Supplier", party: selectedVendor.value.name }
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
  if (!payForm.bank_cash_account) { toast("Choose an account to pay from", "error"); return; }
  if (!amount || amount <= 0) { toast("Enter a valid amount", "error"); return; }
  if (amount > obInfo.value.outstanding + 0.01) { toast("Amount exceeds outstanding opening balance", "error"); return; }

  payLoading.value = true;
  try {
    const doc = {
      doctype: "Payment Entry",
      payment_type: "Pay",
      party_type: "Supplier",
      party: selectedVendor.value.name,
      party_name: selectedVendor.value.supplier_name,
      company: obInfo.value.company,
      paid_from: payForm.bank_cash_account,
      paid_to: obInfo.value.party_account,
      paid_amount: amount,
      received_amount: amount,
      payment_date: payForm.payment_date,
      remarks: `Opening balance payment for ${selectedVendor.value.supplier_name || selectedVendor.value.name}`,
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
    // list, the PAYABLES card, and (if open) the Transactions/Statement
    // tabs — otherwise they keep showing the pre-payment amount until a
    // full page reload.
    const [sum, txns] = await Promise.all([
      apiGET("zoho_books_clone.api.docs.get_vendor_summary", { vendor: selectedVendor.value.name }).catch(() => ({})),
      apiGET("zoho_books_clone.api.docs.get_vendor_transactions", { vendor: selectedVendor.value.name, limit: 100 }).catch(() => []),
    ]);
    vendorSummary.value = sum || {};
    vendorTxns.value = txns || [];
    loadAllBalances();
    if (activeVendorTab.value === "statement") await loadStatement();
  } catch (e) {
    toast(e.message || "Failed to record payment", "error");
  } finally {
    payLoading.value = false;
  }
}

async function loadStatement() {
  if (!selectedVendor.value) return;
  detailLoading.value = true;
  stmtPage.value = 1;
  try {
    vendorStatement.value = await apiGET("zoho_books_clone.api.docs.get_vendor_statement", {
      vendor: selectedVendor.value.name,
      from_date: stmtRange.from || "",
      to_date:   stmtRange.to   || "",
    }) || { rows: [], totals: {} };
  } catch (e) { toast(e.message || "Failed to load statement", "error"); }
  detailLoading.value = false;
}

// ── Vendor statement PDF export ─────────────────────────────────────────
// Same running-balance ledger layout used for the Customer statement PDF,
// built client-side from vendorStatement (already has date/type/ref/debit/
// credit/balance per row) and rendered server-side via render_pdf_from_html.
const downloadingVendorStmtPdf = ref(false);

function fmtVendStmtDate(d) {
  if (!d) return "";
  const dt = new Date(d);
  if (isNaN(dt)) return String(d);
  return dt.toLocaleDateString("en-GB", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function buildVendorStatementPdfHtml() {
  const vendName = selectedVendor.value?.supplier_name || selectedVendor.value?.name || "";
  const company = window.__booksCompany || "";
  const today = new Date().toLocaleDateString("en-GB", { day: "2-digit", month: "2-digit", year: "numeric" });

  const rowsHtml = (vendorStatement.value.rows || []).map(r => `<tr>
      <td>${fmtVendStmtDate(r.date)}</td>
      <td>${r.type || ""}</td>
      <td>${r.ref || ""}</td>
      <td class="num">${Number(r.debit||0) ? fmtCur(r.debit) : ""}</td>
      <td class="num">${Number(r.credit||0) ? fmtCur(r.credit) : ""}</td>
      <td class="num bal">${fmtCur(r.balance)}</td>
    </tr>`).join("");

  const closing = vendorStatement.value.totals?.closing_balance || 0;
  const rangeLabel = stmtRange.from || stmtRange.to
    ? `From ${stmtRange.from || "start"} to ${stmtRange.to || "today"}`
    : `As on ${today}`;

  return `<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @page { size: A4; margin: 18mm 14mm; }
  * { box-sizing: border-box; }
  body { font-family: Arial, Helvetica, sans-serif; color: #1a1a1a; font-size: 12px; }
  .stmt-header { text-align: center; margin-bottom: 4px; }
  .stmt-company { font-size: 16px; font-weight: 700; letter-spacing: .02em; }
  .stmt-title { font-size: 13px; font-weight: 600; margin-top: 10px; }
  .stmt-sub { font-size: 11.5px; color: #444; margin-top: 2px; }
  table { width: 100%; border-collapse: collapse; margin-top: 14px; }
  th, td { border: 1px solid #999; padding: 5px 8px; font-size: 11.5px; }
  th { background: #f0f0f0; text-align: left; font-weight: 700; }
  td.num, th.num { text-align: right; white-space: nowrap; }
  td.bal { font-weight: 600; }
  tfoot td { font-weight: 700; background: #f7f7f7; }
</style></head>
<body>
  <div class="stmt-header">
    ${company ? `<div class="stmt-company">${company}</div>` : ""}
    <div class="stmt-title">Vendor Account Statement</div>
    <div class="stmt-sub">Account: ${vendName} &nbsp;|&nbsp; ${rangeLabel}</div>
  </div>
  <table>
    <thead>
      <tr>
        <th>Date</th>
        <th>Type</th>
        <th>Ref No</th>
        <th class="num">Debit</th>
        <th class="num">Credit</th>
        <th class="num">Balance</th>
      </tr>
    </thead>
    <tbody>${rowsHtml}</tbody>
    <tfoot>
      <tr>
        <td colspan="5">Closing Balance</td>
        <td class="num">${fmtCur(closing)}</td>
      </tr>
    </tfoot>
  </table>
</body></html>`;
}

async function downloadVendorStatementPdf() {
  if (!vendorStatement.value.rows?.length) { toast("No statement rows to export", "error"); return; }
  downloadingVendorStmtPdf.value = true;
  try {
    const html = buildVendorStatementPdfHtml();
    const filename = `vendor-statement-${selectedVendor.value.name}-${new Date().toISOString().slice(0,10)}.pdf`;
    const csrf = window.frappe?.csrf_token || "";
    const res = await fetch("/api/method/zoho_books_clone.api.docs.render_pdf_from_html", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded", "X-Frappe-CSRF-Token": csrf },
      credentials: "same-origin",
      body: new URLSearchParams({ pdf_html: html, filename }),
    });
    if (!res.ok) throw new Error("PDF generation failed");
    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = objectUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(objectUrl), 5000);
  } catch (e) {
    toast("Failed to generate statement PDF", "error");
  }
  downloadingVendorStmtPdf.value = false;
}

async function emailVendorStatement() {
  if (!selectedVendor.value) return;
  try {
    const d = await apiGET("zoho_books_clone.api.docs.get_vendor_email_defaults",
      { vendor: selectedVendor.value.name });
    const to = await prompt({
      title: "Email Statement",
      label: "Send statement to:",
      defaultValue: d?.to || "",
      placeholder: "name@example.com",
      okLabel: "Send",
      inputType: "email",
    });
    if (!to) return;
    await (await import("../api/client.js")).apiPOST("zoho_books_clone.api.docs.send_vendor_statement_email", {
      vendor: selectedVendor.value.name,
      to, subject: d?.subject || "Statement", body: d?.body || "",
    });
    toast(`Statement emailed to ${to}`, "success");
  } catch (e) { toast(e.message || "Email failed", "error"); }
}

async function bulkSetDisabled(disable) {
  if (!canWrite("customers")) { toast("Read-only access", "error"); return; }
  const names = [...selectedRows.value];
  if (!names.length) { toast("No vendors selected", "info"); return; }
  bulkBusy.value = true;
  try {
    const { apiPOST } = await import("../api/client.js");
    await apiPOST("zoho_books_clone.api.docs.bulk_set_vendor_disabled", {
      vendor_names: JSON.stringify(names),
      disabled: disable ? 1 : 0,
    });
    toast(`${disable ? "Disabled" : "Enabled"} ${names.length} vendor(s)`, "success");
    clearSelection();
    await load();
  } catch (e) { toast(e.message || "Bulk update failed", "error"); }
  finally { bulkBusy.value = false; }
}

function exportCSV() {
  const rows = selectedRows.value.size
    ? filtered.value.filter(v => selectedRows.value.has(v.name))
    : filtered.value;
  if (!rows.length) return;
  const head = ["Vendor","Type","GSTIN","Email","Mobile","City","State","Outstanding","Status"];
  const esc = v => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const out = [head.map(esc).join(",")];
  for (const v of rows) {
    out.push([
      v.supplier_name || v.name, v.supplier_type || "", v.tax_id || "",
      v.email_id || "", v.mobile_no || "", v.city || "", v.state || "",
      Number(balancesByVendor.value[v.name] || 0).toFixed(2),
      v.disabled ? "Disabled" : "Active",
    ].map(esc).join(","));
  }
  const blob = new Blob(["﻿" + out.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `vendors_${new Date().toISOString().slice(0,10)}.csv`;
  a.click(); URL.revokeObjectURL(url);
  toast(`Exported ${rows.length} vendor(s)`, "success");
}

const totalPayable = computed(() =>
  Object.values(balancesByVendor.value).reduce((s, x) => s + Number(x || 0), 0)
);
const vendorsWithBalance = computed(() =>
  Object.values(balancesByVendor.value).filter(x => Number(x) > 0).length
);

const vendorKpiCards = computed(() => [
  {
    key: "total", label: "Total Vendors", format: "number",
    value: list.value.length, sub: "all vendors",
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2" stroke-linecap="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
    iconBg: "#eff6ff", valueClass: "bk-kpi-blue",
  },
  {
    key: "active", label: "Active", format: "number",
    value: list.value.filter(v => !v.disabled).length, sub: "enabled",
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2" stroke-linecap="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/><polyline points="16 11 18 13 22 9"/></svg>`,
    iconBg: "#f0fdf4", valueClass: "bk-kpi-green",
  },
  {
    key: "with_balance", label: "With Open Balance", format: "number",
    value: vendorsWithBalance.value, sub: "outstanding payables",
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
    iconBg: "#fff7ed", valueClass: "bk-kpi-amber",
  },
  {
    key: "total_payable", label: "Total Payable", format: "currency",
    value: totalPayable.value, sub: "accounts payable",
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12"/><path d="M6 8h12"/><path d="m6 13 8.5 8"/><path d="M6 13h3"/><path d="M9 13c6.667 0 6.667-10 0-10"/></svg>`,
    iconBg: "#fef2f2", valueClass: "bk-kpi-red",
  },
]);

function vendorInitials(name) {
  return (name || "?").split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2);
}
function fmtCur(v) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 2 }).format(Number(v || 0));
}

async function loadAllBalances() {
  // Single batched query for every vendor's outstanding payables
  try {
    const map = await apiGET("zoho_books_clone.api.books_data.get_vendor_outstanding");
    balancesByVendor.value = map || {};
  } catch {
    balancesByVendor.value = {};
  }
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

// Map existing display names (lowercased) -> Supplier id, for upsert matching
function buildExistingNameMap() {
  const m = {};
  for (const v of list.value) {
    const key = (v.supplier_name || "").trim().toLowerCase();
    if (key && !(key in m)) m[key] = v.name;
  }
  return m;
}

// Phase 1: parse CSV, classify rows as new/update, open preview dialog
async function importCSV(e) {
  const file = e.target.files && e.target.files[0];
  if (importInput.value) importInput.value.value = "";
  if (!file) return;
  try {
    const text = await file.text();
    const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/).filter(l => l.trim().length);
    if (lines.length < 2) { toast("CSV has no data rows", "error"); return; }
    const header = parseCsvLine(lines[0]).map(h => h.toLowerCase());
    const idx = (...names) => { for (const n of names) { const i = header.indexOf(n); if (i !== -1) return i; } return -1; };
    const col = {
      name:   idx("name", "vendor", "supplier", "vendor name", "supplier name", "display name"),
      type:   idx("type", "vendor type", "supplier type"),
      gstin:  idx("gstin", "gstin / tax id", "tax id", "tax_id"),
      email:  idx("email", "email address", "email_id"),
      mobile: idx("mobile", "mobile no", "phone"),
      city:   idx("city"),
      state:  idx("state"),
    };
    if (col.name === -1) { toast('CSV must have a "Name" or "Vendor Name" column', "error"); return; }
    const existing = buildExistingNameMap();
    const rows = [];
    for (let r = 1; r < lines.length; r++) {
      const cells = parseCsvLine(lines[r]);
      const vname = (cells[col.name] || "").trim();
      if (!vname) continue;
      const rawType = col.type !== -1 ? (cells[col.type] || "").trim() : "";
      const vtype = SUPPLIER_TYPES.includes(rawType) ? rawType : "Company";
      const existingName = existing[vname.toLowerCase()] || "";
      rows.push({
        vname, vtype,
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

// Build save payload. On update, blank cells are omitted so existing data is kept.
function buildImportPayload(row, isUpdate) {
  const p = { supplier_name: row.vname, supplier_type: row.vtype };
  if (row.vtype !== "Individual") p.company_name = row.vname;
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

// Phase 2: execute upsert, then show summary
async function runImport() {
  if (!importModal.rows.length || importModal.running) return;
  importModal.running = true;
  let created = 0, updated = 0, failed = 0;
  try {
    const booksCompany = await resolveCompany();
    for (const row of importModal.rows) {
      try {
        if (row.action === "update" && row.existingName) {
          const fresh = await apiGET("zoho_books_clone.api.docs.get_doc", { doctype: "Supplier", name: row.existingName });
          await apiSave({ ...fresh, ...buildImportPayload(row, true), doctype: "Supplier", name: row.existingName });
          updated++;
        } else {
          await apiSave({ doctype: "Supplier", naming_series: "SUPP-.YYYY.-.#####", books_company: booksCompany, ...buildImportPayload(row, false) });
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


const route = useRoute();
onMounted(async () => {
  await load();
  loadAccounts();
  loadAllBalances();
  useOpenFromQuery({ route, openByName: (n) => selectVendor(list.value.find(v => v.name === n) || { name: n }) });
});
</script>

<style scoped>
.ven-pay-modal-overlay{position:fixed;inset:0;background:rgba(15,23,42,.45);display:flex;align-items:center;justify-content:center;z-index:100;}
.ven-pay-modal{background:#fff;border-radius:12px;padding:22px;width:340px;box-shadow:0 10px 30px rgba(0,0,0,.15);}
/* ── Drawer slide-in animation ──────────────────────────── */
.inv-drawer-panel {
  width: min(600px, 96vw);
  transform: translateX(100%);
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.inv-drawer-panel.open {
  transform: translateX(0);
}

/* ── Vendor avatar circle (orange gradient) ─────────────── */
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
  background: linear-gradient(135deg, #E67700, #C96200);
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

/* ── Vendor-specific column helpers ─────────────────────── */
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
.vt-th-check  { width: 36px; padding-left: 16px; }
.vt-th-num    { text-align: right; }
.vt-th-actions { text-align: center; width: 88px; }
.vt-td {
  padding: 11px 14px;
  vertical-align: middle;
  color: #374151;
  white-space: nowrap;
}
.vt-td-check  { padding-left: 16px; width: 36px; }
.vt-td-num    { text-align: right; }
.vt-td-mono   { font-size: 13px; color: #374151; }
.vt-td-secondary { color: #6b7280; font-size: 12.5px; }
.vt-td-actions { text-align: center; width: 88px; }
.vt-checkbox { width: 15px; height: 15px; accent-color: #E67700; cursor: pointer; border-radius: 3px; }
.vt-row-shimmer td { padding: 13px 14px; }
.vt-row-disabled   { opacity: 0.55; }
.vt-row-selected   { background: #fff7ed !important; }
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
.vt-amount-due { font-weight: 600; color: #E67700; font-size: 13px; }
.vt-amount-nil { color: #d1d5db; }
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

/* ── Mobile card view ── */
.ven-mobile-cards { display: none; }
.ven-desktop-table { display: table; }

/* ── Transactions / Statement: mobile cards hidden by default ── */
.ven-txn-mobile-cards  { display: none; }
.ven-stmt-mobile-cards { display: none; }

/* ── Load-more bar ── */
.ven-load-more-wrap {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #FAFAFA;
}
.ven-load-more-end {
  justify-content: center;
  color: #9CA3AF;
  font-size: 12px;
}
.ven-load-more-count {
  font-size: 12px;
  color: #6B7280;
}
.ven-load-more-btn {
  font-size: 12.5px;
  font-weight: 600;
  color: #2563EB;
  background: #EFF6FF;
  border: 1px solid #BFDBFE;
  border-radius: 7px;
  padding: 5px 14px;
  cursor: pointer;
  transition: background .13s;
}
.ven-load-more-btn:hover { background: #DBEAFE; }

@media (max-width: 768px) {
  .ven-desktop-table { display: none !important; }
  .ven-mobile-cards { display: flex; flex-direction: column; gap: 0; background: #f8fafc; }
  .ven-mobile-card { background: #fff; border-bottom: 1px solid #e5e7eb; padding: 12px 14px; cursor: pointer; transition: background .12s; }
  .ven-mobile-card:active { background: #f8f9fc; }
  .ven-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
  .ven-mc-name { font-size: 14px; font-weight: 700; color: #1a1d23; }
  .ven-mc-meta { display: flex; justify-content: space-between; font-size: 12px; color: #868e96; margin-bottom: 8px; }
  .ven-mc-footer { display: flex; gap: 6px; }
  .ven-mc-btn { flex: 1; padding: 6px 10px; border-radius: 7px; font-size: 12px; font-weight: 600; cursor: pointer; background: #f1f5f9; border: 1px solid #e2e8f0; color: #374151; }
  .ven-mc-danger { background: #fff1f2; border-color: #fecaca; color: #dc2626; }
  .ven-mc--skeleton { pointer-events: none; }
  .ven-mc-shimmer { border-radius: 6px; background: linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size: 200% 100%; animation: ven-shimmer 1.4s infinite; }
  @keyframes ven-shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
  .ven-mc-empty { text-align: center; padding: 32px 16px; color: #868e96; font-size: 13px; }

  /* ── Detail panel: hide left pane, go full-width ── */
  .zb-master-detail { flex-direction: column !important; height: auto !important; min-height: calc(100vh - 56px); }
  .zb-list-pane { display: none !important; }

  /* ── Overview: stack two columns vertically ── */
  .ven-overview-cols { flex-direction: column !important; }
  .ven-overview-cols > div { flex: none !important; width: 100% !important; min-width: 0 !important; }

  /* ── Payables table: compact + wrap headers ── */
  .ven-recv-table th {
    font-size: 9.5px !important;
    padding: 6px 8px !important;
    white-space: normal !important;
    word-break: break-word !important;
    line-height: 1.3 !important;
  }
  .ven-recv-table td { font-size: 12px !important; padding: 8px !important; }

  /* ── Transactions tab: switch to card view ── */
  .ven-txn-wrap { overflow: visible !important; border: none !important; background: transparent !important; }
  .ven-txn-desktop { display: none !important; }
  .ven-txn-mobile-cards { display: flex; flex-direction: column; gap: 8px; }
  .ven-txn-mc { background: #fff; border: 1px solid #E5E7EB; border-radius: 10px; padding: 12px 14px; }
  .ven-txn-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
  .ven-txn-mc-badge { font-size: 10.5px; font-weight: 700; padding: 2px 8px; border-radius: 10px; }
  .ven-txn-mc-amount { font-size: 14px; font-weight: 700; }
  .ven-txn-mc-mid { display: flex; align-items: center; justify-content: space-between; }
  .ven-txn-mc-ref { font-size: 13px; font-weight: 600; color: #2563EB; }
  .ven-txn-mc-date { font-size: 12px; color: #6B7280; }
  .ven-txn-mc-outstanding { margin-top: 8px; padding-top: 8px; border-top: 1px solid #F3F4F6; font-size: 12px; color: #E67700; }

  /* ── Statement tab: card view ── */
  .ven-stmt-desktop { display: none !important; }
  .ven-stmt-mobile-cards { display: flex; flex-direction: column; gap: 8px; padding: 8px; }
  .ven-stmt-mc { background: #fff; border: 1px solid #E5E7EB; border-radius: 10px; padding: 12px 14px; }
  .ven-stmt-mc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .ven-stmt-mc-ref { font-size: 13.5px; font-weight: 600; color: #2563EB; }
  .ven-stmt-mc-type { font-size: 11px; font-weight: 600; color: #6B7280; background: #F3F4F6; padding: 2px 8px; border-radius: 10px; }
  .ven-stmt-mc-date { font-size: 12px; color: #6B7280; margin-bottom: 8px; }
  .ven-stmt-mc-amounts { display: flex; gap: 12px; flex-wrap: wrap; padding-top: 8px; border-top: 1px solid #F3F4F6; }
  .ven-stmt-mc-debit  { display: flex; flex-direction: column; font-size: 13px; font-weight: 700; color: #059669; }
  .ven-stmt-mc-credit { display: flex; flex-direction: column; font-size: 13px; font-weight: 700; color: #E67700; }
  .ven-stmt-mc-balance { display: flex; flex-direction: column; font-size: 13px; font-weight: 700; color: #111827; margin-left: auto; text-align: right; }
  .ven-stmt-mc-lbl { font-size: 9.5px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: #9CA3AF; margin-bottom: 2px; }

  /* ── Statement KPIs: 1-col on mobile (inline-style override) ── */
  .ven-stmt-kpis { grid-template-columns: 1fr !important; gap: 8px !important; }

  /* ── New/Edit Vendor form: stack multi-col grids to 1 col ── */
  .ven-form-grid2 { grid-template-columns: 1fr !important; }
  .ven-form-grid3 { grid-template-columns: 1fr !important; }
  [style*="grid-template-columns:1fr 1fr"],
  [style*="grid-template-columns: 1fr 1fr"],
  [style*="grid-template-columns:1fr 1fr 1fr"],
  [style*="grid-template-columns: 1fr 1fr 1fr"] {
    grid-template-columns: 1fr !important;
  }

  :deep(.inv-add-drawer),
  :deep(.ven-add-drawer) {
    width: 100vw !important;
    right: -100vw !important;
    max-width: 100vw !important;
  }
  :deep(.inv-add-drawer.open),
  :deep(.ven-add-drawer.open) { right: 0 !important; }

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

  /* ── Bank Details grid: force single column ── */
  .ven-bank-grid { grid-template-columns: 1fr !important; }
  .ven-bank-full { grid-column: span 1 !important; }

  /* ── Drawer footer: sticky row layout ── */
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
  :deep(.inv-dfooter) .form-btn-primary { flex: 2 !important; }
}

@media (max-width: 480px) {
  .view-toggle-btn { display: none !important; }
}

/* ── CSV Import Modal styles ────────────────────────────────────────────── */
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
.cus-import-mono {font-size: 11.5px; color: #374151; }
.cus-import-badge { font-size: 10.5px; font-weight: 700; padding: 2px 9px; border-radius: 12px; }
.cus-import-badge-new { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
.cus-import-badge-upd { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
.cus-import-more { padding: 8px 12px; font-size: 11.5px; color: #9ca3af; text-align: center; background: #fafbfd; }

</style>