<template>
<div class="b-page">

  <!-- Company context banner -->
  <div v-if="currentCompany" style="display:flex;align-items:center;gap:8px;margin-bottom:10px;padding:8px 14px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;font-size:12.5px;color:#1d4ed8">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 21h18"/><rect x="9" y="10" width="6" height="11"/><path d="M5 21V7l7-4 7 4v14"/></svg>
    <span>Showing fiscal years for <strong>{{ currentCompany }}</strong></span>
  </div>

  <div class="fy-stats-grid" style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px">
    <div class="b-card fy-kpi-card">
      <div class="fy-kpi-lbl">Total Years</div>
      <div class="fy-kpi-val">{{stats.total}}</div>
    </div>
    <div class="b-card fy-kpi-card fy-kpi-card--green">
      <div class="fy-kpi-lbl" style="color:#2F9E44">Current Year</div>
      <div class="fy-kpi-val fy-kpi-val--sm" style="color:#2F9E44">{{stats.currentName}}</div>
    </div>
    <div class="b-card fy-kpi-card fy-kpi-card--blue">
      <div class="fy-kpi-lbl" style="color:#3B5BDB">Days Elapsed</div>
      <div class="fy-kpi-val" style="color:#3B5BDB">{{stats.elapsed}}</div>
    </div>
    <div class="b-card fy-kpi-card fy-kpi-card--orange">
      <div class="fy-kpi-lbl" style="color:#E67700">Periods Locked</div>
      <div class="fy-kpi-val" style="color:#E67700">{{stats.locked}}</div>
    </div>
    <div class="b-card fy-kpi-card" :class="stats.needsClosing?'fy-kpi-card--red':''">
      <div class="fy-kpi-lbl" :style="{color:stats.needsClosing?'#C92A2A':'#868E96'}">Needs Closing</div>
      <div class="fy-kpi-val" :style="{color:stats.needsClosing?'#C92A2A':'#1A1D23'}">{{stats.needsClosing}}</div>
    </div>
  </div>

  <div class="b-card fy-lock-card" style="padding:14px 18px;display:flex;align-items:center;gap:14px;flex-wrap:wrap" :style="{borderLeft: lockDate ? '3px solid #C92A2A' : '3px solid #E2E8F0'}">
    <span v-html="icon('lock',16)" :style="{color: lockDate ? '#C92A2A' : '#868E96'}"></span>
    <div>
      <div style="font-size:13px;font-weight:700;color:#1A1D23">Books Lock Date</div>
      <div style="font-size:11.5px;color:#868E96">Freezes every financial transaction dated on or before this date. Only a System Manager can post past it.</div>
    </div>
    <div style="margin-left:auto;display:flex;align-items:center;gap:8px;flex-wrap:wrap">
      <span v-if="lockDate" style="font-size:12px;color:#C92A2A;font-weight:700">Locked up to {{ fmtLock(lockDate) }}</span>
      <span v-else style="font-size:12px;color:#868E96;font-weight:600">No lock set</span>
      <input v-model="lockDateInput" type="date" :disabled="!$canEdit('accounts')" style="border:1px solid #E2E8F0;border-radius:7px;padding:6px 10px;font:inherit;font-size:13px;outline:none"/>
      <button class="b-btn b-btn-primary" @click="saveLockDate" :disabled="lockSaving || !lockDateInput || !$canEdit('accounts')" :title="!$canEdit('accounts') ? 'Read-only access' : ''">{{ lockSaving ? 'Saving…' : (lockDate ? 'Update' : 'Lock') }}</button>
      <button v-if="lockDate" class="b-btn b-btn-ghost" @click="clearLockDate" :disabled="lockSaving || !$canEdit('accounts')" :title="!$canEdit('accounts') ? 'Read-only access' : ''">Clear</button>
    </div>
  </div>

  <!-- Load error banner -->
  <div v-if="loadError" style="padding:10px 16px;background:#FFF5F5;border:1px solid #FFD8D8;border-radius:8px;font-size:13px;color:#C92A2A;display:flex;align-items:center;gap:8px">
    <span>⚠</span><span>{{loadError}}</span>
    <button class="b-btn b-btn-ghost" style="margin-left:auto;font-size:12px" @click="load">Retry</button>
  </div>

  <div class="fy-main-layout" style="display:grid;grid-template-columns:380px 1fr;gap:20px;align-items:start">

    <div class="fy-left-panel" :class="{'fy-left-panel--hidden': selectedYear}" style="display:flex;flex-direction:column;gap:12px">
      <div v-if="loading" class="b-card" style="padding:40px;text-align:center;color:#868E96">Loading fiscal years…</div>
      <template v-else>
        <div v-for="y in allYears" :key="y.name"
          style="background:#fff;border:1.5px solid #E2E8F0;border-radius:10px;padding:18px 20px;cursor:pointer;transition:all .15s;position:relative;overflow:hidden"
          :style="{borderColor:selectedYear===y.name?'#3B5BDB':isCurrent(y.start,y.end)?'#2F9E44':'#E2E8F0',background:selectedYear===y.name?'#F5F8FF':'#fff'}"
          @click="selectYear(y.name)">
          <div v-if="y.is_closed"
            style="position:absolute;top:0;right:0;background:#868E96;color:#fff;font-size:10px;font-weight:700;padding:3px 10px;border-radius:0 10px 0 6px;letter-spacing:.5px">CLOSED</div>
          <div v-else-if="isCurrent(y.start,y.end)"
            style="position:absolute;top:0;right:0;background:#2F9E44;color:#fff;font-size:10px;font-weight:700;padding:3px 10px;border-radius:0 10px 0 6px;letter-spacing:.5px">CURRENT</div>

          <div style="font-size:15px;font-weight:700;margin-bottom:3px;padding-right:70px">{{y.year_label || y.name}}</div>
          <div style="font-size:12px;color:#868E96;margin-bottom:10px;">{{fmtDate(y.start)}} → {{fmtDate(y.end)}}</div>

          <template v-if="isCurrent(y.start,y.end)">
            <div style="margin-bottom:10px">
              <div style="display:flex;justify-content:space-between;font-size:11px;color:#868E96;margin-bottom:4px">
                <span>Year progress</span>
                <span style="font-weight:700;color:#3B5BDB">{{Math.round(daysElapsed(y.start,y.end)/Math.max(1,daysBetween(y.start,y.end))*100)}}%</span>
              </div>
              <div style="background:#E8ECF0;border-radius:20px;height:7px;overflow:hidden">
                <div style="height:100%;border-radius:20px;background:linear-gradient(90deg,#3B5BDB,#6495f7);transition:width .4s ease"
                  :style="{width:Math.round(daysElapsed(y.start,y.end)/Math.max(1,daysBetween(y.start,y.end))*100)+'%'}"></div>
              </div>
            </div>
          </template>

          <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px">
            <span style="font-size:11px;padding:2px 8px;border-radius:20px;font-weight:500;background:#F8F9FC;color:#868E96">{{y.period_type}}</span>
            <span v-if="(y.periods||[]).filter(p=>p.locked).length" style="font-size:11px;padding:2px 8px;border-radius:20px;font-weight:500;background:#FFF5F5;color:#C92A2A">{{(y.periods||[]).filter(p=>p.locked).length}} locked</span>
            <span v-if="y.is_default" style="font-size:11px;padding:2px 8px;border-radius:20px;font-weight:500;background:#EBFBEE;color:#2F9E44">Default</span>
            <span v-if="isPast(y.end)&&!y.is_closed" style="font-size:11px;padding:2px 8px;border-radius:20px;font-weight:500;background:#FFF3BF;color:#E67700">⚠ Needs closing</span>
          </div>

          <div v-if="(y.periods||[]).length" style="display:grid;grid-template-columns:repeat(12,1fr);gap:2px">
            <div v-for="(p,i) in (y.periods||[]).slice(0,12)" :key="i"
              style="height:5px;border-radius:2px"
              :style="{background:p.locked?'#CED4DA':p.is_current?'#3B5BDB':p.is_past?'#A5D8FF':'#DEE2E6'}"
              :title="p.name+(p.locked?' · Locked':p.is_current?' · Current':p.is_past?' · Past':' · Future')"></div>
          </div>
        </div>

        <div v-if="!allYears.length && !loadError" style="padding:28px;text-align:center;color:#868E96;font-size:13px">
          No fiscal years found for this company.
        </div>

        <button class="b-btn b-btn-ghost" :disabled="!$canCreate('accounts')" :title="!$canCreate('accounts') ? 'Read-only access' : ''" @click="openAdd" style="width:100%;justify-content:center">
          <span v-html="icon('plus',13)"></span>Add Fiscal Year
        </button>
      </template>
    </div>

    <div class="fy-right-panel" :class="{'fy-right-panel--visible': selectedYear}">

      <!-- Mobile back button -->
      <div class="fy-mobile-back">
        <button @click="selectedYear=null" class="fy-back-btn">
          <span style="font-size:16px;line-height:1">&#8592;</span>
          Back to years
        </button>
      </div>

      <div v-if="!selectedYearData" class="b-card" style="padding:48px;text-align:center;color:#868E96">
        <div style="font-size:40px;margin-bottom:14px">📅</div>
        <div style="font-weight:600;font-size:15px;color:#1A1D23;margin-bottom:6px">Select a fiscal year</div>
        <div style="font-size:13px;line-height:1.6">Click any year on the left to view and manage its accounting periods, lock past periods, and run year-end close.</div>
        <button class="b-btn b-btn-primary" :disabled="!$canCreate('accounts')" :title="!$canCreate('accounts') ? 'Read-only access' : ''" @click="openAdd" style="margin-top:18px">+ Add First Fiscal Year</button>
      </div>

      <template v-else>
        <div class="b-card" style="padding:0;overflow:hidden;margin-bottom:14px">
          <div style="padding:16px 20px;border-bottom:1px solid #E2E8F0;display:flex;align-items:center;justify-content:space-between;background:#F8F9FC">
            <div>
              <div style="font-size:16px;font-weight:700">{{selectedYearData.year_label || selectedYearData.name}}</div>
              <div style="font-size:12px;color:#868E96;margin-top:2px;">
                {{fmtDate(selectedYearData.start)}} → {{fmtDate(selectedYearData.end)}}
                &nbsp;·&nbsp;{{daysBetween(selectedYearData.start,selectedYearData.end)}} days
                &nbsp;·&nbsp;{{(selectedYearData.periods||[]).length}} periods
              </div>
            </div>
            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
              <span v-if="isCurrent(selectedYearData.start,selectedYearData.end)"
                style="display:inline-flex;align-items:center;padding:2px 9px;border-radius:20px;font-size:11px;font-weight:600;background:#EBFBEE;color:#2F9E44">● Current</span>
              <span v-if="selectedYearData.is_closed"
                style="display:inline-flex;align-items:center;padding:2px 9px;border-radius:20px;font-size:11px;font-weight:600;background:#F1F3F5;color:#868E96">Closed</span>
              <button v-if="isPast(selectedYearData.end)&&!selectedYearData.is_closed"
                class="b-btn b-btn-ghost" style="border-color:#C92A2A;color:#C92A2A;font-size:12px;padding:5px 11px"
                :disabled="!$canEdit('accounts')" :title="!$canEdit('accounts') ? 'Read-only access' : ''"
                @click="openCloseYear(selectedYearData.name)">🔒 Close Year</button>
              <button class="b-btn b-btn-ghost" style="font-size:12px;padding:5px 11px"
                :disabled="!$canEdit('accounts')" :title="!$canEdit('accounts') ? 'Read-only access' : ''"
                @click="openEdit(selectedYearData.name)">Edit</button>
            </div>
          </div>

          <div v-if="isCurrent(selectedYearData.start,selectedYearData.end)"
            style="padding:14px 20px;border-bottom:1px solid #E2E8F0;background:#fff">
            <div style="display:flex;justify-content:space-between;font-size:12px;color:#868E96;margin-bottom:6px">
              <span>Year progress — {{daysElapsed(selectedYearData.start,selectedYearData.end)}} of {{daysBetween(selectedYearData.start,selectedYearData.end)}} days elapsed</span>
              <span style="font-weight:700;color:#3B5BDB">{{Math.round(daysElapsed(selectedYearData.start,selectedYearData.end)/Math.max(1,daysBetween(selectedYearData.start,selectedYearData.end))*100)}}%</span>
            </div>
            <div style="background:#E8ECF0;border-radius:20px;height:10px;overflow:hidden">
              <div style="height:100%;border-radius:20px;background:linear-gradient(90deg,#3B5BDB,#6495f7);transition:width .4s"
                :style="{width:Math.round(daysElapsed(selectedYearData.start,selectedYearData.end)/Math.max(1,daysBetween(selectedYearData.start,selectedYearData.end))*100)+'%'}"></div>
            </div>
          </div>

          <!-- Desktop periods table (hidden on mobile) -->
          <div class="fy-desktop-periods">
            <div style="display:grid;grid-template-columns:1fr 140px 110px 90px;gap:0;padding:8px 16px;background:#F8F9FC;border-bottom:1px solid #E2E8F0;font-size:10.5px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;color:#868E96">
              <span>Period</span><span>Date Range</span><span>Status</span><span style="text-align:center">Action</span>
            </div>
            <div v-for="(p,i) in (selectedYearData.periods||[])" :key="i"
              style="display:grid;grid-template-columns:1fr 140px 110px 90px;align-items:center;gap:0;padding:9px 16px;border-bottom:1px solid #F1F3F5;font-size:13px;transition:background .12s"
              :style="{background:p.locked?'#FFF5F5':p.is_current?'#EEF2FF':'#fff'}">
              <div>
                <span :style="{fontWeight:p.is_current?'700':'400',color:p.is_current?'#1A1D23':'#344054'}">{{p.name}}</span>
                <span v-if="p.is_current" style="margin-left:6px;font-size:10px;background:#EEF2FF;color:#3B5BDB;padding:1px 6px;border-radius:10px;font-weight:600">NOW</span>
              </div>
              <div style="font-size:11.5px;color:#868E96;">{{fmtShort(p.start)}} – {{fmtShort(p.end)}}</div>
              <div>
                <span v-if="p.locked" style="font-size:11px;padding:2px 8px;border-radius:20px;font-weight:600;background:#FFE3E3;color:#C92A2A">🔒 Locked</span>
                <span v-else-if="p.is_current" style="font-size:11px;padding:2px 8px;border-radius:20px;font-weight:600;background:#EEF2FF;color:#3B5BDB">Open</span>
                <span v-else-if="p.is_past" style="font-size:11px;padding:2px 8px;border-radius:20px;font-weight:600;background:#F8F9FA;color:#868E96">Past</span>
                <span v-else style="font-size:11px;padding:2px 8px;border-radius:20px;font-weight:600;background:#F8F9FA;color:#ADB5BD">Future</span>
              </div>
              <div style="text-align:center">
                <button v-if="!p.is_current"
                  style="background:none;border:1px solid;border-radius:5px;cursor:pointer;padding:3px 8px;font-size:11px;font-family:inherit;transition:all .15s"
                  :style="{borderColor:p.locked?'#C92A2A':'#CED4DA',color:p.locked?'#C92A2A':'#868E96',background:p.locked?'#FFF5F5':'#fff'}"
                  :disabled="!$canEdit('accounts')" :title="!$canEdit('accounts') ? 'Read-only access' : ''"
                  @click="togglePeriodLock(selectedYearData.name,i)">
                  {{p.locked?"Unlock":"Lock"}}
                </button>
                <span v-else style="color:#CED4DA;font-size:12px">—</span>
              </div>
            </div>
          </div><!-- end .fy-desktop-periods -->

          <!-- Mobile period cards (shown only at 375–425px) -->
          <div class="fy-mobile-periods">
            <div v-for="(p,i) in (selectedYearData.periods||[])" :key="'mc'+i"
              class="fy-period-card"
              :class="p.locked?'fy-pc--locked':p.is_current?'fy-pc--current':p.is_past?'fy-pc--past':'fy-pc--future'"
              :style="{background:p.locked?'#FFF5F5':p.is_current?'#EEF2FF':'#fff'}">
              <div class="fy-pc-top">
                <div class="fy-pc-name">
                  <span :style="{fontWeight:p.is_current?700:500,color:p.is_current?'#1A1D23':'#344054'}">{{p.name}}</span>
                  <span v-if="p.is_current" style="margin-left:6px;font-size:10px;background:#EEF2FF;color:#3B5BDB;padding:1px 6px;border-radius:10px;font-weight:600">NOW</span>
                </div>
                <div class="fy-pc-status">
                  <span v-if="p.locked" style="font-size:11px;padding:2px 8px;border-radius:20px;font-weight:600;background:#FFE3E3;color:#C92A2A">🔒 Locked</span>
                  <span v-else-if="p.is_current" style="font-size:11px;padding:2px 8px;border-radius:20px;font-weight:600;background:#EEF2FF;color:#3B5BDB">Open</span>
                  <span v-else-if="p.is_past" style="font-size:11px;padding:2px 8px;border-radius:20px;font-weight:600;background:#F8F9FA;color:#868E96">Past</span>
                  <span v-else style="font-size:11px;padding:2px 8px;border-radius:20px;font-weight:600;background:#F8F9FA;color:#ADB5BD">Future</span>
                </div>
              </div>
              <div class="fy-pc-bottom">
                <span class="fy-pc-date">{{fmtShort(p.start)}} – {{fmtShort(p.end)}}</span>
                <button v-if="!p.is_current"
                  class="fy-pc-lock-btn"
                  :class="{' fy-pc-lock-btn--locked':p.locked}"
                  :disabled="!$canEdit('accounts')" :title="!$canEdit('accounts') ? 'Read-only access' : ''"
                  @click="togglePeriodLock(selectedYearData.name,i)">
                  {{p.locked?"Unlock":"Lock"}}
                </button>
                <span v-else style="color:#CED4DA;font-size:12px">—</span>
              </div>
            </div>
          </div><!-- end .fy-mobile-periods -->

          <div style="padding:10px 16px;background:#F8F9FC;border-top:1px solid #E2E8F0;display:flex;justify-content:space-between;align-items:center">
            <span style="font-size:12px;color:#868E96">
              {{(selectedYearData.periods||[]).filter(p=>p.locked).length}} of {{(selectedYearData.periods||[]).length}} periods locked
            </span>
            <div style="display:flex;gap:8px">
              <button class="b-btn b-btn-ghost" style="font-size:12px;padding:5px 10px" :disabled="!$canEdit('accounts')" :title="!$canEdit('accounts') ? 'Read-only access' : ''" @click="lockAllPeriods(selectedYearData.name,true)">Lock All Past</button>
              <button class="b-btn b-btn-ghost" style="font-size:12px;padding:5px 10px" :disabled="!$canEdit('accounts')" :title="!$canEdit('accounts') ? 'Read-only access' : ''" @click="lockAllPeriods(selectedYearData.name,false)">Unlock All</button>
            </div>
          </div>
        </div>

        <div class="b-card" style="padding:0;overflow:hidden">
          <div style="padding:13px 20px;border-bottom:1px solid #E2E8F0;font-size:13px;font-weight:600;color:#1A1D23">Year-End Configuration</div>
          <div style="padding:16px 20px;display:grid;grid-template-columns:1fr 1fr;gap:14px;font-size:13px">
            <div><div style="font-size:11px;color:#868E96;margin-bottom:3px;text-transform:uppercase;letter-spacing:.4px">Closing Account</div><div style="font-weight:600">{{selectedYearData.closing_acct||"Retained Earnings"}}</div></div>
            <div><div style="font-size:11px;color:#868E96;margin-bottom:3px;text-transform:uppercase;letter-spacing:.4px">Period Type</div><div style="font-weight:600">{{selectedYearData.period_type||"Monthly"}}</div></div>
            <div><div style="font-size:11px;color:#868E96;margin-bottom:3px;text-transform:uppercase;letter-spacing:.4px">Auto-close on End</div><div style="font-weight:600">{{selectedYearData.auto_close?"Yes":"No"}}</div></div>
            <div><div style="font-size:11px;color:#868E96;margin-bottom:3px;text-transform:uppercase;letter-spacing:.4px">Default Year</div><div style="font-weight:600">{{selectedYearData.is_default?"Yes":"No"}}</div></div>
          </div>
        </div>
      </template>
    </div>
  </div>

  <Teleport to="body">
    <div v-if="showDrawer" style="position:fixed;inset:0;z-index:9000;background:rgba(15,23,42,.45);display:flex;justify-content:flex-end;backdrop-filter:blur(2px)" @click.self="closeDrawer">
      <div style="width:480px;max-width:95vw;height:100%;background:#fff;display:flex;flex-direction:column;box-shadow:-20px 0 60px rgba(0,0,0,.15)">
        <div style="background:linear-gradient(135deg,#2563eb,#4f46e5);padding:18px 24px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0">
          <div>
            <div style="color:#fff;font-size:16px;font-weight:700">{{editingName?"Edit Fiscal Year":"New Fiscal Year"}}</div>
            <div style="color:rgba(255,255,255,.75);font-size:12px;margin-top:2px;">
              {{editingName?"Update dates, periods and year-end settings":"Define the year range and accounting periods"}}
            </div>
          </div>
          <button @click="closeDrawer" style="background:rgba(255,255,255,.15);border:none;cursor:pointer;width:30px;height:30px;border-radius:8px;color:#fff;display:grid;place-items:center">
            <span v-html="icon('x',16)"></span>
          </button>
        </div>

        <div v-if="drawerError" style="background:#FFF5F5;border-bottom:1px solid #FFD8D8;padding:10px 24px;font-size:12.5px;color:#C92A2A;display:flex;align-items:center;gap:8px;flex-shrink:0">
          <span>⚠</span><span>{{drawerError}}</span>
        </div>

        <div style="flex:1;overflow-y:auto;padding:24px">
          <div style="background:#EEF2FF;border:1px solid rgba(59,91,219,.15);border-radius:8px;padding:11px 14px;font-size:12.5px;color:#2f4ec4;line-height:1.6;margin-bottom:20px">
            📌 India standard: <strong>1 April → 31 March</strong>. Other year-ends require MCA approval.
          </div>

          <div style="font-size:10.5px;font-weight:700;letter-spacing:.7px;text-transform:uppercase;color:#868E96;margin-bottom:10px">Year Definition</div>
          <div style="display:grid;gap:14px;margin-bottom:6px">
            <div>
              <label style="display:block;font-size:11.5px;font-weight:600;color:#495057;margin-bottom:5px">Year Name <span style="color:#C92A2A">*</span></label>
              <input v-model="fForm.name" class="b-input" placeholder="e.g. 2025-26"
                @input="nameManuallyEdited=true"/>
              <div style="font-size:11px;color:#868E96;margin-top:3px">Auto-generated from dates — or type a custom name</div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
              <div>
                <label style="display:block;font-size:11.5px;font-weight:600;color:#495057;margin-bottom:5px">Start Date <span style="color:#C92A2A">*</span></label>
                <input v-model="fForm.start" class="b-input" type="date" @change="autoFillName"/>
              </div>
              <div>
                <label style="display:block;font-size:11.5px;font-weight:600;color:#495057;margin-bottom:5px">End Date <span style="color:#C92A2A">*</span></label>
                <input v-model="fForm.end" class="b-input" type="date" @change="autoFillName"/>
              </div>
            </div>
            <div>
              <label style="display:block;font-size:11.5px;font-weight:600;color:#495057;margin-bottom:5px">Period Generation</label>
              <select v-model="fForm.period_type" class="b-input">
                <option value="Monthly">Monthly — 12 periods per year</option>
                <option value="Quarterly">Quarterly — 4 periods per year</option>
                <option value="Annual">Annual — 1 period (full year)</option>
              </select>
              <div style="font-size:11px;color:#868E96;margin-top:3px">Lock past periods to prevent backdated entries</div>
            </div>
          </div>

          <div style="font-size:10.5px;font-weight:700;letter-spacing:.7px;text-transform:uppercase;color:#868E96;margin-bottom:10px;margin-top:22px;padding-top:20px;border-top:1px solid #E2E8F0">Year-End Settings</div>
          <div style="display:grid;gap:14px;margin-bottom:6px">
            <div>
              <label style="display:block;font-size:11.5px;font-weight:600;color:#495057;margin-bottom:5px">Closing Account for P&amp;L</label>
              <input v-model="fForm.closing_acct" class="b-input" placeholder="e.g. Retained Earnings"/>
              <div style="font-size:11px;color:#868E96;margin-top:3px">Net P&amp;L is transferred here at year-end close</div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
              <div>
                <label style="display:block;font-size:11.5px;font-weight:600;color:#495057;margin-bottom:5px">Auto-close on Year End?</label>
                <div style="display:flex;gap:14px;margin-top:6px">
                  <label style="display:flex;align-items:center;gap:5px;cursor:pointer;font-size:13px"><input type="radio" v-model="fForm.auto_close" :value="1" style="accent-color:#3B5BDB"/> Yes</label>
                  <label style="display:flex;align-items:center;gap:5px;cursor:pointer;font-size:13px"><input type="radio" v-model="fForm.auto_close" :value="0" style="accent-color:#3B5BDB"/> No</label>
                </div>
              </div>
              <div>
                <label style="display:block;font-size:11.5px;font-weight:600;color:#495057;margin-bottom:5px">Is Default Year?</label>
                <div style="display:flex;gap:14px;margin-top:6px">
                  <label style="display:flex;align-items:center;gap:5px;cursor:pointer;font-size:13px"><input type="radio" v-model="fForm.is_default" :value="1" style="accent-color:#3B5BDB"/> Yes</label>
                  <label style="display:flex;align-items:center;gap:5px;cursor:pointer;font-size:13px"><input type="radio" v-model="fForm.is_default" :value="0" style="accent-color:#3B5BDB"/> No</label>
                </div>
              </div>
            </div>
          </div>

          <div style="font-size:10.5px;font-weight:700;letter-spacing:.7px;text-transform:uppercase;color:#868E96;margin-bottom:10px;margin-top:22px;padding-top:20px;border-top:1px solid #E2E8F0">
            Period Preview
            <span v-if="periodPreview.length" style="margin-left:6px;font-size:10px;background:#EEF2FF;color:#3B5BDB;padding:1px 7px;border-radius:10px;font-weight:600;text-transform:none">{{periodPreview.length}} periods</span>
          </div>
          <div style="border:1px solid #E2E8F0;border-radius:8px;overflow:hidden">
            <div v-if="!periodPreview.length" style="padding:16px;text-align:center;color:#868E96;font-size:13px">
              {{fForm.start&&fForm.end&&fForm.start>=fForm.end?"⚠ End date must be after start date":"Set start and end dates to preview periods"}}
            </div>
            <template v-else>
              <div v-for="(p,i) in (showAllPeriods ? periodPreview : periodPreview.slice(0,6))" :key="i"
                style="display:flex;justify-content:space-between;padding:8px 14px;border-bottom:1px solid #F1F3F5;font-size:12.5px">
                <span :style="{color:p.is_current?'#3B5BDB':'#344054',fontWeight:p.is_current?600:400}">
                  {{p.name}}<span v-if="p.is_current" style="margin-left:5px;font-size:10px;background:#EEF2FF;color:#3B5BDB;padding:1px 5px;border-radius:8px">NOW</span>
                </span>
                <span style="color:#868E96;">{{p.start}} – {{p.end}}</span>
              </div>
              <div v-if="periodPreview.length>6"
                @click="showAllPeriods=!showAllPeriods"
                style="padding:8px 14px;text-align:center;font-size:12px;background:#F8F9FC;cursor:pointer;color:#2563eb;font-weight:600;user-select:none">
                {{ showAllPeriods ? '▲ Show less' : '+ ' + (periodPreview.length-6) + ' more periods' }}
              </div>
            </template>
          </div>
        </div>

        <div style="padding:14px 24px;border-top:1px solid #E2E8F0;display:flex;justify-content:flex-end;gap:10px;background:#F8F9FC;flex-shrink:0">
          <button class="b-btn b-btn-ghost" @click="closeDrawer">Cancel</button>
          <button class="b-btn b-btn-primary" @click="saveYear" :disabled="saving" style="min-width:130px">
            {{saving?"Saving…":editingName?"Update Year":"Create Year"}}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showCloseModal" style="position:fixed;inset:0;z-index:9100;background:rgba(15,23,42,.5);display:flex;align-items:center;justify-content:center;padding:20px;backdrop-filter:blur(3px)" @click.self="showCloseModal=false">
      <div style="background:#fff;border-radius:12px;padding:28px 32px;max-width:480px;width:100%;box-shadow:0 20px 60px rgba(0,0,0,.2)">
        <div style="font-size:18px;font-weight:700;margin-bottom:6px;color:#1A1D23">Close Fiscal Year "{{closeModalYear}}"?</div>
        <div style="font-size:13px;color:#868E96;margin-bottom:18px;line-height:1.6">This will lock all periods and mark the year as closed. Review the actions below before proceeding.</div>
        <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:20px">
          <div style="display:flex;align-items:center;gap:10px;font-size:13px;padding:9px 12px;background:#EBFBEE;border-radius:7px;color:#2F9E44">
            <span style="font-size:15px">✓</span> All past periods will be locked (no backdated entries)
          </div>
          <div style="display:flex;align-items:center;gap:10px;font-size:13px;padding:9px 12px;background:#F8F9FC;border-radius:7px;color:#495057">
            <span style="font-size:15px">→</span> Net P&amp;L transferred to "{{selectedYearData?.closing_acct||"Retained Earnings"}}"
          </div>
          <div style="display:flex;align-items:center;gap:10px;font-size:13px;padding:9px 12px;background:#F8F9FC;border-radius:7px;color:#495057">
            <span style="font-size:15px">🔒</span> All transactions in this year become read-only
          </div>
        </div>
        <div style="background:#FFF3BF;border:1px solid rgba(230,119,0,.25);border-radius:8px;padding:10px 14px;font-size:12.5px;color:#7F3E00;margin-bottom:20px">
          ⚠ This action <strong>cannot be reversed</strong> without manual journal entries.
        </div>
        <div style="display:flex;gap:10px;justify-content:flex-end">
          <button class="b-btn b-btn-ghost" @click="showCloseModal=false">Cancel</button>
          <button class="b-btn b-btn-primary" style="background:#C92A2A" @click="doCloseYear">Proceed &amp; Close Year</button>
        </div>
      </div>
    </div>
  </Teleport>
