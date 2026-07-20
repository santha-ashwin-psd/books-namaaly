<template>
  <div class="dep-chart">
    <div class="dep-chart-legend">
      <span class="dep-legend-item"><span class="dep-legend-swatch swatch-bar"></span>Depreciation</span>
      <span class="dep-legend-item"><span class="dep-legend-swatch swatch-line"></span>Book Value (WDV)</span>
    </div>
    <svg :viewBox="`0 0 ${w} ${h}`" class="dep-svg" preserveAspectRatio="xMidYMid meet">
      <!-- gridlines -->
      <line
        v-for="g in gridLines"
        :key="'g' + g.y"
        :x1="padL" :x2="w - padR" :y1="g.y" :y2="g.y"
        class="dep-grid"
      />
      <text
        v-for="g in gridLines"
        :key="'gl' + g.y"
        :x="padL - 8" :y="g.y + 4"
        class="dep-axis-label dep-axis-y"
      >{{ g.label }}</text>

      <!-- x axis labels -->
      <text
        v-for="(lab, i) in xLabels"
        :key="'x' + i"
        :x="barCenters[i]" :y="h - padB + 18"
        class="dep-axis-label dep-axis-x"
      >{{ lab }}</text>

      <!-- bars (depreciation) -->
      <rect
        v-for="(row, i) in rows"
        :key="'b' + i"
        :x="barCenters[i] - barW / 2"
        :y="yScale(row.depreciation_amount)"
        :width="barW"
        :height="Math.max(0, chartBottom - yScale(row.depreciation_amount))"
        rx="3"
        class="dep-bar"
      >
        <title>{{ 'Year ' + row.year + ' — Depreciation ' + fmt(row.depreciation_amount) }}</title>
      </rect>

      <!-- line (closing / book value) -->
      <polyline
        :points="linePoints"
        class="dep-line"
        fill="none"
      />
      <circle
        v-for="(row, i) in rows"
        :key="'c' + i"
        :cx="barCenters[i]"
        :cy="yScale(row.closing_value)"
        r="3.5"
        class="dep-dot"
      >
        <title>{{ 'Year ' + row.year + ' — Book Value ' + fmt(row.closing_value) }}</title>
      </circle>
    </svg>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { fmt } from "../utils/format.js";

const props = defineProps({
  rows: { type: Array, default: () => [] },
});

const w = 640;
const h = 260;
const padL = 56;
const padR = 16;
const padT = 16;
const padB = 34;
const chartBottom = h - padB;
const chartTop = padT;

const maxValue = computed(() => {
  let m = 0;
  for (const r of props.rows) {
    m = Math.max(m, Number(r.depreciation_amount) || 0, Number(r.closing_value) || 0);
  }
  return m || 1;
});

const yScale = (v) => {
  const t = (Number(v) || 0) / maxValue.value;
  return chartBottom - t * (chartBottom - chartTop);
};

const gridLines = computed(() => {
  const ticks = 4;
  const lines = [];
  for (let i = 0; i <= ticks; i++) {
    const val = (maxValue.value / ticks) * i;
    lines.push({ y: yScale(val), label: fmt(val) });
  }
  return lines;
});

const barCenters = computed(() => {
  const n = props.rows.length || 1;
  const usable = w - padL - padR;
  const step = usable / n;
  return props.rows.map((_, i) => padL + step * (i + 0.5));
});

const barW = computed(() => {
  const n = props.rows.length || 1;
  const step = (w - padL - padR) / n;
  return Math.max(6, Math.min(36, step * 0.5));
});

const xLabels = computed(() => props.rows.map((r) => "Y" + r.year));

const linePoints = computed(() =>
  props.rows
    .map((r, i) => `${barCenters.value[i]},${yScale(r.closing_value)}`)
    .join(" ")
);
</script>

<style scoped>
.dep-chart {
  width: 100%;
}
.dep-chart-legend {
  display: flex;
  gap: 18px;
  margin-bottom: 6px;
  font-size: 12px;
  color: #6b7280;
}
.dep-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.dep-legend-swatch {
  width: 14px;
  height: 10px;
  border-radius: 2px;
  display: inline-block;
}
.swatch-bar { background: #93c5fd; }
.swatch-line { background: #2563eb; border-radius: 50%; width: 10px; height: 10px; }
.dep-svg {
  width: 100%;
  height: auto;
  display: block;
}
.dep-grid {
  stroke: #eef2f7;
  stroke-width: 1;
}
.dep-axis-label {
  fill: #9ca3af;
  font-size: 10px;
}
.dep-axis-y {
  text-anchor: end;
}
.dep-axis-x {
  text-anchor: middle;
}
.dep-bar {
  fill: #93c5fd;
  transition: fill 0.15s;
}
.dep-bar:hover { fill: #60a5fa; }
.dep-line {
  stroke: #2563eb;
  stroke-width: 2;
}
.dep-dot {
  fill: #2563eb;
  stroke: #fff;
  stroke-width: 1.5;
}
</style>