import type { Divination, Hexagram, NajiaChart } from './types'
import { najiaLineName, najiaStatusTags, readableNajiaResults } from './najiaPresentation'
import { specialLineForCast } from './specialLine'

// Export only named result fields, never serialize the whole record or settings.
function text(value: unknown): string {
  return typeof value === 'string' || typeof value === 'number' ? String(value) : ''
}

function md(value: unknown): string {
  return (text(value) || '未记录').replace(/\r\n?/g, '\n')
    .replace(/[\u0000-\u0008\u000b-\u001f\u007f]/g, '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/[\\`*_{}\[\]()#+.!|~-]/g, '\\$&')
}

function cell(value: unknown): string {
  return md(value).replace(/\n/g, '<br>')
}

function source(label: string, url: unknown, revision?: number | null): string {
  let link = '未记录有效来源链接'
  try {
    const parsed = new URL(text(url))
    if (parsed.protocol === 'https:' || parsed.protocol === 'http:') {
      const href = parsed.href.replace(/\(/g, '%28').replace(/\)/g, '%29')
      link = `[查看来源](${href})`
    }
  } catch { /* Missing legacy source: keep an explicit placeholder. */ }
  return `${md(label)}：${link}${revision != null ? `（修订 ${md(revision)}）` : ''}`
}

function table(headers: string[], rows: unknown[][]): string {
  const row = (values: unknown[]) => `| ${values.map(cell).join(' | ')} |`
  return [row(headers), `| ${headers.map(() => '---').join(' | ')} |`, ...rows.map(row)].join('\n')
}

function hexagramSection(label: string, hexagram: Hexagram | null | undefined): string {
  return `## ${label}：${cell(hexagram?.title)}\n\n${md(hexagram?.judgment)}\n\n${source('经文来源', hexagram?.source_url, hexagram?.source_revision_id)}`
}

function chartSection(chart: NajiaChart): string {
  const sections = ['## 已保存的六爻排盘', table(['项目', '记录值'], [
    ['卦宫', [chart.palace, chart.palace_element, chart.palace_position].filter(Boolean).join(' · ')],
    ['日干支', chart.day_ganzhi], ['月建', chart.month_branch], ['旬空', chart.xunkong?.join('、')],
    ['世爻', chart.world_position ? najiaLineName(chart.world_position) : null],
    ['应爻', chart.response_position ? najiaLineName(chart.response_position) : null],
    ['时间输入', chart.timestamp_source === 'automatic' ? '自动历法' : chart.timestamp_source === 'manual' ? '手动干支' : null],
  ])]
  if (chart.calendar_context) {
    const c = chart.calendar_context
    sections.push(table(['历法依据', '记录值'], [
      ['本地时间', c.local_datetime], ['时区', c.timezone], ['UTC 偏移', c.utc_offset],
      ['对应时刻', c.utc_instant], ['日界约定', c.day_rule], ['月建约定', c.month_rule],
      ['节气参考时区', c.jieqi_reference_timezone], ['历法引擎', `${c.engine} ${c.engine_version}`],
      ['时区数据库', `${c.timezone_database} ${c.timezone_database_version}`],
    ]))
  }
  sections.push('上爻在上，初爻在下。', table(
    ['爻位', '六神', '伏神', '六亲', '本卦阴阳', '纳甲五行', '世应与状态', '变爻'],
    [...(chart.base?.lines ?? [])].sort((a, b) => b.position - a.position).map((line) => {
      const changed = chart.changed?.lines?.find((item) => item.position === line.position)
      return [najiaLineName(line.position), line.spirit,
        line.hidden_relative ? [line.hidden_relative, line.hidden_stem, line.hidden_branch, line.hidden_element].filter(Boolean).join(' ') : '无',
        line.relative, line.yin_yang, [line.stem, line.branch, line.element].filter(Boolean).join(' '),
        najiaStatusTags(line, chart.rule_analysis).map((tag) => tag.label).join('、') || '无特殊标记',
        changed ? [changed.relative, changed.stem, changed.branch, changed.element, changed.yin_yang].filter(Boolean).join(' ') : null]
    }),
  ), md(chart.rules_note))
  for (const s of chart.sources ?? []) sections.push(source(`${s.scope} · ${s.title}`, s.url, s.revision_id))
  for (const [key, module] of Object.entries(chart.rule_analysis?.modules ?? {})) {
    if (!module) continue
    sections.push(`### ${cell(module.module)}`, md(module.explanation),
      `规则版本：${cell(module.ruleset?.id)} / ${cell(module.ruleset?.version)}`)
    const items = readableNajiaResults(key, module)
    if (items.length) sections.push(table(['分析项', '记录结果'], items.map((item) => [item.label, item.detail])))
    if (module.matched_rules?.length) sections.push(`匹配规则：${md(module.matched_rules.map((rule) => rule.name).join('、'))}`)
    for (const s of module.sources ?? []) sections.push(source(s.title, s.url, s.revision_id))
  }
  return sections.join('\n\n')
}

export function divinationMarkdown(record: Divination): string {
  const lines = record.lines ?? []
  const moving = record.moving_positions ?? []
  const sections = ['# 起卦记录', '## 占问', md(record.question), table(['项目', '记录值'], [
    ['起卦时间（原始记录）', record.created_at],
    ['起卦方式', record.method === 'coins' ? '铜钱起卦' : record.method === 'manual' ? '手动起卦' : null],
    ['本卦', record.base_hexagram?.title], ['动爻', !record.moving_positions ? null : moving.length ? moving.map(najiaLineName).join('、') : '本卦无动爻'],
    ['之卦', record.changed_hexagram?.title],
  ]), '## 原始爻值（初爻至上爻）', table(['爻位', '爻值', '阴阳', '动静', '铜钱结果'],
    [...lines].sort((a, b) => a.position - b.position).map((line) => [
      najiaLineName(line.position), line.value, line.yin_yang, line.changing ? '动' : '静', line.coins?.join('、'),
    ])), hexagramSection('本卦', record.base_hexagram), '### 本次动爻爻辞']
  if (!record.moving_positions) sections.push('动爻信息未记录。')
  else if (!moving.length) sections.push('本卦无动爻，此处不列爻辞。')
  for (const position of moving) sections.push(`#### ${najiaLineName(position)}`, md(record.base_hexagram?.line_texts?.[position - 1]))
  const special = record.base_hexagram ? specialLineForCast(record.base_hexagram, lines) : null
  if (special) sections.push(`### ${special.name}`, md(special.text), source('特殊爻辞来源', special.source_url))
  sections.push(hexagramSection('之卦', record.changed_hexagram))
  const reading = record.traditional_reading
  if (reading) {
    sections.push('## 本次传统取辞', md(reading.plain_rule_explanation))
    for (const passage of reading.passages ?? []) {
      sections.push(`### ${cell(passage.hexagram_title)} · ${cell(passage.label)}${passage.primary ? '（主参考）' : ''}`,
        md(passage.text), source('经文来源', passage.source_url, passage.source_revision_id))
    }
    sections.push(md(reading.interpretation_limit), `取辞体系：${cell(reading.ruleset_name)} / ${cell(reading.ruleset_version)}`,
      source(reading.source_title, reading.source_url, reading.source_revision_id))
  }
  sections.push(record.najia_chart ? chartSection(record.najia_chart) : '## 六爻排盘\n\n此记录暂无已保存排盘。')
  sections.push('---', '仅导出本条起卦记录及已保存排盘；不含 AI 会话、密钥或内部配置。未重新计算卦象。',
    '典籍转录适用独立来源许可（来源页面标注 CC BY-SA 4.0），不属于项目代码的 MIT 授权范围。')
  return `${sections.join('\n\n')}\n`
}

export function markdownFilename(record: Divination): string {
  // Prefix avoids Windows reserved device names, even if the question is CON.
  const clean = (value: string) => value.replace(/[<>:"/\\|?*\u0000-\u001f\u007f-\u009f\u202a-\u202e\u2066-\u2069]/g, '_')
    .replace(/\s+/g, ' ').replace(/[. ]+$/g, '').trim()
  const date = clean(record.created_at?.slice(0, 10) ?? '') || '时间未记录'
  const question = Array.from(clean(record.question ?? '')).slice(0, 50).join('').replace(/[. ]+$/g, '') || '未填写占问'
  return `起卦-${date}-${question}.md`
}
