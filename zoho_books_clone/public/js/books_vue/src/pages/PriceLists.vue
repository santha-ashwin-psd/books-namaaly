<template>
<div class="b-page pl-root">

  <!-- ══ A. SIDEBAR ══ -->
  <div class="pl-sidebar">

    <!-- A1. Header -->
    <div class="pl-sidebar-head">
      <div class="pl-sidebar-title">
        Price Lists
        <span class="pl-count-chip">{{ priceLists.length }}</span>
      </div>
      <button class="b-btn b-btn-primary pl-new-btn" :disabled="!$canWrite('inventory')" :title="!$canWrite('inventory') ? 'Read-only access' : ''" @click="openNewListDialog">
        <span v-html="icon('plus', 12)"></span> New
      </button>
    </div>

    <!-- A2. Tab pills -->
    <div class="pl-tab-row">
      <button v-for="t in listTabs" :key="t.k"
        class="pl-tab-pill" :class="{ active: listTab === t.k }"
        @click="listTab = t.k">{{ t.label }}</button>
    </div>

    <!-- A3. Search -->
    <div class="pl-sidebar-search">
      <span v-html="icon('search', 12)" style="flex-shrink:0;color:#868E96"></span>
      <input v-model="listSearch" placeholder="Search price lists…"/>
    </div>

    <!-- A4. Cards -->
    <div class="pl-sidebar-body">
      <template v-if="loadingLists">
        <div v-for="n in 4" :key="n" class="pl-card-shimmer b-shimmer"></div>
      </template>
      <template v-else>
        <div v-if="!filteredLists.length" class="pl-sidebar-empty">No price lists match</div>
        <div v-for="pl in filteredLists" :key="pl.name"
          class="pl-card" :class="{ 'pl-card-active': selectedList?.name === pl.name }"
          @click="selectList(pl)">

          <div class="pl-card-icon"
            :class="pl.selling && pl.buying ? 'pl-icon-both' : pl.selling ? 'pl-icon-sell' : 'pl-icon-buy'">
            {{ pl.selling && pl.buying ? '🔄' : pl.selling ? '🏷️' : '🛒' }}
          </div>

          <div class="pl-card-info">
            <div class="pl-card-name">{{ pl.name }}</div>
            <div class="pl-card-sub">
              {{ pl.selling && pl.buying ? 'Both' : pl.selling ? 'Selling' : 'Buying' }}
              · {{ pl.currency || 'INR' }}
              <span v-if="pl._ic != null"> · {{ pl._ic }} item{{ pl._ic !== 1 ? 's' : '' }}</span>
            </div>
          </div>

          <!-- Status toggle -->
          <button class="pl-toggle" :class="{ active: pl.enabled }"
            @click.stop="toggleEnabled(pl)"
            :title="pl.enabled ? 'Disable' : 'Enable'">
            <span class="pl-toggle-dot"></span>
          </button>

          <!-- Edit icon (shows on card hover) -->
          <button class="pl-dots-btn" @click.stop="openCardMenu(pl, $event)"
           ><span class="ba-kebab-dots"></span></button>
        </div>
      </template>
    </div>

    <!-- A6. Bottom new btn -->
    <div class="pl-sidebar-foot">
      <button class="b-btn b-btn-ghost" style="width:100%;font-size:12px" @click="openNewListDialog">
        <span v-html="icon('plus', 11)" style="vertical-align:-1px;margin-right:4px"></span>
        New Price List
      </button>
    </div>
  </div>

  <!-- ══ MOBILE TOOLBAR (≤768px) ══ -->
  <div class="pl-mob-toolbar">
    <!-- Price list picker -->
    <div class="pl-mob-group-wrap">
      <span class="pl-mob-group-prefix">List</span>
      <div class="pl-mob-group-select-wrap">
        <select class="pl-mob-group-select"
          :value="selectedList?.name || ''"
          @change="e => { const pl = priceLists.find(p => p.name === e.target.value); if (pl) selectList(pl); }">
          <option value="">— Select list —</option>
          <option v-for="pl in filteredLists" :key="pl.name" :value="pl.name">
            {{ pl.name }} ({{ pl.selling && pl.buying ? 'Both' : pl.selling ? 'Selling' : 'Buying' }})
          </option>
        </select>
        <span class="pl-mob-group-chev" v-html="icon('chevD', 12)"></span>
      </div>
    </div>

    <!-- Tab filter -->
    <div class="pl-mob-tab-row">
      <button v-for="t in listTabs" :key="t.k"
        class="pl-mob-tab-pill" :class="{ active: listTab === t.k }"
        @click="listTab = t.k">{{ t.label }}</button>
    </div>

    <div style="flex:1"></div>

    <!-- New button -->
    <button class="pl-mob-new-btn" @click="openNewListDialog">
      <span v-html="icon('plus', 13)"></span>
    </button>
  </div>

  <!-- ══ B. CONTENT PANEL ══ -->
  <div class="pl-content">

    <!-- B1. No list selected -->
    <div v-if="!selectedList" class="pl-empty-state">

      <!-- Mobile: lists exist but none selected → guide to dropdown -->
      <template v-if="priceLists.length">
        <div class="pl-es-title">Pick a Price List</div>
        <div class="pl-es-sub pl-es-sub--mob-only">
          Tap the <strong>List</strong> dropdown above to select a price list
        </div>
        <div class="pl-es-sub pl-es-sub--desk-only">
          Choose a price list on the left to view and manage item prices
        </div>
        <!-- Mobile shortcut: show the lists inline as tap targets -->
        <div class="pl-es-list-picker" v-if="filteredLists.length">
          <div v-for="pl in filteredLists" :key="pl.name"
            class="pl-es-pick-row" @click="selectList(pl)">
            <span class="pl-es-pick-icon">
              {{ pl.selling && pl.buying ? '🔄' : pl.selling ? '🏷️' : '🛒' }}
            </span>
            <div class="pl-es-pick-info">
              <div class="pl-es-pick-name">{{ pl.name }}</div>
              <div class="pl-es-pick-sub">
                {{ pl.selling && pl.buying ? 'Both' : pl.selling ? 'Selling' : 'Buying' }}
                · {{ pl.currency || 'INR' }}
              </div>
            </div>
            <span class="pl-es-pick-arrow">›</span>
          </div>
        </div>
        <div v-else class="pl-es-no-match">No price lists match this filter</div>
        <button class="b-btn b-btn-ghost pl-es-new-ghost" @click="openNewListDialog">
          <span v-html="icon('plus', 11)"></span> New Price List
        </button>
      </template>

      <!-- No lists at all → create first -->
      <template v-else>
        <div class="pl-es-icon">🏷️</div>
        <div class="pl-es-title">No Price Lists Yet</div>
        <div class="pl-es-sub">Create your first price list to start managing item prices</div>
        <button class="b-btn b-btn-primary" :disabled="!$canWrite('inventory')" :title="!$canWrite('inventory') ? 'Read-only access' : ''" style="margin-top:16px" @click="openNewListDialog">
          <span v-html="icon('plus', 13)"></span> Create Price List
        </button>
      </template>

    </div>

    <!-- B2. List selected -->
    <template v-else>

      <!-- B2a. Header -->
      <div class="pl-panel-head pl-mob-panel-head">
        <div class="pl-panel-title-row">
          <h2 class="pl-panel-name">{{ selectedList.name }}</h2>
          <span :class="typeBadgeClass(selectedList)">{{ typeLabel(selectedList) }}</span>
          <span class="b-badge b-badge-blue" style="font-size:11px">{{ selectedList.currency || 'INR' }}</span>
          <span class="b-badge" :class="selectedList.enabled ? 'b-badge-green' : 'b-badge-muted'" style="font-size:11px">
            {{ selectedList.enabled ? 'Active' : 'Inactive' }}
          </span>
          <!-- Mobile-only: Edit + Enable/Disable actions -->
          <div class="pl-mob-head-actions">
            <button class="pl-mob-action-btn"
              @click="openEditListDialog(selectedList)"
              title="Edit price list">
              <span v-html="icon('edit', 13)"></span>
              <span class="pl-mob-action-label">Edit</span>
            </button>
            <button class="pl-mob-action-btn"
              :class="selectedList.enabled ? 'pl-mob-action-disable' : 'pl-mob-action-enable'"
              @click="toggleEnabled(selectedList)"
              :title="selectedList.enabled ? 'Disable' : 'Enable'">
              <span class="pl-mob-toggle-dot"></span>
              <span class="pl-mob-action-label">{{ selectedList.enabled ? 'Disable' : 'Enable' }}</span>
            </button>
          </div>
        </div>

        <!-- B2b. Stats chips -->
        <div class="pl-stats-row" v-if="listDetail">
          <div class="pl-stat-chip">
            <span class="pl-stat-label">Total Items</span>
            <span class="pl-stat-val">{{ listDetail.item_count }}</span>
          </div>
          <div class="pl-stat-chip">
            <span class="pl-stat-label">Avg Rate</span>
            <span class="pl-stat-val">{{ fmtRate(listDetail.avg_rate) }}</span>
          </div>
          <div class="pl-stat-chip">
            <span class="pl-stat-label">Active Now</span>
            <span class="pl-stat-val">{{ listDetail.active_count }}</span>
          </div>
        </div>
      </div>

      <!-- B2c. Toolbar -->
      <div class="pl-toolbar">
        <div class="pl-toolbar-search">
          <span v-html="icon('search', 13)" style="color:#868E96;flex-shrink:0"></span>
          <input v-model="itemSearch" placeholder="Search items…"/>
        </div>
        <select class="pl-sort-select" v-model="sortKey">
          <option value="item_code_asc">Item Code A→Z</option>
          <option value="item_code_desc">Item Code Z→A</option>
          <option value="rate_asc">Rate Low→High</option>
          <option value="rate_desc">Rate High→Low</option>
        </select>
        <button class="b-btn b-btn-ghost pl-toolbar-btn" @click="showImportModal=true">
          <span v-html="icon('download', 13)"></span> Import CSV
        </button>
        <button class="b-btn b-btn-ghost pl-toolbar-btn" @click="exportCSV" :disabled="!sortedPrices.length">
          <span v-html="icon('download', 13)"></span> Export CSV
        </button>
        <button class="b-btn b-btn-primary pl-toolbar-btn" :disabled="!$canWrite('inventory')" :title="!$canWrite('inventory') ? 'Read-only access' : ''" @click="openAddDrawer">
          <span v-html="icon('plus', 13)"></span> Add Item
        </button>
      </div>

      <!-- B2d. Table -->
      <div class="b-card pl-tbl-card" style="padding:0;overflow:hidden">
        <table class="b-table">
          <thead>
            <tr>
              <th style="width:36px">#</th>
              <th>Item Code</th>
              <th>Item Name</th>
              <th class="pl-col-uom">UOM</th>
              <th class="pl-col-minqty ta-r">Min Qty</th>
              <th class="ta-r">Rate</th>
              <th class="pl-col-dates">Valid From</th>
              <th class="pl-col-dates">Valid Upto</th>
              <th style="width:40px"></th>
            </tr>
          </thead>
          <tbody>
            <template v-if="loadingPrices">
              <tr v-for="n in 5" :key="n">
                <td colspan="9" style="padding:12px">
                  <div class="b-shimmer" style="height:12px;border-radius:6px"></div>
                </td>
              </tr>
            </template>
            <tr v-else-if="!pagedPrices.length">
              <td colspan="9" class="b-empty">
                {{ itemSearch ? 'No items match your search' : 'No item prices yet — click "Add Item" to start' }}
              </td>
            </tr>
            <tr v-else v-for="(p, i) in pagedPrices" :key="p.name"
              class="pl-row clickable" @click="openEditDrawer(p)">
              <td class="c-muted" style="font-size:11px">{{ pageOffset + i + 1 }}</td>
              <td><span style="font-size:12px;color:#3B5BDB;font-weight:600">{{ p.item_code }}</span></td>
              <td class="fw-600" style="font-size:13px">{{ p.item_name || p.item_code }}</td>
              <td class="pl-col-uom c-muted" style="font-size:12px">{{ p.uom || 'Nos' }}</td>
              <td class="pl-col-minqty ta-r c-muted" style="font-size:12px">{{ p.packing_unit || '—' }}</td>
              <td class="ta-r fw-600" style="color:#2F9E44;font-size:13px">{{ fmtRate(p.price_list_rate) }}</td>
              <td class="pl-col-dates c-muted" style="font-size:12px">{{ p.valid_from ? fmtDate(p.valid_from) : '—' }}</td>
              <td class="pl-col-dates" style="font-size:12px">
                <span v-if="p.valid_upto" :class="validityClass(p)" style="font-size:11px;padding:2px 7px">
                  {{ validityLabel(p) }}
                </span>
                <span v-else class="c-muted">—</span>
              </td>
              <td style="text-align:center">
                <button @click.stop="confirmDeletePrice(p)"
                  class="pl-row-delete"
                  v-html="icon('trash', 13)"
                  style="background:none;border:none;cursor:pointer;color:#C92A2A;padding:4px;border-radius:4px"></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- B2d-mob. Card list (mobile) -->
      <div class="pl-item-cards">
        <template v-if="loadingPrices">
          <div v-for="n in 5" :key="n" class="pl-item-card-shimmer b-shimmer"></div>
        </template>
        <div v-else-if="!pagedPrices.length" class="b-empty">
          {{ itemSearch ? 'No items match your search' : 'No item prices yet — tap "Add Item" to start' }}
        </div>
        <div v-else v-for="(p, i) in pagedPrices" :key="p.name"
          class="pl-item-card" @click="openEditDrawer(p)">

          <div class="pl-item-card-top">
            <div class="pl-item-card-codewrap">
              <span class="pl-item-card-idx">{{ pageOffset + i + 1 }}</span>
              <span class="pl-item-card-code">{{ p.item_code }}</span>
            </div>
            <button @click.stop="confirmDeletePrice(p)"
              class="pl-item-card-delete"
              v-html="icon('trash', 14)"></button>
          </div>

          <div class="pl-item-card-name">{{ p.item_name || p.item_code }}</div>

          <div class="pl-item-card-bottom">
            <div class="pl-item-card-meta">
              <span>{{ p.uom || 'Nos' }}</span>
              <span v-if="p.packing_unit"> · Min {{ p.packing_unit }}</span>
              <span v-if="p.valid_from"> · From {{ fmtDate(p.valid_from) }}</span>
              <span v-if="p.valid_upto" :class="['pl-item-card-validity', validityClass(p)]">
                {{ validityLabel(p) }}
              </span>
            </div>
            <div class="pl-item-card-rate">{{ fmtRate(p.price_list_rate) }}</div>
          </div>
        </div>
      </div>

      <!-- B2e. Pagination -->
      <div v-if="sortedPrices.length > pageSize" class="pl-pagination">
        <span class="c-muted" style="font-size:12px">
          Showing {{ pageOffset + 1 }}–{{ Math.min(pageOffset + pageSize, sortedPrices.length) }}
          of {{ sortedPrices.length }}
        </span>
        <button class="b-btn b-btn-ghost" style="padding:5px 12px;font-size:12px"
          :disabled="page === 0" @click="page--">‹ Prev</button>
        <button class="b-btn b-btn-ghost" style="padding:5px 12px;font-size:12px"
          :disabled="pageOffset + pageSize >= sortedPrices.length" @click="page++">Next ›</button>
      </div>
    </template>
  </div>

  <!-- ══ TELEPORTED OVERLAYS ══ -->
  <Teleport to="body">

    <!-- C. Item Price Drawer -->
    <div v-if="showDrawer" class="pl-drawer-backdrop" @click.self="closeDrawer">
      <div class="pl-drawer">
        <div class="pl-drawer-head">
          <div>
            <div class="pl-drawer-title">{{ drawerMode === 'add' ? 'Add Item Price' : 'Edit Item Price' }}</div>
            <div class="pl-drawer-sub">{{ selectedList?.name }}</div>
          </div>
          <button style="background:none;border:none;cursor:pointer;color:rgba(255,255,255,.7);padding:4px"
            @click="closeDrawer" v-html="icon('x', 16)"></button>
        </div>

        <div class="pl-drawer-body">
          <!-- Duplicate warning -->
          <div v-if="dupWarning" class="pl-dup-warn">⚠ {{ dupWarning }}</div>

          <!-- Item Code -->
          <div class="nim-field">
            <label class="nim-label">Item Code <span style="color:#C92A2A">*</span></label>
            <SearchableSelect
              v-model="form.item_code"
              :options="itemOptions"
              valueKey="item_code"
              labelKey="item_code"
              placeholder="Type to search items…"
              :disabled="drawerMode === 'edit'"
              :createable="drawerMode === 'add'"
              createLabel="+ Create new item"
              @select="onItemSelect"
              @create="createQuickItem"
            />
            <span v-if="formErrors.item_code" class="pl-field-err">{{ formErrors.item_code }}</span>
          </div>

          <!-- Item Name -->
          <div class="nim-field">
            <label class="nim-label">Item Name</label>
            <input class="nim-input" v-model="form.item_name" placeholder="Auto-filled from item code"/>
          </div>

          <!-- Rate + UOM -->
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
            <div class="nim-field">
              <label class="nim-label">Rate ({{ currencySymbol }}) <span style="color:#C92A2A">*</span></label>
              <div class="pl-rate-wrap">
                <span class="pl-currency-prefix">{{ currencySymbol }}</span>
                <input class="nim-input pl-rate-input" type="number"
                  v-model="form.price_list_rate"
                  min="0.01" max="9999999.99" step="0.01" placeholder="0.00"/>
              </div>
              <span v-if="formErrors.price_list_rate" class="pl-field-err">{{ formErrors.price_list_rate }}</span>
            </div>
            <div class="nim-field">
              <label class="nim-label">UOM</label>
              <input class="nim-input" v-model="form.uom" placeholder="Nos"/>
            </div>
          </div>

          <!-- Min Order Qty -->
          <div class="nim-field">
            <label class="nim-label">Min Order Qty <span class="c-muted" style="font-weight:400">(optional)</span></label>
            <input class="nim-input" type="number" v-model="form.packing_unit" min="0" placeholder="0"/>
          </div>

          <!-- Dates -->
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
            <div class="nim-field">
              <label class="nim-label">Valid From</label>
              <input class="nim-input" type="date" v-model="form.valid_from"/>
            </div>
            <div class="nim-field">
              <label class="nim-label">Valid Upto</label>
              <input class="nim-input" type="date" v-model="form.valid_upto"/>
              <span v-if="formErrors.valid_upto" class="pl-field-err">{{ formErrors.valid_upto }}</span>
            </div>
          </div>
        </div>

        <div class="pl-drawer-foot">
          <button class="nim-btn nim-btn-ghost" @click="closeDrawer">Cancel</button>
          <button v-if="drawerMode === 'add'" class="nim-btn nim-btn-ghost"
            @click="savePrice(true)" :disabled="saving">
            {{ saving ? 'Saving…' : 'Save & Add Another' }}
          </button>
          <button class="nim-btn nim-btn-primary" @click="savePrice(false)" :disabled="saving">
            {{ saving ? 'Saving…' : 'Save Price' }}
          </button>
        </div>
      </div>
    </div>

    <!-- D. Price List Dialog (New / Edit) -->
    <div v-if="showListDialog" class="nim-overlay" @click.self="showListDialog=false">
      <div class="nim-dialog" style="max-width:480px;width:100%">
        <div class="nim-header">
          <span style="font-size:15px;font-weight:700; color:#fff">
            {{ listDialogMode === 'new' ? 'New Price List' : 'Edit Price List' }}
          </span>
          <button  style="background: rgba(255, 255, 255, .15);
    border: none;
    cursor: pointer;
    color: #fff;
    height: 30px;
    border-radius: 8px;
    display: grid;
    place-items: center;
    transition: .15s;"
     class="nim-btn nim-btn-ghost" @click="showListDialog=false">
            <span v-html="icon('x', 14)"/>
          </button>
        </div>
        <div class="nim-body" style="display:flex;flex-direction:column;gap:14px">
          <!-- Name -->
          <div class="nim-field">
            <label class="nim-label">Price List Name <span style="color:#C92A2A">*</span></label>
            <input class="nim-input" v-model="listForm.name" placeholder="e.g. Wholesale 2025"/>
            <span v-if="listFormErrors.name" class="pl-field-err">{{ listFormErrors.name }}</span>
          </div>

          <!-- Type toggle -->
          <div class="nim-field">
            <label class="nim-label">Type <span style="color:#C92A2A">*</span></label>
            <div class="pl-type-toggle">
              <button class="pl-type-btn" :class="{ active: listForm.selling && !listForm.buying }"
                @click="listForm.selling=1; listForm.buying=0">Selling</button>
              <button class="pl-type-btn" :class="{ active: listForm.buying && !listForm.selling }"
                @click="listForm.buying=1; listForm.selling=0">Buying</button>
              <button class="pl-type-btn" :class="{ active: listForm.selling && listForm.buying }"
                @click="listForm.selling=1; listForm.buying=1">Both</button>
            </div>
          </div>

          <!-- Currency -->
          <div class="nim-field">
            <label class="nim-label">Currency</label>
            <select class="nim-input" v-model="listForm.currency">
              <option v-for="c in CURRENCY_LIST" :key="c.code" :value="c.code">
                {{ c.code }} — {{ c.name }}
              </option>
            </select>
          </div>

          <!-- Currency change warning (edit mode) -->
          <div v-if="listDialogMode === 'edit' && listForm.currency !== originalCurrency && listDetail?.item_count > 0"
            class="pl-warn-box">
            This list has {{ listDetail.item_count }} items priced in {{ originalCurrency }}.
            Changing currency will not update existing rates.
          </div>

          <!-- Description -->
          <div class="nim-field">
            <label class="nim-label">Description <span class="c-muted" style="font-weight:400">(optional)</span></label>
            <textarea class="nim-input" v-model="listForm.description"
              rows="2" placeholder="Notes about when or how this list is used"
              style="resize:vertical;min-height:58px"></textarea>
          </div>
        </div>
        <div class="nim-footer">
          <button class="nim-btn nim-btn-ghost" @click="showListDialog=false">Cancel</button>
          <button class="nim-btn nim-btn-primary" @click="saveListDialog" :disabled="savingList">
            {{ savingList ? 'Saving…' : listDialogMode === 'new' ? 'Create Price List' : 'Save Changes' }}
          </button>
        </div>
      </div>
    </div>

    <!-- E. Duplicate Dialog -->
    <div v-if="showDuplicateDialog" class="nim-overlay" @click.self="showDuplicateDialog=false">
      <div class="nim-dialog" style="max-width:420px;width:100%">
        <div class="nim-header">
          <span style="font-size:15px;color:#fff;font-weight:700">Duplicate Price List</span>
          <button style="background: rgba(255, 255, 255, .15);
    border: none;
    cursor: pointer;
    color: #fff;
    height: 30px;
    border-radius: 8px;
    display: grid;
    place-items: center;
    transition: .15s;" class="nim-btn nim-btn-ghost" @click="showDuplicateDialog=false">
            <span v-html="icon('x', 14)"/>
          </button>
        </div>
        <div class="nim-body">
          <p class="c-muted" style="font-size:12.5px;margin-bottom:14px">
            Creates a copy of <strong>{{ duplicateSource?.name }}</strong> with all its item prices.
          </p>
          <div class="nim-field">
            <label class="nim-label">New Price List Name <span style="color:#C92A2A">*</span></label>
            <input class="nim-input" v-model="duplicateName" placeholder="e.g. Wholesale 2025 — Copy"/>
          </div>
        </div>
        <div class="nim-footer">
          <button class="nim-btn nim-btn-ghost" @click="showDuplicateDialog=false">Cancel</button>
          <button class="nim-btn nim-btn-primary" @click="doDuplicate" :disabled="duplicating">
            {{ duplicating ? 'Duplicating…' : 'Duplicate' }}
          </button>
        </div>
      </div>
    </div>

    <!-- F. CSV Import Modal -->
    <div v-if="showImportModal" class="nim-overlay" @click.self="closeImportModal">
      <div class="nim-dialog" style="max-width:660px;width:100%">
        <div class="nim-header">
          <span style="font-size:15px;font-weight:700">Import Item Prices</span>
          <button class="nim-btn nim-btn-ghost" @click="closeImportModal">
            <span v-html="icon('x', 14)"/>
          </button>
        </div>
        <div class="nim-body" style="display:flex;flex-direction:column;gap:16px">
          <div class="pl-import-step">
            <div class="pl-import-sub">Step 1 — Download the CSV template</div>
            <button class="b-btn b-btn-ghost" style="align-self:flex-start;font-size:12.5px"
              @click="downloadTemplate">
              <span v-html="icon('download', 13)"></span> Download Template
            </button>
          </div>
          <div class="pl-import-step">
            <div class="pl-import-sub">Step 2 — Fill in your prices and upload</div>
            <input type="file" accept=".csv" ref="csvFileRef" @change="onFileSelect"
              style="font-size:13px"/>
          </div>

          <!-- Preview (after parse) -->
          <template v-if="csvPreviewRows.length">
            <div class="pl-import-summary">
              <span class="b-badge b-badge-green">{{ validRows.length }} valid</span>
              <span v-if="errorRows.length" class="b-badge b-badge-red">{{ errorRows.length }} error{{ errorRows.length !== 1 ? 's' : '' }}</span>
            </div>
            <div class="pl-import-preview">
              <table class="b-table" style="font-size:11.5px">
                <thead>
                  <tr>
                    <th>#</th><th>Item Code</th><th>Item Name</th>
                    <th class="ta-r">Rate</th><th>UOM</th>
                    <th>Valid From</th><th>Valid Upto</th><th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(r, i) in csvPreviewRows.slice(0, 12)" :key="i"
                    :class="r._hasError ? 'pl-import-err-row' : 'pl-import-ok-row'">
                    <td class="c-muted">{{ i + 1 }}</td>
                    <td>{{ r.item_code }}</td>
                    <td class="c-muted">{{ r.item_name }}</td>
                    <td class="ta-r">{{ r.rate }}</td>
                    <td>{{ r.uom }}</td>
                    <td class="c-muted">{{ r.valid_from || '—' }}</td>
                    <td class="c-muted">{{ r.valid_upto || '—' }}</td>
                    <td>
                      <span v-if="r._hasError" class="b-badge b-badge-red" style="font-size:10px">{{ r._error }}</span>
                      <span v-else class="b-badge b-badge-green" style="font-size:10px">OK</span>
                    </td>
                  </tr>
                </tbody>
              </table>
              <div v-if="csvPreviewRows.length > 12" class="c-muted" style="font-size:11.5px;margin-top:6px;text-align:center">
                … and {{ csvPreviewRows.length - 12 }} more rows
              </div>
            </div>
          </template>
        </div>
        <div class="nim-footer">
          <button class="nim-btn nim-btn-ghost" @click="closeImportModal">Cancel</button>
          <button class="nim-btn nim-btn-primary"
            :disabled="!validRows.length || importingCSV"
            @click="doImport">
            {{ importingCSV ? 'Importing…' : `Import ${validRows.length} valid row${validRows.length !== 1 ? 's' : ''}` }}
          </button>
        </div>
      </div>
    </div>

    <!-- G. Context menu -->
    <div v-if="showCardMenu" class="pl-ctx-menu"
      :style="`top:${menuPos.y}px;right:${menuPos.r}px`"
      ref="ctxMenuRef">
      <button class="pl-ctx-item" @click="openEditListDialog(menuTarget); showCardMenu=false">
        <span v-html="icon('edit', 13)"></span> Edit
      </button>
      <button class="pl-ctx-item" @click="openDuplicateDialog(menuTarget); showCardMenu=false">
        <span v-html="icon('copy', 13)"></span> Duplicate
      </button>
      <button class="pl-ctx-item danger" @click="confirmDeleteList(menuTarget); showCardMenu=false">
        <span v-html="icon('trash', 13)"></span> Delete
      </button>
    </div>

  </Teleport>
