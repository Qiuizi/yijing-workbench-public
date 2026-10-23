import { describe, expect, it } from 'vitest'
import { createSSRApp } from 'vue'
import { renderToString } from '@vue/server-renderer'
import catalog from '../../backend/data/hexagrams.json'
import { filterHexagrams, reviewedGuide } from './learning'
import { parseRoute } from './navigation'
import HexagramGlyph from './components/HexagramGlyph.vue'

describe('read-only learning', () => {
  it('finds every King Wen entry by number, including padded numbers', () => {
    for (let id = 1; id <= 64; id++) {
      expect(
        filterHexagrams(catalog, String(id).padStart(2, '0'), 'all').map(
          (entry) => entry.wenwang_order,
        ),
      ).toEqual([id])
    }
    expect(filterHexagrams(catalog, '乾为天', 'all')[0]?.wenwang_order).toBe(1)
    expect(filterHexagrams(catalog, '不存在', 'all')).toEqual([])
    expect(filterHexagrams(catalog, '', 'upper')).toHaveLength(30)
    expect(filterHexagrams(catalog, '', 'lower')).toHaveLength(34)
    expect(filterHexagrams(catalog, '64', 'upper')).toEqual([])
    expect(reviewedGuide(1)?.hexagram_id).toBe(1)
    expect(reviewedGuide(5)?.hexagram_id).toBe(5)
    expect(reviewedGuide(64)?.hexagram_id).toBe(64)
  })
  it('renders all six lines in the source direction, including asymmetric hexagrams', async () => {
    for (const entry of catalog) {
      const html = await renderToString(
        createSSRApp(HexagramGlyph, {
          code: entry.binary_code,
          label: entry.title,
          compact: true,
        }),
      )
      expect(
        [...html.matchAll(/data-position="(\d)"/g)].map((match) => match[1]),
      ).toEqual(['6', '5', '4', '3', '2', '1'])
      expect(
        [...html.matchAll(/data-polarity="([阴阳])"/g)].map(
          (match) => match[1],
        ),
      ).toEqual(
        entry.binary_code.split('').map((bit) => (bit === '1' ? '阳' : '阴')),
      )
    }
  })
  it('supports direct links and safely handles invalid routes', () => {
    expect(parseRoute('#/learning/64')).toEqual({
      page: 'learning',
      hexagramId: 64,
    })
    expect(parseRoute('#/history')).toEqual({
      page: 'history',
      hexagramId: null,
    })
    expect(parseRoute('#/learning/65')).toEqual({
      page: 'learning',
      hexagramId: null,
    })
    expect(parseRoute('#/unknown')).toEqual({
      page: 'divination',
      hexagramId: null,
    })
  })
})
