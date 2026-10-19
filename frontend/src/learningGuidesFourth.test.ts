import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { createSSRApp } from 'vue'
import { renderToString } from '@vue/server-renderer'
import guides from './data/learning_guides.json'
import catalog from '../../backend/data/hexagrams.json'
import { reviewedGuide } from './learning'
import LearningReader from './components/LearningReader.vue'
import type { Hexagram, LearningGuide } from './types'

const batch = guides.filter((g) => g.hexagram_id >= 13 && g.hexagram_id <= 16)
const audit = readFileSync(
  new URL('../../docs/learning-guides-review-13-16.md', import.meta.url), 'utf8',
)
const han = (s: string) => [...s.matchAll(/\p{Script=Han}/gu)].length

describe('fourth learning batch 13-16 stays unpublished until human review', () => {
  it('preserves King Wen order and all prior reviewed/draft statuses', () => {
    expect(guides.map((g) => g.hexagram_id)).toEqual(Array.from({length:16},(_,i)=>i+1))
    expect(new Set(guides.map((g) => g.hexagram_id)).size).toBe(guides.length)
    expect(batch.map((g) => g.hexagram_id)).toEqual([13, 14, 15, 16])
    for (const guide of guides) {
      expect(guide.review_status).toBe(guide.hexagram_id <= 4 ? 'reviewed' : 'draft')
      expect(reviewedGuide(guide.hexagram_id)?.hexagram_id).toBe(
        guide.hexagram_id <= 4 ? guide.hexagram_id : undefined,
      )
    }
    for (let id = 17; id <= 64; id++) expect(reviewedGuide(id)).toBeUndefined()
  })
  it('keeps 4 original sources, complete line notes and audit synchronization', () => {
    for (const guide of batch) {
      expect(guide.review_status).toBe('draft')
      expect(guide.editorial_version).toBe('learning-v1-13-16-draft.1')
      expect(Object.keys(guide.line_guides)).toEqual(['1', '2', '3', '4', '5', '6'])
      expect(han(guide.one_liner)).toBeGreaterThanOrEqual(15)
      expect(han(guide.one_liner)).toBeLessThanOrEqual(30)
      expect(han(guide.overview)).toBeGreaterThanOrEqual(200)
      expect(han(guide.overview)).toBeLessThanOrEqual(350)
      const original = catalog[guide.hexagram_id - 1]!
      expect(guide.references).toHaveLength(3)
      expect(guide.references[0]!.url).toBe(original.source_url)
      expect(guide.references[0]!.title).toContain(String(original.source_revision_id))
      for (const term of [guide.one_liner, guide.overview, original.judgment,
        ...original.line_texts, ...guide.references.map((source) => source.url)]) {
        expect(audit).toContain(term)
      }
      for (const text of Object.values(guide.line_guides)) {
        expect(han(text)).toBeGreaterThanOrEqual(60)
        expect(han(text)).toBeLessThanOrEqual(120)
        expect(audit).toContain(text)
      }
      for (const ref of guide.references) expect(new URL(ref.url).hostname).toBe('zh.wikisource.org')
    }
    expect(audit).toContain('弗克攻')
  })
  it('does not reveal any of the four drafts or their summaries in real reader', async () => {
    for (const guide of batch) {
      const original = catalog[guide.hexagram_id - 1] as Hexagram
      const html = await renderToString(createSSRApp(LearningReader, { hexagram: original, guide }))
      expect(html).toContain('导读整理中')
      expect(html).toContain(original.judgment)
      expect(html).not.toContain(guide.one_liner)
      expect(html).not.toContain(guide.overview)
      for (const note of Object.values(guide.line_guides)) expect(html).not.toContain(note)
    }
  })
  it('supports an in-memory reviewed copy while leaving source drafts unchanged', async () => {
    for (const source of batch) {
      const copy: LearningGuide = { ...source, review_status: 'reviewed' }
      const html = await renderToString(createSSRApp(LearningReader, {
        hexagram: catalog[source.hexagram_id - 1] as Hexagram, guide: copy,
      }))
      expect(html).toContain(source.one_liner)
      expect(html).toContain(source.overview)
      for (const ref of source.references) expect(html).toContain(ref.title)
      expect(source.review_status).toBe('draft')
    }
  })
})
