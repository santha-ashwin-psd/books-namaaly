<template>
  <div class="qct-page">

    <!-- ── Header bar ── -->
    <div class="qct-header-bar">
      <div class="qct-header-left">
        <div class="qct-header-ico">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
            <polyline points="10 9 9 9 8 9"/>
          </svg>
        </div>
        <div>
          <div class="qct-header-title">QC Templates</div>
          <div class="qct-header-sub">Define reusable inspection parameter sets for items</div>
        </div>
      </div>
      <div class="qct-header-right">
        <button class="qct-btn-ghost" @click="load"><span v-html="icon('refresh', 14)"></span></button>
        <button class="qct-btn-ghost" @click="exportCSV" :disabled="!filtered.length">
          <span v-html="icon('download', 14)"></span> Export
        </button>
        <button class="qct-btn-primary" @click="openCreate">
          <span v-html="icon('plus', 13)"></span> New Template
        </button>
      </div>
    </div>

    <!-- ── Stats strip ── -->
    <div class="qct-stats-strip">
      <div class="qct-stat">
        <div class="qct-stat-ico" style="background:#eff6ff;color:#2563eb">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
        </div>
        <div><div class="qct-stat-lbl">Total Templates</div><div class="qct-stat-val">{{ list.length }}</div></div>
      </div>
      <div class="qct-stat">
        <div class="qct-stat-ico" style="background:#f0fdf4;color:#16a34a">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 7H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z"/>
            <circle cx="12" cy="12" r="1"/>
          </svg>
        </div>
        <div><div class="qct-stat-lbl">Item-Specific</div><div class="qct-stat-val">{{ list.filter(t => t.item).length }}</div></div>
      </div>
      <div class="qct-stat">
        <div class="qct-stat-ico" style="background:#faf5ff;color:#7c3aed">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
        </div>
        <div><div class="qct-stat-lbl">Generic (All Items)</div><div class="qct-stat-val">{{ list.filter(t => !t.item).length }}</div></div>
      </div>
      <div class="qct-stat">
        <div class="qct-stat-ico" style="background:#fffbeb;color:#d97706">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
          </svg>
        </div>
        <div><div class="qct-stat-lbl">Avg Parameters</div><div class="qct-stat-val">{{ avgParams }}</div></div>
      </div>
    </div>

    <!-- ── Filter / search bar ── -->
    <div class="qct-filter-bar">
      <div class="qct-search-wrap">
        <span v-html="icon('search', 13)" style="color:#9ca3af;flex-shrink:0"></span>
        <input v-model="search" placeholder="Search template name, item, description…" class="qct-search-input" />
      </div>
      <select v-model="filterType" class="qct-select">
        <option value="">All Types</option>
        <option value="All">All</option>
        <option value="Incoming">Incoming</option>
        <option value="Outgoing">Outgoing</option>
        <option value="In Process">In Process</option>
      </select>
      <select v-model="filterScope" class="qct-select">
        <option value="">All Scopes</option>
        <option value="specific">Item-Specific</option>
        <option value="generic">Generic</option>
      </select>
    </div>

    <!-- ── Desktop Table ── -->
    <div class="qct-card qct-table-wrap">
      <table class="qct-table">
        <thead><tr>
          <th @click="sort('template_name')" class="sortable">Template Name <span v-html="sortArrow('template_name')"></span></th>
          <th @click="sort('item')" class="sortable">Item <span v-html="sortArrow('item')"></span></th>
          <th>Item Group</th>
          <th @click="sort('inspection_type')" class="sortable">Inspection Type <span v-html="sortArrow('inspection_type')"></span></th>
          <th class="ta-c" style="width:110px">Parameters</th>
          <th>Description</th>
          <th style="width:80px"></th>
        </tr></thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 6" :key="n"><td colspan="7"><div class="qct-shimmer"></div></td></tr>
          </template>
          <template v-else>
            <tr v-for="t in paginated" :key="t.name" class="qct-row" @click="openView(t)">
              <td>
                <div style="display:flex;align-items:center;gap:8px">
                  <div class="qct-tpl-ico">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14 2 14 8 20 8"/>
                    </svg>
                  </div>
                  <span class="qct-tpl-name">{{ t.template_name }}</span>
                </div>
              </td>
              <td>
                <span v-if="t.item" class="qct-item-badge">{{ t.item }}</span>
                <span v-else class="qct-generic-badge">Generic</span>
              </td>
              <td style="font-size:12px;color:#6b7280">{{ t.item_group || '—' }}</td>
              <td><span class="qct-type-badge" :style="typeStyle(t.inspection_type)">{{ t.inspection_type || 'All' }}</span></td>
              <td class="ta-c">
                <span class="qct-param-count">{{ t.parameter_count ?? '—' }}</span>
              </td>
              <td style="font-size:12px;color:#6b7280;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
                {{ t.description || '—' }}
              </td>
              <td @click.stop style="display:flex;gap:6px;padding:10px 8px">
                <button class="qct-act-btn" @click="openEdit(t)" title="Edit">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                </button>
                <button class="qct-act-btn" @click="openView(t)" title="View">
                  <span v-html="icon('eye', 13)"></span>
                </button>
                <button class="qct-act-btn qct-act-del" @click="deleteTemplate(t)" title="Delete">
                  <span v-html="icon('trash', 13)"></span>
                </button>
              </td>
            </tr>
            <tr v-if="!filtered.length">
              <td colspan="7" class="qct-empty">
                <div style="font-size:36px;margin-bottom:10px">📋</div>
                <div style="font-weight:700;margin-bottom:6px;font-size:15px">No QC Templates found</div>
                <div style="font-size:13px;color:#9ca3af;margin-bottom:14px">
                  Templates define the parameters inspectors check during a QC Inspection
                </div>
                <button class="qct-btn-primary" @click="openCreate">
                  <span v-html="icon('plus', 13)"></span> Create First Template
                </button>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- ── Mobile Card List (≤425px) ── -->
    <div class="qct-mobile-list">
      <!-- shimmer -->
      <template v-if="loading">
        <div v-for="n in 4" :key="n" class="qct-mobile-shimmer"></div>
      </template>
      <!-- empty -->
      <div v-else-if="!filtered.length" class="qct-mobile-empty">
        <div style="font-size:32px;margin-bottom:8px">📋</div>
        <div style="font-weight:700;margin-bottom:6px;font-size:14px">No QC Templates found</div>
        <div style="font-size:12px;color:#9ca3af;margin-bottom:14px">Templates define the parameters inspectors check during a QC Inspection</div>
        <button class="qct-btn-primary" @click="openCreate"><span v-html="icon('plus', 13)"></span> Create First Template</button>
      </div>
      <!-- cards -->
      <div v-else v-for="t in paginated" :key="t.name" class="qct-mob-card" @click="openView(t)">
        <!-- top: name + param count -->
        <div class="qct-mob-top">
          <div style="display:flex;align-items:center;gap:8px;min-width:0">
            <div class="qct-mob-ico">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
            </div>
            <span class="qct-mob-name">{{ t.template_name }}</span>
          </div>
          <span class="qct-param-count" style="flex-shrink:0">{{ t.parameter_count || 0 }} params</span>
        </div>
        <!-- badges row -->
        <div class="qct-mob-badges">
          <span class="qct-type-badge" :style="typeStyle(t.inspection_type)">{{ t.inspection_type || 'All' }}</span>
          <span v-if="t.item" class="qct-item-badge">{{ t.item }}</span>
          <span v-else class="qct-generic-badge">Generic</span>
          <span v-if="t.item_group" class="qct-mob-group">{{ t.item_group }}</span>
        </div>
        <!-- parameters count row -->
        <div class="qct-mob-params-row">
          <span class="qct-mob-params-lbl">Parameters</span>
          <span class="qct-param-count">{{ t.parameter_count ?? 0 }}</span>
        </div>
        <!-- description -->
        <div v-if="t.description" class="qct-mob-desc">{{ t.description }}</div>
        <!-- footer actions -->
        <div class="qct-mob-footer" @click.stop>
          <span class="qct-mob-footer-hint">Tap to view details</span>
          <div style="display:flex;gap:6px">
            <button class="qct-act-btn" @click.stop="openEdit(t)">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            </button>
            <button class="qct-act-btn" @click.stop="openView(t)"><span v-html="icon('eye', 13)"></span></button>
            <button class="qct-act-btn qct-act-del" @click.stop="deleteTemplate(t)"><span v-html="icon('trash', 13)"></span></button>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="filtered.length > pageSize" style="display:flex;justify-content:space-between;align-items:center;font-size:12px;color:#6b7280;padding:4px 2px">
      <span>Showing {{ paginated.length }} of {{ filtered.length }}</span>
      <div style="display:flex;gap:4px">
        <button class="qct-pg-btn" :disabled="page===1" @click="page--">‹</button>
        <span style="padding:4px 8px;font-weight:600">{{ page }} / {{ totalPages }}</span>
        <button class="qct-pg-btn" :disabled="page===totalPages" @click="page++">›</button>
      </div>
    </div>

    <!-- ── Create Drawer ── -->
    <div v-if="createOpen" class="qct-overlay" @click.self="createOpen=false"></div>
    <div class="qct-drawer" :class="{open: createOpen}">
      <div class="qct-dheader">
        <button class="qct-dclose" @click="createOpen=false"><span v-html="icon('x', 16)"></span></button>
        <div class="qct-dh-top">
          <div class="qct-dh-ico">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
            </svg>
          </div>
          <div>
            <div class="qct-dh-title">New QC Template</div>
            <div class="qct-dh-sub">Define parameters for quality inspection</div>
          </div>
        </div>
      </div>
      <div class="qct-dbody">
        <div class="qct-section-lbl">Basic Information</div>
        <div class="qct-fields-grid">
          <div class="qct-field" style="grid-column:1/-1">
            <label class="qct-label">Template Name <span class="req">*</span></label>
            <input v-model="form.template_name" class="qct-input" placeholder="e.g. Incoming Raw Material Check" />
          </div>
          <div class="qct-field">
            <label class="qct-label">Item <span style="font-weight:400;color:#9ca3af">(Optional)</span></label>
            <SearchableSelect
              v-model="form.item"
              :options="items"
              placeholder="Search item code…"
              value-key="value"
              label-key="label"
            />
            <span v-if="form.item" style="font-size:11px;color:#6b7280;margin-top:2px">
              Template will apply only to this item
            </span>
          </div>
          <div class="qct-field">
            <label class="qct-label">Item Group <span style="font-weight:400;color:#9ca3af">(Optional)</span></label>
            <SearchableSelect
              v-model="form.item_group"
              :options="itemGroups"
              placeholder="Search item group…"
              value-key="value"
              label-key="label"
            />
            <span v-if="form.item_group" style="font-size:11px;color:#6b7280;margin-top:2px">
              Template will apply to all items in this group
            </span>
          </div>
          <div class="qct-field" style="grid-column:1/-1">
            <label class="qct-label">Applicable Inspection Type</label>
            <select v-model="form.inspection_type" class="qct-select-full">
              <option value="All">All — applicable for any inspection</option>
              <option value="Incoming">Incoming — purchasing goods</option>
              <option value="Outgoing">Outgoing — dispatching goods</option>
              <option value="In Process">In Process — manufacturing</option>
            </select>
          </div>
          <div class="qct-field" style="grid-column:1/-1">
            <label class="qct-label">Description</label>
            <textarea v-model="form.description" rows="2" class="qct-input" placeholder="Optional notes about this template…"></textarea>
          </div>
        </div>

        <div class="qct-section-lbl" style="margin-top:4px">
          Inspection Parameters
          <button class="qct-add-param-btn" @click="addParam">
            <span v-html="icon('plus', 11)"></span> Add Parameter
          </button>
        </div>

        <div v-if="form.parameters.length === 0" class="qct-param-empty">
          No parameters yet — click "Add Parameter" to define what inspectors should check
        </div>

        <div v-for="(p, i) in form.parameters" :key="i" class="qct-param-card">
          <div class="qct-param-header">
            <span class="qct-param-num">{{ i + 1 }}</span>
            <span style="font-size:12.5px;font-weight:600;color:#374151;flex:1">
              {{ p.parameter || 'New Parameter' }}
            </span>
            <button class="qct-param-del" @click="removeParam(i)"><span v-html="icon('x', 12)"></span></button>
          </div>
          <div class="qct-param-fields">
            <div class="qct-field">
              <label class="qct-label">Parameter Name <span class="req">*</span></label>
              <input v-model="p.parameter" class="qct-input qct-input-sm" placeholder="e.g. Moisture Content" />
            </div>
            <div class="qct-field">
              <label class="qct-label">Type</label>
              <select v-model="p.parameter_type" class="qct-select-full qct-input-sm">
                <option value="Numeric">Numeric (min/max range)</option>
                <option value="Non-Numeric">Non-Numeric (expected value)</option>
                <option value="Formula">Formula</option>
              </select>
            </div>
            <template v-if="p.parameter_type === 'Numeric'">
              <div class="qct-field">
                <label class="qct-label">Min Value</label>
                <input v-model.number="p.min_value" type="number" step="any" class="qct-input qct-input-sm" placeholder="0" />
              </div>
              <div class="qct-field">
                <label class="qct-label">Max Value</label>
                <input v-model.number="p.max_value" type="number" step="any" class="qct-input qct-input-sm" placeholder="100" />
              </div>
            </template>
            <template v-else-if="p.parameter_type === 'Non-Numeric'">
              <div class="qct-field" style="grid-column:1/-1">
                <label class="qct-label">Acceptance Criteria Value</label>
                <input v-model="p.acceptance_criteria_value" class="qct-input qct-input-sm" placeholder="e.g. No visible defects" />
              </div>
            </template>
            <template v-else>
              <div class="qct-field" style="grid-column:1/-1">
                <label class="qct-label">Formula</label>
                <input v-model="p.formula" class="qct-input qct-input-sm" placeholder="e.g. (reading_1 + reading_2) / 2 < 5" />
              </div>
            </template>
          </div>
        </div>
      </div>
      <div class="qct-dfooter">
        <button class="qct-btn-ghost" @click="createOpen=false">Cancel</button>
        <button class="qct-btn-primary" :disabled="saving" @click="saveTemplate">
          <span v-html="icon('save', 13)"></span>{{ saving ? 'Saving…' : 'Save Template' }}
        </button>
      </div>
    </div>

    <!-- ── View / Edit Drawer ── -->
    <div v-if="viewOpen" class="qct-overlay" @click.self="viewOpen=false"></div>
    <div class="qct-drawer qct-view-drawer" :class="{open: viewOpen}">
      <template v-if="viewDoc">
        <div class="qct-dheader">
          <button class="qct-dclose" @click="viewOpen=false"><span v-html="icon('x', 16)"></span></button>
          <div class="qct-dh-top">
            <div class="qct-dh-ico">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
            </div>
            <div>
              <div class="qct-dh-title">{{ viewDoc.template_name }}</div>
              <div class="qct-dh-sub">{{ viewDoc.inspection_type || 'All' }} · {{ (viewDoc.parameters || []).length }} parameter(s)</div>
            </div>
            <span class="qct-type-badge" :style="typeStyle(viewDoc.inspection_type)" style="margin-left:auto;flex-shrink:0">
              {{ viewDoc.inspection_type || 'All' }}
            </span>
          </div>
        </div>
        <div class="qct-dbody">

          <!-- Summary -->
          <div class="qct-summary-grid">
            <div class="qct-sum-item">
              <span class="qct-sum-lbl">Item</span>
              <span class="qct-sum-val">{{ viewDoc.item || 'Generic (all items)' }}</span>
            </div>
            <div class="qct-sum-item">
              <span class="qct-sum-lbl">Item Group</span>
              <span class="qct-sum-val">{{ viewDoc.item_group || '—' }}</span>
            </div>
            <div class="qct-sum-item">
              <span class="qct-sum-lbl">Parameters</span>
              <span class="qct-sum-val" style="color:#2563eb;font-weight:700">{{ (viewDoc.parameters || []).length }}</span>
            </div>
            <div class="qct-sum-item">
              <span class="qct-sum-lbl">Inspection Type</span>
              <span class="qct-sum-val">{{ viewDoc.inspection_type || 'All' }}</span>
            </div>
          </div>

          <div v-if="viewDoc.description" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 14px;font-size:13px;color:#374151">
            {{ viewDoc.description }}
          </div>

          <!-- Parameters table -->
          <div v-if="viewLoading">
            <div v-for="n in 3" :key="n" class="qct-shimmer" style="height:48px;margin-bottom:8px;border-radius:8px"></div>
          </div>
          <div v-else-if="(viewDoc.parameters || []).length">
            <div class="qct-view-sec-lbl">Parameters ({{ viewDoc.parameters.length }})</div>
            <table class="qct-params-tbl">
              <thead><tr>
                <th>#</th>
                <th>Parameter Name</th>
                <th>Type</th>
                <th>Range / Criteria</th>
              </tr></thead>
              <tbody>
                <tr v-for="(p, i) in viewDoc.parameters" :key="p.name || i">
                  <td style="color:#9ca3af;font-size:11px;font-weight:700;width:28px">{{ i + 1 }}</td>
                  <td style="font-weight:600;font-size:13px">{{ p.parameter }}</td>
                  <td><span class="qct-type-mini" :style="paramTypeStyle(p.parameter_type)">{{ p.parameter_type }}</span></td>
                  <td style="font-size:12px;color:#374151">
                    <template v-if="p.parameter_type === 'Numeric'">
                      {{ p.min_value ?? '—' }} → {{ p.max_value ?? '—' }}
                    </template>
                    <template v-else-if="p.parameter_type === 'Non-Numeric'">
                      {{ p.acceptance_criteria_value || '—' }}
                    </template>
                    <template v-else>
                      <code style="font-size:11px;background:#f3f4f6;padding:2px 6px;border-radius:4px">{{ p.formula || '—' }}</code>
                    </template>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="qct-param-empty">No parameters defined for this template</div>

        </div>
        <div class="qct-dfooter">
          <button class="qct-btn-ghost" @click="viewOpen=false">Close</button>
          <button class="qct-btn-edit" @click="openEdit(viewDoc); viewOpen=false">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            Edit
          </button>
          <button class="qct-act-btn qct-act-del" style="padding:8px 14px;border-radius:8px;font-size:13px;font-weight:600;display:flex;align-items:center;gap:6px" @click="deleteTemplate(viewDoc)">
            <span v-html="icon('trash', 13)"></span> Delete
          </button>
        </div>
      </template>
    </div>

    <!-- ── Edit Drawer ── -->
    <div v-if="editOpen" class="qct-overlay" @click.self="editOpen=false"></div>
    <div class="qct-drawer" :class="{open: editOpen}">
      <div class="qct-dheader" style="background:linear-gradient(135deg,#1e3a5f,#2563eb)">
        <button class="qct-dclose" @click="editOpen=false"><span v-html="icon('x', 16)"></span></button>
        <div class="qct-dh-top">
          <div class="qct-dh-ico">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          </div>
          <div>
            <div class="qct-dh-title">Edit QC Template</div>
            <div class="qct-dh-sub">{{ editForm._name }}</div>
          </div>
        </div>
      </div>
      <div class="qct-dbody">
        <div class="qct-section-lbl">Basic Information</div>
        <div class="qct-fields-grid">
          <div class="qct-field" style="grid-column:1/-1">
            <label class="qct-label">Template Name <span class="req">*</span></label>
            <input v-model="editForm.template_name" class="qct-input" placeholder="e.g. Incoming Raw Material Check" />
          </div>
          <div class="qct-field">
            <label class="qct-label">Item <span style="font-weight:400;color:#9ca3af">(Optional)</span></label>
            <SearchableSelect
              v-model="editForm.item"
              :options="items"
              placeholder="Search item code…"
              value-key="value"
              label-key="label"
            />
          </div>
          <div class="qct-field">
            <label class="qct-label">Item Group <span style="font-weight:400;color:#9ca3af">(Optional)</span></label>
            <SearchableSelect
              v-model="editForm.item_group"
              :options="itemGroups"
              placeholder="Search item group…"
              value-key="value"
              label-key="label"
            />
          </div>
          <div class="qct-field" style="grid-column:1/-1">
            <label class="qct-label">Applicable Inspection Type</label>
            <select v-model="editForm.inspection_type" class="qct-select-full">
              <option value="All">All — applicable for any inspection</option>
              <option value="Incoming">Incoming — purchasing goods</option>
              <option value="Outgoing">Outgoing — dispatching goods</option>
              <option value="In Process">In Process — manufacturing</option>
            </select>
          </div>
          <div class="qct-field" style="grid-column:1/-1">
            <label class="qct-label">Description</label>
            <textarea v-model="editForm.description" rows="2" class="qct-input" placeholder="Optional notes about this template…"></textarea>
          </div>
        </div>

        <div class="qct-section-lbl" style="margin-top:4px">
          Inspection Parameters
          <button class="qct-add-param-btn" @click="addEditParam">
            <span v-html="icon('plus', 11)"></span> Add Parameter
          </button>
        </div>

        <div v-if="editForm.parameters.length === 0" class="qct-param-empty">
          No parameters yet — click "Add Parameter" to define what inspectors should check
        </div>

        <div v-for="(p, i) in editForm.parameters" :key="i" class="qct-param-card">
          <div class="qct-param-header">
            <span class="qct-param-num">{{ i + 1 }}</span>
            <span style="font-size:12.5px;font-weight:600;color:#374151;flex:1">
              {{ p.parameter || 'New Parameter' }}
            </span>
            <button class="qct-param-del" @click="removeEditParam(i)"><span v-html="icon('x', 12)"></span></button>
          </div>
          <div class="qct-param-fields">
            <div class="qct-field">
              <label class="qct-label">Parameter Name <span class="req">*</span></label>
              <input v-model="p.parameter" class="qct-input qct-input-sm" placeholder="e.g. Moisture Content" />
            </div>
            <div class="qct-field">
              <label class="qct-label">Type</label>
              <select v-model="p.parameter_type" class="qct-select-full qct-input-sm">
                <option value="Numeric">Numeric (min/max range)</option>
                <option value="Non-Numeric">Non-Numeric (expected value)</option>
                <option value="Formula">Formula</option>
              </select>
            </div>
            <template v-if="p.parameter_type === 'Numeric'">
              <div class="qct-field">
                <label class="qct-label">Min Value</label>
                <input v-model.number="p.min_value" type="number" step="any" class="qct-input qct-input-sm" placeholder="0" />
              </div>
              <div class="qct-field">
                <label class="qct-label">Max Value</label>
                <input v-model.number="p.max_value" type="number" step="any" class="qct-input qct-input-sm" placeholder="100" />
              </div>
            </template>
            <template v-else-if="p.parameter_type === 'Non-Numeric'">
              <div class="qct-field" style="grid-column:1/-1">
                <label class="qct-label">Acceptance Criteria Value</label>
                <input v-model="p.acceptance_criteria_value" class="qct-input qct-input-sm" placeholder="e.g. No visible defects" />
              </div>
            </template>
            <template v-else>
              <div class="qct-field" style="grid-column:1/-1">
                <label class="qct-label">Formula</label>
                <input v-model="p.formula" class="qct-input qct-input-sm" placeholder="e.g. (reading_1 + reading_2) / 2 < 5" />
              </div>
            </template>
          </div>
        </div>
      </div>
      <div class="qct-dfooter">
        <button class="qct-btn-ghost" @click="editOpen=false">Cancel</button>
        <button class="qct-btn-primary" :disabled="editSaving" @click="updateTemplate">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
          {{ editSaving ? 'Saving…' : 'Save Changes' }}
        </button>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { apiCall, apiList } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";