</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { apiGET, apiPOST } from "../api/client.js";
import { useToast } from "../composables/useToast.js";
import { icon } from "../utils/icons.js";
import { usePermissions } from "../composables/usePermissions.js";

const { toast } = useToast();
const { canCreate, canEdit } = usePermissions();

const FY_MONTHS      = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const FY_MONTHS_FULL = ["January","February","March","April","May","June","July","August","September","October","November","December"];

const loading        = ref(true);
const loadError      = ref("");
const allYears       = ref([]);
const selectedYear   = ref(null);
const editingName    = ref(null);
const showDrawer     = ref(false);
const showCloseModal  = ref(false);
const showAllPeriods  = ref(false);
const closeModalYear = ref(null);
const saving         = ref(false);
// frappeConnected: true once we successfully loaded at least one response from Frappe.
// Never reset to false after first success — a re-load failure doesn't mean Frappe is gone.
const frappeConnected = ref(false);
const drawerError    = ref("");
const nameManuallyEdited = ref(false);
const currentCompany = ref("");

const fForm = reactive({ name: "", start: "", end: "", period_type: "Monthly", closing_acct: "Retained Earnings", auto_close: 0, is_default: 0 });

function todayLocal() {
  const d = new Date();
  return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
}
function fmtDate(d) {
  if (!d) return "—";
  const dt = new Date(d + "T00:00:00");
  return String(dt.getDate()).padStart(2, "0") + " " + FY_MONTHS[dt.getMonth()] + " " + dt.getFullYear();
}
function fmtShort(d) {
  if (!d) return "";
  const dt = new Date(d + "T00:00:00");
  return FY_MONTHS[dt.getMonth()] + "'" + String(dt.getFullYear()).slice(2);
}
function daysBetween(a, b) {
  return Math.max(0, Math.round((new Date(b + "T00:00:00") - new Date(a + "T00:00:00")) / 864e5));
}
function daysElapsed(start, end) {
  const now = todayLocal(), s = start, e = end;
  if (now < s) return 0;
  if (now > e) return daysBetween(s, e);
  return daysBetween(s, now);
}
function isCurrent(start, end) { return todayLocal() >= start && todayLocal() <= end; }
function isPast(end) { return todayLocal() > end; }

