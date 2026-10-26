<script setup lang="ts">
/**
 * 品牌标记：六爻既济，第二爻为朱色「变爻」。
 * 纯几何、无字，双线边栏取篆刻意；随主题切换线条与边框色。
 */
withDefaults(defineProps<{ size?: number; tile?: 'auto' | 'ink' | 'none' }>(), {
  size: 38,
  tile: 'auto',
})
</script>

<template>
  <svg
    class="brand-mark"
    :class="'brand-mark--' + tile"
    :width="size"
    :height="size"
    viewBox="0 0 40 40"
    aria-hidden="true"
    focusable="false"
  >
    <rect v-if="tile !== 'none'" class="brand-mark__tile" x="0.5" y="0.5" width="39" height="39" rx="9.5" />
    <rect class="brand-mark__rule" x="3.8" y="3.8" width="32.4" height="32.4" rx="7" />
    <g class="brand-mark__yao">
      <rect x="9" y="8.85" width="9.5" height="2.8" rx="1.4" />
      <rect x="21.5" y="8.85" width="9.5" height="2.8" rx="1.4" />
      <rect x="9" y="12.75" width="22" height="2.8" rx="1.4" />
      <rect x="9" y="16.65" width="9.5" height="2.8" rx="1.4" />
      <rect x="21.5" y="16.65" width="9.5" height="2.8" rx="1.4" />
      <rect x="9" y="20.55" width="22" height="2.8" rx="1.4" />
      <rect x="9" y="24.45" width="9.5" height="2.8" rx="1.4" />
      <rect x="21.5" y="24.45" width="9.5" height="2.8" rx="1.4" />
      <rect x="9" y="28.35" width="22" height="2.8" rx="1.4" />
    </g>
    <rect class="brand-mark__moving" x="9" y="12.75" width="22" height="2.8" rx="1.4" />
  </svg>
</template>

<style scoped>
.brand-mark { display: block; flex: 0 0 auto; overflow: visible; }
.brand-mark__tile { fill: var(--surface-2); stroke: var(--line-strong); stroke-width: .7; }
.brand-mark__rule { fill: none; stroke: var(--bronze); stroke-width: .9; opacity: .34; }
.brand-mark__yao rect { fill: var(--text-1); }
.brand-mark__moving { fill: var(--accent); }

/* 墨玉底：线条换成铜金，变爻提亮 */
.brand-mark--ink .brand-mark__tile { fill: var(--shell-bg); stroke: var(--shell-line); }
.brand-mark--ink .brand-mark__rule { stroke: var(--shell-bronze); opacity: .4; }
.brand-mark--ink .brand-mark__yao rect { fill: var(--shell-bronze); }
.brand-mark--ink .brand-mark__moving { fill: #c4785f; }

/* 无底：直接落在纸面或墨面，只保留线条 */
.brand-mark--none .brand-mark__yao rect { fill: currentColor; }
.brand-mark--none .brand-mark__moving { fill: var(--accent); }
</style>