</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from "vue";
import { apiGET, apiPOST, apiList, apiSave, apiDelete } from "../api/client.js";
import { useToast }   from "../composables/useToast.js";
import { useConfirm } from "../composables/useConfirm.js";
import { icon }       from "../utils/icons.js";
import { flt, fmtDate } from "../utils/format.js";
import SearchableSelect from "../components/SearchableSelect.vue";

const { toast }   = useToast();
const { confirm } = useConfirm();

// ── Currency list ────────────────────────────────────────────────────────────
const CURRENCY_LIST = [
  { code: "INR",  name: "Indian Rupee" },
  { code: "USD",  name: "US Dollar" },
  { code: "EUR",  name: "Euro" },
  { code: "GBP",  name: "British Pound" },
  { code: "AED",  name: "UAE Dirham" },
  { code: "SGD",  name: "Singapore Dollar" },
  { code: "JPY",  name: "Japanese Yen" },
  { code: "CAD",  name: "Canadian Dollar" },
  { code: "AUD",  name: "Australian Dollar" },
  { code: "CHF",  name: "Swiss Franc" },
  { code: "SAR",  name: "Saudi Riyal" },
  { code: "MYR",  name: "Malaysian Ringgit" },
  { code: "QAR",  name: "Qatari Riyal" },
  { code: "CNY",  name: "Chinese Yuan" },
];

