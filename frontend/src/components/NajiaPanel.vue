<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import type { Divination, NajiaChart, NajiaInput, NajiaLine, NajiaOptions, NajiaRuleModule } from '../types'
import { najiaLineName, najiaStatusTags, readableNajiaResults } from '../najiaPresentation'

const props = defineProps<{ divination: Divination | null }>()
const emit = defineEmits<{ startCasting: [] }>()

const options = ref<NajiaOptions | null>(null)
const dayGanzhi = ref('甲子')
const monthBranch = ref('子')
const timestampSource = ref<'manual' | 'automatic'>('manual')
const localDateTime = ref('')
const timezone = ref('Asia/Shanghai')
const analysisEnabled = ref({ use_god: false, time_relations: false, branch_relations: false, moving_changes: false })
const questionCategory = ref('')
const manualUseGodCandidate = ref('')
const chart = ref<NajiaChart | null>(null)
const loading = ref(false)
const saving = ref(false)

const rows = computed(() => {
  if (!chart.value) return []
  return [...chart.value.base.lines].sort((a, b) => b.position - a.position).map((base) => ({
    base,
    changed: chart.value!.changed.lines.find((line) => line.position === base.position)!,
    statusTags: najiaStatusTags(base, chart.value!.rule_analysis),
  }))
})

watch(() => props.divination?.id, () => {
  chart.value = props.divination?.najia_chart ?? null
  if (chart.value) {
    dayGanzhi.value = chart.value.day_ganzhi
    monthBranch.value = chart.value.month_branch
    timestampSource.value = chart.value.timestamp_source
    analysisEnabled.value = { ...(chart.value.rule_analysis?.enabled ?? analysisEnabled.value) }
    questionCategory.value = chart.value.rule_analysis?.question_category ?? ''
    manualUseGodCandidate.value = chart.value.rule_analysis?.manual_use_god_candidate ?? ''
    if (chart.value.calendar_context) {
      localDateTime.value = chart.value.calendar_context.local_datetime
      timezone.value = chart.value.calendar_context.timezone
    }
  } else {
    timestampSource.value = 'manual'
    localDateTime.value = ''
  }
}, { immediate: true })

onMounted(async () => {
  loading.value = true
  try {
    const [loadedOptions, preferences] = await Promise.all([api.najiaOptions(), api.preferences()])
    options.value = loadedOptions
    if (!chart.value?.calendar_context) timezone.value = preferences.timezone
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取干支选项失败。')
  } finally {
    loading.value = false
  }
})

async function createChart() {
  if (!props.divination?.id) {
    ElMessage.warning('请先完成起卦，再生成排盘。')
    return
  }
  saving.value = true
  try {
    const input: NajiaInput = timestampSource.value === 'manual'
      ? { source: 'manual' as const, day_ganzhi: dayGanzhi.value, month_branch: monthBranch.value }
      : { source: 'automatic' as const, local_datetime: localDateTime.value, timezone: timezone.value.trim() }
    input.analysis = {
      enabled: { ...analysisEnabled.value },
      question_category: analysisEnabled.value.use_god ? questionCategory.value || null : null,
      manual_use_god_candidate: analysisEnabled.value.use_god ? manualUseGodCandidate.value.trim() || null : null,
    }
    chart.value = await api.createNajiaChart(props.divination.id, input)
    ElMessage.success('六爻排盘已生成并保存到这条历史记录。')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '排盘失败，请检查干支输入。')
  } finally {
    saving.value = false
  }
}

function lineLabel(position: number) {
  return najiaLineName(position)
}

function glyph(line: NajiaLine) {
  return line.yin_yang === '阳' ? '━━━━━━' : '━━━　━━━'
}

function hiddenText(line: NajiaLine) {
  if (!line.hidden_relative) return '—'
  return `${line.hidden_relative} ${line.hidden_stem}${line.hidden_branch}${line.hidden_element}`
}

const analysisModules = computed(() => Object.entries(chart.value?.rule_analysis?.modules ?? {})
  .flatMap(([key, module]) => module ? [{ key, module: module as NajiaRuleModule }] : []))

function prettyResults(module: NajiaRuleModule) {
  return JSON.stringify(module.results, null, 2)
}
</script>

