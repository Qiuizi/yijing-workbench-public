import { describe, expect, it } from 'vitest'
import { divinationMarkdown, markdownFilename } from './markdownExport'
import type { Divination, Hexagram, NajiaChart } from './types'

function record(): Divination {
  const hexagram: Hexagram = {
    wenwang_order: 1, name: '乾', title: '乾為天', binary_code: '111111',
    upper_trigram: { name: '乾', symbol: '☰', binary_code: '111', image: '天' },
    lower_trigram: { name: '乾', symbol: '☰', binary_code: '111', image: '天' },
    judgment: '测试卦辞，仅为合成示例。', line_texts: ['初爻示例', '二爻示例'],
    text_source: '合成示例', source_url: 'https://example.org/卦?oldid=1', source_revision_id: 1,
    special_line: { name: '用九', text: '特殊爻辞示例', source_url: 'https://example.org/用九' },
  }
  return {
    id: 123, question: '合成占问：如何安排阅读？', method: 'manual', created_at: '2026-10-16T08:00:00+08:00',
    lines: [{ position: 1, value: 9, yin_yang: '阳', changing: true, coins: null }],
    changed_lines: [], moving_positions: [1], base_hexagram: hexagram,
    changed_hexagram: { ...hexagram, title: '合成之卦' }, traditional_reading: null,
  }
}

describe('single-record Markdown', () => {
  it('exports Chinese, original time, moving texts and sources without changing the record', () => {
    const input = record()
    const before = JSON.stringify(input)
    const result = divinationMarkdown(input)
    expect(result).toContain('合成占问：如何安排阅读？')
    expect(result).toContain('2026\\-10\\-16T08:00:00\\+08:00')
    expect(result).toContain('手动起卦')
    expect(result).toContain('| 项目 | 记录值 |\n| --- | --- |')
    expect(result).toContain('## 本卦：乾為天')
    expect(result).toContain('## 之卦：合成之卦')
    expect(result).toContain('#### 初爻\n\n初爻示例')
    expect(result).not.toContain('二爻示例')
    expect(result).toContain('oldid=1')
    expect(result).not.toContain('特殊爻辞示例')
    expect(JSON.stringify(input)).toBe(before)
    expect(new TextDecoder().decode(new TextEncoder().encode(result))).toBe(result)
  })

  it('handles old records with absent fields without inventing time, notes or a chart', () => {
    const result = divinationMarkdown({} as Divination)
    expect(result).toContain('未记录')
    expect(result).toContain('动爻信息未记录')
    expect(result).toContain('暂无已保存排盘')
    expect(result).not.toMatch(/undefined|NaN|Invalid Date|## 备注/)
    const input = record()
    input.moving_positions = []
    expect(divinationMarkdown(input)).toContain('本卦无动爻，此处不列爻辞。')
  })

  it('escapes multiline Markdown and HTML, safely links sources, and preserves long text', () => {
    const input = record()
    input.question = '# 标题\n<script>alert(1)</script>\n[[私人链接]] | *内容* `代码` ' + '长文本'.repeat(5000)
    input.base_hexagram.title = '卦|名\n下一行'
    input.base_hexagram.source_url = 'https://example.org/a(b)?x=1'
    input.changed_hexagram.source_url = 'javascript:alert(1)'
    const result = divinationMarkdown(input)
    expect(result).toContain('\\# 标题')
    expect(result).toContain('&lt;script&gt;')
    expect(result).toContain('\\[\\[私人链接\\]\\] \\| \\*内容\\* \\`代码\\`')
    expect(result).toContain('卦\\|名<br>下一行')
    expect(result).toContain('https://example.org/a%28b%29?x=1')
    expect(result).toContain('长文本'.repeat(5000))
    expect(result).not.toContain('javascript:')
  })

  it('reuses existing special-line selection and saved traditional passages', () => {
    const input = record()
    input.lines = Array.from({ length: 6 }, (_, i) => ({ position: i + 1, value: 9, yin_yang: '阳', changing: true, coins: null }))
    input.traditional_reading = {
      ruleset_id: 'example', ruleset_version: '1', ruleset_name: '示例规则', source_title: '规则出处',
      source_url: 'https://example.org/rules', source_revision_id: 2, moving_count: 6,
      passages: [{ kind: 'special_line', hexagram_order: 1, hexagram_title: '乾為天', label: '用九', text: '已保存选文',
        line_position: null, primary: true, source_url: 'https://example.org/passage', source_revision_id: 3 }],
      rationale: '示例', plain_rule_explanation: '按已保存的取辞显示', interpretation_limit: '不另作断语',
    }
    const result = divinationMarkdown(input)
    expect(result).toContain('### 用九\n\n特殊爻辞示例')
    expect(result).toContain('已保存选文')
    expect(result).toContain('（主参考）')
    expect(result).toContain('https://example.org/passage')
    expect(result).toContain('不另作断语')
  })

  it('exports only saved chart fields in board order, tolerating a missing changed line', () => {
    const input = record()
    input.najia_chart = {
      palace: '乾', palace_element: '金', palace_position: '本宫', world_position: 6, response_position: 3,
      day_ganzhi: '甲子', month_branch: '子', xunkong: ['戌', '亥'], timestamp_source: 'manual', calendar_context: null,
      base: { lines: [2, 6].map((position) => ({ position, yin_yang: '阳', moving: position === 2, stem: '甲', branch: '子',
        element: '水', relative: '父母', spirit: '青龙', role: position === 6 ? '世' : null, xunkong: false, month_build: true })) },
      changed: { lines: [] }, sources: [], rules_note: '只展示保存结果',
    } as unknown as NajiaChart
    const result = divinationMarkdown(input)
    expect(result).toContain('甲子')
    expect(result).toContain('戌、亥')
    expect(result).toContain('青龙')
    expect(result).toContain('世、月建')
    expect(result).toContain('动、月建')
    expect(result.indexOf('| 上爻 | 青龙')).toBeLessThan(result.indexOf('| 二爻 | 青龙'))
    expect(result).toContain('只展示保存结果')
    expect(result).not.toContain('undefined')
  })

  it('never serializes AI sessions, unknown notes, credentials or unrelated configuration', () => {
    const input = Object.assign(record(), { api_key: 'SECRET_KEY_SENTINEL', ai_sessions: [{ model_id: 'PRIVATE_MODEL_SENTINEL' }],
      preferences: { value: 'PRIVATE_CONFIG_SENTINEL' }, notes: 'UNSUPPORTED_FIELD_SENTINEL' }) as Divination
    expect(divinationMarkdown(input)).not.toMatch(/SENTINEL/)
  })

  it('creates bounded Windows-safe names including reserved names, emoji and missing dates', () => {
    const input = record()
    input.question = 'CON<>:"/\\|?*\u0000\n' + '中文😀'.repeat(100)
    const name = markdownFilename(input)
    expect(name).toMatch(/^起卦-2026-10-16-CON/)
    expect(name).toMatch(/\.md$/)
    expect(name).not.toMatch(/[<>:"/\\|?*\u0000-\u001f]/)
    expect(name.length).toBeLessThan(150)
    expect(name).not.toMatch(/[\ud800-\udbff](?![\udc00-\udfff])/)
    input.question = '   ... '
    input.created_at = null
    expect(markdownFilename(input)).toBe('起卦-时间未记录-未填写占问.md')
  })
})
