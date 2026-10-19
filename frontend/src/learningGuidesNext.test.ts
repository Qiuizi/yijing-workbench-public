import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { createSSRApp } from 'vue'
import { renderToString } from '@vue/server-renderer'
import guides from './data/learning_guides.json'
import catalog from '../../backend/data/hexagrams.json'
import { reviewedGuide } from './learning'
import LearningReader from './components/LearningReader.vue'
import type { Hexagram, LearningGuide } from './types'

const draftGuides = guides.filter((guide) => guide.hexagram_id >= 5 && guide.hexagram_id <= 8)
const doc = readFileSync(
  new URL('../../docs/learning-guides-review-05-08.md', import.meta.url),
  'utf8',
)
const hanLength = (text: string) => [...text.matchAll(/\p{Script=Han}/gu)].length

describe('second learning batch: four unpublished editorial drafts', () => {
  it('contains exactly the four next King Wen entries with 24 full explanations', () => {
    expect(guides.map((guide) => guide.hexagram_id)).toEqual([1, 2, 3, 4, 5, 6, 7, 8])
    expect(draftGuides.map((guide) => guide.hexagram_id)).toEqual([5, 6, 7, 8])
    expect(new Set(guides.map((guide) => guide.hexagram_id)).size).toBe(8)
    for (const guide of draftGuides) {
      expect(guide.review_status).toBe('draft')
      expect(guide.editorial_version).toBe('learning-v1-05-08-draft.1')
      expect(Object.keys(guide.line_guides)).toEqual(['1', '2', '3', '4', '5', '6'])
      expect(hanLength(guide.one_liner)).toBeGreaterThanOrEqual(15)
      expect(hanLength(guide.one_liner)).toBeLessThanOrEqual(30)
      expect(hanLength(guide.overview)).toBeGreaterThanOrEqual(200)
      expect(hanLength(guide.overview)).toBeLessThanOrEqual(350)
      for (const explanation of Object.values(guide.line_guides)) {
        expect(hanLength(explanation)).toBeGreaterThanOrEqual(60)
        expect(hanLength(explanation)).toBeLessThanOrEqual(120)
      }
      expect(doc).toContain(guide.one_liner)
      expect(doc).toContain(guide.overview)
      const original = catalog[guide.hexagram_id - 1]!
      expect(doc).toContain(original.judgment)
      for (const line of original.line_texts) expect(doc).toContain(line)
      expect(guide.references[0]?.url).toBe(original.source_url)
      for (const reference of guide.references) {
        expect(doc).toContain(reference.url)
        expect(new URL(reference.url).hostname).toBe('zh.wikisource.org')
      }
      for (const explanation of Object.values(guide.line_guides)) expect(doc).toContain(explanation)
    }
  })

  it('continues to show approved first four while hiding drafts 5-8 and all remaining entries', () => {
    for (let id = 1; id <= 4; id++) expect(reviewedGuide(id)?.hexagram_id).toBe(id)
    for (let id = 5; id <= 64; id++) expect(reviewedGuide(id)).toBeUndefined()
  })

  it('keeps 5-8 in original-only reader mode even when a draft is passed directly', async () => {
    for (const source of draftGuides) {
      const original = catalog[source.hexagram_id - 1] as Hexagram
      const hidden: LearningGuide = { ...source, review_status: 'draft' }
      const html = await renderToString(createSSRApp(LearningReader, {
        hexagram: original, guide: hidden,
      }))
      expect(html).toContain('导读整理中')
      expect(html).toContain(original.judgment)
      expect(html).not.toContain(source.one_liner)
      expect(html).not.toContain(source.overview)
      for (const explanation of Object.values(source.line_guides)) expect(html).not.toContain(explanation)
    }
  })

  it('can render a reviewed test copy without approving any source entry', async () => {
    for (const source of draftGuides) {
      const testCopy: LearningGuide = { ...source, review_status: 'reviewed' }
      const original = catalog[source.hexagram_id - 1] as Hexagram
      const html = await renderToString(createSSRApp(LearningReader, {
        hexagram: original, guide: testCopy,
      }))
      expect(html).toContain(source.one_liner)
      expect(html).toContain(source.overview)
      for (const reference of source.references) expect(html).toContain(reference.title)
      expect(source.review_status).toBe('draft')
    }
  })
})
