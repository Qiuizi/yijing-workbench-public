import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { createSSRApp } from 'vue'
import { renderToString } from '@vue/server-renderer'
import catalog from '../../backend/data/hexagrams.json'
import guides from './data/learning_guides.json'
import { reviewedGuide } from './learning'
import LearningReader from './components/LearningReader.vue'
import type { Hexagram, LearningGuide } from './types'

const han = (text: string) => [...text.matchAll(/\p{Script=Han}/gu)].length
const newGuides = guides.filter((guide) => guide.hexagram_id >= 21)
const dossiers = new Map<number, string>()
for (const [from, to] of [[21, 32], [33, 44], [45, 56], [57, 64]]) {
  const text = readFileSync(
    new URL(`../../docs/learning-guides-review-${from}-${to}.md`, import.meta.url), 'utf8',
  )
  for (let id = from; id <= to; id++) dossiers.set(id, text)
}

describe('64-hexagram first-pass V1 learning content coverage', () => {
  it('includes every King Wen hexagram in canonical order, with distinct initial notes', () => {
    expect(guides.map((entry) => entry.hexagram_id))
      .toEqual(Array.from({ length: 64 }, (_, index) => index + 1))
    expect(new Set(guides.map((entry) => entry.hexagram_id)).size).toBe(64)
    expect(newGuides).toHaveLength(44)
    expect(newGuides.flatMap((guide) => Object.values(guide.line_guides))).toHaveLength(264)
    expect(new Set(newGuides.flatMap((guide) => Object.values(guide.line_guides))).size).toBe(264)
  })

  it('keeps exactly four published guides and sixty unpublished drafts', () => {
    for (const guide of guides) {
      expect(guide.review_status).toBe(guide.hexagram_id <= 4 ? 'reviewed' : 'draft')
      expect(reviewedGuide(guide.hexagram_id)?.hexagram_id).toBe(
        guide.hexagram_id <= 4 ? guide.hexagram_id : undefined,
      )
    }
  })

  it('validates canonical sources, drafts, editorial lengths and complete audit dossiers', () => {
    for (const guide of newGuides) {
      const original = catalog[guide.hexagram_id - 1]!
      const audit = dossiers.get(guide.hexagram_id)!
      expect(guide.review_status).toBe('draft')
      expect(guide.editorial_version).toBe('learning-v1-21-64-initial.1')
      expect(Object.keys(guide.line_guides)).toEqual(['1', '2', '3', '4', '5', '6'])
      expect(han(guide.one_liner)).toBeGreaterThanOrEqual(15)
      expect(han(guide.one_liner)).toBeLessThanOrEqual(30)
      expect(han(guide.overview)).toBeGreaterThanOrEqual(200)
      expect(han(guide.overview)).toBeLessThanOrEqual(350)
      expect(guide.references).toHaveLength(1)
      expect(guide.references[0]!.url).toBe(original.source_url)
      expect(guide.references[0]!.title).toContain(String(original.source_revision_id))
      expect(audit).toContain(guide.one_liner)
      expect(audit).toContain(guide.overview)
      expect(audit).toContain(original.judgment)
      expect(audit).toContain(original.source_url)
      for (const line of original.line_texts) expect(audit).toContain(line)
      for (const line of Object.values(guide.line_guides)) {
        expect(han(line)).toBeGreaterThanOrEqual(60)
        expect(han(line)).toBeLessThanOrEqual(120)
        expect(audit).toContain(line)
      }
    }
  })

  it('does not expose unreviewed text in the actual reading component', async () => {
    for (const guide of newGuides) {
      const original = catalog[guide.hexagram_id - 1] as Hexagram
      const html = await renderToString(createSSRApp(LearningReader, {
        hexagram: original, guide: guide as LearningGuide,
      }))
      expect(html).toContain('导读整理中')
      expect(html).toContain(original.judgment)
      expect(html).not.toContain(guide.one_liner)
      expect(html).not.toContain(guide.overview)
      for (const note of Object.values(guide.line_guides)) expect(html).not.toContain(note)
    }
  })

  it('can display isolated editorial review copies without writing approval flags', async () => {
    for (const originalGuide of newGuides) {
      const testCopy: LearningGuide = { ...originalGuide, review_status: 'reviewed' }
      const html = await renderToString(createSSRApp(LearningReader, {
        hexagram: catalog[originalGuide.hexagram_id - 1] as Hexagram,
        guide: testCopy,
      }))
      expect(html).toContain(originalGuide.one_liner)
      expect(html).toContain(originalGuide.overview)
      for (const note of Object.values(originalGuide.line_guides)) expect(html).not.toContain(note)
      expect(originalGuide.review_status).toBe('draft')
    }
  })
})
