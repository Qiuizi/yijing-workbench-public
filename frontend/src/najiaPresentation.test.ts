import { describe, expect, it } from 'vitest'
import { najiaLineName, najiaStatusTags, readableNajiaResults } from './najiaPresentation'
import type { NajiaLine, NajiaRuleAnalysis, NajiaRuleModule } from './types'

const line: NajiaLine = {
  position: 2, yin_yang: '阳', moving: true, stem: '甲', branch: '子', element: '水',
  relative: '父母', spirit: '青龙', role: '世', hidden_relative: null, hidden_stem: null,
  hidden_branch: null, hidden_element: null, flying_relative: null, xunkong: true, month_build: false,
}

function module(key: string, results: Record<string, unknown>): NajiaRuleModule {
  return {
    ruleset: { id: 'test', version: '1' }, module: key, inputs: {}, results,
    matched_rules: [], applied_rules: [], sources: [], explanation: '只展示规则记录。',
  }
}

describe('Najia presentation', () => {
  it('keeps line names in top-to-bottom board positions', () => {
    expect([6, 5, 4, 3, 2, 1].map(najiaLineName)).toEqual(['上爻', '五爻', '四爻', '三爻', '二爻', '初爻'])
  })

  it('projects existing role, motion, void, calendar and clash records into labeled tags', () => {
    const analysis = {
      enabled: { use_god: false, time_relations: true, branch_relations: true, moving_changes: false },
      question_category: null, manual_use_god_candidate: null,
      modules: {
        time_relations: module('日月及旬空关系', { lines: [{ position: 2, month_break: true, day_clash: true, month_branch_relation: '六合', day_branch_relation: null }] }),
        branch_relations: module('地支六合、六冲', { base_pair_matches: [{ positions: [2, 5], branches: ['子', '午'], relation: '六冲' }] }),
      },
    } as unknown as NajiaRuleAnalysis
    const labels = najiaStatusTags(line, analysis).map((tag) => tag.label)
    expect(labels).toEqual(['世', '动', '旬空', '月破', '日冲', '月合', '本卦六冲 · 五爻'])
  })

  it('turns time relation codes into readable line descriptions', () => {
    const result = readableNajiaResults('time_relations', module('日月及旬空关系', {
      lines: [{ position: 1, branch: '子', element: '水', month_element_relation: '比和', day_element_relation: 'source_generates_target', xunkong: true }],
    }))
    expect(result).toEqual([{ label: '初爻 · 子水', detail: '月：比和；日：月日五行生爻五行；旬空' }])
    expect(JSON.stringify(result)).not.toContain('source_generates_target')
  })

  it('shows an explicit no-moving-line result instead of an empty JSON block', () => {
    expect(readableNajiaResults('moving_changes', module('动爻与变爻对应关系', { transitions: [] }))).toEqual([
      { label: '动变关系', detail: '本卦没有动爻。' },
    ])
  })
})