// ── Sidebar state ────────────────────────────────────────────────────────────
const priceLists      = ref([]);
const loadingLists    = ref(false);
const listTab         = ref("all");
const listSearch      = ref("");
const mobileSidebarOpen = ref(false);
const listTabs        = [{ k: "all", label: "All" }, { k: "selling", label: "Selling" }, { k: "buying", label: "Buying" }];

// ── Selection / content ──────────────────────────────────────────────────────
const selectedList  = ref(null);
const itemPrices    = ref([]);
const loadingPrices = ref(false);
const listDetail    = ref(null);   // {item_count, avg_rate, active_count}

// ── Table state ──────────────────────────────────────────────────────────────
const itemSearch = ref("");
const sortKey    = ref("item_code_asc");
const page       = ref(0);
const pageSize   = 50;

// ── Context menu ─────────────────────────────────────────────────────────────
const menuTarget  = ref(null);
const menuPos     = ref({ y: 0, r: 0 });
const showCardMenu = ref(false);
const ctxMenuRef   = ref(null);

// ── Item Price Drawer ────────────────────────────────────────────────────────
const showDrawer = ref(false);
const drawerMode = ref("add");
const saving     = ref(false);
const form       = reactive({
  name: "", price_list: "", item_code: "", item_name: "",
  price_list_rate: "", uom: "Nos", packing_unit: "", valid_from: "", valid_upto: "",
});
const formErrors  = reactive({ item_code: "", price_list_rate: "", valid_upto: "" });
const dupWarning  = ref("");
const itemOptions = ref([]);
let   itemFetchTimer = null;

