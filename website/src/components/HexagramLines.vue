<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{ binary: string; size?: 'sm' | 'md' | 'lg' }>(), {
  size: 'sm',
})

// binary[0] = 初爻 (bottom), binary[5] = 上爻 (top). Rendered top-to-bottom.
const lines = computed(() => {
  const out: ('yang' | 'yin')[] = []
  for (let i = 5; i >= 0; i--) out.push(props.binary.charAt(i) === '1' ? 'yang' : 'yin')
  return out
})
</script>

<template>
  <div class="yao" :class="'yao--' + size" aria-hidden="true">
    <span v-for="(l, i) in lines" :key="i" class="yao__row" :class="'yao__row--' + l">
      <i class="yao__seg" />
      <i v-if="l === 'yin'" class="yao__gap" />
      <i class="yao__seg" />
    </span>
  </div>
</template>

<style scoped>
.yao { display: flex; flex-direction: column; gap: 2px; color: currentColor; }
.yao__row { display: flex; align-items: center; width: 100%; }
.yao__row--yang { justify-content: center; }
.yao__row--yin { justify-content: center; }
.yao__seg { height: 3px; border-radius: 2px; background: currentColor; flex: 0 1 100%; }
.yao__row--yin .yao__seg { flex: 0 1 42%; }
.yao__gap { flex: 0 0 16%; }

.yao--sm .yao__seg { height: 2px; border-radius: 1px; }
.yao--md .yao__seg { height: 4px; }
.yao--lg .yao__seg { height: 6px; border-radius: 3px; }
.yao--lg { gap: 4px; }
</style>