import SearchableSelect from "../components/SearchableSelect.vue";

const { toast } = useToast();

// ── State ──────────────────────────────────────────────────────────────────────
const list        = ref([]);
const loading     = ref(false);
const createOpen  = ref(false);
const viewOpen    = ref(false);
const viewDoc     = ref(null);
const viewLoading = ref(false);
const editOpen    = ref(false);
const editSaving  = ref(false);
const saving      = ref(false);
const search      = ref("");
const filterType  = ref("");
const filterScope = ref("");
const page        = ref(1);
const pageSize    = 40;
const sortCol     = ref("template_name");
const sortDir     = ref("asc");

// ── Dropdown data ──────────────────────────────────────────────────────────────
const items      = ref([]);
const itemGroups = ref([]);

const form = reactive({
  template_name:  "",
  item:           "",
  item_group:     "",
  inspection_type: "All",
  description:    "",
  parameters:     [],
});

const editForm = reactive({
  _name:          "",
  template_name:  "",
  item:           "",
  item_group:     "",
  inspection_type: "All",
  description:    "",
  parameters:     [],
});

// ── Type helpers ───────────────────────────────────────────────────────────────
const TYPE_COLOR = {
  "All":        "#6b7280",
  "Incoming":   "#0891b2",
  "Outgoing":   "#ea580c",
  "In Process": "#7c3aed",
};
function typeStyle(t) {
  const c = TYPE_COLOR[t] || TYPE_COLOR["All"];
  return `background:${c}18;color:${c};border:1px solid ${c}33`;
}
function paramTypeStyle(pt) {
  if (pt === "Numeric")     return "background:#eff6ff;color:#2563eb";
  if (pt === "Non-Numeric") return "background:#f0fdf4;color:#16a34a";
  return "background:#faf5ff;color:#7c3aed";
}