<template>
  <section class="panel najia-panel" aria-label="六爻纳甲排盘">
    <div class="section-heading section-heading--compact">
      <div><span class="section-index">03</span><h2>六爻排盘</h2></div>
      <span v-if="chart" class="najia-panel__palace">{{ chart.palace }}宫 · {{ chart.palace_element }} · {{ chart.palace_position }}</span>
    </div>

    <p class="najia-panel__intro">自动模式按选定 IANA 时区计算日干支，并按 UTC+08 节气交接确定月建；也可保留手动输入。自动计算不覆盖原始卦象。</p>
    <el-radio-group v-model="timestampSource" class="najia-source-toggle" aria-label="历法输入方式">
      <el-radio-button value="automatic">自动历法</el-radio-button>
      <el-radio-button value="manual">手动输入</el-radio-button>
    </el-radio-group>
    <div class="najia-controls">
      <template v-if="timestampSource === 'manual'">
        <label>日干支
        <el-select v-model="dayGanzhi" filterable :loading="loading" aria-label="选择日干支">
          <el-option v-for="value in options?.day_ganzhi_options ?? []" :key="value" :value="value" :label="value" />
        </el-select>
        </label>
        <label>月建地支
        <el-select v-model="monthBranch" :loading="loading" aria-label="选择月建地支">
          <el-option v-for="value in options?.month_branches ?? []" :key="value" :value="value" :label="`${value}月`" />
        </el-select>
        </label>
      </template>
      <template v-else>
        <label>所选时区的本地日期时间
          <el-input v-model="localDateTime" type="datetime-local" step="1" aria-label="所选时区本地日期时间" />
        </label>
        <label>IANA 时区
          <el-input v-model="timezone" aria-label="IANA 时区" placeholder="例如 Asia/Shanghai" />
        </label>
      </template>
      <el-button type="primary" :loading="saving" :disabled="!props.divination" @click="createChart">生成 / 更新排盘</el-button>
    </div>

    <details class="najia-analysis-options">
      <summary>传统规则分析选项</summary>
      <p>规则分别启停，只输出带文献来源的结构信息；不自动判断吉凶、应期或现实事件。</p>
      <div class="najia-analysis-options__grid">
        <el-checkbox v-model="analysisEnabled.use_god">用神候选辅助</el-checkbox>
        <el-checkbox v-model="analysisEnabled.time_relations">月建、日辰与旬空关系</el-checkbox>
        <el-checkbox v-model="analysisEnabled.branch_relations">地支六合、六冲</el-checkbox>
        <el-checkbox v-model="analysisEnabled.moving_changes">动爻与变爻关系</el-checkbox>
      </div>
      <div v-if="analysisEnabled.use_god" class="najia-analysis-options__inputs">
        <label>占问类别
          <el-select v-model="questionCategory" clearable placeholder="不按类别筛选">
            <el-option value="parent_elder_document" label="父母、长辈、房屋或文书" />
            <el-option value="sibling" label="兄弟姐妹或同辈" />
            <el-option value="wealth_spouse" label="配偶、财物或求财" />
            <el-option value="descendant_student" label="子女、晚辈或门生" />
            <el-option value="official_career" label="功名、官府或妻占夫" />
            <el-option value="medicine" label="医药（只映射典籍类别）" />
          </el-select>
        </label>
        <label>手动指定候选（可选）
          <el-input v-model="manualUseGodCandidate" placeholder="例如 line:2 或 hidden:3" />
        </label>
      </div>
    </details>

    <template v-if="chart">
      <section class="najia-summary" aria-label="排盘摘要">
        <article><span>起卦时间</span><strong>{{ chart.calendar_context?.local_datetime ?? '手动干支输入' }}</strong><small>{{ chart.calendar_context?.timezone ?? '未使用自动时间计算' }}</small></article>
        <article><span>日干支</span><strong>{{ chart.day_ganzhi }}</strong><small>日支 {{ chart.day_ganzhi[1] }}</small></article>
        <article><span>月建</span><strong>{{ chart.month_branch }}月</strong><small>按当前排盘参数</small></article>
        <article><span>旬空</span><strong>{{ chart.xunkong.join('、') }}</strong><small>按日干支记录</small></article>
        <article><span>本卦 → 变卦</span><strong>{{ props.divination?.base_hexagram.title ?? chart.base.hexagram_title }} → {{ props.divination?.changed_hexagram.title ?? chart.changed.hexagram_title }}</strong><small>卦象保持原始起卦结果</small></article>
        <article><span>卦宫 · 世应</span><strong>{{ chart.palace }}宫 · {{ chart.palace_element }}</strong><small>世 {{ lineLabel(chart.world_position) }} · 应 {{ lineLabel(chart.response_position) }}</small></article>
      </section>
      <details v-if="chart.calendar_context" class="najia-calendar-context">
        <summary>查看历法计算依据与版本</summary>
        <div class="najia-calendar-context__details">
          <span>本地时间：{{ chart.calendar_context.local_datetime }} {{ chart.calendar_context.timezone }}（UTC{{ chart.calendar_context.utc_offset }}）</span>
          <span>对应时刻：{{ chart.calendar_context.utc_instant }} · 节气参考时区 {{ chart.calendar_context.jieqi_reference_timezone }}</span>
          <span>{{ chart.calendar_context.day_rule }}{{ chart.calendar_context.month_rule }}</span>
          <small>{{ chart.calendar_context.engine }} {{ chart.calendar_context.engine_version }} · tzdata {{ chart.calendar_context.timezone_database_version }} · {{ chart.calendar_context.ruleset_id }}@{{ chart.calendar_context.ruleset_version }}</small>
        </div>
      </details>
      <div class="najia-board-heading">
        <div><span>六爻排盘</span><small>上爻在上，初爻在下</small></div>
        <span>起卦数据 · {{ chart.timestamp_source === 'automatic' ? '自动历法' : '手动干支' }}</span>
      </div>
      <div class="najia-table-scroll" role="region" aria-label="六爻排盘表，可横向滚动" tabindex="0">
        <table class="najia-table">
          <thead>
            <tr>
              <th scope="col">爻位</th><th scope="col">六神</th><th scope="col">伏神</th><th scope="col">六亲</th><th scope="col">本卦爻象</th><th scope="col">地支 · 五行</th><th scope="col">世应与状态</th><th scope="col">变爻</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.base.position" :class="{ 'najia-table__row--moving': row.base.moving }" :aria-label="`${lineLabel(row.base.position)}，${row.base.relative}，${row.base.branch}${row.base.element}`">
              <th scope="row">{{ lineLabel(row.base.position) }}</th>
              <td class="najia-table__spirit">{{ row.base.spirit }}</td>
              <td>{{ hiddenText(row.base) }}</td>
              <td><strong>{{ row.base.relative }}</strong></td>
              <td class="najia-table__glyph">{{ glyph(row.base) }}</td>
              <td><strong>{{ row.base.stem }}{{ row.base.branch }}</strong><small>{{ row.base.element }}行</small></td>
              <td class="najia-table__statuses">
                <span v-for="tag in row.statusTags" :key="tag.label" class="najia-tag" :class="`najia-tag--${tag.kind}`">{{ tag.label }}</span>
                <span v-if="!row.statusTags.length" class="najia-status-none">无特殊标记</span>
              </td>
              <td class="najia-table__changed"><strong>{{ row.changed.relative }}</strong><span>{{ row.changed.stem }}{{ row.changed.branch }} · {{ row.changed.element }}行</span><span class="najia-table__glyph">{{ glyph(row.changed) }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="najia-source-note">{{ chart.rules_note }}</p>
      <div class="najia-sources">
        <a v-for="source in chart.sources" :key="source.revision_id" :href="source.url" target="_blank" rel="noreferrer">
          {{ source.scope }} · {{ source.title }}（修订 {{ source.revision_id }}）
        </a>
      </div>
      <section v-if="analysisModules.length" class="najia-analysis-results" aria-label="传统规则分析结果">
        <div class="section-heading section-heading--compact"><div><span class="section-index">分</span><h2>规则分析</h2></div><span>规则版本 {{ chart.rule_analysis?.ruleset.version }}</span></div>
        <article v-for="entry in analysisModules" :key="entry.key" class="najia-analysis-card">
          <template v-if="entry.module">
          <h3>{{ entry.module.module }}</h3>
          <p>{{ entry.module.explanation }}</p>
          <div v-if="readableNajiaResults(entry.key, entry.module).length" class="najia-analysis-card__items">
            <div v-for="item in readableNajiaResults(entry.key, entry.module)" :key="`${item.label}-${item.detail}`" class="najia-analysis-card__item">
              <strong>{{ item.label }}</strong><span>{{ item.detail }}</span>
            </div>
          </div>
          <div v-if="entry.module.matched_rules.length" class="najia-analysis-card__matches">
            <span v-for="rule in entry.module.matched_rules" :key="rule.id">{{ rule.name }}</span>
          </div>
          <details class="najia-analysis-card__advanced"><summary>高级信息 · 原始计算数据</summary><pre>{{ prettyResults(entry.module) }}</pre></details>
          <a v-for="source in entry.module.sources" :key="source.revision_id" :href="source.url" target="_blank" rel="noreferrer">{{ source.title }}（修订 {{ source.revision_id }}）</a>
          </template>
        </article>
      </section>
    </template>
    <div v-else class="najia-empty">
      <span class="najia-empty__mark">六爻</span>
      <strong>{{ props.divination ? '排盘尚未生成' : '先起一卦，再生成排盘' }}</strong>
      <p>{{ props.divination ? '选择自动历法，或输入日干支与月建，然后生成 / 更新排盘。' : '起卦后可查看六神、纳甲、世应和带来源的关系分析。' }}</p>
      <el-button v-if="!props.divination" plain @click="emit('startCasting')">前往起卦</el-button>
    </div>
  </section>
</template>