function generatePeriods(start, end, type, existingPeriods) {
  const lockMap = {};
  (existingPeriods || []).forEach((p) => { lockMap[p.start] = p.locked; });

  const periods = [];
  const s = new Date(start + "T00:00:00"), e = new Date(end + "T00:00:00");
  if (type === "Annual") {
    periods.push({ name: fmtShort(start) + " – " + fmtShort(end), start, end, locked: lockMap[start] || false, is_current: isCurrent(start, end), is_past: isPast(end) });
    return periods;
  }
  const step = type === "Quarterly" ? 3 : 1;
  let cur = new Date(s);
  while (cur <= e) {
    const pStart = cur.getFullYear() + "-" + String(cur.getMonth() + 1).padStart(2, "0") + "-" + String(cur.getDate()).padStart(2, "0");
    const nxt = new Date(cur);
    nxt.setMonth(nxt.getMonth() + step);
    nxt.setDate(0);
    const pEndDt = nxt > e ? e : nxt;
    const pEnd = pEndDt.getFullYear() + "-" + String(pEndDt.getMonth() + 1).padStart(2, "0") + "-" + String(pEndDt.getDate()).padStart(2, "0");
    const ps = new Date(pStart + "T00:00:00");
    const pName = type === "Quarterly"
      ? "Q" + Math.ceil((ps.getMonth() + 1) / 3) + " " + ps.getFullYear()
      : FY_MONTHS_FULL[ps.getMonth()] + " " + ps.getFullYear();
    periods.push({ name: pName, start: pStart, end: pEnd, locked: lockMap[pStart] || false, is_current: isCurrent(pStart, pEnd), is_past: isPast(pEnd) });
    cur = new Date(pEndDt); cur.setDate(cur.getDate() + 1);
    if (cur > e) break;
  }
  return periods;
}