// ── Computed ───────────────────────────────────────────────────────────────────
const avgParams = computed(() => {
  if (!list.value.length) return 0;
  const total = list.value.reduce((s, t) => s + (t.parameter_count || 0), 0);
  return Math.round(total / list.value.length);
});

const filtered = computed(() => {
  let r = list.value;
  if (filterType.value)  r = r.filter(t => (t.inspection_type || "All") === filterType.value);
  if (filterScope.value === "specific") r = r.filter(t => t.item);
  if (filterScope.value === "generic")  r = r.filter(t => !t.item);
  if (search.value.trim()) {
    const q = search.value.toLowerCase();
    r = r.filter(t =>
      (t.template_name || "").toLowerCase().includes(q) ||
      (t.item          || "").toLowerCase().includes(q) ||
      (t.description   || "").toLowerCase().includes(q)
    );
  }
  return r;
});

const sorted = computed(() => {
  const col = sortCol.value;
  return [...filtered.value].sort((a, b) => {
    const av = a[col] ?? "", bv = b[col] ?? "";
    const c = String(av).localeCompare(String(bv));
    return sortDir.value === "asc" ? c : -c;
  });
});

const totalPages = computed(() => Math.max(1, Math.ceil(sorted.value.length / pageSize)));
const paginated  = computed(() => {
  const s = (page.value - 1) * pageSize;
  return sorted.value.slice(s, s + pageSize);
});