// ── Price List dialog ────────────────────────────────────────────────────────
const showListDialog   = ref(false);
const listDialogMode   = ref("new");
const savingList       = ref(false);
const originalCurrency = ref("INR");
const listForm         = reactive({ name: "", currency: "INR", selling: 1, buying: 0, description: "" });
const listFormErrors   = reactive({ name: "" });

// ── Duplicate ────────────────────────────────────────────────────────────────
const showDuplicateDialog = ref(false);
const duplicateName       = ref("");
const duplicating         = ref(false);
const duplicateSource     = ref(null);

// ── CSV Import ───────────────────────────────────────────────────────────────
const showImportModal  = ref(false);
const csvFileRef       = ref(null);
const csvPreviewRows   = ref([]);
const importingCSV     = ref(false);

// ── Currency symbol map ──────────────────────────────────────────────────────
const CURRENCY_SYMBOLS = { INR: "₹", USD: "$", EUR: "€", GBP: "£", AED: "د.إ", SGD: "S$", JPY: "¥", CAD: "C$", AUD: "A$" };

// ── Computed ─────────────────────────────────────────────────────────────────
const filteredLists = computed(() => {
  let lists = priceLists.value;
  if (listTab.value === "selling") lists = lists.filter(p => p.selling && !p.buying);
  if (listTab.value === "buying")  lists = lists.filter(p => p.buying && !p.selling);
  const q = listSearch.value.trim().toLowerCase();
  if (q) lists = lists.filter(p => (p.name || "").toLowerCase().includes(q));
  return lists;
});

const filteredPrices = computed(() => {
  const q = itemSearch.value.trim().toLowerCase();
  if (!q) return itemPrices.value;
  return itemPrices.value.filter(p =>
    (p.item_code || "").toLowerCase().includes(q) ||
    (p.item_name || "").toLowerCase().includes(q)
  );
});

const sortedPrices = computed(() => {
  const arr = [...filteredPrices.value];
  switch (sortKey.value) {
    case "item_code_asc":  arr.sort((a, b) => (a.item_code || "").localeCompare(b.item_code || "")); break;
    case "item_code_desc": arr.sort((a, b) => (b.item_code || "").localeCompare(a.item_code || "")); break;
    case "rate_asc":  arr.sort((a, b) => flt(a.price_list_rate) - flt(b.price_list_rate)); break;
    case "rate_desc": arr.sort((a, b) => flt(b.price_list_rate) - flt(a.price_list_rate)); break;
  }
  return arr;
});

const pageOffset  = computed(() => page.value * pageSize);
const pagedPrices = computed(() => sortedPrices.value.slice(pageOffset.value, pageOffset.value + pageSize));

const currencySymbol = computed(() =>
  CURRENCY_SYMBOLS[selectedList.value?.currency] || selectedList.value?.currency || "₹"
);

const validRows  = computed(() => csvPreviewRows.value.filter(r => !r._hasError));
const errorRows  = computed(() => csvPreviewRows.value.filter(r => r._hasError));

// ── Sidebar / loading ────────────────────────────────────────────────────────
async function loadPriceLists() {
  loadingLists.value = true;
  try {
    const rows = await apiList("Price List", {
      fields: ["name", "currency", "buying", "selling", "enabled"],
      limit: 200,
      order: "name asc",
    });
    // Attach item counts lazily (fetch in one shot)
    const lists = rows || [];
    if (lists.length) {
      try {
        // Fire detail calls in parallel (limited to 10 at a time to avoid overload)
        const chunks = [];
        for (let i = 0; i < Math.min(lists.length, 30); i++) {
          chunks.push(
            apiPOST("zoho_books_clone.api.books_data.get_price_list_detail",
              { price_list_name: lists[i].name })
              .then(d => { lists[i]._ic = d?.item_count ?? null; })
              .catch(() => { lists[i]._ic = null; })
          );
        }
        await Promise.all(chunks);
      } catch {}
    }
    priceLists.value = lists;
  } catch (e) { toast("Could not load price lists: " + e.message, "error"); }
  loadingLists.value = false;
}

async function selectList(pl) {
  selectedList.value = pl;
  itemSearch.value   = "";
  page.value         = 0;
  mobileSidebarOpen.value = false;
  await Promise.all([loadItemPrices(), loadListDetail()]);
}

async function loadItemPrices() {
  if (!selectedList.value) return;
  loadingPrices.value = true;
  try {
    itemPrices.value = await apiList("Item Price", {
      fields: ["name", "item_code", "item_name", "price_list_rate", "uom", "packing_unit", "valid_from", "valid_upto"],
      filters: [["price_list", "=", selectedList.value.name]],
      limit: 2000,
      order: "item_code asc",
    }) || [];
  } catch (e) { toast("Could not load item prices: " + e.message, "error"); }
  loadingPrices.value = false;
}

async function loadListDetail() {
  if (!selectedList.value) return;
  try {
    listDetail.value = await apiPOST(
      "zoho_books_clone.api.books_data.get_price_list_detail",
      { price_list_name: selectedList.value.name }
    );
    // Update sidebar item count
    const pl = priceLists.value.find(p => p.name === selectedList.value.name);
    if (pl && listDetail.value) pl._ic = listDetail.value.item_count;
  } catch { listDetail.value = null; }
}

// ── Status toggle ────────────────────────────────────────────────────────────
async function toggleEnabled(pl) {
  const newVal = pl.enabled ? 0 : 1;
  try {
    await apiSave({ doctype: "Price List", name: pl.name, enabled: newVal });
    pl.enabled = newVal;
    if (selectedList.value?.name === pl.name) selectedList.value.enabled = newVal;
    toast(`Price list ${newVal ? "enabled" : "disabled"}`);
  } catch (e) { toast(e.message, "error"); }
}