async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    const res = await apiGET("zoho_books_clone.api.docs.get_fiscal_years");
    const co = res?.company || "";
    currentCompany.value = co;
    const allFY = res?.years || [];

    // Mark Frappe as connected on any successful response (even empty list)
    frappeConnected.value = true;

    allYears.value = allFY.map((y) => {
      const serverLockDate = y.lock_date || "";
      return {
        // name = full doc name ("2025-26 - Acme Ltd"), year_label = display ("2025-26")
        name: y.name, year_label: y.year_label || y.name,
        start: y.year_start_date, end: y.year_end_date,
        period_type: "Monthly", closing_acct: "Retained Earnings",
        auto_close: 0, is_default: 0, is_closed: y.is_closed ? 1 : 0,
        company: y.company || "",
        periods: generatePeriods(y.year_start_date, y.year_end_date, "Monthly",
          serverLockDate
            ? generatePeriods(y.year_start_date, y.year_end_date, "Monthly").map(p =>
                ({ ...p, locked: p.end <= serverLockDate }))
            : []
        ),
      };
    });

    const cur = allYears.value.find((y) => isCurrent(y.start, y.end));
    if (!selectedYear.value || !allYears.value.find(y => y.name === selectedYear.value)) {
      selectedYear.value = (cur || allYears.value[0] || {}).name || null;
    }
  } catch (e) {
    loadError.value = "Could not load fiscal years — " + (e.message || "server error. Check that the Frappe server is reachable.");
    // Do NOT populate fake/local years. Keep existing list if we had one from a prior successful load.
    if (!frappeConnected.value) {
      allYears.value = [];
    }
  } finally {
    loading.value = false;
  }
}

