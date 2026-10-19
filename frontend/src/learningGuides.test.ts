import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { createSSRApp } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { describe, expect, it } from 'vitest'
import catalog from '../../backend/data/hexagrams.json'
import guides from './data/learning_guides.json'
import { reviewedGuide } from './learning'
import LearningReader from './components/LearningReader.vue'
import type { Hexagram, LearningGuide } from './types'

const hanLength = (text: string) => [...text.matchAll(/\p{Script=Han}/gu)].length
const reviewDocument = readFileSync(
  new URL('../../docs/learning-guides-review-01-04.md', import.meta.url),
  'utf8',
)
const firstFour = guides.filter((guide) => guide.hexagram_id <= 4)
const requiredFields = [
  'hexagram_id', 'one_liner', 'overview', 'line_guides',
  'editorial_version', 'references', 'review_status',
].sort()

describe('first four reviewed editorial guides', () => {
  it('ships exactly Qian, Kun, Zhun and Meng as complete reviewed LearningGuide records', () => {
    expect(firstFour.map((guide) => guide.hexagram_id)).toEqual([1, 2, 3, 4])
    expect(new Set(guides.map((guide) => guide.hexagram_id)).size).toBe(guides.length)
    for (const guide of firstFour) {
      expect(Object.keys(guide).sort()).toEqual(requiredFields)
      expect(guide.review_status).toBe('reviewed')
      expect(guide.editorial_version).toBe('learning-v1-01-04.1')
      expect(Object.keys(guide.line_guides)).toEqual(['1', '2', '3', '4', '5', '6'])
      // Compile-check every other field against the existing interface;
      // the JSON's status value is separately checked above.
      const checked: LearningGuide = { ...guide, review_status: 'reviewed' }
      expect(checked.hexagram_id).toBe(guide.hexagram_id)
    }
  })

  it('keeps the requested reading depth without empty or repeated line explanations', () => {
    const allLines = firstFour.flatMap((guide) => Object.values(guide.line_guides))
    expect(new Set(allLines).size).toBe(24)
    for (const guide of firstFour) {
      expect(hanLength(guide.one_liner)).toBeGreaterThanOrEqual(15)
      expect(hanLength(guide.one_liner)).toBeLessThanOrEqual(30)
      expect(hanLength(guide.overview)).toBeGreaterThanOrEqual(200)
      expect(hanLength(guide.overview)).toBeLessThanOrEqual(350)
      for (const text of Object.values(guide.line_guides)) {
        expect(hanLength(text)).toBeGreaterThanOrEqual(60)
        expect(hanLength(text)).toBeLessThanOrEqual(120)
      }
    }
  })

  it('uses each canonical pinned source and concrete traditional references', () => {
    for (const guide of firstFour) {
      const original = catalog[guide.hexagram_id - 1]!
      expect(guide.references[0]!.url).toBe(original.source_url)
      expect(guide.references[0]!.title).toContain(String(original.source_revision_id))
      expect(guide.references).toHaveLength(3)
      expect(new Set(guide.references.map((reference) => reference.url)).size).toBe(3)
      for (const reference of guide.references) {
        const url = new URL(reference.url)
        expect(url.protocol).toBe('https:')
        expect(url.hostname).toBe('zh.wikisource.org')
        expect(reference.title.trim().length).toBeGreaterThan(10)
        expect(reference.url).not.toMatch(/example|placeholder|TODO/i)
      }
    }
  })

  it('publishes exactly four guides and leaves the other sixty unannotated', () => {
    for (let id = 1; id <= 4; id++) expect(reviewedGuide(id)?.hexagram_id).toBe(id)
    for (let id = 5; id <= 64; id++) expect(reviewedGuide(id)).toBeUndefined()
    expect(guides.filter((guide) => guide.hexagram_id > 4).map((guide) => guide.review_status)).toEqual(['draft','draft','draft','draft'])
  })

  it('preserves the complete classical catalog byte for byte against the merged UI baseline', () => {
    const source = readFileSync(new URL('../../backend/data/hexagrams.json', import.meta.url))
    expect(createHash('sha256').update(source).digest('hex')).toBe(
      '3cce6f7d443fd08ada0e0aa80b306731bf833efe24daacead84444a6566a538f',
    )
  })

  it('keeps the complete audit document synchronized with the shipped drafts and original quotations', () => {
    for (const guide of firstFour) {
      expect(reviewDocument).toContain(guide.one_liner)
      expect(reviewDocument).toContain(guide.overview)
      for (const text of Object.values(guide.line_guides)) expect(reviewDocument).toContain(text)
      const original = catalog[guide.hexagram_id - 1]!
      expect(reviewDocument).toContain(original.judgment)
      for (const line of original.line_texts) expect(reviewDocument).toContain(line)
      for (const reference of guide.references) expect(reviewDocument).toContain(reference.url)
    }
    expect(reviewDocument).toContain(catalog[0]!.special_line!.text)
    expect(reviewDocument).toContain(catalog[1]!.special_line!.text)
  })

  it('does not render actual draft text even when it is passed directly to the reader', async () => {
    for (const original of catalog) {
      const candidate = guides.find((guide) => guide.hexagram_id === original.wenwang_order)
      const guide: LearningGuide | undefined = candidate
        ? { ...candidate, review_status: 'draft' }
        : undefined
      const html = await renderToString(createSSRApp(LearningReader, {
        hexagram: original as Hexagram,
        guide,
      }))
      expect(html).toContain('导读整理中')
      expect(html).toContain(original.judgment)
      for (const line of original.line_texts) expect(html).toContain(line)
      if (original.special_line) expect(html).toContain(original.special_line.text)
      if (guide) {
        expect(html).not.toContain(guide.one_liner)
        expect(html).not.toContain(guide.overview)
        for (const text of Object.values(guide.line_guides)) expect(html).not.toContain(text)
      }
    }
  })

  it('renders the approved summary, overview and references', async () => {
    for (const source of firstFour) {
      const guide: LearningGuide = { ...source, review_status: 'reviewed' }
      const html = await renderToString(createSSRApp(LearningReader, {
        hexagram: catalog[guide.hexagram_id - 1] as Hexagram,
        guide,
      }))
      expect(html).toContain(guide.one_liner)
      expect(html).toContain(guide.overview)
      for (const reference of guide.references) expect(html).toContain(reference.title)
      expect(html).not.toContain('导读整理中')
      expect(source.review_status).toBe('reviewed')
    }
  })
})