// ── Context menu ─────────────────────────────────────────────────────────────
function openCardMenu(pl, event) {
  menuTarget.value = pl;
  const rect = event.currentTarget.getBoundingClientRect();
  // Position right-edge aligned, below the button
  menuPos.value = {
    y: rect.bottom + window.scrollY + 4,
    r: window.innerWidth - rect.right,
  };
  showCardMenu.value = true;
}

function onDocClick(e) {
  if (showCardMenu.value && ctxMenuRef.value && !ctxMenuRef.value.contains(e.target)) {
    showCardMenu.value = false;
  }
}

// ── Price List dialog (New / Edit) ───────────────────────────────────────────
function openNewListDialog() {
  Object.assign(listForm, { name: "", currency: "INR", selling: 1, buying: 0, description: "" });
  listFormErrors.name = "";
  listDialogMode.value = "new";
  showListDialog.value = true;
}

function openEditListDialog(pl) {
  Object.assign(listForm, {
    name: pl.name,
    currency: pl.currency || "INR",
    selling: pl.selling ? 1 : 0,
    buying:  pl.buying  ? 1 : 0,
    description: pl.description || "",
  });
  originalCurrency.value = pl.currency || "INR";
  listFormErrors.name    = "";
  listDialogMode.value   = "edit";
  showListDialog.value   = true;
}

function validateListForm() {
  listFormErrors.name = "";
  const n = listForm.name.trim();
  if (!n) { listFormErrors.name = "Name is required"; return false; }
  if (n.length < 3) { listFormErrors.name = "Name must be at least 3 characters"; return false; }
  return true;
}

async function saveListDialog() {
  if (!validateListForm()) return;
  savingList.value = true;
  try {
    const doc = {
      doctype: "Price List",
      currency: listForm.currency || "INR",
      selling:  listForm.selling ? 1 : 0,
      buying:   listForm.buying  ? 1 : 0,
      enabled:  1,
    };
    if (listDialogMode.value === "edit") {
      doc.name = listForm.name;
    } else {
      doc.price_list_name = listForm.name;
    }
    await apiSave(doc);
    toast(listDialogMode.value === "new" ? "Price list created" : "Price list updated");
    showListDialog.value = false;
    await loadPriceLists();
    // Re-select if editing current
    if (listDialogMode.value === "edit" && selectedList.value?.name === listForm.name) {
      const updated = priceLists.value.find(p => p.name === listForm.name);
      if (updated) selectedList.value = updated;
    }
  } catch (e) { toast(e.message || "Failed to save", "error"); }
  savingList.value = false;
}

// ── Duplicate ────────────────────────────────────────────────────────────────
function openDuplicateDialog(pl) {
  duplicateSource.value = pl;
  duplicateName.value   = pl.name + " — Copy";
  showDuplicateDialog.value = true;
}

async function doDuplicate() {
  const name = duplicateName.value.trim();
  if (!name) { toast("Name is required", "error"); return; }
  duplicating.value = true;
  try {
    const res = await apiPOST(
      "zoho_books_clone.api.books_data.duplicate_price_list",
      { source_name: duplicateSource.value.name, new_name: name }
    );
    toast(`Price list duplicated with ${res.item_count} item${res.item_count !== 1 ? "s" : ""}`);
    showDuplicateDialog.value = false;
    await loadPriceLists();
  } catch (e) { toast(e.message || "Duplicate failed", "error"); }
  duplicating.value = false;
}

// ── Delete price list ────────────────────────────────────────────────────────
async function confirmDeleteList(pl) {
  const count = listDetail.value?.item_count ?? "?";
  const ok = await confirm({
    title:   `Delete "${pl.name}"?`,
    body:    `This will also remove all ${count} item price${count !== 1 ? "s" : ""} permanently. This cannot be undone.`,
    okLabel: "Delete",
  });
  if (!ok) return;
  try {
    // Delete all item prices first
    const prices = await apiList("Item Price", {
      fields: ["name"],
      filters: [["price_list", "=", pl.name]],
      limit: 2000,
    });
    for (const p of prices) await apiDelete("Item Price", p.name);
    await apiDelete("Price List", pl.name);
    toast(`Price list deleted (${prices.length} item${prices.length !== 1 ? "s" : ""} removed)`);
    if (selectedList.value?.name === pl.name) {
      selectedList.value = null;
      listDetail.value   = null;
    }
    await loadPriceLists();
  } catch (e) { toast(e.message || "Delete failed", "error"); }
}

// ── Item Price Drawer ────────────────────────────────────────────────────────
function openAddDrawer() {
  if (!selectedList.value) { toast("Select a price list first", "error"); return; }
  drawerMode.value = "add";
  Object.assign(form, {
    name: "", price_list: selectedList.value.name,
    item_code: "", item_name: "", price_list_rate: "",
    uom: "Nos", packing_unit: "", valid_from: "", valid_upto: "",
  });
  Object.assign(formErrors, { item_code: "", price_list_rate: "", valid_upto: "" });
  dupWarning.value  = "";
  itemOptions.value = [];
  fetchItemOptions("");
  showDrawer.value  = true;
}

function openEditDrawer(p) {
  drawerMode.value = "edit";
  Object.assign(form, {
    name: p.name,
    price_list: p.price_list || selectedList.value?.name || "",
    item_code:  p.item_code,
    item_name:  p.item_name || "",
    price_list_rate: p.price_list_rate,
    uom:         p.uom || "Nos",
    packing_unit: p.packing_unit || "",
    valid_from:  p.valid_from || "",
    valid_upto:  p.valid_upto || "",
  });
  Object.assign(formErrors, { item_code: "", price_list_rate: "", valid_upto: "" });
  dupWarning.value = "";
  showDrawer.value = true;
}

function closeDrawer() {
  showDrawer.value = false;
  Object.assign(formErrors, { item_code: "", price_list_rate: "", valid_upto: "" });
  dupWarning.value = "";
}

function validateForm() {
  Object.assign(formErrors, { item_code: "", price_list_rate: "", valid_upto: "" });
  let ok = true;
  if (!form.item_code.trim()) {
    formErrors.item_code = "Item is required"; ok = false;
  }
  const rate = parseFloat(form.price_list_rate);
  if (form.price_list_rate === "" || form.price_list_rate === null) {
    formErrors.price_list_rate = "Rate must be greater than 0"; ok = false;
  } else if (isNaN(rate) || rate <= 0) {
    formErrors.price_list_rate = "Rate must be greater than 0"; ok = false;
  } else if (rate > 9999999.99) {
    formErrors.price_list_rate = "Rate cannot exceed 9,999,999.99"; ok = false;
  }
  if (form.valid_from && form.valid_upto && form.valid_upto < form.valid_from) {
    formErrors.valid_upto = "End date must be after start date"; ok = false;
  }
  return ok;
}

function checkDuplicate() {
  if (drawerMode.value !== "add" || !form.item_code) { dupWarning.value = ""; return; }
  const existing = itemPrices.value.find(
    p => p.item_code === form.item_code && (p.uom || "Nos") === (form.uom || "Nos")
  );
  if (existing) {
    dupWarning.value = `This item already has a price in this list (${fmtRate(existing.price_list_rate)}). Save to overwrite or cancel.`;
  } else {
    dupWarning.value = "";
  }
}

function onItemSelect(opt) {
  // Auto-fill item_name from the selected option
  const found = itemOptions.value.find(o => o.item_code === (opt?.value || form.item_code));
  form.item_name = found?.item_name || opt?.label || form.item_code;
}

async function fetchItemOptions(q) {
  // Load a broad set so SearchableSelect can filter client-side.
  // Pass q only if it differs from whatever is already selected (i.e. user typed something).
  clearTimeout(itemFetchTimer);
  itemFetchTimer = setTimeout(async () => {
    try {
      const filters = q ? [["item_code", "like", `%${q}%`]] : [];
      const res = await apiList("Item", {
        fields: ["item_code", "item_name"],
        filters,
        limit: 100,
      });
      itemOptions.value = (res || []).map(r => ({
        item_code: r.item_code || r.name,
        item_name: r.item_name || r.name,
      }));
    } catch { itemOptions.value = []; }
  }, 0);
}

async function createQuickItem(typed) {
  const code = (typeof typed === "string" ? typed : typed?.value || typed?.item_code || "").trim();
  if (!code) return;
  try {
    await apiSave({
      doctype:    "Item",
      item_code:  code,
      item_name:  code,
      stock_uom:  "Nos",
      item_group: "All Item Groups",
      item_type:  "Product",
    });
    form.item_code = code;
    form.item_name = code;
    // Add to options immediately so SearchableSelect shows it selected
    if (!itemOptions.value.find(o => o.item_code === code)) {
      itemOptions.value = [{ item_code: code, item_name: code }, ...itemOptions.value];
    }
    toast(`Item "${code}" created`);
  } catch (e) { toast(e.message || "Failed to create item", "error"); }
}