const stats = computed(() => {
  const cur = allYears.value.find((y) => isCurrent(y.start, y.end));
  const allPeriods = allYears.value.flatMap((y) => y.periods || []);
  return {
    total: allYears.value.length,
    currentName: cur ? (cur.year_label || cur.name) : "None",
    elapsed: cur ? daysElapsed(cur.start, cur.end) + " / " + daysBetween(cur.start, cur.end) : "—",
    locked: allPeriods.filter((p) => p.locked).length,
    needsClosing: allYears.value.filter((y) => isPast(y.end) && !y.is_closed).length,
  };
});

const selectedYearData = computed(() => allYears.value.find((y) => y.name === selectedYear.value) || null);
const periodPreview = computed(() => {
  if (!fForm.start || !fForm.end || fForm.start >= fForm.end) return [];
  return generatePeriods(fForm.start, fForm.end, fForm.period_type);
});

function selectYear(name) { selectedYear.value = name; }

function computeFYLockDate(y) {
  const locked = (y.periods || []).filter((p) => p.locked && !p.is_current);
  if (!locked.length) return "";
  return locked.map((p) => p.end).sort().reverse()[0];
}

async function persistFYLockDate(y) {
  if (!frappeConnected.value) return;
  const lockDateVal = computeFYLockDate(y);
  try {
    await apiPOST("frappe.client.set_value", {
      doctype: "Fiscal Year",
      name: y.name,
      fieldname: "lock_date",
      value: lockDateVal,
    });
  } catch (e) {
    toast("Warning: could not persist lock to server — " + (e.message || "unknown error"), "error");
  }
}