function sort(col) {
  if (sortCol.value === col) sortDir.value = sortDir.value === "asc" ? "desc" : "asc";
  else { sortCol.value = col; sortDir.value = "asc"; }
}
function sortArrow(col) {
  if (sortCol.value !== col) return '<span style="color:#d1d5db">⇅</span>';
  return sortDir.value === "asc" ? "↑" : "↓";
}

// ── API ────────────────────────────────────────────────────────────────────────
async function load() {
  loading.value = true;
  try {
    const res = await apiCall("zoho_books_clone.api.qc.get_templates", {});
    const templates = res?.message || res || [];
    // Fetch parameter counts in one pass via detail calls (or use the count from list)
    list.value = templates.map(t => ({ ...t, parameter_count: t.parameter_count || null }));
  } catch (e) {
    toast.error(e.message || "Failed to load QC Templates");
  } finally {
    loading.value = false;
  }
}

async function openView(t) {
  viewDoc.value = { ...t };
  viewOpen.value = true;
  viewLoading.value = true;
  try {
    const res = await apiCall("zoho_books_clone.api.qc.get_template_detail", { template_name: t.name || t.template_name });
    if (res?.message) viewDoc.value = res.message;
    else if (res)     viewDoc.value = res;
  } catch { /* keep list row */ }
  viewLoading.value = false;
}

