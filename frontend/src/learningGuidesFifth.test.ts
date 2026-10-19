import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { createSSRApp } from 'vue'
import { renderToString } from '@vue/server-renderer'
import catalog from '../../backend/data/hexagrams.json'
import guides from './data/learning_guides.json'
import { reviewedGuide } from './learning'
import LearningReader from './components/LearningReader.vue'
import type { Hexagram, LearningGuide } from './types'

const batch = guides.filter((g) => g.hexagram_id >= 17 && g.hexagram_id <= 20)
const audit = readFileSync(new URL('../../docs/learning-guides-review-17-20.md', import.meta.url), 'utf8')
const han = (text: string) => [...text.matchAll(/\p{Script=Han}/gu)].length

describe('fifth batch editorial safety and content integrity (17–20)', () => {
  it('has 20 sequential entries: 4 public and 16 drafts', () => {
    expect(guides.map((g) => g.hexagram_id)).toEqual(Array.from({ length: 20 }, (_, i) => i + 1))
    expect(new Set(guides.map((g) => g.hexagram_id)).size).toBe(guides.length)
    expect(batch.map((g) => g.hexagram_id)).toEqual([17, 18, 19, 20])
    for (const guide of guides) {
      expect(guide.review_status).toBe(guide.hexagram_id <= 4 ? 'reviewed' : 'draft')
      expect(reviewedGuide(guide.hexagram_id)?.hexagram_id).toBe(
        guide.hexagram_id <= 4 ? guide.hexagram_id : undefined,
      )
    }
    for (let id = 21; id <= 64; id++) expect(reviewedGuide(id)).toBeUndefined()
  })
  it('keeps four complete drafts with individual original source references', () => {
    for (const guide of batch) {
      const original = catalog[guide.hexagram_id - 1]!
      expect(guide.review_status).toBe('draft')
      expect(guide.editorial_version).toBe('learning-v1-17-20-draft.1')
      expect(Object.keys(guide.line_guides)).toEqual(['1','2','3','4','5','6'])
      expect(han(guide.one_liner)).toBeGreaterThanOrEqual(15)
      expect(han(guide.one_liner)).toBeLessThanOrEqual(30)
      expect(han(guide.overview)).toBeGreaterThanOrEqual(200)
      expect(han(guide.overview)).toBeLessThanOrEqual(350)
      expect(guide.references).toHaveLength(3)
      expect(guide.references[0]!.url).toBe(original.source_url)
      expect(guide.references[0]!.title).toContain(String(original.source_revision_id))
      for (const text of [guide.one_liner, guide.overview, original.judgment,
        ...original.line_texts, ...guide.references.map((ref) => ref.url)]) expect(audit).toContain(text)
      for (const line of Object.values(guide.line_guides)) {
        expect(han(line)).toBeGreaterThanOrEqual(60)
        expect(han(line)).toBeLessThanOrEqual(120)
        expect(audit).toContain(line)
      }
      for (const ref of guide.references) expect(new URL(ref.url).hostname).toBe('zh.wikisource.org')
    }
  })
  it('never reveals new drafts in a direct article render', async () => {
    for (const guide of batch) {
      const original = catalog[guide.hexagram_id - 1] as Hexagram
      const html = await renderToString(createSSRApp(LearningReader, { hexagram: original, guide }))
      expect(html).toContain('导读整理中')
      expect(html).toContain(original.judgment)
      expect(html).not.toContain(guide.one_liner)
      expect(html).not.toContain(guide.overview)
      for (const line of Object.values(guide.line_guides)) expect(html).not.toContain(line)
    }
  })
  it('renders review copies without changing actual approval flags', async () => {
    for (const draft of batch) {
      const copy: LearningGuide = { ...draft, review_status: 'reviewed' }
      const html = await renderToString(createSSRApp(LearningReader, {
        hexagram: catalog[draft.hexagram_id - 1] as Hexagram, guide: copy,
      }))
      expect(html).toContain(draft.one_liner)
      expect(html).toContain(draft.overview)
      for (const ref of draft.references) expect(html).toContain(ref.title)
      expect(draft.review_status).toBe('draft')
    }
  })
})