function togglePeriodLock(yearName, idx) {
  if (!canEdit("accounts")) { toast("Read-only access", "error"); return; }
  const y = allYears.value.find((x) => x.name === yearName);
  if (!y) return;
  const nowLocked = !y.periods[idx].locked;
  y.periods[idx] = { ...y.periods[idx], locked: nowLocked };
  persistFYLockDate(y);
  toast(nowLocked ? "Period locked" : "Period unlocked");
}
function lockAllPeriods(yearName, lock) {
  if (!canEdit("accounts")) { toast("Read-only access", "error"); return; }
  const y = allYears.value.find((x) => x.name === yearName);
  if (!y) return;
  y.periods = y.periods.map((p) =>
    p.is_current ? p : { ...p, locked: lock ? !!p.is_past : false }
  );
  persistFYLockDate(y);
  toast(lock ? "All past periods locked" : "All periods unlocked");
}

function openAdd() {
  editingName.value = null; nameManuallyEdited.value = false; drawerError.value = "";
  const now = new Date(); const ys = now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1;
  Object.assign(fForm, { name: ys + "-" + String(ys + 1).slice(2), start: ys + "-04-01", end: (ys + 1) + "-03-31", period_type: "Monthly", closing_acct: "Retained Earnings", auto_close: 0, is_default: 0 });
  showDrawer.value = true;
}
function openEdit(name) {
  const y = allYears.value.find((x) => x.name === name);
  if (!y) return;
  editingName.value = name; nameManuallyEdited.value = true; drawerError.value = "";
  // fForm.name should show the display label (without company suffix), not the full doc name
  Object.assign(fForm, { name: y.year_label || y.name, start: y.start, end: y.end, period_type: y.period_type || "Monthly", closing_acct: y.closing_acct || "Retained Earnings", auto_close: y.auto_close || 0, is_default: y.is_default || 0 });
  showDrawer.value = true;
}
function closeDrawer() { showDrawer.value = false; editingName.value = null; drawerError.value = ""; }

