import { describe, expect, it } from 'vitest'
import { specialLineForCast } from './specialLine'
import type { DivinationLine, Hexagram } from './types'

function makeHexagram(order: number, name: '用九' | '用六' | null): Hexagram {
  return {
    wenwang_order: order,
    name: order === 1 ? '乾' : order === 2 ? '坤' : '姤',
    title: order === 1 ? '乾为天' : order === 2 ? '坤为地' : '天风姤',
    binary_code: '000000',
    upper_trigram: { name: '乾', symbol: '☰', binary_code: '111', image: '天' },
    lower_trigram: { name: '乾', symbol: '☰', binary_code: '111', image: '天' },
    judgment: '',
    line_texts: ['', '', '', '', '', ''],
    source_revision_id: null,
    special_line: name ? { name, text: `${name}：原文`, source_url: 'https://example.test' } : null,
    text_source: '',
    source_url: '',
  }
}

function makeLines(value: number): DivinationLine[] {
  return Array.from({ length: 6 }, (_, index) => ({
    position: index + 1,
    value,
    yin_yang: value === 6 || value === 8 ? '阴' : '阳',
    changing: value === 6 || value === 9,
    coins: null,
  }))
}

describe('specialLineForCast', () => {
  it('shows 用九 only for six old-yang lines of Qian', () => {
    expect(specialLineForCast(makeHexagram(1, '用九'), makeLines(9))?.name).toBe('用九')
  })

  it('shows 用六 only for six old-yin lines of Kun', () => {
    expect(specialLineForCast(makeHexagram(2, '用六'), makeLines(6))?.name).toBe('用六')
  })

  it('does not show special texts for other hexagrams or incomplete matches', () => {
    expect(specialLineForCast(makeHexagram(44, null), makeLines(9))).toBeNull()
    expect(specialLineForCast(makeHexagram(1, '用九'), [...makeLines(9).slice(0, 5), { ...makeLines(7)[5], position: 6 }])).toBeNull()
    expect(specialLineForCast(makeHexagram(2, '用六'), [...makeLines(6).slice(0, 5)])).toBeNull()
  })
})
