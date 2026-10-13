import type { NajiaLine, NajiaRuleAnalysis, NajiaRuleModule } from './types'

export type NajiaTagKind = 'role' | 'moving' | 'void' | 'calendar' | 'break' | 'clash' | 'relation'

export interface NajiaStatusTag {
  label: string
  kind: NajiaTagKind
}

export interface NajiaAnalysisItem {
  label: string
  detail: string
}

const LINE_NAMES = ['初爻', '二爻', '三爻', '四爻', '五爻', '上爻']

export function najiaLineName(position: number): string {
  return LINE_NAMES[position - 1] ?? `${position}爻`
}

function records(module: NajiaRuleModule | undefined, key: string): Record<string, unknown>[] {
  const value = module?.results[key]
  return Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object') : []
}

function relationText(value: unknown): string {
  const labels: Record<string, string> = {
    比和: '比和',
    source_generates_target: '月日五行生爻五行',
    target_generates_source: '爻五行生月日五行',
    source_controls_target: '月日五行克爻五行',
    target_controls_source: '爻五行克月日五行',
  }
  return typeof value === 'string' ? labels[value] ?? value : '未记录'
}

export function najiaStatusTags(line: NajiaLine, analysis: NajiaRuleAnalysis | null | undefined): NajiaStatusTag[] {
  const tags: NajiaStatusTag[] = []
  if (line.role) tags.push({ label: line.role, kind: 'role' })
  if (line.moving) tags.push({ label: '动', kind: 'moving' })
  if (line.xunkong) tags.push({ label: '旬空', kind: 'void' })
  if (line.month_build) tags.push({ label: '月建', kind: 'calendar' })

  const timeModule = analysis?.modules.time_relations ?? undefined
  const timeLine = records(timeModule, 'lines').find((item) => item.position === line.position)
  if (timeLine?.month_break === true) tags.push({ label: '月破', kind: 'break' })
  if (timeLine?.day_clash === true) tags.push({ label: '日冲', kind: 'clash' })
  if (timeLine?.month_branch_relation === '六合') tags.push({ label: '月合', kind: 'relation' })
  if (timeLine?.day_branch_relation === '六合') tags.push({ label: '日合', kind: 'relation' })

  const branchModule = analysis?.modules.branch_relations ?? undefined
  for (const [key, scope] of [['base_pair_matches', '本卦'], ['changed_pair_matches', '之卦']] as const) {
    for (const item of records(branchModule, key)) {
      const positions = item.positions
      if (!Array.isArray(positions) || !positions.includes(line.position) || (item.relation !== '六合' && item.relation !== '六冲')) continue
      const other = positions.find((position) => position !== line.position)
      tags.push({ label: `${scope}${item.relation} · ${najiaLineName(Number(other))}`, kind: 'relation' })
    }
  }
  return tags.filter((tag, index) => tags.findIndex((candidate) => candidate.label === tag.label) === index)
}

export function readableNajiaResults(key: string, module: NajiaRuleModule): NajiaAnalysisItem[] {
  if (key === 'use_god') {
    const candidates = records(module, 'candidates')
    if (!candidates.length) return [{ label: '候选结果', detail: '未找到符合当前筛选条件的爻位；可以取消类别筛选或查看原排盘。' }]
    return candidates.map((candidate) => ({
      label: `${String(candidate.kind ?? '候选')} · ${najiaLineName(Number(candidate.position))}`,
      detail: `${String(candidate.relative ?? '六亲未记录')}　${String(candidate.stem ?? '')}${String(candidate.branch ?? '')}${String(candidate.element ?? '')}`,
    }))
  }

  if (key === 'time_relations') {
    return records(module, 'lines').map((line) => {
      const statuses = [
        line.month_break === true ? '月破' : '',
        line.day_clash === true ? '日冲' : '',
        line.xunkong === true ? '旬空' : '',
        line.month_branch_relation === '六合' ? '月合' : '',
        line.day_branch_relation === '六合' ? '日合' : '',
      ].filter(Boolean)
      const details = [
        `月：${relationText(line.month_element_relation)}`,
        `日：${relationText(line.day_element_relation)}`,
        ...statuses,
      ]
      return {
        label: `${najiaLineName(Number(line.position))} · ${String(line.branch ?? '')}${String(line.element ?? '')}`,
        detail: details.join('；'),
      }
    })
  }

  if (key === 'branch_relations') {
    const items: NajiaAnalysisItem[] = []
    for (const [pairsKey, scope] of [['base_pair_matches', '本卦'], ['changed_pair_matches', '之卦']] as const) {
      for (const pair of records(module, pairsKey)) {
        const positions = Array.isArray(pair.positions) ? pair.positions.map(Number) : []
        const branches = Array.isArray(pair.branches) ? pair.branches.map(String) : []
        if (positions.length !== 2 || branches.length !== 2) continue
        items.push({
          label: `${scope}${String(pair.relation ?? '地支关系')}`,
          detail: `${najiaLineName(positions[0])} ${branches[0]} · ${najiaLineName(positions[1])} ${branches[1]}`,
        })
      }
    }
    const base = module.results.base_hexagram_relation as Record<string, unknown> | undefined
    const changed = module.results.changed_hexagram_relation as Record<string, unknown> | undefined
    for (const [scope, relation] of [['本卦', base?.kind], ['之卦', changed?.kind]] as const) {
      if (typeof relation === 'string') items.unshift({ label: `${scope}整体结构`, detail: relation })
    }
    return items.length ? items : [{ label: '地支关系', detail: '当前结果中没有表列的六合或六冲配对。' }]
  }

  if (key === 'moving_changes') {
    const transitions = records(module, 'transitions')
    if (!transitions.length) return [{ label: '动变关系', detail: '本卦没有动爻。' }]
    return transitions.map((transition) => {
      const from = transition.from as Record<string, unknown> | undefined
      const to = transition.to as Record<string, unknown> | undefined
      const before = `${String(from?.relative ?? '')} ${String(from?.branch ?? '')}${String(from?.element ?? '')}`.trim()
      const after = `${String(to?.relative ?? '')} ${String(to?.branch ?? '')}${String(to?.element ?? '')}`.trim()
      const branch = transition.branch_relation ? `；地支${String(transition.branch_relation)}` : ''
      return {
        label: `${najiaLineName(Number(transition.position))} · 动变对应`,
        detail: `${before} → ${after}；五行${relationText(transition.element_relation)}${branch}`,
      }
    })
  }

  return []
}
