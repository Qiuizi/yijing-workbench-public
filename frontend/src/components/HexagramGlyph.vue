<script setup lang="ts">
import { computed } from 'vue'
import { toVisualLines } from '../lineView'
import type { DivinationLine } from '../types'
const props = withDefaults(
  defineProps<{
    code: string
    label: string
    lines?: DivinationLine[]
    movingPositions?: number[]
    compact?: boolean
  }>(),
  { movingPositions: () => [], compact: false },
)
const visualLines = computed(() =>
  toVisualLines(
    props.lines ??
      props.code
        .split('')
        .reverse()
        .map((bit, index) => ({
          position: index + 1,
          value: bit === '1' ? 7 : 8,
          yin_yang: bit === '1' ? '阳' : '阴',
          changing: false,
          coins: null,
        })),
  ),
)
</script>
<template>
  <div
    class="hexagram-glyph"
    :class="{ 'hexagram-glyph--compact': compact }"
    role="img"
    :aria-label="`${label}，上爻在上，初爻在下`"
  >
    <div
      v-for="line in visualLines"
      :key="line.position"
      class="gua-line-row"
      :class="{
        'gua-line-row--moving': movingPositions.includes(line.position),
      }"
      :data-position="line.position"
      :data-polarity="line.yinYang"
    >
      <span v-if="!compact" class="gua-line-row__label">{{
        ['', '初', '二', '三', '四', '五', '上'][line.position]
      }}</span>
      <span
        class="gua-line"
        :class="[
          line.yinYang === '阳' ? 'gua-line--yang' : 'gua-line--yin',
          line.changing ? 'gua-line--changing' : '',
        ]"
        ><i class="gua-line__segment"></i
        ><i v-if="line.yinYang === '阴'" class="gua-line__segment"></i
      ></span>
      <span v-if="!compact" class="gua-line-row__marker">{{
        movingPositions.includes(line.position) ? '动' : ''
      }}</span>
    </div>
  </div>
</template>