async function savePrice(addAnother) {
  if (!validateForm()) return;
  saving.value = true;
  try {
    const doc = {
      doctype:         "Item Price",
      price_list:      form.price_list || selectedList.value?.name,
      item_code:       form.item_code.trim(),
      item_name:       form.item_name || form.item_code,
      price_list_rate: parseFloat(form.price_list_rate),
      uom:             form.uom || "Nos",
      packing_unit:    parseInt(form.packing_unit) || 0,
      valid_from:      form.valid_from || null,
      valid_upto:      form.valid_upto || null,
    };
    if (drawerMode.value === "edit" && form.name) doc.name = form.name;
    await apiSave(doc);
    toast(drawerMode.value === "add" ? "Price added" : "Price updated");
    await loadItemPrices();
    await loadListDetail();
    if (addAnother) {
      Object.assign(form, {
        name: "", item_code: "", item_name: "", price_list_rate: "",
        uom: "Nos", packing_unit: "", valid_from: "", valid_upto: "",
      });
      Object.assign(formErrors, { item_code: "", price_list_rate: "", valid_upto: "" });
      dupWarning.value = "";
      fetchItemOptions("");
    } else {
      closeDrawer();
    }
  } catch (e) { toast(e.message || "Failed to save", "error"); }
  saving.value = false;
}

async function confirmDeletePrice(p) {
  const ok = await confirm({
    title:   "Remove item price?",
    body:    `Remove price for ${p.item_code} from ${selectedList.value?.name}? This cannot be undone.`,
    okLabel: "Delete",
  });
  if (!ok) return;
  try {
    await apiDelete("Item Price", p.name);
    toast("Price removed");
    await loadItemPrices();
    await loadListDetail();
  } catch (e) { toast(e.message || "Delete failed", "error"); }
}

// ── CSV Import ───────────────────────────────────────────────────────────────
function downloadTemplate() {
  const headers  = "Item Code,Item Name,Rate,UOM,Min Qty,Valid From,Valid Upto";
  const example  = "ITEM-001,Example Item,99.00,Nos,1,2025-01-01,2025-12-31";
  const blob     = new Blob([headers + "\r\n" + example], { type: "text/csv;charset=utf-8;" });
  const url      = URL.createObjectURL(blob);
  const a        = document.createElement("a");
  a.href         = url;
  a.download     = "item_prices_template.csv";
  a.click();
  URL.revokeObjectURL(url);
}

function onFileSelect(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = ev => { csvPreviewRows.value = parseCSV(ev.target.result); };
  reader.readAsText(file);
}

function parseCSV(text) {
  const lines = text.split(/\r?\n/).filter(l => l.trim());
  if (lines.length < 2) return [];
  const headers = lines[0].split(",").map(h => h.trim().toLowerCase().replace(/\s+/g, "_"));
  return lines.slice(1).map((line, i) => {
    // simple CSV split (handles no embedded commas in values)
    const cols = line.split(",");
    const row  = {};
    headers.forEach((h, j) => { row[h] = (cols[j] || "").trim(); });

    const item_code  = row.item_code || "";
    const rate       = parseFloat(row.rate || row.price_list_rate || 0);
    const valid_from = row.valid_from || "";
    const valid_upto = row.valid_upto || "";
    const dateRe     = /^\d{4}-\d{2}-\d{2}$/;

    const errors = [];
    if (!item_code)                             errors.push("missing item_code");
    if (!(rate > 0))                            errors.push("rate must be > 0");
    if (valid_from && !dateRe.test(valid_from)) errors.push("invalid valid_from (use YYYY-MM-DD)");
    if (valid_upto && !dateRe.test(valid_upto)) errors.push("invalid valid_upto");

    return {
      item_code,
      item_name:  row.item_name || item_code,
      rate,
      uom:        row.uom || "Nos",
      min_qty:    row.min_qty || "",
      valid_from,
      valid_upto,
      _hasError:  errors.length > 0,
      _error:     errors.join("; "),
    };
  });
}

async function doImport() {
  if (!validRows.value.length) { toast("No valid rows to import", "error"); return; }
  importingCSV.value = true;
  try {
    const res = await apiPOST(
      "zoho_books_clone.api.books_data.bulk_create_item_prices",
      {
        price_list: selectedList.value.name,
        rows_json:  JSON.stringify(validRows.value.map(r => ({
          item_code:       r.item_code,
          item_name:       r.item_name,
          price_list_rate: r.rate,
          uom:             r.uom,
          min_qty:         r.min_qty,
          valid_from:      r.valid_from,
          valid_upto:      r.valid_upto,
        }))),
      }
    );
    const created = res?.created ?? 0;
    toast(`Imported ${created} item price${created !== 1 ? "s" : ""}`);
    closeImportModal();
    await loadItemPrices();
    await loadListDetail();
  } catch (e) { toast(e.message || "Import failed", "error"); }
  importingCSV.value = false;
}

function closeImportModal() {
  showImportModal.value = false;
  csvPreviewRows.value  = [];
  if (csvFileRef.value) csvFileRef.value.value = "";
}