function openCreate() {
  Object.assign(form, {
    template_name:  "",
    item:           "",
    item_group:     "",
    inspection_type: "All",
    description:    "",
    parameters:     [],
  });
  // Load dropdowns when drawer opens
  fetchItems("");
  fetchItemGroups("");
  createOpen.value = true;
}

function addParam() {
  form.parameters.push({
    parameter:                 "",
    parameter_type:           "Numeric",
    min_value:                null,
    max_value:                null,
    acceptance_criteria_value: "",
    formula:                  "",
  });
}

// ── Dropdown fetchers ──────────────────────────────────────────────────────────
async function fetchItems(q = "") {
  try {
    const rows = await apiList("Item", {
      fields:  ["name", "item_name"],
      filters: [["disabled", "=", 0], ...(q ? [["name", "like", `%${q}%`]] : [])],
      limit:   50,
      order:   "item_name asc",
    });
    items.value = rows.map(r => ({ value: r.name, label: r.item_name ? `${r.name} — ${r.item_name}` : r.name }));
  } catch { items.value = []; }
}

async function fetchItemGroups(q = "") {
  try {
    const rows = await apiList("Item Group", {
      fields:  ["name"],
      filters: [["is_group", "=", 0], ...(q ? [["name", "like", `%${q}%`]] : [])],
      limit:   50,
      order:   "name asc",
    });
    itemGroups.value = rows.map(r => ({ value: r.name, label: r.name }));
  } catch { itemGroups.value = []; }
}

function removeParam(i) {
  form.parameters.splice(i, 1);
}

async function saveTemplate() {
  if (!form.template_name.trim()) {
    return toast.error("Template Name is required.");
  }
  saving.value = true;
  try {
    await apiCall("frappe.client.insert", {
      doc: {
        doctype: "QC Inspection Template",
        template_name: form.template_name.trim(),
        item:           form.item.trim() || null,
        item_group:     form.item_group.trim() || null,
        inspection_type: form.inspection_type,
        description:    form.description.trim() || null,
        parameters: form.parameters.map((p, i) => ({
          doctype:                  "QC Inspection Template Parameter",
          idx:                      i + 1,
          parameter:                 p.parameter,
          parameter_type:           p.parameter_type,
          min_value:                p.parameter_type === "Numeric"     ? (p.min_value ?? null) : null,
          max_value:                p.parameter_type === "Numeric"     ? (p.max_value ?? null) : null,
          acceptance_criteria_value: p.parameter_type === "Non-Numeric" ? p.acceptance_criteria_value : null,
          formula:                  p.parameter_type === "Formula"     ? p.formula : null,
        })),
      },
    });
    toast.success(`Template "${form.template_name}" created`);
    createOpen.value = false;
    await load();
  } catch (e) {
    toast.error(e.message || "Failed to save template");
  } finally {
    saving.value = false;
  }
}

async function deleteTemplate(t) {
  const name = t.name || t.template_name;
  if (!confirm(`Delete template "${t.template_name}"? This cannot be undone.`)) return;
  try {
    await apiCall("frappe.client.delete", { doctype: "QC Inspection Template", name });
    toast.success(`Template "${t.template_name}" deleted`);
    viewOpen.value = false;
    await load();
  } catch (e) {
    toast.error(e.message || "Failed to delete template");
  }
}

// ── Edit Template ──────────────────────────────────────────────────────────────
async function openEdit(t) {
  // Fetch full detail first so we have all parameters
  let detail = { ...t };
  try {
    const res = await apiCall("zoho_books_clone.api.qc.get_template_detail", { template_name: t.name || t.template_name });
    if (res?.message) detail = res.message;
    else if (res)     detail = res;
  } catch { /* fall back to list row */ }

  Object.assign(editForm, {
    _name:           detail.name || detail.template_name || "",
    template_name:   detail.template_name || "",
    item:            detail.item            || "",
    item_group:      detail.item_group      || "",
    inspection_type: detail.inspection_type || "All",
    description:     detail.description     || "",
    parameters: (detail.parameters || []).map(p => ({
      name:                      p.name || "",
      parameter:                 p.parameter || "",
      parameter_type:            p.parameter_type || "Numeric",
      min_value:                 p.min_value ?? null,
      max_value:                 p.max_value ?? null,
      acceptance_criteria_value: p.acceptance_criteria_value || "",
      formula:                   p.formula || "",
    })),
  });
  // Load dropdowns
  fetchItems("");
  fetchItemGroups("");
  editOpen.value = true;
}