function autoFillName() {
  if (nameManuallyEdited.value) return;
  if (fForm.start && fForm.end && fForm.start < fForm.end) {
    const sy = new Date(fForm.start + "T00:00:00").getFullYear();
    const ey = new Date(fForm.end + "T00:00:00").getFullYear();
    fForm.name = sy === ey ? String(sy) : sy + "-" + String(ey).slice(2);
  }
}

function validateForm() {
  if (!fForm.name.trim()) return "Year name is required.";
  if (!fForm.start) return "Start date is required.";
  if (!fForm.end) return "End date is required.";
  if (fForm.start >= fForm.end) return "End date must be after start date.";
  const label = fForm.name.trim();
  for (const y of allYears.value) {
    // Skip the year currently being edited
    if (editingName.value && y.name === editingName.value) continue;
    // Duplicate check: compare the SHORT display label only (never the full doc name with company suffix)
    if ((y.year_label || y.name) === label) {
      return `A fiscal year named "${label}" already exists for this company. Use Edit to modify it.`;
    }
    // Date overlap check — closed years are exempt
    if (y.is_closed) continue;
    if (fForm.start <= y.end && fForm.end >= y.start) {
      return `Dates overlap with existing fiscal year "${y.year_label || y.name}" (${fmtDate(y.start)} – ${fmtDate(y.end)}).`;
    }
  }
  return "";
}

async function saveYear() {
  if (!(editingName.value ? canEdit("accounts") : canCreate("accounts"))) { toast("Read-only access", "error"); return; }
  drawerError.value = "";
  const err = validateForm();
  if (err) { drawerError.value = err; return; }
  saving.value = true;
  try {
    if (frappeConnected.value) {
      // Backend resolves the correct company via _resolve_company_for()
      await apiPOST("zoho_books_clone.api.docs.save_fiscal_year", {
        year_label: fForm.name.trim(),
        start_date: fForm.start,
        end_date:   fForm.end,
        doc_name:   editingName.value || "",
      });
      await load();
      toast(editingName.value ? "Fiscal year updated" : "Fiscal year created");
      closeDrawer();
    } else {
      drawerError.value = "Not connected to server. Please refresh the page and try again.";
    }
  } catch (e) {
    drawerError.value = "Save error: " + (e.message || "could not save");
  } finally {
    saving.value = false;
  }
}

function openCloseYear(name) {
  if (!canEdit("accounts")) { toast("Read-only access", "error"); return; }
  closeModalYear.value = name; showCloseModal.value = true;
}

async function doCloseYear() {
  if (!canEdit("accounts")) { toast("Read-only access", "error"); showCloseModal.value = false; return; }
  const name = closeModalYear.value;
  if (!name) return;
  showCloseModal.value = false; closeModalYear.value = null;
  if (frappeConnected.value) {
    try {
      const res = await apiPOST("zoho_books_clone.accounts.fiscal_close.close_fiscal_year", { fiscal_year: name });
      await load();
      const je = res?.journal_entry;
      toast(je ? "Year closed — Closing JE " + je + " posted" : res?.message || "Fiscal year closed in Frappe");
    } catch (e) {
      toast("Failed to close fiscal year — " + (e.message || "please try again"), "error");
    }
  } else {
    toast("Not connected to server — cannot close year", "error");
  }
}

