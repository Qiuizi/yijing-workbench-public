import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { createSSRApp } from 'vue'
import { renderToString } from '@vue/server-renderer'
import guides from './data/learning_guides.json'
import catalog from '../../backend/data/hexagrams.json'
import { reviewedGuide } from './learning'
import LearningReader from './components/LearningReader.vue'
import type { Hexagram, LearningGuide } from './types'

const thirdBatch = guides.filter((item) => item.hexagram_id >= 9 && item.hexagram_id <= 12)
const doc = readFileSync(new URL('../../docs/learning-guides-review-09-12.md', import.meta.url), 'utf8')
const han = (text: string) => [...text.matchAll(/\p{Script=Han}/gu)].length

describe('learning guides 09–12 draft and source integrity', () => {
  it('includes exactly four new complete and unapproved guides', () => {
    expect(guides.slice(0, 12).map((guide) => guide.hexagram_id)).toEqual(Array.from({ length: 12 }, (_, i) => i + 1))
    expect(thirdBatch.map((guide) => guide.hexagram_id)).toEqual([9, 10, 11, 12])
    expect(new Set(guides.map((guide) => guide.hexagram_id)).size).toBe(guides.length)
    for (const guide of thirdBatch) {
      const original = catalog[guide.hexagram_id - 1]!
      expect(['draft', 'reviewed']).toContain(guide.review_status)
      expect(guide.editorial_version).toBe('learning-v1-09-12-draft.1')
      expect(Object.keys(guide.line_guides)).toEqual(['1', '2', '3', '4', '5', '6'])
      expect(han(guide.one_liner)).toBeGreaterThanOrEqual(15)
      expect(han(guide.one_liner)).toBeLessThanOrEqual(30)
      expect(han(guide.overview)).toBeGreaterThanOrEqual(200)
      expect(han(guide.overview)).toBeLessThanOrEqual(350)
      expect(doc).toContain(guide.one_liner)
      expect(doc).toContain(guide.overview)
      expect(doc).toContain(original.judgment)
      for (const originalLine of original.line_texts) expect(doc).toContain(originalLine)
      for (const explanation of Object.values(guide.line_guides)) {
        expect(han(explanation)).toBeGreaterThanOrEqual(60)
        expect(han(explanation)).toBeLessThanOrEqual(120)
        expect(doc).toContain(explanation)
      }
      expect(guide.references).toHaveLength(3)
      expect(guide.references[0]!.url).toBe(original.source_url)
      expect(guide.references[0]!.title).toContain(String(original.source_revision_id))
      for (const ref of guide.references) {
        expect(new URL(ref.url).hostname).toBe('zh.wikisource.org')
        expect(doc).toContain(ref.url)
      }
    }
  })
  it('uses the current approval status in the application selector', () => {
    for (const guide of guides) {
      const expected = guide.review_status === 'reviewed' ? guide.hexagram_id : undefined
      expect(reviewedGuide(guide.hexagram_id)?.hexagram_id).toBe(expected)
    }
  })
  it('hides all four new draft guides even if directly passed as props', async () => {
    for (const guide of thirdBatch) {
      const hexagram = catalog[guide.hexagram_id - 1] as Hexagram
      const hidden: LearningGuide = { ...guide, review_status: 'draft' }
      const html = await renderToString(createSSRApp(LearningReader, { hexagram, guide: hidden }))
      expect(html).toContain('导读整理中')
      expect(html).toContain(hexagram.judgment)
      expect(html).not.toContain(guide.one_liner)
      expect(html).not.toContain(guide.overview)
      for (const note of Object.values(guide.line_guides)) expect(html).not.toContain(note)
    }
  })
  it('can render the four explanations only in an isolated reviewed test copy', async () => {
    for (const guide of thirdBatch) {
      const originalStatus = guide.review_status
      const copy: LearningGuide = { ...guide, review_status: 'reviewed' }
      const html = await renderToString(createSSRApp(LearningReader, {
        hexagram: catalog[guide.hexagram_id - 1] as Hexagram, guide: copy,
      }))
      expect(html).toContain(guide.one_liner)
      expect(html).toContain(guide.overview)
      for (const ref of guide.references) expect(html).toContain(ref.title)
      expect(guide.review_status).toBe(originalStatus)
    }
  })
})
