<template>
  <div class="page-reports">

    <!-- Report selector tabs -->
    <div class="report-tabs">
      <button
        v-for="r in reports"
        :key="r.key"
        class="report-tab"
        :class="{ active: activeReport === r.key }"
        @click="activeReport = r.key"
      >
        <span v-html="r.icon"></span>
        {{ r.label }}
      </button>
    </div>

    <!-- Date range picker (hidden for aging reports which use as-of-date) -->
    <div class="books-card date-range-bar">
      <template v-if="['ar','ap'].includes(activeReport)">
        <label class="dr-label">As of Date</label>
        <input type="date" v-model="toDate" class="dr-input" />
      </template>
      <template v-else>
        <label class="dr-label">From</label>
        <input type="date" v-model="fromDate" class="dr-input" />
        <label class="dr-label">To</label>
        <input type="date" v-model="toDate" class="dr-input" />
      </template>
      <button class="books-btn books-btn-primary" @click="runReport">Run Report</button>
      <button v-if="['ar','ap'].includes(activeReport) && (arAging.length||apAging.length)"
        class="books-btn" style="background:#EBFBEE;color:#2F9E44;border:1px solid #8CE99A"
        @click="exportAgingCSV">
        Export CSV
      </button>
      <button v-if="activeReport === 'items' && itemSales.length"
        class="books-btn" style="background:#EBFBEE;color:#2F9E44;border:1px solid #8CE99A"
        @click="exportItemSalesCSV">
        Export CSV
      </button>
      <button v-if="activeReport === 'customers' && customerSales.length"
        class="books-btn" style="background:#EBFBEE;color:#2F9E44;border:1px solid #8CE99A"
        @click="exportCustomerSalesCSV">
        Export CSV
      </button>
      <button v-if="activeReport === 'profit' && profitReport.length"
        class="books-btn" style="background:#EBFBEE;color:#2F9E44;border:1px solid #8CE99A"
        @click="exportProfitCSV">
        Export CSV
      </button>
      <button v-if="activeReport === 'invoice_profit' && invoiceProfit.length"
        class="books-btn" style="background:#EBFBEE;color:#2F9E44;border:1px solid #8CE99A"
        @click="exportInvoiceProfitCSV">
        Export CSV
      </button>
    </div>

    <!-- P&L -->
    <div v-if="activeReport === 'pl'" class="books-card report-card">
      <div class="books-card-title">Profit & Loss</div>
      <template v-if="plLoading"><div class="loading-shimmer" style="height:120px;border-radius:8px"></div></template>
      <template v-else-if="pl">
        <div class="pl-row income">
          <span>Total Income</span>
          <span class="mono green">{{ fmt(pl.total_income) }}</span>
        </div>
        <div v-if="pl.cogs" class="pl-row expense">
          <span>Cost of Goods Sold</span>
          <span class="mono red">{{ fmt(pl.cogs) }}</span>
        </div>
        <div v-if="pl.cogs" class="pl-row" :class="pl.gross_profit >= 0 ? 'profit' : 'loss'">
          <span>Gross Profit</span>
          <span class="mono">{{ fmt(pl.gross_profit) }}</span>
        </div>
        <div class="pl-row expense">
          <span>Total Expense</span>
          <span class="mono red">{{ fmt(pl.total_expense) }}</span>
        </div>
        <div v-if="pl.stock_adjustment" class="pl-row expense">
          <span>Stock Adjustment</span>
          <span class="mono" :class="pl.stock_adjustment > 0 ? 'red' : 'green'">{{ fmt(pl.stock_adjustment) }}</span>
        </div>
        <div class="pl-divider"></div>
        <div class="pl-row net" :class="pl.net_profit >= 0 ? 'profit' : 'loss'">
          <span>Net Profit</span>
          <span class="mono">{{ fmt(pl.net_profit) }}</span>
        </div>
      </template>
      <div v-else class="empty-msg">Run the report to see results.</div>
    </div>

    <!-- P&L Monthly Chart -->
    <div v-if="activeReport === 'pl' && plMonthly.length" class="books-card report-card">
      <div class="books-card-title" style="margin-bottom:16px">Monthly Trend</div>
      <div style="overflow-x:auto">
        <div style="display:flex;align-items:flex-end;gap:6px;min-width:400px;height:140px;padding:0 4px">
          <div v-for="m in plMonthly" :key="m.month" style="flex:1;display:flex;flex-direction:column;align-items:center;gap:3px">
            <div style="width:100%;display:flex;flex-direction:column;align-items:center;gap:2px;flex:1;justify-content:flex-end">
              <div :style="{width:'60%',background:'#4C6EF5',borderRadius:'3px 3px 0 0',height:barH(m.income)+'px',minHeight:'2px',transition:'height .3s'}" :title="'Income: ₹'+fmtN(m.income)"></div>
            </div>
            <div style="width:100%;display:flex;flex-direction:column;align-items:center;gap:2px;flex:1;justify-content:flex-end">
              <div :style="{width:'60%',background:'#FA5252',borderRadius:'3px 3px 0 0',height:barH(m.expense)+'px',minHeight:'2px',transition:'height .3s'}" :title="'Expense: ₹'+fmtN(m.expense)"></div>
            </div>
            <div style="font-size:10px;color:#868E96;margin-top:4px;white-space:nowrap">{{m.month.slice(5)}}</div>
          </div>
        </div>
        <div style="display:flex;gap:16px;justify-content:center;margin-top:10px;font-size:11.5px">
          <span style="display:flex;align-items:center;gap:4px"><span style="width:10px;height:10px;background:#4C6EF5;border-radius:2px;display:inline-block"></span>Income</span>
          <span style="display:flex;align-items:center;gap:4px"><span style="width:10px;height:10px;background:#FA5252;border-radius:2px;display:inline-block"></span>Expense</span>
        </div>
      </div>
    </div>

    <!-- Balance sheet -->
    <div v-if="activeReport === 'bs'" class="books-card report-card">
      <div class="books-card-title">Balance Sheet</div>
      <template v-if="bsLoading"><div class="loading-shimmer" style="height:120px;border-radius:8px"></div></template>
      <template v-else-if="bs">
        <div class="bs-grid">
          <div class="bs-block assets">
            <div class="bs-section-title">Assets</div>
            <div class="bs-amount">{{ fmt(bs.total_assets) }}</div>
          </div>
          <div class="bs-block liabilities">
            <div class="bs-section-title">Liabilities</div>
            <div class="bs-amount">{{ fmt(bs.total_liabilities) }}</div>
          </div>
          <div class="bs-block equity">
            <div class="bs-section-title">Equity</div>
            <div class="bs-amount">{{ fmt(bs.total_equity) }}</div>
            <div v-if="bs.retained_earnings != null" class="bs-eq-sub">
              <span>Capital {{ fmt(bs.equity_capital) }}</span>
              <span>Retained {{ fmt(bs.retained_earnings) }}</span>
            </div>
          </div>
        </div>
        <div class="bs-balance-check" :class="bsBalanced ? 'bs-ok' : 'bs-bad'">
          <span class="bs-bc-icon">{{ bsBalanced ? '✓' : '✕' }}</span>
          Assets = Liabilities + Equity
          <span class="bs-bc-eq">{{ fmt(bs.total_assets) }} = {{ fmt(bs.total_liabilities) }} + {{ fmt(bs.total_equity) }}</span>
        </div>
      </template>
      <div v-else class="empty-msg">Run the report to see results.</div>
    </div>

    <!-- Cash flow -->
    <div v-if="activeReport === 'cf'" class="books-card report-card">
      <div class="books-card-title">Cash Flow</div>
      <template v-if="cfLoading"><div class="loading-shimmer" style="height:120px;border-radius:8px"></div></template>
      <template v-else-if="cf">
        <div class="cf-rows">
          <div class="cf-row"><span>Operating Activities <span class="cf-hint">P&amp;L + working capital</span></span><span class="mono" :class="cf.operating >= 0 ? 'green':'red'">{{ fmt(cf.operating) }}</span></div>
          <div class="cf-row"><span>Investing Activities <span class="cf-hint">asset changes</span></span><span class="mono" :class="cf.investing >= 0 ? 'green':'red'">{{ fmt(cf.investing) }}</span></div>
          <div class="cf-row"><span>Financing Activities <span class="cf-hint">equity / debt</span></span><span class="mono" :class="cf.financing >= 0 ? 'green':'red'">{{ fmt(cf.financing) }}</span></div>
          <div class="pl-divider"></div>
          <div class="cf-row net"><span>Net Change in Cash</span><span class="mono" :class="cf.net_change >= 0 ? 'green':'red'">{{ fmt(cf.net_change) }}</span></div>
          <template v-if="cf.opening_cash != null">
            <div class="cf-row cf-sub"><span>Opening Cash &amp; Bank</span><span class="mono">{{ fmt(cf.opening_cash) }}</span></div>
            <div class="cf-row cf-sub"><span>Closing Cash &amp; Bank</span><span class="mono">{{ fmt(cf.closing_cash) }}</span></div>
          </template>
        </div>
      </template>
      <div v-else class="empty-msg">Run the report to see results.</div>
    </div>

    <!-- VAT Summary -->
    <div v-if="activeReport === 'vat'" class="books-card report-card">
      <div class="books-card-title">VAT Summary</div>
      <template v-if="vatLoading"><div class="loading-shimmer" style="height:80px;border-radius:8px"></div></template>
      <template v-else-if="vat">
        <div class="gst-cards">
          <div class="gst-card">
            <div class="gst-card-header">
              <span class="badge badge-blue">Output VAT (on Sales)</span>
            </div>
            <div class="gst-card-body">
              <div class="gst-kv">
                <span class="gst-kv-label">Invoice Count</span>
                <span class="gst-kv-value mono-sm">{{ vat.output_invoice_count }}</span>
              </div>
              <div class="gst-kv">
                <span class="gst-kv-label">Total VAT Collected</span>
                <span class="gst-kv-value mono-sm green fw-600">{{ fmt(vat.output_vat) }}</span>
              </div>
            </div>
          </div>
          <div class="gst-card">
            <div class="gst-card-header">
              <span class="badge badge-blue">Input VAT (on Purchases)</span>
            </div>
            <div class="gst-card-body">
              <div class="gst-kv">
                <span class="gst-kv-label">Invoice Count</span>
                <span class="gst-kv-value mono-sm">{{ vat.input_invoice_count }}</span>
              </div>
              <div class="gst-kv">
                <span class="gst-kv-label">Total VAT Reclaimable</span>
                <span class="gst-kv-value mono-sm green fw-600">{{ fmt(vat.input_vat) }}</span>
              </div>
            </div>
          </div>
          <div class="gst-card" style="border:1px solid var(--accent, #4C6EF5)">
            <div class="gst-card-header">
              <span class="badge" :class="vat.net_vat_payable >= 0 ? 'badge-orange' : 'badge-green'">
                {{ vat.net_vat_payable >= 0 ? 'Net VAT Payable' : 'Net VAT Refundable' }}
              </span>
            </div>
            <div class="gst-card-body">
              <div class="gst-kv">
                <span class="gst-kv-label">Output VAT − Input VAT</span>
                <span class="gst-kv-value mono-sm fw-600" :style="{color: vat.net_vat_payable >= 0 ? '#D9480F' : '#2B8A3E'}">
                  {{ fmt(Math.abs(vat.net_vat_payable)) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </template>
      <div v-else class="empty-msg">Run the report to see results.</div>
    </div>

    <!-- AR Aging -->
    <div v-if="activeReport === 'ar'" class="books-card report-card">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
        <div class="books-card-title" style="margin:0">Accounts Receivable Aging</div>
        <div v-if="arAging.length" style="font-size:12.5px;color:#868E96">
          Total: <span style="font-weight:700;color:#C92A2A">₹{{fmtN(arAging.reduce((s,r)=>s+r.total,0))}}</span>
        </div>
      </div>
      <template v-if="arLoading"><div class="loading-shimmer" style="height:120px;border-radius:8px"></div></template>

      <template v-else-if="arAging.length">
        <div class="aging-cards">
          <div v-for="r in arAging" :key="r.customer" class="aging-card">
            <div class="aging-card-name">{{ r.customer_name || r.customer }}</div>
            <div class="aging-buckets">
              <div class="aging-bucket">
                <span class="bucket-label">Current</span>
                <span class="bucket-val mono-sm">{{ r.current > 0 ? fmtAmt(r.current) : '—' }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">1–30 days</span>
                <span class="bucket-val mono-sm" :class="r.days_1_30>0?'text-warn':''">{{ r.days_1_30 > 0 ? fmtAmt(r.days_1_30) : '—' }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">31–60 days</span>
                <span class="bucket-val mono-sm" :class="r.days_31_60>0?'text-danger':''">{{ r.days_31_60 > 0 ? fmtAmt(r.days_31_60) : '—' }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">61–90 days</span>
                <span class="bucket-val mono-sm" :class="r.days_61_90>0?'text-danger':''">{{ r.days_61_90 > 0 ? fmtAmt(r.days_61_90) : '—' }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">90+ days</span>
                <span class="bucket-val mono-sm" :class="r.days_90_plus>0?'text-danger fw-700':''">{{ r.days_90_plus > 0 ? fmtAmt(r.days_90_plus) : '—' }}</span>
              </div>
            </div>
            <div class="aging-card-total">
              <span class="bucket-label">Total</span>
              <span class="mono-sm fw-700 text-danger">{{ fmtAmt(r.total) }}</span>
            </div>
          </div>
          <!-- Totals summary card -->
          <div class="aging-card aging-card-totals">
            <div class="aging-card-name fw-700">TOTAL</div>
            <div class="aging-buckets">
              <div class="aging-bucket">
                <span class="bucket-label">Current</span>
                <span class="bucket-val mono-sm fw-700">{{ fmtAmt(arAging.reduce((s,r)=>s+r.current,0)) }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">1–30 days</span>
                <span class="bucket-val mono-sm fw-700">{{ fmtAmt(arAging.reduce((s,r)=>s+r.days_1_30,0)) }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">31–60 days</span>
                <span class="bucket-val mono-sm fw-700">{{ fmtAmt(arAging.reduce((s,r)=>s+r.days_31_60,0)) }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">61–90 days</span>
                <span class="bucket-val mono-sm fw-700">{{ fmtAmt(arAging.reduce((s,r)=>s+r.days_61_90,0)) }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">90+ days</span>
                <span class="bucket-val mono-sm fw-700 text-danger">{{ fmtAmt(arAging.reduce((s,r)=>s+r.days_90_plus,0)) }}</span>
              </div>
            </div>
            <div class="aging-card-total">
              <span class="bucket-label">Total</span>
              <span class="mono-sm fw-700 text-danger">{{ fmtAmt(arAging.reduce((s,r)=>s+r.total,0)) }}</span>
            </div>
          </div>
        </div>
      </template>
      <div v-else class="empty-msg">{{arRan ? 'No outstanding receivables as of this date.' : 'Run the report to see results.'}}</div>
    </div>

    <!-- AP Aging -->
    <div v-if="activeReport === 'ap'" class="books-card report-card">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
        <div class="books-card-title" style="margin:0">Accounts Payable Aging</div>
        <div v-if="apAging.length" style="font-size:12.5px;color:#868E96">
          Total: <span style="font-weight:700;color:#C92A2A">₹{{fmtN(apAging.reduce((s,r)=>s+r.total,0))}}</span>
        </div>
      </div>
      <template v-if="apLoading"><div class="loading-shimmer" style="height:120px;border-radius:8px"></div></template>
      <template v-else-if="apAging.length">
        <div class="aging-cards">
          <div v-for="r in apAging" :key="r.supplier" class="aging-card">
            <div class="aging-card-name">{{ r.supplier_name || r.supplier }}</div>
            <div class="aging-buckets">
              <div class="aging-bucket">
                <span class="bucket-label">Current</span>
                <span class="bucket-val mono-sm">{{ r.current > 0 ? fmtAmt(r.current) : '—' }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">1–30 days</span>
                <span class="bucket-val mono-sm" :class="r.days_1_30>0?'text-warn':''">{{ r.days_1_30 > 0 ? fmtAmt(r.days_1_30) : '—' }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">31–60 days</span>
                <span class="bucket-val mono-sm" :class="r.days_31_60>0?'text-danger':''">{{ r.days_31_60 > 0 ? fmtAmt(r.days_31_60) : '—' }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">61–90 days</span>
                <span class="bucket-val mono-sm" :class="r.days_61_90>0?'text-danger':''">{{ r.days_61_90 > 0 ? fmtAmt(r.days_61_90) : '—' }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">90+ days</span>
                <span class="bucket-val mono-sm" :class="r.days_90_plus>0?'text-danger fw-700':''">{{ r.days_90_plus > 0 ? fmtAmt(r.days_90_plus) : '—' }}</span>
              </div>
            </div>
            <div class="aging-card-total">
              <span class="bucket-label">Total</span>
              <span class="mono-sm fw-700 text-danger">{{ fmtAmt(r.total) }}</span>
            </div>
          </div>
          <!-- Totals summary card -->
          <div class="aging-card aging-card-totals">
            <div class="aging-card-name fw-700">TOTAL</div>
            <div class="aging-buckets">
              <div class="aging-bucket">
                <span class="bucket-label">Current</span>
                <span class="bucket-val mono-sm fw-700">{{ fmtAmt(apAging.reduce((s,r)=>s+r.current,0)) }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">1–30 days</span>
                <span class="bucket-val mono-sm fw-700">{{ fmtAmt(apAging.reduce((s,r)=>s+r.days_1_30,0)) }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">31–60 days</span>
                <span class="bucket-val mono-sm fw-700">{{ fmtAmt(apAging.reduce((s,r)=>s+r.days_31_60,0)) }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">61–90 days</span>
                <span class="bucket-val mono-sm fw-700">{{ fmtAmt(apAging.reduce((s,r)=>s+r.days_61_90,0)) }}</span>
              </div>
              <div class="aging-bucket">
                <span class="bucket-label">90+ days</span>
                <span class="bucket-val mono-sm fw-700 text-danger">{{ fmtAmt(apAging.reduce((s,r)=>s+r.days_90_plus,0)) }}</span>
              </div>
            </div>
            <div class="aging-card-total">
              <span class="bucket-label">Total</span>
              <span class="mono-sm fw-700 text-danger">{{ fmtAmt(apAging.reduce((s,r)=>s+r.total,0)) }}</span>
            </div>
          </div>
        </div>
      </template>
      <div v-else class="empty-msg">{{apRan ? 'No outstanding payables as of this date.' : 'Run the report to see results.'}}</div>
    </div>

    <!-- Item-wise Sales -->
    <div v-if="activeReport === 'items'" class="books-card report-card">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
        <div class="books-card-title" style="margin:0">Item-wise Sales</div>
        <div v-if="itemSales.length" style="font-size:12.5px;color:#868E96">
          Total: <span style="font-weight:700;color:#2F9E44">₹{{fmtN(itemSales.reduce((s,r)=>s+Number(r.total_amount||0),0))}}</span>
        </div>
      </div>
      <template v-if="itemsLoading"><div class="loading-shimmer" style="height:200px;border-radius:8px"></div></template>
      <template v-else-if="itemSales.length">
        <table class="books-table aging-table" style="width:100%">
          <thead>
            <tr>
              <th>Item</th>
              <th>UOM</th>
              <th class="ta-r">Invoices</th>
              <th class="ta-r">Qty Sold</th>
              <th class="ta-r">Avg Rate</th>
              <th class="ta-r">Discount</th>
              <th class="ta-r">Total Amount</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in itemSales" :key="row.item_code">
              <td>{{ row.item_name || row.item_code }}</td>
              <td>{{ row.uom || '—' }}</td>
              <td class="ta-r mono-sm">{{ row.invoice_count }}</td>
              <td class="ta-r mono-sm">{{ fmtN(row.qty_sold) }}</td>
              <td class="ta-r mono-sm">{{ fmtAmt(row.avg_rate) }}</td>
              <td class="ta-r mono-sm red">{{ row.total_discount ? fmtAmt(row.total_discount) : '—' }}</td>
              <td class="ta-r mono-sm fw-700 green">{{ fmtAmt(row.total_amount) }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="aging-totals-row">
              <td colspan="3" class="fw-700">TOTAL</td>
              <td class="ta-r fw-700">{{ fmtN(itemSales.reduce((s,r)=>s+Number(r.qty_sold||0),0)) }}</td>
              <td></td>
              <td class="ta-r fw-700 red">{{ fmtAmt(itemSales.reduce((s,r)=>s+Number(r.total_discount||0),0)) }}</td>
              <td class="ta-r fw-700 green">{{ fmtAmt(itemSales.reduce((s,r)=>s+Number(r.total_amount||0),0)) }}</td>
            </tr>
          </tfoot>
        </table>
      </template>
      <div v-else class="empty-msg">{{itemsRan ? 'No sales in this period.' : 'Run the report to see results.'}}</div>
    </div>

    <!-- Customer-wise Sales -->
    <div v-if="activeReport === 'customers'" class="books-card report-card">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
        <div class="books-card-title" style="margin:0">Customer-wise Sales</div>
        <div v-if="customerSales.length" style="font-size:12.5px;color:#868E96">
          Total: <span style="font-weight:700;color:#2F9E44">₹{{fmtN(customerSales.reduce((s,r)=>s+Number(r.total_amount||0),0))}}</span>
        </div>
      </div>
      <template v-if="customersLoading"><div class="loading-shimmer" style="height:200px;border-radius:8px"></div></template>
      <template v-else-if="customerSales.length">
        <table class="books-table aging-table" style="width:100%">
          <thead>
            <tr>
              <th>Customer</th>
              <th class="ta-r">Invoices</th>
              <th class="ta-r">Net Total</th>
              <th class="ta-r">Discount</th>
              <th class="ta-r">Tax</th>
              <th class="ta-r">Avg Invoice</th>
              <th class="ta-r">Outstanding</th>
              <th class="ta-r">Total Amount</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in customerSales" :key="row.customer">
              <td>{{ row.customer_name || row.customer }}</td>
              <td class="ta-r mono-sm">{{ row.invoice_count }}</td>
              <td class="ta-r mono-sm">{{ fmtAmt(row.net_total) }}</td>
              <td class="ta-r mono-sm red">{{ row.total_discount ? fmtAmt(row.total_discount) : '—' }}</td>
              <td class="ta-r mono-sm">{{ fmtAmt(row.total_tax) }}</td>
              <td class="ta-r mono-sm">{{ fmtAmt(row.avg_invoice_value) }}</td>
              <td class="ta-r mono-sm" :class="row.outstanding_amount>0?'text-danger':''">{{ row.outstanding_amount ? fmtAmt(row.outstanding_amount) : '—' }}</td>
              <td class="ta-r mono-sm fw-700 green">{{ fmtAmt(row.total_amount) }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="aging-totals-row">
              <td class="fw-700">TOTAL</td>
              <td class="ta-r fw-700">{{ fmtN(customerSales.reduce((s,r)=>s+Number(r.invoice_count||0),0)) }}</td>
              <td class="ta-r fw-700">{{ fmtAmt(customerSales.reduce((s,r)=>s+Number(r.net_total||0),0)) }}</td>
              <td class="ta-r fw-700 red">{{ fmtAmt(customerSales.reduce((s,r)=>s+Number(r.total_discount||0),0)) }}</td>
              <td class="ta-r fw-700">{{ fmtAmt(customerSales.reduce((s,r)=>s+Number(r.total_tax||0),0)) }}</td>
              <td></td>
              <td class="ta-r fw-700 text-danger">{{ fmtAmt(customerSales.reduce((s,r)=>s+Number(r.outstanding_amount||0),0)) }}</td>
              <td class="ta-r fw-700 green">{{ fmtAmt(customerSales.reduce((s,r)=>s+Number(r.total_amount||0),0)) }}</td>
            </tr>
          </tfoot>
        </table>
      </template>
      <div v-else class="empty-msg">{{customersRan ? 'No sales in this period.' : 'Run the report to see results.'}}</div>
    </div>

    <!-- Profit-wise Report -->
    <div v-if="activeReport === 'profit'" class="books-card report-card">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
        <div class="books-card-title" style="margin:0">Profit-wise Report (by Item)</div>
        <div v-if="profitReport.length" style="font-size:12.5px;color:#868E96">
          Total Profit: <span style="font-weight:700" :class="profitTotal>=0?'green':'red'">{{ fmtAmt(profitTotal) }}</span>
        </div>
      </div>
      <div v-if="profitReport.length" style="font-size:11.5px;color:#94a3b8;margin-bottom:12px">
        Cost is estimated from current average valuation rate per item (excluding WIP warehouses); margins are indicative, not historical FIFO cost.
      </div>
      <template v-if="profitLoading"><div class="loading-shimmer" style="height:200px;border-radius:8px"></div></template>
      <template v-else-if="profitReport.length">
        <table class="books-table aging-table" style="width:100%">
          <thead>
            <tr>
              <th>Item</th>
              <th class="ta-r">Qty Sold</th>
              <th class="ta-r">Revenue</th>
              <th class="ta-r">Cost Rate</th>
              <th class="ta-r">Total Cost</th>
              <th class="ta-r">Profit</th>
              <th class="ta-r">Margin %</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in profitReport" :key="row.item_code">
              <td>
                {{ row.item_name || row.item_code }}
                <span v-if="!row.cost_rate" class="badge badge-muted" style="margin-left:6px;font-size:10px" title="No valuation or standard buying rate found for this item — margin below is not meaningful">no cost data</span>
              </td>
              <td class="ta-r mono-sm">{{ fmtN(row.qty_sold) }}</td>
              <td class="ta-r mono-sm">{{ fmtAmt(row.revenue) }}</td>
              <td class="ta-r mono-sm">{{ row.cost_rate ? fmtAmt(row.cost_rate) : '—' }}</td>
              <td class="ta-r mono-sm red">{{ row.total_cost ? fmtAmt(row.total_cost) : '—' }}</td>
              <td class="ta-r mono-sm fw-700" :class="row.profit>=0?'green':'red'">{{ row.cost_rate ? fmtAmt(row.profit) : '—' }}</td>
              <td class="ta-r mono-sm" :class="row.margin_pct>=0?'green':'red'">{{ row.cost_rate ? Number(row.margin_pct||0).toFixed(1)+'%' : '—' }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="aging-totals-row">
              <td class="fw-700">TOTAL</td>
              <td class="ta-r fw-700">{{ fmtN(profitReport.reduce((s,r)=>s+Number(r.qty_sold||0),0)) }}</td>
              <td class="ta-r fw-700">{{ fmtAmt(profitReport.reduce((s,r)=>s+Number(r.revenue||0),0)) }}</td>
              <td></td>
              <td class="ta-r fw-700 red">{{ fmtAmt(profitReport.filter(r=>r.cost_rate).reduce((s,r)=>s+Number(r.total_cost||0),0)) }}</td>
              <td class="ta-r fw-700" :class="profitTotal>=0?'green':'red'">{{ fmtAmt(profitTotal) }}</td>
              <td class="ta-r fw-700" :class="profitMarginTotal>=0?'green':'red'">{{ profitMarginTotal.toFixed(1) }}%</td>
            </tr>
          </tfoot>
        </table>
        <div v-if="noCostDataCount" style="font-size:11.5px;color:#94a3b8;margin-top:10px">
          {{ noCostDataCount }} item{{noCostDataCount>1?'s':''}} excluded from the profit/margin totals above — no valuation or standard buying rate found (see "no cost data" tag).
        </div>
      </template>
      <div v-else class="empty-msg">{{profitRan ? 'No sales in this period.' : 'Run the report to see results.'}}</div>
    </div>

    <!-- Invoice-wise Profit (single + multi-select) -->
    <div v-if="activeReport === 'invoice_profit'" class="books-card report-card">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;flex-wrap:wrap;gap:8px">
        <div class="books-card-title" style="margin:0">Invoice Profitability</div>
        <div v-if="invoiceProfit.length" style="font-size:12.5px;color:#868E96">
          Total Profit ({{ invoiceProfit.length }} invoices): <span style="font-weight:700" :class="invoiceProfitTotals.profit>=0?'green':'red'">{{ fmtAmt(invoiceProfitTotals.profit) }}</span>
        </div>
      </div>
      <div v-if="invoiceProfit.length" style="font-size:11.5px;color:#94a3b8;margin-bottom:12px">
        Cost is estimated from current average valuation rate per item (excluding WIP warehouses); margins are indicative, not historical FIFO cost. Tick rows to see profit for a single invoice or any combination of selected invoices.
      </div>
      <template v-if="invoiceProfitLoading"><div class="loading-shimmer" style="height:200px;border-radius:8px"></div></template>
      <template v-else-if="invoiceProfit.length">
        <div v-if="selectedInvoices.size" class="books-card" style="background:#F8F9FF;border:1px solid #D0D9FF;padding:10px 14px;margin-bottom:12px;display:flex;gap:22px;flex-wrap:wrap;font-size:12.5px">
          <span><strong>{{ invoiceProfitSelectedTotals.count }}</strong> selected</span>
          <span>Revenue: <span class="mono fw-700">{{ fmtAmt(invoiceProfitSelectedTotals.revenue) }}</span></span>
          <span>Est. Cost: <span class="mono fw-700 red">{{ fmtAmt(invoiceProfitSelectedTotals.total_cost) }}</span></span>
          <span>Profit: <span class="mono fw-700" :class="invoiceProfitSelectedTotals.profit>=0?'green':'red'">{{ fmtAmt(invoiceProfitSelectedTotals.profit) }}</span></span>
        </div>
        <table class="books-table aging-table" style="width:100%">
          <thead>
            <tr>
              <th style="width:32px"><input type="checkbox" :checked="invoiceProfitAllSelected" @change="toggleAllInvoiceSelection" /></th>
              <th>Invoice</th>
              <th>Date</th>
              <th>Customer</th>
              <th class="ta-r">Revenue</th>
              <th class="ta-r">Est. Cost</th>
              <th class="ta-r">Profit</th>
              <th class="ta-r">Margin %</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in invoiceProfit" :key="row.invoice" :class="{ 'row-selected': selectedInvoices.has(row.invoice) }">
              <td><input type="checkbox" :checked="selectedInvoices.has(row.invoice)" @change="toggleInvoiceSelection(row.invoice)" /></td>
              <td class="mono-sm">
                <a href="#" class="inv-detail-link" @click.prevent="openInvoiceDetail(row.invoice)">{{ row.invoice }}</a>
                <span v-if="row.no_cost_lines" class="badge badge-muted" style="margin-left:6px;font-size:10px" title="One or more items on this invoice have no valuation or standard buying rate — cost/margin is understated">partial cost data</span>
              </td>
              <td class="mono-sm">{{ row.posting_date }}</td>
              <td>{{ row.customer_name || row.customer }}</td>
              <td class="ta-r mono-sm">{{ fmtAmt(row.revenue) }}</td>
              <td class="ta-r mono-sm red">{{ fmtAmt(row.total_cost) }}</td>
              <td class="ta-r mono-sm fw-700" :class="row.profit>=0?'green':'red'">{{ fmtAmt(row.profit) }}</td>
              <td class="ta-r mono-sm" :class="row.margin_pct>=0?'green':'red'">{{ Number(row.margin_pct||0).toFixed(1) }}%</td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="aging-totals-row">
              <td colspan="4" class="fw-700">TOTAL</td>
              <td class="ta-r fw-700">{{ fmtAmt(invoiceProfitTotals.revenue) }}</td>
              <td class="ta-r fw-700 red">{{ fmtAmt(invoiceProfitTotals.total_cost) }}</td>
              <td class="ta-r fw-700" :class="invoiceProfitTotals.profit>=0?'green':'red'">{{ fmtAmt(invoiceProfitTotals.profit) }}</td>
              <td class="ta-r fw-700" :class="invoiceProfitTotals.profit>=0?'green':'red'">{{ invoiceProfitTotals.revenue ? (invoiceProfitTotals.profit/invoiceProfitTotals.revenue*100).toFixed(1) : '0.0' }}%</td>
            </tr>
          </tfoot>
        </table>
      </template>
      <div v-else class="empty-msg">{{invoiceProfitRan ? 'No sales in this period.' : 'Run the report to see results.'}}</div>
    </div>

    <!-- Single-invoice item-level P&L drill-down -->
    <Modal :show="invoiceDetailOpen" width="720px" :title="invoiceDetail ? `Profit & Loss — ${invoiceDetail.invoice.name}` : 'Profit & Loss'" @close="invoiceDetailOpen=false">
      <template v-if="invoiceDetailLoading"><div class="loading-shimmer" style="height:180px;border-radius:8px"></div></template>
      <template v-else-if="invoiceDetail">
        <div style="display:flex;flex-wrap:wrap;gap:16px;font-size:12.5px;color:#868E96;margin-bottom:14px">
          <span>Date: <strong style="color:#212529">{{ invoiceDetail.invoice.posting_date }}</strong></span>
          <span>Customer: <strong style="color:#212529">{{ invoiceDetail.invoice.customer_name || invoiceDetail.invoice.customer }}</strong></span>
          <span>Status: <strong style="color:#212529">{{ invoiceDetail.invoice.status }}</strong></span>
        </div>
        <div v-if="invoiceDetail.totals.no_cost_lines" style="font-size:11.5px;color:#94a3b8;margin-bottom:12px">
          {{ invoiceDetail.totals.no_cost_lines }} item{{invoiceDetail.totals.no_cost_lines>1?'s':''}} below have no valuation or standard buying rate — their cost is shown as "—" and excluded from the totals.
        </div>
        <table class="books-table aging-table" style="width:100%">
          <thead>
            <tr>
              <th>Item</th>
              <th class="ta-r">Qty</th>
              <th class="ta-r">Rate</th>
              <th class="ta-r">Revenue</th>
              <th class="ta-r">Cost Rate</th>
              <th class="ta-r">Total Cost</th>
              <th class="ta-r">Profit</th>
              <th class="ta-r">Margin %</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in invoiceDetail.items" :key="row.item_code">
              <td>{{ row.item_name || row.item_code }}</td>
              <td class="ta-r mono-sm">{{ fmtN(row.qty) }}</td>
              <td class="ta-r mono-sm">{{ fmtAmt(row.rate) }}</td>
              <td class="ta-r mono-sm">{{ fmtAmt(row.revenue) }}</td>
              <td class="ta-r mono-sm">{{ row.cost_rate ? fmtAmt(row.cost_rate) : '—' }}</td>
              <td class="ta-r mono-sm red">{{ row.cost_rate ? fmtAmt(row.total_cost) : '—' }}</td>
              <td class="ta-r mono-sm fw-700" :class="row.profit>=0?'green':'red'">{{ row.cost_rate ? fmtAmt(row.profit) : '—' }}</td>
              <td class="ta-r mono-sm" :class="row.margin_pct>=0?'green':'red'">{{ row.cost_rate ? Number(row.margin_pct||0).toFixed(1)+'%' : '—' }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="aging-totals-row">
              <td colspan="3" class="fw-700">TOTAL</td>
              <td class="ta-r fw-700">{{ fmtAmt(invoiceDetail.totals.revenue) }}</td>
              <td></td>
              <td class="ta-r fw-700 red">{{ fmtAmt(invoiceDetail.totals.total_cost) }}</td>
              <td class="ta-r fw-700" :class="invoiceDetail.totals.profit>=0?'green':'red'">{{ fmtAmt(invoiceDetail.totals.profit) }}</td>
              <td class="ta-r fw-700" :class="invoiceDetail.totals.profit>=0?'green':'red'">{{ Number(invoiceDetail.totals.margin_pct||0).toFixed(1) }}%</td>
            </tr>
          </tfoot>
        </table>
      </template>
      <div v-else class="empty-msg">Couldn't load this invoice.</div>
    </Modal>

    <!-- Trial Balance -->
    <div v-if="activeReport === 'tb'" class="books-card report-card">
      <div class="books-card-title">Trial Balance</div>
      <template v-if="tbLoading"><div class="loading-shimmer" style="height:200px;border-radius:8px"></div></template>
      <template v-else-if="tb?.length">
        <div class="tb-cards">
          <div v-for="row in tb" :key="row.account" class="tb-card">
            <div class="tb-card-top">
              <div class="tb-account-name">{{ row.account }}</div>
              <span class="badge badge-muted" style="font-size:10.5px">{{ row.account_type }}</span>
            </div>
            <div class="tb-buckets">
              <div class="tb-bucket">
                <span class="bucket-label">Opening</span>
                <span class="bucket-val mono-sm" :class="row.opening<0?'red':''">{{ fmtAmt(row.opening||0) }}</span>
              </div>
              <div class="tb-bucket">
                <span class="bucket-label">Debit</span>
                <span class="bucket-val mono-sm green">{{ fmtAmt(row.debit||0) }}</span>
              </div>
              <div class="tb-bucket">
                <span class="bucket-label">Credit</span>
                <span class="bucket-val mono-sm red">{{ fmtAmt(row.credit||0) }}</span>
              </div>
              <div class="tb-bucket">
                <span class="bucket-label">Closing</span>
                <span class="bucket-val mono-sm fw-600" :class="row.closing<0?'red':'green'">{{ fmtAmt(row.closing||0) }}</span>
              </div>
            </div>
          </div>
        </div>
      </template>
      <div v-else class="empty-msg">Run the report to see results.</div>
    </div>

    <!-- Stock vs GL Reconciliation -->
    <div v-if="activeReport === 'stockgl'" class="books-card report-card">
      <div class="books-card-title">Stock Ledger vs Inventory GL</div>
      <div style="font-size:11.5px;color:#94a3b8;margin-bottom:12px">
        Compares the operational Stock Ledger (Bin valuation) against the financial General Ledger
        (Inventory Asset account balance). These are two independently-maintained ledgers — this
        check is the tripwire that catches drift immediately instead of at year-end audit.
      </div>
      <template v-if="stockGlLoading"><div class="loading-shimmer" style="height:160px;border-radius:8px"></div></template>
      <template v-else-if="stockGl">
        <div class="bs-balance-check" :class="stockGl.is_reconciled ? 'bs-ok' : 'bs-bad'">
          <span class="bs-bc-icon">{{ stockGl.is_reconciled ? '✓' : '✕' }}</span>
          Bin Stock Value = Inventory GL Balance
          <span class="bs-bc-eq">{{ fmt(stockGl.total_bin_value) }} vs {{ fmt(stockGl.total_gl_balance) }}
            <template v-if="!stockGl.is_reconciled"> (diff {{ fmt(stockGl.total_difference) }})</template>
          </span>
        </div>

        <div v-if="stockGl.grir_account" style="margin-top:12px;font-size:12.5px;color:#64748b">
          Stock Received (GR/IR): <span class="mono-sm fw-600">{{ fmt(stockGl.grir_balance) }}</span>
          <span style="color:#94a3b8"> — goods received, awaiting bill. Nonzero is normal.</span>
        </div>

        <table v-if="stockGl.accounts?.length" class="books-table aging-table" style="width:100%;margin-top:16px">
          <thead>
            <tr>
              <th>Inventory Account</th>
              <th class="ta-r">Bin Stock Value</th>
              <th class="ta-r">GL Balance</th>
              <th class="ta-r">Difference</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in stockGl.accounts" :key="row.account">
              <td>{{ row.account }}</td>
              <td class="ta-r mono-sm">{{ fmt(row.bin_stock_value) }}</td>
              <td class="ta-r mono-sm">{{ fmt(row.gl_balance) }}</td>
              <td class="ta-r mono-sm" :class="row.is_reconciled ? '' : 'text-danger fw-700'">{{ fmt(row.difference) }}</td>
              <td><span class="badge" :class="row.is_reconciled ? 'badge-blue' : 'badge-danger'">{{ row.is_reconciled ? 'OK' : 'DRIFT' }}</span></td>
            </tr>
          </tbody>
        </table>

        <div v-if="stockGl.items?.length" style="margin-top:20px">
          <div class="books-card-title" style="font-size:13px;margin-bottom:10px">Item-level Bin Detail</div>
          <table class="books-table aging-table" style="width:100%">
            <thead>
              <tr>
                <th>Item</th>
                <th>Warehouse</th>
                <th class="ta-r">Qty</th>
                <th class="ta-r">Valuation Rate</th>
                <th class="ta-r">Stock Value</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in stockGl.items" :key="row.item_code + row.warehouse">
                <td>{{ row.item_name || row.item_code }}</td>
                <td>{{ row.warehouse }}</td>
                <td class="ta-r mono-sm">{{ fmtN(row.actual_qty) }}</td>
                <td class="ta-r mono-sm">{{ fmtAmt(row.valuation_rate) }}</td>
                <td class="ta-r mono-sm">{{ fmtAmt(row.stock_value) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <div v-else class="empty-msg">{{stockGlRan ? 'No stock on hand for this company.' : 'Run the report to see results.'}}</div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { useFrappeCall, formatCurrency } from "../composables/useFrappe.js";
import { apiGET, resolveCompany } from "../api/client.js";
import Modal from "../components/Modal.vue";

const fmt    = formatCurrency;
const fmtAmt = (v) => v != null ? "₹" + Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "—";
const fmtN   = (v) => Number(v||0).toLocaleString("en-IN", { maximumFractionDigits: 0 });

const today    = new Date();
const fromDate = ref(new Date(today.getFullYear(), today.getMonth(), 1).toISOString().slice(0,10));
const toDate   = ref(today.toISOString().slice(0,10));
const activeReport = ref("pl");

const { data: pl,  loading: plLoading,  execute: loadPl  } = useFrappeCall("zoho_books_clone.db.queries.get_profit_and_loss");
const { data: bs,  loading: bsLoading,  execute: loadBs  } = useFrappeCall("zoho_books_clone.db.queries.get_balance_sheet_totals");
const { data: cf,  loading: cfLoading,  execute: loadCf  } = useFrappeCall("zoho_books_clone.db.queries.get_cash_flow");
const { data: vat, loading: vatLoading, execute: loadVat } = useFrappeCall("zoho_books_clone.db.queries.get_vat_summary");
const { data: tb,  loading: tbLoading,  execute: loadTb  } = useFrappeCall("zoho_books_clone.db.queries.get_trial_balance");

const arAging  = ref([]);
const apAging  = ref([]);
const plMonthly = ref([]);
const arLoading = ref(false);
const apLoading = ref(false);
const arRan = ref(false);
const apRan = ref(false);

const itemSales   = ref([]);
const itemsLoading = ref(false);
const itemsRan     = ref(false);

const customerSales   = ref([]);
const customersLoading = ref(false);
const customersRan     = ref(false);

const profitReport   = ref([]);
const profitLoading  = ref(false);
const profitRan      = ref(false);

const invoiceProfit        = ref([]);
const invoiceProfitLoading = ref(false);
const invoiceProfitRan     = ref(false);
const selectedInvoices     = ref(new Set());

const invoiceDetailOpen    = ref(false);
const invoiceDetailLoading = ref(false);
const invoiceDetail        = ref(null);
async function openInvoiceDetail(invoiceName) {
  invoiceDetailOpen.value = true;
  invoiceDetailLoading.value = true;
  invoiceDetail.value = null;
  try {
    invoiceDetail.value = await apiGET("zoho_books_clone.db.queries.get_invoice_profit_detail", { invoice: invoiceName });
  } catch {
    invoiceDetail.value = null;
  }
  invoiceDetailLoading.value = false;
}

const stockGl        = ref(null);
const stockGlLoading = ref(false);
const stockGlRan     = ref(false);

const bsBalanced = computed(() => {
  if (!bs.value) return false;
  const a = Number(bs.value.total_assets) || 0;
  const l = Number(bs.value.total_liabilities) || 0;
  const e = Number(bs.value.total_equity) || 0;
  return Math.abs(a - (l + e)) < 1;
});
const maxMonthlyVal = computed(() => Math.max(...plMonthly.value.flatMap(m => [m.income||0, m.expense||0]), 1));
function barH(v) { return Math.round((Math.max(0,v) / maxMonthlyVal.value) * 80); }

const profitTotal = computed(() => profitReport.value.filter(r => r.cost_rate).reduce((s,r) => s + Number(r.profit||0), 0));
const profitMarginTotal = computed(() => {
  const priced = profitReport.value.filter(r => r.cost_rate);
  const revenue = priced.reduce((s,r) => s + Number(r.revenue||0), 0);
  const profit = priced.reduce((s,r) => s + Number(r.profit||0), 0);
  return revenue !== 0 ? (profit / revenue) * 100 : 0;
});
const noCostDataCount = computed(() => profitReport.value.filter(r => !r.cost_rate).length);

const invoiceProfitSelectedRows = computed(() =>
  invoiceProfit.value.filter(r => selectedInvoices.value.has(r.invoice))
);
const invoiceProfitAllSelected = computed(() =>
  invoiceProfit.value.length > 0 && selectedInvoices.value.size === invoiceProfit.value.length
);
function toggleInvoiceSelection(invoice) {
  const s = new Set(selectedInvoices.value);
  if (s.has(invoice)) s.delete(invoice); else s.add(invoice);
  selectedInvoices.value = s;
}
function toggleAllInvoiceSelection() {
  selectedInvoices.value = invoiceProfitAllSelected.value
    ? new Set()
    : new Set(invoiceProfit.value.map(r => r.invoice));
}
function sumField(rows, field) { return rows.reduce((s, r) => s + Number(r[field] || 0), 0); }
const invoiceProfitTotals = computed(() => ({
  revenue: sumField(invoiceProfit.value, "revenue"),
  total_cost: sumField(invoiceProfit.value, "total_cost"),
  profit: sumField(invoiceProfit.value, "profit"),
}));
const invoiceProfitSelectedTotals = computed(() => ({
  count: invoiceProfitSelectedRows.value.length,
  revenue: sumField(invoiceProfitSelectedRows.value, "revenue"),
  total_cost: sumField(invoiceProfitSelectedRows.value, "total_cost"),
  profit: sumField(invoiceProfitSelectedRows.value, "profit"),
}));

async function runReport() {
  const company = await resolveCompany();
  const args = { company, from_date: fromDate.value, to_date: toDate.value };
  if (activeReport.value === "pl") {
    await loadPl(args);
    try {
      plMonthly.value = await apiGET("zoho_books_clone.db.queries.get_pl_monthly_breakdown", args) || [];
    } catch { plMonthly.value = []; }
  }
  if (activeReport.value === "bs")  await loadBs({ company, as_of_date: toDate.value });
  if (activeReport.value === "cf")  await loadCf(args);
  if (activeReport.value === "vat") await loadVat(args);
  if (activeReport.value === "tb")  await loadTb(args);
  if (activeReport.value === "ar") {
    arLoading.value = true; arRan.value = true;
    try { arAging.value = await apiGET("zoho_books_clone.db.queries.get_ar_aging", { company, as_of_date: toDate.value }) || []; }
    catch { arAging.value = []; }
    arLoading.value = false;
  }
  if (activeReport.value === "ap") {
    apLoading.value = true; apRan.value = true;
    try { apAging.value = await apiGET("zoho_books_clone.db.queries.get_ap_aging", { company, as_of_date: toDate.value }) || []; }
    catch { apAging.value = []; }
    apLoading.value = false;
  }
  if (activeReport.value === "items") {
    itemsLoading.value = true; itemsRan.value = true;
    try { itemSales.value = await apiGET("zoho_books_clone.db.queries.get_item_wise_sales", args) || []; }
    catch { itemSales.value = []; }
    itemsLoading.value = false;
  }
  if (activeReport.value === "customers") {
    customersLoading.value = true; customersRan.value = true;
    try { customerSales.value = await apiGET("zoho_books_clone.db.queries.get_customer_wise_sales", args) || []; }
    catch { customerSales.value = []; }
    customersLoading.value = false;
  }
  if (activeReport.value === "profit") {
    profitLoading.value = true; profitRan.value = true;
    try { profitReport.value = await apiGET("zoho_books_clone.db.queries.get_profit_wise_report", args) || []; }
    catch { profitReport.value = []; }
    profitLoading.value = false;
  }
  if (activeReport.value === "invoice_profit") {
    invoiceProfitLoading.value = true; invoiceProfitRan.value = true;
    selectedInvoices.value = new Set();
    try { invoiceProfit.value = await apiGET("zoho_books_clone.db.queries.get_invoice_wise_profit", args) || []; }
    catch { invoiceProfit.value = []; }
    invoiceProfitLoading.value = false;
  }
  if (activeReport.value === "stockgl") {
    stockGlLoading.value = true; stockGlRan.value = true;
    try { stockGl.value = await apiGET("zoho_books_clone.db.queries.get_inventory_reconciliation", { company }) || null; }
    catch { stockGl.value = null; }
    stockGlLoading.value = false;
  }
}

function exportItemSalesCSV() {
  const header = ["Item","UOM","Invoices","Qty Sold","Avg Rate","Discount","Total Amount"].join(",");
  const lines = itemSales.value.map(r =>
    [r.item_name || r.item_code, r.uom || "", r.invoice_count, r.qty_sold, r.avg_rate, r.total_discount || 0, r.total_amount].join(",")
  );
  const csv = [header, ...lines].join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "item_wise_sales_" + fromDate.value + "_to_" + toDate.value + ".csv";
  a.click();
  URL.revokeObjectURL(url);
}

function exportCustomerSalesCSV() {
  const header = ["Customer","Invoices","Net Total","Discount","Tax","Avg Invoice","Outstanding","Total Amount"].join(",");
  const lines = customerSales.value.map(r =>
    [r.customer_name || r.customer, r.invoice_count, r.net_total, r.total_discount || 0, r.total_tax, r.avg_invoice_value, r.outstanding_amount || 0, r.total_amount].join(",")
  );
  const csv = [header, ...lines].join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "customer_wise_sales_" + fromDate.value + "_to_" + toDate.value + ".csv";
  a.click();
  URL.revokeObjectURL(url);
}

function exportProfitCSV() {
  const header = ["Item","Qty Sold","Revenue","Cost Rate","Total Cost","Profit","Margin %"].join(",");
  const lines = profitReport.value.map(r =>
    [r.item_name || r.item_code, r.qty_sold, r.revenue, r.cost_rate, r.total_cost, r.profit, Number(r.margin_pct||0).toFixed(1)].join(",")
  );
  const csv = [header, ...lines].join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "profit_wise_report_" + fromDate.value + "_to_" + toDate.value + ".csv";
  a.click();
  URL.revokeObjectURL(url);
}

function exportInvoiceProfitCSV() {
  const header = ["Invoice","Date","Customer","Revenue","Est. Cost","Profit","Margin %"].join(",");
  const rows = invoiceProfitSelectedRows.value.length ? invoiceProfitSelectedRows.value : invoiceProfit.value;
  const lines = rows.map(r =>
    [r.invoice, r.posting_date, r.customer_name || r.customer, r.revenue, r.total_cost, r.profit, Number(r.margin_pct||0).toFixed(1)].join(",")
  );
  const csv = [header, ...lines].join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "invoice_profitability_" + fromDate.value + "_to_" + toDate.value + ".csv";
  a.click();
  URL.revokeObjectURL(url);
}

function exportAgingCSV() {
  const isAR = activeReport.value === "ar";
  const rows = isAR ? arAging.value : apAging.value;
  const nameCol = isAR ? "Customer" : "Vendor";
  const keyCol  = isAR ? "customer_name" : "supplier_name";
  const header = [nameCol,"Current","1-30 Days","31-60 Days","61-90 Days","90+ Days","Total"].join(",");
  const lines = rows.map(r =>
    [r[keyCol]||r[isAR?'customer':'supplier'], r.current, r.days_1_30, r.days_31_60, r.days_61_90, r.days_90_plus, r.total]
      .join(",")
  );
  const csv = [header, ...lines].join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = (isAR ? "ar_aging" : "ap_aging") + "_" + toDate.value + ".csv";
  a.click();
  URL.revokeObjectURL(url);
}

const reports = [
  { key: "pl",  label: "Profit & Loss",  icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/></svg>` },
  { key: "bs",  label: "Balance Sheet",  icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="18" rx="2"/><line x1="8" y1="3" x2="8" y2="21"/></svg>` },
  { key: "cf",  label: "Cash Flow",      icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 1l4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><path d="M7 23l-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>` },
  { key: "vat", label: "VAT Summary",    icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>` },
  { key: "items", label: "Item-wise Sales", icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.59 13.41L13.42 20.58a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>` },
  { key: "customers", label: "Customer-wise Sales", icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>` },
  { key: "profit", label: "Profit-wise", icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>` },
  { key: "invoice_profit", label: "Invoice Profitability", icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="9" y1="17" x2="15" y2="17"/><line x1="9" y1="13" x2="12" y2="13"/></svg>` },
  { key: "ar",  label: "AR Aging",       icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>` },
  { key: "ap",  label: "AP Aging",       icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 8 14"/></svg>` },
  { key: "tb",  label: "Trial Balance",  icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>` },
  { key: "stockgl", label: "Stock vs GL", icon: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>` },
];
</script>

<style scoped>
.row-selected { background: #F8F9FF; }
.inv-detail-link { color: var(--accent, #4C6EF5); text-decoration: none; font-weight: 600; }
.inv-detail-link:hover { text-decoration: underline; }
.page-reports { display: flex; flex-direction: column; gap: 16px; padding: 24px; }
.report-tabs  { display: flex; gap: 8px; flex-wrap: wrap; }
.report-tab {
  display: flex; align-items: center; gap: 7px;
  padding: 8px 16px; border-radius: var(--radius-sm);
  border: 1px solid var(--border); background: var(--surface);
  color: var(--text-3); cursor: pointer; font-size: 13px; font-weight: 600;
  transition: all .15s; font-family: var(--font);
}
.report-tab:hover { border-color: var(--accent); color: var(--text); }
.report-tab.active { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }

.date-range-bar {
  display: flex; align-items: center; gap: 12px; padding: 14px 20px; flex-wrap: wrap;
}
.dr-label { font-size: 12px; font-family: var(--font); color: var(--text-3); letter-spacing: .06em; }
.dr-input {
  background: var(--surface-2); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 6px 10px; color: var(--text);
  font-size: 12.5px; font-family: var(--font); outline: none;
}
.dr-input:focus { border-color: var(--accent); }

.pl-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 0; border-bottom: 1px solid var(--border); font-size: 14px;
}
.pl-row.net { border-bottom: none; font-size: 16px; font-weight: 700; margin-top: 4px; }
.pl-row.profit .mono { color: var(--green); }
.pl-row.loss   .mono { color: var(--red);   }
.pl-divider { height: 2px; background: var(--border); margin: 4px 0; }

.bs-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
@media (max-width: 700px) { .bs-grid { grid-template-columns: 1fr; } }
.bs-block { background: var(--surface-2); border-radius: var(--radius-sm); padding: 18px; }
.bs-section-title { font-size: 10.5px; letter-spacing: .1em; text-transform: uppercase; color: var(--text-3); margin-bottom: 10px; }
.assets .bs-amount    { color: var(--accent); font-size: 20px; font-weight: 700; }
.liabilities .bs-amount { color: var(--red);    font-size: 20px; font-weight: 700; }
.equity .bs-amount    { color: var(--amber);  font-size: 20px; font-weight: 700; }
.bs-eq-sub { display:flex; gap:10px; flex-wrap:wrap; margin-top:6px; font-size:11px; color:#94a3b8; }
.bs-balance-check {
  margin-top: 14px; display:flex; align-items:center; gap:8px; flex-wrap:wrap;
  padding: 10px 14px; border-radius: 8px; font-size: 12.5px; font-weight: 600;
}
.bs-balance-check.bs-ok  { background:#f0fdf4; color:#15803d; border:1px solid #bbf7d0; }
.bs-balance-check.bs-bad { background:#fef2f2; color:#b91c1c; border:1px solid #fecaca; }
.bs-bc-icon { font-weight:800; }
.bs-bc-eq { margin-left:auto; font-weight:500; opacity:.85; }

.cf-rows { display: flex; flex-direction: column; gap: 0; }
.cf-row { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid var(--border); font-size: 14px; }
.cf-row.net { border-bottom: none; font-weight: 700; font-size: 15px; margin-top: 4px; }
.cf-row.cf-sub { font-size: 12.5px; color: #64748b; padding: 6px 0; border-bottom: none; }
.cf-hint { font-size: 11px; color: #94a3b8; font-weight: 400; margin-left: 4px; }

.aging-table th, .aging-table td { padding: 9px 12px; white-space: nowrap; }
.aging-total { background: #F8F9FA; }
.aging-totals-row td { border-top: 2px solid #E2E8F0; background: #F8F9FA; }

/* GST Cards */
.gst-cards { display: flex; flex-direction: column; gap: 10px; }
.gst-card { background: var(--surface-2); border-radius: var(--radius-sm); padding: 14px 16px; }
.gst-card-header { margin-bottom: 10px; }
.gst-card-body { display: flex; flex-direction: column; gap: 6px; }
.gst-kv { display: flex; justify-content: space-between; align-items: center; font-size: 13px; }
.gst-kv-label { color: var(--text-3); font-size: 12px; }
.gst-kv-value { font-weight: 600; }

/* Aging Cards */
.aging-cards { display: flex; flex-direction: column; gap: 10px; }
.aging-card {
  background: var(--surface-2); border-radius: var(--radius-sm);
  padding: 14px 16px; border: 1px solid var(--border);
}
.aging-card-totals { border: 2px solid var(--border); background: #F8F9FA; }
.aging-card-name { font-size: 13.5px; font-weight: 600; color: var(--text); margin-bottom: 10px; }
.aging-buckets { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; margin-bottom: 10px; }
@media (max-width: 600px) { .aging-buckets { grid-template-columns: repeat(2, 1fr); } }
.aging-bucket { display: flex; flex-direction: column; gap: 3px; }
.bucket-label { font-size: 10.5px; color: var(--text-3); text-transform: uppercase; letter-spacing: .05em; }
.bucket-val { font-size: 13px; }
.aging-card-total {
  display: flex; justify-content: space-between; align-items: center;
  padding-top: 10px; border-top: 1px solid var(--border); font-size: 13px;
}

/* Trial Balance Cards */
.tb-cards { display: flex; flex-direction: column; gap: 10px; }
.tb-card {
  background: var(--surface-2); border-radius: var(--radius-sm);
  padding: 14px 16px; border: 1px solid var(--border);
}
.tb-card-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; margin-bottom: 12px; }
.tb-account-name { font-size: 13px; font-weight: 600; color: var(--text); line-height: 1.4; }
.tb-buckets { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
@media (max-width: 500px) { .tb-buckets { grid-template-columns: repeat(2, 1fr); } }
.tb-bucket { display: flex; flex-direction: column; gap: 3px; }
.text-warn   { color: #E67700; }
.text-danger { color: #C92A2A; }
.fw-600 { font-weight: 600; }
.fw-700 { font-weight: 700; }

.mono-sm  {font-size: 13px; }
.green    { color: var(--green); }
.red      { color: var(--red);   }
.ta-r     { text-align: right; }
.empty-msg { text-align: center; padding: 32px; color: var(--text-3); font-size: 13px; }

.badge { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 10px; font-size: 11.5px; font-weight: 600; }
.badge-blue   { background: #E7F5FF; color: #1971C2; }
.badge-muted  { background: #F1F3F5; color: #868E96; }
.badge-danger { background: #FFF5F5; color: #C92A2A; }
.badge-orange { background: #FFF4E6; color: #D9480F; }
.badge-green  { background: #EBFBEE; color: #2B8A3E; }

@media (max-width: 768px) {
  .date-range-bar { padding: 12px 14px; gap: 8px; }
  .report-card { overflow-x: auto; }
}
@media (max-width: 480px) {
  .page-reports { padding: 12px; gap: 12px; }
  .dr-input { width: 100%; }
}
</style>