// ── Books lock date (per-company, resolved server-side) ──────────────────────
const lockDate = ref("");
const lockDateInput = ref("");
const lockSaving = ref(false);

function fmtLock(d) { if (!d) return ""; try { return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }); } catch { return d; } }

async function loadLockDate() {
  try {
    const r = await apiGET("zoho_books_clone.api.admin.get_books_lock_date");
    const v = r?.lock_date || "";
    if (r?.company && !currentCompany.value) currentCompany.value = r.company;
    lockDate.value = v;
    lockDateInput.value = v;
  } catch { lockDate.value = ""; }
}

async function saveLockDate() {
  if (!canEdit("accounts")) { toast("Read-only access", "error"); return; }
  if (!lockDateInput.value) return;
  lockSaving.value = true;
  try {
    const r = await apiPOST("zoho_books_clone.api.admin.set_books_lock_date", { lock_date: lockDateInput.value });
    lockDate.value = r?.lock_date || lockDateInput.value;
    toast("Books locked up to " + fmtLock(lockDate.value), "success");
  } catch (e) { toast(e.message || "Failed to set lock date", "error"); }
  finally { lockSaving.value = false; }
}

async function clearLockDate() {
  if (!canEdit("accounts")) { toast("Read-only access", "error"); return; }
  lockSaving.value = true;
  try {
    await apiPOST("zoho_books_clone.api.admin.set_books_lock_date", { lock_date: "" });
    lockDate.value = ""; lockDateInput.value = "";
    toast("Books lock date cleared", "success");
  } catch (e) { toast(e.message || "Failed to clear lock date", "error"); }
  finally { lockSaving.value = false; }
}

onMounted(async () => { await load(); await loadLockDate(); });
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   Fiscal Years — base layout tokens
   ═══════════════════════════════════════════════════════════ */
.fy-mobile-periods  { display: none; }
.fy-desktop-periods { display: block; }
.fy-mobile-back     { display: none; }
.fy-right-panel     { display: block; }
.fy-left-panel      { display: flex; }

/* ── KPI stat cards ── */
.fy-kpi-card { padding: 13px 16px; }
.fy-kpi-lbl  { font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; color: #868E96; margin-bottom: 6px; }
.fy-kpi-val  { font-size: 22px; font-weight: 700; color: #1A1D23; line-height: 1; }
.fy-kpi-val--sm { font-size: 14px; }
.fy-kpi-card--green { background: linear-gradient(135deg,#f0fdf4,#fff); }
.fy-kpi-card--blue  { background: linear-gradient(135deg,#eff6ff,#fff); }
.fy-kpi-card--orange{ background: linear-gradient(135deg,#fff7ed,#fff); }
.fy-kpi-card--red   { background: linear-gradient(135deg,#fff1f2,#fff); }

/* ═══════════════════════════════════════════════════════════
   RESPONSIVE  –  ≤ 768 px (tablets + phones)
   ═══════════════════════════════════════════════════════════ */
@media (max-width: 768px) {

  /* ── Stats strip: 2-col ── */
  .fy-stats-grid {
    grid-template-columns: 1fr 1fr !important;
    gap: 8px !important;
  }

  /* ── Lock date card: stack vertically ── */
  .fy-lock-card {
    flex-direction: column !important;
    align-items: flex-start !important;
    gap: 10px !important;
    padding: 12px 14px !important;
  }
  .fy-lock-card > div:last-child {
    margin-left: 0 !important;
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .fy-lock-card > div:last-child input[type="date"] {
    width: 100%;
    box-sizing: border-box;
  }
  .fy-lock-card > div:last-child button { width: 100%; }

  /* ── Main layout: single column ── */
  .fy-main-layout {
    grid-template-columns: 1fr !important;
    gap: 0 !important;
  }

  .fy-left-panel { width: 100%; flex-direction: column; }

  .fy-left-panel--hidden { display: none !important; }

  .fy-right-panel { display: none; width: 100%; }
  .fy-right-panel--visible { display: block !important; }

  /* ── Back button ── */
  .fy-mobile-back { display: block; margin-bottom: 12px; }

  .fy-back-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #fff;
    border: 1.5px solid #e5e7eb;
    border-radius: 8px;
    padding: 7px 14px;
    font-size: 13px;
    font-weight: 600;
    color: #374151;
    cursor: pointer;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    transition: background 0.15s;
  }
  .fy-back-btn:hover { background: #f9fafb; }

  /* ── Period TABLE → hidden on mobile ── */
  .fy-desktop-periods { display: none !important; }

  /* ── Period CARDS → shown on mobile ── */
  .fy-mobile-periods {
    display: flex;
    flex-direction: column;
    gap: 0;
    padding: 8px 10px;
    background: #f8fafc;
  }

  .fy-period-card {
    border-radius: 10px;
    border: 1px solid #e5e7eb;
    border-left: 3px solid #E2E8F0;
    margin-bottom: 8px;
    padding: 10px 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  }

  .fy-pc--locked  { border-left-color: #C92A2A; }
  .fy-pc--current { border-left-color: #3B5BDB; }
  .fy-pc--past    { border-left-color: #ADB5BD; }
  .fy-pc--future  { border-left-color: #DEE2E6; }

  .fy-pc-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 8px;
  }
  .fy-pc-name {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 4px;
    font-size: 13px;
  }
  .fy-pc-status { flex-shrink: 0; }

  .fy-pc-bottom {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  .fy-pc-date { font-size: 11.5px; color: #868E96; }

  .fy-pc-lock-btn {
    background: #fff;
    border: 1px solid #CED4DA;
    border-radius: 6px;
    cursor: pointer;
    padding: 4px 12px;
    font-size: 11.5px;
    font-family: inherit;
    color: #868E96;
    transition: all 0.15s;
    flex-shrink: 0;
  }
  .fy-pc-lock-btn--locked {
    border-color: #C92A2A;
    color: #C92A2A;
    background: #FFF5F5;
  }

  /* Drawer: full screen */
  div[style*="width:480px"] {
    width: 100% !important;
    max-width: 100vw !important;
  }

} /* end @media ≤768px */
</style>