// ── Export CSV ───────────────────────────────────────────────────────────────
function exportCSV() {
  const rows = sortedPrices.value;
  if (!rows.length) return;
  const esc = v => { const s = v == null ? "" : String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  const listName = selectedList.value?.name || "price_list";
  const lines = [["Item Code", "Item Name", "Rate", "UOM", "Min Qty", "Currency", "Valid From", "Valid Upto"].join(",")];
  for (const p of rows) {
    lines.push([
      p.item_code || "", p.item_name || "",
      parseFloat(p.price_list_rate) || 0,
      p.uom || "", p.packing_unit || "",
      p.currency || selectedList.value?.currency || "",
      p.valid_from || "", p.valid_upto || "",
    ].map(esc).join(","));
  }
  const blob = new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv;charset=utf-8;" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = `prices_${listName}_${new Date().toISOString().slice(0, 10)}`.replace(/\s+/g, "_") + ".csv";
  a.click();
  URL.revokeObjectURL(url);
  toast(`Exported ${rows.length} price${rows.length !== 1 ? "s" : ""}`);
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function fmtRate(v) {
  const n   = flt(v) || 0;
  const sym = currencySymbol.value;
  return sym + n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function typeLabel(pl) {
  return pl.selling && pl.buying ? "Both" : pl.selling ? "Selling" : "Buying";
}

function typeBadgeClass(pl) {
  if (pl.selling && pl.buying) return "b-badge b-badge-purple";
  if (pl.selling)              return "b-badge b-badge-green";
  return "b-badge b-badge-amber";
}

function validityLabel(p) {
  if (!p.valid_upto) return fmtDate(p.valid_upto);
  const today = new Date().toISOString().slice(0, 10);
  if (p.valid_upto < today) return "Expired";
  if (p.valid_from && p.valid_from > today) return "Upcoming";
  return fmtDate(p.valid_upto);
}

function validityClass(p) {
  if (!p.valid_upto) return "";
  const today = new Date().toISOString().slice(0, 10);
  if (p.valid_upto < today) return "b-badge b-badge-red";
  if (p.valid_from && p.valid_from > today) return "b-badge b-badge-amber";
  return "b-badge b-badge-green";
}

// ── Watches ──────────────────────────────────────────────────────────────────
watch(listTab,    () => { page.value = 0; });
watch(itemSearch, () => { page.value = 0; });
watch(sortKey,    () => { page.value = 0; });
watch(() => [form.item_code, form.uom], checkDuplicate);

// ── Lifecycle ────────────────────────────────────────────────────────────────
onMounted(() => {
  loadPriceLists();
  document.addEventListener("pointerdown", onDocClick, true);
});
onUnmounted(() => {
  document.removeEventListener("pointerdown", onDocClick, true);
});
</script>

<style>
/* ══ Price Lists Page — pl- prefix ══════════════════════════════════════════ */

/* Root layout */
.pl-root {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 16px;
  align-items: start;
}

/* ── Sidebar ──────────────────────────────────────────────────────────────── */
.pl-sidebar {
  background: #fff;
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 80px);
  overflow: hidden;
  position: sticky;
  top: 16px;
}
.pl-sidebar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 14px 10px;
  border-bottom: 1px solid #F1F3F5;
  flex-shrink: 0;
}
.pl-sidebar-title {
  font-size: 13px;
  font-weight: 700;
  color: #1A1D23;
  display: flex;
  align-items: center;
  gap: 6px;
}
.pl-count-chip {
  background: #E7F5FF;
  color: #1971C2;
  font-size: 10.5px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 10px;
}
.pl-new-btn { font-size: 11.5px !important; padding: 5px 10px !important; }

/* Tab pills */
.pl-tab-row {
  display: flex;
  gap: 4px;
  padding: 8px 12px;
  border-bottom: 1px solid #F1F3F5;
  flex-shrink: 0;
}
.pl-tab-pill {
  background: #fff;
  border: 1px solid #E2E8F0;
  border-radius: 16px;
  padding: 4px 12px;
  font-size: 11.5px;
  font-weight: 600;
  color: #495057;
  cursor: pointer;
  font-family: inherit;
  transition: background .12s, color .12s, border-color .12s;
}
.pl-tab-pill.active {
  background: #3B5BDB;
  color: #fff;
  border-color: #3B5BDB;
}

/* Search */
.pl-sidebar-search {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 8px 12px;
  background: #F8F9FC;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  padding: 7px 10px;
  flex-shrink: 0;
}
.pl-sidebar-search input {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  font: inherit;
  font-size: 12.5px;
  color: #1A1D23;
}

/* Card list */
.pl-sidebar-body {
  flex: 1;
  overflow-y: auto;
}
.pl-card-shimmer {
  margin: 8px 12px;
  height: 58px;
  border-radius: 8px;
}
.pl-sidebar-empty {
  padding: 24px 16px;
  text-align: center;
  color: #868E96;
  font-size: 12.5px;
}

/* Price list card */
.pl-card {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 10px 12px;
  cursor: pointer;
  border-bottom: 1px solid #F8F9FA;
  transition: background .12s;
  border-left: 3px solid transparent;
  position: relative;
}
.pl-card:hover { background: #F8F9FC; }
.pl-card-active {
  background: #EDF2FF !important;
  border-left-color: #3B5BDB;
}
.pl-card-icon {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  flex-shrink: 0;
}
.pl-icon-sell { background: #EBFBEE; }
.pl-icon-buy  { background: #FFF3BF; }
.pl-icon-both { background: #F3F0FF; }
.pl-card-info { flex: 1; min-width: 0; }
.pl-card-name {
  font-size: 13px;
  font-weight: 600;
  color: #1A1D23;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pl-card-sub {
  font-size: 11px;
  color: #868E96;
  margin-top: 1px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Toggle switch */
.pl-toggle {
  position: relative;
  width: 30px;
  height: 17px;
  border-radius: 9px;
  background: #CED4DA;
  border: none;
  cursor: pointer;
  flex-shrink: 0;
  transition: background .2s;
  padding: 0;
}
.pl-toggle.active { background: #2F9E44; }
.pl-toggle-dot {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 13px;
  height: 13px;
  border-radius: 50%;
  background: #fff;
  transition: left .2s;
  box-shadow: 0 1px 2px rgba(0,0,0,.2);
}
.pl-toggle.active .pl-toggle-dot { left: 15px; }

/* Edit button (shows on hover) */
.pl-dots-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: #868E96;
  padding: 3px 5px;
  border-radius: 4px;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: color .12s, background .12s;
}
.pl-dots-btn:hover { color: #3B5BDB; background: #EDF2FF; }

/* Sidebar footer */
.pl-sidebar-foot {
  padding: 10px 12px;
  border-top: 1px solid #F1F3F5;
  flex-shrink: 0;
}

/* ── Content panel ────────────────────────────────────────────────────────── */
.pl-content {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* Empty state */
.pl-empty-state {
  background: #fff;
  border: 1px dashed #E2E8F0;
  border-radius: 14px;
  padding: 80px 40px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.pl-es-icon  { font-size: 52px; }
.pl-es-title { font-size: 16px; font-weight: 700; color: #1A1D23; }
.pl-es-sub   { font-size: 13px; color: #868E96; max-width: 320px; }

/* Panel header */
.pl-panel-head { display: flex; flex-direction: column; gap: 10px; }
.pl-panel-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.pl-panel-name {
  font-size: 17px;
  font-weight: 700;
  color: #1A1D23;
  margin: 0;
}

/* Stats chips */
.pl-stats-row { display: flex; gap: 10px; flex-wrap: wrap; }
.pl-stat-chip {
  background: #ffffff;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  padding: 7px 14px;
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 90px;
}
.pl-stat-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .04em;
  color: #868E96;
}
.pl-stat-val {
  font-size: 17px;
  font-weight: 700;
  color: #1A1D23;
}

/* Toolbar */
.pl-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.pl-toolbar-search {
  display: flex;
  align-items: center;
  gap: 7px;
  background: #fff;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  padding: 6px 11px;
  flex: 1;
  max-width: 260px;
}
.pl-toolbar-search input {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  font: inherit;
  font-size: 13px;
  color: #1A1D23;
}
.pl-sort-select {
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  padding: 6px 10px;
  font: inherit;
  font-size: 12.5px;
  color: #374151;
  background: #fff;
  cursor: pointer;
  outline: none;
}
.pl-toolbar-btn { font-size: 12.5px !important; }

/* Table */
.pl-tbl-card { overflow: hidden; }
.pl-row-delete { opacity: 0; transition: opacity .15s; }
.pl-row:hover .pl-row-delete { opacity: 1; }

/* Item cards (mobile) — hidden by default, shown ≤768px */
.pl-item-cards { display: none; }
.pl-item-card {
  background: #fff;
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  padding: 12px 14px;
  cursor: pointer;
  transition: border-color .12s, box-shadow .12s;
}
.pl-item-card:hover { border-color: #C7D2FE; box-shadow: 0 1px 4px rgba(59,91,219,.08); }
.pl-item-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.pl-item-card-codewrap {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}
.pl-item-card-idx {
  font-size: 11px;
  color: #ADB5BD;
  flex-shrink: 0;
}
.pl-item-card-code {
  font-size: 12.5px;
  font-weight: 700;
  color: #3B5BDB;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pl-item-card-delete {
  background: none;
  border: none;
  cursor: pointer;
  color: #C92A2A;
  padding: 4px;
  border-radius: 6px;
  flex-shrink: 0;
  display: flex;
}
.pl-item-card-delete:active { background: #FFF5F5; }
.pl-item-card-name {
  font-size: 14px;
  font-weight: 600;
  color: #1A1D23;
  margin-top: 4px;
}
.pl-item-card-bottom {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 8px;
  margin-top: 8px;
}
.pl-item-card-meta {
  font-size: 11.5px;
  color: #868E96;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  min-width: 0;
}
.pl-item-card-validity {
  font-size: 10.5px !important;
  padding: 1px 7px !important;
  margin-left: 2px;
}
.pl-item-card-rate {
  font-size: 15px;
  font-weight: 700;
  color: #2F9E44;
  flex-shrink: 0;
  white-space: nowrap;
}
.pl-item-card-shimmer {
  height: 76px;
  border-radius: 12px;
}

/* Pagination */
.pl-pagination {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: flex-end;
  padding: 4px 0;
}

/* Mobile overlay */
.pl-mob-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.35);
  z-index: 499;
}
.pl-mob-sidebar-toggle { display: none; }

/* ── Context menu ─────────────────────────────────────────────────────────── */
.pl-ctx-menu {
  position: fixed;
  background: #fff;
  border: 1px solid #E2E8F0;
  border-radius: 9px;
  box-shadow: 0 8px 28px rgba(0,0,0,.13);
  z-index: 9999;
  padding: 4px 0;
  min-width: 150px;
}
.pl-ctx-item {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 15px;
  font-size: 13px;
  cursor: pointer;
  color: #374151;
  font-family: inherit;
  background: none;
  border: none;
  width: 100%;
  text-align: left;
  transition: background .1s;
}
.pl-ctx-item:hover { background: #F3F4F6; }
.pl-ctx-item.danger { color: #C92A2A; }
.pl-ctx-item.danger:hover { background: #FFF5F5; }

/* ── Item Price Drawer ────────────────────────────────────────────────────── */
.pl-drawer-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, .45);
  z-index: 9000;
  display: flex;
  justify-content: flex-end;
}
.pl-drawer {
  width: 480px;
  max-width: 100vw;
  height: 100%;
  background: #fff;
  display: flex;
  flex-direction: column;
  box-shadow: -8px 0 32px rgba(0,0,0,.15);
  animation: pl-slide-in .2s ease;
}
@keyframes pl-slide-in {
  from { transform: translateX(100%); }
  to   { transform: translateX(0); }
}
.pl-drawer-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 18px 22px 14px;
  border-bottom: 1px solid rgba(255,255,255,.12);
  background: linear-gradient(135deg, #1a1d23, #2d3748);
  flex-shrink: 0;
}
.pl-drawer-title { font-size: 15px; font-weight: 700; color: #fff; }
.pl-drawer-sub   { font-size: 11.5px; color: rgba(255,255,255,.6); margin-top: 2px; }
.pl-drawer-body  {
  flex: 1;
  overflow-y: auto;
  padding: 20px 22px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.pl-drawer-foot {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  padding: 12px 22px;
  border-top: 1px solid #E2E8F0;
  background: #FAFAFA;
  flex-shrink: 0;
}

/* Rate input with currency prefix */
.pl-rate-wrap {
  display: flex;
  align-items: stretch;
}
.pl-currency-prefix {
  background: #F1F3F5;
  border: 1px solid #E2E8F0;
  border-right: none;
  border-radius: 6px 0 0 6px;
  padding: 0 11px;
  display: flex;
  align-items: center;
  font-size: 13px;
  color: #495057;
  font-weight: 600;
  flex-shrink: 0;
}
.pl-rate-input { border-radius: 0 6px 6px 0 !important; }

/* Validation */
.pl-field-err {
  color: #C92A2A;
  font-size: 11.5px;
  margin-top: 4px;
  display: block;
}
.pl-dup-warn {
  background: #FFF3BF;
  border: 1px solid #E67700;
  border-radius: 7px;
  padding: 10px 13px;
  font-size: 12.5px;
  color: #7B4800;
  line-height: 1.45;
}

/* Type toggle (3-button) */
.pl-type-toggle {
  display: flex;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  overflow: hidden;
}
.pl-type-btn {
  flex: 1;
  background: #fff;
  border: none;
  border-right: 1px solid #E2E8F0;
  padding: 8px 4px;
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  color: #6B7280;
  cursor: pointer;
  transition: background .12s, color .12s;
}
.pl-type-btn:last-child { border-right: none; }
.pl-type-btn.active { background: #3B5BDB; color: #fff; }
.pl-type-btn:hover:not(.active) { background: #F3F4F6; }

/* Currency change warning in dialog */
.pl-warn-box {
  background: #FFF3BF;
  border: 1px solid #E67700;
  border-radius: 7px;
  padding: 10px 13px;
  font-size: 12.5px;
  color: #7B4800;
  line-height: 1.45;
}

/* CSV import */
.pl-import-step  { display: flex; flex-direction: column; gap: 10px; }
.pl-import-sub   { font-size: 12.5px; font-weight: 700; color: #374151; }
.pl-import-summary { display: flex; gap: 8px; align-items: center; }
.pl-import-preview { max-height: 280px; overflow-y: auto; border: 1px solid #E2E8F0; border-radius: 8px; }
.pl-import-err-row td { background: #FFF5F5; }
.pl-import-ok-row  td { background: #F0FFF4; }

/* ══ RESPONSIVE BREAKPOINTS ══════════════════════════════════════════════════ */

/* Mobile toolbar: hidden on desktop */
.pl-mob-head-actions { display: none; }
.pl-mob-toolbar { display: none; }
.ba-kebab-dots,.ba-kebab-dots::before,.ba-kebab-dots::after{width:3px;height:3px;border-radius:50%;background:#64748b;display:block;}
.ba-kebab-dots{position:relative;}
.ba-kebab-dots::before,.ba-kebab-dots::after{content:"";position:absolute;left:0;}
.ba-kebab-dots::before{top:-5px;}.ba-kebab-dots::after{top:5px;}

/* Empty state sub-text variants: desktop shows desk-only, hides mob-only */
.pl-es-sub--mob-only  { display: none; }
.pl-es-sub--desk-only { display: block; }
/* List picker only visible on mobile (hidden by default) */
.pl-es-list-picker    { display: none; }
.pl-es-new-ghost      { display: none; }

/* Tablet: 768px – 1024px */
@media (max-width: 1024px) {
  .pl-root { grid-template-columns: 260px 1fr; gap: 12px; }
  .pl-col-minqty { display: none; }
  .pl-col-dates  { display: none; }
  .pl-tbl-card   { overflow-x: auto; -webkit-overflow-scrolling: touch; }
  .pl-tbl-card .b-table { min-width: 420px; }
}

/* Mobile: < 768px */
@media (max-width: 768px) {
  /* Switch to single-column, sidebar hidden */
  .pl-root { grid-template-columns: 1fr; gap: 0; }
  .pl-sidebar { display: none; }

  /* Show mobile toolbar */
  .pl-mob-toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 16px;
    background: #fff;
    border-bottom: 1px solid #E2E8F0;
    flex-wrap: wrap;
  }

  /* Group-like price list picker */
  .pl-mob-group-wrap {
    display: flex;
    align-items: center;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    overflow: hidden;
    background: #fff;
    flex: 1 1 auto;
    min-width: 0;
  }
  .pl-mob-group-prefix {
    padding: 0 10px;
    font-size: 11.5px;
    font-weight: 700;
    color: #6B7280;
    background: #F8F9FC;
    border-right: 1px solid #E2E8F0;
    white-space: nowrap;
    align-self: stretch;
    display: flex;
    align-items: center;
    flex-shrink: 0;
  }
  .pl-mob-group-select-wrap {
    position: relative;
    flex: 1;
    min-width: 0;
  }
  .pl-mob-group-select {
    width: 100%;
    border: none;
    background: transparent;
    padding: 8px 28px 8px 10px;
    font-size: 13px;
    font-weight: 600;
    color: #1A1D23;
    font-family: inherit;
    appearance: none;
    -webkit-appearance: none;
    outline: none;
    cursor: pointer;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .pl-mob-group-chev {
    position: absolute;
    right: 8px;
    top: 50%;
    transform: translateY(-50%);
    pointer-events: none;
    color: #868E96;
  }

  /* Tab pills row */
  .pl-mob-tab-row {
    display: flex;
    gap: 4px;
    flex-shrink: 0;
  }
  .pl-mob-tab-pill {
    background: #fff;
    border: 1px solid #E2E8F0;
    border-radius: 16px;
    padding: 5px 10px;
    font-size: 11.5px;
    font-weight: 600;
    color: #495057;
    cursor: pointer;
    font-family: inherit;
    white-space: nowrap;
    transition: background .12s, color .12s, border-color .12s;
  }
  .pl-mob-tab-pill.active {
    background: #3B5BDB;
    color: #fff;
    border-color: #3B5BDB;
  }

  /* New button (icon only) */
  .pl-mob-new-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    background: #3B5BDB;
    color: #fff;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    flex-shrink: 0;
    transition: opacity .12s;
  }
  .pl-mob-new-btn:hover { opacity: .88; }

  /* Content: full width */
  .pl-content { padding-bottom: 24px; }

  /* Panel head: tighter on mobile */
  .pl-mob-panel-head { padding: 12px 14px 10px; }

  /* Toolbar wrap */
  .pl-toolbar { flex-wrap: wrap; gap: 6px; }
  .pl-toolbar-search { max-width: 100%; flex: unset; width: 100%; }

  /* Table: hide, show card list instead */
  .pl-col-uom    { display: none; }
  .pl-col-minqty { display: none; }
  .pl-col-dates  { display: none; }
  .pl-tbl-card   { display: none; }
  .pl-item-cards {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  /* Drawer: bottom sheet */
  .pl-drawer-backdrop { align-items: flex-end; }
  .pl-drawer {
    width: 100vw;
    max-height: 92dvh;
    height: auto;
    border-radius: 18px 18px 0 0;
    animation: pl-slide-up .22s ease;
  }
  @keyframes pl-slide-up {
    from { transform: translateY(100%); }
    to   { transform: translateY(0); }
  }

  /* Stats: 2-col grid */
  .pl-stats-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }

  .pl-drawer-foot .nim-btn {
    width: 100%;
    justify-content: center;
  }

  .pl-es-list-picker { display: flex; }
  .pl-es-new-ghost   { display: inline-flex; }

  /* Empty state: tighter padding */
  .pl-empty-state { padding: 16px 16px 24px; }

  /* Mobile panel header action buttons (Edit + Enable/Disable) */
  .pl-mob-head-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-left: auto;
    flex-shrink: 0;
  }
  .pl-mob-action-btn {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 5px 10px;
    border-radius: 7px;
    border: 1px solid #E2E8F0;
    background: #fff;
    font-size: 12px;
    font-weight: 600;
    color: #495057;
    cursor: pointer;
    font-family: inherit;
    transition: background .12s, border-color .12s;
    white-space: nowrap;
  }
  .pl-mob-action-btn:active { background: #F1F3F5; }
  .pl-mob-action-label { font-size: 11.5px; }

  /* Disable button — red tint */
  .pl-mob-action-disable {
    border-color: #FFC9C9;
    color: #C92A2A;
    background: #FFF5F5;
  }
  .pl-mob-action-disable:active { background: #FFE3E3; }

  /* Enable button — green tint */
  .pl-mob-action-enable {
    border-color: #B2F2BB;
    color: #2B8A3E;
    background: #EBFBEE;
  }
  .pl-mob-action-enable:active { background: #D3F9D8; }

  /* Toggle dot inside the enable/disable button */
  .pl-mob-toggle-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: currentColor;
    flex-shrink: 0;
  }

  /* Mobile panel header action buttons: visible on mobile */
  .pl-mob-head-actions { display: flex; }

  /* On mobile: show mobile guidance, hide desktop guidance */
  .pl-es-sub--mob-only  { display: block; }
  .pl-es-sub--desk-only { display: none; }

  /* Mobile list picker inside empty state */
  .pl-es-list-picker {
    display: flex;
    flex-direction: column;
    gap: 0;
    width: 100%;
    max-width: 400px;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    overflow: hidden;
    margin-top: 20px;
  }
  .pl-es-pick-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 13px 16px;
    background: #fff;
    border-bottom: 1px solid #F1F3F5;
    cursor: pointer;
    transition: background .12s;
  }
  .pl-es-pick-row:last-child { border-bottom: none; }
  .pl-es-pick-row:active { background: #F8F9FC; }
  .pl-es-pick-icon { font-size: 20px; flex-shrink: 0; }
  .pl-es-pick-info { flex: 1; min-width: 0; }
  .pl-es-pick-name {
    font-size: 13.5px;
    font-weight: 700;
    color: #1A1D23;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .pl-es-pick-sub { font-size: 11.5px; color: #868E96; margin-top: 1px; }
  .pl-es-pick-arrow {
    font-size: 20px;
    color: #ADB5BD;
    font-weight: 300;
    flex-shrink: 0;
  }
  .pl-es-no-match {
    margin-top: 20px;
    font-size: 13px;
    color: #ADB5BD;
  }
  .pl-es-new-ghost {
    margin-top: 16px;
    font-size: 12px;
    color: #495057;
  }
}

/* Extra small: < 480px */
@media (max-width: 480px) {
  .pl-mob-toolbar { padding: 10px 12px; gap: 6px; }
  .pl-mob-tab-row { order: 2; width: 100%; }
  .pl-mob-tab-pill { flex: 1; text-align: center; }
  .pl-mob-group-wrap { order: 0; }
  .pl-mob-new-btn { order: 1; }
}
</style>