function addEditParam() {
  editForm.parameters.push({
    name: "",
    parameter:                 "",
    parameter_type:           "Numeric",
    min_value:                null,
    max_value:                null,
    acceptance_criteria_value: "",
    formula:                  "",
  });
}

function removeEditParam(i) {
  editForm.parameters.splice(i, 1);
}

async function updateTemplate() {
  if (!editForm.template_name.trim()) {
    return toast.error("Template Name is required.");
  }
  editSaving.value = true;
  try {
    const docName = editForm._name;
    // Update the parent doc fields
    await apiCall("frappe.client.set_value", {
      doctype: "QC Inspection Template",
      name: docName,
      fieldname: JSON.stringify({
        template_name:  editForm.template_name.trim(),
        item:           editForm.item.trim()        || null,
        item_group:     editForm.item_group.trim()  || null,
        inspection_type: editForm.inspection_type,
        description:    editForm.description.trim() || null,
      }),
    });
    // Replace all parameters by saving full doc
    await apiCall("frappe.client.save", {
      doc: {
        doctype:        "QC Inspection Template",
        name:           docName,
        template_name:  editForm.template_name.trim(),
        item:           editForm.item.trim()        || null,
        item_group:     editForm.item_group.trim()  || null,
        inspection_type: editForm.inspection_type,
        description:    editForm.description.trim() || null,
        parameters: editForm.parameters.map((p, i) => ({
          doctype:                  "QC Inspection Template Parameter",
          name:                     p.name || undefined,
          idx:                      i + 1,
          parameter:                p.parameter,
          parameter_type:           p.parameter_type,
          min_value:                p.parameter_type === "Numeric"     ? (p.min_value ?? null) : null,
          max_value:                p.parameter_type === "Numeric"     ? (p.max_value ?? null) : null,
          acceptance_criteria_value: p.parameter_type === "Non-Numeric" ? p.acceptance_criteria_value : null,
          formula:                  p.parameter_type === "Formula"     ? p.formula : null,
        })),
      },
    });
    toast.success(`Template "${editForm.template_name}" updated`);
    editOpen.value = false;
    await load();
  } catch (e) {
    toast.error(e.message || "Failed to update template");
  } finally {
    editSaving.value = false;
  }
}

