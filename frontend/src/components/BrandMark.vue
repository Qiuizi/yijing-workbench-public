<script setup lang="ts">
/**
 * 品牌标记：六爻既济，第二爻为朱色「变爻」。
 * 与官网同形，双线边栏取篆刻意；随主题切换线条与底色。
 */
withDefaults(defineProps<{ size?: number; tile?: boolean }>(), {
  size: 36,
  tile: true,
})
</script>

<template>
  <svg
    class="brand-mark"
    :width="size"
    :height="size"
    viewBox="0 0 40 40"
    aria-hidden="true"
    focusable="false"
  >
    <rect v-if="tile" class="brand-mark__tile" x="0.5" y="0.5" width="39" height="39" rx="9.5" />
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
.brand-mark { display: block; flex: 0 0 auto; }
.brand-mark__tile { fill: var(--surface); stroke: var(--border-strong); stroke-width: .7; }
.brand-mark__rule { fill: none; stroke: var(--bronze); stroke-width: .9; opacity: .34; }
.brand-mark__yao rect { fill: var(--text-primary); }
.brand-mark__moving { fill: var(--accent); }
</style>