function exportCSV() {
  if (!filtered.value.length) return;
  const esc = v => { const s = v == null ? "" : String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  const hdr = ["Template Name", "Item", "Item Group", "Inspection Type", "Parameters", "Description"];
  const lines = [hdr.join(",")];
  for (const t of sorted.value) {
    lines.push([
      t.template_name, t.item || "", t.item_group || "",
      t.inspection_type || "All", t.parameter_count || 0, t.description || "",
    ].map(esc).join(","));
  }
  const blob = new Blob(["\uFEFF" + lines.join("\r\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `qc_templates_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click(); URL.revokeObjectURL(url);
  toast.success(`Exported ${sorted.value.length} template(s)`);
}

onMounted(load);
</script>

<style scoped>
.qct-page { display:flex; flex-direction:column; gap:14px; padding:24px; min-width:0; }

/* Header bar */
.qct-header-bar { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px; }
.qct-header-left { display:flex; align-items:center; gap:12px; }
.qct-header-ico { width:44px; height:44px; border-radius:12px; background:linear-gradient(135deg,#1e3a5f,#2563eb); display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.qct-header-title { font-size:18px; font-weight:700; color:#0f172a; }
.qct-header-sub { font-size:12px; color:#6b7280; margin-top:1px; }
.qct-header-right { display:flex; align-items:center; gap:8px; }

/* Stats */
.qct-stats-strip { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; }
.qct-stat { background:#fff; border:1px solid #e5e7eb; border-radius:10px; padding:12px 14px; display:flex; align-items:center; gap:12px; }
.qct-stat-ico { width:36px; height:36px; border-radius:9px; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.qct-stat-lbl { font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.05em; color:#9ca3af; }
.qct-stat-val { font-size:20px; font-weight:700; color:#0f172a; line-height:1.2; }

/* Filter */
.qct-filter-bar { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.qct-search-wrap { display:flex; align-items:center; gap:8px; background:#fff; border:1px solid #e5e7eb; border-radius:8px; padding:6px 12px; min-width:0; flex:1; width:100%; }
.qct-search-input { border:none; background:transparent; outline:none; font:inherit; color:#111827; width:100%; font-size:13px; }
.qct-select { border:1px solid #e5e7eb; border-radius:6px; padding:6px 10px; font:inherit; font-size:12px; color:#374151; background:#fff; outline:none; cursor:pointer; }

/* Buttons */
.qct-btn-primary { display:inline-flex; align-items:center; gap:6px; background:#2563eb; color:#fff; border:none; border-radius:8px; padding:8px 14px; font-size:13px; font-weight:600; cursor:pointer; font-family:inherit; transition:background .15s; }
.qct-btn-primary:hover { background:#1d4ed8; } .qct-btn-primary:disabled { opacity:.5; cursor:not-allowed; }
.qct-btn-ghost { display:inline-flex; align-items:center; gap:6px; background:#fff; border:1px solid #e5e7eb; border-radius:8px; padding:8px 12px; font-size:13px; color:#374151; cursor:pointer; font-family:inherit; }
.qct-btn-ghost:hover { background:#f9fafb; }
.qct-btn-edit { display:inline-flex; align-items:center; gap:6px; background:#fffbeb; border:1px solid #f59e0b; color:#b45309; border-radius:8px; padding:8px 14px; font-size:13px; font-weight:600; cursor:pointer; font-family:inherit; }
.qct-btn-edit:hover { background:#fef3c7; }

/* Table */
.qct-card { background:#fff; border:1px solid #e5e7eb; border-radius:10px; overflow:hidden; overflow-x:auto; }
.qct-table { width:100%; border-collapse:collapse; font-size:13px; }
.qct-table th { background:#f9fafb; padding:10px 12px; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:#6b7280; text-align:left; border-bottom:1px solid #e5e7eb; white-space:nowrap; }
.qct-table td { padding:10px 12px; border-bottom:1px solid #f3f4f6; vertical-align:middle; }
.qct-row { cursor:pointer; transition:background .12s; }
.qct-row:hover { background:#f8fafc; }
.qct-tpl-ico { width:28px; height:28px; border-radius:6px; background:#eff6ff; color:#2563eb; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.qct-tpl-name { font-weight:600; font-size:13px; color:#0f172a; }
.qct-item-badge { font-size:11px; font-weight:600; background:#eff6ff; color:#2563eb; padding:2px 8px; border-radius:10px; border:1px solid #bfdbfe; }
.qct-generic-badge { font-size:11px; font-weight:600; background:#f3f4f6; color:#6b7280; padding:2px 8px; border-radius:10px; }
.qct-type-badge { font-size:11px; font-weight:700; padding:3px 9px; border-radius:20px; }
.qct-type-mini { font-size:10px; font-weight:600; padding:2px 7px; border-radius:10px; }
.qct-param-count { font-size:13px; font-weight:700; color:#2563eb; background:#eff6ff; padding:2px 8px; border-radius:8px; }
.sortable { cursor:pointer; }
.ta-r { text-align:right; }
.ta-c { text-align:center; }
.qct-act-btn { background:none; border:1px solid #e5e7eb; border-radius:6px; padding:5px 7px; cursor:pointer; color:#6b7280; display:inline-flex; align-items:center; }
.qct-act-btn:hover { background:#f3f4f6; }
.qct-act-del { color:#dc2626; border-color:#fca5a5; }
.qct-act-del:hover { background:#fef2f2; }
.qct-empty { text-align:center; padding:48px 0; color:#6b7280; }
.qct-shimmer { height:32px; background:linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size:200%; animation:shimmer 1.4s infinite; border-radius:4px; }
@keyframes shimmer { 0%{background-position:200%} 100%{background-position:-200%} }

/* Pagination */
.qct-pg-btn { background:#fff; border:1px solid #e5e7eb; border-radius:6px; padding:4px 8px; cursor:pointer; font-size:13px; }
.qct-pg-btn:disabled { opacity:.4; cursor:not-allowed; }

/* Drawer */
.qct-overlay { position:fixed; inset:0; background:rgba(0,0,0,.35); z-index:998; }
.qct-drawer { position:fixed; right:0; top:0; bottom:0; width:560px; background:#fff; z-index:999; display:flex; flex-direction:column; transform:translateX(100%); transition:transform .25s cubic-bezier(.4,0,.2,1); box-shadow:-4px 0 24px rgba(0,0,0,.12); }
.qct-drawer.open { transform:translateX(0); }
.qct-view-drawer { width:620px; }
.qct-dheader { padding:20px 20px 16px; background:linear-gradient(135deg,#1e3a5f,#2563eb); position:relative; flex-shrink:0; }
.qct-dh-top { display:flex; align-items:center; gap:12px; }
.qct-dh-ico { width:40px; height:40px; border-radius:10px; background:rgba(255,255,255,.2); display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.qct-dh-title { font-size:16px; font-weight:700; color:#fff; }
.qct-dh-sub { font-size:12px; color:rgba(255,255,255,.75); margin-top:2px; }
.qct-dclose { position:absolute; top:14px; right:14px; background:rgba(255,255,255,.15); border:none; border-radius:8px; padding:6px; cursor:pointer; color:#fff; display:flex; align-items:center; }
.qct-dclose:hover { background:rgba(255,255,255,.25); }
.qct-dbody { flex:1; overflow-y:auto; padding:18px 20px; display:flex; flex-direction:column; gap:14px; width:100%; box-sizing:border-box; }
.qct-dfooter { padding:14px 20px; border-top:1px solid #e5e7eb; display:flex; gap:8px; justify-content:flex-end; flex-shrink:0; }

/* Create form */
.qct-section-lbl { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; color:#9ca3af; display:flex; align-items:center; gap:8px; }
.qct-fields-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; min-width:0; }
.qct-field { display:flex; flex-direction:column; gap:4px; min-width:0; }
.qct-label { font-size:12px; font-weight:600; color:#374151; }
.req { color:#ef4444; }
.qct-input { border:1px solid #e5e7eb; border-radius:8px; padding:8px 10px; font:inherit; font-size:13px; outline:none; color:#111827; transition:border-color .15s; width:100%; box-sizing:border-box; }
.qct-input:focus { border-color:#2563eb; box-shadow:0 0 0 3px rgba(37,99,235,.08); }
.qct-input-sm { padding:6px 8px; font-size:12.5px; }
.qct-select-full { border:1px solid #e5e7eb; border-radius:8px; padding:8px 10px; font:inherit; font-size:13px; outline:none; color:#111827; background:#fff; width:100%; box-sizing:border-box; }
.qct-select-full:focus { border-color:#2563eb; }

/* Parameter cards */
.qct-add-param-btn { margin-left:auto; display:inline-flex; align-items:center; gap:4px; background:#eff6ff; color:#2563eb; border:1px solid #bfdbfe; border-radius:6px; padding:3px 9px; font-size:11.5px; font-weight:600; cursor:pointer; font-family:inherit; }
.qct-add-param-btn:hover { background:#dbeafe; }
.qct-param-empty { text-align:center; padding:20px; color:#9ca3af; font-size:12.5px; background:#f9fafb; border-radius:8px; border:1px dashed #e5e7eb; }
/* NOTE: NO overflow:hidden on param-card — that clips the inputs! */
.qct-param-card { border:1px solid #e5e7eb; border-radius:10px; width:100%; box-sizing:border-box; background:#fff; }
.qct-param-header { background:#f9fafb; padding:10px 12px; display:flex; align-items:center; gap:8px; border-bottom:1px solid #e5e7eb; border-top-left-radius:9px; border-top-right-radius:9px; }
.qct-param-num { width:22px; height:22px; border-radius:50%; background:#2563eb; color:#fff; font-size:10.5px; font-weight:700; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.qct-param-del { margin-left:auto; flex-shrink:0; background:none; border:none; cursor:pointer; color:#9ca3af; padding:4px; display:flex; align-items:center; border-radius:4px; }
.qct-param-del:hover { color:#dc2626; background:#fee2e2; }
.qct-param-fields { padding:12px; display:grid; grid-template-columns:1fr 1fr; gap:10px; width:100%; box-sizing:border-box; }

/* View sections */
.qct-summary-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:10px; background:#f8fafc; border-radius:8px; padding:12px 14px; border:1px solid #e5e7eb; }
.qct-sum-item { display:flex; flex-direction:column; gap:2px; }
.qct-sum-lbl { font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:#9ca3af; }
.qct-sum-val { font-size:13px; font-weight:600; color:#0f172a; }
.qct-view-sec-lbl { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:#9ca3af; margin-bottom:6px; }
.qct-params-tbl { width:100%; border-collapse:collapse; font-size:13px; border:1px solid #e5e7eb; border-radius:8px; overflow:hidden; }
.qct-params-tbl th { background:#f9fafb; padding:8px 12px; font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:#6b7280; text-align:left; border-bottom:1px solid #e5e7eb; }
.qct-params-tbl td { padding:10px 12px; border-bottom:1px solid #f3f4f6; vertical-align:middle; }
.qct-params-tbl tr:last-child td { border-bottom:none; }

/* ── Mobile card list: hidden by default, shown ≤425px ── */
.qct-mobile-list { display:none; }

/* ── Responsive: tablet (≤768px) ── */
@media (max-width: 768px) {
  .qct-stats-strip { grid-template-columns:repeat(2,1fr); }
  .qct-drawer,.qct-view-drawer { width:100%; }
  /* Only collapse the basic form fields grid, NOT param-fields (drawer is fixed 560px) */
  .qct-fields-grid { grid-template-columns:1fr; }
  .qct-page { padding:12px; }
  .qct-filter-bar { flex-direction:column; align-items:stretch; }
  .qct-header-bar { gap:8px; }
}

/* ── Responsive: 480px — covers 425px + 375px mobile ── */
@media (max-width: 480px) {
  .qct-page { padding:10px 8px; gap:10px; }

  /* hide desktop table, show cards */
  .qct-table-wrap { display:none; }
  .qct-mobile-list { display:flex; flex-direction:column; gap:10px; }

  /* shimmer */
  .qct-mobile-shimmer { height:120px; border-radius:12px; background:linear-gradient(90deg,#f3f4f6 25%,#e9ecef 50%,#f3f4f6 75%); background-size:200%; animation:shimmer 1.4s infinite; }

  /* empty */
  .qct-mobile-empty { text-align:center; padding:40px 16px; background:#fff; border:1px solid #e5e7eb; border-radius:12px; color:#6b7280; }

  /* card */
  .qct-mob-card { background:#fff; border:1px solid #e5e7eb; border-radius:12px; padding:12px 14px; display:flex; flex-direction:column; gap:8px; cursor:pointer; transition:box-shadow .15s,transform .12s; }
  .qct-mob-card:active { box-shadow:0 4px 16px rgba(0,0,0,.08); transform:scale(.99); }

  /* top: name + param count */
  .qct-mob-top { display:flex; align-items:center; justify-content:space-between; gap:8px; }
  .qct-mob-ico { width:26px; height:26px; border-radius:6px; background:#eff6ff; color:#2563eb; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
  .qct-mob-name { font-weight:700; font-size:13px; color:#0f172a; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }

  /* badges row */
  .qct-mob-badges { display:flex; flex-wrap:wrap; gap:5px; align-items:center; }
  .qct-mob-group { font-size:11px; font-weight:600; background:#f3f4f6; color:#6b7280; padding:2px 7px; border-radius:10px; }

  /* parameters count row */
  .qct-mob-params-row { display:flex; align-items:center; justify-content:space-between; background:#f8fafc; border:1px solid #e5e7eb; border-radius:7px; padding:6px 10px; }
  .qct-mob-params-lbl { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:#9ca3af; }

  /* description */
  .qct-mob-desc { font-size:12px; color:#6b7280; line-height:1.4; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }

  /* footer */
  .qct-mob-footer { display:flex; align-items:center; justify-content:space-between; padding-top:6px; border-top:1px solid #f3f4f6; margin-top:2px; }
  .qct-mob-footer-hint { font-size:11px; color:#9ca3af; }

  /* Header */
  .qct-header-bar { flex-direction:column; align-items:flex-start; gap:10px; }
  .qct-header-right { width:100%; justify-content:flex-end; }
  .qct-header-ico { width:36px; height:36px; border-radius:10px; }
  .qct-header-title { font-size:16px; }
  .qct-header-sub { font-size:11px; }
  .qct-btn-ghost { padding:7px 10px; font-size:12px; }
  .qct-btn-primary { padding:8px 12px; font-size:12.5px; }

  /* Stats */
  .qct-stats-strip { grid-template-columns:1fr 1fr; gap:8px; }
  .qct-stat { padding:10px 10px; gap:8px; }
  .qct-stat-ico { width:30px; height:30px; border-radius:7px; flex-shrink:0; }
  .qct-stat-lbl { font-size:9.5px; letter-spacing:0; }
  .qct-stat-val { font-size:17px; }

  /* Filter */
  .qct-filter-bar { flex-direction:column; align-items:stretch; gap:8px; }
  .qct-search-wrap { min-width:0; width:100%; }
  .qct-search-input { font-size:12.5px; }
  .qct-select { width:100%; font-size:12px; padding:6px 8px; }

  /* Drawer */
  .qct-drawer,.qct-view-drawer { width:100%; }
  .qct-dheader { padding:16px 14px 12px; }
  .qct-dh-title { font-size:14px; }
  .qct-dh-sub { font-size:11px; }
  .qct-dbody { padding:14px; gap:12px; }
  .qct-dfooter { padding:12px 14px; }
  .qct-dbody { padding:12px 14px; gap:10px; }
  /* On mobile, collapse both grids to single column */
  .qct-fields-grid,.qct-param-fields { grid-template-columns:1fr; gap:8px; }
  .qct-summary-grid { grid-template-columns:1fr 1fr; }
  .qct-params-tbl { font-size:12px; }
  .qct-params-tbl th { padding:7px 8px; font-size:10px; }
  .qct-params-tbl td { padding:8px 8px; }
}

/* ── Responsive: 375px ── */
@media (max-width: 375px) {
  .qct-page { padding:8px 6px; gap:8px; }

  /* cards: tighter */
  .qct-mob-card { padding:10px 12px; gap:6px; border-radius:10px; }
  .qct-mob-name { font-size:12.5px; }
  .qct-mob-desc { font-size:11.5px; }
  .qct-mobile-shimmer { height:108px; }

  /* Header */
  .qct-header-ico { width:32px; height:32px; border-radius:8px; }
  .qct-header-title { font-size:14px; }
  .qct-header-sub { display:none; }
  .qct-btn-ghost { padding:6px 8px; font-size:11.5px; }
  .qct-btn-primary { padding:7px 10px; font-size:12px; }

  /* Stats */
  .qct-stat { padding:8px 8px; gap:7px; }
  .qct-stat-ico { width:26px; height:26px; border-radius:6px; }
  .qct-stat-lbl { font-size:9px; }
  .qct-stat-val { font-size:15px; }

  /* Filter */
  .qct-search-input { font-size:12px; }
  .qct-select { font-size:11.5px; }

  /* Drawer */
  .qct-dheader { padding:12px 12px 10px; }
  .qct-dh-title { font-size:13px; }
  .qct-dbody { padding:12px; }
  .qct-dfooter { padding:10px 12px; }
  .qct-summary-grid { grid-template-columns:1fr; }
  .qct-params-tbl { font-size:11.5px; }
}
</style>
